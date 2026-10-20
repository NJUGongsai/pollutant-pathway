"""S4b 原生正式导出 —— 文件级 payload + manifest + 读取/过期/完整性
首消费(契约 ppv1-native-export-3 / native-export-policy-3 登记)。

S4b 范围(任务书 §7 S4b 第 1-4 项 + §4.4 G02):把 S4a 原生结果对象
落为**正式文件导出**(run 目录 ``native_export/<export_digest>/``):

- ``payload.json``:原生结果全量载荷(canonical_json 字节,含
  content_digest;共同产物/备选/不同来路/条件/依赖/audit/proof
  scope/deferred/未展开集合/预算/停止原因/endpoint 分账全字段 ——
  导出不截断、不按 CN 合并、不改写 unknown/partial/deferred);
- ``manifest.json``:导出身份与新鲜度锚(全部版本常量、固定导出
  策略、payload 字节 sha、**graph revision 等价身份** = 全部事实表
  内容 digest、权威引用(endpoint/stop 行 hash、原生结果 artifact、
  逐 artifact 内容 hash、冻结计划))。

确定性(G02):payload 与 manifest 均无时间戳、键序固定、列表稳定
排序;``export_digest = content_hash(manifest 核心)`` ⇒ 相同事实 +
相同版本 + 相同策略 ⇒ 相同目录、相同字节(同进程/跨进程一致);
事实变化 = 新 digest = 新目录,旧导出文件**保全不覆盖**(历史保留,
按 digest 可回溯)。

首消费(读取)按固定次序核验,fail-closed 结构化拒绝(kind):

1. 文件缺失 ⇒ ``export_missing``;
2. manifest 不可解析/缺 export_digest/与请求 digest 不符 ⇒
   ``export_manifest_corrupt``(integrity);
2b. **manifest core 自身 digest 复算(S4-C02 回修)**:manifest 去掉
   export_digest 键后重算 content_hash,与声明的 export_digest 不符
   ⇒ ``export_manifest_corrupt`` —— manifest-only 改坏(run_id/契约
   版本/策略正文/引用集合,保持原 digest)不再被字面值比较放过;
3. payload 字节 sha 与 manifest 不符 ⇒ ``export_payload_corrupt``
   (integrity;保全原文件,不覆盖不重算);
4. manifest schema 版本未知 ⇒ ``export_version_unknown``(fail-closed
   不猜迁移);**契约版本块整组绑定(S4-C02)**:manifest.contract_
   versions 与当前 profile 常量逐项不符 ⇒ 同 kind 拒(自洽重写换
   版本集合不再照收);
4b. **run 绑定(S4-C02)**:manifest.run_id != ledger.run_id ⇒
   ``export_reference_mismatch``(run/版本/策略内容与当前登记源
   绑定,不是 manifest 内自洽证书);
5. payload 内容 digest 复算不符 ⇒ ``export_digest_mismatch``;
5b. **payload 原生结果版本门(S4-C04 r2,复审 R2 §4)**:payload
   的 ``native_result_version`` 缺失/非当前登记版本 ⇒
   ``export_version_unknown``(与 manifest schema/契约版本块同
   一登记源 profile 常量;自洽重封换版本不再被内容 digest 复算
   之外的口放过);
6. 权威引用断裂(endpoint/stop 行、原生结果 artifact、被引用
   artifact、冻结计划;含内容 hash 不一致)⇒
   ``export_reference_mismatch``(endpoint 记录自身的 staleness 由
   read_run_endpoint 首消费先行 —— 输入漂移先以 endpoint 拒绝浮出);
7. 导出策略 hash/正文绑定(S4-C02:manifest 自记策略正文重算 hash
   须与自记 sha256 一致,且正文须等于当前策略)不符 ⇒
   ``export_policy_stale``(stale 类;策略/版本变化后旧导出不得当
   当前结果);
8. graph facts digest 与当前持久权威不符 ⇒ ``export_stale``
   (stale 类;改变源图 ⇒ 旧结果过期,不能静默消费);
9. **必要 artifact 引用集合闭合(S4-C02;S4 回修 r2 复审 R2 §4)**:
   应有必要项由**已完成 action/task/commit + 原生实际消费
   (payload 引用)+ 冻结计划锚行**同源闭合(共用
   artifact_reference_index 索引,必要性按权威行判定),**不由
   "文件目前存在"决定** —— 删已完成任务的 production_report 文件
   + 删 manifest 同引用 + 自洽重算新 digest(文件与引用一起消失)
   不再把必要项缩成合法缺席;应有项缺文件/漏引用 ⇒ 拒(导出侧
   写入前同样先拒,不封不完整 manifest);现存集合与必要集合分别
   核,与每行 hash 校验(第 6 步)分开;合法未生产/空池/deferred/
   未完成 action 候选保持合法缺席,不一刀切所有索引候选;枚举中
   撞到损坏 artifact ⇒ 结构化 ``export_reference_mismatch`` 拒
   (坏必要 soutc 等不能被跳过)。

防"洗白":过期/损坏导出**零写入、原文件保全**;自洽重写 payload +
manifest(重算内部 hash)逃不过第 6/8/9 条 —— 引用与事实 digest 从
独立权威(DB 行 + artifact store)重算,不信任 manifest 自声明。
不做密码学签名、不抗全库协同改写(沿 S3B-01/S4a 同一边界披露)。

边界:本模块不修改 legacy/export_v3.py(v3 有损投影见
v3_projection.py);不产生新化学判定(纯派生文件);payload 即
S4a 原生结果(不另造第二套字段);导出/读取共用本模块判据,
不在其他入口复制。
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from ..domain.models import canonical_json, content_hash, stable_id
from .endpoint import read_run_endpoint
from .native_result import (
    _CONTEXT_ARTIFACT,
    _EXPANSION_OUTCOME,
    _PRODUCTION_REPORT,
    NATIVE_RESULT_ARTIFACT,
    NATIVE_RESULT_TASK_KEY,
    artifact_reference_index,
    read_native_result,
)
from .profile import (
    PPV1_ENDPOINT_POLICY_VERSION,
    PPV1_ENDPOINT_SCHEMA_VERSION,
    PPV1_NATIVE_EXPORT_POLICY_VERSION,
    PPV1_NATIVE_EXPORT_VERSION,
    PPV1_NATIVE_RESULT_VERSION,
    PPV1_PROFILE_SCHEMA_VERSION,
    PPV1_RUNFLOW_SCHEMA_VERSION,
    PPV1_SEARCH_SCHEMA_VERSION,
    PPV1_STORE_SCHEMA_VERSION,
)
from .search import (
    ACTION_KIND_EXPAND_HYPOTHESIS,
    ACTION_KIND_RETRIEVE,
    ACTION_STATUS_DONE,
    COMMIT_KIND_OUTCOME,
    SearchArtifactIntegrityError,
    read_search_artifact,
)

NATIVE_EXPORT_SUBDIR = "native_export"
NATIVE_EXPORT_PAYLOAD_FILE = "payload.json"
NATIVE_EXPORT_MANIFEST_FILE = "manifest.json"

# 冻结计划 artifact 引用(runflow 常量的单一来源;延迟导入避免
# 模块级循环:runflow → native_export → runflow 常量)
_FROZEN_PLAN_TASK_KEY = "run-plan"
_FROZEN_PLAN_ARTIFACT = "frozen_plan"


class NativeExportContractError(RuntimeError):
    """原生正式导出契约违反(结构化 fail-closed;零写入)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


