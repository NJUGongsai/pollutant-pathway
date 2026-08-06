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
    LedgerBalanceStatus,
    LineageResolutionQuality,
    MappingQualityClass,
    MappingStatus,
    ParticipantRole,
    QuarantineBehavior,
    SourceAssignmentMethod,
)
from reaction_agent.schemas.evidence import ReactionEvidence
from reaction_agent.schemas.ledger import (
    AddedAtomSource,
    CofactorChange,
    FormalAtomTransferAssignment,
    MechanisticOriginEvidence,
    RemovedAtomSink,
    RoleAssignment,
    SourceReactionLedger,
    StoichiometricEntry,
)
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


# Strict precondition: changed_atom_coverage must be complete for strict.
# Partial coverage means some changed heavy atoms are not mapped — strict
# requires full formal accounting (§4.2).
_STRICT_CHANGED_ATOM_COVERAGE_THRESHOLD = 1.0

# Strict precondition: mapped_heavy_atom_fraction must be complete. Partial
# heavy-atom mapping means some heavy atoms are unaccounted — strict requires
# full formal accounting (§6.4). Conservative frozen default; NO looser value.
_STRICT_MAPPED_HEAVY_ATOM_FRACTION_THRESHOLD = 1.0

# Strict precondition: the formal assignment quality must be the top controlled
# class. Anything below high_quality is not reliable enough for strict (§6.4).
_STRICT_ASSIGNMENT_QUALITY = MappingQualityClass.high_quality

# Round 4 (§6.1) strict preconditions.
# R4-01: every participant must be fully mapped. A partially-mapped participant
# cannot back a strict formal provenance claim (§7.3.2). Conservative frozen
# default; NO looser value.
_STRICT_PARTICIPANT_MAPPED_FRACTION_THRESHOLD = 1.0

# R4-14: strict only accepts the frozen controlled direction vocabulary. Step 3
# of ``_classify_state`` rejects only ""/"unknown"; any OTHER uncontrolled value
# (e.g. "sideways") is equally meaningless for strict provenance → fail closed.
_ALLOWED_STRICT_DIRECTIONS = frozenset({"forward", "reverse"})

# Round 5 (§7.1) participant registry: the participant side is a controlled
# vocabulary. Any other value (e.g. "middle") means the participant cannot be
# placed in a strict reactant/product provenance claim → fail closed.
_ALLOWED_PARTICIPANT_SIDES = frozenset({"reactant", "product"})

# Round 5 (§7.8) formal-atom-transfer assignment method: the schema default
# "formal" is the only controlled value. Any other value (empty is rejected by
# the schema, but "unknown"/"uncontrolled" strings are possible) means the
# transfer provenance is not trustworthy → fail closed.
_ALLOWED_FAT_ASSIGNMENT_METHODS = frozenset({"formal"})

# Round 5 (§7.4) role↔side consistency: transformed_substrate/product are
# authoritative identity roles — they must sit on the matching side AND be a
# resolved lineage reactant/product. The other frozen roles (co_substrate,
# cofactor, carrier, coproduct, spectator, catalytic_species, unknown) carry
# no side requirement in the frozen vocabulary (final_design §7.3).
_ROLE_SIDE_REQUIREMENT = {
    ParticipantRole.transformed_substrate: "reactant",
    ParticipantRole.transformed_product: "product",
}

# Round 6 (§6) cofactor direction vocabulary: the real source builder
# (reaction_agent/ledgers/source_builder.py) only ever emits "unknown", and the
# schema default is "unknown". There is NO other frozen direction authority in
# the P0 design/ADRs. Conservative policy: "unknown" keeps the existing
# conditional (missing_noncritical_cofactor_stoich) policy; ANY other value has
# no authority and must fail closed (never strict).
_ALLOWED_COFACTOR_DIRECTIONS = frozenset({"unknown"})


def _element_balance_contradiction(ledger: SourceReactionLedger) -> str | None:
    """Return a token-bearing reason for a STRUCTURAL element-balance
    contradiction that applies to EVERY ledger regardless of balance_status,
    else None (R4-04 + Round 5 §8.1).

    Structural consistency for every ElementBalance:
      - reactant_count >= 0 and product_count >= 0 (negative counts are an
        internal data contradiction, R5-10);
      - delta == product_count - reactant_count (a delta contradicting its own
        counts is an internal contradiction);
      - element keys unique (one element, two conflicting rows).

    The fully_balanced-specific requirement (delta == 0) is checked separately
    in ``_classify_state`` step 8 — a partial/unbalanced ledger may legally
    carry a CONSISTENT non-zero delta and must NOT be quarantined as a
    "fully-balanced contradiction" (R5-11).
    """
    seen_elements: set[str] = set()
    for eb in ledger.element_balance:
        if eb.element in seen_elements:
            return (
                f"element_balance_contradiction: duplicate element_balance row "
                f"for {eb.element!r}"
            )
        seen_elements.add(eb.element)
        if eb.reactant_count < 0:
            return (
                f"element_balance_contradiction: element {eb.element!r} has "
                f"negative reactant_count={eb.reactant_count}"
            )
        if eb.product_count < 0:
            return (
                f"element_balance_contradiction: element {eb.element!r} has "
                f"negative product_count={eb.product_count}"
            )
        if eb.delta != eb.product_count - eb.reactant_count:
            return (
                f"element_balance_contradiction: element {eb.element!r} delta="
                f"{eb.delta} inconsistent with product_count-reactant_count="
                f"{eb.product_count - eb.reactant_count}"
            )
    return None


# =====================================================================
# Round 5 (§7) — centralized participant/map registry + ledger reference
# validator. One reusable cross-object validator so the individual checks do
# not drift. These helpers ONLY run on the strict path (called from
# ``_validate_strict_preconditions``); they never mutate any input.
# =====================================================================

def _build_participant_registry(
    reaction_evidence: ReactionEvidence,
) -> tuple[dict | None, str | None]:
    """Build the participant/map registries for strict validation (§7.1).

    Returns ``(registry, None)`` on success, or ``(None, reason)`` when a
    participant-level invariant is violated:
      - participant_id uniqueness;
      - participant side in the controlled {reactant, product} vocabulary;
      - within-participant atom map uniqueness;
      - same-side cross-participant atom map uniqueness (reactant and product
        sides are SEPARATE registries because the formal mapping connects the
        two sides — a reactant and a product may both use map 1).

    The registry is the single authority the ledger-reference validator checks
    against; it is built ONCE per strict evaluation (§7.1).
    """
    participant_by_id: dict[str, ReactionParticipant] = {}
    reactant_map_registry: dict[int, str] = {}
    product_map_registry: dict[int, str] = {}
    maps_by_participant: dict[str, set[int]] = {}
    seen_ids: set[str] = set()
    for p in reaction_evidence.participants:
        if p.participant_id in seen_ids:
            return None, (
                f"strict_precondition_failed: participant_duplicate_id — "
                f"participant_id {p.participant_id!r} appears more than once"
            )
        seen_ids.add(p.participant_id)
        if p.side not in _ALLOWED_PARTICIPANT_SIDES:
            return None, (
                f"strict_precondition_failed: participant_side — participant "
                f"{p.participant_id!r} has uncontrolled side={p.side!r} (must "
                f"be 'reactant' or 'product')"
            )
        maps = list(p.atom_map_numbers)
        # R7-02: every atom-map identifier must be a strictly positive integer.
        # This central check runs on the participant authority FIRST, so formal
        # pairs, lineages, AddedAtomSource/RemovedAtomSink/FAT maps and
        # mechanistic product targets all inherit the rejection (§7.3).
        for m in maps:
            if not isinstance(m, int) or m <= 0:
                return None, (
                    f"strict_precondition_failed: participant_map_identifier — "
                    f"participant {p.participant_id!r} declares non-positive "
                    f"atom map identifier {m!r} (must be a positive integer)"
                )
        if len(maps) != len(set(maps)):
            return None, (
                f"strict_precondition_failed: participant_map_duplicate — "
                f"participant {p.participant_id!r} declares duplicate atom map "
                f"numbers {maps}"
            )
        if p.side == "reactant":
            for m in maps:
                owner = reactant_map_registry.get(m)
                if owner is not None and owner != p.participant_id:
                    return None, (
                        f"strict_precondition_failed: participant_map_collision "
                        f"— reactant atom map {m} declared by both {owner!r} "
                        f"and {p.participant_id!r}"
                    )
                reactant_map_registry[m] = p.participant_id
        else:  # product side
            for m in maps:
                owner = product_map_registry.get(m)
                if owner is not None and owner != p.participant_id:
                    return None, (
                        f"strict_precondition_failed: participant_map_collision "
                        f"— product atom map {m} declared by both {owner!r} "
                        f"and {p.participant_id!r}"
                    )
                product_map_registry[m] = p.participant_id
        participant_by_id[p.participant_id] = p
        maps_by_participant[p.participant_id] = set(maps)
    return {
        "participant_by_id": participant_by_id,
        "reactant_ids": {
            pid for pid, p in participant_by_id.items() if p.side == "reactant"
        },
        "product_ids": {
            pid for pid, p in participant_by_id.items() if p.side == "product"
        },
        "reactant_map_registry": reactant_map_registry,
        "product_map_registry": product_map_registry,
        "maps_by_participant": maps_by_participant,
    }, None


