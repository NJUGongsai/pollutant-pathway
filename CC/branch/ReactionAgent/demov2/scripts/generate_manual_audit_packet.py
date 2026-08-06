#!/usr/bin/env python3
"""Build the sealed evidence packet used by independent P1-T11 annotators.

The packet contains the exact four T10 fixture records after eligibility
classification, their index membership, the frozen protocol hash, and the
real proline/2OG G03 evidence required for H2.  It is data only: no annotation
or expected rubric answer is embedded.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reaction_agent.snapshot.builder import build_snapshot, compute_snapshot_hash  # noqa: E402
from reaction_agent.snapshot.loader import load_snapshot  # noqa: E402
from scripts.run_p1_gate import (  # noqa: E402
    _g09_t10_fixture_config,
    _g09_t10_fixture_items,
)

OUTPUT = ROOT / "reports" / "p1" / "manual_audit_evidence_packet.json"
PROTOCOL = ROOT / "docs" / "manual_audit_protocol.md"
SAMPLE_MANIFEST = ROOT / "reports" / "p1" / "manual_audit_sample_manifest.json"
LINEAGE_CASES = ROOT / "reports" / "p1" / "lineage_regression_cases.json"
LEGACY_AUDIT = ROOT / "reports" / "data_audit" / "legacy_lineage_audit.json"
REQUIRED_CASE_QUARANTINE = (
    ROOT / "reports" / "p1" / "required_case_quarantine_evidence.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p1_manual_audit_packet_") as temp_dir:
        items = _g09_t10_fixture_items()
        config_a = _g09_t10_fixture_config(os.path.join(temp_dir, "snapshots_a"))
        config_b = _g09_t10_fixture_config(os.path.join(temp_dir, "snapshots_b"))
        hash_only = compute_snapshot_hash(config_a, items)
        manifest_a = build_snapshot(config_a, iter(items))
        manifest_b = build_snapshot(config_b, iter(reversed(items)))
        snapshot_dir_a = Path(config_a.output_snapshot_root) / manifest_a.snapshot_id
        snapshot_dir_b = Path(config_b.output_snapshot_root) / manifest_b.snapshot_id
        loaded_a = load_snapshot(str(snapshot_dir_a))
        loaded_b = load_snapshot(str(snapshot_dir_b))
        records = _jsonl(snapshot_dir_a / "records.jsonl")
        indices = {
            "production": _jsonl(snapshot_dir_a / "production_index.jsonl"),
            "diagnostic": _jsonl(snapshot_dir_a / "diagnostic_index.jsonl"),
            "quarantine": _jsonl(snapshot_dir_a / "quarantine_index.jsonl"),
        }
        on_disk_manifest_a = _json(snapshot_dir_a / "manifest.json")
        on_disk_manifest_b = _json(snapshot_dir_b / "manifest.json")

    replay_hashes = {
        hash_only,
        manifest_a.snapshot_hash,
        manifest_b.snapshot_hash,
        loaded_a.manifest.snapshot_hash,
        loaded_b.manifest.snapshot_hash,
    }
    replay_ids = {
        manifest_a.snapshot_id,
        manifest_b.snapshot_id,
        loaded_a.snapshot_id,
        loaded_b.snapshot_id,
    }
    if len(replay_hashes) != 1 or len(replay_ids) != 1:
        raise RuntimeError("snapshot replay evidence is inconsistent")

    sample_manifest = _json(SAMPLE_MANIFEST)
    if sample_manifest.get("snapshot_id") != manifest_a.snapshot_id:
        raise RuntimeError("sample manifest snapshot_id differs from rebuilt snapshot")
    if sample_manifest.get("snapshot_hash") != manifest_a.snapshot_hash:
        raise RuntimeError("sample manifest snapshot_hash differs from rebuilt snapshot")

    required_case_quarantine = _json(REQUIRED_CASE_QUARANTINE)
    if not (
        required_case_quarantine.get("case_count") == 3
        and required_case_quarantine.get("quarantined_count") == 3
        and required_case_quarantine.get("production_eligible_count") == 0
        and required_case_quarantine.get("forbidden_lineage_present_count") == 0
    ):
        raise RuntimeError("real required-case quarantine evidence is incomplete")

    legacy_audit = _json(LEGACY_AUDIT)
    required_cases = [
        example
        for example in legacy_audit["examples"]
        if example.get("required_case") == "proline_2og"
    ]
    packet = {
        "packet_version": "p1-t11-evidence-4",
        "fixture_disclosure": (
            "The four T10 records are synthetic contract fixtures, not real "
            "production chemistry. They audit pipeline semantics only."
        ),
        "frozen_protocol": {
            "path": "docs/manual_audit_protocol.md",
            "sha256": _sha256(PROTOCOL),
        },
        "sample_manifest": sample_manifest,
        "snapshot_manifest": on_disk_manifest_a,
        "snapshot_replay_evidence": {
            "input_a_order": "forward",
            "input_b_order": "reverse",
            "hash_only_no_write": hash_only,
            "build_a": {
                "snapshot_id": manifest_a.snapshot_id,
                "snapshot_hash": manifest_a.snapshot_hash,
                "build_status": manifest_a.build_status,
                "loader_accepted": True,
                "loaded_snapshot_id": loaded_a.snapshot_id,
                "loaded_snapshot_hash": loaded_a.manifest.snapshot_hash,
            },
            "build_b": {
                "snapshot_id": manifest_b.snapshot_id,
                "snapshot_hash": manifest_b.snapshot_hash,
                "build_status": manifest_b.build_status,
                "loader_accepted": True,
                "loaded_snapshot_id": loaded_b.snapshot_id,
                "loaded_snapshot_hash": loaded_b.manifest.snapshot_hash,
            },
            "same_hash_across_hash_build_load": len(replay_hashes) == 1,
            "same_snapshot_id_across_build_load": len(replay_ids) == 1,
            "manifest_a_record_content_hashes": on_disk_manifest_a[
                "record_content_hashes"
            ],
            "manifest_b_record_content_hashes": on_disk_manifest_b[
                "record_content_hashes"
            ],
            "record_content_hashes_equal": (
                on_disk_manifest_a["record_content_hashes"]
                == on_disk_manifest_b["record_content_hashes"]
            ),
        },
        "records": sorted(
            records,
            key=lambda record: record["reaction_evidence"]["reaction_id"],
        ),
        "index_membership": {
            name: sorted(
                record["reaction_evidence"]["reaction_id"] for record in values
            )
            for name, values in indices.items()
        },
        "real_required_case_evidence": {
            "legacy_source": "reports/data_audit/legacy_lineage_audit.json",
            "legacy_source_sha256": _sha256(LEGACY_AUDIT),
            "legacy_case_summary": legacy_audit["proline_2og_case"],
            "legacy_rows": required_cases,
            "new_pipeline_quarantine_source": (
                "reports/p1/required_case_quarantine_evidence.json"
            ),
            "new_pipeline_quarantine_sha256": _sha256(REQUIRED_CASE_QUARANTINE),
            "new_pipeline_quarantine": required_case_quarantine,
            "interpretation_boundary": (
                "The legacy rows establish real source presence and the old "
                "cross-lineage failure. The new pipeline runs the available "
                "formal diagnostic mapper and explicitly quarantines every row. "
                "No reacting-center edge is represented as a full atom map and "
                "no expected lineage is synthesized."
            ),
        },
        "curated_lineage_regression": {
            "source": "reports/p1/lineage_regression_cases.json",
            "source_sha256": _sha256(LINEAGE_CASES),
            "proline_case": _json(LINEAGE_CASES)["regression_cases"][0],
            "real_source_case_audit": _json(LINEAGE_CASES)["real_source_case_audit"],
        },
        "annotation_contract": {
            "sample_ids": [item["sample_id"] for item in _json(SAMPLE_MANIFEST)["items"]],
            "rubric_ids": [f"R{index}" for index in range(1, 12)],
            "catastrophic_error_ids": [f"C{index}" for index in range(1, 10)],
            "required_per_rubric_fields": ["verdict", "reason", "evidence_pointer"],
            "verdict_vocabulary": ["pass", "fail", "not_applicable"],
            "current_census_rule": (
                "Every R1-R11 item is explicitly applicable for all four "
                "samples; current verdicts must be pass or fail. Section "
                "17.3.1 freezes R7/R9/R11 interpretation."
            ),
        },
    }
    OUTPUT.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}")
    print(f"records={len(packet['records'])}, required_case_rows={len(required_cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
