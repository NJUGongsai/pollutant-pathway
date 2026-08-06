"""P4-T6 typed abstention (final_design §15.3, §15.4).

Frozen precedence: the official §15.3 list order (earliest wins). System
failures are NEVER scientific abstention conditions — they route to ``failed``.
Every abstention carries 0 candidates, one primary reason, optional secondary
reasons, complete trace, policy/config version, and source evidence scope.
"""
from __future__ import annotations

from reaction_agent.policies.p4_decision_policy import (
    P4_POLICY_VERSION,
    ABSTENTION_PRECEDENCE,
)
from reaction_agent.schemas.common import (
    ScientificAbstentionReason,
    SystemFailureReason,
)
from reaction_agent.schemas.p4.decision import AbstentionDecision

# System failures are NOT abstention conditions; kept here to make the
# separation explicit and importable.
SYSTEM_FAILURE_PRECEDENCE: tuple[str, ...] = tuple(
    r.value for r in SystemFailureReason)


def decide_abstention(
    conditions: set[str] | list[str],
    trace,
    policy_version: str,
    candidate_count: int = 0,
    source_evidence_scope: str = "train_only",
) -> AbstentionDecision:
    """Decide an abstention using frozen precedence (earliest reason wins).

    ``conditions`` is the set of applicable scientific-abstention reason
    names. The primary reason is the earliest in ABSTENTION_PRECEDENCE.
    """
    if candidate_count != 0:
        raise ValueError(
            f"abstention requires 0 candidates, got {candidate_count}")

    conds = set(conditions)
    for name in ABSTENTION_PRECEDENCE:
        if name in conds:
            primary = ScientificAbstentionReason(name)
            secondary = [
                ScientificAbstentionReason(n).value
                for n in ABSTENTION_PRECEDENCE
                if n in conds and n != name
            ]
            return AbstentionDecision(
                reason_code=primary,
                primary_reason=primary.value,
                secondary_reasons=secondary,
                candidate_count=0,
                trace=trace,
                policy_version=policy_version,
                source_evidence_scope=source_evidence_scope,
            )

    raise ValueError(
        f"no recognized abstention condition in {sorted(conds)}")


def detect_abstention_conditions(
    invalid_input: bool = False,
    no_in_domain_donor: bool = False,
    no_resolved_lineage: bool = False,
    no_transferable_transform: bool = False,
    no_compatible_site: bool = False,
    all_candidates_invalid: bool = False,
    evidence_conflict: bool = False,
    insufficient_support: bool = False,
    out_of_domain: bool = False,
    system_failure: str | None = None,
) -> set[str]:
    """Detect which scientific-abstention conditions apply.

    ``system_failure`` is deliberately excluded — system failures are NOT
    scientific abstention conditions and must never leak into abstention.
    """
    conditions: set[str] = set()
    if invalid_input:
        conditions.add("INVALID_INPUT")
    if no_in_domain_donor:
        conditions.add("NO_IN_DOMAIN_DONOR")
    if no_resolved_lineage:
        conditions.add("NO_RESOLVED_LINEAGE")
    if no_transferable_transform:
        conditions.add("NO_TRANSFERABLE_TRANSFORM")
    if no_compatible_site:
        conditions.add("NO_COMPATIBLE_SITE")
    if all_candidates_invalid:
        conditions.add("ALL_CANDIDATES_CHEMICALLY_INVALID")
    if evidence_conflict:
        conditions.add("EVIDENCE_CONFLICT")
    if insufficient_support:
        conditions.add("INSUFFICIENT_SUPPORT")
    if out_of_domain:
        conditions.add("OUT_OF_DOMAIN")
    # system_failure is intentionally ignored here.
    return conditions
