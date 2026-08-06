"""P1 Round 5 — complete ledger participant/map reference integrity + element
balance + map-uniqueness-from-content + lineage canonical duplicate + public
snapshot boundary (§7–§10 of CHATGPT_P1_REMEDIATION_PROMPT_ROUND_5.md).

Every negative test starts from the GENUINELY strict baseline
(``test_reference_integrity_valid_strict_baseline_is_strict`` proves it), then
perturbs EXACTLY ONE target condition, asserts the decision is no longer
strict (or routes to the correct lane), and asserts an invariant-specific
reason token so the failure cannot be an unrelated blocker (§11.6).

These tests are RED against the Round-4 engine (they currently return
``strict_eligible`` / wrong lane) and GREEN after the Round-5 fail-closed
implementation. The public-snapshot boundary tests read the REAL generated
``records.jsonl`` lane — they cannot be satisfied by only fixing the direct
``decide_eligibility`` helper (§6.2).
"""
from __future__ import annotations

import json
import os

import pytest

from reaction_agent.config import BuildConfig
from reaction_agent.eligibility.engine import decide_eligibility
from reaction_agent.schemas.common import (
    EligibilityStatus,
    LedgerBalanceStatus,
    LineageResolutionQuality,
    MappingQualityClass,
    MappingStatus,
    ParticipantRole,
    SourceAssignmentMethod,
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
from reaction_agent.schemas.mapping import (
    FormalMappedAtomPair,
    FormalSourceAssignment,
    MappingReport,
)
from reaction_agent.schemas.p1_entities import ResolvedTransformedLineage
from reaction_agent.snapshot.builder import (
    SnapshotEvidenceItem,
    build_snapshot,
)

_STRICT = EligibilityStatus.strict_eligible
_QUAR = EligibilityStatus.quarantine


# =====================================================================
# Fixture helpers (self-contained, mirror cross-invariants conventions)
# =====================================================================

def _participant(
    pid: str,
    side: str,
    smiles: str = "CC",
    atom_map_numbers: list[int] | None = None,
    mapped_fraction: float = 1.0,
) -> ReactionParticipant:
    # R7-01B: the default baseline is GENUINELY fully mapped — CC has exactly
    # 2 heavy atoms and the default map list [1,2] has exactly 2 unique IDs.
    return ReactionParticipant(
        participant_id=pid,
        molecule_id=f"mol_{pid}",
        canonical_smiles=smiles,
        side=side,
        atom_map_numbers=atom_map_numbers if atom_map_numbers is not None else [1, 2],
        mapped_fraction=mapped_fraction,
        changed_atom_fraction=0.0,
        provenance=[f"prov_{pid}"],
    )


def _pair(r_pid: str, r_map: int, p_pid: str, p_map: int) -> FormalMappedAtomPair:
    return FormalMappedAtomPair(
        reactant_participant_id=r_pid,
        reactant_atom_map=r_map,
        product_participant_id=p_pid,
        product_atom_map=p_map,
    )


def _mapping_report(
    pairs: list[FormalMappedAtomPair] | None = None,
) -> MappingReport:
    if pairs is None:
        pairs = [_pair("r1", 1, "p1", 1), _pair("r1", 2, "p1", 2)]
    return MappingReport(
        mapper_name="fake_mapper",
        mapper_version="v1",
        mapper_parameters={"timeout": "30"},
        input_hash="inp_abc",
        output_hash="out_def",
        mapping_status=MappingStatus.fully_mapped,
        mapped_heavy_atom_fraction=1.0,
        map_number_uniqueness=True,
        changed_atom_coverage=1.0,
        formal_mapped_source_assignment=FormalSourceAssignment(
            mapper_name="fake_mapper",
            mapper_version="v1",
            mapped_atom_pairs=pairs,
            assignment_method=SourceAssignmentMethod.formal_mapped,
            assignment_quality=MappingQualityClass.high_quality,
            assignment_ambiguity=False,
        ),
        fallback_method=None,
    )


def _ledger(
    reaction_id: str = "rxn_ri_001",
    *,
    balance_status: LedgerBalanceStatus = LedgerBalanceStatus.fully_balanced_explicit_reaction,
    roles: list[RoleAssignment] | None = None,
    element_balance: list[ElementBalance] | None = None,
    added_atom_sources: list[AddedAtomSource] | None = None,
    removed_atom_sinks: list[RemovedAtomSink] | None = None,
    reactant_entries: list[StoichiometricEntry] | None = None,
    product_entries: list[StoichiometricEntry] | None = None,
    stoichiometry: list[StoichiometricEntry] | None = None,
    cofactor_changes: list[CofactorChange] | None = None,
    mechanistic_origin_evidence: list[MechanisticOriginEvidence] | None = None,
    formal_atom_transfer_assignments: list[FormalAtomTransferAssignment] | None = None,
) -> SourceReactionLedger:
    if roles is None:
        roles = [
            RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
            RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_product, score=0.9),
        ]
    return SourceReactionLedger(
        ledger_id=f"srl_{reaction_id}",
        reaction_evidence_id=reaction_id,
        balance_status=balance_status,
        charge_balance=0,
        role_assignments=roles,
        element_balance=element_balance or [],
        added_atom_sources=added_atom_sources or [],
        removed_atom_sinks=removed_atom_sinks or [],
        reactant_entries=reactant_entries or [],
        product_entries=product_entries or [],
        stoichiometry=stoichiometry or [],
        cofactor_changes=cofactor_changes or [],
        mechanistic_origin_evidence=mechanistic_origin_evidence or [],
        formal_atom_transfer_assignments=formal_atom_transfer_assignments or [],
        unknowns=[],
        hydrogen_policy="explicit",
        proton_policy="explicit",
        electron_policy="explicit",
        source_completeness="complete",
        mapping_completeness="complete",
    )


def _lineage(
    *,
    lineage_id: str = "lin_r1_p1",
    reactant: str = "r1",
    product: str = "p1",
    atom_maps: list[int] | None = None,
) -> ResolvedTransformedLineage:
    return ResolvedTransformedLineage(
        lineage_id=lineage_id,
        reactant_participant_id=reactant,
        product_participant_id=product,
        ambiguity="none",
        resolution_quality=LineageResolutionQuality.resolved,
        transformed_atom_maps=atom_maps if atom_maps is not None else [1, 2],
        evidence_ids=["lin_ev_1"],
    )


def _evidence(
    *,
    reaction_id: str = "rxn_ri_001",
    participants: list[ReactionParticipant] | None = None,
    mapping_report: MappingReport | None = None,
    resolved_transformed_lineages: list[str] | None = None,
    direction: str = "forward",
) -> ReactionEvidence:
    if participants is None:
        # R7-01B: genuine fully-mapped baseline — CC (2 heavy atoms) with
        # exactly 2 maps on each side (see _participant).
        participants = [
            _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
            _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
        ]
    return ReactionEvidence(
        reaction_id=reaction_id,
        source_record_id=f"src_{reaction_id}",
        source_name="fixture_source_a",
        source_version="v1",
        raw_reaction="CC>>CC",
        normalized_reaction="CC>>CC",
        direction=direction,
        participants=participants,
        mapping_report=mapping_report if mapping_report is not None else _mapping_report(),
        resolved_transformed_lineages=resolved_transformed_lineages or [],
        provenance=["rxn_prov_a"],
    )


def _decide(evidence, ledger, lineages):
    return decide_eligibility(evidence, ledger, lineages)


def _config(tmp_path) -> BuildConfig:
    return BuildConfig(
        input_source="fixture_source_a",
        output_snapshot_root=str(tmp_path / "snapshots"),
        mapper_backend="fake",
        mapper_version="p1-1",
        mapper_parameters={},
        normalization_version="p1-1",
        role_policy_version="p1-1",
        lineage_resolver_version="p1-1",
        ledger_version="p1-1",
        eligibility_policy_version="p1-1",
        random_seed=42,
    )


