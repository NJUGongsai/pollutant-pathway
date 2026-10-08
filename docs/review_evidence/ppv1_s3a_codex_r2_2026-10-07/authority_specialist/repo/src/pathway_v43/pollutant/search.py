"""S3a 持久搜索底座 —— 身份、预算、认领与恢复(实施书 §9,S3a 批次)。

范围(任务书 §2.3 S3a 行):新搜索/任务/attempt/request 身份与 schema、
配置实际计数(search-limits 草案 v2 → 实际可执行 v3)、认领/预算事务、
artifact 校验、低层提交恢复协议、停止原因、四崩溃/H05–H08/E03/E04
底座夹具。**S3b 未交付**:队列化学集成(冻结池/备选/两类 deferred 的
调度语义)、条件依赖/场景转换语义、新模型假设协议与格式反馈、固定
工具中心证据生产链、PPV1 独立 runner start_run/resume_run 分流 ——
`workflow.runner` 对 PPV1 继续 fail-closed,本模块不解除。

**S3a 回修 r2(2026-10-07,Codex S3a 复审 S3A-01~05)**:本版把搜索
消费协议的五个缺口闭合(见各方法 docstring 的"S3A-0x"标注):

- S3A-01 输出消费身份闭合:B3 bundle 消费、write_commit_bundle 与
  正常 submit 共用 action+attempt+task+event 绑定(`_event_identity_
  mismatch`/`_verify_bundle_identity`/`_verify_event_frozen_to_
  action`),事件 run/parent/context/hypothesis 任一异于 action 冻结
  身份 ⇒ 消费/写账前拒(artifact 保全);
- S3A-02 完成权威闭合:首次 complete、B4 补账、done/已有提交结果
  复用统一走 `_verify_event_outcome` + `_verify_event_ledger_
  authority` —— 复用公共 `store.submit_event` 重放分支的完整事件账
  校验(states/出现/假设/投影/计划/清单/links),get_event/find_event
  读视图不再当完整性证书;同时核本 action 的 attempt/预约引用行
  (`_verify_action_references`);
- S3A-03 defer 未执行事实 + 策略同源校验:defer 前核"确实未执行"
  (已提交事件/已发送或已响应或已失败请求/已落账 attempt ⇒ 拒),
  register/_limits/恢复共用 profile 的 validate_search_limits(单一
  实现,不在本层复制十键校验);
- S3A-04 请求身份与执行引用闭合:同键异 payload/purpose/action/
  retry_of ⇒ SearchIdentityConflict 零写入;登记/复用/发送/响应/
  失败核合法 run/action/attempt、执行权与生命周期(`_verify_
  request_execution`);
- S3A-05 停止报告披露:claimed action 与 open attempt 计入 unexplored
  并阻止 exhausted_search(执行未完成不得称"所有路线都探索完")。

入口矩阵(每处消费的对象/身份/版本/权威及校验来源;回修 r2 更新):

| # | 入口 | 消费 | 校验/事务 |
| 1 | register_search_run | profile 身份块(search_limits) | 十键同源校验(profile.validate_search_limits;四非法块零写入拒);幂等/异块冲突 |
| 2 | enqueue_action | 任务身份输入(run/父/context/subject/kind/revision/policy) | 幂等;同键异内容冲突;深度/宽度结构性拒绝;_limits 读取时同源校验 |
| 3 | claim_action | 冻结 action 行 + 预算账 | BEGIN IMMEDIATE;all-or-nothing 预约;done 复用前经完整提交权威核验(S3A-02) |
| 4 | create/continue attempt | hypothesis 语义尝试 | 恢复同 attempt 不再扣;新备选/重开换 attempt |
| 5 | register_model_request | 请求载荷+执行引用 | 同键异身份内容冲突(S3A-04);action 须 claimed、attempt 归属且 open;真实 provider 预登记即时占额 |
| 6 | record_request_sent/response/failed | 请求状态迁移 | 状态机 + 执行引用闭合(已释放执行权不可继续发送/记响应,S3A-04) |
| 7 | submit_action_event | PathwayEvent(冻结身份) | 沿 action 冻结 run/parent/hypothesis/context;经公共 store.submit_event(不绕过首消费验证);done 复用前经提交权威核验 |
| 8 | write_commit_bundle | 事件+投影+计划+states+假设 | 事件身份冻结到 action + task_key 绑定(S3A-01);不可覆盖 |
| 9 | complete_action | 认领所有权+事件/引用权威 | 事件类 outcome:非空/存在/身份冻结/完整账权威;attempt/预约引用行核验;幂等复用同样核验(S3A-02) |
| 10 | defer_action | 认领所有权+未执行事实 | 先核未执行(事件/请求/attempt 执行证据 ⇒ 拒);合法未执行释放预约、abandon attempt、registered 请求转 abandoned(S3A-03) |
| 11 | recover_run | 持久权威记录 | B4/done 经 complete/_verify_commit_event 完整权威;B3 经 bundle 身份+公共 writer;B1 核引用行;损坏保全失败(H07/H08) |
| 12 | budget_snapshot / stop_report | 持久记录派生值 | 内存重置仍从记录复算;stop 披露 claimed/open attempt(S3A-05) |

预算账表(十上限的预约/consume/release 边界;持久行为事实源):

| limit_key | 计数 scope | 预约点 | consume | release |
| max_total_search_actions | run | claim(每 action 1) | 完成/失败(执行过) | defer(仅未执行,S3A-03) |
| max_alternative_hypotheses_per_parent | parent | claim 首次选中该 hypothesis(主体幂等) | 随 action | defer(仅未执行) |
| max_attempts_per_hypothesis | hypothesis | claim 建 attempt(含首次) | attempt 记录/失败 | abandon(仅未执行 defer) |
| max_reopens_per_hypothesis | hypothesis | claim 重开 attempt | 随 attempt | abandon |
| max_product_expansion_width | source event | enqueue 结构上限(队列级,不算已用) | — | — |
| max_search_depth | path | enqueue 结构上限(0=不展开产品) | — | — |
| max_scenario_transitions | run | claim(transition action 另加 1) | 完成 | defer(仅未执行) |
| max_real_model_requests | run | 登记(即时占额:失败/超时/悬空均占) | — | 永不释放 |
| max_retrievals_per_parent | parent | claim(retrieve 且非缓存复用) | 完成 | defer(仅未执行) |
| max_retrievals_total | run | 同上 | 完成 | defer(仅未执行) |

预约 ID 确定性派生(幂等基准:action 作用域上限以 action_id 为基准,
主体作用域上限以 subject 为基准)⇒ 重放/恢复同 ID 复用,不重复扣额。

零预算只阻止确实消费该资源的动作(任务书 §4.2):真实请求 0 ⇒ 仅
拒绝 real provider 请求登记(网络发送被阻止),纯规则/scripted 搜索
照常;检索 0 ⇒ retrieve action 拒绝,已冻结池(decide)可用;转换 0 ⇒
仅 scenario_transition 拒绝,普通反应不受阻;总 action 0 ⇒ 全部拒绝。

崩溃边界与恢复(§4.4;持久权威记录决定,不猜数据):

- **B1** action 已认领、预约已落账:恢复读冻结 action/attempt/预约
  继续(引用行核验),不按当前 revision 重算任务身份、不再扣额
  (同 attempt/同预约行);
- **B2** 请求已登记、无响应:暴露 pending/unknown,不默发第二请求;
  显式重试 = 新 request_key(新 request_id)+ 剩余额度;provider_kind
  与 network_request_count 分别记录(scripted/fake 恒 0,不冒充真实调用);
- **B3** 输出 artifact 已写、事件未提交:先验版本/hash/身份(H07)与
  事件↔action 完整身份绑定(S3A-01),再消费同一 output/attempt 完成
  —— 不重发请求、不把草稿当事件;artifact 不可反序列化/hash 不符/
  身份错绑 ⇒ 完整性错误、保全原文件、不覆盖;
- **B4** 事件已提交、队列/后续状态未完整:由完整权威记录(事件行 +
  认领/预约/attempt 行 + 提交记录)确定恢复,事件/预算不重复;提交
  事实与 ledger 不一致 ⇒ 保全失败(H08;完整事件账权威核验在补账前)。

提交事务边界(§4.3):事件提交走公共 `PollutantPathwayStore.submit_
event`(既有冻结事务,本模块不复制其校验);搜索记账(预约 consume/
action 状态/提交记录)在 store.conn 的独立事务闭合,两段之间的中断由
B4 恢复协议覆盖 —— 权威在事件行与提交记录,不以内存状态或 LangGraph
checkpoint 声称跨文件原子;artifact 文件先写(不可覆盖),"有文件"
不等于事件已提交。S3A-02 的权威核验在记账写事务**之前**执行(公共
writer 重放路径自带事务;核验只读、失败零写入),写事务内的引用核验
对预约/attempt 行重读;核验与写事务之间的极端并发窗口按顺序消费模型
披露(单进程消费链内无窗口)。

事件幂等(§4.1):事件 ID 继续绑定 run/parent_path/hypothesis/context/
事件语义(公共 event_id_for),不含 retry 号/claim owner/attempt 序号
—— 认领者或 attempt 变化不产生第二个事件;不同 parent/context 的同
反应假设是不同 hypothesis_id(身份含父路径),不是全局互斥对象。
"""

from __future__ import annotations

import json
import sqlite3

from ..domain.models import content_hash, now_iso, stable_id
from ..storage.artifact_store import ArtifactIntegrityError
from .events import PathwayEvent, event_id_for
from .profile import (
    PPV1_SEARCH_SCHEMA_VERSION,
    SEARCH_LIMITS_VERSION,
    validate_search_limits,
)
from .store import PollutantPathwayStore

# ---- 持久对象枚举(schema 固定;语义变更须升版本) ----

ACTION_KIND_RETRIEVE = "retrieve"
ACTION_KIND_DECIDE = "decide"
ACTION_KIND_EXPAND_HYPOTHESIS = "expand_hypothesis"
ACTION_KIND_ACTIVATE_DEFERRED = "activate_deferred"
ACTION_KIND_SCENARIO_TRANSITION = "scenario_transition"
ACTION_KINDS = frozenset({
    ACTION_KIND_RETRIEVE, ACTION_KIND_DECIDE,
    ACTION_KIND_EXPAND_HYPOTHESIS, ACTION_KIND_ACTIVATE_DEFERRED,
    ACTION_KIND_SCENARIO_TRANSITION,
})
# activate_deferred / scenario_transition 的调度语义(触发条件、
# expected_parent_revision、显式支持来源)属 S3b;S3a 只登记种类与
# 底座事务,不实现队列化学集成。

ACTION_STATUS_PENDING = "pending"
ACTION_STATUS_CLAIMED = "claimed"
ACTION_STATUS_DONE = "done"
ACTION_STATUS_DEFERRED = "deferred"
ACTION_STATUS_BLOCKED = "blocked"
ACTION_STATUSES = frozenset({
    ACTION_STATUS_PENDING, ACTION_STATUS_CLAIMED, ACTION_STATUS_DONE,
    ACTION_STATUS_DEFERRED, ACTION_STATUS_BLOCKED,
})

ATTEMPT_STATUS_OPEN = "open"
ATTEMPT_STATUS_RECORDED = "recorded"
ATTEMPT_STATUS_FAILED = "failed"
ATTEMPT_STATUS_ABANDONED = "abandoned"
ATTEMPT_STATUSES = frozenset({
    ATTEMPT_STATUS_OPEN, ATTEMPT_STATUS_RECORDED,
    ATTEMPT_STATUS_FAILED, ATTEMPT_STATUS_ABANDONED,
})

PROVIDER_KIND_REAL = "real"
PROVIDER_KIND_SCRIPTED = "scripted"
PROVIDER_KIND_FAKE = "fake"
PROVIDER_KINDS = frozenset({
    PROVIDER_KIND_REAL, PROVIDER_KIND_SCRIPTED, PROVIDER_KIND_FAKE,
})

REQUEST_STATUS_REGISTERED = "registered"
REQUEST_STATUS_SENT = "sent"
REQUEST_STATUS_RESPONDED = "responded"
REQUEST_STATUS_FAILED = "failed"
REQUEST_STATUS_ABANDONED = "abandoned"
REQUEST_STATUSES = frozenset({
    REQUEST_STATUS_REGISTERED, REQUEST_STATUS_SENT,
    REQUEST_STATUS_RESPONDED, REQUEST_STATUS_FAILED,
    REQUEST_STATUS_ABANDONED,
})

RESERVATION_STATUS_RESERVED = "reserved"
RESERVATION_STATUS_CONSUMED = "consumed"
RESERVATION_STATUS_RELEASED = "released"
RESERVATION_STATUSES = frozenset({
    RESERVATION_STATUS_RESERVED, RESERVATION_STATUS_CONSUMED,
    RESERVATION_STATUS_RELEASED,
})

COMMIT_KIND_EVENT = "event_committed"
COMMIT_KIND_OUTCOME = "outcome_recorded"
COMMIT_KINDS = frozenset({COMMIT_KIND_EVENT, COMMIT_KIND_OUTCOME})

# ---- 停止原因(S3 版本登记;主因优先级冻结于 profile) ----

STOP_REASON_USER_STOP = "user_stop"
STOP_REASON_BUDGET_LIMIT = "budget_limit"
STOP_REASON_DEPTH_LIMIT = "depth_limit"
STOP_REASON_NO_LOCAL_CANDIDATE = "no_local_candidate"
STOP_REASON_AWAITING_PREDICTION = "awaiting_prediction"
STOP_REASON_EXHAUSTED_SEARCH = "exhausted_search"
# 主因优先级(实施书 §9.1/任务书 §4.2:多原因同时成立按此次序取主因,
# 其余原因保留;user_stop 恒最优先)
STOP_REASON_PRIORITY = (
    STOP_REASON_USER_STOP,
    STOP_REASON_BUDGET_LIMIT,
    STOP_REASON_DEPTH_LIMIT,
    STOP_REASON_NO_LOCAL_CANDIDATE,
    STOP_REASON_AWAITING_PREDICTION,
    STOP_REASON_EXHAUSTED_SEARCH,
)
STOP_REASONS = frozenset(STOP_REASON_PRIORITY)

# 提交捆绑 artifact 的载荷版本(事件+投影+计划+states+假设 一起冻结;
# 恢复消费同一 output,B3 边界)
SEARCH_COMMIT_BUNDLE_VERSION = "ppv1-search-commit-bundle-1"


# ---- 结构化异常(机器码分列;fail-closed) ----


class SearchContractError(RuntimeError):
    """搜索底座输入/身份契约违反(结构化,零写入)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


class SearchIdentityConflict(SearchContractError):
    """同键异内容(任务身份/请求键/提交记录冲突;不覆盖)。"""


class SearchClaimError(SearchContractError):
    """认领竞争/所有权冲突(already_claimed、owner_mismatch 等)。"""


class SearchBudgetExhausted(SearchContractError):
    """某上限的剩余额度不足以执行该动作(仅阻止该资源)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message, detail)
        self.detail = dict(self.detail)
        self.detail.setdefault("reason_category", STOP_REASON_BUDGET_LIMIT)


