"""P1-T10 Immutable snapshot builder — contract tests (§16.1-16.7).

Tests define the contract for:
- ``build_snapshot(config, evidence_iter) -> SnapshotManifest`` — atomic finalize
- ``load_snapshot(snapshot_id_or_path, root=None) -> SnapshotRecord`` — read-only,
  verify hash

Design references (brief §16.1-16.7):
- §16.1 pipeline: source load → raw preserve → normalize → mapping → roles →
  lineage → ledger → eligibility → production/diagnostic/quarantine → manifest →
  hash → atomic finalize.
- §16.3 manifest: schema version, source files+hashes, record count, each version,
  included strict/conditional/diagnostic/quarantine count, failure counts by
  reason, record content hashes, production index hash, quarantine index hash,
  snapshot hash, build status.
- §16.4 atomicity: temp dir → verify all artifacts → compute final hash → atomic
  finalize → complete=true LAST. Interrupted build → complete=false, loader
  rejects, does NOT overwrite existing immutable snapshot.
- §16.5 loader: explicit snapshot ID/path required, read-only, verify manifest
  hash, reject incomplete, reject hash mismatch, no auto-latest, no modification.
- §16.6 determinism: same source + same versions + same config → identical
  snapshot hash + identical record IDs + identical index content. Source/policy/
  version change → hash change. timestamp / temp path / run ID / unordered
  iteration NOT in canonical snapshot content hash.
- §16.7: 13 tests (deterministic rebuild / source change / policy change /
  quarantine in manifest / production excludes quarantine / all filters counted /
  interrupted not complete / hash mismatch rejected / read-only load /
  explicit snapshot required / existing not overwritten / input ordering
  stability / timestamp not in canonical hash).

Preflight BLOCKED (rdkit absent): the snapshot builder uses fixture data
(synthetic ReactionEvidence + SourceReactionLedger + ResolvedTransformedLineage)
for determinism / atomicity / loader tests. Real source snapshots require rdkit
and are clearly separated from fixture snapshots in the sample report. No real
data fabricated.
"""
from __future__ import annotations

import json
import os
import pytest

from reaction_agent.schemas.common import (
    EligibilityStatus,
    EvaluationBucket,
    QuarantineBehavior,
    LedgerBalanceStatus,
    ParticipantRole,
)
from reaction_agent.schemas.evidence import (
    ReactionEvidence,
    ReactionParticipant,
    RoleHypothesis,
)
from reaction_agent.schemas.ledger import (
    SourceReactionLedger,
    RoleAssignment,
    AddedAtomSource,
    CofactorChange,
)
from reaction_agent.schemas.p1_entities import (
    ResolvedTransformedLineage,
    SnapshotManifest,
    SnapshotRecord,
)
from reaction_agent.config import BuildConfig
from reaction_agent.snapshot.builder import (
    build_snapshot,
    compute_snapshot_hash,
    SnapshotEvidenceItem,
    SnapshotExistsError,
    SnapshotBuildError,
    BUILDER_VERSION,
)
from reaction_agent.snapshot.loader import (
    load_snapshot,
    SnapshotNotFoundError,
    SnapshotIncompleteError,
    SnapshotHashMismatchError,
)


# =====================================================================
# Fixture helpers (synthetic / curated — no real data fabricated)
# =====================================================================

def _participant(
    participant_id: str,
    side: str,
    canonical_smiles: str = "C",
    formal_charge: int = 0,
    stoichiometry: int = 1,
    atom_map_numbers: list[int] | None = None,
    mapped_fraction: float = 1.0,
    changed_atom_fraction: float = 0.0,
    role_hypotheses: list | None = None,
    provenance: list[str] | None = None,
) -> ReactionParticipant:
    """Deterministic ReactionParticipant for unit tests."""
    kwargs: dict = {
        "participant_id": participant_id,
        "molecule_id": f"mol_{participant_id}",
        "canonical_smiles": canonical_smiles,
        "side": side,
        "formal_charge": formal_charge,
        "stoichiometry": stoichiometry,
        "mapped_fraction": mapped_fraction,
        "changed_atom_fraction": changed_atom_fraction,
        "atom_map_numbers": atom_map_numbers or [],
        "role_hypotheses": role_hypotheses or [],
    }
    if provenance is not None:
        kwargs["provenance"] = provenance
    return ReactionParticipant(**kwargs)


