"""S3b 回修 r2 回归(Codex S3b 复审 S3B-01~06 六组 P1 的收口;
ppv1-runflow-2 / search-6 / model-proposals-2 / profile-14)。

覆盖(复审报告 §4 六组最低回修,入口→行为→可执行断言):
- S3B-01 冻结计划/池输入身份:start 持久化冻结计划;resume 无 plan
  沿冻结输入(缺输入不变空池);传入内容不符结构化拒(旧任务不消费
  新输入);冻结计划 artifact 被篡改 ⇒ 完整性失败(保全);
- S3B-02 恢复裁定接执行门:坏 bundle(hash/JSON)⇒ 隔离不重执行
  (零坏任务 event/成功 commit;证据保全;合法独立任务继续);合法
  B3 同 output 恢复保持(既有四崩溃测试);
- S3B-03 后续集合完整性:三产物部分调度(2/3)⇒ 恢复逐对象补齐 3/3;
  转换入队后崩溃 ⇒ pending_followup 一次冻结,恢复执行到新上下文;
  B4 事件已提交转换未入队 ⇒ 恢复补齐转换并以后效上下文调度 followup;
- S3B-04 执行会话互斥:两个真实公开 resume 进程(工具入口计数 +
  barrier)只一方执行;竞争方在执行前结构化拒;崩溃后单进程接管
  (原 attempt/预约保持,既有四崩溃测试);
- S3B-05 novel 独立假设消费者:池外提案(内容+来源)⇒ 独立假设走
  固定工具→audit→admission→submit;空池仍组装底物档案并消费模型
  响应;弃权合法;无足够内容结构化拒;
- S3B-06 blocked 原因/对象持久接公开 stop:零深度+预算复合 ⇒ 主因
  budget(优先级不动),depth_limit 入其他原因,blocked 对象入
  unexplored;重复恢复不重数。

红绿分类约定:本文件对直接父基线 c1211183 同字节运行 —— 行为红
(修复目标断言)与合法正控(父亦绿)分开;父上本文件不是 collection
红(模块在父已存在),是行为红。
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.runflow import (  # noqa: E402
    PPV1RunError,
    resume_ppv1_run,
    start_ppv1_run,
)
from pathway_v43.workflow.runner import (  # noqa: E402
    resume_run,
    start_run,
)
from pathway_v43.storage.run_identity import (  # noqa: E402
    PROFILE_POLLUTANT_PATHWAY_V1,
)

WORKER = str(Path(__file__).resolve().parent / "s3b_worker.py")
PY = sys.executable
ENV = {"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"}


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


def novel_response(novel_key: str = "novel:1",
                   product: str = "CC=O",
                   origin: str = "novel_outside_pool") -> str:
    return json.dumps({"proposals": [{
        "hypothesis_id": novel_key,
        "proposal_context": {"reference_hypothesis_ids": [],
                              "output_origin": origin},
        "reaction_spec": {
            "key": "Novel", "product_smiles": product, "coefficient": 1,
            "transformation_ref": f"donor-{novel_key}",
            "origin_group_key": f"donor-{novel_key}",
            "edits": [{"op": "change_bond_order", "atom1": "S_C_2",
                       "atom2": "S_O_1", "from_order": "single",
                       "to_order": "double"}],
            "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
            "alignment": {"status": "resolved",
                          "donor_to_current": {"S_C_2": "S_C_2",
                                               "S_O_1": "S_O_1"},
                          "ref": "align-A"},
            "expectation": {"target_smiles": product}}}]})


def run_worker(*args, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, "-B", WORKER, *args], capture_output=True, text=True,
        timeout=timeout, env=ENV)


def db(runs_root: Path, run_id: str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(runs_root / run_id / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    return conn


def start_crash(runs_root: Path, run_id: str, *, crash_after: str,
                with_model: bool = False, coproducts=None,
                transitions: bool = False, injection: str | None = None,
                policy: dict | None = None) -> subprocess.CompletedProcess:
    args = ["start-crash", "--runs-root", str(runs_root),
            "--run-id", run_id, "--crash-after", crash_after]
    if with_model:
        args.append("--with-model")
    if coproducts:
        args += ["--coproducts", ",".join(coproducts)]
    if transitions:
        args.append("--transitions")
    if injection:
        args += ["--injection", injection]
    if policy:
        # policy 经环境侧注入不可行(worker 不读);策略走 start_run
        # 的 profile_policy —— 子进程模式只用默认策略,需自定义策略
        # 的用例走 in-process start
        raise ValueError("worker start-crash 不接受自定义策略")
    return run_worker(*args)


def artifact_files(runs_root: Path, run_id: str, name: str) -> list[Path]:
    return sorted(
        (runs_root / run_id / "results").rglob(f"{name}.json"))


# ---------------------------------------------------------------- S3B-01


def test_s3b01_resume_without_plan_uses_frozen_input(tmp_path) -> None:
    """B1 崩溃后 resume 不传 plan:沿冻结输入完成旧任务(缺输入不变
    空池;旧任务不消费"空"新输入)。父基线:空池 no_local_candidate
    (行为红)。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "fpo", crash_after="after_claim")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    out = resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                          run_id="fpo", plan=None)
    assert out["counts"]["events"] == 1  # 沿冻结计划完成 B
    conn = db(runs_root, "fpo")
    commits = conn.execute(
        "SELECT COUNT(*) FROM search_commit_records").fetchone()[0]
    assert commits == 4  # retrieve/decide/expand/followup(不重复扣)


