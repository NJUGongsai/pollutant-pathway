"""Read-only snapshot loader (§16.5).

``load_snapshot(snapshot_id_or_path, root=None) -> SnapshotRecord`` loads a
frozen immutable snapshot in read-only mode.

Contract (§16.5):
- Requires an explicit snapshot ID or path. Does NOT auto-select "latest".
- Read-only: does NOT modify any snapshot file (verified by mtime check in
  tests).
- Verifies the manifest's ``snapshot_hash`` against a recomputed content hash
  computed from the on-disk artifacts. Rejects on mismatch.
- Rejects incomplete snapshots (``build_status != "complete"``).
- Rejects hash mismatch (tampered files).
- Does NOT modify the snapshot directory.
"""
from __future__ import annotations

import json
import os
from typing import Any

from reaction_agent.config import BuildConfig, get_build_info
from reaction_agent.eligibility.engine import (
    ENGINE_VERSION as ELIGIBILITY_ENGINE_VERSION,
)
from reaction_agent.hashing import canonical_hash
from reaction_agent.schemas.p1_entities import SnapshotManifest, SnapshotRecord
from reaction_agent.snapshot.builder import (
    BUILDER_VERSION,
    _COMPLETE_MARKER,
    _DIAGNOSTIC_INDEX,
    _MANIFEST_FILENAME,
    _PRODUCTION_INDEX,
    _QUARANTINE_INDEX,
    _RECORD_META_FIELDS,
    _RECORDS_FILENAME,
    _build_config_hash,
)


# =====================================================================
# Errors
# =====================================================================

class SnapshotNotFoundError(FileNotFoundError):
    """Snapshot directory or manifest not found."""


class SnapshotIncompleteError(ValueError):
    """Snapshot build_status is not 'complete'."""


class SnapshotHashMismatchError(ValueError):
    """Recomputed content hash does not match stored snapshot_hash."""


# =====================================================================
# Lane authority (§5.3 item 3) — lane is bound into the hashed payload AND
# independently re-derived from the complete eligibility decision, then
# strictly compared. A record whose stored ``lane`` disagrees with the lane
# implied by ``eligibility_decision.eligibility`` is a tamper and is rejected.
# =====================================================================

_ELIGIBILITY_TO_LANE = {
    "strict_eligible": "strict",
    "conditional_eligible": "conditional",
    "strict_prohibited": "diagnostic",
    "quarantine": "quarantine",
}


def _record_reaction_id(record: dict) -> str:
    """Extract the reaction_id from a record (Critical-1 §5.3 nested payload).

    Records persist the complete nested ``reaction_evidence`` object, so the
    reaction_id lives at ``record["reaction_evidence"]["reaction_id"]``.
    """
    ev = record.get("reaction_evidence")
    if isinstance(ev, dict) and "reaction_id" in ev:
        return ev["reaction_id"]
    raise SnapshotHashMismatchError(
        "record missing nested reaction_evidence.reaction_id — the record is "
        "not a complete §5.3 canonical payload (Critical-1 not satisfied)"
    )


def _record_source_name(record: dict) -> str:
    """Extract the source_name from a record's nested reaction_evidence."""
    ev = record.get("reaction_evidence")
    if isinstance(ev, dict) and "source_name" in ev:
        return ev["source_name"]
    raise SnapshotHashMismatchError(
        "record missing nested reaction_evidence.source_name — the record is "
        "not a complete §5.3 canonical payload (Critical-1 not satisfied)"
    )


def _rederive_lane(record: dict) -> str:
    """Re-derive the lane from the complete eligibility decision (§5.3).

    The lane MUST equal the lane implied by ``eligibility_decision.eligibility``.
    An unknown eligibility fails closed to ``quarantine`` (never production).
    """
    decision = record.get("eligibility_decision")
    if not isinstance(decision, dict) or "eligibility" not in decision:
        raise SnapshotHashMismatchError(
            "record missing complete eligibility_decision — cannot re-derive "
            "the lane (Critical-1 not satisfied)"
        )
    return _ELIGIBILITY_TO_LANE.get(decision["eligibility"], "quarantine")


# =====================================================================
# Path resolution
# =====================================================================

def _resolve_snapshot_path(
    snapshot_id_or_path: str,
    root: str | None,
) -> str:
    """Resolve the snapshot directory path from an ID or explicit path.

    §16.5: explicit ID or path required. No auto-latest. Refuses to load
    temp directories (``.tmp_*``) as snapshots (M1 fix).
    """
    if not snapshot_id_or_path or not isinstance(snapshot_id_or_path, str):
        raise SnapshotNotFoundError(
            "explicit snapshot ID or path required (empty/None rejected; "
            "no auto-latest selection)"
        )

    # If it's an existing directory path, use it directly — but reject temp dirs
    if os.path.isdir(snapshot_id_or_path):
        basename = os.path.basename(os.path.normpath(snapshot_id_or_path))
        if basename.startswith(".tmp_"):
            raise SnapshotNotFoundError(
                f"refusing to load temp dir as snapshot: {snapshot_id_or_path} "
                f"(temp dirs are not complete immutable snapshots)"
            )
        return os.path.realpath(snapshot_id_or_path)

    # If it looks like a path (contains os.sep or is absolute), treat as path
    if os.sep in snapshot_id_or_path or os.path.isabs(snapshot_id_or_path):
        raise SnapshotNotFoundError(
            f"snapshot path not found: {snapshot_id_or_path}"
        )

    # Otherwise treat as a snapshot ID under root
    if root is None:
        raise SnapshotNotFoundError(
            f"snapshot ID {snapshot_id_or_path!r} given but no root specified. "
            f"Either pass an explicit path or provide root=."
        )
    # Reject snapshot IDs that look like temp dirs
    if snapshot_id_or_path.startswith(".tmp_"):
        raise SnapshotNotFoundError(
            f"refusing to load temp dir as snapshot: {snapshot_id_or_path}"
        )
    snap_dir = os.path.join(root, snapshot_id_or_path)
    if not os.path.isdir(snap_dir):
        raise SnapshotNotFoundError(
            f"snapshot not found: {snap_dir}"
        )
    return os.path.realpath(snap_dir)


