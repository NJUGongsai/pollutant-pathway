#!/usr/bin/env python3
"""v3.5 environmental-asset evaluation (soil/sludge repair round 2, 2026-09-18).

Two calibers on the crawled EAWAG-SOIL/SLUDGE (+SEDIMENT) data:

  A. HONEST GENERALIZATION (leave-parent-out): holdout parents whose
     reactions are EXCLUDED from library_eval + corpus_env_eval — the hybrid
     (v3.4 scoring, expanded retrieval corpus, no lookup visibility) must
     find their true products via genuine transfer.  Reports:
       A1 retrieval-transfer oracle (fast, all holdout parents): fraction
          whose true product appears among top-20 retrieved donors' products
       A2 full hybrid Hit@K on a random sample (slow, engine per parent)

  B. LIBRARY-COVERED (deployment proxy = the colleague's soil/sludge
     caliber): in-library parents with library_full + corpus_env — the
     lookup tier delivers recorded products at rank-1 by construction;
     this validates the wiring and approximates what the frozen v3.5 will
     score on their set (their parents are EAWAG-SOIL/SLUDGE compounds).

NEVER reads the colleague's soil/sludge gold (not present locally).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
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
import diag_ss_feedback_20260918 as D  # noqa: E402

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
ENV_OUT = os.path.join(_HERE, "data", "env_expand")
KS = (1, 3, 5, 10)


def sb(smi):
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m else None


def sbn(smi):
    norm = V33.normalize_charge_smiles(smi)
    return sb(norm) if norm else sb(smi)


def load_truth():
    truth = {}
    with open(os.path.join(ENV_OUT, "holdout_truth.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            truth[r["parent_id"]] = {
                "raw": r["parent"],
                "truth_sb": set(r["accepted_products_sb"]),
                "truth_sbn": {sbn(p) for p in r["accepted_products_sb"]},
            }
    return truth


def hybrid_case(smi, lookup_index, truth_sb, truth_sbn, k=10):
    """One full hybrid case (v3.4 prediction + lookup pinned)."""
    root_identity = X._identity(smi) or smi
    root_node = {
        "node_id": X._node_id("ENV-EVAL", 0, root_identity),
        "case_id": "ENV-EVAL", "depth": 0, "smiles": smi,
        "canonical_smiles": root_identity, "is_root": True,
        "ancestor_canons": set(), "path_score": 1.0,
    }
    S.attach_retrieval([root_node])
    res = S.expand_node(root_node)
    pred = list(res["edges"])
    look = EGD.lookup(lookup_index, smi)
    look_canons = {sb(V33.normalize_charge_smiles(c["product_smiles"])
                      or c["product_smiles"]) for c in look}
    pred_dedup = [e for e in pred
                  if sb(V33.normalize_charge_smiles(e["product_smiles"])
                        or e["product_smiles"]) not in look_canons]
    merged = list(look) + pred_dedup if look else pred

    hr = None
    for i, m in enumerate(merged[:k]):
        ps = m.get("product_smiles", "")
        pid = m.get("product_identity", ps)
        hit = (sb(ps) in truth_sb) or (sbn(pid) in truth_sbn)
        if hit:
            hr = i + 1
            break
    return {"hit_rank": hr, "n_lookup": len(look), "n_pred": len(pred)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", type=int, default=60,
                    help="A2 full-hybrid sample size")
    ap.add_argument("--sample-covered", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-b", action="store_true")
    ap.add_argument("--only-b", action="store_true",
                    help="run only the B (library-covered) caliber")
    ap.add_argument("--out-suffix", default="",
                    help="suffix for the output json (avoid write races)")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    # ---- A1: retrieval-transfer oracle (fast) on ALL holdout parents ----
    a1 = {"skipped": True}
    a2 = {"skipped": True}
    if not args.only_b:
        print("[A1] loading eval corpus engines...", flush=True)
        X.CORPUS_DIR = os.path.join(_HERE, "data", "corpus_env_eval")
        t0 = time.time()
        S.load_engines()
        print(f"[A1] engines loaded ({time.time()-t0:.0f}s): "
              f"{len(X._G_RECORDS)} records, "
              f"{len(X._G_DONOR_TO_RECORDS)} donors", flush=True)

        truth = load_truth()
        print(f"[A1] {len(truth)} holdout parents", flush=True)

        donors = sorted(X._G_DONOR_TO_RECORDS.keys())
        q_map = {v["raw"]: v["raw"] for v in truth.values()}
        t0 = time.time()
        ranked = S.retrieval.rank_queries(q_map, donors, k=20)
        print(f"[A1] retrieval done ({time.time()-t0:.0f}s)", flush=True)

        a1 = {"n": 0, "retrieval_oracle": 0, "exact_donor_leak": 0}
        for pid, v in truth.items():
            raw = v["raw"]
            hits = ranked.get(raw, {}).get("topK", [])
            a1["n"] += 1
            if any(h["tanimoto"] >= 0.999 for h in hits):
                a1["exact_donor_leak"] += 1
            found = False
            for h in hits:
                for rid in X._G_DONOR_TO_RECORDS.get(h["donor_smiles"], []):
                    rec = X._G_RECORDS.get(rid)
                    if rec is None:
                        continue
                    for prod in rec.get("product_components", []):
                        if sb(prod) in v["truth_sb"] or sbn(prod) in v["truth_sbn"]:
                            found = True
                            break
                    if found:
                        break
                if found:
                    break
            if found:
                a1["retrieval_oracle"] += 1
        print(f"[A1] retrieval-transfer oracle: "
              f"{a1['retrieval_oracle']}/{a1['n']} = "
              f"{a1['retrieval_oracle']/max(a1['n'],1):.1%}; "
              f"exact-donor leak check: {a1['exact_donor_leak']}", flush=True)

        # ---- A2: full hybrid on a holdout sample ----
        print("[A2] full hybrid on holdout sample (v3.4 + eval corpus)...",
              flush=True)
        X._G_SCORING = "v34"
        S.setup_v34()
        index_eval = EGD.build_index(os.path.join(ENV_OUT, "library_eval.jsonl"))
        index_eval.pop("__parse_fail__", None)
        sample = rng.sample(sorted(truth), min(args.sample, len(truth)))
        results = []
        t0 = time.time()
        for i, pid in enumerate(sample):
            v = truth[pid]
            r = hybrid_case(v["raw"], index_eval, v["truth_sb"], v["truth_sbn"])
            results.append({"parent_id": pid, **r})
            if (i + 1) % 10 == 0:
                print(f"[A2] {i+1}/{len(sample)} ({time.time()-t0:.0f}s) "
                      f"hit@1 so far: "
                      f"{sum(1 for x in results if x['hit_rank']==1)}",
                      flush=True)
        hits = {k: sum(1 for r in results
                       if r["hit_rank"] is not None and r["hit_rank"] <= k)
                for k in KS}
        a2 = {"n": len(results),
              **{f"hit@{k}": hits[k] for k in KS},
              **{f"hit@{k}_pct": round(hits[k] / max(len(results), 1), 4)
                 for k in KS}}

    # ---- B: library-covered wiring check ----
    b = {}
    b2 = {}
    if not args.skip_b:
        print("[B] library-covered caliber (library_full + corpus_env)...",
              flush=True)
        X.CORPUS_DIR = os.path.join(_HERE, "data", "corpus_env")
        S.load_engines()
        X._G_SCORING = "v34"
        S.setup_v34()
        index_full = EGD.build_index(os.path.join(ENV_OUT,
                                                  "library_full.jsonl"))
        index_full.pop("__parse_fail__", None)
        lib_parents = {}
        with open(os.path.join(ENV_OUT, "library_full.jsonl")) as f:
            for line in f:
                r = json.loads(line)
                lib_parents.setdefault(r["donor_id"], r["donor_smiles"])
        # first-generation truth (mirrors the colleague's curation policy);
        # B caliber samples PATHWAY-ROOT parents (first-gen truth)
        fg_truth = {}
        all_truth = {}
        with open(os.path.join(ENV_OUT, "first_gen_truth_all.jsonl")) as f:
            for line in f:
                r = json.loads(line)
                if r.get("is_root_parent"):
                    fg_truth[r["parent_id"]] = set(
                        r["accepted_products_sb"])
                all_truth[r["parent_id"]] = set(r["all_products_sb"])
        # soil/sludge parent domain only (the colleague's set provenance)
        ss_parents = {pid: lib_parents[pid] for pid in fg_truth
                      if pid in lib_parents}
        ss_all = {pid: lib_parents[pid] for pid in all_truth
                  if pid in lib_parents}
        print(f"[B] root soil/sludge parents in library: {len(ss_parents)}; "
              f"all soil/sludge parents in library: {len(ss_all)}",
              flush=True)
        sample_cov = rng.sample(sorted(ss_parents),
                                min(args.sample_covered, len(ss_parents)))
        cov_results = []
        for pid in sample_cov:
            raw = ss_parents[pid]
            ts = fg_truth[pid]
            tsn = {sbn(t) for t in ts}
            r = hybrid_case(raw, index_full, ts, tsn)
            cov_results.append({"parent_id": pid, **r})
        hits_c = {k: sum(1 for r in cov_results
                         if r["hit_rank"] is not None and r["hit_rank"] <= k)
                  for k in KS}
        b = {"n": len(cov_results),
             "n_lookup_visible": sum(1 for r in cov_results if r["n_lookup"]),
             **{f"hit@{k}": hits_c[k] for k in KS},
             **{f"hit@{k}_pct": round(hits_c[k] / max(len(cov_results), 1), 4)
                for k in KS}}

        # B2: ALL-parents / ALL-products truth — the closest local mirror of
        # the colleague's set statistics (1,788 parents ~ all educts;
        # 2,924 products ~ deduped SOIL+SLUDGE pairs)
        sample_all = rng.sample(sorted(ss_all),
                                 min(args.sample_covered, len(ss_all)))
        cov2_results = []
        for pid in sample_all:
            raw = ss_all[pid]
            ts = all_truth[pid]
            tsn = {sbn(t) for t in ts}
            r = hybrid_case(raw, index_full, ts, tsn)
            cov2_results.append({"parent_id": pid, **r})
        hits_c2 = {k: sum(1 for r in cov2_results
                          if r["hit_rank"] is not None and r["hit_rank"] <= k)
                   for k in KS}
        b2 = {"n": len(cov2_results),
              "n_lookup_visible": sum(1 for r in cov2_results
                                       if r["n_lookup"]),
              **{f"hit@{k}": hits_c2[k] for k in KS},
              **{f"hit@{k}_pct": round(hits_c2[k] / max(len(cov2_results), 1),
                                       4) for k in KS}}

    out = {"A1_retrieval_transfer_oracle": a1,
           "A2_hybrid_holdout_v34": a2,
           "B_library_covered_firstgen": b,
           "B2_library_covered_allpairs": b2,
           "sample": args.sample, "seed": args.seed}
    with open(os.path.join(_HERE, "reports", "SS_DIAG_2026-09-18",
                           f"v35_env_eval{args.out_suffix}.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False), flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
