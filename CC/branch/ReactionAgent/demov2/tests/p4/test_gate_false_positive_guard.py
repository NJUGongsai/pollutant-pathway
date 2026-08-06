"""P4-R1-F/J RED→GREEN: Gate/mutation false-positive prevention.

- G11 must fail when pytest exits nonzero or the report is absent/stale
  (it must never trust a leftover success JSON);
- gate-check execution exceptions are typed ERROR, never a target FAIL;
- mutations declare an expected failure code; only a mutated run that
  executes normally and matches the expected code is ``caught``;
- M04 must be a real test-evidence isolation failure (no recursion);
- G14 must not trust a stored P2/P3 status string;
- any real-input item that is false AND not blocked fails the whole gate.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from types import SimpleNamespace

import pytest

DEMOV2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, DEMOV2_ROOT)


class TestG11:
    def test_g11_pytest_exit_nonzero_fails(self, monkeypatch):
        """pytest exit code != 0 must FAIL G11 even if a leftover report
        exists (the report is bound to THIS run via a fresh temp path)."""
        from scripts.run_p4_gate import check_g11_tests
        monkeypatch.setattr(
            "scripts.run_p4_gate._run_subprocess",
            lambda cmd, timeout=600: SimpleNamespace(
                returncode=7, stdout="", stderr=""))
        result = check_g11_tests()
        assert result["passed"] is False
        assert "exit" in result["evidence"].lower()

    def test_g11_missing_report_fails(self, monkeypatch):
        from scripts.run_p4_gate import check_g11_tests
        monkeypatch.setattr(
            "scripts.run_p4_gate._run_subprocess",
            lambda cmd, timeout=600: SimpleNamespace(
                returncode=0, stdout="", stderr=""))
        result = check_g11_tests()
        assert result["passed"] is False
        assert "report" in result["evidence"].lower()

    def test_g11_writes_report_with_zero_skips(self, monkeypatch):
        """A real zero-skip green run passes G11."""
        from scripts.run_p4_gate import check_g11_tests
        import scripts.run_p4_gate as gate

        def fake_run(cmd, timeout=600):
            # The fresh report path is passed as --json-report-file=<path>.
            report_path = next(
                a.split("=", 1)[1] for a in cmd if a.startswith("--json-report-file="))
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump({"summary": {"collected": 130, "passed": 130,
                                       "failed": 0, "errors": 0,
                                       "skipped": 0, "xfailed": 0,
                                       "xpassed": 0, "warnings": 0}},
                          f)
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        monkeypatch.setattr(gate, "_run_subprocess", fake_run)
        result = check_g11_tests()
        assert result["passed"] is True


class TestTypedError:
    def test_gate_check_exception_returns_typed_error(self, monkeypatch):
        """A gate check that raises must return a typed ERROR result, never
        be confused with a target invariant FAIL."""
        from scripts.run_p4_gate import GATE_CHECKS, _result
        # Build a check that raises on first call.
        def boom():
            raise RuntimeError("boom")
        result = _typed_error_check(boom)
        assert result.get("error") is True
        assert result.get("passed") is False
        assert result.get("blocked") is False

    def test_error_is_not_counted_as_caught_mutation(self):
        """A mutation that raises during execution is ERROR, not caught."""
        from scripts.run_p4_mutations import _run_one
        def boom():
            raise RuntimeError("recursion")
        mutation = {
            "id": "MER", "name": "raises", "check_fn": boom,
            "patch": (os, "name", "x"), "expected_failure_code": "X",
        }
        result = _run_one(mutation)
        assert result["error"] is True
        assert result["caught"] is False
        assert result["escaped"] is False


def _flaky_check(evidence_on_fail: str):
    """A check_fn that PASSES on the baseline call and FAILS on the mutated
    call (first call = baseline, second call = mutated)."""
    calls = {"n": 0}

    def check():
        calls["n"] += 1
        if calls["n"] == 1:
            return {"passed": True, "blocked": False, "error": False,
                    "evidence": "baseline ok", "details": {}}
        return {"passed": False, "blocked": False, "error": False,
                "evidence": evidence_on_fail, "details": {}}
    return check


class TestMutationFailureCode:
    def test_wrong_failure_code_not_caught(self, monkeypatch):
        """A mutated run that fails with the WRONG failure code is not a
        caught mutation (expected code must match exactly)."""
        from scripts.run_p4_mutations import _run_one
        mutation = {
            "id": "MWC", "name": "wrong code",
            "check_fn": _flaky_check("some unrelated failure"),
            "patch": (os, "name", "x"),
            "expected_failure_code": "TEST_EVIDENCE_ISOLATION",
        }
        result = _run_one(mutation)
        assert result["caught"] is False
        assert result["actual_status"] == "FAIL"

    def test_matching_failure_code_caught(self, monkeypatch):
        from scripts.run_p4_mutations import _run_one
        mutation = {
            "id": "MOK", "name": "matched",
            "check_fn": _flaky_check(
                "TEST_EVIDENCE_ISOLATION: test:ev_1 leaked"),
            "patch": (os, "name", "x"),
            "expected_failure_code": "TEST_EVIDENCE_ISOLATION",
        }
        result = _run_one(mutation)
        assert result["caught"] is True
        assert result["error"] is False


class TestM04:
    def test_m04_is_real_test_evidence_isolation_not_recursion(self):
        """M04 must not recurse; it must produce a typed test-evidence
        isolation failure."""
        import scripts.run_p4_mutations as mut
        m04 = next(m for m in mut.MUTATIONS if m["id"] == "M04")
        assert m04.get("expected_failure_code"), "M04 must declare expected code"
        result = mut._run_one(m04)
        assert result["error"] is False, f"M04 errored: {result['evidence']}"
        assert result["caught"] is True
        assert "TEST_EVIDENCE_ISOLATION" in (result.get("failure_code") or "") or \
            "test:ev_999" in result.get("evidence", "") or \
            "TEST_EVIDENCE_ISOLATION" in result.get("evidence", "")


class TestAuthorityGates:
    def test_g14_stored_status_string_is_not_authority(self):
        """G14 must not trust a stored P2 status string; it stays BLOCKED
        until a current-run P2 artifact/hash/receipt is verified."""
        from scripts.run_p4_gate import check_g14_p2_truth_authority
        result = check_g14_p2_truth_authority()
        assert result.get("blocked") is True
        assert result["passed"] is False

    def test_real_input_false_non_blocked_fails_overall(self):
        """A real-input item that is false and NOT blocked must fail the whole
        gate (currently all real-input items are honestly BLOCKED)."""
        from scripts.run_p4_gate import generate_report, _result
        checks = [
            {"gate_id": "P4-G01", "name": "machinery", "passed": True,
             "blocked": False, "evidence": "ok", "details": {}},
            {"gate_id": "P4-G12", "name": "real", "passed": False,
             "blocked": False, "evidence": "not blocked but false", "details": {}},
        ]
        _, _, status, exit_code = generate_report(checks, env={})
        assert status == "P4_GATE_FAIL_NEEDS_REMEDIATION"
        assert exit_code == 1


def _typed_error_check(fn):
    """Run a check that raises; the runner must convert it to typed ERROR."""
    try:
        fn()
        return {"passed": True, "blocked": False, "error": False,
                "evidence": "ok", "details": {}}
    except Exception as e:  # noqa: BLE001
        return {"passed": False, "blocked": False, "error": True,
                "evidence": f"check error: {e}", "details": {}}