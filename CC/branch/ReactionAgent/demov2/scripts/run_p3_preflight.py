#!/usr/bin/env python
"""P3 preflight runner — writes reports/p3/P3_PREFLIGHT.{json,md}."""
from __future__ import annotations

import json
import sys

sys.path.insert(0, ".")
from reaction_agent.p3.preflight import run_p3_preflight  # noqa: E402

REPORT_DIR = "reports/p3"


def main() -> int:
    import os
    os.makedirs(REPORT_DIR, exist_ok=True)
    report = run_p3_preflight()
    with open(f"{REPORT_DIR}/P3_PREFLIGHT.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    _write_md(report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def _write_md(report: dict) -> None:
    lines = ["# P3 Preflight", ""]
    lines.append("## Runtime")
    lines.append(f"- python: `{report['runtime']['python']}`")
    lines.append(f"- platform: `{report['runtime']['platform']}`")
    lines.append("")
    lines.append("## Capabilities")
    for name, cap in report["capabilities"].items():
        lines.append(f"- **{name}**: `{cap['state']}`"
                     + (f" ({cap.get('version', '')})" if cap.get('version') else ""))
    lines.append("")
    lines.append("## Evidence inventory")
    lines.append(f"- real snapshot available: `{report['evidence_inventory']['real_snapshot_available']}`")
    lines.append(f"- synthetic fixture reactions: `{report['evidence_inventory']['synthetic_fixture_reactions']}`")
    lines.append("")
    lines.append(f"## Real-evidence Gate status: **{report['real_evidence_gate_status']}**")
    lines.append("")
    lines.append("> Fixture evidence is synthetic_fixture and can only verify machinery;")
    lines.append("> it cannot satisfy real-evidence Gate items.")
    with open(f"{REPORT_DIR}/P3_PREFLIGHT.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
