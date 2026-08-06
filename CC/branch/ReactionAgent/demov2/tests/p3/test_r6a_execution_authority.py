"""R6-A: Gate trusted execution context is fail-closed and cannot be forged.

ChatGPT P3 Round 5 audit findings (NOT CLOSED):

1. ``evaluate_gate_artifact(..., trusted_context=...)`` publicly accepts a
   plain dict; ``set_trusted_execution_context(items)`` is a public global
   setter; ``has_trusted_context`` only checks ``ctx is not None`` so an
   empty dict ``{}`` counts as trusted; the verifier only checks evidence
   artifact IDs when the executed item exists (no fail-closed on a missing
   executed item); the verifier does NOT compare submitted vs executed
   status / evidence kind / artifact type / evidence content / hash / title /
   full identity; the final verdict and item_statuses come from the submitted
   JSON, not the executed items.

The audit's independent repro with the REAL execution context and elevated
submitted statuses produced ``verified=True, PASS`` — the decisive P0.

R6-A contract:
- offline serialized artifacts can only be ``structurally_valid`` — never
  ``verified=True``;
- the public trusted-context injection and the global setter are removed;
  an ordinary caller cannot create an execution authority (the opaque
  ``GateExecutionAuthority`` requires a module-private proof token);
- an empty dict / plain dict / any non-authority context is rejected
  fail-closed (``UNTRUSTED_CONTEXT``);
- verified evaluation resolves the authority of the run that produced the
  artifact (registered by the runner, keyed by run_id);
- the verdict is DERIVED FROM THE EXECUTED ITEMS, never from submitted
  statuses;
- the submitted report must EXACTLY match the executed result — any missing /
  extra / changed item, status change, evidence-kind change, type/content/
  hash/namespace change FAILS (complete-match contract);
- missing executed items fail closed; every artifact type has a strict typed
  content model (not a string allowlist).

These tests are RED on the R5 code and GREEN after R6-A.
"""
from __future__ import annotations

import pytest

from reaction_agent.p3.gate import (
    GateExecutionAuthority,
    evaluate_gate_artifact,
    run_p3_gate,
)


def _real_artifact() -> dict:
    report = run_p3_gate(run_mutations=True)
    return report.model_dump(mode="json")


# -- 1. the audit's decisive repro: real context + elevated status -----------


def test_actual_context_blocked_status_cannot_be_elevated_to_pass():
    """The audit's exact attack: keep the REAL executed context, elevate the
    submitted G01/G03/G07 status from BLOCKED to PASS.  The verdict must NOT
    become PASS — the executed statuses govern."""
    report = run_p3_gate(run_mutations=True)
    artifact = report.model_dump(mode="json")
    for item in artifact["items"]:
        if item["item_id"] in ("G01", "G03", "G07"):
            item["status"] = "PASS"
            item["evidence_kind"] = "real"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL", (
        f"elevated submitted status must be rejected, got {evaluation.verdict}"
    )
    assert evaluation.verified is False
    assert any(
        f.startswith("EXECUTED_STATUS_MISMATCH") or f.startswith("EXECUTED_EVIDENCE_KIND_MISMATCH")
        for f in evaluation.machinery_failures
    )


# -- 2. empty context is not execution authority ------------------------------


def test_empty_context_is_not_execution_authority():
    """The audit's repro: an empty public context ``{}`` must NOT be an
    execution authority (verified must be False)."""
    artifact = _real_artifact()
    evaluation = evaluate_gate_artifact(artifact, trusted_context={})
    assert evaluation.verified is False
    assert evaluation.verdict == "FAIL"
    assert "UNTRUSTED_CONTEXT" in evaluation.machinery_failures


# -- 3. missing executed item fails closed ------------------------------------


