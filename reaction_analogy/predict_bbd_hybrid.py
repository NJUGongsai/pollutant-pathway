#!/usr/bin/env python3
"""BBD P4.2 hybrid predictor — Layer 1 (EAWAG lookup) + Layer 2 (v3.2 prediction).

Two-layer merge (task §4.3, soft-landing two-block route):

  Layer 2 (prediction): reuse the v3.2 candidate pool, re-scored at FULL
    precision (``ns_score = max over belonging sources of (p_source/3)`` computed
    from the pool's three per-source probabilities — NO round before sorting,
    per §4.6) with the cofactor filter applied (病 1) in addition to the ion
    filter.  Sorted by ``(filtered, -ns_score_full, product_smiles)``.

  Layer 1 (lookup): Engine D ``eawag_lookup.lookup(index, parent)`` —
    stereo-blind parent hit in ``donor_product.jsonl``.  Candidates ranked by
    ``(filtered, -tanimoto, product_smiles)`` and pinned to the top of the
    merged list when the parent is a recorded EAWAG donor.

  Merge: parent is a donor (Layer 1 non-empty) → lookup block first, then the
    Layer-2 block (deduped by stereo-blind canonical — duplicates keep the
    lookup evidence).  Parent not a donor → Layer-2 block only.

  Structural pinning: "Layer 1 命中" is decided structurally (parent is a
  recorded donor), NEVER by the answer key.  This is answer-key-isolated, so it
  cannot reproduce the §1 truth-aware OR-fallback ceiling (93.0%); the gap is
  the selection-fail cases where a structural lookup pin pre-empts a correct
  prediction — reported honestly in the REPORT.

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

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
V32_POOL = os.path.join(ROOT, "bbd_predictions/bbd_product_pool_v32.jsonl")
DONOR_PRODUCT = os.path.join(ROOT, "reaction_analogy/data/bbd_expand/donor_product.jsonl")
BLIND_CSV = os.path.join(
    ROOT,
    "bbd_known_pathway_full_route_v0_3_candidate_v3_1_strict_blind_fix_20260821/blind/"
    "BBD_KNOWN_PATHWAY_FULL_ROUTE_V0_3_V3_1_BLIND_PARENT_INPUTS_FOR_PREDICTION_STRICT.csv",
)
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


def _predict_serialize(c: dict) -> dict:
    return {
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


def _lookup_serialize(c: dict) -> dict:
    return {
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v32-pool", default=V32_POOL)
    ap.add_argument("--donor-product", default=DONOR_PRODUCT)
    ap.add_argument("--blind-csv", default=BLIND_CSV)
    ap.add_argument("--out-preds", required=True)
    ap.add_argument("--out-pool", required=True)
    ap.add_argument("--out-report", required=True)
    ap.add_argument("--limit", type=int, default=0, help="limit cases (debug)")
    args = ap.parse_args()

    t0 = time.time()

    # ---- build EAWAG lookup index ----
    print("building EAWAG lookup index...", flush=True)
    index = EGD.build_index(args.donor_product)
    pf = index.pop("__parse_fail__", [{"count": 0}])[0]["count"]
    print(f"  {len(index)} donors, {pf} parse-fail", flush=True)

    # ---- load v3.2 pool (Layer 2 source) ----
    print("loading v3.2 pool...", flush=True)
    pool_cases = []
    with open(args.v32_pool) as f:
        for line in f:
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
        te = set(json.load(open(te_path))["train_educts_sb"])
        overlap = te & blind_parents
        assert not overlap, f"LEAK: {len(overlap)} overlap"
        print("  leak assertion passed (0 overlap)", flush=True)

    # ---- per case: merge Layer 1 + Layer 2 ----
    print("merging layers...", flush=True)
    results = []
    n_lookup_hit = 0
    n_ion = n_cof = 0

    for r in pool_cases:
        cid = r["case_id"]
        smi = r["smiles"]
        v32_cands = r.get("all_candidates", [])

        # --- Layer 2: prediction candidates, full-precision + cofactor re-rank ---
        pred = []
        for c in v32_cands:
            prod = c.get("product_smiles", "")
            can = _sb(prod) or prod
            ion = IF.is_ion_fragment(prod)
            cof = CF.is_cofactor_conjugate(prod)
            nsf = ns_score_full(c)
            d = dict(c)  # carry v3.2 fields through
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

        n_atoms = (Chem.MolFromSmiles(smi).GetNumAtoms()
                   if Chem.MolFromSmiles(smi) else 0)
        results.append({
            "case_id": cid, "smiles": smi, "n_atoms": n_atoms,
            "n_cand_union": len(merged),
            "n_lookup": len(look),
            "lookup_hit": lookup_hit,
            "n_ion_filtered": sum(1 for c in merged if c.get("ion_filtered")),
            "n_cofactor_filtered": sum(1 for c in merged if c.get("cofactor_filtered")),
            "top_products": top,
            "all_candidates": pool,
            "pool_truncated": pool_trunc,
        })

    results.sort(key=lambda r: r["case_id"])

    with open(args.out_preds, "w") as f:
        for r in results:
            out = {k: v for k, v in r.items() if k != "all_candidates"}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    with open(args.out_pool, "w") as f:
        for r in results:
            out = {k: v for k, v in r.items() if k != "top_products"}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    report = {
        "n_cases": len(results),
        "total_time_s": round(time.time() - t0, 2),
        "n_lookup_hit_cases": n_lookup_hit,
        "n_lookup_miss_cases": len(results) - n_lookup_hit,
        "total_ion_filtered": n_ion,
        "total_cofactor_filtered": n_cof,
        "mean_cands_per_case": round(
            sum(r["n_cand_union"] for r in results) / max(len(results), 1), 1),
        "zero_candidate_cases": [r["case_id"] for r in results
                                  if r["n_cand_union"] == 0],
    }
    with open(args.out_report, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"DONE: {len(results)} cases, {n_lookup_hit} lookup-hit, "
          f"{n_ion} ions + {n_cof} cofactors sunk, {time.time()-t0:.1f}s",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
