"""S4a endpoint 分账 —— execution/stop/chemical endpoint/bookkeeping
四分账 + F01/F02/F03 + 证据字段 + 独立持久化与首消费
(实施书 §10/§17.3;契约 ppv1-endpoint-1 / endpoint-policy-1 登记)。

四分账(四者独立存在、互不代替,任务书 §2.A):

- ``execution_status``:执行会话本身是否完成(completed/failed/
  incomplete —— claimed/open 在途 = incomplete;run_error = failed);
- ``search_stop_reason``:搜索为何停(六原因枚举 + 主因优先级,
  沿用 search.py 冻结优先级;**独立持久化**于 stop_reason_records
  表,endpoint 记录只按摘要引用,不复制语义);
- ``chemical_endpoint_assessment``:化学终点判断
  (unknown / metabolic_handoff / supported_terminal_transformation_
  product / supported_mineralization),**只**由独立终点证据
  (frozen plan 的 endpoint_evidence 声明,来源层直报)决定;
- ``bookkeeping_status``:参与物/系数/根碳账/映射是否在声明范围内
  闭合(closed_within_declared_scope / not_closed / unknown)——
  账平只表示核查范围内账面闭合,**不等于矿化,不等于生物可行**。

硬约束(任务书 §4;逐条实现,不止在一个入口补判断):

- **F01 停止不是终点**:停止原因(无候选/深度/预算/弃权/等待/耗尽
  /用户停止)永不映射为终点值;无独立终点证据 ⇒ ``unknown``;
  停止不覆盖已有有效终点证据(证据与评估并存,评估只随证据/依赖
  变化);停止时保留 deferred/未展开/预算原因/已有证据;
- **F02 未知依赖不被 recorded 洗白**:route 上未解决依赖(上下文
  Dependency status != supported)沿途保留并继承到 endpoint 记录;
  recorded/来源直报不升级"本场景已观察事实" —— 存在未解决必要
  依赖时终点保持 unknown(evidence 保留 + blocked_reasons 披露),
  未解决依赖清单与依赖来源、条件评估、proof scope 一并保留;
- **S4-C01(确认复核 §4,回修 r1)必要条件同源限制**:当前路线
  已引入的必要条件(level=essential、basis=essential_claimed_by_
  source)经**同源** ``PathContext.route_assessment()``(历史快照
  逐边合取 + 当前阶段 live;旧边按记录值消费,不重评)评估为
  unknown/conflict 时,终点同样保持 unknown —— 必要条件未知/
  冲突不能被 recorded 或充分证据字段洗白;逐条评估行全文保留在
  record.route_condition_assessment,输入摘要(route_conditions_
  digest)入 derived_from 与首消费 staleness 同源重算;已知兼容
  正控、无必要条件、缺启动 NAD 依赖正/负控保持既有行为(不全拒、
  不解析自由文本、不新增化学门;契约 ppv1-endpoint-2 /
  endpoint-policy-2);
- **F03 不同来路与重复来源不增独立支持**:证据条目按"观察身份"
  (来源引用集合 + basis + 声明 + 窗口/检测/条件)去重后计数;
  同一来源的多个引用/同一观察的多个包装只算一次独立支持;
  **来路不删除** —— 全部原始条目按原样保留,只有计数用去重口径;
  模型预测/路径推断不能单独产生 supported_*(只作披露)。

终点证据字段(spec §10/§17.3.5;证据声明必须可完整追溯):
evidence_basis(direct_observation/inferred_from_pathway/model_
prediction/no_evidence)、endpoint_claim(该证据声称的终点类型)、
source_refs(来源引用)、source_support_scope(来源支持范围)、
conditions_environment(条件与环境)、observation_window(观察
时间/窗口)、detection_range(检测范围)、necessary_dependencies
(必要依赖)、root_carbon_fate_check_scope(根碳去向核查范围)、
unverified_axes(未核实轴)、proof_scope(证明范围)。

声明级充分性(claim 所需字段缺失 ⇒ 该证据不足以支持该 claim,
评估保持 unknown 并逐字段披露缺失;不是把证据丢掉):

- metabolic_handoff:source_refs + source_support_scope;
- supported_terminal_transformation_product:source_refs +
  source_support_scope + conditions_environment + observation_window
  + detection_range;
- supported_mineralization:terminal 五字段 + root_carbon_fate_
  check_scope + necessary_dependencies(缺根碳去向/来源终点证据/
  必要条件 ⇒ unknown,任务书 §4.5)。

根碳账规则(任务书 §4.5/§8 根碳账行):

- bookkeeping 只核"声明范围内账面闭合";root_carbon_accounting_
  coverage 是**核查范围**(查了什么),不是"所有根碳已转化";
- 不同备选反应生成的 CO₂ **不相加**(逐事件/逐备选列示,运行级
  聚合值不产生);
- 单项 CO₂ 产物不自动解释为根污染物矿化(root_carbon_fate_status
  恒不由 bookkeeping 产生);
- 账目闭合不等于发生矿化,也不等于生物可行。

入口矩阵(每处消费的事实/权威/校验/失败表示):

| # | 入口 | 消费事实 | 独立权威 | 校验 | 失败表示 |
| 1 | derive_run_endpoint | stop ledger(持久行)/事件行/上下文 artifact/冻结计划证据/**必要条件同源 route_assessment** | search_actions/events/search_attempts + path_context artifact + frozen plan | stop report 六原因枚举;证据字段契约;去重同源 canonical_json;必要条件 = PathContext 同源评估 | 派生内契约违反 ⇒ EndpointContractError(零写入) |
| 2 | put_stop_record / put_endpoint_record | 派生载荷 | 本表行 | payload_hash 全量哈希;幂等同内容重写零漂移 | 同 run 异内容 = 正常更新(派生投影,不是事件);损坏行读取先拒 |
| 3 | read_run_endpoint(非严格) | endpoint/stop 行 | DB 行 | 版本门 + payload_hash 复算 + 跨表引用一致 + 与当前事实的 staleness 对照(含 route_conditions_digest) | 缺失 ⇒ None;损坏/未知版本/过期 ⇒ 结构化失败(保全,不覆盖) |
| 4 | consume_run_endpoint(严格首消费) | 同上 | 同上 + 当前 events/actions/依赖/证据/必要条件摘要 | 同上全部 + 任一输入漂移 ⇒ endpoint_record_stale 拒 | 拒绝 = 零写入、原行保全 |
| 5 | build_native_result(native_result.py) | endpoint 记录 + 全部持久事实 | 本模块产出的 endpoint/stop 记录 + store 行 | 只消费已验证记录 | 过期/损坏先拒,不包装成"正式结果" |

resume/replay:derive 只读业务表(事件/假设/状态/动作行零写入),
重复 resume 重复派生同内容 ⇒ 同 payload_hash(幂等;不重复写
event/attempt/request/budget);事实变化(激活/新事件)⇒ 行更新
(payload_hash 变化如实反映)。
"""

