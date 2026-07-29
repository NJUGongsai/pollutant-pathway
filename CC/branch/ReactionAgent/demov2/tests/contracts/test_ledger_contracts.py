"""ADR-0003: Ledger and mapping/mechanism contract tests.

Tests formal vs mechanistic separation, dual ledger boundaries,
typed skeleton enforcement.
"""

import pytest
from pydantic import ValidationError
from reaction_agent.schemas import (
    MappingReport,
    MappingStatus,
    FormalSourceAssignment,
    MechanisticAtomOrigin,
    SourceAssignmentMethod,
    SourceReactionLedger,
    CandidateAnalogyLedger,
    LedgerBalanceStatus,
    RoleAssignment,
    StoichiometricEntry,
    FormalAtomTransferAssignment,
    ElementBalance,
    ParticipantRole,
)


# -- Formal ≠ Mechanistic --

@pytest.mark.contract
def test_formal_mapping_without_mechanism_passes():
    mr = MappingReport(
        mapper_name="rxnmapper", mapper_version="1.0",
        input_hash="abc", output_hash="def",
        mapping_status=MappingStatus.fully_mapped,
        mapped_heavy_atom_fraction=1.0,
        map_number_uniqueness=True,
        changed_atom_coverage=1.0,
    )
    assert mr.mechanistic_atom_origin is None


@pytest.mark.contract
def test_mechanism_without_evidence_ids_rejected():
    with pytest.raises(ValidationError, match="at least 1 evidence ID"):
        MechanisticAtomOrigin(evidence_ids=[], evidence_type="isotope_tracing")


@pytest.mark.contract
def test_mechanism_with_evidence_ids_passes():
    mo = MechanisticAtomOrigin(
        evidence_ids=["isotope_study_001"],
        evidence_type="isotope_tracing",
    )
    assert len(mo.evidence_ids) == 1


@pytest.mark.contract
def test_mechanistic_origin_with_full_report():
    mr = MappingReport(
        mapper_name="curated", mapper_version="1.0",
        input_hash="abc", output_hash="def",
        mapping_status=MappingStatus.fully_mapped,
        mapped_heavy_atom_fraction=1.0,
        map_number_uniqueness=True,
        changed_atom_coverage=1.0,
        mechanistic_atom_origin=MechanisticAtomOrigin(
            evidence_ids=["ev1"], evidence_type="isotope_tracing",
        ),
    )
    assert mr.mechanistic_atom_origin is not None


@pytest.mark.contract
def test_mapping_report_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        MappingReport(
            mapper_name="test", mapper_version="1.0",
            input_hash="abc", output_hash="def",
            mapping_status=MappingStatus.fully_mapped,
            mapped_heavy_atom_fraction=1.0,
            map_number_uniqueness=True,
            changed_atom_coverage=1.0,
            unknown_mapping_field="bad",
        )


# -- Source vs Candidate Ledger separation --

@pytest.mark.contract
def test_source_ledger_typed_skeleton():
    sl = SourceReactionLedger(
        ledger_id="sl1",
        reaction_evidence_id="rxn1",
        balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
        role_assignments=[
            RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_substrate),
        ],
        element_balance=[
            ElementBalance(element="C", reactant_count=8, product_count=8, delta=0),
        ],
    )
    assert len(sl.role_assignments) == 1


@pytest.mark.contract
def test_candidate_ledger_requires_source_linkage():
    cl = CandidateAnalogyLedger(
        ledger_id="cl1",
        source_ledger_id="sl1",
        candidate_id="c1",
    )
    assert cl.source_ledger_id == "sl1"


@pytest.mark.contract
def test_candidate_ledger_rejects_missing_source_linkage():
    with pytest.raises(ValidationError):
        CandidateAnalogyLedger(
            ledger_id="cl1",
            candidate_id="c1",
        )


@pytest.mark.contract
def test_source_ledger_rejects_candidate_fields():
    with pytest.raises(ValidationError):
        SourceReactionLedger(
            ledger_id="sl1",
            reaction_evidence_id="rxn1",
            balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
            candidate_id="c1",
        )


@pytest.mark.contract
def test_candidate_ledger_rejects_source_fields():
    with pytest.raises(ValidationError):
        CandidateAnalogyLedger(
            ledger_id="cl1",
            source_ledger_id="sl1",
            candidate_id="c1",
            reaction_evidence_id="rxn1",
        )


@pytest.mark.contract
def test_source_ledger_preserves_unknowns():
    sl = SourceReactionLedger(
        ledger_id="sl1",
        reaction_evidence_id="rxn1",
        balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        unknowns=["cofactor_stoichiometry_unknown"],
    )
    assert len(sl.unknowns) == 1


# -- Typed nested skeletons reject unknown fields --

@pytest.mark.contract
def test_role_assignment_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        RoleAssignment(
            participant_id="p1",
            role=ParticipantRole.transformed_substrate,
            unknown_field="bad",
        )


@pytest.mark.contract
def test_element_balance_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        ElementBalance(
            element="C",
            reactant_count=8,
            product_count=8,
            delta=0,
            unknown_field="bad",
        )