def _build_lanes(tmp_path, items) -> dict:
    """Build a snapshot and return an index-aware public boundary (R7-05).

    Reads records.jsonl lanes AND the real production/diagnostic/quarantine
    indexes, so a record whose records lane is non-strict but which is wrongly
    present in the production index (index-only leakage) is visible to the
    tests. Returns:

    {
        "record_lanes": {reaction_id: lane},
        "production_ids": set(...),
        "diagnostic_ids": set(...),
        "quarantine_ids": set(...),
    }
    """
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter(items))
    snap_dir = os.path.join(config.output_snapshot_root, manifest.snapshot_id)
    record_lanes: dict[str, str] = {}
    production_ids: set[str] = set()
    diagnostic_ids: set[str] = set()
    quarantine_ids: set[str] = set()

    def _read_ids(fname: str) -> set[str]:
        ids: set[str] = set()
        with open(os.path.join(snap_dir, fname), encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                ids.add(rec["reaction_evidence"]["reaction_id"])
        return ids

    production_ids = _read_ids("production_index.jsonl")
    diagnostic_ids = _read_ids("diagnostic_index.jsonl")
    quarantine_ids = _read_ids("quarantine_index.jsonl")
    with open(os.path.join(snap_dir, "records.jsonl"), encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            record_lanes[rec["reaction_evidence"]["reaction_id"]] = rec["lane"]
    return {
        "record_lanes": record_lanes,
        "production_ids": production_ids,
        "diagnostic_ids": diagnostic_ids,
        "quarantine_ids": quarantine_ids,
    }


def _boundary_lane(boundary: dict, rid: str) -> str:
    return boundary["record_lanes"][rid]


def _assert_public_negative(
    boundary: dict,
    rid: str,
    *,
    expected_index: str = "diagnostic",
) -> None:
    """R7-05: a public negative must satisfy the FULL boundary:
    records lane != strict; NOT in production; present in the expected
    diagnostic/quarantine index; absent from the other incompatible index."""
    assert boundary["record_lanes"][rid] != "strict", (
        f"record {rid} reached the strict lane: {boundary['record_lanes'][rid]}"
    )
    assert rid not in boundary["production_ids"], (
        f"record {rid} leaked into the production index (index-only leakage)"
    )
    if expected_index == "diagnostic":
        assert rid in boundary["diagnostic_ids"], (
            f"record {rid} not in diagnostic index"
        )
        assert rid not in boundary["quarantine_ids"], (
            f"record {rid} wrongly in quarantine index"
        )
    elif expected_index == "quarantine":
        assert rid in boundary["quarantine_ids"], (
            f"record {rid} not in quarantine index"
        )
        assert rid not in boundary["diagnostic_ids"], (
            f"record {rid} wrongly in diagnostic index"
        )
    else:
        raise AssertionError(f"unknown expected_index {expected_index}")


def _assert_public_strict(boundary: dict, rid: str) -> None:
    """R7-05: a public positive strict record must satisfy the FULL boundary:
    records lane == strict; IN production; NOT in diagnostic/quarantine."""
    assert boundary["record_lanes"][rid] == "strict", (
        f"record {rid} is not in the strict lane: {boundary['record_lanes'][rid]}"
    )
    assert rid in boundary["production_ids"], (
        f"record {rid} missing from the production index"
    )
    assert rid not in boundary["diagnostic_ids"], (
        f"record {rid} wrongly in diagnostic index"
    )
    assert rid not in boundary["quarantine_ids"], (
        f"record {rid} wrongly in quarantine index"
    )


# =====================================================================
# Positive baseline — the fixture is a GENUINE strict-valid object (§11.6 #8)
# =====================================================================

def test_reference_integrity_valid_strict_baseline_is_strict():
    """The unmutated fixture (participants r1/p1, full formal pairs, resolved
    lineage, fully-balanced ledger) MUST be strict — so every negative mutation
    below is meaningful and the fix does NOT simply reject everything."""
    decision = _decide(_evidence(), _ledger(), [_lineage()])
    assert decision.eligibility == _STRICT, (
        f"valid strict baseline must be strict_eligible, got "
        f"{decision.eligibility}: {decision.reason}"
    )


def test_reactant_product_matching_map_number_remains_valid():
    """Positive protection (§7.1/§9.3): reactant r1 and product p1 may BOTH
    use formal map numbers 1,2 because the formal mapping connects the two
    sides. This must remain strict — never mistaken for a same-side collision."""
    decision = _decide(_evidence(), _ledger(), [_lineage()])
    assert decision.eligibility == _STRICT, (
        "reactant/product sharing formal map numbers must remain valid strict, "
        f"got {decision.eligibility}: {decision.reason}"
    )


# =====================================================================
# §7.6 AddedAtomSource — participant exists but map/evidence invalid
# =====================================================================

def test_added_atom_source_existing_participant_unknown_map_never_strict():
    """R5-01: source_participant_id='r1' EXISTS but atom_map_number=999 does
    not belong to it → must never be strict."""
    aas = [AddedAtomSource(atom_map_number=999, source_participant_id="r1")]
    decision = _decide(_evidence(), _ledger(added_atom_sources=aas), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "AddedAtomSource with existing participant but unknown map must NOT be strict"
    )
    assert "added_atom_source_map" in decision.reason, decision.reason


def test_added_atom_mechanistic_evidence_id_must_resolve():
    """R5-§7.6: AddedAtomSource.mechanistic_evidence_id non-empty must resolve
    to an existing MechanisticOriginEvidence.evidence_id."""
    aas = [AddedAtomSource(
        atom_map_number=1, source_participant_id="r1",
        mechanistic_evidence_id="mech_nonexistent")]
    decision = _decide(_evidence(), _ledger(added_atom_sources=aas), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "AddedAtomSource with a dangling mechanistic_evidence_id must NOT be strict"
    )
    assert "added_atom_source_evidence" in decision.reason, decision.reason


# =====================================================================
# §7.2 Reactant/Product entries — ghost participant / wrong side
# =====================================================================

def test_reactant_entry_ghost_participant_never_strict():
    """R5-02: reactant_entries[] references a ghost participant."""
    entries = [StoichiometricEntry(participant_id="ghost_r", coefficient=1, side="reactant")]
    decision = _decide(_evidence(), _ledger(reactant_entries=entries), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "reactant_entries referencing a ghost participant must NOT be strict"
    )
    assert "reactant_entry_ghost" in decision.reason, decision.reason


def test_product_entry_ghost_participant_never_strict():
    """R5-03: product_entries[] references a ghost participant."""
    entries = [StoichiometricEntry(participant_id="ghost_p", coefficient=1, side="product")]
    decision = _decide(_evidence(), _ledger(product_entries=entries), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "product_entries referencing a ghost participant must NOT be strict"
    )
    assert "product_entry_ghost" in decision.reason, decision.reason


def test_reactant_entry_wrong_side_never_strict():
    """R5-§7.2: reactant entry whose participant is product-side."""
    entries = [StoichiometricEntry(participant_id="p1", coefficient=1, side="reactant")]
    decision = _decide(_evidence(), _ledger(reactant_entries=entries), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "reactant_entry with a product-side participant must NOT be strict"
    )
    assert "reactant_entry_side" in decision.reason, decision.reason


def test_product_entry_wrong_side_never_strict():
    """R5-§7.2: product entry whose participant is reactant-side."""
    entries = [StoichiometricEntry(participant_id="r1", coefficient=1, side="product")]
    decision = _decide(_evidence(), _ledger(product_entries=entries), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "product_entry with a reactant-side participant must NOT be strict"
    )
    assert "product_entry_side" in decision.reason, decision.reason


# =====================================================================
# §7.3 Stoichiometry — side / coefficient
# =====================================================================

def test_stoichiometry_existing_participant_wrong_side_never_strict():
    """R5-04: stoichiometry references REAL r1 but side wrongly written
    product."""
    stoich = [StoichiometricEntry(participant_id="r1", coefficient=1, side="product")]
    decision = _decide(_evidence(), _ledger(stoichiometry=stoich), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "stoichiometry entry whose side disagrees with participant side must NOT be strict"
    )
    assert "stoichiometry_side" in decision.reason, decision.reason


def test_negative_stoichiometric_coefficient_never_strict():
    """R5-05: stoichiometric coefficient=-2."""
    stoich = [StoichiometricEntry(participant_id="r1", coefficient=-2, side="reactant")]
    decision = _decide(_evidence(), _ledger(stoichiometry=stoich), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "a negative stoichiometric coefficient must NOT be strict (§8.4)"
    )
    assert "stoichiometry_coefficient" in decision.reason, decision.reason


# =====================================================================
# §7.8 FormalAtomTransferAssignment — sides / maps / formal-pair conflict
# =====================================================================

def test_formal_transfer_existing_participants_wrong_sides_never_strict():
    """R5-06: source/target participants EXIST but sides reversed (source is a
    product, target is a reactant) and map=999."""
    fat = [FormalAtomTransferAssignment(
        source_participant_id="p1", target_participant_id="r1",
        transferred_atom_map_numbers=[999])]
    decision = _decide(
        _evidence(), _ledger(formal_atom_transfer_assignments=fat), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "FormalAtomTransferAssignment with reversed source/target sides must NOT be strict"
    )
    assert "formal_atom_transfer_side" in decision.reason, decision.reason


def test_formal_transfer_unknown_map_never_strict():
    """R5-§7.8: correct sides but transferred map not in source participant."""
    fat = [FormalAtomTransferAssignment(
        source_participant_id="r1", target_participant_id="p1",
        transferred_atom_map_numbers=[999])]
    decision = _decide(
        _evidence(), _ledger(formal_atom_transfer_assignments=fat), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "FormalAtomTransferAssignment with an unknown transferred map must NOT be strict"
    )
    assert "formal_atom_transfer_map" in decision.reason, decision.reason


def test_formal_transfer_conflicts_with_formal_pairs_never_strict():
    """R5-§7.8: source map exists but is NOT supported by a formal mapped pair
    on the source→target edge."""
    # Formal pairs support the lineage r1→p2 ([1,2]); the FAT claims r1→p1
    # transfers map 1, but the formal r1→p1 edge carries NO reactant maps.
    # p1 (the FAT target) declares no atom maps and is a ZERO-heavy-atom proton
    # so the ONLY defect is the FAT/formal-pair conflict (Round 6 heavy-atom
    # empty-map check must not fire first). r1/p2 are CC (2 heavy atoms, 2 maps).
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("p1", "product", "[H+]", atom_map_numbers=[]),
        _participant("p2", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    mr = _mapping_report(pairs=[_pair("r1", 1, "p2", 1), _pair("r1", 2, "p2", 2)])
    fat = [FormalAtomTransferAssignment(
        source_participant_id="r1", target_participant_id="p1",
        transferred_atom_map_numbers=[1])]
    roles = [
        RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
        RoleAssignment(participant_id="p2", role=ParticipantRole.transformed_product, score=0.9),
    ]
    decision = _decide(
        _evidence(participants=participants, mapping_report=mr),
        _ledger(roles=roles, formal_atom_transfer_assignments=fat),
        [_lineage(product="p2")])
    assert decision.eligibility != _STRICT, (
        "FormalAtomTransferAssignment conflicting with formal mapped pairs must NOT be strict"
    )
    assert "formal_atom_transfer_pair" in decision.reason, decision.reason


# =====================================================================
# §7.7 RemovedAtomSink — ghost participant / map
# =====================================================================

def test_removed_atom_sink_ghost_participant_never_strict():
    """R5-07: RemovedAtomSink references a ghost participant."""
    sinks = [RemovedAtomSink(atom_map_number=1, sink_participant_id="ghost_sink")]
    decision = _decide(_evidence(), _ledger(removed_atom_sinks=sinks), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "RemovedAtomSink referencing a ghost participant must NOT be strict"
    )
    assert "removed_atom_sink_ghost" in decision.reason, decision.reason


def test_removed_atom_sink_unknown_map_never_strict():
    """R5-§7.7: sink participant exists but atom map not in its registry."""
    sinks = [RemovedAtomSink(atom_map_number=999, sink_participant_id="p1")]
    decision = _decide(_evidence(), _ledger(removed_atom_sinks=sinks), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "RemovedAtomSink with an unknown atom map must NOT be strict"
    )
    assert "removed_atom_sink_map" in decision.reason, decision.reason


# =====================================================================
# §7.5 CofactorChange — ghost participant
# =====================================================================

def test_cofactor_change_ghost_participant_never_strict():
    """R5-08: CofactorChange references a ghost participant."""
    changes = [CofactorChange(participant_id="ghost_cof", direction="oxidized")]
    decision = _decide(_evidence(), _ledger(cofactor_changes=changes), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "CofactorChange referencing a ghost participant must NOT be strict"
    )
    assert "cofactor_change_ghost" in decision.reason, decision.reason


# =====================================================================
# §7.9 MechanisticOriginEvidence — ghost participant / map / evidence linkage
# =====================================================================

def test_mechanistic_evidence_ghost_participant_never_strict():
    """R5-09: MechanisticOriginEvidence references a ghost source participant."""
    mech = [MechanisticOriginEvidence(
        evidence_id="mech_1", evidence_type="isotope_tracing",
        source_participant_id="ghost_mech", target_atom_map_numbers=[1])]
    decision = _decide(_evidence(), _ledger(mechanistic_origin_evidence=mech), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "MechanisticOriginEvidence with a ghost source participant must NOT be strict"
    )
    assert "mechanistic_evidence_ghost" in decision.reason, decision.reason


def test_mechanistic_evidence_unknown_target_map_never_strict():
    """R5-§7.9: target_atom_map_numbers cannot resolve in the map registry."""
    mech = [MechanisticOriginEvidence(
        evidence_id="mech_1", evidence_type="isotope_tracing",
        source_participant_id="r1", target_atom_map_numbers=[999])]
    decision = _decide(_evidence(), _ledger(mechanistic_origin_evidence=mech), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "MechanisticOriginEvidence with an unknown target map must NOT be strict"
    )
    assert "mechanistic_evidence_map" in decision.reason, decision.reason


# =====================================================================
# §7.4 Role assignments — contradictions / side-lineage consistency
# =====================================================================

def test_contradictory_role_assignments_never_strict():
    """R5-14: the SAME participant carries two mutually contradictory
    authoritative role assignments."""
    roles = [
        RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
        RoleAssignment(participant_id="r1", role=ParticipantRole.cofactor, score=0.9),
        RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_product, score=0.9),
    ]
    decision = _decide(_evidence(), _ledger(roles=roles), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "contradictory role assignments on one participant must NOT be strict"
    )
    assert "role_assignment_conflict" in decision.reason, decision.reason


# =====================================================================
# §8 Element balance — negative counts / delta consistency / partial semantics
# =====================================================================

def test_negative_element_reactant_count_never_strict():
    """R5-10: reactant_count negative → internal contradiction."""
    eb = [ElementBalance(element="C", reactant_count=-1, product_count=1, delta=2)]
    decision = _decide(_evidence(), _ledger(element_balance=eb), [_lineage()])
    assert decision.eligibility == _QUAR, (
        "a negative element reactant_count is an internal data contradiction"
    )
    assert "element_balance_contradiction" in decision.reason, decision.reason
    assert "reactant_count" in decision.reason, decision.reason


def test_negative_element_product_count_never_strict():
    """R5-§8.1: product_count negative → internal contradiction."""
    eb = [ElementBalance(element="C", reactant_count=1, product_count=-1, delta=-2)]
    decision = _decide(_evidence(), _ledger(element_balance=eb), [_lineage()])
    assert decision.eligibility == _QUAR, (
        "a negative element product_count is an internal data contradiction"
    )
    assert "element_balance_contradiction" in decision.reason, decision.reason
    assert "product_count" in decision.reason, decision.reason


def test_element_delta_must_equal_product_minus_reactant():
    """R5-§8.1: delta must equal product_count - reactant_count for every
    ledger (structural consistency, independent of balance_status)."""
    eb = [ElementBalance(element="C", reactant_count=2, product_count=2, delta=5)]
    decision = _decide(_evidence(), _ledger(element_balance=eb), [_lineage()])
    assert decision.eligibility == _QUAR, (
        "an ElementBalance whose delta contradicts its counts is a structural "
        "contradiction and must be quarantined"
    )
    assert "element_balance_contradiction" in decision.reason, decision.reason


def test_fully_balanced_nonzero_delta_routes_to_quarantine():
    """R5-§8.2: fully_balanced ledger with non-zero delta → quarantine
    (the balanced status silently hides the imbalance)."""
    eb = [ElementBalance(element="C", reactant_count=2, product_count=3, delta=1)]
    decision = _decide(_evidence(), _ledger(element_balance=eb), [_lineage()])
    assert decision.eligibility == _QUAR, (
        "a fully_balanced ledger with a non-zero element delta must be quarantined"
    )
    assert "element_balance_contradiction" in decision.reason, decision.reason


def test_partial_consistent_nonzero_delta_not_mislabeled_quarantine():
    """R5-11: partial_or_unbalanced ledger with a CONSISTENT non-zero delta
    (delta == product-reactant) is NOT a 'fully-balanced contradiction' — it
    must NOT be quarantined with a reason that claims fully-balanced."""
    eb = [ElementBalance(element="C", reactant_count=2, product_count=3, delta=1)]
    decision = _decide(
        _evidence(),
        _ledger(balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
                element_balance=eb),
        [_lineage()])
    assert decision.eligibility != _QUAR, (
        "a partial ledger with a consistent non-zero delta must NOT be quarantined "
        "as a fully-balanced contradiction"
    )
    assert "fully_balanced" not in decision.reason, decision.reason


def test_partial_consistent_nonzero_delta_never_strict():
    """R5-§8.3: a partial ledger with consistent non-zero delta must never be
    strict — it fails closed to strict_prohibited."""
    eb = [ElementBalance(element="C", reactant_count=2, product_count=3, delta=1)]
    decision = _decide(
        _evidence(),
        _ledger(balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
                element_balance=eb),
        [_lineage()])
    assert decision.eligibility != _STRICT, (
        "a partial/unbalanced ledger must never be strict"
    )


# =====================================================================
# §9 Participant/map registry — uniqueness derived from content
# =====================================================================

def test_duplicate_participant_id_never_strict():
    """R5-§7.1/§9: two participants share the same participant_id."""
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("r1", "reactant", "CC", atom_map_numbers=[3, 4]),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    decision = _decide(_evidence(participants=participants), _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "duplicate participant_id must NOT be strict"
    )
    assert "participant_duplicate_id" in decision.reason, decision.reason


def test_uncontrolled_participant_side_never_strict():
    """R5-13: a participant with side='middle' (outside the controlled
    {reactant, product} vocabulary) and empty maps must NOT be strict."""
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("m1", "middle", "CCC", atom_map_numbers=[]),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    decision = _decide(_evidence(participants=participants), _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "an uncontrolled participant side must NOT be strict"
    )
    assert "participant_side" in decision.reason, decision.reason


def test_duplicate_atom_map_within_participant_never_strict():
    """R5-12: participant.atom_map_numbers=[1,1,2] — internal duplicate even
    though MappingReport self-reports map_number_uniqueness=True."""
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 1, 2]),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    decision = _decide(_evidence(participants=participants), _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "a participant declaring duplicate atom map numbers must NOT be strict "
        "(self-reported uniqueness cannot override content)"
    )
    assert "participant_map_duplicate" in decision.reason, decision.reason


