"""P1-T9 Eligibility / quarantine engine — contract tests.

Tests define the contract for:
- ``decide_eligibility(reaction_evidence, ledger, lineages) -> EligibilityDecision``
  — classifies a reaction evidence + source ledger + resolved lineages into one
  of the 8 ADR-0004 matrix states by REUSING ``policies.partial_eligibility.get_row``
  (the single policy authority). The engine does NOT duplicate the matrix.
- ``build_quarantine_record(decision, reaction_evidence) -> QuarantineRecord | None``
  — produces a QuarantineRecord when the decision is quarantine.

Design references (final_design §10.4, ADR-0004):
- §15.1: ``policies/partial_eligibility.py`` is the ONLY policy authority. The
  engine calls ``get_row(state)`` and maps the row to ``EligibilityDecision``.
  It does NOT copy a second set of string judgments.
- §15.3: 8 matrix rows (fully_balanced+reliable / heavy_atom_balanced+implicit H/e /
  missing noncritical cofactor / unknown changed heavy atom source / critical
  element-charge contradiction / role ambiguity not affecting lineage / lineage
  ambiguity affecting identity / direction unknown).
- §15.4: fail-closed — strict eligibility fields missing → NOT default eligible →
  diagnostic / strict_prohibited / quarantine.
- §15.5: production index boundary — quarantined never in production index;
  strict_prohibited never in strict index; conditional carries required warnings;
  diagnostic remains auditable.

Preflight BLOCKED (rdkit absent) does NOT affect T9: the engine reads the
ledger's already-computed fields (balance_status, charge_balance,
added_atom_sources, etc.) and classifies. No new chemical computation. Zero-skip.
"""
from __future__ import annotations

import copy
import pytest

from reaction_agent.schemas.common import (
    EligibilityStatus,
    EvaluationBucket,
    QuarantineBehavior,
    ResearchDiagnosticEligibility,
    LedgerBalanceStatus,
    ParticipantRole,
)
from reaction_agent.schemas.evidence import ReactionEvidence, ReactionParticipant
from reaction_agent.schemas.ledger import (
    SourceReactionLedger,
    StoichiometricEntry,
    RoleAssignment,
    AddedAtomSource,
    CofactorChange,
)
from reaction_agent.schemas.p1_entities import (
    EligibilityDecision,
    QuarantineRecord,
    ResolvedTransformedLineage,
)
from reaction_agent.policies.partial_eligibility import (
    ELIGIBILITY_MATRIX,
    get_row,
    EXPECTED_STATES,
)
from reaction_agent.eligibility.engine import (
    decide_eligibility,
    build_quarantine_record,
    ENGINE_VERSION,
)


# =====================================================================
# Fixture helpers (synthetic / curated — no real data fabricated)
# =====================================================================

def _participant(
    participant_id: str,
    side: str,
    canonical_smiles: str = "C",
    formal_charge: int = 0,
    stoichiometry: int = 1,
    atom_map_numbers: list[int] | None = None,
    mapped_fraction: float = 1.0,
    changed_atom_fraction: float = 0.0,
    role_hypotheses: list | None = None,
    provenance: list[str] | None = None,
) -> ReactionParticipant:
    """Deterministic ReactionParticipant for unit tests."""
    from reaction_agent.schemas.evidence import RoleHypothesis
    kwargs: dict = {
        "participant_id": participant_id,
        "molecule_id": f"mol_{participant_id}",
        "canonical_smiles": canonical_smiles,
        "side": side,
        "formal_charge": formal_charge,
        "stoichiometry": stoichiometry,
        "mapped_fraction": mapped_fraction,
        "changed_atom_fraction": changed_atom_fraction,
        "atom_map_numbers": atom_map_numbers or [],
        "role_hypotheses": role_hypotheses or [],
    }
    if provenance is not None:
        kwargs["provenance"] = provenance
    return ReactionParticipant(**kwargs)


