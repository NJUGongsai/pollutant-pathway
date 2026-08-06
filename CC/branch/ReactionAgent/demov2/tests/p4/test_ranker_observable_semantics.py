"""P4-R1-I RED→GREEN: the ranker score is a weighted average over OBSERVABLE
features only.

An unobservable feature must NOT dilute the score (it is not 0). The
denominator is the sum of the weights of the observable features; a fully
unobservable candidate scores 0; conflict_penalty is subtracted and never
participates in the denominator.
"""
from __future__ import annotations

import pytest

from tests.fixtures.p4.p4_contract_fixture import (
    build_strict_candidate,
)
from reaction_agent.policies.p4_decision_policy import RANKING_FEATURES
from reaction_agent.schemas.p4.observation import FeatureObservation
from reaction_agent.schemas.common import Lane
from reaction_agent.inference.ranker import rank_strict_candidates


def _obs(key: str, ordinal: int | None) -> FeatureObservation:
    return FeatureObservation(feature_key=key, ordinal=ordinal)


def _vector(overrides: dict | None = None, observable: int = 3) -> dict:
    """A vector where every structural feature is observable with the same
    ordinal, unless overridden to None. conflict_penalty defaults to 0 (no
    conflict) and is only raised by an explicit override."""
    vec = {}
    for k in RANKING_FEATURES:
        if k == "conflict_penalty":
            vec[k] = _obs(k, 0)
        else:
            vec[k] = _obs(k, observable)
    for k, v in (overrides or {}).items():
        vec[k] = _obs(k, v)
    return vec


def _cand(cid="cand_ox_001") -> "object":
    return build_strict_candidate()


class TestObservableOnlySemantics:
    def test_all_observable_same_ordinal_scores_full(self):
        """All features observable at ordinal 3 => score 1.0 (minus the
        conflict penalty, which is 0 with no conflicts)."""
        vec = _vector()
        ranked = rank_strict_candidates([_cand()], {_cand().candidate_id: vec},
                                        policy_version="p4-policy-1")
        assert ranked.candidates[0].ranking_score == pytest.approx(1.0, abs=1e-6)

    def test_unobservable_feature_does_not_dilute_score(self):
        """Making one feature unobservable must NOT dilute the score — the
        average is over observable features only."""
        full = _vector()
        partial = _vector(overrides={"retrieval_stability": None})
        r_full = rank_strict_candidates([_cand()],
                                        {_cand().candidate_id: full},
                                        policy_version="p4-policy-1")
        r_partial = rank_strict_candidates([_cand()],
                                           {_cand().candidate_id: partial},
                                           policy_version="p4-policy-1")
        s_full = r_full.candidates[0].ranking_score
        s_partial = r_partial.candidates[0].ranking_score
        assert s_partial == pytest.approx(s_full, abs=1e-6), \
            "unobservable feature must not dilute the observable average"

    def test_low_observable_ordinal_drops_score(self):
        """Ordinal 1 on one observable feature lowers the average."""
        vec = _vector(overrides={"donor_similarity": 1})
        ranked = rank_strict_candidates([_cand()], {_cand().candidate_id: vec},
                                        policy_version="p4-policy-1")
        assert ranked.candidates[0].ranking_score < 1.0

    def test_fully_unobservable_scores_zero(self):
        """A candidate with no observable features scores 0 (never ranked)."""
        vec = _vector(observable=None)
        ranked = rank_strict_candidates([_cand()], {_cand().candidate_id: vec},
                                        policy_version="p4-policy-1")
        assert ranked.candidates[0].ranking_score == 0.0

    def test_conflict_penalty_subtracted_not_in_denominator(self):
        """A strong conflict subtracts the penalty weight but is not part of
        the observable-feature denominator."""
        vec = _vector()  # all 3, no conflict
        vec_penalty = _vector(overrides={"conflict_penalty": 3})
        r0 = rank_strict_candidates([_cand()], {_cand().candidate_id: vec},
                                    policy_version="p4-policy-1")
        r1 = rank_strict_candidates([_cand()], {_cand().candidate_id: vec_penalty},
                                    policy_version="p4-policy-1")
        s0 = r0.candidates[0].ranking_score
        s1 = r1.candidates[0].ranking_score
        assert s1 < s0
        # penalty is the normalized conflict weight * (3/3), not a full point.
        from reaction_agent.policies.p4_decision_policy import RANKER_WEIGHTS
        norm_penalty = RANKER_WEIGHTS["conflict_penalty"] / sum(RANKER_WEIGHTS.values())
        assert s0 - s1 == pytest.approx(norm_penalty, abs=1e-6)