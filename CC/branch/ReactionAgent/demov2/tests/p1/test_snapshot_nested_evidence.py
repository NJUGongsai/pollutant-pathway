"""Critical-1 RED tests — snapshot hash must cover complete nested evidence.

Implements §3.4 of CHATGPT_P1_REMEDIATION_PROMPT_ROUND_2.md.

The OLD ``_record_content_hash`` only hashes top-level evidence fields +
decision. It does NOT cover:
- complete participants (atom_map_numbers / provenance / role_hypotheses)
- mapping_report (formal_mapped_source_assignment / fallback_method)
- SourceReactionLedger (unknowns / evidence_ids / added_atom_sources)
- resolved lineages (transformed_atom_maps / evidence_ids / ambiguity)

Each test ACTUALLY mutates nested content and recomputes the hash — it does
NOT assert a precomputed boolean (§3.4 forbids ``assert same_hash_3way``).
The records-persist tests read ``records.jsonl`` and assert full nested
content is present. The loader-tamper tests mutate ``records.jsonl`` nested
fields (keeping ``record_content_hash`` unchanged) and assert the loader
rejects the tampered snapshot.
"""
from __future__ import annotations

import json
import os

import pytest

from reaction_agent.config import BuildConfig
from reaction_agent.schemas.common import (
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
    RoleAssignment,
    SourceReactionLedger,
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
    compute_snapshot_hash,
)
from reaction_agent.snapshot.loader import (
    SnapshotHashMismatchError,
    _recompute_snapshot_hash,
    load_snapshot,
)


# =====================================================================
# Fixture helpers (self-contained — no cross-test-file import)
# =====================================================================

def _participant(
    pid: str,
    side: str,
    smiles: str = "CC",
    atom_map_numbers: list[int] | None = None,
    provenance: list[str] | None = None,
    role_hypotheses: list | None = None,
    mapped_fraction: float = 1.0,
    changed_atom_fraction: float = 0.0,
) -> ReactionParticipant:
    kwargs: dict = {
        "participant_id": pid,
        "molecule_id": f"mol_{pid}",
        "canonical_smiles": smiles,
        "side": side,
        "atom_map_numbers": atom_map_numbers or [],
        "mapped_fraction": mapped_fraction,
        "changed_atom_fraction": changed_atom_fraction,
    }
    if provenance is not None:
        kwargs["provenance"] = provenance
    if role_hypotheses is not None:
        kwargs["role_hypotheses"] = role_hypotheses
    return ReactionParticipant(**kwargs)


def _mapping_report(
    *,
    mapper_name: str = "fake_mapper",
    mapper_version: str = "v1",
    mapping_status: str = "fully_mapped",
    fallback_method: str | None = None,
    map_number_uniqueness: bool = True,
    changed_atom_coverage: float = 1.0,
    mapped_heavy_atom_fraction: float = 1.0,
    reactant_pid: str = "r1",
    product_pid: str = "p1",
    assignment_method: str = "formal_mapped",
) -> MappingReport:
    return MappingReport(
        mapper_name=mapper_name,
        mapper_version=mapper_version,
        mapper_parameters={"timeout": "30"},
        input_hash="inp_abc",
        output_hash="out_def",
        mapping_status=MappingStatus(mapping_status),
        mapped_heavy_atom_fraction=mapped_heavy_atom_fraction,
        map_number_uniqueness=map_number_uniqueness,
        changed_atom_coverage=changed_atom_coverage,
        formal_mapped_source_assignment=FormalSourceAssignment(
            mapper_name=mapper_name,
            mapper_version=mapper_version,
            mapped_atom_pairs=[
                FormalMappedAtomPair(
                    reactant_participant_id=reactant_pid,
                    reactant_atom_map=1,
                    product_participant_id=product_pid,
                    product_atom_map=1,
                ),
                FormalMappedAtomPair(
                    reactant_participant_id=reactant_pid,
                    reactant_atom_map=2,
                    product_participant_id=product_pid,
                    product_atom_map=2,
                ),
            ],
            assignment_method=SourceAssignmentMethod(assignment_method),
            assignment_quality=MappingQualityClass.high_quality,
            assignment_ambiguity=False,
        ),
        fallback_method=fallback_method,
    )


def _ledger(
    *,
    reaction_evidence_id: str = "rxn_strict_001",
    balance_status: LedgerBalanceStatus = LedgerBalanceStatus.fully_balanced_explicit_reaction,
    unknowns: list[str] | None = None,
    evidence_ids: list[str] | None = None,
    added_atom_sources: list[AddedAtomSource] | None = None,
    charge_balance: int = 0,
) -> SourceReactionLedger:
    return SourceReactionLedger(
        ledger_id=f"srl_{reaction_evidence_id}",
        reaction_evidence_id=reaction_evidence_id,
        balance_status=balance_status,
        charge_balance=charge_balance,
        added_atom_sources=added_atom_sources or [],
        role_assignments=[
            RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
            RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_product, score=0.9),
        ],
        unknowns=unknowns or [],
        evidence_ids=evidence_ids or [],
        hydrogen_policy="explicit",
        proton_policy="explicit",
        electron_policy="explicit",
        source_completeness="complete",
        mapping_completeness="complete",
    )