# =====================================================================
# Hash verification
# =====================================================================

def _read_jsonl(path: str) -> list[dict]:
    """Read a JSONL file and return a list of dicts."""
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _recompute_record_hash(record: dict) -> str:
    """Recompute the per-record content hash from the record's fields.

    Critical-1 fix: the loader does NOT trust the stored
    ``record_content_hash``. It recomputes the hash from the COMPLETE record
    content — including participants / mapping_report / source_ledger /
    resolved_lineages — by stripping only the meta fields
    (``_RECORD_META_FIELDS``: lane / record_content_hash / quarantine_reason).
    This detects tampering of ANY nested field (participant provenance,
    mapping pair, ledger unknowns, lineage atom maps, lineage evidence IDs)
    even when the stored hash is left unchanged.

    The field set is exactly ``record.items()`` minus ``_RECORD_META_FIELDS``,
    which mirrors the builder's ``_canonical_record_payload`` (§3.2 — builder
    and loader hash the same object).
    """
    payload = {
        k: v for k, v in record.items()
        if k not in _RECORD_META_FIELDS
    }
    return canonical_hash(payload)


def _canonical_payload_of(record: dict) -> dict:
    """Return the canonical payload of a stored record / index entry.

    Strips exactly the meta fields (``_RECORD_META_FIELDS``) so the result is
    directly comparable to the builder's ``_canonical_record_payload``. Used
    by the index-partition validator for exact entry == full-record equality.
    """
    return {
        k: v for k, v in record.items()
        if k not in _RECORD_META_FIELDS
    }


