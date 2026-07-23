# src/nodes/substrate_node.py
# Node 1: 底物解析节点 (LLM)

import logging
from datetime import datetime, timezone

from src.state import EnzymeCrewState
from src.schemas.evidence import EvidenceRecord
from src.tools.substrate_parser import parse_substrate

logger = logging.getLogger(__name__)


def substrate_node(state: EnzymeCrewState) -> dict:
    """
    SubstrateNode: 解析用户查询 → 底物 SMILES
    
    输入: state.user_query
    输出: state.substrate_info + evidence_chain 追加
    """
    logger.info(f"[SubstrateNode] Processing query: {state.user_query[:80]}...")

    try:
        substrate_info = parse_substrate(state.user_query)
    except (ValueError, RuntimeError) as e:
        logger.error(f"[SubstrateNode] Failed: {e}")
        return {
            "error": f"SubstrateNode: {str(e)}",
            "fail_closed": True,
        }

    # 追加证据链
    evidence = EvidenceRecord(
        stage="substrate",
        action=f"parsed_substrate_via_{substrate_info.source}",
        data={
            "smiles": substrate_info.substrate_smiles,
            "name": substrate_info.substrate_name,
            "source": substrate_info.source,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "substrate_info": substrate_info,
        "evidence_chain": state.evidence_chain + [evidence],
    }
