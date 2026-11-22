"""S3b PPV1 独立 runner 执行流 —— start/resume 分流后的确定性驱动
(实施书 §6.2;契约随 search-6 / profile-16 / runflow-5 登记)。

S4a 增量(runflow-4):公共 start/resume 在驱动结束(stop report
之后)进入 **endpoint 四分账派生**(pollutant/endpoint.py:execution_
status / search_stop_reason / chemical_endpoint_assessment /
bookkeeping_status 独立分账、F01 停止非终点/F02 未知依赖不被
recorded 洗白/F03 去重计数不增独立支持),stop 与 endpoint 分别
持久化于 stop_reason_records / endpoint_records 两张派生投影表
(store-10;派生只读业务表,零 event/attempt/request/budget 写入),
派生后立即首消费读回(版本/hash/跨表引用/staleness 自校验)并构建
**原生结果对象**(pollutant/native_result.py:完整字段 + canonical
确定性规范化,同事实同 digest)。

S4b 增量(runflow-5):endpoint/原生对象之后立即进入**正式文件
导出与 v3 有损投影**(pollutant/native_export.py:payload+manifest
文件级导出,graph facts digest 新鲜度锚,首消费五类拒;
pollutant/v3_projection.py:显式 lossy_projection + 原生引用 +
信息损失清单 + 反向消费禁止)—— 导出后立即首消费读回(导出与
投影的完整性/过期自校验,不留"只写不读"的未验证窗口)。完整
公共链:scripted 输入 → start/resume → action/attempt/ledger →
停止 → endpoint 分账 → 原生导出 → 过期识别 → v3 适配 → 再次
读取/消费/replay。停止不是化学终点;endpoint 评估只由独立终点
证据决定;导出/投影纯派生(零 event/attempt/request/budget 写入)。

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
from .chemstate import ChemicalStateError, build_chemical_state, strict_identity_of
from .endpoint import (
    derive_run_endpoint,
    endpoint_summary_fields,
    read_run_endpoint,
)
from .hypothesis import HypothesisContractError
from .model_protocol import (
    FEEDBACK_ELIGIBLE,
    FORMAT_ERROR_STRUCTURE_UNPARSEABLE,
    MODEL_PROTOCOL_VERSION_PRODUCT_FIRST,
    NOVEL_VERIFICATION_FAILED_KIND,
    ModelProtocolError,
    feedback_policy_from_ledger,
    format_feedback_rounds_used,
    latest_format_feedback_round,
    parse_model_proposals,
    register_format_feedback_round,
)
from .novel_product_first import (
    ADDED_FRAGMENT_WHITELIST_SHA256,
    ADDED_HEAVY_ATOMS_BACKSTOP,
    KNOWN_MOIETY_TABLE_SHA256,
    LEAVING_GROUP_WHITELIST_SHA256,
    MAX_ADDED_FRAGMENTS,
    NOVEL_BUCKET_POLICY_VERSION,
    NOVEL_BUCKET_TABLE_SHA256,
    REMOVED_HEAVY_ATOMS_BACKSTOP,
    VERIFICATION_TIER_FULL,
    compile_novel_product_first,
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
    NOVEL_PROTOCOL_ATOM_EDIT,
    NOVEL_PROTOCOL_BLIND_FIRST,
    NOVEL_PROTOCOL_PRODUCT_FIRST,
    NOVEL_PROTOCOLS,
    PPV1_RUNFLOW_SCHEMA_VERSION,
    build_profile_identity_block,
    format_feedback_policy_version_for,
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
from .native_export import (
    export_native_result,
    read_native_export,
)
from .native_result import build_native_result, persist_native_result
from .store import PollutantPathwayStore
from .substrate_profile import build_substrate_profile
from .v3_projection import (
    build_v3_projection,
    persist_v3_projection,
    read_v3_projection,
)

# 单一事实源:profile.PPV1_RUNFLOW_SCHEMA_VERSION(S4b 起移入 profile,
# native_export manifest 的 contract_versions 与本模块共用同一常量)
RUNFLOW_VERSION = PPV1_RUNFLOW_SCHEMA_VERSION
FROZEN_PLAN_VERSION = "ppv1-frozen-plan-1"
FROZEN_PLAN_TASK_KEY = "run-plan"
FROZEN_PLAN_ARTIFACT = "frozen_plan"
# W3:统一选择排序规则版本("模型选择"与"确定性 fallback"两个版本化
# 规则;显式 rank 先于 fallback;novel 不因来源排后;净反应签名去重)。
# v2(2026-10-17,T-F 合成验证证实的修复):同签名折叠时被折叠者的声明
# 位次优于幸存者(或幸存者无声明位次)⇒ 幸存者继承该位次并逐条披露
# (模型对净反应的偏好不因表示重复丢失;v1 该位次被静默丢弃)
S5B_RANK_POLICY_VERSION = "s5b-rank-policy-2"

# EXP1 C 臂(2026-11-06):合并阶段池条目里"先前盲写"来源标记(仅该阶段
# 渲染;A/B 臂条目永不带 ⇒ 载荷逐字节不变)
BLIND_FIRST_ORIGIN = "blind_first"


class PPV1RunError(RuntimeError):
    """PPV1 run 入口契约违反(结构化)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _plan_digest(plan: dict) -> str:
    return content_hash(plan or {})


def _resolve_novel_protocol(value) -> str:
    """novel 协议归一（None ⇒ atom_edit 缺省 = A 臂/旧 run;未知值 ⇒
    结构化拒,不静默落回 A 臂）。"""
    if value is None:
        return NOVEL_PROTOCOL_ATOM_EDIT
    protocol = str(value)
    if protocol not in NOVEL_PROTOCOLS:
        raise PPV1RunError(
            f"novel 协议非法值:{value!r}(须 None/"
            f"{'/'.join(NOVEL_PROTOCOLS)};fail-closed 拒,不猜)",
            {"kind": "novel_protocol_invalid", "value": repr(value)})
    return protocol


def _novel_bucket_identity_fields() -> dict:
    """方案甲策略身份(只进 B/C 臂;A 臂零新键)。

    策略版本 + 冻结参数 + 三张表内容哈希(逐表 + 合并),供 run 摘要与
    decide note 共用同一事实源。
    """
    return {
        "novel_bucket_policy_version": NOVEL_BUCKET_POLICY_VERSION,
        "added_heavy_atoms_backstop": int(ADDED_HEAVY_ATOMS_BACKSTOP),
        "removed_heavy_atoms_backstop": int(REMOVED_HEAVY_ATOMS_BACKSTOP),
        "max_added_fragments": int(MAX_ADDED_FRAGMENTS),
        "novel_bucket_table_sha256": NOVEL_BUCKET_TABLE_SHA256,
        "novel_bucket_table_sha256_by_table": {
            "added_fragment_whitelist": ADDED_FRAGMENT_WHITELIST_SHA256,
            "leaving_group_whitelist": LEAVING_GROUP_WHITELIST_SHA256,
            "known_moiety_table": KNOWN_MOIETY_TABLE_SHA256,
        },
    }


def _novel_protocol_summary_fields(protocol: str) -> dict:
    """实验臂 run 摘要披露(仅非默认臂;A 臂/旧 run 零新键)。

    B 臂(product_first_feedback)与 C 臂(blind_first)共用同一组摘要
    键;C 臂另在 run 身份的 prediction.prompt_versions 披露双 prompt
    版本(盲写 + 合并)。
    """
    return {
        "novel_protocol": str(protocol),
        **_novel_bucket_identity_fields(),
        "format_feedback_policy_version":
            format_feedback_policy_version_for(protocol),
    }


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


def _declared_consistency_report(prepared: dict,
                                 declared_product: str,
                                 declared_coproducts: list[str],
                                 effective_spec: dict) -> dict:
    """v1.3 T4-A:落库结构 vs 模型声明产物的一致性核验(只披露、不改行为)。

    语义(开关 ``enable_v13_declared_product_consistency`` 打开时消费;
    默认关闭 ⇒ 本函数不被调用,行为与改前逐字节同):

    - **落库侧** = ``prepared["product_states"]`` 的结构串 —— 即
      ``prepare_hypothesis`` 之后真正进事件/落库的那组产物(含执行器
      自动补齐的裂解/水解副产物);
    - **声明侧** = 模型 ``reaction_spec.product_smiles`` +
      ``coproducts``;
    - 逐条按 ``strict_identity_of``(与 state_id 同一事实源)的严格身份
      做**多重集包含**:每条声明组分都要在落库组分里找到同身份条目
      (消耗式匹配,数量不够 ⇒ 不覆盖);
    - 返回值**只进机读披露**(``v13_declared_consistency_mismatches``),
      **不拒提案、不改排序**:T4-pre §5.3 的原始现象(atom_edit 优先
      路径把共产物执行成别的结构)在本树不成立 —— 该路径因
      ``execute_atomtool_expansion`` 未在 ``_run_decide`` 作用域导入而
      恒抛 NameError(既有缺陷,本轮只报告不修),所有 novel 提案本来
      就走产物优先回退编译;回退编译的 spec 里 ``coproducts`` 也**不是**
      最终事件产物集(执行器会补水解副产物/水),拿 spec 当判据会误杀
      真命中。因此本函数以落库侧 prepared 为唯一事实源。

    不做的事:不做中和/互变异构/电荷规整 —— 严格身份是既定口径;
    本函数只判「落库结构是否覆盖模型声明的那组产物」,不放宽产物身份。
    """
    declared: list[str] = []
    if str(declared_product or "").strip():
        declared.append(str(declared_product).strip())
    for cop in (declared_coproducts or []):
        text = str(cop or "").strip()
        if text:
            declared.append(text)
    stored: list[str] = []
    for state in (prepared or {}).get("product_states") or []:
        smiles = str(getattr(state, "smiles_isomeric", "") or "").strip()
        if smiles:
            stored.append(smiles)
    report: dict = {
        "declared_product": str(declared_product or ""),
        "declared_coproducts": list(declared_coproducts or []),
        "stored_products": stored,
        "compiled_product": str(
            (effective_spec or {}).get("product_smiles") or ""),
        "compiled_coproducts": [
            str(c) for c in ((effective_spec or {}).get("coproducts") or [])],
        "covered": False,
        "reason": "",
    }
    if not declared or not stored:
        report["reason"] = ("no_declared_components" if not declared
                            else "no_stored_products")
        return report
    try:
        rest: list[str] = [strict_identity_of(part) for part in stored]
    except ChemicalStateError:
        report["reason"] = "stored_identity_failed"
        return report
    for part in declared:
        try:
            want = strict_identity_of(part)
        except ChemicalStateError:
            report["reason"] = "declared_identity_failed"
            return report
        if want not in rest:
            report["reason"] = "declared_component_not_stored"
            report["missing_component"] = part
            return report
        rest.remove(want)
    report["covered"] = True
    report["reason"] = "covered"
    return report


def _execution_declaration_mismatch(exec_out: dict,
                                    declared: list[str]) -> dict:
    """T10-A 开关 1:执行产物组分集 vs 模型声明组分集的严格身份核验。

    返回空 dict = 一致;非空 = 结构化差异(``reason`` + 两侧组分)。
    语义:``execute_atomtool_expansion`` 实际执行的产物组分必须与模型
    声明的 ``product_smiles + coproducts`` **严格身份多重集相等** ——
    落库侧 ``prepared["product_states"]`` 本就由声明构建,单看它无法
    发现「声明产物不是执行产物」;atom_edit 优先路径必须同时核对执行
    结果,否则会把未执行出的产物写进事件(T4-A3 同根反例)。不做中和/
    互变异构/电荷规整:严格身份是既定口径,不一致一律回退产物优先
    编译(不朴素拒绝、不放宽身份)。
    """
    from .chemstate import strict_identity_of

    result = (exec_out or {}).get("result") or {}
    executed = [part for part in str(
        result.get("product_smiles") or "").split(".") if part.strip()]
    if not executed:
        return {"reason": "no_executed_product"}
    declared_parts = [part for part in
                      [str(x) for x in (declared or [])]
                      for part in part.split(".") if part.strip()]
    try:
        have = sorted(strict_identity_of(part) for part in executed)
        want = sorted(strict_identity_of(part) for part in declared_parts)
    except Exception:
        return {"reason": "identity_failed"}
    if have != want:
        return {"reason": "executed_product_set_mismatch",
                "executed_components": executed[:8],
                "declared_components": declared_parts[:8]}
    return {}


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


ROUTING_TIER_RANK: dict[str, int] = {
    "primary": 0, "secondary": 1, "other": 2, "unrouted": 2}


def order_pool_entries_by_routing_tier(entries: list[dict]) -> list[dict]:
    """v1.3 T11:Stage 2 池条目按 ``routing_tier`` **稳定**分组重排。

    - 组序 ``primary`` → ``secondary`` → ``other``(``unrouted`` 与
      ``other`` 同组序,排在其后到达次序);
    - 组内保持原相对顺序(Python sort 稳定);
    - **零删池**:只换序,不增不减(条目对象原样返回,同一引用);
    - 未知/缺失 tier ⇒ 归 ``other`` 组序(不丢条目)。
    """
    return sorted(
        list(entries or []),
        key=lambda entry: ROUTING_TIER_RANK.get(
            str(entry.get("routing_tier") or "unrouted"), 2))


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


def _novel_verification_error(failures: list[dict]) -> ModelProtocolError:
    """核验失败集 → 可登记的可反馈错误(E5/E7)。

    detail 只含**预注册 §5 白名单**字段(与送模型的反应用同一渲染器
    ``render_verification_feedback``),无时间戳/路径/repr/不稳定排序
    ⇒ 同一响应 + 同一编译结果可确定性重算 payload_hash(反馈轮复用
    身份门 ``latest_format_feedback_round`` 判据 4 依赖此性质)。
    """
    from .real_model import render_verification_feedback

    cleaned = render_verification_feedback(
        {"failures": list(failures or [])})["failures"]
    cleaned.sort(key=lambda item: (str(item.get("hypothesis_id") or ""),
                                   str(item.get("failure_kind") or "")))
    return ModelProtocolError(
        "novel 提案程序核验未通过(产物优先:编译/执行/产物集合核对;"
        "核验失败不计事件,可经有界反馈修正)",
        {"kind": NOVEL_VERIFICATION_FAILED_KIND, "failures": cleaned})


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


def _verify_frozen_plan_binding(
        ledger: SearchLedger, run_id: str, frozen_plan: dict,
        *,
        feedback_policy_version: str = FORMAT_FEEDBACK_POLICY_VERSION
        ) -> dict:
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
            feedback_policy_version=feedback_policy_version)
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


def effective_stage1_routing(
    model_note: dict | None,
    external: dict | None,
) -> dict | None:
    """T12-B 路由事实选择：运行自身 Stage-1 outcome 优先，外部映射兜底。

    - 两段式路由批：``_model_proposals`` 已把 Stage-1 解析结果写进
      ``note["class_routing"]``（T12-A 修键后非空）；解析失败时
      ``primary_class`` 为 None ⇒ 落到外部映射（如有）。
    - 零调用重放批（历史臂无 Stage-1 调用）：只用计划注入的外部脱敏
      映射 ``v13_stage1_routing_external``。
    两者都不可用 ⇒ 返回 None（该题不触发精排，原样返回）。
    """
    note = dict(model_note or {})
    own = dict(note.get("class_routing") or {})
    if own.get("primary_class"):
        return {
            "primary_class": own.get("primary_class"),
            "secondary_class": own.get("secondary_class"),
            "source": "stage1_live",
        }
    ext = dict(external or {})
    if ext.get("primary_class"):
        return {
            "primary_class": ext.get("primary_class"),
            "secondary_class": ext.get("secondary_class"),
            "source": "external_replay_map",
        }
    return None


def consensus_and_smart_backfill(
    *,
    substrate_state,
    parent_ctx,
    pool_specs: list[dict],
    prepared_entries: list[tuple[str, dict, dict]],
    deduped_indices: list[int],
    novel_entry_idx: set[int],
    blind_idx_set: set[int],
    ranked_keys: list[str],
    retained_keys: list[str],
    pre_dedup_novel_stricts: set[str] | None = None,
    derive_branch_ctx_fn=None,
    s5_supplement_gate_max_s1d: int = 2,
    s5_super_consensus_score: float = 115.0,
    s5_max_supplements: int = 2,
    target_slots: int = 5,
    v13_rank_rules: bool = False,
    v13_stage1_rank: bool = False,
    stage1_routing: dict | None = None,
    stage1_params: dict | None = None,
    stage1_debug_sink: dict | None = None,
    v13_multi_sample_consensus: bool = False,
    v13_consensus_params: dict | None = None,
    secondary_ranked_keys_list: list[list[str]] | None = None,
    v13_consensus_debug_sink: dict | None = None,
    # v1.4 T14-4(默认关):跨池资格率归一化(1:1 对齐的每 pass 资格键)
    secondary_eligible_keys_list: list[list[str] | None] | None = None,
    v14_cross_pool_elig_norm: bool = False,
    enable_v12_post_mechanism: bool = True,
    collect_pass_debug: bool = False,
    enable_v14_pairwise_adjudication: bool = False,
    v14_adjudication_external: dict | None = None,
    v14_adjudication_sink: dict | None = None,
    disable_cleavage_upgrade: bool = False,
    disable_ranking_calibration: bool = False,
) -> dict:
    """v44-Next 决策与核验后置层：跨源独立共识升位 (Consensus Boost) + 智能门控尾部回填 (Smart-Gated Backfill)。

    ``enable_v12_post_mechanism=False`` 时整体关闭 v1.2 回复后机制
    （3.5 候选排序校准 + 裂解共产物补齐），复现 v1.1 回复后行为（T2-G 硬门）。

    ``enable_v14_pairwise_adjudication``（v1.4 T14-3，默认关）只在 3.5 之后
    按外部脱敏判决**在既有 Top-N 内部**换位（3.6 段）；关闭或没有外部判决
    ⇒ 3.6 段整段不执行，与 v1.3 逐字节一致。

    所有进入排序与尾部回填的候选均须通过正规 `prepare_hypothesis` + RDKit `execute_atomtool_expansion`
    + 11 项 `audit_hypothesis` + `decide_admission` 核验。
    """
    from .audit import audit_hypothesis, decide_admission
    from .chemstate import strict_identity_of
    from .production import ADMISSION_SUBMITTABLE, execute_atomtool_expansion

    pool_principal_stricts = {
        strict_identity_of(str(s.get("product_smiles") or ""))
        for s in (pool_specs or [])
        if str(s.get("product_smiles") or "").strip()
    }
    pool_principal_stricts.discard("")
    novel_stricts = set(pre_dedup_novel_stricts or set())

    verified_by_key: dict[str, bool] = {}
    prod_strict_by_key: dict[str, str] = {}
    prior_score_by_key: dict[str, float] = {}
    is_supp_by_key: dict[str, bool] = {}
    orig_idx_by_key: dict[str, int] = {}
    consensus_boost_by_key: dict[str, bool] = {}

    model_selected_set = set(ranked_keys) | set(retained_keys)

    for orig_idx, (key, spec, prepared) in zip(deduped_indices, prepared_entries):
        orig_idx_by_key[key] = int(orig_idx)
        p_smi = str(spec.get("product_smiles") or "")
        p_strict = strict_identity_of(p_smi) if p_smi else ""
        prod_strict_by_key[key] = p_strict
        c_meta = spec.get("compile") or {}
        p_score = float(
            spec.get("s5_prior_score")
            if spec.get("s5_prior_score") is not None
            else (c_meta.get("s5_prior_score") or 0.0)
        )
        prior_score_by_key[key] = p_score
        is_supp = bool(
            spec.get("is_gated_supplement")
            if spec.get("is_gated_supplement") is not None
            else c_meta.get("is_gated_supplement", False)
        )
        is_supp_by_key[key] = is_supp

        # 执行 RDKit 工具展开与 11 项 audit_hypothesis 核验
        admitted_ok = False
        try:
            exec_in = str(
                prepared["tool_inputs"].get("execution_input_smiles")
                or substrate_state.smiles_isomeric
            )
            exec_out = execute_atomtool_expansion(
                substrate_smiles=exec_in,
                tool_inputs=prepared["tool_inputs"],
            )
            if exec_out.get("execution_ok"):
                ctx_for_audit = parent_ctx
                if (
                    derive_branch_ctx_fn is not None
                    and (spec.get("requirements") or spec.get("dependencies") or spec.get("assumptions"))
                ):
                    ctx_for_audit = derive_branch_ctx_fn(
                        parent_ctx, prepared, prepared["hypothesis"].hypothesis_id
                    )
                audit_rep = audit_hypothesis(
                    prepared["hypothesis"],
                    run_id="v44-precheck",
                    states=prepared["states"],
                    context=ctx_for_audit,
                    center_evidence=exec_out["center_evidence"],
                )
                disposition, _reasons = decide_admission(audit_rep)
                if disposition in ADMISSION_SUBMITTABLE:
                    admitted_ok = True
        except Exception:
            admitted_ok = False
        verified_by_key[key] = admitted_ok

        # 跨源独立共识判定：
        # 1) 模型合法提案（盲写/novel 或模型首推/显式选中的池外一致主产物）与候选池主产物 strict_identity_of 一致；
        # 2) 或池事件具备 s5_prior_score >= s5_super_consensus_score（跨 >= 2 独立源共识）
        src_fams = set(spec.get("source_families") or c_meta.get("source_families") or [])
        is_novel_or_blind = (orig_idx in novel_entry_idx) or (orig_idx in blind_idx_set) or (p_strict in novel_stricts)
        model_pool_consensus = bool(
            admitted_ok
            and p_strict
            and p_strict in pool_principal_stricts
            and (
                is_novel_or_blind
                or (key in ranked_keys[:1])
                or (key in model_selected_set and len(src_fams) >= 2)
            )
        )
        super_prior_consensus = bool(
            admitted_ok
            and p_score >= float(s5_super_consensus_score)
            and (len(src_fams) >= 2 or spec.get("s5_prior_tier") == "HIGH_CONSENSUS")
        )
        is_boost = bool(model_pool_consensus or super_prior_consensus)
        consensus_boost_by_key[key] = is_boost
        if is_boost:
            spec["consensus_boost"] = True

    # 1. 整理模型主推合法事件序列（100% 保持模型显式给出的排序）
    raw_model_order = list(ranked_keys) + [k for k in retained_keys if k not in ranked_keys]
    verified_model_picks = [k for k in raw_model_order if verified_by_key.get(k, False)]
    ordered_model_picks = list(verified_model_picks)

    # 2. 候选池中通过核验的预编译事件（按共识升位 -> 化学先验分降序 -> 原始池序）
    n_s1d_templates = sum(
        1
        for s in (pool_specs or [])
        if str((s.get("compile") or {}).get("source_kind") or "") != "s5_hybrid_rule"
        and not s.get("is_gated_supplement")
    )
    verified_pool_keys = [
        key
        for orig_idx, (key, _spec, _prep) in zip(deduped_indices, prepared_entries)
        if orig_idx < len(pool_specs or []) and verified_by_key.get(key, False)
    ]
    verified_pool_keys.sort(
        key=lambda k: (
            0 if consensus_boost_by_key.get(k, False) else 1,
            -prior_score_by_key.get(k, 0.0),
            orig_idx_by_key.get(k, 9999),
        )
    )

    sparse_gate = n_s1d_templates <= int(s5_supplement_gate_max_s1d)
    super_consensus_gate = any(
        prior_score_by_key.get(k, 0.0) >= float(s5_super_consensus_score)
        for k in verified_pool_keys
    )
    underfilled_gate = len(ordered_model_picks) < int(target_slots)
    smart_gate_triggered = bool(sparse_gate or super_consensus_gate or underfilled_gate)

    # 筛选门控高先验补充项（最多 s5_max_supplements 条，用于未满尾部槽位优先回填）
    gated_supp_keys: list[str] = []
    if sparse_gate or super_consensus_gate:
        for k in verified_pool_keys:
            if len(gated_supp_keys) >= int(s5_max_supplements):
                break
            if (
                is_supp_by_key.get(k, False)
                or prior_score_by_key.get(k, 0.0) >= float(s5_super_consensus_score)
                or (sparse_gate and prior_score_by_key.get(k, 0.0) >= 70.0)
            ):
                gated_supp_keys.append(k)

    def _assemble_top(picks: list[str]) -> tuple[list[str], list[str]]:
        selected: list[str] = []
        kept_stricts: set[str] = set()
        backfilled: list[str] = []
        picks_set = set(picks)
        gate_on = bool(
            sparse_gate or super_consensus_gate
            or len(picks) < int(target_slots)
        )

        def _try_add(cand_k: str, *, is_backfill: bool = False) -> bool:
            if len(selected) >= int(target_slots):
                return False
            if cand_k in selected:
                return False
            st = prod_strict_by_key.get(cand_k, "")
            if st and st in kept_stricts:
                return False
            selected.append(cand_k)
            if st:
                kept_stricts.add(st)
            if is_backfill and cand_k not in picks_set:
                backfilled.append(cand_k)
            return True

        for k in picks:
            if len(selected) >= int(target_slots):
                break
            _try_add(k, is_backfill=False)

        if len(selected) < int(target_slots):
            for k in gated_supp_keys:
                if len(selected) >= int(target_slots):
                    break
                _try_add(k, is_backfill=True)

        if gate_on and len(selected) < int(target_slots):
            for k in verified_pool_keys:
                if len(selected) >= int(target_slots):
                    break
                _try_add(k, is_backfill=True)

        return selected, backfilled

    # 3. 组装前 target_slots (5) 槽位：
    # 模型从池内或 novel 显式选中的合法候选 100% 按模型声明序保留在前部；
    # 尾部空缺槽位优先由门控高先验补充项 (gated_supp_keys) 确定性回填，再由候选池其余高先验合法事件补满至 5 条
    selected_top_keys, backfilled_keys = _assemble_top(ordered_model_picks)
    assembled_sec_keys_list: list[list[str]] | None = None
    if v13_multi_sample_consensus and secondary_ranked_keys_list:
        assembled_sec_keys_list = [
            _assemble_top([k for k in (sec_picks or [])
                           if verified_by_key.get(k, False)])[0]
            for sec_picks in secondary_ranked_keys_list
        ]

    # 3.5 DECISION-9 方向 3（v44-Next v1.2 候选排序器校准 + 多产物裂解共产物补齐）
    # T2-G：``enable_v12_post_mechanism=False`` 时整段跳过，等于 v1.1 回复后行为。
    if enable_v12_post_mechanism:
        from ..services.s5_hybrid_choice import (
            _smiles_has_carbon,
            calibrate_submittable_ranking,
            try_upgrade_cleavage_spec,
        )

        if not disable_ranking_calibration:
            selected_top_keys = calibrate_submittable_ranking(
                selected_top_keys=selected_top_keys,
                prepared_entries=prepared_entries,
                deduped_indices=deduped_indices,
                pool_specs=pool_specs,
                verified_by_key=verified_by_key,
                prod_strict_by_key=prod_strict_by_key,
                novel_entry_idx=novel_entry_idx,
                target_slots=int(target_slots),
                v13_rank_rules=bool(v13_rank_rules),
                v13_stage1_rank=bool(v13_stage1_rank),
                stage1_routing=stage1_routing,
                substrate_smiles=str(
                    getattr(substrate_state, "smiles_isomeric", "") or ""),
                stage1_params=stage1_params,
                stage1_debug_sink=stage1_debug_sink,
                v13_multi_sample_consensus=bool(v13_multi_sample_consensus),
                v13_consensus_params=v13_consensus_params,
                secondary_ranked_keys_list=(
                    assembled_sec_keys_list
                    if assembled_sec_keys_list is not None
                    else secondary_ranked_keys_list
                ),
                v13_consensus_debug_sink=v13_consensus_debug_sink,
                collect_pass_debug=bool(collect_pass_debug),
                secondary_eligible_keys_list=secondary_eligible_keys_list,
                enable_v14_cross_pool_elig_norm=bool(
                    v14_cross_pool_elig_norm),
            )
        for k in selected_top_keys:
            if k not in ordered_model_picks and k not in backfilled_keys:
                backfilled_keys.append(k)

        selected_top_set = set(selected_top_keys)
        for idx_in_prep, (orig_idx, (k, spec, prep)) in enumerate(
            zip(deduped_indices, prepared_entries)
        ):
            if k not in selected_top_set:
                continue
            is_s5_or_novel = (
                str(k).startswith("s5-")
                or str(k).startswith("novel-")
                or (int(orig_idx) in novel_entry_idx)
            )
            if not is_s5_or_novel or not spec.get("undeclared_coproducts"):
                continue
            if any(_smiles_has_carbon(str(c)) for c in (spec.get("coproducts") or [])):
                continue
            if disable_cleavage_upgrade:
                # 论文消融 v1.4 ②(默认 False ⇒ 逐字节不变):关闭
                # try_upgrade_cleavage_spec 逆向补碳升级,候选/共产物
                # 原样保留。
                continue
            up_spec = try_upgrade_cleavage_spec(substrate_state.smiles_isomeric, spec)
            if up_spec is not None:
                try:
                    src_refs = [
                        dict(r) if isinstance(r, dict) else {"record": str(r)}
                        for r in (getattr(prep["hypothesis"], "source_refs", None) or [])
                    ]
                    up_prep = prepare_hypothesis(
                        up_spec,
                        parent_path_id=str(prep["hypothesis"].parent_path_id),
                        substrate_state=substrate_state,
                        transformation_ref=str(up_spec.get("transformation_ref") or ""),
                        source_refs=src_refs or None,
                    )
                    spec.clear()
                    spec.update(up_spec)
                    prepared_entries[idx_in_prep] = (k, spec, up_prep)
                except Exception:
                    pass

    # 3.6 v1.4 T14-3 成对互换机理裁决重排（默认关；零候选增删）。
    # 位置纪律：必须排在 ``try_upgrade_cleavage_spec`` 循环**之后**、
    # ``effective_rank_by_key`` **之前** —— 裂解升级会改写裂解候选的共同
    # 产物与 ``prepared_entries``，只有在此处算出的展示串才与最终落入
    # ``pollutant.sqlite`` 的 event 逐字节一致。
    if (
        enable_v14_pairwise_adjudication
        and v14_adjudication_external
        and len(selected_top_keys) >= 2
    ):
        from ..services.adjudication_v14 import (
            apply_pairwise_adjudication,
            candidate_display_from_prepared,
            candidate_display_sha256,
        )

        prep_by_key = {
            str(k): prep for k, _spec, prep in prepared_entries
        }
        sha_by_key = {
            str(k): candidate_display_sha256(
                candidate_display_from_prepared(prep_by_key[k]))
            for k in selected_top_keys
            if k in prep_by_key
        }
        selected_top_keys, _adj_disclosure = apply_pairwise_adjudication(
            selected_top_keys=list(selected_top_keys),
            sha_by_key=sha_by_key,
            external=v14_adjudication_external,
        )
        if v14_adjudication_sink is not None:
            v14_adjudication_sink["note"] = dict(_adj_disclosure)

    # 4. 生成重排后的 effective_rank_by_key 与 rank_basis_by_key
    effective_rank_by_key: dict[str, int] = {}
    rank_basis_by_key: dict[str, str] = {}
    next_rank = 1
    for k in selected_top_keys:
        effective_rank_by_key[k] = next_rank
        rank_basis_by_key[k] = (
            "model_selection" if k in ranked_keys else "deterministic_fallback"
        )
        next_rank += 1
    for _idx, (k, _spec, _prep) in zip(deduped_indices, prepared_entries):
        if k in effective_rank_by_key:
            continue
        if verified_by_key.get(k, False):
            effective_rank_by_key[k] = next_rank
            rank_basis_by_key[k] = (
                "model_selection" if k in ranked_keys else "deterministic_fallback"
            )
            next_rank += 1
    for _idx, (k, _spec, _prep) in zip(deduped_indices, prepared_entries):
        if k in effective_rank_by_key:
            continue
        effective_rank_by_key[k] = next_rank
        rank_basis_by_key[k] = "deterministic_fallback"
        next_rank += 1

    return {
        "effective_rank_by_key": effective_rank_by_key,
        "rank_basis_by_key": rank_basis_by_key,
        "consensus_boost_by_key": consensus_boost_by_key,
        "backfilled_keys": backfilled_keys,
        "selected_top_keys": selected_top_keys,
        "smart_gate_triggered": smart_gate_triggered,
        "n_s1d_templates": n_s1d_templates,
    }