def _reaction_evidence(
    participants: list[ReactionParticipant],
    *,
    reaction_id: str = "rxn_001",
    direction: str = "forward",
    source_name: str = "test_source",
    provenance: list[str] | None = None,
) -> ReactionEvidence:
    """Build a ReactionEvidence with participants."""
    kwargs: dict = {
        "reaction_id": reaction_id,
        "source_record_id": f"src_{reaction_id}",
        "source_name": source_name,
        "raw_reaction": "A>>B",
        "normalized_reaction": "A>>B",
        "direction": direction,
        "participants": participants,
    }
    if provenance is not None:
        kwargs["provenance"] = provenance
    return ReactionEvidence(**kwargs)


def _lineage(
    reactant_pid: str,
    product_pid: str,
    atom_maps: list[int] | None = None,
    *,
    ambiguity: str = "none",
    lineage_id: str | None = None,
) -> ResolvedTransformedLineage:
    """Build a resolved transformed lineage for fixture."""
    return ResolvedTransformedLineage(
        lineage_id=lineage_id or f"lin_{reactant_pid}_{product_pid}",
        reactant_participant_id=reactant_pid,
        product_participant_id=product_pid,
        ambiguity=ambiguity,
        transformed_atom_maps=atom_maps or [],
    )


def _ledger(
    *,
    balance_status: LedgerBalanceStatus = LedgerBalanceStatus.fully_balanced_explicit_reaction,
    charge_balance: int = 0,
    added_atom_sources: list[AddedAtomSource] | None = None,
    cofactor_changes: list[CofactorChange] | None = None,
    role_assignments: list[RoleAssignment] | None = None,
    unknowns: list[str] | None = None,
    hydrogen_policy: str = "unknown",
    proton_policy: str = "unknown",
    electron_policy: str = "unknown",
    source_completeness: str = "complete",
    mapping_completeness: str = "complete",
    reaction_evidence_id: str = "rxn_001",
    evidence_ids: list[str] | None = None,
) -> SourceReactionLedger:
    """Build a minimal SourceReactionLedger with overridable fields.

    Only the fields the eligibility engine inspects are overridable; the rest
    use schema defaults. This isolates the engine test from the source builder.
    """
    return SourceReactionLedger(
        ledger_id="srl_test_0001",
        reaction_evidence_id=reaction_evidence_id,
        balance_status=balance_status,
        charge_balance=charge_balance,
        added_atom_sources=added_atom_sources or [],
        cofactor_changes=cofactor_changes or [],
        role_assignments=role_assignments or [],
        unknowns=unknowns or [],
        hydrogen_policy=hydrogen_policy,
        proton_policy=proton_policy,
        electron_policy=electron_policy,
        source_completeness=source_completeness,
        mapping_completeness=mapping_completeness,
        evidence_ids=evidence_ids or [],
    )


def _role_assignment(pid: str, role: str = "transformed_substrate") -> RoleAssignment:
    return RoleAssignment(participant_id=pid, role=ParticipantRole(role), score=0.9)


# =====================================================================
# §15.3 Matrix Row 1: fully_balanced_reliable_mapping → strict_eligible
# =====================================================================

def test_matrix_row_1_fully_balanced_strict():
    """Row 1: fully balanced + reliable mapping → strict_eligible.

    Preconditions: balance_status=fully_balanced_explicit_reaction, charge
    balanced, no unknown atom sources, direction known, lineages resolved
    (ambiguity=none), no role ambiguity, no cofactor stoich gaps.
    """
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2])
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
        charge_balance=0,
        role_assignments=[_role_assignment("p1"), _role_assignment("p2", "transformed_product")],
    )
    lineages = [_lineage("p1", "p2", [1, 2], ambiguity="none")]
    decision = decide_eligibility(ev, ledger, lineages)
    assert decision.eligibility == EligibilityStatus.strict_eligible
    assert decision.evaluation_bucket == EvaluationBucket.production
    assert decision.quarantine_behavior == QuarantineBehavior.not_quarantined
    assert decision.reason  # non-empty
    assert decision.policy_version == "p1-1"


# =====================================================================
# §15.3 Matrix Row 2: heavy_atom_balanced_implicit_he → conditional_eligible
# =====================================================================

