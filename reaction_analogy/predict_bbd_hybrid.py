#!/usr/bin/env python3
"""BBD hybrid predictor — Layer 1 (EAWAG lookup) + Layer 2 (prediction).

P4.2 mode (default, ``--rankers`` absent): behaviour byte-identical to the
delivered P4.2 predictor — Layer 2 reuses the v3.2 candidate pool re-scored at
FULL precision (``ns_score = max over belonging sources of (p_source/3)`` from
the pool's three per-source probabilities, NO round) with the cofactor +
ion filter; sorted by ``(filtered, -ns_score_full, product_smiles)``. Layer 1
is the EAWAG lookup, pinned on top when the parent is a recorded donor.

P5 / v5 mode (``--rankers <dir>``): the three per-source v5 rankers (trained on
the RHEA+EAWAG mixed set with the 28-dim ``is_eawag_domain`` feature) re-score
every v3.2 candidate → ``p_*_v5`` / ``ns_score_v5`` (the v3.1 ``p_*`` are
KEPT for the new-vs-old-ranker ablation). The EAWAG rules engine
(``--eawag-rules``) generates new ``rule_family="eawag_rule"`` candidates
(source="envipath", folded into the envipath ranker) and scores them with the
v5 envipath ranker. A secondary ``tiebreak_key`` (§4.3, |mw_diff|/parent_mw +
0.1·|n_atoms_diff|/parent_n_atoms) breaks exact-score ties
(``round(ns_score_v5, 9)`` quantizer — only candidates within 1e-9 share a
bucket, so non-tied cases are bit-unchanged vs tiebreak-off). ``--tiebreak
on|off`` is the ablation switch.

v5 emits THREE outputs: hybrid predictions + hybrid pool (as P4.2) AND an
UNDEDUPED v5 prediction pool (``--out-pred-pool``) so the prediction caliber
and the 4 ablations can be re-derived from one pool file without starving
lookup-hit cases (the P4.2 invariant).

Answer-key isolation: this file NEVER reads the answer key.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from rdkit import Chem, RDLogger  # noqa: E402
RDLogger.DisableLog("rdApp.*")

import bbd_v32_ion_filter as IF  # noqa: E402
import bbd_cofactor_filter as CF  # noqa: E402
import eawag_lookup as EGD  # noqa: E402
import bbd_v3_features as F  # noqa: E402 — _mol_props for tiebreak
import io_retry as IOR  # noqa: E402 — robust I/O for flaky external drive

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
V32_POOL = os.path.join(ROOT, "bbd_predictions/bbd_product_pool_v32.jsonl")
DONOR_PRODUCT = os.path.join(ROOT, "reaction_analogy/data/bbd_expand/donor_product.jsonl")
EAWAG_RULES_PATH = os.path.join(
    ROOT, "reaction_analogy/data/bbd_expand/rules_new_clean.jsonl")
BLIND_CSV = os.path.join(
    ROOT,
    "bbd_known_pathway_full_route_v0_3_candidate_v3_1_strict_blind_fix_20260821/blind/"
    "BBD_KNOWN_PATHWAY_FULL_ROUTE_V0_3_V3_1_BLIND_PARENT_INPUTS_FOR_PREDICTION_STRICT.csv")
TOP_K = 20
POOL_CAP = 2000
SOURCES = ("uspto", "envipath", "retrieval")


def _sb(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def _belongs(src: str, sk: str) -> bool:
    return sk in src or (sk in ("uspto", "envipath") and src == "both")


def ns_score_full(c: dict) -> float:
    """Full-precision no-selector shadow score: max over belonging sources of
    (p_source / 3), computed from the pool's three per-source probabilities
    WITHOUT rounding.  Identical formula in ``score_bbd_hybrid.py`` so the
    prediction caliber reproduces the prediction-block order from the pool."""
    best = 0.0
    src = c.get("source", "")
    for sk in SOURCES:
        if _belongs(src, sk):
            p = float(c.get(f"p_{sk}", 0.0))
            if p / 3.0 > best:
                best = p / 3.0
    return best


def ns_score_v5(c: dict) -> float:
    """v5 ranker shadow score: max over belonging sources of (p_source_v5/3),
    full precision. Same formula as ns_score_full but reading the v5 fields."""
    best = 0.0
    src = c.get("source", "")
    for sk in SOURCES:
        if _belongs(src, sk):
            p = float(c.get(f"p_{sk}_v5", 0.0))
            if p / 3.0 > best:
                best = p / 3.0
    return best


def tiebreak_key(cand_smi: str, parent_mw: float, parent_n_atoms: int) -> float:
    """§4.3 secondary tie-break key (smaller = better).

    = |mw_diff|/parent_mw + 0.1·|n_atoms_diff|/parent_n_atoms.  Only effective
    on exact-score ties (the sort key quantises ns_score to 9 decimals).  On
    parse failure returns a large value so the candidate sinks within a tie.
    """
    pp = F._mol_props(cand_smi)
    if pp is None or parent_mw <= 0 or parent_n_atoms <= 0:
        return 9.9
    return (abs(pp["mw"] - parent_mw) / parent_mw
            + 0.1 * abs(pp["n_atoms"] - parent_n_atoms) / parent_n_atoms)


def _predict_serialize(c: dict) -> dict:
    out = {
        "product_smiles": c["product_smiles"],
        "product_smiles_full": c.get("product_smiles_full", c["product_smiles"]),
        "source": c.get("source", ""),
        "layer": "prediction",
        "eawag_reactions": [],
        "donor_exact_match": c.get("donor_exact_match", False),
        "n_evidence": c.get("n_evidence", 0),
        "max_tanimoto": c.get("max_tanimoto", 0.0),
        "mean_tanimoto": c.get("mean_tanimoto", 0.0),
        "template_freq": c.get("template_freq", 0),
        "reactions_count": c.get("reactions_count", 0),
        "pattern_atom_count": c.get("pattern_atom_count", 0),
        "ranker_proba_v3": round(c.get("ranker_proba_v3",
                                       c.get("ranker_proba", 0.0)), 6),
        "p_uspto": c.get("p_uspto", 0.0),
        "p_envipath": c.get("p_envipath", 0.0),
        "p_retrieval": c.get("p_retrieval", 0.0),
        "ns_score": round(c["_ns_score_full"], 6),
        "ns_best_source": c.get("ns_best_source", ""),
        "ion_filtered": c["ion_filtered"],
        "cofactor_filtered": c["cofactor_filtered"],
        "filtered": c["filtered"],
    }
    # v5 fields (present only in v5 mode — keeps P4.2 output byte-identical)
    if c.get("_v5"):
        out["p_uspto_v5"] = round(c.get("p_uspto_v5", 0.0), 6)
        out["p_envipath_v5"] = round(c.get("p_envipath_v5", 0.0), 6)
        out["p_retrieval_v5"] = round(c.get("p_retrieval_v5", 0.0), 6)
        out["ns_score_v5"] = round(c["_ns_score_v5"], 6)
        out["ns_best_source_v5"] = c.get("ns_best_source_v5", "")
        out["tiebreak_key"] = c.get("tiebreak_key", 0.0)
        if c.get("rule_family"):
            out["rule_family"] = c["rule_family"]
    return out


def _lookup_serialize(c: dict) -> dict:
    out = {
        "product_smiles": c["product_smiles"],
        "product_smiles_full": c.get("product_smiles_full", c["product_smiles"]),
        "source": "eawag_lookup",
        "layer": "lookup",
        "eawag_reactions": c.get("eawag_reactions", []),
        "donor_exact_match": True,
        "n_evidence": c.get("n_evidence", 0),
        "max_tanimoto": c.get("tanimoto", 0.0),
        "mean_tanimoto": c.get("tanimoto", 0.0),
        "template_freq": 0,
        "reactions_count": len(c.get("eawag_reactions", [])),
        "pattern_atom_count": 0,
        "ranker_proba_v3": 0.0,
        "p_uspto": 0.0,
        "p_envipath": 0.0,
        "p_retrieval": 0.0,
        "ns_score": 0.0,
        "ns_best_source": "",
        "tanimoto": c.get("tanimoto", 0.0),
        "ion_filtered": c["ion_filtered"],
        "cofactor_filtered": c["cofactor_filtered"],
        "filtered": c["filtered"],
    }
    if c.get("_v5"):
        out["p_uspto_v5"] = 0.0
        out["p_envipath_v5"] = 0.0
        out["p_retrieval_v5"] = 0.0
        out["ns_score_v5"] = 0.0
        out["tiebreak_key"] = c.get("tiebreak_key", 0.0)
    return out


def _rescore_v5(cands, rankers, parent_smiles):
    """Compute v5 features (28-dim, is_eawag_domain=0) and re-score each
    candidate with the v5 per-source rankers → p_*_v5 / ns_score_v5 (in-place).
    Keeps v3.1 p_* untouched. Reuses bbd_v5_features.compute_v5_case_features
    (the single source of truth shared with training)."""
    import bbd_v5_features as F5
    F5.compute_v5_case_features(cands, parent_smiles, 0)
    for c in cands:
        src = c.get("source", "")
        best_p = 0.0
        best_source = "uspto"
        p_values = {}
        for sk in SOURCES:
            if not _belongs(src, sk):
                p_values[sk] = 0.0
                continue
            feats = c.get("_v31_features", {}).get(sk)
            if feats is None or sk not in rankers:
                p_values[sk] = 0.0
                continue
            p = float(rankers[sk].predict([feats])[0])
            p_values[sk] = p
            if p > best_p:
                best_p = p
                best_source = sk
        c["p_uspto_v5"] = p_values.get("uspto", 0.0)
        c["p_envipath_v5"] = p_values.get("envipath", 0.0)
        c["p_retrieval_v5"] = p_values.get("retrieval", 0.0)
        c["_ns_score_v5"] = best_p / 3.0
        c["ns_best_source_v5"] = best_source
        c["_v5"] = True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v32-pool", default=V32_POOL)
    ap.add_argument("--donor-product", default=DONOR_PRODUCT)
    ap.add_argument("--blind-csv", default=BLIND_CSV)
    ap.add_argument("--out-preds", required=True)
    ap.add_argument("--out-pool", required=True)
    ap.add_argument("--out-report", required=True)
    ap.add_argument("--limit", type=int, default=0, help="limit cases (debug)")
    # ---- P5 / v5 args (absent ⇒ P4.2 behaviour byte-identical) ----
    ap.add_argument("--rankers", default=None,
                    help="v5 ranker dir (e.g. data/bbd_v5/rankers); enables v5 mode")
    ap.add_argument("--eawag-rules", default=None,
                    help="EAWAG rules jsonl (enables engine-B second batch)")
    ap.add_argument("--tiebreak", default="on", choices=["on", "off"],
                    help="secondary tie-break on exact-score ties (v5 only)")
    ap.add_argument("--out-pred-pool", default=None,
                    help="undeduped v5 prediction pool (v5 only; ablation source)")
    args = ap.parse_args()

    v5 = bool(args.rankers)
    tiebreak = v5 and (args.tiebreak == "on")

    t0 = time.time()

    # ---- build EAWAG lookup index ----
    print("building EAWAG lookup index...", flush=True)
    index = EGD.build_index(args.donor_product)
    pf = index.pop("__parse_fail__", [{"count": 0}])[0]["count"]
    print(f"  {len(index)} donors, {pf} parse-fail", flush=True)

    # ---- load v3.2 pool (Layer 2 source) ----
    print("loading v3.2 pool...", flush=True)
    pool_cases = []
    for line in IOR.robust_readlines(args.v32_pool):
        pool_cases.append(json.loads(line))
    if args.limit:
        pool_cases = pool_cases[:args.limit]
    print(f"  {len(pool_cases)} cases", flush=True)

    # ---- leak assertion (train educt ∩ blind parent == 0, reuse v3.2 guard) ----
    blind_parents = set()
    with open(args.blind_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            s = _sb(row.get("parent_smiles", ""))
            if s:
                blind_parents.add(s)
    te_path = os.path.join(ROOT, "data/bbd_v3/train_educts.json")
    if os.path.exists(te_path):
        te = set(json.load(IOR.robust_open(te_path))["train_educts_sb"])
        overlap = te & blind_parents
        assert not overlap, f"LEAK: {len(overlap)} overlap"
        print("  leak assertion passed (RHEA 0 overlap)", flush=True)
    if v5:
        te5_path = os.path.join(ROOT, "data/bbd_v5/train_educts_v5.json")
        if os.path.exists(te5_path):
            te5 = set(json.load(IOR.robust_open(te5_path))["train_educts_sb"])
            overlap = te5 & blind_parents
            assert not overlap, f"LEAK: {len(overlap)} combined overlap"
            print("  leak assertion passed (combined RHEA+EAWAG 0 overlap)",
                  flush=True)

    # ---- v5: load rankers + eawag rules ----
    rankers = {}
    eawag_rules = None
    if v5:
        import lightgbm as lgb
        for sk in SOURCES:
            rp = os.path.join(args.rankers, f"{sk}_ranker.txt")
            if os.path.exists(rp):
                rankers[sk] = lgb.Booster(model_file=rp)
        print(f"  loaded {len(rankers)} v5 rankers", flush=True)
        if args.eawag_rules:
            import eawag_rules_engine as ERE
            eawag_rules = ERE.load_eawag_rules(args.eawag_rules)
            print(f"  loaded {len(eawag_rules)} EAWAG rules", flush=True)

    # ---- per case: merge Layer 1 + Layer 2 ----
    print("merging layers...", flush=True)
    results = []
    pred_pool_results = []  # undeduped v5 prediction pool (v5 only)
    n_lookup_hit = 0
    n_ion = n_cof = 0
    n_eawag_rule_cands = 0

    for r in pool_cases:
        cid = r["case_id"]
        smi = r["smiles"]
        v32_cands = r.get("all_candidates", [])

        # --- Layer 2 prediction candidates ---
        if v5:
            # combine v3.2 candidates + EAWAG-rule candidates (source="envipath")
            pred_cands = [dict(c) for c in v32_cands]
            if eawag_rules is not None:
                er = ERE.apply_eawag_rules(smi, eawag_rules, _sb(smi))
                for c in er:
                    c["p_uspto"] = 0.0
                    c["p_envipath"] = 0.0
                    c["p_retrieval"] = 0.0
                    pred_cands.append(c)
                    n_eawag_rule_cands += 1
            _rescore_v5(pred_cands, rankers, smi)
            # parent props for tiebreak
            pprops = F._mol_props(smi)
            pmw = pprops["mw"] if pprops else 0.0
            pna = pprops["n_atoms"] if pprops else 0
            pred = []
            for c in pred_cands:
                prod = c.get("product_smiles", "")
                can = _sb(prod) or prod
                ion = IF.is_ion_fragment(prod)
                cof = CF.is_cofactor_conjugate(prod)
                d = dict(c)
                d["_canon"] = can
                d["_ns_score_v5"] = ns_score_v5(d)
                d["_ns_score_full"] = ns_score_full(d)
                d["ion_filtered"] = ion
                d["cofactor_filtered"] = cof
                d["filtered"] = bool(ion or cof)
                d["tiebreak_key"] = tiebreak_key(prod, pmw, pna)
                pred.append(d)
            if tiebreak:
                pred.sort(key=lambda c: (c["filtered"],
                                         -round(c["_ns_score_v5"], 9),
                                         c["tiebreak_key"],
                                         c.get("product_smiles", "")))
            else:
                pred.sort(key=lambda c: (c["filtered"], -c["_ns_score_v5"],
                                         c.get("product_smiles", "")))
        else:
            # P4.2 path (byte-identical to delivered predictor)
            pred = []
            for c in v32_cands:
                prod = c.get("product_smiles", "")
                can = _sb(prod) or prod
                ion = IF.is_ion_fragment(prod)
                cof = CF.is_cofactor_conjugate(prod)
                nsf = ns_score_full(c)
                d = dict(c)
                d["_canon"] = can
                d["_ns_score_full"] = nsf
                d["ion_filtered"] = ion
                d["cofactor_filtered"] = cof
                d["filtered"] = bool(ion or cof)
                pred.append(d)
            pred.sort(key=lambda c: (c["filtered"], -c["_ns_score_full"],
                                     c.get("product_smiles", "")))

        # --- Layer 1: lookup candidates (already (filtered, -tanimoto, sb)) ---
        look = EGD.lookup(index, smi)
        for c in look:
            c["_canon"] = c["product_smiles"]
            if v5:
                pprops = F._mol_props(smi)
                pmw = pprops["mw"] if pprops else 0.0
                pna = pprops["n_atoms"] if pprops else 0
                c["_v5"] = True
                c["tiebreak_key"] = tiebreak_key(c["product_smiles"], pmw, pna)

        # --- merge: lookup block first (if hit), then deduped prediction block ---
        look_canons = {c["_canon"] for c in look}
        pred_dedup = [c for c in pred if c["_canon"] not in look_canons]
        lookup_hit = bool(look)
        if lookup_hit:
            n_lookup_hit += 1
            merged = list(look) + pred_dedup
        else:
            merged = pred

        n_ion += sum(1 for c in merged if c.get("ion_filtered"))
        n_cof += sum(1 for c in merged if c.get("cofactor_filtered"))

        # --- serialize ---
        def _ser(c: dict) -> dict:
            if c.get("layer") == "lookup" or c.get("source") == "eawag_lookup":
                return _lookup_serialize(c)
            return _predict_serialize(c)

        top = [_ser(c) for c in merged[:TOP_K]]
        pool = [_ser(c) for c in merged[:POOL_CAP]]
        pool_trunc = len(merged) > POOL_CAP

        # undeduped v5 prediction pool (v5 only) — ALL prediction candidates
        # (v3.2 + eawag_rule), layer="prediction", for the prediction caliber
        # + 4 ablations. NOT deduped against lookup (P4.2 invariant).
        if v5 and args.out_pred_pool:
            pred_pool_results.append({
                "case_id": cid, "smiles": smi,
                "n_atoms": (Chem.MolFromSmiles(smi).GetNumAtoms()
                            if Chem.MolFromSmiles(smi) else 0),
                "n_cand_union": len(pred),
                "all_candidates": [_ser(c) for c in pred[:POOL_CAP]],
                "pool_truncated": len(pred) > POOL_CAP,
            })

        n_atoms = (Chem.MolFromSmiles(smi).GetNumAtoms()
                   if Chem.MolFromSmiles(smi) else 0)
        results.append({
            "case_id": cid, "smiles": smi, "n_atoms": n_atoms,
            "n_cand_union": len(merged),
            "n_lookup": len(look),
            "lookup_hit": lookup_hit,
            "n_ion_filtered": sum(1 for c in merged if c.get("ion_filtered")),
            "n_cofactor_filtered": sum(1 for c in merged
                                       if c.get("cofactor_filtered")),
            "top_products": top,
            "all_candidates": pool,
            "pool_truncated": pool_trunc,
        })

    results.sort(key=lambda r: r["case_id"])
    pred_pool_results.sort(key=lambda r: r["case_id"])

    def _write_jsonl(path, rows, drop_field):
        lines = []
        for r in rows:
            out = {k: v for k, v in r.items() if k != drop_field}
            lines.append(json.dumps(out, ensure_ascii=False) + "\n")
        IOR.robust_writelines(path, lines)

    _write_jsonl(args.out_preds, results, "all_candidates")
    _write_jsonl(args.out_pool, results, "top_products")
    if v5 and args.out_pred_pool:
        _write_jsonl(args.out_pred_pool, pred_pool_results, "top_products")

    report = {
        "mode": "v5" if v5 else "p42",
        "tiebreak": tiebreak,
        "n_cases": len(results),
        "total_time_s": round(time.time() - t0, 2),
        "n_lookup_hit_cases": n_lookup_hit,
        "n_lookup_miss_cases": len(results) - n_lookup_hit,
        "total_ion_filtered": n_ion,
        "total_cofactor_filtered": n_cof,
        "n_eawag_rule_candidates": n_eawag_rule_cands,
        "mean_cands_per_case": round(
            sum(r["n_cand_union"] for r in results) / max(len(results), 1), 1),
        "zero_candidate_cases": [r["case_id"] for r in results
                                  if r["n_cand_union"] == 0],
    }
    IOR.robust_json_dump(args.out_report, report)
    print(f"DONE: {len(results)} cases, {n_lookup_hit} lookup-hit, "
          f"{n_ion} ions + {n_cof} cofactors sunk, "
          f"{n_eawag_rule_cands} eawag_rule cands, {time.time()-t0:.1f}s",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
