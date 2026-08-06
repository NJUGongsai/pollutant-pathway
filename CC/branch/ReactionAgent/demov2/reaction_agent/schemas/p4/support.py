"""P4 support aggregation schemas (final_design §16.1, final_plan §7.2).

Support features must bind evidence IDs individually. The output is an
explainable weighted/ordinal support breakdown. It is NOT a probability and
NOT a confidence: ``support_tier`` and ``evidence_strength`` are ordinal
vocabularies frozen by the P4 decision policy (p4_decision_policy.py).

Empty evidence must not automatically become support: a feature with no
evidence IDs is ``is_observable=False`` and contributes no support.
"""
from __future__ import annotations

from enum import Enum
from reaction_agent.schemas.common import StrictModel, NonEmptyStr


class SupportTier(str, Enum):
    """Ordinal support tier (P4 deliverable; NOT a probability)."""
    none = "none"
    weak = "weak"
    moderate = "moderate"
    strong = "strong"


class EvidenceStrength(str, Enum):
    """Ordinal evidence strength (P4 deliverable; NOT a probability)."""
    none = "none"
    single_source = "single_source"
    multiple_independent_sources = "multiple_independent_sources"
    high_quality_multiple_independent = "high_quality_multiple_independent"


class SupportFeature(StrictModel):
    """A single support feature bound to evidence IDs.

    ``ordinal_score`` is 0..3 (None when not observable). Every feature must
    reference the evidence IDs it was derived from.
    """
    feature_key: NonEmptyStr
    evidence_ids: list[NonEmptyStr] = []
    ordinal_score: int | None = None
    is_observable: bool = False
    reason: str = ""


class SupportBreakdown(StrictModel):
    """Support aggregation for one strict candidate."""
    candidate_id: NonEmptyStr
    features: list[SupportFeature]
    support_tier: SupportTier
    evidence_strength: EvidenceStrength
    independent_evidence_count: int
    all_evidence_ids: list[NonEmptyStr]
    policy_version: NonEmptyStr
    breakdown_hash: NonEmptyStr
