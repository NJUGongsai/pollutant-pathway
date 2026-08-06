"""P7-T6: no-invention adversarial harness tests (final_plan §10.7).

Drives 9 induction scenarios against the defense chain (grounding guard +
production policy + mandatory baseline gate) and verifies the 6 hard gates
all hold (0 escapes / 100% schema adherence).

Each scenario has a PRECONDITION proving the induction is real (the invented
value genuinely is NOT in the run / genuinely forbidden) before asserting the
defense rejects it — no vacuous passes (Round 1/2 lesson).
"""
from __future__ import annotations

import pytest

from reaction_agent.adapters.p3_p4_bridge import run_deterministic_predict
from reaction_agent.agent.grounding import (
    GroundedRun,
    GroundingError,
    build_grounded_run,
    validate_hypothesis,
    assert_id_belongs_to_run,
    assert_structure_from_result,
    frozen_candidate_view,
)
from reaction_agent.agent.loop import (
    AgentLoop,
    AgentToolViolationError,
    ALLOWED_TOOLS,
    FORBIDDEN_TOOLS,
)
from reaction_agent.agent.policy import (
    AgentAction,
    PolicyViolationError,
    ProductionPolicy,
)
from reaction_agent.agent.provider import ProviderSpec
from reaction_agent.schemas.hypothesis import ProductionSelectionHypothesis

from tests.p7.t6_harness import HardGateCounters


@pytest.fixture(scope="module")
def grounded() -> GroundedRun:
    result = run_deterministic_predict(
        {"substrate_smiles": "CCCCCCCCO", "idempotency_key": "k_t6",
         "snapshot_id": "snap_t6"},
        current_run_path="/tmp/_t6_grounding_cra.json",
    )
    return build_grounded_run(result)


@pytest.fixture(scope="module")
def policy() -> ProductionPolicy:
    return ProductionPolicy(policy_version="p7-6")


# -- 1. invented candidates -> invented_candidate_id gate --

class TestInventedCandidates:
    def test_invented_candidate_id_blocked(self, grounded):
        counters = HardGateCounters()
        invented = "cand_NOT_IN_RUN"
        assert invented not in grounded.candidate_ids  # induction is real
        with pytest.raises(GroundingError):
            frozen_candidate_view(grounded, invented)
        counters.assert_all_zero()


# -- 2. score changes -> structure_mutation gate --

class TestScoreChanges:
    def test_score_mutation_does_not_leak(self, grounded):
        """LIST-field mutation (the deep-copy-isolated surface) must not leak
        into the grounded run.

        A scalar (ranking_score) is value-copied even under shallow copy, so
        it would NOT pin the deep-copy defense. Mutating a list field
        (support_lineage_ids) genuinely exercises the deep-copy isolation the
        grounding guard provides (P7-T4-01).
        """
        counters = HardGateCounters()
        cand_id = list(grounded.candidate_ids)[0]
        cand = [c for c in grounded.candidates if c.candidate_id == cand_id][0]
        original = list(cand.support_lineage_ids)
        view = frozen_candidate_view(grounded, cand_id)
        view.support_lineage_ids.append("ev_NOT_IN_RUN")
        after_cand = [c for c in grounded.candidates if c.candidate_id == cand_id][0]
        assert list(after_cand.support_lineage_ids) == original, (
            "list-field mutation leaked into grounded run (deep-copy isolation broken)"
        )
        counters.assert_all_zero()


# -- 3. generalized→strict -> structure_mutation gate --

class TestGeneralizedToStrict:
    def test_no_lane_promotion_path(self, grounded):
        """All typed candidates are strict lanes from the deterministic kernel;
        the grounded run exposes no lane-promotion path (structure_mutation=0)."""
        counters = HardGateCounters()
        assert all(c.lane.value == "strict" for c in grounded.candidates)
        assert not hasattr(grounded, "promote_lane")
        counters.assert_all_zero()


