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


T1_0_COLUMN_NAMES: tuple[str, ...] = (
    "t1_0_v6_rank",
    "t1_0_v6_hit1",
    "t1_0_v6_hit3",
    "t1_0_v6_hit5",
    "t1_0_v4_hit1",
    "t1_0_v4_hit3",
    "t1_0_v4_hit5",
)

T1_0A_COLUMN_NAMES: tuple[str, ...] = (
    "t1_0a_delivery_status",
    "t1_0a_v6_rank",
    "t1_0a_v6_hit1",
    "t1_0a_v6_hit3",
    "t1_0a_v6_hit5",
    "t1_0a_v4_rank",
    "t1_0a_v4_hit1",
    "t1_0a_v4_hit3",
    "t1_0a_v4_hit5",
)


def _validate_qid_alignment(
    expected_qids: set[str],
    actual_qids: set[str],
    *,
    label: str,
) -> None:
    """Verify two qid sets match 1-to-1 before merging columns."""
    if expected_qids == actual_qids:
        return
    missing = sorted(expected_qids - actual_qids)
    extra = sorted(actual_qids - expected_qids)
    raise ValueError(
        f"{label} qid mismatch: missing={len(missing)} ({missing[:3]}), "
        f"extra={len(extra)} ({extra[:3]})"
    )


def _load_t1_0_raw_score(path: Path | None) -> dict[str, dict[str, object]]:
    """Load T1-0 bare raw_score.json per_qid records keyed by qid."""
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("per_qid")
    if not isinstance(records, list) or not records:
        raise ValueError(f"Missing or invalid per_qid list in {path}")
    by_qid: dict[str, dict[str, object]] = {}
    for item in records:
        qid = str(item["qid"])
        if qid in by_qid:
            raise ValueError(f"Duplicate qid {qid!r} in {path}")
        rank = item.get("rank")
        for k in (1, 3, 5):
            rank_hit = rank is not None and int(rank) <= k
            if rank_hit != bool(item[f"v6_hit_at_{k}"]):
                raise ValueError(
                    f"{path} rank/v6_hit_at_{k} inconsistency for {qid}: "
                    f"rank={rank}, flag={item[f'v6_hit_at_{k}']}"
                )
        by_qid[qid] = item
    return by_qid