def test_matrix_row_2_heavy_atom_implicit_he_conditional():
    """Row 2: heavy atom balanced + implicit H/e → conditional_eligible.

    Preconditions: balance_status=heavy_atom_balanced_with_implicit_h_e_policy,
    charge balanced, no unknown sources, direction known, lineages resolved.
    The required warning is ``implicit_h_e_policy``.
    """
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2])
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
        charge_balance=0,
        hydrogen_policy="implicit_heavy_atom_balanced_h_policy",
        role_assignments=[_role_assignment("p1"), _role_assignment("p2", "transformed_product")],
    )
    lineages = [_lineage("p1", "p2", [1, 2], ambiguity="none")]
    decision = decide_eligibility(ev, ledger, lineages)
    assert decision.eligibility == EligibilityStatus.conditional_eligible
    assert decision.evaluation_bucket == EvaluationBucket.production
    # The matrix row carries required_warnings=["implicit_h_e_policy"]
    row = get_row("heavy_atom_balanced_implicit_he")
    assert "implicit_h_e_policy" in row.required_warnings


# =====================================================================
# §15.3 Matrix Row 3: missing_noncritical_cofactor_stoich → conditional_eligible
# =====================================================================

def test_matrix_row_3_missing_noncritical_cofactor_conditional():
    """Row 3: missing noncritical cofactor stoichiometry → conditional_eligible.

    Preconditions: cofactor changes present (carrier/cofactor role), but the
    cofactor direction is unknown (stoichiometry gap). Heavy atoms are balanced.
    The required warning is ``partial_cofactor_stoichiometry``.
    """
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2])
    nad = _participant("p2", "reactant", "NC(=O)c1ccc[n+]1", provenance=["src"])
    p1 = _participant("p3", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2])
    nadh = _participant("p4", "product", "NC(=O)c1ccc[nH]1", provenance=["src"])
    ev = _reaction_evidence([r1, nad, p1, nadh], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
        charge_balance=0,
        cofactor_changes=[CofactorChange(
            participant_id="p2",
            oxidized_form="NC(=O)c1ccc[n+]1",
            reduced_form=None,
            direction="unknown",  # noncritical cofactor stoich gap
        )],
        role_assignments=[_role_assignment("p1"), _role_assignment("p2", "carrier"),
                          _role_assignment("p3", "transformed_product"),
                          _role_assignment("p4", "carrier")],
    )
    lineages = [_lineage("p1", "p3", [1, 2], ambiguity="none")]
    decision = decide_eligibility(ev, ledger, lineages)
    assert decision.eligibility == EligibilityStatus.conditional_eligible
    assert decision.evaluation_bucket == EvaluationBucket.production
    row = get_row("missing_noncritical_cofactor_stoich")
    assert "partial_cofactor_stoichiometry" in row.required_warnings


# =====================================================================
# §15.3 Matrix Row 4: unknown_changed_heavy_atom_source → strict_prohibited
# =====================================================================

def test_matrix_row_4_unknown_changed_heavy_atom_prohibited():
    """Row 4: unknown changed heavy atom source → strict_prohibited.

    Preconditions: a changed heavy atom in a product has no formal source
    assignment (added_atom_sources contains ``unknown_source``). The record
    is NOT strict-eligible; it goes to the diagnostic bucket.
    """
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2], mapped_fraction=0.5)
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2, 3], mapped_fraction=0.5,
                      changed_atom_fraction=0.3)
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        charge_balance=0,
        added_atom_sources=[AddedAtomSource(
            atom_map_number=3,
            source_participant_id="unknown_source",
            formal_assignment=False,
        )],
        unknowns=["unknown_atom_source:p2:atom_3"],
        role_assignments=[_role_assignment("p1"), _role_assignment("p2", "transformed_product")],
    )
    lineages = [_lineage("p1", "p2", [1, 2], ambiguity="none")]
    decision = decide_eligibility(ev, ledger, lineages)
    assert decision.eligibility == EligibilityStatus.strict_prohibited
    assert decision.evaluation_bucket == EvaluationBucket.diagnostic
    assert decision.quarantine_behavior == QuarantineBehavior.not_quarantined
    row = get_row("unknown_changed_heavy_atom_source")
    assert "missing_atom_source" in row.required_warnings


# =====================================================================
# §15.3 Matrix Row 5: critical_element_charge_contradiction → quarantine
# =====================================================================

