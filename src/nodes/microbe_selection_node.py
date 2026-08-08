# src/nodes/microbe_selection_node.py
# M5: 微生物推荐节点
# 根据排序后的酶，推荐携带该酶的功能微生物（适配污水环境）

import logging
from datetime import datetime, timezone

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord
from src.tools.microbe_recommender import map_enzyme_hosts, microbe_candidates_from_provenance
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

    # 单次网络查询：酶 UID → reviewed UniProt 宿主 + KEGG multiplicity（原始证据维度透传，MT-D1/D2）
    provenance_map = map_enzyme_hosts(top_uids)
    candidates = microbe_candidates_from_provenance(provenance_map, top_uids, environment="wastewater")

    # OrganismAggregator（框架 §3.3）：按 reviewed 宿主的 NCBI taxon 聚合酶排序。
    # 组内 (rank, uid) 排序键与支持酶 score/rank/CI 取自 ranked_enzymes（模型真实排序，同源）。
    organism_candidates = aggregate_organisms(state.ranked_enzymes or [], provenance_map)

    uncertainty_flags = list(state.uncertainty_flags)
    if not candidates:
        uncertainty_flags.append(
            "microbe_selection: 未获得 organism 映射（UniProt 不可达或 UID 无命中），微生物列表为空"
        )
        status = "empty_no_mapping"
    else:
        status = "uniprot_organism_mapping"
        # MT-D2/D3（2026-07-18 裁定）已实装：排序=支持酶数降序+taxid 升序，不产 confidence float。

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
                    "ncbi_taxon_id": o.ncbi_taxon_id,
                    "default_order_rank": o.default_order_rank,
                    "supporting_enzyme_count": o.supporting_enzyme_count,
                    "supporting_enzymes": [se.uid for se in o.supporting_enzymes],
                    "per_enzyme_source_provenance": [
                        {
                            "enzyme_uid": p.enzyme_uid,
                            "reviewed_taxon": (
                                p.uniprot_reviewed.ncbi_taxon_id if p.uniprot_reviewed else None
                            ),
                            "annotation_score": (
                                p.uniprot_reviewed.annotation_score if p.uniprot_reviewed else None
                            ),
                            "protein_existence": (
                                p.uniprot_reviewed.protein_existence if p.uniprot_reviewed else None
                            ),
                            "kegg_multiplicity": (p.kegg.multiplicity if p.kegg else None),
                            "kegg_state": (p.kegg.state if p.kegg else None),
                        }
                        for p in o.per_enzyme_source_provenance
                    ],
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
