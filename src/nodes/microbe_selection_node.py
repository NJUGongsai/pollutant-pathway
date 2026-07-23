# src/nodes/microbe_selection_node.py
# M5: 微生物推荐节点
# 根据排序后的酶，推荐携带该酶的功能微生物（适配污水环境）

import logging
from datetime import datetime, timezone

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord
from src.tools.microbe_recommender import recommend_microbes
from src.utils.organism_aggregator import aggregate_organisms

logger = logging.getLogger(__name__)


def microbe_selection_node(state: EnzymeCrewState) -> dict:
    """
    MicrobeSelectionNode (M5): 酶 → 来源生物映射（M4a 授权范围）

    ⚠️ OOL 风险较高 —— 缓解措施:
    - 只对 Top-5 酶查询
    - 按需查询 UniProt，不预注入全量信息

    输入: state.reranked_enzymes（优先）或 state.ranked_enzymes
    输出: state.microbe_candidates

    数据源: UniProt REST（UID → organism）。metaTraits 污水性状筛选属 M4b，
    未立项前不在此做（见 trait_filter_node）。网络不可用时诚实降级为空列表，
    不 fail-closed（微生物映射是增强项，非核心链路）。
    """
    # 确定酶列表来源：重排优先
    if state.reranked_enzymes:
        top_uids = [e.uid for e in state.reranked_enzymes[:5]]
        enzyme_source = "reranked_enzymes"
    elif state.ranked_enzymes:
        top_uids = [e.uid for e in state.ranked_enzymes[:5]]
        enzyme_source = "ranked_enzymes"
    else:
        logger.warning("[MicrobeSelectionNode] No enzymes to map, skipping")
        return {}

    logger.info(f"[MicrobeSelectionNode] Mapping {len(top_uids)} enzymes to organisms...")

    candidates = recommend_microbes(top_uids, environment="wastewater", top_k=len(top_uids))

    # OrganismAggregator（框架 §3.3）：将「单酶→菌」映射按候选菌聚合。
    # enzyme_score 取自 ranked_enzymes（模型真实排序分）；CI 同源。
    enzyme_scores = {}
    enzyme_cis = {}
    for e in (state.ranked_enzymes or []):
        enzyme_scores[e.uid] = e.score
        if e.ensemble_ci is not None:
            enzyme_cis[e.uid] = e.ensemble_ci
    organism_candidates = aggregate_organisms(candidates, enzyme_scores, enzyme_cis)

    uncertainty_flags = list(state.uncertainty_flags)
    if not candidates:
        uncertainty_flags.append(
            "microbe_selection: 未获得 organism 映射（UniProt 不可达或 UID 无命中），微生物列表为空"
        )
        status = "empty_no_mapping"
    else:
        status = "uniprot_organism_mapping"
        # D2/D3 降级假设显式留痕（聚合层）
        uncertainty_flags.append(
            "organism_aggregator: cumulative_score 基于临时 confidence 折算（D2 未定）"
            "与 tax_id 主键聚合（D3 未定），排序仅供参考，待学生定稿"
        )

    evidence = EvidenceRecord(
        stage="microbe",
        action="microbe_selection",
        data={
            "enzyme_source": enzyme_source,
            "input_enzyme_count": len(top_uids),
            "output_candidates": len(candidates),
            "source_db": "UniProt",
            "status": status,
            "sample_organisms": [c.organism_name for c in candidates[:3]],
            # 聚合层三层证据可见（原始数据优先原则）
            "aggregated_organisms": len(organism_candidates),
            "top_organisms": [
                {
                    "organism": o.organism_name,
                    "tax_id": o.organism_uid,
                    "cumulative_score": o.cumulative_score,
                    "supporting_enzymes": o.supporting_enzymes,
                    "evidence_levels": o.evidence_levels,
                }
                for o in organism_candidates[:3]
            ],
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "microbe_candidates": candidates,
        "organism_candidates": organism_candidates,
        "uncertainty_flags": uncertainty_flags,
        "evidence_chain": state.evidence_chain + [evidence],
    }
