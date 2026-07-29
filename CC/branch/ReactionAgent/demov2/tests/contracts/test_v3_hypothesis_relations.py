"""V3 remediation: relation-aware hypothesis & ledger validation (Section 6, 7).

Upgrades reference validation from "ID set existence" to "relation integrity":
- lineage -> reaction membership
- transformation -> cited lineage derivation
- site -> transformation membership
- atom/bond target -> query membership
- relaxation -> selected policy membership
- source_ledger_id -> real existence
- candidate_id -> context membership

Negative cases (Section 19 #1-#9).
"""

import pytest

from pydantic import ValidationError

from reaction_agent.schemas import (
    ProductionSelectionHypothesis,
    AgentProposedHypothesis,
    HypothesisReferenceRegistry,
    HypothesisValidationContext,
    LedgerReferenceRegistry,
    validate_hypothesis_references,
    validate_hypothesis_against_context,
    validate_candidate_ledger_references,
    UnknownReferenceError,
    AtomTarget,
    BondTarget,
    CandidateAnalogyLedger,
)


# -- Section 19 #6: BondTarget self-bond --

@pytest.mark.contract
def test_bond_target_self_bond_rejected():
    """BondTarget with begin_atom_id == end_atom_id must be rejected."""
    with pytest.raises(ValidationError, match="begin.*end"):
        BondTarget(begin_atom_id=4, end_atom_id=4)


@pytest.mark.contract
def test_bond_target_distinct_atoms_accepted():
    """BondTarget with distinct atoms is valid."""
    bt = BondTarget(begin_atom_id=0, end_atom_id=1)
    assert bt.begin_atom_id == 0
    assert bt.end_atom_id == 1


# -- Section 19 #1: site belongs to another transformation --

@pytest.mark.contract
def test_site_belongs_to_another_transformation_rejected():
    """site s1 belongs to t1; hypothesis selecting t2 + s1 must be rejected."""
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        transformation_ids=frozenset({"t1", "t2"}),
        site_ids=frozenset({"s1"}),
        site_to_transformation_id={"s1": "t1"},
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        transformation_id="t2",
        site_id="s1",
    )
    with pytest.raises(UnknownReferenceError, match="site.*transformation"):
        validate_hypothesis_references(h, registry)


# -- Section 19 #2: lineage belongs to another reaction --

@pytest.mark.contract
def test_lineage_belongs_to_another_reaction_rejected():
    """lineage l1 belongs to rxn2; citing it under support rxn1 must be rejected."""
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1", "rxn2"}),
        lineage_ids=frozenset({"l1"}),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset({"s1"}),
        lineage_to_reaction_id={"l1": "rxn2"},
        site_to_transformation_id={"s1": "t1"},
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        support_lineage_ids=["l1"],
        transformation_id="t1",
        site_id="s1",
    )
    with pytest.raises(UnknownReferenceError, match="lineage.*reaction"):
        validate_hypothesis_references(h, registry)


# -- Section 19 #3: transformation not derived from cited lineage --

@pytest.mark.contract
def test_transformation_not_from_cited_lineage_rejected():
    """transformation t1 derives from l2; citing l1 with t1 must be rejected."""
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        lineage_ids=frozenset({"l1", "l2"}),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset({"s1"}),
        lineage_to_reaction_id={"l1": "rxn1", "l2": "rxn1"},
        transformation_to_lineage_ids={"t1": ["l2"]},
        site_to_transformation_id={"s1": "t1"},
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        support_lineage_ids=["l1"],
        transformation_id="t1",
        site_id="s1",
    )
    with pytest.raises(UnknownReferenceError, match="transformation.*lineage"):
        validate_hypothesis_references(h, registry)


# -- Section 19 #7: relaxation exists globally but not under selected policy --

@pytest.mark.contract
def test_relaxation_not_under_selected_policy_rejected():
    """r2 exists globally but policy_a only allows r1; r2 under policy_a rejected."""
    registry = HypothesisReferenceRegistry(
        transformation_family_ids=frozenset({"ox"}),
        relaxation_policy_ids=frozenset({"policy_a"}),
        relaxation_ids=frozenset({"r1", "r2"}),
        relaxation_policy_to_allowed_ids={"policy_a": ["r1"]},
    )
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        transformation_family_id="ox",
        typed_target_atom_or_bond_set=[AtomTarget(atom_id=0)],
        relaxation_policy_id="policy_a",
        allowed_relaxation_ids=["r2"],
    )
    with pytest.raises(UnknownReferenceError, match="relaxation.*policy"):
        validate_hypothesis_references(h, registry)


# -- Positive: valid relation-aware production selection --

