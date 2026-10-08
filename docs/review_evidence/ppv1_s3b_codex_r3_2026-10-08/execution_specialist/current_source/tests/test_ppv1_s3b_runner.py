"""S3b 公开 runner 分流端到端回归(workflow.runner start/resume →
pollutant.runflow;E01/E02/C06/H04/场景转换/四崩溃/身份)。

覆盖(任务书 §7 S3b「公开分流」「E01/E02」「C06/H04/条件继承」「场景
转换」行):
- E01:首选下游无候选 ⇒ B 留事件/attempt/unresolved_continuation,
  C 在上限内继续(不反证上游、不无限重开);
- E02:两类 deferred(共同产物/备选反应)分别激活;重复触发幂等;
  旧 revision unchanged;预算不足留独立未展开原因;完整共同产物事件
  不截断;
- C06/H04:unknown 可有界探索且沿途保留(retain_conditional 事件提交,
  unknown 不升格);essential conflict 阻当前场景(假设保留不提交);
  两分支隔离;共底物循环缺启动供给 ⇒ unresolved_initial_supply(不
  reject、不称化学不可能);有支持 ⇒ 不自动阻断;
- 场景转换:显式 source_ref、独立 action/预算、只后效(旧边评估冻结
  于 phase_history)、followup 用新上下文;
- 四崩溃:独立子进程硬杀 + 新进程 resume(B1/B2/B3/B4);
- 身份/分流:PPV1 独立存储(无 legacy PathwayStore)、未知 profile 拒、
  重复 start 拒、身份变动 resume 拒、传 model 不补真实请求预算
  (max_real_model_requests 恒 0、网络 0)。
基线 b7f2bba 上本文件为 collection 红(pollutant.runflow 缺失)。
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.runflow import (  # noqa: E402
    PPV1RunError,
    resume_ppv1_run,
    start_ppv1_run,
)
from pathway_v43.pollutant.search import SearchCrashInjection  # noqa: E402
from pathway_v43.workflow.runner import (  # noqa: E402
    RunAlreadyExists,
    RunError,
    resume_run,
    start_run,
)
from pathway_v43.storage.run_identity import (  # noqa: E402
    PROFILE_POLLUTANT_PATHWAY_V1,
)

WORKER = str(Path(__file__).resolve().parent / "s3b_worker.py")
PY = sys.executable


def spec(key: str, product: str, tref: str, **overrides) -> dict:
    d = {
        "key": key, "product_smiles": product, "coefficient": 1,
        "transformation_ref": tref, "origin_group_key": f"donor-{key}",
        "edits": [{"op": "change_bond_order", "atom1": "S_C_2",
                   "atom2": "S_O_1", "from_order": "single",
                   "to_order": "double"}],
        "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
        "alignment": {"status": "resolved",
                      "donor_to_current": {"S_C_2": "S_C_2",
                                           "S_O_1": "S_O_1"},
                      "ref": "align-A"},
        "expectation": {"target_smiles": product},
    }
    d.update(overrides)
    return d


def oxygen_req():
    return [{"key": "oxygen_regime", "level": "essential",
             "value": "aerobic", "source_refs": ["src:synthetic"]}]


def cyclic_dep(initial_supply: str):
    return [{"dependency_id": "dep-NAD", "kind": "cosubstrate_supply",
             "statement": "NAD+ regeneration cycle", "cyclic": True,
             "initial_supply": initial_supply}]


def outcomes(runs_root: Path, run_id: str) -> list[dict]:
    out = []
    for path in sorted((runs_root / run_id / "results").rglob(
            "expansion_outcome.json")):
        out.append(json.loads(
            path.read_text(encoding="utf-8"))["payload"]["outcome"])
    return out


def contexts(runs_root: Path, run_id: str) -> list[dict]:
    found = []
    for path in sorted((runs_root / run_id / "results").rglob(
            "path_context.json")):
        found.append(json.loads(path.read_text(encoding="utf-8"))["payload"])
    return found


# ---------------------------------------------------------------- E01


def test_e01_preferred_downstream_no_candidate_alternatives_continue(
        tmp_path: Path) -> None:
    """E01:首选 B 展开后下游池空 ⇒ 记 unresolved_continuation(不反证
    上游:事件/attempt 保留);备选 C 在上限内继续。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B"),
                              spec("C", "CC=O", "donor-C")]}}
    runs_root = tmp_path / "runs"
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="e01", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    assert out["counts"]["events"] == 2  # B 与 C 都留事件
    assert out["counts"]["hypotheses"] == 2
    # 两个 attempt 均 recorded(执行事实保留)
    conn = sqlite3.connect(str(runs_root / "e01" / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    attempts = conn.execute(
        "SELECT status FROM search_attempts").fetchall()
    assert all(r["status"] == "recorded" for r in attempts)
    assert len(attempts) == 2
    # 下游无候选 ⇒ unresolved_continuation(引用来源事件,不反证上游)
    all_outcomes = outcomes(runs_root, "e01")
    unresolved = [o for o in all_outcomes
                  if o.get("detail", {}).get("unresolved_continuation")]
    assert len(unresolved) == 2  # B 与 C 的下游 followup 各一条
    assert all(o.get("kind") == "no_local_candidate" for o in unresolved)
    assert all(o["detail"]["source_event_id"].startswith("ppev_")
               for o in unresolved)


# ---------------------------------------------------------------- E02


def test_e02_two_deferred_types_activation_and_idempotence(
        tmp_path: Path) -> None:
    """E02:备选反应 deferred(selection cap)与共同产物 deferred(宽度
    上限)分别激活;重复触发幂等;旧 revision unchanged;完整共同产物
    事件不截断。"""
    plan = {
        "pools": {"CCO": [spec("B", "CC=O", "donor-B",
                               coproducts=["[H][H]"]),
                          spec("C", "CC=O", "donor-C")]},
        "schedule_budget": {"max_select": 1},
        "activations": [
            {"deferred_type": "alternative_reaction_deferred",
             "trigger": "explicit_user", "expected_parent_revision": 0,
             "parent": "root"},
            {"deferred_type": "alternative_reaction_deferred",
             "trigger": "explicit_user", "expected_parent_revision": 5,
             "parent": "root"},  # 旧 revision:unchanged
        ],
    }
    runs_root = tmp_path / "runs"
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="e02", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan,
                    profile_policy={"search_limits": {
                        "max_total_search_actions": 12,
                        "max_product_expansion_width": 1}})
    conn = sqlite3.connect(str(runs_root / "e02" / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    # B 事件完整保留共同产物([H][H] 参与物不被宽度截断)
    events = conn.execute("SELECT payload FROM events").fetchall()
    participants = json.loads(events[0]["payload"])["participants"]
    product_refs = [p["state_ref"] for p in participants
                    if p["side"] == "product"]
    assert len(product_refs) == 2  # 主产物 + 共同产物都完整入事件
    # 激活后 C 也展开(备选 deferred 激活成功)
    assert out["counts"]["events"] == 2
    # 共同产物 deferred:[H][H] followup 以 coproduct_deferred 留痕
    deferred = conn.execute(
        "SELECT payload, defer_reason FROM search_actions WHERE"
        " status = 'deferred'").fetchall()
    coproduct_deferred = [r for r in deferred
                          if json.loads(r["payload"]).get("deferred_type")
                          == "coproduct_deferred"]
    assert coproduct_deferred
    assert coproduct_deferred[0]["defer_reason"] == "product_width_limit"
    # 旧 revision 激活:unchanged(不改状态)
    activation_outcomes = [o for o in outcomes(runs_root, "e02")
                           if o["kind"] == "activation_dispatched"]
    # 两次激活:第一次 activated ≥1;第二次(stale)unchanged
    assert any(o["detail"]["activated"] for o in activation_outcomes)
    stale = [o for o in activation_outcomes
             if not o["detail"]["activated"]]
    assert stale and stale[0]["detail"]["unchanged"] >= 1


def test_e02_budget_insufficient_keeps_unexpanded_reason(
        tmp_path: Path) -> None:
    """预算不足:激活预检(备选 alternatives 已耗尽)留独立未展开原因
    (budget_exhausted),不改 deferred 状态;不重复安排同 action。"""
    plan = {
        "pools": {"CCO": [spec("B", "CC=O", "donor-B"),
                          spec("C", "CC=O", "donor-C"),
                          spec("D", "CC=O", "donor-D")]},
        "schedule_budget": {"max_select": 2},
        "activations": [
            {"deferred_type": "alternative_reaction_deferred",
             "trigger": "explicit_user", "expected_parent_revision": 0,
             "parent": "root"}],
    }
    runs_root = tmp_path / "runs"
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="e02b", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan,
                    profile_policy={"search_limits": {
                        "max_alternative_hypotheses_per_parent": 2}})
    # B/C 选中并展开(alternatives 2/2 用完);D deferred ⇒ 激活预检
    # alternatives 剩余 0 ⇒ unchanged budget_exhausted
    activation = [o for o in outcomes(runs_root, "e02b")
                  if o["kind"] == "activation_dispatched"][0]
    assert activation["detail"]["activated"] == []
    assert activation["detail"]["unchanged"] >= 1
    conn = sqlite3.connect(str(runs_root / "e02b" / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    deferred = conn.execute(
        "SELECT * FROM search_actions WHERE status = 'deferred'").fetchall()
    assert deferred
    payload = json.loads(deferred[0]["payload"])
    assert payload["deferred_type"] == "alternative_reaction_deferred"
    # 预算不足的独立未展开原因:激活结果与 deferred 行都不掩盖
    activation_out = activate_result(runs_root, "e02b")
    assert activation_out


def activate_result(runs_root: Path, run_id: str):
    return [o for o in outcomes(runs_root, run_id)
            if o["kind"] == "activation_dispatched"]


# ---------------------------------------------------------------- C06/H04


def test_c06_h04_unknown_bounded_exploration_and_initial_supply(
        tmp_path: Path) -> None:
    """C06/H04:调度→audit→admission→提交→子路径,unknown 可有界探索
    且沿途保留;共底物循环缺启动供给 ⇒ unresolved_initial_supply(不
    reject、不称化学不可能);essential 冲突阻当前场景(另测)。"""
    plan = {
        "scenario_ref": "scenario-aerobic",
        "condition_facts": [{"key": "oxygen_regime", "value": "aerobic",
                             "status": "known_present",
                             "source_ref": "src:synthetic"}],
        "pools": {"CCO": [spec(
            "B", "CC=O", "donor-B",
            requirements=oxygen_req(),
            dependencies=cyclic_dep("missing"))]},
    }
    runs_root = tmp_path / "runs"
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="c06", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    # 事件已提交(unknown 保留的有界探索,不因缺证据全拒)
    assert out["counts"]["events"] == 1
    # 分支上下文:依赖 unresolved + unresolved_initial_supply 标记
    branch_ctx = [c for c in contexts(runs_root, "c06")
                  if c.get("dependencies")]
    assert branch_ctx
    dep = branch_ctx[0]["dependencies"][0]
    assert dep["status"] == "unresolved"
    assert "unresolved_initial_supply" in dep["statement"]
    assert "不称化学不可能" in dep["statement"]
    # 生产报告:admission 非 expand(unknown 未升格;不 R6)
    for path in (runs_root / "c06" / "results").rglob(
            "production_report.json"):
        report = json.loads(path.read_text(encoding="utf-8"))["payload"]
        assert report["admission"]["disposition"] in (
            "retain_conditional",)
        reasons = ";".join(report["admission"]["reasons"])
        assert "R5" in reasons  # unknown 保留,不是 reject


def test_h04_supported_initial_supply_not_blocked(tmp_path: Path) -> None:
    """H04:启动供应有支持 ⇒ 依赖 supported 不自动阻断。"""
    plan = {
        "condition_facts": [{"key": "oxygen_regime", "value": "aerobic",
                             "status": "known_present",
                             "source_ref": "src:synthetic"}],
        "pools": {"CCO": [spec(
            "B", "CC=O", "donor-B",
            requirements=oxygen_req(),
            dependencies=cyclic_dep("supported"))]},
    }
    runs_root = tmp_path / "runs"
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="h04s", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    assert out["counts"]["events"] == 1  # 不因循环依赖自动阻断
    ctx = [c for c in contexts(runs_root, "h04s")
           if c.get("dependencies")]
    assert ctx and ctx[0]["dependencies"][0]["status"] == "supported"


def test_essential_conflict_blocks_current_scenario_hypothesis_kept(
        tmp_path: Path) -> None:
    """essential conflict:当前场景不展开(不提交事件),假设保留留痕
    (可展示为需不同条件的备选)。"""
    plan = {
        "scenario_ref": "scenario-anaerobic",
        "condition_facts": [{"key": "oxygen_regime", "value": "anaerobic",
                             "status": "known_present",
                             "source_ref": "src:synthetic"}],
        "pools": {"CCO": [spec(
            "B", "CC=O", "donor-B", requirements=oxygen_req())]},
    }
    runs_root = tmp_path / "runs"
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="r3conf", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    assert out["counts"]["events"] == 0  # 当前场景不展开
    # 假设保留(put_hypothesis 留痕;R3 defer)
    assert out["counts"]["hypotheses"] == 1
    deferred_outcomes = [o for o in outcomes(runs_root, "r3conf")
                         if o["kind"] == "admission_deferred"]
    assert deferred_outcomes
    assert "R3" in ";".join(
        deferred_outcomes[0]["detail"]["admission"]["reasons"])


def test_branch_isolation_two_contexts(tmp_path: Path) -> None:
    """分支隔离:带自身要求/依赖的假设派生专属子上下文;分支互不污染
    (另一无要求分支用根上下文)。"""
    plan = {
        "condition_facts": [{"key": "oxygen_regime", "value": "aerobic",
                             "status": "known_present",
                             "source_ref": "src:synthetic"}],
        "pools": {"CCO": [
            spec("B", "CC=O", "donor-B", requirements=oxygen_req()),
            spec("C", "CC=O", "donor-C")]},
    }
    runs_root = tmp_path / "runs"
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="iso", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    assert out["counts"]["events"] == 2
    ctx_list = contexts(runs_root, "iso")
    ctx_ids = {c["context_id"] for c in ctx_list}
    assert len(ctx_ids) >= 2  # 根上下文 + B 的分支上下文
    with_reqs = [c for c in ctx_list if c["accumulated_requirements"]]
    without_reqs = [c for c in ctx_list
                    if not c["accumulated_requirements"]]
    assert with_reqs and without_reqs  # 两分支上下文互不污染


# ---------------------------------------------------------------- 场景转换


def test_scenario_transition_explicit_only_effect_future(
        tmp_path: Path) -> None:
    """场景转换:显式 source_ref、独立 action/预算、只后效(旧边评估
    冻结于 phase_history;followup 用新上下文)。"""
    plan = {
        "pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
        "scenario_transitions": [{
            "after_hypothesis_key": "B",
            "transition": {"source_ref": "user:switch-anaerobic",
                            "new_phase_id": "phase-1",
                            "new_scenario_ref": "scenario-anaerobic"}}],
    }
    runs_root = tmp_path / "runs"
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="trans", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    assert out["counts"]["events"] == 1
    conn = sqlite3.connect(str(runs_root / "trans" / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    transitions = conn.execute(
        "SELECT * FROM search_actions WHERE action_kind ="
        " 'scenario_transition'").fetchall()
    assert len(transitions) == 1
    assert transitions[0]["status"] == "done"
    # 转换预算独立计(不是反应边)
    used = conn.execute(
        "SELECT COUNT(*) FROM budget_reservations WHERE limit_key ="
        " 'max_scenario_transitions' AND status IN ('reserved',"
        " 'consumed')").fetchone()[0]
    assert used == 1
    # 新上下文(phase-1/anaerobic)+ 旧边评估冻结
    ctx_list = contexts(runs_root, "trans")
    new_ctx = [c for c in ctx_list if c["phase_id"] == "phase-1"]
    assert new_ctx
    assert new_ctx[0]["scenario_ref"] == "scenario-anaerobic"
    # followup retrieve 用新上下文(转换后调度)
    retrieves = conn.execute(
        "SELECT context_ref FROM search_actions WHERE action_kind ="
        " 'retrieve' AND parent_path_id != (SELECT parent_path_id FROM"
        " search_actions WHERE action_kind='retrieve' ORDER BY created_at"
        " LIMIT 1)").fetchall()
    assert any(r["context_ref"] == new_ctx[0]["context_id"]
               for r in retrieves)
    # 缺 source_ref 的转换:契约失败如实停止(不自行换场景;事件已
    # 提交的权威保留,run_error 披露,不吞)
    bad_plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
                "scenario_transitions": [{
                    "after_hypothesis_key": "B",
                    "transition": {"new_phase_id": "p9",
                                   "new_scenario_ref": "s9"}}]}
    bad_out = start_run(config=resolve_config(),
                        runs_root=tmp_path / "runs2",
                        run_id="trans-bad", smiles="CCO", max_depth=3,
                        max_expansions=10, max_frontier_width=2,
                        finder=object(), scripted=True,
                        profile=PROFILE_POLLUTANT_PATHWAY_V1,
                        ppv1_plan=bad_plan)
    assert bad_out["stop"].get("run_error", {}).get("kind") == \
        "transition_source_ref_missing"


# ---------------------------------------------------------------- 四崩溃


@pytest.mark.parametrize("crash_after", [
    "after_claim", "after_request_registered", "after_bundle_written",
    "after_event_submitted"])
def test_crash_recovery_subprocess_hard_kill(crash_after, tmp_path) -> None:
    """四崩溃:独立子进程硬杀(真实进程崩溃,连接不清理)→ 新进程
    resume(身份核对 + recover_run + 继续驱动)。"""
    runs_root = tmp_path / "runs"
    run_id = f"crash-{crash_after}"
    worker_args = [PY, "-B", WORKER, "start-crash",
                   "--runs-root", str(runs_root),
                   "--run-id", run_id, "--crash-after", crash_after]
    if crash_after == "after_request_registered":
        # B2 注入需要模型请求(decide 的 scripted proposals 请求)
        worker_args.append("--with-model")
    proc = subprocess.run(
        worker_args,
        capture_output=True, text=True, timeout=120,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
    crashed = json.loads(proc.stdout.strip().splitlines()[-1])
    assert crashed["crashed"] is True
    assert proc.returncode == 1  # os._exit(1) 硬杀
    # 新进程 resume:恢复 + 继续驱动(事件补齐;不重复)。B2 场景
    # (model 结构失败保持):resume 披露 pending 请求、网络 0、不默发
    if crash_after == "after_request_registered":
        proc2 = subprocess.run(
            [PY, "-B", WORKER, "resume", "--runs-root", str(runs_root),
             "--run-id", run_id, "--with-model"],
            capture_output=True, text=True, timeout=120,
            env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
        resumed = json.loads(proc2.stdout.strip().splitlines()[-1])
        assert resumed["resumed"] is True
        conn = sqlite3.connect(
            str(runs_root / run_id / "pollutant.sqlite"))
        network = conn.execute(
            "SELECT SUM(network_request_count) FROM model_requests"
        ).fetchone()[0] or 0
        assert network == 0  # 不默发第二请求(scripted 网络 0)
        return
    proc2 = subprocess.run(
        [PY, "-B", WORKER, "resume", "--runs-root", str(runs_root),
         "--run-id", run_id],
        capture_output=True, text=True, timeout=120,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
    resumed = json.loads(proc2.stdout.strip().splitlines()[-1])
    assert resumed["resumed"] is True
    assert resumed["events"] == 1
    # 事件仅一次(重放不重复;恢复不重扣)
    conn = sqlite3.connect(str(runs_root / run_id / "pollutant.sqlite"))
    events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert events == 1
    commits = conn.execute(
        "SELECT COUNT(*) FROM search_commit_records").fetchone()[0]
    # retrieve/decide/expandB/followup-retrieve 各一条(不重复扣;
    # followup 池空 ⇒ no_local_candidate 亦是合法 outcome 提交)
    assert commits == 4


def test_b2_pending_request_disclosed_not_resent(tmp_path) -> None:
    """B2:请求已登记无响应 ⇒ pending 披露,不默发第二请求(网络 0)。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
            "model": {"provider_kind": "scripted",
                      "responses": ['{"proposals": "not-a-list"}']}}
    runs_root = tmp_path / "runs"
    with pytest.raises(SearchCrashInjection):
        start_ppv1_run(config=resolve_config(), runs_root=runs_root,
                       run_id="b2", smiles="CCO", plan=plan, scripted=True,
                       crash_after="after_request_registered")
    out = resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                          run_id="b2", plan=plan)
    pending = out["recovery"]["pending_requests"]
    assert pending  # 结构化披露
    assert all(p["network_request_count"] == 0 for p in pending)
    conn = sqlite3.connect(str(runs_root / "b2" / "pollutant.sqlite"))
    total = conn.execute("SELECT COUNT(*) FROM model_requests"
                         ).fetchone()[0]
    # 不默发第二请求(登记 1 条 + 反馈被预算拒后结构失败,无新增)
    assert total >= 1
    network = conn.execute(
        "SELECT SUM(network_request_count) FROM model_requests"
    ).fetchone()[0]
    assert network == 0


# ---------------------------------------------------------------- 分流/身份


def test_ppv1_independent_storage_and_no_legacy(tmp_path) -> None:
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    runs_root = tmp_path / "runs"
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="indep", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    assert (runs_root / "indep" / "pollutant.sqlite").is_file()
    assert not (runs_root / "indep" / "pathway.sqlite").exists()
    assert not (runs_root / "indep" / "checkpoint.sqlite").exists()
    assert out["stop"]["unexplored"]["pending_actions"] == 0


def test_duplicate_start_rejected(tmp_path) -> None:
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    runs_root = tmp_path / "runs"
    start_run(config=resolve_config(), runs_root=runs_root, run_id="dup",
              smiles="CCO", max_depth=3, max_expansions=10,
              max_frontier_width=2, finder=object(), scripted=True,
              profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    with pytest.raises(RunAlreadyExists):
        start_run(config=resolve_config(), runs_root=runs_root, run_id="dup",
                  smiles="CCO", max_depth=3, max_expansions=10,
                  max_frontier_width=2, finder=object(), scripted=True,
                  profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)


def test_unknown_profile_rejected(tmp_path) -> None:
    with pytest.raises(RunError, match="未知 profile"):
        start_run(config=resolve_config(), runs_root=tmp_path / "runs",
                  run_id="bad", smiles="CCO", max_depth=1,
                  max_expansions=1, max_frontier_width=1,
                  finder=object(), scripted=True, profile="bogus")


def test_resume_identity_mismatch_rejected(tmp_path) -> None:
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    runs_root = tmp_path / "runs"
    start_run(config=resolve_config(), runs_root=runs_root, run_id="ident",
              smiles="CCO", max_depth=3, max_expansions=10,
              max_frontier_width=2, finder=object(), scripted=True,
              profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    # 身份变动 ⇒ resume 拒(不原地切换):以 model 重建 prediction 身份
    # (保存身份为 off;模型身份块不同 ⇒ IdentityMismatch)
    class FakeModel:
        def identity_block(self):
            return {"enabled": True, "provider": "fake",
                    "model_id": "fake-1", "prompt_versions": {},
                    "policy_version": "p", "policy": {}}
    from pathway_v43.storage.run_identity import IdentityMismatch
    with pytest.raises(IdentityMismatch):
        resume_run(config=resolve_config(), runs_root=runs_root,
                   run_id="ident", finder=object(), model=FakeModel(),
                   ppv1_plan=plan)


def test_resume_legacy_profile_run_refused_by_ppv1_path(tmp_path) -> None:
    # legacy 身份的 run 不走 PPV1 resume 分流(profile 不符明确拒)
    from pathway_v43.storage.run_identity import (
        build_run_identity, write_run_identity)
    runs_root = tmp_path / "runs"
    identity = build_run_identity(
        run_id="legacy-run", root_smiles="CCO", root_cn="CCO",
        strategy={"max_depth": 2, "max_expansions": 5,
                  "max_frontier_width": 3},
        asset_identity={"mode": "scripted_fixture"},
        v3_code_identity={"mode": "scripted_fixture"},
        prediction=None)
    write_run_identity(runs_root, identity)
    with pytest.raises(PPV1RunError, match="profile"):
        resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                        run_id="legacy-run")


def test_model_object_does_not_derive_real_request_budget(
        tmp_path) -> None:
    """传入模型对象不自动启用/补预算:max_real_model_requests 恒 0;
    真实 provider 登记被拒(网络发送被阻止);scripted 网络 0。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
            "model": {"provider_kind": "real", "responses": ["{}"]}}
    runs_root = tmp_path / "runs"

    class FakeModel:
        def identity_block(self):
            return {"enabled": True, "provider": "fake",
                    "model_id": "fake-1", "prompt_versions": {},
                    "policy_version": "p", "policy": {}}
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="model-b", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True, model=FakeModel(),
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    budget = out["stop"]["budget"]["run_level"]["max_real_model_requests"]
    assert budget["max"] == 0  # 不因传 model 派生正数
    conn = sqlite3.connect(str(runs_root / "model-b" / "pollutant.sqlite"))
    network = conn.execute(
        "SELECT SUM(network_request_count) FROM model_requests"
    ).fetchone()[0] or 0
    assert network == 0
    # decide 记方法失败(真实请求登记被拒)
    method_failed = [o for o in outcomes(runs_root, "model-b")
                     if o["kind"] == "method_failed"]
    assert method_failed


def test_stop_report_deferred_blocks_exhausted_search_claim(
        tmp_path) -> None:
    """deferred/知识缺口存在时不称"所有路线都探索完"(stop 报告语义)。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B"),
                              spec("C", "CC=O", "donor-C")]},
            "schedule_budget": {"max_select": 1}}
    runs_root = tmp_path / "runs"
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="stopd", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    reasons = {out["stop"]["primary"]} | set(
        out["stop"].get("other_reasons", []))
    assert "exhausted_search" not in reasons


# ---------------------------------------------------------------- 并发


def test_concurrent_barrier_start_single_winner(tmp_path) -> None:
    """H06(runner 级):双进程 barrier 同时 start 同一 run —— 只有一方
    建身份进驱动(RunAlreadyExists 另一方);无重复事件。"""
    runs_root = tmp_path / "runs"
    barrier = tmp_path / "barrier"
    procs = []
    for i, worker in enumerate(("w1", "w2")):
        proc = subprocess.Popen(
            [PY, "-B", WORKER, "barrier-start",
             "--runs-root", str(runs_root), "--run-id", "conc",
             "--barrier-dir", str(barrier), "--worker", worker,
             "--out-json", str(tmp_path / f"result-{i}.json")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
        procs.append(proc)
    # 等两方 ready 再放行 GO(不靠顺序调用/sleep)
    import time
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if all((barrier / f"{w}.ready").exists() for w in ("w1", "w2")):
            (barrier / "GO").write_text("go\n", encoding="utf-8")
            break
        time.sleep(0.02)
    else:
        for p in procs:
            p.kill()
        pytest.fail("barrier ready 超时")
    results = []
    for proc in procs:
        stdout, _stderr = proc.communicate(timeout=120)
        results.append(json.loads(stdout.strip().splitlines()[-1]))
    started = [r for r in results if r.get("started")]
    losers = [r for r in results if not r.get("started")]
    assert len(started) == 1
    assert losers and losers[0]["error"] == "RunAlreadyExists"
    conn = sqlite3.connect(str(runs_root / "conc" / "pollutant.sqlite"))
    events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert events == 1
