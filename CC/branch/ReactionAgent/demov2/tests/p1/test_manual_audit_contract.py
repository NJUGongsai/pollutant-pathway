"""P1-T11 Manual audit contract tests.

These tests verify the manual audit protocol, sample manifest, and report
integrity. They are designed to PASS in both states:

- BLOCKED_MANUAL_AUDIT_INCOMPLETE (current): no second independent annotator;
  annotations/adjudication files are NOT produced. Tests verify the blockage
  is transparent and no fake annotations exist (§17.1/§17.7).
- COMPLETE (future, after unblock): double annotation + adjudication produced.
  Tests verify two distinct annotator IDs, adjudication fields, and threshold
  compliance.

Tests use conditional early-return (not pytest.skip) so the suite reports
zero skip in either state.
"""

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS_P1 = REPO_ROOT / "reports" / "p1"
DOCS = REPO_ROOT / "docs"
SCHEMAS_JSON = REPO_ROOT / "schemas" / "json"

PROTOCOL_PATH = DOCS / "manual_audit_protocol.md"
MANIFEST_PATH = REPORTS_P1 / "manual_audit_sample_manifest.json"
REPORT_JSON_PATH = REPORTS_P1 / "manual_audit_report.json"
REPORT_MD_PATH = REPORTS_P1 / "manual_audit_report.md"
ANNOTATIONS_A_PATH = REPORTS_P1 / "manual_audit_annotations_a.json"
ANNOTATIONS_B_PATH = REPORTS_P1 / "manual_audit_annotations_b.json"
ADJUDICATION_PATH = REPORTS_P1 / "manual_audit_adjudication.json"
EVIDENCE_PACKET_PATH = REPORTS_P1 / "manual_audit_evidence_packet.json"
SNAPSHOT_SAMPLE_PATH = REPORTS_P1 / "snapshot_build_sample.json"
REQUIRED_CASE_EVIDENCE_PATH = REPORTS_P1 / "required_case_quarantine_evidence.json"
SCHEMA_PATH = SCHEMAS_JSON / "ManualAuditRecord.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


# -- §17.6: Protocol exists and thresholds are frozen before results --------


def test_protocol_document_exists():
    """§17.6: The protocol document must exist (frozen before results)."""
    assert PROTOCOL_PATH.exists(), f"Protocol document missing: {PROTOCOL_PATH}"


def test_threshold_frozen_before_results():
    """§17.6: Protocol must contain the frozen threshold string.

    The string 'catastrophic errors in production index = 0' is the H1 hard
    condition. Its presence (written BEFORE any results) proves the threshold
    was frozen, not adjusted after seeing results.
    """
    proto = PROTOCOL_PATH.read_text()
    assert "catastrophic errors in production index = 0" in proto


def test_protocol_mtime_precedes_report_mtime():
    """§17.6: Protocol file mtime <= report file mtime (frozen before results).

    The protocol is written first; the report is written after. If the report
    mtime is earlier than the protocol mtime, the threshold was not frozen
    before the results — a violation.
    """
    assert PROTOCOL_PATH.exists(), "Protocol missing"
    assert REPORT_JSON_PATH.exists(), "Report missing"
    proto_mtime = os.path.getmtime(PROTOCOL_PATH)
    report_mtime = os.path.getmtime(REPORT_JSON_PATH)
    assert proto_mtime <= report_mtime + 1.0, (
        "Protocol mtime must precede (or equal) report mtime — "
        f"protocol={proto_mtime}, report={report_mtime}"
    )


def test_protocol_contains_all_hard_conditions():
    """§17.6: Protocol must list all 7 frozen hard conditions H1-H7."""
    proto = PROTOCOL_PATH.read_text()
    for marker in [
        "catastrophic errors in production index = 0",
        "proline-2OG correct or quarantined",
        "critical tie silently selected = 0",
        "quarantine leakage = 0",
        "participant destructive loss = 0",
        "formal",
        "mechanistic",
        "snapshot replay",
        "hash failure",
    ]:
        assert marker.lower() in proto.lower(), (
            f"Protocol missing hard-condition marker: {marker}"
        )


