# src/nodes/reaction_node.py
# Node 2: 相似反应检索节点 (确定性，无LLM)

import logging
from datetime import datetime, timezone
import hashlib

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord
from src.tools.reaction_retriever import retrieve_similar_reactions, ReactionDatabase

logger = logging.getLogger(__name__)

# 模块级惰性单例
_reaction_db: ReactionDatabase | None = None


def _get_db() -> ReactionDatabase:
    global _reaction_db
    if _reaction_db is None:
        _reaction_db = ReactionDatabase()
    return _reaction_db


def reaction_node(state: EnzymeCrewState) -> dict:
    """
    ReactionNode: 底物 SMILES → Top-K 相似反应
    
    输入: state.substrate_info.substrate_smiles
    输出: state.candidate_reactions + evidence_chain 追加
    """
    if state.substrate_info is None:
        return {
            "error": "ReactionNode: substrate_info is None (upstream failure)",
            "fail_closed": True,
        }

    substrate_smiles = state.substrate_info.substrate_smiles
    logger.info(f"[ReactionNode] Retrieving reactions for: {substrate_smiles}")

    # 单步场景统一公共 ID 合同（T6-R3 裁定 4）：reaction_task_id = RT-{16hex}。
    # 多步桥接已写入 state.reaction_task_id 时保留；单步则按底物确定性生成，
    # 作为 T5 消费与跨组件 crosswalk 的唯一锚定键（MISS 与命中共用）。
    reaction_task_id = state.reaction_task_id or (
        f"RT-{hashlib.md5(substrate_smiles.encode('utf-8')).hexdigest()[:16]}"
    )

    try:
        db = _get_db()
        candidates = retrieve_similar_reactions(
            substrate_smiles=substrate_smiles,
            topk=10,
            db=db,
        )
    except (ValueError, OSError) as e:
        logger.error(f"[ReactionNode] Failed: {e}")
        return {
            "error": f"ReactionNode: {str(e)}",
            "fail_closed": True,
        }

    if not candidates:
        # Route C 真实 MISS：检索正常完成但无相似反应命中，并非失败。
        # 不置 fail_closed/error，交由 route_after_reaction 决定去向：
        #   M5 → ReactionPredictionNode（BioTransformer ENVMICRO fallback，裁定 2）；
        #   M3 → enzyme_pool 后由 pool 层显式报停。
        evidence = EvidenceRecord(
            stage="reaction",
            action="retrieval_miss",
            data={
                "reaction_task_id": reaction_task_id,
                "substrate_smiles": substrate_smiles,
                "num_candidates": 0,
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return {
            "candidate_reactions": [],
            "reaction_task_id": reaction_task_id,
            "evidence_chain": state.evidence_chain + [evidence],
        }

    # 命中：追加证据链
    evidence = EvidenceRecord(
        stage="reaction",
        action="retrieved_similar_reactions",
        data={
            "reaction_task_id": reaction_task_id,
            "substrate_smiles": substrate_smiles,
            "num_candidates": len(candidates),
            "top_score": candidates[0].similarity_score,
            "top_reaction": candidates[0].reaction_smiles[:60],
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "candidate_reactions": candidates,
        "reaction_task_id": reaction_task_id,
        "evidence_chain": state.evidence_chain + [evidence],
    }
