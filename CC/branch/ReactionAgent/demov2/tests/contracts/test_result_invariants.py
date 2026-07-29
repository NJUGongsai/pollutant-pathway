"""ADR-0005: PredictionResult state machine tests.

Complete cross-field invariant coverage for all 4 states.
"""

import pytest
from pydantic import ValidationError
from reaction_agent.schemas import (
    PredictionResult,
    ResultStatus,
    DecisionKind,
    Candidate,
    Lane,
    ScientificAbstentionReason,
    SystemFailureReason,
)
from reaction_agent.schemas.result import Abstention, Failure


def _c(cid="c1"):
    return Candidate(
        candidate_id=cid, canonical_product="CCCC=O",
        lane=Lane.strict, origin="agent_selected_from_evidence_space",
    )


# -- completed --

@pytest.mark.contract
def test_completed_positive():
    r = PredictionResult(
        run_id="r1", status=ResultStatus.completed,
        decision=DecisionKind.predicted,
        normalized_query="CCCCO", snapshot_id="s1",
        candidates=[_c()],
    )
    assert r.status == ResultStatus.completed


@pytest.mark.contract
def test_completed_zero_candidates_rejected():
    with pytest.raises(ValidationError, match="at least 1 candidate"):
        PredictionResult(
            run_id="r1", status=ResultStatus.completed,
            decision=DecisionKind.predicted,
            normalized_query="CCCCO", snapshot_id="s1",
            candidates=[],
        )


@pytest.mark.contract
def test_completed_with_abstention_rejected():
    with pytest.raises(ValidationError, match="must not have abstention"):
        PredictionResult(
            run_id="r1", status=ResultStatus.completed,
            decision=DecisionKind.predicted,
            normalized_query="CCCCO", snapshot_id="s1",
            candidates=[_c()],
            abstention=Abstention(reason_code=ScientificAbstentionReason.INSUFFICIENT_SUPPORT),
        )


@pytest.mark.contract
def test_completed_with_failure_rejected():
    with pytest.raises(ValidationError, match="must not have failure"):
        PredictionResult(
            run_id="r1", status=ResultStatus.completed,
            decision=DecisionKind.predicted,
            normalized_query="CCCCO", snapshot_id="s1",
            candidates=[_c()],
            failure=Failure(reason_code=SystemFailureReason.STORAGE_FAILURE),
        )


@pytest.mark.contract
def test_completed_with_partial_reason_rejected():
    with pytest.raises(ValidationError, match="must not have partial_reason"):
        PredictionResult(
            run_id="r1", status=ResultStatus.completed,
            decision=DecisionKind.predicted,
            normalized_query="CCCCO", snapshot_id="s1",
            candidates=[_c()], partial_reason="reason",
        )


# -- abstained --

@pytest.mark.contract
def test_abstained_positive():
    r = PredictionResult(
        run_id="r1", status=ResultStatus.abstained,
        decision=DecisionKind.abstained,
        normalized_query="CCCCO", snapshot_id="s1",
        candidates=[],
        abstention=Abstention(reason_code=ScientificAbstentionReason.NO_IN_DOMAIN_DONOR),
    )
    assert r.status == ResultStatus.abstained


@pytest.mark.contract
def test_abstained_with_candidates_rejected():
    with pytest.raises(ValidationError, match="0 candidates"):
        PredictionResult(
            run_id="r1", status=ResultStatus.abstained,
            decision=DecisionKind.abstained,
            normalized_query="CCCCO", snapshot_id="s1",
            candidates=[_c()],
            abstention=Abstention(reason_code=ScientificAbstentionReason.NO_IN_DOMAIN_DONOR),
        )


@pytest.mark.contract
def test_abstained_without_reason_rejected():
    with pytest.raises(ValidationError):
        PredictionResult(
            run_id="r1", status=ResultStatus.abstained,
            decision=DecisionKind.abstained,
            normalized_query="CCCCO", snapshot_id="s1",
            candidates=[],
        )


@pytest.mark.contract
def test_abstained_with_system_failure_reason_rejected():
    with pytest.raises(ValidationError):
        Abstention(reason_code="SNAPSHOT_UNAVAILABLE")


@pytest.mark.contract
def test_abstained_with_failure_rejected():
    with pytest.raises(ValidationError, match="must not have failure"):
        PredictionResult(
            run_id="r1", status=ResultStatus.abstained,
            decision=DecisionKind.abstained,
            normalized_query="CCCCO", snapshot_id="s1",
            candidates=[],
            abstention=Abstention(reason_code=ScientificAbstentionReason.NO_IN_DOMAIN_DONOR),
            failure=Failure(reason_code=SystemFailureReason.STORAGE_FAILURE),
        )


