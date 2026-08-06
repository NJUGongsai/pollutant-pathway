"""P4-T4 strict-only deterministic baseline ranker (final_design §18.1, §18.2).

Strict lane only. generalized / agent_proposed candidates never enter strict
production ranking. ranking_score is a weighted ordinal aggregate in [0,1]
with deterministic tie-break (ascending tie_break_key). It is an
ordinal/relative selection score, NEVER a probability or confidence.
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash
from reaction_agent.policies.p4_decision_policy import (
    P4_POLICY_VERSION,
    RANKING_FEATURES,
    RANKER_WEIGHTS,
)
from reaction_agent.schemas.common import Lane
from reaction_agent.schemas.p4.ranking import (
    FeatureContribution,
    RankedStrictCandidate,
    RankingResult,
)

RANKER_VERSION = "p4-ranker-1"

# Frozen baseline weights are normalized so they form a true weighted average
# (sum to 1.0) over observable features.
_TOTAL_WEIGHT = sum(RANKER_WEIGHTS.values())


def _norm_weight(key: str) -> float:
    return RANKER_WEIGHTS[key] / _TOTAL_WEIGHT


def _assert_all_strict(candidates) -> None:
    for c in candidates:
        lane = c.lane if hasattr(c, "lane") else c.get("lane")
        if lane != Lane.strict:
            raise ValueError(
                f"candidate {getattr(c, 'candidate_id', '?')} lane={lane!r} "
                f"is not strict; strict ranking must not mix lanes")


def _score_candidate(candidate, vector: dict) -> tuple[list[FeatureContribution], float]:
    """Score = weighted average over OBSERVABLE positive features (P4-R1-I).

    The denominator is the sum of the normalized weights of the observable
    positive features — an unobservable feature does NOT dilute the score.
    conflict_penalty is subtracted (never part of the denominator).
    """
    contributions: list[FeatureContribution] = []
    score = 0.0
    positive = [k for k in RANKING_FEATURES if k != "conflict_penalty"]
    observable = [
        k for k in positive
        if (v := vector.get(k)) is not None and v.ordinal is not None
    ]
    denominator = sum(_norm_weight(k) for k in observable)
    for key in RANKING_FEATURES:
        weight = _norm_weight(key)
        obs = vector.get(key)
        ordinal = obs.ordinal if obs is not None else None
        is_observable = ordinal is not None
        if key == "conflict_penalty":
            # Penalty is subtracted: strong conflict (3) subtracts weight.
            penalty_ordinal = ordinal if is_observable else 0
            contribution = -weight * (penalty_ordinal / 3.0)
            contributions.append(FeatureContribution(
                feature_key=key, weight=weight,
                ordinal_score=ordinal if is_observable else None,
                contribution=round(contribution, 6)))
            score += contribution
        elif is_observable and denominator > 0:
            contribution = weight * (ordinal / 3.0) / denominator
            contributions.append(FeatureContribution(
                feature_key=key, weight=weight,
                ordinal_score=ordinal, contribution=round(contribution, 6)))
            score += contribution
        else:
            contributions.append(FeatureContribution(
                feature_key=key, weight=weight,
                ordinal_score=None, contribution=0.0))
    return contributions, round(min(max(score, 0.0), 1.0), 6)


def _tie_break_key(candidate) -> str:
    return canonical_hash({
        "candidate_id": getattr(candidate, "candidate_id", ""),
        "canonical_product": getattr(candidate, "canonical_product", ""),
    })


def rank_strict_candidates(
    candidates,
    feature_vectors: dict,
    policy_version: str,
) -> RankingResult:
    """Deterministically rank a strict-only candidate set."""
    _assert_all_strict(candidates)

    ranked: list[RankedStrictCandidate] = []
    for c in candidates:
        cand_id = getattr(c, "candidate_id", "")
        vector = feature_vectors.get(cand_id, {})
        contributions, score = _score_candidate(c, vector)
        ranked.append(RankedStrictCandidate(
            candidate_id=cand_id,
            canonical_product=getattr(c, "canonical_product", ""),
            lane=Lane.strict,
            ranking_score=score,
            rank=0,  # assigned below
            contributions=contributions,
            tie_break_key=_tie_break_key(c),
            ranker_version=RANKER_VERSION,
        ))

    # Deterministic ordering: score desc, then tie_break_key asc.
    ranked.sort(key=lambda rc: (-rc.ranking_score, rc.tie_break_key))
    for pos, rc in enumerate(ranked, start=1):
        # frozen copy of the RankedStrictCandidate with the assigned rank
        ranked[pos - 1] = rc.model_copy(update={"rank": pos})

    ranking_hash = canonical_hash({
        "policy_version": policy_version,
        "ranker_version": RANKER_VERSION,
        "candidates": [
            {"candidate_id": rc.candidate_id, "score": rc.ranking_score,
             "rank": rc.rank, "tie_break_key": rc.tie_break_key}
            for rc in ranked
        ],
    })

    return RankingResult(
        candidates=ranked,
        ranker_version=RANKER_VERSION,
        policy_version=policy_version,
        ranking_hash=ranking_hash,
    )
