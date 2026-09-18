#!/usr/bin/env python3
"""BBD v3.2 predictor: no-selector (uniform w=1/3) + ion fragment filter.

Pure inference — reuses the 4 existing v3.1 LightGBM models (no retraining).

Scoring (no-selector, shadow mechanism):
    ns_score(c) = max over c's sources of (p_source(c) / 3)

v3.3 fusion (default, --scoring v33; DBP post-freeze fix 2026-09-14):
    candidates differing only by protonation state are merged into one
    identity (charge normalization); ns33 = (max p_source/3)
    * (1 + AGREE_BONUS*(n_sources-1)) * SKELETON_KEEP_FACTOR^flag, capped 1/3.
    See bbd_v33_fusion.py.  --scoring v32 keeps the raw v3.2 behavior.

Ion filter:
    is_ion_fragment(c) → sink to bottom (not deleted); ``ion_filtered`` flag set.

Ranking key: (ion_filtered, -ns_score, product_smiles) — non-ions first.

Pool schema stores ALL THREE per-source probabilities (p_uspto, p_envipath,
p_retrieval) so ablations can re-score without model reload.

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
import bbd_v32_ion_filter as IF  # noqa: E402
import bbd_v33_fusion as V33  # noqa: E402

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
import bbd_data_root as D  # noqa: E402 — BBD_DATA_ROOT resolver (HF-migrated assets)
V3_POOL = D.resolve("bbd_predictions/bbd_product_pool_v3.jsonl")
MODEL_DIR = D.resolve("data/bbd_v31")
TOP_K = 20
POOL_CAP = 2000

SOURCES = ("uspto", "envipath", "retrieval")


def _stereo_blind(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def _belongs_to_source(src: str, sk: str) -> bool:
    """Whether candidate with source label *src* belongs to source *sk*."""
    return sk in src or (sk in ("uspto", "envipath") and src == "both")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v3-pool", default=V3_POOL)
    ap.add_argument("--blind-csv", required=True)
    ap.add_argument("--model-dir", default=MODEL_DIR)
    ap.add_argument("--out-preds", required=True)
    ap.add_argument("--out-pool", required=True)
    ap.add_argument("--out-report", required=True)
    ap.add_argument("--scoring", default="v33",
                    choices=["v34", "v35", "v33", "v32"],
                    help="v33 = charge-normalized fusion (default); "
                         "v34/v35 = per-source calibrated fusion — the mode "
                         "IS the calibrator version (P0-2: explicit); "
                         "v32 = raw max(p)/3 shadow")
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

    # ---- leak assertion ----
    te_path = os.path.join(ROOT, "data/bbd_v3/train_educts.json")
    if os.path.exists(te_path):
        te = set(json.load(open(te_path))["train_educts_sb"])
        overlap = te & blind_parents
        assert not overlap, f"LEAK: {len(overlap)} overlap"
        print("  leak assertion passed (0 overlap)", flush=True)

    # ---- load per-source rankers (NOT selector — no-selector is default) ----
    print("loading per-source rankers...", flush=True)
    import lightgbm as lgb
    rankers: dict[str, lgb.Booster] = {}
    for sk in SOURCES:
        path = os.path.join(args.model_dir, f"{sk}_ranker.txt")
        if os.path.exists(path):
            rankers[sk] = lgb.Booster(model_file=path)
    print(f"  loaded {len(rankers)} rankers", flush=True)

    # ---- process each case ----
    print("scoring...", flush=True)
    results = []
    ion_filtered_total = 0

    for r in pool_cases:
        cid = r["case_id"]
        smi = r["smiles"]
        cands = r.get("all_candidates", [])

        # compute v3.1 features (needed for per-source ranker input)
        F.compute_v31_case_features(cands, smi)

        # score each candidate with per-source rankers (shadow mechanism)
        for c in cands:
            src = c.get("source", "")
            best_p = 0.0
            best_source = "uspto"
            p_values = {}
            for sk in SOURCES:
                if not _belongs_to_source(src, sk):
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
            c["p_uspto"] = round(p_values.get("uspto", 0.0), 6)
            c["p_envipath"] = round(p_values.get("envipath", 0.0), 6)
            c["p_retrieval"] = round(p_values.get("retrieval", 0.0), 6)
            # no-selector: max over sources of (p_source / 3)
            c["ns_score"] = round(best_p / 3.0, 6)
            c["ns_best_source"] = best_source
            # ion filter
            c["ion_filtered"] = IF.is_ion_fragment(c["product_smiles"])
            if c["ion_filtered"]:
                ion_filtered_total += 1

        # ---- ranking ----
        if args.scoring in ("v34", "v35"):
            # per-source calibrated fusion (P0-2: the scoring mode IS the
            # calibrator version — explicit, no auto-upgrade)
            import bbd_v34_fusion as V34
            import expand_bbd_routes as XR
            if XR._G_V34_VERSION != args.scoring:
                XR.set_calibrator_path(
                    XR.calibrator_repo_path(args.scoring), args.scoring)
            calib = XR._load_v34_calibrator(version=args.scoring)
            if not calib:
                ranked = V33.score_candidates_v33(cands, smi)
            else:
                ranked = V34.score_candidates_v34(
                    cands, smi, calib,
                    combiner=V34.DEFAULT_COMBINER)
                if XR._G_V34_POLICY:
                    k, ms, me = XR._G_V34_POLICY
                    ranked = V34.apply_topk_policy(ranked, k=k,
                                                   max_same_scaffold=ms,
                                                   min_env=me)
        elif args.scoring == "v33":
            # charge-normalized identity merge + agreement + skeleton check
            ranked = V33.score_candidates_v33(cands, smi)
        else:
            ranked = cands
            ranked.sort(key=lambda c: (c["ion_filtered"], -c["ns_score"],
                                       c["product_smiles"]))

        n_atoms = Chem.MolFromSmiles(smi).GetNumAtoms() if Chem.MolFromSmiles(smi) else 0

        def _serialize(c: dict) -> dict:
            out = {
                "product_smiles": c["product_smiles"],
                "product_identity": c.get("product_identity",
                                           c["product_smiles"]),
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
                "p_uspto": c.get("p_uspto", 0.0),
                "p_envipath": c.get("p_envipath", 0.0),
                "p_retrieval": c.get("p_retrieval", 0.0),
                "ns_score": c.get("ns_score", 0.0),
                "ns_best_source": c.get("ns_best_source", ""),
                "ion_filtered": c.get("ion_filtered", False),
                "wildcard_filtered": c.get("wildcard_filtered", False),
                "charge_variants": [v.get("product_smiles")
                                    for v in c.get("charge_variants", [])
                                    ] or [c["product_smiles"]],
            }
            if "ns_semantics" in c:  # v3.3 audit fields
                out["ns_semantics"] = c["ns_semantics"]
                out["n_independent_sources"] = c.get("n_independent_sources", 1)
                out["skeleton_unexplained"] = c.get("skeleton_unexplained", False)
                out["skeleton_reason"] = c.get("skeleton_reason", "")
            return out

        top = [_serialize(c) for c in ranked[:TOP_K]]
        pool = [_serialize(c) for c in ranked[:POOL_CAP]]
        pool_truncated = len(ranked) > POOL_CAP
        cands = ranked

        results.append({
            "case_id": cid, "smiles": smi, "n_atoms": n_atoms,
            "n_cand_union": len(cands),
            "n_ion_filtered": sum(1 for c in cands if c.get("ion_filtered")),
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
        "scoring": args.scoring,
        "total_time_s": round(time.time() - t_start, 2),
        "total_ion_filtered": ion_filtered_total,
        "mean_cands_per_case": round(sum(r["n_cand_union"] for r in results) / max(len(results), 1), 1),
        "zero_candidate_cases": [r["case_id"] for r in results if r["n_cand_union"] == 0],
    }
    with open(args.out_report, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"DONE: {len(results)} cases, {ion_filtered_total} ions filtered, "
          f"{time.time()-t_start:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
