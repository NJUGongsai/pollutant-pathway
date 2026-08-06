"""R5-E: report counts must come from ONE structured command record source.

Round 4 defect: the worklog's finding paragraphs carried stale counts
(20/20, 29/29, 20/20, 18/18) while the verification matrix and submission
carried new numbers (21/21, 30/30, 22/22, 19/19) — the independent current
total was 96 passed, so the tests passed but the report was internally
inconsistent.

R5-E contract:
- every Markdown count in the submission / worklog / audit evidence is
  generated from the SAME structured command record (label/command/exit_code/
  collected/passed/failed/errors/skipped/stdout_stderr_hash);
- finding paragraphs, verification matrix, submission and audit-evidence
  JSON numbers are IDENTICAL by construction (single source);
- no count is hand-copied and no expected-collected value is hard-coded;
- the generator FAILS CLOSED when a number is inconsistent (e.g. a finding
  paragraph count that does not match the command record, or collected !=
  sum(outcomes));
- RED evidence must correspond to real executable commands (never a bare
  "ChatGPT audit repro" string);
- every report carries generation timestamp, worktree, branch, HEAD and real
  Git state.

These tests validate the generator's single-source and fail-closed
machinery.  They are RED on the R4 report generator (no single-source
enforcement) and GREEN after R5-E.
"""
from __future__ import annotations

import pytest

import scripts.r5_report_lib as gen5


def _record(label="r5a", collected=15, passed=15, failed=0, errors=0,
            skipped=0, exit_code=0):
    return {
        "label": label,
        "command": ["python", "-m", "pytest", "tests/p3/test_r5a.py",
                    "-q", "-p", "no:cacheprovider", "--color=no"],
        "cwd": "/worktree",
        "python_executable": "/venv/bin/python",
        "started_at": "2026-08-03T00:00:00Z",
        "finished_at": "2026-08-03T00:00:01Z",
        "duration_seconds": 1.0,
        "exit_code": exit_code,
        "collected": collected,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "xfailed": 0,
        "xpassed": 0,
        "stdout_stderr_hash": "a" * 64,
        "raw_tail": "15 passed in 1.0s",
    }


# -- single-source count extraction -------------------------------------------


def test_counts_extracted_from_record_single_source():
    """The finding paragraph count must be DERIVED from the command record,
    never hand-copied."""
    record = _record()
    counts = gen5.record_counts(record)
    assert counts == {
        "collected": 15, "passed": 15, "failed": 0, "errors": 0,
        "skipped": 0, "xfailed": 0, "xpassed": 0,
    }


def test_finding_paragraph_renders_from_record():
    record = _record()
    text = gen5.render_finding_paragraph("R5-A", record)
    assert "15/15 passed" in text
    assert "0 failed" in text


def test_verification_matrix_renders_from_same_records():
    records = [_record("r5a"), _record("r5b", collected=16, passed=16)]
    matrix = gen5.render_verification_matrix(records)
    assert "| r5a | 0 | 15 | 15 | 0 | 0 | 0 |" in matrix
    assert "| r5b | 0 | 16 | 16 | 0 | 0 | 0 |" in matrix


# -- fail-closed consistency ---------------------------------------------------


def test_fail_closed_on_collected_sum_mismatch():
    """collected != sum(outcomes) must abort report generation."""
    record = _record(collected=15, passed=14)  # 14 != 15
    with pytest.raises(SystemExit):
        gen5.fail_closed_counts([record])


def test_fail_closed_on_passed_zero_with_positive_collected():
    record = _record(collected=15, passed=0, failed=0)
    with pytest.raises(SystemExit):
        gen5.fail_closed_counts([record])


def test_fail_closed_on_nonzero_exit_for_pytest_suite():
    record = _record(exit_code=1, collected=15, passed=15)
    with pytest.raises(SystemExit):
        gen5.fail_closed_counts([record])


def test_fail_closed_on_missing_stdout_hash():
    record = _record()
    record["stdout_stderr_hash"] = ""
    with pytest.raises(SystemExit):
        gen5.fail_closed_counts([record])


def test_consistent_record_passes():
    record = _record()
    gen5.fail_closed_counts([record])  # must not raise


# -- RED evidence must reference real commands ---------------------------------


def test_red_evidence_requires_real_command():
    """A finding whose RED evidence has no executable command must fail
    closed (no bare 'ChatGPT audit repro' strings)."""
    finding = {
        "finding_id": "R5-A",
        "red_command": None,  # not a real executable command
        "red_exit_code": 1,
    }
    with pytest.raises(SystemExit):
        gen5.validate_red_evidence(finding)


def test_red_evidence_with_real_command_passes():
    finding = {
        "finding_id": "R5-A",
        "red_command": ["python", "-m", "pytest",
                        "tests/p3/test_r5a_execution_authority.py",
                        "-q", "-p", "no:cacheprovider", "--color=no"],
        "red_exit_code": 1,
        "red_observed_failure": "2 failed",
        "red_stdout_hash": "b" * 64,
    }
    gen5.validate_red_evidence(finding)  # must not raise


# -- report header carries git state -------------------------------------------


def test_report_header_requires_git_state():
    header = gen5.render_report_header(
        generated_at="2026-08-03T00:00:00Z",
        worktree="/wt", branch="codex/p3-strict-kernel",
        head="4eb463368e38f2faa3d3656a05974c4b1c1211a6",
        git_status=" M docs/manual_audit_protocol.md",
    )
    assert "2026-08-03T00:00:00Z" in header
    assert "codex/p3-strict-kernel" in header
    assert "4eb463368e38f2faa3d3656a05974c4b1c1211a6" in header
    assert "M docs/manual_audit_protocol.md" in header