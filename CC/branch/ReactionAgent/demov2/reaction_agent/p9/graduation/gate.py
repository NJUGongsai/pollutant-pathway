"""P9-T2: Evidence-based graduation gate (final_plan §12.2, final_design §19.3,
ADR-0002).

The gate is the SOLE arbiter of graduation: it re-evaluates a
``GraduationPackage`` against thresholds and emits a ``GraduationOutcome``
(graduated / blocked). The package carries no self-declared status — the gate
re-derives it from evidence every time (evidence-based, not declaration-based).

``admit_to_production_ranking`` is the only way to construct a
``ProductionRankingAdmission``; a blocked outcome raises
``GraduationBlockedError``, so a non-graduated class is structurally barred
from production ranking (§12.2 "未毕业不进入 production ranking").

The demo has no real human approval, so the expected terminal state is BLOCKED
with a readable, controlled-vocabulary blocker — never a faked PASS.

Hard boundary (strict untouched): ADDITIVE only.
"""
from __future__ import annotations

from reaction_agent.p9.graduation.schemas import (
    ADRRecord,
    BlockerReasonCode,
    CostRecord,
    DEFAULT_GRADUATION_THRESHOLDS,
    GraduationBlockedError,
    GraduationOutcome,
    GraduationPackage,
    GraduationStatus,
    GraduationThresholds,
    GroundingRecord,
    HeldOutResults,
    HumanApproval,
    HypothesisClass,
    HypothesisClassAllowlist,
    ProductionRankingAdmission,
    RiskCoverage,
    ShiftResult,
    ShiftResults,
    VersionPin,
)


# ---------------------------------------------------------------------------
# Evidence-based gate
# ---------------------------------------------------------------------------


def evaluate_graduation(
    package: GraduationPackage,
    *,
    thresholds: GraduationThresholds = DEFAULT_GRADUATION_THRESHOLDS,
) -> GraduationOutcome:
    """Evaluate a graduation package against thresholds (sole arbiter).

    Re-derives status from evidence every call — the package's embedded fields
    are never trusted as self-declaration (ADR-0002 evidence-based). Returns
    ``graduated`` only when every check passes; otherwise ``blocked`` with a
    readable, controlled-vocabulary blocker list.
    """
    blockers: list[BlockerReasonCode] = []

    # Component 1+2: hypothesis class must be registered in the allowlist
    registered_ids = {c.class_id for c in package.allowlist.registered_classes}
    if not registered_ids:
        blockers.append(BlockerReasonCode.class_not_in_allowlist)
    elif package.hypothesis_class.class_id not in registered_ids:
        blockers.append(BlockerReasonCode.class_not_in_allowlist)

    # Component 3: held-out evaluation metrics (§19.3 nine)
    h = package.held_out_results
    if h.incremental_recall is None:
        blockers.append(BlockerReasonCode.incremental_recall_unmeasured)
    elif h.incremental_recall < thresholds.min_incremental_recall:
        blockers.append(BlockerReasonCode.incremental_recall_insufficient)

    if h.invented_id_or_structure_mutations != 0:
        blockers.append(BlockerReasonCode.invented_id_or_structure_mutation_nonzero)

    if h.risk_at_fixed_coverage > thresholds.max_risk:
        blockers.append(BlockerReasonCode.risk_exceeds_threshold)

    if h.repeated_run_agreement < thresholds.min_repeated_run_agreement:
        blockers.append(BlockerReasonCode.repeated_run_agreement_below_threshold)

    if h.grounding_score < thresholds.min_grounding:
        blockers.append(BlockerReasonCode.grounding_insufficient)

    # Component 4: family/scaffold shift
    if package.shift_results.max_recall_drop > thresholds.max_recall_drop:
        blockers.append(BlockerReasonCode.excessive_family_scaffold_shift)

    # Component 5: risk/coverage (cross-check the aggregate held-out risk)
    if package.risk_coverage.risk_at_fixed_coverage > thresholds.max_risk:
        blockers.append(BlockerReasonCode.risk_exceeds_threshold)

    # Component 6: grounding evidence
    if package.grounding.grounding_score < thresholds.min_grounding:
        blockers.append(BlockerReasonCode.grounding_insufficient)

    # Component 8: ADR must be accepted (demo uses "proposed" -> blocked)
    if package.adr.status != "accepted":
        blockers.append(BlockerReasonCode.adr_not_accepted)

    # Component 9: human approval (the demo blocker)
    if package.human_approval is None:
        blockers.append(BlockerReasonCode.missing_human_approval)

    # Version pin: chain policy content hash must be present
    if not package.version_pin.chain_policy_content_hash:
        blockers.append(BlockerReasonCode.missing_version_pin)

    status = (
        GraduationStatus.graduated
        if not blockers
        else GraduationStatus.blocked
    )
    return GraduationOutcome(
        status=status,
        blockers=blockers,
        package_content_hash=package.content_hash,
    )


# ---------------------------------------------------------------------------
# Production ranking admission (structural enforcement)
# ---------------------------------------------------------------------------


