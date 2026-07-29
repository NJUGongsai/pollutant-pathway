"""V4 fail-closed context validation (P0-G03 remediation, RED phase).

Proves that the OLD hypothesis validator is fail-open: when relation maps,
query context, or relaxation policy are missing/empty, it silently ACCEPTS
hypotheses that the NEW fail-closed validator must reject.

Negative cases (1-15) MUST raise on the NEW implementation; on the OLD
implementation they FAIL (RED) — either no raise or a mismatched raise.
Positive cases (P1-P5) MUST NOT raise on either implementation.
"""

import pytest
from pydantic import ValidationError

from reaction_agent.schemas import (
    AgentProposedHypothesis,
    AtomTarget,
    BondTarget,
    HypothesisReferenceRegistry,
    HypothesisValidationContext,
    ProductionSelectionHypothesis,
    UnknownReferenceError,
    validate_hypothesis_against_context,
    validate_hypothesis_references,
)


# -- Neg 1-6: ProductionSelection relation-coverage failures (UnknownReferenceError) --


@pytest.mark.contract
def test_all_ids_exist_but_relation_maps_empty():
    """All cited IDs exist but ALL relation maps empty -> must reject (lineage mapping missing)."""
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        lineage_ids=frozenset({"l1"}),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset({"s1"}),
        lineage_to_reaction_id={},
        transformation_to_lineage_ids={},
        site_to_transformation_id={},
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        support_lineage_ids=["l1"],
        transformation_id="t1",
        site_id="s1",
    )
    with pytest.raises(UnknownReferenceError, match=r"lineage.*mapping|mapping.*lineage"):
        validate_hypothesis_references(h, registry)


@pytest.mark.contract
def test_relation_maps_present_but_site_uncovered():
    """lineage & transformation maps consistent, but site_to_transformation_id does not cover s1 -> must reject."""
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        lineage_ids=frozenset({"l1"}),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset({"s1"}),
        lineage_to_reaction_id={"l1": "rxn1"},
        transformation_to_lineage_ids={"t1": ["l1"]},
        site_to_transformation_id={},  # s1 absent
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        support_lineage_ids=["l1"],
        transformation_id="t1",
        site_id="s1",
    )
    with pytest.raises(UnknownReferenceError, match=r"site.*mapping|mapping.*site"):
        validate_hypothesis_references(h, registry)


@pytest.mark.contract
def test_relation_maps_present_but_transformation_uncovered():
    """lineage & site maps present, but transformation_to_lineage_ids does not cover t1 -> must reject."""
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        lineage_ids=frozenset({"l1"}),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset({"s1"}),
        lineage_to_reaction_id={"l1": "rxn1"},
        transformation_to_lineage_ids={},  # t1 absent
        site_to_transformation_id={"s1": "t1"},
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        support_lineage_ids=["l1"],
        transformation_id="t1",
        site_id="s1",
    )
    with pytest.raises(UnknownReferenceError, match=r"transformation.*mapping|mapping.*transformation"):
        validate_hypothesis_references(h, registry)


@pytest.mark.contract
def test_cited_lineage_has_no_lineage_to_reaction_mapping():
    """transformation & site maps present, but lineage_to_reaction_id does not cover cited l1 -> must reject."""
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        lineage_ids=frozenset({"l1"}),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset({"s1"}),
        lineage_to_reaction_id={},  # l1 absent
        transformation_to_lineage_ids={"t1": ["l1"]},
        site_to_transformation_id={"s1": "t1"},
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        support_lineage_ids=["l1"],
        transformation_id="t1",
        site_id="s1",
    )
    with pytest.raises(UnknownReferenceError, match=r"lineage.*mapping"):
        validate_hypothesis_references(h, registry)


@pytest.mark.contract
def test_production_support_reactions_empty():
    """Full consistent registry but support_reaction_ids empty -> must reject with explicit emptiness error."""
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        lineage_ids=frozenset({"l1"}),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset({"s1"}),
        lineage_to_reaction_id={"l1": "rxn1"},
        transformation_to_lineage_ids={"t1": ["l1"]},
        site_to_transformation_id={"s1": "t1"},
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=[],
        support_lineage_ids=["l1"],
        transformation_id="t1",
        site_id="s1",
    )
    with pytest.raises(UnknownReferenceError, match=r"support_reaction_ids.*empty|empty.*support_reaction_ids"):
        validate_hypothesis_references(h, registry)


@pytest.mark.contract
def test_production_support_lineages_empty():
    """Full consistent registry but support_lineage_ids empty -> must reject with explicit emptiness error."""
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        lineage_ids=frozenset({"l1"}),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset({"s1"}),
        lineage_to_reaction_id={"l1": "rxn1"},
        transformation_to_lineage_ids={"t1": ["l1"]},
        site_to_transformation_id={"s1": "t1"},
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        support_lineage_ids=[],
        transformation_id="t1",
        site_id="s1",
    )
    with pytest.raises(UnknownReferenceError, match=r"support_lineage_ids.*empty|empty.*support_lineage_ids"):
        validate_hypothesis_references(h, registry)


