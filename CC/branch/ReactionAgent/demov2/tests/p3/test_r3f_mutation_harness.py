"""R3-F real mutation evidence tests.

Round 2 defect: the harness only observed pytest PASSED/FAILED/ERROR, then
HARDCODED ``baseline_status="PASS"`` and COPIED ``expected_failure_code``
into ``observed_failure_code``.

Round 3 contract: every mutation provides an executable baseline case and
mutated case, run SEPARATELY, each recording real status / exit code /
artifact hash / failure code / command / duration / stdout hash.  Rules:
baseline not PASS -> INVALID_BASELINE + Gate FAIL; mutation PASS (escape) ->
Gate FAIL; mutation ERROR -> Gate FAIL; observed code mismatch -> Gate FAIL.
"""
import pytest

from reaction_agent.p3.mutation_harness import adjudicate, run_mutation_suite
from reaction_agent.p3.mutations_round3 import MUTATION_REGISTRY


REQUIRED_MUTATIONS = {
    "m_ab_only_stripped_reaction",
    "m_deleted_participant",
    "m_partial_mapping",
    "m_missing_lineage",
    "m_skipped_preconditions",
    "m_forged_source_ledger",
    "m_fold_pollution",
    "m_relaxed_edit_strict",
    "m_system_failure_as_abstention",
    "m_forged_gate_pass",
    "m_reaction_hash_forgery",
    "m_transform_hash_collision",
    "m_forged_evidence_path",
    "m_bad_reaction_kernel_crash",
}


def _run(status, code=""):
    return {"status": status, "failure_code": code}


# -- pure fail-closed rules ---------------------------------------------------


def test_adjudicate_clean_case_is_valid_and_caught():
    verdict = adjudicate(_run("PASS"), _run("FAIL", "CODE_X"), "CODE_X")
    assert verdict["valid"] is True
    assert verdict["caught"] is True
    assert verdict["baseline_status"] == "PASS"
    assert verdict["mutated_status"] == "FAIL"
    assert verdict["observed_failure_code"] == "CODE_X"


def test_adjudicate_invalid_baseline_fails_gate():
    verdict = adjudicate(_run("FAIL", "B"), _run("FAIL", "CODE_X"), "CODE_X")
    assert verdict["baseline_status"] == "INVALID_BASELINE"
    assert verdict["valid"] is False
    assert "INVALID_BASELINE" in verdict["invalid_reason"]


def test_adjudicate_escaped_mutation_fails_gate():
    verdict = adjudicate(_run("PASS"), _run("PASS"), "CODE_X")
    assert verdict["valid"] is False
    assert verdict["caught"] is False
    assert "MUTATION_ESCAPED" in verdict["invalid_reason"]


def test_adjudicate_mutated_error_fails_gate():
    verdict = adjudicate(_run("PASS"), _run("ERROR"), "CODE_X")
    assert verdict["valid"] is False
    assert "MUTATED_RUN_ERROR" in verdict["invalid_reason"]


def test_adjudicate_observed_code_mismatch_fails_gate():
    verdict = adjudicate(_run("PASS"), _run("FAIL", "OTHER_CODE"), "CODE_X")
    assert verdict["valid"] is False
    assert verdict["caught"] is False
    assert "OBSERVED_CODE_MISMATCH" in verdict["invalid_reason"]


# -- registry completeness ------------------------------------------------------


def test_registry_covers_required_mutations():
    registered = {c["mutation_id"] for c in MUTATION_REGISTRY}
    assert REQUIRED_MUTATIONS <= registered
    for case in MUTATION_REGISTRY:
        assert case["expected_failure_code"]
        assert case["target_gate_item"]


# -- real suite execution evidence ------------------------------------------------


@pytest.fixture(scope="module")
def suite_results():
    return run_mutation_suite(use_cache=True)


def test_every_mutation_ran_two_separate_real_executions(suite_results):
    assert len(suite_results) == len(MUTATION_REGISTRY)
    for record in suite_results:
        baseline = record["baseline"]
        mutated = record["mutated"]
        # separate commands (different variant), separate outputs
        assert baseline["command"] != mutated["command"]
        assert "--variant" in baseline["command"]
        assert baseline["stdout_stderr_hash"]
        assert mutated["stdout_stderr_hash"]
        assert baseline["python_executable"]
        assert baseline["duration_seconds"] >= 0
        assert mutated["duration_seconds"] >= 0
        # artifact hashes recorded from the real subprocess payload
        assert baseline["artifact_hash"]
        assert mutated["artifact_hash"]


def test_every_mutation_caught_with_real_observed_code(suite_results):
    for record in suite_results:
        assert record["baseline_status"] == "PASS", (
            f"{record['mutation_id']} baseline invalid: "
            f"{record['baseline']['raw_tail']}"
        )
        assert record["mutated_status"] == "FAIL", (
            f"{record['mutation_id']} mutated run did not FAIL: "
            f"{record['mutated_status']} {record['mutated']['raw_tail']}"
        )
        assert record["caught"] is True
        assert record["valid"] is True, record["invalid_reason"]
        # observed code is what production emitted — and it matched expected
        assert record["observed_failure_code"] == record["expected_failure_code"]
        assert record["mutated"]["failure_code"] == record["expected_failure_code"]


def test_mutation_exit_codes_are_real(suite_results):
    for record in suite_results:
        # scenario contract: PASS=0, FAIL=1
        assert record["baseline"]["exit_code"] == 0
        assert record["mutated"]["exit_code"] == 1