@pytest.mark.contract
def test_valid_production_selection_with_relations_accepted():
    """A fully consistent production selection must pass relation validation."""
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


# -- Section 19 #4: AtomTarget not in query --

@pytest.mark.contract
def test_atom_target_not_in_query_rejected():
    """AtomTarget(atom_id=999) when query has atoms {0,1,2} must be rejected."""
    registry = HypothesisReferenceRegistry(
        transformation_family_ids=frozenset({"ox"}),
    )
    context = HypothesisValidationContext(
        registry=registry,
        query_atom_ids=frozenset({0, 1, 2}),
    )
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        transformation_family_id="ox",
        typed_target_atom_or_bond_set=[AtomTarget(atom_id=999)],
    )
    with pytest.raises(UnknownReferenceError, match="atom.*query"):
        validate_hypothesis_against_context(h, context)


# -- Section 19 #5: BondTarget not in query --

@pytest.mark.contract
def test_bond_target_not_in_query_rejected():
    """BondTarget(0,2) when query only has bond (0,1) must be rejected."""
    registry = HypothesisReferenceRegistry(
        transformation_family_ids=frozenset({"ox"}),
    )
    context = HypothesisValidationContext(
        registry=registry,
        query_atom_ids=frozenset({0, 1, 2}),
        query_bond_pairs=frozenset({(0, 1)}),
    )
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        transformation_family_id="ox",
        typed_target_atom_or_bond_set=[BondTarget(begin_atom_id=0, end_atom_id=2)],
    )
    with pytest.raises(UnknownReferenceError, match="bond.*query"):
        validate_hypothesis_against_context(h, context)


# -- Positive: atom/bond target in query --

@pytest.mark.contract
def test_atom_and_bond_target_in_query_accepted():
    """Targets present in the query context must pass."""
    registry = HypothesisReferenceRegistry(
        transformation_family_ids=frozenset({"ox"}),
    )
    context = HypothesisValidationContext(
        registry=registry,
        query_atom_ids=frozenset({0, 1, 2}),
        query_bond_pairs=frozenset({(0, 1), (1, 2)}),
    )
    h = AgentProposedHypothesis(
        hypothesis_id="h2",
        transformation_family_id="ox",
        typed_target_atom_or_bond_set=[
            AtomTarget(atom_id=0),
            BondTarget(begin_atom_id=1, end_atom_id=2),
        ],
    )
    validate_hypothesis_against_context(h, context)  # must not raise


# -- Section 19 #8: source_ledger_id non-empty but unknown --

@pytest.mark.contract
def test_candidate_ledger_unknown_source_ledger_id_rejected():
    """source_ledger_id='DOES_NOT_EXIST' (non-empty but unknown) must be rejected."""
    registry = LedgerReferenceRegistry(
        source_ledger_ids=frozenset({"sl1"}),
        candidate_ids=frozenset({"c1"}),
    )
    ledger = CandidateAnalogyLedger(
        ledger_id="cl1",
        source_ledger_id="DOES_NOT_EXIST",
        candidate_id="c1",
    )
    with pytest.raises(UnknownReferenceError, match="source_ledger"):
        validate_candidate_ledger_references(ledger, registry)


# -- Section 19 #9: candidate_id unknown --

@pytest.mark.contract
def test_candidate_ledger_unknown_candidate_id_rejected():
    """candidate_id not in registry must be rejected."""
    registry = LedgerReferenceRegistry(
        source_ledger_ids=frozenset({"sl1"}),
        candidate_ids=frozenset({"c1"}),
    )
    ledger = CandidateAnalogyLedger(
        ledger_id="cl1",
        source_ledger_id="sl1",
        candidate_id="UNKNOWN",
    )
    with pytest.raises(UnknownReferenceError, match="candidate"):
        validate_candidate_ledger_references(ledger, registry)


# -- Section 7: missing source_ledger_id still rejected by schema --

@pytest.mark.contract
def test_candidate_ledger_missing_source_ledger_id_rejected():
    """Missing source_ledger_id must be rejected at schema level (existing contract)."""
    with pytest.raises(ValidationError):
        CandidateAnalogyLedger(ledger_id="cl1", candidate_id="c1")


# -- Positive: valid candidate ledger references --

@pytest.mark.contract
def test_valid_candidate_ledger_references_accepted():
    """A candidate ledger with known source_ledger_id and candidate_id must pass."""
    registry = LedgerReferenceRegistry(
        source_ledger_ids=frozenset({"sl1"}),
        candidate_ids=frozenset({"c1"}),
    )
    ledger = CandidateAnalogyLedger(
        ledger_id="cl1",
        source_ledger_id="sl1",
        candidate_id="c1",
    )
    validate_candidate_ledger_references(ledger, registry)  # must not raise
