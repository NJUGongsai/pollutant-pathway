"""ADR-0002: Hypothesis lane contract tests.

Tests lane separation, reference validation, typed targets.
"""

import pytest
from pydantic import ValidationError, TypeAdapter
from reaction_agent.schemas import (
    ProductionSelectionHypothesis,
    AgentProposedHypothesis,
    Hypothesis,
    HypothesisReferenceRegistry,
    UnknownReferenceError,
    validate_hypothesis_references,
    AtomTarget,
    BondTarget,
)


# -- Positive cases --

@pytest.mark.contract
def test_production_selection_positive():
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        support_lineage_ids=["lin1"],
        transformation_id="t1",
        site_id="s1",
        rationale_summary="alcohol oxidation",
        policy_version="1.0",
    )
    assert h.hypothesis_origin == "agent_selected_from_evidence_space"


@pytest.mark.contract
def test_agent_proposed_positive():
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        support_reaction_ids=["rxn1"],
        transformation_family_id="oxidation",
        typed_target_atom_or_bond_set=[AtomTarget(kind="atom", atom_id=0)],
        rationale_summary="novel hydroxylation",
        policy_version="1.0",
    )
    assert h.hypothesis_origin == "agent_proposed"


# -- Lane mixing rejection --

@pytest.mark.contract
def test_production_selection_rejects_agent_proposed_origin():
    with pytest.raises(ValidationError):
        ProductionSelectionHypothesis(
            hypothesis_id="h1",
            hypothesis_origin="agent_proposed",
            transformation_id="t1",
            site_id="s1",
        )


@pytest.mark.contract
def test_agent_proposed_rejects_production_origin():
    with pytest.raises(ValidationError):
        AgentProposedHypothesis(
            hypothesis_id="h1",
            hypothesis_origin="agent_selected_from_evidence_space",
            transformation_family_id="ox",
            typed_target_atom_or_bond_set=[AtomTarget(kind="atom", atom_id=0)],
        )


# -- Discriminated union --

@pytest.mark.contract
def test_discriminated_union_selects_production():
    adapter = TypeAdapter(Hypothesis)
    h = adapter.validate_python({
        "hypothesis_id": "h1",
        "hypothesis_origin": "agent_selected_from_evidence_space",
        "transformation_id": "t1",
        "site_id": "s1",
        "rationale_summary": "test",
        "policy_version": "1.0",
    })
    assert isinstance(h, ProductionSelectionHypothesis)


@pytest.mark.contract
def test_discriminated_union_selects_agent_proposed():
    adapter = TypeAdapter(Hypothesis)
    h = adapter.validate_python({
        "hypothesis_id": "h2",
        "hypothesis_origin": "agent_proposed",
        "transformation_family_id": "oxidation",
        "typed_target_atom_or_bond_set": [{"kind": "atom", "atom_id": 0}],
        "rationale_summary": "test",
        "policy_version": "1.0",
    })
    assert isinstance(h, AgentProposedHypothesis)


# -- Reference validation --

@pytest.mark.contract
def test_reference_validation_passes_with_known_ids():
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        lineage_ids=frozenset({"lin1"}),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset({"s1"}),
        lineage_to_reaction_id={"lin1": "rxn1"},
        transformation_to_lineage_ids={"t1": ["lin1"]},
        site_to_transformation_id={"s1": "t1"},
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        support_lineage_ids=["lin1"],
        transformation_id="t1",
        site_id="s1",
    )
    validate_hypothesis_references(h, registry)  # should not raise


@pytest.mark.contract
def test_reference_validation_rejects_unknown_ids():
    registry = HypothesisReferenceRegistry()  # empty registry
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["nonexistent_rxn"],
        transformation_id="t1",
        site_id="s1",
    )
    with pytest.raises(UnknownReferenceError):
        validate_hypothesis_references(h, registry)


# -- Production selection has no relaxation fields --

@pytest.mark.contract
def test_production_selection_no_relaxation_fields():
    schema = ProductionSelectionHypothesis.model_json_schema()
    props = schema.get("properties", {})
    assert "relaxation_policy_id" not in props
    assert "allowed_relaxation_ids" not in props


# -- Unknown field rejection --

@pytest.mark.contract
def test_production_selection_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        ProductionSelectionHypothesis(
            hypothesis_id="h1",
            transformation_id="t1",
            site_id="s1",
            invented_field="bad",
        )


@pytest.mark.contract
def test_agent_proposed_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        AgentProposedHypothesis(
            hypothesis_id="h1",
            transformation_family_id="ox",
            typed_target_atom_or_bond_set=[AtomTarget(kind="atom", atom_id=0)],
            invented_field="bad",
        )
