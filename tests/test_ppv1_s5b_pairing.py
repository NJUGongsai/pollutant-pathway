"""S5b 启动批 evaluation-4 回归:qid 感知样本↔导出配对(mimo r25
⚠️P1-9 G1 配对错位修复)。

背景:``docs/mimo_ppv1_chem_review_response_r25.md`` 收口清单 #9 ——
evaluation-3 的 ``_pair_exports_to_samples`` 按根严格身份**首中即
break** + ``digests[0]`` 取首位:53 个重复底物下同根的两个 export 全
部配给排序在前的图(判分张冠李戴),后图 ``not_evaluated_export_
missing`` 大面积 pending。evaluation-4 改为 qid 感知配对:
manifest 条目声明图侧 qid(须在 ``root_entity.source_refs``),导出
条目声明导出侧 qid(run↔qid 映射,entry.run_id 与 payload 权威
run_id 绑定核验);任一侧声明 qid ⇒ 严格 qid 档;qid 缺配 ⇒
not_evaluated + reason 明示;两侧均无 qid(合成夹具)⇒ 回退根身份
配对并机读披露 pairing_basis。

夹具纪律:合成 run 走公共 ``start_run`` 真实生成(两题同底物 CCO、
不同 qid、可区分的计划:一题事件带 [H][H] 共同产物、一题不带),
导出经 ``read_native_export`` 首消费读取(多 run 分发 reader 按条目
run_id 取各自 ledger);参考图为合成规则级(零金标/题面;合成 qid
与真实 RXNG_* 题面零重叠)。全部数字是合成规则级接口结果,不外推
dev/298,不构成科学性能声明;判分零 LLM、零网络、零费用。

父基线预期(4fe1e0a,evaluation-3):互抢/张冠李戴/无披露各案
red(后图 pending、错图偷导出、consumed 取 digest 字典序首位、
qid 子字段被忽略不拒),排序无关正控案按配对语义在父上同样受
首中即 break 影响而 red;契约登记案 red(父为 evaluation-3/
profile-23)——逐案红绿分类见交付书与证据包。
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant import preregistration  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    EvaluationContractError,
    evaluate_scientific,
    native_export_reader_from_ledger,
)
from pathway_v43.pollutant.search import SearchLedger  # noqa: E402
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402
from pathway_v43.storage.run_identity import (  # noqa: E402
    PROFILE_POLLUTANT_PATHWAY_V1,
)
from pathway_v43.workflow.runner import start_run  # noqa: E402

from test_ppv1_s4a_endpoint import spec  # noqa: E402
from test_ppv1_s5a_schema import (  # noqa: E402
    synth_evaluation_input,
    synth_reference_graph,
)


QID_A = "RXNG-SYNTH-A"
QID_B = "RXNG-SYNTH-B"


def _plan_coproduct() -> dict:
    """题 A 计划:CCO → CC=O + [H][H](事件带共同产物)。"""
    return {
        "condition_facts": [{
            "key": "oxygen_regime", "value": "aerobic",
            "status": "known_present", "source_ref": "src:synthetic"}],
        "pools": {"CCO": [
            spec("B", "CC=O", "donor-B", coproducts=["[H][H]"])]},
        "schedule_budget": {"max_select": 2},
        "endpoint_evidence": [],
    }


def _plan_no_coproduct() -> dict:
    """题 B 计划:CCO → CC=O(事件不带共同产物)。

    与题 A 同底物同主产物、不同共同产物形状——两导出可按
    e-alt-1/e-alt-2 的覆盖结果互相区分,判分不串可证。
    """
    return {
        "condition_facts": [{
            "key": "oxygen_regime", "value": "aerobic",
            "status": "known_present", "source_ref": "src:synthetic"}],
        "pools": {"CCO": [spec("C", "CC=O", "donor-C")]},
        "schedule_budget": {"max_select": 2},
        "endpoint_evidence": [],
    }


def _run(tmp_path: Path, run_id: str, plan: dict) -> dict:
    """公共 start_run 真实生成;同 tmp_path 内重复调用幂等复用
    (run 目录已存在 ⇒ 从既有 manifest 读回完整 export digest,
    不重跑)。"""
    runs_root = tmp_path / "runs"
    if (runs_root / run_id / "run_identity.json").is_file():
        import json as _json
        from pathway_v43.pollutant.native_export import (
            NATIVE_EXPORT_MANIFEST_FILE,
            NATIVE_EXPORT_SUBDIR,
            list_native_exports,
        )
        prefixes = list_native_exports(runs_root / run_id)
        assert len(prefixes) == 1, \
            f"复用 run {run_id} 应恰有一个导出,得到 {len(prefixes)}"
        manifest = _json.loads(
            (runs_root / run_id / NATIVE_EXPORT_SUBDIR / prefixes[0]
             / NATIVE_EXPORT_MANIFEST_FILE).read_text(encoding="utf-8"))
        return {"native_export": {
            "export_digest": str(manifest["export_digest"])}}
    out = start_run(
        config=resolve_config(), runs_root=runs_root,
        run_id=run_id, smiles="CCO", max_depth=3, max_expansions=10,
        max_frontier_width=2, finder=object(), scripted=True,
        profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    return out


def _multi_run_reader(runs_root: Path, run_ids: list[str]):
    """多 run 分发 reader:按导出条目 run_id 取各自 run 的 ledger。

    (S5b 每题一个 run 的读取通道形状;read_native_export 的
    manifest↔ledger run 绑定核验对每个 run 独立生效。)
    """
    readers = {}
    for run_id in run_ids:
        store = PollutantPathwayStore(
            runs_root / run_id / "pollutant.sqlite")
        artifacts = ArtifactStore(runs_root, run_id)
        ledger = SearchLedger(store, artifacts, run_id)
        readers[run_id] = native_export_reader_from_ledger(
            ledger, runs_root / run_id)

    def reader(entry: dict) -> dict:
        run_id = str(entry.get("run_id"))
        if run_id not in readers:
            raise LookupError(
                f"no ledger wired for run_id {run_id!r}(合成多 run reader)")
        return readers[run_id](entry)

    return reader


def _qid_graph(graph_id: str, qid: str) -> dict:
    """合成 G1 图:root_entity.source_refs 携带 qid(转换规则 §2.2)。"""
    graph = copy.deepcopy(synth_reference_graph(graph_id))
    refs = list(graph["root_entity"]["source_refs"])
    if qid not in refs:
        refs.insert(0, qid)
    graph["root_entity"]["source_refs"] = refs
    return graph


def _two_graph_split(graph_ids: list[str]) -> dict:
    """两图同 development 的合成 split manifest(同根同组不跨集合)。"""
    return {
        "schema_version": synth_evaluation_input()["split_manifest"][
            "schema_version"],
        "split_manifest_id": "sm-synth-pairing",
        "split_rule_version": "ppv1-split-rule-synth-1",
        "input_data_manifest_hash": "sha:synthetic-inputs",
        "assignments": [
            {"reference_graph_id": graph_id,
             "source_group_id": group, "split": "development"}
            for graph_id in graph_ids
            for group in ("sg-study-A", "sg-study-B")],
        "unseen_exclusion_manifest": {
            "track": "unseen_path_inference", "excluded": []},
    }


def _evaluate_two_runs(tmp_path: Path, *, graph_a_id: str,
                       graph_b_id: str, qid_a: str, qid_b: str,
                       manifest_qids: dict[str, str | None] | None = None,
                       export_order: str = "a_b",
                       graph_b_run: bool = True) -> dict:
    """两题同底物 G1 场景公共装配:两图两 run,按 qid 严格配对。

    返回 ``{"output", "digest_a", "digest_b"}``(digest_b 在
    graph_b_run=False 时为 None)。缺省:两图 manifest 各声明自己的
    qid、两导出条目各声明自己 run 的 qid;manifest_qids 可覆盖某图
    的 qid 声明(值 None = 该图不声明)。graph_b_run=False 时不生成
    题 B 的 run(题 B qid 缺配导出案)。
    """
    run_a = _run(tmp_path, "s5b-pair-a", _plan_coproduct())
    digest_a = run_a["native_export"]["export_digest"]
    if graph_b_run:
        run_b = _run(tmp_path, "s5b-pair-b", _plan_no_coproduct())
        digest_b = run_b["native_export"]["export_digest"]
    else:
        digest_b = None
    graphs = [_qid_graph(graph_a_id, qid_a),
              _qid_graph(graph_b_id, qid_b)]
    exports = [
        {"run_id": "s5b-pair-a", "export_digest": digest_a,
         "qid": qid_a}]
    if digest_b is not None:
        exports.append({
            "run_id": "s5b-pair-b", "export_digest": digest_b,
            "qid": qid_b})
    if export_order == "b_a" and digest_b is not None:
        exports.reverse()
    evaluation_input = synth_evaluation_input(
        graphs=graphs, split_manifest=_two_graph_split(
            [graph_a_id, graph_b_id]), exports=exports)
    if manifest_qids is None:
        manifest_qids = {graph_a_id: qid_a, graph_b_id: qid_b}
    for entry in evaluation_input["reference_graph_manifest"]:
        declared = manifest_qids.get(
            str(entry["reference_graph_id"]))
        if declared is not None:
            entry["qid"] = declared
    reader = _multi_run_reader(
        tmp_path / "runs",
        ["s5b-pair-a"] + (["s5b-pair-b"] if digest_b is not None else []))
    output = evaluate_scientific(
        evaluation_input,
        reference_graphs={g["reference_graph_id"]: g for g in graphs},
        native_export_reader=reader,
        preregistration=preregistration.build_preregistration_template())
    return {"output": output, "digest_a": digest_a, "digest_b": digest_b}


def _sample_of(output: dict, graph_id: str) -> dict:
    return next(s for s in output["sample_results"]
                if s["reference_graph_id"] == graph_id)


def _edge_status(sample: dict, edge_id: str) -> str:
    return next(entry["match_status"]
                for entry in sample["predicted_edge_matches"]
                if entry["edge_id"] == edge_id)


# ------------------------------------------- G1 同底物两 qid:各配各的


def test_g1_same_substrate_two_qids_pair_own_runs(tmp_path: Path) -> None:
    """同底物两题(不同 qid)各配各的 run:判分不串、互不抢占。

    修复前(evaluation-3):两 export 按根身份首中即 break 全配给
    排序在前的图,后图 pending;修复后(evaluation-4)严格 qid 配对,
    两题各自消费自己 run 的导出——用两计划的可区分覆盖结果证明
    判分不串(带共同产物的事件只严中 e-alt-1,不带只严中 e-alt-2)。
    """
    result = _evaluate_two_runs(
        tmp_path, graph_a_id="rg-q-a", graph_b_id="rg-q-b",
        qid_a=QID_A, qid_b=QID_B)
    output = result["output"]
    sample_a = _sample_of(output, "rg-q-a")
    sample_b = _sample_of(output, "rg-q-b")
    # 两题均 scored(不再出现后图 not_evaluated_export_missing)
    assert sample_a["scoring_status"] == "scored"
    assert sample_b["scoring_status"] == "scored"
    # 严格 qid 档:各配各的导出(消费 digest 与各自 run 输出一致)
    assert sample_a["pairing"]["basis"] == "qid_strict"
    assert sample_b["pairing"]["basis"] == "qid_strict"
    assert sample_a["pairing"]["qid"] == QID_A
    assert sample_b["pairing"]["qid"] == QID_B
    for sample in (sample_a, sample_b):
        assert len(sample["pairing"]["paired_export_digests"]) == 1
        assert sample["pairing"]["consumed_export_digest"] == \
            sample["pairing"]["paired_export_digests"][0]
        assert sample["pairing"]["digest_selection_rule"] == \
            "native_path_exports_list_order_first"
    assert sample_a["pairing"]["consumed_export_digest"] == \
        result["digest_a"]
    assert sample_b["pairing"]["consumed_export_digest"] == \
        result["digest_b"]
    # 判分不串:题 A(带 [H][H] 共同产物的 run)⇒ e-alt-1 严格、
    # e-alt-2 超集降档;题 B(不带共同产物的 run,导出中无 [H][H]
    # 状态)⇒ e-alt-2 严格、e-alt-1 必要节点未覆盖——互为反相,
    # 配错即翻(两图消费同一导出必现同一侧模式)
    assert _edge_status(sample_a, "e-alt-1") == "matched_strict"
    assert _edge_status(sample_a, "e-alt-2") == \
        "matched_participant_coverage_partial"
    assert _edge_status(sample_b, "e-alt-2") == "matched_strict"
    assert _edge_status(sample_b, "e-alt-1") == \
        "unmatched_required_node_uncovered"
    # 无导出被两题争用:零 unmatched
    assert output["coverage_report"]["unmatched_exports"] == []
    # 覆盖报告机读披露两图的配对档与消费 digest
    report = output["coverage_report"]["pairing"]
    assert report["bases_by_graph"] == {
        "rg-q-a": "qid_strict", "rg-q-b": "qid_strict"}
    assert report["qids_by_graph"] == {
        "rg-q-a": QID_A, "rg-q-b": QID_B}
    assert report["consumed_export_digest_by_graph"] == {
        "rg-q-a": result["digest_a"], "rg-q-b": result["digest_b"]}


# ------------------------------------------- qid 缺配导出:不张冠李戴


def test_qid_unpaired_not_mispaired_by_root(tmp_path: Path) -> None:
    """qid 声明了但缺配导出 ⇒ not_evaluated + reason 明示,不偷同根
    别题的导出(修复前:排序在前的图首中即抢走别题导出,判分张冠
    李戴)。

    排布:rg-a0(排序在前,qid QID_B,无导出)与 rg-z9(qid QID_A,
    持有唯一导出)——修复前 rg-a0 抢走 rg-z9 的导出,rg-z9 pending;
    修复后 rg-a0 空配对 + reason qid 未配到,rg-z9 正常判分。
    """
    result = _evaluate_two_runs(
        tmp_path, graph_a_id="rg-z9", graph_b_id="rg-a0",
        qid_a=QID_A, qid_b=QID_B, graph_b_run=False)
    output = result["output"]
    sample_orphan = _sample_of(output, "rg-a0")
    sample_owner = _sample_of(output, "rg-z9")
    # 缺配题:not_evaluated + reason 明示 qid 未配到(机读携带 qid)
    assert sample_orphan["scoring_status"] == "not_evaluated_export_missing"
    error = sample_orphan["scoring_errors"][0]
    assert error["kind"] == "sample_qid_unpaired"
    assert error["qid"] == QID_B
    assert "未配到" in error["note"]
    assert "张冠李戴" in error["note"]
    assert error["qid_declared_by_export_entry"] is False
    # 不偷别题导出:持有导出的题正常判分并消费自己的导出
    assert sample_owner["scoring_status"] == "scored"
    assert sample_owner["pairing"]["qid"] == QID_A
    assert sample_owner["pairing"]["consumed_export_digest"] == \
        result["digest_a"]
    assert output["coverage_report"]["unmatched_exports"] == []


def test_qid_declared_by_unreadable_entry_disclosed(tmp_path: Path) -> None:
    """qid 声明的导出条目读取失败 ⇒ 样本仍 not_evaluated(reason
    qid 未配到)且披露该 qid 曾被导出条目声明;不回退根身份。"""
    _run(tmp_path, "s5b-unreadable", _plan_coproduct())
    graph = _qid_graph("rg-unreadable", QID_A)
    evaluation_input = synth_evaluation_input(
        graphs=[graph],
        exports=[{"run_id": "s5b-unreadable",
                  "export_digest": "0" * 64, "qid": QID_A}])
    evaluation_input["reference_graph_manifest"][0]["qid"] = QID_A
    reader = _multi_run_reader(tmp_path / "runs", ["s5b-unreadable"])
    output = evaluate_scientific(
        evaluation_input,
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=reader,
        preregistration=preregistration.build_preregistration_template())
    sample = output["sample_results"][0]
    assert sample["scoring_status"] == "not_evaluated_export_missing"
    error = sample["scoring_errors"][0]
    assert error["kind"] == "sample_qid_unpaired"
    assert error["qid_declared_by_export_entry"] is True
    assert output["export_read_errors"][0]["kind"] == \
        "native_export_unreadable"


def test_strict_regime_graph_without_qid_not_root_paired(
        tmp_path: Path) -> None:
    """严格档下未声明 qid 的图不回退根身份配对(回退即重新引入
    首中即 break 错位):单独 reason 披露,排序在前的无 qid 图不再
    抢走有 qid 图的导出。"""
    result = _evaluate_two_runs(
        tmp_path, graph_a_id="rg-z", graph_b_id="rg-b",
        qid_a=QID_A, qid_b=QID_B,
        manifest_qids={"rg-z": QID_A, "rg-b": None})
    output = result["output"]
    sample_no_qid = _sample_of(output, "rg-b")
    sample_with_qid = _sample_of(output, "rg-z")
    # 无 qid 图(排序在前):not_evaluated + 单独 reason
    # (不静默、不根身份回退;修复前它抢走唯一导出)
    assert sample_no_qid["scoring_status"] == "not_evaluated_export_missing"
    error = sample_no_qid["scoring_errors"][0]
    assert error["kind"] == "graph_qid_missing_in_strict_pairing"
    assert "不回退根身份" in error["note"]
    # 有 qid 图:自己的导出自己的分
    assert sample_with_qid["scoring_status"] == "scored"
    assert sample_with_qid["pairing"]["qid"] == QID_A
    assert sample_with_qid["pairing"]["consumed_export_digest"] == \
        result["digest_a"]


def test_export_qid_orphan_to_no_graph_unmatched_exports(
        tmp_path: Path) -> None:
    """可读导出声明无人认领的 qid ⇒ unmatched_exports 机读披露
    (每个导出至多配一个样本;修复前同根导出会全配给首中图)。"""
    run_a = _run(tmp_path, "s5b-orphan-a", _plan_coproduct())
    digest_a = run_a["native_export"]["export_digest"]
    run_b = _run(tmp_path, "s5b-orphan-b", _plan_no_coproduct())
    digest_b = run_b["native_export"]["export_digest"]
    graph = _qid_graph("rg-sole", QID_A)
    evaluation_input = synth_evaluation_input(
        graphs=[graph],
        exports=[
            {"run_id": "s5b-orphan-a", "export_digest": digest_a,
             "qid": QID_A},
            {"run_id": "s5b-orphan-b", "export_digest": digest_b,
             "qid": "RXNG-SYNTH-ORPHAN"}])
    evaluation_input["reference_graph_manifest"][0]["qid"] = QID_A
    reader = _multi_run_reader(
        tmp_path / "runs", ["s5b-orphan-a", "s5b-orphan-b"])
    output = evaluate_scientific(
        evaluation_input,
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=reader,
        preregistration=preregistration.build_preregistration_template())
    sample = output["sample_results"][0]
    # 唯一图只消费自己 qid 的导出;孤儿导出进 unmatched 披露
    assert sample["scoring_status"] == "scored"
    assert sample["pairing"]["consumed_export_digest"] == digest_a
    assert output["coverage_report"]["unmatched_exports"] == [digest_b]


# ------------------------------------------- 无 qid 合成夹具:回退披露


def test_fallback_root_identity_pairing_disclosed(tmp_path: Path) -> None:
    """两侧均不声明 qid(合成夹具)⇒ 回退根严格身份配对,机读披露
    pairing_basis=root_identity_fallback(不静默;行为与 evaluation-3
    一致:单图单导出照常 scored)。"""
    run = _run(tmp_path, "s5b-fallback", _plan_coproduct())
    digest = run["native_export"]["export_digest"]
    graph = synth_reference_graph("rg-fb")  # source_refs 无 qid
    evaluation_input = synth_evaluation_input(
        graphs=[graph],
        exports=[{"run_id": "s5b-fallback", "export_digest": digest}])
    reader = _multi_run_reader(tmp_path / "runs", ["s5b-fallback"])
    output = evaluate_scientific(
        evaluation_input,
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=reader,
        preregistration=preregistration.build_preregistration_template())
    sample = output["sample_results"][0]
    assert sample["scoring_status"] == "scored"
    assert sample["pairing"]["basis"] == "root_identity_fallback"
    assert sample["pairing"]["qid"] is None
    assert sample["pairing"]["consumed_export_digest"] == digest
    assert sample["pairing"]["digest_selection_rule"] == \
        "root_identity_first_match_sorted_digest_order"
    report = output["coverage_report"]["pairing"]
    assert report["bases_by_graph"] == {"rg-fb":
                                        "root_identity_fallback"}
    assert report["qids_by_graph"] == {"rg-fb": None}
    assert report["consumed_export_digest_by_graph"] == {"rg-fb": digest}


# ------------------------------------------- 同 qid 多导出:显式清单序


def test_same_qid_multiple_exports_list_order_selection(
        tmp_path: Path) -> None:
    """同一 qid 两个导出 ⇒ 按输入 native_path_exports 清单序取首位
    (显式清单序,确定性;披露 paired 全清单与被消费 digest;不随机)
    ——倒序输入 ⇒ 消费另一端,双向可证。"""
    run_a = _run(tmp_path, "s5b-multi-a", _plan_coproduct())
    digest_a = run_a["native_export"]["export_digest"]
    run_b = _run(tmp_path, "s5b-multi-b", _plan_no_coproduct())
    digest_b = run_b["native_export"]["export_digest"]
    graph = _qid_graph("rg-multi", QID_A)
    exports_forward = [
        {"run_id": "s5b-multi-a", "export_digest": digest_a,
         "qid": QID_A},
        {"run_id": "s5b-multi-b", "export_digest": digest_b,
         "qid": QID_A}]
    reader = _multi_run_reader(
        tmp_path / "runs", ["s5b-multi-a", "s5b-multi-b"])

    def _evaluate(exports: list[dict]) -> dict:
        evaluation_input = synth_evaluation_input(
            graphs=[graph], exports=exports)
        evaluation_input["reference_graph_manifest"][0]["qid"] = QID_A
        return evaluate_scientific(
            evaluation_input,
            reference_graphs={graph["reference_graph_id"]: graph},
            native_export_reader=reader,
            preregistration=preregistration.build_preregistration_template())

    forward = _evaluate(exports_forward)
    sample = forward["sample_results"][0]
    assert sample["scoring_status"] == "scored"
    # 配对清单 = 两导出(同 qid 多 run),消费 = 清单首位
    assert sorted(sample["pairing"]["paired_export_digests"]) == \
        sorted([digest_a, digest_b])
    assert sample["pairing"]["consumed_export_digest"] == digest_a
    assert sample["pairing"]["digest_selection_rule"] == \
        "native_path_exports_list_order_first"
    # 倒序输入 ⇒ 消费另一端(同一确定性规则的两个方向)
    reversed_output = _evaluate(list(reversed(exports_forward)))
    reversed_sample = reversed_output["sample_results"][0]
    assert reversed_sample["pairing"]["consumed_export_digest"] == digest_b
    # 两方向均零 unmatched(两导出都属同一图)
    assert forward["coverage_report"]["unmatched_exports"] == []
    assert reversed_output["coverage_report"]["unmatched_exports"] == []


# ------------------------------------------- 排序无关性(正控)


def test_pairing_independent_of_entry_order(tmp_path: Path) -> None:
    """qid 配对结果与 manifest/导出条目顺序无关(只依赖 qid 身份):
    倒排导出清单 ⇒ 各图消费 digest 不变。"""
    forward = _evaluate_two_runs(
        tmp_path, graph_a_id="rg-o-a", graph_b_id="rg-o-b",
        qid_a=QID_A, qid_b=QID_B)
    reversed_case = _evaluate_two_runs(
        tmp_path, graph_a_id="rg-o-a", graph_b_id="rg-o-b",
        qid_a=QID_A, qid_b=QID_B, export_order="b_a")
    for case in (forward, reversed_case):
        for graph_id, qid in (("rg-o-a", QID_A), ("rg-o-b", QID_B)):
            sample = _sample_of(case["output"], graph_id)
            assert sample["scoring_status"] == "scored"
            assert sample["pairing"]["qid"] == qid
    forward_a = _sample_of(forward["output"], "rg-o-a")["pairing"][
        "consumed_export_digest"]
    reversed_a = _sample_of(reversed_case["output"], "rg-o-a")["pairing"][
        "consumed_export_digest"]
    forward_b = _sample_of(forward["output"], "rg-o-b")["pairing"][
        "consumed_export_digest"]
    reversed_b = _sample_of(reversed_case["output"], "rg-o-b")["pairing"][
        "consumed_export_digest"]
    assert forward_a == reversed_a
    assert forward_b == reversed_b
    assert forward_a != forward_b


# ------------------------------------------- qid 声明契约(fail-closed)


def test_manifest_qid_not_in_source_refs_rejected(
        tmp_path: Path) -> None:
    """manifest 声明 qid 未出现在 root_entity.source_refs ⇒ 结构化拒
    (图侧 qid 一致性核;不猜哪个是真)。"""
    run = _run(tmp_path, "s5b-srcmismatch", _plan_coproduct())
    digest = run["native_export"]["export_digest"]
    graph = synth_reference_graph("rg-mismatch")  # source_refs 无 qid
    evaluation_input = synth_evaluation_input(
        graphs=[graph],
        exports=[{"run_id": "s5b-srcmismatch", "export_digest": digest,
                  "qid": QID_A}])
    evaluation_input["reference_graph_manifest"][0]["qid"] = QID_A
    reader = _multi_run_reader(tmp_path / "runs", ["s5b-srcmismatch"])
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(
            evaluation_input,
            reference_graphs={graph["reference_graph_id"]: graph},
            native_export_reader=reader,
            preregistration=preregistration.build_preregistration_template())
    assert excinfo.value.detail["kind"] == \
        "reference_graph_qid_not_in_source_refs"
    assert excinfo.value.detail["qid"] == QID_A
    assert excinfo.value.detail["reference_graph_id"] == "rg-mismatch"


def test_duplicate_manifest_qid_rejected(tmp_path: Path) -> None:
    """两图声明同一 qid(G1 一题一图下配对键歧义)⇒ 结构化拒。"""
    graph_a = _qid_graph("rg-dup-a", QID_A)
    graph_b = _qid_graph("rg-dup-b", QID_A)
    evaluation_input = synth_evaluation_input(
        graphs=[graph_a, graph_b],
        split_manifest=_two_graph_split(["rg-dup-a", "rg-dup-b"]),
        exports=[])
    for entry in evaluation_input["reference_graph_manifest"]:
        entry["qid"] = QID_A
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(
            evaluation_input,
            reference_graphs={"rg-dup-a": graph_a, "rg-dup-b": graph_b},
            preregistration=preregistration.build_preregistration_template())
    assert excinfo.value.detail["kind"] == "evaluation_input_duplicate_qid"
    assert excinfo.value.detail["qid"] == QID_A


def test_export_qid_run_binding_mismatch_rejected(tmp_path: Path) -> None:
    """声明 qid 的导出条目 run_id 与导出 payload 权威 run_id 不符 ⇒
    结构化拒(qid↔run 映射与 read_native_export 的 run/identity 链
    断裂,声明不可信;不用声明侧静默配对)。"""
    run = _run(tmp_path, "s5b-binding", _plan_coproduct())
    digest = run["native_export"]["export_digest"]
    graph = _qid_graph("rg-binding", QID_A)
    evaluation_input = synth_evaluation_input(
        graphs=[graph],
        exports=[{"run_id": "s5b-binding-spoof",
                  "export_digest": digest, "qid": QID_A}])
    evaluation_input["reference_graph_manifest"][0]["qid"] = QID_A
    # reader 固定用真实 run 的单 ledger(读出 payload.run_id=
    # s5b-binding;不看条目 run_id——正是 run 绑定核验要拦的错接线)
    runs_root = tmp_path / "runs"
    store = PollutantPathwayStore(
        runs_root / "s5b-binding" / "pollutant.sqlite")
    artifacts = ArtifactStore(runs_root, "s5b-binding")
    ledger = SearchLedger(store, artifacts, "s5b-binding")
    reader = native_export_reader_from_ledger(
        ledger, runs_root / "s5b-binding")
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(
            evaluation_input,
            reference_graphs={graph["reference_graph_id"]: graph},
            native_export_reader=reader,
            preregistration=preregistration.build_preregistration_template())
    assert excinfo.value.detail["kind"] == \
        "evaluation_export_run_binding_mismatch"
    assert excinfo.value.detail["entry_run_id"] == "s5b-binding-spoof"
    assert excinfo.value.detail["payload_run_id"] == "s5b-binding"
    assert excinfo.value.detail["qid"] == QID_A


def test_empty_qid_string_rejected(tmp_path: Path) -> None:
    """qid 声明为空字符串 ⇒ 结构化拒(空值不静默当未声明)。"""
    graph = _qid_graph("rg-empty", QID_A)
    evaluation_input = synth_evaluation_input(
        graphs=[graph],
        exports=[{"run_id": "synth", "export_digest": "d" * 64,
                  "qid": ""}])
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(
            evaluation_input,
            reference_graphs={graph["reference_graph_id"]: graph},
            preregistration=preregistration.build_preregistration_template())
    assert excinfo.value.detail["kind"] == \
        "evaluation_input_field_invalid"
    assert "qid" in excinfo.value.detail["field"]


# ------------------------------------------- 确定性/契约登记


def test_pairing_disclosure_deterministic(tmp_path: Path) -> None:
    """同输入重复评测:配对披露(含 consumed digest)确定性一致
    (S5-24 纪律延伸到 evaluation-4 配对块)。"""
    first = _evaluate_two_runs(
        tmp_path, graph_a_id="rg-det-a", graph_b_id="rg-det-b",
        qid_a=QID_A, qid_b=QID_B)
    second = _evaluate_two_runs(
        tmp_path, graph_a_id="rg-det-a", graph_b_id="rg-det-b",
        qid_a=QID_A, qid_b=QID_B)
    assert first["output"]["output_sha256"] == \
        second["output"]["output_sha256"]
    assert first["output"]["sample_results"] == \
        second["output"]["sample_results"]
    assert first["output"]["coverage_report"]["pairing"] == \
        second["output"]["coverage_report"]["pairing"]


def test_evaluation4_contract_registered() -> None:
    """evaluation / profile 契约登记(配对语义变更升版,不偷换
    同一已登记契约;reference-graph-1/split-manifest-1 不变)。

    S5b 启动批:evaluation-4/profile-24(qid 感知配对);S5b 启动批
    回修(S5B-L01):evaluation-5/profile-25(real 档配对禁
    root_identity_fallback;守卫回归另见
    tests/test_ppv1_s5b_rework_l01.py)。
    """
    from pathway_v43.pollutant.profile import (
        PPV1_EVALUATION_VERSION,
        PPV1_PROFILE_SCHEMA_VERSION,
        PPV1_REFERENCE_GRAPH_VERSION,
        PPV1_SPLIT_MANIFEST_VERSION,
        contract_versions,
    )
    assert PPV1_EVALUATION_VERSION == "ppv1-evaluation-5"
    assert PPV1_PROFILE_SCHEMA_VERSION == "ppv1-profile-25"
    assert contract_versions()["evaluation"] == "ppv1-evaluation-5"
    assert contract_versions()["profile"] == "ppv1-profile-25"
    # qid 是 manifest/导出条目级输入子字段与消费侧语义:
    # reference-graph-1 / split-manifest-1 字段形状零变化
    assert PPV1_REFERENCE_GRAPH_VERSION == "ppv1-reference-graph-1"
    assert PPV1_SPLIT_MANIFEST_VERSION == "ppv1-split-manifest-1"