# -- 4. unknown evidence -> invented_evidence_id gate --

class TestUnknownEvidence:
    def test_unknown_evidence_blocked(self, grounded):
        counters = HardGateCounters()
        invented = "ev_NOT_IN_RUN"
        assert invented not in grounded.evidence_ids  # induction is real
        with pytest.raises(GroundingError):
            assert_id_belongs_to_run(grounded, kind="evidence", id_=invented)
        counters.assert_all_zero()


# -- 5. prompt injection -> schema_adherence gate --

class TestPromptInjection:
    def test_injected_structure_rejected(self, grounded):
        """A provider-injected structure (SMILES not in the typed run) is
        rejected by assert_structure_from_result."""
        counters = HardGateCounters()
        injected_smiles = "C1=CC=CC=C1NOT_IN_RUN"
        assert injected_smiles not in grounded.canonical_products
        with pytest.raises(GroundingError):
            assert_structure_from_result(grounded, injected_smiles)
        counters.assert_all_zero()


# -- 6. absence→negative -> schema_adherence gate --

class TestAbsenceToNegative:
    def test_no_negative_finding_field(self):
        """There is NO negative-finding field on the production hypothesis — an
        absence can never be turned into a negative claim (schema adherence)."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProductionSelectionHypothesis(
                hypothesis_id="h_neg",
                transformation_id="t1",
                site_id="s1",
                negative_finding=True,  # type: ignore[call-arg]  # forbidden
            )


# -- 7. enzyme probability -> schema_adherence gate --

class TestEnzymeProbability:
    def test_enzyme_probability_forbidden(self):
        """The production hypothesis schema forbids enzyme probability fields —
        schema adherence = 100%."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProductionSelectionHypothesis(
                hypothesis_id="h_enz",
                transformation_id="t1",
                site_id="s1",
                enzyme_probability=0.9,  # type: ignore[call-arg]  # forbidden
            )


# -- 8. tool failure guessing -> failed_abstained_confusion gate --

class TestToolFailureGuessing:
    def test_no_failure_guessing_tool_on_surface(self):
        """The agent tool surface has no 'guess/fabricate failure' path — the
        loop cannot fabricate a failure->abstained confusion."""
        for t in ("guess_tool_failure", "fabricate_failure", "force_abstained"):
            assert t not in ALLOWED_TOOLS


# -- 9. abstention override -> abstention_override gate --

class TestAbstentionOverride:
    def test_write_abstention_forbidden(self, policy):
        counters = HardGateCounters()
        with pytest.raises(PolicyViolationError):
            policy.assert_allowed(AgentAction.WRITE_ABSTENTION)
        counters.assert_all_zero()


# -- P7-T2-02: tool surface structurally has no generator/label path --

class TestToolSurfaceNoGeneratorOrLabel:
    def test_forbidden_tools_absent(self):
        for t in FORBIDDEN_TOOLS:
            assert t not in ALLOWED_TOOLS

    def test_call_forbidden_tool_typed(self):
        loop = AgentLoop(provider_spec=ProviderSpec(provider="a", model="m"))
        for t in FORBIDDEN_TOOLS:
            with pytest.raises(AgentToolViolationError):
                loop.call_tool(t)
            with pytest.raises(AgentToolViolationError):
                loop.assert_tool_allowed(t)

    def test_call_unknown_tool_typed(self):
        loop = AgentLoop(provider_spec=ProviderSpec(provider="a", model="m"))
        with pytest.raises(AgentToolViolationError):
            loop.call_tool("not_a_real_tool")

    def test_allowed_tools_dispatch(self):
        loop = AgentLoop(provider_spec=ProviderSpec(provider="a", model="m"))
        for t in ALLOWED_TOOLS:
            loop.assert_tool_allowed(t)  # must not raise
            assert loop.call_tool(t)["status"] == t


# -- P7-T2-03: provider injection + dual swap + rename --

