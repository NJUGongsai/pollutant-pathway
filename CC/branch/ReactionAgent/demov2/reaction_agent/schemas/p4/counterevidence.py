"""P4 counterevidence schemas (final_design §16.2, §16.3, final_plan §7.3).

First-version counterevidence is restricted to the allowed typed reasons in
p4_decision_policy.py. database absence, "no second enzyme found", similar
molecule not covered, source not reporting negative, and low frequency are
NEVER negative evidence — they are only "not observed / unknown".
"""
from __future__ import annotations

from enum import Enum
from reaction_agent.schemas.common import StrictModel, NonEmptyStr


class CounterevidenceType(str, Enum):
    """Allowed counterevidence types (final_design §16.2)."""
    COMPETING_TRANSFORM = "COMPETING_TRANSFORM"
    FAILED_TRANSFORM_PRECONDITIONS = "FAILED_TRANSFORM_PRECONDITIONS"
    SITE_INCOMPATIBILITY = "SITE_INCOMPATIBILITY"
    INVALID_GENERATION = "INVALID_GENERATION"
    LEDGER_CONTRADICTION = "LEDGER_CONTRADICTION"
    PROVENANCE_DIRECTION_ROLE_CONFLICT = "PROVENANCE_DIRECTION_ROLE_CONFLICT"
    STRICT_FAILURE_ONLY_RELAXATION = "STRICT_FAILURE_ONLY_RELAXATION"
    ALL_SUPPORT_LOW_QUALITY_OR_SAME_SOURCE = "ALL_SUPPORT_LOW_QUALITY_OR_SAME_SOURCE"


class CounterevidenceRecord(StrictModel):
    """One typed counterevidence record bound to evidence IDs."""
    record_id: NonEmptyStr
    evidence_ids: list[NonEmptyStr]
    source_identity: str
    scope: str
    counter_type: CounterevidenceType
    policy_version: NonEmptyStr
    detail: str = ""


class CounterevidenceCollection(StrictModel):
    """Counterevidence collected for a candidate/transform context."""
    candidate_id: NonEmptyStr
    records: list[CounterevidenceRecord]
    has_conflict: bool
    policy_version: NonEmptyStr
