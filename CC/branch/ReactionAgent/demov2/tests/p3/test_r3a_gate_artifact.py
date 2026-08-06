"""R3-A Gate artifact forgery tests.

Round 2 defect: ``evaluate_gate_from_artifacts`` treated a truthy value under
a recognized key as verified evidence; the forged payload

    {"schema_hash": "not-a-schema-hash", "items": {"G01": "PASS"}}

incorrectly returned ``PASS`` (recorded RED evidence:
``forged_payload_verdict_round2=PASS``).

Round 3 contract: typed artifacts only; schema hashes recomputed from live
schemas; complete G01-G10 item set; missing/duplicate/unknown/invalid items
rejected; every item bound to verified evidence; run-namespace consistency;
evidence-kind semantics (synthetic never satisfies real-evidence items);
stored status strings are never authority; any machinery invariant failure is
FAIL even when other items are BLOCKED.

Round 4 (R4-A): evidence is a list of TYPED, content-hash-verifiable,
namespace-bound ``EvidenceReference`` (never arbitrary strings); the
mutation set is MANDATORY and must EXACTLY equal the frozen registry; every
mutation must carry real execution artifacts and be internally consistent.
"""
import pytest

from reaction_agent.p3.gate import (
    REAL_EVIDENCE_ITEMS,
    REQUIRED_GATE_ITEMS,
    GateItemResult,
    evaluate_gate_artifact,
    evaluate_gate_from_artifacts,
    make_evidence_reference,
    run_p3_gate,
)
from reaction_agent.p3.manifest import build_interface_manifest, manifest_schema_hash
from reaction_agent.p3.schemas import EvidenceKind


def _live_hash():
    return manifest_schema_hash(build_interface_manifest())


_REAL_MUTATIONS = None
_REAL_SESSION_NONCE = None


def _frozen_mutations():
    """The real mutation executions from the gate runner (cached)."""
    global _REAL_MUTATIONS, _REAL_SESSION_NONCE
    if _REAL_MUTATIONS is None:
        report = run_p3_gate(run_mutations=True)
        _REAL_MUTATIONS = report.mutations
        _REAL_SESSION_NONCE = report.session_nonce
    return _REAL_MUTATIONS


def _session_nonce():
    _frozen_mutations()
    return _REAL_SESSION_NONCE


def _ev_ref(item_id, run_id="run_r3a", fold_id="fold_r3a"):
    # R6-A: the artifact content must satisfy the STRICT typed content model
    # of its artifact type (kernel_run), so the fabricated items use a
    # schema-valid kernel_run gate_check.
    return make_evidence_reference(
        artifact_type="kernel_run", artifact_id=f"run_{item_id}",
        content={"gate_check": "equivalent_smiles_invariant", "ok": True},
        run_id=run_id, fold_id=fold_id, snapshot_id="s_r3a", snapshot_hash="h_r3a",
    )


def _typed_item(item_id, status="PASS", kind=EvidenceKind.synthetic_fixture,
                evidence=None):
    return GateItemResult(
        item_id=item_id,
        title=f"title {item_id}",
        status=status,
        evidence=evidence or [_ev_ref(item_id)],
        evidence_kind=kind,
    ).model_dump(mode="json")


def _complete_items(overrides=None):
    overrides = overrides or {}
    kinds = {
        "G01": EvidenceKind.real, "G03": EvidenceKind.real,
        "G07": EvidenceKind.real,
    }
    items = []
    for item_id in REQUIRED_GATE_ITEMS:
        kind = kinds.get(item_id, EvidenceKind.synthetic_fixture)
        items.append(_typed_item(item_id, kind=kind))
    for idx, override in overrides.items():
        items[int(idx[1:]) - 1].update(override)
    return items


