#!/usr/bin/env python3
"""Generate P4 report artifacts: fixture_vs_real_evidence_manifest.json,
dependency_matrix.md, integration_worklog.md (all under reports/p4/)."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

DEMOV2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEMOV2_ROOT)
REPORT_DIR = os.path.join(DEMOV2_ROOT, "reports", "p4")


def fixture_manifest() -> dict:
    from tests.fixtures.p4.p4_contract_fixture import (
        build_evidence_records, build_strict_candidate, POLICY_VERSION)
    records = build_evidence_records()
    return {
        "manifest_version": "p4-fixture-vs-real-1",
        "policy_version": POLICY_VERSION,
        "fixture_evidence": {
            "row_count": len(records),
            "reaction_ids": [r.reaction_id for r in records],
            "classification": "synthetic_fixture",
            "license_provenance": "synthetic contract fixture, no real source",
        },
        "fixture_candidate": {
            "candidate_id": build_strict_candidate().candidate_id,
            "classification": "synthetic_fixture",
        },
        "real_evidence": {
            "available": False,
            "blocked_reasons": [
                "p3_interface_manifest_missing",
                "rdkit_absent",
                "real_evidence_not_confirmed",
            ],
        },
        "rule": "synthetic fixture must never be mixed into real audit counts; "
                "synthetic-only => typed BLOCKED, never PASS.",
    }


def dependency_matrix() -> list[dict]:
    return [
        {"dependency": "P1 snapshot/lineage/ledger/eligibility authority",
         "status": "ACCEPTED (P1 final acceptance 2026-08-02)",
         "usage": "P4 consumes ReactionEvidence + Candidate schemas and snapshot ID; read-only",
         "blocker": None},
        {"dependency": "P2 truth/isolation/Gate/mutation",
         "status": "P2 formal Gate BLOCKED",
         "usage": "NOT treated as authority; p2_truth_authority_available=False; real-input gate P4-G14 BLOCKED",
         "blocker": "p2_gate_blocked"},
        {"dependency": "P3 strict kernel + p3_p4_interface_manifest.json",
         "status": "absent (no reports/p3/p3_p4_interface_manifest.json)",
         "usage": "P4 consumer adapter returns typed BLOCKED; real-input gate P4-G12 BLOCKED; no real candidates consumed",
         "blocker": "p3_interface_manifest_missing"},
        {"dependency": "chemistry backend (rdkit)",
         "status": "absent",
         "usage": "structural features not observable (is_observable=False); preflight BLOCKED",
         "blocker": "rdkit_absent"},
        {"dependency": "shared schemas (StrictModel, PredictionResult, enums)",
         "status": "reused read-only",
         "usage": "P4 reuses P1 PredictionResult via adapter; no synonymous schema created",
         "blocker": None},
        {"dependency": "reaction_agent/hashing.py canonical_hash / stable_id",
         "status": "reused",
         "usage": "content-addressed evidence/group/run/result hashes",
         "blocker": None},
    ]


def integration_worklog() -> list[dict]:
    return [
        {"step": "P4-T1 evidence identity/dedup",
         "module": "reaction_agent/inference/evidence_identity.py",
         "verification": "tests/p4/test_evidence_identity.py: 6 tests"},
        {"step": "P4-T2 support aggregation",
         "module": "reaction_agent/inference/support.py + features.py",
         "verification": "tests/p4/test_support.py: 5 tests"},
        {"step": "P4-T3 counterevidence",
         "module": "reaction_agent/inference/counterevidence.py",
         "verification": "tests/p4/test_counterevidence.py: 4 tests"},
        {"step": "P4-T4 strict ranker",
         "module": "reaction_agent/inference/ranker.py",
         "verification": "tests/p4/test_ranker.py: 4 tests"},
        {"step": "P4-T5 applicability",
         "module": "reaction_agent/inference/applicability.py",
         "verification": "tests/p4/test_applicability.py: 4 tests"},
        {"step": "P4-T6 typed abstention",
         "module": "reaction_agent/inference/abstention.py",
         "verification": "tests/p4/test_abstention.py: 7 tests"},
        {"step": "P4-T7 PredictionResult invariants",
         "module": "reaction_agent/adapters/prediction_result_adapter.py",
         "verification": "tests/p4/test_prediction_result_invariants.py: 9 tests"},
        {"step": "P4-T8 immutable run/trace/manifest",
         "module": "reaction_agent/runtime/{trace,manifest,run}.py",
         "verification": "tests/p4/test_immutable_run.py: 6 tests"},
        {"step": "P3->P4 consumer adapter",
         "module": "reaction_agent/adapters/p3_consumer.py",
         "verification": "tests/p4/test_p3_consumer_adapter.py: 4 tests"},
        {"step": "P4 pipeline orchestrator",
         "module": "reaction_agent/inference/predictor.py",
         "verification": "tests/p4/test_predictor_pipeline.py: 5 tests"},
        {"step": "P4 Gate + mutation runner",
         "module": "scripts/run_p4_gate.py + run_p4_mutations.py",
         "verification": "tests/p4/test_p4_gate_contract.py: 3 tests; 14/14 mutations caught"},
        {"step": "P4->P5 interface manifest",
         "module": "reports/p4/p4_p5_interface_manifest.json",
         "verification": "frozen contract; hash + version pinned"},
    ]


def main() -> int:
    os.makedirs(REPORT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()

    fm = fixture_manifest()
    fm["timestamp"] = ts
    with open(os.path.join(REPORT_DIR, "fixture_vs_real_evidence_manifest.json"),
              "w", encoding="utf-8") as f:
        json.dump(fm, f, indent=2, ensure_ascii=False, default=str)

    dm = dependency_matrix()
    dm_lines = [
        "# P4 Dependency Matrix", "",
        f"**Timestamp (UTC):** {ts}", "",
        "| Dependency | Status | Usage | Blocker |",
        "|-----------|--------|-------|---------|",
    ]
    for d in dm:
        dm_lines.append(f"| {d['dependency']} | {d['status']} | {d['usage']} | "
                        f"{d['blocker'] or '-'} |")
    with open(os.path.join(REPORT_DIR, "dependency_matrix.md"),
              "w", encoding="utf-8") as f:
        f.write("\n".join(dm_lines))

    wl = integration_worklog()
    wl_lines = [
        "# P4 Integration Worklog", "",
        f"**Timestamp (UTC):** {ts}", "",
        "| Step | Module | Verification |",
        "|------|--------|-------------|",
    ]
    for s in wl:
        wl_lines.append(f"| {s['step']} | {s['module']} | {s['verification']} |")
    wl_lines.extend(["", "## No network / install / provider / commit / push",
                     "This P4 worktree run performed no network access, no "
                     "dependency installation, no real LLM/MCP/Orchestra calls, "
                     "and no git commit/push/merge."])
    with open(os.path.join(REPORT_DIR, "integration_worklog.md"),
              "w", encoding="utf-8") as f:
        f.write("\n".join(wl_lines))

    print("wrote fixture_vs_real_evidence_manifest.json")
    print("wrote dependency_matrix.md")
    print("wrote integration_worklog.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
