#!/usr/bin/env python3
"""MPNN 域微调试水 — Phase 2（chenyu 运行）: 加载 v3 权重 → 小 lr 微调 →
对 BBD 93 底物 + USPTO 5k 抽样推理 → dump 概率/指标文件。

架构修正: 任务书 §4.2 写 MPNN(68,6,256,6)，但 ~/rxn6/gnn_model_v3/model.pt
实际是 MPNN(68,6,384,8)（result.json: hidden=384/layers=8/hit1=0.7523 证实）。
用 256/6 load_state_dict 会 shape mismatch 崩溃，故用 384/8。

红线: 全部输出落 ~/rxn6/mpnn_trial/。单卡、无 DataParallel（§4.5 确定性）。
"""
import argparse
import copy
import json
import os
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F

# import 自 chenyu 同款训练脚本（~/rxn6/gnn_phase2_train_uspto.py）
sys.path.insert(0, os.path.expanduser("~/rxn6"))
from gnn_phase2_train_uspto import (  # noqa: E402
    MPNN, D_ATOM, D_BOND, mol_to_tensor, collate, load_records)

from rdkit import Chem  # noqa: E402
from rdkit import RDLogger  # noqa: E402
RDLogger.DisableLog("rdApp.*")

TRIAL_DIR = os.path.expanduser("~/rxn6/mpnn_trial")
V3_MODEL = os.path.expanduser("~/rxn6/gnn_model_v3/model.pt")
V3_RESULT = os.path.expanduser("~/rxn6/gnn_model_v3/result.json")
BBD_BASELINE = os.path.expanduser("~/rxn6/bbd_predictions.jsonl")
USPTO_TEST = os.path.expanduser("~/rxn6/gnn_uspto_test/train_set.jsonl")
TRAIN_SET = os.path.join(TRIAL_DIR, "finetune_train.jsonl")

HIDDEN = 384
LAYERS = 8
LR = 1e-4
EPOCHS = 50
PATIENCE = 10
POS_WEIGHT = 20.0
BSIZE = 32
USPTO_SAMPLE_N = 5000


def set_seed(seed=0):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def eval_hit1(model, recs, device, bsize=64):
    """device-aware 复刻 evaluate 的 hit1/hit2/mean_per_mol_ap（原 evaluate 不搬 x/adj/edge
    到 cuda，v3 是 CPU 训的；本机 cuda 上直接搬）。"""
    from sklearn.metrics import average_precision_score
    model.eval()
    per_ap = []
    hit1 = hit2 = n_with_pos = 0
    n_total = 0
    with torch.no_grad():
        for i in range(0, len(recs), bsize):
            items = recs[i:i + bsize]
            x, adj, edge, y, mask = collate(items)
            p = torch.sigmoid(
                model(x.to(device), adj.to(device), edge.to(device),
                      mask.to(device))["atom"])
            y = y.to(device)
            for b, it in enumerate(items):
                n = it[0][4]
                yt = y[b, :n].cpu().numpy().astype(int)
                ps = p[b, :n].cpu().numpy()
                n_total += 1
                if yt.sum() == 0:
                    continue
                n_with_pos += 1
                per_ap.append(average_precision_score(yt, ps))
                order = np.argsort(-ps)
                if yt[order[:1]].sum() > 0:
                    hit1 += 1
                if yt[order[:2]].sum() > 0:
                    hit2 += 1
    return {
        "hit1": hit1 / n_with_pos if n_with_pos else float("nan"),
        "hit2": hit2 / n_with_pos if n_with_pos else float("nan"),
        "mean_per_mol_ap": float(np.mean(per_ap)) if per_ap else float("nan"),
        "n_with_pos": n_with_pos,
        "n_total": n_total,
    }



def load_v3(device):
    model = MPNN(D_ATOM, D_BOND, HIDDEN, LAYERS)
    sd = torch.load(V3_MODEL, map_location="cpu")
    model.load_state_dict(sd)
    model.to(device)
    return model


