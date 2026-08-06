"""P6 MCP Service — T5 resources: opaque URI, access control, retention.

Layered on top of the Phase-A immutable ``RunStore``. The kernel already
emits ``reactionagent://runs/{run_id}/...`` URIs (RUN_INVARIANT
``resource_uris_opaque``: agents must not derive URIs). This module makes
those URIs *opaque in the capability sense*: possession of the URI string
does NOT grant access — resolution always goes through an authorized
``AccessContext`` and the retention policy.

Fail-closed semantics:
- no ``AccessContext`` on a secured resource → ``UnauthorizedError``
- cross-tenant read → ``ForbiddenError``
- expired TTL → ``ResourceExpiredError``
- missing run → ``RunNotFoundError``
- corrupt run file → ``StorageError``
- malformed/unknown-scheme URI → ``ProtocolError``

Every failure is a typed ``P6Error`` subclass — never a raw exception.
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from reaction_agent.mcp.errors import (
    ForbiddenError,
    P6Error,
    ProtocolError,
    ResourceExpiredError,
    RunNotFoundError,
    StorageError,
    UnauthorizedError,
)
from reaction_agent.mcp.runs import RunRecord, RunStore

# Resource URI grammar:
#   reactionagent://runs/{run_id}/manifest
#   reactionagent://runs/{run_id}/evidence/{evidence_id}
SCHEME = "reactionagent"
HOST_RUNS = "runs"
_KIND_MANIFEST = "manifest"
_KIND_EVIDENCE = "evidence"


class ResourceURI:
    """Parsed opaque resource URI.

    Construct via ``render()`` (server-side minting) or ``parse()`` (client
    resolution). Clients must NOT derive URIs by string concatenation; the
    only legitimate source is a tool response. ``parse`` rejects unknown
    schemes, malformed paths, and unknown resource kinds with a typed error.
    """

    __slots__ = ("run_id", "kind", "evidence_id")

    def __init__(
        self,
        run_id: str,
        kind: str,
        evidence_id: Optional[str] = None,
    ):
        if kind not in (_KIND_MANIFEST, _KIND_EVIDENCE):
            raise ProtocolError(f"unknown resource kind '{kind}'")
        if kind == _KIND_EVIDENCE and not evidence_id:
            raise ProtocolError("evidence resource requires evidence_id")
        self.run_id = run_id
        self.kind = kind
        self.evidence_id = evidence_id

    def render(self) -> str:
        if self.kind == _KIND_MANIFEST:
            return f"{SCHEME}://{HOST_RUNS}/{self.run_id}/{_KIND_MANIFEST}"
        return f"{SCHEME}://{HOST_RUNS}/{self.run_id}/{_KIND_EVIDENCE}/{self.evidence_id}"

    @classmethod
    def parse(cls, uri: str) -> "ResourceURI":
        if not isinstance(uri, str) or not uri.startswith(f"{SCHEME}://"):
            raise ProtocolError(
                f"unsupported resource scheme (expected '{SCHEME}://')"
            )
        body = uri[len(f"{SCHEME}://"):]
        parts = body.split("/")
        # parts: [HOST_RUNS, run_id, kind, (evidence_id)]
        if len(parts) < 3 or parts[0] != HOST_RUNS:
            raise ProtocolError("malformed resource URI")
        run_id = parts[1]
        kind = parts[2]
        if not run_id:
            raise ProtocolError("malformed resource URI: empty run id")
        evidence_id = parts[3] if len(parts) > 3 else None
        if len(parts) > 4:
            raise ProtocolError("malformed resource URI: trailing segments")
        try:
            return cls(run_id=run_id, kind=kind, evidence_id=evidence_id)
        except ProtocolError:
            raise
        except Exception as exc:  # defensive: never leak a raw exception
            raise ProtocolError(f"malformed resource URI: {exc}")


class AccessContext:
    """Caller identity for access-control decisions.

    ``principal`` is the caller id; ``tenant_id`` scopes run ownership;
    ``roles`` is reserved for future role-based checks. A resource is
    readable iff ``ctx.tenant_id == run.tenant_id`` (or the run is unbound
    AND the kernel is in legacy/unsecured mode — secured mode always
    requires a matching tenant).
    """

    __slots__ = ("principal", "tenant_id", "roles")

    def __init__(
        self,
        principal: str,
        tenant_id: str,
        roles: Optional[set] = None,
    ):
        if not principal or not tenant_id:
            raise UnauthorizedError("access context requires principal and tenant_id")
        self.principal = principal
        self.tenant_id = tenant_id
        self.roles = set(roles) if roles else set()


class RetentionPolicy:
    """Retention rules for the run store.

    ``max_age_seconds`` — runs expire ``max_age_seconds`` after creation
    (time-based TTL). ``max_runs`` — sweep trims to at most ``max_runs``
    survivors, removing the earliest-expiring first. Both optional; a policy
    with neither set still puts the kernel in *secured mode* (ctx required,
    tenant stamped/checked) without purging anything.

    ``clock`` is injectable for deterministic tests.
    """

    __slots__ = ("max_age_seconds", "max_runs", "_clock")

    def __init__(
        self,
        max_age_seconds: Optional[float] = None,
        max_runs: Optional[int] = None,
        clock: Optional[Callable[[], float]] = None,
    ):
        self.max_age_seconds = max_age_seconds
        self.max_runs = max_runs
        self._clock = clock or time.time

    def expiry_now(self) -> Optional[float]:
        """Absolute expiry epoch for a run created now (None = immortal)."""
        if self.max_age_seconds is None:
            return None
        return self._clock() + self.max_age_seconds

    def is_expired(self, run: RunRecord) -> bool:
        if run.expires_at is None:
            return False
        return self._clock() > run.expires_at


class ResourceManager:
    """Mints + resolves opaque resource URIs with access control + retention.

    Wraps a ``RunStore``. ``resolve`` is the single authorized entry point
    for reading a resource by URI; it parses the URI, loads the run, checks
    tenant binding, then checks retention — failing closed with a typed
    ``P6Error`` at every step.
    """

    def __init__(
        self,
        run_store: RunStore,
        policy: Optional[RetentionPolicy] = None,
    ):
        self._runs = run_store
        self._policy = policy

    # -- minting (server side) --

    def mint_manifest_uri(self, run_id: str) -> str:
        return ResourceURI(run_id=run_id, kind=_KIND_MANIFEST).render()

    def mint_evidence_uri(self, run_id: str, evidence_id: str) -> str:
        return ResourceURI(
            run_id=run_id, kind=_KIND_EVIDENCE, evidence_id=evidence_id
        ).render()

    # -- resolution (client side, authorized) --

    def resolve(self, uri: str, ctx: Optional[AccessContext]) -> dict:
        parsed = ResourceURI.parse(uri)  # ProtocolError on malformed
        if ctx is None:
            raise UnauthorizedError("resource resolution requires an access context")
        run = self._runs.get_run(parsed.run_id)  # RunNotFoundError / StorageError
        self._authorize(run, ctx)  # ForbiddenError on cross-tenant
        self._check_retention(run)  # ResourceExpiredError on TTL
        if parsed.kind == _KIND_MANIFEST:
            return {"run_id": run.run_id, "manifest": run.to_dict()}
        return {
            "run_id": run.run_id,
            "evidence_id": parsed.evidence_id,
            "evidence_uri": parsed.render(),
        }

    # -- internal checks --

    def _authorize(self, run: RunRecord, ctx: AccessContext) -> None:
        # Unbound runs (legacy/Phase-A) are readable by anyone in unsecured
        # mode; but in secured mode (policy set) a bound run requires an
        # exact tenant match — fail-closed on mismatch.
        if run.tenant_id is not None and run.tenant_id != ctx.tenant_id:
            raise ForbiddenError(
                f"run '{run.run_id}' not accessible from tenant '{ctx.tenant_id}'"
            )

    def _check_retention(self, run: RunRecord) -> None:
        if self._policy is not None and self._policy.is_expired(run):
            raise ResourceExpiredError(f"run '{run.run_id}' expired")

    # -- sweep --

    def sweep(self) -> int:
        """Purge expired (TTL) and over-cap (max_runs) runs. Returns count."""
        if self._policy is None:
            return 0
        runs: list = []
        for rid in self._runs.list_runs():
            try:
                runs.append((rid, self._runs.get_run(rid)))
            except P6Error:
                # a corrupt/unreadable run is swept away too
                self._runs.delete_run(rid)
        removed = 0
        # 1. time-based expiry
        for rid, run in runs:
            if self._policy.is_expired(run):
                self._runs.delete_run(rid)
                removed += 1
        # 2. count cap on survivors (earliest-expiring first)
        if self._policy.max_runs is not None:
            survivors = [
                (rid, run)
                for rid, run in runs
                if not self._policy.is_expired(run)
            ]
            survivors.sort(
                key=lambda pair: pair[1].expires_at
                if pair[1].expires_at is not None
                else float("inf")
            )
            excess = len(survivors) - self._policy.max_runs
            for rid, _ in survivors[: max(0, excess)]:
                self._runs.delete_run(rid)
                removed += 1
        return removed