def _reaction_evidence(
    participants: list[ReactionParticipant],
    *,
    reaction_id: str = "rxn_001",
    direction: str = "forward",
    source_name: str = "fixture_source_a",
    source_version: str = "v1",
    raw_reaction: str = "A>>B",
    normalized_reaction: str = "A>>B",
    provenance: list[str] | None = None,
) -> ReactionEvidence:
    """Build a ReactionEvidence with participants."""
    kwargs: dict = {
        "reaction_id": reaction_id,
        "source_record_id": f"src_{reaction_id}",
        "source_name": source_name,
        "source_version": source_version,
        "raw_reaction": raw_reaction,
        "normalized_reaction": normalized_reaction,
        "direction": direction,
        "participants": participants,
    }
    if provenance is not None:
        kwargs["provenance"] = provenance
    return ReactionEvidence(**kwargs)


def _lineage(
    reactant_pid: str,
    product_pid: str,
    atom_maps: list[int] | None = None,
    *,
    ambiguity: str = "none",
    lineage_id: str | None = None,
) -> ResolvedTransformedLineage:
    return ResolvedTransformedLineage(
        lineage_id=lineage_id or f"lin_{reactant_pid}_{product_pid}",
        reactant_participant_id=reactant_pid,
        product_participant_id=product_pid,
        ambiguity=ambiguity,
        transformed_atom_maps=atom_maps or [],
    )


def _ledger(
    *,
    balance_status: LedgerBalanceStatus = LedgerBalanceStatus.fully_balanced_explicit_reaction,
    charge_balance: int = 0,
    added_atom_sources: list[AddedAtomSource] | None = None,
    cofactor_changes: list[CofactorChange] | None = None,
    role_assignments: list[RoleAssignment] | None = None,
    unknowns: list[str] | None = None,
    hydrogen_policy: str = "unknown",
    reaction_evidence_id: str = "rxn_001",
) -> SourceReactionLedger:
    return SourceReactionLedger(
        ledger_id=f"srl_{reaction_evidence_id}",
        reaction_evidence_id=reaction_evidence_id,
        balance_status=balance_status,
        charge_balance=charge_balance,
        added_atom_sources=added_atom_sources or [],
        cofactor_changes=cofactor_changes or [],
        role_assignments=role_assignments or [],
        unknowns=unknowns or [],
        hydrogen_policy=hydrogen_policy,
        proton_policy="unknown",
        electron_policy="unknown",
        source_completeness="complete",
        mapping_completeness="complete",
    )


def _role(pid: str, role: str = "transformed_substrate") -> RoleAssignment:
    return RoleAssignment(participant_id=pid, role=ParticipantRole(role), score=0.9)


def _item_strict(
    reaction_id: str = "rxn_strict_001",
    source_name: str = "fixture_source_a",
) -> SnapshotEvidenceItem:
    """strict_eligible item: fully balanced + reliable mapping → production (strict)."""
    r1 = _participant("r1", "reactant", "CCO", atom_map_numbers=[1, 2])
    p1 = _participant("p1", "product", "CC(=O)O", atom_map_numbers=[1, 2])
    ev = _reaction_evidence(
        [r1, p1], reaction_id=reaction_id, source_name=source_name,
        raw_reaction="CCO>>CC(=O)O", normalized_reaction="CCO>>CC(=O)O",
    )
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
        charge_balance=0,
        role_assignments=[_role("r1"), _role("p1", "transformed_product")],
        reaction_evidence_id=reaction_id,
    )
    lineages = [_lineage("r1", "p1", [1, 2], ambiguity="none")]
    return SnapshotEvidenceItem(ev, ledger, lineages)


