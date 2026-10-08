"""S5a 科学评测器接口(ppv1-evaluation-1;S5 任务书 §8/§9/§11/§12)。

S5a 边界(任务书 §15):本评测器是**接口与规则级程序行为交付** ——
消费 S4 公开入口(``read_native_export``;§3.1)、确定性零 LLM 判分、
输出结构化指标分轴;**不输出任何 dev/298 科学性能结论**:

- **零 LLM**(§4.3/S5-25):判分路径无任何模型调用;只消费冻结的
  结构化字段清单(见 ``_CONSUMED_EXPORT_FIELDS``/``_CONSUMED_INPUT_
  FIELDS``),自然语言字段不进任何判定 —— 输入里的自由文本/narrative
  不能改变程序结果;
- **收费 provider 默认关**(§13.5/S5-26):``model_provider_policy``
  默认 ``none``;``real`` 无用户逐次授权 ⇒ 结构化拒绝(本模块无任何
  网络代码,网络请求与费用为零;正式科学评测不启动);
- **确定性**(S5-24):输出无时间戳、canonical_json 键序 + 列表稳定
  排序;``output_sha256`` = 输出去掉自身后的内容哈希;同输入 ⇒
  字节级一致;
- **状态语义**(§12/S5-23):评测器只允许发 ``pending_*``/``interface_
  verified_only``/``blocked_*`` 族;``evaluated_*`` 永不由程序生成
  (§11 第 19 步:最终科学状态由用户/teacher 按预注册裁定);
- **防泄漏**(§6.3/S5-07/S5-08):split manifest + 同 source group 跨
  集合 + known/unseen 直接证据重叠检查;失败 ⇒ ``blocked_leakage``,
  不聚合;
- **金标写入守卫**(S5-27):含金标产物只能进授权 gitignored 根
  (``persist_evaluation_output``);普通目录拒绝;
- **S4 导出缺席**(S5-28):无导出 ⇒ 状态 ``pending_no_independent_
  data``,不运行正式科学评测。

匹配规则(严格结构身份 vs CN 旁证、step_scope 分轴、条件
conflict/unknown/compatible、endpoint/矿化声明检查、预算漏展开、
深度分桶)全部为 **proposed 规则级实现**(预注册模板中逐项标注
proposed;最终冻结属用户/teacher,§10.1)。阈值/样本量/分母/置信
区间全部 TBD(输出里逐项携带 ``TBD_USER_TEACHER_DECISION``)。

本模块不读取真实科学数据/金标/题面/封存 run;不写数据库;合成
规则级测试之外的数字一律 interface/pending。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..domain.models import canonical_json, content_hash
from .native_export import read_native_export
from .profile import (
    PPV1_EVALUATION_VERSION,
    PPV1_NATIVE_EXPORT_VERSION,
    PPV1_SPLIT_MANIFEST_VERSION,
)
from .reference_graph import (
    DOMAINS,
    ENDPOINT_ASSESSMENTS,
    SPLITS,
    TRACKS,
    ReferenceGraphContractError,
    load_reference_graph,
    reference_graph_sha256,
    validate_reference_graph,
)

try:  # chemstate 的严格身份/CN 旁证与生产同一事实源
    from .chemstate import ChemicalStateError, strict_identity_of
    from ..domain.identity import cn_identity
except ImportError:  # pragma: no cover —— 环境异常时 fail-closed
    strict_identity_of = None  # type: ignore[assignment]
    cn_identity = None  # type: ignore[assignment]
    ChemicalStateError = RuntimeError  # type: ignore[assignment]

# ---- §12 状态枚举与程序可发子集 ----

SCIENTIFIC_STATUSES = frozenset({
    "pending_no_independent_data",
    "pending_preregistration",
    "pending_user_teacher_decision",
    "interface_verified_only",
    "evaluated_not_passed",
    "evaluated_passed_with_scope",
    "blocked_data_integrity",
    "blocked_leakage",
    "blocked_scoring_contract",
})
# 评测器永不发 evaluated_*(§11 第 19 步:最终科学状态由用户/teacher
# 按预注册结果裁定后另行登记)
EMITTED_STATUSES = frozenset(SCIENTIFIC_STATUSES - {
    "evaluated_not_passed", "evaluated_passed_with_scope"})

DATA_SCOPES = frozenset({"synthetic_rule_level", "real"})
PROVIDER_KINDS = frozenset({"none", "scripted", "real"})
SPLITS_LIST = sorted(SPLITS)
STOP_REASONS = frozenset({"budget_limit", "depth_limit",
                          "no_local_candidate", "awaiting_prediction",
                          "exhausted_search", "user_stop"})

# 金标内容唯一允许的落盘根(镜像 .gitignore 的金标隔离目录;S5b 前
# 评测输出本身不含金标 —— 本守卫为接口级预置,S5-27)
GOLD_AUTHORIZED_ROOTS = frozenset({
    "reports/phase_s0_hit60/manual_review",
    "reports/phase_s1_hit60/dev_gold",
    "reports/phase_s15_hit60/edit_path_replay/raw_inputs",
})

# 评测器实际消费的结构化字段(S5-25:自然语言/自由文本字段不进
# 判定;本清单之外的一切输入字段一律忽略,不参与任何匹配或计数)
_CONSUMED_INPUT_FIELDS = (
    "evaluator_schema_version", "run_identity", "native_path_exports",
    "reference_graph_manifest", "split_manifest", "domain", "track",
    "metric_policy_version", "preregistration_id",
    "scoring_policy_version", "missingness_policy_version",
    "data_scope", "interface_verification", "model_provider_policy",
)
_CONSUMED_EXPORT_FIELDS = (
    "states", "state_appearances", "paths", "hypotheses", "events",
    "alternatives", "coproducts", "contexts", "provenance_records",
    "audit_production_reports", "expansion_outcomes",
    "deferred_entries", "blocked_entries", "search_actions",
    "model_requests", "budget", "endpoint_record", "event_ids",
    "run_id", "native_result_version",
)


class EvaluationContractError(RuntimeError):
    """评测契约违反(结构化 fail-closed;零写入、零网络)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 输入校验