def _full_strict_item(
    reaction_id: str = "rxn_strict_001",
    source_name: str = "fixture_source_a",
    *,
    participants: list[ReactionParticipant] | None = None,
    mapping_report: MappingReport | None = None,
    ledger: SourceReactionLedger | None = None,
    lineages: list[ResolvedTransformedLineage] | None = None,
) -> SnapshotEvidenceItem:
    """A strict-eligible item with COMPLETE nested evidence (participants,
    mapping_report, ledger, lineages all populated). Each call returns a fresh
    independent instance so tests can mutate one without affecting another."""
    if participants is None:
        # R7-01B: genuine fully-mapped strict baseline — CC (2 heavy atoms,
        # 2 maps) on each side.
        participants = [
            _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2],
                         provenance=["src_r1", "db_rxn"]),
            _participant("p1", "product", "CC", atom_map_numbers=[1, 2],
                         provenance=["src_p1"]),
        ]
    ev = ReactionEvidence(
        reaction_id=reaction_id,
        source_record_id=f"src_{reaction_id}",
        source_name=source_name,
        source_version="v1",
        raw_reaction="CC>>CC",
        normalized_reaction="CC>>CC",
        direction="forward",
        participants=participants,
        mapping_report=mapping_report or _mapping_report(),
        provenance=["rxn_prov_a"],
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
                evidence_ids=["lin_ev_1"],
            ),
        ],
    )


def _config(
    tmp_path,
    *,
    mapper_version: str = "p1-1",
    eligibility_policy_version: str = "p1-1",
) -> BuildConfig:
    return BuildConfig(
        input_source="fixture_source_a",
        output_snapshot_root=str(tmp_path / "snapshots"),
        mapper_backend="fake",
        mapper_version=mapper_version,
        mapper_parameters={},
        normalization_version="p1-1",
        role_policy_version="p1-1",
        lineage_resolver_version="p1-1",
        ledger_version="p1-1",
        eligibility_policy_version=eligibility_policy_version,
        random_seed=42,
    )


def _build_and_get_dir(tmp_path, items=None):
    items = items if items is not None else [_full_strict_item()]
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter(items))
    snap_dir = os.path.join(config.output_snapshot_root, manifest.snapshot_id)
    return snap_dir, manifest


def _read_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_jsonl(path: str, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")


# =====================================================================
# Round 8 fixture additions — non-strict lanes (self-contained, synthetic)
# =====================================================================

def _full_conditional_item(
    reaction_id: str = "rxn_cond_001",
    source_name: str = "fixture_source_a",
) -> SnapshotEvidenceItem:
    """Conditional-eligible item (heavy-atom balanced with implicit H/e
    policy) → ``conditional`` lane (still production, never diagnostic)."""
    return _full_strict_item(
        reaction_id=reaction_id,
        source_name=source_name,
        ledger=_ledger(
            reaction_evidence_id=reaction_id,
            balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
        ),
    )


def _full_diagnostic_item(
    reaction_id: str = "rxn_diag_001",
    source_name: str = "fixture_source_a",
) -> SnapshotEvidenceItem:
    """Strict-prohibited item (partial/unbalanced source with an unknown
    added-atom source) → ``diagnostic`` lane (NEVER production). Synthetic
    fixture only — does not impersonate real reaction evidence."""
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2],
                     mapped_fraction=0.5),
        _participant("p1", "product", "CCC", atom_map_numbers=[1, 2, 3],
                     changed_atom_fraction=0.3),
    ]
    ev = ReactionEvidence(
        reaction_id=reaction_id,
        source_record_id=f"src_{reaction_id}",
        source_name=source_name,
        source_version="v1",
        raw_reaction="CC>>CCC",
        normalized_reaction="CC>>CCC",
        direction="forward",
        participants=participants,
        mapping_report=_mapping_report(),
        provenance=["rxn_prov_a"],
    )
    ledger = _ledger(
        reaction_evidence_id=reaction_id,
        balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        added_atom_sources=[
            AddedAtomSource(atom_map_number=3, source_participant_id="unknown_source"),
        ],
    )
    lineage = ResolvedTransformedLineage(
        lineage_id="lin_r1_p1",
        reactant_participant_id="r1",
        product_participant_id="p1",
        ambiguity="none",
        transformed_atom_maps=[1, 2],
        resolution_quality=LineageResolutionQuality.resolved,
        evidence_ids=["lin_ev_1"],
    )
    return SnapshotEvidenceItem(ev, ledger, [lineage])


def _full_quarantine_item(
    reaction_id: str = "rxn_quar_001",
    source_name: str = "fixture_source_a",
) -> SnapshotEvidenceItem:
    """Quarantine item (charge_balance != 0 → critical element/charge
    contradiction) → ``quarantine`` lane (NEVER production)."""
    return _full_strict_item(
        reaction_id=reaction_id,
        source_name=source_name,
        ledger=_ledger(
            reaction_evidence_id=reaction_id,
            balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
            charge_balance=1,
        ),
    )