def test_same_side_cross_participant_atom_map_collision_never_strict():
    """R5-§9.2: reactant r1 and reactant r2 both declare atom map 1 on the SAME
    side — a same-side collision the summary can hide."""
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("r2", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    mr = _mapping_report(pairs=[_pair("r1", 1, "p1", 1)])
    decision = _decide(
        _evidence(participants=participants, mapping_report=mr),
        _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "two same-side participants declaring the same atom map must NOT be strict"
    )
    assert "participant_map_collision" in decision.reason, decision.reason


# =====================================================================
# §10 Lineage canonical duplicate — embedded IDs / reordered maps / internal dup
# =====================================================================

def test_duplicate_embedded_lineage_ids_never_strict():
    """R5-15: embedded resolved_transformed_lineages contains a duplicate ID,
    but the set matches the external lineage IDs."""
    evidence = _evidence(resolved_transformed_lineages=["lin_r1_p1", "lin_r1_p1"])
    decision = _decide(evidence, _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "duplicate embedded lineage IDs must NOT be strict (must check raw list "
        "before set comparison)"
    )
    assert "embedded_lineage_duplicate" in decision.reason, decision.reason


def test_duplicate_lineage_content_with_reordered_maps_never_strict():
    """R5-16: same edge/maps, only map order [1,2] vs [2,1] — a semantic
    duplicate under set semantics that the tuple-order signature misses."""
    lineages = [
        _lineage(lineage_id="lin_r1_p1", atom_maps=[1, 2]),
        _lineage(lineage_id="lin_r1_p1_b", atom_maps=[2, 1]),
    ]
    decision = _decide(_evidence(), _ledger(), lineages)
    assert decision.eligibility != _STRICT, (
        "reordered-map semantic duplicate lineages must NOT be strict"
    )
    assert "duplicate_lineage" in decision.reason, decision.reason


def test_duplicate_transformed_maps_within_lineage_never_strict():
    """R5-§10.3: a single lineage's transformed_atom_maps contain an internal
    duplicate."""
    lineages = [_lineage(atom_maps=[1, 1, 2])]
    decision = _decide(_evidence(), _ledger(), lineages)
    assert decision.eligibility != _STRICT, (
        "a lineage with duplicate transformed atom maps must NOT be strict"
    )
    assert "lineage_map_duplicate" in decision.reason, decision.reason


# =====================================================================
# §6.2 Public snapshot boundary — records.jsonl lane cannot be strict
# =====================================================================

def test_public_snapshot_cannot_promote_added_atom_unknown_map(tmp_path):
    """R5-01 through the public API: AddedAtomSource with an existing
    participant but unknown map must NOT land in the strict lane."""
    aas = [AddedAtomSource(atom_map_number=999, source_participant_id="r1")]
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_aas"),
        _ledger("rxn_pub_aas", added_atom_sources=aas),
        [_lineage()],
    )
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_aas")