def test_s3b01_resume_changed_plan_rejected(tmp_path) -> None:
    """B1 崩溃后 resume 传入变更 plan(B→X)⇒ 结构化拒
    frozen_plan_mismatch(差异须显式新 revision/新任务);零新写入。
    父基线:接受并提交 donor-X(行为红)。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "fpx", crash_after="after_claim")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    changed = {"pools": {"CCO": [spec("X", "CC=O", "donor-X")]}}
    with pytest.raises(PPV1RunError) as ei:
        resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                        run_id="fpx", plan=changed)
    assert ei.value.detail["kind"] == "frozen_plan_mismatch"
    conn = db(runs_root, "fpx")
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_s3b01_frozen_plan_tamper_integrity_failure(tmp_path) -> None:
    """冻结计划 artifact 被篡改(载荷改字节)⇒ H07 完整性失败,结构化
    拒(保全原文件;不猜)。父基线:无冻结计划绑定,篡改不被发现
    (行为红)。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "fpt", crash_after="after_claim")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    plan_file = runs_root / "fpt" / "results" / "run-plan" / \
        "frozen_plan.json"
    assert plan_file.is_file()
    envelope = json.loads(plan_file.read_text(encoding="utf-8"))
    envelope["payload"]["plan"]["pools"]["CCO"] = []
    plan_file.write_text(json.dumps(envelope, ensure_ascii=False),
                         encoding="utf-8")
    with pytest.raises(PPV1RunError) as ei:
        resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                        run_id="fpt", plan=None)
    assert ei.value.detail["kind"] == "frozen_plan_integrity_failure"


def test_s3b01_same_plan_resume_positive_control(tmp_path) -> None:
    """同计划正控(合法恢复保持):B3 同 output 恢复事件仅一次。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "fps", crash_after="after_bundle_written")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    same = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    out = resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                          run_id="fps", plan=same)
    assert out["counts"]["events"] == 1
    conn = db(runs_root, "fps")
    assert conn.execute(
        "SELECT COUNT(*) FROM search_commit_records").fetchone()[0] == 4
    # 再次 resume:幂等复用(不重数)
    out2 = resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                           run_id="fps", plan=same)
    assert out2["counts"]["events"] == 1
    assert db(runs_root, "fps").execute(
        "SELECT COUNT(*) FROM search_commit_records").fetchone()[0] == 4


# ---------------------------------------------------------------- S3B-02


def _bundle_file(runs_root: Path, run_id: str) -> Path:
    files = artifact_files(runs_root, run_id, "search_commit_bundle")
    assert len(files) == 1
    return files[0]


def test_s3b02_bad_bundle_hash_isolated_not_reexecuted(tmp_path) -> None:
    """B3 bundle 载荷被改(hash 不符)⇒ recover 认坏,resume 隔离该
    action(claimed→blocked):零重执行/零坏任务 event/commit;原坏
    文件逐字保全;合法已完成任务不受影响。父基线:重跑真工具并写
    1 event(行为红)。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "h07a", crash_after="after_bundle_written")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    bundle = _bundle_file(runs_root, "h07a")
    envelope = json.loads(bundle.read_text(encoding="utf-8"))
    bad_bytes = bundle.read_bytes()
    envelope["payload"]["event"]["event_id"] = "ppev_tampered"
    bundle.write_text(json.dumps(envelope, ensure_ascii=False),
                      encoding="utf-8")
    conn = db(runs_root, "h07a")
    events_before = conn.execute(
        "SELECT COUNT(*) FROM events").fetchone()[0]
    commits_before = conn.execute(
        "SELECT COUNT(*) FROM search_commit_records").fetchone()[0]
    assert events_before == 0 and commits_before == 2
    out = resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                          run_id="h07a", plan=None)
    assert out["counts"]["events"] == 0  # 不重执行、零坏任务事件
    conn = db(runs_root, "h07a")
    assert conn.execute(
        "SELECT COUNT(*) FROM search_commit_records").fetchone()[0] == 2
    # 隔离:expand action blocked + 原因;恢复裁定披露
    rows = conn.execute(
        "SELECT * FROM search_actions WHERE status = 'blocked'").fetchall()
    assert len(rows) == 1
    assert rows[0]["defer_reason"] == \
        "recovery_failure:artifact_hash_mismatch"
    assert rows[0]["action_kind"] == "expand_hypothesis"
    isolated = out["recovery"]["isolated_actions"]
    assert len(isolated) == 1
    assert isolated[0]["failure"]["kind"] == "artifact_hash_mismatch"
    # 坏原文件保全(不被恢复覆盖)
    assert bundle.read_bytes() != bad_bytes  # 本测试主动篡改后的字节
    assert "ppev_tampered" in bundle.read_text(encoding="utf-8")