def _req_str(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvaluationContractError(
            f"评测输入字段 {field} 必须是非空字符串(缺字段明确失败,"
            "不静默补全)", {"kind": "evaluation_input_field_invalid",
                         "field": field})
    return value


def _req_enum(value, field: str, allowed: frozenset) -> str:
    _req_str(value, field)
    if value not in allowed:
        raise EvaluationContractError(
            f"评测输入字段 {field} 取值非法:{value!r}(允许 "
            f"{sorted(allowed)})", {"kind": "evaluation_input_enum_invalid",
                                 "field": field, "value": value,
                                 "allowed": sorted(allowed)})
    return value


def validate_evaluation_input(evaluation_input: dict) -> dict:
    """校验评测输入(§8.1;缺字段/未知枚举/混合题域与轨道拒绝)。

    S5-21/S5-22:输入声明单一 (domain, track);manifest 中任何参考图
    的 domain/track 与之不符 ⇒ 结构化拒绝(不产生无题域标签总分)。
    损坏输入结构化拒、不静默删字段。
    """
    if not isinstance(evaluation_input, dict):
        raise EvaluationContractError(
            "评测输入必须是对象", {"kind":
                                   "evaluation_input_not_object",
                                   "value_type":
                                   type(evaluation_input).__name__})
    for field in _CONSUMED_INPUT_FIELDS:
        if field not in evaluation_input and field not in (
                "data_scope", "interface_verification",
                "model_provider_policy"):
            raise EvaluationContractError(
                f"评测输入缺必需字段:{field}(§8.1;缺字段明确失败)",
                {"kind": "evaluation_input_field_missing",
                 "field": field})
    declared_version = str(evaluation_input.get(
        "evaluator_schema_version") or "")
    if declared_version != PPV1_EVALUATION_VERSION:
        raise EvaluationContractError(
            f"评测器 schema 版本未知:{declared_version!r}(当前 "
            f"{PPV1_EVALUATION_VERSION};fail-closed 不猜迁移)", {
                "kind": "evaluation_version_unknown",
                "field": "evaluator_schema_version"})
    domain = _req_enum(evaluation_input.get("domain"), "domain", DOMAINS)
    track = _req_enum(evaluation_input.get("track"), "track", TRACKS)
    run_identity = evaluation_input.get("run_identity")
    if not isinstance(run_identity, dict):
        raise EvaluationContractError(
            "run_identity 必须是对象", {"kind":
                                       "evaluation_input_field_invalid",
                                       "field": "run_identity"})
    for key in ("run_id", "profile_version", "export_schema_version"):
        if key not in run_identity:
            raise EvaluationContractError(
                f"run_identity.{key} 缺失", {
                    "kind": "evaluation_input_field_missing",
                    "field": f"run_identity.{key}"})
        _req_str(run_identity.get(key), f"run_identity.{key}")
    if str(run_identity.get("export_schema_version")) != \
            PPV1_NATIVE_EXPORT_VERSION:
        raise EvaluationContractError(
            f"run_identity.export_schema_version 与当前登记源不符:"
            f"{run_identity.get('export_schema_version')!r}"
            f"(当前 {PPV1_NATIVE_EXPORT_VERSION};S4 导出契约绑定)",
            {"kind": "evaluation_export_version_mismatch",
             "field": "run_identity.export_schema_version"})
    for field in ("metric_policy_version", "preregistration_id",
                  "scoring_policy_version", "missingness_policy_version"):
        _req_str(evaluation_input.get(field), field)
    _req_enum(evaluation_input.get("data_scope") or "synthetic_rule_level",
              "data_scope", DATA_SCOPES)
    if not isinstance(evaluation_input.get("interface_verification") or
                      False, bool):
        raise EvaluationContractError(
            "interface_verification 必须是布尔", {
                "kind": "evaluation_input_field_invalid",
                "field": "interface_verification"})
    # ---- provider 策略(默认关;real 无授权拒绝在 evaluate 侧) ----
    provider = evaluation_input.get("model_provider_policy") or {}
    if not isinstance(provider, dict):
        raise EvaluationContractError(
            "model_provider_policy 必须是对象(默认 {'provider_kind':"
            " 'none'})", {"kind": "evaluation_input_field_invalid",
                        "field": "model_provider_policy"})
    declared_provider = str(provider.get("provider_kind") or "none")
    if declared_provider not in PROVIDER_KINDS:
        raise EvaluationContractError(
            f"model_provider_policy.provider_kind 非法:"
            f"{declared_provider!r}(允许 {sorted(PROVIDER_KINDS)};"
            "默认 none = 无网络请求、零费用)", {
                "kind": "evaluation_input_enum_invalid",
                "field": "model_provider_policy.provider_kind"})
    # ---- 导出条目(§8.1;lossy 投影显式标记) ----
    exports = evaluation_input.get("native_path_exports")
    if not isinstance(exports, list):
        raise EvaluationContractError(
            "native_path_exports 必须是列表", {
                "kind": "evaluation_input_field_invalid",
                "field": "native_path_exports"})
    export_digests: set[str] = set()
    for i, entry in enumerate(exports):
        field = f"native_path_exports[{i}]"
        if not isinstance(entry, dict):
            raise EvaluationContractError(
                f"{field} 必须是对象", {"kind":
                                       "evaluation_input_field_invalid",
                                       "field": field})
        _req_str(entry.get("run_id"), f"{field}.run_id")
        digest = _req_str(entry.get("export_digest"),
                          f"{field}.export_digest")
        if digest in export_digests:
            raise EvaluationContractError(
                f"export_digest 重复:{digest}", {
                    "kind": "evaluation_input_duplicate_export",
                    "export_digest": digest})
        export_digests.add(digest)
        lossy = bool(entry.get("lossy_projection") or False)
        if lossy:
            # §3.1:消费 v3 有损投影必须标记 lossy + 原生引用 + 已丢字段
            if not isinstance(entry.get("native_reference"), str) or \
                    not entry.get("native_reference"):
                raise EvaluationContractError(
                    f"{field}.native_reference 缺失(lossy 投影必须声明"
                    "原生结果引用)", {
                        "kind": "evaluation_input_field_missing",
                        "field": f"{field}.native_reference"})
            if not isinstance(entry.get("lost_fields"), list):
                raise EvaluationContractError(
                    f"{field}.lost_fields 缺失(lossy 投影必须声明已丢"
                    "字段;该投影不得用于完整路径语义科学指标)", {
                        "kind": "evaluation_input_field_missing",
                        "field": f"{field}.lost_fields"})
    # ---- 参考图 manifest(S5-21/22:题域/轨道一致性) ----
    manifest = evaluation_input.get("reference_graph_manifest")
    if not isinstance(manifest, list) or not manifest:
        raise EvaluationContractError(
            "reference_graph_manifest 必须是非空列表", {
                "kind": "evaluation_input_field_invalid",
                "field": "reference_graph_manifest"})
    graph_ids: set[str] = set()
    for i, entry in enumerate(manifest):
        field = f"reference_graph_manifest[{i}]"
        if not isinstance(entry, dict):
            raise EvaluationContractError(
                f"{field} 必须是对象", {
                    "kind": "evaluation_input_field_invalid",
                    "field": field})
        graph_id = _req_str(entry.get("reference_graph_id"),
                            f"{field}.reference_graph_id")
        if graph_id in graph_ids:
            raise EvaluationContractError(
                f"reference_graph_id 重复:{graph_id}", {
                    "kind": "evaluation_input_duplicate_reference_graph",
                    "reference_graph_id": graph_id})
        graph_ids.add(graph_id)
        _req_str(entry.get("sha256"), f"{field}.sha256")
        entry_domain = str(entry.get("domain") or "")
        entry_track = str(entry.get("track") or "")
        if entry_domain != domain:
            raise EvaluationContractError(
                f"参考图 {graph_id} 题域 {entry_domain!r} 与评测输入 "
                f"{domain!r} 不符(混合题域拒绝;dev/298 必须分开评测,"
                "不产生无题域标签总分;S5-21)", {
                    "kind": "evaluation_domain_mismatch",
                    "reference_graph_id": graph_id,
                    "manifest_domain": entry_domain,
                    "input_domain": domain})
        if entry_track != track:
            raise EvaluationContractError(
                f"参考图 {graph_id} 轨道 {entry_track!r} 与评测输入 "
                f"{track!r} 不符(known/unseen 混合拒绝;两轨道不得合并"
                "单一总分;S5-22)", {
                    "kind": "evaluation_track_mismatch",
                    "reference_graph_id": graph_id,
                    "manifest_track": entry_track,
                    "input_track": track})
    if not isinstance(evaluation_input.get("split_manifest"), dict):
        raise EvaluationContractError(
            "split_manifest 必须是对象", {
                "kind": "evaluation_input_field_invalid",
                "field": "split_manifest"})
    return evaluation_input


def validate_split_manifest(manifest: dict) -> dict:
    """校验划分清单(§6.3;确定性;同 source group 跨集合由 leakage
    检查另核,本层先核 schema 完整性)。"""
    if not isinstance(manifest, dict):
        raise EvaluationContractError(
            "split manifest 必须是对象", {
                "kind": "split_manifest_not_object"})
    if str(manifest.get("schema_version") or "") != \
            PPV1_SPLIT_MANIFEST_VERSION:
        raise EvaluationContractError(
            f"split manifest 版本未知:{manifest.get('schema_version')!r}"
            f"(当前 {PPV1_SPLIT_MANIFEST_VERSION};fail-closed)", {
                "kind": "split_manifest_version_unknown",
                "schema_version": str(manifest.get("schema_version")
                                       or "")})
    _req_str(manifest.get("split_manifest_id"), "split_manifest_id")
    _req_str(manifest.get("split_rule_version"), "split_rule_version")
    _req_str(manifest.get("input_data_manifest_hash"),
             "split_manifest.input_data_manifest_hash")
    assignments = manifest.get("assignments")
    if not isinstance(assignments, list):
        raise EvaluationContractError(
            "split_manifest.assignments 必须是列表", {
                "kind": "split_manifest_field_invalid",
                "field": "assignments"})
    graph_assignments: dict[str, str] = {}
    for i, assignment in enumerate(assignments):
        field = f"split_manifest.assignments[{i}]"
        if not isinstance(assignment, dict):
            raise EvaluationContractError(
                f"{field} 必须是对象", {
                    "kind": "split_manifest_field_invalid",
                    "field": field})
        for key in ("reference_graph_id", "source_group_id", "split"):
            if key not in assignment:
                raise EvaluationContractError(
                    f"{field}.{key} 缺失", {
                        "kind": "split_manifest_field_missing",
                        "field": f"{field}.{key}"})
        graph_id = _req_str(assignment.get("reference_graph_id"),
                            f"{field}.reference_graph_id")
        split = _req_enum(assignment.get("split"), f"{field}.split", SPLITS)
        if graph_id in graph_assignments and \
                graph_assignments[graph_id] != split:
            raise EvaluationContractError(
                f"参考图 {graph_id} 被指到多个 split:"
                f"{graph_assignments[graph_id]}/{split}", {
                    "kind": "split_manifest_duplicate_assignment",
                    "reference_graph_id": graph_id})
        graph_assignments[graph_id] = split
        _req_str(assignment.get("source_group_id"),
                 f"{field}.source_group_id")
    exclusion = manifest.get("unseen_exclusion_manifest")
    if not isinstance(exclusion, dict):
        raise EvaluationContractError(
            "split_manifest.unseen_exclusion_manifest 必须是对象"
            "(即使 known 轨道也须显式声明空排除范围)", {
                "kind": "split_manifest_field_invalid",
                "field": "unseen_exclusion_manifest"})
    _req_enum(exclusion.get("track") or "unseen_path_inference",
              "unseen_exclusion_manifest.track", TRACKS)
    excluded = exclusion.get("excluded") or []
    if not isinstance(excluded, list):
        raise EvaluationContractError(
            "unseen_exclusion_manifest.excluded 必须是列表", {
                "kind": "split_manifest_field_invalid",
                "field": "unseen_exclusion_manifest.excluded"})
    for i, item in enumerate(excluded):
        field = f"unseen_exclusion_manifest.excluded[{i}]"
        if not isinstance(item, dict):
            raise EvaluationContractError(
                f"{field} 必须是对象", {
                    "kind": "split_manifest_field_invalid",
                    "field": field})
        for key in ("source_group_id", "scope", "reason"):
            if key not in item:
                raise EvaluationContractError(
                    f"{field}.{key} 缺失(未见排除范围必须显式:精确反应"
                    "/精确底物/精确边/整条研究路线 + 理由)", {
                        "kind": "split_manifest_field_missing",
                        "field": f"{field}.{key}"})
        _req_str(item.get("source_group_id"), f"{field}.source_group_id")
        _req_str(item.get("scope"), f"{field}.scope")
        _req_str(item.get("reason"), f"{field}.reason")
    return manifest


# ---------------------------------------------------------------- 泄漏检查


def check_leakage(split_manifest: dict,
                  reference_graphs: dict[str, dict]) -> dict:
    """防泄漏检查(§6.3;S5-07/S5-08;失败 ⇒ blocked_leakage,不聚合)。

    - 同一 source_group_id 跨 development/tuning/held_out/
      independent_confirmation 集合 ⇒ violation(S5-07);
    - 同一研究路线(route_group_key)跨集合 ⇒ violation(§6.3 同研究
      相邻边/高度相关路线不得拆到不同集合;proposed 规则);
    - unseen 排除范围与 known 评测集直接证据重叠 ⇒ violation(S5-08);
    - 同根对象跨 development 与 held_out/independent_confirmation ⇒
      violation(proposed:研究来源高度相关的根按 group split 整体划分);
    - 多数据库记录归并 source group 的记账(记录数 vs 组数)与
      independence unknown 组披露(S5-05/S5-06;披露非 violation)。
    """
    violations: list[dict] = []
    group_splits: dict[str, set[str]] = {}
    for assignment in split_manifest.get("assignments") or []:
        group_id = str(assignment.get("source_group_id"))
        split = str(assignment.get("split"))
        group_splits.setdefault(group_id, set()).add(split)
    for group_id, splits in sorted(group_splits.items()):
        if len(splits) > 1:
            violations.append({
                "check": "source_group_across_splits",
                "source_group_id": group_id,
                "splits": sorted(splits),
                "spec": "S5-07/§6.3:同一 source_group_id 不得跨开发/留出"
                        "/独立确证集合"})
    # ---- 路线/根对象跨集合(proposed 规则级) ----
    route_splits: dict[str, set[str]] = {}
    root_splits: dict[str, set[str]] = {}
    group_route: dict[str, str] = {}
    for graph_id, graph in sorted(reference_graphs.items()):
        assignment = graph.get("split_assignment") or {}
        split = str(assignment.get("split") or "")
        for route_key in assignment.get("route_group_keys") or []:
            route_splits.setdefault(str(route_key), set()).add(split)
        root_splits.setdefault(
            str((graph.get("root_entity") or {}).get("entity_id") or ""),
            set()).add(split)
        for group_ref in (graph.get("source_groups") or []):
            group_route.setdefault(
                str(group_ref.get("source_group_id")), split)
    for route_key, splits in sorted(route_splits.items()):
        if len(splits) > 1:
            violations.append({
                "check": "route_identity_across_splits",
                "route_group_key": route_key,
                "splits": sorted(splits),
                "spec": "§6.3:同一研究路线/相邻边不得拆到不同集合"
                        "(proposed)"})
    for root_id, splits in sorted(root_splits.items()):
        if len(splits) > 1 and ("development" in splits and (
                "held_out" in splits or "independent_confirmation"
                in splits)):
            violations.append({
                "check": "root_entity_across_development_and_held_out",
                "root_entity_id": root_id,
                "splits": sorted(splits),
                "spec": "§6.3:同根对象研究来源高度相关时按 group split "
                        "整体划分(proposed)"})
    # ---- known/unseen 直接证据重叠(S5-08) ----
    excluded_groups = sorted({
        str(item.get("source_group_id"))
        for item in ((split_manifest.get("unseen_exclusion_manifest")
                      or {}).get("excluded") or [])})
    known_groups = sorted(group_splits)
    overlap = sorted(set(excluded_groups) & set(known_groups))
    if overlap:
        violations.append({
            "check": "unseen_exclusion_overlaps_known_evaluation",
            "source_group_ids": overlap,
            "spec": "S5-08:known 与 unseen 直接证据重叠 ⇒ 未见轨道排除"
                    "检查失败,不继续聚合"})
    # ---- 记账与披露(非 violation) ----
    record_count = 0
    unknown_independence: list[str] = []
    for graph in reference_graphs.values():
        for group in graph.get("source_groups") or []:
            record_count += len(group.get("member_records") or [])
            if str(group.get("independence_status")) == "unknown":
                unknown_independence.append(
                    str(group.get("source_group_id")))
    return {
        "status": "failed" if violations else "passed",
        "violations": violations,
        "statistics": {
            "source_group_count": len(group_splits),
            "database_record_count": record_count,
            "record_to_group_ratio_note": (
                "同一来源组的多条数据库记录只计一个 source group"
                "(S5-05);不虚增独立支持"),
            "unknown_independence_groups": sorted(
                set(unknown_independence)),
            "unknown_independence_note": (
                "independence=unknown 的组不进入要求独立支持的指标分母"
                "(S5-06;除非预注册另有规定)"),
        },
    }


# ---------------------------------------------------------------- 匹配引擎


def _export_states(payload: dict) -> dict[str, dict]:
    """导出 states 行 → {state_id: {smiles_isomeric, cn_identity, ...}}。"""
    out: dict[str, dict] = {}
    for row in payload.get("states") or []:
        state_id = str(row.get("state_id"))
        body = row.get("payload") or {}
        if isinstance(body, str):
            import json as _json
            try:
                body = _json.loads(body)
            except (ValueError, TypeError):
                body = {}
        out[state_id] = {
            "smiles_isomeric": str(body.get("smiles_isomeric") or ""),
            "cn_identity": str(body.get("cn_identity") or ""),
        }
    return out


def _event_participants(event_row: dict) -> list[dict]:
    body = event_row.get("payload")
    if isinstance(body, str):
        import json as _json
        try:
            body = _json.loads(body)
        except (ValueError, TypeError):
            body = {}
    return [p for p in (body or {}).get("participants") or []
            if isinstance(p, dict)]


def _hypothesis_payloads(payload: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in payload.get("hypotheses") or []:
        body = row.get("payload")
        if isinstance(body, str):
            import json as _json
            try:
                body = _json.loads(body)
            except (ValueError, TypeError):
                body = {}
        out[str(row.get("hypothesis_id"))] = body or {}
    return out


def match_reference_nodes(reference_graph: dict,
                          payload: dict) -> list[dict]:
    """参考节点匹配(确定性;严格身份 vs CN 旁证分轴;distinct
    occurrence 不按 CN/首现合并)。

    返回逐 reference 节点条目:
    - ``match_status`` ∈ strict_structure | cn_only | unmatched |
      reference_structure_unparseable;
    - 严格结构命中要求双方严格身份相等;CN 相同但严格身份不同/未知
      ⇒ ``cn_only``(**不**计为严格结构命中,S5-10/S5-11);
    - 每条 occurrence 独立条目(同结构不同 occurrence 不合并,S5-04);
    - 预测侧 occurrence 计数(state_appearances/事件参与)如实披露。
    """
    states = _export_states(payload)
    appearance_counts: dict[str, int] = {}
    for row in payload.get("state_appearances") or []:
        appearance_counts[str(row.get("state_id"))] = \
            appearance_counts.get(str(row.get("state_id")), 0) + 1
    participation_counts: dict[str, int] = {}
    for event in payload.get("events") or []:
        for participant in _event_participants(event):
            ref = str(participant.get("state_ref") or "")
            participation_counts[ref] = participation_counts.get(ref, 0) + 1
    out: list[dict] = []
    for node in reference_graph.get("nodes") or []:
        entry = {
            "node_id": str(node.get("node_id")),
            "occurrence_id": str(node.get("occurrence_id")),
            "role": str(node.get("role")),
            "reference_identity_scope": str(
                node.get("structure_identity_scope")),
            "match_status": "unmatched",
            "matched_state_ids": [],
            "cn_only_state_ids": [],
            "predicted_occurrence_count": 0,
        }
        try:
            ref_strict = strict_identity_of(
                str(node.get("structure_smiles")))
        except ChemicalStateError:
            entry["match_status"] = "reference_structure_unparseable"
            entry["match_status_note"] = (
                "参考图结构不可解析 ⇒ 该节点不参与匹配(样本按坏输入"
                "披露,不静默删除)")
            out.append(entry)
            continue
        ref_cn = cn_identity(str(node.get("structure_smiles")))
        strict_ids: list[str] = []
        cn_ids: list[str] = []
        for state_id, state in sorted(states.items()):
            pred_strict = state["smiles_isomeric"]
            if pred_strict == ref_strict:
                strict_ids.append(state_id)
            elif ref_cn is not None and state["cn_identity"] == ref_cn:
                cn_ids.append(state_id)
        if strict_ids:
            entry["match_status"] = "strict_structure"
            entry["matched_state_ids"] = sorted(strict_ids)
            entry["predicted_occurrence_count"] = max(
                appearance_counts.get(sid, 0) for sid in strict_ids)
        elif cn_ids:
            # CN 相同但严格身份不同/未知:旁证,不计严格命中
            entry["match_status"] = "cn_only"
            entry["cn_only_state_ids"] = sorted(cn_ids)
            entry["predicted_occurrence_count"] = max(
                participation_counts.get(sid, 0) for sid in cn_ids)
        out.append(entry)
    return out


def match_reference_edges(reference_graph: dict, payload: dict,
                          node_matches: list[dict]) -> list[dict]:
    """参考边匹配(确定性;step_scope 分轴;备选不合并;共同产物不被
    报告 K 删除)。

    - 候选事件:反应物/产物侧状态分别命中 from/to 参考节点的严格
      匹配集合;
    - ``match_status`` ∈ matched_strict | matched_structure_only |
      unmatched_reference_coverage | unmatched_budget_unexpanded |
      unmatched —— step_scope 不一致 ⇒ ``matched_structure_only``
      (net reaction/elementary step/multistep summary 不混作同一边,
      S5-12);
    - 同父多备选事件逐条列示(A→B 与 A→C 不合并成 B+C 单一事件,
      S5-02);
    - 事件级共同产物参与物完整计数(报告 K/展开宽度不删 C,S5-03)。
    """
    states = _export_states(payload)
    strict_by_node: dict[str, set[str]] = {}
    for entry in node_matches:
        if entry["match_status"] == "strict_structure":
            strict_by_node[entry["node_id"]] = set(
                entry["matched_state_ids"])
    hypotheses = _hypothesis_payloads(payload)
    events = payload.get("events") or []
    stop_reason = str(((payload.get("endpoint_record") or {}).get(
        "search_stop_reason") or {}).get("primary") or "")
    deferred_count = len(payload.get("deferred_entries") or [])
    coverage = reference_graph.get("coverage_statement") or {}
    not_evaluable_edges = set(
        str(x) for x in coverage.get("not_evaluable_edge_ids") or [])
    known_gaps = list(coverage.get("known_gaps") or [])
    out: list[dict] = []
    for edge in reference_graph.get("edges") or []:
        edge_id = str(edge.get("edge_id"))
        from_ids = [str(x) for x in edge.get("from_node_ids") or []]
        to_ids = [str(x) for x in edge.get("to_node_ids") or []]
        from_states = set().union(*(
            strict_by_node.get(n, set()) for n in from_ids)) if \
            from_ids else set()
        to_states = set().union(*(
            strict_by_node.get(n, set()) for n in to_ids)) if \
            to_ids else set()
        exact_events: list[dict] = []
        coverage_mismatch_events: list[dict] = []
        structure_only_events: list[dict] = []
        if (not from_ids or from_states) and (to_ids and to_states):
            # 参考侧声明了 from/to 节点但严格匹配集为空 ⇒ 不产生候选
            # (结构未命中不能借空集放行为"任意反应物")
            for event in sorted(events,
                                key=lambda e: str(e.get("event_id"))):
                participants = _event_participants(event)
                reactants = {str(p.get("state_ref")) for p in participants
                             if str(p.get("side")) == "reactant"}
                products = {str(p.get("state_ref")) for p in participants
                            if str(p.get("side")) == "product"}
                if not (reactants & from_states or
                        (not from_states and reactants)):
                    continue
                if not products & to_states:
                    continue
                hypothesis = hypotheses.get(
                    str(event.get("hypothesis_id"))) or {}
                event_scope = str(hypothesis.get("step_scope")
                                  or "unknown")
                ref_scope = str(edge.get("step_scope") or "unknown")
                item = {
                    "event_id": str(event.get("event_id")),
                    "event_step_scope": event_scope,
                    "reference_step_scope": ref_scope,
                    "step_scope_consistent": event_scope == ref_scope,
                    "participant_state_refs": sorted({
                        str(p.get("state_ref"))
                        for p in _event_participants(event)}),
                    "coproduct_participants": sorted({
                        str(p.get("state_ref")) for p
                        in _event_participants(event)
                        if str(p.get("role")) == "coproduct"}),
                    # 参与物覆盖(proposed 规则:参考声明完整清单时,
                    # 精确 = 事件参与物集合与参考节点集合两侧相等;
                    # 事件多出共同产物等 ⇒ 超集;缺声明参与物 ⇒ 部分
                    # —— 两种非精确覆盖均单独披露,不计严格匹配)
                    "participant_coverage": (
                        "exact" if reactants == from_states
                        and products == to_states
                        else ("superset" if
                              from_states <= reactants
                              and to_states <= products
                              else "partial_subset")),
                }
                if item["step_scope_consistent"]:
                    if item["participant_coverage"] == "exact":
                        exact_events.append(item)
                    else:
                        coverage_mismatch_events.append(item)
                else:
                    structure_only_events.append(item)
        if exact_events:
            status = "matched_strict"
        elif coverage_mismatch_events:
            status = "matched_participant_coverage_partial"
        elif structure_only_events:
            status = "matched_structure_only"
        elif edge_id in not_evaluable_edges or known_gaps:
            status = "unmatched_reference_coverage"
        elif stop_reason in ("budget_limit", "depth_limit") or \
                deferred_count:
            status = "unmatched_budget_unexpanded"
        else:
            status = "unmatched"
        entry = {
            "edge_id": edge_id,
            "match_status": status,
            "matched_events": exact_events,
            "coverage_mismatch_events": coverage_mismatch_events,
            "structure_only_events": structure_only_events,
            "reference_participant_node_ids": [
                str(p.get("node_id"))
                for p in edge.get("participants") or []],
            "coproduct_preserved_note": (
                "完整事件保留共同产物参与物(报告 K/展开宽度不删除;"
                "S5-03);同父备选反应各自独立(不合并为单反应,S5-02)"),
        }
        out.append(entry)
    return out


def _value_matches(required: str, fact_value: str) -> bool:
    """确定性值比较(精确字符串;或 lo-hi 区间包含数值)。"""
    if str(required) == str(fact_value):
        return True
    required = str(required)
    fact_value = str(fact_value)
    if "-" in required:
        parts = required.split("-", 1)
        try:
            low, high = float(parts[0]), float(parts[1])
            value = float(fact_value)
            return low <= value <= high
        except (ValueError, TypeError):
            return False
    return False


def classify_condition_requirement(requirement: dict,
                                   facts: list[dict]) -> str:
    """条件分类(§9.5;conflict/unknown/compatible/分桶,不互相混算)。

    - essential + 事实 known_absent 或值冲突 ⇒ ``essential_conflict``
      (S5-14;unknown 不混入冲突);
    - 事实缺席/未知、要求状态未知 ⇒ ``condition_unknown``
      (S5-13:必要项缺失报 unknown,不报 compatible);
    - preference 不满足 ⇒ ``preference_unsatisfied``(非冲突);
    - 事实与要求均已知且一致 ⇒ ``compatible``;
    - 要求挂接的 subject scenario 与事实场景不同 ⇒
      ``scenario_transition_changed``;
    - 历史来源条件由 ``source_conditions_preserved`` 原样披露
      (S5-15,不改写为当前事实 —— 不在本分类器内)。
    """
    key = str(requirement.get("key") or "")
    required_level = str(requirement.get("required") or "essential")
    required_value = str(requirement.get("value_or_interval") or "")
    required_status = str(requirement.get("status") or "unknown")
    ref_scenario = str(requirement.get("subject_scenario_ref") or "")
    if required_status == "unknown":
        return "condition_unknown"
    matching = [f for f in facts
                if isinstance(f, dict) and str(f.get("key")) == key]
    if not matching:
        return "condition_unknown"
    fact = matching[0]
    fact_status = str(fact.get("status") or "unknown")
    fact_value = str(fact.get("value") or "")
    fact_scenario = str(fact.get("subject_scenario_ref") or "")
    if ref_scenario and fact_scenario and ref_scenario != fact_scenario:
        return "scenario_transition_changed"
    if fact_status == "unknown":
        return "condition_unknown"
    if fact_status == "known_absent":
        return ("essential_conflict" if required_level == "essential"
                else "preference_unsatisfied")
    if fact_status == "known_present":
        if _value_matches(required_value, fact_value):
            return "compatible"
        return ("essential_conflict" if required_level == "essential"
                else "preference_unsatisfied")
    return "condition_unknown"


def classify_sample_conditions(reference_graph: dict,
                               payload: dict) -> dict:
    """样本级条件轴:参考条件要求 × 预测条件事实(来自导出 contexts
    的 condition_facts;S4 公开字段)分桶 + 历史来源条件原样保留。"""
    facts: list[dict] = []
    for context in payload.get("contexts") or []:
        body = context.get("payload") or {}
        if isinstance(body, dict):
            facts.extend(x for x in body.get("condition_facts") or []
                         if isinstance(x, dict))
    buckets: dict[str, int] = {}
    details: list[dict] = []
    requirements: list[dict] = []
    for node in reference_graph.get("nodes") or []:
        requirements.extend(node.get("condition_scope") or [])
    for edge in reference_graph.get("edges") or []:
        requirements.extend(edge.get("condition_requirements") or [])
    for requirement in requirements:
        status = classify_condition_requirement(requirement, facts)
        buckets[status] = buckets.get(status, 0) + 1
        details.append({
            "key": str(requirement.get("key")),
            "required": str(requirement.get("required")),
            "classification": status,
        })
    # S5-15:历史来源条件原样保留(不改写为当前场景事实)
    source_conditions_preserved: list[dict] = []
    for record in reference_graph.get("provenance_manifest") or []:
        if record.get("source_conditions"):
            source_conditions_preserved.append({
                "provenance_id": str(record.get("provenance_id")),
                "source_conditions": record.get("source_conditions"),
            })
    return {
        "buckets": dict(sorted(buckets.items())),
        "details": sorted(details, key=lambda d: (
            d["key"], d["required"], d["classification"])),
        "condition_facts_consumed": sorted(
            {str(f.get("key")) for f in facts}),
        "source_conditions_preserved": source_conditions_preserved,
        "note": ("unknown 不计为冲突;满足不升级为全路径相容;"
                 "历史来源条件保留原文(S5-13/14/15)"),
    }


def check_endpoint_claims(endpoint_record: dict,
                          reference_annotations: list[dict]) -> dict:
    """终点/矿化声明检查(§9.6;消费 S4 四分账,分账独立不互推)。

    - ``search_stop_reason`` ≠ 终点:停止原因在场而评估却非 unknown
      且无证据 ⇒ ``stop_reason_mislabeled_as_endpoint``(S5-18);
    - 矿化声明须有根碳账核查范围 + 来源层直报证据
      (``mineralization_claim_without_root_carbon_account``,
      S5-17:仅提出 CO₂ 无根碳账不得判矿化);
    - ``metabolic_handoff`` ≠ 矿化(错叫 ⇒ 记误声明类型);
    - 上游 unresolved 依赖继承 ⇒ 末端不得升格为 supported_*
      (S5-19:recorded 不洗白);
    - 备选路线 CO₂ 不合并(``co2_aggregated`` 标记检查);
    - 模型推演不得声称已观察终点(``endpoint_evidence`` 空/模型
      来源 ⇒ ``observed_endpoint_claimed_from_model_only``)。
    """
    assessment = str(endpoint_record.get("chemical_endpoint_assessment")
                     or "unknown")
    stop_reason = str((endpoint_record.get("search_stop_reason") or {})
                      .get("primary") or "")
    evidence = endpoint_record.get("endpoint_evidence") or []
    bookkeeping = endpoint_record.get("bookkeeping") or {}
    inherited = endpoint_record.get("inherited_unresolved_dependencies") \
        or []
    misclaims: list[dict] = []
    if assessment != "unknown" and stop_reason in STOP_REASONS and \
            not evidence:
        misclaims.append({
            "type": "stop_reason_mislabeled_as_endpoint",
            "stop_reason": stop_reason,
            "assessment": assessment})
    if assessment == "supported_mineralization":
        root_scope = any(
            str((e or {}).get("root_carbon_fate_check_scope") or "")
            for e in evidence)
        if not root_scope or not evidence:
            misclaims.append({
                "type": "mineralization_claim_without_root_carbon_account",
                "note": "仅提出 CO₂、无根碳账与来源层终点证据 ⇒ 不得判"
                        "矿化(S5-17)"})
        if any(str((e or {}).get("evidence_basis") or "") ==
               "metabolic_handoff" for e in evidence):
            misclaims.append({
                "type": "metabolic_handoff_mislabeled_as_mineralization",
                "note": "metabolic_handoff 不等于矿化"})
    if assessment in ("supported_terminal_transformation_product",
                      "supported_mineralization") and inherited:
        unresolved = [d for d in inherited
                      if isinstance(d, dict) and str(
                          d.get("status") or "unresolved") == "unresolved"]
        if unresolved:
            misclaims.append({
                "type": "unresolved_dependency_promoted",
                "unresolved_count": len(unresolved),
                "note": "上游 unresolved 依赖继承到末端,不被 recorded "
                        "洗白(S5-19)"})
    if assessment in ("supported_terminal_transformation_product",
                      "supported_mineralization") and \
            all(str((e or {}).get("evidence_basis") or "")
                .startswith("model") for e in evidence) and evidence:
        misclaims.append({
            "type": "observed_endpoint_claimed_from_model_only",
            "note": "仅有模型推演不得声称已观察终点"})
    if bool(bookkeeping.get("co2_aggregated")):
        misclaims.append({
            "type": "co2_merged_across_alternative_routes",
            "note": "不同备选路线的 CO₂ 不得合并后声称同一路径矿化"})
    annotation_checks = []
    for annotation in reference_annotations or []:
        annotation_checks.append({
            "annotation_id": str(annotation.get("annotation_id")),
            "reference_assessment": str(
                annotation.get("endpoint_assessment")),
            "predicted_assessment": assessment,
            "agrees": str(annotation.get("endpoint_assessment"))
            == assessment,
        })
    return {
        "predicted_assessment": assessment,
        "search_stop_reason": stop_reason,
        "stop_endpoint_separated": (
            "search_stop_reason 与 chemical_endpoint_assessment 分账"
            "独立;停止原因永不映射为终点(S5-18)"),
        "misclaims": misclaims,
        "annotation_checks": sorted(
            annotation_checks, key=lambda a: a["annotation_id"]),
    }


def budget_omission_from_export(payload: dict) -> dict:
    """预算导致漏展开(§9.8;单独报告,不静默从分母删除,不计化学错误)。

    分桶:action_budget / depth_budget / product_expansion_width /
    per_parent_alternative_limit / retrieval_limit / model_request_
    limit / deferred_not_activated / blocked_objects / awaiting_
    prediction / other_explicit_stop。
    """
    stop_reason = str(((payload.get("endpoint_record") or {}).get(
        "search_stop_reason") or {}).get("primary") or "")
    buckets: dict[str, int] = {
        "action_budget": 1 if stop_reason == "budget_limit" else 0,
        "depth_budget": 1 if stop_reason == "depth_limit" else 0,
        "awaiting_prediction": 1 if stop_reason == "awaiting_prediction"
        else 0,
        "other_explicit_stop": 1 if stop_reason in (
            "no_local_candidate", "exhausted_search", "user_stop")
        else 0,
    }
    deferred = payload.get("deferred_entries") or []
    buckets["deferred_not_activated"] = len(deferred)
    buckets["blocked_objects"] = len(payload.get("blocked_entries") or [])
    budget = (payload.get("budget") or {}).get("budget_snapshot") or {}
    scoped = budget.get("scoped") or {}
    for scope_key, rows in sorted(scoped.items()):
        if not isinstance(rows, dict):
            continue
        for limit_key, info in sorted(rows.items()):
            if not isinstance(info, dict):
                continue
            if int(info.get("used") or 0) >= int(info.get("max") or 0) \
                    and int(info.get("max") or 0) >= 0 and \
                    str(scope_key) != "run_level":
                bucket = {
                    "max_product_expansion_width":
                        "product_expansion_width",
                    "max_alternative_hypotheses_per_parent":
                        "per_parent_alternative_limit",
                    "max_retrievals_per_parent": "retrieval_limit",
                    "max_attempts_per_hypothesis": "attempt_limit",
                }.get(str(limit_key), "scoped_limit_reached")
                buckets[bucket] = buckets.get(bucket, 0) + 1
    return {
        "buckets": dict(sorted(buckets.items())),
        "stop_reason": stop_reason,
        "deferred_entries": sorted(
            str(d.get("action_id")) for d in deferred),
        "note": ("预算漏展开单独报告;不计为模型化学错误,也不从科学"
                 "命中分母无声删除(分母定义 TBD 用户/teacher 裁定)"),
    }


def depth_metrics_from_export(payload: dict) -> dict:
    """按深度表现(§9.7:第 1/2/3+ 条反应边 + 超出深度预算未展开;
    样本量不足 ⇒ insufficient_sample,不合并成总分)。"""
    depths: dict[str, int] = {}
    unknown_depth_events: list[str] = []
    for report in payload.get("audit_production_reports") or []:
        body = report.get("production_payload") or {}
        submitted = body.get("submitted") or {}
        event_id = str(submitted.get("event_id") or "")
        if not event_id:
            continue
        depth = body.get("child_depth")
        if not isinstance(depth, int):
            unknown_depth_events.append(event_id)
            continue
        depths[event_id] = depth
    stop_reason = str(((payload.get("endpoint_record") or {}).get(
        "search_stop_reason") or {}).get("primary") or "")
    buckets = {
        "depth_1": sum(1 for d in depths.values() if d <= 1),
        "depth_2": sum(1 for d in depths.values() if d == 2),
        "depth_3_plus": sum(1 for d in depths.values() if d >= 3),
        "beyond_depth_budget": 1 if stop_reason == "depth_limit" else 0,
        "events_with_unknown_depth": len(unknown_depth_events),
    }
    insufficient = sorted(
        bucket for bucket, count in buckets.items() if count == 0)
    return {
        "buckets": dict(sorted(buckets.items())),
        "event_depths": dict(sorted(depths.items())),
        "insufficient_sample_buckets": insufficient,
        "note": ("样本量不足的桶标记 insufficient_sample,不合并成看似"
                 "稳定的总分;最低样本量 TBD 用户/teacher 裁定"),
    }


def unknown_partial_summary_from_export(payload: dict) -> dict:
    """unknown/partial/conditional 保留(§14.1/S5-16:不计 confirmed
    也不自动计错误)。"""
    conditional_events = 0
    unknown_checks = 0
    for report in payload.get("audit_production_reports") or []:
        body = report.get("production_payload") or {}
        admission = (body.get("admission") or {}).get("disposition") or ""
        if admission == "retain_conditional":
            conditional_events += 1
        audit = body.get("audit") or {}
        unknown_checks += sum(
            1 for check in audit.get("checks") or []
            if str(check.get("status")) == "unknown")
    unresolved_outcomes = sum(
        1 for outcome in payload.get("expansion_outcomes") or []
        if "unresolved" in str(
            (outcome.get("outcome_payload") or {}).get("outcome") or ""))
    return {
        "conditional_admission_events": conditional_events,
        "audit_unknown_checks": unknown_checks,
        "unresolved_outcomes": unresolved_outcomes,
        "note": ("unknown/partial/conditional 如实保留:不计 confirmed,"
                 "也不自动计为错误(S5-16);分母处理 TBD"),
    }


def outside_reference_edges_from_export(payload: dict,
                                         matched_event_ids: set[str]
                                         ) -> dict:
    """参考外未验证边(§9.4:拆分有依据/仅模型/无可审计依据)。"""
    buckets = {
        "outside_reference_with_allowed_inference_basis": 0,
        "outside_reference_model_only": 0,
        "outside_reference_no_auditable_basis": 0,
        "reference_coverage_indeterminate": 0,
    }
    events = payload.get("events") or []
    hypothesis_provenance = {}
    for row in payload.get("hypotheses") or []:
        body = row.get("payload")
        if isinstance(body, str):
            import json as _json
            try:
                body = _json.loads(body)
            except (ValueError, TypeError):
                body = {}
        hypothesis_provenance[str(row.get("hypothesis_id"))] = [
            str(x) for x in ((body or {}).get("provenance_refs")
                             or [])] + [
            str(x) for x in ((body or {}).get("support_group_refs")
                             or [])]
    audited_events = set()
    for report in payload.get("audit_production_reports") or []:
        body = report.get("production_payload") or {}
        event_id = str((body.get("submitted") or {}).get("event_id") or "")
        if event_id:
            audited_events.add(event_id)
    for event in events:
        event_id = str(event.get("event_id"))
        if event_id in matched_event_ids:
            continue
        refs = hypothesis_provenance.get(
            str(event.get("hypothesis_id")), [])
        if event_id not in audited_events:
            buckets["outside_reference_no_auditable_basis"] += 1
        elif refs:
            buckets["outside_reference_with_allowed_inference_basis"] += 1
        else:
            buckets["outside_reference_model_only"] += 1
    return {
        "buckets": buckets,
        "note": ("参考图可能不完备/unseen 轨道允许未见边:该指标不直接"
                 "等同错误率;参考覆盖不足无法判断的边在 coverage_report"
                 " 披露"),
    }


# ---------------------------------------------------------------- 评测主流程


def native_export_reader_from_ledger(ledger, run_dir: str | Path):
    """S4 公开入口消费契约(§3.1):返回导出条目读取器。

    读取器调用 ``read_native_export``(首消费:integrity → 版本门 →
    digest → 权威引用 → 策略 → staleness;fail-closed)。合成 run 的
    产物必须走真实链路生成,不得造假导出对象。
    """

    def reader(entry: dict) -> dict:
        return read_native_export(ledger, run_dir,
                                  str(entry.get("export_digest")))

    return reader


def _root_states_of_export(payload: dict) -> set[str]:
    """导出根状态(paths origin=root 的 product_state_ref)。"""
    roots: set[str] = set()
    for path in payload.get("paths") or []:
        if str(path.get("origin")) == "root":
            roots.add(str(path.get("product_state_ref") or ""))
    return roots


def _pair_exports_to_samples(graphs: dict[str, dict],
                             export_payloads: dict[str, dict]
                             ) -> dict[str, list[str]]:
    """样本 ↔ 导出配对(按根实体严格身份;确定性)。

    每个导出最多配到一个样本(根身份不同 ⇒ 不配);一个样本可配多
    个导出(同根多 run);配不到的导出到 coverage_report 披露。
    """
    pairing: dict[str, list[str]] = {graph_id: []
                                     for graph_id in sorted(graphs)}
    for digest, payload in sorted(export_payloads.items()):
        root_states = _root_states_of_export(payload)
        root_strict = set()
        states = _export_states(payload)
        for state_id in root_states:
            identity = states.get(state_id, {}).get("smiles_isomeric")
            if identity:
                root_strict.add(identity)
        for graph_id, graph in sorted(graphs.items()):
            root_entity = graph.get("root_entity") or {}
            try:
                ref_strict = strict_identity_of(
                    str(root_entity.get("structure_smiles_raw") or ""))
            except ChemicalStateError:
                ref_strict = str(
                    root_entity.get("strict_structure_identity") or "")
            if ref_strict in root_strict:
                pairing[graph_id].append(digest)
                break
    return pairing


_METRIC_SPECS = (
    ("reference_edge_recall", "S5-spec 9.1"),
    ("key_intermediate_recall", "S5-spec 9.2"),
    ("confirmed_error_rate", "S5-spec 9.3"),
    ("outside_reference_unverified_edges", "S5-spec 9.4"),
    ("environment_conflict_rate", "S5-spec 9.5"),
    ("endpoint_mineralization_misclaim_rate", "S5-spec 9.6"),
    ("depth_performance", "S5-spec 9.7"),
    ("budget_omission", "S5-spec 9.8"),
)


def _aggregate_metrics(domain: str, track: str, split: str,
                       sample_results: list[dict]) -> list[dict]:
    """按 §9.1–9.8 聚合接口指标(分轴桶 + 计数;分母/阈值 TBD;
    无科学通过线,无合并总分)。"""
    samples = [s for s in sample_results
               if s["scoring_status"] == "scored"]
    edge_buckets: dict[str, int] = {}
    for sample in samples:
        for entry in sample["predicted_edge_matches"]:
            status = entry["match_status"]
            edge_buckets[status] = edge_buckets.get(status, 0) + 1
    node_buckets: dict[str, int] = {}
    for sample in samples:
        for entry in sample["key_intermediate_matches"]:
            status = entry["match_status"]
            node_buckets[status] = node_buckets.get(status, 0) + 1
    outside_buckets: dict[str, int] = {}
    for sample in samples:
        for key, value in sorted(
                (sample["false_or_unverified_edges"] or {}).get(
                    "buckets", {}).items()):
            outside_buckets[key] = outside_buckets.get(key, 0) + value
    condition_buckets: dict[str, int] = {}
    for sample in samples:
        for key, value in sorted(
                sample["environment_conflicts"].get("buckets", {})
                .items()):
            condition_buckets[key] = condition_buckets.get(key, 0) + value
    misclaim_types: dict[str, int] = {}
    for sample in samples:
        for entry in (sample["endpoint_claim_checks"].get("misclaims")
                      or []) + (sample["mineralization_claim_checks"]
                                .get("misclaims") or []):
            misclaim_types[entry["type"]] = \
                misclaim_types.get(entry["type"], 0) + 1
    depth_buckets: dict[str, int] = {}
    for sample in samples:
        for key, value in sorted(
                sample["depth_metrics"].get("buckets", {}).items()):
            depth_buckets[key] = depth_buckets.get(key, 0) + value
    budget_buckets: dict[str, int] = {}
    for sample in samples:
        for key, value in sorted(
                (sample["budget_omission"] or {}).get("buckets", {})
                .items()):
            budget_buckets[key] = budget_buckets.get(key, 0) + value
    confirmed = sum(
        1 for sample in samples
        if sample["unknown_or_partial_summary"]
        ["conditional_admission_events"] == 0)
    metrics = [
        {"metric_id": "reference_edge_recall", "spec_ref": "S5-spec 9.1",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(edge_buckets.items())),
         "denominator_policy": "TBD_USER_TEACHER_DECISION",
         "status": "interface_only_synthetic",
         "note": ("严格反应边召回与结构身份/step scope/参考覆盖/预算"
                  "未展开分桶;分母与通过线 TBD")},
        {"metric_id": "key_intermediate_recall",
         "spec_ref": "S5-spec 9.2",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(node_buckets.items())),
         "key_intermediate_list_frozen": "TBD_USER_TEACHER_DECISION",
         "status": "interface_only_synthetic",
         "note": ("关键中间体清单须评测前冻结;不按预测结果动态决定;"
                  "严格身份与仅 CN 分轴;known/unseen 分轨")},
        {"metric_id": "confirmed_error_rate", "spec_ref": "S5-spec 9.3",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": {"confirmed_claim_events": confirmed,
                     **dict(sorted(misclaim_types.items()))},
         "independent_review_subset": "TBD_USER_TEACHER_DECISION",
         "coverage_policy": "TBD_USER_TEACHER_DECISION",
         "status": "interface_only_synthetic",
         "note": ("仅在有独立正负复核依据的子集上报告;unknown/partial/"
                  "conditional 不计 confirmed(本接口只数程序可见的"
                  "误声明类型;独立复核 TBD)")},
        {"metric_id": "outside_reference_unverified_edges",
         "spec_ref": "S5-spec 9.4",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(outside_buckets.items())),
         "status": "interface_only_synthetic",
         "note": ("不直接等同错误率:参考图可能不完备;unseen 轨道允许"
                  "未见边;参考覆盖不足另在 coverage_report 披露")},
        {"metric_id": "environment_conflict_rate",
         "spec_ref": "S5-spec 9.5",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(condition_buckets.items())),
         "status": "interface_only_synthetic",
         "note": ("essential 冲突/条件未知/覆盖不足/preference 不满足/"
                  "来源条件不可映射分桶;unknown 不计冲突,满足不升级"
                  "为全路径相容")},
        {"metric_id": "endpoint_mineralization_misclaim_rate",
         "spec_ref": "S5-spec 9.6",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(misclaim_types.items())),
         "endpoint_taxonomy": sorted(ENDPOINT_ASSESSMENTS),
         "status": "interface_only_synthetic",
         "note": ("终点分类沿用 S4 四分账;bookkeeping_status 不单独"
                  "提升为矿化结论;停止原因不是终点")},
        {"metric_id": "depth_performance", "spec_ref": "S5-spec 9.7",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(depth_buckets.items())),
         "insufficient_sample_policy": "TBD_USER_TEACHER_DECISION",
         "status": "interface_only_synthetic",
         "note": ("按第 1/2/3+ 条反应边分桶;样本量不足 ⇒ "
                  "insufficient_sample,不合并总分")},
        {"metric_id": "budget_omission", "spec_ref": "S5-spec 9.8",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(budget_buckets.items())),
         "status": "interface_only_synthetic",
         "note": ("预算漏展开单独报告;不计化学错误,不从分母无声删除;"
                  "是否作性能指标/限制项/单独门槛 TBD")},
    ]
    return metrics