class SearchConcurrencyError(SearchContractError):
    """SQLite busy/锁超时等可见并发结果(不是化学拒绝)。"""


class SearchArtifactIntegrityError(SearchContractError):
    """H07:artifact 不可反序列化或 hash 不符(保全原文件,不覆盖)。"""


class SearchIntegrityError(SearchContractError):
    """H08:提交事实与 ledger 权威记录不一致(保全证据、失败/隔离)。"""


class SearchRecoveryError(SearchContractError):
    """恢复前置失败(未注册 run/策略身份不一致/权威记录不足)。"""


class SearchCrashInjection(SearchContractError):
    """测试注入点:事件提交后、记账前强制“终止”(B4 夹具;非生产路径)。"""


# ---- 任务键构造(§4.1:身份输入进键;parent_search_revision 只进
# 实际依赖局部搜索状态的键,不进无关底物特征缓存) ----


def decision_task_key(
    *,
    run_id: str,
    parent_path_id: str,
    context_ref: str,
    frozen_pool_digest: str,
    parent_search_revision: int,
    policy_version: str,
    strict_state_digest: str = "",
    tool_id: str = "",
    prompt_version: str = "",
    feedback_policy_version: str = "",
) -> str:
    """决策类任务键(检索后选假设/排序):绑定冻结池摘要、父 context、
    所需局部搜索快照(revision)与全部相关版本(严格原始化学状态、
    工具、提示词、反馈策略)。"""
    return stable_id(
        "stask-dec", run_id, parent_path_id, context_ref,
        frozen_pool_digest, str(int(parent_search_revision)),
        policy_version, strict_state_digest, tool_id, prompt_version,
        feedback_policy_version)


def expansion_task_key(
    *,
    run_id: str,
    parent_path_id: str,
    context_ref: str,
    hypothesis_id: str,
    attempt_id: str,
    policy_version: str,
    strict_state_digest: str = "",
    tool_id: str = "",
    prompt_version: str = "",
    feedback_policy_version: str = "",
) -> str:
    """单假设验证/裁决任务键:绑定 hypothesis_id 与 attempt 引用
    (§9.2:同父换假设/换 attempt ⇒ 换键,不复用旧 decision/validation)。"""
    return stable_id(
        "stask-exp", run_id, parent_path_id, context_ref, hypothesis_id,
        attempt_id, policy_version, strict_state_digest, tool_id,
        prompt_version, feedback_policy_version)


def substrate_feature_cache_key(
    *,
    state_digest: str,
    feature_policy_version: str,
) -> str:
    """底物特征缓存键:只绑定状态摘要与特征策略版本 —— **不含**
    parent_search_revision(底物特征不依赖局部搜索状态,塞入全图
    revision 会造成无意义重算;E03 正控)。"""
    return stable_id("sfeat", state_digest, feature_policy_version)


def search_policy_version(*, search_limits_version: str = "") -> str:
    """搜索策略身份串(action/任务键的 policy_version 输入):
    搜索契约版本 + 实际计数版本。语义改变升版本,不改原值。"""
    return (f"{PPV1_SEARCH_SCHEMA_VERSION}/"
            f"{search_limits_version or SEARCH_LIMITS_VERSION}")


# ---- 共享取值/身份辅助(S3A-01/02/04 消费入口同源校验) ----


def _row_get(row, key: str, default=None):
    """sqlite3.Row / dict 安全取值(缺键/None ⇒ default;Row 缺键抛
    IndexError、dict 缺键抛 KeyError,统一吞掉为默认值)。"""
    try:
        value = row[key]
    except (KeyError, IndexError):
        return default
    return default if value is None else value


def _event_from_row(ev_row) -> PathwayEvent:
    """从 events 表行重建 PathwayEvent(只读;权威核验用 —— 载荷不可
    解析由调用方包结构化失败,不在本函数猜修)。"""
    payload = json.loads(ev_row["payload"])
    return PathwayEvent(
        event_id=ev_row["event_id"], run_id=ev_row["run_id"],
        parent_path_id=ev_row["parent_path_id"],
        hypothesis_id=ev_row["hypothesis_id"],
        context_hash=ev_row["context_hash"],
        participants=payload.get("participants") or [],
        participant_state_refs=payload.get("participant_state_refs") or [],
        catalytic_support=payload.get("catalytic_support") or [],
        schema_version=payload.get("schema_version") or "",
    )


def _event_identity_mismatch(action_row, event) -> dict | None:
    """S3A-01:事件身份 vs action 冻结身份的**共用比较**(submit/
    write_bundle/B3/complete/恢复复用同一判据,不追单例补丁)。
    返回冲突 detail(键 ⇒ 冻结值/提交值)或 None。"""
    mismatch: dict = {}
    if event.run_id != _row_get(action_row, "run_id", ""):
        mismatch["run_id"] = {"frozen": _row_get(action_row, "run_id"),
                              "submitted": event.run_id}
    if event.parent_path_id != _row_get(action_row, "parent_path_id", ""):
        mismatch["parent_path_id"] = {
            "frozen": _row_get(action_row, "parent_path_id"),
            "submitted": event.parent_path_id}
    if event.context_hash != _row_get(action_row, "context_ref", ""):
        mismatch["context_hash"] = {
            "frozen": _row_get(action_row, "context_ref"),
            "submitted": event.context_hash}
    if _row_get(action_row, "action_kind") == \
            ACTION_KIND_EXPAND_HYPOTHESIS and \
            event.hypothesis_id != _row_get(action_row, "subject_ref", ""):
        mismatch["hypothesis_id"] = {
            "frozen": _row_get(action_row, "subject_ref"),
            "submitted": event.hypothesis_id}
    return mismatch or None


# ---- 停止原因解析(H05;纯规则级) ----


def resolve_search_stop(reasons, *, unexplored: dict | None = None) -> dict:
    """多原因同时成立按冻结优先级取主因,保留其他原因与未探索集合。

    - 输入 reasons ⊆ STOP_REASONS(未知原因 ⇒ 契约拒绝,不猜测);
    - exhausted_search 只在无 pending/deferred/blocked/悬空请求时由
      调用方给出;存在 deferred/知识缺口时不得称“所有路线都探索完”
      (停止不是化学终点,chemical endpoint 属 S4 另行分账);
    - 输出:{primary, other_reasons, unexplored}。
    """
    reason_set = set(reasons)
    unknown = reason_set - STOP_REASONS
    if unknown:
        raise SearchContractError(
            f"未知停止原因:{sorted(unknown)}(允许 {sorted(STOP_REASONS)})",
            {"kind": "unknown_stop_reason", "unknown": sorted(unknown)})
    unexplored = dict(unexplored or {})
    if not reason_set:
        return {"primary": None, "other_reasons": [], "unexplored": unexplored}
    primary = next(r for r in STOP_REASON_PRIORITY if r in reason_set)
    return {
        "primary": primary,
        "other_reasons": sorted(reason_set - {primary}),
        "unexplored": unexplored,
    }


# ---- 工件读取(H07 wrapper;不修改 ArtifactStore,只包完整性语义) ----


def read_search_artifact(artifact_store, task_key: str, name: str) -> dict:
    """读搜索 artifact 并把损坏上升为结构化完整性错误(H07)。

    - 文件字节损坏(非 JSON)⇒ SearchArtifactIntegrityError(
      kind=artifact_unparseable),**保全原文件**(不删不改不重跑覆盖);
    - 信封 payload_hash 与实际不符 ⇒ kind=artifact_hash_mismatch
      (统一类型并保留原始 stored/actual hash);
    - 正常返回信封 dict(payload 含版本/身份,消费前再验)。
    """
    try:
        return artifact_store.read(task_key, name)
    except ArtifactIntegrityError as exc:
        raise SearchArtifactIntegrityError(
            f"搜索 artifact 完整性失败:{task_key}/{name}(hash 不符;"
            "保全原文件,不静默跳过、不覆盖重跑)",
            {"task_key": task_key, "name": name,
             "kind": "artifact_hash_mismatch",
             "original_error": type(exc).__name__,
             "stored_hash": exc.detail.get("stored_hash"),
             "actual_hash": exc.detail.get("actual_hash")}) from exc
    except (ValueError, TypeError) as exc:  # json 解析失败等
        raise SearchArtifactIntegrityError(
            f"搜索 artifact 不可反序列化:{task_key}/{name}(保全原文件,"
            "不静默跳过、不覆盖重跑)",
            {"task_key": task_key, "name": name,
             "kind": "artifact_unparseable",
             "original_error": type(exc).__name__,
             "reason": str(exc)[:200]}) from exc


# ---- 预算可用性核算(纯派生;事实源是 budget_reservations 行) ----


def _reservation_units(conn, run_id: str, limit_key: str, scope: str,
                        *, statuses=(RESERVATION_STATUS_RESERVED,
                                     RESERVATION_STATUS_CONSUMED)) -> int:
    rows = conn.execute(
        "SELECT units FROM budget_reservations WHERE run_id = ? AND"
        " limit_key = ? AND scope = ? AND status IN (?, ?)",
        (run_id, limit_key, scope, *statuses)).fetchall()
    return int(sum(int(r["units"]) for r in rows))


def _remaining(conn, run_id: str, limit_key: str, scope: str,
               maximum: int) -> int:
    return maximum - _reservation_units(conn, run_id, limit_key, scope)


def _crash_boundary_rows(conn, run_id: str) -> dict:
    """扫描持久权威记录,按四崩溃边界归类(只读;恢复决策的输入)。"""
    actions = [dict(r) for r in conn.execute(
        "SELECT * FROM search_actions WHERE run_id = ? ORDER BY created_at,"
        " action_id", (run_id,)).fetchall()]
    attempts = [dict(r) for r in conn.execute(
        "SELECT * FROM search_attempts WHERE run_id = ? ORDER BY created_at,"
        " expansion_attempt_id", (run_id,)).fetchall()]
    requests = [dict(r) for r in conn.execute(
        "SELECT * FROM model_requests WHERE run_id = ? ORDER BY created_at,"
        " request_id", (run_id,)).fetchall()]
    reservations = [dict(r) for r in conn.execute(
        "SELECT * FROM budget_reservations WHERE run_id = ? ORDER BY"
        " reservation_id", (run_id,)).fetchall()]
    commits = {r["action_id"]: dict(r) for r in conn.execute(
        "SELECT * FROM search_commit_records WHERE run_id = ?",
        (run_id,)).fetchall()}
    pending_requests = [r for r in requests if r["status"] in (
        REQUEST_STATUS_REGISTERED, REQUEST_STATUS_SENT)]
    boundaries: dict[str, list[dict]] = {
        "claimed_pending_completion": [],    # B1(含 B3 attempt 续跑)
        "registered_without_response": [],   # B2
        "artifact_written_event_uncommitted": [],  # B3
        "event_committed_bookkeeping_incomplete": [],  # B4
    }
    for a in actions:
        if a["status"] != ACTION_STATUS_CLAIMED:
            continue
        boundaries["claimed_pending_completion"].append(a)
        if commits.get(a["action_id"]) is None:
            boundaries[
                "event_committed_bookkeeping_incomplete"].append(a)
    return {
        "actions": actions, "attempts": attempts, "requests": requests,
        "reservations": reservations, "commits": commits,
        "pending_requests": pending_requests, "boundaries": boundaries,
    }


