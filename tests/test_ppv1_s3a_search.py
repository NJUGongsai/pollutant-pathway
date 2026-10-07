"""S3a 持久搜索底座回归(身份/E03/E04/H05/H06/请求;ppv1-search-2 r2 回修)。

规则级合成夹具(CCO → CC=O);临时 SQLite/artifact,无金标/封存材料。
覆盖(任务书 §7 矩阵 a 批行):
- 身份/E03:任务/attempt/action 创建、同父换假设、同键异内容拒、
  同事件重放不多事件、恢复沿已冻结键、parent_search_revision 只进
  依赖局部搜索状态的键(不进底物特征缓存);
- P0-3/E04:十上限登记/默认/范围/单位/优先级、配置往返、预算账表
  逐步复算、循环稳定停、内存重置复算、缓存检索不重复计数;
- H05:零 action 预算/零深度/空池三独立夹具、复合主因优先级、
  user_stop 支配、deferred 不称探索完、正控;
- H06:双连接 barrier 同争一 action 单赢家、done 复用、陈旧 worker
  不可越权、同 hypothesis 异 context 不互斥、SQLite busy 可见;
- 请求:B2 登记状态机、真实额度 0 阻止登记(网络发送被阻止)、
  scripted 网络 0;
- 继承:搜索层不绕过公共 writer 首消费验证;runner 对 PPV1 仍拒。
基线 00e509a 上本文件为 collection 红(新模块 pollutant.search 缺失),
test_ppv1_profile.py 的版本断言为行为红 —— 分类登记见交付书。
"""

from __future__ import annotations

import inspect
import sqlite3
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from s3a_worker import make_fixture  # noqa: E402
from pathway_v43.pollutant.events import PathwayEvent  # noqa: E402
from pathway_v43.pollutant.profile import (  # noqa: E402
    SEARCH_LIMITS_DEFAULTS,
    SEARCH_LIMITS_RANGES,
    SEARCH_LIMITS_VERSION,
    build_profile_identity_block,
)
from pathway_v43.pollutant.search import (  # noqa: E402
    ACTION_KINDS,
    ACTION_KIND_EXPAND_HYPOTHESIS,
    ACTION_KIND_RETRIEVE,
    ACTION_KIND_SCENARIO_TRANSITION,
    ACTION_STATUSES,
    ATTEMPT_STATUS_OPEN,
    COMMIT_KIND_OUTCOME,
    PROVIDER_KIND_REAL,
    PROVIDER_KIND_SCRIPTED,
    REQUEST_STATUS_REGISTERED,
    REQUEST_STATUS_RESPONDED,
    REQUEST_STATUS_SENT,
    STOP_REASON_PRIORITY,
    SearchBudgetExhausted,
    SearchClaimError,
    SearchConcurrencyError,
    SearchCrashInjection,
    SearchIdentityConflict,
    SearchLedger,
    SearchRecoveryError,
    STOP_REASON_AWAITING_PREDICTION,
    STOP_REASON_BUDGET_LIMIT,
    STOP_REASON_DEPTH_LIMIT,
    STOP_REASON_EXHAUSTED_SEARCH,
    STOP_REASON_NO_LOCAL_CANDIDATE,
    STOP_REASON_USER_STOP,
    commit_search_event,
    decision_task_key,
    expansion_task_key,
    read_search_artifact,
    resolve_search_stop,
    search_policy_version,
    substrate_feature_cache_key,
)
from pathway_v43.pollutant.store import (  # noqa: E402
    PollutantPathwayStore,
)
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402

PV = search_policy_version()


def make_run(tmp_path: Path, name: str, limits: dict | None = None):
    """注册好搜索策略的 run(store+ledger+artifact+policy 块)。"""
    runs_root = tmp_path / "runs"
    store = PollutantPathwayStore(tmp_path / f"{name}.sqlite")
    art = ArtifactStore(runs_root, name)
    ledger = SearchLedger(store, art, name)
    policy = build_profile_identity_block(
        search_limits=limits) if limits else build_profile_identity_block()
    ledger.register_search_run(name, policy)
    return store, ledger, art, policy


def enqueue_expand(ledger, run_id, *, parent, context, subject, revision=0,
                    task_key, depth=1, source_event_id="", pool="pool-A"):
    return ledger.enqueue_action(
        run_id=run_id, parent_path_id=parent, context_ref=context,
        subject_ref=subject, action_kind=ACTION_KIND_EXPAND_HYPOTHESIS,
        parent_search_revision=revision, policy_version=PV,
        payload={"task_key": task_key, "frozen_pool_digest": pool,
                 "strict_state_digest": "sd", "tool_id": "atom-tool",
                 "prompt_version": "p1", "feedback_policy_version": "fb1"},
        depth=depth, source_event_id=source_event_id)


def drive_commit(ledger, run_id, action_id, *, parent="p1", origin="k1",
                 context="ctx1", worker="w1", task_key="",
                 write_bundle=False, attempt_id=""):
    """认领后完整提交(bundle→事件→记账;测试驱动,非生产 runner)。"""
    receipt = ledger.claim_action(action_id, worker_id=worker)
    assert receipt["claimed"]
    attempt = attempt_id or (receipt["attempt_refs"] or [""])[0]
    _, _, _, event, ev_args = make_fixture(run_id, parent, origin, context)
    return commit_search_event(
        ledger, action_id, event, worker_id=worker, attempt_id=attempt,
        task_key=task_key or receipt["task_key"] or "tk",
        write_bundle=write_bundle, **ev_args)


# ------------------------------------------------ 模块契约与 run 注册


def test_s3a_schema_enums_registered() -> None:
    assert ACTION_KINDS == frozenset({
        "retrieve", "decide", "expand_hypothesis", "activate_deferred",
        "scenario_transition"})
    assert ACTION_STATUSES == frozenset({
        "pending", "claimed", "done", "deferred", "blocked"})
    assert STOP_REASON_PRIORITY == (
        "user_stop", "budget_limit", "depth_limit", "no_local_candidate",
        "awaiting_prediction", "exhausted_search")
    assert SEARCH_LIMITS_VERSION == "ppv1-search-limits-3"
    # 十上限默认/范围(P0-3 实际可执行版本;键/默认/范围沿用草案 v2)
    assert set(SEARCH_LIMITS_RANGES) == set(
        k for k in SEARCH_LIMITS_DEFAULTS if k != "version")
    assert len(SEARCH_LIMITS_RANGES) == 10


def test_register_run_idempotent_and_conflict(tmp_path: Path) -> None:
    _, ledger, _, policy = make_run(tmp_path, "r-reg")
    ledger.register_search_run("r-reg", policy)  # 同块幂等
    other = build_profile_identity_block(
        search_limits={"max_total_search_actions": 3})
    with pytest.raises(SearchIdentityConflict) as ei:
        ledger.register_search_run("r-reg", other)
    assert ei.value.detail["kind"] == "search_policy_conflict"


