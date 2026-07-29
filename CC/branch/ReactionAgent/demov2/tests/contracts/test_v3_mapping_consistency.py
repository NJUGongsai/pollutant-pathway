"""V3 remediation: MappingReport consistency, typed pairs, unbound evidence.

Section 10: typed object and flat fields must be consistent (no dual truth source).
Section 11: mapped/mechanistic atom pairs must be typed skeletons, not arbitrary dict.
Section 12: unbound mechanistic evidence is prohibited (ADR-0003 decision: forbid).

Negative cases (Section 19 #12-#16).
"""

import pytest

from pydantic import ValidationError

from reaction_agent.schemas import (
    MappingReport,
    MappingStatus,
    MappingQualityClass,
    SourceAssignmentMethod,
    FormalSourceAssignment,
    MechanisticAtomOrigin,
    FormalMappedAtomPair,
    MechanisticAtomPair,
)


def _base_report_kwargs():
    """Minimal valid MappingReport fields (no formal/mechanistic)."""
    return {
        "mapper_name": "t",
        "mapper_version": "1",
        "input_hash": "a",
        "output_hash": "b",
        "mapping_status": MappingStatus.fully_mapped,
        "mapped_heavy_atom_fraction": 1.0,
        "map_number_uniqueness": True,
        "changed_atom_coverage": 1.0,
    }


# -- Section 19 #12: mechanistic typed evidence IDs conflict with flat --

@pytest.mark.contract
def test_mechanistic_typed_evidence_ids_conflict_with_flat_rejected():
    """mechanistic_atom_origin.evidence_ids=['E1'] vs flat=['E2'] must be rejected."""
    with pytest.raises(ValidationError, match="evidence IDs conflict"):
        MappingReport(
            **_base_report_kwargs(),
            mechanistic_atom_origin=MechanisticAtomOrigin(
                evidence_ids=["E1"], evidence_type="isotope_tracing"
            ),
            mechanistic_origin_evidence_ids=["E2"],
        )


# -- Section 19 #13: formal typed assignment method conflicts with flat --

@pytest.mark.contract
def test_formal_typed_method_conflicts_with_flat_rejected():
    with pytest.raises(ValidationError, match="assignment_method conflict"):
        MappingReport(
            **_base_report_kwargs(),
            formal_mapped_source_assignment=FormalSourceAssignment(
                mapper_name="t",
                mapper_version="1",
                assignment_method=SourceAssignmentMethod.manual_curation,
            ),
            source_assignment_method=SourceAssignmentMethod.formal_mapped,
        )


# -- Section 19 #14: typed assignment quality conflicts with flat --

@pytest.mark.contract
def test_typed_quality_conflicts_with_flat_rejected():
    with pytest.raises(ValidationError, match="assignment_quality conflict"):
        MappingReport(
            **_base_report_kwargs(),
            formal_mapped_source_assignment=FormalSourceAssignment(
                mapper_name="t",
                mapper_version="1",
                assignment_quality=MappingQualityClass.high_quality,
            ),
            source_assignment_quality=MappingQualityClass.low_quality,
        )


# -- Section 19 #15: typed ambiguity conflicts with flat --

@pytest.mark.contract
def test_typed_ambiguity_conflicts_with_flat_rejected():
    with pytest.raises(ValidationError, match="assignment_ambiguity conflict"):
        MappingReport(
            **_base_report_kwargs(),
            formal_mapped_source_assignment=FormalSourceAssignment(
                mapper_name="t",
                mapper_version="1",
                assignment_ambiguity=True,
            ),
            source_assignment_ambiguity=False,
        )


# -- Section 19 #16: arbitrary nested mapped atom pair field --

@pytest.mark.contract
def test_arbitrary_nested_mapped_atom_pair_field_rejected():
    """An extra field in a mapped atom pair dict must be rejected (typed skeleton)."""
    with pytest.raises(ValidationError):
        FormalSourceAssignment(
            mapper_name="t",
            mapper_version="1",
            mapped_atom_pairs=[
                {
                    "reactant_participant_id": "p1",
                    "reactant_atom_map": 1,
                    "product_participant_id": "p2",
                    "product_atom_map": 2,
                    "extra_field": "bad",
                }
            ],
        )