def admit_to_production_ranking(
    outcome: GraduationOutcome,
    package: GraduationPackage,
) -> ProductionRankingAdmission:
    """Admit a graduated hypothesis class to production ranking.

    Structural enforcement (§12.2 "未毕业不进入 production ranking"): a
    ``blocked`` outcome raises ``GraduationBlockedError`` — there is no path
    that yields a ``ProductionRankingAdmission`` from a non-graduated package.
    """
    if outcome.status is not GraduationStatus.graduated:
        raise GraduationBlockedError(
            "cannot admit a blocked outcome to production ranking: "
            f"status={outcome.status.value}, "
            f"blockers={[b.value for b in outcome.blockers]}"
        )
    if outcome.package_content_hash != package.content_hash:
        raise GraduationBlockedError(
            "outcome/package content_hash mismatch — the outcome does not "
            "attest this package (refusing admission)"
        )
    # gate guarantees human_approval is present when graduated, but assert
    # defensively — never trust a None here
    if package.human_approval is None:
        raise GraduationBlockedError(
            "internal error: graduated outcome but package has no human_approval"
        )
    return ProductionRankingAdmission(
        lane="agent_proposed",
        admitted=True,
        graduated_package_hash=package.content_hash,
        human_approval_id=package.human_approval.approver_id,
        adr_id=package.adr.adr_id,
    )


# ---------------------------------------------------------------------------
# Demo builders
# ---------------------------------------------------------------------------


def _demo_hypothesis_class() -> HypothesisClass:
    return HypothesisClass(
        class_id="hc_oh_to_c",
        description="hydroxyl-to-carbonyl agent-proposed class",
        transformation_family_ids=["fam_oh_to_c"],
        chain_policy_version="1.0.0",
    )


def _demo_allowlist() -> HypothesisClassAllowlist:
    return HypothesisClassAllowlist.create(
        allowlist_id="hc_allowlist_1",
        version="1.0.0",
        registered_classes=[_demo_hypothesis_class()],
    )


def _demo_held_out() -> HeldOutResults:
    return HeldOutResults(
        incremental_recall=0.5,  # truth-set denominator (Phase B口径)
        added_incorrect=1,
        risk_at_fixed_coverage=0.1,
        abstention_impact=0.1,
        repeated_run_agreement=0.95,
        grounding_score=0.9,
        invented_id_or_structure_mutations=0,
        cost=CostRecord(llm_calls=0, tool_calls=2, latency_ms=80),
        shift=ShiftResults(
            results=[
                ShiftResult(
                    family_id="fam_oh_to_c",
                    scaffold="primary_alcohol",
                    recall=0.5,
                    risk=0.1,
                    n_held_out=10,
                )
            ],
            max_recall_drop=0.05,
        ),
    )


def _demo_shift() -> ShiftResults:
    return ShiftResults(
        results=[
            ShiftResult(
                family_id="fam_oh_to_c",
                scaffold="primary_alcohol",
                recall=0.5,
                risk=0.1,
                n_held_out=10,
            )
        ],
        max_recall_drop=0.05,
    )


def _demo_risk_coverage() -> RiskCoverage:
    return RiskCoverage(
        risk_at_fixed_coverage=0.1,
        fixed_coverage=0.95,
        coverage_curve=[{"coverage": 0.95, "risk": 0.1}],
    )


def _demo_grounding() -> GroundingRecord:
    return GroundingRecord(
        grounding_score=0.9,
        grounded_family_ids=["fam_oh_to_c"],
        ungrounded_family_ids=[],
    )


def _demo_cost() -> CostRecord:
    return CostRecord(llm_calls=0, tool_calls=2, latency_ms=80)


def _demo_adr() -> ADRRecord:
    return ADRRecord.create(
        adr_id="ADR-P9-0001",
        title="Graduate hc_oh_to_c agent-proposed class",
        status="accepted",
        rationale="held-out evidence supports admission; risk within budget",
    )


def _demo_approval() -> HumanApproval:
    return HumanApproval(
        approver_id="human_cc",
        approved_at="2026-08-07T00:00:00Z",
        approval_token="signed_token_xyz",
        notes="reviewed held-out evidence",
    )


def _demo_version_pin() -> VersionPin:
    return VersionPin(
        policy_version="1.0.0",
        model_version="mock-v0",
        tool_version="rdkit-2026.03",
        chain_policy_content_hash="deadbeef" * 8,  # links to Phase B chain policy
    )


def build_valid_graduation_package() -> GraduationPackage:
    """Build a complete, gate-passing graduation package (all 9 components,
    human approval present, ADR accepted, metrics within thresholds).

    Used by tests to exercise the ``graduated`` path. The values are honest
    mock evidence (no real LLM/API burn); the gate re-evaluates them, never
    trusts a declaration.
    """
    return GraduationPackage.create(
        package_id="pkg_demo_valid",
        hypothesis_class=_demo_hypothesis_class(),
        allowlist=_demo_allowlist(),
        held_out_results=_demo_held_out(),
        shift_results=_demo_shift(),
        risk_coverage=_demo_risk_coverage(),
        grounding=_demo_grounding(),
        cost=_demo_cost(),
        adr=_demo_adr(),
        human_approval=_demo_approval(),
        version_pin=_demo_version_pin(),
    )


def build_demo_graduation_package() -> GraduationPackage:
    """Build a demo package with NO human approval.

    The demo has no real human approver, so the expected terminal state is
    BLOCKED with ``missing_human_approval`` — never a faked PASS. Every other
    component is valid, isolating the approval blocker.
    """
    return GraduationPackage.create(
        package_id="pkg_demo_blocked",
        hypothesis_class=_demo_hypothesis_class(),
        allowlist=_demo_allowlist(),
        held_out_results=_demo_held_out(),
        shift_results=_demo_shift(),
        risk_coverage=_demo_risk_coverage(),
        grounding=_demo_grounding(),
        cost=_demo_cost(),
        adr=_demo_adr(),
        human_approval=None,  # demo: no real human approval -> BLOCKED
        version_pin=_demo_version_pin(),
    )


__all__ = [
    "evaluate_graduation",
    "admit_to_production_ranking",
    "build_valid_graduation_package",
    "build_demo_graduation_package",
]
