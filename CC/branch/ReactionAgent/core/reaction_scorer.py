"""Step 3 候选排序器：DRFP-酶集反应可信度 (M1 验证采纳, 见 DEV_PLAN §2.5)。

思路: 候选反应 X>>Y'ᵢ 现算 DRFP, 与"该酶 E 催化过的已知反应族"的 DRFP 取 max Tanimoto,
      衡量"这条候选反应是否像 E 平时会干的事"。真产物那条反应相似度最高 → 排第一。

判别力实测(54 多候选案例, vs 口袋打分/随机): top-1 77.8% vs 29%, 平均排名 1.36 vs 3.81。
该信号锚定酶的反应族且排除真答案本身, 不依赖真产物指纹, 可迁移到真实 novel 场景。

依赖: drfp (晨羽 enzymecage_py312 已装 0.3.7)。
"""
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Tuple

import numpy as np

# 与探针 step3a_drfp_probe.py 完全一致的默认配置
E_RXN_CAP = 40  # 每个酶最多取多少条已知反应参与相似度比较


@dataclass
class ScoredCandidate:
    product_smiles: str
    score: float                 # 与酶反应族的 max DRFP Tanimoto ∈ [0,1]
    best_match_reaction: str     # 酶反应族中与候选最相似的那条已知反应 (可解释证据)
    candidate: object = None     # 原始 CandidateProduct (若有)


@lru_cache(maxsize=100000)
def _drfp(rxn: str):
    """现算反应 DRFP → bool ndarray; 失败返回 None。带缓存避免重复编码。"""
    from drfp import DrfpEncoder
    try:
        fp = DrfpEncoder.encode([rxn])[0]
        return np.asarray(fp, dtype=bool)
    except Exception:
        return None


def _tanimoto(a, b) -> float:
    if a is None or b is None:
        return 0.0
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter) / float(union) if union else 0.0


def score_candidates(
    reactant_side: str,
    candidate_product_smiles: List[str],
    enzyme_reactions: List[str],
    exclude_reaction: Optional[str] = None,
    cap: int = E_RXN_CAP,
) -> List[ScoredCandidate]:
    """对候选产物按 DRFP-酶集可信度打分并降序排序。

    reactant_side:            查询反应物侧 SMILES (X 及 co-reactants, 以 '.' 连接), 作反应左侧。
    candidate_product_smiles: 候选产物 SMILES 列表 (每项可含多片段, '.' 连接)。
    enzyme_reactions:         该酶催化过的已知反应 SMILES 列表 (reactions_for_enzyme 的返回)。
    exclude_reaction:         需从酶反应族中剔除的反应 (防真答案泄漏); 真实 novel 场景传 None。
    """
    ref = [r for r in enzyme_reactions if r != exclude_reaction][:cap]
    ref_fps = [(r, _drfp(r)) for r in ref]
    ref_fps = [(r, f) for r, f in ref_fps if f is not None]

    scored = []
    for prod in candidate_product_smiles:
        cand_fp = _drfp(f"{reactant_side}>>{prod}")
        best_s, best_r = 0.0, ""
        for r, rf in ref_fps:
            s = _tanimoto(cand_fp, rf)
            if s > best_s:
                best_s, best_r = s, r
        scored.append(ScoredCandidate(product_smiles=prod, score=best_s, best_match_reaction=best_r))
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored


def rank_candidates(
    reactant_side: str,
    candidates: List[object],
    enzyme_uniprot: str,
    exclude_reaction: Optional[str] = None,
    cap: int = E_RXN_CAP,
) -> List[ScoredCandidate]:
    """高层入口: 给定候选(CandidateProduct 列表)+ 催化酶 UniProt, 返回排序后的 ScoredCandidate。

    自动经 enzyme_lookup 取该酶的反应族。候选无 product_smiles 属性时按 str 处理。
    """
    import enzyme_lookup as el
    enzyme_reactions = el.reactions_for_enzyme(enzyme_uniprot)
    prods = [getattr(c, "product_smiles", c) for c in candidates]
    scored = score_candidates(reactant_side, prods, enzyme_reactions, exclude_reaction, cap)
    # 回填原始候选对象 (按 product_smiles 对齐)
    by_smiles = {getattr(c, "product_smiles", c): c for c in candidates}
    for sc in scored:
        sc.candidate = by_smiles.get(sc.product_smiles)
    return scored