def _validate_index_partition(
    all_records: list[dict],
    production_records: list[dict],
    diagnostic_records: list[dict],
    quarantine_records: list[dict],
) -> None:
    """Validate the Round 8 index partition contract (§R8-7).

    ``records.jsonl`` is the complete record authority. The three indexes must
    form an EXACT, COMPLETE, UNIQUE, PAIRWISE-DISJOINT partition:

        strict / conditional   -> production_index exactly once
        diagnostic             -> diagnostic_index exactly once
        quarantine             -> quarantine_index exactly once

    Every index entry must (a) rehash to its OWN stored record_content_hash,
    (b) agree with the full record's stored hash, and (c) equal the full
    record's canonical payload. The loader NEVER trusts an index entry's
    self-reported hash — a hash-coherent but semantically wrong partition, a
    missing diagnostic member, or a mutated nested index payload all fail
    closed. Runs BEFORE the snapshot hash verdict in ``load_snapshot``.

    Raises ``SnapshotHashMismatchError`` with a stable reason token
    (Round 8 §8.1):

        index_record_duplicate        duplicate reaction_id in records.jsonl
        index_entry_duplicate         duplicate reaction_id within one index
        index_entry_hash_mismatch     entry stored hash disagrees with full record
        index_entry_content_mismatch  entry payload rehash/payload differs
        index_partition_wrong_lane    entry lane not allowed in its index
        index_partition_missing       expected member absent
        index_partition_unexpected    member without records authority / extra
        index_partition_overlap       reaction_id in more than one index
    """

    def _reject(token: str, message: str) -> None:
        raise SnapshotHashMismatchError(f"{token}: {message}")

    # 1. records.jsonl reaction_id uniqueness
    record_ids: list[str] = []
    for rec in all_records:
        rid = _record_reaction_id(rec)
        if rid in record_ids:
            _reject("index_record_duplicate",
                    f"records.jsonl contains reaction_id {rid!r} more than once")
        record_ids.append(rid)
    records_by_id: dict[str, dict] = {
        _record_reaction_id(rec): rec for rec in all_records
    }

    # 2. per-index entry validation (uniqueness + lane + rehash + exact equality)
    partition_specs = [
        (production_records, _PRODUCTION_INDEX, {"strict", "conditional"}),
        (diagnostic_records, _DIAGNOSTIC_INDEX, {"diagnostic"}),
        (quarantine_records, _QUARANTINE_INDEX, {"quarantine"}),
    ]
    actual_ids: dict[str, list[str]] = {
        _PRODUCTION_INDEX: [], _DIAGNOSTIC_INDEX: [], _QUARANTINE_INDEX: [],
    }
    for index_records, index_name, allowed_lanes in partition_specs:
        seen: list[str] = []
        for entry in index_records:
            rid = _record_reaction_id(entry)
            if rid in seen:
                _reject("index_entry_duplicate",
                        f"{index_name} contains reaction_id {rid!r} more than once")
            seen.append(rid)
            full = records_by_id.get(rid)
            if full is None:
                _reject("index_partition_unexpected",
                        f"{index_name} entry {rid!r} has no records.jsonl authority")
            entry_lane = entry.get("lane")
            if entry_lane not in allowed_lanes:
                _reject("index_partition_wrong_lane",
                        f"{index_name} entry {rid!r} lane={entry_lane!r} not allowed "
                        f"in {index_name} (allowed={sorted(allowed_lanes)})")
            if entry.get("record_content_hash") != full.get("record_content_hash"):
                _reject("index_entry_hash_mismatch",
                        f"{index_name} entry {rid!r} stored record_content_hash "
                        f"disagrees with records.jsonl")
            entry_recomputed = _recompute_record_hash(entry)
            if entry_recomputed != entry.get("record_content_hash"):
                _reject("index_entry_content_mismatch",
                        f"{index_name} entry {rid!r} payload rehash "
                        f"{entry_recomputed} != stored {entry.get('record_content_hash')}")
            if _canonical_payload_of(entry) != _canonical_payload_of(full):
                _reject("index_entry_content_mismatch",
                        f"{index_name} entry {rid!r} canonical payload differs from "
                        f"the records.jsonl full record")
        actual_ids[index_name] = seen

    # 3. expected partition rebuilt from records lanes
    expected_ids: dict[str, list[str]] = {
        _PRODUCTION_INDEX: [], _DIAGNOSTIC_INDEX: [], _QUARANTINE_INDEX: [],
    }
    for rec in all_records:
        rid = _record_reaction_id(rec)
        lane = rec.get("lane")
        if lane in ("strict", "conditional"):
            expected_ids[_PRODUCTION_INDEX].append(rid)
        elif lane == "diagnostic":
            expected_ids[_DIAGNOSTIC_INDEX].append(rid)
        elif lane == "quarantine":
            expected_ids[_QUARANTINE_INDEX].append(rid)
        else:
            _reject("index_partition_wrong_lane",
                    f"record {rid!r} has unknown lane {lane!r}")

    # 4. exact completeness: expected == actual for every index
    for index_name in (_PRODUCTION_INDEX, _DIAGNOSTIC_INDEX, _QUARANTINE_INDEX):
        expected_set = set(expected_ids[index_name])
        actual_set = set(actual_ids[index_name])
        missing = expected_set - actual_set
        unexpected = actual_set - expected_set
        if missing:
            _reject("index_partition_missing",
                    f"{index_name} missing expected member(s): {sorted(missing)}")
        if unexpected:
            _reject("index_partition_unexpected",
                    f"{index_name} unexpected member(s): {sorted(unexpected)}")

    # 5. pairwise disjointness
    prod_ids = set(actual_ids[_PRODUCTION_INDEX])
    diag_ids = set(actual_ids[_DIAGNOSTIC_INDEX])
    quar_ids = set(actual_ids[_QUARANTINE_INDEX])
    overlaps = [
        ("production", "diagnostic", prod_ids & diag_ids),
        ("production", "quarantine", prod_ids & quar_ids),
        ("diagnostic", "quarantine", diag_ids & quar_ids),
    ]
    for name_a, name_b, overlap in overlaps:
        if overlap:
            _reject("index_partition_overlap",
                    f"{name_a} ∩ {name_b} overlap: {sorted(overlap)}")


# =====================================================================
# Round 9 — manifest authority (§R9-6)
#
# The on-disk manifest is the snapshot's audit envelope. Its authority fields
# MUST be present with the correct type and MUST equal the value rebuilt from
# verified artifacts (records / indexes / canonical hash). A missing required
# field, a wrong-type field, a forged snapshot_id, a tampered count, a forged
# record-hash list, a forged index hash, a forged source summary, or a forged
# failure summary all fail closed with a stable ``manifest_*`` /
# ``snapshot_identity_mismatch`` reason token — never a generic stored/
# recomputed hash mismatch.
# =====================================================================

# Required on-disk manifest authority fields (§R9-6.1). Presence + type are
# enforced BEFORE any hash recomputation; the value checks happen against the
# verified artifacts in _validate_manifest_authority.
_REQUIRED_MANIFEST_FIELDS: dict[str, type] = {
    "snapshot_id": str,
    "schema_version": str,
    "included_strict_count": int,
    "conditional_count": int,
    "diagnostic_count": int,
    "quarantine_count": int,
    "build_status": str,
    "snapshot_hash": str,
    "build_id": str,
    "source_counts": dict,
    "policy_version": str,
    "record_count": int,
    "versions": dict,
    "source_files": dict,
    "failure_counts_by_reason": dict,
    "record_content_hashes": list,
    "production_index_hash": str,
    "diagnostic_index_hash": str,
    "quarantine_index_hash": str,
    "build_config_hash": str,
}


def _validate_manifest_required_fields(manifest: dict) -> None:
    """Required-field presence + exact-type checks (§R9-6.1 / Round 10 §R10-1.2).

    A missing required field fails closed with ``manifest_required_field_missing``
    (never skipped via ``.get()``); a wrong type fails closed with
    ``manifest_field_type_invalid``.

    Round 10: the type check uses the JSON exact top-level type
    (``type(value) is expected_type``), NOT ``isinstance`` — JSON booleans are
    instances of ``int`` in Python (``isinstance(True, int)`` is True), so
    ``record_count=true`` / ``diagnostic_count=false`` must be rejected, never
    accepted as the int 0/1.
    """
    for field, expected_type in _REQUIRED_MANIFEST_FIELDS.items():
        if field not in manifest:
            raise SnapshotHashMismatchError(
                f"manifest_required_field_missing: {field}")
        if type(manifest[field]) is not expected_type:
            raise SnapshotHashMismatchError(
                f"manifest_field_type_invalid: {field} expected "
                f"{expected_type.__name__} got {type(manifest[field]).__name__}")