def _sync_snapshot_hash(snap_dir: str) -> None:
    """Recompute the snapshot hash from CURRENT on-disk artifacts and sync
    manifest.json snapshot_hash + COMPLETE marker (and the extended
    diagnostic_index_hash manifest field). Used ONLY by the hash-coherent
    wrong-partition tests to prove the loader rejects a
    self-consistent-but-semantically-wrong snapshot (Round 8 §10)."""
    from reaction_agent.hashing import canonical_hash
    manifest_path = os.path.join(snap_dir, "manifest.json")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    # keep the extended diagnostic_index_hash field coherent with the current
    # diagnostic index before recomputing the overall snapshot hash
    diag_path = os.path.join(snap_dir, "diagnostic_index.jsonl")
    diag = _read_jsonl(diag_path)
    manifest["diagnostic_index_hash"] = canonical_hash(
        sorted(r["record_content_hash"] for r in diag)
    )
    recomputed = _recompute_snapshot_hash(manifest, snap_dir)
    manifest["snapshot_hash"] = recomputed
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, sort_keys=True, indent=2)
    with open(os.path.join(snap_dir, "COMPLETE"), "w", encoding="utf-8") as f:
        f.write(recomputed)


# =====================================================================
# §3.4 — hash changes when nested evidence changes (9 tests)
# =====================================================================

def test_snapshot_hash_changes_when_participant_changes(tmp_path):
    """Mutate participant canonical_smiles → snapshot hash must change."""
    config = _config(tmp_path)
    hash_before = compute_snapshot_hash(config, [_full_strict_item()])
    mutated = _full_strict_item()
    mutated.reaction_evidence.participants[0].canonical_smiles = "CCCCO"
    hash_after = compute_snapshot_hash(config, [mutated])
    assert hash_before != hash_after, (
        "participant canonical_smiles change did not alter snapshot hash — "
        "participants are not covered by the content hash"
    )


def test_snapshot_hash_changes_when_participant_provenance_changes(tmp_path):
    """Mutate participant provenance → snapshot hash must change."""
    config = _config(tmp_path)
    hash_before = compute_snapshot_hash(config, [_full_strict_item()])
    mutated = _full_strict_item()
    mutated.reaction_evidence.participants[0].provenance.append("extra_prov")
    hash_after = compute_snapshot_hash(config, [mutated])
    assert hash_before != hash_after, (
        "participant provenance change did not alter snapshot hash"
    )


def test_snapshot_hash_changes_when_mapping_report_changes(tmp_path):
    """Mutate mapping_report mapper_name → snapshot hash must change."""
    config = _config(tmp_path)
    hash_before = compute_snapshot_hash(config, [_full_strict_item()])
    mutated = _full_strict_item()
    mutated.reaction_evidence.mapping_report.mapper_name = "different_mapper"
    hash_after = compute_snapshot_hash(config, [mutated])
    assert hash_before != hash_after, (
        "mapping_report change did not alter snapshot hash"
    )


def test_snapshot_hash_changes_when_mapping_pair_changes(tmp_path):
    """Mutate formal_mapped_source_assignment.mapped_atom_pairs → hash must change."""
    config = _config(tmp_path)
    hash_before = compute_snapshot_hash(config, [_full_strict_item()])
    mutated = _full_strict_item()
    mutated.reaction_evidence.mapping_report.formal_mapped_source_assignment.mapped_atom_pairs[0].product_atom_map = 99
    hash_after = compute_snapshot_hash(config, [mutated])
    assert hash_before != hash_after, (
        "mapping pair change did not alter snapshot hash"
    )


def test_snapshot_hash_changes_when_source_ledger_changes(tmp_path):
    """Mutate ledger unknowns → snapshot hash must change."""
    config = _config(tmp_path)
    hash_before = compute_snapshot_hash(config, [_full_strict_item()])
    mutated = _full_strict_item()
    mutated.source_ledger.unknowns.append("new_unknown_entry")
    hash_after = compute_snapshot_hash(config, [mutated])
    assert hash_before != hash_after, (
        "source ledger unknowns change did not alter snapshot hash"
    )


def test_snapshot_hash_changes_when_lineage_pair_changes(tmp_path):
    """Mutate lineage reactant/product participant_id → snapshot hash must change."""
    config = _config(tmp_path)
    hash_before = compute_snapshot_hash(config, [_full_strict_item()])
    mutated = _full_strict_item()
    mutated.lineages[0].product_participant_id = "p9"
    hash_after = compute_snapshot_hash(config, [mutated])
    assert hash_before != hash_after, (
        "lineage pair change did not alter snapshot hash"
    )


def test_snapshot_hash_changes_when_transformed_atom_maps_change(tmp_path):
    """Mutate lineage transformed_atom_maps → snapshot hash must change."""
    config = _config(tmp_path)
    hash_before = compute_snapshot_hash(config, [_full_strict_item()])
    mutated = _full_strict_item()
    mutated.lineages[0].transformed_atom_maps.append(99)
    hash_after = compute_snapshot_hash(config, [mutated])
    assert hash_before != hash_after, (
        "transformed_atom_maps change did not alter snapshot hash"
    )


def test_snapshot_hash_changes_when_lineage_evidence_changes(tmp_path):
    """Mutate lineage evidence_ids → snapshot hash must change."""
    config = _config(tmp_path)
    hash_before = compute_snapshot_hash(config, [_full_strict_item()])
    mutated = _full_strict_item()
    mutated.lineages[0].evidence_ids.append("lin_ev_extra")
    hash_after = compute_snapshot_hash(config, [mutated])
    assert hash_before != hash_after, (
        "lineage evidence_ids change did not alter snapshot hash"
    )


