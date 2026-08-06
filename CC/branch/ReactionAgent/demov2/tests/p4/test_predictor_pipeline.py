"""End-to-end P4 predictor pipeline (identity→support→rank→decide)."""
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
from reaction_agent.schemas.common import ResultStatus, SystemFailureReason
from reaction_agent.schemas.result import PredictionResult
from reaction_agent.schemas.p4.authority import (
    AuthoritySource,
    P3AuthorityHandle,
    P4Classification,
    RunNamespace,
)
from reaction_agent.inference.predictor import run_p4_pipeline, PipelineOutcome


def _fei(cand_id="cand_ox_001") -> dict:
    return {cand_id: build_feature_evidence_binding()}


def _authority(evidence_kind: str = "synthetic_fixture",
               blocked: bool = False) -> P3AuthorityHandle:
    """A verified current-run authority over the synthetic fixture, or a
    blocked authority (mirrors the P3 consumer's verified handle)."""
    if blocked:
        return P3AuthorityHandle(
            source=AuthoritySource.blocked,
            manifest_version="p3-p4-3",
            namespace=RunNamespace(
                run_id="unknown", case_id="unknown", query_id="unknown",
                fold_id="unknown", snapshot_id="unknown",
                snapshot_hash="unknown"),
            evidence_kind=P4Classification.blocked,
            blocked_reasons=["p3_interface_manifest_missing"],
        )
    return P3AuthorityHandle(
        source=AuthoritySource.p3_current_run,
        manifest_version="p3-p4-3",
        schema_hash="",
        namespace=RunNamespace(
            run_id="run_abc", case_id="case_1", query_id="q_1",
            fold_id="fold_1", snapshot_id="snap_c589494081df",
            snapshot_hash="deadbeef" * 4,
            policy_version=POLICY_VERSION,
        ),
        evidence_kind=P4Classification(evidence_kind),
        blocked_reasons=[],
    )


def test_completed_pipeline_on_pass_capable_fixture():
    """P4 pipeline: fixture => completed prediction with ranked strict top-K."""
    outcome = run_p4_pipeline(
        query=build_query(),
        evidence_records=build_evidence_records(),
        candidates=[build_strict_candidate()],
        structural_contexts={build_strict_candidate().candidate_id: build_structural_context()},
        authority=_authority(),
        top_k=3,
        feature_evidence_ids=_fei(),
    )
    assert isinstance(outcome, PipelineOutcome)
    result = outcome.build_prediction_result()
    assert isinstance(result, PredictionResult)
    assert result.status == ResultStatus.completed
    assert len(result.candidates) >= 1
    assert result.abstention is None
    assert result.stage_summary is not None
    assert result.stage_summary.donor_evidence_ids
    assert result.stage_summary.candidate_ids


def test_pipeline_never_creates_structures():
    """P4: candidates come from P3 only; P4 adds rank/support, never SMILES."""
    cand = build_strict_candidate()
    outcome = run_p4_pipeline(
        query=build_query(),
        evidence_records=build_evidence_records(),
        candidates=[cand],
        structural_contexts={cand.candidate_id: build_structural_context()},
        authority=_authority(),
        top_k=3,
        feature_evidence_ids=_fei(),
    )
    result = outcome.build_prediction_result()
    for c in result.candidates:
        # canonical_product equals the P3-provided product (no fabrication).
        assert c.canonical_product == cand.canonical_product
        assert c.ranking_score is not None
        assert c.lane.value == "strict"


def test_no_candidates_yields_typed_abstention():
    """P4: zero candidates + insufficient support => INSUFFICIENT_SUPPORT."""
    outcome = run_p4_pipeline(
        query=build_query(),
        evidence_records=build_evidence_records(),
        candidates=[],
        structural_contexts={},
        authority=_authority(),
        top_k=3,
        feature_evidence_ids=_fei(),
    )
    result = outcome.build_prediction_result()
    assert result.status == ResultStatus.abstained
    assert result.abstention is not None
    assert result.abstention.reason_code.value == "INSUFFICIENT_SUPPORT"
    assert len(result.candidates) == 0


