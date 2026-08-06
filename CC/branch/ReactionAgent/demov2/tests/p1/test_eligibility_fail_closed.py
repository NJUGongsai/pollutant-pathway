"""Critical-2 RED tests — incomplete source/mapping must NEVER enter strict.

Implements §4.4 of CHATGPT_P1_REMEDIATION_PROMPT_ROUND_2.md.

The OLD ``_classify_state`` returns ``strict_eligible`` whenever
``balance_status == fully_balanced_explicit_reaction`` — WITHOUT checking
``source_completeness`` / ``mapping_completeness`` / ``mapping_report`` /
``fallback_method`` / ``assignment_method`` / lineage participant references.
ChatGPT constructed a legal-schema input with source_completeness=incomplete +
mapping_completeness=failed + balance=fully_balanced and the engine fail-OPENED
to strict_eligible. These tests prove that fail-open.

Each test constructs a legal-schema item (passes pydantic validation) with ONE
bad cross-invariant and asserts ``decide_eligibility`` does NOT return
``strict_eligible``. Fail-closed is the correct behavior (§4.2).
"""
from __future__ import annotations

import json
import os

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
    RoleAssignment,
    SourceReactionLedger,
)
from reaction_agent.schemas.mapping import (
    FormalMappedAtomPair,
    FormalSourceAssignment,
    MappingReport,
)
from reaction_agent.schemas.p1_entities import ResolvedTransformedLineage
from reaction_agent.snapshot.builder import SnapshotEvidenceItem, build_snapshot


# =====================================================================
# Fixture helpers (self-contained)
# =====================================================================

def _participant(pid: str, side: str, smiles: str = "CC",
                 amn: list[int] | None = None) -> ReactionParticipant:
    return ReactionParticipant(
        participant_id=pid,
        molecule_id=f"mol_{pid}",
        canonical_smiles=smiles,
        side=side,
        atom_map_numbers=amn or [],
        mapped_fraction=1.0,
        changed_atom_fraction=0.0,
    )


def _mapping_report(
    *,
    mapping_status: str = "fully_mapped",
    fallback_method: str | None = None,
    map_number_uniqueness: bool = True,
    changed_atom_coverage: float = 1.0,
    assignment_method: str = "formal_mapped",
    symmetry_ambiguity: bool = False,
    resonance_tautomer_ambiguity: bool = False,
) -> MappingReport:
    return MappingReport(
        mapper_name="fake_mapper",
        mapper_version="v1",
        mapper_parameters={"timeout": "30"},
        input_hash="inp_abc",
        output_hash="out_def",
        mapping_status=MappingStatus(mapping_status),
        mapped_heavy_atom_fraction=1.0,
        map_number_uniqueness=map_number_uniqueness,
        changed_atom_coverage=changed_atom_coverage,
        formal_mapped_source_assignment=FormalSourceAssignment(
            mapper_name="fake_mapper",
            mapper_version="v1",
            mapped_atom_pairs=[
                FormalMappedAtomPair(
                    reactant_participant_id="r1", reactant_atom_map=1,
                    product_participant_id="p1", product_atom_map=1,
                ),
                FormalMappedAtomPair(
                    reactant_participant_id="r1", reactant_atom_map=2,
                    product_participant_id="p1", product_atom_map=2,
                ),
            ],
            assignment_method=SourceAssignmentMethod(assignment_method),
            assignment_quality=MappingQualityClass.high_quality,
            assignment_ambiguity=False,
        ),
        fallback_method=fallback_method,
        symmetry_ambiguity=symmetry_ambiguity,
        resonance_tautomer_ambiguity=resonance_tautomer_ambiguity,
    )


def _ledger(
    *,
    reaction_evidence_id: str = "rxn_strict_001",
    balance_status: LedgerBalanceStatus = LedgerBalanceStatus.fully_balanced_explicit_reaction,
    source_completeness: str = "complete",
    mapping_completeness: str = "complete",
    unknowns: list[str] | None = None,
) -> SourceReactionLedger:
    return SourceReactionLedger(
        ledger_id=f"srl_{reaction_evidence_id}",
        reaction_evidence_id=reaction_evidence_id,
        balance_status=balance_status,
        charge_balance=0,
        role_assignments=[
            RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
            RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_product, score=0.9),
        ],
        unknowns=unknowns or [],
        hydrogen_policy="explicit",
        proton_policy="explicit",
        electron_policy="explicit",
        source_completeness=source_completeness,
        mapping_completeness=mapping_completeness,
    )