from __future__ import annotations

import json

from ..domain.models import content_hash, now_iso
from .profile import (
    PPV1_ENDPOINT_SCHEMA_VERSION,
    PPV1_ENDPOINT_POLICY_VERSION,
    PPV1_SEARCH_SCHEMA_VERSION,
)

# ---- 执行状态(执行会话本身;与停止原因/终点/账目互不代替) ----

EXECUTION_STATUS_COMPLETED = "completed"
EXECUTION_STATUS_FAILED = "failed"
EXECUTION_STATUS_INCOMPLETE = "incomplete"
EXECUTION_STATUSES = frozenset({
    EXECUTION_STATUS_COMPLETED, EXECUTION_STATUS_FAILED,
    EXECUTION_STATUS_INCOMPLETE,
})

# ---- 化学终点评估(四值;spec §10) ----

ENDPOINT_UNKNOWN = "unknown"
ENDPOINT_METABOLIC_HANDOFF = "metabolic_handoff"
ENDPOINT_SUPPORTED_TERMINAL_TRANSFORMATION_PRODUCT = (
    "supported_terminal_transformation_product")
ENDPOINT_SUPPORTED_MINERALIZATION = "supported_mineralization"
ENDPOINT_ASSESSMENTS = frozenset({
    ENDPOINT_UNKNOWN, ENDPOINT_METABOLIC_HANDOFF,
    ENDPOINT_SUPPORTED_TERMINAL_TRANSFORMATION_PRODUCT,
    ENDPOINT_SUPPORTED_MINERALIZATION,
})
# 评估取"已获支持的最强声明"(mineralization > terminal product >
# handoff);无支持 ⇒ unknown
_ENDPOINT_CLAIM_RANK = {
    ENDPOINT_METABOLIC_HANDOFF: 1,
    ENDPOINT_SUPPORTED_TERMINAL_TRANSFORMATION_PRODUCT: 2,
    ENDPOINT_SUPPORTED_MINERALIZATION: 3,
}

# ---- 证据依据类型(表示依据种类,非固定强度次序;spec §17.3.5) ----

EVIDENCE_BASIS_DIRECT_OBSERVATION = "direct_observation"
EVIDENCE_BASIS_INFERRED_FROM_PATHWAY = "inferred_from_pathway"
EVIDENCE_BASIS_MODEL_PREDICTION = "model_prediction"
EVIDENCE_BASIS_NO_EVIDENCE = "no_evidence"
EVIDENCE_BASES = frozenset({
    EVIDENCE_BASIS_DIRECT_OBSERVATION,
    EVIDENCE_BASIS_INFERRED_FROM_PATHWAY,
    EVIDENCE_BASIS_MODEL_PREDICTION,
    EVIDENCE_BASIS_NO_EVIDENCE,
})

# 证据声明的终点 claim(与评估枚举对应,minus unknown)
ENDPOINT_CLAIMS = frozenset({
    ENDPOINT_METABOLIC_HANDOFF,
    ENDPOINT_SUPPORTED_TERMINAL_TRANSFORMATION_PRODUCT,
    ENDPOINT_SUPPORTED_MINERALIZATION,
})

# ---- 账目闭合状态(只表达账面;不等于矿化/生物可行) ----

BOOKKEEPING_CLOSED_WITHIN_DECLARED_SCOPE = "closed_within_declared_scope"
BOOKKEEPING_NOT_CLOSED = "not_closed"
BOOKKEEPING_UNKNOWN = "unknown"
BOOKKEEPING_STATUSES = frozenset({
    BOOKKEEPING_CLOSED_WITHIN_DECLARED_SCOPE,
    BOOKKEEPING_NOT_CLOSED,
    BOOKKEEPING_UNKNOWN,
})

# ---- 根碳账核查范围(coverage = 查了什么,不是"已全部转化") ----

ROOT_CARBON_COVERAGE_NONE = "no_events_no_account"
ROOT_CARBON_COVERAGE_DECLARED_PARTICIPANTS = (
    "declared_participants_of_submitted_events")

# CO2 的规范 SMILES(元素账/根碳账的矿化标志物;O=C=O)
CO2_SMILES = "O=C=O"


