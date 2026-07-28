# src/nodes/organism_selection_node.py
# M5: 选菌层节点（MicrobeSelectionAgent 有界理由层）
#
# 授权边界（学生 07-27 §4.6 / D6）：M4b TraitFilterLayer 与 M4c 完整决策层 NOT AUTHORIZED，
#   当前仅允许「按既有聚合主键（MT-D3）呈现 Top-K + 生成有界理由」。本节点严格落在此范围内：
#   - 消费 OrganismAggregator 产出的 organism_candidates（已 MT-D3 确定性排序）。
#   - LLM 只生成有界推荐理由，不重排、不增删候选池成员（确定性主链路不受 LLM 幻觉影响）。
#   - 不依赖 trait_score（M4b 锁定），不产出 total_score。
#
# D6 硬约束（写入 prompt + 代码兜底）：
#   - 禁止绕过确定性约束；每条 recommended 至少引用 2 条可追溯 evidence（不足则降级）。
#   - 证据不足 → insufficient_evidence / unknown；冲突 / no_robust_majority → uncertainty_flags。
#   - 禁止把 soft evidence 改写成 hard exclusion。
#
# 【硬依赖不可降级】（用户裁定）：选菌 LLM 综合判断是核心价值，不允许静默降级。
#   LLM 不可用（无 key / 超时 / 限流 / 断网 / 响应不合法）时必须显式 fail_closed 报错，
#   绝不按聚合分直通透传（禁止"无面试录取"）。此约束仅针对选菌层。

import json
import logging
import re
from datetime import datetime, timezone

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord, OrganismRecommendation
from src.utils.llm import call_dashscope

logger = logging.getLogger(__name__)

TOP_K = 5

SELECTION_SYSTEM_PROMPT = """你是微生物工程专家，负责对已确定性排序的候选宿主菌生成有界推荐理由。

严格约束（违反即无效）:
1. 候选菌集合与其名次（default_order_rank）由上游确定性聚合给定，你【不得】增删候选、【不得】改变名次。
2. 你只能引用输入中已列出的 evidence（酶支持数、EnzymeCAGE 分/rank、UniProt reviewed 状态/annotation_score/protein_existence、KEGG multiplicity）。禁止编造任何未提供的生物学事实或数值。
3. 每条 recommendation_status="recommended" 必须引用【至少 2 条】可追溯 evidence（写入 cited_evidence）。证据不足时置 "insufficient_evidence"；信息缺失置 "unknown"。
4. 证据冲突或无稳健多数时，写入 uncertainty_flags，不要强行下正向结论。
5. 全部为参考性 soft 证据，禁止把 soft evidence 改写成 hard exclusion（不得声称"必须排除某菌"）。

只输出纯 JSON 数组，不要 markdown 代码块、不要多余解释:
[{"organism_uid": "...", "recommendation_status": "recommended|insufficient_evidence|unknown", "cited_evidence": ["...", "..."], "rationale": "...", "uncertainty_flags": ["..."]}, ...]
"""


def _extract_json_array(text: str) -> list:
    """从 LLM 文本响应稳健抽取 JSON 数组（容忍 ```json 围栏与前后噪声）。"""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        return json.loads(cleaned[start : end + 1])
    raise ValueError("响应中未找到合法 JSON 数组")


def _candidate_evidence_lines(cand) -> list:
    """把候选菌的原始证据维度铺平成可追溯 evidence 文本（供 LLM 引用 + 证据链留痕）。"""
    lines = [f"supporting_enzyme_count={cand.supporting_enzyme_count}"]
    for se in cand.supporting_enzymes:
        ci = f",ensemble_ci={se.ensemble_ci}" if se.ensemble_ci is not None else ""
        lines.append(f"enzyme {se.uid}: EnzymeCAGE score={se.score},rank={se.rank}{ci}")
    for p in cand.per_enzyme_source_provenance:
        up = p.uniprot_reviewed
        if up is not None:
            lines.append(
                f"{p.enzyme_uid} UniProt reviewed: annotation_score={up.annotation_score},"
                f"protein_existence={up.protein_existence},taxon={up.ncbi_taxon_id}"
            )
        if p.kegg is not None:
            lines.append(
                f"{p.enzyme_uid} KEGG: multiplicity={p.kegg.multiplicity},state={p.kegg.state}"
            )
    return lines


def _build_prompt(top_candidates) -> str:
    lines = ["候选宿主菌（已按 MT-D3 确定性排序，名次固定不可改）:", ""]
    for c in top_candidates:
        lines.append(f"[#{c.default_order_rank}] organism_uid={c.organism_uid} name={c.organism_name} taxID={c.ncbi_taxon_id}")
        for ev in _candidate_evidence_lines(c):
            lines.append(f"    - {ev}")
        lines.append("")
    lines.append(f"请对上述 {len(top_candidates)} 个候选菌逐一生成有界推荐理由，输出 JSON 数组。")
    return "\n".join(lines)