def _strict_item(
    *,
    reaction_id: str = "rxn_strict_001",
    mapping_report: MappingReport | None = "_default",
    ledger: SourceReactionLedger | None = None,
    lineages: list[ResolvedTransformedLineage] | None = None,
    participants: list[ReactionParticipant] | None = None,
) -> SnapshotEvidenceItem:
    """Legal strict-eligible item: fully_balanced + complete + fully_mapped +
    formal_mapped + no fallback + lineage refs valid. Each call → fresh instance."""
    if mapping_report == "_default":
        mapping_report = _mapping_report()
    if participants is None:
        participants = [_participant("r1", "reactant", "CC", [1, 2]),
                        _participant("p1", "product", "CC", [1, 2])]
    ev = ReactionEvidence(
        reaction_id=reaction_id,
        source_record_id=f"src_{reaction_id}",
        source_name="fixture_source_a",
        source_version="v1",
        raw_reaction="CC>>CC",
        normalized_reaction="CC>>CC",
        direction="forward",
        participants=participants,
        mapping_report=mapping_report,
    )
    return SnapshotEvidenceItem(
        ev,
        ledger or _ledger(reaction_evidence_id=reaction_id),
        lineages or [
            ResolvedTransformedLineage(
                lineage_id="lin_r1_p1",
                reactant_participant_id="r1",
                product_participant_id="p1",
                ambiguity="none",
                transformed_atom_maps=[1, 2],
                resolution_quality=LineageResolutionQuality.resolved,
            ),
        ],
    )


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


def _read_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# =====================================================================
# §4.4 — fail-closed RED tests (12)
# =====================================================================

def test_incomplete_source_never_strict_eligible():
    """source_completeness=incomplete + fully_balanced → NOT strict."""
    item = _strict_item(ledger=_ledger(source_completeness="incomplete"))
    d = decide_eligibility(item.reaction_evidence, item.source_ledger, item.lineages)
    assert d.eligibility != EligibilityStatus.strict_eligible, (
        f"incomplete source fail-OPENED to strict_eligible: {d.eligibility} / {d.reason}"
    )


def test_failed_mapping_never_strict_eligible():
    """mapping_status=mapping_failed + fully_balanced → NOT strict."""
    item = _strict_item(mapping_report=_mapping_report(mapping_status="mapping_failed"))
    d = decide_eligibility(item.reaction_evidence, item.source_ledger, item.lineages)
    assert d.eligibility != EligibilityStatus.strict_eligible, (
        f"failed mapping fail-OPENED to strict_eligible: {d.eligibility} / {d.reason}"
    )


def test_partial_mapping_never_strict_eligible():
    """mapping_status=partially_mapped + fully_balanced → NOT strict."""
    item = _strict_item(mapping_report=_mapping_report(mapping_status="partially_mapped"))
    d = decide_eligibility(item.reaction_evidence, item.source_ledger, item.lineages)
    assert d.eligibility != EligibilityStatus.strict_eligible, (
        f"partial mapping fail-OPENED to strict_eligible: {d.eligibility} / {d.reason}"
    )


def test_unmapped_never_strict_eligible():
    """mapping_status=unmapped + fully_balanced → NOT strict."""
    item = _strict_item(mapping_report=_mapping_report(mapping_status="unmapped"))
    d = decide_eligibility(item.reaction_evidence, item.source_ledger, item.lineages)
    assert d.eligibility != EligibilityStatus.strict_eligible, (
        f"unmapped fail-OPENED to strict_eligible: {d.eligibility} / {d.reason}"
    )


def test_mcs_fallback_never_strict_eligible():
    """assignment_method=formal_mcs + fully_balanced → NOT strict."""
    item = _strict_item(mapping_report=_mapping_report(assignment_method="formal_mcs"))
    d = decide_eligibility(item.reaction_evidence, item.source_ledger, item.lineages)
    assert d.eligibility != EligibilityStatus.strict_eligible, (
        f"MCS fallback fail-OPENED to strict_eligible: {d.eligibility} / {d.reason}"
    )


def test_center_pair_fallback_never_strict_eligible():
    """fallback_method=center_pair + fully_balanced → NOT strict."""
    item = _strict_item(mapping_report=_mapping_report(fallback_method="center_pair"))
    d = decide_eligibility(item.reaction_evidence, item.source_ledger, item.lineages)
    assert d.eligibility != EligibilityStatus.strict_eligible, (
        f"center_pair fallback fail-OPENED to strict_eligible: {d.eligibility} / {d.reason}"
    )


