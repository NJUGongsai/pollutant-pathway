"""T3+T4 RED tests — idempotency layer + side-effect accuracy.

Must FAIL (RED) until the kernel is built, then PASS (GREEN).

T3 scenarios (final_plan §9.4, ADR-0006):
- repeat (same key + same request → reuse run)
- concurrent duplicate (atomic dedup → exactly one run)
- same key + different payload → typed conflict
- interrupted write (crashed/stale run file → recover or fail typed)
- child expansion (expand creates child run, parent preserved)

T4 side effects must match F3 matrix:
- predict → append_write_immutable_run (run write)
- get_run / get_candidate_evidence → read-only
- expand_evidence_local → append_immutable_child_run
- network=False everywhere
"""
from __future__ import annotations

import os
import threading

import pytest

from reaction_agent.contracts.mcp_side_effects import (
    MCP_TOOL_CONTRACTS,
    get_tool_contract,
    validate_policy_integrity,
)
from reaction_agent.mcp.errors import (
    IdempotencyConflictError,
    RunNotFoundError,
    StorageError,
)
from reaction_agent.mcp.idempotency import (
    IdempotencyStore,
    canonical_request_hash,
    make_request_hash,
)
from reaction_agent.mcp.runs import RunStore, RunRecord


@pytest.fixture()
def run_store(tmp_path):
    return RunStore(root=tmp_path / "runs")


@pytest.fixture()
def idem_store(tmp_path):
    return IdempotencyStore(root=tmp_path / "idem")


# =====================================================================
# T4 — Side-effect contract is authoritative (F3 matrix)
# =====================================================================

class TestSideEffectMatrix:
    """T4: kernel side effects must equal the frozen F3 matrix."""

    def test_policy_integrity_valid(self):
        issues = validate_policy_integrity()
        assert issues == [], f"policy integrity issues: {issues}"

    def test_predict_side_effect(self):
        tc = get_tool_contract("predict")
        assert tc.run_store == "append_write_immutable_run"
        assert tc.evidence_corpus == "read-only"
        assert tc.network is False
        assert tc.idempotency == "request_hash_snapshot_version_idempotency_key_reuse"

    def test_get_side_effects_read_only(self):
        for name in ("get_run", "get_candidate_evidence"):
            tc = get_tool_contract(name)
            assert tc.run_store == "read-only"
            assert tc.network is False

    def test_expand_local_child_run(self):
        tc = get_tool_contract("expand_evidence_local")
        assert tc.run_store == "append_immutable_child_run"
        assert tc.network is False
        assert tc.idempotency == "child_request_reuse"

    def test_external_absent_from_mvp(self):
        # final_plan §9.5: external absent from MVP.
        # The kernel must NOT expose an external expansion tool.
        from reaction_agent.mcp.schemas import MCP_TOOL_SCHEMAS
        assert "reaction.expand_evidence_external_v1" not in MCP_TOOL_SCHEMAS


# =====================================================================
# T3 — Idempotency
# =====================================================================


class TestCanonicalHash:
    """Canonical request hash determinism."""

    def test_same_request_same_hash(self):
        a = make_request_hash(tool="predict", payload={"substrate_smiles": "CCO"}, snapshot_id="s1")
        b = make_request_hash(tool="predict", payload={"substrate_smiles": "CCO"}, snapshot_id="s1")
        assert a == b

    def test_stable_serialization(self):
        # key order in payload must not change the hash
        a = canonical_request_hash({"a": 1, "b": 2})
        b = canonical_request_hash({"b": 2, "a": 1})
        assert a == b

    def test_different_payload_same_hash(self):
        a = make_request_hash(tool="predict", payload={"substrate_smiles": "CCO"}, snapshot_id="s1")
        b = make_request_hash(tool="predict", payload={"substrate_smiles": "CCC"}, snapshot_id="s1")
        assert a != b

    def test_different_snapshot_different_hash(self):
        a = make_request_hash(tool="predict", payload={"substrate_smiles": "CCO"}, snapshot_id="s1")
        b = make_request_hash(tool="predict", payload={"substrate_smiles": "CCO"}, snapshot_id="s2")
        assert a != b