class _Driver:
    """一次驱动会话(进程内;恢复后新实例从持久记录继续;消费冻结
    计划输入)。"""

    def __init__(self, ledger: SearchLedger, plan: dict, run_id: str,
                 worker_id: str, crash_after: str | None = None,
                 model=None, evidence_card_enabled: bool = True,
                 evidence_card_version: str | None = None,
                 novel_protocol: str | None = None,
                 enable_smart_gated_backfill: bool = False,
                 s5_supplement_gate_max_s1d: int = 2,
                 s5_super_consensus_score: float = 115.0,
                 s5_max_supplements: int = 2,
                 backfill_target_events: int = 5) -> None:
        self.ledger = ledger
        self.store = ledger.store
        self.plan = plan or {}
        self.run_id = run_id
        self.worker_id = worker_id
        self.crash_after = crash_after
        # S5b 最小接线钩子:调用方注入的模型对象(scripted 恒 None;
        # real=RealModelAdapter —— 只在 provider_kind=real 且对象实现
        # ppv1_real_fetch 时改"取响应"一步,其余行为逐字节不变)
        self.model = model
        # chain14:批级证据卡开关(A/B 唯一差分变量;消费点 =
        # _call_real_fetch,false ⇒ 载荷回到证据卡实施前四字段形状)
        self.evidence_card_enabled = bool(evidence_card_enabled)
        # P2(2026-10-21):证据卡版本;None/v1=旧路径逐字节等价,
        # v2=新 prompt/v2 字段,v1card=v2 prompt/v1 证据卡（两臂共享
        # v2 prompt）
        self.evidence_card_version = evidence_card_version
        # EXP1(2026-11-05):novel 协议(A 臂 atom_edit = 缺省;B 臂
        # product_first_feedback = 产物优先编译 + 核验反馈循环)。
        # 冻结反馈策略版本按协议取(A 臂 v1 / B 臂 v2),进任务键。
        self.raw_novel_protocol = novel_protocol
        self.novel_protocol = _resolve_novel_protocol(novel_protocol)
        self.format_feedback_policy_version = \
            format_feedback_policy_version_for(self.novel_protocol)
        preset_norm = str(self.plan.get("preset") or "").strip().lower().replace("_", "-")
        self.enable_smart_gated_backfill = bool(
            enable_smart_gated_backfill
            or self.plan.get("enable_smart_gated_backfill")
            or preset_norm == "v44-next"
        )
        self.s5_supplement_gate_max_s1d = int(
            self.plan.get("s5_supplement_gate_max_s1d", s5_supplement_gate_max_s1d)
        )
        self.s5_super_consensus_score = float(
            self.plan.get("s5_super_consensus_score", s5_super_consensus_score)
        )
        self.s5_max_supplements = int(
            self.plan.get("s5_max_supplements", s5_max_supplements)
        )
        self.backfill_target_events = int(
            self.plan.get("backfill_target_events", backfill_target_events)
        )
        # v1.3 T1-C：机理排序规则开关（默认关闭；关闭时与 v1.2 零漂移）
        self.enable_v13_rank_rules = bool(
            self.plan.get("enable_v13_rank_rules", False)
        )
        # v1.3 T1-D：通用枚举器吸附开关（默认关闭；枚举清单不进提示词）
        self.enable_v13_generic_enumeration = bool(
            self.plan.get("enable_v13_generic_enumeration", False)
        )
        # T2-G：v1.2 回复后机制总开关（默认开启＝v1.2 行为；关闭＝v1.1 回复后行为）
        self.enable_v12_post_mechanism = bool(
            self.plan.get("enable_v12_post_mechanism", True)
        )
        # v1.3 T4-A：立体消解扩展（断键/芳香化后手性标签消失；默认关闭）
        self.enable_v13_stereo_dissolution_extended = bool(
            self.plan.get("enable_v13_stereo_dissolution_extended", False)
        )
        # v1.3 T4-A：atom_edit 执行结果与声明产物一致性门（不一致回退
        # 产物优先编译；默认关闭）
        self.enable_v13_declared_product_consistency = bool(
            self.plan.get("enable_v13_declared_product_consistency", False)
        )
        # v1.3 T4-A：模型回复容错解析（逐条丢弃非法提案，保留合法提案；
        # 默认关闭＝整响应结构失败）
        self.enable_v13_tolerant_model_parse = bool(
            self.plan.get("enable_v13_tolerant_model_parse", False)
        )
        # T10-A 开关 1：_run_decide atom_edit 路径缺 execute_atomtool_
        # expansion 导入（既有 NameError ⇒ prepared=None 恒回退产物优先
        # 编译）。默认关闭＝与改前逐字节同；打开才局部导入并在落库前
        # 做严格身份覆盖核验（不覆盖则回退产物优先编译，绝不放宽）。
        self.fix_decide_atomtool_import = bool(
            self.plan.get("fix_decide_atomtool_import", False)
        )
        # T10-A 开关 2：预算拒绝时的已付费响应消费（格式反馈预算用尽
        # 时用容错解析消费已返回响应；drive 层预算拒时先跳过该 pending
        # action、把已认领且已 responded 的 action 消费完再停）。默认
        # 关闭＝与改前逐字节同。
        self.fix_budget_limit_consumption = bool(
            self.plan.get("fix_budget_limit_consumption", False)
        )
        # ---- 论文消融 v1.4(2026-11-16;默认全 False ⇒ 与改前逐字节同)----
        # ① AtomTool 输入视图/纯 SMILES 协议:关断 execution_graph +
        # substrate_atom_id_map 注入并切换 v3_type_raw_smiles 合同;
        # 该协议只定义在产物优先(compile_novel_product_first)路径上。
        self.disable_atomtool_prompt = bool(
            self.plan.get("disable_atomtool_prompt", False)
        )
        # ② 裂解补碳逆向升级(try_upgrade_cleavage_spec)消融。
        self.disable_cleavage_upgrade = bool(
            self.plan.get("disable_cleavage_upgrade", False)
        )
        # ③ 产物优先逆向图差编译回退消融:True ⇒ 池外 novel 只能靠模型
        # 正向手写 AtomTool edits 通过;回退失败 ⇒ 直接拒提案。
        self.disable_product_first_fallback = bool(
            self.plan.get("disable_product_first_fallback", False)
        )
        # ④ 回复后排序校准(calibrate_submittable_ranking / R1 守卫规则)
        # 消融:True ⇒ 只跳过排序校准,保留裂解共产物补齐(后者的独立
        # 开关见 ②;两行消融不得互相污染)。
        self.disable_ranking_calibration = bool(
            self.plan.get("disable_ranking_calibration", False)
        )
        if self.disable_atomtool_prompt:
            # 显式指定非产物优先协议 ⇒ fail-closed(不静默混协议);
            # 缺省原子编辑协议(null)在本开关下强制切到产物优先。
            _explicit_protocol = str(novel_protocol or "").strip()
            if _explicit_protocol and \
                    _explicit_protocol != NOVEL_PROTOCOL_PRODUCT_FIRST:
                raise PPV1RunError(
                    "disable_atomtool_prompt 只定义在产物优先(compile_"
                    "novel_product_first)路径上(显式非产物优先协议;"
                    "fail-closed,不混协议)",
                    {"kind": "disable_atomtool_prompt_protocol_conflict",
                     "novel_protocol": _explicit_protocol,
                     "disable_atomtool_prompt": True})
            if self.evidence_card_version is not None:
                raise PPV1RunError(
                    "disable_atomtool_prompt 与证据卡版本不兼容(纯 "
                    "SMILES 协议载荷不含证据卡;fail-closed)",
                    {"kind": "disable_atomtool_prompt_evidence_conflict",
                     "evidence_card_version": self.evidence_card_version,
                     "disable_atomtool_prompt": True})
            # 注意:本块位于 v3 开关属性赋值之前 ⇒ 从 plan 读取(不能
            # 引用 self.enable_v13_prompt_v3_type,否则首次构造即
            # AttributeError)。
            _plan_v3_type = bool(
                self.plan.get("enable_v13_prompt_v3_type", False))
            _plan_v3_site = bool(
                self.plan.get("enable_v13_prompt_v3_site", False))
            if _plan_v3_type or _plan_v3_site:
                raise PPV1RunError(
                    "disable_atomtool_prompt 与 v1.3 分域提示词开关互斥"
                    "(同一 system prompt 槽位;fail-closed)",
                    {"kind": "disable_atomtool_prompt_v3_conflict",
                     "disable_atomtool_prompt": True,
                     "enable_v13_prompt_v3_type": _plan_v3_type,
                     "enable_v13_prompt_v3_site": _plan_v3_site})
            self.raw_novel_protocol = NOVEL_PROTOCOL_PRODUCT_FIRST
            self.novel_protocol = NOVEL_PROTOCOL_PRODUCT_FIRST
            self.format_feedback_policy_version = \
                format_feedback_policy_version_for(self.novel_protocol)
        # T10-A 开关 3/4：编译器表达扩展（电荷编辑 / 立体安全回退）。
        # 默认关闭；只有池编译阶段显式传参时生效（run 期不消费）。
        self.atom_tool_charge_ops = bool(
            self.plan.get("atom_tool_charge_ops", False)
        )
        self.stereo_edit_graceful_fallback = bool(
            self.plan.get("stereo_edit_graceful_fallback", False)
        )
        # v1.3 T8：分域提示词开关（默认关闭；两者互斥；只定义在原子编辑
        # 合同 + 无证据卡路径上 —— 其它组合 fail-closed，不静默混协议）
        self.enable_v13_prompt_v3_type = bool(
            self.plan.get("enable_v13_prompt_v3_type", False)
        )
        self.enable_v13_prompt_v3_site = bool(
            self.plan.get("enable_v13_prompt_v3_site", False)
        )
        # v1.3 T11：两段式反应大类分流（默认关闭）。完整两段 = Stage 1
        # 盲底物路由 + Stage 2 路由排序提案；stage1_only 只跑 Stage 1
        # 即落账返回（Step 1 的 457 题盲路由批用）。关闭 ⇒ 零字节漂移。
        self.enable_v13_two_stage_routing = bool(
            self.plan.get("enable_v13_two_stage_routing", False)
        )
        self.v13_routing_stage1_only = bool(
            self.plan.get("v13_routing_stage1_only", False)
        )
        # v1.3 T12-B：响应后 Stage-1 大类一致性精排（默认关）。开启时
        # 消费①运行自身 Stage-1 outcome（两段式路由批），否则②计划内
        # 注入的外部脱敏映射（零调用重放批：qid → primary/secondary）。
        # 两者都没有 ⇒ 该题不触发（原样返回,不改顺序）。
        self.enable_v13_stage1_rank_calibration = bool(
            self.plan.get("enable_v13_stage1_rank_calibration", False)
        )
        _ext_routing = self.plan.get("v13_stage1_routing_external")
        self.v13_stage1_routing_external: dict | None = None
        if isinstance(_ext_routing, dict):
            # 只留两个类键 + 显式来源标（计划里的其它字段不进事实链）
            self.v13_stage1_routing_external = {
                "primary_class": _ext_routing.get("primary_class"),
                "secondary_class": _ext_routing.get("secondary_class"),
                "source": "external_replay_map",
            }
        # T12 研究期参数覆盖（只由离线重放的 plan patch 注入；缺省 None
        # ⇒ 用 ranking_rules_v13.STAGE1_DEFAULT_PARAMS，生产默认不变）。
        _s1_params = self.plan.get("v13_stage1_rank_params")
        self.v13_stage1_rank_params: dict | None = (
            dict(_s1_params) if isinstance(_s1_params, dict) else None)
        # 研究期机读记录（默认空 ⇒ 不写任何文件；只由离线诊断脚本显式
        # 设置,不参与判据/不改行为）。
        self.v13_stage1_debug_dir = str(
            os.environ.get("V13_T12_STAGE1_DUMP_DIR") or "")
        # v1.3 T13-B：多采样一致性共识（默认关）。开启时消费计划注入的
        # 次级 pass（同题其他采样 run 的模型回复文本；零调用重放用）：
        # 每个次级 pass 重新解析 → 映射回本 run 的池逻辑键 → 与主 pass
        # 一起做 RRF + Stage-1 融合。关闭 ⇒ 零字节漂移。
        self.enable_v13_multi_sample_consensus = bool(
            self.plan.get("enable_v13_multi_sample_consensus", False)
        )
        _consensus_params = self.plan.get("v13_consensus_params")
        _base_consensus_params = (
            dict(_consensus_params)
            if isinstance(_consensus_params, dict) else None)
        # v1.4 T14-1A：plan 级开关是唯一生产入口（默认全 False ⇒ 参数
        # 维持 None/原值，与 v1.3 逐字节一致）。开关关闭时剔除研究参数
        # 里的 v1.4 键 ⇒ 不能靠 plan patch 绕过开关激活新机制。
        from ..services.consensus_v13 import consensus_params_from_plan

        self.enable_v14_equiv_product_consensus = bool(
            self.plan.get("enable_v14_equiv_product_consensus", False))
        self.enable_v14_novel_low_sim_boost = bool(
            self.plan.get("enable_v14_novel_low_sim_boost", False))
        self.enable_v14_raw_order_consensus = bool(
            self.plan.get("enable_v14_raw_order_consensus", False))
        # v1.4 T14-1B(默认关):run 期扩展编译器表达面(立体消解/安全
        # 回退/芳环裂解 + 稠环保留芳环)与次级 pass 池外 novel 对称回退。
        self.enable_v14_compiler_ext = bool(
            self.plan.get("enable_v14_compiler_ext", False))
        # v1.4 T14-4(默认关):编译器扩展面 v2(立体 parity 核验 + 芳环
        # 成键 v2)。与 v1 开关独立;两开关并集下发。
        self.enable_v14_compiler_ext_2 = bool(
            self.plan.get("enable_v14_compiler_ext_2", False))
        self.enable_v14_sec_novel_backfill = bool(
            self.plan.get("enable_v14_sec_novel_backfill", False))
        # v1.4 T14-4(默认关):跨池资格率归一化共识。只经共识参数/融合
        # 层消费;开关关 ⇒ 参数零注入、融合调用与改前逐字节同。
        self.enable_v14_cross_pool_elig_norm = bool(
            self.plan.get("enable_v14_cross_pool_elig_norm", False))
        self.enable_v14_multipass_consensus_v3 = bool(
            self.plan.get("enable_v14_multipass_consensus_v3", False))
        # v1.4 T14-3（默认关）：成对互换机理裁决重排。开关关闭时**强制**
        # 丢弃 plan 里的 ``v14_adjudication_external``（plan 残留键不得绕过
        # 开关）；打开时只提取白名单脱敏字段（verdict / defender_sha256 /
        # challenger_sha256 / order_sha256s / gate_tag）。
        self.enable_v14_pairwise_adjudication = bool(
            self.plan.get("enable_v14_pairwise_adjudication", False))
        self.v14_adjudication_external: dict | None = None
        if self.enable_v14_pairwise_adjudication:
            from ..services.adjudication_v14 import (
                sanitize_adjudication_external,
            )

            self.v14_adjudication_external = sanitize_adjudication_external(
                self.plan.get("v14_adjudication_external"))
        self.v13_consensus_params: dict | None = consensus_params_from_plan(
            self.plan, _base_consensus_params)
        self.v13_consensus_secondary_passes: list[dict] = []
        _raw_sec_passes = self.plan.get("v13_consensus_secondary_passes")
        if isinstance(_raw_sec_passes, list):
            for _item in _raw_sec_passes:
                if isinstance(_item, dict):
                    _content = str(_item.get("content") or "")
                    if not _content.strip():
                        continue
                    _pass: dict = {
                        "run_id": str(_item.get("run_id") or ""),
                        "content": _content,
                    }
                    # v1.4 T14-1A：跨池/零池次级 pass 的可选同源池输入
                    # （缺省不出现 ⇒ 与 v1.3 映射路径 100% 相同）。
                    if "sec_pool_specs" in _item:
                        _pass["sec_pool_specs"] = _item.get("sec_pool_specs")
                    if "sec_pools" in _item:
                        _pass["sec_pools"] = _item.get("sec_pools")
                    if "allow_verified_sec_pool_promotion" in _item:
                        _pass["allow_verified_sec_pool_promotion"] = bool(
                            _item.get("allow_verified_sec_pool_promotion"))
                    self.v13_consensus_secondary_passes.append(_pass)
                elif isinstance(_item, str) and _item.strip():
                    self.v13_consensus_secondary_passes.append({
                        "run_id": "", "content": _item})
        if self.enable_v13_multi_sample_consensus:
            if self.enable_v13_stage1_rank_calibration:
                # 两个机制消费同一 Stage-1 信号；同时开会在单 pass 末尾
                # 先精排、再融合（同一信号双计）⇒ 不混臂，fail-closed。
                raise PPV1RunError(
                    "多采样共识与响应后 Stage-1 精排不得同时打开"
                    "(同一 Stage-1 信号双计;fail-closed)",
                    {"kind": "v13_consensus_stage1_conflict",
                     "enable_v13_multi_sample_consensus": True,
                     "enable_v13_stage1_rank_calibration": True})
            if not self.enable_smart_gated_backfill:
                # calibrate_submittable_ranking 只挂在回复后机制链上；
                # 共识没有排序链可挂 ⇒ fail-closed(不静默空转)。
                raise PPV1RunError(
                    "多采样共识只定义在 enable_smart_gated_backfill 的"
                    "回复后排序链上(当前未打开;fail-closed)",
                    {"kind": "v13_consensus_requires_backfill",
                     "enable_v13_multi_sample_consensus": True,
                     "enable_smart_gated_backfill": False})
        if self.v13_routing_stage1_only and \
                not self.enable_v13_two_stage_routing:
            raise PPV1RunError(
                "v13_routing_stage1_only 必须与 "
                "enable_v13_two_stage_routing 同时打开(fail-closed)",
                {"kind": "two_stage_routing_switch_conflict",
                 "enable_v13_two_stage_routing": False,
                 "v13_routing_stage1_only": True})
        if (self.enable_v13_two_stage_routing
                or self.v13_routing_stage1_only) and (
                self.novel_protocol != NOVEL_PROTOCOL_ATOM_EDIT
                or self.evidence_card_version is not None
                or self.enable_v13_prompt_v3_type
                or self.enable_v13_prompt_v3_site):
            raise PPV1RunError(
                "两段式路由只定义在原子编辑合同 + 无证据卡 + 非分域"
                "提示词路径上(当前组合不兼容;fail-closed,不混协议)",
                {"kind": "two_stage_routing_path_conflict",
                 "novel_protocol": self.novel_protocol,
                 "evidence_card_version": self.evidence_card_version,
                 "enable_v13_prompt_v3_type":
                     self.enable_v13_prompt_v3_type,
                 "enable_v13_prompt_v3_site":
                     self.enable_v13_prompt_v3_site})
        if self.enable_v13_prompt_v3_type and \
                self.enable_v13_prompt_v3_site:
            raise PPV1RunError(
                "分域提示词开关同时打开(v3_type 与 v3_site 互斥;"
                "fail-closed)",
                {"kind": "prompt_v3_switch_conflict",
                 "enable_v13_prompt_v3_type": True,
                 "enable_v13_prompt_v3_site": True})
        if (self.enable_v13_prompt_v3_type
                or self.enable_v13_prompt_v3_site) and (
                self.novel_protocol != NOVEL_PROTOCOL_ATOM_EDIT
                or self.evidence_card_version is not None):
            raise PPV1RunError(
                "分域提示词只定义在原子编辑合同 + 无证据卡路径上"
                "(当前组合不兼容;fail-closed,不混协议)",
                {"kind": "prompt_v3_path_conflict",
                 "novel_protocol": self.novel_protocol,
                 "evidence_card_version": self.evidence_card_version})
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
        # EXP1 C 臂(2026-11-06):第①阶段(盲写)已核验并 prepared 的
        # 条目登记(索引 = 本次 _run_decide 的 prepared_entries 下标;
        # _run_decide 按索引标 novel_entry_idx,不按字串猜来源身份)。
        self.blind_entries: list[dict] = []

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
        稳定次序:created_at, action_id(**判据一字不动**;W-V1
        s5b-submit-order-1 后 created_at 为本 run 严格单调递增微秒
        装配 ⇒ 本序忠实返回调度入队序=effective_rank 序,同秒
        action_id 哈希 tie-break 形态消除——事件提交序=调度序)。"""
        rows = self.ledger.conn.execute(
            "SELECT action_id FROM search_actions WHERE run_id = ? AND"
            " (status = ? OR (status = ? AND claimed_by = ?))"
            " ORDER BY created_at, action_id",
            (self.run_id, "pending", "claimed", self.worker_id)).fetchall()
        return [str(r["action_id"]) for r in rows]

    def drive(self) -> dict:
        self.reconcile_followups()
        activations_applied = False
        # T10-A 开关 2:预算拒的 action 记入跳过集(不阻断其它在途
        # action —— 已认领且已 responded 的付费响应必须在停止前消费完);
        # 开关关闭时该集恒空,控制流与改前逐字节同。
        budget_skipped: set[str] = set()
        while True:
            pending = [a for a in self._inflight_action_ids()
                       if a not in budget_skipped]
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
                if self.fix_budget_limit_consumption:
                    # 跳过该 pending action,继续尝试其它在途 action
                    budget_skipped.add(action_id)
                    if any(a not in budget_skipped
                           for a in self._inflight_action_ids()):
                        continue
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
            feedback_policy_version=self.format_feedback_policy_version)
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
        # C 臂:本次 decide 的盲写条目索引只对本次 prepared_entries 有效
        # (不跨 decide 复用;A/B 臂零读)
        self.blind_entries = []
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
            if self.enable_smart_gated_backfill:
                try:
                    prepared = prepare_hypothesis(
                        spec, parent_path_id=receipt["parent_path_id"],
                        substrate_state=substrate,
                        transformation_ref=str(spec.get("transformation_ref")
                                                or ""))
                except Exception:
                    continue
            else:
                prepared = prepare_hypothesis(
                    spec, parent_path_id=receipt["parent_path_id"],
                    substrate_state=substrate,
                    transformation_ref=str(spec.get("transformation_ref")
                                            or ""))
            prepared_entries.append((key, spec, prepared))
        model_note: dict = {}
        if self.plan.get("model"):
            try:
                model_note = self._model_proposals(
                    receipt, prepared_entries,
                    substrate_profile=substrate_profile)
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
        # ---- PC8(CC 2026-11-06):产物优先分支(B/C 两臂)对模型自写
        # 池侧声明键的忽略记录汇总进 note(条目级 ignored_spec_keys 已由
        # _verify_novel_product_first 传播);A 臂无该字段 ⇒ 零新键。 ----
        _ignored_note: dict[str, list[str]] = {}
        for _item in ((model_note.get("novel_compiled") or [])
                      + (model_note.get("declared_bucket") or [])):
            if isinstance(_item, dict) and _item.get("ignored_spec_keys"):
                _ignored_note[str(_item.get("hypothesis_id") or "")] = [
                    str(_key) for _key in _item["ignored_spec_keys"]]
        if _ignored_note:
            # P1-3 回修:与臂内跨轮累积取**并集**(同 ID 的早轮键名不因
            # 末轮条目更短而丢失;条目级列表仍是解析层同源键名)。
            _merged_ignored: dict[str, set[str]] = {}
            for _source in (model_note.get("novel_ignored_spec_keys") or {},
                            _ignored_note):
                for _key, _values in _source.items():
                    _merged_ignored.setdefault(str(_key), set()).update(
                        str(_value) for _value in (_values or []))
            model_note["novel_ignored_spec_keys"] = {
                _key: sorted(_merged_ignored[_key])
                for _key in sorted(_merged_ignored)
                if _merged_ignored[_key]}
        # ---- S3B-05:novel 池外提案的独立假设消费(经 prepare_
        # hypothesis 单一构建源;来源经 proposal_context 明示入冻结
        # 任务输入)----
        # W5(有限容错):单条 novel 提案的 reaction_spec 非法(结构/
        # 契约)在共同 prevalidation **逐条拒并保留合法候选** —— 一坏
        # 一合法是正控;全坏如实 empty(不 run 拒)。整 JSON 不可解析、
        # 权威记录损坏、真正 audit/store 契约违规仍 run 拒(不走本容
        # 错;不能 catch-all 把损坏洗成方法失败)。
        novel_by_key: dict[str, dict] = {}
        novel_rejections: list[dict] = []
        # T-F 回修(Codex P1,2026-10-17):novel 自报 ID 与池逻辑 key 合法
        # 同名时两表按字串查会错读来源 ⇒ 条目进入继承计算须带来源身份
        novel_entry_idx: set[int] = set()
        # W5:共同 prevalidation —— 同一 render 事实源逐条 validate_edits
        # (坏引用/未知 op/非法 ID 在 decide 层逐条拒,不留到执行层)
        from ..services.atom_tool import render as _render, \
            validate_edits as _validate_edits

        try:
            _current_render = _render(substrate_smiles, "S")
        except Exception:  # noqa: BLE001 —— 底物渲染失败走 run 级失败
            _current_render = None
        # EXP1(E8):product_first 消费 E7 的 novel_compiled(编译后的
        # 完整 spec,含 edits;只含 full 级 —— declared 桶不进事件);
        # A 臂继续消费模型原样 reaction_spec(逐字节不变)。
        if self.novel_protocol == NOVEL_PROTOCOL_PRODUCT_FIRST:
            novel_items = []
            for item in (model_note.get("novel_compiled") or []):
                entry = dict(item)
                entry["source_ref_record"] = (
                    "novel-model-proposal:product_first:"
                    f"{entry.get('verification_tier') or 'full'}")
                novel_items.append(entry)
        elif self.novel_protocol == NOVEL_PROTOCOL_BLIND_FIRST:
            # C 臂:第①阶段盲写条目已在 _model_proposals_blind_first
            # 中预校验 + prepare 并就地追加(不重复 prepare);这里按
            # **索引**标来源身份,并以 **prepared hypothesis ID** 作其
            # 逻辑提案身份(自报 ID 与池 key/合并阶段新提案可合法同名;
            # 位次只认合并阶段 prepared ID,自报 ID 仅披露 —— P1-1
            # 回修 2026-11-06)。
            for blind in self.blind_entries:
                index = int(blind["index"])
                if 0 <= index < len(prepared_entries):
                    novel_entry_idx.add(index)
                    prepared_blind_id = str(
                        blind["prepared_hypothesis_id"])
                    novel_by_key[prepared_blind_id] = {
                        "hypothesis_id": prepared_blind_id,
                        "proposal_context": dict(
                            blind.get("proposal_context") or {}),
                        "reaction_spec": dict(
                            blind.get("reaction_spec") or {}),
                    }
            novel_items = []
            for item in (model_note.get("novel_compiled") or []):
                entry = dict(item)
                entry["source_ref_record"] = (
                    "novel-model-proposal:product_first:"
                    f"{entry.get('verification_tier') or 'full'}")
                novel_items.append(entry)
        else:
            novel_items = [dict(p) for p in
                           (model_note.get("novel_proposals") or [])]
        # P1-1 回修(2026-11-06):合并阶段新 novel 的**自报 ID → prepared
        # hypothesis ID** 翻译表(C 臂位次披露用;A/B 臂只登记不使用)。
        novel_prepared_id_by_self_report: dict[str, str] = {}
        for novel_idx, proposal in enumerate(novel_items, 1):
            reaction_spec = dict(proposal["reaction_spec"])
            novel_key = str(proposal.get("hypothesis_id") or "")
            origin = str((proposal.get("proposal_context") or {}).get(
                "output_origin") or "novel_outside_pool")
            source_ref_record = str(
                proposal.get("source_ref_record")
                or f"novel-model-proposal:{origin}")

            # 池外 novel 双路编译：当开启 v44-next (enable_smart_gated_backfill) 时，
            # 优先尝试模型给出的 atom_edit 预检 + prepare + execute + audit；
            # 若 atom_edit 失败或未产主产物，但存在可解析的目标产物 SMILES，自动回退调用
            # compile_s5_candidate_to_spec 将其编译为合规 ReactionSpec。
            if self.enable_smart_gated_backfill:
                prepared = None
                effective_spec = reaction_spec
                edit_list = reaction_spec.get("edits") or []
                edit_ok = bool(edit_list)
                if edit_ok and _current_render is not None:
                    verdict = _validate_edits(_current_render, edit_list)
                    edit_ok = bool(verdict.get("ok"))
                if edit_ok:
                    # T10-A 开关 1:补 execute_atomtool_expansion 的局部
                    # 导入。改前该符号在 _run_decide 作用域未绑定 ⇒ atom_edit
                    # 优先路径恒抛 NameError(prepared=None)并静默回退产物优先
                    # 编译。默认关闭时仍走原名(保持既有 NameError 行为);
                    # 打开时才真正尝试 atom_edit 先行。
                    _atomtool_expand = None
                    if self.fix_decide_atomtool_import:
                        from .production import (
                            execute_atomtool_expansion as _atomtool_expand,
                        )
                    try:
                        cand_prep = prepare_hypothesis(
                            reaction_spec,
                            parent_path_id=receipt["parent_path_id"],
                            substrate_state=substrate,
                            transformation_ref=str(
                                reaction_spec.get("transformation_ref") or ""),
                            source_refs=[{"record": source_ref_record}])
                        exec_in = str(
                            cand_prep["tool_inputs"].get("execution_input_smiles")
                            or substrate.smiles_isomeric
                        )
                        if _atomtool_expand is not None:
                            exec_out = _atomtool_expand(
                                substrate_smiles=exec_in,
                                tool_inputs=cand_prep["tool_inputs"],
                            )
                        else:
                            # 改前行为:未导入 ⇒ NameError(外层 except 收敛
                            # 为 prepared=None,路径守恒)
                            exec_out = execute_atomtool_expansion(
                                substrate_smiles=exec_in,
                                tool_inputs=cand_prep["tool_inputs"],
                            )
                        if exec_out.get("execution_ok"):
                            from .audit import audit_hypothesis, decide_admission
                            from .production import ADMISSION_SUBMITTABLE

                            audit_rep = audit_hypothesis(
                                cand_prep["hypothesis"],
                                run_id="v44-novel-check",
                                states=cand_prep["states"],
                                context=parent_ctx,
                                center_evidence=exec_out["center_evidence"],
                            )
                            disp, _ = decide_admission(audit_rep)
                            if disp in ADMISSION_SUBMITTABLE:
                                if self.fix_decide_atomtool_import:
                                    # 防回归硬规则(T4-A3 教训):落库结构
                                    # product_states 必须严格身份多重集覆盖
                                    # 模型声明产物 + 共产物;不覆盖 ⇒ 回退产物
                                    # 优先编译(不朴素拒绝 coproduct,也不放宽
                                    # 身份)。
                                    _cov = _declared_consistency_report(
                                        cand_prep,
                                        str(reaction_spec.get(
                                            "product_smiles") or ""),
                                        [str(c) for c in
                                         (reaction_spec.get(
                                             "coproducts") or [])],
                                        reaction_spec)
                                    # 叠加执行侧同源核验:声明产物必须是
                                    # 实际执行产物(product_states 由声明
                                    # 构建,单看它无法发现「声明≠执行」)。
                                    _exec_cov = _execution_declaration_mismatch(
                                        exec_out,
                                        [str(reaction_spec.get(
                                            "product_smiles") or "")]
                                        + [str(c) for c in
                                           (reaction_spec.get(
                                               "coproducts") or [])])
                                    if _cov.get("covered") and not _exec_cov:
                                        prepared = cand_prep
                                        model_note.setdefault(
                                            "v13_atomtool_prepared",
                                            []).append({
                                                "hypothesis_id": novel_key})
                                    else:
                                        model_note.setdefault(
                                            "v13_atomtool_coverage_rejects",
                                            []).append({
                                                "hypothesis_id": novel_key,
                                                "reason": str(
                                                    _exec_cov.get("reason")
                                                    or _cov.get("reason")
                                                    or "")})
                                else:
                                    prepared = cand_prep
                    except Exception:
                        prepared = None

                if prepared is None and not self.disable_product_first_fallback:
                    # 论文消融 v1.4 ③:disable_product_first_fallback=True
                    # 时整段产物优先逆向图差编译回退不执行(池外 novel
                    # 只能靠模型正向手写 AtomTool edits 过安检门)。
                    expect_dict = reaction_spec.get("expectation")
                    expect_smi = (
                        expect_dict.get("target_smiles")
                        if isinstance(expect_dict, dict)
                        else ""
                    )
                    exp_prods = reaction_spec.get("expected_products") or proposal.get("expected_products")
                    first_exp_prod = (
                        str(exp_prods[0]).strip()
                        if isinstance(exp_prods, list) and exp_prods
                        else ""
                    )
                    target_prod_smi = str(
                        reaction_spec.get("product_smiles")
                        or reaction_spec.get("target_product_smiles")
                        or expect_smi
                        or first_exp_prod
                        or proposal.get("product_smiles")
                        or proposal.get("target_product_smiles")
                        or ""
                    ).strip()
                    raw_cops = (
                        reaction_spec.get("coproducts")
                        or proposal.get("coproducts")
                        or []
                    )
                    cop_sets = (
                        [[str(c).strip() for c in raw_cops if str(c).strip()]]
                        if isinstance(raw_cops, list) and raw_cops
                        else None
                    )
                    if target_prod_smi:
                        from ..services.s5_hybrid_choice import (
                            compile_s5_candidate_to_spec,
                        )

                        fb_spec = compile_s5_candidate_to_spec(
                            substrate.smiles_isomeric,
                            {"cand_smiles": target_prod_smi},
                            index=80 + novel_idx,
                            is_gated_supplement=False,
                            coproduct_sets=cop_sets,
                            extended_stereo_dissolution=bool(
                                self.enable_v13_stereo_dissolution_extended
                                or self.enable_v14_compiler_ext),
                            stereo_edit_graceful_fallback=bool(
                                self.enable_v14_compiler_ext),
                            allow_ring_cleavage_and_fused_dearomatization=(
                                bool(self.enable_v14_compiler_ext)),
                            # v1.4 T14-4:编译器 v2 两开关(默认关 ⇒
                            # 调用参数逐字节同)
                            retained_tetrahedral_parity_check=bool(
                                self.enable_v14_compiler_ext_2),
                            allow_aromatic_ring_closure=bool(
                                self.enable_v14_compiler_ext_2),
                        )
                        if fb_spec is None and cop_sets and self.enable_v14_compiler_ext_2:
                            # v1.4 T14-4:主/次 pass novel 对称回补 ——
                            # 声明共产物导致编译失败时,回退为「只按主
                            # 产物」再试一次(共产物由编译器按产物优先
                            # 规则推断;不新增任何判据)。
                            fb_spec = compile_s5_candidate_to_spec(
                                substrate.smiles_isomeric,
                                {"cand_smiles": target_prod_smi},
                                index=80 + novel_idx,
                                is_gated_supplement=False,
                                coproduct_sets=None,
                                extended_stereo_dissolution=bool(
                                    self.enable_v13_stereo_dissolution_extended
                                    or self.enable_v14_compiler_ext),
                                stereo_edit_graceful_fallback=bool(
                                    self.enable_v14_compiler_ext),
                                allow_ring_cleavage_and_fused_dearomatization=(
                                    bool(self.enable_v14_compiler_ext)),
                                retained_tetrahedral_parity_check=bool(
                                    self.enable_v14_compiler_ext_2),
                                allow_aromatic_ring_closure=bool(
                                    self.enable_v14_compiler_ext_2),
                            )
                        if fb_spec is not None:
                            fb_spec["key"] = novel_key
                            fb_spec["transformation_ref"] = str(
                                reaction_spec.get("transformation_ref")
                                or fb_spec.get("transformation_ref")
                                or f"novel-pf:{novel_key}"
                            )
                            try:
                                prepared = prepare_hypothesis(
                                    fb_spec,
                                    parent_path_id=receipt["parent_path_id"],
                                    substrate_state=substrate,
                                    transformation_ref=str(
                                        fb_spec.get("transformation_ref") or ""
                                    ),
                                    source_refs=[{"record": source_ref_record}],
                                )
                                effective_spec = fb_spec
                            except Exception:
                                prepared = None

                        # v1.3 T1-D novel 吸附：atom_edit 与产物直编都失败时，
                        # 把目标产物吸附到通用枚举器最相近的合法产物再编译
                        # 一次。默认关闭；枚举清单不进提示词，可零调用评估。
                        if prepared is None and self.enable_v13_generic_enumeration:
                            from ..services.generic_enumerator import (
                                adsorb_to_enumeration,
                            )

                            adsorption = adsorb_to_enumeration(
                                substrate.smiles_isomeric, target_prod_smi)
                            if adsorption is not None:
                                ads_spec = compile_s5_candidate_to_spec(
                                    substrate.smiles_isomeric,
                                    {"cand_smiles": adsorption["adsorbed_smiles"]},
                                    index=160 + novel_idx,
                                    is_gated_supplement=False,
                                    coproduct_sets=None,
                                    extended_stereo_dissolution=(
                                        self.enable_v13_stereo_dissolution_extended),
                                    # v1.4 T14-4:编译器 v2 两开关(默认关
                                    # ⇒ 调用参数逐字节同)
                                    retained_tetrahedral_parity_check=bool(
                                        self.enable_v14_compiler_ext_2),
                                    allow_aromatic_ring_closure=bool(
                                        self.enable_v14_compiler_ext_2),
                                )
                                if ads_spec is not None:
                                    ads_spec["key"] = novel_key
                                    ads_spec["transformation_ref"] = str(
                                        reaction_spec.get("transformation_ref")
                                        or f"novel-pf:{novel_key}"
                                    )
                                    try:
                                        prepared = prepare_hypothesis(
                                            ads_spec,
                                            parent_path_id=receipt[
                                                "parent_path_id"],
                                            substrate_state=substrate,
                                            transformation_ref=str(
                                                ads_spec.get(
                                                    "transformation_ref") or ""
                                            ),
                                            source_refs=[{
                                                "record": source_ref_record}],
                                        )
                                        effective_spec = ads_spec
                                    except Exception:
                                        prepared = None
                                model_note.setdefault(
                                    "v13_enumeration_adsorptions", []).append({
                                        "hypothesis_id": novel_key,
                                        "target_smiles": adsorption[
                                            "target_smiles"],
                                        "adsorbed_smiles": adsorption[
                                            "adsorbed_smiles"],
                                        "similarity": adsorption["similarity"],
                                        "compiled": prepared is not None,
                                    })

                if prepared is None:
                    if self.disable_product_first_fallback:
                        # 论文消融 v1.4 ③:回退通道被显式关断 ⇒ 如实
                        # 记录拒绝原因(不是"双路都编译失败",而是
                        # "回退被消融")。
                        novel_rejections.append({
                            "hypothesis_id": novel_key,
                            "kind": "product_first_fallback_disabled",
                            "reasons": [
                                "atom_edit_not_prepared_and_product_first_"
                                "fallback_disabled"]})
                    else:
                        novel_rejections.append({
                            "hypothesis_id": novel_key,
                            "kind": "novel_dual_path_compilation_failed",
                            "reasons": ["atom_edit_and_product_first_fallback_failed"]})
                    continue

                if self.enable_v13_declared_product_consistency:
                    # v1.3 T4-A:落库结构 vs 模型声明产物的一致性**披露**
                    # (严格身份多重集包含;只写机读记录,不拒提案、不改
                    # 排序 —— 拒提案会误杀「编译 spec 少了共产物、但执行
                    # 器补齐后事件仍命中」的真命中,见 T4 报告 A3 节)。
                    consistency = _declared_consistency_report(
                        prepared,
                        str(reaction_spec.get("product_smiles") or ""),
                        [str(c) for c in
                         (reaction_spec.get("coproducts") or [])],
                        effective_spec)
                    consistency["hypothesis_id"] = novel_key
                    model_note.setdefault(
                        "v13_declared_consistency_mismatches",
                        []).append(consistency)

                prepared_entries.append((novel_key, effective_spec, prepared))
                novel_entry_idx.add(len(prepared_entries) - 1)
                novel_by_key[novel_key] = proposal
                novel_prepared_id_by_self_report[novel_key] = str(
                    prepared["hypothesis"].hypothesis_id)
                continue

            if _current_render is not None:
                verdict = _validate_edits(
                    _current_render,
                    reaction_spec.get("edits") or [])
                if not verdict.get("ok"):
                    novel_rejections.append({
                        "hypothesis_id": novel_key,
                        "kind": "novel_edit_prevalidation_failed",
                        "reasons": verdict.get("reasons", [])[:6]})
                    continue
            try:
                prepared = prepare_hypothesis(
                    reaction_spec,
                    parent_path_id=receipt["parent_path_id"],
                    substrate_state=substrate,
                    transformation_ref=str(
                        reaction_spec.get("transformation_ref") or ""),
                    source_refs=[{"record": source_ref_record}])
            except (PPV1RunError, SearchContractError,
                    HypothesisContractError, ChemicalStateError) as exc:
                _detail = getattr(exc, "detail", None)
                _kind = ""
                if isinstance(_detail, dict):
                    _kind = str(_detail.get("kind") or "")
                novel_rejections.append({
                    "hypothesis_id": novel_key,
                    "kind": _kind or type(exc).__name__,
                    "reason": str(exc)[:200]})
                continue
            # 非回填入口:直接消费模型自己的 reaction_spec(声明 == 消费
            # 的结构,无替换),声明一致性门在此**平凡成立**;有替换风险
            # 的入口是上面的产物优先回退编译,门设在那里。
            prepared_entries.append((novel_key, reaction_spec, prepared))
            novel_entry_idx.add(len(prepared_entries) - 1)
            novel_by_key[novel_key] = proposal
            novel_prepared_id_by_self_report[novel_key] = str(
                prepared["hypothesis"].hypothesis_id)
        if novel_rejections:
            model_note["novel_rejections"] = novel_rejections
        if not prepared_entries:
            # 有效候选集为空(池空且模型弃权/无 novel):no_local_
            # candidate 如实落账(不改上游真假)
            # P0-3(2026-11-07):空池 no_local_candidate 分支挂 detail.model
            self.empty_pool_retrievals += 1
            source_event_id = str(payload.get("source_event_id") or "")
            no_cand_detail: dict = {
                "substrate_smiles": substrate_smiles,
                "source_event_id": source_event_id,
                "unresolved_continuation": bool(source_event_id),
                "note": ("检索/池与模型提案均无候选;不反证"
                         "上游;按稳定次序继续可用备选"),
            }
            if model_note:
                no_cand_detail["model"] = {
                    k: v for k, v in model_note.items()
                    if k not in ("rank_by_key", "_earliest_pool_rank_by_id")}
            _complete_action(
                self.ledger, receipt["action_id"],
                worker_id=self.worker_id,
                outcome={"kind": OUTCOME_KIND_NO_LOCAL_CANDIDATE,
                         "detail": no_cand_detail},
                evidence_refs=[source_event_id] if source_event_id else [])
            return
        # ---- v1.3 T13-B：次级 pass（同题其他采样 run 的零调用回复）→
        # 本 run 逻辑键排序表。必须在去重之前落地：次级 novel 经程序
        # 编译核验后作为新条目参与本轮去重/排序/落账（零放宽：只消费
        # 既有核验链的 full 级候选；解析失败只减少该 pass 贡献）。
        _consensus_sec_keys: list[list[str]] = []
        _consensus_sec_debug: dict = {}
        # v1.4 T14-4：与次级排序表 1:1 的每 pass 资格键集合（默认路径
        # 下仍采集，但只有 plan 开关打开时下游才消费）。
        _consensus_sec_elig: list[list[str] | None] = []
        _sec_novel_idx: set[int] = set()
        if self.enable_v13_multi_sample_consensus:
            _pre_sec_novel_idx = set(novel_entry_idx)
            _consensus_sec_keys, _consensus_sec_debug = \
                self._secondary_consensus_ranked_keys(
                    substrate_smiles=substrate_smiles,
                    substrate=substrate,
                    receipt=receipt,
                    specs=specs,
                    prepared_entries=prepared_entries,
                    novel_entry_idx=novel_entry_idx,
                    novel_by_key=novel_by_key)
            _consensus_sec_elig = [
                (None if _el is None else [str(_k) for _k in _el])
                for _el in (
                    _consensus_sec_debug.get(
                        "secondary_eligible_keys_list") or [])]
            _sec_novel_idx = set(novel_entry_idx) - _pre_sec_novel_idx
        rank_by_key = model_note.get("rank_by_key") or {}
        # ---- W3(S5b rank-policy-1):统一选择排序规则(版本化) ----
        # logical proposal ID(池 spec key / novel hypothesis_id)→
        # prepared hypothesis ID → 净反应签名(去重/合并 provenance)→
        # effective_rank → 实际提交事件:
        # - **模型选择**:parsed rank_hypotheses 的显式位次(model_rank,
        #   1 起始;novel 与池条目同权 —— novel 不因来源被排后);
        # - **确定性 fallback**:未获显式 rank 的条目按池声明序 + novel
        #   提案序;
        # - **全部显式有效 rank 先于一切未 rank fallback**(模型未选
        #   的池条目不隐式抢前 5;旧实现未 rank 池条目按池 index+1 落
        #   位,可与模型位次冲突甚至反超 —— 已证源码问题);
        # - 去重:同净反应签名(严格产物多重集)的后续条目折叠,合并
        #   provenance;不同反应/条件/角色不因主产物或 CN 相同被误并;
        # - 不在 score 后重排事件;成功 root 事件按实际 (created_at,
        #   event_id) 供原 scorer 计 K(提交序 = 高分辨率 created_at,
        #   store 公共 writer 忠实记录)。
        from .s5b_compiler import net_reaction_signature

        # W3 位次继承(s5b-rank-policy-2;Codex 回修 2026-10-17 P1):
        # 声明位次查表按**条目来源**分流——池条目读 rank_by_key(池逻辑
        # 键表),novel 条目读 model_rank_by_id(模型原始 ID 表);两表
        # 命名空间不同,novel 自报 ID 与池 key 合法同名时按字串优先级
        # 查表会错读来源(反例:首位 novel 被读成池条目位次,继承失效)
        model_rank_by_id_pre = {
            str(k): int(v)
            for k, v in (model_note.get("model_rank_by_id")
                         or {}).items()}
        if self.novel_protocol == NOVEL_PROTOCOL_BLIND_FIRST:
            # P1-1 回修:C 臂合并阶段位次词表 = **prepared hypothesis ID**
            # (池/盲写条目在合并载荷里就以此 ID 出现)∪ 合并新 novel 的
            # 自报 ID(模型只能用它引用自己新提的那条;prepared ID 在
            # prepare 之后才存在)。self_report 表仅在此查表里补位,
            # 不覆盖已命中的 prepared ID(同名时新提案优先)。
            for _sid, _item in (
                    model_note.get("model_rank_self_reported_ids")
                    or {}).items():
                _pos = (_item.get("position") if isinstance(_item, dict)
                        else _item)
                if _pos is None:
                    continue
                model_rank_by_id_pre.setdefault(str(_sid), int(_pos))

        def _declared_rank(entry_idx: int, k: str):
            if entry_idx in novel_entry_idx:
                return model_rank_by_id_pre.get(k)
            if k in (rank_by_key or {}):
                return int(rank_by_key[k])
            return None

        if self.novel_protocol == NOVEL_PROTOCOL_BLIND_FIRST:
            # ---- C 臂位次披露重写(prepared ID 命名空间;P1-1) ----
            # 记录面只保留 prepared hypothesis ID → 合并位次:
            #   * 池条目 / 盲写条目:合并 rank 里的 ID 本身就是 prepared ID;
            #   * 合并新 novel:自报 ID 在 prepare 后翻译为其 prepared ID;
            #   * 盲写条目的自报 ID 仅在「合并响应没有同名新提案」时作
            #     别名披露(PC2 既有断言面);同名 ⇒ 新提案优先,别名不写。
            # 位次解析已在上面的 _declared_rank / 本次重写前完成
            # (model_rank_by_id_pre 是原始查询表,不受本重写影响)。
            _prepared_ids = {
                str(prepared["hypothesis"].hypothesis_id)
                for _, _, prepared in prepared_entries}
            _rank_prepared: dict[str, int] = {
                _rid: int(_pos) for _rid, _pos in model_rank_by_id_pre.items()
                if _rid in _prepared_ids}
            for _sid, _pid in novel_prepared_id_by_self_report.items():
                if _sid in model_rank_by_id_pre and _pid in _prepared_ids:
                    _rank_prepared[_pid] = int(model_rank_by_id_pre[_sid])
            _merge_self_report_ids = {
                _sid for _sid in model_rank_by_id_pre
                if _sid not in _prepared_ids}
            for _blind in self.blind_entries:
                _sid = str(_blind["hypothesis_id"])
                _pid = str(_blind["prepared_hypothesis_id"])
                if _sid in _merge_self_report_ids or _sid in _rank_prepared:
                    continue
                if _pid in _rank_prepared:
                    _rank_prepared[_sid] = _rank_prepared[_pid]
            model_note["model_rank_by_id"] = {
                _rid: _rank_prepared[_rid]
                for _rid in sorted(_rank_prepared,
                                   key=lambda _k: (_rank_prepared[_k], _k))}
            _self_report_disclosure = {
                _sid: {
                    "position": int(_pos),
                    "prepared_hypothesis_id":
                        novel_prepared_id_by_self_report.get(_sid, "")}
                for _sid, _pos in model_rank_by_id_pre.items()
                if _sid not in _prepared_ids}
            if _self_report_disclosure:
                model_note["model_rank_self_reported_ids"] = {
                    _sid: _self_report_disclosure[_sid]
                    for _sid in sorted(
                        _self_report_disclosure,
                        key=lambda _k: (
                            _self_report_disclosure[_k]["position"], _k))}

        # ---- P0-1(2026-11-07):跨轮保留条目与 C 臂盲写条目的排序合成 ----
        # Tier 0: 末轮显式排序且合法的条目(model_rank_by_key);
        # Tier 1: 早轮通过、末轮未复述的条目,按(首次通过轮次, 该轮内位次)追加;
        # Tier 2: C 臂盲写通过、合并轮未复述的条目(排在显式排序的池条目之后、
        #         未排序池条目之前);
        # Tier 3: 未被任何轮显式排序的池条目最后。
        earliest_pool_rank_by_id = dict(
            model_note.get("_earliest_pool_rank_by_id") or {})
        blind_info_by_idx: dict[int, dict] = {
            int(b["index"]): b for b in self.blind_entries
            if 0 <= int(b["index"]) < len(prepared_entries)}
        blind_idx_set: set[int] = set(blind_info_by_idx)
        retention_by_idx: dict[int, tuple] = {}
        for _eidx, (_ekey, _espec, _eprepared) in enumerate(prepared_entries):
            _epid = str(_eprepared["hypothesis"].hypothesis_id)
            if _eidx in blind_info_by_idx:
                if _epid in earliest_pool_rank_by_id:
                    _er, _epos = earliest_pool_rank_by_id[_epid]
                    retention_by_idx[_eidx] = (1, int(_er), int(_epos), _eidx)
                else:
                    _binfo = blind_info_by_idx[_eidx]
                    retention_by_idx[_eidx] = (
                        2,
                        int(_binfo.get("blind_tier", 1)),
                        int(_binfo.get("first_pass_round", 0)),
                        int(_binfo.get("first_pass_pos", _eidx + 1)),
                        _eidx,
                    )
            elif _eidx in novel_entry_idx:
                _nprop = novel_by_key.get(_ekey) or {}
                if "first_pass_round" in _nprop:
                    retention_by_idx[_eidx] = (
                        1,
                        int(_nprop.get("first_pass_round", 0)),
                        int(_nprop.get("first_pass_pos", _eidx + 1)),
                        _eidx,
                    )
            else:
                if _epid in earliest_pool_rank_by_id:
                    _er, _epos = earliest_pool_rank_by_id[_epid]
                    retention_by_idx[_eidx] = (1, int(_er), int(_epos), _eidx)

        pre_dedup_novel_stricts: set[str] = set()
        if self.enable_smart_gated_backfill:
            for _pidx, (_pkey, _pspec, _pprep) in enumerate(prepared_entries):
                if (_pidx in novel_entry_idx and _pidx not in _sec_novel_idx) \
                        or _pidx in blind_idx_set:
                    _psmi = str(_pspec.get("product_smiles") or "").strip()
                    if _psmi:
                        _pst = strict_identity_of(_psmi)
                        if _pst:
                            pre_dedup_novel_stricts.add(_pst)

        dedup_rejections: list[dict] = []
        dedup_by_signature: dict[tuple, tuple] = {}   # sig -> (key, idx)
        deduped_entries: list = []
        deduped_indices: list[int] = []   # 幸存条目的原索引(来源身份随行)
        best_folded_rank: dict[str, tuple] = {}  # survivor -> (rank, 折叠者, idx, 来源)
        for entry_idx, entry in enumerate(prepared_entries):
            key, spec, _prepared = entry
            signature = net_reaction_signature(spec)
            if signature in dedup_by_signature:
                survivor, survivor_idx = dedup_by_signature[signature]
                folded_source = ("novel" if entry_idx in novel_entry_idx
                                 else "pool")
                folded_rank = _declared_rank(entry_idx, key)
                if survivor in best_folded_rank:
                    survivor_rank: int | None = best_folded_rank[
                        survivor][0]
                else:
                    survivor_rank = _declared_rank(survivor_idx, survivor)
                inherit = folded_rank is not None and (
                    survivor_rank is None or folded_rank < survivor_rank)
                if inherit:
                    best_folded_rank[survivor] = (
                        folded_rank, key, entry_idx, folded_source)
                if entry_idx in retention_by_idx:
                    _folded_ret = retention_by_idx[entry_idx]
                    _surv_ret = retention_by_idx.get(survivor_idx)
                    if _surv_ret is None or _folded_ret < _surv_ret:
                        retention_by_idx[survivor_idx] = _folded_ret
                if entry_idx in blind_idx_set:
                    blind_idx_set.add(survivor_idx)
                dedup_rejections.append({
                    "logical_proposal_id": key,
                    "folded_entry_source": folded_source,
                    "merged_into": survivor,
                    "signature": [str(x) for x in signature][:6],
                    "folded_model_rank": folded_rank,
                    "rank_inherited": bool(inherit)})
                continue
            dedup_by_signature[signature] = (key, entry_idx)
            deduped_entries.append(entry)
            deduped_indices.append(entry_idx)
        prepared_entries = deduped_entries
        if dedup_rejections:
            model_note["dedup_rejections"] = dedup_rejections
        # v1.3 T13-B：次级 pass 排序键随去重折叠（同净反应签名被并入
        # 幸存者 ⇒ 次级引用同步改指幸存键；不改主 pass 的位次事实）。
        if _consensus_sec_keys:
            _merged_into: dict[str, str] = {}
            for _rej in dedup_rejections:
                _src_key = str(_rej.get("logical_proposal_id") or "")
                _dst_key = str(_rej.get("merged_into") or "")
                if _src_key and _dst_key:
                    _merged_into[_src_key] = _dst_key

            def _fold_key(key: str) -> str:
                seen_fold: set[str] = set()
                while key in _merged_into and key not in seen_fold:
                    seen_fold.add(key)
                    key = _merged_into[key]
                return key

            _folded_lists: list[list[str]] = []
            _present = {str(k) for k, _s, _p in prepared_entries}
            for _keys in _consensus_sec_keys:
                _folded: list[str] = []
                _seen: set[str] = set()
                for _key in _keys:
                    _fk = _fold_key(str(_key))
                    if not _fk or _fk not in _present or _fk in _seen:
                        continue
                    _seen.add(_fk)
                    _folded.append(_fk)
                _folded_lists.append(_folded)
            _consensus_sec_keys = _folded_lists
            # v1.4 T14-4：资格集随去重折叠同源改指（同 1:1 位置；不新增
            # 候选、不改变主 pass 事实）。
            _folded_elig: list[list[str] | None] = []
            for _el in _consensus_sec_elig:
                if _el is None:
                    _folded_elig.append(None)
                    continue
                _folded_el: list[str] = []
                _seen_el: set[str] = set()
                for _key in _el:
                    _fk = _fold_key(str(_key))
                    if not _fk or _fk not in _present or _fk in _seen_el:
                        continue
                    _seen_el.add(_fk)
                    _folded_el.append(_fk)
                _folded_elig.append(_folded_el)
            _consensus_sec_elig = _folded_elig
        model_rank_by_key = {
            str(k): int(v) for k, v in (rank_by_key or {}).items()
            if str(k) in {key for key, _, _ in prepared_entries}}
        # W3:novel 条目的模型位次从原始 ID 表补回(novel 键 = 模型
        # 自报 hypothesis_id;池条目键 = 池 key —— 两个命名空间都按
        # 模型 rank 原位次收录,不因来源排后)。
        # T-F 回修二(Codex 复审 2026-10-17,原 P1 余项):补回按**真实
        # 条目来源**(原索引随幸存条目保留)——池条目与已折叠 novel 同名
        # 时,旧判据 key in novel_by_key 会把折叠 novel 的位次误补给
        # 未排名池条目;不得在去重后重新 enumerate 套用去重前索引。
        for entry_idx, (key, _spec, _prepared) in zip(
                deduped_indices, prepared_entries):
            if key in model_rank_by_key:
                continue
            if entry_idx in novel_entry_idx:
                if key in model_rank_by_id_pre:
                    model_rank_by_key[key] = model_rank_by_id_pre[key]
        # W3 位次继承落地:幸存者取 min(自身声明位次,被折叠者最优位次);
        # 来源身份入披露(model_rank_inherited_from="来源:ID")
        inherited_from_by_key: dict[str, str] = {}
        survivor_keys = {key for key, _, _ in prepared_entries}
        for survivor, (folded_rank, folded_key, _fidx, folded_source) in \
                best_folded_rank.items():
            if survivor not in survivor_keys:
                continue
            current = model_rank_by_key.get(survivor)
            if current is None or folded_rank < current:
                model_rank_by_key[survivor] = folded_rank
                inherited_from_by_key[survivor] = \
                    f"{folded_source}:{folded_key}"
        ranked_keys = [k for k, _ in sorted(
            model_rank_by_key.items(), key=lambda kv: (kv[1], kv[0]))]
        effective_rank_by_key: dict[str, int] = {}
        rank_basis_by_key: dict[str, str] = {}
        next_rank = 1
        for key in ranked_keys:                      # Tier 0: 末轮显式位次
            effective_rank_by_key[key] = next_rank
            rank_basis_by_key[key] = "model_selection"
            next_rank += 1
        # Tier 1 & Tier 2: 早轮通过未复述条目 + C 臂盲写未复述条目
        retained_candidates: list[tuple[tuple, str]] = []
        for entry_idx, (key, _spec, _prepared) in zip(
                deduped_indices, prepared_entries):
            if key in effective_rank_by_key:
                continue
            if entry_idx in retention_by_idx:
                retained_candidates.append((retention_by_idx[entry_idx], key))
        retained_candidates.sort(key=lambda pair: (pair[0], pair[1]))
        for _ret_tuple, key in retained_candidates:
            effective_rank_by_key[key] = next_rank
            rank_basis_by_key[key] = "deterministic_fallback"
            next_rank += 1
        # Tier 3: 未被任何轮显式排序的池条目(及其他确定性 fallback)
        for key, _spec, _prepared in prepared_entries:
            if key in effective_rank_by_key:
                continue
            effective_rank_by_key[key] = next_rank
            rank_basis_by_key[key] = "deterministic_fallback"
            next_rank += 1
        # C 臂扩展宽度截断保底:至少为盲写条目保留 1 个名额
        if self.novel_protocol == NOVEL_PROTOCOL_BLIND_FIRST:
            blind_survivor_keys = [
                key for entry_idx, (key, _s, _p) in zip(
                    deduped_indices, prepared_entries)
                if entry_idx in blind_idx_set and key in effective_rank_by_key]
            if blind_survivor_keys:
                _limits = self.ledger._limits(self.run_id)
                _alt_max = int(
                    _limits["max_alternative_hypotheses_per_parent"])
                _alt_used = 0
                for _rrow in self.ledger.conn.execute(
                        "SELECT units FROM budget_reservations WHERE run_id"
                        " = ? AND limit_key = ? AND scope = ? AND status IN"
                        " (?, ?)",
                        (self.run_id,
                         "max_alternative_hypotheses_per_parent",
                         receipt["parent_path_id"],
                         "reserved", "consumed")).fetchall():
                    _alt_used += int(_rrow["units"])
                _selectable = max(0, _alt_max - _alt_used)
                _sched_budget = self.plan.get("schedule_budget")
                if isinstance(_sched_budget, dict) and \
                        _sched_budget.get("max_select") is not None:
                    try:
                        _selectable = min(
                            _selectable, int(_sched_budget["max_select"]))
                    except (TypeError, ValueError):
                        pass
                if _selectable >= 1 and min(
                        effective_rank_by_key[k]
                        for k in blind_survivor_keys) > _selectable:
                    _best_blind = min(
                        blind_survivor_keys,
                        key=lambda k: effective_rank_by_key[k])
                    _old_rank = effective_rank_by_key[_best_blind]
                    for _k, _r in list(effective_rank_by_key.items()):
                        if _selectable <= _r < _old_rank:
                            effective_rank_by_key[_k] = _r + 1
                    effective_rank_by_key[_best_blind] = _selectable
                    model_note["blind_slot_reserved"] = _best_blind

        consensus_boost_by_key: dict[str, bool] = {}
        backfilled_key_set: set[str] = set()
        effective_schedule_budget = self.plan.get("schedule_budget")
        if self.enable_smart_gated_backfill:
            _stage1_routing = None
            _stage1_sink: dict | None = None
            _consensus_active = bool(
                self.enable_v13_multi_sample_consensus)
            _consensus_sink: dict | None = (
                {} if _consensus_active else None)
            # v1.4 T14-3：成对互换机理裁决披露 sink（只在开关打开时非
            # None ⇒ 关闭时零字节漂移）。
            _adj_sink: dict | None = (
                {} if self.enable_v14_pairwise_adjudication else None)
            # v1.4 T14-0：研究期候选 dump 只要 env 显式开启就收集
            # （不参与判据；sink 只在诊断重放里非 None）。
            if self.v13_stage1_debug_dir:
                _stage1_sink = {}
            if self.enable_v13_stage1_rank_calibration or _consensus_active:
                # T12-B 精排与 T13-B 融合都消费同一条 Stage-1 路由事实
                # （运行自身 outcome 优先、外部脱敏映射兜底）；两者互斥
                # 由 __init__ fail-closed，不叠加。
                _stage1_routing = effective_stage1_routing(
                    model_note, self.v13_stage1_routing_external)
                if _stage1_routing is not None and \
                        self.enable_v13_stage1_rank_calibration:
                    _stage1_sink = {}
            backfill_out = consensus_and_smart_backfill(
                substrate_state=substrate,
                parent_ctx=parent_ctx,
                pool_specs=specs,
                prepared_entries=prepared_entries,
                deduped_indices=deduped_indices,
                novel_entry_idx=novel_entry_idx,
                blind_idx_set=blind_idx_set,
                ranked_keys=ranked_keys,
                retained_keys=[k for _rt, k in retained_candidates],
                pre_dedup_novel_stricts=pre_dedup_novel_stricts,
                derive_branch_ctx_fn=self._derive_branch_context,
                s5_supplement_gate_max_s1d=self.s5_supplement_gate_max_s1d,
                s5_super_consensus_score=self.s5_super_consensus_score,
                s5_max_supplements=self.s5_max_supplements,
                target_slots=self.backfill_target_events,
                v13_rank_rules=self.enable_v13_rank_rules,
                v13_stage1_rank=self.enable_v13_stage1_rank_calibration,
                stage1_routing=_stage1_routing,
                stage1_params=self.v13_stage1_rank_params,
                stage1_debug_sink=_stage1_sink,
                v13_multi_sample_consensus=_consensus_active,
                v13_consensus_params=self.v13_consensus_params,
                secondary_ranked_keys_list=_consensus_sec_keys,
                v13_consensus_debug_sink=_consensus_sink,
                # v1.4 T14-4（默认关）：跨池资格率归一化（1:1 资格键集）
                secondary_eligible_keys_list=(
                    _consensus_sec_elig if _consensus_sec_elig else None),
                v14_cross_pool_elig_norm=bool(
                    self.enable_v14_cross_pool_elig_norm),
                enable_v12_post_mechanism=self.enable_v12_post_mechanism,
                collect_pass_debug=bool(self.v13_stage1_debug_dir),
                enable_v14_pairwise_adjudication=bool(
                    self.enable_v14_pairwise_adjudication),
                v14_adjudication_external=self.v14_adjudication_external,
                v14_adjudication_sink=_adj_sink,
                # 论文消融 v1.4 ②(默认 False ⇒ 零字节漂移)
                disable_cleavage_upgrade=self.disable_cleavage_upgrade,
                # 论文消融 v1.4 ④(默认 False ⇒ 零字节漂移)
                disable_ranking_calibration=self.disable_ranking_calibration,
            )
            if self.enable_v14_pairwise_adjudication and \
                    _adj_sink is not None and _adj_sink:
                # v1.4 T14-3 机读披露（小体积；零 SMILES / 零 QID / 零
                # 先验分；进 decide outcome 的 model 块）。
                model_note["v14_pairwise_adjudication"] = dict(
                    _adj_sink.get("note") or {
                        "enabled": True,
                        "applied": False,
                        "verdict": "",
                        "promoted_from_rank": None,
                        "gate_tag": "",
                        "skipped": "no_disclosure",
                    })
            if self.enable_v13_stage1_rank_calibration and \
                    _stage1_sink is not None and _stage1_sink:
                _s1_note = dict(_stage1_sink.get("stage1_note") or {})
                # 机读披露（小体积,进 decide outcome）
                model_note["v13_stage1_rank_calibration"] = {
                    "enabled": True,
                    "routing_source": str(
                        (_stage1_routing or {}).get("source") or ""),
                    "primary_class": (
                        (_stage1_routing or {}).get("primary_class")),
                    "secondary_class": (
                        (_stage1_routing or {}).get("secondary_class")),
                    "triggered_rules": list(
                        _s1_note.get("triggered_rules") or []),
                    "promoted_src": str(
                        _s1_note.get("promoted_src") or ""),
                    "skipped": str(_s1_note.get("skipped") or ""),
                    "top5_before": list(
                        _stage1_sink.get("top5_before") or []),
                    "top5_after": list(
                        _stage1_sink.get("top5_after") or []),
                }
            if _consensus_sink is not None:
                # v1.3 T13-B 机读披露（小体积；无 SMILES；进 decide
                # outcome 的 model 块，供离线逐题核对共识触发面）。
                _consensus_note = dict(_consensus_sink.get("note") or {})
                _pass_keys = list(
                    _consensus_sink.get("pass_top5_keys") or [])
                # v1.4 T14-4：溯源保护门禁（``trace_protected``）逐位元数据。
                # 全票锁/强锚点保护会让 ``result_keys``（最终序）与
                # ``note["rows"]``（融合打序）排序不同 ⇒ **按 src 建表再按
                # 最终序逐位查找**，不假定两列表可直接 zip。找不到（未
                # 落 row，例如未 engaged 的兜底）时按既有前缀规则降级。
                # 只含来源类别与 pass 计数：零 SMILES / 零 QID / 零先验分。
                _after_keys = list(
                    _consensus_sink.get("result_keys") or [])
                _row_by_src = {
                    str(_r.get("src") or ""): _r
                    for _r in (_consensus_note.get("rows") or [])
                    if str(_r.get("src") or "")
                }
                _top5_row_meta: list[dict] = []
                for _k in _after_keys:
                    _r = _row_by_src.get(str(_k)) or {}
                    _top5_row_meta.append({
                        "src": str(_k),
                        "is_rec": (
                            bool(_r.get("is_rec")) if _r
                            else str(_k).startswith("rec-")),
                        "is_novel": (
                            bool(_r.get("is_novel")) if _r
                            else (
                                str(_k).startswith(
                                    ("novel-", "sec-novel-", "hyp_"))
                                or ("@" in str(_k)))),
                        "n_passes_present": (
                            int(_r.get("n_passes_present") or 0)
                            if _r else 0),
                        "top1_votes": (
                            sum(
                                1 for _rk in
                                ((_r.get("pass_ranks") or {}).values())
                                if int(_rk) == 0)
                            if _r else 0),
                    })
                model_note["v13_multi_sample_consensus"] = {
                    "enabled": True,
                    "engaged": bool(
                        _consensus_sink.get("engaged", False)),
                    "version": str(
                        _consensus_sink.get("version") or ""),
                    "stage1_routing_source": str(
                        (_stage1_routing or {}).get("source") or ""),
                    "primary_class": (
                        (_stage1_routing or {}).get("primary_class")),
                    "secondary_class": (
                        (_stage1_routing or {}).get("secondary_class")),
                    "secondary_passes": list(
                        _consensus_sec_debug.get("passes") or []),
                    "secondary_skipped": str(
                        _consensus_sec_debug.get("skipped") or ""),
                    # v1.4 T14-1A：跨池/零池映射与开关面披露（默认关 ⇒
                    # 计数恒 0 / 模式 calibrated / 等价簇 none；不参与判分）。
                    "n_sec_pools_cross_run": int(
                        _consensus_sec_debug.get(
                            "n_sec_pools_cross_run") or 0),
                    "n_sec_pools_unmapped": int(
                        _consensus_sec_debug.get(
                            "n_sec_pools_unmapped") or 0),
                    "n_sec_pools_promoted": int(
                        _consensus_sec_debug.get(
                            "n_sec_pools_promoted") or 0),
                    "pass_mode": str(
                        _consensus_sink.get("pass_mode") or ""),
                    "equiv_cluster_mode": str(
                        _consensus_note.get("equiv_cluster_mode") or "none"),
                    "equiv_version": str(
                        _consensus_note.get("equiv_version") or ""),
                    "top5_before": list(_pass_keys[0] if _pass_keys else []),
                    "top5_after": list(
                        _consensus_sink.get("result_keys") or []),
                    "n_passes": int(
                        _consensus_note.get("n_passes") or 0),
                    "protections": list(
                        _consensus_note.get("protections") or []),
                    "skipped": str(
                        _consensus_note.get("skipped")
                        or _consensus_sink.get("skipped") or ""),
                    # v1.4 T14-4 溯源保护：与 ``top5_after`` 逐位对齐的
                    # 来源类别元数据（零 SMILES / 零 QID / 零先验分）。
                    "top5_row_meta": _top5_row_meta,
                }
            if _stage1_sink is not None and _stage1_sink and \
                    self.v13_stage1_debug_dir:
                # 研究期机读记录（只在 T12 诊断重放里显式开启；不进
                # 判据、不进评分、不改变任何执行分支）。
                try:
                    _dump_dir = Path(self.v13_stage1_debug_dir)
                    _dump_dir.mkdir(parents=True, exist_ok=True)
                    _stage1_sink["run_id"] = self.run_id
                    (_dump_dir / f"{self.run_id}.json").write_text(
                        json.dumps(_stage1_sink, ensure_ascii=False),
                        encoding="utf-8")
                except OSError:
                    pass
            effective_rank_by_key = backfill_out["effective_rank_by_key"]
            rank_basis_by_key = backfill_out["rank_basis_by_key"]
            consensus_boost_by_key = backfill_out["consensus_boost_by_key"]
            backfilled_key_set = set(backfill_out["backfilled_keys"])
            boosted_list = [
                k for k, v in consensus_boost_by_key.items() if v
            ]
            if boosted_list:
                model_note["consensus_boost_keys"] = boosted_list
            if backfill_out["backfilled_keys"]:
                model_note["smart_gated_backfill_keys"] = list(
                    backfill_out["backfilled_keys"]
                )
            model_note["smart_gate_triggered"] = bool(
                backfill_out["smart_gate_triggered"]
            )
            if effective_schedule_budget is None and backfill_out["selected_top_keys"]:
                effective_schedule_budget = {
                    "max_select": min(
                        int(self.backfill_target_events),
                        len(backfill_out["selected_top_keys"]),
                    )
                }

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
            rank = int(effective_rank_by_key.get(key, index + 1))
            task_key = expansion_task_key(
                run_id=self.run_id,
                parent_path_id=receipt["parent_path_id"],
                context_ref=context_ref,
                hypothesis_id=hypothesis.hypothesis_id, attempt_id="",
                policy_version=receipt["policy_version"],
                strict_state_digest=substrate.state_id,
                tool_id="atom-tool-vendored",
                prompt_version=_plan_digest(self.plan)[:16],
                feedback_policy_version=self.format_feedback_policy_version)
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
                # ---- W3:统一排序字段(logical→effective→事件链) ----
                "logical_proposal_id": key,
                "prepared_hypothesis_id": hypothesis.hypothesis_id,
                "net_reaction_signature": [
                    str(x) for x in net_reaction_signature(spec)],
                "model_rank": (
                    int(model_rank_by_key[key])
                    if key in model_rank_by_key else None),
                "model_rank_inherited_from": inherited_from_by_key.get(key),
                "effective_rank": rank,
                "rank_basis": rank_basis_by_key.get(key, ""),
                "rank_policy_version": S5B_RANK_POLICY_VERSION,
            }
            if self.enable_smart_gated_backfill:
                entry_payload["consensus_boost"] = bool(
                    consensus_boost_by_key.get(key, False)
                )
                entry_payload["smart_gated_backfill"] = bool(
                    key in backfilled_key_set
                )
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
            budget=effective_schedule_budget)
        _complete_action(
            self.ledger, receipt["action_id"], worker_id=self.worker_id,
            outcome={"kind": OUTCOME_KIND_SCHEDULED,
                     "detail": {"pool_digest": schedule["pool_digest"],
                                "selected": len(schedule["selected"]),
                                "deferred": len(schedule["deferred"]),
                                "blocked": len(schedule["blocked"]),
                                "model": {
                                    k: v for k, v in model_note.items()
                                    if k not in (
                                        "rank_by_key",
                                        "_earliest_pool_rank_by_id")}}})

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
                         prepared_entries: list, *,
                         substrate_profile=None) -> dict:
        """scripted 模型 proposals[] 协议(网络 0;真实 provider 默认
        off —— 登记被预算拒绝,网络发送被阻止)。novel 池外提案
        (S3B-05)须携带 reaction_spec 完整反应内容,由调用方构造独立
        假设消费。

        S5b 最小接线(pre §3.2):plan.model.provider_kind=real 且注入的
        model 对象实现 ``ppv1_real_fetch`` 时,"取响应"一步改走真实
        provider(登记→sent→complete→responded/failed→同一确定性解析
        器);格式反馈轮的重试响应同样经真实 fetch(反馈请求已由
        register_format_feedback_round 登记并占额)。其余路径(含
        scripted/无 model)行为不变。substrate_profile 穿参给
        _call_real_fetch(候选证据卡底物级在线档案值)。

        EXP1:B 臂(novel_protocol=product_first_feedback)改走
        ``_model_proposals_product_first``(产物优先编译 + 核验反馈
        循环,至多 policy 上限轮);C 臂(blind_first)改走
        ``_model_proposals_blind_first``(盲写 → 合并两阶段,反馈轮
        两阶段共用);A 臂(atom_edit)本函数体逐字节不变。"""
        if self.enable_v13_two_stage_routing and \
                self.v13_routing_stage1_only:
            # v1.3 T11 Step 1:只跑 Stage 1(盲底物路由)即落账返回;
            # 不发 Stage 2、不产提案(池保持冻结池,零删池)。路由结果
            # 进 decide outcome 的 model 块供离线统计。
            real_fetch = self._real_fetch_entry()
            if real_fetch is None:
                raise PPV1RunError(
                    "两段式路由需要真实模型适配器(未注入 ppv1_real_fetch;"
                    "fail-closed)", {"kind": "two_stage_routing_no_adapter"})
            stage1 = self._stage1_class_routing(real_fetch, receipt)
            return {
                "request_id": stage1["request_id"],
                "provider_kind": self.model_provider_kind,
                "network_request_count": 1,
                "parsed_proposals": 0,
                "abstained": True,
                "rank_by_key": {},
                "model_rank_by_id": {},
                "routing_stage1_only": True,
                "class_routing": stage1["routing"],
                "class_routing_parse_fallback": not stage1["parsed"],
                "class_routing_prompt_version": stage1["prompt_version"],
            }
        if self.novel_protocol == NOVEL_PROTOCOL_PRODUCT_FIRST:
            return self._model_proposals_product_first(
                receipt, prepared_entries,
                substrate_profile=substrate_profile)
        if self.novel_protocol == NOVEL_PROTOCOL_BLIND_FIRST:
            return self._model_proposals_blind_first(
                receipt, prepared_entries,
                substrate_profile=substrate_profile)
        action_id = receipt["action_id"]
        attempt_id = (receipt.get("attempt_refs") or [""])[0]
        allowed = {prepared["hypothesis"].hypothesis_id
                   for _, _, prepared in prepared_entries}
        real_fetch = self._real_fetch_entry()
        if real_fetch is not None:
            try:
                fetched = self._call_real_fetch(
                    real_fetch, receipt, prepared_entries,
                    substrate_profile=substrate_profile)
            except PPV1RunError as exc:
                if self.raw_novel_protocol is not None \
                        and exc.detail.get("kind") == "real_model_transport_failure" \
                        and prepared_entries:
                    return {
                        "request_id": str(
                            exc.detail.get("request_id") or ""),
                        "provider_kind": self.model_provider_kind,
                        "network_request_count": 1,
                        "parsed_proposals": 0,
                        "abstained": True,
                        "rank_by_key": {},
                        "model_rank_by_id": {},
                        "transport_aborted_round": {
                            "round": 0,
                            "stage": "initial",
                            "request_id": str(
                                exc.detail.get("request_id") or ""),
                            "error_kind": str(
                                exc.detail.get("error_kind") or ""),
                        },
                    }
                raise
            response = fetched["response_text"]
            request = fetched["request"]
            _class_routing_note = fetched.get("class_routing_note")
        else:
            response = self._next_model_response()
            _class_routing_note = None
            request = self.ledger.register_model_request(
                run_id=self.run_id, action_id=action_id,
                attempt_id=attempt_id,
                provider_kind=self.model_provider_kind,
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
        if _class_routing_note:
            # v1.3 T11:Stage 1 路由结果 + tier 计数进 decide outcome
            # (Step 1 离线统计与 Step 2 软降级披露的机器事实源)
            # v1.3 T12-A:``_call_real_fetch`` 的 routing_note 生产端把
            # 路由体写在 ``"response"`` 键(见本文件 T11 路由块),此处
            # 旧实现只读 ``"routing"`` ⇒ ``class_routing`` 恒空 ``{}``。
            # 两键都认(``routing`` 优先,兼容未来改名),不改变生产端
            # 写盘形状;开关关闭时本块整体不执行 ⇒ 零漂移。
            _stage1 = dict(
                _class_routing_note.get("routing")
                or _class_routing_note.get("response")
                or {})
            note["class_routing"] = _stage1
            note["class_routing_parsed"] = bool(
                _class_routing_note.get("parsed"))
            note["class_routing_parse_fallback"] = not bool(
                _class_routing_note.get("parsed"))
            note["class_routing_request_id"] = str(
                _class_routing_note.get("request_id") or "")
            note["class_routing_prompt_version"] = str(
                _class_routing_note.get("prompt_version") or "")
            note["routing_tier_counts"] = dict(
                _class_routing_note.get("tier_counts") or {})
            note["pool_entries_total"] = int(
                _class_routing_note.get("pool_entries_total") or 0)

        def _parse_response(text: str) -> tuple[dict, list[dict]]:
            """v1.3 T4-A 逐条容错解析入口(开关关闭 ⇒ 原样单次解析)。

            开关关闭时返回 ``(parsed, [])``,异常照旧上抛(判据与改前
            逐字节同);打开时先按严格口径解析,失败再按逐条容错解析
            (丢弃非法提案、保留合法提案,丢弃清单进机读披露)。
            """
            if not self.enable_v13_tolerant_model_parse:
                return parse_model_proposals(
                    text, allowed_hypothesis_ids=allowed), []
            try:
                return parse_model_proposals(
                    text, allowed_hypothesis_ids=allowed), []
            except ModelProtocolError:
                tolerant = parse_model_proposals(
                    text, allowed_hypothesis_ids=allowed,
                    drop_invalid_proposals=True)
                return tolerant, list(
                    tolerant.get("dropped_proposals") or [])

        dropped_proposals: list[dict] = []
        try:
            parsed, dropped_proposals = _parse_response(response)
        except ModelProtocolError as exc:
            kind = exc.detail.get("kind")
            if kind in FEEDBACK_ELIGIBLE:
                # 有界格式反馈(默认 0 轮 ⇒ 反馈被预算拒 ⇒ 结构失败
                # 保持;每轮持久记录输入/错误类别/反馈版本/次数)
                # chain14 P1-1(2026-10-16 Codex 代审回修):反馈轮沿
                # **实际 provider_kind** 登记(与 decide 登记同源
                # self.model_provider_kind)—— 旧实现硬编码 SCRIPTED 而
                # 反馈响应随后走 real fetch ⇒ real 批反馈首发不占每题
                # 额度,组合路径(首发失败→重试→反馈首发→反馈重试)
                # 实发 4 次只预约 3 次,每题预算被旁路。沿实际 kind
                # 登记 ⇒ 全部真实发送共用每题预算,第 4 次发送前被
                # register_model_request 即时占额拦截(拒绝优先于 HTTP)。
                # chain14 P1-2 余项(2026-10-16 复核 §⑤.1):真实取响应
                # 路径先查并**复用同一错误来源既有反馈轮**(原请求键/
                # 原轮次;resume 重入的崩溃窗口里其完整响应已落盘未
                # 消费)—— 行状态机在 ppv1_real_fetch:responded+完整
                # blob ⇒ R3 零调用重放;failed ⇒ 唯一重试终态链核验后
                # 零调用消费;坏 blob/错身份 ⇒ 维持拒绝。不得先分配新
                # 轮、不为恢复另发付费请求、不重算新键掩盖坏记录;
                # 无既有轮才走新轮登记(轮数/每题预算判据不变,预算
                # 第 4 次发送前拒保持;purpose 被篡改的坏行由查找面
                # 结构化拒,不以新轮登记绕过)。
                # chain14 P1-2 收口轮(2026-10-16 第四轮,findings §三):
                # 复用之前统一核验原登记身份/内容/执行引用(所有状态
                # 分支共用一套判据,核验门在 latest_format_feedback_
                # round 内)—— 计数>0 却查不到应有原行 ⇒ 结构化拒
                # (不返回 None 走新登记另发);payload_hash 按同源确定
                # 性重算核验(载荷无时间戳,不以重新生成内容身份洗掉
                # 坏记录)。
                if real_fetch is not None:
                    feedback = latest_format_feedback_round(
                        self.ledger, run_id=self.run_id,
                        action_id=action_id, attempt_id=attempt_id,
                        provider_kind=self.model_provider_kind,
                        error=exc, response_excerpt=str(response))
                else:
                    feedback = None
                consumed_in_place = False
                if feedback is None:
                    try:
                        feedback = register_format_feedback_round(
                            self.ledger, run_id=self.run_id,
                            action_id=action_id, attempt_id=attempt_id,
                            error=exc, response_excerpt=str(response),
                            provider_kind=self.model_provider_kind)
                    except SearchBudgetExhausted as feedback_exhausted:
                        # 反馈轮超上限(或策略 0):结构失败保持,不以反馈
                        # 重试到通过 —— 升级为结构失败(不是真实请求预算
                        # 的资源拒绝路径)
                        consumed = None
                        if self.fix_budget_limit_consumption:
                            # T10-A 开关 2:反馈预算拒 ≠ 已付费响应不可用。
                            # 按逐条容错口径消费**已返回**响应(丢弃非法
                            # 提案、保留合法提案),不整条丢弃已付费内容;
                            # 容错解析仍失败 ⇒ 按结构失败如实停止(原行为)。
                            try:
                                consumed = parse_model_proposals(
                                    response,
                                    allowed_hypothesis_ids=allowed,
                                    drop_invalid_proposals=True)
                            except ModelProtocolError:
                                consumed = None
                        if consumed is None:
                            note["format_feedback_exhausted"] = {
                                "kind": feedback_exhausted.detail.get("kind")}
                            raise PPV1RunError(
                                "模型响应结构失败(格式反馈耗尽或策略 0 轮;"
                                "结构失败保持,不以反馈改分子再试到通过)",
                                {"kind": "model_structure_failure",
                                 "error_kind": kind,
                                 "feedback_kind":
                                     feedback_exhausted.detail.get("kind")})                         from feedback_exhausted
                        note["format_feedback_budget_rejected"] = {
                            "kind": str(
                                feedback_exhausted.detail.get("kind") or ""),
                            "consumed_with": "tolerant_parse"}
                        dropped_proposals = list(
                            consumed.get("dropped_proposals") or [])
                        parsed = consumed
                        consumed_in_place = True
                if not consumed_in_place:
                    note["format_feedback_round"] = feedback["request_id"]
                    if real_fetch is not None:
                        retry_fetched = self._call_real_fetch(
                            real_fetch, receipt, prepared_entries,
                            feedback_request=feedback,
                            feedback_error={
                                "kind": kind,
                                "response_excerpt": str(response)},
                            substrate_profile=substrate_profile)
                        retry = retry_fetched["response_text"]
                    else:
                        retry = self._next_model_response()
                    parsed, retry_dropped = _parse_response(retry)
                    dropped_proposals = dropped_proposals + retry_dropped
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
        if dropped_proposals:
            # v1.3 T4-A:逐条容错丢弃清单(机读披露;含 rank 引用被丢弃
            # 提案而跳过的 ID)。开关关闭时该键不出现。
            note["dropped_proposals"] = dropped_proposals
        note["parsed_proposals"] = len(parsed["proposals"])
        note["abstained"] = parsed["abstained"]
        note["rank_by_key"] = rank_by_key
        # W3:模型 rank 的**原始 ID 表**(池 prepared hypothesis_id 与
        # novel 自报 id 都收录)—— novel 在本函数之后才准备,其模型
        # 位次若只按池键映射会丢失(旧实现 895–909 后追加 + 941 池后
        # fallback ⇒ 模型首位 novel 可能丢失;统一映射在 _run_decide)
        note["model_rank_by_id"] = {
            str(hid): position
            for position, hid in enumerate(parsed["rank_hypotheses"], 1)}
        novel = [p for p in parsed["proposals"]
                 if p.get("origin") == "novel"]
        if novel:
            note["novel_proposals"] = novel
        return note

    # ---------------------------------------------- EXP1 产物优先(核验反馈)

    def _verify_novel_product_first(self, novel_proposals: list[dict],
                                    substrate_smiles: str):
        """逐条 novel 提案调 E6(单一编译/核验入口),分三路:

        - ``full`` 级(七条件全满足,方案甲)⇒ novel_compiled;
        - ``declared`` 级(成功但进声明桶;``bucket_kind`` 区分
          ``declared_recognized`` / ``declared_unrecognized``)⇒
          declared_bucket(**不进事件**);
        - 失败 ⇒ whitelist 失败项(``hypothesis_id`` + ``failure_kind``
          [+ ``executed_components`` 仅 product_set_mismatch])。

        全部判据来自程序编译核验(零 LLM、零金标);返回顺序按
        hypothesis_id 排序(确定性,可重放)。
        """
        compiled: list[dict] = []
        declared: list[dict] = []
        failures: list[dict] = []
        for proposal in (novel_proposals or []):
            hypothesis_id = str(proposal.get("hypothesis_id") or "")
            spec_in = dict(proposal.get("reaction_spec") or {})
            fb_edits = (
                [
                    dict(e)
                    for e in (proposal.get("fallback_edits") or [])
                    if isinstance(e, dict)
                ]
                or None
            )
            outcome = compile_novel_product_first(
                substrate_smiles,
                str(spec_in.get("product_smiles") or ""),
                [str(c) for c in (spec_in.get("coproducts") or [])],
                hypothesis_id,
                fallback_edits=fb_edits,
                extended_stereo_dissolution=bool(
                    self.enable_v13_stereo_dissolution_extended
                    or self.enable_v14_compiler_ext),
                stereo_edit_graceful_fallback=bool(
                    self.enable_v14_compiler_ext),
                allow_ring_cleavage_and_fused_dearomatization=bool(
                    self.enable_v14_compiler_ext),
                # v1.4 T14-4:编译器 v2 两开关(默认关 ⇒ 逐字节同)
                retained_tetrahedral_parity_check=bool(
                    self.enable_v14_compiler_ext_2),
                allow_aromatic_ring_closure=bool(
                    self.enable_v14_compiler_ext_2))
            if outcome.get("status") != "compiled":
                failure = dict(outcome.get("feedback") or {})
                failure["hypothesis_id"] = hypothesis_id
                failures.append(failure)
                continue
            entry = {
                "hypothesis_id": hypothesis_id,
                "proposal_context": dict(
                    proposal.get("proposal_context") or {}),
                "reaction_spec": dict(outcome["spec"]),
                "verification_tier": outcome["verification_tier"],
                "bucket_kind": str(outcome["bucket_kind"]),
                "added_heavy_atoms": int(outcome["added_heavy_atoms"]),
                "removed_heavy_atoms": int(outcome["removed_heavy_atoms"]),
                "added_fragment_count": int(
                    outcome["added_fragment_count"]),
                "net_zero_rewrite": bool(outcome["net_zero_rewrite"]),
                "bucket_policy_version": str(
                    outcome["bucket_policy_version"]),
                "bucket_table_sha256": str(outcome["bucket_table_sha256"]),
                "bucket_conditions": dict(
                    outcome.get("bucket_conditions") or {}),
                "bucket_reasons": list(outcome.get("bucket_reasons") or []),
                "bucket_metrics": dict(outcome.get("bucket_metrics") or {}),
                "principal_reassigned": bool(
                    outcome["principal_reassigned"]),
                "principal_reassign_reason": str(
                    outcome["principal_reassign_reason"] or ""),
                "declared_product": str(outcome["declared_product"]),
                "compiled_principal": str(outcome["compiled_principal"]),
                "formnorm_status": str(outcome["formnorm_status"]),
            }
            # PC8:模型自写、被产物优先分支忽略的 reaction_spec 键名
            # 随条目传播(仅非空时附加 —— clean 响应零增量)
            if proposal.get("ignored_spec_keys"):
                entry["ignored_spec_keys"] = [
                    str(key) for key in proposal["ignored_spec_keys"]]
            if outcome["verification_tier"] == VERIFICATION_TIER_FULL:
                compiled.append(entry)
            else:
                declared.append(dict(entry, diagnostics=dict(
                    outcome.get("diagnostics") or {})))
        failures.sort(key=lambda item: (
            str(item.get("hypothesis_id") or ""),
            str(item.get("failure_kind") or "")))
        compiled.sort(key=lambda item: str(item.get("hypothesis_id") or ""))
        declared.sort(key=lambda item: str(item.get("hypothesis_id") or ""))
        return compiled, declared, failures

    def _secondary_consensus_ranked_keys(
        self,
        *,
        substrate_smiles: str,
        substrate,
        receipt: dict,
        specs: list[dict],
        prepared_entries: list,
        novel_entry_idx: set[int],
        novel_by_key: dict[str, dict],
    ) -> tuple[list[list[str]], dict]:
        """T13-B：把计划注入的次级 pass 回复解析成**本 run 逻辑键**排序表。

        输入 = ``plan.v13_consensus_secondary_passes`` 的
        ``{run_id, content}`` 列表（同题其他采样 run 的模型原始回复；
        零调用重放通道）。每个 pass：

        1. 用该次级 run 的根路径 + 同底物状态重建池条目 hypothesis ID
           映射（``prepare_hypothesis`` 单一构建源；depth-0 决定的口径，
           与任务书一致）；
        2. ``parse_model_proposals``（逐条容错）解析；有效引用 = 池内
           ID（映射回本 run 的池逻辑键）∪ 池外 novel（须带
           ``proposal_context`` + ``reaction_spec``）；
        3. novel 逐条走 ``_verify_novel_product_first``（程序编译核验，
           零放宽）：full 级才消费；净反应签名已存在 ⇒ 复用既有条目
           键（零新条目），否则 ``prepare_hypothesis`` 后追加进
           ``prepared_entries`` 并标 ``novel_entry_idx``（键加
           ``@<sec_run_id>`` 后缀防跨 pass 撞键）；
        4. 排序 = ``rank_hypotheses`` 顺序优先，其余按 proposal 声明序；
           映射失败/非 full 的 ID 记入 debug 的 ``skipped_ids``。

        只读输入内容、只追加经既有核验链的合法候选；任何解析/编译失败
        只让该 pass 贡献变少（如实记 debug），不改变主 pass 行为。

        v1.4 T14-1A：跨池 / 零池（盲写）次级 pass 无损映射（默认关）。
        次级元素可**可选**携带：

        - ``sec_pool_specs``：次级批自身 ``run_inputs/<qid>.json`` 里
          ``plan.pools[substrate]`` 的同源 specs 列表（首选入口）；
        - ``sec_pools``：次级池条目列表（经同一池 spec 结构直接消费）；
        - ``allow_verified_sec_pool_promotion``：未命中主池签名、但模型在
          该 pass 前列（默认前 5）明确选入的外池候选，经既有合规
          ``_verify_novel_product_first`` 编译核验后追加为合法备选
          （默认 ``False``：只映射主池已有签名 + 正常核验次级 novel）。

        给出 ``sec_pool_specs``/``sec_pools`` 时用**次级自身**的 specs +
        ``sec_run_id`` 根 + 同底物重建 ``sec_hyp_id``，再按
        ``net_reaction_signature`` 映射到本 run 既有键（零新条目、不把
        外池池尾干扰项塞进主池）；显式 ``sec_pools=[]``（零池盲写批）
        ⇒ 无可映射池候选，带 ``reaction_spec`` 的提案自然走既有
        ``_verify_novel_product_first`` 核验后汇入共识。**未携带**任一
        键 ⇒ 与 v1.3 的映射路径 100% 相同。
        """
        passes = list(self.v13_consensus_secondary_passes or [])
        debug: dict = {
            "passes": [],
            "skipped": "",
            "n_sec_pools_cross_run": 0,
            "n_sec_pools_unmapped": 0,
            "n_sec_pools_promoted": 0,
        }
        if not passes:
            debug["skipped"] = "no_secondary_passes"
            return [], debug

        from .s5b_compiler import net_reaction_signature

        # 既有条目净反应签名 → 键（novel 复用判据；确定性首见优先）
        sig_to_key: dict[tuple, str] = {}
        for _key, _spec, _prep in prepared_entries:
            try:
                _sig = net_reaction_signature(_spec)
            except Exception:  # noqa: BLE001 —— 缺产品等非法 spec 不参与
                continue
            sig_to_key.setdefault(_sig, str(_key))

        # v1.4 T14-4：已核验条目主产物严格身份 → 键（跨 pass 同主产物
        # 复用；默认关 ⇒ 不建索引、不消费）。
        from .chemstate import strict_identity_of

        def _principal_strict(spec_in: dict) -> str:
            smi = str(spec_in.get("product_smiles") or "")
            if not smi:
                return ""
            try:
                return str(strict_identity_of(smi) or "")
            except Exception:  # noqa: BLE001 —— 不可解析 ⇒ 不复用
                return ""

        principal_to_key: dict[str, str] = {}
        if self.enable_v14_compiler_ext_2:
            for _key, _spec, _prep in prepared_entries:
                _pst = _principal_strict(_spec)
                if _pst:
                    principal_to_key.setdefault(_pst, str(_key))

        def _pass_pool_specs(sec_pass: dict) -> tuple[list | None, str, int]:
            """次级 pass 自带的同源池输入（v1.4 T14-1A）。

            返回 ``(specs | None, source, n_invalid)``：

            - ``None`` ⇒ 该 pass **未携带**池输入 ⇒ 沿用 v1.3 的"同池"
              映射路径（用本 run 的 ``specs`` 重建次级 hypothesis ID）；
            - 列表（**含空列表**）⇒ 跨池/零池显式路径：空列表 = 零池盲写
              批（``sec_pools=[]``）⇒ 无可映射池候选，全部带
              ``reaction_spec`` 的提案走既有 ``_verify_novel_product_first``；
            - ``n_invalid`` = 非 dict / 既无 ``reaction_spec`` 又无
              ``product_smiles`` 的条目数（如实计数，不猜内容）。
            """
            raw = sec_pass.get("sec_pool_specs")
            source = "sec_pool_specs"
            if raw is None:
                raw = sec_pass.get("sec_pools")
                source = "sec_pools"
                if raw is None:
                    return None, "same_run_pool", 0
            if not isinstance(raw, list):
                return [], f"{source}_invalid", 1
            kept: list = []
            n_invalid = 0
            for item in raw:
                if not isinstance(item, dict):
                    n_invalid += 1
                    continue
                nested = item.get("reaction_spec")
                has_nested = isinstance(nested, dict) and bool(
                    str(nested.get("product_smiles") or ""))
                if has_nested or str(item.get("product_smiles") or ""):
                    kept.append(item)
                elif not item:
                    # 空 dict 不构成可重建池条目
                    n_invalid += 1
                else:
                    kept.append(item)
            return kept, source, n_invalid

        result_lists: list[list[str]] = []
        # v1.4 T14-4：每 pass 资格键集合（与 ``result_lists`` 1:1）。
        # 同池 pass（未携带 sec 池输入）⇒ ``None``（无资格信息）；
        # 跨池/零池 pass ⇒ 该次级池映射到本 run 的逻辑键集合（空池 ⇒
        # 空集，不计入池 pass 数）。资格集不参与本函数的映射判据。
        elig_lists: list[set[str] | None] = []
        for pass_idx, sec_pass in enumerate(passes):
            sec_run_id = str(sec_pass.get("run_id") or "")
            content = str(sec_pass.get("content") or "")
            sec_specs, pool_source, n_pool_invalid = _pass_pool_specs(sec_pass)
            cross_pool = sec_specs is not None
            allow_promotion = bool(
                sec_pass.get("allow_verified_sec_pool_promotion"))
            entry: dict = {
                "index": int(pass_idx),
                "run_id": sec_run_id,
                "parsed": False,
                "pool_source": pool_source,
                "cross_pool": bool(cross_pool),
                "allow_verified_sec_pool_promotion": bool(allow_promotion),
                "sec_pool_specs_invalid": int(n_pool_invalid),
                "n_pool_ids": 0,
                "n_sec_pool_ids": 0,
                "n_sec_pool_unmapped": 0,
                "sec_pool_promoted": 0,
                "unmapped_pool_ids": [],
                "n_referenced_ids": 0,
                "n_mapped": 0,
                "novel_added": 0,
                "novel_reused": 0,
                "skipped_ids": [],
                "error": "",
            }
            if not sec_run_id or not content.strip():
                entry["error"] = "missing_run_id_or_content"
                debug["passes"].append(entry)
                # v1.4 T14-4：错误 pass 不产排序表 ⇒ 资格集同样不追加
                # （保持与 ``result_lists`` 1:1，防下游错位配对）。
                continue

            # 1) 次级 run 的池 hypothesis ID → 本 run 逻辑键
            sec_root = stable_id("spath", sec_run_id, "root")
            sec_substrate = _substrate_state(
                substrate_smiles, f"ppv1-substrate:{sec_run_id}")
            hyp_to_key: dict[str, str] = {}
            unmapped_sec_ids: set[str] = set()
            promotable_spec_by_hyp: dict[str, dict] = {}
            pool_specs_for_mapping = sec_specs if cross_pool else list(specs)
            for idx, spec in enumerate(pool_specs_for_mapping or []):
                if not isinstance(spec, dict):
                    continue
                key = str(spec.get("key") or f"spec-{idx}")
                try:
                    sec_prep = prepare_hypothesis(
                        spec, parent_path_id=sec_root,
                        substrate_state=sec_substrate,
                        transformation_ref=str(
                            spec.get("transformation_ref") or ""))
                except Exception:  # noqa: BLE001 —— 单条不可重建 ⇒ 不映射
                    continue
                sec_hyp_id = str(sec_prep["hypothesis"].hypothesis_id)
                if not cross_pool:
                    # v1.3 逐字节路径：同池 ⇒ 直接映射回本 run 的池逻辑键
                    hyp_to_key[sec_hyp_id] = key
                    continue
                # 跨池：按**净反应签名**映射到本 run 既有合法键（同签名
                # ⇒ 同反应 ⇒ 直接复用既有键；零新条目、不把外池池尾干扰
                # 项塞进主池）
                try:
                    sig = net_reaction_signature(spec)
                except Exception:  # noqa: BLE001
                    sig = None
                target = sig_to_key.get(sig) if sig is not None else None
                if target is None:
                    unmapped_sec_ids.add(sec_hyp_id)
                    promotable_spec_by_hyp[sec_hyp_id] = spec
                    continue
                hyp_to_key[sec_hyp_id] = target
            entry["n_pool_ids"] = len(hyp_to_key)
            entry["n_sec_pool_ids"] = len(hyp_to_key) if cross_pool else 0
            entry["n_sec_pool_unmapped"] = len(unmapped_sec_ids)

            # 2) 解析（逐条容错：单条非法不拖垮整个 pass）。跨池里未映射
            # 的**次级池引用**也进 allowed 集合：它们确实是那批池的 ID，
            # 只是本 run 无法表示 —— 如实解析、随后记 skipped，不把它们
            # 误判成"池外 novel"再走核验（不伪造来源）。
            try:
                parsed = parse_model_proposals(
                    content,
                    allowed_hypothesis_ids=(
                        set(hyp_to_key) | set(unmapped_sec_ids)),
                    protocol=self.novel_protocol,
                    drop_invalid_proposals=True)
            except ModelProtocolError as exc:
                entry["error"] = (
                    f"parse:{exc.detail.get('kind') or type(exc).__name__}")
                debug["passes"].append(entry)
                # v1.4 T14-4：解析失败 pass 不产排序表 ⇒ 资格集不追加
                # （1:1 对齐守卫同上）。
                continue
            entry["parsed"] = True

            proposal_by_id: dict[str, dict] = {}
            ordered_ids: list[str] = []
            for raw_id in (parsed.get("rank_hypotheses") or []):
                hid = str(raw_id or "")
                if hid and hid not in ordered_ids:
                    ordered_ids.append(hid)
            for prop in (parsed.get("proposals") or []):
                if not isinstance(prop, dict):
                    continue
                hid = str(prop.get("hypothesis_id") or "")
                if not hid:
                    continue
                proposal_by_id.setdefault(hid, prop)
                if hid not in ordered_ids:
                    ordered_ids.append(hid)
            entry["n_referenced_ids"] = len(ordered_ids)

            # 2b) 受控池候选晋升（默认关）：未命中主池签名、但模型在该
            # 次级 pass **前列**（``promotion_max_rank`` 内）明确选入的
            # 外池候选，可经既有合规产物优先编译核验后追加为合法备选
            # （同一 ``_verify_novel_product_first`` 链，零放宽）。
            promotion_max_rank = 5
            promote_props: dict[str, dict] = {}
            if cross_pool and allow_promotion:
                for pos, hid in enumerate(ordered_ids):
                    if pos >= promotion_max_rank:
                        break
                    spec = promotable_spec_by_hyp.get(hid)
                    if not isinstance(spec, dict):
                        continue
                    nested = spec.get("reaction_spec")
                    product = str(
                        spec.get("product_smiles")
                        or (nested.get("product_smiles")
                            if isinstance(nested, dict) else "")
                        or "")
                    if not product:
                        continue
                    # 忠实转发次级池 spec 自身的共产物声明（compile 判据
                    # 同源；缺省才由编译器按产物优先规则推断，零放宽）。
                    coproducts = spec.get("coproducts")
                    if coproducts is None and isinstance(nested, dict):
                        coproducts = nested.get("coproducts")
                    reaction_spec: dict = {"product_smiles": product}
                    if isinstance(coproducts, (list, tuple)) and coproducts:
                        reaction_spec["coproducts"] = [
                            str(item) for item in coproducts]
                    promote_props[hid] = {
                        "hypothesis_id": hid,
                        "proposal_context": {
                            "reference_hypothesis_ids": [],
                            "output_origin": "sec_pool_promotion",
                        },
                        "reaction_spec": reaction_spec,
                    }

            # 3) ID → 本 run 逻辑键（池引用直接映射；novel 走程序核验）
            mapped_keys: list[str] = []
            for hid in ordered_ids:
                from_promotion = False
                if hid in hyp_to_key:
                    mapped_keys.append(hyp_to_key[hid])
                    continue
                if hid in unmapped_sec_ids:
                    prop = promote_props.get(hid)
                    if prop is None:
                        entry["skipped_ids"].append(hid)
                        entry["unmapped_pool_ids"].append(hid)
                        continue
                    from_promotion = True
                else:
                    prop = proposal_by_id.get(hid)
                    if prop is None:
                        entry["skipped_ids"].append(hid)
                        continue
                compiled: list[dict] = []
                disable_pf = bool(
                    getattr(self, "disable_product_first_fallback", False))
                if disable_pf:
                    # 论文消融 T1-L11：disable_product_first_fallback=True
                    # 时次级 pass 同源禁止走产物优先逆向编译与
                    # enable_v14_sec_novel_backfill，只允许携带原子编辑
                    # (edits) 的提案走 AtomTool 正向执行 + 审计核验。
                    sec_spec = dict(prop.get("reaction_spec") or {})
                    if sec_spec.get("edits"):
                        sec_expand = None
                        if self.fix_decide_atomtool_import:
                            from .production import (
                                execute_atomtool_expansion as sec_expand,
                            )
                        try:
                            from .audit import audit_hypothesis, decide_admission
                            from .production import ADMISSION_SUBMITTABLE

                            sec_parent_ctx = load_context(
                                self.ledger.artifact_store,
                                receipt["parent_path_id"])
                            cand_prep = prepare_hypothesis(
                                sec_spec,
                                parent_path_id=sec_root,
                                substrate_state=sec_substrate,
                                transformation_ref=str(
                                    sec_spec.get("transformation_ref") or ""),
                                source_refs=[{
                                    "record": "novel-model-proposal:"
                                              "sec_atomtool"}])
                            exec_in = str(
                                cand_prep["tool_inputs"].get(
                                    "execution_input_smiles")
                                or sec_substrate.smiles_isomeric)
                            if sec_expand is not None:
                                exec_out = sec_expand(
                                    substrate_smiles=exec_in,
                                    tool_inputs=cand_prep["tool_inputs"])
                            else:
                                exec_out = execute_atomtool_expansion(
                                    substrate_smiles=exec_in,
                                    tool_inputs=cand_prep["tool_inputs"])
                            if exec_out.get("execution_ok"):
                                audit_rep = audit_hypothesis(
                                    cand_prep["hypothesis"],
                                    run_id=f"{sec_run_id or 'sec'}-novel-check",
                                    states=cand_prep["states"],
                                    context=sec_parent_ctx,
                                    center_evidence=exec_out[
                                        "center_evidence"])
                                disp, _ = decide_admission(audit_rep)
                                if disp in ADMISSION_SUBMITTABLE:
                                    decl_prod = str(
                                        sec_spec.get("product_smiles") or "")
                                    decl_cops = [
                                        str(c) for c in (
                                            sec_spec.get("coproducts") or [])]
                                    if self.fix_decide_atomtool_import:
                                        _cov = _declared_consistency_report(
                                            cand_prep, decl_prod, decl_cops,
                                            sec_spec)
                                        _exec_cov = (
                                            _execution_declaration_mismatch(
                                                exec_out,
                                                [decl_prod] + decl_cops))
                                        if _cov.get("covered") and not _exec_cov:
                                            compiled = [{
                                                "reaction_spec": dict(sec_spec)
                                            }]
                                    else:
                                        compiled = [{
                                            "reaction_spec": dict(sec_spec)}]
                        except Exception:  # noqa: BLE001 —— 单条异常不扩权
                            compiled = []
                else:
                    try:
                        compiled, _declared, _failures = \
                            self._verify_novel_product_first(
                                [prop], substrate_smiles)
                    except Exception:  # noqa: BLE001 —— 单条编译异常不扩权
                        entry["skipped_ids"].append(hid)
                        continue
                if (not disable_pf
                        and not compiled
                        and self.enable_v14_sec_novel_backfill):
                    # v1.4 T14-1B:池外 novel 对称回退 —— 与 _run_decide
                    # 的池外回退同源(产物优先直编;11 门核验由
                    # compile_s5_candidate_to_spec 内部完成)。默认关 ⇒
                    # 该分支不存在,零字节漂移。
                    from ..services.s5_hybrid_choice import (
                        compile_s5_candidate_to_spec,
                    )

                    spec_in_fb = dict(prop.get("reaction_spec") or {})
                    expect_fb = spec_in_fb.get("expectation")
                    expect_smi_fb = (
                        str(expect_fb.get("target_smiles") or "").strip()
                        if isinstance(expect_fb, dict) else "")
                    exp_prods_fb = (
                        spec_in_fb.get("expected_products")
                        or prop.get("expected_products") or [])
                    first_exp_fb = (
                        str(exp_prods_fb[0]).strip()
                        if isinstance(exp_prods_fb, list)
                        and exp_prods_fb else "")
                    fb_target = str(
                        spec_in_fb.get("product_smiles")
                        or spec_in_fb.get("target_product_smiles")
                        or expect_smi_fb
                        or first_exp_fb
                        or prop.get("product_smiles")
                        or prop.get("target_product_smiles")
                        or "").strip()
                    raw_cops_fb = (
                        spec_in_fb.get("coproducts")
                        or prop.get("coproducts") or [])
                    fb_cop_sets = (
                        [[str(c).strip() for c in raw_cops_fb
                          if str(c).strip()]]
                        if isinstance(raw_cops_fb, list) and raw_cops_fb
                        else None)
                    fb_spec = None
                    if fb_target:
                        try:
                            fb_spec = compile_s5_candidate_to_spec(
                                substrate.smiles_isomeric,
                                {"cand_smiles": fb_target},
                                index=180 + len(mapped_keys),
                                is_gated_supplement=False,
                                coproduct_sets=fb_cop_sets,
                                extended_stereo_dissolution=bool(
                                    self.enable_v13_stereo_dissolution_extended
                                    or self.enable_v14_compiler_ext),
                                stereo_edit_graceful_fallback=bool(
                                    self.enable_v14_compiler_ext),
                                allow_ring_cleavage_and_fused_dearomatization=(
                                    bool(self.enable_v14_compiler_ext)),
                                retained_tetrahedral_parity_check=bool(
                                    self.enable_v14_compiler_ext_2),
                                allow_aromatic_ring_closure=bool(
                                    self.enable_v14_compiler_ext_2),
                            )
                        except Exception:  # noqa: BLE001 —— 回退失败不扩权
                            fb_spec = None
                        if (fb_spec is None and fb_cop_sets
                                and self.enable_v14_compiler_ext_2):
                            # v1.4 T14-4：主/次 pass novel 对称回补 ——
                            # 声明共产物编译失败时回退为「只按主产物」。
                            try:
                                fb_spec = compile_s5_candidate_to_spec(
                                    substrate.smiles_isomeric,
                                    {"cand_smiles": fb_target},
                                    index=180 + len(mapped_keys),
                                    is_gated_supplement=False,
                                    coproduct_sets=None,
                                    extended_stereo_dissolution=bool(
                                        self.enable_v13_stereo_dissolution_extended
                                        or self.enable_v14_compiler_ext),
                                    stereo_edit_graceful_fallback=bool(
                                        self.enable_v14_compiler_ext),
                                    allow_ring_cleavage_and_fused_dearomatization=(
                                        bool(self.enable_v14_compiler_ext)),
                                    retained_tetrahedral_parity_check=bool(
                                        self.enable_v14_compiler_ext_2),
                                    allow_aromatic_ring_closure=bool(
                                        self.enable_v14_compiler_ext_2),
                                )
                            except Exception:  # noqa: BLE001
                                fb_spec = None
                    if fb_spec is not None:
                        compiled = [
                            {"reaction_spec": dict(fb_spec)}]
                        entry["sec_novel_backfilled"] = int(
                            entry.get("sec_novel_backfilled", 0)) + 1
                if not compiled:
                    entry["skipped_ids"].append(hid)
                    continue
                item = compiled[0]
                novel_spec = dict(item.get("reaction_spec") or {})
                try:
                    sig = net_reaction_signature(novel_spec)
                except Exception:  # noqa: BLE001
                    entry["skipped_ids"].append(hid)
                    continue
                existing = sig_to_key.get(sig)
                if (existing is None
                        and self.enable_v14_compiler_ext_2):
                    # v1.4 T14-4：同主产物已核验键复用（净反应签名
                    # 不同但主产物相同 ⇒ 复用既有合法条目，零新条目）。
                    _pst_novel = _principal_strict(novel_spec)
                    if _pst_novel:
                        existing = principal_to_key.get(_pst_novel)
                if existing:
                    mapped_keys.append(existing)
                    entry["novel_reused"] += 1
                    if from_promotion:
                        entry["sec_pool_promoted"] += 1
                    continue
                base_key = f"{hid}@{sec_run_id}" if sec_run_id else hid
                novel_key = base_key
                existing_keys = {str(k) for k, _s, _p in prepared_entries}
                dup = 2
                while novel_key in existing_keys:
                    novel_key = f"{base_key}#{dup}"
                    dup += 1
                novel_spec["key"] = novel_key
                novel_spec["transformation_ref"] = str(
                    novel_spec.get("transformation_ref")
                    or f"novel-consensus:{novel_key}")
                try:
                    novel_prep = prepare_hypothesis(
                        novel_spec,
                        parent_path_id=receipt["parent_path_id"],
                        substrate_state=substrate,
                        transformation_ref=str(
                            novel_spec.get("transformation_ref") or ""),
                        source_refs=[{
                            "record": (
                                "novel-model-proposal:consensus:"
                                f"{sec_run_id}")}])
                except Exception:  # noqa: BLE001 —— 编译后建假设失败 ⇒ 跳过
                    entry["skipped_ids"].append(hid)
                    continue
                prepared_entries.append(
                    (novel_key, novel_spec, novel_prep))
                novel_entry_idx.add(len(prepared_entries) - 1)
                novel_by_key[novel_key] = prop
                sig_to_key[sig] = novel_key
                if self.enable_v14_compiler_ext_2:
                    _pst_added = _principal_strict(novel_spec)
                    if _pst_added:
                        principal_to_key.setdefault(_pst_added, novel_key)
                mapped_keys.append(novel_key)
                entry["novel_added"] += 1
                if from_promotion:
                    entry["sec_pool_promoted"] += 1

            seen: set[str] = set()
            sec_keys: list[str] = []
            present_keys = {str(k) for k, _s, _p in prepared_entries}
            for _key in mapped_keys:
                if _key in seen or _key not in present_keys:
                    continue
                seen.add(_key)
                sec_keys.append(_key)
            entry["n_mapped"] = len(sec_keys)
            result_lists.append(sec_keys)
            # v1.4 T14-4：资格集在映射完成后定格（同池 ⇒ None 无信息）。
            elig_lists.append(
                None if not cross_pool else set(hyp_to_key.values()))
            debug["passes"].append(entry)

        debug["n_sec_pools_cross_run"] = sum(
            1 for e in debug["passes"] if e.get("cross_pool"))
        debug["n_sec_pools_unmapped"] = sum(
            int(e.get("n_sec_pool_unmapped") or 0)
            for e in debug["passes"])
        debug["n_sec_pools_promoted"] = sum(
            int(e.get("sec_pool_promoted") or 0)
            for e in debug["passes"])

        # v1.4 T14-4：资格集机读记录（与 result_lists 1:1；仅排序研究
        # 期消费，缺省不开开关时下游直接忽略）。
        debug["secondary_eligible_keys_list"] = [
            (None if ek is None else sorted(ek)) for ek in elig_lists]
        return result_lists, debug

    def _accumulate_round_full(
        self,
        accumulated_by_id: dict[str, dict],
        earliest_pool_rank: dict[str, tuple[int, int]],
        *,
        eval_round: int,
        parsed: dict,
        compiled: list[dict],
        allowed_ids: set[str],
    ) -> None:
        """P0-1(2026-11-07):跨轮累积已通过 full 核验的 novel 提案,并记录
        每个条目首次通过的 (first_pass_round, first_pass_pos) 以及池/已准
        备条目首次被显式排序的 (eval_round, pos)。"""
        from .s5b_compiler import net_reaction_signature

        rank_list = [str(hid) for hid in (parsed.get("rank_hypotheses") or [])]
        rank_pos_map: dict[str, int] = {}
        for pos, hid in enumerate(rank_list, 1):
            rank_pos_map.setdefault(hid, pos)
            if hid in allowed_ids and hid not in earliest_pool_rank:
                earliest_pool_rank[hid] = (int(eval_round), int(pos))
        proposal_pos_map: dict[str, int] = {}
        for idx, prop in enumerate(parsed.get("proposals") or [], 1):
            phid = str(prop.get("hypothesis_id") or "")
            if phid:
                proposal_pos_map.setdefault(phid, len(rank_list) + idx)
        for item in compiled:
            hid = str(item.get("hypothesis_id") or "")
            within_pos = rank_pos_map.get(
                hid, proposal_pos_map.get(hid, len(rank_list) + 999))
            sig = net_reaction_signature(item.get("reaction_spec") or {})
            if hid in accumulated_by_id:
                prev = accumulated_by_id[hid]
                prev_sig = net_reaction_signature(
                    prev.get("reaction_spec") or {})
                if prev_sig == sig:
                    updated = dict(item)
                    updated["first_pass_round"] = int(
                        prev["first_pass_round"])
                    updated["first_pass_pos"] = int(prev["first_pass_pos"])
                    accumulated_by_id[hid] = updated
                else:
                    alt_id = f"{hid}@r{prev['first_pass_round']}"
                    if alt_id not in accumulated_by_id:
                        prev_copy = dict(prev)
                        prev_copy["hypothesis_id"] = alt_id
                        accumulated_by_id[alt_id] = prev_copy
                    entry_copy = dict(item)
                    entry_copy["first_pass_round"] = int(eval_round)
                    entry_copy["first_pass_pos"] = int(within_pos)
                    accumulated_by_id[hid] = entry_copy
            else:
                entry_copy = dict(item)
                entry_copy["first_pass_round"] = int(eval_round)
                entry_copy["first_pass_pos"] = int(within_pos)
                accumulated_by_id[hid] = entry_copy

    def _model_proposals_product_first(self, receipt: dict,
                                       prepared_entries: list, *,
                                       substrate_profile=None) -> dict:
        """B 臂取响应 + 编译核验 + 有界核验反馈循环(E7 + P0-1/P0-2)。

        - 首发(经真实通道或脚本队列);
        - 解析(product_first 协议)→ 逐条 novel 编译核验;
        - P0-1:跨轮保留所有已通过 ``full`` 核验的 novel 提案(记录首次通过
          轮次与轮内位次);
        - P0-2:后续轮传输失败(超时/429 耗尽)或有池候选时的首轮传输失败
          ⇒ 回退到已落账、已核验状态,记 ``transport_aborted_round``,
          兜底绝不补发请求;仅首轮首发失败且无任何可用候选时走 run 级失败;
        - 有失败且剩余轮数 > 0 ⇒ 登记一轮反馈(kind=
          novel_verification_failed,载荷只含预注册 §5 白名单)并重取;
        - 至多 ``max_format_feedback_rounds`` 轮;预算/超限 ⇒ E9:
          池条目与已累积 full 条目照常排期(不 run 拒);
        - ``structure_unparseable``(非 JSON)仍按现行语义记 run 级
          结构失败。
        """
        action_id = receipt["action_id"]
        attempt_id = (receipt.get("attempt_refs") or [""])[0]
        allowed = {prepared["hypothesis"].hypothesis_id
                   for _, _, prepared in prepared_entries}
        real_fetch = self._real_fetch_entry()
        payload = receipt.get("payload") or {}
        substrate_smiles = str(payload.get("substrate_smiles") or "")
        policy = feedback_policy_from_ledger(self.ledger, self.run_id)
        max_rounds = int(policy["max_format_feedback_rounds"])
        if real_fetch is not None:
            try:
                fetched = self._call_real_fetch(
                    real_fetch, receipt, prepared_entries,
                    substrate_profile=substrate_profile)
            except PPV1RunError as exc:
                if exc.detail.get("kind") == "real_model_transport_failure" \
                        and prepared_entries:
                    return {
                        "request_id": str(
                            exc.detail.get("request_id") or ""),
                        "provider_kind": self.model_provider_kind,
                        "network_request_count": 1,
                        "novel_protocol": NOVEL_PROTOCOL_PRODUCT_FIRST,
                        "model_protocol_version":
                            MODEL_PROTOCOL_VERSION_PRODUCT_FIRST,
                        **_novel_bucket_identity_fields(),
                        "format_feedback_rounds_max": max_rounds,
                        "verification_rounds": 0,
                        "verification_feedback_requests": [],
                        "verification_failures": [],
                        "transport_aborted_round": {
                            "round": 0,
                            "stage": "initial",
                            "request_id": str(
                                exc.detail.get("request_id") or ""),
                            "error_kind": str(
                                exc.detail.get("error_kind") or ""),
                        },
                        "parsed_proposals": 0,
                        "abstained": True,
                        "novel_compiled": [],
                        "declared_bucket": [],
                    }
                raise
            response = fetched["response_text"]
            request = fetched["request"]
        else:
            response = self._next_model_response()
            request = self.ledger.register_model_request(
                run_id=self.run_id, action_id=action_id,
                attempt_id=attempt_id,
                provider_kind=self.model_provider_kind,
                request_key=f"decide:{action_id}", purpose="proposals",
                payload={"response": str(response)[:2000]})
        if self.crash_after == "after_request_registered":
            raise SearchCrashInjection(
                "请求已登记、无响应(B2 注入点)",
                {"action_id": action_id,
                 "request_id": request["request_id"]})
        note: dict = {
            "request_id": request["request_id"],
            "provider_kind": self.model_provider_kind,
            "network_request_count": request.get(
                "network_request_count", 0),
            "novel_protocol": NOVEL_PROTOCOL_PRODUCT_FIRST,
            "model_protocol_version": MODEL_PROTOCOL_VERSION_PRODUCT_FIRST,
            **_novel_bucket_identity_fields(),
            "format_feedback_rounds_max": max_rounds,
        }
        rounds_used = 0
        feedback_request_ids: list[str] = []
        last_parsed = None
        last_verification: tuple[list, list, list] = ([], [], [])
        final_failures: list[dict] = []
        accumulated_full_by_id: dict[str, dict] = {}
        earliest_pool_rank: dict[str, tuple[int, int]] = {}
        # P1-3 回修(2026-11-06):每次**成功解析**后从该响应的所有 novel
        # 条目累积被忽略的 reaction_spec 键名(同 ID 跨轮取并集)——
        # 核验失败/被后续反馈冲掉的早期提案的忽略事实不再只存在于末轮
        # 条目上(旧实现只汇总最终 compiled/declared ⇒ 键名丢失)。
        ignored_keys_by_id: dict[str, list[str]] = {}
        while True:
            error: ModelProtocolError | None = None
            try:
                parsed = parse_model_proposals(
                    response, allowed_hypothesis_ids=allowed,
                    protocol=NOVEL_PROTOCOL_PRODUCT_FIRST)
            except ModelProtocolError as exc:
                kind = str(exc.detail.get("kind") or "")
                if kind == FORMAT_ERROR_STRUCTURE_UNPARSEABLE:
                    # E9:非 JSON 仍按现行语义记 run 级结构失败(零反馈)
                    note["structure_failure"] = {"error_kind": kind}
                    raise PPV1RunError(
                        "模型响应结构失败(不可解析;结构失败保持,不进"
                        "格式反馈)",
                        {"kind": "model_structure_failure",
                         "error_kind": kind}) from exc
                if kind not in FEEDBACK_ELIGIBLE:
                    note["structure_failure"] = {"error_kind": kind}
                    raise PPV1RunError(
                        "模型响应结构失败(不可反馈的错误类别;结构失败"
                        "保持)", {"kind": "model_structure_failure",
                                  "error_kind": kind}) from exc
                # 格式错误:本轮无可用提案;失败项按白名单
                # format_error:<原四类> 报送
                error = _novel_verification_error(
                    [{"failure_kind": f"format_error:{kind}"}])
            else:
                novels = [p for p in parsed["proposals"]
                          if p.get("origin") == "novel"]
                compiled, declared, failures = \
                    self._verify_novel_product_first(
                        novels, substrate_smiles)
                self._accumulate_round_full(
                    accumulated_full_by_id,
                    earliest_pool_rank,
                    eval_round=rounds_used,
                    parsed=parsed,
                    compiled=compiled,
                    allowed_ids=allowed,
                )
                last_parsed = parsed
                last_verification = (compiled, declared, failures)
                for proposal in novels:
                    if proposal.get("ignored_spec_keys"):
                        _ignored_id = str(
                            proposal.get("hypothesis_id") or "")
                        _ignored_merged = set(
                            ignored_keys_by_id.get(_ignored_id) or [])
                        _ignored_merged.update(
                            str(_key) for _key in
                            proposal["ignored_spec_keys"])
                        ignored_keys_by_id[_ignored_id] = sorted(
                            _ignored_merged)
                if not failures:
                    final_failures = []
                    break
                error = _novel_verification_error(failures)
            # ---- 有失败:剩余轮数 ⇒ 登记 + 重取;否则 E9 落池 ----
            if rounds_used >= max_rounds:
                note["verification_rounds_exhausted"] = {
                    "kind": "format_feedback_budget_exhausted",
                    "used": rounds_used, "max": max_rounds}
                final_failures = list(
                    (error.detail.get("failures") or []))
                break
            round_no = rounds_used + 1
            feedback = None
            if real_fetch is not None:
                feedback = latest_format_feedback_round(
                    self.ledger, run_id=self.run_id,
                    action_id=action_id, attempt_id=attempt_id,
                    provider_kind=self.model_provider_kind,
                    error=error, response_excerpt=str(response),
                    round_index=round_no)
            if feedback is None:
                try:
                    feedback = register_format_feedback_round(
                        self.ledger, run_id=self.run_id,
                        action_id=action_id, attempt_id=attempt_id,
                        error=error, response_excerpt=str(response),
                        provider_kind=self.model_provider_kind)
                except SearchBudgetExhausted as exhausted:
                    # E9:反馈预算(轮数上限或每题真实请求额度)用尽 ⇒
                    # 丢弃未过核验 novel、已通过 full 与池条目照常排期(不 run 拒)
                    note["verification_rounds_exhausted"] = {
                        "kind": str(exhausted.detail.get("kind") or
                                    "format_feedback_budget_exhausted"),
                        "used": rounds_used, "max": max_rounds}
                    final_failures = list(
                        (error.detail.get("failures") or []))
                    break
            rounds_used = round_no
            feedback_request_ids.append(str(feedback["request_id"]))
            if self.crash_after == "after_feedback_registered":
                # EXP1 PF8 注入点:核验反馈轮已登记、响应未取(崩溃恢复
                # 必须复用同一轮原行,不另发请求/不分配新轮)
                raise SearchCrashInjection(
                    "核验反馈轮已登记、无响应(PF8 注入点)",
                    {"action_id": action_id,
                     "request_id": str(feedback["request_id"]),
                     "round": round_no})
            # 送模型的反馈对象 = 白名单 + 轮次信息(登记载荷不含轮次,
            # 见 model_protocol:载荷须可同源确定性重算)
            sent_feedback = {
                "failures": list(error.detail.get("failures") or []),
                "round": round_no,
                "rounds_left": max(0, max_rounds - round_no),
            }
            if real_fetch is not None:
                try:
                    retry_fetched = self._call_real_fetch(
                        real_fetch, receipt, prepared_entries,
                        feedback_request=feedback,
                        feedback_error=sent_feedback,
                        substrate_profile=substrate_profile)
                except PPV1RunError as exc:
                    if exc.detail.get("kind") == \
                            "real_model_transport_failure":
                        note["transport_aborted_round"] = {
                            "round": round_no,
                            "stage": "feedback",
                            "request_id": str(
                                exc.detail.get("request_id")
                                or feedback["request_id"]),
                            "error_kind": str(
                                exc.detail.get("error_kind") or ""),
                        }
                        final_failures = list(
                            (error.detail.get("failures") or []))
                        break
                    raise
                response = retry_fetched["response_text"]
            else:
                response = self._next_model_response()
        # ---- 汇总(跨轮保留 full + 末轮显式位次)----
        note["verification_rounds"] = rounds_used
        note["verification_feedback_requests"] = feedback_request_ids
        note["verification_failures"] = final_failures
        if earliest_pool_rank:
            note["_earliest_pool_rank_by_id"] = dict(earliest_pool_rank)
        if ignored_keys_by_id:
            # P1-3:跨轮累积的忽略键名(仅非空时写该键 —— clean 响应/
            # A 臂零新键;B/C 合同)
            note["novel_ignored_spec_keys"] = {
                _key: list(ignored_keys_by_id[_key])
                for _key in sorted(ignored_keys_by_id)}
        if self.enable_v14_compiler_ext_2 and self.enable_v14_sec_novel_backfill:
            last_verification = self._backfill_pass0_novel_proposals(
                substrate_smiles, last_parsed, accumulated_full_by_id,
                last_verification)
        accumulated_compiled = sorted(
            accumulated_full_by_id.values(),
            key=lambda item: str(item.get("hypothesis_id") or ""))
        if last_parsed is None:
            note["parsed_proposals"] = 0
            note["abstained"] = True
            note["novel_compiled"] = accumulated_compiled
            note["declared_bucket"] = []
            return note
        note["parsed_proposals"] = len(last_parsed["proposals"])
        note["abstained"] = last_parsed["abstained"]
        key_by_id = {prepared["hypothesis"].hypothesis_id: key
                     for key, _, prepared in prepared_entries}
        rank_by_key = {}
        for position, hyp_id in enumerate(last_parsed["rank_hypotheses"], 1):
            key = key_by_id.get(hyp_id)
            if key is not None:
                rank_by_key[key] = position
        note["rank_by_key"] = rank_by_key
        final_compiled, declared, _failures = last_verification
        final_novel_ids = {
            str(p.get("hypothesis_id") or "")
            for p in (last_parsed.get("proposals") or [])
            if p.get("origin") == "novel"}
        final_compiled_ids = {
            str(item.get("hypothesis_id") or "")
            for item in final_compiled}
        note["model_rank_by_id"] = {
            str(hid): position
            for position, hid in enumerate(last_parsed["rank_hypotheses"], 1)
            if (str(hid) not in final_novel_ids
                or str(hid) in final_compiled_ids)}
        note["novel_compiled"] = accumulated_compiled
        note["declared_bucket"] = declared
        return note

    # ------------------------------------- EXP1 C 臂(先盲写、后看池)

    def _model_proposals_blind_first(self, receipt: dict,
                                     prepared_entries: list, *,
                                     substrate_profile=None) -> dict:
        """C 臂取响应:两阶段(① 盲写 → ② 合并)产物优先 + 共用反馈轮。

        **阶段①(盲写,request_key ``decide:{action}:blind``)**:
        载荷只含底物/原子 ID 表/执行图/底物档案卡(**零池条目、零池
        证据**),系统提示词 ``v2_pf_blind``;解析(产物优先协议,
        allowed=∅)+ 编译核验 + 有界反馈(与 B 臂同一循环)。轮数事实源
        是同一 action 的持久 ``model_requests`` 轮行(两阶段共用;阶段①
        从轮号 1 确定性重放,阶段②以阶段①结束计数为轮号基准续号 ——
        resume 时同号复用原行,不跳号另配新轮)。轮耗尽/预算拒 ⇒
        **保留已通过盲写 full、进入阶段②**(不 run 拒);
        ``structure_unparseable`` 仍 run 拒。

        盲写 full 级编译条目逐个 ``_validate_edits`` 预校验 → 
        ``prepare_hypothesis``(source_refs=
        ``novel-model-proposal:product_first:blind_first``)就地追加进
        调用方的 ``prepared_entries``(新索引记入 ``self.blind_entries``,
        供 ``_run_decide`` 标 novel 来源身份;不重复 prepare)。

        崩溃注入点 ``after_blind_response``:盲写响应已落盘、阶段②
        调用前(PC5:resume 走同键 blob 零调用重放,不重发盲写请求)。

        **阶段②(合并,request_key ``decide:{action}`` 与 A/B 同键)**:
        载荷 = 现行池条目 + 盲写已核验条目(hypothesis_id=prepared 哈希
        ID,``origin=blind_first``);系统提示词 ``v2_pf``;解析
        allowed = 池 prepared ID ∪ 盲写 prepared ID;合并响应里的新
        novel 走同款核验循环(轮数继续共用,上限不变)。跨轮保留已通过
        full 核验的 novel 提案。
        """
        action_id = receipt["action_id"]
        attempt_id = (receipt.get("attempt_refs") or [""])[0]
        payload = receipt.get("payload") or {}
        substrate_smiles = str(payload.get("substrate_smiles") or "")
        real_fetch = self._real_fetch_entry()
        policy = feedback_policy_from_ledger(self.ledger, self.run_id)
        max_rounds = int(policy["max_format_feedback_rounds"])
        note: dict = {
            "provider_kind": self.model_provider_kind,
            "novel_protocol": NOVEL_PROTOCOL_BLIND_FIRST,
            "model_protocol_version": MODEL_PROTOCOL_VERSION_PRODUCT_FIRST,
            **_novel_bucket_identity_fields(),
            "format_feedback_rounds_max": max_rounds,
        }
        self.blind_entries = []
        feedback_request_ids: list[str] = []
        ignored_keys_by_id: dict[str, list[str]] = {}

        # ============================== 阶段①:盲写(零池内容)
        # 轮号从 1 起(阶段①之前没有任何反馈轮)。resume 语义:阶段①
        # 从盲写首发响应确定性重放,既有轮按**轮号**复用原行(不跳号、
        # 不另配新轮)—— 与 B 臂单阶段循环同一 resume 判据。
        blind_rounds_start = 0
        rounds_used = blind_rounds_start
        if real_fetch is not None:
            try:
                fetched = self._call_real_fetch(
                    real_fetch, receipt, prepared_entries,
                    substrate_profile=substrate_profile,
                    blind_stage=True)
            except PPV1RunError as exc:
                if exc.detail.get("kind") == "real_model_transport_failure" \
                        and prepared_entries:
                    req_id = str(exc.detail.get("request_id") or "")
                    note["request_id"] = req_id
                    note["network_request_count"] = 1
                    note["blind_stage"] = {
                        "request_id": req_id,
                        "rounds_used": 0,
                        "compiled": 0,
                        "declared": 0,
                        "failed_proposals": 0,
                        "exhausted": False,
                    }
                    note["blind_compiled"] = []
                    note["verification_rounds"] = 0
                    note["verification_feedback_requests"] = []
                    note["verification_failures"] = []
                    note["transport_aborted_round"] = {
                        "round": 0,
                        "stage": "blind_initial",
                        "request_id": req_id,
                        "error_kind": str(
                            exc.detail.get("error_kind") or ""),
                    }
                    note["parsed_proposals"] = 0
                    note["abstained"] = True
                    note["novel_compiled"] = []
                    note["declared_bucket"] = []
                    note["rank_by_key"] = {}
                    note["model_rank_by_id"] = {}
                    return note
                raise
            response = fetched["response_text"]
            blind_request = fetched["request"]
        else:
            response = self._next_model_response()
            blind_request = self.ledger.register_model_request(
                run_id=self.run_id, action_id=action_id,
                attempt_id=attempt_id,
                provider_kind=self.model_provider_kind,
                request_key=f"decide:{action_id}:blind",
                purpose="proposals",
                payload={"response": str(response)[:2000]})
        blind_parsed = None
        blind_verification: tuple[list, list, list] = ([], [], [])
        blind_failures: list[dict] = []
        blind_exhausted = False
        blind_transport_aborted = False
        blind_accumulated_by_id: dict[str, dict] = {}
        blind_earliest_dummy: dict[str, tuple[int, int]] = {}
        while True:
            error: ModelProtocolError | None = None
            try:
                parsed = parse_model_proposals(
                    response, allowed_hypothesis_ids=set(),
                    protocol=NOVEL_PROTOCOL_BLIND_FIRST)
            except ModelProtocolError as exc:
                kind = str(exc.detail.get("kind") or "")
                if kind == FORMAT_ERROR_STRUCTURE_UNPARSEABLE:
                    # E9 同语义:非 JSON 记 run 级结构失败(零反馈)
                    note["structure_failure"] = {"error_kind": kind}
                    raise PPV1RunError(
                        "模型响应结构失败(盲写阶段不可解析;结构失败保持,"
                        "不进格式反馈)",
                        {"kind": "model_structure_failure",
                         "error_kind": kind}) from exc
                if kind not in FEEDBACK_ELIGIBLE:
                    note["structure_failure"] = {"error_kind": kind}
                    raise PPV1RunError(
                        "模型响应结构失败(盲写阶段不可反馈的错误类别;"
                        "结构失败保持)",
                        {"kind": "model_structure_failure",
                         "error_kind": kind}) from exc
                error = _novel_verification_error(
                    [{"failure_kind": f"format_error:{kind}"}])
            else:
                novels = [p for p in parsed["proposals"]
                          if p.get("origin") == "novel"]
                compiled, declared, failures = \
                    self._verify_novel_product_first(
                        novels, substrate_smiles)
                self._accumulate_round_full(
                    blind_accumulated_by_id,
                    blind_earliest_dummy,
                    eval_round=rounds_used - blind_rounds_start,
                    parsed=parsed,
                    compiled=compiled,
                    allowed_ids=set(),
                )
                blind_parsed = parsed
                blind_verification = (compiled, declared, failures)
                for proposal in novels:
                    if proposal.get("ignored_spec_keys"):
                        # P1-3:解析即汇总,同 ID 跨轮取并集(盲写/合并
                        # 两阶段同一张表;失败条目同样计入 —— 它们也在
                        # 解析层携带 ignored_spec_keys)
                        _ignored_id = str(
                            proposal.get("hypothesis_id") or "")
                        _ignored_merged = set(
                            ignored_keys_by_id.get(_ignored_id) or [])
                        _ignored_merged.update(
                            str(_key) for _key in
                            proposal["ignored_spec_keys"])
                        ignored_keys_by_id[_ignored_id] = sorted(
                            _ignored_merged)
                if not failures:
                    blind_failures = []
                    break
                error = _novel_verification_error(failures)
            # ---- 有失败:剩余轮数 ⇒ 登记 + 重取;否则进入阶段② ----
            if rounds_used >= max_rounds:
                blind_exhausted = True
                blind_failures = list(error.detail.get("failures") or [])
                break
            round_no = rounds_used + 1
            feedback = None
            if real_fetch is not None:
                feedback = latest_format_feedback_round(
                    self.ledger, run_id=self.run_id,
                    action_id=action_id, attempt_id=attempt_id,
                    provider_kind=self.model_provider_kind,
                    error=error, response_excerpt=str(response),
                    round_index=round_no)
            if feedback is None:
                try:
                    feedback = register_format_feedback_round(
                        self.ledger, run_id=self.run_id,
                        action_id=action_id, attempt_id=attempt_id,
                        error=error, response_excerpt=str(response),
                        provider_kind=self.model_provider_kind)
                except SearchBudgetExhausted:
                    # E9:反馈预算用尽 ⇒ 保留已过盲写 full、照常进入合并
                    blind_exhausted = True
                    blind_failures = list(
                        error.detail.get("failures") or [])
                    break
            rounds_used = round_no
            feedback_request_ids.append(str(feedback["request_id"]))
            sent_feedback = {
                "failures": list(error.detail.get("failures") or []),
                "round": round_no,
                "rounds_left": max(0, max_rounds - round_no),
            }
            if real_fetch is not None:
                try:
                    retry_fetched = self._call_real_fetch(
                        real_fetch, receipt, prepared_entries,
                        feedback_request=feedback,
                        feedback_error=sent_feedback,
                        substrate_profile=substrate_profile,
                        blind_stage=True)
                except PPV1RunError as exc:
                    if exc.detail.get("kind") == \
                            "real_model_transport_failure":
                        note["transport_aborted_round"] = {
                            "round": round_no,
                            "stage": "blind_feedback",
                            "request_id": str(
                                exc.detail.get("request_id")
                                or feedback["request_id"]),
                            "error_kind": str(
                                exc.detail.get("error_kind") or ""),
                        }
                        blind_failures = list(
                            error.detail.get("failures") or [])
                        blind_transport_aborted = True
                        break
                    raise
                response = retry_fetched["response_text"]
            else:
                response = self._next_model_response()
        if self.crash_after == "after_blind_response":
            # PC5 注入点:盲写响应已落盘、阶段②调用前
            raise SearchCrashInjection(
                "盲写响应已落盘、合并调用未开始(PC5 注入点)",
                {"action_id": action_id,
                 "request_id": str(blind_request["request_id"])})
        if self.enable_v14_compiler_ext_2 and self.enable_v14_sec_novel_backfill:
            blind_verification = self._backfill_pass0_novel_proposals(
                substrate_smiles, blind_parsed, blind_accumulated_by_id,
                blind_verification)
        blind_compiled = sorted(
            blind_accumulated_by_id.values(),
            key=lambda item: str(item.get("hypothesis_id") or ""))
        blind_declared = list(blind_verification[1])
        blind_final_rank_map: dict[str, int] = {}
        if blind_parsed is not None:
            for _bpos, _bhid in enumerate(
                    blind_parsed.get("rank_hypotheses") or [], 1):
                blind_final_rank_map.setdefault(str(_bhid), int(_bpos))

        # ---- 盲写 full 级条目:预校验 + prepare(就地追加;不重复) ----
        from ..services.atom_tool import render as _render, \
            validate_edits as _validate_edits

        try:
            current_render = _render(substrate_smiles, "S")
        except Exception:  # noqa: BLE001 —— 底物渲染失败走执行层
            current_render = None
        substrate = _substrate_state(
            substrate_smiles, f"ppv1-substrate:{self.run_id}")
        blind_rejections: list[dict] = []
        blind_prepared_items: list[dict] = []
        for item in blind_compiled:
            hypothesis_id = str(item.get("hypothesis_id") or "")
            reaction_spec = dict(item.get("reaction_spec") or {})
            if current_render is not None:
                verdict = _validate_edits(
                    current_render, reaction_spec.get("edits") or [])
                if not verdict.get("ok"):
                    blind_rejections.append({
                        "hypothesis_id": hypothesis_id,
                        "kind": "novel_edit_prevalidation_failed",
                        "reasons": verdict.get("reasons", [])[:6]})
                    continue
            try:
                prepared = prepare_hypothesis(
                    reaction_spec,
                    parent_path_id=receipt["parent_path_id"],
                    substrate_state=substrate,
                    transformation_ref=str(
                        reaction_spec.get("transformation_ref") or ""),
                    source_refs=[{"record":
                                  "novel-model-proposal:product_first:"
                                  "blind_first"}])
            except (PPV1RunError, SearchContractError,
                    HypothesisContractError, ChemicalStateError) as exc:
                _detail = getattr(exc, "detail", None)
                _kind = ""
                if isinstance(_detail, dict):
                    _kind = str(_detail.get("kind") or "")
                blind_rejections.append({
                    "hypothesis_id": hypothesis_id,
                    "kind": _kind or type(exc).__name__,
                    "reason": str(exc)[:200]})
                continue
            entry_index = len(prepared_entries)
            prepared_id = str(prepared["hypothesis"].hypothesis_id)
            # P1-1 回修:盲写条目的**逻辑提案身份 = prepared hypothesis
            # ID**(自报 ID 与合并阶段新提案可合法同名 ⇒ 不入位次键空间;
            # 自报 ID 只留在 blind_entries/blind_compiled 披露)。
            prepared_entries.append((prepared_id, reaction_spec, prepared))
            if hypothesis_id in blind_final_rank_map:
                _b_tier = 0
                _b_round = 0
                _b_pos = blind_final_rank_map[hypothesis_id]
            else:
                _b_tier = 1
                _b_round = int(item.get("first_pass_round", 0))
                _b_pos = int(item.get("first_pass_pos", entry_index + 1))
            self.blind_entries.append({
                "index": entry_index,
                "hypothesis_id": hypothesis_id,
                "prepared_hypothesis_id": prepared_id,
                "proposal_context": dict(
                    item.get("proposal_context") or {}),
                "reaction_spec": reaction_spec,
                "blind_tier": _b_tier,
                "first_pass_round": _b_round,
                "first_pass_pos": _b_pos,
            })
            item["prepared_hypothesis_id"] = prepared_id
            blind_prepared_items.append(dict(item))
        for entry in blind_declared:
            entry["stage"] = "blind_first"
        blind_rounds_used = rounds_used - blind_rounds_start
        note["blind_stage"] = {
            "request_id": str(blind_request["request_id"]),
            "rounds_used": int(blind_rounds_used),
            "compiled": len(self.blind_entries),
            "declared": len(blind_declared),
            "failed_proposals": len(blind_failures),
            "exhausted": bool(blind_exhausted),
        }
        note["blind_compiled"] = blind_prepared_items
        if blind_rejections:
            note["blind_rejections"] = blind_rejections
        if blind_transport_aborted:
            # P0-2:盲写反馈轮传输失败 ⇒ 回退至已落账已核验状态,绝不补发阶段②请求
            note["request_id"] = str(blind_request["request_id"])
            note["network_request_count"] = blind_request.get(
                "network_request_count", 0)
            note["verification_rounds"] = rounds_used
            note["verification_feedback_requests"] = feedback_request_ids
            note["verification_failures"] = blind_failures
            note["parsed_proposals"] = (
                len(blind_parsed["proposals"])
                if blind_parsed is not None else 0)
            note["abstained"] = (
                bool(blind_parsed["abstained"])
                if blind_parsed is not None else True)
            note["novel_compiled"] = []
            note["declared_bucket"] = list(blind_declared)
            note["rank_by_key"] = {}
            note["model_rank_by_id"] = {}
            if ignored_keys_by_id:
                note["novel_ignored_spec_keys"] = {
                    key: list(value)
                    for key, value in sorted(ignored_keys_by_id.items())}
            return note

        # ============================== 阶段②:合并(池 + 盲写)
        allowed = {prepared["hypothesis"].hypothesis_id
                   for _, _, prepared in prepared_entries}
        # P1-2 回修(2026-11-06):来源标记按**盲写条目的 prepared
        # hypothesis ID** 命中(合并载荷里池条目/盲写条目都以 prepared
        # ID 出现);不再拿内部池逻辑 key 或自报 ID 做字串匹配 ——
        # 同名的真实池条目不会被误标 origin=blind_first。
        blind_prepared_ids = {entry["prepared_hypothesis_id"]
                              for entry in self.blind_entries}
        merge_transport_aborted = False
        if real_fetch is not None:
            try:
                fetched = self._call_real_fetch(
                    real_fetch, receipt, prepared_entries,
                    substrate_profile=substrate_profile,
                    blind_prepared_ids=blind_prepared_ids or None)
            except PPV1RunError as exc:
                if exc.detail.get("kind") == "real_model_transport_failure":
                    req_id = str(
                        exc.detail.get("request_id")
                        or blind_request["request_id"])
                    note["request_id"] = req_id
                    note["network_request_count"] = blind_request.get(
                        "network_request_count", 0)
                    note["transport_aborted_round"] = {
                        "round": rounds_used,
                        "stage": "merge_initial",
                        "request_id": str(
                            exc.detail.get("request_id") or ""),
                        "error_kind": str(
                            exc.detail.get("error_kind") or ""),
                    }
                    merge_transport_aborted = True
                else:
                    raise
            else:
                response = fetched["response_text"]
                request = fetched["request"]
        else:
            response = self._next_model_response()
            request = self.ledger.register_model_request(
                run_id=self.run_id, action_id=action_id,
                attempt_id=attempt_id,
                provider_kind=self.model_provider_kind,
                request_key=f"decide:{action_id}", purpose="proposals",
                payload={"response": str(response)[:2000]})
        if not merge_transport_aborted:
            if self.crash_after == "after_request_registered":
                raise SearchCrashInjection(
                    "请求已登记、无响应(B2 注入点)",
                    {"action_id": action_id,
                     "request_id": request["request_id"]})
            note["request_id"] = str(request["request_id"])
            note["network_request_count"] = request.get(
                "network_request_count", 0)
        # ---- 阶段②轮号基准:与阶段①共用同一 **持久** 轮计数 ----
        # 阶段①每轮都登记/复用 model_requests 行,其结束时的本地计数
        # == 阶段②入口的账本计数。这里从账本读回并核验(账本 < 本地
        # 计数 ⇒ 轮行被删改,结构化拒,不静默改轮号);账本 > 本地计数
        # = resume 时已有**本阶段**登记未消费的轮 ⇒ 轮号仍以本地计数
        # 为基准(同号复用原行,不跳号另配新轮洗掉已登记行)。
        ledger_rounds = format_feedback_rounds_used(
            self.ledger, action_id)
        if ledger_rounds < rounds_used:
            raise PPV1RunError(
                "阶段①结束后持久反馈轮数少于本地重放计数(轮行被删改;"
                "结构化拒,不静默改轮号另配新轮)",
                {"kind": "format_feedback_rounds_corrupt",
                 "ledger_rounds": int(ledger_rounds),
                 "replayed_rounds": int(rounds_used),
                 "action_id": action_id})
        last_parsed = None
        last_verification: tuple[list, list, list] = ([], [], [])
        final_failures: list[dict] = []
        merge_accumulated_by_id: dict[str, dict] = {}
        earliest_pool_rank: dict[str, tuple[int, int]] = {}
        merge_eval_round = 0
        while not merge_transport_aborted:
            error = None
            try:
                parsed = parse_model_proposals(
                    response, allowed_hypothesis_ids=allowed,
                    protocol=NOVEL_PROTOCOL_BLIND_FIRST)
            except ModelProtocolError as exc:
                kind = str(exc.detail.get("kind") or "")
                if kind == FORMAT_ERROR_STRUCTURE_UNPARSEABLE:
                    note["structure_failure"] = {"error_kind": kind}
                    raise PPV1RunError(
                        "模型响应结构失败(不可解析;结构失败保持,不进"
                        "格式反馈)",
                        {"kind": "model_structure_failure",
                         "error_kind": kind}) from exc
                if kind not in FEEDBACK_ELIGIBLE:
                    note["structure_failure"] = {"error_kind": kind}
                    raise PPV1RunError(
                        "模型响应结构失败(不可反馈的错误类别;结构失败"
                        "保持)", {"kind": "model_structure_failure",
                                  "error_kind": kind}) from exc
                error = _novel_verification_error(
                    [{"failure_kind": f"format_error:{kind}"}])
            else:
                novels = [p for p in parsed["proposals"]
                          if p.get("origin") == "novel"]
                compiled, declared, failures = \
                    self._verify_novel_product_first(
                        novels, substrate_smiles)
                self._accumulate_round_full(
                    merge_accumulated_by_id,
                    earliest_pool_rank,
                    eval_round=merge_eval_round,
                    parsed=parsed,
                    compiled=compiled,
                    allowed_ids=allowed,
                )
                last_parsed = parsed
                last_verification = (compiled, declared, failures)
                for proposal in novels:
                    if proposal.get("ignored_spec_keys"):
                        # P1-3:解析即汇总,同 ID 跨轮取并集(盲写/合并
                        # 两阶段同一张表;失败条目同样计入 —— 它们也在
                        # 解析层携带 ignored_spec_keys)
                        _ignored_id = str(
                            proposal.get("hypothesis_id") or "")
                        _ignored_merged = set(
                            ignored_keys_by_id.get(_ignored_id) or [])
                        _ignored_merged.update(
                            str(_key) for _key in
                            proposal["ignored_spec_keys"])
                        ignored_keys_by_id[_ignored_id] = sorted(
                            _ignored_merged)
                if not failures:
                    final_failures = []
                    break
                error = _novel_verification_error(failures)
            merge_eval_round += 1
            if rounds_used >= max_rounds:
                note["verification_rounds_exhausted"] = {
                    "kind": "format_feedback_budget_exhausted",
                    "used": rounds_used, "max": max_rounds}
                final_failures = list(
                    (error.detail.get("failures") or []))
                break
            round_no = rounds_used + 1
            feedback = None
            if real_fetch is not None:
                feedback = latest_format_feedback_round(
                    self.ledger, run_id=self.run_id,
                    action_id=action_id, attempt_id=attempt_id,
                    provider_kind=self.model_provider_kind,
                    error=error, response_excerpt=str(response),
                    round_index=round_no)
            if feedback is None:
                try:
                    feedback = register_format_feedback_round(
                        self.ledger, run_id=self.run_id,
                        action_id=action_id, attempt_id=attempt_id,
                        error=error, response_excerpt=str(response),
                        provider_kind=self.model_provider_kind)
                except SearchBudgetExhausted as exhausted:
                    note["verification_rounds_exhausted"] = {
                        "kind": str(exhausted.detail.get("kind") or
                                    "format_feedback_budget_exhausted"),
                        "used": rounds_used, "max": max_rounds}
                    final_failures = list(
                        (error.detail.get("failures") or []))
                    break
            rounds_used = round_no
            feedback_request_ids.append(str(feedback["request_id"]))
            if self.crash_after == "after_feedback_registered":
                raise SearchCrashInjection(
                    "核验反馈轮已登记、无响应(PF8 注入点)",
                    {"action_id": action_id,
                     "request_id": str(feedback["request_id"]),
                     "round": round_no})
            sent_feedback = {
                "failures": list(error.detail.get("failures") or []),
                "round": round_no,
                "rounds_left": max(0, max_rounds - round_no),
            }
            if real_fetch is not None:
                try:
                    retry_fetched = self._call_real_fetch(
                        real_fetch, receipt, prepared_entries,
                        feedback_request=feedback,
                        feedback_error=sent_feedback,
                        substrate_profile=substrate_profile,
                        blind_prepared_ids=blind_prepared_ids or None)
                except PPV1RunError as exc:
                    if exc.detail.get("kind") == \
                            "real_model_transport_failure":
                        note["transport_aborted_round"] = {
                            "round": round_no,
                            "stage": "merge_feedback",
                            "request_id": str(
                                exc.detail.get("request_id")
                                or feedback["request_id"]),
                            "error_kind": str(
                                exc.detail.get("error_kind") or ""),
                        }
                        final_failures = list(
                            (error.detail.get("failures") or []))
                        break
                    raise
                response = retry_fetched["response_text"]
            else:
                response = self._next_model_response()
        # ---- 汇总(跨轮保留 full + 末轮显式位次)----
        note["verification_rounds"] = rounds_used
        note["verification_feedback_requests"] = feedback_request_ids
        note["verification_failures"] = final_failures
        if earliest_pool_rank:
            note["_earliest_pool_rank_by_id"] = dict(earliest_pool_rank)
        if self.enable_v14_compiler_ext_2 and self.enable_v14_sec_novel_backfill:
            last_verification = self._backfill_pass0_novel_proposals(
                substrate_smiles, last_parsed, merge_accumulated_by_id,
                last_verification)
        merge_compiled_all = sorted(
            merge_accumulated_by_id.values(),
            key=lambda item: str(item.get("hypothesis_id") or ""))
        if last_parsed is None:
            note["parsed_proposals"] = 0
            note["abstained"] = True
            note["novel_compiled"] = merge_compiled_all
            note["declared_bucket"] = blind_declared
            note["rank_by_key"] = {}
            note["model_rank_by_id"] = {}
        else:
            note["parsed_proposals"] = len(last_parsed["proposals"])
            note["abstained"] = last_parsed["abstained"]
            key_by_id = {prepared["hypothesis"].hypothesis_id: key
                         for key, _, prepared in prepared_entries}
            rank_by_key = {}
            for position, hyp_id in enumerate(
                    last_parsed["rank_hypotheses"], 1):
                key = key_by_id.get(hyp_id)
                if key is not None:
                    rank_by_key[key] = position
            note["rank_by_key"] = rank_by_key
            # C3 / P1-1 回修(2026-11-06):位次表只按**合并阶段
            # prepared hypothesis ID** 命名空间披露(池条目/盲写条目在
            # 合并载荷里都以 prepared ID 出现)。合并响应里的自报 ID
            # 只在它指**合并阶段新提案**时才有意义 ⇒ 放进
            # model_rank_self_reported_ids 披露字段,由 _run_decide 在
            # prepare 后翻译为对应 prepared ID 合入本表;同名的新提案
            # 优先,未被提及的盲写条目落确定性 fallback(不再借同名
            # 自报 ID 继承位次)。
            known_prepared = {
                str(prepared["hypothesis"].hypothesis_id)
                for _, _, prepared in prepared_entries}
            raw_rank = {
                str(hid): position
                for position, hid in enumerate(
                    last_parsed["rank_hypotheses"], 1)}
            note["model_rank_by_id"] = {
                hid: position for hid, position in raw_rank.items()
                if hid in known_prepared}
            final_compiled, declared, _failures = last_verification
            final_novel_ids = {
                str(p.get("hypothesis_id") or "")
                for p in (last_parsed.get("proposals") or [])
                if p.get("origin") == "novel"}
            final_compiled_ids = {
                str(item.get("hypothesis_id") or "")
                for item in final_compiled}
            self_reported = {
                hid: {"position": int(position),
                      "prepared_hypothesis_id": ""}
                for hid, position in raw_rank.items()
                if (hid not in known_prepared
                    and (hid not in final_novel_ids
                         or hid in final_compiled_ids))}
            if self_reported:
                note["model_rank_self_reported_ids"] = {
                    hid: self_reported[hid] for hid in sorted(
                        self_reported,
                        key=lambda _k: (self_reported[_k]["position"], _k))}
            for entry in declared:
                entry["stage"] = "merge"
            note["novel_compiled"] = merge_compiled_all
            note["declared_bucket"] = list(blind_declared) + list(declared)
        if ignored_keys_by_id:
            # PC8:被忽略的模型自写键名(逐条 hypothesis_id;两阶段合并;
            # 无忽略键 ⇒ 该 note 键不出现 —— B 臂 clean 响应零增量)
            note["novel_ignored_spec_keys"] = {
                key: list(value)
                for key, value in sorted(ignored_keys_by_id.items())}
        return note

    def _backfill_pass0_novel_proposals(
        self,
        substrate_smiles: str,
        parsed_obj: dict | None,
        accumulated_by_id: dict[str, dict],
        verification_tuple: tuple[list, list, list],
    ) -> tuple[list, list, list]:
        """v1.4 T14-4: Pass 0 (B/C 臂) 池外 novel 对称回补。

        当 ``enable_v14_compiler_ext_2`` 与 ``enable_v14_sec_novel_backfill``
        同时开启时，对反馈循环结束后未进入 ``accumulated_by_id`` 的 novel
        提案，走与次级 pass 完全同源的 ``compile_s5_candidate_to_spec``
        11 门核验回补（默认关闭 ⇒ 零调用、零字节漂移）。
        """
        if parsed_obj is None or not substrate_smiles:
            return verification_tuple
        from ..services.s5_hybrid_choice import compile_s5_candidate_to_spec

        try:
            sub_iso = _substrate_state(
                substrate_smiles, f"ppv1-substrate:{self.run_id}"
            ).smiles_isomeric
        except Exception:  # noqa: BLE001
            sub_iso = str(substrate_smiles)
        added: list[dict] = []
        for idx, prop in enumerate(parsed_obj.get("proposals") or []):
            if not isinstance(prop, dict) or prop.get("origin") != "novel":
                continue
            hid = str(prop.get("hypothesis_id") or "")
            if not hid or hid in accumulated_by_id:
                continue
            spec_in_fb = dict(prop.get("reaction_spec") or {})
            expect_fb = spec_in_fb.get("expectation")
            expect_smi_fb = (
                str(expect_fb.get("target_smiles") or "").strip()
                if isinstance(expect_fb, dict) else ""
            )
            exp_prods_fb = (
                spec_in_fb.get("expected_products")
                or prop.get("expected_products") or []
            )
            first_exp_fb = (
                str(exp_prods_fb[0]).strip()
                if isinstance(exp_prods_fb, list) and exp_prods_fb else ""
            )
            fb_target = str(
                spec_in_fb.get("product_smiles")
                or spec_in_fb.get("target_product_smiles")
                or expect_smi_fb
                or first_exp_fb
                or prop.get("product_smiles")
                or prop.get("target_product_smiles")
                or ""
            ).strip()
            if not fb_target:
                continue
            raw_cops_fb = (
                spec_in_fb.get("coproducts")
                or prop.get("coproducts") or []
            )
            fb_cop_sets = (
                [[str(c).strip() for c in raw_cops_fb if str(c).strip()]]
                if isinstance(raw_cops_fb, list) and raw_cops_fb
                else None
            )
            fb_spec = None
            try:
                fb_spec = compile_s5_candidate_to_spec(
                    sub_iso,
                    {"cand_smiles": fb_target},
                    index=160 + idx,
                    is_gated_supplement=False,
                    coproduct_sets=fb_cop_sets,
                    extended_stereo_dissolution=True,
                    stereo_edit_graceful_fallback=True,
                    allow_ring_cleavage_and_fused_dearomatization=True,
                    retained_tetrahedral_parity_check=True,
                    allow_aromatic_ring_closure=True,
                )
            except Exception:  # noqa: BLE001
                fb_spec = None
            if fb_spec is None and fb_cop_sets is not None:
                try:
                    fb_spec = compile_s5_candidate_to_spec(
                        sub_iso,
                        {"cand_smiles": fb_target},
                        index=160 + idx,
                        is_gated_supplement=False,
                        coproduct_sets=None,
                        extended_stereo_dissolution=True,
                        stereo_edit_graceful_fallback=True,
                        allow_ring_cleavage_and_fused_dearomatization=True,
                        retained_tetrahedral_parity_check=True,
                        allow_aromatic_ring_closure=True,
                    )
                except Exception:  # noqa: BLE001
                    fb_spec = None
            if fb_spec is not None:
                entry = {
                    "hypothesis_id": hid,
                    "proposal_context": dict(prop.get("proposal_context") or {}),
                    "reaction_spec": dict(fb_spec),
                    "verification_tier": "s5_backfill",
                    "first_pass_round": 0,
                    "first_pass_pos": idx + 1,
                }
                accumulated_by_id[hid] = entry
                added.append(entry)
        if not added:
            return verification_tuple
        added_ids = {str(e.get("hypothesis_id") or "") for e in added}
        return (
            list(verification_tuple[0]) + added,
            [
                d for d in verification_tuple[1]
                if str(d.get("hypothesis_id") or "") not in added_ids
            ],
            verification_tuple[2],
        )

    def _real_fetch_entry(self):
        """S5b 接线判定:注入对象带 ppv1_real_fetch 即改"取响应"一步。

        登记 provider_kind 仍按 plan.model.provider_kind(real=占
        max_real_model_requests 额度、network=1;scripted 桩=网络 0、
        不占真实额度——测试/冒烟路径)。无对象/无方法 ⇒ None(旧行为
        逐字节不变)。"""
        if self.model is None:
            return None
        fetch = getattr(self.model, "ppv1_real_fetch", None)
        return fetch if callable(fetch) else None

    def _stage1_class_routing(self, fetch, receipt: dict) -> dict:
        """v1.3 T11 Stage 1:盲底物大类路由一次调用(零池条目)。

        载荷只含底物 SMILES/原子 ID 映射/执行图(适配层再补确定性
        RDKit 组成与官能团摘要);系统提示词 = Stage 1 合同。响应严格
        解析;坏 JSON/非法标签 ⇒ ``parsed=False`` + 原错误摘要(调用方
        走软降级,不重发、不丢题)。

        传输失败仍按既有语义包装为 ``PPV1RunError``(失败/超时/悬空占
        额度,失败题留分母)。
        """
        from .real_model import (
            CLASS_ROUTING_PROMPT_VERSION,
            CLASS_ROUTING_STAGE1_SYSTEM_PROMPT,
            execution_graph_payload,
            parse_class_routing_response,
            substrate_atom_id_map,
        )

        payload = receipt.get("payload") or {}
        substrate_smiles = str(payload.get("substrate_smiles") or "")
        routing_payload = {
            "substrate_smiles": substrate_smiles,
            "atom_id_map": substrate_atom_id_map(substrate_smiles),
            "execution_graph": execution_graph_payload(substrate_smiles),
        }
        try:
            fetched = fetch(
                ledger=self.ledger, run_id=self.run_id,
                action_id=str(receipt["action_id"]),
                attempt_id=(receipt.get("attempt_refs") or [""])[0],
                prompt_payload=routing_payload,
                request_key=(
                    f"decide:{receipt['action_id']}:class_routing"),
                purpose="class_routing",
                request=None,
                feedback_error=None,
                provider_kind=self.model_provider_kind,
                system_prompt=CLASS_ROUTING_STAGE1_SYSTEM_PROMPT)
        except Exception as exc:  # 传输/装配失败 ⇒ 结构化 run 失败
            detail = dict(getattr(exc, "detail", {}) or {})
            detail.setdefault("kind", "real_model_call_failure")
            raise PPV1RunError(
                f"Stage 1 盲底物路由调用失败({type(exc).__name__};失败/"
                "超时/悬空占额度,失败题留分母):"
                f"{str(exc)[:300]}", detail) from exc
        request = dict(fetched.get("request") or {})
        text = str(fetched.get("response_text") or "")
        try:
            routing = parse_class_routing_response(text)
            parsed = True
        except ValueError as exc:
            routing = {
                "primary_class": None,
                "secondary_class": None,
                "rationale": "",
                "parse_error": str(exc)[:200],
            }
            parsed = False
        return {
            "request_id": str(request.get("request_id") or ""),
            "parsed": parsed,
            "routing": routing,
            "prompt_version": CLASS_ROUTING_PROMPT_VERSION,
        }

    def _call_real_fetch(self, fetch, receipt: dict, prepared_entries,
                         *, feedback_request: dict | None = None,
                         feedback_error: dict | None = None,
                         substrate_profile=None,
                         blind_stage: bool = False,
                         blind_prepared_ids: set | None = None) -> dict:
        """真实取响应一步(登记→sent→complete→记账;错误包装为
        PPV1RunError 结构化失败,失败题留分母,不吞)。

        候选证据卡(Plan v1 §2.1;设计书 EVIDENCE_CARD_DESIGN_NOTE_
        2026-10-15):池条目携带 ``evidence`` 子对象 + 载荷顶层
        ``substrate_evidence``——candidate_evidence 纯函数,只读
        spec/prepared/底物 RDKit 计算,池/检索/判分零触碰;decide 与
        格式反馈轮共用本入口(证据一致)。

        chain14 批级开关(A/B 唯一差分变量;预注册 CHAIN14_EVIDENCE_
        AB_PREREG_2026-10-15):``evidence_card_enabled=false``(A 臂
        对照)⇒ 池条目不带 ``evidence`` 子对象、不传 ``substrate_
        evidence`` ⇒ 载荷 = 证据卡实施前四字段形状(逐字节兼容;系统
        提示词两臂同版,PROPOSALS_PROMPT_VERSION 不变);true(B 臂)
        ⇒ 现行 candidate-evidence-2 行为。

        P2 版本开关(2026-10-21,§3.3):``evidence_card_version=
        "v1card"`` ⇒ **v2 system prompt + v1 证据卡**(candidate_
        evidence_payload/substrate_evidence_payload、schema/
        descriptor=v1、默认 JSON 分隔符)⇒ 用户载荷与 v1 B 臂逐字节
        相同;``"v2"`` ⇒ v2 prompt + v2 证据卡/schema/紧凑分隔符。

        EXP1 C 臂(2026-11-06):``blind_stage=True`` ⇒ 盲写阶段 ——
        **池条目零渲染**(``pool_hypotheses=[]``)、系统提示词
        ``v2_pf_blind``、request_key 加 ``:blind`` 后缀;底物档案卡/
        执行图照常。``blind_prepared_ids`` ⇒ 合并阶段渲染池条目时对
        **prepared hypothesis ID 命中**的条目附加 ``origin="blind_first"``
        (P1-2 回修:不按内部池逻辑 key / 模型自报 ID 做字串匹配;
        build_proposals_user_payload 条件渲染;A/B 臂条目永不带 ⇒
        载荷逐字节不变)。
        """
        payload = receipt.get("payload") or {}
        substrate_smiles = str(payload.get("substrate_smiles") or "")
        from .real_model import execution_graph_payload, \
            substrate_atom_id_map
        prompt_payload = {
            "substrate_smiles": substrate_smiles,
            "atom_id_map": substrate_atom_id_map(substrate_smiles),
            # W5:同一执行图载荷(与 W1 编译器/execute_edits 同一事实源;
            # 模型不自猜 RDKit 解析/Kekulé)
            "execution_graph": execution_graph_payload(substrate_smiles),
        }
        if self.disable_atomtool_prompt:
            # 论文消融 v1.4 ①:纯 SMILES 协议 —— 适配器不注入
            # execution_graph / substrate_atom_id_map(标志缺省 ⇒ True
            # ⇒ 既有载荷逐字节不变)。
            prompt_payload["include_atomtool_view"] = False
        fetch_kwargs: dict = {}
        # EXP1:系统提示词按 novel 协议选(C 臂盲写 = v2_pf_blind;B 臂
        # 与 C 臂合并 = v2_pf;A 臂 v2/缺省不变)
        product_first = self.novel_protocol in (NOVEL_PROTOCOL_PRODUCT_FIRST,
                                                NOVEL_PROTOCOL_BLIND_FIRST)
        blind = bool(blind_stage)
        blind_prepared_id_set = {
            str(_pid) for _pid in (blind_prepared_ids or set())}
        prompt_version = ("v2_pf_blind" if blind
                          else ("v2_pf" if product_first else "v2"))
        if self.disable_atomtool_prompt:
            # 论文消融 v1.4 ①:Raw-SMILES 合同(产物优先 + 12 类大类
            # 审题引导;零 edits/atom_id/donor/alignment 描述)。
            prompt_version = "v3_type_raw_smiles"
        # ---- v1.3 T11:Stage 1 盲底物路由 → Stage 2 排序提示 ----
        # 开关关闭或盲写阶段 ⇒ 整块不执行(零字节漂移)。Stage 1 先于
        # Stage 2 发送(实时路径与 v13_t1b_replay 按 (saved_at,
        # request_id) 回放两个 blob 的次序一致)。解析失败 ⇒ 软降级:
        # 默认池序 + routing_tier="unrouted",不重发、不丢题。
        class_by_hypothesis: dict[str, str] = {}
        tier_by_hypothesis: dict[str, str] = {}
        routing_note: dict = {}
        routing_classes: dict | None = None
        if self.enable_v13_two_stage_routing and not blind:
            stage1 = self._stage1_class_routing(fetch, receipt)
            routing_note = {
                "request_id": stage1["request_id"],
                "parsed": stage1["parsed"],
                "prompt_version": stage1["prompt_version"],
                "response": stage1["routing"],
            }
            if stage1["parsed"]:
                primary = stage1["routing"]["primary_class"]
                secondary = stage1["routing"]["secondary_class"]
                routing_classes = {
                    "primary_class": primary,
                    "secondary_class": secondary,
                }
            from ..services.s5_hybrid_choice import (
                classify_reaction_12class,
            )
            for _key, _spec, _prepared in prepared_entries:
                _pid = str(_prepared["hypothesis"].hypothesis_id)
                _raw = str(_spec.get("reaction_class_12") or "").strip()
                if not _raw or _raw.lower() in ("none", "null"):
                    # 入口 B:池条目缺标签 ⇒ 渲染侧确定性兜底
                    try:
                        _raw = classify_reaction_12class(
                            substrate_smiles,
                            str(_spec.get("product_smiles") or ""))[1]
                    except Exception:  # noqa: BLE001 —— 如实 unknown
                        _raw = "other_unknown"
                class_by_hypothesis[_pid] = _raw
                if routing_classes is None:
                    tier_by_hypothesis[_pid] = "unrouted"
                elif _raw == routing_classes["primary_class"]:
                    tier_by_hypothesis[_pid] = "primary"
                elif _raw == routing_classes["secondary_class"]:
                    tier_by_hypothesis[_pid] = "secondary"
                else:
                    tier_by_hypothesis[_pid] = "other"
        # v1.3 T8:分域提示词(只有原子编辑合同 + 无证据卡路径可达;
        # 构造期已 fail-closed 校验;系统提示词在下方显式注入)
        if self.enable_v13_prompt_v3_type:
            prompt_version = "v3_type"
        elif self.enable_v13_prompt_v3_site:
            prompt_version = "v3_site"

        def _pool_entry(_key, spec, prepared, evidence) -> dict:
            prepared_id = str(prepared["hypothesis"].hypothesis_id)
            entry = {
                "hypothesis_id": prepared["hypothesis"].hypothesis_id,
                "product_smiles": str(spec.get("product_smiles") or ""),
                "transformation_ref": str(spec.get("transformation_ref")
                                          or ""),
                "coproducts": [str(c) for c in (spec.get("coproducts")
                                                or [])],
            }
            if evidence is not None:
                entry["evidence"] = evidence
            if blind_prepared_id_set and \
                    prepared_id in blind_prepared_id_set:
                # C 臂合并阶段:第①阶段已核验的盲写提案(可排序条目);
                # 判据 = prepared hypothesis ID(P1-2:不按逻辑 key /
                # 模型自报 ID 匹配,同名池条目不被误标)
                entry["origin"] = BLIND_FIRST_ORIGIN
            if self.enable_v13_two_stage_routing and not blind:
                # T11:仅开关打开时透传(关闭 ⇒ 键不出现 ⇒ 载荷逐字节
                # 与改前同);类别缺失已在上方渲染侧兜底补齐。
                entry["reaction_class_12"] = class_by_hypothesis.get(
                    prepared_id, "other_unknown")
                entry["routing_tier"] = tier_by_hypothesis.get(
                    prepared_id, "unrouted")
            return entry

        if self.evidence_card_version == "v2":
            # P2：v2 证据字段（两臂共享 v2 prompt；A 臂只省略证据键）
            from .candidate_evidence import (
                CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2,
                candidate_evidence_payload_v2,
                substrate_evidence_from_facts_v2,
                substrate_facts_v2,
            )
            from .real_model import proposals_system_prompt

            substrate_facts = substrate_facts_v2(substrate_smiles)
            # C 臂盲写:池条目零渲染(零池条目/零池证据)
            prompt_payload["pool_entries"] = [] if blind else [
                _pool_entry(
                    _key, spec, prepared,
                    (candidate_evidence_payload_v2(
                        spec=spec, prepared=prepared,
                        substrate_facts=substrate_facts)
                     if self.evidence_card_enabled else None))
                for _key, spec, prepared in prepared_entries]
            if self.evidence_card_enabled:
                prompt_payload["substrate_evidence"] = \
                    substrate_evidence_from_facts_v2(
                        substrate_facts,
                        substrate_profile=substrate_profile)
            fetch_kwargs = {
                "system_prompt": proposals_system_prompt(prompt_version),
                "schema_version": CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2,
            }
        else:
            from .candidate_evidence import (
                CANDIDATE_EVIDENCE_SCHEMA_VERSION,
                candidate_evidence_payload,
                substrate_evidence_payload,
            )
            prompt_payload["pool_entries"] = [] if blind else [
                _pool_entry(
                    _key, spec, prepared,
                    (candidate_evidence_payload(
                        spec=spec, prepared=prepared)
                     if self.evidence_card_enabled else None))
                for _key, spec, prepared in prepared_entries]
            if self.evidence_card_enabled:
                # 候选证据卡底物级(官能团/参考描述符/在线档案值;纯函数;
                # 开关 off ⇒ 键不渲染,载荷与实施前逐字节同)
                prompt_payload["substrate_evidence"] = \
                    substrate_evidence_payload(
                        substrate_smiles,
                        substrate_profile=substrate_profile)
            if self.evidence_card_version == "v1card":
                # P2 A 臂（v2 prompt + v1 卡）：证据载荷/schema/
                # descriptor 全沿 v1（上面同一组纯函数）；只换 system
                # prompt。schema_version 传 v1 常量 ⇒ 载荷继续用默认
                # 分隔符 ⇒ 用户 JSON 与 v1 B 臂逐字节相同（不得走
                # v2 B 的紧凑分隔符）。
                from .real_model import proposals_system_prompt
                fetch_kwargs = {
                    "system_prompt": proposals_system_prompt(prompt_version),
                    "schema_version": CANDIDATE_EVIDENCE_SCHEMA_VERSION,
                }
        if product_first and not fetch_kwargs:
            # EXP1 B/C 臂且无证据卡版本键:产物优先合同是协议的一部分
            # (不是证据卡),系统提示词仍取 v2_pf(盲写阶段 v2_pf_blind);
            # A 臂缺省路径不设 fetch_kwargs ⇒ v1 prompt 逐字节不变
            from .real_model import proposals_system_prompt

            fetch_kwargs = {
                "system_prompt": proposals_system_prompt(prompt_version)}
        if self.enable_v13_two_stage_routing and not blind:
            # T11 Stage 2:零删池稳定分组重排(primary → secondary →
            # other;组内保持原相对顺序;unrouted 归 other 组序),
            # 顶层 class_routing 仅在解析成功时渲染(失败 ⇒ 默认池序,
            # 不渲染 class_routing,软降级见 routing_note)。
            _entries = list(prompt_payload.get("pool_entries") or [])
            # 稳定排序:同 tier 保持原相对顺序(Python sort 稳定),
            # 集合/基数零变化(零删池;条目只换序,不增不减)。
            prompt_payload["pool_entries"] = \
                order_pool_entries_by_routing_tier(_entries)
            if routing_classes is not None:
                prompt_payload["class_routing"] = dict(routing_classes)
            from .real_model import proposals_system_prompt

            fetch_kwargs = dict(fetch_kwargs)
            fetch_kwargs["system_prompt"] = proposals_system_prompt(
                "v13_routing")
        if self.enable_v13_prompt_v3_type or self.enable_v13_prompt_v3_site:
            # v1.3 T8:显式注入 v3 系统提示词(A 臂缺省路径不设
            # fetch_kwargs ⇒ 关闭时仍走适配器默认 v1 prompt,零漂移)
            from .real_model import proposals_system_prompt

            fetch_kwargs = dict(fetch_kwargs)
            fetch_kwargs["system_prompt"] = proposals_system_prompt(
                prompt_version)
        if self.enable_v13_two_stage_routing and not blind:
            # Stage 2 分组披露(零删池:总数 = prepared 条目数)
            _counts = {"primary": 0, "secondary": 0, "other": 0,
                       "unrouted": 0}
            for _tier in tier_by_hypothesis.values():
                _counts[str(_tier)] = _counts.get(str(_tier), 0) + 1
            routing_note["tier_counts"] = _counts
            routing_note["pool_entries_total"] = len(
                prompt_payload.get("pool_entries") or [])
            # 注意:不改写 ``prompt_version``(那是 Stage 1 提示词 sha256,
            # 供身份披露);Stage 2 提示词身份另键记录。
            routing_note["stage2_prompt_version"] = "v13_routing"
        try:
            fetched = fetch(
                ledger=self.ledger, run_id=self.run_id,
                action_id=str(receipt["action_id"]),
                attempt_id=(receipt.get("attempt_refs") or [""])[0],
                prompt_payload=prompt_payload,
                request_key=(
                    f"decide:{receipt['action_id']}:blind" if blind
                    else f"decide:{receipt['action_id']}"),
                purpose="proposals",
                request=feedback_request,
                feedback_error=feedback_error,
                provider_kind=self.model_provider_kind,
                **fetch_kwargs)
        except Exception as exc:  # 传输/装配失败 ⇒ 结构化 run 失败
            detail = dict(getattr(exc, "detail", {}) or {})
            detail.setdefault("kind", "real_model_call_failure")
            raise PPV1RunError(
                f"真实模型调用失败({type(exc).__name__};失败/超时/悬空"
                "占额度,失败题留分母;429 有界重试已在传输层完成):"
                f"{str(exc)[:300]}", detail) from exc
        if routing_note:
            fetched = dict(fetched)
            fetched["class_routing_note"] = routing_note
        return fetched

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
        # W1 #9:followup 调度按 distinct 状态生成唯一条目(事件参与物
        # 语义完整保留在事件载荷;同 state 重复不重复调度)
        product_refs: list[str] = []
        for state in prepared["product_states"]:
            if state.state_id not in product_refs:
                product_refs.append(state.state_id)
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


def _derive_endpoint_and_native_result(ledger: SearchLedger,
                                       report: dict,
                                       driver: _Driver) -> dict:
    """S4a+S4b:公共 start/resume 的 endpoint 四分账派生 + 独立持久化 +
    首消费读回 + 原生结果对象(确定性规范化)+ **正式文件导出 +
    v3 有损投影 + 双首消费读回**。

    - 派生只读业务表(零 event/attempt/request/budget 写入;唯一
      写入 = stop_reason_records/endpoint_records 两张派生投影表、
      原生结果 artifact、导出/投影文件);
    - 派生后立即以 read_run_endpoint 首消费读回(版本门/hash/跨表
      引用/staleness 自校验 —— 派生与消费共用同一判据来源,不留
      "只写不读"的未验证窗口);
    - 原生结果对象消费已验证 endpoint 记录(过期/损坏记录不包装成
      "正式结果");
    - S4b:导出(payload+manifest)与 v3 投影后各自立即首消费读回
      (integrity/version/引用/策略/staleness 自校验);
    - 派生/导出失败(如上下文 artifact 首消费失败)⇒ 结构化
      EndpointContractError/NativeExportContractError 上抛(不吞成
      成功;已写入的派生行与事件如实保留,下次派生幂等更新)。
    """
    record = derive_run_endpoint(
        ledger, stop_report=report, run_error=driver.run_error,
        plan=driver.plan)
    verified = read_run_endpoint(ledger, ledger.run_id)
    native = build_native_result(ledger, endpoint_record=verified)
    persisted_native = persist_native_result(ledger, native)
    run_dir = Path(ledger.artifact_store.base).parent
    export_out = export_native_result(ledger, native, run_dir)
    read_native_export(ledger, run_dir, export_out["export_digest"])
    v3_payload = build_v3_projection(
        ledger, native, native_export=export_out, run_dir=run_dir)
    v3_out = persist_v3_projection(run_dir, v3_payload)
    read_v3_projection(run_dir, v3_out["projection_digest"], ledger=ledger)
    return {
        "record": record,
        "verified": verified,
        "native_result": {
            "content_digest": persisted_native["content_digest"],
            "task_key": persisted_native["task_key"],
            "native_result_version": native["native_result_version"],
            "note": ("S4a 对象底座:完整字段 + 确定性规范化(同事实同 "
                     "digest);正式文件导出见 native_export"),
        },
        "native_export": _native_export_summary(export_out),
        "v3_projection": _v3_projection_summary(v3_out, v3_payload),
    }


def _native_export_summary(export_out: dict) -> dict:
    return {
        "export_digest": export_out["export_digest"],
        "dir": export_out["dir"],
        "payload_sha256": export_out["payload_sha256"],
        "content_digest": export_out["content_digest"],
        "schema_version": export_out["schema_version"],
        "export_policy_version": export_out["export_policy_version"],
        "note": ("S4b 正式文件导出(全量事实 + manifest 新鲜度锚);"
                 "读取/消费走 read_native_export(首消费:missing/"
                 "corrupt/version/policy/stale/reference 拒)"),
    }


def _v3_projection_summary(v3_out: dict, v3_payload: dict) -> dict:
    return {
        "projection_digest": v3_out["projection_digest"],
        "dir": v3_out["dir"],
        "native_export_digest": v3_payload["native_reference"][
            "native_export_digest"],
        "lossy_projection": True,
        "steps": len(v3_payload["route"]["steps"]),
        "information_loss_axes": sorted(
            loss["axis"] for loss in v3_payload["information_losses"]),
        "note": ("v3 有损投影(lossy_projection;原生引用 + 信息损失"
                 "清单);反向消费禁止 —— 不得从投影改写原生事实/事件;"
                 "读取走 read_v3_projection"),
    }


def _v2_identity_fields() -> dict:
    """v2 证据卡身份字段（schema/descriptor/RDKit/版本）；只在 v2 时
    进入 strategy 块。resume 侧用同一函数重算，版本漂移 ⇒ 身份不符。"""
    from rdkit import rdBase

    from .candidate_evidence import (
        CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION_V2,
        CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2,
    )

    return {
        "evidence_card_version": "v2",
        "candidate_evidence_schema_version":
            CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2,
        "candidate_evidence_descriptor_version":
            CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION_V2,
        "rdkit_version": str(rdBase.rdkitVersion),
    }


def _v1card_identity_fields() -> dict:
    """v1card 证据卡身份字段（v1 schema/descriptor + RDKit/版本；
    prereg §2.2 A 臂身份表要求 rdkit_version）。只在 v1card 时进入
    strategy 块；resume 侧用同一函数重算，版本漂移 ⇒ 身份不符。"""
    from rdkit import rdBase

    from .candidate_evidence import (
        CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION,
        CANDIDATE_EVIDENCE_SCHEMA_VERSION,
    )

    return {
        "evidence_card_version": "v1card",
        "candidate_evidence_schema_version":
            CANDIDATE_EVIDENCE_SCHEMA_VERSION,
        "candidate_evidence_descriptor_version":
            CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION,
        "rdkit_version": str(rdBase.rdkitVersion),
    }


def _strategy_block(limits: dict, *,
                    evidence_card_enabled: bool = True,
                    evidence_card_version: str | None = None) -> dict:
    """PPV1 策略块(身份记录用;搜索预算事实源是 search_limits ——
    **不从 model 派生任何真实请求预算**)。

    chain14(2026-10-15):批级证据卡开关入策略块 = run 身份记录;
    resume 侧以保存身份同判据核对(见 resume_ppv1_run 的
    evidence_card_flag_mismatch 门)。

    P2(2026-10-21):v2/v1card 证据卡版本/身份只在对应模式追加；旧
    路径不出现任何新键（off 逐字节/逐键等价）。RDKit 版本进入参数
    身份（设计 §二.2「RDKit 版本串入参数指纹」）。
    """
    block = {
        "max_depth": int(limits["max_search_depth"]),
        "max_expansions": int(limits["max_total_search_actions"]),
        "max_frontier_width": int(limits["max_product_expansion_width"]),
        "max_llm_calls": 0,
        "max_proposals": 0,
        "evidence_card_enabled": bool(evidence_card_enabled),
    }
    if evidence_card_version == "v2":
        block.update(_v2_identity_fields())
    elif evidence_card_version == "v1card":
        block.update(_v1card_identity_fields())
    return block


def _resolve_evidence_card_flag(value) -> bool:
    """chain14 证据卡开关归一(None ⇒ True = 现行行为;非 bool ⇒
    结构化拒,不猜)。批级冻结值由 worker 侧 load_evidence_card_flag
    装载后显式传入;直连调用方缺省沿证据卡实施后行为(on)。"""
    if value is None:
        return True
    if not isinstance(value, bool):
        raise PPV1RunError(
            f"证据卡开关非法值:{value!r}(须 true/false;A/B 唯一差分"
            "变量非法值 fail-closed 拒,不猜)",
            {"kind": "evidence_card_flag_invalid",
             "value": repr(value)})
    return bool(value)


def _resolve_evidence_card_version(value) -> str | None:
    """P2 证据卡版本归一：None/"v1" ⇒ None（旧路径）；"none"/"off" ⇒
    "none"（v44-Next 显式禁用证据卡）；"v1card" ⇒ "v1card"（v2 prompt
    + v1 卡）；"v2" ⇒ "v2"；其它值 fail-closed（拼错不静默落回
    v1/其它模式）。"""
    if value in (None, "v1"):
        return None
    if value in ("none", "off"):
        return "none"
    if value in ("v1card", "v2"):
        return str(value)
    raise PPV1RunError(
        f"证据卡版本非法值:{value!r}(须 None/v1/none/v1card/v2;非法值 "
        "fail-closed 拒,不猜)",
        {"kind": "evidence_card_version_invalid",
         "value": repr(value)})


def _require_v1card_evidence(version: str | None, flag: bool) -> None:
    """v1card 只定义「v2 prompt + v1 卡」一种语义；开关 false 不静默
    退回无证据路径（否则 A 臂会混成 r2 的 v2-A 语义），结构化拒。"""
    if version == "v1card" and not flag:
        raise PPV1RunError(
            "evidence_card_version=v1card 要求 evidence_card_enabled=true"
            "(不定义无证据的 v1card;false 不静默降级)",
            {"kind": "v1card_requires_evidence",
             "evidence_card_version": "v1card",
             "evidence_card_enabled": False})


def _plan_prompt_switch(plan: dict | None) -> str | None:
    """v1.3 T8:plan 内的分域提示词开关 → 版本名（默认关闭）。

    两个开关互斥；同时打开 ⇒ 结构化拒（不猜优先顺序）。只认 bool
    真值路径，缺省/False ⇒ None（旧批逐字节零漂移）。
    """
    from .real_model import (PROMPT_V3_SITE_PLAN_KEY,
                             PROMPT_V3_TYPE_PLAN_KEY)
    plan = plan or {}
    want_raw = bool(plan.get("disable_atomtool_prompt", False))
    want_type = bool(plan.get(PROMPT_V3_TYPE_PLAN_KEY, False))
    want_site = bool(plan.get(PROMPT_V3_SITE_PLAN_KEY, False))
    if want_raw:
        # 论文消融 v1.4 ①:Raw-SMILES 合同与分域提示词共用同一 system
        # prompt 槽位 ⇒ 同时打开 fail-closed;司机构造期同一拦截。
        if want_type or want_site:
            raise PPV1RunError(
                "disable_atomtool_prompt 与 v1.3 分域提示词开关互斥"
                "(同一 system prompt 槽位;fail-closed)",
                {"kind": "prompt_v3_raw_switch_conflict",
                 "disable_atomtool_prompt": True,
                 "enable_v13_prompt_v3_type": want_type,
                 "enable_v13_prompt_v3_site": want_site})
        return "v3_type_raw_smiles"
    if want_type and want_site:
        raise PPV1RunError(
            "分域提示词开关同时打开(v3_type 与 v3_site 互斥;fail-closed)",
            {"kind": "prompt_v3_switch_conflict",
             "enable_v13_prompt_v3_type": True,
             "enable_v13_prompt_v3_site": True})
    if want_type:
        return "v3_type"
    if want_site:
        return "v3_site"
    return None


def _prediction_block(model, evidence_card_version: str | None = None,
                      novel_protocol: str | None = None,
                      prompt_switch: str | None = None) -> dict:
    """模型预测身份块；v2/v1card 时把 prompt 版本替换为 v2 哈希
    （两臂共用 v2 prompt；模型对象自身 identity_block 仍报 v1，不在
    模型构造期引入开关）。

    EXP1:novel_protocol=product_first_feedback ⇒ prompt 版本替换为
    ``v2_pf`` 哈希;C 臂(``product_first_feedback_blind_first``)⇒
    双值 ``proposals``(合并,v2_pf)+ ``proposals_blind``(盲写,
    v2_pf_blind)—— A 臂/旧 run 不出现任何新键。

    D4(2026-11-06):有模型时追加 ``sampling_params`` 块（单一来源 =
    real_model.sampling_params_sent，喂同一 ``request_params`` —— 即
    发送侧真正合并进请求体的那份；未设的键记
    ``provider_default_unset``）。**A 臂也写**（CC 授权的身份新增字段；
    载荷字节不受影响）。``model is None``（off，无发送）不加该键 ——
    没有请求就没有采样参数，不记空洞事实。

    v1.3 T8(2026-11-13):``prompt_switch``(v3_type/v3_site,来自 plan
    的分域提示词开关)⇒ 把 ``proposals`` 哈希替换为对应 v3 版本;只
    允许原子编辑合同且无证据卡(v3 段按 v1 合同追加),其它组合
    fail-closed(不静默混协议)。
    """
    protocol = _resolve_novel_protocol(novel_protocol)
    if prompt_switch is not None:
        if prompt_switch not in ("v3_type", "v3_site",
                                 "v3_type_raw_smiles"):
            raise PPV1RunError(
                f"未知分域提示词开关:{prompt_switch!r}"
                "(允许 v3_type/v3_site/v3_type_raw_smiles;fail-closed)",
                {"kind": "prompt_v3_switch_invalid",
                 "prompt_switch": repr(prompt_switch)})
        if prompt_switch == "v3_type_raw_smiles":
            # 论文消融 v1.4 ①:raw 合同固定在批级 atom_edit 预算身份
            # (1 请求/0 反馈)下由 plan 开关切产物优先解析;身份块只
            # 披露真实 prompt 哈希,不改批级协议标签。
            pass
        else:
            if protocol != NOVEL_PROTOCOL_ATOM_EDIT:
                raise PPV1RunError(
                    "分域提示词只定义在原子编辑合同上(A 臂);当前 novel 协议"
                    "不兼容(fail-closed,不混协议)",
                    {"kind": "prompt_v3_protocol_conflict",
                     "prompt_switch": prompt_switch,
                     "novel_protocol": protocol})
        if evidence_card_version not in (None,):
            raise PPV1RunError(
                "分域提示词只定义在无证据卡路径上(v1 合同);当前证据卡"
                "版本不兼容(fail-closed)",
                {"kind": "prompt_v3_evidence_conflict",
                 "prompt_switch": prompt_switch,
                 "evidence_card_version": evidence_card_version})
    if model is not None:
        from .real_model import sampling_params_sent

        block = dict(model.identity_block())
        if protocol == NOVEL_PROTOCOL_BLIND_FIRST:
            from .real_model import proposals_prompt_version

            prompt_versions = dict(block.get("prompt_versions") or {})
            prompt_versions["proposals"] = proposals_prompt_version("v2_pf")
            prompt_versions["proposals_blind"] = \
                proposals_prompt_version("v2_pf_blind")
            block["prompt_versions"] = prompt_versions
        elif protocol == NOVEL_PROTOCOL_PRODUCT_FIRST:
            from .real_model import proposals_prompt_version

            prompt_versions = dict(block.get("prompt_versions") or {})
            prompt_versions["proposals"] = proposals_prompt_version("v2_pf")
            block["prompt_versions"] = prompt_versions
        elif evidence_card_version in ("v2", "v1card"):
            from .real_model import proposals_prompt_version

            prompt_versions = dict(block.get("prompt_versions") or {})
            prompt_versions["proposals"] = proposals_prompt_version("v2")
            block["prompt_versions"] = prompt_versions
        if prompt_switch is not None:
            from .real_model import proposals_prompt_version

            prompt_versions = dict(block.get("prompt_versions") or {})
            prompt_versions["proposals"] = \
                proposals_prompt_version(prompt_switch)
            block["prompt_versions"] = prompt_versions
        block["sampling_params"] = sampling_params_sent(
            block.get("request_params") or {})
        return block
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
    evidence_card_enabled: bool | None = None,
    evidence_card_version: str | None = None,
    novel_protocol: str | None = None,
    preset: str | None = None,
    enable_smart_gated_backfill: bool = False,
    s5_supplement_gate_max_s1d: int = 2,
    s5_super_consensus_score: float = 115.0,
    s5_max_supplements: int = 2,
    backfill_target_events: int = 5,
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
    effective_preset = str(
        preset or (plan or {}).get("preset") or ""
    ).strip().lower().replace("_", "-")
    is_v44_next = effective_preset == "v44-next"
    eff_evcard_version_arg = (
        evidence_card_version
        if evidence_card_version is not None
        else (
            (plan or {}).get("evidence_card_version")
            if (plan or {}).get("evidence_card_version") is not None
            else ("none" if is_v44_next else None)
        )
    )
    # chain14/P2:开关与版本先归一（非法值/未定义组合在创建 run 目录
    # 前结构化拒，不留空 run 目录阻塞同 id 重试；合法输入行为不变）
    evidence_version = _resolve_evidence_card_version(
        eff_evcard_version_arg)
    if evidence_version == "none":
        if evidence_card_enabled is True:
            raise PPV1RunError(
                "evidence_card_version=none 与 evidence_card_enabled=true 冲突",
                {"kind": "evidence_card_flag_conflict",
                 "evidence_card_version": "none",
                 "evidence_card_enabled": True})
        evidence_flag = False
        evidence_version = None
    elif is_v44_next and evidence_card_enabled is None and evidence_version is None:
        evidence_flag = False
    else:
        evidence_flag = _resolve_evidence_card_flag(evidence_card_enabled)
    _require_v1card_evidence(evidence_version, evidence_flag)
    eff_backfill = bool(
        enable_smart_gated_backfill
        or (plan or {}).get("enable_smart_gated_backfill")
        or is_v44_next
    )
    # EXP1:novel 协议先归一(非法值在建目录前拒);profile_policy 若显式
    # 声明同键必须同值(不得以 profile_policy 绕过 start 参数换臂)
    protocol = _resolve_novel_protocol(novel_protocol)
    policy_kwargs = dict(profile_policy or {})
    if eff_backfill:
        raw_sl = dict(policy_kwargs.get("search_limits") or {})
        if "max_alternative_hypotheses_per_parent" not in raw_sl:
            raw_sl["max_alternative_hypotheses_per_parent"] = max(
                5, int(backfill_target_events)
            )
        if "max_total_search_actions" not in raw_sl:
            raw_sl["max_total_search_actions"] = 12
        policy_kwargs["search_limits"] = raw_sl
    declared_protocol = policy_kwargs.pop("novel_protocol", None)
    if declared_protocol is not None and \
            str(declared_protocol) != protocol:
        raise PPV1RunError(
            "profile_policy.novel_protocol 与 start 参数不一致"
            "(同一开关不得两处异值;fail-closed)",
            {"kind": "novel_protocol_conflict",
             "profile_policy_novel_protocol": repr(declared_protocol),
             "novel_protocol": protocol})
    # 原子独占目录创建:并发 start 同一 run 只有胜者(败者
    # FileExistsError → RunAlreadyExists;不进 store/identity 写入)
    runs_root.mkdir(parents=True, exist_ok=True)
    try:
        run_dir.mkdir()
    except FileExistsError:
        from ..workflow.runner import RunAlreadyExists
        raise RunAlreadyExists(run_id, run_dir) from None
    with _DriverSession(run_dir) as session:
        policy_block = build_profile_identity_block(
            novel_protocol=protocol, **policy_kwargs)
        limits = policy_block["search_limits"]
        asset_identity = (scripted_asset_identity() if scripted
                          else retrieval_asset_identity(config))
        identity = build_run_identity(
            run_id=run_id, root_smiles=smiles, root_cn=_cn_of(smiles),
            strategy=_strategy_block(
                limits, evidence_card_enabled=evidence_flag,
                evidence_card_version=evidence_version),
            asset_identity=asset_identity,
            v3_code_identity=v3_code_identity(config.v3_code_root),
            prediction=_prediction_block(
                model, evidence_version, protocol,
                prompt_switch=_plan_prompt_switch(plan)),
            profile=PROFILE_POLLUTANT_PATHWAY_V1,
            profile_policy={**policy_kwargs, **(
                {} if protocol == NOVEL_PROTOCOL_ATOM_EDIT
                else {"novel_protocol": protocol})})
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
        raw_protocol_to_pass = novel_protocol or declared_protocol
        driver = _Driver(ledger, plan or {}, run_id, _worker_id(run_id),
                         crash_after=crash_after, model=model,
                         evidence_card_enabled=evidence_flag,
                         evidence_card_version=evidence_version,
                         novel_protocol=raw_protocol_to_pass,
                         enable_smart_gated_backfill=eff_backfill,
                         s5_supplement_gate_max_s1d=s5_supplement_gate_max_s1d,
                         s5_super_consensus_score=s5_super_consensus_score,
                         s5_max_supplements=s5_max_supplements,
                         backfill_target_events=backfill_target_events)
        root_path = driver.root_path_id
        task_key = decision_task_key(
            run_id=run_id, parent_path_id=root_path,
            context_ref=context_ref,
            frozen_pool_digest=_plan_digest(plan or {}),
            parent_search_revision=0, policy_version=search_policy_version(),
            strict_state_digest=root_state.state_id,
            tool_id="atom-tool-vendored",
            prompt_version=_plan_digest(plan or {})[:16],
            feedback_policy_version=driver.format_feedback_policy_version)
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
        # ---- S4a:endpoint 四分账派生 + 独立持久化 + 首消费 + 原生
        # 结果对象(确定性规范化;停止不是化学终点) ----
        endpoint_out = _derive_endpoint_and_native_result(
            ledger, report, driver)
        summary = _summary(store, run_id, report, resumed=False)
        summary["evidence_card_enabled"] = evidence_flag
        if evidence_version in ("v2", "v1card"):
            summary["evidence_card_version"] = evidence_version
        if protocol != NOVEL_PROTOCOL_ATOM_EDIT:
            summary.update(_novel_protocol_summary_fields(protocol))
        summary["driver_session"] = dict(session.info)
        summary["endpoint"] = endpoint_summary_fields(endpoint_out["record"])
        summary["endpoint_record_payload_hash"] = endpoint_out["record"][
            "payload_hash"]
        summary["native_result"] = dict(endpoint_out["native_result"])
        summary["native_export"] = dict(endpoint_out["native_export"])
        summary["v3_projection"] = dict(endpoint_out["v3_projection"])
        return summary


def resume_ppv1_run(
    *,
    config: V43Config,
    runs_root: str | Path,
    run_id: str,
    plan: dict | None = None,
    model=None,
    evidence_card_enabled: bool | None = None,
    evidence_card_version: str | None = None,
    novel_protocol: str | None = None,
    preset: str | None = None,
    enable_smart_gated_backfill: bool = False,
    s5_supplement_gate_max_s1d: int = 2,
    s5_super_consensus_score: float = 115.0,
    s5_max_supplements: int = 2,
    backfill_target_events: int = 5,
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
            "search_limits", "format_feedback_policy", "novel_protocol")
        if key in saved_profile_block}
    # P2：先归一见版本与开关，再重建 prediction（v2 prompt 哈希必须
    # 与保存身份一致，否则 check_resume_identity 拒绝）。版本切换检查
    # 先于身份重建，给调用方结构化错误而不是笼统的身份不符。
    effective_preset = str(
        preset or (plan or {}).get("preset") or ""
    ).strip().lower().replace("_", "-")
    is_v44_next = effective_preset == "v44-next"
    eff_evcard_version_arg = (
        evidence_card_version
        if evidence_card_version is not None
        else ("none" if is_v44_next else None)
    )
    evidence_version = _resolve_evidence_card_version(
        eff_evcard_version_arg)
    if evidence_version == "none":
        if evidence_card_enabled is True:
            raise PPV1RunError(
                "evidence_card_version=none 与 evidence_card_enabled=true 冲突",
                {"kind": "evidence_card_flag_conflict",
                 "evidence_card_version": "none",
                 "evidence_card_enabled": True})
        evidence_flag = False
        evidence_version = None
    elif is_v44_next and evidence_card_enabled is None and evidence_version is None:
        evidence_flag = False
    else:
        evidence_flag = _resolve_evidence_card_flag(evidence_card_enabled)
    _require_v1card_evidence(evidence_version, evidence_flag)
    # EXP1:novel 协议同臂核对(旧 run 身份块无该键 ⇒ atom_edit;中途
    # 换臂 ⇒ 结构化拒,在建 prediction/身份前给明确原因)
    protocol = _resolve_novel_protocol(novel_protocol)
    saved_protocol = saved_profile_block.get("novel_protocol") \
        or NOVEL_PROTOCOL_ATOM_EDIT
    if saved_protocol != protocol:
        raise PPV1RunError(
            "resume 的 novel 协议与 run 启动时不一致(A/B 唯一差分变量"
            "组不得中途换臂;差异须显式新 run/新批登记)",
            {"kind": "novel_protocol_mismatch", "run_id": run_id,
             "saved": saved_protocol, "current": protocol})
    saved_version = (saved.get("strategy") or {}).get(
        "evidence_card_version")
    if saved_version not in (None, "v2", "v1card"):
        raise PPV1RunError(
            "run 身份中的证据卡版本非法(resume fail-closed)",
            {"kind": "evidence_card_version_corrupt",
             "run_id": run_id, "saved": saved_version})
    if saved_version != evidence_version:
        raise PPV1RunError(
            "resume 的证据卡版本与 run 启动时不一致(不得中途换版本;"
            "差异须显式新 run/新批登记)",
            {"kind": "evidence_card_version_mismatch",
             "run_id": run_id, "saved": saved_version,
             "current": evidence_version})
    current_strategy = dict(saved["strategy"])
    if evidence_version == "v2":
        # 用当前 schema/descriptor/RDKit 重算 v2 身份字段；任一漂移
        # ⇒ check_resume_identity 拒绝（不静默继续旧 run）。
        current_strategy.update(_v2_identity_fields())
    elif evidence_version == "v1card":
        # 用当前 v1 schema/descriptor/RDKit 重算；漂移 ⇒ 身份不符。
        current_strategy.update(_v1card_identity_fields())
    current = build_run_identity(
        run_id=run_id, root_smiles=saved["inputs"]["root_smiles"],
        root_cn=saved["inputs"].get("root_identity"),
        strategy=current_strategy, asset_identity=current_asset,
        v3_code_identity=v3_code_identity(config.v3_code_root),
        prediction=_prediction_block(
                model, evidence_version, protocol,
                prompt_switch=_plan_prompt_switch(plan)),
        profile=PROFILE_POLLUTANT_PATHWAY_V1,
        profile_policy=profile_kwargs or None)
    check_resume_identity(saved, current)
    # ---- chain14:证据卡开关与 run 启动时同判据核对(A/B 唯一差分
    # 变量;同 run 两段载荷口径必须一致 —— 差异须显式新 run/新批)。
    # 前代身份无该键 ⇒ 按现行行为(on)兼容读取。 ----
    saved_flag = (saved.get("strategy") or {}).get(
        "evidence_card_enabled")
    if saved_flag is None:
        saved_flag = True
    if saved_flag != evidence_flag:
        raise PPV1RunError(
            "resume 的证据卡开关与 run 启动时不一致(A/B 唯一差分变量"
            "不得中途换臂;差异须显式新 run/新批登记)",
            {"kind": "evidence_card_flag_mismatch",
             "run_id": run_id, "saved": saved_flag,
             "current": evidence_flag})
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
        binding = _verify_frozen_plan_binding(
            ledger, run_id, frozen_plan,
            feedback_policy_version=format_feedback_policy_version_for(
                saved_protocol))
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
                         crash_after=crash_after, model=model,
                         evidence_card_enabled=evidence_flag,
                         evidence_card_version=evidence_version,
                         novel_protocol=saved_profile_block.get("novel_protocol"),
                         enable_smart_gated_backfill=bool(
                             enable_smart_gated_backfill or is_v44_next
                         ),
                         s5_supplement_gate_max_s1d=s5_supplement_gate_max_s1d,
                         s5_super_consensus_score=s5_super_consensus_score,
                         s5_max_supplements=s5_max_supplements,
                         backfill_target_events=backfill_target_events)
        report = driver.drive()
        # ---- S4a:endpoint 四分账派生(恢复后按当前事实重派生;重复
        # resume 同事实 ⇒ 同 payload_hash 幂等,不重复写 event/
        # attempt/request/budget) ----
        endpoint_out = _derive_endpoint_and_native_result(
            ledger, report, driver)
        summary = _summary(store, run_id, report, resumed=True)
        summary["evidence_card_enabled"] = evidence_flag
        if evidence_version in ("v2", "v1card"):
            summary["evidence_card_version"] = evidence_version
        if saved_protocol != NOVEL_PROTOCOL_ATOM_EDIT:
            summary.update(_novel_protocol_summary_fields(saved_protocol))
        summary["recovery"] = {
            "actions": recovery.get("actions"),
            "pending_requests": recovery.get("pending_requests"),
            "unknown_status_requests": recovery.get(
                "unknown_status_requests"),
            "isolated_actions": isolated,
        }
        summary["frozen_plan_binding"] = dict(binding)
        summary["driver_session"] = dict(session.info)
        summary["endpoint"] = endpoint_summary_fields(endpoint_out["record"])
        summary["endpoint_record_payload_hash"] = endpoint_out["record"][
            "payload_hash"]
        summary["native_result"] = dict(endpoint_out["native_result"])
        summary["native_export"] = dict(endpoint_out["native_export"])
        summary["v3_projection"] = dict(endpoint_out["v3_projection"])
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
