"""domain 层 — 纯数据模型与选择策略,不导入 LangGraph/框架/CLI。"""

from .identity import cn_identity, normalize_charge_smiles, parseable, stereo_blind
from .models import (
    ATOM_MAPPING_UNAVAILABLE,
    CONDITION_COMPATIBLE,
    CONDITION_CONFLICT,
    CONDITION_UNKNOWN,
    DOMAIN_SCHEMA_VERSION,
    EVIDENCE_KIND_ANALOG,
    EVIDENCE_KIND_RECORDED,
    EVIDENCE_KIND_RULE,
    PATH_STATUS_AWAITING_PREDICTION,
    PATH_STATUS_DEAD_END,
    PATH_STATUS_DEFERRED,
    PATH_STATUS_DEPTH_LIMIT,
    PATH_STATUS_EXPANDED,
    PATH_STATUS_FRONTIER,
    PATH_STATUS_REJECTED,
    STRATEGY_VERSION,
    Compound,
    Decision,
    Evidence,
    PathInstance,
    ReactionEvent,
    canonical_json,
    content_hash,
    stable_id,
)
from .pathway import (
    ancestry_chain,
    ancestry_chain_records,
    ancestry_identities,
    display_name,
    is_in_path_cycle,
)
from .policy import (
    OUTCOME_AWAITING_PREDICTION,
    OUTCOME_COMMIT_RECORDED,
    OUTCOME_DEAD_END,
    classify_evidence,
    schedule_products,
    select_frontier,
    stop_reason,
)

__all__ = [
    "ATOM_MAPPING_UNAVAILABLE", "CONDITION_COMPATIBLE", "CONDITION_CONFLICT",
    "CONDITION_UNKNOWN", "DOMAIN_SCHEMA_VERSION", "EVIDENCE_KIND_ANALOG",
    "EVIDENCE_KIND_RECORDED", "EVIDENCE_KIND_RULE",
    "PATH_STATUS_AWAITING_PREDICTION", "PATH_STATUS_DEAD_END",
    "PATH_STATUS_DEFERRED", "PATH_STATUS_DEPTH_LIMIT", "PATH_STATUS_EXPANDED",
    "PATH_STATUS_FRONTIER", "PATH_STATUS_REJECTED", "STRATEGY_VERSION",
    "Compound", "Decision", "Evidence", "PathInstance", "ReactionEvent",
    "canonical_json", "content_hash", "cn_identity", "stable_id",
    "stereo_blind", "normalize_charge_smiles", "parseable",
    "ancestry_chain", "ancestry_chain_records", "ancestry_identities",
    "display_name", "is_in_path_cycle",
    "OUTCOME_AWAITING_PREDICTION", "OUTCOME_COMMIT_RECORDED", "OUTCOME_DEAD_END",
    "classify_evidence", "schedule_products", "select_frontier", "stop_reason",
]
