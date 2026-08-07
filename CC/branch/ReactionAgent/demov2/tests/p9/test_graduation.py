"""P9-T2 RED tests — Graduation package + evidence-based gate (final_plan
§12.2, final_design §19.3, ADR-0002).

The graduation gate is EVIDENCE-BASED, not declaration-based: a hypothesis
class enters production ranking ONLY after a GraduationPackage passes the gate
(all 9 components present + valid + human approval + ADR accepted + held-out
metrics meet thresholds). The GraduationPackage carries NO self-declared status
field — the gate is the sole arbiter.

The demo has no real human approval, so the expected terminal state is BLOCKED
with a readable, controlled-vocabulary blocker — never a faked PASS. The lane
is probability-free, so no Brier/ECE/calibration fields exist (§19.3 "没有
probability 时不伪造 calibration").

Hard boundary (strict untouched): ADDITIVE only — lives in
``reaction_agent/p9/graduation/``; never imports or modifies the strict channel
(P3-P6), P7, P8, Phase B's agent_proposed lane (only consumes its report
口径), or deepseek's external/ package.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from reaction_agent.schemas.common import Lane
from reaction_agent.schemas.errors import ContractViolation
from reaction_agent.p9.graduation import (
    ADRRecord,
    BlockerReasonCode,
    CoveragePoint,
    CostRecord,
    DEFAULT_APPROVER_REGISTRY,
    DEFAULT_GRADUATION_THRESHOLDS,
    GraduationBlockedError,
    GraduationOutcome,
    GraduationPackage,
    GraduationStatus,
    GroundingRecord,
    HumanApproval,
    HeldOutResults,
    HypothesisClass,
    HypothesisClassAllowlist,
    ProductionRankingAdmission,
    RiskCoverage,
    ShiftResult,
    ShiftResults,
    VersionPin,
    admit_to_production_ranking,
    build_demo_graduation_package,
    build_valid_graduation_package,
    evaluate_graduation,
    package_evidence_hash,
    rebuild_graduation_package,
    verify_production_admission,
)

# ---------------------------------------------------------------------------
# Helpers — a fully graduated package and a demo (no approval) package
# ---------------------------------------------------------------------------


def _allowlist() -> HypothesisClassAllowlist:
    return HypothesisClassAllowlist.create(
        allowlist_id="hc_allowlist_1",
        version="1.0.0",
        registered_classes=[
            HypothesisClass(
                class_id="hc_oh_to_c",
                description="hydroxyl-to-carbonyl agent-proposed class",
                transformation_family_ids=["fam_oh_to_c"],
                chain_policy_version="1.0.0",
            ),
        ],
    )


def _held_out(*, invented: int = 0, risk: float = 0.1, recall=0.5, rra=0.95) -> HeldOutResults:
    return HeldOutResults(
        incremental_recall=recall,  # truth-set denominator (Phase B口径)
        added_incorrect=1,
        risk_at_fixed_coverage=risk,
        abstention_impact=0.1,
        repeated_run_agreement=rra,
        grounding_score=0.9,
        invented_id_or_structure_mutations=invented,
        cost=CostRecord(llm_calls=0, tool_calls=2, latency_ms=80),
        shift=ShiftResults(
            results=[
                ShiftResult(
                    family_id="fam_oh_to_c",
                    scaffold="primary_alcohol",
                    recall=recall,
                    risk=risk,
                    n_held_out=10,
                )
            ],
            max_recall_drop=0.05,
        ),
    )


def _version_pin() -> VersionPin:
    return VersionPin(
        policy_version="1.0.0",
        model_version="mock-v0",
        tool_version="rdkit-2026.03",
        chain_policy_content_hash="deadbeef" * 8,  # links to Phase B chain policy
    )


def _adr(*, status: str = "accepted") -> ADRRecord:
    return ADRRecord.create(
        adr_id="ADR-P9-0001",
        title="Graduate hc_oh_to_c agent-proposed class",
        status=status,
        rationale="held-out evidence supports admission; risk within budget",
    )


def _approval() -> HumanApproval:
    return HumanApproval(
        approver_id="human_cc",
        approved_at="2026-08-07T00:00:00Z",
        approval_token="signed_token_xyz",
        notes="reviewed held-out evidence",
    )


def _grounding() -> GroundingRecord:
    return GroundingRecord(
        grounding_score=0.9,
        grounded_family_ids=["fam_oh_to_c"],
        ungrounded_family_ids=[],
    )


def _risk_coverage(risk: float = 0.1) -> RiskCoverage:
    return RiskCoverage(
        risk_at_fixed_coverage=risk,
        fixed_coverage=0.95,
        coverage_curve=[{"coverage": 0.95, "risk": risk}],
    )


def _shift() -> ShiftResults:
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


# ---------------------------------------------------------------------------
# Component 1+2: hypothesis class + allowlist (frozen, content-hashed)
# ---------------------------------------------------------------------------


def test_allowlist_is_frozen_and_content_hashed():
    al = _allowlist()
    assert al.version == "1.0.0"
    assert al.content_hash
    # frozen: assignment must raise
    with pytest.raises((ValidationError, Exception)):
        al.registered_classes = []  # type: ignore[misc]
    # content-hash verified on reconstruct
    rebuilt = HypothesisClassAllowlist.create(
        allowlist_id="hc_allowlist_1",
        version="1.0.0",
        registered_classes=[
            HypothesisClass(
                class_id="hc_oh_to_c",
                description="hydroxyl-to-carbonyl agent-proposed class",
                transformation_family_ids=["fam_oh_to_c"],
                chain_policy_version="1.0.0",
            ),
        ],
    )
    assert rebuilt.content_hash == al.content_hash
    # tamper detection
    with pytest.raises(ValidationError):
        HypothesisClassAllowlist(
            allowlist_id=al.allowlist_id,
            version=al.version,
            registered_classes=al.registered_classes,
            content_hash="tampered",
        )


# ---------------------------------------------------------------------------
# Component 8: ADR (frozen, content-hashed)
# ---------------------------------------------------------------------------


def test_adr_is_frozen_and_content_hashed():
    adr = _adr()
    assert adr.adr_id == "ADR-P9-0001"
    assert adr.content_hash
    rebuilt = ADRRecord.create(
        adr_id="ADR-P9-0001",
        title="Graduate hc_oh_to_c agent-proposed class",
        status="accepted",
        rationale="held-out evidence supports admission; risk within budget",
    )
    assert rebuilt.content_hash == adr.content_hash


# ---------------------------------------------------------------------------
# Component 3: held-out results — §19.3 nine metrics, NO probability fields
# ---------------------------------------------------------------------------


def test_held_out_results_covers_nine_section_19_3_metrics():
    h = _held_out()
    # the nine §19.3 metrics
    assert h.incremental_recall is not None
    assert h.added_incorrect == 1
    assert h.risk_at_fixed_coverage == 0.1
    assert h.abstention_impact == 0.1
    assert h.repeated_run_agreement == 0.95
    assert h.grounding_score == 0.9
    assert h.invented_id_or_structure_mutations == 0
    assert h.cost.tool_calls == 2
    assert h.shift.max_recall_drop == 0.05


def test_held_out_results_has_no_probability_calibration_fields():
    # §19.3: no probability -> do not fake calibration. The schema must NOT
    # carry Brier/ECE/probability fields (extra="forbid" rejects them).
    h = _held_out()
    # the probability-free lane pins this off
    assert h.probability_introduced is False
    # a Brier field is rejected by extra="forbid" at construction
    with pytest.raises(ValidationError):
        HeldOutResults(
            incremental_recall=0.5,
            added_incorrect=1,
            risk_at_fixed_coverage=0.1,
            abstention_impact=0.1,
            repeated_run_agreement=0.95,
            grounding_score=0.9,
            invented_id_or_structure_mutations=0,
            cost=CostRecord(llm_calls=0, tool_calls=2, latency_ms=80),
            shift=_shift(),
            brier=0.1,  # type: ignore[call-arg]  # extra field -> forbidden
        )
    with pytest.raises(ValidationError):
        HeldOutResults(
            incremental_recall=0.5,
            added_incorrect=1,
            risk_at_fixed_coverage=0.1,
            abstention_impact=0.1,
            repeated_run_agreement=0.95,
            grounding_score=0.9,
            invented_id_or_structure_mutations=0,
            cost=CostRecord(llm_calls=0, tool_calls=2, latency_ms=80),
            shift=_shift(),
            probability_introduced=True,  # Literal[False] rejects True
        )


# ---------------------------------------------------------------------------
# The 9-component package (content-hashed)
# ---------------------------------------------------------------------------


def test_graduation_package_has_nine_components_and_content_hash():
    pkg = build_valid_graduation_package()
    # §12.2 nine components
    assert isinstance(pkg.hypothesis_class, HypothesisClass)        # 1
    assert isinstance(pkg.allowlist, HypothesisClassAllowlist)       # 2
    assert isinstance(pkg.held_out_results, HeldOutResults)         # 3
    assert isinstance(pkg.shift_results, ShiftResults)               # 4
    assert isinstance(pkg.risk_coverage, RiskCoverage)              # 5
    assert isinstance(pkg.grounding, GroundingRecord)               # 6
    assert isinstance(pkg.cost, CostRecord)                          # 7
    assert isinstance(pkg.adr, ADRRecord)                            # 8
    assert isinstance(pkg.human_approval, HumanApproval)             # 9
    assert isinstance(pkg.version_pin, VersionPin)                   # §19.3 versions
    assert pkg.content_hash


def test_graduation_package_content_hash_tamper_detection():
    pkg = build_valid_graduation_package()
    # reconstruct with identical fields -> same hash
    rebuilt = build_valid_graduation_package()
    assert rebuilt.content_hash == pkg.content_hash
    # tampered content_hash must raise at construction (model_validator verifies)
    with pytest.raises(ValidationError):
        GraduationPackage(
            **pkg.model_dump(exclude={"content_hash"}),
            content_hash="tampered",
        )


def test_graduation_package_has_no_self_declared_status_field():
    # evidence-based, not declaration-based (ADR-0002): the package carries NO
    # status / graduated / approved declaration — the gate is the sole arbiter
    pkg = build_valid_graduation_package()
    dump = pkg.model_dump()
    for forbidden in ("status", "graduated", "approved", "is_graduated"):
        assert forbidden not in dump, f"package must not self-declare {forbidden!r}"


# ---------------------------------------------------------------------------
# The evidence-based gate
# ---------------------------------------------------------------------------


def test_gate_returns_graduated_for_complete_package():
    pkg = build_valid_graduation_package()
    outcome = evaluate_graduation(pkg)
    assert outcome.status is GraduationStatus.graduated
    assert outcome.blockers == []
    assert outcome.package_content_hash == pkg.content_hash


def test_gate_blocks_when_human_approval_missing():
    pkg = build_demo_graduation_package()  # no human approval
    outcome = evaluate_graduation(pkg)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.missing_human_approval in outcome.blockers


def test_gate_blocks_when_adr_not_accepted():
    pkg = build_valid_graduation_package().model_copy(
        update={"adr": _adr(status="proposed")}
    )
    outcome = evaluate_graduation(pkg)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.adr_not_accepted in outcome.blockers


def test_gate_blocks_when_invented_mutation_nonzero():
    pkg = build_valid_graduation_package().model_copy(
        update={"held_out_results": _held_out(invented=2)}
    )
    outcome = evaluate_graduation(pkg)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.invented_id_or_structure_mutation_nonzero in outcome.blockers


def test_gate_blocks_when_risk_exceeds_threshold():
    pkg = build_valid_graduation_package().model_copy(
        update={
            "held_out_results": _held_out(risk=0.9),
            "risk_coverage": _risk_coverage(risk=0.9),
        }
    )
    outcome = evaluate_graduation(pkg)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.risk_exceeds_threshold in outcome.blockers


def test_gate_blocks_when_repeated_run_agreement_low():
    pkg = build_valid_graduation_package().model_copy(
        update={"held_out_results": _held_out(rra=0.3)}
    )
    outcome = evaluate_graduation(pkg)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.repeated_run_agreement_below_threshold in outcome.blockers


def test_gate_blocks_when_class_not_in_allowlist():
    rogue = HypothesisClass(
        class_id="hc_rogue",
        description="not registered",
        transformation_family_ids=["fam_x"],
        chain_policy_version="1.0.0",
    )
    pkg = build_valid_graduation_package().model_copy(update={"hypothesis_class": rogue})
    outcome = evaluate_graduation(pkg)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.class_not_in_allowlist in outcome.blockers


def test_gate_blocks_when_incremental_recall_unmeasured():
    h = _held_out()
    h_unmeasured = h.model_copy(update={"incremental_recall": None})
    pkg = build_valid_graduation_package().model_copy(
        update={"held_out_results": h_unmeasured}
    )
    outcome = evaluate_graduation(pkg)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.incremental_recall_unmeasured in outcome.blockers


def test_gate_blocks_when_excessive_shift():
    shift = ShiftResults(
        results=[],
        max_recall_drop=0.99,  # far beyond threshold
    )
    pkg = build_valid_graduation_package().model_copy(
        update={"shift_results": shift}
    )
    outcome = evaluate_graduation(pkg)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.excessive_family_scaffold_shift in outcome.blockers


def test_gate_blocks_when_grounding_insufficient():
    pkg = build_valid_graduation_package().model_copy(
        update={
            "grounding": GroundingRecord(
                grounding_score=0.1,
                grounded_family_ids=[],
                ungrounded_family_ids=["fam_oh_to_c"],
            ),
            "held_out_results": _held_out(),  # grounding_score here stays 0.9; isolate the grounding component
        }
    )
    outcome = evaluate_graduation(pkg)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.grounding_insufficient in outcome.blockers


def test_gate_blockers_use_controlled_vocabulary():
    # blockers are enum members (controlled vocabulary), not free text
    pkg = build_demo_graduation_package()
    outcome = evaluate_graduation(pkg)
    for b in outcome.blockers:
        assert isinstance(b, BlockerReasonCode)


def test_gate_outcome_is_lane_pinned_exploratory():
    pkg = build_valid_graduation_package()
    outcome = evaluate_graduation(pkg)
    assert outcome.lane == "agent_proposed"
    assert outcome.output_semantics == "graduation_gate"
    # no production rank fields — structurally distinct from PredictionResult
    dump = outcome.model_dump()
    for forbidden in ("ranking_score", "run_id", "decision", "canonical_product"):
        assert forbidden not in dump


# ---------------------------------------------------------------------------
# Production ranking admission — structural enforcement
# ---------------------------------------------------------------------------


def test_admit_to_production_ranking_rejects_blocked_outcome():
    pkg = build_demo_graduation_package()
    outcome = evaluate_graduation(pkg)
    assert outcome.status is GraduationStatus.blocked
    with pytest.raises(GraduationBlockedError):
        admit_to_production_ranking(outcome, pkg)


def test_admit_to_production_ranking_accepts_graduated_outcome():
    pkg = build_valid_graduation_package()
    outcome = evaluate_graduation(pkg)
    admission = admit_to_production_ranking(outcome, pkg)
    assert isinstance(admission, ProductionRankingAdmission)
    assert admission.lane == "agent_proposed"
    assert admission.admitted is True
    assert admission.graduated_package_hash == pkg.content_hash
    assert admission.human_approval_id
    assert admission.adr_id
    assert admission.admission_attestation  # R1-01: recomputable gate attestation


def test_verify_production_admission_accepts_honest_admission():
    pkg = build_valid_graduation_package()
    outcome = evaluate_graduation(pkg)
    admission = admit_to_production_ranking(outcome, pkg)
    verify_production_admission(admission, pkg)  # no raise — honest attestation


def test_production_ranking_admission_structurally_distinct_from_strict_candidate():
    # an admission cannot be assigned to a strict Candidate
    from reaction_agent.schemas.candidate import Candidate

    pkg = build_valid_graduation_package()
    outcome = evaluate_graduation(pkg)
    admission = admit_to_production_ranking(outcome, pkg)
    with pytest.raises(ValidationError):
        Candidate.model_validate(admission.model_dump())


# ---------------------------------------------------------------------------
# Demo terminal state — BLOCKED without human approval (no faked PASS)
# ---------------------------------------------------------------------------


def test_demo_terminal_state_blocked_without_human_approval():
    pkg = build_demo_graduation_package()
    outcome = evaluate_graduation(pkg)
    # the demo has no real human approval -> BLOCKED (never a faked PASS)
    assert outcome.status is GraduationStatus.blocked
    # the blocker is the readable, controlled reason
    assert BlockerReasonCode.missing_human_approval in outcome.blockers
    # and admission is structurally refused
    with pytest.raises(GraduationBlockedError):
        admit_to_production_ranking(outcome, pkg)


def test_no_fake_calibration_when_no_probability():
    # the lane is probability-free; no Brier/ECE are fabricated
    h = _held_out()
    assert h.probability_introduced is False
    dump = h.model_dump()
    for forbidden in ("brier", "ece", "calibration", "probability"):
        assert forbidden not in dump or forbidden == "probability_introduced"


# ---------------------------------------------------------------------------
# Thresholds — configurable, content-pinned
# ---------------------------------------------------------------------------


def test_default_thresholds_are_sensible():
    t = DEFAULT_GRADUATION_THRESHOLDS
    assert t.max_risk > 0.0
    assert 0.0 < t.min_repeated_run_agreement <= 1.0
    assert t.min_grounding > 0.0
    assert t.min_incremental_recall >= 0.0
    assert t.max_recall_drop >= 0.0


def test_gate_respects_custom_thresholds():
    # a package that passes default thresholds fails under strict thresholds
    pkg = build_valid_graduation_package()
    strict = DEFAULT_GRADUATION_THRESHOLDS.model_copy(
        update={"min_repeated_run_agreement": 0.999}
    )
    outcome = evaluate_graduation(pkg, thresholds=strict)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.repeated_run_agreement_below_threshold in outcome.blockers


# ===========================================================================
# Round 2 remediation (kimi Phase-C Round-1 findings P9C-R1-01..07)
#
# Sole-arbiter self-consistency: the gate re-derives status from evidence at
# EVERY consumption point (evaluate, admit, verify) — it never trusts an
# embedded hash, a passed outcome, a self-declared approval token, or an
# allowlist id match. Production admission is gated by a recomputable
# attestation that a directly-constructed admission cannot forge.
# ===========================================================================


# ---------------------------------------------------------------------------
# R1-01 (P0): admit reruns the gate; admission carries a recomputable
# attestation; verify rejects directly-constructed / forged admissions.
# ---------------------------------------------------------------------------


def test_admit_reruns_gate_rejects_forged_graduated_outcome():
    # forge an outcome that claims "graduated" for a BLOCKED (demo) package
    pkg = build_demo_graduation_package()  # human_approval=None -> blocked
    forged = GraduationOutcome(
        status=GraduationStatus.graduated,  # LIE
        blockers=[],
        package_content_hash=pkg.content_hash,
    )
    # admit must re-run evaluate_graduation and refuse the forged outcome
    with pytest.raises(GraduationBlockedError):
        admit_to_production_ranking(forged, pkg)


def test_admit_reruns_gate_rejects_outcome_hash_mismatch():
    # an honest graduated outcome but bound to a DIFFERENT package hash
    valid = build_valid_graduation_package()
    honest = evaluate_graduation(valid)
    other = build_demo_graduation_package()
    with pytest.raises(GraduationBlockedError):
        admit_to_production_ranking(honest, other)  # outcome != package


def test_verify_rejects_directly_constructed_admission():
    # a ProductionRankingAdmission constructed by hand (not via admit) cannot
    # forge a valid attestation -> verify re-derives and refuses
    pkg = build_valid_graduation_package()
    forged_admission = ProductionRankingAdmission(
        lane="agent_proposed",
        admitted=True,
        graduated_package_hash=pkg.content_hash,
        human_approval_id="human_cc",
        adr_id=pkg.adr.adr_id,
        admission_attestation="i-am-not-an-attestation",
    )
    with pytest.raises(GraduationBlockedError):
        verify_production_admission(forged_admission, pkg)


def test_verify_rejects_admission_pointing_at_blocked_package():
    pkg = build_demo_graduation_package()  # blocked
    # even with a "correct-looking" attestation, verify re-runs the gate and
    # finds the package blocked -> refuse
    admission = ProductionRankingAdmission(
        lane="agent_proposed",
        admitted=True,
        graduated_package_hash=pkg.content_hash,
        human_approval_id="nobody",
        adr_id=pkg.adr.adr_id,
        admission_attestation=package_evidence_hash(pkg),  # wrong attestation
    )
    with pytest.raises(GraduationBlockedError):
        verify_production_admission(admission, pkg)


def test_admission_attestation_is_deterministic_and_recomputable():
    pkg = build_valid_graduation_package()
    outcome = evaluate_graduation(pkg)
    a1 = admit_to_production_ranking(outcome, pkg)
    # re-running the whole flow yields the same attestation
    outcome2 = evaluate_graduation(pkg)
    a2 = admit_to_production_ranking(outcome2, pkg)
    assert a1.admission_attestation == a2.admission_attestation


# ---------------------------------------------------------------------------
# R1-02 (P1): human approval — approver registry + package binding
# (demo scope: presence + binding; no cryptographic signature — documented)
# ---------------------------------------------------------------------------


def test_gate_blocks_forged_approver_not_in_registry():
    pkg = build_valid_graduation_package()
    ev_hash = package_evidence_hash(pkg)
    mallory = HumanApproval(
        approver_id="mallory",  # not in DEFAULT_APPROVER_REGISTRY
        approved_at="2026-08-07T00:00:00Z",
        approval_token="i-am-not-a-signature",
        package_content_hash=ev_hash,  # correctly bound (isolates the approver check)
        notes="forged",
    )
    pkg_mallory = rebuild_graduation_package(pkg, human_approval=mallory)
    outcome = evaluate_graduation(pkg_mallory)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.approver_not_registered in outcome.blockers


def test_gate_blocks_approval_bound_to_wrong_package():
    pkg = build_valid_graduation_package()
    wrong = HumanApproval(
        approver_id="human_cc",  # in registry
        approved_at="2026-08-07T00:00:00Z",
        approval_token="signed_token_xyz",
        package_content_hash="wrong_package_hash",  # mis-bound
        notes="",
    )
    pkg_wrong = rebuild_graduation_package(pkg, human_approval=wrong)
    outcome = evaluate_graduation(pkg_wrong)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.approval_package_binding_mismatch in outcome.blockers


def test_default_approver_registry_contains_demo_approver():
    assert "human_cc" in DEFAULT_APPROVER_REGISTRY


# ---------------------------------------------------------------------------
# R1-03 (P1): gate recomputes content hashes (package / allowlist / ADR) —
# model_copy desync is rejected, never trusted as a declaration.
# ---------------------------------------------------------------------------


def test_gate_recomputes_package_hash_desync_blocked():
    pkg = build_valid_graduation_package()
    # model_copy bypasses the content_hash validator -> stale hash
    desynced = pkg.model_copy(update={"content_hash": "stale_tampered_hash"})
    outcome = evaluate_graduation(desynced)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.content_hash_mismatch in outcome.blockers
    # outcome binds to the RECOMPUTED hash, not the stale embedded one
    assert outcome.package_content_hash != "stale_tampered_hash"


def test_gate_recomputes_allowlist_hash_desync_blocked():
    pkg = build_valid_graduation_package()
    tampered_al = pkg.allowlist.model_copy(update={"content_hash": "al_tampered"})
    desynced = pkg.model_copy(update={"allowlist": tampered_al})
    outcome = evaluate_graduation(desynced)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.allowlist_content_hash_mismatch in outcome.blockers


def test_gate_recomputes_adr_hash_desync_blocked():
    pkg = build_valid_graduation_package()
    tampered_adr = pkg.adr.model_copy(update={"content_hash": "adr_tampered"})
    desynced = pkg.model_copy(update={"adr": tampered_adr})
    outcome = evaluate_graduation(desynced)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.adr_content_hash_mismatch in outcome.blockers


# ---------------------------------------------------------------------------
# R1-04 (P1): dual-copy evidence consistency — package validator (construct)
# + gate worst-case (consume, defends model_copy desync).
# ---------------------------------------------------------------------------


def test_package_validator_rejects_inconsistent_shift():
    # held_out.shift must equal shift_results (component 3 vs 4)
    pkg = build_valid_graduation_package()
    inconsistent_shift = pkg.shift_results.model_copy(update={"max_recall_drop": 0.99})
    # rebuild with held_out.shift (0.05) != shift_results (0.99) -> validator fires
    with pytest.raises(ValidationError):
        rebuild_graduation_package(pkg, shift_results=inconsistent_shift)


def test_package_validator_rejects_inconsistent_cost():
    pkg = build_valid_graduation_package()
    inconsistent_cost = pkg.cost.model_copy(update={"llm_calls": 999})
    with pytest.raises(ValidationError):
        rebuild_graduation_package(pkg, cost=inconsistent_cost)


def test_gate_blocks_shift_inconsistency_worst_case():
    # model_copy bypasses the package validator; gate takes the WORST-CASE
    # value across the two shift copies -> blocked
    pkg = build_valid_graduation_package()
    evil_shift = pkg.shift_results.model_copy(update={"max_recall_drop": 0.99})
    desynced = pkg.model_copy(update={"shift_results": evil_shift})
    outcome = evaluate_graduation(desynced)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.excessive_family_scaffold_shift in outcome.blockers


# ---------------------------------------------------------------------------
# R1-05 (P1): allowlist content match — same class_id but different
# registered content (families / chain_policy_version) is rejected.
# ---------------------------------------------------------------------------


def test_gate_blocks_class_content_drift():
    pkg = build_valid_graduation_package()
    # same class_id "hc_oh_to_c" but different families + policy version
    drifted = HypothesisClass(
        class_id="hc_oh_to_c",
        description="hydroxyl-to-carbonyl agent-proposed class",
        transformation_family_ids=["fam_evil_unvetted"],  # different
        chain_policy_version="9.9.9",  # different
    )
    pkg_drifted = rebuild_graduation_package(pkg, hypothesis_class=drifted)
    outcome = evaluate_graduation(pkg_drifted)
    assert outcome.status is GraduationStatus.blocked
    assert BlockerReasonCode.class_content_drift in outcome.blockers


# ---------------------------------------------------------------------------
# R1-06 (P2): added_incorrect is required (no default 0 masquerading as
# a measured zero).
# ---------------------------------------------------------------------------


def test_added_incorrect_required_no_default():
    # omitting added_incorrect must raise (no silent 0)
    with pytest.raises(ValidationError):
        HeldOutResults(
            # added_incorrect deliberately omitted
            incremental_recall=0.5,
            risk_at_fixed_coverage=0.1,
            abstention_impact=0.1,
            repeated_run_agreement=0.95,
            grounding_score=0.9,
            invented_id_or_structure_mutations=0,
            cost=CostRecord(llm_calls=0, tool_calls=2, latency_ms=80),
            shift=_shift(),
        )


# ---------------------------------------------------------------------------
# R1-07 (P2): hygiene — blockers deduplicated; coverage_curve typed;
# ShiftResult.risk bounded.
# ---------------------------------------------------------------------------


def test_blockers_deduplicated():
    # both shift + risk copies exceed thresholds -> each reason appears ONCE
    pkg = build_valid_graduation_package()
    evil_held_out = pkg.held_out_results.model_copy(
        update={"risk_at_fixed_coverage": 0.9}
    )
    evil_risk_cov = pkg.risk_coverage.model_copy(update={"risk_at_fixed_coverage": 0.9})
    desynced = pkg.model_copy(
        update={"held_out_results": evil_held_out, "risk_coverage": evil_risk_cov}
    )
    outcome = evaluate_graduation(desynced)
    assert outcome.blockers.count(BlockerReasonCode.risk_exceeds_threshold) == 1


def test_coverage_curve_typed_model():
    pt = CoveragePoint(coverage=0.95, risk=0.1)
    assert pt.coverage == 0.95
    # a typed point rejects unknown fields / bad types
    with pytest.raises(ValidationError):
        CoveragePoint(coverage="high", risk=0.1)  # type: ignore[arg-type]
    # RiskCoverage.coverage_curve accepts CoveragePoint, rejects raw bad dict
    rc = RiskCoverage(
        risk_at_fixed_coverage=0.1, fixed_coverage=0.95, coverage_curve=[pt]
    )
    assert rc.coverage_curve[0].risk == 0.1


def test_shift_result_risk_upper_bound():
    # risk is a rate in [0.0, 1.0]
    with pytest.raises(ValidationError):
        ShiftResult(family_id="f", scaffold="s", recall=0.5, risk=1.5, n_held_out=10)


def test_dead_blocker_codes_not_emitted():
    # the previously-dead "missing X" codes are removed from the enum
    dead = {
        "missing_hypothesis_class",
        "incomplete_held_out_evaluation",
        "missing_shift_results",
        "missing_risk_coverage",
        "missing_grounding",
        "missing_cost",
        "missing_adr",
        "missing_version_pin",
    }
    emitted = {b.value for b in BlockerReasonCode}
    assert dead.isdisjoint(emitted)
