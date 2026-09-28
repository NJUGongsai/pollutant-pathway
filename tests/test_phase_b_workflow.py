"""EC298 Phase B 工作流验收测试(TASK_V43_EC298_PHASE_B §5 夹具 1-4)。

- 夹具 1:同父两张 usable recorded 卡,模型选 A、order 含 B:A 占 @1 并
  提交;B 逐卡验证后可报告但不提交、不生成子路径;B 条件冲突则留拒因
  不占位;模型 order 违反契约(未知/重复/非首位)走有界重试后显式停留。
- 夹具 2:唯一 recorded + 其他卡:首位与下一步稳定;规则卡
  not_validated_for_reporting 不进答卷;选中卡多产物有效/无效逐项裁决。
- 夹具 3:报告宽度(max_reportable_products=5)与展开宽度
  (max_frontier_width)分别限制;已提交 deferred 产物仍报告;两者都不
  凭空产生下一步。
- 夹具 4:三处硬杀/重放(草稿落盘后 / 事件提交后 / 最终化后)——比较
  最终账本事件数、裁决 payload SHA、LLM 调用账;无重复事件、不多耗调用、
  无悬空裁决。
"""

from __future__ import annotations

import json
import os
import subprocess
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.domain.models import stable_id  # noqa: E402

from wf_helpers import (  # noqa: E402
    CATECHOL,
    evidence,
    fake_model,
    load_report,
    rank_response,
    run_scripted,
)

S = cn_identity(CATECHOL)
P1 = "CC(O)=O"          # 儿茶酚 → 羧酸(示意)
P2 = "O=CCC=CO"


def _rec(rid, prods, *, rank=1, condition_fit="unknown"):
    return evidence(rid, "recorded_reaction", S, prods, rank=rank,
                    condition_fit=condition_fit)


def _rule(rid, prods, *, rank=3):
    return evidence(rid, "rule_application", S, prods, rank=rank,
                    match_type="rule_template")


def _read_final_adjudication(runs_root: Path, run_id: str,
                             path_id: str) -> dict:
    results = runs_root / run_id / "results"
    found = []
    for task_dir in sorted(results.iterdir()):
        p = task_dir / "report_adjudication.json"
        if p.is_file():
            payload = json.loads(p.read_text(encoding="utf-8"))["payload"]
            if payload.get("path_id") == path_id:
                found.append(payload)
    assert len(found) == 1, f"期望恰一份最终裁决:{path_id}"
    return found[0]


def _read_draft(runs_root: Path, run_id: str, path_id: str) -> dict | None:
    results = runs_root / run_id / "results"
    for task_dir in sorted(results.iterdir()):
        p = task_dir / "report_adjudication_draft.json"
        if p.is_file():
            payload = json.loads(p.read_text(encoding="utf-8"))["payload"]
            if payload.get("path_id") == path_id:
                return payload
    return None


# ------------------------------------------------------------- 夹具 1


def test_two_usable_recorded_model_order_reports_but_not_expands(tmp_path):
    """模型选 A、order 含 B:A 提交占 @1;B 可报告但不提交、不生成子路径。"""
    a = _rec("btA", [P1], rank=1)
    b = _rec("btB", [P2], rank=2)
    model = fake_model({"rank_candidates": [
        rank_response("E-btA", order=["E-btA", "E-btB"])]})
    summary, runs_root = run_scripted(
        "pb1", {S: [a, b]}, smiles=CATECHOL, max_depth=2,
        max_expansions=6, max_frontier_width=3, runs_root=tmp_path,
        model=model)
    root_pid = stable_id("p", "pb1", "root", S)
    assert summary["counts"]["reaction_events"] == 1
    final = _read_final_adjudication(runs_root, "pb1", root_pid)
    ranked = [r for r in final["products"] if r["reportable"]]
    assert [(r["evidence_id"], r["report_rank"]) for r in ranked] == [
        ("E-btA", 1), ("E-btB", 2)]
    b_entry = next(r for r in final["products"] if r["evidence_id"] == "E-btB")
    assert b_entry["committed_event_ref"] is None
    assert not b_entry["expand_selected"]
    assert final["rank_basis"] == "model_order"
    assert final["event"]["event_id"] and not final["event"]["no_event"]
    # B 未提交:根下只有 A 产物一条子路径(不生成 B 的子路径)
    store_paths = load_report(runs_root, "pb1")["path_instances"]
    children = [p for p in store_paths if p["parent_path_id"] == root_pid]
    assert len(children) == 1
    assert children[0]["substrate_identity"] == cn_identity(P1)
    # 草稿与最终并存,草稿无事件引用
    draft = _read_draft(runs_root, "pb1", root_pid)
    assert draft is not None and draft["stage"] == "draft"
    assert all(r["committed_event_ref"] is None
               for r in draft["products"])


