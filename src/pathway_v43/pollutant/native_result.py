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
  (unresolved_continuation/method_failed/contract_aborted 等)+
  attempt 状态(S4b 修正:非事件动作完成的调度结论 artifact
  —— record_expansion_outcome 的 action.task_key 键与 _complete_
  action 的 soutc 键**都**聚合;S4a 只查前者,retrieve/decide 等
  调度结论漏聚;**S4-C03 回修(确认复核 §4)**:soutc 键按
  action_id 独立枚举,空 action.task_key 不再挡住 child retrieve
  等的 no_local_candidate/unresolved_continuation 结论聚合与
  manifest 引用;坏必要 artifact 结构化拒,不静默略过;契约
  ppv1-native-result-2);
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

from ..domain.models import content_hash, stable_id
from .chemstate import ChemicalState, ChemicalStateError
from .hypothesis import (
    PARTICIPANT_ROLE_UNKNOWN as _UNKNOWN_TOKEN,
    PARTICIPANT_SIDE_PRODUCT as _PRODUCT_SIDE,
)
from .profile import PPV1_NATIVE_RESULT_VERSION
from .search import (
    ATTEMPT_STATUS_RECORDED as _RECORDED_TOKEN,
    SearchArtifactIntegrityError,
    read_search_artifact,
)

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


