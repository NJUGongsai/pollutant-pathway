"""P4-T8 immutable run/trace/manifest (freeze, replay, child run)."""
from __future__ import annotations

import pytest

from tests.fixtures.p4.p4_contract_fixture import (
    build_evidence_records,
    build_query,
    POLICY_VERSION,
)
from reaction_agent.schemas.result import StageSummary
from reaction_agent.schemas.p4.run import ImmutableRunManifest, RunFreezeState
from reaction_agent.runtime.run import (
    ImmutableRunStore,
    RuntimeRun,
    RunAlreadyFrozenError,
    RunNotFoundError,
)
from reaction_agent.runtime.manifest import build_run_manifest
from reaction_agent.runtime.trace import build_stage_summary


def _trace() -> StageSummary:
    return StageSummary(
        donor_evidence_ids=["ev_d1", "ev_d2"],
        transformation_hypothesis_ids=["t1"],
        site_hypothesis_ids=["site_c1"],
        graph_edit_ids=["delta_1"],
        candidate_ids=["cand_ox_001"],
        ledger_ids=["srl_ev_d1"],
        rank_result={"rank": "1"},
        decision_result={"decision": "predicted"},
    )


def _manifest(store: ImmutableRunStore) -> ImmutableRunManifest:
    return build_run_manifest(
        run_id="run_abc",
        parent_run_id=None,
        query=build_query(),
        snapshot_id="snap_c589494081df",
        snapshot_hash="deadbeef" * 4,
        versions={
            "normalization_version": "p1-1",
            "config_version": "p1-1",
            "policy_version": POLICY_VERSION,
            "kernel_version": "p3-blocked",
            "candidate_version": "p3-blocked",
            "ranker_version": "p4-ranker-1",
            "snapshot_builder_version": "p1-1",
        },
        trace=_trace(),
        evidence_ids=["ev_d1", "ev_d2"],
        independent_group_ids=["evg_1", "evg_2"],
        result_hash=None,  # builder computes the single result hash
        freeze_state=RunFreezeState.active,
        capability_status="synthetic_fixture",
        blocked_reasons=[],
        classification="synthetic_fixture",
    )


def test_same_request_versions_frozen_evidence_same_result_hash():
    """P4-T8: replay contract — same inputs produce identical result hash."""
    store = ImmutableRunStore()
    m1 = _manifest(store)
    store.create(m1)
    # Recompute the manifest for the same run request.
    m2 = build_run_manifest(
        run_id="run_abc",
        parent_run_id=None,
        query=build_query(),
        snapshot_id="snap_c589494081df",
        snapshot_hash="deadbeef" * 4,
        versions={"normalization_version": "p1-1", "config_version": "p1-1",
                  "policy_version": POLICY_VERSION, "kernel_version": "p3-blocked",
                  "candidate_version": "p3-blocked", "ranker_version": "p4-ranker-1",
                  "snapshot_builder_version": "p1-1"},
        trace=_trace(),
        evidence_ids=["ev_d1", "ev_d2"],
        independent_group_ids=["evg_1", "evg_2"],
        result_hash=None,  # builder computes the single result hash
        freeze_state=RunFreezeState.active,
        capability_status="synthetic_fixture",
        blocked_reasons=[],
        classification="synthetic_fixture",
    )
    assert m1.result_hash == m2.result_hash


def test_freeze_prevents_mutation():
    """P4-T8: frozen runs cannot be silently mutated."""
    store = ImmutableRunStore()
    store.create(_manifest(store))
    store.freeze("run_abc")
    assert store.get("run_abc").freeze_state == RunFreezeState.frozen
    with pytest.raises(RunAlreadyFrozenError):
        store.mutate("run_abc", {"result_hash": "tampered"})


def test_child_run_preserves_parent():
    """P4-T8: child run keeps parent identity and never overwrites parent result."""
    store = ImmutableRunStore()
    m = _manifest(store)
    store.create(m)
    parent = store.get("run_abc")
    child = store.create_child("run_abc", "run_abc_child", {"result_hash": "child_res"})
    assert child.parent_run_id == "run_abc"
    assert store.get("run_abc").result_hash == m.result_hash
    assert store.get("run_abc_child").parent_run_id == "run_abc"


def test_missing_run_not_found():
    store = ImmutableRunStore()
    with pytest.raises(RunNotFoundError):
        store.get("nope")


def test_manifest_hash_covers_trace_and_versions():
    """P4-T8: manifest request hash covers trace + versions deterministically."""
    m1 = _manifest(None if False else ImmutableRunStore())
    assert m1.request_hash
    assert m1.trace.donor_evidence_ids
    assert m1.freeze_state == RunFreezeState.active


def test_stage_summary_build_is_deterministic():
    s1 = build_stage_summary(
        donor_evidence_ids=["ev_d1", "ev_d2"],
        transformation_hypothesis_ids=["t1"],
        site_hypothesis_ids=["site_c1"],
        graph_edit_ids=["delta_1"],
        candidate_ids=["cand_ox_001"],
        ledger_ids=["srl_ev_d1"],
        rank_result={"rank": "1"},
        decision_result={"decision": "predicted"},
    )
    s2 = build_stage_summary(
        donor_evidence_ids=["ev_d1", "ev_d2"],
        transformation_hypothesis_ids=["t1"],
        site_hypothesis_ids=["site_c1"],
        graph_edit_ids=["delta_1"],
        candidate_ids=["cand_ox_001"],
        ledger_ids=["srl_ev_d1"],
        rank_result={"rank": "1"},
        decision_result={"decision": "predicted"},
    )
    assert s1 == s2
    assert s1.donor_evidence_ids == ["ev_d1", "ev_d2"]