def test_unregistered_run_fail_closed(tmp_path: Path) -> None:
    store = PollutantPathwayStore(tmp_path / "u.sqlite")
    ledger = SearchLedger(store, None, "unregistered")
    with pytest.raises(SearchRecoveryError) as ei:
        ledger.enqueue_action(
            run_id="unregistered", parent_path_id="p", context_ref="c",
            subject_ref="s", action_kind="decide", policy_version=PV,
            payload={})
    assert ei.value.detail["kind"] == "search_run_unregistered"
    with pytest.raises(SearchRecoveryError):
        ledger.recover_run("unregistered")
    store.close()


def test_policy_identity_mismatch_recovery_refused(tmp_path) -> None:
    _, ledger, _, policy = make_run(tmp_path, "r-mismatch")
    other = build_profile_identity_block(
        search_limits={"max_search_depth": 2})
    with pytest.raises(SearchRecoveryError) as ei:
        ledger.recover_run("r-mismatch", policy_block=other)
    assert ei.value.detail["kind"] == "search_policy_identity_mismatch"
    ledger.recover_run("r-mismatch", policy_block=policy)  # 同块通过


def test_config_roundtrip_registered_block(tmp_path: Path) -> None:
    _, ledger, _, policy = make_run(tmp_path, "r-rt")
    stored = ledger.search_policy_block("r-rt")
    assert stored == policy
    # 完整序列化块可原样回灌 profile(往返可重放)
    again = build_profile_identity_block(
        **{k: v for k, v in stored.items()
           if k in ("input_preview_policy", "chemical_reproposal",
                    "search_intent", "search_limits")})
    assert again == stored


# ------------------------------------------------ 入队幂等/结构上限


def test_enqueue_idempotent_and_payload_conflict(tmp_path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "r-enq")
    out1 = enqueue_expand(ledger, "r-enq", parent="p1", context="ctx1",
                          subject="hyp1", task_key="tk1")
    assert out1["created"]
    out2 = enqueue_expand(ledger, "r-enq", parent="p1", context="ctx1",
                          subject="hyp1", task_key="tk1")
    assert out2["unchanged"] and not out2["created"]
    # 同键异内容:池摘要变(身份输入相同、任务输入不同)⇒ 冲突拒
    with pytest.raises(SearchIdentityConflict) as ei:
        enqueue_expand(ledger, "r-enq", parent="p1", context="ctx1",
                       subject="hyp1", task_key="tk1", pool="pool-B")
    assert ei.value.detail["kind"] == "action_payload_conflict"


def test_enqueue_depth_guard(tmp_path: Path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "r-depth")
    out = enqueue_expand(ledger, "r-depth", parent="p", context="c",
                         subject="h", task_key="t", depth=4)
    assert not out["created"] and out["reason"] == "depth_limit"
    assert ledger.action(out["action_id"] or "x") is None  # 零写入
    # 非 expand 类不受深度约束(阶段转换另计)
    ok = ledger.enqueue_action(
        run_id="r-depth", parent_path_id="p", context_ref="c",
        subject_ref="pool", action_kind=ACTION_KIND_SCENARIO_TRANSITION,
        policy_version=PV, payload={})
    assert ok["created"]


def test_enqueue_product_width_guard(tmp_path: Path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "r-width")
    for i in range(2):
        out = enqueue_expand(ledger, "r-width", parent="p", context="c",
                             subject=f"h{i}", task_key=f"t{i}",
                             source_event_id="ev1")
        assert out["created"]
    out3 = enqueue_expand(ledger, "r-width", parent="p", context="c",
                          subject="h2", task_key="t2",
                          source_event_id="ev1")
    assert not out3["created"]
    assert out3["reason"] == "product_width_limit"
    assert out3["detail"]["max_product_expansion_width"] == 2


# ------------------------------------------------ E03:任务键矩阵


def test_decision_task_key_varies_with_all_identity_inputs() -> None:
    base = dict(run_id="r", parent_path_id="p", context_ref="c",
                frozen_pool_digest="poolA", parent_search_revision=0,
                policy_version=PV)
    k0 = decision_task_key(**base)
    assert k0 != decision_task_key(**{**base, "frozen_pool_digest": "poolB"})
    assert k0 != decision_task_key(**{**base, "context_ref": "c2"})
    assert k0 != decision_task_key(**{**base, "parent_search_revision": 1})
    assert k0 != decision_task_key(**{**base, "policy_version": PV + "x"})
    assert k0 != decision_task_key(**{**base, "strict_state_digest": "sd2"})
    assert k0 != decision_task_key(**{**base, "tool_id": "tool2"})
    assert k0 != decision_task_key(**{**base, "prompt_version": "p2"})
    assert k0 != decision_task_key(
        **{**base, "feedback_policy_version": "fb2"})
    assert k0 == decision_task_key(**base)  # 同输入幂等


def test_expansion_task_key_binds_hypothesis_and_attempt() -> None:
    base = dict(run_id="r", parent_path_id="p", context_ref="c",
                hypothesis_id="h1", attempt_id="a1", policy_version=PV)
    k = expansion_task_key(**base)
    assert k != expansion_task_key(**{**base, "hypothesis_id": "h2"})
    assert k != expansion_task_key(**{**base, "attempt_id": "a2"})
    assert k != expansion_task_key(**{**base, "policy_version": PV + "x"})
    assert k == expansion_task_key(**base)


def test_substrate_feature_cache_key_excludes_search_revision() -> None:
    """E03:parent_search_revision 只进依赖局部搜索状态的键;底物特征
    缓存键不含该参数(结构证据:签名无此参数)。"""
    params = inspect.signature(
        substrate_feature_cache_key).parameters
    assert "parent_search_revision" not in params
    assert substrate_feature_cache_key(
        state_digest="s", feature_policy_version="f1") == \
        substrate_feature_cache_key(state_digest="s",
                                    feature_policy_version="f1")
    assert substrate_feature_cache_key(
        state_digest="s", feature_policy_version="f1") != \
        substrate_feature_cache_key(state_digest="s2",
                                    feature_policy_version="f1")


def test_two_hypotheses_distinct_tasks_attempts_events(tmp_path) -> None:
    """E03 核心:同父两假设 ⇒ 不同任务键/attempt,互不复用;各自提交
    ⇒ 两个事件;alternatives 计 2。"""
    _, ledger, _, _ = make_run(tmp_path, "r-e03")
    subs = []
    for i, origin in enumerate(("k1", "k2")):
        _, _, hyp, _, _ = make_fixture("r-e03", "p1", origin, "ctx1")
        out = enqueue_expand(ledger, "r-e03", parent="p1", context="ctx1",
                             subject=hyp.hypothesis_id,
                             task_key=f"tk-{i}")
        result = drive_commit(ledger, "r-e03", out["action_id"],
                              parent="p1", origin=origin, context="ctx1")
        assert result["completed"]
        subs.append((hyp.hypothesis_id, out["action_id"]))
    assert subs[0][0] != subs[1][0]  # 不同 hypothesis_id
    assert subs[0][1] != subs[1][1]
    snapshot = ledger.budget_snapshot("r-e03")
    assert snapshot["scoped"][
        "max_alternative_hypotheses_per_parent"]["p1"]["used"] == 2
    assert snapshot["run_level"]["max_total_search_actions"]["used"] == 2
    assert snapshot["scoped"]["max_attempts_per_hypothesis"] and all(
        v["used"] == 1 for v in snapshot["scoped"][
            "max_attempts_per_hypothesis"].values())


