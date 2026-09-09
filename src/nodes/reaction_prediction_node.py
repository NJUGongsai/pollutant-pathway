# src/nodes/reaction_prediction_node.py
# M5: 反应预测节点 (fallback 分支)
# 当 ReactionNode 相似性检索失败时，通过 LLM/逆合成工具生成候选反应

import logging
from datetime import datetime, timezone

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord, PredictedReaction
from src.tools.reaction_predictor import predict_reactions

logger = logging.getLogger(__name__)


def reaction_prediction_node(state: EnzymeCrewState) -> dict:
    """
    ReactionPredictionNode (M5): 反应预测 fallback
    
    触发条件: ReactionNode 返回空或相似度过低
    输出: state.predicted_reactions + reaction_source 更新
    
    实现路线 (2026-08-05 实装):
    - biotransformer_envmicro: BioTransformer 3.0 ENVMICRO 规则引擎（EAWAG-BBD/PPS，
      SMARTS 命中 + SMIRKS 变换），jar 路径由 BIOTRANSFORMER_JAR 环境变量提供
    - template_matching / llm_generation: 占位，待引擎选型裁定后实装
    
    fail-closed 语义：jar 未配置或调用失败时 predict_reactions 返回空，
    本节点维持原有 fail_closed 行为（不伪造候选）。
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

    # ─── M5 实装：BioTransformer ENVMICRO fallback ─────────
    # 产物经 adapter 后处理（RDKit 规范化/去重/Top-K），映射为 parent>>product 半反应；
    # 规则引擎无概率，confidence=0.0，语义在 provenance 中标注。
    predicted: list[PredictedReaction] = predict_reactions(substrate_smiles)

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
