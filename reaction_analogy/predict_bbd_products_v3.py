#!/usr/bin/env python3
"""BBD v3: three-engine candidate generation + LightGBM ranker inference.

Engines A+B: read directly from the v2 pool file (``bbd_product_pool_v2.jsonl``)
— no re-generation needed (v2 is deterministic and byte-verified).
Engine C:   read from the v3 retrieval pool
             (``data/retrieval_v3/candidates.jsonl``).

Merge by ``product_smiles`` (isomeric canonical), apply parent filtering,
compute features (``bbd_v3_features``), load the LightGBM ranker, predict
probabilities, rank by ``(-proba, product_smiles)``.

Answer-key isolation: this file NEVER reads the restricted answer key.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")

import bbd_v3_features as F  # noqa: E402

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
V2_POOL = os.path.join(ROOT, "bbd_predictions/bbd_product_pool_v2.jsonl")
V3_CANDS = os.path.join(_HERE, "data/retrieval_v3/candidates.jsonl")
V3_QUERIES = os.path.join(_HERE, "data/retrieval_v3/queries.jsonl")
RANKER_MODEL = os.path.join(ROOT, "data/bbd_v3/ranker_model.txt")
TOP_K = 20
POOL_CAP = 2000


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _stereo_blind(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def _to_isomeric(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=True) if m is not None else None


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #
def load_v2_pool(path: str) -> dict[str, list[dict]]:
    """Return {case_id: [candidate_dict, ...]} from v2 pool.

    Each candidate dict is the raw entry from ``all_candidates``.
    """
    out: dict[str, list[dict]] = defaultdict(list)
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            cid = r["case_id"]
            out[cid] = r.get("all_candidates", [])
    return dict(out)


def load_v3_retrieval(cands_path: str, queries_path: str) -> dict[str, list[dict]]:
    """Return {case_id: [retrieval_candidate_dict, ...]}.

    Each dict has candidate_smiles, product_smiles_full, n_evidence,
    max_tanimoto, mean_tanimoto, donor_exact_match, etc.  We rename
    candidate_smiles → product_smiles and add default v2 fields.
    """
    # load queries for parent SMILES (needed for parent filter)
    queries = {}
    with open(queries_path) as f:
        for line in f:
            r = json.loads(line)
            queries[r["case_id"]] = r["x_smiles"]

    out: dict[str, list[dict]] = defaultdict(list)
    with open(cands_path) as f:
        for line in f:
            d = json.loads(line)
            cid = d["case_id"]
            iso = _to_isomeric(d["candidate_smiles"])
            if iso is None:
                continue
            c = {
                "product_smiles": iso,
                "product_smiles_full": d.get("product_smiles_full", iso),
                "source": "retrieval",
                "template_freq": 0,
                "reactions_count": 0,
                "pattern_atom_count": 0,
                "mpnn_site_mean": 0.0,
                "mpnn_site_max": 0.0,
                "site_atoms": [],
                "rule_ids": [],
                "n_evidence": d.get("n_evidence", 0),
                "max_tanimoto": d.get("max_tanimoto", 0.0),
                "mean_tanimoto": d.get("mean_tanimoto", 0.0),
                "donor_exact_match": d.get("donor_exact_match", False),
                "n_donor_records": d.get("n_donor_records", 0),
            }
            out[cid].append(c)
    return dict(out)


# --------------------------------------------------------------------------- #
# Merge
# --------------------------------------------------------------------------- #
def _merge_source(src_a: str, src_b: str) -> str:
    """Merge two source labels into a combined label.

    Handles v2's ``"both"`` (= uspto+envipath) and v3's explicit ``"uspto+..."``
    forms uniformly.
    """
    engines = set()
    for s in (src_a, src_b):
        if s == "both" or "uspto" in s:
            engines.add("uspto")
        if s == "both" or "envipath" in s:
            engines.add("envipath")
        if "retrieval" in s:
            engines.add("retrieval")
    parts = []
    if "uspto" in engines:
        parts.append("uspto")
    if "envipath" in engines:
        parts.append("envipath")
    if "retrieval" in engines:
        parts.append("retrieval")
    if len(parts) == 3:
        return "all"
    return "+".join(parts) if parts else "uspto"


def merge_candidates(v2_cands: list[dict], v3_cands: list[dict],
                     parent_sb: str) -> tuple[list[dict], dict]:
    """Merge v2 + v3 candidates, parent-filter, return (merged, counters)."""
    merged: dict[str, dict] = {}
    counters = {"parent_filtered": 0}

    for c in v2_cands + v3_cands:
        smi = c["product_smiles"]
        # parent filter
        if _stereo_blind(smi) == parent_sb:
            counters["parent_filtered"] += 1
            continue
        if smi not in merged:
            merged[smi] = dict(c)
        else:
            mc = merged[smi]
            mc["source"] = _merge_source(mc["source"], c["source"])
            # take max of numeric fields
            for fld in ("template_freq", "reactions_count", "pattern_atom_count",
                        "n_evidence", "n_donor_records"):
                if c.get(fld, 0) > mc.get(fld, 0):
                    mc[fld] = c[fld]
            for fld in ("max_tanimoto", "mean_tanimoto", "mpnn_site_mean",
                        "mpnn_site_max"):
                if c.get(fld, 0.0) > mc.get(fld, 0.0):
                    mc[fld] = c[fld]
            if c.get("donor_exact_match", False):
                mc["donor_exact_match"] = True
            # prefer fuller product_smiles_full
            if c.get("product_smiles_full", "").count(".") > mc.get("product_smiles_full", "").count("."):
                mc["product_smiles_full"] = c["product_smiles_full"]

    return list(merged.values()), counters


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2-pool", default=V2_POOL)
    ap.add_argument("--v3-cands", default=V3_CANDS)
    ap.add_argument("--v3-queries", default=V3_QUERIES)
    ap.add_argument("--blind-csv", required=True, help="blind parent CSV (93 cases)")
    ap.add_argument("--ranker", default=RANKER_MODEL)
    ap.add_argument("--out-preds", required=True)
    ap.add_argument("--out-pool", required=True)
    ap.add_argument("--out-report", required=True)
    args = ap.parse_args()

    t_start = time.time()

    # ---- load data ----
    print("loading v2 pool...", flush=True)
    v2_pool = load_v2_pool(args.v2_pool)
    print(f"  {len(v2_pool)} cases", flush=True)

    print("loading v3 retrieval...", flush=True)
    v3_ret = load_v3_retrieval(args.v3_cands, args.v3_queries)
    print(f"  {len(v3_ret)} cases", flush=True)

    print("loading blind CSV...", flush=True)
    import csv
    blind = []
    with open(args.blind_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            blind.append({
                "case_id": row["full_route_case_id"],
                "smiles": row["parent_smiles"],
            })
    print(f"  {len(blind)} cases", flush=True)

    # ---- leak assertion (§5.2): training educts ∩ blind parents = 0 ----
    train_educts_path = os.path.join(os.path.dirname(args.ranker), "train_educts.json")
    if os.path.exists(train_educts_path):
        with open(train_educts_path) as f:
            te = json.load(f)
        train_sb = set(te.get("train_educts_sb", []))
        blind_sb = {_stereo_blind(b["smiles"]) for b in blind
                    if _stereo_blind(b["smiles"]) is not None}
        overlap = train_sb & blind_sb
        assert not overlap, (
            f"LEAK DETECTED: {len(overlap)} training educts overlap blind parents! "
            f"Samples: {sorted(overlap)[:5]}"
        )
        print(f"  leak assertion passed: 0 overlap "
              f"({len(train_sb)} train educts vs {len(blind_sb)} blind parents)",
              flush=True)
    else:
        print(f"  WARNING: train_educts.json not found, skip leak assertion",
              file=sys.stderr, flush=True)

    # ---- load ranker ----
    print("loading ranker model...", flush=True)
    import lightgbm as lgb
    model = lgb.Booster(model_file=args.ranker)
    print(f"  model loaded ({model.num_feature()} features)", flush=True)

    # ---- process each case ----
    print("predicting...", flush=True)
    results = []
    total_pf = 0
    total_cands = 0
    src_counts = defaultdict(int)

    for b in blind:
        cid = b["case_id"]
        smi = b["smiles"]
        parent_sb = _stereo_blind(smi)
        if parent_sb is None:
            results.append({
                "case_id": cid, "smiles": smi, "n_atoms": 0,
                "error": "parse_fail", "top_products": [],
                "all_candidates": [], "n_cand_union": 0,
            })
            continue

        v2_c = v2_pool.get(cid, [])
        v3_c = v3_ret.get(cid, [])
        merged, counters = merge_candidates(v2_c, v3_c, parent_sb)
        total_pf += counters["parent_filtered"]
        total_cands += len(merged)

        # compute features + predict
        scored = []
        for c in merged:
            feats = F.candidate_features(c, smi)
            if feats is None:
                continue
            proba = model.predict([feats])[0]
            c["ranker_proba"] = float(proba)
            src_counts[c["source"]] += 1
            scored.append(c)

        # sort by (-proba, product_smiles)
        scored.sort(key=lambda c: (-c["ranker_proba"], c["product_smiles"]))

        n_atoms = Chem.MolFromSmiles(smi).GetNumAtoms()

        def _serialize(c: dict) -> dict:
            return {
                "product_smiles": c["product_smiles"],
                "product_smiles_full": c.get("product_smiles_full", c["product_smiles"]),
                "source": c["source"],
                "rule_ids": c.get("rule_ids", []),
                "template_freq": c.get("template_freq", 0),
                "reactions_count": c.get("reactions_count", 0),
                "pattern_atom_count": c.get("pattern_atom_count", 0),
                "mpnn_site_mean": round(c.get("mpnn_site_mean", 0.0), 6),
                "mpnn_site_max": round(c.get("mpnn_site_max", 0.0), 6),
                "n_evidence": c.get("n_evidence", 0),
                "max_tanimoto": c.get("max_tanimoto", 0.0),
                "mean_tanimoto": c.get("mean_tanimoto", 0.0),
                "donor_exact_match": c.get("donor_exact_match", False),
                "ranker_proba": round(c["ranker_proba"], 6),
            }

        top = [_serialize(c) for c in scored[:TOP_K]]

        pool_truncated = False
        pool = [_serialize(c) for c in scored[:POOL_CAP]]
        if len(scored) > POOL_CAP:
            pool_truncated = True

        results.append({
            "case_id": cid,
            "smiles": smi,
            "n_atoms": n_atoms,
            "n_cand_v2": len(v2_c),
            "n_cand_v3": len(v3_c),
            "n_cand_union": len(scored),
            "parent_filtered": counters["parent_filtered"],
            "top_products": top,
            "all_candidates": pool,
            "pool_truncated": pool_truncated,
        })

    # ---- sort by case_id + write ----
    results.sort(key=lambda r: r["case_id"])

    with open(args.out_preds, "w") as f:
        for r in results:
            out = {k: v for k, v in r.items() if k != "all_candidates"}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    with open(args.out_pool, "w") as f:
        for r in results:
            out = {k: v for k, v in r.items() if k != "top_products"}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    # ---- run report ----
    report = {
        "n_cases": len(results),
        "total_time_s": round(time.time() - t_start, 2),
        "total_candidates": total_cands,
        "total_parent_filtered": total_pf,
        "source_distribution": dict(sorted(src_counts.items())),
        "pool_truncated_cases": [r["case_id"] for r in results if r.get("pool_truncated")],
        "zero_candidate_cases": [r["case_id"] for r in results if r.get("n_cand_union", 0) == 0],
        "mean_cands_per_case": round(total_cands / max(len(results), 1), 1),
    }
    with open(args.out_report, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"DONE: {len(results)} cases, {total_cands} candidates, "
          f"{total_pf} parent-filtered, {time.time() - t_start:.1f}s", flush=True)
    print(f"  source distribution: {dict(sorted(src_counts.items()))}", flush=True)
    zero = report["zero_candidate_cases"]
    if zero:
        print(f"  zero-candidate cases: {zero}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