def _item_conditional(
    reaction_id: str = "rxn_cond_001",
    source_name: str = "fixture_source_a",
) -> SnapshotEvidenceItem:
    """conditional_eligible item: heavy atom balanced + implicit H/e → production (conditional)."""
    r1 = _participant("r1", "reactant", "CCO", atom_map_numbers=[1, 2])
    p1 = _participant("p1", "product", "CC(=O)O", atom_map_numbers=[1, 2])
    ev = _reaction_evidence(
        [r1, p1], reaction_id=reaction_id, source_name=source_name,
        raw_reaction="CCO>>CC(=O)O", normalized_reaction="CCO>>CC(=O)O",
    )
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
        charge_balance=0,
        hydrogen_policy="implicit_heavy_atom_balanced_h_policy",
        role_assignments=[_role("r1"), _role("p1", "transformed_product")],
        reaction_evidence_id=reaction_id,
    )
    lineages = [_lineage("r1", "p1", [1, 2], ambiguity="none")]
    return SnapshotEvidenceItem(ev, ledger, lineages)


def _item_diagnostic(
    reaction_id: str = "rxn_diag_001",
    source_name: str = "fixture_source_a",
) -> SnapshotEvidenceItem:
    """strict_prohibited item: unknown changed heavy atom source → diagnostic."""
    r1 = _participant("r1", "reactant", "CCO", atom_map_numbers=[1, 2],
                      mapped_fraction=0.5)
    p1 = _participant("p1", "product", "CC(=O)O", atom_map_numbers=[1, 2, 3],
                      changed_atom_fraction=0.3)
    ev = _reaction_evidence(
        [r1, p1], reaction_id=reaction_id, source_name=source_name,
        raw_reaction="CCO>>CC(=O)O", normalized_reaction="CCO>>CC(=O)O",
    )
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        charge_balance=0,
        added_atom_sources=[AddedAtomSource(
            atom_map_number=3, source_participant_id="unknown_source",
        )],
        role_assignments=[_role("r1"), _role("p1", "transformed_product")],
        reaction_evidence_id=reaction_id,
    )
    lineages = [_lineage("r1", "p1", [1, 2], ambiguity="none")]
    return SnapshotEvidenceItem(ev, ledger, lineages)


def _item_quarantine(
    reaction_id: str = "rxn_quar_001",
    source_name: str = "fixture_source_a",
) -> SnapshotEvidenceItem:
    """quarantine item: critical element charge contradiction → excluded."""
    r1 = _participant("r1", "reactant", "CCO", atom_map_numbers=[1, 2])
    p1 = _participant("p1", "product", "CC(=O)O", atom_map_numbers=[1, 2])
    ev = _reaction_evidence(
        [r1, p1], reaction_id=reaction_id, source_name=source_name,
        raw_reaction="CCO>>CC(=O)O", normalized_reaction="CCO>>CC(=O)O",
    )
    # charge_balance != 0 → critical_element_charge_contradiction → quarantine
    ledger = _ledger(
        balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        charge_balance=1,  # contradiction
        role_assignments=[_role("r1"), _role("p1", "transformed_product")],
        reaction_evidence_id=reaction_id,
    )
    lineages = [_lineage("r1", "p1", [1, 2], ambiguity="none")]
    return SnapshotEvidenceItem(ev, ledger, lineages)


def _full_fixture_items() -> list[SnapshotEvidenceItem]:
    """All four lane items: 1 strict + 1 conditional + 1 diagnostic + 1 quarantine."""
    return [
        _item_strict(),
        _item_conditional(),
        _item_diagnostic(),
        _item_quarantine(),
    ]


