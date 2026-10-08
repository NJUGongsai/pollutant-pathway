"""S3b 队列调度 —— 冻结池选择、deferred 两类分别激活、场景转换进调度
(实施书 §5.1/§5.2;契约 ppv1-search-6)。

范围(任务书 §2.3 S3b 行):`schedule_hypotheses`(selected/deferred/
blocked + 原因)、`record_expansion_outcome`(非事件尝试结论持久化)、
`activate_deferred`(共同产物 deferred 与备选反应 deferred 分别激活:
幂等/trigger/expected_parent_revision 校验、预算不足留独立未展开原因)、
`enqueue_scenario_transition`(显式支持的场景转换独立 action/预算)、
`enqueue_coproduct_followups`(事件后子产物 followup 与共同产物
deferred)。本模块只做调度事务与身份,不构造化学对象(假设构建在
pollutant/production.py,本层只冻结其产物)。

入口矩阵(每处消费的对象/身份/版本/权威及校验来源):

| # | 入口 | 消费 | 校验/事务 |
| 1 | schedule_hypotheses | 池条目(调用方经 production 冻结的 hypothesis/spec)+ 父/上下文/revision/预算视图 | 池条目结构契约(dict/hypothesis_id/payload);_limits 严格冻结块;剩余额度从预约行派生(快照不是事实源);enqueue 幂等/同键异内容冲突;深度结构性拒绝(**S3b r2/S3B-06:深度阻断对象经 record_blocked_hypothesis 持久化为 blocked 行 + 原因,stop_report 同源消费**);选中数受剩余 alternatives 与调用方 max_select 双重限制 |
| 2 | record_expansion_outcome | attempt 行 + 认领所有权 + outcome 载荷 | attempt 存在/归属本 run+本 action 且 open;action 处于 claimed 且 worker 为认领者;outcome kind 枚举;artifact 先写(expansion_outcome,不可覆盖);complete_action 走 S3A-02 完整权威核验 |
| 3 | activate_deferred | deferred action 行 + trigger + expected_parent_revision | ledger.reactivate_deferred_action 同一判据(状态/trigger/revision/预算预检);按 deferred_type 分类;trigger 不一致逐项结构化冲突;重复触发幂等 unchanged |
| 4 | enqueue_scenario_transition | 转换载荷(须显式 source_ref)+ 当前上下文 + **S3b r2/S3B-03:pending_followup(转换后 followup 的事实)在创建时一次冻结入载荷** | 转换 dict 契约(source_ref 非空、new_phase_id/new_scenario_ref);pending_followup 须非空 dict(事件/产物全集/父路径/上下文/revision/深度 —— 转换执行后按新上下文调度);enqueue 幂等/冲突;转换预算在 claim 预约(独立计,不是反应边);**入队与附随一次写入(无两写窗口,B4 恢复按冻结载荷幂等闭合)** |
| 5 | enqueue_coproduct_followups | 事件产物清单 + 展开计划(expanded/deferred/not_tracked) | 计划引用必须是事件产物参与物;宽度/预算不足的产物入 deferred(独立未展开原因);完整事件事实不截断(计划只管 followup) |

deferred 两类(任务书 §5.1):共同产物 deferred(coproduct_deferred,
对象 = 事件产物 state_ref)与父底物备选反应 deferred(
alternative_reaction_deferred,对象 = 备选假设 id)分别有类型、对象、
触发条件/未展开原因 —— 都以 search_actions 行持久化(
initial_status=deferred + defer_reason 列 + payload 内 deferred_type/
defer_trigger),激活走 reactivate_deferred_action(不重建任务输入)。

停止与未探索(任务书 §4.2/§5.1):deferred/blocked 计入未探索集合
(stop_report 已消费);存在 deferred/知识缺口时不称"所有路线都探索
完";停止不是化学终点。首选下游无候选(E01)由调用方以
record_expansion_outcome(kind=unresolved_continuation) 落账,本层不
反推上游真假。
"""

from __future__ import annotations

import json

from ..domain.models import content_hash, now_iso, stable_id
from .profile import SEARCH_LIMITS_VERSION
from .search import (
    ACTION_KIND_EXPAND_HYPOTHESIS,
    ACTION_KIND_RETRIEVE,
    ACTION_KIND_SCENARIO_TRANSITION,
    ACTION_STATUS_DEFERRED,
    ACTION_STATUS_DONE,
    ACTION_STATUS_PENDING,
    ATTEMPT_STATUS_FAILED,
    ATTEMPT_STATUS_OPEN,
    ATTEMPT_STATUS_RECORDED,
    COMMIT_KIND_OUTCOME,
    SearchContractError,
    SearchLedger,
    read_search_artifact,
)

