"""P4-R1-D RED→GREEN: cross-case/fold/snapshot/policy/run isolation.

The P4 request, the evidence, the candidates and the authority handle must
all resolve to the SAME frozen RunNamespace. A query claiming a different
case/fold/snapshot/policy, or evidence from a different snapshot, is rejected
fail-closed — never silently merged.
"""
from __future__ import annotations

import pytest

from tests.fixtures.p4.p4_contract_fixture import (
    build_evidence_records,
    build_strict_candidate,
    build_structural_context,
    build_feature_evidence_binding,
    build_query,
    POLICY_VERSION,
)
from reaction_agent.schemas.p4.authority import (
    AuthoritySource,
    P3AuthorityHandle,
    P4Classification,
    RunNamespace,
)
from reaction_agent.inference.predictor import run_p4_pipeline


def _authority(**overrides) -> P3AuthorityHandle:
    ns = dict(
        run_id="run_abc", case_id="case_1", query_id="q_1", fold_id="fold_1",
        snapshot_id="snap_c589494081df", snapshot_hash="deadbeef" * 4,
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


def _run(query=None, evidence=None, authority=None, ctx=None):
    cand = build_strict_candidate()
    return run_p4_pipeline(
        query=query or build_query(),
        evidence_records=evidence or build_evidence_records(),
        candidates=[cand],
        structural_contexts=ctx or {cand.candidate_id: build_structural_context()},
        authority=authority or _authority(),
        top_k=3,
        feature_evidence_ids={
            cand.candidate_id: build_feature_evidence_binding()},
    )


class TestNamespaceIsolation:
    def test_matching_namespace_completes(self):
        """The happy path: request/evidence/authority all in one namespace."""
        outcome = _run()
        assert outcome.decision.status.value == "completed"

    def test_cross_query_id_rejected(self):
        """query 声明 q_2，authority 是 q_1 => fail-closed."""
        q = dict(build_query(), query_id="q_2")
        with pytest.raises(Exception):
            _run(query=q)

    def test_cross_case_id_rejected(self):
        q = dict(build_query(), case_id="case_2")
        with pytest.raises(Exception):
            _run(query=q)

    def test_cross_fold_id_rejected(self):
        q = dict(build_query(), fold_id="fold_2")
        with pytest.raises(Exception):
            _run(query=q)

    def test_cross_snapshot_id_rejected(self):
        q = dict(build_query(), snapshot_id="snap_other_namespace")
        with pytest.raises(Exception):
            _run(query=q)

    def test_snapshot_hash_mismatch_rejected(self):
        q = dict(build_query(), snapshot_hash="cafebabe" * 4)
        with pytest.raises(Exception):
            _run(query=q)

    def test_wrong_policy_version_rejected(self):
        """query 指定错误 policy = 与 authority 绑定不一致 => fail-closed."""
        q = dict(build_query(), policy_version="wrong-policy-version")
        with pytest.raises(Exception):
            _run(query=q)

    def test_evidence_snapshot_mismatch_rejected(self):
        """evidence 来自另一个 snapshot => 拒绝（cross-snapshot smuggling）。"""
        from reaction_agent.schemas.evidence import ReactionEvidence
        records = build_evidence_records()
        bad = []
        for rec in records:
            if isinstance(rec, ReactionEvidence):
                bad.append(rec.model_copy(
                    update={"snapshot_id": "snap_other_namespace"}))
            else:
                bad.append(dict(rec, snapshot_id="snap_other_namespace"))
        with pytest.raises(Exception):
            _run(evidence=bad)

    def test_authority_wrong_snapshot_hash_rejected(self):
        """authority 的 snapshot_hash 与 query 不一致 => 拒绝。"""
        auth = _authority(snapshot_hash="cafebabe" * 4)
        with pytest.raises(Exception):
            _run(authority=auth)

    def test_authority_wrong_policy_rejected(self):
        auth = _authority(policy_version="p4-policy-9")
        with pytest.raises(Exception):
            _run(authority=auth)