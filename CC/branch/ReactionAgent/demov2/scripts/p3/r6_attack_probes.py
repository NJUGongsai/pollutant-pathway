#!/usr/bin/env python
"""R6-A / R6-B attack probes (RED on the R5 code, GREEN after R6 fixes).

Each probe reproduces the EXACT attack the ChatGPT Round 5 audit documented.
The probes are REAL: they run the production gate against a real gate report
and mutate it the way the audit did.  The output is a single JSON document
that the R6 evidence generator captures.

RED expectation (R5 code): the probe returns a verdict that is NOT FAIL
(verified=True PASS / BLOCKED with no machinery failures) — the attack was
not detected.
GREEN expectation (R6 code): every probe returns FAIL with a typed machinery
failure — the attack is detected.
"""
from __future__ import annotations

import hashlib
import json
import sys

sys.path.insert(0, ".")

from reaction_agent.p3.gate import evaluate_gate_artifact, run_p3_gate  # noqa: E402


def _sha256(text: str) -> str:
    if isinstance(text, str):
        text = text.encode("utf-8")
    return hashlib.sha256(text).hexdigest()


def _artifact():
    report = run_p3_gate(run_mutations=True)
    return report.model_dump(mode="json")


def probe_submitted_status_elevation_with_actual_context():
    """R6-A #1: real context, submitted G01/G03/G07 status elevated to PASS."""
    artifact = _artifact()
    for item in artifact["items"]:
        if item["item_id"] in ("G01", "G03", "G07"):
            item["status"] = "PASS"
            item["evidence_kind"] = "real"
    evaluation = evaluate_gate_artifact(artifact)
    return {
        "probe": "submitted_status_elevation_with_actual_context",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
        "item_statuses": evaluation.item_statuses,
    }


def probe_empty_public_context():
    """R6-A #2: an empty dict must not be an execution authority."""
    artifact = _artifact()
    evaluation = evaluate_gate_artifact(artifact, trusted_context={})
    return {
        "probe": "empty_public_context",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
    }


def probe_artifact_type_content_mismatch_with_actual_context():
    """R6-A #3: relabel a real kernel_run payload as capability_probe."""
    artifact = _artifact()
    artifact["items"][0]["evidence"][0]["artifact_type"] = "capability_probe"
    evaluation = evaluate_gate_artifact(artifact)
    return {
        "probe": "artifact_type_content_mismatch_with_actual_context",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
    }


def probe_mutation_artifact_rewritten_and_rehashed():
    """R6-B #1: rewrite the typed artifact and recompute its hash."""
    artifact = _artifact()
    m = artifact["mutations"][0]
    m["mutated"]["artifact"] = {**m["mutated"]["artifact"], "_forged": True}
    artifact_json = json.dumps(
        m["mutated"]["artifact"], ensure_ascii=False, sort_keys=True, default=str,
    )
    m["mutated"]["artifact_hash"] = _sha256(artifact_json)
    evaluation = evaluate_gate_artifact(artifact)
    return {
        "probe": "mutation_artifact_rewritten_and_rehashed",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
    }


def probe_mutation_stdout_rewritten_and_rehashed():
    """R6-B #2: rewrite the raw output and recompute its hash."""
    artifact = _artifact()
    m = artifact["mutations"][0]
    m["mutated"]["raw_output"] = m["mutated"]["raw_output"] + "\nFORGED\n"
    m["mutated"]["stdout_stderr_hash"] = _sha256(m["mutated"]["raw_output"])
    evaluation = evaluate_gate_artifact(artifact)
    return {
        "probe": "mutation_stdout_rewritten_and_rehashed",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
    }


def probe_receipt_identity_fields():
    """R6-B #3: the real receipts' run_id/component/schema_version."""
    artifact = _artifact()
    m = artifact["mutations"][0]
    return {
        "probe": "receipt_identity_fields",
        "run_id": m["mutated"]["run_id"],
        "component": m["mutated"]["component"],
        "schema_version": m["mutated"]["schema_version"],
        "session_nonce": m["mutated"]["session_nonce"],
    }


def probe_receipt_from_previous_execution_nonce():
    """R6-B #8: a receipt bound to a previous execution nonce."""
    artifact = _artifact()
    artifact["mutations"][0]["mutated"]["session_nonce"] = "previous_execution_nonce"
    evaluation = evaluate_gate_artifact(artifact)
    return {
        "probe": "receipt_from_previous_execution_nonce",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
    }


def probe_public_context_construction():
    """R6-A #8: a public caller cannot construct a verified context."""
    artifact = _artifact()
    evaluation = evaluate_gate_artifact(
        artifact, trusted_context={i["item_id"]: i for i in artifact["items"]},
    )
    return {
        "probe": "public_context_construction",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
    }


def probe_real_gate_artifact():
    """Baseline: the real gate artifact must still pass machinery verification."""
    artifact = _artifact()
    evaluation = evaluate_gate_artifact(artifact)
    return {
        "probe": "real_gate_artifact",
        "verdict": evaluation.verdict,
        "verified": evaluation.verified,
        "machinery_failures": evaluation.machinery_failures,
    }


PROBES = [
    probe_submitted_status_elevation_with_actual_context,
    probe_empty_public_context,
    probe_artifact_type_content_mismatch_with_actual_context,
    probe_mutation_artifact_rewritten_and_rehashed,
    probe_mutation_stdout_rewritten_and_rehashed,
    probe_receipt_identity_fields,
    probe_receipt_from_previous_execution_nonce,
    probe_public_context_construction,
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