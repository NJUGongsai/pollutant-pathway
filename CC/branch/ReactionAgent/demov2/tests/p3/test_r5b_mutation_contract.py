"""R5-B: frozen mutation contracts bound to REAL execution receipts.

Round 4 defect: ``_frozen_mutation_ids()`` froze only mutation IDs.  The Gate
compared the submitted ID set and the submitter's own expected/observed codes
+ non-empty hashes, so a nonexistent command, arbitrary non-empty hashes and
attacker-chosen failure codes still passed.

R5-B contract:
- every mutation is declared in a TYPED frozen registry that binds mutation
  ID, target Gate item, expected failure code, baseline case, mutated case,
  component and schema version, and carries a canonical registry hash;
- the Gate compares the FULL metadata (not just the ID set) and the registry
  hash is bound to the current Gate execution;
- baseline/mutated execution receipts are verified by the trusted execution
  authority: stdout hash is RECOMPUTED from the real stdout, artifact hash is
  RECOMPUTED from the typed output, observed failure code is parsed from the
  real output, and exit code / status / failure code must be mutually
  consistent;
- ``cwd``/executable strings are never execution proof; a fabricated or
  cached receipt without a trusted root is rejected.

These tests are RED on the R4 code (attacker-chosen metadata passes) and
GREEN after R5-B.
"""
from __future__ import annotations

import pytest

from reaction_agent.p3.gate import (
    MutationCaseRun,
    MutationResult,
    evaluate_gate_artifact,
    run_p3_gate,
)
from reaction_agent.p3.manifest import build_interface_manifest, manifest_schema_hash
from reaction_agent.p3.mutations_round3 import MUTATION_REGISTRY


def _live_hash():
    return manifest_schema_hash(build_interface_manifest())


def _real_gate_artifact() -> dict:
    report = run_p3_gate(run_mutations=True)
    return report.model_dump(mode="json")


def _ns_artifact():
    return {
        "gate_id": "p3_gate",
        "interface_manifest_schema_hash": _live_hash(),
        "run_id": "run_r5b", "case_id": "case_r5b", "query_id": "q_r5b",
        "fold_id": "fold_r5b", "snapshot_id": "snap_r5b", "snapshot_hash": "hh_r5b",
    }


def test_registry_binds_full_metadata() -> None:
    """Every registry entry must carry target/expected/baseline/mutated/
    component/schema — never just a mutation ID."""
    from reaction_agent.p3.mutations_round3 import MUTATION_REGISTRY
    for case in MUTATION_REGISTRY:
        assert case["mutation_id"]
        assert case["target_gate_item"]
        assert case["expected_failure_code"]
        assert case["baseline_case"], case["mutation_id"]
        assert case["mutated_case"], case["mutation_id"]
        assert case["component"], case["mutation_id"]
        assert case["schema_version"], case["mutation_id"]


def test_registry_has_canonical_hash() -> None:
    from reaction_agent.p3.mutations_round3 import mutation_registry_hash
    h = mutation_registry_hash()
    assert h and len(h) == 64
    # deterministic
    assert mutation_registry_hash() == h


# -- attacker-chosen metadata (R5-B attack set) -------------------------------


def test_attack_correct_ids_wrong_targets_rejected() -> None:
    artifact = _real_gate_artifact()
    for m in artifact["mutations"]:
        m["target_gate_item"] = "G10"  # all wrong targets
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("TARGET" in f or "MUTATION" in f for f in evaluation.machinery_failures)


def test_attack_correct_ids_attacker_expected_code_rejected() -> None:
    artifact = _real_gate_artifact()
    for m in artifact["mutations"]:
        m["expected_failure_code"] = "ATTACKER_SELECTED_CODE"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("EXPECTED" in f or "MUTATION" in f for f in evaluation.machinery_failures)


def test_attack_expected_equals_observed_but_not_registry_rejected() -> None:
    artifact = _real_gate_artifact()
    for m in artifact["mutations"]:
        m["expected_failure_code"] = "FORGED_CODE"
        m["observed_failure_code"] = "FORGED_CODE"  # self-consistent but wrong
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("EXPECTED" in f or "MUTATION" in f for f in evaluation.machinery_failures)


def test_attack_baseline_status_conflicts_with_baseline_run_rejected() -> None:
    artifact = _real_gate_artifact()
    artifact["mutations"][0]["baseline_status"] = "INVALID_BASELINE"
    artifact["mutations"][0]["baseline"]["status"] = "PASS"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("BASELINE" in f for f in evaluation.machinery_failures)


