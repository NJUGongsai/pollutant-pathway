"""工作流验收用例(脚本夹具,快速)—— 任务书 §3 第 1-4 组。

覆盖:唯一已记录反应多产物、两条路线汇合、竞争/规则/类比/冲突/无证据、
无效 SMILES、重复兄弟、预算耗尽、深度上限,以及 State 与路径图分离。
崩溃恢复(第 5 组)在 test_workflow_recovery.py;真实引擎(第 6 组)在
test_finder_real.py 与 test_cli_workflow.py。
"""

from __future__ import annotations

import json

import pytest

from pathway_v43.domain.identity import cn_identity
from pathway_v43.workflow import RunAlreadyExists, start_run
from pathway_v43.workflow.state import WorkflowState

from wf_helpers import (
    CATECHOL,
    evidence,
    load_report,
    run_scripted,
)

S = cn_identity(CATECHOL)
P1 = cn_identity("O=CCC=CO")
P2 = cn_identity("CC(O)=O")
Q = cn_identity("O=CCO")


def rec(rid, reactant, prods, **kw):
    return evidence(rid, "recorded_reaction", reactant, prods, **kw)


def rule(rid, reactant, prods):
    return evidence(rid, "rule_application", reactant, prods,
                    match_type="rule_template")


def test_unique_recorded_multi_product_one_event_ordered(tmp_path):
    """验收 1:一个已记录反应含多个有序产物 → 同一事件入图,顺序保留。"""
    scripted = {S: [rec("bt0001#r0001", S, ["O=CCC=CO", "CC(O)=O"])]}
    summary, runs = run_scripted("multi1", scripted, max_frontier_width=2,
                                 runs_root=tmp_path)
    assert summary["counts"]["reaction_events"] == 1
    assert summary["counts"]["event_products"] == 2
    assert summary["counts"]["path_instances"] == 3  # 根 + 2 产物
    report = load_report(runs, "multi1")
    ev = report["reaction_events"][0]
    assert [p["product_smiles"] for p in ev["products"]] == ["O=CCC=CO", "CC(O)=O"]
    assert [p["position"] for p in ev["products"]] == [0, 1]
    # 子路径无证据 → dead_end;run 完成(不是待预测)
    assert summary["stop_reason"] == "completed"
    assert len(report["paths_by_status"].get("dead_end", [])) == 2
    # top-5 报告与展开分离:top5 报告事件产物,展开数来自 budget
    assert report["summary"]["top5_reported_events"][0]["top5"] == [
        "O=CCC=CO", "CC(O)=O"]


def test_width_controls_expansion_and_marks_deferred(tmp_path):
    scripted = {
        S: [rec("bt0001#r0001", S, ["O=CCC=CO", "CC(O)=O"])],
        P1: [rule("bt0002#r0002", P1, ["O=CC=CO"])],
    }
    summary, runs = run_scripted("width1", scripted, max_frontier_width=1,
                                 runs_root=tmp_path)
    report = load_report(runs, "width1")
    # 只展开最前面 1 条;另一条合法候选标 deferred(保留,不删除)
    assert summary["stop_reason"] == "awaiting_prediction"
    statuses = {p["display_name"]: p["status"] for p in report["path_instances"]}
    assert statuses["S11"] == "awaiting_prediction"  # 仅规则证据 → 待预测
    assert statuses["S12"] == "deferred"
    assert report["summary"]["n_deferred"] == 1


def test_junction_two_routes_one_compound_full_history(tmp_path):
    """验收 2:同一分子经不同路线汇合 → 两个 PathInstance、一个 Compound。"""
    scripted = {
        S: [rec("btR1", S, ["O=CCC=CO", "CC(O)=O"])],
        P1: [rec("btR2", P1, ["O=CCO"])],
        P2: [rec("btR3", P2, ["O=CCO"])],
    }
    summary, runs = run_scripted("junc1", scripted, max_depth=3,
                                 max_frontier_width=2, runs_root=tmp_path)
    assert summary["counts"]["compounds"] == 4  # S, P1, P2, Q
    assert summary["counts"]["path_instances"] == 5  # S, P1, P2, Q, Q
    report = load_report(runs, "junc1")
    q_paths = [p for p in report["path_instances"]
               if p["substrate_identity"] == Q]
    assert len(q_paths) == 2
    parents = {p["parent_path_id"] for p in q_paths}
    assert len(parents) == 2
    # 各自完整历史:S11 的首个子路径记 S211,S12 的首个子路径记 S221
    # (约定:S{深度} + 完整位次链)
    names = {"->".join(a["display_name"] for a in p["ancestry"])
             for p in q_paths}
    assert names == {"S1->S11->S211", "S1->S12->S221"}
    # 汇合分子继续检索:两条 Q 路径各自独立 dead_end(无证据)
    assert all(p["status"] == "dead_end" for p in q_paths)