def test_missing_executed_item_fails_closed():
    report = run_p3_gate(run_mutations=True)
    artifact = report.model_dump(mode="json")
    # Drop one submitted item: the executed set still has it -> missing.
    artifact["items"] = [i for i in artifact["items"] if i["item_id"] != "G02"]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert evaluation.verified is False
    assert any(
        f.startswith("EXECUTED_ITEM_MISSING") or f.startswith("MISSING_GATE_ITEMS")
        for f in evaluation.machinery_failures
    )


# -- 4. executed vs submitted status mismatch fails ---------------------------


def test_executed_and_submitted_status_mismatch_fails():
    """A submitted PASS for an executed BLOCKED item (or vice versa) must
    fail even when the item is otherwise valid."""
    report = run_p3_gate(run_mutations=True)
    artifact = report.model_dump(mode="json")
    # G02 is executed as PASS; flip the submitted status to BLOCKED.
    for item in artifact["items"]:
        if item["item_id"] == "G02":
            item["status"] = "BLOCKED"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(
        f.startswith("EXECUTED_STATUS_MISMATCH") for f in evaluation.machinery_failures
    )


# -- 5. executed vs submitted evidence kind mismatch fails --------------------


def test_executed_and_submitted_evidence_kind_mismatch_fails():
    report = run_p3_gate(run_mutations=True)
    artifact = report.model_dump(mode="json")
    # G02 is executed as synthetic_fixture; relabel it real.
    for item in artifact["items"]:
        if item["item_id"] == "G02":
            item["evidence_kind"] = "real"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(
        f.startswith("EXECUTED_EVIDENCE_KIND_MISMATCH")
        for f in evaluation.machinery_failures
    )


# -- 6. executed vs submitted content rehash mismatch fails -------------------


def test_executed_and_submitted_content_rehash_mismatch_fails():
    """A submitted evidence whose content was changed (and its content hash
    recomputed) must fail against the executed evidence."""
    import hashlib

    report = run_p3_gate(run_mutations=True)
    artifact = report.model_dump(mode="json")
    ev = artifact["items"][0]["evidence"][0]
    ev["content"] = {**ev["content"], "forged": True}
    ev["content_hash"] = hashlib.sha256(
        repr(ev["content"]).encode("utf-8")
    ).hexdigest()
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(
        f.startswith("EXECUTED_EVIDENCE_MISMATCH") or f.startswith("EVIDENCE_HASH_MISMATCH")
        for f in evaluation.machinery_failures
    )


# -- 7. artifact-type-specific content schema mismatch fails ------------------


def test_artifact_type_specific_content_schema_mismatch_fails():
    """Relabeling a real kernel_run payload as capability_probe (keeping the
    artifact ID) must fail the STRICT typed content model of the target
    type — not just a string allowlist."""
    report = run_p3_gate(run_mutations=True)
    artifact = report.model_dump(mode="json")
    artifact["items"][0]["evidence"][0]["artifact_type"] = "capability_probe"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(
        f.startswith("EVIDENCE_ARTIFACT_SCHEMA") for f in evaluation.machinery_failures
    )


# -- 8. public caller cannot construct a verified context ---------------------


def test_public_caller_cannot_construct_verified_context():
    """A caller must NOT be able to construct an execution authority.  The
    constructor requires the module-private proof token (never exported), so
    direct construction raises TypeError.  A plain dict / empty dict / any
    other object is rejected by the verifier."""
    report = run_p3_gate(run_mutations=True)
    artifact = report.model_dump(mode="json")
    # A plain dict of items is NOT an authority.
    evaluation = evaluate_gate_artifact(
        artifact, trusted_context={i["item_id"]: i for i in artifact["items"]},
    )
    assert evaluation.verified is False
    assert "UNTRUSTED_CONTEXT" in evaluation.machinery_failures
    # Direct construction of the opaque authority is impossible for callers.
    with pytest.raises(TypeError):
        GateExecutionAuthority(report.items, object())  # wrong proof
    # The real gate artifact resolves the authority of its own run and is
    # verified (the only legitimate path).
    legit = evaluate_gate_artifact(artifact)
    assert legit.verified is True
    assert legit.machinery_failures == []
    assert legit.verdict == report.verdict