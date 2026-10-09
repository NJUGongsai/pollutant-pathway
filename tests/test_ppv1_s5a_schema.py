"""S5a 评测接口 schema 回归(参考图/split manifest/评测输入/预注册
模板/守卫;S5 任务书 §7/§8/§10.2/§14.3 + 验收矩阵 S5-01/S5-21/
S5-22/S5-23/S5-26/S5-27/S5-28)。

覆盖:
- S5-01 合成 reference graph 读取:schema/版本/字段完整性确定性校验,
  缺字段/坏版本/坏文件明确失败(不静默删字段、不自动补全);
- §7 全字段:根对象有限范围声明、distinct occurrence 保留(重复
  occurrence 拒绝、同结构不同 occurrence 合法)、边交叉引用、
  矿化注记最低口径字段、来源组/条件/覆盖/评审字段;
- split manifest schema(§6.3);
- 评测输入 schema(§8.1):缺字段/重复导出/lossy 投影契约/
  混合题域(S5-21)/混合轨道(S5-22)拒绝;
- 预注册模板(§10.2/§14.3):TBD 逐项标注、approval pending、
  frozen=False、版本 fail-closed;
- S5-26 收费 provider 默认关:real 无授权结构化拒绝;
- S5-27 含金标产物写入普通目录拒绝(授权 gitignored 根放行);
- S5-28 S4 native export 未交付:可验证接口,状态 pending,零指标。

全部为合成规则级夹具:零金标、零题面、零网络、零 LLM、零费用;
数字不外推 dev/298。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant import preregistration  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    EMITTED_STATUSES,
    EvaluationContractError,
    GOLD_AUTHORIZED_ROOTS,
    evaluate_scientific,
    persist_evaluation_output,
    validate_evaluation_input,
    validate_split_manifest,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    PPV1_EVALUATION_VERSION,
    PPV1_NATIVE_EXPORT_VERSION,
    PPV1_PREREGISTRATION_TEMPLATE_VERSION,
    PPV1_REFERENCE_GRAPH_VERSION,
    PPV1_SPLIT_MANIFEST_VERSION,
)
from pathway_v43.pollutant.reference_graph import (  # noqa: E402
    ReferenceGraphContractError,
    load_reference_graph,
    reference_graph_sha256,
    validate_reference_graph,
)

REPO = Path(__file__).resolve().parents[1]


# ---------------------------------------------------- 合成参考图夹具


def condition_scope(key: str, value: str, *, status: str = "known_present",
                    required: str = "essential") -> dict:
    return {
        "key": key,
        "value_or_interval": value,
        "unit": "",
        "status": status,
        "required": required,
        "subject_scenario_ref": "scenario:synth-aerobic",
        "source_refs": ["src:synthetic"],
    }


def synth_reference_graph(
        graph_id: str = "rg-synth-1", *,
        domain: str = "dev",
        track: str = "known_evidence_reconstruction",
        split: str = "development",
        extra_edges: list[dict] | None = None,
        provenance_override: list[dict] | None = None,
        source_groups_override: list[dict] | None = None,
        track_cn_only_node: bool = False,
        coverage_override: dict | None = None,
) -> dict:
    """S5a 合成参考图(规则级;与真实链路合成 run 的产物对应:
    root CCO → CC=O(+[H][H] 共同产物/无共同产物两条备选边)。"""
    nodes = [
        {
            "node_id": "n-root", "state_identity": "strict:CCO",
            "structure_smiles": "CCO",
            "structure_identity_scope": "strict_structure",
            "role": "root", "occurrence_id": "occ-root-1",
            "source_group_refs": ["sg-study-A", "sg-study-B"],
            "condition_scope": [],
            "provenance_refs": ["pv-1", "pv-2"],
            "node_status": "observed",
        },
        {
            "node_id": "n-int-occ-a", "state_identity": "strict:CC=O",
            "structure_smiles": "CC=O",
            "structure_identity_scope": "strict_structure",
            "role": "intermediate", "occurrence_id": "occ-cco-a",
            "source_group_refs": ["sg-study-A"],
            "condition_scope": [],
            "provenance_refs": ["pv-1"],
            "node_status": "observed",
        },
        {
            # S5-04:同一结构不同来路 distinct occurrence(不按 CN 合并)
            "node_id": "n-int-occ-b", "state_identity": "strict:CC=O",
            "structure_smiles": "CC=O",
            "structure_identity_scope": "strict_structure",
            "role": "intermediate", "occurrence_id": "occ-cco-b",
            "source_group_refs": ["sg-study-B"],
            "condition_scope": [],
            "provenance_refs": ["pv-2"],
            "node_status": "observed",
        },
        {
            "node_id": "n-coproduct-h2", "state_identity": "strict:[H][H]",
            "structure_smiles": "[H][H]",
            "structure_identity_scope": "strict_structure",
            "role": "coproduct", "occurrence_id": "occ-h2-a",
            "source_group_refs": ["sg-study-A"],
            "condition_scope": [],
            "provenance_refs": ["pv-1"],
            "node_status": "observed",
        },
    ]
    if track_cn_only_node:
        nodes.append({
            "node_id": "n-cn-only", "state_identity": "cn:CC=O",
            "structure_smiles": "CC=O",
            "structure_identity_scope": "cn_only",
            "role": "unknown", "occurrence_id": "occ-cn-1",
            "source_group_refs": ["sg-study-B"],
            "condition_scope": [],
            "provenance_refs": ["pv-2"],
            "node_status": "reference_only",
        })
    edges = [
        {
            # S5-02 备选边 1:A→B + 共同产物(S5-03 共同产物不被报告 K 删)
            "edge_id": "e-alt-1", "from_node_ids": ["n-root"],
            "to_node_ids": ["n-int-occ-a", "n-coproduct-h2"],
            "transformation_ref": "tref-donor-B",
            "transformation_signature_status": "declared",
            "participants": [
                {"node_id": "n-root", "side": "reactant",
                 "role": "primary_substrate", "coefficient": 1,
                 "coefficient_status": "known"},
                {"node_id": "n-int-occ-a", "side": "product",
                 "role": "principal_product", "coefficient": 1,
                 "coefficient_status": "known"},
                {"node_id": "n-coproduct-h2", "side": "product",
                 "role": "coproduct", "coefficient": None,
                 "coefficient_status": "unknown"},
            ],
            "participant_list_status": "declared_complete",
            "coefficient_status": "partial",
            "step_scope": "net_reaction",
            "condition_requirements": [
                condition_scope("oxygen_regime", "aerobic"),
                condition_scope("redox_regime", "anaerobic"),
                condition_scope("oxygen_regime", "anaerobic"),
            ],
            "scenario_scope": "scenario:synth-aerobic",
            "provenance_refs": ["pv-1"],
            "source_group_refs": ["sg-study-A"],
            "evidence_basis": "study_series",
            "edge_status": "observed",
        },
        {
            # S5-02 备选边 2:A→C(同父备选,不合并成 B+C 单一事件)
            "edge_id": "e-alt-2", "from_node_ids": ["n-root"],
            "to_node_ids": ["n-int-occ-b"],
            "transformation_ref": "tref-donor-C",
            "transformation_signature_status": "declared",
            "participants": [
                {"node_id": "n-root", "side": "reactant",
                 "role": "primary_substrate", "coefficient": 1,
                 "coefficient_status": "known"},
                {"node_id": "n-int-occ-b", "side": "product",
                 "role": "principal_product", "coefficient": 1,
                 "coefficient_status": "known"},
            ],
            "participant_list_status": "declared_complete",
            "coefficient_status": "known",
            "step_scope": "net_reaction",
            "condition_requirements": [
                condition_scope("oxygen_regime", "aerobic")],
            "scenario_scope": "scenario:synth-aerobic",
            "provenance_refs": ["pv-2"],
            "source_group_refs": ["sg-study-B"],
            "evidence_basis": "study_series",
            "edge_status": "observed",
        },
    ]
    edges.extend(extra_edges or [])
    source_groups = source_groups_override or [
        {   # S5-05:同一研究两条数据库记录归并一组(不虚增独立支持)
            "source_group_id": "sg-study-A",
            "independence_status": "independent",
            "member_records": ["rhea:1001", "rhea:1002"],
            "note": "同论文两条记录:一组",
        },
        {
            "source_group_id": "sg-study-B",
            "independence_status": "independent",
            "member_records": ["rhea:2001"],
            "note": "独立研究 B",
        },
    ]
    split_assignment = {
        "split": split,
        "split_rule_version": "ppv1-split-rule-synth-1",
        "route_group_keys": ["route-ethanol-oxidation"],
    }
    if track == "unseen_path_inference":
        split_assignment["unseen_exclusion_ref"] = "uex-synth-1"
    provenance = provenance_override or [
        {
            "provenance_id": "pv-1", "source_group_id": "sg-study-A",
            "source_origin": "journal",
            "evidence_basis": "direct_observation",
            "citation_ref": "cite:synth-A",
            "structure_match_scope": "strict_structure",
            "observation_scope": "lab_incubation",
            # S5-15:历史来源条件原样保留(不改写为当前场景事实)
            "source_conditions": [
                {"key": "temperature", "value_or_interval": "30",
                 "unit": "C", "status": "known_present",
                 "required": "preference",
                 "subject_scenario_ref": "scenario:study-A-historical",
                 "source_refs": ["cite:synth-A"]}],
            "independent_status": "independent",
        },
        {
            "provenance_id": "pv-2", "source_group_id": "sg-study-B",
            "source_origin": "database",
            "evidence_basis": "recorded",
            "citation_ref": "cite:synth-B",
            "structure_match_scope": "strict_structure",
            "observation_scope": "recorded_only",
            "source_conditions": [],
            "independent_status": "independent",
        },
    ]
    return {
        "schema_version": PPV1_REFERENCE_GRAPH_VERSION,
        "reference_graph_id": graph_id,
        "domain": domain,
        "track": track,
        "root_entity": {
            "entity_id": "root-ethanol",
            "structure_smiles_raw": "CCO",
            "strict_structure_identity": "CCO",
            "formal_charge": 0,
            "stereo_information_status": "not_applicable",
            "isotope_information_status": "not_applicable",
            "source_refs": ["src:synthetic"],
        },
        "nodes": nodes,
        "edges": edges,
        "endpoint_annotations": [],
        "source_groups": source_groups,
        "split_assignment": split_assignment,
        "coverage_statement": coverage_override or {
            "covered_axes": ["nodes", "edges"],
            "known_gaps": [],
            "not_evaluable_node_ids": [],
            "not_evaluable_edge_ids": [],
        },
        "provenance_manifest": provenance,
        "creation_review": {
            "review_status": "synthetic_rule_level",
            "reviewer": "s5a-synthetic",
            "note": "S5a 合成规则级参考图(无金标/题面)",
        },
    }


def synth_split_manifest(*, graph_id: str = "rg-synth-1",
                         split: str = "development",
                         group_ids: list[str] | None = None,
                         excluded: list[dict] | None = None) -> dict:
    return {
        "schema_version": PPV1_SPLIT_MANIFEST_VERSION,
        "split_manifest_id": "sm-synth-1",
        "split_rule_version": "ppv1-split-rule-synth-1",
        "input_data_manifest_hash": "sha:synthetic-inputs",
        "assignments": [
            {"reference_graph_id": graph_id,
             "source_group_id": group_id, "split": split}
            for group_id in (
                group_ids or ["sg-study-A", "sg-study-B"])],
        "unseen_exclusion_manifest": {
            "track": "unseen_path_inference",
            "excluded": excluded or [],
        },
    }


def synth_evaluation_input(*, domain: str = "dev",
                           track: str = "known_evidence_reconstruction",
                           graphs: list[dict] | None = None,
                           split_manifest: dict | None = None,
                           exports: list[dict] | None = None,
                           provider: dict | None = None,
                           interface: bool = True,
                           data_scope: str = "synthetic_rule_level",
                           extra: dict | None = None) -> dict:
    graphs = graphs if graphs is not None else [synth_reference_graph()]
    manifest = split_manifest or synth_split_manifest()
    graph_entries = [{
        "reference_graph_id": graph["reference_graph_id"],
        "sha256": reference_graph_sha256(graph),
        "domain": domain,
        "track": track,
    } for graph in graphs]
    evaluation_input = {
        "evaluator_schema_version": PPV1_EVALUATION_VERSION,
        "run_identity": {
            "run_id": "synth-run-1",
            # S5b 启动批回修:profile-24 → -25(evaluation-5 real 档
            # 配对禁 root_identity_fallback,S5B-L01;run_identity 夹具
            # 字面量同步)
            "profile_version": "ppv1-profile-25",
            "export_schema_version": PPV1_NATIVE_EXPORT_VERSION,
        },
        "native_path_exports": exports or [],
        "reference_graph_manifest": graph_entries,
        "split_manifest": manifest,
        "domain": domain,
        "track": track,
        "metric_policy_version": "ppv1-evaluation-metrics-proposed",
        "preregistration_id": "prereg-s5a-template",
        "scoring_policy_version": "ppv1-evaluation-scoring-proposed",
        "missingness_policy_version":
            "ppv1-evaluation-missingness-proposed",
        "data_scope": data_scope,
        "interface_verification": interface,
        "model_provider_policy": provider or {"provider_kind": "none"},
    }
    if extra:
        evaluation_input.update(extra)
    return evaluation_input


# ---------------------------------------------------- S5-01 参考图读取


def test_s5_01_reference_graph_full_field_validation() -> None:
    """S5-01:全字段确定性校验通过;sha256 稳定。"""
    graph = synth_reference_graph()
    assert validate_reference_graph(graph) is graph
    assert reference_graph_sha256(graph) == \
        reference_graph_sha256(synth_reference_graph())


def test_s5_01_missing_field_fails_with_field_path() -> None:
    """S5-01:缺字段明确失败(kind + 字段路径;不静默补全)。"""
    graph = synth_reference_graph()
    del graph["edges"][0]["step_scope"]
    with pytest.raises(ReferenceGraphContractError) as excinfo:
        validate_reference_graph(graph)
    assert excinfo.value.detail["kind"] == \
        "reference_graph_field_missing"
    assert "step_scope" in excinfo.value.detail["field"]


def test_s5_01_unknown_schema_version_refused() -> None:
    """S5-01:版本未知 fail-closed 拒绝(不猜迁移)。"""
    graph = synth_reference_graph()
    graph["schema_version"] = "ppv1-reference-graph-0"
    with pytest.raises(ReferenceGraphContractError) as excinfo:
        validate_reference_graph(graph)
    assert excinfo.value.detail["kind"] == \
        "reference_graph_version_unknown"


def test_s5_01_unparseable_file_refused(tmp_path: Path) -> None:
    """S5-01:坏文件(非 JSON)结构化拒绝。"""
    bad = tmp_path / "bad_graph.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ReferenceGraphContractError) as excinfo:
        load_reference_graph(bad)
    assert excinfo.value.detail["kind"] == \
        "reference_graph_unparseable"
    good = tmp_path / "good_graph.json"
    good.write_text(json.dumps(synth_reference_graph()),
                    encoding="utf-8")
    assert load_reference_graph(good)["reference_graph_id"] == \
        "rg-synth-1"


def test_reference_graph_unknown_top_level_field_refused() -> None:
    graph = synth_reference_graph()
    graph["surprise"] = 1
    with pytest.raises(ReferenceGraphContractError) as excinfo:
        validate_reference_graph(graph)
    assert excinfo.value.detail["kind"] == \
        "reference_graph_unknown_field"


def test_reference_graph_root_limited_scope_declaration() -> None:
    """§7.2:缺完整结构必须显式 identity_scope + 缺失维度 + 指标范围。"""
    graph = synth_reference_graph()
    graph["root_entity"]["strict_structure_identity"] = ""
    with pytest.raises(ReferenceGraphContractError) as excinfo:
        validate_reference_graph(graph)
    assert excinfo.value.detail["kind"] == \
        "reference_graph_identity_scope_missing"
    graph["root_entity"]["identity_scope"] = "cn_only"
    graph["root_entity"]["missing_structure_dimensions"] = ["stereo"]
    graph["root_entity"]["metric_scope_note"] = "仅 CN 旁证可用"
    validate_reference_graph(graph)  # 合法:显式声明有限范围


def test_reference_graph_distinct_occurrence_kept() -> None:
    """§7.3/S5-04:同结构 distinct occurrence 合法保留;重复 occurrence
    拒绝(不按 CN 或结构首现合并)。"""
    graph = synth_reference_graph()
    occurrences = [node["occurrence_id"] for node in graph["nodes"]
                   if node["structure_smiles"] == "CC=O"]
    assert len(occurrences) == 2  # occ-cco-a / occ-cco-b 保留
    duplicate = dict(graph["nodes"][1])
    duplicate["node_id"] = "n-dup"  # 仅 occurrence 重复,节点 ID 不同
    graph["nodes"].append(duplicate)
    with pytest.raises(ReferenceGraphContractError) as excinfo:
        validate_reference_graph(graph)
    assert excinfo.value.detail["kind"] == \
        "reference_graph_duplicate_occurrence"


def test_reference_graph_mineralization_evidence_floor() -> None:
    """§7/§9.6:矿化注记须带最低口径字段(根碳账核查范围/观察范围/
    来源;只核存在,内容裁定属用户/teacher)。"""
    graph = synth_reference_graph()
    graph["endpoint_annotations"] = [{
        "annotation_id": "ann-1", "edge_id": "e-alt-1",
        "endpoint_assessment": "supported_mineralization",
        "evidence_basis": "direct_observation",
        "source_refs": ["src:synthetic"],
    }]
    with pytest.raises(ReferenceGraphContractError) as excinfo:
        validate_reference_graph(graph)
    assert excinfo.value.detail["kind"] == (
        "reference_graph_mineralization_evidence_missing")
    graph["endpoint_annotations"][0].update({
        "root_carbon_fate_check_scope": "14C 平衡 92%",
        "observation_scope": "28d incubation",
    })
    validate_reference_graph(graph)


# ---------------------------------------------------- split manifest


def test_split_manifest_schema() -> None:
    manifest = synth_split_manifest()
    assert validate_split_manifest(manifest) is manifest
    bad = synth_split_manifest()
    bad["schema_version"] = "ppv1-split-manifest-0"
    with pytest.raises(EvaluationContractError) as excinfo:
        validate_split_manifest(bad)
    assert excinfo.value.detail["kind"] == "split_manifest_version_unknown"
    conflicting = synth_split_manifest()
    conflicting["assignments"].append({
        "reference_graph_id": "rg-synth-1",
        "source_group_id": "sg-study-A", "split": "held_out"})
    with pytest.raises(EvaluationContractError) as excinfo:
        validate_split_manifest(conflicting)
    assert excinfo.value.detail["kind"] == \
        "split_manifest_duplicate_assignment"


# ------------------------------------------- S5-21/S5-22 输入 schema


def test_evaluation_input_required_fields() -> None:
    evaluation_input = synth_evaluation_input()
    assert validate_evaluation_input(evaluation_input) is evaluation_input
    missing = dict(evaluation_input)
    del missing["scoring_policy_version"]
    with pytest.raises(EvaluationContractError) as excinfo:
        validate_evaluation_input(missing)
    assert excinfo.value.detail["kind"] == \
        "evaluation_input_field_missing"
    wrong_version = dict(evaluation_input)
    wrong_version["evaluator_schema_version"] = "ppv1-evaluation-0"
    with pytest.raises(EvaluationContractError) as excinfo:
        validate_evaluation_input(wrong_version)
    assert excinfo.value.detail["kind"] == "evaluation_version_unknown"


def test_s5_21_mixed_domain_refused() -> None:
    """S5-21:dev 与 298 输入混合 ⇒ 评测器拒绝,不产生无题域标签总分。"""
    evaluation_input = synth_evaluation_input(domain="dev")
    # manifest 条目声明 298 ⇒ 与输入 dev 不符
    evaluation_input["reference_graph_manifest"][0]["domain"] = "298"
    with pytest.raises(EvaluationContractError) as excinfo:
        validate_evaluation_input(evaluation_input)
    assert excinfo.value.detail["kind"] == "evaluation_domain_mismatch"


def test_s5_22_mixed_track_refused() -> None:
    """S5-22:known 与 unseen 输入混合 ⇒ 拒绝合并,轨道分别报告。"""
    evaluation_input = synth_evaluation_input(
        track="known_evidence_reconstruction")
    evaluation_input["reference_graph_manifest"][0]["track"] = \
        "unseen_path_inference"
    with pytest.raises(EvaluationContractError) as excinfo:
        validate_evaluation_input(evaluation_input)
    assert excinfo.value.detail["kind"] == "evaluation_track_mismatch"


def test_evaluation_input_lossy_projection_contract() -> None:
    """§3.1:lossy 投影条目必须携带 native_reference + lost_fields。"""
    evaluation_input = synth_evaluation_input(exports=[
        {"run_id": "synth-run-1", "export_digest": "d1",
         "lossy_projection": True}])
    with pytest.raises(EvaluationContractError) as excinfo:
        validate_evaluation_input(evaluation_input)
    assert excinfo.value.detail["kind"] == \
        "evaluation_input_field_missing"
    evaluation_input["native_path_exports"][0].update({
        "native_reference": "native:d1", "lost_fields": ["route_origins"]})
    validate_evaluation_input(evaluation_input)


# ---------------------------------------------------- 预注册模板


def test_s5_23_preregistration_template_tbd_marking() -> None:
    """S5-23/§14.3:样本量或通过线为 TBD ⇒ 状态保持 pending,不生成
    科学通过结论;模板逐项标注 TBD/proposed/接口级/发布限制。"""
    template = preregistration.build_preregistration_template()
    fields = preregistration.preregistration_frozen_fields(template)
    assert fields["approval_status"] == "pending_user_teacher_decision"
    assert fields["frozen"] is False
    # §10.1 全部 20 项均为 TBD(用户/teacher 裁定,不得代定)
    assert len(fields["tbd_user_teacher_decision_items"]) == 20
    assert "sample_size_dev" in fields["tbd_user_teacher_decision_items"]
    assert "pass_threshold" in fields["tbd_user_teacher_decision_items"]
    assert "TBD_USER_TEACHER_DECISION" == template["sample_size"]
    assert template["threshold_policy"] == "TBD_USER_TEACHER_DECISION"
    # proposed 规则未冻结
    assert "identity_matching_policy" in fields["proposed_rule_fields"]
    assert template["model_provider_policy"]["status"] == \
        "PROPOSED_DEFAULT_OFF"
    # 指标只有接口定义
    assert template["metric_interface_status"][
        "reference_edge_recall"] == "interface_definition_only"
    # 冻结前不得对外发布
    assert template["publication_restriction"] == (
        "no_release_before_freeze:冻结前不得对外发布任何 dev/298"
        "科学指标数值;对外数字必须带题域标签;工程绿数与接口验证"
        "不得写成科学性能通过(§12)")


def test_preregistration_validation_fail_closed() -> None:
    template = preregistration.build_preregistration_template()
    assert preregistration.validate_preregistration(template) is template
    with pytest.raises(ValueError, match="模板版本未知"):
        preregistration.validate_preregistration(
            {"template_version": "ppv1-preregistration-template-0"})
    with pytest.raises(ValueError, match="approval_status 非法"):
        preregistration.validate_preregistration(
            {**template, "approval_status": "auto_approved"})
    assert preregistration.preregistration_sha256(template) == \
        preregistration.preregistration_sha256(
            preregistration.build_preregistration_template())


# ---------------------------------------------------- S5-26 provider


def test_s5_26_paid_provider_off_by_default() -> None:
    """S5-26:收费 provider 默认关 —— real 无用户逐次授权 ⇒ 结构化
    拒绝(无授权时网络请求为零、费用为零,正式科学评测不启动)。"""
    evaluation_input = synth_evaluation_input(provider={
        "provider_kind": "real"})
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(
            evaluation_input,
            reference_graphs={"rg-synth-1": synth_reference_graph()},
            preregistration=preregistration.build_preregistration_template())
    assert excinfo.value.detail["kind"] == "provider_not_authorized"
    # 未知 provider_kind 在输入校验层拒绝
    with pytest.raises(EvaluationContractError) as excinfo:
        validate_evaluation_input(synth_evaluation_input(provider={
            "provider_kind": "whatever"}))
    assert excinfo.value.detail["kind"] == \
        "evaluation_input_enum_invalid"


def test_real_data_scope_requires_approved_prereg() -> None:
    """真实数据评测须已批准预注册(S5b 边界;本批一律拒绝)。"""
    evaluation_input = synth_evaluation_input(
        data_scope="real", interface=False)
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(
            evaluation_input,
            reference_graphs={"rg-synth-1": synth_reference_graph()},
            preregistration=preregistration.build_preregistration_template())
    assert excinfo.value.detail["kind"] == \
        "real_data_requires_approved_preregistration"


# ---------------------------------------------------- S5-27 金标守卫


def test_s5_27_gold_output_write_guard(tmp_path: Path) -> None:
    """S5-27:含金标产物写入普通目录 ⇒ 流程拒绝;授权 gitignored 根
    (镜像 .gitignore)放行;非金标输出正常写。

    S5A-04:核验与写入同一解析后实际规范路径 —— 未声明根 ⇒ 含金标
    一律拒(gold_content_root_required);解析后逃出声明根(错 cwd/
    symlink 逃根)先拒零新文件(gold_content_outside_declared_root)。"""
    output = {"status": "interface_verified_only", "payload": "synthetic"}
    plain = tmp_path / "out" / "report.json"
    with pytest.raises(EvaluationContractError) as excinfo:
        persist_evaluation_output(output, plain, contains_gold=True)
    # S5A-04:未声明 repo_root ⇒ 含金标写入一律拒绝(根规则明确)
    assert excinfo.value.detail["kind"] == "gold_content_root_required"
    assert not plain.exists()  # 零写入
    # 仓内普通路径同样拒绝(用临时 repo_root 模拟仓根)
    repo_root = tmp_path / "repo"
    inside_plain = repo_root / "docs" / "report.json"
    with pytest.raises(EvaluationContractError):
        persist_evaluation_output(
            output, inside_plain, contains_gold=True,
            repo_root=repo_root)
    # 授权根(镜像 .gitignore 金标隔离目录)放行;回执为实际写入路径
    authorized = repo_root / "reports" / "phase_s1_hit60" / "dev_gold" \
        / "report.json"
    receipt = persist_evaluation_output(
        output, authorized, contains_gold=True,
        repo_root=repo_root)
    assert authorized.is_file()
    assert receipt["sha256"]
    assert receipt["path"] == str(authorized.resolve())
    assert "reports/phase_s1_hit60/dev_gold" in GOLD_AUTHORIZED_ROOTS
    # 非金标输出写普通目录合法
    normal = persist_evaluation_output(output, plain)
    assert normal["path"] == str(plain)


# ---------------------------------------------------- S5-28 导出缺席


def test_s5_28_no_native_export_pending() -> None:
    """S5-28:S4 native export 未交付 ⇒ 可验证接口,不运行正式科学
    评测,状态 pending;零科学指标数值。"""
    evaluation_input = synth_evaluation_input(exports=[])
    output = evaluate_scientific(
        evaluation_input,
        reference_graphs={"rg-synth-1": synth_reference_graph()},
        preregistration=preregistration.build_preregistration_template())
    assert output["status"] == "pending_no_independent_data"
    assert output["scoring_provenance"]["llm_in_scoring"] is False
    assert output["scoring_provenance"]["network_request_count"] == 0
    assert output["scoring_provenance"]["provider_kind"] == "none"
    assert output["scoring_provenance"]["cost"] == 0
    assert output["scoring_provenance"]["data_scope"] == \
        "synthetic_rule_level"
    # 全部样本披露"导出缺席",不冒充已评
    assert output["sample_results"][0]["scoring_status"] == \
        "not_evaluated_export_missing"
    assert output["invalid_input_count"] == 1
    # 聚合指标桶全空(接口结构在,无数值主张)
    assert all(metric["status"] == "interface_only_synthetic"
               for metric in output["aggregate_metrics"])


def test_emitted_status_never_evaluated() -> None:
    """§12:评测器永不生成 evaluated_*(最终科学状态由用户/teacher
    按预注册裁定)。"""
    assert "evaluated_not_passed" not in EMITTED_STATUSES
    assert "evaluated_passed_with_scope" not in EMITTED_STATUSES
    assert EMITTED_STATUSES <= {
        "pending_no_independent_data", "pending_preregistration",
        "pending_user_teacher_decision", "interface_verified_only",
        "blocked_data_integrity", "blocked_leakage",
        "blocked_scoring_contract"}
