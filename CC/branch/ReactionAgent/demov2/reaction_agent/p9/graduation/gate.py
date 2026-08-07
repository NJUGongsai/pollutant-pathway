"""P9-T2: Evidence-based graduation gate (final_plan §12.2, final_design §19.3,
ADR-0002).

The gate is the SOLE arbiter of graduation and is self-consistent at every
consumption point:

- ``evaluate_graduation`` RECOMPUTES the package / allowlist / ADR content hashes
  (never trusts an embedded declaration), matches the hypothesis class against
  the registered allowlist content (not just the id), takes the WORST-CASE
  value across dual-copy evidence fields, and checks the human approval against
  a runtime approver registry + the package-evidence binding.
- ``admit_to_production_ranking`` RE-RUNS ``evaluate_graduation`` and refuses a
  passed outcome that does not match the freshly re-derived one. It issues a
  ``ProductionRankingAdmission`` carrying a recomputable ``admission_attestation``.
- ``verify_production_admission`` re-derives the attestation and refuses a
  directly-constructed or forged admission.

The demo has no real human approval, so the expected terminal state is BLOCKED
with a readable, controlled-vocabulary blocker — never a faked PASS.

Hard boundary (strict untouched): ADDITIVE only.
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash
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
# Approver registry (demo scope — R1-02: presence + binding + registry)
# ---------------------------------------------------------------------------

#: Default known-approver set for the demo. A real deployment would back this
#: with an identity provider; the demo only checks membership + package binding
#: (no cryptographic signature — documented follow-up).
DEFAULT_APPROVER_REGISTRY: frozenset[str] = frozenset({"human_cc"})


# ---------------------------------------------------------------------------
# Package evidence hash — the hash a human approval binds to
# ---------------------------------------------------------------------------


def package_evidence_hash(package: GraduationPackage) -> str:
    """Canonical hash of the package evidence (excludes ``content_hash`` and
    ``human_approval``).

    A ``HumanApproval`` embeds this hash so the approval is bound to a specific
    package's evidence; a stolen approval cannot be replayed onto a different
    package (R1-02). Excluding ``human_approval`` avoids a circular dependency
    (the approval binds to evidence that does not include itself).
    """
    body = package.model_dump(exclude={"content_hash", "human_approval"})
    return canonical_hash(body)


# ---------------------------------------------------------------------------
# Rebuild helper — reconstruct a package with overrides, recomputing the hash
# (so tests can mutate a component without ``model_copy`` hash desync)
# ---------------------------------------------------------------------------


def rebuild_graduation_package(
    package: GraduationPackage, /, **overrides
) -> GraduationPackage:
    """Reconstruct a package with overridden components, recomputing content_hash.

    Unlike ``model_copy`` (which bypasses validators and desyncs the hash),
    this rebuilds via ``GraduationPackage.create`` so the content hash and the
    consistency validator both run. Used by tests to mutate a single component
    while keeping the package self-consistent.
    """
    fields = {
        "package_id": package.package_id,
        "hypothesis_class": package.hypothesis_class,
        "allowlist": package.allowlist,
        "held_out_results": package.held_out_results,
        "shift_results": package.shift_results,
        "risk_coverage": package.risk_coverage,
        "grounding": package.grounding,
        "cost": package.cost,
        "adr": package.adr,
        "human_approval": package.human_approval,
        "version_pin": package.version_pin,
    }
    fields.update(overrides)
    return GraduationPackage.create(**fields)


# ---------------------------------------------------------------------------
# Evidence-based gate
# ---------------------------------------------------------------------------


def evaluate_graduation(
    package: GraduationPackage,
    *,
    thresholds: GraduationThresholds = DEFAULT_GRADUATION_THRESHOLDS,
    approver_registry: frozenset[str] = DEFAULT_APPROVER_REGISTRY,
) -> GraduationOutcome:
    """Evaluate a graduation package against thresholds (sole arbiter).

    Self-consistent at every step:
    - R1-03: recomputes package / allowlist / ADR content hashes and refuses to
      trust an embedded declaration (model_copy desync -> blocker).
    - R1-05: matches the hypothesis class against the registered allowlist
      CONTENT (not just the class_id).
    - R1-04: takes the WORST-CASE value across dual-copy evidence fields
      (defends ``model_copy`` desync that bypasses the construction-time
      consistency validator).
    - R1-02: checks the human approval against the approver registry AND the
      package-evidence binding.
    - Blockers are deduplicated (controlled vocabulary, no free text).

    Returns ``graduated`` only when every check passes; otherwise ``blocked``
    with a readable blocker list. The outcome binds to the RECOMPUTED package
    hash (never the embedded one).
    """
    blockers: list[BlockerReasonCode] = []

    # R1-03: recompute content hashes (never trust embedded declarations)
    recomputed_pkg_hash = canonical_hash(package.model_dump(exclude={"content_hash"}))
    if recomputed_pkg_hash != package.content_hash:
        blockers.append(BlockerReasonCode.content_hash_mismatch)
    recomputed_al_hash = canonical_hash(
        package.allowlist.model_dump(exclude={"content_hash"})
    )
    if recomputed_al_hash != package.allowlist.content_hash:
        blockers.append(BlockerReasonCode.allowlist_content_hash_mismatch)
    recomputed_adr_hash = canonical_hash(
        package.adr.model_dump(exclude={"content_hash"})
    )
    if recomputed_adr_hash != package.adr.content_hash:
        blockers.append(BlockerReasonCode.adr_content_hash_mismatch)

    # R1-05: allowlist content match (find by class_id, compare full content)
    registered: HypothesisClass | None = None
    for c in package.allowlist.registered_classes:
        if c.class_id == package.hypothesis_class.class_id:
            registered = c
            break
    if registered is None:
        blockers.append(BlockerReasonCode.class_not_in_allowlist)
    elif registered.model_dump() != package.hypothesis_class.model_dump():
        blockers.append(BlockerReasonCode.class_content_drift)

    # Component 3: held-out evaluation metrics (§19.3 nine)
    h = package.held_out_results
    if h.incremental_recall is None:
        blockers.append(BlockerReasonCode.incremental_recall_unmeasured)
    elif h.incremental_recall < thresholds.min_incremental_recall:
        blockers.append(BlockerReasonCode.incremental_recall_insufficient)

    if h.invented_id_or_structure_mutations != 0:
        blockers.append(BlockerReasonCode.invented_id_or_structure_mutation_nonzero)

    # R1-04: worst-case across dual copies
    effective_risk = max(
        h.risk_at_fixed_coverage, package.risk_coverage.risk_at_fixed_coverage
    )
    if effective_risk > thresholds.max_risk:
        blockers.append(BlockerReasonCode.risk_exceeds_threshold)

    if h.repeated_run_agreement < thresholds.min_repeated_run_agreement:
        blockers.append(BlockerReasonCode.repeated_run_agreement_below_threshold)

    effective_grounding = min(h.grounding_score, package.grounding.grounding_score)
    if effective_grounding < thresholds.min_grounding:
        blockers.append(BlockerReasonCode.grounding_insufficient)

    effective_shift_drop = max(
        h.shift.max_recall_drop, package.shift_results.max_recall_drop
    )
    if effective_shift_drop > thresholds.max_recall_drop:
        blockers.append(BlockerReasonCode.excessive_family_scaffold_shift)

    # Component 8: ADR must be accepted
    if package.adr.status != "accepted":
        blockers.append(BlockerReasonCode.adr_not_accepted)

    # Component 9: human approval (R1-02: presence + registry + binding)
    if package.human_approval is None:
        blockers.append(BlockerReasonCode.missing_human_approval)
    else:
        if package.human_approval.approver_id not in approver_registry:
            blockers.append(BlockerReasonCode.approver_not_registered)
        if package.human_approval.package_content_hash != package_evidence_hash(package):
            blockers.append(BlockerReasonCode.approval_package_binding_mismatch)

    # dedup blockers (preserve first-occurrence order)
    seen: set[BlockerReasonCode] = set()
    deduped: list[BlockerReasonCode] = []
    for b in blockers:
        if b not in seen:
            seen.add(b)
            deduped.append(b)

    status = (
        GraduationStatus.graduated if not deduped else GraduationStatus.blocked
    )
    return GraduationOutcome(
        status=status,
        blockers=deduped,
        package_content_hash=recomputed_pkg_hash,
    )


# ---------------------------------------------------------------------------
# Admission attestation (recomputable)
# ---------------------------------------------------------------------------


def _attestation(
    recomputed_package_hash: str,
    package: GraduationPackage,
    status: GraduationStatus,
    blockers: list[BlockerReasonCode],
) -> str:
    """Recomputable gate attestation over the recomputed hash + approval + ADR
    + outcome digest. A directly-constructed admission cannot forge this
    because it depends on the gate's re-derived status + blocker digest.
    """
    body = {
        "graduated_package_hash": recomputed_package_hash,
        "human_approval_id": package.human_approval.approver_id if package.human_approval else "",
        "adr_id": package.adr.adr_id,
        "status": status.value,
        "blockers_digest": canonical_hash(sorted(b.value for b in blockers)),
    }
    return canonical_hash(body)


# ---------------------------------------------------------------------------
# Production ranking admission — structural enforcement (re-runs the gate)
# ---------------------------------------------------------------------------


def admit_to_production_ranking(
    outcome: GraduationOutcome,
    package: GraduationPackage,
    *,
    thresholds: GraduationThresholds = DEFAULT_GRADUATION_THRESHOLDS,
    approver_registry: frozenset[str] = DEFAULT_APPROVER_REGISTRY,
) -> ProductionRankingAdmission:
    """Admit a graduated hypothesis class to production ranking.

    R1-01: RE-RUNS ``evaluate_graduation`` and refuses a passed outcome that
    does not match the freshly re-derived one (never trusts the outcome
    argument). A blocked package raises ``GraduationBlockedError`` — there is
    no path that yields a ``ProductionRankingAdmission`` from a non-graduated
    package.
    """
    fresh = evaluate_graduation(
        package, thresholds=thresholds, approver_registry=approver_registry
    )
    # cross-check the passed outcome (never trust it)
    if (
        outcome.status is not fresh.status
        or outcome.package_content_hash != fresh.package_content_hash
    ):
        raise GraduationBlockedError(
            "admit re-runs the gate and refuses the passed outcome: "
            f"passed status={outcome.status.value}, "
            f"re-derived status={fresh.status.value} (outcome is not trusted)"
        )
    if fresh.status is not GraduationStatus.graduated:
        raise GraduationBlockedError(
            "cannot admit a blocked package to production ranking: "
            f"blockers={[b.value for b in fresh.blockers]}"
        )
    # defensive — gate guarantees approval present when graduated
    if package.human_approval is None:  # pragma: no cover - gate invariant
        raise GraduationBlockedError("internal error: graduated but no human_approval")

    attestation = _attestation(
        fresh.package_content_hash, package, fresh.status, fresh.blockers
    )
    return ProductionRankingAdmission(
        lane="agent_proposed",
        admitted=True,
        graduated_package_hash=fresh.package_content_hash,
        human_approval_id=package.human_approval.approver_id,
        adr_id=package.adr.adr_id,
        admission_attestation=attestation,
    )


def verify_production_admission(
    admission: ProductionRankingAdmission,
    package: GraduationPackage,
    *,
    thresholds: GraduationThresholds = DEFAULT_GRADUATION_THRESHOLDS,
    approver_registry: frozenset[str] = DEFAULT_APPROVER_REGISTRY,
) -> None:
    """Re-verify a production ranking admission against a package.

    R1-01: re-runs ``evaluate_graduation`` and re-derives the attestation. A
    directly-constructed admission (with a forged or absent attestation), or
    one pointing at a blocked / hash-desynced package, is refused. This is the
    downstream verification point — the only way an admission is trusted is by
    re-deriving it from the package evidence.
    """
    fresh = evaluate_graduation(
        package, thresholds=thresholds, approver_registry=approver_registry
    )
    if fresh.status is not GraduationStatus.graduated:
        raise GraduationBlockedError(
            "verify: package did not graduate on re-evaluation "
            f"(status={fresh.status.value}, blockers={[b.value for b in fresh.blockers]})"
        )
    expected = _attestation(
        fresh.package_content_hash, package, fresh.status, fresh.blockers
    )
    if admission.admission_attestation != expected:
        raise GraduationBlockedError(
            "verify: admission_attestation does not match the recomputed gate "
            "attestation (directly-constructed or forged admission refused)"
        )
    if admission.graduated_package_hash != fresh.package_content_hash:
        raise GraduationBlockedError(
            "verify: graduated_package_hash does not match the recomputed hash"
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
    from reaction_agent.p9.graduation.schemas import CoveragePoint

    return RiskCoverage(
        risk_at_fixed_coverage=0.1,
        fixed_coverage=0.95,
        coverage_curve=[CoveragePoint(coverage=0.95, risk=0.1)],
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


def _demo_approval(evidence_hash: str) -> HumanApproval:
    return HumanApproval(
        approver_id="human_cc",
        approved_at="2026-08-07T00:00:00Z",
        approval_token="signed_token_xyz",
        package_content_hash=evidence_hash,
        notes="reviewed held-out evidence",
    )


def _demo_version_pin() -> VersionPin:
    return VersionPin(
        policy_version="1.0.0",
        model_version="mock-v0",
        tool_version="rdkit-2026.03",
        chain_policy_content_hash="deadbeef" * 8,  # links to Phase B chain policy
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


def build_valid_graduation_package() -> GraduationPackage:
    """Build a complete, gate-passing graduation package (all 9 components,
    human approval present + registry-bound + package-bound, ADR accepted,
    metrics within thresholds).

    The approval's ``package_content_hash`` is bound to the package's evidence
    hash (computed from the no-approval form, which is stable since the evidence
    hash excludes ``human_approval``). Used by tests to exercise the
    ``graduated`` path; the gate re-evaluates the evidence, never trusts a
    declaration.
    """
    demo = build_demo_graduation_package()
    evidence_hash = package_evidence_hash(demo)
    approval = _demo_approval(evidence_hash)
    return rebuild_graduation_package(demo, human_approval=approval)


__all__ = [
    "DEFAULT_APPROVER_REGISTRY",
    "package_evidence_hash",
    "rebuild_graduation_package",
    "evaluate_graduation",
    "admit_to_production_ranking",
    "verify_production_admission",
    "build_valid_graduation_package",
    "build_demo_graduation_package",
]