def _validate_manifest_nested_types(manifest: dict) -> None:
    """Recursive shape/type checks on nested manifest authority fields
    (Round 10 §R10-1.3).

    JSON booleans are instances of ``int`` in Python (``isinstance(True, int)``
    is True) and ``1.0`` compares equal to ``1``, so a bare ``isinstance`` /
    equality check would accept ``true`` / ``1.0`` as a count. These shape
    checks require the JSON exact top-level type and fail closed with
    ``manifest_field_type_invalid``:

        source_counts            = dict[str, exact int >= 0]
        failure_counts_by_reason = dict[str, exact int >= 0]
        source_files             = dict[str, non-empty str]
        versions                 = dict[str, non-empty str]
        record_content_hashes    = list[non-empty str]
    """
    _validate_nested_int_dict(manifest, "source_counts")
    _validate_nested_int_dict(manifest, "failure_counts_by_reason")
    _validate_nested_str_dict(manifest, "source_files")
    _validate_nested_str_dict(manifest, "versions")
    _validate_nested_str_list(manifest, "record_content_hashes")


def _validate_nested_int_dict(manifest: dict, field: str) -> None:
    """Require ``field`` to be ``dict[str, exact int >= 0]`` (§R10-1.3)."""
    value = manifest[field]
    if type(value) is not dict:
        raise SnapshotHashMismatchError(
            f"manifest_field_type_invalid: {field} expected dict got "
            f"{type(value).__name__}")
    for key, item in value.items():
        if type(item) is not int:
            raise SnapshotHashMismatchError(
                f"manifest_field_type_invalid: {field}[{key!r}] expected "
                f"exact int got {type(item).__name__}")
        if item < 0:
            raise SnapshotHashMismatchError(
                f"manifest_field_type_invalid: {field}[{key!r}] must be "
                f">= 0, got {item}")


def _validate_nested_str_dict(manifest: dict, field: str) -> None:
    """Require ``field`` to be ``dict[str, non-empty str]`` (§R10-1.3)."""
    value = manifest[field]
    if type(value) is not dict:
        raise SnapshotHashMismatchError(
            f"manifest_field_type_invalid: {field} expected dict got "
            f"{type(value).__name__}")
    for key, item in value.items():
        if type(item) is not str or not item.strip():
            raise SnapshotHashMismatchError(
                f"manifest_field_type_invalid: {field}[{key!r}] expected "
                f"non-empty str got {type(item).__name__}")


def _validate_nested_str_list(manifest: dict, field: str) -> None:
    """Require ``field`` to be ``list[non-empty str]`` (§R10-1.3)."""
    value = manifest[field]
    if type(value) is not list:
        raise SnapshotHashMismatchError(
            f"manifest_field_type_invalid: {field} expected list got "
            f"{type(value).__name__}")
    for index, item in enumerate(value):
        if type(item) is not str or not item.strip():
            raise SnapshotHashMismatchError(
                f"manifest_field_type_invalid: {field}[{index}] expected "
                f"non-empty str got {type(item).__name__}")


