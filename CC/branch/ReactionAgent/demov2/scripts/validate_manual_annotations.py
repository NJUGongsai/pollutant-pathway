#!/usr/bin/env python3
"""Validate independent P1-T11 annotations and build an adjudication packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKET = ROOT / "reports" / "p1" / "manual_audit_evidence_packet.json"
PROTOCOL = ROOT / "docs" / "manual_audit_protocol.md"

RUBRICS = {f"R{i}" for i in range(1, 12)}
ERRORS = {f"C{i}" for i in range(1, 10)}
VERDICTS = {"pass", "fail", "not_applicable"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reject_forbidden_text(data: dict, label: str) -> None:
    if "confidence" in json.dumps(data, ensure_ascii=False).lower():
        raise ValueError(f"{label} contains forbidden self-assessment vocabulary")


def _validate_annotation(path: Path, expected_id: str, packet: dict) -> dict:
    data = _load(path)
    _reject_forbidden_text(data, path.name)
    if data.get("schema_version") != "p1-t11-annotation-1":
        raise ValueError(f"{path.name}: wrong schema_version")
    if data.get("status") != "COMPLETE":
        raise ValueError(f"{path.name}: status must be COMPLETE")
    if data.get("annotator_id") != expected_id:
        raise ValueError(f"{path.name}: unexpected annotator_id")
    if data.get("evidence_packet_sha256") != _sha256(PACKET):
        raise ValueError(f"{path.name}: evidence packet hash mismatch")
    independence = data.get("independence", {})
    if independence.get("session_kind") != "codex_internal_subagent":
        raise ValueError(f"{path.name}: wrong session kind")
    if independence.get("blinded_to_peer") is not True:
        raise ValueError(f"{path.name}: blindness not affirmed")
    if independence.get("peer_output_read") is not False:
        raise ValueError(f"{path.name}: peer output may have been read")

    expected_samples = {
        item["sample_id"]: item["reaction_id"]
        for item in packet["sample_manifest"]["items"]
    }
    applicable_by_sample = {
        item["sample_id"]: set(item.get("rubric_items_applicable", []))
        for item in packet["sample_manifest"]["items"]
    }
    annotations = data.get("annotations", [])
    if len(annotations) != len(expected_samples):
        raise ValueError(f"{path.name}: wrong annotation count")
    if {item.get("sample_id") for item in annotations} != set(expected_samples):
        raise ValueError(f"{path.name}: sample coverage mismatch")
    for item in annotations:
        sample_id = item["sample_id"]
        if item.get("reaction_id") != expected_samples[sample_id]:
            raise ValueError(f"{path.name}: reaction ID mismatch for {sample_id}")
        rubrics = item.get("rubrics", {})
        if set(rubrics) != RUBRICS:
            raise ValueError(f"{path.name}: rubric coverage mismatch for {sample_id}")
        for rubric_id, judgment in rubrics.items():
            if judgment.get("verdict") not in VERDICTS:
                raise ValueError(f"{path.name}: invalid {rubric_id} verdict")
            if rubric_id in applicable_by_sample[sample_id]:
                if judgment.get("verdict") == "not_applicable":
                    raise ValueError(
                        f"{path.name}: {sample_id}:{rubric_id} is explicitly "
                        "applicable in the frozen manifest"
                    )
            elif judgment.get("verdict") != "not_applicable":
                raise ValueError(
                    f"{path.name}: {sample_id}:{rubric_id} is omitted from the "
                    "frozen applicability list and must be not_applicable"
                )
            if not judgment.get("reason") or not judgment.get("evidence_pointer"):
                raise ValueError(f"{path.name}: incomplete {rubric_id} judgment")
        errors = item.get("catastrophic_errors", {})
        if not isinstance(errors, dict) or set(errors) != ERRORS:
            raise ValueError(f"{path.name}: C1-C9 coverage mismatch for {sample_id}")
        for error_id, entry in errors.items():
            if not isinstance(entry.get("observed"), bool):
                raise ValueError(
                    f"{path.name}: non-boolean catastrophic judgment {error_id}"
                )
            if not entry.get("reason") or not entry.get("evidence_pointer"):
                raise ValueError(f"{path.name}: incomplete catastrophic judgment")
    required_case = data.get("required_case_assessment", {})
    if required_case.get("H2_verdict") not in {"pass", "fail"}:
        raise ValueError(f"{path.name}: invalid H2 verdict")
    if not required_case.get("reason") or not required_case.get("evidence_pointer"):
        raise ValueError(f"{path.name}: incomplete H2 assessment")
    return data


def _by_sample(data: dict) -> dict[str, dict]:
    return {item["sample_id"]: item for item in data["annotations"]}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate blinded A/B annotations and seal adjudication input",
    )
    parser.add_argument("annotation_a", type=Path)
    parser.add_argument("annotation_b", type=Path)
    parser.add_argument("--annotator-a-id", required=True)
    parser.add_argument("--annotator-b-id", required=True)
    parser.add_argument("--adjudicator-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    a_path, b_path = args.annotation_a, args.annotation_b
    packet = _load(PACKET)
    a = _validate_annotation(a_path, args.annotator_a_id, packet)
    b = _validate_annotation(b_path, args.annotator_b_id, packet)
    if a["annotator_id"] == b["annotator_id"]:
        raise ValueError("annotator IDs are not independent")
    a_samples, b_samples = _by_sample(a), _by_sample(b)
    disagreements: list[dict] = []
    agreements = 0
    total = 0
    per_field: dict[str, dict[str, int]] = {
        rubric: {"agreed": 0, "total": 0} for rubric in sorted(RUBRICS)
    }
    for sample_id in sorted(a_samples):
        for rubric in sorted(RUBRICS):
            av = a_samples[sample_id]["rubrics"][rubric]["verdict"]
            bv = b_samples[sample_id]["rubrics"][rubric]["verdict"]
            total += 1
            per_field[rubric]["total"] += 1
            if av == bv:
                agreements += 1
                per_field[rubric]["agreed"] += 1
            else:
                disagreements.append({
                    "disagreement_id": f"{sample_id}:{rubric}",
                    "kind": "rubric",
                    "sample_id": sample_id,
                    "field_id": rubric,
                    "annotator_a": a_samples[sample_id]["rubrics"][rubric],
                    "annotator_b": b_samples[sample_id]["rubrics"][rubric],
                })
        a_errors = a_samples[sample_id]["catastrophic_errors"]
        b_errors = b_samples[sample_id]["catastrophic_errors"]
        for error_id in sorted(ERRORS):
            if a_errors[error_id]["observed"] != b_errors[error_id]["observed"]:
                disagreements.append({
                    "disagreement_id": f"{sample_id}:{error_id}",
                    "kind": "catastrophic_error",
                    "sample_id": sample_id,
                    "field_id": error_id,
                    "annotator_a": a_errors[error_id],
                    "annotator_b": b_errors[error_id],
                })
    if a["required_case_assessment"]["H2_verdict"] != b["required_case_assessment"]["H2_verdict"]:
        disagreements.append({
            "disagreement_id": "required_case:H2",
            "kind": "required_case",
            "sample_id": None,
            "field_id": "H2",
            "annotator_a": a["required_case_assessment"],
            "annotator_b": b["required_case_assessment"],
        })

    adjudication_packet = {
        "schema_version": "p1-t11-adjudication-packet-1",
        "protocol_path": str(PROTOCOL),
        "protocol_sha256": _sha256(PROTOCOL),
        "evidence_packet_path": str(PACKET),
        "evidence_packet_sha256": _sha256(PACKET),
        "annotation_a_path": str(a_path),
        "annotation_a_sha256": _sha256(a_path),
        "annotation_b_path": str(b_path),
        "annotation_b_sha256": _sha256(b_path),
        "annotator_a_id": a["annotator_id"],
        "annotator_b_id": b["annotator_id"],
        "rubric_raw_agreement": agreements / total,
        "rubric_agreement_counts": {"agreed": agreements, "total": total},
        "per_rubric_agreement": {
            rubric: values["agreed"] / values["total"]
            for rubric, values in per_field.items()
        },
        "disagreement_count": len(disagreements),
        "disagreements": disagreements,
        "annotation_a": a,
        "annotation_b": b,
        "adjudicator_contract": {
            "required_id": args.adjudicator_id,
            "must_resolve_disagreement_ids": [
                item["disagreement_id"] for item in disagreements
            ],
            "outcome_fields": [
                "disagreement_id", "final_value", "reason", "evidence_pointer"
            ],
            "must_independently_review_all_agreed_catastrophic_judgments": True,
            "must_independently_review_H2": True,
        },
    }
    args.output.write_text(
        json.dumps(adjudication_packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"validated A/B; raw agreement={agreements}/{total}={agreements/total:.6f}")
    print(f"disagreements={len(disagreements)}")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
