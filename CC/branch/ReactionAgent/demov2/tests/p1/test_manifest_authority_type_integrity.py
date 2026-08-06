"""Round 10 Task A RED tests — manifest type-authority integrity.

ChatGPT's P1 Round 9 independent audit confirmed that the loader still has a
type-authority gap: JSON booleans (``true``/``false``) and floats (``1.0``) are
accepted where the frozen manifest contract requires exact integers, a missing
or wrong-typed ``build_status`` bypasses the required/type validator, a
non-object manifest is not rejected up front, and ``_validate_manifest_authority``
returns raw manifest values instead of rebuilt/verified ones.

Every negative test here:
1. builds a legal snapshot with the public ``build_snapshot``;
2. loads it with the real public ``load_snapshot`` BEFORE the mutation;
3. mutates exactly ONE manifest condition;
4. leaves records / indexes / snapshot hash / COMPLETE unchanged;
5. calls the real public ``load_snapshot`` again;
6. asserts the specific exception type AND the stable reason token;
7. runs in ``tmp_path``;
8. never passes by catching a JSON parse error, a missing file, or a
   downstream Pydantic error — the asserted token is a loader-emitted token.
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
)
from reaction_agent.snapshot.loader import (
    SnapshotHashMismatchError,
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
    return ReactionParticipant(**kwargs)


def _mapping_report(
    *,
    mapper_name: str = "fake_mapper",
    mapper_version: str = "v1",
    mapping_status: str = "fully_mapped",
    fallback_method: str | None = None,
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
        mapped_heavy_atom_fraction=1.0,
        map_number_uniqueness=True,
        changed_atom_coverage=1.0,
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
    ledger: SourceReactionLedger | None = None,
    lineages: list[ResolvedTransformedLineage] | None = None,
) -> SnapshotEvidenceItem:
    """A strict-eligible item with COMPLETE nested evidence. Each call returns
    a fresh independent instance so tests can mutate one without affecting
    another."""
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
        mapping_report=_mapping_report(),
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


def _full_conditional_item(
    reaction_id: str = "rxn_cond_001",
    source_name: str = "fixture_source_a",
) -> SnapshotEvidenceItem:
    """Conditional-eligible item → ``conditional`` lane (still production)."""
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
    """Strict-prohibited item → ``diagnostic`` lane. Synthetic fixture only."""
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
    """Quarantine item (charge_balance != 0) → ``quarantine`` lane."""
    return _full_strict_item(
        reaction_id=reaction_id,
        source_name=source_name,
        ledger=_ledger(
            reaction_evidence_id=reaction_id,
            balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
            charge_balance=1,
        ),
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


def _build_and_get_dir(tmp_path, items=None):
    items = items if items is not None else [_full_strict_item()]
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter(items))
    snap_dir = os.path.join(config.output_snapshot_root, manifest.snapshot_id)
    return snap_dir, manifest


def _read_manifest(snap_dir: str) -> dict:
    with open(os.path.join(snap_dir, "manifest.json"), encoding="utf-8") as f:
        return json.load(f)


def _write_manifest(snap_dir: str, manifest: dict) -> None:
    with open(os.path.join(snap_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, sort_keys=True, indent=2)


def _read_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# The 20 frozen Round 9 required manifest authority fields. Every one must be
# rejected by the real public load_snapshot when missing (manifest_required_field_missing).
_REQUIRED_MANIFEST_FIELDS = [
    "snapshot_id",
    "schema_version",
    "included_strict_count",
    "conditional_count",
    "diagnostic_count",
    "quarantine_count",
    "build_status",
    "snapshot_hash",
    "build_id",
    "source_counts",
    "policy_version",
    "record_count",
    "versions",
    "source_files",
    "failure_counts_by_reason",
    "record_content_hashes",
    "production_index_hash",
    "diagnostic_index_hash",
    "quarantine_index_hash",
    "build_config_hash",
]


# =====================================================================
# Booleans / floats must NOT be accepted as exact-int counts
# =====================================================================

def test_loader_rejects_manifest_record_count_bool(tmp_path):
    """record_count=true is a bool, not an exact int — must fail closed with
    manifest_field_type_invalid, never be accepted as the int 1."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["record_count"] = True  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_included_strict_count_bool(tmp_path):
    """included_strict_count=true must fail closed with
    manifest_field_type_invalid (bool is not an exact int)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["included_strict_count"] = True  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_conditional_count_bool(tmp_path):
    """conditional_count=true must fail closed with manifest_field_type_invalid."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_conditional_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["conditional_count"] = True  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_diagnostic_count_bool(tmp_path):
    """diagnostic_count=true must fail closed with manifest_field_type_invalid."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["diagnostic_count"] = True  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_quarantine_count_bool(tmp_path):
    """quarantine_count=true must fail closed with manifest_field_type_invalid."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_quarantine_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["quarantine_count"] = True  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_source_count_bool(tmp_path):
    """A bool source count inside source_counts must fail closed with
    manifest_field_type_invalid, never be accepted as the int 1."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["source_counts"] = {"fixture_source_a": True}  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_source_count_float(tmp_path):
    """A float source count inside source_counts must fail closed with
    manifest_field_type_invalid (1.0 is not an exact int)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["source_counts"] = {"fixture_source_a": 1.0}  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_failure_count_bool(tmp_path):
    """A bool failure count inside failure_counts_by_reason must fail closed
    with manifest_field_type_invalid (true count is 1)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    assert manifest["failure_counts_by_reason"], "diagnostic lane implies non-empty failure counts"
    reason = next(iter(manifest["failure_counts_by_reason"]))
    manifest["failure_counts_by_reason"] = {reason: True}  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_failure_count_float(tmp_path):
    """A float failure count inside failure_counts_by_reason must fail closed
    with manifest_field_type_invalid (1.0 is not an exact int)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    assert manifest["failure_counts_by_reason"], "diagnostic lane implies non-empty failure counts"
    reason = next(iter(manifest["failure_counts_by_reason"]))
    manifest["failure_counts_by_reason"] = {reason: 1.0}  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


