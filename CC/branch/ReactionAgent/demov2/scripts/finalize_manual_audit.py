#!/usr/bin/env python3
"""Validate independent P1-T11 evidence and finalize the canonical audit.

This script is deliberately mechanical. It does not invent or revise any
judgment: agreed rubric values come from A/B, disagreements come only from the
independent adjudicator, and pass/fail is computed from the frozen protocol.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.validate_manual_annotations import (  # noqa: E402
    ERRORS,
    RUBRICS,
    _load,
    _sha256,
    _validate_annotation,
)


REPORTS = ROOT / "reports" / "p1"
PACKET = REPORTS / "manual_audit_evidence_packet.json"
PROTOCOL = ROOT / "docs" / "manual_audit_protocol.md"
MANIFEST = REPORTS / "manual_audit_sample_manifest.json"

DOMAIN_RUBRICS = {
    "mapping_rubric_score": ("R1", "R5"),
    "role_rubric_score": ("R2", "R6"),
    "lineage_rubric_score": ("R3", "R11"),
    "ledger_rubric_score": ("R4", "R7", "R8", "R9", "R10"),
}


def _args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("annotation_a", type=Path)
    parser.add_argument("annotation_b", type=Path)
    parser.add_argument("adjudication", type=Path)
    parser.add_argument("--annotator-a-id", required=True)
    parser.add_argument("--annotator-b-id", required=True)
    parser.add_argument("--adjudicator-id", required=True)
    parser.add_argument("--round", type=int, required=True)
    return parser.parse_args(argv[1:])


def _reject_forbidden_text(data: dict, label: str) -> None:
    if "confidence" in json.dumps(data, ensure_ascii=False).lower():
        raise ValueError(f"{label} contains protocol-forbidden audit vocabulary")


def _validate_adjudication(
    path: Path,
    *,
    expected_id: str,
    a_path: Path,
    b_path: Path,
    adjudication_packet: dict,
) -> dict:
    data = _load(path)
    _reject_forbidden_text(data, path.name)
    if data.get("schema_version") != "p1-t11-adjudication-1":
        raise ValueError("wrong adjudication schema_version")
    if data.get("status") != "COMPLETE":
        raise ValueError("adjudication status must be COMPLETE")
    if data.get("adjudicator_id") != expected_id:
        raise ValueError("unexpected adjudicator_id")
    if data.get("evidence_packet_sha256") != _sha256(PACKET):
        raise ValueError("adjudication evidence packet hash mismatch")
    if data.get("annotation_a_sha256") != _sha256(a_path):
        raise ValueError("adjudication annotation A hash mismatch")
    if data.get("annotation_b_sha256") != _sha256(b_path):
        raise ValueError("adjudication annotation B hash mismatch")
    independence = data.get("independence", {})
    if independence.get("session_kind") != "codex_internal_subagent":
        raise ValueError("wrong adjudicator session kind")
    if independence.get("independent_of_annotators") is not True:
        raise ValueError("adjudicator independence not affirmed")
    if independence.get("annotator_conversations_read") is not False:
        raise ValueError("adjudicator may have read annotator conversations")

    expected_disagreements = {
        item["disagreement_id"] for item in adjudication_packet["disagreements"]
    }
    outcomes = data.get("outcomes", [])
    if data.get("disagreement_count") != len(expected_disagreements):
        raise ValueError("adjudicator disagreement_count mismatch")
    if {item.get("disagreement_id") for item in outcomes} != expected_disagreements:
        raise ValueError("adjudication outcomes do not exactly cover disagreements")
    for outcome in outcomes:
        if outcome.get("final_value") not in {
            "pass", "fail", "not_applicable", True, False,
        }:
            raise ValueError(f"invalid final_value for {outcome.get('disagreement_id')}")
        if not outcome.get("reason") or not outcome.get("evidence_pointer"):
            raise ValueError("incomplete adjudication outcome")

    sample_ids = {
        item["sample_id"] for item in _load(MANIFEST)["items"]
    }
    catastrophic = data.get("catastrophic_final_by_sample", {})
    if set(catastrophic) != sample_ids:
        raise ValueError("adjudicator catastrophic sample coverage mismatch")
    for sample_id, judgments in catastrophic.items():
        if set(judgments) != ERRORS:
            raise ValueError(f"{sample_id}: adjudicator C1-C9 coverage mismatch")
        for error_id, judgment in judgments.items():
            if not isinstance(judgment.get("observed"), bool):
                raise ValueError(f"{sample_id}:{error_id} observed must be boolean")
            if not judgment.get("reason") or not judgment.get("evidence_pointer"):
                raise ValueError(f"{sample_id}:{error_id} judgment incomplete")

    hard = data.get("hard_conditions", {})
    if set(hard) != {f"H{i}" for i in range(1, 8)}:
        raise ValueError("adjudicator H1-H7 coverage mismatch")
    for hard_id, judgment in hard.items():
        if judgment.get("verdict") not in {"pass", "fail"}:
            raise ValueError(f"{hard_id}: invalid hard-condition verdict")
        if not judgment.get("reason") or not judgment.get("evidence_pointer"):
            raise ValueError(f"{hard_id}: incomplete hard-condition judgment")
    required = data.get("required_case_final", {})
    if required.get("H2_verdict") != hard["H2"]["verdict"]:
        raise ValueError("required_case_final conflicts with hard condition H2")
    return data


def _annotation_samples(annotation: dict) -> dict[str, dict]:
    return {item["sample_id"]: item for item in annotation["annotations"]}


def _final_rubric_values(
    a: dict,
    b: dict,
    adjudication: dict,
) -> dict[str, dict[str, str]]:
    a_samples = _annotation_samples(a)
    b_samples = _annotation_samples(b)
    outcomes = {
        item["disagreement_id"]: item["final_value"]
        for item in adjudication["outcomes"]
    }
    final: dict[str, dict[str, str]] = {}
    for sample_id in sorted(a_samples):
        final[sample_id] = {}
        for rubric in sorted(RUBRICS):
            av = a_samples[sample_id]["rubrics"][rubric]["verdict"]
            bv = b_samples[sample_id]["rubrics"][rubric]["verdict"]
            if av == bv:
                final[sample_id][rubric] = av
            else:
                value = outcomes.get(f"{sample_id}:{rubric}")
                if value not in {"pass", "fail", "not_applicable"}:
                    raise ValueError(f"missing rubric resolution: {sample_id}:{rubric}")
                final[sample_id][rubric] = value
    return final


def _domain_scores(final_rubrics: dict[str, dict[str, str]]) -> dict[str, float]:
    result: dict[str, float] = {}
    for score_name, rubrics in DOMAIN_RUBRICS.items():
        values = [
            per_sample[rubric]
            for per_sample in final_rubrics.values()
            for rubric in rubrics
            if per_sample[rubric] != "not_applicable"
        ]
        if not values:
            raise ValueError(f"no applicable judgments for {score_name}")
        result[score_name] = sum(value == "pass" for value in values) / len(values)
    return result


def _markdown(report: dict) -> str:
    hard_rows = "\n".join(
        f"| {hard_id} | {judgment['verdict'].upper()} | {judgment['reason']} |"
        for hard_id, judgment in report["hard_condition_results"].items()
    )
    score_rows = "\n".join(
        f"| {name} | {value:.6f} |"
        for name, value in report["domain_scores"].items()
    )
    return f"""# P1-T11 Manual Audit Report — Round {report['audit_round']}