@pytest.mark.contract
def test_typed_mapped_atom_pair_accepted():
    """A properly typed FormalMappedAtomPair must be accepted."""
    fsa = FormalSourceAssignment(
        mapper_name="t",
        mapper_version="1",
        mapped_atom_pairs=[
            FormalMappedAtomPair(
                reactant_participant_id="p1",
                reactant_atom_map=1,
                product_participant_id="p2",
                product_atom_map=2,
            )
        ],
    )
    assert len(fsa.mapped_atom_pairs) == 1
    assert fsa.mapped_atom_pairs[0].reactant_atom_map == 1


# -- Section 12: unbound mechanistic evidence prohibited --

@pytest.mark.contract
def test_unbound_mechanistic_evidence_prohibited():
    """mechanistic_origin_evidence_ids non-empty without mechanistic_atom_origin
    is prohibited (Section 12, ADR-0003 decision: forbid unbound evidence)."""
    with pytest.raises(ValidationError, match="Unbound"):
        MappingReport(
            **_base_report_kwargs(),
            mechanistic_origin_evidence_ids=["ev1"],
            mechanistic_atom_origin=None,
        )


# -- Section 11: mechanistic pair must reference existing evidence --

@pytest.mark.contract
def test_mechanistic_pair_unknown_evidence_rejected():
    """mechanistic_atom_pair.evidence_id must exist in mechanistic_atom_origin.evidence_ids."""
    with pytest.raises(ValidationError, match="unknown evidence_id"):
        MechanisticAtomOrigin(
            evidence_ids=["E1"],
            evidence_type="isotope_tracing",
            mechanistic_atom_pairs=[
                MechanisticAtomPair(
                    source_participant_id="p1",
                    source_atom_identifier=1,
                    target_participant_id="p2",
                    target_atom_identifier=2,
                    evidence_id="E_UNKNOWN",
                )
            ],
        )


@pytest.mark.contract
def test_mechanistic_pair_valid_evidence_accepted():
    """A mechanistic pair referencing an existing evidence ID must be accepted."""
    mao = MechanisticAtomOrigin(
        evidence_ids=["E1"],
        evidence_type="isotope_tracing",
        mechanistic_atom_pairs=[
            MechanisticAtomPair(
                source_participant_id="p1",
                source_atom_identifier=1,
                target_participant_id="p2",
                target_atom_identifier=2,
                evidence_id="E1",
            )
        ],
    )
    assert len(mao.mechanistic_atom_pairs) == 1


# -- Positive: typed-only assignment derives flat fields --

@pytest.mark.contract
def test_typed_only_assignment_derives_flat_fields():
    """When only the typed object is provided, flat fields must be derived from it."""
    mr = MappingReport(
        **_base_report_kwargs(),
        formal_mapped_source_assignment=FormalSourceAssignment(
            mapper_name="t",
            mapper_version="1",
            assignment_method=SourceAssignmentMethod.manual_curation,
            assignment_quality=MappingQualityClass.high_quality,
            assignment_ambiguity=True,
        ),
    )
    assert mr.source_assignment_method == SourceAssignmentMethod.manual_curation
    assert mr.source_assignment_quality == MappingQualityClass.high_quality
    assert mr.source_assignment_ambiguity is True


# -- Positive: typed/flat consistent accepted --

@pytest.mark.contract
def test_typed_flat_consistent_accepted():
    """When typed and flat are explicitly consistent, the report must be accepted."""
    mr = MappingReport(
        **_base_report_kwargs(),
        formal_mapped_source_assignment=FormalSourceAssignment(
            mapper_name="t",
            mapper_version="1",
            assignment_method=SourceAssignmentMethod.manual_curation,
        ),
        source_assignment_method=SourceAssignmentMethod.manual_curation,
    )
    assert mr.source_assignment_method == SourceAssignmentMethod.manual_curation


# -- Positive: mechanistic evidence IDs derived from typed --

@pytest.mark.contract
def test_mechanistic_typed_derives_flat_evidence_ids():
    """When only mechanistic_atom_origin is provided, flat evidence IDs derive from it."""
    mr = MappingReport(
        **_base_report_kwargs(),
        mechanistic_atom_origin=MechanisticAtomOrigin(
            evidence_ids=["E1", "E2"], evidence_type="isotope_tracing"
        ),
    )
    assert set(mr.mechanistic_origin_evidence_ids) == {"E1", "E2"}