def test_context_change_yields_new_action_both_legal(tmp_path) -> None:
    """H06 正控:同 hypothesis 不同 context 不是全局互斥对象 —— 两个
    action 各自可认领(事件幂等键含 context,互不覆盖)。"""
    _, ledger, _, _ = make_run(tmp_path, "r-ctx")
    _, _, hyp, _, _ = make_fixture("r-ctx", "p1", "k1", "ctx1")
    ids = []
    for ctx in ("ctx1", "ctx2"):
        out = enqueue_expand(ledger, "r-ctx", parent="p1", context=ctx,
                             subject=hyp.hypothesis_id, task_key="tk")
        assert out["created"]
        ids.append(out["action_id"])
        receipt = ledger.claim_action(out["action_id"], worker_id="w-" + ctx)
        assert receipt["claimed"]
    assert ids[0] != ids[1]


def test_event_replay_no_duplicate_across_retry_attempt(tmp_path) -> None:
    """E03:事件幂等绑定 run/parent/hypothesis/context/语义 —— retry 号/
    claim owner/attempt 序号变化不重复建事件(重开走新 attempt、事件
    重放 created=False、账本仍只有一个事件)。"""
    _, ledger, _, _ = make_run(tmp_path, "r-replay")
    _, _, hyp, event, ev_args = make_fixture("r-replay", "p1", "k1", "ctx1")
    out1 = enqueue_expand(ledger, "r-replay", parent="p1", context="ctx1",
                          subject=hyp.hypothesis_id, task_key="tk1",
                          revision=0)
    receipt = ledger.claim_action(out1["action_id"], worker_id="w1")
    commit_search_event(ledger, out1["action_id"], event, worker_id="w1",
                        attempt_id=(receipt["attempt_refs"] or [""])[0],
                        task_key="tk1", **ev_args)
    first_attempt = (receipt["attempt_refs"])[0]
    # 失败重开:revision 前进 ⇒ 新 action;reopen ⇒ 新 attempt
    out2 = enqueue_expand(ledger, "r-replay", parent="p1", context="ctx1",
                          subject=hyp.hypothesis_id, task_key="tk1",
                          revision=1)
    receipt2 = ledger.claim_action(out2["action_id"], worker_id="w1",
                                   reopen_of=first_attempt)
    second_attempt = (receipt2["attempt_refs"])[0]
    assert second_attempt != first_attempt
    submitted = ledger.submit_action_event(
        out2["action_id"], event, worker_id="w1", **ev_args)
    assert submitted["created"] is False  # 同事件重放,不新增
    ledger.complete_action(out2["action_id"], worker_id="w1",
                            event_id=event.event_id)
    assert ledger.store.counts()["events"] == 1
    snapshot = ledger.budget_snapshot("r-replay")
    assert snapshot["scoped"]["max_attempts_per_hypothesis"][
        hyp.hypothesis_id]["used"] == 2
    assert snapshot["scoped"]["max_reopens_per_hypothesis"][
        hyp.hypothesis_id]["used"] == 1


def test_recovery_follows_frozen_task_key(tmp_path) -> None:
    """E03:恢复沿已冻结键 —— 认领后(即使后续 revision 前进)重开
    ledger/恢复/再认领,task_key 与 attempt 不按当前 revision 重算。"""
    _, ledger, _, _ = make_run(tmp_path, "r-frozen")
    _, _, hyp, _, _ = make_fixture("r-frozen", "p1", "k1", "ctx1")
    out = enqueue_expand(ledger, "r-frozen", parent="p1", context="ctx1",
                         subject=hyp.hypothesis_id, task_key="TK-ORIG")
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    frozen_task_key = receipt["payload"]["task_key"]
    frozen_attempt = receipt["attempt_refs"][0]
    # 搜索状态前进(revision 1 的新 action 入队)
    enqueue_expand(ledger, "r-frozen", parent="p1", context="ctx1",
                   subject=hyp.hypothesis_id, task_key="TK-REV1",
                   revision=1)
    # 内存重置 + 恢复 + 同 worker 再认领
    ledger2 = SearchLedger(ledger.store, ledger.artifact_store, "r-frozen")
    report = ledger2.recover_run("r-frozen")
    b1 = [a for a in report["actions"]
          if a["action_id"] == out["action_id"]]
    assert b1 and b1[0]["boundary"] == "B1_claimed_pending_completion"
    again = ledger2.claim_action(out["action_id"], worker_id="w1")
    assert again["reason"] == "reclaimed_by_owner"
    assert again["payload"]["task_key"] == frozen_task_key
    assert again["attempt_refs"] == [frozen_attempt]
    # 预算未重复扣:原 action 的总 action 预约行恰好一行(再认领复用
    # 同一确定性 ID;revision1 新 action 尚未认领、无预约行)
    rows = ledger.store.conn.execute(
        "SELECT COUNT(*) FROM budget_reservations WHERE action_id = ?"
        " AND limit_key = 'max_total_search_actions'",
        (out["action_id"],)).fetchone()[0]
    assert rows == 1
    snapshot = ledger2.budget_snapshot("r-frozen")
    assert snapshot["run_level"]["max_total_search_actions"]["used"] == 1


# ------------------------------------------------ E04:预算账表/循环