def _validate_manifest_authority(
    *,
    manifest: dict,
    snap_dir: str,
    recomputed_snapshot_hash: str,
    records: list[dict],
    production_records: list[dict],
    diagnostic_records: list[dict],
    quarantine_records: list[dict],
) -> dict:
    """Verify the on-disk manifest against values rebuilt from VERIFIED
    artifacts (§R9-6.2–6.7) and return a verified SnapshotManifest field dict.

    Runs after: required-field/type checks, the COMPLETE marker check, the
    Round 8 index-partition validator, and the canonical snapshot hash
    recomputation. Fails closed (``SnapshotHashMismatchError``) on any of:

        snapshot hash != recomputed        (identity)
        snapshot_id != snap_+hash[:12]     (snapshot_identity_mismatch)
        snapshot_id != dir basename        (snapshot_identity_mismatch)
        record_count / lane counts wrong   (manifest_count_mismatch)
        record_content_hashes wrong        (manifest_record_hashes_mismatch)
        production/diagnostic/quarantine   (manifest_index_hash_mismatch)
            index hash wrong
        source_counts wrong                (manifest_source_counts_mismatch)
        source_files wrong                 (manifest_source_hash_mismatch)
        failure_counts_by_reason wrong     (manifest_failure_counts_mismatch)

    The returned dict contains ONLY values that passed cross-verification —
    the downstream ``SnapshotManifest`` is built from it, never from raw
    manifest values (§R9-6.8).
    """
    # --- identity (§R9-6.2) ---
    stored_hash = manifest["snapshot_hash"]
    if stored_hash != recomputed_snapshot_hash:
        raise SnapshotHashMismatchError(
            f"snapshot hash mismatch for {manifest['snapshot_id']}: "
            f"stored={stored_hash} recomputed={recomputed_snapshot_hash}. "
            f"Snapshot may have been tampered."
        )
    snap_basename = os.path.basename(os.path.normpath(snap_dir))
    expected_snapshot_id = f"snap_{stored_hash[:12]}"
    if manifest["snapshot_id"] != expected_snapshot_id:
        raise SnapshotHashMismatchError(
            f"snapshot_identity_mismatch: manifest snapshot_id="
            f"{manifest['snapshot_id']} expected={expected_snapshot_id} "
            f"(derived from snapshot_hash)")
    if manifest["snapshot_id"] != snap_basename:
        raise SnapshotHashMismatchError(
            f"snapshot_identity_mismatch: manifest snapshot_id="
            f"{manifest['snapshot_id']} != resolved directory basename "
            f"{snap_basename}")

    # --- counts (§R9-6.3) ---
    lane_counts = {
        "strict": sum(1 for r in records if r.get("lane") == "strict"),
        "conditional": sum(1 for r in records if r.get("lane") == "conditional"),
        "diagnostic": sum(1 for r in records if r.get("lane") == "diagnostic"),
        "quarantine": sum(1 for r in records if r.get("lane") == "quarantine"),
    }
    record_count = len(records)
    if manifest["record_count"] != record_count:
        raise SnapshotHashMismatchError(
            f"manifest_count_mismatch: record_count manifest="
            f"{manifest['record_count']} verified={record_count}")
    if sum(lane_counts.values()) != record_count:
        raise SnapshotHashMismatchError(
            f"manifest_count_mismatch: sum(lane_counts)="
            f"{sum(lane_counts.values())} != record_count={record_count}")
    for field, lane in (("included_strict_count", "strict"),
                        ("conditional_count", "conditional"),
                        ("diagnostic_count", "diagnostic"),
                        ("quarantine_count", "quarantine")):
        if manifest[field] != lane_counts[lane]:
            raise SnapshotHashMismatchError(
                f"manifest_count_mismatch: {field} manifest="
                f"{manifest[field]} verified={lane_counts[lane]}")

    # --- record hash list (§R9-6.4) ---
    verified_record_hashes = sorted(r["record_content_hash"] for r in records)
    if manifest["record_content_hashes"] != verified_record_hashes:
        raise SnapshotHashMismatchError(
            f"manifest_record_hashes_mismatch: manifest list length "
            f"{len(manifest['record_content_hashes'])} != verified length "
            f"{len(verified_record_hashes)}")

    # --- index hashes (§R9-6.5) ---
    index_checks = [
        ("production_index_hash", production_records),
        ("diagnostic_index_hash", diagnostic_records),
        ("quarantine_index_hash", quarantine_records),
    ]
    for field, index_records in index_checks:
        verified_index_hash = canonical_hash(
            sorted(r["record_content_hash"] for r in index_records))
        if manifest[field] != verified_index_hash:
            raise SnapshotHashMismatchError(
                f"manifest_index_hash_mismatch: {field} manifest="
                f"{manifest[field]} verified={verified_index_hash}")

    # --- source summaries (§R9-6.6) ---
    src_counts: dict[str, int] = {}
    src_buckets: dict[str, list[str]] = {}
    for r in records:
        src = _record_source_name(r)
        src_counts[src] = src_counts.get(src, 0) + 1
        src_buckets.setdefault(src, []).append(r["record_content_hash"])
    if manifest["record_count"] != sum(src_counts.values()):
        raise SnapshotHashMismatchError(
            f"manifest_source_counts_mismatch: sum(source_counts)="
            f"{sum(src_counts.values())} != record_count={manifest['record_count']}")
    if manifest["source_counts"] != dict(sorted(src_counts.items())):
        raise SnapshotHashMismatchError(
            f"manifest_source_counts_mismatch: manifest="
            f"{manifest['source_counts']} verified="
            f"{dict(sorted(src_counts.items()))}")
    verified_source_files = {
        src: canonical_hash(sorted(hashes)) for src, hashes in src_buckets.items()
    }
    if set(manifest["source_files"]) != set(src_counts):
        raise SnapshotHashMismatchError(
            f"manifest_source_hash_mismatch: source key set manifest="
            f"{sorted(manifest['source_files'])} verified={sorted(src_counts)}")
    if manifest["source_files"] != dict(sorted(verified_source_files.items())):
        raise SnapshotHashMismatchError(
            f"manifest_source_hash_mismatch: manifest="
            f"{manifest['source_files']} verified="
            f"{dict(sorted(verified_source_files.items()))}")

    # --- failure summaries (§R9-6.7) ---
    failure_counts: dict[str, int] = {}
    for r in records:
        if r.get("lane") in ("diagnostic", "quarantine"):
            decision = r.get("eligibility_decision")
            if not isinstance(decision, dict) or "reason" not in decision:
                raise SnapshotHashMismatchError(
                    f"record {_record_reaction_id(r)} missing "
                    f"eligibility_decision.reason — cannot rebuild failure "
                    f"summaries")
            reason = decision["reason"]
            key = reason[:60] if len(reason) > 60 else reason
            failure_counts[key] = failure_counts.get(key, 0) + 1
    if manifest["failure_counts_by_reason"] != dict(sorted(failure_counts.items())):
        raise SnapshotHashMismatchError(
            f"manifest_failure_counts_mismatch: manifest="
            f"{manifest['failure_counts_by_reason']} verified="
            f"{dict(sorted(failure_counts.items()))}")

    # --- verified SnapshotManifest field set (§R9-6.8 / Round 10 §R10-1.4) ---
    # Return the REBUILT values, never raw manifest echoes, for every field
    # that can be rebuilt from verified artifacts:
    #   snapshot_id            ← expected_snapshot_id
    #   snapshot_hash          ← recomputed_snapshot_hash
    #   included_strict_count  ← rebuilt lane_counts["strict"]
    #   conditional_count      ← rebuilt lane_counts["conditional"]
    #   diagnostic_count       ← rebuilt lane_counts["diagnostic"]
    #   quarantine_count       ← rebuilt lane_counts["quarantine"]
    #   build_status           ← verified literal "complete"
    #   source_counts          ← rebuilt sorted source counts
    # The trust-root fields that cannot be rebuilt from records/indexes but ARE
    # protected by the canonical snapshot hash (schema_version / build_id /
    # policy_version / build_config_hash) are returned from the manifest after
    # strict type + hash verification.
    return {
        "snapshot_id": expected_snapshot_id,
        "schema_version": manifest["schema_version"],
        "included_strict_count": lane_counts["strict"],
        "conditional_count": lane_counts["conditional"],
        "diagnostic_count": lane_counts["diagnostic"],
        "quarantine_count": lane_counts["quarantine"],
        "build_status": "complete",
        "snapshot_hash": recomputed_snapshot_hash,
        "build_id": manifest["build_id"],
        "source_counts": dict(sorted(src_counts.items())),
        "policy_version": manifest["policy_version"],
        "build_config_hash": manifest["build_config_hash"],
    }