def test_snapshot_hash_changes_when_policy_or_content_version_changes(tmp_path):
    """Mutate mapper_version / eligibility_policy_version → snapshot hash must change."""
    items = [_full_strict_item()]
    hash_v1 = compute_snapshot_hash(_config(tmp_path / "a", mapper_version="p1-1"), items)
    hash_v2 = compute_snapshot_hash(_config(tmp_path / "b", mapper_version="p1-2"), items)
    assert hash_v1 != hash_v2, "mapper_version change did not alter snapshot hash"
    hash_p1 = compute_snapshot_hash(
        _config(tmp_path / "c", eligibility_policy_version="p1-1"), items)
    hash_p2 = compute_snapshot_hash(
        _config(tmp_path / "d", eligibility_policy_version="p1-2"), items)
    assert hash_p1 != hash_p2, "eligibility_policy_version change did not alter hash"


# =====================================================================
# §3.4 — records.jsonl persists complete nested evidence (3 tests)
# =====================================================================

def test_snapshot_records_persist_complete_reaction_evidence(tmp_path):
    """records.jsonl must persist complete participants (with atom_map_numbers + provenance)."""
    snap_dir, _ = _build_and_get_dir(tmp_path)
    records = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    assert len(records) == 1
    rec = records[0]
    # Critical-1 §5.3: participants live inside the complete nested
    # reaction_evidence object, not as a top-level whitelist projection.
    assert "reaction_evidence" in rec, "records.jsonl missing reaction_evidence object"
    ev = rec["reaction_evidence"]
    assert "participants" in ev, "reaction_evidence missing participants field"
    assert len(ev["participants"]) == 2
    assert ev["participants"][0]["atom_map_numbers"] == [1, 2]
    assert ev["participants"][0]["provenance"] == ["src_r1", "db_rxn"]


def test_snapshot_records_persist_source_ledger(tmp_path):
    """records.jsonl must persist complete SourceReactionLedger (unknowns + evidence_ids)."""
    snap_dir, _ = _build_and_get_dir(tmp_path)
    records = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    rec = records[0]
    assert "source_ledger" in rec, "records.jsonl missing source_ledger field"
    ledger = rec["source_ledger"]
    assert ledger["source_completeness"] == "complete"
    assert ledger["mapping_completeness"] == "complete"
    assert "unknowns" in ledger
    assert "evidence_ids" in ledger


def test_snapshot_records_persist_resolved_lineages(tmp_path):
    """records.jsonl must persist complete resolved lineages (transformed_atom_maps + evidence_ids)."""
    snap_dir, _ = _build_and_get_dir(tmp_path)
    records = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    rec = records[0]
    assert "resolved_lineages" in rec, "records.jsonl missing resolved_lineages field"
    lins = rec["resolved_lineages"]
    assert len(lins) == 1
    assert lins[0]["transformed_atom_maps"] == [1, 2]
    assert lins[0]["evidence_ids"] == ["lin_ev_1"]
    assert lins[0]["ambiguity"] == "none"


# =====================================================================
# §3.4 — loader rejects tampered nested evidence (4 tests)
# =====================================================================

def test_loader_rejects_tampered_nested_participant(tmp_path):
    """Mutate records.jsonl participant (keep record_content_hash) → loader rejects."""
    snap_dir, _ = _build_and_get_dir(tmp_path)
    path = os.path.join(snap_dir, "records.jsonl")
    records = _read_jsonl(path)
    records[0]["reaction_evidence"]["participants"][0]["atom_map_numbers"] = [99, 98]
    _write_jsonl(path, records)
    with pytest.raises(SnapshotHashMismatchError):
        load_snapshot(snap_dir)


def test_loader_rejects_tampered_mapping_report(tmp_path):
    """Mutate records.jsonl mapping_report → loader rejects."""
    snap_dir, _ = _build_and_get_dir(tmp_path)
    path = os.path.join(snap_dir, "records.jsonl")
    records = _read_jsonl(path)
    records[0]["reaction_evidence"]["mapping_report"]["mapper_name"] = "tampered_mapper"
    _write_jsonl(path, records)
    with pytest.raises(SnapshotHashMismatchError):
        load_snapshot(snap_dir)


def test_loader_rejects_tampered_source_ledger(tmp_path):
    """Mutate records.jsonl source_ledger unknowns → loader rejects."""
    snap_dir, _ = _build_and_get_dir(tmp_path)
    path = os.path.join(snap_dir, "records.jsonl")
    records = _read_jsonl(path)
    records[0]["source_ledger"]["unknowns"].append("tampered_unknown")
    _write_jsonl(path, records)
    with pytest.raises(SnapshotHashMismatchError):
        load_snapshot(snap_dir)


def test_loader_rejects_tampered_lineage(tmp_path):
    """Mutate records.jsonl lineage transformed_atom_maps → loader rejects."""
    snap_dir, _ = _build_and_get_dir(tmp_path)
    path = os.path.join(snap_dir, "records.jsonl")
    records = _read_jsonl(path)
    records[0]["resolved_lineages"][0]["transformed_atom_maps"] = [99]
    _write_jsonl(path, records)
    with pytest.raises(SnapshotHashMismatchError):
        load_snapshot(snap_dir)


# =====================================================================
# §3.4 — index integrity (2 tests)
# =====================================================================

