"""P4-R1-C RED→GREEN: the PredictionResult adapter must never construct a
fallback Candidate. Every ranked candidate must exist EXACTLY in the verified
P3 candidate map with matching identity/product/lane/validation; any absence
or mismatch is a typed rejection, never a silent fabrication.
"""
from __future__ import annotations

import pytest

from tests.fixtures.p4.p4_contract_fixture import (
    build_strict_candidate,
    POLICY_VERSION,
)
from reaction_agent.schemas.common import (
    DecisionKind,
    ResultStatus,
    Lane,
)
from reaction_agent.schemas.candidate import Candidate
from reaction_agent.schemas.p4.decision import PredictionDecision
from reaction_agent.schemas.p4.ranking import RankedStrictCandidate
from reaction_agent.adapters.prediction_result_adapter import (
    PredictionResultAdapter,
)


def _ranked(candidate_id="cand_ox_001", canonical_product="CC=O",
            score=0.8) -> RankedStrictCandidate:
    return RankedStrictCandidate(
        candidate_id=candidate_id,
        canonical_product=canonical_product,
        lane=Lane.strict,
        ranking_score=score,
        rank=1,
        contributions=[],
        tie_break_key="tb",
        ranker_version="p4-ranker-1",
    )


def _completed_decision(ranked: list[RankedStrictCandidate]) -> PredictionDecision:
    return PredictionDecision(
        decision=DecisionKind.predicted,
        status=ResultStatus.completed,
        ranked_candidates=ranked,
        policy_version=POLICY_VERSION,
    )


def _adapter() -> PredictionResultAdapter:
    return PredictionResultAdapter(policy_version=POLICY_VERSION)


class TestCandidateProvenance:
    def test_empty_candidate_map_is_rejected(self):
        """completed with zero verified P3 candidates must be rejected — the
        adapter must NOT fabricate a fallback Candidate (P4-R1-C)."""
        candidate_map = {}
        decision = _completed_decision([_ranked()])
        with pytest.raises(Exception):
            _adapter().validate_and_build(decision, candidate_map=candidate_map)

    def test_ranked_id_not_in_candidate_map_is_rejected(self):
        """A ranked candidate whose ID is absent from the verified P3 map is
        rejected (no invention from the ranking record)."""
        candidate_map = {"other_candidate": build_strict_candidate()}
        decision = _completed_decision([_ranked(candidate_id="ghost")])
        with pytest.raises(Exception):
            _adapter().validate_and_build(decision, candidate_map=candidate_map)

    def test_canonical_product_mismatch_is_rejected(self):
        """The map's candidate and the ranked record must agree on the
        canonical product identity; a mismatch is rejected."""
        cand = build_strict_candidate()
        cand = cand.model_copy(update={"canonical_product": "CC=O"})
        # ranked claims a different product
        decision = _completed_decision([_ranked(canonical_product="CCO")])
        with pytest.raises(Exception):
            _adapter().validate_and_build(decision, candidate_map={cand.candidate_id: cand})

    def test_empty_validation_is_rejected(self):
        """A candidate with empty validation cannot be used as provenance."""
        cand = build_strict_candidate().model_copy(update={"validation": {}})
        decision = _completed_decision([_ranked()])
        with pytest.raises(Exception):
            _adapter().validate_and_build(decision, candidate_map={cand.candidate_id: cand})

    def test_failed_validation_is_rejected(self):
        """A candidate whose validation says invalid_molecule is rejected."""
        cand = build_strict_candidate().model_copy(update={
            "validation": {"valid_molecule": False}})
        decision = _completed_decision([_ranked()])
        with pytest.raises(Exception):
            _adapter().validate_and_build(decision, candidate_map={cand.candidate_id: cand})

    def test_non_strict_lane_is_rejected(self):
        """A generalized/agent_proposed candidate cannot be ranked as strict."""
        cand = build_strict_candidate().model_copy(update={"lane": Lane.generalized})
        decision = _completed_decision([_ranked()])
        with pytest.raises(Exception):
            _adapter().validate_and_build(decision, candidate_map={cand.candidate_id: cand})

    def test_exact_match_builds_without_fabrication(self):
        """The happy path: the ranked candidate exists in the map with the
        exact identity/product/validation; the result reuses the P3 candidate
        (no invented fields, no fallback)."""
        cand = build_strict_candidate()
        decision = _completed_decision([_ranked(candidate_id=cand.candidate_id)])
        result = _adapter().validate_and_build(
            decision, candidate_map={cand.candidate_id: cand})
        assert len(result.candidates) == 1
        out = result.candidates[0]
        assert out.candidate_id == cand.candidate_id
        assert out.canonical_product == cand.canonical_product
        # provenance is extended, never replaced by an invented origin
        assert "p4:ranked" in out.provenance
        assert out.origin == cand.origin  # origin preserved, not invented