def _recompute_snapshot_hash(manifest: dict, snap_dir: str) -> str:
    """Recompute the canonical snapshot content hash from on-disk artifacts.

    §16.6: EXCLUDES timestamp, temp path, run ID. Uses only the content fields
    that were part of the original canonical content.

    H2 fix: per-record hashes are RECOMPUTED from record fields, not trusted
    from the stored ``record_content_hash`` field. This detects content
    tampering even when the stored hash is left unchanged.
    """
    # Read back the index files
    production_records = _read_jsonl(os.path.join(snap_dir, _PRODUCTION_INDEX))
    diagnostic_records = _read_jsonl(os.path.join(snap_dir, _DIAGNOSTIC_INDEX))
    quarantine_records = _read_jsonl(os.path.join(snap_dir, _QUARANTINE_INDEX))
    all_records = _read_jsonl(os.path.join(snap_dir, _RECORDS_FILENAME))

    # H2 fix: recompute each record's hash from its fields and verify against
    # the stored value. Reject on mismatch (tamper detection). The recomputed
    # payload includes the COMPLETE nested reaction_evidence / source_ledger /
    # resolved_lineages / eligibility_decision / quarantine_record / lane
    # (Critical-1 §5.3), so a mutation of ANY nested scientific field is caught.
    for r in all_records:
        stored_rch = r.get("record_content_hash")
        if stored_rch is None:
            raise SnapshotHashMismatchError(
                f"record {_record_reaction_id(r)} missing "
                f"record_content_hash field"
            )
        recomputed_rch = _recompute_record_hash(r)
        if recomputed_rch != stored_rch:
            raise SnapshotHashMismatchError(
                f"record {_record_reaction_id(r)} content hash mismatch: "
                f"stored={stored_rch} recomputed={recomputed_rch}. "
                f"Record content may have been tampered."
            )
        # §5.3 item 3: lane is independently re-derived from the complete
        # eligibility decision and strictly compared. A stored lane that
        # disagrees with eligibility_decision.eligibility is a tamper.
        rederived_lane = _rederive_lane(r)
        if r.get("lane") != rederived_lane:
            raise SnapshotHashMismatchError(
                f"record {_record_reaction_id(r)} lane={r.get('lane')!r} "
                f"disagrees with lane re-derived from "
                f"eligibility_decision.eligibility={rederived_lane!r}. "
                f"Lane/decision disagreement is a tamper."
            )

    # Critical-1 §3.3: index integrity — every production/diagnostic/quarantine
    # index entry must reference an existing full record in records.jsonl, and
    # its lane + record_content_hash must match the full record. This catches
    # dangling references and lane/hash disagreements that a hash-only check
    # would miss (e.g. an entry whose reaction_id is swapped to a dangling id
    # while keeping the same record_content_hash).
    records_by_id: dict[str, dict] = {
        _record_reaction_id(r): r for r in all_records
    }
    for index_records, index_name in (
        (production_records, _PRODUCTION_INDEX),
        (diagnostic_records, _DIAGNOSTIC_INDEX),
        (quarantine_records, _QUARANTINE_INDEX),
    ):
        for entry in index_records:
            rid = _record_reaction_id(entry)
            full = records_by_id.get(rid)
            if full is None:
                raise SnapshotHashMismatchError(
                    f"{index_name} entry reaction_id {rid!r} not found in "
                    f"records.jsonl (dangling reference)"
                )
            if entry.get("lane") != full.get("lane"):
                raise SnapshotHashMismatchError(
                    f"{index_name} entry {rid!r} lane={entry.get('lane')!r} "
                    f"disagrees with records lane={full.get('lane')!r}"
                )
            if entry.get("record_content_hash") != full.get("record_content_hash"):
                raise SnapshotHashMismatchError(
                    f"{index_name} entry {rid!r} record_content_hash disagrees "
                    f"with records.jsonl"
                )

    # Use the VERIFIED stored hashes (now confirmed to match recomputed)
    record_hashes = sorted(r["record_content_hash"] for r in all_records)
    production_hashes = sorted(r["record_content_hash"] for r in production_records)
    diagnostic_hashes = sorted(r["record_content_hash"] for r in diagnostic_records)
    quarantine_hashes = sorted(r["record_content_hash"] for r in quarantine_records)

    production_index_hash = canonical_hash(production_hashes)
    # Round 8: the diagnostic index is bound into the immutable snapshot
    # integrity — deleting/adding/modifying a diagnostic member changes the
    # recomputed hash even when records.jsonl is untouched (R8-02 closed).
    diagnostic_index_hash = canonical_hash(diagnostic_hashes)
    quarantine_index_hash = canonical_hash(quarantine_hashes)

    # Rebuild the canonical content (must match builder._compute_canonical_snapshot_content)
    strict_count = sum(1 for r in all_records if r["lane"] == "strict")
    conditional_count = sum(1 for r in all_records if r["lane"] == "conditional")
    diagnostic_count = sum(1 for r in all_records if r["lane"] == "diagnostic")
    quarantine_count = sum(1 for r in all_records if r["lane"] == "quarantine")

    # Rebuild source content hashes from stored records
    by_source: dict[str, list[str]] = {}
    for r in all_records:
        src = _record_source_name(r)
        by_source.setdefault(src, []).append(r["record_content_hash"])
    source_hashes = {
        src: canonical_hash(sorted(hashes)) for src, hashes in by_source.items()
    }

    canonical = {
        "schema_version": manifest["schema_version"],
        "build_config_hash": manifest["build_config_hash"],
        "versions": manifest["versions"],
        "source_content_hashes": dict(sorted(source_hashes.items())),
        "record_count": len(all_records),
        "counts": {
            "strict": strict_count,
            "conditional": conditional_count,
            "diagnostic": diagnostic_count,
            "quarantine": quarantine_count,
        },
        "record_content_hashes": record_hashes,
        "production_index_hash": production_index_hash,
        "diagnostic_index_hash": diagnostic_index_hash,
        "quarantine_index_hash": quarantine_index_hash,
        "policy_version": manifest["policy_version"],
    }
    return canonical_hash(canonical)


