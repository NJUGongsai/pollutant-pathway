#!/usr/bin/env python3
"""BBD v3.1 training: hard negative mining + per-source rankers.

Two-stage training (task §4.4):

  Stage 1 — cache: re-run v3 candidate generation, score with v3 model,
            dump ``train_candidates.jsonl`` (per-candidate raw fields + v3 proba + label).

  Hard neg mining: per (educt × source) group:
    Rule 1: top-K=20 highest v3-proba negatives
    Rule 2: "margin negatives" (v3-proba > any true product proba, cap 50/educt)
    Keep all positives + 10% easy negatives (seed=0)

  Stage 2 — train 4 models:
    3 per-source LightGBM rankers (uspto/envipath/retrieval)
    1 source-selector (4-class multiclass, group-level features)

  Model selection: only RHEA validation set (10% educt split, same for all 4).
  93-case eval runs ONCE after models are fixed (§4.5).

Answer-key isolation: this file NEVER reads the answer key.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from typing import Any

import multiprocessing as mp
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "src"))

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem
RDLogger.DisableLog("rdApp.*")

import gnn_phase6_apply as A  # noqa: E402
import bbd_v3_features as F  # noqa: E402
import train_bbd_v3_ranker as T3  # noqa: E402 — reuse pipeline
import predict_bbd_products_v2 as P2  # noqa: E402 — engine helpers
import bbd_v31_ranker as R31  # noqa: E402

import lightgbm as lgb

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
OUT_DIR = os.path.join(ROOT, "data/bbd_v31")
V3_MODEL = os.path.join(ROOT, "data/bbd_v3/ranker_model.txt")

SOURCES = ("uspto", "envipath", "retrieval")
HARD_NEG_TOP_K = 20
MARGIN_NEG_CAP = 50
EASY_NEG_KEEP = 0.1

# Globals for fork workers
_G_V3_MODEL = None  # LightGBM Booster, loaded per-worker via initializer (NOT fork-inherited)


def _init_worker(model_path: str):
    """Pool initializer: load the v3 model fresh in each worker.

    LightGBM Booster objects are NOT fork-safe (internal C++ threads deadlock).
    This initializer loads the model after fork, avoiding inheritance issues.
    """
    global _G_V3_MODEL
    _G_V3_MODEL = lgb.Booster(model_file=model_path)


# --------------------------------------------------------------------------- #
# Stage 1: candidate generation (reuses v3 pipeline, returns raw dicts)
# --------------------------------------------------------------------------- #
def _process_educt_raw(educt: dict) -> tuple[str, list[dict]]:
    """Like T3._process_educt but returns raw candidate dicts (not features).

    Returns (educt_sb, [candidate_dict, ...]).
    Each dict has all fields needed for v3.1 features + label.
    """
    esb = educt["educt_sb"]
    true_products = educt["true_products_sb"]
    mol = Chem.MolFromSmiles(esb)
    if mol is None:
        return (esb, [])

    # reuse v3's _process_educt for candidate generation, but we need raw dicts.
    # Since T3._process_educt doesn't return dicts, we replicate its logic here.
    n_atoms = mol.GetNumAtoms()
    parent_sb = esb
    cands: dict[str, dict] = {}

    # ---- Engine A: USPTO top-N templates ----
    msigm = Counter(T3._sig(a) for a in mol.GetAtoms())
    t0 = time.time()
    for rf, pf, freq, csm, rtype, n_rfrag in T3._G_TPL_A:
        if time.time() - t0 > T3.RXN_BUDGET_TRAIN:
            break
        if any(csm[s] > msigm.get(s, 0) for s in csm):
            continue
        for prod_smi, site in A.apply_to(mol, rf, pf).items():
            iso = T3.canonical_smiles(prod_smi) if hasattr(T3, 'canonical_smiles') else _canon_iso(prod_smi)
            if iso is None:
                continue
            if T3._stereo_blind(iso) == parent_sb:
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
    for rule in T3._G_RULES_B:
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
            if T3._stereo_blind(max_smi) == parent_sb:
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
    for entry in T3._G_RETRIEVAL.get(esb, []):
        donor_smi = entry["donor_smiles"]
        tanimoto = entry["tanimoto"]
        donor_sb = T3._stereo_blind(donor_smi)
        is_exact = (donor_sb == parent_sb) if donor_sb and parent_sb else False
        for rid in entry["donor_records"]:
            rec = T3._G_RECORDS.get(rid)
            if rec is None:
                continue
            for prod_frag in rec.get("product_components", []):
                try:
                    c_smi = _canon_iso(prod_frag)
                except Exception:
                    continue
                if not c_smi:
                    continue
                if T3._stereo_blind(c_smi) == parent_sb:
                    continue
                if c_smi not in cands:
                    cands[c_smi] = {
                        "product_smiles": c_smi, "product_smiles_full": c_smi,
                        "source": "retrieval", "template_freq": 0,
                        "reactions_count": 0, "pattern_atom_count": 0,
                        "n_evidence": 1, "max_tanimoto": tanimoto,
                        "mean_tanimoto": tanimoto,
                        "donor_exact_match": is_exact,
                    }
                else:
                    c = cands[c_smi]
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
                    c["mean_tanimoto"] = ((c["mean_tanimoto"] * (c["n_evidence"] - 1)
                                           + tanimoto) / c["n_evidence"])
                    if is_exact:
                        c["donor_exact_match"] = True

    # ---- add labels + v3 proba (batched per educt for speed) ----
    import numpy as np
    result = []
    all_feats = []
    all_keys = []
    for c_smi, c in cands.items():
        c_sb = T3._stereo_blind(c_smi)
        c["label"] = 1 if c_sb in true_products else 0
        c["educt_sb"] = esb
        feats = F.candidate_features(c, esb)
        if feats is not None:
            all_feats.append(feats)
            all_keys.append(c_smi)
        else:
            c["v3_proba"] = 0.0
        result.append(c)

    # batch predict (one call per educt, not per candidate)
    if _G_V3_MODEL is not None and all_feats:
        probas = _G_V3_MODEL.predict(np.array(all_feats, dtype=np.float64))
        for i, c_smi in enumerate(all_keys):
            cands[c_smi]["v3_proba"] = float(probas[i])
    else:
        for c_smi in all_keys:
            cands[c_smi]["v3_proba"] = 0.0

    return (esb, result)


def _canon_iso(smi: str) -> str | None:
    from ra.chem import canonical_smiles
    try:
        return canonical_smiles(smi)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-dir", default=T3.CORPUS_DIR)
    ap.add_argument("--templates", default=T3.USPTO_TEMPLATES)
    ap.add_argument("--envipath-rules", default=T3.ENVIPATH_RULES)
    ap.add_argument("--envipath-tsv", default=T3.ENVIPATH_TSV)
    ap.add_argument("--blind-csv", required=True, help="blind parent CSV (leak filter)")
    ap.add_argument("--v3-model", default=V3_MODEL)
    ap.add_argument("--top-n", type=int, default=T3.TRAIN_TOP_N)
    ap.add_argument("--procs", type=int, default=min(8, os.cpu_count() or 4))
    ap.add_argument("--out-dir", default=OUT_DIR)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    t_start = time.time()

    # ---- Step 1: load + filter educts (same as v3) ----
    print("loading training educts...", flush=True)
    educts = T3.load_training_educts(args.corpus_dir)
    blind_parents = T3.load_blind_parents(args.blind_csv)
    educts, leak_stats = T3.filter_leaks(educts, blind_parents)

    # assert consistency with v3 train_educts.json
    v3_te_path = os.path.join(ROOT, "data/bbd_v3/train_educts.json")
    if os.path.exists(v3_te_path):
        v3_te = set(json.load(open(v3_te_path))["train_educts_sb"])
        cur_te = {e["educt_sb"] for e in educts}
        assert v3_te == cur_te, "leak filter inconsistent with v3!"
        print(f"  leak filter matches v3: {len(cur_te)} educts", flush=True)

    if args.limit > 0:
        educts = educts[:args.limit]
        print(f"  limited to {len(educts)}", flush=True)

    # ---- Step 2: setup globals (same as v3) ----
    print("batch retrieval...", flush=True)
    retrieval_results = T3.batch_retrieval(educts, args.corpus_dir)
    print(f"  done for {len(retrieval_results)} educts", flush=True)

    print(f"parsing USPTO top-{args.top_n} templates...", flush=True)
    tpl_a = T3.parse_top_templates(args.templates, args.top_n)
    rules_b, _ = P2._load_envipath_rules(args.envipath_rules, args.envipath_tsv)

    # set globals for fork workers
    T3._G_TPL_A = tpl_a
    T3._G_RULES_B = rules_b
    T3._G_RETRIEVAL = retrieval_results
    # NOTE: _G_V3_MODEL is NOT set here — LightGBM Booster is not fork-safe.
    # It's loaded fresh in each worker via the Pool initializer.

    # ---- Step 3: generate candidates (multiprocessing) ----
    print("generating + caching candidates...", flush=True)
    ctx = mp.get_context("fork")
    with ctx.Pool(args.procs, initializer=_init_worker,
                  initargs=(args.v3_model,)) as pool:
        results = pool.map(_process_educt_raw, educts, chunksize=10)

    # ---- Step 4: dump cache (v3 proba already computed in workers) ----
    print("dumping cache...", flush=True)

    cache_path = os.path.join(args.out_dir, "train_candidates.jsonl")
    with open(cache_path, "w") as f:
        for esb, cands in results:
            for c in cands:
                f.write(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n")

    total_cands = sum(len(cs) for _, cs in results)
    total_pos = sum(1 for _, cs in results for c in cs if c.get("label"))
    print(f"  cached {total_cands} candidates ({total_pos} pos) in {time.time()-t_start:.0f}s",
          flush=True)

    # ---- Step 5: compute v3.1 features on FULL candidate set (before mining) ----
    print("computing v3.1 features on full candidate set...", flush=True)
    educt_full_cands: dict[str, list[dict]] = {esb: cs for esb, cs in results}
    for esb, cands in educt_full_cands.items():
        F.compute_v31_case_features(cands, esb)

    # ---- Step 6: hard negative mining (per educt × source) ----
    print("hard negative mining...", flush=True)
    rng = np.random.RandomState(0)

    # group by (educt, source) — a multi-source candidate appears in multiple groups
    educt_source_cands: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for esb, cands in results:
        for c in cands:
            src = c.get("source", "")
            for sk in SOURCES:
                belongs = sk in src or (sk in ("uspto", "envipath") and src == "both")
                if belongs:
                    educt_source_cands[(esb, sk)].append(c)

    mined_samples = []  # list of (educt_sb, source_key, candidate_dict)
    mine_stats = {"pos": 0, "hard_topk": 0, "margin": 0, "easy_kept": 0}

    for (esb, sk), group_cands in sorted(educt_source_cands.items()):
        positives = [c for c in group_cands if c.get("label")]
        negatives = [c for c in group_cands if not c.get("label")]

        negatives.sort(key=lambda c: -c.get("v3_proba", 0.0))

        hard_topk = negatives[:HARD_NEG_TOP_K]
        max_pos_proba = max((c.get("v3_proba", 0.0) for c in positives), default=0.0)
        margin_negs = [c for c in negatives if c.get("v3_proba", 0.0) > max_pos_proba]
        margin_negs = margin_negs[:MARGIN_NEG_CAP]

        remaining_negs = [c for c in negatives
                          if c not in hard_topk and c not in margin_negs]
        n_easy_keep = int(len(remaining_negs) * EASY_NEG_KEEP)
        if n_easy_keep > 0:
            easy_idx = rng.choice(len(remaining_negs), n_easy_keep, replace=False)
            easy_kept = [remaining_negs[i] for i in sorted(easy_idx)]
        else:
            easy_kept = []

        kept = positives + hard_topk + margin_negs + easy_kept
        for c in kept:
            mined_samples.append((esb, sk, c))

        mine_stats["pos"] += len(positives)
        mine_stats["hard_topk"] += len(hard_topk)
        mine_stats["margin"] += len(margin_negs)
        mine_stats["easy_kept"] += len(easy_kept)

    print(f"  mined: {mine_stats}", flush=True)

    # ---- Step 7: prepare per-source training data ----
    print("preparing per-source training data...", flush=True)
    source_data: dict[str, list[tuple]] = {sk: [] for sk in SOURCES}
    selector_data = []  # (features, label_class, educt)

    for esb, sk, c in mined_samples:
        feats = c.get("_v31_features", {}).get(sk)
        if feats is None:
            continue
        label = c.get("label", 0)
        source_data[sk].append((feats, label, esb))

    # selector data: per educt, which source's top-1 (by v3_proba) is the true product
    for esb, cands in sorted(educt_full_cands.items()):
        source_top1 = {}
        for sk in SOURCES:
            sk_cands = [c for c in cands if sk in c.get("source", "")
                        or (sk in ("uspto", "envipath") and c.get("source") == "both")]
            if sk_cands:
                top = max(sk_cands, key=lambda c: c.get("v3_proba", 0.0))
                source_top1[sk] = top
            else:
                source_top1[sk] = None

        label_class = 3  # none
        for i, sk in enumerate(SOURCES):
            top = source_top1.get(sk)
            if top and top.get("label"):
                label_class = i
                break

        sel_feats = cands[0].get("_v31_selector_features")
        if sel_feats is not None:
            selector_data.append((sel_feats, label_class, esb))

    for sk in SOURCES:
        print(f"  {sk}: {len(source_data[sk])} samples "
              f"({sum(1 for _,l,_ in source_data[sk] if l)} pos)", flush=True)
    print(f"  selector: {len(selector_data)} groups", flush=True)

    # ---- Step 8: split validation (same split for all 4 models) ----
    all_educts = sorted(educt_full_cands.keys())
    n_val = max(1, len(all_educts) // 10)
    val_educts = set(all_educts[-n_val:])

    def split(data, is_group=False):
        train, val = [], []
        for item in data:
            *rest, esb = item
            (val if esb in val_educts else train).append(item)
        return train, val

    # ---- Step 9: train per-source rankers ----
    print("training per-source rankers...", flush=True)
    model_stats = {}

    for sk in SOURCES:
        data = source_data[sk]
        train_data, val_data = split(data)

        if len(train_data) < 100 or sum(l for _, l, _ in train_data) < 5:
            print(f"  {sk}: insufficient data ({len(train_data)} train), skipping", flush=True)
            model_stats[sk] = {"status": "skipped", "n_train": len(train_data)}
            continue

        envipath_small = (sk == "envipath" and len(train_data) < 5000)

        X_train = np.array([d[0] for d in train_data], dtype=np.float64)
        y_train = np.array([d[1] for d in train_data], dtype=np.int32)
        X_val = np.array([d[0] for d in val_data], dtype=np.float64) if val_data else None
        y_val = np.array([d[1] for d in val_data], dtype=np.int32) if val_data else None

        pos = int(y_train.sum())
        neg = len(y_train) - pos
        spw = neg / pos if pos > 0 else 1.0

        params = {
            "objective": "binary", "metric": "auc",
            "num_leaves": 31 if envipath_small else 63,
            "min_data_in_leaf": 50 if envipath_small else 20,
            "learning_rate": 0.05, "n_estimators": 1000,
            "scale_pos_weight": spw, "random_state": 0,
            "deterministic": True, "force_row_wise": True,
            "verbose": -1, "feature_fraction": 0.9,
            "bagging_fraction": 0.9, "bagging_freq": 5,
        }

        dtrain = lgb.Dataset(X_train, label=y_train)
        cbs = [lgb.log_evaluation(100)]
        valid_sets = []
        if X_val is not None and len(y_val) > 0:
            dval = lgb.Dataset(X_val, label=y_val, reference=dtrain)
            valid_sets = [dval]
            cbs.append(lgb.early_stopping(50))

        model = lgb.train(params, dtrain, valid_sets=valid_sets, callbacks=cbs)

        model_path = os.path.join(args.out_dir, f"{sk}_ranker.txt")
        model.save_model(model_path)

        val_auc = 0.0
        if X_val is not None and len(y_val) > 0:
            from sklearn.metrics import roc_auc_score
            try:
                val_auc = roc_auc_score(y_val, model.predict(X_val))
            except Exception:
                val_auc = 0.0

        imp = model.feature_importance(importance_type="gain")
        feat_imp = sorted(zip(F.FEATURE_NAMES_V31, imp.tolist()), key=lambda x: -x[1])

        model_stats[sk] = {
            "status": "trained" if not envipath_small else "trained_small",
            "n_train": len(train_data), "n_val": len(val_data),
            "n_pos_train": pos, "val_auc": round(val_auc, 6),
            "feature_importance_top5": [(n, round(v, 2)) for n, v in feat_imp[:5]],
        }
        print(f"  {sk}: {len(train_data)} train, AUC={val_auc:.4f}, "
              f"best_iter={model.best_iteration}", flush=True)

    # ---- Step 10: train source selector ----
    print("training source selector...", flush=True)
    sel_train, sel_val = split(selector_data, is_group=True)

    X_sel_train = np.array([d[0] for d in sel_train], dtype=np.float64)
    y_sel_train = np.array([d[1] for d in sel_train], dtype=np.int32)
    X_sel_val = np.array([d[0] for d in sel_val], dtype=np.float64) if sel_val else None
    y_sel_val = np.array([d[1] for d in sel_val], dtype=np.int32) if sel_val else None

    sel_params = {
        "objective": "multiclass", "num_class": 4,
        "metric": "multi_logloss",
        "num_leaves": 31, "learning_rate": 0.05, "n_estimators": 500,
        "random_state": 0, "deterministic": True, "force_row_wise": True,
        "verbose": -1, "feature_fraction": 0.9,
        "bagging_fraction": 0.9, "bagging_freq": 5,
    }

    dsel_train = lgb.Dataset(X_sel_train, label=y_sel_train)
    sel_cbs = [lgb.log_evaluation(100)]
    sel_valid = []
    if X_sel_val is not None and len(y_sel_val) > 0:
        dsel_val = lgb.Dataset(X_sel_val, label=y_sel_val, reference=dsel_train)
        sel_valid = [dsel_val]
        sel_cbs.append(lgb.early_stopping(50))

    sel_model = lgb.train(sel_params, dsel_train, valid_sets=sel_valid, callbacks=sel_cbs)
    sel_model.save_model(os.path.join(args.out_dir, "source_selector.txt"))

    # selector validation Hit@1 proxy
    sel_val_hit1 = 0.0
    if X_sel_val is not None and len(y_sel_val) > 0:
        sel_probs = sel_model.predict(X_sel_val)
        # proxy: if argmax predicts the correct source, count as hit
        pred_classes = np.argmax(sel_probs, axis=1)
        sel_val_hit1 = float((pred_classes == y_sel_val).mean())

    sel_imp = sel_model.feature_importance(importance_type="gain")
    sel_feat_imp = sorted(zip(F.SELECTOR_FEATURE_NAMES, sel_imp.tolist()), key=lambda x: -x[1])

    model_stats["selector"] = {
        "n_train": len(sel_train), "n_val": len(sel_val),
        "val_hit1_proxy": round(sel_val_hit1, 6),
        "feature_importance_top5": [(n, round(v, 2)) for n, v in sel_feat_imp[:5]],
        "best_iter": sel_model.best_iteration,
    }
    print(f"  selector: {len(sel_train)} train, val_hit1_proxy={sel_val_hit1:.4f}",
          flush=True)

    # ---- Step 11: save stats ----
    stats = {
        "leak_filter": leak_stats,
        "n_training_educts": len(educts),
        "total_candidates_cached": total_cands,
        "total_pos_cached": total_pos,
        "hard_neg_mining": mine_stats,
        "val_educts": n_val,
        "model_stats": model_stats,
        "total_time_s": round(time.time() - t_start, 2),
    }
    stats_path = os.path.join(args.out_dir, "v31_train_stats.json")
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2, sort_keys=True)

    # save hard neg stats
    with open(os.path.join(args.out_dir, "hard_neg_stats.json"), "w") as f:
        json.dump(mine_stats, f, indent=2, sort_keys=True)

    print(f"\n=== v3.1 Training Complete ({time.time()-t_start:.0f}s) ===", flush=True)
    print(f"  educts: {len(educts)}, cached: {total_cands} ({total_pos} pos)", flush=True)
    print(f"  mined: {mine_stats}", flush=True)
    for sk in SOURCES:
        s = model_stats.get(sk, {})
        print(f"  {sk}_ranker: {s.get('status','?')} "
              f"AUC={s.get('val_auc','?')}", flush=True)
    print(f"  selector: val_hit1_proxy={sel_val_hit1:.4f}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
