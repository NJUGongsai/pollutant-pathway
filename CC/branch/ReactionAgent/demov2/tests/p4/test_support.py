"""P4-T2 support aggregation (evidence-ID bound, no probability semantics)."""
from __future__ import annotations

import pytest

from tests.fixtures.p4.p4_contract_fixture import (
    build_evidence_records,
    build_strict_candidate,
    build_structural_context,
    build_feature_evidence_binding,
    POLICY_VERSION,
)
from reaction_agent.schemas.p4.support import SupportBreakdown, SupportTier, EvidenceStrength
from reaction_agent.inference.evidence_identity import resolve_evidence_identity
from reaction_agent.inference.support import aggregate_support


def _resolution():
    return resolve_evidence_identity(build_evidence_records(), policy_version=POLICY_VERSION)


def test_support_breakdown_binds_evidence_ids():
    """P4-T2: observable support features must reference the evidence IDs that
    produced them (per-feature binding, never the full set); unobservable
    features bind nothing (empty evidence never becomes support)."""
    cand = build_strict_candidate()
    res = _resolution()
    binding = build_feature_evidence_binding()
    sup = aggregate_support(cand, build_evidence_records(), res,
                            structural_context=build_structural_context(),
                            feature_evidence_ids=binding)
    assert isinstance(sup, SupportBreakdown)
    observable = [f for f in sup.features if f.is_observable]
    unobservable = [f for f in sup.features if not f.is_observable]
    assert observable, "fixture should have observable structural features"
    for feature in observable:
        assert feature.evidence_ids, f"observable feature {feature.feature_key} must bind evidence IDs"
        for ev_id in feature.evidence_ids:
            assert ev_id in sup.all_evidence_ids
    for feature in unobservable:
        assert feature.evidence_ids == [], \
            f"unobservable feature {feature.feature_key} must not bind evidence"


def test_support_is_not_probability():
    """P4-T2: support tier/strength are ordinal, not probability."""
    cand = build_strict_candidate()
    sup = aggregate_support(cand, build_evidence_records(), _resolution(),
                            structural_context=build_structural_context())
    assert sup.support_tier in (SupportTier.none, SupportTier.weak,
                                SupportTier.moderate, SupportTier.strong)
    assert sup.evidence_strength in (EvidenceStrength.none,
                                     EvidenceStrength.single_source,
                                     EvidenceStrength.multiple_independent_sources,
                                     EvidenceStrength.high_quality_multiple_independent)


def test_duplicates_do_not_inflate_support():
    """P4-T2: merged duplicates must not raise the independent count."""
    cand = build_strict_candidate()
    res = _resolution()
    sup = aggregate_support(cand, build_evidence_records(), res,
                            structural_context=build_structural_context())
    # 3 independent groups => independent_evidence_count == 3 (not 5 rows).
    assert sup.independent_evidence_count == 3


def test_empty_evidence_never_becomes_support():
    """P4-T2: empty evidence must not automatically become support."""
    cand = build_strict_candidate()
    res = resolve_evidence_identity([], policy_version=POLICY_VERSION)
    sup = aggregate_support(cand, [], res, structural_context=None)
    assert sup.support_tier == SupportTier.none
    assert sup.evidence_strength == EvidenceStrength.none
    assert sup.independent_evidence_count == 0
    # Features without observable data are flagged, not silently supported.
    assert all(not f.is_observable for f in sup.features) or \
        all(f.ordinal_score == 0 for f in sup.features if f.is_observable)


def test_support_breakdown_hash_deterministic():
    """P4-T2: same inputs => same breakdown hash."""
    cand = build_strict_candidate()
    recs = build_evidence_records()
    res = _resolution()
    sup1 = aggregate_support(cand, recs, res, structural_context=build_structural_context())
    sup2 = aggregate_support(cand, recs, res, structural_context=build_structural_context())
    assert sup1.breakdown_hash == sup2.breakdown_hash
    assert sup1.policy_version == POLICY_VERSION