class EndpointContractError(RuntimeError):
    """endpoint 分账契约违反(结构化 fail-closed;零写入)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 证据声明


# 各 claim 的充分性字段(缺失 ⇒ 该证据不足以支持该 claim,逐字段披露;
# 不是把证据丢掉 —— 证据整体保留,评估保持 unknown)
_CLAIM_REQUIRED_FIELDS = {
    ENDPOINT_METABOLIC_HANDOFF: ("source_refs", "source_support_scope"),
    ENDPOINT_SUPPORTED_TERMINAL_TRANSFORMATION_PRODUCT: (
        "source_refs", "source_support_scope", "conditions_environment",
        "observation_window", "detection_range"),
    ENDPOINT_SUPPORTED_MINERALIZATION: (
        "source_refs", "source_support_scope", "conditions_environment",
        "observation_window", "detection_range",
        "root_carbon_fate_check_scope", "necessary_dependencies"),
}

_EVIDENCE_LIST_FIELDS = (
    "source_refs", "necessary_dependencies", "unverified_axes")


def _evidence_dedup_key(entry: dict) -> str:
    """观察身份(F03 去重键):同一观察的多个包装/同一来源的重复
    记录在计数上只算一次。**来路不删除** —— 原始条目全部保留,
    只有独立支持计数使用本键去重。"""
    return content_hash({
        "source_refs": sorted(set(map(str, entry.get("source_refs") or []))),
        "evidence_basis": str(entry.get("evidence_basis") or ""),
        "endpoint_claim": str(entry.get("endpoint_claim") or ""),
        "source_support_scope": str(entry.get("source_support_scope") or ""),
        "conditions_environment": str(
            entry.get("conditions_environment") or ""),
        "observation_window": str(entry.get("observation_window") or ""),
        "detection_range": str(entry.get("detection_range") or ""),
    })


def _evidence_source_identity(entry: dict) -> str:
    """来源身份(F03):同一来源的多个引用只算一个独立支持组
    (spec §5.4);无来源引用的证据不能支持任何 claim。"""
    refs = sorted(set(map(str, entry.get("source_refs") or [])))
    return content_hash({"source_refs": refs})


def validate_endpoint_evidence_entry(entry, index: int) -> dict:
    """校验/规范一条终点证据声明(冻结计划输入侧;fail-closed)。

    - dict + evidence_basis/endpoint_claim 枚举合法;
    - 列表字段必须是 list(str 化);其余字段为可选字符串;
    - 不猜补字段、不改写声明内容(仅深拷贝 + 列表元素规范化);
    - 声明级字段充分性在评估时逐 claim 核(此处只核形状)。
    """
    if not isinstance(entry, dict):
        raise EndpointContractError(
            f"endpoint_evidence[{index}] 必须是 dict,得到 "
            f"{type(entry).__name__}(来源层证据声明;不猜形状)",
            {"kind": "endpoint_evidence_invalid_type", "index": index})
    basis = str(entry.get("evidence_basis") or "")
    if basis not in EVIDENCE_BASES:
        raise EndpointContractError(
            f"endpoint_evidence[{index}].evidence_basis 非法:{basis!r}"
            f"(允许 {sorted(EVIDENCE_BASES)};表示依据种类,不是强度)",
            {"kind": "endpoint_evidence_basis_invalid", "index": index,
             "evidence_basis": basis})
    claim = str(entry.get("endpoint_claim") or "")
    if claim not in ENDPOINT_CLAIMS:
        raise EndpointContractError(
            f"endpoint_evidence[{index}].endpoint_claim 非法:{claim!r}"
            f"(允许 {sorted(ENDPOINT_CLAIMS)})",
            {"kind": "endpoint_evidence_claim_invalid", "index": index,
             "endpoint_claim": claim})
    out = dict(entry)
    for field in _EVIDENCE_LIST_FIELDS:
        value = out.get(field)
        if value is None:
            out[field] = []
            continue
        if not isinstance(value, list):
            raise EndpointContractError(
                f"endpoint_evidence[{index}].{field} 必须是 list",
                {"kind": "endpoint_evidence_field_invalid", "index": index,
                 "field": field, "type": type(value).__name__})
        out[field] = [str(v) for v in value]
    for field in ("source_support_scope", "conditions_environment",
                  "observation_window", "detection_range",
                  "root_carbon_fate_check_scope", "proof_scope", "note"):
        value = out.get(field)
        if value is not None and not isinstance(value, str):
            raise EndpointContractError(
                f"endpoint_evidence[{index}].{field} 必须是 str",
                {"kind": "endpoint_evidence_field_invalid", "index": index,
                 "field": field, "type": type(value).__name__})
        out[field] = "" if value is None else str(value)
    return out


def validate_endpoint_evidence(raw) -> list[dict]:
    """冻结计划的 endpoint_evidence 声明列表 → 规范证据条目列表。"""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise EndpointContractError(
            "plan.endpoint_evidence 必须是 list(来源层证据声明列表)",
            {"kind": "endpoint_evidence_list_invalid",
             "type": type(raw).__name__})
    return [validate_endpoint_evidence_entry(e, i)
            for i, e in enumerate(raw)]


# ---------------------------------------------------------------- 事实采集


def _events_digest(events: list[dict]) -> str:
    return content_hash([
        {"event_id": str(e["event_id"]),
         "event_semantics_hash": str(e["event_semantics_hash"])}
        for e in sorted(events, key=lambda e: str(e["event_id"]))])


def _search_actions_digest(conn, run_id: str) -> str:
    rows = conn.execute(
        "SELECT action_id, status, defer_reason FROM search_actions"
        " WHERE run_id = ? ORDER BY action_id", (run_id,)).fetchall()
    return content_hash([[str(r["action_id"]), str(r["status"]),
                          str(r["defer_reason"] or "")] for r in rows])


def _inherited_unresolved_dependencies(ledger) -> list[dict]:
    """F02:route 上未解决必要依赖(上下文 Dependency status != supported
    ⇒ unresolved/contradicted)沿途保留。上下文从 search_actions 的
    context_ref 去重枚举(稳定次序),经 H07 + 内容身份首消费守卫读取
    (load_context);同 dependency_id 去重,保留完整字段(来源/声明/
    resolution_log 摘要)。"""
    from .production import load_context
    rows = ledger.conn.execute(
        "SELECT DISTINCT context_ref FROM search_actions WHERE run_id = ?"
        " AND context_ref != '' ORDER BY context_ref",
        (ledger.run_id,)).fetchall()
    seen: dict[str, dict] = {}
    for row in rows:
        context_ref = str(row["context_ref"])
        try:
            context = load_context(ledger.artifact_store, context_ref)
        except Exception as exc:  # noqa: BLE001 —— H07/身份失败如实上抛
            raise EndpointContractError(
                f"endpoint 派生消费上下文 {context_ref} 失败(首消费守卫;"
                "不清洗后继续)",
                {"kind": "endpoint_context_consumption_failed",
                 "context_ref": context_ref,
                 "error": f"{type(exc).__name__}: {exc}"[:200]}) from exc
        for dep in (context.to_dict().get("dependencies") or []):
            if not isinstance(dep, dict):
                continue
            status = str(dep.get("status") or "")
            if status in ("supported",):
                continue
            dep_id = str(dep.get("dependency_id") or "")
            if dep_id and dep_id in seen:
                continue  # 同依赖多来路去重(来路在 resolution_log 保留)
            seen[dep_id] = {
                "dependency_id": dep_id,
                "kind": str(dep.get("kind") or ""),
                "statement": str(dep.get("statement") or ""),
                "status": status,
                "source_refs": list(dep.get("source_refs") or []),
                "introduced_at_hypothesis_id": str(
                    dep.get("introduced_at_hypothesis_id") or ""),
                "context_ref": context_ref,
            }
    return sorted(seen.values(), key=lambda d: d["dependency_id"])


def _route_condition_assessments(ledger) -> list[dict]:
    """S4-C01(确认复核 §4):当前路线已引入的**必要条件**评估消费。

    与 F02 依赖继承同一来源面(search_actions.context_ref 去重枚举的
    上下文,经 load_context H07 + 内容身份首消费),消费**同源**
    ``PathContext.route_assessment()``(历史快照逐边合取 + 当前阶段
    live;旧边结论按记录值消费,不拿当前事实重评后洗白),收集:

    - 每上下文的 requirement_coverage 摘要(unknown_keys/conflict_
      keys/essential_keys)与 environment_fit;
    - **必要**(level=essential 且 basis=essential_claimed_by_source)
      且 status ∈ {unknown, conflict} 的逐条评估行**全文保留**
      (key/status/reason/fact_sources/requirement_signature/
      route_edge_source 等;不解析自由文本,不改化学门);
    - 阻断输入 = 必要条件 unknown/conflict 行(与 F02 未解决依赖
      同层);无必要要求或全部满足的上下文只记摘要,不构成阻断
      (合法正控保持 supported,不"全拒")。

    上下文消费失败 ⇒ endpoint_context_consumption_failed 结构化拒
    (不清洗后继续)。"""
    from .path_context import (
        CONFLICT as _CONFLICT,
        REQUIREMENT_BASIS_ESSENTIAL_CLAIMED as _ESSENTIAL_CLAIMED,
        REQUIREMENT_ESSENTIAL as _ESSENTIAL,
        UNKNOWN as _UNKNOWN,
    )
    from .production import load_context
    rows = ledger.conn.execute(
        "SELECT DISTINCT context_ref FROM search_actions WHERE run_id = ?"
        " AND context_ref != '' ORDER BY context_ref",
        (ledger.run_id,)).fetchall()
    out: list[dict] = []
    for row in rows:
        context_ref = str(row["context_ref"])
        try:
            context = load_context(ledger.artifact_store, context_ref)
        except Exception as exc:  # noqa: BLE001 —— H07/身份失败如实上抛
            raise EndpointContractError(
                f"endpoint 派生消费上下文 {context_ref} 失败(首消费守卫;"
                "不清洗后继续)",
                {"kind": "endpoint_context_consumption_failed",
                 "context_ref": context_ref,
                 "error": f"{type(exc).__name__}: {exc}"[:200]}) from exc
        assessment = context.route_assessment()
        coverage = dict(assessment.requirement_coverage or {})
        necessary_rows = [
            dict(r) for r in (assessment.per_requirement or [])
            if isinstance(r, dict)
            and str(r.get("level") or "") == _ESSENTIAL
            and str(r.get("basis") or "") == _ESSENTIAL_CLAIMED]
        blocking_rows = [
            r for r in necessary_rows
            if str(r.get("status") or "") in (_UNKNOWN, _CONFLICT)]
        out.append({
            "context_ref": context_ref,
            "environment_fit": str(assessment.environment_fit or ""),
            "requirement_coverage": {
                "essential_keys": list(coverage.get("essential_keys") or []),
                "unknown_keys": list(coverage.get("unknown_keys") or []),
                "conflict_keys": list(coverage.get("conflict_keys") or []),
            },
            "necessary_unmet_per_requirement": blocking_rows,
            "source": ("PathContext.route_assessment(历史快照逐边合取 + "
                       "当前阶段 live;旧边按记录值消费,不重评)"),
        })
    return out


def _necessary_condition_keys(route_conditions: list[dict]) -> tuple:
    """必要条件 unknown/conflict 键聚合(去重稳定排序;来自同源
    route_assessment 的阻断行,不解析自由文本)。"""
    unknown: set[str] = set()
    conflict: set[str] = set()
    for entry in route_conditions or []:
        for row in entry.get("necessary_unmet_per_requirement") or []:
            key = str(row.get("key") or "")
            if not key:
                continue
            if str(row.get("status") or "") == "conflict":
                conflict.add(key)
            else:
                unknown.add(key)
    return sorted(unknown), sorted(conflict)


def _route_conditions_snapshot(ledger) -> dict:
    """条件/环境快照(终点证据保留字段的条件侧输入):上下文条件
    事实按 key 聚合已知/未知计数与冲突计数;known_conflict 的评估归
    path_context(route_assessment),此处只采事实不重评估。"""
    from .production import load_context
    rows = ledger.conn.execute(
        "SELECT DISTINCT context_ref FROM search_actions WHERE run_id = ?"
        " AND context_ref != '' ORDER BY context_ref",
        (ledger.run_id,)).fetchall()
    known: dict[str, int] = {}
    unknown: dict[str, int] = {}
    for row in rows:
        context = load_context(ledger.artifact_store, str(row["context_ref"]))
        payload = context.to_dict()
        for fact in (payload.get("condition_facts") or []):
            if not isinstance(fact, dict):
                continue
            key = str(fact.get("key") or "")
            status = str(fact.get("status") or "")
            if status == "unknown":
                unknown[key] = unknown.get(key, 0) + 1
            elif status:
                known[key] = known.get(key, 0) + 1
    return {"condition_keys_known": sorted(known),
            "condition_keys_unknown": sorted(unknown),
            "note": ("条件事实快照(来路/评估权威在 PathContext;此处"
                     "只采计数,不重评估、不把未知条件判缺席")}


def _bookkeeping_from_events(store, events: list[dict]) -> dict:
    """账目分账(声明范围内账面闭合;与终点/停止互不代替)。

    - 参与物系数:任何事件存在 unknown 系数 ⇒ 账目 unknown(未知系数
      不猜数值);
    - 参与物状态引用悬空(states 行缺失)⇒ not_closed(引用完整性);
    - CO₂:逐事件/逐假设列示(备选反应各自保留,**不相加**;运行级
      聚合不产生);
    - root_carbon_accounting_coverage = 核查范围(查了什么),不是
      "所有根碳已转化";root_carbon_fate_status 只能来自证据
      (root_carbon_fate_inferred_from_bookkeeping: false 恒成立);
    - 账平只表示核查范围内账面闭合,不等于矿化,不等于生物可行。
    """
    unknown_coefficient_events: list[dict] = []
    missing_state_refs: list[dict] = []
    co2_occurrences: list[dict] = []
    participants_total = 0
    participants_known_coefficient = 0
    for event in sorted(events, key=lambda e: str(e["event_id"])):
        event_id = str(event["event_id"])
        payload = json.loads(event["payload"]) if isinstance(
            event.get("payload"), str) else (event.get("payload") or {})
        participants = payload.get("participants") or []
        event_unknown = False
        for p in participants:
            if not isinstance(p, dict):
                continue
            participants_total += 1
            coefficient_status = str(p.get("coefficient_status") or "")
            if coefficient_status == "known":
                participants_known_coefficient += 1
            else:
                event_unknown = True
            state_ref = str(p.get("state_ref") or "")
            if state_ref and store.get_state(state_ref) is None:
                missing_state_refs.append(
                    {"event_id": event_id, "state_ref": state_ref})
        if event_unknown:
            unknown_coefficient_events.append(
                {"event_id": event_id,
                 "hypothesis_id": str(event.get("hypothesis_id") or "")})
        # CO₂ 出现(逐事件;聚合禁止)
        for p in participants:
            if not isinstance(p, dict) or p.get("side") != "product":
                continue
            state_ref = str(p.get("state_ref") or "")
            state = store.get_state(state_ref) if state_ref else None
            if state is None:
                continue
            if str(state.get("smiles_isomeric") or "") == CO2_SMILES:
                co2_occurrences.append({
                    "event_id": event_id,
                    "hypothesis_id": str(event.get("hypothesis_id") or ""),
                    "parent_path_id": str(event.get("parent_path_id") or ""),
                    "state_ref": state_ref})
    if not events:
        bookkeeping_status = BOOKKEEPING_UNKNOWN
        coverage = ROOT_CARBON_COVERAGE_NONE
    elif missing_state_refs:
        bookkeeping_status = BOOKKEEPING_NOT_CLOSED
        coverage = ROOT_CARBON_COVERAGE_DECLARED_PARTICIPANTS
    elif unknown_coefficient_events:
        bookkeeping_status = BOOKKEEPING_UNKNOWN
        coverage = ROOT_CARBON_COVERAGE_DECLARED_PARTICIPANTS
    else:
        bookkeeping_status = BOOKKEEPING_CLOSED_WITHIN_DECLARED_SCOPE
        coverage = ROOT_CARBON_COVERAGE_DECLARED_PARTICIPANTS
    return {
        "bookkeeping_status": bookkeeping_status,
        "root_carbon_accounting_coverage": coverage,
        "participants_total": participants_total,
        "participants_known_coefficient": participants_known_coefficient,
        "events_with_unknown_coefficients": unknown_coefficient_events,
        "missing_participant_state_refs": missing_state_refs,
        "co2_product_occurrences": co2_occurrences,
        "co2_aggregated": False,
        "co2_run_total": None,
        "root_carbon_fate_status": "unknown",
        "root_carbon_fate_inferred_from_bookkeeping": False,
        "note": ("账目闭合只表示声明范围内账面闭合(参与物/系数引用"
                 "完整),不等于发生矿化,也不等于生物可行;不同备选"
                 "反应生成的 CO₂ 不相加(逐事件/逐备选列示,运行级聚合"
                 "不产生);root carbon accounting coverage 只表示核查"
                 "范围,不表示所有根碳已转化;单项 CO₂ 产物不自动解释"
                 "为根污染物矿化"),
    }


def _assess_endpoint(evidence: list[dict],
                     inherited_unresolved: list[dict],
                     route_conditions: list[dict] | None = None) -> dict:
    """chemical_endpoint_assessment 派生(四值;只由独立终点证据决定)。

    - F01:无证据/证据不足 ⇒ unknown(停止原因永不映射为终点);
    - 证据依据只有 direct_observation 可支持 claim;
      inferred_from_pathway/model_prediction/no_evidence 只作披露
      (模型预测或路径推断不能单独产生 supported_*);
    - 声明级充分性:claim 所需字段缺失 ⇒ 不足以支持,逐字段披露;
    - F02:存在未解决必要依赖 ⇒ 评估保持 unknown(evidence 保留;
      blocked_reasons 披露;resolved 后同证据可支持);
    - S4-C01(确认复核 §4):当前路线已引入的**必要条件**存在
      unknown/conflict(同源 route_assessment,历史快照消费)⇒ 评估
      同样保持 unknown(evidence 全文保留;blocked_reasons 披露;
      已知兼容正控/无必要条件不受影响 —— 不全拒、不改化学门);
    - F03:计数用去重口径(观察身份 + 来源身份),来路全保留;
    - 评估 = 已获支持的最强声明;mineralization 优先于 terminal
      product 优先于 handoff(同为来源层声明,取较强者)。
    """
    route_conditions = list(route_conditions or [])
    unknown_keys, conflict_keys = _necessary_condition_keys(route_conditions)
    dedup_by_key: dict[str, list[dict]] = {}
    for entry in evidence:
        dedup_by_key.setdefault(_evidence_dedup_key(entry), []).append(entry)
    deduped = [entries[0] for entries in dedup_by_key.values()]
    duplicate_disclosures = [
        {"observation_identity": key,
         "wrapped_references": len(entries)}
        for key, entries in sorted(dedup_by_key.items())
        if len(entries) > 1]
    direct = [e for e in deduped
              if e.get("evidence_basis") == EVIDENCE_BASIS_DIRECT_OBSERVATION
              and (e.get("source_refs") or [])]
    source_identities = {_evidence_source_identity(e) for e in direct}
    basis_counts: dict[str, int] = {}
    for entry in deduped:
        basis = str(entry.get("evidence_basis"))
        basis_counts[basis] = basis_counts.get(basis, 0) + 1
    blocked_reasons: list[str] = []
    missing_field_disclosures: list[dict] = []
    supported_claims: dict[str, list[str]] = {}
    for entry in direct:
        claim = str(entry.get("endpoint_claim"))
        required = _CLAIM_REQUIRED_FIELDS.get(claim, ())
        missing = [f for f in required
                   if not (entry.get(f) or [])] if required else []
        # 必要依赖字段非空 list 才算声明了必要依赖
        if "necessary_dependencies" in required and \
                not (entry.get("necessary_dependencies") or []):
            missing.append("necessary_dependencies")
        if missing:
            missing_field_disclosures.append({
                "endpoint_claim": claim,
                "missing_fields": sorted(set(missing)),
                "source_refs": list(entry.get("source_refs") or [])})
            continue
        supported_claims.setdefault(claim, []).append(
            _evidence_source_identity(entry))
    if inherited_unresolved:
        blocked_reasons.append("unresolved_dependencies_inherited")
    if unknown_keys:
        blocked_reasons.append("necessary_conditions_unknown")
    if conflict_keys:
        blocked_reasons.append("necessary_conditions_conflict")
    assessment = ENDPOINT_UNKNOWN
    if not blocked_reasons and supported_claims:
        assessment = max(
            supported_claims,
            key=lambda claim: _ENDPOINT_CLAIM_RANK.get(claim, 0))
    elif blocked_reasons and supported_claims:
        # F02:证据存在且充分,但 route 未解决必要依赖 ⇒ 评估保持
        # unknown;证据与"若无未解决依赖本可支持的声明"一并披露
        assessment = ENDPOINT_UNKNOWN
    return {
        "chemical_endpoint_assessment": assessment,
        "endpoint_evidence": list(evidence),
        "evidence_summary": {
            "evidence_entries_total": len(evidence),
            "distinct_observation_claims": len(deduped),
            "direct_observation_entries": len(direct),
            "independent_source_support_count": len(source_identities),
            "basis_counts": dict(sorted(basis_counts.items())),
            "duplicate_evidence_disclosures": duplicate_disclosures,
            "supported_claims_without_route_blockers": sorted(
                supported_claims),
            "supported_claim_evidence": {
                claim: sorted(set(ids))
                for claim, ids in sorted(supported_claims.items())},
            "missing_field_disclosures": missing_field_disclosures,
            "blocked_reasons": blocked_reasons,
            "necessary_condition_unknown_keys": unknown_keys,
            "necessary_condition_conflict_keys": conflict_keys,
            "dedup_note": ("F03 去重口径 = 观察身份(来源引用集合 + "
                           "basis + 声明 + 窗口/检测/条件)与来源身份"
                           "(来源引用集合);来路不删除,全部原始条目"
                           "保留在 endpoint_evidence;同一来源多个引用"
                           "/同一观察多个包装不增加独立支持"),
        },
        "inherited_unresolved_dependencies": list(inherited_unresolved),
        "assessment_note": ("评估只由独立终点证据决定(来源层直报;"
                            "模型预测/路径推断不能单独产生 supported_*;"
                            "停止原因永不映射为终点(F01);存在未解决"
                            "必要依赖时评估保持 unknown(F02);当前路线"
                            "已引入的必要条件 unknown/conflict 同样保持"
                            " unknown(S4-C01,同源 route_assessment;"
                            "已知兼容正控不受影响));"
                            "metabolic_handoff 不等于矿化;"
                            "supported_terminal_transformation_product"
                            " 不推断永久去除"),
    }


# ---------------------------------------------------------------- 持久化


def put_stop_record(conn, run_id: str, stop_report: dict) -> dict:
    """停止原因独立持久化(stop_reason_records 表;与 endpoint 记录
    分表 —— 搜索停止是执行事实,不是化学终点)。幂等:同内容重写
    payload_hash 不变;同 run 事实变化 ⇒ 行更新(派生投影)。"""
    payload = {
        "record_version": PPV1_ENDPOINT_SCHEMA_VERSION,
        "run_id": run_id,
        "stop_report": stop_report,
    }
    payload_hash = content_hash(payload)
    now = now_iso()
    conn.execute(
        "INSERT INTO stop_reason_records (run_id, payload, payload_hash,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(run_id) DO UPDATE SET payload = excluded.payload,"
        " payload_hash = excluded.payload_hash,"
        " updated_at = excluded.updated_at",
        (run_id, json.dumps(payload, ensure_ascii=False, sort_keys=True),
         payload_hash, now, now))
    conn.commit()
    return {"run_id": run_id, "payload_hash": payload_hash}


def read_stop_record(conn, run_id: str) -> dict | None:
    row = conn.execute(
        "SELECT payload, payload_hash FROM stop_reason_records WHERE"
        " run_id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    payload = json.loads(row["payload"])
    if content_hash(payload) != str(row["payload_hash"]):
        raise EndpointContractError(
            f"stop_reason_records[{run_id}] payload_hash 复算不一致"
            "(完整性失败;保全原行,不覆盖)",
            {"kind": "stop_record_corrupt", "run_id": run_id})
    return payload


def put_endpoint_record(conn, run_id: str, record: dict) -> dict:
    """endpoint 四分账记录持久化(endpoint_records 表)。幂等同内容
    重写;resume 重复派生同内容 ⇒ 同 hash 零事实漂移。"""
    payload = dict(record)
    payload_hash = content_hash(payload)
    now = now_iso()
    conn.execute(
        "INSERT INTO endpoint_records (run_id, payload, payload_hash,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(run_id) DO UPDATE SET payload = excluded.payload,"
        " payload_hash = excluded.payload_hash,"
        " updated_at = excluded.updated_at",
        (run_id, json.dumps(payload, ensure_ascii=False, sort_keys=True),
         payload_hash, now, now))
    conn.commit()
    return {"run_id": run_id, "payload_hash": payload_hash}


def _endpoint_current_input_digests(ledger, evidence: list[dict]) -> dict:
    """首消费 staleness 校验的重算输入(与派生时的 derived_from 同源;
    stop 报告含会话 refusals 不可无会话复算 —— 以持久化 stop 记录行
    的 hash 作跨表一致性,不参与本重算)。"""
    events = ledger.store.list_events(ledger.run_id)
    inherited = _inherited_unresolved_dependencies(ledger)
    route_conditions = _route_condition_assessments(ledger)
    return {
        "events_digest": _events_digest(events),
        "search_actions_digest": _search_actions_digest(
            ledger.conn, ledger.run_id),
        "endpoint_evidence_digest": content_hash(evidence),
        "inherited_dependencies_digest": content_hash(inherited),
        "route_conditions_digest": content_hash(route_conditions),
    }


def read_run_endpoint(ledger, run_id: str, *, strict: bool = False) -> dict:
    """endpoint 记录读取(首消费:版本门 + payload_hash 复算 + 跨表
    stop 引用一致 + staleness 重算对照)。

    - 非严格:缺失 ⇒ None;损坏/未知版本/stale ⇒ 结构化失败(保全
      原行,零写入,不清洗后继续);
    - 严格(consume):同上全部;任一输入漂移 ⇒ endpoint_record_stale
      拒(旧记录不能被静默当作当前结果);
    - 停止原因独立行(stop_reason_records)hash 与记录内引用交叉核对。
    """
    row = ledger.conn.execute(
        "SELECT payload, payload_hash FROM endpoint_records WHERE"
        " run_id = ?", (run_id,)).fetchone()
    if row is None:
        if strict:
            raise EndpointContractError(
                f"run {run_id} 无 endpoint 记录(先经公共 start/resume"
                " 派生;不猜默认)",
                {"kind": "endpoint_record_missing", "run_id": run_id})
        return None
    payload = json.loads(row["payload"])
    if content_hash(payload) != str(row["payload_hash"]):
        raise EndpointContractError(
            f"endpoint_records[{run_id}] payload_hash 复算不一致"
            "(完整性失败;保全原行,不覆盖、不重算新 ID 洗白)",
            {"kind": "endpoint_record_corrupt", "run_id": run_id})
    version = str(payload.get("schema_version") or "")
    if version != PPV1_ENDPOINT_SCHEMA_VERSION:
        raise EndpointContractError(
            f"endpoint 记录 schema 版本未知:{version!r}(当前 "
            f"{PPV1_ENDPOINT_SCHEMA_VERSION};fail-closed 不猜迁移)",
            {"kind": "endpoint_record_version_unknown", "run_id": run_id,
             "schema_version": version})
    stop_ref = str(
        (payload.get("search_stop_reason") or {}).get(
            "stop_record_payload_hash") or "")
    stop_row = ledger.conn.execute(
        "SELECT payload_hash FROM stop_reason_records WHERE run_id = ?",
        (run_id,)).fetchone()
    stop_hash = str(stop_row["payload_hash"]) if stop_row is not None else ""
    if not stop_ref or stop_hash != stop_ref:
        raise EndpointContractError(
            f"endpoint 记录与停止记录交叉引用不一致(四分账独立持久"
            "化;引用断裂 ⇒ 结构化失败,不猜补)",
            {"kind": "endpoint_stop_reference_mismatch", "run_id": run_id,
             "endpoint_stop_ref": stop_ref, "stop_record_hash": stop_hash})
    derived_from = payload.get("derived_from") or {}
    evidence = validate_endpoint_evidence(
        (payload.get("endpoint_evidence_source") or {}).get(
            "raw_plan_endpoint_evidence"))
    current = _endpoint_current_input_digests(ledger, evidence)
    changed = sorted(
        key for key, value in current.items()
        if str(derived_from.get(key)) != str(value))
    policy_changed = str(derived_from.get("endpoint_policy_version")) \
        != PPV1_ENDPOINT_POLICY_VERSION
    if changed or policy_changed:
        raise EndpointContractError(
            f"endpoint 记录已过期(输入事实与当前持久权威不一致:"
            f"{changed or ['endpoint_policy_version']};旧记录不能被"
            "静默当作当前结果 —— 拒绝消费,重新派生走公共 start/resume)",
            {"kind": "endpoint_record_stale", "run_id": run_id,
             "changed_inputs": changed,
             "policy_changed": policy_changed,
             "record_derived_from": {
                 k: derived_from.get(k) for k in current},
             "current": current})
    return payload


def consume_run_endpoint(ledger, run_id: str) -> dict:
    """endpoint 记录严格首消费(过期/损坏/缺引用 ⇒ 拒,零写入)。"""
    return read_run_endpoint(ledger, run_id, strict=True)


# ---------------------------------------------------------------- 派生


def derive_run_endpoint(ledger, *, stop_report: dict,
                        run_error: dict | None = None,
                        plan: dict | None = None) -> dict:
    """公共 start/resume 的 endpoint 四分账派生 + 独立持久化。

    消费的独立权威(全部只读,零 event/attempt/request/budget 写入):
    - stop report(驱动会话从持久行 + 会话 refusals 派生的停止账;
      停止原因六值枚举与主因优先级已在 search 层冻结);
    - events 行(参与物/系数/CO₂ → bookkeeping 分账);
    - 上下文 artifact(H07 + 内容身份首消费)→ F02 未解决依赖 +
      条件事实快照 + **必要条件同源 route_assessment(S4-C01)**;
    - 冻结计划的 endpoint_evidence 声明(来源层直报;F03 去重计数)。

    输出四分账 + 证据 + 账目 + derived_from(重算输入摘要,消费侧
    staleness 校验同源)。
    """
    run_id = ledger.run_id
    plan = plan or {}
    evidence = validate_endpoint_evidence(plan.get("endpoint_evidence"))
    events = ledger.store.list_events(run_id)
    unexplored = dict((stop_report or {}).get("unexplored") or {})
    claimed = int(unexplored.get("claimed_actions") or 0)
    open_attempts = int(unexplored.get("open_attempts") or 0)
    if run_error is not None:
        execution_status = EXECUTION_STATUS_FAILED
    elif claimed > 0 or open_attempts > 0:
        execution_status = EXECUTION_STATUS_INCOMPLETE
    else:
        execution_status = EXECUTION_STATUS_COMPLETED
    stop_persisted = put_stop_record(ledger.conn, run_id, stop_report or {})
    inherited = _inherited_unresolved_dependencies(ledger)
    route_conditions = _route_condition_assessments(ledger)
    conditions = _route_conditions_snapshot(ledger)
    bookkeeping = _bookkeeping_from_events(ledger.store, events)
    assessment = _assess_endpoint(evidence, inherited, route_conditions)
    # 根碳去向状态只能来自证据(声明了核查范围的直报证据 ⇒ 记录其
    # 声明范围;仍不是本仓自己的核实)—— 不从 bookkeeping 推导
    fate_reported = any(
        str(e.get("root_carbon_fate_check_scope") or "")
        for e in evidence)
    bookkeeping["root_carbon_fate_status"] = (
        "source_reported_check_scope_only" if fate_reported else "unknown")
    record = {
        "schema_version": PPV1_ENDPOINT_SCHEMA_VERSION,
        "run_id": run_id,
        # ---- 四分账(四者互不代替) ----
        "execution_status": execution_status,
        "search_stop_reason": {
            "primary": (stop_report or {}).get("primary"),
            "other_reasons": list(
                (stop_report or {}).get("other_reasons") or []),
            "unexplored": unexplored,
            "stop_record_payload_hash": stop_persisted["payload_hash"],
            "note": ("搜索停止是执行事实,独立持久化于 stop_reason_"
                     "records;停止原因不映射为化学终点(F01)"),
        },
        "chemical_endpoint_assessment":
            assessment["chemical_endpoint_assessment"],
        "bookkeeping_status": bookkeeping["bookkeeping_status"],
        # ---- 证据与 F02/F03 ----
        "endpoint_evidence": assessment["endpoint_evidence"],
        "evidence_summary": assessment["evidence_summary"],
        "inherited_unresolved_dependencies":
            assessment["inherited_unresolved_dependencies"],
        "assessment_note": assessment["assessment_note"],
        "endpoint_evidence_source": {
            "raw_plan_endpoint_evidence": plan.get("endpoint_evidence"),
            "source": "frozen_plan_input",
            "note": ("证据声明为冻结计划输入(S3B-01 冻结来源);来源层"
                     "直报,不代表本仓已核实来源真实性"),
        },
        # ---- 账目与条件 ----
        "bookkeeping": bookkeeping,
        "conditions_snapshot": conditions,
        # ---- S4-C01:必要条件同源评估(全文保留;阻断输入) ----
        "route_condition_assessment": {
            "contexts": route_conditions,
            "necessary_condition_unknown_keys":
                assessment["evidence_summary"][
                    "necessary_condition_unknown_keys"],
            "necessary_condition_conflict_keys":
                assessment["evidence_summary"][
                    "necessary_condition_conflict_keys"],
            "note": ("当前路线必要条件评估(同源 PathContext.route_"
                     "assessment:历史快照逐边合取 + 当前阶段 live;旧边"
                     "按记录值消费,不拿当前事实重评);必要条件存在 "
                     "unknown/conflict ⇒ 终点保持 unknown(证据全文保留,"
                     "不被 recorded 或充分字段洗白);已知兼容/无必要条件"
                     "不构成阻断(不全拒);条件评估权威在 PathContext,"
                     "此处只消费同源结果,不解析自由文本、不新增化学门"),
        },
        # ---- 运行错误与执行披露 ----
        "run_error": dict(run_error) if run_error is not None else None,
        # ---- 派生输入摘要(消费侧 staleness 同源重算) ----
        "derived_from": {
            "events_digest": _events_digest(events),
            "search_actions_digest": _search_actions_digest(
                ledger.conn, run_id),
            "endpoint_evidence_digest": content_hash(evidence),
            "inherited_dependencies_digest": content_hash(inherited),
            "route_conditions_digest": content_hash(route_conditions),
            "endpoint_policy_version": PPV1_ENDPOINT_POLICY_VERSION,
            "search_schema_version": PPV1_SEARCH_SCHEMA_VERSION,
            "derived_note": ("重算输入摘要;stop 报告含会话 refusals "
                             "不可无会话复算,以持久 stop 记录行 hash "
                             "作跨表一致性核对"),
        },
    }
    # 记录载荷不含时间戳(行自带 created_at/updated_at 列)——
    # 同事实重复派生 ⇒ 同 payload_hash(确定性;resume 重复派生
    # 零事实漂移)
    persisted = put_endpoint_record(ledger.conn, run_id, record)
    record["payload_hash"] = persisted["payload_hash"]
    return record


def endpoint_summary_fields(record: dict) -> dict:
    """公共 summary 的四分账字段(脚本输出断言面;完整记录在
    endpoint_records 表)。"""
    route_conditions = record.get("route_condition_assessment") or {}
    return {
        "execution_status": record["execution_status"],
        "search_stop_reason": record["search_stop_reason"]["primary"],
        "chemical_endpoint_assessment": record[
            "chemical_endpoint_assessment"],
        "bookkeeping_status": record["bookkeeping_status"],
        "independent_source_support_count": record["evidence_summary"][
            "independent_source_support_count"],
        "inherited_unresolved_dependencies": len(
            record["inherited_unresolved_dependencies"]),
        "necessary_condition_unknown_keys": list(
            route_conditions.get("necessary_condition_unknown_keys") or []),
        "necessary_condition_conflict_keys": list(
            route_conditions.get("necessary_condition_conflict_keys") or []),
        "payload_hash": record["payload_hash"],
    }
