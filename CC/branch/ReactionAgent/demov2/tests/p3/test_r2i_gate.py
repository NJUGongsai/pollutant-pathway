"""R2-I Gate + mutation evidence chain tests."""
from reaction_agent.p3.gate import (
    evaluate_gate_from_artifacts,
    exit_code_for,
    run_p3_gate,
)


def test_artifactless_pass_dictionary_rejected():
    # A bare {"status":"PASS","items":{...}} dict has NO typed artifacts.
    forged = {
        "status": "PASS",
        "items": {f"G{i:02d}": "PASS" for i in range(1, 11)},
    }
    assert evaluate_gate_from_artifacts(forged) != "PASS"


def test_artifactless_pass_no_attacker_flag_needed():
    # No "no_artifacts" flag is required — absence of artifacts is enough.
    forged = {"status": "PASS", "items": {"G01": "PASS"}}
    assert evaluate_gate_from_artifacts(forged) != "PASS"


def test_gate_recomputes_artifact_hashes():
    # The gate runs the kernel and derives the verdict from executed artifacts.
    report = run_p3_gate(run_mutations=True)
    assert report.derived_from_artifacts is True
    for item in report.items:
        assert item.evidence, f"gate item {item.item_id} lacks artifact evidence"


def test_gate_rejects_schema_invalid_artifact():
    forged = {"status": "PASS", "items": {"G01": "PASS"}, "bogus_artifact": "x"}
    # even with an extra key, no verifiable schema hash / namespace -> non-PASS
    assert evaluate_gate_from_artifacts(forged) != "PASS"


def test_gate_rejects_namespace_mismatch():
    # An artifact dict with a namespace mismatch in its evidence must not pass.
    forged = {
        "status": "PASS",
        "items": {"G01": "PASS", "G02": "PASS"},
        "run_id": "run_A",
        "candidate_run_id": "run_B",  # mismatch
        "schema_hash": "h",
    }
    assert evaluate_gate_from_artifacts(forged) != "PASS"


def test_gate_rejects_fixture_as_real_evidence():
    from reaction_agent.p3.gate import GateItemResult, make_evidence_reference
    from reaction_agent.p3.schemas import EvidenceKind
    # A fixture-only gate item must never satisfy a real-evidence item.
    item = GateItemResult(
        item_id="G01", title="real end-to-end",
        status="BLOCKED",  # fixture cannot satisfy a real-evidence gate
        evidence=[make_evidence_reference(
            artifact_type="capability_probe", artifact_id="cap_real",
            content={"gate_check": "real_evidence", "real_snapshot_available": False},
            run_id="p3_gate", fold_id="fold_fx_p3",
        )],
        evidence_kind=EvidenceKind.blocked,
    )
    assert item.status == "BLOCKED"
    assert item.evidence_kind is EvidenceKind.blocked


def test_mutation_requires_pass_baseline():
    report = run_p3_gate(run_mutations=True)
    for mutation in report.mutations:
        assert mutation.baseline_status == "PASS", (
            f"mutation {mutation.mutation_id} has invalid baseline"
        )


def test_mutation_requires_target_pass_to_fail():
    report = run_p3_gate(run_mutations=True)
    for mutation in report.mutations:
        # every registered mutation targets a real gate item
        item_ids = {i.item_id for i in report.items}
        assert mutation.target_gate_item in item_ids, (
            f"mutation {mutation.mutation_id} targets unknown item "
            f"{mutation.target_gate_item}"
        )


def test_mutation_requires_expected_failure_code():
    report = run_p3_gate(run_mutations=True)
    for mutation in report.mutations:
        assert mutation.expected_failure_code
        assert mutation.observed_failure_code


def test_mutation_escape_causes_gate_fail_even_when_real_items_blocked():
    # If a mutation escapes (not caught), the gate must NOT be PASS even
    # though real-evidence items are BLOCKED.
    report = run_p3_gate(run_mutations=True)
    assert all(m.caught for m in report.mutations), "no mutation may escape"
    # When real items are BLOCKED the verdict is BLOCKED (honest), never PASS.
    assert report.verdict == "BLOCKED"


def test_exit_codes_distinct():
    assert exit_code_for("PASS") == 0
    assert exit_code_for("FAIL") == 1
    assert exit_code_for("BLOCKED") == 2
