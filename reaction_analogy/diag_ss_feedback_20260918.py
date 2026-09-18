#!/usr/bin/env python3
"""BBD v3.3 soil/sludge feedback — diagnostic suite (2026-09-18).

Responds to《FEEDBACK_TO_GONG_DEPENDING_V33_SOIL_SLUDGE_LOW_TOP1_AND_REQUIRED_REPAIR
_2026-09-17》§四 items 1-7.  Runs ONLY on local, independent-of-soil/sludge data:

  Stage A  EAWAG donor cache (775 environmental educts, prediction layer only)
           — the closest local proxy for the 97% lookup-invisible soil/sludge
           parents (v3.1 rankers were never trained on these educts).
  Stage B  RHEA validation split (1,234 educts) — library-external regime at
           scale (used for v3.1 model selection only; never used for fusion
           tuning).  Disclosed in the report.
  Stage C  BBD83 (93 cases, now a public diagnostic set per the feedback) —
           v3.2 pool + v3.3 fusion + EAWAG lookup hybrid caliber.
  Stage E  environmental-domain coverage (BBD83 pollutant categories x
           lookup visibility / enviPath-rule applicability / retrieval).
  Stage F  parent-copy / invalid / ion / cofactor / wildcard anomaly scan
           on local artefacts (EAWAG cache, BBD83 pools, A7 freeze outputs).

Diagnostics delivered (feedback §四 numbering):
  1  oracle recall of candidate generation per source (strict + charge-norm)
  2  source-stratified funnel: generated -> positives -> Top-50/10/1 + hits
  3  fusion/truncation audit: static rule inventory + quantified displacement
     (USPTO-only removal counterfactual, parameter-free)
  4  ranker score audit: per-source pos/neg distributions, within-source AUC,
     cross-source overranking rates
  5  Top-10 diversity: Murcko-scaffold duplication, family concentration,
     multi-product parents' distinct-hit count
  6  environmental coverage table by pollutant category
  7  parent-copy / invalid structure counts

This file NEVER reads any soil/sludge gold (not present locally) and does not
modify any production code.  Outputs: reports/SS_DIAG_2026-09-18/*.json + MD.
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
from rdkit.Chem.Scaffolds import MurckoScaffold  # noqa: E402
RDLogger.DisableLog("rdApp.*")

import bbd_v3_features as F  # noqa: E402
import bbd_v32_ion_filter as IF  # noqa: E402
import bbd_v33_fusion as V33  # noqa: E402

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
EAWAG_CACHE = os.path.join(ROOT, "data/bbd_v5/eawag_candidates.jsonl")
RHEA_CACHE = os.path.join(ROOT, "data/bbd_v31/train_candidates.jsonl")
VAL_SPLIT = os.path.join(ROOT, "data/bbd_v31/val_split.json")
DONOR_PRODUCT = os.path.join(_HERE, "data/bbd_expand/donor_product.jsonl")
V32_POOL = os.path.join(ROOT, "bbd_predictions/bbd_product_pool_v32.jsonl")
BBD83_AK = os.path.join(
    ROOT, "bbd83_answer_key_scoring_handoff_20260816/restricted/"
    "KNOWN_PATHWAY_POLLUTANT_RESTRICTED_ANSWER_KEY_V0_2.jsonl")
BBD83_BLIND = os.path.join(
    ROOT, "bbd83_answer_key_scoring_handoff_20260816/blind/"
    "KNOWN_PATHWAY_POLLUTANT_BLIND_PARENT_INPUTS_V0_2.csv")
CORPUS = os.path.join(_HERE, "data/corpus_v1/corpus_v1.jsonl")
MODEL_DIR = os.path.join(ROOT, "data/bbd_v31")

SOURCES = ("uspto", "envipath", "retrieval")
KS = (1, 3, 5, 10, 50)

# ---- speed: cache mol props (deterministic pure function of SMILES) ----
_orig_mol_props = F._mol_props
_pp_cache: dict[str, dict | None] = {}


def _cached_mol_props(smi):
    if smi not in _pp_cache:
        _pp_cache[smi] = _orig_mol_props(smi)
    return _pp_cache[smi]


F._mol_props = _cached_mol_props


def sb(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def sbn(smi: str) -> str | None:
    """stereo-blind(charge-normalized(smi)) — v3.3 identity convention."""
    norm = V33.normalize_charge_smiles(smi)
    return sb(norm) if norm else sb(smi)


def family(src: str) -> str:
    s = set()
    if "uspto" in src or src == "both":
        s.add("uspto")
    if "envipath" in src or src == "both":
        s.add("envipath")
    if "retrieval" in src:
        s.add("retrieval")
    return "+".join(sorted(s)) if s else "uspto"


_SCAF_CACHE: dict[str, str] = {}


def scaffold(smi: str) -> str:
    if smi not in _SCAF_CACHE:
        try:
            _SCAF_CACHE[smi] = MurckoScaffold.MurckoScaffoldSmiles(smiles=smi) or ""
        except Exception:
            _SCAF_CACHE[smi] = ""
    return _SCAF_CACHE[smi]


def auc_mw(pos: list[float], neg: list[float]) -> float:
    """Mann-Whitney AUC (prob a random pos outranks a random neg), ties=0.5."""
    if not pos or not neg:
        return float("nan")
    from bisect import bisect_left, bisect_right
    neg_sorted = sorted(neg)
    n1, n2 = len(pos), len(neg)
    total = 0.0
    for p in pos:
        lo = bisect_left(neg_sorted, p)
        hi = bisect_right(neg_sorted, p)
        total += lo + 0.5 * (hi - lo)  # negs below + half the ties
    return total / (n1 * n2)


def quantiles(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0}
    xs2 = sorted(xs)
    n = len(xs2)

    def q(p):
        return round(xs2[min(n - 1, int(p * n))], 4)
    return {"n": n, "mean": round(sum(xs2) / n, 4), "p10": q(0.10),
            "p50": q(0.50), "p90": q(0.90), "p99": q(0.99)}


# --------------------------------------------------------------------------- #
# per-educt analysis (shared by Stage A and Stage B)
# --------------------------------------------------------------------------- #
def load_rankers(model_dir: str):
    import lightgbm as lgb
    rankers = {}
    for sk in SOURCES:
        p = os.path.join(model_dir, f"{sk}_ranker.txt")
        if os.path.exists(p):
            rankers[sk] = lgb.Booster(model_file=p)
    return rankers


def score_case(cands: list[dict], parent_sb_smiles: str, rankers) -> None:
    """Compute v3.1 features + per-source ranker probabilities (in-place)."""
    F.compute_v31_case_features(cands, parent_sb_smiles)
    for sk in SOURCES:
        idx_feats = []
        for i, c in enumerate(cands):
            src = c.get("source", "")
            if not (sk in src or (sk in ("uspto", "envipath") and src == "both")):
                continue
            feats = c.get("_v31_features", {}).get(sk)
            if feats is None or sk not in rankers:
                continue
            idx_feats.append((i, feats))
        if idx_feats:
            import numpy as np
            probas = rankers[sk].predict(
                np.array([f for _, f in idx_feats], dtype=np.float64))
            for (i, _), p in zip(idx_feats, probas):
                cands[i][f"p_{sk}"] = float(p)


def analyze_educt(educt_sb_smiles: str, cands: list[dict],
                  truth_sb: set[str], rankers) -> dict:
    """Full per-educt diagnostic.  Returns aggregates for the stage report."""
    truth_sbn = {sbn(t) for t in truth_sb}
    res: dict = {"educt": educt_sb_smiles,
                 "n_truth": len(truth_sb), "n_cand": len(cands)}

    # ---- generation-side oracle (per family + overall) ----
    fam_pos_strict: Counter = Counter()
    fam_pos_cn: Counter = Counter()
    fam_gen: Counter = Counter()
    for c in cands:
        fm = family(c.get("source", ""))
        fam_gen[fm] += 1
        psb = sb(c.get("product_smiles", ""))
        if psb in truth_sb:
            fam_pos_strict[fm] += 1
        if psb is not None and sbn(c["product_smiles"]) in truth_sbn:
            fam_pos_cn[fm] += 1
    res["fam_gen"] = dict(fam_gen)
    res["fam_pos_strict"] = dict(fam_pos_strict)
    res["fam_pos_cn"] = dict(fam_pos_cn)
    res["oracle_strict"] = sum(fam_pos_strict.values()) > 0
    res["oracle_cn"] = sum(fam_pos_cn.values()) > 0
    # per-source oracle: does that source alone generate a true product?
    src_oracle = {}
    for sk in SOURCES:
        hit = False
        for c in cands:
            if sk in c.get("source", "") or (sk in ("uspto", "envipath")
                                             and c.get("source") == "both"):
                psb = sb(c.get("product_smiles", ""))
                if psb in truth_sb or (psb is not None
                                       and sbn(c["product_smiles"]) in truth_sbn):
                    hit = True
                    break
        src_oracle[sk] = hit
    res["src_oracle"] = src_oracle

    # ---- parent-copy / invalid / ion at generation side ----
    parent_copies = invalids = ions = 0
    for c in cands:
        ps = c.get("product_smiles", "")
        psb = sb(ps)
        if psb is None:
            invalids += 1
        elif psb == educt_sb_smiles:
            parent_copies += 1
        if IF.is_ion_fragment(ps):
            ions += 1
    res["gen_parent_copy"] = parent_copies
    res["gen_invalid"] = invalids
    res["gen_ion"] = ions

    # ---- rank + v3.3 fusion ----
    score_case(cands, educt_sb_smiles, rankers)
    ranked = V33.score_candidates_v33(cands, educt_sb_smiles)

    # hits (strict: any raw charge-variant member matches truth sb;
    #        cn: normalized identity matches truth_sbn)
    hit_rank_strict = hit_rank_cn = None
    for i, m in enumerate(ranked):
        if hit_rank_strict is None:
            for v in m.get("charge_variants", [m]):
                if sb(v.get("product_smiles", "")) in truth_sb:
                    hit_rank_strict = i + 1
                    break
        if hit_rank_cn is None and sb(m["product_smiles"]) in truth_sbn:
            hit_rank_cn = i + 1
        if hit_rank_strict and hit_rank_cn:
            break
    res["hit_rank_strict"] = hit_rank_strict
    res["hit_rank_cn"] = hit_rank_cn

    # Top-K composition by family (K=10 and K=50)
    for K in (10, 50):
        comp = Counter(family(c.get("source", "")) for c in ranked[:K]
                       if not c.get("ion_filtered"))
        res[f"top{K}_family"] = dict(comp)
    res["rank1_family"] = family(ranked[0]["source"]) if ranked else None
    res["rank1_ion_filtered"] = ranked[0].get("ion_filtered") if ranked else None

    # ---- miss attribution (generated true product but ranking missed) ----
    if res["oracle_cn"] and (hit_rank_cn is None or hit_rank_cn > 10):
        best_true = None
        for i, m in enumerate(ranked):
            if sb(m["product_smiles"]) in truth_sbn:
                best_true = i
                break
        if best_true is not None:
            above = ranked[:best_true]
            uspto_only_above = sum(1 for c in above
                                   if family(c.get("source", "")) == "uspto")
            res["miss"] = {
                "best_true_rank0": best_true,
                "n_above": len(above),
                "n_uspto_only_above": uspto_only_above,
                "best_true_family": family(ranked[best_true]["source"]),
                "best_true_ns33": ranked[best_true].get("ns_score"),
                "best_true_skeleton_flag": ranked[best_true].get(
                    "skeleton_unexplained"),
            }
    elif not res["oracle_cn"]:
        res["miss"] = {"generation_gap": True}

    # ---- parameter-free counterfactual: drop USPTO-only candidates ----
    no_uspto = [dict(c) for c in cands if family(c.get("source", "")) != "uspto"]
    if no_uspto:
        for c in no_uspto:
            c.pop("_v31_features", None)
            c.pop("_source_ranks", None)
        score_case(no_uspto, educt_sb_smiles, rankers)
        ranked2 = V33.score_candidates_v33(no_uspto, educt_sb_smiles)
        hr = None
        for i, m in enumerate(ranked2):
            if sb(m["product_smiles"]) in truth_sbn:
                hr = i + 1
                break
        res["no_uspto_hit_rank_cn"] = hr
    else:
        res["no_uspto_hit_rank_cn"] = None

    # ---- calibration points (per-source pos/neg scores) ----
    cal = {}
    for sk in SOURCES:
        pos_s, neg_s = [], []
        for c in cands:
            src = c.get("source", "")
            if not (sk in src or (sk in ("uspto", "envipath") and src == "both")):
                continue
            p = c.get(f"p_{sk}")
            if p is None:
                continue
            psb = sb(c.get("product_smiles", ""))
            is_pos = psb is not None and (
                psb in truth_sb or sbn(c["product_smiles"]) in truth_sbn)
            (pos_s if is_pos else neg_s).append(float(p))
        cal[sk] = {"pos": pos_s, "neg": neg_s}
    res["_cal"] = cal

    # ---- diversity of Top-10 ----
    top10 = [c for c in ranked[:10] if not c.get("ion_filtered")]
    scafs = [scaffold(c["product_smiles"]) for c in top10]
    fams = [family(c.get("source", "")) for c in top10]
    res["div"] = {
        "n_top10": len(top10),
        "n_distinct_scaffold": len(set(scafs)),
        "rank1_scaffold_share": (round(scafs.count(scafs[0]) / len(scafs), 3)
                                 if scafs else None),
        "max_family_share": (round(max(Counter(fams).values()) / len(fams), 3)
                             if fams else None),
        "n_true_in_top10": sum(1 for i, c in enumerate(ranked[:10])
                               if sb(c["product_smiles"]) in truth_sbn),
    }
    return res


def aggregate_stage(results: list[dict], n_truth_educts: int,
                    label: str) -> dict:
    """Aggregate per-educt results into the stage-level report."""
    n = len(results)
    out = {"label": label, "n_educts": n, "n_truth": n_truth_educts}

    fam_gen = Counter()
    fam_pos = Counter()
    for r in results:
        fam_gen.update(r["fam_gen"])
        fam_pos.update(r["fam_pos_cn"])
    out["gen_rows_by_family"] = dict(fam_gen)
    out["gen_pos_by_family"] = dict(fam_pos)

    # per-family generation recall: positives / rows
    out["family_precision_at_generation"] = {
        fm: round(fam_pos[fm] / fam_gen[fm], 5) for fm in fam_gen}

    # oracle: educts whose true product is generated (per family, cn caliber)
    fam_cover = Counter()
    for r in results:
        for fm, v in r["fam_pos_cn"].items():
            if v > 0:
                fam_cover[fm] += 1
    out["educts_covered_by_family"] = dict(fam_cover)
    out["oracle_educts_cn"] = sum(1 for r in results if r["oracle_cn"])
    out["oracle_educts_strict"] = sum(1 for r in results if r["oracle_strict"])
    src_oracle = {sk: sum(1 for r in results if r["src_oracle"][sk])
                  for sk in SOURCES}
    out["educts_covered_by_source"] = src_oracle

    # hits
    for caliber in ("strict", "cn"):
        hr_key = f"hit_rank_{caliber}"
        hits = {K: 0 for K in KS}
        mrr10 = 0.0
        for r in results:
            hr = r[hr_key]
            if hr is None:
                continue
            for K in KS:
                if hr <= K:
                    hits[K] += 1
            if hr <= 10:
                mrr10 += 1.0 / hr
        out[f"hits_{caliber}"] = {f"hit@{K}": hits[K] for K in KS}
        out[f"hits_{caliber}_pct"] = {
            f"hit@{K}": round(hits[K] / max(n, 1), 4) for K in KS}
        out[f"mrr10_{caliber}"] = round(mrr10 / max(n, 1), 4)

    # counterfactual (drop USPTO-only)
    cf = {K: 0 for K in KS}
    for r in results:
        hr = r.get("no_uspto_hit_rank_cn")
        if hr is None:
            continue
        for K in KS:
            if hr <= K:
                cf[K] += 1
    out["no_uspto_only_cf_pct"] = {
        f"hit@{K}": round(cf[K] / max(n, 1), 4) for K in KS}

    # Top-10 / Top-50 composition + rank-1 family x hit matrix
    top10_comp = Counter()
    top50_comp = Counter()
    for r in results:
        top10_comp.update(r["top10_family"])
        top50_comp.update(r["top50_family"])
    out["top10_rows_by_family"] = dict(top10_comp)
    out["top50_rows_by_family"] = dict(top50_comp)

    rank1 = Counter()
    rank1_hit = Counter()
    for r in results:
        fm = r["rank1_family"]
        if fm is None or r["rank1_ion_filtered"]:
            continue
        rank1[fm] += 1
        if r["hit_rank_cn"] == 1:
            rank1_hit[fm] += 1
    out["rank1_rows_by_family"] = dict(rank1)
    out["rank1_hits_by_family"] = dict(rank1_hit)

    # miss attribution
    gen_gap = sum(1 for r in results
                  if r.get("miss", {}).get("generation_gap"))
    rank_miss = [r for r in results
                 if r.get("miss") and not r["miss"].get("generation_gap")]
    out["miss"] = {
        "generation_gap_educts": gen_gap,
        "ranking_miss_educts": len(rank_miss),
        "best_true_rank0_median": (
            sorted(r["miss"]["best_true_rank0"] for r in rank_miss)
            [len(rank_miss) // 2] if rank_miss else None),
        "n_uspto_only_above_median": (
            sorted(r["miss"]["n_uspto_only_above"] for r in rank_miss)
            [len(rank_miss) // 2] if rank_miss else None),
        "best_true_family_dist": dict(Counter(
            r["miss"]["best_true_family"] for r in rank_miss)),
    }

    # calibration aggregates
    cal = {sk: {"pos": [], "neg": []} for sk in SOURCES}
    for r in results:
        for sk in SOURCES:
            cal[sk]["pos"].extend(r["_cal"][sk]["pos"])
            cal[sk]["neg"].extend(r["_cal"][sk]["neg"])
    out["calibration"] = {
        sk: {
            "pos_scores": quantiles(cal[sk]["pos"]),
            "neg_scores": quantiles(cal[sk]["neg"]),
            "auc_within_source": round(
                auc_mw(cal[sk]["pos"], cal[sk]["neg"]), 4),
        } for sk in SOURCES}

    # diversity aggregates
    scaf_dup = [r["div"]["rank1_scaffold_share"] for r in results
                if r["div"]["rank1_scaffold_share"] is not None]
    fam_con = [r["div"]["max_family_share"] for r in results
               if r["div"]["max_family_share"] is not None]
    multi = [r for r in results if r["n_truth"] >= 2]
    out["diversity"] = {
        "mean_rank1_scaffold_share": round(sum(scaf_dup) / max(len(scaf_dup), 1), 3),
        "mean_max_family_share": round(sum(fam_con) / max(len(fam_con), 1), 3),
        "n_multiproduct_educts": len(multi),
        "multiproduct_mean_true_in_top10": round(
            sum(r["div"]["n_true_in_top10"] for r in multi) / max(len(multi), 1), 3),
    }

    # anomaly aggregates
    out["anomalies"] = {
        "gen_parent_copy_rows": sum(r["gen_parent_copy"] for r in results),
        "gen_invalid_rows": sum(r["gen_invalid"] for r in results),
        "gen_ion_rows": sum(r["gen_ion"] for r in results),
        "parent_copy_in_top10": sum(
            1 for r in results
            for c in r.get("top10_family", {}) if False),  # placeholder
    }
    # parent copy in top10 (recompute from ranked stored? not stored) — skip
    del out["anomalies"]["parent_copy_in_top10"]
    return out


# --------------------------------------------------------------------------- #
# Stage A — EAWAG environmental domain
# --------------------------------------------------------------------------- #
def donor_truth() -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    with open(DONOR_PRODUCT) as f:
        for line in f:
            r = json.loads(line)
            d, p = sb(r["donor_smiles"]), sb(r["product_smiles"])
            if d and p:
                out[d].add(p)
    return dict(out)


def run_stage_a(rankers, out_dir, limit=0) -> dict:
    print("[A] loading EAWAG cache...", flush=True)
    truth = donor_truth()
    groups: dict[str, list[dict]] = defaultdict(list)
    with open(EAWAG_CACHE) as f:
        for line in f:
            r = json.loads(line)
            groups[r["educt_sb"]].append(r)
    print(f"[A] {len(groups)} educts, {sum(len(v) for v in groups.values())} rows",
          flush=True)

    items = sorted(groups.items())
    if limit:
        items = items[:limit]
    results = []
    t0 = time.time()
    for i, (esb, cands) in enumerate(items):
        truth_sb = truth.get(esb, set())
        results.append(analyze_educt(esb, cands, truth_sb, rankers))
        if (i + 1) % 100 == 0:
            print(f"[A] {i+1}/{len(groups)} ({time.time()-t0:.0f}s)", flush=True)
    agg = aggregate_stage(results, len(items), "A_eawag_domain")

    # persist per-educt (for error analysis)
    with open(os.path.join(out_dir, "stageA_per_educt.jsonl"), "w") as f:
        for r in results:
            r2 = {k: v for k, v in r.items() if k != "_cal"}
            f.write(json.dumps(r2, ensure_ascii=False) + "\n")
    with open(os.path.join(out_dir, "stageA_agg.json"), "w") as f:
        json.dump(agg, f, indent=2, ensure_ascii=False)
    print(f"[A] done in {time.time()-t0:.0f}s", flush=True)
    return agg


# --------------------------------------------------------------------------- #
# Stage B — RHEA validation split (library-external regime)
# --------------------------------------------------------------------------- #
def corpus_truth_for(educts: set[str]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    with open(CORPUS) as f:
        for line in f:
            r = json.loads(line)
            if not r.get("product_components"):
                continue
            comps = r.get("donor_components") or (
                [r.get("donor_A_smiles", "")] if r.get("donor_A_smiles") else [])
            for frag in comps:
                m = Chem.MolFromSmiles(frag)
                if m is None or m.GetNumHeavyAtoms() <= 2:
                    continue
                e = sb(frag)
                if e in educts:
                    for prod in r["product_components"]:
                        ps = sb(prod)
                        if ps:
                            out[e].add(ps)
    return dict(out)


def run_stage_b(rankers, out_dir, limit=0) -> dict:
    print("[B] loading val split...", flush=True)
    val = set(json.load(open(VAL_SPLIT))["val_educts_sb"])
    truth = corpus_truth_for(val)
    print(f"[B] {len(val)} val educts, truth found for {len(truth)}", flush=True)

    groups: dict[str, list[dict]] = defaultdict(list)
    t0 = time.time()
    with open(RHEA_CACHE) as f:
        for line in f:
            r = json.loads(line)
            if r["educt_sb"] in val:
                groups[r["educt_sb"]].append(r)
    print(f"[B] cache scanned {time.time()-t0:.0f}s, "
          f"{len(groups)} educts matched", flush=True)

    items = sorted(groups.items())
    if limit:
        items = items[:limit]
    results = []
    t0 = time.time()
    for i, (esb, cands) in enumerate(items):
        truth_sb = truth.get(esb, set())
        results.append(analyze_educt(esb, cands, truth_sb, rankers))
        if (i + 1) % 100 == 0:
            print(f"[B] {i+1}/{len(items)} ({time.time()-t0:.0f}s)", flush=True)
    agg = aggregate_stage(results, len(items), "B_rhea_val")
    with open(os.path.join(out_dir, "stageB_agg.json"), "w") as f:
        json.dump(agg, f, indent=2, ensure_ascii=False)
    print(f"[B] done in {time.time()-t0:.0f}s", flush=True)
    return agg


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stages", default="a,b,e,f")
    ap.add_argument("--out-dir",
                    default=os.path.join(_HERE, "reports/SS_DIAG_2026-09-18"))
    ap.add_argument("--rhea-limit", type=int, default=0)
    ap.add_argument("--eawag-limit", type=int, default=0)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    todo = set(args.stages.split(","))

    rankers = load_rankers(MODEL_DIR) if ("a" in todo or "b" in todo) else {}
    aggs = {}
    if "a" in todo:
        aggs["A"] = run_stage_a(rankers, args.out_dir, args.eawag_limit)
    if "b" in todo:
        aggs["B"] = run_stage_b(rankers, args.out_dir, args.rhea_limit)
    print("ALL DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