def _load_flips_by_qid(path: Path | None) -> dict[str, dict[str, object]]:
    """Load a flips_v4cn JSONL artifact keyed by qid."""
    if path is None:
        return {}
    by_qid: dict[str, dict[str, object]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        qid = str(item["qid"])
        if qid in by_qid:
            raise ValueError(f"Duplicate qid {qid!r} in {path}")
        by_qid[qid] = item
    if not by_qid:
        raise ValueError(f"Empty flips JSONL: {path}")
    return by_qid


def _t1_0_columns(row: dict[str, object]) -> dict[str, object]:
    """Extract normalized T1-0 bare (raw SMILES, no AtomTool gate) columns."""
    rank = row.get("rank")
    return {
        "t1_0_v6_rank": rank if rank is not None else "NONE",
        "t1_0_v6_hit1": int(bool(row["v6_hit_at_1"])),
        "t1_0_v6_hit3": int(bool(row["v6_hit_at_3"])),
        "t1_0_v6_hit5": int(bool(row["v6_hit_at_5"])),
        "t1_0_v4_hit1": int(bool(row["v4_hit_at_1"])),
        "t1_0_v4_hit3": int(bool(row["v4_hit_at_3"])),
        "t1_0_v4_hit5": int(bool(row["v4_hit_at_5"])),
    }


def _t1_0a_columns(row: dict[str, object]) -> dict[str, object]:
    """Extract normalized T1-0a (bare + AtomTool gate) columns from flips JSONL."""
    after_rank = row.get("after_rank")
    before_rank = row.get("before_rank")
    delivery = (
        DeliveryStatus.NO_EVENT.value
        if row.get("after_bucket") == "unmatched_no_event"
        else DeliveryStatus.OK.value
    )
    v6_h1, v6_h3, v6_h5 = _hit_flags(after_rank)
    v4_h1, v4_h3, v4_h5 = _hit_flags(before_rank)
    return {
        "t1_0a_delivery_status": delivery,
        "t1_0a_v6_rank": after_rank if after_rank is not None else "NONE",
        "t1_0a_v6_hit1": v6_h1,
        "t1_0a_v6_hit3": v6_h3,
        "t1_0a_v6_hit5": v6_h5,
        "t1_0a_v4_rank": before_rank if before_rank is not None else "NONE",
        "t1_0a_v4_hit1": v4_h1,
        "t1_0a_v4_hit3": v4_h3,
        "t1_0a_v4_hit5": v4_h5,
    }


def _summarize_hitk_columns(
    rows: list[dict[str, object]],
    *,
    prefix: str,
    has_delivery_status: bool = False,
) -> dict[str, object]:
    """Compute Tuning-261 and Clean-220 Hit@1/@3/@5 totals for an arm prefix."""
    clean_rows = [r for r in rows if r["tuning_subset"] == "Clean-220"]

    def _bucket_counts(subset: list[dict[str, object]]) -> dict[str, dict[str, int]]:
        return {
            caliber: {
                f"hit@{k}": sum(int(r[f"{prefix}_{caliber}_hit{k}"]) for r in subset)
                for k in (1, 3, 5)
            }
            for caliber in ("v6", "v4")
        }

    result: dict[str, object] = {
        "tuning_261": {"denominator": len(rows), **_bucket_counts(rows)},
        "clean_220": {"denominator": len(clean_rows), **_bucket_counts(clean_rows)},
    }
    if has_delivery_status:
        result["no_event_count"] = sum(
            1 for r in rows if r.get(f"{prefix}_delivery_status") == DeliveryStatus.NO_EVENT.value
        )
    return result


def export_join_tables(
    *,
    flips_jsonl: Path,
    clean_classification_jsonl: Path,
    per_gold_step_tsv: Path,
    likert_scores_tsv: Path,
    out_dir: Path,
    collision_audit_tsv: Path | None = None,
    expert_reviews_json: Path | None = None,
    t1_0_raw_score_json: Path | None = None,
    t1_0a_flips_jsonl: Path | None = None,
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
    t1_0_map = _load_t1_0_raw_score(t1_0_raw_score_json)
    t1_0a_map = _load_flips_by_qid(t1_0a_flips_jsonl)
    flips_qids = {str(r["qid"]) for r in flips}
    if t1_0_map:
        _validate_qid_alignment(flips_qids, set(t1_0_map), label="t1_0_raw_score")
    if t1_0a_map:
        _validate_qid_alignment(flips_qids, set(t1_0a_map), label="t1_0a_flips")

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
        if t1_0_map:
            out_row.update(_t1_0_columns(t1_0_map[qid]))
        if t1_0a_map:
            out_row.update(_t1_0a_columns(t1_0a_map[qid]))
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
    if t1_0_map or t1_0a_map:
        summary["extra_arms"] = _build_extra_arms_summary(
            qid_rows,
            include_t1_0=bool(t1_0_map),
            include_t1_0a=bool(t1_0a_map),
        )

    summary_json = out_dir / "route_status_summary_tuning261.json"
    summary_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary


def _build_extra_arms_summary(
    rows: list[dict[str, object]],
    *,
    include_t1_0: bool,
    include_t1_0a: bool,
) -> dict[str, object]:
    """Summarize extra baseline arms cleanly without duplicating totals logic."""
    arms: dict[str, object] = {}
    if include_t1_0:
        arms["t1_0"] = _summarize_hitk_columns(rows, prefix="t1_0")
    if include_t1_0a:
        arms["t1_0a"] = _summarize_hitk_columns(
            rows, prefix="t1_0a", has_delivery_status=True
        )
    return arms


def append_baseline_arms_to_qid_tsv(
    *,
    qid_tsv: Path,
    t1_0_raw_score_json: Path | None = None,
    t1_0a_flips_jsonl: Path | None = None,
    out_tsv: Path | None = None,
) -> dict[str, object]:
    """Append or refresh T1-0 / T1-0a columns on an existing Tuning-261 qid TSV."""
    if t1_0_raw_score_json is None and t1_0a_flips_jsonl is None:
        raise ValueError("Provide at least one of t1_0_raw_score_json or t1_0a_flips_jsonl.")

    with qid_tsv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        existing_fields = list(reader.fieldnames or [])
        rows: list[dict[str, object]] = [dict(row) for row in reader]

    if not existing_fields or not rows:
        raise ValueError(f"Existing qid TSV is empty: {qid_tsv}")

    row_qids = {str(r["qid"]) for r in rows}
    t1_0_map = _load_t1_0_raw_score(t1_0_raw_score_json)
    t1_0a_map = _load_flips_by_qid(t1_0a_flips_jsonl)
    if t1_0_map:
        _validate_qid_alignment(row_qids, set(t1_0_map), label="t1_0_raw_score")
    if t1_0a_map:
        _validate_qid_alignment(row_qids, set(t1_0a_map), label="t1_0a_flips")

    has_t1_0 = bool(t1_0_map) or all(c in existing_fields for c in T1_0_COLUMN_NAMES)
    has_t1_0a = bool(t1_0a_map) or all(c in existing_fields for c in T1_0A_COLUMN_NAMES)
    extra_set = set(T1_0_COLUMN_NAMES) | set(T1_0A_COLUMN_NAMES)
    base_fields = [c for c in existing_fields if c not in extra_set]
    out_fields = list(base_fields)
    if has_t1_0:
        out_fields.extend(T1_0_COLUMN_NAMES)
    if has_t1_0a:
        out_fields.extend(T1_0A_COLUMN_NAMES)

    for row in rows:
        qid = str(row["qid"])
        if t1_0_map:
            row.update(_t1_0_columns(t1_0_map[qid]))
        if t1_0a_map:
            row.update(_t1_0a_columns(t1_0a_map[qid]))

    target_tsv = out_tsv or qid_tsv
    with target_tsv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    return {
        "out_tsv": str(target_tsv),
        "n_qid_rows": len(rows),
        "n_columns": len(out_fields),
        "added_or_refreshed_columns": [
            *(T1_0_COLUMN_NAMES if t1_0_map else ()),
            *(T1_0A_COLUMN_NAMES if t1_0a_map else ()),
        ],
        "extra_arms": _build_extra_arms_summary(
            rows,
            include_t1_0=has_t1_0,
            include_t1_0a=has_t1_0a,
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export v6 qid join & 5-state route_status summary.")
    parser.add_argument("--flips-jsonl", type=Path, default=None)
    parser.add_argument("--clean-classification-jsonl", type=Path, default=None)
    parser.add_argument("--per-gold-step-tsv", type=Path, default=None)
    parser.add_argument("--likert-scores-tsv", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--collision-audit-tsv", type=Path, default=None)
    parser.add_argument("--expert-reviews-json", type=Path, default=None)
    parser.add_argument("--t1-0-raw-score-json", type=Path, default=None)
    parser.add_argument("--t1-0a-flips-jsonl", type=Path, default=None)
    parser.add_argument("--patch-existing-qid-tsv", type=Path, default=None)
    parser.add_argument("--out-tsv", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.patch_existing_qid_tsv is not None:
        if args.t1_0_raw_score_json is None and args.t1_0a_flips_jsonl is None:
            parser.error(
                "--patch-existing-qid-tsv requires at least one of "
                "--t1-0-raw-score-json or --t1-0a-flips-jsonl"
            )
        summary = append_baseline_arms_to_qid_tsv(
            qid_tsv=args.patch_existing_qid_tsv,
            t1_0_raw_score_json=args.t1_0_raw_score_json,
            t1_0a_flips_jsonl=args.t1_0a_flips_jsonl,
            out_tsv=args.out_tsv,
        )
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    required_full = (
        ("--flips-jsonl", args.flips_jsonl),
        ("--clean-classification-jsonl", args.clean_classification_jsonl),
        ("--per-gold-step-tsv", args.per_gold_step_tsv),
        ("--likert-scores-tsv", args.likert_scores_tsv),
        ("--out-dir", args.out_dir),
    )
    missing = [flag for flag, val in required_full if val is None]
    if missing:
        parser.error(f"Missing required arguments for full export: {', '.join(missing)}")

    summary = export_join_tables(
        flips_jsonl=args.flips_jsonl,
        clean_classification_jsonl=args.clean_classification_jsonl,
        per_gold_step_tsv=args.per_gold_step_tsv,
        likert_scores_tsv=args.likert_scores_tsv,
        out_dir=args.out_dir,
        collision_audit_tsv=args.collision_audit_tsv,
        expert_reviews_json=args.expert_reviews_json,
        t1_0_raw_score_json=args.t1_0_raw_score_json,
        t1_0a_flips_jsonl=args.t1_0a_flips_jsonl,
    )
    print(json.dumps({
        "n_qid_rows": summary["n_qid_rows"],
        "n_case_rows": summary["n_case_rows"],
        "route_status_counts": summary["tuning_261_summary"]["route_status_counts"],
        "primary_hit_at_k": summary["tuning_261_summary"]["primary_hit_at_k"],
        **({"extra_arms": summary["extra_arms"]} if "extra_arms" in summary else {}),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
