#!/usr/bin/env python3
"""Stage C/E/F addendum for diag_ss_feedback_20260918.py (2026-09-18).

Runs the remaining diagnostics on local data:
  Stage C  BBD83 (93-case v3.2 pool) — v3.3 fusion + EAWAG lookup hybrid
           caliber vs the merged answer key; per-family funnel, rank-1
           composition, lookup-visible/excluded split, Top-10 diversity.
  Stage E  environmental coverage by pollutant category: lookup visibility,
           enviPath-rule applicability (286 rules actually deployed in v3.3),
           EAWAG-rule applicability (49 rules, v5-only today), retrieval
           evidence, oracle/hit outcome.
  Stage F  parent-copy / invalid / empty anomaly scan on the A7 freeze
           outputs (deployed-artefact mirror of the feedback's §3.4 counts).

Reuses helpers from diag_ss_feedback_20260918 (same directory).  NEVER reads
any soil/sludge gold (not present locally); the BBD83 answer key is treated
as a public diagnostic set per the feedback §六.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "src"))

from rdkit import Chem, RDLogger  # noqa: E402
RDLogger.DisableLog("rdApp.*")

import diag_ss_feedback_20260918 as D  # noqa: E402
import bbd_v33_fusion as V33  # noqa: E402

ROOT = D.ROOT
OUT_DEFAULT = os.path.join(_HERE, "reports/SS_DIAG_2026-09-18")
ENVIPATH_RULES = os.path.join(ROOT, "data/hfix/templates_implicitH.jsonl")
ENVIPATH_TSV = os.path.join(
    ROOT, "reaction_v3/data/lib_envipath/templates.tsv.gz")
EAWAG_RULES = os.path.join(
    _HERE, "data/bbd_expand/rules_new_clean.jsonl")
KS = D.KS


def load_ak() -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    with open(D.BBD83_AK) as f:
        for line in f:
            r = json.loads(line)
            pc = D.sb(r.get("parent_smiles", ""))
            if not pc:
                continue
            for ap in r.get("accepted_products", []):
                c = D.sb(ap.get("product_smiles", ""))
                if c:
                    out[pc].add(c)
    return dict(out)


# --------------------------------------------------------------------------- #
# Stage C
# --------------------------------------------------------------------------- #
def run_stage_c(out_dir: str) -> dict:
    import eawag_lookup as EGD
    print("[C] BBD83 v3.2 pool + v3.3 fusion + lookup...", flush=True)
    ak = load_ak()
    index = EGD.build_index(D.DONOR_PRODUCT)
    index.pop("__parse_fail__", None)

    cases = []
    with open(D.V32_POOL) as f:
        for line in f:
            cases.append(json.loads(line))
    print(f"[C] {len(cases)} pool cases, {len(ak)} answer-key parents",
          flush=True)

    results = []
    for r in cases:
        smi = r["smiles"]
        psb = D.sb(smi)
        truth = ak.get(psb) if psb else None
        if truth is None:
            continue
        truth_sbn = {D.sbn(t) for t in truth}
        cands = [dict(c) for c in r.get("all_candidates", [])]
        for c in cands:
            c.pop("_v31_features", None)
            c.pop("_source_ranks", None)
        ranked = V33.score_candidates_v33(cands, smi)

        look = EGD.lookup(index, smi)
        look_canons = {c["product_smiles"] for c in look}
        pred_dedup = [c for c in ranked
                      if D.sb(c.get("product_smiles", "")) not in look_canons]
        merged = list(look) + pred_dedup if look else list(ranked)

        def _is_hit(m) -> bool:
            if (m.get("layer") == "lookup"
                    or m.get("source") == "eawag_lookup"):
                if D.sb(m.get("product_smiles", "")) in truth:
                    return True
            else:
                for v in m.get("charge_variants", [m]):
                    if D.sb(v.get("product_smiles", "")) in truth:
                        return True
            return D.sbn(m.get("product_smiles", "")) in truth_sbn

        hit_rank = next((i + 1 for i, m in enumerate(merged) if _is_hit(m)),
                        None)
        hit_rank_pred = next(
            (i + 1 for i, m in enumerate(ranked)
             if D.sbn(m["product_smiles"]) in truth_sbn
             or any(D.sb(v.get("product_smiles", "")) in truth
                    for v in m.get("charge_variants", [m]))), None)

        def fam(m):
            if (m.get("layer") == "lookup"
                    or m.get("source") == "eawag_lookup"):
                return "eawag_lookup"
            return D.family(m.get("source", ""))

        top10 = [c for c in merged[:10] if not c.get("ion_filtered")]
        top10_fam = Counter(fam(c) for c in top10)
        pc_top10 = inv_top10 = 0
        for c in merged[:10]:
            cps = c.get("product_smiles", "")
            csb = D.sb(cps)
            if csb is None:
                inv_top10 += 1
            elif psb and csb == psb:
                pc_top10 += 1
        scafs = [D.scaffold(c.get("product_smiles", "")) for c in top10]

        results.append({
            "case_id": r.get("case_id"), "parent": psb,
            "n_truth": len(truth), "n_cand": r.get("n_cand_union", len(cands)),
            "lookup_hit": bool(look), "n_lookup": len(look),
            "hit_rank_hybrid": hit_rank, "hit_rank_pred": hit_rank_pred,
            "rank1_family": fam(merged[0]) if merged else None,
            "rank1_hit": hit_rank == 1,
            "top10_family": dict(top10_fam),
            "oracle_pred_cn": hit_rank_pred is not None,
            "parent_copy_top10": pc_top10, "invalid_top10": inv_top10,
            "div": {
                "n_top10": len(top10),
                "n_distinct_scaffold": len(set(scafs)),
                "rank1_scaffold_share": (
                    round(scafs.count(scafs[0]) / len(scafs), 3)
                    if scafs else None),
                "n_true_in_top10": sum(1 for m in merged[:10] if _is_hit(m)),
            },
        })

    n = len(results)
    hits = {K: 0 for K in KS}
    hits_pred = {K: 0 for K in KS}
    hits_lu_excl = {K: 0 for K in KS}
    n_lu_excl = 0
    mrr = 0.0
    rank1 = Counter()
    rank1_hit = Counter()
    top10_comp = Counter()
    pc10 = inv10 = 0
    for res in results:
        for K in KS:
            hr = res["hit_rank_hybrid"]
            hp = res["hit_rank_pred"]
            if hr is not None and hr <= K:
                hits[K] += 1
            if hp is not None and hp <= K:
                hits_pred[K] += 1
            if not res["lookup_hit"] and hp is not None and hp <= K:
                hits_lu_excl[K] += 1
        if not res["lookup_hit"]:
            n_lu_excl += 1
        if res["hit_rank_hybrid"] is not None and res["hit_rank_hybrid"] <= 10:
            mrr += 1.0 / res["hit_rank_hybrid"]
        if res["rank1_family"]:
            rank1[res["rank1_family"]] += 1
            if res["rank1_hit"]:
                rank1_hit[res["rank1_family"]] += 1
        top10_comp.update(res["top10_family"])
        pc10 += res["parent_copy_top10"]
        inv10 += res["invalid_top10"]

    multi = [r for r in results if r["n_truth"] >= 2]
    agg = {
        "label": "C_bbd83", "n_cases": n,
        "n_lookup_visible": sum(1 for r in results if r["lookup_hit"]),
        "n_lookup_excluded": n_lu_excl,
        "hits_hybrid_pct": {f"hit@{K}": round(hits[K] / max(n, 1), 4)
                            for K in KS},
        "hits_prediction_only_pct": {
            f"hit@{K}": round(hits_pred[K] / max(n, 1), 4) for K in KS},
        "hits_prediction_lookup_excluded_pct": {
            f"hit@{K}": round(hits_lu_excl[K] / max(n_lu_excl, 1), 4)
            for K in KS},
        "mrr10_hybrid": round(mrr / max(n, 1), 4),
        "rank1_rows_by_family": dict(rank1),
        "rank1_hits_by_family": dict(rank1_hit),
        "top10_rows_by_family": dict(top10_comp),
        "oracle_pred_cn": sum(1 for r in results if r["oracle_pred_cn"]),
        "parent_copy_top10_rows": pc10,
        "invalid_top10_rows": inv10,
        "diversity": {
            "mean_rank1_scaffold_share": round(
                sum((r["div"]["rank1_scaffold_share"] or 0)
                    for r in results) / max(n, 1), 3),
            "n_multiproduct": len(multi),
            "multiproduct_mean_true_in_top10": round(
                sum(r["div"]["n_true_in_top10"] for r in multi)
                / max(len(multi), 1), 3),
        },
    }
    with open(os.path.join(out_dir, "stageC_per_case.jsonl"), "w") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(out_dir, "stageC_agg.json"), "w") as f:
        json.dump(agg, f, indent=2, ensure_ascii=False)
    print(f"[C] done: hybrid hit@1={agg['hits_hybrid_pct']['hit@1']:.1%}, "
          f"pred-only hit@1={agg['hits_prediction_only_pct']['hit@1']:.1%}, "
          f"pred-only (lookup-excl) hit@1="
          f"{agg['hits_prediction_lookup_excluded_pct']['hit@1']:.1%} "
          f"on {n_lu_excl} cases", flush=True)
    return agg


# --------------------------------------------------------------------------- #
# Stage E
# --------------------------------------------------------------------------- #
def run_stage_e(out_dir: str) -> dict:
    import csv as _csv
    import eawag_lookup as EGD
    import eawag_rules_engine as ERE
    import predict_bbd_products_v2 as P2

    print("[E] coverage by pollutant category...", flush=True)
    index = EGD.build_index(D.DONOR_PRODUCT)
    index.pop("__parse_fail__", None)
    rules_b, _skip = P2._load_envipath_rules(ENVIPATH_RULES, ENVIPATH_TSV)
    rules_e = ERE.load_eawag_rules(EAWAG_RULES)
    print(f"[E] {len(rules_b)} enviPath rules, {len(rules_e)} EAWAG rules",
          flush=True)

    c_by_parent = {}
    p = os.path.join(out_dir, "stageC_per_case.jsonl")
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                r = json.loads(line)
                c_by_parent[r["parent"]] = r

    retrieval_ev: dict[str, float] = {}
    with open(D.V32_POOL) as f:
        for line in f:
            r = json.loads(line)
            psb = D.sb(r.get("smiles", ""))
            if not psb:
                continue
            tans = [c.get("max_tanimoto", 0.0)
                    for c in r.get("all_candidates", [])
                    if "retrieval" in c.get("source", "")]
            retrieval_ev[psb] = max(tans) if tans else 0.0

    rows = []
    with open(D.BBD83_BLIND, encoding="utf-8") as f:
        for row in _csv.DictReader(f):
            smi = row["parent_smiles"]
            psb = D.sb(smi)
            mol = Chem.MolFromSmiles(smi)
            if not psb or mol is None:
                continue
            lu = EGD.lookup(index, smi)
            n_rules_b = sum(1 for rule in rules_b
                            if mol.HasSubstructMatch(rule["rt"]))
            n_rules_e = sum(1 for rule in rules_e
                            if mol.HasSubstructMatch(rule["rt"]))
            cr = c_by_parent.get(psb, {})
            rows.append({
                "case_id": row["benchmark_case_id"],
                "category": row["pollutant_category"],
                "parent": psb,
                "lookup_visible": bool(lu),
                "n_envipath_rules_matched": n_rules_b,
                "n_eawag_rules_matched": n_rules_e,
                "retrieval_max_tanimoto": round(
                    retrieval_ev.get(psb, 0.0), 3),
                "v33_pred_hit1": cr.get("hit_rank_pred") == 1,
                "v33_hybrid_hit1": cr.get("hit_rank_hybrid") == 1,
                "oracle_cn": cr.get("oracle_pred_cn", False),
            })

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    cat_table = {}
    for cat, rs in sorted(by_cat.items()):
        cat_table[cat] = {
            "n": len(rs),
            "lookup_visible": sum(1 for r in rs if r["lookup_visible"]),
            "envipath_rule_zero": sum(
                1 for r in rs if r["n_envipath_rules_matched"] == 0),
            "eawag_rule_zero": sum(
                1 for r in rs if r["n_eawag_rules_matched"] == 0),
            "retrieval_tanimoto_median": sorted(
                r["retrieval_max_tanimoto"] for r in rs)[len(rs) // 2],
            "pred_hit1": sum(1 for r in rs if r["v33_pred_hit1"]),
            "hybrid_hit1": sum(1 for r in rs if r["v33_hybrid_hit1"]),
            "oracle_cn": sum(1 for r in rs if r["oracle_cn"]),
        }
    agg = {"n_parents": len(rows),
           "envipath_rules_total": len(rules_b),
           "eawag_rules_total": len(rules_e),
           "by_category": cat_table}
    with open(os.path.join(out_dir, "stageE_coverage.json"), "w") as f:
        json.dump({"aggregate": agg, "rows": rows}, f, indent=2,
                  ensure_ascii=False)
    print(f"[E] done: {len(rows)} parents, {len(cat_table)} categories",
          flush=True)
    return agg


# --------------------------------------------------------------------------- #
# Stage F
# --------------------------------------------------------------------------- #
A7_DIR = os.path.join(
    _HERE, "reports/T62_A7_GOLD_2026-09-15/normalized")


def run_stage_f(out_dir: str) -> dict:
    print("[F] anomaly scan (parent-copy / invalid / empty)...", flush=True)
    out = {}

    def scan(path: str, label: str):
        pc = inv = empty = 0
        n_rows = 0
        cases: dict[str, dict] = {}
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                # A7 normalized schema: one row per case x rank
                if "prediction_rank" in r or "case_id" in r and \
                        "predicted_product_smiles_canonical" in r:
                    cid = r.get("case_id", "")
                    psb = D.sb(r.get("parent_smiles", ""))
                    try:
                        rank = int(r.get("prediction_rank", 0) or 0)
                    except (TypeError, ValueError):
                        continue
                    if rank == 0:
                        continue
                    c = cases.setdefault(cid, {"psb": psb, "ranks": {}})
                    c["ranks"][rank] = r.get(
                        "predicted_product_smiles_canonical",
                        r.get("predicted_product_smiles_original", ""))
                    continue
                # predictions-file schema: one row per case with a list
                psb = D.sb(r.get("smiles", r.get("parent_smiles", "")))
                prods = r.get("top_products", r.get("predictions", []))
                if not prods:
                    empty += 1
                for tp in prods[:10]:
                    s = tp.get("product_smiles", tp.get("smiles", ""))
                    n_rows += 1
                    csb = D.sb(s)
                    if csb is None:
                        inv += 1
                    elif psb and csb == psb:
                        pc += 1
        for cid, c in cases.items():
            top = [c["ranks"][k] for k in sorted(c["ranks"])[:10]]
            if not top:
                empty += 1
            for s in top:
                n_rows += 1
                csb = D.sb(s)
                if csb is None:
                    inv += 1
                elif c["psb"] and csb == c["psb"]:
                    pc += 1
        out[label] = {"top10_rows": n_rows, "parent_copy_top10": pc,
                      "invalid_top10": inv, "empty_cases": empty}

    if os.path.isdir(A7_DIR):
        for fn in sorted(os.listdir(A7_DIR)):
            if fn.endswith(".jsonl"):
                scan(os.path.join(A7_DIR, fn), f"a7:{fn}")
    with open(os.path.join(out_dir, "stageF_anomalies.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"[F] done: {list(out)}", flush=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stages", default="c,e,f")
    ap.add_argument("--out-dir", default=OUT_DEFAULT)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    todo = set(args.stages.split(","))
    if "c" in todo:
        run_stage_c(args.out_dir)
    if "e" in todo:
        run_stage_e(args.out_dir)
    if "f" in todo:
        run_stage_f(args.out_dir)
    print("ALL DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
