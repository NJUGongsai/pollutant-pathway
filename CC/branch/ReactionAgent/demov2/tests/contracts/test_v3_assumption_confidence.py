"""V3 remediation: donor assumption, confidence bypass, canonical exception.

Section 8: InheritedDonorContext.is_assumption must be Literal[True].
Section 9: confidence_note bypass must be removed; replaced by controlled enum.
Section 14: UnknownReferenceError must be canonical (schemas.errors).

Negative cases (Section 19 #10, #11, #17).
"""

import pytest

from pydantic import ValidationError

from reaction_agent.schemas import (
    AdaptationVerificationStatus,
    InheritedDonorContext,
    QueryCandidateAdaptation,
    UnknownReferenceError,
    ContractViolation,
)
import reaction_agent.schemas.hypothesis as hypothesis_module
import reaction_agent.schemas.errors as errors_module


# -- Section 19 #10: InheritedDonorContext(is_assumption=False) --

@pytest.mark.contract
def test_inherited_donor_context_is_assumption_false_rejected():
    """is_assumption=False must be rejected — donor context is always an assumption."""
    with pytest.raises(ValidationError, match="is_assumption"):
        InheritedDonorContext(
            donor_reaction_id="rxn1",
            donor_participant_id="p1",
            is_assumption=False,
        )


@pytest.mark.contract
def test_inherited_donor_context_is_assumption_true_accepted():
    """Default is_assumption=True must be accepted."""
    ctx = InheritedDonorContext(
        donor_reaction_id="rxn1",
        donor_participant_id="p1",
    )
    assert ctx.is_assumption is True


@pytest.mark.contract
def test_inherited_donor_context_serializes_assumption_true():
    """Serialization must explicitly output is_assumption=true."""
    ctx = InheritedDonorContext(
        donor_reaction_id="rxn1",
        donor_participant_id="p1",
    )
    assert ctx.model_dump()["is_assumption"] is True


@pytest.mark.contract
def test_inherited_donor_context_explicit_true_accepted():
    """Explicit is_assumption=True must be accepted."""
    ctx = InheritedDonorContext(
        donor_reaction_id="rxn1",
        donor_participant_id="p1",
        is_assumption=True,
    )
    assert ctx.is_assumption is True


# -- Section 19 #11: confidence_note bypass removed --

@pytest.mark.contract
def test_query_candidate_adaptation_no_confidence_note_field():
    """confidence_note field must be removed from QueryCandidateAdaptation."""
    props = QueryCandidateAdaptation.model_json_schema().get("properties", {})
    assert "confidence_note" not in props, (
        "QueryCandidateAdaptation still has forbidden 'confidence_note' field"
    )


@pytest.mark.contract
def test_query_candidate_adaptation_rejects_confidence_note_input():
    """Passing confidence_note must be rejected (field removed, extra=forbid)."""
    with pytest.raises(ValidationError):
        QueryCandidateAdaptation(
            donor_participant_id="p1",
            confidence_note="high confidence",
        )


@pytest.mark.contract
def test_query_candidate_adaptation_has_verification_status_enum():
    """A controlled adaptation_verification_status enum must replace confidence_note."""
    props = QueryCandidateAdaptation.model_json_schema().get("properties", {})
    assert "adaptation_verification_status" in props, (
        "QueryCandidateAdaptation missing adaptation_verification_status enum"
    )


@pytest.mark.contract
def test_query_candidate_adaptation_verification_status_is_controlled():
    """The enum must NOT accept arbitrary high/medium/low confidence text."""
    with pytest.raises(ValidationError):
        QueryCandidateAdaptation(
            donor_participant_id="p1",
            adaptation_verification_status="high confidence",
        )


@pytest.mark.contract
def test_query_candidate_adaptation_verification_status_accepts_controlled_values():
    """Controlled enum values must be accepted."""
    for value in (
        AdaptationVerificationStatus.unverified_analogy,
        AdaptationVerificationStatus.formally_mapped,
        AdaptationVerificationStatus.evidence_supported,
    ):
        qca = QueryCandidateAdaptation(
            donor_participant_id="p1",
            adaptation_verification_status=value,
        )
        assert qca.adaptation_verification_status == value


@pytest.mark.contract
def test_query_candidate_adaptation_no_confidence_keyword_in_schema():
    """No property name may contain 'confidence' in QueryCandidateAdaptation."""
    props = QueryCandidateAdaptation.model_json_schema().get("properties", {})
    for name in props:
        assert "confidence" not in name.lower(), (
            f"QueryCandidateAdaptation has confidence-bearing field: {name}"
        )


# -- Section 19 #17: canonical UnknownReferenceError --

@pytest.mark.contract
def test_exported_unknown_reference_error_is_canonical():
    """reaction_agent.schemas.UnknownReferenceError must be the canonical
    schemas.errors class (not a duplicate defined in hypothesis.py)."""
    assert UnknownReferenceError is errors_module.UnknownReferenceError


@pytest.mark.contract
def test_unknown_reference_error_inherits_contract_violation():
    """UnknownReferenceError must inherit ContractViolation."""
    assert issubclass(UnknownReferenceError, ContractViolation)


@pytest.mark.contract
def test_hypothesis_module_uses_canonical_unknown_reference_error():
    """hypothesis.py must NOT define its own UnknownReferenceError; it must
    use the canonical class from schemas.errors."""
    assert hypothesis_module.UnknownReferenceError is errors_module.UnknownReferenceError
