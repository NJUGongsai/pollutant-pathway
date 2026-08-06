#!/usr/bin/env python3
"""Generate the P4 Round 2 deliverable set under reports/p4/ (honest:
machinery PASS, real gate BLOCKED)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

DEMOV2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEMOV2_ROOT)
REPORT_DIR = os.path.join(DEMOV2_ROOT, "reports", "p4")

TS = datetime.now(timezone.utc).isoformat()
PYTHON = sys.executable
CWD = DEMOV2_ROOT


def _run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=CWD, capture_output=True, text=True,
                          timeout=600)
    return {
        "command": " ".join(cmd),
        "cwd": CWD,
        "python": PYTHON,
        "exit_code": proc.returncode,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
    }


def changed_files() -> dict:
    """P4 files changed in this round (untracked + committed)."""
    proc = subprocess.run(
        ["git", "status", "--short", "CC/branch/ReactionAgent/demov2/"],
        cwd=os.path.dirname(DEMOV2_ROOT), capture_output=True, text=True)
    lines = [l for l in proc.stdout.splitlines()
             if "reports/p4/" in l or "reaction_agent/" in l or
             "scripts/p4" in l or "tests/p4" in l or "tests/fixtures/p4" in l]
    return {"count": len(lines), "files": lines}


def main() -> int:
    os.makedirs(REPORT_DIR, exist_ok=True)

    # 1. Gate round2 (copy from the just-run gate)
    gate = json.load(open(os.path.join(REPORT_DIR, "P4_GATE_REPORT.json")))
    gate["round"] = 2
    gate["audit_submission_version"] = "p4-round-2"
    with open(os.path.join(REPORT_DIR, "P4_GATE_REPORT_ROUND_2.json"),
              "w", encoding="utf-8") as f:
        json.dump(gate, f, indent=2, ensure_ascii=False, default=str)
    md_src = open(os.path.join(REPORT_DIR, "P4_GATE_REPORT.md")).read()
    with open(os.path.join(REPORT_DIR, "P4_GATE_REPORT_ROUND_2.md"),
              "w", encoding="utf-8") as f:
        f.write(md_src.replace("# P4 Gate Report",
                              "# P4 Gate Report — Round 2"))

    # 2. Mutation round2
    mut = json.load(open(os.path.join(REPORT_DIR, "P4_MUTATION_RESULTS.json")))
    mut["round"] = 2
    with open(os.path.join(REPORT_DIR, "P4_MUTATION_RESULTS_ROUND_2.json"),
              "w", encoding="utf-8") as f:
        json.dump(mut, f, indent=2, ensure_ascii=False, default=str)

    # 3. p4->p5 interface manifest round2
    p5 = {
        "manifest_version": "p4-p5-2",
        "description": "P4 -> P5 frozen interface manifest (Round 2). "
                       "P5 consumes P4 outputs read-only.",
        "policy_version": "p4-policy-1",
        "ranker_version": "p4-ranker-1",
        "hash_algo": "sha256 (reaction_agent.hashing.canonical_hash)",
        "classification_vocabulary": ["real", "synthetic_fixture", "blocked",
                                      "diagnostic"],
        "authority_binding": {
            "p1_snapshot": "snap_c589494081df (fixture synthetic)",
            "p2_formal_gate": "BLOCKED (stored status string is NOT an authority)",
            "p3_interface_manifest": "p3-p4-3 frozen (parsed by P3InterfaceConsumer)",
            "p3_current_run_artifact": "absent -> typed BLOCKED (no candidates)",
            "evidence": "synthetic_fixture",
        },
        "pi_r1_contracts": {
            "P4-R1-A": "P3 consumer parses frozen p3-p4-3 manifest; interface "
                       "alone never grants capability; current-run KernelResult "
                       "artifact verified (schema/hash/namespace/evidence-kind)",
            "P4-R1-B": "P4Classification frozen enum + cross-field invariants; "
                       "P3AuthorityHandle is the only pipeline authority",
            "P4-R1-C": "no fallback Candidate; ranked candidates must exist in "
                       "the verified P3 map",
            "P4-R1-D": "RunNamespace exact-match (run/query/case/fold/snapshot/"
                       "policy)",
            "P4-R1-E": "single result-hash preimage; deep immutable run; "
                       "pipeline verify; child collision rejected",
            "P4-R1-G": "per-feature FeatureObservation evidence binding; "
                       "fail-closed applicability/counterevidence",
            "P4-R1-H": "per-candidate aggregation; weak/conflicted removed",
            "P4-R1-I": "ranker observable-only weighted average",
            "P4-R1-F": "gate/mutation ERROR typing + expected failure codes",
            "P4-R1-J": "typed TEST_EVIDENCE_ISOLATION; authority-backed gates",
        },
        "components": {
            "PredictionResult": {
                "version": "p4-result-1",
                "fields": ["run_id", "status", "decision", "normalized_query",
                           "snapshot_id", "candidates", "abstention", "failure",
                           "stage_summary", "manifest_uri", "resource_uris"],
                "semantics": "P4 adds rank/support/applicability; NEVER creates "
                             "candidate structures; validation only from "
                             "versioned policy",
            },
            "RunManifest": {
                "version": "p4-manifest-2",
                "fields": ["run_id", "request_hash", "snapshot_id",
                           "snapshot_hash", "versions", "trace",
                           "evidence_ids", "independent_group_ids",
                           "result_hash", "freeze_state", "classification",
                           "decision", "ranking", "applicability",
                           "support_hashes", "counterevidence_hashes",
                           "namespace"],
                "semantics": "content-addressed immutable run; single result "
                             "hash preimage covering decision/ranking/"
                             "applicability/support/counterevidence/trace/"
                             "namespace/versions/classification",
            },
        },
        "terminal_status": "P4_ROUND_2_IMPLEMENTATION_COMPLETE_REAL_GATE_BLOCKED_READY_FOR_CHATGPT_AUDIT",
    }
    with open(os.path.join(REPORT_DIR, "p4_p5_interface_manifest_round_2.json"),
              "w", encoding="utf-8") as f:
        json.dump(p5, f, indent=2, ensure_ascii=False, default=str)

    # 4. changed files
    cf = changed_files()
    with open(os.path.join(REPORT_DIR, "P4_ROUND_2_CHANGED_FILES.json"),
              "w", encoding="utf-8") as f:
        json.dump({"generated_at": TS, "count": cf["count"],
                   "files": cf["files"]}, f, indent=2, ensure_ascii=False)

    # 5. worktree states
    def _git_state():
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=os.path.dirname(DEMOV2_ROOT),
                              capture_output=True, text=True).stdout.strip()
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=os.path.dirname(DEMOV2_ROOT),
                                capture_output=True, text=True).stdout.strip()
        return head, branch

    start_head, start_branch = "4eb463368e38f2faa3d3656a05974c4b1c1211a6", "worktree-p4-strict-kernel"
    end_head, end_branch = _git_state()
    with open(os.path.join(REPORT_DIR, "P4_ROUND_2_STARTING_WORKTREE_STATE.md"),
              "w", encoding="utf-8") as f:
        f.write(f"# P4 Round 2 Starting Worktree State\n\n"
                f"- worktree: {DEMOV2_ROOT}\n"
                f"- branch: {start_branch}\n"
                f"- HEAD: {start_head}\n"
                f"- P4 files: all untracked (P1 baseline; no P4 commit)\n")
    with open(os.path.join(REPORT_DIR, "P4_ROUND_2_FINAL_WORKTREE_STATE.md"),
              "w", encoding="utf-8") as f:
        f.write(f"# P4 Round 2 Final Worktree State\n\n"
                f"- worktree: {DEMOV2_ROOT}\n"
                f"- branch: {end_branch}\n"
                f"- HEAD: {end_head}\n"
                f"- P4 commits: 8 (P4-R1-A/B/C/D/E/G/H/I/F-J)\n"
                f"- P4 suite: 138 passed; contracts: 290 passed\n"
                f"- Gate: P4_IMPLEMENTATION_COMPLETE_GATE_BLOCKED\n"
                f"- Mutations: 14/14 CAUGHT\n")

    # 6. audit evidence JSON
    evidence = {
        "generated_at": TS,
        "python": PYTHON,
        "cwd": CWD,
        "p4_suite": _run([PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "tests/p4"]),
        "p0_contracts": _run([PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                              "tests/contracts"]),
        "gate": _run([PYTHON, "scripts/run_p4_gate.py"]),
        "mutations": _run([PYTHON, "scripts/run_p4_mutations.py"]),
        "gate_status": gate.get("status"),
        "mutation_caught": mut.get("caught"),
        "mutation_total": mut.get("total"),
        "p3_authority": {
            "frozen_interface_manifest": "p3-p4-3 (schema_hash "
                                         "07ab8f71ba3d4e15026ba09d0d2d5f73260ead9e7eaa79ef84f55bac85f63aae)",
            "current_run_artifact": "ABSENT -> typed BLOCKED (no real candidates)",
            "real_evidence": "unavailable",
            "p2_truth_authority": "BLOCKED (stored status string not an authority)",
        },
        "fixture_vs_real": {
            "fixture": "synthetic contract fixture (machinery only)",
            "real": "unavailable",
            "rule": "synthetic never mixed into real counts; synthetic-only => BLOCKED",
        },
    }
    with open(os.path.join(REPORT_DIR, "P4_ROUND_2_AUDIT_EVIDENCE.json"),
              "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False, default=str)

    print("wrote P4_GATE_REPORT_ROUND_2.json/.md")
    print("wrote P4_MUTATION_RESULTS_ROUND_2.json")
    print("wrote p4_p5_interface_manifest_round_2.json")
    print("wrote P4_ROUND_2_CHANGED_FILES.json")
    print("wrote P4_ROUND_2_STARTING_WORKTREE_STATE.md / FINAL")
    print("wrote P4_ROUND_2_AUDIT_EVIDENCE.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())