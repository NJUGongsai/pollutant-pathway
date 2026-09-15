#!/usr/bin/env python3
"""BBD v5 ranker training: RHEA + EAWAG mixed, per-source rankers + selector.

Task §4.1 (component A).  Retrains the 3 per-source LightGBM rankers
(uspto/envipath/retrieval) + source selector on the mixed RHEA+EAWAG
candidate set with one new feature (``is_eawag_domain``, 28-dim total).
Hyperparameters and hard-negative mining are UNCHANGED from v3.1 (task §5.3
— only ``scale_pos_weight`` auto-recomputes). The envipath ranker now trains
on RHEA+EAWAG envipath candidates including the EAWAG-rule candidates (folded
with source="envipath" by build_bbd_train_v2 / eawag_rules_engine).

Inputs (read-only):
  RHEA cache:  data/bbd_v31/train_candidates.jsonl  (1.88M rows, is_eawag_domain=0)
  EAWAG cache: data/bbd_v5/eawag_candidates.jsonl   (is_eawag_domain=1)

Validation split is STRATIFIED by domain (task §4.1): last-10% RHEA educts +
last-10% EAWAG educts, so both domains are represented in validation.

Outputs: data/bbd_v5/rankers/{uspto,envipath,retrieval}_ranker.txt,
         source_selector.txt, v5_train_stats.json, hard_neg_stats_v5.json.

Answer-key isolation: this file NEVER reads the answer key.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from rdkit import Chem, RDLogger  # noqa: E402
RDLogger.DisableLog("rdApp.*")

import bbd_v5_features as F5  # noqa: E402 — 28-dim feature wrapper
import bbd_v3_features as F  # noqa: E402 — SELECTOR_FEATURE_NAMES
import train_bbd_v3_ranker as T3  # noqa: E402 — load_blind_parents, _stereo_blind
import io_retry as IOR  # noqa: E402 — robust I/O for flaky external drive
import bbd_data_root as D  # noqa: E402 — BBD_DATA_ROOT resolver (HF-migrated assets)

import lightgbm as lgb

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
OUT_DIR = os.path.join(ROOT, "data/bbd_v5")
RHEA_CACHE = D.resolve("data/bbd_v31/train_candidates.jsonl")
EAWAG_CACHE = D.resolve("data/bbd_v5/eawag_candidates.jsonl")
BLIND_CSV = os.path.join(ROOT,
    "bbd_known_pathway_full_route_v0_3_candidate_v3_1_strict_blind_fix_20260821/blind/"
    "BBD_KNOWN_PATHWAY_FULL_ROUTE_V0_3_V3_1_BLIND_PARENT_INPUTS_FOR_PREDICTION_STRICT.csv")
TRAIN_EDUCTS_V5 = os.path.join(ROOT, "data/bbd_v5/train_educts_v5.json")

SOURCES = ("uspto", "envipath", "retrieval")
HARD_NEG_TOP_K = 20
MARGIN_NEG_CAP = 50
EASY_NEG_KEEP = 0.1


def load_cache(path: str, is_eawag_domain: int) -> dict[str, list[dict]]:
    """Read a candidate cache; return {educt_sb: [candidate_dict, ...]}.

    Tags every candidate with is_eawag_domain (0 for RHEA, 1 for EAWAG).
    The cache rows already carry is_eawag_domain for EAWAG (set by
    build_bbd_train_v2); RHEA rows get it here.
    """
    out: dict[str, list[dict]] = defaultdict(list)
    for line in IOR.robust_readlines(path):
        if not line.strip():
            continue
        c = json.loads(line)
        c["is_eawag_domain"] = is_eawag_domain
        esb = c.get("educt_sb", "")
        if esb:
            out[esb].append(c)
    return dict(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rhea-cache", default=RHEA_CACHE)
    ap.add_argument("--eawag-cache", default=EAWAG_CACHE)
    ap.add_argument("--blind-csv", default=BLIND_CSV)
    ap.add_argument("--train-educts", default=TRAIN_EDUCTS_V5)
    ap.add_argument("--out-dir", default=OUT_DIR)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(os.path.join(args.out_dir, "rankers"), exist_ok=True)
    t_start = time.time()

    # ---- RED LINE 1: leak assertion (combined train educts ∩ blind == 0) ----
    blind_parents = T3.load_blind_parents(args.blind_csv)
    te = json.load(IOR.robust_open(args.train_educts))
    combined_educts = set(te["train_educts_sb"])
    overlap = combined_educts & blind_parents
    assert not overlap, f"LEAK: {len(overlap)} combined train educts are blind parents"
    print(f"leak assertion passed: {len(combined_educts)} combined train educts, "
          f"0 overlap with {len(blind_parents)} blind parents", flush=True)

    # ---- load caches ----
    print("loading RHEA cache...", flush=True)
    rhea_cands = load_cache(args.rhea_cache, 0)
    print(f"  {len(rhea_cands)} RHEA educts, "
          f"{sum(len(v) for v in rhea_cands.values())} candidates", flush=True)
    print("loading EAWAG cache...", flush=True)
    eawag_cands = load_cache(args.eawag_cache, 1)
    print(f"  {len(eawag_cands)} EAWAG educts, "
          f"{sum(len(v) for v in eawag_cands.values())} candidates", flush=True)

    rhea_educt_sbs = sorted(rhea_cands.keys())
    eawag_educt_sbs = sorted(eawag_cands.keys())
    educt_domain = {esb: 0 for esb in rhea_educt_sbs}
    educt_domain.update({esb: 1 for esb in eawag_educt_sbs})

    # ---- merge ----
    educt_full_cands: dict[str, list[dict]] = {}
    educt_full_cands.update(rhea_cands)
    for esb, cs in eawag_cands.items():
        educt_full_cands.setdefault(esb, []).extend(cs)

    if args.limit > 0:
        kept = sorted(educt_full_cands.keys())[:args.limit]
        educt_full_cands = {esb: educt_full_cands[esb] for esb in kept}
        print(f"  limited to {len(educt_full_cands)} educts", flush=True)

    # ---- compute v5 features (28-dim) on FULL candidate set ----
    print("computing v5 (28-dim) features...", flush=True)
    for esb in sorted(educt_full_cands.keys()):
        F5.compute_v5_case_features(educt_full_cands[esb], esb,
                                    educt_domain[esb])

    total_cands = sum(len(v) for v in educt_full_cands.values())
    total_pos = sum(1 for cs in educt_full_cands.values()
                     for c in cs if c.get("label"))
    print(f"  {len(educt_full_cands)} educts, {total_cands} candidates "
          f"({total_pos} pos)", flush=True)

    # ---- hard negative mining (per educt × source) — identical to v3.1 ----
    print("hard negative mining...", flush=True)
    rng = np.random.RandomState(0)
    educt_source_cands: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for esb, cands in educt_full_cands.items():
        for c in cands:
            src = c.get("source", "")
            for sk in SOURCES:
                belongs = sk in src or (sk in ("uspto", "envipath") and src == "both")
                if belongs:
                    educt_source_cands[(esb, sk)].append(c)

    mined_samples = []
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

    # ---- prepare per-source training data ----
    print("preparing per-source training data...", flush=True)
    source_data: dict[str, list[tuple]] = {sk: [] for sk in SOURCES}
    selector_data = []
    for esb, sk, c in mined_samples:
        feats = c.get("_v31_features", {}).get(sk)
        if feats is None:
            continue
        source_data[sk].append((feats, c.get("label", 0), esb))

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
        label_class = 3
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

    # ---- stratified validation split (RHEA last-10% + EAWAG last-10%) ----
    n_rhea_val = max(1, len(rhea_educt_sbs) // 10)
    n_eawag_val = max(1, len(eawag_educt_sbs) // 10)
    val_educts = set(rhea_educt_sbs[-n_rhea_val:]) | set(eawag_educt_sbs[-n_eawag_val:])
    print(f"  val: {len(val_educts)} educts ({n_rhea_val} RHEA + "
          f"{n_eawag_val} EAWAG)", flush=True)

    def split(data):
        train, val = [], []
        for item in data:
            *rest, esb = item
            (val if esb in val_educts else train).append(item)
        return train, val

    # ---- train per-source rankers ----
    print("training per-source rankers...", flush=True)
    model_stats = {}
    ranker_dir = os.path.join(args.out_dir, "rankers")
    for sk in SOURCES:
        data = source_data[sk]
        train_data, val_data = split(data)
        if len(train_data) < 100 or sum(l for _, l, _ in train_data) < 5:
            print(f"  {sk}: insufficient data ({len(train_data)} train), skipping",
                  flush=True)
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
        model.save_model(os.path.join(ranker_dir, f"{sk}_ranker.txt"))
        val_auc = 0.0
        if X_val is not None and len(y_val) > 0:
            from sklearn.metrics import roc_auc_score
            try:
                val_auc = roc_auc_score(y_val, model.predict(X_val))
            except Exception:
                val_auc = 0.0
        imp = model.feature_importance(importance_type="gain")
        feat_imp = sorted(zip(F5.FEATURE_NAMES_V5, imp.tolist()), key=lambda x: -x[1])
        model_stats[sk] = {
            "status": "trained" if not envipath_small else "trained_small",
            "n_train": len(train_data), "n_val": len(val_data),
            "n_pos_train": pos, "val_auc": round(val_auc, 6),
            "scale_pos_weight": round(spw, 4),
            "feature_importance_top8": [(n, round(v, 2)) for n, v in feat_imp[:8]],
            "is_eawag_domain_importance": dict(
                zip(F5.FEATURE_NAMES_V5, imp.tolist())).get("is_eawag_domain", 0.0),
            "best_iter": model.best_iteration,
        }
        print(f"  {sk}: {len(train_data)} train, AUC={val_auc:.4f}, "
              f"best_iter={model.best_iteration}", flush=True)

    # ---- train source selector ----
    print("training source selector...", flush=True)
    sel_train, sel_val = split(selector_data)
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
    sel_model = lgb.train(sel_params, dsel_train, valid_sets=sel_valid,
                          callbacks=sel_cbs)
    sel_model.save_model(os.path.join(ranker_dir, "source_selector.txt"))
    sel_val_hit1 = 0.0
    if X_sel_val is not None and len(y_sel_val) > 0:
        sel_probs = sel_model.predict(X_sel_val)
        pred_classes = np.argmax(sel_probs, axis=1)
        sel_val_hit1 = float((pred_classes == y_sel_val).mean())
    model_stats["selector"] = {
        "n_train": len(sel_train), "n_val": len(sel_val),
        "val_hit1_proxy": round(sel_val_hit1, 6),
        "best_iter": sel_model.best_iteration,
    }
    print(f"  selector: {len(sel_train)} train, val_hit1_proxy={sel_val_hit1:.4f}",
          flush=True)

    # ---- save stats ----
    stats = {
        "n_rhea_educts": len(rhea_educt_sbs),
        "n_eawag_educts": len(eawag_educt_sbs),
        "n_training_educts": len(educt_full_cands),
        "total_candidates": total_cands,
        "total_pos": total_pos,
        "hard_neg_mining": mine_stats,
        "val_educts": {"rhea": n_rhea_val, "eawag": n_eawag_val,
                       "total": len(val_educts)},
        "feature_dim": F5.N_FEATURES_V5,
        "feature_names": F5.FEATURE_NAMES_V5,
        "model_stats": model_stats,
        "total_time_s": round(time.time() - t_start, 2),
    }
    IOR.robust_json_dump(os.path.join(args.out_dir, "v5_train_stats.json"), stats)
    IOR.robust_json_dump(os.path.join(args.out_dir, "hard_neg_stats_v5.json"),
                         mine_stats)

    print(f"\n=== v5 Training Complete ({time.time()-t_start:.0f}s) ===", flush=True)
    print(f"  educts: {len(educt_full_cands)} "
          f"({len(rhea_educt_sbs)} RHEA + {len(eawag_educt_sbs)} EAWAG)", flush=True)
    print(f"  candidates: {total_cands} ({total_pos} pos)", flush=True)
    print(f"  mined: {mine_stats}", flush=True)
    for sk in SOURCES:
        s = model_stats.get(sk, {})
        print(f"  {sk}_ranker: {s.get('status','?')} AUC={s.get('val_auc','?')}",
              flush=True)
    print(f"  selector: val_hit1_proxy={sel_val_hit1:.4f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