def test_missing_mapping_report_never_strict_eligible():
    """mapping_report=None + fully_balanced → NOT strict."""
    item = _strict_item(mapping_report=None)
    d = decide_eligibility(item.reaction_evidence, item.source_ledger, item.lineages)
    assert d.eligibility != EligibilityStatus.strict_eligible, (
        f"missing mapping_report fail-OPENED to strict_eligible: {d.eligibility} / {d.reason}"
    )


def test_ledger_reaction_id_mismatch_fails_closed():
    """ledger.reaction_evidence_id != reaction_id → NOT strict (fail-closed)."""
    item = _strict_item(ledger=_ledger(reaction_evidence_id="different_rxn"))
    d = decide_eligibility(item.reaction_evidence, item.source_ledger, item.lineages)
    assert d.eligibility != EligibilityStatus.strict_eligible, (
        f"ledger/reaction id mismatch fail-OPENED to strict_eligible: {d.eligibility} / {d.reason}"
    )


def test_lineage_unknown_participant_fails_closed():
    """lineage references a participant_id not in participants → NOT strict."""
    item = _strict_item(lineages=[
        ResolvedTransformedLineage(
            lineage_id="lin_r1_p9",
            reactant_participant_id="r1",
            product_participant_id="p9",  # not in participants
            ambiguity="none",
            transformed_atom_maps=[1],
        ),
    ])
    d = decide_eligibility(item.reaction_evidence, item.source_ledger, item.lineages)
    assert d.eligibility != EligibilityStatus.strict_eligible, (
        f"unknown lineage participant fail-OPENED to strict_eligible: {d.eligibility} / {d.reason}"
    )


def test_contradictory_balance_and_mapping_state_rejected():
    """balance=fully_balanced + mapping_completeness=failed → NOT strict
    (the contradictory combo ChatGPT used to prove fail-open)."""
    item = _strict_item(ledger=_ledger(
        balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
        mapping_completeness="failed",
    ))
    d = decide_eligibility(item.reaction_evidence, item.source_ledger, item.lineages)
    assert d.eligibility != EligibilityStatus.strict_eligible, (
        f"contradictory balance+mapping fail-OPENED to strict_eligible: {d.eligibility} / {d.reason}"
    )


def test_incomplete_mapping_never_enters_production_index(tmp_path):
    """build_snapshot with mapping_completeness=failed → record NOT in production_index."""
    item = _strict_item(ledger=_ledger(mapping_completeness="failed"))
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter([item]))
    snap_dir = os.path.join(config.output_snapshot_root, manifest.snapshot_id)
    prod = _read_jsonl(os.path.join(snap_dir, "production_index.jsonl"))
    rid = item.reaction_evidence.reaction_id
    in_prod = any(r["reaction_id"] == rid for r in prod)
    assert not in_prod, (
        f"record with mapping_completeness=failed entered production index (lane should be diagnostic)"
    )


def test_direct_deserialization_cannot_bypass_strict_boundary(tmp_path):
    """Public API SnapshotEvidenceItem with bad ledger → record lane != strict.

    Proves the strict boundary cannot be bypassed by constructing a
    SnapshotEvidenceItem directly (no schema deserialization shortcut)."""
    item = _strict_item(ledger=_ledger(source_completeness="incomplete"))
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter([item]))
    snap_dir = os.path.join(config.output_snapshot_root, manifest.snapshot_id)
    records = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    assert records[0]["lane"] != "strict", (
        f"direct-constructed bad-ledger item entered strict lane: {records[0]['lane']}"
    )


# =====================================================================
# Sanity: the legal strict item IS strict (proves fail-CLOSED, not fail-ALWAYS)
# =====================================================================

def test_legal_strict_item_is_strict_eligible():
    """A fully-compliant item (complete + fully_mapped + formal_mapped + no
    fallback + valid lineage refs) MUST be strict_eligible. Proves the engine
    fails closed for bad inputs but still accepts good ones."""
    item = _strict_item()
    d = decide_eligibility(item.reaction_evidence, item.source_ledger, item.lineages)
    assert d.eligibility == EligibilityStatus.strict_eligible, (
        f"legal strict item was NOT strict_eligible: {d.eligibility} / {d.reason}"
    )
