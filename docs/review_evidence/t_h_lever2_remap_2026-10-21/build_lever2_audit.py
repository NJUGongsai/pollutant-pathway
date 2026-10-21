#!/usr/bin/env python3
"""Build the 58-row lever-2 remap death-cause audit (metadata only).

Inputs (read-only):
  reports/ppv1_s5b/t_h_2026-10-20/r2/{metrics.json,p2_face_measure.json,batch_report.json}
  docs/review_evidence/t_h_r2_loss_attr_2026-10-20/r2_run_meta.json
  docs/review_evidence/t_h_p0_2026-10-20/p0d_supply_funnel.json
  new_candidate_meta.json / old_candidate_meta.json (from the sealed HPC batch manifests)

No reference_graphs, gold, questions, substrate SMILES, candidate SMILES, or
structure text is read or emitted. Candidate rows in the HPC schema carry only
channel/outcome/reason/route metadata, not structures.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
from pathlib import Path

ROOT = Path("/Volumes/CC/Enzyme_Agent/dependingv43")
R2 = ROOT / "reports/ppv1_s5b/t_h_2026-10-20/r2"
EV = ROOT / "docs/review_evidence/t_h_lever2_remap_2026-10-21"
LOSS_EV = ROOT / "docs/review_evidence/t_h_r2_loss_attr_2026-10-20"
P0_EV = ROOT / "docs/review_evidence/t_h_p0_2026-10-20"

CAT = {
    "no_alignment": "no_alignment",
    "no_compilable_alignment": "no_alignment",
    "mapping_enumeration_truncated": "enumeration_truncation",
    "alignment_limit_exceeded": "enumeration_truncation",
    "ambiguous_alignment": "enumeration_truncation",
    "ambiguous_mapping": "enumeration_truncation",
    "no_structure_correspondence": "element_mismatch",
    "product_set_mismatch": "element_mismatch",
    "product_component_identity_invalid": "element_mismatch",
    "partial_dearomatization_inconsistent": "element_mismatch",
    "center_empty": "element_mismatch",
}
PRI = {"element_mismatch": 4, "enumeration_truncation": 3, "no_alignment": 2, "other": 1}
F5_SHORT = {"reject": "rej", "defer": "def", "pass": "pass", "not_evaluated": "ne", "None": "none"}
FIX_BY_REASON = {
    "execution_failed": "可修",
    "new_atom_placement_incomplete": "可修",
    "transform_no_change": "可修",
    "charge_edit_unsupported": "需新契约",
    "stereo_edit_unsupported": "需新契约",
    "cosubstrate_bonded_contribution_unsupported": "需新契约",
    "aromatic_new_bond_unsupported": "需新契约",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cat_of(reason: str) -> str:
    return CAT.get(reason, "other")


def load_json(path: Path):
    with open(path) as f:
        return json.load(f)


def main() -> None:
    metrics = load_json(R2 / "metrics.json")
    p2 = load_json(R2 / "p2_face_measure.json")["by_qid"]
    batch = {c["qid"]: c for c in load_json(R2 / "batch_report.json")["cases"]}
    run_meta = load_json(LOSS_EV / "r2_run_meta.json")
    p0d = load_json(P0_EV / "p0d_supply_funnel.json")
    new_meta = load_json(EV / "new_candidate_meta.json")["by_qid"]
    old_meta = load_json(EV / "old_candidate_meta.json")["by_qid"]
    pq = {r["qid"]: r for r in metrics["per_qid"]}
    nm, om, runs = run_meta["new_manifest"], run_meta["old_manifest"], run_meta["runs"]
    idgate = set(run_meta["identity_gate_cop_qids"])
    no_recorded = set(p0d["by_qid"]["no_recorded_prefixes"])

    # --- set definitions (attribution-compatible) -------------------------
    s17 = sorted(q for q, v in p2.items() if v.get("remap", 0) > 0 and v.get("add", 0) == 0)

    def attribution_category(q):
        x = pq[q]
        status = x["main"]["match_status"]
        rank = x["main"].get("rank")
        mc = batch.get(q, {}).get("model_calls")
        npool = nm.get(q, {}).get("pool_size")
        if status == "matched_strict" and rank == 1:
            return "hit"
        if mc == 0:
            return "zero_call"
        if npool == 0:
            return "empty_pool"
        if status == "matched_strict" and isinstance(rank, int) and 2 <= rank <= 5:
            return "strict_rank_2_5"
        if status == "matched_strict" and isinstance(rank, int) and rank > 5:
            return "strict_rank_gt5"
        if status == "matched_participant_coverage_partial":
            return "partial"
        return "unmatched_other"

    s41 = sorted(
        q for q in pq
        if attribution_category(q) == "unmatched_other"
        and pq[q]["old"].get("anyof_rank") is None
        and q in p2
    )
    overlap = sorted(set(s17) & set(s41))
    union = sorted(set(s17) | set(s41))

    def top_reject(q):
        rows = new_meta[q]["candidates"]["rows"]
        rej = [r for r in rows if r["outcome"] == "compile_rejected" and r.get("reason")]
        single = collections.Counter(r["reason"] for r in rej)
        if not single:
            return None, 0, {}
        mx = max(single.values())
        tied = [r for r, v in single.items() if v == mx]
        top = max(tied, key=lambda r: (PRI.get(cat_of(r), 0), r))
        f5 = collections.Counter(str(r.get("f5")) for r in rej if r["reason"] == top)
        return top, single[top], dict(f5)

    def death_cause(q):
        # Identity gate: all 21 cop qids in this set carry identity-gate
        # rejections; the pool delta is recorded separately (9 x -1, 1 x 0).
        if q in idgate and new_meta[q]["candidates"]["by"]["reason"].get(
                "product_component_identity_invalid", 0) > 0:
            return "identity_gate"
        top, _, _ = top_reject(q)
        if top is None:
            return "other"
        return cat_of(top)

    def gate_fixability(q):
        cause = death_cause(q)
        if cause == "identity_gate":
            return "需新契约"
        if cause == "enumeration_truncation":
            return "可修"
        if cause == "no_alignment":
            return "需新契约"
        if cause == "element_mismatch":
            return "需新契约"
        if cause == "other":
            top, _, _ = top_reject(q)
            if top is None:
                return "unknown"
            return FIX_BY_REASON.get(top, "需新契约")
        return "unknown"

    def row_for(q, block):
        x = pq[q]
        n = new_meta[q]
        o = old_meta[q]
        rows = n["candidates"]["rows"]
        comp = [r for r in rows if r["outcome"] == "compiled"]
        comp_ch = collections.Counter(r["channel"] for r in comp)
        top, top_n, top_f5 = top_reject(q)
        cause = death_cause(q)
        status = x["main"]["match_status"]
        is_hit = status == "matched_strict" and x["main"].get("rank") == 1
        if is_hit:
            cause = "n/a (hit)"
        rr = runs.get(q, {})
        violated = sum((rr.get("audit_violated_reason_codes") or {}).values())
        return {
            "qid": q,
            "qid_prefix": q[:17],
            "block": block,
            "sets": "S17+S41" if (q in set(s17) and q in set(s41)) else block,
            "is_overlap": q in set(overlap),
            "remap": p2[q].get("remap"),
            "add": p2[q].get("add"),
            "v2_status": status,
            "v2_rank": x["main"].get("rank"),
            "is_hit": is_hit,
            "old_anyof_rank": x["old"].get("anyof_rank"),
            "old_n_candidates": x["old"].get("n_candidates"),
            "old_width_capped_products": x["old"].get("width_capped_products"),
            "old_pool": o.get("pool_size"),
            "new_pool": n.get("pool_size"),
            "pool_delta": (n.get("pool_size") or 0) - (o.get("pool_size") or 0),
            "compiled_new": len(comp),
            "compiled_new_channels": dict(comp_ch),
            "compiled_old": sum(1 for r in o["candidates"]["rows"] if r["outcome"] == "compiled"),
            "idgate": q in idgate,
            "identity_reject_n": n["candidates"]["by"]["reason"].get(
                "product_component_identity_invalid", 0),
            "p0d_no_recorded": q[:16] in no_recorded,
            "top_reject_reason": top,
            "top_reject_n": top_n,
            "top_reject_f5": top_f5,
            "top_reject_category": cat_of(top) if top else None,
            "reject_category_counts": dict(collections.Counter(
                cat_of(r["reason"]) for r in rows
                if r["outcome"] == "compile_rejected" and r.get("reason"))),
            "reject_reason_counts": dict(collections.Counter(
                r["reason"] for r in rows
                if r["outcome"] == "compile_rejected" and r.get("reason"))),
            "pool_truncated_n": sum(1 for r in rows if r["outcome"] == "pool_truncated"),
            "death_cause": cause,
            "fixability_gate": "n/a (hit)" if is_hit else gate_fixability(q),
            "fixability_qid": "n/a (hit@1)" if is_hit else "unknown",
            "decisive_stage": "survivor_hit" if is_hit else "post_compile_match_coverage",
            "native": {
                "events": rr.get("n_events"),
                "reportable": rr.get("n_reportable_products"),
                "novel": rr.get("outcome_model_novel_proposals"),
                "deferred": rr.get("n_deferred_entries"),
                "violated": violated,
                "method_failed": rr.get("method_failed_n"),
            },
        }

    rows58 = [row_for(q, "S17") for q in s17] + [row_for(q, "S41") for q in s41]
    for i, r in enumerate(rows58, 1):
        r["row_id"] = i

    unique_rows = {q: row_for(q, "S17" if q in set(s17) else "S41") for q in union}

    def count_by(rows, key):
        return dict(collections.Counter(r[key] for r in rows))

    loss58 = [r for r in rows58 if not r["is_hit"]]
    loss_unique = [r for r in unique_rows.values() if not r["is_hit"]]

    # --- secondary enumeration signals -----------------------------------
    width_qids = [q for q in union if (pq[q]["old"].get("width_capped_products") or 0) > 0]
    mapenum_qids = [q for q in union if new_meta[q]["candidates"]["by"]["reason"].get(
        "mapping_enumeration_truncated", 0) > 0]
    pooltrunc_qids = [q for q in union if any(
        r["outcome"] == "pool_truncated" for r in new_meta[q]["candidates"]["rows"])]

    reject_totals = collections.Counter()
    reject_by_cat = collections.Counter()
    for q in union:
        for r in new_meta[q]["candidates"]["rows"]:
            if r["outcome"] == "compile_rejected" and r.get("reason"):
                reject_totals[r["reason"]] += 1
                reject_by_cat[cat_of(r["reason"])] += 1

    summary = {
        "sets": {
            "S17_remap_only": len(s17),
            "S41_old_anyof_none_remap": len(s41),
            "overlap": len(overlap),
            "union_unique": len(union),
            "rows_58": len(rows58),
            "unique_loss_qids": len(loss_unique),
            "unique_hit_survivors": len(union) - len(loss_unique),
        },
        "status_counts": {
            "S17": dict(collections.Counter(pq[q]["main"]["match_status"] for q in s17)),
            "S41": dict(collections.Counter(pq[q]["main"]["match_status"] for q in s41)),
            "union": dict(collections.Counter(pq[q]["main"]["match_status"] for q in union)),
        },
        "death_cause": {
            "58_rows": count_by(rows58, "death_cause"),
            "57_loss_rows": count_by(loss58, "death_cause"),
            "51_unique": count_by(list(unique_rows.values()), "death_cause"),
            "50_unique_loss": count_by(loss_unique, "death_cause"),
        },
        "fixability_gate": {
            "58_rows": count_by(rows58, "fixability_gate"),
            "57_loss_rows": count_by(loss58, "fixability_gate"),
            "51_unique": count_by(list(unique_rows.values()), "fixability_gate"),
            "50_unique_loss": count_by(loss_unique, "fixability_gate"),
        },
        "fixability_qid": {
            "58_rows": count_by(rows58, "fixability_qid"),
            "57_loss_rows": count_by(loss58, "fixability_qid"),
        },
        "decisive_stage": {
            "58_rows": count_by(rows58, "decisive_stage"),
            "unique": count_by(list(unique_rows.values()), "decisive_stage"),
        },
        "identity_gate": {
            "unique_qids": len([q for q in union if q in idgate]),
            "rows_58": len([r for r in rows58 if r["idgate"]]),
            "pool_delta_minus1": len([q for q in union if q in idgate and
                                      (new_meta[q]["pool_size"] - old_meta[q]["pool_size"]) == -1]),
            "pool_delta_0": len([q for q in union if q in idgate and
                                 (new_meta[q]["pool_size"] - old_meta[q]["pool_size"]) == 0]),
            "identity_reject_total": sum(new_meta[q]["candidates"]["by"]["reason"].get(
                "product_component_identity_invalid", 0) for q in union if q in idgate),
        },
        "pool": {
            "unique_pool_new_dist": dict(collections.Counter(nm[q]["pool_size"] for q in union)),
            "unique_pool_old_dist": dict(collections.Counter(om[q]["pool_size"] for q in union)),
            "unique_pool_delta_dist": dict(collections.Counter(
                nm[q]["pool_size"] - om[q]["pool_size"] for q in union)),
            "unique_empty_new_pool": sum(1 for q in union if nm[q]["pool_size"] == 0),
            "unique_with_analog_compiled": sum(
                1 for q in union if any(r["outcome"] == "compiled" and r["channel"] == "analog"
                                        for r in new_meta[q]["candidates"]["rows"])),
            "unique_without_recorded_candidates": sum(
                1 for q in union if new_meta[q]["candidates"]["by"]["channel"].get("recorded", 0) == 0),
            "unique_without_corpus_candidates": sum(
                1 for q in union if new_meta[q]["candidates"]["by"]["channel"].get("corpus", 0) == 0),
        },
        "old_caliber": {
            "S41_old_anyof_none": len([q for q in s41 if pq[q]["old"].get("anyof_rank") is None]),
            "S41_old_n_candidates_min": min(pq[q]["old"].get("n_candidates") or 0 for q in s41),
            "S41_old_n_candidates_max": max(pq[q]["old"].get("n_candidates") or 0 for q in s41),
            "S41_old_n_candidates_zero": sum(1 for q in s41 if pq[q]["old"].get("n_candidates") == 0),
            "S41_width_capped": len([q for q in s41 if (pq[q]["old"].get("width_capped_products") or 0) > 0]),
            "S17_old_anyof_none": len([q for q in s17 if pq[q]["old"].get("anyof_rank") is None]),
            "S17_unmatched_with_old_none": len([
                q for q in s17 if pq[q]["main"]["match_status"] == "unmatched_required_node_uncovered"
                and pq[q]["old"].get("anyof_rank") is None]),
            "S17_unmatched_with_old_present": len([
                q for q in s17 if pq[q]["main"]["match_status"] == "unmatched_required_node_uncovered"
                and pq[q]["old"].get("anyof_rank") is not None]),
        },
        "secondary_enum": {
            "width_capped_unique_qids": len(width_qids),
            "width_capped_58_rows": len([r for r in rows58 if (r["old_width_capped_products"] or 0) > 0]),
            "mapping_enumeration_truncated_unique_qids": len(mapenum_qids),
            "pool_truncated_unique_qids": len(pooltrunc_qids),
            "pool_truncated_58_rows": len([r for r in rows58 if r["pool_truncated_n"] > 0]),
            "pool_truncated_candidate_rows": sum(
                sum(1 for r in new_meta[q]["candidates"]["rows"] if r["outcome"] == "pool_truncated")
                for q in union),
            "mapping_enumeration_candidate_rows": sum(
                new_meta[q]["candidates"]["by"]["reason"].get("mapping_enumeration_truncated", 0)
                for q in union),
            "width_capped_products_sum": sum(
                (pq[q]["old"].get("width_capped_products") or 0) for q in union),
            "any_enum_signal_unique_qids": len([
                q for q in union
                if new_meta[q]["candidates"]["by"]["reason"].get("mapping_enumeration_truncated", 0) > 0
                or any(r["outcome"] == "pool_truncated" for r in new_meta[q]["candidates"]["rows"])
                or (pq[q]["old"].get("width_capped_products") or 0) > 0]),
        },
        "native": {
            "completed": sum(1 for q in union if runs[q].get("endpoint_execution_status") == "completed"),
            "model_calls_1": sum(1 for q in union if batch[q].get("model_calls") == 1),
            "events_dist": dict(collections.Counter(runs[q]["n_events"] for q in union)),
            "method_failed_qids": [q[:17] for q in union if runs[q].get("method_failed_n")],
            "audit_violated_qids": [q[:17] for q in union if runs[q].get("audit_violated_reason_codes")],
            "run_error_nonempty": [q[:17] for q in union if (runs[q].get("run_error") or {}).get("kind")],
        },
        "p0d": {
            "unique_in_no_recorded_prefixes": sum(1 for q in union if q[:16] in no_recorded),
            "no_recorded_anchor_193": len(no_recorded),
            "candidate_rows": p0d["denominators"]["candidate_rows_in_manifest"],
            "compiled": p0d["reason_compatibility"]["candidate_outcomes"]["compiled"],
            "compile_rejected": p0d["reason_compatibility"]["candidate_outcomes"]["compile_rejected"],
            "no_alignment_total": p0d["no_alignment_split"]["candidates_total"],
            "no_alignment_f5_reject": p0d["no_alignment_split"]["f5_pregate_reject"],
            "no_alignment_f5_defer_compiler": p0d["no_alignment_split"]["compiler_after_f5_defer"],
            "no_alignment_not_f5": p0d["no_alignment_split"]["compiler_or_not_f5_applicable"],
        },
        "reject_totals_51_unique": dict(reject_totals),
        "reject_category_totals_51_unique": dict(reject_by_cat),
    }

    # --- provenance -------------------------------------------------------
    source_files = [
        R2 / "metrics.json",
        R2 / "p2_face_measure.json",
        R2 / "batch_report.json",
        LOSS_EV / "r2_run_meta.json",
        P0_EV / "p0d_supply_funnel.json",
        EV / "new_candidate_meta.json",
        EV / "old_candidate_meta.json",
    ]
    provenance = {
        "batch_tag": "t_h_s5b_298_20261020r2",
        "domain_tag": "298=RHEA 通用酶学/已见题；本审计不外推",
        "nature": "只读诊断；零模型调用、零新批次、零金标/reference_graphs 内容、零结构正文输出",
        "local_source_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in source_files},
        "hpc_read_only_sha256": {
            "~/ppv1_hpc/batch/t_h_s5b_298_20261020r2/batch_manifest.json":
                "640249d087be61b7725b4aa3d940aad664733d43831841ae7b43815f53c1006e",
            "~/ppv1_hpc/batch/t_h_s5b_298_20261020/batch_manifest.json":
                "773228e17f730bfaf04c18bc1c1af13d14f1a434efae8a5aa3409fcc1be68966",
            "~/ppv1_hpc/batch/t_h_s5b_298_20261020/degenerate_fragment_face_v2.json":
                "4b344e49dab6789d7420adeac4d675c7ac2c27067ff75a05bef0eb040e678cf0",
            "~/ppv1_hpc/batch/t_h_s5b_298_20261020r2/build_identity.json":
                "49a1d86a02ce9182a90a3fb5b7535bda28d59f7aa51d2662ca4bd7bda41583e2",
        },
        "definitions": {
            "S17": "p2_face_measure.by_qid[q].remap>0 and add==0",
            "S41": "attribution category unmatched_nonempty_other AND old.anyof_rank=None AND q in p2 remap face",
            "overlap": "S17 ∩ S41",
            "dominant_gate": "identity_gate if q in 21 cop qids and product_component_identity_invalid>0; else category of the single largest compile_rejected reason (tie: element_mismatch > enumeration_truncation > no_alignment > other)",
            "decisive_stage": "post_compile_match_coverage if new pool>0; survivor_hit if v2 strict rank1",
            "fixability_gate": "gate-level triage only; not a hit-recovery promise",
            "fixability_qid": "unknown for every loss row because all pools are non-empty and there is no same-question A/B",
        },
        "unknown": [
            "候选级/事件级金标匹配：无逐候选正确性，不能证明哪条候选被误拒",
            "remap 化学有效性：p2_face_measure 只是披露分母，不是化学判据",
            "同题非 remap 对照/A-B：因果 unknown，只能给关联",
            "身份门拒绝的那 1 条 spec 是否含正确候选：unknown",
            "old width_cap 是否切掉了正确产物：unknown",
            "把主拒因修掉后 hit@1 能回收多少：unknown（无收益估计）",
        ],
    }

    out = {
        "provenance": provenance,
        "sets": {"S17": s17, "S41": s41, "overlap": overlap, "union": union},
        "summary": summary,
        "rows_58": rows58,
        "unique_rows": list(unique_rows.values()),
    }
    with open(EV / "lever2_remap_audit.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # --- markdown table ---------------------------------------------------
    def oldanyof(r):
        return "None" if r["old_anyof_rank"] is None else str(r["old_anyof_rank"])

    def chan(r):
        c = r["compiled_new_channels"]
        parts = []
        for k in ("analog", "recorded", "corpus"):
            if c.get(k):
                parts.append(f"{k[0]}{c[k]}")
        return f"{r['compiled_new']}(" + ",".join(parts) + ")"

    def f5(r):
        if not r["top_reject_reason"]:
            return "—"
        parts = []
        for k in ("reject", "defer", "pass", "not_evaluated", "None"):
            v = r["top_reject_f5"].get(k, 0)
            if v:
                parts.append(f"{F5_SHORT[k]}{v}")
        return "/".join(parts)

    def idg(r):
        if not r["idgate"]:
            return "—"
        return f"Y({r['pool_delta']:+d};id{r['identity_reject_n']})"

    def top(r):
        if not r["top_reject_reason"]:
            return "无拒因"
        return f"`{r['top_reject_reason']}×{r['top_reject_n']}` [{f5(r)}]"

    def nat(r):
        n = r["native"]
        p0 = "nr1" if r["p0d_no_recorded"] else "nr0"
        return f"{n['events']}/{n['reportable']}/{n['novel']}/{n['violated']}/{n['method_failed']};{p0}"

    lines = [
        "| # | qid前缀 | 集合 | v2状态 | old anyof/n | width | pool o→n | compiled new | 主拒因(条数; f5) | 死因类 | 身份门 | 可修性(拒因层) | 决定性环节 | native e/r/n/v/m;P0D |",
        "|---:|---|---|---|---:|---:|---|---:|---|---|---|---|---|---|",
    ]
    status_short = {
        "matched_strict": "strict",
        "matched_participant_coverage_partial": "partial",
        "unmatched_required_node_uncovered": "unmatched",
    }
    for r in rows58:
        status = status_short.get(r["v2_status"], r["v2_status"])
        if r["v2_rank"]:
            status += f" r{r['v2_rank']}"
        lines.append(
            f"| {r['row_id']} | `{r['qid_prefix']}` | {r['sets']} | {status} | "
            f"{oldanyof(r)}/{r['old_n_candidates']} | {r['old_width_capped_products'] or 0} | "
            f"{r['old_pool']}→{r['new_pool']} | {chan(r)} | {top(r)} | **{r['death_cause']}** | "
            f"{idg(r)} | {r['fixability_gate']} | {r['decisive_stage']} | {nat(r)} |"
        )
    (EV / "table_58.md").write_text("\n".join(lines) + "\n")

    # --- human summary ----------------------------------------------------
    s = summary
    txt = [
        "T-H lever2 remap audit summary (metadata only)",
        f"sets: {s['sets']}",
        f"death_cause 58 rows: {s['death_cause']['58_rows']}",
        f"death_cause 57 loss rows: {s['death_cause']['57_loss_rows']}",
        f"death_cause 51 unique: {s['death_cause']['51_unique']}",
        f"death_cause 50 unique loss: {s['death_cause']['50_unique_loss']}",
        f"fixability_gate 57 loss rows: {s['fixability_gate']['57_loss_rows']}",
        f"fixability_gate 50 unique loss: {s['fixability_gate']['50_unique_loss']}",
        f"fixability_qid 57 loss rows: {s['fixability_qid']['57_loss_rows']}",
        f"identity_gate: {s['identity_gate']}",
        f"pool: {s['pool']}",
        f"old_caliber: {s['old_caliber']}",
        f"secondary_enum: {s['secondary_enum']}",
        f"native: {s['native']}",
        f"p0d: {s['p0d']}",
    ]
    (EV / "summary.txt").write_text("\n".join(txt) + "\n")
    print("wrote", EV / "lever2_remap_audit.json")
    print("wrote", EV / "table_58.md")
    print("wrote", EV / "summary.txt")
    print(json.dumps(s["sets"], ensure_ascii=False))
    print(json.dumps(s["death_cause"]["58_rows"], ensure_ascii=False))
    print(json.dumps(s["fixability_gate"]["57_loss_rows"], ensure_ascii=False))


if __name__ == "__main__":
    main()