**Status:** `{report['status']}`
**Pass:** `{str(report['pass_status']).lower()}`
**Packet:** `{report['evidence_packet_sha256']}`

## Outcome

Two fresh blinded annotators completed the four-record census and a third
independent adjudicator resolved every disagreement. Round 1 is preserved at
`reports/p1/g10_round_1/`; this report is computed only from Round
{report['audit_round']} inputs.

| Metric | Value |
|---|---:|
| Raw A/B agreement | {report['agreement']:.6f} |
| Disagreements | {report['disagreement_count']} |
| Distinct catastrophic error types | {report['catastrophic_error_count']} |
| All disagreements resolved | {str(report['all_disagreements_resolved']).lower()} |

## Frozen hard conditions

| Condition | Verdict | Independent adjudicator reason |
|---|---|---|
{hard_rows}

## Domain rubric scores

| Score | Value |
|---|---:|
{score_rows}

## Evidence boundary

The four snapshot records are synthetic contract fixtures, not real chemical
performance evidence. H2 is evaluated separately against three real
proline/2OG source rows. The new pipeline explicitly quarantines those rows
because the available mapping is diagnostic formal MCS evidence; it does not
claim that their expected lineages have already been resolved.
"""


def main(argv: list[str]) -> int:
    args = _args(argv)
    packet = _load(PACKET)
    a = _validate_annotation(args.annotation_a, args.annotator_a_id, packet)
    b = _validate_annotation(args.annotation_b, args.annotator_b_id, packet)
    if a["annotator_id"] == b["annotator_id"]:
        raise ValueError("annotator IDs must differ")

    adjudication_packet_path = Path(
        args.adjudication.parent / f"p1_g10_r{args.round}_adjudication_packet.json"
    )
    if not adjudication_packet_path.exists():
        raise ValueError(f"adjudication packet missing: {adjudication_packet_path}")
    adjudication_packet = _load(adjudication_packet_path)
    adjudication = _validate_adjudication(
        args.adjudication,
        expected_id=args.adjudicator_id,
        a_path=args.annotation_a,
        b_path=args.annotation_b,
        adjudication_packet=adjudication_packet,
    )

    final_rubrics = _final_rubric_values(a, b, adjudication)
    scores = _domain_scores(final_rubrics)
    observed_error_types = {
        error_id
        for judgments in adjudication["catastrophic_final_by_sample"].values()
        for error_id, judgment in judgments.items()
        if judgment["observed"]
    }
    catastrophic_count = len(observed_error_types)
    agreement = adjudication_packet["rubric_raw_agreement"]
    expected_disagreements = adjudication_packet["disagreement_count"]
    all_resolved = len(adjudication["outcomes"]) == expected_disagreements
    all_hard_pass = all(
        item["verdict"] == "pass"
        for item in adjudication["hard_conditions"].values()
    )
    quality = {
        "Q1_raw_agreement_ge_0_90": agreement >= 0.90,
        "Q2_catastrophic_error_count_zero": catastrophic_count == 0,
        "Q3_all_domain_scores_ge_0_80": all(value >= 0.80 for value in scores.values()),
        "Q4_all_disagreements_resolved": all_resolved,
    }
    pass_status = all_hard_pass and all(quality.values())
    expected_recommendation = "PASS" if pass_status else "FAIL"
    if adjudication.get("audit_recommendation") != expected_recommendation:
        raise ValueError(
            "adjudicator recommendation conflicts with frozen H1-H7/Q1-Q4 outcome"
        )

    round_dir = REPORTS / f"g10_round_{args.round}"
    round_dir.mkdir(parents=True, exist_ok=True)
    archive_paths = {
        "annotation_a": round_dir / "annotator_a.json",
        "annotation_b": round_dir / "annotator_b.json",
        "adjudication": round_dir / "adjudication.json",
        "adjudication_packet": round_dir / "adjudication_packet.json",
    }
    shutil.copy2(args.annotation_a, archive_paths["annotation_a"])
    shutil.copy2(args.annotation_b, archive_paths["annotation_b"])
    shutil.copy2(args.adjudication, archive_paths["adjudication"])
    shutil.copy2(adjudication_packet_path, archive_paths["adjudication_packet"])

    canonical_a = REPORTS / "manual_audit_annotations_a.json"
    canonical_b = REPORTS / "manual_audit_annotations_b.json"
    canonical_adj = REPORTS / "manual_audit_adjudication.json"
    shutil.copy2(args.annotation_a, canonical_a)
    shutil.copy2(args.annotation_b, canonical_b)
    shutil.copy2(args.adjudication, canonical_adj)

    manifest = _load(MANIFEST)
    report = {
        "report_version": manifest["manifest_version"],
        "task": "P1-T11",
        "audit_round": args.round,
        "status": "COMPLETE",
        "protocol_document": "docs/manual_audit_protocol.md",
        "protocol_sha256": _sha256(PROTOCOL),
        "protocol_frozen_before_results": PROTOCOL.stat().st_mtime <= min(
            args.annotation_a.stat().st_mtime,
            args.annotation_b.stat().st_mtime,
            args.adjudication.stat().st_mtime,
        ),
        "evidence_packet": "reports/p1/manual_audit_evidence_packet.json",
        "evidence_packet_sha256": _sha256(PACKET),
        "sample_manifest": "reports/p1/manual_audit_sample_manifest.json",
        "sample_source": manifest["sample_source"],
        "sample_size": manifest["sample_size"],
        "sample_strategy": manifest["sample_strategy"],
        "snapshot_id": manifest["snapshot_id"],
        "snapshot_hash": manifest["snapshot_hash"],
        "annotator_a_file": "reports/p1/manual_audit_annotations_a.json",
        "annotator_b_file": "reports/p1/manual_audit_annotations_b.json",
        "adjudication_file": "reports/p1/manual_audit_adjudication.json",
        "annotator_a_status": a["status"],
        "annotator_b_status": b["status"],
        "adjudication_status": adjudication["status"],
        "annotator_a_id": a["annotator_id"],
        "annotator_b_id": b["annotator_id"],
        "adjudicator_id": adjudication["adjudicator_id"],
        "agreement": agreement,
        "per_rubric_agreement": adjudication_packet["per_rubric_agreement"],
        "disagreement_count": expected_disagreements,
        "all_disagreements_resolved": all_resolved,
        "catastrophic_error_count": catastrophic_count,
        "observed_catastrophic_error_types": sorted(observed_error_types),
        **scores,
        "domain_scores": scores,
        "final_rubric_values": final_rubrics,
        "pass_threshold_frozen": {
            "H1": "catastrophic errors in production index = 0",
            "H2": "proline-2OG correct or quarantined",
            "H3": "critical tie silently selected = 0",
            "H4": "quarantine leakage = 0",
            "H5": "participant destructive loss = 0",
            "H6": "formal->mechanistic false upgrade = 0",
            "H7": "snapshot replay / hash failure = 0",
            "Q1": "raw agreement >= 0.90",
            "Q2": "catastrophic error count = 0",
            "Q3": "all domain rubric scores >= 0.80",
            "Q4": "all disagreements resolved",
        },
        "hard_condition_results": adjudication["hard_conditions"],
        "quality_gate_results": quality,
        "hard_conditions_evaluated": True,
        "pass_status": pass_status,
        "pass_status_reason": (
            "All frozen H1-H7 and Q1-Q4 conditions passed."
            if pass_status else
            "At least one frozen H1-H7 or Q1-Q4 condition failed."
        ),
        "fixture_disclaimer": (
            "The four-record T10 census is synthetic contract evidence, not "
            "production-performance evidence. H2 uses three real source rows "
            "that are explicitly quarantined without a claimed resolution."
        ),
        "prior_rounds": [
            {
                "round": round_number,
                "status": "FAIL",
                "archive": f"reports/p1/g10_round_{round_number}/",
            }
            for round_number in range(1, args.round)
        ],
    }
    _reject_forbidden_text(report, "final report")
    (REPORTS / "manual_audit_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (REPORTS / "manual_audit_report.md").write_text(_markdown(report), encoding="utf-8")
    (round_dir / "manual_audit_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"finalized Round {args.round}: pass_status={pass_status}")
    print(f"agreement={agreement:.6f}, catastrophic={catastrophic_count}, scores={scores}")
    return 0 if pass_status else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
