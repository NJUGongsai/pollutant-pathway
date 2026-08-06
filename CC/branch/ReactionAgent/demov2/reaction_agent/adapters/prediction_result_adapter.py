"""P4-T7 PredictionResult adapter (final_design §22.5, ADR-0005).

Reuses the P1 shared ``PredictionResult`` schema — P4 does NOT define a
synonymous schema. The adapter enforces:

- decision authority: status/decision/reason_code/rank/lane/validation/
  applicability come only from the versioned decision policy; agent text may
  explain but never override these fields;
- completed => >=1 validated strict candidate, no abstention;
- abstained => 0 candidates + scientific reason;
- partial => partial_reason;
- failed => system failure only, NEVER a scientific abstention;
- forbidden probability/confidence fields are rejected.
"""
from __future__ import annotations

from reaction_agent.schemas.common import (
    NonEmptyStr,
    ResultStatus,
    DecisionKind,
    SystemFailureReason,
    ScientificAbstentionReason,
    FORBIDDEN_FIELD_NAMES,
)
from reaction_agent.schemas.result import (
    PredictionResult,
    Abstention,
    Failure,
    StageSummary,
)
from reaction_agent.schemas.candidate import Candidate
from reaction_agent.schemas.common import Lane, ApplicabilityLabel
from reaction_agent.schemas.p4.decision import PredictionDecision

# Fields ONLY the versioned decision policy may set (ADR-0005).
AUTHORITY_FIELDS = frozenset({
    "status", "decision", "reason_code", "rank", "lane", "validation",
    "applicability",
})


class DecisionAuthorityError(ValueError):
    """Agent text or unstructured input attempted to override a policy field."""


class CandidateProvenanceError(ValueError):
    """A ranked candidate is not backed by a verified P3 candidate — P4 never
    fabricates candidates from ranking records (P4-R1-C)."""


