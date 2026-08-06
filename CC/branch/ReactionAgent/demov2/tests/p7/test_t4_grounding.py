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
        # (do NOT use object.__setattr__, which bypasses the frozen guard).
        with pytest.raises(Exception):
            g.run_id = "tampered"  # type: ignore[misc]
        with pytest.raises(Exception):
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

    def test_unsupported_claim_raises(self, baseline_result):
        """transform + site both valid (in run) but never co-occurring in one
        typed candidate -> unsupported claim -> GroundingError."""
        from reaction_agent.agent.grounding import (
            GroundingError,
            build_grounded_run,
            validate_hypothesis,
        )

        if len(baseline_result.candidates) < 2:
            pytest.skip("need >=2 candidates for cross co-occurrence test")
        c0 = baseline_result.candidates[0]
        c1 = baseline_result.candidates[1]
        # cross: c0's transform + c1's site (presumably non-co-occurring)
        hyp = self._hyp(
            baseline_result,
            transformation_id=c0.transformation_ids[0],
            site_id=c1.site_ids[0],
        )
        g = build_grounded_run(baseline_result)
        # Only raise if they truly don't co-occur; otherwise skip (honest).
        co_occur = any(
            c0.transformation_ids[0] in c.transformation_ids
            and c1.site_ids[0] in c.site_ids
            for c in baseline_result.candidates
        )
        if co_occur:
            pytest.skip("fixture candidates share transform+site; cannot form unsupported claim")
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
