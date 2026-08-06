#!/usr/bin/env python3
"""P5 audit-evidence collector — freeze raw artifacts for re-runnable proof.

R6-01: every key verification conclusion must carry a born-on-disk artifact
(command, exit code, full stdout/stderr, git SHA, UTC timestamp) under
``reports/p5/audit_evidence/`` plus a sha256 manifest. This closes the
"self-asserted, no artifact" defect class (P5-R4-02 / P5-R5-01).

Commands collected (all run in the worktree):
  1. pytest tests/p5                      (invariant suite)
  2. pytest tests/contracts               (contract suite)
  3. run_p5_gate.py                       (P5 gate 8/8 + G08)
  4. pytest tests/p5/test_p5_mutations.py (14 mutations)
  5. run_p4_gate_real.py                  (P4 gate 14/14 real)
  6. run_p5_packet_selfcheck.py           (packet integrity)
  7. pytest tests/p4                      (P4 regression)

Read-only: never mutates the packet or any source artifact.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import subprocess
import sys

_DEMOV2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_DIR = os.path.join(_DEMOV2, "reports", "p5", "audit_evidence")
PYTHON = os.environ.get("P5_PYTHON", "/opt/anaconda3/bin/python3")

COMMANDS = [
    ("p5_invariant_tests",
     [PYTHON, "-m", "pytest", "tests/p5", "-q", "-p", "no:cacheprovider"]),
    ("contracts_tests",
     [PYTHON, "-m", "pytest", "tests/contracts", "-q", "-p", "no:cacheprovider"]),
    ("p5_gate",
     [PYTHON, "scripts/run_p5_gate.py"]),
    ("p5_mutations",
     [PYTHON, "-m", "pytest", "tests/p5/test_p5_mutations.py", "-v", "--tb=line",
      "-p", "no:cacheprovider"]),
    ("p4_gate_real",
     [PYTHON, "scripts/run_p4_gate_real.py"]),
    ("p5_packet_selfcheck",
     [PYTHON, "scripts/run_p5_packet_selfcheck.py"]),
    ("p4_regression",
     [PYTHON, "-m", "pytest", "tests/p4", "-q", "-p", "no:cacheprovider"]),
]


def _git_sha(cwd: str) -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                           text=True, cwd=cwd, timeout=30)
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    git_sha = _git_sha(_DEMOV2)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifest: list[dict] = []
    failures = 0

    for name, cmd in COMMANDS:
        rel = f"{name}.log"
        path = os.path.join(EVIDENCE_DIR, rel)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=_DEMOV2, timeout=900)
            output = result.stdout + result.stderr
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            output = "[TIMEOUT 900s]"
            exit_code = -1

        record = {
            "command": " ".join(cmd),
            "exit_code": exit_code,
            "git_sha": git_sha,
            "timestamp_utc": timestamp,
            "output": output,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

        sha = _sha256_file(path)
        manifest.append({
            "file": rel,
            "sha256": sha,
            "exit_code": exit_code,
            "command": " ".join(cmd),
        })
        ok = "OK" if exit_code == 0 else f"EXIT {exit_code}"
        print(f"[{ok}] {rel} (sha256 {sha[:12]}...)")
        if exit_code != 0:
            failures += 1

    manifest_path = os.path.join(EVIDENCE_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "git_sha": git_sha,
            "timestamp_utc": timestamp,
            "files": manifest,
        }, f, indent=2, ensure_ascii=False)

    print(f"\naudit_evidence: {len(manifest)} artifacts, "
          f"manifest sha256 {_sha256_file(manifest_path)[:16]}...")
    if failures:
        print(f"FAILURES: {failures} commands exited non-zero")
        return 1
    print("ALL_ZERO_EXIT")
    return 0


if __name__ == "__main__":
    sys.exit(main())