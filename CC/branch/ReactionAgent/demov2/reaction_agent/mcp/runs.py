"""P6 MCP Service — immutable run store.

RunRecord is a frozen, content-addressed prediction run. Completed runs are
immutable: once written they are never modified in place. Evidence expansion
writes a child run that preserves the parent's identity and never overwrites
the parent result (RUN_INVARIANTS: completed_run_immutable,
frozen_run_immutable, child_run_preserves_parent).

Storage is atomic (write-then-rename) so an interrupted write never leaves a
half-written run that reads as valid. A corrupt/partial file raises a typed
StorageError rather than crashing.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from reaction_agent.mcp.errors import RunNotFoundError, StorageError


class RunRecord:
    """Immutable run record (frozen after creation)."""

    __slots__ = (
        "run_id", "tool", "request_hash", "snapshot_id", "payload",
        "parent_run_id", "freeze_state", "created_at",
        # Phase B (T5): tenant binding + retention expiry. Optional so that
        # legacy runs / Phase-A callers (no policy configured) keep working.
        "tenant_id", "expires_at",
    )

    def __init__(
        self,
        run_id: str,
        tool: str,
        request_hash: str,
        snapshot_id: str,
        payload: dict,
        parent_run_id: Optional[str] = None,
        freeze_state: str = "frozen",
        created_at: Optional[str] = None,
        tenant_id: Optional[str] = None,
        expires_at: Optional[float] = None,
    ):
        self.run_id = run_id
        self.tool = tool
        self.request_hash = request_hash
        self.snapshot_id = snapshot_id
        self.payload = payload
        self.parent_run_id = parent_run_id
        self.freeze_state = freeze_state
        self.created_at = created_at or "1970-01-01T00:00:00Z"
        self.tenant_id = tenant_id
        self.expires_at = expires_at

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "tool": self.tool,
            "request_hash": self.request_hash,
            "snapshot_id": self.snapshot_id,
            "payload": self.payload,
            "parent_run_id": self.parent_run_id,
            "freeze_state": self.freeze_state,
            "created_at": self.created_at,
            "tenant_id": self.tenant_id,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RunRecord":
        return cls(
            run_id=data["run_id"],
            tool=data["tool"],
            request_hash=data["request_hash"],
            snapshot_id=data["snapshot_id"],
            payload=data.get("payload", {}),
            parent_run_id=data.get("parent_run_id"),
            freeze_state=data.get("freeze_state", "frozen"),
            created_at=data.get("created_at"),
            tenant_id=data.get("tenant_id"),
            expires_at=data.get("expires_at"),
        )


class RunStore:
    """Atomic, immutable run store keyed by run_id."""

    def __init__(self, root: os.PathLike | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _run_path(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"

    def create_run(
        self,
        tool: str,
        request_hash: str,
        snapshot_id: str,
        payload: dict,
        parent_run_id: Optional[str] = None,
        run_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        expires_at: Optional[float] = None,
    ) -> RunRecord:
        """Atomically create and persist a frozen run.

        Completed runs are immutable by construction (file written once via
        write-then-rename; never overwritten afterwards).
        """
        rid = run_id or f"run-{self._next_index()}"
        # If a frozen run with this id already exists, we must not overwrite it.
        existing_path = self._run_path(rid)
        if existing_path.exists():
            raise StorageError(f"run '{rid}' already exists (immutable run store)")

        record = RunRecord(
            run_id=rid,
            tool=tool,
            request_hash=request_hash,
            snapshot_id=snapshot_id,
            payload=payload,
            parent_run_id=parent_run_id,
            freeze_state="frozen",
            tenant_id=tenant_id,
            expires_at=expires_at,
        )
        self._atomic_write(existing_path, record.to_dict())
        return record

    def get_run(self, run_id: str) -> RunRecord:
        path = self._run_path(run_id)
        if not path.exists():
            raise RunNotFoundError(f"run '{run_id}' not found")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            raise StorageError(f"run '{run_id}' is corrupt or unreadable: {exc}")
        return RunRecord.from_dict(data)

    def list_runs(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*.json"))

    def delete_run(self, run_id: str) -> None:
        """Remove a run file (retention sweep). No-op if absent."""
        path = self._run_path(run_id)
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise StorageError(f"failed to delete run '{run_id}': {exc}")

    def _next_index(self) -> int:
        return len(self.list_runs())

    def _atomic_write(self, path: Path, data: dict) -> None:
        """Write to a temp file then rename (atomic). Survives interruption."""
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
            raise StorageError(f"failed to persist run: {exc}")