def test_order_conflict_card_rejected_with_reason_not_ranked(tmp_path):
    """B 条件冲突:B 未选中(唯一 usable 直通),逐卡留拒因、不占位。"""
    a = _rec("btA", [P1], rank=1)
    b = _rec("btB", [P2], rank=2, condition_fit="conflict")
    summary, runs_root = run_scripted(
        "pb2", {S: [a, b]}, smiles=CATECHOL, max_depth=1,
        max_expansions=4, max_frontier_width=3, runs_root=tmp_path)
    root_pid = stable_id("p", "pb2", "root", S)
    assert summary["counts"]["reaction_events"] == 1
    final = _read_final_adjudication(runs_root, "pb2", root_pid)
    ranked = [r for r in final["products"] if r["reportable"]]
    assert [r["evidence_id"] for r in ranked] == ["E-btA"]
    b_entry = next(r for r in final["products"] if r["evidence_id"] == "E-btB")
    assert not b_entry["reportable"]
    assert any("condition_conflict" in r for r in b_entry["reasons"])
    b_card = next(c for c in final["cards"] if c["evidence_id"] == "E-btB")
    assert not b_card["selected"] and not b_card["in_model_order"]


def test_invalid_model_order_consumes_bounded_retries_then_holds(tmp_path):
    """order 违反契约(重复 ID)= 解析失败:有界重试后显式停留,无事件、
    无裁决产物(不悬空)、LLM 调用账 = 1 + max_parse_retries。"""
    a = _rec("btA", [P1], rank=1)
    b = _rec("btB", [P2], rank=2)
    bad = json.dumps({"decision": "select", "evidence_id": "E-btA",
                      "order": ["E-btA", "E-btA"], "reasons": {}})
    model = fake_model({"rank_candidates": [bad]})
    summary, runs_root = run_scripted(
        "pb3", {S: [a, b]}, smiles=CATECHOL, max_depth=1,
        max_expansions=4, max_frontier_width=3, runs_root=tmp_path,
        model=model)
    assert summary["stop_reason"] == "awaiting_prediction"
    assert summary["counts"]["reaction_events"] == 0
    results = runs_root / "pb3" / "results"
    # 1 次首调 + 2 次重试(默认 max_parse_retries=2),全部落盘
    assert len(list(results.glob("*/prediction_call.*.json"))) == 3
    assert len(list(results.glob("*/prediction_response.*.json"))) == 3
    assert not list(results.glob("*/report_adjudication*.json"))


# ------------------------------------------------------------- 夹具 2


def test_unique_recorded_with_other_cards_stable_first(tmp_path):
    """唯一 recorded + 规则卡:首位与下一步稳定;规则卡
    not_validated_for_reporting 不进答卷;模型原文产物不出现。"""
    a = _rec("btA", [P1, "C(C("], rank=1)   # 位置 1 无效:逐项裁决
    rule = _rule("btR", ["CC(N)=O"], rank=2)
    summary, runs_root = run_scripted(
        "pb4", {S: [a, rule]}, smiles=CATECHOL, max_depth=2,
        max_expansions=6, max_frontier_width=3, runs_root=tmp_path)
    root_pid = stable_id("p", "pb4", "root", S)
    assert summary["counts"]["reaction_events"] == 1
    final = _read_final_adjudication(runs_root, "pb4", root_pid)
    ranked = [r for r in final["products"] if r["reportable"]]
    assert [(r["evidence_id"], r["position"]) for r in ranked] == [
        ("E-btA", 0)]  # 仅有效项占位;无效项与规则卡都不进答卷
    invalid = next(r for r in final["products"]
                   if r["evidence_id"] == "E-btA" and r["position"] == 1)
    assert not invalid["accepted"]
    assert any("unparseable" in r for r in invalid["reasons"])
    rule_entry = next(r for r in final["products"]
                      if r["evidence_id"] == "E-btR")
    assert not rule_entry["reportable"]
    rule_card = next(c for c in final["cards"]
                     if c["evidence_id"] == "E-btR")
    assert rule_card["not_validated_for_reporting"]
    assert final["rank_basis"] == "deterministic_fallback"
    # 下一步稳定:A 的有效产物是唯一 frontier
    children = [p for p in load_report(runs_root, "pb4")["path_instances"]
                if p["parent_path_id"] == root_pid]
    assert len(children) == 1


