"""S3b PPV1 独立 runner 执行流 —— start/resume 分流后的确定性驱动
(实施书 §6.2;契约随 search-6 / profile-14 / runflow-3 登记)。

职责:workflow.runner 的 PPV1 分流目标 —— **独立**执行/存储(不落
legacy CN/PathwayStore/预算派生/LangGraph):
- start:严格 root state(工厂守卫)→ 根 context(持久化 artifact,
  消费经 from_dict 内容身份核验)→ **冻结计划输入持久化(S3b r2/
  S3B-01)** → 注册搜索 run(profile 策略块:十上限 + format_feedback
  policy)→ 根 retrieve 入队(任务输入绑定计划摘要)→ 确定性驱动循环;
- resume:身份逐字段核对(code/资产/策略/profile/prediction)→
  **执行会话互斥(S3b r2/S3B-04:run 目录 flock,双进程只一方取得
  执行权;崩溃 OS 自动释放,新进程接管)** → 冻结计划输入核对
  (S3B-01:无 plan 沿冻结输入;传入内容不符结构化拒)→ **冻结
  计划与独立既存 run/root/task 原绑定核对(S3b r3/S3B-01 后段
  锚定:start 落账的根 retrieve 行 plan_digest/task_key 是独立
  权威,artifact 自洽摘要不是证书;先于 recover 补账/事件/调度/
  consume,覆盖 root retrieve 已 done 的 B3/B4)** → recover_run
  四崩溃边界(B4 补账/B3 消费 bundle/B1 续跑/B2 披露)→ **恢复
  裁定的坏 artifact/缺权威 action 明确隔离(S3B-02:不重执行、
  证据保全,合法独立任务继续)** → 继续驱动循环(不重建/不覆盖既有
  搜索/attempt/request/提交记录);
- 驱动循环(scripted/规则级):pending 顺序认领 → 按 action_kind 分发:
  retrieve(池获取;**空池 + 模型在计划内仍进 decide —— 空池可组装
  底物档案并消费 novel 响应,S3b r2/S3B-05**)/ decide(schedule_
  hypotheses + 底物档案 + scripted 模型 proposals[] 协议 + 有界格式
  反馈 + **novel 独立假设消费:S3B-05**)/ expand_hypothesis(固定
  生产链:AtomTool→诊断→converter→audit→admission→提交;
  **AuditContractError 窄捕获记 contract_aborted 方法失败,不吞成
  成功**)/ activate_deferred(两类 deferred 激活)/ scenario_
  transition(derive_child_context 冻结旧阶段快照,只后效,转换后
  followup 用新上下文;**pending_followup 创建时一次冻结入载荷,
  S3b r2/S3B-03**);
- 恢复补调度(S3B-03):reconcile_followups 从权威事件/展开计划/
  提交记录与冻结计划的显式转换意图逐对象幂等补齐(0/部分/全部
  followup 与转换附随;不以任意 payload 引用计数当完整性证书);
- 停止:队列耗尽 + stop_report(主因优先级、claimed/open/deferred/
  blocked 未探索集合;**blocked 对象与深度原因从持久行同源派生,
  S3b r2/S3B-06**);停止不是化学终点。

**预算纪律**:PPV1 不从 model 对象派生任何真实请求预算(与 legacy
的 max_llm_calls 随展开派生不同 —— 传入 model 只记录身份,额度仍是
search_limits 的 max_real_model_requests,默认 0;真实请求登记被
register_model_request 拒绝 ⇒ 网络发送被阻止)。scripted/fake 恒
network_request_count=0。

**计划(plan)是合成/规则级输入**(测试与验收用;不是生产数据):
{condition_facts, scenario_ref, dependencies, pools: {substrate_smiles:
[spec...]}, model: {provider_kind, responses: [text...]},
scenario_transitions: [{after_hypothesis_key, transition}],
activations: [{deferred_type, trigger, expected_parent_revision,
parent}], schedule_budget: {max_select}}。

**S3b r2 冻结输入身份(S3B-01)**:计划在 start 时持久化为冻结
artifact(plan_digest 内容绑定);resume 的 retrieve/decide/模型
请求/expand/followup/转换全部消费该冻结来源 —— 旧任务不消费新输入;
不传 plan 沿冻结输入(缺输入不变空池);传入计划内容不符 ⇒ 结构化
拒绝(frozen_plan_mismatch),差异须显式新 revision/新任务登记;
decide 已冻结的 pool_digest 与 retrieve 任务的 plan_digest 同源核验
(同计划正控保持)。

**S3b r3 后段锚定(S3B-01 残余收口)**:r2 的计划绑定只在 resume
传入比对侧与 retrieve/decide 执行层到达 —— root retrieve 已 done 的
B3/B4 后段不可达,自洽重封装 artifact(重算自身 plan_digest 与信封
payload_hash)仍会被消费。r3 在 resume **首消费前**(recover_run
补账/事件提交/新调度/预算 consume 之前)把读取的冻结计划与独立
既存权威核对:start 时落账的根 retrieve 行(search_actions.payload
的 plan_digest;task_key 由同一 decision_task_key 单一来源派生)
—— artifact 文件内的自 hash/自己写的 plan_digest 不是独立证书。
缺锚(frozen_plan_anchor_missing)/坏锚(frozen_plan_anchor_corrupt)
/摘要不符(frozen_plan_binding_mismatch)先结构化拒,业务表/event/
commit/consume 零新增,原资料保全。正常同计划、省略 plan、显式同
计划、合法原计划转换恢复全保持;只改一份 artifact 的自洽重封装
(B3/B4)必须拒。不做密码学签名、不抗全库协同改写(超范围)。
"""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path

from ..adapters.v3_engine import v3_code_identity
from ..config import V43Config
from ..domain.models import content_hash, now_iso, stable_id
from ..storage.artifact_store import ArtifactStore
from ..storage.run_identity import (
    PROFILE_POLLUTANT_PATHWAY_V1,
    build_run_identity,
    check_resume_identity,
    load_run_identity,
    retrieval_asset_identity,
    scripted_asset_identity,
    write_run_identity,
)
from .audit import AuditContractError
from .chemstate import build_chemical_state
from .model_protocol import (
    FEEDBACK_ELIGIBLE,
    ModelProtocolError,
    parse_model_proposals,
    register_format_feedback_round,
)
from .path_context import build_path_context, derive_child_context
from .production import (
    build_cyclic_dependency,
    expand_hypothesis_production,
    load_context,
    persist_context,
    prepare_hypothesis,
)
from .profile import (
    FORMAT_FEEDBACK_POLICY_VERSION,
    build_profile_identity_block,
)
from .queue import (
    DEFERRED_TRIGGER_EXPLICIT,
    OUTCOME_KIND_ACTIVATED,
    OUTCOME_KIND_ADMISSION_DEFERRED,
    OUTCOME_KIND_ADMISSION_REJECTED,
    OUTCOME_KIND_CONTRACT_ABORTED,
    OUTCOME_KIND_METHOD_FAILED,
    OUTCOME_KIND_NO_LOCAL_CANDIDATE,
    OUTCOME_KIND_POOL_DIGEST,
    OUTCOME_KIND_SCHEDULED,
    OUTCOME_KIND_TRANSITION_APPLIED,
    activate_deferred,
    enqueue_coproduct_followups,
    enqueue_scenario_transition,
    record_expansion_outcome,
    schedule_hypotheses,
)
from .search import (
    ACTION_KIND_ACTIVATE_DEFERRED,
    ACTION_KIND_DECIDE,
    ACTION_KIND_EXPAND_HYPOTHESIS,
    ACTION_KIND_RETRIEVE,
    ACTION_KIND_SCENARIO_TRANSITION,
    COMMIT_KIND_OUTCOME,
    PROVIDER_KIND_REAL,
    PROVIDER_KIND_SCRIPTED,
    SearchArtifactIntegrityError,
    SearchBudgetExhausted,
    SearchClaimError,
    SearchConcurrencyError,
    SearchContractError,
    SearchCrashInjection,
    SearchLedger,
    decision_task_key,
    expansion_task_key,
    read_search_artifact,
    search_policy_version,
)
from .store import PollutantPathwayStore
from .substrate_profile import build_substrate_profile

RUNFLOW_VERSION = "ppv1-runflow-3"
FROZEN_PLAN_VERSION = "ppv1-frozen-plan-1"
FROZEN_PLAN_TASK_KEY = "run-plan"
FROZEN_PLAN_ARTIFACT = "frozen_plan"