def test_index_entry_must_reference_existing_full_record(tmp_path):
    """production_index entry with dangling reaction_id (not in records) → loader rejects."""
    snap_dir, _ = _build_and_get_dir(tmp_path)
    prod_path = os.path.join(snap_dir, "production_index.jsonl")
    prods = _read_jsonl(prod_path)
    # Replace an existing entry's reaction_id with a dangling one (keep
    # record_content_hash so production_index_hash is unchanged). The loader
    # must still reject because the reaction_id does not exist in records.jsonl.
    # Critical-1 §5.3: reaction_id lives inside the nested reaction_evidence.
    prods[0]["reaction_evidence"]["reaction_id"] = "rxn_dangling_999"
    _write_jsonl(prod_path, prods)
    with pytest.raises(SnapshotHashMismatchError):
        load_snapshot(snap_dir)


def test_index_lane_must_match_full_record_decision(tmp_path):
    """production_index entry whose lane disagrees with records → loader rejects."""
    snap_dir, _ = _build_and_get_dir(tmp_path)
    prod_path = os.path.join(snap_dir, "production_index.jsonl")
    prods = _read_jsonl(prod_path)
    # Flip the lane of an existing production entry (keep reaction_id + hash).
    prods[0]["lane"] = "quarantine"
    _write_jsonl(prod_path, prods)
    with pytest.raises(SnapshotHashMismatchError):
        load_snapshot(snap_dir)


# =====================================================================
# Round 8 — loader index partition contract (§7–§10)
#
# These tests were written FIRST (RED) against the Round-7 loader, which only
# checked (a) index reaction_id exists in records, (b) index lane == full
# record lane, (c) index stored record_content_hash == full record stored hash.
# It did NOT verify (1) the exact partition (strict/conditional → production,
# diagnostic → diagnostic, quarantine → quarantine), (2) diagnostic index
# membership completeness, (3) index entry payload rehash, or (4) that the
# diagnostic index is bound into the immutable snapshot hash. Each negative
# test starts from a legal snapshot that loads successfully, mutates ONE
# target condition in a temp dir, and asserts the loader fails closed with a
# stable ``index_partition_*`` / ``index_entry_*`` / ``index_record_*`` reason
# token (never a generic stored/recomputed hash mismatch, missing file, JSON
# parse, or collection failure).
# =====================================================================

def _rid(rec: dict) -> str:
    return rec["reaction_evidence"]["reaction_id"]


def test_loader_rejects_hash_coherent_diagnostic_in_production(tmp_path):
    """R8-01: a hash-coherent diagnostic record injected into production must
    be rejected (production only allows strict/conditional)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    # 1. legal snapshot loads BEFORE mutation; 2. expected membership asserted
    load_snapshot(snap_dir)
    prod_path = os.path.join(snap_dir, "production_index.jsonl")
    assert all(_rid(r) != "rxn_diag_001" for r in _read_jsonl(prod_path))
    # 3. one target condition: inject the diagnostic record into production
    recs = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    rec = next(r for r in recs if _rid(r) == "rxn_diag_001")
    assert rec["lane"] == "diagnostic"
    with open(prod_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    # hash-coherent: recompute + sync manifest/COMPLETE (self-consistent but
    # semantically wrong partition). Failure MUST be index_partition_wrong_lane.
    _sync_snapshot_hash(snap_dir)
    with pytest.raises(SnapshotHashMismatchError, match="index_partition_wrong_lane"):
        load_snapshot(snap_dir)


def test_loader_rejects_hash_coherent_quarantine_in_production(tmp_path):
    """R8-01b: a hash-coherent quarantine record injected into production must
    be rejected (production excludes quarantine)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_quarantine_item()])
    load_snapshot(snap_dir)
    prod_path = os.path.join(snap_dir, "production_index.jsonl")
    assert all(_rid(r) != "rxn_quar_001" for r in _read_jsonl(prod_path))
    recs = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    rec = next(r for r in recs if _rid(r) == "rxn_quar_001")
    assert rec["lane"] == "quarantine"
    with open(prod_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    _sync_snapshot_hash(snap_dir)
    with pytest.raises(SnapshotHashMismatchError, match="index_partition_wrong_lane"):
        load_snapshot(snap_dir)


def test_loader_rejects_hash_coherent_strict_in_diagnostic(tmp_path):
    """R8-01c: a hash-coherent strict record injected into diagnostic must be
    rejected (diagnostic only allows diagnostic)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    diag_path = os.path.join(snap_dir, "diagnostic_index.jsonl")
    assert all(_rid(r) != "rxn_strict_001" for r in _read_jsonl(diag_path))
    recs = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    rec = next(r for r in recs if _rid(r) == "rxn_strict_001")
    assert rec["lane"] == "strict"
    with open(diag_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    _sync_snapshot_hash(snap_dir)
    with pytest.raises(SnapshotHashMismatchError, match="index_partition_wrong_lane"):
        load_snapshot(snap_dir)


def test_loader_rejects_missing_diagnostic_member_without_metadata_change(tmp_path):
    """R8-02: emptying diagnostic_index must be rejected WITHOUT touching
    manifest/hash/COMPLETE (diagnostic audit evidence cannot silently vanish)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)
    diag_path = os.path.join(snap_dir, "diagnostic_index.jsonl")
    assert len(_read_jsonl(diag_path)) == 1
    _write_jsonl(diag_path, [])  # only change: remove the expected member
    with pytest.raises(SnapshotHashMismatchError, match="index_partition_missing"):
        load_snapshot(snap_dir)


