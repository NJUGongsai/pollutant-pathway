"""P7 T4 grounding guard pin tests (RED first).

The grounding guard (``reaction_agent/agent/grounding.py``) enforces the
no-invention boundary at the grounding layer: the agent's claims
(``ProductionSelectionHypothesis`` + agent-selected IDs) are validated
against the TYPED baseline ``PredictionResult``.

Pins (criterion 1, per-item):
- IDs belong to run: unknown candidate/evidence/lineage/transformation/site
  id -> typed ``GroundingError``.
- structures from typed result: an invented SMILES not in the typed
  candidates -> ``GroundingError``.
- rank/lane/ledger immutable: ``GroundedRun`` is frozen; ``frozen_candidate_view``
  exposes typed rank/lane/ledger with no setter; the grounded view cannot be
  mutated to drift from the typed result.
- unsupported claims rejected: a hypothesis whose transform+site resolve but
  do not co-occur in any single typed candidate -> ``GroundingError``.
- unknown IDs -> typed error.

RED until ``grounding.py`` is implemented (ImportError); GREEN after.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from reaction_agent.adapters.p3_p4_bridge import run_deterministic_predict
from reaction_agent.schemas.hypothesis import ProductionSelectionHypothesis


@pytest.fixture(scope="module")
def baseline_result():
    return run_deterministic_predict(
        {"substrate_smiles": "CCCCCCCCO", "idempotency_key": "k_g",
         "snapshot_id": "snap_g"},
        current_run_path="/tmp/_t4_grounding_cra.json",
    )


class TestGroundedRunIDs:
    def test_build_grounded_run_id_sets_from_typed_result(self, baseline_result):
        from reaction_agent.agent.grounding import build_grounded_run

        g = build_grounded_run(baseline_result)
        assert g.run_id == baseline_result.run_id
        assert g.candidate_ids  # non-empty
        # evidence ids from stage_summary
        assert g.evidence_ids
        # lineage/transform/site ids from candidates
        assert g.lineage_ids
        assert g.transformation_ids
        assert g.site_ids
        # canonical products from typed candidates (for invention check)
        assert g.canonical_products

    def test_grounded_run_is_frozen(self, baseline_result):
        from reaction_agent.agent.grounding import build_grounded_run

        g = build_grounded_run(baseline_result)
        # Direct assignment on a frozen dataclass raises FrozenInstanceError
        # specifically (P7-T4-03: pin the exact exception, not a broad
        # Exception). Do NOT use object.__setattr__, which bypasses the
        # frozen guard.
        with pytest.raises(FrozenInstanceError):
            g.run_id = "tampered"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            g.candidate_ids = frozenset({"x"})  # type: ignore[misc]


class TestIDBelongsToRun:
    @pytest.mark.parametrize("kind", ["candidate", "evidence", "lineage", "transformation", "site"])
    def test_unknown_id_raises_typed_error(self, baseline_result, kind):
        from reaction_agent.agent.grounding import (
            GroundingError,
            assert_id_belongs_to_run,
            build_grounded_run,
        )

        g = build_grounded_run(baseline_result)
        with pytest.raises(GroundingError):
            assert_id_belongs_to_run(g, kind=kind, id_="id_does_not_exist_in_run")

    def test_known_id_passes(self, baseline_result):
        from reaction_agent.agent.grounding import (
            assert_id_belongs_to_run,
            build_grounded_run,
        )

        g = build_grounded_run(baseline_result)
        assert_id_belongs_to_run(g, kind="candidate", id_=next(iter(g.candidate_ids)))
        assert_id_belongs_to_run(g, kind="transformation", id_=next(iter(g.transformation_ids)))

    def test_evidence_fail_closed_without_stage_summary(self, baseline_result):
        """P7-T4-02: with no stage_summary, evidence_ids is empty -> any
        agent-claimed evidence id -> GroundingError (fail-closed, never a
        silent pass)."""
        from reaction_agent.agent.grounding import (
            GroundingError,
            assert_id_belongs_to_run,
            build_grounded_run,
        )

        result_no_summary = baseline_result.model_copy(update={"stage_summary": None})
        g = build_grounded_run(result_no_summary)
        assert not g.evidence_ids  # empty without stage_summary
        with pytest.raises(GroundingError):
            assert_id_belongs_to_run(g, kind="evidence", id_="ev_anything_at_all")


class TestStructureFromResult:
    def test_invented_smiles_raises(self, baseline_result):
        from reaction_agent.agent.grounding import (
            GroundingError,
            assert_structure_from_result,
            build_grounded_run,
        )

        g = build_grounded_run(baseline_result)
        with pytest.raises(GroundingError):
            assert_structure_from_result(g, "C1=CC=CC=C1C(O)N invented_smiles")

    def test_typed_smiles_passes(self, baseline_result):
        from reaction_agent.agent.grounding import (
            assert_structure_from_result,
            build_grounded_run,
        )

        g = build_grounded_run(baseline_result)
        assert_structure_from_result(g, next(iter(g.canonical_products)))


class TestValidateHypothesis:
    def _hyp(self, baseline_result, *, transformation_id, site_id,
             support_reaction_ids=None):
        return ProductionSelectionHypothesis(
            hypothesis_id="hyp_test",
            transformation_id=transformation_id,
            site_id=site_id,
            support_reaction_ids=support_reaction_ids or [],
        )

    def test_known_ids_passes(self, baseline_result):
        from reaction_agent.agent.grounding import build_grounded_run, validate_hypothesis

        g = build_grounded_run(baseline_result)
        c = baseline_result.candidates[0]
        hyp = self._hyp(
            baseline_result,
            transformation_id=c.transformation_ids[0],
            site_id=c.site_ids[0],
            support_reaction_ids=list(g.evidence_ids)[:1],
        )
        validate_hypothesis(g, hyp)  # no raise

    def test_unknown_evidence_id_raises(self, baseline_result):
        from reaction_agent.agent.grounding import (
            GroundingError,
            build_grounded_run,
            validate_hypothesis,
        )

        g = build_grounded_run(baseline_result)
        c = baseline_result.candidates[0]
        hyp = self._hyp(
            baseline_result,
            transformation_id=c.transformation_ids[0],
            site_id=c.site_ids[0],
            support_reaction_ids=["ev_invented_does_not_exist"],
        )
        with pytest.raises(GroundingError):
            validate_hypothesis(g, hyp)

    def test_unsupported_claim_raises(self):
        """P7-T4-04: transform+site both valid (in run) but never co-occurring
        in one typed candidate -> unsupported claim -> GroundingError.

        Uses a DETERMINISTIC 2-candidate fixture with disjoint transform+site
        pairs (cand A: t_a/s_a; cand B: t_b/s_b) so the cross pair t_a+s_b
        is guaranteed non-co-occurring — no conditional skip on fixture
        luck.
        """
        from reaction_agent.agent.grounding import (
            GroundingError,
            build_grounded_run,
            validate_hypothesis,
        )
        from reaction_agent.schemas.candidate import Candidate
        from reaction_agent.schemas.common import DecisionKind, Lane, ResultStatus
        from reaction_agent.schemas.result import PredictionResult

        cand_a = Candidate(
            candidate_id="c_a", canonical_product="CCO", lane=Lane.strict,
            origin="deterministic_kernel",
            transformation_ids=["t_a"], site_ids=["s_a"],
            support_lineage_ids=["lin_a"],
        )
        cand_b = Candidate(
            candidate_id="c_b", canonical_product="CCC", lane=Lane.strict,
            origin="deterministic_kernel",
            transformation_ids=["t_b"], site_ids=["s_b"],
            support_lineage_ids=["lin_b"],
        )
        result = PredictionResult(
            run_id="r_disjoint", status=ResultStatus.completed,
            decision=DecisionKind.predicted, normalized_query="CCO",
            snapshot_id="snap_disjoint", candidates=[cand_a, cand_b],
        )
        g = build_grounded_run(result)
        # cross pair: t_a (cand A) + s_b (cand B) — both valid, never co-occur.
        hyp = ProductionSelectionHypothesis(
            hypothesis_id="h_unsup", transformation_id="t_a", site_id="s_b",
        )
        with pytest.raises(GroundingError):
            validate_hypothesis(g, hyp)


class TestImmutability:
    def test_frozen_candidate_view_read_only(self, baseline_result):
        from reaction_agent.agent.grounding import (
            build_grounded_run,
            frozen_candidate_view,
        )

        g = build_grounded_run(baseline_result)
        cand_id = baseline_result.candidates[0].candidate_id
        view = frozen_candidate_view(g, cand_id)
        # Typed rank/lane/ledger exposed, matching the typed result (no drift).
        typed = baseline_result.candidates[0]
        assert view.ranking_score == typed.ranking_score
        assert view.lane == typed.lane
        assert view.support_tier == typed.support_tier
        assert view.applicability == typed.applicability
        assert view.candidate_analogy_ledger_id == typed.candidate_analogy_ledger_id

    def test_frozen_candidate_view_unknown_raises(self, baseline_result):
        from reaction_agent.agent.grounding import (
            GroundingError,
            build_grounded_run,
            frozen_candidate_view,
        )

        g = build_grounded_run(baseline_result)
        with pytest.raises(GroundingError):
            frozen_candidate_view(g, "cand_not_in_run")

    def test_no_mutation_api_for_rank_lane_ledger(self, baseline_result):
        """The grounding module exposes no setter for rank/lane/ledger."""
        from reaction_agent.agent import grounding as grounding_mod

        for forbidden in ("set_rank", "set_lane", "set_ledger",
                          "mutate_rank", "mutate_lane", "mutate_ledger",
                          "set_ranking_score", "set_support_tier"):
            assert not hasattr(grounding_mod, forbidden), (
                f"grounding must not expose mutation API {forbidden!r}"
            )


class TestImmutabilityAttackChain:
    """P7-T4-01: deep-copy isolation of the typed PredictionResult from the
    grounding view. An agent must not be able to mutate the typed result (or
    the grounded run) via list fields on a view; re-grounding after a pollution
    attempt must still reject invented IDs.

    RED on the shallow-copy HEAD (``model_copy()`` default ``deep=False``
    shares list references); GREEN after ``model_copy(deep=True)`` at both
    ``build_grounded_run`` and ``frozen_candidate_view``.
    """

    def test_view_list_append_does_not_leak_into_typed_result(self, baseline_result):
        from reaction_agent.agent.grounding import (
            build_grounded_run,
            frozen_candidate_view,
        )

        g = build_grounded_run(baseline_result)
        typed_cand = baseline_result.candidates[0]
        typed_before = list(typed_cand.transformation_ids)
        view = frozen_candidate_view(g, typed_cand.candidate_id)
        view.transformation_ids.append("t_INVENTED_by_agent")
        # typed result must be unchanged (zero drift) — deep-copy isolation.
        assert typed_cand.transformation_ids == typed_before, (
            "LEAK: view list append mutated the typed PredictionResult"
        )
        # grounded run's own candidate also unchanged.
        assert "t_INVENTED_by_agent" not in g.candidates[0].transformation_ids, (
            "LEAK: view list append mutated the grounded run's candidate"
        )

    def test_attack_chain_re_ground_still_rejects_invented_id(self, baseline_result):
        """Full attack chain: pollute the view -> re-ground from the SAME
        typed result -> validate_hypothesis with the invented id must STILL
        raise GroundingError (no bypass)."""
        from reaction_agent.agent.grounding import (
            GroundingError,
            build_grounded_run,
            frozen_candidate_view,
            validate_hypothesis,
        )

        g = build_grounded_run(baseline_result)
        typed_cand = baseline_result.candidates[0]
        view = frozen_candidate_view(g, typed_cand.candidate_id)
        invented = "t_INVENTED_by_agent"
        view.transformation_ids.append(invented)

        # re-ground from the SAME typed result (deep-copy isolation must keep
        # it unpolluted by the view's append).
        g2 = build_grounded_run(baseline_result)
        hyp = ProductionSelectionHypothesis(
            hypothesis_id="h_attack",
            transformation_id=invented,
            site_id=baseline_result.candidates[0].site_ids[0],
        )
        with pytest.raises(GroundingError):
            validate_hypothesis(g2, hyp)
