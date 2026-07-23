# src/nodes/enzyme_pool_node.py
# Node 3: 酶 Pool 构造节点 (确定性，B-primary / C-fallback)

import logging
from datetime import datetime, timezone

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord
from src.tools.enzyme_pool_builder import build_enzyme_pool

logger = logging.getLogger(__name__)


def enzyme_pool_node(state: EnzymeCrewState) -> dict:
    """
    EnzymePoolNode: 候选反应 → 酶 Pool (B/C 路线)
    
    输入: state.candidate_reactions
    输出: state.enzyme_pool_final, pool_route_used, pool_size + evidence_chain
    """
    if not state.candidate_reactions:
        return {
            "error": "EnzymePoolNode: No candidate reactions (upstream failure)",
            "fail_closed": True,
        }

    logger.info(f"[EnzymePoolNode] Building pool from {len(state.candidate_reactions)} reactions")

    try:
        final_pool, route_used, pool_b, pool_c = build_enzyme_pool(
            candidate_reactions=state.candidate_reactions,
        )
    except (ValueError, OSError) as e:
        logger.error(f"[EnzymePoolNode] Failed: {e}")
        return {
            "error": f"EnzymePoolNode: {str(e)}",
            "fail_closed": True,
        }

    # 路线决策理由（provenance）：B 非空用 B，B 空才回退 C
    if route_used == "B":
        route_decision_reason = (
            f"B-primary: |B|={len(pool_b)} 非空，直接采用 route_b（高置信自匹配/邻居 EC）"
        )
    else:
        route_decision_reason = (
            f"C-fallback: |B|={len(pool_b)} 为空，回退 route_c（泛化检索，|C|={len(pool_c)}）"
        )

    # 追加证据链
    evidence = EvidenceRecord(
        stage="pool",
        action=f"built_pool_via_{route_used}_route",
        data={
            "route_used": route_used,
            "route_decision_reason": route_decision_reason,
            "pool_size": len(final_pool),
            "pool_b_size": len(pool_b),
            "pool_c_size": len(pool_c),
            "sample_uids": final_pool[:5],
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "enzyme_pool_b": pool_b if pool_b else None,
        "enzyme_pool_c": pool_c if pool_c else None,
        "enzyme_pool_final": final_pool,
        "pool_route_used": route_used,
        "pool_size": len(final_pool),
        "evidence_chain": state.evidence_chain + [evidence],
    }
