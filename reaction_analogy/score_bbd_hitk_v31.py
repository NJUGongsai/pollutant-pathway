#!/usr/bin/env python3
"""BBD v3.1 evaluator: Hit@K, ablation, selector-analysis, leak-audit.

Extends v3 scorer with:
  - ablate: v3-ranker (single model) / no-selector (uniform w) / v2-formula
  - selector-analysis: per-case w distribution vs oracle source choice
  - leak-audit: dual口径 (with/without donor==parent)

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


def _canon(smi, stereo_blind=True):
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=not stereo_blind) if m else None


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


def _map_source_v2(src):
    has_u = "uspto" in src or src == "both"
    has_e = "envipath" in src or src == "both"
    has_r = "retrieval" in src
    if has_u and (has_e or has_r):
        return "both"
    if has_u:
        return "uspto"
    return "envipath"


KS = [1, 3, 5, 10, 20]


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
            sc = {c["_canon"] for c in cands
                  if sk in c.get("source", "")
                  or (sk in ("uspto", "envipath") and c.get("source") == "both")}
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
            if ablate == "v3-ranker":
                score = c.get("ranker_proba_v3", c.get("ranker_proba", 0.0))
            elif ablate == "no-selector":
                # uniform weights: final = p_source / 3
                score = c.get("p_source", 0.0) / 3.0
            elif ablate == "v2-formula":
                v2_src = _map_source_v2(c.get("source", "uspto"))
                c2 = dict(c, source=v2_src,
                          mpnn_site_mean=c.get("mpnn_site_mean", 0.0),
                          mpnn_site_max=c.get("mpnn_site_max", 0.0))
                score = S2.score_candidate(c2)
            else:
                continue
            scored.append((score, c["_canon"]))
        scored.sort(key=lambda x: (-x[0], x[1]))
        for k in KS:
            if any(p in truth for p in [s[1] for s in scored[:k]]):
                hits[k] += 1
    nn = max(n, 1)
    print(f"=== Ablate: {ablate} ===")
    for k in KS:
        print(f"  Hit@{k:<2}: {hits[k]}/{n} = {hits[k]/nn:.1%}")
    return {f"hit_at_{k}": hits[k] for k in KS} | {"ablate": ablate, "n": n}


def mode_selector_analysis(args):
    ak = load_answer_key(args.answer, True)
    pool = load_pool(args.pool, True)
    n = 0
    n_exact = 0
    n_oracle_correct = 0
    w_dist = {"uspto": [], "envipath": [], "retrieval": []}

    for cid, pc, cands in pool:
        if pc not in ak:
            continue
        n += 1
        truth = ak[pc]
        # get weights from first candidate
        w = cands[0].get("v31_weights", {}) if cands else {}
        for sk in ("uspto", "envipath", "retrieval"):
            w_dist[sk].append(w.get(sk, 0.0))

        # oracle: which source's top-1 is the true product?
        for sk in ("uspto", "envipath", "retrieval"):
            sk_cands = [c for c in cands
                        if sk in c.get("source", "")
                        or (sk in ("uspto", "envipath") and c.get("source") == "both")]
            if sk_cands:
                top = max(sk_cands, key=lambda c: c.get("p_source", 0.0))
                if top["_canon"] in truth:
                    n_oracle_correct += 1
                    break
        if any(c.get("donor_exact_match", False) for c in cands):
            n_exact += 1

    nn = max(n, 1)
    print(f"=== Selector Analysis ===")
    print(f"  cases: {n}")
    print(f"  oracle (best source top-1 hits): {n_oracle_correct}/{n} = {n_oracle_correct/nn:.1%}")
    for sk in ("uspto", "envipath", "retrieval"):
        vals = w_dist[sk]
        print(f"  w_{sk}: mean={sum(vals)/nn:.3f} min={min(vals):.3f} max={max(vals):.3f}")
    return {"n": n, "oracle_correct": n_oracle_correct,
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
        scored_all = [(c.get("final_score", 0.0), c["_canon"]) for c in cands]
        scored_all.sort(key=lambda x: (-x[0], x[1]))
        no_exact = [c for c in cands if not c.get("donor_exact_match", False)]
        scored_no = [(c.get("final_score", 0.0), c["_canon"]) for c in no_exact]
        scored_no.sort(key=lambda x: (-x[0], x[1]))
        if any(c.get("donor_exact_match", False) for c in cands):
            n_exact += 1
        for k in KS:
            if any(p in truth for p in [s[1] for s in scored_all[:k]]):
                hits_all[k] += 1
            if any(p in truth for p in [s[1] for s in scored_no[:k]]):
                hits_no[k] += 1
        # truth found only via exact?
        in_all = set()
        for k in range(min(20, len(scored_all))):
            if scored_all[k][1] in truth:
                in_all.add(scored_all[k][1])
        in_no = set()
        for k in range(min(20, len(scored_no))):
            if scored_no[k][1] in truth:
                in_no.add(scored_no[k][1])
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
    p = sub.add_parser("ablate"); p.add_argument("--pool", required=True); p.add_argument("--answer", required=True); p.add_argument("--ablate", required=True, choices=["v3-ranker", "no-selector", "v2-formula"]); p.add_argument("--stereo", default="blind", choices=["blind", "strict"]); p.add_argument("--json-out")
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