def test_public_snapshot_cannot_promote_ledger_ghost_entry(tmp_path):
    """R5-02 through the public API: reactant_entries ghost participant must
    NOT land in the strict lane."""
    entries = [StoichiometricEntry(participant_id="ghost_r", coefficient=1, side="reactant")]
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_ghost"),
        _ledger("rxn_pub_ghost", reactant_entries=entries),
        [_lineage()],
    )
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_ghost")


def test_public_snapshot_cannot_promote_formal_transfer_map_conflict(tmp_path):
    """R5-06 through the public API: a reversed-side FAT with map=999 must NOT
    land in the strict lane."""
    fat = [FormalAtomTransferAssignment(
        source_participant_id="p1", target_participant_id="r1",
        transferred_atom_map_numbers=[999])]
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_fat"),
        _ledger("rxn_pub_fat", formal_atom_transfer_assignments=fat),
        [_lineage()],
    )
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_fat")


def test_public_snapshot_cannot_promote_duplicate_participant_map(tmp_path):
    """R5-12 through the public API: a participant with duplicate atom maps
    must NOT land in the strict lane."""
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 1, 2]),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_map", participants=participants),
        _ledger("rxn_pub_map"),
        [_lineage()],
    )
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_map")


def test_public_snapshot_cannot_promote_embedded_duplicate_lineage(tmp_path):
    """R5-15 through the public API: embedded duplicate lineage IDs must NOT
    land in the strict lane."""
    evidence = _evidence(
        reaction_id="rxn_pub_lin",
        resolved_transformed_lineages=["lin_r1_p1", "lin_r1_p1"],
    )
    item = SnapshotEvidenceItem(evidence, _ledger("rxn_pub_lin"), [_lineage()])
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_lin")


# =====================================================================
# Round 6 (§6–§11) — confirmed strict fail-opens from ChatGPT independent
# replication. Each is RED against the Round-5 engine (strict_eligible) and
# GREEN after the Round-6 fail-closed implementation.
# =====================================================================

# ---------------------------------------------------------------------
# §6 R6-01: CofactorChange.direction must be controlled
# ---------------------------------------------------------------------

def test_uncontrolled_cofactor_direction_never_strict():
    """R6-01: an existing cofactor participant with direction='sideways'
    (no frozen authority) must never be strict."""
    changes = [CofactorChange(participant_id="r1", direction="sideways")]
    decision = _decide(_evidence(), _ledger(cofactor_changes=changes), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "an uncontrolled cofactor direction must NOT be strict"
    )
    assert "cofactor_change_direction" in decision.reason, decision.reason


def test_unknown_cofactor_direction_remains_conditional():
    """R6-01 positive: direction='unknown' keeps the existing conditional
    policy (missing_noncritical_cofactor_stoich), never strict."""
    changes = [CofactorChange(participant_id="r1", direction="unknown")]
    decision = _decide(_evidence(), _ledger(cofactor_changes=changes), [_lineage()])
    assert decision.eligibility == EligibilityStatus.conditional_eligible, (
        "an unknown cofactor direction must route to conditional, got "
        f"{decision.eligibility}"
    )


def test_public_snapshot_cannot_promote_uncontrolled_cofactor_direction(tmp_path):
    """R6-01 public boundary: an uncontrolled cofactor direction must NOT land
    in the strict lane via the public build API."""
    changes = [CofactorChange(participant_id="r1", direction="sideways")]
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_cof"),
        _ledger("rxn_pub_cof", cofactor_changes=changes),
        [_lineage()],
    )
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_cof")


# ---------------------------------------------------------------------
# §7 R6-02: duplicate/conflicting stoichiometric authority
# ---------------------------------------------------------------------

def test_duplicate_reactant_entry_never_strict():
    """R6-02: two IDENTICAL reactant entries must not silently double-count."""
    entries = [
        StoichiometricEntry(participant_id="r1", coefficient=1, side="reactant"),
        StoichiometricEntry(participant_id="r1", coefficient=1, side="reactant"),
    ]
    decision = _decide(_evidence(), _ledger(reactant_entries=entries), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "duplicate reactant entries must NOT be strict"
    )
    assert "reactant_entry_duplicate" in decision.reason, decision.reason


def test_conflicting_reactant_entry_coefficients_never_strict():
    """R6-02: same reactant entry participant with coefficients 1 and 2."""
    entries = [
        StoichiometricEntry(participant_id="r1", coefficient=1, side="reactant"),
        StoichiometricEntry(participant_id="r1", coefficient=2, side="reactant"),
    ]
    decision = _decide(_evidence(), _ledger(reactant_entries=entries), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "conflicting reactant entry coefficients must NOT be strict"
    )
    assert "reactant_entry_conflict" in decision.reason, decision.reason