def test_attack_mutated_status_conflicts_with_mutated_run_rejected() -> None:
    artifact = _real_gate_artifact()
    artifact["mutations"][0]["mutated_status"] = "PASS"
    artifact["mutations"][0]["mutated"]["status"] = "FAIL"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("MUTATED" in f or "ESCAPED" in f for f in evaluation.machinery_failures)


def test_attack_status_conflicts_with_exit_code_rejected() -> None:
    artifact = _real_gate_artifact()
    # status says FAIL but exit code 0 (contract: FAIL -> 1, PASS -> 0)
    artifact["mutations"][0]["mutated"]["status"] = "FAIL"
    artifact["mutations"][0]["mutated"]["exit_code"] = 0
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("EXIT" in f or "STATUS" in f for f in evaluation.machinery_failures)


def test_attack_raw_output_modified_without_hash_update_rejected() -> None:
    artifact = _real_gate_artifact()
    m = artifact["mutations"][0]
    m["mutated"]["raw_output"] = m["mutated"]["raw_output"] + "\nFORGED\n"
    # stdout_stderr_hash NOT updated -> recompute must fail
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("STDOUT" in f or "HASH" in f for f in evaluation.machinery_failures)


def test_attack_raw_output_and_hash_updated_but_receipt_not_current_run() -> None:
    artifact = _real_gate_artifact()
    m = artifact["mutations"][0]
    m["mutated"]["raw_output"] = m["mutated"]["raw_output"] + "\nFORGED\n"
    import hashlib
    m["mutated"]["stdout_stderr_hash"] = hashlib.sha256(
        m["mutated"]["raw_output"].encode("utf-8")
    ).hexdigest()
    # receipt belongs to another run/component version -> registry binding fails
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("REGISTRY" in f or "RUN" in f or "MUTATION" in f
               for f in evaluation.machinery_failures)


def test_attack_artifact_hash_arbitrary_nonempty_rejected() -> None:
    artifact = _real_gate_artifact()
    artifact["mutations"][0]["mutated"]["artifact_hash"] = "x" * 64
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("ARTIFACT" in f for f in evaluation.machinery_failures)


def test_attack_command_points_to_nonexistent_program_rejected() -> None:
    artifact = _real_gate_artifact()
    artifact["mutations"][0]["mutated"]["command"] = [
        "/nonexistent/python", "never-executed.py",
    ]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("COMMAND" in f or "EXECUT" in f for f in evaluation.machinery_failures)


def test_attack_cached_mutation_from_another_run_rejected() -> None:
    artifact = _real_gate_artifact()
    artifact["mutations"][0]["mutated"]["run_id"] = "run_OTHER"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("RUN" in f for f in evaluation.machinery_failures)


def test_attack_registry_hash_drift_rejected() -> None:
    artifact = _real_gate_artifact()
    artifact["mutation_registry_hash"] = "d" * 64
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("REGISTRY" in f for f in evaluation.machinery_failures)


# -- genuine executions still pass ---------------------------------------------


def test_real_gate_artifact_mutations_pass_machinery_verification() -> None:
    artifact = _real_gate_artifact()
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.machinery_failures == []
    assert evaluation.verdict == "BLOCKED"  # honest real-evidence blocker


def test_real_mutation_receipts_recompute_hashes() -> None:
    """The real receipts' stdout hash recomputes from raw_output and the
    artifact hash recomputes from the typed artifact."""
    import hashlib
    import json
    artifact = _real_gate_artifact()
    for m in artifact["mutations"]:
        for side in ("baseline", "mutated"):
            run = m[side]
            recomputed = hashlib.sha256(run["raw_output"].encode("utf-8")).hexdigest()
            assert recomputed == run["stdout_stderr_hash"], (
                f"{m['mutation_id']}.{side} stdout hash does not recompute"
            )
            assert run["artifact"], f"{m['mutation_id']}.{side} missing artifact"
            artifact_json = json.dumps(
                run["artifact"], ensure_ascii=False, sort_keys=True, default=str
            )
            assert hashlib.sha256(artifact_json.encode("utf-8")).hexdigest() == (
                run["artifact_hash"]
            ), f"{m['mutation_id']}.{side} artifact hash does not recompute"