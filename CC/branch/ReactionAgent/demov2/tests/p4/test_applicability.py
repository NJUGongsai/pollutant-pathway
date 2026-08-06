"""P4-T5 structural applicability (never enzyme activity)."""
from __future__ import annotations

import pytest

from tests.fixtures.p4.p4_contract_fixture import (
    build_evidence_records,
    build_strict_candidate,
    build_structural_context,
    POLICY_VERSION,
)
from reaction_agent.schemas.common import ApplicabilityLabel
from reaction_agent.schemas.p4.applicability import ApplicabilityAssessment
from reaction_agent.inference.evidence_identity import resolve_evidence_identity
from reaction_agent.inference.applicability import assess_applicability


def _resolution():
    return resolve_evidence_identity(build_evidence_records(), policy_version=POLICY_VERSION)


def test_applicability_is_structural_only():
    """P4-T5: label ∈ {in_domain, near_domain, out_of_domain, conflicted,
    unknown}; reason codes are structural; never activity probability."""
    cand = build_strict_candidate()
    res = _resolution()
    a = assess_applicability(cand, build_evidence_records(), res,
                             structural_context=build_structural_context())
    assert isinstance(a, ApplicabilityAssessment)
    assert a.label in (ApplicabilityLabel.in_domain, ApplicabilityLabel.near_domain,
                       ApplicabilityLabel.out_of_domain, ApplicabilityLabel.conflicted,
                       ApplicabilityLabel.unknown)
    assert a.reason_codes, "applicability must carry structural reason codes"
    assert a.evidence_ids, "applicability must reference evidence"
    assert a.policy_version == POLICY_VERSION


def test_no_evidence_is_unknown():
    """P4-T5: no structural evidence => unknown, never a fabricated label."""
    cand = build_strict_candidate()
    res = resolve_evidence_identity([], policy_version=POLICY_VERSION)
    a = assess_applicability(cand, [], res, structural_context=None)
    assert a.label == ApplicabilityLabel.unknown
    assert any(c.value == "NO_STRUCTURAL_EVIDENCE" for c in a.reason_codes)


def test_assessment_hash_deterministic():
    cand = build_strict_candidate()
    res = _resolution()
    a1 = assess_applicability(cand, build_evidence_records(), res,
                              structural_context=build_structural_context())
    a2 = assess_applicability(cand, build_evidence_records(), res,
                              structural_context=build_structural_context())
    assert a1.assessment_hash == a2.assessment_hash


def test_conflicted_label_on_conflict():
    """P4-T5: conflicting structural evidence => conflicted."""
    cand = build_strict_candidate()
    res = _resolution()
    a = assess_applicability(
        cand, build_evidence_records(), res,
        structural_context=build_structural_context(),
        conflicts=["provenance_direction_role_conflict"])
    assert a.label == ApplicabilityLabel.conflicted