# =====================================================================
# build_status must go through the required/type validator
# =====================================================================

def test_loader_rejects_missing_manifest_build_status(tmp_path):
    """A missing build_status must fail closed with manifest_required_field_missing
    (not silently default to 'unknown' and raise SnapshotIncompleteError)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    del manifest["build_status"]  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_required_field_missing"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_build_status_wrong_type(tmp_path):
    """build_status=true (a bool, not a str) must fail closed with
    manifest_field_type_invalid, not be compared to 'complete'."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["build_status"] = True  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


# =====================================================================
# Non-object manifest and nested shape/type violations
# =====================================================================

def test_loader_rejects_non_object_manifest(tmp_path):
    """A JSON manifest that is not an object (here: a list) must fail closed
    with manifest_field_type_invalid — never reach .get() / AttributeError."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    with open(os.path.join(snap_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump([], f)  # only change: top-level manifest is a list
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_versions_nested_wrong_type(tmp_path):
    """versions must be dict[str, non-empty str]; a non-str nested value must
    fail closed with manifest_field_type_invalid (before any hash recompute)."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["versions"] = {"package_version": 123}  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_source_files_nested_wrong_type(tmp_path):
    """source_files must be dict[str, non-empty str]; a non-str nested value
    must fail closed with manifest_field_type_invalid."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["source_files"] = {"fixture_source_a": 123}  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


def test_loader_rejects_manifest_record_hash_list_nested_wrong_type(tmp_path):
    """record_content_hashes must be list[non-empty str]; a non-str element
    must fail closed with manifest_field_type_invalid."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_strict_item()])
    load_snapshot(snap_dir)
    manifest = _read_manifest(snap_dir)
    manifest["record_content_hashes"] = ["f" * 64, 123]  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_field_type_invalid"):
        load_snapshot(snap_dir)


# =====================================================================
# Returned SnapshotManifest carries REBUILT values
# =====================================================================

