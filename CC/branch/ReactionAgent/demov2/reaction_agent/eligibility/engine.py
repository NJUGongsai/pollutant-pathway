"""Eligibility / quarantine engine (final_design §10.4, ADR-0004 §15).

``decide_eligibility`` classifies a ReactionEvidence + SourceReactionLedger +
resolved transformed lineages into one of the 8 ADR-0004 matrix states, then
delegates the eligibility / bucket / quarantine decision to
``policies.partial_eligibility.get_row(state)`` — the ONLY policy authority
(§15.1). The engine does NOT duplicate the matrix or carry a second set of
eligibility strings.

Classification priority (§15.4 fail-closed — most severe wins):
1. ``critical_element_charge_contradiction`` (quarantine) — ledger is None OR
   charge_balance != 0. Cannot verify charge conservation → quarantine.
2. ``lineage_ambiguity_affecting_identity`` (strict_prohibited) — lineages list
   is empty OR any lineage has ambiguity="critical". Identity uncertain.
3. ``reaction_direction_unknown`` (strict_prohibited) — direction field is
   "unknown" or empty. Cannot determine forward/backward.
4. ``unknown_changed_heavy_atom_source`` (strict_prohibited) — any
   AddedAtomSource has source_participant_id="unknown_source". A changed heavy
   atom has no traceable formal source.
5. ``role_ambiguity_not_affecting_lineage`` (conditional) — any RoleAssignment
   has role=unknown, but lineages are resolved. Roles unclear, identity ok.
6. ``missing_noncritical_cofactor_stoich`` (conditional) — cofactor_changes
   present with direction="unknown" (stoichiometry gap for noncritical cofactor).
7. ``heavy_atom_balanced_implicit_he`` (conditional) — balance_status is
   heavy_atom_balanced_with_implicit_h_e_policy. H/e balance is implicit.
8. ``fully_balanced_reliable_mapping`` (strict_eligible) — balance_status is
   fully_balanced_explicit_reaction. Everything verified.

Fail-closed (§15.4): if ledger is None, lineages empty, or direction missing,
the engine NEVER defaults to eligible. It routes to quarantine or
strict_prohibited per the priority above. If the balance_status is
partial_or_unbalanced but none of the specific severe conditions match (e.g.
source/mapping incomplete), the engine fails-closed to
``unknown_changed_heavy_atom_source`` (not strict eligible).

Production index boundary (§15.5): the matrix row's evaluation_bucket and
quarantine_behavior enforce the boundary — quarantine → excluded,
strict_prohibited → diagnostic, conditional → production (with warnings),
strict_eligible → production.

Immutability: ``decide_eligibility`` does NOT mutate any input.
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash, stable_id
from reaction_agent.policies.partial_eligibility import get_row
from reaction_agent.schemas.common import (
    EligibilityStatus,
    EvaluationBucket,
    ParticipantRole,
    QuarantineBehavior,
)
from reaction_agent.schemas.evidence import ReactionEvidence
from reaction_agent.schemas.ledger import SourceReactionLedger
from reaction_agent.schemas.p1_entities import (
    EligibilityDecision,
    QuarantineRecord,
    ResolvedTransformedLineage,
)


# =====================================================================
# Engine version (embedded in decision_id for traceability)
# =====================================================================

ENGINE_VERSION = "p1-t9-1"
POLICY_VERSION = "p1-1"


# =====================================================================
# State classification (§15.3 + §15.4 fail-closed)
# =====================================================================

# The 8 canonical matrix state names (must match policies.partial_eligibility)
_STATE_CRITICAL_CONTRADICTION = "critical_element_charge_contradiction"
_STATE_LINEAGE_AMBIGUITY = "lineage_ambiguity_affecting_identity"
_STATE_DIRECTION_UNKNOWN = "reaction_direction_unknown"
_STATE_UNKNOWN_ATOM_SOURCE = "unknown_changed_heavy_atom_source"
_STATE_ROLE_AMBIGUITY = "role_ambiguity_not_affecting_lineage"
_STATE_MISSING_COFACTOR = "missing_noncritical_cofactor_stoich"
_STATE_HEAVY_ATOM_IMPLICIT = "heavy_atom_balanced_implicit_he"
_STATE_FULLY_BALANCED = "fully_balanced_reliable_mapping"


def _classify_state(
    reaction_evidence: ReactionEvidence,
    ledger: SourceReactionLedger | None,
    lineages: list[ResolvedTransformedLineage],
) -> str:
    """Classify the evidence into one of the 8 matrix states.

    Priority is fail-closed (§15.4): the most severe applicable condition
    wins. Missing fields (None ledger, empty lineages, unknown direction)
    NEVER default to eligible — they route to quarantine or strict_prohibited.

    Returns the state name (a key in ELIGIBILITY_MATRIX).
    """
    # -- 1. Critical element/charge contradiction (quarantine) --
    # Fail-closed: ledger is None → cannot verify balance → quarantine.
    if ledger is None:
        return _STATE_CRITICAL_CONTRADICTION
    if ledger.charge_balance != 0:
        return _STATE_CRITICAL_CONTRADICTION

    # -- 2. Lineage ambiguity affecting identity (strict_prohibited) --
    # Fail-closed: empty lineages → cannot verify identity → strict_prohibited.
    if not lineages:
        return _STATE_LINEAGE_AMBIGUITY
    has_critical_lineage = any(
        lin.ambiguity == "critical" for lin in lineages
    )
    if has_critical_lineage:
        return _STATE_LINEAGE_AMBIGUITY

    # -- 3. Reaction direction unknown (strict_prohibited) --
    direction = reaction_evidence.direction
    if not direction or direction == "unknown":
        return _STATE_DIRECTION_UNKNOWN

    # -- 4. Unknown changed heavy atom source (strict_prohibited) --
    has_unknown_source = any(
        s.source_participant_id == "unknown_source"
        for s in ledger.added_atom_sources
    )
    if has_unknown_source:
        return _STATE_UNKNOWN_ATOM_SOURCE

    # -- 5. Role ambiguity not affecting lineage (conditional) --
    # Lineages are resolved (no critical ambiguity), but at least one
    # participant has role=unknown. The ambiguity is local to roles.
    has_role_ambiguity = any(
        ra.role == ParticipantRole.unknown for ra in ledger.role_assignments
    )
    if has_role_ambiguity:
        return _STATE_ROLE_AMBIGUITY

    # -- 6. Missing noncritical cofactor stoichiometry (conditional) --
    # Cofactor changes are present, but the direction is unknown (gap in
    # noncritical cofactor stoichiometry). Heavy atoms are balanced.
    if ledger.cofactor_changes:
        has_cofactor_stoich_gap = any(
            cc.direction == "unknown" for cc in ledger.cofactor_changes
        )
        if has_cofactor_stoich_gap:
            return _STATE_MISSING_COFACTOR

    # -- 7. Heavy atom balanced with implicit H/e (conditional) --
    from reaction_agent.schemas.common import LedgerBalanceStatus
    if ledger.balance_status == LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy:
        return _STATE_HEAVY_ATOM_IMPLICIT

    # -- 8. Fully balanced + reliable mapping (strict_eligible) --
    if ledger.balance_status == LedgerBalanceStatus.fully_balanced_explicit_reaction:
        return _STATE_FULLY_BALANCED

    # -- Fail-closed default (§15.4) --
    # balance_status is partial_or_unbalanced but none of the specific severe
    # conditions above matched (e.g. source/mapping incomplete, formal
    # assignment ambiguous). Cannot confirm strict eligibility → fail-closed
    # to unknown_changed_heavy_atom_source (not strict eligible).
    return _STATE_UNKNOWN_ATOM_SOURCE


# =====================================================================
# Stable decision ID
# =====================================================================

def _decision_id(reaction_id: str, state: str) -> str:
    """Stable decision ID: reaction identity + state + engine version.

    Content-addressed via canonical_hash. Deterministic: same inputs → same ID.
    """
    payload = {
        "reaction": reaction_id,
        "state": state,
        "version": ENGINE_VERSION,
        "kind": "eligibility_decision",
    }
    return f"ed_{canonical_hash(payload)[:12]}"


# =====================================================================
# Reason code builder
# =====================================================================

def _build_reason(
    state: str,
    reaction_evidence: ReactionEvidence,
    ledger: SourceReactionLedger | None,
    lineages: list[ResolvedTransformedLineage],
) -> str:
    """Build a human-readable reason string for the classified state.

    The reason includes the state name and a brief trigger description.
    Never empty — fail-closed requires an explicit reason.
    """
    if state == _STATE_CRITICAL_CONTRADICTION:
        if ledger is None:
            return f"{state}: ledger is None (cannot verify charge/balance, fail-closed)"
        return f"{state}: charge_balance={ledger.charge_balance} (reactant/product charges mismatch)"

    if state == _STATE_LINEAGE_AMBIGUITY:
        if not lineages:
            return f"{state}: no resolved lineages (cannot verify identity, fail-closed)"
        critical = [lin.lineage_id for lin in lineages if lin.ambiguity == "critical"]
        return f"{state}: critical lineage ambiguity in {critical}"

    if state == _STATE_DIRECTION_UNKNOWN:
        return f"{state}: direction='{reaction_evidence.direction}' (cannot determine forward/backward)"

    if state == _STATE_UNKNOWN_ATOM_SOURCE:
        unknown_atoms = [
            s.atom_map_number for s in ledger.added_atom_sources
            if s.source_participant_id == "unknown_source"
        ]
        return f"{state}: changed heavy atoms {unknown_atoms} have no formal source"

    if state == _STATE_ROLE_AMBIGUITY:
        unknown_pids = [
            ra.participant_id for ra in ledger.role_assignments
            if ra.role == ParticipantRole.unknown
        ]
        return f"{state}: participants {unknown_pids} have unknown role (lineage unaffected)"

    if state == _STATE_MISSING_COFACTOR:
        unknown_cofactors = [
            cc.participant_id for cc in ledger.cofactor_changes
            if cc.direction == "unknown"
        ]
        return f"{state}: cofactors {unknown_cofactors} have unknown stoichiometry direction"

    if state == _STATE_HEAVY_ATOM_IMPLICIT:
        return f"{state}: heavy atoms balanced, H/e policy implicit (balance_status={ledger.balance_status.value})"

    if state == _STATE_FULLY_BALANCED:
        return f"{state}: fully balanced explicit reaction, all atoms sourced, direction known"

    # Defensive — should never reach here
    return f"{state}: (unclassified trigger)"


# =====================================================================
# Evidence ID collection
# =====================================================================

def _collect_evidence_ids(
    reaction_evidence: ReactionEvidence,
    ledger: SourceReactionLedger | None,
) -> list[str]:
    """Collect evidence IDs from reaction provenance + ledger.

    Deduplicated, order-preserving. If ledger is None, uses only reaction
    provenance.
    """
    ids: list[str] = []
    for eid in reaction_evidence.provenance:
        if eid not in ids:
            ids.append(eid)
    if ledger is not None:
        for eid in ledger.evidence_ids:
            if eid not in ids:
                ids.append(eid)
    return ids


# =====================================================================
# Public API
# =====================================================================

def decide_eligibility(
    reaction_evidence: ReactionEvidence,
    ledger: SourceReactionLedger | None,
    lineages: list[ResolvedTransformedLineage],
) -> EligibilityDecision:
    """Decide production-side eligibility for a reaction evidence record.

    Classifies the evidence into one of 8 ADR-0004 matrix states by inspecting
    the ledger (balance_status, charge_balance, added_atom_sources,
    cofactor_changes, role_assignments), the reaction direction, and the
    resolved lineages (ambiguity). Then delegates to
    ``policies.partial_eligibility.get_row(state)`` — the ONLY policy authority
    — to obtain the authoritative eligibility / bucket / quarantine /
    warnings. The engine does NOT duplicate the matrix.

    Fail-closed (§15.4): missing fields (None ledger, empty lineages, unknown
    direction) → NOT default eligible → quarantine or strict_prohibited.

    Production index boundary (§15.5): enforced by the matrix row's
    evaluation_bucket and quarantine_behavior — quarantine → excluded,
    strict_prohibited → diagnostic, conditional → production, strict_eligible
    → production.

    The ``participant_id`` field of the decision is set to
    ``reaction_evidence.reaction_id`` (reaction-scoped decision).

    Immutability: ``reaction_evidence``, ``ledger``, and ``lineages`` are NOT
    mutated.
    """
    state = _classify_state(reaction_evidence, ledger, lineages)
    row = get_row(state)

    # The matrix row is the authority — the engine maps its fields to the
    # EligibilityDecision. No second set of eligibility strings is introduced.
    reason = _build_reason(state, reaction_evidence, ledger, lineages)
    evidence_ids = _collect_evidence_ids(reaction_evidence, ledger)
    decision_id = _decision_id(reaction_evidence.reaction_id, state)

    return EligibilityDecision(
        decision_id=decision_id,
        participant_id=reaction_evidence.reaction_id,
        eligibility=row.strict_eligibility,
        evaluation_bucket=row.evaluation_bucket,
        quarantine_behavior=row.quarantine_behavior,
        reason=reason,
        evidence_ids=evidence_ids,
        policy_version=POLICY_VERSION,
    )


def build_quarantine_record(
    decision: EligibilityDecision,
    reaction_evidence: ReactionEvidence,
) -> QuarantineRecord | None:
    """Build a QuarantineRecord for a quarantine decision.

    Returns None if the decision is NOT quarantine (no silent quarantine of
    eligible/prohibited records). The QuarantineRecord carries a mandatory
    non-empty reason (fail-closed: never quarantine silently).

    The ``source_record_id`` links the quarantine to the original source record
    for audit traceability.
    """
    if decision.eligibility != EligibilityStatus.quarantine:
        return None

    record_id = stable_id("qr", {
        "decision_id": decision.decision_id,
        "reaction_id": reaction_evidence.reaction_id,
        "version": ENGINE_VERSION,
    })

    return QuarantineRecord(
        record_id=record_id,
        reason=decision.reason,
        category="critical_contradiction",
        evidence_ids=list(decision.evidence_ids),
        source_record_id=reaction_evidence.source_record_id,
        quarantine_behavior=QuarantineBehavior.quarantined,
        notes=f"auto-quarantined by eligibility engine ({ENGINE_VERSION}); state=critical_element_charge_contradiction",
    )
