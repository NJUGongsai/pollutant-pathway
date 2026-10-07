"""S3a 崩溃恢复回归(四崩溃边界/H07/H08/H06 双进程;ppv1-search-1)。

全部用**独立子进程硬杀**(os._exit,不做连接清理)模拟真实进程崩溃,
父测试随后用全新 store/ledger 连接跑恢复协议 —— 不以“同进程内存异常
后继续”冒充进程崩溃恢复(任务书 §4.4/§11.3)。夹具与 s3a_worker.py
共享(CCO → CC=O 合成;同参数 ⇒ 同 hypothesis/event ID)。

- B1 认领+预约后硬杀:恢复读冻结 action/attempt/预约,同 attempt、
  不重扣、不按当前 revision 重算任务身份;执行方沿原身份续跑完成;
- B2 请求已登记无响应:恢复暴露 pending/unknown,不默发第二请求;
  显式重试 = 新 request_key + 剩余额度;
- B3 artifact 已写、事件未提交:恢复先验版本/hash/身份再消费同一
  output/attempt 完成(事件仅一次、请求不重发);负控:字节损坏/
  hash 不符 ⇒ 完整性错误、原文件保全、不覆盖;
- B4 事件已提交、记账未闭合:合法恢复幂等补账(预算 consume 恰一次、
  事件不重复);负控(H08):提交记录↔事件行不一致 ⇒ 保全失败零写入;
- H06 双进程 barrier 争同一 action:恰一方取得执行权。
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from s3a_worker import make_fixture  # noqa: E402
from pathway_v43.pollutant.profile import (  # noqa: E402
    build_profile_identity_block,
)
from pathway_v43.pollutant.search import (  # noqa: E402
    ACTION_KIND_EXPAND_HYPOTHESIS,
    PROVIDER_KIND_SCRIPTED,
    REQUEST_STATUS_REGISTERED,
    RESERVATION_STATUS_CONSUMED,
    RESERVATION_STATUS_RESERVED,
    SearchArtifactIntegrityError,
    SearchIntegrityError,
    SearchLedger,
    SearchRecoveryError,
    commit_search_event,
    search_policy_version,
)
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "tests" / "s3a_worker.py"
PV = search_policy_version()


def make_run(tmp_path: Path, name: str, limits: dict | None = None):
    runs_root = tmp_path / "runs"
    db = tmp_path / f"{name}.sqlite"
    store = PollutantPathwayStore(db)
    art = ArtifactStore(runs_root, name)
    ledger = SearchLedger(store, art, name)
    policy = build_profile_identity_block(
        search_limits=limits) if limits else build_profile_identity_block()
    ledger.register_search_run(name, policy)
    return store, ledger, art, policy, db, runs_root


def enqueue(ledger, run, subject, *, parent="p1", context="ctx1",
            revision=0, task_key="tk1"):
    return ledger.enqueue_action(
        run_id=run, parent_path_id=parent, context_ref=context,
        subject_ref=subject, action_kind=ACTION_KIND_EXPAND_HYPOTHESIS,
        parent_search_revision=revision, policy_version=PV,
        payload={"task_key": task_key, "frozen_pool_digest": "pool-A"},
        depth=1)


def spawn(mode: str, db: Path, runs_root: Path, run: str, action_id: str,
          worker: str, *, parent="p1", origin="k1", context="ctx1",
          task_key="tk1", request_key="req-1", provider="scripted",
          barrier_dir=None, n_workers=2, out_json=None) -> dict:
    """跑 worker 子进程(硬杀模式退出码 1;结果从 stdout 解析)。"""
    cmd = [sys.executable, "-B", str(WORKER), mode,
           "--db", str(db), "--runs-root", str(runs_root), "--run-id", run,
           "--action-id", action_id, "--worker", worker,
           "--parent", parent, "--origin-key", origin, "--context", context,
           "--task-key", task_key, "--request-key", request_key,
           "--provider-kind", provider]
    if barrier_dir is not None:
        cmd += ["--barrier-dir", str(barrier_dir),
                "--n-workers", str(n_workers)]
    if out_json is not None:
        cmd += ["--out-json", str(out_json)]
    proc = subprocess.run(
        cmd, cwd=str(REPO), capture_output=True, text=True, timeout=120,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
    out = {}
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                out = json.loads(line)
            except json.JSONDecodeError:
                pass
    return {"returncode": proc.returncode, "stdout": out,
            "stderr": proc.stderr}


def fresh_ledger(db: Path, runs_root: Path, run: str) -> SearchLedger:
    """新进程视角:全新 store/ledger 连接(内存重置)。"""
    store = PollutantPathwayStore(db)
    return SearchLedger(store, ArtifactStore(runs_root, run), run)


def search_counts(ledger: SearchLedger, run: str) -> dict:
    one = lambda sql: ledger.conn.execute(  # noqa: E731
        sql, (run,)).fetchone()[0]
    return {
        "actions": one("SELECT COUNT(*) FROM search_actions WHERE run_id=?"),
        "attempts": one(
            "SELECT COUNT(*) FROM search_attempts WHERE run_id=?"),
        "reservations": one(
            "SELECT COUNT(*) FROM budget_reservations WHERE run_id=?"),
        "requests": one(
            "SELECT COUNT(*) FROM model_requests WHERE run_id=?"),
        "commits": one(
            "SELECT COUNT(*) FROM search_commit_records WHERE run_id=?"),
    }


# ------------------------------------------------------------ B1


def test_b1_claimed_reservation_frozen_then_resume(tmp_path: Path) -> None:
    """B1:认领+预约已落账后进程硬杀 —— 新进程恢复读冻结 action/
    attempt/预约继续(同 attempt、不重扣、不按当前 revision 重算),
    执行方沿原身份续跑完成,预算复算相同。"""
    store, ledger, art, policy, db, runs_root = make_run(
        tmp_path, "b1")
    _, _, hyp, _, _ = make_fixture("b1", "p1", "k1", "ctx1")
    out = enqueue(ledger, "b1", hyp.hypothesis_id)
    store.close()
    crash = spawn("claim-exit", db, runs_root, "b1", out["action_id"], "wX")
    assert crash["returncode"] == 1  # 硬杀(非零退出)
    assert crash["stdout"].get("claimed") is True

    ledger2 = fresh_ledger(db, runs_root, "b1")
    report = ledger2.recover_run("b1", policy_block=policy)
    entry = [a for a in report["actions"]
             if a["action_id"] == out["action_id"]][0]
    assert entry["boundary"] == "B1_claimed_pending_completion"
    assert "frozen_attempt_reservation_intact" in entry["disposition"]
    counts = search_counts(ledger2, "b1")
    assert counts["attempts"] == 1
    assert counts["reservations"] == 3  # total+alternatives+attempts,无重复
    assert counts["requests"] == 0 and counts["commits"] == 0
    snapshot_after_crash = ledger2.budget_snapshot("b1")

    # 执行方(可与崩溃 worker 同名续跑或恢复者)沿原身份再认领+完成
    receipt = ledger2.claim_action(out["action_id"], worker_id="wX")
    assert receipt["reason"] == "reclaimed_by_owner"
    assert receipt["attempt_refs"] == [crash["stdout"]["attempt_id"]]
    assert receipt["payload"]["task_key"] == crash["stdout"]["task_key"]
    _, _, _, event, ev_args = make_fixture("b1", "p1", "k1", "ctx1")
    commit_search_event(
        ledger2, out["action_id"], event, worker_id="wX",
        attempt_id=receipt["attempt_refs"][0],
        task_key=receipt["payload"]["task_key"], **ev_args)
    snapshot_final = ledger2.budget_snapshot("b1")
    # 预算复算相同:崩溃前后/完成后的 used 一致推进,无重复扣
    assert snapshot_final["run_level"]["max_total_search_actions"]["used"] \
        == snapshot_after_crash["run_level"][
            "max_total_search_actions"]["used"] == 1
    assert ledger2.store.counts()["events"] == 1
    ledger2.store.close()


# ------------------------------------------------------------ B2


def test_b2_registered_request_pending_unknown_no_resend(tmp_path) -> None:
    """B2:请求已登记、无响应,进程硬杀 —— 恢复暴露 pending/unknown,
    不默发第二请求(scripted network 恒 0);显式重试=新 request_key。"""
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, "b2")
    _, _, hyp, _, _ = make_fixture("b2", "p1", "k1", "ctx1")
    out = enqueue(ledger, "b2", hyp.hypothesis_id)
    store.close()
    crash = spawn("request-exit", db, runs_root, "b2", out["action_id"],
                  "wX", request_key="rk-1")
    assert crash["returncode"] == 1
    request_id = crash["stdout"]["request"]["request_id"]

    ledger2 = fresh_ledger(db, runs_root, "b2")
    report = ledger2.recover_run("b2")
    pending = report["pending_requests"]
    assert len(pending) == 1
    assert pending[0]["request_id"] == request_id
    assert pending[0]["status"] == REQUEST_STATUS_REGISTERED
    assert pending[0]["network_request_count"] == 0  # scripted 恒 0
    assert "不默发第二请求" in pending[0]["note"]
    # 恢复不自动发送:状态保持 registered
    assert ledger2.request(request_id)["status"] == REQUEST_STATUS_REGISTERED
    counts = search_counts(ledger2, "b2")
    assert counts["requests"] == 1  # 未新建请求
    # 显式重试:新 request_key ⇒ 新 request_id(不重发旧请求)
    retry = ledger2.register_model_request(
        run_id="b2", action_id=out["action_id"],
        attempt_id=crash["stdout"]["attempt_id"],
        provider_kind=PROVIDER_KIND_SCRIPTED, request_key="rk-2",
        retry_of=request_id)
    assert retry["registered"] and retry["request_id"] != request_id
    ledger2.store.close()


# ------------------------------------------------------------ B3


def test_b3_artifact_written_consumed_same_output_after_crash(
        tmp_path: Path) -> None:
    """B3:artifact 已写、事件未提交,进程硬杀 —— 恢复先验版本/hash/
    身份,消费同一 output/attempt 完成:事件仅一次、请求 0(不重发)、
    预算 consume 恰一次;二次恢复幂等。"""
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, "b3")
    _, _, hyp, _, _ = make_fixture("b3", "p1", "k1", "ctx1")
    out = enqueue(ledger, "b3", hyp.hypothesis_id)
    store.close()
    crash = spawn("bundle-exit", db, runs_root, "b3", out["action_id"], "wX",
                  task_key="tk1")
    assert crash["returncode"] == 1
    assert crash["stdout"].get("receipt_claimed") is True
    assert ledger is not None

    ledger2 = fresh_ledger(db, runs_root, "b3")
    report = ledger2.recover_run("b3")
    entry = [a for a in report["actions"]
             if a["action_id"] == out["action_id"]][0]
    assert entry["boundary"] == "B3_artifact_written_event_uncommitted"
    assert "consumed_same_output_attempt" in entry["disposition"]
    assert ledger2.store.counts()["events"] == 1  # 事件仅一次
    assert search_counts(ledger2, "b3")["requests"] == 0  # 请求不重发
    snap = ledger2.budget_snapshot("b3")
    assert snap["run_level"]["max_total_search_actions"]["used"] == 1
    rows = ledger2.conn.execute(
        "SELECT status FROM budget_reservations WHERE run_id='b3' AND"
        " limit_key='max_total_search_actions'").fetchall()
    assert [r["status"] for r in rows] == [RESERVATION_STATUS_CONSUMED]
    # 二次恢复:幂等(done 状态的提交记录↔事件核验通过,零新增)
    before = search_counts(ledger2, "b3")
    report2 = ledger2.recover_run("b3")
    entry2 = [a for a in report2["actions"]
              if a["action_id"] == out["action_id"]][0]
    assert entry2["boundary"] == "B4_verified"
    assert entry2["disposition"] == "done_commit_verified"
    assert search_counts(ledger2, "b3") == before
    assert ledger2.store.counts()["events"] == 1
    ledger2.store.close()


@pytest.mark.parametrize("mode", ["garbage", "hash_mismatch"])
def test_b3_corrupt_artifact_preserved_fail_closed(tmp_path: Path,
                                                   mode: str) -> None:
    """B3 负控(H07):artifact 字节损坏/信封 hash 不符 ⇒ 明确完整性
    错误、保全原文件、不静默跳过、不覆盖重跑;事件零提交。"""
    store, ledger, art, policy, db, runs_root = make_run(tmp_path,
                                                          f"b3{mode}")
    _, _, hyp, _, _ = make_fixture(f"b3{mode}", "p1", "k1", "ctx1")
    out = enqueue(ledger, f"b3{mode}", hyp.hypothesis_id)
    store.close()
    spawn("bundle-exit", db, runs_root, f"b3{mode}", out["action_id"], "wX",
          task_key="tk1")
    path = runs_root / f"b3{mode}" / "results" / "tk1" / \
        "search_commit_bundle.json"
    assert path.is_file()
    if mode == "garbage":
        path.write_bytes(b"\x00\x01 not json at all")
    else:
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["payload"]["event"]["participants"] = []
        path.write_text(json.dumps(doc), encoding="utf-8")
    before_bytes = path.read_bytes()

    ledger2 = fresh_ledger(db, runs_root, f"b3{mode}")
    report = ledger2.recover_run(f"b3{mode}")
    entry = [a for a in report["actions"]
             if a["action_id"] == out["action_id"]][0]
    assert entry["disposition"]["error"] == "SearchArtifactIntegrityError"
    assert entry["disposition"]["kind"] == (
        "artifact_unparseable" if mode == "garbage"
        else "artifact_hash_mismatch")
    assert "原文件保全" in entry["disposition"]["note"]
    assert path.read_bytes() == before_bytes  # 保全(不删不改不覆盖)
    assert ledger2.store.counts()["events"] == 0  # 草稿不当事件
    assert search_counts(ledger2, f"b3{mode}")["commits"] == 0
    # action 仍 claimed(未完成、未静默跳过)
    assert ledger2.action(out["action_id"])["status"] == "claimed"
    ledger2.store.close()


def test_b3_bundle_identity_verification(tmp_path: Path) -> None:
    """B3 先验身份:bundle 版本未知/action 绑定不符/attempt 绑定不符
    ⇒ 拒绝消费(不消费他人 attempt 的 output)。"""
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, "b3id")
    _, _, hyp, _, _ = make_fixture("b3id", "p1", "k1", "ctx1")
    out = enqueue(ledger, "b3id", hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    attempt = receipt["attempt_refs"][0]
    _, _, _, event, ev_args = make_fixture("b3id", "p1", "k1", "ctx1")
    for mutate in ("version", "action", "attempt"):
        payload = {
            "bundle_version": (
                "ppv1-search-commit-bundle-X" if mutate == "version"
                else "ppv1-search-commit-bundle-1"),
            "action_id": "other" if mutate == "action"
            else out["action_id"],
            "attempt_id": "att-other" if mutate == "attempt" else attempt,
            "event": {
                "schema_version": event.schema_version,
                "event_id": event.event_id, "run_id": event.run_id,
                "parent_path_id": event.parent_path_id,
                "hypothesis_id": event.hypothesis_id,
                "context_hash": event.context_hash,
                "participants": list(event.participants),
                "participant_state_refs": list(
                    event.participant_state_refs),
                "catalytic_support": list(event.catalytic_support),
            },
            "report_projection": ev_args["report_projection"],
            "expansion_plan": ev_args["expansion_plan"],
            "states": ev_args["states"],
            "hypothesis_dict": ev_args["hypothesis_dict"],
            "task_key": "tkX",
        }
        art.write(f"tk-{mutate}", "search_commit_bundle", payload)
        # 手工把伪造 bundle 挂到该 action 的 task_key 路径
        ledger.action(out["action_id"])
        real = art._path(f"tk-{mutate}", "search_commit_bundle")
        target = art._path("tkX", "search_commit_bundle")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(real.read_bytes())
        entry_kind = None
        report = None
        # 恢复会尝试消费 tkX;身份先验失败 ⇒ 完整性错误(不消费)
        try:
            ledger2 = SearchLedger(store, art, "b3id")
            # 伪造 action 行指向 tkX 的 task_key 不可行(payload 冻结);
            # 直接以恢复的私有验证入口单测先验逻辑:
            action_row = {
                "action_id": out["action_id"],
                "attempt_refs": json.dumps([attempt]),
            }
            envelope = art.read(f"tk-{mutate}", "search_commit_bundle")
            try:
                ledger2._verify_bundle_identity(action_row, envelope)
                entry_kind = "accepted"
            except SearchArtifactIntegrityError as exc:
                entry_kind = exc.detail["kind"]
        finally:
            target.unlink(missing_ok=True)
        assert entry_kind in (
            "bundle_version_unknown", "bundle_action_binding_mismatch",
            "bundle_attempt_binding_mismatch")
    store.close()


# ------------------------------------------------------------ B4


def test_b4_event_committed_bookkeeping_completed_idempotently(
        tmp_path: Path) -> None:
    """B4 合法恢复:事件已提交(提交后进程硬杀/注入点)、记账未闭合
    ⇒ 恢复幂等补账:事件不重复(仅 1)、预算 consume 恰一次、attempt
    recorded、action done;二次恢复零新增。"""
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, "b4")
    _, _, hyp, _, _ = make_fixture("b4", "p1", "k1", "ctx1")
    out = enqueue(ledger, "b4", hyp.hypothesis_id)
    store.close()
    crash = spawn("submit-exit", db, runs_root, "b4", out["action_id"], "wX")
    assert crash["returncode"] == 1
    assert crash["stdout"]["submitted"]["created"] is True

    ledger2 = fresh_ledger(db, runs_root, "b4")
    assert ledger2.store.counts()["events"] == 1  # 事件已落账
    report = ledger2.recover_run("b4")
    entry = [a for a in report["actions"]
             if a["action_id"] == out["action_id"]][0]
    assert entry["boundary"] == "B4_event_committed_bookkeeping_incomplete"
    assert entry["disposition"] == "bookkeeping_completed_idempotent"
    # 事件不重复 / 产品扩展不重复(仍一个事件、一个投影、一个计划)
    assert ledger2.store.counts()["events"] == 1
    assert ledger2.store.counts()["expansion_plans"] == 1
    # 预算恰好 consume 一次(不是两倍)
    snap = ledger2.budget_snapshot("b4")
    assert snap["run_level"]["max_total_search_actions"]["used"] == 1
    rows = ledger2.conn.execute(
        "SELECT status FROM budget_reservations WHERE run_id='b4' AND"
        " limit_key='max_total_search_actions'").fetchall()
    assert [r["status"] for r in rows] == [RESERVATION_STATUS_CONSUMED]
    assert ledger2.action(out["action_id"])["status"] == "done"
    attempt = ledger2.conn.execute(
        "SELECT status FROM search_attempts WHERE run_id='b4'"
    ).fetchone()
    assert attempt["status"] == "recorded"
    # 二次恢复:done 提交记录↔事件核验通过,零新增
    before = search_counts(ledger2, "b4")
    report2 = ledger2.recover_run("b4")
    entry2 = [a for a in report2["actions"]
              if a["action_id"] == out["action_id"]][0]
    assert entry2["boundary"] == "B4_verified"
    assert entry2["disposition"] == "done_commit_verified"
    assert search_counts(ledger2, "b4") == before
    ledger2.store.close()


def test_h08_commit_record_event_missing_preserved(tmp_path: Path) -> None:
    """H08 负控 1:提交记录引用的事件行被删 ⇒ 恢复保全证据、明确
    失败,不默认补事件/修库;搜索表零写入。"""
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, "h8a")
    _, _, hyp, _, _ = make_fixture("h8a", "p1", "k1", "ctx1")
    out = enqueue(ledger, "h8a", hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    _, _, _, event, ev_args = make_fixture("h8a", "p1", "k1", "ctx1")
    commit_search_event(
        ledger, out["action_id"], event, worker_id="w1",
        attempt_id=receipt["attempt_refs"][0], task_key="tk1", **ev_args)
    counts_before = search_counts(ledger, "h8a")
    # 合成损坏:删事件行(提交事实与 ledger 不一致)
    ledger.conn.execute(
        "DELETE FROM events WHERE event_id = ?", (event.event_id,))
    ledger.conn.commit()
    ledger.store.close()

    ledger2 = fresh_ledger(db, runs_root, "h8a")
    with pytest.raises(SearchIntegrityError) as ei:
        ledger2.recover_run("h8a")
    assert ei.value.detail["kind"] == "commit_record_event_missing"
    assert ei.value.detail["action_id"] == out["action_id"]
    # 保全失败:搜索表零写入(commits 行仍在、未被删/改)
    assert search_counts(ledger2, "h8a") == counts_before
    row = ledger2.conn.execute(
        "SELECT event_id FROM search_commit_records WHERE action_id = ?",
        (out["action_id"],)).fetchone()
    assert row["event_id"] == event.event_id  # 记录未被自动“修库”
    ledger2.store.close()


def test_h08_commit_record_tampered_event_id(tmp_path: Path) -> None:
    """H08 负控 2:提交记录的 event_id 被改指向不存在的事件 ⇒ 恢复
    失败保全(引用缺失),不猜数据。"""
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, "h8b")
    _, _, hyp, _, _ = make_fixture("h8b", "p1", "k1", "ctx1")
    out = enqueue(ledger, "h8b", hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    _, _, _, event, ev_args = make_fixture("h8b", "p1", "k1", "ctx1")
    commit_search_event(
        ledger, out["action_id"], event, worker_id="w1",
        attempt_id=receipt["attempt_refs"][0], task_key="tk1", **ev_args)
    ledger.conn.execute(
        "UPDATE search_commit_records SET event_id = 'ev-missing' WHERE"
        " action_id = ?", (out["action_id"],))
    ledger.conn.commit()
    ledger.store.close()

    ledger2 = fresh_ledger(db, runs_root, "h8b")
    with pytest.raises(SearchIntegrityError) as ei:
        ledger2.recover_run("h8b")
    assert ei.value.detail["kind"] == "commit_record_event_missing"
    ledger2.store.close()


def test_h08_event_identity_columns_tampered(tmp_path: Path) -> None:
    """H08 负控 3:事件行身份列被改(parent_path_id)⇒ 提交记录与
    action 冻结身份不一致,恢复保全失败。"""
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, "h8c")
    _, _, hyp, _, _ = make_fixture("h8c", "p1", "k1", "ctx1")
    out = enqueue(ledger, "h8c", hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    _, _, _, event, ev_args = make_fixture("h8c", "p1", "k1", "ctx1")
    commit_search_event(
        ledger, out["action_id"], event, worker_id="w1",
        attempt_id=receipt["attempt_refs"][0], task_key="tk1", **ev_args)
    ledger.conn.execute(
        "UPDATE events SET parent_path_id = 'px' WHERE event_id = ?",
        (event.event_id,))
    ledger.conn.commit()
    ledger.store.close()

    ledger2 = fresh_ledger(db, runs_root, "h8c")
    with pytest.raises(SearchIntegrityError) as ei:
        ledger2.recover_run("h8c")
    assert ei.value.detail[
        "kind"] == "commit_record_event_identity_mismatch"
    ledger2.store.close()


# ------------------------------------------------------------ H06 双进程


def test_h06_two_processes_barrier_single_winner(tmp_path: Path) -> None:
    """H06:两个独立**进程**配文件 barrier 同时争同一 action —— 恰一方
    取得执行权(另一方 already_claimed);attempt/请求/预约无翻倍。"""
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, "h06p")
    _, _, hyp, _, _ = make_fixture("h06p", "p1", "k1", "ctx1")
    out = enqueue(ledger, "h06p", hyp.hypothesis_id)
    store.close()
    barrier = tmp_path / "barrier"
    barrier.mkdir()

    procs = []
    for i, name in enumerate(("wA", "wB")):
        cmd = [sys.executable, "-B", str(WORKER), "barrier-claim",
               "--db", str(db), "--runs-root", str(runs_root),
               "--run-id", "h06p", "--action-id", out["action_id"],
               "--worker", name, "--barrier-dir", str(barrier),
               "--n-workers", "2", "--out-json",
               str(barrier / f"{name}.json")]
        procs.append(subprocess.Popen(
            cmd, cwd=str(REPO), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
            env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"}))
    # 双 ready 后放行(确定性同时,不靠 sleep 概率)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        ready = {p.name for p in barrier.glob("*.ready")}
        if len(ready) == 2:
            break
        time.sleep(0.05)
    assert len({p.name for p in barrier.glob("*.ready")}) == 2
    (barrier / "GO").write_text("go\n", encoding="utf-8")
    for p in procs:
        p.wait(timeout=60)

    results = {}
    for name in ("wA", "wB"):
        results[name] = json.loads(
            (barrier / f"{name}.json").read_text(encoding="utf-8"))
    winners = [n for n, r in results.items() if r.get("claimed")]
    assert len(winners) == 1
    loser = "wB" if winners[0] == "wA" else "wA"
    assert results[loser]["claimed"] is False
    assert results[loser]["error"] == "SearchClaimError"
    assert results[loser]["kind"] == "already_claimed"
    # 无翻倍
    ledger2 = fresh_ledger(db, runs_root, "h06p")
    counts = search_counts(ledger2, "h06p")
    assert counts["attempts"] == 1
    assert counts["requests"] == 0
    snap = ledger2.budget_snapshot("h06p")
    assert snap["run_level"]["max_total_search_actions"]["used"] == 1
    ledger2.store.close()


def test_worker_full_commit_end_to_end(tmp_path: Path) -> None:
    """worker 全链驱动(claim→bundle→submit→complete)冒烟:子进程
    完整提交一次,退出 0。"""
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, "full")
    _, _, hyp, _, _ = make_fixture("full", "p1", "k1", "ctx1")
    out = enqueue(ledger, "full", hyp.hypothesis_id)
    store.close()
    result = spawn("full-commit", db, runs_root, "full",
                   out["action_id"], "w1", task_key="tk1")
    assert result["returncode"] == 0
    assert result["stdout"]["outcome"]["completed"] is True
    ledger2 = fresh_ledger(db, runs_root, "full")
    assert ledger2.store.counts()["events"] == 1
    assert ledger2.action(out["action_id"])["status"] == "done"
    ledger2.store.close()


def test_recover_unregistered_run_fail_closed(tmp_path: Path) -> None:
    store = PollutantPathwayStore(tmp_path / "unreg.sqlite")
    ledger = SearchLedger(store, None, "nobody")
    with pytest.raises(SearchRecoveryError):
        ledger.recover_run("nobody")
    store.close()