def test_s3b02_bad_bundle_json_isolated_independent_tasks_continue(
        tmp_path) -> None:
    """B3 bundle 不可反序列化 + 池内独立备选:坏任务隔离,合法独立
    任务(B/C 中的 C)继续执行。父基线:坏任务也被重执行(2 events,
    行为红)。"""
    runs_root = tmp_path / "runs"
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B"),
                              spec("C", "CC=O", "donor-C")]}}
    with pytest.raises(Exception):  # SearchCrashInjection:B 的 bundle 已写
        start_ppv1_run(config=resolve_config(), runs_root=runs_root,
                       run_id="h07b", smiles="CCO", plan=plan,
                       scripted=True, crash_after="after_bundle_written")
    bundle = _bundle_file(runs_root, "h07b")
    bundle.write_text("{not-json", encoding="utf-8")
    out = resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                          run_id="h07b", plan=None)
    assert out["counts"]["events"] == 1  # 仅 C(合法独立任务)
    conn = db(runs_root, "h07b")
    blocked = conn.execute(
        "SELECT * FROM search_actions WHERE status = 'blocked'").fetchall()
    assert len(blocked) == 1
    assert blocked[0]["defer_reason"] == \
        "recovery_failure:artifact_unparseable"
    isolated = out["recovery"]["isolated_actions"]
    assert isolated and isolated[0]["failure"]["kind"] == \
        "artifact_unparseable"
    # C 的提交完整(commit 记录闭合;followup 如常)
    events = conn.execute("SELECT hypothesis_id FROM events").fetchall()
    assert len(events) == 1
    assert events[0]["hypothesis_id"] != blocked[0]["subject_ref"]


# ---------------------------------------------------------------- S3B-03


def _followup_retrieves(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return [r for r in conn.execute(
        "SELECT * FROM search_actions WHERE action_kind = 'retrieve'"
        " ORDER BY created_at, action_id").fetchall()
        if json.loads(r["payload"]).get("source_event_id")]


def _event_products(conn: sqlite3.Connection) -> list[str]:
    return [p["state_ref"] for e in conn.execute(
        "SELECT payload FROM events").fetchall()
        for p in json.loads(e["payload"])["participants"]
        if p["side"] == "product"]


def test_s3b03_partial_followup_hard_kill_completed(tmp_path) -> None:
    """注入:第二条 followup retrieve 入队后硬杀(真实进程崩溃)⇒
    新进程 resume 从权威事件/计划逐对象补齐 3/3(不以已有引用计数当
    完整性证书;事件/预算不重复)。父基线:仅 2/3(行为红)。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "t3k", crash_after="none",
                       coproducts=["[H][H]", "O"],
                       injection="after_two_followups")
    assert proc.returncode == 77  # 队列级注入硬杀(os._exit(77))
    out = resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                          run_id="t3k", plan=None)
    assert out["counts"]["events"] == 1  # 事件不重放
    conn = db(runs_root, "t3k")
    products = _event_products(conn)
    assert len(products) == 3
    followups = _followup_retrieves(conn)
    assert len(followups) == 3  # 2/3 → 恢复后 3/3 逐对象闭合
    assert {r["subject_ref"] for r in followups} == set(products)


def test_s3b03_b4_event_submitted_no_followup_completed(tmp_path) -> None:
    """B4(0 followup,正控分层):事件已提交、任何 followup 未入队 ⇒
    恢复补齐全部产物 followup(该 0/全部窗口旧 LIKE 计数恰好不误跳;
    r2 与父均应闭合 —— 幂等双保险)。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "t3b", crash_after="after_event_submitted",
                       coproducts=["[H][H]", "O"])
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    out = resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                          run_id="t3b", plan=None)
    assert out["counts"]["events"] == 1
    conn = db(runs_root, "t3b")
    products = _event_products(conn)
    assert len(products) == 3
    assert len(_followup_retrieves(conn)) == 3


