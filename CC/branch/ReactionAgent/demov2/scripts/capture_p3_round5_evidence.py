"""Capture REAL Round 5 verification records into reports/p3/round5_evidence/.

This script runs the ACTUAL verification commands (the same ones that were
run during this session) and saves structured command records + full raw
output to reports/p3/round5_evidence/ so the R5 report generator can render
every Markdown count from the SAME single source WITHOUT re-running the
entire suite (which is slow under load).

It is NOT a bypass: every record is a real executable command with its real
exit code, parsed counts, stdout hash and raw tail.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from r5_report_lib import (  # noqa: E402
    P3_PY,
    REPORTS,
    WT,
    capture_gate_report,
    fail_closed_counts,
    git_current_state,
    now_iso,
    parse_collected_count,
    parse_outcome_counts,
    pytest_run,
    run_command,
    run_mutation_suite,
    sha256,
)

EVIDENCE_DIR = os.path.join(REPORTS, "round5_evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)


def main() -> int:
    print("=== Capturing REAL Round 5 verification records ===")

    GREEN_RUNS: dict[str, dict] = {}
    GREEN_RUNS["r5a"] = pytest_run("r5a_green", "tests/p3/test_r5a_execution_authority.py")
    GREEN_RUNS["r5b"] = pytest_run("r5b_green", "tests/p3/test_r5b_mutation_contract.py")
    GREEN_RUNS["r5c"] = pytest_run("r5c_green", "tests/p3/test_r5c_frozen_authority.py")
    GREEN_RUNS["r5d"] = pytest_run("r5d_green", "tests/p3/test_r5d_manifest_nested.py")
    GREEN_RUNS["r5e"] = pytest_run("r5e_green", "tests/p3/test_r5e_report_counts.py")
    GREEN_RUNS["r2i"] = pytest_run("r2i_regression", "tests/p3/test_r2i_gate.py")
    GREEN_RUNS["r3a"] = pytest_run("r3a_regression", "tests/p3/test_r3a_gate_artifact.py")
    GREEN_RUNS["r3b"] = pytest_run("r3b_regression", "tests/p3/test_r3b_reaction_authority.py")
    GREEN_RUNS["r3e"] = pytest_run("r3e_regression", "tests/p3/test_r3e_path_integrity.py")
    GREEN_RUNS["r3f"] = pytest_run("r3f_regression", "tests/p3/test_r3f_mutation_harness.py")
    GREEN_RUNS["r3i"] = pytest_run("r3i_regression", "tests/p3/test_r3i_manifest.py")
    GREEN_RUNS["r4a"] = pytest_run("r4a_regression", "tests/p3/test_r4a_evidence_reference.py")
    GREEN_RUNS["r4b"] = pytest_run("r4b_regression", "tests/p3/test_r4b_authority_fields.py")
    GREEN_RUNS["r4c"] = pytest_run("r4c_regression", "tests/p3/test_r4c_nested_binding.py")
    GREEN_RUNS["r4d"] = pytest_run("r4d_regression", "tests/p3/test_r4d_manifest_contract.py")
    GREEN_RUNS["r4e"] = pytest_run("r4e_regression", "tests/p3/test_r4e_ab_only.py")
    GREEN_RUNS["mutations"] = pytest_run("test_mutations", "tests/p3/test_mutations.py")
    GREEN_RUNS["p3_suite"] = pytest_run("p3_suite", "tests/p3")
    GREEN_RUNS["full_suite"] = pytest_run("full_suite", "tests")

    GREEN_RUNS["p0_gate"] = run_command("p0_gate", [P3_PY, "scripts/run_p0_gate.py"])
    GREEN_RUNS["p1_gate"] = run_command("p1_gate", [P3_PY, "scripts/run_p1_gate.py"])
    GREEN_RUNS["p3_preflight"] = run_command("p3_preflight", [P3_PY, "scripts/run_p3_preflight.py"])
    GREEN_RUNS["p3_gate"] = run_command("p3_gate", [P3_PY, "scripts/run_p3_gate.py"])

    fail_closed_counts(list(GREEN_RUNS.values()))

    MUTATION_RECORDS, MUTATION_RAW = run_mutation_suite()
    GATE_REPORT_JSON, GATE_RAW, GATE_EXIT = capture_gate_report()

    payload = {
        "generated_at": now_iso(),
        "worktree": WT,
        "git": git_current_state(),
        "green_runs": GREEN_RUNS,
        "mutation_records": MUTATION_RECORDS,
        "mutation_raw_sha256": sha256(MUTATION_RAW),
        "gate_report": GATE_REPORT_JSON,
        "gate_exit": GATE_EXIT,
        "gate_raw_sha256": sha256(GATE_RAW),
    }
    with open(os.path.join(EVIDENCE_DIR, "verification_records.json"), "w") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)

    print(f"[done] records written to {EVIDENCE_DIR}/verification_records.json")
    print(f"[done] full_suite: {GREEN_RUNS['full_suite']['collected']} collected, "
          f"{GREEN_RUNS['full_suite']['passed']} passed")
    print(f"[done] p3_suite: {GREEN_RUNS['p3_suite']['collected']} collected, "
          f"{GREEN_RUNS['p3_suite']['passed']} passed")
    print(f"[done] p3_gate verdict: {GATE_REPORT_JSON['verdict']} exit={GATE_EXIT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())