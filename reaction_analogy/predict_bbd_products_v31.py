#!/usr/bin/env python3
"""BBD v3.1 predictor: per-source ranker + selector arbitration.

Reads the v3 pool (locked candidates), computes v3.1 features, scores with
the 4-model ensemble (3 per-source rankers + source selector), outputs
top-20 predictions with final_score / p_source / w decomposition.

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

from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")

import bbd_v3_features as F  # noqa: E402
import bbd_v31_ranker as R31  # noqa: E402

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
V3_POOL = os.path.join(ROOT, "bbd_predictions/bbd_product_pool_v3.jsonl")
MODEL_DIR = os.path.join(ROOT, "data/bbd_v31")
TOP_K = 20
POOL_CAP = 2000


def _stereo_blind(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v3-pool", default=V3_POOL)
    ap.add_argument("--blind-csv", required=True)
    ap.add_argument("--model-dir", default=MODEL_DIR)
    ap.add_argument("--out-preds", required=True)
    ap.add_argument("--out-pool", required=True)
    ap.add_argument("--out-report", required=True)
    args = ap.parse_args()

    t_start = time.time()

    # ---- load v3 pool ----
    print("loading v3 pool...", flush=True)
    pool_cases = []
    with open(args.v3_pool) as f:
        for line in f:
            pool_cases.append(json.loads(line))
    print(f"  {len(pool_cases)} cases", flush=True)

    # ---- load blind CSV (for leak assertion) ----
    blind_parents = set()
    with open(args.blind_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sb = _stereo_blind(row.get("parent_smiles", ""))
            if sb:
                blind_parents.add(sb)

    # ---- leak assertion (reuse v3 train_educts.json) ----
    te_path = os.path.join(ROOT, "data/bbd_v3/train_educts.json")
    if os.path.exists(te_path):
        te = set(json.load(open(te_path))["train_educts_sb"])
        overlap = te & blind_parents
        assert not overlap, f"LEAK: {len(overlap)} overlap"
        print(f"  leak assertion passed (0 overlap)", flush=True)

    # ---- load ranker ----
    print("loading v3.1 models...", flush=True)
    ranker = R31.load_ranker(args.model_dir)
    print(f"  loaded {len(ranker.source_rankers)} source rankers"
          f" + {'selector' if ranker.selector else 'no selector'}", flush=True)

    # ---- process each case ----
    print("scoring...", flush=True)
    results = []

    for r in pool_cases:
        cid = r["case_id"]
        smi = r["smiles"]
        cands = r.get("all_candidates", [])

        # compute v3.1 features
        F.compute_v31_case_features(cands, smi)

        # score with ranker
        ranker.score_candidates(cands, smi)

        n_atoms = Chem.MolFromSmiles(smi).GetNumAtoms() if Chem.MolFromSmiles(smi) else 0

        def _serialize(c: dict) -> dict:
            return {
                "product_smiles": c["product_smiles"],
                "product_smiles_full": c.get("product_smiles_full", c["product_smiles"]),
                "source": c.get("source", ""),
                "template_freq": c.get("template_freq", 0),
                "reactions_count": c.get("reactions_count", 0),
                "pattern_atom_count": c.get("pattern_atom_count", 0),
                "n_evidence": c.get("n_evidence", 0),
                "max_tanimoto": c.get("max_tanimoto", 0.0),
                "mean_tanimoto": c.get("mean_tanimoto", 0.0),
                "donor_exact_match": c.get("donor_exact_match", False),
                "ranker_proba_v3": round(c.get("ranker_proba", 0.0), 6),
                "final_score": round(c.get("final_score", 0.0), 6),
                "p_source": round(c.get("p_source", 0.0), 6),
                "w_source": round(c.get("w_source", 0.0), 6),
                "v31_weights": c.get("v31_weights", {}),
            }

        top = [_serialize(c) for c in cands[:TOP_K]]
        pool = [_serialize(c) for c in cands[:POOL_CAP]]
        pool_truncated = len(cands) > POOL_CAP

        results.append({
            "case_id": cid, "smiles": smi, "n_atoms": n_atoms,
            "n_cand_union": len(cands),
            "top_products": top,
            "all_candidates": pool,
            "pool_truncated": pool_truncated,
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
        "total_time_s": round(time.time() - t_start, 2),
        "mean_cands_per_case": round(sum(r["n_cand_union"] for r in results) / max(len(results), 1), 1),
        "zero_candidate_cases": [r["case_id"] for r in results if r["n_cand_union"] == 0],
    }
    with open(args.out_report, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"DONE: {len(results)} cases, {time.time()-t_start:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
