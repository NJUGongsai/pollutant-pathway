"""S4a 原生结果对象 —— 完整字段与确定性规范化(原生结果底座;
契约 ppv1-native-result-1 登记;正式文件导出/G02 manifest/S4b)。

S4a 范围(任务书 §7 S4a 第 7 项):**对象**与确定性规范化 ——
从持久权威(store 行 + H07 校验 artifact)聚合全部路径事实与
不确定性,canonical_json 规范化(键排序 + 列表稳定排序),content
digest 全量哈希;相同事实 ⇒ 相同 digest(确定性底座,重复生成
等价)。S4b 再交付:正式文件导出/manifest/读取消费/过期识别与
v3 有损适配 —— 本模块不实现文件消费契约。

字段组(任务书 §2.B 全量清单;S4a 聚合其中可从持久权威同源取得的
全部组):

- ChemicalState:states + state_appearances(不同来路 source_refs/
  structure_origin 各自保留,不按 CN 合并);
- 路径身份:root/sub 路径(child_path_id = 父 + 事件 + 产物引用,
  同 queue.child_path_id 单一来源);
- 全部反应假设与事件(参与物/系数/角色完整;报告投影与展开计划
  分列 —— 仅报告状态与已展开状态分开);
- 备选反应关系(同 parent 的多 expand action;deferred 集合两类
  分别列示);
- 共同产物(事件内 role=coproduct 参与物);
- 条件与依赖(上下文 artifact:H07 + 内容身份首消费后入对象);
- source/provenance:provenance_records 行 + 出现 source_refs;
- audit 结果与 proof scope:每个 expand action 的 production_report
  artifact(H07 校验读取;含 audit/admission/执行诊断);
- 失败/unknown/partial/violated 原因:expansion_outcome artifact
  (unresolved_continuation/method_failed/contract_aborted 等)+ attempt
  状态;
- 预算预约与实际消耗:budget_reservations 聚合 + budget_snapshot
  (同 search 层派生,不复制判据);
- 搜索停止原因:stop_reason_records 行(独立持久化;经 hash 复算);
- endpoint 分账:endpoint_records 行(经首消费校验:版本/hash/
  stale —— 过期记录不包装成"正式结果")。

确定性:全部列表按稳定键排序(行 id / content hash / 声明次序
固定的字段保持原序);canonical_json 键序固定;digest =
content_hash(规范化载荷)。两个独立进程对同一事实库构建 ⇒
相同 digest(S4a 测试断言;文件级字节导出为 S4b)。

边界:本对象不是 v3 报告;不做 CN 合并;不把 deferred/unknown/
partial 改写为成功;网络与真实 provider 不经本对象;不修改任何
既有行(纯只读聚合 + 派生 artifact 落盘)。
"""

from __future__ import annotations

import json

from ..domain.models import content_hash
from .profile import PPV1_NATIVE_RESULT_VERSION
from .search import read_search_artifact

NATIVE_RESULT_TASK_KEY = "run-native-result"
NATIVE_RESULT_ARTIFACT = "native_result"

_PRODUCTION_REPORT = "production_report"
_EXPANSION_OUTCOME = "expansion_outcome"
_CONTEXT_ARTIFACT = "path_context"


