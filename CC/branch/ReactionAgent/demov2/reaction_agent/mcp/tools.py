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
"""
from __future__ import annotations

from typing import Any, Callable

from reaction_agent.mcp.errors import (
    ProtocolError,
    RunNotFoundError,
    SnapshotUnavailableError,
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
    """Stateless kernel object wiring the immutable run store + idempotency.

    The kernel does not depend on the LLM or on the MCP server transport,
    so every tool is usable without an LLM (Gate P6: usable-without-LLM).
    """

    def __init__(
        self,
        run_store: RunStore,
        idem_store: IdempotencyStore,
        snapshots: Callable[[str], bool] | None = None,
    ):
        self.runs = run_store
        self.idem = idem_store
        # snapshot availability predicate: snapshot_id -> bool. Default: any.
        self._snapshots = snapshots or (lambda sid: True)

    # -- helpers -------------------------------------------------------

    def _require_snapshot(self, snapshot_id: str) -> None:
        if not self._snapshots(snapshot_id):
            raise SnapshotUnavailableError(f"snapshot '{snapshot_id}' is not available")

    def _require_idempotency(self, payload: dict) -> None:
        if "idempotency_key" not in payload:
            raise ProtocolError("mutation requires idempotency_key")

    # -- handlers ------------------------------------------------------

    def handle_predict(self, payload: dict) -> dict:
        """predict → append_write_immutable_run (idempotent reuse or new run)."""
        validate_input(TOOL_PREDICT, payload)
        self._require_idempotency(payload)
        self._require_snapshot(payload["snapshot_id"])
        req_hash = make_request_hash(
            tool="predict", payload=payload.get("payload", payload), snapshot_id=payload["snapshot_id"]
        )
        key = payload["idempotency_key"]
        rec = self.idem.record_if_absent(
            key=key,
            request_hash=req_hash,
            create_run=lambda rid: self.runs.create_run(
                tool="predict",
                request_hash=req_hash,
                snapshot_id=payload["snapshot_id"],
                payload=payload,
                run_id=rid,
            ),
        )
        run = self.runs.get_run(rec.run_id)
        return {
            "run_id": run.run_id,
            "manifest_uri": f"reactionagent://runs/{run.run_id}/manifest",
            "status": run.freeze_state,
            "reused": rec.run_id is not None,
        }

    def handle_get_run(self, payload: dict) -> dict:
        """get_run → read-only."""
        validate_input(TOOL_GET_RUN, payload)
        run = self.runs.get_run(payload["run_id"])
        return {
            "run_id": run.run_id,
            "tool": run.tool,
            "snapshot_id": run.snapshot_id,
            "freeze_state": run.freeze_state,
            "manifest_uri": f"reactionagent://runs/{run.run_id}/manifest",
        }

    def handle_get_candidate_evidence(self, payload: dict) -> dict:
        """get_candidate_evidence → read-only."""
        validate_input(TOOL_GET_EVIDENCE, payload)
        run = self.runs.get_run(payload["run_id"])
        # Evidence id is stored on the run payload; read-only passthrough.
        evidence_uri = f"reactionagent://runs/{run.run_id}/evidence/{payload['evidence_id']}"
        return {
            "run_id": run.run_id,
            "evidence_id": payload["evidence_id"],
            "evidence_uri": evidence_uri,
        }

    def handle_expand(self, payload: dict) -> dict:
        """expand_evidence → append_immutable_child_run (parent preserved)."""
        validate_input(TOOL_EXPAND, payload)
        self._require_idempotency(payload)
        self._require_snapshot(payload["snapshot_id"])
        parent = self.runs.get_run(payload["run_id"])  # parent must exist
        req_hash = make_request_hash(
            tool="expand_evidence_local", payload=payload, snapshot_id=payload["snapshot_id"]
        )
        key = payload["idempotency_key"]
        rec = self.idem.record_if_absent(
            key=key,
            request_hash=req_hash,
            create_run=lambda rid: self.runs.create_run(
                tool="expand_evidence_local",
                request_hash=req_hash,
                snapshot_id=payload["snapshot_id"],
                payload=payload,
                parent_run_id=parent.run_id,
                run_id=rid,
            ),
        )
        child = self.runs.get_run(rec.run_id)
        return {
            "child_run_id": child.run_id,
            "parent_run_id": parent.run_id,
            "manifest_uri": f"reactionagent://runs/{child.run_id}/manifest",
            "status": child.freeze_state,
        }

    # -- dispatch ------------------------------------------------------

    def handle(self, tool_name: str, payload: dict) -> dict:
        """Dispatch one tool call. Raises typed P6Error on contract violation."""
        if tool_name == TOOL_PREDICT:
            return self.handle_predict(payload)
        if tool_name == TOOL_GET_RUN:
            return self.handle_get_run(payload)
        if tool_name == TOOL_GET_EVIDENCE:
            return self.handle_get_candidate_evidence(payload)
        if tool_name == TOOL_EXPAND:
            return self.handle_expand(payload)
        raise ProtocolError(f"unknown tool '{tool_name}'")