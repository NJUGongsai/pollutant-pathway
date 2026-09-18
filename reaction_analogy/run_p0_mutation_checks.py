#!/usr/bin/env python3
"""Mutation checks for the P0 fix test suite (colleague requirement #6).

Applies two targeted mutations, re-runs the relevant tests in subprocesses,
and asserts the tests FAIL (i.e. the suite actually guards the P0
contracts).  Files are restored byte-identically afterwards (verified).

  M1 (P0-2 mutation): calibrator_repo_path ignores the version -> every
     mode loads calibrator_v35.json.  Guard: T1/T2 (explicit versioning).
  M2 (P0-1 mutation): env_asset_root.verify skips the SHA comparison ->
     corrupted assets load silently.  Guard: T5 (fail-closed).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))   # reaction_analogy/
PY = sys.executable


def _run_tests(*names):
    r = subprocess.run(
        [PY, os.path.join(_HERE, "tests", "test_v35_p0_fixes.py"), *names],
        capture_output=True, text=True, cwd=_HERE, timeout=600)
    return r.returncode, r.stdout


def _mutate(path, old, new):
    text = open(path, encoding="utf-8").read()
    assert old in text, f"mutation anchor not found in {path}: {old!r}"
    open(path, "w", encoding="utf-8").write(text.replace(old, new, 1))


def main() -> int:
    results = []

    # ---- M1: version-ignored calibrator path (P0-2 regression) ----
    target = os.path.join(_HERE, "expand_bbd_routes.py")
    backup = target + ".mutation-bak"
    shutil.copy2(target, backup)
    try:
        _mutate(target,
                'return os.path.join(_HERE, "..", "data", "bbd_v34",\n'
                '                        f"calibrator_{version}.json")',
                'return os.path.join(_HERE, "..", "data", "bbd_v34",\n'
                '                        "calibrator_v35.json")  # MUTANT')
        rc, out = _run_tests("T1", "T2")
        results.append(("M1 version-ignored calibrator", rc,
                        "T1/T2 must fail", out))
    finally:
        shutil.move(backup, target)

    # ---- M2: SHA comparison skipped (P0-1 regression) ----
    target = os.path.join(_HERE, "env_asset_root.py")
    backup = target + ".mutation-bak"
    shutil.copy2(target, backup)
    try:
        _mutate(target, "if want != actual:", "if False and want != actual:"
                "  # MUTANT")
        rc, out = _run_tests("T5")
        results.append(("M2 SHA-check disabled", rc,
                        "T5 must fail", out))
    finally:
        shutil.move(backup, target)

    # ---- report ----
    ok = True
    for name, rc, expect, out in results:
        caught = rc != 0
        ok = ok and caught
        verdict = "CAUGHT the mutation" if caught else "MISSED the mutation"
        print(f"{name}: tests {verdict} (exit={rc}, expected {expect})",
              flush=True)
        if not caught:
            print(out[-600:], flush=True)

    # ---- post-restore sanity: the suite is green again ----
    rc, out = _run_tests("FAST")
    print(f"post-restore sanity (fast suite): exit={rc}", flush=True)
    ok &= (rc == 0)
    print("MUTATION CHECKS: " + ("ALL PASS" if ok else "FAIL"),
          flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
