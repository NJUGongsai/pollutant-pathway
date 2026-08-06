"""T2 RED tests — agent loop (final_plan §10.3) + policy P2 closures.

Must FAIL (RED) until:
- ``reaction_agent/agent/loop.py`` exists (mandatory baseline gate wiring)
- policy P2 closures land in ``reaction_agent/agent/policy.py`` / ``provider.py``

P2 closures:
- P7-T1T3-01: ``assert_allowed`` accepts raw string / None and raises a TYPED
  PolicyViolationError (not AttributeError).
- P7-T1T3-02: ``decide()`` handles duplicate hypothesis_id (dedup or reject).
- P7-T1T3-03: loop constructs the provider with ``max_calls > 0`` (budget).
"""
from __future__ import annotations

import pytest

from reaction_agent.agent.loop import AgentLoop
from reaction_agent.agent.policy import (
    AgentAction,
    PolicyViolationError,
    ProductionPolicy,
)
from reaction_agent.agent.provider import ProviderSpec
from reaction_agent.schemas.hypothesis import (
    ProductionSelectionHypothesis,
    HypothesisReferenceRegistry,
    HypothesisValidationContext,
)


# -- P7-T1T3-01: assert_allowed raw string / None -> typed PolicyViolationError --

class TestAssertAllowedTyped:
    def test_raw_string_forbidden_action_raises_typed(self):
        policy = ProductionPolicy(policy_version="p7-2")
        with pytest.raises(PolicyViolationError):
            policy.assert_allowed("create_structure")

    def test_none_raises_typed(self):
        policy = ProductionPolicy(policy_version="p7-2")
        with pytest.raises(PolicyViolationError):
            policy.assert_allowed(None)

    def test_raw_string_allowed_action_passes(self):
        policy = ProductionPolicy(policy_version="p7-2")
        # allowed actions still pass when passed as raw strings
        policy.assert_allowed("expand_local_evidence")

    def test_enum_forbidden_action_raises_typed(self):
        policy = ProductionPolicy(policy_version="p7-2")
        with pytest.raises(PolicyViolationError):
            policy.assert_allowed(AgentAction.WRITE_ABSTENTION)


# -- P7-T1T3-02: decide() duplicate hypothesis_id --

def _registry():
    return HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1", "rxn2"}),
        lineage_ids=frozenset({"lin1", "lin2"}),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset({"s1"}),
        lineage_to_reaction_id={"lin1": "rxn1", "lin2": "rxn2"},
        transformation_to_lineage_ids={"t1": ["lin1", "lin2"]},
        site_to_transformation_id={"s1": "t1"},
    )


def _hypothesis(hid: str, rxn: str, lin: str):
    return ProductionSelectionHypothesis(
        hypothesis_id=hid,
        support_reaction_ids=[rxn],
        support_lineage_ids=[lin],
        transformation_id="t1",
        site_id="s1",
    )


class TestDecideDuplicate:
    def test_decide_rejects_duplicate_hypothesis_id(self):
        """Duplicate hypothesis_id must be rejected (or deduped) — never
        silently double-listed in the priority output."""
        policy = ProductionPolicy(policy_version="p7-2")
        context = HypothesisValidationContext(registry=_registry())
        # h1 duplicated
        hypotheses = [
            _hypothesis("h1", "rxn1", "lin1"),
            _hypothesis("h1", "rxn1", "lin1"),
            _hypothesis("h2", "rxn2", "lin2"),
        ]
        decision = policy.decide(context=context, hypotheses=hypotheses)
        # must not contain h1 twice
        assert len(decision.priority) == len(set(decision.priority))
        assert decision.priority.count("h1") == 1


# -- P7-T1T3-03: loop constructs provider with max_calls > 0 --

class TestLoopProviderBudget:
    def test_loop_constructs_provider_with_max_calls_gt_zero(self):
        loop = AgentLoop(provider_spec=ProviderSpec(provider="a", model="m"))
        assert loop.provider.spec.max_calls > 0, (
            "agent loop must inject a positive provider call budget"
        )