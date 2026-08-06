"""R7-A: mutation outcomes are bound to the SAME trusted execution authority.

ChatGPT P3 Round 6 audit finding (NOT CLOSED):

``GateExecutionAuthority`` only saved and compared ``GateItemResult items``.
``run_p3_gate()`` registered the authority BEFORE the mutation suite ran, so
the R6-A complete-match only protected Gate items — never mutations.  The
R6-B verifier parses the marker-delimited JSON receipt and compares the raw
receipt with the typed fields; but the raw receipt, typed fields, artifact
hash and stdout hash are ALL in the submitted report, so a caller can rewrite
them together.  A self-consistent rewrite of BOTH the raw and typed receipt
was therefore NOT detected by the R6-A execution authority.

R7-A contract:
- the authority binds the ACTUAL executed items AND the ACTUAL executed
  mutation results (registered AFTER the mutation suite completes);
- the verifier EXACT-MATCHES the submitted mutations against the executed
  mutations — same count, same order, same full record (baseline + mutated
  receipts, every hash, status, failure code, case, variant, session nonce,
  adjudication);
- missing / extra / duplicate / reordered / fully-synchronized-rewritten
  mutations produce a typed failure code and ``verified=False``;
- the mutation verdict / caught / valid / observed code are derived from the
  executed mutations (the submitted copies are forced to be identical).

These tests are RED on the R6 code and GREEN after R7-A.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from reaction_agent.p3.gate import evaluate_gate_artifact, run_p3_gate
from reaction_agent.p3.mutation_harness import RECEIPT_BEGIN, RECEIPT_END


def _real_artifact() -> dict:
    report = run_p3_gate(run_mutations=True)
    return report.model_dump(mode="json")


def _real_report():
    return run_p3_gate(run_mutations=True)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rebuild_raw_receipt(payload: dict) -> str:
    """Rebuild the marker-delimited receipt exactly as the subprocess emits it."""
    return (
        RECEIPT_BEGIN + "\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        + "\n" + RECEIPT_END + "\n"
    )


# -- 1. the audit's decisive repro: BOTH raw and typed receipt rewritten -------


def test_simultaneous_raw_and_typed_receipt_rewrite_fails_against_execution_authority():
    """The audit's exact nine-step attack:

    1. run the real P3 Gate and take the real report (and the registered
       in-process execution authority);
    2. parse a real mutated receipt;
    3. modify the artifact inside the receipt;
    4. recompute the receipt ``artifact_hash``;
    5. synchronously update the typed ``run.artifact`` and ``run.artifact_hash``;
    6. regenerate the full marker-delimited raw receipt;
    7. recompute ``stdout_stderr_hash``;
    8. keep every other mutation contract field legal;
    9. call ``evaluate_gate_artifact()``.

    The verdict must be FAIL, ``verified`` False, and the failures must
    contain ``EXECUTED_MUTATION_MISMATCH`` — the rewritten mutation no longer
    matches the mutation the runner ACTUALLY executed.
    """
    from reaction_agent.p3.mutation_harness import parse_strict_receipt

    artifact = _real_artifact()
    m = artifact["mutations"][0]
    side = m["mutated"]

    # 2. parse the real receipt from the real raw output
    receipt = parse_strict_receipt(side["raw_output"])
    assert receipt is not None, "real mutated receipt must be parseable"

    # 3. modify the artifact inside the receipt payload
    forged_artifact = {**receipt["artifact"], "_forged": True}
    forged_json = json.dumps(
        forged_artifact, ensure_ascii=False, sort_keys=True, default=str,
    )
    # 4. recompute the receipt artifact hash
    receipt = {**receipt, "artifact": forged_artifact,
               "artifact_hash": _sha256(forged_json)}
    # 5. synchronously update the typed artifact + artifact hash
    side["artifact"] = forged_artifact
    side["artifact_hash"] = _sha256(forged_json)
    # 6. regenerate the full marker-delimited raw receipt
    side["raw_output"] = _rebuild_raw_receipt(receipt)
    # 7. recompute stdout_stderr_hash
    side["stdout_stderr_hash"] = _sha256(side["raw_output"])
    # 8. all other contract fields stay legal (they are untouched)

    # 9. verify against the in-process execution authority (resolved by run_id)
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL", (
        f"fully-synchronized raw+typed receipt rewrite must be rejected, "
        f"got {evaluation.verdict}"
    )
    assert evaluation.verified is False
    assert any(
        f.startswith("EXECUTED_MUTATION_MISMATCH")
        for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"


# -- 2. missing mutation ------------------------------------------------------


def test_missing_mutation_fails_against_execution_authority():
    """Dropping one submitted mutation must fail: the executed set has more
    entries than the submitted set."""
    artifact = _real_artifact()
    artifact["mutations"] = artifact["mutations"][1:]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert evaluation.verified is False
    assert any(
        f.startswith("EXECUTED_MUTATION_COUNT_MISMATCH")
        or f.startswith("EXECUTED_MUTATION_MISSING")
        for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"


# -- 3. extra mutation --------------------------------------------------------


def test_extra_mutation_fails_against_execution_authority():
    """Appending a duplicate mutation must fail: the submitted set has more
    entries than the executed set."""
    artifact = _real_artifact()
    artifact["mutations"].append(dict(artifact["mutations"][0]))
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert evaluation.verified is False
    assert any(
        f.startswith("EXECUTED_MUTATION_COUNT_MISMATCH")
        or f.startswith("SUBMITTED_MUTATION_EXTRA")
        or f.startswith("MUTATION_ID_DUPLICATE")
        for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"


# -- 4. order substitution ----------------------------------------------------


def test_reordered_mutations_fail_against_execution_authority():
    """Swapping two submitted mutations (same set, same count) must fail: the
    order is part of the execution contract."""
    artifact = _real_artifact()
    muts = artifact["mutations"]
    muts[0], muts[1] = muts[1], muts[0]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert evaluation.verified is False
    assert any(
        f.startswith("EXECUTED_MUTATION_ORDER_MISMATCH")
        for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"


# -- 5. adjudication-field rewrite --------------------------------------------


def test_adjudication_rewrite_fails_against_execution_authority():
    """Rewriting the adjudication (caught / valid / observed code) to a
    self-consistent but different value must fail against the executed
    mutation — the outcome is derived FROM the executed record."""
    artifact = _real_artifact()
    m = artifact["mutations"][0]
    m["caught"] = not m["caught"]
    m["valid"] = not m["valid"]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert evaluation.verified is False
    assert any(
        f.startswith("EXECUTED_MUTATION_MISMATCH")
        for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"


# -- 6. genuine gate still passes ---------------------------------------------


def test_real_gate_mutations_match_executed_authority():
    """The real gate's own mutations must exactly match the executed authority
    (registered by the runner after the mutation suite) and pass machinery
    verification."""
    report = _real_report()
    artifact = report.model_dump(mode="json")
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verified is True
    assert evaluation.machinery_failures == [], (
        f"failures={evaluation.machinery_failures}"
    )
    # The authority (resolved by run_id) holds exactly the executed mutations.
    from reaction_agent.p3.gate import _resolve_execution_authority
    authority = _resolve_execution_authority("p3_gate")
    assert authority is not None
    assert len(authority.mutations) == len(report.mutations)


# -- 7. offline (fresh process) artifact can never be verified ----------------

def test_offline_artifact_without_authority_cannot_be_verified():
    """An artifact resolved to NO in-process authority (simulating a fresh
    process) is at most structurally valid — never verified=True, even when
    every mutation is internally consistent."""
    report = _real_report()
    report_offline = report.model_copy(update={"run_id": "offline_unknown_run"})
    artifact = report_offline.model_dump(mode="json")
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verified is False
    assert evaluation.verdict == "FAIL"