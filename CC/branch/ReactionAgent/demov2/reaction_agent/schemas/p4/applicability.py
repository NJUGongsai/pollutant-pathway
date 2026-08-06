"""P4 structural applicability schemas (final_design §16.4, final_plan §7.5).

Applicability describes the structural-analogy applicability domain only,
never enzyme activity, feasibility or biological probability. Each label must
carry structural reason codes and the evidence it was derived from.
"""
from __future__ import annotations

from enum import Enum
from reaction_agent.schemas.common import (
    StrictModel,
    NonEmptyStr,
    ApplicabilityLabel,
)


class ApplicabilityReasonCode(str, Enum):
    """Structural reason codes for applicability (P4 deliverable)."""
    IN_DOMAIN_DONOR = "IN_DOMAIN_DONOR"
    NEAR_DOMAIN_SIMILARITY = "NEAR_DOMAIN_SIMILARITY"
    OUT_OF_DOMAIN_QUERY = "OUT_OF_DOMAIN_QUERY"
    CONFLICTED_EVIDENCE = "CONFLICTED_EVIDENCE"
    NO_STRUCTURAL_EVIDENCE = "NO_STRUCTURAL_EVIDENCE"


class ApplicabilityAssessment(StrictModel):
    """Structural-only applicability assessment for a candidate."""
    candidate_id: NonEmptyStr
    label: ApplicabilityLabel
    reason_codes: list[ApplicabilityReasonCode]
    evidence_ids: list[NonEmptyStr]
    policy_version: NonEmptyStr
    assessment_hash: NonEmptyStr