def _validate_native_state_rows(states: list[dict],
                                appearances: list[dict]) -> None:
    """原生构建的状态身份闭合(官方链对持久 states 权威的**首次消费**;
    criteria-v2 P1 回修,2026-10-14;P1fix2 同日扩为完整出现集合核验)。

    **完整 appearance 集合核验(P1fix2)**:对进入聚合载荷的全部
    state_appearances 行(不区分其 state 是否还有其他合法出现)逐行核
    三件事 —— ①**对象形状**:非 dict 载荷 ⇒ 结构化拒绝(不静默跳过;
    不再允许"同 state 还有一条合法 dict"掩护坏权威记录继续进入
    native_result 与导出);②**appearance_hash 内容绑定**:经 store
    `_verify_appearance_content_hash` 单一验证源(与写入收集阶段/
    重放同一判据,不另立标准、不重算新哈希洗损坏);③**state_id
    绑定**:出现载荷内 state_id 与行键/语义块一致(store.
    _split_state_payload 写入侧把 state_id 放进 appearance 的身份
    绑定,首消费闭环核验)。任一失败 ⇒ NativeResultContractError
    结构化拒绝、链在构建处截断(persist/export/reader/evaluator 不
    执行),底层损坏信息(kind/detail)原样保全可追溯。

    **(语义, 出现) 逐对事实重算**(P1 原闭合,保持):states 行载荷是
    语义块、state_appearances 行载荷是出现块(store._split_state_
    payload 拆分的两侧),按 store 同源出现字段清单反向拼回完整
    state dict,逐 (语义, 出现) 对过 ChemicalState.from_dict
    (**单一验证源**:与恢复入口/audit 直接 states 消费/公共 writer
    store._verify_state_payload_facts 同源,不另立判据)重推
    state_id/formal_charge/cn_identity/立体/同位素事实与 raw→strict
    身份。任一对不一致(SQLite 载荷单点腐蚀绕过 writer 的情形在内)
    ⇒ 结构化拒绝,不静默略过、不清洗后继续 —— 已损坏权威 state 不得
    被官方链重新包装为当前载荷。

    - 零出现记录的 state 同拒(store 无合法路径只写语义块不写出现;
      无法验证身份即不授信,fail-closed 不猜);
    - CN-only 态走 validate_state_object 专用未知事实契约(不重推导
      结构);
    - 合法数据零行为差:put_state 写前已用同源验证核过每个
      (语义, 出现) 对;本验证纯只读,不修改聚合载荷(native_result
      digest 不变)。
    """
    from .store import (_STATE_APPEARANCE_FIELDS,  # 拆分字段同源;延迟防环
                        Ppv1LedgerCorrupt,
                        _verify_appearance_content_hash)
    by_state: dict[str, list[dict]] = {}
    for app_row in appearances:
        sid_row = str(app_row.get("state_id"))
        app_hash = str(app_row.get("appearance_hash") or "")
        app_payload = app_row.get("payload")
        if not isinstance(app_payload, dict):
            # ① 对象形状:非 dict 载荷 = 损坏权威出现记录,结构化拒绝
            # (不静默跳过)。底层内容⇄哈希绑定事实经同一验证源核出后
            # 原样附入 detail(与重放侧同结论,可追溯)。
            try:
                _verify_appearance_content_hash(sid_row, app_hash,
                                                app_payload)
                hash_ok = True
            except Ppv1LedgerCorrupt:
                hash_ok = False
            raise NativeResultContractError(
                f"原生结果聚合的出现记录载荷损坏:{sid_row}(载荷非对象;"
                "完整出现集合首次消费核验 —— 不静默跳过、不清洗后继续,"
                "已损坏权威出现记录不得被重新包装为正式结果)",
                {"kind": "native_result_appearance_corrupt",
                 "state_id": sid_row,
                 "reason": "payload_not_object",
                 "payload_kind": type(app_payload).__name__,
                 "appearance_hash": app_hash,
                 "appearance_hash_matches": hash_ok})
        # ② appearance_hash 内容绑定(写入/重放/首消费共用单一验证源)
        try:
            _verify_appearance_content_hash(sid_row, app_hash, app_payload)
        except Ppv1LedgerCorrupt as exc:
            raise NativeResultContractError(
                f"原生结果聚合的出现记录内容与哈希不一致:{sid_row}"
                "(官方链首次消费与 store 写入/重放共用同一哈希判据;"
                "底层 kind/detail 原样保全)",
                {"kind": "native_result_appearance_corrupt",
                 "state_id": sid_row,
                 "reason": "appearance_hash_mismatch",
                 "appearance_error_kind": exc.detail.get("kind"),
                 "appearance_error_detail": exc.detail}) from exc
        # ③ state_id 绑定:出现载荷身份与行键/语义块一致
        # (_split_state_payload 写入侧不变式;哈希被重签时由此拦截)
        if app_payload.get("state_id") != sid_row:
            raise NativeResultContractError(
                f"原生结果聚合的出现记录 state_id 绑定不一致:{sid_row}"
                "(出现载荷的 state_id 与行键/语义块必须一致;损坏权威"
                "出现记录不得被重新包装为正式结果)",
                {"kind": "native_result_appearance_corrupt",
                 "state_id": sid_row,
                 "reason": "state_id_binding_mismatch",
                 "payload_state_id": app_payload.get("state_id")})
        by_state.setdefault(sid_row, []).append(app_payload)
    for row in states:
        sid = str(row.get("state_id"))
        semantic = row.get("payload")
        apps = by_state.get(sid) or []
        if not isinstance(semantic, dict) or not apps:
            raise NativeResultContractError(
                f"原生结果聚合的状态载荷不可验证:{sid}(语义块非对象"
                "或零出现记录;store 无合法路径只写语义不写出现 —— "
                "fail-closed 拒绝,不猜不清洗)",
                {"kind": "native_result_state_unverifiable",
                 "state_id": sid,
                 "semantic_is_object": isinstance(semantic, dict),
                 "appearance_count": len(apps)})
        for app in apps:
            joined = dict(semantic)
            for k in _STATE_APPEARANCE_FIELDS:
                if k in app:
                    joined[k] = app[k]
            try:
                ChemicalState.from_dict(joined)
            except ChemicalStateError as exc:
                raise NativeResultContractError(
                    f"原生结果聚合的状态身份/事实重算不一致:{sid}"
                    "(官方链首次消费共源闭合;已损坏权威 state 不得被"
                    "重新包装为正式结果;底层 kind/detail 原样保全)",
                    {"kind": "native_result_state_corrupt",
                     "state_id": sid,
                     "state_error_kind": exc.detail.get("kind"),
                     "state_error_detail": exc.detail}) from exc


