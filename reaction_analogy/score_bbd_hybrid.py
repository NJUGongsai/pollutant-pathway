#!/usr/bin/env python3
"""BBD P4.2 evaluator — three calibers + attribution + dual donor==parent.

Three calibers (task §4.4), all from the single hybrid pool:

  hybrid       Layer 1 (lookup) pinned + Layer 2 (prediction) fallback.
               Uses the merged ``top_products`` order as emitted by the
               predictor (answer-key-isolated structural pinning).
  prediction   Lookup OFF: only ``layer == "prediction"`` candidates, re-ranked
               at full precision (``ns_score_full`` from the pool's three p_
               fields) with cofactor + ion filter — the "fixed prediction
               layer" baseline (病 1 cofactor + 病 2 round(6)).
  lookup-only  Only ``layer == "lookup"`` candidates, in Tanimoto order.

Dual donor==parent 口径 (照旧, leak-audit discipline): for each caliber, also
score a "no donor==parent" variant that excludes ``donor_exact_match`` candidates
(EAWAG lookup hits AND RHEA retrieval exact-donor hits), disclosing how much of
the score rests on exact-donor evidence.

Attribution: per case, the layer ("lookup"/"prediction") of the first hit and
its rank, so the contribution of each engine is auditable.

Answer-key isolation: this is the ONLY file that reads the answer key.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import bbd_v32_ion_filter as IF  # noqa: E402
import bbd_cofactor_filter as CF  # noqa: E402

SOURCES = ("uspto", "envipath", "retrieval")
KS = [1, 3, 5, 10, 20]


def _canon(smi, stereo_blind=True):
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=not stereo_blind) if m else None


def _belongs(src, sk):
    return sk in src or (sk in ("uspto", "envipath") and src == "both")


def ns_score_full(c):
    """max over belonging sources of (p_source/3), NO round (§4.6)."""
    best = 0.0
    src = c.get("source", "")
    for sk in SOURCES:
        if _belongs(src, sk):
            p = float(c.get(f"p_{sk}", 0.0))
            if p / 3.0 > best:
                best = p / 3.0
    return best


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


def load_pool(path, stereo_blind=True):
    """Return [(case_id, parent_canon, [candidate_dicts_with__canon])]."""
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


def load_preds(path, stereo_blind=True):
    """Return [(case_id, parent_canon, [top_product_canon])]."""
    out = []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            pc = _canon(r.get("smiles", ""), stereo_blind)
            prods = [_canon(t.get("product_smiles", ""), stereo_blind)
                     for t in r.get("top_products", [])]
            prods = [p for p in prods if p]
            out.append((r.get("case_id", ""), pc, prods))
    return out


def _rank_prediction(cands):
    """Re-rank prediction-layer candidates: (filtered, -ns_score_full, smiles)."""
    scored = []
    for c in cands:
        prod = c.get("product_smiles", "")
        ion = IF.is_ion_fragment(prod)
        cof = CF.is_cofactor_conjugate(prod)
        scored.append((bool(ion or cof), ns_score_full(c), c["_canon"], c))
    scored.sort(key=lambda x: (x[0], -x[1], x[2]))
    return [s[3] for s in scored]


def _eval(prods, truth, ks=KS):
    """Return {hit_at_k} for an ordered product list vs truth set."""
    out = {}
    for k in ks:
        out[f"hit_at_{k}"] = int(any(p in truth for p in prods[:k]))
    return out


def _first_hit_layer(prods_with_layer, truth):
    """Return (layer, rank) of first hit, or (None, None)."""
    for i, (canon, layer) in enumerate(prods_with_layer):
        if canon in truth:
            return layer, i + 1
    return None, None


def caliber_hybrid(preds, ak):
    hits = {k: 0 for k in KS}
    mrr = 0.0
    n = 0
    attrib = Counter()
    first_hit_rank = []
    for cid, pc, prods in preds:
        if pc not in ak:
            continue
        n += 1
        truth = ak[pc]
        h = _eval(prods, truth)
        for k in KS:
            hits[k] += h[f"hit_at_{k}"]
        for i, p in enumerate(prods[:10]):
            if p in truth:
                mrr += 1.0 / (i + 1)
                break
        # attribution via pool not available here; caller augments from pool
    nn = max(n, 1)
    return _format("hybrid", hits, mrr, n, nn)


def _format(name, hits, mrr, n, nn):
    line = f"  {name:14s}: " + "  ".join(f"H@{k}={hits[k]}/{n}={hits[k]/nn:.1%}"
                                         for k in KS)
    print(line)
    print(f"  {'':14s}  MRR@10={mrr/nn:.4f}  (n={n})")
    return {f"hit_at_{k}": hits[k] for k in KS} | {
        "n": n, "mrr": round(mrr / nn, 4)}


def _caliber_prediction(name, v32pool, ak):
    """Prediction-only caliber: lookup OFF, v3.2 candidate set re-ranked with
    cofactor + full-precision (病 1 + 病 2 fixes applied to v3.2).

    Sourced from the ORIGINAL v3.2 pool (undeduped — the hybrid pool's
    prediction block has lookup-duplicates removed, which would starve the
    prediction caliber for lookup-hit cases whose truth overlaps a lookup
    product).  This is the "fixed prediction layer" baseline vs v3.2's 33.7%.
    """
    return _rank_and_score(name, v32pool, ak, rerank=True)


def _caliber_lookup_only(name, hpool, ak):
    """Lookup-only caliber: only layer=="lookup" candidates (Tanimoto order)."""
    return _rank_and_score_filtered(name, hpool, ak,
                                   layer_filter="lookup", rerank=False)


def _rank_and_score(name, pool, ak, rerank):
    """Score a pool (list of (cid, pc, [cands])) top-20, with no-donor==parent
    dual口径 and attribution.  No layer filter (uses ALL candidates)."""
    return _rank_and_score_filtered(name, pool, ak, None, rerank)


def _rank_and_score_filtered(name, pool, ak, layer_filter, rerank):
    hits = {k: 0 for k in KS}
    hits_no_exact = {k: 0 for k in KS}
    mrr = 0.0
    n = 0
    n_exact = 0
    attrib = Counter()
    for cid, pc, cands in pool:
        if pc not in ak:
            continue
        n += 1
        truth = ak[pc]
        sel = [c for c in cands if layer_filter is None
               or c.get("layer") == layer_filter]
        if rerank:
            sel = _rank_prediction(sel)
        prods = [c["_canon"] for c in sel[:20]]
        prods_layer = [(c["_canon"], c.get("layer", "prediction")) for c in sel[:20]]
        layer, rank = _first_hit_layer(prods_layer, truth)
        if layer is not None:
            attrib[layer] += 1
        h = _eval(prods, truth)
        for k in KS:
            hits[k] += h[f"hit_at_{k}"]
        for i, p in enumerate(prods[:10]):
            if p in truth:
                mrr += 1.0 / (i + 1)
                break
        no_exact = [c for c in sel if not c.get("donor_exact_match", False)]
        if rerank:
            no_exact = _rank_prediction(no_exact)
        prods_ne = [c["_canon"] for c in no_exact[:20]]
        he = _eval(prods_ne, truth)
        if any(c.get("donor_exact_match", False) for c in sel):
            n_exact += 1
        for k in KS:
            hits_no_exact[k] += he[f"hit_at_{k}"]
    nn = max(n, 1)
    print(f"=== Caliber: {name} ===")
    res = _format(name, hits, mrr, n, nn)
    line2 = f"  {'no donor==par':14s}: " + "  ".join(
        f"H@{k}={hits_no_exact[k]}/{n}={hits_no_exact[k]/nn:.1%}" for k in KS)
    print(line2)
    print(f"  attribution (first-hit layer): {dict(attrib)}")
    print(f"  exact-donor cases: {n_exact}/{n}")
    return res | {
        "no_donor_parent": {f"hit_at_{k}": hits_no_exact[k] for k in KS},
        "n_exact": n_exact,
        "attribution": dict(attrib),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["score", "calibers"])
    ap.add_argument("--preds", help="hybrid predictions (for hybrid caliber)")
    ap.add_argument("--pool", required=True, help="hybrid pool (lookup-only)")
    ap.add_argument("--v32-pool", required=True,
                    help="original v3.2 pool (prediction caliber, undeduped)")
    ap.add_argument("--answer", required=True)
    ap.add_argument("--stereo", default="blind", choices=["blind", "strict"])
    ap.add_argument("--json-out")
    args = ap.parse_args()

    stereo_blind = args.stereo == "blind"
    ak = load_answer_key(args.answer, stereo_blind)
    hpool = load_pool(args.pool, stereo_blind)       # hybrid pool
    v32pool = load_pool(args.v32_pool, stereo_blind)  # original v3.2 pool

    print(f"# BBD P4.2 eval (stereo={args.stereo}, "
          f"n_hybrid={len(hpool)}, n_v32={len(v32pool)})\n")
    results = {}
    # --- hybrid caliber (from merged preds: lookup pinned + prediction fallback) ---
    if args.preds:
        preds = load_preds(args.preds, stereo_blind)
        print("=== Caliber: hybrid ===")
        results["hybrid"] = caliber_hybrid(preds, ak)
    # --- prediction caliber (v3.2 pool, full-precision + cofactor re-rank) ---
    results["prediction"] = _caliber_prediction("prediction", v32pool, ak)
    # --- lookup-only caliber (hybrid pool, layer=="lookup") ---
    results["lookup_only"] = _caliber_lookup_only("lookup-only", hpool, ak)

    # --- gate check ---
    print("\n=== Gate check ===")
    h = results.get("hybrid", {})
    h1 = h.get("hit_at_1", 0) / max(h.get("n", 1), 1)
    p = results["prediction"]
    p1 = p["hit_at_1"] / max(p["n"], 1)
    p10 = p["hit_at_10"] / max(p["n"], 1)
    print(f"  hybrid Hit@1      = {h1:.1%}  (gate >=85%)  {'PASS' if h1>=0.85 else 'FAIL'}")
    print(f"  prediction Hit@1  = {p1:.1%}  (gate >=40%)  {'PASS' if p1>=0.40 else 'FAIL'}")
    print(f"  prediction Hit@10 = {p10:.1%} (gate >=68%) {'PASS' if p10>=0.68 else 'FAIL'}")

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
