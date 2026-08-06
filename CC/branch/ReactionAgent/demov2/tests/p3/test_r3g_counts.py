"""R3-G pytest count integrity tests.

Round 2 defect: evidence recorded ``collected=0`` with positive passed
counts, and ``_fail_closed()`` accepted it.

Round 3 contract: a trustworthy, nonzero collected count (derived from the
pytest summary or a separate collect-only run), verified against ALL outcome
categories without double counting; zero/missing/malformed/interrupted/
timeout/inconsistent summaries fail closed.
"""
import pytest

import scripts.generate_p3_round3_reports as gen3


# -- parser: outcome categories --------------------------------------------------


def test_parse_successful_quiet_output():
    counts = gen3.parse_outcome_counts("175 passed, 12 warnings in 4.49s\n")
    assert counts["passed"] == 175
    assert counts["failed"] == 0
    assert counts["errors"] == 0


def test_parse_failures():
    counts = gen3.parse_outcome_counts("1 failed, 174 passed in 5.2s\n")
    assert counts["failed"] == 1
    assert counts["passed"] == 174


def test_parse_errors():
    counts = gen3.parse_outcome_counts("2 errors, 3 passed in 1.0s\n")
    assert counts["errors"] == 2
    assert counts["passed"] == 3


def test_parse_skipped_xfailed_xpassed():
    counts = gen3.parse_outcome_counts(
        "10 passed, 1 skipped, 2 xfailed, 1 xpassed in 2s\n"
    )
    assert counts["passed"] == 10
    assert counts["skipped"] == 1
    assert counts["xfailed"] == 2
    assert counts["xpassed"] == 1


def test_parse_ansi_output():
    text = "\x1b[32m10 passed\x1b[0m, \x1b[31m1 failed\x1b[0m in 1s\n"
    counts = gen3.parse_outcome_counts(text)
    assert counts["passed"] == 10
    assert counts["failed"] == 1


def test_warning_summary_is_not_an_outcome():
    counts = gen3.parse_outcome_counts("12 warnings in 4.49s\n")
    assert sum(counts.values()) == 0


def test_parse_malformed_output_is_zero():
    counts = gen3.parse_outcome_counts("hello world\nno summary here\n")
    assert sum(counts.values()) == 0


# -- collected count ---------------------------------------------------------------


def test_parse_collected_from_collect_only():
    assert gen3.parse_collected_count("20 tests collected in 0.01s\n") == 20
    assert gen3.parse_collected_count("collected 175 items\n") == 175
    assert gen3.parse_collected_count("nothing here") is None


# -- consistency (no double counting) ----------------------------------------------


def test_consistency_requires_nonzero_collected():
    assert gen3.counts_are_consistent({"passed": 0}, 0) is False


def test_consistency_requires_exact_sum():
    ok = {"passed": 174, "failed": 1, "errors": 0, "skipped": 0,
          "xfailed": 0, "xpassed": 0}
    assert gen3.counts_are_consistent(ok, 175) is True
    assert gen3.counts_are_consistent(ok, 176) is False
    assert gen3.counts_are_consistent(ok, 0) is False


# -- fail-closed signatures ----------------------------------------------------------


def test_no_tests_collected_fails_closed():
    with pytest.raises(gen3.PytestCountError):
        gen3.check_suite_exit(5, "no tests ran in 0.01s\n")


def test_collection_error_fails_closed():
    with pytest.raises(gen3.PytestCountError):
        gen3.check_suite_exit(2, "!!! Interrupted: 1 error during collection !!!\n")


def test_interrupted_fails_closed():
    with pytest.raises(gen3.PytestCountError):
        gen3.check_suite_exit(2, "!!! KeyboardInterrupt !!!\n")


def test_unexpected_exit_code_fails_closed():
    with pytest.raises(gen3.PytestCountError):
        gen3.check_suite_exit(3, "internal error\n")


def test_timeout_signature_fails_closed():
    with pytest.raises(gen3.PytestCountError):
        gen3.check_suite_exit(-1, "TIMEOUT after 3600s\n")


# -- fail_closed gate rules ------------------------------------------------------------


def test_fail_closed_rejects_zero_collected_with_passed():
    # The Round-2 defect: collected=0 with positive passed must be rejected.
    records = [{
        "label": "full_suite", "exit_code": 0, "timed_out": False,
        "collected": 0, "passed": 175, "failed": 0, "errors": 0,
        "skipped": 0, "xfailed": 0, "xpassed": 0, "consistent": False,
    }]
    with pytest.raises(SystemExit):
        gen3.fail_closed(records)


def test_fail_closed_rejects_inconsistent_counts():
    records = [{
        "label": "p3_suite", "exit_code": 0, "timed_out": False,
        "collected": 100, "passed": 90, "failed": 0, "errors": 0,
        "skipped": 0, "xfailed": 0, "xpassed": 0, "consistent": False,
    }]
    with pytest.raises(SystemExit):
        gen3.fail_closed(records)


def test_fail_closed_accepts_consistent_record():
    records = [{
        "label": "p3_suite", "exit_code": 0, "timed_out": False,
        "collected": 10, "passed": 10, "failed": 0, "errors": 0,
        "skipped": 0, "xfailed": 0, "xpassed": 0, "consistent": True,
    }]
    gen3.fail_closed(records)  # must not raise


# -- live: a real suite run is reconciled ---------------------------------------------


def test_live_suite_run_has_nonzero_consistent_collected():
    record = gen3.run_pytest_suite(
        "normalize_suite_r3g", ["tests/p3/test_normalize.py"]
    )
    assert record["exit_code"] == 0
    assert record["collected"] >= 1
    assert record["consistent"] is True
    assert record["passed"] == record["collected"]
    assert record["stdout_stderr_hash"]