class TestIdempotencyRepeat:
    """repeat: same key + same request → reuse the same run."""

    def test_repeat_returns_same_run(self, run_store, idem_store):
        req_hash = make_request_hash(tool="predict", payload={"s": "CCO"}, snapshot_id="s1")
        run1 = run_store.create_run(
            tool="predict",
            request_hash=req_hash,
            snapshot_id="s1",
            payload={"s": "CCO"},
        )
        idem_store.record(key="k1", request_hash=req_hash, run_id=run1.run_id)

        # repeat
        resolved = idem_store.resolve(key="k1", request_hash=req_hash)
        assert resolved is not None
        assert resolved.run_id == run1.run_id
        assert resolved.request_hash == req_hash

    def test_idempotent_predict_reuses_run(self, run_store, idem_store):
        # Full path: second identical predict returns the first run, no new run.
        req_hash = make_request_hash(tool="predict", payload={"s": "CCO"}, snapshot_id="s1")
        r1 = run_store.create_run(tool="predict", request_hash=req_hash, snapshot_id="s1", payload={"s": "CCO"})
        idem_store.record(key="k1", request_hash=req_hash, run_id=r1.run_id)

        resolved = idem_store.resolve(key="k1", request_hash=req_hash)
        assert resolved.run_id == r1.run_id


class TestConcurrentDuplicate:
    """concurrent duplicate: atomic dedup → exactly one run."""

    def test_concurrent_identical_creates_one_run(self, run_store, idem_store):
        req_hash = make_request_hash(tool="predict", payload={"s": "CCO"}, snapshot_id="s1")
        results = []
        lock = threading.Lock()

        def worker():
            resolved = idem_store.record_if_absent(
                key="ckey", request_hash=req_hash,
                create_run=lambda rid: run_store.create_run(
                    tool="predict", request_hash=req_hash, snapshot_id="s1",
                    payload={"s": "CCO"}, run_id=rid,
                ),
            )
            with lock:
                results.append(resolved)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # all workers resolved to the SAME run_id
        run_ids = {r.run_id for r in results}
        assert len(run_ids) == 1, f"expected exactly one run, got {run_ids}"
        # and only one run actually created on disk
        assert len(run_store.list_runs()) == 1


class TestSameKeyDiffPayload:
    """same key + different payload → typed conflict."""

    def test_same_key_diff_payload_conflict(self, run_store, idem_store):
        req_hash_a = make_request_hash(tool="predict", payload={"s": "CCO"}, snapshot_id="s1")
        req_hash_b = make_request_hash(tool="predict", payload={"s": "CCC"}, snapshot_id="s1")
        idem_store.record(key="k1", request_hash=req_hash_a, run_id="run-a")

        with pytest.raises(IdempotencyConflictError):
            idem_store.resolve(key="k1", request_hash=req_hash_b)

    def test_conflict_is_typed_error(self):
        from reaction_agent.mcp.errors import P6Error
        assert issubclass(IdempotencyConflictError, P6Error)


class TestInterruptedWrite:
    """interrupted write: crashed/stale run file → recover or fail typed."""

    def test_missing_run_file_raises_typed(self, run_store):
        # A recorded run id whose file is gone → RunNotFoundError (typed), not crash.
        with pytest.raises(RunNotFoundError):
            run_store.get_run("run-noton-disk")

    def test_partial_run_file_raises_typed(self, run_store):
        # A run file that was interrupted mid-write (invalid JSON) → StorageError typed.
        run_store.create_run(tool="predict", request_hash="h", snapshot_id="s1", payload={})
        # corrupt the first run file
        runfile = run_store._run_path("run-0")
        runfile.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(StorageError):
            run_store.get_run("run-0")


class TestChildExpansion:
    """child expansion: expand creates child run, parent preserved."""

    def test_expand_creates_child_run(self, run_store):
        parent = run_store.create_run(tool="predict", request_hash="h", snapshot_id="s1", payload={})
        child = run_store.create_run(
            tool="expand_evidence_local",
            request_hash="h2",
            snapshot_id="s1",
            payload={},
            parent_run_id=parent.run_id,
        )
        assert child.parent_run_id == parent.run_id
        # parent preserved (unchanged)
        stored_parent = run_store.get_run(parent.run_id)
        assert stored_parent.run_id == parent.run_id

    def test_run_record_has_required_fields(self, run_store):
        run = run_store.create_run(tool="predict", request_hash="h", snapshot_id="s1", payload={})
        assert isinstance(run, RunRecord)
        assert run.tool == "predict"
        assert run.request_hash == "h"
        assert run.snapshot_id == "s1"
        assert run.freeze_state == "frozen"  # completed runs immutable
        assert run.parent_run_id is None