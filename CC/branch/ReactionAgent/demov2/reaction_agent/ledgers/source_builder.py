"""SourceReactionLedger builder (final_design §10.1–§10.4, ADR-0003).

``build_source_ledger`` constructs a SourceReactionLedger from a
ReactionEvidence + resolved transformed lineages. It fills all §10.1 fields.

No-fabrication discipline (brief §13.4 / §10.4):
- Missing stoichiometry → unknown (NOT default 1 asserted as fact). Detection
  uses ``participant.model_fields_set``: if ``stoichiometry`` was not
  explicitly provided at construction, the pydantic default (1) is NOT
  asserted as a recorded fact — an unknowns entry is added instead.
- Missing H+/e− → explicit policy (NOT silent fill to "balanced"). Policies
  are "unknown" or an explicit implicit-policy label; never "balanced".
- Formal mapper → formal assignment (NOT promoted to proven mechanism).
  ``mechanistic_origin_evidence`` is populated ONLY from
  ``mapping_report.mechanistic_atom_origin`` (which the mapper never
  auto-populates — ADR-0003). Formal assignments go to
  ``formal_atom_transfer_assignments`` with ``assignment_method="formal"``.
- Each new changed heavy atom must have a formal source assignment OR an
  explicit ``unknown_source`` (§10.4). When source is needed but untraceable,
  the record is NOT strict-eligible (balance_status =
  partial_or_unbalanced_source).

rdkit-absent discipline (Preflight BLOCKED):
- Element balance (molecular formula comparison) requires rdkit. It is NOT
  fabricated. The ledger leaves ``element_balance`` computed only from the
  structured inputs available (participant counts as a lossless proxy when
  mapping provides atom counts), and records ``element_balance_rdkit_absent``
  in ``unknowns`` when real formula comparison is needed but unavailable.
- Charge balance IS computable from ``formal_charge`` fields (no rdkit) and
  is always computed.
- Cofactor change direction (oxidation vs reduction) requires structure
  comparison; when rdkit is absent, direction defaults to "unknown" (never
  fabricated).

Immutability: ``build_source_ledger`` does NOT mutate ``reaction_evidence``
or ``lineages``. New objects are returned throughout.
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash
from reaction_agent.schemas.common import (
    LedgerBalanceStatus,
    MappingStatus,
    ParticipantRole,
)
from reaction_agent.schemas.evidence import ReactionEvidence, ReactionParticipant
from reaction_agent.schemas.ledger import (
    AddedAtomSource,
    CofactorChange,
    ElementBalance,
    FormalAtomTransferAssignment,
    MechanisticOriginEvidence,
    RemovedAtomSink,
    RoleAssignment,
    SourceReactionLedger,
    StoichiometricEntry,
)
from reaction_agent.schemas.mapping import MappingReport
from reaction_agent.schemas.p1_entities import ResolvedTransformedLineage


# =====================================================================
# Builder version (embedded in ledger_id for traceability)
# =====================================================================

BUILDER_VERSION = "p1-t7-1"

# Policy labels (never "balanced" — explicit implicit-policy or unknown)
_H_POLICY_IMPLICIT = "implicit_heavy_atom_balanced_h_policy"
_H_POLICY_UNKNOWN = "unknown"
_PROTON_POLICY_REDOX = "cofactor_redox_implicit_proton_policy"
_PROTON_POLICY_UNKNOWN = "unknown"
_ELECTRON_POLICY_REDOX = "cofactor_redox_implicit_e_policy"
_ELECTRON_POLICY_UNKNOWN = "unknown"


# =====================================================================
# Internal helpers
# =====================================================================

def _is_stoichiometry_recorded(p: ReactionParticipant) -> bool:
    """Whether stoichiometry was explicitly provided (not pydantic default).

    Uses ``model_fields_set``: if ``stoichiometry`` is NOT in the set, the
    value (1) is the pydantic default, NOT a recorded fact. This is the
    no-fabrication detection (brief §13.4).
    """
    return "stoichiometry" in p.model_fields_set


def _has_source_annotation(p: ReactionParticipant) -> bool:
    """Whether the participant carries source annotation (provenance)."""
    return bool(p.provenance)


def _participant_index(
    participants: list[ReactionParticipant],
) -> dict[str, ReactionParticipant]:
    """Build a participant_id → ReactionParticipant lookup."""
    return {p.participant_id: p for p in participants}


def _split_by_side(
    participants: list[ReactionParticipant],
) -> tuple[list[ReactionParticipant], list[ReactionParticipant]]:
    """Split participants into (reactants, products) by side field."""
    reactants = [p for p in participants if p.side == "reactant"]
    products = [p for p in participants if p.side == "product"]
    return reactants, products


def _build_stoichiometric_entries(
    participants: list[ReactionParticipant],
) -> list[StoichiometricEntry]:
    """Build StoichiometricEntry list from participants.

    The coefficient carries the participant's stoichiometry value (lossless),
    even when unverified. The verification status is tracked separately in
    ``unknowns`` — the entry itself never lies about the value.
    """
    return [
        StoichiometricEntry(
            participant_id=p.participant_id,
            coefficient=p.stoichiometry,
            side=p.side,
        )
        for p in participants
    ]


def _build_role_assignments(
    participants: list[ReactionParticipant],
) -> list[RoleAssignment]:
    """Build RoleAssignment list from participants' role hypotheses.

    Picks the highest-scored hypothesis per participant. If no hypotheses,
    role=unknown. Roles are hypotheses (§11.2), NOT ground-truth assignments.
    """
    assignments: list[RoleAssignment] = []
    for p in participants:
        if not p.role_hypotheses:
            assignments.append(RoleAssignment(
                participant_id=p.participant_id,
                role=ParticipantRole.unknown,
                score=0.0,
                evidence_codes=["no_role_hypothesis"],
            ))
            continue
        # Pick the highest-scored hypothesis (ordering hint, NOT probability)
        best = max(p.role_hypotheses, key=lambda h: h.score)
        assignments.append(RoleAssignment(
            participant_id=p.participant_id,
            role=best.role,
            score=best.score,
            evidence_codes=list(best.evidence_codes),
        ))
    return assignments


def _build_formal_atom_transfers(
    mapping_report: MappingReport | None,
) -> list[FormalAtomTransferAssignment]:
    """Build FormalAtomTransferAssignment list from the mapping report.

    Groups formal atom pairs by (reactant_pid, product_pid). These are FORMAL
    assignments (assignment_method="formal"), NOT mechanistic proof.
    """
    if mapping_report is None:
        return []
    fma = mapping_report.formal_mapped_source_assignment
    if fma is None:
        return []

    grouped: dict[tuple[str, str], list[int]] = {}
    for pair in fma.mapped_atom_pairs:
        key = (pair.reactant_participant_id, pair.product_participant_id)
        grouped.setdefault(key, []).append(pair.reactant_atom_map)

    return [
        FormalAtomTransferAssignment(
            source_participant_id=r_pid,
            target_participant_id=p_pid,
            transferred_atom_map_numbers=sorted(atoms),
            assignment_method="formal",
        )
        for (r_pid, p_pid), atoms in grouped.items()
    ]


def _build_mechanistic_origin_evidence(
    mapping_report: MappingReport | None,
) -> list[MechanisticOriginEvidence]:
    """Build MechanisticOriginEvidence list from the mapping report.

    Populated ONLY from ``mapping_report.mechanistic_atom_origin`` (which the
    mapper NEVER auto-populates — ADR-0003). Formal mapping is NOT promoted
    to mechanistic proof. If mechanistic_atom_origin is None → empty list.
    """
    if mapping_report is None:
        return []
    mo = mapping_report.mechanistic_atom_origin
    if mo is None:
        return []

    evidence: list[MechanisticOriginEvidence] = []
    for eid in mo.evidence_ids:
        # Collect target atom numbers for this evidence ID
        target_atoms = [
            pair.target_atom_identifier
            for pair in mo.mechanistic_atom_pairs
            if pair.evidence_id == eid
        ]
        source_pid = None
        for pair in mo.mechanistic_atom_pairs:
            if pair.evidence_id == eid:
                source_pid = pair.source_participant_id
                break
        evidence.append(MechanisticOriginEvidence(
            evidence_id=eid,
            evidence_type=mo.evidence_type,
            source_participant_id=source_pid,
            target_atom_map_numbers=target_atoms,
        ))
    return evidence


def _build_atom_sources_and_sinks(
    participants: list[ReactionParticipant],
    mapping_report: MappingReport | None,
    lineages: list[ResolvedTransformedLineage],
    unknowns: list[str],
) -> tuple[list[AddedAtomSource], list[RemovedAtomSink]]:
    """Build added_atom_sources and removed_atom_sinks from lineages.

    For each lineage (reactant → product):
    - Product atoms NOT in the lineage's transformed_atom_maps are "new" atoms.
      Each new atom gets an AddedAtomSource: formal_assignment=True if a
      formal mapping pair traces it to another reactant; else
      source_participant_id="unknown_source", formal_assignment=False.
    - Reactant atoms NOT in the lineage's transformed_atom_maps are "removed".
      Each removed atom gets a RemovedAtomSink: formal_assignment=True if a
      formal mapping pair traces it to another product; else
      sink_participant_id="unknown_sink".

    §10.4: each new changed heavy atom must have a formal source OR explicit
    unknown_source. Unknown sources → not strict-eligible.
    """
    pidx = _participant_index(participants)

    # Build reverse lookup: product_atom → source_reactant_pid (from mapping)
    product_atom_to_source: dict[tuple[str, int], str] = {}
    if mapping_report is not None:
        fma = mapping_report.formal_mapped_source_assignment
        if fma is not None:
            for pair in fma.mapped_atom_pairs:
                product_atom_to_source[(pair.product_participant_id,
                                        pair.product_atom_map)] = \
                    pair.reactant_participant_id

    # Build reverse lookup: reactant_atom → sink_product_pid (from mapping)
    reactant_atom_to_sink: dict[tuple[str, int], str] = {}
    if mapping_report is not None:
        fma = mapping_report.formal_mapped_source_assignment
        if fma is not None:
            for pair in fma.mapped_atom_pairs:
                reactant_atom_to_sink[(pair.reactant_participant_id,
                                       pair.reactant_atom_map)] = \
                    pair.product_participant_id

    added_sources: list[AddedAtomSource] = []
    removed_sinks: list[RemovedAtomSink] = []
    seen_added: set[tuple[str, int]] = set()  # (product_pid, atom) dedup
    seen_removed: set[tuple[str, int]] = set()  # (reactant_pid, atom) dedup

    for lin in lineages:
        reactant = pidx.get(lin.reactant_participant_id)
        product = pidx.get(lin.product_participant_id)
        if reactant is None or product is None:
            continue

        shared = set(lin.transformed_atom_maps)
        product_atoms = set(product.atom_map_numbers)
        reactant_atoms = set(reactant.atom_map_numbers)

        # New atoms in product (not in shared)
        new_atoms = product_atoms - shared
        for atom in sorted(new_atoms):
            key = (lin.product_participant_id, atom)
            if key in seen_added:
                continue
            seen_added.add(key)
            source_pid = product_atom_to_source.get(key)
            if source_pid is not None:
                added_sources.append(AddedAtomSource(
                    atom_map_number=atom,
                    source_participant_id=source_pid,
                    formal_assignment=True,
                ))
            else:
                # No formal source → explicit unknown_source (§10.4)
                added_sources.append(AddedAtomSource(
                    atom_map_number=atom,
                    source_participant_id="unknown_source",
                    formal_assignment=False,
                ))
                unknowns.append(
                    f"unknown_atom_source:{lin.product_participant_id}:atom_{atom}"
                )

        # Removed atoms from reactant (not in shared)
        removed_atoms = reactant_atoms - shared
        for atom in sorted(removed_atoms):
            key = (lin.reactant_participant_id, atom)
            if key in seen_removed:
                continue
            seen_removed.add(key)
            sink_pid = reactant_atom_to_sink.get(key)
            if sink_pid is not None:
                removed_sinks.append(RemovedAtomSink(
                    atom_map_number=atom,
                    sink_participant_id=sink_pid,
                    formal_assignment=True,
                ))
            else:
                removed_sinks.append(RemovedAtomSink(
                    atom_map_number=atom,
                    sink_participant_id="unknown_sink",
                    formal_assignment=False,
                ))
                unknowns.append(
                    f"unknown_atom_sink:{lin.reactant_participant_id}:atom_{atom}"
                )

    return added_sources, removed_sinks


def _compute_charge_balance(
    reactants: list[ReactionParticipant],
    products: list[ReactionParticipant],
) -> int:
    """Compute charge balance: sum(reactant charges) - sum(product charges).

    Computable from ``formal_charge`` fields (no rdkit needed). A non-zero
    result indicates a charge mismatch (partial_or_unbalanced_source).
    """
    r_total = sum(p.formal_charge * p.stoichiometry for p in reactants)
    p_total = sum(p.formal_charge * p.stoichiometry for p in products)
    return r_total - p_total


def _compute_element_balance(
    reactants: list[ReactionParticipant],
    products: list[ReactionParticipant],
    unknowns: list[str],
) -> list[ElementBalance]:
    """Compute element balance.

    rdkit absent: real molecular formula comparison is NOT possible. We do
    NOT fabricate element counts. The element_balance list is left empty
    (no fabrication) and an ``element_balance_rdkit_absent`` unknowns entry
    is recorded.

    When rdkit becomes available, this will compute real per-element counts
    from molecular formulas.
    """
    if not reactants and not products:
        return []
    # rdkit absent — cannot compute real element counts. Record honestly.
    unknowns.append("element_balance_rdkit_absent_proxy")
    return []


def _detect_cofactor_changes(
    participants: list[ReactionParticipant],
) -> list[CofactorChange]:
    """Detect cofactor state changes.

    Looks for participants with carrier/cofactor role hypotheses on both
    reactant and product sides. Records a CofactorChange entry. Direction
    defaults to "unknown" (structure comparison needed for oxidation vs
    reduction — rdkit absent, not fabricated).
    """
    reactants, products = _split_by_side(participants)

    def _has_cofactor_role(p: ReactionParticipant) -> bool:
        roles = {h.role for h in p.role_hypotheses}
        return (
            ParticipantRole.carrier in roles
            or ParticipantRole.cofactor in roles
        )

    r_cofactors = [p for p in reactants if _has_cofactor_role(p)]
    p_cofactors = [p for p in products if _has_cofactor_role(p)]

    if not r_cofactors and not p_cofactors:
        return []

    changes: list[CofactorChange] = []
    # Record cofactor changes for reactant-side cofactors
    for p in r_cofactors:
        changes.append(CofactorChange(
            participant_id=p.participant_id,
            oxidized_form=p.canonical_smiles,
            reduced_form=None,
            direction="unknown",
        ))
    # Record cofactor changes for product-side cofactors
    for p in p_cofactors:
        changes.append(CofactorChange(
            participant_id=p.participant_id,
            oxidized_form=None,
            reduced_form=p.canonical_smiles,
            direction="unknown",
        ))
    return changes


def _has_redox_cofactors(
    participants: list[ReactionParticipant],
) -> bool:
    """Whether any participant has a carrier/cofactor role (redox indicator)."""
    for p in participants:
        roles = {h.role for h in p.role_hypotheses}
        if ParticipantRole.carrier in roles or ParticipantRole.cofactor in roles:
            return True
    return False


def _determine_policies(
    participants: list[ReactionParticipant],
    mapping_report: MappingReport | None,
) -> tuple[str, str, str]:
    """Determine hydrogen/proton/electron policies.

    Never returns "balanced" (no-fabrication: H+/e− balance is NOT silently
    filled). Returns "unknown" or an explicit implicit-policy label.
    """
    has_redox = _has_redox_cofactors(participants)
    has_mapping = mapping_report is not None

    # Hydrogen policy: implicit if heavy atoms mapped, else unknown
    if has_mapping:
        h_policy = _H_POLICY_IMPLICIT
    else:
        h_policy = _H_POLICY_UNKNOWN

    # Proton / electron policy: redox if cofactors present, else unknown
    if has_redox:
        proton_policy = _PROTON_POLICY_REDOX
        electron_policy = _ELECTRON_POLICY_REDOX
    else:
        proton_policy = _PROTON_POLICY_UNKNOWN
        electron_policy = _ELECTRON_POLICY_UNKNOWN

    return h_policy, proton_policy, electron_policy


def _determine_source_completeness(
    participants: list[ReactionParticipant],
    unknowns: list[str],
) -> str:
    """Determine source_completeness.

    "complete" if ALL participants have provenance AND stoichiometry verified.
    "incomplete" if any gap. "unknown" if no participants.
    """
    if not participants:
        return "unknown"
    has_gap = False
    for p in participants:
        if not _has_source_annotation(p):
            unknowns.append(f"source_annotation_missing:{p.participant_id}")
            has_gap = True
        if not _is_stoichiometry_recorded(p):
            unknowns.append(f"stoichiometry_unverified:{p.participant_id}")
            has_gap = True
    return "incomplete" if has_gap else "complete"


def _determine_mapping_completeness(
    mapping_report: MappingReport | None,
) -> str:
    """Determine mapping_completeness from the mapping report status."""
    if mapping_report is None:
        return "unknown"
    status = mapping_report.mapping_status
    if status == MappingStatus.fully_mapped:
        return "complete"
    if status in (MappingStatus.partially_mapped, MappingStatus.mapping_ambiguous):
        return "partial"
    return "unknown"


def _determine_balance_status(
    charge_balance: int,
    added_sources: list[AddedAtomSource],
    source_completeness: str,
    mapping_completeness: str,
    mapping_report: MappingReport | None,
    unknowns: list[str],
) -> LedgerBalanceStatus:
    """Determine the balance_status (§10.3).

    - ``partial_or_unbalanced_source``: charge mismatch, OR unknown atom
      source, OR source incomplete, OR mapping incomplete/ambiguous, OR
      stoichiometry unverified.
    - ``heavy_atom_balanced_with_implicit_h_e_policy``: charge balanced, all
      changed atoms have formal sources, source/mapping complete, but H+/e−
      balance is implicit (rdkit absent — cannot verify element balance).
    - ``fully_balanced_explicit_reaction``: would require rdkit-computed
      element balance; not asserted without rdkit. Downgraded to
      heavy_atom_balanced_with_implicit_h_e_policy (honest).
    """
    # Check for disqualifying conditions → partial_or_unbalanced_source
    if charge_balance != 0:
        unknowns.append(f"charge_mismatch:{charge_balance}")
        return LedgerBalanceStatus.partial_or_unbalanced_source

    # Unknown atom sources → not strict-eligible (§10.4)
    has_unknown_source = any(
        s.source_participant_id == "unknown_source" for s in added_sources
    )
    if has_unknown_source:
        return LedgerBalanceStatus.partial_or_unbalanced_source

    if source_completeness != "complete":
        return LedgerBalanceStatus.partial_or_unbalanced_source

    if mapping_completeness not in ("complete",):
        return LedgerBalanceStatus.partial_or_unbalanced_source

    # Ambiguous formal assignment → partial
    if mapping_report is not None:
        fma = mapping_report.formal_mapped_source_assignment
        if fma is not None and fma.assignment_ambiguity:
            unknowns.append("formal_assignment_ambiguous")
            return LedgerBalanceStatus.partial_or_unbalanced_source

    # All checks passed: heavy atoms balanced, charge balanced, source complete.
    # H+/e− balance is implicit (rdkit absent — cannot verify element balance).
    # This is the honest best-case status without rdkit.
    return LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy


def _collect_evidence_ids(
    reaction_evidence: ReactionEvidence,
    mapping_report: MappingReport | None,
) -> list[str]:
    """Collect evidence IDs from reaction provenance + mapping report."""
    ids: list[str] = []
    # Reaction provenance
    for p in reaction_evidence.provenance:
        if p not in ids:
            ids.append(p)
    # Mapping report evidence
    if mapping_report is not None:
        for eid in mapping_report.mechanistic_origin_evidence_ids:
            if eid not in ids:
                ids.append(eid)
    return ids


def _ledger_id(reaction_id: str) -> str:
    """Stable ledger ID: reaction identity + builder version."""
    payload = {
        "reaction": reaction_id,
        "version": BUILDER_VERSION,
        "kind": "source_ledger",
    }
    return f"srl_{canonical_hash(payload)[:12]}"


# =====================================================================
# Public API
# =====================================================================

def build_source_ledger(
    reaction_evidence: ReactionEvidence,
    lineages: list[ResolvedTransformedLineage],
) -> SourceReactionLedger:
    """Build a SourceReactionLedger from reaction evidence + resolved lineages.

    Fills all §10.1 fields. No fabrication (brief §13.4):
    - Missing stoichiometry → unknown (detected via ``model_fields_set``).
    - Missing H+/e− → explicit policy (never "balanced").
    - Formal mapper → formal assignment (never promoted to mechanism).
    - Unknown atom source → explicit ``unknown_source`` (never fabricated).

    rdkit-absent: element balance is NOT fabricated (left empty with an
    unknowns entry). Charge balance IS computed (no rdkit needed). Cofactor
    direction defaults to "unknown" (not fabricated).

    Immutability: ``reaction_evidence`` and ``lineages`` are NOT mutated.
    """
    participants = list(reaction_evidence.participants)
    mapping_report = reaction_evidence.mapping_report
    unknowns: list[str] = []

    # -- Split participants by side --
    reactants, products = _split_by_side(participants)

    # -- Stoichiometric entries (reactant / product / flat) --
    reactant_entries = _build_stoichiometric_entries(reactants)
    product_entries = _build_stoichiometric_entries(products)
    stoichiometry = _build_stoichiometric_entries(participants)

    # -- Role assignments --
    role_assignments = _build_role_assignments(participants)

    # -- Formal atom transfers (from mapping, formal only) --
    formal_transfers = _build_formal_atom_transfers(mapping_report)

    # -- Mechanistic origin evidence (only if independent evidence exists) --
    mechanistic_evidence = _build_mechanistic_origin_evidence(mapping_report)

    # -- Added atom sources / removed atom sinks (from lineages) --
    added_sources, removed_sinks = _build_atom_sources_and_sinks(
        participants, mapping_report, lineages, unknowns,
    )

    # -- Charge balance (computable without rdkit) --
    charge_balance = _compute_charge_balance(reactants, products)

    # -- Element balance (rdkit absent — not fabricated) --
    element_balance = _compute_element_balance(
        reactants, products, unknowns,
    )

    # -- Policies (H/proton/electron — never "balanced") --
    h_policy, proton_policy, electron_policy = _determine_policies(
        participants, mapping_report,
    )

    # -- Cofactor changes --
    cofactor_changes = _detect_cofactor_changes(participants)

    # -- Source / mapping completeness --
    source_completeness = _determine_source_completeness(
        participants, unknowns,
    )
    mapping_completeness = _determine_mapping_completeness(mapping_report)

    # -- Balance status (§10.3) --
    balance_status = _determine_balance_status(
        charge_balance, added_sources, source_completeness,
        mapping_completeness, mapping_report, unknowns,
    )

    # -- Evidence IDs --
    evidence_ids = _collect_evidence_ids(reaction_evidence, mapping_report)

    # -- Ledger ID --
    ledger_id = _ledger_id(reaction_evidence.reaction_id)

    return SourceReactionLedger(
        ledger_id=ledger_id,
        reaction_evidence_id=reaction_evidence.reaction_id,
        reactant_entries=reactant_entries,
        product_entries=product_entries,
        role_assignments=role_assignments,
        stoichiometry=stoichiometry,
        formal_atom_transfer_assignments=formal_transfers,
        mechanistic_origin_evidence=mechanistic_evidence,
        added_atom_sources=added_sources,
        removed_atom_sinks=removed_sinks,
        element_balance=element_balance,
        charge_balance=charge_balance,
        hydrogen_policy=h_policy,
        proton_policy=proton_policy,
        electron_policy=electron_policy,
        cofactor_changes=cofactor_changes,
        source_completeness=source_completeness,
        mapping_completeness=mapping_completeness,
        balance_status=balance_status,
        unknowns=unknowns,
        evidence_ids=evidence_ids,
    )