def test_proposal_products_reported_donor_card_not_reportable(tmp_path):
    """novel 提案产物照常报告提交;检索侧规则卡不因提案存在而升格。"""
    from wf_helpers import novel_response

    rule = _rule("btR", ["CC(N)=O"], rank=1)
    model = fake_model({"novel_proposal": [novel_response(
        [{"smiles": "OC(C(=O))C", "note": "氧化提议"}])]})
    summary, runs_root = run_scripted(
        "pb5", {S: [rule]}, smiles=CATECHOL, max_depth=1,
        max_expansions=4, max_frontier_width=2, runs_root=tmp_path,
        model=model)
    assert summary["counts"]["reaction_events"] == 1
    root_pid = stable_id("p", "pb5", "root", S)
    final = _read_final_adjudication(runs_root, "pb5", root_pid)
    ranked = [r for r in final["products"] if r["reportable"]]
    assert len(ranked) == 1
    assert ranked[0]["entry_layer"] == "model_proposal"
    rule_card = next(c for c in final["cards"] if c["evidence_id"] == "E-btR")
    assert rule_card["not_validated_for_reporting"]


# ------------------------------------------------------------- 夹具 3


def test_report_width_and_frontier_width_limit_separately(tmp_path):
    """七个合格产品:报告五位;展开宽度 2 → 2 frontier + 5 deferred;
    deferred 已提交产物仍报告;两者都不凭空产生下一步。"""
    prods = []
    i = 0
    while len(prods) < 7:
        s = f"C{'C' * (i + 2)}O" if i % 2 == 0 else f"CC(=O)C{'C' * i}O"
        if cn_identity(s) and cn_identity(s) != S:
            prods.append(s)
        i += 1
    a = _rec("btA", prods, rank=1)
    summary, runs_root = run_scripted(
        "pb6", {S: [a]}, smiles=CATECHOL, max_depth=1,
        max_expansions=6, max_frontier_width=2, runs_root=tmp_path)
    root_pid = stable_id("p", "pb6", "root", S)
    assert summary["counts"]["reaction_events"] == 1
    # 提交集 = 报告占位产物(committed ⇒ reportable 不变量);
    # 超出报告宽度的合格产物保持已验证、未提交
    assert summary["counts"]["event_products"] == 5
    final = _read_final_adjudication(runs_root, "pb6", root_pid)
    ranked = [r for r in final["products"] if r["reportable"]]
    assert [r["report_rank"] for r in ranked] == [1, 2, 3, 4, 5]
    assert final["n_committed"] == 5 and final["n_expand_selected"] == 2
    assert final["n_deferred"] == 3
    capped = [r for r in final["products"]
              if r["dedup_reason"] == "report_width_cap:5"]
    assert len(capped) == 2
    assert all(r["accepted"] and r["committed_event_ref"] is None
               for r in capped)
    # 展开宽度 2:根下 2 条 frontier 系子路径(max_depth=1 下如实标
    # depth_limit)+ 3 条 deferred(不删除),不因报告宽度多展开
    paths = load_report(runs_root, "pb6")["path_instances"]
    children = [p for p in paths if p["parent_path_id"] == root_pid]
    assert len(children) == 5
    assert [p["status"] for p in children].count("deferred") == 3
    assert [p["status"] for p in children].count("depth_limit") == 2
    assert summary["stop_reason"] in ("completed", "budget_exhausted")


# ------------------------------------------------------------- 夹具 4


DRIVER = Path(__file__).resolve().parent / "recovery_driver.py"


def _driver(mode: str, runs_root: Path, run_id: str, scripted: Path,
            counter: Path, llm_counter: Path, fake_script: Path,
            crash_after: str | None = None):
    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = "1"
    cmd = [sys.executable, str(DRIVER), mode,
           "--runs-root", str(runs_root), "--run-id", run_id,
           "--smiles", CATECHOL, "--scripted", str(scripted),
           "--counter", str(counter), "--llm-counter", str(llm_counter),
           "--fake-script", str(fake_script), "--model", "fake",
           "--max-depth", "2", "--max-expansions", "6",
           "--max-frontier-width", "2"]
    if crash_after:
        cmd += ["--crash-after", crash_after]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                          env=env)