def organism_selection_node(state: EnzymeCrewState) -> dict:
    """
    OrganismSelectionNode (M5 选菌层): 对 MT-D3 排序后的候选菌生成 D6 有界推荐理由。

    输入: state.organism_candidates（OrganismAggregator 输出，已确定性排序）
    输出: state.organism_recommendations

    容错语义:
    - 无候选菌（上游 UniProt 不可达 / 无 reviewed 宿主）→ 优雅跳过，不视作 LLM 失败。
    - 有候选菌但 LLM 不可用/响应不合法 → 硬依赖，显式 fail_closed 报错（不静默透传）。
    """
    if not state.organism_candidates:
        logger.warning("[OrganismSelectionNode] 无候选菌，跳过选菌层（非 LLM 失败）")
        return {
            "uncertainty_flags": state.uncertainty_flags
            + ["organism_selection: 无候选菌可选（上游未产出 reviewed 宿主），选菌层跳过"]
        }

    top_candidates = state.organism_candidates[:TOP_K]
    by_uid = {c.organism_uid: c for c in top_candidates}
    logger.info(f"[OrganismSelectionNode] 选菌层对 {len(top_candidates)} 个候选菌生成有界理由（LLM 硬依赖）...")

    # ── 硬依赖：LLM 不可用即显式失败，绝不降级 ──
    try:
        raw = call_dashscope(
            prompt=_build_prompt(top_candidates),
            system_prompt=SELECTION_SYSTEM_PROMPT,
            node_name="organism_selection_node",
        )
        items = _extract_json_array(raw)
        if not isinstance(items, list) or not items:
            raise ValueError("LLM 响应未产出任何候选菌推荐")
    except Exception as e:  # noqa: BLE001 — 选菌层 LLM 硬依赖，失败必须显式报错
        msg = f"选菌层 LLM 硬依赖不可用/响应不合法，显式 fail_closed（不降级透传）: {str(e)[:200]}"
        logger.error(f"[OrganismSelectionNode] {msg}")
        return {
            "error": msg,
            "fail_closed": True,
            "uncertainty_flags": state.uncertainty_flags + [f"organism_selection fail_closed: {str(e)[:120]}"],
        }

    # ── 解析 + 代码兜底（LLM 只能标注给定候选，不得增删/改名次；D6 ≥2 evidence 强制）──
    annotated = {}
    for it in items:
        uid = str(it.get("organism_uid", "")).strip()
        if uid not in by_uid or uid in annotated:
            continue  # 幻觉 / 越界 / 重复 uid 一律丢弃
        annotated[uid] = it

    uncertainty_flags = list(state.uncertainty_flags)
    recommendations = []
    for c in top_candidates:  # 保持 MT-D3 确定性顺序与成员完整
        it = annotated.get(c.organism_uid)
        if it is None:
            # LLM 未覆盖该候选：不丢弃（成员由确定性聚合决定），置 unknown 并留痕
            uncertainty_flags.append(f"organism_selection: {c.organism_uid} 未被 LLM 覆盖，置 unknown")
            recommendations.append(
                OrganismRecommendation(
                    organism_uid=c.organism_uid,
                    organism_name=c.organism_name,
                    ncbi_taxon_id=c.ncbi_taxon_id,
                    default_order_rank=c.default_order_rank,
                    supporting_enzyme_count=c.supporting_enzyme_count,
                    recommendation_status="unknown",
                    cited_evidence=[],
                    rationale="[uncovered] LLM 未覆盖该候选，按确定性成员保留并置 unknown",
                    uncertainty_flags=["llm_uncovered"],
                )
            )
            continue

        status = str(it.get("recommendation_status", "unknown")).strip()
        if status not in {"recommended", "insufficient_evidence", "unknown"}:
            status = "unknown"
        cited = [str(x).strip() for x in (it.get("cited_evidence") or []) if str(x).strip()]
        flags = [str(x).strip() for x in (it.get("uncertainty_flags") or []) if str(x).strip()]
        rationale = str(it.get("rationale", "")).strip()[:800] or "(no rationale)"

        # D6 兜底：recommended 必须 ≥2 条可追溯 evidence，不足则降级
        if status == "recommended" and len(cited) < 2:
            flags.append("d6_downgrade: recommended 引用 evidence 不足 2 条，降级为 insufficient_evidence")
            status = "insufficient_evidence"

        recommendations.append(
            OrganismRecommendation(
                organism_uid=c.organism_uid,
                organism_name=c.organism_name,
                ncbi_taxon_id=c.ncbi_taxon_id,
                default_order_rank=c.default_order_rank,
                supporting_enzyme_count=c.supporting_enzyme_count,
                recommendation_status=status,
                cited_evidence=cited,
                rationale=rationale,
                uncertainty_flags=flags,
            )
        )

    recommended_n = sum(1 for r in recommendations if r.recommendation_status == "recommended")
    evidence = EvidenceRecord(
        stage="microbe",
        action="organism_selection_bounded_rationale",
        data={
            "input_candidates": len(top_candidates),
            "recommendations": len(recommendations),
            "recommended": recommended_n,
            "authorization": "M4a bounded rationale only; M4b/M4c NOT AUTHORIZED",
            "top3": [
                {
                    "rank": r.default_order_rank,
                    "organism": r.organism_name,
                    "status": r.recommendation_status,
                    "cited_evidence_count": len(r.cited_evidence),
                }
                for r in recommendations[:3]
            ],
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "organism_recommendations": recommendations,
        "uncertainty_flags": uncertainty_flags,
        "evidence_chain": state.evidence_chain + [evidence],
    }