def test_cycle_product_back_to_ancestor_dead_end(tmp_path):
    """验收 2b:路径内返回祖先 → cycle,产物全部被拒 → dead_end 且明示拒因。"""
    A = cn_identity("O=CCC=CO")
    scripted = {
        S: [rec("btR1", S, ["O=CCC=CO"])],
        A: [rec("btR2", A, [CATECHOL])],  # A 的产物回到根底物
    }
    summary, runs = run_scripted("cycle1", scripted, max_depth=2,
                                 runs_root=tmp_path)
    assert summary["stop_reason"] == "completed"
    report = load_report(runs, "cycle1")
    statuses = {p["display_name"]: p for p in report["path_instances"]}
    assert statuses["S11"]["status"] == "dead_end"
    assert "in_path_cycle" in statuses["S11"]["status_reason"]
    # 循环产物不入图:无 A→S 事件
    assert summary["counts"]["reaction_events"] == 1  # 只有 S→A


def test_competing_recorded_awaiting_and_all_evidence_preserved(tmp_path):
    """验收 3a:两条已记录反应竞争 → awaiting_prediction,候选全保留。"""
    scripted = {S: [rec("bt0001#r0001", S, ["O=CCC=CO"], rank=1, score=0.95),
                    rec("bt0002#r0002", S, ["CC(O)=O"], rank=2, score=0.30)]}
    summary, runs = run_scripted("comp1", scripted, runs_root=tmp_path)
    assert summary["stop_reason"] == "awaiting_prediction"
    assert summary["counts"]["reaction_events"] == 0  # 未提交任何反应
    report = load_report(runs, "comp1")
    root = report["path_instances"][0]
    assert root["status"] == "awaiting_prediction"
    considered = root["evidence"]["considered"]
    assert {c["evidence_id"] for c in considered} == {
        "E-bt0001#r0001", "E-bt0002#r0002"}
    assert all(c["tier"] == "recorded_usable" for c in considered)


def test_rule_only_and_analog_only_await_not_recorded(tmp_path):
    for tag, kind, mt in (("rule1", "rule_application", "rule_template"),
                          ("analog1", "analog_reaction",
                           "retrieval_neighbor_transfer")):
        scripted = {S: [evidence(f"src-{tag}", kind, S, ["CC(O)=O"],
                                 match_type=mt)]}
        summary, runs = run_scripted(tag, scripted, runs_root=tmp_path)
        assert summary["stop_reason"] == "awaiting_prediction", tag
        report = load_report(runs, tag)
        assert report["path_instances"][0]["status"] == "awaiting_prediction"
        assert report["counts"]["reaction_events"] == 0


def test_condition_conflict_recorded_dead_end_with_reason(tmp_path):
    scripted = {S: [rec("bt0001#r0001", S, ["O=CCC=CO"],
                         condition_fit="conflict")]}
    summary, runs = run_scripted("conf1", scripted, runs_root=tmp_path)
    assert summary["stop_reason"] == "completed"
    report = load_report(runs, "conf1")
    root = report["path_instances"][0]
    assert root["status"] == "dead_end"
    assert "recorded_not_usable" in root["status_reason"]


def test_no_evidence_dead_end(tmp_path):
    summary, runs = run_scripted("none1", {}, runs_root=tmp_path)
    assert summary["stop_reason"] == "completed"
    report = load_report(runs, "none1")
    assert report["path_instances"][0]["status"] == "dead_end"
    assert "no_evidence" in report["path_instances"][0]["status_reason"]


def test_invalid_smiles_structured_and_inspectable(tmp_path):
    """验收 4a:无效 SMILES → 明确拒因、已写产物一致、可 inspect。"""
    summary, runs = run_scripted("bad1", {}, smiles="C(C)(C)(C)(C)C",
                                 runs_root=tmp_path)
    assert summary["stop_reason"] == "invalid_input"
    assert summary["error"]["gate"] == "smiles"
    report = load_report(runs, "bad1")
    assert report["stop_reason"] == "invalid_input"
    assert report["error"]["message"].startswith("unparseable")
    assert summary["counts"]["path_instances"] == 0


def test_budget_exhausted_with_frontier_remaining(tmp_path):
    """验收 4b:预算耗尽 → budget_exhausted,frontier 剩余如实保留。"""
    scripted = {
        S: [rec("btR1", S, ["O=CCC=CO", "CC(O)=O"])],
        P1: [rule("btR2", P1, ["O=CC=CO"])],
        P2: [rule("btR3", P2, ["CC=O"])],
    }
    summary, runs = run_scripted("budget1", scripted, max_expansions=1,
                                 max_frontier_width=2, runs_root=tmp_path)
    assert summary["stop_reason"] == "budget_exhausted"
    assert summary["budget"]["used_expansions"] == 1
    assert summary["counts"]["frontier"] == 2  # P1/P2 仍待探索,不删除
    assert summary["counts"]["reaction_events"] == 1


