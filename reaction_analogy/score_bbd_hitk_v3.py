#!/usr/bin/env python3
"""BBD v3 evaluator: Hit@K, pool-recall (3 sources), ablation, leak-audit.

Extends the v2 scorer with:
  - three-source pool recall (USPTO / enviPath / retrieval)
  - leak-audit mode (dual口径: with/without donor==parent candidates)
  - formula ablation (re-score v3 pool with v2's fixed formula)

Answer-key isolation: this is the ONLY file that reads the restricted answer
key.  All other v3 files never touch it.
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
import bbd_v2_scoring as S2  # noqa: E402 — for formula ablation


# --------------------------------------------------------------------------- #
# Canonicalisation helpers (shared with v2 scorer)
# --------------------------------------------------------------------------- #
def _canon(smi: str, stereo_blind: bool = True) -> str | None:
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    return Chem.MolToSmiles(m, isomericSmiles=not stereo_blind)


def _fragments(smi: str, stereo_blind: bool = True) -> set[str]:
    c = _canon(smi, stereo_blind)
    if c is None:
        return set()
    return {f for f in c.split(".") if f}


# --------------------------------------------------------------------------- #
# Answer-key / prediction loaders (same logic as v2 scorer)
# --------------------------------------------------------------------------- #
def load_answer_key(path: str, stereo_blind: bool = True) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            psmi = r.get("parent_smiles", "")
            pc = _canon(psmi, stereo_blind)
            if pc is None:
                continue
            prods = set()
            for ap in r.get("accepted_products", []):
                c = _canon(ap.get("product_smiles", ""), stereo_blind)
                if c is not None:
                    prods.add(c)
            if pc in out:
                out[pc] |= prods
            else:
                out[pc] = prods
    return out


def load_predictions(path: str, stereo_blind: bool = True):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            cid = r.get("case_id", "")
            smi = r.get("smiles", "")
            pc = _canon(smi, stereo_blind)
            prods = [_canon(tp.get("product_smiles", ""), stereo_blind)
                     for tp in r.get("top_products", [])
                     if _canon(tp.get("product_smiles", ""), stereo_blind) is not None]
            out.append((cid, pc, prods))
    return out


def load_pool(path: str, stereo_blind: bool = True):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            cid = r.get("case_id", "")
            smi = r.get("smiles", "")
            pc = _canon(smi, stereo_blind)
            cands = []
            for c in r.get("all_candidates", []):
                ps = c.get("product_smiles", "")
                cc = _canon(ps, stereo_blind)
                if cc is not None:
                    c2 = dict(c)
                    c2["_canon"] = cc
                    cands.append(c2)
            out.append((cid, pc, cands))
    return out


# --------------------------------------------------------------------------- #
# Source mapping for v2 formula ablation
# --------------------------------------------------------------------------- #
def _map_source_v2(src: str) -> str:
    """Map v3 three-engine source to v2's {uspto, envipath, both}."""
    has_u = "uspto" in src or src == "both"
    has_e = "envipath" in src or src == "both"
    has_r = "retrieval" in src
    # retrieval maps to enviPath branch (domain-matched candidate source)
    if has_u and (has_e or has_r):
        return "both"
    if has_u:
        return "uspto"
    return "envipath"  # envipath, retrieval, or envipath+retrieval


# --------------------------------------------------------------------------- #
# Mode 1: score
# --------------------------------------------------------------------------- #
def mode_score(args):
    stereo_blind = args.stereo == "blind"
    ak = load_answer_key(args.answer, stereo_blind)
    preds = load_predictions(args.preds, stereo_blind)
    ks = [1, 3, 5, 10, 20]
    hits = {k: 0 for k in ks}
    mrr_sum = 0.0
    n_matched = 0

    for cid, pc, prods in preds:
        if pc not in ak:
            continue
        n_matched += 1
        truth = ak[pc]
        for k in ks:
            if any(p in truth for p in prods[:k]):
                hits[k] += 1
        rank = None
        for i, p in enumerate(prods[:10]):
            if p in truth:
                rank = i + 1
                break
        if rank is not None:
            mrr_sum += 1.0 / rank

    n = max(n_matched, 1)
    print(f"=== Score (stereo={args.stereo}) ===")
    print(f"  matched: {n_matched}/{len(preds)}")
    for k in ks:
        print(f"  Hit@{k:<2}: {hits[k]}/{n_matched} = {hits[k]/n:.1%}")
    print(f"  MRR@10: {mrr_sum/n:.4f}")
    return {f"hit_at_{k}": hits[k] for k in ks} | {
        "n_matched": n_matched, "mrr_at_10": round(mrr_sum / n, 4)}


