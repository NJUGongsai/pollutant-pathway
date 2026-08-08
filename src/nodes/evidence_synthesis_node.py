# src/nodes/evidence_synthesis_node.py
# M5: 证据链合成节点
# 汇总全流程证据链，生成结构化最终报告

import logging
from datetime import datetime, timezone

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord

logger = logging.getLogger(__name__)


def evidence_synthesis_node(state: EnzymeCrewState) -> dict:
    """
    EvidenceSynthesisNode (M5): 证据链最终合成
    
    汇总所有节点的 evidence_chain，生成结构化报告:
    - 底物来源与解析方式
    - 反应检索/预测路线
    - Pool 构造策略 (B/C)
    - EnzymeCAGE 排序结果
    - LLM 重排序理由 (如有)
    - 微生物推荐及性状匹配
    - 不确定性声明
    
    输出: state.final_summary
    """
    logger.info("[EvidenceSynthesisNode] Synthesizing evidence chain...")

    # 从证据链抽取各阶段关键 provenance（确定性拼接，不调 LLM）
    def _evidence_data(stage: str) -> dict:
        for rec in reversed(state.evidence_chain):
            if rec.stage == stage:
                return rec.data or {}
        return {}

    pool_ev = _evidence_data("pool")
    trait_ev = _evidence_data("trait")

    # 占位: 结构化文本拼接
    lines = []
    lines.append("# EnzymeCrew 分析报告")
    lines.append(f"\n## 查询\n{state.user_query}")

    if state.substrate_info:
        lines.append(f"\n## 底物\n- SMILES: `{state.substrate_info.substrate_smiles}`")
        lines.append(f"- 来源: {state.substrate_info.source}")

    if state.candidate_reactions:
        lines.append(f"\n## 候选反应 ({len(state.candidate_reactions)} 个)")
        for i, rxn in enumerate(state.candidate_reactions[:3], 1):
            lines.append(f"  {i}. `{rxn.reaction_smiles[:50]}...` (score={rxn.similarity_score})")

    if state.pool_route_used:
        lines.append(f"\n## 酶 Pool\n- 路线: {state.pool_route_used}")
        lines.append(f"- Pool 大小: {state.pool_size}")
        # route provenance: B/C sizes + 决策理由
        if pool_ev:
            lines.append(
                f"- 路线组成: |B|={pool_ev.get('pool_b_size', '?')}, "
                f"|C|={pool_ev.get('pool_c_size', '?')}"
            )
            if pool_ev.get("route_decision_reason"):
                lines.append(f"- 决策理由: {pool_ev['route_decision_reason']}")

    if state.ranked_enzymes:
        lines.append(f"\n## 排序结果 (Top-5)")
        for e in state.ranked_enzymes[:5]:
            lines.append(f"  - {e.uid}: score={e.score:.4f} (rank={e.rank})")

    if state.reranked_enzymes:
        lines.append(f"\n## LLM 重排序 (Top-5)")
        for e in state.reranked_enzymes[:5]:
            lines.append(f"  - {e.uid}: rerank={e.reranked_rank} ({e.rerank_rationale[:40]})")

    if state.microbe_candidates:
        lines.append(f"\n## 推荐微生物 ({len(state.microbe_candidates)} 个，单酶→菌映射)")
        for m in state.microbe_candidates[:5]:
            tax = f"taxID:{m.tax_id}" if m.tax_id else "taxID:?"
            ev = m.evidence_level or "未知"
            lines.append(
                f"  - {m.organism_name} ({tax}, enzyme: {m.enzyme_uid}, 来源: {m.source_db}, 证据: {ev})"
            )

    # OrganismAggregator 聚合结果（菌→支持酶集合，三层证据不坠缩）
    if state.organism_candidates:
        lines.append(f"\n## 候选菌聚合 ({len(state.organism_candidates)} 个，按支持酶数降序、ncbi_taxon_id 升序 tie-break（MT-D3）)")
        for o in state.organism_candidates[:5]:
            uids = [se.uid for se in o.supporting_enzymes]
            scores = [se.score for se in o.supporting_enzymes]
            # MT-D2 原始维度透传（reviewed 状态 / annotation score / protein existence / KEGG multiplicity），
            # 不折算 confidence float。
            src_dims = []
            for p in o.per_enzyme_source_provenance:
                up = p.uniprot_reviewed
                kegg = p.kegg
                src_dims.append(
                    f"{p.enzyme_uid}[reviewed"
                    + (f",annot={up.annotation_score},pe={up.protein_existence}" if up else "")
                    + (f",kegg={kegg.multiplicity}/{kegg.state}" if kegg else "")
                    + "]"
                )
            lines.append(
                f"  - #{o.default_order_rank} {o.organism_name} (taxID:{o.ncbi_taxon_id}): "
                f"支持酶 {o.supporting_enzyme_count} 个 {uids}, "
                f"酶分={scores}, "
                f"原始证据={src_dims}"
            )
        if state.organism_candidates[0].aggregation_notes:
            lines.append(f"  > 聚合假设: {state.organism_candidates[0].aggregation_notes}")

    # 选菌层（D6 有界理由；MT-D3 名次不变，LLM 仅解释、不重排/不增删）
    if state.organism_recommendations:
        lines.append(
            f"\n## 选菌推荐 ({len(state.organism_recommendations)} 个，D6 有界理由；M4b/M4c 未授权，无 trait_score 融合)"
        )
        for r in state.organism_recommendations[:5]:
            lines.append(
                f"  - #{r.default_order_rank} {r.organism_name} (taxID:{r.ncbi_taxon_id}) "
                f"[{r.recommendation_status}]：{r.rationale}"
            )
            if r.cited_evidence:
                lines.append(f"    引用 evidence({len(r.cited_evidence)}): {r.cited_evidence}")
            if r.uncertainty_flags:
                lines.append(f"    不确定: {r.uncertainty_flags}")

    # 性状筛选状态（M4b 锁定说明）
    if trait_ev:
        lines.append("\n## 性状筛选 (M4b)")
        lines.append(f"- 状态: {trait_ev.get('status', 'unknown')}")
        lines.append(f"- 模式: {trait_ev.get('filter_mode', 'n/a')}")
        if trait_ev.get("lock_reason"):
            lines.append(f"- 锁定原因: {trait_ev['lock_reason']}")

    if state.uncertainty_flags:
        lines.append(f"\n## ⚠️ 不确定性\n- " + "\n- ".join(state.uncertainty_flags))

    lines.append(f"\n## 证据链\n- 共 {len(state.evidence_chain)} 条记录")

    summary = "\n".join(lines)

    evidence = EvidenceRecord(
        stage="synthesis",
        action="evidence_chain_synthesized",
        data={
            "total_evidence_records": len(state.evidence_chain),
            "summary_length": len(summary),
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "final_summary": summary,
        "evidence_chain": state.evidence_chain + [evidence],
    }
