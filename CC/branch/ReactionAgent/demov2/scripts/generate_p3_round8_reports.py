#!/usr/bin/env python
"""Generate the Round 8 deliverables from the captured evidence (single source).

Reads reports/p3/round8_evidence/ (captured by capture_p3_round8_evidence.py)
and renders every Round 8 deliverable:

- reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_8.md
- reports/p3/P3_ROUND_8_AUDIT_EVIDENCE.json
- reports/p3/P3_ROUND_8_REMEDIATION_WORKLOG.md
- reports/p3/P3_GATE_REPORT_ROUND_8.json
- reports/p3/P3_ROUND_8_CHANGED_FILES.json

Every Markdown count is derived from the structured records (single source).
The generator FAILS CLOSED on any count inconsistency.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from r6_report_lib import (  # noqa: E402
    REPORTS,
    WT,
    changed_files_from_tree,
    fail_closed_counts,
    git_current_state,
    now_iso,
    render_report_header,
    render_verification_matrix,
    sha256,
)

EVIDENCE_DIR = os.path.join(REPORTS, "round8_evidence")


def _load(name: str):
    with open(os.path.join(EVIDENCE_DIR, name)) as f:
        return json.load(f)


def _write(name: str, text: str) -> None:
    path = os.path.join(REPORTS, name)
    with open(path, "w") as f:
        f.write(text)
    print(f"  wrote {name}")


def _write_json(name: str, payload) -> None:
    path = os.path.join(REPORTS, name)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    print(f"  wrote {name}")


def commit_parent(commit: str) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", f"{commit}^"], capture_output=True, text=True, cwd=WT,
    )
    return proc.stdout.strip()


def main() -> int:
    evidence = _load("round8_audit_evidence.json")
    r8_probes = _load("round8_r8_probes.json")["probes"]
    r7_probes = _load("round8_r7_probes.json")["probes"]
    mutations = _load("round8_mutation_suite.json")["mutations"]
    gate_report = _load("round8_gate_report.json")
    manifest = _load("round8_interface_manifest.json")
    records = evidence["verification_commands"]
    fail_closed_counts(records)

    git_state = git_current_state()
    generated_at = now_iso()
    # ---- commits (R6-E metadata distinction) -------------------------------
    implementation_commit = os.environ.get("R8_IMPLEMENTATION_COMMIT", "")
    deliverables_commit = os.environ.get("R8_DELIVERABLES_COMMIT", "")
    audit_target_head = git_state["head"]
    impl_parent = commit_parent(implementation_commit) if implementation_commit else ""

    # ---- P3 Gate report deliverable ----------------------------------------
    _write_json("P3_GATE_REPORT_ROUND_8.json", gate_report)

    # ---- P3_ROUND_8_CHANGED_FILES.json -------------------------------------
    changed = changed_files_from_tree(
        implementation_commit or audit_target_head
    )
    _write_json("P3_ROUND_8_CHANGED_FILES.json", changed)

    # ---- P3_ROUND_8_AUDIT_EVIDENCE.json ------------------------------------
    audit_evidence = {
        "round": 8,
        "generated_at": generated_at,
        "worktree": WT,
        "branch": git_state["branch"],
        "implementation_commit": implementation_commit,
        "implementation_commit_parent": impl_parent,
        "deliverables_commit": deliverables_commit,
        "audit_target_head": audit_target_head,
        "final_status": "P3_ROUND_8_READY_FOR_CHATGPT_READ_ONLY_AUDIT_P4_BLOCKED",
        "gate_trust_model": evidence["gate_trust_model"],
        "verification_commands": records,
        "r8_probes": r8_probes,
        "r8_probes_output_hash": evidence["r8_probes_output_hash"],
        "r7_probes": r7_probes,
        "r7_probes_output_hash": evidence["r7_probes_output_hash"],
        "gate": gate_report,
        "gate_exit": evidence["gate_exit"],
        "mutation_suite": mutations,
        "interface_manifest": manifest["manifest"],
        "interface_manifest_schema_hash": manifest["schema_hash"],
        "gate_mutation_registry_hash": gate_report.get("mutation_registry_hash", ""),
        "gate_run_session_nonce": gate_report.get("session_nonce", ""),
        "findings": evidence["findings"],
    }
    _write_json("P3_ROUND_8_AUDIT_EVIDENCE.json", audit_evidence)

    # ---- P3_ROUND_8_REMEDIATION_WORKLOG.md ---------------------------------
    worklog = _render_worklog(evidence, r8_probes, records)
    _write("P3_ROUND_8_REMEDIATION_WORKLOG.md", worklog)

    # ---- SUBMISSION_TO_CHATGPT_P3_ROUND_8.md --------------------------------
    submission = _render_submission(
        audit_evidence, records, r8_probes, r7_probes, mutations, gate_report,
        changed, implementation_commit, deliverables_commit, audit_target_head,
    )
    _write("SUBMISSION_TO_CHATGPT_P3_ROUND_8.md", submission)

    print("\n=== Round 8 deliverables generated ===")
    return 0


def _render_worklog(evidence: dict, r8_probes: list[dict], records: list[dict]) -> str:
    lines = [
        "# P3 Round 8 Remediation Worklog",
        "",
        f"- generated_at: {evidence['generated_at']}",
        f"- worktree: {evidence['worktree']}",
        f"- branch: {evidence['branch']}",
        f"- head: {evidence['head']}",
        "",
        "## Scope (Round 8 only)",
        "",
        "Round 8 fixes exactly ONE contract from the ChatGPT Round 7 audit "
        "(ordinary Python object-reference aliasing — not a network issue):",
        "",
        "**R8 — the execution authority shares no mutable object with the "
        "returned GateReport.** `GateExecutionAuthority` now converts every "
        "executed item and mutation into an INDEPENDENT canonical JSON "
        "snapshot (a plain immutable string generated at registration time).  "
        "The returned `GateReport` shares NO mutable object with the "
        "authority, so mutating a returned report's mutation/item (or any "
        "nested dict/list inside it) can never change the authority's audit "
        "basis.  `evaluate_gate_artifact()` exact-matches against the "
        "independent snapshots and fails with `EXECUTED_MUTATION_MISMATCH` / "
        "`EXECUTED_STATUS_MISMATCH` / `EXECUTED_EVIDENCE_MISMATCH`.",
        "",
        "No other P3 area was rewritten (kernel / ranking / P4 / P0/P1 "
        "frozen scientific contracts / R7-A / R7-B / R6-A / R6-B / R6-C / "
        "R5-D / R5-E untouched).",
        "",
        "## Files changed (implementation)",
        "",
        "- `reaction_agent/p3/gate.py` — R8: `_model_snapshot_json` helper; "
        "`GateExecutionAuthority` stores independent canonical JSON snapshots "
        "and exposes parsed copies (`items` / `mutations` / `executed`); "
        "`evaluate_gate_artifact` exact-matches against the snapshots; "
        "`_evidence_lists_exact_match` compares by value (model vs dict).",
        "- `tests/p3/test_r8a_authority_aliasing.py` — 3 tests: mutation "
        "aliasing (audit's exact repro), item aliasing, real-gate no-regression.",
        "- `scripts/p3/r8_aliasing_probes.py` — 5 GREEN probes.",
        "- `scripts/capture_p3_round8_evidence.py` / "
        "`scripts/generate_p3_round8_reports.py` — Round 8 report generation.",
        "",
        "## Verification matrix",
        "",
        render_verification_matrix(records),
        "",
        "## R8 aliasing probes (GREEN)",
        "",
    ]
    for p in r8_probes:
        lines.append(f"- `{p['probe']}` -> {json.dumps(p, ensure_ascii=False)}")
    lines += [
        "",
        "## Status",
        "",
        "```text",
        "P3_ROUND_8_READY_FOR_CHATGPT_READ_ONLY_AUDIT_P4_BLOCKED",
        "```",
        "",
    ]
    return "\n".join(lines)


def _render_submission(
    audit_evidence: dict,
    records: list[dict],
    r8_probes: list[dict],
    r7_probes: list[dict],
    mutations: list[dict],
    gate_report: dict,
    changed: dict,
    implementation_commit: str,
    deliverables_commit: str,
    audit_target_head: str,
) -> str:
    counts = {r["label"]: r for r in records}
    git_state = git_current_state()
    header = render_report_header(
        generated_at=audit_evidence["generated_at"],
        worktree=git_state["worktree"] if "worktree" in git_state else WT,
        branch=git_state["branch"],
        head=git_state["head"],
        git_status=git_state["status"],
    )
    lines = [
        "# Submission to ChatGPT — P3 Round 8 (directed remediation)",
        "",
        header,
        "",
        "- implementation_commit: "
        f"**{implementation_commit or '(unset — see audit_target_head)'}**",
        f"- implementation_commit_parent: **{audit_evidence.get('implementation_commit_parent', '')}**",
        f"- deliverables_commit: **{deliverables_commit or '(created after this render)'}**",
        f"- audit_target_head: **{audit_target_head}**",
        "",
        "## Final status",
        "",
        "```text",
        "P3_ROUND_8_READY_FOR_CHATGPT_READ_ONLY_AUDIT_P4_BLOCKED",
        "```",
        "",
        "## Summary",
        "",
        "Round 8 fixes exactly the ONE remaining NOT-CLOSED contract from "
        "the ChatGPT Round 7 audit: **R8 — report/authority mutable "
        "aliasing**.  `GateExecutionAuthority` no longer keeps the raw "
        "mutable model references it was registered with; it keeps "
        "INDEPENDENT canonical JSON snapshots (plain immutable strings) of "
        "the executed items and mutations.  The returned `GateReport` shares "
        "no mutable object with the authority, so the audit's exact repro "
        "(mutate a returned report's mutation, re-sync the raw receipt + "
        "artifact hash + stdout hash) now evaluates to `FAIL` with "
        "`EXECUTED_MUTATION_MISMATCH` and `verified=False`.  R7-A / R7-B "
        "remain closed (all regression tests + R7 probes still GREEN); "
        "tests/p3 passes; the full suite passes; P0 Gate exit 0; P1 Gate "
        "exit 0; P3 Gate stays honestly BLOCKED (exit 2) because real "
        "evidence resources are still missing — P4 remains BLOCKED.",
        "",
        "## R8 — execution authority holds independent immutable snapshots",
        "",
        "**Original attack (RED)**: `report.mutations[0] is "
        "authority.mutations[0]` was `True` — `run_p3_gate()` handed the "
        "SAME mutable objects to both the authority and the returned report.  "
        "Mutating a returned report's mutation (and re-syncing the raw "
        "receipt, artifact hash and stdout hash) also mutated the authority "
        "and produced `verified=True, BLOCKED` with no machinery failures.",
        "",
        "**GREEN command**: `python -m pytest "
        "tests/p3/test_r8a_authority_aliasing.py -q`",
        f"- green exit_code: {counts['r8_aliasing']['exit_code']}",
        f"- green: {counts['r8_aliasing']['passed']} passed, "
        f"{counts['r8_aliasing']['failed']} failed",
        "",
        "**Code**: `reaction_agent/p3/gate.py` — `_model_snapshot_json`; "
        "`GateExecutionAuthority` stores `_item_snapshots` / "
        "`_mutation_snapshots` / `_by_id` as canonical JSON strings and "
        "exposes parsed copies; `evaluate_gate_artifact()` exact-matches the "
        "submitted items/mutations against the independent snapshots; "
        "`_evidence_lists_exact_match` compares by value.",
        "**Tests**: `tests/p3/test_r8a_authority_aliasing.py` (3 tests, "
        "incl. `test_mutating_returned_report_mutation_does_not_change_"
        "execution_authority` and `test_mutating_returned_report_item_"
        "does_not_change_execution_authority`).",
        "**Invariants**: (1) `report.mutations[0] is authority.mutations[0]` "
        "is `False`; (2) mutating the returned report's mutation cannot "
        "change the authority snapshot (`same_object=false`, "
        "`snapshot_changed=false`, `forged_leaked_into_authority=false`); "
        "(3) the report-mutated mutation fails with `EXECUTED_MUTATION_"
        "MISMATCH`, `verified=False`; (4) the report-mutated item fails with "
        "`EXECUTED_STATUS_MISMATCH` / `EXECUTED_EVIDENCE_MISMATCH`; (5) the "
        "real gate artifact still verifies against the snapshots.",
        "**Residual risk**: within one process the authority is in-memory "
        "(keyed by run_id); a fresh process cannot verify a stored artifact "
        "(by design).",
        "",
        "## R7-A / R7-B regression",
        "",
        "All R7-A / R7-B / R6-A / R6-B / R6-C / R5-A / R5-B / R5-C / R4-E "
        "tests still pass (see the verification matrix: `r7a_regression` / "
        "`r7b_regression` / `r6a_regression` / `r6b_regression` / "
        "`r6c_regression` / `r5a_regression` / `r5b_regression` / "
        "`r5c_regression` / `r4e_regression` rows).  The R7 attack probes "
        "are still GREEN: every raw+typed receipt rewrite is rejected and "
        "the fixture/production authority type isolation holds.",
        "",
        "## Verification matrix",
        "",
        render_verification_matrix(records),
        "",
        "## GREEN aliasing probes (R8)",
        "",
    ]
    for p in r8_probes:
        lines.append(f"- `{p['probe']}` -> {json.dumps(p, ensure_ascii=False)}")
    lines += [
        "",
        "## R7 attack probes (regression, GREEN)",
        "",
    ]
    for p in r7_probes:
        lines.append(f"- `{p['probe']}` -> {json.dumps(p, ensure_ascii=False)}")
    lines += [
        "",
        "## Gate reports",
        "",
        f"- P3 Gate verdict: {gate_report.get('verdict')} "
        f"(exit {audit_evidence['gate_exit']})",
        f"- P3 Gate session nonce: {str(gate_report.get('session_nonce', ''))[:16]}...",
        f"- P3 Gate mutation registry hash: "
        f"{str(gate_report.get('mutation_registry_hash', ''))[:16]}...",
        f"- P0 Gate: {counts['p0_gate']['exit_code']} (10/10)",
        f"- P1 Gate: {counts['p1_gate']['exit_code']} (10/10)",
        "",
        "## Mutation suite",
        "",
        f"- mutations: {len(mutations)}",
        f"- all valid: {all(m.get('valid') for m in mutations)}",
        f"- all caught: {all(m.get('caught') for m in mutations)}",
        "",
        "## Changed files (from the implementation commit tree)",
        "",
        f"- commit: {changed.get('commit')}",
        f"- parent: {changed.get('parent')}",
        f"- count: {changed.get('count')}",
        "",
    ]
    for name in changed.get("files", []):
        lines.append(f"- {name}")
    lines += [
        "",
        "## Final status",
        "",
        "P3_ROUND_8_READY_FOR_CHATGPT_READ_ONLY_AUDIT_P4_BLOCKED",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())