def test_s3b03_transition_after_event_submitted_new_context(
        tmp_path) -> None:
    """B4:事件已提交、转换未入队 ⇒ 恢复补齐显式转换并按新上下文
    调度 followup(旧边冻结)。父基线:转换意图丢失、followup 用旧
    上下文(行为红)。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "trb4", crash_after="after_event_submitted",
                       transitions=True)
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    out = resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                          run_id="trb4", plan=None)
    assert out["counts"]["events"] == 1
    conn = db(runs_root, "trb4")
    transitions = conn.execute(
        "SELECT * FROM search_actions WHERE action_kind ="
        " 'scenario_transition'").fetchall()
    assert len(transitions) == 1
    assert transitions[0]["status"] == "done"
    # 转换载荷携带冻结 pending_followup(创建时一次写入)
    tpayload = json.loads(transitions[0]["payload"])
    assert tpayload.get("pending_followup", {}).get(
        "event_id", "").startswith("ppev_")
    # followup retrieve 用转换后的新上下文(phase-1)
    followups = _followup_retrieves(conn)
    assert followups
    ctx_ids = {r["context_ref"] for r in followups}
    contexts = [json.loads(p.read_text(encoding="utf-8"))["payload"]
                for p in artifact_files(runs_root, "trb4", "path_context")]
    new_ctx = [c for c in contexts if c["phase_id"] == "phase-1"]
    assert new_ctx
    assert new_ctx[0]["context_id"] in ctx_ids  # 实际下一边新 context


def test_s3b03_transition_enqueued_crash_window_closed(tmp_path) -> None:
    """转换 action 入队后立刻硬杀(入队与附随之间)⇒ 恢复后转换执行
    且 followup 用新上下文(pending_followup 创建时一次冻结,无两写
    窗口)。父基线:转换载荷无附随,恢复丢后效(行为红)。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "trw",
                       crash_after="none",
                       transitions=True,
                       injection="after_transition_enqueued")
    assert proc.returncode == 77
    out = resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                          run_id="trw", plan=None)
    assert out["counts"]["events"] == 1
    conn = db(runs_root, "trw")
    transitions = conn.execute(
        "SELECT * FROM search_actions WHERE action_kind ="
        " 'scenario_transition'").fetchall()
    assert len(transitions) == 1
    assert transitions[0]["status"] == "done"
    assert json.loads(transitions[0]["payload"]).get("pending_followup")
    followups = _followup_retrieves(conn)
    assert followups
    contexts = [json.loads(p.read_text(encoding="utf-8"))["payload"]
                for p in artifact_files(runs_root, "trw", "path_context")]
    new_ctx = [c for c in contexts if c["phase_id"] == "phase-1"]
    assert new_ctx
    assert {r["context_ref"] for r in followups} == \
        {new_ctx[0]["context_id"]}


def test_s3b03_three_products_normal_positive_control(tmp_path) -> None:
    """合法正控(父亦绿):三产物正常完成,3 条 followup、事件不截断。"""
    runs_root = tmp_path / "runs"
    out = start_run(
        config=resolve_config(), runs_root=runs_root, run_id="t3n",
        smiles="CCO", max_depth=3, max_expansions=20,
        max_frontier_width=3, finder=object(), scripted=True,
        profile=PROFILE_POLLUTANT_PATHWAY_V1,
        profile_policy={"search_limits": {
            "max_product_expansion_width": 3,
            "max_total_search_actions": 20}},
        ppv1_plan={"pools": {"CCO": [
            spec("B", "CC=O", "donor-B", coproducts=["[H][H]", "O"])]}})
    assert out["counts"]["events"] == 1
    conn = db(runs_root, "t3n")
    assert len(_followup_retrieves(conn)) == 3
    assert len(_event_products(conn)) == 3


