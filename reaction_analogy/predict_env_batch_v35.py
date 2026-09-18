#!/usr/bin/env python3
"""BBD v3.5 batch predictor — environmental assets + v3.4 hybrid caliber.

The deployment vehicle for the soil/sludge re-run (soil/sludge repair round
2, 2026-09-18): engines are loaded ONCE (188k USPTO templates + 286 enviPath
+ 49 EAWAG rules + expanded environmental retrieval corpus), then every
parent from the input CSV gets the full hybrid:

  Layer 1 (lookup):  expanded environmental library (EAWAG-BBD +
                     EAWAG-SOIL/SLUDGE/SEDIMENT packages), charge-normalized
                     identity keyed, pinned on top with eawag_reactions
                     provenance (package:pathway#reaction);
  Layer 2 (pred):    three engines + v3.4 calibrated fusion (regime-gated),
                     deduped against lookup identities.

Input CSV needs a parent SMILES column (header row; column name
``parent_smiles`` or ``smiles`` — first SMILES-looking column otherwise).

Outputs (frozen-chain compatible):
  <out>/predictions.jsonl     one row per case: top_products (rank, layer,
                              product_smiles, product_identity, source,
                              score, score_semantics, v34_regime,
                              eawag_reactions provenance)
  <out>/run_report.json       counts + library/corpus fingerprints
  <out>/MANIFEST.sha256       sha256 of outputs

Answer-key isolation: this file NEVER reads any answer key.  The library is
public enviPath/EAWAG-BBD package data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "src"))

from rdkit import Chem, RDLogger  # noqa: E402
RDLogger.DisableLog("rdApp.*")

import expand_bbd_routes as X  # noqa: E402
import single_smiles_v32 as S  # noqa: E402
import eawag_lookup as EGD  # noqa: E402
import bbd_v33_fusion as V33  # noqa: E402

ENV_OUT = os.path.join(_HERE, "data", "env_expand")
ENV_LIBRARY = os.path.join(ENV_OUT, "library_full.jsonl")
ENV_CORPUS = os.path.join(_HERE, "data", "corpus_env")
BBD_LIBRARY = os.path.join(_HERE, "data", "bbd_expand", "donor_product.jsonl")
BBD_CORPUS = os.path.join(_HERE, "data", "corpus_v1")


def _serialize_edge(e, rank):
    out = {
        "rank": rank,
        "layer": e.get("layer", "prediction"),
        "product_smiles": e["product_smiles"],
        "product_identity": e.get("product_identity",
                                  e["product_smiles"]),
        "source": e.get("source", ""),
        "score": e.get("edge_score", e.get("tanimoto", 0.0)),
        "score_semantics": e.get(
            "score_semantics",
            "eawag_lookup_tanimoto" if e.get("layer") == "lookup" else ""),
        "v34_regime": e.get("v34_regime", ""),
        "eawag_reactions": e.get("eawag_reactions", []),
        "p_uspto": e.get("p_uspto", 0.0),
        "p_envipath": e.get("p_envipath", 0.0),
        "p_retrieval": e.get("p_retrieval", 0.0),
        "ion_filtered": e.get("ion_filtered", False),
        "wildcard_filtered": e.get("wildcard_filtered", False),
        "charge_variants": e.get("charge_variants", []),
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--parents-csv", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--scoring", default="v34", choices=["v34", "v33"])
    ap.add_argument("--legacy-assets", action="store_true",
                    help="use the v3.3 assets (EAWAG-BBD library only, "
                         "corpus_v1) instead of the expanded environmental "
                         "assets — for A/B comparison")
    ap.add_argument("--v34-no-policy", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    library = BBD_LIBRARY if args.legacy_assets else ENV_LIBRARY
    corpus_dir = BBD_CORPUS if args.legacy_assets else ENV_CORPUS

    os.makedirs(args.out_dir, exist_ok=True)
    t0 = time.time()

    # ---- engines (loaded once) ----
    X.CORPUS_DIR = corpus_dir
    print(f"loading engines (corpus={corpus_dir})...", flush=True)
    S.load_engines()
    X._G_SCORING = args.scoring
    if args.scoring == "v34":
        S.setup_v34(no_policy=args.v34_no_policy)
    lookup_index = EGD.build_index(library)
    lookup_index.pop("__parse_fail__", None)
    lib_fingerprint = hashlib.sha256(
        open(library, "rb").read()).hexdigest()
    print(f"engines + library loaded: {len(lookup_index)} donors, "
          f"{len(X._G_RECORDS)} corpus records "
          f"({time.time()-t0:.0f}s)", flush=True)

    # ---- parents ----
    with open(args.parents_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    col = None
    for c in ("parent_smiles", "smiles", "SMILES", "parent"):
        if rows and c in rows[0]:
            col = c
            break
    if col is None and rows:
        for c in rows[0]:
            if "smile" in c.lower():
                col = c
                break
    if col is None:
        print("FATAL: no parent SMILES column found", file=sys.stderr)
        return 2
    cases = [(r.get("case_id") or r.get("benchmark_case_id") or f"case{i+1}",
              r[col].strip()) for i, r in enumerate(rows)]
    if args.limit:
        cases = cases[:args.limit]
    print(f"{len(cases)} parents (column: {col})", flush=True)

    # ---- per-case hybrid ----
    out_path = os.path.join(args.out_dir, "predictions.jsonl")
    n_lookup_hit = 0
    t_c = time.time()
    with open(out_path, "w") as f:
        for i, (cid, smi) in enumerate(cases):
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                f.write(json.dumps({
                    "case_id": cid, "smiles": smi, "top_products": [],
                    "error": "unparseable_parent"}) + "\n")
                continue
            root_identity = X._identity(smi) or smi
            root_node = {
                "node_id": X._node_id(cid, 0, root_identity),
                "case_id": cid, "depth": 0, "smiles": smi,
                "canonical_smiles": root_identity, "is_root": True,
                "ancestor_canons": set(), "path_score": 1.0,
            }
            S.attach_retrieval([root_node])
            res = S.expand_node(root_node)
            pred = list(res["edges"])
            look = EGD.lookup(lookup_index, smi)
            if look:
                n_lookup_hit += 1
            look_canons = {
                sb_(V33.normalize_charge_smiles(c["product_smiles"])
                    or c["product_smiles"]) for c in look}
            pred_dedup = [
                e for e in pred
                if sb_(V33.normalize_charge_smiles(e["product_smiles"])
                       or e["product_smiles"]) not in look_canons]
            merged = list(look) + pred_dedup if look else pred
            top = [_serialize_edge(e, r + 1)
                   for r, e in enumerate(merged[:args.top_k])]
            f.write(json.dumps({
                "case_id": cid, "smiles": smi,
                "lookup_hit": bool(look), "n_lookup": len(look),
                "n_pred_candidates": len(pred),
                "top_products": top}, ensure_ascii=False) + "\n")
            if (i + 1) % 25 == 0:
                el = time.time() - t_c
                print(f"{i+1}/{len(cases)} ({el:.0f}s, "
                      f"{el/(i+1):.1f}s/case, lookup-hit {n_lookup_hit})",
                      flush=True)

    report = {
        "mode": "v35-batch" if not args.legacy_assets else "v33-legacy-batch",
        "scoring": args.scoring,
        "n_cases": len(cases),
        "n_lookup_hit": n_lookup_hit,
        "library": library,
        "library_sha256": lib_fingerprint,
        "corpus_dir": corpus_dir,
        "corpus_records": len(X._G_RECORDS),
        "top_k": args.top_k,
        "total_time_s": round(time.time() - t0, 1),
        "git_commit": os.popen(
            "git -C " + os.path.join(_HERE, "..") +
            " rev-parse HEAD").read().strip(),
    }
    with open(os.path.join(args.out_dir, "run_report.json"), "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    lines = []
    for fn in ("predictions.jsonl", "run_report.json"):
        p = os.path.join(args.out_dir, fn)
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        lines.append(f"{h}  {fn}")
    with open(os.path.join(args.out_dir, "MANIFEST.sha256"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"DONE: {len(cases)} cases, {n_lookup_hit} lookup-hit, "
          f"{time.time()-t0:.0f}s", flush=True)
    return 0


def sb_(smi):
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m else None


if __name__ == "__main__":
    raise SystemExit(main())