def finetune(model, recs, device, lr=LR, epochs=EPOCHS, bsize=BSIZE,
             pos_weight=POS_WEIGHT, patience=PATIENCE):
    """小 lr 全参数微调，train-loss 早停（§4.2）。返回 (log, best_state_epoch)。"""
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    pw = torch.tensor(pos_weight, device=device)
    n_batches = (len(recs) + bsize - 1) // bsize
    log = []
    best_loss = float("inf")
    best_state = None
    best_epoch = -1
    patience_left = patience
    for ep in range(epochs):
        model.train()
        idx = np.random.permutation(len(recs))
        tot = 0.0
        nb = 0
        for bi in range(0, len(recs), bsize):
            items = [recs[j] for j in idx[bi:bi + bsize]]
            x, adj, edge, y, mask = collate(items)
            opt.zero_grad()
            out = model(x.to(device), adj.to(device), edge.to(device),
                        mask.to(device))
            y = y.to(device)
            mask = mask.to(device)
            loss = F.binary_cross_entropy_with_logits(
                out["atom"], y, pos_weight=pw, reduction="none")
            loss = (loss * mask.float()).sum() / mask.float().sum()
            loss.backward()
            opt.step()
            tot += loss.item()
            nb += 1
        avg = tot / max(1, nb)
        log.append({"epoch": ep, "train_loss": avg})
        improved = avg < best_loss - 1e-6
        if improved:
            best_loss = avg
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = ep
            patience_left = patience
        else:
            patience_left -= 1
        print(f"  [ft {ep}/{epochs}] loss={avg:.4f} best={best_loss:.4f}@{best_epoch} "
              f"patience_left={patience_left}", flush=True)
        if patience_left <= 0:
            print(f"  early stop at epoch {ep} (patience={patience})", flush=True)
            break
    # 恢复最佳 train-loss 权重
    if best_state is not None:
        model.load_state_dict(best_state)
    return log, best_epoch, best_loss