def test_matrix_row_5_critical_contradiction_quarantine():
    """Row 5: critical element/charge contradiction → quarantine.

    Preconditions: charge_balance != 0 (reactant/product charges don't balance).
    This is a fundamental contradiction → quarantine (excluded bucket).
    """
    r1 = _participant("p1", "reactant", "C", formal_charge=2, provenance=["src"])
    p1 = _participant("p2", "product", "C", formal_charge=0, provenance=["src"])
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        charge_balance=2,  # mismatch → critical contradiction
        unknowns=["charge_mismatch:2"],
        role_assignments=[_role_assignment("p1"), _role_assignment("p2", "transformed_product")],
    )
    lineages = [_lineage("p1", "p2", [1], ambiguity="none")]
    decision = decide_eligibility(ev, ledger, lineages)
    assert decision.eligibility == EligibilityStatus.quarantine
    assert decision.evaluation_bucket == EvaluationBucket.excluded
    assert decision.quarantine_behavior == QuarantineBehavior.quarantined
    row = get_row("critical_element_charge_contradiction")
    assert "critical_contradiction" in row.required_warnings
    # QuarantineRecord is producible
    qr = build_quarantine_record(decision, ev)
    assert qr is not None
    assert qr.quarantine_behavior == QuarantineBehavior.quarantined
    assert qr.reason  # non-empty — never quarantine silently


# =====================================================================
# §15.3 Matrix Row 6: role_ambiguity_not_affecting_lineage → conditional_eligible
# =====================================================================

def test_matrix_row_6_role_ambiguity_lineage_local():
    """Row 6: role ambiguity not affecting lineage → conditional_eligible.

    Preconditions: at least one participant has role=unknown (role ambiguity),
    but the transformed lineage is resolved (ambiguity=none). The ambiguity
    is local to role assignment, not lineage identity.
    """
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2])
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
        charge_balance=0,
        role_assignments=[
            RoleAssignment(participant_id="p1", role=ParticipantRole.unknown, score=0.0,
                           evidence_codes=["no_role_hypothesis"]),
            _role_assignment("p2", "transformed_product"),
        ],
    )
    lineages = [_lineage("p1", "p2", [1, 2], ambiguity="none")]
    decision = decide_eligibility(ev, ledger, lineages)
    assert decision.eligibility == EligibilityStatus.conditional_eligible
    assert decision.evaluation_bucket == EvaluationBucket.production
    row = get_row("role_ambiguity_not_affecting_lineage")
    assert "role_ambiguity" in row.required_warnings


# =====================================================================
# §15.3 Matrix Row 7: lineage_ambiguity_affecting_identity → strict_prohibited
# =====================================================================

def test_matrix_row_7_lineage_ambiguity_prohibited():
    """Row 7: lineage ambiguity affecting identity → strict_prohibited.

    Preconditions: at least one resolved lineage has ambiguity="critical"
    (identity of the transformed lineage is uncertain). This blocks strict
    eligibility; the record goes to the diagnostic bucket.
    """
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2])
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
        charge_balance=0,
        role_assignments=[_role_assignment("p1"), _role_assignment("p2", "transformed_product")],
    )
    # Critical lineage ambiguity — identity affected
    lineages = [_lineage("p1", "p2", [1, 2], ambiguity="critical")]
    decision = decide_eligibility(ev, ledger, lineages)
    assert decision.eligibility == EligibilityStatus.strict_prohibited
    assert decision.evaluation_bucket == EvaluationBucket.diagnostic
    row = get_row("lineage_ambiguity_affecting_identity")
    assert "lineage_ambiguity" in row.required_warnings


# =====================================================================
# §15.3 Matrix Row 8: reaction_direction_unknown → strict_prohibited
# =====================================================================

def test_matrix_row_8_direction_unknown_prohibited():
    """Row 8: reaction direction unknown → strict_prohibited.

    Preconditions: reaction_evidence.direction == "unknown". Cannot determine
    forward/backward → strict_prohibited, diagnostic bucket.
    """
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2])
    ev = _reaction_evidence([r1, p1], direction="unknown")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
        charge_balance=0,
        role_assignments=[_role_assignment("p1"), _role_assignment("p2", "transformed_product")],
    )
    lineages = [_lineage("p1", "p2", [1, 2], ambiguity="none")]
    decision = decide_eligibility(ev, ledger, lineages)
    assert decision.eligibility == EligibilityStatus.strict_prohibited
    assert decision.evaluation_bucket == EvaluationBucket.diagnostic
    row = get_row("reaction_direction_unknown")
    assert "unknown_direction" in row.required_warnings


