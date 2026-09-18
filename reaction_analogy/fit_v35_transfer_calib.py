#!/usr/bin/env python3
"""Fit the v3.5 transfer calibration: donor-Tanimoto -> P(candidate correct).

Diagnosis (diag_a2_gap.py): on library-external environmental parents the
correct retrieval-transfer candidates rank 12-363, buried under USPTO-only
candidates, because the EAWAG-fitted isotonic maps retrieval scores to tiny
values (the v3.1 retrieval ranker's p does not reflect donor similarity for
NON-exact donors — its top feature is donor_exact_match).

Fix: fit a second isotonic directly on the retrieval evidence:
  P(candidate correct | donor Tanimoto)  — transfer probability
fitted on a calib2 split (300 soil/sludge parents whose own reactions are
excluded from the calibration corpus; disjoint from BOTH the deployment
library and the holdout evaluation split).  Also refits the retrieval
score-isotonic on the new-corpus candidate distribution.  Saved as
data/bbd_v34/calibrator_v35.json (superset of calibrator_v34.json).

Data discipline: holdout parents (the A1/A2 evaluation set) are NEVER used
for fitting; the colleague's soil/sludge gold is never read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "src"))

from rdkit import Chem, RDLogger  # noqa: E402
RDLogger.DisableLog("rdApp.*")

import expand_bbd_routes as X  # noqa: E402
import single_smiles_v32 as S  # noqa: E402
import bbd_v33_fusion as V33  # noqa: E402
import bbd_v34_fusion as V34  # noqa: E402
import diag_ss_feedback_20260918 as D  # noqa: E402

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
ENV_OUT = os.path.join(_HERE, "data", "env_expand")
CALIB_DIR = os.path.join(ROOT, "data", "bbd_v34")


def sb(smi):
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m else None


def sbn(smi):
    norm = V33.normalize_charge_smiles(smi)
    return sb(norm) if norm else sb(smi)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-calib2", type=int, default=300)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    import random
    rng = random.Random(args.seed)

    # ---- 1. splits: held (eval) vs calib2 (fit) vs library ----
    held = set(json.load(open(os.path.join(ENV_OUT, "holdout_parents.json")))
               ["parents"])
    fg_all = {}
    with open(os.path.join(ENV_OUT, "first_gen_truth_all.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            fg_all[r["parent_id"]] = r
    pool = [pid for pid in fg_all if pid not in held]
    calib2 = set(rng.sample(pool, min(args.n_calib2, len(pool))))
    print(f"held (eval): {len(held)}, calib2 (fit): {len(calib2)}, "
          f"library parents: {len(pool) - len(calib2)}", flush=True)

    # ---- 2. calibration corpus: all records minus held AND calib2 parents
    # (reuse the builder logic: env_reactions + BBD pairs, drop excluded) ----
    env_rows = [json.loads(line) for line in
                open(os.path.join(ENV_OUT, "env_reactions.jsonl"))]

    def donor_id(smi):
        norm = V33.normalize_charge_smiles(smi)
        return sb(norm) if norm else sb(smi)

    cal_corpus = os.path.join(_HERE, "data", "corpus_calib2")
    os.makedirs(cal_corpus, exist_ok=True)
    excluded = held | calib2
    n_rec = n_di = 0
    with open(os.path.join(_HERE, "data/corpus_v1/corpus_v1.jsonl")) as src, \
            open(os.path.join(cal_corpus, "corpus_v1.jsonl"), "w") as dst:
        for line in src:
            dst.write(line)
        for r in env_rows:
            did = donor_id(r["educt_smiles"])
            if did is None or did in excluded:
                continue
            rec = {
                "atom_mapping": None, "direction": None,
                "donor_A_smiles": r["educt_smiles"],
                "donor_components": [r["educt_smiles"]],
                "ec": (r.get("ec_numbers") or [None])[0],
                "mapping_status": "absent", "master_id": None,
                "parse_note": f"envipath-{r['package'].lower()}",
                "product_B_smiles": r["product_smiles"],
                "product_components": [r["product_smiles"]],
                "provenance_sha256": None, "reaction_smiles": None,
                "record_id": f"env:{r['package']}:{r['reaction_id']}",
                "source_id": r["pathway_id"], "source_type": "envipath",
            }
            dst.write(json.dumps(rec, ensure_ascii=False, sort_keys=True)
                      + "\n")
            n_rec += 1
    with open(os.path.join(_HERE, "data/bbd_expand/donor_product.jsonl")) as bf, \
            open(os.path.join(cal_corpus, "corpus_v1.jsonl"), "a") as dst:
        for line in bf:
            r = json.loads(line)
            did = donor_id(r["donor_smiles"])
            if did is None or did in excluded:
                continue
            rec = {
                "atom_mapping": None, "direction": None,
                "donor_A_smiles": r["donor_smiles"],
                "donor_components": [r["donor_smiles"]],
                "ec": None, "mapping_status": "absent", "master_id": None,
                "parse_note": "envipath-eawag-bbd",
                "product_B_smiles": r["product_smiles"],
                "product_components": [r["product_smiles"]],
                "provenance_sha256": None, "reaction_smiles": None,
                "record_id": f"env:EAWAG-BBD:{r.get('btid','')}#"
                             f"{r.get('reac_id','')}",
                "source_id": r.get("btid", ""), "source_type": "envipath",
            }
            dst.write(json.dumps(rec, ensure_ascii=False, sort_keys=True)
                      + "\n")
            n_rec += 1
    with open(os.path.join(_HERE, "data/corpus_v1/donor_index.jsonl")) as src, \
            open(os.path.join(cal_corpus, "donor_index.jsonl"), "w") as dst:
        for line in src:
            dst.write(line)
        seen_di = set()
        for r in env_rows:
            did = donor_id(r["educt_smiles"])
            if did is None or did in excluded:
                continue
            rec_id = f"env:{r['package']}:{r['reaction_id']}"
            if (did, rec_id) in seen_di:
                continue
            seen_di.add((did, rec_id))
            dst.write(json.dumps({
                "donor_smiles": r["educt_smiles"], "donor_id": did,
                "donor_record_id": rec_id, "source_type": "envipath",
                "package": r["package"]},
                ensure_ascii=False, sort_keys=True) + "\n")
            n_di += 1
    print(f"corpus_calib2: +{n_rec} records, +{n_di} donors "
          f"(held+calib2 excluded)", flush=True)

    # ---- 3. generate + score candidates for calib2 parents ----
    X.CORPUS_DIR = cal_corpus
    print("loading engines (calib2 corpus)...", flush=True)
    S.load_engines()
    rankers = D.load_rankers(os.path.join(ROOT, "data/bbd_v31"))

    tan_pairs = []      # (max_tanimoto, label) retrieval-family candidates
    rp_pairs = []       # (p_retrieval, label) for refit
    t0 = time.time()
    items = sorted(calib2)
    for i, pid in enumerate(items):
        r = fg_all[pid]
        smi = None
        # raw parent smiles: find from env rows
        for er in env_rows:
            if donor_id(er["educt_smiles"]) == pid:
                smi = er["educt_smiles"]
                break
        if smi is None:
            continue
        ts = set(r["all_products_sb"]) | set(r["accepted_products_sb"])
        tsn = {sbn(p) for p in ts}
        parent_sb = sb(smi)
        root_node = {
            "node_id": "CAL2", "case_id": "CAL2", "depth": 0, "smiles": smi,
            "canonical_smiles": X._identity(smi) or parent_sb or smi,
            "is_root": True, "ancestor_canons": set(), "path_score": 1.0,
        }
        S.attach_retrieval([root_node])
        cands, _ = X._generate_candidates(smi, parent_sb, root_node["_retrieval"])
        D.score_case(cands, smi, rankers)
        for c in cands:
            psb = sb(c.get("product_smiles", ""))
            lab = int(psb is not None and (psb in ts
                                           or sbn(c["product_smiles"]) in tsn))
            if "retrieval" in c.get("source", ""):
                tan_pairs.append((float(c.get("max_tanimoto", 0.0)), lab))
                rp_pairs.append((float(c.get("p_retrieval", 0.0)), lab))
        if (i + 1) % 50 == 0:
            print(f"  calib2 {i+1}/{len(items)} ({time.time()-t0:.0f}s, "
                  f"{len(tan_pairs)} retrieval candidates)", flush=True)

    print(f"retrieval candidates: {len(tan_pairs)}, "
          f"positives: {sum(l for _, l in tan_pairs)}", flush=True)

    # ---- 4. fit ----
    from sklearn.isotonic import IsotonicRegression

    def fit_iso(pairs):
        xs = [p for p, _ in pairs]
        ys = [l for _, l in pairs]
        if not xs or sum(ys) == 0:
            return None
        ir = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        ir.fit(xs, ys)
        return {"cuts": [float(x) for x in ir.X_thresholds_],
                "vals": [float(y) for y in ir.y_thresholds_]}

    tan_iso = fit_iso(tan_pairs)
    rp_iso = fit_iso(rp_pairs)
    if tan_iso:
        # spot values
        def val_at(p):
            cuts, vals = tan_iso["cuts"], tan_iso["vals"]
            if p <= cuts[0]:
                return vals[0]
            if p >= cuts[-1]:
                return vals[-1]
            import bisect
            i = min(bisect.bisect_left(cuts, p), len(vals) - 1)
            return vals[i]
        print("tanimoto->P(pos):", {t: round(val_at(t), 4)
                                     for t in (0.3, 0.5, 0.7, 0.85, 0.95, 1.0)},
              flush=True)

    # ---- 5. save calibrator_v35.json (v34 + transfer iso) ----
    base = json.load(open(os.path.join(CALIB_DIR, "calibrator_v34.json")))
    base["version"] = "v35-calibrator-1"
    base["retrieval_tanimoto"] = tan_iso or {}
    if rp_iso:
        base["sources"]["retrieval"] = rp_iso
        base["meta"]["retrieval_refit"] = {"n": len(rp_pairs),
                                           "pos": int(sum(l for _, l in
                                                          rp_pairs))}
    with open(os.path.join(CALIB_DIR, "calibrator_v35.json"), "w") as f:
        json.dump(base, f, indent=2)
    print("saved calibrator_v35.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
