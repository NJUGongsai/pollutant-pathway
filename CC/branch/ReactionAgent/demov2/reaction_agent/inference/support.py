"""P4-T2 support aggregation (final_design §16.1, final_plan §7.2).

Every support feature binds evidence IDs. The output is an explainable
ordinal support breakdown; ``support_tier`` and ``evidence_strength`` are
ordinal vocabularies, NOT probabilities/confidences. Empty evidence never
becomes support (unobservable features are flagged, not silently supported).
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash
from reaction_agent.policies.p4_decision_policy import (
    P4_POLICY_VERSION,
    SUPPORT_FEATURES,
    SUPPORT_TIER_ORDINAL,
    EVIDENCE_STRENGTH_ORDINAL,
)
from reaction_agent.schemas.p4.support import (
    SupportTier,
    EvidenceStrength,
    SupportFeature,
    SupportBreakdown,
)
from reaction_agent.inference.features import build_support_feature_vector


def _all_evidence_ids(evidence_records) -> list[str]:
    ids: list[str] = []
    for rec in evidence_records:
        rid = rec.reaction_id if not isinstance(rec, dict) else rec.get("reaction_id", "")
        if rid and rid not in ids:
            ids.append(rid)
    return ids


def _validate_evidence_binding(feature_evidence_ids: dict | None,
                               resolution) -> None:
    """P4-R1-G: every evidence id bound to a feature must exist in the
    verified resolution — orphan ids are rejected, never silently dropped."""
    from reaction_agent.inference.evidence_identity import (
        EvidenceIdentityValidationError)
    if not feature_evidence_ids:
        return
    known = {i.evidence_id for i in resolution.identities}
    for feature, ids in feature_evidence_ids.items():
        for eid in (ids or []):
            if eid not in known:
                raise EvidenceIdentityValidationError(
                    f"feature {feature!r} binds orphan evidence id {eid!r} "
                    f"not present in the verified resolution")


def _tier_from_fraction(fraction: float, independent_count: int) -> SupportTier:
    if independent_count <= 0 or fraction <= 0.0:
        return SupportTier.none
    if fraction < 0.5:
        return SupportTier.weak
    if fraction < 0.75:
        return SupportTier.moderate
    return SupportTier.strong


def _strength_from(independent_count: int, observable_scores: list[int]) -> EvidenceStrength:
    if independent_count <= 0 or not observable_scores:
        return EvidenceStrength.none
    if independent_count == 1:
        return EvidenceStrength.single_source
    if independent_count >= 2:
        # "high quality multiple independent" requires strong (>=2) observable scores.
        if all(s >= 2 for s in observable_scores):
            return EvidenceStrength.high_quality_multiple_independent
        return EvidenceStrength.multiple_independent_sources
    return EvidenceStrength.none


def aggregate_support(
    candidate,
    evidence_records,
    resolution,
    structural_context: dict | None = None,
    conflicts: list[str] | None = None,
    feature_evidence_ids: dict | None = None,
) -> SupportBreakdown:
    """Aggregate support for one candidate into an evidence-bound breakdown.

    P4-R1-G: each feature binds ONLY the evidence ids that genuinely produced
    it (``feature_evidence_ids``). A bare ordinal without a binding is
    observable but evidence-less — it never becomes strong support.
    """
    cand_id = candidate.candidate_id
    evidence_ids = _all_evidence_ids(evidence_records)
    _validate_evidence_binding(feature_evidence_ids, resolution)
    vector = build_support_feature_vector(
        candidate, resolution, structural_context, conflicts,
        feature_evidence_ids=feature_evidence_ids)

    features: list[SupportFeature] = []
    for key in SUPPORT_FEATURES:
        obs = vector.get(key)
        ordinal = obs.ordinal if obs is not None else None
        is_observable = ordinal is not None
        # Observable features bind ONLY the evidence that produced them.
        bound_ids = list(obs.evidence_ids) if obs is not None else []
        features.append(SupportFeature(
            feature_key=key,
            evidence_ids=bound_ids,
            ordinal_score=ordinal,
            is_observable=is_observable,
            reason=("observed" if is_observable else "not_observable: no structural evidence"),
        ))

    independent_count = resolution.independent_count if resolution is not None else 0
    # Tier/strength must rest on genuinely STRUCTURAL observable features with
    # a real evidence binding, not on the self-derived independent_support_count
    # alone. A bare row count or an evidence-less ordinal with zero structural
    # grounding is NOT strong support (P4-R1-G).
    structural_scores = [
        f.ordinal_score for f in features
        if f.is_observable and f.feature_key != "independent_support_count"
        and f.evidence_ids
    ]
    if independent_count <= 0 or not structural_scores:
        tier = SupportTier.none
        strength = EvidenceStrength.none
    else:
        fraction = sum(structural_scores) / (3.0 * len(structural_scores))
        tier = _tier_from_fraction(fraction, independent_count)
        strength = _strength_from(independent_count, structural_scores)

    breakdown_hash = canonical_hash({
        "candidate_id": cand_id,
        "features": [
            {"key": f.feature_key, "ordinal": f.ordinal_score,
             "evidence_ids": sorted(f.evidence_ids)}
            for f in sorted(features, key=lambda f: f.feature_key)
        ],
        "support_tier": tier.value,
        "evidence_strength": strength.value,
        "independent_evidence_count": independent_count,
        "policy_version": P4_POLICY_VERSION,
    })

    return SupportBreakdown(
        candidate_id=cand_id,
        features=features,
        support_tier=tier,
        evidence_strength=strength,
        independent_evidence_count=independent_count,
        all_evidence_ids=evidence_ids,
        policy_version=P4_POLICY_VERSION,
        breakdown_hash=breakdown_hash,
    )
