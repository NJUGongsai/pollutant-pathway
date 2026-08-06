"""R5-A: gate artifacts must carry REAL in-process execution authority.

ChatGPT P3 Round 4 independent audit constructed a fully-fabricated gate
artifact (live interface hash + 10 hand-written PASS items + attacker-chosen
content/hash/run-id/status + nonexistent artifact IDs + executed=false) and
obtained:

    fully_fabricated_round4_verdict='PASS'
    fully_fabricated_round4_verified=True

Root cause: ``EvidenceReference`` was self-authored/self-signed — the caller
supplied content, content hash, artifact ID, artifact type, run ID, evidence
kind and Gate status, and the verifier only proved the caller's content
matched the caller's hash.  ``canonical_hash(content) == content_hash`` is an
integrity check, NOT a provenance/execution proof.

R5-A adopts trust model A (in-process execution authority):
- only the actual Gate runner's EXECUTED checks produce authoritative items;
- every Gate item status is DERIVED from the check function's return value;
- serialized artifacts are only ``structurally_valid``; a JSON dict alone can
  NEVER become ``verified=True``;
- the verifier requires a trusted execution context (the typed item objects
  produced by the runner) and recomputes every item from the live checks;
- a bare dict without the trusted execution context cannot get verified PASS.

These tests lock that contract.  They are RED on the R4 code (the fabricated
artifact passes) and GREEN after R5-A.
"""
from __future__ import annotations

import pytest

from reaction_agent.p3.gate import (
    REQUIRED_GATE_ITEMS,
    GateEvaluation,
    evaluate_gate_artifact,
    run_p3_gate,
)
from reaction_agent.p3.manifest import build_interface_manifest, manifest_schema_hash

_NS = {
    "fold_id": "fold_r5a",
    "snapshot_id": "snap_r5a",
    "snapshot_hash": "hh_r5a",
}


def _live_hash():
    return manifest_schema_hash(build_interface_manifest())


def _fabricated_item(item_id: str) -> dict:
    """The exact Round-4 audit forgery: attacker-chosen content/hash/status."""
    content = {
        "gate_check": f"forged {item_id}",
        "executed": False,
        "real_artifact": False,
    }
    return {
        "item_id": item_id,
        "title": f"t {item_id}",
        "status": "PASS",
        "evidence": [{
            "artifact_type": "kernel_run",
            "artifact_id": "nonexistent_artifact_xyz",
            "content_hash": "deadbeef" * 8,
            "schema_version": "p3-1",
            "run_id": "run_attacker",
            "fold_id": "fold_r5a",
            "snapshot_id": "snap_r5a",
            "snapshot_hash": "hh_r5a",
            "content": content,
        }],
        "evidence_kind": (
            "real" if item_id in ("G01", "G03", "G07") else "synthetic_fixture"
        ),
    }


def _fabricated_artifact(**extra) -> dict:
    return {
        "gate_id": "p3_gate",
        "interface_manifest_schema_hash": _live_hash(),
        "run_id": "run_attacker", "case_id": "case_attacker", "query_id": "q_attacker",
        **_NS,
        "items": [_fabricated_item(i) for i in REQUIRED_GATE_ITEMS],
        "mutations": [],
        **extra,
    }


# -- 1. fully-fabricated artifact (the Round-4 audit repro) -------------------


def test_fully_fabricated_artifact_cannot_verify() -> None:
    """A dict with attacker content+hash+status must NOT become verified PASS."""
    evaluation = evaluate_gate_artifact(_fabricated_artifact())
    assert evaluation.verdict == "FAIL", (
        f"fully-fabricated artifact must FAIL, got {evaluation.verdict}"
    )
    assert evaluation.verified is False
    assert evaluation.machinery_failures, "must carry machinery failures"


# -- 2. content + content hash BOTH replaced by attacker ----------------------


def test_attacker_replaced_content_and_hash_rejected() -> None:
    artifact = _fabricated_artifact()
    # The attacker already replaced BOTH content and hash (self-consistent).
    # Without a trusted execution root this must fail — the hash proves
    # nothing about execution.
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert evaluation.verified is False


# -- 3. nonexistent artifact ID / path ----------------------------------------


def test_nonexistent_artifact_id_rejected() -> None:
    artifact = _fabricated_artifact()
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("ARTIFACT" in f or "EXECUTION" in f or "EVIDENCE" in f
               for f in evaluation.machinery_failures)