# -- Neg 7-9: AgentProposed query-context failures (UnknownReferenceError) --


@pytest.mark.contract
def test_agent_target_present_but_query_context_not_provided():
    """typed_target present but query_atom_ids & query_bond_pairs both None -> must reject (context not provided)."""
    registry = HypothesisReferenceRegistry(transformation_family_ids=frozenset({"ox"}))
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        transformation_family_id="ox",
        typed_target_atom_or_bond_set=[AtomTarget(atom_id=0)],
    )
    with pytest.raises(UnknownReferenceError, match=r"query.*not.*provided|context.*not.*provided"):
        ctx = HypothesisValidationContext(
            registry=registry,
            query_atom_ids=None,
            query_bond_pairs=None,
        )
        validate_hypothesis_against_context(h, ctx)


@pytest.mark.contract
def test_bond_target_present_but_query_bond_pairs_none():
    """BondTarget present, query_atom_ids provided, but query_bond_pairs=None -> must reject (bond context not provided)."""
    registry = HypothesisReferenceRegistry(transformation_family_ids=frozenset({"ox"}))
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        transformation_family_id="ox",
        typed_target_atom_or_bond_set=[BondTarget(begin_atom_id=0, end_atom_id=1)],
    )
    with pytest.raises(UnknownReferenceError, match=r"bond.*not.*provided|query_bond_pairs.*not.*provided"):
        ctx = HypothesisValidationContext(
            registry=registry,
            query_atom_ids=frozenset({0, 1}),
            query_bond_pairs=None,
        )
        validate_hypothesis_against_context(h, ctx)


@pytest.mark.contract
def test_bond_target_endpoint_not_in_query_atoms():
    """BondTarget(0,2): pair is in query_bond_pairs but endpoint 2 is NOT in query_atom_ids -> must reject."""
    registry = HypothesisReferenceRegistry(transformation_family_ids=frozenset({"ox"}))
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        transformation_family_id="ox",
        typed_target_atom_or_bond_set=[BondTarget(begin_atom_id=0, end_atom_id=2)],
    )
    with pytest.raises(UnknownReferenceError, match=r"endpoint.*not.*in.*query|bond.*endpoint"):
        ctx = HypothesisValidationContext(
            registry=registry,
            query_atom_ids=frozenset({0, 1}),
            query_bond_pairs=frozenset({(0, 2)}),
        )
        validate_hypothesis_against_context(h, ctx)


# -- Neg 10-11: Relaxation/policy failures (UnknownReferenceError) --


@pytest.mark.contract
def test_relaxation_non_empty_but_policy_null():
    """allowed_relaxation_ids non-empty but relaxation_policy_id=None -> must reject (policy null)."""
    registry = HypothesisReferenceRegistry(
        transformation_family_ids=frozenset({"ox"}),
        relaxation_ids=frozenset({"r1"}),
        relaxation_policy_ids=frozenset(),
        relaxation_policy_to_allowed_ids={},
    )
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        transformation_family_id="ox",
        typed_target_atom_or_bond_set=[AtomTarget(atom_id=0)],
        relaxation_policy_id=None,
        allowed_relaxation_ids=["r1"],
    )
    with pytest.raises(UnknownReferenceError, match=r"policy.*null|allowed.*non-empty.*policy|policy.*not.*None"):
        validate_hypothesis_references(h, registry)


@pytest.mark.contract
def test_policy_non_empty_but_not_covered_by_map():
    """relaxation_policy_id=p1 exists but p1 absent from relaxation_policy_to_allowed_ids map -> must reject."""
    registry = HypothesisReferenceRegistry(
        transformation_family_ids=frozenset({"ox"}),
        relaxation_policy_ids=frozenset({"p1"}),
        relaxation_ids=frozenset(),
        relaxation_policy_to_allowed_ids={},  # p1 absent
    )
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        transformation_family_id="ox",
        typed_target_atom_or_bond_set=[AtomTarget(atom_id=0)],
        relaxation_policy_id="p1",
        allowed_relaxation_ids=[],
    )
    with pytest.raises(UnknownReferenceError, match=r"policy.*not.*covered|policy.*mapping|covered.*policy"):
        validate_hypothesis_references(h, registry)


# -- Neg 12-15: Registry internal-consistency failures (ValidationError at construction) --


