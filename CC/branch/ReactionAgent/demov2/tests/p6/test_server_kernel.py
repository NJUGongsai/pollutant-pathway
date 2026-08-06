"""P6 server tests — kernel dispatch + typed failures (usable without LLM).

Covers the full tool-dispatch path (no LLM, no MCP transport): the kernel
rejects protocol violations, resolves idempotency, enforces side effects,
and never lets an uncaught exception escape a tool call.
"""
from __future__ import annotations

import pytest

from reaction_agent.mcp.errors import (
    IdempotencyConflictError,
    ProtocolError,
    RunNotFoundError,
    SchemaError,
    SnapshotUnavailableError,
)
from reaction_agent.mcp.idempotency import IdempotencyStore
from reaction_agent.mcp.runs import RunStore
from reaction_agent.mcp.tools import (
    TOOL_EXPAND,
    TOOL_GET_EVIDENCE,
    TOOL_GET_RUN,
    TOOL_PREDICT,
    ReactionMCPKernel,
)


@pytest.fixture()
def kernel(tmp_path):
    return ReactionMCPKernel(
        run_store=RunStore(tmp_path / "runs"),
        idem_store=IdempotencyStore(tmp_path / "idem"),
    )


def _predict_payload(smiles="CCO", key="k1", snap="s1"):
    return {
        "substrate_smiles": smiles,
        "idempotency_key": key,
        "snapshot_id": snap,
    }


class TestKernelPredict:
    def test_predict_creates_immutable_run(self, kernel):
        out = kernel.handle(TOOL_PREDICT, _predict_payload())
        assert out["run_id"]
        assert out["manifest_uri"].startswith("reactionagent://runs/")
        assert out["status"] == "frozen"

    def test_predict_requires_idempotency_key(self, kernel):
        # idempotency_key is in the strict schema's required set, so removing
        # it is rejected as a typed schema error (ADR-0006: predict without
        # idempotency key → protocol/schema error, never a crash).
        payload = _predict_payload()
        del payload["idempotency_key"]
        with pytest.raises((SchemaError, ProtocolError)):
            kernel.handle(TOOL_PREDICT, payload)

    def test_predict_rejects_unknown_field(self, kernel):
        payload = _predict_payload()
        payload["bogus"] = True
        with pytest.raises(SchemaError):
            kernel.handle(TOOL_PREDICT, payload)

    def test_predict_rejects_unknown_snapshot(self, kernel):
        def snapshots(sid):
            return sid == "known"
        k = ReactionMCPKernel(
            run_store=kernel.runs,
            idem_store=kernel.idem,
            snapshots=snapshots,
        )
        with pytest.raises(SnapshotUnavailableError):
            k.handle(TOOL_PREDICT, _predict_payload(snap="nope"))


class TestKernelIdempotency:
    def test_repeat_reuses_same_run(self, kernel):
        a = kernel.handle(TOOL_PREDICT, _predict_payload())
        b = kernel.handle(TOOL_PREDICT, _predict_payload())
        assert a["run_id"] == b["run_id"]

    def test_same_key_diff_payload_conflict(self, kernel):
        kernel.handle(TOOL_PREDICT, _predict_payload(smiles="CCO"))
        with pytest.raises(IdempotencyConflictError):
            kernel.handle(TOOL_PREDICT, _predict_payload(smiles="CCC"))

    def test_different_key_different_run(self, kernel):
        a = kernel.handle(TOOL_PREDICT, _predict_payload(key="k1"))
        b = kernel.handle(TOOL_PREDICT, _predict_payload(key="k2"))
        assert a["run_id"] != b["run_id"]


class TestKernelReadOnly:
    def test_get_run_reads(self, kernel):
        created = kernel.handle(TOOL_PREDICT, _predict_payload())
        got = kernel.handle(TOOL_GET_RUN, {"run_id": created["run_id"]})
        assert got["run_id"] == created["run_id"]
        assert got["freeze_state"] == "frozen"

    def test_get_run_missing_typed(self, kernel):
        with pytest.raises(RunNotFoundError):
            kernel.handle(TOOL_GET_RUN, {"run_id": "run-nope"})

    def test_get_evidence_read_only(self, kernel):
        created = kernel.handle(TOOL_PREDICT, _predict_payload())
        out = kernel.handle(
            TOOL_GET_EVIDENCE,
            {"run_id": created["run_id"], "evidence_id": "ev-1"},
        )
        assert out["evidence_uri"].endswith("/evidence/ev-1")


class TestKernelExpand:
    def test_expand_creates_child_run_parent_preserved(self, kernel):
        parent = kernel.handle(TOOL_PREDICT, _predict_payload())
        child = kernel.handle(
            TOOL_EXPAND,
            {
                "run_id": parent["run_id"],
                "evidence_id": "ev-1",
                "idempotency_key": "exp-1",
                "snapshot_id": "s1",
            },
        )
        assert child["child_run_id"] != child["parent_run_id"]
        assert child["parent_run_id"] == parent["run_id"]
        # parent still readable and unchanged
        got_parent = kernel.handle(TOOL_GET_RUN, {"run_id": parent["run_id"]})
        assert got_parent["run_id"] == parent["run_id"]

    def test_expand_requires_parent_exists(self, kernel):
        with pytest.raises(RunNotFoundError):
            kernel.handle(
                TOOL_EXPAND,
                {
                    "run_id": "run-missing",
                    "evidence_id": "ev-1",
                    "idempotency_key": "exp-1",
                    "snapshot_id": "s1",
                },
            )

    def test_expand_idempotent_reuse(self, kernel):
        parent = kernel.handle(TOOL_PREDICT, _predict_payload())
        payload = {
            "run_id": parent["run_id"],
            "evidence_id": "ev-1",
            "idempotency_key": "exp-same",
            "snapshot_id": "s1",
        }
        a = kernel.handle(TOOL_EXPAND, payload)
        b = kernel.handle(TOOL_EXPAND, payload)
        assert a["child_run_id"] == b["child_run_id"]


class TestNoUncaughtLeak:
    def test_unknown_tool_typed(self, kernel):
        with pytest.raises(ProtocolError):
            kernel.handle("reaction.bogus_tool_v1", {})

    def test_all_errors_are_typed_p6(self, kernel):
        # every failure path raises P6Error subclass, never raw Exception
        from reaction_agent.mcp.errors import P6Error
        for fn, payload in [
            (lambda: kernel.handle(TOOL_PREDICT, {"x": 1}), SchemaError),
            (lambda: kernel.handle(TOOL_EXPAND, {}), (SchemaError, ProtocolError)),
            (lambda: kernel.handle(TOOL_GET_RUN, {"run_id": "nope"}), RunNotFoundError),
        ]:
            with pytest.raises((P6Error, SchemaError, ProtocolError, RunNotFoundError)):
                fn()
            assert True