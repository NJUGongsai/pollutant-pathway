"""P4-T5 structural applicability (final_design §16.4, final_plan §7.5).

Applicability describes the structural-analogy applicability domain only
(in_domain / near_domain / out_of_domain / conflicted / unknown). It NEVER
expresses enzyme activity, feasibility, or biological probability. Without
structural evidence the label is ``unknown`` with NO_STRUCTURAL_EVIDENCE.
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash
from reaction_agent.policies.p4_decision_policy import P4_POLICY_VERSION
from reaction_agent.schemas.common import ApplicabilityLabel
from reaction_agent.schemas.p4.applicability import (
    ApplicabilityReasonCode,
    ApplicabilityAssessment,
)


def _evidence_ids(evidence_records) -> list[str]:
    out: list[str] = []
    for rec in evidence_records:
        rid = rec.reaction_id if not isinstance(rec, dict) else rec.get("reaction_id", "")
        if rid and rid not in out:
            out.append(rid)
    return out


def assess_applicability(
    candidate,
    evidence_records,
    resolution,
    structural_context: dict | None = None,
    conflicts: list[str] | None = None,
    feature_evidence_ids: dict | None = None,
) -> ApplicabilityAssessment:
    """Assess structural applicability for one candidate.

    P4-R1-G: a non-unknown label requires a verifiable structural observation
    AND non-empty evidence/path ids. A bare scalar (e.g. donor_similarity=3)
    with zero evidence can only be ``unknown``/fail-closed.
    """
    cand_id = candidate.candidate_id
    ctx = structural_context or {}
    evidence_ids = _evidence_ids(evidence_records)
    donor_evidence = list(
        (feature_evidence_ids or {}).get("donor_similarity", []) or [])

    if conflicts:
        label = ApplicabilityLabel.conflicted
        reason_codes = [ApplicabilityReasonCode.CONFLICTED_EVIDENCE]
    else:
        donor_ordinal = ctx.get("donor_similarity")
        if donor_ordinal is None:
            label = ApplicabilityLabel.unknown
            reason_codes = [ApplicabilityReasonCode.NO_STRUCTURAL_EVIDENCE]
        elif not donor_evidence:
            # A high scalar without any bound evidence is NOT a domain claim.
            label = ApplicabilityLabel.unknown
            reason_codes = [ApplicabilityReasonCode.NO_STRUCTURAL_EVIDENCE]
        elif donor_ordinal >= 2:
            label = ApplicabilityLabel.in_domain
            reason_codes = [ApplicabilityReasonCode.IN_DOMAIN_DONOR]
        elif donor_ordinal == 1:
            label = ApplicabilityLabel.near_domain
            reason_codes = [ApplicabilityReasonCode.NEAR_DOMAIN_SIMILARITY]
        else:
            label = ApplicabilityLabel.out_of_domain
            reason_codes = [ApplicabilityReasonCode.OUT_OF_DOMAIN_QUERY]

    bound_evidence = donor_evidence or evidence_ids
    assessment_hash = canonical_hash({
        "candidate_id": cand_id,
        "label": label.value,
        "reason_codes": [r.value for r in reason_codes],
        "evidence_ids": sorted(bound_evidence),
        "policy_version": P4_POLICY_VERSION,
    })

    return ApplicabilityAssessment(
        candidate_id=cand_id,
        label=label,
        reason_codes=reason_codes,
        evidence_ids=bound_evidence,
        policy_version=P4_POLICY_VERSION,
        assessment_hash=assessment_hash,
    )