# ---- deferred 两类(§5.1:分别有类型、对象、触发条件/未展开原因) ----

DEFERRED_TYPE_COPRODUCT = "coproduct_deferred"
DEFERRED_TYPE_ALTERNATIVE = "alternative_reaction_deferred"
DEFERRED_TYPES = frozenset({DEFERRED_TYPE_COPRODUCT,
                            DEFERRED_TYPE_ALTERNATIVE})

# 默认激活 trigger(显式决策;调用方可按需定义其他 token,激活时与
# 记录一致即可 —— 可验证 trigger = 与冻结记录一致)
DEFERRED_TRIGGER_EXPLICIT = "explicit_user"

# record_expansion_outcome 的结论 kind(非事件 outcome;枚举固定)
OUTCOME_KIND_UNRESOLVED_CONTINUATION = "unresolved_continuation"
OUTCOME_KIND_METHOD_FAILED = "method_failed"
OUTCOME_KIND_CONTRACT_ABORTED = "contract_aborted"
OUTCOME_KIND_NO_LOCAL_CANDIDATE = "no_local_candidate"
OUTCOME_KIND_POOL_DIGEST = "pool_digest"
OUTCOME_KIND_SCHEDULED = "scheduled"
OUTCOME_KIND_TRANSITION_APPLIED = "transition_applied"
OUTCOME_KIND_ACTIVATED = "activation_dispatched"
OUTCOME_KIND_ADMISSION_REJECTED = "admission_rejected"
OUTCOME_KIND_ADMISSION_DEFERRED = "admission_deferred"
OUTCOME_KINDS = frozenset({
    OUTCOME_KIND_UNRESOLVED_CONTINUATION, OUTCOME_KIND_METHOD_FAILED,
    OUTCOME_KIND_CONTRACT_ABORTED, OUTCOME_KIND_NO_LOCAL_CANDIDATE,
    OUTCOME_KIND_POOL_DIGEST, OUTCOME_KIND_SCHEDULED,
    OUTCOME_KIND_TRANSITION_APPLIED, OUTCOME_KIND_ACTIVATED,
    OUTCOME_KIND_ADMISSION_REJECTED, OUTCOME_KIND_ADMISSION_DEFERRED,
})
# method 类失败(工具/契约/方法层,不是化学判定)⇒ attempt failed;
# 其余非事件结论 ⇒ attempt recorded(如实记录结论)
_OUTCOME_FAILED_KINDS = frozenset({
    OUTCOME_KIND_METHOD_FAILED, OUTCOME_KIND_CONTRACT_ABORTED})

# 展开计划 deferred 的标准原因(与 build_expansion_plan 的 reasons 对齐)
DEFER_REASON_PRODUCT_WIDTH = "product_width_limit"
DEFER_REASON_BUDGET = "budget_limit"
DEFER_REASON_DEPTH = "depth_limit"

# 持久结论 artifact 的载荷版本
EXPANSION_OUTCOME_VERSION = "ppv1-search-outcome-1"


def child_path_id(parent_path_id: str, source_event_id: str,
                  product_state_ref: str) -> str:
    """子路径身份(确定性:父路径 + 事件 + 产物引用;同输入同 ID ⇒
    幂等,不按 CN 归并、不丢路径来路)。"""
    return stable_id("spath", parent_path_id, source_event_id,
                     product_state_ref)


def frozen_pool_digest(pool: list[dict]) -> str:
    """冻结池摘要(可重放:条目身份 + 声明次序 + 截断标记都进摘要;
    池成员/档位/原顺序不被 preview 或筛选结果改写 —— 本层不消费
    conservation_filter_and_rank 的任何筛选输出)。"""
    entries = []
    for item in pool or []:
        entries.append({
            "hypothesis_key": str(item.get("hypothesis_key", "")),
            "hypothesis_id": str(item.get("hypothesis_id", "")),
            "rank": item.get("rank"),
        })
    return content_hash({"version": SEARCH_LIMITS_VERSION,
                         "entries": entries})


# ---- 结构化异常 ----