class SearchLedger:
    """一个 run 的持久搜索账本(与 PollutantPathwayStore 同 SQLite 文件
    共享事务边界;事件提交经公共 submit_event,不复制其校验)。

    约定:
    - 写方法在 store.conn 上用 BEGIN IMMEDIATE 单事务闭合(并发认领
      只有一方取得执行权;竞争方 already_claimed/复用;SQLite busy ⇒
      可见并发结果 SearchConcurrencyError,不当化学拒绝);
    - 预约 ID 确定性派生 ⇒ 重放/恢复同 ID 复用,不重复扣额;
    - snapshot/stop_report 是**派生值**(每次从持久记录重算,内存
      重置后仍一致),不是事实源;
    - 本类不构造/修改 ChemicalState 或任何化学对象 —— 化学事实经
      公共 store 的首消费验证(不绕过 R7-01/R8 已关闭的入口)。
    """

    def __init__(self, store: PollutantPathwayStore,
                 artifact_store=None, run_id: str = "") -> None:
        self.store = store
        self.conn = store.conn
        self.artifact_store = artifact_store
        self.run_id = run_id

    # ------------------------------------------------------------ 事务

    def _begin(self) -> None:
        try:
            self.conn.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            raise SearchConcurrencyError(
                f"取锁失败(SQLite busy;可见并发结果,不当化学拒绝;"
                f"重试须沿原 action/预约身份,不能绕预算):{exc}",
                {"kind": "sqlite_busy"}) from exc

    # ------------------------------------------------------------ run 注册

    def register_search_run(self, run_id: str, policy_block: dict) -> None:
        """run 的搜索策略注册(配置实际计数,完整往返可重放)。

        - policy_block 至少含 search_limits(经 profile 校验的完整块);
        - **S3A-03:注册入口共用现成十键类型/范围/版本校验**(单一实现
          profile.validate_search_limits,不在本层复制):未知键/bool/
          负数/越界块在写入**之前**拒绝(零写入),不借 int coercion
          接受 bool、不让越界块入账后仅按额度不足拒;
        - 重复注册:幂等(同 run 同块);同 run 异块 ⇒ 身份冲突拒绝
          (不原地切换策略;语义改变升版本开新 run);
        - 未注册 run 的 enqueue/claim/恢复一律 fail-closed。
        """
        limits = (policy_block or {}).get("search_limits")
        if not isinstance(limits, dict) or \
                limits.get("version") != SEARCH_LIMITS_VERSION:
            raise SearchContractError(
                f"run {run_id} 的 search policy 块非法(须含经 profile "
                f"校验的完整 search_limits,版本 {SEARCH_LIMITS_VERSION})",
                {"run_id": run_id, "kind": "invalid_search_policy_block"})
        try:
            validate_search_limits(limits)
        except ValueError as exc:
            raise SearchContractError(
                f"run {run_id} 的 search policy 块非法(十键类型/范围/"
                f"版本同源校验失败;零写入):{exc}",
                {"run_id": run_id, "kind": "invalid_search_policy_block",
                 "reason": str(exc)[:300]}) from exc
        encoded = json.dumps(policy_block, ensure_ascii=False,
                             sort_keys=True)
        self._begin()
        try:
            row = self.conn.execute(
                "SELECT policy_block FROM search_runs WHERE run_id = ?",
                (run_id,)).fetchone()
            if row is not None:
                if row["policy_block"] != encoded:
                    raise SearchIdentityConflict(
                        f"run {run_id} 已注册不同搜索策略(不原地切换;"
                        "语义改变升版本开新 run)",
                        {"run_id": run_id,
                         "kind": "search_policy_conflict"})
                self.conn.rollback()
                return
            self.conn.execute(
                "INSERT INTO search_runs (run_id, policy_block, created_at)"
                " VALUES (?, ?, ?)", (run_id, encoded, now_iso()))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def _limits(self, run_id: str) -> dict:
        """读取 run 的搜索上限(**S3A-03:读取/恢复实际消费配置用与
        注册/装配同一实现的十键类型/范围/版本校验**;存储块被改坏 ⇒
        消费前结构化拒绝,不猜数据)。"""
        row = self.conn.execute(
            "SELECT policy_block FROM search_runs WHERE run_id = ?",
            (run_id,)).fetchone()
        if row is None:
            raise SearchRecoveryError(
                f"run {run_id} 未注册搜索策略(fail-closed,不猜测默认)",
                {"run_id": run_id,
                 "kind": "search_run_unregistered"})
        try:
            block = json.loads(row["policy_block"])
            limits = (block or {}).get("search_limits")
            return validate_search_limits(limits)
        except SearchRecoveryError:
            raise
        except Exception as exc:
            raise SearchRecoveryError(
                f"run {run_id} 的存储搜索策略块非法(同源十键校验失败;"
                f"不猜数据、不静默修块):{exc}",
                {"run_id": run_id,
                 "kind": "search_policy_block_corrupt",
                 "reason": str(exc)[:300]}) from exc

    def search_policy_block(self, run_id: str) -> dict:
        row = self.conn.execute(
            "SELECT policy_block FROM search_runs WHERE run_id = ?",
            (run_id,)).fetchone()
        if row is None:
            raise SearchRecoveryError(
                f"run {run_id} 未注册搜索策略",
                {"run_id": run_id, "kind": "search_run_unregistered"})
        return json.loads(row["policy_block"])

    # ------------------------------------------------------------ 队列创建

    def enqueue_action(
        self,
        *,
        run_id: str,
        parent_path_id: str,
        context_ref: str,
        subject_ref: str,
        action_kind: str,
        parent_search_revision: int = 0,
        policy_version: str,
        payload: dict,
        depth: int | None = None,
        source_event_id: str = "",
    ) -> dict:
        """创建 pending SearchAction(幂等;同键异内容冲突)。

        - action_id 由身份输入派生(run/父/context/subject/kind/
          revision/policy_version);payload 全量任务输入冻结落账,
          重复入队同 ID 同 payload ⇒ unchanged;同 ID 异 payload ⇒
          冲突(不覆盖);
        - 结构性上限在入队处拒绝(队列级,不算已用预算):
          深度(depth > max_search_depth ⇒ 拒绝,0=不展开产品;仅
          expand_hypothesis 受深度约束,阶段转换另计);产品宽度(同
          source_event 的展开数 ≥ max_product_expansion_width ⇒ 拒
          绝;只限继续探索,不截断完整事件事实);
        - 队列待办不计预算(claim 才预约)。
        """
        if action_kind not in ACTION_KINDS:
            raise SearchContractError(
                f"action_kind 非法:{action_kind!r}"
                f"(允许 {sorted(ACTION_KINDS)})",
                {"kind": "invalid_action_kind", "action_kind": action_kind})
        limits = self._limits(run_id)
        if action_kind == ACTION_KIND_EXPAND_HYPOTHESIS and depth is None:
            raise SearchContractError(
                "expand_hypothesis action 必须携带 depth(路径反应边深度)",
                {"kind": "missing_depth"})
        if action_kind == ACTION_KIND_EXPAND_HYPOTHESIS:
            max_depth = int(limits["max_search_depth"])
            if int(depth) > max_depth:
                return {"created": False,
                        "reason": STOP_REASON_DEPTH_LIMIT,
                        "action_id": "",
                        "detail": {"depth": int(depth),
                                   "max_search_depth": max_depth}}
            if source_event_id:
                width = int(limits["max_product_expansion_width"])
                rows = self.conn.execute(
                    "SELECT payload FROM search_actions WHERE run_id = ?"
                    " AND action_kind = ?",
                    (run_id, ACTION_KIND_EXPAND_HYPOTHESIS)).fetchall()
                existing = sum(
                    1 for r in rows
                    if (json.loads(r["payload"]).get("source_event_id")
                        or "") == source_event_id)
                if existing >= width:
                    return {"created": False,
                            "reason": "product_width_limit",
                            "action_id": "",
                            "detail": {"source_event_id": source_event_id,
                                       "existing": existing,
                                       "max_product_expansion_width":
                                           width}}
        task_payload = dict(payload)
        task_payload.setdefault("source_event_id", source_event_id)
        action_id = stable_id(
            "sact", run_id, parent_path_id, context_ref, subject_ref,
            action_kind, str(int(parent_search_revision)), policy_version)
        payload_json = json.dumps(task_payload, ensure_ascii=False,
                                  sort_keys=True)
        payload_digest = content_hash(task_payload)
        self._begin()
        try:
            row = self.conn.execute(
                "SELECT payload, status FROM search_actions WHERE"
                " action_id = ?", (action_id,)).fetchone()
            if row is not None:
                stored = json.loads(row["payload"])
                if content_hash(stored) != payload_digest:
                    raise SearchIdentityConflict(
                        f"action {action_id} 已存在且任务输入不同(同键异"
                        "内容拒绝,不覆盖)",
                        {"action_id": action_id,
                         "kind": "action_payload_conflict"})
                self.conn.rollback()
                return {"created": False, "unchanged": True,
                        "action_id": action_id,
                        "status": row["status"],
                        "reason": "already_enqueued"}
            self.conn.execute(
                "INSERT INTO search_actions (action_id, run_id,"
                " parent_path_id, context_ref, subject_ref, action_kind,"
                " parent_search_revision, policy_version, status, payload,"
                " task_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,"
                " ?, ?, ?)",
                (action_id, run_id, parent_path_id, context_ref,
                 subject_ref, action_kind, int(parent_search_revision),
                 policy_version, ACTION_STATUS_PENDING, payload_json,
                 str(task_payload.get("task_key", "")), now_iso()))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return {"created": True, "action_id": action_id,
                "status": ACTION_STATUS_PENDING}

    def action(self, action_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM search_actions WHERE action_id = ?",
            (action_id,)).fetchone()
        if row is None:
            return None
        out = dict(row)
        out["payload"] = json.loads(row["payload"])
        out["attempt_refs"] = json.loads(row["attempt_refs"] or "[]")
        out["budget_reservation_ref"] = json.loads(
            row["budget_reservation_ref"] or "[]")
        return out

    # ------------------------------------------------------------ 认领+预算

    def _reserve(self, run_id: str, limit_key: str, scope: str,
                 subject: str, maximum: int, *, id_basis: str,
                 action_id: str = "") -> str:
        """确定性预约(幂等):同 id_basis 行存在 ⇒ 复用;额度不足 ⇒
        拒绝。id_basis 是幂等基准 —— action 作用域上限用 action_id,
        主体作用域上限(alternatives/attempts/reopens)用 subject,使
        同一主体跨 action 不重复扣。"""
        reservation_id = stable_id("sres", run_id, limit_key, scope,
                                   id_basis)
        row = self.conn.execute(
            "SELECT status FROM budget_reservations WHERE"
            " reservation_id = ?", (reservation_id,)).fetchone()
        if row is not None:
            if row["status"] == RESERVATION_STATUS_RELEASED:
                raise SearchIntegrityError(
                    f"预约 {reservation_id} 曾被释放后再次出现(记账不变"
                    "量破坏;不猜数据)",
                    {"reservation_id": reservation_id,
                     "kind": "reservation_reuse_after_release"})
            return reservation_id
        remaining = _remaining(self.conn, run_id, limit_key, scope, maximum)
        if remaining < 1:
            raise SearchBudgetExhausted(
                f"预算不足:{limit_key}(scope={scope!r},剩余 0/上限"
                f"{maximum};零预算只阻止确实消费该资源的动作)",
                {"limit_key": limit_key, "scope": scope,
                 "kind": "budget_exhausted", "max": maximum,
                 "remaining": 0})
        self.conn.execute(
            "INSERT INTO budget_reservations (reservation_id, run_id,"
            " limit_key, scope, subject, units, action_id, status,"
            " created_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)",
            (reservation_id, run_id, limit_key, scope, subject, action_id,
             RESERVATION_STATUS_RESERVED, now_iso()))
        return reservation_id

    def claim_action(
        self,
        action_id: str,
        *,
        worker_id: str,
        cache_hit: bool = False,
        reopen_of: str = "",
        hypothesis_binding: str = "",
    ) -> dict:
        """事务认领(BEGIN IMMEDIATE;同 action 只有一方取得执行权)。

        - pending ⇒ 预约所需预算(all-or-nothing)+ 建新 attempt
          (expand 类)⇒ claimed;SQLite busy ⇒ 可见并发结果;
        - 已被他人 claimed ⇒ SearchClaimError(already_claimed;不创建
          新 attempt/request、不重复扣额度);
        - 同 worker 重复认领 ⇒ 幂等返回原收据(执行方恢复续跑入口);
        - done ⇒ 复用已完成结果(竞争方读 outcome,不新建);
        - 所需预算按 action_kind 精确预约(§4.2 零预算只挡该资源);
        - reopen_of 非空 ⇒ 重开:受 max_reopens_per_hypothesis 与总
          attempt 双重约束;恢复沿已冻结 attempt/预约,不再扣。
        """
        self._begin()
        try:
            row = self.conn.execute(
                "SELECT * FROM search_actions WHERE action_id = ?",
                (action_id,)).fetchone()
            if row is None:
                raise SearchContractError(
                    f"action 不存在:{action_id}",
                    {"action_id": action_id, "kind": "action_missing"})
            status = row["status"]
            if status == ACTION_STATUS_DONE:
                # done ⇒ 复用已完成结果(竞争方读 outcome,不新建);
                # S3A-02:复用同样经完整提交权威核验(提交记录/记录哈希/
                # 事件完整账),不能 get 索引即成功
                self.conn.rollback()
                self._verify_done_action_authority(row)
                return {"claimed": False, "status": ACTION_STATUS_DONE,
                        "action_id": action_id,
                        "outcome_ref": row["outcome_ref"],
                        "reason": "already_completed"}
            if status == ACTION_STATUS_CLAIMED:
                if row["claimed_by"] == worker_id:
                    receipt = self._claim_receipt(row)
                    self.conn.rollback()
                    receipt["claimed"] = True
                    receipt["reason"] = "reclaimed_by_owner"
                    return receipt
                self.conn.rollback()
                raise SearchClaimError(
                    f"action {action_id} 已由 {row['claimed_by']!r} 认领"
                    "(already_claimed;不创建新 attempt/request、不重复"
                    "扣额度)",
                    {"action_id": action_id, "kind": "already_claimed",
                     "claimed_by": row["claimed_by"],
                     "requested_by": worker_id})
            if status != ACTION_STATUS_PENDING:
                self.conn.rollback()
                raise SearchClaimError(
                    f"action {action_id} 状态为 {status}(不可认领;"
                    "deferred 须经 activate_deferred[S3b],blocked 保留"
                    "原因不强行执行)",
                    {"action_id": action_id, "kind": "not_pending",
                     "status": status})
            run_id = row["run_id"]
            parent_path_id = row["parent_path_id"]
            kind = row["action_kind"]
            subject = row["subject_ref"]
            limits = self._limits(run_id)
            reservations: list[str] = []
            # --- 预算预约(按 kind 精确;all-or-nothing) ---
            reservations.append(self._reserve(
                run_id, "max_total_search_actions", "", action_id,
                int(limits["max_total_search_actions"]),
                id_basis=action_id, action_id=action_id))
            if kind == ACTION_KIND_RETRIEVE and not cache_hit:
                reservations.append(self._reserve(
                    run_id, "max_retrievals_per_parent", parent_path_id,
                    action_id, int(limits["max_retrievals_per_parent"]),
                    id_basis=action_id, action_id=action_id))
                reservations.append(self._reserve(
                    run_id, "max_retrievals_total", "", action_id,
                    int(limits["max_retrievals_total"]),
                    id_basis=action_id, action_id=action_id))
            if kind == ACTION_KIND_SCENARIO_TRANSITION:
                reservations.append(self._reserve(
                    run_id, "max_scenario_transitions", "", action_id,
                    int(limits["max_scenario_transitions"]),
                    id_basis=action_id, action_id=action_id))
            attempt_id = ""
            if kind == ACTION_KIND_EXPAND_HYPOTHESIS:
                hypothesis_id = hypothesis_binding or subject
                open_attempt = self.conn.execute(
                    "SELECT * FROM search_attempts WHERE action_id = ?"
                    " AND status = ?",
                    (action_id, ATTEMPT_STATUS_OPEN)).fetchone()
                if open_attempt is not None:
                    # B1 恢复:继续旧 attempt,不再扣 attempts/alternatives
                    attempt_id = open_attempt["expansion_attempt_id"]
                else:
                    attempt_id, extra = self._create_attempt(
                        run_id, action_id, hypothesis_id, parent_path_id,
                        row["task_key"], reopen_of=reopen_of, limits=limits)
                    reservations.extend(extra)
            existing_res = json.loads(
                row["budget_reservation_ref"] or "[]")
            merged = sorted(set(existing_res) | set(reservations))
            attempt_refs = json.loads(row["attempt_refs"] or "[]")
            if attempt_id and attempt_id not in attempt_refs:
                attempt_refs.append(attempt_id)
            self.conn.execute(
                "UPDATE search_actions SET status = ?, claimed_by = ?,"
                " claimed_at = ?, budget_reservation_ref = ?,"
                " attempt_refs = ? WHERE action_id = ?",
                (ACTION_STATUS_CLAIMED, worker_id, now_iso(),
                 json.dumps(merged), json.dumps(attempt_refs), action_id))
            self.conn.commit()
        except sqlite3.OperationalError as exc:
            self.conn.rollback()
            raise SearchConcurrencyError(
                f"认领事务失败(SQLite busy;可见并发结果,不当化学拒绝"
                f";重试沿原 action 身份):{exc}",
                {"action_id": action_id, "kind": "sqlite_busy"}) from exc
        except Exception:
            self.conn.rollback()
            raise
        fresh = self.conn.execute(
            "SELECT * FROM search_actions WHERE action_id = ?",
            (action_id,)).fetchone()
        receipt = self._claim_receipt(fresh)
        receipt["claimed"] = True
        return receipt

    def _create_attempt(self, run_id: str, action_id: str,
                        hypothesis_id: str, parent_path_id: str,
                        task_key: str, *, reopen_of: str,
                        limits: dict) -> tuple[str, list[str]]:
        """新建语义尝试(同事务内预约 attempts/alternatives/reopen)。

        - attempt 序号按 (run, hypothesis) 持久计数(含首次);
        - 新备选假设 ⇒ alternatives 预约(scope=parent,主体幂等:同父
          同假设只扣一次);
        - reopen ⇒ reopen 预约 + 总 attempt 双重约束(§4.2)。
        返回 (expansion_attempt_id, 预约 ID 列表)。
        """
        prior = int(self.conn.execute(
            "SELECT COUNT(*) FROM search_attempts WHERE run_id = ? AND"
            " hypothesis_id = ?", (run_id, hypothesis_id)).fetchone()[0])
        attempt_index = prior + 1
        attempt_id = stable_id(
            "sattempt", run_id, hypothesis_id, str(attempt_index))
        existing = self.conn.execute(
            "SELECT status FROM search_attempts WHERE"
            " expansion_attempt_id = ?", (attempt_id,)).fetchone()
        if existing is not None:
            # 确定性 ID 幂等(防御;计数含该行时不应到达)
            return attempt_id, []
        reservations: list[str] = []
        reservations.append(self._reserve(
            run_id, "max_alternative_hypotheses_per_parent",
            parent_path_id, hypothesis_id,
            int(limits["max_alternative_hypotheses_per_parent"]),
            id_basis=f"alt:{hypothesis_id}", action_id=action_id))
        reservations.append(self._reserve(
            run_id, "max_attempts_per_hypothesis", hypothesis_id,
            attempt_id, int(limits["max_attempts_per_hypothesis"]),
            id_basis=f"att:{attempt_id}", action_id=action_id))
        if reopen_of:
            reservations.append(self._reserve(
                run_id, "max_reopens_per_hypothesis", hypothesis_id,
                attempt_id, int(limits["max_reopens_per_hypothesis"]),
                id_basis=f"re:{attempt_id}", action_id=action_id))
        self.conn.execute(
            "INSERT INTO search_attempts (expansion_attempt_id, run_id,"
            " action_id, hypothesis_id, attempt_index, reopen_of, status,"
            " task_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (attempt_id, run_id, action_id, hypothesis_id, attempt_index,
             reopen_of, ATTEMPT_STATUS_OPEN, task_key, now_iso()))
        return attempt_id, reservations

    def _claim_receipt(self, row) -> dict:
        return {
            "action_id": row["action_id"], "run_id": row["run_id"],
            "parent_path_id": row["parent_path_id"],
            "context_ref": row["context_ref"],
            "subject_ref": row["subject_ref"],
            "action_kind": row["action_kind"],
            "parent_search_revision": row["parent_search_revision"],
            "policy_version": row["policy_version"],
            "status": row["status"], "task_key": row["task_key"],
            "claimed_by": row["claimed_by"],
            "attempt_refs": json.loads(row["attempt_refs"] or "[]"),
            "budget_reservation_ref": json.loads(
                row["budget_reservation_ref"] or "[]"),
            "payload": json.loads(row["payload"]),
        }

    def open_attempt(self, action_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM search_attempts WHERE action_id = ? AND"
            " status = ?", (action_id, ATTEMPT_STATUS_OPEN)).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------ 模型请求

    def register_model_request(
        self,
        *,
        run_id: str,
        action_id: str,
        attempt_id: str,
        provider_kind: str,
        request_key: str,
        purpose: str = "",
        payload: dict | None = None,
        retry_of: str = "",
    ) -> dict:
        """请求预登记(真实 provider 发出前必须预登记;§4.4 B2)。

        - **S3A-04 执行引用闭合(登记/复用前核)**:action 须存在、
          属于本 run 且处于 claimed(未认领/不存在/已释放的 action 不可
          登记 —— 公共口不得成为绕过认领的捷径);attempt 非空时须
          存在、归属本 run 与本 action 且 open(recorded/failed/
          abandoned 的 attempt 是已失效执行引用);空 attempt 仅对
          非 expand 类合法(decide/retrieve 的 action 驱动路径),
          expand 类请求必须绑定语义 attempt;
        - **S3A-04 同键幂等须同身份内容**:已有同 request_id 行时比对
          action/purpose/payload_hash/retry_of(其余身份列已进 ID 派生),
          任一不同 ⇒ SearchIdentityConflict 结构化冲突、零写入(同键换
          payload/换 purpose/换 action/存储 hash 被改坏后重注册均拒),
          不以"键相同"当幂等证书;
        - provider_kind=real ⇒ 即时占 max_real_model_requests 额度
          (失败/超时/悬空均占额,永不释放);额度 0 ⇒ 拒绝登记
          ⇒ 网络发送被阻止(PPV1 不接受"传了模型对象就派生正额度");
        - scripted/fake ⇒ 不占真实请求额度,network_request_count 恒
          0(日志区分 script 调用/请求登记/真实请求,不冒充真实调用);
        - request_key 调用方去重键:同键同内容 ⇒ 幂等返回;显式重试换
          新键(新 request_id + 剩余额度,不默发第二请求);
        - retry_of 记录显式重试来源请求。
        """
        if provider_kind not in PROVIDER_KINDS:
            raise SearchContractError(
                f"provider_kind 非法:{provider_kind!r}(允许 "
                f"{sorted(PROVIDER_KINDS)})",
                {"kind": "invalid_provider_kind",
                 "provider_kind": provider_kind})
        payload_hash = content_hash(payload or {})
        request_id = stable_id(
            "sreq", run_id, attempt_id, provider_kind, request_key)
        limits = self._limits(run_id)
        self._begin()
        try:
            # ---- S3A-04:执行引用闭合(新登记与同键复用共用) ----
            action_row = self.conn.execute(
                "SELECT * FROM search_actions WHERE action_id = ?",
                (action_id,)).fetchone()
            if action_row is None:
                raise SearchContractError(
                    f"请求登记引用的 action 不存在:{action_id}",
                    {"run_id": run_id, "action_id": action_id,
                     "request_id": request_id,
                     "kind": "request_action_missing"})
            if action_row["run_id"] != run_id:
                raise SearchContractError(
                    f"请求登记引用的 action {action_id} 属于 run "
                    f"{action_row['run_id']!r}(与登记 run {run_id!r} "
                    "不一致;异 run 引用拒绝)",
                    {"run_id": run_id, "action_id": action_id,
                     "request_id": request_id,
                     "kind": "request_action_run_mismatch"})
            if action_row["status"] != ACTION_STATUS_CLAIMED:
                raise SearchContractError(
                    f"请求登记引用的 action {action_id} 状态为 "
                    f"{action_row['status']}(须处于认领执行权下;未认领/"
                    "已释放的执行引用不可登记新请求)",
                    {"run_id": run_id, "action_id": action_id,
                     "request_id": request_id,
                     "kind": "request_action_not_claimed",
                     "status": action_row["status"]})
            if attempt_id:
                attempt_row = self.conn.execute(
                    "SELECT * FROM search_attempts WHERE"
                    " expansion_attempt_id = ?", (attempt_id,)).fetchone()
                if attempt_row is None:
                    raise SearchContractError(
                        f"请求登记引用的 attempt 不存在:{attempt_id}",
                        {"run_id": run_id, "action_id": action_id,
                         "attempt_id": attempt_id,
                         "request_id": request_id,
                         "kind": "request_attempt_missing"})
                if attempt_row["run_id"] != run_id or \
                        attempt_row["action_id"] != action_id:
                    raise SearchContractError(
                        f"请求登记引用的 attempt {attempt_id} 不属于本 "
                        f"action/本 run(异属执行引用拒绝)",
                        {"run_id": run_id, "action_id": action_id,
                         "attempt_id": attempt_id,
                         "request_id": request_id,
                         "kind": "request_attempt_binding_mismatch",
                         "attempt_run": attempt_row["run_id"],
                         "attempt_action": attempt_row["action_id"]})
                if attempt_row["status"] != ATTEMPT_STATUS_OPEN:
                    raise SearchContractError(
                        f"请求登记引用的 attempt {attempt_id} 状态为 "
                        f"{attempt_row['status']}(已失效执行引用不可登记"
                        "请求)",
                        {"run_id": run_id, "action_id": action_id,
                         "attempt_id": attempt_id,
                         "request_id": request_id,
                         "kind": "request_attempt_not_open",
                         "attempt_status": attempt_row["status"]})
            elif action_row["action_kind"] == ACTION_KIND_EXPAND_HYPOTHESIS:
                raise SearchContractError(
                    f"expand_hypothesis action {action_id} 的请求必须绑定"
                    "语义 attempt(空 attempt 仅非 expand 类合法)",
                    {"run_id": run_id, "action_id": action_id,
                     "request_id": request_id,
                     "kind": "request_attempt_required_for_expand"})
            row = self.conn.execute(
                "SELECT * FROM model_requests WHERE request_id = ?",
                (request_id,)).fetchone()
            if row is not None:
                # ---- S3A-04:同键幂等须同身份内容(异内容零写入拒) ----
                conflicts: dict = {}
                if row["action_id"] != action_id:
                    conflicts["action_id"] = {
                        "stored": row["action_id"], "submitted": action_id}
                if row["purpose"] != purpose:
                    conflicts["purpose"] = {
                        "stored": row["purpose"], "submitted": purpose}
                if row["payload_hash"] != payload_hash:
                    conflicts["payload_hash"] = {
                        "stored": row["payload_hash"],
                        "submitted": payload_hash}
                if row["retry_of"] != retry_of:
                    conflicts["retry_of"] = {
                        "stored": row["retry_of"], "submitted": retry_of}
                if conflicts:
                    raise SearchIdentityConflict(
                        f"请求 {request_id} 同键异身份内容(不覆盖、不"
                        "以键相同当幂等证书;零写入)",
                        {"request_id": request_id, "run_id": run_id,
                         "kind": "request_identity_conflict",
                         "conflicts": conflicts})
                self.conn.rollback()
                return {"registered": False, "unchanged": True,
                        "request_id": request_id,
                        "status": row["status"],
                        "reason": "same_request_key"}
            if provider_kind == PROVIDER_KIND_REAL:
                # 即时占额(consume;悬空/失败不释放)
                reservation_id = stable_id(
                    "sres", run_id, "max_real_model_requests", "",
                    f"req:{request_id}")
                remaining = _remaining(
                    self.conn, run_id, "max_real_model_requests", "",
                    int(limits["max_real_model_requests"]))
                if remaining < 1:
                    raise SearchBudgetExhausted(
                        "真实模型请求额度不足(max_real_model_requests;"
                        "默认 0/off —— 登记被拒,网络发送被阻止;传入"
                        "模型对象不自动补预算)",
                        {"limit_key": "max_real_model_requests",
                         "kind": "budget_exhausted",
                         "max": int(limits["max_real_model_requests"]),
                         "remaining": 0})
                self.conn.execute(
                    "INSERT INTO budget_reservations (reservation_id,"
                    " run_id, limit_key, scope, subject, units, action_id,"
                    " status, created_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?,"
                    " ?)",
                    (reservation_id, run_id, "max_real_model_requests", "",
                     request_id, action_id,
                     RESERVATION_STATUS_CONSUMED, now_iso()))
            self.conn.execute(
                "INSERT INTO model_requests (request_id, run_id, action_id,"
                " attempt_id, provider_kind, purpose, status,"
                " network_request_count, payload_hash, retry_of, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)",
                (request_id, run_id, action_id, attempt_id, provider_kind,
                 purpose, REQUEST_STATUS_REGISTERED, payload_hash, retry_of,
                 now_iso()))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return {"registered": True, "request_id": request_id,
                "status": REQUEST_STATUS_REGISTERED,
                "provider_kind": provider_kind,
                "network_request_count": 0}

    def _verify_request_execution(self, request_row, *,
                                  where: str) -> None:
        """S3A-04:请求**状态消费**前的执行引用闭合 —— 请求行引用的
        action 存在且处于 claimed、attempt(若绑定)存在/归属本 action
        且 open。已释放执行权(action deferred/done/attempt abandoned
        等)不可继续发送/记录响应/记失败;不能消费不存在或异属引用。"""
        action_id = request_row["action_id"]
        action_row = self.conn.execute(
            "SELECT * FROM search_actions WHERE action_id = ?",
            (action_id,)).fetchone()
        if action_row is None:
            raise SearchContractError(
                f"{where}:请求 {request_row['request_id']} 引用的 action"
                f" 不存在:{action_id}",
                {"request_id": request_row["request_id"],
                 "action_id": action_id, "where": where,
                 "kind": "request_action_missing"})
        if action_row["status"] != ACTION_STATUS_CLAIMED:
            raise SearchContractError(
                f"{where}:请求 {request_row['request_id']} 的执行权已"
                f"释放(action {action_id} 状态为 "
                f"{action_row['status']};已释放执行引用不可继续消费)",
                {"request_id": request_row["request_id"],
                 "action_id": action_id, "where": where,
                 "kind": "request_execution_released",
                 "action_status": action_row["status"]})
        if request_row["attempt_id"]:
            attempt_row = self.conn.execute(
                "SELECT * FROM search_attempts WHERE"
                " expansion_attempt_id = ?",
                (request_row["attempt_id"],)).fetchone()
            if attempt_row is None:
                raise SearchContractError(
                    f"{where}:请求 {request_row['request_id']} 引用的"
                    f" attempt 不存在:{request_row['attempt_id']}",
                    {"request_id": request_row["request_id"],
                     "attempt_id": request_row["attempt_id"],
                     "where": where,
                     "kind": "request_attempt_missing"})
            if attempt_row["action_id"] != action_id:
                raise SearchContractError(
                    f"{where}:请求 {request_row['request_id']} 引用的"
                    f" attempt {request_row['attempt_id']} 不属于本 "
                    "action(异属执行引用)",
                    {"request_id": request_row["request_id"],
                     "action_id": action_id,
                     "attempt_id": request_row["attempt_id"],
                     "where": where,
                     "kind": "request_attempt_binding_mismatch"})
            if attempt_row["status"] != ATTEMPT_STATUS_OPEN:
                raise SearchContractError(
                    f"{where}:请求 {request_row['request_id']} 的执行"
                    f"引用已失效(attempt {request_row['attempt_id']} "
                    f"状态为 {attempt_row['status']})",
                    {"request_id": request_row["request_id"],
                     "action_id": action_id,
                     "attempt_id": request_row["attempt_id"],
                     "where": where,
                     "kind": "request_execution_released",
                     "attempt_status": attempt_row["status"]})

    def request(self, request_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM model_requests WHERE request_id = ?",
            (request_id,)).fetchone()
        return dict(row) if row else None

    def record_request_sent(self, request_id: str) -> None:
        """登记 → sent(真实 provider 计 network_request_count=1;
        scripted/fake 恒 0)。已 sent ⇒ 拒绝(不默发第二请求)。
        **S3A-04**:发送前核执行引用(action 仍 claimed、attempt 仍
        open)——已释放执行权(defer/完成/abandon 后)不可继续发送。"""
        self._begin()
        try:
            row = self.conn.execute(
                "SELECT * FROM model_requests WHERE request_id = ?",
                (request_id,)).fetchone()
            if row is None:
                raise SearchContractError(
                    f"请求不存在:{request_id}",
                    {"request_id": request_id, "kind": "request_missing"})
            if row["status"] != REQUEST_STATUS_REGISTERED:
                raise SearchContractError(
                    f"请求 {request_id} 状态为 {row['status']}(不可重复"
                    "发送;显式重试须登记新 request 并占剩余额度)",
                    {"request_id": request_id,
                     "kind": "request_not_resendable",
                     "status": row["status"]})
            self._verify_request_execution(row, where="record_request_sent")
            network = 1 if row["provider_kind"] == PROVIDER_KIND_REAL else 0
            self.conn.execute(
                "UPDATE model_requests SET status = ?,"
                " network_request_count = ?, updated_at = ? WHERE"
                " request_id = ?",
                (REQUEST_STATUS_SENT, network, now_iso(), request_id))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def record_request_response(self, request_id: str,
                                response_ref: str) -> None:
        """sent → responded(记录响应引用;响应缺失由恢复暴露 unknown)。
        **S3A-04**:响应消费前核执行引用(已释放执行权不可记响应)。"""
        self._begin()
        try:
            row = self.conn.execute(
                "SELECT * FROM model_requests WHERE request_id = ?",
                (request_id,)).fetchone()
            if row is None or row["status"] != REQUEST_STATUS_SENT:
                raise SearchContractError(
                    f"请求 {request_id} 不处于 sent(不可记录响应)",
                    {"request_id": request_id,
                     "kind": "request_not_awaiting",
                     "status": row["status"] if row else None})
            self._verify_request_execution(
                row, where="record_request_response")
            self.conn.execute(
                "UPDATE model_requests SET status = ?, response_ref = ?,"
                " updated_at = ? WHERE request_id = ?",
                (REQUEST_STATUS_RESPONDED, response_ref, now_iso(),
                 request_id))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def mark_request_failed(self, request_id: str) -> None:
        """registered/sent → failed(方法失败如实记录;占额不释放)。
        **S3A-04**:失败记账前核执行引用(消费口与发送/响应同一闭合)。"""
        self._begin()
        try:
            row = self.conn.execute(
                "SELECT * FROM model_requests WHERE request_id = ?",
                (request_id,)).fetchone()
            if row is None:
                raise SearchContractError(
                    f"请求不存在:{request_id}",
                    {"request_id": request_id, "kind": "request_missing"})
            if row["status"] in (REQUEST_STATUS_RESPONDED,
                                 REQUEST_STATUS_FAILED,
                                 REQUEST_STATUS_ABANDONED):
                raise SearchContractError(
                    f"请求 {request_id} 状态为 {row['status']}(不可改记"
                    "失败)",
                    {"request_id": request_id,
                     "kind": "request_not_failable",
                     "status": row["status"]})
            self._verify_request_execution(
                row, where="mark_request_failed")
            self.conn.execute(
                "UPDATE model_requests SET status = ?, updated_at = ? WHERE"
                " request_id = ?",
                (REQUEST_STATUS_FAILED, now_iso(), request_id))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # ------------------------------------------------------------ 提交/完成

    def submit_action_event(
        self, action_id: str, event: PathwayEvent, *,
        report_projection: dict, expansion_plan: dict, states: list[dict],
        hypothesis_dict: dict | None, worker_id: str,
    ) -> dict:
        """经公共 store.submit_event 提交事件(沿 action 冻结身份)。

        - 事件提交走既有冻结事务(全部首消费验证照常,本模块不复制
          校验、不绕过 chemstate/store 契约);
        - 提交前核认领所有权与冻结身份一致性(陈旧 worker 拒绝;
          done ⇒ 幂等复用,不覆盖;**S3A-02**:done 复用同样经完整
          提交权威核验,不能 get 索引即成功);
        - 提交后记账未闭合 ⇒ B4,由 complete_action / recover_run 补;
        - 同事件重放幂等(store 既有行为):retry/owner/attempt 变化
          不新增事件。
        """
        row = self.conn.execute(
            "SELECT * FROM search_actions WHERE action_id = ?",
            (action_id,)).fetchone()
        if row is None:
            raise SearchContractError(
                f"action 不存在:{action_id}",
                {"action_id": action_id, "kind": "action_missing"})
        if row["status"] == ACTION_STATUS_DONE:
            self._verify_done_action_authority(row)
            return {"created": False, "event_id": event.event_id,
                    "reason": "already_completed"}
        if row["status"] != ACTION_STATUS_CLAIMED:
            raise SearchClaimError(
                f"action {action_id} 状态为 {row['status']}(未处于认领"
                "执行权下,不可提交事件)",
                {"action_id": action_id, "kind": "not_claimed",
                 "status": row["status"]})
        if row["claimed_by"] != worker_id:
            raise SearchClaimError(
                f"action {action_id} 由 {row['claimed_by']!r} 认领,"
                f"{worker_id!r} 是陈旧 worker(不得越权提交)",
                {"action_id": action_id, "kind": "owner_mismatch",
                 "claimed_by": row["claimed_by"],
                 "worker_id": worker_id})
        self._verify_event_frozen_to_action(row, event)
        out = self.store.submit_event(
            event, report_projection=report_projection,
            expansion_plan=expansion_plan, states=states,
            hypothesis_dict=hypothesis_dict)
        out["action_id"] = action_id
        return out

    def _verify_event_frozen_to_action(self, action_row, event) -> None:
        """事件身份必须与 action 冻结身份一致(retry/owner/attempt 序号
        变化不产生第二个事件;事件幂等键不含 attempt/owner)。
        **S3A-01**:比较判据经 `_event_identity_mismatch` 与 write_
        bundle/B3/complete 复用(同一绑定,不追单例补丁)。"""
        mismatch = _event_identity_mismatch(action_row, event)
        if mismatch:
            raise SearchContractError(
                f"事件身份与 action {action_row['action_id']} 冻结身份"
                "不一致(run/parent/context/hypothesis 任一变化须开新 "
                "action,不得沿用旧认领)",
                {"action_id": action_row["action_id"],
                 "kind": "event_identity_not_frozen_to_action",
                 "mismatch": mismatch})

    def write_commit_bundle(
        self, *, action_id: str, attempt_id: str, event: PathwayEvent,
        report_projection: dict, expansion_plan: dict, states: list[dict],
        hypothesis_dict: dict | None, task_key: str,
    ) -> dict:
        """写提交捆绑 artifact(事件提交前的输出落盘;B3 输入)。

        - **S3A-01:写侧即核事件身份冻结到 action**(与正常 submit/B3
          消费同一 `_event_identity_mismatch` 判据)与 task_key 绑定
          (action 行 task_key 非空时须一致)—— 异身份事件不写盘,
          不把"消费口会拒"当作写侧免检;action 须处于认领执行权下;
        - artifact 先写(不可覆盖:同键异内容 ArtifactConflict);
        - “有文件”不等于事件已提交 —— 提交事实以事件行 + 提交记录
          为准,恢复按 B3 消费同一 output;
        - 载荷含版本与冻结身份(恢复先验版本/hash/身份再消费)。
        """
        if self.artifact_store is None:
            raise SearchContractError(
                "SearchLedger 未配置 artifact_store(无法写提交捆绑)",
                {"kind": "artifact_store_missing"})
        row = self.conn.execute(
            "SELECT * FROM search_actions WHERE action_id = ?",
            (action_id,)).fetchone()
        if row is None:
            raise SearchContractError(
                f"action 不存在:{action_id}",
                {"action_id": action_id, "kind": "action_missing"})
        if row["status"] != ACTION_STATUS_CLAIMED:
            raise SearchClaimError(
                f"action {action_id} 状态为 {row['status']}(提交捆绑只在"
                "认领执行权下写)",
                {"action_id": action_id, "kind": "not_claimed",
                 "status": row["status"]})
        self._verify_event_frozen_to_action(row, event)
        stored_task_key = row["task_key"] or ""
        if task_key and stored_task_key and task_key != stored_task_key:
            raise SearchContractError(
                f"commit bundle 的 task_key {task_key!r} 与 action "
                f"{action_id} 冻结 task_key {stored_task_key!r} 不一致"
                "(同源任务绑定拒绝)",
                {"action_id": action_id,
                 "kind": "bundle_task_key_binding_mismatch",
                 "bundle_task_key": task_key,
                 "action_task_key": stored_task_key})
        payload = {
            "bundle_version": SEARCH_COMMIT_BUNDLE_VERSION,
            "action_id": action_id, "attempt_id": attempt_id,
            "event": {
                "schema_version": event.schema_version,
                "event_id": event.event_id, "run_id": event.run_id,
                "parent_path_id": event.parent_path_id,
                "hypothesis_id": event.hypothesis_id,
                "context_hash": event.context_hash,
                "participants": list(event.participants),
                "participant_state_refs": list(
                    event.participant_state_refs),
                "catalytic_support": list(event.catalytic_support),
            },
            "report_projection": report_projection,
            "expansion_plan": expansion_plan,
            "states": states,
            "hypothesis_dict": hypothesis_dict,
            "task_key": task_key,
        }
        return self.artifact_store.write(
            task_key, "search_commit_bundle", payload)

    def _verify_action_references(self, action_row) -> None:
        """S3A-02/03:action 冻结引用的行级核验(写账/挂起/恢复前)。

        - claim 必留 ≥1 预约引用、expand 必留 ≥1 attempt 引用
          (空引用集合 = 记账不变量破坏,缺权威失败);
        - 每个预约/attempt 行必须存在且归属本 run/本 action(引用行被
          删/被挪 ⇒ UPDATE 0 行不是成功,是缺权威失败,不猜补坏行);
        - claimed 状态下出现已释放预约 ⇒ 不变量破坏。
        """
        action_id = action_row["action_id"]
        run_id = action_row["run_id"]
        reservation_refs = json.loads(
            _row_get(action_row, "budget_reservation_ref", "[]") or "[]")
        attempt_refs = json.loads(
            _row_get(action_row, "attempt_refs", "[]") or "[]")
        if not reservation_refs:
            raise SearchIntegrityError(
                f"action {action_id} 处于认领状态但无预算预约引用(记账"
                "不变量破坏;缺权威,不补账)",
                {"action_id": action_id, "run_id": run_id,
                 "kind": "claimed_action_reservation_missing"})
        if action_row["action_kind"] == ACTION_KIND_EXPAND_HYPOTHESIS \
                and not attempt_refs:
            raise SearchIntegrityError(
                f"expand action {action_id} 认领后无 attempt 引用(记账"
                "不变量破坏;缺权威,不补账)",
                {"action_id": action_id, "run_id": run_id,
                 "kind": "claimed_action_attempt_missing"})
        for rid in reservation_refs:
            rrow = self.conn.execute(
                "SELECT run_id, limit_key, scope, subject, action_id,"
                " status FROM budget_reservations"
                " WHERE reservation_id = ?", (rid,)).fetchone()
            if rrow is None:
                raise SearchIntegrityError(
                    f"action {action_id} 的预算预约行缺失:{rid}(引用"
                    "完整性失败;保全,不补账/不重建新 ID 洗损坏)",
                    {"action_id": action_id, "run_id": run_id,
                     "reservation_id": rid,
                     "kind": "reservation_row_missing"})
            if rrow["run_id"] != run_id:
                raise SearchIntegrityError(
                    f"action {action_id} 的预算预约 {rid} 归属不一致"
                    "(run 绑定破坏;保全失败)",
                    {"action_id": action_id, "run_id": run_id,
                     "reservation_id": rid,
                     "reservation_run": rrow["run_id"],
                     "reservation_action": rrow["action_id"],
                     "kind": "reservation_binding_mismatch"})
            if rrow["action_id"] != action_id:
                # 主体作用域预约(同父同假设的 alternatives)按设计跨
                # action 共享(id_basis=主体,非 action);此时核
                # scope=本 action 父路径与 subject=本 action 主体,
                # 其余 limit 的预约行必须由本 action 创建
                shared_ok = (
                    rrow["limit_key"] ==
                    "max_alternative_hypotheses_per_parent"
                    and rrow["scope"] == action_row["parent_path_id"]
                    and rrow["subject"] == action_row["subject_ref"])
                if not shared_ok:
                    raise SearchIntegrityError(
                        f"action {action_id} 的预算预约 {rid} 归属不一致"
                        "(action 绑定破坏;保全失败)",
                        {"action_id": action_id, "run_id": run_id,
                         "reservation_id": rid,
                         "reservation_run": rrow["run_id"],
                         "reservation_action": rrow["action_id"],
                         "kind": "reservation_binding_mismatch"})
            if rrow["status"] == RESERVATION_STATUS_RELEASED:
                raise SearchIntegrityError(
                    f"action {action_id} 的预算预约 {rid} 已被释放却仍处"
                    "认领链(记账不变量破坏)",
                    {"action_id": action_id, "run_id": run_id,
                     "reservation_id": rid,
                     "kind": "reservation_released_under_claim"})
        for aid in attempt_refs:
            arow = self.conn.execute(
                "SELECT run_id, action_id FROM search_attempts WHERE"
                " expansion_attempt_id = ?", (aid,)).fetchone()
            if arow is None:
                raise SearchIntegrityError(
                    f"action {action_id} 的 attempt 行缺失:{aid}(引用"
                    "完整性失败;保全,不补账)",
                    {"action_id": action_id, "run_id": run_id,
                     "attempt_id": aid,
                     "kind": "attempt_row_missing"})
            if arow["run_id"] != run_id or arow["action_id"] != action_id:
                raise SearchIntegrityError(
                    f"action {action_id} 的 attempt {aid} 归属不一致"
                    "(保全失败)",
                    {"action_id": action_id, "run_id": run_id,
                     "attempt_id": aid,
                     "attempt_run": arow["run_id"],
                     "attempt_action": arow["action_id"],
                     "kind": "attempt_binding_mismatch"})

    def _verify_event_ledger_authority(self, event_id: str, *,
                                       action_id: str,
                                       where: str) -> None:
        """S3A-02:已提交事件的**完整账权威**核验(只读、零写入)。

        复用公共 `store.submit_event` 的**重放分支**(同源校验:事件行
        语义 hash/payload 复算、参与物 states 行内容重推导、appearance
        内容 hash、假设行 ID 重推导、事件出现清单 + 独立 links 表双向
        核验、投影/计划行齐全)—— get_event/find_event 是读视图,其
        四个身份列相等不是完整性证书。坏事件账(12 类:state 载荷/
        schema、出现来源/raw、假设前提、事件清单、投影/计划/links/
        state/出现/假设行删除)在本入口**消费/补账之前**结构化失败、
        保全证据、零写入;正常 writer 同一输入重放仍拒(复审继承专项
        24/24 反例即此路径)。附带记录的哈希复算见 _verify_commit_
        event。核验失败包装为 SearchIntegrityError(带源异常 detail)。
        """
        try:
            ev = self.store.get_event(event_id)
            if ev is None:
                raise SearchIntegrityError(
                    f"{where}:事件 {event_id} 不在账本(提交事实缺失;"
                    "保全失败,不补事件/不猜修)",
                    {"event_id": event_id, "action_id": action_id,
                     "where": where, "kind": "commit_event_missing"})
            event = _event_from_row(ev)
            proj = self.store.report_projection(event_id)
            plan = self.store.expansion_plan(event_id)
            if proj is None or plan is None:
                raise SearchIntegrityError(
                    f"{where}:事件 {event_id} 缺附随记录(投影/展开计划"
                    "行缺失;账本不完整,保全失败不补账)",
                    {"event_id": event_id, "action_id": action_id,
                     "where": where,
                     "kind": "commit_attached_record_missing",
                     "missing_table": ("report_projections" if proj is None
                                       else "expansion_plans")})
            out = self.store.submit_event(
                event, report_projection=proj, expansion_plan=plan,
                states=[], hypothesis_dict=None)
        except SearchIntegrityError:
            raise
        except sqlite3.OperationalError as exc:
            raise SearchConcurrencyError(
                f"{where}:权威核验取锁失败(SQLite busy;可见并发结果,"
                f"不当化学拒绝):{exc}",
                {"event_id": event_id, "where": where,
                 "kind": "sqlite_busy"}) from exc
        except Exception as exc:
            raise SearchIntegrityError(
                f"{where}:事件 {event_id} 的完整事件账权威核验失败"
                "(公共 writer 重放同源校验拒绝;保全证据、零写入、"
                "不消费/不补账/不猜修库)",
                {"event_id": event_id, "action_id": action_id,
                 "where": where,
                 "kind": "event_ledger_authority_failed",
                 "source_error": type(exc).__name__,
                 "source_detail": getattr(exc, "detail", None) or {},
                 "reason": str(exc)[:200]}) from exc
        if out.get("created"):
            raise SearchIntegrityError(
                f"{where}:事件 {event_id} 在权威核验中意外走首次提交"
                "路径(核验时行缺失后重现;权威记录不一致,保全失败)",
                {"event_id": event_id, "action_id": action_id,
                 "where": where,
                 "kind": "event_ledger_authority_unexpected_write"})

    def _verify_event_outcome(self, action_row, event_id: str,
                              *, where: str) -> None:
        """S3A-01/02:事件类 outcome 的完整闭合 —— event_id 非空、
        事件行存在、身份冻结到 action(列级)、完整账权威(重放同源)。
        空/缺失/异父事件一律零成功消费;合法非事件 outcome 走
        COMMIT_KIND_OUTCOME,不在此强制 event。"""
        if not event_id:
            raise SearchContractError(
                f"action {action_row['action_id']} 的事件类 outcome 缺"
                "event_id(空事件不可完成;非事件 outcome 须显式用 "
                f"{COMMIT_KIND_OUTCOME})",
                {"action_id": action_row["action_id"],
                 "where": where, "kind": "commit_event_id_empty"})
        ev = self.store.get_event(event_id)
        if ev is None:
            raise SearchIntegrityError(
                f"{where}:action {action_row['action_id']} 的 outcome "
                f"指向不存在的事件 {event_id}(提交事实缺失;零写入,"
                "不按索引缺失当成功)",
                {"action_id": action_row["action_id"],
                 "event_id": event_id, "where": where,
                 "kind": "commit_event_missing"})
        pairs = (
            ("run_id", "run_id", "run_id"),
            ("parent_path_id", "parent_path_id", "parent_path_id"),
            ("context_hash", "context_ref", "context_hash"),
        )
        if _row_get(action_row, "action_kind") == \
                ACTION_KIND_EXPAND_HYPOTHESIS:
            pairs += (("hypothesis_id", "subject_ref", "hypothesis_id"),)
        failed = {key: {
            "frozen": _row_get(action_row, frozen_field, ""),
            "event": ev[event_col]}
            for key, frozen_field, event_col in pairs
            if _row_get(action_row, frozen_field, "") != ev[event_col]}
        if failed:
            raise SearchIntegrityError(
                f"{where}:action {action_row['action_id']} 的 outcome "
                f"指向的事件 {event_id} 身份列与冻结身份不一致(错绑;"
                "零写入,保全失败)",
                {"action_id": action_row["action_id"],
                 "event_id": event_id, "where": where,
                 "kind": "commit_event_identity_mismatch",
                 "mismatch": failed})
        self._verify_event_ledger_authority(
            event_id, action_id=action_row["action_id"], where=where)

    def _verify_commit_record_hash(self, action_row, commit_row,
                                   *, where: str) -> None:
        """S3A-02:提交记录的 payload_hash 复算(记录被改 ⇒ 损坏,
        不以其自身哈希当证书;空 outcome_ref 落账时写的是哈希前缀,
        两种候选都复算)。"""
        base = {"action_id": action_row["action_id"],
                "outcome_kind": commit_row["commit_kind"],
                "event_id": commit_row["event_id"]}
        candidates = {content_hash({**base, "outcome_ref": oref})
                      for oref in (action_row["outcome_ref"], "")}
        if commit_row["payload_hash"] not in candidates:
            raise SearchIntegrityError(
                f"{where}:action {action_row['action_id']} 的提交记录"
                "哈希与记录/action 内容复算不一致(记录被改;保全失败,"
                "不猜修)",
                {"action_id": action_row["action_id"],
                 "commit_id": commit_row["commit_id"],
                 "where": where,
                 "kind": "commit_record_hash_mismatch",
                 "stored_hash": commit_row["payload_hash"]})

    def _preverify_completion(self, action_id: str, *,
                              outcome_kind: str,
                              event_id: str) -> None:
        """S3A-02:complete_action 写事务**之前**的只读权威核验。

        - 已有提交记录 ⇒ 幂等复用路径同样核验(记录引用的事件完整
          权威 + 记录哈希复算);
        - 事件类 outcome ⇒ event_id 非空/事件存在/身份冻结/完整账
          权威(公共 writer 重放同源,12×2 坏事件账在首次消费前拒);
        - 非事件 outcome 不强制 event(合法 decide/retrieve/transition
          的适用契约保留),但显式带了 event 引用则同样核验。
        本方法零写入(公共 writer 重放路径自带事务并在结尾回滚);写
        事务内的引用行核验由 _verify_action_references 再执行。
        """
        row = self.conn.execute(
            "SELECT * FROM search_actions WHERE action_id = ?",
            (action_id,)).fetchone()
        if row is None:
            raise SearchContractError(
                f"action 不存在:{action_id}",
                {"action_id": action_id, "kind": "action_missing"})
        commit_row = self.conn.execute(
            "SELECT * FROM search_commit_records WHERE action_id = ?",
            (action_id,)).fetchone()
        if commit_row is not None:
            record_event_id = commit_row["event_id"]
            if record_event_id:
                self._verify_event_outcome(
                    row, record_event_id, where="commit_reuse")
            self._verify_commit_record_hash(
                row, commit_row, where="commit_reuse")
            return
        if outcome_kind == COMMIT_KIND_EVENT:
            self._verify_event_outcome(
                row, event_id, where="first_complete")
        elif event_id:
            self._verify_event_outcome(
                row, event_id, where="first_complete")

    def _verify_done_action_authority(self, action_row) -> None:
        """S3A-02:done/已有完成结果的**复用核验**(claim 复用/submit
        复用/恢复 done 分支同源):提交记录存在、记录哈希可复算、
        记录引用的事件完整权威。不能 get 索引即成功。"""
        commit_row = self.conn.execute(
            "SELECT * FROM search_commit_records WHERE action_id = ?",
            (action_row["action_id"],)).fetchone()
        if commit_row is None:
            raise SearchIntegrityError(
                f"action {action_row['action_id']} 状态 done 但缺提交"
                "记录(记账不变量破坏;保全失败,不补写)",
                {"action_id": action_row["action_id"],
                 "run_id": action_row["run_id"],
                 "kind": "done_without_commit_record"})
        self._verify_commit_event(
            action_row["run_id"], action_row, commit_row)

    def complete_action(
        self, action_id: str, *, worker_id: str,
        outcome_kind: str = COMMIT_KIND_EVENT,
        outcome_ref: str = "", event_id: str = "",
        attempt_status: str = ATTEMPT_STATUS_RECORDED,
    ) -> dict:
        """完成 action(搜索记账事务:consume 预约、attempt 落账、
        action→done、写提交记录;B4 的后半段)。

        - **S3A-02 写账前完整权威核验**(见 _preverify_completion):
          事件类 outcome 不能空/不存在/错绑,已有提交记录的幂等复用
          同样经完整事件账权威(公共 writer 重放同源)+ 记录哈希复算;
        - **S3A-02 引用核验**(写事务内,_verify_action_references):
          本 action 必需的 attempt/预约行存在且归属正确,UPDATE 0 行
          按缺权威失败处理,不猜补坏行;
        - 认领所有权核验(陈旧 worker 不可越权;已有提交记录 ⇒ 幂等
          复用,不覆盖既有 outcome;记录与提交不一致 ⇒ 保全失败);
        - 提交记录 action 维度唯一(确定性 ID);
        - 事件已提交而记账未闭合(B4)⇒ 本方法幂等补账:预约恰好
          consume 一次(确定性 ID),不重复扣、不重开事件;
        - 合法非事件 outcome(COMMIT_KIND_OUTCOME)按其适用契约保留,
          不给无关 decide/retrieve 强加 event。
        """
        if outcome_kind not in COMMIT_KINDS:
            raise SearchContractError(
                f"commit_kind 非法:{outcome_kind!r}",
                {"kind": "invalid_commit_kind"})
        if attempt_status not in (ATTEMPT_STATUS_RECORDED,
                                  ATTEMPT_STATUS_FAILED):
            raise SearchContractError(
                f"attempt 完成状态非法:{attempt_status!r}(recorded/"
                "failed;abandoned 走 defer)",
                {"kind": "invalid_attempt_status"})
        # ---- S3A-02 阶段 1:写事务之前的只读权威核验(零写入) ----
        self._preverify_completion(
            action_id, outcome_kind=outcome_kind, event_id=event_id)
        self._begin()
        try:
            row = self.conn.execute(
                "SELECT * FROM search_actions WHERE action_id = ?",
                (action_id,)).fetchone()
            if row is None:
                raise SearchContractError(
                    f"action 不存在:{action_id}",
                    {"action_id": action_id, "kind": "action_missing"})
            commit_row = self.conn.execute(
                "SELECT * FROM search_commit_records WHERE action_id = ?",
                (action_id,)).fetchone()
            if commit_row is not None:
                if commit_row["event_id"] and event_id and \
                        commit_row["event_id"] != event_id:
                    raise SearchIntegrityError(
                        f"action {action_id} 已有提交记录且 event_id 不同"
                        "(不覆盖、不猜数据;保全证据)",
                        {"action_id": action_id,
                         "kind": "commit_record_conflict",
                         "recorded_event": commit_row["event_id"],
                         "submitted_event": event_id})
                if row["status"] != ACTION_STATUS_DONE:
                    raise SearchIntegrityError(
                        f"action {action_id} 已有提交记录但状态为 "
                        f"{row['status']}(提交记录与 action 状态同事务"
                        "写入,不一致即记账不变量破坏;保全失败)",
                        {"action_id": action_id,
                         "kind": "commit_record_status_mismatch",
                         "status": row["status"]})
                # 幂等复用(权威核验已在阶段 1 执行)
                self.conn.rollback()
                return {"completed": False, "unchanged": True,
                        "action_id": action_id,
                        "outcome_ref": row["outcome_ref"],
                        "reason": "already_committed"}
            if row["status"] == ACTION_STATUS_DONE:
                # done 但无提交记录(同事务写入的不变量被破坏)⇒ H08
                raise SearchIntegrityError(
                    f"action {action_id} 状态 done 但缺提交记录(记账"
                    "不变量破坏;保全失败,不补写)",
                    {"action_id": action_id,
                     "kind": "done_without_commit_record"})
            if row["status"] != ACTION_STATUS_CLAIMED:
                raise SearchClaimError(
                    f"action {action_id} 状态为 {row['status']}(不可完成)",
                    {"action_id": action_id, "kind": "not_claimed",
                     "status": row["status"]})
            if row["claimed_by"] != worker_id:
                raise SearchClaimError(
                    f"action {action_id} 由 {row['claimed_by']!r} 认领,"
                    f"{worker_id!r} 不可越权完成(陈旧 worker 不覆盖完成"
                    "结果)",
                    {"action_id": action_id, "kind": "owner_mismatch",
                     "claimed_by": row["claimed_by"],
                     "worker_id": worker_id})
            # ---- S3A-02 阶段 2:写事务内引用核验(存在/归属) ----
            self._verify_action_references(row)
            reservation_refs = json.loads(
                row["budget_reservation_ref"] or "[]")
            attempt_refs = json.loads(row["attempt_refs"] or "[]")
            # consume 预约(确定性 ID;reserved ⇒ consumed)
            for rid in reservation_refs:
                self.conn.execute(
                    "UPDATE budget_reservations SET status = ?,"
                    " settled_at = ? WHERE reservation_id = ? AND"
                    " status = ?",
                    (RESERVATION_STATUS_CONSUMED, now_iso(), rid,
                     RESERVATION_STATUS_RESERVED))
            # attempt 落账(open ⇒ recorded/failed)
            for aid in attempt_refs:
                self.conn.execute(
                    "UPDATE search_attempts SET status = ?, recorded_at = ?,"
                    " outcome_ref = ? WHERE expansion_attempt_id = ? AND"
                    " status = ?",
                    (attempt_status, now_iso(), outcome_ref, aid,
                     ATTEMPT_STATUS_OPEN))
            commit_id = stable_id("scommit", action_id)
            record_hash = content_hash({
                "action_id": action_id,
                "outcome_kind": outcome_kind,
                "outcome_ref": outcome_ref, "event_id": event_id})
            self.conn.execute(
                "INSERT INTO search_commit_records (commit_id, run_id,"
                " action_id, attempt_id, event_id, commit_kind,"
                " payload_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (commit_id, row["run_id"], action_id,
                 attempt_refs[0] if attempt_refs else "", event_id,
                 outcome_kind, record_hash, now_iso()))
            self.conn.execute(
                "UPDATE search_actions SET status = ?, outcome_ref = ?,"
                " updated_at = ? WHERE action_id = ?",
                (ACTION_STATUS_DONE, outcome_ref or record_hash[:20],
                 now_iso(), action_id))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return {"completed": True, "action_id": action_id,
                "outcome_ref": outcome_ref, "event_id": event_id}

    def defer_action(self, action_id: str, *, worker_id: str,
                     reason: str) -> dict:
        """挂起 action(claimed ⇒ deferred):释放**未执行**预约、
        attempt abandoned;挂起原因持久保留在独立列(S3b 的
        activate_deferred 按 reason/trigger 再激活,不覆盖冻结任务输入)。

        **S3A-03:先核"确实未执行"的持久事实**——释放必须消费未执行
        证据,已执行工作不得以 defer 退还已用预算:
        - 本 action 已有提交记录 ⇒ 拒(完成过);
        - 冻结身份下已存在已提交事件且无其他 action 的提交记录把该
          事件归因(重复执行方)⇒ 拒(本 action 的提交证据;先提交后
          defer 退额度是可执行漏洞,上限 1 连用三个事件 used=0 已拒);
        - 本 action 的请求处于 sent/responded/failed ⇒ 拒(已发送或
          已执行操作);registered 悬空请求不阻止挂起(真实请求登记
          额度本就不随 action 释放,悬空/失败真实请求继续占额);
        - 本 action 的 attempt 处于 recorded/failed ⇒ 拒(已执行);
        - 引用行(预约/attempt)缺失或异属 ⇒ 完整性失败(不猜补)。

        合法未执行路径保持:释放 reserved 预约、abandon open attempt、
        registered 请求转 abandoned(执行引用失效,后续发送/响应被
        生命周期拒绝),真实请求的 max_real_model_requests 预约行不在
        action 预约引用内、永不释放。"""
        self._begin()
        try:
            row = self.conn.execute(
                "SELECT * FROM search_actions WHERE action_id = ?",
                (action_id,)).fetchone()
            if row is None:
                raise SearchContractError(
                    f"action 不存在:{action_id}",
                    {"action_id": action_id, "kind": "action_missing"})
            if row["status"] == ACTION_STATUS_DEFERRED:
                self.conn.rollback()
                return {"deferred": True, "unchanged": True,
                        "reason": reason}
            if row["status"] != ACTION_STATUS_CLAIMED:
                raise SearchClaimError(
                    f"action {action_id} 状态为 {row['status']}(只有认领"
                    "方可挂起;已完成/未认领的 action 不可挂起)",
                    {"action_id": action_id, "kind": "not_claimed",
                     "status": row["status"]})
            if row["claimed_by"] != worker_id:
                raise SearchClaimError(
                    "挂起须由认领者执行(陈旧 worker 不可处置)",
                    {"action_id": action_id, "kind": "owner_mismatch",
                     "claimed_by": row["claimed_by"],
                     "worker_id": worker_id})
            # ---- S3A-03:未执行事实核验(先于任何释放) ----
            commit_row = self.conn.execute(
                "SELECT 1 FROM search_commit_records WHERE action_id = ?",
                (action_id,)).fetchone()
            if commit_row is not None:
                raise SearchContractError(
                    f"action {action_id} 已有提交记录(已执行工作不能以"
                    "挂起退还已用预算)",
                    {"action_id": action_id,
                     "kind": "defer_after_execution",
                     "evidence": "commit_record"})
            frozen_event = self.store.find_event(
                row["run_id"], row["parent_path_id"], row["subject_ref"],
                row["context_ref"])
            if frozen_event is not None:
                attributed = self.conn.execute(
                    "SELECT 1 FROM search_commit_records WHERE event_id = ?"
                    " AND action_id != ? LIMIT 1",
                    (frozen_event["event_id"], action_id)).fetchone()
                if attributed is None:
                    raise SearchContractError(
                        f"action {action_id} 冻结身份下已有已提交事件 "
                        f"{frozen_event['event_id']}(本 action 的执行"
                        "证据;已提交事件不能以挂起退还已用预算)",
                        {"action_id": action_id,
                         "kind": "defer_after_execution",
                         "evidence": "committed_event",
                         "event_id": frozen_event["event_id"]})
            req_rows = self.conn.execute(
                "SELECT request_id, status FROM model_requests WHERE"
                " action_id = ?", (action_id,)).fetchall()
            for r in req_rows:
                if r["status"] in (REQUEST_STATUS_SENT,
                                   REQUEST_STATUS_RESPONDED,
                                   REQUEST_STATUS_FAILED):
                    raise SearchContractError(
                        f"action {action_id} 的请求 {r['request_id']} 处于"
                        f" {r['status']}(已发送/已执行操作不能以挂起退还"
                        "已用预算;真实请求登记额度本就不释放)",
                        {"action_id": action_id,
                         "kind": "defer_after_execution",
                         "evidence": f"request_{r['status']}",
                         "request_id": r["request_id"]})
            # ---- 引用行核验(行缺失/异属 ⇒ 完整性失败,不猜补) ----
            self._verify_action_references(row)
            reservation_refs = json.loads(
                row["budget_reservation_ref"] or "[]")
            attempt_refs = json.loads(row["attempt_refs"] or "[]")
            for aid in attempt_refs:
                arow = self.conn.execute(
                    "SELECT status FROM search_attempts WHERE"
                    " expansion_attempt_id = ?", (aid,)).fetchone()
                if arow["status"] in (ATTEMPT_STATUS_RECORDED,
                                      ATTEMPT_STATUS_FAILED):
                    raise SearchContractError(
                        f"action {action_id} 的 attempt {aid} 已落账 "
                        f"({arow['status']};已执行工作不能以挂起退还"
                        "已用预算)",
                        {"action_id": action_id,
                         "kind": "defer_after_execution",
                         "evidence": f"attempt_{arow['status']}",
                         "attempt_id": aid})
            # ---- 合法未执行:释放/abandon/请求生命周期闭合 ----
            for rid in reservation_refs:
                self.conn.execute(
                    "UPDATE budget_reservations SET status = ?,"
                    " settled_at = ? WHERE reservation_id = ? AND"
                    " status = ?",
                    (RESERVATION_STATUS_RELEASED, now_iso(), rid,
                     RESERVATION_STATUS_RESERVED))
            for aid in attempt_refs:
                self.conn.execute(
                    "UPDATE search_attempts SET status = ?, recorded_at = ?"
                    " WHERE expansion_attempt_id = ? AND status = ?",
                    (ATTEMPT_STATUS_ABANDONED, now_iso(), aid,
                     ATTEMPT_STATUS_OPEN))
            # registered 悬空请求 ⇒ abandoned(执行引用失效;S3A-04
            # 的发送/响应/失败消费口将按生命周期拒绝);真实请求的
            # max_real_model_requests 预约不在此释放(悬空继续占额)
            self.conn.execute(
                "UPDATE model_requests SET status = ?, updated_at = ? WHERE"
                " action_id = ? AND status = ?",
                (REQUEST_STATUS_ABANDONED, now_iso(), action_id,
                 REQUEST_STATUS_REGISTERED))
            self.conn.execute(
                "UPDATE search_actions SET status = ?, defer_reason = ?,"
                " updated_at = ? WHERE action_id = ?",
                (ACTION_STATUS_DEFERRED, reason, now_iso(), action_id))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return {"deferred": True, "action_id": action_id, "reason": reason}

    # ------------------------------------------------------------ 派生视图

    def budget_snapshot(self, run_id: str) -> dict:
        """预算快照(派生值;每次从持久预约行重算 —— 内存重置后仍从
        记录复算;snapshot 不是事实源,可用记录校验)。"""
        limits = self._limits(run_id)
        run_level: dict[str, dict] = {}
        for key in ("max_total_search_actions", "max_retrievals_total",
                    "max_scenario_transitions", "max_real_model_requests"):
            used = _reservation_units(self.conn, run_id, key, "")
            run_level[key] = {"max": int(limits[key]), "used": used,
                              "remaining": int(limits[key]) - used}
        scoped: dict[str, dict[str, dict]] = {}
        for key in ("max_retrievals_per_parent",
                    "max_alternative_hypotheses_per_parent",
                    "max_attempts_per_hypothesis",
                    "max_reopens_per_hypothesis"):
            scoped[key] = {}
            rows = self.conn.execute(
                "SELECT scope, units FROM budget_reservations WHERE"
                " run_id = ? AND limit_key = ? AND status IN (?, ?)",
                (run_id, key, RESERVATION_STATUS_RESERVED,
                 RESERVATION_STATUS_CONSUMED)).fetchall()
            per_scope: dict[str, int] = {}
            for r in rows:
                per_scope[r["scope"]] = per_scope.get(
                    r["scope"], 0) + int(r["units"])
            for scope, used in per_scope.items():
                scoped[key][scope] = {
                    "max": int(limits[key]), "used": used,
                    "remaining": int(limits[key]) - used}
        return {"version": SEARCH_LIMITS_VERSION, "run_level": run_level,
                "scoped": scoped}

    def stop_report(
        self, run_id: str, *, user_stop: bool = False,
        refusals: list[dict] | None = None,
        no_local_candidate: bool = False,
    ) -> dict:
        """停止报告(队列入口;H05):从持久状态派生原因集合,按冻结
        优先级取主因,保留其他原因与未探索集合。

        - user_stop 恒最优先;
        - budget_limit:任一上限 used ≥ max(真实零/耗尽即停该资源);
        - depth_limit / product_width_limit 等入队拒绝来自 refusals
          (调用方收集;瞬态拒绝不留行 —— 拒绝原因即返回值);
        - awaiting_prediction:存在 registered/sent 无响应请求且无其他
          pending 动作;
        - **S3A-05:claimed/inflight action 与 open attempt 计入未完成
         集合并阻止 exhausted_search** —— 存在实际持久的未完成工作
          (认领中/尝试进行中)时不得称"所有路线都探索完";此时可
          primary=None(尚未停止)或由调用方登记准确等待语义,六原因
          顺序保持不加新原因;
        - exhausted_search:队列空、无 claimed/open attempt/deferred/
          blocked/悬空请求(存在 deferred/知识缺口时**不**称"所有路线
          都探索完"——停止不是化学终点);
        - no_local_candidate:检索/池无任何候选(调用方如实标记)。
        """
        reasons: set[str] = set()
        snapshot = self.budget_snapshot(run_id)
        # 预算成因:实际耗尽(used>0 且 used>=max)或实际动作被拒
        # (refusals 携带 budget_limit 的 limit_key)—— 从未消费且从未
        # 被要求的零上限(如默认 real requests 0/off)不构成停止原因
        # (§4.2:零预算只阻止确实消费该资源的动作,不看任一上限为 0
        # 就全局停)。
        exhausted_keys = [
            key for key, v in snapshot["run_level"].items()
            if v["used"] > 0 and v["max"] <= v["used"]]
        for key, scopes in snapshot["scoped"].items():
            for scope, v in scopes.items():
                if v["used"] > 0 and v["max"] <= v["used"]:
                    exhausted_keys.append(f"{key}@{scope}")
        refusal_budget_keys = [
            str((r or {}).get("limit_key")
                or (r or {}).get("detail", {}).get("limit_key"))
            for r in (refusals or [])
            if (r or {}).get("reason") == STOP_REASON_BUDGET_LIMIT]
        refusal_budget_keys = [k for k in refusal_budget_keys if k]
        if exhausted_keys or refusal_budget_keys:
            reasons.add(STOP_REASON_BUDGET_LIMIT)
        refusal_kinds = {(r or {}).get("reason", "")
                         for r in (refusals or [])}
        if STOP_REASON_DEPTH_LIMIT in refusal_kinds:
            reasons.add(STOP_REASON_DEPTH_LIMIT)
        pending_actions = int(self.conn.execute(
            "SELECT COUNT(*) FROM search_actions WHERE run_id = ? AND"
            " status = ?", (run_id, ACTION_STATUS_PENDING)).fetchone()[0])
        deferred = int(self.conn.execute(
            "SELECT COUNT(*) FROM search_actions WHERE run_id = ? AND"
            " status = ?", (run_id, ACTION_STATUS_DEFERRED)).fetchone()[0])
        blocked = int(self.conn.execute(
            "SELECT COUNT(*) FROM search_actions WHERE run_id = ? AND"
            " status = ?", (run_id, ACTION_STATUS_BLOCKED)).fetchone()[0])
        # ---- S3A-05:正在执行的动作与开放尝试(持久未完成工作) ----
        claimed_actions = int(self.conn.execute(
            "SELECT COUNT(*) FROM search_actions WHERE run_id = ? AND"
            " status = ?", (run_id, ACTION_STATUS_CLAIMED)).fetchone()[0])
        open_attempts = int(self.conn.execute(
            "SELECT COUNT(*) FROM search_attempts WHERE run_id = ? AND"
            " status = ?", (run_id, ATTEMPT_STATUS_OPEN)).fetchone()[0])
        pending_requests = int(self.conn.execute(
            "SELECT COUNT(*) FROM model_requests WHERE run_id = ? AND"
            " status IN (?, ?)",
            (run_id, REQUEST_STATUS_REGISTERED,
             REQUEST_STATUS_SENT)).fetchone()[0])
        if pending_requests and not pending_actions:
            reasons.add(STOP_REASON_AWAITING_PREDICTION)
        if no_local_candidate:
            reasons.add(STOP_REASON_NO_LOCAL_CANDIDATE)
        if not pending_actions and not deferred and not blocked \
                and not pending_requests and not refusal_kinds \
                and not no_local_candidate and not exhausted_keys \
                and not claimed_actions and not open_attempts:
            reasons.add(STOP_REASON_EXHAUSTED_SEARCH)
        if user_stop:
            reasons.add(STOP_REASON_USER_STOP)
        unexplored = {
            "pending_actions": pending_actions, "deferred": deferred,
            "blocked": blocked,
            "claimed_actions": claimed_actions,
            "open_attempts": open_attempts,
            "pending_requests": pending_requests,
            "note": ("停止不是化学终点;存在 deferred/知识缺口时不称"
                     "“所有路线都探索完”;claimed/open attempt 是仍在"
                     "执行的未完成工作,存在时不报 exhausted_search"),
        }
        report = resolve_search_stop(reasons, unexplored=unexplored)
        report["budget"] = snapshot
        report["budget_exhausted_keys"] = sorted(
            set(exhausted_keys) | set(refusal_budget_keys))
        return report

    # ------------------------------------------------------------ 恢复协议

    def recover_run(self, run_id: str, *,
                    policy_block: dict | None = None,
                    worker_id: str = "recovery") -> dict:
        """四崩溃边界的恢复协议(§4.4;新进程/新连接调用)。

        前置:run 已注册且策略身份一致(未注册/不一致 ⇒ fail-closed,
        不猜数据)。逐 action 按权威记录恢复:
        - 提交记录存在 ⇒ H08 + S3A-02:事件行身份列一致**且完整事件账
          权威核验 + 记录哈希复算**(不一致 ⇒ 保全失败,零写入;done
          而无提交记录同样是记账不变量破坏);
        - 事件已提交(公共路径)而记账未闭合 ⇒ B4 合法恢复:经
          complete_action 的写前完整权威核验后,以记录在案的 claim
          owner 名义幂等补账(consume 恰一次、不重开事件、不重复
          扣额;执行权来自已验证的持久权威记录);
        - claimed 且有 commit bundle artifact ⇒ B3:先验版本/hash/身份
          (S3A-01:事件完整身份冻结到 action)再消费同一 output/
          attempt 完成(不重发请求);artifact 损坏或身份错绑 ⇒
          H07 完整性错误、保全原文件(报告披露,不抛出中断其余
          action 的恢复);
        - claimed 无 artifact/无事件 ⇒ B1:读冻结 action/attempt/预约
          继续(引用行核验;同 attempt、不重扣;等待执行方续跑,
          不自动执行);
        - 请求 registered/sent 无响应 ⇒ B2:暴露 pending/unknown,
          不默发第二请求(显式重试走 register_model_request 新键)。
        返回结构化恢复报告(每 action 的边界归类与处置结果)。
        """
        stored = self.search_policy_block(run_id)
        if policy_block is not None:
            if json.dumps(policy_block, ensure_ascii=False,
                          sort_keys=True) != json.dumps(
                    stored, ensure_ascii=False, sort_keys=True):
                raise SearchRecoveryError(
                    f"run {run_id} 恢复拒绝:搜索策略身份与注册不一致"
                    "(profile/策略身份不一致 fail-closed,不原地切换)",
                    {"run_id": run_id,
                     "kind": "search_policy_identity_mismatch"})
        state = _crash_boundary_rows(self.conn, run_id)
        report = {
            "run_id": run_id, "policy_version": SEARCH_LIMITS_VERSION,
            "actions": [],
            "pending_requests": [
                {"request_id": r["request_id"],
                 "provider_kind": r["provider_kind"],
                 "status": r["status"],
                 "network_request_count": r["network_request_count"],
                 "note": "pending/unknown;不默发第二请求,显式重试须新"
                         " request 及剩余额度"}
                for r in state["pending_requests"]],
            "budget": self.budget_snapshot(run_id),
        }
        for a in state["actions"]:
            entry = {"action_id": a["action_id"],
                     "action_kind": a["action_kind"],
                     "status": a["status"], "boundary": None,
                     "disposition": ""}
            commit = state["commits"].get(a["action_id"])
            if a["status"] == ACTION_STATUS_DONE:
                # ---- H8:done 的记账闭合证据核验 ----
                if commit is None:
                    raise SearchIntegrityError(
                        f"恢复 {run_id}:action {a['action_id']} 状态 done"
                        "但缺提交记录(记账不变量破坏;保全失败,不补写)",
                        {"run_id": run_id, "action_id": a["action_id"],
                         "kind": "done_without_commit_record"})
                self._verify_commit_event(run_id, a, commit)
                entry["boundary"] = "B4_verified"
                entry["disposition"] = "done_commit_verified"
                report["actions"].append(entry)
                continue
            if a["status"] != ACTION_STATUS_CLAIMED:
                entry["disposition"] = "not_claimed_no_recovery_needed"
                report["actions"].append(entry)
                continue
            entry["boundary"] = "B1_claimed_pending_completion"
            owner = a["claimed_by"] or worker_id  # 记录在案的 claim owner
            if commit is not None:
                # ---- H08:提交事实 ↔ ledger 权威一致性 ----
                self._verify_commit_event(run_id, a, commit)
                entry["boundary"] = "B4_verified"
                entry["disposition"] = "already_committed_verified"
                report["actions"].append(entry)
                continue
            # 无提交记录的 claimed action:B4(事件已提交?)→ B3 → B1
            frozen_event = self.store.find_event(
                run_id, a["parent_path_id"], a["subject_ref"],
                a["context_ref"])
            if frozen_event is not None:
                # ---- B4 合法恢复:事件已提交、记账未闭合 ----
                # 以记录在案的 claim owner 名义完成(执行权来自已验证
                # 的持久权威记录:事件行 + 认领/预约/attempt 行)
                outcome = self.complete_action(
                    a["action_id"], worker_id=owner,
                    outcome_kind=COMMIT_KIND_EVENT,
                    event_id=frozen_event["event_id"])
                entry["boundary"] = (
                    "B4_event_committed_bookkeeping_incomplete")
                entry["disposition"] = (
                    "bookkeeping_completed_idempotent"
                    if outcome.get("completed") else outcome.get("reason"))
                report["actions"].append(entry)
                continue
            task_key = a["task_key"]
            bundle = None
            artifact_error = None
            if self.artifact_store is not None and task_key:
                path = self.artifact_store._path(
                    task_key, "search_commit_bundle")
                if path.is_file():
                    try:
                        bundle = read_search_artifact(
                            self.artifact_store, task_key,
                            "search_commit_bundle")
                    except SearchArtifactIntegrityError as exc:
                        artifact_error = exc
            if bundle is not None:
                # ---- B3 先验:版本/hash/身份(S3A-01:事件完整身份冻结
                # 到 action,与正常 submit 同一判据;身份错绑与字节损坏
                # 同样按完整性失败处理,保全原文件、零消费) ----
                try:
                    self._verify_bundle_identity(a, bundle)
                except SearchArtifactIntegrityError as exc:
                    artifact_error = exc
                    bundle = None
            if artifact_error is not None:
                # ---- H07/S3A-01:保全原文件、明确失败,不覆盖 ----
                entry["boundary"] = "B3_artifact_written_event_uncommitted"
                entry["disposition"] = {
                    "error": "SearchArtifactIntegrityError",
                    "kind": artifact_error.detail.get("kind"),
                    "note": "原文件保全,不静默跳过/不重跑覆盖;身份错绑"
                            "事件不消费"}
                report["actions"].append(entry)
                continue
            if bundle is not None:
                # ---- B3:验版本/身份后消费同一 output/attempt ----
                event_payload = bundle["payload"]["event"]
                event = PathwayEvent(
                    event_id=event_payload["event_id"],
                    run_id=event_payload["run_id"],
                    parent_path_id=event_payload["parent_path_id"],
                    hypothesis_id=event_payload["hypothesis_id"],
                    context_hash=event_payload["context_hash"],
                    participants=event_payload["participants"],
                    participant_state_refs=event_payload[
                        "participant_state_refs"],
                    catalytic_support=event_payload["catalytic_support"],
                    schema_version=event_payload["schema_version"],
                )
                self.store.submit_event(
                    event,
                    report_projection=bundle["payload"]["report_projection"],
                    expansion_plan=bundle["payload"]["expansion_plan"],
                    states=bundle["payload"]["states"],
                    hypothesis_dict=bundle["payload"]["hypothesis_dict"],
                )
                self.complete_action(
                    a["action_id"], worker_id=owner,
                    outcome_kind=COMMIT_KIND_EVENT,
                    event_id=event.event_id)
                entry["boundary"] = "B3_artifact_written_event_uncommitted"
                entry["disposition"] = ("consumed_same_output_attempt;"
                                        "请求不重发,事件仅一次")
                report["actions"].append(entry)
                continue
            # ---- B1:读冻结 action/attempt/预约继续(不自动执行); ----
            # S3A-02:冻结引用行核验(预约/attempt 行缺失或异属 ⇒ 缺
            # 权威失败,不按"intact"披露)
            self._verify_action_references(a)
            entry["boundary"] = "B1_claimed_pending_completion"
            entry["disposition"] = (
                "frozen_attempt_reservation_intact;预算未重复扣,等待"
                "执行方续跑(不按当前 revision 重算任务身份)")
            report["actions"].append(entry)
        return report

    def _verify_commit_event(self, run_id: str, action_row,
                             commit_row) -> None:
        """H08 + S3A-02:提交记录的完整权威核验。

        - 记录哈希复算(记录列/action 内容重推;被改 ⇒ 损坏);
        - 引用的事件行存在且身份列与 action 冻结身份一致(不一致 ⇒
          保全证据、明确失败,不补事件/修库);
        - **完整事件账权威**(公共 writer 重放同源,12×2 坏事件账
          在恢复消费前拒)—— get_event 的身份列不是完整性证书;
        - 非事件 outcome(commit_kind 非 event_committed)只核记录
          哈希,不强加事件。
        """
        # ---- S3A-02:记录哈希复算(先于事件核验;任何记录均核) ----
        self._verify_commit_record_hash(action_row, commit_row,
                                         where="commit_record_verify")
        event_id = commit_row["event_id"]
        if not event_id:
            return  # 非事件 outcome:无事件权威可核(记录哈希已核)
        ev = self.store.get_event(event_id)
        if ev is None:
            raise SearchIntegrityError(
                f"恢复 {run_id}:提交记录引用的事件 {event_id} 在账本"
                "缺失(提交事实与 ledger 不一致;保全证据、明确失败,"
                "不默认补事件/修库)",
                {"run_id": run_id, "action_id": action_row["action_id"],
                 "event_id": event_id,
                 "kind": "commit_record_event_missing"})
        if ev["run_id"] != run_id or \
                ev["hypothesis_id"] != action_row["subject_ref"] or \
                ev["parent_path_id"] != action_row["parent_path_id"] or \
                ev["context_hash"] != action_row["context_ref"]:
            raise SearchIntegrityError(
                f"恢复 {run_id}:提交记录引用的事件 {event_id} 身份列与"
                "action 冻结身份不一致(H08;保全失败,不猜数据)",
                {"run_id": run_id, "action_id": action_row["action_id"],
                 "event_id": event_id,
                 "kind": "commit_record_event_identity_mismatch"})
        # ---- S3A-02:完整事件账权威(重放同源;坏账保全失败) ----
        self._verify_event_ledger_authority(
            event_id, action_id=action_row["action_id"],
            where="commit_record_verify")

    def _verify_bundle_identity(self, action_row,
                                bundle_envelope) -> None:
        """B3 消费前的版本/身份验证(bundle 版本、action/attempt 绑定、
        **事件完整身份冻结到 action(S3A-01)**、task_key 绑定、事件
        ID 与冻结身份的重推导)。

        S3A-01:合法有效但属于**别的动作/别的身份**的事件(仅 run/
        parent/context/hypothesis 之一不同)在消费前拒 —— 与正常
        submit 共用 `_event_identity_mismatch` 判据,"bundle 绑定了本
        action"不等于"事件属于本 action"。"""
        payload = bundle_envelope.get("payload") or {}
        if payload.get("bundle_version") != SEARCH_COMMIT_BUNDLE_VERSION:
            raise SearchArtifactIntegrityError(
                f"commit bundle 版本未知:{payload.get('bundle_version')!r}"
                "(fail-closed,不按未知版本消费)",
                {"kind": "bundle_version_unknown",
                 "bundle_version": payload.get("bundle_version")})
        if payload.get("action_id") != action_row["action_id"]:
            raise SearchArtifactIntegrityError(
                "commit bundle 的 action 绑定与当前 action 不一致",
                {"kind": "bundle_action_binding_mismatch",
                 "bundle_action": payload.get("action_id"),
                 "action_id": action_row["action_id"]})
        attempt_refs = json.loads(
            _row_get(action_row, "attempt_refs", "[]") or "[]")
        if payload.get("attempt_id") and attempt_refs and \
                payload["attempt_id"] not in attempt_refs:
            raise SearchArtifactIntegrityError(
                "commit bundle 的 attempt 绑定与 action 冻结 attempt 不"
                "一致(不消费他人 attempt 的 output)",
                {"kind": "bundle_attempt_binding_mismatch",
                 "bundle_attempt": payload.get("attempt_id"),
                 "frozen_attempts": attempt_refs})
        event_payload = payload.get("event") or {}
        # ---- S3A-01:事件完整身份冻结(与 submit 同一判据) ----
        event = PathwayEvent(
            event_id=event_payload.get("event_id", ""),
            run_id=event_payload.get("run_id", ""),
            parent_path_id=event_payload.get("parent_path_id", ""),
            hypothesis_id=event_payload.get("hypothesis_id", ""),
            context_hash=event_payload.get("context_hash", ""),
            participants=event_payload.get("participants") or [],
            participant_state_refs=event_payload.get(
                "participant_state_refs") or [],
            catalytic_support=event_payload.get("catalytic_support") or [],
            schema_version=event_payload.get("schema_version") or "",
        )
        mismatch = _event_identity_mismatch(action_row, event)
        if mismatch:
            raise SearchArtifactIntegrityError(
                "commit bundle 内事件的身份与 action 冻结身份不一致"
                "(S3A-01:有效但属于别的身份的事件不消费;保全原文件)",
                {"kind": "bundle_event_identity_not_frozen",
                 "action_id": action_row["action_id"],
                 "mismatch": mismatch})
        # ---- task_key 绑定(双方非空时必须一致) ----
        bundle_task_key = str(payload.get("task_key") or "")
        action_task_key = str(_row_get(action_row, "task_key", "") or "")
        if bundle_task_key and action_task_key and \
                bundle_task_key != action_task_key:
            raise SearchArtifactIntegrityError(
                "commit bundle 的 task_key 与 action 冻结 task_key 不"
                "一致(同源任务绑定;不消费其他任务的 output)",
                {"kind": "bundle_task_key_binding_mismatch",
                 "action_id": action_row["action_id"],
                 "bundle_task_key": bundle_task_key,
                 "action_task_key": action_task_key})
        rederived = event_id_for(
            event_payload.get("run_id", ""),
            event_payload.get("parent_path_id", ""),
            event_payload.get("hypothesis_id", ""),
            event_payload.get("context_hash", ""),
            content_hash({
                "participants": event_payload.get("participants"),
                "catalytic_support": event_payload.get("catalytic_support"),
                "hypothesis_id": event_payload.get("hypothesis_id"),
            }))
        if rederived != event_payload.get("event_id"):
            raise SearchArtifactIntegrityError(
                "commit bundle 内事件 ID 与其身份重推导不一致(先验身份"
                "失败,不消费)",
                {"kind": "bundle_event_identity_mismatch",
                 "rederived": rederived,
                 "bundle_event_id": event_payload.get("event_id")})