def _fixture_file(tmp_path: Path) -> Path:
    fixture = {
        S: [_rec("btA", [P1, P2], rank=1), _rec("btB", ["CC(N)=O"], rank=2)],
        cn_identity(P1): [evidence("btC", "recorded_reaction",
                                   cn_identity(P1), ["O=CC=O"], rank=1)],
    }
    p = tmp_path / "scripted_fixture.json"
    p.write_text(json.dumps(fixture), encoding="utf-8")
    return p


def _fake_script_file(tmp_path: Path) -> Path:
    # rank 模式:选 E-btA,order 含 E-btB(夹具 1 语义)
    p = tmp_path / "fake_script.json"
    p.write_text(json.dumps({"rank_candidates": [
        rank_response("E-btA", order=["E-btA", "E-btB"])]}),
        encoding="utf-8")
    return p


def _adjudication_shas(runs_root: Path, run_id: str) -> list[str]:
    """最终裁决 payload 内容哈希(不含信封时间戳;跨进程可比)。"""
    from pathway_v43.domain.models import content_hash

    out = []
    results = runs_root / run_id / "results"
    for task_dir in sorted(results.iterdir()):
        p = task_dir / "report_adjudication.json"
        if p.is_file():
            out.append(content_hash(json.loads(p.read_text(
                encoding="utf-8"))["payload"]))
    return sorted(out)


def _store_counts(runs_root: Path, run_id: str) -> dict:
    from pathway_v43.storage.pathway_store import PathwayStore

    st = PathwayStore(runs_root / run_id / "pathway.sqlite")
    try:
        return st.counts()
    finally:
        st.close()


