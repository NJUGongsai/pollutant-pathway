"""S3a 回修 r2 回归(Codex S3a 复审 S3A-01~05;ppv1-search-2 消费协议)。

先固定合法与坏输入,再断言修复后的正确行为(任务书 §9.1):本文件在
直接父基线 9b78f4279cc6fa50b3b51c31a5c8e07abbeda207 上跑同字节时,
坏案断言按预期失败(行为红 = 修前缺口),合法控制保持绿 —— 红绿分类
见交付书;不拿 00e509a 的初次 S3a collection 红替代本轮行为红。

覆盖(复审报告 §4 五组 P1 的最低验收):
- S3A-01:B3 消费四类异身份有效事件(run/parent/context/hypothesis
  各一案)在写 event/commit/consume 前拒、artifact 保全;写侧
  write_commit_bundle 同源拒;正常提交路径同判据;
- S3A-02:首次 complete 空/缺失/异父 event 拒;B4 缺预约/attempt
  引用行拒;12×2 坏事件账(B4/done 各 12)在恢复消费前结构化失败、
  零补账;done/已有提交结果复用入口同样经完整权威核验;
- S3A-03:已提交事件经 defer 退已用预算被拒(上限 1 连用反例);
  已发送请求不可 defer 退;合法未执行 defer 释放保持;registered
  请求随 defer 转 abandoned 且真实请求占额保留;四非法策略块注册
  零写入拒 + 合法块通过;存储块被改坏在读取消费前拒;
- S3A-04:请求同键异 payload/purpose/action/损坏 hash 冲突零写入;
  登记 execution 引用闭合(未认领/不存在 action、异属/缺失 attempt、
  expand 空 attempt);已释放执行权不可发送/记响应/记失败(状态机
  + 执行引用双闸);非 expand 合法空 attempt 正控;
- S3A-05:claimed/open attempt 计入未完成集合且阻止 exhausted_search;
  空 run/真完成的合法 exhaustion、user_stop 支配保持。

全部合成输入(CCO → CC=O),无金标/题面/封存材料/外部模型。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from s3a_worker import make_fixture  # noqa: E402
from pathway_v43.pollutant.profile import (  # noqa: E402
    build_profile_identity_block,
)
from pathway_v43.pollutant.search import (  # noqa: E402
    ACTION_KIND_EXPAND_HYPOTHESIS,
    ATTEMPT_STATUS_ABANDONED,
    ATTEMPT_STATUS_OPEN,
    COMMIT_KIND_OUTCOME,
    PROVIDER_KIND_REAL,
    PROVIDER_KIND_SCRIPTED,
    REQUEST_STATUS_ABANDONED,
    RESERVATION_STATUS_CONSUMED,
    RESERVATION_STATUS_RELEASED,
    RESERVATION_STATUS_RESERVED,
    SearchArtifactIntegrityError,
    SearchBudgetExhausted,
    SearchClaimError,
    SearchContractError,
    SearchIdentityConflict,
    SearchIntegrityError,
    SearchLedger,
    SearchRecoveryError,
    commit_search_event,
    search_policy_version,
)
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402

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


def fresh_ledger(db: Path, runs_root: Path, run: str) -> SearchLedger:
    return SearchLedger(PollutantPathwayStore(db),
                        ArtifactStore(runs_root, run), run)


def one(ledger, sql, params=()):
    return ledger.conn.execute(sql, params).fetchone()[0]


def action_status(ledger, action_id) -> str:
    return one(ledger, "SELECT status FROM search_actions WHERE"
                " action_id = ?", (action_id,))


def bundle_path(runs_root: Path, run: str, task_key: str) -> Path:
    return runs_root / run / "results" / task_key / \
        "search_commit_bundle.json"


# ------------------------------------------------------------ S3A-01


@pytest.mark.parametrize("mutate", ["run", "parent", "context",
                                    "hypothesis"])
def test_b3_wrong_identity_event_rejected_before_consume(
        tmp_path: Path, mutate: str) -> None:
    """S3A-01 四分案:合法 claimed A + 独立有效事件 B(仅 run/parent/
    context/hypothesis 之一不同),bundle 绑定 A 的 action/attempt、
    字节/hash 合法 —— 恢复必须在写 event/commit/consume 前拒,原
    artifact 保全,B 不入账;同一 B 经正常提交也拒(同判据)。"""
    name = f"r2a-{mutate}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp_a, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp_a.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    attempt = receipt["attempt_refs"][0]
    # 独立有效事件 B:按 mutation 改单一身份维度(内容/hash 全合法)
    b_run = "other-run" if mutate == "run" else name
    b_parent = "p2" if mutate == "parent" else "p1"
    b_origin = "k2" if mutate == "hypothesis" else "k1"
    b_ctx = "ctx2" if mutate == "context" else "ctx1"
    _, _, _, event_b, ev_b = make_fixture(b_run, b_parent, b_origin, b_ctx)
    payload = {
        "bundle_version": "ppv1-search-commit-bundle-1",
        "action_id": out["action_id"], "attempt_id": attempt,
        "event": {
            "schema_version": event_b.schema_version,
            "event_id": event_b.event_id, "run_id": event_b.run_id,
            "parent_path_id": event_b.parent_path_id,
            "hypothesis_id": event_b.hypothesis_id,
            "context_hash": event_b.context_hash,
            "participants": list(event_b.participants),
            "participant_state_refs": list(event_b.participant_state_refs),
            "catalytic_support": list(event_b.catalytic_support),
        },
        "report_projection": ev_b["report_projection"],
        "expansion_plan": ev_b["expansion_plan"],
        "states": ev_b["states"],
        "hypothesis_dict": ev_b["hypothesis_dict"],
        "task_key": "tk1",
    }
    art.write("tk1", "search_commit_bundle", payload)
    path = bundle_path(runs_root, name, "tk1")
    before = path.read_bytes()

    # 同一 B 经正常搜索提交:身份未冻结到 A ⇒ 拒(同源判据)
    with pytest.raises(SearchContractError) as e_sub:
        ledger.submit_action_event(out["action_id"], event_b,
                                   worker_id="w1", **ev_b)
    assert e_sub.value.detail["kind"] == "event_identity_not_frozen_to_action"

    ledger2 = fresh_ledger(db, runs_root, name)
    report = ledger2.recover_run(name)
    entry = [a for a in report["actions"]
             if a["action_id"] == out["action_id"]][0]
    assert entry["boundary"] == "B3_artifact_written_event_uncommitted"
    assert entry["disposition"]["error"] == "SearchArtifactIntegrityError"
    assert entry["disposition"]["kind"] == "bundle_event_identity_not_frozen"
    # 坏 action 零 event/commit/consume;A 仍 claimed;artifact 保全
    assert ledger2.store.counts()["events"] == 0
    assert one(ledger2, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == 0
    assert action_status(ledger2, out["action_id"]) == "claimed"
    assert path.read_bytes() == before
    # 二次恢复同样拒绝(不静默跳过/不重跑覆盖)
    report2 = ledger2.recover_run(name)
    entry2 = [a for a in report2["actions"]
              if a["action_id"] == out["action_id"]][0]
    assert entry2["disposition"]["kind"] == "bundle_event_identity_not_frozen"
    assert ledger2.store.counts()["events"] == 0
    store.close()
    ledger2.store.close()


def test_write_bundle_rejects_wrong_identity_event(tmp_path: Path) -> None:
    """S3A-01 写侧:write_commit_bundle 对异身份事件同源拒,artifact
    不落盘(不把"消费口会拒"当写侧免检);task_key 错绑同拒。"""
    name = "r2a-write"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp_a, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp_a.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    attempt = receipt["attempt_refs"][0]
    _, _, _, event_b, ev_b = make_fixture(name, "p2", "k1", "ctx1")
    with pytest.raises(SearchContractError) as ei:
        ledger.write_commit_bundle(
            action_id=out["action_id"], attempt_id=attempt,
            event=event_b, task_key="tk1", **ev_b)
    assert ei.value.detail["kind"] == "event_identity_not_frozen_to_action"
    assert not bundle_path(runs_root, name, "tk1").exists()
    # 合法事件 + 错 task_key(与 action 冻结 task_key 不一致)⇒ 写侧拒
    _, _, _, event_a, ev_a = make_fixture(name, "p1", "k1", "ctx1")
    with pytest.raises(SearchContractError) as e2:
        ledger.write_commit_bundle(
            action_id=out["action_id"], attempt_id=attempt,
            event=event_a, task_key="tkX", **ev_a)
    assert e2.value.detail["kind"] == "bundle_task_key_binding_mismatch"
    assert not bundle_path(runs_root, name, "tk1").exists()
    store.close()


# ------------------------------------------------------------ S3A-02


def test_first_complete_event_outcome_requires_real_event(
        tmp_path: Path) -> None:
    """S3A-02:事件类 outcome 不能空/不存在/异父 —— 三案在写 done/
    commit/consume 之前拒,零写账。"""
    name = "r2c-empty"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    # 1) 空 event_id
    with pytest.raises(SearchContractError) as e1:
        ledger.complete_action(out["action_id"], worker_id="w1")
    assert e1.value.detail["kind"] == "commit_event_id_empty"
    # 2) 不存在的 event
    with pytest.raises(SearchIntegrityError) as e2:
        ledger.complete_action(out["action_id"], worker_id="w1",
                               event_id="ev-missing-xxx")
    assert e2.value.detail["kind"] == "commit_event_missing"
    # 3) 另父有效 event:同 run 下 p2 的合法 action 先提交一个事件
    _, _, hyp_b, event_b, ev_b = make_fixture(name, "p2", "k1", "ctx1")
    out_b = enqueue(ledger, name, hyp_b.hypothesis_id, parent="p2",
                    task_key="tkB")
    ledger.claim_action(out_b["action_id"], worker_id="w1")
    ledger.submit_action_event(out_b["action_id"], event_b,
                               worker_id="w1", **ev_b)
    with pytest.raises(SearchIntegrityError) as e3:
        ledger.complete_action(out["action_id"], worker_id="w1",
                               event_id=event_b.event_id)
    assert e3.value.detail["kind"] == "commit_event_identity_mismatch"
    # 三案均零写账:A 仍 claimed、无提交记录、预约未被 consume
    assert action_status(ledger, out["action_id"]) == "claimed"
    assert one(ledger, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == 0
    rows = ledger.conn.execute(
        "SELECT status FROM budget_reservations WHERE action_id = ? AND"
        " limit_key = 'max_total_search_actions'",
        (out["action_id"],)).fetchall()
    assert [r["status"] for r in rows] == [RESERVATION_STATUS_RESERVED]
    store.close()


@pytest.mark.parametrize("drop", ["reservation", "attempt"])
def test_b4_recovery_missing_reference_rows_refused(
        tmp_path: Path, drop: str) -> None:
    """S3A-02:合法事件提交后删本 action 必需的预约/attempt 行 ⇒
    B4 恢复按缺权威失败(UPDATE 0 行不是成功),零补账。"""
    name = f"r2b-{drop}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, event, ev_args = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    ledger.claim_action(out["action_id"], worker_id="w1")
    ledger.submit_action_event(out["action_id"], event,
                               worker_id="w1", **ev_args)  # B4 状态
    if drop == "reservation":
        rid = ledger.action(out["action_id"])["budget_reservation_ref"][0]
        ledger.conn.execute(
            "DELETE FROM budget_reservations WHERE reservation_id = ?",
            (rid,))
    else:
        aid = ledger.action(out["action_id"])["attempt_refs"][0]
        ledger.conn.execute(
            "DELETE FROM search_attempts WHERE expansion_attempt_id = ?",
            (aid,))
    ledger.conn.commit()
    store.close()

    ledger2 = fresh_ledger(db, runs_root, name)
    with pytest.raises(SearchIntegrityError) as ei:
        ledger2.recover_run(name)
    assert ei.value.detail["kind"] == (
        "reservation_row_missing" if drop == "reservation"
        else "attempt_row_missing")
    # 零补账:action 仍 claimed、无提交记录、事件仍 1
    assert action_status(ledger2, out["action_id"]) == "claimed"
    assert one(ledger2, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == 0
    assert ledger2.store.counts()["events"] == 1
    ledger2.store.close()


def _event_manifest_entry(conn, event_id: str):
    row = conn.execute(
        "SELECT payload, hypothesis_id FROM events WHERE event_id = ?",
        (event_id,)).fetchone()
    payload = json.loads(row["payload"])
    entry = payload["event_appearance_manifest"][0]
    return entry["state_id"], entry["appearance_hash"], row["hypothesis_id"]


def corrupt_event_ledger(conn, event_id: str, kind: str) -> None:
    """12 类坏事件账注入(复审继承专项同款口径;只改/删,不重建)。"""
    sid, ahash, hyp_id = _event_manifest_entry(conn, event_id)

    def rewrite(table, key_sql, key_params, mutate):
        row = conn.execute(f"SELECT payload FROM {table} WHERE {key_sql}",
                           key_params).fetchone()
        doc = json.loads(row["payload"])
        mutate(doc)
        conn.execute(f"UPDATE {table} SET payload = ? WHERE {key_sql}",
                     (json.dumps(doc, ensure_ascii=False, sort_keys=True),
                      *key_params))

    if kind == "state_charge":
        rewrite("states", "state_id = ?", (sid,),
                lambda d: d.update(formal_charge=99))
    elif kind == "state_schema":
        rewrite("states", "state_id = ?", (sid,),
                lambda d: d.update(schema_version="ppv1-chemstate-99"))
    elif kind == "appearance_source":
        rewrite("state_appearances",
                "state_id = ? AND appearance_hash = ?", (sid, ahash),
                lambda d: d.update(structure_origin="evil_origin"))
    elif kind == "appearance_raw":
        rewrite("state_appearances",
                "state_id = ? AND appearance_hash = ?", (sid, ahash),
                lambda d: d.update(structure_smiles_raw="CCCO"))
    elif kind == "hypothesis_origin":
        rewrite("hypotheses", "hypothesis_id = ?", (hyp_id,),
                lambda d: d.update(origin_group_key="evil-origin"))
    elif kind == "event_manifest":
        rewrite("events", "event_id = ?", (event_id,),
                lambda d: d.__setitem__(
                    "event_appearance_manifest",
                    d["event_appearance_manifest"][:-1]))
    elif kind == "projection_delete":
        conn.execute("DELETE FROM report_projections WHERE event_id = ?",
                     (event_id,))
    elif kind == "plan_delete":
        conn.execute("DELETE FROM expansion_plans WHERE event_id = ?",
                     (event_id,))
    elif kind == "links_delete":
        conn.execute("DELETE FROM event_appearance_links WHERE"
                     " event_id = ?", (event_id,))
    elif kind == "state_delete":
        conn.execute("DELETE FROM states WHERE state_id = ?", (sid,))
    elif kind == "appearance_delete":
        conn.execute("DELETE FROM state_appearances WHERE state_id = ?"
                     " AND appearance_hash = ?", (sid, ahash))
    elif kind == "hypothesis_delete":
        conn.execute("DELETE FROM hypotheses WHERE hypothesis_id = ?",
                     (hyp_id,))
    else:  # pragma: no cover - 参数化穷尽
        raise AssertionError(f"unknown corruption kind {kind}")
    conn.commit()


BAD_LEDGER_KINDS = [
    "state_charge", "state_schema", "appearance_source", "appearance_raw",
    "hypothesis_origin", "event_manifest", "projection_delete",
    "plan_delete", "links_delete", "state_delete", "appearance_delete",
    "hypothesis_delete",
]


@pytest.mark.parametrize("kind", BAD_LEDGER_KINDS)
@pytest.mark.parametrize("mode", ["b4", "done"])
def test_bad_event_ledger_authority_refused_before_consume(
        tmp_path: Path, mode: str, kind: str) -> None:
    """S3A-02 12×2:坏事件账在 B4 补账/done 复用**首次消费之前**结构化
    失败(完整权威核验 = 公共 writer 重放同源),零补账、保全;同库
    原有效输入经公共 writer 重放同样拒(已有 S0–S2 契约,不重验)。"""
    name = f"r2d-{mode}-{kind}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, event, ev_args = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    ledger.claim_action(out["action_id"], worker_id="w1")
    ledger.submit_action_event(out["action_id"], event,
                               worker_id="w1", **ev_args)
    if mode == "done":
        ledger.complete_action(out["action_id"], worker_id="w1",
                               event_id=event.event_id)
        assert action_status(ledger, out["action_id"]) == "done"
    corrupt_event_ledger(ledger.conn, event.event_id, kind)
    commits_before = one(ledger, "SELECT COUNT(*) FROM"
                          " search_commit_records WHERE run_id = ?", (name,))
    store.close()

    ledger2 = fresh_ledger(db, runs_root, name)
    with pytest.raises(SearchIntegrityError) as ei:
        ledger2.recover_run(name)
    assert ei.value.detail["kind"] in (
        "event_ledger_authority_failed", "commit_attached_record_missing",
        "commit_event_missing", "commit_event_identity_mismatch",
        "commit_record_event_missing", "commit_record_hash_mismatch")
    # 零补账:提交记录数不变;b4 保持 claimed(未补 done),done 保持
    # done(未被"修复");事件/产品扩展不重复
    assert one(ledger2, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == commits_before
    expected = "claimed" if mode == "b4" else "done"
    assert action_status(ledger2, out["action_id"]) == expected
    assert ledger2.store.counts()["events"] == 1
    ledger2.store.close()


def test_done_reuse_entries_verify_full_authority(tmp_path: Path) -> None:
    """S3A-02 复用入口:claim 的 done 复用分支与 complete 的幂等复用
    分支同样经完整权威核验(不能 get 索引即成功);坏账 ⇒ 结构化失败。"""
    name = "r2e"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, event, ev_args = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    ledger.claim_action(out["action_id"], worker_id="w1")
    commit_search_event(ledger, out["action_id"], event, worker_id="w1",
                        attempt_id="", task_key="tk1", **ev_args)
    assert action_status(ledger, out["action_id"]) == "done"
    corrupt_event_ledger(ledger.conn, event.event_id, "state_delete")
    store.close()

    ledger2 = fresh_ledger(db, runs_root, name)
    with pytest.raises(SearchIntegrityError):
        ledger2.claim_action(out["action_id"], worker_id="w-other")
    with pytest.raises(SearchIntegrityError):
        ledger2.complete_action(out["action_id"], worker_id="w1",
                                event_id=event.event_id)
    with pytest.raises(SearchIntegrityError):
        ledger2.submit_action_event(out["action_id"], event,
                                    worker_id="w1", **ev_args)
    ledger2.store.close()


# ------------------------------------------------------------ S3A-03


def test_defer_cannot_refund_submitted_event_budget(tmp_path: Path) -> None:
    """S3A-03 上限 1 连用反例:先提交事件再 defer 退额度被拒 ——
    完整公开链无法留下多个已执行 event 而预算 used=0;实际执行次数
    与预算源记录可逐步复算(used 恒 ≥ 已提交事件归属的执行数)。"""
    limits = {"max_total_search_actions": 1,
              "max_alternative_hypotheses_per_parent": 1}
    name = "r2f"
    store, ledger, art, policy, db, runs_root = make_run(
        tmp_path, name, limits)
    _, _, hyp, event, ev_args = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    ledger.claim_action(out["action_id"], worker_id="w1")
    ledger.submit_action_event(out["action_id"], event,
                               worker_id="w1", **ev_args)
    with pytest.raises(SearchContractError) as ei:
        ledger.defer_action(out["action_id"], worker_id="w1", reason="x")
    assert ei.value.detail["kind"] == "defer_after_execution"
    assert ei.value.detail["evidence"] == "committed_event"
    # 预算未退:used=1;事件 1;A 仍 claimed;第二个备选无法再占用
    snap = ledger.budget_snapshot(name)
    assert snap["run_level"]["max_total_search_actions"]["used"] == 1
    assert ledger.store.counts()["events"] == 1
    assert action_status(ledger, out["action_id"]) == "claimed"
    _, _, hyp2, _, _ = make_fixture(name, "p1", "k2", "ctx1")
    out2 = enqueue(ledger, name, hyp2.hypothesis_id, task_key="tk2")
    with pytest.raises(SearchBudgetExhausted) as eb:
        ledger.claim_action(out2["action_id"], worker_id="w1")
    assert eb.value.detail["limit_key"] == "max_total_search_actions"
    store.close()


def test_defer_after_sent_request_refused(tmp_path: Path) -> None:
    """S3A-03:已发送请求是已执行操作,defer 不可退额度。"""
    name = "r2g"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    req = ledger.register_model_request(
        run_id=name, action_id=out["action_id"],
        attempt_id=receipt["attempt_refs"][0],
        provider_kind=PROVIDER_KIND_SCRIPTED, request_key="k1")
    ledger.record_request_sent(req["request_id"])
    with pytest.raises(SearchContractError) as ei:
        ledger.defer_action(out["action_id"], worker_id="w1", reason="x")
    assert ei.value.detail["kind"] == "defer_after_execution"
    assert ei.value.detail["evidence"] == "request_sent"
    snap = ledger.budget_snapshot(name)
    assert snap["run_level"]["max_total_search_actions"]["used"] == 1
    assert action_status(ledger, out["action_id"]) == "claimed"
    store.close()


def test_defer_unexecuted_releases_legal_control(tmp_path: Path) -> None:
    """S3A-03 正控:未执行 defer 合法释放(预约 released、attempt
    abandoned、action deferred);不能全面拒绝合法路径。"""
    name = "r2h"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    result = ledger.defer_action(out["action_id"], worker_id="w1",
                                 reason="await")
    assert result["deferred"]
    assert action_status(ledger, out["action_id"]) == "deferred"
    rows = ledger.conn.execute(
        "SELECT status FROM budget_reservations WHERE action_id = ? AND"
        " limit_key = 'max_total_search_actions'",
        (out["action_id"],)).fetchall()
    assert [r["status"] for r in rows] == [RESERVATION_STATUS_RELEASED]
    attempt = ledger.conn.execute(
        "SELECT status FROM search_attempts WHERE run_id = ?",
        (name,)).fetchone()
    assert attempt["status"] == ATTEMPT_STATUS_ABANDONED
    snap = ledger.budget_snapshot(name)
    assert snap["run_level"]["max_total_search_actions"]["used"] == 0
    store.close()


def test_defer_abandons_registered_request_real_quota_kept(
        tmp_path: Path) -> None:
    """S3A-03/04:registered(未发送)请求不阻止合法 defer;defer 把
    该请求转 abandoned(生命周期闭合),真实请求登记额度继续占额
    (悬空/失败真实请求占额,永不释放)。"""
    name = "r2i"
    store, ledger, art, policy, db, runs_root = make_run(
        tmp_path, name, {"max_real_model_requests": 2})
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    req = ledger.register_model_request(
        run_id=name, action_id=out["action_id"],
        attempt_id=receipt["attempt_refs"][0],
        provider_kind=PROVIDER_KIND_REAL, request_key="rk")
    result = ledger.defer_action(out["action_id"], worker_id="w1",
                                 reason="await")
    assert result["deferred"]
    assert ledger.request(req["request_id"])["status"] == \
        REQUEST_STATUS_ABANDONED
    snap = ledger.budget_snapshot(name)
    assert snap["run_level"]["max_real_model_requests"]["used"] == 1
    # abandoned 请求不可再发送(显式重试须新 request 及剩余额度)
    with pytest.raises(SearchContractError) as ei:
        ledger.record_request_sent(req["request_id"])
    assert ei.value.detail["kind"] == "request_not_resendable"
    store.close()


@pytest.mark.parametrize("bad_limits,why", [
    ({"max_total_search_actions": 1001}, "越界"),
    ({"max_total_search_actions": True}, "bool 不是整数"),
    ({"nope_unknown_key": 1}, "未知键"),
    ({"max_total_search_actions": -1}, "负数"),
])
def test_register_rejects_illegal_policy_blocks(tmp_path: Path,
                                                bad_limits: dict,
                                                why: str) -> None:
    """S3A-03:四非法策略块在注册写入前拒(现成十键类型/范围同源
    校验),search_runs 零写入;合法修改块通过。"""
    name = f"r2j-{why}"
    store = PollutantPathwayStore(tmp_path / f"{name}.sqlite")
    ledger = SearchLedger(store, None, name)
    policy = build_profile_identity_block()
    policy["search_limits"].update(bad_limits)
    with pytest.raises(SearchContractError) as ei:
        ledger.register_search_run(name, policy)
    assert ei.value.detail["kind"] == "invalid_search_policy_block"
    n = store.conn.execute(
        "SELECT COUNT(*) FROM search_runs WHERE run_id = ?",
        (name,)).fetchone()[0]
    assert n == 0  # 零写入
    # 合法修改块通过
    ok_policy = build_profile_identity_block(
        search_limits={"max_total_search_actions": 3})
    ledger.register_search_run(name, ok_policy)
    assert ledger._limits(name)["max_total_search_actions"] == 3
    store.close()


def test_stored_policy_block_corrupt_rejected_on_read(tmp_path) -> None:
    """S3A-03:存储策略块被改坏 ⇒ 读取消费(enqueue/claim 恢复路径
    的 _limits)结构化拒绝,不猜数据。"""
    name = "r2k"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    corrupt = json.loads(json.dumps(policy))
    corrupt["search_limits"]["max_total_search_actions"] = 1001
    ledger.conn.execute(
        "UPDATE search_runs SET policy_block = ? WHERE run_id = ?",
        (json.dumps(corrupt, ensure_ascii=False, sort_keys=True), name))
    ledger.conn.commit()
    with pytest.raises(SearchRecoveryError) as ei:
        enqueue(ledger, name, "h", task_key="tk1")
    assert ei.value.detail["kind"] == "search_policy_block_corrupt"
    store.close()


# ------------------------------------------------------------ S3A-04


@pytest.mark.parametrize("mutate", ["payload", "purpose", "action",
                                    "tampered_hash"])
def test_request_same_key_conflicts(tmp_path: Path, mutate: str) -> None:
    """S3A-04:同键异 payload/purpose/action(空 attempt 的非 expand
    请求)/损坏 hash 的同载荷重用均结构化冲突,零写入。"""
    name = f"r2l-{mutate}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    # 两个合法 claimed decide action(空 attempt:非 expand 合法路径)
    ids = []
    for i in range(2):
        out = ledger.enqueue_action(
            run_id=name, parent_path_id="p1", context_ref="ctx1",
            subject_ref=f"pool-{i}", action_kind="decide",
            policy_version=PV, payload={"task_key": f"tk{i}"})
        ledger.claim_action(out["action_id"], worker_id="w1")
        ids.append(out["action_id"])
    base = dict(run_id=name, action_id=ids[0], attempt_id="",
                provider_kind=PROVIDER_KIND_SCRIPTED, request_key="same-k",
                purpose="rank", payload={"a": 1})
    ledger.register_model_request(**base)
    if mutate == "tampered_hash":
        ledger.conn.execute(
            "UPDATE model_requests SET payload_hash = ? WHERE run_id = ?",
            ("0" * 64, name))
        ledger.conn.commit()
        again = dict(base)
    elif mutate == "payload":
        again = {**base, "payload": {"a": 2}}
    elif mutate == "purpose":
        again = {**base, "purpose": "propose"}
    else:  # action:同键(同 attempt=空、同 provider、同 key)换 action
        again = {**base, "action_id": ids[1]}
    with pytest.raises(SearchIdentityConflict) as ei:
        ledger.register_model_request(**again)
    assert ei.value.detail["kind"] == "request_identity_conflict"
    # 零新增(仍一行;tampered_hash 案不覆盖既有行)
    n = one(ledger, "SELECT COUNT(*) FROM model_requests WHERE run_id = ?",
            (name,))
    assert n == 1
    store.close()


@pytest.mark.parametrize("case", ["unclaimed", "missing_action",
                                  "foreign_attempt", "missing_attempt",
                                  "expand_empty_attempt"])
def test_request_registration_execution_reference_closed(
        tmp_path: Path, case: str) -> None:
    """S3A-04:登记核合法 run/action/适用 attempt/执行权/生命周期 ——
    未认领/不存在 action、异属/缺失 attempt、expand 空 attempt 均拒,
    请求与真实额度预约零写入。"""
    name = f"r2m-{case}"
    store, ledger, art, policy, db, runs_root = make_run(
        tmp_path, name, {"max_real_model_requests": 2})
    _, _, hyp_a, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out_a = enqueue(ledger, name, hyp_a.hypothesis_id, task_key="tkA")
    receipt_a = ledger.claim_action(out_a["action_id"], worker_id="w1")
    attempt_a = receipt_a["attempt_refs"][0]
    # 第二个 action:claimed(decide)与 pending(expand)各备一个
    out_dec = ledger.enqueue_action(
        run_id=name, parent_path_id="p1", context_ref="ctx1",
        subject_ref="pool-1", action_kind="decide", policy_version=PV,
        payload={"task_key": "tkD"})
    ledger.claim_action(out_dec["action_id"], worker_id="w1")
    out_pend = enqueue(ledger, name, "hyp-pend", task_key="tkP")
    _, _, hyp_pend, _, _ = make_fixture(name, "p1", "k2", "ctx1")
    out_pend2 = enqueue(ledger, name, hyp_pend.hypothesis_id,
                        task_key="tkP2")

    kwargs = dict(run_id=name, action_id=out_a["action_id"],
                  attempt_id=attempt_a,
                  provider_kind=PROVIDER_KIND_REAL, request_key="rk")
    if case == "unclaimed":
        # pending action:状态闸先于 attempt 检查拒
        kwargs.update(action_id=out_pend2["action_id"], attempt_id="")
        with pytest.raises(SearchContractError) as ei:
            ledger.register_model_request(**kwargs)
        assert ei.value.detail["kind"] == "request_action_not_claimed"
    elif case == "missing_action":
        kwargs.update(action_id="sact-missing")
        with pytest.raises(SearchContractError) as ei:
            ledger.register_model_request(**kwargs)
        assert ei.value.detail["kind"] == "request_action_missing"
    elif case == "foreign_attempt":
        # 合法 claimed action + 属于别的 action 的 attempt
        kwargs.update(action_id=out_dec["action_id"], attempt_id=attempt_a)
        with pytest.raises(SearchContractError) as ei:
            ledger.register_model_request(**kwargs)
        assert ei.value.detail["kind"] == "request_attempt_binding_mismatch"
    elif case == "missing_attempt":
        kwargs.update(attempt_id="sattempt-missing")
        with pytest.raises(SearchContractError) as ei:
            ledger.register_model_request(**kwargs)
        assert ei.value.detail["kind"] == "request_attempt_missing"
    else:  # expand_empty_attempt
        kwargs.update(action_id=out_a["action_id"], attempt_id="")
        with pytest.raises(SearchContractError) as ei:
            ledger.register_model_request(**kwargs)
        assert ei.value.detail["kind"] == \
            "request_attempt_required_for_expand"
    n_req = one(ledger, "SELECT COUNT(*) FROM model_requests WHERE"
                " run_id = ?", (name,))
    n_res = one(ledger, "SELECT COUNT(*) FROM budget_reservations WHERE"
                " run_id = ? AND limit_key = 'max_real_model_requests'",
                (name,))
    assert n_req == 0 and n_res == 0  # 零写入(登记与占额都没有)
    store.close()


def test_request_state_consumption_after_execution_released(
        tmp_path: Path) -> None:
    """S3A-04:已释放执行权不可继续发送/记响应/记失败 —— 状态机
    (defer ⇒ abandoned)+ 执行引用双闸;直改状态绕过 abandoned 时
    执行引用闸仍拒(request_execution_released)。"""
    name = "r2n"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    req = ledger.register_model_request(
        run_id=name, action_id=out["action_id"],
        attempt_id=receipt["attempt_refs"][0],
        provider_kind=PROVIDER_KIND_SCRIPTED, request_key="k")
    ledger.defer_action(out["action_id"], worker_id="w1", reason="await")
    # 第一闸:请求已被 defer 置 abandoned ⇒ 状态机拒
    with pytest.raises(SearchContractError) as e1:
        ledger.record_request_sent(req["request_id"])
    assert e1.value.detail["kind"] == "request_not_resendable"
    # 第二闸:改库把状态拨回(模拟漏标)⇒ 执行引用仍拒
    ledger.conn.execute(
        "UPDATE model_requests SET status = 'registered' WHERE"
        " request_id = ?", (req["request_id"],))
    ledger.conn.commit()
    with pytest.raises(SearchContractError) as e2:
        ledger.record_request_sent(req["request_id"])
    assert e2.value.detail["kind"] == "request_execution_released"
    ledger.conn.execute(
        "UPDATE model_requests SET status = 'sent' WHERE"
        " request_id = ?", (req["request_id"],))
    ledger.conn.commit()
    with pytest.raises(SearchContractError) as e3:
        ledger.record_request_response(req["request_id"], "resp")
    assert e3.value.detail["kind"] == "request_execution_released"
    ledger.conn.execute(
        "UPDATE model_requests SET status = 'registered' WHERE"
        " request_id = ?", (req["request_id"],))
    ledger.conn.commit()
    with pytest.raises(SearchContractError) as e4:
        ledger.mark_request_failed(req["request_id"])
    assert e4.value.detail["kind"] == "request_execution_released"
    # 零成功状态写入:始终未变成 sent/responded/failed 之外的消费
    row = ledger.request(req["request_id"])
    assert row["network_request_count"] == 0  # scripted 恒 0
    store.close()


def test_request_empty_attempt_on_decide_positive_control(
        tmp_path: Path) -> None:
    """S3A-04 正控:非 expand(decide)的合法空 attempt 请求登记
    (action 驱动路径保留,不对无关 action 强加 expand attempt)。"""
    name = "r2o"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    out = ledger.enqueue_action(
        run_id=name, parent_path_id="p1", context_ref="ctx1",
        subject_ref="pool-1", action_kind="decide", policy_version=PV,
        payload={"task_key": "tkD"})
    ledger.claim_action(out["action_id"], worker_id="w1")
    req = ledger.register_model_request(
        run_id=name, action_id=out["action_id"], attempt_id="",
        provider_kind=PROVIDER_KIND_SCRIPTED, request_key="k")
    assert req["registered"] and req["network_request_count"] == 0
    ledger.record_request_sent(req["request_id"])
    assert ledger.request(req["request_id"])["status"] == "sent"
    store.close()


# ------------------------------------------------------------ S3A-05


def test_stop_report_claimed_actions_not_exhausted(tmp_path: Path) -> None:
    """S3A-05:预算有余、仅 claim 一个有效 action、无请求 ⇒ 不得
    exhausted_search;机器披露 claimed/open attempt 数量;完成后合法
    exhaustion;空 run 正控。"""
    name = "r2p"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    # 空 run 对照:合法 exhaustion
    empty = ledger.stop_report(name)
    assert empty["primary"] == "exhausted_search"
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    ledger.claim_action(out["action_id"], worker_id="w1")
    report = ledger.stop_report(name)
    assert report["primary"] != "exhausted_search"
    assert report["primary"] is None  # 未停止:仍有执行中的持久工作
    assert report["unexplored"]["claimed_actions"] == 1
    assert report["unexplored"]["open_attempts"] == 1
    # user_stop 恒支配(六原因顺序保持)
    report_u = ledger.stop_report(name, user_stop=True)
    assert report_u["primary"] == "user_stop"
    # 完成后:合法 exhaustion(claimed 0、无 pending/deferred/请求)
    ledger.complete_action(out["action_id"], worker_id="w1",
                           outcome_kind=COMMIT_KIND_OUTCOME)
    report_done = ledger.stop_report(name)
    assert report_done["primary"] == "exhausted_search"
    store.close()
