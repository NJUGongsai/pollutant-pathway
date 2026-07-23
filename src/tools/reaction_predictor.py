# src/tools/reaction_predictor.py
# M5: 反应预测工具 (fallback 分支)
# 当相似反应检索失败时，生成候选反应

import logging
from typing import List, Optional

from src.schemas.evidence import PredictedReaction

logger = logging.getLogger(__name__)


def predict_reactions(
    substrate_smiles: str,
    method: str = "template_matching",
    top_k: int = 5,
) -> List[PredictedReaction]:
    """
    基于底物 SMILES 预测可能的降解反应。
    
    可选方法 (TODO M5):
    - "template_matching": 已知降解路径模板匹配
    - "retrosynthesis": 逆合成工具 (AiZynthFinder / ASKCOS)
    - "llm_generation": LLM 生成 + RDKit 验证
    
    Args:
        substrate_smiles: 底物 SMILES
        method: 预测方法
        top_k: 返回最大候选反应数
        
    Returns:
        PredictedReaction 列表
    """
    # ─── TODO M5: 实际实现 ───────────────────────────────
    # 选项 A: 模板库匹配
    #   - 加载已知降解反应模板 (EAWAG-BBD / UM-PPS 规则)
    #   - 底物子结构匹配 → 生成产物
    #
    # 选项 B: LLM 生成 + 验证
    #   - 调用 qwen-max 生成候选反应 SMILES
    #   - RDKit 验证化学合理性
    #   - 检查原子守恒
    #
    # 选项 C: 逆合成 API
    #   - 调用外部逆合成服务
    # ────────────────────────────────────────────────────────

    logger.warning(f"[reaction_predictor] Not implemented for {substrate_smiles[:30]}")
    return []


def validate_reaction_smiles(reaction_smiles: str) -> bool:
    """
    验证反应 SMILES 的化学合理性。
    
    检查:
    - 格式正确 (A>>B)
    - 底物/产物均可解析
    - 原子数守恒 (可选)
    """
    try:
        from rdkit import Chem
        parts = reaction_smiles.split(">>")
        if len(parts) != 2:
            return False
        for side in parts:
            mols = side.split(".")
            for smi in mols:
                if Chem.MolFromSmiles(smi) is None:
                    return False
        return True
    except Exception:
        return False
