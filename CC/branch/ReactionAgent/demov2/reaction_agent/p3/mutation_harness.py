"""R3-F real mutation evidence harness.

Every mutation case is executed as TWO SEPARATE subprocess runs (baseline
and mutated) through ``scripts/run_p3_mutation_case.py``.  The harness
records, for each run, the real command, exit code, parsed status, observed
failure code, artifact hash, stdout/stderr hash and duration — then applies
the fail-closed rules:

- baseline not PASS          -> INVALID_BASELINE, Gate FAIL
- mutated PASS (escape)      -> Gate FAIL
- mutated ERROR              -> Gate FAIL
- observed code != expected  -> Gate FAIL

No helper-only shortcut: every scenario executes the relevant production
path (loader / transform / sites / validation / kernel / gate / schemas).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
CASE_RUNNER = os.path.join(PROJECT_ROOT, "scripts", "run_p3_mutation_case.py")

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# R6-B: the strictly versioned mutation receipt schema.  The subprocess emits
# ONE receipt block (marker-delimited) carrying ALL fields bound to the SAME
# trusted execution; the verifier parses it from the raw output and requires
# the stored typed fields to EXACTLY match it.
RECEIPT_SCHEMA_VERSION = "p3-mutation-receipt-1"
RECEIPT_BEGIN = "---P3_MUTATION_RECEIPT_1---"
RECEIPT_END = "---P3_MUTATION_RECEIPT_END---"

# Module-level cache: the suite is deterministic per worktree state; the Gate
# and its tests call this repeatedly and must not re-fork ~28 subprocesses on
# every call.  ``clear_cache()`` is exposed for report generation.
_SUITE_CACHE: list | None = None

# R6-B: the process-session nonce.  Created once per process (the first
# mutation execution); every receipt in this process is bound to it.  A
# receipt from a previous execution (different nonce) is rejected by the
# verifier.
_SESSION_NONCE: str | None = None


def session_nonce() -> str:
    """The trusted execution session nonce for THIS process's mutation runs."""
    global _SESSION_NONCE
    if _SESSION_NONCE is None:
        _SESSION_NONCE = secrets.token_hex(16)
    return _SESSION_NONCE


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_strict_receipt(raw_output: str) -> dict | None:
    """R6-B: parse the UNIQUE strict JSON receipt from the raw output.

    Returns the receipt dict, or None when the marker-delimited block is
    missing / malformed / has an unknown schema version.  The receipt is the
    ONLY execution-semantic payload: the verifier derives the typed artifact
    and every outcome field from it.
    """
    lines = raw_output.splitlines()
    for i, line in enumerate(lines):
        if line.strip() != RECEIPT_BEGIN:
            continue
        for j in range(i + 1, min(i + 8, len(lines))):
            if lines[j].strip() == RECEIPT_END:
                payload = "\n".join(lines[i + 1:j]).strip()
                try:
                    parsed = json.loads(payload)
                except json.JSONDecodeError:
                    return None
                if (
                    isinstance(parsed, dict)
                    and parsed.get("receipt_schema_version") == RECEIPT_SCHEMA_VERSION
                ):
                    return parsed
                return None
    return None