def _valid_artifact(mutations=None, **extra):
    if mutations is None:
        mutations = [m.model_dump(mode="json") for m in _frozen_mutations()]
    from reaction_agent.p3.mutations_round3 import mutation_registry_hash
    return {
        "gate_id": "p3_gate",
        "interface_manifest_schema_hash": _live_hash(),
        "run_id": "run_r3a", "case_id": "case_r3a", "query_id": "q_r3a",
        "fold_id": "fold_r3a", "snapshot_id": "s_r3a", "snapshot_hash": "h_r3a",
        "mutation_registry_hash": mutation_registry_hash(),
        # R6-B: the artifact must carry the SAME session nonce as the
        # mutation receipts it embeds.
        "session_nonce": _session_nonce(),
        "items": _complete_items(),
        "mutations": mutations,
        **extra,
    }


# -- 1. The audit's forged payload -------------------------------------------


def test_forged_schema_hash_payload_is_fail():
    forged = {"schema_hash": "not-a-schema-hash", "items": {"G01": "PASS"}}
    evaluation = evaluate_gate_artifact(forged)
    assert evaluation.verdict == "FAIL"
    assert "FORGED_SCHEMA_HASH" in evaluation.machinery_failures


def test_missing_schema_hash_is_fail():
    payload = {"items": {f"G{i:02d}": "PASS" for i in range(1, 11)}}
    evaluation = evaluate_gate_artifact(payload)
    assert evaluation.verdict == "FAIL"
    assert (
        "MISSING_SCHEMA_HASH" in evaluation.machinery_failures
        or "ARTIFACTLESS_PASS" in evaluation.machinery_failures
    )


# -- 2. Incomplete / unknown / duplicate items ---------------------------------


def test_incomplete_typed_items_rejected():
    artifact = _valid_artifact()
    artifact["items"] = artifact["items"][:3]  # drop G04..G10
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "MISSING_GATE_ITEMS" in evaluation.machinery_failures


def test_unknown_item_rejected():
    artifact = _valid_artifact()
    artifact["items"] = artifact["items"] + [_typed_item("G99")]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "UNKNOWN_GATE_ITEM" in evaluation.machinery_failures


def test_duplicate_item_rejected():
    artifact = _valid_artifact()
    artifact["items"] = artifact["items"] + [artifact["items"][0]]
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "DUPLICATE_GATE_ITEM" in evaluation.machinery_failures


def test_item_without_evidence_rejected():
    artifact = _valid_artifact()
    # bypass the model validator the way a forger would: raw dict
    artifact["items"][1]["evidence"] = []
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(f.startswith("GATE_ITEM_NO_EVIDENCE") or f == "ITEMS_NOT_TYPED"
               for f in evaluation.machinery_failures)


# -- 3. Truthy fake trace / probes ----------------------------------------------


def test_truthy_fake_trace_rejected():
    artifact = _valid_artifact(candidate_trace={"stages": 42})
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "INVALID_CANDIDATE_TRACE" in evaluation.machinery_failures


def test_truthy_fake_capability_probes_rejected():
    artifact = _valid_artifact(capability_probes={"run_id": "x", "bogus": 1})
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "INVALID_CAPABILITY_PROBES" in evaluation.machinery_failures


# -- 4. Namespace consistency -----------------------------------------------------


def test_namespace_mismatch_rejected():
    artifact = _valid_artifact(candidate_run_id="run_OTHER")
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "NAMESPACE_MISMATCH" in evaluation.machinery_failures


# -- 5. Evidence-kind semantics ----------------------------------------------------


def test_synthetic_cannot_satisfy_real_evidence_item():
    artifact = _valid_artifact()
    # G01 is a real-evidence item; a synthetic PASS must be rejected.
    artifact["items"][0]["evidence_kind"] = "synthetic_fixture"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "SYNTHETIC_AS_REAL_EVIDENCE" in evaluation.machinery_failures


def test_real_items_accept_real_kind():
    assert REAL_EVIDENCE_ITEMS == {"G01", "G03", "G07"}
    artifact = _valid_artifact()
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "PASS"
    # R5-A: an offline dict without the trusted execution context is
    # structurally valid but never verified=True.
    assert evaluation.verified is False
    assert evaluation.structurally_valid is True