def test_budget_ledger_stepwise_recompute(tmp_path: Path) -> None:
    """E04:按 retrieve→decide→expand→transition 逐步驱动,每步快照
    与持久记录复算一致(内存计数器不存在;快照是派生值)。"""
    _, ledger, _, _ = make_run(tmp_path, "r-e04")
    run = "r-e04"
    # retrieve(非缓存)
    ret = ledger.enqueue_action(
        run_id=run, parent_path_id="p1", context_ref="ctx1",
        subject_ref="pool-1", action_kind=ACTION_KIND_RETRIEVE,
        policy_version=PV, payload={"task_key": "tk-r"})
    ledger.claim_action(ret["action_id"], worker_id="w1")
    # 非事件 outcome 须显式声明(S3A-02:事件类 outcome 不再接受空
    # event_id;decide/retrieve/transition 的合法完成走 OUTCOME)
    ledger.complete_action(ret["action_id"], worker_id="w1",
                            outcome_kind=COMMIT_KIND_OUTCOME)
    s = ledger.budget_snapshot(run)
    assert s["run_level"]["max_total_search_actions"]["used"] == 1
    assert s["scoped"]["max_retrievals_per_parent"]["p1"]["used"] == 1
    assert s["run_level"]["max_retrievals_total"]["used"] == 1
    # decide(冻结池,无检索/attempt)
    dec = ledger.enqueue_action(
        run_id=run, parent_path_id="p1", context_ref="ctx1",
        subject_ref="pool-1", action_kind="decide", policy_version=PV,
        payload={"task_key": "tk-d", "frozen_pool_digest": "poolA"})
    ledger.claim_action(dec["action_id"], worker_id="w1")
    ledger.complete_action(dec["action_id"], worker_id="w1",
                            outcome_kind=COMMIT_KIND_OUTCOME)
    s = ledger.budget_snapshot(run)
    assert s["run_level"]["max_total_search_actions"]["used"] == 2
    assert s["run_level"]["max_retrievals_total"]["used"] == 1
    # expand
    _, _, hyp, _, _ = make_fixture(run, "p1", "k1", "ctx1")
    out = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                         subject=hyp.hypothesis_id, task_key="tk-e")
    drive_commit(ledger, run, out["action_id"])
    s = ledger.budget_snapshot(run)
    assert s["run_level"]["max_total_search_actions"]["used"] == 3
    assert s["scoped"]["max_alternative_hypotheses_per_parent"][
        "p1"]["used"] == 1
    assert s["scoped"]["max_attempts_per_hypothesis"][
        hyp.hypothesis_id]["used"] == 1
    # scenario_transition(另计转换)
    tr = ledger.enqueue_action(
        run_id=run, parent_path_id="p1", context_ref="ctx1",
        subject_ref="scenario-1",
        action_kind=ACTION_KIND_SCENARIO_TRANSITION,
        policy_version=PV, payload={"task_key": "tk-t"})
    ledger.claim_action(tr["action_id"], worker_id="w1")
    ledger.complete_action(tr["action_id"], worker_id="w1",
                            outcome_kind=COMMIT_KIND_OUTCOME)
    s = ledger.budget_snapshot(run)
    assert s["run_level"]["max_scenario_transitions"]["used"] == 1
    assert s["run_level"]["max_total_search_actions"]["used"] == 4


def test_budget_memory_reset_recompute(tmp_path: Path) -> None:
    """E04:内存重置(新 store/ledger 连接)仍从持久记录复算。"""
    db = tmp_path / "r-reset.sqlite"
    store = PollutantPathwayStore(db)
    ledger = SearchLedger(store, ArtifactStore(tmp_path / "runs", "r-reset"),
                          "r-reset")
    ledger.register_search_run("r-reset", build_profile_identity_block())
    _, _, hyp, _, _ = make_fixture("r-reset", "p1", "k1", "ctx1")
    out = enqueue_expand(ledger, "r-reset", parent="p1", context="ctx1",
                         subject=hyp.hypothesis_id, task_key="tk")
    drive_commit(ledger, "r-reset", out["action_id"])
    before = ledger.budget_snapshot("r-reset")
    store.close()
    store2 = PollutantPathwayStore(db)
    ledger2 = SearchLedger(store2, None, "r-reset")
    assert ledger2.budget_snapshot("r-reset") == before
    store2.close()


def test_attempts_per_hypothesis_cap(tmp_path: Path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "r-att")
    run = "r-att"
    _, _, hyp, _, _ = make_fixture(run, "p1", "k1", "ctx1")
    # attempt 1
    out1 = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                          subject=hyp.hypothesis_id, task_key="tk",
                          revision=0)
    drive_commit(ledger, run, out1["action_id"])
    # attempt 2(revision 前进的新 action)
    out2 = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                          subject=hyp.hypothesis_id, task_key="tk",
                          revision=1)
    drive_commit(ledger, run, out2["action_id"])
    # attempt 3 超上限(max_attempts_per_hypothesis=2)
    out3 = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                          subject=hyp.hypothesis_id, task_key="tk",
                          revision=2)
    with pytest.raises(SearchBudgetExhausted) as ei:
        ledger.claim_action(out3["action_id"], worker_id="w1")
    assert ei.value.detail["limit_key"] == "max_attempts_per_hypothesis"
    n = ledger.store.conn.execute(
        "SELECT COUNT(*) FROM search_attempts WHERE run_id = ?",
        (run,)).fetchone()[0]
    assert n == 2


def test_reopen_cap_and_double_constraint(tmp_path: Path) -> None:
    """重开受 max_reopens_per_hypothesis 与总 attempt 双重约束(§4.2):
    本夹具放大 attempts(8)单独验 reopens 上限;attempts 上限由
    test_attempts_per_hypothesis_cap 单独覆盖。"""
    _, ledger, _, _ = make_run(
        tmp_path, "r-reopen",
        {"max_attempts_per_hypothesis": 8, "max_reopens_per_hypothesis": 1})
    run = "r-reopen"
    _, _, hyp, _, _ = make_fixture(run, "p1", "k1", "ctx1")
    out1 = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                          subject=hyp.hypothesis_id, task_key="tk",
                          revision=0)
    receipt = ledger.claim_action(out1["action_id"], worker_id="w1")
    first = receipt["attempt_refs"][0]
    ledger.complete_action(out1["action_id"], worker_id="w1",
                            outcome_kind=COMMIT_KIND_OUTCOME,
                            attempt_status="failed")
    # 重开 1:合法(占 attempts+reopen 双重额度)
    out2 = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                          subject=hyp.hypothesis_id, task_key="tk",
                          revision=1)
    receipt2 = ledger.claim_action(out2["action_id"], worker_id="w1",
                                   reopen_of=first)
    assert receipt2["claimed"]
    ledger.complete_action(out2["action_id"], worker_id="w1",
                           outcome_kind=COMMIT_KIND_OUTCOME,
                           attempt_status="failed")
    # 重开 2:超 max_reopens_per_hypothesis=1
    out3 = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                          subject=hyp.hypothesis_id, task_key="tk",
                          revision=2)
    with pytest.raises(SearchBudgetExhausted) as ei:
        ledger.claim_action(out3["action_id"], worker_id="w1",
                            reopen_of=receipt2["attempt_refs"][0])
    assert ei.value.detail["limit_key"] == "max_reopens_per_hypothesis"


def test_alternatives_per_parent_cap(tmp_path: Path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "r-alt")
    run = "r-alt"
    for i, origin in enumerate(("k1", "k2", "k3")):
        _, _, hyp, _, _ = make_fixture(run, "p1", origin, "ctx1")
        out = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                             subject=hyp.hypothesis_id, task_key=f"tk{i}")
        if i < 2:
            drive_commit(ledger, run, out["action_id"], origin=origin)
        else:
            with pytest.raises(SearchBudgetExhausted) as ei:
                ledger.claim_action(out["action_id"], worker_id="w1")
            assert ei.value.detail[
                "limit_key"] == "max_alternative_hypotheses_per_parent"
    # 不同父不受同一上限约束(计数按 parent scope)
    _, _, hyp2, _, _ = make_fixture(run, "p2", "k3", "ctx1")
    out_p2 = enqueue_expand(ledger, run, parent="p2", context="ctx1",
                            subject=hyp2.hypothesis_id, task_key="tkp2")
    receipt = ledger.claim_action(out_p2["action_id"], worker_id="w1")
    assert receipt["claimed"]