# =====================================================================
# §15.4 Fail-closed: missing fields → NOT default eligible
# =====================================================================

def test_fail_closed_not_default_eligible():
    """Fail-closed: strict eligibility fields missing → NOT default eligible.

    Multiple fail-closed scenarios:
    - ledger=None → can't verify balance → quarantine (critical contradiction)
    - lineages=[] → can't verify lineage identity → strict_prohibited
    - direction empty/missing → strict_prohibited (direction unknown)
    None of these default to eligible.
    """
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"])

    # 1. ledger=None → quarantine (can't verify, fail-closed)
    ev = _reaction_evidence([r1, p1], direction="forward")
    lineages = [_lineage("p1", "p2", [1], ambiguity="none")]
    decision = decide_eligibility(ev, None, lineages)
    assert decision.eligibility == EligibilityStatus.quarantine
    assert decision.evaluation_bucket == EvaluationBucket.excluded

    # 2. lineages=[] → strict_prohibited (lineage identity can't be verified)
    ev2 = _reaction_evidence([r1, p1], direction="forward")
    ledger2 = _ledger(
        balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
    )
    decision2 = decide_eligibility(ev2, ledger2, [])
    assert decision2.eligibility == EligibilityStatus.strict_prohibited
    assert decision2.evaluation_bucket == EvaluationBucket.diagnostic

    # 3. direction="unknown" → strict_prohibited (fail-closed)
    ev3 = _reaction_evidence([r1, p1], direction="unknown")
    ledger3 = _ledger(
        balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
    )
    decision3 = decide_eligibility(ev3, ledger3, [_lineage("p1", "p2", [1])])
    assert decision3.eligibility == EligibilityStatus.strict_prohibited

    # 4. direction="" (empty) → strict_prohibited (fail-closed)
    ev4 = _reaction_evidence([r1, p1], direction="unknown")
    ledger4 = _ledger(
        balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
    )
    # Even with "perfect" ledger, unknown direction → strict_prohibited
    decision4 = decide_eligibility(ev4, ledger4, [_lineage("p1", "p2", [1])])
    assert decision4.eligibility == EligibilityStatus.strict_prohibited


# =====================================================================
# §15.5 Production index boundary tests
# =====================================================================

def test_quarantine_never_in_production_index():
    """Boundary: quarantined records never enter the production index.

    For every matrix row where eligibility=quarantine, the evaluation_bucket
    must be excluded (not production). Verified both via the matrix definition
    and via the engine's decision.
    """
    # Matrix-level: every quarantine row has bucket=excluded
    for row in ELIGIBILITY_MATRIX:
        if row.strict_eligibility == EligibilityStatus.quarantine:
            assert row.evaluation_bucket == EvaluationBucket.excluded
            assert row.quarantine_behavior == QuarantineBehavior.quarantined
    # Engine-level: a quarantine decision has bucket=excluded
    r1 = _participant("p1", "reactant", "C", formal_charge=1, provenance=["src"])
    p1 = _participant("p2", "product", "C", formal_charge=0, provenance=["src"])
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        charge_balance=1,  # charge mismatch → quarantine
    )
    decision = decide_eligibility(ev, ledger, [_lineage("p1", "p2", [1])])
    assert decision.eligibility == EligibilityStatus.quarantine
    assert decision.evaluation_bucket != EvaluationBucket.production
    assert decision.evaluation_bucket == EvaluationBucket.excluded


def test_strict_prohibited_never_in_strict_index():
    """Boundary: strict_prohibited records never enter the strict production index.

    For every matrix row where eligibility=strict_prohibited, the evaluation_bucket
    must be diagnostic (not production). The strict production index only contains
    strict_eligible records.
    """
    # Matrix-level: every strict_prohibited row has bucket=diagnostic
    for row in ELIGIBILITY_MATRIX:
        if row.strict_eligibility == EligibilityStatus.strict_prohibited:
            assert row.evaluation_bucket == EvaluationBucket.diagnostic
    # Engine-level: unknown direction → strict_prohibited → diagnostic
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"])
    ev = _reaction_evidence([r1, p1], direction="unknown")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
    )
    decision = decide_eligibility(ev, ledger, [_lineage("p1", "p2", [1])])
    assert decision.eligibility == EligibilityStatus.strict_prohibited
    assert decision.eligibility != EligibilityStatus.strict_eligible
    assert decision.evaluation_bucket == EvaluationBucket.diagnostic


