"""v4.3 领域契约 — Compound / ReactionEvent / PathInstance / Evidence / Decision。

版本化(schema_version)的数据类,全部可 JSON 往返。化学路径图语义:
``分子 → 反应事件 → 有序产物集合``;一个已记录反应的多个产物同属一个
ReactionEvent;同一分子经不同路线到达共享 Compound 身份但保留各自
PathInstance。执行层(LangGraph State)不在此列 —— State 只持引用。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

DOMAIN_SCHEMA_VERSION = "v43-domain-1"

# PathInstance.status 的完整状态集(任务书 §1.1:状态分清,不得隐瞒)
PATH_STATUS_FRONTIER = "frontier"                    # 待探索
PATH_STATUS_EXPANDED = "expanded"                    # 已展开(事件已提交)
PATH_STATUS_DEFERRED = "deferred"                    # 合法候选但策略暂缓
PATH_STATUS_AWAITING_PREDICTION = "awaiting_prediction"  # 仅规则/类比或竞争反应
PATH_STATUS_DEAD_END = "dead_end"                    # 无有效证据
PATH_STATUS_DEPTH_LIMIT = "depth_limit"              # 已到深度上限
PATH_STATUS_REJECTED = "rejected"                    # 校验拒绝

TERMINAL_PATH_STATUSES = {
    PATH_STATUS_EXPANDED,
    PATH_STATUS_AWAITING_PREDICTION,
    PATH_STATUS_DEAD_END,
    PATH_STATUS_DEPTH_LIMIT,
    PATH_STATUS_REJECTED,
}

EVIDENCE_KIND_RECORDED = "recorded_reaction"
EVIDENCE_KIND_RULE = "rule_application"
EVIDENCE_KIND_ANALOG = "analog_reaction"
EVIDENCE_KIND_NOVEL = "novel_proposal"  # 模型受约束新提案(预测,非实测)

# 预测任务协议(任务书 §2)
PREDICTION_MODE_RANK = "rank_candidates"
PREDICTION_MODE_ANALOGY = "analogy_edit"
PREDICTION_MODE_NOVEL = "novel_proposal"

CONDITION_COMPATIBLE = "compatible"
CONDITION_UNKNOWN = "unknown"
CONDITION_CONFLICT = "conflict"

ATOM_MAPPING_UNAVAILABLE = "unavailable"

STRATEGY_VERSION = "v43-policy-4"  # 选择策略版本;策略变更须升版本并拒绝旧 run resume(v4=Phase D:reactant_similar 检索通道)


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def stable_id(prefix: str, *parts: str) -> str:
    """由内容派生的稳定内部 ID(幂等重放产生同一 ID)。"""
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:20]}"


def canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


@dataclass
class Compound:
    cn: str                       # 规范身份(主键)
    example_smiles: str           # 首次见到时的原始 SMILES
    first_path_id: str

    def to_dict(self) -> dict:
        return {
            "cn": self.cn, "example_smiles": self.example_smiles,
            "first_path_id": self.first_path_id,
        }


@dataclass
class Evidence:
    """证据卡(任务书 §1.2 全字段)。检索结果按 evidence_id 幂等。"""

    evidence_id: str
    source_id: str                # 数据库/规则/索引条目 ID(如 bt0254#r0601)
    kind: str                     # recorded_reaction | rule_application | analog_reaction
    query_identity: str           # 检索时的规范底物身份
    match_type: str               # 如 exact_donor_cn_match / rule_template / retrieval_neighbor
    reactant_smiles: str
    reactant_identity: str
    products: list[dict]          # 有序:[{position, product_smiles, product_smiles_full, product_identity, score, ...}]
    atom_mapping: str             # 可用映射或 "unavailable"
    condition_fit: str            # compatible | unknown | conflict
    retrieval_rank: int           # 引擎原始顺序(1 起始)
    score: float
    score_semantics: str          # 分数含义,不混称概率
    source_record: dict           # 引擎原始行(可复查出处)
    asset_file: str               # 相对资产根的来源文件路径
    asset_sha256: str
    run_id: str = ""
    path_id: str = ""
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, d: dict) -> "Evidence":
        return cls(**d)


@dataclass
class ReactionEvent:
    event_id: str
    run_id: str
    parent_path_id: str           # 触发事件的路径(底物所在)
    substrate_identity: str
    evidence_id: str              # 证据卡引用(全文在 retrieval artifact)
    evidence_hash: str            # 证据卡内容哈希(同键不同内容 → 冲突)
    source_id: str
    kind: str
    condition_fit: str
    model_ref: str = ""           # 模型决策引用(确定性通路为空;store v2)
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class PathInstance:
    path_id: str
    run_id: str
    parent_path_id: str | None    # None = 根路径
    event_id: str | None          # None = 根路径;否则父事件
    product_position: int | None  # 在父事件有序产物中的位次(0 起始);根为 None
    substrate_identity: str
    status: str
    depth: int                    # 根=0
    status_reason: str = ""
    seq: int = 0                  # 同 run 内创建顺序(frontier 排序依据)
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class Decision:
    """classify_evidence 的策略裁决(纯函数产物,持久化为 artifact)。"""

    run_id: str
    path_id: str
    outcome: str                  # commit_recorded | awaiting_prediction | dead_end
    accepted_evidence_id: str | None
    reason: str
    considered: list[dict]        # 每张证据卡的分级与取舍原因
    strategy_version: str = STRATEGY_VERSION
    prediction_mode: str = ""     # 预测协议路由(None/空=不进模型)
    prediction_reason: str = ""
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return dict(self.__dict__)