def test_protocol_contains_rubric_and_catastrophic_definitions():
    """§17.3/§17.4: Protocol must define the 11 rubric items and 9 catastrophic errors."""
    proto = PROTOCOL_PATH.read_text()
    # 11 rubric items R1-R11
    for i in range(1, 12):
        assert f"R{i}" in proto, f"Protocol missing rubric item R{i}"
    # 9 catastrophic errors C1-C9
    for i in range(1, 10):
        assert f"C{i}" in proto, f"Protocol missing catastrophic error C{i}"


def test_protocol_forbids_double_annotation_fraud():
    """§17.1: Protocol must forbid single-process duplicate-as-double-annotation."""
    proto = PROTOCOL_PATH.read_text()
    assert "§17.1" in proto or "17.1" in proto
    assert "double" in proto.lower() or "independent" in proto.lower()


# -- §17.2: Sample manifest ------------------------------------------------


def test_sample_manifest_exists():
    """§17.2: Stratified sample manifest must exist."""
    assert MANIFEST_PATH.exists(), f"Sample manifest missing: {MANIFEST_PATH}"


def test_sample_manifest_has_strata():
    """§17.2: Manifest must contain stratification dimensions."""
    manifest = _load_json(MANIFEST_PATH)
    assert "strata" in manifest, "Manifest missing 'strata' field"
    assert "sample_strategy" in manifest, "Manifest missing 'sample_strategy'"
    assert "sample_size" in manifest, "Manifest missing 'sample_size'"


def test_sample_manifest_records_fixture_label():
    """§17.2: Fixture snapshot must be labeled as fixture (not real data)."""
    manifest = _load_json(MANIFEST_PATH)
    assert manifest.get("sample_source") == "fixture_snapshot_t10"
    assert "fixture" in manifest.get("fixture_label", "").lower()


def test_sample_manifest_census_for_small_dataset():
    """§17.2: Small dataset (<=50) uses full census, no random seed."""
    manifest = _load_json(MANIFEST_PATH)
    assert manifest["sample_strategy"] == "census"
    assert manifest["random_seed"] is None
    assert manifest["sample_size"] == manifest["total_records_in_snapshot"]


def test_sample_manifest_items_match_snapshot():
    """§17.2: Manifest items must correspond to T10 snapshot records."""
    manifest = _load_json(MANIFEST_PATH)
    items = manifest["items"]
    assert len(items) == 4, f"Expected 4 census items, got {len(items)}"
    lanes = {item["lane_expected"] for item in items}
    assert lanes == {"strict", "conditional", "diagnostic", "quarantine"}
    expected_rubrics = {f"R{i}" for i in range(1, 12)}
    assert all(
        set(item["rubric_items_applicable"]) == expected_rubrics
        for item in items
    )


def test_sample_manifest_identity_matches_rebuilt_snapshot_authority():
    """The sample cannot name a stale snapshot ID/hash from an older fixture."""
    manifest = _load_json(MANIFEST_PATH)
    packet = _load_json(EVIDENCE_PACKET_PATH)
    snapshot_sample = _load_json(SNAPSHOT_SAMPLE_PATH)["fixture_snapshot"]
    authorities = [
        (manifest["snapshot_id"], manifest["snapshot_hash"]),
        (
            packet["snapshot_manifest"]["snapshot_id"],
            packet["snapshot_manifest"]["snapshot_hash"],
        ),
        (
            snapshot_sample["on_disk_manifest"]["snapshot_id"],
            snapshot_sample["on_disk_manifest"]["snapshot_hash"],
        ),
        (
            snapshot_sample["loaded_record"]["snapshot_id"],
            snapshot_sample["loaded_record"]["snapshot_hash"],
        ),
    ]
    assert len(set(authorities)) == 1, f"snapshot identity authorities disagree: {authorities}"


def test_sample_manifest_strata_are_serialized_facts_not_intended_chemistry():
    """Round-1 false multi-reactant/cofactor labels must not recur."""
    manifest = _load_json(MANIFEST_PATH)
    packet = _load_json(EVIDENCE_PACKET_PATH)
    records = {
        record["reaction_evidence"]["reaction_id"]: record
        for record in packet["records"]
    }
    for item in manifest["items"]:
        record = records[item["reaction_id"]]
        labels = item["stratum_labels"]
        participants = record["reaction_evidence"]["participants"]
        reactants = sum(p["side"] == "reactant" for p in participants)
        products = sum(p["side"] == "product" for p in participants)
        assert labels["participant_count"] == f"reactants_{reactants}_products_{products}"
        roles = {
            assignment["role"]
            for assignment in record["source_ledger"]["role_assignments"]
        }
        expected_cofactor = (
            "with_explicit_cofactor_role"
            if "cofactor" in roles else "no_explicit_cofactor_role"
        )
        assert labels["cofactor_pattern"] == expected_cofactor
        assert labels["mapping_quality"] == record["reaction_evidence"]["mapping_report"]["mapping_status"]
        assert labels["eligibility_lane"] == record["lane"]
    assert manifest["strata"]["by_participant_count"] == {"reactants_1_products_1": 4}
    assert manifest["strata"]["by_cofactor_pattern"] == {"no_explicit_cofactor_role": 4}