def test_system_failure_is_failed_not_abstained():
    """P4: infrastructure failure => failed, never scientific abstention."""
    outcome = run_p4_pipeline(
        query=build_query(),
        evidence_records=[],
        candidates=[],
        structural_contexts={},
        authority=_authority(blocked=True),
        top_k=3,
    )
    result = outcome.build_prediction_result()
    assert result.status == ResultStatus.failed
    assert result.failure is not None
    assert result.failure.reason_code == SystemFailureReason.SNAPSHOT_UNAVAILABLE or \
        result.failure.reason_code.value in {r.value for r in SystemFailureReason}
    assert result.abstention is None


def test_synthetic_only_is_not_pass():
    """P4: synthetic-only fixture classification must not be promoted to real."""
    outcome = run_p4_pipeline(
        query=build_query(),
        evidence_records=build_evidence_records(),
        candidates=[build_strict_candidate()],
        structural_contexts={build_strict_candidate().candidate_id: build_structural_context()},
        authority=_authority(),
        top_k=3,
        feature_evidence_ids=_fei(),
    )
    assert outcome.classification == "synthetic_fixture"
    assert outcome.capability.evidence_kind == P4Classification.synthetic_fixture


def test_trace_is_complete_d_to_a():
    """P4-T8: D/T/S/Δ/Y/L/R/A trace populated end to end."""
    cand = build_strict_candidate()
    outcome = run_p4_pipeline(
        query=build_query(),
        evidence_records=build_evidence_records(),
        candidates=[cand],
        structural_contexts={cand.candidate_id: build_structural_context()},
        authority=_authority(),
        top_k=3,
        feature_evidence_ids=_fei(),
    )
    ts = outcome.manifest.trace
    assert ts.donor_evidence_ids
    assert ts.transformation_hypothesis_ids
    assert ts.site_hypothesis_ids
    assert ts.graph_edit_ids
    assert ts.candidate_ids
    assert ts.ledger_ids
    assert ts.rank_result
    assert ts.decision_result
    # The shipped PredictionResult must also carry R/A (not just the manifest).
    result = outcome.build_prediction_result()
    assert result.stage_summary is not None
    assert result.stage_summary.rank_result, "result trace missing R (ranking)"
    assert result.stage_summary.decision_result, "result trace missing A (decision)"


def test_out_of_domain_query_abstains():
    """P4-T6: structurally out-of-domain query must NOT complete — it must
    return a typed OUT_OF_DOMAIN abstention."""
    cand = build_strict_candidate()
    ctx = build_structural_context()
    ctx = dict(ctx, donor_similarity=0, transform_support=0, site_compatibility=0)
    outcome = run_p4_pipeline(
        query=build_query(),
        evidence_records=build_evidence_records(),
        candidates=[cand],
        structural_contexts={cand.candidate_id: ctx},
        authority=_authority(),
        top_k=3,
        feature_evidence_ids=_fei(),
    )
    result = outcome.build_prediction_result()
    assert result.status == ResultStatus.abstained
    assert result.abstention is not None
    assert result.abstention.reason_code.value == "OUT_OF_DOMAIN"
    assert len(result.candidates) == 0


def test_no_structural_support_is_insufficient():
    """P4-T2: a row count alone (independent evidence) without structural
    grounding must NOT produce a strong tier — it abstains INSUFFICIENT_SUPPORT."""
    cand = build_strict_candidate()
    outcome = run_p4_pipeline(
        query=build_query(),
        evidence_records=build_evidence_records(),
        candidates=[cand],
        structural_contexts={},  # no structural observability
        authority=_authority(),
        top_k=3,
        feature_evidence_ids=_fei(),
    )
    result = outcome.build_prediction_result()
    assert result.status == ResultStatus.abstained
    assert result.abstention is not None
    assert result.abstention.reason_code.value == "INSUFFICIENT_SUPPORT"


def test_applicability_attached_to_ranked_candidate():
    """P4-T5: the completed result carries per-candidate applicability."""
    cand = build_strict_candidate()
    outcome = run_p4_pipeline(
        query=build_query(),
        evidence_records=build_evidence_records(),
        candidates=[cand],
        structural_contexts={cand.candidate_id: build_structural_context()},
        authority=_authority(),
        top_k=3,
        feature_evidence_ids=_fei(),
    )
    result = outcome.build_prediction_result()
    for c in result.candidates:
        assert c.applicability is not None
        assert c.applicability.value in {
            "in_domain", "near_domain", "out_of_domain", "conflicted", "unknown"}