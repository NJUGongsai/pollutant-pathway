#!/usr/bin/env python3
"""Regenerate reports/p1/snapshot_build_sample.json after Critical-1/2 changes.

Uses the SAME ``_g09_t10_fixture_items`` as ``check_g09_snapshot_reproducibility``
to build a real snapshot, then records the on-disk manifest + hashes so G09
cross-verification (independent rebuild == stored hash) passes.

Re-run whenever the snapshot hash algorithm or the T10 fixture changes.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

DEMOV2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEMOV2_ROOT)

from scripts.run_p1_gate import (  # noqa: E402
    _g09_t10_fixture_items,
    _g09_t10_fixture_config,
)
from reaction_agent.snapshot.builder import (  # noqa: E402
    build_snapshot,
    compute_snapshot_hash,
)
from reaction_agent.snapshot.loader import load_snapshot  # noqa: E402


def main() -> None:
    items = _g09_t10_fixture_items()
    with tempfile.TemporaryDirectory(prefix="regen_snap_") as tmp:
        config_a = _g09_t10_fixture_config(os.path.join(tmp, "snapshots_a"))
        config_b = _g09_t10_fixture_config(os.path.join(tmp, "snapshots_b"))
        snapshot_hash = compute_snapshot_hash(config_a, items)
        manifest_a = build_snapshot(config_a, iter(items))
        manifest_b = build_snapshot(config_b, iter(reversed(items)))
        snap_dir_a = os.path.join(
            config_a.output_snapshot_root, manifest_a.snapshot_id,
        )
        snap_dir_b = os.path.join(
            config_b.output_snapshot_root, manifest_b.snapshot_id,
        )
        loaded_a = load_snapshot(snap_dir_a)
        loaded_b = load_snapshot(snap_dir_b)
        with open(os.path.join(snap_dir_a, "manifest.json"), encoding="utf-8") as f:
            on_disk = json.load(f)

    if not (
        snapshot_hash
        == manifest_a.snapshot_hash
        == manifest_b.snapshot_hash
        == loaded_a.manifest.snapshot_hash
        == loaded_b.manifest.snapshot_hash
    ):
        raise RuntimeError("snapshot replay mismatch across hash/build/load paths")
    if manifest_a.snapshot_id != manifest_b.snapshot_id:
        raise RuntimeError("snapshot replay produced different snapshot IDs")

    manifest = manifest_a

    sample_path = os.path.join(DEMOV2_ROOT, "reports", "p1", "snapshot_build_sample.json")
    with open(sample_path, encoding="utf-8") as f:
        data = json.load(f)

    fs = data.setdefault("fixture_snapshot", {})
    counts = {
        "strict": manifest.included_strict_count,
        "conditional": manifest.conditional_count,
        "diagnostic": manifest.diagnostic_count,
        "quarantine": manifest.quarantine_count,
    }

    # determinism_evidence — the hash G09 cross-verifies against
    de = fs.setdefault("determinism_evidence", {})
    de["hash_value"] = snapshot_hash
    de["same_hash_3way"] = True
    de["same_snapshot_id"] = True

    # build_a / build_b — independently materialized from forward/reverse order.
    for key, built in (("build_a", manifest_a), ("build_b", manifest_b)):
        b = fs.setdefault(key, {})
        b["snapshot_hash"] = built.snapshot_hash
        b["snapshot_id"] = built.snapshot_id
        b["build_status"] = "complete"
        b["counts"] = counts

    # on_disk_manifest — the real manifest from build_snapshot
    fs["on_disk_manifest"] = on_disk

    # hash_only_no_write — compute_snapshot_hash result (no disk write)
    fs["hash_only_no_write"] = snapshot_hash

    # loaded_record — a real loader result from build A.
    lr = fs.setdefault("loaded_record", {})
    lr["resources"] = sorted(loaded_a.resources)
    lr["freeze_status"] = loaded_a.freeze_status
    lr["evidence_ids_count"] = len(loaded_a.reaction_evidence_ids)
    lr["snapshot_id"] = loaded_a.snapshot_id
    lr["snapshot_hash"] = loaded_a.manifest.snapshot_hash
    fs["replay_verification"] = {
        "build_a_input_order": "forward",
        "build_b_input_order": "reverse",
        "build_a_loader_accepted": True,
        "build_b_loader_accepted": True,
        "same_hash_across_hash_build_load": True,
        "same_snapshot_id": True,
    }

    # real_source_snapshot — derive status from live mapper availability and
    # the deterministic required-case quarantine evidence.
    rdkit_available = False
    rdkit_version = None
    try:
        import rdkit  # noqa: F401
        rdkit_available = True
        rdkit_version = getattr(rdkit, "__version__", "unknown")
    except Exception:  # noqa: BLE001
        rdkit_available = False

    required_evidence_path = os.path.join(
        DEMOV2_ROOT, "reports", "p1", "required_case_quarantine_evidence.json",
    )
    required_evidence = None
    if os.path.isfile(required_evidence_path):
        with open(required_evidence_path, encoding="utf-8") as f:
            required_evidence = json.load(f)

    required_cases_quarantined = bool(
        required_evidence
        and required_evidence.get("case_count") == 3
        and required_evidence.get("quarantined_count") == 3
        and required_evidence.get("production_eligible_count") == 0
        and required_evidence.get("forbidden_lineage_present_count") == 0
    )
    if rdkit_available and required_cases_quarantined:
        reason = (
            "Three real proline/2OG rows were located by G03 and processed by "
            "the new required-case safety path. The available RDKit MCS result "
            "is diagnostic only, so all three are explicitly quarantined; none "
            "enters production and no lineage is synthesized."
        )
        blocked_at = [
            "validated complete atom mapping and independently audited lineage "
            "resolution are required before any future production promotion"
        ]
        status = "REQUIRED_CASES_EXPLICITLY_QUARANTINED"
    elif rdkit_available:
        reason = (
            "real required-case quarantine evidence has not been generated. "
            f"RDKit is available at runtime (v{rdkit_version})."
        )
        blocked_at = ["required-case quarantine evidence missing or invalid"]
        status = "BLOCKED"
    else:
        reason = (
            "Preflight BLOCKED (rdkit absent). Real source snapshot requires rdkit "
            "for T4 mapping, T6 lineage, T7 source ledger balance. Builder API is "
            "ready; accepts pre-computed T4-T8 artifacts. No real data fabricated."
        )
        blocked_at = ["T4 mapping (rdkit)", "T6 lineage (rdkit)",
                      "T7 source ledger balance (rdkit)"]
        status = "BLOCKED"
    data["real_source_snapshot"] = {
        "builder_api_ready": True,
        "clear_separation": (
            "Fixture snapshots use source_name=fixture_source_*. Real snapshots "
            "will use source_name=<real_db_name>. The builder does not fabricate "
            "real data."),
        "runtime_probe": {
            "rdkit_available": rdkit_available,
            "rdkit_version": rdkit_version,
        },
        "pipeline_blocked_at": blocked_at,
        "reason": reason,
        "required_case_evidence": (
            "reports/p1/required_case_quarantine_evidence.json"
            if required_cases_quarantined else None
        ),
        "status": status,
    }

    with open(sample_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    print(f"snapshot_hash = {snapshot_hash}")
    print(f"snapshot_id   = {manifest.snapshot_id}")
    print(f"counts        = {counts}")
    print(f"rdkit_available = {rdkit_available} (v{rdkit_version})")
    print(f"updated: {sample_path}")


if __name__ == "__main__":
    main()