# -- 6. Status strings are never authority -----------------------------------------


def test_status_string_items_never_pass():
    payload = {
        "interface_manifest_schema_hash": _live_hash(),
        "items": {f"G{i:02d}": "PASS" for i in range(1, 11)},
    }
    evaluation = evaluate_gate_artifact(payload)
    assert evaluation.verdict == "FAIL"
    assert "ARTIFACTLESS_PASS" in evaluation.machinery_failures
    assert evaluate_gate_from_artifacts(payload) == "FAIL"


# -- 7. Machinery failure dominates BLOCKED ----------------------------------------


def test_machinery_failure_dominates_blocked_items():
    artifact = _valid_artifact()
    # make G01 honestly BLOCKED ...
    artifact["items"][0].update({
        "status": "BLOCKED", "evidence_kind": "blocked",
        "evidence": [_ev_ref("G01", fold_id="fold_r3a").model_dump(mode="json")],
    })
    # ... but forge the schema hash: the verdict must be FAIL, not BLOCKED.
    artifact["interface_manifest_schema_hash"] = "forged"
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"


# -- 8. Mutation evidence is type-checked -------------------------------------------


def test_escaped_mutation_in_artifact_rejected():
    report = run_p3_gate(run_mutations=False)
    artifact = report.model_dump(mode="json")
    # Keep the full frozen registry, but turn ONE mutation into an escaped
    # (mutated PASS) record — the machinery must reject it.
    artifact["mutations"][0].update({
        "mutated_status": "PASS", "caught": False, "valid": False,
        "invalid_reason": "MUTATION_ESCAPED",
    })
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert any(f.startswith("MUTATION_ESCAPED") for f in evaluation.machinery_failures)


def test_invalid_mutation_records_rejected():
    artifact = _valid_artifact(mutations=[{"mutation_id": "incomplete"}])
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verdict == "FAIL"
    assert "INVALID_MUTATION_RECORDS" in evaluation.machinery_failures


# -- 9. A genuinely validated artifact -----------------------------------------------


def test_genuinely_validated_artifact_passes():
    evaluation = evaluate_gate_artifact(_valid_artifact())
    assert evaluation.verdict == "PASS"
    # R5-A: an offline dict WITHOUT the trusted execution context can be
    # structurally valid but is NEVER verified=True.
    assert evaluation.verified is False
    assert evaluation.structurally_valid is True
    assert evaluation.machinery_failures == []
    assert evaluation.item_statuses == {
        item_id: "PASS" for item_id in REQUIRED_GATE_ITEMS
    }


def test_artifact_verified_against_trusted_context():
    # R6-A: the SAME artifact verified against the opaque GateExecutionAuthority
    # of the run that produced it becomes verified=True.  The runner
    # registered the authority under this run's identity; a public caller
    # cannot construct an authority itself.
    report = run_p3_gate(run_mutations=True)
    artifact = report.model_dump(mode="json")
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.verified is True
    assert evaluation.machinery_failures == []
    assert evaluation.verdict == report.verdict


def test_gate_self_report_is_verified():
    # The gate's own (mutation-free) report must pass the same typed
    # verification a reviewer applies.
    report = run_p3_gate(run_mutations=False)
    artifact = report.model_dump(mode="json")
    evaluation = evaluate_gate_artifact(artifact)
    assert evaluation.machinery_failures == []
    assert evaluation.verdict == report.verdict
    assert report.derived_from_artifacts is True


def test_gate_blocked_items_keep_honest_blocked_verdict():
    report = run_p3_gate(run_mutations=False)
    blocked = [i for i in report.items if i.status == "BLOCKED"]
    assert blocked, "real-evidence items must remain honestly BLOCKED"
    assert report.verdict == "BLOCKED"