def _parse_heavy_atom_count(smiles: str) -> int | None:
    """Parse a SMILES with RDKit and return the heavy-atom count, or None if
    the SMILES cannot be parsed (or RDKit is unavailable at runtime).

    RDKit is probed lazily and read-only — no dependency is installed. If the
    molecule cannot be parsed, ``None`` means "cannot prove" and the caller
    must fail closed (Round 6 §10.3).
    """
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return int(mol.GetNumHeavyAtoms())
    except Exception:  # noqa: BLE001 — runtime probe failure => cannot prove
        return None


def _validate_participant_heavy_atom_evidence(
    reaction_evidence: ReactionEvidence,
) -> str | None:
    """Round 6 §10.5 + Round 7 §5: heavy-atom map evidence must be compatible
    with the molecule's heavy-atom content.

    - parseable & heavy_atom_count > 0 + EMPTY maps → fail closed
      (``participant_heavy_atom_map_evidence``, R6-05);
    - parseable & heavy_atom_count > 0 + unique map count != heavy count
      (underflow/overflow) → fail closed
      (``participant_heavy_atom_map_count``, R7-01) — a self-reported
      ``mapped_fraction=1.0`` (participant-level) or a global
      ``mapped_heavy_atom_fraction=1.0`` cannot override a participant-level
      map-count contradiction;
    - parseable & heavy_atom_count == 0 + maps declared → fail closed
      (``participant_heavy_atom_map_count``, R7-01 §5.5 zero-heavy policy) — a
      zero-heavy-atom participant must not carry heavy-atom map IDs;
    - parseable & heavy_atom_count == 0 + no maps → allowed (proton/electron
      policy);
    - unparseable / unprovable → fail closed (cannot verify, not guessed).
    """
    for p in reaction_evidence.participants:
        heavy = _parse_heavy_atom_count(p.canonical_smiles)
        if heavy is None:
            return (
                f"strict_precondition_failed: participant_heavy_atom_map_evidence "
                f"— participant {p.participant_id!r} SMILES "
                f"{p.canonical_smiles!r} cannot be parsed/verified (fail closed)"
            )
        unique_maps = set(p.atom_map_numbers)
        if heavy > 0 and not p.atom_map_numbers:
            return (
                f"strict_precondition_failed: participant_heavy_atom_map_evidence "
                f"— participant {p.participant_id!r} has {heavy} heavy atoms "
                f"but no atom_map_numbers (mapped_fraction={p.mapped_fraction} "
                f"cannot self-report full mapping)"
            )
        if heavy > 0 and len(unique_maps) != heavy:
            return (
                f"strict_precondition_failed: participant_heavy_atom_map_count "
                f"— participant {p.participant_id!r} has "
                f"heavy_atom_count={heavy} but unique_map_count="
                f"{len(unique_maps)} (mapped_fraction={p.mapped_fraction} "
                f"cannot self-report full mapping; atom_map_numbers="
                f"{list(p.atom_map_numbers)})"
            )
        if heavy == 0 and p.atom_map_numbers:
            return (
                f"strict_precondition_failed: participant_heavy_atom_map_count "
                f"— participant {p.participant_id!r} has heavy_atom_count=0 "
                f"but declares heavy-atom map IDs "
                f"{list(p.atom_map_numbers)} (zero-heavy policy; cannot claim "
                f"fully-mapped heavy atoms)"
            )
    return None


def _validate_stoich_collection(
    entries: list[StoichiometricEntry],
    expected_side: str,
    registry: dict,
    token_prefix: str,
) -> str | None:
    """Validate a reactant_entries / product_entries collection (§7.2 +
    Round 6 §7).

    - participant must exist;
    - participant side must equal the collection side;
    - entry.side must equal the collection side;
    - coefficient > 0 (§8.4);
    - (participant_id) is the SINGLE stoichiometric authority key: same key +
      same coefficient → ``{token_prefix}_duplicate``; same key + different
      coefficient → ``{token_prefix}_conflict``. Neither may silently
      double-count nor enter strict (R6-02).

    Round 6 does not require the collections to be non-empty — existing legal
    strict fixtures may keep empty entries. Only provided content is validated.
    """
    participant_by_id = registry["participant_by_id"]
    seen_coeff: dict[str, int] = {}  # participant_id -> coefficient
    for entry in entries:
        if entry.participant_id not in participant_by_id:
            return (
                f"strict_precondition_failed: {token_prefix}_ghost — "
                f"participant_id {entry.participant_id!r} not in participants"
            )
        p = participant_by_id[entry.participant_id]
        if p.side != expected_side:
            return (
                f"strict_precondition_failed: {token_prefix}_side — participant "
                f"{entry.participant_id!r} has side={p.side!r} (expected "
                f"{expected_side!r})"
            )
        if entry.side != expected_side:
            return (
                f"strict_precondition_failed: {token_prefix}_side — entry.side="
                f"{entry.side!r} disagrees with collection side {expected_side!r}"
            )
        if entry.coefficient <= 0:
            return (
                f"strict_precondition_failed: {token_prefix}_coefficient — "
                f"participant {entry.participant_id!r} coefficient="
                f"{entry.coefficient} (must be > 0)"
            )
        prev = seen_coeff.get(entry.participant_id)
        if prev is not None:
            if prev == entry.coefficient:
                return (
                    f"strict_precondition_failed: {token_prefix}_duplicate — "
                    f"duplicate {token_prefix} for participant "
                    f"{entry.participant_id!r}"
                )
            return (
                f"strict_precondition_failed: {token_prefix}_conflict — "
                f"conflicting coefficients {prev} and {entry.coefficient} for "
                f"participant {entry.participant_id!r}"
            )
        seen_coeff[entry.participant_id] = entry.coefficient
    return None


def _validate_stoichiometry(
    stoich_entries: list[StoichiometricEntry],
    registry: dict,
) -> str | None:
    """Validate ledger.stoichiometry (§7.3 + Round 6 §7).

    - participant exists (R4-07 ghost token preserved);
    - entry.side equals the participant side (R5-04);
    - coefficient > 0 (R5-05, §8.4);
    - (participant_id, side) is the SINGLE stoichiometric authority key: same
      key + same coefficient → ``stoichiometry_duplicate``; same key +
      different coefficient → ``stoichiometry_conflict`` (R6-02).
    """
    participant_by_id = registry["participant_by_id"]
    seen_coeff: dict[tuple[str, str], int] = {}  # (pid, side) -> coefficient
    for entry in stoich_entries:
        if entry.participant_id not in participant_by_id:
            return (
                f"strict_precondition_failed: stoichiometry_ghost — "
                f"participant_id {entry.participant_id!r} not in participants"
            )
        p = participant_by_id[entry.participant_id]
        if entry.side != p.side:
            return (
                f"strict_precondition_failed: stoichiometry_side — entry.side="
                f"{entry.side!r} disagrees with participant "
                f"{entry.participant_id!r} side={p.side!r}"
            )
        if entry.coefficient <= 0:
            return (
                f"strict_precondition_failed: stoichiometry_coefficient — "
                f"participant {entry.participant_id!r} coefficient="
                f"{entry.coefficient} (must be > 0)"
            )
        key = (entry.participant_id, entry.side)
        prev = seen_coeff.get(key)
        if prev is not None:
            if prev == entry.coefficient:
                return (
                    f"strict_precondition_failed: stoichiometry_duplicate — "
                    f"duplicate stoichiometry for {entry.participant_id!r}/"
                    f"{entry.side!r}"
                )
            return (
                f"strict_precondition_failed: stoichiometry_conflict — "
                f"conflicting coefficients {prev} and {entry.coefficient} for "
                f"{entry.participant_id!r}/{entry.side!r}"
            )
        seen_coeff[key] = entry.coefficient
    return None