def _config(
    tmp_path,
    *,
    input_source: str = "fixture_source_a",
    eligibility_policy_version: str = "p1-1",
    mapper_version: str = "p1-1",
    random_seed: int = 42,
) -> BuildConfig:
    return BuildConfig(
        input_source=input_source,
        output_snapshot_root=str(tmp_path / "snapshots"),
        mapper_backend="fake",
        mapper_version=mapper_version,
        mapper_parameters={},
        normalization_version="p1-1",
        role_policy_version="p1-1",
        lineage_resolver_version="p1-1",
        ledger_version="p1-1",
        eligibility_policy_version=eligibility_policy_version,
        random_seed=random_seed,
    )


# =====================================================================
# §16.7 Test 1: deterministic rebuild same hash
# =====================================================================

def test_deterministic_rebuild_same_hash(tmp_path):
    """Same source + same versions + same config → same snapshot hash."""
    items = _full_fixture_items()
    config_a = _config(tmp_path / "build_a")
    config_b = _config(tmp_path / "build_b")

    manifest_a = build_snapshot(config_a, iter(items))
    manifest_b = build_snapshot(config_b, iter(items))

    assert manifest_a.snapshot_hash == manifest_b.snapshot_hash
    assert manifest_a.snapshot_id == manifest_b.snapshot_id
    assert manifest_a.build_status == "complete"
    assert manifest_b.build_status == "complete"


# =====================================================================
# §16.7 Test 2: source change new hash
# =====================================================================

def test_source_change_new_hash(tmp_path):
    """Change source content → different snapshot hash."""
    # Build A: items from fixture_source_a
    items_a = _full_fixture_items()
    # Build B: same structure but different source_name
    items_b = [
        _item_strict(source_name="fixture_source_b"),
        _item_conditional(source_name="fixture_source_b"),
        _item_diagnostic(source_name="fixture_source_b"),
        _item_quarantine(source_name="fixture_source_b"),
    ]
    config_a = _config(tmp_path / "a", input_source="fixture_source_a")
    config_b = _config(tmp_path / "b", input_source="fixture_source_b")

    manifest_a = build_snapshot(config_a, iter(items_a))
    manifest_b = build_snapshot(config_b, iter(items_b))

    assert manifest_a.snapshot_hash != manifest_b.snapshot_hash
    assert manifest_a.snapshot_id != manifest_b.snapshot_id


# =====================================================================
# §16.7 Test 3: policy change new hash
# =====================================================================

def test_policy_change_new_hash(tmp_path):
    """Change eligibility_policy_version → different snapshot hash."""
    items = _full_fixture_items()
    config_a = _config(tmp_path / "a", eligibility_policy_version="p1-1")
    config_b = _config(tmp_path / "b", eligibility_policy_version="p1-2")

    manifest_a = build_snapshot(config_a, iter(items))
    manifest_b = build_snapshot(config_b, iter(items))

    assert manifest_a.snapshot_hash != manifest_b.snapshot_hash


# =====================================================================
# §16.7 Test 4: quarantine in manifest
# =====================================================================

def test_quarantine_in_manifest(tmp_path):
    """Quarantine records appear in manifest count + quarantine index."""
    items = _full_fixture_items()
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter(items))

    assert manifest.quarantine_count == 1
    assert manifest.included_strict_count == 1
    assert manifest.conditional_count == 1
    assert manifest.diagnostic_count == 1

    # Verify quarantine index file exists and contains the quarantine record
    snap_dir = os.path.join(config.output_snapshot_root, manifest.snapshot_id)
    quarantine_index = os.path.join(snap_dir, "quarantine_index.jsonl")
    assert os.path.exists(quarantine_index)
    with open(quarantine_index) as f:
        lines = f.readlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["eligibility"] == "quarantine"


# =====================================================================
# §16.7 Test 5: production excludes quarantine
# =====================================================================