def test_snapshot_replay_evidence_is_two_builds_plus_hash_and_loader():
    """H7 requires observed replay evidence, not a same-hash assertion alone."""
    packet = _load_json(EVIDENCE_PACKET_PATH)
    replay = packet["snapshot_replay_evidence"]
    assert replay["input_a_order"] == "forward"
    assert replay["input_b_order"] == "reverse"
    assert replay["build_a"]["loader_accepted"] is True
    assert replay["build_b"]["loader_accepted"] is True
    assert replay["same_hash_across_hash_build_load"] is True
    assert replay["same_snapshot_id_across_build_load"] is True
    assert replay["record_content_hashes_equal"] is True
    hashes = {
        replay["hash_only_no_write"],
        replay["build_a"]["snapshot_hash"],
        replay["build_a"]["loaded_snapshot_hash"],
        replay["build_b"]["snapshot_hash"],
        replay["build_b"]["loaded_snapshot_hash"],
    }
    assert hashes == {packet["snapshot_manifest"]["snapshot_hash"]}


def test_real_required_case_evidence_is_explicit_quarantine_not_claimed_resolution():
    """H2 passes through honest quarantine until validated lineage exists."""
    evidence = _load_json(REQUIRED_CASE_EVIDENCE_PATH)
    assert evidence["case_count"] == 3
    assert evidence["quarantined_count"] == 3
    assert evidence["production_eligible_count"] == 0
    assert evidence["forbidden_lineage_present_count"] == 0
    assert evidence["resolved_lineage_count"] == 0
    for case in evidence["cases"]:
        mapping = case["formal_mapping_summary"]
        disposition = case["new_pipeline_disposition"]
        assert mapping["fallback_method"] == "mcs"
        assert mapping["mechanistic_atom_origin"] is None
        assert disposition["disposition"] == "quarantined"
        assert disposition["production_eligible"] is False
        assert disposition["resolved_lineages"] == []
        assert disposition["quarantine_record"]["source_record_id"] == case["source_id"]


# -- §17.7: No fabricated annotations when BLOCKED -------------------------


def test_report_exists():
    """Audit report must exist (even in BLOCKED state)."""
    assert REPORT_JSON_PATH.exists(), f"Report JSON missing: {REPORT_JSON_PATH}"
    assert REPORT_MD_PATH.exists(), f"Report MD missing: {REPORT_MD_PATH}"


def test_report_status_matches_annotation_lifecycle():
    """§17.1/§17.7: report is either honestly BLOCKED or independently COMPLETE."""
    rep = _load_json(REPORT_JSON_PATH)
    assert rep["status"] in {
        "BLOCKED_MANUAL_AUDIT_INCOMPLETE",
        "COMPLETE",
    }
    if rep["status"] == "COMPLETE":
        assert rep["annotator_a_status"] == "COMPLETE"
        assert rep["annotator_b_status"] == "COMPLETE"
        assert rep["adjudication_status"] == "COMPLETE"


def test_no_fake_annotations_when_blocked():
    """§17.7: When BLOCKED, annotations_a/b.json must NOT exist with fake content.

    If the files exist at all (future placeholder), they must declare
    BLOCKED status and have an empty annotations list — never fabricated
    annotation data.
    """
    rep = _load_json(REPORT_JSON_PATH)
    if rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE":
        # In BLOCKED state, annotation files should not exist.
        # If they exist as placeholders, they must be empty + labeled BLOCKED.
        for path in [ANNOTATIONS_A_PATH, ANNOTATIONS_B_PATH]:
            if path.exists():
                data = _load_json(path)
                assert data.get("status") == "BLOCKED_MANUAL_AUDIT_INCOMPLETE", (
                    f"{path.name} exists but is not labeled BLOCKED — "
                    "possible fabricated annotation (§17.1/§17.7)"
                )
                assert data.get("annotations", []) == [], (
                    f"{path.name} has non-empty annotations in BLOCKED state — "
                    "possible fabricated annotation (§17.7)"
                )
            else:
                # File absent — correct behavior when BLOCKED.
                pass
    else:
        # COMPLETE state: both annotation files must exist with real content.
        assert ANNOTATIONS_A_PATH.exists(), "Annotator A file missing in COMPLETE state"
        assert ANNOTATIONS_B_PATH.exists(), "Annotator B file missing in COMPLETE state"