# ---------------------------------------------------------------- S3B-04


def test_s3b04_concurrent_public_resume_single_executor(tmp_path) -> None:
    """两个真实公开 resume 进程(工具入口计数 + barrier):只一方进入
    真实工具;竞争方在任何执行前结构化拒(driver_session_active);
    最终幂等(事件 1/commit 4);胜者完成后再次 resume 幂等复用。
    父基线:两方都实际执行(行为红)。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "conc", crash_after="after_claim")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    barrier = tmp_path / "barrier"
    receipts = tmp_path / "tool_receipts"
    first = subprocess.Popen(
        [PY, "-B", WORKER, "concurrent-resume",
         "--runs-root", str(runs_root), "--run-id", "conc",
         "--barrier-dir", str(barrier), "--worker", "first",
         "--tool-receipt-dir", str(receipts)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=ENV)
    # 等 first 就绪(它等 GO),再放行
    deadline = time.monotonic() + 30
    barrier.mkdir(parents=True, exist_ok=True)
    while time.monotonic() < deadline and not \
            (receipts / "first.tool_entered.json").exists() and \
            first.poll() is None:
        if not (barrier / "GO").exists():
            (barrier / "GO").write_text("go\n", encoding="utf-8")
        time.sleep(0.05)
    (barrier / "GO").write_text("go\n", encoding="utf-8")
    second = subprocess.Popen(
        [PY, "-B", WORKER, "concurrent-resume",
         "--runs-root", str(runs_root), "--run-id", "conc",
         "--barrier-dir", str(barrier), "--worker", "second",
         "--tool-receipt-dir", str(receipts)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=ENV)
    out_first, _ = first.communicate(timeout=180)
    out_second, _ = second.communicate(timeout=180)
    result_first = json.loads(out_first.strip().splitlines()[-1])
    result_second = json.loads(out_second.strip().splitlines()[-1])
    # 只一方取得执行权:second 在任何执行前被拒
    assert result_first["resumed"] is True
    assert result_second["resumed"] is False
    assert result_second["error"] == "PPV1RunError"
    assert result_second["kind"] == "driver_session_active"
    assert result_second["tool_entries"] == 0
    # 真实工具入口恰一次(执行权互斥的执行证据,不止最终 event 幂等)
    assert (receipts / "first.tool_entered.json").is_file()
    assert not (receipts / "second.tool_entered.json").exists()
    assert result_first["tool_entries"] == 1
    # 最终账目幂等
    conn = db(runs_root, "conc")
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM search_commit_records").fetchone()[0] == 4
    # 胜者退出后:竞争方复用(幂等 resume,不新建事件/attempt)
    out_again = resume_ppv1_run(config=resolve_config(),
                                runs_root=runs_root, run_id="conc",
                                plan=None)
    assert out_again["counts"]["events"] == 1
    assert db(runs_root, "conc").execute(
        "SELECT COUNT(*) FROM search_commit_records").fetchone()[0] == 4


# ---------------------------------------------------------------- S3B-05


def test_s3b05_novel_nonempty_independent_hypothesis_chain(tmp_path) -> None:
    """池内 B + novel 池外提案(内容+来源)⇒ novel 成为独立假设走固定
    工具→audit→admission→submit(2 events/2 hypotheses/真实生产链);
    网络恒 0。父基线:novel 只计数不消费(1 event,行为红)。"""
    runs_root = tmp_path / "runs"
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
            "model": {"provider_kind": "scripted",
                      "responses": [novel_response()]}}
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="nv1", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    assert out["counts"]["events"] == 2  # B + novel 各自事件
    assert out["counts"]["hypotheses"] == 2
    conn = db(runs_root, "nv1")
    hyp_ids = {r["hypothesis_id"] for r in conn.execute(
        "SELECT hypothesis_id FROM hypotheses").fetchall()}
    event_hyps = {r["hypothesis_id"] for r in conn.execute(
        "SELECT hypothesis_id FROM events").fetchall()}
    assert event_hyps == hyp_ids  # novel 假设与事件一一对应
    # novel 独立假设:不同于池内 B(来源组键不同 ⇒ 身份不同)
    assert len(hyp_ids) == 2
    # 真实生产链:novel 的 expand 也落 production_report(经真工具/
    # audit/admission;scripted 网络恒 0)
    reports = artifact_files(runs_root, "nv1", "production_report")
    assert len(reports) == 2
    network = conn.execute(
        "SELECT SUM(network_request_count) FROM model_requests"
    ).fetchone()[0] or 0
    assert network == 0
    # novel 提案的冻结任务输入披露来源(proposal_context)
    expands = [r for r in conn.execute(
        "SELECT * FROM search_actions WHERE action_kind ="
        " 'expand_hypothesis'").fetchall()]
    novel_payloads = [json.loads(r["payload"]) for r in expands
                      if json.loads(r["payload"]).get("proposal_context")]
    assert novel_payloads
    assert novel_payloads[0]["proposal_context"]["output_origin"] == \
        "novel_outside_pool"


def test_s3b05_novel_empty_pool_profile_and_consumption(tmp_path) -> None:
    """空池 + 模型 novel 响应:仍组装底物档案并消费(独立假设/事件/
    模型请求;网络 0)。父基线:retrieve 直接 no_local_candidate、
    模型请求 0(行为红)。"""
    runs_root = tmp_path / "runs"
    plan = {"pools": {},
            "model": {"provider_kind": "scripted",
                      "responses": [novel_response()]}}
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="nv2", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    assert out["counts"]["events"] == 1  # novel 独立假设的事件
    assert out["counts"]["hypotheses"] == 1
    conn = db(runs_root, "nv2")
    requests = conn.execute(
        "SELECT COUNT(*), SUM(network_request_count) FROM model_requests"
    ).fetchone()
    assert requests[0] >= 1  # 模型响应被消费(登记)
    assert (requests[1] or 0) == 0
    # 底物档案独立于候选(空池仍组装;持久 artifact;根底物 CCO 在档)
    profiles = artifact_files(runs_root, "nv2", "substrate_profile")
    assert profiles
    smiles_in_profiles = {
        json.loads(p.read_text(encoding="utf-8"))["payload"]
        ["structure_smiles"] for p in profiles}
    assert "CCO" in smiles_in_profiles


def test_s3b05_model_abstain_empty_pool_legal(tmp_path) -> None:
    """空池 + 合法弃权(proposals=[]):模型被消费(1 请求),有效
    候选集为空 ⇒ no_local_candidate 如实停止(不强制停止规则池)。
    父基线:模型不被咨询(0 请求;行为红)。"""
    runs_root = tmp_path / "runs"
    plan = {"pools": {},
            "model": {"provider_kind": "scripted",
                      "responses": ['{"proposals": []}']}}
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="nv3", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan,
                    profile_policy={"search_limits": {
                        "max_retrievals_per_parent": 2}})
    assert out["counts"]["events"] == 0
    assert out["stop"]["primary"] == "no_local_candidate"
    conn = db(runs_root, "nv3")
    assert conn.execute(
        "SELECT COUNT(*) FROM model_requests").fetchone()[0] == 1


def test_s3b05_novel_insufficient_content_structured_reject(
        tmp_path) -> None:
    """novel reaction_spec 无反应内容(缺 product_smiles)⇒ 构造侧
    结构化拒(run_error 如实停止;不伪造内容、不进格式反馈)。
    父基线:提案被忽略、池内 B 照常完成(无 run_error,行为红)。"""
    runs_root = tmp_path / "runs"
    bad_spec = {"key": "Novel", "coefficient": 1}
    response = json.dumps({"proposals": [{
        "hypothesis_id": "novel:bad",
        "proposal_context": {"reference_hypothesis_ids": [],
                              "output_origin": "novel_outside_pool"},
        "reaction_spec": bad_spec}]})
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
            "model": {"provider_kind": "scripted",
                      "responses": [response]}}
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="nv4", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    assert out["stop"].get("run_error", {}).get("kind") == \
        "spec_missing_product"
    assert out["counts"]["events"] == 0


# ---------------------------------------------------------------- S3B-06


def test_s3b06_zero_depth_budget_composite_stop_disclosure(
        tmp_path) -> None:
    """零深度+预算复合:主因 budget_limit(既定优先级不动);
    depth_limit 入其他原因;blocked 对象(假设/原因)入 unexplored;
    scheduled outcome blocked=1。父基线:other_reasons 空、blocked 0
    (行为红)。"""
    runs_root = tmp_path / "runs"
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="zd", smiles="CCO", max_depth=0,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1,
                    profile_policy={"search_limits": {
                        "max_search_depth": 0}}, ppv1_plan=plan)
    assert out["counts"]["events"] == 0
    stop = out["stop"]
    # 主因按冻结优先级:budget(检索预算耗尽)优先于 depth
    assert stop["primary"] == "budget_limit"
    assert "depth_limit" in stop["other_reasons"]
    unexplored = stop["unexplored"]
    assert unexplored["blocked"] == 1
    objects = unexplored["blocked_objects"]
    assert len(objects) == 1
    assert objects[0]["reason"] == "depth_limit"
    conn = db(runs_root, "zd")
    blocked_row = conn.execute(
        "SELECT * FROM search_actions WHERE status = 'blocked'"
    ).fetchone()
    # 对象身份与持久 blocked 行同源(subject = 冻结假设 id)
    assert blocked_row["subject_ref"] == objects[0]["hypothesis_id"]
    assert blocked_row["action_id"] == objects[0]["action_id"]
    assert blocked_row["defer_reason"] == "depth_limit"
    # 调度 outcome 如实披露 blocked=1
    outcomes = [json.loads(p.read_text(encoding="utf-8"))["payload"]
                ["outcome"] for p in artifact_files(
                    runs_root, "zd", "expansion_outcome")]
    scheduled = [o for o in outcomes if o["kind"] == "scheduled"][0]
    assert scheduled["detail"]["blocked"] == 1
    assert scheduled["detail"]["selected"] == 0


def test_s3b06_zero_depth_repeat_resume_not_recounted(tmp_path) -> None:
    """重复 resume:blocked 对象/原因同源复算,不丢、不重数。"""
    runs_root = tmp_path / "runs"
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    start_run(config=resolve_config(), runs_root=runs_root, run_id="zdr",
              smiles="CCO", max_depth=0, max_expansions=10,
              max_frontier_width=2, finder=object(), scripted=True,
              profile=PROFILE_POLLUTANT_PATHWAY_V1,
              profile_policy={"search_limits": {
                  "max_search_depth": 0}}, ppv1_plan=plan)
    resumed = resume_ppv1_run(config=resolve_config(), runs_root=runs_root,
                              run_id="zdr", plan=None)
    stop = resumed["stop"]
    assert stop["unexplored"]["blocked"] == 1
    assert len(stop["unexplored"]["blocked_objects"]) == 1
    assert "depth_limit" in stop["other_reasons"]
    assert stop["primary"] == "budget_limit"
    conn = db(runs_root, "zdr")
    assert conn.execute(
        "SELECT COUNT(*) FROM search_actions WHERE status = 'blocked'"
    ).fetchone()[0] == 1


def test_s3b06_legal_nonzero_no_blocked_positive_control(tmp_path) -> None:
    """合法非零正控(父亦绿):正常展开运行无 blocked 对象/深度原因。"""
    runs_root = tmp_path / "runs"
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="nz", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    assert out["counts"]["events"] == 1
    stop = out["stop"]
    # .get:父基线无 blocked_objects 字段(键容错)—— 本控是行为正控,
    # 父须保持绿;新增字段缺席不构成行为翻转
    assert stop["unexplored"].get("blocked", 0) == 0
    assert stop["unexplored"].get("blocked_objects", []) == []
    assert "depth_limit" not in stop["other_reasons"]


def test_s3b06_empty_pool_no_local_candidate_positive_control(
        tmp_path) -> None:
    """空池正控(父亦绿):no_local_candidate 主因(独立夹具:检索
    预算不耗尽,主因不是 budget)。"""
    runs_root = tmp_path / "runs"
    out = start_run(config=resolve_config(), runs_root=runs_root,
                    run_id="ep", smiles="CCO", max_depth=3,
                    max_expansions=10, max_frontier_width=2,
                    finder=object(), scripted=True,
                    profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan={},
                    profile_policy={"search_limits": {
                        "max_retrievals_per_parent": 2}})
    assert out["stop"]["primary"] == "no_local_candidate"
    assert out["counts"]["events"] == 0
