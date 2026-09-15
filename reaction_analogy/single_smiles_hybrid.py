#!/usr/bin/env python3
"""BBD 单 SMILES 混合口径预测入口（v3.2 引擎 + v3.3 融合 + EAWAG lookup 层）。

背景（2026-09-14）: 测试部门的 DBP 诊断（2026-09-12）与 v3.3 修复报告
（BBD_V33_FUSION_FIX_2026-09-14.md）评估的都是**纯预测口径**（三引擎 +
LightGBM 排序，lookup 关闭）。README 终版声明的 89.5%/95.3% 是**混合口径**
（EAWAG known-pathway lookup 置顶 + 预测兜底）。本入口补齐单 SMILES 场景下的
混合口径运行能力，供测试部门对 DBP（及任意新污染物）复测。

分层规则（与 predict_bbd_hybrid.py 的 P4.2 语义一致）:
  depth 1..D 每层:
    Layer 1 (lookup):  当前底物是 EAWAG donor → 其已知反应产物按
                       (过滤, -Tanimoto, smiles) 排序置顶（带 eawag_reactions 溯源）;
    Layer 2 (预测):    v3.2 三引擎 + v3.3 融合的候选跟后（与 lookup 产物去重）。
  lookup 未命中 → 该层全部为预测候选（行为 = single_smiles_v32.py）。

用法（DBP 混合口径复测）:
  python single_smiles_hybrid.py --smiles "CCCCOC(=O)c1ccccc1C(=O)OCCCC" \
      --top-k 10 --max-depth 3 --case-id DBP --out-prefix /tmp/dbp_hybrid

输出（冻结链兼容命名 + 混合层注记）:
  <prefix>_RAW_STDOUT.json            全量结果（top_predictions 含 layer 字段）
  <prefix>_ALL_NORMALIZED_PREDICTIONS.csv
  <prefix>_RUN_META.json

answer key 隔离: 本文件不读任何答案文件（donor_product.jsonl 是公共 EAWAG-BBD 库）。
"""
import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "src"))

from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")

import expand_bbd_routes as X  # noqa: E402
import single_smiles_v32 as S  # noqa: E402 — 复用引擎加载/展开/装配
import eawag_lookup as EGD  # noqa: E402

