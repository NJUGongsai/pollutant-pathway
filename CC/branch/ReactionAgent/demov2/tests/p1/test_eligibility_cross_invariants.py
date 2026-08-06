"""Critical-2 (§6) — unreliable / contradictory mapping & lineage must NEVER
enter ``strict_eligible`` (nor the strict production lane).

Round 2 shipped ``reaction_agent/eligibility/engine.py::
_validate_strict_preconditions`` which checked SOME state fields but NOT the
complete mapping/lineage cross-relationships. ChatGPT reproduced (§6.2) that
every one of the following schema-valid objects was still granted
``strict_eligible``:

    mapped_heavy_atom_fraction = 0.25
    formal assignment assignment_ambiguity = True
    formal pair referencing a non-existent reactant participant
    formal pair referencing an atom map (999999) absent from the participant
    lineage resolution_quality = unresolved
    lineage ambiguity = partial
    two reactants pointing at one transformed product (the 2OG→hydroxyproline
        class of error — the current ``cross = reactants & products`` check
        cannot see it, §6.3)

These tests are written FIRST (R3-T4). They are RED against the current engine
and GREEN after R3-T5. The positive baseline (``test_valid_strict_baseline_
is_strict``) proves the fixture is a genuine strict-valid object, so every
negative mutation is meaningful and the fix must NOT simply reject everything
(§6.7 — do not fossilise the wrong semantics in the fixture).

At least one test drives the PUBLIC API
(``SnapshotEvidenceItem → build_snapshot → production_index``) to prove the bad
object does not merely return non-strict from ``decide_eligibility`` but is
actually kept out of the strict production lane (§6.6).
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
    ElementBalance,
    FormalAtomTransferAssignment,
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
    SnapshotBuildError,
    SnapshotEvidenceItem,
    build_snapshot,
)

_STRICT = EligibilityStatus.strict_eligible


# =====================================================================
# Fixture helpers (self-contained)
# =====================================================================

def _participant(
    pid: str,
    side: str,
    smiles: str = "CC",
    atom_map_numbers: list[int] | None = None,
    mapped_fraction: float = 1.0,
) -> ReactionParticipant:
    # R7-01B: default baseline is GENUINELY fully mapped — CC (2 heavy atoms)
    # with exactly 2 unique map IDs [1,2].
    return ReactionParticipant(
        participant_id=pid,
        molecule_id=f"mol_{pid}",
        canonical_smiles=smiles,
        side=side,
        atom_map_numbers=atom_map_numbers or [1, 2],
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
    *,
    pairs: list[FormalMappedAtomPair] | None = None,
    mapped_heavy_atom_fraction: float = 1.0,
    changed_atom_coverage: float = 1.0,
    assignment_quality: MappingQualityClass = MappingQualityClass.high_quality,
    assignment_ambiguity: bool = False,
    assignment_method: SourceAssignmentMethod = SourceAssignmentMethod.formal_mapped,
    mapping_status: MappingStatus = MappingStatus.fully_mapped,
    fallback_method: str | None = None,
) -> MappingReport:
    if pairs is None:
        pairs = [_pair("r1", 1, "p1", 1), _pair("r1", 2, "p1", 2)]
    return MappingReport(
        mapper_name="fake_mapper",
        mapper_version="v1",
        mapper_parameters={"timeout": "30"},
        input_hash="inp_abc",
        output_hash="out_def",
        mapping_status=mapping_status,
        mapped_heavy_atom_fraction=mapped_heavy_atom_fraction,
        map_number_uniqueness=True,
        changed_atom_coverage=changed_atom_coverage,
        formal_mapped_source_assignment=FormalSourceAssignment(
            mapper_name="fake_mapper",
            mapper_version="v1",
            mapped_atom_pairs=pairs,
            assignment_method=assignment_method,
            assignment_quality=assignment_quality,
            assignment_ambiguity=assignment_ambiguity,
        ),
        fallback_method=fallback_method,
    )


def _ledger(
    reaction_id: str = "rxn_strict_001",
    *,
    balance_status: LedgerBalanceStatus = LedgerBalanceStatus.fully_balanced_explicit_reaction,
    charge_balance: int = 0,
    roles: list[RoleAssignment] | None = None,
    element_balance: list[ElementBalance] | None = None,
    added_atom_sources: list[AddedAtomSource] | None = None,
    stoichiometry: list[StoichiometricEntry] | None = None,
    formal_atom_transfer_assignments: list[FormalAtomTransferAssignment] | None = None,
    unknowns: list[str] | None = None,
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
        charge_balance=charge_balance,
        role_assignments=roles,
        element_balance=element_balance or [],
        added_atom_sources=added_atom_sources or [],
        stoichiometry=stoichiometry or [],
        formal_atom_transfer_assignments=formal_atom_transfer_assignments or [],
        unknowns=unknowns or [],
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
    resolution_quality: LineageResolutionQuality = LineageResolutionQuality.resolved,
    ambiguity: str = "none",
) -> ResolvedTransformedLineage:
    return ResolvedTransformedLineage(
        lineage_id=lineage_id,
        reactant_participant_id=reactant,
        product_participant_id=product,
        ambiguity=ambiguity,
        resolution_quality=resolution_quality,
        transformed_atom_maps=atom_maps if atom_maps is not None else [1, 2],
        evidence_ids=["lin_ev_1"],
    )


def _evidence(
    *,
    reaction_id: str = "rxn_strict_001",
    participants: list[ReactionParticipant] | None = None,
    mapping_report: MappingReport | None = None,
    direction: str = "forward",
    quarantine: str | None = None,
    ambiguity_sets: list[dict[str, str]] | None = None,
    resolved_transformed_lineages: list[str] | None = None,
) -> ReactionEvidence:
    if participants is None:
        # R7-01B: genuine fully-mapped baseline — CC (2 heavy atoms) with 2 maps.
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
        ambiguity_sets=ambiguity_sets or [],
        resolved_transformed_lineages=resolved_transformed_lineages or [],
        quarantine=quarantine,
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
    """Build a snapshot and return an index-aware public boundary (R7-05):
    records.jsonl lanes AND real production/diagnostic/quarantine index IDs."""
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


def _assert_public_negative(boundary: dict, rid: str, *,
                            expected_index: str = "diagnostic") -> None:
    """R7-05: records lane != strict; NOT in production; in the expected
    diagnostic/quarantine index; absent from the other incompatible index."""
    assert boundary["record_lanes"][rid] != "strict", (
        f"record {rid} reached the strict lane: {boundary['record_lanes'][rid]}"
    )
    assert rid not in boundary["production_ids"], (
        f"record {rid} leaked into the production index (index-only leakage)"
    )
    if expected_index == "diagnostic":
        assert rid in boundary["diagnostic_ids"], f"record {rid} not in diagnostic index"
        assert rid not in boundary["quarantine_ids"], f"record {rid} wrongly in quarantine index"
    elif expected_index == "quarantine":
        assert rid in boundary["quarantine_ids"], f"record {rid} not in quarantine index"
        assert rid not in boundary["diagnostic_ids"], f"record {rid} wrongly in diagnostic index"


# =====================================================================
# Positive baseline — the fixture is a GENUINE strict-valid object (§6.7)
# =====================================================================

def test_valid_strict_baseline_is_strict():
    """The unmutated fixture (resolved lineage, complete formal pairs,
    full coverage, high-quality unambiguous assignment) MUST be strict — so
    every negative mutation below is meaningful and the fix does not simply
    reject everything."""
    decision = _decide(_evidence(), _ledger(), [_lineage()])
    assert decision.eligibility == _STRICT, (
        f"valid strict baseline must be strict_eligible, got "
        f"{decision.eligibility}: {decision.reason}"
    )


# =====================================================================
# §6.4 MappingReport layer
# =====================================================================

def test_low_mapped_heavy_atom_fraction_never_strict():
    mr = _mapping_report(mapped_heavy_atom_fraction=0.25)
    decision = _decide(_evidence(mapping_report=mr), _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "mapped_heavy_atom_fraction=0.25 must NOT be strict "
        "(strict requires the frozen conservative threshold 1.0)"
    )


def test_ambiguous_formal_assignment_never_strict():
    mr = _mapping_report(assignment_ambiguity=True)
    decision = _decide(_evidence(mapping_report=mr), _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "assignment_ambiguity=True must NOT be strict"
    )


def test_low_quality_formal_assignment_never_strict():
    mr = _mapping_report(assignment_quality=MappingQualityClass.low_quality)
    decision = _decide(_evidence(mapping_report=mr), _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "assignment_quality=low_quality must NOT be strict"
    )


# =====================================================================
# §6.4 Formal mapped pairs layer
# =====================================================================

def test_formal_pair_unknown_reactant_participant_never_strict():
    mr = _mapping_report(pairs=[_pair("r_unknown", 1, "p1", 1), _pair("r1", 2, "p1", 2)])
    decision = _decide(_evidence(mapping_report=mr), _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "formal pair referencing a non-existent reactant participant must NOT be strict"
    )


def test_formal_pair_unknown_product_participant_never_strict():
    mr = _mapping_report(pairs=[_pair("r1", 1, "p_unknown", 1), _pair("r1", 2, "p1", 2)])
    decision = _decide(_evidence(mapping_report=mr), _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "formal pair referencing a non-existent product participant must NOT be strict"
    )


def test_formal_pair_wrong_participant_side_never_strict():
    # r1 is (wrongly) a product-side participant, yet used as a pair's reactant.
    participants = [
        _participant("r1", "product", "CC", atom_map_numbers=[1, 2]),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    mr = _mapping_report()  # pairs use r1 as reactant side
    decision = _decide(
        _evidence(participants=participants, mapping_report=mr),
        _ledger(), [_lineage()],
    )
    assert decision.eligibility != _STRICT, (
        "formal pair whose reactant participant has side!=reactant must NOT be strict"
    )


def test_formal_pair_unknown_reactant_atom_map_never_strict():
    mr = _mapping_report(pairs=[_pair("r1", 999999, "p1", 1), _pair("r1", 2, "p1", 2)])
    decision = _decide(_evidence(mapping_report=mr), _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "formal pair referencing an atom map absent from the reactant participant "
        "must NOT be strict"
    )


def test_formal_pair_unknown_product_atom_map_never_strict():
    mr = _mapping_report(pairs=[_pair("r1", 1, "p1", 999999), _pair("r1", 2, "p1", 2)])
    decision = _decide(_evidence(mapping_report=mr), _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "formal pair referencing an atom map absent from the product participant "
        "must NOT be strict"
    )


def test_contradictory_or_duplicate_mapping_pairs_never_strict():
    # reactant_atom_map 1 mapped to two contradictory product atom maps.
    mr = _mapping_report(pairs=[_pair("r1", 1, "p1", 1), _pair("r1", 1, "p1", 2)])
    decision = _decide(_evidence(mapping_report=mr), _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "contradictory mapping pairs (one reactant atom map → two product atom "
        "maps) must NOT be strict"
    )


# =====================================================================
# §6.4 Resolved lineage layer
# =====================================================================

def test_unresolved_lineage_never_strict():
    lin = _lineage(resolution_quality=LineageResolutionQuality.unresolved)
    decision = _decide(_evidence(), _ledger(), [lin])
    assert decision.eligibility != _STRICT, (
        "lineage resolution_quality=unresolved must NOT be strict"
    )


def test_failed_lineage_never_strict():
    lin = _lineage(resolution_quality=LineageResolutionQuality.failed)
    decision = _decide(_evidence(), _ledger(), [lin])
    assert decision.eligibility != _STRICT, (
        "lineage resolution_quality=failed must NOT be strict"
    )


def test_partially_resolved_lineage_never_strict():
    lin = _lineage(resolution_quality=LineageResolutionQuality.partially_resolved)
    decision = _decide(_evidence(), _ledger(), [lin])
    assert decision.eligibility != _STRICT, (
        "lineage resolution_quality=partially_resolved must NOT be strict"
    )


def test_partial_identity_ambiguity_never_strict():
    lin = _lineage(ambiguity="partial")
    decision = _decide(_evidence(), _ledger(), [lin])
    assert decision.eligibility != _STRICT, (
        "lineage ambiguity=partial must NOT be strict (no typed merge authority "
        "in the current schema to prove it does not affect identity)"
    )


def test_lineage_pair_must_be_supported_by_formal_mapping():
    # Lineage claims r1→p1, but the formal pairs only connect r1→p2.
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("p1", "product", "CC", atom_map_numbers=[3, 4]),
        _participant("p2", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    mr = _mapping_report(pairs=[_pair("r1", 1, "p2", 1), _pair("r1", 2, "p2", 2)])
    roles = [
        RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
        RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_product, score=0.9),
    ]
    decision = _decide(
        _evidence(participants=participants, mapping_report=mr),
        _ledger(roles=roles), [_lineage(reactant="r1", product="p1")],
    )
    assert decision.eligibility != _STRICT, (
        "a strict lineage pair not supported by any formal mapped pair must NOT be strict"
    )


def test_lineage_transformed_maps_must_be_supported_by_mapping():
    # Lineage transformed_atom_maps = [99] — not present in any mapped pair.
    lin = _lineage(atom_maps=[99])
    decision = _decide(_evidence(), _ledger(), [lin])
    assert decision.eligibility != _STRICT, (
        "lineage transformed_atom_maps not supported by valid mapped atoms must "
        "NOT be strict"
    )


def test_two_reactants_claiming_same_transformed_product_fail_closed():
    # r1→p1 AND r2→p1: two transformed reactants claim one product. The old
    # ``cross = reactants & products`` check (§6.3) cannot detect this.
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("r2", "reactant", "CC", atom_map_numbers=[3, 4]),
        _participant("p1", "product", "CCCC", atom_map_numbers=[1, 2, 3, 4]),
    ]
    mr = _mapping_report(pairs=[
        _pair("r1", 1, "p1", 1), _pair("r1", 2, "p1", 2),
        _pair("r2", 3, "p1", 3), _pair("r2", 4, "p1", 4),
    ])
    roles = [
        RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
        RoleAssignment(participant_id="r2", role=ParticipantRole.transformed_substrate, score=0.9),
        RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_product, score=0.9),
    ]
    lineages = [
        _lineage(lineage_id="lin_r1_p1", reactant="r1", product="p1", atom_maps=[1, 2]),
        _lineage(lineage_id="lin_r2_p1", reactant="r2", product="p1", atom_maps=[3, 4]),
    ]
    decision = _decide(
        _evidence(participants=participants, mapping_report=mr),
        _ledger(roles=roles), lineages,
    )
    assert decision.eligibility != _STRICT, (
        "two transformed reactants claiming one product (no typed merge "
        "authority) must fail closed — never strict"
    )


# =====================================================================
# §6.6 public API — a bad object must not reach the strict production lane
# =====================================================================

def test_forbidden_2og_to_hydroxyproline_cannot_enter_snapshot_strict(tmp_path):
    """Public API (SnapshotEvidenceItem → build_snapshot → records): the
    two-reactants→one-product object must NOT be written into the strict lane."""
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("r2", "reactant", "CC", atom_map_numbers=[3, 4]),
        _participant("p1", "product", "CCCC", atom_map_numbers=[1, 2, 3, 4]),
    ]
    mr = _mapping_report(pairs=[
        _pair("r1", 1, "p1", 1), _pair("r1", 2, "p1", 2),
        _pair("r2", 3, "p1", 3), _pair("r2", 4, "p1", 4),
    ])
    roles = [
        RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
        RoleAssignment(participant_id="r2", role=ParticipantRole.transformed_substrate, score=0.9),
        RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_product, score=0.9),
    ]
    lineages = [
        _lineage(lineage_id="lin_r1_p1", reactant="r1", product="p1", atom_maps=[1, 2]),
        _lineage(lineage_id="lin_r2_p1", reactant="r2", product="p1", atom_maps=[3, 4]),
    ]
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_2og", participants=participants, mapping_report=mr),
        _ledger("rxn_2og", roles=roles),
        lineages,
    )
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_2og")


def test_public_snapshot_api_cannot_bypass_new_cross_invariants(tmp_path):
    """An unresolved-lineage object routed through the public build API must
    not land in the strict lane."""
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_bad"),
        _ledger("rxn_bad"),
        [_lineage(resolution_quality=LineageResolutionQuality.unresolved)],
    )
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_bad")


# =====================================================================
# §6.4 embedded/external ledger consistency (enforced fail-closed at build)
# =====================================================================

def test_embedded_external_ledger_mismatch_never_strict(tmp_path):
    """A disagreeing embedded (ReactionEvidence.source_reaction_ledger) and
    external (SnapshotEvidenceItem.source_ledger) must fail the build closed —
    the object can never reach any lane, let alone strict (§5.4/§6.4)."""
    external = _ledger("rxn_mismatch")
    embedded = _ledger(
        "rxn_mismatch",
        balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        charge_balance=3,
    )
    evidence = _evidence(reaction_id="rxn_mismatch")
    evidence.source_reaction_ledger = embedded
    item = SnapshotEvidenceItem(evidence, external, [_lineage()])
    with pytest.raises(SnapshotBuildError):
        build_snapshot(_config(tmp_path), iter([item]))


# =====================================================================
# Round 4 (§6.1) — 14 confirmed strict fail-opens. Each is RED against the
# pre-R4 engine (it returns strict_eligible) and GREEN after the fix. Every
# test perturbs the proven strict baseline (test_valid_strict_baseline_is_strict)
# by exactly one target condition, so a non-strict result cannot be an
# accidental side effect of an unrelated baseline blocker (§8 requirement 5),
# and asserts a stable, invariant-specific reason token (§8 requirement 4).
# =====================================================================

_QUAR = EligibilityStatus.quarantine


# -- R4-01: participant mapped_fraction below the strict threshold --

def test_participant_low_mapped_fraction_never_strict():
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2], mapped_fraction=0.25),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    decision = _decide(_evidence(participants=participants), _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "a participant with mapped_fraction=0.25 must NOT be strict"
    )
    assert "participant_mapped_fraction" in decision.reason, decision.reason


# -- R4-02: self-reported full mapping but incomplete actual pair coverage --

def test_self_reported_full_mapping_with_incomplete_actual_pair_coverage_never_strict():
    # r1 declares atom maps [1, 2] but the formal pairs only cover map 1.
    # The MappingReport still self-reports mapped_heavy_atom_fraction=1.0 and
    # changed_atom_coverage=1.0. The lineage references only the covered map
    # so the ONLY defect is the uncovered participant atom map (§7.3.2).
    mr = _mapping_report(pairs=[_pair("r1", 1, "p1", 1)])
    lineages = [_lineage(atom_maps=[1])]
    decision = _decide(_evidence(mapping_report=mr), _ledger(), lineages)
    assert decision.eligibility != _STRICT, (
        "self-reported 1.0 mapping whose formal pairs do not cover every declared "
        "participant atom map must NOT be strict"
    )
    assert "participant_atom_map_uncovered" in decision.reason, decision.reason


# -- R4-03: reverse collision — two reactant atoms map to one product atom --

def test_reverse_collision_many_to_one_mapping_never_strict():
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    # r1:1 → p1:1 AND r1:2 → p1:1 (product atom target 1 occupied twice).
    mr = _mapping_report(pairs=[_pair("r1", 1, "p1", 1), _pair("r1", 2, "p1", 1)])
    lineages = [_lineage(atom_maps=[1, 2])]
    decision = _decide(_evidence(mapping_report=mr), _ledger(), lineages)
    assert decision.eligibility != _STRICT, (
        "two reactant atoms mapping to the same product atom (no typed merge "
        "authority) must fail closed — never strict"
    )
    assert "product_atom_target_collision" in decision.reason, decision.reason


# -- R4-04: element balance contradictions route to quarantine --

def test_nonzero_element_balance_never_strict():
    eb = [ElementBalance(element="C", reactant_count=2, product_count=3, delta=1)]
    decision = _decide(_evidence(), _ledger(element_balance=eb), [_lineage()])
    assert decision.eligibility == _QUAR, (
        "a fully_balanced ledger carrying a non-zero element delta is an explicit "
        "scientific contradiction and must be quarantined"
    )
    assert "element_balance_contradiction" in decision.reason, decision.reason


def test_element_delta_inconsistent_with_counts_never_strict():
    # delta (5) != product_count - reactant_count (0).
    eb = [ElementBalance(element="C", reactant_count=2, product_count=2, delta=5)]
    decision = _decide(_evidence(), _ledger(element_balance=eb), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "an ElementBalance whose delta contradicts its counts must NOT be strict"
    )
    assert "element_balance_contradiction" in decision.reason, decision.reason


def test_duplicate_element_balance_entry_never_strict():
    eb = [
        ElementBalance(element="C", reactant_count=2, product_count=2, delta=0),
        ElementBalance(element="C", reactant_count=3, product_count=3, delta=0),
    ]
    decision = _decide(_evidence(), _ledger(element_balance=eb), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "duplicate/conflicting ElementBalance entries for one element must NOT be strict"
    )
    assert "element_balance_contradiction" in decision.reason, decision.reason


# -- R4-05: AddedAtomSource ghost participant reference --

def test_added_atom_source_ghost_reference_never_strict():
    aas = [AddedAtomSource(atom_map_number=1, source_participant_id="ghost_participant")]
    decision = _decide(_evidence(), _ledger(added_atom_sources=aas), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "an AddedAtomSource referencing a participant not in the multiset must NOT "
        "be strict (a ghost string other than 'unknown_source' must not slip "
        "through)"
    )
    assert "added_atom_source_ghost" in decision.reason, decision.reason


# -- R4-06: RoleAssignment ghost participant --

def test_role_assignment_ghost_participant_never_strict():
    roles = [
        RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
        RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_product, score=0.9),
        RoleAssignment(participant_id="ghost", role=ParticipantRole.transformed_product, score=0.9),
    ]
    decision = _decide(_evidence(), _ledger(roles=roles), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "a RoleAssignment referencing a ghost participant must NOT be strict"
    )
    assert "role_assignment_ghost" in decision.reason, decision.reason


# -- R4-07: StoichiometricEntry ghost participant --

def test_stoichiometry_ghost_participant_never_strict():
    stoich = [StoichiometricEntry(participant_id="ghost", coefficient=1, side="reactant")]
    decision = _decide(_evidence(), _ledger(stoichiometry=stoich), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "a StoichiometricEntry referencing a ghost participant must NOT be strict"
    )
    assert "stoichiometry_ghost" in decision.reason, decision.reason


# -- R4-08: FormalAtomTransferAssignment ghost participant --

def test_formal_atom_transfer_ghost_participant_never_strict():
    fat = [FormalAtomTransferAssignment(
        source_participant_id="ghost", target_participant_id="p1",
        transferred_atom_map_numbers=[1],
    )]
    decision = _decide(
        _evidence(), _ledger(formal_atom_transfer_assignments=fat), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "a FormalAtomTransferAssignment referencing a ghost participant must NOT "
        "be strict"
    )
    assert "formal_atom_transfer_ghost" in decision.reason, decision.reason


# -- R4-09: generic ledger unknowns are non-empty --

def test_generic_unknowns_never_strict():
    decision = _decide(
        _evidence(),
        _ledger(unknowns=["identity_of_added_carbon_unknown"]),
        [_lineage()],
    )
    assert decision.eligibility != _STRICT, (
        "a ledger with non-empty generic unknowns must NOT be strict (no typed "
        "criticality to prove the unknown is harmless)"
    )
    assert "ledger_unknowns" in decision.reason, decision.reason


# -- R4-10: duplicate lineage id / content --

def test_duplicate_lineage_id_or_content_never_strict():
    lineages = [_lineage(), _lineage()]  # identical id AND content
    decision = _decide(_evidence(), _ledger(), lineages)
    assert decision.eligibility != _STRICT, (
        "duplicate lineage id / exact-duplicate lineage content must NOT be strict"
    )
    assert "duplicate_lineage" in decision.reason, decision.reason


# -- R4-11: explicit ReactionEvidence.quarantine routes to quarantine --

def test_explicit_reaction_evidence_quarantine_routes_to_quarantine():
    evidence = _evidence(quarantine="flagged_by_upstream_curator")
    decision = _decide(evidence, _ledger(), [_lineage()])
    assert decision.eligibility == _QUAR, (
        "a record with an explicit ReactionEvidence.quarantine must route to "
        "quarantine, never be overridden to strict by a self-reported balanced "
        "ledger"
    )
    assert "explicit_evidence_quarantine" in decision.reason, decision.reason


# -- R4-12: identity ambiguity set present --

def test_identity_ambiguity_set_never_strict():
    evidence = _evidence(ambiguity_sets=[{"kind": "donor_identity", "members": "r1|r2"}])
    decision = _decide(evidence, _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "a record with a non-empty ambiguity_sets must NOT be strict (untyped "
        "authority cannot prove the ambiguity is identity-irrelevant)"
    )
    assert "ambiguity_sets" in decision.reason, decision.reason


# -- R4-13: embedded lineage IDs conflict with external typed lineages --

def test_embedded_external_lineage_mismatch_never_strict():
    # external typed lineage id is lin_r1_p1; embedded list names a ghost id.
    evidence = _evidence(resolved_transformed_lineages=["lin_ghost"])
    decision = _decide(evidence, _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "embedded lineage IDs disagreeing with the external typed lineages must "
        "NOT be strict (no silent pick of one representation)"
    )
    assert "embedded_external_lineage" in decision.reason, decision.reason


# -- R4-14: uncontrolled direction value --

def test_uncontrolled_direction_value_never_strict():
    decision = _decide(_evidence(direction="sideways"), _ledger(), [_lineage()])
    assert decision.eligibility != _STRICT, (
        "an uncontrolled direction value ('sideways') must NOT be strict — strict "
        "only accepts the frozen controlled vocabulary"
    )
    assert "direction" in decision.reason, decision.reason


# =====================================================================
# Round 4 (§6.2 / §8) — public snapshot API cannot promote these to strict
# =====================================================================

def test_public_snapshot_api_cannot_promote_element_imbalance_to_strict(tmp_path):
    eb = [ElementBalance(element="C", reactant_count=2, product_count=3, delta=1)]
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_elem"),
        _ledger("rxn_elem", element_balance=eb),
        [_lineage()],
    )
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_elem", expected_index="quarantine")


def test_public_snapshot_api_cannot_promote_explicit_quarantine_to_strict(tmp_path):
    evidence = _evidence(reaction_id="rxn_q", quarantine="flagged_by_upstream_curator")
    item = SnapshotEvidenceItem(evidence, _ledger("rxn_q"), [_lineage()])
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_q", expected_index="quarantine")


def test_public_snapshot_api_cannot_promote_mapping_reverse_collision_to_strict(tmp_path):
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    mr = _mapping_report(pairs=[_pair("r1", 1, "p1", 1), _pair("r1", 2, "p1", 1)])
    item = SnapshotEvidenceItem(
        _evidence(reaction_id="rxn_rev", participants=participants, mapping_report=mr),
        _ledger("rxn_rev"),
        [_lineage(atom_maps=[1, 2])],
    )
    boundary = _build_lanes(tmp_path, [item])
    _assert_public_negative(boundary, "rxn_rev")