def test_production_excludes_quarantine(tmp_path):
    """Production index has NO quarantine records (§15.5 boundary)."""
    items = _full_fixture_items()
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter(items))

    snap_dir = os.path.join(config.output_snapshot_root, manifest.snapshot_id)
    production_index = os.path.join(snap_dir, "production_index.jsonl")
    with open(production_index) as f:
        prod_records = [json.loads(line) for line in f]

    # Production = strict + conditional = 2 records
    assert len(prod_records) == 2
    for rec in prod_records:
        assert rec["eligibility"] in ("strict_eligible", "conditional_eligible")
        assert rec["evaluation_bucket"] == "production"
    # No quarantine in production
    assert all(r["eligibility"] != "quarantine" for r in prod_records)


# =====================================================================
# §16.7 Test 6: all filters counted
# =====================================================================

def test_all_filters_counted(tmp_path):
    """strict + conditional + diagnostic + quarantine counts sum to total."""
    items = _full_fixture_items()
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter(items))

    total = (manifest.included_strict_count
             + manifest.conditional_count
             + manifest.diagnostic_count
             + manifest.quarantine_count)
    # record_count is stored in the on-disk manifest
    snap_dir = os.path.join(config.output_snapshot_root, manifest.snapshot_id)
    with open(os.path.join(snap_dir, "manifest.json")) as f:
        on_disk = json.load(f)
    assert total == on_disk["record_count"]
    assert total == len(items)


# =====================================================================
# §16.7 Test 7: interrupted build not complete
# =====================================================================

def test_interrupted_build_not_complete(tmp_path):
    """Interrupted build → complete=false (or no snapshot), loader rejects."""
    config = _config(tmp_path)

    # Iterator that raises mid-iteration after yielding 2 items
    def _interrupted_iter():
        yield _item_strict()
        yield _item_conditional()
        raise RuntimeError("simulated interruption")

    with pytest.raises(SnapshotBuildError):
        build_snapshot(config, _interrupted_iter())

    # No complete snapshot should exist at the final path
    # (temp dir cleaned up, no atomic rename happened)
    snap_root = config.output_snapshot_root
    if os.path.isdir(snap_root):
        for entry in os.listdir(snap_root):
            entry_path = os.path.join(snap_root, entry)
            if entry.startswith(".tmp_"):
                continue  # temp leftover (cleaned up, but defensive)
            manifest_path = os.path.join(entry_path, "manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path) as f:
                    m = json.load(f)
                assert m["build_status"] != "complete"

    # Loader rejects: no complete snapshot to load
    with pytest.raises((SnapshotNotFoundError, SnapshotIncompleteError)):
        load_snapshot("any_snapshot_id", root=snap_root)


# =====================================================================
# §16.7 Test 8: hash mismatch rejected
# =====================================================================

def test_hash_mismatch_rejected(tmp_path):
    """Tampered snapshot → recomputed hash != stored hash → loader rejects."""
    items = _full_fixture_items()
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter(items))

    snap_dir = os.path.join(config.output_snapshot_root, manifest.snapshot_id)
    manifest_path = os.path.join(snap_dir, "manifest.json")

    # Tamper: add an extra record to production_index without updating hash
    prod_path = os.path.join(snap_dir, "production_index.jsonl")
    with open(prod_path, "a") as f:
        f.write(json.dumps({"reaction_id": "tampered", "eligibility": "strict_eligible"}) + "\n")

    with pytest.raises(SnapshotHashMismatchError):
        load_snapshot(manifest.snapshot_id, root=config.output_snapshot_root)


# =====================================================================
# §16.7 Test 9: read-only load
# =====================================================================

