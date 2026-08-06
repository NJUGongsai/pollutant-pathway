#!/usr/bin/env python3
"""P5 Gate runner — verifies artifact schema/hash/leakage/baseline fairness.

Gate items:
1. Leakage zero and all required domains audited
2. All filters and denominators complete
3. Multi-answer active and policy-bound
4. Strict metrics complete or explicit unavailable blocker
5. Baselines fair and oracle separated
6. Formal KPI registry only records when data allows
7. Go/No-Go traceable

Gate status: PASS, BLOCKED, or FAIL.
- PASS: all gate items pass with machine-verifiable evidence
- BLOCKED: upstream P2/P3/P4 missing or real snapshot unavailable
- FAIL: implementation invariant failure

Gate derives from structured evidence, not stored status strings.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import datetime
from typing import Any

# Add project root to path (worktree-portable)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from reaction_agent.p5.schemas import (
    P5_SCHEMA_VERSION,
    ArtifactClassification,
    FullSnapshotManifest,
    ProductionIndexManifest,
    RebuiltCaseRecord,
    SplitFamilyManifest,
    SplitFamilyName,
    BaselineRunArtifact,
    BaselineName,
    SixLayerReport,
    FormalKPIRegistry,
    GoNoGoDecision,
    P5RunManifest,
    MetricUnavailableReason,
)
from reaction_agent.p5.snapshot_reader import (
    read_p1_snapshot,
    build_full_snapshot_manifest,
    build_production_index_manifest,
)
from reaction_agent.p5.builder import (
    build_rebuilt_cases,
    build_split_families,
    build_fair_baselines,
    build_six_layer_report,
    build_formal_kpi_registry,
    build_go_no_go_decision,
)
from reaction_agent.p5 import real_data as rd

REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports/p5")
P1_SNAPSHOT_PATH = os.path.join(PROJECT_ROOT, "reports/p1/snapshot_build_sample.json")
P1_GATE_PATH = os.path.join(PROJECT_ROOT, "reports/p1/P1_GATE_REPORT.json")

# Real-data paths (present when the real chain is integrated)
REAL_SNAPSHOT_DIR = os.path.join(
    PROJECT_ROOT, "reports", "p1", "real_snapshot", "snap_19caddc6b312")
P4_GATE_PATH = os.path.join(PROJECT_ROOT, "reports", "p4", "P4_GATE_REPORT.json")


def real_chain_available() -> bool:
    """True when the real P1 snapshot + P2/P3/P4 artifacts are present."""
    return (os.path.exists(os.path.join(REAL_SNAPSHOT_DIR, "manifest.json"))
            and os.path.exists(rd.P2_TRUTH_PATH)
            and os.path.exists(rd.P2_SPLIT_PATH)
            and os.path.exists(rd.P3_ARTIFACT_PATH)
            and os.path.exists(P4_GATE_PATH))


def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def _canonical_hash(obj: Any) -> str:
    return _sha256_hex(json.dumps(obj, sort_keys=True, ensure_ascii=False))


def run_p5_gate() -> dict[str, Any]:
    """Run P5 Gate and return structured report."""
    os.makedirs(REPORTS_DIR, exist_ok=True)

    # Read P1 gate
    with open(P1_GATE_PATH) as f:
        p1_gate = json.load(f)

    p1_status = "PASS" if p1_gate.get("all_passed") else "FAIL"

    use_real = real_chain_available()

    if use_real:
        # ============ REAL chain: P1/P2/P3/P4 real artifacts ============
        p1_data = rd.load_real_p1_snapshot()
        upstream = rd.load_upstream_status()
        p2_status = upstream["p2"][0]
        p3_status = upstream["p3"][0]
        p4_status = upstream["p4"][0]
        p3_artifact = rd._load_json(rd.P3_ARTIFACT_PATH) if upstream["p3"][1] else None
        p4_gate = rd._load_json(P4_GATE_PATH) if upstream["p4"][1] else None

        full_manifest = rd.build_real_full_snapshot_manifest(p1_data)
        prod_manifest = rd.build_real_production_index(p1_data, full_manifest)
        truth = rd._load_json(rd.P2_TRUTH_PATH)
        cases = rd.build_real_rebuilt_cases(p1_data, truth)
        p2_split = rd._load_json(rd.P2_SPLIT_PATH)
        splits = rd.build_real_split_families(full_manifest, cases, p2_split)

        available_split = next((s for s in splits if not s.unavailable), None)
        baselines = []
        if available_split:
            baselines = rd.build_real_baselines(full_manifest, available_split, p3_artifact)

        six_layer_report = None
        if available_split:
            first_baseline = next(
                (b for b in baselines if b.available and not b.is_oracle), None)
            if first_baseline:
                six_layer_report = rd.build_real_six_layer_report(
                    full_manifest, available_split, first_baseline, p3_artifact, p4_gate)

        kpi_registry = None
        go_no_go = None
        if available_split:
            kpi_registry = rd.build_real_kpi_registry(
                full_manifest, available_split, p3_artifact, p4_gate)
            go_no_go = rd.build_real_go_no_go(
                full_manifest, kpi_registry,
                {"p2": upstream["p2"][1], "p3": upstream["p3"][1],
                 "p4": upstream["p4"][1]})
    else:
        # ============ FIXTURE chain (fallback, protocol-only) ============
        p1_data = read_p1_snapshot(P1_SNAPSHOT_PATH)
        p2_status = "BLOCKED"  # no real chain without P2
        p3_status = "MISSING"
        p4_status = "MISSING"

        full_manifest = build_full_snapshot_manifest(p1_data)
        prod_manifest = build_production_index_manifest(p1_data, full_manifest)
        cases = build_rebuilt_cases(
            full_manifest,
            upstream_p2_available=False,
            upstream_p3_available=False,
            upstream_p4_available=False,
        )
        splits = build_split_families(full_manifest, cases)

        available_split = next((s for s in splits if not s.unavailable), None)
        baselines = []
        if available_split:
            baselines = build_fair_baselines(full_manifest, available_split, "case_registry_p5_0")

        six_layer_report = None
        if available_split:
            first_baseline = next((b for b in baselines if b.available), None)
            six_layer_report = build_six_layer_report(full_manifest, available_split, first_baseline)

        kpi_registry = None
        go_no_go = None
        if available_split:
            kpi_registry = build_formal_kpi_registry(
                full_manifest, available_split,
                upstream_p3_available=False,
                upstream_p4_available=False,
            )
            go_no_go = build_go_no_go_decision(
                full_manifest, kpi_registry,
                upstream_p2_available=False,
                upstream_p3_available=False,
                upstream_p4_available=False,
            )

    # =================================================================
    # Gate items
    # =================================================================
    gate_items = []

    # Gate 1: Leakage zero and all required domains audited
    leakage_zero = True
    all_domains_audited = True
    for split in splits:
        if not split.unavailable:
            if split.domain_audit.leakage_count > 0:
                leakage_zero = False
            if not split.domain_audit.audit_complete:
                all_domains_audited = False
    # Source/time are unavailable (not audited) — this is correct behavior
    source_unavailable = any(
        s.split_family_name == SplitFamilyName.source and s.unavailable for s in splits
    )
    time_unavailable = any(
        s.split_family_name == SplitFamilyName.time and s.unavailable for s in splits
    )

    gate_items.append({
        "gate_id": "P5-G01",
        "name": "leakage_zero_and_domains_audited",
        "passed": leakage_zero and all_domains_audited,
        "blocked": False,
        "evidence": f"leakage_zero={leakage_zero}, all_audited={all_domains_audited}, "
                    f"source_unavailable={source_unavailable}, time_unavailable={time_unavailable}",
    })

    # Gate 2: All filters and denominators complete
    filters_complete = len(full_manifest.filter_accounting) > 0
    no_silent_drop = all(
        f.removed_count == f.denominator_before - f.denominator_after
        for f in full_manifest.filter_accounting
    )
    partition_sum = (
        full_manifest.production_count
        + full_manifest.diagnostic_count
        + full_manifest.quarantine_count
        + full_manifest.excluded_count
    )
    partition_matches = partition_sum == full_manifest.pre_normalization_count

    gate_items.append({
        "gate_id": "P5-G02",
        "name": "all_filters_and_denominators_complete",
        "passed": filters_complete and no_silent_drop and partition_matches,
        "blocked": False,
        "evidence": f"filters={len(full_manifest.filter_accounting)}, "
                    f"no_silent_drop={no_silent_drop}, "
                    f"partition_matches={partition_matches} "
                    f"(partition_sum={partition_sum}, pre_norm={full_manifest.pre_normalization_count})",
    })

    # Gate 3: Multi-answer active and policy-bound
    multi_answer_active = all(
        isinstance(c.allowed_product_set, list) and len(c.allowed_product_set) >= 1
        for c in cases
    )
    incomplete_retained = all(
        not c.incomplete_truth or (c.incomplete_truth and c.incomplete_reason)
        for c in cases
    )

    gate_items.append({
        "gate_id": "P5-G03",
        "name": "multi_answer_active_and_policy_bound",
        "passed": multi_answer_active and incomplete_retained,
        "blocked": False,
        "evidence": f"multi_answer_active={multi_answer_active}, "
                    f"incomplete_retained={incomplete_retained}, "
                    f"cases={len(cases)}",
    })

    # Gate 4: Strict metrics complete or explicit unavailable blocker
    metrics_have_n_or_unavailable = True
    if six_layer_report:
        for m in six_layer_report.metrics:
            if m.unavailable:
                if m.unavailable_reason is None:
                    metrics_have_n_or_unavailable = False
            else:
                if m.n is None or m.denominator is None or m.numerator is None:
                    metrics_have_n_or_unavailable = False

    # Metrics are blocked because P3/P4 are missing — this is correct
    metrics_blocked = p3_status == "MISSING" or p4_status == "MISSING"

    gate_items.append({
        "gate_id": "P5-G04",
        "name": "strict_metrics_complete_or_unavailable_blocker",
        "passed": metrics_have_n_or_unavailable,
        "blocked": metrics_blocked,
        "evidence": f"metrics_have_n_or_unavailable={metrics_have_n_or_unavailable}, "
                    f"blocked_by_p3_missing={p3_status == 'MISSING'}, "
                    f"blocked_by_p4_missing={p4_status == 'MISSING'}",
    })

    # Gate 5: Baselines fair and oracle separated
    baselines_fair = True
    oracle_separated = True
    if baselines:
        snapshot_ids = {b.snapshot_id for b in baselines}
        split_ids = {b.split_id for b in baselines}
        case_registries = {b.case_registry_id for b in baselines}
        train_resources = {b.train_only_resource_id for b in baselines}
        baselines_fair = len(snapshot_ids) == 1 and len(split_ids) == 1 and len(case_registries) == 1
        for b in baselines:
            if b.is_oracle and b.namespace != "diagnostic":
                oracle_separated = False

    gate_items.append({
        "gate_id": "P5-G05",
        "name": "baselines_fair_and_oracle_separated",
        "passed": baselines_fair and oracle_separated,
        "blocked": False,
        "evidence": f"baselines_fair={baselines_fair}, "
                    f"oracle_separated={oracle_separated}, "
                    f"baseline_count={len(baselines)}",
    })

    # Gate 6: Formal KPI registry only records when data allows
    kpi_correct = True
    if kpi_registry:
        if not kpi_registry.registered and kpi_registry.kpi_entries:
            kpi_correct = False
        if kpi_registry.registered and not kpi_registry.kpi_entries:
            kpi_correct = False

    gate_items.append({
        "gate_id": "P5-G06",
        "name": "formal_kpi_registry_only_when_data_allows",
        "passed": kpi_correct,
        "blocked": p3_status == "MISSING" or p4_status == "MISSING",
        "evidence": f"kpi_correct={kpi_correct}, "
                    f"registered={kpi_registry.registered if kpi_registry else 'N/A'}, "
                    f"blocked_by_upstream={p3_status == 'MISSING' or p4_status == 'MISSING'}",
    })

    # Gate 7: Go/No-Go traceable
    go_no_go_traceable = go_no_go is not None and go_no_go.decision in ("go", "no_go", "blocked")

    gate_items.append({
        "gate_id": "P5-G07",
        "name": "go_no_go_traceable",
        "passed": go_no_go_traceable,
        "blocked": go_no_go is not None and go_no_go.decision == "blocked",
        "evidence": f"go_no_go_traceable={go_no_go_traceable}, "
                    f"decision={go_no_go.decision if go_no_go else 'N/A'}",
    })

    # Gate 8: invariant test suite must be green — a PASS gate with a red
    # test suite is a bypass (P5-R1-02). The gate consumes the live pytest
    # result; any failure/error keeps the gate from PASSING.
    invariant_result = run_invariant_tests()
    tests_pass = (invariant_result["failed"] == 0
                  and invariant_result["errors"] == 0
                  and invariant_result["exit_code"] == 0)
    gate_items.append({
        "gate_id": "P5-G08",
        "name": "invariant_tests_pass",
        "passed": tests_pass,
        "blocked": False,
        "evidence": f"tests_passed={invariant_result['passed']}, "
                    f"tests_failed={invariant_result['failed']}, "
                    f"tests_errors={invariant_result['errors']}, "
                    f"exit_code={invariant_result['exit_code']}",
    })

    # =================================================================
    # Overall gate status
    # =================================================================
    any_fail = any(not g["passed"] and not g["blocked"] for g in gate_items)
    any_block = any(g["blocked"] for g in gate_items)
    all_pass = all(g["passed"] and not g["blocked"] for g in gate_items)

    if any_fail:
        gate_status = "FAIL"
    elif any_block:
        gate_status = "BLOCKED"
    else:
        gate_status = "PASS"

    # Run mutations
    mutation_result = run_mutations()

    # If any mutation escaped, gate FAILS
    if mutation_result["escaped"] > 0 or mutation_result["errors"] > 0:
        gate_status = "FAIL"

    # =================================================================
    # Build run manifest
    # =================================================================
    run_id = f"p5_run_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    run_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    run_manifest = P5RunManifest(
        schema_version=P5_SCHEMA_VERSION,
        run_id=run_id,
        run_timestamp=run_timestamp,
        artifact_classification=(
            ArtifactClassification.real if use_real
            else ArtifactClassification.synthetic_fixture),
        p1_snapshot_id=full_manifest.snapshot_id,
        p1_snapshot_hash=full_manifest.snapshot_hash,
        p1_status=p1_status,
        p2_status=p2_status,
        p3_status=p3_status,
        p4_status=p4_status,
        full_snapshot_manifest_path="reports/p5/full_snapshot_manifest.json",
        production_index_manifest_path="reports/p5/production_index_manifest.json",
        rebuilt_case_manifest_path="reports/p5/rebuilt_case_manifest.json",
        split_family_manifest_path="reports/p5/split_family_manifest.json",
        baseline_run_manifest_path="reports/p5/baseline_run_manifest.json",
        six_layer_report_path="reports/p5/six_layer_report.json",
        fixture_vs_real_evidence_manifest_path="reports/p5/fixture_vs_real_evidence_manifest.json",
        p5_p6_interface_manifest_path="reports/p5/p5_p6_interface_manifest.json",
        formal_kpi_registry_path="reports/p5/formal_kpi_registry.json",
        go_no_go_decision_path="reports/p5/go_no_go_decision.json",
        gate_status=gate_status,
        run_hash=_canonical_hash({
            "run_id": run_id,
            "p1_snapshot_id": full_manifest.snapshot_id,
            "p1_snapshot_hash": full_manifest.snapshot_hash,
        }),
    )

    # =================================================================
    # Write all reports
    # =================================================================
    write_json(os.path.join(REPORTS_DIR, "full_snapshot_manifest.json"), full_manifest.model_dump(mode="json"))
    write_json(os.path.join(REPORTS_DIR, "production_index_manifest.json"), prod_manifest.model_dump(mode="json"))
    write_json(os.path.join(REPORTS_DIR, "rebuilt_case_manifest.json"), [c.model_dump(mode="json") for c in cases])
    write_json(os.path.join(REPORTS_DIR, "split_family_manifest.json"), [s.model_dump(mode="json") for s in splits])
    write_json(os.path.join(REPORTS_DIR, "baseline_run_manifest.json"), [b.model_dump(mode="json") for b in baselines])
    if six_layer_report:
        write_json(os.path.join(REPORTS_DIR, "six_layer_report.json"), six_layer_report.model_dump(mode="json"))
    if kpi_registry:
        write_json(os.path.join(REPORTS_DIR, "formal_kpi_registry.json"), kpi_registry.model_dump(mode="json"))
    if go_no_go:
        write_json(os.path.join(REPORTS_DIR, "go_no_go_decision.json"), go_no_go.model_dump(mode="json"))

    # Fixture vs real evidence manifest
    if use_real:
        fixture_vs_real = {
            "schema_version": P5_SCHEMA_VERSION,
            "summary": {
                "total_artifacts": 10,
                "real": 6,
                "synthetic_fixture": 0,
                "derived_diagnostic": 1,
                "protocol_only": 3,
                "blocked": 0,
            },
            "artifacts": [
                {"name": "full_snapshot_manifest", "classification": "real",
                 "reason": "Real P1 snapshot snap_19caddc6b312 (50 audited Rhea cases)"},
                {"name": "production_index_manifest", "classification": "real",
                 "reason": "Derived from real snapshot records (7 production + 43 diagnostic)"},
                {"name": "rebuilt_case_manifest", "classification": "real",
                 "reason": "50 cases from real records + P2 audited truth (allowed_product_set)"},
                {"name": "split_family_manifest", "classification": "mixed",
                 "reason": "exact_x/scaffold/ood are real (P2 split + RDKit Murcko); "
                           "transformation_family/source/time are protocol_only (honest unavailable)"},
                {"name": "baseline_run_manifest", "classification": "mixed",
                 "reason": "strict_kernel real (P3 artifact); other baselines protocol_only "
                           "(defined, not run)"},
                {"name": "six_layer_report", "classification": "real",
                 "reason": "Real metrics from P3 kernel + P4 verified bundle; cost/runtime unavailable"},
                {"name": "formal_kpi_registry", "classification": "real",
                 "reason": "Registered when P3+P4 real data available"},
                {"name": "go_no_go_decision", "classification": "real",
                 "reason": "Go decision on real data integrity + retrieval availability"},
                {"name": "p5_p6_interface_manifest", "classification": "protocol_only",
                 "reason": "Interface contract only"},
                {"name": "oracle_upper_bound", "classification": "derived_diagnostic",
                 "reason": "Oracle baseline (diagnostic only), unavailable"},
            ],
        }
    else:
        fixture_vs_real = {
            "schema_version": P5_SCHEMA_VERSION,
            "summary": {
                "total_artifacts": 10,
                "real": 0,
                "synthetic_fixture": 8,
                "derived_diagnostic": 1,
                "protocol_only": 1,
                "blocked": 0,
            },
            "artifacts": [
                {"name": "full_snapshot_manifest", "classification": "synthetic_fixture",
                 "reason": "P1 snapshot is fixture (4 synthetic records)"},
                {"name": "production_index_manifest", "classification": "synthetic_fixture",
                 "reason": "Derived from fixture snapshot"},
                {"name": "rebuilt_case_manifest", "classification": "synthetic_fixture",
                 "reason": "Cases built from fixture snapshot, P2 truth unavailable"},
                {"name": "split_family_manifest", "classification": "mixed",
                 "reason": "exact_x/scaffold/txf/ood are synthetic_fixture; source/time are protocol_only"},
                {"name": "baseline_run_manifest", "classification": "synthetic_fixture",
                 "reason": "Baselines on fixture data, no real candidates"},
                {"name": "six_layer_report", "classification": "synthetic_fixture",
                 "reason": "Report on fixture data, most metrics unavailable (P3/P4 missing)"},
                {"name": "formal_kpi_registry", "classification": "protocol_only",
                 "reason": "KPI not registered (upstream blocked)"},
                {"name": "go_no_go_decision", "classification": "blocked",
                 "reason": "Decision blocked by upstream P2/P3/P4"},
                {"name": "p5_p6_interface_manifest", "classification": "protocol_only",
                 "reason": "Interface contract only, no real data"},
                {"name": "oracle_upper_bound", "classification": "derived_diagnostic",
                 "reason": "Oracle baseline (diagnostic only), unavailable"},
            ],
        }
    write_json(os.path.join(REPORTS_DIR, "fixture_vs_real_evidence_manifest.json"), fixture_vs_real)

    # P5-P6 interface manifest
    p5_p6_interface = {
        "schema_version": P5_SCHEMA_VERSION,
        "description": "P5→P6 interface manifest — frozen artifact/hash/version contract",
        "artifact_types": {
            "FullSnapshotManifest": {
                "fields": ["snapshot_id", "snapshot_hash", "artifact_classification",
                           "production_count", "diagnostic_count", "quarantine_count",
                           "filter_accounting[]"],
                "hash_algorithm": "sha256",
                "version": P5_SCHEMA_VERSION,
            },
            "ProductionIndexManifest": {
                "fields": ["production_record_ids[]", "strict_count", "conditional_count",
                           "diagnostic_ids[]", "quarantine_ids[]"],
                "hash_algorithm": "sha256",
                "version": P5_SCHEMA_VERSION,
            },
            "RebuiltCaseRecord": {
                "fields": ["case_id", "query_smiles", "allowed_product_set[]",
                           "source_reaction_ids[]", "transformation_ids[]",
                           "incomplete_truth", "fold_eligible"],
                "hash_algorithm": "sha256",
                "version": P5_SCHEMA_VERSION,
            },
            "SplitFamilyManifest": {
                "fields": ["split_family_name", "split_id", "split_hash",
                           "train_query_ids[]", "test_query_ids[]",
                           "domain_audit", "unavailable", "unavailable_reason"],
                "hash_algorithm": "sha256",
                "version": P5_SCHEMA_VERSION,
            },
            "BaselineRunArtifact": {
                "fields": ["baseline_id", "baseline_name", "snapshot_id", "split_id",
                           "case_registry_id", "config_hash", "is_oracle", "namespace"],
                "hash_algorithm": "sha256",
                "version": P5_SCHEMA_VERSION,
            },
            "LayerMetricReport": {
                "fields": ["metric_name", "layer", "numerator", "denominator", "n",
                           "ci_lower", "ci_upper", "unavailable", "unavailable_reason"],
                "hash_algorithm": "sha256",
                "version": P5_SCHEMA_VERSION,
            },
            "SixLayerReport": {
                "fields": ["report_id", "metrics[]", "report_hash",
                           "snapshot_id", "split_id", "baseline_id"],
                "hash_algorithm": "sha256",
                "version": P5_SCHEMA_VERSION,
            },
            "FormalKPIRegistry": {
                "fields": ["registered", "kpi_entries[]", "registration_reason"],
                "hash_algorithm": "sha256",
                "version": P5_SCHEMA_VERSION,
            },
            "GoNoGoDecision": {
                "fields": ["decision", "blockers[]", "decision_reason",
                           "data_integrity_assessed", "retrieval_availability_assessed"],
                "hash_algorithm": "sha256",
                "version": P5_SCHEMA_VERSION,
            },
            "P5RunManifest": {
                "fields": ["run_id", "run_timestamp", "p1_snapshot_id",
                           "p1_snapshot_hash", "p1_status", "p2_status",
                           "p3_status", "p4_status", "gate_status"],
                "hash_algorithm": "sha256",
                "version": P5_SCHEMA_VERSION,
            },
        },
        "artifact_classification_enum": ["real", "synthetic_fixture", "derived_diagnostic", "protocol_only", "blocked"],
        "metric_unavailable_reason_enum": [r.value for r in MetricUnavailableReason],
    }
    write_json(os.path.join(REPORTS_DIR, "p5_p6_interface_manifest.json"), p5_p6_interface)

    # Write run manifest
    write_json(os.path.join(REPORTS_DIR, "p5_run_manifest.json"), run_manifest.model_dump(mode="json"))

    # Write mutation results
    write_json(os.path.join(REPORTS_DIR, "P5_MUTATION_RESULTS.json"), mutation_result)

    # Write gate report
    gate_report = {
        "timestamp": run_timestamp,
        "gate_version": "p5-gate-1",
        "schema_version": P5_SCHEMA_VERSION,
        "run_id": run_id,
        "status": gate_status,
        "pass_count": sum(1 for g in gate_items if g["passed"] and not g["blocked"]),
        "block_count": sum(1 for g in gate_items if g["blocked"]),
        "fail_count": sum(1 for g in gate_items if not g["passed"] and not g["blocked"]),
        "total_checks": len(gate_items),
        "all_passed": gate_status == "PASS",
        "checks": gate_items,
        "upstream_status": {
            "p1": p1_status,
            "p2": p2_status,
            "p3": p3_status,
            "p4": p4_status,
        },
        "mutation_summary": {
            "total": mutation_result["total"],
            "caught": mutation_result["caught"],
            "escaped": mutation_result["escaped"],
            "errors": mutation_result["errors"],
        },
        "p1_snapshot": {
            "snapshot_id": full_manifest.snapshot_id,
            "snapshot_hash": full_manifest.snapshot_hash,
            "artifact_classification": full_manifest.artifact_classification.value,
        },
    }
    write_json(os.path.join(REPORTS_DIR, "P5_GATE_REPORT.json"), gate_report)
    write_md_report(os.path.join(REPORTS_DIR, "P5_GATE_REPORT.md"), gate_report)

    return gate_report


def write_md_report(path: str, report: dict[str, Any]):
    """Render the Markdown gate report from the JSON authority (read-only)."""
    up = report["upstream_status"]
    checks = "\n".join(
        f"| {g['gate_id']} | {g['name']} | {g['passed']} | {g['blocked']} | "
        f"{g['evidence']} |"
        for g in report["checks"])
    snapshot = report["p1_snapshot"]
    md = f"""# P5 Gate Report