def _validate_role_assignments(
    roles: list[RoleAssignment],
    registry: dict,
    lineages: list[ResolvedTransformedLineage],
) -> str | None:
    """Validate ledger.role_assignments (§7.4).

    - participant exists (R4-06 ghost token preserved);
    - exact duplicate assignments are not silently double-counted;
    - mutually contradictory assignments on one participant fail closed (the
      schema carries no typed ambiguity authority);
    - transformed_substrate must sit on a reactant that is a resolved lineage
      reactant; transformed_product on a product that is a lineage product.
    """
    participant_by_id = registry["participant_by_id"]
    lineage_reactants = {lin.reactant_participant_id for lin in lineages}
    lineage_products = {lin.product_participant_id for lin in lineages}
    seen_keys: set[tuple[str, ParticipantRole]] = set()
    roles_by_participant: dict[str, set[ParticipantRole]] = {}
    for ra in roles:
        if ra.participant_id not in participant_by_id:
            return (
                f"strict_precondition_failed: role_assignment_ghost — "
                f"participant_id {ra.participant_id!r} not in participants"
            )
        key = (ra.participant_id, ra.role)
        if key in seen_keys:
            return (
                f"strict_precondition_failed: role_assignment_duplicate — exact "
                f"duplicate role assignment {ra.participant_id!r}="
                f"{ra.role.value!r}"
            )
        seen_keys.add(key)
        prev_roles = roles_by_participant.setdefault(ra.participant_id, set())
        if prev_roles and ra.role not in prev_roles:
            return (
                f"strict_precondition_failed: role_assignment_conflict — "
                f"participant {ra.participant_id!r} carries contradictory roles "
                f"{sorted(r.value for r in prev_roles)} and {ra.role.value!r}"
            )
        prev_roles.add(ra.role)
        req_side = _ROLE_SIDE_REQUIREMENT.get(ra.role)
        if req_side is None:
            continue
        p = participant_by_id[ra.participant_id]
        if p.side != req_side:
            return (
                f"strict_precondition_failed: role_assignment_conflict — "
                f"participant {ra.participant_id!r} role={ra.role.value!r} on "
                f"side={p.side!r} (expected {req_side!r})"
            )
        if req_side == "reactant" and ra.participant_id not in lineage_reactants:
            return (
                f"strict_precondition_failed: role_assignment_conflict — "
                f"transformed_substrate {ra.participant_id!r} is not a resolved "
                f"lineage reactant"
            )
        if req_side == "product" and ra.participant_id not in lineage_products:
            return (
                f"strict_precondition_failed: role_assignment_conflict — "
                f"transformed_product {ra.participant_id!r} is not a resolved "
                f"lineage product"
            )
    return None


def _validate_added_atom_sources(
    aas_list: list[AddedAtomSource],
    registry: dict,
    mechanistic_evidence_ids: set[str],
) -> str | None:
    """Validate ledger.added_atom_sources (§7.6).

    - source_participant_id must exist (R4-05 ghost token preserved);
    - atom_map_number must belong to the declared source participant
      (R5-01 — an existing participant with an unknown map still fails);
    - mechanistic_evidence_id non-empty must resolve to an existing
      MechanisticOriginEvidence.evidence_id.
    """
    participant_by_id = registry["participant_by_id"]
    maps_by_participant = registry["maps_by_participant"]
    # R7-03a: collection-level duplicate/conflict authority. An exact duplicate
    # (same canonical signature) must not be double-counted; the same atom map
    # claimed by two different source authorities (no typed ambiguity authority)
    # must fail closed.
    seen_signatures: set[tuple] = set()
    map_to_authority: dict[int, tuple] = {}
    for aas in aas_list:
        sig = (
            aas.atom_map_number,
            aas.source_participant_id,
            aas.formal_assignment,
            aas.mechanistic_evidence_id,
        )
        if sig in seen_signatures:
            return (
                f"strict_precondition_failed: added_atom_source_duplicate — "
                f"duplicate AddedAtomSource for atom_map_number "
                f"{aas.atom_map_number} source {aas.source_participant_id!r}"
            )
        seen_signatures.add(sig)
        authority = (aas.source_participant_id, aas.mechanistic_evidence_id)
        prev_authority = map_to_authority.get(aas.atom_map_number)
        if prev_authority is not None and prev_authority != authority:
            return (
                f"strict_precondition_failed: added_atom_source_conflict — "
                f"atom_map_number {aas.atom_map_number} claimed by both "
                f"{prev_authority!r} and {authority!r} (no typed ambiguity "
                f"authority)"
            )
        map_to_authority[aas.atom_map_number] = authority

        if aas.source_participant_id not in participant_by_id:
            return (
                f"strict_precondition_failed: added_atom_source_ghost — "
                f"source_participant_id {aas.source_participant_id!r} not in "
                f"participants"
            )
        if aas.atom_map_number not in maps_by_participant.get(aas.source_participant_id, set()):
            return (
                f"strict_precondition_failed: added_atom_source_map — "
                f"atom_map_number {aas.atom_map_number} not in source "
                f"participant {aas.source_participant_id!r} atom_map_numbers"
            )
        if aas.mechanistic_evidence_id:
            if aas.mechanistic_evidence_id not in mechanistic_evidence_ids:
                return (
                    f"strict_precondition_failed: added_atom_source_evidence — "
                    f"mechanistic_evidence_id {aas.mechanistic_evidence_id!r} "
                    f"does not resolve to an existing MechanisticOriginEvidence"
                )
        # Round 6 §11.1: an AddedAtomSource that is NOT formally assigned AND
        # carries no mechanistic evidence is an unproven shell — the schema has
        # no authority to grant it strict donor truth.
        if not aas.formal_assignment and not aas.mechanistic_evidence_id:
            return (
                f"strict_precondition_failed: added_atom_source_unbacked — "
                f"atom_map_number {aas.atom_map_number} source "
                f"{aas.source_participant_id!r} is not formally assigned and has "
                f"no mechanistic evidence"
            )
    return None