def test_read_only_load(tmp_path):
    """Loader does NOT modify snapshot files."""
    items = _full_fixture_items()
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter(items))

    snap_dir = os.path.join(config.output_snapshot_root, manifest.snapshot_id)

    # Record file state (mtime + size) before load
    files_before = {}
    for fname in os.listdir(snap_dir):
        fpath = os.path.join(snap_dir, fname)
        if os.path.isfile(fpath):
            st = os.stat(fpath)
            files_before[fname] = (st.st_size, st.st_mtime_ns)

    record = load_snapshot(manifest.snapshot_id, root=config.output_snapshot_root)

    # Assert no file changed
    for fname, (size_before, mtime_before) in files_before.items():
        fpath = os.path.join(snap_dir, fname)
        st = os.stat(fpath)
        assert st.st_size == size_before, f"{fname} size changed"
        assert st.st_mtime_ns == mtime_before, f"{fname} mtime changed"

    assert record.freeze_status == "frozen"
    assert record.snapshot_id == manifest.snapshot_id


# =====================================================================
# §16.7 Test 10: explicit snapshot required
# =====================================================================

def test_explicit_snapshot_required(tmp_path):
    """Loader does NOT auto-select latest; requires explicit ID/path."""
    config = _config(tmp_path)

    # Build two snapshots (different content → different IDs)
    build_snapshot(config, iter([_item_strict()]))
    build_snapshot(config, iter([_item_conditional()]))

    snap_root = config.output_snapshot_root
    snapshot_ids = [d for d in os.listdir(snap_root) if not d.startswith(".tmp_")]
    assert len(snapshot_ids) >= 2

    # No ID / empty ID → reject
    with pytest.raises((SnapshotNotFoundError, ValueError, TypeError)):
        load_snapshot("", root=snap_root)

    # None → reject
    with pytest.raises((SnapshotNotFoundError, ValueError, TypeError)):
        load_snapshot(None, root=snap_root)  # type: ignore[arg-type]

    # Nonexistent ID → reject
    with pytest.raises(SnapshotNotFoundError):
        load_snapshot("snap_nonexistent_000", root=snap_root)

    # Explicit valid ID → succeed
    valid = snapshot_ids[0]
    record = load_snapshot(valid, root=snap_root)
    assert record.snapshot_id == valid


# =====================================================================
# §16.7 Test 11: existing snapshot not overwritten
# =====================================================================

def test_existing_snapshot_not_overwritten(tmp_path):
    """Rebuild with same config+content does NOT overwrite existing snapshot."""
    items = _full_fixture_items()
    config = _config(tmp_path)

    manifest_first = build_snapshot(config, iter(items))
    snap_dir = os.path.join(config.output_snapshot_root, manifest_first.snapshot_id)
    manifest_path = os.path.join(snap_dir, "manifest.json")

    # Record original manifest content + mtime
    with open(manifest_path) as f:
        original_manifest = json.load(f)
    original_mtime = os.stat(manifest_path).st_mtime_ns

    # Rebuild with same config + same content → should refuse to overwrite
    with pytest.raises(SnapshotExistsError):
        build_snapshot(config, iter(items))

    # Manifest unchanged
    with open(manifest_path) as f:
        after_manifest = json.load(f)
    assert after_manifest == original_manifest
    assert os.stat(manifest_path).st_mtime_ns == original_mtime


# =====================================================================
# §16.7 Test 12: input record ordering stability
# =====================================================================

def test_input_record_ordering_stability(tmp_path):
    """Different input order → same snapshot hash (canonical sorting)."""
    items = _full_fixture_items()
    config_a = _config(tmp_path / "a")
    config_b = _config(tmp_path / "b")

    # Forward order
    manifest_a = build_snapshot(config_a, iter(items))
    # Reversed order
    manifest_b = build_snapshot(config_b, iter(list(reversed(items))))

    assert manifest_a.snapshot_hash == manifest_b.snapshot_hash
    assert manifest_a.snapshot_id == manifest_b.snapshot_id
    # Counts identical regardless of input order
    assert manifest_a.included_strict_count == manifest_b.included_strict_count
    assert manifest_a.quarantine_count == manifest_b.quarantine_count


# =====================================================================
# §16.7 Test 13: timestamp not in canonical hash
# =====================================================================

