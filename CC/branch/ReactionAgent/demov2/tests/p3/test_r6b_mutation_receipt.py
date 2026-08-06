"""R6-B: mutation receipts are bound to the trusted execution, not self-signed.

ChatGPT P3 Round 5 audit findings (NOT CLOSED):

1. ``_verify_mutation_contract`` recomputes ``stdout_stderr_hash`` from
   ``run.raw_output`` and ``artifact_hash`` from ``run.artifact`` SEPARATELY,
   so the raw output and the typed artifact have NO cryptographic or
   execution-semantic binding — both can be replaced independently and
   re-hashed to keep passing.
2. The receipt's ``run_id`` / ``component`` / ``schema_version`` are empty in
   the real gate report; the verifier uses ``if run.run_id ...`` conditional
   checks so empty values bypass the current-run/component/schema binding.
3. The verifier never parses a unique typed payload from the raw output,
   never compares the parsed artifact with ``run.artifact``, never cross
   compares the parsed status / failure code / case / variant with the
   receipt fields, and never proves the recorded command executed.

R6-B contract:
- the mutation subprocess emits a UNIQUE, STRICT, VERSIONED JSON receipt
  (marker-delimited) binding session nonce / run id / mutation id / case /
  variant / component / schema version / command identity / exit code /
  status / failure code / typed artifact / canonical artifact hash to ONE
  trusted execution;
- the runner parses the receipt and builds the typed run FROM the parsed
  payload — the stored artifact is not an independently modifiable copy;
- the verifier PARSEES the receipt from the raw output and requires the
  stored typed fields to EXACTLY match the parsed payload (raw output and
  typed artifact are bound);
- ``run_id`` / ``component`` / ``schema_version`` / ``case`` / ``variant`` /
  ``session_nonce`` are REQUIRED non-empty fields — no conditional
  "non-empty then compare" bypass;
- the mutation outcome is derived from the trusted execution receipt, not
  from the submission's stored fields;
- a receipt from a previous execution (different session nonce) is rejected.

These tests are RED on the R5 code and GREEN after R6-B.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from reaction_agent.p3.gate import evaluate_gate_artifact, run_p3_gate


def _real_artifact() -> dict:
    report = run_p3_gate(run_mutations=True)
    return report.model_dump(mode="json")


def _real_report():
    return run_p3_gate(run_mutations=True)


# -- 1. rewrite the typed artifact and rehash it ------------------------------


def test_rewrite_typed_artifact_and_rehash_is_rejected():
    """The audit's repro: rewrite ``run.artifact`` and recompute
    ``artifact_hash`` from the new content while keeping the raw output
    unchanged.  The verifier must reject the raw-output/typed-artifact
    mismatch."""
    artifact = _real_artifact()
    m = artifact["mutations"][0]
    m["mutated"]["artifact"] = {**m["mutated"]["artifact"], "_forged": True}
    artifact_json = json.dumps(
        m["mutated"]["artifact"], ensure_ascii=False, sort_keys=True, default=str,
    )
    m["mutated"]["artifact_hash"] = hashlib.sha256(
        artifact_json.encode("utf-8")
    ).hexdigest()
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(
        f.startswith("MUTATION_RAW_ARTIFACT_MISMATCH")
        for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"


# -- 2. rewrite the raw output and rehash it ----------------------------------


def test_rewrite_raw_output_and_rehash_is_rejected():
    """The audit's repro: rewrite ``raw_output`` and recompute
    ``stdout_stderr_hash`` while keeping the typed artifact unchanged.  The
    parsed receipt's artifact differs from the stored artifact -> rejected."""
    artifact = _real_artifact()
    m = artifact["mutations"][0]
    m["mutated"]["raw_output"] = m["mutated"]["raw_output"] + "\nFORGED\n"
    m["mutated"]["stdout_stderr_hash"] = hashlib.sha256(
        m["mutated"]["raw_output"].encode("utf-8")
    ).hexdigest()
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(
        f.startswith("MUTATION_RAW_ARTIFACT_MISMATCH")
        or f.startswith("MUTATION_STDOUT_HASH_MISMATCH")
        or f.startswith("MUTATION_NO_STRICT_RECEIPT")
        for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"


# -- 3./4./5. empty receipt identity fields are rejected -----------------------


def test_empty_receipt_run_id_is_rejected():
    artifact = _real_artifact()
    artifact["mutations"][0]["mutated"]["run_id"] = ""
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(
        f.startswith("MUTATION_EMPTY_RUN_ID") or f == "INVALID_MUTATION_RECORDS"
        for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"


def test_empty_receipt_component_is_rejected():
    artifact = _real_artifact()
    artifact["mutations"][0]["mutated"]["component"] = ""
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(
        f.startswith("MUTATION_EMPTY_COMPONENT") or f == "INVALID_MUTATION_RECORDS"
        for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"


def test_empty_receipt_schema_version_is_rejected():
    artifact = _real_artifact()
    artifact["mutations"][0]["mutated"]["schema_version"] = ""
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(
        f.startswith("MUTATION_EMPTY_SCHEMA_VERSION") or f == "INVALID_MUTATION_RECORDS"
        for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"


# -- 6. raw payload artifact must equal the typed receipt artifact ------------


def test_raw_payload_artifact_must_equal_typed_receipt_artifact():
    """The parsed receipt artifact (from the raw output) must EXACTLY equal
    the stored typed artifact — the two are not independently modifiable."""
    from reaction_agent.p3.mutation_harness import parse_strict_receipt

    report = _real_report()
    for m in report.mutations:
        for side in ("baseline", "mutated"):
            run = getattr(m, side)
            receipt = parse_strict_receipt(run.raw_output)
            assert receipt is not None, f"{m.mutation_id}.{side} no strict receipt"
            assert receipt["artifact"] == run.artifact, (
                f"{m.mutation_id}.{side} parsed artifact != typed artifact"
            )


# -- 7. raw payload status / failure code must equal the receipt --------------


def test_raw_payload_status_and_failure_code_must_equal_receipt():
    artifact = _real_artifact()
    m = artifact["mutations"][0]
    # Flip the stored status while keeping the raw output unchanged.
    m["mutated"]["status"] = "PASS"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(
        f.startswith("MUTATION_RAW_STATUS_MISMATCH") for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"

    artifact2 = _real_artifact()
    m2 = artifact2["mutations"][0]
    # Change the stored failure code while keeping the raw output unchanged.
    m2["mutated"]["failure_code"] = "FORGED_CODE"
    evaluation2 = evaluate_gate_artifact(artifact2)
    assert evaluation2.verdict == "FAIL"
    assert any(
        f.startswith("MUTATION_RAW_FAILURE_CODE_MISMATCH")
        for f in evaluation2.machinery_failures
    ), f"failures={evaluation2.machinery_failures}"


# -- 8. receipt from a previous execution nonce is rejected -------------------


def test_receipt_from_previous_execution_nonce_is_rejected():
    """A receipt bound to a DIFFERENT session nonce than the report's trusted
    execution must be rejected."""
    artifact = _real_artifact()
    artifact["mutations"][0]["mutated"]["session_nonce"] = "previous_execution_nonce"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(
        f.startswith("MUTATION_RECEIPT_NONCE_MISMATCH")
        or f.startswith("MUTATION_RAW_NONCE_MISMATCH")
        or f.startswith("MUTATION_SESSION_NONCE_MISMATCH")
        for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"


# -- genuine receipts still pass ----------------------------------------------


def test_real_gate_receipts_are_execution_bound():
    """The real gate's mutation receipts carry every required non-empty
    identity field and pass machinery verification."""
    report = _real_report()
    assert report.session_nonce, "gate report must carry a session nonce"
    for m in report.mutations:
        assert m.session_nonce == report.session_nonce
        for side in ("baseline", "mutated"):
            run = getattr(m, side)
            assert run.run_id, f"{m.mutation_id}.{side} run_id empty"
            assert run.component, f"{m.mutation_id}.{side} component empty"
            assert run.schema_version, f"{m.mutation_id}.{side} schema empty"
            assert run.case, f"{m.mutation_id}.{side} case empty"
            assert run.variant, f"{m.mutation_id}.{side} variant empty"
            assert run.session_nonce, f"{m.mutation_id}.{side} nonce empty"
    artifact = report.model_dump(mode="json")
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.machinery_failures == []