def _validate_removed_atom_sinks(
    sinks: list[RemovedAtomSink],
    registry: dict,
) -> str | None:
    """Validate ledger.removed_atom_sinks (§7.7).

    - sink_participant_id must exist;
    - atom_map_number must exist in the sink participant's registry.

    If the schema cannot prove the sink/map authority, strict fails closed
    (never default to pass). Documented schema limitation: the sink's formal
    semantics (which participant the removed atom lands in) are not further
    typed, so existence + map-membership is the strongest provable check.
    """
    participant_by_id = registry["participant_by_id"]
    maps_by_participant = registry["maps_by_participant"]
    # R7-03b: collection-level duplicate/conflict authority. An exact duplicate
    # must not be double-counted; the same atom map claimed by two different
    # sink authorities (no typed ambiguity authority) must fail closed.
    seen_signatures: set[tuple] = set()
    map_to_sink: dict[int, str] = {}
    for sink in sinks:
        sig = (sink.atom_map_number, sink.sink_participant_id, sink.formal_assignment)
        if sig in seen_signatures:
            return (
                f"strict_precondition_failed: removed_atom_sink_duplicate — "
                f"duplicate RemovedAtomSink for atom_map_number "
                f"{sink.atom_map_number} sink {sink.sink_participant_id!r}"
            )
        seen_signatures.add(sig)
        prev_sink = map_to_sink.get(sink.atom_map_number)
        if prev_sink is not None and prev_sink != sink.sink_participant_id:
            return (
                f"strict_precondition_failed: removed_atom_sink_conflict — "
                f"atom_map_number {sink.atom_map_number} claimed by both "
                f"{prev_sink!r} and {sink.sink_participant_id!r} (no typed "
                f"ambiguity authority)"
            )
        map_to_sink[sink.atom_map_number] = sink.sink_participant_id

        if sink.sink_participant_id not in participant_by_id:
            return (
                f"strict_precondition_failed: removed_atom_sink_ghost — "
                f"sink_participant_id {sink.sink_participant_id!r} not in "
                f"participants"
            )
        if sink.atom_map_number not in maps_by_participant.get(sink.sink_participant_id, set()):
            return (
                f"strict_precondition_failed: removed_atom_sink_map — "
                f"atom_map_number {sink.atom_map_number} not in sink participant "
                f"{sink.sink_participant_id!r} atom_map_numbers"
            )
        # R7-04: a RemovedAtomSink with formal_assignment=False has NO other
        # typed sink authority (the schema carries no mechanistic sink evidence),
        # so it cannot grant strict donor truth.
        if not sink.formal_assignment:
            return (
                f"strict_precondition_failed: removed_atom_sink_unbacked — "
                f"atom_map_number {sink.atom_map_number} sink "
                f"{sink.sink_participant_id!r} is not formally assigned and has "
                f"no other typed sink authority"
            )
    return None


def _validate_cofactor_changes(
    changes: list[CofactorChange],
    participant_by_id: dict,
) -> str | None:
    """Validate ledger.cofactor_changes (§7.5 + Round 6 §6).

    - participant must exist; ghost cofactor references fail closed
      (R4/§7.5, ``cofactor_change_ghost``);
    - ``direction`` must be in the frozen controlled vocabulary
      (``_ALLOWED_COFACTOR_DIRECTIONS`` = {"unknown"}). ``unknown`` continues
      to use the existing conditional policy (handled in ``_classify_state``);
      any OTHER non-empty value has no frozen authority (R6-01) and must fail
      closed (``cofactor_change_direction``) — a non-empty string is NOT a
      known direction.
    """
    for cc in changes:
        if cc.participant_id not in participant_by_id:
            return (
                f"strict_precondition_failed: cofactor_change_ghost — "
                f"participant_id {cc.participant_id!r} not in participants"
            )
        if cc.direction not in _ALLOWED_COFACTOR_DIRECTIONS:
            return (
                f"strict_precondition_failed: cofactor_change_direction — "
                f"participant {cc.participant_id!r} direction="
                f"{cc.direction!r} not in controlled vocabulary "
                f"{sorted(_ALLOWED_COFACTOR_DIRECTIONS)}"
            )
    return None


def _validate_formal_atom_transfers(
    fats: list[FormalAtomTransferAssignment],
    registry: dict,
    formal_edge_reactant_maps: dict[tuple[str, str], set[int]],
) -> str | None:
    """Validate ledger.formal_atom_transfer_assignments (§7.8 + Round 6 §9).

    - assignment_method in the frozen controlled vocabulary ("formal");
    - source/target participants exist (R4-08 ghost token preserved);
    - source side = reactant, target side = product (R5-06);
    - transferred map list must be NON-EMPTY (R6-04 — a shell assignment that
      transfers no atom cannot be strict by vacuous truth) and contain no
      duplicates (``formal_atom_transfer_duplicate_map``);
    - transferred maps exist in the source participant's maps (R5-06 map=999);
    - each transferred map is supported by a formal mapped pair on the
      source→target edge (no conflict with the MappingReport formal pairs).

    The whole collection may be empty (assignment-level validation, not
    collection requiredness).
    """
    participant_by_id = registry["participant_by_id"]
    maps_by_participant = registry["maps_by_participant"]
    # R7-03c: collection-level duplicate/conflict authority (pre-pass, before
    # the per-assignment checks). An exact duplicate assignment must not be
    # double-counted; the same source atom map claimed by two DIFFERENT target
    # edges (no typed split authority) must fail closed.
    seen_signatures: set[tuple] = set()
    source_map_targets: dict[tuple[str, int], str] = {}
    for fat in fats:
        sig = (
            fat.source_participant_id,
            fat.target_participant_id,
            tuple(sorted(set(fat.transferred_atom_map_numbers))),
            fat.assignment_method,
        )
        if sig in seen_signatures:
            return (
                f"strict_precondition_failed: formal_atom_transfer_duplicate_"
                f"assignment — duplicate FormalAtomTransferAssignment "
                f"{fat.source_participant_id!r}→{fat.target_participant_id!r} "
                f"transfers {fat.transferred_atom_map_numbers}"
            )
        seen_signatures.add(sig)
        for m in fat.transferred_atom_map_numbers:
            key = (fat.source_participant_id, m)
            prev_target = source_map_targets.get(key)
            if prev_target is not None and prev_target != fat.target_participant_id:
                return (
                    f"strict_precondition_failed: formal_atom_transfer_"
                    f"assignment_conflict — source atom map {m} of "
                    f"{fat.source_participant_id!r} claimed by target edges "
                    f"{prev_target!r} and {fat.target_participant_id!r} (no "
                    f"typed split authority)"
                )
            source_map_targets[key] = fat.target_participant_id

    for fat in fats:
        if fat.assignment_method not in _ALLOWED_FAT_ASSIGNMENT_METHODS:
            return (
                f"strict_precondition_failed: formal_atom_transfer_method — "
                f"assignment_method {fat.assignment_method!r} not in controlled "
                f"vocabulary {sorted(_ALLOWED_FAT_ASSIGNMENT_METHODS)}"
            )
        if fat.source_participant_id not in participant_by_id:
            return (
                f"strict_precondition_failed: formal_atom_transfer_ghost — "
                f"source_participant_id {fat.source_participant_id!r} not in "
                f"participants"
            )
        if fat.target_participant_id not in participant_by_id:
            return (
                f"strict_precondition_failed: formal_atom_transfer_ghost — "
                f"target_participant_id {fat.target_participant_id!r} not in "
                f"participants"
            )
        src = participant_by_id[fat.source_participant_id]
        tgt = participant_by_id[fat.target_participant_id]
        if src.side != "reactant":
            return (
                f"strict_precondition_failed: formal_atom_transfer_side — source "
                f"{fat.source_participant_id!r} has side={src.side!r} (expected "
                f"'reactant')"
            )
        if tgt.side != "product":
            return (
                f"strict_precondition_failed: formal_atom_transfer_side — target "
                f"{fat.target_participant_id!r} has side={tgt.side!r} (expected "
                f"'product')"
            )
        if not fat.transferred_atom_map_numbers:
            return (
                f"strict_precondition_failed: formal_atom_transfer_empty — "
                f"assignment {fat.source_participant_id!r}→"
                f"{fat.target_participant_id!r} transfers no atoms"
            )
        if len(fat.transferred_atom_map_numbers) != len(set(fat.transferred_atom_map_numbers)):
            return (
                f"strict_precondition_failed: formal_atom_transfer_duplicate_map "
                f"— assignment {fat.source_participant_id!r}→"
                f"{fat.target_participant_id!r} transfers duplicate maps "
                f"{fat.transferred_atom_map_numbers}"
            )
        src_maps = maps_by_participant.get(fat.source_participant_id, set())
        for m in fat.transferred_atom_map_numbers:
            if m not in src_maps:
                return (
                    f"strict_precondition_failed: formal_atom_transfer_map — "
                    f"transferred map {m} not in source participant "
                    f"{fat.source_participant_id!r} atom_map_numbers"
                )
        edge = (fat.source_participant_id, fat.target_participant_id)
        edge_maps = formal_edge_reactant_maps.get(edge, set())
        for m in fat.transferred_atom_map_numbers:
            if m not in edge_maps:
                return (
                    f"strict_precondition_failed: formal_atom_transfer_pair — "
                    f"transferred map {m} not supported by a formal mapped pair "
                    f"on edge {edge}"
                )
    return None