# --------------------------------------------------------------------------- #
# Mode 2: pool-recall (3 sources)
# --------------------------------------------------------------------------- #
def mode_pool_recall(args):
    stereo_blind = args.stereo == "blind"
    ak = load_answer_key(args.answer, stereo_blind)
    pool = load_pool(args.pool, stereo_blind)
    n_matched = 0
    recall = {"uspto": 0, "envipath": 0, "retrieval": 0, "union": 0}

    for cid, pc, cands in pool:
        if pc not in ak:
            continue
        n_matched += 1
        truth = ak[pc]
        all_canons = {c["_canon"] for c in cands}
        if any(t in all_canons for t in truth):
            recall["union"] += 1
        for src_key in ("uspto", "envipath", "retrieval"):
            src_canons = {c["_canon"] for c in cands
                          if src_key in c.get("source", "")
                          or (src_key in ("uspto", "envipath")
                              and c.get("source") == "both")}
            if any(t in src_canons for t in truth):
                recall[src_key] += 1

    n = max(n_matched, 1)
    print(f"=== Pool-recall (3 sources, stereo={args.stereo}) ===")
    print(f"  matched: {n_matched}")
    for k in ("uspto", "envipath", "retrieval", "union"):
        print(f"  {k:10s}: {recall[k]}/{n_matched} = {recall[k]/n:.1%}")
    return {f"{k}_recall": recall[k] for k in recall} | {"n_matched": n_matched}


# --------------------------------------------------------------------------- #
# Mode 3: ablate (engine-only + v2-formula)
# --------------------------------------------------------------------------- #
def mode_ablate(args):
    stereo_blind = args.stereo == "blind"
    ak = load_answer_key(args.answer, stereo_blind)
    pool = load_pool(args.pool, stereo_blind)
    ablate = args.ablate

    filter_source = None
    use_formula = False
    if ablate == "uspto-only":
        filter_source = {"uspto"}
    elif ablate == "envipath-only":
        filter_source = {"envipath"}
    elif ablate == "retrieval-only":
        filter_source = {"retrieval"}
    elif ablate == "v2-formula":
        use_formula = True
    else:
        print(f"Unknown ablation: {ablate}", file=sys.stderr)
        sys.exit(1)

    ks = [1, 3, 5, 10, 20]
    hits = {k: 0 for k in ks}
    n_matched = 0

    for cid, pc, cands in pool:
        if pc not in ak:
            continue
        n_matched += 1
        truth = ak[pc]
        scored = []
        for c in cands:
            if filter_source and not any(
                s in c.get("source", "")
                or (s in ("uspto", "envipath") and c.get("source") == "both")
                for s in filter_source
            ):
                continue
            if use_formula:
                # re-score with v2 formula
                v2_src = _map_source_v2(c.get("source", "uspto"))
                c2 = dict(c, source=v2_src)
                score = S2.score_candidate(c2)
            else:
                score = c.get("ranker_proba", 0.0)
            scored.append((score, c["_canon"]))
        scored.sort(key=lambda x: (-x[0], x[1]))
        for k in ks:
            if any(p in truth for p in [s[1] for s in scored[:k]]):
                hits[k] += 1

    n = max(n_matched, 1)
    print(f"=== Ablate: {ablate} (stereo={args.stereo}) ===")
    print(f"  matched: {n_matched}")
    for k in ks:
        print(f"  Hit@{k:<2}: {hits[k]}/{n_matched} = {hits[k]/n:.1%}")
    return {f"hit_at_{k}": hits[k] for k in ks} | {"ablate": ablate, "n_matched": n_matched}


