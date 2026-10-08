"""S5a 参考图 schema(ppv1-reference-graph-1;S5 任务书 §7 全字段)。

参考图是 S5 科学评测的**权威输入**,不是模型输出,也不能由评测程序
根据模型结果反向生成(§7)。本模块只做**确定性 schema 校验**:

- §7.1 顶层字段(全部必填;未知顶层键 fail-closed 拒绝,不静默忽略);
- §7.2 根对象(严格结构身份缺失 ⇒ 必须显式声明 identity_scope 有限
  范围 + 缺失结构维度 + 指标使用范围;该样本不得被当作严格结构确证);
- §7.3 节点(node_status/role 枚举;**distinct occurrence**:同一分子
  不同来路/场景/研究来源必须保留 distinct occurrence_id,不按 CN 或
  结构首现合并 —— 校验拒绝重复 (node_id) 与重复 (structure 身份 +
  occurrence_id),但同一结构不同 occurrence_id 合法保留);
- §7.4 边(step_scope/participant_list_status/edge_status 枚举;
  共同产物/备选反应/多步汇总边按字段显式区分,不互相冒充);
- §7.5 条件与来源(ConditionScope 状态枚举;ProvenanceRecord 的
  source_origin 与 evidence_basis 分开保存,recorded 只能表示库中有
  记录,不自动升格为实测);
- endpoint_annotations(终点注记:只允许 S4 四分账枚举,矿化证据
  最低口径字段须存在 —— 证据内容本身属用户/teacher 裁定,本模块
  只核字段存在与枚举合法);
- source_groups(研究来源组独立性边界;同一研究多数据库记录归并
  为一组,independence unknown 不计独立支持);
- split_assignment(划分归属;unseen 轨道必须携带排除声明引用);
- coverage_statement(覆盖声明:参考图不完备处如实标注,未画出的边
  不能自动判模型错误);
- provenance_manifest / creation_review(合成规则级样本标
  synthetic_rule_level;真实评审状态属用户/teacher)。

校验失败 ⇒ ReferenceGraphContractError(结构化 kind + 字段路径;
fail-closed,不静默删字段、不自动补全)。本模块零 LLM、零网络、
零数据库写入;不读取任何真实科学数据/金标/题面(S5a 边界)。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..domain.models import canonical_json
from .profile import PPV1_REFERENCE_GRAPH_VERSION

# ---- 枚举(S5 任务书 §5/§7;取值域 fail-closed) ----

DOMAINS = frozenset({"dev", "298"})
TRACKS = frozenset({"known_evidence_reconstruction",
                    "unseen_path_inference"})
SPLITS = frozenset({"development", "tuning", "held_out",
                    "independent_confirmation"})
NODE_ROLES = frozenset({"root", "intermediate", "principal_product",
                        "coproduct", "terminal_product", "unknown"})
NODE_STATUSES = frozenset({"observed", "inferred_from_source",
                           "reference_only", "unknown"})
IDENTITY_SCOPES = frozenset({"strict_structure", "cn_only", "partial",
                             "unknown"})
PARTICIPANT_LIST_STATUSES = frozenset({"source_complete",
                                       "declared_complete", "partial",
                                       "unknown"})
STEP_SCOPES = frozenset({"net_reaction", "elementary_step",
                         "multistep_summary", "unknown"})
EDGE_STATUSES = frozenset({"observed", "supported_inference",
                           "reference_only", "unknown"})
CONDITION_STATUSES = frozenset({"known_present", "known_absent",
                                "unknown"})
REQUIREMENT_LEVELS = frozenset({"essential", "preference"})
INDEPENDENCE_STATUSES = frozenset({"independent", "related", "unknown"})
ENDPOINT_ASSESSMENTS = frozenset({"unknown", "metabolic_handoff",
                                  "supported_terminal_transformation_"
                                  "product", "supported_mineralization"})
CREATION_REVIEW_STATUSES = frozenset({"synthetic_rule_level",
                                      "pending_user_teacher_review",
                                      "reviewed"})

# 矿化证据最低口径字段(endpoint annotation 声明 supported_mineralization
# 时必须存在;§7/§9.6 —— 只核存在,不评内容,内容口径属用户/teacher)
MINERALIZATION_EVIDENCE_FIELDS = (
    "root_carbon_fate_check_scope",
    "observation_scope",
    "source_refs",
)

_TOP_LEVEL_FIELDS = (
    "schema_version", "reference_graph_id", "domain", "track",
    "root_entity", "nodes", "edges", "endpoint_annotations",
    "source_groups", "split_assignment", "coverage_statement",
    "provenance_manifest", "creation_review",
)
_ROOT_ENTITY_FIELDS = (
    "entity_id", "structure_smiles_raw", "strict_structure_identity",
    "formal_charge", "stereo_information_status",
    "isotope_information_status", "source_refs",
)
_NODE_FIELDS = (
    "node_id", "state_identity", "structure_smiles",
    "structure_identity_scope", "role", "occurrence_id",
    "source_group_refs", "condition_scope", "provenance_refs",
    "node_status",
)
_EDGE_FIELDS = (
    "edge_id", "from_node_ids", "to_node_ids", "transformation_ref",
    "transformation_signature_status", "participants",
    "participant_list_status", "coefficient_status", "step_scope",
    "condition_requirements", "scenario_scope", "provenance_refs",
    "source_group_refs", "evidence_basis", "edge_status",
)
_PROVENANCE_FIELDS = (
    "provenance_id", "source_group_id", "source_origin",
    "evidence_basis", "citation_ref", "structure_match_scope",
    "observation_scope", "source_conditions", "independent_status",
)


class ReferenceGraphContractError(RuntimeError):
    """参考图契约违反(结构化 fail-closed;零写入)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _req_str(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReferenceGraphContractError(
            f"参考图字段 {field} 必须是非空字符串(缺字段/空值 fail-closed,"
            "不自动补全)", {"kind": "reference_graph_field_invalid",
                         "field": field, "value_type":
                         type(value).__name__})
    return value


def _req_enum(value, field: str, allowed: frozenset) -> str:
    _req_str(value, field)
    if value not in allowed:
        raise ReferenceGraphContractError(
            f"参考图字段 {field} 取值非法:{value!r}(允许 "
            f"{sorted(allowed)};fail-closed)", {
                "kind": "reference_graph_enum_invalid",
                "field": field, "value": value,
                "allowed": sorted(allowed)})
    return value


def _req_str_list(value, field: str) -> list[str]:
    if not isinstance(value, list) or any(
            not isinstance(x, str) or not x for x in value):
        raise ReferenceGraphContractError(
            f"参考图字段 {field} 必须是字符串列表", {
                "kind": "reference_graph_field_invalid",
                "field": field, "value_type": type(value).__name__})
    return list(value)


def _validate_condition_scope(cond: dict, field: str) -> None:
    if not isinstance(cond, dict):
        raise ReferenceGraphContractError(
            f"{field} 必须是对象(ConditionScope)", {
                "kind": "reference_graph_field_invalid",
                "field": field,
                "value_type": type(cond).__name__})
    _req_str(cond.get("key"), f"{field}.key")
    if "value_or_interval" not in cond:
        raise ReferenceGraphContractError(
            f"{field}.value_or_interval 缺失(条件值/区间必须显式;"
            "不静默补默认)", {"kind": "reference_graph_field_missing",
                          "field": f"{field}.value_or_interval"})
    _req_enum(cond.get("status"), f"{field}.status", CONDITION_STATUSES)
    _req_enum(cond.get("required"), f"{field}.required",
              REQUIREMENT_LEVELS)
    for key in ("key", "value_or_interval", "unit", "status", "required",
                "subject_scenario_ref"):
        if key not in cond:
            raise ReferenceGraphContractError(
                f"{field}.{key} 缺失(ConditionScope 必须完整声明)",
                {"kind": "reference_graph_field_missing",
                 "field": f"{field}.{key}"})
    _req_str_list(cond.get("source_refs", []), f"{field}.source_refs")


def validate_reference_graph(graph: dict) -> dict:
    """校验参考图(§7 全字段;确定性,fail-closed;返回原 dict)。

    缺字段明确失败、未知枚举拒绝、交叉引用(node/edge/provenance/
    source group)断裂拒绝;同一结构 distinct occurrence 保留(重复
    (结构,occurrence_id) 拒绝,同结构不同 occurrence 合法)。
    """
    if not isinstance(graph, dict):
        raise ReferenceGraphContractError(
            "参考图必须是对象", {"kind": "reference_graph_not_object",
                             "value_type": type(graph).__name__})
    unknown_top = sorted(set(graph) - set(_TOP_LEVEL_FIELDS))
    if unknown_top:
        raise ReferenceGraphContractError(
            f"参考图含未知顶层字段:{unknown_top}(允许 "
            f"{list(_TOP_LEVEL_FIELDS)};fail-closed 不静默忽略)", {
                "kind": "reference_graph_unknown_field",
                "fields": unknown_top})
    if str(graph.get("schema_version") or "") != \
            PPV1_REFERENCE_GRAPH_VERSION:
        raise ReferenceGraphContractError(
            f"参考图 schema 版本未知:{graph.get('schema_version')!r}"
            f"(当前 {PPV1_REFERENCE_GRAPH_VERSION};fail-closed 不猜迁移)",
            {"kind": "reference_graph_version_unknown",
             "schema_version": str(graph.get("schema_version") or "")})
    graph_id = _req_str(graph.get("reference_graph_id"),
                        "reference_graph_id")
    _req_enum(graph.get("domain"), "domain", DOMAINS)
    _req_enum(graph.get("track"), "track", TRACKS)

    # ---- §7.2 根对象 ----
    root = graph.get("root_entity")
    if not isinstance(root, dict):
        raise ReferenceGraphContractError(
            "root_entity 必须是对象", {"kind":
                                     "reference_graph_field_invalid",
                                     "field": "root_entity"})
    unknown_root = sorted(set(root) - set(_ROOT_ENTITY_FIELDS)
                           - {"identity_scope",
                              "missing_structure_dimensions",
                              "metric_scope_note"})
    if unknown_root:
        raise ReferenceGraphContractError(
            f"root_entity 含未知字段:{unknown_root}", {
                "kind": "reference_graph_unknown_field",
                "field": "root_entity", "fields": unknown_root})
    for field in _ROOT_ENTITY_FIELDS:
        if field not in root:
            raise ReferenceGraphContractError(
                f"root_entity.{field} 缺失(§7.2 全字段必填)",
                {"kind": "reference_graph_field_missing",
                 "field": f"root_entity.{field}"})
    _req_str(root.get("entity_id"), "root_entity.entity_id")
    _req_str(root.get("structure_smiles_raw"),
             "root_entity.structure_smiles_raw")
    if not isinstance(root.get("formal_charge"), int) and \
            root.get("formal_charge") is not None:
        raise ReferenceGraphContractError(
            "root_entity.formal_charge 必须是整数或 null", {
                "kind": "reference_graph_field_invalid",
                "field": "root_entity.formal_charge"})
    _req_str(root.get("stereo_information_status"),
             "root_entity.stereo_information_status")
    _req_str(root.get("isotope_information_status"),
             "root_entity.isotope_information_status")
    _req_str_list(root.get("source_refs"), "root_entity.source_refs")
    strict_identity = str(root.get("strict_structure_identity") or "")
    if not strict_identity:
        # §7.2:缺少完整结构必须显式声明有限范围 + 缺失维度 + 指标范围
        scope = root.get("identity_scope")
        if scope not in IDENTITY_SCOPES - {"strict_structure"}:
            raise ReferenceGraphContractError(
                "root_entity.strict_structure_identity 为空时必须显式声明"
                " identity_scope 有限范围(cn_only/partial/unknown)—— "
                "该样本不得被当作严格结构确证", {
                    "kind": "reference_graph_identity_scope_missing",
                    "field": "root_entity.identity_scope",
                    "graph_id": graph_id})
        missing_dims = _req_str_list(
            root.get("missing_structure_dimensions"),
            "root_entity.missing_structure_dimensions")
        if not missing_dims:
            raise ReferenceGraphContractError(
                "root_entity 有限结构范围必须声明缺失的结构维度"
                "(missing_structure_dimensions 非空)", {
                    "kind": "reference_graph_field_invalid",
                    "field": "root_entity.missing_structure_dimensions"})
        _req_str(root.get("metric_scope_note"),
                 "root_entity.metric_scope_note")

    # ---- §7.3 节点(distinct occurrence 保留) ----
    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ReferenceGraphContractError(
            "nodes 必须是非空列表(参考图至少声明根节点)", {
                "kind": "reference_graph_field_invalid",
                "field": "nodes"})
    node_ids: set[str] = set()
    occurrence_keys: set[tuple[str, str]] = set()
    for i, node in enumerate(nodes):
        field = f"nodes[{i}]"
        if not isinstance(node, dict):
            raise ReferenceGraphContractError(
                f"{field} 必须是对象", {"kind":
                                      "reference_graph_field_invalid",
                                      "field": field})
        unknown_keys = sorted(
            set(node) - set(_NODE_FIELDS) - {"structure_identity"})
        if unknown_keys:
            raise ReferenceGraphContractError(
                f"{field} 含未知字段:{unknown_keys}", {
                    "kind": "reference_graph_unknown_field",
                    "field": field, "fields": unknown_keys})
        for key in _NODE_FIELDS:
            if key not in node:
                raise ReferenceGraphContractError(
                    f"{field}.{key} 缺失(§7.3 全字段必填)", {
                        "kind": "reference_graph_field_missing",
                        "field": f"{field}.{key}"})
        node_id = _req_str(node.get("node_id"), f"{field}.node_id")
        if node_id in node_ids:
            raise ReferenceGraphContractError(
                f"节点 ID 重复:{node_id}", {
                    "kind": "reference_graph_duplicate_node_id",
                    "node_id": node_id})
        node_ids.add(node_id)
        _req_str(node.get("state_identity"), f"{field}.state_identity")
        _req_str(node.get("structure_smiles"), f"{field}.structure_smiles")
        _req_enum(node.get("structure_identity_scope"),
                  f"{field}.structure_identity_scope", IDENTITY_SCOPES)
        _req_enum(node.get("role"), f"{field}.role", NODE_ROLES)
        occurrence_id = _req_str(node.get("occurrence_id"),
                                 f"{field}.occurrence_id")
        occurrence_key = (str(node.get("state_identity")), occurrence_id)
        if occurrence_key in occurrence_keys:
            raise ReferenceGraphContractError(
                f"重复 occurrence:{occurrence_key}(同一结构同一 occurrence_"
                "id 只能声明一次;不同来路必须 distinct occurrence)", {
                    "kind": "reference_graph_duplicate_occurrence",
                    "state_identity": occurrence_key[0],
                    "occurrence_id": occurrence_id})
        occurrence_keys.add(occurrence_key)
        _req_str_list(node.get("source_group_refs"),
                      f"{field}.source_group_refs")
        _req_str_list(node.get("provenance_refs"),
                      f"{field}.provenance_refs")
        _req_enum(node.get("node_status"), f"{field}.node_status",
                  NODE_STATUSES)
        if not isinstance(node.get("condition_scope"), list):
            raise ReferenceGraphContractError(
                f"{field}.condition_scope 必须是列表", {
                    "kind": "reference_graph_field_invalid",
                    "field": f"{field}.condition_scope"})
        for j, cond in enumerate(node.get("condition_scope") or []):
            _validate_condition_scope(
                cond, f"{field}.condition_scope[{j}]")

    # ---- §7.4 边(备选/共同产物/多步汇总按字段显式区分) ----
    edges = graph.get("edges")
    if not isinstance(edges, list):
        raise ReferenceGraphContractError(
            "edges 必须是列表", {"kind": "reference_graph_field_invalid",
                              "field": "edges"})
    edge_ids: set[str] = set()
    for i, edge in enumerate(edges):
        field = f"edges[{i}]"
        if not isinstance(edge, dict):
            raise ReferenceGraphContractError(
                f"{field} 必须是对象", {"kind":
                                      "reference_graph_field_invalid",
                                      "field": field})
        unknown_keys = sorted(set(edge) - set(_EDGE_FIELDS))
        if unknown_keys:
            raise ReferenceGraphContractError(
                f"{field} 含未知字段:{unknown_keys}", {
                    "kind": "reference_graph_unknown_field",
                    "field": field, "fields": unknown_keys})
        for key in _EDGE_FIELDS:
            if key not in edge:
                raise ReferenceGraphContractError(
                    f"{field}.{key} 缺失(§7.4 全字段必填)", {
                        "kind": "reference_graph_field_missing",
                        "field": f"{field}.{key}"})
        edge_id = _req_str(edge.get("edge_id"), f"{field}.edge_id")
        if edge_id in edge_ids:
            raise ReferenceGraphContractError(
                f"边 ID 重复:{edge_id}", {
                    "kind": "reference_graph_duplicate_edge_id",
                    "edge_id": edge_id})
        edge_ids.add(edge_id)
        for side in ("from_node_ids", "to_node_ids"):
            ids = _req_str_list(edge.get(side), f"{field}.{side}")
            if side == "to_node_ids" and not ids:
                raise ReferenceGraphContractError(
                    f"{field}.to_node_ids 不能为空(反应边必须声明产物"
                    "侧参与节点)", {
                        "kind": "reference_graph_field_invalid",
                        "field": f"{field}.{side}"})
            for ref in ids:
                if ref not in node_ids:
                    raise ReferenceGraphContractError(
                        f"{field}.{side} 引用未声明节点:{ref}"
                        "(交叉引用断裂 fail-closed)", {
                            "kind": "reference_graph_dangling_ref",
                            "field": f"{field}.{side}", "ref": ref})
        _req_str(edge.get("transformation_ref"),
                 f"{field}.transformation_ref")
        _req_str(edge.get("transformation_signature_status"),
                 f"{field}.transformation_signature_status")
        _req_enum(edge.get("participant_list_status"),
                  f"{field}.participant_list_status",
                  PARTICIPANT_LIST_STATUSES)
        _req_str(edge.get("coefficient_status"),
                 f"{field}.coefficient_status")
        _req_enum(edge.get("step_scope"), f"{field}.step_scope",
                  STEP_SCOPES)
        _req_str(edge.get("scenario_scope"), f"{field}.scenario_scope")
        _req_str(edge.get("evidence_basis"), f"{field}.evidence_basis")
        _req_enum(edge.get("edge_status"), f"{field}.edge_status",
                  EDGE_STATUSES)
        _req_str_list(edge.get("provenance_refs"),
                      f"{field}.provenance_refs")
        _req_str_list(edge.get("source_group_refs"),
                      f"{field}.source_group_refs")
        participants = edge.get("participants")
        if not isinstance(participants, list) or not participants:
            raise ReferenceGraphContractError(
                f"{field}.participants 必须是非空列表(参与物/角色/系数"
                "完整;共同产物/主产物按 role 区分)", {
                    "kind": "reference_graph_field_invalid",
                    "field": f"{field}.participants"})
        for j, participant in enumerate(participants):
            pfield = f"{field}.participants[{j}]"
            if not isinstance(participant, dict) or \
                    not participant.get("node_id"):
                raise ReferenceGraphContractError(
                    f"{pfield} 必须含 node_id(参与物引用节点)", {
                        "kind": "reference_graph_field_invalid",
                        "field": pfield})
            if str(participant["node_id"]) not in node_ids:
                raise ReferenceGraphContractError(
                    f"{pfield}.node_id 引用未声明节点", {
                        "kind": "reference_graph_dangling_ref",
                        "field": pfield,
                        "ref": str(participant["node_id"])})
            for key in ("node_id", "side", "role", "coefficient",
                        "coefficient_status"):
                if key not in participant:
                    raise ReferenceGraphContractError(
                        f"{pfield}.{key} 缺失", {
                            "kind": "reference_graph_field_missing",
                            "field": f"{pfield}.{key}"})
            _req_str(participant.get("side"), f"{pfield}.side")
            _req_str(participant.get("role"), f"{pfield}.role")
            _req_str(participant.get("coefficient_status"),
                     f"{pfield}.coefficient_status")
        if not isinstance(edge.get("condition_requirements"), list):
            raise ReferenceGraphContractError(
                f"{field}.condition_requirements 必须是列表", {
                    "kind": "reference_graph_field_invalid",
                    "field": f"{field}.condition_requirements"})
        for j, cond in enumerate(edge.get("condition_requirements") or []):
            _validate_condition_scope(
                cond, f"{field}.condition_requirements[{j}]")

    # ---- source_groups(研究来源组;同研究多记录归并一组) ----
    groups = graph.get("source_groups")
    if not isinstance(groups, list):
        raise ReferenceGraphContractError(
            "source_groups 必须是列表", {
                "kind": "reference_graph_field_invalid",
                "field": "source_groups"})
    group_ids: set[str] = set()
    for i, group in enumerate(groups):
        field = f"source_groups[{i}]"
        if not isinstance(group, dict):
            raise ReferenceGraphContractError(
                f"{field} 必须是对象", {
                    "kind": "reference_graph_field_invalid",
                    "field": field})
        for key in ("source_group_id", "independence_status",
                    "member_records", "note"):
            if key not in group:
                raise ReferenceGraphContractError(
                    f"{field}.{key} 缺失", {
                        "kind": "reference_graph_field_missing",
                        "field": f"{field}.{key}"})
        group_id = _req_str(group.get("source_group_id"),
                            f"{field}.source_group_id")
        if group_id in group_ids:
            raise ReferenceGraphContractError(
                f"来源组 ID 重复:{group_id}", {
                    "kind": "reference_graph_duplicate_source_group",
                    "source_group_id": group_id})
        group_ids.add(group_id)
        _req_enum(group.get("independence_status"),
                  f"{field}.independence_status", INDEPENDENCE_STATUSES)
        _req_str_list(group.get("member_records"),
                      f"{field}.member_records")
        _req_str(group.get("note"), f"{field}.note")
    referenced_groups = set()
    for node in nodes:
        referenced_groups.update(node.get("source_group_refs") or [])
    for edge in edges:
        referenced_groups.update(edge.get("source_group_refs") or [])
    dangling_groups = sorted(referenced_groups - group_ids)
    if dangling_groups:
        raise ReferenceGraphContractError(
            f"节点/边引用未声明的来源组:{dangling_groups}", {
                "kind": "reference_graph_dangling_ref",
                "refs": dangling_groups})

    # ---- split_assignment(§6.3 划分归属;unseen 轨道须带排除声明) ----
    split_assignment = graph.get("split_assignment")
    if not isinstance(split_assignment, dict):
        raise ReferenceGraphContractError(
            "split_assignment 必须是对象", {
                "kind": "reference_graph_field_invalid",
                "field": "split_assignment"})
    for key in ("split", "split_rule_version", "route_group_keys"):
        if key not in split_assignment:
            raise ReferenceGraphContractError(
                f"split_assignment.{key} 缺失", {
                    "kind": "reference_graph_field_missing",
                    "field": f"split_assignment.{key}"})
    _req_enum(split_assignment.get("split"), "split_assignment.split",
              SPLITS)
    _req_str(split_assignment.get("split_rule_version"),
             "split_assignment.split_rule_version")
    _req_str_list(split_assignment.get("route_group_keys"),
                  "split_assignment.route_group_keys")
    if graph.get("track") == "unseen_path_inference":
        _req_str(split_assignment.get("unseen_exclusion_ref"),
                 "split_assignment.unseen_exclusion_ref")

    # ---- endpoint_annotations(四分账枚举;矿化证据最低口径字段) ----
    annotations = graph.get("endpoint_annotations")
    if not isinstance(annotations, list):
        raise ReferenceGraphContractError(
            "endpoint_annotations 必须是列表", {
                "kind": "reference_graph_field_invalid",
                "field": "endpoint_annotations"})
    for i, annotation in enumerate(annotations):
        field = f"endpoint_annotations[{i}]"
        if not isinstance(annotation, dict):
            raise ReferenceGraphContractError(
                f"{field} 必须是对象", {
                    "kind": "reference_graph_field_invalid",
                    "field": field})
        for key in ("annotation_id", "endpoint_assessment",
                    "evidence_basis", "source_refs"):
            if key not in annotation:
                raise ReferenceGraphContractError(
                    f"{field}.{key} 缺失", {
                        "kind": "reference_graph_field_missing",
                        "field": f"{field}.{key}"})
        _req_str(annotation.get("annotation_id"),
                 f"{field}.annotation_id")
        _req_enum(annotation.get("endpoint_assessment"),
                  f"{field}.endpoint_assessment", ENDPOINT_ASSESSMENTS)
        _req_str(annotation.get("evidence_basis"),
                 f"{field}.evidence_basis")
        _req_str_list(annotation.get("source_refs"),
                      f"{field}.source_refs")
        target = annotation.get("node_id") or annotation.get("edge_id")
        if target is None:
            raise ReferenceGraphContractError(
                f"{field} 必须引用 node_id 或 edge_id(终点注记挂点)", {
                    "kind": "reference_graph_field_invalid",
                    "field": field})
        if annotation.get("node_id") is not None and \
                str(annotation["node_id"]) not in node_ids:
            raise ReferenceGraphContractError(
                f"{field}.node_id 引用未声明节点", {
                    "kind": "reference_graph_dangling_ref",
                    "field": field, "ref": str(annotation["node_id"])})
        if annotation.get("edge_id") is not None and \
                str(annotation["edge_id"]) not in edge_ids:
            raise ReferenceGraphContractError(
                f"{field}.edge_id 引用未声明边", {
                    "kind": "reference_graph_dangling_ref",
                    "field": field, "ref": str(annotation["edge_id"])})
        if annotation.get("endpoint_assessment") == \
                "supported_mineralization":
            missing = [key for key in MINERALIZATION_EVIDENCE_FIELDS
                       if not annotation.get(key)]
            if missing:
                raise ReferenceGraphContractError(
                    f"{field} 声明 supported_mineralization 但缺最低口径"
                    f"字段:{missing}(根碳账核查范围/观察范围/来源必须"
                    "显式;证据内容裁定属用户/teacher)", {
                        "kind":
                        "reference_graph_mineralization_evidence_missing",
                        "field": field, "missing": missing})

    # ---- coverage_statement(参考图不完处如实标注) ----
    coverage = graph.get("coverage_statement")
    if not isinstance(coverage, dict):
        raise ReferenceGraphContractError(
            "coverage_statement 必须是对象", {
                "kind": "reference_graph_field_invalid",
                "field": "coverage_statement"})
    for key in ("covered_axes", "known_gaps", "not_evaluable_node_ids",
                "not_evaluable_edge_ids"):
        if key not in coverage:
            raise ReferenceGraphContractError(
                f"coverage_statement.{key} 缺失(参考图不完备处必须"
                "如实标注;未画出的边不自动判模型错误)", {
                    "kind": "reference_graph_field_missing",
                    "field": f"coverage_statement.{key}"})
        _req_str_list(coverage[key], f"coverage_statement.{key}")
    dangling_not_evaluable = sorted(
        set(coverage["not_evaluable_node_ids"]) - node_ids)
    if dangling_not_evaluable:
        raise ReferenceGraphContractError(
            f"coverage_statement.not_evaluable_node_ids 引用未声明节点:"
            f"{dangling_not_evaluable}", {
                "kind": "reference_graph_dangling_ref",
                "refs": dangling_not_evaluable})

    # ---- provenance_manifest(§7.5;source_origin 与 evidence_basis
    # 分开保存;recorded 不自动升格实测) ----
    provenance = graph.get("provenance_manifest")
    if not isinstance(provenance, list):
        raise ReferenceGraphContractError(
            "provenance_manifest 必须是列表", {
                "kind": "reference_graph_field_invalid",
                "field": "provenance_manifest"})
    provenance_ids: set[str] = set()
    for i, record in enumerate(provenance):
        field = f"provenance_manifest[{i}]"
        if not isinstance(record, dict):
            raise ReferenceGraphContractError(
                f"{field} 必须是对象", {
                    "kind": "reference_graph_field_invalid",
                    "field": field})
        for key in _PROVENANCE_FIELDS:
            if key not in record:
                raise ReferenceGraphContractError(
                    f"{field}.{key} 缺失(§7.5 全字段必填)", {
                        "kind": "reference_graph_field_missing",
                        "field": f"{field}.{key}"})
        provenance_id = _req_str(record.get("provenance_id"),
                                 f"{field}.provenance_id")
        if provenance_id in provenance_ids:
            raise ReferenceGraphContractError(
                f"provenance_id 重复:{provenance_id}", {
                    "kind": "reference_graph_duplicate_provenance",
                    "provenance_id": provenance_id})
        provenance_ids.add(provenance_id)
        _req_str(record.get("source_group_id"),
                 f"{field}.source_group_id")
        _req_str(record.get("source_origin"), f"{field}.source_origin")
        _req_str(record.get("evidence_basis"), f"{field}.evidence_basis")
        _req_str(record.get("citation_ref"), f"{field}.citation_ref")
        _req_str(record.get("structure_match_scope"),
                 f"{field}.structure_match_scope")
        _req_str(record.get("observation_scope"),
                 f"{field}.observation_scope")
        _req_enum(record.get("independent_status"),
                  f"{field}.independent_status", INDEPENDENCE_STATUSES)
        if not isinstance(record.get("source_conditions"), list):
            raise ReferenceGraphContractError(
                f"{field}.source_conditions 必须是列表(历史来源条件"
                "保留,不改写为当前场景事实)", {
                    "kind": "reference_graph_field_invalid",
                    "field": f"{field}.source_conditions"})
    referenced_provenance: set[str] = set()
    for node in nodes:
        referenced_provenance.update(node.get("provenance_refs") or [])
    for edge in edges:
        referenced_provenance.update(edge.get("provenance_refs") or [])
    dangling_provenance = sorted(referenced_provenance - provenance_ids)
    if dangling_provenance:
        raise ReferenceGraphContractError(
            f"节点/边引用未声明的 provenance:{dangling_provenance}", {
                "kind": "reference_graph_dangling_ref",
                "refs": dangling_provenance})

    # ---- creation_review(合成规则级样本显式标注) ----
    review = graph.get("creation_review")
    if not isinstance(review, dict):
        raise ReferenceGraphContractError(
            "creation_review 必须是对象", {
                "kind": "reference_graph_field_invalid",
                "field": "creation_review"})
    for key in ("review_status", "reviewer", "note"):
        if key not in review:
            raise ReferenceGraphContractError(
                f"creation_review.{key} 缺失", {
                    "kind": "reference_graph_field_missing",
                    "field": f"creation_review.{key}"})
    _req_enum(review.get("review_status"),
              "creation_review.review_status", CREATION_REVIEW_STATUSES)
    _req_str(review.get("reviewer"), "creation_review.reviewer")
    _req_str(review.get("note"), "creation_review.note")
    return graph


def reference_graph_sha256(graph: dict) -> str:
    """参考图内容的 SHA-256(canonical_json 确定性序列化)。"""
    return hashlib.sha256(
        canonical_json(graph).encode("utf-8")).hexdigest()


def load_reference_graph(path: str | Path) -> dict:
    """读取参考图文件并校验(S5-01:缺字段/坏版本明确失败)。"""
    path = Path(path)
    try:
        graph = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise ReferenceGraphContractError(
            f"参考图文件不可读取/不可解析:{path}", {
                "kind": "reference_graph_unparseable",
                "path": str(path),
                "error": f"{type(exc).__name__}: {exc}"[:200]}) from exc
    return validate_reference_graph(graph)