def test_duplicate_product_entry_never_strict():
    """R6-02: two IDENTICAL product entries must not silently double-count."""
    entries = [
        StoichiometricEntry(participant_id="p1", coefficient=1, side="product"),
        StoichiometricEntry(participant_id="p1", coefficient=1, side="product"),
    ]
    decision = _decide(_evidence(), _ledger(product_entries=entries), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "duplicate product entries must NOT be strict"
    )
    assert "product_entry_duplicate" in decision.reason, decision.reason


def test_conflicting_product_entry_coefficients_never_strict():
    """R6-02: same product entry participant with coefficients 1 and 2."""
    entries = [
        StoichiometricEntry(participant_id="p1", coefficient=1, side="product"),
        StoichiometricEntry(participant_id="p1", coefficient=2, side="product"),
    ]
    decision = _decide(_evidence(), _ledger(product_entries=entries), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "conflicting product entry coefficients must NOT be strict"
    )
    assert "product_entry_conflict" in decision.reason, decision.reason


def test_duplicate_stoichiometry_entry_never_strict():
    """R6-02: two IDENTICAL stoichiometry entries must not silently
    double-count."""
    stoich = [
        StoichiometricEntry(participant_id="r1", coefficient=1, side="reactant"),
        StoichiometricEntry(participant_id="r1", coefficient=1, side="reactant"),
    ]
    decision = _decide(_evidence(), _ledger(stoichiometry=stoich), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "duplicate stoichiometry entries must NOT be strict"
    )
    assert "stoichiometry_duplicate" in decision.reason, decision.reason


def test_conflicting_stoichiometry_coefficients_never_strict():
    """R6-02: same stoichiometry participant/side with coefficients 1 and 2."""
    stoich = [
        StoichiometricEntry(participant_id="r1", coefficient=1, side="reactant"),
        StoichiometricEntry(participant_id="r1", coefficient=2, side="reactant"),
    ]
    decision = _decide(_evidence(), _ledger(stoichiometry=stoich), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "conflicting stoichiometry coefficients must NOT be strict"
    )
    assert "stoichiometry_conflict" in decision.reason, decision.reason


def test_public_snapshot_cannot_promote_conflicting_reactant_entries(tmp_path):
    """R6-02 public boundary: conflicting reactant entries must NOT land in
    the strict lane."""
    entries = [
        StoichiometricEntry(participant_id="r1", coefficient=1, side="reactant"),
        StoichiometricEntry(participant_id="r1", coefficient=2, side="reactant"),
    ]
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_rent"),
        _ledger("rxn_pub_rent", reactant_entries=entries),
        [_lineage()],
    )
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_rent")


def test_public_snapshot_cannot_promote_conflicting_stoichiometry(tmp_path):
    """R6-02 public boundary: conflicting stoichiometry must NOT land in the
    strict lane."""
    stoich = [
        StoichiometricEntry(participant_id="r1", coefficient=1, side="reactant"),
        StoichiometricEntry(participant_id="r1", coefficient=2, side="reactant"),
    ]
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_stoich"),
        _ledger("rxn_pub_stoich", stoichiometry=stoich),
        [_lineage()],
    )
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_stoich")


# ---------------------------------------------------------------------
# §8 R6-03: mechanistic target must resolve via product map registry
# ---------------------------------------------------------------------

def _r6_03_evidence():
    """r1 maps [1,2,3] / p1 maps [1,2,4] / pairs r1:1→p1:1, r1:2→p1:2,
    r1:3→p1:4 / lineage transformed maps [1,2,3]. Baseline is strict; map 3
    exists ONLY on the reactant side. r1=CCO (3 heavy, 3 maps) and p1=CCN
    (3 heavy, 3 maps) are both heavy-atom consistent."""
    participants = [
        _participant("r1", "reactant", "CCO", atom_map_numbers=[1, 2, 3]),
        _participant("p1", "product", "CCN", atom_map_numbers=[1, 2, 4]),
    ]
    mr = _mapping_report(pairs=[
        _pair("r1", 1, "p1", 1), _pair("r1", 2, "p1", 2), _pair("r1", 3, "p1", 4),
    ])
    return _evidence(participants=participants, mapping_report=mr), \
        _lineage(atom_maps=[1, 2, 3])


def test_mechanistic_target_map_must_exist_on_product_side():
    """R6-03: mechanistic target map 3 exists only on the reactant side — it
    cannot be accepted as a product atom target."""
    ev, lin = _r6_03_evidence()
    mech = [MechanisticOriginEvidence(
        evidence_id="me_r_only", evidence_type="isotope_tracing",
        source_participant_id="r1", target_atom_map_numbers=[3])]
    decision = _decide(ev, _ledger(mechanistic_origin_evidence=mech), [lin])
    assert decision.eligibility != _STRICT, (
        "a mechanistic target map present only on the reactant side must NOT "
        "be strict"
    )
    assert "mechanistic_evidence_map" in decision.reason, decision.reason


def test_mechanistic_target_product_map_remains_valid():
    """R6-03 positive: a mechanistic target map that IS a product map must not
    be rejected by an all-reject fix."""
    ev, lin = _r6_03_evidence()
    mech = [MechanisticOriginEvidence(
        evidence_id="me_ok", evidence_type="isotope_tracing",
        source_participant_id="r1", target_atom_map_numbers=[1])]
    decision = _decide(ev, _ledger(mechanistic_origin_evidence=mech), [lin])
    assert decision.eligibility == _STRICT, (
        "a mechanistic target that resolves on the product side must remain "
        f"strict, got {decision.eligibility}: {decision.reason}"
    )


def test_public_snapshot_cannot_promote_reactant_only_mechanistic_target_map(tmp_path):
    """R6-03 public boundary: a reactant-only mechanistic target map must NOT
    land in the strict lane."""
    ev, lin = _r6_03_evidence()
    ev.reaction_id = "rxn_pub_mech"
    mech = [MechanisticOriginEvidence(
        evidence_id="me_r_only", evidence_type="isotope_tracing",
        source_participant_id="r1", target_atom_map_numbers=[3])]
    item = SnapshotEvidenceItem(
        ev, _ledger("rxn_pub_mech", mechanistic_origin_evidence=mech), [lin])
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_mech")


# ---------------------------------------------------------------------
# §9 R6-04: FormalAtomTransferAssignment must not be a shell
# ---------------------------------------------------------------------

def test_empty_formal_transfer_maps_never_strict():
    """R6-04: a FAT with empty transferred_atom_map_numbers must not pass via
    vacuous truth."""
    fat = [FormalAtomTransferAssignment(
        source_participant_id="r1", target_participant_id="p1")]
    decision = _decide(_evidence(), _ledger(formal_atom_transfer_assignments=fat), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "a formal atom transfer assignment with no transferred maps must NOT "
        "be strict"
    )
    assert "formal_atom_transfer_empty" in decision.reason, decision.reason


def test_duplicate_formal_transfer_maps_never_strict():
    """R6-04: a FAT with duplicate transferred maps must not be strict."""
    fat = [FormalAtomTransferAssignment(
        source_participant_id="r1", target_participant_id="p1",
        transferred_atom_map_numbers=[1, 1])]
    decision = _decide(_evidence(), _ledger(formal_atom_transfer_assignments=fat), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "a formal atom transfer assignment with duplicate transferred maps "
        "must NOT be strict"
    )
    assert "formal_atom_transfer_duplicate_map" in decision.reason, decision.reason


def test_valid_nonempty_formal_transfer_remains_strict():
    """R6-04 positive: a NON-EMPTY FAT supported by the formal edge must not
    be rejected by an all-reject fix."""
    fat = [FormalAtomTransferAssignment(
        source_participant_id="r1", target_participant_id="p1",
        transferred_atom_map_numbers=[1])]
    decision = _decide(_evidence(), _ledger(formal_atom_transfer_assignments=fat), [_lineage()])
    assert decision.eligibility == _STRICT, (
        "a valid non-empty formal atom transfer must remain strict, got "
        f"{decision.eligibility}: {decision.reason}"
    )


def test_public_snapshot_cannot_promote_empty_formal_transfer(tmp_path):
    """R6-04 public boundary: an empty FAT must NOT land in the strict lane."""
    fat = [FormalAtomTransferAssignment(
        source_participant_id="r1", target_participant_id="p1")]
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_fat_empty"),
        _ledger("rxn_pub_fat_empty", formal_atom_transfer_assignments=fat),
        [_lineage()],
    )
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_fat_empty")


# ---------------------------------------------------------------------
# §10 R6-05: heavy-atom participant must not self-report full mapping
# ---------------------------------------------------------------------