class ScheduleContractError(SearchContractError):
    """调度输入/身份契约违反(结构化,零写入)。"""


def _validate_pool_entry(entry, index: int) -> dict:
    if not isinstance(entry, dict):
        raise ScheduleContractError(
            f"池条目 #{index} 必须是 dict,得到 {type(entry).__name__}",
            {"kind": "pool_entry_invalid_type", "index": index})
    hypothesis_id = str(entry.get("hypothesis_id") or "")
    if not hypothesis_id:
        raise ScheduleContractError(
            f"池条目 #{index} 缺 hypothesis_id(调用方经 production 冻结;"
            "调度层不构造化学对象)",
            {"kind": "pool_entry_missing_hypothesis_id", "index": index})
    payload = entry.get("payload")
    if not isinstance(payload, dict):
        raise ScheduleContractError(
            f"池条目 #{index} 的 payload 必须是 dict(冻结任务输入)",
            {"kind": "pool_entry_payload_invalid", "index": index})
    return entry


def schedule_hypotheses(
    ledger: SearchLedger,
    *,
    run_id: str,
    parent_path_id: str,
    context_ref: str,
    parent_search_revision: int,
    pool: list[dict],
    policy_version: str,
    depth: int,
    source_event_id: str = "",
    budget: dict | None = None,
    defer_trigger: str = DEFERRED_TRIGGER_EXPLICIT,
) -> dict:
    """冻结池 → selected / deferred / blocked(幂等;同键异内容冲突;
    队列待办不计预算,claim 才预约)。

    - 选中:按池声明次序(rank 升序,同 rank 按 hypothesis_id 稳定
      tie-break)取至多 `min(剩余 alternatives 额度, 调用方 max_select)`
      条,以 pending expand action 入队(subject = hypothesis_id,
      payload = 条目冻结任务输入);
    - deferred(备选反应):超出选中额度的池条目以
      initial_status=deferred 入队(deferred_type=
      alternative_reaction_deferred;独立未展开原因
      alternatives_budget / selection_cap;激活条件 defer_trigger);
    - blocked:深度超限(**S3b r2:持久 blocked 行 + 原因;不入可执
      行队列**)、同一身份的 action 已 done(无新信息不再安排 ⇒
      already_expanded)等结构性格拒;
    - 池 digest(条目身份+次序)返回给调用方进 decision 任务键
      (决策身份绑定冻结池;池成员顺序不可被调度结果改写);
    - 剩余 alternatives 从持久预约行派生(含 reserved/consumed;快照
      不是事实源);本入口零预算预约。
    """
    for i, entry in enumerate(pool or []):
        _validate_pool_entry(entry, i)
    limits = ledger._limits(run_id)
    alternatives_max = int(limits["max_alternative_hypotheses_per_parent"])
    used = 0
    for row in ledger.conn.execute(
            "SELECT scope, status, subject, units FROM budget_reservations"
            " WHERE run_id = ? AND limit_key = ? AND scope = ? AND status"
            " IN (?, ?)",
            (run_id, "max_alternative_hypotheses_per_parent",
             parent_path_id, "reserved", "consumed")).fetchall():
        used += int(row["units"])
    remaining_alternatives = max(0, alternatives_max - used)
    max_select = None
    if budget is not None:
        if not isinstance(budget, dict):
            raise ScheduleContractError(
                "budget 视图必须是 dict", {"kind": "budget_view_invalid"})
        raw = budget.get("max_select")
        if raw is not None:
            if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
                raise ScheduleContractError(
                    f"budget.max_select 非法:{raw!r}(非负整数)",
                    {"kind": "budget_max_select_invalid"})
            max_select = raw
    selectable = remaining_alternatives
    if max_select is not None:
        selectable = min(selectable, max_select)
    ordered = sorted(
        enumerate(pool or []),
        key=lambda pair: (
            (pair[1].get("rank") is None, pair[1].get("rank") or 0,
             str(pair[1].get("hypothesis_id", "")), pair[0])))
    digest = frozen_pool_digest(pool or [])
    selected: list[dict] = []
    deferred: list[dict] = []
    blocked: list[dict] = []
    taken = 0
    depth = int(depth)
    if depth > int(limits["max_search_depth"]):
        # 深度超限:整池 blocked —— **S3b r2(S3B-06):blocked 对象
        # 持久化为 search_actions 行(status=blocked,defer_reason=
        # depth_limit,冻结任务输入)**;stop_report 从持久行派生
        # depth_limit 停止原因与 blocked_objects 未探索清单(不是只存
        # 计数;blocked 不可执行,reactivate/claim 均拒)。
        for _, entry in ordered:
            blocked.append({
                "hypothesis_id": str(entry["hypothesis_id"]),
                "reason": "depth_limit",
                "action_id": "",
                "detail": {"depth": depth,
                           "max_search_depth":
                               int(limits["max_search_depth"])}})
            recorded = ledger.record_blocked_hypothesis(
                run_id=run_id, parent_path_id=parent_path_id,
                context_ref=str(entry.get("payload", {}).get(
                    "context_ref") or context_ref),
                subject_ref=str(entry["hypothesis_id"]),
                parent_search_revision=parent_search_revision,
                policy_version=policy_version,
                payload=dict(entry["payload"]),
                blocked_reason="depth_limit")
            if recorded.get("action_id"):
                blocked[-1]["action_id"] = recorded["action_id"]
                blocked[-1]["status"] = recorded.get("status")
        return {
            "run_id": run_id, "parent_path_id": parent_path_id,
            "context_ref": context_ref,
            "parent_search_revision": int(parent_search_revision),
            "pool_digest": digest, "pool_size": len(pool or []),
            "selected": selected, "deferred": deferred, "blocked": blocked,
            "remaining_alternatives": remaining_alternatives,
            "alternatives_max": alternatives_max,
        }
    for _, entry in ordered:
        hypothesis_id = str(entry["hypothesis_id"])
        # 每条目的 context_ref(分支隔离:带自身要求/依赖的假设经
        # derive_child_context 派生专属上下文;缺省用调用的父上下文)
        entry_context = str(entry.get("payload", {}).get("context_ref")
                            or context_ref)
        task_payload = dict(entry["payload"])
        task_payload.setdefault("context_ref", entry_context)
        task_payload["frozen_pool_digest"] = digest
        task_payload.setdefault("source_event_id", source_event_id)
        will_select = taken < selectable
        if will_select:
            enqueue = ledger.enqueue_action(
                run_id=run_id, parent_path_id=parent_path_id,
                context_ref=entry_context, subject_ref=hypothesis_id,
                action_kind=ACTION_KIND_EXPAND_HYPOTHESIS,
                parent_search_revision=parent_search_revision,
                policy_version=policy_version, payload=task_payload,
                depth=depth, source_event_id=source_event_id)
        else:
            reason = ("selection_cap" if max_select is not None
                      and remaining_alternatives > taken
                      else "alternatives_budget")
            task_payload["deferred_type"] = DEFERRED_TYPE_ALTERNATIVE
            task_payload["defer_reason"] = reason
            enqueue = ledger.enqueue_action(
                run_id=run_id, parent_path_id=parent_path_id,
                context_ref=entry_context, subject_ref=hypothesis_id,
                action_kind=ACTION_KIND_EXPAND_HYPOTHESIS,
                parent_search_revision=parent_search_revision,
                policy_version=policy_version, payload=task_payload,
                depth=depth, source_event_id=source_event_id,
                initial_status=ACTION_STATUS_DEFERRED,
                defer_reason=reason, defer_trigger=defer_trigger)
        if not enqueue.get("created"):
            status = enqueue.get("status")
            if enqueue.get("reason") == "depth_limit":
                # S3b r2(S3B-06):入队层深度拒绝同样持久 blocked 行
                recorded = ledger.record_blocked_hypothesis(
                    run_id=run_id, parent_path_id=parent_path_id,
                    context_ref=entry_context, subject_ref=hypothesis_id,
                    parent_search_revision=parent_search_revision,
                    policy_version=policy_version,
                    payload=dict(task_payload),
                    blocked_reason="depth_limit")
                blocked.append({"hypothesis_id": hypothesis_id,
                                "reason": "depth_limit",
                                "action_id": recorded.get("action_id")})
                continue
            if status == ACTION_STATUS_DONE:
                blocked.append({"hypothesis_id": hypothesis_id,
                                "reason": "already_expanded",
                                "action_id": enqueue.get("action_id")})
                continue
            existing = {"hypothesis_id": hypothesis_id,
                        "action_id": enqueue.get("action_id"),
                        "status": status,
                        "reason": "already_enqueued"}
            if status == ACTION_STATUS_DEFERRED:
                deferred.append(existing)
            else:
                selected.append(existing)
            continue
        if will_select:
            selected.append({"hypothesis_id": hypothesis_id,
                             "action_id": enqueue["action_id"],
                             "status": ACTION_STATUS_PENDING})
            taken += 1
        else:
            deferred.append({
                "hypothesis_id": hypothesis_id,
                "action_id": enqueue["action_id"],
                "status": ACTION_STATUS_DEFERRED,
                "deferred_type": DEFERRED_TYPE_ALTERNATIVE,
                "reason": str(task_payload.get("defer_reason")),
            })
    return {
        "run_id": run_id, "parent_path_id": parent_path_id,
        "context_ref": context_ref,
        "parent_search_revision": int(parent_search_revision),
        "pool_digest": digest, "pool_size": len(pool or []),
        "selected": selected, "deferred": deferred, "blocked": blocked,
        "remaining_alternatives": remaining_alternatives,
        "alternatives_max": alternatives_max,
    }