# ---- 便捷驱动入口(合成/scripted 夹具用;不是生产 runner) ----


def commit_search_event(
    ledger: SearchLedger, action_id: str, event: PathwayEvent, *,
    report_projection: dict, expansion_plan: dict, states: list[dict],
    hypothesis_dict: dict | None, worker_id: str,
    attempt_id: str = "", task_key: str = "",
    write_bundle: bool = False,
    crash_after: str | None = None,
) -> dict:
    """claim 后的完整提交链(bundle artifact → 事件[公共事务] → 搜索
    记账事务)。

    - write_bundle=True ⇒ 事件提交前先写 commit bundle artifact
      (B3 输入;不可覆盖);
    - crash_after="event_submitted" ⇒ 事件提交后、记账前**模拟崩溃**
      (抛 SearchCrashInjection;B4 边界的显式注入点,生产路径不传);
    - 两段事务之间的中断由 B4 恢复协议闭合(权威 = 事件行 + 认领/
      预约/attempt 行 + 提交记录;不以内存状态或 checkpoint 声称
      跨文件原子)。
    """
    if write_bundle:
        if not task_key:
            raise SearchContractError(
                "write_bundle 需要 task_key(artifact 绑定任务身份)",
                {"kind": "missing_task_key"})
        ledger.write_commit_bundle(
            action_id=action_id, attempt_id=attempt_id, event=event,
            report_projection=report_projection,
            expansion_plan=expansion_plan, states=states,
            hypothesis_dict=hypothesis_dict, task_key=task_key)
    submitted = ledger.submit_action_event(
        action_id, event, report_projection=report_projection,
        expansion_plan=expansion_plan, states=states,
        hypothesis_dict=hypothesis_dict, worker_id=worker_id)
    if crash_after == "event_submitted":
        raise SearchCrashInjection(
            "事件已提交、搜索记账未闭合(B4 注入点)",
            {"action_id": action_id, "event_id": event.event_id,
             "submitted": submitted})
    return ledger.complete_action(
        action_id, worker_id=worker_id,
        outcome_kind=COMMIT_KIND_EVENT, event_id=event.event_id)