def _run_case_subprocess(
    mutation_id: str,
    variant: str,
    *,
    python_executable: str,
    run_id: str,
    session_nonce: str,
    component: str,
    schema_version: str,
    case_name: str,
    timeout: float = 600.0,
) -> dict:
    """Run ONE case variant in its own subprocess and record real evidence.

    R5-B: the receipt carries the REAL raw output (``raw_output``) and the
    parsed typed artifact (``artifact``) so the verifier can RECOMPUTE the
    stdout hash and the artifact hash from the actual output — never trust a
    submitter-provided non-empty string.

    R6-B: the subprocess emits a UNIQUE, STRICT, VERSIONED JSON receipt
    (marker-delimited) binding session nonce / run id / case / variant /
    component / schema version / command / exit code / status / failure code
    / typed artifact / canonical artifact hash to ONE trusted execution.  The
    harness parses that receipt and builds the typed record FROM it — the
    stored artifact is not an independently modifiable copy.
    """
    cmd = [
        python_executable, CASE_RUNNER,
        "--case", mutation_id, "--variant", variant,
        "--run-id", run_id, "--session-nonce", session_nonce,
    ]
    started_at = time.time()
    timed_out = False
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, cwd=PROJECT_ROOT,
            timeout=timeout,
        )
        exit_code = proc.returncode
        raw = (proc.stdout or "") + "\n" + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = -1
        raw = f"TIMEOUT after {timeout}s\n{exc}"
    finished_at = time.time()
    # R5-B: strip the raw output ONCE here so the stored stdout hash and the
    # stored raw_output are over the SAME byte string.  (pydantic
    # ``str_strip_whitespace`` would otherwise strip the trailing newline
    # from ``raw_output`` after the hash was computed, making the hash
    # unrecomputable.)
    raw_clean = _ANSI.sub("", raw).strip()

    status = "ERROR"
    failure_code = ""
    artifact_hash = ""
    artifact: dict = {}
    receipt = parse_strict_receipt(raw_clean)
    if receipt is not None:
        if (
            receipt.get("case") != case_name
            or receipt.get("variant") != variant
            or receipt.get("mutation_id") != mutation_id
            or receipt.get("run_id") != run_id
            or receipt.get("session_nonce") != session_nonce
            or receipt.get("component") != component
            or receipt.get("schema_version") != schema_version
        ):
            status = "ERROR"
            failure_code = "RECEIPT_IDENTITY_MISMATCH"
        elif receipt.get("status") in ("PASS", "FAIL", "ERROR"):
            status = receipt["status"]
            failure_code = receipt.get("failure_code", "") or ""
            artifact_hash = receipt.get("artifact_hash", "") or ""
            artifact = receipt.get("artifact") or {}
        else:
            status = "ERROR"
            failure_code = "RECEIPT_STATUS_INVALID"
    elif timed_out:
        failure_code = "TIMEOUT"
    else:
        failure_code = "UNPARSEABLE_OUTPUT"

    return {
        "command": cmd,
        "cwd": PROJECT_ROOT,
        "python_executable": python_executable,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": round(finished_at - started_at, 3),
        "exit_code": exit_code,
        "status": status,
        "failure_code": failure_code,
        "artifact_hash": artifact_hash,
        "stdout_stderr_hash": _sha256(raw_clean),
        "raw_output": raw_clean,
        "raw_tail": "\n".join(raw_clean.splitlines()[-8:]),
        "artifact": artifact,
        "timed_out": timed_out,
        "run_id": run_id,
        "component": component,
        "schema_version": schema_version,
        "case": case_name,
        "variant": variant,
        "session_nonce": session_nonce,
    }


def adjudicate(baseline: dict, mutated: dict, expected_failure_code: str) -> dict:
    """Pure fail-closed rules (unit-testable without subprocesses)."""
    problems: list[str] = []
    if baseline["status"] != "PASS":
        problems.append("INVALID_BASELINE")
    if mutated["status"] == "PASS":
        problems.append("MUTATION_ESCAPED")
    elif mutated["status"] == "ERROR":
        problems.append("MUTATED_RUN_ERROR")
    elif mutated["failure_code"] != expected_failure_code:
        problems.append("OBSERVED_CODE_MISMATCH")
    caught = (
        mutated["status"] == "FAIL"
        and bool(mutated["failure_code"])
        and mutated["failure_code"] == expected_failure_code
        and baseline["status"] == "PASS"
    )
    return {
        "baseline_status": "PASS" if baseline["status"] == "PASS" else "INVALID_BASELINE",
        "mutated_status": mutated["status"],
        "observed_failure_code": mutated["failure_code"],
        "caught": caught,
        "valid": not problems,
        "invalid_reason": "; ".join(problems),
    }


def run_mutation_suite(
    *,
    python_executable: str | None = None,
    use_cache: bool = True,
    run_id: str = "p3_gate",
) -> list[dict]:
    """Execute the full R3-F mutation suite (baseline + mutated, separately).

    Returns one record per mutation case with the complete structured
    evidence for BOTH runs plus the adjudication.

    R6-B: every receipt is bound to the SAME trusted execution session (the
    process session nonce) and the SAME run identity as the Gate report.
    """
    global _SUITE_CACHE
    if use_cache and _SUITE_CACHE is not None:
        return _SUITE_CACHE
    from reaction_agent.p3.mutations_round3 import MUTATION_REGISTRY
    python = python_executable or sys.executable
    nonce = session_nonce()
    results: list[dict] = []
    for case in MUTATION_REGISTRY:
        baseline = _run_case_subprocess(
            case["mutation_id"], "baseline", python_executable=python,
            run_id=run_id, session_nonce=nonce,
            component=case["component"], schema_version=case["schema_version"],
            case_name=case["baseline_case"],
        )
        mutated = _run_case_subprocess(
            case["mutation_id"], "mutated", python_executable=python,
            run_id=run_id, session_nonce=nonce,
            component=case["component"], schema_version=case["schema_version"],
            case_name=case["mutated_case"],
        )
        verdict = adjudicate(baseline, mutated, case["expected_failure_code"])
        results.append({
            "mutation_id": case["mutation_id"],
            "target_gate_item": case["target_gate_item"],
            "expected_failure_code": case["expected_failure_code"],
            "baseline": baseline,
            "mutated": mutated,
            **verdict,
        })
    if use_cache:
        _SUITE_CACHE = results
    return results


def clear_cache() -> None:
    global _SUITE_CACHE
    _SUITE_CACHE = None


def suite_started_at_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
