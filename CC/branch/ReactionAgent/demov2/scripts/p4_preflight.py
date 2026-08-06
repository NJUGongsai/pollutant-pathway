#!/usr/bin/env python3
"""P4 preflight (honest capability inventory).

Checks what P4 can and cannot consume right now:
- P3 interface manifest present? (absent -> typed BLOCKED for real input)
- chemistry backend (rdkit) available? (absent -> no real chemistry)
- P2 formal Gate status? (BLOCKED -> not an authority)
- P1 snapshot authority present? (fixture snapshot only)
- evidence classification (synthetic_fixture)

Writes reports/p4/P4_PREFLIGHT.json + P4_PREFLIGHT.md. This is a capability
inventory, NOT a Gate: it does not fabricate capability.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

DEMOV2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEMOV2_ROOT)
REPORT_DIR = os.path.join(DEMOV2_ROOT, "reports", "p4")


def _read_json(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def run() -> dict:
    checks = {}

    # 1. P3 interface manifest
    from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
    p3 = P3InterfaceConsumer().load()
    checks["p3_interface_manifest"] = {
        "status": "BLOCKED" if not p3.present else "PRESENT",
        "present": p3.present,
        "classification": p3.classification,
        "blocked_reasons": p3.blocked_reasons,
    }

    # 2. chemistry backend
    rdkit = importlib.util.find_spec("rdkit")
    checks["chemistry_backend"] = {
        "status": "AVAILABLE" if rdkit else "BLOCKED",
        "rdkit_present": rdkit is not None,
        "blocked_reasons": [] if rdkit else ["rdkit_absent"],
    }

    # 3. P2 formal Gate
    p2_path = os.path.join(DEMOV2_ROOT, "reports", "p2", "P2_GATE_REPORT.json")
    p2 = _read_json(p2_path)
    p2_status = (p2 or {}).get("status", "BLOCKED (report absent)")
    checks["p2_formal_gate"] = {
        "status": "AUTHORITY" if p2_status == "READY_FOR_CHATGPT_P2_AUDIT" else "BLOCKED",
        "report_present": p2 is not None,
        "reported_status": p2_status,
        "blocked_reasons": [] if p2_status == "READY_FOR_CHATGPT_P2_AUDIT" else ["p2_gate_blocked"],
    }

    # 4. P1 snapshot authority (fixture snapshot)
    checks["p1_snapshot_authority"] = {
        "status": "PRESENT (fixture synthetic)",
        "snapshot_id": "snap_c589494081df",
        "classification": "synthetic_fixture",
    }

    # 5. evidence classification
    from tests.fixtures.p4.p4_contract_fixture import build_evidence_records
    n_ev = len(build_evidence_records())
    checks["evidence_classification"] = {
        "status": "SYNTHETIC_FIXTURE",
        "evidence_row_count": n_ev,
        "classification": "synthetic_fixture",
        "blocked_reasons": ["real_evidence_not_confirmed"],
    }

    blocked = any(c.get("status") == "BLOCKED" for c in checks.values())
    preflight = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "preflight_version": "p4-preflight-1",
        "working_directory": DEMOV2_ROOT,
        "status": "BLOCKED" if blocked else "READY",
        "checks": checks,
        "conclusion": (
            "P4 machinery is implementable now; real-input authority "
            "(P3 manifest / real chemistry / P2 Gate) is BLOCKED. P4 must "
            "NOT claim real performance or production PASS."
        ),
    }
    return preflight


def main() -> int:
    preflight = run()
    os.makedirs(REPORT_DIR, exist_ok=True)
    json_path = os.path.join(REPORT_DIR, "P4_PREFLIGHT.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(preflight, f, indent=2, ensure_ascii=False, default=str)
    md = [
        "# P4 Preflight", "",
        f"**Status:** {preflight['status']}",
        f"**Timestamp (UTC):** {preflight['timestamp']}", "",
        "| Check | Status | Detail |",
        "|-------|--------|--------|",
    ]
    for name, c in preflight["checks"].items():
        md.append(f"| {name} | {c['status']} | "
                  f"{c.get('blocked_reasons', []) or c.get('classification', '')} |")
    md.extend(["", "## Conclusion", "", preflight["conclusion"]])
    md_path = os.path.join(REPORT_DIR, "P4_PREFLIGHT.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Status: {preflight['status']}")
    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
