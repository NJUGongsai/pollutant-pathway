# src/utils/organism_aggregator.py
# OrganismAggregator（无状态函数，框架 §3.3）
#
# 职责：把 MicrobeSelectionNode 产出的「单酶 → 菌」事实映射（List[MicrobeCandidate]）
#       按候选菌聚合成「菌 → 支持酶集合」的 OrganismCandidate 列表，供下游选菌/性状层排序。
#
# 属 M4a 授权范围（酶→菌聚合），不涉及 metaTraits 性状（M4b，未立项，见 trait_filter_node）。
#
# 纪律：D2（confidence 归一化）/ D3（聚合主键）学生尚未定稿。
#   - 本实现采用**有据可查的降级默认**并在 aggregation_notes / uncertainty 中显式标注：
#       * D3 聚合主键：优先 tax_id，缺失时回退 organism_name（记录于 notes）
#       * D2 confidence：来自 UniProt evidence_level 折算（reviewed=1.0 / unreviewed=0.5 / 未知=0.5）
#   - 绝不编造 confidence；缺失一律走保守默认并留痕。

import logging
from typing import Dict, List, Optional, Tuple

from src.schemas.evidence import MicrobeCandidate, OrganismCandidate

logger = logging.getLogger(__name__)

_DEFAULT_CONFIDENCE = 0.5  # 与 microbe_recommender._DEFAULT_CONFIDENCE 对齐


def _organism_key(cand: MicrobeCandidate) -> Tuple[str, bool]:
    """聚合主键（D3 未定，降级策略）：tax_id 优先，缺失回退 organism_name。

    返回 (key, used_name_fallback)。
    """
    if cand.tax_id is not None:
        return str(cand.tax_id), False
    return cand.organism_name, True


def _avg_ci(cis: List[Optional[Tuple[float, float]]]) -> Optional[Tuple[float, float]]:
    """支持酶 CI 的简单平均；无有效 CI 时返回 None（不编造区间）。"""
    valid = [ci for ci in cis if ci is not None]
    if not valid:
        return None
    lo = sum(ci[0] for ci in valid) / len(valid)
    hi = sum(ci[1] for ci in valid) / len(valid)
    return (round(lo, 4), round(hi, 4))


def aggregate_organisms(
    microbe_candidates: List[MicrobeCandidate],
    enzyme_scores: Dict[str, float],
    enzyme_cis: Optional[Dict[str, Tuple[float, float]]] = None,
) -> List[OrganismCandidate]:
    """按候选菌聚合 MicrobeCandidate → OrganismCandidate。

    Args:
        microbe_candidates: MicrobeSelectionNode 的「酶→菌」事实映射列表。
        enzyme_scores: {enzyme_uid: EnzymeCAGE score}，来自 ranked_enzymes（模型真实排序分）。
        enzyme_cis:    {enzyme_uid: (lo, hi)}，可选，来自 ranked_enzymes.ensemble_ci。

    Returns:
        List[OrganismCandidate]，按 cumulative_score 降序。
        cumulative_score = Σ(enzyme_score × confidence)；enzyme_score 缺失按 0 计并留痕。
    """
    if not microbe_candidates:
        return []

    enzyme_cis = enzyme_cis or {}

    # 分组：key -> 聚合中间态
    groups: Dict[str, dict] = {}
    used_name_fallback = False

    for cand in microbe_candidates:
        key, is_name_fallback = _organism_key(cand)
        used_name_fallback = used_name_fallback or is_name_fallback

        g = groups.setdefault(
            key,
            {
                "organism_uid": key,
                "organism_name": cand.organism_name,
                "supporting_enzymes": [],
                "cumulative_score": 0.0,
                "cis": [],
                "evidence_levels": [],
                "missing_score_uids": [],
            },
        )

        conf = cand.confidence if cand.confidence is not None else _DEFAULT_CONFIDENCE
        score = enzyme_scores.get(cand.enzyme_uid)
        if score is None:
            g["missing_score_uids"].append(cand.enzyme_uid)
            score = 0.0

        if cand.enzyme_uid not in g["supporting_enzymes"]:
            g["supporting_enzymes"].append(cand.enzyme_uid)
        g["cumulative_score"] += score * conf
        g["cis"].append(enzyme_cis.get(cand.enzyme_uid))
        g["evidence_levels"].append(cand.evidence_level or "unknown")

    candidates: List[OrganismCandidate] = []
    for g in groups.values():
        notes_parts = [
            "D3 聚合主键=tax_id" + ("（部分菌缺 tax_id，已回退 organism_name）" if used_name_fallback else ""),
            "D2 confidence 来自 UniProt evidence_level 折算（临时默认，待学生定稿）",
        ]
        if g["missing_score_uids"]:
            notes_parts.append(
                f"以下支持酶未在 ranked_enzymes 中找到打分，按 0 计入: {g['missing_score_uids']}"
            )
        candidates.append(
            OrganismCandidate(
                organism_uid=g["organism_uid"],
                organism_name=g["organism_name"],
                supporting_enzymes=g["supporting_enzymes"],
                cumulative_score=round(g["cumulative_score"], 4),
                avg_ensemble_ci=_avg_ci(g["cis"]),
                evidence_levels=g["evidence_levels"],
                aggregation_notes="；".join(notes_parts),
            )
        )

    candidates.sort(key=lambda c: c.cumulative_score, reverse=True)
    logger.info(
        f"[organism_aggregator] 聚合 {len(microbe_candidates)} 条酶→菌映射 "
        f"→ {len(candidates)} 个候选菌"
    )
    return candidates