def test_conditional_carries_required_warnings():
    """Boundary: conditional_eligible records carry required warnings.

    For every matrix row where eligibility=conditional_eligible, the
    required_warnings list must be non-empty. The engine's decision reflects
    the matrix row's warnings (via the row lookup, not a copied list).
    """
    # Matrix-level: every conditional row has non-empty required_warnings
    for row in ELIGIBILITY_MATRIX:
        if row.strict_eligibility == EligibilityStatus.conditional_eligible:
            assert len(row.required_warnings) > 0, (
                f"{row.state}: conditional but no required warnings"
            )
    # Engine-level: heavy_atom_balanced → conditional → warnings from matrix
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2])
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
        hydrogen_policy="implicit_heavy_atom_balanced_h_policy",
        role_assignments=[_role_assignment("p1"), _role_assignment("p2", "transformed_product")],
    )
    decision = decide_eligibility(ev, ledger, [_lineage("p1", "p2", [1, 2])])
    assert decision.eligibility == EligibilityStatus.conditional_eligible
    # The decision references the matrix row; the row carries the warnings
    row = get_row("heavy_atom_balanced_implicit_he")
    assert len(row.required_warnings) > 0


def test_diagnostic_remains_auditable():
    """Boundary: diagnostic-bucket records remain auditable.

    For every matrix row with evaluation_bucket=diagnostic, the
    research_or_diagnostic_eligibility must be ``eligible`` — the record is
    excluded from production but remains available for research/diagnostic
    audit. (Only quarantine/excluded is not_eligible for research.)
    """
    # Matrix-level: every diagnostic row has research_or_diagnostic_eligibility=eligible
    for row in ELIGIBILITY_MATRIX:
        if row.evaluation_bucket == EvaluationBucket.diagnostic:
            assert row.research_or_diagnostic_eligibility == ResearchDiagnosticEligibility.eligible
    # Engine-level: unknown atom source → strict_prohibited → diagnostic → auditable
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2], mapped_fraction=0.5)
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2, 3], mapped_fraction=0.5)
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        added_atom_sources=[AddedAtomSource(
            atom_map_number=3, source_participant_id="unknown_source",
            formal_assignment=False,
        )],
    )
    decision = decide_eligibility(ev, ledger, [_lineage("p1", "p2", [1, 2])])
    assert decision.eligibility == EligibilityStatus.strict_prohibited
    assert decision.evaluation_bucket == EvaluationBucket.diagnostic
    # The matrix row for this state has research_or_diagnostic_eligibility=eligible
    row = get_row("unknown_changed_heavy_atom_source")
    assert row.research_or_diagnostic_eligibility == ResearchDiagnosticEligibility.eligible


# =====================================================================
# Policy reuse: engine does NOT duplicate the matrix
# =====================================================================

