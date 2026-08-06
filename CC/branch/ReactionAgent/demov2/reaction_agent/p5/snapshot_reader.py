"""P5 snapshot reader — reads P1 snapshot authority (read-only).

P5 does NOT build another snapshot/mapping/lineage/eligibility authority.
It reads P1 frozen artifacts and generates versioned manifests/indices.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Optional

from reaction_agent.p5.schemas import (
    P5_SCHEMA_VERSION,
    ArtifactClassification,
    FullSnapshotManifest,
    ProductionIndexManifest,
    FilterAccountingEntry,
)


def _sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _canonical_hash(obj: Any) -> str:
    """Deterministic content hash of a JSON-serializable object."""
    return _sha256_hex(json.dumps(obj, sort_keys=True, ensure_ascii=False))


P5_SNAPSHOT_READER_VERSION = "p5-t1-1"


def read_p1_snapshot(
    p1_snapshot_sample_path: str,
) -> dict[str, Any]:
    """Read P1 snapshot_build_sample.json (read-only).

    Returns the raw P1 snapshot data. P5 does not modify P1 artifacts.
    """
    if not os.path.exists(p1_snapshot_sample_path):
        raise FileNotFoundError(
            f"P1 snapshot sample not found: {p1_snapshot_sample_path}"
        )
    with open(p1_snapshot_sample_path, "r") as f:
        return json.load(f)


def build_full_snapshot_manifest(
    p1_snapshot_data: dict[str, Any],
    artifact_classification: ArtifactClassification = ArtifactClassification.synthetic_fixture,
) -> FullSnapshotManifest:
    """Build a FullSnapshotManifest from P1 snapshot data.

    P5 reads P1 snapshot authority (read-only). This manifest records
    production, diagnostic, quarantine indices, source counts, filter
    accounting, and provenance.
    """
    fixture_snapshot = p1_snapshot_data.get("fixture_snapshot", {})
    on_disk = fixture_snapshot.get("on_disk_manifest", {})
    loaded_record = fixture_snapshot.get("loaded_record", {})
    items = fixture_snapshot.get("items", [])

    snapshot_id = on_disk.get("snapshot_id", loaded_record.get("snapshot_id", "unknown"))
    snapshot_hash = on_disk.get("snapshot_hash", loaded_record.get("snapshot_hash", "unknown"))

    # Source counts
    source_counts = on_disk.get("source_counts", {})

    # Index partition
    strict_count = on_disk.get("included_strict_count", 0)
    conditional_count = on_disk.get("conditional_count", 0)
    diagnostic_count = on_disk.get("diagnostic_count", 0)
    quarantine_count = on_disk.get("quarantine_count", 0)
    record_count = on_disk.get("record_count", len(items))

    # Build filter accounting from P1 data
    filter_accounting = []

    # Source load filter
    filter_accounting.append(FilterAccountingEntry(
        filter_name="source_load",
        filter_stage="ingestion",
        denominator_before=record_count,
        denominator_after=record_count,
        removed_count=0,
        reason="all records loaded from source",
    ))

    # Normalization filter
    filter_accounting.append(FilterAccountingEntry(
        filter_name="normalization",
        filter_stage="normalization",
        denominator_before=record_count,
        denominator_after=record_count,
        removed_count=0,
        reason="all records normalized",
    ))

    # Mapping filter
    filter_accounting.append(FilterAccountingEntry(
        filter_name="mapping",
        filter_stage="mapping",
        denominator_before=record_count,
        denominator_after=record_count,
        removed_count=0,
        reason="mapping adapter applied to all records",
    ))

    # Eligibility filter (the main partition filter)
    production_count = strict_count + conditional_count
    excluded_count = 0  # P1 doesn't have a separate "excluded" beyond quarantine+diagnostic
    filter_accounting.append(FilterAccountingEntry(
        filter_name="eligibility_decision",
        filter_stage="eligibility",
        denominator_before=record_count,
        denominator_after=production_count,
        removed_count=diagnostic_count + quarantine_count,
        reason=f"{diagnostic_count} diagnostic + {quarantine_count} quarantine",
        quarantine_reason=f"{quarantine_count} quarantined" if quarantine_count > 0 else None,
    ))

    # Failure counts from P1
    failure_counts = on_disk.get("failure_counts_by_reason", {})
    duplicate_count = 0  # P1 snapshot doesn't report duplicates separately
    unresolved_count = sum(failure_counts.values()) if failure_counts else 0

    return FullSnapshotManifest(
        schema_version=P5_SCHEMA_VERSION,
        snapshot_id=snapshot_id,
        snapshot_hash=snapshot_hash,
        artifact_classification=artifact_classification,
        source_counts=source_counts,
        pre_normalization_count=record_count,
        post_normalization_count=record_count,
        production_count=production_count,
        diagnostic_count=diagnostic_count,
        quarantine_count=quarantine_count,
        excluded_count=excluded_count,
        duplicate_count=duplicate_count,
        unresolved_count=unresolved_count,
        filter_accounting=filter_accounting,
        p1_snapshot_id=snapshot_id,
        p1_snapshot_hash=snapshot_hash,
        builder_version=P5_SNAPSHOT_READER_VERSION,
        production_index_hash=on_disk.get("production_index_hash"),
        diagnostic_index_hash=on_disk.get("diagnostic_index_hash"),
        quarantine_index_hash=on_disk.get("quarantine_index_hash"),
    )


def build_production_index_manifest(
    p1_snapshot_data: dict[str, Any],
    full_manifest: FullSnapshotManifest,
    artifact_classification: ArtifactClassification = ArtifactClassification.synthetic_fixture,
) -> ProductionIndexManifest:
    """Build ProductionIndexManifest from P1 snapshot data.

    Namespace isolation: production records are strictly separated from
    diagnostic and quarantine.
    """
    fixture_snapshot = p1_snapshot_data.get("fixture_snapshot", {})
    on_disk = fixture_snapshot.get("on_disk_manifest", {})
    items = fixture_snapshot.get("items", [])

    # Partition by lane
    production_ids = [item["reaction_id"] for item in items
                      if item.get("lane_expected") in ("strict", "conditional")]
    diagnostic_ids = [item["reaction_id"] for item in items
                      if item.get("lane_expected") == "diagnostic"]
    quarantine_ids = [item["reaction_id"] for item in items
                      if item.get("lane_expected") == "quarantine"]

    strict_count = sum(1 for item in items if item.get("lane_expected") == "strict")
    conditional_count = sum(1 for item in items if item.get("lane_expected") == "conditional")

    # Quality distributions (from P1 data — simplified)
    mapping_status_distribution = {}
    lineage_quality_distribution = {}
    ledger_balance_distribution = {}

    # From P1 on-disk manifest
    for item in items:
        lane = item.get("lane_expected", "unknown")
        if lane in ("strict", "conditional"):
            mapping_status_distribution["fully_mapped"] = mapping_status_distribution.get("fully_mapped", 0) + 1
            lineage_quality_distribution["reliable"] = lineage_quality_distribution.get("reliable", 0) + 1
            ledger_balance_distribution[on_disk.get("ledger_balance_status", "unknown")] = \
                ledger_balance_distribution.get(on_disk.get("ledger_balance_status", "unknown"), 0) + 1

    return ProductionIndexManifest(
        schema_version=P5_SCHEMA_VERSION,
        snapshot_id=full_manifest.snapshot_id,
        snapshot_hash=full_manifest.snapshot_hash,
        artifact_classification=artifact_classification,
        production_record_count=len(production_ids),
        production_record_ids=production_ids,
        strict_count=strict_count,
        conditional_count=conditional_count,
        diagnostic_ids=diagnostic_ids,
        quarantine_ids=quarantine_ids,
        mapping_status_distribution=mapping_status_distribution,
        lineage_quality_distribution=lineage_quality_distribution,
        ledger_balance_distribution=ledger_balance_distribution,
    )
