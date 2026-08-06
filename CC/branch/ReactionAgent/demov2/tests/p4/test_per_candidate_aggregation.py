"""P4-R1-H RED→GREEN: per-candidate decision aggregation.

A weak/out-of-domain/conflicted candidate is moved OUT of the production
ranking (with trace) — it must NOT abort the whole candidate set. As long as
at least one verified strict candidate passes the policy, the eligible subset
is ranked and the run completes. Only when the eligible set is empty does the
pipeline produce a global typed abstention. Candidate-local conflict is
distinct from a global evidence conflict.
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
from reaction_agent.schemas.common import ResultStatus
from reaction_agent.schemas.p4.authority import (
    AuthoritySource,
    P3AuthorityHandle,
    P4Classification,
    RunNamespace,
)
from reaction_agent.inference.predictor import run_p4_pipeline


def _authority() -> P3AuthorityHandle:
    return P3AuthorityHandle(
        source=AuthoritySource.p3_current_run,
        manifest_version="p3-p4-3",
        schema_hash="",
        namespace=RunNamespace(
            run_id="run_abc", case_id="case_1", query_id="q_1",
            fold_id="fold_1", snapshot_id="snap_c589494081df",
            snapshot_hash="deadbeef" * 4, policy_version=POLICY_VERSION),
        evidence_kind=P4Classification.synthetic_fixture,
        blocked_reasons=[],
    )


def _cand2() -> "object":
    c = build_strict_candidate()
    return c.model_copy(update={"candidate_id": "cand_ox_002"})


def _weak_ctx() -> dict:
    """Structural context that yields NO support (all zero ordinals)."""
    return {
        "donor_similarity": 0, "transform_support": 0, "site_compatibility": 0,
        "mapping_lineage_quality": 0, "source_quality": 0,
        "ledger_completeness": 0, "retrieval_stability": 0,
    }


def _conflicted_ctx() -> dict:
    ctx = build_structural_context()
    ctx["competing_transform"] = ["t2"]
    return ctx


class TestPerCandidateAggregation:
    def test_strong_plus_weak_completes_with_strong_only(self):
        """candidate A strong + candidate B weak => completed with A only."""
        strong = build_strict_candidate()
        weak = _cand2()
        outcome = run_p4_pipeline(
            query=build_query(),
            evidence_records=build_evidence_records(),
            candidates=[strong, weak],
            structural_contexts={
                strong.candidate_id: build_structural_context(),
                weak.candidate_id: _weak_ctx(),
            },
            authority=_authority(),
            top_k=3,
            feature_evidence_ids={
                strong.candidate_id: build_feature_evidence_binding(),
                weak.candidate_id: build_feature_evidence_binding(),
            },
        )
        result = outcome.build_prediction_result()
        assert result.status == ResultStatus.completed
        ids = [c.candidate_id for c in result.candidates]
        assert strong.candidate_id in ids
        assert weak.candidate_id not in ids, "weak candidate must be removed"

    def test_two_strong_completes_with_both(self):
        """Two strong candidates both rank and complete."""
        strong = build_strict_candidate()
        strong2 = _cand2()
        outcome = run_p4_pipeline(
            query=build_query(),
            evidence_records=build_evidence_records(),
            candidates=[strong, strong2],
            structural_contexts={
                strong.candidate_id: build_structural_context(),
                strong2.candidate_id: build_structural_context(),
            },
            authority=_authority(),
            top_k=3,
            feature_evidence_ids={
                strong.candidate_id: build_feature_evidence_binding(),
                strong2.candidate_id: build_feature_evidence_binding(),
            },
        )
        result = outcome.build_prediction_result()
        assert result.status == ResultStatus.completed
        assert len(result.candidates) == 2

    def test_good_plus_conflicted_completes_with_good_only(self):
        """A candidate-local conflict removes that candidate, not the set."""
        good = build_strict_candidate()
        conflicted = _cand2()
        outcome = run_p4_pipeline(
            query=build_query(),
            evidence_records=build_evidence_records(),
            candidates=[good, conflicted],
            structural_contexts={
                good.candidate_id: build_structural_context(),
                conflicted.candidate_id: _conflicted_ctx(),
            },
            authority=_authority(),
            top_k=3,
            feature_evidence_ids={
                good.candidate_id: build_feature_evidence_binding(),
                conflicted.candidate_id: build_feature_evidence_binding(),
            },
        )
        result = outcome.build_prediction_result()
        assert result.status == ResultStatus.completed
        ids = [c.candidate_id for c in result.candidates]
        assert good.candidate_id in ids
        assert conflicted.candidate_id not in ids

    def test_all_weak_abstains_insufficient_support(self):
        """All candidates weak => global INSUFFICIENT_SUPPORT abstention."""
        weak = build_strict_candidate()
        weak2 = _cand2()
        outcome = run_p4_pipeline(
            query=build_query(),
            evidence_records=build_evidence_records(),
            candidates=[weak, weak2],
            structural_contexts={
                weak.candidate_id: _weak_ctx(),
                weak2.candidate_id: _weak_ctx(),
            },
            authority=_authority(),
            top_k=3,
            feature_evidence_ids={
                weak.candidate_id: build_feature_evidence_binding(),
                weak2.candidate_id: build_feature_evidence_binding(),
            },
        )
        result = outcome.build_prediction_result()
        assert result.status == ResultStatus.abstained
        assert result.abstention.reason_code.value == "INSUFFICIENT_SUPPORT"

    def test_all_out_of_domain_abstains_out_of_domain(self):
        """All candidates out-of-domain => global OUT_OF_DOMAIN abstention."""
        ood = build_strict_candidate()
        ood2 = _cand2()
        ood_ctx = dict(build_structural_context(), donor_similarity=0,
                       transform_support=0, site_compatibility=0)
        outcome = run_p4_pipeline(
            query=build_query(),
            evidence_records=build_evidence_records(),
            candidates=[ood, ood2],
            structural_contexts={
                ood.candidate_id: ood_ctx,
                ood2.candidate_id: ood_ctx,
            },
            authority=_authority(),
            top_k=3,
            feature_evidence_ids={
                ood.candidate_id: build_feature_evidence_binding(),
                ood2.candidate_id: build_feature_evidence_binding(),
            },
        )
        result = outcome.build_prediction_result()
        assert result.status == ResultStatus.abstained
        assert result.abstention.reason_code.value == "OUT_OF_DOMAIN"

    def test_candidate_permutation_does_not_change_result(self):
        """Input candidate order must not change the outcome."""
        a = build_strict_candidate()
        b = _cand2()
        run1 = run_p4_pipeline(
            query=build_query(), evidence_records=build_evidence_records(),
            candidates=[a, b],
            structural_contexts={
                a.candidate_id: build_structural_context(),
                b.candidate_id: _weak_ctx(),
            },
            authority=_authority(), top_k=3,
            feature_evidence_ids={
                a.candidate_id: build_feature_evidence_binding(),
                b.candidate_id: build_feature_evidence_binding(),
            })
        run2 = run_p4_pipeline(
            query=build_query(), evidence_records=build_evidence_records(),
            candidates=[b, a],
            structural_contexts={
                a.candidate_id: build_structural_context(),
                b.candidate_id: _weak_ctx(),
            },
            authority=_authority(), top_k=3,
            feature_evidence_ids={
                a.candidate_id: build_feature_evidence_binding(),
                b.candidate_id: build_feature_evidence_binding(),
            })
        r1 = run1.build_prediction_result()
        r2 = run2.build_prediction_result()
        assert r1.status == r2.status
        assert [c.candidate_id for c in r1.candidates] == \
            [c.candidate_id for c in r2.candidates]
        assert run1.manifest.result_hash == run2.manifest.result_hash