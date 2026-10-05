"""事件、报告投影与展开计划 — 三个集合分开(实施书 §5.3,S1)。

- 事件(PathwayEvent)保存该假设**全部已知参与物和产物**,包括不展开的
  副产物、已知共底物及系数;事件不被报告 top-K 截断;
- report projection 只决定展示/评分的主产物位次,保存自己的版本与
  理由;改报告 K 不删改完整事件(A02);
- expansion plan 只决定哪些产物继续探索,保存 deferred 或不追踪原因
  (A03);
- 某共同产物本身格式非法时不得静默丢掉:事件提交前必须能对全部参与物
  构建 ChemicalState,任一失败 → 参与物状态失败(结构化,调用方拒绝或
  挂起该假设并报告整体问题,不部分提交);
- 酶/催化剂另存 catalytic_support,不塞进净反应计量;
- 幂等键 (run_id, parent_path_id, hypothesis_id, context_hash,
  event_semantics_hash):同键重放不新增事件;同键异内容冲突。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.models import canonical_json, content_hash, now_iso, stable_id
from .chemstate import ChemicalState, build_chemical_state
from .hypothesis import (
    PARTICIPANT_SIDE_PRODUCT,
    ReactionHypothesis,
)
from .profile import PPV1_EVENT_SCHEMA_VERSION

EXPANSION_STATUS_EXPANDED = "expanded"
EXPANSION_STATUS_DEFERRED = "deferred"
EXPANSION_STATUS_NOT_TRACKED = "not_tracked"
EXPANSION_STATUSES = frozenset({EXPANSION_STATUS_EXPANDED,
                                EXPANSION_STATUS_DEFERRED,
                                EXPANSION_STATUS_NOT_TRACKED})


class EventContractError(RuntimeError):
    """事件/投影/展开计划的契约违反(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


class ParticipantStateError(EventContractError):
    """参与物无法构建 ChemicalState(整体问题,不静默丢共同产物)。"""


@dataclass
class CatalyticSupport:
    """催化支持(酶/催化剂;不进净反应计量,§5.3)。"""

    agent_ref: str                     # 酶/CN/名称等引用
    role: str = "catalyst"             # catalyst | cometabolic_partner | …
    evidence_refs: list[str] = field(default_factory=list)
    status: str = "unknown"            # supported | inferred | unknown | conflict

    def to_dict(self) -> dict:
        return {"agent_ref": self.agent_ref, "role": self.role,
                "evidence_refs": list(self.evidence_refs),
                "status": self.status}


@dataclass
class PathwayEvent:
    """反应事件(完整参与物账目;独立于报告投影与展开计划)。"""

    event_id: str
    run_id: str
    parent_path_id: str
    hypothesis_id: str
    context_hash: str
    participants: list[dict]           # ReactionHypothesis.participants 序列化
    participant_state_refs: list[str]  # 全部参与物 ChemicalState 引用
    catalytic_support: list[dict] = field(default_factory=list)
    schema_version: str = PPV1_EVENT_SCHEMA_VERSION
    created_at: str = field(default_factory=now_iso)

    @property
    def event_semantics_hash(self) -> str:
        """事件语义哈希(幂等键成分;与投影/展开无关)。"""
        return content_hash({
            "participants": self.participants,
            "catalytic_support": self.catalytic_support,
            "hypothesis_id": self.hypothesis_id,
        })


@dataclass
class ReportProjection:
    """报告投影:展示/评分的主产物位次(自己的版本与理由;§5.3)。"""

    product_ranks: list[dict]          # [{state_ref, report_rank, basis, note}]
    max_reportable: int                # 报告宽度 K(投影参数,非事件事实)
    dedup_notes: list[dict] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    projection_version: str = "ppv1-report-projection-1"

    def to_dict(self) -> dict:
        return {
            "product_ranks": [dict(r) for r in self.product_ranks],
            "max_reportable": self.max_reportable,
            "dedup_notes": [dict(d) for d in self.dedup_notes],
            "reasons": list(self.reasons),
            "projection_version": self.projection_version,
        }


@dataclass
class ExpansionPlan:
    """展开计划:哪些产物继续探索 + 不追踪原因(§5.3)。"""

    entries: list[dict]                # [{state_ref, status, reason}]
    policy_version: str = "ppv1-expansion-1"

    def to_dict(self) -> dict:
        return {"entries": [dict(e) for e in self.entries],
                "policy_version": self.policy_version}


def event_id_for(run_id: str, parent_path_id: str, hypothesis_id: str,
                 context_hash: str, semantics_hash: str) -> str:
    """事件幂等键 ID(run+父路径+假设+上下文+事件语义,§9.2)。"""
    return stable_id("ppev", run_id, parent_path_id, hypothesis_id,
                     context_hash, semantics_hash)


def build_event_states(
    hypothesis: ReactionHypothesis,
    *,
    raw_structures: dict[str, str],
    state_origins: dict[str, str] | None = None,
    state_source_refs: dict[str, list[dict]] | None = None,
) -> dict[str, ChemicalState]:
    """为假设的全部参与物构建 ChemicalState(整体构建,不部分提交)。

    raw_structures: state_ref → 原始结构串。任一参与物缺结构串或解析
    失败 → ParticipantStateError(含参与物定位;不静默丢掉任何共同
    产物,由调用方拒绝/挂起整个假设)。
    """
    states: dict[str, ChemicalState] = {}
    for p in hypothesis.participants:
        ref = p.state_ref
        structure = (raw_structures or {}).get(ref)
        if structure is None:
            raise ParticipantStateError(
                "参与物缺少原始结构(事件提交需要全部参与物状态)",
                {"state_ref": ref, "hypothesis_id": hypothesis.hypothesis_id,
                 "kind": "missing_structure"})
        try:
            states[ref] = build_chemical_state(
                structure,
                (state_origins or {}).get(ref, "source_product"),
                (state_source_refs or {}).get(ref),
            )
        except Exception as exc:
            raise ParticipantStateError(
                "参与物结构无法解析(格式非法的共同产物不得静默丢弃)",
                {"state_ref": ref,
                 "hypothesis_id": hypothesis.hypothesis_id,
                 "kind": "unparseable_participant",
                 "reason": str(exc)[:200]}) from exc
    return states


def build_pathway_event(
    hypothesis: ReactionHypothesis,
    *,
    run_id: str,
    context_hash: str,
    catalytic_support: list[CatalyticSupport] | None = None,
) -> PathwayEvent:
    """假设 → 完整事件(参与者全量入账;不引用投影/展开)。"""
    participants = [p.to_dict() for p in hypothesis.participants]
    semantics = content_hash({
        "participants": participants,
        "catalytic_support": [c.to_dict() for c in catalytic_support or []],
        "hypothesis_id": hypothesis.hypothesis_id,
    })
    return PathwayEvent(
        event_id=event_id_for(run_id, hypothesis.parent_path_id,
                              hypothesis.hypothesis_id, context_hash,
                              semantics),
        run_id=run_id,
        parent_path_id=hypothesis.parent_path_id,
        hypothesis_id=hypothesis.hypothesis_id,
        context_hash=context_hash,
        participants=participants,
        participant_state_refs=[p["state_ref"] for p in participants],
        catalytic_support=[c.to_dict() for c in catalytic_support or []],
    )


def build_report_projection(
    hypothesis: ReactionHypothesis,
    *,
    max_reportable: int,
    ranked_state_refs: list[str],
    reasons: list[str] | None = None,
    dedup_notes: list[dict] | None = None,
) -> ReportProjection:
    """报告投影(K 只作用于投影;事件参与物不受影响)。

    ranked_state_refs:按主产物位次排序的产物 state_ref(去重后);
    超出 K 的产物不入位次(投影如实记录宽度上限,事件不删)。
    """
    if max_reportable < 1:
        raise EventContractError(
            f"报告宽度必须 ≥1:{max_reportable}", {"max_reportable":
                                                  max_reportable})
    product_refs = [p.state_ref for p in hypothesis.participants
                    if p.side == PARTICIPANT_SIDE_PRODUCT]
    known = set(product_refs)
    for ref in ranked_state_refs:
        if ref not in known:
            raise EventContractError(
                "报告位次引用了非产物参与物",
                {"state_ref": ref, "hypothesis_id": hypothesis.hypothesis_id})
    ranks = []
    for rank, ref in enumerate(ranked_state_refs[:max_reportable], start=1):
        ranks.append({"state_ref": ref, "report_rank": rank,
                      "basis": "declared_rank_order", "note": ""})
    for ref in ranked_state_refs[max_reportable:]:
        ranks.append({"state_ref": ref, "report_rank": None,
                      "basis": "report_width_cap",
                      "note": f"report_width_cap:{max_reportable}"})
    return ReportProjection(product_ranks=ranks,
                            max_reportable=max_reportable,
                            dedup_notes=list(dedup_notes or []),
                            reasons=list(reasons or []))


def build_expansion_plan(
    hypothesis: ReactionHypothesis,
    *,
    expanded: list[str],
    deferred: list[str],
    not_tracked: list[str],
    reasons: dict[str, str] | None = None,
) -> ExpansionPlan:
    """展开计划(独立原因;A03:not_tracked 产物在事件中完整保留)。"""
    reasons = reasons or {}
    product_refs = {p.state_ref for p in hypothesis.participants
                    if p.side == PARTICIPANT_SIDE_PRODUCT}
    declared = set(expanded) | set(deferred) | set(not_tracked)
    unknown = declared - product_refs
    if unknown:
        raise EventContractError(
            "展开计划引用了非产物参与物",
            {"unknown_refs": sorted(unknown),
             "hypothesis_id": hypothesis.hypothesis_id})
    entries = []
    for ref in expanded:
        entries.append({"state_ref": ref, "status": EXPANSION_STATUS_EXPANDED,
                        "reason": reasons.get(ref, "")})
    for ref in deferred:
        entries.append({"state_ref": ref, "status": EXPANSION_STATUS_DEFERRED,
                        "reason": reasons.get(ref, "")})
    for ref in not_tracked:
        entries.append({"state_ref": ref,
                        "status": EXPANSION_STATUS_NOT_TRACKED,
                        "reason": reasons.get(ref, "")})
    # 未出现在任何名单的产物:默认不追踪,但必须显式留原因(不静默)
    unlisted = product_refs - declared
    for ref in sorted(unlisted):
        entries.append({"state_ref": ref,
                        "status": EXPANSION_STATUS_NOT_TRACKED,
                        "reason": reasons.get(
                            ref, "not_declared_in_expansion_plan")})
    return ExpansionPlan(entries=entries)


def event_commit_payload(event: PathwayEvent) -> dict:
    """事件提交载荷(事件 + 投影 + 展开计划分开序列化,同事务落账)。"""
    return {
        "event": {
            "schema_version": event.schema_version,
            "event_id": event.event_id,
            "run_id": event.run_id,
            "parent_path_id": event.parent_path_id,
            "hypothesis_id": event.hypothesis_id,
            "context_hash": event.context_hash,
            "participants": list(event.participants),
            "participant_state_refs": list(event.participant_state_refs),
            "catalytic_support": list(event.catalytic_support),
            "created_at": event.created_at,
            "event_semantics_hash": event.event_semantics_hash,
        },
        "semantics_json": canonical_json(event.participants),
    }