def test_no_fake_adjudication_when_blocked():
    """§17.7: When BLOCKED, adjudication.json must NOT exist with fake content."""
    rep = _load_json(REPORT_JSON_PATH)
    if rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE":
        if ADJUDICATION_PATH.exists():
            data = _load_json(ADJUDICATION_PATH)
            assert data.get("status") == "BLOCKED_MANUAL_AUDIT_INCOMPLETE", (
                "adjudication.json exists but is not labeled BLOCKED — "
                "possible fabricated adjudication (§17.7)"
            )
    else:
        assert ADJUDICATION_PATH.exists(), "Adjudication file missing in COMPLETE state"


# -- §17.5: No LLM self-confidence as audit confidence --------------------


def test_no_llm_self_confidence_as_audit():
    """§17.5: Report must not contain any forbidden confidence vocabulary.

    The audit report JSON string is scanned for the full forbidden-word list
    ["llm_confidence", "self_confidence", "confidence"]. LLM self-assessment
    confidence is forbidden as audit evidence. Audit quality is expressed only
    via agreement + catastrophic_error_count.

    A full-string scan (not just a field-name check) catches disguised
    variants like `llm_self_confidence_present` that the narrower
    `llm_confidence` substring check would miss (the `self_` infix breaks
    the match).
    """
    rep_str = REPORT_JSON_PATH.read_text().lower()
    forbidden = ["llm_confidence", "self_confidence", "confidence"]
    for word in forbidden:
        assert word not in rep_str, (
            f"Report contains '{word}' — forbidden by §17.5 "
            f"(LLM self-confidence is not audit evidence; "
            f"audit quality is via agreement + catastrophic_error_count only)"
        )


def test_report_no_confidence_field_in_schema():
    """§17.5: ManualAuditRecord schema must not have a confidence-typed field."""
    schema = _load_json(SCHEMA_PATH)
    props = schema.get("properties", {})
    forbidden_props = ["confidence", "llm_confidence", "self_confidence"]
    for word in forbidden_props:
        assert word not in props, (
            f"ManualAuditRecord schema has a '{word}' field — "
            f"forbidden by §17.5"
        )


# -- Catastrophic error reporting ------------------------------------------


def test_catastrophic_errors_reported():
    """Report must contain catastrophic_error_count field.

    In BLOCKED state, the value is null (cannot be determined without double
    annotation). In COMPLETE state, it is an integer >= 0.
    """
    rep = _load_json(REPORT_JSON_PATH)
    assert "catastrophic_error_count" in rep, (
        "Report missing 'catastrophic_error_count' field"
    )


def test_catastrophic_error_count_null_when_blocked():
    """When BLOCKED, catastrophic_error_count is null (not zero, not fabricated)."""
    rep = _load_json(REPORT_JSON_PATH)
    if rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE":
        assert rep["catastrophic_error_count"] is None, (
            "BLOCKED report must have catastrophic_error_count=null "
            "(cannot be determined without double annotation)"
        )


def test_pass_status_false_when_blocked():
    """BLOCKED audit cannot pass."""
    rep = _load_json(REPORT_JSON_PATH)
    if rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE":
        assert rep["pass_status"] is False, (
            "BLOCKED audit must have pass_status=false"
        )


# -- §17.1: Double annotator independence (verified when COMPLETE) ---------