def artifact_reference_index(ledger) -> list[dict]:
    """原生结果消费的 artifact 引用索引(**单一来源**:build_native_
    result 的读取循环与 native_export 的 manifest 引用集合/首消费
    必要集合闭合共用本函数,不各自实现第二套枚举规则)。

    条目 = {task_key, name, source_action_id}(稳定排序:task_key);
    覆盖 build_native_result 实际消费的全部 artifact:
    - path_context(上下文:条件/依赖;task_key = ctx:<ref>);
    - production_report(按 action.task_key 与 action_kind 过滤,与
      build 的过滤条件逐字一致;**仅键合法时列举** —— 空 task_key
      不产空键引用);
    - expansion_outcome(**两个写入口的键都枚举**):展开尝试的非事件
      结论走 record_expansion_outcome ⇒ action.task_key(仅键合法时
      列举);非事件动作完成(retrieve/decide/activate/transition 的
      调度结论)走 runflow._complete_action ⇒ stable_id("soutc",
      action_id) —— **S4-C03 回修(确认复核 §4):soutc 键按
      action_id 独立枚举,不依赖 action.task_key 非空**;S4b 首批
      在空 task_key 动作上提前 continue,使 child retrieve 等的
      no_local_candidate/unresolved_continuation 结论在 build 聚合
      与 manifest 引用里全部漏掉。缺键/缺席 artifact 读取时自然
      跳过(合法缺席);坏(损坏)artifact 在读取入口如实上抛,
      不静默略过。冻结计划 artifact 不在本索引内(native 构建不
      消费它;导出侧由 native_export 单独引用)。
    """
    conn = ledger.conn
    run_id = ledger.run_id
    actions = _rows_sorted(
        conn.execute(
            "SELECT action_id, action_kind, context_ref, subject_ref,"
            " task_key FROM search_actions WHERE run_id = ?"
            " ORDER BY action_id", (run_id,)).fetchall(), ("action_id",))
    entries: list[dict] = []
    context_refs = sorted({
        str(a.get("context_ref") or "") for a in actions
        if str(a.get("context_ref") or "")})
    for ref in context_refs:
        entries.append({"task_key": f"ctx:{ref}",
                        "name": _CONTEXT_ARTIFACT,
                        "source_action_id": ""})
    for action in actions:
        task_key = str(action.get("task_key") or "")
        kind = str(action.get("action_kind"))
        action_id = str(action.get("action_id"))
        outcome_kinds = ("expand_hypothesis", "retrieve", "decide",
                         "activate_deferred", "scenario_transition")
        # task_key 键引用:仅在键合法时列举(缺键不产空键引用)
        if task_key:
            if kind in ("expand_hypothesis", "retrieve", "decide"):
                entries.append({"task_key": task_key,
                                "name": _PRODUCTION_REPORT,
                                "source_action_id": action_id})
            if kind in outcome_kinds:
                entries.append({"task_key": task_key,
                                "name": _EXPANSION_OUTCOME,
                                "source_action_id": action_id})
        # soutc 键引用:按 action_id 独立枚举(S4-C03 —— 空 task_key
        # 不能挡 soutc(action_id) 的枚举;build 与 manifest 共用本索引)
        if kind in outcome_kinds:
            entries.append({"task_key": stable_id("soutc", action_id),
                            "name": _EXPANSION_OUTCOME,
                            "source_action_id": action_id})
    return sorted(entries, key=lambda e: (
        e["task_key"], e["name"], e["source_action_id"]))


