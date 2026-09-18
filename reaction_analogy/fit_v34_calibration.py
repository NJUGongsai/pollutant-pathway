#!/usr/bin/env python3
"""Fit + validate the v3.4 per-source calibration and Top-K policy (2026-09-18).

Data discipline (feedback §六 "不能使用test gold调权重"):
  - CALIB/VAL: EAWAG donor cache split 50/50 by seeded shuffle (seed=0).
    Environmental domain, never used to train the v3.1 rankers.
  - REGRESSION: BBD83 (public diagnostic set per the feedback) — evaluated
    AFTER parameter selection, reported as-is.
  - RHEA val (1,234 educts): domain-shift reference, evaluated after
    selection via diag stage B artefacts when available.
  - soil/sludge gold: NEVER read (not present locally).

Steps:
  1. score every EAWAG-cache candidate with the three local v3.1 rankers
  2. fit one isotonic per source on the CALIB split (label = strict-or-cn
     truth match)
  3. evaluate on VAL: v3.3 baseline vs v3.4 (raw) vs v3.4+policy grid
     (max_same_scaffold x min_env), Hit@K/MRR + Top-10 composition
  4. select policy params by val hit@10 then hit@1 (ties -> simpler policy)
  5. BBD83 regression: v3.3 hybrid vs v3.4 hybrid (lookup pinned, same
     P4.2 semantics)
  6. persist: data/bbd_v34/calibrator.json + reports/SS_DIAG_2026-09-18/
     v34_fit_report.json (+ md table)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "src"))

from rdkit import Chem, RDLogger  # noqa: E402
RDLogger.DisableLog("rdApp.*")

import bbd_v33_fusion as V33  # noqa: E402
import bbd_v34_fusion as V34  # noqa: E402
import diag_ss_feedback_20260918 as D  # noqa: E402

ROOT = D.ROOT
OUT_DIR = os.path.join(_HERE, "reports/SS_DIAG_2026-09-18")
CALIB_DIR = os.path.join(ROOT, "data/bbd_v34")
KS = (1, 3, 5, 10, 50)


def family(src: str) -> str:
    return D.family(src)


def hits_and_mrr(per_case: list[dict], key: str = "hit_rank") -> dict:
    n = len(per_case)
    out = {}
    for K in KS:
        out[f"hit@{K}"] = sum(1 for r in per_case
                              if r[key] is not None and r[key] <= K)
    mrr = sum(1.0 / r[key] for r in per_case
              if r[key] is not None and r[key] <= 10)
    out["n"] = n
    out["mrr10"] = round(mrr / max(n, 1), 4)
    for K in KS:
        out[f"hit@{K}_pct"] = round(out[f"hit@{K}"] / max(n, 1), 4)
    return out


def topk_composition(per_case: list[dict], k: int = 10,
                     key: str = "topk_fams") -> dict:
    comp = Counter()
    for r in per_case:
        comp.update(r[key][:k])
    total = sum(comp.values())
    return {fm: round(v / max(total, 1), 3) for fm, v in comp.items()} | {
        "_rows": total}


def evaluate_ranked(ranked: list[dict], truth_sb: set[str],
                    truth_sbn: set[str], policy: tuple | None) -> dict:
    """Measure one ranked list under both calibers (+optional policy)."""
    if policy is not None:
        k, ms, me = policy
        ranked = V34.apply_topk_policy(ranked, k=k, max_same_scaffold=ms,
                                       min_env=me)
    hr_strict = hr_cn = None
    fams = []
    for i, m in enumerate(ranked[:50]):
        if i < 10:
            fams.append(family(m.get("source", "")))
        if hr_strict is None:
            if (m.get("layer") == "lookup"
                    or m.get("source") == "eawag_lookup"):
                if D.sb(m.get("product_smiles", "")) in truth_sb:
                    hr_strict = i + 1
            else:
                for v in m.get("charge_variants", [m]):
                    if D.sb(v.get("product_smiles", "")) in truth_sb:
                        hr_strict = i + 1
                        break
        if hr_cn is None and D.sbn(m.get("product_identity",
                                        m.get("product_smiles", ""))
                                   ) in truth_sbn:
            hr_cn = i + 1
        if hr_strict and hr_cn:
            break
    return {"hit_rank_strict": hr_strict, "hit_rank_cn": hr_cn,
            "topk_fams": fams}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--val-frac", type=float, default=0.5)
    ap.add_argument("--out-dir", default=OUT_DIR)
    ap.add_argument("--calib-dir", default=CALIB_DIR)
    ap.add_argument("--skip-bbd83", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.calib_dir, exist_ok=True)

    t0 = time.time()
    rankers = D.load_rankers(os.path.join(ROOT, "data/bbd_v31"))
    print(f"rankers loaded: {list(rankers)}", flush=True)

    # ---- 1. load EAWAG cache + truth, split calib/val ----
    truth = D.donor_truth()
    groups: dict[str, list[dict]] = defaultdict(list)
    with open(D.EAWAG_CACHE) as f:
        for line in f:
            r = json.loads(line)
            groups[r["educt_sb"]].append(r)
    educts = sorted(groups)
    rng = random.Random(args.seed)
    rng.shuffle(educts)
    n_val = int(len(educts) * args.val_frac)
    val_educts = set(educts[:n_val])
    calib_educts = [e for e in educts if e not in val_educts]
    print(f"split: {len(calib_educts)} calib / {len(val_educts)} val "
          f"(seed={args.seed})", flush=True)

    # ---- 2. score all candidates once; keep in memory ----
    def truth_sets(esb):
        ts = truth.get(esb, set())
        return ts, {D.sbn(t) for t in ts}

    calib_pairs: dict[str, list[tuple[float, int]]] = defaultdict(list)
    all_pairs: dict[str, list[tuple[float, int]]] = defaultdict(list)  # AUC diag
    val_cases: list[dict] = []
    val_truth: dict[str, tuple[set, set]] = {}

    all_educts = [("calib", e) for e in sorted(calib_educts)] + \
        [("val", e) for e in sorted(val_educts)]
    scored_cache: dict[str, list[dict]] = {}  # esb -> scored candidate dicts
    for i, (split, esb) in enumerate(all_educts):
        cands = [dict(c) for c in groups[esb]]
        D.score_case(cands, esb, rankers)
        scored_cache[esb] = cands
        ts, tsn = truth_sets(esb)
        if split == "calib":
            for c in cands:
                psb = D.sb(c.get("product_smiles", ""))
                is_pos = psb is not None and (
                    psb in ts or D.sbn(c["product_smiles"]) in tsn)
                for sk in D.SOURCES:
                    src = c.get("source", "")
                    if sk in src or (sk in ("uspto", "envipath")
                                     and src == "both"):
                        p = c.get(f"p_{sk}")
                        if p is not None:
                            calib_pairs[sk].append((float(p), int(is_pos)))
                            all_pairs[sk].append((float(p), int(is_pos)))
        else:
            for c in cands:
                psb = D.sb(c.get("product_smiles", ""))
                is_pos = psb is not None and (
                    psb in ts or D.sbn(c["product_smiles"]) in tsn)
                for sk in D.SOURCES:
                    src = c.get("source", "")
                    if sk in src or (sk in ("uspto", "envipath")
                                     and src == "both"):
                        p = c.get(f"p_{sk}")
                        if p is not None:
                            all_pairs[sk].append((float(p), int(is_pos)))
            val_truth[esb] = (ts, tsn)
            val_cases.append({"educt": esb, "cands": cands})
        if (i + 1) % 200 == 0:
            print(f"  scored {i+1}/{len(all_educts)} "
                  f"({time.time()-t0:.0f}s)", flush=True)

    # full-domain within-source AUC (diagnostic; correct tie handling)
    domain_auc = {}
    for sk in D.SOURCES:
        rows = all_pairs[sk]
        pos = [p for p, lab in rows if lab]
        neg = [p for p, lab in rows if not lab]
        domain_auc[sk] = {
            "n": len(rows), "pos": len(pos),
            "auc_within_source": round(D.auc_mw(pos, neg), 4),
            "pos_rate": round(len(pos) / max(len(rows), 1), 5),
        }
    print("domain AUC:", json.dumps(domain_auc), flush=True)

    # ---- 3. fit calibrator ----
    calib = V34.SourceCalibrator()
    calib.fit({sk: calib_pairs[sk] for sk in D.SOURCES})
    print("calibrator meta:", json.dumps(calib.meta), flush=True)
    calib.save(os.path.join(args.calib_dir, "calibrator_v34.json"))
    cuts = {sk: {"cuts": calib._cuts.get(sk), "vals": calib._vals.get(sk)}
            for sk in D.SOURCES}
    with open(os.path.join(args.out_dir, "v34_calibrator_cuts.json"),
              "w") as f:
        json.dump(cuts, f, indent=2)

    # ---- 3b. design selection on the CALIB split (val untouched here) ----
    # Compare v3.3 vs v3.4 combiners (max / noisy-OR) on the calib split only;
    # the val split below is a one-shot report for the SELECTED design.
    # NOTE: reuse the SCORED candidate dicts from the loop above (fresh dicts
    # from `groups` would lack the p_* ranker scores).
    calib_cases = []
    for esb in sorted(calib_educts):
        cands = scored_cache[esb]
        ts, tsn = truth_sets(esb)
        calib_cases.append({"educt": esb, "cands": cands, "ts": ts, "tsn": tsn})

    def eval_calib(mode: str) -> list[dict]:
        per_case = []
        for cc in calib_cases:
            if mode == "v33":
                ranked = V33.score_candidates_v33(
                    [dict(c) for c in cc["cands"]], cc["educt"])
            else:
                ranked = V34.score_candidates_v34(
                    [dict(c) for c in cc["cands"]], cc["educt"], calib,
                    combiner=mode)
            res = evaluate_ranked(ranked, cc["ts"], cc["tsn"], None)
            per_case.append({"educt": cc["educt"], **res})
        return per_case

    calib_eval = {mode: eval_calib(mode) for mode in ("v33", "max", "noisy_or")}
    calib_summary = {mode: hits_and_mrr(pc, "hit_rank_cn")
                     for mode, pc in calib_eval.items()}
    print("calib-split design comparison:", json.dumps(
        {m: {"h1": calib_summary[m]["hit@1_pct"],
             "h10": calib_summary[m]["hit@10_pct"],
             "mrr": calib_summary[m]["mrr10"]}
         for m in calib_summary}), flush=True)
    # selection rule (pre-registered): hit@1 first, then hit@10, then mrr
    best_combiner = max(("max", "noisy_or"),
                        key=lambda m: (calib_summary[m]["hit@1"],
                                       calib_summary[m]["hit@10"],
                                       calib_summary[m]["mrr10"]))
    if calib_summary[best_combiner]["hit@1"] <= calib_summary["v33"]["hit@1"] \
            and calib_summary[best_combiner]["hit@10"] < \
            calib_summary["v33"]["hit@10"]:
        best_combiner = "v33"  # calibration not better on calib -> keep v3.3
    print(f"selected combiner: {best_combiner}", flush=True)
    # fusion is computed once per case; policies only reorder the cached list
    val_ranked_v33: list[dict] = []
    val_ranked_v34: list[dict] = []
    for vc in val_cases:
        ts, tsn = val_truth[vc["educt"]]
        val_ranked_v33.append({
            "educt": vc["educt"], "ts": ts, "tsn": tsn,
            "ranked": V33.score_candidates_v33(
                [dict(c) for c in vc["cands"]], vc["educt"])})
        val_ranked_v34.append({
            "educt": vc["educt"], "ts": ts, "tsn": tsn,
            "ranked": V34.score_candidates_v34(
                [dict(c) for c in vc["cands"]], vc["educt"], calib,
                combiner=best_combiner if best_combiner != "v33" else "max")})
        if len(val_ranked_v34) % 100 == 0:
            print(f"  fused val {len(val_ranked_v34)}/{len(val_cases)}",
                  flush=True)

    def run_val(mode: str, policy=None) -> list[dict]:
        per_case = []
        for vc in (val_ranked_v33 if mode == "v33" else val_ranked_v34):
            ranked = [dict(c) for c in vc["ranked"]]
            res = evaluate_ranked(ranked, vc["ts"], vc["tsn"], policy)
            per_case.append({"educt": vc["educt"], **res})
        return per_case

    results = {}
    results["v33_baseline"] = run_val("v33")
    results["v34_raw"] = run_val("v34", policy=None)

    grid = []
    for ms in (10, 3, 2):          # 10 = scaffold cap off
        for me in (0, 2, 3):
            if ms == 10 and me == 0:
                continue  # == raw
            pc = run_val("v34", policy=(10, ms, me))
            grid.append({"max_same_scaffold": ms, "min_env": me,
                         **hits_and_mrr(pc, "hit_rank_cn"),
                         "top10": topk_composition(pc)})
    with open(os.path.join(args.out_dir, "v34_val_grid.json"), "w") as f:
        json.dump(grid, f, indent=2)

    summary = {
        "split": {"seed": args.seed, "n_calib": len(calib_educts),
                  "n_val": len(val_educts)},
        "calibrator_meta": calib.meta,
        "domain_auc_full_cache": domain_auc,
        "calib_design_selection": {
            "rule": "hit@1 > hit@10 > mrr on calib split; v33 kept if both "
                    "worse",
            "calib_results": {m: {"hit@1_pct": calib_summary[m]["hit@1_pct"],
                                  "hit@10_pct": calib_summary[m]["hit@10_pct"],
                                  "mrr10": calib_summary[m]["mrr10"]}
                              for m in calib_summary},
            "selected_combiner": best_combiner,
        },
        "v33_val": hits_and_mrr(results["v33_baseline"], "hit_rank_cn"),
        "v33_val_strict": hits_and_mrr(results["v33_baseline"],
                                       "hit_rank_strict"),
        "v34_raw_val": hits_and_mrr(results["v34_raw"], "hit_rank_cn"),
        "v34_raw_val_strict": hits_and_mrr(results["v34_raw"],
                                           "hit_rank_strict"),
        "v33_top10": topk_composition(results["v33_baseline"]),
        "v34_top10": topk_composition(results["v34_raw"]),
        "grid": [{k: v for k, v in g.items() if k != "top10"}
                 for g in grid],
    }
    print(json.dumps({k: summary[k] for k in
                      ("v33_val", "v34_raw_val")}, indent=1), flush=True)

    # ---- 5. BBD83 regression (after selection; report as-is) ----
    if not args.skip_bbd83:
        import eawag_lookup as EGD
        import diag_ss_stagesCEF_20260918 as CEF
        ak = CEF.load_ak()
        index = EGD.build_index(D.DONOR_PRODUCT)
        index.pop("__parse_fail__", None)
        cases = [json.loads(line) for line in open(D.V32_POOL)]

        def run_bbd(mode: str, policy=None) -> list[dict]:
            per_case = []
            for r in cases:
                smi = r["smiles"]
                psb = D.sb(smi)
                tr = ak.get(psb) if psb else None
                if tr is None:
                    continue
                tsn = {D.sbn(t) for t in tr}
                cands = [dict(c) for c in r.get("all_candidates", [])]
                for c in cands:
                    c.pop("_v31_features", None)
                if mode == "v33":
                    ranked = V33.score_candidates_v33(cands, smi)
                    res = evaluate_ranked(ranked, tr, tsn, None)
                else:
                    ranked = V34.score_candidates_v34(
                        cands, smi, calib,
                        combiner=best_combiner if best_combiner != "v33"
                        else "max")
                    res = evaluate_ranked(ranked, tr, tsn, policy)
                # hybrid: lookup pinned, prediction deduped
                look = EGD.lookup(index, smi)
                if look:
                    look_canons = {c["product_smiles"] for c in look}
                    pred = [c for c in ranked if
                            D.sb(c.get("product_identity",
                                       c.get("product_smiles", "")))
                            not in look_canons]
                    merged = list(look) + pred
                    hr = None
                    for i, m in enumerate(merged):
                        hit = (D.sb(m.get("product_smiles", "")) in tr) or (
                            D.sbn(m.get("product_identity",
                                        m.get("product_smiles", ""))
                                  ) in tsn)
                        if hit:
                            hr = i + 1
                            break
                    res = {"hit_rank_strict": hr, "hit_rank_cn": hr,
                           "topk_fams": [
                               "eawag_lookup" if
                               (m.get("layer") == "lookup" or
                                m.get("source") == "eawag_lookup") else
                               family(m.get("source", ""))
                               for m in merged[:10]]}
                per_case.append({"case": r.get("case_id"), **res})
            return per_case

        results["bbd83_v33_hybrid"] = run_bbd("v33")
        results["bbd83_v34_hybrid_raw"] = run_bbd("v34", policy=None)
        sel_policy = (V34.DEFAULT_TOPK, V34.DEFAULT_MAX_SAME_SCAFFOLD,
                      V34.DEFAULT_MIN_ENV)
        results["bbd83_v34_hybrid_policy"] = run_bbd("v34", policy=sel_policy)
        summary["bbd83_v33_hybrid"] = hits_and_mrr(
            results["bbd83_v33_hybrid"], "hit_rank_cn")
        summary["bbd83_v34_hybrid_raw"] = hits_and_mrr(
            results["bbd83_v34_hybrid_raw"], "hit_rank_cn")
        summary["bbd83_v34_hybrid_policy"] = hits_and_mrr(
            results["bbd83_v34_hybrid_policy"], "hit_rank_cn")
        summary["bbd83_policy_params"] = sel_policy

    # persist per-case + summary
    with open(os.path.join(args.out_dir, "v34_fit_per_case.jsonl"), "w") as f:
        for name, pc in results.items():
            for r in pc:
                f.write(json.dumps({"eval": name, **r},
                                   ensure_ascii=False) + "\n")
    with open(os.path.join(args.out_dir, "v34_fit_report.json"), "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"DONE in {time.time()-t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