def test_depth_limit_status(tmp_path):
    """验收 4c:深度上限 → 子路径标 depth_limit,不再检索。"""
    scripted = {S: [rec("btR1", S, ["O=CCC=CO", "CC(O)=O"])]}
    summary, runs = run_scripted("depth1", scripted, max_depth=1,
                                 max_frontier_width=2, runs_root=tmp_path)
    assert summary["stop_reason"] == "completed"
    report = load_report(runs, "depth1")
    statuses = [p["status"] for p in report["path_instances"]
                if p["display_name"] != "S1"]
    assert statuses == ["depth_limit", "depth_limit"]
    assert summary["budget"]["used_expansions"] == 1  # 只有根检索了一次


def test_duplicate_run_id_rejected(tmp_path):
    scripted = {S: []}
    run_scripted("dup1", scripted, runs_root=tmp_path)
    with pytest.raises(RunAlreadyExists):
        run_scripted("dup1", scripted, runs_root=tmp_path)


def test_rejected_first_product_keeps_original_position(tmp_path):
    """P1 修复回归:前序产物被拒,后续有效产物保持原始位次与展开资格。"""
    A = cn_identity("O=CCC=CO")
    # 产物 0 = 当前底物自身(in_path_cycle 拒);产物 1 = 有效
    scripted = {S: [rec("btR1", S, [CATECHOL, "O=CCC=CO"])]}
    summary, runs = run_scripted("pos1", scripted, max_depth=2,
                                 max_frontier_width=2, runs_root=tmp_path)
    report = load_report(runs, "pos1")
    ev = report["reaction_events"][0]
    # 事件产物只有被接受的一个,且 position 保持原始位次 1(不重排为 0)
    assert [p["position"] for p in ev["products"]] == [1]
    assert ev["products"][0]["product_identity"] == A
    # 有效产物路径:原始位次 1 → 展示名 S12,正常进入 frontier 并探索
    child = [p for p in report["path_instances"] if p["depth"] == 1][0]
    assert child["display_name"] == "S12"
    assert child["product_position"] == 1
    assert child["status"] == "dead_end"  # 无证据探索后死端,而非 rejected
    assert "no_evidence" in child["status_reason"]
    assert summary["counts"]["path_instances"] == 2


def test_awaiting_path_reports_top5_candidates(tmp_path):
    """P2 修复回归:待预测路径同样输出 top-5 候选(与展开分离)。"""
    scripted = {
        S: [rec("bt0001#r0001", S, ["O=CCC=CO"], rank=1),
            rec("bt0002#r0002", S, ["CC(O)=O"], rank=2),
            evidence("src-rule", "rule_application", S, ["CC=O"],
                     match_type="rule_template", rank=3)],
    }
    summary, runs = run_scripted("top5a", scripted, runs_root=tmp_path)
    assert summary["stop_reason"] == "awaiting_prediction"
    report = load_report(runs, "top5a")
    root = report["path_instances"][0]
    assert root["status"] == "awaiting_prediction"
    top5 = root["top5_candidates"]
    assert len(top5) == 3
    assert [c["retrieval_rank"] for c in top5] == [1, 2, 3]
    assert top5[0]["kind"] == "recorded_reaction"
    assert report["summary"]["top5_reported_paths"][0]["display_name"] == "S1"


def test_state_keeps_references_not_chemistry(tmp_path):
    """State 与路径图分离:执行状态只持引用,化学事实在存储与产物。"""
    assert "evidences" not in WorkflowState.__annotations__
    assert "products" not in WorkflowState.__annotations__
    assert "path_instances" not in WorkflowState.__annotations__
    scripted = {S: [rec("btR1", S, ["O=CCC=CO"])]}
    summary, runs = run_scripted("state1", scripted, runs_root=tmp_path)
    # 化学事实在 pathway.sqlite 与 results 产物中(State 只持 task_id 引用)
    assert summary["counts"]["reaction_events"] == 1
    # 根 + P1(子路径无证据也要检索一次)各一份检索产物
    retrieval_dirs = list((runs / "state1" / "results").glob("*/retrieval.json"))
    assert len(retrieval_dirs) == 2
    envelope = json.loads(retrieval_dirs[0].read_text())
    assert envelope["payload"]["evidences"][0]["kind"] == "recorded_reaction"