def test_loader_returns_recomputed_manifest_counts(tmp_path):
    """The returned SnapshotManifest counts must be the values REBUILT from the
    verified records (per lane), with build_status verified 'complete'."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [
        _full_strict_item(), _full_conditional_item(),
        _full_diagnostic_item(), _full_quarantine_item(),
    ])
    records = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    rebuilt = {}
    for r in records:
        rebuilt[r["lane"]] = rebuilt.get(r["lane"], 0) + 1
    rec = load_snapshot(snap_dir)
    assert rec.freeze_status == "frozen"
    assert rec.manifest.build_status == "complete"
    assert rec.manifest.included_strict_count == rebuilt.get("strict", 0)
    assert rec.manifest.conditional_count == rebuilt.get("conditional", 0)
    assert rec.manifest.diagnostic_count == rebuilt.get("diagnostic", 0)
    assert rec.manifest.quarantine_count == rebuilt.get("quarantine", 0)


def test_loader_returns_recomputed_source_counts(tmp_path):
    """The returned source_counts must be rebuilt from the verified records
    (per-source counts), not raw manifest echoes."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [
        _full_strict_item(reaction_id="rxn_strict_001", source_name="fixture_source_a"),
        _full_strict_item(reaction_id="rxn_strict_002", source_name="fixture_source_b"),
        _full_strict_item(reaction_id="rxn_strict_003", source_name="fixture_source_a"),
    ])
    records = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    rebuilt = {}
    for r in records:
        src = r["reaction_evidence"]["source_name"]
        rebuilt[src] = rebuilt.get(src, 0) + 1
    rec = load_snapshot(snap_dir)
    assert rec.freeze_status == "frozen"
    assert rec.manifest.source_counts == dict(sorted(rebuilt.items()))
    assert sum(rec.manifest.source_counts.values()) == len(records)


# =====================================================================
# Positive protection — a legal four-lane snapshot still loads
# =====================================================================

def test_loader_accepts_round10_verified_manifest_all_four_lanes(tmp_path):
    """POSITIVE protection: a legal four-lane snapshot loads and every verified
    manifest value equals the value rebuilt from verified artifacts."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [
        _full_strict_item(), _full_conditional_item(),
        _full_diagnostic_item(), _full_quarantine_item(),
    ])
    rec = load_snapshot(snap_dir)
    assert rec.freeze_status == "frozen"
    assert rec.manifest.build_status == "complete"
    records = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    lane_counts = {}
    for r in records:
        lane_counts[r["lane"]] = lane_counts.get(r["lane"], 0) + 1
    assert rec.manifest.included_strict_count == lane_counts.get("strict", 0)
    assert rec.manifest.conditional_count == lane_counts.get("conditional", 0)
    assert rec.manifest.diagnostic_count == lane_counts.get("diagnostic", 0)
    assert rec.manifest.quarantine_count == lane_counts.get("quarantine", 0)
    assert sum(rec.manifest.source_counts.values()) == len(records)
    manifest = _read_manifest(snap_dir)
    assert rec.manifest.snapshot_hash == manifest["snapshot_hash"]
    # snapshot_id is the rebuilt identity: "snap_" + hash[:12] == dir basename
    assert rec.manifest.snapshot_id == f"snap_{manifest['snapshot_hash'][:12]}"
    assert os.path.basename(snap_dir) == rec.manifest.snapshot_id


# =====================================================================
# Required-field deletion (all 20 frozen fields)
# =====================================================================

@pytest.mark.parametrize("field", _REQUIRED_MANIFEST_FIELDS)
def test_loader_rejects_missing_required_manifest_field(tmp_path, field):
    """Deleting ANY of the 20 frozen required manifest fields must be rejected
    by the real public load_snapshot with manifest_required_field_missing."""
    snap_dir, _ = _build_and_get_dir(tmp_path, [_full_diagnostic_item()])
    load_snapshot(snap_dir)  # legal snapshot loads BEFORE mutation
    manifest = _read_manifest(snap_dir)
    assert field in manifest, f"fixture manifest missing required field {field}"
    del manifest[field]  # only change
    _write_manifest(snap_dir, manifest)
    with pytest.raises(SnapshotHashMismatchError, match="manifest_required_field_missing"):
        load_snapshot(snap_dir)
