#!/usr/bin/env python3
"""Generate the P1-T11 fixture census manifest from serialized T10 evidence."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reaction_agent.snapshot.builder import build_snapshot  # noqa: E402
from scripts.run_p1_gate import (  # noqa: E402
    _g09_t10_fixture_config,
    _g09_t10_fixture_items,
)


OUTPUT = ROOT / "reports" / "p1" / "manual_audit_sample_manifest.json"
PROTOCOL = ROOT / "docs" / "manual_audit_protocol.md"

_SAMPLE_IDS = {
    "rxn_strict_001": "audit_001",
    "rxn_cond_001": "audit_002",
    "rxn_diag_001": "audit_003",
    "rxn_quar_001": "audit_004",
}


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _reaction_class(record: dict) -> str:
    evidence = record["reaction_evidence"]
    rid = evidence["reaction_id"]
    if rid in {"rxn_strict_001", "rxn_cond_001"}:
        return "identity_no_heavy_atom_change"
    if rid == "rxn_diag_001":
        return "carbon_chain_extension_unknown_atom_source"
    if rid == "rxn_quar_001":
        return "charge_neutralization_unbalanced"
    raise ValueError(f"unclassified fixture reaction: {rid}")


def _participant_count_label(record: dict) -> str:
    participants = record["reaction_evidence"]["participants"]
    reactants = sum(p["side"] == "reactant" for p in participants)
    products = sum(p["side"] == "product" for p in participants)
    return f"reactants_{reactants}_products_{products}"


def _cofactor_label(record: dict) -> str:
    ledger = record.get("source_ledger") or {}
    roles = {assignment["role"] for assignment in ledger.get("role_assignments", [])}
    return "with_explicit_cofactor_role" if "cofactor" in roles else "no_explicit_cofactor_role"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p1_manual_manifest_") as tmp:
        config = _g09_t10_fixture_config(os.path.join(tmp, "snapshots"))
        manifest = build_snapshot(config, iter(_g09_t10_fixture_items()))
        snap_dir = Path(config.output_snapshot_root) / manifest.snapshot_id
        records = _jsonl(snap_dir / "records.jsonl")

    if len(records) != 4 or {r["reaction_evidence"]["reaction_id"] for r in records} != set(_SAMPLE_IDS):
        raise RuntimeError("T10 fixture census does not match the frozen four-record set")

    items: list[dict] = []
    for record in sorted(records, key=lambda r: _SAMPLE_IDS[r["reaction_evidence"]["reaction_id"]]):
        evidence = record["reaction_evidence"]
        quarantine = record.get("quarantine_record")
        labels = {
            "mapping_quality": evidence["mapping_report"]["mapping_status"],
            "eligibility_lane": record["lane"],
            "source": evidence["source_name"],
            "reaction_class": _reaction_class(record),
            "participant_count": _participant_count_label(record),
            "cofactor_pattern": _cofactor_label(record),
            "ledger_status": record["source_ledger"]["balance_status"],
            "quarantine_reason": (
                quarantine["category"] if quarantine is not None else "none"
            ),
        }
        items.append({
            "sample_id": _SAMPLE_IDS[evidence["reaction_id"]],
            "reaction_id": evidence["reaction_id"],
            "source_name": evidence["source_name"],
            "lane_expected": record["lane"],
            "stratum_labels": labels,
            "rubric_items_applicable": [f"R{i}" for i in range(1, 12)],
        })

    strata_keys = [
        "mapping_quality", "eligibility_lane", "source", "reaction_class",
        "participant_count", "cofactor_pattern", "ledger_status",
        "quarantine_reason",
    ]
    strata = {
        f"by_{key}": dict(sorted(Counter(
            item["stratum_labels"][key] for item in items
        ).items()))
        for key in strata_keys
    }
    protocol_hash = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    output = {
        "manifest_version": "p1-t11-3",
        "protocol_sha256": protocol_hash,
        "sample_source": "fixture_snapshot_t10",
        "snapshot_id": manifest.snapshot_id,
        "snapshot_hash": manifest.snapshot_hash,
        "sample_strategy": "census",
        "random_seed": None,
        "sample_size_justification": (
            "T10 fixture snapshot contains 4 records (strict=1, conditional=1, "
            "diagnostic=1, quarantine=1). Per §17.2, datasets with ≤ 50 records "
            "are audited in full census. Only observed fixture strata are listed."
        ),
        "coverage_boundary": (
            "Contract-fixture lane/semantics census only. It does not claim real "
            "chemical-diversity or performance coverage; absent multi-reactant "
            "and explicit-cofactor strata are disclosed, not fabricated."
        ),
        "total_records_in_snapshot": len(records),
        "sample_size": len(items),
        "fixture_label": (
            "FIXTURE — synthetic ReactionEvidence + SourceReactionLedger + "
            "ResolvedTransformedLineage. No real data fabricated and no "
            "production-performance claim."
        ),
        "strata": strata,
        "items": items,
        "annotator_requirements": {
            "annotator_count": 2,
            "independence": (
                "Annotator A and B must be distinct no-shared-context instances; "
                "neither may read the peer output before submission."
            ),
            "adjudicator": (
                "A third no-shared-context instance reviews A+B only after both "
                "outputs are complete."
            ),
        },
        "current_status": "READY_FOR_INDEPENDENT_ROUND_3_AUDIT",
        "current_census_verdict_rule": (
            "Every listed R1-R11 cell is applicable and must be pass or fail; "
            "the frozen §17.3.1 rules define R7/R9/R11 per-row interpretation."
        ),
        "prior_rounds": [
            {"round": 1, "status": "FAIL", "archive": "reports/p1/g10_round_1/", "preserved": True},
            {"round": 2, "status": "FAIL", "archive": "reports/p1/g10_round_2/", "preserved": True},
        ],
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}")
    print(f"snapshot={manifest.snapshot_id} hash={manifest.snapshot_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