def record_expansion_outcome(
    ledger: SearchLedger, attempt_id: str, *,
    outcome: dict, evidence_refs: list[str] | None = None,
    worker_id: str,
) -> dict:
    """持久化一次展开尝试的**非事件结论**(E01 的 unresolved_
    continuation、工具/契约方法失败等;事件类结算走
    submit_action_event + complete_action,不经本入口)。

    - attempt 须存在、归属本 run 且 open,且其 action 处于 claimed、
      认领者为 worker(执行权闭合;陈旧 worker 不可落账);
    - outcome.kind 枚举(未知 ⇒ 契约拒);method 类失败
      (method_failed/contract_aborted)⇒ attempt failed(方法失败不是
      化学判定);其余 ⇒ recorded;
    - 结论 artifact 先写(task_key 绑定 action 冻结任务键;不可覆盖),
      结算经 complete_action(outcome 类;S3A-02 完整权威核验);
    - outcome_ref 返回给调用方(事件/账本关联的持久引用)。
    """
    if not isinstance(outcome, dict) or \
            outcome.get("kind") not in OUTCOME_KINDS:
        raise ScheduleContractError(
            f"outcome.kind 非法:{(outcome or {}).get('kind')!r}"
            f"(允许 {sorted(OUTCOME_KINDS)})",
            {"kind": "invalid_outcome_kind"})
    row = ledger.conn.execute(
        "SELECT * FROM search_attempts WHERE expansion_attempt_id = ?",
        (attempt_id,)).fetchone()
    if row is None:
        raise ScheduleContractError(
            f"attempt 不存在:{attempt_id}",
            {"attempt_id": attempt_id, "kind": "attempt_missing"})
    action_id = row["action_id"]
    action = ledger.conn.execute(
        "SELECT * FROM search_actions WHERE action_id = ?",
        (action_id,)).fetchone()
    if action is None or action["run_id"] != row["run_id"]:
        raise ScheduleContractError(
            f"attempt {attempt_id} 引用的 action 缺失或异属(执行引用"
            "闭合失败)",
            {"attempt_id": attempt_id, "action_id": action_id,
             "kind": "attempt_action_binding_mismatch"})
    if action["status"] != "claimed":
        raise ScheduleContractError(
            f"action {action_id} 状态为 {action['status']}(非事件结论"
            "只在认领执行权下落账)",
            {"attempt_id": attempt_id, "action_id": action_id,
             "kind": "not_claimed", "status": action["status"]})
    if action["claimed_by"] != worker_id:
        raise ScheduleContractError(
            f"action {action_id} 由 {action['claimed_by']!r} 认领,"
            f"{worker_id!r} 不可越权落账尝试结论",
            {"attempt_id": attempt_id, "action_id": action_id,
             "kind": "owner_mismatch"})
    if row["status"] != ATTEMPT_STATUS_OPEN:
        raise ScheduleContractError(
            f"attempt {attempt_id} 状态为 {row['status']}(已落账的尝试"
            "不可再记非事件结论)",
            {"attempt_id": attempt_id, "kind": "attempt_not_open",
             "status": row["status"]})
    payload = {
        "outcome_version": EXPANSION_OUTCOME_VERSION,
        "attempt_id": attempt_id, "action_id": action_id,
        "run_id": row["run_id"], "hypothesis_id": row["hypothesis_id"],
        "outcome": dict(outcome),
        "evidence_refs": [str(r) for r in (evidence_refs or [])],
        "recorded_at": now_iso(),
    }
    task_key = action["task_key"] or stable_id("soutc", action_id)
    if ledger.artifact_store is not None:
        ledger.artifact_store.write(task_key, "expansion_outcome", payload)
    outcome_ref = content_hash(payload)
    attempt_status = (ATTEMPT_STATUS_FAILED
                      if outcome["kind"] in _OUTCOME_FAILED_KINDS
                      else ATTEMPT_STATUS_RECORDED)
    return ledger.complete_action(
        action_id, worker_id=worker_id,
        outcome_kind=COMMIT_KIND_OUTCOME, outcome_ref=outcome_ref,
        attempt_status=attempt_status)