def test_loop_stable_stop_on_small_limits(tmp_path: Path) -> None:
    """E04:小上限 + 循环提案(每轮换备选假设/推进 revision)⇒ 稳定
    终止(循环有界,不反复重开);预算由持久记录复算,used == max。"""
    limits = {"max_alternative_hypotheses_per_parent": 8,
              "max_attempts_per_hypothesis": 8,
              "max_total_search_actions": 5}
    _, ledger, _, _ = make_run(tmp_path, "r-loop", limits)
    run = "r-loop"
    refusals = []
    iterations = 0
    while iterations < 100:  # 循环护栏(证明由预算停,不是护栏停)
        iterations += 1
        origin = f"k{iterations}"
        _, _, hyp, _, _ = make_fixture(run, "p1", origin, "ctx1")
        out = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                             subject=hyp.hypothesis_id,
                             task_key=f"tk{iterations}",
                             revision=iterations)
        if not out.get("created"):
            refusals.append(out)
            break
        try:
            drive_commit(ledger, run, out["action_id"], origin=origin)
        except SearchBudgetExhausted as exc:
            refusals.append({"reason": "budget_limit",
                             "limit_key": exc.detail.get("limit_key")})
            break
    assert iterations < 100, "循环必须由预算停止(稳定终止)"
    assert refusals and refusals[0]["reason"] == "budget_limit"
    report = ledger.stop_report(run, refusals=refusals)
    assert report["primary"] == "budget_limit"
    assert "max_total_search_actions" in report["budget_exhausted_keys"]
    assert report["budget"]["run_level"]["max_total_search_actions"][
        "used"] == 5
    assert report["budget"]["run_level"]["max_total_search_actions"][
        "remaining"] == 0


def test_cache_retrieval_not_double_counted(tmp_path: Path) -> None:
    """E04:复用缓存不算 actual retrieval(检索 0 额度下缓存检索仍可
    执行);但新增 action 不免费(总 action 预算照扣)。"""
    limits = {"max_retrievals_per_parent": 1,
              "max_retrievals_total": 1,
              "max_total_search_actions": 10}
    _, ledger, _, _ = make_run(tmp_path, "r-cache", limits)
    run = "r-cache"
    a1 = ledger.enqueue_action(
        run_id=run, parent_path_id="p1", context_ref="c",
        subject_ref="pool", action_kind=ACTION_KIND_RETRIEVE,
        policy_version=PV, payload={"task_key": "t1"})
    ledger.claim_action(a1["action_id"], worker_id="w1")  # actual
    # 缓存复用:同父第二个 retrieve(cache_hit)可认领,不扣检索额度
    a2 = ledger.enqueue_action(
        run_id=run, parent_path_id="p1", context_ref="c",
        subject_ref="pool", action_kind=ACTION_KIND_RETRIEVE,
        parent_search_revision=1, policy_version=PV,
        payload={"task_key": "t2", "cache_of": "t1"})
    receipt = ledger.claim_action(a2["action_id"], worker_id="w1",
                                  cache_hit=True)
    assert receipt["claimed"]
    # 第三个非缓存 retrieve:per-parent 检索额度(1)已用 ⇒ 拒
    a3 = ledger.enqueue_action(
        run_id=run, parent_path_id="p1", context_ref="c",
        subject_ref="pool", action_kind=ACTION_KIND_RETRIEVE,
        parent_search_revision=2, policy_version=PV,
        payload={"task_key": "t3"})
    with pytest.raises(SearchBudgetExhausted) as ei:
        ledger.claim_action(a3["action_id"], worker_id="w1")
    assert ei.value.detail["limit_key"] == "max_retrievals_per_parent"
    s = ledger.budget_snapshot(run)
    assert s["run_level"]["max_total_search_actions"]["used"] == 2  # 不免费
    assert s["run_level"]["max_retrievals_total"]["used"] == 1


# ------------------------------------------------ 零预算只挡该资源


def test_zero_real_requests_blocks_registration_not_scripted(tmp_path):
    limits = {"max_real_model_requests": 0}
    _, ledger, _, _ = make_run(tmp_path, "r-real0", limits)
    run = "r-real0"
    out = enqueue_expand(ledger, run, parent="p", context="c",
                         subject="h", task_key="t")
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    attempt = receipt["attempt_refs"][0]
    # 真实 provider:额度 0 ⇒ 登记被拒(网络发送被阻止;无请求行)
    with pytest.raises(SearchBudgetExhausted) as ei:
        ledger.register_model_request(
            run_id=run, action_id=out["action_id"], attempt_id=attempt,
            provider_kind=PROVIDER_KIND_REAL, request_key="rk",
            purpose="rank")
    assert ei.value.detail["limit_key"] == "max_real_model_requests"
    n = ledger.store.conn.execute(
        "SELECT COUNT(*) FROM model_requests WHERE run_id = ?",
        (run,)).fetchone()[0]
    assert n == 0
    # scripted provider:登记合法,网络计数 0(不冒充真实调用)
    req = ledger.register_model_request(
        run_id=run, action_id=out["action_id"], attempt_id=attempt,
        provider_kind=PROVIDER_KIND_SCRIPTED, request_key="sk",
        purpose="rank")
    assert req["registered"] and req["network_request_count"] == 0
    ledger.record_request_sent(req["request_id"])
    row = ledger.request(req["request_id"])
    assert row["status"] == "sent"
    assert row["network_request_count"] == 0  # scripted 恒 0


def test_real_request_dangling_occupies_budget(tmp_path: Path) -> None:
    """B2 记账:真实请求失败/超时/悬空均占额;显式重试占剩余额度。"""
    _, ledger, _, _ = make_run(tmp_path, "r-real2",
                                {"max_real_model_requests": 2})
    run = "r-real2"
    out = enqueue_expand(ledger, run, parent="p", context="c",
                         subject="h", task_key="t")
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    attempt = receipt["attempt_refs"][0]
    r1 = ledger.register_model_request(
        run_id=run, action_id=out["action_id"], attempt_id=attempt,
        provider_kind=PROVIDER_KIND_REAL, request_key="k1")
    ledger.record_request_sent(r1["request_id"])
    # r1 悬空(sent 无响应)⇒ 占额
    r2 = ledger.register_model_request(
        run_id=run, action_id=out["action_id"], attempt_id=attempt,
        provider_kind=PROVIDER_KIND_REAL, request_key="k2",
        retry_of=r1["request_id"])
    assert r2["registered"] and r2["request_id"] != r1["request_id"]
    s = ledger.budget_snapshot(run)
    assert s["run_level"]["max_real_model_requests"]["used"] == 2
    # 第三个(即使前两个都悬空)⇒ 拒绝:悬空占额不释放
    with pytest.raises(SearchBudgetExhausted):
        ledger.register_model_request(
            run_id=run, action_id=out["action_id"], attempt_id=attempt,
            provider_kind=PROVIDER_KIND_REAL, request_key="k3")
    ledger.mark_request_failed(r1["request_id"])
    s = ledger.budget_snapshot(run)
    assert s["run_level"]["max_real_model_requests"]["used"] == 2  # 失败仍占