def test_crash_replay_three_kill_points_same_ledger_and_adjudication(
        tmp_path):
    """三处硬杀/重放:草稿落盘后、事件提交后、最终化后。

    - 账本事件数/产物数/路径数与无崩溃基线一致;LLM 调用账一致
      (不多耗);
    - 重放确定性由幂等写保证:恢复进程重算草稿/最终裁决,内容漂移会以
      ArtifactConflict / EventConflict 使 resume 失败 —— resume 成功即证明
      同输入重算同内容;
    - 崩溃时刻已存在的草稿(kill 1)与最终裁决(kill 3)在恢复后逐字节
      不变;无悬空(每份草稿都有对应最终裁决)。
    """
    fixture = _fixture_file(tmp_path)
    fake = _fake_script_file(tmp_path)

    def _payload_hash(runs_root: Path, name: str) -> str | None:
        from pathway_v43.domain.models import content_hash

        results = runs_root / "pb_cmp" / "results"
        for task_dir in sorted(results.iterdir()):
            p = task_dir / name
            if p.is_file():
                return content_hash(
                    json.loads(p.read_text(encoding="utf-8"))["payload"])
        return None

    def _all_payload_hashes(runs_root: Path, name: str) -> list[str]:
        from pathway_v43.domain.models import content_hash

        results = runs_root / "pb_cmp" / "results"
        out = []
        for task_dir in sorted(results.iterdir()):
            p = task_dir / name
            if p.is_file():
                out.append(content_hash(
                    json.loads(p.read_text(encoding="utf-8"))["payload"]))
        return sorted(out)

    def _run(name, crash=None):
        # 同一 run_id、独立 runs_root:path_id/event_id 由 run_id 派生;
        # 账本计数跨 run 可比,payload 引用的任务 ID 因检索信封时间戳跨
        # run 天然不同 —— 确定性断言在 run 内(幂等重放)完成
        runs_root = tmp_path / f"runs_{name}"
        counter = tmp_path / f"cnt_{name}.txt"
        llm_counter = tmp_path / f"llm_{name}.txt"
        counter.write_text("0")
        llm_counter.write_text("0")
        crash_state: dict = {}
        if crash is None:
            proc = _driver("run", runs_root, "pb_cmp", fixture, counter,
                           llm_counter, fake)
        else:
            proc = _driver("run", runs_root, "pb_cmp", fixture, counter,
                           llm_counter, fake, crash_after=crash)
            assert proc.returncode == 70, proc.stdout + proc.stderr
            # 崩溃时刻盘上状态(重放后必须不变)
            crash_state["draft"] = _all_payload_hashes(
                runs_root, "report_adjudication_draft.json")
            crash_state["final"] = _all_payload_hashes(
                runs_root, "report_adjudication.json")
            proc = _driver("resume", runs_root, "pb_cmp", fixture, counter,
                           llm_counter, fake)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        for line in proc.stdout.splitlines():
            if line.startswith("SUMMARY "):
                summary = json.loads(line[len("SUMMARY "):])
                break
        else:
            raise AssertionError(proc.stdout + proc.stderr)
        return summary, runs_root, llm_counter, crash_state

    baseline, base_runs, base_llm, _ = _run("pb_base")
    assert baseline["counts"]["reaction_events"] == 2
    assert len(_all_payload_hashes(base_runs,
                                   "report_adjudication.json")) == 2

    for kill in ("adjudicate_candidates", "commit_event", "commit_pathway"):
        summary, runs_root, llm_counter, crash_state = _run(
            f"pb_{kill}", crash=kill)
        counts = summary["counts"]
        assert counts["reaction_events"] == 2, kill
        assert counts["event_products"] == baseline["counts"][
            "event_products"], kill
        assert counts["path_instances"] == baseline["counts"][
            "path_instances"], kill
        # resume 成功已证明重算幂等(否则 ArtifactConflict/EventConflict)
        # —— 崩溃时刻已有的草稿/最终裁决恢复后逐字节不变(恢复只增不改性;
        # kill 在首个提交即触发,后续路径在恢复后才处理,集合只增不变)
        for name, snap in (("report_adjudication_draft.json",
                            crash_state["draft"]),
                           ("report_adjudication.json",
                            crash_state["final"])):
            after = _all_payload_hashes(runs_root, name)
            for h in snap:
                assert h in after, (kill, name)
        # LLM 调用账:恢复不多耗(fake 计数 = 基线)
        assert llm_counter.read_text() == base_llm.read_text(), kill
        # 无悬空:每份草稿都有对应最终裁决
        results = runs_root / "pb_cmp" / "results"
        drafts = list(results.glob("*/report_adjudication_draft.json"))
        finals = list(results.glob("*/report_adjudication.json"))
        assert len(drafts) == len(finals) == 2, kill
        for d in drafts:
            dp = json.loads(d.read_text())["payload"]
            assert any(
                json.loads(f.read_text())["payload"]["path_id"] == dp["path_id"]
                for f in finals), kill


def test_all_products_rejected_finalizes_no_event(tmp_path):
    """选中卡全被拒(全部无效 SMILES):no_event 终态最终化 + dead_end,
    其他卡不因模型/策略被偷换提交。"""
    a = _rec("btA", ["C(C(", "((("], rank=1)
    summary, runs_root = run_scripted(
        "pb7", {S: [a]}, smiles=CATECHOL, max_depth=1,
        max_expansions=4, max_frontier_width=3, runs_root=tmp_path)
    root_pid = stable_id("p", "pb7", "root", S)
    assert summary["counts"]["reaction_events"] == 0
    assert summary["stop_reason"] == "completed"
    final = _read_final_adjudication(runs_root, "pb7", root_pid)
    assert final["event"]["no_event"] is True
    assert final["event"]["no_event_reason"]
    assert final["n_committed"] == 0
    assert all(not r["reportable"] for r in final["products"])


def test_rank_selected_rejected_report_only_alternative(tmp_path):
    """rank 模式选中卡全被拒、order 中 B 合格:B 只报告不提交(dead_end);
    不偷换 B 提交事件。"""
    a = _rec("btA", ["C(C("], rank=1)      # 全无效
    b = _rec("btB", [P2], rank=2)
    model = fake_model({"rank_candidates": [
        rank_response("E-btA", order=["E-btA", "E-btB"])]})
    summary, runs_root = run_scripted(
        "pb8", {S: [a, b]}, smiles=CATECHOL, max_depth=1,
        max_expansions=4, max_frontier_width=3, runs_root=tmp_path,
        model=model)
    root_pid = stable_id("p", "pb8", "root", S)
    assert summary["counts"]["reaction_events"] == 0
    final = _read_final_adjudication(runs_root, "pb8", root_pid)
    assert final["event"]["no_event"] is True
    ranked = [r for r in final["products"] if r["reportable"]]
    assert [r["evidence_id"] for r in ranked] == ["E-btB"]
    assert ranked[0]["committed_event_ref"] is None
    # B 无产物路径(未提交 → 不产生下一步)
    children = [p for p in load_report(runs_root, "pb8")["path_instances"]
                if p["parent_path_id"] == root_pid]
    assert children == []