def activate_deferred(
    ledger: SearchLedger,
    *,
    run_id: str,
    parent_path_id: str,
    trigger: str,
    expected_parent_revision: int,
    deferred_type: str | None = None,
) -> dict:
    """激活 deferred(两类分别;幂等;trigger/expected_parent_revision
    校验;预算不足留独立未展开原因;不重复安排同 action)。

    - deferred_type=None ⇒ 父路径全部 deferred;指定
      coproduct_deferred / alternative_reaction_deferred ⇒ 只激活该类
      (两类不混队);
    - 每项经 ledger.reactivate_deferred_action 同一判据:p ok/
      claimed/done ⇒ unchanged already_active(重复触发幂等);旧
      revision ⇒ unchanged stale_parent_revision;预算不足 ⇒
      unchanged budget_exhausted(独立未展开原因,不改状态);trigger
      与冻结激活条件不一致 ⇒ 逐项结构化冲突(冲突不是成功激活);
    - 激活只把 deferred → pending(执行仍走 claim 的权威预算事务);
     不重建任务输入、不覆盖冻结身份。
    """
    if deferred_type is not None and deferred_type not in DEFERRED_TYPES:
        raise ScheduleContractError(
            f"deferred_type 非法:{deferred_type!r}(允许 "
            f"{sorted(DEFERRED_TYPES)};None = 两类全部)",
            {"kind": "invalid_deferred_type", "deferred_type": deferred_type})
    rows = ledger.conn.execute(
        "SELECT * FROM search_actions WHERE run_id = ? AND"
        " parent_path_id = ? ORDER BY created_at, action_id",
        (run_id, parent_path_id)).fetchall()
    items = []
    for row in rows:
        payload = json.loads(row["payload"])
        item = dict(row)
        item["payload"] = payload
        if deferred_type is None:
            if not str(payload.get("deferred_type") or ""):
                continue  # 非 deferred 载荷的 action 不参与激活
        elif str(payload.get("deferred_type") or "") != deferred_type:
            continue
        items.append(item)
    activated_ids: list[str] = []
    unchanged: list[dict] = []
    conflicts: list[dict] = []
    for item in items:
        try:
            out = ledger.reactivate_deferred_action(
                item["action_id"], trigger=trigger,
                expected_parent_revision=expected_parent_revision)
        except SearchContractError as exc:
            conflicts.append({"action_id": item["action_id"],
                              "hypothesis_or_object": item["subject_ref"],
                              "deferred_type": str(
                                  item["payload"].get("deferred_type")
                                  or ""),
                              "error": type(exc).__name__,
                              "kind": exc.detail.get("kind"),
                              "detail": exc.detail})
            continue
        entry = {"action_id": item["action_id"],
                 "hypothesis_or_object": item["subject_ref"],
                 "deferred_type": str(
                     item["payload"].get("deferred_type") or ""),
                 "reason": out.get("reason")}
        if out.get("detail"):
            entry["detail"] = out.get("detail")
        if out.get("activated"):
            activated_ids.append(item["action_id"])
        else:
            unchanged.append(entry)
    return {"run_id": run_id, "parent_path_id": parent_path_id,
            "deferred_type": deferred_type, "trigger": str(trigger),
            "expected_parent_revision": int(expected_parent_revision),
            "activated_ids": activated_ids, "unchanged": unchanged,
            "conflicts": conflicts, "matched": len(items)}