def test_zero_retrieval_only_blocks_retrieve(tmp_path: Path) -> None:
    limits = {"max_retrievals_total": 0, "max_retrievals_per_parent": 0}
    _, ledger, _, _ = make_run(tmp_path, "r-ret0", limits)
    run = "r-ret0"
    ret = ledger.enqueue_action(
        run_id=run, parent_path_id="p", context_ref="c", subject_ref="pool",
        action_kind=ACTION_KIND_RETRIEVE, policy_version=PV, payload={})
    with pytest.raises(SearchBudgetExhausted) as ei:
        ledger.claim_action(ret["action_id"], worker_id="w1")
    assert ei.value.detail["limit_key"] in (
        "max_retrievals_per_parent", "max_retrievals_total")
    # 检索 0 下已冻结池仍可用(decide 可认领)
    dec = ledger.enqueue_action(
        run_id=run, parent_path_id="p", context_ref="c", subject_ref="pool",
        action_kind="decide", policy_version=PV,
        payload={"frozen_pool_digest": "poolA"})
    assert ledger.claim_action(dec["action_id"], worker_id="w1")["claimed"]


def test_zero_transitions_only_blocks_transition(tmp_path: Path) -> None:
    limits = {"max_scenario_transitions": 0}
    _, ledger, _, _ = make_run(tmp_path, "r-tr0", limits)
    run = "r-tr0"
    tr = ledger.enqueue_action(
        run_id=run, parent_path_id="p", context_ref="c",
        subject_ref="sc", action_kind=ACTION_KIND_SCENARIO_TRANSITION,
        policy_version=PV, payload={})
    with pytest.raises(SearchBudgetExhausted) as ei:
        ledger.claim_action(tr["action_id"], worker_id="w1")
    assert ei.value.detail["limit_key"] == "max_scenario_transitions"
    # 普通 expand 不受转换 0 影响
    out = enqueue_expand(ledger, run, parent="p", context="c",
                         subject="h", task_key="t")
    assert ledger.claim_action(out["action_id"], worker_id="w1")["claimed"]


def test_zero_total_actions_blocks_all(tmp_path: Path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "r-act0",
                                {"max_total_search_actions": 0})
    run = "r-act0"
    for kind, subject in (("decide", "pool"), ("retrieve", "pool")):
        out = ledger.enqueue_action(
            run_id=run, parent_path_id="p", context_ref="c",
            subject_ref=subject, action_kind=kind, policy_version=PV,
            payload={})
        with pytest.raises(SearchBudgetExhausted) as ei:
            ledger.claim_action(out["action_id"], worker_id="w1")
        assert ei.value.detail["limit_key"] == "max_total_search_actions"


def test_zero_depth_only_blocks_expansion(tmp_path: Path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "r-d0", {"max_search_depth": 0})
    run = "r-d0"
    out = enqueue_expand(ledger, run, parent="p", context="c",
                         subject="h", task_key="t", depth=1)
    assert not out["created"] and out["reason"] == "depth_limit"
    dec = ledger.enqueue_action(
        run_id=run, parent_path_id="p", context_ref="c", subject_ref="pool",
        action_kind="decide", policy_version=PV, payload={})
    assert ledger.claim_action(dec["action_id"], worker_id="w1")["claimed"]


# ------------------------------------------------ H05:停止原因


def test_h05_zero_action_budget_independent_fixture(tmp_path) -> None:
    """H05 独立夹具 1:仅总 action 预算为 0(其余资源正常)—— 认领被
    拒(refusal 携带 limit_key),主因 budget_limit 且只归因该键。"""
    _, ledger, _, _ = make_run(tmp_path, "r-h05a",
                                {"max_total_search_actions": 0})
    run = "r-h05a"
    out = ledger.enqueue_action(
        run_id=run, parent_path_id="p", context_ref="c", subject_ref="pool",
        action_kind="decide", policy_version=PV, payload={})
    with pytest.raises(SearchBudgetExhausted) as ei:
        ledger.claim_action(out["action_id"], worker_id="w1")
    assert ei.value.detail["limit_key"] == "max_total_search_actions"
    report = ledger.stop_report(
        run, refusals=[{"reason": "budget_limit",
                        "limit_key": "max_total_search_actions"}])
    assert report["primary"] == "budget_limit"
    assert report["budget_exhausted_keys"] == ["max_total_search_actions"]


def test_h05_zero_depth_independent_fixture(tmp_path: Path) -> None:
    """H05 独立夹具 2:仅深度为 0(预算有余额,入队拒绝披露 depth)。"""
    _, ledger, _, _ = make_run(tmp_path, "r-h05b", {"max_search_depth": 0})
    run = "r-h05b"
    refusal = enqueue_expand(ledger, run, parent="p", context="c",
                             subject="h", task_key="t", depth=1)
    assert refusal["reason"] == "depth_limit"
    report = ledger.stop_report(run, refusals=[refusal])
    assert report["primary"] == "depth_limit"
    assert report["budget_exhausted_keys"] == []  # 预算未耗尽(独立成因)


def test_h05_empty_pool_independent_fixture(tmp_path: Path) -> None:
    """H05 独立夹具 3:池为空(无本地候选),预算/深度均正常。"""
    _, ledger, _, _ = make_run(tmp_path, "r-h05c")
    report = ledger.stop_report("r-h05c", no_local_candidate=True)
    assert report["primary"] == "no_local_candidate"
    assert report["budget_exhausted_keys"] == []


def test_h05_user_stop_dominates_composite(tmp_path: Path) -> None:
    resolved = resolve_search_stop(
        {"user_stop", "budget_limit", "depth_limit"})
    assert resolved["primary"] == "user_stop"
    assert set(resolved["other_reasons"]) == {"budget_limit",
                                              "depth_limit"}


def test_h05_budget_beats_depth_priority(tmp_path: Path) -> None:
    resolved = resolve_search_stop({"budget_limit", "depth_limit"})
    assert resolved["primary"] == "budget_limit"
    assert resolved["other_reasons"] == ["depth_limit"]
    with pytest.raises(Exception) as ei:  # noqa: BLE001
        resolve_search_stop({"not_a_reason"})
    assert type(ei.value).__name__ == "SearchContractError"


def test_h05_awaiting_prediction(tmp_path: Path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "r-h05d")
    run = "r-h05d"
    out = enqueue_expand(ledger, run, parent="p", context="c",
                         subject="h", task_key="t")
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    ledger.register_model_request(
        run_id=run, action_id=out["action_id"],
        attempt_id=receipt["attempt_refs"][0],
        provider_kind=PROVIDER_KIND_SCRIPTED, request_key="k")
    report = ledger.stop_report(run)
    # claimed 不算 pending;无 pending 动作且有悬空请求 ⇒ awaiting
    assert report["primary"] == "awaiting_prediction"
    assert report["unexplored"]["pending_requests"] == 1


