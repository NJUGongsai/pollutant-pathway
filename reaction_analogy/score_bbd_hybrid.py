#!/usr/bin/env python3
"""BBD evaluator — three calibers + attribution + dual donor==parent.

P4.2 mode (``calibers``): three calibers from the P4.2 hybrid pool — hybrid
(lookup pinned + prediction fallback), prediction (lookup OFF, v3.2 candidate
set re-ranked with cofactor + full-precision), lookup-only. Dual
donor==parent 口径 + first-hit layer attribution.

P5 / v5 mode (``calibers_v5``): three calibers from the v5 outputs PLUS four
ablation groups on the prediction caliber, all re-derived from the single
undeduped v5 prediction pool (which carries v3.1 ``p_*`` AND v5 ``p_*_v5``,
``rule_family``, ``tiebreak_key``):
  (a) new vs old ranker  — (v5, rules off, tiebreak off) vs (v3, off, off)
  (b) rules on/off        — (v5, tiebreak off, on vs off)
  (c) tiebreak on/off     — (v5, rules on, on vs off)
  (d) full v5 vs P4.2     — (v5, on, on) vs (v3, off, off)
Gate (v5): prediction Hit@1 ≥ 45%, Hit@10 ≥ 70%, hybrid ≥ 90.7%.

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
import io_retry as IOR  # noqa: E402

SOURCES = ("uspto", "envipath", "retrieval")
KS = [1, 3, 5, 10, 20]


def _canon(smi, stereo_blind=True):
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=not stereo_blind) if m else None


def _belongs(src, sk):
    return sk in src or (sk in ("uspto", "envipath") and src == "both")


def ns_score_full(c):
    """max over belonging sources of (p_source/3), NO round (§4.6). P4.2 v3."""
    best = 0.0
    src = c.get("source", "")
    for sk in SOURCES:
        if _belongs(src, sk):
            p = float(c.get(f"p_{sk}", 0.0))
            if p / 3.0 > best:
                best = p / 3.0
    return best


def _ns_score(c, version):
    """Version-aware no-selector score: v3 reads p_sk, v5 reads p_sk_v5."""
    best = 0.0
    src = c.get("source", "")
    for sk in SOURCES:
        if _belongs(src, sk):
            field = f"p_{sk}_v5" if version == "v5" else f"p_{sk}"
            p = float(c.get(field, 0.0))
            if p / 3.0 > best:
                best = p / 3.0
    return best


def load_answer_key(path, stereo_blind=True):
    out = {}
    for line in IOR.robust_readlines(path):
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
    out = []
    for line in IOR.robust_readlines(path):
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
    out = []
    for line in IOR.robust_readlines(path):
        r = json.loads(line)
        pc = _canon(r.get("smiles", ""), stereo_blind)
        prods = [_canon(t.get("product_smiles", ""), stereo_blind)
                 for t in r.get("top_products", [])]
        prods = [p for p in prods if p]
        out.append((r.get("case_id", ""), pc, prods))
    return out


def _rank_prediction(cands):
    """P4.2 re-rank: (filtered, -ns_score_full, smiles)."""
    scored = []
    for c in cands:
        prod = c.get("product_smiles", "")
        ion = IF.is_ion_fragment(prod)
        cof = CF.is_cofactor_conjugate(prod)
        scored.append((bool(ion or cof), ns_score_full(c), c["_canon"], c))
    scored.sort(key=lambda x: (x[0], -x[1], x[2]))
    return [s[3] for s in scored]


def _rank_prediction_v5(cands, version, tiebreak, rules):
    """v5 re-rank with version/tiebreak/rules switches (ablation source)."""
    scored = []
    for c in cands:
        if rules == "off" and c.get("rule_family") == "eawag_rule":
            continue
        prod = c.get("product_smiles", "")
        ion = IF.is_ion_fragment(prod)
        cof = CF.is_cofactor_conjugate(prod)
        nsf = _ns_score(c, version)
        tb = c.get("tiebreak_key", 0.0)
        scored.append((bool(ion or cof), nsf, tb, c["_canon"], c))
    if tiebreak == "on":
        scored.sort(key=lambda x: (x[0], -round(x[1], 9), x[2], x[3]))
    else:
        scored.sort(key=lambda x: (x[0], -x[1], x[3]))
    return [s[4] for s in scored]


def _eval(prods, truth, ks=KS):
    out = {}
    for k in ks:
        out[f"hit_at_{k}"] = int(any(p in truth for p in prods[:k]))
    return out


def _first_hit_layer(prods_with_layer, truth):
    for i, (canon, layer) in enumerate(prods_with_layer):
        if canon in truth:
            return layer, i + 1
    return None, None


def caliber_hybrid(preds, ak):
    hits = {k: 0 for k in KS}
    mrr = 0.0
    n = 0
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
    nn = max(n, 1)
    return _format("hybrid", hits, mrr, n, nn)


def _format(name, hits, mrr, n, nn):
    line = f"  {name:20s}: " + "  ".join(
        f"H@{k}={hits[k]}/{n}={hits[k]/nn:.1%}" for k in KS)
    print(line)
    print(f"  {'':20s}  MRR@10={mrr/nn:.4f}  (n={n})")
    return {f"hit_at_{k}": hits[k] for k in KS} | {"n": n, "mrr": round(mrr / nn, 4)}


def _caliber_prediction(name, v32pool, ak):
    return _rank_and_score(name, v32pool, ak, rerank=True)


def _caliber_lookup_only(name, hpool, ak):
    return _rank_and_score_filtered(name, hpool, ak, layer_filter="lookup",
                                    rerank=False)


def _rank_and_score(name, pool, ak, rerank):
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
    line2 = f"  {'no donor==par':20s}: " + "  ".join(
        f"H@{k}={hits_no_exact[k]}/{n}={hits_no_exact[k]/nn:.1%}" for k in KS)
    print(line2)
    print(f"  attribution (first-hit layer): {dict(attrib)}")
    print(f"  exact-donor cases: {n_exact}/{n}")
    return res | {
        "no_donor_parent": {f"hit_at_{k}": hits_no_exact[k] for k in KS},
        "n_exact": n_exact,
        "attribution": dict(attrib),
    }


def _rank_and_score_v5(name, pool, ak, version, tiebreak, rules, verbose=True):
    """v5 prediction caliber with (version, tiebreak, rules) switches."""
    hits = {k: 0 for k in KS}
    mrr = 0.0
    n = 0
    for cid, pc, cands in pool:
        if pc not in ak:
            continue
        n += 1
        truth = ak[pc]
        sel = _rank_prediction_v5(cands, version, tiebreak, rules)
        prods = [c["_canon"] for c in sel[:20]]
        h = _eval(prods, truth)
        for k in KS:
            hits[k] += h[f"hit_at_{k}"]
        for i, p in enumerate(prods[:10]):
            if p in truth:
                mrr += 1.0 / (i + 1)
                break
    nn = max(n, 1)
    res = {f"hit_at_{k}": hits[k] for k in KS} | {
        "n": n, "mrr": round(mrr / nn, 4)}
    if verbose:
        label = f"{name} [{version}/tb={tiebreak}/rules={rules}]"
        print(f"  {label:40s}: " + "  ".join(
            f"H@{k}={hits[k]}/{n}={hits[k]/nn:.1%}" for k in (1, 3, 5, 10))
              + f"  MRR={mrr/nn:.4f}")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["score", "calibers", "calibers_v5"])
    ap.add_argument("--preds", help="hybrid predictions (hybrid caliber)")
    ap.add_argument("--pool", help="hybrid pool (lookup-only caliber)")
    ap.add_argument("--v32-pool", help="original v3.2 pool (prediction caliber)")
    ap.add_argument("--answer", required=True)
    ap.add_argument("--stereo", default="blind", choices=["blind", "strict"])
    ap.add_argument("--json-out")
    args = ap.parse_args()

    stereo_blind = args.stereo == "blind"
    ak = load_answer_key(args.answer, stereo_blind)
    results = {}

    if args.mode == "calibers":
        hpool = load_pool(args.pool, stereo_blind)
        v32pool = load_pool(args.v32_pool, stereo_blind)
        print(f"# BBD P4.2 eval (stereo={args.stereo}, n_hybrid={len(hpool)}, "
              f"n_v32={len(v32pool)})\n")
        if args.preds:
            preds = load_preds(args.preds, stereo_blind)
            print("=== Caliber: hybrid ===")
            results["hybrid"] = caliber_hybrid(preds, ak)
        results["prediction"] = _caliber_prediction("prediction", v32pool, ak)
        results["lookup_only"] = _caliber_lookup_only("lookup-only", hpool, ak)
        print("\n=== Gate check (P4.2) ===")
        h = results.get("hybrid", {})
        h1 = h.get("hit_at_1", 0) / max(h.get("n", 1), 1)
        p = results["prediction"]
        p1 = p["hit_at_1"] / max(p["n"], 1)
        p10 = p["hit_at_10"] / max(p["n"], 1)
        print(f"  hybrid Hit@1      = {h1:.1%}  (gate >=85%)  "
              f"{'PASS' if h1>=0.85 else 'FAIL'}")
        print(f"  prediction Hit@1  = {p1:.1%}  (gate >=40%)  "
              f"{'PASS' if p1>=0.40 else 'FAIL'}")
        print(f"  prediction Hit@10 = {p10:.1%} (gate >=68%) "
              f"{'PASS' if p10>=0.68 else 'FAIL'}")

    elif args.mode == "calibers_v5":
        hpool = load_pool(args.pool, stereo_blind)        # hybrid pool v5
        v5pool = load_pool(args.v32_pool, stereo_blind)  # undeduped v5 pred pool
        print(f"# BBD P5 eval (stereo={args.stereo}, n_hybrid={len(hpool)}, "
              f"n_v5pred={len(v5pool)})\n")
        # --- 3 calibers (full v5 defaults: v5 ranker, rules on, tiebreak on) ---
        if args.preds:
            preds = load_preds(args.preds, stereo_blind)
            print("=== Caliber: hybrid (v5) ===")
            results["hybrid"] = caliber_hybrid(preds, ak)
        results["lookup_only"] = _caliber_lookup_only("lookup-only", hpool, ak)
        print("=== Caliber: prediction (full v5) ===")
        results["prediction_full_v5"] = _rank_and_score_v5(
            "prediction", v5pool, ak, "v5", "on", "on")
        # --- 4 ablation groups (prediction caliber) ---
        print("\n=== Ablation: prediction caliber ===")
        abl = {}
        # (a) new vs old ranker (rules off, tiebreak off)
        abl["a_old_ranker_v3"] = _rank_and_score_v5(
            "a_old", v5pool, ak, "v3", "off", "off")
        abl["a_new_ranker_v5"] = _rank_and_score_v5(
            "a_new", v5pool, ak, "v5", "off", "off")
        # (b) rules on/off (v5, tiebreak off)
        abl["b_rules_off"] = abl["a_new_ranker_v5"]  # same config
        abl["b_rules_on"] = _rank_and_score_v5(
            "b_rules_on", v5pool, ak, "v5", "off", "on")
        # (c) tiebreak on/off (v5, rules on)
        abl["c_tiebreak_off"] = _rank_and_score_v5(
            "c_tb_off", v5pool, ak, "v5", "off", "on")
        abl["c_tiebreak_on"] = results["prediction_full_v5"]
        # (d) full v5 vs P4.2 baseline (v3, off, off == a_old_ranker_v3)
        results["ablations"] = abl
        # --- gate ---
        print("\n=== Gate check (P5) ===")
        h = results.get("hybrid", {})
        h1 = h.get("hit_at_1", 0) / max(h.get("n", 1), 1)
        full = results["prediction_full_v5"]
        p1 = full["hit_at_1"] / max(full["n"], 1)
        p10 = full["hit_at_10"] / max(full["n"], 1)
        print(f"  hybrid Hit@1       = {h1:.1%}  (gate >=90.7% no-regression) "
              f"{'PASS' if h1>=0.907 else 'FAIL'}")
        print(f"  prediction Hit@1   = {p1:.1%}  (gate >=45%)  "
              f"{'PASS' if p1>=0.45 else 'FAIL'}")
        print(f"  prediction Hit@10  = {p10:.1%}  (gate >=70%)  "
              f"{'PASS' if p10>=0.70 else 'FAIL'}")
        # ablation deltas vs old ranker baseline
        base = abl["a_old_ranker_v3"]
        bn = max(base["n"], 1)
        print("  --- ablation deltas (Hit@1 vs old-ranker baseline) ---")
        for key in ["a_new_ranker_v5", "b_rules_on", "c_tiebreak_on"]:
            d = abl[key]
            print(f"    {key:20s}: H@1 {d['hit_at_1']}/{d['n']}="
                  f"{d['hit_at_1']/max(d['n'],1):.1%} "
                  f"(Δ={d['hit_at_1']-base['hit_at_1']:+d})")

    if args.json_out:
        IOR.robust_json_dump(args.json_out, results)


if __name__ == "__main__":
    main()
