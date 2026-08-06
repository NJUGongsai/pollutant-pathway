"""R4-A: Gate artifacts must be bound to REAL executed evidence.

ChatGPT P3 Round 3 audit independently constructed a fully-fabricated typed
gate artifact (live schema hash + 10 hand-written PASS items + arbitrary
non-empty evidence strings + empty mutations) and obtained::

    fully_fabricated_typed_gate_verdict='PASS'
    fully_fabricated_typed_gate_verified=True

This test locks the R4-A contract: evidence must be typed, hash-verifiable,
namespace-bound references; the mutation set is mandatory and must exactly
equal the frozen registry; every mutation must carry real execution
artifacts and be internally consistent.
"""
from __future__ import annotations

from reaction_agent.p3.gate import (
    REQUIRED_GATE_ITEMS,
    GateItemResult,
    evaluate_gate_artifact,
    make_evidence_reference,
    run_p3_gate,
)
from reaction_agent.p3.manifest import build_interface_manifest, manifest_schema_hash
from reaction_agent.p3.schemas import EvidenceKind

_NS = {
    "fold_id": "fold_r4a",
    "snapshot_id": "snap_r4a",
    "snapshot_hash": "hh_r4a",
}


def _live_hash():
    return manifest_schema_hash(build_interface_manifest())


def _ev_ref(item_id, **over):
    # R6-A: the artifact content must satisfy the STRICT typed content model
    # of its artifact type (kernel_run), so the fabricated items use a
    # schema-valid kernel_run gate_check.
    ref = make_evidence_reference(
        artifact_type="kernel_run", artifact_id=f"run_{item_id}",
        content={"gate_check": "equivalent_smiles_invariant", "ok": True},
        run_id="run_r4a", **{**_NS, **over},
    )
    return ref.model_dump(mode="json")


_REPORT_SESSION_NONCE = None


def _mutations():
    global _REPORT_SESSION_NONCE
    if _REPORT_SESSION_NONCE is None:
        report = run_p3_gate(run_mutations=True)
        _REPORT_SESSION_NONCE = report.session_nonce
        cached = [m.model_dump(mode="json") for m in report.mutations]
    else:
        cached = [m.model_dump(mode="json") for m in run_p3_gate(run_mutations=True).mutations]
    return cached


def _items(overrides=None):
    overrides = overrides or {}
    kinds = {"G01": EvidenceKind.real, "G03": EvidenceKind.real, "G07": EvidenceKind.real}
    out = []
    for item_id in REQUIRED_GATE_ITEMS:
        out.append(GateItemResult(
            item_id=item_id, title=f"t {item_id}", status="PASS",
            evidence=[make_evidence_reference(
                artifact_type="kernel_run", artifact_id=f"run_{item_id}",
                content={"gate_check": "equivalent_smiles_invariant", "ok": True},
                run_id="run_r4a", **_NS,
            )],
            evidence_kind=kinds.get(item_id, EvidenceKind.synthetic_fixture),
        ).model_dump(mode="json"))
    for idx, ov in overrides.items():
        out[int(idx[1:]) - 1].update(ov)
    return out


def _artifact(**extra):
    return {
        "gate_id": "p3_gate",
        "interface_manifest_schema_hash": _live_hash(),
        "run_id": "run_r4a", "case_id": "case_r4a", "query_id": "q_r4a",
        **_NS,
        "mutation_registry_hash": _registry_hash(),
        # R6-B: the artifact must carry the SAME session nonce as the
        # mutation receipts it embeds.
        "session_nonce": _report_session_nonce(),
        "items": _items(),
        "mutations": _mutations(),
        **extra,
    }


def _report_session_nonce():
    _mutations()
    return _REPORT_SESSION_NONCE


def _registry_hash():
    from reaction_agent.p3.mutations_round3 import mutation_registry_hash
    return mutation_registry_hash()


# -- 1. arbitrary non-empty evidence strings ---------------------------------


def test_arbitrary_evidence_strings_rejected():
    artifact = _artifact()
    # The audit's forgery: bare non-empty strings under evidence.  Build the
    # item as a raw dict (bypassing the model validator like a forger would).
    artifact["items"] = [
        {
            "item_id": i,
            "title": f"t {i}",
            "status": "PASS",
            "evidence": ["verified artifact evidence"],
            "evidence_kind": (
                "real" if i in ("G01", "G03", "G07")
                else "synthetic_fixture"
            ),
        }
        for i in REQUIRED_GATE_ITEMS
    ]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "ITEMS_NOT_TYPED" in evaluation.machinery_failures or any(
        f.startswith("EVIDENCE_") for f in evaluation.machinery_failures
    )


def test_fully_fabricated_typed_gate_artifact_cannot_pass():
    # The EXACT audit forgery shape: typed items + arbitrary strings + empty
    # mutations.  R4-A must reject it.
    artifact = _artifact(mutations=[])
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "EMPTY_MUTATIONS" in evaluation.machinery_failures


# -- 2./3. evidence content tampered without hash update ---------------------


def test_evidence_content_tampered_without_hash_update_rejected():
    artifact = _artifact()
    ref = _ev_ref("G02")
    ref["content"] = {"gate_check": "EVIDENCE_FORGED", "ok": False}
    artifact["items"][1]["evidence"] = [ref]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(f.startswith("EVIDENCE_HASH_MISMATCH") for f in evaluation.machinery_failures)