def _heavy_atom_empty_map_evidence(reaction_id="rxn_r605"):
    """Strict baseline PLUS an extra heavy-atom reactant x1 (CC) with EMPTY
    atom maps and mapped_fraction=1.0. The baseline r1/p1 are CC (2 heavy atoms,
    2 maps) so the ONLY defect is x1's empty heavy-atom map evidence."""
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("x1", "reactant", "CC", atom_map_numbers=[], mapped_fraction=1.0),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    ev = _evidence(reaction_id=reaction_id, participants=participants)
    return ev, _ledger(reaction_id)


def test_heavy_atom_participant_with_empty_maps_never_strict():
    """R6-05: a parseable heavy-atom participant (CCO) with empty atom maps
    and mapped_fraction=1.0 must never be strict."""
    ev, ld = _heavy_atom_empty_map_evidence()
    decision = _decide(ev, ld, [_lineage()])
    assert decision.eligibility != _STRICT, (
        "a heavy-atom participant with no atom map evidence must NOT be strict"
    )
    assert "participant_heavy_atom_map_evidence" in decision.reason, decision.reason


def test_mapped_fraction_one_cannot_override_empty_heavy_atom_maps():
    """R6-05: mapped_fraction=1.0 (self-report) cannot override the absence of
    verifiable heavy-atom map evidence."""
    ev, ld = _heavy_atom_empty_map_evidence(reaction_id="rxn_r605b")
    decision = _decide(ev, ld, [_lineage()])
    assert decision.eligibility != _STRICT, (
        "mapped_fraction=1.0 must not override empty heavy-atom maps"
    )
    assert "participant_heavy_atom_map_evidence" in decision.reason, decision.reason


def test_valid_fully_mapped_heavy_atom_participant_remains_strict():
    """R6-05 positive: a fully-mapped heavy-atom participant (CCO with maps)
    must remain strict — the fix must NOT reject all participants."""
    decision = _decide(_evidence(), _ledger(), [_lineage()])
    assert decision.eligibility == _STRICT, (
        "a valid fully-mapped heavy-atom participant must remain strict, got "
        f"{decision.eligibility}: {decision.reason}"
    )


def test_zero_heavy_atom_policy_does_not_get_accidentally_broken():
    """R6-05 positive: a zero-heavy-atom participant (proton [H+]) with no
    maps must NOT be rejected — the proton/electron policy stays intact."""
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("h1", "reactant", "[H+]", atom_map_numbers=[]),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    decision = _decide(_evidence(participants=participants), _ledger(), [_lineage()])
    assert decision.eligibility == _STRICT, (
        "a zero-heavy-atom participant must not break strict eligibility, got "
        f"{decision.eligibility}: {decision.reason}"
    )


def test_public_snapshot_cannot_promote_unmapped_heavy_atom_participant(tmp_path):
    """R6-05 public boundary: an unmapped heavy-atom participant must NOT land
    in the strict lane."""
    ev, ld = _heavy_atom_empty_map_evidence(reaction_id="rxn_pub_ha")
    item = SnapshotEvidenceItem(ev, ld, [_lineage()])
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_ha")


# ---------------------------------------------------------------------
# §11 extra shell-evidence risks
# ---------------------------------------------------------------------

def test_nonformal_added_atom_source_without_mechanism_never_strict():
    """§11.1: an AddedAtomSource that is not formally assigned AND has no
    mechanistic evidence backing it must not be strict."""
    aas = [AddedAtomSource(
        atom_map_number=1, source_participant_id="r1",
        formal_assignment=False, mechanistic_evidence_id=None)]
    decision = _decide(_evidence(), _ledger(added_atom_sources=aas), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "a non-formal, mechanism-less AddedAtomSource must NOT be strict "
        "(unproven atom source)"
    )
    assert "added_atom_source_unbacked" in decision.reason, decision.reason


def test_empty_mechanistic_target_maps_never_strict():
    """§11.2: a MechanisticOriginEvidence that targets no atom must not be a
    strict mechanism authority by vacuous truth."""
    mech = [MechanisticOriginEvidence(
        evidence_id="me_empty", evidence_type="isotope_tracing",
        source_participant_id="r1", target_atom_map_numbers=[])]
    decision = _decide(_evidence(), _ledger(mechanistic_origin_evidence=mech), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "a mechanistic evidence with no target maps must NOT be strict"
    )
    assert "mechanistic_evidence_empty_target" in decision.reason, decision.reason


# =====================================================================
# Round 7 (§5–§10) — strict mapping/ledger/public-index science boundary.
# R7-01 heavy-atom map count vs fully-mapped claim
# R7-02 positive atom-map identifiers
# R7-03 collection-level duplicate/conflict ledger evidence
# R7-04 unbacked RemovedAtomSink
# R7-05 index-aware public boundary (records + production/diagnostic/quarantine)
# =====================================================================

def _assert_reference_baseline_strict():
    """RED-quality guard (§12 #2/#3/#4): the unmutated baseline must be a
    genuine strict-valid object whose participant maps are heavy-atom-count
    consistent and strictly positive — otherwise every negative mutation below
    would be vacuous or caught by an unrelated precondition."""
    ev = _evidence()
    d = _decide(ev, _ledger(), [_lineage()])
    assert d.eligibility == _STRICT, (
        f"baseline not strict: {d.eligibility}: {d.reason}"
    )
    for p in ev.participants:
        maps = list(p.atom_map_numbers)
        assert maps, f"baseline participant {p.participant_id} has no maps"
        assert all(isinstance(m, int) and m > 0 for m in maps), (
            f"baseline participant {p.participant_id} has non-positive map IDs {maps}"
        )


# ---------------------------------------------------------------------
# R7-01 (§5): heavy-atom map count must match the fully-mapped claim
# ---------------------------------------------------------------------

def test_genuinely_fully_mapped_heavy_atom_participant_remains_strict():
    """R7-01B positive: the rebuilt baseline (CC + [1,2] on both sides) is a
    GENUINE fully-mapped participant — 2 heavy atoms, 2 unique maps — and must
    remain strict. This is the positive protection that proves the fix does not
    reject all participants."""
    _assert_reference_baseline_strict()


def test_zero_heavy_atom_proton_policy_remains_valid():
    """R7-01 §5.5 positive: [H+] (zero heavy atoms, no maps) must not be
    rejected — the proton policy stays intact. A zero-heavy-atom participant
    must NOT carry heavy-atom maps either (overflow) but may carry none."""
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("h1", "reactant", "[H+]", atom_map_numbers=[]),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    decision = _decide(_evidence(participants=participants), _ledger(), [_lineage()])
    assert decision.eligibility == _STRICT, (
        "a zero-heavy-atom proton must remain valid, got "
        f"{decision.eligibility}: {decision.reason}"
    )


def test_heavy_atom_map_count_underflow_never_strict():
    """R7-01a: CC declares only ONE map (unique count 1 != heavy count 2) while
    self-reporting mapped_fraction=1.0 → must never be strict."""
    _assert_reference_baseline_strict()
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1]),
        _participant("p1", "product", "CC", atom_map_numbers=[1]),
    ]
    ev = _evidence(participants=participants)
    ev.mapping_report = _mapping_report(pairs=[_pair("r1", 1, "p1", 1)])
    lineages = [_lineage(atom_maps=[1])]
    decision = _decide(ev, _ledger(), lineages)
    assert decision.eligibility != _STRICT, (
        "heavy-atom map-count underflow must NOT be strict"
    )
    assert "participant_heavy_atom_map_count" in decision.reason, decision.reason


def test_heavy_atom_map_count_overflow_never_strict():
    """R7-01b: C declares TWO maps (unique count 2 != heavy count 1) while
    self-reporting mapped_fraction=1.0 → must never be strict."""
    _assert_reference_baseline_strict()
    participants = [
        _participant("r1", "reactant", "C", atom_map_numbers=[1, 2]),
        _participant("p1", "product", "C", atom_map_numbers=[1, 2]),
    ]
    ev = _evidence(participants=participants)
    ev.mapping_report = _mapping_report(pairs=[
        _pair("r1", 1, "p1", 1), _pair("r1", 2, "p1", 2)])
    lineages = [_lineage(atom_maps=[1, 2])]
    decision = _decide(ev, _ledger(), lineages)
    assert decision.eligibility != _STRICT, (
        "heavy-atom map-count overflow must NOT be strict"
    )
    assert "participant_heavy_atom_map_count" in decision.reason, decision.reason


def test_mapped_fraction_one_cannot_override_map_count_underflow():
    """R7-01: a participant mapped_fraction=1.0 cannot override an atom-map
    count that underflows its molecule's heavy-atom count."""
    _assert_reference_baseline_strict()
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1], mapped_fraction=1.0),
        _participant("p1", "product", "CC", atom_map_numbers=[1], mapped_fraction=1.0),
    ]
    ev = _evidence(participants=participants)
    ev.mapping_report = _mapping_report(pairs=[_pair("r1", 1, "p1", 1)])
    lineages = [_lineage(atom_maps=[1])]
    decision = _decide(ev, _ledger(), lineages)
    assert decision.eligibility != _STRICT, (
        "mapped_fraction=1.0 must not override map-count underflow"
    )
    assert "participant_heavy_atom_map_count" in decision.reason, decision.reason


