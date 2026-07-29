"""ADR-0004: Partial eligibility — tests import from formal policy artifact."""

import pytest
from reaction_agent.policies.partial_eligibility import (
    ELIGIBILITY_MATRIX,
    EXPECTED_STATES,
    get_row,
    validate_matrix_integrity,
    EligibilityMatrixRow,
)
from reaction_agent.schemas.common import (
    EligibilityStatus,
    EvaluationBucket,
    QuarantineBehavior,
)


@pytest.mark.contract
def test_matrix_has_eight_rows():
    assert len(ELIGIBILITY_MATRIX) == 8


@pytest.mark.contract
def test_matrix_no_duplicate_states():
    states = [row.state for row in ELIGIBILITY_MATRIX]
    assert len(states) == len(set(states))


@pytest.mark.contract
def test_matrix_all_expected_states_present():
    expected = {
        "fully_balanced_reliable_mapping",
        "heavy_atom_balanced_implicit_he",
        "missing_noncritical_cofactor_stoich",
        "unknown_changed_heavy_atom_source",
        "critical_element_charge_contradiction",
        "role_ambiguity_not_affecting_lineage",
        "lineage_ambiguity_affecting_identity",
        "reaction_direction_unknown",
    }
    actual = {row.state for row in ELIGIBILITY_MATRIX}
    assert expected == actual, f"Missing: {expected - actual}, Extra: {actual - expected}"


@pytest.mark.contract
def test_matrix_integrity():
    issues = validate_matrix_integrity()
    assert issues == [], f"Matrix integrity issues: {issues}"


@pytest.mark.contract
def test_strict_prohibited_not_in_production():
    for row in ELIGIBILITY_MATRIX:
        if row.strict_eligibility == EligibilityStatus.strict_prohibited:
            assert row.evaluation_bucket != EvaluationBucket.production


@pytest.mark.contract
def test_quarantine_goes_to_excluded():
    for row in ELIGIBILITY_MATRIX:
        if row.strict_eligibility == EligibilityStatus.quarantine:
            assert row.evaluation_bucket == EvaluationBucket.excluded
            assert row.quarantine_behavior == QuarantineBehavior.quarantined


@pytest.mark.contract
def test_conditional_eligible_has_required_warnings():
    for row in ELIGIBILITY_MATRIX:
        if row.strict_eligibility == EligibilityStatus.conditional_eligible:
            assert len(row.required_warnings) > 0


@pytest.mark.contract
def test_get_row_returns_correct_row():
    row = get_row("fully_balanced_reliable_mapping")
    assert row is not None
    assert row.strict_eligibility == EligibilityStatus.strict_eligible


@pytest.mark.contract
def test_get_row_returns_none_for_unknown():
    assert get_row("nonexistent_state") is None


@pytest.mark.contract
def test_all_rows_are_typed_models():
    for row in ELIGIBILITY_MATRIX:
        assert isinstance(row, EligibilityMatrixRow)
