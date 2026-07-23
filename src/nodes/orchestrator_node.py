# src/nodes/orchestrator_node.py
# M5: 编排器节点 (LLM 意图分类 + 动态路由)
# M3 模式下此节点为 pass-through，直接走固定路由

import logging
from datetime import datetime, timezone

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord, IntentClassification
from src.utils.llm import call_dashscope

logger = logging.getLogger(__name__)

INTENT_SYSTEM_PROMPT = """你是 EnzymeCrew 智能编排器。根据用户输入判断意图类型。

可选意图：
- enzyme_recommendation: 用户提供底物/反应，需要推荐降解酶
- microbe_recommendation: 用户需要推荐携带目标酶的微生物
- trait_query: 用户需要查询微生物性状（如污水适应性）
- reaction_exploration: 用户想探索某底物的可能反应路径
- general_question: 一般性问题

严格以 JSON 格式返回：
{"intent": "...", "confidence": 0.95, "extracted_entities": {"substrate": "...", "smiles": "..."}}
"""


def orchestrator_node(state: EnzymeCrewState) -> dict:
    """
    OrchestratorNode: 用户意图分类 + 路由决策
    
    M3 模式: 跳过 LLM，默认 enzyme_recommendation
    M5 模式: 调用 LLM 进行意图分类，动态路由
    """
    # M3: 固定路由，不调用 LLM
    if state.pipeline_mode == "m3":
        logger.info("[OrchestratorNode] M3 mode: fixed route (enzyme_recommendation)")
        intent = IntentClassification(
            intent="enzyme_recommendation",
            confidence=1.0,
            extracted_entities={},
        )
        return {"intent": intent}

    # M5: LLM 意图分类
    logger.info("[OrchestratorNode] M5 mode: classifying intent via LLM...")

    try:
        llm_response = call_dashscope(
            prompt=f"用户输入: {state.user_query}",
            system_prompt=INTENT_SYSTEM_PROMPT,
            node_name="orchestrator_node",
        )
        # TODO M5: 解析 LLM 返回的 JSON，构造 IntentClassification
        # 当前占位，fallback 到 enzyme_recommendation
        import json, re
        cleaned = re.sub(r'```json?\s*', '', llm_response)
        cleaned = re.sub(r'```\s*$', '', cleaned).strip()
        result = json.loads(cleaned)
        intent = IntentClassification(**result)
    except Exception as e:
        logger.warning(f"[OrchestratorNode] Intent classification failed: {e}, fallback to enzyme_recommendation")
        intent = IntentClassification(
            intent="enzyme_recommendation",
            confidence=0.5,
            extracted_entities={},
        )

    evidence = EvidenceRecord(
        stage="orchestration",
        action=f"intent_classified_as_{intent.intent}",
        data={"intent": intent.intent, "confidence": intent.confidence},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "intent": intent,
        "evidence_chain": state.evidence_chain + [evidence],
    }
