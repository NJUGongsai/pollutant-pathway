#!/usr/bin/env python3
"""后处理：重算 shards_train3 候选的 mpnn 特征。

背景：run_shard 跑时 parse_center 不认 2-part center（train.txt 格式）→ convert_line 返回
None → mpnn 全 0。现 parse_center 已修（接受 2-part）。本脚本不重跑模板匹配，而是用 shard
里存的 lhs + site_atom_idx：按 lhs 查 train.txt 重建 full line → convert_line(已修) → 查
train_preds → 用 atom-map 桥接 site 原子重算 mpnn，原地改写 shard。

用法（HPC）：python gnn_phase6_rempnn.py  (默认扫 shards_train3/shard_*.json，1 进程)
"""
import glob
import json
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from rdkit import Chem, RDLogger  # noqa: E402
RDLogger.DisableLog("rdApp.*")
import gnn_phase2_uspto as L  # noqa: E402  (convert_line + parse_center 已修)


def _mpnn(site, mol, m2c, p):
    if not m2c or p is None:
        return 0.0
    best = 0.0
    for i in site:
        m = mol.GetAtomWithIdx(i).GetAtomMapNum()
        ci = m2c.get(m)
        if ci is not None and 0 <= ci < len(p):
            if p[ci] > best:
                best = p[ci]
    return best


def _substrate_only(line):
    """轻量 convert_line：只取 (canon_substrate_smiles, mapnum->canon_idx)，
    跳过 CanonicalRankAtoms×2（O(n²)，仅用于 label 映射，本脚本不需要）。
    与 convert_line 同 _submol+MolToSmiles 路径 + 同 fragment 选择（含 H-transfer），
    保证 substrate 与 train_preds key 一致。"""
    line = line.rstrip("\n")
    parts = line.split()
    if len(parts) < 1 or ">>" not in parts[0]:
        return None, None
    rxn = parts[0]
    center = parts[1] if len(parts) > 1 else ""
    lhs, rhs = rxn.split(">>", 1)
    R = Chem.MolFromSmiles(lhs)
    P = Chem.MolFromSmiles(rhs)
    if R is None or P is None:
        return None, None
    R_by_map = {a.GetAtomMapNum(): a.GetIdx() for a in R.GetAtoms() if a.GetAtomMapNum() > 0}
    P_by_map = {a.GetAtomMapNum(): a.GetIdx() for a in P.GetAtoms() if a.GetAtomMapNum() > 0}
    reacted = set()
    for a, b, _o in L.parse_center(center):
        if a in R_by_map:
            reacted.add(a)
        if b in R_by_map:
            reacted.add(b)
    for m in set(R_by_map) & set(P_by_map):
        ra = R.GetAtomWithIdx(R_by_map[m])
        pa = P.GetAtomWithIdx(P_by_map[m])
        if ra.GetTotalNumHs() != pa.GetTotalNumHs() or ra.GetFormalCharge() != pa.GetFormalCharge():
            reacted.add(m)
    if not reacted:
        return None, None
    frags = Chem.GetMolFrags(R)
    best, best_n = None, 0
    for frag in frags:
        n = sum(1 for i in frag if R.GetAtomWithIdx(i).GetAtomMapNum() in reacted)
        if n > best_n:
            best_n, best = n, frag
    if best is None or best_n == 0:
        return None, None
    sub = L.gnn_labels._submol(R, list(best))
    canon = Chem.MolToSmiles(sub)
    cm = Chem.MolFromSmiles(canon)
    if cm is None:
        return None, None
    m2c = {a.GetAtomMapNum(): a.GetIdx() for a in cm.GetAtoms() if a.GetAtomMapNum() > 0}
    return canon, m2c


PRED = {}          # module global（fork 子进程继承）
LHS2LINE = {}      # module global
CACHE = {}         # lhs -> (m2c, parr)，apply 阶段 fork 继承


def _worker(lhs):
    """fork 子进程：lhs -> (lhs, canon, m2c)。parr 在主进程查 PRED（避免大 list 经 IPC）。"""
    full = LHS2LINE.get(lhs)
    if not full:
        return lhs, None, None
    canon, m2c = _substrate_only(full)
    return lhs, canon, m2c


def _apply_shard(f):
    """fork 子进程：处理单个 shard，原地改写 mpnn。返回 (cands, mpnn_gt0, hit, skip)。"""
    cands = mpnn_gt0 = hit = 0
    try:
        d = json.load(open(f))
        for case in d.get("dump", []):
            lhs = case.get("lhs", "")
            m2c, parr = CACHE.get(lhs, (None, None))
            if parr is not None:
                hit += 1
            mol = Chem.MolFromSmiles(lhs) if lhs else None
            for cand in case.get("cands", []):
                site = cand.get("site_atom_idx", [])
                cand["mpnn"] = round(_mpnn(site, mol, m2c, parr), 6)
                cands += 1
                if cand["mpnn"] > 0:
                    mpnn_gt0 += 1
        with open(f, "w") as fh:
            json.dump(d, fh)
    except Exception as e:
        return f, 0, 0, 0, str(e)[:40]
    return f, cands, mpnn_gt0, hit, ""


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preds", default="train_preds.jsonl", help="MPNN preds jsonl")
    ap.add_argument("--train", default="train.txt", help="反应文件（建 lhs→full_line 索引）")
    ap.add_argument("--shards", default="shards_train3/shard_*.json", help="shard glob")
    args = ap.parse_args()
    pred_path = args.preds
    train_path = args.train
    shard_glob = args.shards

    print("loading train_preds...", flush=True)
    global PRED, LHS2LINE, CACHE
    PRED = {}
    with open(pred_path) as fh:
        for line in fh:
            r = json.loads(line)
            PRED[r["s"]] = r["p"]
    print(f"  {len(PRED)} substrates", flush=True)

    print("indexing train.txt by lhs...", flush=True)
    LHS2LINE = {}
    with open(train_path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if ">>" not in line:
                continue
            lhs = line.split(">>", 1)[0]
            if lhs not in LHS2LINE:  # 首次出现（同 lhs 底物相同）
                LHS2LINE[lhs] = line
    print(f"  {len(LHS2LINE)} unique lhs", flush=True)

    # 阶段1：并行预算 cache（lhs -> (m2c, parr)），fork 子进程继承 LHS2LINE（COW 只读共享）
    print("parallel cache build (64 procs)...", flush=True)
    n_hit = 0
    with Pool(64) as p:
        for lhs, canon, m2c in p.imap(_worker, list(LHS2LINE), chunksize=500):
            parr = PRED.get(canon) if canon is not None else None
            if parr is not None:
                n_hit += 1
            else:
                m2c = None
            CACHE[lhs] = (m2c, parr)
    print(f"  cache={len(CACHE)} hit={n_hit}", flush=True)

    # 阶段2：并行 apply（每 shard 一任务，fork 继承 CACHE），原地改写 mpnn
    files = sorted(glob.glob(shard_glob))
    print(f"parallel apply to {len(files)} shards (64 procs)...", flush=True)
    tot_c = tot_m = tot_h = n_skip = 0
    with Pool(64) as p:
        for f, c, m, h, err in p.imap(_apply_shard, files, chunksize=4):
            if err:
                n_skip += 1
                print(f"  SKIP {f}: {err}", flush=True)
                continue
            tot_c += c; tot_m += m; tot_h += h
    cov = tot_m / max(1, tot_c)
    print(f"DONE cands={tot_c} mpnn>0={tot_m} hit={tot_h} "
          f"coverage={cov:.3f} skip={n_skip}", flush=True)


if __name__ == "__main__":
    main()
