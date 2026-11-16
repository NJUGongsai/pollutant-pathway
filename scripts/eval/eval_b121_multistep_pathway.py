#!/usr/bin/env python3
"""Phase 1 Multi-Step Reaction Pathway Capability Evaluation on [biosysmodb121·调参集].

Strictly evaluates ONLY the 76 tuning pathways (261 reaction steps) defined in
`reports/ppv1_s5b/holdout_v1/b121/dev_qids.txt`.
Zero LLM calls; zero access to the 43 holdout pathways (156 steps).
Public outputs contain zero `BIOPATH150_xxx` IDs, zero `BSY-rxxxx` IDs, and zero SMILES.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pathway_v43.pollutant.chemstate import strict_identity_of  # noqa: E402

DEV_QIDS_PATH = REPO_ROOT / "reports/ppv1_s5b/holdout_v1/b121/dev_qids.txt"
HOLDOUT_QIDS_PATH = REPO_ROOT / "reports/ppv1_s5b/holdout_v1/b121/holdout_qids.txt"
TUNING_QUESTIONS_PATH = (
    REPO_ROOT / "reports/ppv1_s5b/v44_next_tuning_20261110/questions_b121_tuning.jsonl"
)
B1A_STEP_QUERIES_PATH = (
    REPO_ROOT
    / "reports/ppv1_s5b/b121_full_20261103/biosysmodb121/work/B1/out/step_queries.tsv"
)

# 4 self-record QIDs in [biosysmodb121·调参集] identified by compliance audit
SELF_RECORD_QIDS = {
    "BIOPATH150_007__S04__BSY-r00050",
    "BIOPATH150_007__S08__BSY-r00054",
    "BIOPATH150_029__S02__BSY-r00140",
    "BIOPATH150_098__S01__BSY-r00657",
}

PUBLIC_JSON_OUT = (
    REPO_ROOT
    / "docs/reviews/evidence/b121_multistep_eval_2026-11-11/b121_multistep_tuning_summary.json"
)
PRIVATE_TSV_OUT = (
    REPO_ROOT
    / "reports/manual_review/b121_multistep_eval_2026-11-11/per_pathway_tuning_detail.tsv"
)


def _parse_int_or_none(val: Any) -> int | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s == "None":
        return None
    return int(s)


def load_tuning_qids_and_topology() -> tuple[list[str], dict[str, dict[str, Any]], dict[str, list[str]]]:
    """Load the 261 tuning QIDs, verify zero holdout overlap, and join B1a topology."""
    dev_qids = sorted(DEV_QIDS_PATH.read_text(encoding="utf-8").split())
    holdout_qids = set(HOLDOUT_QIDS_PATH.read_text(encoding="utf-8").split())
    assert len(dev_qids) == 261, f"Expected 261 dev_qids, got {len(dev_qids)}"
    assert len(set(dev_qids) & holdout_qids) == 0, "Holdout QID overlap detected!"

    dev_cases = {q.split("__")[0] for q in dev_qids}
    holdout_cases = {q.split("__")[0] for q in holdout_qids}
    assert len(dev_cases) == 76, f"Expected 76 tuning cases, got {len(dev_cases)}"
    assert len(dev_cases & holdout_cases) == 0, "Holdout case_id overlap detected!"

    # Load tuning questions
    questions_by_qid: dict[str, dict[str, Any]] = {}
    with open(TUNING_QUESTIONS_PATH, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                obj = json.loads(line)
                if obj["qid"] in set(dev_qids):
                    questions_by_qid[obj["qid"]] = obj
    assert len(questions_by_qid) == 261

    # Load B1a step_queries.tsv ONLY for the 261 tuning QIDs
    b1a_by_qid: dict[str, dict[str, Any]] = {}
    with open(B1A_STEP_QUERIES_PATH, encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            qid = row["step_occurrence_id"]
            if qid in questions_by_qid:
                b1a_by_qid[qid] = row
    assert len(b1a_by_qid) == 261

    # Compute offline pool GIP@8 (S0') and GIP@16 (v44-Next)
    s0_flags_path = (
        REPO_ROOT
        / "reports/manual_review/strong_model_probe_2026-11-09/per_qid_flags_b121_f_ds.tsv"
    )
    s0_gip: dict[str, bool] = {}
    s0_pool_size: dict[str, int] = {}
    with open(s0_flags_path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            q = row["qid"]
            if q in questions_by_qid:
                s0_gip[q] = row["gip_rb"] == "True"
                s0_pool_size[q] = int(row["pool_size"])

    v44_batch_dir = (
        REPO_ROOT
        / "reports/ppv1_s5b/v44_next_v1_1_tuning_20261110/batch_b121_tuning_v44next"
    )
    v44_gip_rb: dict[str, bool] = {}
    v44_gip_ra: dict[str, bool] = {}
    v44_pool_size: dict[str, int] = {}
    for q in dev_qids:
        qobj = questions_by_qid[q]
        gold_ids = {
            strict_identity_of(p)
            for p in qobj["products_smiles"]
            if strict_identity_of(p)
        }
        ri = json.load(open(v44_batch_dir / "run_inputs" / f"{q}.json", encoding="utf-8"))
        specs = [sp for plist in ri["plan"]["pools"].values() for sp in plist]
        v44_pool_size[q] = len(specs)
        hit_rb = False
        hit_ra = False
        for sp in specs[:16]:
            ps = sp.get("product_smiles", "")
            cp = sp.get("coproducts", [])
            pid = strict_identity_of(ps) if ps else None
            if pid and gold_ids and gold_ids.issubset({pid}):
                hit_rb = True
            all_p = {
                strict_identity_of(x)
                for x in ([ps] + cp)
                if x and strict_identity_of(x)
            }
            if gold_ids and gold_ids.issubset(all_p):
                hit_ra = True
        v44_gip_rb[q] = hit_rb
        v44_gip_ra[q] = hit_ra

    # Group steps into 76 pathways ordered by S-index
    pathways_steps: dict[str, list[str]] = defaultdict(list)
    for q in dev_qids:
        cid = q.split("__")[0]
        pathways_steps[cid].append(q)
    for cid in pathways_steps:
        pathways_steps[cid].sort(key=lambda x: int(x.split("__")[1][1:]))

    step_meta: dict[str, dict[str, Any]] = {}
    for cid, qlist in pathways_steps.items():
        for seq_idx, q in enumerate(qlist, 1):
            b1 = b1a_by_qid[q]
            s_label = q.split("__")[1]
            s_num = int(s_label[1:])
            preds = [p for p in b1["predecessor_step_ids"].split("|") if p]
            succs = [s for s in b1["successor_step_ids"].split("|") if s]
            step_meta[q] = {
                "qid": q,
                "case_id": cid,
                "s_label": s_label,
                "s_num": s_num,
                "seq_pos": seq_idx,
                "pathway_eval_len": len(qlist),
                "ordered_step_count": int(b1["ordered_step_count"]),
                "final_graph_status": b1["final_graph_status"],
                "topological_level": int(b1["topological_level"]),
                "branch_id": int(b1["branch_id"]),
                "predecessor_step_ids": preds,
                "successor_step_ids": succs,
                "all_preds_in_dev": all(p in set(qlist) for p in preds),
                "is_self_record": q in SELF_RECORD_QIDS,
                "s0_gip_at_8": s0_gip[q],
                "s0_pool_size": s0_pool_size[q],
                "v44next_gip_at_16_rb": v44_gip_rb[q],
                "v44next_gip_at_16_ra": v44_gip_ra[q],
                "v44next_pool_size": v44_pool_size[q],
            }

    return dev_qids, step_meta, dict(pathways_steps)


def load_all_arms_per_qid(
    dev_qids: list[str], step_meta: dict[str, dict[str, Any]]
) -> dict[str, dict[str, dict[str, Any]]]:
    """Load per-QID ranks and diagnostic flags for all experimental arms on the 261 tuning steps."""
    dev_set = set(dev_qids)
    arms: dict[str, dict[str, dict[str, Any]]] = {}

    # 1. Permanent_v4_Baseline
    agg_path = REPO_ROOT / "reports/ppv1_s5b/b121_417_20261030/c_v4_v4impl/aggregate.json"
    agg = json.load(open(agg_path, encoding="utf-8"))
    perm_map: dict[str, dict[str, Any]] = {}
    for entry in agg["per_qid"]:
        q = entry["qid"]
        if q not in dev_set:
            continue
        v4_rank = entry["product_hit"]["rank"]
        v4_any = bool(entry["product_hit"]["matched_product_hit"])
        v2_rank = entry["main"]["rank"]
        old_rank = entry["old"]["rank"]
        perm_map[q] = {
            "v4_rank": v4_rank,
            "v4_hit_any": v4_any,
            # Permanent_v4_Baseline predates v5 role_bound_product_hit; store v4_rank for structural parity where needed, mark v5_available=False
            "v5_rank": None,
            "v5_available": False,
            "v2_rank": v2_rank,
            "old_cn_hit": old_rank is not None,
            "gip": step_meta[q]["s0_gip_at_8"],
            "wrote_gold": False,
        }
    arms["Permanent_v4_Baseline"] = perm_map

    # 2. Exp1b_Arm_A, 3. SMP_F_ds, 4. SMP_M_qw
    smp_priv = json.load(
        open(
            REPO_ROOT
            / "reports/manual_review/strong_model_probe_2026-11-09/strong_model_probe_private_qids_b121.json",
            encoding="utf-8",
        )
    )["per_qid_arm_records_tune"]

    tsv_configs = [
        (
            "Exp1b_Arm_A",
            REPO_ROOT
            / "reports/manual_review/exp1b_product_first_feedback_2026-11-08/per_qid_flags_b121_a.tsv",
            None,
        ),
        (
            "SMP_F_ds",
            REPO_ROOT
            / "reports/manual_review/strong_model_probe_2026-11-09/per_qid_flags_b121_f_ds.tsv",
            smp_priv["f_ds"],
        ),
        (
            "SMP_M_qw",
            REPO_ROOT
            / "reports/manual_review/strong_model_probe_2026-11-09/per_qid_flags_b121_m_qw.tsv",
            smp_priv["m_qw"],
        ),
    ]
    for arm_name, tsv_path, priv_records in tsv_configs:
        amap: dict[str, dict[str, Any]] = {}
        with open(tsv_path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                q = row["qid"]
                if q not in dev_set:
                    continue
                v4_rank = _parse_int_or_none(row["rank_rb"])
                v5_rank = _parse_int_or_none(row["rank_ra"])
                v2_rank = _parse_int_or_none(row["V2_rank_role_blind"])
                cn_hit = row["cn_any"] == "True" or row["stereo_blind_any"] == "True"
                wrote_gold = bool(priv_records[q]["wrote_gold_rb"]) if priv_records else False
                amap[q] = {
                    "v4_rank": v4_rank,
                    "v4_hit_any": v4_rank is not None,
                    "v5_rank": v5_rank,
                    "v5_available": True,
                    "v2_rank": v2_rank,
                    "old_cn_hit": cn_hit,
                    "gip": step_meta[q]["s0_gip_at_8"],
                    "wrote_gold": wrote_gold,
                }
        arms[arm_name] = amap

    # 5. v44_Next_v1_0, 6. v44_Next_v1_1, 7. v44_Next_v1_2
    v44_configs = [
        (
            "v44_Next_v1_0",
            REPO_ROOT
            / "reports/ppv1_s5b/v44_next_tuning_20261110/batch_b121_tuning_v44next",
        ),
        (
            "v44_Next_v1_1",
            REPO_ROOT
            / "reports/ppv1_s5b/v44_next_v1_1_tuning_20261110/batch_b121_tuning_v44next",
        ),
        (
            "v44_Next_v1_2",
            REPO_ROOT
            / "reports/ppv1_s5b/v44_next_v1_2_tuning_20261110/batch_b121_tuning_v44next_v12",
        ),
    ]
    for arm_name, bdir in v44_configs:
        m4 = {
            x["qid"]: x
            for x in json.load(open(bdir / "metrics_v4.json", encoding="utf-8"))["per_qid"]
            if x["qid"] in dev_set
        }
        m5 = {
            x["qid"]: x
            for x in json.load(open(bdir / "metrics_v5.json", encoding="utf-8"))["per_qid"]
            if x["qid"] in dev_set
        }
        m2 = {
            x["qid"]: x
            for x in json.load(open(bdir / "metrics_v2.json", encoding="utf-8"))["per_qid"]
            if x["qid"] in dev_set
        }
        amap = {}
        for q in dev_qids:
            v4_rank = m4[q]["product_hit"]["rank"]
            v5_rank = m5[q]["role_bound_hit"]["rank"]
            v2_rank = m2[q]["main"]["rank"]
            old_rank = m4[q]["old"]["rank"]
            amap[q] = {
                "v4_rank": v4_rank,
                "v4_hit_any": bool(m4[q]["product_hit"]["matched_product_hit"]),
                "v5_rank": v5_rank,
                "v5_available": True,
                "v2_rank": v2_rank,
                "old_cn_hit": old_rank is not None,
                "gip": step_meta[q]["v44next_gip_at_16_rb"],
                "wrote_gold": False,
            }
        arms[arm_name] = amap

    return arms


def is_step_hit(rec: dict[str, Any], meta: dict[str, Any], caliber: str, k: int) -> bool:
    """Return True if step hits at rank <= k under the given caliber."""
    if caliber == "v4":
        r = rec["v4_rank"]
        return r is not None and r <= k
    if caliber == "v4_ex_self":
        if meta["is_self_record"]:
            return False
        r = rec["v4_rank"]
        return r is not None and r <= k
    if caliber == "v5":
        if not rec["v5_available"]:
            return False
        r = rec["v5_rank"]
        return r is not None and r <= k
    if caliber == "v5_ex_self":
        if not rec["v5_available"] or meta["is_self_record"]:
            return False
        r = rec["v5_rank"]
        return r is not None and r <= k
    raise ValueError(f"Unknown caliber: {caliber}")


def classify_step_failure(rec: dict[str, Any], k: int = 1) -> str:
    """Classify a step miss at @k into the 4 mutually-exclusive failure buckets."""
    r = rec["v4_rank"]
    if r is not None and r <= k:
        return "hit"
    # 1. ranking_loss: gold passed compile & 11-item audit and is in final scored events, but rank > k
    if (r is not None and r > k) or rec["v4_hit_any"]:
        return "ranking_loss"
    # 2. compile_or_audit_loss: gold was in offline pool (GIP) or raw model proposals, but lost before final Top-5
    if rec["gip"] or rec["wrote_gold"]:
        return "compile_or_audit_loss"
    # 3. form_representation_gap: cn_identity / stereo-blind match in final events, but strict_identity_of missed
    if rec["old_cn_hit"]:
        return "form_representation_gap"
    # 4. pool_miss_and_novel_miss: pure retrieval + generation miss
    return "pool_miss_and_novel_miss"


def compute_pathway_metrics_for_arm(
    arm_data: dict[str, dict[str, Any]],
    pathways_steps: dict[str, list[str]],
    step_meta: dict[str, dict[str, Any]],
    caliber: str,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Compute pathway-level metrics across all subsets and return (agg_summary, per_pathway_records)."""
    pw_records: dict[str, dict[str, Any]] = {}
    for cid, qlist in sorted(pathways_steps.items()):
        L = len(qlist)
        m0 = step_meta[qlist[0]]
        graph_status = m0["final_graph_status"]
        source_len = m0["ordered_step_count"]
        is_source_complete = L == source_len
        all_preds_in_dev = all(step_meta[q]["all_preds_in_dev"] for q in qlist)

        rec_pw: dict[str, Any] = {
            "case_id": cid,
            "L_eval": L,
            "L_source": source_len,
            "final_graph_status": graph_status,
            "is_source_complete": is_source_complete,
            "all_preds_in_dev": all_preds_in_dev,
        }

        for k in (1, 3, 5):
            hits = [is_step_hit(arm_data[q], step_meta[q], caliber, k) for q in qlist]
            n_hits = sum(1 for h in hits if h)
            exact = all(hits)
            prefix_depth = 0
            for h in hits:
                if h:
                    prefix_depth += 1
                else:
                    break
            prefix_ratio = prefix_depth / L
            macro_recall = n_hits / L

            # B1a strict predecessor topological reachability
            reachable: set[str] = set()
            for q in qlist:
                preds = step_meta[q]["predecessor_step_ids"]
                q_hit = is_step_hit(arm_data[q], step_meta[q], caliber, k)
                if q_hit and all(p in reachable for p in preds):
                    reachable.add(q)
            b1a_reach_count = len(reachable)
            b1a_exact = (b1a_reach_count == L) and is_source_complete

            # First break step and failure bucket
            first_break_pos: int | None = None
            first_break_s_label: str | None = None
            first_break_bucket: str = "no_break"
            if not exact:
                first_break_pos = prefix_depth + 1
                q_break = qlist[prefix_depth]
                first_break_s_label = step_meta[q_break]["s_label"]
                first_break_bucket = classify_step_failure(arm_data[q_break], k=k)

            rec_pw[f"hits_at_{k}"] = n_hits
            rec_pw[f"exact_at_{k}"] = exact
            rec_pw[f"prefix_depth_at_{k}"] = prefix_depth
            rec_pw[f"prefix_ratio_at_{k}"] = prefix_ratio
            rec_pw[f"macro_recall_at_{k}"] = macro_recall
            rec_pw[f"b1a_reachable_steps_at_{k}"] = b1a_reach_count
            rec_pw[f"b1a_strict_exact_at_{k}"] = b1a_exact
            rec_pw[f"first_break_pos_at_{k}"] = first_break_pos
            rec_pw[f"first_break_s_label_at_{k}"] = first_break_s_label
            rec_pw[f"first_break_bucket_at_{k}"] = first_break_bucket

        pw_records[cid] = rec_pw

    def _agg_subset(cids: list[str]) -> dict[str, Any]:
        n_pw = len(cids)
        n_steps = sum(pw_records[c]["L_eval"] for c in cids)
        out: dict[str, Any] = {
            "n_pathways": n_pw,
            "n_steps": n_steps,
        }
        if n_pw == 0:
            return out
        for k in (1, 3, 5):
            ex_cnt = sum(1 for c in cids if pw_records[c][f"exact_at_{k}"])
            b1a_ex_cnt = sum(1 for c in cids if pw_records[c][f"b1a_strict_exact_at_{k}"])
            mean_pd = sum(pw_records[c][f"prefix_depth_at_{k}"] for c in cids) / n_pw
            mean_pr = sum(pw_records[c][f"prefix_ratio_at_{k}"] for c in cids) / n_pw
            mean_mr = sum(pw_records[c][f"macro_recall_at_{k}"] for c in cids) / n_pw
            micro_hits = sum(pw_records[c][f"hits_at_{k}"] for c in cids)
            p_ge1 = sum(1 for c in cids if pw_records[c][f"prefix_depth_at_{k}"] >= 1)
            p_ge2 = sum(1 for c in cids if pw_records[c][f"prefix_depth_at_{k}"] >= 2)
            p_ge3 = sum(1 for c in cids if pw_records[c][f"prefix_depth_at_{k}"] >= 3)
            p_ge4 = sum(1 for c in cids if pw_records[c][f"prefix_depth_at_{k}"] >= 4)
            b1a_reach_steps = sum(
                pw_records[c][f"b1a_reachable_steps_at_{k}"] for c in cids
            )
            fb_counts = Counter(
                pw_records[c][f"first_break_bucket_at_{k}"]
                for c in cids
                if not pw_records[c][f"exact_at_{k}"]
            )
            out[f"at_{k}"] = {
                "pw_exact_count": ex_cnt,
                "pw_exact_pct": round(ex_cnt / n_pw * 100, 2),
                "pw_b1a_strict_exact_count": b1a_ex_cnt,
                "pw_b1a_strict_exact_pct": round(b1a_ex_cnt / n_pw * 100, 2),
                "pw_prefix_depth_mean": round(mean_pd, 3),
                "pw_prefix_ratio_pct": round(mean_pr * 100, 2),
                "pw_macro_recall_pct": round(mean_mr * 100, 2),
                "micro_step_hits": micro_hits,
                "micro_step_recall_pct": round(micro_hits / n_steps * 100, 2) if n_steps else 0.0,
                "b1a_reachable_steps": b1a_reach_steps,
                "b1a_reachable_steps_pct": round(b1a_reach_steps / n_steps * 100, 2)
                if n_steps
                else 0.0,
                "prefix_ge_1_count": p_ge1,
                "prefix_ge_2_count": p_ge2,
                "prefix_ge_3_count": p_ge3,
                "prefix_ge_4_count": p_ge4,
                "first_break_attribution": {
                    "pool_miss_and_novel_miss": fb_counts.get("pool_miss_and_novel_miss", 0),
                    "compile_or_audit_loss": fb_counts.get("compile_or_audit_loss", 0),
                    "ranking_loss": fb_counts.get("ranking_loss", 0),
                    "form_representation_gap": fb_counts.get("form_representation_gap", 0),
                },
            }
        return out

    all_cids = sorted(pw_records.keys())
    ge2_cids = [c for c in all_cids if pw_records[c]["L_eval"] >= 2]
    linear_all_cids = [c for c in all_cids if pw_records[c]["final_graph_status"] == "LINEAR_UNIQUE"]
    branched_all_cids = [c for c in all_cids if pw_records[c]["final_graph_status"] == "BRANCHED_DAG"]
    linear_ge2_cids = [c for c in ge2_cids if pw_records[c]["final_graph_status"] == "LINEAR_UNIQUE"]
    branched_ge2_cids = [c for c in ge2_cids if pw_records[c]["final_graph_status"] == "BRANCHED_DAG"]
    closed_pred_ge2_cids = [c for c in ge2_cids if pw_records[c]["all_preds_in_dev"]]
    source_complete_ge2_cids = [c for c in ge2_cids if pw_records[c]["is_source_complete"]]

    by_length_buckets: dict[str, Any] = {}
    for b_label, pred_fn in [
        ("L_1", lambda L: L == 1),
        ("L_2", lambda L: L == 2),
        ("L_3", lambda L: L == 3),
        ("L_4", lambda L: L == 4),
        ("L_5", lambda L: L == 5),
        ("L_6_plus", lambda L: L >= 6),
    ]:
        bcids = [c for c in all_cids if pred_fn(pw_records[c]["L_eval"])]
        by_length_buckets[b_label] = _agg_subset(bcids)

    agg_summary = {
        "all_76_pathways": _agg_subset(all_cids),
        "multistep_L_ge_2_68_pathways": _agg_subset(ge2_cids),
        "linear_unique_59_pathways": _agg_subset(linear_all_cids),
        "branched_dag_17_pathways": _agg_subset(branched_all_cids),
        "linear_unique_L_ge_2_53_pathways": _agg_subset(linear_ge2_cids),
        "branched_dag_L_ge_2_15_pathways": _agg_subset(branched_ge2_cids),
        "closed_predecessor_L_ge_2_39_pathways": _agg_subset(closed_pred_ge2_cids),
        "source_complete_L_ge_2_30_pathways": _agg_subset(source_complete_ge2_cids),
        "by_length_bucket": by_length_buckets,
    }
    return agg_summary, pw_records