def test_timestamp_not_in_canonical_hash(tmp_path):
    """timestamp / run ID / temp path NOT in canonical content hash."""
    items = _full_fixture_items()
    config_a = _config(tmp_path / "a")
    config_b = _config(tmp_path / "b")

    # Build with explicit build_id (simulating different run ID)
    manifest_a = build_snapshot(config_a, iter(items), build_id="run_001")
    manifest_b = build_snapshot(config_b, iter(items), build_id="run_002")

    # Same hash despite different build_id
    assert manifest_a.snapshot_hash == manifest_b.snapshot_hash

    # Verify build_id is stored on disk but NOT in the hash payload
    snap_dir_a = os.path.join(config_a.output_snapshot_root, manifest_a.snapshot_id)
    with open(os.path.join(snap_dir_a, "manifest.json")) as f:
        disk_a = json.load(f)
    assert disk_a["build_id"] == "run_001"
    # The snapshot_hash is identical even though build_id differs
    snap_dir_b = os.path.join(config_b.output_snapshot_root, manifest_b.snapshot_id)
    with open(os.path.join(snap_dir_b, "manifest.json")) as f:
        disk_b = json.load(f)
    assert disk_b["build_id"] == "run_002"
    assert disk_a["snapshot_hash"] == disk_b["snapshot_hash"]


# =====================================================================
# Additional contract tests
# =====================================================================

def test_compute_snapshot_hash_no_write(tmp_path):
    """compute_snapshot_hash returns hash without writing to disk."""
    items = _full_fixture_items()
    config = _config(tmp_path / "hash_only")
    h = compute_snapshot_hash(config, items)
    assert isinstance(h, str)
    assert len(h) == 64  # sha256 hex
    # Same items → same hash
    h2 = compute_snapshot_hash(config, items)
    assert h == h2
    # No snapshot directory was created
    assert not os.path.exists(os.path.join(str(tmp_path / "hash_only"), "snapshots"))


def test_manifest_carries_versions_and_counts(tmp_path):
    """Manifest carries schema_version, policy_version, source_counts, all 4 counts."""
    items = _full_fixture_items()
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter(items))

    assert manifest.schema_version == "p1-1"
    assert manifest.policy_version == "p1-1"
    assert manifest.build_status == "complete"
    assert manifest.snapshot_hash
    assert manifest.included_strict_count == 1
    assert manifest.conditional_count == 1
    assert manifest.diagnostic_count == 1
    assert manifest.quarantine_count == 1
    # source_counts present
    assert isinstance(manifest.source_counts, dict)
    assert sum(manifest.source_counts.values()) == 4


def test_on_disk_manifest_has_full_16_3_fields(tmp_path):
    """On-disk manifest.json has all §16.3 fields."""
    items = _full_fixture_items()
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter(items))

    snap_dir = os.path.join(config.output_snapshot_root, manifest.snapshot_id)
    with open(os.path.join(snap_dir, "manifest.json")) as f:
        disk = json.load(f)

    # §16.3 required fields
    required = [
        "snapshot_id", "schema_version", "build_status", "snapshot_hash",
        "record_count", "included_strict_count", "conditional_count",
        "diagnostic_count", "quarantine_count",
        "source_files", "versions", "failure_counts_by_reason",
        "record_content_hashes", "production_index_hash",
        "quarantine_index_hash", "build_config_hash", "policy_version",
    ]
    for key in required:
        assert key in disk, f"manifest.json missing §16.3 field: {key}"

    # failure_counts_by_reason: quarantine reason present
    assert isinstance(disk["failure_counts_by_reason"], dict)
    assert sum(disk["failure_counts_by_reason"].values()) >= 1  # at least the quarantine

    # record_content_hashes: sorted list of sha256 hex
    hashes = disk["record_content_hashes"]
    assert hashes == sorted(hashes)
    assert all(len(h) == 64 for h in hashes)


