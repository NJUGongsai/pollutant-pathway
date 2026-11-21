"""导出 Tuning-261 qid 级 Hit@k / 五态 route_status 对接表与 Tuning-76 case 级对照表。

零 LLM 调用、零触碰留出集、零 SMILES 泄漏：
- 仅消费调参集 `flips_v4cn` JSONL、干净子集分类表、`PER_GOLD_STEP.tsv` 与
  `LIKERT_V05_SCORES_726.tsv`；
- 通过 `pathway_v43.pollutant.route_status` 确定性映射五态路线状态
  （未经专家书面复核的未命中一律 fail-closed 记为 ``UNRESOLVED`` / ``NE``）；
- 为验收清单第 6 项（`program_vs_likert` join）提供路径线标准 `qid → Hit@k` 与
  `case_id → Hit@k` 键。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pathway_v43.pollutant.route_status import (  # noqa: E402
    DeliveryStatus,
    ExpertReviewRecord,
    RouteStatus,
    classify_route_status,
    summarize_route_statuses,
)


def _load_collision_cases(path: Path | None) -> set[str]:
    if path is None or not path.is_file():
        return set()
    with path.open(encoding="utf-8", newline="") as f:
        return {row["case_id"] for row in csv.DictReader(f, delimiter="\t")}


def _load_expert_reviews(path: Path | None) -> dict[str, ExpertReviewRecord]:
    if path is None or not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    if path.suffix == ".jsonl":
        items = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        raw = json.loads(text)
        if isinstance(raw, dict):
            return {k: ExpertReviewRecord.from_dict(v) for k, v in raw.items()}
        items = raw
    return {item["qid"]: ExpertReviewRecord.from_dict(item) for item in items}


def _hit_flags(rank: int | None) -> tuple[int, int, int]:
    if rank is None:
        return (0, 0, 0)
    return (int(rank <= 1), int(rank <= 3), int(rank <= 5))


def export_join_tables(
    *,
    flips_jsonl: Path,
    clean_classification_jsonl: Path,
    per_gold_step_tsv: Path,
    likert_scores_tsv: Path,
    out_dir: Path,
    collision_audit_tsv: Path | None = None,
    expert_reviews_json: Path | None = None,
) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)

    flips = [
        json.loads(line)
        for line in flips_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    clean_map = {
        row["qid"]: row
        for line in clean_classification_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }

    pgs_by_step: dict[str, dict[str, str]] = {}
    with per_gold_step_tsv.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            pgs_by_step.setdefault(row["gold_step_id"], row)

    likert_by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    with likert_scores_tsv.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            likert_by_case[row["case_id"]].append(row)

    collision_cases = _load_collision_cases(collision_audit_tsv)
    expert_reviews = _load_expert_reviews(expert_reviews_json)

    qid_rows: list[dict[str, object]] = []
    status_records = []
    clean_status_records = []
    case_buckets: dict[str, list[dict[str, object]]] = defaultdict(list)

    for row in sorted(flips, key=lambda r: r["qid"]):
        qid = row["qid"]
        parts = qid.split("__")
        case_id = parts[0]
        step_label = parts[1] if len(parts) > 1 else ""
        gold_reaction_id = parts[2] if len(parts) > 2 else ""

        cls_info = clean_map[qid]
        layer = cls_info["layer"]
        tuning_subset = "Clean-220" if layer == "CLEAN" else "Excluded-41"
        pgs_info = pgs_by_step.get(qid)
        in_pgs = pgs_info is not None
        scope_evaluable = pgs_info["scope_evaluable"] if pgs_info is not None else "N/A"
        is_collision = case_id in collision_cases

        after_rank = row.get("after_rank")
        before_rank = row.get("before_rank")
        after_bucket = row.get("after_bucket")
        delivery = (
            DeliveryStatus.NO_EVENT
            if after_bucket == "unmatched_no_event"
            else DeliveryStatus.OK
        )
        rec = classify_route_status(
            qid=qid,
            case_id=case_id,
            caliber="ppv1-criteria-v6",
            hit_rank=after_rank,
            match_bucket=after_bucket,
            delivery_status=delivery,
            expert_review=expert_reviews.get(qid),
            notes=(
                "tuning_step_in_scope"
                if in_pgs
                else "outside_g3_515_public_step_scope"
            ),
        )
        status_records.append(rec)
        if layer == "CLEAN":
            clean_status_records.append(rec)

        v6_h1, v6_h3, v6_h5 = _hit_flags(after_rank)
        v4_h1, v4_h3, v4_h5 = _hit_flags(before_rank)

        out_row: dict[str, object] = {
            "qid": qid,
            "case_id": case_id,
            "step_label": step_label,
            "gold_reaction_id": gold_reaction_id,
            "tuning_subset": tuning_subset,
            "clean_filter_layer": layer,
            "clean_filter_reason": cls_info["reason"],
            "in_per_gold_step_public": in_pgs,
            "per_gold_step_scope_evaluable": scope_evaluable,
            "is_route_gold_collision_case": is_collision,
            "v14_t16_delivery_status": rec.delivery_status.value,
            "v14_t16_v6_rank": after_rank if after_rank is not None else "NONE",
            "v14_t16_v6_hit1": v6_h1,
            "v14_t16_v6_hit3": v6_h3,
            "v14_t16_v6_hit5": v6_h5,
            "v14_t16_v4_rank": before_rank if before_rank is not None else "NONE",
            "v14_t16_v4_hit1": v4_h1,
            "v14_t16_v4_hit3": v4_h3,
            "v14_t16_v4_hit5": v4_h5,
            "v14_t16_route_status": rec.route_status.value,
            "v14_t16_scientific_eval_label": rec.scientific_eval_label.value,
            "v14_t16_zero_reason": rec.zero_reason.value,
            "v14_t16_expert_reviewed": rec.expert_review is not None and rec.expert_review.confirmed,
            "primary_score_immutable": rec.primary_score_immutable,
        }
        qid_rows.append(out_row)
        case_buckets[case_id].append(out_row)

    qid_tsv = out_dir / "pathway_qid_hitk_join_tuning261.tsv"
    qid_fields = list(qid_rows[0].keys())
    with qid_tsv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=qid_fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(qid_rows)

    case_rows: list[dict[str, object]] = []
    for case_id in sorted(case_buckets):
        steps = case_buckets[case_id]
        n_steps = len(steps)
        n_clean = sum(1 for s in steps if s["tuning_subset"] == "Clean-220")
        n_pgs = sum(1 for s in steps if s["in_per_gold_step_public"] is True)
        v6_h1_steps = sum(int(s["v14_t16_v6_hit1"]) for s in steps)
        v6_h3_steps = sum(int(s["v14_t16_v6_hit3"]) for s in steps)
        v6_h5_steps = sum(int(s["v14_t16_v6_hit5"]) for s in steps)
        v4_h1_steps = sum(int(s["v14_t16_v4_hit1"]) for s in steps)
        v4_h3_steps = sum(int(s["v14_t16_v4_hit3"]) for s in steps)
        v4_h5_steps = sum(int(s["v14_t16_v4_hit5"]) for s in steps)
        in_gold_exact = sum(
            1 for s in steps if s["v14_t16_route_status"] == RouteStatus.IN_GOLD_EXACT.value
        )
        unresolved_ne = sum(
            1 for s in steps if s["v14_t16_route_status"] == RouteStatus.UNRESOLVED.value
        )

        l_rows = likert_by_case.get(case_id, [])
        l_scored = [
            float(r["likert_total"])
            for r in l_rows
            if r["likert_status"] == "COMPARABLE" and r["likert_total"]
        ]
        p_usable = [
            float(r["program_weighted_total_100"])
            for r in l_rows
            if r["program_engineering_class"] == "USABLE"
            and r["program_weighted_total_100"]
        ]
        eng_fails = sorted(
            f"{r['model_display']}:{r['program_engineering_class']}"
            for r in l_rows
            if r["program_engineering_class"] != "USABLE"
        )

        case_rows.append(
            {
                "case_id": case_id,
                "n_tuning_steps": n_steps,
                "n_clean_220_steps": n_clean,
                "in_per_gold_step_count": n_pgs,
                "likert_row_count": len(l_rows),
                "likert_scored_count": len(l_scored),
                "likert_engineering_fail_models": ";".join(eng_fails) if eng_fails else "NONE",
                "is_route_gold_collision_case": case_id in collision_cases,
                "v14_t16_v6_hit1_steps": v6_h1_steps,
                "v14_t16_v6_hit3_steps": v6_h3_steps,
                "v14_t16_v6_hit5_steps": v6_h5_steps,
                "v14_t16_v6_hit1_rate": round(v6_h1_steps / n_steps, 4),
                "v14_t16_v6_hit3_rate": round(v6_h3_steps / n_steps, 4),
                "v14_t16_v6_hit5_rate": round(v6_h5_steps / n_steps, 4),
                "v14_t16_v4_hit1_steps": v4_h1_steps,
                "v14_t16_v4_hit3_steps": v4_h3_steps,
                "v14_t16_v4_hit5_steps": v4_h5_steps,
                "v14_t16_route_status_in_gold_exact_steps": in_gold_exact,
                "v14_t16_route_status_unresolved_ne_steps": unresolved_ne,
                "likert_v05_six_model_mean_total_ref": (
                    round(sum(l_scored) / len(l_scored), 2) if l_scored else "NONE"
                ),
                "program_v1_six_model_mean_total_ref": (
                    round(sum(p_usable) / len(p_usable), 2) if p_usable else "NONE"
                ),
            }
        )

    case_tsv = out_dir / "pathway_case_hitk_join_tuning76.tsv"
    case_fields = list(case_rows[0].keys())
    with case_tsv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=case_fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(case_rows)

    summary = {
        "arm_id": "v14_t16_wl4_pa_11p_at16_cons_v3_prom_adj",
        "caliber": "ppv1-criteria-v6",
        "n_qid_rows": len(qid_rows),
        "n_case_rows": len(case_rows),
        "in_per_gold_step_count": sum(
            1 for r in qid_rows if r["in_per_gold_step_public"] is True
        ),
        "missing_per_gold_step_qids": [
            r["qid"] for r in qid_rows if r["in_per_gold_step_public"] is False
        ],
        "likert_726_matched_cases": sum(
            1 for r in case_rows if int(r["likert_row_count"]) > 0
        ),
        "v4_reference_totals": {
            "tuning_261": {
                "hit@1": sum(int(r["v14_t16_v4_hit1"]) for r in qid_rows),
                "hit@3": sum(int(r["v14_t16_v4_hit3"]) for r in qid_rows),
                "hit@5": sum(int(r["v14_t16_v4_hit5"]) for r in qid_rows),
            },
            "clean_220": {
                "hit@1": sum(
                    int(r["v14_t16_v4_hit1"])
                    for r in qid_rows
                    if r["tuning_subset"] == "Clean-220"
                ),
                "hit@3": sum(
                    int(r["v14_t16_v4_hit3"])
                    for r in qid_rows
                    if r["tuning_subset"] == "Clean-220"
                ),
                "hit@5": sum(
                    int(r["v14_t16_v4_hit5"])
                    for r in qid_rows
                    if r["tuning_subset"] == "Clean-220"
                ),
            },
        },
        "tuning_261_summary": summarize_route_statuses(status_records),
        "clean_220_summary": summarize_route_statuses(clean_status_records),
    }

    summary_json = out_dir / "route_status_summary_tuning261.json"
    summary_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export v6 qid join & 5-state route_status summary.")
    parser.add_argument("--flips-jsonl", type=Path, required=True)
    parser.add_argument("--clean-classification-jsonl", type=Path, required=True)
    parser.add_argument("--per-gold-step-tsv", type=Path, required=True)
    parser.add_argument("--likert-scores-tsv", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--collision-audit-tsv", type=Path, default=None)
    parser.add_argument("--expert-reviews-json", type=Path, default=None)
    args = parser.parse_args(argv)

    summary = export_join_tables(
        flips_jsonl=args.flips_jsonl,
        clean_classification_jsonl=args.clean_classification_jsonl,
        per_gold_step_tsv=args.per_gold_step_tsv,
        likert_scores_tsv=args.likert_scores_tsv,
        out_dir=args.out_dir,
        collision_audit_tsv=args.collision_audit_tsv,
        expert_reviews_json=args.expert_reviews_json,
    )
    print(json.dumps({
        "n_qid_rows": summary["n_qid_rows"],
        "n_case_rows": summary["n_case_rows"],
        "route_status_counts": summary["tuning_261_summary"]["route_status_counts"],
        "primary_hit_at_k": summary["tuning_261_summary"]["primary_hit_at_k"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
