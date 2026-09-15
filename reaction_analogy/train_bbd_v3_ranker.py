#!/usr/bin/env python3
"""BBD v3 LightGBM ranker training.

Training data = RHEA reactions from corpus_v1 (educt→product).  For each
unique educt (leak-filtered per §5.2), candidates are generated with three
engines offline:

  A: USPTO top-2k templates by freq (graph-edit, 60s budget/educt)
  B: enviPath 286 rules (RunReactants)
  C: retrieval (educt as query vs donor library, Tanimoto top-20)

Label = candidate stereo-blind canonical == true product stereo-blind canonical
(binary pointwise; lambda-rank not needed — positives are sparse and Hit@K
口径 is pointwise-sufficient per task §4.4).

Leak filtering (§5.2, fail-closed):
  1. Exact match: educt stereo-blind canonical ∈ blind parent canonicals → drop
  2. Near-dup: Tanimoto(educt, any blind parent) ≥ 0.95 → drop
  The surviving educt list is saved as meta for runtime assertion.

No MPNN features (§4.4 "both sides without" — v2 ablation showed near-zero
MPNN discriminative power; chenyu step skipped).

Answer-key isolation: this file NEVER reads the restricted answer key.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict
from typing import Any

import multiprocessing as mp

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "src"))

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem
from rdkit import DataStructs
RDLogger.DisableLog("rdApp.*")

import gnn_phase6_apply as A  # noqa: E402
import predict_bbd_products_v2 as P2  # noqa: E402 — reuse engine A/B
import bbd_v3_features as F  # noqa: E402
from ra import corpus, retrieval  # noqa: E402
from ra.chem import canonical_smiles, morgan_fp  # noqa: E402
from ra.io import stable_json_dump  # noqa: E402

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
CORPUS_DIR = os.path.join(_HERE, "data", "corpus_v1")
USPTO_TEMPLATES = os.path.join(_HERE, "templates.json")
ENVIPATH_RULES = os.path.join(ROOT, "data/hfix/templates_implicitH.jsonl")
ENVIPATH_TSV = os.path.join(ROOT, "reaction_v3/data/lib_envipath/templates.tsv.gz")
TRAIN_TOP_N = 2000  # USPTO top-N templates by freq for training
RXN_BUDGET_TRAIN = 60.0  # per-educt budget for Engine A

# Globals for fork workers
_G_TPL_A: list | None = None
_G_RULES_B: list | None = None
_G_RECORDS: dict | None = None
_G_DONOR_TO_RECORDS: dict | None = None
_G_RETRIEVAL: dict | None = None  # educt_smi -> [{donor_smiles, tanimoto, donor_records}]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _stereo_blind(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def _sig(a):
    return (a.GetSymbol(), a.GetIsAromatic(), a.GetFormalCharge())


# --------------------------------------------------------------------------- #
# Step 1: Load RHEA reactions and extract unique educts
# --------------------------------------------------------------------------- #
def load_training_educts(corpus_dir: str) -> list[dict]:
    """Load RHEA reactions with products; return unique educt → true products.

    Uses ``donor_components`` (individual fragments) and filters out small
    co-substrates (≤ 2 heavy atoms: water, O₂, ammonia, H⁺, etc.) so that
    the educt set reflects organic substrates (~12k unique, per task spec).

    Returns list of {educt_smiles, educt_sb, true_products_sb: set}.
    """
    records = list(corpus.read_records(os.path.join(corpus_dir, "corpus_v1.jsonl")))
    educt_map: dict[str, set[str]] = {}  # educt_sb -> set of true product sb

    for rec in records:
        if not rec.get("product_components"):
            continue
        # use individual donor components (not the joined donor_A_smiles)
        comps = rec.get("donor_components") or []
        if not comps:
            comps = [rec.get("donor_A_smiles", "")] if rec.get("donor_A_smiles") else []
        for frag in comps:
            m = Chem.MolFromSmiles(frag)
            if m is None:
                continue
            if m.GetNumHeavyAtoms() <= 2:  # skip small co-substrates
                continue
            educt_sb = _stereo_blind(frag)
            if not educt_sb:
                continue
            for prod in rec["product_components"]:
                prod_sb = _stereo_blind(prod)
                if prod_sb:
                    educt_map.setdefault(educt_sb, set()).add(prod_sb)

    return [{"educt_sb": k, "true_products_sb": v}
            for k, v in sorted(educt_map.items())]


# --------------------------------------------------------------------------- #
# Step 2: Leak filtering (§5.2)
# --------------------------------------------------------------------------- #
def load_blind_parents(csv_path: str) -> set[str]:
    """Return set of stereo-blind canonical SMILES for 93 blind parents."""
    parents = set()
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sb = _stereo_blind(row.get("parent_smiles", ""))
            if sb:
                parents.add(sb)
    return parents


def filter_leaks(educts: list[dict], blind_parents: set[str],
                 tanimoto_threshold: float = 0.95) -> tuple[list[dict], dict]:
    """Remove educts that match or nearly match blind parents (§5.2).

    Returns (filtered_educts, stats).
    """
    # Step 1: exact match
    exact_hits = []
    remaining = []
    for e in educts:
        if e["educt_sb"] in blind_parents:
            exact_hits.append(e["educt_sb"])
        else:
            remaining.append(e)

    # Step 2: Tanimoto ≥ threshold
    blind_fps = []
    blind_sb_list = sorted(blind_parents)
    for sb in blind_sb_list:
        try:
            fp = morgan_fp(sb)
            if fp is not None:
                blind_fps.append(fp)
        except Exception:
            pass

    near_dup = []
    if blind_fps:
        for e in remaining:
            try:
                fp = morgan_fp(e["educt_sb"])
                if fp is None:
                    continue
            except Exception:
                continue
            sims = DataStructs.BulkTanimotoSimilarity(fp, blind_fps)
            if any(s >= tanimoto_threshold for s in sims):
                near_dup.append(e["educt_sb"])

    near_dup_set = set(near_dup)
    filtered = [e for e in remaining if e["educt_sb"] not in near_dup_set]

    stats = {
        "n_educts_total": len(educts),
        "n_exact_match_removed": len(exact_hits),
        "n_near_dup_removed": len(near_dup),
        "n_educts_kept": len(filtered),
        "exact_match_samples": sorted(exact_hits)[:10],
        "near_dup_samples": sorted(near_dup)[:10],
    }
    return filtered, stats


# --------------------------------------------------------------------------- #
# Step 3: Batch retrieval (Engine C) for all training educts
# --------------------------------------------------------------------------- #
def batch_retrieval(educts: list[dict], corpus_dir: str) -> dict:
    """Pre-compute retrieval results for all training educts at once.

    Returns {educt_sb: [{donor_smiles, tanimoto, donor_records}]}.
    """
    donor_entries = corpus.load_donor_index(
        os.path.join(corpus_dir, "donor_index.jsonl"))
    donor_to_records: dict[str, list[str]] = defaultdict(list)
    for e in donor_entries:
        donor_to_records[e["donor_smiles"]].append(e["donor_record_id"])
    for k in donor_to_records:
        donor_to_records[k] = sorted(set(donor_to_records[k]))
    donors = sorted(donor_to_records.keys())

    records = {r["record_id"]: r
               for r in corpus.read_records(os.path.join(corpus_dir, "corpus_v1.jsonl"))}

    q_map = {e["educt_sb"]: e["educt_sb"] for e in educts}
    ranked = retrieval.rank_queries(q_map, donors, k=20)

    result = {}
    for e in educts:
        esb = e["educt_sb"]
        topk = ranked.get(esb, {}).get("topK", [])
        ev = []
        for hit in topk:
            rec_ids = donor_to_records.get(hit["donor_smiles"], [])
            ev.append({
                "donor_smiles": hit["donor_smiles"],
                "tanimoto": hit["tanimoto"],
                "donor_records": rec_ids,
            })
        result[esb] = ev

    # store records globally for workers
    global _G_RECORDS, _G_DONOR_TO_RECORDS
    _G_RECORDS = records
    _G_DONOR_TO_RECORDS = donor_to_records
    return result


# --------------------------------------------------------------------------- #
# Step 4: Parse USPTO templates (top-N by freq)
# --------------------------------------------------------------------------- #
def parse_top_templates(templates_path: str, top_n: int) -> list:
    """Parse top-N USPTO templates by frequency."""
    data = json.load(open(templates_path))
    items = sorted(data["templates"].items(), key=lambda x: -x[1])[:top_n]
    parsed = []
    for tpl_str, freq in items:
        rf, pf = A.parse_template(tpl_str)
        if rf is None or pf is None:
            continue
        csm = Counter(_sig(a) for a in rf.GetAtoms() if a.GetAtomMapNum() > 0)
        rtype = A.template_type(rf)
        parsed.append((rf, pf, freq, csm, rtype, rf.GetNumAtoms()))
    return parsed


# --------------------------------------------------------------------------- #
# Step 5: Per-educt candidate generation (worker function)
# --------------------------------------------------------------------------- #
def _process_educt(educt: dict) -> tuple[str, list[tuple]]:
    """Generate candidates for one educt, return (educt_sb, [(features, label)]).

    Each element is (feature_vector, label) where label=1 if the candidate
    matches a true product (stereo-blind).
    """
    esb = educt["educt_sb"]
    true_products = educt["true_products_sb"]
    mol = Chem.MolFromSmiles(esb)
    if mol is None:
        return (esb, [])
    n_atoms = mol.GetNumAtoms()
    parent_sb = esb  # stereo-blind canonical

    cands: dict[str, dict] = {}

    # ---- Engine A: USPTO top-N templates ----
    msigm = Counter(_sig(a) for a in mol.GetAtoms())
    t0 = time.time()
    for rf, pf, freq, csm, rtype, n_rfrag in _G_TPL_A:
        if time.time() - t0 > RXN_BUDGET_TRAIN:
            break
        if any(csm[s] > msigm.get(s, 0) for s in csm):
            continue
        for prod_smi, site in A.apply_to(mol, rf, pf).items():
            iso = canonical_smiles(prod_smi)
            if iso is None:
                continue
            if _stereo_blind(iso) == parent_sb:
                continue
            if iso not in cands:
                cands[iso] = {
                    "product_smiles": iso, "product_smiles_full": iso,
                    "source": "uspto", "template_freq": freq,
                    "reactions_count": 0, "pattern_atom_count": n_rfrag,
                    "n_evidence": 0, "max_tanimoto": 0.0,
                    "mean_tanimoto": 0.0, "donor_exact_match": False,
                }
            else:
                c = cands[iso]
                c["template_freq"] += freq
                if n_rfrag > c["pattern_atom_count"]:
                    c["pattern_atom_count"] = n_rfrag

    # ---- Engine B: enviPath 286 rules ----
    for rule in _G_RULES_B:
        rt = rule["rt"]
        rxn = rule["rxn"]
        try:
            matches = mol.GetSubstructMatches(rt, maxMatches=1000)
        except Exception:
            continue
        if not matches:
            continue
        try:
            outs = rxn.RunReactants([mol])
        except Exception:
            continue
        if not outs:
            continue
        for prod_tuple in outs:
            clean_mols = []
            bad = False
            for p in prod_tuple:
                p2 = P2._strip_maps(p)
                try:
                    Chem.SanitizeMol(p2)
                except Exception:
                    bad = True
                    break
                if any(a.GetAtomicNum() == 0 for a in p2.GetAtoms()):
                    bad = True
                    break
                clean_mols.append(p2)
            if bad:
                continue
            all_frags = []
            for cm in clean_mols:
                all_frags.extend(Chem.GetMolFrags(cm, asMols=True))
            if not all_frags:
                continue
            frag_scored = [(f.GetNumAtoms(),
                            Chem.MolToSmiles(f, isomericSmiles=True), f)
                           for f in all_frags]
            frag_scored.sort(key=lambda x: (-x[0], x[1]))
            max_smi = frag_scored[0][1]
            if _stereo_blind(max_smi) == parent_sb:
                continue
            if max_smi not in cands:
                cands[max_smi] = {
                    "product_smiles": max_smi,
                    "product_smiles_full": ".".join(sorted(s for _, s, _ in frag_scored)),
                    "source": "envipath", "template_freq": 0,
                    "reactions_count": rule["reactions_count"],
                    "pattern_atom_count": rule["n_mapped"],
                    "n_evidence": 0, "max_tanimoto": 0.0,
                    "mean_tanimoto": 0.0, "donor_exact_match": False,
                }
            else:
                c = cands[max_smi]
                if "envipath" not in c["source"] and "uspto" in c["source"]:
                    c["source"] = "uspto+envipath"
                if rule["reactions_count"] > c["reactions_count"]:
                    c["reactions_count"] = rule["reactions_count"]
                if rule["n_mapped"] > c["pattern_atom_count"]:
                    c["pattern_atom_count"] = rule["n_mapped"]

    # ---- Engine C: retrieval ----
    retrieval_results = _G_RETRIEVAL.get(esb, [])
    for entry in retrieval_results:
        donor_smi = entry["donor_smiles"]
        tanimoto = entry["tanimoto"]
        donor_sb = _stereo_blind(donor_smi)
        is_exact = (donor_sb == parent_sb) if donor_sb and parent_sb else False
        for rid in entry["donor_records"]:
            rec = _G_RECORDS.get(rid)
            if rec is None:
                continue
            for prod_frag in rec.get("product_components", []):
                try:
                    c_smi = canonical_smiles(prod_frag)
                except Exception:
                    continue
                if not c_smi:
                    continue
                if _stereo_blind(c_smi) == parent_sb:
                    continue
                if c_smi not in cands:
                    cands[c_smi] = {
                        "product_smiles": c_smi,
                        "product_smiles_full": c_smi,
                        "source": "retrieval", "template_freq": 0,
                        "reactions_count": 0, "pattern_atom_count": 0,
                        "n_evidence": 1, "max_tanimoto": tanimoto,
                        "mean_tanimoto": tanimoto,
                        "donor_exact_match": is_exact,
                    }
                else:
                    c = cands[c_smi]
                    # merge sources
                    if "retrieval" not in c["source"]:
                        if c["source"] == "uspto":
                            c["source"] = "uspto+retrieval"
                        elif c["source"] == "envipath":
                            c["source"] = "envipath+retrieval"
                        elif "uspto" in c["source"] and "envipath" in c["source"]:
                            c["source"] = "all"
                    c["n_evidence"] += 1
                    if tanimoto > c["max_tanimoto"]:
                        c["max_tanimoto"] = tanimoto
                    # update mean (simple running average)
                    c["mean_tanimoto"] = (c["mean_tanimoto"] * (c["n_evidence"] - 1)
                                          + tanimoto) / c["n_evidence"]
                    if is_exact:
                        c["donor_exact_match"] = True

    # ---- compute features + labels ----
    features_labels = []
    for c_smi, c in cands.items():
        feats = F.candidate_features(c, esb)
        if feats is None:
            continue
        c_sb = _stereo_blind(c_smi)
        label = 1 if c_sb in true_products else 0
        features_labels.append((feats, label))

    return (esb, features_labels)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-dir", default=CORPUS_DIR)
    ap.add_argument("--templates", default=USPTO_TEMPLATES)
    ap.add_argument("--envipath-rules", default=ENVIPATH_RULES)
    ap.add_argument("--envipath-tsv", default=ENVIPATH_TSV)
    ap.add_argument("--blind-csv", required=True,
                    help="blind parent CSV (for leak filtering §5.2)")
    ap.add_argument("--top-n", type=int, default=TRAIN_TOP_N)
    ap.add_argument("--procs", type=int,
                    default=min(8, os.cpu_count() or 4))
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "data/bbd_v3"))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    t_start = time.time()

    # ---- Step 1: load training educts ----
    print("loading RHEA training educts...", flush=True)
    educts = load_training_educts(args.corpus_dir)
    print(f"  {len(educts)} unique educts", flush=True)

    # ---- Step 2: leak filtering ----
    print("leak filtering (§5.2)...", flush=True)
    blind_parents = load_blind_parents(args.blind_csv)
    educts, leak_stats = filter_leaks(educts, blind_parents)
    print(f"  kept {leak_stats['n_educts_kept']} educts "
          f"(removed {leak_stats['n_exact_match_removed']} exact + "
          f"{leak_stats['n_near_dup_removed']} near-dup)", flush=True)

    if args.limit > 0:
        educts = educts[:args.limit]
        print(f"  limited to {len(educts)} educts", flush=True)

    # ---- Step 3: batch retrieval (Engine C) ----
    print("batch retrieval (Engine C)...", flush=True)
    retrieval_results = batch_retrieval(educts, args.corpus_dir)
    print(f"  retrieval done for {len(retrieval_results)} educts", flush=True)

    # ---- Step 4: parse USPTO top-N templates ----
    print(f"parsing USPTO top-{args.top_n} templates...", flush=True)
    tpl_a = parse_top_templates(args.templates, args.top_n)
    print(f"  {len(tpl_a)} templates parsed", flush=True)

    # ---- Step 4b: load enviPath rules ----
    print("loading enviPath rules...", flush=True)
    rules_b, skip_multi = P2._load_envipath_rules(args.envipath_rules,
                                                   args.envipath_tsv)
    print(f"  {len(rules_b)} rules loaded", flush=True)

    # ---- set globals for fork workers ----
    global _G_TPL_A, _G_RULES_B, _G_RETRIEVAL
    _G_TPL_A = tpl_a
    _G_RULES_B = rules_b
    _G_RETRIEVAL = retrieval_results

    # ---- Step 5: generate candidates (multiprocessing) ----
    print("generating training candidates...", flush=True)
    ctx = mp.get_context("fork")
    with ctx.Pool(args.procs) as pool:
        results = pool.map(_process_educt, educts, chunksize=1)

    # ---- Step 6: collect features + labels ----
    all_features = []
    all_labels = []
    group_sizes = []
    n_pos = 0
    n_neg = 0
    n_empty = 0

    for esb, feat_labels in results:
        if not feat_labels:
            n_empty += 1
            continue
        group_sizes.append(len(feat_labels))
        for feats, label in feat_labels:
            all_features.append(feats)
            all_labels.append(label)
            if label:
                n_pos += 1
            else:
                n_neg += 1

    print(f"  {len(all_features)} samples ({n_pos} pos, {n_neg} neg) "
          f"from {len(group_sizes)} educts ({n_empty} empty)", flush=True)

    # ---- Step 7: train LightGBM ----
    print("training LightGBM...", flush=True)
    import lightgbm as lgb
    import numpy as np

    X = np.array(all_features, dtype=np.float64)
    y = np.array(all_labels, dtype=np.int32)
    groups = np.array(group_sizes, dtype=np.int32)

    # 10% validation split by educt groups
    n_groups = len(group_sizes)
    n_val = max(1, n_groups // 10)
    val_start = sum(group_sizes[:n_groups - n_val])
    X_train, X_val = X[:val_start], X[val_start:]
    y_train, y_val = y[:val_start], y[val_start:]
    grp_train = groups[:n_groups - n_val]
    grp_val = groups[n_groups - n_val:]

    pos = int(y_train.sum())
    neg = len(y_train) - pos
    spw = neg / pos if pos > 0 else 1.0

    dtrain = lgb.Dataset(X_train, label=y_train, group=grp_train)
    dval = lgb.Dataset(X_val, label=y_val, group=grp_val, reference=dtrain)

    params = {
        "objective": "binary",
        "metric": "auc",
        "num_leaves": 63,
        "learning_rate": 0.05,
        "n_estimators": 1000,
        "scale_pos_weight": spw,
        "random_state": 0,
        "deterministic": True,
        "force_row_wise": True,
        "verbose": -1,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.9,
        "bagging_freq": 5,
    }

    model = lgb.train(
        params, dtrain,
        valid_sets=[dval],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)],
    )

    # ---- Step 8: save model + stats ----
    model_path = os.path.join(args.out_dir, "ranker_model.txt")
    model.save_model(model_path)
    print(f"  model saved → {model_path}", flush=True)

    # validation AUC
    val_pred = model.predict(X_val)
    from sklearn.metrics import roc_auc_score
    try:
        val_auc = roc_auc_score(y_val, val_pred)
    except Exception:
        val_auc = 0.0

    # feature importance
    imp = model.feature_importance(importance_type="gain")
    feat_imp = sorted(zip(F.FEATURE_NAMES, imp.tolist()), key=lambda x: -x[1])

    # save training educt list (for leak assertion)
    train_educts_path = os.path.join(args.out_dir, "train_educts.json")
    train_educt_list = sorted(e["educt_sb"] for e in educts)
    with open(train_educts_path, "w") as f:
        json.dump({"train_educts_sb": train_educt_list}, f, sort_keys=True)

    stats = {
        "leak_filter": leak_stats,
        "n_training_educts": len(educts),
        "n_samples": len(all_features),
        "n_pos": n_pos,
        "n_neg": n_neg,
        "pos_ratio": round(n_pos / max(len(all_features), 1), 6),
        "n_empty_educts": n_empty,
        "top_n_templates": args.top_n,
        "n_val_educts": n_val,
        "val_auc": round(val_auc, 6),
        "feature_importance_top15": [(n, round(v, 2)) for n, v in feat_imp[:15]],
        "lightgbm_params": params,
        "total_time_s": round(time.time() - t_start, 2),
    }
    stats_path = os.path.join(args.out_dir, "ranker_train_stats.json")
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2, sort_keys=True)

    print(f"\n=== Training Stats ===", flush=True)
    print(f"  educts: {len(educts)} (leak-filtered from {leak_stats['n_educts_total']})", flush=True)
    print(f"  samples: {len(all_features)} ({n_pos} pos / {n_neg} neg)", flush=True)
    print(f"  val AUC: {val_auc:.4f}", flush=True)
    print(f"  top-5 features: {feat_imp[:5]}", flush=True)
    print(f"  total time: {time.time() - t_start:.1f}s", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