def test_loader_rejects_missing_production_member(tmp_path):
    """Removing a conditional member from production_index must be rejected
    with index_partition_missing (not a generic hash mismatch)."""
    snap_dir, _ = _build_and_get_dir(
        tmp_path, [_full_strict_item(), _full_conditional_item()])
    load_snapshot(snap_dir)
    prod_path = os.path.join(snap_dir, "production_index.jsonl")
    prods = _read_jsonl(prod_path)
    assert {_rid(r) for r in prods} == {"rxn_strict_001", "rxn_cond_001"}
    # only change: drop the conditional member from production
    _write_jsonl(prod_path, [r for r in prods if _rid(r) != "rxn_cond_001"])
    with pytest.raises(SnapshotHashMismatchError, match="index_partition_missing"):
        load_snapshot(snap_dir)


def test_loader_rejects_missing_quarantine_member(tmp_path):
    """Removing a quarantine member from quarantine_index must be rejected with
    index_partition_missing (quarantine cannot silently disappear)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_quarantine_item()])
    load_snapshot(snap_dir)
    quar_path = os.path.join(snap_dir, "quarantine_index.jsonl")
    assert len(_read_jsonl(quar_path)) == 1
    _write_jsonl(quar_path, [])
    with pytest.raises(SnapshotHashMismatchError, match="index_partition_missing"):
        load_snapshot(snap_dir)


def test_loader_rejects_duplicate_records_reaction_id(tmp_path):
    """records.jsonl must have unique reaction_ids — a duplicate record is an
    index_record_duplicate, not a generic hash mismatch."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    recs_path = os.path.join(snap_dir, "records.jsonl")
    recs = _read_jsonl(recs_path)
    _write_jsonl(recs_path, recs + recs)  # duplicate the single record
    with pytest.raises(SnapshotHashMismatchError, match="index_record_duplicate"):
        load_snapshot(snap_dir)


def test_loader_rejects_duplicate_index_reaction_id(tmp_path):
    """An index must not contain the same reaction_id twice — index_entry_duplicate."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    prod_path = os.path.join(snap_dir, "production_index.jsonl")
    prods = _read_jsonl(prod_path)
    _write_jsonl(prod_path, prods + prods)
    with pytest.raises(SnapshotHashMismatchError, match="index_entry_duplicate"):
        load_snapshot(snap_dir)


def test_loader_rejects_cross_index_membership(tmp_path):
    """A record must appear in EXACTLY one index. Injecting a strict record
    into diagnostic_index makes it a cross-index member — rejected. (An entry
    in a foreign index always carries a lane that index forbids, so the
    partition validator catches it as index_partition_wrong_lane.)"""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    diag_path = os.path.join(snap_dir, "diagnostic_index.jsonl")
    prod_path = os.path.join(snap_dir, "production_index.jsonl")
    assert all(_rid(r) != "rxn_strict_001" for r in _read_jsonl(diag_path))
    assert any(_rid(r) == "rxn_strict_001" for r in _read_jsonl(prod_path))
    recs = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    rec = next(r for r in recs if _rid(r) == "rxn_strict_001")
    with open(diag_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    with pytest.raises(SnapshotHashMismatchError, match="index_partition_wrong_lane"):
        load_snapshot(snap_dir)


def test_loader_rejects_mutated_nested_production_index_payload(tmp_path):
    """R8-03: mutating an index entry's nested chemistry payload (keeping the
    entry's stored record_content_hash) must be rejected — the loader must
    rehash the index entry payload, never trust its self-reported hash."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    prod_path = os.path.join(snap_dir, "production_index.jsonl")
    prods = _read_jsonl(prod_path)
    stored_hash = prods[0]["record_content_hash"]
    prods[0]["reaction_evidence"]["participants"][0]["canonical_smiles"] = "C#N"
    assert prods[0]["record_content_hash"] == stored_hash  # entry hash untouched
    _write_jsonl(prod_path, prods)
    with pytest.raises(SnapshotHashMismatchError, match="index_entry_content_mismatch"):
        load_snapshot(snap_dir)


def test_loader_rejects_mutated_nested_diagnostic_index_payload(tmp_path):
    """Mutating a diagnostic_index entry's nested payload (keeping its stored
    hash) must be rejected — index_entry_content_mismatch."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)
    diag_path = os.path.join(snap_dir, "diagnostic_index.jsonl")
    diags = _read_jsonl(diag_path)
    stored_hash = diags[0]["record_content_hash"]
    diags[0]["reaction_evidence"]["participants"][0]["canonical_smiles"] = "C#N"
    assert diags[0]["record_content_hash"] == stored_hash
    _write_jsonl(diag_path, diags)
    with pytest.raises(SnapshotHashMismatchError, match="index_entry_content_mismatch"):
        load_snapshot(snap_dir)


def test_loader_accepts_exact_complete_index_partition(tmp_path):
    """POSITIVE protection: a snapshot with all four lanes loads, and the three
    indexes are an exact, complete, pairwise-disjoint partition of records."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [
        _full_strict_item(), _full_conditional_item(),
        _full_diagnostic_item(), _full_quarantine_item(),
    ])
    loaded = load_snapshot(snap_dir)
    assert loaded.freeze_status == "frozen"
    records = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    prod = _read_jsonl(os.path.join(snap_dir, "production_index.jsonl"))
    diag = _read_jsonl(os.path.join(snap_dir, "diagnostic_index.jsonl"))
    quar = _read_jsonl(os.path.join(snap_dir, "quarantine_index.jsonl"))
    record_ids = {_rid(r) for r in records}
    prod_ids = {_rid(r) for r in prod}
    diag_ids = {_rid(r) for r in diag}
    quar_ids = {_rid(r) for r in quar}
    # exact complete partition: union == records
    assert prod_ids | diag_ids | quar_ids == record_ids
    # pairwise disjoint
    assert prod_ids & diag_ids == set()
    assert prod_ids & quar_ids == set()
    assert diag_ids & quar_ids == set()
    # lane-exact membership
    assert {_rid(r) for r in records if r["lane"] == "strict"} | \
           {_rid(r) for r in records if r["lane"] == "conditional"} == prod_ids
    assert {_rid(r) for r in records if r["lane"] == "diagnostic"} == diag_ids
    assert {_rid(r) for r in records if r["lane"] == "quarantine"} == quar_ids