# ------------------------------------------------- R1 修复回归(工作流级)


def test_dirty_selected_card_zero_commit_workflow(tmp_path):
    """Review R1 P1 完整工作流回归:两张 usable recorded 进入 rank;第三张
    异底物 recorded 卡混进检索,fake 模型试图选它且 order 排第一。

    双重防线:任务候选筛选(R1 修复)把脏卡挡在 PredictionTask 外 →
    引用它的响应 = invalid_evidence_id,有界重试耗尽后显式停留 ——
    零提交、零报告该卡、调用账 = 1+max_parse_retries、状态清晰。
    不依赖 Phase C 代码。"""
    a = _rec("btA", [P1], rank=1)
    b = _rec("btB", [P2], rank=2)
    dirty = evidence("btDIRTY", "recorded_reaction", S, ["CC#N"], rank=3,
                     extra={"query_identity": S,
                            "reactant_identity": "CN"})
    resp = json.dumps({"decision": "select", "evidence_id": "E-btDIRTY",
                       "order": ["E-btDIRTY", "E-btA", "E-btB"],
                       "reasons": {}, "reason": "选第三张"})
    model = fake_model({"rank_candidates": [resp]})
    summary, runs_root = run_scripted(
        "r1dirty", {S: [a, b, dirty]}, smiles=CATECHOL, max_depth=1,
        max_expansions=6, max_frontier_width=3, runs_root=tmp_path,
        model=model)
    # 零提交、零裁决:脏卡未入选,预测引用非法 ID 后停留
    assert summary["counts"]["reaction_events"] == 0
    assert summary["stop_reason"] == "awaiting_prediction"
    results = runs_root / "r1dirty" / "results"
    assert not list(results.glob("*/report_adjudication*.json"))
    # 有界重试:1 次首调 + 2 次重试(max_parse_retries=2)全部落盘
    assert len(list(results.glob("*/prediction_call.*.json"))) == 3
    # 防线一:脏卡不进 PredictionTask(任务候选 = 完整资格判据筛选)
    task_env = json.loads(next(results.glob("*/prediction_task.json"))
                          .read_text())["payload"]
    task_ids = {c["evidence_id"] for c in task_env["candidates"]}
    assert "E-btDIRTY" not in task_ids
    assert task_ids == {"E-btA", "E-btB"}
    # 防线二(选中卡资格复验)由纯函数层测试覆盖
    # (test_report_adjudication::test_dirty_selected_card_never_ranked)
    # 状态清晰:awaiting_prediction + prediction_failed 拒因
    root_pid = stable_id("p", "r1dirty", "root", S)
    rep = load_report(runs_root, "r1dirty")
    root_rec = next(p for p in rep["path_instances"]
                    if p["path_id"] == root_pid)
    assert root_rec["status"] == "awaiting_prediction"
    assert "prediction_failed" in root_rec["status_reason"]


def test_donor_not_exact_card_blocked_from_task(tmp_path):
    """donor_exact_match=false 的 recorded 卡同样不进 rank 任务候选。"""
    a = _rec("btA", [P1], rank=1)
    b = _rec("btB", [P2], rank=2)
    dirty = evidence("btD2", "recorded_reaction", S, ["CC#N"], rank=3,
                     extra={"source_record": {"donor_exact_match": False,
                                              "btid": "x"}})
    model = fake_model({"rank_candidates": [
        rank_response("E-btA", order=["E-btA", "E-btB"])]})
    summary, runs_root = run_scripted(
        "r1d2", {S: [a, b, dirty]}, smiles=CATECHOL, max_depth=1,
        max_expansions=6, max_frontier_width=3, runs_root=tmp_path,
        model=model)
    assert summary["counts"]["reaction_events"] == 1  # 正常解耦行为不回退
    results = runs_root / "r1d2" / "results"
    task_env = json.loads(next(results.glob("*/prediction_task.json"))
                          .read_text())["payload"]
    assert "E-btD2" not in {c["evidence_id"] for c in task_env["candidates"]}


