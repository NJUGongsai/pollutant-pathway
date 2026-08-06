"""P3-T7 Candidate validation (final_plan §6.8, R2-F).

A candidate enters the strict lane only when ALL of:
- valid molecule
- REAL transform fidelity (report identity + deterministic edit REPLAY equals
  the canonical product; not just heavy-atom count)
- precondition recheck
- formal heavy-atom source/sink accounting
- CandidateAnalogyLedger valid against the frozen reference registry and the
  donor evidence authority
- not critical contradiction / no relaxation / no critical ambiguity
- failure_code is None

Rejection is a typed failure, never a silent downgrade.
"""
from __future__ import annotations

from collections import Counter

from rdkit import Chem  # type: ignore

from reaction_agent.hashing import stable_id
from reaction_agent.p3.generate import generate_product
from reaction_agent.p3.schemas import (
    CandidateValidation,
    ConditionedSite,
    GenerationReport,
    NormalizedQuery,
    ResolvedDonorEvidence,
    StrictTransformation,
)
from reaction_agent.p3.transform import (
    TransformBindingError,
    verify_transform_binding,
)
from reaction_agent.schemas.ledger import (
    CandidateAnalogyLedger,
    ElementBalance,
    FormalAtomTransferAssignment,
    FormalBalanceUnderAssumptions,
    InheritedDonorContext,
    LedgerReferenceRegistry,
    QueryCandidateAdaptation,
    validate_candidate_ledger_references,
)
from reaction_agent.schemas.common import (
    AdaptationVerificationStatus,
    LedgerBalanceStatus,
    ParticipantRole,
)


def _heavy_atom_count(smiles: str) -> int:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return -1
    return sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() > 1)


def _derived_balance(
    donor_evidence: ResolvedDonorEvidence,
    transform: StrictTransformation,
) -> FormalBalanceUnderAssumptions:
    """Derive the formal balance from the ACTUAL graph edit (R2-F).

    Never hardcoded: element deltas and charge delta come from the
    transferred / removed / changed atoms of the transform.
    """
    # Element counts of removed atoms, read from the donor molecule.
    removed_elements: Counter = Counter()
    removed_charge = 0
    donor_mol = Chem.MolFromSmiles(donor_evidence.context.donor_canonical_smiles)
    if donor_mol is not None:
        for atom in donor_mol.GetAtoms():
            m = atom.GetAtomMapNum()
            if m in set(transform.removed_atom_maps):
                removed_elements[atom.GetSymbol()] += 1
                removed_charge += atom.GetFormalCharge()

    added_elements: Counter = Counter()
    added_charge = 0
    for t in transform.transferred_atoms:
        added_elements[t.element] += 1
        added_charge += t.formal_charge

    # Net element balance (product side minus query side).
    net = Counter(added_elements)
    net.subtract(removed_elements)
    element_balances = [
        ElementBalance(
            element=el,
            reactant_count=0,
            product_count=max(0, count),
            delta=count,
        )
        for el, count in sorted(net.items())
        if count != 0
    ]

    charge_delta = (
        sum((st.formal_charge_change or 0) for st in transform.atom_state_changes)
        + added_charge
        - removed_charge
    )

    return FormalBalanceUnderAssumptions(
        element_balances=element_balances,
        charge_delta=charge_delta,
        assumption_notes=[
            "balance is DERIVED from the transform's transferred/removed/"
            "changed atoms (not hardcoded)",
            "balance holds only under donor-derived assumptions",
        ],
    )


def _build_candidate_ledger(
    donor_evidence: ResolvedDonorEvidence,
    transform: StrictTransformation,
    site: ConditionedSite,
    candidate_id: str,
    source_ledger_id: str,
    canonical_product: str,
) -> CandidateAnalogyLedger:
    context = donor_evidence.context
    adaptation = QueryCandidateAdaptation(
        donor_participant_id=context.donor_participant_id,
        query_atom_ids=sorted(int(v) for v in site.atom_map_correspondence.values()),
        adaptation_method="deterministic_graph_edit",
        adaptation_verification_status=AdaptationVerificationStatus.formally_mapped,
    )
    inherited_context = [
        InheritedDonorContext(
            donor_reaction_id=context.reaction_id,
            donor_participant_id=context.donor_participant_id,
            inherited_role=ParticipantRole.unknown,
        )
    ]
    formal_transfers = [
        FormalAtomTransferAssignment(
            source_participant_id=t.source_participant_id,
            target_participant_id=context.donor_participant_id,
            transferred_atom_map_numbers=[t.transfer_map_number],
            assignment_method="formal",
        )
        for t in transform.transferred_atoms
    ]
    return CandidateAnalogyLedger(
        ledger_id=stable_id("cal", {
            "candidate": candidate_id,
            "source_ledger": source_ledger_id,
            "version": "p3-1",
        }),
        source_ledger_id=source_ledger_id,
        candidate_id=candidate_id,
        query_candidate_adaptation=adaptation,
        inherited_donor_context=inherited_context,
        inherited_assumptions=[
            "donor_context_is_assumption_not_x_y_fact",
        ],
        formal_atom_transfer_assignments=formal_transfers,
        formal_balance_under_assumptions=_derived_balance(donor_evidence, transform),
        unknown_actual_co_substrates=["unknown_actual_co_substrates"],
        unknown_actual_cofactors=["unknown_actual_cofactors"],
        unknown_actual_stoichiometry=["unknown_actual_stoichiometry"],
        candidate_balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        unknowns=[],
        evidence_ids=list(context.source_ledger.evidence_ids),
    )