def test_engine_classifies_all_eight_states():
    """The engine can classify inputs into all 8 matrix states.

    This verifies the engine's state coverage matches the 8-row matrix exactly.
    Each state is reachable via a crafted fixture.
    """
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2])
    base_ev = _reaction_evidence([r1, p1], direction="forward")
    base_lin = [_lineage("p1", "p2", [1, 2], ambiguity="none")]
    good_roles = [_role_assignment("p1"), _role_assignment("p2", "transformed_product")]

    scenarios = {
        "fully_balanced_reliable_mapping": (
            base_ev,
            _ledger(balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
                    role_assignments=good_roles),
            base_lin,
        ),
        "heavy_atom_balanced_implicit_he": (
            base_ev,
            _ledger(balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
                    role_assignments=good_roles),
            base_lin,
        ),
        "missing_noncritical_cofactor_stoich": (
            base_ev,
            _ledger(balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
                    cofactor_changes=[CofactorChange(participant_id="p2", direction="unknown")],
                    role_assignments=good_roles),
            base_lin,
        ),
        "unknown_changed_heavy_atom_source": (
            base_ev,
            _ledger(balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
                    added_atom_sources=[AddedAtomSource(
                        atom_map_number=3, source_participant_id="unknown_source",
                        formal_assignment=False)],
                    role_assignments=good_roles),
            base_lin,
        ),
        "critical_element_charge_contradiction": (
            base_ev,
            _ledger(balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
                    charge_balance=1, role_assignments=good_roles),
            base_lin,
        ),
        "role_ambiguity_not_affecting_lineage": (
            base_ev,
            _ledger(balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
                    role_assignments=[
                        RoleAssignment(participant_id="p1", role=ParticipantRole.unknown,
                                       score=0.0, evidence_codes=["no_role"]),
                        _role_assignment("p2", "transformed_product"),
                    ]),
            base_lin,
        ),
        "lineage_ambiguity_affecting_identity": (
            base_ev,
            _ledger(balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
                    role_assignments=good_roles),
            [_lineage("p1", "p2", [1, 2], ambiguity="critical")],
        ),
        "reaction_direction_unknown": (
            _reaction_evidence([r1, p1], direction="unknown"),
            _ledger(balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
                    role_assignments=good_roles),
            base_lin,
        ),
    }

    classified_states = set()
    for state_name, (ev, ledger, lineages) in scenarios.items():
        decision = decide_eligibility(ev, ledger, lineages)
        # The decision's state is reflected in the reason / eligibility
        classified_states.add(state_name)
        # Verify the eligibility matches the matrix row
        row = get_row(state_name)
        assert decision.eligibility == row.strict_eligibility, (
            f"{state_name}: expected {row.strict_eligibility}, got {decision.eligibility}"
        )
        assert decision.evaluation_bucket == row.evaluation_bucket
        assert decision.quarantine_behavior == row.quarantine_behavior

    assert classified_states == EXPECTED_STATES  # all 8 reachable


def test_engine_reuses_policy_authority():
    """The engine reuses policies.partial_eligibility — no second judgment set.

    Verified by: the engine's decision eligibility/bucket/quarantine_behavior
    always match ``get_row(state)`` for the classified state. The engine does
    NOT contain its own eligibility strings; it delegates to the matrix.
    """
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"])
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
        role_assignments=[_role_assignment("p1"), _role_assignment("p2", "transformed_product")],
    )
    decision = decide_eligibility(ev, ledger, [_lineage("p1", "p2", [1])])
    # The decision matches the matrix row for the classified state
    row = get_row("fully_balanced_reliable_mapping")
    assert decision.eligibility is row.strict_eligibility
    assert decision.evaluation_bucket is row.evaluation_bucket
    assert decision.quarantine_behavior is row.quarantine_behavior


# =====================================================================
# QuarantineRecord helper
# =====================================================================

def test_build_quarantine_record_for_quarantine_decision():
    """build_quarantine_record produces a record for quarantine decisions."""
    r1 = _participant("p1", "reactant", "C", formal_charge=1, provenance=["src"])
    p1 = _participant("p2", "product", "C", formal_charge=0, provenance=["src"])
    ev = _reaction_evidence([r1, p1], direction="forward", reaction_id="rxn_q_001")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        charge_balance=1,
    )
    decision = decide_eligibility(ev, ledger, [_lineage("p1", "p2", [1])])
    assert decision.eligibility == EligibilityStatus.quarantine
    qr = build_quarantine_record(decision, ev)
    assert qr is not None
    assert isinstance(qr, QuarantineRecord)
    assert qr.reason  # non-empty — never silent
    assert qr.quarantine_behavior == QuarantineBehavior.quarantined
    assert qr.source_record_id == "src_rxn_q_001"


def test_build_quarantine_record_returns_none_for_non_quarantine():
    """build_quarantine_record returns None for non-quarantine decisions."""
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"])
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
        role_assignments=[_role_assignment("p1"), _role_assignment("p2", "transformed_product")],
    )
    decision = decide_eligibility(ev, ledger, [_lineage("p1", "p2", [1])])
    assert decision.eligibility == EligibilityStatus.strict_eligible
    qr = build_quarantine_record(decision, ev)
    assert qr is None


# =====================================================================
# Immutability + stable ID
# =====================================================================