class NativeExportConflict(NativeExportContractError):
    """同 digest 目录已存在不同内容(不可变导出;保全原文件)。"""


def native_export_policy() -> dict:
    """固定导出策略(ppv1-native-export-policy-3;无用户可配项)。

    变更任一规则(序列化/命名/无时间戳/manifest 组成/首消费核验集)
    须升 PPV1_NATIVE_EXPORT_POLICY_VERSION —— 旧导出按 policy stale 拒。

    v2(S4-C02 回修,确认复核 §4):首消费新增 manifest core 自身
    digest 复算、run/契约版本/策略正文与当前登记源绑定、必要
    artifact 引用集合由独立权威同源枚举后整集闭合(与每行 hash
    校验分别核)。
    v3(S4 回修 r2,复审 R2 §4):必要集合闭合的枚举语义修正 ——
    应有必要项由已完成 action/task/commit + 原生实际消费(payload
    引用)+ 冻结计划锚行同源闭合,不由"文件目前存在"决定(文件+
    引用一起消失的自洽重封不再照收;导出侧写入前同样先拒);首
    消费新增 payload 原生结果版本门(native_result_version)。
    """
    return {
        "version": PPV1_NATIVE_EXPORT_POLICY_VERSION,
        "payload_serialization": "canonical_json_sortkeys_compact_newline",
        "manifest_serialization": "canonical_json_sortkeys_compact_newline",
        "directory_naming": "native_export/<export_digest[:24]>/",
        "export_digest_basis":
            "content_hash(manifest_core_without_export_digest)",
        "payload_timestamps": "forbidden",
        "manifest_timestamps": "forbidden",
        "overwrite": "forbidden_same_digest_different_bytes_refused",
        "stale_detection": (
            "manifest_core_digest_recompute+run_and_contract_version"
            "_binding+payload_native_result_version_binding+graph"
            "_facts_digests+authority_references+necessary_artifact"
            "_reference_set_closure_from_completed_actions_commits"
            "_and_native_consumption+policy_body_and_hash"),
    }


def export_policy_hash(policy: dict) -> str:
    return hashlib.sha256(
        canonical_json(policy).encode("utf-8")).hexdigest()


def _current_contract_versions() -> dict:
    """manifest contract_versions 的当前登记源(profile 常量单一来源;
    写入与首消费绑定核验共用,不在读取侧另造第二套版本集合)。"""
    return {
        "profile": PPV1_PROFILE_SCHEMA_VERSION,
        "store": PPV1_STORE_SCHEMA_VERSION,
        "search": PPV1_SEARCH_SCHEMA_VERSION,
        "runflow": PPV1_RUNFLOW_SCHEMA_VERSION,
        "endpoint": PPV1_ENDPOINT_SCHEMA_VERSION,
        "endpoint_policy": PPV1_ENDPOINT_POLICY_VERSION,
        "native_result": PPV1_NATIVE_RESULT_VERSION,
    }


def _existing_artifact_reference_keys(ledger) -> dict:
    """**现存** artifact 引用键集合(S4-C02 r2:与必要集合分开)。

    与 _artifact_references/manifest 写入共用 artifact_reference_index
    + 冻结计划两个来源(**同一完整索引,不另修一套规则**);此处
    枚举的是"当前实际存在"的集合:缺席(尚未产出)的 artifact 不
    产空引用(合法缺席);损坏 artifact ⇒ 结构化拒(坏必要 soutc
    等不能被跳过,不静默略过后当合法缺席)。
    返回 {key: payload_hash}(key = task_key/name)。

    S4 回修 r2(复审 R2 §4):本函数只回答"文件现在在不在";**应
    有必要项**(即使文件已消失也必须被引用/存在)由
    ``_necessary_artifact_reference_keys`` 按独立权威行闭合 ——
    两集合分别核,必要性不由存在性决定。"""
    refs: dict[str, str] = {}
    for entry in artifact_reference_index(ledger):
        try:
            envelope = read_search_artifact(
                ledger.artifact_store, entry["task_key"], entry["name"])
        except SearchArtifactIntegrityError as exc:
            raise NativeExportContractError(
                f"导出必要引用的 artifact 损坏:{entry['task_key']}/"
                f"{entry['name']}(H07 完整性失败;保全原文件,不能跳过"
                "后当合法缺席)",
                {"kind": "export_reference_mismatch",
                 "artifact": f"{entry['task_key']}/{entry['name']}",
                 "artifact_error_kind": exc.detail.get("kind"),
                 "original_error": type(exc).__name__}) from exc
        if envelope is None:
            continue  # 合法缺席(不产空引用)
        refs[f"{entry['task_key']}/{entry['name']}"] = \
            str(envelope.get("payload_hash") or "")
    frozen = _read_frozen_plan_or_refuse(ledger)
    if frozen is not None:
        refs[f"{_FROZEN_PLAN_TASK_KEY}/{_FROZEN_PLAN_ARTIFACT}"] = \
            str(frozen.get("payload_hash") or "")
    return dict(sorted(refs.items()))