class NativeResultContractError(RuntimeError):
    """原生结果对象构建契约违反(结构化;零写入)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _rows_sorted(rows: list, key_fields: tuple) -> list[dict]:
    out = []
    for row in rows:
        item = {k: row[k] for k in row.keys()}
        for k in list(item):
            if isinstance(item[k], str) and item[k].startswith(("{", "[")):
                try:
                    item[k] = json.loads(item[k])
                except (ValueError, TypeError):
                    pass
        out.append(item)
    return sorted(out, key=lambda d: tuple(
        str(d.get(f) or "") for f in key_fields))


def build_native_result(ledger, *, endpoint_record: dict) -> dict:
    """从持久权威聚合原生结果对象(确定性;S4a 对象底座)。

    endpoint_record 必须是已通过首消费校验的记录(调用方经
    read_run_endpoint/consume_run_endpoint 取得;过期记录不得包装
    成正式结果)。构建纯只读;落盘为派生 artifact(键含 digest,
    不可变,重复生成同内容幂等)。
    """
    store = ledger.store
    conn = ledger.conn
    run_id = ledger.run_id

    # ---- 状态与出现(不同来路保留) ----
    states = _rows_sorted(
        conn.execute("SELECT * FROM states").fetchall(), ("state_id",))
    appearances = _rows_sorted(
        conn.execute(
            "SELECT state_id, appearance_hash, payload, created_at FROM"
            " state_appearances ORDER BY state_id, appearance_hash"
        ).fetchall(), ("state_id", "appearance_hash"))

    # ---- 假设/事件/投影/计划(完整事实;报告与展开分列) ----
    hypotheses = _rows_sorted(
        conn.execute("SELECT * FROM hypotheses").fetchall(),
        ("hypothesis_id",))
    events = _rows_sorted(
        conn.execute("SELECT * FROM events").fetchall(), ("event_id",))
    event_ids = [str(e["event_id"]) for e in events]
    projections = _rows_sorted(
        conn.execute(
            "SELECT * FROM report_projections ORDER BY event_id"
        ).fetchall(), ("event_id",))
    plans = _rows_sorted(
        conn.execute(
            "SELECT * FROM expansion_plans ORDER BY event_id"
        ).fetchall(), ("event_id",))

    # ---- 搜索动作/尝试/预约/请求/提交记录(调度事实) ----
    actions = _rows_sorted(
        conn.execute(
            "SELECT action_id, run_id, parent_path_id, context_ref,"
            " subject_ref, action_kind, parent_search_revision,"
            " policy_version, status, payload, task_key, outcome_ref,"
            " budget_reservation_ref, attempt_refs, defer_reason,"
            " created_at, claimed_at, claimed_by, updated_at FROM"
            " search_actions WHERE run_id = ? ORDER BY action_id",
            (run_id,)).fetchall(), ("action_id",))
    attempts = _rows_sorted(
        conn.execute(
            "SELECT * FROM search_attempts WHERE run_id = ?"
            " ORDER BY expansion_attempt_id", (run_id,)).fetchall(),
        ("expansion_attempt_id",))
    reservations = conn.execute(
        "SELECT limit_key, scope, status, COUNT(*) AS n, SUM(units) AS"
        " units FROM budget_reservations WHERE run_id = ? GROUP BY"
        " limit_key, scope, status ORDER BY limit_key, scope, status",
        (run_id,)).fetchall()
    budget_summary = {
        "reservation_groups": [
            {"limit_key": str(r["limit_key"]), "scope": str(r["scope"]),
             "status": str(r["status"]), "rows": int(r["n"]),
             "units": int(r["units"] or 0)} for r in reservations],
        "budget_snapshot": ledger.budget_snapshot(run_id),
    }
    requests = _rows_sorted(
        conn.execute(
            "SELECT request_id, run_id, action_id, attempt_id,"
            " provider_kind, purpose, status, network_request_count,"
            " retry_of, created_at FROM model_requests WHERE run_id = ?"
            " ORDER BY request_id", (run_id,)).fetchall(),
        ("request_id",))
    commits = _rows_sorted(
        conn.execute(
            "SELECT * FROM search_commit_records WHERE run_id = ?"
            " ORDER BY commit_id", (run_id,)).fetchall(), ("commit_id",))

    # ---- 路径身份(root + followup 子路径;同 queue 单一来源派生) ----
    from .queue import child_path_id as _child_path_id
    paths: list[dict] = []
    for action in actions:
        payload = action.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        if str(action.get("action_kind")) == "retrieve":
            source_event = str(payload.get("source_event_id") or "")
            product_ref = str(payload.get("product_state_ref") or "")
            parent = str(action.get("parent_path_id") or "")
            if source_event and product_ref:
                paths.append({
                    "path_id": _child_path_id(parent, source_event,
                                              product_ref),
                    "parent_path_id": parent,
                    "source_event_id": source_event,
                    "product_state_ref": product_ref,
                    "context_ref": str(action.get("context_ref") or ""),
                    "origin": "coproduct_followup",
                })
    root_rows = [a for a in actions
                 if str(a.get("action_kind")) == "retrieve"
                 and not (isinstance(a.get("payload"), dict)
                          and a["payload"].get("source_event_id"))]
    for root_row in root_rows:
        paths.append({
            "path_id": str(root_row.get("parent_path_id") or ""),
            "parent_path_id": "",
            "source_event_id": "",
            "product_state_ref": str(root_row.get("subject_ref") or ""),
            "context_ref": str(root_row.get("context_ref") or ""),
            "origin": "root",
        })
    paths = sorted(paths, key=lambda p: (
        p["path_id"], p["source_event_id"], p["product_state_ref"]))

    # ---- 上下文(条件/依赖;H07 + 内容身份首消费) ----
    context_refs = sorted({
        str(a.get("context_ref") or "") for a in actions
        if str(a.get("context_ref") or "")})
    contexts = []
    for ref in context_refs:
        envelope = read_search_artifact(
            ledger.artifact_store, f"ctx:{ref}", _CONTEXT_ARTIFACT)
        if envelope is not None:
            contexts.append({"context_ref": ref,
                             "payload": envelope.get("payload")})

    # ---- audit 结果/proof scope/失败原因(per-action artifact) ----
    audit_reports: list[dict] = []
    outcome_records: list[dict] = []
    for action in actions:
        task_key = str(action.get("task_key") or "")
        if not task_key:
            continue
        kind = str(action.get("action_kind"))
        if kind in ("expand_hypothesis", "retrieve", "decide"):
            report = read_search_artifact(
                ledger.artifact_store, task_key, _PRODUCTION_REPORT)
            if report is not None:
                payload = dict(report.get("payload") or {})
                audit_reports.append({
                    "action_id": str(action.get("action_id")),
                    "task_key": task_key,
                    "production_payload": payload,
                })
        if kind in ("expand_hypothesis", "retrieve", "decide",
                    "activate_deferred", "scenario_transition"):
            outcome = read_search_artifact(
                ledger.artifact_store, task_key, _EXPANSION_OUTCOME)
            if outcome is not None:
                payload = dict(outcome.get("payload") or {})
                outcome_records.append({
                    "action_id": str(action.get("action_id")),
                    "task_key": task_key,
                    "outcome_payload": payload,
                })

    # ---- 备选反应关系(同 parent 多 expand action)+ 共同产物 ----
    alternatives: list[dict] = []
    expand_by_parent: dict[str, list] = {}
    for action in actions:
        if str(action.get("action_kind")) == "expand_hypothesis":
            expand_by_parent.setdefault(
                str(action.get("parent_path_id") or ""),
                []).append(action)
    for parent, items in sorted(expand_by_parent.items()):
        alternatives.append({
            "parent_path_id": parent,
            "alternative_hypotheses": sorted(
                str(a.get("subject_ref") or "") for a in items),
            "statuses": sorted(
                str(a.get("status") or "") for a in items),
            "note": ("同父备选反应各自独立(不合并为单反应;A01);"
                     "不同来路/parent/context 不按 CN 全局合并"),
        })
    coproducts: list[dict] = []
    for event in events:
        payload = event.get("payload")
        participants = (json.loads(payload).get("participants")
                        if isinstance(payload, str) and payload
                        else (payload or {}).get("participants")) or []
        coproduct_refs = [
            str(p.get("state_ref")) for p in participants
            if isinstance(p, dict) and p.get("role") == "coproduct"]
        if coproduct_refs:
            coproducts.append({
                "event_id": str(event["event_id"]),
                "coproduct_state_refs": sorted(coproduct_refs),
                "note": "完整事件保留共同产物(不被报告 K/展开宽度截断)",
            })

    # ---- deferred 两类(分别列示;未展开集合) ----
    deferred_entries: list[dict] = []
    for action in actions:
        if str(action.get("status")) != "deferred":
            continue
        payload = action.get("payload")
        payload = (json.loads(payload) if isinstance(payload, str)
                   else payload) or {}
        deferred_entries.append({
            "action_id": str(action.get("action_id")),
            "deferred_type": str(payload.get("deferred_type") or ""),
            "object": str(action.get("subject_ref") or ""),
            "reason": str(action.get("defer_reason") or ""),
            "parent_path_id": str(action.get("parent_path_id") or ""),
        })
    deferred_entries.sort(key=lambda d: d["action_id"])
    blocked_entries = [
        {"action_id": str(a.get("action_id")),
         "object": str(a.get("subject_ref") or ""),
         "reason": str(a.get("defer_reason") or "")}
        for a in actions if str(a.get("status")) == "blocked"]
    blocked_entries.sort(key=lambda d: d["action_id"])

    # ---- provenance ----
    provenance = _rows_sorted(
        conn.execute(
            "SELECT * FROM provenance_records WHERE run_id = ?"
            " ORDER BY record_id", (run_id,)).fetchall(), ("record_id",))

    payload = {
        "native_result_version": PPV1_NATIVE_RESULT_VERSION,
        "run_id": run_id,
        "generated_at_basis": {
            "source": "persistent store rows + H07-verified artifacts",
            "note": ("生成依据:store SQLite 行 + artifact store(H07 "
                     "完整性包装)读取;确定性规范化 = canonical_json "
                     "键序 + 列表稳定排序;载荷不含构建时间戳(同事实"
                     "⇒ 同 digest;artifact 信封 created_at 记录落盘"
                     "时刻);正式文件导出/manifest/读取消费契约属 "
                     "S4b"),
        },
        "states": states,
        "state_appearances": appearances,
        "paths": paths,
        "hypotheses": hypotheses,
        "events": events,
        "report_projections": projections,
        "expansion_plans": plans,
        "alternatives": alternatives,
        "coproducts": coproducts,
        "contexts": contexts,
        "provenance_records": provenance,
        "audit_production_reports": audit_reports,
        "expansion_outcomes": outcome_records,
        "deferred_entries": deferred_entries,
        "blocked_entries": blocked_entries,
        "search_actions": actions,
        "search_attempts": attempts,
        "search_commit_records": commits,
        "model_requests": requests,
        "budget": budget_summary,
        "endpoint_record": endpoint_record,
        "event_ids": event_ids,
    }
    digest = content_hash(payload)
    payload["content_digest"] = digest
    return payload


def persist_native_result(ledger, native_result: dict) -> dict:
    """原生结果对象落盘(派生 artifact;键含 digest ⇒ 不可变幂等,
    事实变化 = 新键新记录,历史保留;不覆盖任何既有 artifact)。"""
    if ledger.artifact_store is None:
        raise NativeResultContractError(
            "持久化原生结果需要 artifact_store",
            {"kind": "artifact_store_missing"})
    digest = str(native_result["content_digest"])
    task_key = f"{NATIVE_RESULT_TASK_KEY}:{digest[:24]}"
    ledger.artifact_store.write(
        task_key, NATIVE_RESULT_ARTIFACT, native_result)
    return {"task_key": task_key, "content_digest": digest}


def read_native_result(artifact_store, task_key: str) -> dict:
    """读取已落盘的原生结果对象(H07 完整性包装;正式消费契约与
    过期识别属 S4b —— 此处只保证读到的载荷与写入口径一致)。"""
    envelope = read_search_artifact(
        artifact_store, task_key, NATIVE_RESULT_ARTIFACT)
    if envelope is None:
        raise NativeResultContractError(
            f"原生结果 artifact 缺失:{task_key}(不猜默认)",
            {"kind": "native_result_missing", "task_key": task_key})
    payload = dict(envelope.get("payload") or {})
    if content_hash({
            k: v for k, v in payload.items()
            if k != "content_digest"}) != str(payload.get("content_digest")):
        raise NativeResultContractError(
            f"原生结果内容摘要复算不一致:{task_key}(完整性失败)",
            {"kind": "native_result_digest_mismatch",
             "task_key": task_key})
    return payload
