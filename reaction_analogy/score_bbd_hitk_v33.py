#!/usr/bin/env python3
"""BBD v3.3 evaluator: re-score a v3.2 pool with the v3.3 fusion layer.

Reports BOTH evaluation口径 required by the DBP diagnostic protocol:
  strict-neutral-exact    raw stereo-blind canonical (v3.2 convention)
  charge-normalized       identities normalized with RDKit Uncharger before
                          comparison (neutral / [O-] count as one product)

Answer-key isolation: reads the answer key (like score_bbd_hitk_v32.py), but
NEVER writes it anywhere; v3.3 constants are a-priori chemistry priors.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from rdkit import RDLogger
RDLogger.DisableLog("rdApp.*")

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from score_bbd_hitk_v32 import load_answer_key, load_pool, _canon  # noqa: E402
from bbd_v33_fusion import score_candidates_v33, normalize_charge_smiles  # noqa: E402

KS = [1, 3, 5, 10, 20]


def hits_table(hits: dict[int, int], n: int) -> str:
    return "  ".join(f"Hit@{k}={hits[k]/max(n,1):.1%}" for k in KS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--answer", required=True)
    ap.add_argument("--stereo", default="blind", choices=["blind", "strict"])
    ap.add_argument("--top-k", type=int, default=20, help="truncate re-ranked list")
    ap.add_argument("--out-preds", default=None, help="write re-ranked predictions jsonl")
    ap.add_argument("--limit", type=int, default=0, help="only first N cases (debug)")
    args = ap.parse_args()
    stereo_blind = args.stereo == "blind"

    ak = load_answer_key(args.answer, stereo_blind)
    # charge-normalized truth view (stereo-blind, same as candidate side)
    from bbd_v33_fusion import stereo_blind
    ak_norm: dict[str, set[str]] = {}
    for pc, prods in ak.items():
        pcn = stereo_blind(normalize_charge_smiles(pc) or pc) or pc
        ak_norm.setdefault(pcn, set()).update(
            stereo_blind(normalize_charge_smiles(p) or p) or _canon(p, True)
            for p in prods)

    pool = load_pool(args.pool, stereo_blind)
    if args.limit > 0:
        pool = pool[:args.limit]

    hits_strict = {k: 0 for k in KS}
    hits_norm = {k: 0 for k in KS}
    mrr_strict = mrr_norm = 0.0
    n = 0
    n_flagged_top = 0
    n_merged_pairs = 0

    for cid, pc, cands in pool:
        truth = ak.get(pc)
        pcn = stereo_blind(normalize_charge_smiles(pc) or pc) or pc
        truth_n = ak_norm.get(pcn)
        if truth is None or truth_n is None:
            continue
        n += 1
        scored = score_candidates_v33(cands, pc)
        n_merged_pairs += len(cands) - len(scored)
        n_flagged_top += sum(1 for s in scored[:10] if s.get("skeleton_unexplained"))

        ranked = [(s["product_smiles"], s) for s in scored[:args.top_k]]
        # strict口径: merged candidate hits if ANY raw member variant exactly
        # matches truth (rank stays at the merged-candidate level)
        strict_hit_at = lambda k: any(
            any(c in truth for c in s["member_canons"]) for s in scored[:k])
        norm_ids = [stereo_blind(normalize_charge_smiles(smi) or smi)
                    or _canon(smi, True) for smi, _ in ranked]
        norm_hit_at = lambda k: any(p in truth_n for p in norm_ids[:k])

        for k in KS:
            if strict_hit_at(k):
                hits_strict[k] += 1
            if norm_hit_at(k):
                hits_norm[k] += 1

        for i, s in enumerate(scored[:10]):
            if any(c in truth for c in s["member_canons"]):
                mrr_strict += 1.0 / (i + 1)
                break
        for i, p in enumerate(norm_ids[:10]):
            if p in truth_n:
                mrr_norm += 1.0 / (i + 1)
                break

        if args.out_preds:
            rec = {
                "case_id": cid, "smiles": pc,
                "top_products": [{
                    "product_smiles": s["product_smiles"],
                    "source": s["source"],
                    "ns_score": s["ns_score"],
                    "n_independent_sources": s["n_independent_sources"],
                    "skeleton_unexplained": s["skeleton_unexplained"],
                    "skeleton_reason": s["skeleton_reason"],
                    "charge_variants": [v["product_smiles"] for v in s["charge_variants"]],
                } for _, s in ranked],
            }
            with open(args.out_preds, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    nn = max(n, 1)
    print(f"=== v3.3 fusion evaluation (cases={n}) ===")
    print(f"merged charge-variant pairs: {n_merged_pairs}")
    print(f"flagged candidates in top-10 (across cases): {n_flagged_top}")
    print(f"{'strict-neutral':16s} {hits_table(hits_strict, n)}  MRR@10={mrr_strict/nn:.4f}")
    print(f"{'charge-normalized':16s} {hits_table(hits_norm, n)}  MRR@10={mrr_norm/nn:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