def test_h05_positive_control_mid_run(tmp_path: Path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "r-h05e")
    run = "r-h05e"
    _, _, hyp, _, _ = make_fixture(run, "p1", "k1", "ctx1")
    out = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                         subject=hyp.hypothesis_id, task_key="tk")
    drive_commit(ledger, run, out["action_id"])
    nxt = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                         subject=hyp.hypothesis_id, task_key="tk2",
                         revision=1)
    report = ledger.stop_report(run)
    assert report["primary"] is None  # 预算有余额、队列有待办:不停
    assert report["unexplored"]["pending_actions"] >= 1
    assert nxt["created"]


def test_h05_deferred_present_not_exhausted_search(tmp_path) -> None:
    """存在 deferred/知识缺口时不称“所有路线都探索完”(停止不是化学
    终点);对照 run:全部完成且无任何未展开集合才 exhausted_search。"""
    _, ledger, _, _ = make_run(tmp_path, "r-h05f")
    run = "r-h05f"
    _, _, hyp, _, _ = make_fixture(run, "p1", "k1", "ctx1")
    out = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                         subject=hyp.hypothesis_id, task_key="tk")
    ledger.claim_action(out["action_id"], worker_id="w1")
    ledger.defer_action(out["action_id"], worker_id="w1",
                        reason="budget_awaiting_prediction")
    report = ledger.stop_report(run)
    assert report["primary"] != "exhausted_search"
    assert report["unexplored"]["deferred"] == 1
    # 对照(独立 run):全部 done、无 deferred/请求/待办 ⇒ exhausted
    _, ledger2, _, _ = make_run(tmp_path, "r-h05f2")
    run2 = "r-h05f2"
    _, _, hyp2, _, _ = make_fixture(run2, "p1", "k1", "ctx1")
    out2 = enqueue_expand(ledger2, run2, parent="p1", context="ctx1",
                          subject=hyp2.hypothesis_id, task_key="tk2")
    drive_commit(ledger2, run2, out2["action_id"])
    report2 = ledger2.stop_report(run2)
    assert report2["primary"] == "exhausted_search"


# ------------------------------------------------ H06:并发认领


def test_h06_two_connections_barrier_single_winner(tmp_path) -> None:
    """H06:两个独立连接配 threading.Barrier 同时争同一 action —— 一方
    取得执行权,另一方 already_claimed;attempt/预约/事件均不翻倍。"""
    db = tmp_path / "r-h06.sqlite"
    store = PollutantPathwayStore(db)
    ledger = SearchLedger(store, ArtifactStore(tmp_path / "runs", "r-h06"),
                          "r-h06")
    ledger.register_search_run("r-h06", build_profile_identity_block())
    _, _, hyp, _, _ = make_fixture("r-h06", "p1", "k1", "ctx1")
    out = enqueue_expand(ledger, "r-h06", parent="p1", context="ctx1",
                         subject=hyp.hypothesis_id, task_key="tk")
    store.close()

    results: dict[str, dict] = {}
    errors: dict[str, BaseException] = {}
    barrier = threading.Barrier(2, timeout=10)

    def contender(name: str) -> None:
        try:
            s = PollutantPathwayStore(db)
            l = SearchLedger(s, None, "r-h06")
            barrier.wait()  # 双方同时到达认领点(确定性同步)
            try:
                results[name] = l.claim_action(out["action_id"],
                                               worker_id=name)
            finally:
                s.close()
        except BaseException as exc:  # noqa: BLE001
            errors[name] = exc

    t1 = threading.Thread(target=contender, args=("wA",))
    t2 = threading.Thread(target=contender, args=("wB",))
    t1.start(); t2.start(); t1.join(30); t2.join(30)

    winners = [n for n, r in results.items() if r.get("claimed")]
    assert len(winners) == 1
    loser = "wB" if winners[0] == "wA" else "wA"
    assert loser in errors
    assert type(errors[loser]).__name__ == "SearchClaimError"
    assert errors[loser].detail["kind"] == "already_claimed"
    # 无翻倍:一行 attempt、一单位总 action 预约
    s2 = PollutantPathwayStore(db)
    l2 = SearchLedger(s2, None, "r-h06")
    assert s2.conn.execute(
        "SELECT COUNT(*) FROM search_attempts WHERE run_id = 'r-h06'"
    ).fetchone()[0] == 1
    snap = l2.budget_snapshot("r-h06")
    assert snap["run_level"]["max_total_search_actions"]["used"] == 1
    s2.close()


def test_h06_claim_done_reuses_outcome_no_new_rows(tmp_path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "r-done")
    run = "r-done"
    _, _, hyp, _, _ = make_fixture(run, "p1", "k1", "ctx1")
    out = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                         subject=hyp.hypothesis_id, task_key="tk")
    result = drive_commit(ledger, run, out["action_id"])
    before = ledger.store.counts()
    receipt = ledger.claim_action(out["action_id"], worker_id="w-other")
    assert receipt["claimed"] is False
    assert receipt["reason"] == "already_completed"
    assert receipt["outcome_ref"]
    assert ledger.store.counts() == before  # 复用完成结果,零新增


def test_h06_stale_worker_cannot_submit_or_overwrite(tmp_path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "r-stale")
    run = "r-stale"
    _, _, hyp, event, ev_args = make_fixture(run, "p1", "k1", "ctx1")
    out = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                         subject=hyp.hypothesis_id, task_key="tk")
    ledger.claim_action(out["action_id"], worker_id="w-owner")
    # 陈旧 worker:提交/完成均拒绝(owner_mismatch)
    with pytest.raises(SearchClaimError) as e1:
        ledger.submit_action_event(out["action_id"], event, worker_id="w2",
                                   **ev_args)
    assert e1.value.detail["kind"] == "owner_mismatch"
    with pytest.raises(SearchClaimError) as e2:
        ledger.complete_action(out["action_id"], worker_id="w2",
                               outcome_kind=COMMIT_KIND_OUTCOME)
    assert e2.value.detail["kind"] == "owner_mismatch"
    # 认领者完成后,陈晚到的 w2 不能覆盖 outcome(幂等 unchanged)
    ledger.complete_action(out["action_id"], worker_id="w-owner",
                           outcome_kind=COMMIT_KIND_OUTCOME,
                           outcome_ref="OUT-1")
    late = ledger.complete_action(out["action_id"], worker_id="w2",
                                  outcome_kind=COMMIT_KIND_OUTCOME,
                                  outcome_ref="EVIL")
    assert late["completed"] is False and late["unchanged"]
    assert ledger.action(out["action_id"])["outcome_ref"] == "OUT-1"


def test_h06_sqlite_busy_visible_concurrency(tmp_path) -> None:
    """SQLite busy 是可见并发结果(SearchConcurrencyError),不当化学
    拒绝;重试沿原 action 身份。"""
    _, ledger, _, _ = make_run(tmp_path, "r-busy")
    run = "r-busy"
    out = enqueue_expand(ledger, run, parent="p", context="c",
                         subject="h", task_key="t")
    conn2 = sqlite3.connect(str(tmp_path / "r-busy.sqlite"))
    conn2.execute("BEGIN IMMEDIATE")  # 持有写锁
    try:
        ledger.conn.execute("PRAGMA busy_timeout=80")
        with pytest.raises(SearchConcurrencyError) as ei:
            ledger.claim_action(out["action_id"], worker_id="w1")
        assert ei.value.detail["kind"] == "sqlite_busy"
    finally:
        conn2.rollback()
        conn2.close()
        ledger.conn.execute("PRAGMA busy_timeout=5000")
    # 锁释放后沿同一 action 重试成功(不绕预算)
    assert ledger.claim_action(out["action_id"], worker_id="w1")["claimed"]