def compute_step_depth_decay(
    dev_qids: list[str],
    step_meta: dict[str, dict[str, Any]],
    arms: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Compute Table 2 step-depth decay across sequence position, S-index, and B1a topological level."""

    def _bucket_stats(qids_in_bucket: list[str]) -> dict[str, Any]:
        n = len(qids_in_bucket)
        s0_gip = sum(1 for q in qids_in_bucket if step_meta[q]["s0_gip_at_8"])
        v44_gip_rb = sum(1 for q in qids_in_bucket if step_meta[q]["v44next_gip_at_16_rb"])
        v44_gip_ra = sum(1 for q in qids_in_bucket if step_meta[q]["v44next_gip_at_16_ra"])
        arm_stats: dict[str, Any] = {}
        for arm_name, amap in arms.items():
            v4_1 = sum(1 for q in qids_in_bucket if is_step_hit(amap[q], step_meta[q], "v4", 1))
            v4_3 = sum(1 for q in qids_in_bucket if is_step_hit(amap[q], step_meta[q], "v4", 3))
            v4_5 = sum(1 for q in qids_in_bucket if is_step_hit(amap[q], step_meta[q], "v4", 5))
            v4_ex_5 = sum(
                1 for q in qids_in_bucket if is_step_hit(amap[q], step_meta[q], "v4_ex_self", 5)
            )
            v5_1 = sum(1 for q in qids_in_bucket if is_step_hit(amap[q], step_meta[q], "v5", 1))
            v5_3 = sum(1 for q in qids_in_bucket if is_step_hit(amap[q], step_meta[q], "v5", 3))
            v5_5 = sum(1 for q in qids_in_bucket if is_step_hit(amap[q], step_meta[q], "v5", 5))
            fb_1 = Counter(classify_step_failure(amap[q], k=1) for q in qids_in_bucket)
            arm_stats[arm_name] = {
                "v4_hit_1": v4_1,
                "v4_hit_1_pct": round(v4_1 / n * 100, 2) if n else 0.0,
                "v4_hit_3": v4_3,
                "v4_hit_3_pct": round(v4_3 / n * 100, 2) if n else 0.0,
                "v4_hit_5": v4_5,
                "v4_hit_5_pct": round(v4_5 / n * 100, 2) if n else 0.0,
                "v4_ex_self_hit_5": v4_ex_5,
                "v4_ex_self_hit_5_pct": round(v4_ex_5 / n * 100, 2) if n else 0.0,
                "v5_hit_1": v5_1,
                "v5_hit_1_pct": round(v5_1 / n * 100, 2) if n else 0.0,
                "v5_hit_3": v5_3,
                "v5_hit_3_pct": round(v5_3 / n * 100, 2) if n else 0.0,
                "v5_hit_5": v5_5,
                "v5_hit_5_pct": round(v5_5 / n * 100, 2) if n else 0.0,
                "step_loss_breakdown_at_1": {
                    "hit": fb_1.get("hit", 0),
                    "ranking_loss": fb_1.get("ranking_loss", 0),
                    "compile_or_audit_loss": fb_1.get("compile_or_audit_loss", 0),
                    "form_representation_gap": fb_1.get("form_representation_gap", 0),
                    "pool_miss_and_novel_miss": fb_1.get("pool_miss_and_novel_miss", 0),
                },
            }
        return {
            "n_steps": n,
            "s0_gip_at_8": {"count": s0_gip, "pct": round(s0_gip / n * 100, 2) if n else 0.0},
            "v44next_gip_at_16_rb": {
                "count": v44_gip_rb,
                "pct": round(v44_gip_rb / n * 100, 2) if n else 0.0,
            },
            "v44next_gip_at_16_ra": {
                "count": v44_gip_ra,
                "pct": round(v44_gip_ra / n * 100, 2) if n else 0.0,
            },
            "arms": arm_stats,
        }

    # 1. By evaluated sequence position Pos_1..Pos_5+
    by_seq_pos: dict[str, Any] = {}
    for pos_label, pred in [
        ("Pos_1", lambda m: m["seq_pos"] == 1),
        ("Pos_2", lambda m: m["seq_pos"] == 2),
        ("Pos_3", lambda m: m["seq_pos"] == 3),
        ("Pos_4", lambda m: m["seq_pos"] == 4),
        ("Pos_5_plus", lambda m: m["seq_pos"] >= 5),
    ]:
        qs = [q for q in dev_qids if pred(step_meta[q])]
        by_seq_pos[pos_label] = _bucket_stats(qs)

    # 2. By original S-index S01..S05+
    by_s_index: dict[str, Any] = {}
    for s_label, pred in [
        ("S01", lambda m: m["s_num"] == 1),
        ("S02", lambda m: m["s_num"] == 2),
        ("S03", lambda m: m["s_num"] == 3),
        ("S04", lambda m: m["s_num"] == 4),
        ("S05_plus", lambda m: m["s_num"] >= 5),
    ]:
        qs = [q for q in dev_qids if pred(step_meta[q])]
        by_s_index[s_label] = _bucket_stats(qs)

    # 3. By B1a topological_level Level_0..Level_4+
    by_topo_level: dict[str, Any] = {}
    for lvl_label, pred in [
        ("Level_0", lambda m: m["topological_level"] == 0),
        ("Level_1", lambda m: m["topological_level"] == 1),
        ("Level_2", lambda m: m["topological_level"] == 2),
        ("Level_3", lambda m: m["topological_level"] == 3),
        ("Level_4_plus", lambda m: m["topological_level"] >= 4),
    ]:
        qs = [q for q in dev_qids if pred(step_meta[q])]
        by_topo_level[lvl_label] = _bucket_stats(qs)

    return {
        "by_evaluated_seq_position": by_seq_pos,
        "by_original_s_index": by_s_index,
        "by_b1a_topological_level": by_topo_level,
    }


def compute_paired_pathway_comparisons(
    pw_by_arm_v4: dict[str, dict[str, dict[str, Any]]]
) -> dict[str, Any]:
    """Compute paired pathway-level flips (exact match and prefix depth gains/losses) across arms."""
    pairs = [
        ("v44_Next_v1_2", "Permanent_v4_Baseline"),
        ("v44_Next_v1_2", "Exp1b_Arm_A"),
        ("v44_Next_v1_2", "SMP_F_ds"),
        ("v44_Next_v1_2", "SMP_M_qw"),
        ("v44_Next_v1_2", "v44_Next_v1_1"),
        ("v44_Next_v1_1", "Permanent_v4_Baseline"),
        ("v44_Next_v1_1", "Exp1b_Arm_A"),
        ("SMP_M_qw", "SMP_F_ds"),
    ]
    out: dict[str, Any] = {}
    all_cids = sorted(pw_by_arm_v4["v44_Next_v1_2"].keys())
    ge2_cids = [c for c in all_cids if pw_by_arm_v4["v44_Next_v1_2"][c]["L_eval"] >= 2]

    for arm_a, arm_b in pairs:
        key = f"{arm_a}__vs__{arm_b}"
        pair_res: dict[str, Any] = {}
        for sub_name, cids in [("all_76", all_cids), ("L_ge_2_68", ge2_cids)]:
            sub_res: dict[str, Any] = {}
            for k in (1, 3, 5):
                ex_gained = sum(
                    1
                    for c in cids
                    if pw_by_arm_v4[arm_a][c][f"exact_at_{k}"]
                    and not pw_by_arm_v4[arm_b][c][f"exact_at_{k}"]
                )
                ex_lost = sum(
                    1
                    for c in cids
                    if not pw_by_arm_v4[arm_a][c][f"exact_at_{k}"]
                    and pw_by_arm_v4[arm_b][c][f"exact_at_{k}"]
                )
                ex_both = sum(
                    1
                    for c in cids
                    if pw_by_arm_v4[arm_a][c][f"exact_at_{k}"]
                    and pw_by_arm_v4[arm_b][c][f"exact_at_{k}"]
                )
                pd_higher = sum(
                    1
                    for c in cids
                    if pw_by_arm_v4[arm_a][c][f"prefix_depth_at_{k}"]
                    > pw_by_arm_v4[arm_b][c][f"prefix_depth_at_{k}"]
                )
                pd_lower = sum(
                    1
                    for c in cids
                    if pw_by_arm_v4[arm_a][c][f"prefix_depth_at_{k}"]
                    < pw_by_arm_v4[arm_b][c][f"prefix_depth_at_{k}"]
                )
                pd_equal = sum(
                    1
                    for c in cids
                    if pw_by_arm_v4[arm_a][c][f"prefix_depth_at_{k}"]
                    == pw_by_arm_v4[arm_b][c][f"prefix_depth_at_{k}"]
                )
                sub_res[f"at_{k}"] = {
                    "exact_gained": ex_gained,
                    "exact_lost": ex_lost,
                    "exact_net": ex_gained - ex_lost,
                    "exact_both": ex_both,
                    "prefix_depth_higher_pathways": pd_higher,
                    "prefix_depth_lower_pathways": pd_lower,
                    "prefix_depth_net_pathways": pd_higher - pd_lower,
                    "prefix_depth_equal_pathways": pd_equal,
                }
            pair_res[sub_name] = sub_res
        out[key] = pair_res
    return out


def compute_phase2_tree_search_budget(
    pathways_steps: dict[str, list[str]], step_meta: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Compute Table 4 candidate subsets and estimated LLM calls / Token budget for Phase 2."""
    # From v44-Next v1.1/v1.2 tuning ledger: 261 calls = 3,901,489 total tokens (~14,948 tokens/call)
    avg_input_tokens_per_call = 4101  # 1,070,368 / 261
    avg_output_tokens_per_call = 10847  # 2,831,121 / 261
    avg_total_tokens_per_call = avg_input_tokens_per_call + avg_output_tokens_per_call

    subsets = {
        "P2_A_closed_predecessor_L_ge_2": [
            cid
            for cid, qs in sorted(pathways_steps.items())
            if len(qs) >= 2 and all(step_meta[q]["all_preds_in_dev"] for q in qs)
        ],
        "P2_B_source_complete_L_ge_2": [
            cid
            for cid, qs in sorted(pathways_steps.items())
            if len(qs) >= 2 and len(qs) == step_meta[qs[0]]["ordered_step_count"]
        ],
        "P2_C_linear_unique_L_ge_2": [
            cid
            for cid, qs in sorted(pathways_steps.items())
            if len(qs) >= 2 and step_meta[qs[0]]["final_graph_status"] == "LINEAR_UNIQUE"
        ],
        "P2_D_all_multistep_L_ge_2": [
            cid for cid, qs in sorted(pathways_steps.items()) if len(qs) >= 2
        ],
    }

    budget_table: dict[str, Any] = {
        "empirical_per_call_token_basis": {
            "source_run": "v44_Next_v1_1_biosysmodb121_tuning_261",
            "avg_input_tokens_per_call": avg_input_tokens_per_call,
            "avg_output_tokens_per_call": avg_output_tokens_per_call,
            "avg_total_tokens_per_call": avg_total_tokens_per_call,
        },
        "subsets": {},
    }

    for sub_key, cids in subsets.items():
        n_pw = len(cids)
        total_steps = sum(len(pathways_steps[c]) for c in cids)
        downstream_steps = total_steps - n_pw  # steps t >= 2
        len_dist = Counter(len(pathways_steps[c]) for c in cids)
        beams: dict[str, Any] = {}
        for B in (1, 3, 5):
            # Step 1 requires 1 root call per pathway (or 0 new calls if warm-started from v44_Next_v1_2 S01 output)
            # Each downstream step t >= 2 expands up to B active beam states (upper bound = B * downstream_steps;
            # with deduplication & early termination on invalid states, typical factor is ~0.75 * B).
            cold_max_calls = n_pw + B * downstream_steps
            warm_s01_max_calls = B * downstream_steps
            expected_dedup_calls = round(B * 0.75 * downstream_steps)
            beams[f"beam_{B}"] = {
                "beam_width": B,
                "cold_start_upper_bound_calls": cold_max_calls,
                "warm_start_reuse_step1_upper_bound_calls": warm_s01_max_calls,
                "warm_start_expected_dedup_calls": expected_dedup_calls,
                "cold_start_upper_bound_tokens_M": round(
                    cold_max_calls * avg_total_tokens_per_call / 1e6, 2
                ),
                "warm_start_upper_bound_tokens_M": round(
                    warm_s01_max_calls * avg_total_tokens_per_call / 1e6, 2
                ),
                "warm_start_expected_tokens_M": round(
                    expected_dedup_calls * avg_total_tokens_per_call / 1e6, 2
                ),
            }
        budget_table["subsets"][sub_key] = {
            "n_pathways": n_pw,
            "total_evaluated_steps": total_steps,
            "step1_root_steps": n_pw,
            "downstream_steps_t_ge_2": downstream_steps,
            "length_distribution": {str(k): v for k, v in sorted(len_dist.items())},
            "beam_budgets": beams,
        }

    return budget_table


def main() -> None:
    dev_qids, step_meta, pathways_steps = load_tuning_qids_and_topology()
    arms = load_all_arms_per_qid(dev_qids, step_meta)

    arm_order = [
        "Permanent_v4_Baseline",
        "Exp1b_Arm_A",
        "SMP_F_ds",
        "SMP_M_qw",
        "v44_Next_v1_0",
        "v44_Next_v1_1",
        "v44_Next_v1_2",
    ]

    arms_pathway_summary: dict[str, Any] = {}
    pw_records_v4_by_arm: dict[str, dict[str, dict[str, Any]]] = {}
    pw_records_v5_by_arm: dict[str, dict[str, dict[str, Any]]] = {}

    for arm_name in arm_order:
        amap = arms[arm_name]
        v4_agg, v4_pw = compute_pathway_metrics_for_arm(
            amap, pathways_steps, step_meta, "v4"
        )
        v4_ex_agg, _ = compute_pathway_metrics_for_arm(
            amap, pathways_steps, step_meta, "v4_ex_self"
        )
        v5_agg, v5_pw = compute_pathway_metrics_for_arm(
            amap, pathways_steps, step_meta, "v5"
        )
        v5_ex_agg, _ = compute_pathway_metrics_for_arm(
            amap, pathways_steps, step_meta, "v5_ex_self"
        )
        pw_records_v4_by_arm[arm_name] = v4_pw
        pw_records_v5_by_arm[arm_name] = v5_pw
        arms_pathway_summary[arm_name] = {
            "v4_matched_product_hit": v4_agg,
            "v4_ex_self": v4_ex_agg,
            "v5_role_bound_product_hit": v5_agg,
            "v5_ex_self": v5_ex_agg,
        }

    step_depth_decay = compute_step_depth_decay(dev_qids, step_meta, arms)
    paired_comparisons = compute_paired_pathway_comparisons(pw_records_v4_by_arm)
    phase2_budget = compute_phase2_tree_search_budget(pathways_steps, step_meta)

    # Topology overview of the 76 tuning pathways
    len_dist_all = Counter(len(qs) for qs in pathways_steps.values())
    public_summary = {
        "schema_version": "b121-multistep-pathway-eval-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domain": "[biosysmodb121·调参集]",
        "holdout_touched": False,
        "llm_calls": 0,
        "n_tuning_pathways": len(pathways_steps),
        "n_tuning_steps": len(dev_qids),
        "n_multistep_pathways_L_ge_2": sum(
            1 for qs in pathways_steps.values() if len(qs) >= 2
        ),
        "n_multistep_steps_L_ge_2": sum(
            len(qs) for qs in pathways_steps.values() if len(qs) >= 2
        ),
        "topology_overview": {
            "linear_unique_pathways": sum(
                1
                for qs in pathways_steps.values()
                if step_meta[qs[0]]["final_graph_status"] == "LINEAR_UNIQUE"
            ),
            "branched_dag_pathways": sum(
                1
                for qs in pathways_steps.values()
                if step_meta[qs[0]]["final_graph_status"] == "BRANCHED_DAG"
            ),
            "source_complete_pathways": sum(
                1
                for qs in pathways_steps.values()
                if len(qs) == step_meta[qs[0]]["ordered_step_count"]
            ),
            "closed_b1a_predecessor_pathways_all": sum(
                1
                for qs in pathways_steps.values()
                if all(step_meta[q]["all_preds_in_dev"] for q in qs)
            ),
            "closed_b1a_predecessor_pathways_L_ge_2": sum(
                1
                for qs in pathways_steps.values()
                if len(qs) >= 2 and all(step_meta[q]["all_preds_in_dev"] for q in qs)
            ),
            "evaluated_length_distribution": {
                str(k): v for k, v in sorted(len_dist_all.items())
            },
        },
        "arms_pathway_metrics": arms_pathway_summary,
        "step_depth_decay": step_depth_decay,
        "paired_pathway_comparisons_v4": paired_comparisons,
        "phase2_autoregressive_tree_search_budget": phase2_budget,
    }

    PUBLIC_JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_JSON_OUT.write_text(
        json.dumps(public_summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Write private per-pathway TSV (gitignored)
    PRIVATE_TSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    tsv_rows: list[dict[str, Any]] = []
    for cid in sorted(pathways_steps.keys()):
        qlist = pathways_steps[cid]
        m0 = step_meta[qlist[0]]
        row: dict[str, Any] = {
            "case_id": cid,
            "L_eval": len(qlist),
            "L_source": m0["ordered_step_count"],
            "final_graph_status": m0["final_graph_status"],
            "is_source_complete": len(qlist) == m0["ordered_step_count"],
            "all_preds_in_dev": all(step_meta[q]["all_preds_in_dev"] for q in qlist),
            "step_s_labels": "|".join(step_meta[q]["s_label"] for q in qlist),
            "s0_gip_steps": sum(1 for q in qlist if step_meta[q]["s0_gip_at_8"]),
            "v44next_gip_steps": sum(1 for q in qlist if step_meta[q]["v44next_gip_at_16_rb"]),
        }
        for arm_name in arm_order:
            pw_v4 = pw_records_v4_by_arm[arm_name][cid]
            pw_v5 = pw_records_v5_by_arm[arm_name][cid]
            row[f"{arm_name}_v4_exact_1"] = pw_v4["exact_at_1"]
            row[f"{arm_name}_v4_exact_3"] = pw_v4["exact_at_3"]
            row[f"{arm_name}_v4_exact_5"] = pw_v4["exact_at_5"]
            row[f"{arm_name}_v4_prefix_1"] = pw_v4["prefix_depth_at_1"]
            row[f"{arm_name}_v4_prefix_5"] = pw_v4["prefix_depth_at_5"]
            row[f"{arm_name}_v4_hits_1"] = pw_v4["hits_at_1"]
            row[f"{arm_name}_v4_hits_5"] = pw_v4["hits_at_5"]
            row[f"{arm_name}_v4_break_pos_1"] = pw_v4["first_break_pos_at_1"] or ""
            row[f"{arm_name}_v4_break_bucket_1"] = pw_v4["first_break_bucket_at_1"]
            row[f"{arm_name}_v4_break_pos_5"] = pw_v4["first_break_pos_at_5"] or ""
            row[f"{arm_name}_v4_break_bucket_5"] = pw_v4["first_break_bucket_at_5"]
            row[f"{arm_name}_v5_exact_1"] = pw_v5["exact_at_1"]
            row[f"{arm_name}_v5_exact_5"] = pw_v5["exact_at_5"]
            row[f"{arm_name}_v5_prefix_1"] = pw_v5["prefix_depth_at_1"]
            row[f"{arm_name}_v5_prefix_5"] = pw_v5["prefix_depth_at_5"]
        tsv_rows.append(row)

    with open(PRIVATE_TSV_OUT, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(tsv_rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(tsv_rows)

    print(
        f"SUCCESS: Evaluated {len(pathways_steps)} tuning pathways ({len(dev_qids)} steps), "
        f"holdout_touched=False. Wrote {PUBLIC_JSON_OUT} and {PRIVATE_TSV_OUT}."
    )


if __name__ == "__main__":
    main()