DONOR_PRODUCT = os.path.join(_HERE, "data", "bbd_expand", "donor_product.jsonl")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smiles", required=True)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument("--k1", type=int, default=S.X.K1)
    ap.add_argument("--k2", type=int, default=S.X.K2)
    ap.add_argument("--scoring", default="v33", choices=["v33", "v32"])
    ap.add_argument("--case-id", default=None)
    ap.add_argument("--out-prefix", default=None)
    args = ap.parse_args()

    smi = args.smiles.strip()
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        print(f"FATAL: unparseable SMILES: {smi!r}", file=sys.stderr)
        return 2
    X._G_SCORING = args.scoring

    case_id = args.case_id or "SINGLE-HYBRID"
    t_start = time.time()
    S.load_engines()
    lookup_index = EGD.build_index(DONOR_PRODUCT)
    print(f"engines + lookup index loaded "
          f"({len([k for k in lookup_index if k != '__parse_fail__'])} donors)",
          flush=True)

    root_identity = X._identity(smi) or smi
    root_node = {
        "node_id": X._node_id(case_id, 0, root_identity), "case_id": case_id,
        "depth": 0, "smiles": smi, "canonical_smiles": root_identity,
        "is_root": True, "ancestor_canons": set(), "path_score": 1.0,
    }

    all_edges: list[dict] = []
    nodes_by_id = {root_node["node_id"]: root_node}
    children_by_node: dict[str, list[dict]] = defaultdict(list)
    frontier: list[dict] = []
    depth1_lookup_hit = EGD.lookup(lookup_index, smi)

    # ---- depth 1 ----
    S.attach_retrieval([root_node])
    res = S.expand_node(root_node)
    pred_edges = []
    for e in res["edges"]:
        e["depth"] = 1
        e["source_node_id"] = root_node["node_id"]
        e["source_smiles"] = smi
        e["parent_case_id"] = case_id
        e["layer"] = "prediction"
        prod_identity = X._identity(e["product_smiles"]) or ""
        e["product_node_id"] = X._node_id(case_id, 1, prod_identity)
        e["parent_copy_filtered"] = (prod_identity == root_identity)
        e["cycle"] = e["parent_copy_filtered"]
        pred_edges.append(e)

    # lookup tier: charge-normalized identity 与预测层合并去重
    from bbd_v33_fusion import normalize_charge_smiles
    look_edges = []
    for i, c in enumerate(depth1_lookup_hit):
        pid = normalize_charge_smiles(c["product_smiles"]) or c["product_smiles"]
        pid = X._identity(pid) or X._identity(c["product_smiles"]) or ""
        look_edges.append({
            "depth": 1, "layer": "lookup", "rank": None,
            "source_node_id": root_node["node_id"], "source_smiles": smi,
            "parent_case_id": case_id,
            "product_smiles": c["product_smiles"],
            "product_node_id": X._node_id(case_id, 1, pid),
            "edge_score": round(c.get("tanimoto", 0.0), 6),
            "score_semantics": "eawag_lookup_tanimoto",
            "source": "eawag_lookup",
            "eawag_reactions": c.get("eawag_reactions", []),
            "tanimoto": c.get("tanimoto"),
            "donor_exact_match": True,
            "p_uspto": 0.0, "p_envipath": 0.0, "p_retrieval": 0.0,
            "ion_filtered": c.get("ion_filtered", False),
            "wildcard_filtered": False,
            "cycle": False, "parent_copy_filtered": False,
        })

    # 预测层去掉与 lookup 同身份（charge-normalized）的候选
    look_ids = {X._identity(normalize_charge_smiles(le["product_smiles"]) or le["product_smiles"])
                for le in look_edges}
    pred_edges = [e for e in pred_edges
                  if (X._identity(normalize_charge_smiles(e["product_smiles"]) or e["product_smiles"])
                      not in look_ids)]
    # 合并: lookup 置顶（tanimoto 序），预测跟后（原 v3.3 序）
    depth1_merged = sorted(look_edges, key=lambda e: (e["ion_filtered"], -e["edge_score"],
                                                      e["product_smiles"])) + pred_edges
    for r, e in enumerate(depth1_merged, 1):
        e["rank"] = r
        e["product_in_frontier"] = (
            not e["ion_filtered"] and not e["wildcard_filtered"]
            and not e["cycle"] and e["rank"] <= args.k1)
        all_edges.append(e)
        if e["product_in_frontier"]:
            child = {
                "node_id": e["product_node_id"], "case_id": case_id, "depth": 1,
                "smiles": e["product_smiles"],
                "canonical_smiles": X._identity(e["product_smiles"]) or "",
                "is_root": False, "ancestor_canons": {root_identity},
                "path_score": e["edge_score"],
            }
            if child["node_id"] not in nodes_by_id:
                nodes_by_id[child["node_id"]] = child
                children_by_node[root_node["node_id"]].append(e)
                frontier.append(child)
    print(f"depth 1: lookup={len(look_edges)} pred={len(pred_edges)} "
          f"frontier={len(frontier)}", flush=True)

    engine_invocations = {"1": 1}
    # ---- BFS depth 2..D（每层同样做 lookup 融合）----
    for depth in range(2, args.max_depth + 1):
        if not frontier:
            print(f"depth {depth}: frontier empty, stopping", flush=True)
            break
        S.attach_retrieval(frontier)
        engine_invocations[str(depth)] = len(frontier)
        new_frontier = []
        for node in frontier:
            r = S.expand_node(node)
            pe = []
            for e in r["edges"]:
                e["depth"] = depth
                e["source_node_id"] = node["node_id"]
                e["source_smiles"] = node["smiles"]
                e["parent_case_id"] = case_id
                e["layer"] = "prediction"
                prod_identity = X._identity(e["product_smiles"]) or ""
                e["product_node_id"] = X._node_id(case_id, depth, prod_identity)
                e["parent_copy_filtered"] = (prod_identity == node["canonical_smiles"])
                pe.append(e)
            # lookup at this node
            le = []
            for c in EGD.lookup(lookup_index, node["smiles"]):
                pid = normalize_charge_smiles(c["product_smiles"]) or c["product_smiles"]
                pid = X._identity(pid) or ""
                le.append({
                    "depth": depth, "layer": "lookup", "rank": None,
                    "source_node_id": node["node_id"], "source_smiles": node["smiles"],
                    "parent_case_id": case_id,
                    "product_smiles": c["product_smiles"],
                    "product_node_id": X._node_id(case_id, depth, pid),
                    "edge_score": round(c.get("tanimoto", 0.0), 6),
                    "score_semantics": "eawag_lookup_tanimoto",
                    "source": "eawag_lookup",
                    "eawag_reactions": c.get("eawag_reactions", []),
                    "tanimoto": c.get("tanimoto"), "donor_exact_match": True,
                    "p_uspto": 0.0, "p_envipath": 0.0, "p_retrieval": 0.0,
                    "ion_filtered": c.get("ion_filtered", False),
                    "wildcard_filtered": False,
                    "cycle": False, "parent_copy_filtered": False,
                })
            look_ids = {X._identity(normalize_charge_smiles(x["product_smiles"]) or x["product_smiles"])
                        for x in le}
            pe = [e for e in pe
                  if (X._identity(normalize_charge_smiles(e["product_smiles"]) or e["product_smiles"])
                      not in look_ids)]
            merged = sorted(le, key=lambda e: (e["ion_filtered"], -e["edge_score"],
                                               e["product_smiles"])) + pe
            for rk, e in enumerate(merged, 1):
                e["rank"] = rk
                e["product_in_frontier"] = (
                    not e["ion_filtered"] and not e["wildcard_filtered"]
                    and e["rank"] <= args.k2)
                all_edges.append(e)
                if e["product_in_frontier"]:
                    pid_canon = X._identity(e["product_smiles"]) or ""
                    if X._node_id(case_id, depth, pid_canon) in nodes_by_id:
                        continue
                    child = {
                        "node_id": e["product_node_id"], "case_id": case_id,
                        "depth": depth, "smiles": e["product_smiles"],
                        "canonical_smiles": pid_canon, "is_root": False,
                        "ancestor_canons": node["ancestor_canons"] | {node["canonical_smiles"]},
                        "path_score": round(node["path_score"] * e["edge_score"], 9),
                    }
                    nodes_by_id[child["node_id"]] = child
                    children_by_node[node["node_id"]].append(e)
                    new_frontier.append(child)
        print(f"depth {depth}: frontier={len(new_frontier)}", flush=True)
        frontier = new_frontier

    # ---- routes + PRIMARY（同 S 的规则: greedy rank-1 cascade, 含 lookup 边）----
    depth1_ranked = [e for e in all_edges if e["depth"] == 1]
    routes = S.assemble_routes(depth1_ranked, children_by_node,
                               root_node["node_id"], args.max_depth)
    routes.sort(key=lambda r: (-r["n_edges"], -r["path_score"],
                               r["edges"][0]["product_smiles"]))
    primary = []
    node = root_node
    for d in range(1, args.max_depth + 1):
        kids = children_by_node.get(node["node_id"], [])
        if not kids:
            break
        best = min(kids, key=lambda e: e["rank"])
        primary.append(best)
        node = nodes_by_id.get(best["product_node_id"])
        if node is None:
            break

    # ---- outputs（冻结链兼容）----
    import hashlib
    prefix = args.out_prefix or f"hybrid_{hashlib.sha1(smi.encode()).hexdigest()[:8]}"
    os.makedirs(os.path.dirname(os.path.abspath(prefix)), exist_ok=True)

    def _row(e):
        return {
            "rank": e["rank"], "layer": e.get("layer", "prediction"),
            "product_smiles": e["product_smiles"],
            "product_identity": X._identity(e["product_smiles"]),
            "source": e["source"], "score": e["edge_score"],
            "score_semantics": e.get("score_semantics",
                                     "ns33_max_source_x_agreement_x_skeleton_over_3"),
            "eawag_reactions": e.get("eawag_reactions", []),
            "tanimoto": e.get("tanimoto", ""),
            "p_uspto": e.get("p_uspto", 0.0),
            "p_envipath": e.get("p_envipath", 0.0),
            "p_retrieval": e.get("p_retrieval", 0.0),
            "n_independent_sources": e.get("n_independent_sources", ""),
            "skeleton_unexplained": e.get("skeleton_unexplained", ""),
            "skeleton_reason": e.get("skeleton_reason", ""),
            "charge_variants": ";".join(e.get("charge_variants", [])
                                        or [e["product_smiles"]]),
            "ion_filtered": e.get("ion_filtered", False),
            "wildcard_filtered": e.get("wildcard_filtered", False),
            "is_calibrated_probability": False,
            "depth": e["depth"],
        }

    top_rows = [_row(e) for e in depth1_ranked[:args.top_k]]
    raw = {
        "case_id": case_id, "input_smiles": smi,
        "input_identity": root_identity,
        "caliber": "hybrid (EAWAG lookup tier + v3.3 prediction fallback)",
        "params": {"top_k": args.top_k, "max_depth": args.max_depth,
                   "K1": args.k1, "K2": args.k2, "scoring": args.scoring},
        "lookup_tier": {"depth1_hit": bool(depth1_lookup_hit),
                        "n_lookup_products": len(depth1_lookup_hit)},
        "depth_engine_invocations": engine_invocations,
        "top_predictions": top_rows,
        "n_edges": len(all_edges),
        "edges": [{k: e.get(k) for k in (
            "source_smiles", "product_smiles", "source_node_id",
            "product_node_id", "edge_score", "rank", "depth", "layer", "source",
            "eawag_reactions", "tanimoto", "p_uspto", "p_envipath", "p_retrieval",
            "ion_filtered", "wildcard_filtered", "cycle", "product_in_frontier",
            "n_independent_sources", "skeleton_unexplained", "skeleton_reason",
            "charge_variants")}
            for e in all_edges],
        "routes": [{"path_score": r["path_score"], "n_edges": r["n_edges"],
                    "steps": [{"depth": e["depth"], "rank": e["rank"],
                               "layer": e.get("layer"), "product_smiles": e["product_smiles"],
                               "score": e["edge_score"], "source": e["source"],
                               "eawag_reactions": e.get("eawag_reactions", []),
                               "skeleton_unexplained": e.get("skeleton_unexplained", False)}
                              for e in r["edges"]]}
                   for r in routes[:50]],
        "primary_route": {"rule": "greedy native rank=1 cascade (lookup tier pinned)",
                          "steps": [{"depth": e["depth"], "rank": e["rank"],
                                     "layer": e.get("layer"),
                                     "product_smiles": e["product_smiles"],
                                     "score": e["edge_score"], "source": e["source"],
                                     "eawag_reactions": e.get("eawag_reactions", [])}
                                    for e in primary]},
        "total_time_s": round(time.time() - t_start, 1),
    }
    with open(f"{prefix}_RAW_STDOUT.json", "w") as f:
        json.dump(raw, f, indent=1, ensure_ascii=False)
    with open(f"{prefix}_ALL_NORMALIZED_PREDICTIONS.csv", "w", newline="") as f:
        if top_rows:
            w = csv.DictWriter(f, fieldnames=list(top_rows[0].keys()))
            w.writeheader()
            w.writerows(top_rows)
    with open(f"{prefix}_RUN_META.json", "w") as f:
        json.dump({"case_id": case_id, "input_smiles": smi,
                   "caliber": "hybrid", "n_edges": len(all_edges),
                   "depth_engine_invocations": engine_invocations,
                   "primary": [e["product_smiles"] for e in primary],
                   "total_time_s": raw["total_time_s"]}, f, indent=1)

    print(f"DONE hybrid: {len(all_edges)} edges, primary="
          f"{' -> '.join(e['product_smiles'][:20] for e in primary)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
