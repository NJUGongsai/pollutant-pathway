#!/usr/bin/env python3
"""BBD v3.2 evaluator: score, pool-recall, ablate, selector-analysis, leak-audit.

Fixes v3.1 scorer bugs (task §1.3):
  1. no-selector ablation: shadow mechanism `max over sources of (p_source/3)`
     (v3.1 wrongly used `p_source/3` with selector-distorted p_source).
  2. selector-analysis oracle: per-source ranker probabilities + per-case counting
     (v3.1 used post-arbitration p_source and double-counted).

New mode: `ion-ablate` (no-selector without ion filter — quantifies ion gain).

Answer-key isolation: this is the ONLY file that reads the answer key.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import bbd_v2_scoring as S2  # noqa: E402
import bbd_v32_ion_filter as IF  # noqa: E402

SOURCES = ("uspto", "envipath", "retrieval")
KS = [1, 3, 5, 10, 20]


def _canon(smi, stereo_blind=True):
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=not stereo_blind) if m else None


def _belongs(src, sk):
    return sk in src or (sk in ("uspto", "envipath") and src == "both")


def _ns_score(c):
    """no-selector shadow mechanism: max over belonging sources of (p_source/3)."""
    best = 0.0
    for sk in SOURCES:
        if _belongs(c.get("source", ""), sk):
            p = c.get(f"p_{sk}", 0.0)
            if p / 3.0 > best:
                best = p / 3.0
    return best


def _map_source_v2(src):
    has_u = "uspto" in src or src == "both"
    has_e = "envipath" in src or src == "both"
    has_r = "retrieval" in src
    if has_u and (has_e or has_r):
        return "both"
    if has_u:
        return "uspto"
    return "envipath"


def load_answer_key(path, stereo_blind=True):
    out = {}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            pc = _canon(r.get("parent_smiles", ""), stereo_blind)
            if not pc:
                continue
            prods = set()
            for ap in r.get("accepted_products", []):
                c = _canon(ap.get("product_smiles", ""), stereo_blind)
                if c:
                    prods.add(c)
            out[pc] = out.get(pc, set()) | prods
    return out


def load_predictions(path, stereo_blind=True):
    out = []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            pc = _canon(r.get("smiles", ""), stereo_blind)
            prods = [_canon(tp.get("product_smiles", ""), stereo_blind)
                     for tp in r.get("top_products", [])
                     if _canon(tp.get("product_smiles", ""), stereo_blind)]
            out.append((r.get("case_id", ""), pc, prods))
    return out


def load_pool(path, stereo_blind=True):
    out = []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            pc = _canon(r.get("smiles", ""), stereo_blind)
            cands = []
            for c in r.get("all_candidates", []):
                cc = _canon(c.get("product_smiles", ""), stereo_blind)
                if cc:
                    c2 = dict(c)
                    c2["_canon"] = cc
                    cands.append(c2)
            out.append((r.get("case_id", ""), pc, cands))
    return out


# --------------------------------------------------------------------------- #
def mode_score(args):
    stereo_blind = args.stereo == "blind"
    ak = load_answer_key(args.answer, stereo_blind)
    preds = load_predictions(args.preds, stereo_blind)
    hits = {k: 0 for k in KS}
    mrr = 0.0
    n = 0
    for cid, pc, prods in preds:
        if pc not in ak:
            continue
        n += 1
        truth = ak[pc]
        for k in KS:
            if any(p in truth for p in prods[:k]):
                hits[k] += 1
        for i, p in enumerate(prods[:10]):
            if p in truth:
                mrr += 1.0 / (i + 1)
                break
    nn = max(n, 1)
    print(f"=== Score (stereo={args.stereo}) ===")
    print(f"  matched: {n}/{len(preds)}")
    for k in KS:
        print(f"  Hit@{k:<2}: {hits[k]}/{n} = {hits[k]/nn:.1%}")
    print(f"  MRR@10: {mrr/nn:.4f}")
    return {f"hit_at_{k}": hits[k] for k in KS} | {"n": n, "mrr": round(mrr/nn, 4)}


def mode_pool_recall(args):
    stereo_blind = args.stereo == "blind"
    ak = load_answer_key(args.answer, stereo_blind)
    pool = load_pool(args.pool, stereo_blind)
    recall = {"uspto": 0, "envipath": 0, "retrieval": 0, "union": 0}
    n = 0
    for cid, pc, cands in pool:
        if pc not in ak:
            continue
        n += 1
        truth = ak[pc]
        allc = {c["_canon"] for c in cands}
        if any(t in allc for t in truth):
            recall["union"] += 1
        for sk in ("uspto", "envipath", "retrieval"):
            sc = {c["_canon"] for c in cands if _belongs(c.get("source", ""), sk)}
            if any(t in sc for t in truth):
                recall[sk] += 1
    nn = max(n, 1)
    print(f"=== Pool-recall (stereo={args.stereo}) ===")
    for k in ("uspto", "envipath", "retrieval", "union"):
        print(f"  {k:10s}: {recall[k]}/{n} = {recall[k]/nn:.1%}")
    return {f"{k}_recall": recall[k] for k in recall} | {"n": n}


def mode_ablate(args):
    stereo_blind = args.stereo == "blind"
    ak = load_answer_key(args.answer, stereo_blind)
    pool = load_pool(args.pool, stereo_blind)
    ablate = args.ablate

    hits = {k: 0 for k in KS}
    n = 0
    for cid, pc, cands in pool:
        if pc not in ak:
            continue
        n += 1
        truth = ak[pc]
        scored = []
        for c in cands:
            if ablate == "no-selector":
                score = _ns_score(c)
            elif ablate == "no-selector-no-ion":
                score = _ns_score(c)  # same scoring, but no ion sink
            elif ablate == "ion-ablate":
                score = _ns_score(c)  # ion filter OFF
            elif ablate == "v3-ranker":
                score = c.get("ranker_proba_v3", c.get("ranker_proba", 0.0))
            elif ablate == "v2-formula":
                v2_src = _map_source_v2(c.get("source", "uspto"))
                c2 = dict(c, source=v2_src,
                          mpnn_site_mean=c.get("mpnn_site_mean", 0.0),
                          mpnn_site_max=c.get("mpnn_site_max", 0.0))
                score = S2.score_candidate(c2)
            else:
                continue

            # ion filter: sink ions to bottom (except ion-ablate which disables it)
            ion = IF.is_ion_fragment(c.get("product_smiles", "")) if ablate != "ion-ablate" else False
            scored.append((ion, score, c["_canon"]))

        scored.sort(key=lambda x: (x[0], -x[1], x[2]))
        for k in KS:
            if any(p in truth for p in [s[2] for s in scored[:k]]):
                hits[k] += 1
    nn = max(n, 1)
    print(f"=== Ablate: {ablate} ===")
    for k in KS:
        print(f"  Hit@{k:<2}: {hits[k]}/{n} = {hits[k]/nn:.1%}")
    return {f"hit_at_{k}": hits[k] for k in KS} | {"ablate": ablate, "n": n}


def mode_selector_analysis(args):
    """Fixed oracle: per-source ranker probabilities, per-case counting."""
    ak = load_answer_key(args.answer, True)
    pool = load_pool(args.pool, True)
    n = 0
    n_oracle = 0
    w_dist = {sk: [] for sk in SOURCES}

    for cid, pc, cands in pool:
        if pc not in ak:
            continue
        n += 1
        truth = ak[pc]
        # w from selector (stored in v3.1 pool) or uniform
        w = cands[0].get("v31_weights", {}) if cands else {}
        for sk in SOURCES:
            w_dist[sk].append(w.get(sk, 1.0/3))

        # oracle: which source's top-1 (by per-source ranker prob) is truth?
        # FIXED: use per-source ranker probabilities (p_uspto etc.), not p_source
        # FIXED: count per-case (break after first source hits)
        for sk in SOURCES:
            sk_cands = [c for c in cands if _belongs(c.get("source", ""), sk)]
            if sk_cands:
                top = max(sk_cands, key=lambda c: c.get(f"p_{sk}", 0.0))
                if top["_canon"] in truth:
                    n_oracle += 1
                    break  # FIXED: per-case, not per-source

    nn = max(n, 1)
    print(f"=== Selector Analysis (fixed) ===")
    print(f"  cases: {n}")
    print(f"  oracle (best source top-1 hits, per-case): {n_oracle}/{n} = {n_oracle/nn:.1%}")
    for sk in SOURCES:
        vals = w_dist[sk]
        print(f"  w_{sk}: mean={sum(vals)/nn:.3f} min={min(vals):.3f} max={max(vals):.3f}")
    return {"n": n, "oracle_correct": n_oracle,
            "w_means": {sk: round(sum(v)/nn, 4) for sk, v in w_dist.items()}}


def mode_leak_audit(args):
    ak = load_answer_key(args.answer, True)
    pool = load_pool(args.pool, True)
    hits_all = {k: 0 for k in KS}
    hits_no = {k: 0 for k in KS}
    n = 0
    n_exact = 0
    n_truth_via_exact = 0

    for cid, pc, cands in pool:
        if pc not in ak:
            continue
        n += 1
        truth = ak[pc]
        # sort by v3.2 ranking (ion_filtered, -ns_score, product_smiles)
        scored_all = [(IF.is_ion_fragment(c.get("product_smiles","")),
                       c.get("ns_score", _ns_score(c)), c["_canon"])
                      for c in cands]
        scored_all.sort(key=lambda x: (x[0], -x[1], x[2]))
        no_exact = [c for c in cands if not c.get("donor_exact_match", False)]
        scored_no = [(IF.is_ion_fragment(c.get("product_smiles","")),
                       c.get("ns_score", _ns_score(c)), c["_canon"])
                      for c in no_exact]
        scored_no.sort(key=lambda x: (x[0], -x[1], x[2]))
        if any(c.get("donor_exact_match", False) for c in cands):
            n_exact += 1
        for k in KS:
            if any(p in truth for p in [s[2] for s in scored_all[:k]]):
                hits_all[k] += 1
            if any(p in truth for p in [s[2] for s in scored_no[:k]]):
                hits_no[k] += 1
        in_all = {s[2] for s in scored_all[:20] if s[2] in truth}
        in_no = {s[2] for s in scored_no[:20] if s[2] in truth}
        if in_all and not in_no:
            n_truth_via_exact += 1

    nn = max(n, 1)
    print(f"=== Leak-audit (dual口径) ===")
    print(f"  matched: {n}, exact cases: {n_exact}, truth-only-via-exact: {n_truth_via_exact}")
    print(f"  {'口径':20s}  Hit@1  Hit@3  Hit@5  Hit@10 Hit@20")
    print(f"  {'all (main)':20s}  " + "  ".join(f"{hits_all[k]/nn:.1%}" for k in KS))
    print(f"  {'no donor==parent':20s}  " + "  ".join(f"{hits_no[k]/nn:.1%}" for k in KS))
    return {"n": n, "n_exact": n_exact, "n_truth_via_exact": n_truth_via_exact,
            "all": {f"hit_at_{k}": hits_all[k] for k in KS},
            "no_exact": {f"hit_at_{k}": hits_no[k] for k in KS}}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("score"); p.add_argument("--preds", required=True); p.add_argument("--answer", required=True); p.add_argument("--stereo", default="blind", choices=["blind", "strict"]); p.add_argument("--json-out")
    p = sub.add_parser("pool-recall"); p.add_argument("--pool", required=True); p.add_argument("--answer", required=True); p.add_argument("--stereo", default="blind", choices=["blind", "strict"]); p.add_argument("--json-out")
    p = sub.add_parser("ablate"); p.add_argument("--pool", required=True); p.add_argument("--answer", required=True); p.add_argument("--ablate", required=True, choices=["no-selector", "no-selector-no-ion", "ion-ablate", "v3-ranker", "v2-formula"]); p.add_argument("--stereo", default="blind", choices=["blind", "strict"]); p.add_argument("--json-out")
    p = sub.add_parser("selector-analysis"); p.add_argument("--pool", required=True); p.add_argument("--answer", required=True); p.add_argument("--json-out")
    p = sub.add_parser("leak-audit"); p.add_argument("--pool", required=True); p.add_argument("--answer", required=True); p.add_argument("--json-out")
    args = ap.parse_args()
    modes = {"score": mode_score, "pool-recall": mode_pool_recall,
             "ablate": mode_ablate, "selector-analysis": mode_selector_analysis,
             "leak-audit": mode_leak_audit}
    result = modes[args.mode](args)
    if getattr(args, "json_out", None):
        with open(args.json_out, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