def test_validation_refs_resolve_end_to_end(tmp_path):
    """R1 P1-2 工作流回归:选中卡可报告条目引用 validation.json、未选中
    可报告卡引用 cardval.<...>.json;按引用回查逐项一致;导出成功。"""
    a = _rec("btA", [P1], rank=1)
    b = _rec("btB", [P2], rank=2)
    model = fake_model({"rank_candidates": [
        rank_response("E-btA", order=["E-btA", "E-btB"])]})
    summary, runs_root = run_scripted(
        "r1refs", {S: [a, b]}, smiles=CATECHOL, max_depth=1,
        max_expansions=6, max_frontier_width=3, runs_root=tmp_path,
        model=model)
    assert summary["counts"]["reaction_events"] == 1
    root_pid = stable_id("p", "r1refs", "root", S)
    final = _read_final_adjudication(runs_root, "r1refs", root_pid)
    from pathway_v43.services.report_adjudication import (
        resolve_adjudication_validation_refs)

    summary_r = resolve_adjudication_validation_refs(
        runs_root / "r1refs", final)
    assert summary_r["n_reportable_checked"] == 2
    by_card = {r["evidence_id"]: r for r in final["products"]}
    sel_ref = by_card["E-btA"]["validation_ref"]
    unsel_ref = by_card["E-btB"]["validation_ref"]
    assert sel_ref["artifact"] == "validation"
    # 选中卡引用 validation task 目录;未选中卡引用 adjudication task 目录
    # 下的 cardval 产物 —— 两者 task_id 不同是设计使然
    assert unsel_ref["artifact"].startswith("cardval.")
    assert unsel_ref["task_id"] != sel_ref["task_id"]
    assert sel_ref["payload_sha256"] and unsel_ref["payload_sha256"]
    assert sel_ref["payload_sha256"] != unsel_ref["payload_sha256"]
    # 卡级记录同样携带引用
    cards = {c["evidence_id"]: c for c in final["cards"]}
    assert cards["E-btA"]["validation_ref"] == sel_ref
    assert cards["E-btB"]["validation_ref"] == unsel_ref
    # 导出按同一读取端回查通过
    from pathway_v43.output.export_v3 import export_run_v3

    export_run_v3(runs_root, "r1refs")


def test_validation_ref_tamper_fails_export(tmp_path):
    """裁决条目引用被篡改(指向不存在产物)→ 导出 fail-closed。"""
    a = _rec("btA", [P1], rank=1)
    summary, runs_root = run_scripted(
        "r1tamp", {S: [a]}, smiles=CATECHOL, max_depth=1,
        max_expansions=4, max_frontier_width=3, runs_root=tmp_path)
    root_pid = stable_id("p", "r1tamp", "root", S)
    final = _read_final_adjudication(runs_root, "r1tamp", root_pid)
    # 篡改引用的 payload_sha256(信封哈希同步重算,模拟"合法"裁决被改)
    results = runs_root / "r1tamp" / "results"
    adj_path = next(p for p in results.glob("*/report_adjudication.json"))
    envelope = json.loads(adj_path.read_text())
    envelope["payload"]["products"][0]["validation_ref"]["payload_sha256"] \
        = "f" * 64
    from pathway_v43.domain.models import content_hash

    envelope["payload_hash"] = content_hash(envelope["payload"])
    adj_path.write_text(json.dumps(envelope, ensure_ascii=False) + "\n")
    from pathway_v43.output.export_v3 import LedgerCorrupt, export_run_v3

    with pytest.raises(LedgerCorrupt):
        export_run_v3(runs_root, "r1tamp")


# ------------------------------------------------- R2 修复回归(工作流级)