def test_global_mapped_fraction_one_cannot_override_participant_count_mismatch():
    """R7-01: the global MappingReport mapped_heavy_atom_fraction=1.0 cannot
    override a participant-level map-count contradiction."""
    _assert_reference_baseline_strict()
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1]),
        _participant("p1", "product", "CC", atom_map_numbers=[1]),
    ]
    ev = _evidence(participants=participants)
    ev.mapping_report = _mapping_report(pairs=[_pair("r1", 1, "p1", 1)])
    lineages = [_lineage(atom_maps=[1])]
    decision = _decide(ev, _ledger(), lineages)
    assert decision.eligibility != _STRICT, (
        "global mapped_heavy_atom_fraction=1.0 must not override participant "
        "map-count mismatch"
    )
    assert "participant_heavy_atom_map_count" in decision.reason, decision.reason


def test_public_snapshot_cannot_promote_heavy_map_count_underflow(tmp_path):
    """R7-01 public: an underflow participant must not reach the strict lane nor
    the production index (R7-05 index-aware boundary)."""
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1]),
        _participant("p1", "product", "CC", atom_map_numbers=[1]),
    ]
    ev = _evidence(reaction_id="rxn_pub_uflow", participants=participants)
    ev.mapping_report = _mapping_report(pairs=[_pair("r1", 1, "p1", 1)])
    item = SnapshotEvidenceItem(ev, _ledger("rxn_pub_uflow"), [_lineage(atom_maps=[1])])
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_uflow")


def test_public_snapshot_cannot_promote_heavy_map_count_overflow(tmp_path):
    """R7-01 public: an overflow participant must not reach the strict lane nor
    the production index (R7-05 index-aware boundary)."""
    participants = [
        _participant("r1", "reactant", "C", atom_map_numbers=[1, 2]),
        _participant("p1", "product", "C", atom_map_numbers=[1, 2]),
    ]
    ev = _evidence(reaction_id="rxn_pub_oflow", participants=participants)
    ev.mapping_report = _mapping_report(pairs=[
        _pair("r1", 1, "p1", 1), _pair("r1", 2, "p1", 2)])
    item = SnapshotEvidenceItem(ev, _ledger("rxn_pub_oflow"), [_lineage(atom_maps=[1, 2])])
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_oflow")


# ---------------------------------------------------------------------
# R7-02 (§7): atom map identifiers must be strictly positive
# ---------------------------------------------------------------------

def test_positive_atom_map_identifiers_remain_strict():
    """R7-02 positive: the baseline uses strictly positive map IDs and must
    remain strict — the fix must not reject valid positive maps."""
    _assert_reference_baseline_strict()


def test_zero_atom_map_identifier_never_strict():
    """R7-02: an atom map identifier of 0 (not a valid positive integer) in a
    participant must never be strict."""
    _assert_reference_baseline_strict()
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[0, 1]),
        _participant("p1", "product", "CC", atom_map_numbers=[0, 1]),
    ]
    ev = _evidence(participants=participants)
    ev.mapping_report = _mapping_report(pairs=[
        _pair("r1", 0, "p1", 0), _pair("r1", 1, "p1", 1)])
    lineages = [_lineage(atom_maps=[0, 1])]
    decision = _decide(ev, _ledger(), lineages)
    assert decision.eligibility != _STRICT, (
        "a zero atom-map identifier must NOT be strict"
    )
    assert "participant_map_identifier" in decision.reason, decision.reason


def test_negative_atom_map_identifier_never_strict():
    """R7-02: a negative atom map identifier in a participant must never be
    strict."""
    _assert_reference_baseline_strict()
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[-1, 1]),
        _participant("p1", "product", "CC", atom_map_numbers=[-1, 1]),
    ]
    ev = _evidence(participants=participants)
    ev.mapping_report = _mapping_report(pairs=[
        _pair("r1", -1, "p1", -1), _pair("r1", 1, "p1", 1)])
    lineages = [_lineage(atom_maps=[-1, 1])]
    decision = _decide(ev, _ledger(), lineages)
    assert decision.eligibility != _STRICT, (
        "a negative atom-map identifier must NOT be strict"
    )
    assert "participant_map_identifier" in decision.reason, decision.reason


def test_nonpositive_formal_pair_map_never_strict():
    """R7-02: a formal mapped pair using a non-positive map declared by a
    participant cannot bypass the central participant-map authority."""
    _assert_reference_baseline_strict()
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[0, 1]),
        _participant("p1", "product", "CC", atom_map_numbers=[0, 1]),
    ]
    ev = _evidence(participants=participants)
    ev.mapping_report = _mapping_report(pairs=[
        _pair("r1", 0, "p1", 0), _pair("r1", 1, "p1", 1)])
    lineages = [_lineage(atom_maps=[0, 1])]
    decision = _decide(ev, _ledger(), lineages)
    assert decision.eligibility != _STRICT, (
        "a formal pair over a non-positive map must NOT be strict"
    )
    assert "participant_map_identifier" in decision.reason, decision.reason


def test_nonpositive_lineage_map_never_strict():
    """R7-02: a lineage over a non-positive map declared by a participant
    cannot bypass the central participant-map authority."""
    _assert_reference_baseline_strict()
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[0, 1]),
        _participant("p1", "product", "CC", atom_map_numbers=[0, 1]),
    ]
    ev = _evidence(participants=participants)
    ev.mapping_report = _mapping_report(pairs=[
        _pair("r1", 0, "p1", 0), _pair("r1", 1, "p1", 1)])
    lineages = [_lineage(atom_maps=[0, 1])]
    decision = _decide(ev, _ledger(), lineages)
    assert decision.eligibility != _STRICT, (
        "a lineage over a non-positive map must NOT be strict"
    )
    assert "participant_map_identifier" in decision.reason, decision.reason


def test_public_snapshot_cannot_promote_nonpositive_atom_maps(tmp_path):
    """R7-02 public: non-positive atom maps must not reach the strict lane nor
    the production index."""
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[-1, 0]),
        _participant("p1", "product", "CC", atom_map_numbers=[-1, 0]),
    ]
    ev = _evidence(reaction_id="rxn_pub_nonpos", participants=participants)
    ev.mapping_report = _mapping_report(pairs=[
        _pair("r1", -1, "p1", -1), _pair("r1", 0, "p1", 0)])
    item = SnapshotEvidenceItem(ev, _ledger("rxn_pub_nonpos"), [_lineage(atom_maps=[-1, 0])])
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_nonpos")


# ---------------------------------------------------------------------
# R7-03 (§8): collection-level duplicate/conflict ledger evidence
# ---------------------------------------------------------------------

def test_distinct_valid_ledger_evidence_remains_valid():
    """R7-03 positive: distinct, well-formed ledger evidence (one AddedAtomSource,
    one RemovedAtomSink, one FAT, one mechanistic evidence) must remain strict —
    the fix must not reject valid non-duplicate evidence."""
    _assert_reference_baseline_strict()
    aas = [AddedAtomSource(atom_map_number=1, source_participant_id="r1",
                           formal_assignment=True)]
    sink = [RemovedAtomSink(atom_map_number=1, sink_participant_id="r1",
                            formal_assignment=True)]
    fat = [FormalAtomTransferAssignment(source_participant_id="r1",
                                        target_participant_id="p1",
                                        transferred_atom_map_numbers=[1])]
    mech = [MechanisticOriginEvidence(evidence_id="me_ok",
                                      evidence_type="isotope_tracing",
                                      source_participant_id="r1",
                                      target_atom_map_numbers=[1])]
    decision = _decide(
        _evidence(),
        _ledger(added_atom_sources=aas, removed_atom_sinks=sink,
                formal_atom_transfer_assignments=fat,
                mechanistic_origin_evidence=mech),
        [_lineage()])
    assert decision.eligibility == _STRICT, (
        "distinct valid ledger evidence must remain strict, got "
        f"{decision.eligibility}: {decision.reason}"
    )


def test_duplicate_added_atom_source_never_strict():
    """R7-03a: the SAME AddedAtomSource object appearing twice (collection-level
    duplicate) must not be silently double-counted into strict."""
    _assert_reference_baseline_strict()
    src = AddedAtomSource(atom_map_number=1, source_participant_id="r1",
                          formal_assignment=True)
    decision = _decide(
        _evidence(), _ledger(added_atom_sources=[src, src]), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "duplicate AddedAtomSource must NOT be strict"
    )
    assert "added_atom_source_duplicate" in decision.reason, decision.reason


