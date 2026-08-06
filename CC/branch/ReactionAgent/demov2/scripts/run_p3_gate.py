#!/usr/bin/env python
"""P3 Gate runner.  Exit codes: PASS=0, FAIL=1, BLOCKED=2."""
from __future__ import annotations

import json
import sys

sys.path.insert(0, ".")
from reaction_agent.p3.gate import exit_code_for, run_p3_gate  # noqa: E402


def main() -> int:
    report = run_p3_gate(run_mutations=True)
    print(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False))
    code = exit_code_for(report.verdict)
    print(f"\nP3 GATE VERDICT: {report.verdict} (exit {code})")
    return code


if __name__ == "__main__":
    sys.exit(main())
