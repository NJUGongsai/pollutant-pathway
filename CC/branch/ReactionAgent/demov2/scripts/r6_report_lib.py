"""R6-E single-source report libraries (pure functions, no side effects).

Every Markdown count in the Round 6 submission / worklog / audit evidence is
generated from the SAME structured command record through these functions.
This module is import-safe (no subprocess / no file writes at import time).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

WT = "/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2"
P3_PY = os.environ.get(
    "P3_PY",
    "/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python",
)
REPORTS = os.path.join(WT, "reports", "p3")

_OUTCOME_KEYS = ("passed", "failed", "errors", "skipped", "xfailed", "xpassed")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record_counts(record: dict) -> dict:
    return {
        "collected": record.get("collected", 0),
        "passed": record.get("passed", 0),
        "failed": record.get("failed", 0),
        "errors": record.get("errors", 0),
        "skipped": record.get("skipped", 0),
        "xfailed": record.get("xfailed", 0),
        "xpassed": record.get("xpassed", 0),
    }


def counts_are_consistent(record: dict) -> bool:
    counts = record_counts(record)
    if counts["collected"] <= 0:
        return False
    return sum(counts[k] for k in _OUTCOME_KEYS) == counts["collected"]


def fail_closed_counts(records: list[dict]) -> None:
    """Abort report generation on ANY count inconsistency (R5-E / R6-E)."""
    problems: list[str] = []
    for record in records:
        label = record.get("label", "?")
        if not record.get("stdout_stderr_hash"):
            problems.append(f"{label}: missing stdout_stderr_hash")
        is_pytest = not label.startswith(("p0_", "p1_", "p3_", "probe_", "red_", "green_"))
        if is_pytest:
            if record.get("exit_code") != 0:
                problems.append(f"{label}: exit={record.get('exit_code')}")
            if not counts_are_consistent(record):
                problems.append(
                    f"{label}: collected ({record.get('collected')}) != "
                    f"sum(outcomes) ({sum(record.get(k, 0) for k in _OUTCOME_KEYS)}) "
                    f"or collected==0"
                )
            if record.get("passed", 0) == 0 and record.get("failed", 0) == 0:
                problems.append(f"{label}: no pass/fail parsed")
        else:
            if label in ("p0_gate", "p1_gate"):
                if record.get("exit_code") != 0:
                    problems.append(f"{label}: exit={record.get('exit_code')}")
            elif label == "p3_gate":
                if record.get("exit_code") not in (0, 1, 2):
                    problems.append(f"{label}: unexpected exit={record.get('exit_code')}")
    if problems:
        raise SystemExit(
            f"report generation FAILED CLOSED (R6-E): {'; '.join(problems)}"
        )


def render_verification_matrix(records: list[dict]) -> str:
    lines = [
        "| label | exit | collected | passed | failed | errors | skipped |",
        "|-------|------|-----------|--------|--------|--------|---------|",
    ]
    for rec in records:
        counts = record_counts(rec)
        lines.append(
            f"| {rec.get('label', '?')} | {rec.get('exit_code', '?')} | "
            f"{counts['collected']} | {counts['passed']} | {counts['failed']} | "
            f"{counts['errors']} | {counts['skipped']} |"
        )
    return "\n".join(lines)


def render_report_header(
    *,
    generated_at: str,
    worktree: str,
    branch: str,
    head: str,
    git_status: str,
) -> str:
    return (
        f"- generated_at: {generated_at}\n"
        f"- worktree: {worktree}\n"
        f"- branch: **{branch}**\n"
        f"- head: **{head}**\n"
        f"- git_status:\n```text\n{git_status}\n```"
    )


def run_command(label: str, cmd: list[str], *, collect_only: bool = False) -> dict:
    started = time.time()
    proc = subprocess.run(cmd, cwd=WT, capture_output=True, text=True, timeout=3600)
    finished = time.time()
    output = proc.stdout + proc.stderr
    record = {
        "label": label,
        "command": cmd,
        "cwd": WT,
        "python_executable": P3_PY,
        "started_at": now_iso(),
        "finished_at": now_iso(),
        "duration_seconds": round(finished - started, 3),
        "exit_code": proc.returncode,
        "stdout_stderr_hash": sha256(output),
        "raw_tail": "\n".join(output.splitlines()[-8:]),
    }
    if collect_only:
        record["collected"] = parse_collected_count(output)
    else:
        counts = parse_outcome_counts(output)
        record.update(counts)
        record["collected"] = parse_collected_count(output) or 0
    return record


def pytest_run(label: str, test: str) -> dict:
    record = run_command(label, [P3_PY, "-m", "pytest", test, "-q",
                                 "-p", "no:cacheprovider", "--color=no"])
    collect = run_command(
        label + "_collect",
        [P3_PY, "-m", "pytest", test, "--collect-only", "-q",
         "-p", "no:cacheprovider", "--color=no"],
        collect_only=True,
    )
    record["collected"] = collect["collected"]
    return record


def parse_outcome_counts(text: str) -> dict:
    counts = {k: 0 for k in _OUTCOME_KEYS}
    for line in text.splitlines():
        line_low = line.lower()
        if not any(tok in line_low for tok in (
            "passed", "failed", "error", "skipped", "xfailed", "xpassed",
        )):
            continue
        for key, pat in (
            ("passed", r"(\d+) passed"),
            ("failed", r"(\d+) failed"),
            ("errors", r"(\d+) errors?"),
            ("skipped", r"(\d+) skipped"),
            ("xfailed", r"(\d+) xfailed"),
            ("xpassed", r"(\d+) xpassed"),
        ):
            m = re.search(pat, line)
            if m:
                counts[key] = int(m.group(1))
    return counts


def parse_collected_count(text: str) -> int:
    collected = 0
    for line in text.splitlines():
        m = re.search(r"(\d+) tests? collected", line)
        if m:
            collected = int(m.group(1))
            continue
        m = re.search(r"collected (\d+) items?", line)
        if m:
            collected = int(m.group(1))
    return collected


def git_current_state() -> dict:
    status = subprocess.run(
        ["git", "status", "--short"], capture_output=True, text=True, cwd=WT,
    ).stdout
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True, cwd=WT,
    ).stdout.split()
    return {
        "status": status,
        "untracked": untracked,
        "branch": subprocess.run(
            ["git", "branch", "--show-current"], capture_output=True, text=True,
            cwd=WT,
        ).stdout.strip(),
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=WT,
        ).stdout.strip(),
    }


def build_manifest() -> dict:
    code = (
        "from reaction_agent.p3.manifest import build_interface_manifest, "
        "manifest_schema_hash;"
        "import json;"
        "m = build_interface_manifest();"
        "print(json.dumps({'manifest': m, 'schema_hash': manifest_schema_hash(m)}))"
    )
    proc = subprocess.run([P3_PY, "-c", code], cwd=WT, capture_output=True,
                          text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"manifest build failed: {proc.stderr[-2000:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def run_mutation_suite() -> tuple[list[dict], str]:
    code = (
        "from reaction_agent.p3.mutation_harness import clear_cache, run_mutation_suite;"
        "clear_cache();"
        "import json; print(json.dumps(run_mutation_suite(use_cache=False)))"
    )
    proc = subprocess.run(
        [P3_PY, "-c", code], cwd=WT, capture_output=True, text=True, timeout=1800,
    )
    output = proc.stdout + proc.stderr
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"mutation suite failed: {output[-2000:]}")
    records = json.loads(proc.stdout.strip().splitlines()[-1])
    return records, output


def capture_gate_report() -> tuple[dict, str, int]:
    proc = subprocess.run(
        [P3_PY, "scripts/run_p3_gate.py"], cwd=WT, capture_output=True,
        text=True, timeout=1800,
    )
    output = proc.stdout + proc.stderr
    lines = output.splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip().startswith("{"))
    text = "\n".join(lines[start:])
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(text)
    return obj, output, proc.returncode


def run_green_probes() -> tuple[list[dict], str]:
    """Run the R6 attack probes (GREEN: every attack is FAIL)."""
    proc = subprocess.run(
        [P3_PY, "scripts/p3/r6_attack_probes.py"], cwd=WT, capture_output=True,
        text=True, timeout=1800,
    )
    output = proc.stdout + proc.stderr
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"green probes failed: {output[-2000:]}")
    probes = json.loads(proc.stdout.strip().splitlines()[-1])["probes"]
    return probes, output


def changed_files_from_tree(commit: str) -> dict:
    """R6-E: changed-files manifest generated from the FINAL commit/tree (not
    from a hand-filled working tree)."""
    proc = subprocess.run(
        ["git", "show", "--name-only", "--format=", commit],
        capture_output=True, text=True, cwd=WT,
    )
    names = [n for n in proc.stdout.splitlines() if n.strip()]
    return {
        "commit": commit,
        "parent": subprocess.run(
            ["git", "rev-parse", f"{commit}^"], capture_output=True, text=True,
            cwd=WT,
        ).stdout.strip(),
        "files": names,
        "count": len(names),
    }