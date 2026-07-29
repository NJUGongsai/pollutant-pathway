"""Dual ledger schemas (final_design §10, ADR-0003).

SourceReactionLedger: records what the source database actually says.
CandidateAnalogyLedger: records donor-derived analogy assumptions for X→Y.

These MUST NOT be mixed. Donor cofactors/stoichiometry in source
ledger do NOT become proven facts about X→Y.

All nested structures use typed skeletons, not arbitrary dict.
"""

from typing import Literal

from pydantic import field_validator
from reaction_agent.schemas.common import (
    StrictModel,
    NonEmptyStr,
    LedgerBalanceStatus,
    ParticipantRole,
    AdaptationVerificationStatus,
)
from reaction_agent.schemas.errors import UnknownReferenceError


# -- Typed nested skeletons --

class RoleAssignment(StrictModel):
    """A role assignment for a participant."""
    participant_id: NonEmptyStr
    role: ParticipantRole
    score: float = 0.0
    evidence_codes: list[NonEmptyStr] = []


class StoichiometricEntry(StrictModel):
    """Stoichiometry for a participant."""
    participant_id: NonEmptyStr
    coefficient: int = 1
    side: NonEmptyStr  # "reactant" or "product"


class FormalAtomTransferAssignment(StrictModel):
    """Formal atom transfer between participants."""
    source_participant_id: NonEmptyStr
    target_participant_id: NonEmptyStr
    transferred_atom_map_numbers: list[int] = []
    assignment_method: NonEmptyStr = "formal"


class MechanisticOriginEvidence(StrictModel):
    """Mechanistic evidence for atom origin (separate from formal assignment)."""
    evidence_id: NonEmptyStr
    evidence_type: NonEmptyStr  # e.g. "isotope_tracing"
    source_participant_id: NonEmptyStr | None = None
    target_atom_map_numbers: list[int] = []


class AddedAtomSource(StrictModel):
    """Source of atoms added during reaction."""
    atom_map_number: int
    source_participant_id: NonEmptyStr
    formal_assignment: bool = True
    mechanistic_evidence_id: str | None = None


class RemovedAtomSink(StrictModel):
    """Sink for atoms removed during reaction."""
    atom_map_number: int
    sink_participant_id: NonEmptyStr
    formal_assignment: bool = True


class ElementBalance(StrictModel):
    """Element balance for the reaction."""
    element: NonEmptyStr
    reactant_count: int = 0
    product_count: int = 0
    delta: int = 0


class CofactorChange(StrictModel):
    """Cofactor state change."""
    participant_id: NonEmptyStr
    oxidized_form: NonEmptyStr | None = None
    reduced_form: NonEmptyStr | None = None
    direction: NonEmptyStr = "unknown"


# -- Candidate-specific typed skeletons --

class QueryCandidateAdaptation(StrictModel):
    """How donor context was adapted to query X.

    Uses a controlled adaptation_verification_status enum (Section 9), NOT
    free-text confidence. Does not imply enzyme activity probability.
    """
    donor_participant_id: NonEmptyStr
    query_atom_ids: list[int] = []
    adaptation_method: NonEmptyStr = "formal_mapping"
    adaptation_verification_status: AdaptationVerificationStatus = (
        AdaptationVerificationStatus.unverified_analogy
    )


class InheritedDonorContext(StrictModel):
    """Donor context inherited by candidate (assumption, not fact).

    is_assumption is locked to True (Section 8): donor-derived context can
    never be marked as a proven X->Y fact.
    """
    donor_reaction_id: NonEmptyStr
    donor_participant_id: NonEmptyStr
    inherited_role: ParticipantRole = ParticipantRole.unknown
    is_assumption: Literal[True] = True


class FormalBalanceUnderAssumptions(StrictModel):
    """Balance computed under donor-derived assumptions."""
    element_balances: list[ElementBalance] = []
    charge_delta: int = 0
    assumption_notes: list[NonEmptyStr] = []


# -- Top-level ledgers --

