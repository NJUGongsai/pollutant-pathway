#!/usr/bin/env python3
"""MPNN 域微调试水 — Phase 3（本地评估）: 算三个 go/no-go 指标 + 判据 + 诊断。

判据先于结果（红线 §5.3）: 先打印 §0 判据表（基线 + Go 门槛），再填实测，
再给 Go / No-Go / 有条件 Go。基线与微调同法同口径算分离度。
"""
import argparse
import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "reaction_analogy", "data", "bbd_mpnn_trial")

DOC_BASELINE = {"median_sep": 0.0195, "frac_below_0p01": 0.44, "uspto_hit1": 0.7523}
GO_THRESH = {"median_sep": 0.039, "frac_below_0p01": 0.30, "uspto_hit1": 0.70}

HIST_BINS = [0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]


def load_probs(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            out.append((r.get("case_id"), r.get("smiles"), r.get("atom_probs", [])))
    return out


def sep_summary(probs_rows):
    seps = []
    for cid, smi, ps in probs_rows:
        if len(ps) < 2:
            continue
        s = sorted(ps, reverse=True)
        seps.append(s[0] - s[1])
    seps = np.array(seps, dtype=np.float64)
    n = len(seps)
    return {
        "n": n,
        "median_sep": float(np.median(seps)) if n else None,
        "frac_below_0p01": float((seps < 0.01).mean()) if n else None,
        "mean_sep": float(np.mean(seps)) if n else None,
        "q25": float(np.quantile(seps, 0.25)) if n else None,
        "q75": float(np.quantile(seps, 0.75)) if n else None,
        "hist": {f"{HIST_BINS[i]}-{HIST_BINS[i+1]}": int(((seps >= HIST_BINS[i]) & (seps < HIST_BINS[i+1])).sum())
                 for i in range(len(HIST_BINS) - 1)} if n else {},
    }


def topk_table(rows_ft, rows_v3):
    d_v3 = {cid: ps for cid, _, ps in rows_v3}
    out = []
    for cid, smi, ps in rows_ft:
        if cid not in d_v3:
            continue
        ps_v3 = sorted(d_v3[cid], reverse=True)
        ps_ft = sorted(ps, reverse=True)
        out.append({
            "case_id": cid, "smiles": smi, "n_atoms": len(ps),
            "v3_top1": ps_v3[0] if ps_v3 else None,
            "v3_top2": ps_v3[1] if len(ps_v3) > 1 else None,
            "ft_top1": ps_ft[0] if ps_ft else None,
            "ft_top2": ps_ft[1] if len(ps_ft) > 1 else None,
            "v3_sep": (ps_v3[0] - ps_v3[1]) if len(ps_v3) > 1 else None,
            "ft_sep": (ps_ft[0] - ps_ft[1]) if len(ps_ft) > 1 else None,
        })
    return out


def verdict(sep_med, sep_frac, uspto):
    sep_go = (sep_med >= GO_THRESH["median_sep"]) and (sep_frac <= GO_THRESH["frac_below_0p01"])
    uspto_go = uspto >= GO_THRESH["uspto_hit1"]
    if sep_go and uspto_go:
        return "Go"
    if sep_go and (not uspto_go):
        return "有条件Go(retry_needed)"
    return "No-Go"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default=DATA)
    ap.add_argument("--ft", default="trial_bbd_probs.jsonl")
    ap.add_argument("--v3-paired", default="trial_bbd_probs_v3.jsonl")
    ap.add_argument("--orig-baseline", default="bbd_predictions_v3_baseline.jsonl")
    ap.add_argument("--uspto", default="trial_uspto_hit.json")
    ap.add_argument("--train-log", default="train_log.json")
    ap.add_argument("--suffix", default="")
    args = ap.parse_args()

    d = args.dir
    suffix = args.suffix
    def p(fn):
        return os.path.join(d, fn)

    ft_path = p(("trial_bbd_probs" + suffix + ".jsonl") if suffix else args.ft)
    v3_path = p(("trial_bbd_probs_v3" + suffix + ".jsonl") if suffix else args.v3_paired)
    uspto_path = p(("trial_uspto_hit" + suffix + ".json") if suffix else args.uspto)
    log_path = p(("train_log" + suffix + ".json") if suffix else args.train_log)

    rows_orig = load_probs(p(args.orig_baseline))
    rows_v3 = load_probs(v3_path)
    rows_ft = load_probs(ft_path)
    with open(uspto_path) as fh:
        uspto = json.load(fh)
    with open(log_path) as fh:
        train_log = json.load(fh)

    sep_orig = sep_summary(rows_orig)
    sep_v3 = sep_summary(rows_v3)
    sep_ft = sep_summary(rows_ft)
    uspto_ft = uspto.get("finetuned_hit1")
    uspto_v3_paired = uspto.get("v3_paired_hit1")
    uspto_v3_full = uspto.get("v3_full_40k_hit1_reference")

    print("=" * 70)
    print("§0 Go/No-Go 判据表（跑前定死）")
    print("=" * 70)
    print(f"{'指标':<28} {'基线(v3)':<14} {'Go门槛':<14}")
    print(f"{'分离度中位 top1-top2':<28} {DOC_BASELINE['median_sep']:<14.4f} {'>='+str(GO_THRESH['median_sep']):<14}")
    print(f"{'分离度<0.01 占比':<28} {DOC_BASELINE['frac_below_0p01']:<14.2f} {'<='+str(GO_THRESH['frac_below_0p01']):<14}")
    print(f"{'USPTO test hit@1':<28} {DOC_BASELINE['uspto_hit1']:<14.4f} {'>='+str(GO_THRESH['uspto_hit1']):<14}")
    print("三项全过=Go; 分离度两项过但USPTO崩=有条件Go(§4.4重试); 其他=No-Go\n")

    v = verdict(sep_ft["median_sep"], sep_ft["frac_below_0p01"], uspto_ft)

    print("=" * 70)
    print("实测结果")
    print("=" * 70)
    print(f"{'指标':<28} {'原基线':<14} {'配对v3':<14} {'微调':<14} {'门槛':<12} 过?")
    print(f"{'分离度中位':<28} {sep_orig['median_sep']:<14.5f} {sep_v3['median_sep']:<14.5f} {sep_ft['median_sep']:<14.5f} {GO_THRESH['median_sep']:<12} {'Y' if sep_ft['median_sep']>=GO_THRESH['median_sep'] else 'N'}")
    print(f"{'分离度<0.01占比':<28} {sep_orig['frac_below_0p01']:<14.3f} {sep_v3['frac_below_0p01']:<14.3f} {sep_ft['frac_below_0p01']:<14.3f} {GO_THRESH['frac_below_0p01']:<12} {'Y' if sep_ft['frac_below_0p01']<=GO_THRESH['frac_below_0p01'] else 'N'}")
    print(f"{'USPTO hit@1(5k)':<28} {'(n/a)':<14} {uspto_v3_paired:<14.4f} {uspto_ft:<14.4f} {GO_THRESH['uspto_hit1']:<12} {'Y' if uspto_ft>=GO_THRESH['uspto_hit1'] else 'N'}")
    print(f"{'(ref 全量40k v3)':<28} {uspto_v3_full:<14.4f}")
    print(f"\n=== 判据结论: {v} ===\n")

    topk = topk_table(rows_ft, rows_v3)
    print("分离度直方图（bin: count）")
    print(f"{'bin':<16} {'配对v3':<10} {'微调':<10}")
    for i in range(len(HIST_BINS) - 1):
        k = f"{HIST_BINS[i]}-{HIST_BINS[i+1]}"
        print(f"{k:<16} {sep_v3['hist'].get(k,0):<10} {sep_ft['hist'].get(k,0):<10}")
    print(f"\ntrain: {train_log.get('epochs_run')} epochs, best_loss={train_log.get('best_loss')} @ep{train_log.get('best_epoch')}, wall={train_log.get('wall_seconds')}s, lr={train_log.get('lr')}, freeze={train_log.get('freeze_layers')}")

    result = {
        "criteria": {"baseline_ref": DOC_BASELINE, "go_thresholds": GO_THRESH},
        "separation": {"original_baseline": sep_orig, "paired_v3": sep_v3, "finetuned": sep_ft},
        "uspto": {"finetuned_hit1": uspto_ft, "v3_paired_hit1": uspto_v3_paired,
                  "v3_full_40k_hit1_reference": uspto_v3_full, "threshold": GO_THRESH["uspto_hit1"]},
        "verdict": v,
        "train_log_summary": {k: train_log.get(k) for k in
                              ("epochs_run", "best_loss", "best_epoch", "wall_seconds", "lr", "freeze_layers", "n_train")},
        "topk_table_excerpt": topk[:10],
        "hist_bins": HIST_BINS,
    }
    out_path = p(("trial_eval" + suffix + ".json") if suffix else "trial_eval.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"\n写入 {out_path}", flush=True)


if __name__ == "__main__":
    main()
