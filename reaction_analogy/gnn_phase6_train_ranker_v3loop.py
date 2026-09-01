#!/usr/bin/env python3
"""§v3loop 排序变体：gnn_phase6_train_ranker.py 的超集（实验 B 域特征）。

与原脚本的唯一差异（保证 v1 口径可复现）:
  1. 新增 --is-metal 开关: cand_row 追加 1 列 is_metal（候选 type 含金属元素 → 1）。
     金属清单 = 任务书 §4.2 的 21 种（Pd,Ni,Cu,Zn,Fe,Mg,Li,Na,K,Sn,Ti,Co,Mn,Al,Ag,
     Hg,Ca,B,Si,Se），写死在 METAL_ELEMS。不加该开关时特征向量与原脚本逐位一致。
  2. 输出 json 追加 feature_importance（gain）+ is_metal_pos_rate（特征统计），
     便于报告引用; 不影响训练/评估本身。

评测口径、超参、下采样、LightGBM 确定性参数全部沿用原脚本（不改动）。
"""
import argparse
import glob as _glob
import json
import math
import os
import random
import sys
from collections import Counter
from multiprocessing import Pool

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

# 任务书 §4.2 的金属/域代理元素清单（21 种，含 B/Si/Se 等类金属——按任务书原文）
METAL_ELEMS = {"Pd", "Ni", "Cu", "Zn", "Fe", "Mg", "Li", "Na", "K", "Sn",
               "Ti", "Co", "Mn", "Al", "Ag", "Hg", "Ca", "B", "Si", "Se"}


def iter_files(path):
    return sorted(_glob.glob(path)) if "*" in path else [path]


def load_cases(f):
    d = json.load(open(f))
    return d.get("dump") if isinstance(d, dict) else (d or [])


MPNN_OFF = False   # --mpnn-off 时置 True，cand_row 的 mpnn 特征置 0（对照实验用）
IS_METAL = False   # --is-metal 时置 True，cand_row 追加 is_metal 列（实验 B）


def is_metal_of(c):
    """候选 type（center 元素 tuple）含金属元素 → 1。"""
    return 1 if any(e in METAL_ELEMS for e in (c.get("type") or [])) else 0


def cand_row(c, ncand, type_map, n_types):
    """单候选 -> 特征行（全部预计算，无 RDKit）。"""
    f = c["f"]
    sf = c.get("sf") or []
    tidx = type_map.get(tuple(c.get("type", [])), n_types)
    sim, atomsize, conserv = c.get("v", [0.0, 0.0, 0])
    r = c.get("r", 0)
    fsum = c.get("fs") or (f or 1)
    nc = ncand or 1
    mpnn = 0.0 if MPNN_OFF else c.get("mpnn", 0.0)
    row = ([f, f / fsum, math.log1p(f), r, r / nc, nc, sim, atomsize, conserv, mpnn]
           + sf + [tidx])
    if IS_METAL:
        row.append(is_metal_of(c))
    return row


# ---- worker（顶层函数，可 pickle）----

def _w_stats(f):
    """pass1 文件统计：type 计数 + 正负数 + is_metal 统计。"""
    tc = Counter(); npos = nneg = ncase = 0
    n_metal = n_metal_pos = 0
    for case in load_cases(f):
        ncase += 1
        for c in case.get("cands") or []:
            tc[tuple(c.get("type", []))] += 1
            if is_metal_of(c):
                n_metal += 1
                if c.get("l") == 1:
                    n_metal_pos += 1
            if c.get("l") == 1:
                npos += 1
            else:
                nneg += 1
    return tc, npos, nneg, ncase, n_metal, n_metal_pos