def test_conditional_record_is_only_in_production_index(tmp_path):
    """POSITIVE protection: conditional records stay in production (never
    diagnostic / quarantine) and the loader still accepts."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_conditional_item()])
    loaded = load_snapshot(snap_dir)
    assert loaded.freeze_status == "frozen"
    prod = _read_jsonl(os.path.join(snap_dir, "production_index.jsonl"))
    diag = _read_jsonl(os.path.join(snap_dir, "diagnostic_index.jsonl"))
    quar = _read_jsonl(os.path.join(snap_dir, "quarantine_index.jsonl"))
    assert any(_rid(r) == "rxn_cond_001" for r in prod)
    assert all(_rid(r) != "rxn_cond_001" for r in diag)
    assert all(_rid(r) != "rxn_cond_001" for r in quar)


def test_diagnostic_index_content_changes_snapshot_hash(tmp_path):
    """The diagnostic index MUST be bound into the immutable snapshot hash:
    changing diagnostic index content (adding a duplicate member, records and
    manifest untouched) changes the recomputed snapshot hash. RED on Round 7
    (diagnostic_index_hash absent from canonical content)."""
    from reaction_agent.snapshot.loader import _recompute_snapshot_hash as _rh
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    manifest_path = os.path.join(snap_dir, "manifest.json")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    hash_before = _rh(manifest, snap_dir)
    diag_path = os.path.join(snap_dir, "diagnostic_index.jsonl")
    diags = _read_jsonl(diag_path)
    _write_jsonl(diag_path, diags + diags)  # diagnostic content changed
    hash_after = _rh(manifest, snap_dir)
    assert hash_before != hash_after, (
        "diagnostic index content is not bound into the snapshot hash — "
        "diagnostic_index_hash missing from canonical content"
    )


def test_snapshot_manifest_persists_diagnostic_index_hash(tmp_path):
    """The on-disk manifest must persist diagnostic_index_hash, and it must
    equal canonical_hash of the sorted diagnostic record content hashes."""
    from reaction_agent.hashing import canonical_hash
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)  # positive: the snapshot still loads
    with open(os.path.join(snap_dir, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    assert "diagnostic_index_hash" in manifest, (
        "on-disk manifest missing diagnostic_index_hash field")
    diag = _read_jsonl(os.path.join(snap_dir, "diagnostic_index.jsonl"))
    expected = canonical_hash(sorted(r["record_content_hash"] for r in diag))
    assert manifest["diagnostic_index_hash"] == expected
    assert isinstance(manifest["diagnostic_index_hash"], str)
    assert len(manifest["diagnostic_index_hash"]) == 64


# =====================================================================
# Round 9 — manifest-authority envelope (§R9-6/§R9-8)
#
# Round 7/8 loaders trusted the raw on-disk manifest: a missing required
# field was skipped via .get(), counts were returned downstream untampered,
# and snapshot_id identity was never verified. These tests were written FIRST
# (RED) against that loader. Each negative test starts from a legal snapshot
# that loads successfully, mutates ONE manifest authority condition in a temp
# dir, and asserts the loader fails closed with a stable ``manifest_*`` /
# ``snapshot_identity_mismatch`` reason token — never a generic stored/
# recomputed hash mismatch, JSON parse, or missing-file error.
# =====================================================================

def _read_manifest(snap_dir: str) -> dict:
    with open(os.path.join(snap_dir, "manifest.json"), encoding="utf-8") as f:
        return json.load(f)


def _write_manifest(snap_dir: str, manifest: dict) -> None:
    with open(os.path.join(snap_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, sort_keys=True, indent=2)


def test_loader_rejects_missing_manifest_diagnostic_index_hash(tmp_path):
    """R9-01: deleting the required manifest diagnostic_index_hash field must
    fail closed (manifest_required_field_missing), not be skipped via .get()."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)  # 1. legal snapshot loads BEFORE mutation
    manifest = _read_manifest(snap_dir)
    assert "diagnostic_index_hash" in manifest
    del manifest["diagnostic_index_hash"]  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_required_field_missing"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_diagnostic_index_hash_wrong_type(tmp_path):
    """A required manifest field with the wrong type (int instead of str) must
    fail closed with manifest_field_type_invalid."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["diagnostic_index_hash"] = 123  # only change: wrong type
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_diagnostic_index_hash_wrong_value(tmp_path):
    """A manifest diagnostic_index_hash that disagrees with the recomputed
    value (from the diagnostic index) must fail closed with
    manifest_index_hash_mismatch."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["diagnostic_index_hash"] = "f" * 64  # only change: wrong value
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_index_hash_mismatch"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_count_mismatch(tmp_path):
    """R9-02: a tampered manifest lane count (diagnostic_count=999) must fail
    closed with manifest_count_mismatch — not be returned downstream."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["diagnostic_count"] = 999  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_count_mismatch"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_record_count_mismatch(tmp_path):
    """A tampered manifest record_count must fail closed with
    manifest_count_mismatch."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["record_count"] = 999  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_count_mismatch"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_record_hashes_mismatch(tmp_path):
    """A tampered manifest record_content_hashes list must fail closed with
    manifest_record_hashes_mismatch (never trust the manifest self-report)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["record_content_hashes"] = ["f" * 64]  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_record_hashes_mismatch"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_production_index_hash_mismatch(tmp_path):
    """A tampered manifest production_index_hash must fail closed with
    manifest_index_hash_mismatch (production)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["production_index_hash"] = "f" * 64  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_index_hash_mismatch"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_diagnostic_index_hash_mismatch(tmp_path):
    """A tampered manifest diagnostic_index_hash must fail closed with
    manifest_index_hash_mismatch (diagnostic)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["diagnostic_index_hash"] = "e" * 64  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_index_hash_mismatch"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_quarantine_index_hash_mismatch(tmp_path):
    """A tampered manifest quarantine_index_hash must fail closed with
    manifest_index_hash_mismatch (quarantine)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_quarantine_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["quarantine_index_hash"] = "d" * 64  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_index_hash_mismatch"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_source_counts_mismatch(tmp_path):
    """A forged manifest source_counts must fail closed with
    manifest_source_counts_mismatch (total must equal record_count)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["source_counts"] = {"fixture_source_a": 999}  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_source_counts_mismatch"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_source_hash_mismatch(tmp_path):
    """A forged manifest source_files hash must fail closed with
    manifest_source_hash_mismatch."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["source_files"] = {"fixture_source_a": "f" * 64}  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_source_hash_mismatch"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_failure_counts_mismatch(tmp_path):
    """A forged manifest failure_counts_by_reason must fail closed with
    manifest_failure_counts_mismatch."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    assert manifest["failure_counts_by_reason"], "diagnostic lane implies non-empty failure counts"
    manifest["failure_counts_by_reason"] = {"forged_reason": 7}  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_failure_counts_mismatch"):
        load_snapshot(snap_dir)


def test_loader_rejects_snapshot_identity_mismatch(tmp_path):
    """R9-03: a forged manifest snapshot_id must fail closed with
    snapshot_identity_mismatch (snapshot_id must equal 'snap_'+hash[:12] AND
    the resolved directory basename)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["snapshot_id"] = "snap_forged000000"  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="snapshot_identity_mismatch"):
        load_snapshot(snap_dir)