def test_two_distinct_annotator_ids_when_complete():
    """§17.1: When annotations exist (COMPLETE state), annotator IDs must differ.

    In BLOCKED state, no annotation files exist → test PASSES (no violation
    possible). In COMPLETE state, annotator A and B must have distinct IDs.
    """
    rep = _load_json(REPORT_JSON_PATH)
    if rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE":
        # No annotations in BLOCKED state — nothing to check, no violation.
        return
    a = _load_json(ANNOTATIONS_A_PATH)
    b = _load_json(ANNOTATIONS_B_PATH)
    assert a["annotator_id"] != b["annotator_id"], (
        "§17.1 violation: annotator A and B have the same ID — "
        "single process duplicating answers as double annotation"
    )


def test_annotations_not_identical_copies_when_complete():
    """§17.1: When COMPLETE, annotations A and B must not be identical copies.

    Identical content (despite different IDs) would indicate a single process
    copied its output into both files.
    """
    rep = _load_json(REPORT_JSON_PATH)
    if rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE":
        return
    a = _load_json(ANNOTATIONS_A_PATH)
    b = _load_json(ANNOTATIONS_B_PATH)
    # Compare the annotation payloads (excluding annotator_id and timestamp).
    a_payload = {k: v for k, v in a.items() if k not in ("annotator_id", "annotated_at")}
    b_payload = {k: v for k, v in b.items() if k not in ("annotator_id", "annotated_at")}
    assert a_payload != b_payload, (
        "§17.1 violation: annotations A and B are identical copies — "
        "single process duplicated its answers"
    )


# -- Adjudication contract (verified when COMPLETE) ------------------------


def test_adjudication_present_when_complete():
    """§17.6: When COMPLETE, adjudication must contain required fields.

    In BLOCKED state, no adjudication file exists → test PASSES.
    """
    rep = _load_json(REPORT_JSON_PATH)
    if rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE":
        return
    assert ADJUDICATION_PATH.exists(), "Adjudication file missing in COMPLETE state"
    adj = _load_json(ADJUDICATION_PATH)
    assert "disagreement_count" in adj, "Adjudication missing 'disagreement_count'"
    assert "outcomes" in adj, "Adjudication missing 'outcomes'"


def test_complete_annotations_cover_every_sample_and_rubric():
    """COMPLETE requires a 4x11 double annotation, not status-only promotion."""
    rep = _load_json(REPORT_JSON_PATH)
    if rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE":
        return
    manifest = _load_json(MANIFEST_PATH)
    expected_samples = {item["sample_id"] for item in manifest["items"]}
    applicable = {
        item["sample_id"]: set(item["rubric_items_applicable"])
        for item in manifest["items"]
    }
    expected_rubrics = {f"R{i}" for i in range(1, 12)}
    for path in (ANNOTATIONS_A_PATH, ANNOTATIONS_B_PATH):
        data = _load_json(path)
        assert data["status"] == "COMPLETE"
        annotations = data["annotations"]
        assert {item["sample_id"] for item in annotations} == expected_samples
        for item in annotations:
            assert set(item["rubrics"]) == expected_rubrics
            for rubric_id, judgment in item["rubrics"].items():
                assert judgment["verdict"] in {"pass", "fail", "not_applicable"}
                if rubric_id in applicable[item["sample_id"]]:
                    assert judgment["verdict"] in {"pass", "fail"}, (
                        f"{item['sample_id']}:{rubric_id} is frozen applicable"
                    )
                else:
                    assert judgment["verdict"] == "not_applicable"
                assert judgment["reason"]
                assert judgment["evidence_pointer"]


def test_complete_annotations_cover_catastrophic_error_vocabulary():
    """Every COMPLETE sample must explicitly evaluate C1-C9."""
    rep = _load_json(REPORT_JSON_PATH)
    if rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE":
        return
    expected = {f"C{i}" for i in range(1, 10)}
    for path in (ANNOTATIONS_A_PATH, ANNOTATIONS_B_PATH):
        for item in _load_json(path)["annotations"]:
            errors = item["catastrophic_errors"]
            assert set(errors) == expected
            assert all(
                isinstance(entry["observed"], bool) for entry in errors.values()
            )


def test_complete_annotation_provenance_is_blinded_and_packet_bound():
    """Independent files must declare blindness and bind the sealed packet hash."""
    rep = _load_json(REPORT_JSON_PATH)
    if rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE":
        return
    import hashlib

    packet = REPORTS_P1 / "manual_audit_evidence_packet.json"
    expected_hash = hashlib.sha256(packet.read_bytes()).hexdigest()
    for path in (ANNOTATIONS_A_PATH, ANNOTATIONS_B_PATH):
        data = _load_json(path)
        assert data["evidence_packet_sha256"] == expected_hash
        assert data["independence"]["blinded_to_peer"] is True
        assert data["independence"]["peer_output_read"] is False