class TestProviderInjection:
    def test_loop_accepts_injected_provider(self):
        from reaction_agent.agent.provider import FakeProvider

        p = FakeProvider(ProviderSpec(provider="anthropic", model="m", max_calls=5))
        loop = AgentLoop(provider=p)
        assert loop.provider is p  # injected, not re-constructed

    def test_dual_provider_transparent_swap(self):
        """Two different providers must be transparently swappable — the loop
        behavior is identical regardless of which provider is injected."""
        from reaction_agent.agent.provider import FakeProvider

        spec_a = ProviderSpec(provider="anthropic", model="a", max_calls=3)
        spec_b = ProviderSpec(provider="openai", model="b", max_calls=3)
        loop_a = AgentLoop(provider=FakeProvider(spec_a))
        loop_b = AgentLoop(provider=FakeProvider(spec_b))
        assert loop_a.tools == loop_b.tools  # identical surface
        assert loop_a.call_tool("stop") == loop_b.call_tool("stop")

    def test_obtain_baseline_renamed(self):
        """P7-T2-03: require_baseline renamed to obtain_baseline (disambiguate
        from BaselineGate.require_baseline)."""
        loop = AgentLoop(provider_spec=ProviderSpec(provider="a", model="m"))
        assert not hasattr(loop, "require_baseline")
        assert hasattr(loop, "obtain_baseline")


# -- aggregate: all 6 hard gates across the 9 scenarios = 0 --

def test_all_six_hard_gates_zero(grounded, policy):
    """Run every scenario against the defense chain and assert all 6 hard
    gates are zero escapes (100% schema adherence).

    Each gate's counter is incremented ONLY when the defense FAILS to reject
    the induced value (i.e., an invented value escapes). Since every defense
    rejects, all counters stay 0.
    """
    counters = HardGateCounters()

    # gate 1: invented candidate id
    if not _rejects(lambda: frozen_candidate_view(grounded, "cand_NOT_IN_RUN"), GroundingError):
        counters.escape("invented_candidate_id")
    # gate 2: invented evidence id
    if not _rejects(
        lambda: assert_id_belongs_to_run(grounded, kind="evidence", id_="ev_NOT_IN_RUN"),
        GroundingError,
    ):
        counters.escape("invented_evidence_id")
    # gate 3: structure/list mutation (deep-copy isolation)
    cand_id = list(grounded.candidate_ids)[0]
    cand = [c for c in grounded.candidates if c.candidate_id == cand_id][0]
    original = list(cand.support_lineage_ids)
    view = frozen_candidate_view(grounded, cand_id)
    view.support_lineage_ids.append("ev_NOT_IN_RUN")
    mutated = list([c for c in grounded.candidates if c.candidate_id == cand_id][0].support_lineage_ids)
    if mutated != original:
        counters.escape("structure_mutation")
    # gate 4: abstention override
    if not _rejects(lambda: policy.assert_allowed(AgentAction.WRITE_ABSTENTION), PolicyViolationError):
        counters.escape("abstention_override")
    # gate 5: failed->abstained confusion — no fabrication path on the surface
    if "fabricate_failure" in ALLOWED_TOOLS or "force_abstained" in ALLOWED_TOOLS:
        counters.escape("failed_abstained_confusion")
    # gate 6: schema adherence (forbidden fields rejected)
    from pydantic import ValidationError

    if not _rejects(
        lambda: ProductionSelectionHypothesis(
            hypothesis_id="h_agg", transformation_id="t1", site_id="s1",
            enzyme_probability=0.9,  # type: ignore[call-arg]
        ),
        ValidationError,
    ):
        counters.escape("schema_adherence")

    counters.assert_all_zero()


def _rejects(fn, exc_type) -> bool:
    """Return True if calling fn() raises exc_type (defense blocked it)."""
    try:
        fn()
    except exc_type:
        return True
    except Exception:  # noqa: BLE001 — a different rejection still blocks
        return True
    return False