class PredictionResultAdapter:
    """Validates a PredictionDecision and builds the shared PredictionResult."""

    def __init__(self, policy_version: str):
        self.policy_version = policy_version

    def validate_and_build(
        self,
        decision: PredictionDecision,
        agent_text: dict | None = None,
        candidate_map: dict[str, Candidate] | None = None,
        extra_structured: dict | None = None,
        run_id: str = "run_p4",
        snapshot_id: str = "snap_p4",
        normalized_query: str = "query",
    ) -> PredictionResult:
        self._reject_forbidden_fields(extra_structured or {})
        self._assert_no_authority_override(agent_text or {})
        self._assert_system_failure_not_abstention(decision)
        self._assert_reason_consistency(decision)

        candidates = self._build_candidates(decision, candidate_map or {})
        abstention = self._build_abstention(decision)
        failure = self._build_failure(decision)
        partial_reason = (
            decision.reason_detail or None
            if decision.status == ResultStatus.partial else None
        )
        if decision.abstention is not None:
            stage_summary = decision.abstention.trace
        elif decision.trace is not None:
            stage_summary = decision.trace
        else:
            stage_summary = StageSummary(
                donor_evidence_ids=[],
                candidate_ids=[c.candidate_id for c in decision.ranked_candidates],
            )

        manifest_uri = f"reactionagent://runs/{run_id}/manifest"
        resource_uris = [f"reactionagent://runs/{run_id}"] + [
            f"reactionagent://runs/{run_id}/candidates/{c.candidate_id}"
            for c in decision.ranked_candidates
        ]

        return PredictionResult(
            run_id=run_id,
            status=decision.status,
            decision=decision.decision,
            normalized_query=normalized_query,
            snapshot_id=snapshot_id,
            candidates=candidates,
            abstention=abstention,
            partial_reason=partial_reason,
            failure=failure,
            stage_summary=stage_summary,
            manifest_uri=manifest_uri,
            resource_uris=resource_uris,
        )

    # -- internal helpers ------------------------------------------------

    def _reject_forbidden_fields(self, structured: dict) -> None:
        from reaction_agent.policies.p4_decision_policy import (
            FORBIDDEN_PROBABILITY_FIELDS)
        forbidden = FORBIDDEN_FIELD_NAMES | FORBIDDEN_PROBABILITY_FIELDS
        for key in structured:
            if key in forbidden:
                raise ValueError(
                    f"forbidden probability/confidence field: {key!r}")

    def _assert_no_authority_override(self, agent_text: dict) -> None:
        overlap = AUTHORITY_FIELDS & set(agent_text.keys())
        if overlap:
            raise DecisionAuthorityError(
                f"agent text attempted to override authority field(s): "
                f"{sorted(overlap)}")

    def _assert_system_failure_not_abstention(self, decision: PredictionDecision) -> None:
        sys_reasons = {r.value for r in SystemFailureReason}
        if decision.reason_code in sys_reasons and decision.status != ResultStatus.failed:
            raise DecisionAuthorityError(
                f"system failure {decision.reason_code!r} cannot be reported as "
                f"scientific {decision.status.value}")

    def _assert_reason_consistency(self, decision: PredictionDecision) -> None:
        if decision.status == ResultStatus.abstained:
            if decision.abstention is None:
                raise ValueError("abstained decision requires an AbstentionDecision")
            if decision.reason_code and decision.reason_code not in {
                    r.value for r in ScientificAbstentionReason}:
                raise ValueError(
                    f"abstained decision reason_code must be scientific: "
                    f"{decision.reason_code!r}")
        if decision.status == ResultStatus.failed:
            if decision.reason_code not in {r.value for r in SystemFailureReason}:
                raise ValueError(
                    f"failed decision requires a system failure reason: "
                    f"{decision.reason_code!r}")

    def _build_candidates(self, decision: PredictionDecision,
                          candidate_map: dict) -> list[Candidate]:
        """Build the ranked candidate list from the VERIFIED P3 candidate map.

        P4-R1-C: P4 never constructs a fallback Candidate. Every ranked
        candidate must exist exactly in ``candidate_map`` with a matching
        candidate id, canonical product identity, strict lane and a non-empty
        validation verdict. Any absence or mismatch raises
        ``CandidateProvenanceError`` (the caller turns it into a typed
        FAIL/BLOCKED — never a silently fabricated candidate).
        """
        if decision.status != ResultStatus.completed:
            return []
        candidates: list[Candidate] = []
        for rc in decision.ranked_candidates:
            base = candidate_map.get(rc.candidate_id)
            if base is None:
                raise CandidateProvenanceError(
                    f"ranked candidate {rc.candidate_id!r} is not present in "
                    f"the verified P3 candidate map")
            if base.canonical_product != rc.canonical_product:
                raise CandidateProvenanceError(
                    f"ranked candidate {rc.candidate_id!r} canonical product "
                    f"mismatch: map={base.canonical_product!r} "
                    f"ranked={rc.canonical_product!r}")
            if base.lane != Lane.strict:
                raise CandidateProvenanceError(
                    f"ranked candidate {rc.candidate_id!r} lane={base.lane.value!r} "
                    f"is not strict")
            if not base.validation:
                raise CandidateProvenanceError(
                    f"ranked candidate {rc.candidate_id!r} has empty validation")
            if base.validation.get("valid_molecule") is False:
                raise CandidateProvenanceError(
                    f"ranked candidate {rc.candidate_id!r} failed validation "
                    f"(valid_molecule=False)")
            candidates.append(Candidate(
                **{
                    **base.model_dump(mode="json"),
                    "ranking_score": rc.ranking_score,
                    "lane": Lane.strict,
                    # per-candidate applicability if present, else the
                    # single decision-level assessment, else unknown.
                    "applicability": (
                        base.applicability
                        if base.applicability is not None
                        else self._applicability_for(decision, rc.candidate_id)),
                    "provenance": base.provenance + ["p4:ranked"],
                }))
        return candidates

    def _applicability_for(self, decision: PredictionDecision,
                           candidate_id: str) -> ApplicabilityLabel:
        if decision.applicability is not None and \
                decision.applicability.candidate_id == candidate_id:
            return decision.applicability.label
        return ApplicabilityLabel.unknown

    def _build_abstention(self, decision: PredictionDecision) -> Abstention | None:
        if decision.abstention is None:
            return None
        return Abstention(
            reason_code=decision.abstention.reason_code,
            stage="decided",
            detail=decision.abstention.primary_reason,
        )

    def _build_failure(self, decision: PredictionDecision) -> Failure | None:
        if decision.status != ResultStatus.failed:
            return None
        return Failure(
            reason_code=SystemFailureReason(decision.reason_code),
            detail=decision.reason_detail,
        )
