"""P4 Gate contract test (PASS-capable machinery + honest BLOCKED real-input)."""
from __future__ import annotations

import json
import os
import subprocess
import sys

DEMOV2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, DEMOV2_ROOT)

# Recursion guard: when the gate runs pytest as a subprocess, this env var
# tells inner pytest NOT to re-run the gate.
os.environ.setdefault("P4_GATE_RECURSION_GUARD", "1")


def _run_gate() -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["P4_GATE_RECURSION_GUARD"] = "1"
    return subprocess.run(
        [sys.executable, "scripts/run_p4_gate.py"],
        cwd=DEMOV2_ROOT, capture_output=True, text=True, timeout=600,
        env=env,
    )


def _run_mutations() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/run_p4_mutations.py"],
        cwd=DEMOV2_ROOT, capture_output=True, text=True, timeout=600,
    )


def test_gate_machinery_checks_pass_on_fixture():
    """P4 Gate: machinery checks (identity/support/rank/abstention/run) pass
    on the PASS-capable contract fixture — the mutation baseline must be valid."""
    from scripts.run_p4_gate import GATE_CHECKS
    for gate_id, _name, fn in GATE_CHECKS:
        result = fn()
        # Machinery checks must not be BLOCKED; blocked is reserved for
        # real-input checks (P3/P2/real-evidence).
        assert not result.get("blocked"), f"{gate_id} unexpectedly blocked: {result['evidence']}"


def test_gate_does_not_fake_pass_with_missing_real_input():
    """P4 Gate: with P3 interface absent and evidence synthetic-only, the gate
    must NOT claim PASS. Exit code must be the BLOCKED code (not 0)."""
    proc = _run_gate()
    assert proc.returncode != 0, "gate must not exit 0 (PASS) without real P3 input"
    report_path = os.path.join(DEMOV2_ROOT, "reports", "p4", "P4_GATE_REPORT.json")
    assert os.path.isfile(report_path)
    with open(report_path) as f:
        report = json.load(f)
    status = report.get("status", "")
    assert status in {"BLOCKED", "NOT_READY_FOR_CHATGPT_AUDIT",
                      "P4_IMPLEMENTATION_COMPLETE_GATE_BLOCKED"}
    # Real-input checks are honestly BLOCKED, machinery checks PASS.
    blocked = [c for c in report.get("checks", []) if c.get("blocked")]
    assert blocked, "expected honest BLOCKED real-input checks"
    for c in blocked:
        gate_num = int(c["gate_id"].split("-")[1][1:])
        assert c["gate_id"].startswith("P4-G") and gate_num >= 12, \
            f"machinery check {c['gate_id']} must not be blocked"


def test_mutations_flip_pass_to_fail_on_pass_capable_fixture():
    """P4 Gate: mutation runner must catch every mutation as PASS→FAIL on the
    PASS-capable fixture (never a BLOCKED baseline pretending to be caught)."""
    proc = _run_mutations()
    results_path = os.path.join(DEMOV2_ROOT, "reports", "p4", "P4_MUTATION_RESULTS.json")
    assert os.path.isfile(results_path), "mutation runner must write results JSON"
    with open(results_path) as f:
        results = json.load(f)
    mutations = results.get("mutations", [])
    assert mutations, "no mutations recorded"
    caught = [m for m in mutations if m.get("caught")]
    assert len(caught) == len(mutations), (
        f"not all mutations caught: {sum(1 for m in mutations if not m.get('caught'))} missed")
    # Every caught mutation must be a genuine PASS→FAIL flip.
    for m in mutations:
        assert m.get("baseline_status") == "PASS", \
            f"{m['mutation_id']} baseline must be PASS-capable, got {m.get('baseline_status')}"
        assert m.get("expected_status") == "FAIL", \
            f"{m['mutation_id']} expected FAIL, got {m.get('expected_status')}"
        assert m.get("escaped") is not True, f"{m['mutation_id']} escaped"
        assert m.get("error") is not True, f"{m['mutation_id']} errored"
