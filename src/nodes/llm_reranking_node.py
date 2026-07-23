# src/nodes/llm_reranking_node.py
# M5: LLM 重排序节点
# 对 EnzymeCAGE 排序结果进行 LLM 后处理，结合反应上下文重排

import json
import logging
import re
from datetime import datetime, timezone

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord, RerankedEnzyme
from src.utils.llm import call_dashscope

logger = logging.getLogger(__name__)

RERANK_SYSTEM_PROMPT = """你是酶工程专家。给定一组候选酶及其模型排序分数，结合反应背景和污水处理场景，对 Top-N 酶进行重新排序。

评估维度:
1. 催化效率 (模型分数已提供)
2. 环境适应性 (pH/温度/离子强度)
3. 蛋白稳定性 (已有文献证据)
4. 底物特异性匹配度

严格要求:
- 只能对给定 UID 重排，不得新增/删除 UID
- 不得编造 UID 不存在的生物学事实
- 输出必须是纯 JSON 数组，不要 markdown 代码块、不要多余解释

输出 JSON 数组:
[{"uid": "P12345", "reranked_rank": 1, "rerank_rationale": "...", "confidence": 0.8}, ...]
"""


def _extract_json_array(text: str) -> list:
    """从 LLM 文本响应中稳健抽取 JSON 数组（容忍 ```json 围栏与前后噪声）。"""
    # 去掉 markdown 代码围栏
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    # 优先直接解析
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    # 回退：截取第一个 '[' 到最后一个 ']'
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        return json.loads(cleaned[start : end + 1])
    raise ValueError("响应中未找到合法 JSON 数组")


def _build_prompt(reaction_smiles: str, top_n) -> str:
    lines = [f"目标反应 SMILES: {reaction_smiles}", "", "候选酶（模型初始排序）:"]
    for e in top_n:
        lines.append(f"  rank={e.rank}  uid={e.uid}  model_score={e.score:.4f}")
    lines.append("")
    lines.append(f"请对上述 {len(top_n)} 个酶重排序，输出 JSON 数组。")
    return "\n".join(lines)


def _identity_passthrough(top_n, reason: str):
    """LLM 不可用时的诚实回退：保持原排序，理由标注回退原因。"""
    return [
        RerankedEnzyme(
            uid=e.uid,
            original_rank=e.rank,
            reranked_rank=e.rank,
            original_score=e.score,
            rerank_rationale=f"[passthrough] {reason}",
            confidence=None,
        )
        for e in top_n
    ]


def llm_reranking_node(state: EnzymeCrewState) -> dict:
    """
    LLMRerankingNode (M5): 对 EnzymeCAGE Top-N 结果 LLM 重排序

    ⚠️ OOL 风险最高的节点 —— 缓解措施:
    - 只取 Top-10 送入 LLM（不是全量 pool）
    - 压缩摘要输入，不传完整序列
    - 设置 max_tokens 上限（config/llm_config.yaml）

    输入: state.ranked_enzymes (Top-N from EnzymeCAGE) + state.candidate_reactions
    输出: state.reranked_enzymes

    容错语义: LLM 未配置 / 网络失败 / 响应不合法 → 诚实回退为原排序 passthrough，
    并置 uncertainty_flag，绝不 fail-closed（重排是增强项，非核心链路）。
    """
    if not state.ranked_enzymes:
        logger.warning("[LLMRerankingNode] No ranked enzymes to rerank, skipping")
        return {}

    top_n = state.ranked_enzymes[:10]
    logger.info(f"[LLMRerankingNode] Reranking top {len(top_n)} enzymes via LLM...")

    reaction_smiles = (
        state.candidate_reactions[0].reaction_smiles
        if state.candidate_reactions
        else "(reaction context unavailable)"
    )

    uncertainty_flags = list(state.uncertainty_flags)
    valid_uids = {e.uid for e in top_n}
    orig_by_uid = {e.uid: e for e in top_n}
    status = "llm_reranked"

    try:
        raw = call_dashscope(
            prompt=_build_prompt(reaction_smiles, top_n),
            system_prompt=RERANK_SYSTEM_PROMPT,
            node_name="llm_reranking_node",
        )
        items = _extract_json_array(raw)

        reranked = []
        seen = set()
        for it in items:
            uid = str(it.get("uid", "")).strip()
            if uid not in valid_uids or uid in seen:
                # 幻觉 / 重复 UID 一律丢弃，保证只重排给定集合
                continue
            seen.add(uid)
            src = orig_by_uid[uid]
            reranked.append(
                RerankedEnzyme(
                    uid=uid,
                    original_rank=src.rank,
                    reranked_rank=int(it.get("reranked_rank", src.rank)),
                    original_score=src.score,
                    rerank_rationale=str(it.get("rerank_rationale", "")).strip()[:500]
                    or "(no rationale)",
                    confidence=(
                        float(it["confidence"])
                        if isinstance(it.get("confidence"), (int, float))
                        else None
                    ),
                )
            )

        # LLM 漏排的 UID：按原排序补回末尾，保证不丢候选
        missing = [e for e in top_n if e.uid not in seen]
        if missing:
            uncertainty_flags.append(
                f"llm_reranking: {len(missing)} 个 UID 未被 LLM 覆盖，已按原序补回"
            )
            next_rank = (max((r.reranked_rank for r in reranked), default=0)) + 1
            for e in missing:
                reranked.append(
                    RerankedEnzyme(
                        uid=e.uid,
                        original_rank=e.rank,
                        reranked_rank=next_rank,
                        original_score=e.score,
                        rerank_rationale="[appended] LLM 未覆盖，按原序补回",
                        confidence=None,
                    )
                )
                next_rank += 1

        if not reranked:
            raise ValueError("LLM 响应未产出任何合法 UID")

        # 按 reranked_rank 稳定排序并规整为连续 1..N
        reranked.sort(key=lambda r: r.reranked_rank)
        for i, r in enumerate(reranked, 1):
            r.reranked_rank = i

    except Exception as e:  # noqa: BLE001 — 重排失败必须优雅降级，不可炸图
        logger.warning(f"[LLMRerankingNode] LLM 重排失败，回退原排序: {e}")
        status = "passthrough_llm_unavailable"
        uncertainty_flags.append(f"llm_reranking 回退原排序（原因: {str(e)[:120]}）")
        reranked = _identity_passthrough(top_n, reason=str(e)[:120])

    evidence = EvidenceRecord(
        stage="reranking",
        action="llm_reranking" if status == "llm_reranked" else "llm_reranking_passthrough",
        data={
            "input_count": len(top_n),
            "output_count": len(reranked),
            "status": status,
            "reaction_context": reaction_smiles[:80],
            "top3_after_rerank": [r.uid for r in reranked[:3]],
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "reranked_enzymes": reranked,
        "uncertainty_flags": uncertainty_flags,
        "evidence_chain": state.evidence_chain + [evidence],
    }