def enqueue_scenario_transition(
    ledger: SearchLedger,
    *,
    run_id: str,
    parent_path_id: str,
    context_ref: str,
    transition: dict,
    policy_version: str,
    parent_search_revision: int,
    task_key: str = "",
    pending_followup: dict | None = None,
) -> dict:
    """场景转换进调度(§5.2:只由用户/来源明确支持;独立 action/预算/
    记录;仅改变后续阶段,不重写旧边评估)。

    - transition 须为 dict 且携带非空 source_ref(显式支持来源;不能
      从文献观察/矩阵"污水"/工具隐式 O2/H2O/标签造当前条件 ——
      source_ref 缺失结构化拒);
    - new_phase_id/new_scenario_ref 缺省沿用当前(转换仍须显式给);
    - action kind=scenario_transition(转换预算在 claim 预约;转换
      次数与反应边深度分账);执行侧(derive_child_context 冻结旧阶段
      快照、只后效)见 runflow/production;
    - **S3b r2(S3B-03)**:pending_followup(转换后 followup 的必要
      事实:event_id/expansion_plan/产物 state_ref 全集/父路径/上下文/
      parent_search_revision/depth)在**创建时一次冻结入载荷** ——
      消除"先入队、另一次 UPDATE 附加"的两写窗口(崩溃恰好落在两写
      之间会丢失转换与后续的关联);B4 恢复按冻结载荷幂等闭合(同键
      同内容 unchanged;不重发事件、不重复扣额)。pending_followup
      须为非空 dict(缺/坏 ⇒ 契约拒,不猜映射);
    - enqueue 幂等/同键异内容冲突(转换动作身份 = run/父/context/
      subject/kind/revision/policy)。
    """
    if not isinstance(transition, dict):
        raise ScheduleContractError(
            "scenario_transition 必须是 dict(须显式支持来源)",
            {"kind": "transition_invalid_type"})
    if not str(transition.get("source_ref") or ""):
        raise ScheduleContractError(
            "阶段转换必须有来源(用户/来源提供;不自行换场景,不从观察"
            "/标签/工具隐式条件造当前条件)",
            {"kind": "transition_source_ref_missing",
             "transition": transition})
    for key in ("new_phase_id", "new_scenario_ref"):
        if not str(transition.get(key) or ""):
            raise ScheduleContractError(
                f"阶段转换缺 {key}(显式指定新阶段/新场景;不猜默认)",
                {"kind": "transition_field_missing", "field": key})
    if pending_followup is not None and (
            not isinstance(pending_followup, dict) or not pending_followup):
        raise ScheduleContractError(
            "转换的 pending_followup 必须是非空 dict(转换后 followup 的"
            "必要事实一次冻结入载荷;不猜映射)",
            {"kind": "transition_followup_invalid"})
    payload = {"task_key": task_key, "transition": dict(transition),
               "context_ref": context_ref}
    if pending_followup is not None:
        payload["pending_followup"] = dict(pending_followup)
    return ledger.enqueue_action(
        run_id=run_id, parent_path_id=parent_path_id,
        context_ref=context_ref,
        subject_ref=stable_id("strans", parent_path_id, context_ref,
                               content_hash(transition)),
        action_kind=ACTION_KIND_SCENARIO_TRANSITION,
        parent_search_revision=parent_search_revision,
        policy_version=policy_version, payload=payload)


