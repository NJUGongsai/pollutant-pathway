"""S5a 回修 r1 回归(复审 POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_2026-10-09
§4 四组 P1: S5A-01 identity scope 许可消费 / S5A-02 条件分类沿冻结
同源规则 / S5A-03 必要参考节点空命中不被 union 吞 / S5A-04 persist
核验与写入同一实际规范路径;契约 ppv1-evaluation-1 → -2)。

全部为合成规则级夹具(零金标/题面/网络/LLM/费用;数字不外推
dev/298)。真实链路案走公共 ``start_run`` → ``read_native_export``
首读 → ``evaluate_scientific``(与评审 identity/conditions/
write_boundary 探针同案构造,节点→边→聚合逐层断言)。
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.pollutant import preregistration  # noqa: E402
from pathway_v43.pollutant import evaluation as _evaluation_module  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    EvaluationContractError,
    classify_condition_requirement,
    evaluate_scientific,
    match_reference_nodes,
    persist_evaluation_output,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    PPV1_EVALUATION_VERSION,
    PPV1_PREREGISTRATION_TEMPLATE_VERSION,
    PPV1_PROFILE_SCHEMA_VERSION,
)
from pathway_v43.pollutant.reference_graph import (  # noqa: E402
    validate_reference_graph,
)


def _detailed(requirement: dict, facts: list) -> dict:
    """S5A-02 详细分类器(经模块属性取用:父基线缺该实现 ⇒ 逐
    nodeid 真实红,不是 collection 错误)。"""
    return _evaluation_module._classify_condition_requirement_detailed(
        requirement, facts)
from test_ppv1_s4a_endpoint import spec  # noqa: E402
from test_ppv1_s5a_evaluator import (  # noqa: E402
    _plan,
    _reader,
    _run,
)
from test_ppv1_s5a_schema import (  # noqa: E402
    condition_scope,
    synth_evaluation_input,
    synth_reference_graph,
)

LIMITED_SCOPES = ("cn_only", "partial", "unknown")


def _one_run(tmp_path: Path, run_id: str):
    """一条真实链路 run(公共 start;两备选 CCO→CC=O 事件)。"""
    plan = _plan(select=2)
    runs_root, out = _run(tmp_path, run_id, plan)
    digest = out["native_export"]["export_digest"]
    return runs_root, run_id, digest


def _evaluate_graph(tmp_path: Path, run_id: str, digest: str,
                    graph: dict) -> dict:
    validate_reference_graph(graph)
    evaluation_input = synth_evaluation_input(
        graphs=[graph],
        exports=[{"run_id": run_id, "export_digest": digest}])
    evaluation_input["run_identity"]["run_id"] = run_id
    return evaluate_scientific(
        evaluation_input,
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=_reader(
            tmp_path / "runs", run_id),
        preregistration=preregistration.build_preregistration_template())


# ------------------------------------------------------- S5A-01 identity scope


@pytest.mark.parametrize("scope", LIMITED_SCOPES)
def test_s5a01_limited_scope_intermediate_nodes_capped_to_collateral(
        tmp_path: Path, scope: str) -> None:
    """S5A-01(中间体档):参考中间体声明 cn_only/partial/unknown ⇒
    内容严格相等也只作 CN 旁证(cn_only + identity_scope_cap 机读),
    不授 strict_structure;两备选边无许可严格命中 ⇒ 未覆盖分桶;
    聚合 matched_strict 归零(节点→边→聚合逐层翻转)。"""
    runs_root, run_id, digest = _one_run(tmp_path, "s5a01-int-" + scope)
    graph = synth_reference_graph()
    for node in graph["nodes"]:
        if node["role"] == "intermediate":
            node["structure_identity_scope"] = scope
    output = _evaluate_graph(tmp_path, run_id, digest, graph)
    sample = output["sample_results"][0]
    for entry in sample["predicted_node_matches"]:
        if entry["reference_identity_scope"] == scope:
            assert entry["match_status"] == "cn_only"
            assert entry["matched_state_ids"] == []
            # 内容严格相等的旁证状态进 cn_only_state_ids + 机读封顶披露
            assert entry["cn_only_state_ids"]
            assert entry["identity_scope_cap"][
                "reference_identity_scope"] == scope
            assert entry["identity_scope_cap"][
                "content_strict_equal_state_ids"]
            assert entry["identity_scope_cap"]["capped_to"] == "cn_only"
        else:
            # 未声明有限 scope 的节点(根/共同产物)合法严格命中保持
            assert entry["match_status"] == "strict_structure"
    for edge in sample["predicted_edge_matches"]:
        assert edge["match_status"] != "matched_strict"
        assert edge["match_status"] == "unmatched_required_node_uncovered"
        gaps = {g["node_id"] for g in edge["required_node_gaps"]}
        # e-alt-1 声明 to=[n-int-occ-a, n-coproduct-h2]:仅被封顶的
        # 中间体缺严格命中;e-alt-2 声明 to=[n-int-occ-b]
        assert gaps == ({"n-int-occ-a"} if edge["edge_id"] == "e-alt-1"
                        else {"n-int-occ-b"})
    recall = next(m for m in output["aggregate_metrics"]
                  if m["metric_id"] == "reference_edge_recall")
    assert recall["buckets"].get("matched_strict", 0) == 0
    assert recall["buckets"]["unmatched_required_node_uncovered"] == 2
    intermediates = next(
        m for m in output["aggregate_metrics"]
        if m["metric_id"] == "key_intermediate_recall")
    assert intermediates["buckets"].get("strict_structure", 0) == 0
    assert intermediates["buckets"]["cn_only"] == 2


@pytest.mark.parametrize("scope", LIMITED_SCOPES)
def test_s5a01_limited_scope_all_nodes_capped(tmp_path: Path,
                                              scope: str) -> None:
    """S5A-01(全部节点档):整图声明有限 scope ⇒ 全部节点封顶旁证、
    零严格边;不全面拒绝带标签或有限图(样本仍 scored、条目保留)。"""
    runs_root, run_id, digest = _one_run(tmp_path, "s5a01-all-" + scope)
    graph = synth_reference_graph()
    for node in graph["nodes"]:
        node["structure_identity_scope"] = scope
    output = _evaluate_graph(tmp_path, run_id, digest, graph)
    sample = output["sample_results"][0]
    assert sample["scoring_status"] == "scored"  # 不全面拒绝有限图
    for entry in sample["predicted_node_matches"]:
        assert entry["match_status"] == "cn_only"
        assert entry["identity_scope_cap"]
    for edge in sample["predicted_edge_matches"]:
        assert edge["match_status"] == "unmatched_required_node_uncovered"
    recall = next(m for m in output["aggregate_metrics"]
                  if m["metric_id"] == "reference_edge_recall")
    assert recall["buckets"].get("matched_strict", 0) == 0


def test_s5a01_legal_strict_and_real_cn_controls_kept(
        tmp_path: Path) -> None:
    """S5A-01 正控:合法 strict_scope 图保持两条完整严格边与严格节点;
    真实同位素/电荷差异的 CN 旁证(节点 cn_only、边不严格)保持。"""
    runs_root, run_id, digest = _one_run(tmp_path, "s5a01-controls")
    output = _evaluate_graph(tmp_path, run_id, digest,
                             synth_reference_graph())
    sample = output["sample_results"][0]
    assert all(edge["match_status"] == "matched_strict"
               for edge in sample["predicted_edge_matches"])
    assert all(node["match_status"] == "strict_structure"
               for node in sample["predicted_node_matches"])
    assert all(edge["required_node_gaps"] == []
               for edge in sample["predicted_edge_matches"])
    recall = next(m for m in output["aggregate_metrics"]
                  if m["metric_id"] == "reference_edge_recall")
    assert recall["buckets"]["matched_strict"] == 2
    # 真实严格差异(isotope/charge):CN 相同 ⇒ 旁证,非严格(S5-11)
    for name, smiles in (("isotope", "[13CH3]C=O"),
                         ("charge", "CC=[OH+]")):
        graph = synth_reference_graph()
        for node in graph["nodes"]:
            if node["role"] == "intermediate":
                node["structure_smiles"] = smiles
                node["state_identity"] = "strict:" + smiles
        mismatch = _evaluate_graph(tmp_path, run_id, digest, graph)
        nodes = mismatch["sample_results"][0]["predicted_node_matches"]
        assert all(entry["match_status"] == "cn_only"
                   for entry in nodes
                   if entry["reference_identity_scope"] ==
                   "strict_structure" and entry["role"] == "intermediate")
        assert all(edge["match_status"] != "matched_strict"
                   for edge in mismatch["sample_results"][0][
                       "predicted_edge_matches"])


def test_s5a01_matcher_unit_scope_cap() -> None:
    """S5A-01 单元级:cn_only scope 参考节点遇内容严格相等预测 ⇒
    cn_only(封顶);strict_scope 同节点 ⇒ strict_structure(许可差)。"""
    from pathway_v43.domain.identity import cn_identity
    from pathway_v43.pollutant.chemstate import strict_identity_of

    smiles = "F[C@H](Cl)Br"
    payload = {"states": [{
        "state_id": "cs-1",
        "payload": {"smiles_isomeric": strict_identity_of(smiles),
                    "cn_identity": cn_identity(smiles)}}]}
    node = {
        "node_id": "n-cap", "state_identity": "strict:r",
        "structure_smiles": smiles,
        "structure_identity_scope": "cn_only",
        "role": "intermediate", "occurrence_id": "occ-cap-1",
        "source_group_refs": ["sg-study-A"],
        "condition_scope": [], "provenance_refs": ["pv-1"],
        "node_status": "observed",
    }
    graph = synth_reference_graph()
    graph = {**graph, "nodes": graph["nodes"] + [node]}
    capped = match_reference_nodes(graph, payload)
    entry = next(e for e in capped if e["node_id"] == "n-cap")
    assert entry["match_status"] == "cn_only"
    assert entry["matched_state_ids"] == []
    assert entry["cn_only_state_ids"] == ["cs-1"]
    assert entry["identity_scope_cap"]["content_strict_equal_state_ids"] \
        == ["cs-1"]
    # 同一节点改为 strict scope ⇒ 严格命中(许可范围差即档位差)
    strict_node = dict(node)
    strict_node["structure_identity_scope"] = "strict_structure"
    graph = {**graph, "nodes": [n if n["node_id"] != "n-cap"
                                else strict_node
                                for n in graph["nodes"]]}
    granted = match_reference_nodes(graph, payload)
    entry = next(e for e in granted if e["node_id"] == "n-cap")
    assert entry["match_status"] == "strict_structure"
    assert entry["matched_state_ids"] == ["cs-1"]


# ------------------------------------------- S5A-03 required node closure


@pytest.mark.parametrize("side", ("reactant", "product"))
@pytest.mark.parametrize("kind", ("unmatched_structure",
                                  "limited_duplicate"))
def test_s5a03_required_node_empty_hit_blocks_strict(
        tmp_path: Path, side: str, kind: str) -> None:
    """S5A-03:原合法 declared_complete 边新增必需反应物/共同产物节点
    (from/to 与 participants 同源完整、schema 通过),该节点未严格
    命中 ⇒ 真实事件不得 matched_strict;空集保持未覆盖分桶 + 逐节点
    required_node_gaps 机读披露;另一条边合法严格保持。"""
    runs_root, run_id, digest = _one_run(tmp_path, "s5a03-" + side +
                                         "-" + kind)
    graph = synth_reference_graph()
    edge = graph["edges"][1]  # e-alt-2(A→C 备选边)
    existing = graph["nodes"][0] if side == "reactant" \
        else graph["nodes"][2]
    extra = copy.deepcopy(existing)
    extra.update(node_id="n-required-missing",
                 occurrence_id="occ-extra-required")
    if kind == "unmatched_structure":
        extra.update(structure_smiles="C", state_identity="strict:C")
    else:  # limited_duplicate:同结构但声明 cn_only(S5A-01 封顶)
        extra.update(structure_identity_scope="cn_only")
    graph["nodes"].append(extra)
    edge["from_node_ids" if side == "reactant"
         else "to_node_ids"].append(extra["node_id"])
    edge["participants"].append({
        "node_id": extra["node_id"], "side": side,
        "role": "cosubstrate" if side == "reactant" else "coproduct",
        "coefficient": 1, "coefficient_status": "known"})
    output = _evaluate_graph(tmp_path, run_id, digest, graph)
    sample = output["sample_results"][0]
    # schema 回执通过 + 全部节点条目保存(含新增节点)
    assert len(sample["predicted_node_matches"]) == 5
    added = next(e for e in sample["predicted_node_matches"]
                 if e["node_id"] == "n-required-missing")
    assert added["match_status"] in ("cn_only", "unmatched")
    target = next(e for e in sample["predicted_edge_matches"]
                  if e["edge_id"] == "e-alt-2")
    assert target["match_status"] == "unmatched_required_node_uncovered"
    assert target["matched_events"] == []
    gaps = {g["node_id"]: g for g in target["required_node_gaps"]}
    assert gaps["n-required-missing"]["side"] == side
    assert gaps["n-required-missing"]["node_match_status"] == \
        added["match_status"]
    # 未受影响的合法边保持严格
    other = next(e for e in sample["predicted_edge_matches"]
                 if e["edge_id"] == "e-alt-1")
    assert other["match_status"] == "matched_strict"
    assert other["required_node_gaps"] == []
    recall = next(m for m in output["aggregate_metrics"]
                  if m["metric_id"] == "reference_edge_recall")
    assert recall["buckets"]["matched_strict"] == 1
    assert recall["buckets"]["unmatched_required_node_uncovered"] == 1


def test_s5a03_participants_only_node_deferred_p2(
        tmp_path: Path) -> None:
    """S5A-03 范围限定:仅 participants 新增而 from/to 未列的多视图
    节点不进门禁(评审 §4.3 将该 schema 歧义单列 P2/表示语义同步;
    本回归钉住现行为,冻结前须裁定)。"""
    runs_root, run_id, digest = _one_run(tmp_path, "s5a03-part-only")
    graph = synth_reference_graph()
    edge = graph["edges"][1]
    extra = copy.deepcopy(graph["nodes"][3])
    extra.update(node_id="n-part-only", structure_smiles="C",
                 state_identity="strict:C",
                 occurrence_id="occ-part-only", role="coproduct")
    graph["nodes"].append(extra)
    edge["participants"].append({
        "node_id": extra["node_id"], "side": "product",
        "role": "coproduct", "coefficient": 1,
        "coefficient_status": "known"})
    output = _evaluate_graph(tmp_path, run_id, digest, graph)
    target = next(
        e for e in output["sample_results"][0]["predicted_edge_matches"]
        if e["edge_id"] == "e-alt-2")
    assert target["required_node_gaps"] == []
    assert target["match_status"] == "matched_strict"  # P2:不进门禁


def test_s5a03_legal_exact_superset_partial_controls_kept(
        tmp_path: Path) -> None:
    """S5A-03 正控:合法图 required_node_gaps 恒空;事件侧超集/缺共同
    产物的覆盖失配披露(matched_participant_coverage_partial)保持,
    不因必要节点闭合而吞覆盖分桶。"""
    runs_root, run_id, digest = _one_run(tmp_path, "s5a03-controls")
    output = _evaluate_graph(tmp_path, run_id, digest,
                             synth_reference_graph())
    sample = output["sample_results"][0]
    for edge in sample["predicted_edge_matches"]:
        assert edge["required_node_gaps"] == []
    edge1 = next(e for e in sample["predicted_edge_matches"]
                 if e["edge_id"] == "e-alt-1")
    assert edge1["match_status"] == "matched_strict"
    # 缺共同产物的事件仍进覆盖失配披露(partial_subset,不吞)
    partial = [m for m in edge1["coverage_mismatch_events"]
               if m["participant_coverage"] == "partial_subset"]
    assert partial or any(
        m["participant_coverage"] == "partial_subset"
        for e in sample["predicted_edge_matches"]
        for m in e["coverage_mismatch_events"])


# --------------------------------------- S5A-02 condition same-source closure


def _condition_case(name: str):
    """评审 20 条件案的(要求, 事实, 预期分类, 预期冻结状态)。"""
    def req(key, value, **kwargs):
        return {**condition_scope(key, value),
                "subject_scenario_ref": "", **kwargs}

    def fact(key, value, status="known_present", unit=""):
        return {"key": key, "value": value, "status": status,
                "unit": unit, "source_ref": "src:synthetic-observation"}

    cases = {
        "missing_fact": (
            req("oxygen_regime", "aerobic"), [],
            "condition_unknown", "unknown"),
        "same_known_present": (
            req("oxygen_regime", "aerobic"),
            [fact("oxygen_regime", "aerobic")],
            "compatible", "satisfied"),
        "opposite_known_present": (
            req("oxygen_regime", "aerobic"),
            [fact("oxygen_regime", "anaerobic")],
            "essential_conflict", "conflict"),
        "same_known_absent": (
            req("oxygen_regime", "aerobic"),
            [fact("oxygen_regime", "aerobic", "known_absent")],
            "essential_conflict", "conflict"),
        "other_known_absent": (
            req("oxygen_regime", "aerobic"),
            [fact("oxygen_regime", "anaerobic", "known_absent")],
            "condition_unknown", "unknown"),
        "numeric_known_absent": (
            req("temperature_C", "20-30", unit="C"),
            [fact("temperature_C", 25, "known_absent", "C")],
            "condition_unknown", "unknown"),
        "entity_other_known_absent": (
            req("electron_acceptor", "O2"),
            [fact("electron_acceptor", "NO3", "known_absent")],
            "condition_unknown", "unknown"),
        "canonical_unit_positive": (
            req("temperature_C", "20-30", unit="C"),
            [fact("temperature_C", 25, unit="C")],
            "compatible", "satisfied"),
        "unit_unknown": (
            req("temperature_C", "20-30", unit="C"),
            [fact("temperature_C", 25)],
            "condition_unknown", "unknown"),
        "unit_mismatch_K": (
            req("temperature_C", "20-30", unit="C"),
            [fact("temperature_C", 30, unit="K")],
            "condition_unknown", "unknown"),
        "unit_noncanonical_F": (
            req("temperature_C", "20-30", unit="C"),
            [fact("temperature_C", 25, unit="F")],
            "condition_unknown", "unknown"),
        "conflicting_facts_conflict_first": (
            req("oxygen_regime", "aerobic"),
            [fact("oxygen_regime", "anaerobic"),
             fact("oxygen_regime", "aerobic")],
            "condition_unknown", "unknown"),
        "conflicting_facts_satisfied_first": (
            req("oxygen_regime", "aerobic"),
            [fact("oxygen_regime", "aerobic"),
             fact("oxygen_regime", "anaerobic")],
            "condition_unknown", "unknown"),
        "necessity_no_source": (
            req("oxygen_regime", "aerobic", source_refs=[]),
            [fact("oxygen_regime", "anaerobic")],
            "condition_unknown", "unknown"),
        "zero_point_present": (
            req("temperature_C", "0", unit="C"),
            [fact("temperature_C", 0, unit="C")],
            "compatible", "satisfied"),
        "negative_interval_present": (
            req("temperature_C", "-5-10", unit="C"),
            [fact("temperature_C", 0, unit="C")],
            "compatible", "satisfied"),
        "dict_interval_present": (
            req("temperature_C", "20-30", unit="C"),
            [fact("temperature_C", {"lo": 22, "hi": 26}, unit="C")],
            "compatible", "satisfied"),
        "matrix_label_unresolved": (
            req("matrix", "soil"),
            [fact("matrix", "activated_sludge")],
            "condition_unknown", "unknown"),
        "required_absent_fact_absent": (
            req("oxygen_regime", "aerobic", status="known_absent"),
            [fact("oxygen_regime", "aerobic", "known_absent")],
            "requirement_status_not_representable", None),
        "required_absent_fact_present": (
            req("oxygen_regime", "aerobic", status="known_absent"),
            [fact("oxygen_regime", "aerobic")],
            "requirement_status_not_representable", None),
    }
    return cases[name]


_FROZEN_REASON_SNIPPETS = {
    "other_known_absent": "other_value_known_absent_not_determining",
    "numeric_known_absent": "numeric_absence_semantics_undefined",
    "entity_other_known_absent": "entity_not_among_known_facts",
    "unit_unknown": "source_unit_unknown",
    "unit_mismatch_K": "unit_mismatch",
    "unit_noncanonical_F": "unit_mismatch",
    "conflicting_facts_conflict_first":
        "conflicting_applicable_facts",
    "conflicting_facts_satisfied_first":
        "conflicting_applicable_facts",
    "necessity_no_source": "necessity_unsourced_not_gating",
    "zero_point_present": "point_match",
    "negative_interval_present": "within_range",
    "dict_interval_present": "within_range",
    "matrix_label_unresolved": "matrix_value_unresolved",
    "same_known_absent": "required_value_known_absent",
    "opposite_known_present": "value_mismatch",
}


@pytest.mark.parametrize("name", [
    "missing_fact", "same_known_present", "opposite_known_present",
    "same_known_absent", "other_known_absent", "numeric_known_absent",
    "entity_other_known_absent", "canonical_unit_positive",
    "unit_unknown", "unit_mismatch_K", "unit_noncanonical_F",
    "conflicting_facts_conflict_first",
    "conflicting_facts_satisfied_first", "necessity_no_source",
    "zero_point_present", "negative_interval_present",
    "dict_interval_present", "matrix_label_unresolved",
    "required_absent_fact_absent", "required_absent_fact_present",
])
def test_s5a02_condition_classification_matches_frozen_source(
        name: str) -> None:
    """S5A-02:20 条件案(评审 conditions 探针同案)逐案与冻结同源
    评估一致 —— 5 同义正控保持(父基线同分类值)、13 分歧案翻转为
    冻结结果、2 required_absent 单列 not_representable(不伪称冻结
    矛盾)。断言公共分类器:父基线上 5 正控仍绿、15 反例真实红。"""
    requirement, facts, expected, _frozen_status = _condition_case(name)
    assert classify_condition_requirement(requirement, facts) == expected


def test_s5a02_frozen_reasons_and_mapping_disclosures() -> None:
    """S5A-02 机读面:逐案携带冻结 reason 码(单位三态/absence/多
    事实/necessity)与 frozen_status;2 required_absent 案的披露
    kind 单列 requirement_status_not_representable。"""
    for name, snippet in _FROZEN_REASON_SNIPPETS.items():
        requirement, facts, _expected, _frozen = _condition_case(name)
        result = _detailed(requirement, facts)
        assert snippet in result["reason"], name
        assert result["classification"] == _expected, name
    # 2 required_absent 案:单列 not_representable + 唯一披露 kind
    for name in ("required_absent_fact_absent",
                 "required_absent_fact_present"):
        requirement, facts, expected, frozen_status = \
            _condition_case(name)
        result = _detailed(requirement, facts)
        assert result["classification"] == expected
        assert result["frozen_status"] is None
        assert frozen_status is None
        kinds = [d["kind"] for d in result["mapping_disclosures"]]
        assert kinds == ["requirement_status_not_representable"]
    # 冻结状态码逐案对齐(18 可比案)
    for name in ("missing_fact", "same_known_present",
                 "opposite_known_present", "same_known_absent",
                 "other_known_absent", "numeric_known_absent",
                 "entity_other_known_absent", "canonical_unit_positive",
                 "unit_unknown", "unit_mismatch_K", "unit_noncanonical_F",
                 "conflicting_facts_conflict_first",
                 "conflicting_facts_satisfied_first",
                 "necessity_no_source", "zero_point_present",
                 "negative_interval_present", "dict_interval_present",
                 "matrix_label_unresolved"):
        requirement, facts, _expected, frozen_status = \
            _condition_case(name)
        result = _detailed(requirement, facts)
        assert result["frozen_status"] == frozen_status, name


def test_s5a02_unsupported_key_and_fact_disclosures() -> None:
    """S5A-02 缺表示能力机读披露:冻结键集外的键 ⇒
    condition_unsupported_key;无法表示的事实条目 ⇒ 跳过 + 披露
    (该键缺事实 ⇒ 冻结侧 unknown,不静默删也不判冲突)。"""
    unsupported = classify_condition_requirement(
        condition_scope("redox_regime", "anaerobic"),
        [{"key": "oxygen_regime", "value": "aerobic",
          "status": "known_present"}])
    assert unsupported == "condition_unsupported_key"
    result = _detailed(
        condition_scope("redox_regime", "anaerobic"), [])
    assert result["mapping_disclosures"][0]["kind"] == \
        "condition_key_not_representable"
    # 事实条目无法表示(oxygen 枚举外的值)⇒ 跳过 + 机读披露
    facts = [{"key": "oxygen_regime", "value": "microaerobic",
              "status": "known_present"}]
    result = _detailed(
        condition_scope("oxygen_regime", "aerobic"), facts)
    assert result["classification"] == "condition_unknown"
    kinds = [d["kind"] for d in result["mapping_disclosures"]]
    assert "condition_fact_not_representable" in kinds
    # 非区间键非字符串值 ⇒ 要求侧无表示 ⇒ unknown + 披露
    result = _detailed(
        {**condition_scope("matrix", ""), "value_or_interval": 3}, [])
    assert result["classification"] == "condition_unknown"
    assert result["mapping_disclosures"][0]["kind"] == \
        "requirement_value_not_representable"
    # 要求侧非规范单位(首版无换算)⇒ 机读披露 + unknown 族
    result = _detailed(
        {**condition_scope("temperature_C", "20-30"), "unit": "K"}, [])
    assert result["classification"] == "condition_unknown"
    assert result["mapping_disclosures"][0]["kind"] == \
        "requirement_unit_noncanonical"


def test_s5a02_preference_and_scenario_axes_kept() -> None:
    """S5A-02 轴保持:preference 不满足(经同源值轴,永不门禁)与
    场景转换分桶保留;preference 满足 ⇒ compatible。"""
    facts = [{"key": "oxygen_regime", "value": "aerobic",
              "status": "known_present"}]
    preference = classify_condition_requirement(
        condition_scope("oxygen_regime", "anaerobic",
                        required="preference"), facts)
    assert preference == "preference_unsatisfied"
    satisfied_preference = classify_condition_requirement(
        condition_scope("oxygen_regime", "aerobic",
                        required="preference"), facts)
    assert satisfied_preference == "compatible"
    changed = classify_condition_requirement(
        {**condition_scope("oxygen_regime", "aerobic"),
         "subject_scenario_ref": "scenario:phase-2"},
        [{**facts[0], "subject_scenario_ref": "scenario:phase-1"}])
    assert changed == "scenario_transition_changed"


def test_s5a02_end_to_end_buckets_with_frozen_reasons(
        tmp_path: Path) -> None:
    """S5A-02 端到端:真实 public 链上,同键两条相反事实(多事实保守
    unknown)、温度单位不匹配 ⇒ condition_unknown(不再是
    essential_conflict/compatible);分类 details 携带冻结 reason 码。"""
    plan = _plan(select=1)
    plan["condition_facts"] = [
        {"key": "oxygen_regime", "value": "anaerobic",
         "status": "known_present", "source_ref": "src:synthetic"},
        {"key": "oxygen_regime", "value": "aerobic",
         "status": "known_present", "source_ref": "src:synthetic-2"},
        {"key": "temperature_C", "value": 30, "status": "known_present",
         "unit": "K", "source_ref": "src:synthetic"},
    ]
    runs_root, out = _run(tmp_path, "s5a02-e2e", plan)
    digest = out["native_export"]["export_digest"]
    graph = synth_reference_graph(graph_id="rg-s5a02-e2e")
    graph["edges"] = graph["edges"][:1]
    graph["edges"][0]["condition_requirements"] = [
        condition_scope("oxygen_regime", "aerobic"),
        {**condition_scope("temperature_C", "20-30"), "unit": "C"},
    ]
    for node in graph["nodes"]:
        node["condition_scope"] = []
    output = _evaluate_graph(tmp_path, "s5a02-e2e", digest, graph)
    conflicts = output["sample_results"][0]["environment_conflicts"]
    buckets = conflicts["buckets"]
    # 多事实矛盾(anaerobic + aerobic)⇒ 保守 unknown,不首条说了算;
    # 温度 K 对要求 20-30 C ⇒ 单位不匹配 unknown,不假相容
    assert buckets.get("condition_unknown") == 2
    assert buckets.get("essential_conflict", 0) == 0
    assert buckets.get("compatible", 0) == 0
    reasons = {d["key"]: d["reason"]
               for d in conflicts["details"]}
    assert "conflicting_applicable_facts" in \
        reasons["oxygen_regime"]
    assert "unit_mismatch" in reasons["temperature_C"]


# ------------------------------------------------- S5A-04 persist boundary


def test_s5a04_persist_resolved_path_authorization(
        tmp_path: Path) -> None:
    """S5A-04:核验与写入同一解析后实际规范路径 —— 错 cwd 相对路径
    解析逃根 ⇒ 先拒零新文件;不回退原字符串授权(评审五案之一)。"""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    declared = tmp_path / "declared_repo"
    declared.mkdir()
    original = Path.cwd()
    try:
        import os
        os.chdir(elsewhere)
        target = Path("reports/phase_s1_hit60/dev_gold/report.json")
        with pytest.raises(EvaluationContractError) as excinfo:
            persist_evaluation_output(
                {"status": "interface_verified_only",
                 "payload": "synthetic-placeholder-not-gold"},
                target, contains_gold=True, repo_root=declared)
        assert excinfo.value.detail["kind"] == \
            "gold_content_outside_declared_root"
        assert excinfo.value.detail["resolved_target"] == \
            str(target.resolve())
        # 零新文件/目录:解析后的越界路径不存在
        assert not target.resolve().exists()
        assert not (elsewhere / "reports").exists()
    finally:
        os.chdir(original)


def test_s5a04_persist_symlink_escape_refused(tmp_path: Path) -> None:
    """S5A-04:授权名目录为 symlink 指向根外 ⇒ 相对/绝对 target 实际
    逃根均先拒(零新文件);合法根内相对正控接受且回执=实际路径。"""
    import os
    declared = tmp_path / "declared_repo"
    declared.mkdir()
    external = tmp_path / "external_target"
    external.mkdir()
    link = declared / "reports" / "phase_s1_hit60" / "dev_gold"
    link.parent.mkdir(parents=True)
    link.symlink_to(external, target_is_directory=True)
    output = {"status": "interface_verified_only",
              "payload": "synthetic-placeholder-not-gold"}
    original = Path.cwd()
    try:
        os.chdir(declared)
        # 相对 target 经 symlink 逃根 ⇒ 拒
        relative = Path("reports/phase_s1_hit60/dev_gold/report.json")
        with pytest.raises(EvaluationContractError) as excinfo:
            persist_evaluation_output(
                output, relative, contains_gold=True, repo_root=declared)
        assert excinfo.value.detail["kind"] == \
            "gold_content_outside_declared_root"
        assert not relative.resolve().exists()
        assert list(external.iterdir()) == []  # 外部目录零新文件
        # 绝对 target(parent 即 symlink)⇒ 同样先拒
        absolute = declared / "reports/phase_s1_hit60/dev_gold" \
            "/abs_link.json"
        with pytest.raises(EvaluationContractError) as excinfo:
            persist_evaluation_output(
                output, absolute, contains_gold=True,
                repo_root=declared)
        assert excinfo.value.detail["kind"] == \
            "gold_content_outside_declared_root"
        assert not absolute.resolve().exists()
        # 绝对路径在根外(非 symlink)⇒ 拒
        with pytest.raises(EvaluationContractError) as excinfo:
            persist_evaluation_output(
                output, tmp_path / "elsewhere" / "reports" /
                "phase_s1_hit60/dev_gold/abs.json",
                contains_gold=True, repo_root=declared)
        assert excinfo.value.detail["kind"] == \
            "gold_content_outside_declared_root"
        # 合法正控:声明根内授权相对路径 ⇒ 接受,回执=实际写入路径
        normal = tmp_path / "normal_fake_repo"
        normal.mkdir()
        os.chdir(normal)
        good = Path("reports/phase_s1_hit60/dev_gold/good.json")
        receipt = persist_evaluation_output(
            output, good, contains_gold=True, repo_root=normal)
        assert receipt["path"] == str(good.resolve())
        assert good.resolve().is_file()
        assert receipt["sha256"]
    finally:
        os.chdir(original)


def test_s5a04_persist_no_root_refused_and_plain_write_kept(
        tmp_path: Path) -> None:
    """S5A-04 根规则:未声明 repo_root 的含金标写入一律拒(根规则
    明确,不做未解析路径名授权);根内非授权路径拒;普通非敏感写入
    保持原行为。"""
    output = {"status": "interface_verified_only",
              "payload": "synthetic"}
    plain = tmp_path / "out" / "report.json"
    with pytest.raises(EvaluationContractError) as excinfo:
        persist_evaluation_output(output, plain, contains_gold=True)
    assert excinfo.value.detail["kind"] == "gold_content_root_required"
    assert not plain.exists()
    repo_root = tmp_path / "repo"
    inside_plain = repo_root / "docs" / "report.json"
    with pytest.raises(EvaluationContractError) as excinfo:
        persist_evaluation_output(
            output, inside_plain, contains_gold=True,
            repo_root=repo_root)
    assert excinfo.value.detail["kind"] == \
        "gold_content_unauthorized_path"
    assert not inside_plain.exists()
    # 普通非敏感写入(非金标)保持:写调用方给定路径
    normal = persist_evaluation_output(output, plain)
    assert normal["path"] == str(plain)
    assert plain.is_file()


# ------------------------------------------------------- 契约版本登记


def test_s5a_rework_contract_version_registration() -> None:
    """S5a 回修 r1→r2:评测契约 -2→-3、预注册模板 -2→-3、profile
    -21→-22(匹配/分类/写侧语义变更不偷换同一已登记契约;criteria-v1
    冻结正文不受影响;r2 只登记 S5A-02 单位收口与 B2 文案纠错)。"""
    assert PPV1_EVALUATION_VERSION == "ppv1-evaluation-3"
    assert PPV1_PREREGISTRATION_TEMPLATE_VERSION == \
        "ppv1-preregistration-template-3"
    assert PPV1_PROFILE_SCHEMA_VERSION == "ppv1-profile-22"
    template = preregistration.build_preregistration_template()
    # proposed 文本与实现证明范围同步(仍 proposed,不冻结)
    assert "identity_scope=cn_only/partial/unknown" in template[
        "identity_matching_policy"]["rule"]
    assert "状态集合" in template["edge_matching_policy"]["rule"]
    assert "冻结同源规则" in template["condition_policy"]["rule"]
    # S5a 回修 r2:condition_policy 与单位收口实现同真
    assert "无合法冻结表示" in template["condition_policy"]["rule"]
    assert "canonical-by-key 默认合法" in template[
        "condition_policy"]["rule"]
    assert "同键相反事实保守 unknown" in template[
        "condition_policy"]["rule"]
    assert "同一解析后实际规范路径" in template[
        "output_write_boundary_policy"]["rule"]
    assert template["identity_matching_policy"]["status"] == \
        "PROPOSED_NOT_FROZEN"