@pytest.mark.contract
def test_abstained_with_partial_reason_rejected():
    with pytest.raises(ValidationError, match="must not have partial_reason"):
        PredictionResult(
            run_id="r1", status=ResultStatus.abstained,
            decision=DecisionKind.abstained,
            normalized_query="CCCCO", snapshot_id="s1",
            candidates=[],
            abstention=Abstention(reason_code=ScientificAbstentionReason.NO_IN_DOMAIN_DONOR),
            partial_reason="reason",
        )


@pytest.mark.contract
def test_abstained_with_decision_predicted_rejected():
    with pytest.raises(ValidationError, match="requires decision=abstained"):
        PredictionResult(
            run_id="r1", status=ResultStatus.abstained,
            decision=DecisionKind.predicted,
            normalized_query="CCCCO", snapshot_id="s1",
            candidates=[],
            abstention=Abstention(reason_code=ScientificAbstentionReason.NO_IN_DOMAIN_DONOR),
        )


# -- partial --

@pytest.mark.contract
def test_partial_positive():
    r = PredictionResult(
        run_id="r1", status=ResultStatus.partial,
        decision=DecisionKind.partial,
        normalized_query="CCCCO", snapshot_id="s1",
        partial_reason="only generalized candidates",
    )
    assert r.status == ResultStatus.partial


@pytest.mark.contract
def test_partial_without_reason_rejected():
    with pytest.raises(ValidationError, match="partial_reason"):
        PredictionResult(
            run_id="r1", status=ResultStatus.partial,
            decision=DecisionKind.partial,
            normalized_query="CCCCO", snapshot_id="s1",
        )


@pytest.mark.contract
def test_partial_with_failure_rejected():
    with pytest.raises(ValidationError, match="must not have failure"):
        PredictionResult(
            run_id="r1", status=ResultStatus.partial,
            decision=DecisionKind.partial,
            normalized_query="CCCCO", snapshot_id="s1",
            partial_reason="reason",
            failure=Failure(reason_code=SystemFailureReason.STORAGE_FAILURE),
        )


@pytest.mark.contract
def test_partial_with_decision_predicted_rejected():
    with pytest.raises(ValidationError, match="requires decision=partial"):
        PredictionResult(
            run_id="r1", status=ResultStatus.partial,
            decision=DecisionKind.predicted,
            normalized_query="CCCCO", snapshot_id="s1",
            partial_reason="reason",
        )


# -- failed --

@pytest.mark.contract
def test_failed_positive():
    r = PredictionResult(
        run_id="r1", status=ResultStatus.failed,
        decision=DecisionKind.failed,
        normalized_query="CCCCO", snapshot_id="s1",
        failure=Failure(reason_code=SystemFailureReason.SNAPSHOT_UNAVAILABLE),
    )
    assert r.status == ResultStatus.failed


@pytest.mark.contract
def test_failed_without_failure_rejected():
    with pytest.raises(ValidationError, match="requires failure"):
        PredictionResult(
            run_id="r1", status=ResultStatus.failed,
            decision=DecisionKind.failed,
            normalized_query="CCCCO", snapshot_id="s1",
        )


@pytest.mark.contract
def test_failed_with_scientific_reason_rejected():
    with pytest.raises(ValidationError):
        Failure(reason_code="NO_IN_DOMAIN_DONOR")


@pytest.mark.contract
def test_failed_with_scientific_abstention_rejected():
    with pytest.raises(ValidationError, match="must not have scientific abstention"):
        PredictionResult(
            run_id="r1", status=ResultStatus.failed,
            decision=DecisionKind.failed,
            normalized_query="CCCCO", snapshot_id="s1",
            failure=Failure(reason_code=SystemFailureReason.STORAGE_FAILURE),
            abstention=Abstention(reason_code=ScientificAbstentionReason.NO_IN_DOMAIN_DONOR),
        )


@pytest.mark.contract
def test_failed_with_decision_abstained_rejected():
    with pytest.raises(ValidationError, match="requires decision=failed"):
        PredictionResult(
            run_id="r1", status=ResultStatus.failed,
            decision=DecisionKind.abstained,
            normalized_query="CCCCO", snapshot_id="s1",
            failure=Failure(reason_code=SystemFailureReason.STORAGE_FAILURE),
        )


# -- No qualitative confidence field --

@pytest.mark.contract
def test_no_confidence_field_in_result():
    schema = PredictionResult.model_json_schema()
    props = schema.get("properties", {})
    assert "confidence" not in props
    assert "qualitative_confidence" not in props
    assert "biological_probability" not in props
