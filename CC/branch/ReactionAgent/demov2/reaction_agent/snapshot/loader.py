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

    H2 fix: the loader does NOT trust the stored ``record_content_hash``
    field. It recomputes the hash from the record's content fields and
    compares. This detects tampering where an attacker modifies content
    fields but leaves the stored hash unchanged.
    """
    payload = {
        "reaction_id": record["reaction_id"],
        "source_record_id": record["source_record_id"],
        "source_name": record["source_name"],
        "source_version": record["source_version"],
        "normalized_reaction": record["normalized_reaction"],
        "raw_reaction": record["raw_reaction"],
        "direction": record["direction"],
        "decision_id": record["decision_id"],
        "eligibility": record["eligibility"],
        "evaluation_bucket": record["evaluation_bucket"],
        "quarantine_behavior": record["quarantine_behavior"],
        "reason": record["reason"],
        "quarantine_record_id": record.get("quarantine_record_id"),
    }
    return canonical_hash(payload)


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
    # the stored value. Reject on mismatch (tamper detection).
    for r in all_records:
        stored_rch = r.get("record_content_hash")
        if stored_rch is None:
            raise SnapshotHashMismatchError(
                f"record {r.get('reaction_id', '?')} missing "
                f"record_content_hash field"
            )
        recomputed_rch = _recompute_record_hash(r)
        if recomputed_rch != stored_rch:
            raise SnapshotHashMismatchError(
                f"record {r['reaction_id']} content hash mismatch: "
                f"stored={stored_rch} recomputed={recomputed_rch}. "
                f"Record content may have been tampered."
            )

    # Use the VERIFIED stored hashes (now confirmed to match recomputed)
    record_hashes = sorted(r["record_content_hash"] for r in all_records)
    production_hashes = sorted(r["record_content_hash"] for r in production_records)
    quarantine_hashes = sorted(r["record_content_hash"] for r in quarantine_records)

    production_index_hash = canonical_hash(production_hashes)
    quarantine_index_hash = canonical_hash(quarantine_hashes)

    # Rebuild the canonical content (must match builder._compute_canonical_snapshot_content)
    strict_count = sum(1 for r in all_records if r["lane"] == "strict")
    conditional_count = sum(1 for r in all_records if r["lane"] == "conditional")
    diagnostic_count = sum(1 for r in all_records if r["lane"] == "diagnostic")
    quarantine_count = sum(1 for r in all_records if r["lane"] == "quarantine")

    # Rebuild source content hashes from stored records
    by_source: dict[str, list[str]] = {}
    for r in all_records:
        src = r["source_name"]
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
        manifest: dict[str, Any] = json.load(f)

    # §16.5: reject incomplete snapshots
    build_status = manifest.get("build_status", "unknown")
    if build_status != "complete":
        raise SnapshotIncompleteError(
            f"snapshot {manifest.get('snapshot_id', '?')} is not complete "
            f"(build_status={build_status!r}). Loader rejects incomplete snapshots."
        )

    # §16.5: verify COMPLETE marker exists
    marker_path = os.path.join(snap_dir, _COMPLETE_MARKER)
    if not os.path.exists(marker_path):
        raise SnapshotIncompleteError(
            f"COMPLETE marker missing in {snap_dir}. Snapshot may be partially "
            f"written."
        )

    # §16.5: verify snapshot_hash against recomputed content hash
    stored_hash = manifest["snapshot_hash"]
    try:
        recomputed_hash = _recompute_snapshot_hash(manifest, snap_dir)
    except (KeyError, json.JSONDecodeError, OSError) as e:
        # Any artifact read error → hash verification cannot succeed → reject
        raise SnapshotHashMismatchError(
            f"cannot recompute hash for {manifest.get('snapshot_id', '?')}: "
            f"{e}. Snapshot may have been tampered."
        ) from e
    if stored_hash != recomputed_hash:
        raise SnapshotHashMismatchError(
            f"snapshot hash mismatch for {manifest['snapshot_id']}: "
            f"stored={stored_hash} recomputed={recomputed_hash}. "
            f"Snapshot may have been tampered."
        )

    # Build SnapshotManifest (T2 contract)
    t2_manifest = SnapshotManifest(
        snapshot_id=manifest["snapshot_id"],
        schema_version=manifest["schema_version"],
        included_strict_count=manifest["included_strict_count"],
        conditional_count=manifest["conditional_count"],
        diagnostic_count=manifest["diagnostic_count"],
        quarantine_count=manifest["quarantine_count"],
        build_status=manifest["build_status"],
        snapshot_hash=manifest["snapshot_hash"],
        build_id=manifest.get("build_id", ""),
        source_counts=manifest.get("source_counts", {}),
        policy_version=manifest.get("policy_version", "p1-1"),
    )

    # Collect evidence IDs from records file
    all_records = _read_jsonl(os.path.join(snap_dir, _RECORDS_FILENAME))
    evidence_ids = sorted(r["reaction_id"] for r in all_records)

    # Build resource paths (read-only references — no modification)
    resources = {
        "manifest": os.path.join(snap_dir, _MANIFEST_FILENAME),
        "production_index": os.path.join(snap_dir, _PRODUCTION_INDEX),
        "diagnostic_index": os.path.join(snap_dir, _DIAGNOSTIC_INDEX),
        "quarantine_index": os.path.join(snap_dir, _QUARANTINE_INDEX),
        "records": os.path.join(snap_dir, _RECORDS_FILENAME),
    }

    return SnapshotRecord(
        snapshot_id=manifest["snapshot_id"],
        manifest=t2_manifest,
        reaction_evidence_ids=evidence_ids,
        build_config_hash=manifest.get("build_config_hash", ""),
        freeze_status="frozen",
        resources=resources,
    )
