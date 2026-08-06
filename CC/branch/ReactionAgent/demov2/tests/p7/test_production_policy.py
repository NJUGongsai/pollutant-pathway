"""T3 RED tests — ProductionSelectionHypothesis policy (final_plan §10.4).

Must FAIL (RED) until ``reaction_agent/agent/policy.py`` exists.

Scope (final_plan §10.4):
- ID validation
- transform/site exists
- support exists
- rationale summary
- policy version
- priority only

Permission boundary:
- Agent CAN: expand local evidence / compare IDs / choose T/S / prioritize / stop
- Agent CANNOT: create structure / mutate rank.lane.ledger / write abstention

Reuses the existing ProductionSelectionHypothesis schema — does NOT recreate it.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from reaction_agent.agent.policy import (
    AgentAction,
    ProductionPolicy,
    PolicyViolationError,
    PolicyDecision,
)
from reaction_agent.schemas.hypothesis import (
    ProductionSelectionHypothesis,
    HypothesisReferenceRegistry,
    HypothesisValidationContext,
    UnknownReferenceError,
    validate_hypothesis_against_context,
)


def make_registry():
    return HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1", "rxn2"}),
        lineage_ids=frozenset({"lin1", "lin2"}),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset({"s1"}),
        lineage_to_reaction_id={"lin1": "rxn1", "lin2": "rxn2"},
        transformation_to_lineage_ids={"t1": ["lin1", "lin2"]},
        site_to_transformation_id={"s1": "t1"},
    )


def make_context():
    return HypothesisValidationContext(registry=make_registry())


# -- ID validation / existence --

class TestIdValidation:
    def test_hypothesis_accepts_valid_ids(self):
        h = ProductionSelectionHypothesis(
            hypothesis_id="h1",
            support_reaction_ids=["rxn1"],
            support_lineage_ids=["lin1"],
            transformation_id="t1",
            site_id="s1",
            rationale_summary="alcohol oxidation",
            policy_version="p7-1",
        )
        validate_hypothesis_against_context(h, make_context())

    def test_unknown_transformation_rejected(self):
        h = ProductionSelectionHypothesis(
            hypothesis_id="h1",
            support_reaction_ids=["rxn1"],
            support_lineage_ids=["lin1"],
            transformation_id="t_ghost",
            site_id="s1",
        )
        with pytest.raises(UnknownReferenceError):
            validate_hypothesis_against_context(h, make_context())

    def test_unknown_site_rejected(self):
        h = ProductionSelectionHypothesis(
            hypothesis_id="h1",
            support_reaction_ids=["rxn1"],
            support_lineage_ids=["lin1"],
            transformation_id="t1",
            site_id="s_ghost",
        )
        with pytest.raises(UnknownReferenceError):
            validate_hypothesis_against_context(h, make_context())


# -- support exists --

class TestSupport:
    def test_empty_support_reaction_rejected(self):
        h = ProductionSelectionHypothesis(
            hypothesis_id="h1",
            support_reaction_ids=[],
            support_lineage_ids=["lin1"],
            transformation_id="t1",
            site_id="s1",
        )
        with pytest.raises(UnknownReferenceError):
            validate_hypothesis_against_context(h, make_context())


# -- rationale summary / policy version --

class TestRationaleAndVersion:
    def test_rationale_summary_persisted(self):
        h = ProductionSelectionHypothesis(
            hypothesis_id="h1",
            support_reaction_ids=["rxn1"],
            support_lineage_ids=["lin1"],
            transformation_id="t1",
            site_id="s1",
            rationale_summary="clear rationale",
            policy_version="p7-1",
        )
        assert h.rationale_summary == "clear rationale"
        assert h.policy_version == "p7-1"


# -- priority only --

class TestPriorityOnly:
    def test_production_hypothesis_has_no_structure_fields(self):
        """ProductionSelectionHypothesis carries NO relaxed-structure fields
        (typed targets, relaxation policy). Priority-only lane."""
        with pytest.raises(ValidationError):
            ProductionSelectionHypothesis(
                hypothesis_id="h1",
                support_reaction_ids=["rxn1"],
                support_lineage_ids=["lin1"],
                transformation_id="t1",
                site_id="s1",
                typed_target_atom_or_bond_set=[{"kind": "atom", "atom_id": 0}],
            )


# -- policy permission boundary --

class TestPermissionBoundary:
    def test_allowed_actions_do_not_raise(self):
        policy = ProductionPolicy(policy_version="p7-1")
        for action in [
            AgentAction.EXPAND_LOCAL_EVIDENCE,
            AgentAction.COMPARE_IDS,
            AgentAction.CHOOSE_T_S,
            AgentAction.PRIORITIZE,
            AgentAction.STOP,
        ]:
            policy.assert_allowed(action)  # must not raise

    def test_forbidden_actions_raise(self):
        policy = ProductionPolicy(policy_version="p7-1")
        for action in [
            AgentAction.CREATE_STRUCTURE,
            AgentAction.MUTATE_RANK,
            AgentAction.MUTATE_LANE,
            AgentAction.MUTATE_LEDGER,
            AgentAction.WRITE_ABSTENTION,
        ]:
            with pytest.raises(PolicyViolationError):
                policy.assert_allowed(action)

    def test_policy_decision_priority_only(self):
        """PolicyDecision surfaces a priority-ordered selection of existing
        hypothesis IDs — it never creates a structure or mutates rank."""
        policy = ProductionPolicy(policy_version="p7-1")
        decision = policy.decide(
            context=make_context(),
            hypotheses=[
                ProductionSelectionHypothesis(
                    hypothesis_id="h1",
                    support_reaction_ids=["rxn1"],
                    support_lineage_ids=["lin1"],
                    transformation_id="t1",
                    site_id="s1",
                ),
                ProductionSelectionHypothesis(
                    hypothesis_id="h2",
                    support_reaction_ids=["rxn2"],
                    support_lineage_ids=["lin2"],
                    transformation_id="t1",
                    site_id="s1",
                    rationale_summary="second",
                ),
            ],
        )
        assert isinstance(decision, PolicyDecision)
        assert decision.policy_version == "p7-1"
        # priority list references existing hypothesis IDs only
        assert len(decision.priority) == 2
        assert all(hid in {"h1", "h2"} for hid in decision.priority)

    def test_priority_does_not_mutate_rank_lane_ledger(self):
        """PolicyDecision must not carry rank/lane/ledger mutation — the
        decision object has no such fields (strict schema = reject)."""
        with pytest.raises(ValueError):
            PolicyDecision(
                policy_version="p7-1",
                priority=["h1"],
                rank_mutation={"h1": 1},  # forbidden field
            )

    def test_policy_version_required(self):
        with pytest.raises(ValueError):
            ProductionPolicy(policy_version="")