def test_complete_report_satisfies_every_frozen_gate():
    """COMPLETE is insufficient: the frozen H1-H7 and Q1-Q4 must pass."""
    rep = _load_json(REPORT_JSON_PATH)
    if rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE":
        return
    assert rep["pass_status"] is True
    assert rep["agreement"] >= 0.90
    assert rep["catastrophic_error_count"] == 0
    assert rep["all_disagreements_resolved"] is True
    for field in (
        "mapping_rubric_score",
        "role_rubric_score",
        "lineage_rubric_score",
        "ledger_rubric_score",
    ):
        assert rep[field] >= 0.80, f"{field} below frozen threshold"
    assert set(rep["hard_condition_results"]) == {f"H{i}" for i in range(1, 8)}
    assert all(
        judgment["verdict"] == "pass"
        for judgment in rep["hard_condition_results"].values()
    )
    assert set(rep["quality_gate_results"]) == {
        "Q1_raw_agreement_ge_0_90",
        "Q2_catastrophic_error_count_zero",
        "Q3_all_domain_scores_ge_0_80",
        "Q4_all_disagreements_resolved",
    }
    assert all(rep["quality_gate_results"].values())


def test_complete_report_is_bound_to_current_sealed_packet():
    rep = _load_json(REPORT_JSON_PATH)
    if rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE":
        return
    import hashlib

    assert rep["evidence_packet_sha256"] == hashlib.sha256(
        EVIDENCE_PACKET_PATH.read_bytes()
    ).hexdigest()


def test_round_one_failure_archive_is_preserved():
    """Remediation must not rewrite the first independent FAIL into a PASS."""
    archive = REPORTS_P1 / "g10_round_1"
    for name in (
        "annotator_a.json",
        "annotator_b.json",
        "adjudication.json",
        "adjudication_packet.json",
    ):
        assert (archive / name).is_file(), f"Round-1 archive missing {name}"
    assert _load_json(archive / "adjudication.json")["audit_recommendation"] == "FAIL"


def test_complete_round_three_report_preserves_all_prior_failures():
    rep = _load_json(REPORT_JSON_PATH)
    if rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE":
        return
    if rep.get("audit_round", 0) < 3:
        return
    assert rep["prior_rounds"] == [
        {"round": 1, "status": "FAIL", "archive": "reports/p1/g10_round_1/"},
        {"round": 2, "status": "FAIL", "archive": "reports/p1/g10_round_2/"},
    ]
    assert _load_json(REPORTS_P1 / "g10_round_2" / "manual_audit_report.json")["pass_status"] is False


# -- Schema export ---------------------------------------------------------


def test_manual_audit_record_schema_exists():
    """T2 ManualAuditRecord JSON schema must be exported."""
    assert SCHEMA_PATH.exists(), f"Schema missing: {SCHEMA_PATH}"


def test_manual_audit_record_schema_valid_structure():
    """Exported schema must be a valid JSON Schema object."""
    schema = _load_json(SCHEMA_PATH)
    assert schema["type"] == "object"
    assert "properties" in schema
    props = schema["properties"]
    # Core fields from T2 ManualAuditRecord
    for field in [
        "record_id",
        "stratum",
        "sample_size",
        "annotator_count",
        "agreement",
        "disagreement_count",
        "catastrophic_error_count",
        "mapping_rubric_score",
        "role_rubric_score",
        "lineage_rubric_score",
        "ledger_rubric_score",
        "pass_threshold",
        "pass_status",
    ]:
        assert field in props, f"Schema missing field: {field}"


def test_schema_annotator_count_defaults_to_two():
    """T2 contract: annotator_count defaults to 2 (double annotation)."""
    schema = _load_json(SCHEMA_PATH)
    assert schema["properties"]["annotator_count"]["default"] == 2


# -- Report JSON / MD consistency ------------------------------------------


def test_report_json_md_status_consistent():
    """Report JSON and MD must report the same status."""
    rep_json = _load_json(REPORT_JSON_PATH)
    rep_md = REPORT_MD_PATH.read_text()
    assert rep_json["status"] in rep_md, (
        f"Report MD does not mention status '{rep_json['status']}'"
    )