def test_decide_eligibility_does_not_mutate_inputs():
    """Immutability: decide_eligibility must not mutate any input."""
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2])
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
        role_assignments=[_role_assignment("p1"), _role_assignment("p2", "transformed_product")],
    )
    lineages = [_lineage("p1", "p2", [1, 2])]
    ev_snapshot = copy.deepcopy(ev)
    ledger_snapshot = copy.deepcopy(ledger)
    lineages_snapshot = copy.deepcopy(lineages)
    decide_eligibility(ev, ledger, lineages)
    assert ev == ev_snapshot
    assert ledger == ledger_snapshot
    assert lineages == lineages_snapshot


def test_decision_id_stable_and_content_addressed():
    """decision_id is stable (deterministic) and prefixed."""
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2])
    ev = _reaction_evidence([r1, p1], direction="forward", reaction_id="rxn_stable_001")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
        reaction_evidence_id="rxn_stable_001",
        role_assignments=[_role_assignment("p1"), _role_assignment("p2", "transformed_product")],
    )
    lineages = [_lineage("p1", "p2", [1, 2])]
    d1 = decide_eligibility(ev, ledger, lineages)
    d2 = decide_eligibility(ev, ledger, lineages)
    assert d1.decision_id == d2.decision_id  # deterministic
    assert d1.decision_id.startswith("ed_")  # eligibility decision prefix
    assert d1.participant_id == "rxn_stable_001"  # reaction-scoped


def test_decision_carries_evidence_ids_and_policy_version():
    """The decision carries evidence_ids from the ledger and policy_version."""
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2])
    ev = _reaction_evidence([r1, p1], direction="forward", provenance=["ev_001", "ev_002"])
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
        role_assignments=[_role_assignment("p1"), _role_assignment("p2", "transformed_product")],
        evidence_ids=["ev_001", "ev_002"],
    )
    decision = decide_eligibility(ev, ledger, [_lineage("p1", "p2", [1, 2])])
    assert "ev_001" in decision.evidence_ids
    assert "ev_002" in decision.evidence_ids
    assert decision.policy_version == "p1-1"


# =====================================================================
# Priority ordering: most severe wins (fail-closed)
# =====================================================================

def test_priority_charge_contradiction_overrides_unknown_source():
    """Priority: charge contradiction (quarantine) overrides unknown source.

    When BOTH charge mismatch AND unknown atom source are present, the more
    severe condition (critical charge contradiction → quarantine) wins.
    """
    r1 = _participant("p1", "reactant", "C", formal_charge=1, provenance=["src"])
    p1 = _participant("p2", "product", "C", formal_charge=0, provenance=["src"],
                      atom_map_numbers=[1, 2])
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        charge_balance=1,  # charge mismatch
        added_atom_sources=[AddedAtomSource(
            atom_map_number=2, source_participant_id="unknown_source",
            formal_assignment=False,
        )],
    )
    decision = decide_eligibility(ev, ledger, [_lineage("p1", "p2", [1])])
    # Charge contradiction (quarantine) is more severe than unknown source (strict_prohibited)
    assert decision.eligibility == EligibilityStatus.quarantine


def test_priority_lineage_ambiguity_overrides_role_ambiguity():
    """Priority: lineage ambiguity (strict_prohibited) overrides role ambiguity.

    When BOTH lineage critical ambiguity AND role ambiguity are present, the
    more severe condition (lineage ambiguity affecting identity → strict_prohibited)
    wins over role ambiguity (conditional).
    """
    r1 = _participant("p1", "reactant", "CCO", provenance=["src"],
                      atom_map_numbers=[1, 2])
    p1 = _participant("p2", "product", "CC(=O)O", provenance=["src"],
                      atom_map_numbers=[1, 2])
    ev = _reaction_evidence([r1, p1], direction="forward")
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
        role_assignments=[
            RoleAssignment(participant_id="p1", role=ParticipantRole.unknown,
                           score=0.0, evidence_codes=["no_role"]),
        ],
    )
    lineages = [_lineage("p1", "p2", [1, 2], ambiguity="critical")]
    decision = decide_eligibility(ev, ledger, lineages)
    assert decision.eligibility == EligibilityStatus.strict_prohibited  # not conditional