def evaluate_scientific(
    evaluation_input: dict,
    *,
    reference_graphs: dict[str, dict] | None = None,
    native_export_reader=None,
    preregistration: dict | None = None,
) -> dict:
    """正式评测主流程(§11;确定性、可重放、零 LLM)。

    - 输入校验失败 ⇒ ``EvaluationContractError``(结构化,该评测不
      产出结果);
    - 泄漏检查失败 ⇒ 输出 ``status=blocked_leakage``,零聚合;
    - 导出缺席/读取失败 ⇒ 样本级 ``scoring_status`` 披露,不冒充
      已评(S5-28);
    - prereg TBD ⇒ ``pending_preregistration``(S5-23;评测器永不发
      evaluated_*)。
    """
    evaluation_input = validate_evaluation_input(evaluation_input)
    split_manifest = validate_split_manifest(
        evaluation_input.get("split_manifest"))
    domain = str(evaluation_input["domain"])
    track = str(evaluation_input["track"])
    interface_mode = bool(
        evaluation_input.get("interface_verification") or False)
    data_scope = str(evaluation_input.get("data_scope")
                     or "synthetic_rule_level")
    provider = evaluation_input.get("model_provider_policy") or {}
    provider_kind = str(provider.get("provider_kind") or "none")
    authorization = str(provider.get("authorization") or "")
    # ---- S5-26:real provider 无用户逐次授权 ⇒ 拒绝(零网络零费用) ----
    if provider_kind == "real" and not authorization:
        raise EvaluationContractError(
            "model_provider_policy.provider_kind=real 而无用户逐次授权"
            "(收费 provider 默认关闭:无授权时网络请求为零、费用为零,"
            "正式科学评测不启动)", {
                "kind": "provider_not_authorized",
                "provider_kind": provider_kind})
    # ---- 真实数据须已批准预注册(S5b 前另有授权,本批一律拒绝) ----
    prereg = preregistration or {}
    prereg_approved = str(
        prereg.get("approval_status") or "") == "approved"
    if data_scope == "real" and not prereg_approved:
        raise EvaluationContractError(
            "data_scope=real 而预注册未批准(真实数据评测属 S5b;须"
            "用户/teacher 完成题源/金标/样本量/阈值/预算裁定后另行"
            "启动)", {"kind": "real_data_requires_approved_preregistration",
                   "preregistration_id": str(
                       evaluation_input.get("preregistration_id"))})
    # ---- 参考图装载与身份核对(§11 第 4 步) ----
    graphs: dict[str, dict] = {}
    if reference_graphs is not None:
        for graph_id, graph in reference_graphs.items():
            validate_reference_graph(graph)
            graphs[str(graph_id)] = graph
    for entry in evaluation_input.get(
            "reference_graph_manifest") or []:
        graph_id = str(entry.get("reference_graph_id"))
        if graph_id in graphs:
            continue
        if entry.get("path"):
            graphs[graph_id] = load_reference_graph(entry["path"])
    manifest_sha_mismatches: list[dict] = []
    for entry in evaluation_input.get(
            "reference_graph_manifest") or []:
        graph_id = str(entry.get("reference_graph_id"))
        if graph_id in graphs:
            actual = reference_graph_sha256(graphs[graph_id])
            if actual != str(entry.get("sha256")):
                manifest_sha_mismatches.append({
                    "reference_graph_id": graph_id,
                    "declared": str(entry.get("sha256"))[:12],
                    "actual": actual[:12]})
    if manifest_sha_mismatches:
        raise EvaluationContractError(
            f"参考图 manifest sha256 与实际内容不符:"
            f"{manifest_sha_mismatches}(数据完整性阻断;不冒充已评)",
            {"kind": "reference_graph_identity_mismatch",
             "mismatches": manifest_sha_mismatches})
    missing_graphs = sorted({
        str(entry.get("reference_graph_id"))
        for entry in evaluation_input.get(
            "reference_graph_manifest") or []} - set(graphs))
    if missing_graphs:
        raise EvaluationContractError(
            f"参考图未提供且 manifest 无 path:{missing_graphs}"
            "(fail-closed;不猜默认)", {
                "kind": "reference_graph_missing",
                "missing": missing_graphs})
    # ---- 泄漏检查(§11 第 5 步) ----
    leakage = check_leakage(split_manifest, graphs)
    # ---- 导出装载(§11 第 3 步;S4 公开入口) ----
    export_payloads: dict[str, dict] = {}
    export_read_errors: list[dict] = []
    for entry in evaluation_input.get("native_path_exports") or []:
        digest = str(entry.get("export_digest"))
        if bool(entry.get("lossy_projection") or False):
            export_read_errors.append({
                "export_digest": digest,
                "kind": "lossy_projection_not_scorable",
                "note": ("v3 有损投影不得用于需要完整路径语义的科学"
                         "指标(§3.1);须消费原生导出")})
            continue
        if native_export_reader is None:
            continue  # 无读取通道 ⇒ 导出缺席(S5-28 pending 路径)
        try:
            read_back = native_export_reader(entry)
            export_payloads[digest] = read_back.get("payload") or {}
        except Exception as exc:  # noqa: BLE001 —— 结构化披露
            export_read_errors.append({
                "export_digest": digest,
                "kind": "native_export_unreadable",
                "error": f"{type(exc).__name__}: {exc}"[:200]})
    pairing = _pair_exports_to_samples(graphs, export_payloads)
    unmatched_exports = sorted(
        set(export_payloads) - {d for digests in pairing.values()
                                for d in digests})
    # ---- 样本级评分(§11 第 6–14 步) ----
    sample_results: list[dict] = []
    invalid_input_count = 0
    for entry in sorted(evaluation_input.get(
            "reference_graph_manifest") or [],
            key=lambda e: str(e.get("reference_graph_id"))):
        graph_id = str(entry.get("reference_graph_id"))
        graph = graphs[graph_id]
        root_entity = graph.get("root_entity") or {}
        sample_id = f"{domain}:{track}:{graph_id}"
        source_group_ids = sorted({
            str(g.get("source_group_id"))
            for g in graph.get("source_groups") or []})
        sample = {
            "sample_id": sample_id,
            "reference_graph_id": graph_id,
            "root_entity_id": str(root_entity.get("entity_id")),
            "source_group_ids": source_group_ids,
            "scoring_status": "scored",
            "scoring_errors": [],
            "predicted_node_matches": [],
            "predicted_edge_matches": [],
            "key_intermediate_matches": [],
            "false_or_unverified_edges": {},
            "environment_conflicts": {},
            "endpoint_claim_checks": {},
            "mineralization_claim_checks": {},
            "depth_metrics": {},
            "budget_omission": {},
            "unknown_or_partial_summary": {},
        }
        digests = pairing.get(graph_id) or []
        if not digests:
            sample["scoring_status"] = "not_evaluated_export_missing"
            sample["scoring_errors"] = [{
                "kind": "native_export_missing",
                "note": ("S4 native export 未交付 ⇒ 可验证接口,不运行"
                         "正式科学评测,状态 pending(S5-28)")}]
            invalid_input_count += 1
            sample_results.append(sample)
            continue
        payload = export_payloads[digests[0]]
        node_matches = match_reference_nodes(graph, payload)
        edge_matches = match_reference_edges(graph, payload,
                                             node_matches)
        conditions = classify_sample_conditions(graph, payload)
        endpoint_checks = check_endpoint_claims(
            payload.get("endpoint_record") or {},
            graph.get("endpoint_annotations") or [])
        depth = depth_metrics_from_export(payload)
        budget = budget_omission_from_export(payload)
        unknown_partial = unknown_partial_summary_from_export(payload)
        matched_event_ids = {
            event_id for entry in edge_matches
            for event in entry["matched_events"]
            for event_id in [event["event_id"]]}
        outside = outside_reference_edges_from_export(
            payload, matched_event_ids)
        if any(entry["match_status"] ==
               "reference_structure_unparseable"
               for entry in node_matches):
            sample["scoring_status"] = "invalid_input"
            sample["scoring_errors"] = [{
                "kind": "reference_structure_unparseable",
                "note": "参考结构不可解析 ⇒ 停止该样本评测(不静默删)"}]
            invalid_input_count += 1
        sample["predicted_node_matches"] = node_matches
        sample["predicted_edge_matches"] = edge_matches
        sample["key_intermediate_matches"] = [
            entry for entry in node_matches
            if entry["role"] == "intermediate"]
        sample["false_or_unverified_edges"] = outside
        sample["environment_conflicts"] = conditions
        sample["endpoint_claim_checks"] = endpoint_checks
        sample["mineralization_claim_checks"] = {
            "misclaims": [m for m in endpoint_checks["misclaims"]
                          if "mineralization" in m["type"]
                          or "co2" in m["type"]],
            "predicted_assessment": endpoint_checks[
                "predicted_assessment"],
            "note": ("矿化证据最低口径:根碳账核查范围 + 来源层直报;"
                     "仅 CO₂ 产物/仅模型推演/bookkeeping 皆不构成矿化"
                     "结论"),
        }
        sample["depth_metrics"] = depth
        sample["budget_omission"] = budget
        sample["unknown_or_partial_summary"] = unknown_partial
        sample_results.append(sample)
    # ---- 聚合(§11 第 15 步;分层 TBD 时按 split 单层聚合) ----
    aggregates: list[dict] = []
    if leakage["status"] != "failed":
        split_of = {}
        for assignment in split_manifest.get("assignments") or []:
            split_of[str(assignment.get("reference_graph_id"))] = \
                str(assignment.get("split"))
        default_split = "development"
        for split in sorted(set(split_of.values()) or {default_split}):
            split_samples = [
                s for s in sample_results
                if split_of.get(s["reference_graph_id"], default_split)
                == split]
            aggregates.extend(_aggregate_metrics(
                domain, track, split, split_samples))
    # ---- 覆盖/缺失报告(§11 第 16–17 步) ----
    coverage_report = {
        "reference_graphs": sorted(graphs),
        "not_evaluable_edges_per_graph": {
            str(g): sorted((graphs[g].get("coverage_statement")
                            or {}).get("not_evaluable_edge_ids") or [])
            for g in sorted(graphs)},
        "known_gaps_per_graph": {
            str(g): sorted((graphs[g].get("coverage_statement")
                            or {}).get("known_gaps") or [])
            for g in sorted(graphs)},
        "unmatched_exports": unmatched_exports,
        "note": ("未画出的参考边不自动判模型错误,计入参考覆盖限制"
                 "(S5-09);参考图不完备时如实披露覆盖范围"),
    }
    missingness_report = {
        "unknown_partial_summary_per_sample": {
            s["sample_id"]: s["unknown_or_partial_summary"]
            for s in sample_results
            if s["scoring_status"] == "scored"},
        "condition_unknown_note": ("条件未知/覆盖不足与冲突分桶;"
                                   "未知不计冲突"),
        "note": ("unknown/partial/conditional 保留;不用全面拒绝换通过"
                 "(§18 第 16 条)"),
    }
    network_requests = sum(
        int(row.get("network_request_count") or 0)
        for payload in export_payloads.values()
        for row in payload.get("model_requests") or [])
    # ---- 状态裁定(§12;程序永不发 evaluated_*) ----
    if leakage["status"] == "failed":
        status = "blocked_leakage"
    elif not export_payloads or all(s["scoring_status"] != "scored"
                                    for s in sample_results):
        # S5-28:S4 导出未交付/全部样本不可评 ⇒ 可验证接口,不运行
        # 正式科学评测,状态 pending(优先于接口验证模式)
        status = "pending_no_independent_data"
    elif interface_mode:
        status = "interface_verified_only"
    elif not prereg or str(prereg.get("approval_status") or "").startswith(
            "pending"):
        status = "pending_preregistration"
    else:
        status = "pending_user_teacher_decision"
    if status not in EMITTED_STATUSES:  # pragma: no cover —— 防御
        raise EvaluationContractError(
            f"状态裁定越界:{status}(评测器永不生成 evaluated_*;"
            "最终科学状态由用户/teacher 按预注册裁定)",
            {"kind": "evaluation_status_out_of_range",
             "status": status})
    output = {
        "evaluator_schema_version": PPV1_EVALUATION_VERSION,
        "evaluation_id": content_hash({
            "run_identity": evaluation_input.get("run_identity"),
            "reference_graph_manifest": evaluation_input.get(
                "reference_graph_manifest"),
            "split_manifest_id": split_manifest.get(
                "split_manifest_id"),
            "domain": domain, "track": track,
            "preregistration_id": evaluation_input.get(
                "preregistration_id"),
        }),
        "run_identity": evaluation_input.get("run_identity"),
        "domain": domain,
        "track": track,
        "split": {str(a.get("reference_graph_id")):
                  str(a.get("split"))
                  for a in sorted(
                      split_manifest.get("assignments") or [],
                      key=lambda a: str(a.get("reference_graph_id")))},
        "sample_results": sample_results,
        "aggregate_metrics": aggregates,
        "uncertainty_intervals": [{
            "method": "TBD_USER_TEACHER_DECISION",
            "status": "pending_preregistration",
            "note": ("置信区间方法/多重比较处理 TBD;接口仅预留分轴"
                     "结构,不产出区间数值")}],
        "coverage_report": coverage_report,
        "missingness_report": missingness_report,
        "budget_omission_report": {
            "per_sample": {s["sample_id"]: s["budget_omission"]
                           for s in sample_results},
            "note": ("预算漏展开单独报告,不静默从分母删除"
                     "(S5-20/§9.8)")},
        "leakage_checks": leakage,
        "invalid_input_count": invalid_input_count,
        "export_read_errors": export_read_errors,
        "scoring_provenance": {
            "evaluator_version": PPV1_EVALUATION_VERSION,
            "split_manifest_version": PPV1_SPLIT_MANIFEST_VERSION,
            "reference_graph_sha256s": {
                str(entry.get("reference_graph_id")):
                    str(entry.get("sha256"))
                for entry in sorted(
                    evaluation_input.get(
                        "reference_graph_manifest") or [],
                    key=lambda e: str(e.get("reference_graph_id")))},
            "split_manifest_sha256": content_hash(split_manifest),
            "preregistration_sha256": (
                content_hash(prereg) if prereg else ""),
            "llm_in_scoring": False,
            "network_request_count": network_requests,
            "provider_kind": provider_kind,
            "cost": 0,
            "consumed_field_policy": (
                "仅消费冻结结构化字段清单;自然语言字段不进判定"
                "(S5-25)"),
            "data_scope": data_scope,
            "scientific_metric_status": (
                "interface_only:合成规则级数字不外推 dev/298,不构成"
                "科学性能声明(§5.1 题域标签/§12 状态语义)"),
        },
        "status": status,
    }
    output["output_sha256"] = hashlib.sha256(
        canonical_json(output).encode("utf-8")).hexdigest()
    return output