def _frozen_plan_anchor_exists(ledger) -> bool:
    """冻结计划锚行(S3B-01 同源判定):存在携带 plan_digest 的
    retrieve 行 ⇒ 计划已按 start 流程持久化(frozen_plan artifact
    先于任何 retrieve 执行落盘)⇒ 计划 artifact 应存在。"""
    rows = ledger.conn.execute(
        "SELECT payload FROM search_actions WHERE run_id = ? AND"
        " action_kind = ?", (ledger.run_id, ACTION_KIND_RETRIEVE)
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload"] or "{}")
        except (ValueError, TypeError):
            continue  # 坏锚由 resume/绑定层披露;此处不另加门
        if isinstance(payload, dict) and \
                str(payload.get("plan_digest") or ""):
            return True
    return False


def _necessary_artifact_reference_keys(ledger,
                                       payload: dict | None = None) -> dict:
    """**应有必要** artifact 引用集合(S4-C02;S4 回修 r2,复审 R2
    §4:必要性不由"文件目前存在"决定)。

    依**原生实际消费与已完成 action/task/commit/计划同源闭合**
    (同一 artifact_reference_index 索引,必要性按权威行判定,不另
    造第二套枚举;在读文件之前即从 DB 行 + payload 判定):

    - ``expansion_outcome``(soutc 键):status=done 且 outcome 类
      提交的 retrieve/decide/activate_deferred/scenario_transition
      (调度结论 ``runflow._complete_action`` **先写 artifact 后完成**
      ⇒ 完成即已写,含恢复路径;expand 空 task_key 时
      record_expansion_outcome 回退写同键);
    - ``expansion_outcome``(task_key 键):status=done 且 outcome
      类提交的 expand_hypothesis(record_expansion_outcome 写 action
      行冻结 task_key,先写后完成);
    - ``production_report``:必要性**只由原生实际消费(payload 的
      audit_production_reports 引用)决定** —— 行闭合不判:生产链
      ``production.py _report("submitted")`` 在 complete_action
      **之后**落盘,B4 崩溃恢复(事件已提交、记账未闭合 ⇒ 恢复幂
      等补账)**合法不产报告** ⇒ "done expand 必有 report"不是本
      系统不变量,不以行闭合强加(合法 B4 缺席保持;删已完成任务
      报告的反例由 payload 消费闭合捕获);
    - **原生实际消费**:payload 的 audit_production_reports /
      expansion_outcomes / contexts 声明引用的每个键(与行闭合互
      为冗余 —— 原生声明依赖的项即使行判定不必要,缺文件/漏引用
      也拒);
    - **冻结计划**:存在携带 plan_digest 的 retrieve 锚行(S3B-01
      同源)⇒ frozen_plan 应存在。

    合法缺席保留(不强制存在):未完成(pending/claimed/deferred/
    blocked)action 的全部候选、retrieve/decide 的 production_report
    候选(生产链不写)、事件类提交 expand 的报告候选(B4 恢复补账
    合法不产)、payload 未消费的一切。损坏 artifact 由读取入口按
    H07 结构化拒(原有语义不变)。

    返回 {key: basis}(basis = 判定依据标签,供拒绝对话;本函数
    纯只读 DB/payload,零文件写入,不读 artifact 文件 ⇒ 不存在
    "由文件存在反推必要"的回路)。"""
    conn = ledger.conn
    run_id = ledger.run_id
    actions = {str(r["action_id"]): r for r in conn.execute(
        "SELECT action_id, action_kind, task_key, status FROM"
        " search_actions WHERE run_id = ?", (run_id,)).fetchall()}
    commits = {str(r["action_id"]): str(r["commit_kind"] or "")
               for r in conn.execute(
        "SELECT action_id, commit_kind FROM search_commit_records WHERE"
        " run_id = ?", (run_id,)).fetchall()}
    necessary: dict[str, str] = {}
    for entry in artifact_reference_index(ledger):
        action = actions.get(str(entry.get("source_action_id") or ""))
        if action is None:
            continue  # ctx 条目(无 action 行)不由行闭合判定
        if str(action["status"]) != ACTION_STATUS_DONE:
            continue  # 合法缺席:未完成(含 deferred/blocked)
        commit_kind = commits.get(str(action["action_id"]))
        if commit_kind is None:
            # done 无提交记录 = 记账不变量破坏,由权威层披露;
            # 集合闭合不另加新门(不加新科学门)
            continue
        kind = str(action["action_kind"])
        task_key = str(action["task_key"] or "")
        entry_key = str(entry["task_key"])
        if str(entry["name"]) == _EXPANSION_OUTCOME:
            # 先写后完成的不变量:B4 补账只覆盖事件类提交,outcome 类
            # 完成(record_expansion_outcome / runflow._complete_action)
            # 恒先落盘 artifact ⇒ done+outcome 提交 ⇒ artifact 应存在
            is_soutc = entry_key == stable_id(
                "soutc", str(action["action_id"]))
            if commit_kind == COMMIT_KIND_OUTCOME:
                if is_soutc:
                    if kind != ACTION_KIND_EXPAND_HYPOTHESIS or not task_key:
                        necessary[f"{entry_key}/{_EXPANSION_OUTCOME}"] = \
                            "done_outcome_completion_soutc"
                elif kind == ACTION_KIND_EXPAND_HYPOTHESIS and task_key \
                        and entry_key == task_key:
                    necessary[f"{entry_key}/{_EXPANSION_OUTCOME}"] = \
                        "done_expand_outcome_task_key"
        # production_report 的行闭合分支不存在:B4 恢复合法不产报告
        # (见 docstring);其必要性由下方 payload 实际消费闭合决定
    # ---- 原生实际消费(payload 声明依赖;与行闭合互为冗余) ----
    if payload is not None:
        for report in payload.get("audit_production_reports") or []:
            task_key = str((report or {}).get("task_key") or "")
            if task_key:
                necessary.setdefault(
                    f"{task_key}/{_PRODUCTION_REPORT}",
                    "payload_audit_production_report_consumed")
        for outcome in payload.get("expansion_outcomes") or []:
            task_key = str((outcome or {}).get("task_key") or "")
            if task_key:
                necessary.setdefault(
                    f"{task_key}/{_EXPANSION_OUTCOME}",
                    "payload_expansion_outcome_consumed")
        for context in payload.get("contexts") or []:
            context_ref = str((context or {}).get("context_ref") or "")
            if context_ref:
                necessary.setdefault(
                    f"ctx:{context_ref}/{_CONTEXT_ARTIFACT}",
                    "payload_context_consumed")
    # ---- 冻结计划(锚行同源) ----
    if _frozen_plan_anchor_exists(ledger):
        necessary.setdefault(
            f"{_FROZEN_PLAN_TASK_KEY}/{_FROZEN_PLAN_ARTIFACT}",
            "frozen_plan_anchor_row")
    return dict(sorted(necessary.items()))


def _read_frozen_plan_or_refuse(ledger) -> dict | None:
    """冻结计划 artifact 读取(损坏 ⇒ 结构化拒;缺席 ⇒ None 合法)。"""
    try:
        return read_search_artifact(
            ledger.artifact_store, _FROZEN_PLAN_TASK_KEY,
            _FROZEN_PLAN_ARTIFACT)
    except SearchArtifactIntegrityError as exc:
        raise NativeExportContractError(
            f"导出必要引用的冻结计划 artifact 损坏:"
            f"{_FROZEN_PLAN_TASK_KEY}/{_FROZEN_PLAN_ARTIFACT}"
            "(H07 完整性失败;保全原文件,不能跳过后当合法缺席)",
            {"kind": "export_reference_mismatch",
             "artifact": f"{_FROZEN_PLAN_TASK_KEY}/"
                         f"{_FROZEN_PLAN_ARTIFACT}",
             "artifact_error_kind": exc.detail.get("kind"),
             "original_error": type(exc).__name__}) from exc


# ---------------------------------------------------------------- 事实 digest


def _table_digest(conn, sql: str, params: tuple = ()) -> str:
    """一张(组)事实行的内容 digest(全行、稳定排序;payload 保持
    原始 JSON 字符串形态 —— 与行内容一一对应,不重解释)。"""
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    return content_hash([
        [row.get(k) for k in sorted(row)] for row in rows])


def graph_facts_digests(ledger) -> dict:
    """**graph revision 等价身份**:PPV1 pollutant 存储没有整数
    graph_revision(那是 legacy PathwayStore 的概念);本仓的事实图
    修订身份 = 全部持久事实表的逐表内容 digest(全行,含派生投影表)。
    任何事实行新增/改写 ⇒ 对应 digest 变化 ⇒ 旧导出 stale。"""
    conn = ledger.conn
    run_id = ledger.run_id
    facts = {
        "states": _table_digest(conn, "SELECT * FROM states"),
        "state_appearances": _table_digest(
            conn, "SELECT state_id, appearance_hash, payload, created_at"
            " FROM state_appearances"),
        "hypotheses": _table_digest(conn, "SELECT * FROM hypotheses"),
        "events": _table_digest(conn, "SELECT * FROM events"),
        "report_projections": _table_digest(
            conn, "SELECT * FROM report_projections"),
        "expansion_plans": _table_digest(
            conn, "SELECT * FROM expansion_plans"),
        "event_appearance_links": _table_digest(
            conn, "SELECT * FROM event_appearance_links"),
        "provenance_records": _table_digest(
            conn, "SELECT * FROM provenance_records WHERE run_id = ?",
            (run_id,)),
        "search_actions": _table_digest(
            conn, "SELECT * FROM search_actions WHERE run_id = ?",
            (run_id,)),
        "search_attempts": _table_digest(
            conn, "SELECT * FROM search_attempts WHERE run_id = ?",
            (run_id,)),
        "budget_reservations": _table_digest(
            conn, "SELECT * FROM budget_reservations WHERE run_id = ?",
            (run_id,)),
        "model_requests": _table_digest(
            conn, "SELECT * FROM model_requests WHERE run_id = ?",
            (run_id,)),
        "search_commit_records": _table_digest(
            conn, "SELECT * FROM search_commit_records WHERE run_id = ?",
            (run_id,)),
        "stop_reason_records": _table_digest(
            conn, "SELECT run_id, payload, payload_hash FROM"
            " stop_reason_records WHERE run_id = ?", (run_id,)),
        "endpoint_records": _table_digest(
            conn, "SELECT run_id, payload, payload_hash FROM"
            " endpoint_records WHERE run_id = ?", (run_id,)),
    }
    facts["note"] = (
        "PPV1 graph revision 等价身份 = 持久事实表逐表内容 digest"
        "(legacy 整数 graph_revision 不适用;任何行变化 ⇒ 旧导出 stale)")
    return facts


def _artifact_references(ledger) -> dict:
    """导出消费的全部 artifact 的内容 hash 引用(单一来源:
    native_result.artifact_reference_index + 冻结计划 + 原生结果
    artifact 自身;读取侧逐条重读核对 —— 依赖对象内容变化 ⇒
    reference_mismatch 拒)。"""
    refs: dict[str, dict] = {}
    for entry in artifact_reference_index(ledger):
        try:
            envelope = read_search_artifact(
                ledger.artifact_store, entry["task_key"], entry["name"])
        except SearchArtifactIntegrityError as exc:
            raise NativeExportContractError(
                f"导出引用的 artifact 损坏:{entry['task_key']}/"
                f"{entry['name']}(H07 完整性失败;保全原文件,导出先拒)",
                {"kind": "export_reference_mismatch",
                 "artifact": f"{entry['task_key']}/{entry['name']}",
                 "artifact_error_kind": exc.detail.get("kind"),
                 "original_error": type(exc).__name__}) from exc
        if envelope is None:
            continue
        refs[f"{entry['task_key']}/{entry['name']}"] = {
            "payload_hash": str(envelope.get("payload_hash") or ""),
            "source_action_id": entry["source_action_id"],
        }
    frozen = _read_frozen_plan_or_refuse(ledger)
    if frozen is not None:
        refs[f"{_FROZEN_PLAN_TASK_KEY}/{_FROZEN_PLAN_ARTIFACT}"] = {
            "payload_hash": str(frozen.get("payload_hash") or ""),
            "source_action_id": "",
        }
    return dict(sorted(refs.items()))


def _authority_references(ledger, native_result: dict) -> dict:
    """DB 通道独立权威引用(endpoint/stop 行 hash;原生结果 artifact
    键与内容 digest)。"""
    conn = ledger.conn
    run_id = ledger.run_id
    stop_row = conn.execute(
        "SELECT payload_hash FROM stop_reason_records WHERE run_id = ?",
        (run_id,)).fetchone()
    endpoint_row = conn.execute(
        "SELECT payload_hash FROM endpoint_records WHERE run_id = ?",
        (run_id,)).fetchone()
    return {
        "stop_record_payload_hash":
            str(stop_row["payload_hash"]) if stop_row is not None else "",
        "endpoint_record_payload_hash":
            str(endpoint_row["payload_hash"])
            if endpoint_row is not None else "",
        "native_result_task_key": f"{NATIVE_RESULT_TASK_KEY}:"
                                  f"{str(native_result['content_digest'])[:24]}",
        "native_result_content_digest":
            str(native_result["content_digest"]),
    }


# ---------------------------------------------------------------- 写入


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(
        f"{path.name}.{os.getpid()}.{_atomic_write_seq():d}.tmp")
    tmp.write_bytes(data)
    try:
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


_SEQ = [0]


def _atomic_write_seq() -> int:
    _SEQ[0] += 1
    return _SEQ[0]


def _write_immutable(path: Path, data: bytes) -> bool:
    """不可变写入:目标已存在 ⇒ 字节相同幂等(created=False),不同 ⇒
    NativeExportConflict(保全原文件,绝不覆盖)。"""
    if path.exists():
        if path.read_bytes() == data:
            return False
        raise NativeExportConflict(
            f"导出文件已存在且内容不同(不可变导出;保全原文件不覆盖):"
            f"{path}",
            {"kind": "native_export_conflict", "path": str(path)})
    _atomic_write(path, data)
    return True


def export_native_result(ledger, native_result: dict,
                          run_dir: str | Path) -> dict:
    """原生正式导出落盘(payload + manifest;确定性,幂等)。

    - native_result 必须是 build_native_result 的产物(含
      content_digest;其 endpoint 记录须已通过首消费 —— 本函数再经
      read_run_endpoint 首消费门核验,过期记录不包装成正式结果);
    - 同事实/同版本/同策略 ⇒ 同 export_digest、同目录、同字节;
      事实变化 ⇒ 新 digest 新目录(旧文件保全);
    - 纯只读业务表(零 event/attempt/request/budget 写入)。
    """
    run_dir = Path(run_dir)
    # endpoint 记录首消费门(独立于调用方:过期/损坏记录不包装成正式
    # 结果 —— 与 runflow 派生侧同一判据来源,幂等只读)
    read_run_endpoint(ledger, ledger.run_id)
    # ---- S4-C02 r2:导出侧写入前的必要集合闭合(与读取侧同一判据
    # 来源;先结构化拒、零文件写入、缺席形态保全)----
    # 应有必要项由已完成 action/task/commit + 原生实际消费(native_
    # result payload 声明)+ 冻结计划锚行闭合:必要项缺文件(文件+
    # 引用一起消失,或构建时即缺席)不得封成"完整导出"后靠读取侧
    # 兜底;manifest 引用集合(_artifact_references,现存项)必须
    # 覆盖全部必要项。
    necessary = _necessary_artifact_reference_keys(ledger, native_result)
    missing_necessary: list[str] = []
    for key in necessary:
        task_key, _, name = key.partition("/")
        try:
            envelope = read_search_artifact(
                ledger.artifact_store, task_key, name)
        except SearchArtifactIntegrityError as exc:
            raise NativeExportContractError(
                f"导出必要引用的 artifact 损坏:{key}(H07 完整性失败;"
                "保全原文件,不能跳过后当合法缺席;先拒,零写入)",
                {"kind": "export_reference_mismatch",
                 "artifact": key,
                 "artifact_error_kind": exc.detail.get("kind"),
                 "original_error": type(exc).__name__}) from exc
        if envelope is None:
            missing_necessary.append(key)
    missing_necessary.sort()
    if missing_necessary:
        raise NativeExportContractError(
            f"导出必要 artifact 缺席:{missing_necessary}(依据已完成"
            " action/task/commit + 原生实际消费 + 冻结计划锚闭合;应有"
            "项缺文件不能当合法缺席,不封不完整 manifest;零写入,原"
            "状态保全)",
            {"kind": "export_reference_mismatch",
             "check": "necessary_artifact_reference_set_closure",
             "missing_necessary_files": missing_necessary,
             "necessary_basis": {k: necessary[k]
                                 for k in missing_necessary}})
    refs = _artifact_references(ledger)
    omitted_necessary = sorted(set(necessary) - set(refs))
    if omitted_necessary:
        raise NativeExportContractError(
            f"导出的必要 artifact 引用集合不闭合:{omitted_necessary}"
            "(manifest 引用未覆盖必要项;先拒,零写入)",
            {"kind": "export_reference_mismatch",
             "check": "necessary_artifact_reference_set_closure",
             "omitted_necessary_refs": omitted_necessary,
             "necessary_basis": {k: necessary[k]
                                 for k in omitted_necessary}})
    policy = native_export_policy()
    payload_text = canonical_json(native_result) + "\n"
    payload_sha = hashlib.sha256(
        payload_text.encode("utf-8")).hexdigest()
    # manifest 核心(无 export_digest、无时间戳)
    core = {
        "schema_version": PPV1_NATIVE_EXPORT_VERSION,
        "run_id": ledger.run_id,
        "export_policy": policy,
        "export_policy_sha256": export_policy_hash(policy),
        "contract_versions": _current_contract_versions(),
        "content_digest": str(native_result["content_digest"]),
        "payload_sha256": payload_sha,
        "graph_facts": graph_facts_digests(ledger),
        "artifact_references": refs,
        "authority_references": _authority_references(
            ledger, native_result),
        "determinism_note": (
            "payload/manifest 无时间戳;canonical_json 键序 + 列表稳定"
            "排序;export_digest = content_hash(本 manifest 去掉"
            " export_digest 键);同事实+同版本+同策略 ⇒ 同字节"),
    }
    # ---- P0b/D-6 可选诊断块绑定(contract §3) ----
    # 只在原生结果带 `declared_vs_executed` 时新增 manifest 键;关闭
    # (无块)时 manifest 字节与基线一致。该绑定是可选块的内部完整性
    # 锚,不是新的导出硬门:普通 read_native_export 不因块存在与否
    # 改变结果;显式消费走 read_declared_vs_executed()。
    diagnostic_block = native_result.get("declared_vs_executed")
    if isinstance(diagnostic_block, dict):
        core["diagnostic_bindings"] = {
            "declared_vs_executed": {
                "schema": str(diagnostic_block.get("schema") or ""),
                "version": diagnostic_block.get("version"),
                "rule_version": str(
                    diagnostic_block.get("rule_version") or ""),
                "n_events": diagnostic_block.get("n_events"),
                "digest": content_hash(diagnostic_block),
            }
        }
    export_digest = content_hash(core)
    manifest = dict(core)
    manifest["export_digest"] = export_digest
    manifest_text = canonical_json(manifest) + "\n"
    out_dir = run_dir / NATIVE_EXPORT_SUBDIR / export_digest[:24]
    payload_path = out_dir / NATIVE_EXPORT_PAYLOAD_FILE
    manifest_path = out_dir / NATIVE_EXPORT_MANIFEST_FILE
    out_dir.mkdir(parents=True, exist_ok=True)
    payload_created = _write_immutable(payload_path,
                                       payload_text.encode("utf-8"))
    manifest_created = _write_immutable(manifest_path,
                                        manifest_text.encode("utf-8"))
    return {
        "export_digest": export_digest,
        "dir": str(out_dir),
        "payload_path": str(payload_path),
        "manifest_path": str(manifest_path),
        "payload_sha256": payload_sha,
        "content_digest": str(native_result["content_digest"]),
        "schema_version": PPV1_NATIVE_EXPORT_VERSION,
        "export_policy_version": PPV1_NATIVE_EXPORT_POLICY_VERSION,
        "created": {"payload": payload_created, "manifest": manifest_created},
        "note": ("S4b 正式文件导出:全量事实 + manifest 新鲜度锚"
                 "(graph facts digest/权威引用/策略 hash);确定性幂等,"
                 "旧导出按 digest 保全;读取走 read_native_export 首消费"),
    }


def list_native_exports(run_dir: str | Path) -> list[str]:
    """既有导出 digest 列表(目录名;稳定排序;不含验证)。"""
    root = Path(run_dir) / NATIVE_EXPORT_SUBDIR
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


# ---------------------------------------------------------------- 读取(首消费)


def read_declared_vs_executed(payload: dict,
                              manifest: dict | None = None) -> dict | None:
    """显式消费 P0b/D-6 可选诊断块(不改变普通导出读取语义)。

    - 无块 ⇒ 返回 None(开关关闭的合法形态);
    - 有块 ⇒ 校验自有 schema/version、n_events 与 events 计数闭合;
      若给出 manifest,再核 `diagnostic_bindings.declared_vs_executed`
      的 schema/version/digest 绑定。
    fail-closed 抛 NativeExportContractError;不改任何文件。
    """
    from .production import (
        P0B_D6_DIAGNOSTIC_SCHEMA,
        P0B_D6_DIAGNOSTIC_VERSION,
    )

    block = (payload or {}).get("declared_vs_executed")
    if block is None:
        return None
    if not isinstance(block, dict):
        raise NativeExportContractError(
            "P0b/D-6 诊断块形状非法(非对象;不猜迁移)",
            {"kind": "export_diagnostic_corrupt",
             "check": "declared_vs_executed_shape"})
    if str(block.get("schema") or "") != P0B_D6_DIAGNOSTIC_SCHEMA:
        raise NativeExportContractError(
            f"P0b/D-6 诊断块 schema 未知:{block.get('schema')!r}",
            {"kind": "export_version_unknown",
             "check": "declared_vs_executed_schema"})
    try:
        version = int(block.get("version"))
    except (TypeError, ValueError):
        version = -1
    if version != P0B_D6_DIAGNOSTIC_VERSION:
        raise NativeExportContractError(
            f"P0b/D-6 诊断块版本未知:{block.get('version')!r}",
            {"kind": "export_version_unknown",
             "check": "declared_vs_executed_version"})
    events = block.get("events")
    if not isinstance(events, list) or \
            block.get("n_events") != len(events):
        raise NativeExportContractError(
            "P0b/D-6 诊断块事件计数不闭合(n_events != len(events))",
            {"kind": "export_diagnostic_corrupt",
             "check": "declared_vs_executed_n_events"})
    counts = block.get("counts") or {}
    from .hypothesis import PARTICIPANT_ROLE_UNKNOWN as _UNKNOWN_TOKEN
    if set(counts) != {"consistent", "inconsistent", _UNKNOWN_TOKEN,
                       "not_applicable"}:
        raise NativeExportContractError(
            "P0b/D-6 诊断块四态键不闭合(不洗成通过)",
            {"kind": "export_diagnostic_corrupt",
             "check": "declared_vs_executed_counts_keys",
             "count_keys": sorted(str(k) for k in counts)})
    try:
        total = sum(int(counts.get(k) or 0) for k in (
            "consistent", "inconsistent", _UNKNOWN_TOKEN,
            "not_applicable"))
    except (TypeError, ValueError):
        total = -1
    if total != len(events):
        raise NativeExportContractError(
            "P0b/D-6 诊断块四态计数不闭合(不洗成通过)",
            {"kind": "export_diagnostic_corrupt",
             "check": "declared_vs_executed_counts",
             "counts": counts, "n_events": len(events)})
    if manifest is not None:
        binding = ((manifest.get("diagnostic_bindings") or {})
                   .get("declared_vs_executed"))
        if not isinstance(binding, dict):
            raise NativeExportContractError(
                "导出 manifest 缺 P0b/D-6 诊断块绑定(块在而绑定不在;"
                "不猜默认)",
                {"kind": "export_reference_mismatch",
                 "check": "diagnostic_binding_present"})
        if str(binding.get("digest") or "") != content_hash(block):
            raise NativeExportContractError(
                "P0b/D-6 诊断块内容与 manifest 绑定 digest 不符"
                "(完整性失败;不重算洗白)",
                {"kind": "export_reference_mismatch",
                 "check": "diagnostic_binding_digest"})
        if str(binding.get("schema") or "") != str(block.get("schema")) \
                or binding.get("version") != block.get("version") \
                or str(binding.get("rule_version") or "") != \
                str(block.get("rule_version") or ""):
            raise NativeExportContractError(
                "P0b/D-6 诊断块 schema/version/rule_version 与 manifest "
                "绑定不符",
                {"kind": "export_reference_mismatch",
                 "check": "diagnostic_binding_identity"})
    return block


def read_native_export(ledger, run_dir: str | Path, export_digest: str,
                        *, policy: dict | None = None) -> dict:
    """原生正式导出读取(首消费:integrity → 版本门 → digest → 权威
    引用 → 策略 → staleness;fail-closed,零写入,原文件保全)。

    policy:当前导出策略(缺省 = native_export_policy();测试/未来版本
    可显式传入新策略 ⇒ 旧导出按 export_policy_stale 拒)。
    endpoint 记录的首消费(read_run_endpoint)先行 —— 输入事实漂移时
    先以 endpoint 拒绝浮出,导出侧不再吞掉。
    """
    run_dir = Path(run_dir)
    out_dir = run_dir / NATIVE_EXPORT_SUBDIR / str(export_digest)[:24]
    payload_path = out_dir / NATIVE_EXPORT_PAYLOAD_FILE
    manifest_path = out_dir / NATIVE_EXPORT_MANIFEST_FILE
    if not payload_path.is_file() or not manifest_path.is_file():
        raise NativeExportContractError(
            f"原生导出文件缺失:{out_dir}(不猜默认;按 digest 显式消费)",
            {"kind": "export_missing", "dir": str(out_dir),
             "export_digest": str(export_digest)})
    # ---- 2. manifest 可解析 + digest 绑定 ----
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise NativeExportContractError(
            f"导出 manifest 不可解析:{manifest_path}(保全原文件)",
            {"kind": "export_manifest_corrupt",
             "path": str(manifest_path),
             "error": f"{type(exc).__name__}: {exc}"[:200]}) from exc
    if str(manifest.get("export_digest") or "") != str(export_digest):
        raise NativeExportContractError(
            "导出 manifest 的 export_digest 与请求不符(路径/内容身份"
            "断裂;保全原文件)",
            {"kind": "export_manifest_corrupt",
             "requested": str(export_digest),
             "manifest": str(manifest.get("export_digest") or "")})
    # ---- 2b. manifest core 自身 digest 复算(S4-C02) ----
    # manifest 去掉 export_digest 键后重算 content_hash,与声明值比对:
    # manifest-only 改坏(run_id/契约版本/策略正文/引用集合,保持原
    # digest)不再被字面值比较放过;这不是新增一个自比较字段,而是
    # 对文件内容本身的 core 复算(与导出侧 export_digest 同一构造)。
    core_recomputed = content_hash(
        {k: v for k, v in manifest.items() if k != "export_digest"})
    if core_recomputed != str(manifest.get("export_digest")):
        raise NativeExportContractError(
            "导出 manifest core 自身 digest 复算不一致(manifest 被改"
            "而 export_digest 未同步,或 manifest 组成非法;保全原文件,"
            "不以重算新 digest 洗白)",
            {"kind": "export_manifest_corrupt",
             "check": "manifest_core_digest",
             "declared": str(manifest.get("export_digest"))[:12],
             "recomputed": core_recomputed[:12]})
    # ---- 3. payload 字节完整性 ----
    payload_bytes = payload_path.read_bytes()
    payload_sha = hashlib.sha256(payload_bytes).hexdigest()
    if payload_sha != str(manifest.get("payload_sha256")):
        raise NativeExportContractError(
            f"导出 payload 字节与 manifest sha256 不符(完整性失败;"
            f"保全原文件,不覆盖):{payload_path}",
            {"kind": "export_payload_corrupt",
             "path": str(payload_path),
             "recorded": str(manifest.get("payload_sha256"))[:12],
             "actual": payload_sha[:12]})
    # ---- 4. 版本门(schema + 契约版本块整组绑定,S4-C02) ----
    if str(manifest.get("schema_version") or "") != PPV1_NATIVE_EXPORT_VERSION:
        raise NativeExportContractError(
            f"导出 schema 版本未知:{manifest.get('schema_version')!r}"
            f"(当前 {PPV1_NATIVE_EXPORT_VERSION};fail-closed 不猜迁移)",
            {"kind": "export_version_unknown",
             "schema_version": str(manifest.get("schema_version") or "")})
    current_contracts = _current_contract_versions()
    recorded_contracts = manifest.get("contract_versions") or {}
    contract_drift = sorted(
        key for key, value in current_contracts.items()
        if str(recorded_contracts.get(key)) != str(value))
    if contract_drift:
        raise NativeExportContractError(
            f"导出契约版本块与当前登记源不符:{contract_drift}"
            "(run/版本/策略内容与当前权威绑定,不是 manifest 内自洽"
            "证书;旧导出不得当当前结果)",
            {"kind": "export_version_unknown",
             "changed_contracts": contract_drift,
             "recorded": {k: recorded_contracts.get(k)
                          for k in contract_drift},
             "current": {k: current_contracts[k] for k in contract_drift}})
    # ---- 4b. run 绑定(S4-C02) ----
    if str(manifest.get("run_id") or "") != str(ledger.run_id):
        raise NativeExportContractError(
            "导出 manifest 的 run_id 与当前 run 权威不符(run 绑定;"
            "自洽重封换 run 身份不再照收)",
            {"kind": "export_reference_mismatch",
             "check": "run_binding",
             "manifest_run_id": str(manifest.get("run_id") or ""),
             "ledger_run_id": str(ledger.run_id)})
    # ---- 5. payload 内容 digest 复算 ----
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise NativeExportContractError(
            f"导出 payload 不可反序列化:{payload_path}(保全原文件)",
            {"kind": "export_payload_corrupt",
             "path": str(payload_path),
             "error": f"{type(exc).__name__}: {exc}"[:200]}) from exc
    if content_hash({k: v for k, v in payload.items()
                     if k != "content_digest"}) \
            != str(payload.get("content_digest")):
        raise NativeExportContractError(
            f"导出 payload 内容 digest 复算不一致:{payload_path}"
            "(自洽性失败;保全原文件,不以重算新 ID 洗白)",
            {"kind": "export_digest_mismatch",
             "path": str(payload_path)})
    if str(payload.get("content_digest")) != \
            str(manifest.get("content_digest")):
        raise NativeExportContractError(
            "导出 payload 与 manifest 的 content_digest 不一致"
            "(内部引用断裂;保全原文件)",
            {"kind": "export_digest_mismatch",
             "payload": str(payload.get("content_digest")),
             "manifest": str(manifest.get("content_digest"))})
    # ---- 5b. payload 原生结果版本门(S4-C04 r2,复审 R2 §4) ----
    # 与 manifest schema/契约版本块同一登记源(profile 常量);自洽
    # 重封(重算 content_digest/payload_sha256/manifest digest)换
    # native_result_version 不再只靠权威 artifact 绑定兜底 —— 未知/
    # 缺失来源版本不包装成已验证结果(fail-closed 不猜迁移,历史
    # 版本无显式 adapter ⇒ 拒)。
    if str(payload.get("native_result_version") or "") \
            != PPV1_NATIVE_RESULT_VERSION:
        raise NativeExportContractError(
            f"导出 payload 的原生结果版本未知/缺失:"
            f"{payload.get('native_result_version')!r}(当前 "
            f"{PPV1_NATIVE_RESULT_VERSION};fail-closed 不猜迁移;"
            "保全原文件,未知来源版本不包装成已验证结果)",
            {"kind": "export_version_unknown",
             "check": "payload_native_result_version_binding",
             "native_result_version":
                 str(payload.get("native_result_version") or "")})
    # ---- 6. 权威引用(endpoint 首消费先行 + DB 行 + artifacts) ----
    read_run_endpoint(ledger, ledger.run_id)
    refs = manifest.get("authority_references") or {}
    conn = ledger.conn
    stop_row = conn.execute(
        "SELECT payload_hash FROM stop_reason_records WHERE run_id = ?",
        (ledger.run_id,)).fetchone()
    endpoint_row = conn.execute(
        "SELECT payload_hash FROM endpoint_records WHERE run_id = ?",
        (ledger.run_id,)).fetchone()
    if (stop_row is None
            or str(stop_row["payload_hash"])
            != str(refs.get("stop_record_payload_hash"))
            or endpoint_row is None
            or str(endpoint_row["payload_hash"])
            != str(refs.get("endpoint_record_payload_hash"))):
        raise NativeExportContractError(
            "导出与 DB 权威记录(endpoint/stop 行)引用不一致"
            "(四分账独立持久化;断裂 ⇒ 结构化拒,不猜补)",
            {"kind": "export_reference_mismatch",
             "stop_record_payload_hash":
                 str(refs.get("stop_record_payload_hash")),
             "endpoint_record_payload_hash":
                 str(refs.get("endpoint_record_payload_hash"))})
    native_task_key = str(refs.get("native_result_task_key"))
    try:
        native_back = read_native_result(
            ledger.artifact_store, native_task_key)
    except Exception as exc:  # noqa: BLE001 —— 引用失败如实上抛(拒)
        raise NativeExportContractError(
            f"导出引用的原生结果 artifact 不可用:{native_task_key}"
            "(引用断裂/损坏 ⇒ 拒;保全原文件)",
            {"kind": "export_reference_mismatch",
             "native_result_task_key": native_task_key,
             "error": f"{type(exc).__name__}: {exc}"[:200]}) from exc
    if str(native_back.get("content_digest")) != \
            str(manifest.get("content_digest")):
        raise NativeExportContractError(
            "导出 manifest 与原生结果 artifact 的 content_digest 不一致"
            "(权威源分叉;拒)",
            {"kind": "export_reference_mismatch",
             "manifest": str(manifest.get("content_digest")),
             "artifact": str(native_back.get("content_digest"))})
    artifact_refs = manifest.get("artifact_references") or {}
    for key, recorded in sorted(artifact_refs.items()):
        task_key, _, name = key.partition("/")
        try:
            envelope = read_search_artifact(
                ledger.artifact_store, task_key, name)
        except SearchArtifactIntegrityError as exc:
            raise NativeExportContractError(
                f"导出引用的 artifact 损坏:{key}(H07 完整性失败;"
                "保全原文件,不静默略过)",
                {"kind": "export_reference_mismatch",
                 "artifact": key,
                 "artifact_error_kind": exc.detail.get("kind"),
                 "original_error": type(exc).__name__}) from exc
        if envelope is None or str(envelope.get("payload_hash") or "") \
                != str((recorded or {}).get("payload_hash")):
            raise NativeExportContractError(
                f"导出引用的 artifact 内容变化或缺失:{key}"
                "(依赖对象内容变化 ⇒ 旧导出拒;保全原文件)",
                {"kind": "export_reference_mismatch",
                 "artifact": key,
                 "recorded_payload_hash":
                     str((recorded or {}).get("payload_hash"))[:12],
                 "current_payload_hash": (
                     str(envelope.get("payload_hash") or "")[:12]
                     if envelope is not None else "<missing>")})
    # ---- 7. 导出策略(正文与 hash 双绑定,S4-C02) ----
    current_policy = policy if policy is not None else native_export_policy()
    recorded_policy_body = manifest.get("export_policy")
    if not isinstance(recorded_policy_body, dict) \
            or recorded_policy_body != current_policy:
        raise NativeExportContractError(
            "导出过期:导出策略/版本变化(旧导出不得当作当前结果;"
            "重新导出走公共 start/resume 或 export_native_result)",
            {"kind": "export_policy_stale",
             "check": "policy_body_binding",
             "recorded": recorded_policy_body,
             "current": current_policy})
    recorded_policy_sha = str(manifest.get("export_policy_sha256") or "")
    if recorded_policy_sha != export_policy_hash(current_policy) \
            or recorded_policy_sha != export_policy_hash(
                recorded_policy_body):
        raise NativeExportContractError(
            "导出策略 hash 与正文绑定失败(策略正文与自记 sha256 不符;"
            "保全原文件,不以重算 hash 洗白)",
            {"kind": "export_policy_stale",
             "check": "policy_body_hash_binding",
             "recorded": recorded_policy_sha[:12],
             "current": export_policy_hash(current_policy)[:12],
             "body_recomputed": export_policy_hash(
                 recorded_policy_body)[:12]})
    # ---- 8. graph facts staleness(独立权威重算,不信 manifest) ----
    current_facts = graph_facts_digests(ledger)
    recorded_facts = manifest.get("graph_facts") or {}
    changed = sorted(
        key for key, value in current_facts.items()
        if key != "note"
        and str(recorded_facts.get(key)) != str(value))
    if changed:
        raise NativeExportContractError(
            f"导出已过期:源图事实与当前持久权威不一致:{changed}"
            "(旧导出不能静默当作当前结果 —— 拒绝消费;重新导出走公共"
            " start/resume 或 export_native_result)",
            {"kind": "export_stale", "changed_facts": changed,
             "recorded": {k: recorded_facts.get(k) for k in changed},
             "current": {k: current_facts[k] for k in changed}})
    # ---- 9. 必要 artifact 引用集合闭合(S4-C02;S4 回修 r2,复审
    # R2 §4;与每行 hash 校验分别核;放在 stale 之后 —— 事实漂移先以
    # export_stale 浮出,纯引用集合篡改(事实不动)由本步拒) ----
    # 应有必要项由已完成 action/task/commit + 原生实际消费(payload
    # 声明)+ 冻结计划锚行同源闭合(在读文件之前从 DB/payload 判定,
    # 不由文件存在决定):文件+引用一起消失的自洽重封(删已完成任务
    # 的 production_report 等)在此拒 —— 必要项缺文件不是合法缺席。
    # 现存集合(合法缺席语义)与必要集合分别核:漏必要引用、漏现存
    # 引用、悬垂(引用不存在的项)分别披露。
    necessary = _necessary_artifact_reference_keys(ledger, payload)
    existing = _existing_artifact_reference_keys(ledger)
    recorded_ref_keys = set(artifact_refs)
    omitted_necessary = sorted(set(necessary) - recorded_ref_keys)
    omitted_existing = sorted(
        set(existing) - recorded_ref_keys - set(necessary))
    dangling = sorted(recorded_ref_keys - set(existing))
    if omitted_necessary or omitted_existing or dangling:
        raise NativeExportContractError(
            "导出的必要 artifact 引用集合不闭合(应有必要项由已完成"
            " action/task/commit + 原生实际消费 + 冻结计划锚同源闭合,"
            "不由文件存在决定;漏必要/漏现存引用与悬垂引用分别披露;"
            "与每行 hash 校验分别核)",
            {"kind": "export_reference_mismatch",
             "check": "necessary_artifact_reference_set_closure",
             "omitted_necessary_refs": omitted_necessary,
             "necessary_basis": {k: necessary[k]
                                 for k in omitted_necessary},
             "omitted_existing_refs": omitted_existing,
             "dangling_recorded_refs": dangling})
    return {"manifest": manifest, "payload": payload,
            "payload_sha256": payload_sha}