def test_loader_accepts_verified_manifest_authority(tmp_path):
    """POSITIVE protection: a legal snapshot loads, and every verified manifest
    field matches the value rebuilt from verified artifacts."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    rec = load_snapshot(snap_dir)
    assert rec.freeze_status == "frozen"
    manifest = _read_manifest(snap_dir)
    # returned manifest uses VERIFIED values
    assert rec.manifest.snapshot_id == manifest["snapshot_id"]
    assert rec.manifest.diagnostic_count == 1
    assert rec.manifest.included_strict_count == 0  # diagnostic-only snapshot
    # identity: snapshot_id == "snap_" + snapshot_hash[:12] == dir basename
    expected_id = f"snap_{manifest['snapshot_hash'][:12]}"
    assert manifest["snapshot_id"] == expected_id
    assert os.path.basename(snap_dir) == expected_id
    # record hash list: on-disk list == sorted records hashes
    records = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    assert manifest["record_content_hashes"] == sorted(
        r["record_content_hash"] for r in records)
    # diagnostic index hash
    diag = _read_jsonl(os.path.join(snap_dir, "diagnostic_index.jsonl"))
    from reaction_agent.hashing import canonical_hash
    assert manifest["diagnostic_index_hash"] == canonical_hash(
        sorted(r["record_content_hash"] for r in diag))


def test_loader_accepts_verified_manifest_with_all_four_lanes(tmp_path):
    """POSITIVE protection: a four-lane snapshot loads and every count /
    summary field in the returned manifest matches the verified records."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [
        _full_strict_item(), _full_conditional_item(),
        _full_diagnostic_item(), _full_quarantine_item(),
    ])
    rec = load_snapshot(snap_dir)
    assert rec.freeze_status == "frozen"
    records = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    # counts rebuilt from verified records
    lane_counts = {}
    for r in records:
        lane_counts[r["lane"]] = lane_counts.get(r["lane"], 0) + 1
    assert rec.manifest.included_strict_count == lane_counts.get("strict", 0)
    assert rec.manifest.conditional_count == lane_counts.get("conditional", 0)
    assert rec.manifest.diagnostic_count == lane_counts.get("diagnostic", 0)
    assert rec.manifest.quarantine_count == lane_counts.get("quarantine", 0)
    # source_counts sum == record count
    assert sum(rec.manifest.source_counts.values()) == len(records)
