"""R8: the execution authority shares no mutable object with the returned
GateReport.

ChatGPT P3 Round 7 audit finding (CLOSED in Round 8):

``run_p3_gate()`` generated ``items`` and ``mutations`` and handed the SAME
objects to both ``GateExecutionAuthority`` and constructor of the returned
``GateReport``.  ``GateExecutionAuthority`` wrapped the lists in tuples, but a
tuple only prevents the container from being resized — the Pydantic models and
nested dicts inside stayed mutable and shared.  ``report.mutations[0] is
authority.mutations[0]`` was ``True``, so mutating a returned report's
mutation (re-syncing the raw receipt, artifact hash and stdout hash) also
mutated the authority's "audit basis" and the artifact still evaluated to
``verified=True``.

R8 contract:
- the authority converts every executed item and mutation into an INDEPENDENT
  canonical JSON snapshot at registration time (plain immutable strings);
- ``items`` / ``mutations`` / ``executed`` expose parsed COPIES of the
  snapshots — never the original mutable model references;
- modifying the returned ``GateReport`` (or any nested dict/list inside it)
  can never change the authority's audit basis;
- the exact-match comparison in ``evaluate_gate_artifact`` runs against the
  authority's independent snapshots, so a report-mutated mutation/item fails
  with a typed machinery failure and ``verified=False``.

These tests are RED on the R7 code and GREEN after R8.
"""
from __future__ import annotations

import hashlib
import json

from reaction_agent.p3.gate import (
    _resolve_execution_authority,
    evaluate_gate_artifact,
    run_p3_gate,
)
from reaction_agent.p3.mutation_harness import RECEIPT_BEGIN, RECEIPT_END


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rebuild_raw_receipt(payload: dict) -> str:
    """Rebuild the marker-delimited receipt exactly as the subprocess emits it."""
    return (
        RECEIPT_BEGIN + "\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        + "\n" + RECEIPT_END + "\n"
    )


# -- 1. the audit's decisive repro: mutate a returned report mutation ---------


def test_mutating_returned_report_mutation_does_not_change_execution_authority():
    """The audit's exact repro:

    1. call the real ``run_p3_gate()`` and take the returned report AND the
       registered in-process execution authority;
    2. parse a real mutated receipt from the returned report;
    3. modify the artifact inside the receipt;
    4. recompute the receipt ``artifact_hash``;
    5. synchronously update the typed ``run.artifact`` and ``run.artifact_hash``;
    6. regenerate the full marker-delimited raw receipt;
    7. recompute ``stdout_stderr_hash``;
    8. keep every other mutation contract field legal;
    9. call ``evaluate_gate_artifact()`` with the mutated report.

    The verdict must be FAIL, ``verified`` False, and the failures must
    contain ``EXECUTED_MUTATION_MISMATCH`` — the authority's audit basis is
    an independent snapshot that the report mutation cannot touch.
    """
    from reaction_agent.p3.mutation_harness import parse_strict_receipt

    report = run_p3_gate(run_mutations=True)
    authority = _resolve_execution_authority("p3_gate")
    assert authority is not None

    # R8: the authority does NOT hold the report's mutable model references —
    # it exposes parsed copies of independent canonical snapshots, so the
    # report mutation and the authority audit basis are never the same object.
    assert not isinstance(authority.mutations[0], type(report.mutations[0]))
    snap_before = authority.mutations[0]

    # 2. parse the real receipt from the returned report's raw output
    m = report.mutations[0]
    side = m.mutated
    receipt = parse_strict_receipt(side.raw_output)
    assert receipt is not None, "real mutated receipt must be parseable"

    # 3-4. modify the artifact inside the receipt payload + recompute its hash
    forged_artifact = {**receipt["artifact"], "_forged": True}
    forged_json = json.dumps(
        forged_artifact, ensure_ascii=False, sort_keys=True, default=str,
    )
    receipt = {**receipt, "artifact": forged_artifact,
               "artifact_hash": _sha256(forged_json)}
    # 5. synchronously update the typed artifact + artifact hash
    side.artifact = forged_artifact
    side.artifact_hash = _sha256(forged_json)
    # 6-7. regenerate the full raw receipt + recompute the stdout hash
    side.raw_output = _rebuild_raw_receipt(receipt)
    side.stdout_stderr_hash = _sha256(side.raw_output)

    # R8: the authority's audit basis is unchanged by the report mutation.
    assert authority.mutations[0] == snap_before
    assert "_forged" not in json.dumps(
        authority.mutations[0]["mutated"]["artifact"]
    )

    # 9. verify the mutated report against the in-process execution authority
    evaluation = evaluate_gate_artifact(report.model_dump(mode="json"))
    assert evaluation.verdict == "FAIL", (
        f"report-mutated mutation must be rejected against the executed "
        f"snapshot, got {evaluation.verdict}"
    )
    assert evaluation.verified is False
    assert any(
        f.startswith("EXECUTED_MUTATION_MISMATCH")
        for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"


# -- 2. mutate a returned report item ------------------------------------------


def test_mutating_returned_report_item_does_not_change_execution_authority():
    """Mutating a returned report's item status + evidence must not change the
    authority's executed item, and the evaluation must FAIL."""
    report = run_p3_gate(run_mutations=True)
    authority = _resolve_execution_authority("p3_gate")
    assert authority is not None

    # Baseline: G02 is executed as PASS with synthetic_fixture evidence.
    executed_before = authority.executed("G02")
    assert executed_before is not None
    assert executed_before["status"] == "PASS"

    # R8: the exposed snapshot is a COPY — mutating it cannot change the
    # authority's independent audit basis.
    probe = authority.executed("G02")
    probe["status"] = "FAIL"
    assert authority.executed("G02")["status"] == "PASS"

    # Mutate the RETURNED report's item: status + evidence content + rehash.
    for item in report.items:
        if item.item_id == "G02":
            item.status = "BLOCKED"
            ev = item.evidence[0]
            ev.content = {**ev.content, "_forged": True}
            ev.content_hash = hashlib.sha256(
                repr(ev.content).encode("utf-8")
            ).hexdigest()

    # The authority's executed item is unchanged by the report mutation.
    executed_after = authority.executed("G02")
    assert executed_after == executed_before
    assert executed_after["status"] == "PASS"
    assert "_forged" not in json.dumps(executed_after["evidence"][0]["content"])

    evaluation = evaluate_gate_artifact(report.model_dump(mode="json"))
    assert evaluation.verdict == "FAIL"
    assert evaluation.verified is False
    assert any(
        f.startswith("EXECUTED_STATUS_MISMATCH")
        or f.startswith("EXECUTED_EVIDENCE_MISMATCH")
        for f in evaluation.machinery_failures
    ), f"failures={evaluation.machinery_failures}"


# -- 3. the genuine gate still passes (no regression) --------------------------


def test_real_gate_still_verifies_against_snapshot_authority():
    """The real gate's own artifacts must still exactly match the authority's
    independent snapshots and pass machinery verification."""
    report = run_p3_gate(run_mutations=True)
    evaluation = evaluate_gate_artifact(report.model_dump(mode="json"))
    assert evaluation.verified is True
    assert evaluation.machinery_failures == [], (
        f"failures={evaluation.machinery_failures}"
    )
    authority = _resolve_execution_authority("p3_gate")
    assert authority is not None
    assert len(authority.mutations) == len(report.mutations)
    assert len(authority.items) == len(report.items)