"""验证器数据接入层: 反应 → 催化酶(UniProt+EC) → 口袋 3D 坐标。

链路(晨羽实测确认):
  ① reaction SMILES --(formal_filtered_train.csv, col=CANO_RXN_SMILES, 取 Label=1)--> UniProt + EC
  ② UniProt --(gvp_protein_feature_flat.pt[UniProt][0])--> node_xyz [n_res, 3] Cα 坐标

作用: 为 novel 产物预测提供"酶/口袋证据"——检索到的 donor 反应对应一族真实催化酶,
用其口袋几何给候选产物 X→Y' 打分背书 (纯 LLM 给不了的确定性证据)。
"""
import os
import csv
import pickle
from functools import lru_cache

import numpy as np

_DEFAULT_DATA_ROOT = "/Volumes/CC/Enzyme_Agent/depending/data"
_DATA_ROOT = os.environ.get("ENZYMECAGE_DATA_ROOT", _DEFAULT_DATA_ROOT)
_TRAIN_CSV = os.path.join(_DATA_ROOT, "formal_splits/formal_filtered_train.csv")
_GVP_PT = os.path.join(_DATA_ROOT, "feature/protein/gvp/gvp_protein_feature_flat.pt")
# 本地默认使用预构建的正样本缓存 (从 463M CSV 在 HPC 端预生成, 见 sync_assets.sh)
_RXN2ENZ_CACHE = os.environ.get("RXN2ENZYME_CACHE", os.path.join(_DATA_ROOT, "rxn2enzyme_positives.pkl"))


# ── ① 反应 → 催化酶 (仅正样本 Label=1) ────────────────────────────────
@lru_cache(maxsize=1)
def _load_rxn2enzymes():
    """构建 {CANO_RXN_SMILES: [(UniProt, EC), ...]} 仅 Label==1。首次解析 CSV 后缓存。"""
    if os.path.exists(_RXN2ENZ_CACHE):
        with open(_RXN2ENZ_CACHE, "rb") as f:
            return pickle.load(f)
    idx = {}
    with open(_TRAIN_CSV, newline="") as f:
        r = csv.reader(f)
        header = next(r)
        ci = {name: i for i, name in enumerate(header)}
        cu, cs, ce, cl = ci["UniprotID"], ci["CANO_RXN_SMILES"], ci["EC number"], ci["Label"]
        for row in r:
            if len(row) <= cl or row[cl] != "1":
                continue
            idx.setdefault(row[cs], []).append((row[cu], row[ce]))
    try:
        with open(_RXN2ENZ_CACHE, "wb") as f:
            pickle.dump(idx, f)
    except Exception:
        pass
    return idx


def enzymes_for_reaction(rxn_smiles):
    """返回催化该反应的酶 [(uniprot, ec), ...] (仅正样本)。未命中返回 []。"""
    return _load_rxn2enzymes().get(str(rxn_smiles), [])


# ── ①' 酶 → 催化过的反应族 (反向索引, 供 Step3 DRFP-酶集排序器) ──────────
@lru_cache(maxsize=1)
def _load_enz2rxns():
    """由 _load_rxn2enzymes() 反转出 {UniProt: [CANO_RXN_SMILES, ...]}。"""
    idx = {}
    for rxn, pairs in _load_rxn2enzymes().items():
        for uni, _ec in pairs:
            idx.setdefault(uni, []).append(rxn)
    return idx


def reactions_for_enzyme(uniprot):
    """返回该酶催化过的已知反应 SMILES 列表 (仅正样本)。未命中返回 []。"""
    return _load_enz2rxns().get(uniprot, [])


# ── ② UniProt → 口袋 Cα 3D 坐标 ──────────────────────────────────────
@lru_cache(maxsize=1)
def _load_gvp():
    import torch
    return torch.load(_GVP_PT, map_location="cpu", mmap=True)


def pocket_coords(uniprot):
    """返回该酶口袋残基 Cα 坐标 ndarray [n_res, 3]; 未命中返回 None。

    gvp flat .pt: {UniProt: (node_xyz[n,3], node_v, edge_index, node_s, edge_v)}
    元组第 0 项即坐标。mmap 惰性加载, 只物化被索引的酶。
    """
    v = _load_gvp().get(uniprot)
    if v is None:
        return None
    xyz = v[0]
    try:
        return xyz.numpy().astype("float32")
    except Exception:
        return np.asarray(xyz, dtype="float32")


def available():
    return {
        "train_csv": os.path.exists(_TRAIN_CSV),
        "gvp_pt": os.path.exists(_GVP_PT),
        "rxn2enz_cache": os.path.exists(_RXN2ENZ_CACHE),
    }