# =====================================================================
# Public API: load_snapshot
# =====================================================================

def load_snapshot(
    snapshot_id_or_path: str,
    *,
    root: str | None = None,
) -> SnapshotRecord:
    """Load a frozen immutable snapshot in read-only mode (§16.5).

    Contract:
    - Requires explicit snapshot ID or path. No auto-latest.
    - Read-only: does NOT modify any file.
    - Verifies ``snapshot_hash`` against recomputed content hash.
    - Rejects incomplete snapshots (``build_status != "complete"``).
    - Rejects hash mismatch (tampered files).

    Args:
        snapshot_id_or_path: Snapshot ID (resolved under ``root``) or an
            explicit directory path.
        root: Root directory for snapshot ID resolution. Required if
            ``snapshot_id_or_path`` is an ID, not a path.

    Returns:
        SnapshotRecord with manifest, evidence IDs, and resource paths.

    Raises:
        SnapshotNotFoundError: path/ID not found, or empty/None input.
        SnapshotIncompleteError: build_status != "complete".
        SnapshotHashMismatchError: recomputed hash != stored hash.
    """
    snap_dir = _resolve_snapshot_path(snapshot_id_or_path, root)

    # Read manifest (read-only — open "r", never "w" or "a")
    manifest_path = os.path.join(snap_dir, _MANIFEST_FILENAME)
    if not os.path.exists(manifest_path):
        raise SnapshotNotFoundError(f"manifest.json not found: {manifest_path}")

    with open(manifest_path, encoding="utf-8") as f:
        manifest: Any = json.load(f)

    # Round 10 §R10-1.1: confirm the parsed manifest is a JSON object. A
    # non-object manifest (list / string / number / null) must fail closed with
    # manifest_field_type_invalid — never reach .get() and raise AttributeError.
    if type(manifest) is not dict:
        raise SnapshotHashMismatchError(
            f"manifest_field_type_invalid: manifest must be a JSON object, "
            f"got {type(manifest).__name__}")

    # Round 10 §R10-1.2: build_status is gated BEFORE the full required-field
    # scan so a partial/building snapshot (which legitimately lacks other
    # authority fields) still yields SnapshotIncompleteError — the preserved
    # §16.5 contract — while a missing or wrong-typed build_status now fails
    # closed with a stable token instead of being silently defaulted to
    # "unknown" or compared as a non-str.
    if "build_status" not in manifest:
        raise SnapshotHashMismatchError(
            "manifest_required_field_missing: build_status")
    if type(manifest["build_status"]) is not str:
        raise SnapshotHashMismatchError(
            f"manifest_field_type_invalid: build_status expected str got "
            f"{type(manifest['build_status']).__name__}")

    # §16.5: reject incomplete snapshots (interpret build_status).
    if manifest["build_status"] != "complete":
        raise SnapshotIncompleteError(
            f"snapshot {manifest.get('snapshot_id', '?')} is not complete "
            f"(build_status={manifest['build_status']!r}). Loader rejects "
            f"incomplete snapshots."
        )

    # Round 9 §R9-6.1: required-field presence + exact-type checks FIRST — a
    # missing required field fails closed with a specific token (never skipped
    # via .get()), and the trust-root fields used by the recompute below
    # (schema_version / build_config_hash / versions / policy_version) are
    # guaranteed present.
    _validate_manifest_required_fields(manifest)

    # Round 10 §R10-1.3: recursive shape/type checks on the nested manifest
    # authority fields (source_counts / failure_counts_by_reason / source_files
    # / versions / record_content_hashes) — run before any hash recompute so a
    # bool/float-in-count or a non-str nested value fails closed with
    # manifest_field_type_invalid, not a generic stored/recomputed hash mismatch.
    _validate_manifest_nested_types(manifest)

    stored_hash = manifest["snapshot_hash"]

    # §16.5: verify COMPLETE marker exists AND its content cross-verifies the
    # manifest snapshot_hash (I1 fix — closes the M2 trust-root weakness).
    # The builder writes snapshot_hash into the COMPLETE marker file
    # independently of the manifest. An attacker who tampers both
    # manifest["snapshot_hash"] and the trust-root fields (schema_version /
    # build_config_hash / versions / policy_version) cannot forge the marker
    # without knowing the correct snapshot_hash at marker-write time. The
    # marker is an independent second source of truth.
    marker_path = os.path.join(snap_dir, _COMPLETE_MARKER)
    if not os.path.exists(marker_path):
        raise SnapshotIncompleteError(
            f"COMPLETE marker missing in {snap_dir}. Snapshot may be partially "
            f"written."
        )
    with open(marker_path, encoding="utf-8") as f:
        marker_hash = f.read().strip()
    if not marker_hash:
        raise SnapshotIncompleteError(
            f"COMPLETE marker empty in {snap_dir}. Snapshot may be partially "
            f"written."
        )
    if marker_hash != stored_hash:
        raise SnapshotHashMismatchError(
            f"COMPLETE marker hash mismatch for "
            f"{manifest.get('snapshot_id', '?')}: marker={marker_hash} "
            f"manifest={stored_hash}. Snapshot may have been tampered."
        )

    # Round 8: validate the index partition contract BEFORE the snapshot hash
    # verdict (§R8-7/§R8-8.3). This rejects hash-coherent-but-semantically-wrong
    # partitions (diagnostic/quarantine leaked into production), a missing
    # diagnostic member, a duplicate record/index entry, a cross-index member,
    # and a mutated nested index payload — with a stable ``index_*`` reason
    # token, NOT a generic stored/recomputed hash mismatch.
    all_records = _read_jsonl(os.path.join(snap_dir, _RECORDS_FILENAME))
    production_records = _read_jsonl(os.path.join(snap_dir, _PRODUCTION_INDEX))
    diagnostic_records = _read_jsonl(os.path.join(snap_dir, _DIAGNOSTIC_INDEX))
    quarantine_records = _read_jsonl(os.path.join(snap_dir, _QUARANTINE_INDEX))
    _validate_index_partition(
        all_records, production_records, diagnostic_records, quarantine_records,
    )

    # §16.5: verify snapshot_hash against recomputed content hash
    try:
        recomputed_hash = _recompute_snapshot_hash(manifest, snap_dir)
    except (KeyError, json.JSONDecodeError, OSError) as e:
        # Any artifact read error → hash verification cannot succeed → reject
        raise SnapshotHashMismatchError(
            f"cannot recompute hash for {manifest.get('snapshot_id', '?')}: "
            f"{e}. Snapshot may have been tampered."
        ) from e

    # Round 9 §R9-6: verify the manifest authority against the VERIFIED
    # artifacts (records / indexes / canonical hash) and obtain the verified
    # SnapshotManifest field set. This replaces the Round 8 per-field
    # diagnostic_index_hash cross-check with a full manifest envelope audit:
    # identity (snapshot_id / snapshot hash), counts, record hash list, the
    # three index hashes, source summaries, and failure summaries all fail
    # closed with a manifest-specific token.
    verified = _validate_manifest_authority(
        manifest=manifest,
        snap_dir=snap_dir,
        recomputed_snapshot_hash=recomputed_hash,
        records=all_records,
        production_records=production_records,
        diagnostic_records=diagnostic_records,
        quarantine_records=quarantine_records,
    )

    # Build SnapshotManifest (T2 contract) from VERIFIED values only — never
    # from raw manifest values without cross-verification (§R9-6.8).
    t2_manifest = SnapshotManifest(
        snapshot_id=verified["snapshot_id"],
        schema_version=verified["schema_version"],
        included_strict_count=verified["included_strict_count"],
        conditional_count=verified["conditional_count"],
        diagnostic_count=verified["diagnostic_count"],
        quarantine_count=verified["quarantine_count"],
        build_status=verified["build_status"],
        snapshot_hash=verified["snapshot_hash"],
        build_id=verified["build_id"],
        source_counts=verified["source_counts"],
        policy_version=verified["policy_version"],
    )

    # Collect evidence IDs from records file (Critical-1 §5.3 nested payload)
    evidence_ids = sorted(_record_reaction_id(r) for r in all_records)

    # Build resource paths (read-only references — no modification)
    resources = {
        "manifest": os.path.join(snap_dir, _MANIFEST_FILENAME),
        "production_index": os.path.join(snap_dir, _PRODUCTION_INDEX),
        "diagnostic_index": os.path.join(snap_dir, _DIAGNOSTIC_INDEX),
        "quarantine_index": os.path.join(snap_dir, _QUARANTINE_INDEX),
        "records": os.path.join(snap_dir, _RECORDS_FILENAME),
    }

    return SnapshotRecord(
        snapshot_id=verified["snapshot_id"],
        manifest=t2_manifest,
        reaction_evidence_ids=evidence_ids,
        build_config_hash=verified["build_config_hash"],
        freeze_status="frozen",
        resources=resources,
    )
