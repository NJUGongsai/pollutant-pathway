"""Schema strictness contract tests.

Verifies strict=True actually blocks type coercion.
"""

import pytest
from pydantic import ValidationError
from reaction_agent.schemas import (
    StrictModel,
    MappingReport,
    MappingStatus,
    MappingQualityClass,
    ReactionEvidence,
    ReactionParticipant,
    LineageResolution,
    SourceReactionLedger,
    CandidateAnalogyLedger,
    TransformationHypothesis,
    SiteHypothesis,
    ProductionSelectionHypothesis,
    AgentProposedHypothesis,
    Candidate,
    PredictionResult,
    LedgerBalanceStatus,
    ResultStatus,
    DecisionKind,
    Lane,
    ApplicabilityLabel,
    AtomTarget,
    BondTarget,
)


# -- extra="forbid" tests --

@pytest.mark.contract
def test_strict_model_rejects_unknown_fields():
    class TestModel(StrictModel):
        name: str

    with pytest.raises(ValidationError):
        TestModel(name="ok", unknown_field="bad")


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
            unknown_extra="bad",
        )


# -- strict=True coercion rejection --

@pytest.mark.contract
def test_string_to_int_coercion_rejected():
    """Strict mode: '7' must NOT convert to 7."""
    with pytest.raises(ValidationError):
        AtomTarget(kind="atom", atom_id="7")


@pytest.mark.contract
def test_string_to_float_coercion_rejected():
    """Strict mode: '1.0' must NOT convert to 1.0."""
    with pytest.raises(ValidationError):
        MappingReport(
            mapper_name="test", mapper_version="1.0",
            input_hash="abc", output_hash="def",
            mapping_status=MappingStatus.fully_mapped,
            mapped_heavy_atom_fraction="1.0",
            map_number_uniqueness=True,
            changed_atom_coverage=1.0,
        )


@pytest.mark.contract
def test_int_to_bool_coercion_rejected():
    """Strict mode: 1 must NOT convert to True."""
    class TestBool(StrictModel):
        flag: bool

    with pytest.raises(ValidationError):
        TestBool(flag=1)


# -- empty string ID rejection --

@pytest.mark.contract
def test_empty_reaction_id_rejected():
    with pytest.raises(ValidationError):
        ReactionEvidence(
            reaction_id="",
            source_record_id="src1",
            source_name="test",
            raw_reaction="CC>>CC",
            normalized_reaction="CC>>CC",
        )


@pytest.mark.contract
def test_empty_hypothesis_id_rejected():
    with pytest.raises(ValidationError):
        ProductionSelectionHypothesis(
            hypothesis_id="",
            transformation_id="t1",
            site_id="s1",
        )


# -- enum validation --

@pytest.mark.contract
def test_invalid_mapping_status_rejected():
    with pytest.raises(ValidationError):
        MappingReport(
            mapper_name="test", mapper_version="1.0",
            input_hash="abc", output_hash="def",
            mapping_status="not_a_real_status",
            mapped_heavy_atom_fraction=1.0,
            map_number_uniqueness=True,
            changed_atom_coverage=1.0,
        )


# -- JSON Schema export --

TOP_LEVEL_SCHEMAS = [
    MappingReport,
    ReactionParticipant,
    ReactionEvidence,
    LineageResolution,
    SourceReactionLedger,
    CandidateAnalogyLedger,
    TransformationHypothesis,
    SiteHypothesis,
    ProductionSelectionHypothesis,
    AgentProposedHypothesis,
    Candidate,
    PredictionResult,
]


@pytest.mark.contract
@pytest.mark.parametrize("schema_cls", TOP_LEVEL_SCHEMAS, ids=[s.__name__ for s in TOP_LEVEL_SCHEMAS])
def test_schema_exports_json_schema(schema_cls):
    json_schema = schema_cls.model_json_schema()
    assert isinstance(json_schema, dict)
    assert "properties" in json_schema or "title" in json_schema
    assert json_schema.get("additionalProperties", True) is False


# -- required field rejection --

@pytest.mark.contract
def test_mapping_report_requires_mapper_name():
    with pytest.raises(ValidationError):
        MappingReport(
            mapper_version="1.0",
            input_hash="abc", output_hash="def",
            mapping_status=MappingStatus.fully_mapped,
            mapped_heavy_atom_fraction=1.0,
            map_number_uniqueness=True,
            changed_atom_coverage=1.0,
        )


@pytest.mark.contract
def test_candidate_requires_candidate_id():
    with pytest.raises(ValidationError):
        Candidate(
            canonical_product="CCCC=O",
            lane=Lane.strict,
            origin="agent_selected_from_evidence_space",
        )


# -- Typed target validation --

@pytest.mark.contract
def test_atom_target_positive():
    t = AtomTarget(kind="atom", atom_id=5)
    assert t.atom_id == 5
    assert t.kind == "atom"


@pytest.mark.contract
def test_bond_target_positive():
    t = BondTarget(kind="bond", begin_atom_id=3, end_atom_id=5)
    assert t.kind == "bond"


@pytest.mark.contract
def test_unknown_target_kind_rejected():
    with pytest.raises(ValidationError):
        AgentProposedHypothesis(
            hypothesis_id="h1",
            transformation_family_id="ox",
            typed_target_atom_or_bond_set=[{"kind": "molecule", "id": 5}],
        )
