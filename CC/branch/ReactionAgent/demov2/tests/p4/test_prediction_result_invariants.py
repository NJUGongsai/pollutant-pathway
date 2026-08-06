"""P4-T7 PredictionResult invariants via adapter (never synonymous schema)."""
from __future__ import annotations

import pytest

from tests.fixtures.p4.p4_contract_fixture import (
    build_evidence_records,
    build_strict_candidate,
    build_structural_context,
    POLICY_VERSION,
)
from reaction_agent.schemas.common import (
    ResultStatus,
    DecisionKind,
    SystemFailureReason,
    ScientificAbstentionReason,
)
from reaction_agent.schemas.result import PredictionResult, Abstention, Failure
from reaction_agent.schemas.candidate import Candidate
from reaction_agent.schemas.p4.decision import (
    PredictionDecision,
    AbstentionDecision,
)
from reaction_agent.schemas.p4.ranking import RankedStrictCandidate
from reaction_agent.schemas.p4.applicability import ApplicabilityAssessment, ApplicabilityReasonCode
from reaction_agent.schemas.common import ApplicabilityLabel
from reaction_agent.schemas.result import StageSummary
from reaction_agent.adapters.prediction_result_adapter import (
    PredictionResultAdapter,
    DecisionAuthorityError,
)


def _ranked() -> RankedStrictCandidate:
    c = build_strict_candidate()
    return RankedStrictCandidate(
        candidate_id=c.candidate_id,
        canonical_product=c.canonical_product,
        lane=c.lane,
        ranking_score=0.8,
        rank=1,
        contributions=[],
        tie_break_key="tb",
        ranker_version="p4-ranker-1",
    )


def _appl() -> ApplicabilityAssessment:
    return ApplicabilityAssessment(
        candidate_id="cand_ox_001",
        label=ApplicabilityLabel.in_domain,
        reason_codes=[ApplicabilityReasonCode.IN_DOMAIN_DONOR],
        evidence_ids=["ev_d1"],
        policy_version=POLICY_VERSION,
        assessment_hash="h",
    )


def _completed_decision() -> PredictionDecision:
    return PredictionDecision(
        decision=DecisionKind.predicted,
        status=ResultStatus.completed,
        ranked_candidates=[_ranked()],
        applicability=_appl(),
        policy_version=POLICY_VERSION,
    )


def test_completed_requires_at_least_one_valid_strict_candidate():
    """P4-T7: completed => >=1 validated strict candidate, no abstention."""
    adapter = PredictionResultAdapter(policy_version=POLICY_VERSION)
    cand = build_strict_candidate()
    result = adapter.validate_and_build(
        _completed_decision(), candidate_map={cand.candidate_id: cand})
    assert isinstance(result, PredictionResult)
    assert result.status == ResultStatus.completed
    assert result.decision == DecisionKind.predicted
    assert len(result.candidates) >= 1
    assert result.abstention is None
    assert result.failure is None


def test_completed_with_zero_candidates_rejected():
    """P4-T7: completed + 0 candidates => invariant violation."""
    adapter = PredictionResultAdapter(policy_version=POLICY_VERSION)
    decision = _completed_decision()
    decision.ranked_candidates = []
    with pytest.raises(ValueError):
        adapter.validate_and_build(decision)


def test_abstained_requires_reason_and_zero_candidates():
    """P4-T7: abstained => 0 candidates + scientific reason."""
    adapter = PredictionResultAdapter(policy_version=POLICY_VERSION)
    decision = PredictionDecision(
        decision=DecisionKind.abstained,
        status=ResultStatus.abstained,
        abstention=AbstentionDecision(
            reason_code=ScientificAbstentionReason.INSUFFICIENT_SUPPORT,
            primary_reason="INSUFFICIENT_SUPPORT",
            candidate_count=0,
            trace=StageSummary(),
            policy_version=POLICY_VERSION,
            source_evidence_scope="train_only",
        ),
        policy_version=POLICY_VERSION,
    )
    result = adapter.validate_and_build(decision)
    assert result.status == ResultStatus.abstained
    assert len(result.candidates) == 0
    assert result.abstention is not None
    assert result.abstention.reason_code == ScientificAbstentionReason.INSUFFICIENT_SUPPORT


def test_system_failure_not_abstention():
    """P4-T7: system failure must go to failed, never to abstained."""
    adapter = PredictionResultAdapter(policy_version=POLICY_VERSION)
    decision = PredictionDecision(
        decision=DecisionKind.failed,
        status=ResultStatus.failed,
        reason_code=SystemFailureReason.SNAPSHOT_UNAVAILABLE.value,
        policy_version=POLICY_VERSION,
    )
    result = adapter.validate_and_build(decision)
    assert result.status == ResultStatus.failed
    assert result.failure is not None
    assert result.failure.reason_code == SystemFailureReason.SNAPSHOT_UNAVAILABLE
    assert result.abstention is None

    # A caller must not be able to pass a system failure as a scientific abstention.
    bad = PredictionDecision(
        decision=DecisionKind.abstained,
        status=ResultStatus.abstained,
        reason_code=SystemFailureReason.SNAPSHOT_UNAVAILABLE.value,
        abstention=AbstentionDecision(
            reason_code=ScientificAbstentionReason.INVALID_INPUT,
            primary_reason="INVALID_INPUT",
            candidate_count=0,
            trace=StageSummary(),
            policy_version=POLICY_VERSION,
            source_evidence_scope="x",
        ),
        policy_version=POLICY_VERSION,
    )
    with pytest.raises((ValueError, DecisionAuthorityError)):
        adapter.validate_and_build(bad)


def test_agent_text_cannot_override_structured_decision():
    """P4-T7: agent text may explain but never override status/reason/rank."""
    adapter = PredictionResultAdapter(policy_version=POLICY_VERSION)
    decision = _completed_decision()
    with pytest.raises(DecisionAuthorityError):
        adapter.validate_and_build(decision, agent_text={
            "status": "abstained",
            "reason_code": ScientificAbstentionReason.OUT_OF_DOMAIN.value,
        })


def test_probability_fields_rejected_by_schema():
    """P4-T7: injecting forbidden probability/confidence names must fail."""
    adapter = PredictionResultAdapter(policy_version=POLICY_VERSION)
    decision = _completed_decision()
    with pytest.raises(Exception):
        adapter.validate_and_build(decision, extra_structured={
            "confidence": 0.9,
            "enzyme_activity_probability": 0.7,
        })


def test_prediction_result_is_shared_schema_not_synonym():
    """P4-T7: we reuse P1 PredictionResult, we do not define a duplicate."""
    assert PredictionResult.__module__ == "reaction_agent.schemas.result"
    assert not hasattr(PredictionResult, "confidence")