# --------------------------------------------------------------------------- #
# Mode 4: leak-audit (dual口径)
# --------------------------------------------------------------------------- #
def mode_leak_audit(args):
    """Dual口径 Hit@K: with all candidates vs without donor==parent candidates."""
    stereo_blind = True
    ak = load_answer_key(args.answer, stereo_blind)
    pool = load_pool(args.pool, stereo_blind)
    ks = [1, 3, 5, 10, 20]
    hits_all = {k: 0 for k in ks}
    hits_no_exact = {k: 0 for k in ks}
    n_matched = 0
    n_exact_cases = 0  # cases with at least one donor_exact_match candidate
    n_truth_via_exact = 0  # cases where truth was found ONLY via donor==parent

    for cid, pc, cands in pool:
        if pc not in ak:
            continue
        n_matched += 1
        truth = ak[pc]

        # main口径: all candidates, ranked by ranker_proba
        scored_all = [(c.get("ranker_proba", 0.0), c["_canon"]) for c in cands]
        scored_all.sort(key=lambda x: (-x[0], x[1]))

        # 对照口径: remove candidates whose donor_exact_match is True
        # (but keep candidates that have non-exact evidence too)
        no_exact_cands = [c for c in cands
                          if not c.get("donor_exact_match", False)]
        scored_no = [(c.get("ranker_proba", 0.0), c["_canon"]) for c in no_exact_cands]
        scored_no.sort(key=lambda x: (-x[0], x[1]))

        has_exact = any(c.get("donor_exact_match", False) for c in cands)
        if has_exact:
            n_exact_cases += 1

        for k in ks:
            if any(p in truth for p in [s[1] for s in scored_all[:k]]):
                hits_all[k] += 1
            if any(p in truth for p in [s[1] for s in scored_no[:k]]):
                hits_no_exact[k] += 1

        # check if truth was found via exact-match-only candidates
        truth_in_all = set()
        for k in range(min(20, len(scored_all))):
            if scored_all[k][1] in truth:
                truth_in_all.add(scored_all[k][1])
        truth_in_no = set()
        for k in range(min(20, len(scored_no))):
            if scored_no[k][1] in truth:
                truth_in_no.add(scored_no[k][1])
        if truth_in_all and not truth_in_no:
            n_truth_via_exact += 1

    n = max(n_matched, 1)
    print(f"=== Leak-audit (donor==parent dual口径) ===")
    print(f"  matched: {n_matched}")
    print(f"  cases with donor_exact_match candidates: {n_exact_cases}")
    print(f"  cases where truth found ONLY via donor==parent: {n_truth_via_exact}")
    print(f"\n  {'口径':20s}  Hit@1  Hit@3  Hit@5  Hit@10 Hit@20")
    print(f"  {'all (main)':20s}  " + "  ".join(f"{hits_all[k]/n:.1%}" for k in ks))
    print(f"  {'no donor==parent':20s}  " + "  ".join(f"{hits_no_exact[k]/n:.1%}" for k in ks))
    return {
        "n_matched": n_matched,
        "n_exact_cases": n_exact_cases,
        "n_truth_via_exact": n_truth_via_exact,
        "all": {f"hit_at_{k}": hits_all[k] for k in ks},
        "no_donor_exact": {f"hit_at_{k}": hits_no_exact[k] for k in ks},
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)

    p = sub.add_parser("score")
    p.add_argument("--preds", required=True)
    p.add_argument("--answer", required=True)
    p.add_argument("--stereo", choices=["blind", "strict"], default="blind")
    p.add_argument("--json-out")

    p = sub.add_parser("pool-recall")
    p.add_argument("--pool", required=True)
    p.add_argument("--answer", required=True)
    p.add_argument("--stereo", choices=["blind", "strict"], default="blind")
    p.add_argument("--json-out")

    p = sub.add_parser("ablate")
    p.add_argument("--pool", required=True)
    p.add_argument("--answer", required=True)
    p.add_argument("--ablate", required=True,
                   choices=["uspto-only", "envipath-only", "retrieval-only", "v2-formula"])
    p.add_argument("--stereo", choices=["blind", "strict"], default="blind")
    p.add_argument("--json-out")

    p = sub.add_parser("leak-audit")
    p.add_argument("--pool", required=True)
    p.add_argument("--answer", required=True)
    p.add_argument("--json-out")

    args = ap.parse_args()
    if args.mode == "score":
        result = mode_score(args)
    elif args.mode == "pool-recall":
        result = mode_pool_recall(args)
    elif args.mode == "ablate":
        result = mode_ablate(args)
    elif args.mode == "leak-audit":
        result = mode_leak_audit(args)
    else:
        ap.print_help()
        sys.exit(1)

    if getattr(args, "json_out", None):
        with open(args.json_out, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