def _validate_mechanistic_evidence(
    mech_list: list[MechanisticOriginEvidence],
    registry: dict,
) -> str | None:
    """Validate ledger.mechanistic_origin_evidence (§7.9 + Round 6 §8).

    - evidence_id unique;
    - source_participant_id non-empty → must exist;
    - target_atom_map_numbers must be NON-EMPTY (§11.2 — an evidence that
      targets no atom cannot be a strict mechanism authority by vacuous
      truth) and every target map must resolve in the PRODUCT-side map
      registry (R6-03) — a map that exists only on the reactant side cannot
      be a product atom target.
    Formal mapping stays SEPARATE from mechanistic origin (a generic mapper
    cannot auto-generate mechanistic proof — the schema's MechanisticAtomOrigin
    already requires evidence_ids).
    """
    participant_by_id = registry["participant_by_id"]
    product_maps: set[int] = set()
    for pid in registry["product_ids"]:
        product_maps |= registry["maps_by_participant"].get(pid, set())
    seen_ids: set[str] = set()
    for me in mech_list:
        if me.evidence_id in seen_ids:
            return (
                f"strict_precondition_failed: mechanistic_evidence_duplicate_id "
                f"— evidence_id {me.evidence_id!r} appears more than once"
            )
        seen_ids.add(me.evidence_id)
        if me.source_participant_id is not None and me.source_participant_id not in participant_by_id:
            return (
                f"strict_precondition_failed: mechanistic_evidence_ghost — "
                f"source_participant_id {me.source_participant_id!r} not in "
                f"participants"
            )
        if not me.target_atom_map_numbers:
            return (
                f"strict_precondition_failed: mechanistic_evidence_empty_target "
                f"— evidence_id {me.evidence_id!r} targets no product atom"
            )
        # R7-03d: an evidence must not list the same product atom target twice
        # (internal collection duplicate would double-count a mechanism target).
        if len(me.target_atom_map_numbers) != len(set(me.target_atom_map_numbers)):
            return (
                f"strict_precondition_failed: mechanistic_evidence_duplicate_"
                f"target_map — evidence_id {me.evidence_id!r} targets "
                f"duplicate product atom maps "
                f"{me.target_atom_map_numbers}"
            )
        for m in me.target_atom_map_numbers:
            if m not in product_maps:
                return (
                    f"strict_precondition_failed: mechanistic_evidence_map_"
                    f"product_side — target_atom_map_number {m} not in "
                    f"product-side map registry"
                )
    return None


def _validate_ledger_references(
    ledger: SourceReactionLedger,
    registry: dict,
    lineages: list[ResolvedTransformedLineage],
    formal_edge_reactant_maps: dict[tuple[str, str], set[int]],
) -> str | None:
    """Validate EVERY ledger cross-object reference against the participant
    registry (§7.2–§7.9). Central, reusable, minimal — one validator so the
    individual checks cannot drift. Returns a fail-closed reason or None."""
    failure = _validate_stoich_collection(
        ledger.reactant_entries, "reactant", registry, "reactant_entry")
    if failure:
        return failure
    failure = _validate_stoich_collection(
        ledger.product_entries, "product", registry, "product_entry")
    if failure:
        return failure
    failure = _validate_stoichiometry(ledger.stoichiometry, registry)
    if failure:
        return failure
    failure = _validate_role_assignments(ledger.role_assignments, registry, lineages)
    if failure:
        return failure
    failure = _validate_added_atom_sources(
        ledger.added_atom_sources, registry,
        {me.evidence_id for me in ledger.mechanistic_origin_evidence})
    if failure:
        return failure
    failure = _validate_removed_atom_sinks(ledger.removed_atom_sinks, registry)
    if failure:
        return failure
    failure = _validate_cofactor_changes(
        ledger.cofactor_changes, registry["participant_by_id"])
    if failure:
        return failure
    failure = _validate_formal_atom_transfers(
        ledger.formal_atom_transfer_assignments, registry,
        formal_edge_reactant_maps)
    if failure:
        return failure
    failure = _validate_mechanistic_evidence(
        ledger.mechanistic_origin_evidence, registry)
    if failure:
        return failure
    return None


