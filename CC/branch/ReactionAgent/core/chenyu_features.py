"""晨羽真实特征接入层：reacting_center.pkl + rxn2fp.pkl。

在晨羽 HPC(enzymecage_py312 环境)上运行，为 demo 的 Phase 1/2 提供：
  - reaction_center_from_chenyu(): 查表得真值反应中心，替换不可靠的 MCS
  - most_similar_reactions():      DRFP Tanimoto 召回相似反应，供模板集成

实测确认的数据结构:
  reacting_center.pkl: {reaction_smiles(A>>B): (反应物中心原子list, 产物中心原子list)}
                       两条列表等长且一一对齐; 原子索引为"整条底物串一次解析"的全局连续编号。
  rxn2fp.pkl:          {reaction_smiles(A>>B): float32 ndarray(2048,) 二值 DRFP}
"""
import os
import pickle
from functools import lru_cache

import numpy as np
from rdkit import Chem

from pipeline import ReactionCenter

# ── 数据路径 (本地默认 /depending/data; 可用环境变量覆盖) ─────────────
_DEFAULT_DATA_ROOT = "/Volumes/CC/Enzyme_Agent/depending/data"
_DATA_ROOT = os.environ.get("ENZYMECAGE_DATA_ROOT", _DEFAULT_DATA_ROOT)
_RC_PATH = os.path.join(_DATA_ROOT, "feature/reaction/reacting_center/reacting_center.pkl")
_DRFP_PATH = os.path.join(_DATA_ROOT, "feature/reaction/drfp/rxn2fp.pkl")


@lru_cache(maxsize=1)
def _load_rc():
    with open(_RC_PATH, "rb") as f:
        return {str(k): v for k, v in pickle.load(f).items()}


@lru_cache(maxsize=1)
def _load_drfp():
    with open(_DRFP_PATH, "rb") as f:
        return {str(k): np.asarray(v, np.float32) for k, v in pickle.load(f).items()}


# ── 坑修复：全局连续原子索引 → demo 的逐片段局部索引 ────────────────
def _global_to_per_fragment(side_smiles: str, global_idx):
    """把整条串(A.B.C)的全局原子索引拆回每个片段的局部索引 (与 demo 分片段解析一致)。"""
    mol = Chem.MolFromSmiles(side_smiles)
    if mol is None:
        return []
    frags = Chem.GetMolFrags(mol)  # ((g0,g1,...),(...),...) 全局索引按片段分组
    g2fl = {g: (fi, loc) for fi, atoms in enumerate(frags) for loc, g in enumerate(atoms)}
    per = [[] for _ in frags]
    for g in global_idx:
        if g in g2fl:
            fi, loc = g2fl[g]
            per[fi].append(loc)
    return [sorted(s) for s in per]


# ── Phase 1 替换：查表得真值反应中心，跳过 MCS ─────────────────────
def reaction_center_from_chenyu(rxn_smiles: str):
    """命中 reacting_center.pkl 则返回 demo 格式的 ReactionCenter；未命中返回 None。"""
    v = _load_rc().get(str(rxn_smiles))
    if v is None:
        return None
    if ">>" not in rxn_smiles:
        return None
    r_side, p_side = rxn_smiles.split(">>", 1)
    return ReactionCenter(
        reactant_indices=_global_to_per_fragment(r_side, list(v[0])),
        product_indices=_global_to_per_fragment(p_side, list(v[1])),
    )


def reacting_center_atom_map(rxn_smiles: str):
    """返回反应中心的原子映射对 [(reactant_global_idx, product_global_idx), ...]。

    利用 value 两条列表一一对齐的性质，可替代 MCS 给中心原子编号。
    """
    v = _load_rc().get(str(rxn_smiles))
    if v is None:
        return None
    return list(zip(list(v[0]), list(v[1])))


# ── Phase 2 检索：DRFP Tanimoto 召回相似反应 (供模板集成) ────────────
@lru_cache(maxsize=1)
def _drfp_matrix():
    d = _load_drfp()
    keys = list(d.keys())
    mat = np.stack([d[k] for k in keys]).astype(np.float32)
    return keys, mat


def most_similar_reactions(rxn_smiles: str, top_k: int = 10):
    """对库内已知反应做 DRFP Tanimoto 召回。新反应(未预存 DRFP)返回 None。"""
    d = _load_drfp()
    q = d.get(str(rxn_smiles))
    if q is None:
        return None  # 新反应需 pip install drfp 现算指纹
    keys, mat = _drfp_matrix()
    inter = mat @ q
    tani = inter / (mat.sum(1) + q.sum() - inter + 1e-9)  # 二值 DRFP -> Tanimoto
    order = np.argsort(-tani)[:top_k]
    return [(keys[i], float(tani[i])) for i in order]


def available():
    """检查晨羽特征文件是否就位。"""
    return {"reacting_center": os.path.exists(_RC_PATH), "drfp": os.path.exists(_DRFP_PATH)}


# ── Step 1 真实 novel 检索：只凭底物 X 找相似反应 (不依赖产物) ──────────
# most_similar_reactions 需完整反应 A>>B(含产物), 真实 novel 场景只有 X 用不了;
# 本函数用主底物的 Morgan 指纹检索, 回溯到其所属反应作为 donor。
@lru_cache(maxsize=1)
def _substrate_fp_index():
    """构建 (reactions, MorganFPs); 底物库取自有酶背书的反应(rxn2enzymes keys)。"""
    from rdkit.Chem import AllChem
    import enzyme_lookup as el
    rxns = list(el._load_rxn2enzymes().keys())
    reactions, fps = [], []
    for rxn in rxns:
        if ">>" not in rxn:
            continue
        sub = rxn.split(">>", 1)[0].split(".")[0]  # 主底物=第一个反应物, 与 pipeline query 一致
        m = Chem.MolFromSmiles(sub)
        if m is None:
            continue
        reactions.append(rxn)
        fps.append(AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048))
    return reactions, fps


def retrieve_by_substrate(query_smiles: str, top_k: int = 10):
    """只凭底物 X 检索相似反应作 donor。返回 [(reaction, tanimoto), ...] 降序。

    用主底物 Morgan(r=2,2048bit) BulkTanimoto。适用于真实 novel 场景(无产物)。
    """
    from rdkit.Chem import AllChem, DataStructs
    qm = Chem.MolFromSmiles(query_smiles)
    if qm is None:
        return []
    qfp = AllChem.GetMorganFingerprintAsBitVect(qm, 2, nBits=2048)
    reactions, fps = _substrate_fp_index()
    if not fps:
        return []
    sims = DataStructs.BulkTanimotoSimilarity(qfp, fps)
    order = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:top_k]
    return [(reactions[i], float(sims[i])) for i in order]
