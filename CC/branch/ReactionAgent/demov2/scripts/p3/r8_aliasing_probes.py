#!/usr/bin/env python
"""R8 authority-aliasing probes (RED on the R7 code, GREEN after R8 fixes).

Each probe reproduces the EXACT attack the ChatGPT Round 7 audit documented:

R8 (report/authority mutable aliasing): ``run_p3_gate()`` handed the SAME
mutable ``items`` / ``mutations`` objects to both ``GateExecutionAuthority``
and the returned ``GateReport``.  ``report.mutations[0] is
authority.mutations[0]`` was ``True``, so mutating a returned report's
mutation (re-syncing the raw receipt + artifact hash + stdout hash) also
mutated the authority's "audit basis" — the artifact still evaluated to
``verified=True``.

RED expectation (R7 code): the probe returns ``verified=True`` with no
machinery failures (or ``same_object=true``).
GREEN expectation (R8 code): every probe returns FAIL with a typed machinery
failure (``EXECUTED_MUTATION_MISMATCH`` / ``EXECUTED_STATUS_MISMATCH`` /
``EXECUTED_EVIDENCE_MISMATCH``), ``same_object=false``, and the authority's
snapshot is unchanged by the report mutation.
"""
from __future__ import annotations

import hashlib
import json
import sys

sys.path.insert(0, ".")

from reaction_agent.p3.gate import (  # noqa: E402
    _resolve_execution_authority,
    evaluate_gate_artifact,
    run_p3_gate,
)
from reaction_agent.p3.mutation_harness import (  # noqa: E402
    RECEIPT_BEGIN,
    RECEIPT_END,
    parse_strict_receipt,
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rebuild_raw_receipt(payload: dict) -> str:
    return (
        RECEIPT_BEGIN + "\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        + "\n" + RECEIPT_END + "\n"
    )


def probe_mutation_aliasing():
    """R8: the audit's exact repro — mutate the returned report's mutation
    with a fully-synchronized raw+typed receipt rewrite, then evaluate."""
    report = run_p3_gate(run_mutations=True)
    authority = _resolve_execution_authority("p3_gate")
    if authority is None:
        return {"probe": "mutation_aliasing", "error": "no authority"}
    m = report.mutations[0]
    side = m.mutated
    receipt = parse_strict_receipt(side.raw_output)
    if receipt is None:
        return {"probe": "mutation_aliasing", "error": "receipt not parseable"}
    forged_artifact = {**receipt["artifact"], "_forged": True}
    forged_json = json.dumps(
        forged_artifact, ensure_ascii=False, sort_keys=True, default=str,
    )
    receipt = {**receipt, "artifact": forged_artifact,
               "artifact_hash": _sha256(forged_json)}
    side.artifact = forged_artifact
    side.artifact_hash = _sha256(forged_json)
    side.raw_output = _rebuild_raw_receipt(receipt)
    side.stdout_stderr_hash = _sha256(side.raw_output)
    ev = evaluate_gate_artifact(report.model_dump(mode="json"))
    return {
        "probe": "mutation_aliasing",
        "verdict": ev.verdict,
        "verified": ev.verified,
        "machinery_failures": ev.machinery_failures,
    }


def probe_item_aliasing():
    """R8: mutate the returned report's item status + evidence content."""
    report = run_p3_gate(run_mutations=True)
    authority = _resolve_execution_authority("p3_gate")
    if authority is None:
        return {"probe": "item_aliasing", "error": "no authority"}
    for item in report.items:
        if item.item_id == "G02":
            item.status = "BLOCKED"
            ev = item.evidence[0]
            ev.content = {**ev.content, "_forged": True}
            ev.content_hash = _sha256(repr(ev.content))
    ev = evaluate_gate_artifact(report.model_dump(mode="json"))
    return {
        "probe": "item_aliasing",
        "verdict": ev.verdict,
        "verified": ev.verified,
        "machinery_failures": ev.machinery_failures,
    }


def probe_same_object():
    """R8: the report and the authority must not share a mutable model."""
    report = run_p3_gate(run_mutations=True)
    authority = _resolve_execution_authority("p3_gate")
    if authority is None:
        return {"probe": "same_object", "error": "no authority"}
    return {
        "probe": "same_object",
        "report_mutation_is_authority_mutation": (
            report.mutations[0] is authority.mutations[0]
        ),
        "report_item_is_authority_item": (
            report.items[0] is authority.items[0]
        ),
    }


def probe_authority_snapshot_unchanged():
    """R8: mutating the returned report must not change the authority's
    audit basis (independent canonical snapshot)."""
    report = run_p3_gate(run_mutations=True)
    authority = _resolve_execution_authority("p3_gate")
    if authority is None:
        return {"probe": "authority_snapshot_unchanged", "error": "no authority"}
    m = report.mutations[0]
    snap_before = authority.mutations[0]
    m.mutated.artifact = {**m.mutated.artifact, "_forged": True}
    return {
        "probe": "authority_snapshot_unchanged",
        "snapshot_changed": authority.mutations[0] != snap_before,
        "forged_leaked_into_authority": (
            "_forged" in json.dumps(authority.mutations[0]["mutated"]["artifact"])
        ),
    }


def probe_real_gate_artifact():
    """Baseline: the real gate artifact must still pass machinery verification."""
    report = run_p3_gate(run_mutations=True)
    ev = evaluate_gate_artifact(report.model_dump(mode="json"))
    return {
        "probe": "real_gate_artifact",
        "verdict": ev.verdict,
        "verified": ev.verified,
        "machinery_failures": ev.machinery_failures,
    }


PROBES = [
    probe_mutation_aliasing,
    probe_item_aliasing,
    probe_same_object,
    probe_authority_snapshot_unchanged,
    probe_real_gate_artifact,
]


def main() -> int:
    results = []
    for probe in PROBES:
        try:
            results.append(probe())
        except Exception as exc:  # noqa: BLE001 - probe must not crash the run
            results.append({
                "probe": probe.__name__,
                "error": f"{type(exc).__name__}: {exc}",
            })
    payload = {"probes": results}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())