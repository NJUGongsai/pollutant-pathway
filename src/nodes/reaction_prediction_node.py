# src/nodes/reaction_prediction_node.py
# M5: 反应预测节点 (fallback 分支)
# 当 ReactionNode 相似性检索失败时，通过 LLM/逆合成工具生成候选反应

import logging
from datetime import datetime, timezone

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord, PredictedReaction

logger = logging.getLogger(__name__)


def reaction_prediction_node(state: EnzymeCrewState) -> dict:
    """
    ReactionPredictionNode (M5): 反应预测 fallback
    
    触发条件: ReactionNode 返回空或相似度过低
    输出: state.predicted_reactions + reaction_source 更新
    
    实现路线 (TODO M5):
    - 方案 A: 调用逆合成工具 (如 AiZynthFinder 接口)
    - 方案 B: LLM 生成候选反应 SMILES + 验证
    - 方案 C: 规则库匹配 (已知降解路径模板)
    """
    logger.info("[ReactionPredictionNode] M5 fallback: predicting reactions...")

    substrate_smiles = (
        state.substrate_info.substrate_smiles if state.substrate_info else None
    )
    if not substrate_smiles:
        return {
            "error": "ReactionPredictionNode: No substrate SMILES available",
            "fail_closed": True,
        }

    # ─── TODO M5: 实际实现 ───────────────────────────────
    # 当前占位：返回空并标记
    # 正式版本应调用:
    #   from src.tools.reaction_predictor import predict_reactions
    #   predicted = predict_reactions(substrate_smiles)
    # ────────────────────────────────────────────────────────

    predicted: list[PredictedReaction] = []

    if not predicted and not state.candidate_reactions:
        return {
            "error": "ReactionPredictionNode: Both retrieval and prediction failed",
            "fail_closed": True,
            "uncertainty_flags": state.uncertainty_flags + ["reaction_prediction_empty"],
        }

    # 合并 retrieved + predicted
    reaction_source = "merged" if state.candidate_reactions and predicted else (
        "predicted" if predicted else "retrieved"
    )

    evidence = EvidenceRecord(
        stage="reaction",
        action="reaction_prediction_fallback",
        data={
            "substrate_smiles": substrate_smiles,
            "num_predicted": len(predicted),
            "reaction_source": reaction_source,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "predicted_reactions": predicted,
        "reaction_source": reaction_source,
        "evidence_chain": state.evidence_chain + [evidence],
    }
