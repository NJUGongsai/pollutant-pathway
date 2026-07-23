# src/nodes/microbe_selection_node.py
# M5: 微生物推荐节点
# 根据排序后的酶，推荐携带该酶的功能微生物（适配污水环境）

import logging
from datetime import datetime, timezone

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord
from src.tools.microbe_recommender import recommend_microbes

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

    uncertainty_flags = list(state.uncertainty_flags)
    if not candidates:
        uncertainty_flags.append(
            "microbe_selection: 未获得 organism 映射（UniProt 不可达或 UID 无命中），微生物列表为空"
        )
        status = "empty_no_mapping"
    else:
        status = "uniprot_organism_mapping"

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
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "microbe_candidates": candidates,
        "uncertainty_flags": uncertainty_flags,
        "evidence_chain": state.evidence_chain + [evidence],
    }