@pytest.mark.contract
def test_registry_site_map_value_not_in_transformation_ids():
    """site_to_transformation_id references a transformation not in transformation_ids -> ValidationError."""
    with pytest.raises(ValidationError):
        HypothesisReferenceRegistry(
            site_ids=frozenset({"s1"}),
            transformation_ids=frozenset({"t1"}),
            site_to_transformation_id={"s1": "t_unknown"},
        )


@pytest.mark.contract
def test_registry_transformation_map_references_unknown_lineage():
    """transformation_to_lineage_ids references a lineage not in lineage_ids -> ValidationError."""
    with pytest.raises(ValidationError):
        HypothesisReferenceRegistry(
            transformation_ids=frozenset({"t1"}),
            lineage_ids=frozenset({"l1"}),
            transformation_to_lineage_ids={"t1": ["l_unknown"]},
        )


@pytest.mark.contract
def test_registry_lineage_map_references_unknown_reaction():
    """lineage_to_reaction_id references a reaction not in reaction_ids -> ValidationError."""
    with pytest.raises(ValidationError):
        HypothesisReferenceRegistry(
            lineage_ids=frozenset({"l1"}),
            reaction_ids=frozenset({"rxn1"}),
            lineage_to_reaction_id={"l1": "rxn_unknown"},
        )


@pytest.mark.contract
def test_registry_relaxation_policy_map_references_unknown_relaxation():
    """relaxation_policy_to_allowed_ids references a relaxation not in relaxation_ids -> ValidationError."""
    with pytest.raises(ValidationError):
        HypothesisReferenceRegistry(
            relaxation_policy_ids=frozenset({"p1"}),
            relaxation_ids=frozenset({"r1"}),
            relaxation_policy_to_allowed_ids={"p1": ["r_unknown"]},
        )


# -- Pos P1-P5: legal hypotheses must NOT raise --


@pytest.mark.contract
def test_full_production_selection_accepted():
    """Fully consistent production selection must pass relation validation."""
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        lineage_ids=frozenset({"l1"}),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset({"s1"}),
        lineage_to_reaction_id={"l1": "rxn1"},
        transformation_to_lineage_ids={"t1": ["l1"]},
        site_to_transformation_id={"s1": "t1"},
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        support_lineage_ids=["l1"],
        transformation_id="t1",
        site_id="s1",
    )
    validate_hypothesis_references(h, registry)  # must not raise


@pytest.mark.contract
def test_legal_atom_target_accepted():
    """AtomTarget whose atom_id is in query_atom_ids must pass."""
    registry = HypothesisReferenceRegistry(transformation_family_ids=frozenset({"ox"}))
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        transformation_family_id="ox",
        typed_target_atom_or_bond_set=[AtomTarget(atom_id=1)],
    )
    ctx = HypothesisValidationContext(
        registry=registry,
        query_atom_ids=frozenset({0, 1, 2}),
    )
    validate_hypothesis_against_context(h, ctx)  # must not raise


@pytest.mark.contract
def test_legal_bond_target_accepted():
    """BondTarget whose pair is in query_bond_pairs must pass."""
    registry = HypothesisReferenceRegistry(transformation_family_ids=frozenset({"ox"}))
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        transformation_family_id="ox",
        typed_target_atom_or_bond_set=[BondTarget(begin_atom_id=1, end_atom_id=2)],
    )
    ctx = HypothesisValidationContext(
        registry=registry,
        query_atom_ids=frozenset({0, 1, 2}),
        query_bond_pairs=frozenset({(0, 1), (1, 2)}),
    )
    validate_hypothesis_against_context(h, ctx)  # must not raise


@pytest.mark.contract
def test_explicit_empty_bond_set_accepted():
    """Explicit empty query_bond_pairs (frozenset(), NOT None) with legal atom target must pass."""
    registry = HypothesisReferenceRegistry(transformation_family_ids=frozenset({"ox"}))
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        transformation_family_id="ox",
        typed_target_atom_or_bond_set=[AtomTarget(atom_id=0)],
    )
    ctx = HypothesisValidationContext(
        registry=registry,
        query_atom_ids=frozenset({0}),
        query_bond_pairs=frozenset(),  # explicit empty, NOT None
    )
    validate_hypothesis_against_context(h, ctx)  # must not raise


@pytest.mark.contract
def test_legal_relaxation_accepted():
    """Consistent relaxation policy + allowed relaxation IDs must pass."""
    registry = HypothesisReferenceRegistry(
        transformation_family_ids=frozenset({"ox"}),
        relaxation_policy_ids=frozenset({"p1"}),
        relaxation_ids=frozenset({"r1"}),
        relaxation_policy_to_allowed_ids={"p1": ["r1"]},
    )
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        transformation_family_id="ox",
        typed_target_atom_or_bond_set=[AtomTarget(atom_id=0)],
        relaxation_policy_id="p1",
        allowed_relaxation_ids=["r1"],
    )
    validate_hypothesis_references(h, registry)  # must not raise