# ------------------------------------------------------- 输出落盘与金标守卫


def persist_evaluation_output(output: dict, target: str | Path, *,
                              contains_gold: bool = False,
                              repo_root: str | Path | None = None
                              ) -> dict:
    """评测输出落盘(S5-27:含金标产物只能进授权 gitignored 根)。

    ``contains_gold``:输出是否嵌入参考图/金标内容(真实评测时由
    调用方如实标注)。授权根镜像 .gitignore 的金标隔离目录;普通
    目录(含仓内非 gitignored 路径)写入拒绝。
    """
    target = Path(target)
    text = canonical_json(output) + "\n"
    if contains_gold:
        rel = None
        if repo_root is not None:
            root = Path(repo_root).resolve()
            resolved = target.resolve()
            try:
                rel = resolved.relative_to(root).as_posix()
            except ValueError:
                rel = None
        if rel is None:
            rel = target.as_posix().lstrip("/")
        authorized = any(
            rel == root or rel.startswith(root + "/")
            for root in sorted(GOLD_AUTHORIZED_ROOTS))
        if not authorized:
            raise EvaluationContractError(
                f"含金标的评测产物只能写入授权 gitignored 目录:"
                f"{target}(授权根 {sorted(GOLD_AUTHORIZED_ROOTS)};"
                "普通目录写入拒绝,S5-27)", {
                    "kind": "gold_content_unauthorized_path",
                    "target": str(target),
                    "authorized_roots": sorted(
                        GOLD_AUTHORIZED_ROOTS)})
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return {"path": str(target),
            "sha256": hashlib.sha256(
                text.encode("utf-8")).hexdigest()}