def test_rule_card_selected_via_rank_zero_commit(tmp_path):
    """R2 P1 端到端复现:两张合格 recorded 进入 rank + 一张规则卡混在
    检索;fake 模型选规则卡且 order 排第一。

    双重防线:① rank 任务候选只含合格 recorded(规则卡不进任务,引用
    它的响应 = invalid_evidence_id → 有界重试 → 停留);② 裁决层守卫
    (纯函数夹具覆盖:检索层规则卡即使被选中也不升格)。结果零提交、
    零报告该卡、账本无 kind=rule_application 事件。"""
    a = _rec("btA", [P1], rank=1)
    b = _rec("btB", [P2], rank=2)
    rule = _rule("btR", ["CC(N)=O"], rank=3)
    resp = json.dumps({"decision": "select", "evidence_id": "E-btR",
                       "order": ["E-btR", "E-btA", "E-btB"],
                       "reasons": {}, "reason": "选规则卡"})
    model = fake_model({"rank_candidates": [resp]})
    summary, runs_root = run_scripted(
        "r2rule", {S: [a, b, rule]}, smiles=CATECHOL, max_depth=1,
        max_expansions=6, max_frontier_width=3, runs_root=tmp_path,
        model=model)
    # 零提交;无 rule_application 事件
    assert summary["counts"]["reaction_events"] == 0
    results = runs_root / "r2rule" / "results"
    assert not list(results.glob("*/report_adjudication*.json"))
    # 防线①:规则卡不进 rank 任务候选
    task_env = json.loads(next(results.glob("*/prediction_task.json"))
                          .read_text())["payload"]
    task_ids = {c["evidence_id"] for c in task_env["candidates"]}
    assert "E-btR" not in task_ids
    assert task_ids == {"E-btA", "E-btB"}
    # 状态清晰:有界重试后停留,调用账 = 1 + max_parse_retries
    assert summary["stop_reason"] == "awaiting_prediction"
    assert len(list(results.glob("*/prediction_call.*.json"))) == 3
    root_pid = stable_id("p", "r2rule", "root", S)
    rep = load_report(runs_root, "r2rule")
    root_rec = next(p for p in rep["path_instances"]
                    if p["path_id"] == root_pid)
    assert root_rec["status"] == "awaiting_prediction"


def test_rule_card_rank_guard_at_adjudication_layer(tmp_path):
    """R2 P1 防线②(纯函数到导出贯通):绕过任务筛选直接构造"选中检索层
    规则卡"的裁决 → 规则卡 card_eligible=false、产物零占位、带
    not_validated_for_reporting 拒因;正常 recorded 选中不受影响。"""
    from pathway_v43.services.report_adjudication import (
        adjudicate_parent, validate_card_for_reporting)

    a = _rec("btA", [P1], rank=1)
    rule = _rule("btR", ["CC(N)=O"], rank=3)
    result = {"outcome": "selected", "mode": "rank_candidates",
              "selected_evidence_id": "E-btR",
              "order": ["E-btR", "E-btA"], "task_id": "T-x", "attempt": 1}
    card_validations = {"E-btA": validate_card_for_reporting(
        card=a, substrate_identity=S, ancestry_cns=[S],
        entry_layer="retrieval")}
    payload = adjudicate_parent(
        run_id="r", path_id="p-root", substrate_identity=S,
        retrieval_payload={"query": {"substrate_identity": S},
                           "evidences": [a, rule]},
        decision_payload={"accepted_evidence_id": None},
        prediction_task={"candidates": [
            {"evidence_id": "E-btR"}, {"evidence_id": "E-btA"}]},
        prediction_result=result,
        selected_evidence_id="E-btR", selected_card=rule,
        selected_validation={
            "evidence_id": "E-btR",
            "gates": {"direction_source": {"ok": True, "reason": ""},
                      "atom_mapping": {"ok": True, "reason": ""}},
            "verdicts": [{"position": 0,
                          "product_smiles": "CC(N)=O",
                          "product_identity": cn_identity("CC(N)=O"),
                          "accepted": True, "reasons": []}],
            "n_accepted": 1, "n_total": 1},
        card_validations=card_validations,
        validation_refs={
            "E-btR": {"task_id": "T-val", "artifact": "validation",
                      "payload_sha256": "0" * 64},
            "E-btA": {"task_id": "T-adj", "artifact": "cardval.E-btA",
                      "payload_sha256": "1" * 64}},
        stage="draft")
    rule_entry = next(r for r in payload["products"]
                      if r["evidence_id"] == "E-btR")
    assert not rule_entry["reportable"] and rule_entry["report_rank"] is None
    assert any("not_validated_for_reporting" in r
               for r in rule_entry["reasons"])
    rule_card = next(c for c in payload["cards"]
                     if c["evidence_id"] == "E-btR")
    assert rule_card["selected"] and not rule_card["card_eligible"]
    # 干净 recorded 卡在 order 内仍正常占位(不连坐)
    ranked = [r["evidence_id"] for r in payload["products"]
              if r["reportable"]]
    assert ranked == ["E-btA"]
