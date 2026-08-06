"""P4-T2/T4 feature vector builder (versioned, ordinal, evidence-bound).

Feature ordinal scores are {0,1,2,3} or None (not observable). None means the
chemistry/structural observation is absent — it is NEVER fabricated and NEVER
converted into support. ``evidence_independence`` is always observable and is
derived from the independent-group resolution. All other features take their
ordinal from the caller-provided structural context (what P3/P1 chemistry
would supply); when absent they are not observable.

P4-R1-G: every observable feature is a typed ``FeatureObservation`` that binds
ONLY the evidence ids which genuinely produced it (``feature_evidence_ids``).
A bare ordinal without an evidence binding is not silently turned into
support/applicability.
"""
from __future__ import annotations

from reaction_agent.policies.p4_decision_policy import (
    RANKING_FEATURES,
    SUPPORT_FEATURES,
)
from reaction_agent.schemas.p4.observation import FeatureObservation

# Support-feature key -> ranking-feature key (final_design §16.1 vs §18.2).
_SUPPORT_TO_RANK = {
    "donor_structural_similarity": "donor_similarity",
    "transform_recurrence": "transform_support",
    "site_compatibility": "site_compatibility",
    "mapping_lineage_quality": "mapping_lineage_quality",
    "source_quality": "source_quality",
    "ledger_completeness": "ledger_completeness",
    "independent_support_count": "evidence_independence",
    "retrieval_stability": "retrieval_stability",
}


def _ordinal(value, default=None):
    if value is None:
        return default
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    if v < 0 or v > 3:
        raise ValueError(f"ordinal score must be 0..3, got {value}")
    return v


def _feature_evidence_ids(feature_evidence_ids: dict | None,
                          key: str, alt_key: str | None = None) -> list[str]:
    """Binding of real evidence ids for one feature (never the full set).

    Accepts both the ranking key and the support key spelling so callers can
    bind evidence by either name.
    """
    if feature_evidence_ids is None:
        return []
    for k in (key, alt_key):
        if k and feature_evidence_ids.get(k):
            return list(feature_evidence_ids.get(k))
    return []


def build_feature_vector(
    candidate,
    resolution,
    structural_context: dict | None = None,
    conflicts: list[str] | None = None,
    feature_evidence_ids: dict | None = None,
) -> dict[str, FeatureObservation]:
    """Build the 9-key ranking feature vector for one candidate.

    Returns ``{feature_key: FeatureObservation}``. ``evidence_independence``
    is derived from the resolution; the others come from ``structural_context``
    (None when not observable). ``conflicts`` are typed counterevidence reasons
    that feed ``conflict_penalty``. Each observable feature binds only the
    evidence ids that genuinely produced it.
    """
    ctx = structural_context or {}
    vector: dict[str, FeatureObservation] = {}

    # Always observable: independent support count -> ordinal 0..3.
    indep = resolution.independent_count if resolution is not None else 0
    indep_ordinal = 0 if indep <= 0 else (1 if indep == 1 else (2 if indep == 2 else 3))

    for key in RANKING_FEATURES:
        if key == "evidence_independence":
            vector[key] = FeatureObservation(
                feature_key=key, ordinal=indep_ordinal,
                evidence_ids=_feature_evidence_ids(feature_evidence_ids, key),
                source_stage="evidence_identity",
            )
        elif key == "conflict_penalty":
            vector[key] = FeatureObservation(
                feature_key=key, ordinal=3 if conflicts else 0,
                evidence_ids=_feature_evidence_ids(feature_evidence_ids, key),
                source_stage="counterevidence",
            )
        else:
            # lookup by either the ranking key or the support key spelling.
            raw = ctx.get(key)
            if raw is None:
                support_key = next(
                    (k for k, v in _SUPPORT_TO_RANK.items() if v == key), None)
                if support_key is not None:
                    raw = ctx.get(support_key)
            vector[key] = FeatureObservation(
                feature_key=key,
                ordinal=_ordinal(raw),
                evidence_ids=_feature_evidence_ids(feature_evidence_ids, key),
                source_stage="structural_context",
            )

    return vector


def build_support_feature_vector(
    candidate,
    resolution,
    structural_context: dict | None = None,
    conflicts: list[str] | None = None,
    feature_evidence_ids: dict | None = None,
) -> dict[str, FeatureObservation]:
    """Support-feature ordinal observations (SUPPORT_FEATURES keys)."""
    rank_vec = build_feature_vector(
        candidate, resolution, structural_context, conflicts,
        feature_evidence_ids=feature_evidence_ids)
    out: dict[str, FeatureObservation] = {}
    for key in SUPPORT_FEATURES:
        if key == "independent_support_count":
            indep = resolution.independent_count if resolution is not None else 0
            # The independent-group count is derived from ALL resolved
            # evidence, so its binding is the full resolved evidence set.
            all_ev = sorted(i.evidence_id for i in resolution.identities) \
                if resolution is not None else []
            out[key] = FeatureObservation(
                feature_key=key,
                ordinal=0 if indep <= 0 else (1 if indep == 1 else (2 if indep == 2 else 3)),
                evidence_ids=all_ev,
                source_stage="evidence_identity",
            )
        else:
            rank_key = _SUPPORT_TO_RANK.get(key, key)
            obs = rank_vec.get(rank_key)
            out[key] = FeatureObservation(
                feature_key=key,
                ordinal=obs.ordinal if obs is not None else None,
                evidence_ids=(
                    _feature_evidence_ids(feature_evidence_ids, key, rank_key)
                    if obs is not None else []),
                source_stage=obs.source_stage if obs is not None else "",
            )
    return out