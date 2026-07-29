"""V3 remediation: Gate contract tests (Section 15-18, 19 #20-#25).

Verifies the Gate performs real structural checks:
- JSON Schema freshness (full structural equality, not just property names)
- environment specifier validation (real version comparison)
- structured pytest stats (zero skip/xfail/xpass)
"""

import json
import os
import sys

import pytest

DEMOV2_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
SCRIPTS_DIR = os.path.join(DEMOV2_ROOT, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import run_p0_gate  # noqa: E402
from reaction_agent.schemas import (
    AgentProposedHypothesis,
    MappingReport,
)


# -- Section 19 #20: JSON minLength drift --

@pytest.mark.contract
def test_json_min_length_drift_detected():
    """minLength drift with same property names must be detected (Section 19 #20)."""
    schema = AgentProposedHypothesis.model_json_schema()
    tampered = json.loads(json.dumps(schema))
    tampered["properties"]["hypothesis_id"]["minLength"] = 999
    assert not run_p0_gate.json_structural_equal(tampered, schema)


@pytest.mark.contract
def test_json_structural_equal_same_object():
    """Identical objects must compare equal (ignoring key order)."""
    schema = AgentProposedHypothesis.model_json_schema()
    assert run_p0_gate.json_structural_equal(schema, schema)


# -- Section 19 #21: JSON enum drift --

@pytest.mark.contract
def test_json_enum_drift_detected():
    """enum value drift must be detected (Section 19 #21)."""
    schema = MappingReport.model_json_schema()
    tampered = json.loads(json.dumps(schema))
    ms = tampered["properties"]["mapping_status"]
    if "enum" in ms:
        ms["enum"] = ms["enum"][:-1]
    elif "$ref" in ms:
        ref = ms["$ref"].split("/")[-1]
        tampered["$defs"][ref]["enum"] = tampered["$defs"][ref]["enum"][:-1]
    assert not run_p0_gate.json_structural_equal(tampered, schema)


# -- Section 19 #22: nested $defs drift --

@pytest.mark.contract
def test_json_nested_defs_drift_detected():
    """nested $defs drift must be detected (Section 19 #22)."""
    schema = MappingReport.model_json_schema()
    tampered = json.loads(json.dumps(schema))
    assert "$defs" in tampered, "MappingReport schema should have $defs"
    first_def = next(iter(tampered["$defs"]))
    tampered["$defs"][first_def]["properties"]["_drift_field"] = {"type": "string"}
    assert not run_p0_gate.json_structural_equal(tampered, schema)


# -- Section 19 #23: pytest version below spec --

@pytest.mark.contract
def test_environment_specifier_rejects_low_pytest():
    """pytest 7.4.0 below >=8.0 must be flagged (Section 19 #23)."""
    issues = run_p0_gate.check_environment_specifiers(
        versions={"python": "3.11.8", "pydantic": "2.13.4", "pytest": "7.4.0"}
    )
    assert any("pytest" in i.lower() for i in issues), (
        f"low pytest not detected: {issues}"
    )


@pytest.mark.contract
def test_environment_specifier_accepts_current():
    """The current venv environment must satisfy all specifiers."""
    issues = run_p0_gate.check_environment_specifiers()
    assert issues == [], f"environment issues: {issues}"


# -- Section 19 #24: one skipped test --

@pytest.mark.contract
def test_one_skipped_test_fails_gate():
    """A single skipped test must fail the Gate (Section 19 #24)."""
    stats = {
        "collected": 10, "passed": 9, "failed": 0, "errors": 0,
        "skipped": 1, "xfailed": 0, "xpassed": 0,
    }
    assert not run_p0_gate.pytest_stats_pass(stats)


# -- Section 19 #25: one xfailed test --

@pytest.mark.contract
def test_one_xfailed_test_fails_gate():
    """A single xfailed test must fail the Gate (Section 19 #25)."""
    stats = {
        "collected": 10, "passed": 9, "failed": 0, "errors": 0,
        "skipped": 0, "xfailed": 1, "xpassed": 0,
    }
    assert not run_p0_gate.pytest_stats_pass(stats)


@pytest.mark.contract
def test_pytest_stats_pass_clean():
    """A clean run (passed == collected, zero skip/xfail/xpass) must pass."""
    stats = {
        "collected": 10, "passed": 10, "failed": 0, "errors": 0,
        "skipped": 0, "xfailed": 0, "xpassed": 0,
    }
    assert run_p0_gate.pytest_stats_pass(stats)
