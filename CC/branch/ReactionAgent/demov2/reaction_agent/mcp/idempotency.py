"""P6 MCP Service — idempotency layer.

Implements ADR-0006 idempotency semantics over the immutable run store:

- canonical request hash = stable, order-independent serialization of the
  tool + payload + snapshot_id (deterministic).
- same key + same request hash  → reuse existing run (idempotent reuse).
- same key + different request  → IdempotencyConflictError (typed).
- concurrent identical requests → atomic dedup: exactly one run created,
  all callers observe the same run_id.

Every mutation payload carries ``client_request_id`` / ``idempotency_key`` /
``snapshot_id``. A request without an idempotency key → ProtocolError.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from reaction_agent.mcp.errors import (
    IdempotencyConflictError,
    ProtocolError,
    StorageError,
)

# Local lock for record_if_absent atomics within this process (tests use threads).
_thread_lock = threading.Lock()


def canonical_request_hash(obj: Any) -> str:
    """Hashing-aware stable hash of a JSON-serializable object.

    Key order does not matter; types are not coerced. Returns a hex digest.
    """
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_request_hash(
    tool: str,
    payload: dict,
    snapshot_id: str,
    tenant: Optional[str] = None,
) -> str:
    """Canonical request hash = sha256(tool + payload + snapshot_id [+ tenant]).

    ``tenant`` is mixed into the hash in secured mode so that two tenants
    issuing the same payload produce different hashes (and thus different
    content-addressed run ids) — GATE-P6-02 tenant isolation. Unsecured
    callers omit ``tenant`` and get byte-identical hashes to Phase A.
    """
    obj: dict = {"tool": tool, "payload": payload, "snapshot_id": snapshot_id}
    if tenant is not None:
        obj["tenant"] = tenant
    return canonical_request_hash(obj)


class IdempotencyRecord:
    """A persisted idempotency mapping key → {request_hash, run_id}.

    ``reused`` is a *call-time* flag (not persisted): True when the
    ``record_if_absent`` call hit an existing record (idempotent reuse),
    False when it created a new run. Persisted records always load with
    ``reused=False``; callers that round-trip through disk and need the
    flag should use ``record_if_absent`` (which sets it correctly).
    """

    __slots__ = ("key", "request_hash", "run_id", "reused")

    def __init__(self, key: str, request_hash: str, run_id: str, reused: bool = False):
        self.key = key
        self.request_hash = request_hash
        self.run_id = run_id
        self.reused = reused


class IdempotencyStore:
    """Persistent idempotency store with atomic dedup."""

    def __init__(self, root: os.PathLike | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._root_resolved = self.root.resolve()  # GATE-P6-07 containment

    def _path(self, key: str) -> Path:
        # GATE-P6-07: defense-in-depth containment. A key with '/' or '..'
        # cannot escape the root even if a caller bypasses the schema pattern.
        path = (self.root / f"{key}.json").resolve()
        try:
            path.relative_to(self._root_resolved)
        except ValueError:
            raise StorageError(f"idempotency key '{key}' escapes store root")
        return path

    def _read(self, key: str) -> Optional[IdempotencyRecord]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return IdempotencyRecord(
                key=data["key"],
                request_hash=data["request_hash"],
                run_id=data["run_id"],
            )
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            raise StorageError(f"idempotency record '{key}' unreadable: {exc}")

    def _write(self, record: IdempotencyRecord) -> None:
        data = {
            "key": record.key,
            "request_hash": record.request_hash,
            "run_id": record.run_id,
        }
        path = self._path(record.key)
        import tempfile
        fd, tmp = tempfile.mkstemp(dir=str(self.root), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except OSError as exc:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise StorageError(f"failed to persist idempotency key '{record.key}': {exc}")

    def record(self, key: str, request_hash: str, run_id: str) -> IdempotencyRecord:
        rec = IdempotencyRecord(key=key, request_hash=request_hash, run_id=run_id)
        self._write(rec)
        return rec

    def resolve(self, key: str, request_hash: str) -> IdempotencyRecord:
        """Resolve an idempotency key.

        Returns the existing record when key+hash match (idempotent reuse);
        raises IdempotencyConflictError when the same key maps to a different
        request (ADR-0006 same_key_different_request → typed_conflict); raises
        StorageError when the stored record is unreadable.
        """
        rec = self._read(key)
        if rec is None:
            # not yet recorded
            raise ProtocolError(f"idempotency key '{key}' not recorded")
        if rec.request_hash != request_hash:
            raise IdempotencyConflictError(
                f"idempotency key '{key}' already used with a different request"
            )
        return rec

    def record_if_absent(
        self,
        key: str,
        request_hash: str,
        create_run: Callable[[str], Any],
    ) -> IdempotencyRecord:
        """Atomic dedup (ADR-0006 concurrent_identical → atomic_dedup).

        If the key is already recorded:
          - matching hash → return existing (reuse), no new run.
          - different hash → IdempotencyConflictError.
        If not recorded: serialize creation under a per-key lock so that among
        concurrent identical requests exactly one run is created and all
        callers observe the same run_id.
        """
        # Fast path: already recorded.
        rec = self._read(key)
        if rec is not None:
            if rec.request_hash != request_hash:
                raise IdempotencyConflictError(
                    f"idempotency key '{key}' already used with a different request"
                )
            return IdempotencyRecord(rec.key, rec.request_hash, rec.run_id, reused=True)

        with _thread_lock:
            # Re-check under lock (another thread may have recorded meanwhile).
            rec = self._read(key)
            if rec is not None:
                if rec.request_hash != request_hash:
                    raise IdempotencyConflictError(
                        f"idempotency key '{key}' already used with a different request"
                    )
                return IdempotencyRecord(rec.key, rec.request_hash, rec.run_id, reused=True)
            # Content-addressed run id: deterministic from the request hash so
            # concurrent identical requests converge on the same run_id.
            run_id = f"run-{request_hash[:16]}"
            created = create_run(run_id)
            run_id = getattr(created, "run_id", None) or run_id
            rec = IdempotencyRecord(
                key=key, request_hash=request_hash, run_id=run_id, reused=False
            )
            self._write(rec)
            return rec

    # -- retention sweep support (GATE-P6-04) --

    def list_keys(self) -> list[str]:
        """All recorded idempotency keys (for zombie cleanup)."""
        return sorted(p.stem for p in self.root.glob("*.json"))

    def delete(self, key: str) -> None:
        """Remove an idempotency record (zombie cleanup). No-op if absent."""
        path = self._path(key)
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise StorageError(f"failed to delete idempotency key '{key}': {exc}")