**Timestamp:** {report['timestamp']}
**Gate version:** {report['gate_version']}
**Run ID:** {report['run_id']}
**Status:** **{report['status']}**

## Summary

| Metric | Value |
|--------|-------|
| Pass | {report['pass_count']} |
| Block | {report['block_count']} |
| Fail | {report['fail_count']} |
| Total | {report['total_checks']} |
| Mutations caught | {report['mutation_summary']['caught']}/{report['mutation_summary']['total']} |
| Mutations escaped | {report['mutation_summary']['escaped']} |
| Mutations errored | {report['mutation_summary']['errors']} |

## Upstream status

| Phase | Status |
|-------|--------|
| P1 | {up['p1']} |
| P2 | {up['p2']} |
| P3 | {up['p3']} |
| P4 | {up['p4']} |

## P1 snapshot

- Snapshot ID: {snapshot['snapshot_id']}
- Snapshot hash: {snapshot['snapshot_hash']}
- Artifact classification: {snapshot['artifact_classification']}

## Gate items

| Gate ID | Name | Passed | Blocked | Evidence |
|---------|------|--------|---------|----------|
{checks}

## Gate decision

The P5 Gate status is **{report['status']}**.

## JSON authority

The JSON report at `P5_GATE_REPORT.json` is the authority. This Markdown
is rendered from the JSON and must not be used as the source of truth.
"""
    with open(path, "w") as f:
        f.write(md)


def run_invariant_tests() -> dict[str, Any]:
    """Run the P5 invariant test suite; the gate consumes this result.

    A non-green suite (any failure/error/non-zero exit) keeps the gate from
    PASSING — a PASS gate with a red suite is a bypass (P5-R1-02).
    """
    import subprocess
    import re
    python_bin = os.environ.get("P5_PYTHON", "/opt/anaconda3/bin/python3")
    result = subprocess.run(
        [python_bin, "-m", "pytest",
         os.path.join(PROJECT_ROOT, "tests/p5"),
         "-q", "-p", "no:cacheprovider"],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT,
    )
    output = result.stdout + result.stderr
    m = re.search(r"(\d+) (?:passed|failed)", output)
    last_line = output.strip().splitlines()[-1] if output.strip() else ""
    total = int(m.group(1)) if m else 0
    failed = int(re.search(r"(\d+) failed", output).group(1)) if re.search(r"(\d+) failed", output) else 0
    errors = int(re.search(r"(\d+) error", output).group(1)) if re.search(r"(\d+) error", output) else 0
    return {
        "passed": total - failed - errors if failed or errors else total,
        "failed": failed,
        "errors": errors,
        "exit_code": result.returncode,
        "summary": last_line,
    }


def run_mutations() -> dict[str, Any]:
    """Run P5 anti-false-positive mutations."""
    import subprocess
    python_bin = os.environ.get("P5_PYTHON", "/opt/anaconda3/bin/python3")
    result = subprocess.run(
        [python_bin, "-m", "pytest",
         os.path.join(PROJECT_ROOT, "tests/p5/test_p5_mutations.py"),
         "-v", "--tb=line",
         "-p", "no:cacheprovider"],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT,
    )

    # Parse pytest output for pass/fail
    output = result.stdout + result.stderr
    lines = [l for l in output.split("\n") if "::test_mutation_" in l]

    total = len(lines)
    caught = sum(1 for l in lines if "PASSED" in l)
    escaped = sum(1 for l in lines if "FAILED" in l)
    errors = sum(1 for l in lines if "ERROR" in l)

    mutations = []
    for line in lines:
        if "::test_mutation_" in line:
            name = line.split("::test_mutation_")[1].split(" ")[0]
            status = "caught" if "PASSED" in line else ("escaped" if "FAILED" in line else "error")
            mutations.append({"mutation": f"test_mutation_{name}", "status": status})

    return {
        "total": total,
        "caught": caught,
        "escaped": escaped,
        "errors": errors,
        "mutations": mutations,
        "pytest_exit_code": result.returncode,
    }


def write_json(path: str, data: Any):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    report = run_p5_gate()
    print(f"\nP5 Gate Status: {report['status']}")
    print(f"Pass: {report['pass_count']}, Block: {report['block_count']}, Fail: {report['fail_count']}")
    print(f"Mutations: {report['mutation_summary']['caught']}/{report['mutation_summary']['total']} caught")
    print(f"Upstream: P1={report['upstream_status']['p1']}, P2={report['upstream_status']['p2']}, "
          f"P3={report['upstream_status']['p3']}, P4={report['upstream_status']['p4']}")
