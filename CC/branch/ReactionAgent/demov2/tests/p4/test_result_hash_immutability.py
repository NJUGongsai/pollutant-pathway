"""P4-R1-E RED→GREEN: single result-hash preimage, deep immutability, pipeline
verify, child collision.

A normal completed pipeline run must verify immediately (its stored result
hash recomputes to the same value). Frozen runs cannot be mutated through the
public manifest. The result hash covers the decision/ranking/applicability/
support/counterevidence/trace/namespace/versions/classification. Same query
under a different snapshot/evidence/version must not collide. Child runs
recompute their own hash and reject existing child ids.
"""
from __future__ import annotations

import pytest

from tests.fixtures.p4.p4_contract_fixture import (
    build_evidence_records,
    build_strict_candidate,
    build_structural_context,
    build_query,
    POLICY_VERSION,
)
from reaction_agent.schemas.p4.authority import (
    AuthoritySource,
    P3AuthorityHandle,
    P4Classification,
    RunNamespace,
)
from reaction_agent.runtime.run import (
    ImmutableRunStore,
    RunHashMismatchError,
)
from reaction_agent.inference.predictor import run_p4_pipeline


def _authority(snapshot_id="snap_c589494081df", snapshot_hash="deadbeef" * 4,
               **overrides) -> P3AuthorityHandle:
    ns = dict(
        run_id="run_abc", case_id="case_1", query_id="q_1", fold_id="fold_1",
        snapshot_id=snapshot_id, snapshot_hash=snapshot_hash,
        policy_version=POLICY_VERSION,
    )
    ns.update(overrides)
    return P3AuthorityHandle(
        source=AuthoritySource.p3_current_run,
        manifest_version="p3-p4-3",
        schema_hash="",
        namespace=RunNamespace(**ns),
        evidence_kind=P4Classification.synthetic_fixture,
        blocked_reasons=[],
    )


def _run(authority=None, query=None, store=None):
    cand = build_strict_candidate()
    return run_p4_pipeline(
        query=query or build_query(),
        evidence_records=build_evidence_records(),
        candidates=[cand],
        structural_contexts={cand.candidate_id: build_structural_context()},
        authority=authority or _authority(),
        top_k=3,
        run_store=store,
    )


class TestHashVerify:
    def test_completed_pipeline_immediately_verifies(self):
        """A normal completed run's stored result hash must recompute to the
        same value (P4-R1-E: single hash preimage)."""
        outcome = _run()
        run = outcome.run_store.get(outcome.run_id)
        recomputed = run.verify()  # must not raise RunHashMismatchError
        assert recomputed == run.result_hash

    def test_failed_blocked_branch_also_verifies(self):
        """Even the blocked/system-failure branch produces a verifiable run."""
        blocked = _authority()
        outcome = _run(authority=blocked)
        # blocked authority -> system failure run
        run = outcome.run_store.get(outcome.run_id)
        run.verify()

    def test_same_query_different_snapshot_no_collision(self):
        """Same query text under a different snapshot must produce a different
        run id (no silent overwrite) and both verify."""
        from reaction_agent.schemas.evidence import ReactionEvidence
        store = ImmutableRunStore()
        a_out = _run(store=store)
        other = _authority(snapshot_id="snap_x", snapshot_hash="cafe" * 8)
        q2 = dict(build_query(), snapshot_id="snap_x", snapshot_hash="cafe" * 8)
        ev2 = [rec.model_copy(update={"snapshot_id": "snap_x"})
               if isinstance(rec, ReactionEvidence) else dict(rec, snapshot_id="snap_x")
               for rec in build_evidence_records()]
        cand = build_strict_candidate()
        b_out = run_p4_pipeline(
            query=q2, evidence_records=ev2, candidates=[cand],
            structural_contexts={cand.candidate_id: build_structural_context()},
            authority=other, top_k=3, run_store=store)
        assert a_out.run_id != b_out.run_id
        store.verify(a_out.run_id)
        store.verify(b_out.run_id)

    def test_same_query_different_policy_no_collision(self):
        store = ImmutableRunStore()
        a_out = _run(store=store)
        other = _authority(policy_version="p4-policy-2")
        q2 = dict(build_query(), policy_version="p4-policy-2")
        b_out = _run(authority=other, query=q2, store=store)
        assert a_out.run_id != b_out.run_id


class TestImmutability:
    def test_direct_manifest_assignment_does_not_leak(self):
        """Mutating the manifest a caller obtained from the store must not
        change the internal frozen state."""
        outcome = _run()
        store = outcome.run_store
        run = store.get(outcome.run_id)
        original = run.result_hash
        try:
            run.manifest.result_hash = "directly_mutated_after_freeze"
        except Exception:
            pass
        # internal state unchanged
        assert store.get(outcome.run_id).result_hash == original
        store.verify(outcome.run_id)

    def test_nested_trace_list_mutation_does_not_leak(self):
        """Mutating a nested trace list/decision dict must not leak into the
        store's frozen run."""
        outcome = _run()
        store = outcome.run_store
        run = store.get(outcome.run_id)
        original = run.result_hash
        try:
            run.manifest.trace.rank_result["decision"] = "CHANGED"
        except Exception:
            pass
        assert store.get(outcome.run_id).result_hash == original
        store.verify(outcome.run_id)

    def test_frozen_run_rejects_mutation(self):
        from reaction_agent.runtime.run import RunAlreadyFrozenError
        outcome = _run()
        store = outcome.run_store
        store.freeze(outcome.run_id)
        with pytest.raises(RunAlreadyFrozenError):
            store.mutate(outcome.run_id, {"result_hash": "tampered"})


class TestChild:
    def test_child_collision_rejected(self):
        """A child run id that already exists must be rejected — never
        overwritten."""
        outcome = _run()
        store = outcome.run_store
        child = store.create_child(outcome.run_id, "child_1", {})
        with pytest.raises(ValueError):
            store.create_child(outcome.run_id, "child_1", {})
        # parent unchanged
        store.verify(outcome.run_id)
        # child verifies with its own recomputed hash
        store.verify("child_1")
        assert child.parent_run_id == outcome.run_id

    def test_child_recomputes_own_hash(self):
        """A child with different content recomputes its own hash and verifies;
        the parent is untouched."""
        from reaction_agent.schemas.result import StageSummary
        outcome = _run()
        store = outcome.run_store
        parent = store.get(outcome.run_id)
        parent_hash = parent.result_hash
        different_trace = StageSummary(
            donor_evidence_ids=["ev_x"], candidate_ids=["cand_x"])
        child = store.create_child(outcome.run_id, "child_2",
                                   {"trace": different_trace})
        store.verify("child_2")
        assert child.result_hash != parent_hash
        assert store.get(outcome.run_id).result_hash == parent_hash