# ------------------------------------------------ 请求状态机/注入


def test_request_lifecycle_state_machine(tmp_path: Path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "r-req")
    run = "r-req"
    out = enqueue_expand(ledger, run, parent="p", context="c",
                         subject="h", task_key="t")
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    attempt = receipt["attempt_refs"][0]
    req = ledger.register_model_request(
        run_id=run, action_id=out["action_id"], attempt_id=attempt,
        provider_kind=PROVIDER_KIND_SCRIPTED, request_key="k1")
    # 同键幂等
    again = ledger.register_model_request(
        run_id=run, action_id=out["action_id"], attempt_id=attempt,
        provider_kind=PROVIDER_KIND_SCRIPTED, request_key="k1")
    assert again["registered"] is False and again["unchanged"]
    ledger.record_request_sent(req["request_id"])
    # 已 sent ⇒ 不可重复发送(不默发第二请求)
    with pytest.raises(Exception) as ei:  # noqa: BLE001
        ledger.record_request_sent(req["request_id"])
    assert ei.value.detail["kind"] == "request_not_resendable"
    ledger.record_request_response(req["request_id"], "resp-ref")
    assert ledger.request(req["request_id"])[
        "status"] == REQUEST_STATUS_RESPONDED
    with pytest.raises(Exception) as e2:  # noqa: BLE001
        ledger.mark_request_failed(req["request_id"])
    assert e2.value.detail["kind"] == "request_not_failable"


def test_crash_injection_point_b4(tmp_path: Path) -> None:
    """B4 注入点:事件提交后、记账前“终止”(SearchCrashInjection)。"""
    _, ledger, _, _ = make_run(tmp_path, "r-inject")
    run = "r-inject"
    _, _, hyp, event, ev_args = make_fixture(run, "p1", "k1", "ctx1")
    out = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                         subject=hyp.hypothesis_id, task_key="tk")
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    with pytest.raises(SearchCrashInjection):
        commit_search_event(
            ledger, out["action_id"], event, worker_id="w1",
            attempt_id=receipt["attempt_refs"][0], task_key="tk",
            crash_after="event_submitted", **ev_args)
    # 状态:事件已提交、记账未闭合(B4 可达状态)
    assert ledger.store.counts()["events"] == 1
    assert ledger.action(out["action_id"])["status"] == "claimed"


# ------------------------------------------------ 继承与 runner 边界


def test_search_layer_composes_with_frozen_validation(tmp_path) -> None:
    """R8 继承:搜索提交链不绕过公共 writer 首消费验证 —— 篡改 raw
    (CCO |r|)的状态载荷经搜索驱动提交仍被拒,零事件。"""
    _, ledger, _, _ = make_run(tmp_path, "r-tamper")
    run = "r-tamper"
    sub, prod, hyp, event, ev_args = make_fixture(run, "p1", "k1", "ctx1")
    out = enqueue_expand(ledger, run, parent="p1", context="ctx1",
                         subject=hyp.hypothesis_id, task_key="tk")
    ledger.claim_action(out["action_id"], worker_id="w1")
    tampered = sub.to_dict()
    tampered["structure_smiles_raw"] = "CCO |r|"  # R7-01 同根反例
    with pytest.raises(Exception) as ei:  # noqa: BLE001
        ledger.submit_action_event(
            out["action_id"], event, worker_id="w1",
            report_projection=ev_args["report_projection"],
            expansion_plan=ev_args["expansion_plan"],
            states=[tampered, prod.to_dict()],
            hypothesis_dict=ev_args["hypothesis_dict"])
    assert type(ei.value).__name__ in ("Ppv1StateContractError",
                                       "ChemicalStateError")
    assert ledger.store.counts()["events"] == 0  # 零写入


def test_runner_start_and_resume_dispatch_ppv1(tmp_path) -> None:
    """S3b 行为翻转(2026-10-08,原 S3a fail-closed 按交付解除):公开
    runner 双入口对 PPV1 分流到 pollutant.runflow —— start 建独立
    PPV1 存储(resume 不重建/不覆盖既有搜索/attempt/提交记录);完整
    E2E/崩溃恢复验收见 tests/test_ppv1_s3b_runner.py。legacy 不受影响
    (legacy 路径回归另由既有 legacy 测试覆盖)。"""
    from pathway_v43.storage.run_identity import (
        PROFILE_POLLUTANT_PATHWAY_V1,
    )
    from pathway_v43.workflow.runner import resume_run, start_run
    from pathway_v43.config import resolve_config

    runs_root = tmp_path / "runs"
    out = start_run(
        config=resolve_config(), runs_root=runs_root,
        run_id="ppv1-s3a", smiles="CCO", max_depth=2,
        max_expansions=5, max_frontier_width=3, finder=object(),
        scripted=True, profile=PROFILE_POLLUTANT_PATHWAY_V1)
    assert out["profile"] == PROFILE_POLLUTANT_PATHWAY_V1
    assert (runs_root / "ppv1-s3a" / "pollutant.sqlite").is_file()
    resumed = resume_run(config=resolve_config(), runs_root=runs_root,
                         run_id="ppv1-s3a", finder=object())
    assert resumed["resumed"] is True
    assert resumed["counts"]["events"] == out["counts"]["events"]


def test_h07_wrapper_preserves_files(tmp_path: Path) -> None:
    """H07 wrapper 单元:不可反序列化/hash 不符都报结构化完整性错误,
    原文件字节保全。"""
    art = ArtifactStore(tmp_path / "runs", "r-h07")
    art.write("tk", "search_commit_bundle", {"a": 1})
    path = tmp_path / "runs" / "r-h07" / "results" / "tk" / \
        "search_commit_bundle.json"
    # 合法读
    env = read_search_artifact(art, "tk", "search_commit_bundle")
    assert env["payload"] == {"a": 1}
    # hash 不符(payload 被改、信封 hash 不动)
    import json
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["payload"]["a"] = 2
    path.write_text(json.dumps(doc), encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(Exception) as e1:  # noqa: BLE001
        read_search_artifact(art, "tk", "search_commit_bundle")
    assert type(e1.value).__name__ == "SearchArtifactIntegrityError"
    assert e1.value.detail["kind"] == "artifact_hash_mismatch"
    assert path.read_bytes() == before  # 保全
    # 不可反序列化
    path.write_bytes(b"\x00\x91 not json")
    before2 = path.read_bytes()
    with pytest.raises(Exception) as e2:  # noqa: BLE001
        read_search_artifact(art, "tk", "search_commit_bundle")
    assert e2.value.detail["kind"] == "artifact_unparseable"
    assert path.read_bytes() == before2
