#!/usr/bin/env python3
"""Engine C: similarity-retrieval candidate pool for 93 v0.3 blind parents.

Reuses ``retrieve_pilot.py``'s Morgan/Tanimoto logic (fp radius=2, 2048 bit,
Tanimoto top-K=20) but:
  - queries the 93 v0.3 blind parents (not 83 v0.2),
  - applies stereo-blind parent filtering (old pool had 23/83 parent copies),
  - tracks ``donor_exact_match`` evidence for leak-audit (§5.1).

Answer-key isolation: this file NEVER reads the restricted answer key.

Outputs (under data/retrieval_v3/):
  queries.jsonl      — per-case topK + candidate summary
  candidates.jsonl    — flat candidate → evidence mapping
  coverage.json       — coverage summary
  MANIFEST.sha256      — deterministic manifest
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "src"))

from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")

from ra import corpus, retrieval  # noqa: E402
from ra.chem import canonical_smiles  # noqa: E402
from ra.io import manifest_write, stable_json_dump, stable_json_lines  # noqa: E402

CORPUS_DIR = os.path.join(_HERE, "data", "corpus_v1")


# --------------------------------------------------------------------------- #
# Query loading (v0.3 blind CSV — different columns from v0.2)
# --------------------------------------------------------------------------- #
def load_queries_v03(csv_path: str) -> list[dict]:
    """Read v0.3 blind parent inputs.

    Returns ``[{case_id, x_raw, x_smiles|None, error|None}]``.
    """
    queries = []
    with open(csv_path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cid = (row.get("full_route_case_id") or "").strip()
            x_raw = (row.get("parent_smiles") or "").strip()
            try:
                x_smi = canonical_smiles(x_raw)
                error = None
            except Exception as exc:
                x_smi = None
                error = f"{exc}"
            queries.append({
                "case_id": cid,
                "x_raw": x_raw,
                "x_smiles": x_smi,
                "error": error,
            })
    return queries


# --------------------------------------------------------------------------- #
# Canonicalisation helpers
# --------------------------------------------------------------------------- #
def _stereo_blind(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    return Chem.MolToSmiles(m, isomericSmiles=False)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-dir", default=CORPUS_DIR)
    ap.add_argument("--queries-csv", required=True,
                    help="v0.3 blind CSV (93 parents)")
    ap.add_argument("--out", default=os.path.join(_HERE, "data", "retrieval_v3"))
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0, help="limit N cases (0=all)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # ---- load corpus + donor index ----
    print("loading corpus...", flush=True)
    records = {r["record_id"]: r
               for r in corpus.read_records(
                   os.path.join(args.corpus_dir, "corpus_v1.jsonl"))}
    donor_entries = corpus.load_donor_index(
        os.path.join(args.corpus_dir, "donor_index.jsonl"))

    donor_to_records: dict[str, list[str]] = defaultdict(list)
    for e in donor_entries:
        donor_to_records[e["donor_smiles"]].append(e["donor_record_id"])
    for k in donor_to_records:
        donor_to_records[k] = sorted(set(donor_to_records[k]))
    donors = sorted(donor_to_records.keys())
    print(f"  {len(records)} records, {len(donors)} unique donors", flush=True)

    # ---- load queries ----
    queries = load_queries_v03(args.queries_csv)
    if args.limit > 0:
        queries = queries[:args.limit]
    print(f"  {len(queries)} queries", flush=True)

    q_map = {q["case_id"]: q["x_smiles"]
             for q in queries if q["x_smiles"]}
    q_errors = [q for q in queries if not q["x_smiles"]]

    # ---- rank donors per query ----
    print("ranking donors...", flush=True)
    ranked = retrieval.rank_queries(q_map, donors, k=args.k)

    # ---- build candidates + evidence ----
    query_rows = []
    candidate_rows = []
    cases = []
    cases_for_stats = []
    parent_filtered_total = 0

    for q in queries:
        cid = q["case_id"]
        if q["x_smiles"] is None:
            cases.append({"case_id": cid, "has_candidate": False,
                          "n_candidates": 0, "status": "query_unparseable"})
            cases_for_stats.append({"case_id": cid, "candidates": []})
            continue

        x_smi = q["x_smiles"]
        parent_sb = _stereo_blind(x_smi)
        topk = ranked.get(cid, {}).get("topK", [])

        # gather evidence per candidate
        cand_evidence: dict[str, list[dict]] = defaultdict(list)
        cand_full_products: dict[str, str] = {}  # best full product per candidate

        for hit in topk:
            donor_smi = hit["donor_smiles"]
            tanimoto = hit["tanimoto"]
            donor_sb = _stereo_blind(donor_smi)
            is_exact = (donor_sb == parent_sb) if donor_sb and parent_sb else False
            rec_ids = donor_to_records.get(donor_smi, [])

            for rid in rec_ids:
                rec = records.get(rid)
                if rec is None:
                    continue
                # full product from this record
                full_product = ".".join(sorted(rec.get("product_components", [])))
                for prod_frag in rec.get("product_components", []):
                    try:
                        c_smi = canonical_smiles(prod_frag)
                    except Exception:
                        continue
                    if not c_smi:
                        continue
                    ev_entry = {
                        "donor_smiles": donor_smi,
                        "tanimoto": tanimoto,
                        "donor_record_id": rid,
                        "source_id": rec.get("source_id"),
                        "donor_exact_match": is_exact,
                    }
                    cand_evidence[c_smi].append(ev_entry)
                    # keep full product from highest-tanimoto donor
                    if c_smi not in cand_full_products or tanimoto > cand_evidence[c_smi][0]["tanimoto"]:
                        # This is set on first evidence; update with best
                        pass
                    if c_smi not in cand_full_products:
                        cand_full_products[c_smi] = full_product
                    else:
                        # prefer the fuller product or the one from higher-tanimoto donor
                        prev_best_t = max(e["tanimoto"] for e in cand_evidence[c_smi])
                        if tanimoto >= prev_best_t:
                            cand_full_products[c_smi] = full_product

        # parent filter (stereo-blind)
        cands_filtered = {}
        parent_filtered = 0
        for c_smi, ev_list in sorted(cand_evidence.items()):
            c_sb = _stereo_blind(c_smi)
            if c_sb == parent_sb:
                parent_filtered += 1
                continue
            cands_filtered[c_smi] = ev_list
        parent_filtered_total += parent_filtered

        # build candidate rows
        for c_smi, ev_list in sorted(cands_filtered.items()):
            tanimotos = [e["tanimoto"] for e in ev_list]
            max_t = max(tanimotos)
            mean_t = sum(tanimotos) / len(tanimotos)
            donor_exact = any(e["donor_exact_match"] for e in ev_list)
            leak_count = sum(1 for e in ev_list if e["donor_exact_match"])
            source_ids = sorted({e["source_id"] for e in ev_list if e.get("source_id")})

            candidate_rows.append({
                "case_id": cid,
                "candidate_smiles": c_smi,
                "product_smiles_full": cand_full_products.get(c_smi, c_smi),
                "n_evidence": len(ev_list),
                "max_tanimoto": round(max_t, 6),
                "mean_tanimoto": round(mean_t, 6),
                "top_donor_sources": source_ids,
                "n_donor_records": len({e["donor_record_id"] for e in ev_list}),
                "donor_exact_match": donor_exact,
                "leak_filtered_records": leak_count,
            })

        cand_smis = sorted(cands_filtered.keys())
        query_rows.append({
            "case_id": cid,
            "x_smiles": x_smi,
            "n_retrieved": len(topk),
            "topK": [{"rank": h["rank"], "donor_smiles": h["donor_smiles"],
                       "tanimoto": h["tanimoto"]}
                      for h in topk],
            "n_candidates": len(cand_smis),
            "candidates": cand_smis,
            "has_candidate": bool(cand_smis),
            "parent_filtered": parent_filtered,
        })
        cases.append({"case_id": cid, "has_candidate": bool(cand_smis),
                      "n_candidates": len(cand_smis), "status": "ok"})
        cases_for_stats.append({"case_id": cid, "candidates": cand_smis})

    # ---- write outputs ----
    stable_json_lines(query_rows, os.path.join(args.out, "queries.jsonl"))
    stable_json_lines(candidate_rows, os.path.join(args.out, "candidates.jsonl"))
    cov = retrieval.coverage_stats(cases_for_stats)
    cov["unparseable_queries"] = len(q_errors)
    cov["parent_filtered_total"] = parent_filtered_total
    cov["per_case"] = cases
    stable_json_dump(cov, os.path.join(args.out, "coverage.json"))
    manifest_write(args.out, ["queries.jsonl", "candidates.jsonl", "coverage.json"])

    # ---- summary ----
    print(json.dumps({k: v for k, v in cov.items() if k != "per_case"},
                     indent=2, sort_keys=True))
    # check DCE case if present
    for cr in candidate_rows:
        if cr["case_id"] == "FR-BBD3-PARENT-c0001" and cr["candidate_smiles"] == "OCCCl":
            print(f"\n  DCE check: OCCCl found! "
                  f"donor_exact_match={cr['donor_exact_match']} "
                  f"max_tanimoto={cr['max_tanimoto']} "
                  f"sources={cr['top_donor_sources']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