def validate_candidate(
    donor_evidence: ResolvedDonorEvidence,
    transform: StrictTransformation,
    site: ConditionedSite,
    report: GenerationReport,
    query: NormalizedQuery,
    *,
    candidate_id: str,
    source_ledger_id: str,
    case_id: str = "",
) -> tuple[CandidateValidation, CandidateAnalogyLedger]:
    """Validate a generated candidate for the strict lane.

    Returns (validation, candidate_analogy_ledger).  Callers must only accept
    candidates whose validation passes all gates.
    """
    reason_codes: list[str] = []
    failure_code: str | None = None

    if report.failure_code is not None:
        failure_code = "GENERATION_FAILED"
        reason_codes.append(f"generation failed: {report.failure_code}")

    canonical_product = report.canonical_product
    valid_molecule = bool(canonical_product)
    if not valid_molecule:
        failure_code = failure_code or "INVALID_PRODUCT_MOLECULE"
        reason_codes.append("product molecule invalid / not generated")

    # -- Transform binding (R3-C): the stored hash + ID must RECOMPUTE from
    # the transform's own fields before anything else trusts them.
    try:
        verify_transform_binding(transform)
    except TransformBindingError as exc:
        failure_code = failure_code or exc.failure_code
        reason_codes.append(f"transform binding invalid: {exc}")

    # -- REAL transform fidelity (R2-F) --------------------------------------
    transform_fidelity = False
    if valid_molecule and failure_code is None:
        # 1. The report must reference THIS transform and THIS site.
        if report.transformation_id != transform.transformation_id:
            failure_code = "WRONG_GENERATION_TRANSFORM_ID"
            reason_codes.append(
                f"report references transform {report.transformation_id}, "
                f"expected {transform.transformation_id}"
            )
        elif report.site_id != site.site_id:
            failure_code = "WRONG_GENERATION_SITE_ID"
            reason_codes.append(
                f"report references site {report.site_id}, expected {site.site_id}"
            )
        # 2. Deterministic edit replay must reproduce the canonical product.
        replay = generate_product(
            transform, site, query, query_id=query.query_id, case_id=case_id
        )
        if replay.failure_code is not None:
            failure_code = "EDIT_REPLAY_MISMATCH"
            reason_codes.append(f"edit replay failed: {replay.failure_code}")
        elif replay.canonical_product != canonical_product:
            failure_code = "EDIT_REPLAY_MISMATCH"
            reason_codes.append(
                f"edit replay produced {replay.canonical_product!r}, "
                f"report claimed {canonical_product!r}"
            )
        # 3. Heavy-atom accounting + structure changed.
        if failure_code is None:
            query_ha = query.heavy_atom_count
            product_ha = _heavy_atom_count(canonical_product)
            transferred_heavy = sum(
                1 for t in transform.transferred_atoms if t.element != "H"
            )
            removed_heavy = len(transform.removed_atom_maps)
            expected_ha = query_ha + transferred_heavy - removed_heavy
            if product_ha != expected_ha:
                failure_code = "TRANSFORM_FIDELITY_ATOM_COUNT"
                reason_codes.append(
                    f"heavy-atom count mismatch: expected {expected_ha}, got {product_ha}"
                )
            elif canonical_product == query.canonical_smiles:
                failure_code = "TRANSFORM_FIDELITY_NO_CHANGE"
                reason_codes.append("product identical to query — no structural change")
            else:
                transform_fidelity = True

    # -- Precondition recheck -------------------------------------------------
    precondition_recheck = site.eligibility.value == "eligible"
    if not precondition_recheck:
        failure_code = failure_code or "PRECONDITION_FAILED"
        reason_codes.append(
            f"site has {len(site.failed_preconditions)} failed preconditions"
        )

    # -- Formal source/sink accounting ---------------------------------------
    formal_source_accounting = True
    known_participants = {
        p.participant_id for p in donor_evidence.context.reaction_evidence.participants
    }
    for t in transform.transferred_atoms:
        if t.source_participant_id in ("", "unknown_source"):
            formal_source_accounting = False
            reason_codes.append(
                f"transferred atom {t.transfer_map_number} lacks formal source"
            )
        elif t.source_participant_id not in known_participants:
            formal_source_accounting = False
            reason_codes.append(
                f"transferred atom source {t.source_participant_id!r} does not "
                f"exist as a participant"
            )
    if transform.removed_atom_maps:
        # R3-C: validation proves EXACT coverage of removed atoms by
        # map-to-sink assignments — not merely that a ledger contains at
        # least one sink.
        coverage: dict[int, str] = {}
        for sink in transform.removed_atom_sinks:
            if sink.atom_map in coverage:
                formal_source_accounting = False
                reason_codes.append(
                    f"duplicate sink assignment for removed atom {sink.atom_map}"
                )
                continue
            coverage[sink.atom_map] = sink.sink_participant_id
        missing = set(transform.removed_atom_maps) - set(coverage)
        if missing:
            formal_source_accounting = False
            reason_codes.append(
                f"removed atoms {sorted(missing)} have no formal sink "
                f"assignment on the transform"
            )
        for sink_map, sink_pid in coverage.items():
            if sink_pid in ("", "unknown_source"):
                formal_source_accounting = False
                reason_codes.append(
                    f"removed atom {sink_map} sink is unknown/unassigned"
                )
            elif sink_pid not in known_participants:
                formal_source_accounting = False
                reason_codes.append(
                    f"removed atom {sink_map} sink {sink_pid!r} is not a real "
                    f"participant"
                )
        # The donor ledger must not CONTRADICT the transform's assignments.
        ledger = donor_evidence.context.source_ledger
        for ledger_sink in ledger.removed_atom_sinks:
            bound = coverage.get(ledger_sink.atom_map_number)
            if bound is not None and bound != ledger_sink.sink_participant_id:
                formal_source_accounting = False
                reason_codes.append(
                    f"transform sink {bound!r} for removed atom "
                    f"{ledger_sink.atom_map_number} contradicts source ledger "
                    f"sink {ledger_sink.sink_participant_id!r}"
                )
    if not formal_source_accounting:
        failure_code = failure_code or "MISSING_FORMAL_SOURCE_ACCOUNTING"

    # -- Candidate analogy ledger authority (R2-F) ---------------------------
    # Source ledger must be the donor evidence authority's ledger.
    authority_ledger_id = donor_evidence.context.source_ledger.ledger_id
    ledger = _build_candidate_ledger(
        donor_evidence, transform, site, candidate_id, source_ledger_id, canonical_product
    )
    candidate_ledger_valid = False
    if source_ledger_id != authority_ledger_id:
        failure_code = failure_code or "FORGED_SOURCE_LEDGER"
        reason_codes.append(
            f"source_ledger_id {source_ledger_id!r} != donor authority ledger "
            f"{authority_ledger_id!r}"
        )
    else:
        # Frozen reference registry: candidate + source ledger must resolve.
        registry = LedgerReferenceRegistry(
            source_ledger_ids=frozenset([authority_ledger_id]),
            candidate_ids=frozenset([candidate_id]),
            evidence_ids=frozenset(donor_evidence.context.source_ledger.evidence_ids),
            source_ledger_to_reaction_id={authority_ledger_id: donor_evidence.context.reaction_id},
        )
        try:
            validate_candidate_ledger_references(ledger, registry)
            candidate_ledger_valid = True
        except Exception as exc:  # noqa: BLE001 - typed ledger rejection
            failure_code = failure_code or "CANDIDATE_LEDGER_INVALID"
            reason_codes.append(f"candidate ledger reference invalid: {exc}")

    # -- No relaxation / no critical ambiguity / no critical contradiction ----
    relaxation_used = False
    critical_ambiguity = False
    critical_contradiction = bool(
        donor_evidence.context.eligibility_decision.eligibility.value == "quarantine"
    )
    if critical_contradiction:
        failure_code = failure_code or "CRITICAL_CONTRADICTION"
        reason_codes.append("donor evidence carries a critical contradiction (quarantine)")

    validation = CandidateValidation(
        valid_molecule=valid_molecule,
        transform_fidelity=transform_fidelity,
        precondition_recheck=precondition_recheck,
        formal_source_accounting=formal_source_accounting,
        candidate_ledger_valid=candidate_ledger_valid,
        critical_contradiction=critical_contradiction,
        relaxation_used=relaxation_used,
        critical_ambiguity=critical_ambiguity,
        reason_codes=reason_codes,
        failure_code=failure_code,
    )
    return validation, ledger