def test_conflicting_added_atom_sources_never_strict():
    """R7-03a: the same atom map claimed by two DIFFERENT added-atom sources
    (no typed ambiguity authority) must fail closed."""
    _assert_reference_baseline_strict()
    aas = [
        AddedAtomSource(atom_map_number=1, source_participant_id="r1",
                        formal_assignment=True),
        AddedAtomSource(atom_map_number=1, source_participant_id="p1",
                        formal_assignment=True),
    ]
    decision = _decide(
        _evidence(), _ledger(added_atom_sources=aas), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "conflicting added-atom sources must NOT be strict"
    )
    assert "added_atom_source_conflict" in decision.reason, decision.reason


def test_duplicate_removed_atom_sink_never_strict():
    """R7-03b: the SAME RemovedAtomSink object appearing twice must not be
    silently double-counted into strict."""
    _assert_reference_baseline_strict()
    sink = RemovedAtomSink(atom_map_number=1, sink_participant_id="r1",
                           formal_assignment=True)
    decision = _decide(
        _evidence(), _ledger(removed_atom_sinks=[sink, sink]), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "duplicate RemovedAtomSink must NOT be strict"
    )
    assert "removed_atom_sink_duplicate" in decision.reason, decision.reason


def test_conflicting_removed_atom_sinks_never_strict():
    """R7-03b: the same atom map claimed by two DIFFERENT removed-atom sinks
    (no typed ambiguity authority) must fail closed."""
    _assert_reference_baseline_strict()
    sinks = [
        RemovedAtomSink(atom_map_number=1, sink_participant_id="r1",
                        formal_assignment=True),
        RemovedAtomSink(atom_map_number=1, sink_participant_id="p1",
                        formal_assignment=True),
    ]
    decision = _decide(
        _evidence(), _ledger(removed_atom_sinks=sinks), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "conflicting removed-atom sinks must NOT be strict"
    )
    assert "removed_atom_sink_conflict" in decision.reason, decision.reason


def test_duplicate_formal_transfer_assignment_never_strict():
    """R7-03c: the SAME FormalAtomTransferAssignment object appearing twice
    must not be silently double-counted into strict."""
    _assert_reference_baseline_strict()
    fat = FormalAtomTransferAssignment(source_participant_id="r1",
                                       target_participant_id="p1",
                                       transferred_atom_map_numbers=[1])
    decision = _decide(
        _evidence(), _ledger(formal_atom_transfer_assignments=[fat, fat]),
        [_lineage()])
    assert decision.eligibility != _STRICT, (
        "duplicate formal transfer assignment must NOT be strict"
    )
    assert "formal_atom_transfer_duplicate_assignment" in decision.reason, decision.reason


def test_conflicting_formal_transfer_assignments_never_strict():
    """R7-03c: the same source atom map claimed by two DIFFERENT target edges
    of a FAT (no typed split authority) must fail closed."""
    _assert_reference_baseline_strict()
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
        _participant("p2", "product", "CC", atom_map_numbers=[3, 4]),
    ]
    ev = _evidence(participants=participants)
    fats = [
        FormalAtomTransferAssignment(source_participant_id="r1",
                                     target_participant_id="p1",
                                     transferred_atom_map_numbers=[1]),
        FormalAtomTransferAssignment(source_participant_id="r1",
                                     target_participant_id="p2",
                                     transferred_atom_map_numbers=[1]),
    ]
    decision = _decide(ev, _ledger(formal_atom_transfer_assignments=fats), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "conflicting formal transfer assignments must NOT be strict"
    )
    assert "formal_atom_transfer_assignment_conflict" in decision.reason, decision.reason


def test_duplicate_mechanistic_target_maps_never_strict():
    """R7-03d: a MechanisticOriginEvidence whose target_atom_map_numbers list
    contains an internal duplicate ([1,1]) must never be strict."""
    _assert_reference_baseline_strict()
    mech = [MechanisticOriginEvidence(evidence_id="me_dup",
                                      evidence_type="isotope_tracing",
                                      source_participant_id="r1",
                                      target_atom_map_numbers=[1, 1])]
    decision = _decide(
        _evidence(), _ledger(mechanistic_origin_evidence=mech), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "duplicate mechanistic target maps must NOT be strict"
    )
    assert "mechanistic_evidence_duplicate_target_map" in decision.reason, decision.reason


def test_public_snapshot_cannot_promote_duplicate_added_atom_source(tmp_path):
    """R7-03 public: duplicate AddedAtomSource must not reach the strict lane
    nor the production index."""
    src = AddedAtomSource(atom_map_number=1, source_participant_id="r1",
                          formal_assignment=True)
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_dupaas"),
        _ledger("rxn_pub_dupaas", added_atom_sources=[src, src]),
        [_lineage()])
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_dupaas")


def test_public_snapshot_cannot_promote_duplicate_removed_atom_sink(tmp_path):
    """R7-03 public: duplicate RemovedAtomSink must not reach the strict lane
    nor the production index."""
    sink = RemovedAtomSink(atom_map_number=1, sink_participant_id="r1",
                           formal_assignment=True)
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_dupsink"),
        _ledger("rxn_pub_dupsink", removed_atom_sinks=[sink, sink]),
        [_lineage()])
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_dupsink")


def test_public_snapshot_cannot_promote_duplicate_formal_transfer_assignment(tmp_path):
    """R7-03 public: duplicate FAT assignment must not reach the strict lane nor
    the production index."""
    fat = FormalAtomTransferAssignment(source_participant_id="r1",
                                       target_participant_id="p1",
                                       transferred_atom_map_numbers=[1])
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_dupfat"),
        _ledger("rxn_pub_dupfat", formal_atom_transfer_assignments=[fat, fat]),
        [_lineage()])
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_dupfat")


def test_public_snapshot_cannot_promote_duplicate_mechanistic_targets(tmp_path):
    """R7-03 public: duplicate mechanistic target maps must not reach the strict
    lane nor the production index."""
    mech = [MechanisticOriginEvidence(evidence_id="me_dup",
                                      evidence_type="isotope_tracing",
                                      source_participant_id="r1",
                                      target_atom_map_numbers=[1, 1])]
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_dupmech"),
        _ledger("rxn_pub_dupmech", mechanistic_origin_evidence=mech),
        [_lineage()])
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_dupmech")


# ---------------------------------------------------------------------
# R7-04 (§9): RemovedAtomSink non-formal without authority
# ---------------------------------------------------------------------

def test_formally_backed_removed_atom_sink_remains_valid():
    """R7-04 positive: a RemovedAtomSink with formal_assignment=True must remain
    strict — the fix must not reject formally backed sinks."""
    _assert_reference_baseline_strict()
    sink = [RemovedAtomSink(atom_map_number=1, sink_participant_id="r1",
                            formal_assignment=True)]
    decision = _decide(
        _evidence(), _ledger(removed_atom_sinks=sink), [_lineage()])
    assert decision.eligibility == _STRICT, (
        "a formally backed RemovedAtomSink must remain strict, got "
        f"{decision.eligibility}: {decision.reason}"
    )


def test_nonformal_removed_atom_sink_without_authority_never_strict():
    """R7-04: a RemovedAtomSink with formal_assignment=False has NO other typed
    authority (the schema carries no mechanistic sink evidence) — it must never
    be strict."""
    _assert_reference_baseline_strict()
    sink = [RemovedAtomSink(atom_map_number=1, sink_participant_id="r1",
                            formal_assignment=False)]
    decision = _decide(
        _evidence(), _ledger(removed_atom_sinks=sink), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "an unbacked non-formal RemovedAtomSink must NOT be strict"
    )
    assert "removed_atom_sink_unbacked" in decision.reason, decision.reason


def test_public_snapshot_cannot_promote_unbacked_removed_atom_sink(tmp_path):
    """R7-04 public: an unbacked non-formal RemovedAtomSink must not reach the
    strict lane nor the production index."""
    sink = [RemovedAtomSink(atom_map_number=1, sink_participant_id="r1",
                            formal_assignment=False)]
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_unbacked"),
        _ledger("rxn_pub_unbacked", removed_atom_sinks=sink),
        [_lineage()])
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_pub_unbacked")


# ---------------------------------------------------------------------
# R7-05 (§10): index-aware public boundary — a public STRICT positive must
# prove production membership AND absence from diagnostic/quarantine.
# ---------------------------------------------------------------------

def test_public_snapshot_strict_positive_is_in_production_index(tmp_path):
    """R7-05 positive: a genuine strict record must be in the strict lane AND in
    the production index, and must NOT appear in diagnostic/quarantine."""
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_pub_strictpos"),
        _ledger("rxn_pub_strictpos"),
        [_lineage()])
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_strict(boundary, "rxn_pub_strictpos")