class PPV1RunError(RuntimeError):
    """PPV1 run 入口契约违反(结构化)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _plan_digest(plan: dict) -> str:
    return content_hash(plan or {})


def _fact_list(raw: list) -> list:
    from .path_context import build_condition_fact
    facts = []
    for f in (raw or []):
        if isinstance(f, dict):
            facts.append(build_condition_fact(**dict(f)))
        else:
            raise PPV1RunError(
                "plan.condition_facts 的条目必须是 dict(build_condition_"
                "fact 契约)", {"kind": "plan_fact_invalid"})
    return facts


def _substrate_state(smiles: str, label: str):
    """底物状态重建(工厂同源:同 SMILES 同 state_id;首消费守卫在
    工厂/公共 writer)。"""
    return build_chemical_state(smiles, "raw_input",
                                 [{"record": label}])


def _worker_id(run_id: str) -> str:
    """确定性 worker 身份(同 run 的 resume 以同一逻辑 worker 幂等
    reclaim —— B1 续跑;跨进程竞争方被驱动会话互斥挡在执行前)。"""
    return f"ppv1-driver:{run_id}"


def _task_key_for(*, run_id: str, parent_path_id: str, context_ref: str,
                  subject_ref: str, kind: str, revision: int,
                  policy_version: str, extra: str = "") -> str:
    return stable_id("stkey", run_id, parent_path_id, context_ref,
                     subject_ref, kind, str(int(revision)),
                     policy_version, extra)


def _complete_action(ledger: SearchLedger, action_id: str, *,
                     worker_id: str, outcome: dict,
                     evidence_refs: list[str] | None = None) -> dict:
    """非事件完成:outcome artifact 先写 + complete_action(outcome 类;
    S3A-02 完整权威核验)。返回 outcome_ref。"""
    payload = {"outcome_version": "ppv1-runflow-outcome-1",
               "action_id": action_id, "outcome": dict(outcome),
               "evidence_refs": [str(r) for r in (evidence_refs or [])]}
    task_key = stable_id("soutc", action_id)
    outcome_ref = content_hash(payload)
    if ledger.artifact_store is not None:
        ledger.artifact_store.write(task_key, "expansion_outcome", payload)
    return ledger.complete_action(
        action_id, worker_id=worker_id, outcome_kind=COMMIT_KIND_OUTCOME,
        outcome_ref=outcome_ref)


# ------------------------------------------------------- S3B-01 冻结计划输入


def _persist_frozen_plan(artifact_store, plan: dict) -> dict:
    """S3B-01:start 时把计划持久化为**冻结输入来源**(artifact 内容
    身份绑定;plan_digest 全量哈希)。驱动循环此后只消费冻结来源。"""
    if artifact_store is None:
        raise PPV1RunError(
            "持久化冻结计划需要 artifact_store", {"kind": "artifact_store_missing"})
    payload = {"plan_version": FROZEN_PLAN_VERSION,
               "plan": plan or {},
               "plan_digest": _plan_digest(plan)}
    artifact_store.write(FROZEN_PLAN_TASK_KEY, FROZEN_PLAN_ARTIFACT, payload)
    return payload


def _load_frozen_plan(artifact_store) -> dict:
    """S3B-01:resume 加载冻结计划输入(H07 完整性包装 + 内容身份
    核验;缺/坏 ⇒ 结构化拒绝 —— 缺输入不能当空池合法完成,不猜)。"""
    if artifact_store is None:
        raise PPV1RunError(
            "读取冻结计划需要 artifact_store", {"kind": "artifact_store_missing"})
    try:
        envelope = read_search_artifact(
            artifact_store, FROZEN_PLAN_TASK_KEY, FROZEN_PLAN_ARTIFACT)
    except SearchArtifactIntegrityError as exc:
        raise PPV1RunError(
            "冻结计划输入完整性失败(保全原文件;不静默跳过、不覆盖)"
            f":{exc}", {"kind": "frozen_plan_integrity_failure",
                        "artifact_kind": exc.detail.get("kind")}) from exc
    if envelope is None:
        raise PPV1RunError(
            "冻结计划输入缺失(计划在 start 时持久化;缺输入不能当空池"
            "合法完成,不猜)", {"kind": "frozen_plan_missing"})
    payload = envelope.get("payload") or {}
    plan = payload.get("plan")
    digest = str(payload.get("plan_digest") or "")
    if not isinstance(plan, dict) or not digest:
        raise PPV1RunError(
            "冻结计划载荷损坏(缺 plan/plan_digest;fail-closed,不猜)",
            {"kind": "frozen_plan_corrupt"})
    if content_hash(plan) != digest:
        raise PPV1RunError(
            "冻结计划内容与摘要不符(内容身份核验失败;保全失败)",
            {"kind": "frozen_plan_digest_mismatch"})
    return plan


def _verify_frozen_plan_binding(ledger: SearchLedger, run_id: str,
                                frozen_plan: dict) -> dict:
    """S3B-01 后段锚定(S3b r3):resume 首消费前,把读取的冻结计划
    与**独立既存权威**核对 —— start 时落账的根 retrieve 行。

    - 独立权威是 DB 通道的 search_actions 行(payload.plan_digest;
      task_key 由 start 侧同一 `decision_task_key` 单一来源派生并冻结
      落账),与 artifact 文件相互独立 —— **artifact 内自算的
      payload_hash/plan_digest 是自洽证书,不能单独证明"仍是该
      run/root/task 的原输入"**;
    - 覆盖 root retrieve 已 done 的 B3/B4:retrieve 执行层的
      plan_digest 同源核验(`_run_retrieve`)只在 retrieve 实际执行
      时到达,后段不可达 —— 本核对在入口闭合,不依赖旧 retrieve
      是否还会执行;
    - 逐锚两查(单一来源派生,不另造第二套规则):
      ① 锚行自身同源:按行内冻结字段 + 行内 plan_digest 重算
      decision_task_key,与行内冻结 task_key(列与载荷)比对 ——
      不符 ⇒ 坏锚(frozen_plan_anchor_corrupt)先拒;
      ② 锚摘要与当前读取的冻结计划摘要比对 —— 不符 ⇒
      frozen_plan_binding_mismatch(旧任务不消费新输入;差异须显式
      新 revision/新任务登记);
    - 无任何携带 plan_digest 的 retrieve 行(载荷不可解析视同坏锚,
      因无法证明其未携带锚)⇒ frozen_plan_anchor_missing 先拒;
    - 本核对发生在 recover_run(B4 补账/B3 bundle 消费)/驱动调度/
      事件提交/预算 consume **之前**:任何锚缺失/损坏/不符 ⇒ 结构
      化拒,业务表/event/commit/consume 零新增,原资料(artifact/
      DB 行)保全;
    - 不提供密码学签名服务、不抵抗全库协同改写(复审 §4 明示超出
      范围);为符合既有身份规范的最小实现。
    """
    rows = ledger.conn.execute(
        "SELECT action_id, status, parent_path_id, context_ref,"
        " subject_ref, parent_search_revision, policy_version, payload,"
        " task_key FROM search_actions WHERE run_id = ? AND"
        " action_kind = ? ORDER BY created_at, action_id",
        (run_id, ACTION_KIND_RETRIEVE)).fetchall()
    anchors: list[dict] = []
    for row in rows:
        action_id = str(row["action_id"])
        try:
            payload = json.loads(row["payload"] or "{}")
        except (ValueError, TypeError) as exc:
            raise PPV1RunError(
                f"冻结计划锚行 {action_id} 载荷不可解析(坏锚先拒;"
                "无法证明其未携带原绑定;不猜修)",
                {"kind": "frozen_plan_anchor_corrupt",
                 "action_id": action_id, "run_id": run_id,
                 "reason": str(exc)[:200]}) from exc
        if not isinstance(payload, dict):
            raise PPV1RunError(
                f"冻结计划锚行 {action_id} 载荷非 dict(坏锚先拒;"
                "不猜修)",
                {"kind": "frozen_plan_anchor_corrupt",
                 "action_id": action_id, "run_id": run_id})
        anchor_digest = str(payload.get("plan_digest") or "")
        if not anchor_digest:
            continue  # 非锚行(followup retrieve 不绑定计划摘要)
        # ① 锚行自身同源:行内 plan_digest + 行内冻结身份字段 →
        # 单一来源 decision_task_key 重算,与落账 task_key 比对
        expected_task_key = decision_task_key(
            run_id=run_id, parent_path_id=str(row["parent_path_id"]),
            context_ref=str(row["context_ref"]),
            frozen_pool_digest=anchor_digest,
            parent_search_revision=int(row["parent_search_revision"]),
            policy_version=str(row["policy_version"]),
            strict_state_digest=str(row["subject_ref"]),
            tool_id="atom-tool-vendored",
            prompt_version=anchor_digest[:16],
            feedback_policy_version=FORMAT_FEEDBACK_POLICY_VERSION)
        stored_task_keys = {str(row["task_key"] or ""),
                            str(payload.get("task_key") or "")}
        if stored_task_keys != {expected_task_key}:
            raise PPV1RunError(
                f"冻结计划锚行 {action_id} 坏锚(行内 task_key 与按"
                "单一来源 decision_task_key 重算不一致 —— 锚行自身"
                "不再同源;先结构化拒,零补账,原行保全)",
                {"kind": "frozen_plan_anchor_corrupt",
                 "action_id": action_id, "run_id": run_id,
                 "anchor_plan_digest": anchor_digest,
                 "expected_task_key": expected_task_key,
                 "stored_task_keys": sorted(stored_task_keys)})
        anchors.append({"action_id": action_id,
                        "status": str(row["status"]),
                        "plan_digest": anchor_digest,
                        "task_key": expected_task_key})
    if not anchors:
        raise PPV1RunError(
            f"run {run_id} 缺冻结计划锚(无携带 plan_digest 的"
            " retrieve 行;缺锚先拒 —— 不能以无锚状态继续消费任何"
            "冻结输入;零补账,原资料保全)",
            {"kind": "frozen_plan_anchor_missing", "run_id": run_id,
             "note": "根 retrieve 在 start 时落账 plan_digest/task_key;"
                     "锚缺失意味着权威记录被移除或从未落账"})
    frozen_digest = _plan_digest(frozen_plan)
    # ② 锚摘要与当前读取的冻结计划摘要比对(每锚都核,任一不符即拒)
    for anchor in anchors:
        if anchor["plan_digest"] != frozen_digest:
            raise PPV1RunError(
                "冻结计划与既存 run/root/task 原绑定不符(读取的计划"
                "摘要 ≠ start 落账的根任务锚摘要 —— 自洽重封装不是"
                "原输入证书;旧任务不消费新输入,差异须显式新 revision/"
                "新任务登记;先结构化拒,零 event/补账/新调度/consume,"
                "原资料保全)",
                {"kind": "frozen_plan_binding_mismatch",
                 "run_id": run_id,
                 "anchor_action_id": anchor["action_id"],
                 "anchor_status": anchor["status"],
                 "anchor_plan_digest": anchor["plan_digest"],
                 "frozen_plan_digest": frozen_digest})
    return {"anchor_action_ids": [a["action_id"] for a in anchors],
            "anchor_statuses": [a["status"] for a in anchors],
            "anchor_plan_digest": anchors[0]["plan_digest"],
            "frozen_plan_digest": frozen_digest,
            "task_key_verified": True,
            "note": ("后段锚定:root retrieve 已 done(B3/B4)时执行层"
                     "核验不可达,本核对在 resume 首消费前闭合")}


# ------------------------------------------------------- S3B-04 执行会话互斥


class _DriverSession:
    """公开 start/resume 的**执行会话互斥**(S3B-04;run 目录
    driver.lock 的 flock LOCK_EX|LOCK_NB)。

    - 双进程同时驱动同一 run:一方取得执行权,另一方在**任何恢复/
      认领/请求/工具执行之前**结构化拒绝(driver_session_active,
      竞争方可复用:等持有方退出后再次 resume 即幂等复用完成结果);
    - 崩溃(进程死亡)⇒ OS 自动释放 flock ⇒ 新进程接管(原 attempt/
      预约/claim 行原样保留,B1 同 worker 幂等 reclaim 续跑;不永久
      锁死崩溃任务);
    - 锁文件内容记录持有者 pid/时间(披露用;**flock 是权威**,
      文件内容不作判据);同机文件锁语义,不宣称分布式锁或外部
      provider exactly-once;
    - 正常完成/异常退出都释放(try/finally;进程死亡由 OS 释放)。
    """

    def __init__(self, run_dir: Path):
        self.path = Path(run_dir) / "driver.lock"
        self.fh = None
        self.info: dict = {}

    def __enter__(self) -> "_DriverSession":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = open(self.path, "a+", encoding="utf-8")
        try:
            fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            holder: dict = {}
            try:
                holder = json.loads(
                    self.path.read_text(encoding="utf-8") or "{}")
            except (ValueError, OSError):
                holder = {}
            self.fh.close()
            self.fh = None
            raise PPV1RunError(
                "run 已有活动驱动会话(执行会话互斥:竞争方在任何恢复"
                "/认领/请求/工具执行前返回;不创建新 attempt/event、不"
                "重复扣额;崩溃由 OS 释放,新进程可接管)",
                {"kind": "driver_session_active", "holder": holder,
                 "pid": os.getpid()}) from exc
        self.info = {"pid": os.getpid(), "acquired_at": now_iso(),
                     "note": "flock 是执行权权威;崩溃 OS 自动释放"}
        try:
            self.fh.seek(0)
            self.fh.truncate()
            self.fh.write(json.dumps(self.info, ensure_ascii=False))
            self.fh.flush()
        except OSError:
            pass  # 披露信息写失败不影响执行权(flock 已持有)
        return self

    def __exit__(self, *exc) -> bool:
        if self.fh is not None:
            try:
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            finally:
                self.fh.close()
                self.fh = None
        return False


def _isolated_recovery_actions(recovery: dict) -> list[dict]:
    """S3B-02:从恢复报告提取坏 artifact/缺权威的失败处置(disposition
    为携带 error 的 dict);这些 action 须被隔离,不以 claimed 旧收据
    授权重执行。"""
    out = []
    for entry in (recovery or {}).get("actions") or []:
        disp = entry.get("disposition")
        if isinstance(disp, dict) and disp.get("error"):
            out.append({"action_id": entry.get("action_id"),
                        "action_kind": entry.get("action_kind"),
                        "boundary": entry.get("boundary"),
                        "failure": dict(disp)})
    return out


class _Driver:
    """一次驱动会话(进程内;恢复后新实例从持久记录继续;消费冻结
    计划输入)。"""

    def __init__(self, ledger: SearchLedger, plan: dict, run_id: str,
                 worker_id: str, crash_after: str | None = None) -> None:
        self.ledger = ledger
        self.store = ledger.store
        self.plan = plan or {}
        self.run_id = run_id
        self.worker_id = worker_id
        self.crash_after = crash_after
        self.refusals: list[dict] = []
        self.run_error: dict | None = None
        self.empty_pool_retrievals = 0
        self.total_retrievals = 0
        self.events_submitted: list[str] = []
        self.root_path_id = stable_id("spath", run_id, "root")
        self.model_responses = list(
            (self.plan.get("model") or {}).get("responses") or [])
        self.model_provider_kind = str(
            (self.plan.get("model") or {}).get("provider_kind")
            or PROVIDER_KIND_SCRIPTED)

    # ------------------------------------------------------------ 主循环

    def reconcile_followups(self) -> None:
        """B4 补调度(S3b r2/S3B-03):事件已提交、后续调度未完成 ⇒
        从**权威记录**(提交记录的 event_id → 事件行 + 展开计划附件)
        与**冻结计划的显式转换意图**(scenario_transitions 按该 expand
        的 hypothesis_key 匹配)派生期望后续集合,逐对象幂等补齐。

        - 不再以"payload LIKE 引用计数 > 1"当完整性证书:期望集合 =
          事件参与物产物 state_ref 全集 × 展开计划(expanded ⇒ pending
          retrieve / deferred ⇒ deferred retrieve / not_tracked ⇒ 无);
        - 计划带转换 ⇒ 补齐/复用携带 pending_followup 的转换 action
          (转换执行后以新上下文调度 followup —— 只后效;旧边评估不动);
          覆盖事件提交后转换未入队(B4)、转换已入队(载荷一次冻结)
          两窗口;
        - 无转换 ⇒ enqueue_coproduct_followups 幂等补齐全部产物
          (0/部分/全部 followup 逐对象闭合;同键同内容 unchanged,
          不重发事件、不重复扣额);
        - 事件权威不重放(submit 幂等键);损坏权威由 store/recover
        侧先行拒绝,本层不猜补。
        """
        rows = self.ledger.conn.execute(
            "SELECT a.action_id, a.parent_path_id, a.context_ref,"
            " a.parent_search_revision, a.policy_version, a.payload,"
            " c.event_id FROM search_actions a JOIN search_commit_records"
            " c ON c.action_id = a.action_id WHERE a.run_id = ? AND"
            " a.action_kind = ? AND a.status = ? AND c.event_id != ''",
            (self.run_id, ACTION_KIND_EXPAND_HYPOTHESIS,
             "done")).fetchall()
        for row in rows:
            event_id = row["event_id"]
            payload = json.loads(row["payload"]) or {}
            plan_transition = self._match_transition(payload)
            if plan_transition is not None:
                self._ensure_transition_followup(row, event_id, payload,
                                                 plan_transition)
                continue
            plan_doc = self.store.expansion_plan(event_id)
            ev = self.store.get_event(event_id)
            if not plan_doc or not ev:
                continue
            ev_payload = ev.get("payload")
            participants = (json.loads(ev_payload).get("participants")
                            if isinstance(ev_payload, str) and ev_payload
                            else ev.get("participants")) or []
            product_refs = [
                str(p.get("state_ref")) for p in participants
                if isinstance(p, dict) and p.get("side") == "product"]
            smiles_by_ref = {ref: self._state_smiles(ref)
                             for ref in product_refs}
            enqueue_coproduct_followups(
                self.ledger, run_id=self.run_id,
                parent_path_id=row["parent_path_id"],
                context_ref=row["context_ref"], event_id=event_id,
                product_state_refs=product_refs,
                expansion_plan=dict(plan_doc),
                policy_version=row["policy_version"],
                parent_search_revision=int(
                    row["parent_search_revision"]) + 1,
                substrate_smiles_by_ref=smiles_by_ref,
                depth=int(payload.get("depth") or 1))

    def _transition_followup_payload(
            self, *, event_id: str, expansion_plan: dict,
            product_state_refs: list[str], parent_path_id: str,
            context_ref: str, revision: int, depth: int) -> dict:
        """转换 action 的 pending_followup 冻结载荷(**单一构建源**:
        _run_expand 的事件后入队与 B4 reconcile 的补齐共用 —— 同输入
        同字节,幂等闭环)。"""
        return {
            "event_id": event_id,
            "expansion_plan": dict(expansion_plan),
            "product_state_refs": list(product_state_refs),
            "parent_path_id": parent_path_id,
            "context_ref": context_ref,
            "parent_search_revision": int(revision),
            "depth": int(depth),
        }

    def _ensure_transition_followup(self, row, event_id: str,
                                     payload: dict,
                                     plan_transition: dict) -> None:
        """B4/转换窗口:确保携带 pending_followup 的转换 action 存在
        (幂等 enqueue;同键同内容 unchanged)。转换执行后按新上下文
        调度 followup;不重写旧边评估。"""
        parent_path_id = row["parent_path_id"]
        revision = int(row["parent_search_revision"]) + 1
        ev = self.store.get_event(event_id)
        if not ev:
            return
        ev_payload = ev.get("payload")
        participants = (json.loads(ev_payload).get("participants")
                        if isinstance(ev_payload, str) and ev_payload
                        else ev.get("participants")) or []
        product_refs = [
            str(p.get("state_ref")) for p in participants
            if isinstance(p, dict) and p.get("side") == "product"]
        plan_doc = dict(self.store.expansion_plan(event_id) or {})
        pending_followup = self._transition_followup_payload(
            event_id=event_id, expansion_plan=plan_doc,
            product_state_refs=product_refs,
            parent_path_id=parent_path_id,
            context_ref=row["context_ref"], revision=revision,
            depth=int(payload.get("depth") or 1))
        enqueue_scenario_transition(
            self.ledger, run_id=self.run_id,
            parent_path_id=parent_path_id,
            context_ref=row["context_ref"],
            transition=dict(plan_transition),
            policy_version=row["policy_version"],
            parent_search_revision=revision,
            task_key=_task_key_for(
                run_id=self.run_id, parent_path_id=parent_path_id,
                context_ref=row["context_ref"], subject_ref=event_id,
                kind="scenario_transition", revision=revision,
                policy_version=row["policy_version"],
                extra=content_hash(plan_transition)),
            pending_followup=pending_followup)

    def _inflight_action_ids(self) -> list[str]:
        """在途 action(pending + 本 worker 已认领未完成 —— B1 续跑:
        同 worker 幂等 reclaim 后继续执行;其他 worker 认领的 action
        不在驱动清单内,由其执行方续跑;blocked(含恢复隔离)不执行)。
        稳定次序:created_at, action_id。"""
        rows = self.ledger.conn.execute(
            "SELECT action_id FROM search_actions WHERE run_id = ? AND"
            " (status = ? OR (status = ? AND claimed_by = ?))"
            " ORDER BY created_at, action_id",
            (self.run_id, "pending", "claimed", self.worker_id)).fetchall()
        return [str(r["action_id"]) for r in rows]

    def drive(self) -> dict:
        self.reconcile_followups()
        activations_applied = False
        while True:
            pending = self._inflight_action_ids()
            if not pending:
                directives = self.plan.get("activations") or []
                if not activations_applied and directives:
                    # 显式激活指令(计划输入):入队 activate_deferred
                    # action(幂等:done 的指令 action 复用;不重复安排)
                    activations_applied = True
                    for directive in directives:
                        self._enqueue_activation(directive)
                    continue
                break
            action_id = pending[0]
            try:
                receipt = self.ledger.claim_action(
                    action_id, worker_id=self.worker_id)
            except SearchBudgetExhausted as exc:
                self.refusals.append({
                    "reason": "budget_limit",
                    "limit_key": exc.detail.get("limit_key"),
                    "action_id": action_id,
                    "kind": exc.detail.get("kind")})
                break  # 预算拒:停止驱动(stop_report 报主因)
            except (SearchClaimError, SearchConcurrencyError) as exc:
                # already_claimed(并发)/锁:停止,结构化披露(SQLite
                # busy 是可见并发结果,不当化学拒绝)
                self.refusals.append({
                    "reason": "claim_error", "action_id": action_id,
                    "kind": exc.detail.get("kind")})
                break
            if self.crash_after == "after_claim":
                raise SearchCrashInjection(
                    "认领已落账、执行未开始(B1 注入点)",
                    {"action_id": action_id})
            if not receipt.get("claimed") and \
                    receipt.get("status") == "done":
                continue  # done 复用(权威核验已在 claim 内)
            kind = receipt["action_kind"]
            try:
                if kind == ACTION_KIND_RETRIEVE:
                    self._run_retrieve(receipt)
                elif kind == ACTION_KIND_DECIDE:
                    self._run_decide(receipt)
                elif kind == ACTION_KIND_EXPAND_HYPOTHESIS:
                    self._run_expand(receipt)
                elif kind == ACTION_KIND_ACTIVATE_DEFERRED:
                    self._run_activate(receipt)
                elif kind == ACTION_KIND_SCENARIO_TRANSITION:
                    self._run_transition(receipt)
                else:
                    raise PPV1RunError(
                        f"未知 action_kind:{kind!r}(驱动分发缺实现)",
                        {"kind": "unknown_action_kind",
                         "action_kind": kind})
            except SearchCrashInjection:
                raise  # 崩溃注入点不是 run 错误:原样上抛(测试边界)
            except (PPV1RunError, ModelProtocolError,
                    SearchContractError) as exc:
                # 模型结构失败/调度契约失败(如转换缺 source_ref)等
                # run 级错误:如实停止(不吞、不猜;claimed action 保持
                # 认领态计入未完成,不称 exhausted_search;错误进报告)
                self.run_error = {
                    "error": type(exc).__name__,
                    "kind": exc.detail.get("kind"),
                    "message": str(exc)[:300]}
                break
        return self._stop_report()

    # ------------------------------------------------------------ retrieve

    def _run_retrieve(self, receipt: dict) -> None:
        payload = receipt["payload"]
        substrate_smiles = str(payload.get("substrate_smiles") or "")
        source_event_id = str(payload.get("source_event_id") or "")
        substrate_depth = int(payload.get("depth") or 0)
        # ---- S3B-01:任务输入绑定的计划摘要与当前冻结输入同源核验 ----
        frozen_plan_digest = str(payload.get("plan_digest") or "")
        if frozen_plan_digest and \
                frozen_plan_digest != _plan_digest(self.plan):
            raise PPV1RunError(
                "retrieve 任务输入绑定的计划摘要与当前冻结输入不一致"
                "(旧任务不消费新输入;差异须显式新 revision/新任务)",
                {"kind": "plan_digest_mismatch",
                 "task_plan_digest": frozen_plan_digest,
                 "frozen_plan_digest": _plan_digest(self.plan),
                 "action_id": receipt["action_id"]})
        specs = self._pool_for(substrate_smiles)
        self.total_retrievals += 1
        if not specs and not self.plan.get("model"):
            self.empty_pool_retrievals += 1
            # E01:首选下游无候选 ⇒ 记 unresolved_continuation(不改
            # 上游真假;上游事件/attempt 保留)
            _complete_action(
                self.ledger, receipt["action_id"], worker_id=self.worker_id,
                outcome={"kind": OUTCOME_KIND_NO_LOCAL_CANDIDATE,
                         "detail": {
                             "substrate_smiles": substrate_smiles,
                             "source_event_id": source_event_id,
                             "unresolved_continuation": bool(source_event_id),
                             "note": ("检索/池无候选;不反证上游;按稳定"
                                      "次序继续可用备选")}},
                evidence_refs=[source_event_id] if source_event_id else [])
            return
        # 空池但计划带模型(S3B-05):仍进 decide —— 空池可组装底物档案
        # 并消费模型响应(novel 池外提案/合法弃权);有效候选集为空时
        # 由 decide 如实落 no_local_candidate。
        digest = content_hash({"specs": specs})
        task_key = decision_task_key(
            run_id=self.run_id, parent_path_id=receipt["parent_path_id"],
            context_ref=receipt["context_ref"],
            frozen_pool_digest=digest,
            parent_search_revision=int(
                receipt["parent_search_revision"]),
            policy_version=receipt["policy_version"],
            strict_state_digest=stable_id("sfeat", substrate_smiles),
            tool_id="atom-tool-vendored",
            prompt_version=_plan_digest(self.plan)[:16],
            feedback_policy_version=FORMAT_FEEDBACK_POLICY_VERSION)
        self.ledger.enqueue_action(
            run_id=self.run_id, parent_path_id=receipt["parent_path_id"],
            context_ref=receipt["context_ref"],
            subject_ref=f"pool:{digest[:16]}",
            action_kind=ACTION_KIND_DECIDE,
            parent_search_revision=receipt["parent_search_revision"],
            policy_version=receipt["policy_version"],
            payload={"task_key": task_key, "pool_digest": digest,
                     "substrate_smiles": substrate_smiles,
                     "context_ref": receipt["context_ref"],
                     "parent_path_id": receipt["parent_path_id"],
                     "depth": substrate_depth,
                     "source_event_id": source_event_id})
        _complete_action(
            self.ledger, receipt["action_id"], worker_id=self.worker_id,
            outcome={"kind": OUTCOME_KIND_POOL_DIGEST,
                     "detail": {"substrate_smiles": substrate_smiles,
                                "pool_digest": digest,
                                "pool_size": len(specs)}})

    def _pool_for(self, substrate_smiles: str) -> list[dict]:
        pools = self.plan.get("pools") or {}
        if not isinstance(pools, dict):
            raise PPV1RunError("plan.pools 必须是 dict",
                               {"kind": "plan_pools_invalid"})
        specs = pools.get(substrate_smiles) or []
        if not isinstance(specs, list):
            raise PPV1RunError(
                f"plan.pools[{substrate_smiles!r}] 必须是 list",
                {"kind": "plan_pool_specs_invalid"})
        return specs

    # ------------------------------------------------------------ decide

    def _run_decide(self, receipt: dict) -> None:
        payload = receipt["payload"]
        substrate_smiles = str(payload.get("substrate_smiles") or "")
        substrate_depth = int(payload.get("depth") or 0)
        specs = self._pool_for(substrate_smiles)
        # ---- S3B-01:decide 已冻结的池摘要同源核验(retrieve 落账的
        # pool_digest 与当前冻结输入重取的 specs 重算不一致 ⇒ 拒,
        # 不以旧任务键消费新池) ----
        frozen_pool_digest = str(payload.get("pool_digest") or "")
        current_specs_digest = content_hash({"specs": specs})
        if frozen_pool_digest and \
                frozen_pool_digest != current_specs_digest:
            raise PPV1RunError(
                "decide 已冻结的池摘要与当前冻结输入重取的池不一致"
                "(旧任务不消费新输入;差异须显式新 revision/新任务)",
                {"kind": "pool_digest_mismatch",
                 "frozen_pool_digest": frozen_pool_digest,
                 "current_specs_digest": current_specs_digest,
                 "action_id": receipt["action_id"]})
        substrate = _substrate_state(substrate_smiles,
                                     f"ppv1-substrate:{self.run_id}")
        parent_ctx = load_context(self.ledger.artifact_store,
                                  receipt["context_ref"])
        # ---- S3B-05:底物档案独立于候选(空池仍组装;持久 artifact
        # 供审计;S2 已交付的只读构造,不接触模型/策略) ----
        substrate_profile = build_substrate_profile(substrate, parent_ctx)
        if self.ledger.artifact_store is not None and \
                str(receipt.get("task_key") or ""):
            self.ledger.artifact_store.write(
                str(receipt["task_key"]), "substrate_profile",
                substrate_profile.to_dict())
        prepared_entries = []
        for index, spec in enumerate(specs):
            key = str(spec.get("key") or f"spec-{index}")
            prepared = prepare_hypothesis(
                spec, parent_path_id=receipt["parent_path_id"],
                substrate_state=substrate,
                transformation_ref=str(spec.get("transformation_ref")
                                        or ""))
            prepared_entries.append((key, spec, prepared))
        model_note: dict = {}
        if self.plan.get("model"):
            try:
                model_note = self._model_proposals(receipt, prepared_entries)
            except SearchBudgetExhausted as exc:
                # 真实 provider 额度 0(默认):登记被拒 ⇒ 网络发送被
                # 阻止;decide 记方法失败,搜索按预算原因停止 ——
                # **不因传 model 对象补/派生真实请求预算**
                self.refusals.append({
                    "reason": "budget_limit",
                    "limit_key": exc.detail.get("limit_key"),
                    "action_id": receipt["action_id"],
                    "kind": exc.detail.get("kind")})
                _complete_action(
                    self.ledger, receipt["action_id"],
                    worker_id=self.worker_id,
                    outcome={"kind": OUTCOME_KIND_METHOD_FAILED,
                             "detail": {"error": "real_request_refused",
                                        "note": ("真实模型请求额度不足,"
                                                 "网络发送被阻止;传入"
                                                 "模型对象不自动补预算")}})
                return
        # ---- S3B-05:novel 池外提案的独立假设消费(经 prepare_
        # hypothesis 单一构建源:结构身份/参与物/系数/共同产物/条件/
        # 依赖沿既有契约;来源经 proposal_context 明示入冻结任务
        # 输入;无足够内容在解析/构造侧结构化拒,不伪造) ----
        novel_by_key: dict[str, dict] = {}
        for proposal in (model_note.get("novel_proposals") or []):
            reaction_spec = dict(proposal["reaction_spec"])
            novel_key = str(proposal.get("hypothesis_id") or "")
            origin = str((proposal.get("proposal_context") or {}).get(
                "output_origin") or "novel_outside_pool")
            prepared = prepare_hypothesis(
                reaction_spec,
                parent_path_id=receipt["parent_path_id"],
                substrate_state=substrate,
                transformation_ref=str(
                    reaction_spec.get("transformation_ref") or ""),
                source_refs=[{"record": f"novel-model-proposal:{origin}"}])
            prepared_entries.append((novel_key, reaction_spec, prepared))
            novel_by_key[novel_key] = proposal
        if not prepared_entries:
            # 有效候选集为空(池空且模型弃权/无 novel):no_local_
            # candidate 如实落账(不改上游真假)
            self.empty_pool_retrievals += 1
            source_event_id = str(payload.get("source_event_id") or "")
            _complete_action(
                self.ledger, receipt["action_id"],
                worker_id=self.worker_id,
                outcome={"kind": OUTCOME_KIND_NO_LOCAL_CANDIDATE,
                         "detail": {
                             "substrate_smiles": substrate_smiles,
                             "source_event_id": source_event_id,
                             "unresolved_continuation": bool(source_event_id),
                             "note": ("检索/池与模型提案均无候选;不反证"
                                      "上游;按稳定次序继续可用备选")}},
                evidence_refs=[source_event_id] if source_event_id else [])
            return
        rank_by_key = model_note.get("rank_by_key") or {}
        entries: list[dict] = []
        expand_depth = substrate_depth + 1
        for index, (key, spec, prepared) in enumerate(prepared_entries):
            hypothesis = prepared["hypothesis"]
            context_ref = receipt["context_ref"]
            # 分支隔离:带自身要求/依赖的假设派生专属子上下文
            # (derive_child_context 拷贝父事实;分支互不污染)
            if spec.get("requirements") or spec.get("dependencies") \
                    or spec.get("assumptions"):
                child_ctx = self._derive_branch_context(
                    parent_ctx, prepared, hypothesis.hypothesis_id)
                context_ref = persist_context(
                    self.ledger.artifact_store, child_ctx)
            rank = int(rank_by_key.get(key, index + 1))
            task_key = expansion_task_key(
                run_id=self.run_id,
                parent_path_id=receipt["parent_path_id"],
                context_ref=context_ref,
                hypothesis_id=hypothesis.hypothesis_id, attempt_id="",
                policy_version=receipt["policy_version"],
                strict_state_digest=substrate.state_id,
                tool_id="atom-tool-vendored",
                prompt_version=_plan_digest(self.plan)[:16],
                feedback_policy_version=FORMAT_FEEDBACK_POLICY_VERSION)
            entry_payload = {
                "task_key": task_key,
                "spec": dict(spec),
                "hypothesis_key": key,
                "substrate_smiles": substrate_smiles,
                "substrate_state_ref": substrate.state_id,
                "context_ref": context_ref,
                "parent_path_id": receipt["parent_path_id"],
                "depth": expand_depth,
                "source_event_id": str(
                    payload.get("source_event_id") or ""),
            }
            if key in novel_by_key:
                entry_payload["proposal_context"] = dict(
                    novel_by_key[key].get("proposal_context") or {})
            entries.append({
                "hypothesis_key": key,
                "hypothesis_id": hypothesis.hypothesis_id,
                "rank": rank,
                "payload": entry_payload,
            })
        schedule = schedule_hypotheses(
            self.ledger, run_id=self.run_id,
            parent_path_id=receipt["parent_path_id"],
            context_ref=receipt["context_ref"],
            parent_search_revision=int(
                receipt["parent_search_revision"]),
            pool=entries, policy_version=receipt["policy_version"],
            depth=expand_depth,
            source_event_id=str(payload.get("source_event_id") or ""),
            budget=self.plan.get("schedule_budget"))
        _complete_action(
            self.ledger, receipt["action_id"], worker_id=self.worker_id,
            outcome={"kind": OUTCOME_KIND_SCHEDULED,
                     "detail": {"pool_digest": schedule["pool_digest"],
                                "selected": len(schedule["selected"]),
                                "deferred": len(schedule["deferred"]),
                                "blocked": len(schedule["blocked"]),
                                "model": {
                                    k: v for k, v in model_note.items()
                                    if k != "rank_by_key"}}})

    def _derive_branch_context(self, parent_ctx, prepared: dict,
                               hypothesis_id: str):
        from .path_context import build_requirement
        step_requirements = []
        for raw in (prepared["hypothesis"].requirements or []):
            if isinstance(raw, dict):
                fields = {k: v for k, v in dict(raw).items()
                          if k in ("key", "level", "value", "basis",
                                   "value_basis", "source_refs",
                                   "applicable_dimensions",
                                   "observed_source_conditions", "note")}
                step_requirements.append(
                    build_requirement(**fields))
            else:
                step_requirements.append(raw)
        return derive_child_context(
            parent_ctx,
            step_requirements=None if not step_requirements
            else step_requirements,
            step_dependencies=prepared["dependencies"] or None,
            step_edge_ref=hypothesis_id)

    def _model_proposals(self, receipt: dict,
                         prepared_entries: list) -> dict:
        """scripted 模型 proposals[] 协议(网络 0;真实 provider 默认
        off —— 登记被预算拒绝,网络发送被阻止)。novel 池外提案
        (S3B-05)须携带 reaction_spec 完整反应内容,由调用方构造独立
        假设消费。"""
        action_id = receipt["action_id"]
        attempt_id = (receipt.get("attempt_refs") or [""])[0]
        allowed = {prepared["hypothesis"].hypothesis_id
                   for _, _, prepared in prepared_entries}
        response = self._next_model_response()
        request = self.ledger.register_model_request(
            run_id=self.run_id, action_id=action_id,
            attempt_id=attempt_id, provider_kind=self.model_provider_kind,
            request_key=f"decide:{action_id}", purpose="proposals",
            payload={"response": str(response)[:2000]})
        if self.crash_after == "after_request_registered":
            raise SearchCrashInjection(
                "请求已登记、无响应(B2 注入点)",
                {"action_id": action_id,
                 "request_id": request["request_id"]})
        note: dict = {"request_id": request["request_id"],
                      "provider_kind": self.model_provider_kind,
                      "network_request_count": request.get(
                          "network_request_count", 0)}
        try:
            parsed = parse_model_proposals(
                response, allowed_hypothesis_ids=allowed)
        except ModelProtocolError as exc:
            kind = exc.detail.get("kind")
            if kind in FEEDBACK_ELIGIBLE:
                # 有界格式反馈(默认 0 轮 ⇒ 反馈被预算拒 ⇒ 结构失败
                # 保持;每轮持久记录输入/错误类别/反馈版本/次数)
                try:
                    feedback = register_format_feedback_round(
                        self.ledger, run_id=self.run_id,
                        action_id=action_id, attempt_id=attempt_id,
                        error=exc, response_excerpt=str(response),
                        provider_kind=PROVIDER_KIND_SCRIPTED)
                except SearchBudgetExhausted as feedback_exhausted:
                    # 反馈轮超上限(或策略 0):结构失败保持,不以反馈
                    # 重试到通过 —— 升级为结构失败(不是真实请求预算
                    # 的资源拒绝路径)
                    note["format_feedback_exhausted"] = {
                        "kind": feedback_exhausted.detail.get("kind")}
                    raise PPV1RunError(
                        "模型响应结构失败(格式反馈耗尽或策略 0 轮;"
                        "结构失败保持,不以反馈改分子再试到通过)",
                        {"kind": "model_structure_failure",
                         "error_kind": kind,
                         "feedback_kind":
                             feedback_exhausted.detail.get("kind")})                         from feedback_exhausted
                note["format_feedback_round"] = feedback["request_id"]
                retry = self._next_model_response()
                parsed = parse_model_proposals(
                    retry, allowed_hypothesis_ids=allowed)
            else:
                # structure_unparseable:结构失败保持(不进格式反馈,
                # 不能以反馈改分子再试到通过)
                note["structure_failure"] = {"error_kind": kind}
                raise PPV1RunError(
                    "模型响应结构失败(不可解析;结构失败保持,不进格式"
                    "反馈)", {"kind": "model_structure_failure",
                              "error_kind": kind}) from exc
        # rank 提供稳定次序(模型选择不升成 recorded)
        key_by_id = {prepared["hypothesis"].hypothesis_id: key
                     for key, _, prepared in prepared_entries}
        rank_by_key = {}
        for position, hyp_id in enumerate(parsed["rank_hypotheses"], 1):
            key = key_by_id.get(hyp_id)
            if key is not None:
                rank_by_key[key] = position
        note["parsed_proposals"] = len(parsed["proposals"])
        note["abstained"] = parsed["abstained"]
        note["rank_by_key"] = rank_by_key
        novel = [p for p in parsed["proposals"]
                 if p.get("origin") == "novel"]
        if novel:
            note["novel_proposals"] = novel
        return note

    def _next_model_response(self) -> str:
        if self.model_responses:
            return str(self.model_responses.pop(0))
        # 脚本响应队列耗尽 ⇒ 合法弃权(proposals=[];不猜内容、不
        # 伪造响应;弃权与规则池并行,不强制停止规则搜索)
        return '{"proposals": []}'

    # ------------------------------------------------------------ expand

    def _run_expand(self, receipt: dict) -> None:
        payload = receipt["payload"]
        action_id = receipt["action_id"]
        attempt_id = (receipt.get("attempt_refs") or [""])[0]
        substrate = _substrate_state(
            str(payload.get("substrate_smiles") or ""),
            f"ppv1-substrate:{self.run_id}")
        spec = dict(payload.get("spec") or {})
        prepared = prepare_hypothesis(
            spec, parent_path_id=receipt["parent_path_id"],
            substrate_state=substrate,
            transformation_ref=str(spec.get("transformation_ref") or ""))
        context = load_context(self.ledger.artifact_store,
                               receipt["context_ref"])
        limits = self.ledger._limits(self.run_id)
        write_bundle = self.crash_after == "after_bundle_written"
        try:
            production = expand_hypothesis_production(
                self.ledger, action_id, prepared=prepared, context=context,
                worker_id=self.worker_id, attempt_id=attempt_id,
                task_key=str(payload.get("task_key") or ""),
                substrate_state=substrate, limits=limits,
                depth=int(payload.get("depth") or 1),
                parent_search_revision=int(
                    receipt["parent_search_revision"]),
                write_bundle=write_bundle,
                crash_after=("bundle_written" if write_bundle else
                             ("event_submitted"
                              if self.crash_after == "after_event_submitted"
                              else None)))
        except AuditContractError as exc:
            # **窄捕获(R8 P2 ⑧ 义务)**:契约异常中止本次
            # admission/提交 —— 生产链在提交前上抛 ⇒ 零事件/零提交;
            # 此处只记方法失败并调度独立备选,**不吞成成功**(无事件/
            # 无提交/无 verified 可言;attempt 落 failed)。
            record_expansion_outcome(
                self.ledger, attempt_id,
                outcome={"kind": OUTCOME_KIND_CONTRACT_ABORTED,
                         "detail": {"error": "AuditContractError",
                                    "reason": str(exc)[:300]}},
                evidence_refs=[action_id], worker_id=self.worker_id)
            return
        status = production.get("status")
        if status == "method_failed":
            record_expansion_outcome(
                self.ledger, attempt_id,
                outcome={"kind": OUTCOME_KIND_METHOD_FAILED,
                         "detail": {"execution": {
                             "ok": production["execution"]["execution_ok"],
                             "reasons": production["execution"]["result"]
                             .get("reasons", [])[:5]}}},
                evidence_refs=[action_id], worker_id=self.worker_id)
            return
        if status == "rejected":
            record_expansion_outcome(
                self.ledger, attempt_id,
                outcome={"kind": OUTCOME_KIND_ADMISSION_REJECTED,
                         "detail": {"admission":
                                    production["admission"]}},
                evidence_refs=[action_id], worker_id=self.worker_id)
            return
        if status == "deferred":
            # R3/R4:假设保留(put_hypothesis 留痕;不提交事件;当前
            # 场景不展开,可展示为需不同条件的备选)
            self.store.put_hypothesis(
                prepared["hypothesis"].to_dict())
            record_expansion_outcome(
                self.ledger, attempt_id,
                outcome={"kind": OUTCOME_KIND_ADMISSION_DEFERRED,
                         "detail": {"admission":
                                    production["admission"]}},
                evidence_refs=[action_id], worker_id=self.worker_id)
            return
        # submitted:followup 调度(场景转换优先:转换须先执行,followup
        # 才用新上下文 —— 只改变后续阶段,不重写旧边评估)
        self.events_submitted.append(production["event_id"])
        parent_path_id = receipt["parent_path_id"]
        revision = int(receipt["parent_search_revision"]) + 1
        plan_transition = self._match_transition(payload)
        product_refs = [s.state_id for s in prepared["product_states"]]
        if plan_transition is not None:
            # 转换动作携带 pending followup(**创建时一次冻结入载荷**,
            # S3B-03:无两写窗口;转换执行后由新上下文调度)
            pending_followup = self._transition_followup_payload(
                event_id=production["event_id"],
                expansion_plan=production["expansion_plan"],
                product_state_refs=product_refs,
                parent_path_id=parent_path_id,
                context_ref=receipt["context_ref"],
                revision=revision,
                depth=int(payload.get("depth") or 1))
            enqueue_scenario_transition(
                self.ledger, run_id=self.run_id,
                parent_path_id=parent_path_id,
                context_ref=receipt["context_ref"],
                transition=dict(plan_transition),
                policy_version=receipt["policy_version"],
                parent_search_revision=revision,
                task_key=_task_key_for(
                    run_id=self.run_id, parent_path_id=parent_path_id,
                    context_ref=receipt["context_ref"],
                    subject_ref=production["event_id"],
                    kind="scenario_transition", revision=revision,
                    policy_version=receipt["policy_version"],
                    extra=content_hash(plan_transition)),
                pending_followup=pending_followup)
        else:
            substrate_smiles_by_ref = {
                s.state_id: s.smiles_isomeric
                for s in prepared["product_states"]}
            enqueue_coproduct_followups(
                self.ledger, run_id=self.run_id,
                parent_path_id=parent_path_id,
                context_ref=receipt["context_ref"],
                event_id=production["event_id"],
                product_state_refs=product_refs,
                expansion_plan=production["expansion_plan"],
                policy_version=receipt["policy_version"],
                parent_search_revision=revision,
                substrate_smiles_by_ref=substrate_smiles_by_ref,
                depth=int(payload.get("depth") or 1))

    def _match_transition(self, payload: dict) -> dict | None:
        key = str(payload.get("hypothesis_key") or "")
        for entry in (self.plan.get("scenario_transitions") or []):
            if str(entry.get("after_hypothesis_key") or "") == key:
                return dict(entry.get("transition") or {})
        return None

    # ------------------------------------------------------------ activate

    def _enqueue_activation(self, directive: dict) -> None:
        payload = {
            "task_key": _task_key_for(
                run_id=self.run_id, parent_path_id=self.root_path_id,
                context_ref="", subject_ref=content_hash(directive),
                kind="activate", revision=0,
                policy_version=search_policy_version()),
            "deferred_type": str(directive.get("deferred_type") or ""),
            "trigger": str(directive.get("trigger")
                           or DEFERRED_TRIGGER_EXPLICIT),
            "expected_parent_revision": int(
                directive.get("expected_parent_revision") or 0),
            "parent": str(directive.get("parent") or "root"),
        }
        self.ledger.enqueue_action(
            run_id=self.run_id, parent_path_id=self.root_path_id,
            context_ref=str(directive.get("context_ref") or ""),
            subject_ref=stable_id("sactdef", content_hash(directive)),
            action_kind=ACTION_KIND_ACTIVATE_DEFERRED,
            parent_search_revision=0,
            policy_version=search_policy_version(), payload=payload)

    def _run_activate(self, receipt: dict) -> None:
        payload = receipt["payload"]
        deferred_type = str(payload.get("deferred_type") or "") or None
        trigger = str(payload.get("trigger") or DEFERRED_TRIGGER_EXPLICIT)
        expected_revision = int(payload.get("expected_parent_revision")
                                or 0)
        parent = str(payload.get("parent") or "root")
        parent_path_id = (self.root_path_id if parent == "root"
                          else parent)
        result = activate_deferred(
            self.ledger, run_id=self.run_id, parent_path_id=parent_path_id,
            trigger=trigger, expected_parent_revision=expected_revision,
            deferred_type=deferred_type)
        _complete_action(
            self.ledger, receipt["action_id"], worker_id=self.worker_id,
            outcome={"kind": OUTCOME_KIND_ACTIVATED,
                     "detail": {"activated": result["activated_ids"],
                                "unchanged": len(result["unchanged"]),
                                "conflicts": len(result["conflicts"]),
                                "deferred_type": deferred_type,
                                "trigger": trigger}})

    # ------------------------------------------------------------ transition

    def _run_transition(self, receipt: dict) -> None:
        payload = receipt["payload"]
        transition = dict(payload.get("transition") or {})
        parent_ctx = load_context(self.ledger.artifact_store,
                                  receipt["context_ref"])
        child_ctx = derive_child_context(
            parent_ctx, scenario_transition=transition,
            step_edge_ref=receipt["action_id"])
        context_ref = persist_context(self.ledger.artifact_store, child_ctx)
        pending_followup = payload.get("pending_followup")
        if isinstance(pending_followup, dict) and pending_followup:
            # 转换已执行:followup 用新上下文调度(仅改变后续阶段)
            followup = dict(pending_followup)
            product_refs = list(followup.get("product_state_refs") or [])
            smiles_by_ref = {
                ref: self._state_smiles(ref) for ref in product_refs}
            enqueue_coproduct_followups(
                self.ledger, run_id=self.run_id,
                parent_path_id=str(followup.get("parent_path_id")
                                   or receipt["parent_path_id"]),
                context_ref=context_ref,
                event_id=str(followup.get("event_id") or ""),
                product_state_refs=product_refs,
                expansion_plan=dict(followup.get("expansion_plan") or {}),
                policy_version=receipt["policy_version"],
                parent_search_revision=int(
                    followup.get("parent_search_revision")
                    or receipt["parent_search_revision"]),
                substrate_smiles_by_ref=smiles_by_ref,
                depth=int(followup.get("depth") or 1))
        _complete_action(
            self.ledger, receipt["action_id"], worker_id=self.worker_id,
            outcome={"kind": OUTCOME_KIND_TRANSITION_APPLIED,
                     "detail": {"new_context_ref": context_ref,
                                "new_phase_id": child_ctx.phase_id,
                                "new_scenario_ref": child_ctx.scenario_ref,
                                "source_ref": transition.get("source_ref"),
                                "note": ("仅改变后续阶段;旧边评估冻结"
                                         "于 phase_history,不重写")}},
            evidence_refs=[str(transition.get("source_ref") or "")])

    def _state_smiles(self, state_ref: str) -> str:
        state = self.store.get_state(state_ref)
        if state is None:
            raise PPV1RunError(
                f"产物状态 {state_ref} 不在账本(followup 调度需要产物"
                "结构;不猜)", {"kind": "product_state_missing",
                              "state_ref": state_ref})
        return str(state.get("smiles_isomeric") or "")

    # ------------------------------------------------------------ 停止

    def _stop_report(self) -> dict:
        no_local_candidate = (self.total_retrievals > 0
                              and self.empty_pool_retrievals ==
                              self.total_retrievals)
        report = self.ledger.stop_report(
            self.run_id, refusals=self.refusals,
            no_local_candidate=no_local_candidate)
        report["events_submitted_session"] = list(self.events_submitted)
        report["runflow_version"] = RUNFLOW_VERSION
        if self.run_error is not None:
            report["run_error"] = dict(self.run_error)
        return report


# ---------------------------------------------------------------- 入口


def _strategy_block(limits: dict) -> dict:
    """PPV1 策略块(身份记录用;搜索预算事实源是 search_limits ——
    **不从 model 派生任何真实请求预算**)。"""
    return {
        "max_depth": int(limits["max_search_depth"]),
        "max_expansions": int(limits["max_total_search_actions"]),
        "max_frontier_width": int(limits["max_product_expansion_width"]),
        "max_llm_calls": 0,
        "max_proposals": 0,
    }


def _prediction_block(model) -> dict:
    if model is not None:
        return model.identity_block()
    from ..domain.policy import PREDICTION_POLICY_VERSION
    return {"enabled": False, "provider": "off", "model_id": "",
            "prompt_versions": {}, "policy_version":
            PREDICTION_POLICY_VERSION, "policy": {}}


def start_ppv1_run(
    *,
    config: V43Config,
    runs_root: str | Path,
    run_id: str,
    smiles: str,
    plan: dict | None = None,
    model=None,
    profile_policy: dict | None = None,
    scripted: bool = False,
    crash_after: str | None = None,
) -> dict:
    """PPV1 独立 start(分流目标;不落 legacy 图/存储)。

    - profile 策略装配(build_profile_identity_block:十上限 +
      format_feedback_policy;未知取值 fail-closed);
    - run identity(代码/资产/策略/模型/MoleCode;PPV1 哈希全树)落盘
      后进驱动;重复 run 拒绝;
    - **执行会话互斥(S3B-04)**:run 目录 flock(并发 start 单胜者
      由原子目录创建保证;此后驱动全程持锁,并发 resume 在执行前拒);
    - 严格 root state(工厂守卫)+ 根 context(artifact 持久化)+
      **冻结计划输入持久化(S3B-01:plan_digest 内容绑定)** +
      搜索 run 注册(policy block = profile 块;恢复按同一身份);
    - 根 retrieve 入队(任务输入绑定计划摘要;空池 ⇒ no_local_
      candidate 诚实停止 —— 计划带模型时空池仍进 decide,S3B-05);
    - 驱动循环 + stop_report(停止不是化学终点)。
    """
    runs_root = Path(runs_root)
    run_dir = runs_root / run_id
    if (run_dir / "run_identity.json").is_file():
        from ..workflow.runner import RunAlreadyExists
        raise RunAlreadyExists(run_id, run_dir)
    # 原子独占目录创建:并发 start 同一 run 只有胜者(败者
    # FileExistsError → RunAlreadyExists;不进 store/identity 写入)
    runs_root.mkdir(parents=True, exist_ok=True)
    try:
        run_dir.mkdir()
    except FileExistsError:
        from ..workflow.runner import RunAlreadyExists
        raise RunAlreadyExists(run_id, run_dir) from None
    with _DriverSession(run_dir) as session:
        policy_block = build_profile_identity_block(**(profile_policy or {}))
        limits = policy_block["search_limits"]
        asset_identity = (scripted_asset_identity() if scripted
                          else retrieval_asset_identity(config))
        identity = build_run_identity(
            run_id=run_id, root_smiles=smiles, root_cn=_cn_of(smiles),
            strategy=_strategy_block(limits), asset_identity=asset_identity,
            v3_code_identity=v3_code_identity(config.v3_code_root),
            prediction=_prediction_block(model),
            profile=PROFILE_POLLUTANT_PATHWAY_V1,
            profile_policy=profile_policy or None)
        write_run_identity(runs_root, identity)
        store = PollutantPathwayStore(run_dir / "pollutant.sqlite")
        artifacts = ArtifactStore(runs_root, run_id)
        ledger = SearchLedger(store, artifacts, run_id)
        ledger.register_search_run(run_id, policy_block)
        root_state = _substrate_state(smiles, "ppv1-root-input")
        store.put_state(root_state.to_dict())
        root_ctx = build_path_context(
            condition_facts=_fact_list((plan or {}).get("condition_facts")),
            scenario_ref=str((plan or {}).get("scenario_ref") or ""),
            dependencies=[
                build_cyclic_dependency(dict(d))
                for d in ((plan or {}).get("dependencies") or [])])
        context_ref = persist_context(artifacts, root_ctx)
        # ---- S3B-01:计划持久化为冻结输入来源(此后驱动只消费冻结) ----
        _persist_frozen_plan(artifacts, plan or {})
        driver = _Driver(ledger, plan or {}, run_id, _worker_id(run_id),
                         crash_after=crash_after)
        root_path = driver.root_path_id
        task_key = decision_task_key(
            run_id=run_id, parent_path_id=root_path,
            context_ref=context_ref,
            frozen_pool_digest=_plan_digest(plan or {}),
            parent_search_revision=0, policy_version=search_policy_version(),
            strict_state_digest=root_state.state_id,
            tool_id="atom-tool-vendored",
            prompt_version=_plan_digest(plan or {})[:16],
            feedback_policy_version=FORMAT_FEEDBACK_POLICY_VERSION)
        ledger.enqueue_action(
            run_id=run_id, parent_path_id=root_path,
            context_ref=context_ref, subject_ref=root_state.state_id,
            action_kind=ACTION_KIND_RETRIEVE,
            parent_search_revision=0, policy_version=search_policy_version(),
            payload={"task_key": task_key, "substrate_smiles": smiles,
                     "context_ref": context_ref, "parent_path_id": root_path,
                     "depth": 0, "source_event_id": "",
                     "plan_digest": _plan_digest(plan or {})})
        report = driver.drive()
        summary = _summary(store, run_id, report, resumed=False)
        summary["driver_session"] = dict(session.info)
        return summary


def resume_ppv1_run(
    *,
    config: V43Config,
    runs_root: str | Path,
    run_id: str,
    plan: dict | None = None,
    model=None,
    crash_after: str | None = None,
) -> dict:
    """PPV1 独立 resume(身份核对 → 执行会话互斥 → 冻结输入核对 →
    冻结计划后段锚定 → 四边界恢复 → 坏 artifact 隔离 → 继续驱动)。

    - 保存身份的 profile 必须 PPV1(legacy run 不走本路径;未知
      profile fail-closed);
    - 当前身份逐字段核对(check_resume_identity:代码/资产/策略/
      模型/MoleCode 任一变更拒绝;不原地切换);
    - **执行会话互斥(S3B-04)**:先取 run 目录 flock,失败 ⇒ 结构化
      拒绝(竞争方在任何恢复/认领/请求/工具执行前返回;崩溃 OS 自动
      释放,新进程接管原 attempt/预约);
    - **冻结输入核对(S3B-01)**:加载 start 持久化的冻结计划
      (H07 完整性包装 + 内容身份核验;缺/坏结构化拒);不传 plan ⇒
      沿冻结输入(缺输入不变空池);传入计划内容不符 ⇒ 拒
      (frozen_plan_mismatch;差异须显式新 revision/新任务);
    - **冻结计划后段锚定(S3b r3/S3B-01 残余)**:读取的冻结计划
      与独立既存 run/root/task 原绑定核对(start 落账的根 retrieve
      行 plan_digest + task_key 单一来源重算;artifact 自洽摘要不是
      证书)—— 先于 recover 补账/事件/新调度/consume;缺锚/
      坏锚/不符结构化拒(frozen_plan_anchor_missing/
      frozen_plan_anchor_corrupt/frozen_plan_binding_mismatch),
      业务表零新增,原资料保全;覆盖 root retrieve 已 done 的
      B3/B4(retrieve 执行层核验后段不可达);正常同计划/省略
      plan/显式同计划恢复全保持;
    - recover_run:B4 幂等补账/B3 消费同一 output/B1 读冻结记录续跑/
      B2 pending 披露(不默发);
    - **恢复裁定接执行门(S3B-02)**:坏 artifact/缺权威的 claimed
      action 明确隔离(claimed → blocked,recovery_failure:<kind>;
      零猜重算、零坏任务 event/成功 commit/consume,证据保全);
      其他合法独立任务继续驱动;
    - 同 worker 身份继续驱动(幂等 reclaim);不重建/不覆盖既有
      搜索/attempt/request/提交记录。
    """
    runs_root = Path(runs_root)
    saved = load_run_identity(runs_root, run_id)
    if saved is None:
        from ..workflow.runner import RunNotFound
        raise RunNotFound(run_id, runs_root)
    saved_profile = (saved.get("profile") or {}).get("name", "")
    if saved_profile != PROFILE_POLLUTANT_PATHWAY_V1:
        raise PPV1RunError(
            f"run {run_id} 的 profile 为 {saved_profile!r}(PPV1 resume"
            " 只服务 pollutant_pathway_v1 run;legacy 旧身份按既有门槛"
            "拒绝)",
            {"run_id": run_id, "saved_profile": saved_profile,
             "kind": "profile_mismatch"})
    saved_mode = (saved.get("asset_identity") or {}).get(
        "mode", "repo_assets")
    current_asset = (scripted_asset_identity()
                     if saved_mode == "scripted_fixture"
                     else retrieval_asset_identity(config))
    saved_profile_block = saved.get("profile") or {}
    profile_kwargs = {
        key: saved_profile_block.get(key) for key in (
            "input_preview_policy", "chemical_reproposal", "search_intent",
            "search_limits", "format_feedback_policy")
        if key in saved_profile_block}
    current = build_run_identity(
        run_id=run_id, root_smiles=saved["inputs"]["root_smiles"],
        root_cn=saved["inputs"].get("root_identity"),
        strategy=saved["strategy"], asset_identity=current_asset,
        v3_code_identity=v3_code_identity(config.v3_code_root),
        prediction=_prediction_block(model),
        profile=PROFILE_POLLUTANT_PATHWAY_V1,
        profile_policy=profile_kwargs or None)
    check_resume_identity(saved, current)
    run_dir = runs_root / run_id
    with _DriverSession(run_dir) as session:
        store = PollutantPathwayStore(run_dir / "pollutant.sqlite")
        artifacts = ArtifactStore(runs_root, run_id)
        ledger = SearchLedger(store, artifacts, run_id)
        # ---- S3B-01:冻结计划输入核对(先于任何恢复消费) ----
        frozen_plan = _load_frozen_plan(artifacts)
        if plan is not None:
            submitted_digest = _plan_digest(plan)
            frozen_digest = _plan_digest(frozen_plan)
            if submitted_digest != frozen_digest:
                raise PPV1RunError(
                    "resume 传入计划与冻结输入不符(旧任务不消费新输入;"
                    "差异须显式新 revision/新任务登记,不能复用旧裁决键)",
                    {"kind": "frozen_plan_mismatch",
                     "frozen_plan_digest": frozen_digest,
                     "submitted_plan_digest": submitted_digest,
                     "run_id": run_id})
        # ---- S3b r3(S3B-01 后段锚定):读取的冻结计划与独立既存
        # run/root/task 原绑定核对(根 retrieve 行 plan_digest/
        # task_key);先于 recover_run 的 B4 补账/B3 bundle 消费与
        # 任何新调度/事件/预算 consume。自洽 artifact 内自 hash 不是
        # 独立证书;root retrieve 已 done 的 B3/B4 同样闭合(retrieve
        # 执行层核验后段不可达)。缺/坏锚或不符先结构化拒,零新增。 ----
        binding = _verify_frozen_plan_binding(ledger, run_id, frozen_plan)
        recovery = ledger.recover_run(
            run_id, policy_block=(saved.get("profile") or None),
            worker_id=_worker_id(run_id))
        # ---- S3B-02:恢复裁定接 driver 执行门(坏 artifact/缺权威
        # 隔离;合法 B1–B4 不受影响;证据保全) ----
        isolated: list[dict] = []
        for failure in _isolated_recovery_actions(recovery):
            out = ledger.isolate_recovered_failure(
                str(failure["action_id"]),
                kind=str((failure.get("failure") or {}).get("kind")
                         or "unknown"),
                note="恢复裁定的坏 artifact/缺权威:隔离不重执行,"
                     "证据保全;合法独立任务继续")
            isolated.append({**failure, "isolation": out})
        driver = _Driver(ledger, frozen_plan, run_id, _worker_id(run_id),
                         crash_after=crash_after)
        report = driver.drive()
        summary = _summary(store, run_id, report, resumed=True)
        summary["recovery"] = {
            "actions": recovery.get("actions"),
            "pending_requests": recovery.get("pending_requests"),
            "unknown_status_requests": recovery.get(
                "unknown_status_requests"),
            "isolated_actions": isolated,
        }
        summary["frozen_plan_binding"] = dict(binding)
        summary["driver_session"] = dict(session.info)
        return summary


def _cn_of(smiles: str) -> str:
    from ..domain.identity import cn_identity
    return cn_identity(smiles)


def _summary(store: PollutantPathwayStore, run_id: str,
             report: dict, *, resumed: bool) -> dict:
    return {
        "run_id": run_id,
        "profile": PROFILE_POLLUTANT_PATHWAY_V1,
        "runflow_version": RUNFLOW_VERSION,
        "resumed": resumed,
        "stop": report,
        "stop_reason": report.get("primary"),
        "counts": store.counts(),
    }
