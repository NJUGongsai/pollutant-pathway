"""P4 strict ranking schemas (final_design §18.1, §18.2, final_plan §7.4).

Strict lane only. ``ranking_score`` is an ordinal/relative selection score,
NEVER a probability or confidence. Tie-break is deterministic. Different
lanes are never mixed horizontally (generalized / agent_proposed do not enter
strict production ranking).
"""
from __future__ import annotations

from reaction_agent.schemas.common import StrictModel, NonEmptyStr, Lane


class FeatureContribution(StrictModel):
    """Per-feature contribution to the ranking score."""
    feature_key: NonEmptyStr
    weight: float
    ordinal_score: int | None
    contribution: float


class RankedStrictCandidate(StrictModel):
    """A ranked strict candidate (rank is ordinal, not probability)."""
    candidate_id: NonEmptyStr
    canonical_product: NonEmptyStr
    lane: Lane
    ranking_score: float
    rank: int
    contributions: list[FeatureContribution]
    tie_break_key: NonEmptyStr
    ranker_version: NonEmptyStr


class RankingResult(StrictModel):
    """Deterministic ranking result over strict candidates."""
    candidates: list[RankedStrictCandidate]
    ranker_version: NonEmptyStr
    policy_version: NonEmptyStr
    ranking_hash: NonEmptyStr
