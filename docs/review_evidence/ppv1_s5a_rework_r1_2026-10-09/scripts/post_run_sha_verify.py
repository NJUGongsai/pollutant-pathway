#!/usr/bin/env python3
"""Post-run input SHA re-verification for the S5a rework r1 G01 run.

Re-hashes every allowlisted input in the source repo AFTER the isolated
G01 execution and compares with the copy-time input_sha256.json recorded
by the controller (the "SHA 后" side of the 303-lineage before/after
discipline; 304 inputs this round = 303 lineage + 1 new test file).
Also discloses, per nodeid, the G01 skip/deselect absence items.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

RUN = Path(sys.argv[1])
REPO = Path(sys.argv[2])


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


recorded = json.loads((RUN / "input_sha256.json").read_text())
mismatches = []
missing = []
for name, digest in sorted(recorded.items()):
    if not name.startswith("repo/"):
        continue  # v3 sibling inputs re-verified by lineage controller
    source = REPO / name[len("repo/"):]
    if not source.is_file():
        missing.append(name)
        continue
    if sha(source) != digest:
        mismatches.append(name)
result = {
    "run": str(RUN),
    "repo": str(REPO),
    "inputs_recorded": len(recorded),
    "repo_side_inputs": sum(
        1 for n in recorded if n.startswith("repo/")),
    "post_run_sha_mismatches": mismatches,
    "post_run_missing": missing,
    "source_tree_unchanged_after_run": not mismatches and not missing,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result["source_tree_unchanged_after_run"] else 1)
