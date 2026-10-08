"""S5a 评测器端到端回归(真实链路合成 run → S4 公开导出入口 →
确定性零 LLM 评测;S5 任务书 §8/§9/§11/§12 + 验收矩阵 S5-02~S5-20/
S5-24/S5-25/S5-28 + §14.1 行为点)。

夹具纪律:合成 run 走公共 ``start_run``(S3b 起开放的 PPV1 执行流)
真实生成,导出经 ``read_native_export`` 首消费读取(不造假导出对象);
参考图为合成规则级(无金标/题面)。全部数字是合成规则级接口结果,
不外推 dev/298,不构成科学性能声明。

覆盖:
- native export 消费契约(§3.1):reader 走 ledger 首消费;导出缺席
  /读不到 ⇒ 样本级披露 + pending(S5-28);lossy 投影不参与完整语义
  科学指标;
- S5-02 备选不合并 / S5-03 共同产物不被报告 K 删 / S5-04 distinct
  occurrence 不按 CN 合并;
- S5-05 同研究多记录一组 / S5-06 independence unknown 不进独立分母;
- S5-07 同 source group 跨集合 leakage 阻断 / S5-08 known-unseen 直接
  证据重叠阻断;
- S5-09 未画出的参考边 → reference coverage 限制,不自动判错;
- S5-10 严格身份与中心证据分轴 / S5-11 CN 相同不计严格命中;
- S5-12 step_scope 分轴;S5-13/14/15 条件 unknown/conflict/来源条件
  保留;S5-16 unknown/partial 不计 confirmed 不计错误;
- S5-17 矿化负控 / S5-18 停止原因不是终点 / S5-19 unresolved 依赖不
  被 recorded 洗白 / S5-20 预算漏展开单独报告;
- S5-24 同输入重复评测确定性一致(含输出 hash);S5-25 零 LLM/
  自然语言不改变程序结果。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant import preregistration  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    EvaluationContractError,
    budget_omission_from_export,
    check_endpoint_claims,
    classify_condition_requirement,
    evaluate_scientific,
    match_reference_nodes,
    native_export_reader_from_ledger,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    PPV1_NATIVE_EXPORT_VERSION,
)
from pathway_v43.pollutant.search import SearchLedger  # noqa: E402
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402
from pathway_v43.storage.run_identity import (  # noqa: E402
    PROFILE_POLLUTANT_PATHWAY_V1,
)
from pathway_v43.workflow.runner import start_run  # noqa: E402

from test_ppv1_s4a_endpoint import (  # noqa: E402
    mineralization_evidence,
    oxygen_req,
    spec,
)
from test_ppv1_s5a_schema import (  # noqa: E402
    condition_scope,
    synth_evaluation_input,
    synth_reference_graph,
    synth_split_manifest,
)



def _plan(*, with_mineralization: bool = False,
          with_unresolved_dependency: bool = False,
          select: int = 2) -> dict:
    plan = {
        "condition_facts": [{
            "key": "oxygen_regime", "value": "aerobic",
            "status": "known_present", "source_ref": "src:synthetic"}],
        "pools": {"CCO": [
            spec("B", "CC=O", "donor-B", coproducts=["[H][H]"]),
            spec("C", "CC=O", "donor-C",
                 dependencies=(
                     [{"dependency_id": "dep-NAD",
                       "kind": "cosubstrate_supply",
                       "statement": "NAD+ cycle",
                       "cyclic": True,
                       "initial_supply": "missing"}]
                     if with_unresolved_dependency else None))]},
        "schedule_budget": {"max_select": select},
        "endpoint_evidence": (
            [mineralization_evidence()] if with_mineralization else []),
    }
    return plan


def _run(tmp_path: Path, run_id: str, plan: dict) -> tuple[Path, dict]:
    out = start_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_id, smiles="CCO", max_depth=3, max_expansions=10,
        max_frontier_width=2, finder=object(), scripted=True,
        profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    return tmp_path / "runs", out


def _reader(runs_root: Path, run_id: str):
    store = PollutantPathwayStore(runs_root / run_id / "pollutant.sqlite")
    artifacts = ArtifactStore(runs_root, run_id)
    ledger = SearchLedger(store, artifacts, run_id)
    return native_export_reader_from_ledger(
        ledger, runs_root / run_id)


def _evaluate(tmp_path: Path, run_id: str, plan: dict, *,
              graph: dict | None = None,
              split_manifest: dict | None = None,
              provider: dict | None = None,
              extra: dict | None = None,
              interface: bool = True):
    runs_root, out = _run(tmp_path, run_id, plan)
    digest = out["native_export"]["export_digest"]
    graph = graph if graph is not None else synth_reference_graph()
    evaluation_input = synth_evaluation_input(
        graphs=[graph], split_manifest=split_manifest,
        exports=[{"run_id": run_id, "export_digest": digest}],
        provider=provider, interface=interface, extra=extra)
    evaluation_input["run_identity"]["run_id"] = run_id
    output = evaluate_scientific(
        evaluation_input,
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=_reader(runs_root, run_id),
        preregistration=preregistration.build_preregistration_template())
    return output, out


def _sample(output: dict) -> dict:
    assert len(output["sample_results"]) == 1
    return output["sample_results"][0]


def _edge(sample: dict, edge_id: str) -> dict:
    return next(entry for entry in sample["predicted_edge_matches"]
                if entry["edge_id"] == edge_id)


# ----------------------------------------------- native export 消费契约


def test_native_export_consumed_via_public_entry(tmp_path: Path) -> None:
    """§3.1:导出经 read_native_export 首消费读取(真实链路产物,
    非造假对象);输出携带 §8.2 全字段与输出 hash。"""
    output, out = _evaluate(tmp_path, "s5a-consume", _plan())
    sample = _sample(output)
    assert sample["scoring_status"] == "scored"
    assert sample["scoring_errors"] == []
    # §8.2 输出字段
    for field in ("evaluator_schema_version", "evaluation_id",
                  "run_identity", "domain", "track", "split",
                  "sample_results", "aggregate_metrics",
                  "uncertainty_intervals", "coverage_report",
                  "missingness_report", "budget_omission_report",
                  "leakage_checks", "invalid_input_count",
                  "scoring_provenance", "status", "output_sha256"):
        assert field in output, field
    for field in ("sample_id", "root_entity_id", "source_group_ids",
                  "predicted_node_matches", "predicted_edge_matches",
                  "key_intermediate_matches", "false_or_unverified_edges",
                  "environment_conflicts", "endpoint_claim_checks",
                  "mineralization_claim_checks", "depth_metrics",
                  "budget_omission", "unknown_or_partial_summary",
                  "scoring_status"):
        assert field in sample, field
    # 消费的是真实导出(导出 digest 与 run 一致)
    assert output["scoring_provenance"]["network_request_count"] == 0
    assert output["scoring_provenance"]["llm_in_scoring"] is False


def test_s5_28_unreadable_export_disclosed(tmp_path: Path) -> None:
    """S5-28:导出 digest 不存在 ⇒ 读取失败结构化披露,不冒充已评。"""
    runs_root, out = _run(tmp_path, "s5a-missing", _plan())
    graph = synth_reference_graph()
    evaluation_input = synth_evaluation_input(
        graphs=[graph],
        exports=[{"run_id": "s5a-missing",
                  "export_digest": "0" * 64}])
    output = evaluate_scientific(
        evaluation_input,
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=_reader(runs_root, "s5a-missing"),
        preregistration=preregistration.build_preregistration_template())
    assert output["status"] == "pending_no_independent_data"
    assert _sample(output)["scoring_status"] == \
        "not_evaluated_export_missing"
    assert output["export_read_errors"]
    assert output["export_read_errors"][0]["kind"] == \
        "native_export_unreadable"


def test_lossy_projection_not_scorable(tmp_path: Path) -> None:
    """§3.1:v3 有损投影不得用于完整路径语义科学指标(结构化披露)。"""
    graph = synth_reference_graph()
    evaluation_input = synth_evaluation_input(graphs=[graph], exports=[{
        "run_id": "synth", "export_digest": "d1",
        "lossy_projection": True,
        "native_reference": "native:d1",
        "lost_fields": ["route_origins", "coproducts"]}])
    output = evaluate_scientific(
        evaluation_input,
        reference_graphs={graph["reference_graph_id"]: graph},
        preregistration=preregistration.build_preregistration_template())
    assert output["status"] == "pending_no_independent_data"
    error = output["export_read_errors"][0]
    assert error["kind"] == "lossy_projection_not_scorable"
    assert "完整路径语义" in error["note"]


# ----------------------------------------------- S5-02/03/04 匹配语义


def test_s5_02_alternatives_not_merged(tmp_path: Path) -> None:
    """S5-02:A→B 与 A→C 两个备选反应:两条边各自匹配独立事件,不
    合并成 B+C 单一事件;共同产物/无共同产物两条备选分开。"""
    output, _ = _evaluate(tmp_path, "s5a-alt", _plan())
    sample = _sample(output)
    edge1 = _edge(sample, "e-alt-1")
    edge2 = _edge(sample, "e-alt-2")
    assert edge1["match_status"] == "matched_strict"
    assert edge2["match_status"] == "matched_strict"
    # 两条备选边匹配不同事件(不合并):带共同产物的 B 与不带共同
    # 产物的 C 各自精确匹配对应参考边
    assert edge1["matched_events"][0]["event_id"] != \
        edge2["matched_events"][0]["event_id"]
    # 非精确覆盖(同父另一备选/缺共同产物)单独披露,不计严格匹配
    for entry in (edge1, edge2):
        for mismatch in entry["coverage_mismatch_events"]:
            assert mismatch["participant_coverage"] in (
                "superset", "partial_subset")
            assert "共" in entry["coproduct_preserved_note"]


def test_s5_03_coproduct_not_deleted_by_report_k(tmp_path: Path) -> None:
    """S5-03:A 裂解共同生成 B+C:完整事件含 B、C;报告 K/展开宽度
    不删 C —— 匹配条目携带共同产物参与物。"""
    output, _ = _evaluate(tmp_path, "s5a-coprod", _plan())
    sample = _sample(output)
    edge1 = _edge(sample, "e-alt-1")
    # [H][H] 共同产物保留在匹配事件的完整参与物里(报告 K/展开宽度
    # 不删 C)
    assert edge1["matched_events"][0]["coproduct_participants"]
    # 参考边共同产物参与物覆盖(参考侧 coproduct 节点被严格匹配)
    coproduct_match = next(
        entry for entry in sample["predicted_node_matches"]
        if entry["role"] == "coproduct")
    assert coproduct_match["match_status"] == "strict_structure"
    # 缺共同产物的备选事件只进覆盖失配披露(参考声明共同产物完整)
    partial = [m for m in edge1["coverage_mismatch_events"]
               if m["participant_coverage"] == "partial_subset"] or \
        [m for m in _edge(sample, "e-alt-2")[
            "coverage_mismatch_events"]
         if m["participant_coverage"] == "partial_subset"]
    assert partial
    assert partial[0]["coproduct_participants"] == []


def test_s5_04_distinct_occurrence_not_merged_by_cn(tmp_path: Path) -> None:
    """S5-04:不同来路生成同一结构 ⇒ distinct occurrence 保留,不按
    CN 或结构首现合并:两个参考 occurrence 各自条目、各自匹配。"""
    output, _ = _evaluate(tmp_path, "s5a-occ", _plan())
    sample = _sample(output)
    cco_matches = [entry for entry in sample["predicted_node_matches"]
                   if entry["node_id"].startswith("n-int-occ")]
    assert len(cco_matches) == 2  # 两个 occurrence 条目保留
    assert {entry["occurrence_id"] for entry in cco_matches} == {
        "occ-cco-a", "occ-cco-b"}
    # 两个 occurrence 均严格命中(同 state,但条目不合并)
    assert all(entry["match_status"] == "strict_structure"
               for entry in cco_matches)
    occurrences = [entry for entry in sample["predicted_node_matches"]
                   if entry["role"] == "root"]
    assert len(occurrences) == 1


def test_s5_05_same_study_records_one_group(tmp_path: Path) -> None:
    """S5-05:同一研究多条数据库记录 ⇒ 只计一个 source group,不虚增
    独立支持(泄漏检查记账:记录数 vs 组数)。"""
    output, _ = _evaluate(tmp_path, "s5a-group", _plan())
    stats = output["leakage_checks"]["statistics"]
    assert stats["source_group_count"] == 2   # sg-study-A + sg-study-B
    assert stats["database_record_count"] == 3  # 2+1 条记录
    assert "只计一个" in stats["record_to_group_ratio_note"]
    assert stats["unknown_independence_groups"] == []


def test_s5_06_unknown_independence_not_counted(tmp_path: Path) -> None:
    """S5-06:研究身份未知 ⇒ independence=unknown,不进入要求独立支持
    的指标分母(披露,非违规)。"""
    graph = synth_reference_graph(source_groups_override=[
        {"source_group_id": "sg-study-A",
         "independence_status": "unknown",
         "member_records": ["db:1", "db:2", "db:3"],
         "note": "研究身份未知"},
        {"source_group_id": "sg-study-B",
         "independence_status": "independent",
         "member_records": ["rhea:2001"],
         "note": "独立研究 B"},
    ])
    output, _ = _evaluate(
        tmp_path, "s5a-unknown-indep", _plan(), graph=graph)
    stats = output["leakage_checks"]["statistics"]
    assert stats["unknown_independence_groups"] == ["sg-study-A"]
    assert stats["source_group_count"] == 2
    assert stats["database_record_count"] == 4
    assert "不进入" in stats["unknown_independence_note"]


# ----------------------------------------------- S5-07/08 泄漏阻断


def test_s5_07_source_group_across_splits_blocks(tmp_path: Path) -> None:
    """S5-07:同研究相邻边跨开发/留出 ⇒ leakage 检查失败并阻止正式
    评测(blocked_leakage;零聚合)。"""
    graph_a = synth_reference_graph("rg-synth-1")
    graph_b = synth_reference_graph("rg-synth-2")
    split_manifest = synth_split_manifest()
    # rg-synth-2 整体划入 held_out,但携带同一 source group sg-study-A
    # ⇒ 同研究相邻边跨开发/留出集合
    split_manifest["assignments"].extend([
        {"reference_graph_id": "rg-synth-2",
         "source_group_id": "sg-study-A", "split": "held_out"},
        {"reference_graph_id": "rg-synth-2",
         "source_group_id": "sg-study-B", "split": "held_out"},
    ])
    runs_root, out = _run(tmp_path, "s5a-leak", _plan())
    digest = out["native_export"]["export_digest"]
    evaluation_input = synth_evaluation_input(
        graphs=[graph_a, graph_b], split_manifest=split_manifest,
        exports=[{"run_id": "s5a-leak", "export_digest": digest}])
    evaluation_input["run_identity"]["run_id"] = "s5a-leak"
    output = evaluate_scientific(
        evaluation_input,
        reference_graphs={"rg-synth-1": graph_a,
                          "rg-synth-2": graph_b},
        native_export_reader=_reader(runs_root, "s5a-leak"),
        preregistration=preregistration.build_preregistration_template())
    assert output["status"] == "blocked_leakage"
    violation = output["leakage_checks"]["violations"][0]
    assert violation["check"] == "source_group_across_splits"
    assert violation["source_group_id"] == "sg-study-A"
    assert sorted(violation["splits"]) == ["development", "held_out"]
    assert output["aggregate_metrics"] == []  # 阻断 ⇒ 零聚合


def test_s5_08_known_unseen_overlap_blocks(tmp_path: Path) -> None:
    """S5-08:known 与 unseen 直接证据重叠 ⇒ unseen exclusion 检查
    失败,不继续聚合。"""
    graph = synth_reference_graph()
    split_manifest = synth_split_manifest(excluded=[
        {"source_group_id": "sg-study-A", "scope": "exact_edge",
         "reason": "直接对应反应证据被排除"}])
    output, _ = _evaluate(
        tmp_path, "s5a-overlap", _plan(), graph=graph,
        split_manifest=split_manifest)
    assert output["status"] == "blocked_leakage"
    violation = output["leakage_checks"]["violations"][0]
    assert violation["check"] == "unseen_exclusion_overlaps_known_evaluation"
    assert "sg-study-A" in violation["source_group_ids"]
    assert output["aggregate_metrics"] == []


# ----------------------------------------------- S5-09 覆盖不足


def test_s5_09_unpainted_reference_edge_coverage_limit(
        tmp_path: Path) -> None:
    """S5-09:未画出的参考边 ⇒ 不自动判模型错误,计入 reference
    coverage 限制;未标记的未匹配边单独分桶。"""
    extra_edges = [
        {   # 标记为不可评(参考图覆盖不足)
            "edge_id": "e-gap", "from_node_ids": ["n-int-occ-a"],
            "to_node_ids": ["n-coproduct-h2"],
            "transformation_ref": "tref-gap",
            "transformation_signature_status": "unknown",
            "participants": [
                {"node_id": "n-int-occ-a", "side": "reactant",
                 "role": "primary_substrate", "coefficient": 1,
                 "coefficient_status": "known"},
                {"node_id": "n-coproduct-h2", "side": "product",
                 "role": "principal_product", "coefficient": 1,
                 "coefficient_status": "known"}],
            "participant_list_status": "unknown",
            "coefficient_status": "unknown",
            "step_scope": "unknown",
            "condition_requirements": [],
            "scenario_scope": "scenario:synth-aerobic",
            "provenance_refs": ["pv-1"],
            "source_group_refs": ["sg-study-A"],
            "evidence_basis": "reference_only",
            "edge_status": "reference_only",
        },
    ]
    graph = synth_reference_graph(
        extra_edges=extra_edges,
        coverage_override={
            "covered_axes": ["nodes", "edges"],
            "known_gaps": ["gap:deep-oxidation"],
            "not_evaluable_node_ids": [],
            "not_evaluable_edge_ids": ["e-gap"],
        })
    output, _ = _evaluate(tmp_path, "s5a-gap", _plan(), graph=graph)
    sample = _sample(output)
    assert _edge(sample, "e-gap")["match_status"] == \
        "unmatched_reference_coverage"
    # 未匹配不进误确认/错误桶(coverage 限制分桶)
    metric = next(m for m in output["aggregate_metrics"]
                  if m["metric_id"] == "reference_edge_recall")
    assert metric["buckets"].get("unmatched_reference_coverage") == 1
    assert "e-gap" in output["coverage_report"][
        "not_evaluable_edges_per_graph"]["rg-synth-1"]
    assert output["coverage_report"]["known_gaps_per_graph"][
        "rg-synth-1"] == ["gap:deep-oxidation"]


def test_s5_20_budget_unexpanded_edge_separate_bucket(
        tmp_path: Path) -> None:
    """S5-20/S5-18:预算导致未展开的参考边单独分桶(不判错、不静默
    从分母删除);停止原因 budget_limit 披露,不计化学错误。"""
    extra_edges = [
        {   # 未标记覆盖不足的未匹配边(run 停在 budget_limit)
            "edge_id": "e-beyond", "from_node_ids": ["n-int-occ-b"],
            "to_node_ids": ["n-coproduct-h2"],
            "transformation_ref": "tref-beyond",
            "transformation_signature_status": "unknown",
            "participants": [
                {"node_id": "n-int-occ-b", "side": "reactant",
                 "role": "primary_substrate", "coefficient": 1,
                 "coefficient_status": "known"},
                {"node_id": "n-coproduct-h2", "side": "product",
                 "role": "principal_product", "coefficient": 1,
                 "coefficient_status": "known"}],
            "participant_list_status": "unknown",
            "coefficient_status": "unknown",
            "step_scope": "unknown",
            "condition_requirements": [],
            "scenario_scope": "scenario:synth-aerobic",
            "provenance_refs": ["pv-2"],
            "source_group_refs": ["sg-study-B"],
            "evidence_basis": "reference_only",
            "edge_status": "reference_only",
        },
    ]
    output, _ = _evaluate(
        tmp_path, "s5a-budget", _plan(), graph=synth_reference_graph(
            extra_edges=extra_edges))
    sample = _sample(output)
    assert _edge(sample, "e-beyond")["match_status"] == \
        "unmatched_budget_unexpanded"
    budget = sample["budget_omission"]
    assert budget["stop_reason"] == "budget_limit"
    assert budget["buckets"]["action_budget"] == 1
    assert "单独报告" in budget["note"]
    assert "无声删除" in budget["note"]
    # 不计化学错误:误确认桶为空
    metric = next(m for m in output["aggregate_metrics"]
                  if m["metric_id"] == "confirmed_error_rate")
    assert metric["buckets"].get(
        "confirmed_claim_events") == 0


# ----------------------------------------------- S5-10/11/12 分轴


def test_s5_10_strict_identity_and_center_evidence_separate_axes(
        tmp_path: Path) -> None:
    """S5-10:结构严格匹配但中心证据未知 ⇒ 严格身份与中心证据分轴
    报告,不授完整确认(conditional admission 不计 confirmed)。"""
    output, _ = _evaluate(tmp_path, "s5a-axes", _plan())
    sample = _sample(output)
    strict_hits = [entry for entry in sample["predicted_node_matches"]
                   if entry["match_status"] == "strict_structure"]
    assert strict_hits  # 严格身份轴:命中
    # 中心证据轴:audit transformation_center unknown(分轴披露)
    summary = sample["unknown_or_partial_summary"]
    assert summary["conditional_admission_events"] >= 1
    assert summary["audit_unknown_checks"] >= 1
    # 不授完整确认:confirmed 为 0
    metric = next(m for m in output["aggregate_metrics"]
                  if m["metric_id"] == "confirmed_error_rate")
    assert metric["buckets"].get("confirmed_claim_events") == 0


def test_s5_11_cn_same_not_strict_hit() -> None:
    """S5-11:CN 相同但严格结构不同 ⇒ 不能计为严格结构命中(cn_only
    分桶)。合成 states 载荷为规则级匹配单元测试(对映体;CN 取与
    生产同源的 domain.identity.cn_identity 实算值)。"""
    from pathway_v43.domain.identity import cn_identity

    wrong = "F[C@@H](Cl)Br"
    right = "F[C@H](Cl)Br"
    shared_cn = cn_identity(right)
    assert shared_cn == cn_identity(wrong)  # CN 旁证轴:对映体同 CN
    wrong_enantiomer = {"states": [
        {"state_id": "cs-wrong", "payload": {
            "smiles_isomeric": wrong, "cn_identity": shared_cn}},
    ]}
    graph = synth_reference_graph()
    node = {
        "node_id": "n-chiral", "state_identity": "strict:r",
        "structure_smiles": right,
        "structure_identity_scope": "strict_structure",
        "role": "intermediate", "occurrence_id": "occ-chiral-1",
        "source_group_refs": ["sg-study-A"],
        "condition_scope": [], "provenance_refs": ["pv-1"],
        "node_status": "observed",
    }
    graph = {**graph, "nodes": graph["nodes"] + [node]}
    matches = match_reference_nodes(graph, wrong_enantiomer)
    chiral = next(entry for entry in matches
                  if entry["node_id"] == "n-chiral")
    assert chiral["match_status"] == "cn_only"  # CN 同、严格身份不同
    assert chiral["matched_state_ids"] == []
    assert chiral["cn_only_state_ids"] == ["cs-wrong"]
    # 严格结构匹配的正控:同构型节点计严格命中
    right_enantiomer = {"states": [
        {"state_id": "cs-right", "payload": {
            "smiles_isomeric": right, "cn_identity": shared_cn}},
    ]}
    matches2 = match_reference_nodes(graph, right_enantiomer)
    chiral_r = next(entry for entry in matches2
                    if entry["node_id"] == "n-chiral")
    assert chiral_r["match_status"] == "strict_structure"
    assert chiral_r["matched_state_ids"] == ["cs-right"]


def test_s5_12_step_scope_separate_axis(tmp_path: Path) -> None:
    """S5-12:step_scope 不同 ⇒ net reaction/elementary step/multistep
    summary 不混作同一边(结构匹配但 scope 不一致单独分桶)。"""
    graph = synth_reference_graph()
    for edge in graph["edges"]:
        edge["step_scope"] = "multistep_summary"  # 参考声明汇总边
    output, _ = _evaluate(tmp_path, "s5a-scope", _plan(), graph=graph)
    sample = _sample(output)
    for entry in sample["predicted_edge_matches"]:
        assert entry["match_status"] == "matched_structure_only"
        assert entry["matched_events"] == []
        for structure_event in entry["structure_only_events"]:
            assert structure_event["step_scope_consistent"] is False
            assert structure_event["event_step_scope"] == "net_reaction"
            assert structure_event["reference_step_scope"] == \
                "multistep_summary"
    metric = next(m for m in output["aggregate_metrics"]
                  if m["metric_id"] == "reference_edge_recall")
    assert metric["buckets"].get("matched_structure_only", 0) >= 2
    assert metric["buckets"].get("matched_strict", 0) == 0


# ----------------------------------------------- S5-13/14/15 条件


def test_condition_classifier_unknown_conflict_compatible() -> None:
    """S5-13/14:必要项缺失 ⇒ unknown(不报 compatible);明确 essential
    冲突 ⇒ conflict(unknown 不混入);preference 不满足单独分桶。"""
    facts = [{"key": "oxygen_regime", "value": "aerobic",
              "status": "known_present"}]
    missing = classify_condition_requirement(
        condition_scope("redox_regime", "anaerobic"), facts)
    assert missing == "condition_unknown"
    conflict = classify_condition_requirement(
        condition_scope("oxygen_regime", "anaerobic"), facts)
    assert conflict == "essential_conflict"
    compatible = classify_condition_requirement(
        condition_scope("oxygen_regime", "aerobic"), facts)
    assert compatible == "compatible"
    # S5-14:事实 known_absent(条件明确缺席)⇒ essential 冲突
    absent = classify_condition_requirement(
        condition_scope("oxygen_regime", "aerobic"),
        [{"key": "oxygen_regime", "value": "",
          "status": "known_absent"}])
    assert absent == "essential_conflict"
    unknown_fact = classify_condition_requirement(
        condition_scope("oxygen_regime", "aerobic"),
        [{"key": "oxygen_regime", "value": "anaerobic",
          "status": "unknown"}])
    assert unknown_fact == "condition_unknown"
    preference = classify_condition_requirement(
        condition_scope("oxygen_regime", "anaerobic",
                        required="preference"), facts)
    assert preference == "preference_unsatisfied"
    # 区间匹配(确定性)
    interval = classify_condition_requirement(
        condition_scope("ph", "6.5-7.5"),
        [{"key": "ph", "value": "7", "status": "known_present"}])
    assert interval == "compatible"
    # 场景转换后条件变化单独分桶
    changed = classify_condition_requirement(
        {**condition_scope("oxygen_regime", "aerobic"),
         "subject_scenario_ref": "scenario:phase-2"},
        [{"key": "oxygen_regime", "value": "aerobic",
          "status": "known_present",
          "subject_scenario_ref": "scenario:phase-1"}])
    assert changed == "scenario_transition_changed"


def test_s5_13_14_15_condition_axes_end_to_end(tmp_path: Path) -> None:
    """端到端条件轴:e-alt-1 携带 3 条要求 —— aerobic essential
    (事实 aerobic known_present ⇒ compatible)/ redox essential 缺事实
    (⇒ unknown,S5-13)/ aerobic=anaerobic essential(值冲突 ⇒
    conflict,S5-14);历史来源条件原样保留(S5-15)。"""
    output, _ = _evaluate(tmp_path, "s5a-cond", _plan())
    sample = _sample(output)
    buckets = sample["environment_conflicts"]["buckets"]
    assert buckets.get("compatible") == 2  # e-alt-1 + e-alt-2 各一条
    assert buckets.get("condition_unknown") == 1  # redox 缺事实
    assert buckets.get("essential_conflict") == 1  # aerobic=anaerobic
    # unknown 不混入冲突:两个独立分桶(unknown 不计入冲突桶)
    assert set(buckets) >= {"condition_unknown", "essential_conflict"}
    assert buckets["essential_conflict"] == 1
    assert buckets["condition_unknown"] == 1
    assert sample["environment_conflicts"]["condition_facts_consumed"] \
        == ["oxygen_regime"]
    # S5-15:历史来源条件(30C)原样保留,不改写为当前场景事实
    preserved = sample["environment_conflicts"][
        "source_conditions_preserved"]
    assert preserved == [{
        "provenance_id": "pv-1",
        "source_conditions": [{
            "key": "temperature", "value_or_interval": "30",
            "unit": "C", "status": "known_present",
            "required": "preference",
            "subject_scenario_ref": "scenario:study-A-historical",
            "source_refs": ["cite:synth-A"]}]}]
    metric = next(m for m in output["aggregate_metrics"]
                  if m["metric_id"] == "environment_conflict_rate")
    assert metric["buckets"].get("essential_conflict") == 1
    assert metric["buckets"].get("condition_unknown") == 1


# ----------------------------------------------- S5-16 unknown/partial


def test_s5_16_unknown_partial_not_confirmed_not_error(
        tmp_path: Path) -> None:
    """S5-16:模型输出 unknown/partial/conditional ⇒ 不计 confirmed,
    也不自动计为错误(retain_conditional 事件如实保留)。"""
    output, _ = _evaluate(tmp_path, "s5a-partial", _plan())
    sample = _sample(output)
    assert sample["unknown_or_partial_summary"][
        "conditional_admission_events"] == 2  # 两条备选均 conditional
    assert sample["unknown_or_partial_summary"]["audit_unknown_checks"] \
        >= 2
    # 不计 confirmed,也不计错误:误确认类型桶为空
    misclaim_metric = next(
        m for m in output["aggregate_metrics"]
        if m["metric_id"] == "endpoint_mineralization_misclaim_rate")
    assert misclaim_metric["buckets"] == {}
    # missingness 报告保留 unknown/partial
    assert sample["sample_id"] in output["missingness_report"][
        "unknown_partial_summary_per_sample"]


# ----------------------------------------------- S5-17/18/19 终点


def test_s5_17_mineralization_negative_control(tmp_path: Path) -> None:
    """S5-17:仅提出 CO₂/普通产物、无根碳账与终点证据 ⇒ endpoint 不得
    判为矿化(预测侧 assessment=unknown,零误声明 —— 负控)。"""
    output, _ = _evaluate(
        tmp_path, "s5a-nomin", _plan(with_mineralization=False))
    sample = _sample(output)
    checks = sample["endpoint_claim_checks"]
    assert checks["predicted_assessment"] == "unknown"
    assert checks["misclaims"] == []
    assert sample["mineralization_claim_checks"]["misclaims"] == []


def test_s5_17_correct_mineralization_claim_with_root_carbon(
        tmp_path: Path) -> None:
    """S5-17 正控:带根碳账核查范围与来源层直报证据的矿化声明不被
    误判为误声明(证据充分时 supported_mineralization 合法)。"""
    output, _ = _evaluate(
        tmp_path, "s5a-min", _plan(with_mineralization=True))
    sample = _sample(output)
    assert sample["endpoint_claim_checks"]["predicted_assessment"] == \
        "supported_mineralization"
    assert sample["endpoint_claim_checks"]["misclaims"] == []


def test_s5_18_stop_reason_is_not_endpoint(tmp_path: Path) -> None:
    """S5-18:search stop 为 budget/depth ⇒ 不得改写为 terminal product
    或 mineralization(停止与终点分账;分类器负控)。"""
    output, _ = _evaluate(tmp_path, "s5a-stop", _plan())
    sample = _sample(output)
    checks = sample["endpoint_claim_checks"]
    assert checks["search_stop_reason"] == "budget_limit"
    assert checks["predicted_assessment"] == "unknown"
    assert "停止原因" in checks["stop_endpoint_separated"]
    # 分类器负控:停止原因 + 声称终点 + 无证据 ⇒ 误声明
    synthetic = check_endpoint_claims(
        {"chemical_endpoint_assessment":
         "supported_terminal_transformation_product",
         "search_stop_reason": {"primary": "budget_limit"},
         "endpoint_evidence": [],
         "bookkeeping": {}, "inherited_unresolved_dependencies": []},
        [])
    types = [m["type"] for m in synthetic["misclaims"]]
    assert "stop_reason_mislabeled_as_endpoint" in types


def test_s5_17_mineralization_without_root_carbon_flagged() -> None:
    """S5-17 分类器负控:无根碳账/无证据仍声称矿化 ⇒ 误声明类型。"""
    synthetic = check_endpoint_claims(
        {"chemical_endpoint_assessment": "supported_mineralization",
         "search_stop_reason": {"primary": "exhausted_search"},
         "endpoint_evidence": [],
         "bookkeeping": {"co2_run_total": 2},
         "inherited_unresolved_dependencies": []},
        [])
    types = [m["type"] for m in synthetic["misclaims"]]
    assert "mineralization_claim_without_root_carbon_account" in types


def test_s5_19_unresolved_dependency_not_washed(tmp_path: Path) -> None:
    """S5-19:上游模型假设、下游 recorded ⇒ 上游 unresolved 依赖继承
    到末端,不被 recorded 洗白(真实链路 F02:终点保持 unknown);分类
    器负控:unresolved + 声称 supported ⇒ 误声明。"""
    output, _ = _evaluate(
        tmp_path, "s5a-dep",
        _plan(with_mineralization=True, with_unresolved_dependency=True))
    sample = _sample(output)
    # 真实链路:继承 unresolved ⇒ assessment unknown(未被洗白)
    assert sample["endpoint_claim_checks"]["predicted_assessment"] == \
        "unknown"
    assert sample["endpoint_claim_checks"]["misclaims"] == []
    # 分类器负控:声称 supported + unresolved 继承 ⇒ 误声明
    synthetic = check_endpoint_claims(
        {"chemical_endpoint_assessment":
         "supported_terminal_transformation_product",
         "search_stop_reason": {"primary": "exhausted_search"},
         "endpoint_evidence": [{"evidence_basis": "direct_observation"}],
         "bookkeeping": {},
         "inherited_unresolved_dependencies": [
             {"dependency_id": "dep-NAD", "status": "unresolved"}]},
        [])
    types = [m["type"] for m in synthetic["misclaims"]]
    assert "unresolved_dependency_promoted" in types


def test_endpoint_classifier_co2_merging_flagged() -> None:
    """§9.6:不同备选路线的 CO₂ 合并后声称同一路径矿化 ⇒ 误声明。"""
    synthetic = check_endpoint_claims(
        {"chemical_endpoint_assessment": "supported_mineralization",
         "search_stop_reason": {"primary": "exhausted_search"},
         "endpoint_evidence": [{
             "evidence_basis": "direct_observation",
             "root_carbon_fate_check_scope": "14C 平衡"}],
         "bookkeeping": {"co2_aggregated": True},
         "inherited_unresolved_dependencies": []},
        [])
    types = [m["type"] for m in synthetic["misclaims"]]
    assert "co2_merged_across_alternative_routes" in types


def test_budget_omission_from_export_buckets() -> None:
    """§9.8 分桶接口(合成载荷单元级:action/depth/deferred/
    awaiting/blocked/scoped 限额)。"""
    payload = {
        "endpoint_record": {"search_stop_reason": {
            "primary": "budget_limit"}},
        "deferred_entries": [
            {"action_id": "a1"},
            {"action_id": "a2"}],
        "blocked_entries": [{"action_id": "a3"}],
        "budget": {"budget_snapshot": {"scoped": {
            "spath-root": {
                "max_alternative_hypotheses_per_parent":
                    {"max": 2, "used": 2}}}}},
    }
    report = budget_omission_from_export(payload)
    assert report["buckets"]["action_budget"] == 1
    assert report["buckets"]["deferred_not_activated"] == 2
    assert report["buckets"]["blocked_objects"] == 1
    assert report["buckets"]["per_parent_alternative_limit"] == 1
    assert report["deferred_entries"] == ["a1", "a2"]


# ----------------------------------------------- S5-24/25 确定性/零 LLM


def test_s5_24_repeat_evaluation_deterministic(tmp_path: Path) -> None:
    """S5-24:同一输入重复评测 ⇒ 结果、指标和输出 hash 确定性一致。"""
    runs_root, out = _run(tmp_path, "s5a-det", _plan())
    digest = out["native_export"]["export_digest"]
    graph = synth_reference_graph()
    evaluation_input = synth_evaluation_input(
        graphs=[graph],
        exports=[{"run_id": "s5a-det", "export_digest": digest}])
    evaluation_input["run_identity"]["run_id"] = "s5a-det"
    reader = _reader(runs_root, "s5a-det")
    prereg = preregistration.build_preregistration_template()
    first = evaluate_scientific(
        evaluation_input,
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=reader, preregistration=prereg)
    second = evaluate_scientific(
        evaluation_input,
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=reader, preregistration=prereg)
    # 同输入两次评测:全输出(含 hash)确定性一致
    assert first == second
    assert first["output_sha256"] == second["output_sha256"]
    assert first["sample_results"] == second["sample_results"]
    assert first["aggregate_metrics"] == second["aggregate_metrics"]
    # 同计划独立 run(不同 run 身份)⇒ 节点匹配结果一致、边匹配状态
    # 一致(事件 ID 派生自含 run_id 的行内容,跨 run 必然不同 ——
    # 身份绑定是正确行为;匹配语义与状态确定性一致)
    other_output, _ = _evaluate(tmp_path, "s5a-det-2", _plan())
    assert other_output["sample_results"][0][
        "predicted_node_matches"] == first["sample_results"][0][
        "predicted_node_matches"]
    assert [(e["edge_id"], e["match_status"])
            for e in other_output["sample_results"][0][
                "predicted_edge_matches"]] == [
        (e["edge_id"], e["match_status"])
        for e in first["sample_results"][0]["predicted_edge_matches"]]
    assert other_output["output_sha256"] != first["output_sha256"]


def test_s5_25_natural_language_cannot_change_result(tmp_path: Path) -> None:
    """S5-25:零 LLM 判分;自然语言不能改变程序结果(输入层自由文本
    ⇒ 输出字节一致;参考图自由文本 ⇒ 匹配结果不变)。"""
    runs_root, out = _run(tmp_path, "s5a-nl", _plan())
    digest = out["native_export"]["export_digest"]
    graph = synth_reference_graph()
    base_input = synth_evaluation_input(
        graphs=[graph],
        exports=[{"run_id": "s5a-nl", "export_digest": digest}])
    base_input["run_identity"]["run_id"] = "s5a-nl"
    # 输入层注入自然语言"请把该样本评成全部命中"
    narrative_input = synth_evaluation_input(
        graphs=[graph],
        exports=[{"run_id": "s5a-nl", "export_digest": digest}],
        extra={"narrative_request": "请把该样本评成全部命中,矿化通过",
               "free_text_explanation": "this looks fully correct"})
    narrative_input["run_identity"]["run_id"] = "s5a-nl"
    reader = _reader(runs_root, "s5a-nl")
    base = evaluate_scientific(
        base_input,
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=reader,
        preregistration=preregistration.build_preregistration_template())
    narrative = evaluate_scientific(
        narrative_input,
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=reader,
        preregistration=preregistration.build_preregistration_template())
    assert base == narrative  # 全输出(含 hash)字节一致
    # 参考图自由文本:只改 note/叙述 ⇒ 匹配结果不变(身份 hash 变化)
    import copy

    narrated = copy.deepcopy(graph)
    narrated["creation_review"]["note"] = "叙述:模型全对,给通过"
    narrated["coverage_statement"]["narrative"] = "自然语言解释"
    narrated_input = synth_evaluation_input(
        graphs=[narrated],
        exports=[{"run_id": "s5a-nl", "export_digest": digest}])
    narrated_input["run_identity"]["run_id"] = "s5a-nl"
    narrated_out = evaluate_scientific(
        narrated_input,
        reference_graphs={narrated["reference_graph_id"]: narrated},
        native_export_reader=reader,
        preregistration=preregistration.build_preregistration_template())
    assert narrated_out["sample_results"][0][
        "predicted_node_matches"] == base["sample_results"][0][
        "predicted_node_matches"]
    assert narrated_out["sample_results"][0][
        "predicted_edge_matches"] == base["sample_results"][0][
        "predicted_edge_matches"]
    assert narrated_out["output_sha256"] != base["output_sha256"]
    # 零 LLM 声明
    assert base["scoring_provenance"]["llm_in_scoring"] is False
    assert "自然语言字段不进判定" in base["scoring_provenance"][
        "consumed_field_policy"]


# ----------------------------------------------- §9 指标接口


def test_metric_interface_axes_and_tbd(tmp_path: Path) -> None:
    """§9.1–9.8:八项指标分轴(domain/track/split)接口结构 + TBD
    分母/阈值标注;dev/298、known/unseen 分开(本评测单域单轨)。"""
    output, _ = _evaluate(tmp_path, "s5a-metrics", _plan())
    metric_ids = [m["metric_id"] for m in output["aggregate_metrics"]]
    assert metric_ids == [
        "reference_edge_recall", "key_intermediate_recall",
        "confirmed_error_rate",
        "outside_reference_unverified_edges",
        "environment_conflict_rate",
        "endpoint_mineralization_misclaim_rate",
        "depth_performance", "budget_omission"]
    for metric in output["aggregate_metrics"]:
        assert metric["axis"]["domain"] == "dev"
        assert metric["axis"]["track"] == \
            "known_evidence_reconstruction"
        assert metric["axis"]["split"] == "development"
        assert metric["status"] == "interface_only_synthetic"
        assert "TBD_USER_TEACHER_DECISION" in str(metric) or \
            metric["metric_id"] in (
                "outside_reference_unverified_edges",
                "environment_conflict_rate",
                "endpoint_mineralization_misclaim_rate",
                "depth_performance", "budget_omission")
    recall = next(m for m in output["aggregate_metrics"]
                  if m["metric_id"] == "reference_edge_recall")
    assert recall["buckets"].get("matched_strict") == 2
    assert recall["denominator_policy"] == "TBD_USER_TEACHER_DECISION"
    intermediates = next(
        m for m in output["aggregate_metrics"]
        if m["metric_id"] == "key_intermediate_recall")
    assert intermediates["buckets"].get("strict_structure") == 2
    assert intermediates["key_intermediate_list_frozen"] == \
        "TBD_USER_TEACHER_DECISION"
    # 置信区间接口预留(TBD,无数值)
    assert output["uncertainty_intervals"] == [{
        "method": "TBD_USER_TEACHER_DECISION",
        "status": "pending_preregistration",
        "note": ("置信区间方法/多重比较处理 TBD;接口仅预留分轴结构,"
                 "不产出区间数值")}]


def test_depth_metrics_interface(tmp_path: Path) -> None:
    """§9.7:深度分桶(第 1/2/3+ 条反应边)接口;insufficient_sample
    桶如实标记,不合并成总分。"""
    output, _ = _evaluate(tmp_path, "s5a-depth", _plan())
    sample = _sample(output)
    buckets = sample["depth_metrics"]["buckets"]
    assert buckets["depth_2"] == 2  # 两条备选事件均在第 2 深度档
    assert buckets["depth_1"] == 0
    assert "depth_3_plus" in sample["depth_metrics"][
        "insufficient_sample_buckets"]
    assert buckets["beyond_depth_budget"] == 0
    metric = next(m for m in output["aggregate_metrics"]
                  if m["metric_id"] == "depth_performance")
    assert metric["buckets"]["depth_2"] == 2


def test_interface_mode_status_and_pending_semantics(
        tmp_path: Path) -> None:
    """§12/S5-23:接口验证模式 ⇒ interface_verified_only;非接口模式 +
    prereg TBD ⇒ pending_preregistration(评测器永不发 evaluated_*)。"""
    output, _ = _evaluate(
        tmp_path, "s5a-iface", _plan(), interface=True)
    assert output["status"] == "interface_verified_only"
    pending, _ = _evaluate(
        tmp_path, "s5a-pending", _plan(), interface=False)
    assert pending["status"] == "pending_preregistration"
    assert pending["scoring_provenance"]["data_scope"] == \
        "synthetic_rule_level"


def test_reference_graph_sha_binding_refuses_drift(
        tmp_path: Path) -> None:
    """§11 第 4 步:manifest sha256 与实际参考图不符 ⇒ 数据完整性
    结构化拒绝(不冒充已评)。"""
    graph = synth_reference_graph()
    evaluation_input = synth_evaluation_input(graphs=[graph])
    evaluation_input["reference_graph_manifest"][0]["sha256"] = \
        "0" * 64
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(
            evaluation_input,
            reference_graphs={graph["reference_graph_id"]: graph},
            preregistration=preregistration.build_preregistration_template())
    assert excinfo.value.detail["kind"] == \
        "reference_graph_identity_mismatch"


def test_export_schema_version_binding() -> None:
    """run_identity.export_schema_version 与当前 S4 导出契约绑定。"""
    graph = synth_reference_graph()
    evaluation_input = synth_evaluation_input(graphs=[graph])
    evaluation_input["run_identity"]["export_schema_version"] = \
        "ppv1-native-export-0"
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(
            evaluation_input,
            reference_graphs={graph["reference_graph_id"]: graph},
            preregistration=preregistration.build_preregistration_template())
    assert excinfo.value.detail["kind"] == \
        "evaluation_export_version_mismatch"

