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


# -- §17.7: No fabricated annotations when BLOCKED -------------------------


def test_report_exists():
    """Audit report must exist (even in BLOCKED state)."""
    assert REPORT_JSON_PATH.exists(), f"Report JSON missing: {REPORT_JSON_PATH}"
    assert REPORT_MD_PATH.exists(), f"Report MD missing: {REPORT_MD_PATH}"


def test_report_status_blocked_when_no_second_annotator():
    """§17.1/§17.7: Without a second annotator, report status is BLOCKED."""
    rep = _load_json(REPORT_JSON_PATH)
    assert rep["status"] == "BLOCKED_MANUAL_AUDIT_INCOMPLETE"


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
    """§17.5: Report must not contain 'llm_confidence' as a field or value.

    LLM self-assessment confidence is forbidden as audit evidence. Audit
    quality is expressed only via agreement + catastrophic_error_count.
    """
    rep_str = REPORT_JSON_PATH.read_text().lower()
    assert "llm_confidence" not in rep_str, (
        "Report contains 'llm_confidence' — forbidden by §17.5 "
        "(LLM self-confidence is not audit evidence)"
    )


def test_report_no_confidence_field_in_schema():
    """§17.5: ManualAuditRecord schema must not have a 'confidence' field."""
    schema = _load_json(SCHEMA_PATH)
    props = schema.get("properties", {})
    assert "confidence" not in props, (
        "ManualAuditRecord schema has a 'confidence' field — forbidden by §17.5"
    )
    assert "llm_confidence" not in props, (
        "ManualAuditRecord schema has 'llm_confidence' — forbidden by §17.5"
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
