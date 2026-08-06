#!/usr/bin/env python
"""Generate P3 Round 3 deliverables (CHATGPT_P3_ROUND_3 prompt §17).

Every reported count comes from an ACTUAL command run with its real exit
code.  Pytest counts are fail-closed (R3-G):

- ``collected`` is taken from a REAL separate ``--collect-only -q`` run of
  the same selection and must be nonzero;
- outcome categories (passed/failed/errors/skipped/xfailed/xpassed) are
  parsed from the suite's own summary line;
- collected must equal the sum of ALL outcome categories (no double
  counting); zero, missing, malformed, interrupted, timeout or inconsistent
  summaries abort report generation.

Changed files are classified from structured Git state captured at the
round's start vs end (R3-H): inherited tracked modifications / inherited
untracked / Round-3 modified / Round-3 new / generated reports.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, ".")

from reaction_agent.hashing import canonical_hash  # noqa: E402

P3_PY = "/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(PROJECT_ROOT, "reports", "p3")
START_STATE_PATH = os.path.join(REPORT_DIR, "round3_evidence", "git_state_start.json")

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
OUTCOME_KEYS = ("passed", "failed", "errors", "skipped", "xfailed", "xpassed")


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text)


# -- R3-G pytest count parsing ------------------------------------------------


class PytestCountError(ValueError):
    """Raised when pytest output cannot be trusted (fail closed)."""


def parse_outcome_counts(text: str) -> dict:
    """Parse outcome counts from the LAST pytest summary line.

    Handles quiet/verbose summaries, failures, errors, skipped/xfailed/
    xpassed and warning summaries (warnings are NOT an outcome category).
    """
    counts = {key: 0 for key in OUTCOME_KEYS}
    clean = strip_ansi(text)
    for line in clean.splitlines():
        line_low = line.lower()
        if not any(tok in line_low for tok in (
            "passed", "failed", "error", "skipped", "xfailed", "xpassed",
            "no tests ran",
        )):
            continue
        matched_any = False
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
                matched_any = True
        if "no tests ran" in line_low:
            matched_any = True
        if matched_any:
            # keep scanning: the final summary line is authoritative and
            # later lines overwrite earlier counts.
            continue
    return counts


def parse_collected_count(text: str) -> int | None:
    """Parse the collected-test count from collect-only / header output."""
    clean = strip_ansi(text)
    collected = None
    for line in clean.splitlines():
        m = re.search(r"(\d+) tests? collected", line)
        if m:
            collected = int(m.group(1))
            continue
        m = re.search(r"collected (\d+) items?", line)
        if m:
            collected = int(m.group(1))
    return collected


def check_suite_exit(returncode: int, text: str) -> None:
    """Fail closed on interrupted / timeout / collection-error signatures."""
    clean = strip_ansi(text).lower()
    if "!!! interrupted" in clean or "keyboardinterrupt" in clean:
        raise PytestCountError("pytest run was interrupted")
    if "no tests ran" in clean:
        raise PytestCountError("pytest collected no tests")
    if "error" in clean and ("errors during collection" in clean
                              or "collection error" in clean):
        raise PytestCountError("pytest reported collection errors")
    if returncode not in (0, 1):
        raise PytestCountError(f"pytest exit code {returncode} (expected 0/1)")


def counts_are_consistent(counts: dict, collected: int) -> bool:
    """collected must equal the sum of ALL outcome categories."""
    if collected <= 0:
        return False
    return sum(counts[key] for key in OUTCOME_KEYS) == collected


# -- command recording (§16 structured evidence) -------------------------------


def _base_record(label: str, cmd: list[str], cwd: str) -> dict:
    return {
        "label": label,
        "command": cmd,
        "cwd": cwd,
        "python_executable": P3_PY,
    }


def run_command(label: str, cmd: list[str], *, cwd: str = PROJECT_ROOT) -> dict:
    """Run a command and record its real output + parsed pytest counts."""
    started_at = time.time()
    timed_out = False
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=3600,
        )
        exit_code = result.returncode
        raw = (result.stdout or "") + "\n" + (result.stderr or "")
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = -1
        raw = f"TIMEOUT\n{exc}"
    finished_at = time.time()
    raw_clean = strip_ansi(raw)
    counts = parse_outcome_counts(raw_clean)
    record = _base_record(label, cmd, cwd)
    record.update({
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": round(finished_at - started_at, 3),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "collected": parse_collected_count(raw_clean) or 0,
        **counts,
        "stdout_stderr_hash": hashlib.sha256(raw_clean.encode("utf-8")).hexdigest(),
        "raw_tail": "\n".join(raw_clean.splitlines()[-8:]),
    })
    print(f"[run] {label}: exit={exit_code} collected={record['collected']} "
          f"passed={record['passed']} failed={record['failed']} "
          f"errors={record['errors']} timed_out={timed_out}")
    return record


def run_pytest_suite(label: str, selection: list[str]) -> dict:
    """Run one pytest suite + a separate collect-only run and reconcile.

    Fail closed when collected is zero/missing, outcomes are unparseable, or
    collected != sum(outcome categories).
    """
    suite_cmd = [P3_PY, "-m", "pytest", *selection,
                 "-q", "-p", "no:cacheprovider", "--color=no"]
    record = run_command(label, suite_cmd)
    collect_cmd = [P3_PY, "-m", "pytest", *selection,
                   "--collect-only", "-q", "-p", "no:cacheprovider", "--color=no"]
    collect_record = run_command(f"{label}_collect_only", collect_cmd)
    collected = parse_collected_count(
        strip_ansi(" ".join(collect_record["raw_tail"].split()))
    )
    if collected is None:
        # raw_tail may truncate the line; rerun parse on a fresh capture
        proc = subprocess.run(collect_cmd, capture_output=True, text=True,
                              cwd=PROJECT_ROOT, timeout=1800)
        collected = parse_collected_count(strip_ansi(proc.stdout + proc.stderr))
    record["collected"] = collected or 0
    record["collected_source"] = "separate --collect-only run"
    record["consistent"] = counts_are_consistent(
        {k: record[k] for k in OUTCOME_KEYS}, record["collected"]
    )
    return record


def fail_closed(records: list[dict]) -> None:
    """Abort report generation if any required verification is not solid."""
    pytest_labels = {
        "p3_suite", "full_suite", "mutations_r2", "mutation_harness_suite",
        "isolated_p3_suite",
    }
    problems = []
    for record in records:
        label = record["label"]
        if label in pytest_labels:
            if record.get("timed_out"):
                problems.append(f"{label}: timed out")
            elif record["exit_code"] != 0:
                problems.append(f"{label}: exit={record['exit_code']}")
            elif record.get("collected", 0) <= 0:
                problems.append(f"{label}: collected count missing/zero")
            elif not record.get("consistent", False):
                problems.append(
                    f"{label}: collected ({record.get('collected')}) != "
                    f"sum(outcomes) ({sum(record[k] for k in OUTCOME_KEYS)})"
                )
            elif record["passed"] == 0 and record["failed"] == 0:
                problems.append(f"{label}: no pass/fail parsed")
        elif label in ("p0_gate", "p1_gate", "p3_preflight"):
            if record["exit_code"] != 0:
                problems.append(f"{label}: exit={record['exit_code']}")
        elif label == "p3_gate":
            if record["exit_code"] not in (0, 1, 2):
                problems.append(f"{label}: unexpected exit={record['exit_code']}")
    if problems:
        raise SystemExit(f"report generation FAILED CLOSED: {'; '.join(problems)}")


# -- R3-H Git state classification ----------------------------------------------


def git_current_state(cwd: str) -> dict:
    """Structured Git state: tracked modifications + untracked files."""
    status = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=cwd,
    ).stdout
    modified_tracked = sorted({
        line[3:] for line in status.splitlines() if line[:2] == " M"
    })
    untracked = sorted(
        subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, cwd=cwd,
        ).stdout.split()
    )
    return {
        "modified_tracked": modified_tracked,
        "untracked": untracked,
    }


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_round3_changes(start_state: dict, cwd: str) -> dict:
    """Classify the final Git state against the round-start snapshot.

    Categories (never label the whole final dirty state as this round's):
    - inherited_tracked_modified: tracked modifications already present at
      round start (P0/P1 inheritance);
    - inherited_untracked: untracked at start and still byte-identical;
    - round3_modified: files present at start whose content changed OR
      tracked files newly modified during Round 3;
    - round3_new: files untracked at end but absent at start;
    - generated_reports: round3 files under reports/p3/.
    """
    end_state = git_current_state(cwd)
    start_tracked = set(start_state.get("modified_tracked_inherited", []))
    start_untracked = set(start_state.get("untracked_inherited", []))
    start_hashes = dict(start_state.get("untracked_sha256", {}))

    inherited_tracked_modified = sorted(start_tracked)
    round3_modified_tracked = sorted(
        p for p in end_state["modified_tracked"] if p not in start_tracked
    )

    end_untracked = set(end_state["untracked"])
    round3_new = sorted(end_untracked - start_untracked)
    still_present = end_untracked & start_untracked
    inherited_untracked = []
    round3_modified_untracked = []
    for path in sorted(still_present):
        full = os.path.join(cwd, path)
        if os.path.isfile(full):
            current = _sha256_file(full)
            if start_hashes.get(path) == current:
                inherited_untracked.append(path)
            else:
                round3_modified_untracked.append(path)
        else:
            inherited_untracked.append(path)

    generated_reports = sorted(
        p for p in round3_new + round3_modified_untracked
        if p.startswith("reports/p3/")
    )
    return {
        "inherited_tracked_modified": inherited_tracked_modified,
        "inherited_untracked": inherited_untracked,
        "round3_modified_tracked": round3_modified_tracked,
        "round3_modified_untracked": round3_modified_untracked,
        "round3_new": round3_new,
        "generated_reports": generated_reports,
    }


# -- report rendering --------------------------------------------------------------


def _gate_md(gate: dict) -> str:
    lines = ["# P3 Gate Report — Round 3", ""]
    lines.append(f"- verdict: `{gate['verdict']}`")
    lines.append(f"- derived_from_artifacts: `{gate['derived_from_artifacts']}`")
    lines.append(
        f"- interface_manifest_schema_hash: "
        f"`{gate.get('interface_manifest_schema_hash', '')}`"
    )
    mutations = gate.get("mutations", [])
    caught = sum(1 for m in mutations if m.get("caught"))
    valid = sum(1 for m in mutations if m.get("valid"))
    lines.append(f"- mutations caught: `{caught}/{len(mutations)}`")
    lines.append(f"- mutations valid (real baseline+mutated evidence): `{valid}/{len(mutations)}`")
    lines.append("")
    lines.append("| ID | Title | Status | Evidence kind |")
    lines.append("|----|-------|--------|---------------|")
    for item in gate["items"]:
        lines.append(
            f"| {item['item_id']} | {item['title']} | **{item['status']}** "
            f"| {item['evidence_kind']} |"
        )
    lines.append("")
    lines.append("## Mutation evidence (R3-F: separate real executions)")
    lines.append("")
    lines.append("| mutation | target | expected | observed | baseline | mutated | caught |")
    lines.append("|----------|--------|----------|----------|----------|---------|--------|")
    for m in mutations:
        lines.append(
            f"| {m['mutation_id']} | {m['target_gate_item']} "
            f"| {m['expected_failure_code']} | {m['observed_failure_code']} "
            f"| {m['baseline']['exit_code']}/{m['baseline_status']} "
            f"| {m['mutated']['exit_code']}/{m['mutated_status']} "
            f"| {m['caught']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    os.makedirs(REPORT_DIR, exist_ok=True)
    round_started_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print("=== Running verification commands (real outputs) ===")
    records: list[dict] = []
    records.append(run_pytest_suite("p3_suite", ["tests/p3"]))
    records.append(run_pytest_suite("full_suite", ["tests"]))
    records.append(run_pytest_suite("mutations_r2", ["tests/p3/test_mutations.py"]))
    records.append(run_pytest_suite(
        "mutation_harness_suite", ["tests/p3/test_r3f_mutation_harness.py"],
    ))

    records.append(run_command("p0_gate", [P3_PY, "scripts/run_p0_gate.py"]))
    records.append(run_command("p1_gate", [P3_PY, "scripts/run_p1_gate.py"]))
    records.append(run_command("p3_preflight", [P3_PY, "scripts/run_p3_preflight.py"]))
    records.append(run_command("p3_gate", [P3_PY, "scripts/run_p3_gate.py"]))

    # R3-H: isolated run — full copy WITHOUT git metadata; proves the suite
    # does not depend on the real (dirty) worktree state.  The legacy
    # benchmark/ source (read by reaction_agent.roles.cofactors via a path
    # relative to the ReactionAgent/ parent directory) is copied alongside
    # so the isolated tree is self-contained.
    isolated_dir = tempfile.mkdtemp(prefix="p3_round3_isolated_")
    try:
        iso_root = os.path.join(isolated_dir, "ReactionAgent")
        os.makedirs(iso_root)
        dest = os.path.join(iso_root, "demov2")
        shutil.copytree(
            PROJECT_ROOT, dest,
            ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__",
                                          ".pytest_cache"),
        )
        legacy_benchmark = os.path.join(
            os.path.dirname(PROJECT_ROOT), "benchmark"
        )
        if os.path.isdir(legacy_benchmark):
            shutil.copytree(legacy_benchmark, os.path.join(iso_root, "benchmark"))
        records.append(run_pytest_suite_isolated(dest))
    finally:
        shutil.rmtree(isolated_dir, ignore_errors=True)

    fail_closed(records)

    # -- Gate / manifest / preflight / mutations (typed) ----------------------
    from reaction_agent.p3.gate import run_p3_gate, exit_code_for
    from reaction_agent.p3.manifest import build_interface_manifest, manifest_schema_hash
    from reaction_agent.p3.preflight import run_p3_preflight
    from reaction_agent.p3.mutation_harness import clear_cache

    clear_cache()  # report generation records a fresh, uncached execution
    gate = run_p3_gate(run_mutations=True).model_dump(mode="json")
    manifest = build_interface_manifest()
    preflight = run_p3_preflight()

    # -- Git classification (R3-H) --------------------------------------------
    with open(START_STATE_PATH, encoding="utf-8") as fh:
        start_state = json.load(fh)
    changed = classify_round3_changes(start_state, PROJECT_ROOT)
    end_state = git_current_state(PROJECT_ROOT)

    # -- Deliverables ------------------------------------------------------------
    mhash = manifest_schema_hash(manifest)
    evidence = {
        "round": 3,
        "round_started_iso": round_started_iso,
        "gate": gate,
        "verification_commands": records,
        "p3_p4_interface_manifest_schema_hash": mhash,
        "changed_files": changed,
        "git_state_end": end_state,
        "real_evidence_gate": preflight["real_evidence_gate_status"],
        "mutation_rules": {
            "baseline_not_PASS": "INVALID_BASELINE and Gate FAIL",
            "mutation_PASS": "escaped mutation and Gate FAIL",
            "mutation_ERROR": "Gate FAIL",
            "observed_code_mismatch": "Gate FAIL",
            "helper_only_without_production_path": "invalid mutation evidence",
        },
    }
    _write("P3_ROUND_3_AUDIT_EVIDENCE.json", evidence)
    _write("P3_GATE_REPORT_ROUND_3.json", gate)
    _write_text("P3_GATE_REPORT_ROUND_3.md", _gate_md(gate))
    _write("P3_MUTATION_RESULTS_ROUND_3.json", {
        "mutation_rules": evidence["mutation_rules"],
        "mutations": gate["mutations"],
    })
    _write("p3_p4_interface_manifest_round_3.json", manifest)
    _write("P3_ROUND_3_CHANGED_FILES.json", {
        "start_state_source": START_STATE_PATH,
        **changed,
    })

    print(f"[done] gate verdict={gate['verdict']} "
          f"exit={exit_code_for(gate['verdict'])} manifest_hash={mhash[:16]}")
    return 0


def run_pytest_suite_isolated(dest: str) -> dict:
    """The isolated-run variant executes inside the copied tree."""
    label = "isolated_p3_suite"
    suite_cmd = [P3_PY, "-m", "pytest", "tests/p3",
                 "-q", "-p", "no:cacheprovider", "--color=no"]
    record = run_command(label, suite_cmd, cwd=dest)
    collect_cmd = [P3_PY, "-m", "pytest", "tests/p3",
                   "--collect-only", "-q", "-p", "no:cacheprovider", "--color=no"]
    proc = subprocess.run(collect_cmd, capture_output=True, text=True,
                          cwd=dest, timeout=1800)
    collected = parse_collected_count(strip_ansi(proc.stdout + proc.stderr))
    record["collected"] = collected or 0
    record["collected_source"] = "separate --collect-only run (isolated copy)"
    record["consistent"] = counts_are_consistent(
        {k: record[k] for k in OUTCOME_KEYS}, record["collected"]
    )
    return record


def _write(name: str, payload: dict) -> None:
    with open(os.path.join(REPORT_DIR, name), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"[write] reports/p3/{name}")


def _write_text(name: str, text: str) -> None:
    with open(os.path.join(REPORT_DIR, name), "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"[write] reports/p3/{name}")


if __name__ == "__main__":
    sys.exit(main())
