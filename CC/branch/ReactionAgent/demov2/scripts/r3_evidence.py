#!/usr/bin/env python
"""Round 3 structured evidence recorder (CHATGPT_P3_ROUND_3 prompt §16).

Records every command with the full structured-evidence contract:
label / command / cwd / python_executable / started_at / finished_at /
duration_seconds / exit_code / collected / passed / failed / errors /
skipped / xfailed / xpassed / stdout_stderr_hash / raw_tail.

Records are APPENDED to reports/p3/round3_evidence/command_records.jsonl.
Nothing here fabricates counts: counts come only from parsing the real
pytest summary text; unparseable counts stay 0 and the fail-closed checks
in the report generator reject them.

Usage (CLI):
    python scripts/r3_evidence.py --label L [--finding R3-X] [--kind red|green|regression|adversarial|verification] \
        -- <command...>
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, "reports", "p3", "round3_evidence")
RECORDS_PATH = os.path.join(EVIDENCE_DIR, "command_records.jsonl")
P3_PY = "/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python"

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_pytest_counts(text: str) -> dict:
    """Parse pytest outcome counts from combined stdout/stderr text.

    Only real summary tokens are counted.  ``collected`` is filled when a
    ``N tests collected`` line exists; otherwise it stays 0 and the caller
    must obtain it from a separate collect-only run.
    """
    counts = {
        "collected": 0, "passed": 0, "failed": 0, "errors": 0,
        "skipped": 0, "xfailed": 0, "xpassed": 0,
    }
    clean = _ANSI.sub("", text)
    for line in clean.splitlines():
        for key, pat in (
            ("passed", r"(\d+) passed"),
            ("failed", r"(\d+) failed"),
            ("errors", r"(\d+) errors?"),
            ("skipped", r"(\d+) skipped"),
            ("xfailed", r"(\d+) xfailed"),
            ("xpassed", r"(\d+) xpassed"),
            ("collected", r"(\d+) tests? collected"),
        ):
            m = re.search(pat, line)
            if m:
                counts[key] = int(m.group(1))
    return counts


def record_command(
    label: str,
    cmd: list[str],
    *,
    cwd: str = PROJECT_ROOT,
    finding: str = "",
    kind: str = "",
    notes: str = "",
    python_executable: str = P3_PY,
    timeout: float = 2400.0,
) -> dict:
    """Run a command and append its structured record. Never fabricates."""
    started_at = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout,
        )
        exit_code = result.returncode
        raw = (result.stdout or "") + "\n" + (result.stderr or "")
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        exit_code = -1
        raw = (exc.stdout or "") + "\n" + (exc.stderr or "") if isinstance(exc.stdout, str) else str(exc)
        timed_out = True
    finished_at = time.time()
    raw_clean = _ANSI.sub("", raw)
    counts = parse_pytest_counts(raw_clean)
    record = {
        "label": label,
        "finding": finding,
        "kind": kind,
        "notes": notes,
        "command": cmd,
        "cwd": cwd,
        "python_executable": python_executable,
        "started_at": started_at,
        "started_at_iso": datetime.datetime.fromtimestamp(
            started_at, datetime.timezone.utc).isoformat(),
        "finished_at": finished_at,
        "finished_at_iso": datetime.datetime.fromtimestamp(
            finished_at, datetime.timezone.utc).isoformat(),
        "duration_seconds": round(finished_at - started_at, 3),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "collected": counts["collected"],
        "passed": counts["passed"],
        "failed": counts["failed"],
        "errors": counts["errors"],
        "skipped": counts["skipped"],
        "xfailed": counts["xfailed"],
        "xpassed": counts["xpassed"],
        "stdout_stderr_hash": sha256_text(raw_clean),
        "raw_tail": "\n".join(raw_clean.splitlines()[-12:]),
    }
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    with open(RECORDS_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(
        f"[r3-evidence] {label} finding={finding or '-'} kind={kind or '-'} "
        f"exit={exit_code} passed={counts['passed']} failed={counts['failed']} "
        f"errors={counts['errors']} hash={record['stdout_stderr_hash'][:16]} "
        f"duration={record['duration_seconds']}s"
    )
    return record


def main(argv: list[str]) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--finding", default="")
    parser.add_argument("--kind", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--cwd", default=PROJECT_ROOT)
    parser.add_argument("rest", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    cmd = args.rest
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("no command given", file=sys.stderr)
        return 2
    record = record_command(
        args.label, cmd, cwd=args.cwd, finding=args.finding,
        kind=args.kind, notes=args.notes,
    )
    print(record["raw_tail"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