def _validate_strict_preconditions(
    reaction_evidence: ReactionEvidence,
    ledger: SourceReactionLedger,
    lineages: list[ResolvedTransformedLineage],
) -> str | None:
    """Validate the cross-invariants required for strict_eligible (§4.2).

    Returns None if ALL strict preconditions hold, or a typed fail-closed
    reason string if any precondition fails. The engine calls this before
    granting strict_eligible; any failure → fail-closed (never strict).

    These are cross-object invariants the matrix assumes (mapping/ledger/
    lineage consistency) that cannot live in a single model validator. They
    guard against legal-schema-but-contradictory inputs from JSON
    deserialization, external import, migration, or hand construction (§4.3).
    """
    # 1. ledger reaction_evidence_id must match the evidence reaction_id
    if ledger.reaction_evidence_id != reaction_evidence.reaction_id:
        return (
            f"strict_precondition_failed: ledger.reaction_evidence_id="
            f"{ledger.reaction_evidence_id!r} != reaction_id="
            f"{reaction_evidence.reaction_id!r}"
        )

    # 2. source_completeness must be complete
    if ledger.source_completeness != "complete":
        return (
            f"strict_precondition_failed: source_completeness="
            f"{ledger.source_completeness!r} (must be 'complete' for strict)"
        )

    # 3. mapping_completeness must be complete
    if ledger.mapping_completeness != "complete":
        return (
            f"strict_precondition_failed: mapping_completeness="
            f"{ledger.mapping_completeness!r} (must be 'complete' for strict)"
        )

    # 4. mapping_report must exist on the evidence
    mr = reaction_evidence.mapping_report
    if mr is None:
        return "strict_precondition_failed: mapping_report is None"

    # 5. mapping_status must be fully_mapped
    if mr.mapping_status != MappingStatus.fully_mapped:
        return (
            f"strict_precondition_failed: mapping_status="
            f"{mr.mapping_status.value!r} (must be fully_mapped for strict)"
        )

    # 6. no fallback method (MCS / center-pair fallback is not strict)
    if mr.fallback_method is not None:
        return (
            f"strict_precondition_failed: fallback_method={mr.fallback_method!r} "
            f"(must be None for strict; MCS/center-pair not strict)"
        )

    # 7. map_number_uniqueness must hold
    if not mr.map_number_uniqueness:
        return "strict_precondition_failed: map_number_uniqueness is False"

    # 8. changed_atom_coverage must meet the strict threshold
    if mr.changed_atom_coverage < _STRICT_CHANGED_ATOM_COVERAGE_THRESHOLD:
        return (
            f"strict_precondition_failed: changed_atom_coverage="
            f"{mr.changed_atom_coverage} < "
            f"{_STRICT_CHANGED_ATOM_COVERAGE_THRESHOLD} (strict requires full coverage)"
        )

    # 8b. mapped_heavy_atom_fraction must meet the strict threshold
    if mr.mapped_heavy_atom_fraction < _STRICT_MAPPED_HEAVY_ATOM_FRACTION_THRESHOLD:
        return (
            f"strict_precondition_failed: mapped_heavy_atom_fraction="
            f"{mr.mapped_heavy_atom_fraction} < "
            f"{_STRICT_MAPPED_HEAVY_ATOM_FRACTION_THRESHOLD} "
            f"(strict requires full heavy-atom mapping)"
        )

    # 9. formal_mapped_source_assignment must exist
    fsa = mr.formal_mapped_source_assignment
    if fsa is None:
        return "strict_precondition_failed: formal_mapped_source_assignment is None"

    # 10. assignment_method must be formal_mapped (not mcs / center_pair / unknown)
    if fsa.assignment_method != SourceAssignmentMethod.formal_mapped:
        return (
            f"strict_precondition_failed: assignment_method="
            f"{fsa.assignment_method.value!r} (must be formal_mapped; "
            f"mcs/center_pair/unknown not strict)"
        )

    # 10b. formal assignment must be unambiguous
    if fsa.assignment_ambiguity:
        return (
            "strict_precondition_failed: formal assignment_ambiguity is True "
            "(ambiguous formal assignment not strict)"
        )

    # 10c. formal assignment quality must meet the strict policy
    if fsa.assignment_quality != _STRICT_ASSIGNMENT_QUALITY:
        return (
            f"strict_precondition_failed: assignment_quality="
            f"{fsa.assignment_quality.value!r} (must be "
            f"{_STRICT_ASSIGNMENT_QUALITY.value!r} for strict)"
        )

    # 11. no identity-critical ambiguity (symmetry / resonance-tautomer)
    if mr.symmetry_ambiguity:
        return "strict_precondition_failed: symmetry_ambiguity is True"
    if mr.resonance_tautomer_ambiguity:
        return "strict_precondition_failed: resonance_tautomer_ambiguity is True"

    # =================================================================
    # Round 4 (§6.1) additional cross-invariants. Each closes a confirmed
    # strict fail-open and returns a stable, invariant-specific reason token so
    # the targeted tests assert the SPECIFIC defect was caught (§8 req 4). All
    # fail closed → strict_prohibited (never strict).
    # =================================================================
    participant_ids = {p.participant_id for p in reaction_evidence.participants}

    # Round 5 §7.1: build the participant/map registry ONCE and validate the
    # participant-level invariants (unique IDs, controlled side vocabulary,
    # within-participant map uniqueness, same-side cross-participant map
    # uniqueness) BEFORE any per-reference check — so a collision can never be
    # masked by a later "uncovered map" or "duplicate pair" reason.
    registry, registry_failure = _build_participant_registry(reaction_evidence)
    if registry_failure is not None:
        return registry_failure

    # R4-14: strict only accepts the controlled direction vocabulary (step 3
    # rejects only ""/"unknown"; an uncontrolled value like "sideways" is still
    # meaningless for strict provenance).
    if reaction_evidence.direction not in _ALLOWED_STRICT_DIRECTIONS:
        return (
            f"strict_precondition_failed: direction="
            f"{reaction_evidence.direction!r} not in controlled strict "
            f"vocabulary {sorted(_ALLOWED_STRICT_DIRECTIONS)}"
        )

    # R4-01: every participant must be fully mapped. A participant reporting
    # only partial atom mapping cannot back a strict formal provenance claim.
    for p in reaction_evidence.participants:
        if p.mapped_fraction < _STRICT_PARTICIPANT_MAPPED_FRACTION_THRESHOLD:
            return (
                f"strict_precondition_failed: participant_mapped_fraction "
                f"{p.participant_id!r}={p.mapped_fraction} < "
                f"{_STRICT_PARTICIPANT_MAPPED_FRACTION_THRESHOLD} "
                f"(strict requires full per-participant mapping)"
            )

    # Round 6 §10.5 (R6-05): a parseable heavy-atom participant with NO atom
    # map numbers cannot self-report full mapping via mapped_fraction=1.0.
    # Zero-heavy-atom participants (proton/electron policy) are allowed; an
    # unparseable SMILES fails closed (cannot prove, not guessed).
    heavy_failure = _validate_participant_heavy_atom_evidence(reaction_evidence)
    if heavy_failure is not None:
        return heavy_failure

    # R4-12: an identity ambiguity set cannot be proven identity-irrelevant by
    # the current untyped schema → fail closed.
    if reaction_evidence.ambiguity_sets:
        return (
            f"strict_precondition_failed: ambiguity_sets present "
            f"({len(reaction_evidence.ambiguity_sets)}) — no typed authority to "
            f"prove identity-irrelevance"
        )

    # R4-13 + Round 5 §10.1: the embedded resolved_transformed_lineages id
    # list must be validated for duplicates BEFORE the set comparison — a
    # duplicated embedded ID that collapses to the same set as the external
    # lineages must never be silently accepted (R5-15). It must also not
    # disagree with the external typed lineages (no silent pick of one).
    embedded_lineages_raw = reaction_evidence.resolved_transformed_lineages
    if len(embedded_lineages_raw) != len(set(embedded_lineages_raw)):
        return (
            f"strict_precondition_failed: embedded_lineage_duplicate — embedded "
            f"resolved_transformed_lineages contain duplicate IDs "
            f"{embedded_lineages_raw}"
        )
    embedded_lineage_ids = set(embedded_lineages_raw)
    if embedded_lineage_ids:
        external_lineage_ids = {lin.lineage_id for lin in lineages}
        if embedded_lineage_ids != external_lineage_ids:
            return (
                f"strict_precondition_failed: embedded_external_lineage mismatch "
                f"— embedded {sorted(embedded_lineage_ids)} != external "
                f"{sorted(external_lineage_ids)}"
            )

    # R4-09: any generic ledger unknown blocks strict — the schema carries no
    # typed criticality to prove the unknown is harmless.
    if ledger.unknowns:
        return (
            f"strict_precondition_failed: ledger_unknowns present "
            f"({list(ledger.unknowns)}) — cannot prove harmless"
        )

    # Round 5 §7.2–§7.9: complete ledger participant/map reference integrity.
    # This central validator supersedes the Round-4 per-collection ghost loops
    # (AddedAtomSource / RoleAssignment / StoichiometricEntry /
    # FormalAtomTransferAssignment) while preserving their ghost reason tokens,
    # and additionally verifies side consistency, coefficients, atom-map
    # membership, formal-transfer↔formal-pair consistency, mechanistic
    # evidence linkage, and role contradictions (§7.1–§7.9).
    formal_edge_reactant_maps: dict[tuple[str, str], set[int]] = {}
    if fsa.mapped_atom_pairs:
        for _pair in fsa.mapped_atom_pairs:
            _edge = (_pair.reactant_participant_id, _pair.product_participant_id)
            formal_edge_reactant_maps.setdefault(_edge, set()).add(_pair.reactant_atom_map)
    ledger_failure = _validate_ledger_references(
        ledger, registry, lineages, formal_edge_reactant_maps)
    if ledger_failure is not None:
        return ledger_failure

    # -- Formal mapped pair cross-invariants (§6.4) --
    # Each pair must reference participants that EXIST, are on the CORRECT side,
    # and use atom maps that actually belong to those participants. A pair
    # referencing an unknown participant, wrong side, or unknown atom map means
    # the formal mapping is not trustworthy → never strict. Contradictory pairs
    # (one reactant atom map assigned to two product atom maps) and duplicate
    # pairs are also rejected (string non-emptiness is NOT enough).
    participant_by_id = {p.participant_id: p for p in reaction_evidence.participants}
    seen_pairs: set[tuple[str, int, str, int]] = set()
    reactant_map_targets: dict[tuple[str, int], tuple[str, int]] = {}
    # R4-03: reverse-collision guard — a product atom target claimed by two
    # distinct reactant atoms (many-to-one) has no typed merge authority.
    product_target_sources: dict[tuple[str, int], tuple[str, int]] = {}
    for pair in fsa.mapped_atom_pairs:
        r_p = participant_by_id.get(pair.reactant_participant_id)
        if r_p is None:
            return (
                f"strict_precondition_failed: mapped pair reactant_participant_id="
                f"{pair.reactant_participant_id!r} not in participants"
            )
        p_p = participant_by_id.get(pair.product_participant_id)
        if p_p is None:
            return (
                f"strict_precondition_failed: mapped pair product_participant_id="
                f"{pair.product_participant_id!r} not in participants"
            )
        if r_p.side != "reactant":
            return (
                f"strict_precondition_failed: mapped pair reactant participant "
                f"{pair.reactant_participant_id!r} has side={r_p.side!r} "
                f"(expected 'reactant')"
            )
        if p_p.side != "product":
            return (
                f"strict_precondition_failed: mapped pair product participant "
                f"{pair.product_participant_id!r} has side={p_p.side!r} "
                f"(expected 'product')"
            )
        if pair.reactant_atom_map not in r_p.atom_map_numbers:
            return (
                f"strict_precondition_failed: mapped pair reactant_atom_map="
                f"{pair.reactant_atom_map} not in participant "
                f"{pair.reactant_participant_id!r} atom_map_numbers"
            )
        if pair.product_atom_map not in p_p.atom_map_numbers:
            return (
                f"strict_precondition_failed: mapped pair product_atom_map="
                f"{pair.product_atom_map} not in participant "
                f"{pair.product_participant_id!r} atom_map_numbers"
            )
        key = (
            pair.reactant_participant_id, pair.reactant_atom_map,
            pair.product_participant_id, pair.product_atom_map,
        )
        if key in seen_pairs:
            return f"strict_precondition_failed: duplicate mapped pair {key}"
        seen_pairs.add(key)
        src = (pair.reactant_participant_id, pair.reactant_atom_map)
        tgt = (pair.product_participant_id, pair.product_atom_map)
        if src in reactant_map_targets and reactant_map_targets[src] != tgt:
            return (
                f"strict_precondition_failed: contradictory mapping — reactant "
                f"atom {src} assigned to both {reactant_map_targets[src]} and {tgt}"
            )
        reactant_map_targets[src] = tgt
        # R4-03: the product atom target must not already be claimed by a
        # DIFFERENT reactant atom (many-to-one reverse collision).
        if tgt in product_target_sources and product_target_sources[tgt] != src:
            return (
                f"strict_precondition_failed: product_atom_target_collision — "
                f"product atom {tgt} claimed by both "
                f"{product_target_sources[tgt]} and {src}"
            )
        product_target_sources[tgt] = src

    # R4-02: every declared participant atom map must be realised by a formal
    # mapped pair. A self-reported full mapping (mapped_heavy_atom_fraction=1.0)
    # whose pairs do not actually cover every declared participant atom map is
    # not trustworthy for strict (§7.3.2).
    covered_reactant_maps: dict[str, set[int]] = {}
    covered_product_maps: dict[str, set[int]] = {}
    for pair in fsa.mapped_atom_pairs:
        covered_reactant_maps.setdefault(
            pair.reactant_participant_id, set()).add(pair.reactant_atom_map)
        covered_product_maps.setdefault(
            pair.product_participant_id, set()).add(pair.product_atom_map)
    for p in reaction_evidence.participants:
        if not p.atom_map_numbers:
            continue
        if p.side == "reactant":
            covered = covered_reactant_maps.get(p.participant_id, set())
        elif p.side == "product":
            covered = covered_product_maps.get(p.participant_id, set())
        else:
            covered = set()
        uncovered = [m for m in p.atom_map_numbers if m not in covered]
        if uncovered:
            return (
                f"strict_precondition_failed: participant_atom_map_uncovered — "
                f"participant {p.participant_id!r} declared atom maps {uncovered} "
                f"not covered by any formal mapped pair"
            )

    # 12. lineages non-empty (identity cannot be verified without a lineage)
    if not lineages:
        return "strict_precondition_failed: no resolved lineages"

    # R4-10 + Round 5 §10.3: no duplicate lineage id, no internal duplicate
    # transformed map, and no SEMANTIC duplicate lineage content. The content
    # signature treats transformed maps as a SET (sorted unique) so a
    # reordered [1,2] vs [2,1] is the same lineage double-counted under a
    # different lineage_id (R5-16). A repeated lineage double-counts identity
    # evidence — fail closed.
    seen_lineage_ids: set[str] = set()
    seen_lineage_content: set[tuple] = set()
    for lin in lineages:
        if lin.lineage_id in seen_lineage_ids:
            return (
                f"strict_precondition_failed: duplicate_lineage — lineage_id "
                f"{lin.lineage_id!r} appears more than once"
            )
        seen_lineage_ids.add(lin.lineage_id)
        maps = list(lin.transformed_atom_maps)
        if len(maps) != len(set(maps)):
            return (
                f"strict_precondition_failed: lineage_map_duplicate — lineage "
                f"{lin.lineage_id!r} transformed_atom_maps contain duplicates "
                f"{maps}"
            )
        content = (
            lin.reactant_participant_id,
            lin.product_participant_id,
            tuple(sorted(set(maps))),
        )
        if content in seen_lineage_content:
            return (
                f"strict_precondition_failed: duplicate_lineage — semantic-"
                f"duplicate lineage content {content} (reordered or repeated "
                f"edge/maps)"
            )
        seen_lineage_content.add(content)

    # -- Resolved lineage cross-invariants (§6.4) --
    # Build the formal reactant→product participant edges and the reactant atom
    # maps supporting each edge, so each lineage can be checked for actual
    # formal-mapping support (not merely for participant existence).
    formal_edges: set[tuple[str, str]] = set()
    edge_reactant_maps: dict[tuple[str, str], set[int]] = {}
    for pair in fsa.mapped_atom_pairs:
        edge = (pair.reactant_participant_id, pair.product_participant_id)
        formal_edges.add(edge)
        edge_reactant_maps.setdefault(edge, set()).add(pair.reactant_atom_map)

    for lin in lineages:
        # 13. participants must exist in the complete participant multiset ...
        r_p = participant_by_id.get(lin.reactant_participant_id)
        if r_p is None:
            return (
                f"strict_precondition_failed: lineage {lin.lineage_id} "
                f"reactant_participant_id {lin.reactant_participant_id!r} "
                f"not in participants multiset"
            )
        p_p = participant_by_id.get(lin.product_participant_id)
        if p_p is None:
            return (
                f"strict_precondition_failed: lineage {lin.lineage_id} "
                f"product_participant_id {lin.product_participant_id!r} "
                f"not in participants multiset"
            )
        # ... and be on the correct side
        if r_p.side != "reactant":
            return (
                f"strict_precondition_failed: lineage {lin.lineage_id} reactant "
                f"{lin.reactant_participant_id!r} has side={r_p.side!r} "
                f"(expected 'reactant')"
            )
        if p_p.side != "product":
            return (
                f"strict_precondition_failed: lineage {lin.lineage_id} product "
                f"{lin.product_participant_id!r} has side={p_p.side!r} "
                f"(expected 'product')"
            )
        # resolution_quality must be fully resolved
        if lin.resolution_quality != LineageResolutionQuality.resolved:
            return (
                f"strict_precondition_failed: lineage {lin.lineage_id} "
                f"resolution_quality={lin.resolution_quality.value!r} "
                f"(must be 'resolved' for strict)"
            )
        # no identity ambiguity: the current schema carries no typed merge
        # authority to prove a partial ambiguity does not affect identity.
        if lin.ambiguity != "none":
            return (
                f"strict_precondition_failed: lineage {lin.lineage_id} "
                f"ambiguity={lin.ambiguity!r} (must be 'none' for strict)"
            )
        # lineage pair must be supported by a formal mapped edge
        edge = (lin.reactant_participant_id, lin.product_participant_id)
        if edge not in formal_edges:
            return (
                f"strict_precondition_failed: lineage {lin.lineage_id} pair "
                f"{edge} is not supported by any formal mapped pair"
            )
        # transformed_atom_maps must be supported by the mapped reactant atoms
        supported_maps = edge_reactant_maps.get(edge, set())
        unsupported = [
            m for m in lin.transformed_atom_maps if m not in supported_maps
        ]
        if unsupported:
            return (
                f"strict_precondition_failed: lineage {lin.lineage_id} "
                f"transformed_atom_maps {unsupported} not supported by mapped atoms"
            )

    # 14. forbidden cross-lineage pairing (§6.3): keep the original check (a
    # participant that is both a lineage reactant and product), AND detect the
    # 2OG→hydroxyproline class — two DISTINCT transformed reactants claiming the
    # SAME transformed product. The current schema carries no typed merge
    # authority, so multiple reactants → one product fails closed.
    lineage_reactants = {lin.reactant_participant_id for lin in lineages}
    lineage_products = {lin.product_participant_id for lin in lineages}
    cross = lineage_reactants & lineage_products
    if cross:
        return (
            f"strict_precondition_failed: forbidden cross-lineage pairing "
            f"(participant is both reactant and product across lineages): "
            f"{sorted(cross)}"
        )
    product_to_reactants: dict[str, set[str]] = {}
    for lin in lineages:
        product_to_reactants.setdefault(
            lin.product_participant_id, set()
        ).add(lin.reactant_participant_id)
    for product_pid, reactants in product_to_reactants.items():
        if len(reactants) > 1:
            return (
                f"strict_precondition_failed: forbidden pairing — transformed "
                f"product {product_pid!r} claimed by multiple transformed "
                f"reactants {sorted(reactants)} (no typed merge authority; "
                f"fail closed)"
            )

    # All preconditions hold.
    return None