def infer_bbd(model, device, baseline_path):
    """对 BBD 93 底物推理，复刻 bbd_predictions.jsonl schema。"""
    model.eval()
    cases = []
    with open(baseline_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    out = []
    with torch.no_grad():
        for c in cases:
            smi = c["smiles"]
            case_id = c["case_id"]
            t = mol_to_tensor(smi, [])
            if t is None:
                out.append(c)  # fallback 保留原基线记录
                continue
            x, adj, edge, _, n = t
            p = torch.sigmoid(
                model(x.unsqueeze(0).to(device), adj.unsqueeze(0).to(device),
                      edge.unsqueeze(0).to(device),
                      torch.ones(1, n, dtype=torch.bool, device=device))["atom"][0])
            probs = p.cpu().numpy().tolist()
            m = Chem.MolFromSmiles(smi)
            atoms = []
            for a in m.GetAtoms():
                atoms.append({"idx": a.GetIdx(), "symbol": a.GetSymbol(),
                              "atom_map": 0, "prob": probs[a.GetIdx()]})
            atoms.sort(key=lambda d: -d["prob"])
            top_atoms = atoms[:10]
            out.append({
                "case_id": case_id, "smiles": smi, "n_atoms": n,
                "atom_probs": probs, "atoms": atoms, "top_atoms": top_atoms,
            })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", default=TRAIN_SET)
    ap.add_argument("--freeze-layers", type=int, default=0,
                    help="冻结底 N 层消息传递（§4.4 重试用）")
    args = ap.parse_args()

    os.makedirs(TRIAL_DIR, exist_ok=True)
    set_seed(0)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {device}  (n_gpu={torch.cuda.device_count()})", flush=True)
    assert torch.cuda.device_count() == 1, "单卡约束（§4.5）"

    # --- 加载 v3 ---
    print("loading v3 weights...", flush=True)
    model = load_v3(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"MPNN(68,6,{HIDDEN},{LAYERS}) params={n_params}", flush=True)

    # §4.4 重试: 冻结底 N 层消息传递
    if args.freeze_layers > 0:
        for i in range(args.freeze_layers):
            for p in model.mps[i].parameters():
                p.requires_grad = False
        n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"frozen bottom {args.freeze_layers} mp layers; trainable={n_train}",
              flush=True)

    # --- 加载训练集 ---
    print(f"loading train {args.train}...", flush=True)
    recs = load_records(args.train)
    print(f"train: {len(recs)} records", flush=True)

    # --- 微调 ---
    t0 = time.time()
    log, best_epoch, best_loss = finetune(model, recs, device)
    wall = time.time() - t0
    suffix = f"_frozen{args.freeze_layers}" if args.freeze_layers else ""
    torch.save(model.state_dict(),
               os.path.join(TRIAL_DIR, f"model_finetuned_trial{suffix}.pt"))
    with open(os.path.join(TRIAL_DIR, f"train_log{suffix}.json"), "w") as fh:
        json.dump({"log": log, "best_epoch": best_epoch, "best_loss": best_loss,
                   "wall_seconds": round(wall, 1), "lr": LR, "epochs_run": len(log),
                   "n_train": len(recs), "hidden": HIDDEN, "layers": LAYERS,
                   "freeze_layers": args.freeze_layers}, fh, indent=2)
    print(f"finetune done in {wall:.0f}s, best_loss={best_loss:.4f}@ep{best_epoch}",
          flush=True)

    # --- 推理 A: BBD 93 ---
    print("infer BBD 93 substrates (finetuned)...", flush=True)
    bbd_out = infer_bbd(model, device, BBD_BASELINE)
    with open(os.path.join(TRIAL_DIR, f"trial_bbd_probs{suffix}.jsonl"), "w") as fh:
        for r in bbd_out:
            fh.write(json.dumps(r) + "\n")
    print(f"  wrote trial_bbd_probs{suffix}.jsonl ({len(bbd_out)} cases)", flush=True)

    # --- 推理 A: BBD 93 (v3 原模型, 配对基线) ---
    print("infer BBD 93 substrates (v3 original, paired baseline)...", flush=True)
    v3_model = load_v3(device)
    v3_bbd = infer_bbd(v3_model, device, BBD_BASELINE)
    with open(os.path.join(TRIAL_DIR, f"trial_bbd_probs_v3{suffix}.jsonl"), "w") as fh:
        for r in v3_bbd:
            fh.write(json.dumps(r) + "\n")
    print(f"  wrote trial_bbd_probs_v3{suffix}.jsonl", flush=True)

    # --- 推理 B: USPTO 5k 抽样 (v3 + finetuned) ---
    print(f"loading USPTO test {USPTO_TEST}...", flush=True)
    uspto_recs = load_records(USPTO_TEST)
    print(f"uspto test: {len(uspto_recs)} records", flush=True)
    rng = np.random.RandomState(0)
    sample_idx = rng.choice(len(uspto_recs), size=min(USPTO_SAMPLE_N, len(uspto_recs)),
                            replace=False)
    uspto_sample = [uspto_recs[i] for i in sample_idx]
    print(f"sampled {len(uspto_sample)} (seed=0)", flush=True)

    print("eval USPTO 5k (finetuned)...", flush=True)
    ft_metrics = eval_hit1(model, uspto_sample, device, bsize=64)
    print(f"  finetuned hit@1={ft_metrics['hit1']:.4f}", flush=True)

    print("eval USPTO 5k (v3 original, paired)...", flush=True)
    v3_metrics = eval_hit1(v3_model, uspto_sample, device, bsize=64)
    print(f"  v3 hit@1={v3_metrics['hit1']:.4f}", flush=True)

    # 全量 40k 参考
    full_hit1 = None
    if os.path.exists(V3_RESULT):
        with open(V3_RESULT) as fh:
            full_hit1 = json.load(fh).get("hit1")

    uspto_hit = {
        "n_sample": len(uspto_sample),
        "finetuned_hit1": ft_metrics["hit1"],
        "finetuned_mean_ap": ft_metrics["mean_per_mol_ap"],
        "v3_paired_hit1": v3_metrics["hit1"],
        "v3_paired_mean_ap": v3_metrics["mean_per_mol_ap"],
        "v3_full_40k_hit1_reference": full_hit1,
    }
    with open(os.path.join(TRIAL_DIR, f"trial_uspto_hit{suffix}.json"), "w") as fh:
        json.dump(uspto_hit, fh, indent=2)
    print("=== USPTO 防遗忘 ===", flush=True)
    print(json.dumps(uspto_hit, indent=2), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
