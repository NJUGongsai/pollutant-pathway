"""P4 schemas (evidence identity, support, counterevidence, ranking,
applicability, decision, immutable run).

P4 schemas live in their own subpackage so the shared ``schemas/__init__.py``
(P0/P1 owned) is never modified. They reuse the P0/P1 frozen primitives
(``StrictModel``, ``ScientificAbstentionReason``, ``SystemFailureReason``,
``Lane``, ``ApplicabilityLabel``, ``StageSummary``, ``PredictionResult``).
"""
from __future__ import annotations

from reaction_agent.schemas.p4.evidence import (
    DedupDimension,
    EvidenceIdentity,
    IndependentGroup,
    EvidenceIdentityResolution,
)
from reaction_agent.schemas.p4.support import (
    SupportTier,
    EvidenceStrength,
    SupportFeature,
    SupportBreakdown,
)
from reaction_agent.schemas.p4.counterevidence import (
    CounterevidenceType,
    CounterevidenceRecord,
    CounterevidenceCollection,
)
from reaction_agent.schemas.p4.ranking import (
    FeatureContribution,
    RankedStrictCandidate,
    RankingResult,
)
from reaction_agent.schemas.p4.applicability import (
    ApplicabilityReasonCode,
    ApplicabilityAssessment,
)
from reaction_agent.schemas.p4.decision import (
    AbstentionDecision,
    PredictionDecision,
    P4CapabilityStatus,
)
from reaction_agent.schemas.p4.run import (
    RunFreezeState,
    ComponentVersions,
    ImmutableRunManifest,
)

__all__ = [
    "DedupDimension",
    "EvidenceIdentity",
    "IndependentGroup",
    "EvidenceIdentityResolution",
    "SupportTier",
    "EvidenceStrength",
    "SupportFeature",
    "SupportBreakdown",
    "CounterevidenceType",
    "CounterevidenceRecord",
    "CounterevidenceCollection",
    "FeatureContribution",
    "RankedStrictCandidate",
    "RankingResult",
    "ApplicabilityReasonCode",
    "ApplicabilityAssessment",
    "AbstentionDecision",
    "PredictionDecision",
    "P4CapabilityStatus",
    "RunFreezeState",
    "ComponentVersions",
    "ImmutableRunManifest",
]
