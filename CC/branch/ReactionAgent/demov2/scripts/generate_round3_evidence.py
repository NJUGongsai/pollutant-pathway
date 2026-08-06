#!/usr/bin/env python3
"""Generate Round 3 structured audit-evidence JSONs from ACTUAL run outputs.

This script does NOT re-run gates or mutations; it derives the Round 3
evidence subsets from the machine-readable artifacts produced by the actual
executions (``reports/p1/mutation_results.json``, ``P1_GATE_REPORT.json``,
``P0_GATE_REPORT.json``). Numbers are never hand-edited (§12.2).

Outputs (reports/p1/):
  - snapshot_complete_evidence_mutation_results.json  (M18–M21, M26–M31)
  - eligibility_cross_invariant_results.json          (M32–M41)
  - gate_false_positive_mutation_results_round_3.json (M9–M15, M22–M25)
  - P1_ROUND_3_AUDIT_EVIDENCE.json                    (overall roll-up)
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P1 = ROOT / "reports" / "p1"
P0 = ROOT / "reports" / "p0"


def _load(p: Path) -> dict:
    return json.loads(p.read_text())


def _dump(p: Path, data: dict) -> None:
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _by_id(mutations: list[dict]) -> dict[str, dict]:
    return {m["mutation_id"]: m for m in mutations}


def _subset(by_id: dict[str, dict], ids: list[str]) -> list[dict]:
    return [by_id[i] for i in ids if i in by_id]


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True).stdout.strip()


def main() -> int:
    mut = _load(P1 / "mutation_results.json")
    mutations = mut["mutations"]
    by_id = _by_id(mutations)
    now = datetime.now(timezone.utc).isoformat()

    # --- snapshot complete-evidence hash coverage (Critical-1) ---
    snap_ids = ["M18", "M19", "M20", "M21", "M26", "M27", "M28", "M29", "M30", "M31"]
    snap = _subset(by_id, snap_ids)
    _dump(P1 / "snapshot_complete_evidence_mutation_results.json", {
        "generated_at": now,
        "description": ("Critical-1 complete-evidence hash coverage. Each mutation "
                        "changes one scientific field of a frozen record; caught=True "
                        "means the snapshot/record content hash changed (tamper detected)."),
        "mutation_ids": snap_ids,
        "total": len(snap),
        "caught": sum(1 for m in snap if m["caught"]),
        "mutations": snap,
    })

    # --- eligibility strict cross-invariants (Critical-2) ---
    xinv_ids = ["M32", "M33", "M34", "M35", "M36", "M37", "M38", "M39", "M40", "M41"]
    xinv = _subset(by_id, xinv_ids)
    _dump(P1 / "eligibility_cross_invariant_results.json", {
        "generated_at": now,
        "description": ("Critical-2 strict cross-invariants. Each mutation applies one "
                        "bad field to an otherwise genuinely-strict record; caught=True "
                        "means the engine did NOT return strict_eligible (fail-closed), "
                        "or the builder failed closed (M41 dual-ledger disagreement)."),
        "mutation_ids": xinv_ids,
        "total": len(xinv),
        "caught": sum(1 for m in xinv if m["caught"]),
        "mutations": xinv,
    })

    # --- gate false-positive / impl-failure mutations (Round 3 view) ---
    gate_ids = ["M9", "M10", "M11", "M12", "M13", "M14", "M15",
                "M22", "M23", "M24", "M25"]
    gate = _subset(by_id, gate_ids)
    _dump(P1 / "gate_false_positive_mutation_results_round_3.json", {
        "generated_at": now,
        "description": ("Gate false-positive / implementation-failure mutations. "
                        "caught=True means a fabricated PASS is rejected: the gate "
                        "reports FAIL (or BLOCKED via live probe for G04) and, for M25, "
                        "the single aggregate_gate_status authority never lets BLOCKED "
                        "mask an implementation FAIL."),
        "mutation_ids": gate_ids,
        "total": len(gate),
        "caught": sum(1 for m in gate if m["caught"]),
        "mutations": gate,
    })

    # --- overall Round 3 roll-up ---
    p1_gate = _load(P1 / "P1_GATE_REPORT.json")
    p0_gate = _load(P0 / "P0_GATE_REPORT.json")
    _dump(P1 / "P1_ROUND_3_AUDIT_EVIDENCE.json", {
        "generated_at": now,
        "round": 3,
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "head": _git("rev-parse", "HEAD"),
        "mutations": {
            "total": mut["total"],
            "caught": mut["caught"],
            "all_caught": mut["total"] == mut["caught"],
            "critical_1_snapshot_hash_coverage": snap_ids,
            "critical_2_strict_cross_invariants": xinv_ids,
            "gate_false_positive": gate_ids,
        },
        "p0_gate": {
            "status": p0_gate.get("status"),
            "pass_count": p0_gate.get("pass_count"),
            "total": p0_gate.get("total_checks") or p0_gate.get("total"),
        },
        "p1_gate": {
            "status": p1_gate.get("status"),
            "pass_count": p1_gate.get("pass_count"),
            "block_count": p1_gate.get("block_count"),
            "fail_count": p1_gate.get("fail_count"),
            "total": p1_gate.get("total_checks"),
            "blocked_gates": [c["gate_id"] for c in p1_gate.get("checks", [])
                              if c.get("blocked")],
        },
        "note": ("Derived from actual execution artifacts; no hand-edited numbers. "
                 "P1 scientific gate remains BLOCKED pending external inputs; "
                 "P2 remains BLOCKED pending ChatGPT read-only re-audit."),
    })

    print("Round 3 evidence written:")
    for name in ("snapshot_complete_evidence_mutation_results.json",
                 "eligibility_cross_invariant_results.json",
                 "gate_false_positive_mutation_results_round_3.json",
                 "P1_ROUND_3_AUDIT_EVIDENCE.json"):
        print(f"  reports/p1/{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
