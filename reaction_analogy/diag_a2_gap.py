#!/usr/bin/env python3
"""Diagnose the A2 gap: oracle 74.7% vs hybrid hit@1 5% on holdout parents.

For a sample of holdout parents: where do the CORRECT candidates rank in the
v3.4 fused order, what source/score do they carry, and what beats them?
"""
from __future__ import annotations

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

ENV_OUT = os.path.join(_HERE, "data", "env_expand")


def sb(smi):
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m else None


def sbn(smi):
    norm = V33.normalize_charge_smiles(smi)
    return sb(norm) if norm else sb(smi)


def main() -> int:
    rng = random.Random(0)
    X.CORPUS_DIR = os.path.join(_HERE, "data", "corpus_env_eval")
    S.load_engines()
    X._G_SCORING = "v34"
    S.setup_v34()
    index = EGD.build_index(os.path.join(ENV_OUT, "library_eval.jsonl"))
    index.pop("__parse_fail__", None)

    truth = {}
    with open(os.path.join(ENV_OUT, "holdout_truth.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            truth[r["parent_id"]] = r

    sample = rng.sample(sorted(truth), 12)
    for pid in sample:
        r = truth[pid]
        smi = r["parent"]
        ts = set(r["accepted_products_sb"])
        tsn = {sbn(p) for p in ts}
        root_identity = X._identity(smi) or smi
        root_node = {
            "node_id": X._node_id("DIAG", 0, root_identity), "case_id": "DIAG",
            "depth": 0, "smiles": smi, "canonical_smiles": root_identity,
            "is_root": True, "ancestor_canons": set(), "path_score": 1.0,
        }
        S.attach_retrieval([root_node])
        res = S.expand_node(root_node)
        cands = res["edges"]  # ranked, serialized edge dicts
        correct = [(i + 1, c) for i, c in enumerate(cands)
                   if sb(c["product_smiles"]) in ts
                   or sbn(c.get("product_identity",
                                c["product_smiles"])) in tsn]
        n_corr = len(correct)
        best = correct[0] if correct else None
        top1 = cands[0] if cands else None
        above = []
        if best:
            rank, bc = best
            above = [c for c in cands[:rank - 1]]
            fam_above = {}
            for c in above:
                s = c.get("source", "")
                key = ("uspto-only" if s == "uspto" else
                       "envipath-only" if s == "envipath" else
                       "retrieval-only" if s == "retrieval" else s)
                fam_above[key] = fam_above.get(key, 0) + 1
            print(f"{pid[:20]}: n_cand={len(cands)} correct={n_corr} "
                  f"best_rank={rank} src={bc.get('source','')[:18]} "
                  f"score={bc.get('edge_score')} "
                  f"tan={bc.get('max_tanimoto', bc.get('tanimoto',''))} "
                  f"| top1: src={top1.get('source','')[:18]} "
                  f"score={top1.get('edge_score')} "
                  f"| above: {fam_above}")
        else:
            print(f"{pid[:20]}: n_cand={len(cands)} correct=0 (generation "
                  f"gap) | top1: {top1.get('source','') if top1 else ''}"
                  f" {top1.get('edge_score') if top1 else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
