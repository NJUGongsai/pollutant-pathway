"""P6 MCP Service — tool handlers.

Implements the 4 MCP tools with side effects matching the F3 matrix
(ADR-0006 / contracts/mcp_side_effects.py):

- predict_analogical_products_v1 → ``append_write_immutable_run`` (run write)
- get_run_v1                     → ``read-only``
- get_candidate_evidence_v1      → ``read-only``
- expand_evidence_v1             → ``append_immutable_child_run`` (child run)

Every mutation request is validated against its strict schema, carries an
idempotency key, and is resolved through the idempotency store so repeated /
concurrent calls reuse the same immutable run. Read-only tools never write.

Phase B (T5/T6) adds OPTIONAL security hooks — all default to ``None`` so
Phase-A callers (no policy configured) see unchanged behavior:

- ``policy`` (``RetentionPolicy``): when set, the kernel runs in *secured
  mode* — mutations stamp ``tenant_id``/``expires_at`` onto the run, reads
  require an ``AccessContext`` (fail-closed → ``UnauthorizedError``), and
  cross-tenant reads raise ``ForbiddenError``.
- ``budget_guard`` (``BudgetGuard``): cumulative per-tenant candidate budget,
  charged only on NEW run creation (idempotent reuse is free).
- ``payload_max_bytes``: rejects oversized payloads (``PayloadTooLargeError``)
  before schema validation.
- ``protocol_version``: pins the server protocol; a mismatched client version
  raises ``ProtocolVersionMismatchError``.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Optional

from reaction_agent.mcp.errors import (
    BudgetExceededError,
    ForbiddenError,
    PayloadTooLargeError,
    ProtocolError,
    ProtocolVersionMismatchError,
    RunNotFoundError,
    SnapshotUnavailableError,
    UnauthorizedError,
)
from reaction_agent.mcp.idempotency import IdempotencyStore, make_request_hash
from reaction_agent.mcp.runs import RunStore, RunRecord
from reaction_agent.mcp.schemas import validate_input

# Namespaced tool names (ADR field naming kept exact).
TOOL_PREDICT = "reaction.predict_analogical_products_v1"
TOOL_GET_RUN = "reaction.get_run_v1"
TOOL_GET_EVIDENCE = "reaction.get_candidate_evidence_v1"
TOOL_EXPAND = "reaction.expand_evidence_v1"

ALL_TOOLS = (TOOL_PREDICT, TOOL_GET_RUN, TOOL_GET_EVIDENCE, TOOL_EXPAND)


class ReactionMCPKernel:
    """Stateless kernel wiring the immutable run store + idempotency.

    The kernel does not depend on the LLM or on the MCP server transport,
    so every tool is usable without an LLM (Gate P6: usable-without-LLM).

    Phase-B security hooks are opt-in: pass ``policy=...`` to enter secured
    mode. Without a policy the kernel behaves exactly as in Phase A.
    """

    def __init__(
        self,
        run_store: RunStore,
        idem_store: IdempotencyStore,
        snapshots: Callable[[str], bool] | None = None,
        policy: Any | None = None,
        payload_max_bytes: Optional[int] = None,
        protocol_version: Optional[str] = None,
        budget_guard: Any | None = None,
    ):
        self.runs = run_store
        self.idem = idem_store
        # snapshot availability predicate: snapshot_id -> bool. Default: any.
        self._snapshots = snapshots or (lambda sid: True)
        # Phase B hooks (all optional)
        self._policy = policy
        self._payload_max = payload_max_bytes
        self._protocol_version = protocol_version
        self._budget = budget_guard

    # -- Phase B: security / hardening helpers -------------------------

    def _secured(self) -> bool:
        return self._policy is not None

    def _check_protocol_version(self, protocol_version: Optional[str]) -> None:
        if self._protocol_version is None or protocol_version is None:
            return
        if protocol_version != self._protocol_version:
            raise ProtocolVersionMismatchError(
                f"protocol version '{protocol_version}' != "
                f"'{self._protocol_version}'"
            )

    def _check_payload_size(self, payload: Any) -> None:
        if self._payload_max is None:
            return
        try:
            size = len(json.dumps(payload, ensure_ascii=False))
        except (TypeError, ValueError):
            return  # non-serializable payloads fall through to schema validation
        if size > self._payload_max:
            raise PayloadTooLargeError(
                f"payload {size}B exceeds cap {self._payload_max}B"
            )

    def _require_ctx(self, ctx: Any) -> None:
        """Fail-closed: secured mode requires an AccessContext."""
        if self._secured() and ctx is None:
            raise UnauthorizedError("secured mode requires an access context")

    def _authorize_tenant(self, run: RunRecord, ctx: Any) -> None:
        """Deny cross-tenant reads/expansions + unbound runs (fail-closed).

        GATE-P6-01: in secured mode an unbound (tenant_id=None) run is a
        legacy/mixed-in record and is denied to EVERY ctx — a missing tenant
        binding fails closed, not open.
        """
        if not self._secured() or ctx is None:
            return
        if run.tenant_id is None:
            raise ForbiddenError(
                f"run '{run.run_id}' is unbound; denied in secured mode"
            )
        if run.tenant_id != ctx.tenant_id:
            raise ForbiddenError(
                f"run '{run.run_id}' not accessible from tenant '{ctx.tenant_id}'"
            )

    def _tenant_of(self, ctx: Any) -> Optional[str]:
        return ctx.tenant_id if ctx is not None else None

    def _effective_key(self, key: str, ctx: Any) -> str:
        """Tenant-namespaced idem key in secured mode (GATE-P6-02).

        ``tenant:key`` so two tenants issuing the same idempotency_key get
        independent runs instead of silently sharing / conflicting. Unsecured
        mode uses the bare key (Phase-A behavior unchanged).
        """
        if self._secured() and ctx is not None:
            return f"{ctx.tenant_id}:{key}"
        return key

    def _expiry_now(self) -> Optional[float]:
        return self._policy.expiry_now() if self._secured() else None

    @staticmethod
    def _budget_requested(payload: dict) -> int:
        """Units to charge for a predict (default 1 if no budgets given)."""
        budgets = payload.get("budgets")
        if isinstance(budgets, dict):
            mc = budgets.get("max_candidates")
            if isinstance(mc, int) and not isinstance(mc, bool) and mc > 0:
                return mc
        return 1

    # -- pre-existing helpers (unchanged) ------------------------------

    def _require_snapshot(self, snapshot_id: str) -> None:
        if not self._snapshots(snapshot_id):
            raise SnapshotUnavailableError(f"snapshot '{snapshot_id}' is not available")

    def _require_idempotency(self, payload: dict) -> None:
        if "idempotency_key" not in payload:
            raise ProtocolError("mutation requires idempotency_key")

    # -- handlers ------------------------------------------------------

    def handle_predict(self, payload: dict, ctx: Any = None) -> dict:
        """predict → append_write_immutable_run (idempotent reuse or new run)."""
        validate_input(TOOL_PREDICT, payload)
        self._require_idempotency(payload)
        self._require_snapshot(payload["snapshot_id"])
        self._require_ctx(ctx)
        tenant = self._tenant_of(ctx)
        req_hash = make_request_hash(
            tool="predict", payload=payload.get("payload", payload),
            snapshot_id=payload["snapshot_id"], tenant=tenant,
        )
        key = payload["idempotency_key"]
        effective_key = self._effective_key(key, ctx)
        expiry = self._expiry_now()
        budget = self._budget
        requested = self._budget_requested(payload)
        runs = self.runs

        def _create(rid: str) -> RunRecord:
            # Budget is charged inside the idempotency create-run lambda so
            # idempotent REUSE never charges, and a rejection propagates
            # BEFORE the run / idem record is written (no orphan).
            if budget is not None:
                budget.check_and_commit(tenant, requested)
            return runs.create_run(
                tool="predict",
                request_hash=req_hash,
                snapshot_id=payload["snapshot_id"],
                payload=payload,
                run_id=rid,
                tenant_id=tenant,
                expires_at=expiry,
            )

        rec = self.idem.record_if_absent(
            key=effective_key,
            request_hash=req_hash,
            create_run=_create,
        )
        run = self.runs.get_run(rec.run_id)
        return {
            "run_id": run.run_id,
            "manifest_uri": f"reactionagent://runs/{run.run_id}/manifest",
            "status": run.freeze_state,
            "reused": rec.reused,
        }

    def handle_get_run(self, payload: dict, ctx: Any = None) -> dict:
        """get_run → read-only."""
        validate_input(TOOL_GET_RUN, payload)
        self._require_ctx(ctx)
        run = self.runs.get_run(payload["run_id"])
        self._authorize_tenant(run, ctx)
        return {
            "run_id": run.run_id,
            "tool": run.tool,
            "snapshot_id": run.snapshot_id,
            "freeze_state": run.freeze_state,
            "manifest_uri": f"reactionagent://runs/{run.run_id}/manifest",
        }

    def handle_get_candidate_evidence(self, payload: dict, ctx: Any = None) -> dict:
        """get_candidate_evidence → read-only."""
        validate_input(TOOL_GET_EVIDENCE, payload)
        self._require_ctx(ctx)
        run = self.runs.get_run(payload["run_id"])
        self._authorize_tenant(run, ctx)
        # Evidence id is stored on the run payload; read-only passthrough.
        evidence_uri = f"reactionagent://runs/{run.run_id}/evidence/{payload['evidence_id']}"
        return {
            "run_id": run.run_id,
            "evidence_id": payload["evidence_id"],
            "evidence_uri": evidence_uri,
        }

    def handle_expand(self, payload: dict, ctx: Any = None) -> dict:
        """expand_evidence → append_immutable_child_run (parent preserved)."""
        validate_input(TOOL_EXPAND, payload)
        self._require_idempotency(payload)
        self._require_snapshot(payload["snapshot_id"])
        self._require_ctx(ctx)
        parent = self.runs.get_run(payload["run_id"])  # parent must exist
        self._authorize_tenant(parent, ctx)  # cross-tenant expand denied
        tenant = self._tenant_of(ctx)
        req_hash = make_request_hash(
            tool="expand_evidence_local", payload=payload,
            snapshot_id=payload["snapshot_id"], tenant=tenant,
        )
        key = payload["idempotency_key"]
        effective_key = self._effective_key(key, ctx)
        expiry = self._expiry_now()

        def _create(rid: str) -> RunRecord:
            return self.runs.create_run(
                tool="expand_evidence_local",
                request_hash=req_hash,
                snapshot_id=payload["snapshot_id"],
                payload=payload,
                parent_run_id=parent.run_id,
                run_id=rid,
                tenant_id=tenant,
                expires_at=expiry,
            )

        rec = self.idem.record_if_absent(
            key=effective_key,
            request_hash=req_hash,
            create_run=_create,
        )
        child = self.runs.get_run(rec.run_id)
        return {
            "child_run_id": child.run_id,
            "parent_run_id": parent.run_id,
            "manifest_uri": f"reactionagent://runs/{child.run_id}/manifest",
            "status": child.freeze_state,
        }

    # -- dispatch ------------------------------------------------------

    def handle(
        self,
        tool_name: str,
        payload: dict,
        ctx: Any = None,
        protocol_version: Optional[str] = None,
    ) -> dict:
        """Dispatch one tool call. Raises typed P6Error on contract violation."""
        self._check_protocol_version(protocol_version)
        self._check_payload_size(payload)
        if tool_name == TOOL_PREDICT:
            return self.handle_predict(payload, ctx=ctx)
        if tool_name == TOOL_GET_RUN:
            return self.handle_get_run(payload, ctx=ctx)
        if tool_name == TOOL_GET_EVIDENCE:
            return self.handle_get_candidate_evidence(payload, ctx=ctx)
        if tool_name == TOOL_EXPAND:
            return self.handle_expand(payload, ctx=ctx)
        raise ProtocolError(f"unknown tool '{tool_name}'")
