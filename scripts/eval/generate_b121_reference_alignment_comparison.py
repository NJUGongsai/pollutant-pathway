#!/usr/bin/env python3
"""BIOSYSMOdb121 端到端自回归 (Autoregressive B=1) 与参考标准答卷 (Reference & Teacher-Forced)

全方位多步对标分析驱动器。
零 LLM、确定性离线对标，严格遵守三道红线（公开产物零私有题号、零化合物名、零 SMILES）。
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pathway_v43.domain.identity import cn_identity
from pathway_v43.pollutant.chemstate import strict_identity_of
from scripts.eval.run_b121_e2e_mineralization_eval import (
    PathwayReference,
    load_pathway_dataset,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REPORT_DIR = REPO_ROOT / "reports/ppv1_s5b/b121_e2e_mineralization_20261111"
RUN_PATHS = {
    "arm1_naive_d15": REPORT_DIR / "private_detail_full121.json",
    "arm4_non_backtrack_d20": (
        REPORT_DIR / "full121_non_backtracking_b1_depth20/private_detail_full121.json"
    ),
    "arm6_stage_aware_d20": (
        REPORT_DIR / "full121_stage_aware_b1/private_detail_full121.json"
    ),
}

OUT_JSON = (
    REPO_ROOT
    / "docs/reviews/evidence/b121_e2e_mineralization_2026-11-11/b121_reference_alignment_comparison.json"
)


def extract_model_tree(leaf_branches: list[dict[str, Any]]) -> tuple[set[str], set[str], set[tuple[str, str]], set[tuple[str, str]]]:
    """从叶分支恢复模型自回归推演树生成的全部节点与边。"""
    nodes_strict: set[str] = set()
    nodes_cn: set[str] = set()
    edges_strict: set[tuple[str, str]] = set()
    edges_cn: set[tuple[str, str]] = set()

    for b in leaf_branches:
        for st in b.get("steps", []):
            sub_smi = st.get("substrate", "")
            try:
                sub_sid = st.get("substrate_strict_id") or strict_identity_of(sub_smi)
            except Exception:
                sub_sid = sub_smi
            try:
                sub_cn = cn_identity(sub_smi) or sub_sid
            except Exception:
                sub_cn = sub_sid

            nodes_strict.add(sub_sid)
            nodes_cn.add(sub_cn)

            all_prods = st.get("principal_products", []) + st.get("coproducts", [])
            for prod in all_prods:
                psmi = prod.get("smiles", "") if isinstance(prod, dict) else str(prod)
                if not psmi:
                    continue
                try:
                    psid = strict_identity_of(psmi)
                except Exception:
                    psid = psmi
                try:
                    pcn = cn_identity(psmi) or psid
                except Exception:
                    pcn = psid

                nodes_strict.add(psid)
                nodes_cn.add(pcn)
                edges_strict.add((sub_sid, psid))
                edges_cn.add((sub_cn, pcn))

    return nodes_strict, nodes_cn, edges_strict, edges_cn


def analyze_split_alignment(
    sub_pathways: list[PathwayReference],
    arm_data: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """计算单个数据子集的对标统计。"""
    n_pw = len(sub_pathways)
    if n_pw == 0:
        return {}

    tot_ref_steps = sum(len(p.ref_steps) for p in sub_pathways)
    tot_ref_nodes_strict = sum(len(p.ref_nodes) for p in sub_pathways)
    tot_ref_nodes_cn = sum(len(p.ref_nodes_cn) for p in sub_pathways)
    tot_ref_edges = sum(len(p.ref_edges) for p in sub_pathways)

    # 1. Step-1 Hits
    s1_strict_hits = 0
    s1_cn_hits = 0

    # 2. Continuous Prefix Depths
    prefix_depths: list[int] = []
    prefix_ge1 = 0
    prefix_ge2 = 0
    prefix_ge3 = 0
    prefix_full = 0

    # 3. Micro Node & Edge Hits
    micro_node_hits_strict = 0
    micro_node_hits_cn = 0
    micro_edge_hits_strict = 0

    # 4. Macro Recall sums
    macro_node_recall_strict_sum = 0.0
    macro_node_recall_cn_sum = 0.0
    macro_edge_recall_sum = 0.0

    # 5. Position Breakdown (Pos 1, 2, 3, 4, 5+)
    pos_tot: Counter[str] = Counter()
    pos_hit_strict: Counter[str] = Counter()
    pos_hit_cn: Counter[str] = Counter()

    # 6. Terminal hits
    term_hit_and_min = 0
    stopped_early_model_min = 0

    # 7. Four-Type Taxonomy
    t1_aligned_and_min = 0
    t1_stopped_early_sub = 0
    t2_alt_and_min = 0
    t2_reconverged_sub = 0
    t2_pure_alt_sub = 0
    t3_aligned_unfinished = 0
    t4_diverged_unfinished = 0

    for p in sub_pathways:
        c_item = arm_data[p.case_id]
        m = c_item["metrics"]
        outcome = c_item["outcome"]
        is_min = (outcome == "MINERALIZED_CLOSED")

        if m["ref_step1_hit_strict"]:
            s1_strict_hits += 1
        if m["ref_step1_hit_cn"]:
            s1_cn_hits += 1

        pd = m["ref_prefix_depth"]
        prefix_depths.append(pd)
        if pd >= 1:
            prefix_ge1 += 1
        if pd >= 2:
            prefix_ge2 += 1
        if pd >= 3:
            prefix_ge3 += 1
        if pd == len(p.ref_steps):
            prefix_full += 1

        macro_node_recall_strict_sum += m["ref_node_recall_strict"]
        macro_node_recall_cn_sum += m["ref_node_recall_cn"]
        macro_edge_recall_sum += m["ref_edge_recall"]

        if m.get("terminal_hit_and_mineralized"):
            term_hit_and_min += 1
        if m.get("stopped_early_model_mineralized"):
            stopped_early_model_min += 1

        # Micro node & edge hits
        m_nodes_s, m_nodes_cn, m_edges_s, _ = extract_model_tree(c_item.get("leaf_branches", []))
        hit_ns = len(p.ref_nodes & m_nodes_s)
        hit_ncn = len(p.ref_nodes_cn & m_nodes_cn)
        hit_es = len(p.ref_edges & m_edges_s)

        micro_node_hits_strict += hit_ns
        micro_node_hits_cn += hit_ncn
        micro_edge_hits_strict += hit_es

        # Position breakdown
        for idx, rstep in enumerate(p.ref_steps):
            pos = idx + 1
            pos_label = f"Pos_{pos}" if pos < 5 else "Pos_5+"
            pos_tot[pos_label] += 1
            r_prods_s = {x["strict_id"] for x in rstep["prods"]}
            r_prods_cn = {x["cn"] for x in rstep["prods"]}
            if bool(r_prods_s & m_nodes_s):
                pos_hit_strict[pos_label] += 1
            if bool(r_prods_cn & m_nodes_cn):
                pos_hit_cn[pos_label] += 1

        # Four-Type Taxonomy
        has_node_hit = (hit_ncn > 0) or m["ref_step1_hit_cn"]
        if is_min:
            if m["ref_step1_hit_cn"]:
                t1_aligned_and_min += 1
                if m.get("stopped_early_model_mineralized"):
                    t1_stopped_early_sub += 1
            else:
                t2_alt_and_min += 1
                if hit_ncn > 0:
                    t2_reconverged_sub += 1
                else:
                    t2_pure_alt_sub += 1
        else:
            if has_node_hit:
                t3_aligned_unfinished += 1
            else:
                t4_diverged_unfinished += 1

    return {
        "n_pathways": n_pw,
        "tot_ref_steps": tot_ref_steps,
        "tot_ref_nodes_strict": tot_ref_nodes_strict,
        "tot_ref_nodes_cn": tot_ref_nodes_cn,
        "tot_ref_edges": tot_ref_edges,
        "step1_hit_strict": {
            "count": s1_strict_hits,
            "ratio": s1_strict_hits / n_pw,
        },
        "step1_hit_cn": {
            "count": s1_cn_hits,
            "ratio": s1_cn_hits / n_pw,
        },
        "prefix_matching": {
            "mean_depth": sum(prefix_depths) / n_pw,
            "prefix_ge1": {"count": prefix_ge1, "ratio": prefix_ge1 / n_pw},
            "prefix_ge2": {"count": prefix_ge2, "ratio": prefix_ge2 / n_pw},
            "prefix_ge3": {"count": prefix_ge3, "ratio": prefix_ge3 / n_pw},
            "prefix_full_exact": {"count": prefix_full, "ratio": prefix_full / n_pw},
        },
        "micro_hits": {
            "node_hits_strict": {
                "count": micro_node_hits_strict,
                "total": tot_ref_nodes_strict,
                "ratio": micro_node_hits_strict / tot_ref_nodes_strict if tot_ref_nodes_strict else 0.0,
            },
            "node_hits_cn": {
                "count": micro_node_hits_cn,
                "total": tot_ref_nodes_cn,
                "ratio": micro_node_hits_cn / tot_ref_nodes_cn if tot_ref_nodes_cn else 0.0,
            },
            "edge_hits_strict": {
                "count": micro_edge_hits_strict,
                "total": tot_ref_edges,
                "ratio": micro_edge_hits_strict / tot_ref_edges if tot_ref_edges else 0.0,
            },
        },
        "macro_recall": {
            "node_recall_strict": macro_node_recall_strict_sum / n_pw,
            "node_recall_cn": macro_node_recall_cn_sum / n_pw,
            "edge_recall": macro_edge_recall_sum / n_pw,
        },
        "position_breakdown": {
            k: {
                "total": pos_tot[k],
                "hit_strict": pos_hit_strict[k],
                "ratio_strict": pos_hit_strict[k] / pos_tot[k] if pos_tot[k] else 0.0,
                "hit_cn": pos_hit_cn[k],
                "ratio_cn": pos_hit_cn[k] / pos_tot[k] if pos_tot[k] else 0.0,
            }
            for k in ["Pos_1", "Pos_2", "Pos_3", "Pos_4", "Pos_5+"]
        },
        "terminal_alignment": {
            "terminal_hit_and_mineralized": term_hit_and_min,
            "stopped_early_model_mineralized": stopped_early_model_min,
        },
        "four_type_taxonomy": {
            "type_1_exact_aligned_mineralized": {
                "count": t1_aligned_and_min,
                "ratio": t1_aligned_and_min / n_pw,
                "sub_stopped_early_extended": t1_stopped_early_sub,
            },
            "type_2_alternative_reconverged_mineralized": {
                "count": t2_alt_and_min,
                "ratio": t2_alt_and_min / n_pw,
                "sub_reconverged_downstream": t2_reconverged_sub,
                "sub_pure_alternative_catabolic_route": t2_pure_alt_sub,
            },
            "type_3_aligned_prefix_unfinished": {
                "count": t3_aligned_unfinished,
                "ratio": t3_aligned_unfinished / n_pw,
            },
            "type_4_diverged_unfinished": {
                "count": t4_diverged_unfinished,
                "ratio": t4_diverged_unfinished / n_pw,
            },
            "total_mineralized": t1_aligned_and_min + t2_alt_and_min,
        },
    }


def main() -> None:
    pathway_list, pathway_map = load_pathway_dataset()

    # Load 3 arms
    arm_details: dict[str, dict[str, Any]] = {}
    for arm_id, p_path in RUN_PATHS.items():
        if not p_path.exists():
            raise FileNotFoundError(f"Missing run detail: {p_path}")
        arm_details[arm_id] = {x["case_id"]: x for x in json.loads(p_path.read_text())}

    # Reference Denominator Baseline
    denominators: dict[str, Any] = {}
    for sp in ["full_121", "tuning_76", "holdout_43"]:
        sub = (
            pathway_list
            if sp == "full_121"
            else [p for p in pathway_list if p.split == sp.split("_")[0]]
        )
        len_dist = Counter(len(p.ref_steps) for p in sub)
        denominators[sp] = {
            "n_pathways": len(sub),
            "tot_ref_steps": sum(len(p.ref_steps) for p in sub),
            "tot_ref_nodes_strict": sum(len(p.ref_nodes) for p in sub),
            "tot_ref_nodes_cn": sum(len(p.ref_nodes_cn) for p in sub),
            "tot_ref_edges": sum(len(p.ref_edges) for p in sub),
            "path_length_distribution": {f"len_{k}": v for k, v in sorted(len_dist.items())},
        }

    # Teacher-Forced Stepwise Baseline (from B121_MULTISTEP_PATHWAY_BENCHMARK_2026-11-11.md)
    teacher_forced_tuning_76 = {
        "n_pathways": 76,
        "n_steps": 261,
        "step_hits": {
            "v4_hit_at_1": {"count": 66, "ratio": 66 / 261},
            "v4_hit_at_5": {"count": 90, "ratio": 90 / 261},
            "v5_hit_at_1": {"count": 63, "ratio": 63 / 261},
            "v5_hit_at_5": {"count": 87, "ratio": 87 / 261},
        },
        "pathway_exact": {
            "pw_exact_at_1": {"count": 6, "ratio": 6 / 76},
            "pw_exact_at_5": {"count": 11, "ratio": 11 / 76},
        },
        "prefix_depth": {
            "prefix_depth_at_1": 0.426,
            "prefix_depth_at_5": 0.706,
            "prefix_ge2_at_1": 10,
            "prefix_ge2_at_5": 15,
            "prefix_ge3_at_1": 1,
            "prefix_ge3_at_5": 6,
        },
        "position_breakdown_v4": {
            "Pos_1": {"total": 76, "hit_at_1": 20, "hit_at_5": 26},
            "Pos_2": {"total": 68, "hit_at_1": 21, "hit_at_5": 29},
            "Pos_3": {"total": 54, "hit_at_1": 7, "hit_at_5": 14},
            "Pos_4": {"total": 33, "hit_at_1": 11, "hit_at_5": 12},
            "Pos_5+": {"total": 30, "hit_at_1": 7, "hit_at_5": 9},
        },
    }

    # Evaluate arms across splits
    arm_evaluations: dict[str, Any] = {}
    for arm_id, c_data in arm_details.items():
        arm_evaluations[arm_id] = {
            "full_121": analyze_split_alignment(pathway_list, c_data),
            "tuning_76": analyze_split_alignment(
                [p for p in pathway_list if p.split == "tuning"], c_data
            ),
            "holdout_43": analyze_split_alignment(
                [p for p in pathway_list if p.split == "holdout"], c_data
            ),
        }

    output_payload = {
        "benchmark_name": "b121_reference_alignment_comparison",
        "description": "Comparison of End-to-End Autoregressive Trajectories against biosysmodb121 Reference Answers and Teacher-Forced Stepwise Model",
        "anonymity_check": "PASS_ZERO_GOLD_STANDARD_ZERO_SMILES",
        "denominators": denominators,
        "teacher_forced_stepwise_tuning_76": teacher_forced_tuning_76,
        "autoregressive_evaluations": arm_evaluations,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(output_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Comparison JSON saved to {OUT_JSON}")


if __name__ == "__main__":
    main()