def _classify_state(
    reaction_evidence: ReactionEvidence,
    ledger: SourceReactionLedger | None,
    lineages: list[ResolvedTransformedLineage],
) -> tuple[str, str | None]:
    """Classify the evidence into one of the 8 matrix states.

    Returns ``(state_name, strict_detail)``. ``strict_detail`` is None except
    when the engine fail-closes a fully_balanced record AWAY from strict
    because a strict precondition (§4.2) failed — then it carries the typed
    failure reason used as the decision ``reason``.

    Priority is fail-closed (§15.4): the most severe applicable condition
    wins. Missing fields (None ledger, empty lineages, unknown direction)
    NEVER default to eligible — they route to quarantine or strict_prohibited.

    Critical-2 (§4.2): step 8 grants strict_eligible ONLY after
    ``_validate_strict_preconditions`` passes. A fully_balanced ledger with
    incomplete source/mapping, missing mapping_report, MCS/center-pair
    fallback, or unknown lineage participant fail-closes to
    ``unknown_changed_heavy_atom_source`` (strict_prohibited / diagnostic).
    """
    # -- 0. Explicit ReactionEvidence.quarantine (quarantine) --
    # R4-11: an upstream curator flag is the most severe signal and must never
    # be overridden to strict by a self-reported balanced ledger. Route to
    # quarantine with a token-bearing reason.
    if reaction_evidence.quarantine:
        return (
            _STATE_CRITICAL_CONTRADICTION,
            f"explicit_evidence_quarantine: {reaction_evidence.quarantine}",
        )

    # -- 1. Critical element/charge contradiction (quarantine) --
    # Fail-closed: ledger is None → cannot verify balance → quarantine.
    if ledger is None:
        return (_STATE_CRITICAL_CONTRADICTION, None)
    if ledger.charge_balance != 0:
        return (_STATE_CRITICAL_CONTRADICTION, None)

    # R4-04: an explicit element_balance that contradicts conservation (non-zero
    # delta, delta inconsistent with counts, or duplicate element rows) is a
    # scientific contradiction the balanced status silently hides → quarantine.
    eb_contradiction = _element_balance_contradiction(ledger)
    if eb_contradiction is not None:
        return (_STATE_CRITICAL_CONTRADICTION, eb_contradiction)

    # -- 2. Lineage ambiguity affecting identity (strict_prohibited) --
    # Fail-closed: empty lineages → cannot verify identity → strict_prohibited.
    if not lineages:
        return (_STATE_LINEAGE_AMBIGUITY, None)
    has_critical_lineage = any(
        lin.ambiguity == "critical" for lin in lineages
    )
    if has_critical_lineage:
        return (_STATE_LINEAGE_AMBIGUITY, None)

    # -- 3. Reaction direction unknown (strict_prohibited) --
    direction = reaction_evidence.direction
    if not direction or direction == "unknown":
        return (_STATE_DIRECTION_UNKNOWN, None)

    # -- 4. Unknown changed heavy atom source (strict_prohibited) --
    has_unknown_source = any(
        s.source_participant_id == "unknown_source"
        for s in ledger.added_atom_sources
    )
    if has_unknown_source:
        return (_STATE_UNKNOWN_ATOM_SOURCE, None)

    # -- 5. Role ambiguity not affecting lineage (conditional) --
    # Lineages are resolved (no critical ambiguity), but at least one
    # participant has role=unknown. The ambiguity is local to roles.
    has_role_ambiguity = any(
        ra.role == ParticipantRole.unknown for ra in ledger.role_assignments
    )
    if has_role_ambiguity:
        return (_STATE_ROLE_AMBIGUITY, None)

    # -- 6. Missing noncritical cofactor stoichiometry (conditional) --
    # Cofactor changes are present, but the direction is unknown (gap in
    # noncritical cofactor stoichiometry). Heavy atoms are balanced.
    if ledger.cofactor_changes:
        has_cofactor_stoich_gap = any(
            cc.direction == "unknown" for cc in ledger.cofactor_changes
        )
        if has_cofactor_stoich_gap:
            return (_STATE_MISSING_COFACTOR, None)

    # -- 7. Heavy atom balanced with implicit H/e (conditional) --
    if ledger.balance_status == LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy:
        return (_STATE_HEAVY_ATOM_IMPLICIT, None)

    # -- 8. Fully balanced + reliable mapping (strict_eligible) --
    # Critical-2 §4.2: before granting strict, validate ALL cross-invariants
    # (source/mapping completeness, mapping_report, fallback_method,
    # assignment_method, changed_atom_coverage, lineage participant refs,
    # cross-lineage pairing). Any failure fail-closes to strict_prohibited
    # (diagnostic) — never strict.
    if ledger.balance_status == LedgerBalanceStatus.fully_balanced_explicit_reaction:
        # Round 5 §8.2: ONLY a fully_balanced ledger additionally requires
        # delta == 0 for every ElementBalance — a non-zero delta silently
        # contradicts the balanced status → quarantine. (A partial/unbalanced
        # ledger with a CONSISTENT non-zero delta is NOT this contradiction,
        # R5-11.)
        for eb in ledger.element_balance:
            if eb.delta != 0:
                return (
                    _STATE_CRITICAL_CONTRADICTION,
                    f"element_balance_contradiction: element {eb.element!r} has "
                    f"non-zero delta={eb.delta} in a fully_balanced ledger",
                )
        precondition_failure = _validate_strict_preconditions(
            reaction_evidence, ledger, lineages,
        )
        if precondition_failure is not None:
            return (_STATE_UNKNOWN_ATOM_SOURCE, precondition_failure)
        return (_STATE_FULLY_BALANCED, None)

    # -- Fail-closed default (§15.4) --
    # balance_status is partial_or_unbalanced but none of the specific severe
    # conditions above matched (e.g. source/mapping incomplete, formal
    # assignment ambiguous). Cannot confirm strict eligibility → fail-closed
    # to unknown_changed_heavy_atom_source (not strict eligible). Round 5
    # §8.3: a partial ledger must NOT be quarantined with a misleading
    # "fully-balanced" reason — it carries an honest partial reason instead.
    if ledger.balance_status == LedgerBalanceStatus.partial_or_unbalanced_source:
        return (
            _STATE_UNKNOWN_ATOM_SOURCE,
            f"partial_or_unbalanced_source: ledger balance_status="
            f"{ledger.balance_status.value} — partial/unbalanced source cannot "
            f"verify full balance (fail closed, never strict)",
        )
    return (_STATE_UNKNOWN_ATOM_SOURCE, None)


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
    state, strict_detail = _classify_state(reaction_evidence, ledger, lineages)
    row = get_row(state)

    # The matrix row is the authority — the engine maps its fields to the
    # EligibilityDecision. No second set of eligibility strings is introduced.
    reason = _build_reason(state, reaction_evidence, ledger, lineages)
    # Critical-2: if the engine fail-closed a fully_balanced record away from
    # strict due to a precondition failure (§4.2), use the typed failure
    # reason — more informative than the generic unknown_atom_source reason.
    if strict_detail:
        reason = strict_detail
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
        required_warnings=list(row.required_warnings),
        research_diagnostic_eligibility=row.research_or_diagnostic_eligibility,
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