# -- 4. unknown artifact type --------------------------------------------------


def test_unknown_artifact_type_rejected() -> None:
    artifact = _fabricated_artifact()
    artifact["items"][0]["evidence"][0]["artifact_type"] = "attacker_claim"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert evaluation.verified is False


# -- 5. artifact type / content schema mismatch --------------------------------


def test_artifact_type_content_schema_mismatch_rejected() -> None:
    artifact = _fabricated_artifact()
    # capability_probe content must be a typed CapabilityStatus; a kernel_run
    # payload is not.
    artifact["items"][0]["evidence"][0]["artifact_type"] = "capability_probe"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"


# -- 6. evidence run id mismatch -----------------------------------------------


def test_evidence_run_id_mismatch_rejected() -> None:
    artifact = _fabricated_artifact()
    artifact["items"][0]["evidence"][0]["run_id"] = "run_OTHER"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("RUN" in f or "run" in f for f in evaluation.machinery_failures)


# -- 7. case/query/fold/snapshot namespace mismatch ----------------------------


def test_namespace_mismatch_rejected() -> None:
    artifact = _fabricated_artifact()
    artifact["items"][0]["evidence"][0]["fold_id"] = "fold_OTHER"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("FOLD" in f for f in evaluation.machinery_failures)


# -- 8. attacker hand-written evidence_kind=real -------------------------------


def test_attacker_handwritten_evidence_kind_real_rejected() -> None:
    artifact = _fabricated_artifact()
    # G02 is a machinery item; attacker marking it real must not help.
    artifact["items"][1]["evidence_kind"] = "real"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"


# -- 9. attacker status=PASS but evidence indicates failure --------------------


def test_attacker_status_pass_but_evidence_failure_rejected() -> None:
    artifact = _fabricated_artifact()
    artifact["items"][0]["evidence"][0]["content"]["executed"] = False
    artifact["items"][0]["evidence"][0]["content"]["real_artifact"] = False
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert evaluation.verified is False


# -- 10. legal executed artifact moved to another run --------------------------


def test_legit_artifact_moved_to_another_run_rejected() -> None:
    # Take the REAL gate report's items and move one evidence ref to a
    # different run_id: the verifier must reject the run mismatch.
    report = run_p3_gate(run_mutations=True)
    artifact = report.model_dump(mode="json")
    artifact["items"][0]["evidence"][0]["run_id"] = "run_OTHER"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any("RUN" in f for f in evaluation.machinery_failures)


# -- 11. unknown schema version ------------------------------------------------


def test_unknown_schema_version_rejected() -> None:
    artifact = _fabricated_artifact()
    artifact["items"][0]["evidence"][0]["schema_version"] = "p3-999"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"


# -- 12. offline dict without trusted resolver/context -------------------------


def test_offline_dict_without_trusted_context_rejected() -> None:
    # A serialized dict with no trusted execution context can only be
    # structurally validated — never verified.
    artifact = _fabricated_artifact()
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verified is False
    assert evaluation.verdict == "FAIL"


# -- 13. genuinely executed minimal machinery gate can verify ------------------


def test_real_executed_gate_artifact_passes_machinery_verification() -> None:
    report = run_p3_gate(run_mutations=True)
    artifact = report.model_dump(mode="json")
    # R6-A: the artifact is verified against the opaque GateExecutionAuthority
    # of the run that produced it (auto-resolved by run_id).  A public caller
    # cannot construct an authority itself.
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.machinery_failures == []
    assert evaluation.verified is True
    assert evaluation.verdict == report.verdict


# -- 14. machinery FAIL dominates real BLOCKED ---------------------------------


def test_machinery_failure_dominates_blocked() -> None:
    artifact = _fabricated_artifact()
    # G01 honestly BLOCKED (real resource missing) ...
    artifact["items"][0].update({
        "status": "BLOCKED", "evidence_kind": "blocked",
    })
    # ... but a machinery failure (forged schema hash) is present.
    artifact["interface_manifest_schema_hash"] = "forged"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"


# -- 15. the real gate report is honestly BLOCKED on real evidence -------------


def test_real_gate_is_honestly_blocked_on_real_evidence() -> None:
    report = run_p3_gate(run_mutations=True)
    blocked = [i for i in report.items if i.status == "BLOCKED"]
    assert blocked, "real-evidence items must remain honestly BLOCKED"
    assert report.verdict == "BLOCKED"