class SourceReactionLedger(StrictModel):
    """Records what the source database actually documents (final_design §10.1).

    This is about the DONOR reaction, not the target X→Y.
    Unknown information must remain unknown — never silently filled.
    """
    ledger_id: NonEmptyStr
    reaction_evidence_id: NonEmptyStr
    reactant_entries: list[StoichiometricEntry] = []
    product_entries: list[StoichiometricEntry] = []
    role_assignments: list[RoleAssignment] = []
    stoichiometry: list[StoichiometricEntry] = []
    formal_atom_transfer_assignments: list[FormalAtomTransferAssignment] = []
    mechanistic_origin_evidence: list[MechanisticOriginEvidence] = []
    added_atom_sources: list[AddedAtomSource] = []
    removed_atom_sinks: list[RemovedAtomSink] = []
    element_balance: list[ElementBalance] = []
    charge_balance: int = 0
    hydrogen_policy: NonEmptyStr = "unknown"
    proton_policy: NonEmptyStr = "unknown"
    electron_policy: NonEmptyStr = "unknown"
    cofactor_changes: list[CofactorChange] = []
    source_completeness: NonEmptyStr = "unknown"
    mapping_completeness: NonEmptyStr = "unknown"
    balance_status: LedgerBalanceStatus
    unknowns: list[NonEmptyStr] = []
    evidence_ids: list[NonEmptyStr] = []


class CandidateAnalogyLedger(StrictModel):
    """Records analogy assumptions when transferring donor context to X→Y.

    Donor uses NAD(P), O2 etc. does NOT mean X→Y uses same cofactors.
    These are inherited assumptions, explicitly labeled as such.
    """
    ledger_id: NonEmptyStr
    source_ledger_id: NonEmptyStr  # mandatory linkage
    candidate_id: NonEmptyStr
    query_candidate_adaptation: QueryCandidateAdaptation | None = None
    inherited_donor_context: list[InheritedDonorContext] = []
    inherited_assumptions: list[NonEmptyStr] = []
    formal_atom_transfer_assignments: list[FormalAtomTransferAssignment] = []
    formal_balance_under_assumptions: FormalBalanceUnderAssumptions | None = None
    unknown_actual_co_substrates: list[NonEmptyStr] = []
    unknown_actual_cofactors: list[NonEmptyStr] = []
    unknown_actual_stoichiometry: list[NonEmptyStr] = []
    candidate_balance_status: LedgerBalanceStatus = LedgerBalanceStatus.partial_or_unbalanced_source
    unknowns: list[NonEmptyStr] = []
    evidence_ids: list[NonEmptyStr] = []


# -- Ledger reference registry (Section 7) --

class LedgerReferenceRegistry(StrictModel):
    """Minimal ledger reference registry for source/candidate ID validation.

    P0 does not implement a database. This validates that source_ledger_id
    and candidate_id in a CandidateAnalogyLedger actually exist in the
    current run/context — not merely that they are non-empty strings.
    """
    source_ledger_ids: frozenset[str] = frozenset()
    candidate_ids: frozenset[str] = frozenset()
    evidence_ids: frozenset[str] = frozenset()
    source_ledger_to_reaction_id: dict[str, str] = {}


def validate_candidate_ledger_references(
    ledger: CandidateAnalogyLedger,
    registry: LedgerReferenceRegistry,
) -> None:
    """Validate that a CandidateAnalogyLedger references real source/candidate IDs.

    Raises UnknownReferenceError for:
    - source_ledger_id not in registry (non-empty but unknown)
    - candidate_id not in registry (unknown)
    """
    errors: list[str] = []
    if ledger.source_ledger_id not in registry.source_ledger_ids:
        errors.append(f"unknown source_ledger_id: {ledger.source_ledger_id}")
    if ledger.candidate_id not in registry.candidate_ids:
        errors.append(f"unknown candidate_id: {ledger.candidate_id}")
    if errors:
        raise UnknownReferenceError("; ".join(errors))