def _w_rows(a):
    """pass2 文件采样：返回 (rows, labels)。
    flags 经任务元组传递（而非模块全局）——fork 平台（HPC Linux）与 spawn 平台
    （macOS）行为一致; 数值与原脚本的全局变量方案逐位相同。"""
    f, type_map, n_types, neg_prob, seed, mpnn_off, is_metal = a
    global MPNN_OFF, IS_METAL
    MPNN_OFF, IS_METAL = mpnn_off, is_metal
    rng = random.Random(seed)
    X, y = [], []
    for case in load_cases(f):
        ncand = case.get("ncand") or len(case.get("cands") or [])
        for c in case.get("cands") or []:
            if c.get("l") == 1 or rng.random() < neg_prob:
                X.append(cand_row(c, ncand, type_map, n_types))
                y.append(c.get("l", 0))
    return X, y


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train-cands", required=True, help="glob 或单 json")
    ap.add_argument("--test-cands", required=True, help="glob 或单 json")
    ap.add_argument("--out", default="ranker.json")
    ap.add_argument("--procs", type=int, default=64)
    ap.add_argument("--neg-ratio", type=float, default=5.0, help="负:正 下采样比")
    ap.add_argument("--max-iter", type=int, default=1500)
    ap.add_argument("--leaves", type=int, default=127)
    ap.add_argument("--mpnn-off", action="store_true", help="对照：mpnn 特征置 0（测无 MPNN 基线）")
    ap.add_argument("--is-metal", action="store_true", help="实验 B：追加 is_metal 域特征列")
    ap.add_argument("--eval-cap", type=int, default=1000, help="eval 每案例候选上限（top-by-freq，0=不限）")
    ap.add_argument("--gbdt", default="lightgbm", choices=["lightgbm", "sklearn"], help="GBDT 实现（lightgbm predict 快）")
    ap.add_argument("--test-limit", type=int, default=0, help="eval 只用前 N 个 test 分片（0=全量）")
    args = ap.parse_args()

    global MPNN_OFF, IS_METAL
    MPNN_OFF = args.mpnn_off
    IS_METAL = args.is_metal
    print(f"mpnn_off={MPNN_OFF} is_metal={IS_METAL} eval_cap={args.eval_cap}", flush=True)

    train_files = iter_files(args.train_cands)
    test_files = iter_files(args.test_cands)
    print(f"train 分片 {len(train_files)}  test 分片 {len(test_files)}", flush=True)

    # ---- pass1：type_map + 正负统计（多进程） ----
    print("pass1：扫 train 统计...", flush=True)
    type_cnt = Counter(); n_pos = n_neg = n_case = 0
    n_metal = n_metal_pos = 0
    with Pool(args.procs) as pool:
        for tc, npos, nneg, ncase, nm, nmp in pool.imap_unordered(_w_stats, train_files, chunksize=4):
            type_cnt.update(tc); n_pos += npos; n_neg += nneg; n_case += ncase
            n_metal += nm; n_metal_pos += nmp
    top_types = [t for t, _ in type_cnt.most_common(30)]
    type_map = {t: i for i, t in enumerate(top_types)}
    n_types = len(top_types)
    print(f"train case {n_case}  候选正 {n_pos} 负 {n_neg}  类型 top{n_types} "
          f"(覆盖 {sum(type_cnt[t] for t in top_types)}/{sum(type_cnt.values())})", flush=True)
    if IS_METAL:
        print(f"is_metal: {n_metal} cands ({n_metal / max(1, n_pos + n_neg):.4f} of all), "
              f"其中正例 {n_metal_pos} (正例金属率 {n_metal_pos / max(1, n_pos):.4f})", flush=True)

    # ---- pass2：采样特征（多进程） ----
    neg_prob = min(1.0, args.neg_ratio * n_pos / max(n_neg, 1))
    print(f"pass2：采样 neg_prob={neg_prob:.5f}...", flush=True)
    Xs, ys = [], []
    with Pool(args.procs) as pool:
        tasks = [(f, type_map, n_types, neg_prob, i, MPNN_OFF, IS_METAL)
                 for i, f in enumerate(train_files)]
        for X, y in pool.imap_unordered(_w_rows, tasks, chunksize=4):
            Xs.extend(X); ys.extend(y)
    X = np.asarray(Xs, dtype=np.float64)
    y = np.asarray(ys, dtype=np.int32)
    del Xs, ys
    n_kept, n_kept_pos = len(y), int(y.sum())
    X_N_SF = X.shape[1] - 11 - (1 if IS_METAL else 0)
    print(f"训练样本 {n_kept} (正 {n_kept_pos})  X {X.shape}", flush=True)

    if args.gbdt == "lightgbm":
        import lightgbm as lgb
        clf = lgb.LGBMClassifier(
            n_estimators=args.max_iter, num_leaves=args.leaves,
            learning_rate=0.05, n_jobs=args.procs, random_state=0, verbose=-1)
        print("using LightGBM (predict 快，无 sklearn 64 线程开销)", flush=True)
    else:
        clf = HistGradientBoostingClassifier(
            max_iter=args.max_iter, learning_rate=0.05, max_leaf_nodes=args.leaves,
            early_stopping=True, validation_fraction=0.1, random_state=0)
    clf.fit(X, y)
    n_iter_val = getattr(clf, "n_iter_", None)
    if n_iter_val is None:
        n_iter_val = getattr(clf, "best_iteration_", None) or args.max_iter
    print(f"GBDT 训练完成 n_iter={n_iter_val}", flush=True)
    del X, y

    # ---- 评估（主进程流式，纯预测无 RDKit） ----
    print("评估 test...", flush=True)
    KS = (1, 3, 5, 10)
    hit_r = dict.fromkeys(KS, 0)
    hit_f = n = 0
    test_eval = test_files[:args.test_limit] if args.test_limit else test_files
    print(f"  eval on {len(test_eval)}/{len(test_files)} test files", flush=True)
    for f in test_eval:
        for case in load_cases(f):
            cands = case.get("cands") or []
            n += 1
            if not cands:
                continue
            if args.eval_cap and len(cands) > args.eval_cap:  # 避免 huge case 卡死 eval
                cands = sorted(cands, key=lambda c: -c.get("f", 0))[:args.eval_cap]
            ncand = case.get("ncand") or len(cands)
            Xc = np.asarray([cand_row(c, ncand, type_map, n_types) for c in cands],
                            dtype=np.float64)
            proba = clf.predict_proba(Xc)[:, 1]
            order = np.argsort(-proba)
            top_f = max(cands, key=lambda c: c["f"])["s"]
            ct = case["true"]
            if top_f == ct:
                hit_f += 1
            for k in KS:
                topk = {cands[int(i)]["s"] for i in order[:k]}
                if ct in topk:
                    hit_r[k] += 1
        if n % 500 == 0:
            print(f"  eval {n} case  hit@1={hit_r[1]}/{n} @3={hit_r[3]} @5={hit_r[5]} @10={hit_r[10]}", flush=True)
    res = {k: (hit_r[k] / n if n else None) for k in KS}
    top1_f = hit_f / n if n else None
    print(f"test n={n}  top1[freq]={hit_f}/{n}={top1_f:.3f}  "
          f"hit@1={res[1]:.4f} @3={res[3]:.4f} @5={res[5]:.4f} @10={res[10]:.4f}", flush=True)

    # ---- 特征重要性（gain，仅报告用） ----
    feat_imp = None
    is_metal_gain = None
    try:
        names = (["f", "f_norm", "log1p_f", "r", "r_norm", "nc", "sim",
                  "atomsize", "conserv", "mpnn"]
                 + [f"sf_{i}" for i in range(X_N_SF)]
                 + ["type_idx"] + (["is_metal"] if IS_METAL else []))
        gain = clf.booster_.feature_importance(importance_type="gain")
        assert len(names) == len(gain), (len(names), len(gain))
        order_i = sorted(range(len(gain)), key=lambda i: -gain[i])
        feat_imp = {names[i]: float(gain[i]) for i in order_i[:40]}
        if IS_METAL:
            is_metal_gain = float(gain[names.index("is_metal")])
    except Exception as e:
        print(f"feature importance skipped: {e}", flush=True)

    out = {"top1_freq": top1_f, "top1_ranker": res[1],
           "hit_at_3": res[3], "hit_at_5": res[5], "hit_at_10": res[10],
           "n_test": n,
           "n_train_kept": n_kept, "n_pos": n_kept_pos,
           "n_train_case": n_case, "n_types": n_types,
           "neg_prob": neg_prob, "n_iter": int(n_iter_val),
           "max_iter": args.max_iter, "leaves": args.leaves,
           "mpnn_off": MPNN_OFF, "is_metal": IS_METAL}
    if IS_METAL:
        out["is_metal_cands"] = n_metal
        out["is_metal_pos"] = n_metal_pos
    if feat_imp is not None:
        out["feature_importance_gain_top40"] = feat_imp
    if IS_METAL:
        out["is_metal_importance_gain"] = is_metal_gain
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=2)
    # 存模型（LightGBM 支持，供后续 Hit@K 重算免重训）
    try:
        clf.booster_.save_model(args.out.replace(".json", "_model.txt"))
        print("model saved", flush=True)
    except Exception as e:
        print(f"model save skipped: {e}", flush=True)
    print("written", args.out, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