def build_native_result(ledger, *, endpoint_record: dict,
                        include_declared_vs_executed: bool | None = None) -> dict:
    """从持久权威聚合原生结果对象(确定性;S4a 对象底座)。

    endpoint_record 必须是已通过首消费校验的记录(调用方经
    read_run_endpoint/consume_run_endpoint 取得;过期记录不得包装
    成正式结果)。构建纯只读;落盘为派生 artifact(键含 digest,
    不可变,重复生成同内容幂等)。

    ``include_declared_vs_executed``(P0b/D-6,默认 None = 读环境开关
    ``PPV1_P0B_D6_DIAGNOSTICS``,默认关闭):开启时在 payload 顶层
    新增可选 ``declared_vs_executed`` 诊断块;关闭时不新增任何键,
    载荷与基线逐字节等价。诊断块不参与 admission/排序/评分,也不
    改变任何既有字段。
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
    # ---- 状态身份闭合(官方链首次消费;P1 2026-10-14 / P1fix2 同日):
    # 完整出现集合逐行核形状/state_id 绑定/内容⇄哈希(与 store 写入/
    # 重放共用单一验证源),语义/出现逐对共用 ChemicalState.from_dict
    # 事实重算;坏源 state/appearance 在原生构建处结构化拒绝(单点
    # 腐蚀绕过 writer 不得被重新包装) ----
    _validate_native_state_rows(states, appearances)

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

    # ---- 上下文(条件/依赖;H07 + 内容身份首消费)----
    # S4b:引用集合与读取循环共用 artifact_reference_index(单一来源;
    # 追加顺序保持 S4a 语义:contexts 按引用排序,reports/outcomes 按
    # action 次序,name 次序 = report 先于 outcome)。
    refs = artifact_reference_index(ledger)

    def _envelope(task_key: str, name: str) -> dict | None:
        # S4-C03:坏必要 artifact(如 soutc)不能被静默略过 —— H07
        # 完整性失败结构化上抛(保全原文件;合法缺席仍返回 None 跳过)
        try:
            return read_search_artifact(
                ledger.artifact_store, task_key, name)
        except SearchArtifactIntegrityError as exc:
            raise NativeResultContractError(
                f"原生结果消费的必要 artifact 损坏:{task_key}/{name}"
                "(H07 完整性失败;保全原文件,不静默略过、不清洗后继续)",
                {"kind": "native_result_artifact_corrupt",
                 "task_key": task_key, "name": name,
                 "artifact_error_kind": exc.detail.get("kind"),
                 "original_error": type(exc).__name__}) from exc

    contexts: list[dict] = []
    for entry in refs:
        if entry["name"] != _CONTEXT_ARTIFACT:
            continue
        envelope = _envelope(entry["task_key"], _CONTEXT_ARTIFACT)
        if envelope is not None:
            contexts.append({
                "context_ref": entry["task_key"][len("ctx:"):],
                "payload": envelope.get("payload")})

    # ---- audit 结果/proof scope/失败原因(per-action artifact) ----
    audit_reports: list[dict] = []
    outcome_records: list[dict] = []
    _NAME_RANK = {_PRODUCTION_REPORT: 0, _EXPANSION_OUTCOME: 1}
    for entry in sorted(
            (e for e in refs if e["name"] in _NAME_RANK),
            key=lambda e: (e["source_action_id"], _NAME_RANK[e["name"]],
                           e["task_key"])):
        envelope = _envelope(entry["task_key"], entry["name"])
        if envelope is None:
            continue
        if entry["name"] == _PRODUCTION_REPORT:
            payload = dict(envelope.get("payload") or {})
            audit_reports.append({
                "action_id": str(entry["source_action_id"]),
                "task_key": entry["task_key"],
                "production_payload": payload,
            })
        else:
            payload = dict(envelope.get("payload") or {})
            outcome_records.append({
                "action_id": str(entry["source_action_id"]),
                "task_key": entry["task_key"],
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
    # ---- P0b/D-6 旁路披露(可选;默认关闭 ⇒ payload 零新增键) ----
    if include_declared_vs_executed is None:
        from .production import p0b_d6_diagnostics_enabled
        include_declared_vs_executed = p0b_d6_diagnostics_enabled()
    if include_declared_vs_executed:
        payload["declared_vs_executed"] = declared_vs_executed_block(payload)
    digest = content_hash(payload)
    payload["content_digest"] = digest
    return payload


# ---------------------------------------------------------------- P0b/D-6 派生


def _p0b_d6_event_body(event: dict) -> dict | None:
    """事件载荷:合法对象返回 dict;缺失/非对象/解析失败返回 None。

    ``None`` 表示“装配资料不可用”,与合法空对象/空参与物区分;调用方
    不得用 ``or []`` 归一成“已知为空”(R2)。
    """
    if not isinstance(event, dict):
        return None
    body = event.get("payload")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except (ValueError, TypeError):
            return None
    return body if isinstance(body, dict) else None


def _p0b_d6_product_participants(
        body: dict | None, state_smiles: dict[str, str],
) -> tuple[list[str] | None, list[str] | None]:
    """(产物侧 state_ref 列表, 对应结构列表)。

    缺失/坏类型参与物 ⇒ 两个返回值均为 ``None``(装配不可用);合法空
    列表 ⇒ ``([], [])``(已核为空)。产物侧引用存在但状态结构缺失/为空
    ⇒ 结构列表为 ``None``(结构轴不可用),引用列表仍保留。
    """
    if body is None:
        return None, None
    participants = body.get("participants")
    if not isinstance(participants, list):
        return None, None
    refs: list[str] = []
    for participant in participants:
        if not isinstance(participant, dict):
            return None, None
        if str(participant.get("side")) != _PRODUCT_SIDE:
            continue
        ref = str(participant.get("state_ref") or "")
        if not ref:
            return None, None
        refs.append(ref)
    values = [state_smiles.get(ref) for ref in refs]
    if any(not isinstance(value, str) or not value for value in values):
        return refs, None
    return refs, values


def _p0b_d6_action_payload(action: dict) -> dict:
    payload = (action or {}).get("payload")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError):
            payload = {}
    return payload if isinstance(payload, dict) else {}


def _p0b_d6_origin(logical_id: str) -> str:
    """origin 与既有字段同源(contract §1.1):logical_proposal_id 前缀。"""
    lid = str(logical_id or "")
    if not lid:
        return _UNKNOWN_TOKEN
    if lid.startswith("rec-"):
        return _RECORDED_TOKEN
    if lid.startswith("tpl-"):
        return "template"
    return "novel"


def derive_declared_vs_executed(
    payload: dict,
    *,
    qid_by_run_id: dict[str, str] | None = None,
) -> list[dict]:
    """从原生结果 payload 派生逐事件声明 vs 执行披露(纯只读)。

    与生产链共用 ``production.build_declaration_disclosure /
    reconcile_declared_vs_executed`` 单一来源;不重跑执行、不写任何
    事实。事件序 = ``(created_at, event_id)``(与冻结 scorer 的候选序
    一致)。输出禁止包含 SMILES/结构正文。
    """
    from .controlled_vocab import (
        PRODUCTION_REPORT_STATUS_SUBMITTED as _SUBMITTED_STATUS,
    )
    from .production import (
        build_declaration_disclosure,
        reconcile_declared_vs_executed,
    )

    payload = payload if isinstance(payload, dict) else {}
    qid_by_run_id = (
        qid_by_run_id if isinstance(qid_by_run_id, dict) else {})
    run_id = str(payload.get("run_id") or "")
    state_smiles: dict[str, str] = {}
    for state in payload.get("states") or []:
        if not isinstance(state, dict):
            continue
        sp = state.get("payload")
        if isinstance(sp, str):
            try:
                sp = json.loads(sp)
            except (ValueError, TypeError):
                sp = {}
        if not isinstance(sp, dict):
            sp = {}
        sid = str(state.get("state_id") or sp.get("state_id") or "")
        if sid:
            state_smiles[sid] = str(sp.get("smiles_isomeric") or "")
    actions = {}
    for action in payload.get("search_actions") or []:
        if not isinstance(action, dict):
            continue
        action_id = str(action.get("action_id") or "")
        if action_id:
            actions[action_id] = action
    reports: dict[str, list[tuple[dict, dict]]] = {}
    for report in payload.get("audit_production_reports") or []:
        if not isinstance(report, dict):
            continue
        pp = report.get("production_payload")
        if isinstance(pp, str):
            try:
                pp = json.loads(pp)
            except (ValueError, TypeError):
                pp = None
        # 只有可用对象载荷才算“报告在位”;缺失/坏类型保留为来源缺失。
        if not isinstance(pp, dict) or not pp:
            continue
        eid = str(pp.get("event_id")
                  or (((pp.get("event") or {})
                       if isinstance(pp.get("event"), dict) else {})
                      .get("event_id") or ""))
        if eid:
            reports.setdefault(eid, []).append((report, pp))
    for items in reports.values():
        items.sort(key=lambda item: (
            str(item[1].get("status") or ""),
            str(item[0].get("action_id") or "")))
    events = sorted(
        payload.get("events") or [],
        key=lambda e: (str((e or {}).get("created_at") or ""),
                       str((e or {}).get("event_id") or "")))
    rows: list[dict] = []
    for ordinal, event in enumerate(events, 1):
        event = event if isinstance(event, dict) else {}
        eid = str(event.get("event_id") or "")
        body = _p0b_d6_event_body(event)
        product_refs, product_smiles = _p0b_d6_product_participants(
            body, state_smiles)
        chosen = None
        for report, pp in reports.get(eid) or []:
            if str(pp.get("status") or "") == _SUBMITTED_STATUS:
                chosen = (report, pp)
                break
        if chosen is None and reports.get(eid):
            chosen = reports[eid][0]
        report_present = chosen is not None
        report, pp = chosen if chosen is not None else ({}, {})
        action = actions.get(str(report.get("action_id") or "")) or {}
        action_payload = _p0b_d6_action_payload(action)
        spec = action_payload.get("spec")
        disclosure = build_declaration_disclosure(spec)
        origin = _p0b_d6_origin(
            str(action_payload.get("logical_proposal_id") or ""))
        execution_raw = pp.get("execution") if report_present else None
        execution = (execution_raw
                     if isinstance(execution_raw, dict) and execution_raw
                     else None)
        tool_inputs = ((execution or {}).get("tool_inputs")
                       if isinstance(execution, dict) else None)
        tool_inputs = tool_inputs if isinstance(tool_inputs, dict) else {}
        tool_expectation = tool_inputs.get("expectation")
        tool_expectation = (tool_expectation
                            if isinstance(tool_expectation, dict) else {})
        tool_target = tool_expectation.get("target_smiles")
        expectation_invalid = (
            "expectation" in tool_inputs
            and (not isinstance(tool_inputs.get("expectation"), dict)
                 or (tool_target is not None
                     and not isinstance(tool_target, str))))
        expectation_target = (
            tool_target if isinstance(tool_target, str) and tool_target
            else str(disclosure.get("expectation_target") or ""))
        projection = (pp.get("report_projection") or {}) \
            if isinstance(pp.get("report_projection"), dict) else {}
        projection_ranks = projection.get("product_ranks")
        projection_ranks = (
            projection_ranks if isinstance(projection_ranks, list) else [])
        center_evidence = (
            execution.get("center_evidence")
            if isinstance(execution, dict) else None)
        center_evidence = (
            center_evidence if isinstance(center_evidence, dict) else {})
        row = reconcile_declared_vs_executed(
            disclosure,
            execution=execution,
            event_product_refs=product_refs,
            event_product_smiles=product_smiles,
            expectation_target=expectation_target,
            expectation_invalid=expectation_invalid,
            projection_ranks=projection_ranks,
            state_smiles_by_ref=state_smiles,
            audit_center=center_evidence,
            origin=origin,
            production_report_present=report_present,
        )
        row["ordinal"] = ordinal
        row["event_id_prefix"] = eid[:20]
        row["run_id_prefix"] = run_id[:20]
        row["qid_prefix"] = str(
            qid_by_run_id.get(run_id) or "")[:20]
        rows.append(row)
    return rows


def declared_vs_executed_block(
    payload: dict,
    *,
    qid_by_run_id: dict[str, str] | None = None,
) -> dict:
    """顶层披露块(schema/version/counts/events;contract §2)。"""
    from .production import (
        P0B_D6_DIAGNOSTIC_SCHEMA,
        P0B_D6_DIAGNOSTIC_VERSION,
        P0B_D6_IDENTITY_VERSION,
        P0B_D6_RULE_VERSION,
    )

    rows = derive_declared_vs_executed(
        payload, qid_by_run_id=qid_by_run_id)
    counts = {"consistent": 0, "inconsistent": 0, _UNKNOWN_TOKEN: 0,
              "not_applicable": 0}
    by_origin: dict[str, dict[str, int]] = {}
    for row in rows:
        status = str(row.get("status") or "")
        if status in counts:
            counts[status] += 1
        origin = str(row.get("origin") or _UNKNOWN_TOKEN)
        bucket = by_origin.setdefault(origin, {
            "consistent": 0, "inconsistent": 0, _UNKNOWN_TOKEN: 0,
            "not_applicable": 0})
        if status in bucket:
            bucket[status] += 1
    return {
        "schema": P0B_D6_DIAGNOSTIC_SCHEMA,
        "version": P0B_D6_DIAGNOSTIC_VERSION,
        "rule_version": P0B_D6_RULE_VERSION,
        "identity_version": P0B_D6_IDENTITY_VERSION,
        "universe": "submitted events in native result payload",
        "n_events": len(rows),
        "counts": counts,
        "by_origin": {k: dict(sorted(v.items()))
                      for k, v in sorted(by_origin.items())},
        "events": rows,
    }


def strip_declared_vs_executed(payload: dict,
                               *, keep_content_digest: bool = False) -> dict:
    """剔除可选诊断块(零漂移比较/证据用;不修改入参)。"""
    out = {k: v for k, v in (payload or {}).items()
           if k != "declared_vs_executed"}
    if not keep_content_digest:
        out.pop("content_digest", None)
    return out


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
