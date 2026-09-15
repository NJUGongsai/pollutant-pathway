#!/usr/bin/env python3
"""BBD v2 evaluator: Hit@K, pool-recall, and ablation.

Three modes (all read the answer key; the predictor NEVER does):

    score       — Hit@1/3/5/10/20, MRR@10, Product Recall@K
    pool-recall — candidate-pool recall ceiling, by source
    ablate      — re-score from the pool file with a component disabled

Stereo口径:
    blind  (default) — both sides canonicalised with isomericSmiles=False
    strict           — isomericSmiles=True (reference only; Engine A does not
                       produce stereo, so blind is the fair main口径)

Case matching: canonical parent SMILES (same口径 as the scoring).  If two blind
cases map to the same answer-key parent, that is a *collision* (counted, not
deduplicated — each blind case is scored independently).

Answer-key isolation: this is the ONLY file that reads the restricted answer
key.  ``predict_bbd_products_v2.py`` and ``bbd_v2_scoring.py`` never do.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import bbd_v2_scoring as S  # noqa: E402


# --------------------------------------------------------------------------- #
# Canonicalisation helpers
# --------------------------------------------------------------------------- #
def _canon(smi: str, stereo_blind: bool = True) -> str | None:
    """Canonical SMILES.  stereo_blind=True → isomericSmiles=False."""
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    return Chem.MolToSmiles(m, isomericSmiles=not stereo_blind)


def _fragments(smi: str, stereo_blind: bool = True) -> set[str]:
    """All individual fragment canonical SMILES of *smi* (stereo-blind口径)."""
    c = _canon(smi, stereo_blind)
    if c is None:
        return set()
    return {f for f in c.split(".") if f}


# --------------------------------------------------------------------------- #
# Answer-key loader
# --------------------------------------------------------------------------- #
def load_answer_key(path: str, stereo_blind: bool = True) -> dict[str, set[str]]:
    """Return {parent_canonical: set(product_canonical)}.

    Products are the union of all ``accepted_products[].product_smiles``,
    canonicalised to the given口径.
    """
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
                ps = ap.get("product_smiles", "")
                c = _canon(ps, stereo_blind)
                if c is not None:
                    prods.add(c)
            if pc in out:
                out[pc] |= prods
            else:
                out[pc] = prods
    return out


def load_answer_key_raw(path: str, stereo_blind: bool = True):
    """Return list of (benchmark_case_id, parent_canonical, product_canonical_set)."""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            psmi = r.get("parent_smiles", "")
            pc = _canon(psmi, stereo_blind)
            if pc is None:
                continue
            prods = set()
            for ap in r.get("accepted_products", []):
                ps = ap.get("product_smiles", "")
                c = _canon(ps, stereo_blind)
                if c is not None:
                    prods.add(c)
            out.append((r.get("benchmark_case_id", ""), pc, prods))
    return out


# --------------------------------------------------------------------------- #
# Prediction loaders
# --------------------------------------------------------------------------- #
def load_predictions(path: str, stereo_blind: bool = True,
                     parent_filter: bool = False):
    """Return list of (case_id, parent_canonical, [product_canonical_topK]).

    Handles both v2 (``top_products`` with ``product_smiles``) and v1
    (``top_products`` with ``product_smiles``) formats.  If *parent_filter*
    is True, candidates whose stereo-blind canonical equals the parent's
    stereo-blind canonical are removed (for the v1 same-口径 baseline).
    """
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            cid = r.get("case_id", "")
            smi = r.get("smiles", "")
            pc = _canon(smi, stereo_blind)
            parent_sb = _canon(smi, stereo_blind=True)  # always stereo-blind for filter
            prods = []
            for tp in r.get("top_products", []):
                ps = tp.get("product_smiles", "")
                c = _canon(ps, stereo_blind)
                if c is None:
                    continue
                if parent_filter:
                    csb = _canon(ps, stereo_blind=True)
                    if csb == parent_sb:
                        continue
                prods.append(c)
            out.append((cid, pc, prods))
    return out


def load_pool(path: str, stereo_blind: bool = True):
    """Return list of (case_id, parent_canonical, [candidate_dict, ...]).

    Each candidate dict is the raw entry from ``all_candidates`` in the pool
    file, with an added ``_canon`` key (stereo-blind canonical product SMILES)
    and ``_source`` key.
    """
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
# Mode 1: score
# --------------------------------------------------------------------------- #
def mode_score(args):
    stereo_blind = args.stereo == "blind"
    ak = load_answer_key(args.answer, stereo_blind)
    preds = load_predictions(args.preds, stereo_blind, parent_filter=args.parent_filter)

    ks = [1, 3, 5, 10, 20]
    hits = {k: 0 for k in ks}
    mrr_sum = 0.0
    recall_sum = 0.0
    n_matched = 0
    n_unmatched = 0
    collisions = 0
    seen_parents: dict[str, int] = {}

    for cid, pc, prods in preds:
        if pc not in ak:
            n_unmatched += 1
            continue
        n_matched += 1
        seen_parents[pc] = seen_parents.get(pc, 0) + 1
        if seen_parents[pc] > 1:
            collisions += 1

        truth = ak[pc]
        # Hit@K
        for k in ks:
            topk = prods[:k]
            if any(p in truth for p in topk):
                hits[k] += 1
        # MRR@10
        rank = None
        for i, p in enumerate(prods[:10]):
            if p in truth:
                rank = i + 1
                break
        if rank is not None:
            mrr_sum += 1.0 / rank
        # Product Recall@K (fraction of truth products found in top-K)
        topk_set = set(prods[:10])
        if truth:
            recall_sum += len(truth & topk_set) / len(truth)

    n_eval = max(n_matched, 1)
    print(f"=== Score mode (stereo={args.stereo}, parent_filter={args.parent_filter}) ===")
    print(f"  predictions: {len(preds)} cases, matched: {n_matched}, unmatched: {n_unmatched}")
    print(f"  collisions (same parent mapped >1): {collisions}")
    print(f"  Hit@1:  {hits[1]}/{n_matched}  = {hits[1]/n_eval:.1%}")
    print(f"  Hit@3:  {hits[3]}/{n_matched}  = {hits[3]/n_eval:.1%}")
    print(f"  Hit@5:  {hits[5]}/{n_matched}  = {hits[5]/n_eval:.1%}")
    print(f"  Hit@10: {hits[10]}/{n_matched} = {hits[10]/n_eval:.1%}")
    print(f"  Hit@20: {hits[20]}/{n_matched} = {hits[20]/n_eval:.1%}")
    print(f"  MRR@10:       {mrr_sum/n_eval:.4f}")
    print(f"  Recall@10:    {recall_sum/n_eval:.4f}")
    return {
        "stereo": args.stereo, "parent_filter": args.parent_filter,
        "n_preds": len(preds), "n_matched": n_matched, "n_unmatched": n_unmatched,
        "collisions": collisions,
        **{f"hit_at_{k}": hits[k] for k in ks},
        **{f"hit_at_{k}_pct": round(hits[k] / n_eval * 100, 1) for k in ks},
        "mrr_at_10": round(mrr_sum / n_eval, 4),
        "recall_at_10": round(recall_sum / n_eval, 4),
    }


# --------------------------------------------------------------------------- #
# Mode 2: pool-recall
# --------------------------------------------------------------------------- #
def mode_pool_recall(args):
    stereo_blind = args.stereo == "blind"
    ak = load_answer_key(args.answer, stereo_blind)
    pool = load_pool(args.pool, stereo_blind)

    n_matched = 0
    recall = {"uspto": 0, "envipath": 0, "both": 0, "union": 0}
    per_source_counts = {"uspto": 0, "envipath": 0, "union": 0}

    for cid, pc, cands in pool:
        if pc not in ak:
            continue
        n_matched += 1
        truth = ak[pc]
        cand_canons = {c["_canon"] for c in cands}

        # union recall
        if any(t in cand_canons for t in truth):
            recall["union"] += 1

        # per-source recall
        uspto_canons = {c["_canon"] for c in cands
                        if c.get("source") in ("uspto", "both")}
        env_canons = {c["_canon"] for c in cands
                      if c.get("source") in ("envipath", "both")}

        if any(t in uspto_canons for t in truth):
            recall["uspto"] += 1
        if any(t in env_canons for t in truth):
            recall["envipath"] += 1

        per_source_counts["uspto"] += len(uspto_canons)
        per_source_counts["envipath"] += len(env_canons)
        per_source_counts["union"] += len(cand_canons)

    n = max(n_matched, 1)
    print(f"=== Pool-recall mode (stereo={args.stereo}) ===")
    print(f"  matched cases: {n_matched}")
    print(f"  USPTO recall:      {recall['uspto']}/{n_matched} = {recall['uspto']/n:.1%}")
    print(f"  enviPath recall:   {recall['envipath']}/{n_matched} = {recall['envipath']/n:.1%}")
    print(f"  Union recall:      {recall['union']}/{n_matched} = {recall['union']/n:.1%}")
    print(f"  mean candidates/case: uspto={per_source_counts['uspto']/n:.1f} "
          f"envipath={per_source_counts['envipath']/n:.1f} "
          f"union={per_source_counts['union']/n:.1f}")
    return {
        "stereo": args.stereo, "n_matched": n_matched,
        "uspto_recall": recall["uspto"], "envipath_recall": recall["envipath"],
        "union_recall": recall["union"],
        "uspto_recall_pct": round(recall["uspto"] / n * 100, 1),
        "envipath_recall_pct": round(recall["envipath"] / n * 100, 1),
        "union_recall_pct": round(recall["union"] / n * 100, 1),
        "mean_cands": {k: round(v / n, 1) for k, v in per_source_counts.items()},
    }


# --------------------------------------------------------------------------- #
# Mode 3: ablate
# --------------------------------------------------------------------------- #
def mode_ablate(args):
    stereo_blind = args.stereo == "blind"
    ak = load_answer_key(args.answer, stereo_blind)
    pool = load_pool(args.pool, stereo_blind)

    ablate = args.ablate
    mpnn_on = True
    src_on = True
    force_branch = None
    filter_source = None

    if ablate == "mpnn-off":
        mpnn_on = False
    elif ablate == "src-off":
        src_on = False
    elif ablate == "envipath-only":
        filter_source = {"envipath", "both"}
        force_branch = "envipath"
    elif ablate == "uspto-only":
        filter_source = {"uspto", "both"}
        force_branch = "uspto"
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

        # filter + re-score
        scored = []
        for c in cands:
            if filter_source and c.get("source") not in filter_source:
                continue
            score = S.score_candidate(c, mpnn_on=mpnn_on, src_on=src_on,
                                       force_branch=force_branch)
            scored.append((score, c["_canon"]))
        # deterministic sort: (-score, smiles)
        scored.sort(key=lambda x: (-x[0], x[1]))

        for k in ks:
            topk = [s[1] for s in scored[:k]]
            if any(p in truth for p in topk):
                hits[k] += 1

    n = max(n_matched, 1)
    print(f"=== Ablate: {ablate} (stereo={args.stereo}) ===")
    print(f"  matched cases: {n_matched}")
    for k in ks:
        print(f"  Hit@{k:<2}: {hits[k]}/{n_matched} = {hits[k]/n:.1%}")
    return {
        "ablate": ablate, "stereo": args.stereo, "n_matched": n_matched,
        **{f"hit_at_{k}": hits[k] for k in ks},
        **{f"hit_at_{k}_pct": round(hits[k] / n * 100, 1) for k in ks},
    }


# --------------------------------------------------------------------------- #
# hfix consistency check
# --------------------------------------------------------------------------- #
def mode_hfix_check(args):
    """Compare v2 enviPath pool with candidates_hfix.json on 83 shared parents.

    Both sides unified to stereo-blind canonical of *all* individual fragments
    (split product_smiles_full on '.').  Reports per-case |v2\\hfix| and
    |hfix\\v2|; flags cases where hfix has entries v2 lacks.
    """
    stereo_blind = True
    ak_raw = load_answer_key_raw(args.answer, stereo_blind)
    # Build parent canonical → benchmark_case_id map (v0.2 SPD-BBD2-* ids)
    ak_parent_to_cid = {pc: bid for bid, pc, _ in ak_raw}

    # v2 pool enviPath candidates
    pool = load_pool(args.pool, stereo_blind)

    # hfix reference pool
    with open(args.hfix, encoding="utf-8") as f:
        hfix = json.load(f)
    # hfix is keyed by SPD-BBD2-PARENT-* case id; values are lists of SMILES

    # For matching: v2 blind case parent SMILES → canonical → hfix case id
    # hfix case ids are SPD-BBD2-PARENT-*, answer key has benchmark_case_id
    # We match by parent canonical SMILES

    # Build hfix parent canonical → set of fragment canonicals
    hfix_by_parent = {}
    for bid, hfix_cands in hfix.items():
        # hfix case ids don't directly have parent SMILES; use answer key
        pass

    # We need parent SMILES for hfix cases. Load from answer key.
    # answer key: benchmark_case_id (SPD-BBD2-*), parent_smiles
    ak_parent_map = {}  # parent_canonical → benchmark_case_id
    with open(args.answer, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            pc = _canon(r.get("parent_smiles", ""), stereo_blind)
            bid = r.get("benchmark_case_id", "")
            if pc:
                ak_parent_map[pc] = bid

    # Build hfix fragment sets keyed by parent canonical
    hfix_frag_by_parent = {}
    for bid, hfix_cands in hfix.items():
        # find parent canonical for this benchmark_case_id
        pc = None
        for p, b in ak_parent_map.items():
            if b == bid:
                pc = p
                break
        if pc is None:
            continue
        frags = set()
        for s in hfix_cands:
            frags |= _fragments(s, stereo_blind)
        hfix_frag_by_parent[pc] = frags

    # Compare
    hfix_better = 0  # cases where hfix has entries v2 lacks
    v2_better = 0
    total_hfix_minus_v2 = 0
    total_v2_minus_hfix = 0
    details = []

    for cid, pc, cands in pool:
        if pc not in hfix_frag_by_parent:
            continue
        # v2 enviPath fragments
        v2_frags = set()
        for c in cands:
            if c.get("source") in ("envipath", "both"):
                v2_frags |= _fragments(c.get("product_smiles_full", ""),
                                       stereo_blind)
        hfix_frags = hfix_frag_by_parent[pc]

        h_minus_v = hfix_frags - v2_frags
        v_minus_h = v2_frags - hfix_frags

        total_hfix_minus_v2 += len(h_minus_v)
        total_v2_minus_hfix += len(v_minus_h)
        if h_minus_v:
            hfix_better += 1
        if v_minus_h:
            v2_better += 1
        details.append({
            "case_id": cid,
            "parent_canonical": pc,
            "hfix_minus_v2": len(h_minus_v),
            "v2_minus_hfix": len(v_minus_h),
            "hfix_only_samples": sorted(h_minus_v)[:5],
            "v2_only_samples": sorted(v_minus_h)[:5],
        })

    print(f"=== hfix consistency check (stereo-blind, all fragments) ===")
    print(f"  shared cases compared: {len(details)}")
    print(f"  cases where hfix has entries v2 lacks: {hfix_better}")
    print(f"  cases where v2 has entries hfix lacks: {v2_better}")
    print(f"  total hfix\\v2 fragments: {total_hfix_minus_v2}")
    print(f"  total v2\\hfix fragments: {total_v2_minus_hfix}")
    if hfix_better > 5:
        print(f"  WARNING: {hfix_better} cases with hfix-only entries (>5 threshold)")
        print("  Investigating top contributors:")
        for d in sorted(details, key=lambda x: -x["hfix_minus_v2"])[:5]:
            print(f"    {d['case_id']}: hfix\\v2={d['hfix_minus_v2']} "
                  f"v2\\hfix={d['v2_minus_hfix']} "
                  f"samples={d['hfix_only_samples'][:3]}")
    return {
        "n_compared": len(details),
        "hfix_better_cases": hfix_better,
        "v2_better_cases": v2_better,
        "total_hfix_minus_v2": total_hfix_minus_v2,
        "total_v2_minus_hfix": total_v2_minus_hfix,
        "details": details,
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)

    # score
    p_score = sub.add_parser("score", help="Evaluate predictions: Hit@K, MRR, recall")
    p_score.add_argument("--preds", required=True, help="predictions jsonl (v2 or v1)")
    p_score.add_argument("--answer", required=True, help="answer key jsonl")
    p_score.add_argument("--parent-filter", action="store_true",
                         help="remove parent copies from top-K (v1 baseline)")
    p_score.add_argument("--stereo", choices=["blind", "strict"], default="blind")
    p_score.add_argument("--json-out", help="write structured result to this file")

    # pool-recall
    p_pool = sub.add_parser("pool-recall", help="Candidate-pool recall ceiling by source")
    p_pool.add_argument("--pool", required=True, help="pool jsonl")
    p_pool.add_argument("--answer", required=True, help="answer key jsonl")
    p_pool.add_argument("--stereo", choices=["blind", "strict"], default="blind")
    p_pool.add_argument("--json-out", help="write structured result to this file")

    # ablate
    p_ab = sub.add_parser("ablate", help="Re-score from pool with a component disabled")
    p_ab.add_argument("--pool", required=True, help="pool jsonl")
    p_ab.add_argument("--answer", required=True, help="answer key jsonl")
    p_ab.add_argument("--ablate", required=True,
                      choices=["mpnn-off", "src-off", "envipath-only", "uspto-only"])
    p_ab.add_argument("--stereo", choices=["blind", "strict"], default="blind")
    p_ab.add_argument("--json-out", help="write structured result to this file")

    # hfix-check
    p_hf = sub.add_parser("hfix-check", help="Consistency check v2 enviPath pool vs hfix")
    p_hf.add_argument("--pool", required=True, help="pool jsonl")
    p_hf.add_argument("--answer", required=True, help="answer key jsonl")
    p_hf.add_argument("--hfix", required=True, help="candidates_hfix.json")
    p_hf.add_argument("--json-out", help="write structured result to this file")

    args = ap.parse_args()

    if args.mode == "score":
        result = mode_score(args)
    elif args.mode == "pool-recall":
        result = mode_pool_recall(args)
    elif args.mode == "ablate":
        result = mode_ablate(args)
    elif args.mode == "hfix-check":
        result = mode_hfix_check(args)
    else:
        ap.print_help()
        sys.exit(1)

    if getattr(args, "json_out", None):
        with open(args.json_out, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
