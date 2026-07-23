# src/nodes/enzymecage_node.py
# Node 4: EnzymeCAGE 远程排序节点

import logging
from datetime import datetime, timezone

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord
from src.tools.enzymecage_client import call_enzymecage

logger = logging.getLogger(__name__)


def enzymecage_node(state: EnzymeCrewState) -> dict:
    """
    EnzymeCAGENode: 酶 Pool + 反应 → 排序结果
    
    输入: state.enzyme_pool_final, state.candidate_reactions[0] (最相似反应)
    输出: state.ranked_enzymes + evidence_chain
    
    注意: 模型冻结，仅作为排序能力提供者。
    """
    if not state.enzyme_pool_final:
        return {
            "error": "EnzymeCAGENode: enzyme_pool_final is empty",
            "fail_closed": True,
        }

    if not state.candidate_reactions:
        return {
            "error": "EnzymeCAGENode: No candidate reactions",
            "fail_closed": True,
        }

    # 使用相似度最高的反应作为排序 query
    top_reaction = state.candidate_reactions[0]
    logger.info(
        f"[EnzymeCAGENode] Ranking {len(state.enzyme_pool_final)} enzymes "
        f"against reaction: {top_reaction.reaction_smiles[:50]}..."
    )

    try:
        ranked_enzymes = call_enzymecage(
            reaction_smiles=top_reaction.reaction_smiles,
            enzyme_pool_uids=state.enzyme_pool_final,
        )
    except (RuntimeError, Exception) as e:
        logger.error(f"[EnzymeCAGENode] Failed: {e}")
        return {
            "error": f"EnzymeCAGENode: {str(e)}",
            "fail_closed": True,
        }

    if not ranked_enzymes:
        return {
            "error": "EnzymeCAGENode: API returned empty ranking",
            "fail_closed": True,
        }

    # 追加证据链
    evidence = EvidenceRecord(
        stage="ranking",
        action="enzymecage_v1_ensemble_ranking",
        data={
            "model_version": state.model_version,
            "pool_size": len(state.enzyme_pool_final),
            "route_used": state.pool_route_used,
            "num_ranked": len(ranked_enzymes),
            "top1_uid": ranked_enzymes[0].uid,
            "top1_score": ranked_enzymes[0].score,
            "reaction_smiles": top_reaction.reaction_smiles[:60],
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "ranked_enzymes": ranked_enzymes,
        "evidence_chain": state.evidence_chain + [evidence],
    }
