# src/utils/organism_aggregator.py
# OrganismAggregator（无状态函数，框架 §3.3）
#
# 职责：把「酶排序（RankedEnzyme）+ 酶→多源原始证据（EnzymeSourceProvenance）」
#       按 reviewed 宿主的 NCBI taxon 聚合成「菌 → 支持酶集合」的 OrganismCandidate 列表。
#
# 属 M4a 授权范围（酶→菌聚合），不涉及 metaTraits 性状（M4b，未立项，见 trait_filter_node）。
#
# 【严格对齐学生权威实现】microbe_crew/tools/organism_aggregator.py（15 tests passed），
#   规则源 = TEACHER_REPLY_MTD5_ACCEPTED_AND_MTD1_D8_DECISIONS_2026-07-16.md
#   + 学生 07-27 最终回应稿（DECIDED_AND_IMPLEMENTED FOR V1）：
#   - MT-D3：排序主键 = supporting-enzyme count 降序 + NCBI taxon ID 数字升序 tie-break。
#     （已裁定：TEACHER_REPLY_M3_P1_UNLOCK_...2026-07-21.md §MT-TQ-01 明确采纳 NCBI taxon ID
#      数字升序、不切换为 enzyme UID 升序——理由：taxon ID 是聚合后唯一生产主键，UID tie-break
#      存在"用哪条 UID 代表 taxon 组"的二义性。早期 07-16 裁定文的 "UID 升序" 表述已被 §MT-TQ-01
#      supersede；文档—代码口径一致，无遗留冲突。）
#   - 输入酶排序按 uid 首见去重；组内成员按 (rank, uid) 排序；排序后赋 1-based default_order_rank。
#   - 仅按 reviewed 宿主的 ncbi_taxon_id 分组；无 reviewed 映射的酶直接丢弃（无 organism_name 回退）。
#   - MT-D2：不输出 confidence float；原始证据维度经 per_enzyme_source_provenance 透传、不坠缩为分数。

import logging
from typing import Dict, List, Tuple

from src.schemas.evidence import (
    EnzymeSourceProvenance,
    OrganismCandidate,
    RankedEnzyme,
    SupportingEnzyme,
)

logger = logging.getLogger(__name__)


def aggregate_organisms(
    ranked_enzymes: List[RankedEnzyme],
    provenance_map: Dict[str, EnzymeSourceProvenance],
) -> List[OrganismCandidate]:
    """按 reviewed 宿主的 NCBI taxon 聚合酶排序 → OrganismCandidate（对齐学生 aggregate_organisms）。

    Args:
        ranked_enzymes: EnzymeCAGE 真实排序（RankedEnzyme{uid,score,rank,ensemble_ci}），
                        提供组内 (rank, uid) 排序键及支持酶的原始 score/rank/CI（不折算）。
        provenance_map: {enzyme_uid: EnzymeSourceProvenance}，来自 microbe_recommender.map_enzyme_hosts；
                        含 reviewed UniProt 宿主 + KEGG multiplicity + source_errors 原始维度。

    Returns:
        List[OrganismCandidate]，按 MT-D3：supporting-enzyme count 降序 + ncbi_taxon_id 升序。
        无 reviewed 宿主映射的酶不纳入任何候选（无 name 回退）。
    """
    if not ranked_enzymes:
        return []

    # 酶 uid 首见去重（对齐学生 first_ranked 语义）
    first_ranked: Dict[str, RankedEnzyme] = {}
    for ranked in ranked_enzymes:
        if ranked.uid not in first_ranked:
            first_ranked[ranked.uid] = ranked

    # 分组：仅 reviewed 宿主的 ncbi_taxon_id -> [(RankedEnzyme, EnzymeSourceProvenance)]
    grouped: Dict[int, List[Tuple[RankedEnzyme, EnzymeSourceProvenance]]] = {}
    dropped_no_reviewed = 0
    for uid, ranked in first_ranked.items():
        prov = provenance_map.get(uid)
        if prov is None or prov.uniprot_reviewed is None:
            # 无 reviewed 宿主映射 → 无 NCBI taxon 可并入分组（MT-D1：unreviewed 不纳入 v1）
            dropped_no_reviewed += 1
            continue
        taxon_id = prov.uniprot_reviewed.ncbi_taxon_id
        grouped.setdefault(taxon_id, []).append((ranked, prov))

    candidates: List[OrganismCandidate] = []
    for taxon_id, members in grouped.items():
        # 组内成员排序：(rank, uid)
        members.sort(key=lambda item: (item[0].rank, item[0].uid))

        name_variants: List[str] = []
        for _, prov in members:
            name = prov.uniprot_reviewed.scientific_organism_name
            if name not in name_variants:
                name_variants.append(name)

        supporting = [
            SupportingEnzyme(
                uid=ranked.uid,
                score=ranked.score,
                rank=ranked.rank,
                ensemble_ci=ranked.ensemble_ci,
            )
            for ranked, _ in members
        ]
        per_enzyme_provenance = [
            EnzymeSourceProvenance(
                enzyme_uid=ranked.uid,
                uniprot_reviewed=prov.uniprot_reviewed,
                kegg=prov.kegg,
                source_errors=prov.source_errors,
            )
            for ranked, prov in members
        ]

        candidates.append(
            OrganismCandidate(
                organism_uid=str(taxon_id),
                taxonomy_namespace="NCBI_taxon",
                ncbi_taxon_id=taxon_id,
                organism_name=name_variants[0],
                organism_name_variants=name_variants,
                supporting_enzymes=supporting,
                supporting_enzyme_count=len(supporting),
                per_enzyme_source_provenance=per_enzyme_provenance,
                default_order_rank=0,
            )
        )

    # MT-D3：supporting-enzyme count 降序（主）→ ncbi_taxon_id 数字升序（tie-break）
    candidates.sort(key=lambda c: (-c.supporting_enzyme_count, c.ncbi_taxon_id))
    for order_rank, cand in enumerate(candidates, start=1):
        cand.default_order_rank = order_rank

    # 聚合说明（导师侧可观测性附加，不影响排序/语义；学生 schema 无此项）
    notes_parts = [
        "MT-D3：supporting-enzyme count 降序 + ncbi_taxon_id 升序 tie-break",
        "MT-D2：不产出 confidence float，原始证据维度经 per_enzyme_source_provenance 透传",
    ]
    if dropped_no_reviewed:
        notes_parts.append(
            f"丢弃无 reviewed 宿主映射的酶 {dropped_no_reviewed} 个（无 organism_name 回退）"
        )
    agg_notes = "；".join(notes_parts)
    for cand in candidates:
        cand.aggregation_notes = agg_notes

    logger.info(
        f"[organism_aggregator] 聚合 {len(first_ranked)} 个去重酶 "
        f"→ {len(candidates)} 个候选菌（MT-D3 排序；丢弃无 reviewed {dropped_no_reviewed} 个）"
    )
    return candidates