def enqueue_coproduct_followups(
    ledger: SearchLedger,
    *,
    run_id: str,
    parent_path_id: str,
    context_ref: str,
    event_id: str,
    product_state_refs: list[str],
    expansion_plan: dict,
    policy_version: str,
    parent_search_revision: int,
    trigger: str = DEFERRED_TRIGGER_EXPLICIT,
    budget_remaining_zero: bool = False,
    substrate_smiles_by_ref: dict[str, str] | None = None,
    depth: int = 0,
) -> dict:
    """事件提交后的共同产物 followup 调度(§5.1:完整事件保存全部已知
    参与物/产物,报告 K/展开宽度或预算不足**不得删事件事实**;本入口
    只调度 followup)。

    - product_state_refs:本事件产物参与物 state_ref 全集(调用方从
      冻结事件/提交结果取;完整事件事实不经本入口删改);
    - 展开计划(expanded/deferred/not_tracked)引用必须是本事件产物
      state_ref(计划引用非产物 ⇒ 契约拒,不猜映射);
    - expanded 产物 ⇒ pending retrieve followup(子路径 = 父路径 +
      事件 + 产物;subject = 产物 state_ref);
    - deferred 产物(宽度/预算不足)⇒ deferred retrieve followup
      (deferred_type=coproduct_deferred,对象 = 产物 state_ref,独立
      未展开原因来自计划 reasons;完整事件不截断);
    - not_tracked 产物 ⇒ 不调度(事件内事实保留);
    - 预算不足(budget_remaining_zero)时全部产物走 deferred(
      reason=budget_limit);
    - retrieve followup 不预约预算(claim 才预约;检索预约按
      max_retrievals_* 在 claim 发生)。
    """
    plan = expansion_plan or {}
    known = [str(r) for r in (product_state_refs or [])]
    known_set = set(known)
    # 展开计划载荷形状 = ExpansionPlan.to_dict():{"entries": [
    # {state_ref, status, reason}], ...};status ∈ expanded/deferred/
    # not_tracked(旧形状 expanded/deferred/not_tracked 键也兼容读取)
    entry_reasons: dict[str, str] = {}
    expanded: list[str] = []
    deferred_plan: list[str] = []
    not_tracked: list[str] = []
    for entry in (plan.get("entries") or []):
        if not isinstance(entry, dict):
            continue
        ref = str(entry.get("state_ref") or "")
        status = str(entry.get("status") or "")
        if status == "expanded":
            expanded.append(ref)
        elif status == "deferred":
            deferred_plan.append(ref)
        elif status == "not_tracked":
            not_tracked.append(ref)
        if entry.get("reason"):
            entry_reasons[ref] = str(entry["reason"])
    expanded += [str(r) for r in (plan.get("expanded") or [])
                 if str(r) not in expanded]
    deferred_plan += [str(r) for r in (plan.get("deferred") or [])
                      if str(r) not in deferred_plan
                      and str(r) not in expanded]
    not_tracked += [str(r) for r in (plan.get("not_tracked") or [])
                    if str(r) not in not_tracked]
    for label, refs in (("expanded", expanded), ("deferred", deferred_plan),
                        ("not_tracked", not_tracked)):
        unknown = sorted(set(refs) - known_set)
        if unknown:
            raise ScheduleContractError(
                f"展开计划 {label} 引用了非本事件产物:{unknown[:5]}"
                "(计划只调度事件产物的 followup,不猜映射)",
                {"kind": "plan_reference_not_product",
                 "label": label, "unknown": unknown[:10]})
    reasons = dict(plan.get("reasons") or {})
    scheduled: list[dict] = []
    deferred_out: list[dict] = []
    for ref in known:
        if ref in not_tracked:
            continue
        child = child_path_id(parent_path_id, event_id, ref)
        payload = {"task_key": "", "product_state_ref": ref,
                   "source_event_id": event_id,
                   "parent_path_id": parent_path_id,
                   "context_ref": context_ref,
                   "substrate_smiles": str(
                       (substrate_smiles_by_ref or {}).get(ref, "")),
                   "depth": int(depth)}
        if ref in expanded and not budget_remaining_zero:
            out = ledger.enqueue_action(
                run_id=run_id, parent_path_id=child,
                context_ref=context_ref, subject_ref=ref,
                action_kind=ACTION_KIND_RETRIEVE,
                parent_search_revision=parent_search_revision,
                policy_version=policy_version, payload=payload)
            scheduled.append({"product_state_ref": ref,
                              "action_id": out.get("action_id"),
                              "status": out.get("status"),
                              "child_path_id": child})
            continue
        reason = (DEFER_REASON_BUDGET if budget_remaining_zero
                  else str(entry_reasons.get(ref)
                           or reasons.get(ref)
                           or DEFER_REASON_PRODUCT_WIDTH))
        payload["deferred_type"] = DEFERRED_TYPE_COPRODUCT
        out = ledger.enqueue_action(
            run_id=run_id, parent_path_id=child, context_ref=context_ref,
            subject_ref=ref, action_kind=ACTION_KIND_RETRIEVE,
            parent_search_revision=parent_search_revision,
            policy_version=policy_version, payload=payload,
            initial_status=ACTION_STATUS_DEFERRED, defer_reason=reason,
            defer_trigger=trigger)
        deferred_out.append({"product_state_ref": ref,
                             "action_id": out.get("action_id"),
                             "status": out.get("status"),
                             "reason": reason,
                             "child_path_id": child})
    return {"run_id": run_id, "parent_path_id": parent_path_id,
            "event_id": event_id, "scheduled": scheduled,
            "deferred": deferred_out,
            "not_tracked": not_tracked,
            "note": ("完整事件事实不截断;deferred/知识缺口存在时不称"
                     "所有路线都探索完")}