def test_evidence_hash_replaced_with_another_valid_artifact_rejected():
    # hash of a DIFFERENT artifact content — does not match the embedded content.
    other = make_evidence_reference(
        artifact_type="kernel_run", artifact_id="run_other",
        content={"gate_check": "other", "ok": True},
        run_id="run_r4a", **_NS,
    )
    ref = _ev_ref("G02")
    ref["content_hash"] = other.content_hash
    artifact = _artifact()
    artifact["items"][1]["evidence"] = [ref]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(f.startswith("EVIDENCE_HASH_MISMATCH") for f in evaluation.machinery_failures)


def test_evidence_empty_content_rejected():
    artifact = _artifact()
    ref = _ev_ref("G02")
    ref["content"] = {}
    artifact["items"][1]["evidence"] = [ref]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(f.startswith("EVIDENCE_EMPTY_CONTENT") for f in evaluation.machinery_failures)


# -- 5. namespace mismatch ----------------------------------------------------


def test_evidence_fold_namespace_mismatch_rejected():
    artifact = _artifact()
    artifact["items"][1]["evidence"] = [_ev_ref("G02", fold_id="fold_OTHER")]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(f.startswith("EVIDENCE_FOLD_MISMATCH") for f in evaluation.machinery_failures)


def test_evidence_snapshot_namespace_mismatch_rejected():
    artifact = _artifact()
    artifact["items"][1]["evidence"] = [_ev_ref("G02", snapshot_id="snap_OTHER")]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(f.startswith("EVIDENCE_SNAPSHOT_MISMATCH") for f in evaluation.machinery_failures)


def test_evidence_ref_omitting_declared_namespace_rejected():
    # Fail-closed: when the artifact declares a namespace, an evidence
    # reference that OMITS the fold/snapshot binding is rejected.
    artifact = _artifact()
    ref = _ev_ref("G02")
    ref["fold_id"] = ""
    ref["snapshot_id"] = ""
    ref["snapshot_hash"] = ""
    artifact["items"][1]["evidence"] = [ref]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(f.startswith("EVIDENCE_FOLD_MISMATCH") for f in evaluation.machinery_failures)


# -- 7./8./9. mutation set is mandatory + exact registry match ----------------


def test_missing_mutations_rejected():
    artifact = _artifact()
    del artifact["mutations"]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "MISSING_MUTATIONS" in evaluation.machinery_failures


def test_empty_mutations_rejected():
    artifact = _artifact(mutations=[])
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "EMPTY_MUTATIONS" in evaluation.machinery_failures


def test_mutations_one_missing_rejected():
    artifact = _artifact()
    artifact["mutations"] = artifact["mutations"][1:]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(f.startswith("MUTATION_ID_MISMATCH") for f in evaluation.machinery_failures)


def test_mutations_one_extra_rejected():
    artifact = _artifact()
    extra = artifact["mutations"][0].copy()
    extra["mutation_id"] = "m_forged_extra"
    artifact["mutations"] = artifact["mutations"] + [extra]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(f.startswith("MUTATION_ID_MISMATCH") for f in evaluation.machinery_failures)


def test_mutations_duplicate_rejected():
    artifact = _artifact()
    artifact["mutations"] = artifact["mutations"] + [artifact["mutations"][0]]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "MUTATION_ID_DUPLICATE" in evaluation.machinery_failures


def test_mutations_unknown_rejected():
    artifact = _artifact()
    artifact["mutations"][0]["mutation_id"] = "m_unknown_xy"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(f.startswith("MUTATION_ID_MISMATCH") for f in evaluation.machinery_failures)


# -- 10. mutation without real execution artifact -----------------------------


def test_mutation_without_baseline_artifact_rejected():
    artifact = _artifact()
    artifact["mutations"][0]["baseline"]["artifact_hash"] = ""
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(f.startswith("MUTATION_NO_BASELINE_ARTIFACT") for f in evaluation.machinery_failures)


def test_mutation_observed_code_mismatch_rejected():
    artifact = _artifact()
    artifact["mutations"][0]["observed_failure_code"] = "SOMETHING_ELSE"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(f.startswith("MUTATION_OBSERVED_CODE_MISMATCH") for f in evaluation.machinery_failures)


# -- 11. synthetic evidence pretending to be real -----------------------------


def test_synthetic_evidence_as_real_rejected():
    artifact = _artifact()
    artifact["items"][0]["evidence_kind"] = "synthetic_fixture"  # G01 real item
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "SYNTHETIC_AS_REAL_EVIDENCE" in evaluation.machinery_failures


# -- 12. machinery FAIL dominates real-resource BLOCKED -----------------------


def test_machinery_failure_dominates_blocked():
    artifact = _artifact()
    # G01 honestly BLOCKED (real resource missing) ...
    artifact["items"][0].update({
        "status": "BLOCKED", "evidence_kind": "blocked",
        "evidence": [_ev_ref("G01", fold_id="fold_r4a")],
    })
    # ... but a machinery failure (forged schema hash) is present.
    artifact["interface_manifest_schema_hash"] = "forged"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"


def test_blocked_only_keeps_blocked_verdict():
    artifact = _artifact()
    for idx in ("G01", "G03", "G07"):
        artifact["items"][int(idx[1:]) - 1].update({
            "status": "BLOCKED", "evidence_kind": "blocked",
        })
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "BLOCKED"


# -- 13. a real minimal execution chain artifact passes -----------------------


def test_real_gate_artifact_passes_machinery_verification():
    report = run_p3_gate(run_mutations=True)
    artifact = report.model_dump(mode="json")
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.machinery_failures == []
    assert evaluation.verdict == report.verdict


def test_real_gate_artifact_is_honestly_blocked_on_real_evidence():
    report = run_p3_gate(run_mutations=True)
    blocked = [i for i in report.items if i.status == "BLOCKED"]
    assert blocked, "real-evidence items must remain honestly BLOCKED"
    assert report.verdict == "BLOCKED"