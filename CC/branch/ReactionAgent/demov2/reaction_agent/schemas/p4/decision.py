"""P4 decision schemas (final_design §15.3, §15.4, §18.3, §22.5).

The versioned decision policy (p4_decision_policy.py) is the sole authority
for decision/status/reason_code/rank/lane/validation/applicability. Agent
text must never override these structured fields.

System failures are ``failed`` and are NEVER converted to scientific
abstention.

``P4CapabilityStatus`` carries a frozen ``P4Classification`` (never a free
string) and enforces cross-field invariants: ``classification=real`` requires
a verified P3 current-run artifact, real evidence, the correct namespace and
the P2 truth authority — none of which can be fabricated by a caller.
"""
from __future__ import annotations

from pydantic import model_validator

from reaction_agent.schemas.common import (
    StrictModel,
    NonEmptyStr,
    ResultStatus,
    DecisionKind,
    ScientificAbstentionReason,
    SystemFailureReason,
)
from reaction_agent.schemas.result import StageSummary
from reaction_agent.schemas.p4.ranking import RankedStrictCandidate
from reaction_agent.schemas.p4.applicability import ApplicabilityAssessment
from reaction_agent.schemas.p4.authority import P4Classification


class AbstentionDecision(StrictModel):
    """Typed scientific abstention with frozen precedence primary reason."""
    decision: DecisionKind = DecisionKind.abstained
    reason_code: ScientificAbstentionReason
    primary_reason: NonEmptyStr
    secondary_reasons: list[NonEmptyStr] = []
    candidate_count: int = 0
    trace: StageSummary
    policy_version: NonEmptyStr
    source_evidence_scope: str


class PredictionDecision(StrictModel):
    """Structured policy decision consumed by the PredictionResult adapter.

    ``reason_code`` is either a ScientificAbstentionReason (abstained) or a
    SystemFailureReason (failed). For completed, it is empty.
    """
    decision: DecisionKind
    status: ResultStatus
    reason_code: str = ""
    reason_detail: str = ""
    ranked_candidates: list[RankedStrictCandidate] = []
    applicability: ApplicabilityAssessment | None = None
    abstention: AbstentionDecision | None = None
    trace: StageSummary | None = None
    policy_version: NonEmptyStr
    lane: str = "strict"


class P4CapabilityStatus(StrictModel):
    """P4 capability + blocked status classification.

    ``classification`` is a frozen ``P4Classification`` enum. Every P4 output
    must carry this so real vs fixture evidence is never conflated. This
    struct describes capability state; it is NOT an authority handle — the
    pipeline consumes ``P3AuthorityHandle`` instead.
    """
    capability_available: bool
    p3_interface_manifest_present: bool
    real_evidence_available: bool
    p2_truth_authority_available: bool
    classification: P4Classification
    blocked_reasons: list[NonEmptyStr] = []

    @model_validator(mode="after")
    def _cross_field_invariants(self) -> "P4CapabilityStatus":
        c = self.classification
        if c == P4Classification.real:
            if not (self.capability_available
                    and self.p3_interface_manifest_present
                    and self.real_evidence_available
                    and self.p2_truth_authority_available):
                raise ValueError(
                    "classification=real requires verified P3 current-run "
                    "artifact + real evidence + correct namespace + P2 "
                    "truth authority (capability_available="
                    f"{self.capability_available}, "
                    f"p3_present={self.p3_interface_manifest_present}, "
                    f"real_evidence={self.real_evidence_available}, "
                    f"p2_authority={self.p2_truth_authority_available})")
        elif c == P4Classification.synthetic_fixture:
            if self.real_evidence_available:
                raise ValueError(
                    "synthetic_fixture cannot be real_evidence_available=True")
        elif c == P4Classification.blocked:
            if self.capability_available:
                raise ValueError(
                    "blocked classification cannot have capability_available=True")
        return self