def test_load_snapshot_by_path(tmp_path):
    """Loader accepts explicit path (not just ID under root)."""
    items = _full_fixture_items()
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter(items))

    snap_path = os.path.join(config.output_snapshot_root, manifest.snapshot_id)
    record = load_snapshot(snap_path)
    assert record.snapshot_id == manifest.snapshot_id
    assert record.freeze_status == "frozen"


def test_load_snapshot_rejects_incomplete(tmp_path):
    """Loader rejects manifest with build_status != complete."""
    config = _config(tmp_path)
    # Manually create an incomplete snapshot dir
    snap_dir = os.path.join(config.output_snapshot_root, "snap_partial_0001")
    os.makedirs(snap_dir, exist_ok=True)
    with open(os.path.join(snap_dir, "manifest.json"), "w") as f:
        json.dump({
            "snapshot_id": "snap_partial_0001",
            "schema_version": "p1-1",
            "build_status": "partial",
            "snapshot_hash": "fake",
            "record_count": 0,
            "included_strict_count": 0,
            "conditional_count": 0,
            "diagnostic_count": 0,
            "quarantine_count": 0,
        }, f)

    with pytest.raises(SnapshotIncompleteError):
        load_snapshot("snap_partial_0001", root=config.output_snapshot_root)


def test_builder_does_not_mutate_inputs(tmp_path):
    """build_snapshot does NOT mutate input evidence items."""
    items = _full_fixture_items()
    # Deep snapshot of reaction_id + participants before
    before_ids = [it.reaction_evidence.reaction_id for it in items]
    before_smiles = [
        [p.canonical_smiles for p in it.reaction_evidence.participants]
        for it in items
    ]

    config = _config(tmp_path)
    build_snapshot(config, iter(items))

    # After build, original items unchanged
    after_ids = [it.reaction_evidence.reaction_id for it in items]
    after_smiles = [
        [p.canonical_smiles for p in it.reaction_evidence.participants]
        for it in items
    ]
    assert after_ids == before_ids
    assert after_smiles == before_smiles


def test_builder_version():
    """BUILDER_VERSION is defined and non-empty."""
    assert BUILDER_VERSION
    assert BUILDER_VERSION.startswith("p1-t10")


def test_hash_mismatch_content_tamper_detected(tmp_path):
    """H2 fix: tampering record content (but keeping stored hash) is detected."""
    items = _full_fixture_items()
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter(items))

    snap_dir = os.path.join(config.output_snapshot_root, manifest.snapshot_id)

    # Tamper: modify a record's content field but keep its stored
    # record_content_hash unchanged (sophisticated tamper)
    records_path = os.path.join(snap_dir, "records.jsonl")
    with open(records_path) as f:
        lines = f.readlines()
    records = [json.loads(line) for line in lines if line.strip()]
    # Modify the first record's normalized_reaction (content change)
    records[0]["normalized_reaction"] = "TAMPERED>>REACTION"
    with open(records_path, "w") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")

    # Loader should detect: recomputed record hash != stored record_content_hash
    with pytest.raises(SnapshotHashMismatchError):
        load_snapshot(manifest.snapshot_id, root=config.output_snapshot_root)


def test_loader_rejects_temp_dir(tmp_path):
    """M1 fix: loader refuses to load .tmp_* directories as snapshots."""
    items = _full_fixture_items()
    config = _config(tmp_path)
    build_snapshot(config, iter(items))

    snap_root = config.output_snapshot_root
    # Create a fake temp dir
    tmp_dir = os.path.join(snap_root, ".tmp_snap_fake_0001")
    os.makedirs(tmp_dir, exist_ok=True)

    with pytest.raises(SnapshotNotFoundError):
        load_snapshot(tmp_dir)
    with pytest.raises(SnapshotNotFoundError):
        load_snapshot(".tmp_snap_fake_0001", root=snap_root)
