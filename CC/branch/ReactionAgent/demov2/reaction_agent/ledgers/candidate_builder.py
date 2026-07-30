"""CandidateAnalogyLedger skeleton builder (final_design §14, ADR-0003).

``build_candidate_skeleton`` constructs a CandidateAnalogyLedger skeleton from
a SourceReactionLedger + QueryCandidateAdaptation + caller-provided
candidate_id. It inherits donor context as EXPLICIT ASSUMPTIONS and preserves
unknowns — it does NOT generate Y, rank candidates, or produce LLM rationale.

5 key invariants (§14):
1. donor_context_is_assumption = True — InheritedDonorContext.is_assumption is
   locked to True by the schema (Literal[True]); the builder populates
   inherited_donor_context from the source ledger's role assignments.
2. source_ledger_link exists — source_ledger_id is mandatory and must equal
   the input source_ledger.ledger_id (never empty, never fabricated).
3. candidate_id belongs current context — the builder does NOT generate
   candidate_id (that would be generating a candidate, forbidden). The caller
   provides candidate_id from the current context; the builder echoes it back
   verbatim and validates it is non-empty.
4. donor cofactor != proven X→Y cofactor — donor cofactors from
   source_ledger.cofactor_changes flow to ``unknown_actual_cofactors``
   (inherited assumption). The schema has NO field claiming cofactors are
   proven for X→Y.
5. formal_balance_under_assumptions != observed balance — the candidate's
   formal_balance_under_assumptions is a SEPARATE object computed under
   donor-derived assumptions, explicitly labeled via assumption_notes. It is
   NOT the source ledger's observed balance. candidate_balance_status defaults
   to partial_or_unbalanced_source (assumption-based, not observed).

No-fabrication discipline (brief §14):
- Donor cofactors/stoichiometry/co-substrates → unknown_actual_* (NOT proven
  X→Y facts).
- formal_balance_under_assumptions is explicitly labeled as assumption-based.
- Skeleton does NOT generate Y / ranking / LLM rationale / treat fixture as
  prediction.

Preflight BLOCKED (rdkit absent) does NOT affect T8: the skeleton inherits
donor context as assumptions and does not compute real element balance (that
is the source ledger's job in T7). The formal_balance_under_assumptions
copies the source's element_balance/charge_balance structure but labels it
as assumption-based — no new chemical computation.

Immutability: ``build_candidate_skeleton`` does NOT mutate ``source_ledger``
or ``adaptation``. New objects are returned throughout.
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash
from reaction_agent.schemas.common import (
    LedgerBalanceStatus,
    ParticipantRole,
)
from reaction_agent.schemas.ledger import (
    CandidateAnalogyLedger,
    CofactorChange,
    ElementBalance,
    FormalBalanceUnderAssumptions,
    InheritedDonorContext,
    QueryCandidateAdaptation,
    RoleAssignment,
    SourceReactionLedger,
    StoichiometricEntry,
)


# =====================================================================
# Builder version (embedded in ledger_id for traceability)
# =====================================================================

BUILDER_VERSION = "p1-t8-1"

# Assumption note labels (never claim proven X→Y facts)
_NOTE_DONOR_CONTEXT_ASSUMPTION = "donor_context_is_assumption:not_proven_for_xy"
_NOTE_DONOR_COFACTOR_ASSUMPTION = "donor_cofactor_inherited_as_assumption:not_proven_xy_cofactor"
_NOTE_DONOR_STOICHIOMETRY_ASSUMPTION = "donor_stoichiometry_inherited_as_assumption:not_proven_xy_stoichiometry"
_NOTE_DONOR_CO_SUBSTRATE_ASSUMPTION = "donor_co_substrate_inherited_as_assumption:not_proven_xy_co_substrate"
_NOTE_FORMAL_BALANCE_ASSUMPTION = "formal_balance_under_donor_assumptions:not_observed_for_xy"
_NOTE_CANDIDATE_BALANCE_DEFAULT = "candidate_balance_status_default:assumption_based_not_observed"


# =====================================================================
# Internal helpers
# =====================================================================

def _role_for_participant(
    role_assignments: list[RoleAssignment],
    participant_id: str,
) -> ParticipantRole:
    """Find the role assigned to a participant in the source ledger.

    Returns ParticipantRole.unknown if no assignment exists for the
    participant (honest default — never fabricate a role).
    """
    for ra in role_assignments:
        if ra.participant_id == participant_id:
            return ra.role
    return ParticipantRole.unknown


def _build_inherited_donor_context(
    source_ledger: SourceReactionLedger,
    adaptation: QueryCandidateAdaptation,
) -> list[InheritedDonorContext]:
    """Build InheritedDonorContext list from the source ledger + adaptation.

    The donor_participant_id comes from the adaptation (the participant whose
    context is being transferred to query X). The donor_reaction_id is the
    source ledger's reaction_evidence_id. is_assumption is locked to True by
    the schema (Literal[True]) — donor-derived context can NEVER be marked as
    a proven X→Y fact.
    """
    donor_pid = adaptation.donor_participant_id
    inherited_role = _role_for_participant(
        source_ledger.role_assignments, donor_pid,
    )
    return [InheritedDonorContext(
        donor_reaction_id=source_ledger.reaction_evidence_id,
        donor_participant_id=donor_pid,
        inherited_role=inherited_role,
        is_assumption=True,  # locked by schema (Literal[True])
    )]


def _build_inherited_assumptions(
    source_ledger: SourceReactionLedger,
    adaptation: QueryCandidateAdaptation,
) -> list[str]:
    """Build the inherited_assumptions note list.

    Each note explicitly labels an inherited dimension as an assumption (NOT
    a proven X→Y fact). This makes the no-fabrication discipline auditable.
    """
    notes: list[str] = [_NOTE_DONOR_CONTEXT_ASSUMPTION]
    if source_ledger.cofactor_changes:
        notes.append(_NOTE_DONOR_COFACTOR_ASSUMPTION)
    if source_ledger.stoichiometry:
        notes.append(_NOTE_DONOR_STOICHIOMETRY_ASSUMPTION)
    # Co-substrates: participants with co_substrate role
    has_co_substrate = any(
        ra.role == ParticipantRole.co_substrate
        for ra in source_ledger.role_assignments
    )
    if has_co_substrate:
        notes.append(_NOTE_DONOR_CO_SUBSTRATE_ASSUMPTION)
    return notes


def _build_formal_balance_under_assumptions(
    source_ledger: SourceReactionLedger,
) -> FormalBalanceUnderAssumptions:
    """Build formal_balance_under_assumptions (separate from observed).

    Copies the source ledger's element_balance structure and charge_balance,
    but explicitly labels the result as assumption-based via assumption_notes.
    This is NOT the observed balance — it is the balance computed under the
    donor-derived assumption that the donor context transfers to X→Y.

    No new chemical computation is performed (rdkit absent does not block
    this — we inherit the source's already-computed structure).
    """
    # Copy element balances (new list, no mutation of source)
    element_balances: list[ElementBalance] = [
        ElementBalance(
            element=eb.element,
            reactant_count=eb.reactant_count,
            product_count=eb.product_count,
            delta=eb.delta,
        )
        for eb in source_ledger.element_balance
    ]
    return FormalBalanceUnderAssumptions(
        element_balances=element_balances,
        charge_delta=source_ledger.charge_balance,
        assumption_notes=[_NOTE_FORMAL_BALANCE_ASSUMPTION],
    )


def _collect_unknown_cofactors(
    source_ledger: SourceReactionLedger,
) -> list[str]:
    """Collect donor cofactor participant IDs → unknown_actual_cofactors.

    Invariant 4: donor cofactors are NOT proven X→Y cofactors. Each donor
    cofactor participant ID flows to unknown_actual_cofactors (inherited
    assumption). The schema has NO field claiming cofactors are proven for
    X→Y.
    """
    seen: set[str] = set()
    result: list[str] = []
    for cc in source_ledger.cofactor_changes:
        if cc.participant_id not in seen:
            seen.add(cc.participant_id)
            result.append(cc.participant_id)
    return result


def _collect_unknown_co_substrates(
    source_ledger: SourceReactionLedger,
) -> list[str]:
    """Collect donor co-substrate participant IDs → unknown_actual_co_substrates.

    Donor co-substrates are NOT proven X→Y co-substrates. Participants with
    the co_substrate role in the source ledger flow to
    unknown_actual_co_substrates.
    """
    seen: set[str] = set()
    result: list[str] = []
    for ra in source_ledger.role_assignments:
        if ra.role == ParticipantRole.co_substrate and ra.participant_id not in seen:
            seen.add(ra.participant_id)
            result.append(ra.participant_id)
    return result


def _collect_unknown_stoichiometry(
    source_ledger: SourceReactionLedger,
) -> list[str]:
    """Collect donor stoichiometry participant IDs → unknown_actual_stoichiometry.

    Donor stoichiometry is NOT proven X→Y stoichiometry. Each participant in
    the source ledger's stoichiometry list flows to
    unknown_actual_stoichiometry (inherited assumption).
    """
    seen: set[str] = set()
    result: list[str] = []
    for entry in source_ledger.stoichiometry:
        if entry.participant_id not in seen:
            seen.add(entry.participant_id)
            result.append(entry.participant_id)
    return result


def _collect_unknowns(
    source_ledger: SourceReactionLedger,
    inherited_assumptions: list[str],
) -> list[str]:
    """Collect all unknowns entries for the candidate ledger.

    Includes the inherited assumption notes (so the no-fabrication discipline
    is auditable in the unknowns list) plus any source-ledger unknowns that
    are relevant to the candidate context.
    """
    unknowns: list[str] = list(inherited_assumptions)
    # Carry forward source unknowns that affect the candidate (atom sources,
    # stoichiometry gaps, etc.) — prefixed to distinguish donor-source from
    # candidate-side.
    for u in source_ledger.unknowns:
        unknowns.append(f"donor_source_unknown:{u}")
    unknowns.append(_NOTE_CANDIDATE_BALANCE_DEFAULT)
    return unknowns


def _collect_evidence_ids(
    source_ledger: SourceReactionLedger,
) -> list[str]:
    """Collect evidence IDs inherited from the source ledger.

    The candidate ledger inherits the source's evidence chain (the donor
    reaction's evidence supports the analogy assumption). No new evidence is
    fabricated.
    """
    return list(source_ledger.evidence_ids)


def _ledger_id(source_ledger_id: str, candidate_id: str) -> str:
    """Stable ledger ID: source + candidate + builder version.

    Content-addressed via canonical_hash (only basic types: str). Same inputs
    → same id; different candidate → different id.
    """
    payload = {
        "source_ledger_id": source_ledger_id,
        "candidate_id": candidate_id,
        "version": BUILDER_VERSION,
        "kind": "candidate_analogy_ledger",
    }
    return f"cal_{canonical_hash(payload)[:12]}"


# =====================================================================
# Public API
# =====================================================================

def build_candidate_skeleton(
    source_ledger: SourceReactionLedger,
    adaptation: QueryCandidateAdaptation,
    *,
    candidate_id: str,
) -> CandidateAnalogyLedger:
    """Build a CandidateAnalogyLedger skeleton from source ledger + adaptation.

    Constructs the skeleton by inheriting donor context as EXPLICIT
    ASSUMPTIONS and preserving unknowns. Does NOT generate Y, rank
    candidates, or produce LLM rationale (brief §14).

    5 key invariants (§14):
    1. donor_context_is_assumption = True (InheritedDonorContext.is_assumption
       locked by schema; builder populates contexts from source roles).
    2. source_ledger_link exists (source_ledger_id = source_ledger.ledger_id).
    3. candidate_id belongs current context (caller-provided, echoed verbatim;
       builder does NOT generate candidate_id).
    4. donor cofactor != proven X→Y cofactor (donor cofactors →
       unknown_actual_cofactors; no "proven cofactors" field exists).
    5. formal_balance_under_assumptions != observed balance (separate object,
       labeled via assumption_notes; candidate_balance_status defaults to
       partial_or_unbalanced_source).

    Signature deviation from brief: ``candidate_id`` is a required keyword-only
    argument. The brief lists ``build_candidate_skeleton(source_ledger,
    adaptation)`` but CandidateAnalogyLedger.candidate_id is a mandatory
    NonEmptyStr that the builder must NOT generate (generating a candidate_id
    would be generating a candidate, which is forbidden by §14). The caller
    provides candidate_id from the current context. This is documented in
    reports/p1/P1_T8_CANDIDATE_LEDGER_SKELETON.md.

    Immutability: ``source_ledger`` and ``adaptation`` are NOT mutated.
    """
    # -- Inherited donor context (assumption, not fact) --
    inherited_donor_context = _build_inherited_donor_context(
        source_ledger, adaptation,
    )

    # -- Inherited assumptions (explicit notes) --
    inherited_assumptions = _build_inherited_assumptions(
        source_ledger, adaptation,
    )

    # -- Formal atom transfers (inherited from source, formal under assumptions) --
    formal_atom_transfers = [
        # Rebuild as new objects to avoid any shared reference
        type(transfer)(
            source_participant_id=transfer.source_participant_id,
            target_participant_id=transfer.target_participant_id,
            transferred_atom_map_numbers=list(transfer.transferred_atom_map_numbers),
            assignment_method=transfer.assignment_method,
        )
        for transfer in source_ledger.formal_atom_transfer_assignments
    ]

    # -- Formal balance under assumptions (separate from observed) --
    formal_balance = _build_formal_balance_under_assumptions(source_ledger)

    # -- Unknown actual co-substrates / cofactors / stoichiometry --
    unknown_co_substrates = _collect_unknown_co_substrates(source_ledger)
    unknown_cofactors = _collect_unknown_cofactors(source_ledger)
    unknown_stoichiometry = _collect_unknown_stoichiometry(source_ledger)

    # -- Unknowns (auditable assumption notes + donor-source unknowns) --
    unknowns = _collect_unknowns(source_ledger, inherited_assumptions)

    # -- Evidence IDs (inherited from source, not fabricated) --
    evidence_ids = _collect_evidence_ids(source_ledger)

    # -- Ledger ID (stable, content-addressed) --
    ledger_id = _ledger_id(source_ledger.ledger_id, candidate_id)

    # -- candidate_balance_status: default partial (assumption-based) --
    # The candidate balance is under donor-derived assumptions, NOT observed.
    # It defaults to partial_or_unbalanced_source (the honest status for an
    # assumption-based skeleton). This is distinct from the source ledger's
    # observed balance_status.
    candidate_balance_status = LedgerBalanceStatus.partial_or_unbalanced_source

    return CandidateAnalogyLedger(
        ledger_id=ledger_id,
        source_ledger_id=source_ledger.ledger_id,
        candidate_id=candidate_id,
        query_candidate_adaptation=adaptation,
        inherited_donor_context=inherited_donor_context,
        inherited_assumptions=inherited_assumptions,
        formal_atom_transfer_assignments=formal_atom_transfers,
        formal_balance_under_assumptions=formal_balance,
        unknown_actual_co_substrates=unknown_co_substrates,
        unknown_actual_cofactors=unknown_cofactors,
        unknown_actual_stoichiometry=unknown_stoichiometry,
        candidate_balance_status=candidate_balance_status,
        unknowns=unknowns,
        evidence_ids=evidence_ids,
    )
