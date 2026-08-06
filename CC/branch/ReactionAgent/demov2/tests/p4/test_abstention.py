"""P4-T6 typed abstention (frozen precedence; system failure separate)."""
from __future__ import annotations

import pytest

from tests.fixtures.p4.p4_contract_fixture import POLICY_VERSION
from reaction_agent.schemas.common import ScientificAbstentionReason
from reaction_agent.schemas.result import StageSummary
from reaction_agent.schemas.p4.decision import AbstentionDecision
from reaction_agent.inference.abstention import (
    decide_abstention,
    detect_abstention_conditions,
    SYSTEM_FAILURE_PRECEDENCE,
)


def _trace() -> StageSummary:
    return StageSummary(donor_evidence_ids=["ev_d1"], candidate_ids=[])


def test_precedence_invalid_input_wins():
    """P4-T6: when invalid input + no donor + conflict all apply, the frozen
    order picks INVALID_INPUT as the primary reason."""
    d = decide_abstention(
        conditions={"NO_IN_DOMAIN_DONOR", "INVALID_INPUT", "EVIDENCE_CONFLICT",
                    "INSUFFICIENT_SUPPORT"},
        trace=_trace(),
        policy_version=POLICY_VERSION,
    )
    assert isinstance(d, AbstentionDecision)
    assert d.reason_code == ScientificAbstentionReason.INVALID_INPUT
    assert d.primary_reason == ScientificAbstentionReason.INVALID_INPUT.value
    assert d.candidate_count == 0
    assert d.trace is not None
    assert d.policy_version == POLICY_VERSION


def test_precedence_no_donor_before_conflict():
    """P4-T6: NO_IN_DOMAIN_DONOR comes before EVIDENCE_CONFLICT in the order."""
    d = decide_abstention(
        conditions={"EVIDENCE_CONFLICT", "NO_IN_DOMAIN_DONOR"},
        trace=_trace(),
        policy_version=POLICY_VERSION,
    )
    assert d.reason_code == ScientificAbstentionReason.NO_IN_DOMAIN_DONOR


def test_precedence_out_of_domain_last_order_members():
    """P4-T6: EVIDENCE_CONFLICT precedes INSUFFICIENT_SUPPORT precedes OUT_OF_DOMAIN."""
    d1 = decide_abstention(conditions={"INSUFFICIENT_SUPPORT", "EVIDENCE_CONFLICT"},
                           trace=_trace(), policy_version=POLICY_VERSION)
    assert d1.reason_code == ScientificAbstentionReason.EVIDENCE_CONFLICT
    d2 = decide_abstention(conditions={"OUT_OF_DOMAIN", "INSUFFICIENT_SUPPORT"},
                           trace=_trace(), policy_version=POLICY_VERSION)
    assert d2.reason_code == ScientificAbstentionReason.INSUFFICIENT_SUPPORT


def test_abstention_requires_zero_candidates():
    """P4-T6: an abstention must carry 0 candidates."""
    with pytest.raises(ValueError):
        decide_abstention(
            conditions={"INSUFFICIENT_SUPPORT"},
            trace=_trace(),
            policy_version=POLICY_VERSION,
            candidate_count=1,
        )


def test_detection_distinguishes_system_failure():
    """P4-T6: system failures are NOT scientific abstention conditions."""
    conditions = detect_abstention_conditions(
        invalid_input=False,
        no_in_domain_donor=False,
        no_resolved_lineage=False,
        no_transferable_transform=False,
        no_compatible_site=False,
        all_candidates_invalid=False,
        evidence_conflict=False,
        insufficient_support=True,
        out_of_domain=False,
    )
    assert conditions == {"INSUFFICIENT_SUPPORT"}
    # System failure must not leak into abstention conditions.
    sys_conds = detect_abstention_conditions(
        system_failure="SNAPSHOT_UNAVAILABLE", **{k: False for k in
        ["invalid_input", "no_in_domain_donor", "no_resolved_lineage",
         "no_transferable_transform", "no_compatible_site",
         "all_candidates_invalid", "evidence_conflict",
         "insufficient_support", "out_of_domain"]})
    assert sys_conds == set()


def test_precedence_matches_frozen_list():
    """P4-T6: precedence must equal the frozen §15.3 order (primary only)."""
    from reaction_agent.policies.p4_decision_policy import ABSTENTION_PRECEDENCE
    frozen = list(ABSTENTION_PRECEDENCE)
    assert frozen == [r.value for r in ScientificAbstentionReason]
