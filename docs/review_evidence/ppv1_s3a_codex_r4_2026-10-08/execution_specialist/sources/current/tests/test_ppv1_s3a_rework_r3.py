"""S3a 回修 r3 回归(Codex S3a 复审 R2 残余三组 S3A-02/03/04;ppv1-search-3)。

先固定合法与坏输入,再断言修复后的正确行为(任务书 §9.1):本文件在
直接父基线 dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03 上跑同字节时,
坏案断言按预期失败(行为红 = 修前缺口),合法控制保持绿 —— 红绿分类
见交付书;不用旧 collection 红或返回形态异常冒充行为红。

覆盖(复审报告 §4 三组残余 P1 的最低验收):
- S3A-02 完整搜索权威:预约单位/合法状态/scope-subject/主体共享
  alternatives 的行级内容、attempt 状态/hypothesis/task 同源交叉,
  在首次 complete(first consume)与 B4 恢复消费之前拒、零写账;
  done 后删必需预约/attempt 行或改坏提交记录归属/适用 attempt ⇒
  claim/complete/submit/recover 四口一致拒;附随 projection/plan
  被改坏(悬空 state 引用/非法计划状态/incomplete 缺原因)在首次
  complete 与 done 复用之前拒(同一坏载荷经公共 writer 正常首提同
  样拒 = 同源判据对照);B3 在事件提交之前先核必要引用(坏链
  0 event/commit/consume、artifact 保全);done submit 只返回真实
  已完成 event,提交异身份事件是明确冲突(不返回未存的 foreign
  event);合法同事件幂等复用正控;
- S3A-03 冻结策略消费:存储 search_limits 改 null/删 version ⇒
  读取(budget_snapshot)/claim/recover 消费前结构化拒、零执行预约
  (budget 0 不被坏恢复变默认 10);register 对用户 partial 覆盖落账
  完整装配块(装配补齐只在写入侧);合法完整往返/默认零额度/越界
  块读拒保持;
- S3A-04 请求引用:已有 row 复用对照 stored 与 incoming 的 run/
  attempt(存储行被改坏后原参数重登记 ⇒ 冲突零写入);状态口核
  run 绑定与 expand 必要 attempt(不写 sent/responded);恢复的
  pending 请求逐行同源守卫(坏引用结构化披露,不伪装普通合法
  pending、零新状态写入);合法 B2 pending/同键同内容幂等正控。

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
    SEARCH_LIMITS_VERSION,
    build_profile_identity_block,
)
from pathway_v43.pollutant.search import (  # noqa: E402
    ACTION_KIND_EXPAND_HYPOTHESIS,
    COMMIT_KIND_OUTCOME,
    PROVIDER_KIND_SCRIPTED,
    REQUEST_STATUS_REGISTERED,
    REQUEST_STATUS_SENT,
    RESERVATION_STATUS_RESERVED,
    SearchContractError,
    SearchIntegrityError,
    SearchLedger,
    SearchRecoveryError,
    SearchIdentityConflict,
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


def claim_and_submit(ledger, run, action_id):
    """认领 + 提交事件(B4 状态:事件已提交、记账未闭合)。"""
    receipt = ledger.claim_action(action_id, worker_id="w1")
    _, _, _, event, ev_args = make_fixture(run, "p1", "k1", "ctx1")
    ledger.submit_action_event(action_id, event, worker_id="w1", **ev_args)
    return receipt, event, ev_args


def refs_of(ledger, action_id):
    row = ledger.action(action_id)
    return row["budget_reservation_ref"], row["attempt_refs"]


def done_action(ledger, run, action_id):
    """完整合法完成(claim→submit→complete)并返回 (event, ev_args)。"""
    receipt = ledger.claim_action(action_id, worker_id="w1")
    _, _, _, event, ev_args = make_fixture(run, "p1", "k1", "ctx1")
    commit_search_event(ledger, action_id, event, worker_id="w1",
                        attempt_id=receipt["attempt_refs"][0],
                        task_key="tk1", **ev_args)
    assert action_status(ledger, action_id) == "done"
    return event, ev_args


# ------------------------------------------------------------ S3A-02 预约内容


@pytest.mark.parametrize("mutate_sql,kind", [
    ("UPDATE budget_reservations SET units = 0 WHERE reservation_id = ?",
     "reservation_units_invalid"),
    ("UPDATE budget_reservations SET status = 'weird' WHERE"
     " reservation_id = ?", "reservation_status_unknown"),
    ("UPDATE budget_reservations SET scope = 'evil-scope' WHERE"
     " reservation_id = ?", "reservation_scope_subject_mismatch"),
])
def test_first_complete_reservation_content_refused(
        tmp_path: Path, mutate_sql: str, kind: str) -> None:
    """S3A-02 r3:合法事件已提交(B4 状态)后改坏预约行内容(单位 0/
    未知状态/错 scope)⇒ 首次 complete 在写 done/commit/consume 之前
    结构化拒(零提交记录;已执行但 used=0 的缺口关闭)。"""
    name = f"r3a-res-{kind}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    _, event, _ = claim_and_submit(ledger, name, out["action_id"])
    res_refs, _ = refs_of(ledger, out["action_id"])
    # 改坏本 action 的总 action 预约(scope 期望为空串)
    total_rid = [r for r in res_refs
                 if one(ledger, "SELECT limit_key FROM budget_reservations"
                        " WHERE reservation_id = ?", (r,))
                 == "max_total_search_actions"][0]
    ledger.conn.execute(mutate_sql, (total_rid,))
    ledger.conn.commit()
    with pytest.raises(SearchIntegrityError) as ei:
        ledger.complete_action(out["action_id"], worker_id="w1",
                               event_id=event.event_id)
    assert ei.value.detail["kind"] == kind
    # 零写账:无提交记录、action 仍 claimed、事件未被重复
    assert action_status(ledger, out["action_id"]) == "claimed"
    assert one(ledger, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == 0
    assert ledger.store.counts()["events"] == 1
    store.close()


def test_first_complete_alternative_subject_content_refused(
        tmp_path: Path) -> None:
    """S3A-02 r3:主体共享 alternatives 预约的 subject 被改坏(不再等
    于本 action attempt 的 hypothesis)⇒ 内容判据拒(共享行合法语义
    仍按 scope=parent+subject=attempt hypothesis 识别,正控另测)。"""
    name = "r3a-alt-subject"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    _, event, _ = claim_and_submit(ledger, name, out["action_id"])
    res_refs, _ = refs_of(ledger, out["action_id"])
    alt_rid = [r for r in res_refs
               if one(ledger, "SELECT limit_key FROM budget_reservations"
                      " WHERE reservation_id = ?", (r,))
               == "max_alternative_hypotheses_per_parent"][0]
    ledger.conn.execute(
        "UPDATE budget_reservations SET subject = 'hyp-evil' WHERE"
        " reservation_id = ?", (alt_rid,))
    ledger.conn.commit()
    with pytest.raises(SearchIntegrityError) as ei:
        ledger.complete_action(out["action_id"], worker_id="w1",
                               event_id=event.event_id)
    assert ei.value.detail["kind"] == "reservation_scope_subject_mismatch"
    assert one(ledger, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == 0
    assert action_status(ledger, out["action_id"]) == "claimed"
    store.close()


@pytest.mark.parametrize("mutate_sql,kind", [
    ("UPDATE search_attempts SET status = 'abandoned' WHERE"
     " expansion_attempt_id = ?", "attempt_status_not_open_under_claim"),
    ("UPDATE search_attempts SET hypothesis_id = 'hyp-evil' WHERE"
     " expansion_attempt_id = ?", "reservation_scope_subject_mismatch"),
    ("UPDATE search_attempts SET task_key = 'tk-evil' WHERE"
     " expansion_attempt_id = ?", "attempt_task_key_mismatch"),
])
def test_first_complete_attempt_content_refused(
        tmp_path: Path, mutate_sql: str, kind: str) -> None:
    """S3A-02 r3:改坏 attempt 行(abandoned/异 hypothesis/异 task_key)
    ⇒ 首次 complete 之前拒(状态与 action 不匹配/交叉核失败)。"""
    name = f"r3a-att-{kind}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    _, event, _ = claim_and_submit(ledger, name, out["action_id"])
    _, att_refs = refs_of(ledger, out["action_id"])
    ledger.conn.execute(mutate_sql, (att_refs[0],))
    ledger.conn.commit()
    with pytest.raises(SearchIntegrityError) as ei:
        ledger.complete_action(out["action_id"], worker_id="w1",
                               event_id=event.event_id)
    assert ei.value.detail["kind"] == kind
    assert one(ledger, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == 0
    assert action_status(ledger, out["action_id"]) == "claimed"
    store.close()


@pytest.mark.parametrize("case", ["reservation_units", "attempt_status"])
def test_b4_recovery_content_refused(tmp_path: Path, case: str) -> None:
    """S3A-02 r3:B4 恢复(事件已提交、记账未闭合)同样先消费内容判据
    —— 坏预约/attempt 行在补账之前拒,零补账。"""
    name = f"r3a-b4-{case}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    _, event, _ = claim_and_submit(ledger, name, out["action_id"])
    res_refs, att_refs = refs_of(ledger, out["action_id"])
    if case == "reservation_units":
        ledger.conn.execute(
            "UPDATE budget_reservations SET units = 0 WHERE"
            " reservation_id = ?", (res_refs[0],))
    else:
        ledger.conn.execute(
            "UPDATE search_attempts SET status = 'abandoned' WHERE"
            " expansion_attempt_id = ?", (att_refs[0],))
    ledger.conn.commit()
    store.close()

    ledger2 = fresh_ledger(db, runs_root, name)
    with pytest.raises(SearchIntegrityError):
        ledger2.recover_run(name)
    assert action_status(ledger2, out["action_id"]) == "claimed"
    assert one(ledger2, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == 0
    assert ledger2.store.counts()["events"] == 1
    ledger2.store.close()


# -------------------------------------------------- S3A-02 done 四入口一致


DONE_ENTRIES = ("claim", "complete", "submit", "recover")


def _done_entry_call(ledger, entry, action_id, event, ev_args):
    if entry == "claim":
        ledger.claim_action(action_id, worker_id="w-other")
    elif entry == "complete":
        ledger.complete_action(action_id, worker_id="w1",
                               event_id=event.event_id)
    elif entry == "submit":
        ledger.submit_action_event(action_id, event, worker_id="w1",
                                   **ev_args)
    else:
        ledger.recover_run(ledger.run_id)


@pytest.mark.parametrize("entry", DONE_ENTRIES)
@pytest.mark.parametrize("drop", ["reservation", "attempt"])
def test_done_four_entries_deleted_reference_rows_refused(
        tmp_path: Path, entry: str, drop: str) -> None:
    """S3A-02 r3:done 后删必需预约/attempt 行 ⇒ claim/complete/submit/
    recover 四口一致拒(不能一个入口能拒就当全入口闭合)。"""
    name = f"r3a-done-{drop}-{entry}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    event, ev_args = done_action(ledger, name, out["action_id"])
    res_refs, att_refs = refs_of(ledger, out["action_id"])
    if drop == "reservation":
        ledger.conn.execute(
            "DELETE FROM budget_reservations WHERE reservation_id = ?",
            (res_refs[0],))
    else:
        ledger.conn.execute(
            "DELETE FROM search_attempts WHERE expansion_attempt_id = ?",
            (att_refs[0],))
    ledger.conn.commit()
    store.close()

    ledger2 = fresh_ledger(db, runs_root, name)
    with pytest.raises(SearchIntegrityError) as ei:
        _done_entry_call(ledger2, entry, out["action_id"], event, ev_args)
    expected_kinds = ["reservation_row_missing"] if drop == "reservation" \
        else ["attempt_row_missing",
              "commit_record_attempt_binding_mismatch"]
    expected_kinds.append("done_without_commit_record")
    assert ei.value.detail["kind"] in expected_kinds
    # 复用拒绝零写入:提交记录数不变、action 保持 done、事件不重复
    assert one(ledger2, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == 1
    assert action_status(ledger2, out["action_id"]) == "done"
    assert ledger2.store.counts()["events"] == 1
    ledger2.store.close()


@pytest.mark.parametrize("entry", DONE_ENTRIES)
@pytest.mark.parametrize("mutate", ["commit_attempt_missing",
                                    "commit_run_foreign"])
def test_done_four_entries_commit_record_corruption_refused(
        tmp_path: Path, entry: str, mutate: str) -> None:
    """S3A-02 r3:改坏提交记录(commit.attempt_id 不存在 / commit.run
    错属)⇒ 四口一致拒(r2 仅 recover 单口拒 run 错属)。"""
    name = f"r3a-commit-{mutate}-{entry}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    event, ev_args = done_action(ledger, name, out["action_id"])
    if mutate == "commit_attempt_missing":
        ledger.conn.execute(
            "UPDATE search_commit_records SET attempt_id = 'sattempt-x'"
            " WHERE action_id = ?", (out["action_id"],))
    else:
        ledger.conn.execute(
            "UPDATE search_commit_records SET run_id = 'other-run'"
            " WHERE action_id = ?", (out["action_id"],))
    ledger.conn.commit()
    store.close()

    ledger2 = fresh_ledger(db, runs_root, name)
    with pytest.raises(SearchIntegrityError):
        _done_entry_call(ledger2, entry, out["action_id"], event, ev_args)
    # 复用拒绝零写入:提交记录仍在(按 action 计;run 列被改的案不能
    # 按 run 计数)、action 保持 done
    assert one(ledger2, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " action_id = ?", (out["action_id"],)) == 1
    assert action_status(ledger2, out["action_id"]) == "done"
    ledger2.store.close()


# ------------------------------------------------ S3A-02 附随 projection/plan


def _tamper_attached(ledger, event_id, kind):
    """改坏已存附随投影/计划载荷(保留行,只改内容)。"""
    if kind == "projection_dangling_ref":
        row = ledger.conn.execute(
            "SELECT payload FROM report_projections WHERE event_id = ?",
            (event_id,)).fetchone()
        doc = json.loads(row["payload"])
        doc["product_ranks"][0]["state_ref"] = "state-nonexistent"
        target, table = "report_projections", doc
    elif kind == "plan_bad_status":
        row = ledger.conn.execute(
            "SELECT payload FROM expansion_plans WHERE event_id = ?",
            (event_id,)).fetchone()
        doc = json.loads(row["payload"])
        doc["entries"][0]["status"] = "bogus_status"
        target, table = "expansion_plans", doc
    else:  # plan_incomplete_no_reason
        row = ledger.conn.execute(
            "SELECT payload FROM expansion_plans WHERE event_id = ?",
            (event_id,)).fetchone()
        doc = json.loads(row["payload"])
        doc["plan_status"] = "incomplete"
        target, table = "expansion_plans", doc
    ledger.conn.execute(
        f"UPDATE {target} SET payload = ? WHERE event_id = ?",
        (json.dumps(table, ensure_ascii=False, sort_keys=True), event_id))
    ledger.conn.commit()


ATTACHED_KINDS = ("projection_dangling_ref", "plan_bad_status",
                  "plan_incomplete_no_reason")


@pytest.mark.parametrize("kind", ATTACHED_KINDS)
def test_attached_projection_plan_content_refused_before_consume(
        tmp_path: Path, kind: str) -> None:
    """S3A-02 r3:存储附随 projection/plan 被改坏(悬空 state 引用/
    非法计划状态/incomplete 缺原因)⇒ 首次 complete 在写 done/commit
    之前拒 —— 附随内容按首提同一判据核验,不能从当前坏行取出再自比较
    (存储行存在 + 自比较相等不是完整性证书)。"""
    name = f"r3a-attached-{kind}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    _, event, _ = claim_and_submit(ledger, name, out["action_id"])
    _tamper_attached(ledger, event.event_id, kind)
    with pytest.raises(SearchIntegrityError) as ei:
        ledger.complete_action(out["action_id"], worker_id="w1",
                               event_id=event.event_id)
    assert ei.value.detail["kind"] == "event_ledger_authority_failed"
    assert action_status(ledger, out["action_id"]) == "claimed"
    assert one(ledger, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == 0
    store.close()


@pytest.mark.parametrize("kind", ATTACHED_KINDS)
def test_attached_bad_payload_also_refused_at_normal_first_submit(
        tmp_path: Path, kind: str) -> None:
    """S3A-02 r3 同源判据对照:同一坏 projection/plan 载荷经公共
    writer **正常首提**同样被拒(证明权威核验消费的是首提判据本身,
    不是另一套规则;两侧行为一致)。"""
    name = f"r3a-attached-src-{kind}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, _, event, ev_args = make_fixture(name, "p1", "k1", "ctx1")
    bad_projection = json.loads(json.dumps(
        ev_args["report_projection"]))
    bad_plan = json.loads(json.dumps(ev_args["expansion_plan"]))
    if kind == "projection_dangling_ref":
        bad_projection["product_ranks"][0]["state_ref"] = \
            "state-nonexistent"
    elif kind == "plan_bad_status":
        bad_plan["entries"][0]["status"] = "bogus_status"
    else:
        bad_plan["plan_status"] = "incomplete"
    with pytest.raises(Exception) as ei:  # noqa: BLE001
        ledger.store.submit_event(
            event, report_projection=bad_projection,
            expansion_plan=bad_plan, states=ev_args["states"],
            hypothesis_dict=ev_args["hypothesis_dict"])
    assert ledger.store.counts()["events"] == 0  # 首提零写入
    store.close()


def test_done_reuse_attached_content_refused(tmp_path: Path) -> None:
    """S3A-02 r3:done 复用入口(claim/submit)对改坏的附随投影同样
    在返回成功之前拒(完整权威含附随内容,零写入)。"""
    name = "r3a-attached-done"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    event, ev_args = done_action(ledger, name, out["action_id"])
    _tamper_attached(ledger, event.event_id, "projection_dangling_ref")
    store.close()

    ledger2 = fresh_ledger(db, runs_root, name)
    with pytest.raises(SearchIntegrityError):
        ledger2.claim_action(out["action_id"], worker_id="w-other")
    with pytest.raises(SearchIntegrityError):
        ledger2.submit_action_event(out["action_id"], event,
                                    worker_id="w1", **ev_args)
    assert action_status(ledger2, out["action_id"]) == "done"
    assert ledger2.store.counts()["events"] == 1
    ledger2.store.close()


# ------------------------------------------------------------ S3A-02 B3 前置


@pytest.mark.parametrize("drop", ["reservation", "attempt"])
def test_b3_reference_precheck_before_event_write(tmp_path: Path,
                                                  drop: str) -> None:
    """S3A-02 r3:B3(合法 bundle、事件未提交)恢复在**事件提交之前**
    先核必要 attempt/预约引用 —— 删行 ⇒ 0 event/commit/consume、
    artifact 保全、action 仍 claimed(不能先写 event 再靠 complete
    的写事务拒绝"事后"发现)。"""
    name = f"r3a-b3-{drop}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    _, _, _, event, ev_args = make_fixture(name, "p1", "k1", "ctx1")
    ledger.write_commit_bundle(
        action_id=out["action_id"],
        attempt_id=receipt["attempt_refs"][0], event=event,
        task_key="tk1", **ev_args)
    path = runs_root / name / "results" / "tk1" / \
        "search_commit_bundle.json"
    before = path.read_bytes()
    res_refs, att_refs = refs_of(ledger, out["action_id"])
    if drop == "reservation":
        ledger.conn.execute(
            "DELETE FROM budget_reservations WHERE reservation_id = ?",
            (res_refs[0],))
    else:
        ledger.conn.execute(
            "DELETE FROM search_attempts WHERE expansion_attempt_id = ?",
            (att_refs[0],))
    ledger.conn.commit()
    store.close()

    ledger2 = fresh_ledger(db, runs_root, name)
    with pytest.raises(SearchIntegrityError) as ei:
        ledger2.recover_run(name)
    assert ei.value.detail["kind"] in (
        "reservation_row_missing" if drop == "reservation"
        else "attempt_row_missing", "claimed_action_reservation_missing",
        "claimed_action_attempt_missing")
    # 坏链 0 event/commit/consume;artifact 保全;action 仍 claimed
    assert ledger2.store.counts()["events"] == 0
    assert one(ledger2, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == 0
    assert action_status(ledger2, out["action_id"]) == "claimed"
    assert path.read_bytes() == before
    ledger2.store.close()


# ------------------------------------------------ S3A-02 done submit 返回语义


def test_done_submit_foreign_event_explicit_conflict(tmp_path: Path) -> None:
    """S3A-02 r3:合法 done A 后提交有效异 parent 事件 B ⇒ 明确冲突
    (created=False 不再返回未存储的 B 当完成引用);B 不入账、零表
    变化、commit 仍指 A;同 A 幂等重提交返回真实已完成 event。"""
    name = "r3a-done-foreign"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp_a, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp_a.hypothesis_id)
    event_a, ev_a = done_action(ledger, name, out["action_id"])
    # 有效异 parent 事件 B(身份全合法,仅 parent 不同)
    _, _, hyp_b, event_b, ev_b = make_fixture(name, "p2", "k1", "ctx1")
    with pytest.raises(SearchContractError) as ei:
        ledger.submit_action_event(out["action_id"], event_b,
                                   worker_id="w1", **ev_b)
    assert ei.value.detail["kind"] == "event_identity_not_frozen_to_action"
    assert ei.value.detail["completed_event_id"] == event_a.event_id
    # B 不入账;零表变化;commit 仍指 A
    assert ledger.store.counts()["events"] == 1
    assert one(ledger, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == 1
    row = ledger.conn.execute(
        "SELECT event_id FROM search_commit_records WHERE action_id = ?",
        (out["action_id"],)).fetchone()
    assert row["event_id"] == event_a.event_id
    # 同 A 幂等重提交:返回真实已完成 event(created=False)
    again = ledger.submit_action_event(out["action_id"], event_a,
                                       worker_id="w1", **ev_a)
    assert again["created"] is False
    assert again["reason"] == "already_completed"
    assert again["event_id"] == event_a.event_id
    assert ledger.store.counts()["events"] == 1
    store.close()


# ------------------------------------------------------------ S3A-03 冻结策略


@pytest.mark.parametrize("mutate", ["null_limits", "drop_version"])
def test_frozen_policy_corrupt_rejected_before_any_execution(
        tmp_path: Path, mutate: str) -> None:
    """S3A-03 r3:已登记完整块(budget 总额度 0)的存储 search_limits
    被改成 null/删 version ⇒ 读取(budget_snapshot)/claim/recover 在
    消费之前结构化拒、零执行预约 —— 装配补默认只允许在注册写入侧,
    budget 0 不被坏恢复变默认 10;不靠传 expected policy 弥补缺口。"""
    name = f"r3b-{mutate}"
    store, ledger, art, policy, db, runs_root = make_run(
        tmp_path, name, {"max_total_search_actions": 0})
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    # 先入队(入队本身读取 _limits;破坏后入队会先在入队口拒)
    out = enqueue(ledger, name, hyp.hypothesis_id, task_key="tk2")
    # 读取消费(budget_snapshot/_limits)
    stored = json.loads(ledger.conn.execute(
        "SELECT policy_block FROM search_runs WHERE run_id = ?",
        (name,)).fetchone()[0])
    limits = stored["search_limits"]
    if mutate == "null_limits":
        stored["search_limits"] = None
    else:
        stored["search_limits"] = {k: v for k, v in limits.items()
                                   if k != "version"}
    ledger.conn.execute(
        "UPDATE search_runs SET policy_block = ? WHERE run_id = ?",
        (json.dumps(stored, ensure_ascii=False, sort_keys=True), name))
    ledger.conn.commit()
    with pytest.raises(SearchRecoveryError) as eb:
        ledger.budget_snapshot(name)
    assert eb.value.detail["kind"] == "search_policy_block_corrupt"
    # claim 消费:新 action 认领被拒(零预约;不是默认 10 放行)
    n_res = one(ledger, "SELECT COUNT(*) FROM budget_reservations WHERE"
                " run_id = ?", (name,))
    with pytest.raises(SearchRecoveryError) as ec:
        ledger.claim_action(out["action_id"], worker_id="w1")
    assert ec.value.detail["kind"] == "search_policy_block_corrupt"
    assert one(ledger, "SELECT COUNT(*) FROM budget_reservations WHERE"
               " run_id = ?", (name,)) == n_res  # 零新预约
    assert action_status(ledger, out["action_id"]) == "pending"
    store.close()

    # 恢复消费:无 expected 与传原冻结块都拒(公共恢复缺口闭合)
    ledger2 = fresh_ledger(db, runs_root, name)
    with pytest.raises(SearchRecoveryError) as er:
        ledger2.recover_run(name)
    assert er.value.detail["kind"] == "search_policy_block_corrupt"
    with pytest.raises(SearchRecoveryError) as er2:
        ledger2.recover_run(name, policy_block=policy)
    assert er2.value.detail["kind"] in ("search_policy_block_corrupt",
                                        "search_policy_identity_mismatch")
    ledger2.store.close()


def test_frozen_policy_out_of_range_rejected_on_read(tmp_path: Path) -> None:
    """S3A-03 r3(保持):存储块越界值在读取消费前拒(r2 已闭合的
    越界类不回退)。"""
    name = "r3b-range"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    stored = json.loads(ledger.conn.execute(
        "SELECT policy_block FROM search_runs WHERE run_id = ?",
        (name,)).fetchone()[0])
    stored["search_limits"]["max_total_search_actions"] = 1001
    ledger.conn.execute(
        "UPDATE search_runs SET policy_block = ? WHERE run_id = ?",
        (json.dumps(stored, ensure_ascii=False, sort_keys=True), name))
    ledger.conn.commit()
    with pytest.raises(SearchRecoveryError) as ei:
        ledger.budget_snapshot(name)
    assert ei.value.detail["kind"] == "search_policy_block_corrupt"
    store.close()


def test_register_partial_override_stored_complete(tmp_path: Path) -> None:
    """S3A-03 r3:register 对用户 partial 覆盖(带版本、缺预算键)合法
    补齐为完整装配块落账(装配语义只在写入侧);读取/恢复按完整块
    消费;同 effective 策略幂等、异 effective 策略冲突。"""
    name = "r3b-partial"
    store = PollutantPathwayStore(tmp_path / f"{name}.sqlite")
    ledger = SearchLedger(store, None, name)
    partial = {"search_limits": {
        "version": SEARCH_LIMITS_VERSION,
        "max_total_search_actions": 3}}
    ledger.register_search_run(name, partial)
    stored = ledger.search_policy_block(name)
    assert stored["search_limits"]["max_total_search_actions"] == 3
    assert len(stored["search_limits"]) == 11  # version + 十键完整
    # 同 partial 再注册:幂等(同 effective 策略)
    ledger.register_search_run(name, partial)
    # 等价完整块注册:同 effective 策略 ⇒ 幂等
    full = {"search_limits": ledger._limits(name)}
    ledger.register_search_run(name, full)
    # 异 effective 策略 ⇒ 冲突
    other = {"search_limits": {
        "version": SEARCH_LIMITS_VERSION,
        "max_total_search_actions": 4}}
    with pytest.raises(SearchIdentityConflict) as ei:
        ledger.register_search_run(name, other)
    assert ei.value.detail["kind"] == "search_policy_conflict"
    # 读取消费正常(完整块)
    assert ledger._limits(name)["max_total_search_actions"] == 3
    store.close()


def test_frozen_policy_legal_roundtrip_and_zero_budget_control(
        tmp_path: Path) -> None:
    """S3A-03 r3 正控:合法完整块注册→读取往返一致;总额度 0 只拒
    确实消费该资源的认领(注册零预约)。"""
    name = "r3b-ok"
    store, ledger, art, policy, db, runs_root = make_run(
        tmp_path, name, {"max_total_search_actions": 0})
    assert ledger._limits(name)["max_total_search_actions"] == 0
    assert ledger.search_policy_block(name) == policy
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    with pytest.raises(Exception) as ei:  # noqa: BLE001
        ledger.claim_action(out["action_id"], worker_id="w1")
    assert ei.value.detail["limit_key"] == "max_total_search_actions"
    assert one(ledger, "SELECT COUNT(*) FROM budget_reservations WHERE"
               " run_id = ?", (name,)) == 0
    ledger.recover_run(name, policy_block=policy)  # 同块恢复通过
    store.close()


# ------------------------------------------------------------ S3A-04 请求


def _claimed_action(ledger, run, subject="pool-1", kind="decide",
                    task_key="tkD"):
    out = ledger.enqueue_action(
        run_id=run, parent_path_id="p1", context_ref="ctx1",
        subject_ref=subject, action_kind=kind, policy_version=PV,
        payload={"task_key": task_key})
    ledger.claim_action(out["action_id"], worker_id="w1")
    return out


@pytest.mark.parametrize("mutate_sql", [
    "UPDATE model_requests SET run_id = 'other-run' WHERE request_id = ?",
    "UPDATE model_requests SET attempt_id = 'sattempt-evil' WHERE"
    " request_id = ?",
])
def test_request_existing_row_stored_identity_corruption_conflict(
        tmp_path: Path, mutate_sql: str) -> None:
    """S3A-04 r3:存储请求行的 run/attempt 被改坏后,用原正确参数重复
    登记同键 ⇒ 身份冲突零写入(不能"键相同"当幂等证书放行 unchanged)。"""
    name = "r3c-reuse"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    attempt = receipt["attempt_refs"][0]
    base = dict(run_id=name, action_id=out["action_id"],
                attempt_id=attempt, provider_kind=PROVIDER_KIND_SCRIPTED,
                request_key="rk", purpose="rank", payload={"a": 1})
    req = ledger.register_model_request(**base)
    ledger.conn.execute(mutate_sql, (req["request_id"],))
    ledger.conn.commit()
    with pytest.raises(SearchIdentityConflict) as ei:
        ledger.register_model_request(**base)
    assert ei.value.detail["kind"] == "request_identity_conflict"
    conflicts = ei.value.detail["conflicts"]
    assert "run_id" in conflicts or "attempt_id" in conflicts
    # 零新增(仍一行,坏行未被覆盖/修复;按 request 计 —— run 列被改
    # 的案不能按 run 计数)
    assert one(ledger, "SELECT COUNT(*) FROM model_requests WHERE"
               " request_id = ?", (req["request_id"],)) == 1
    store.close()


@pytest.mark.parametrize("mutate_sql,kind", [
    ("UPDATE model_requests SET run_id = 'other-run' WHERE"
     " request_id = ?", "request_run_binding_mismatch"),
    ("UPDATE model_requests SET attempt_id = '' WHERE"
     " request_id = ?", "request_attempt_required_for_expand"),
])
def test_request_state_consumption_reference_corruption_refused(
        tmp_path: Path, mutate_sql: str, kind: str) -> None:
    """S3A-04 r3:状态口(发送/响应/失败)核 run 绑定与 expand 必要
    attempt —— 存储行 run 被改坏成 foreign run / attempt 被清空 ⇒
    结构化拒,不写 sent/responded/failed(不把已损坏的请求权威当合法
    执行引用)。"""
    name = f"r3c-state-{kind}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    req = ledger.register_model_request(
        run_id=name, action_id=out["action_id"],
        attempt_id=receipt["attempt_refs"][0],
        provider_kind=PROVIDER_KIND_SCRIPTED, request_key="rk")
    ledger.conn.execute(mutate_sql, (req["request_id"],))
    ledger.conn.commit()
    # 发送口
    with pytest.raises(SearchContractError) as e1:
        ledger.record_request_sent(req["request_id"])
    assert e1.value.detail["kind"] == kind
    assert ledger.request(req["request_id"])["status"] == \
        REQUEST_STATUS_REGISTERED
    # 拨到 sent 后响应口同样拒
    ledger.conn.execute(
        "UPDATE model_requests SET status = 'sent' WHERE request_id = ?",
        (req["request_id"],))
    ledger.conn.commit()
    with pytest.raises(SearchContractError) as e2:
        ledger.record_request_response(req["request_id"], "resp")
    assert e2.value.detail["kind"] == kind
    store.close()


@pytest.mark.parametrize("case", ["action_deleted", "action_completed"])
def test_recover_pending_requests_reference_guard(tmp_path: Path,
                                                  case: str) -> None:
    """S3A-04 r3:恢复的 pending 请求逐行同源守卫 —— 请求引用的 action
    被删(缺权威)/ action 已完成(执行权已失效的悬空请求)⇒ 结构化
    完整性披露(不伪装普通合法 pending,不新状态成功写入,不猜补);
    请求行原样保全。"""
    name = f"r3c-pending-{case}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    req = ledger.register_model_request(
        run_id=name, action_id=out["action_id"],
        attempt_id=receipt["attempt_refs"][0],
        provider_kind=PROVIDER_KIND_SCRIPTED, request_key="rk")
    if case == "action_deleted":
        ledger.conn.execute(
            "DELETE FROM search_actions WHERE action_id = ?",
            (out["action_id"],))
    else:
        # 悬空:请求未发送但 action 已完成(执行权已释放)
        ledger.complete_action(out["action_id"], worker_id="w1",
                               outcome_kind=COMMIT_KIND_OUTCOME)
    ledger.conn.commit()
    store.close()

    ledger2 = fresh_ledger(db, runs_root, name)
    report = ledger2.recover_run(name)
    pending = report["pending_requests"]
    assert len(pending) == 1
    entry = pending[0]
    assert entry["request_id"] == req["request_id"]
    assert "reference_integrity" in entry
    assert entry["reference_integrity"]["kind"] in (
        "request_action_missing" if case == "action_deleted"
        else "request_execution_released")
    assert "不伪装普通合法 pending" in entry["note"]
    # 零新状态写入:请求行仍 registered、未猜补/未改
    row = ledger2.request(req["request_id"])
    assert row["status"] == REQUEST_STATUS_REGISTERED
    assert one(ledger2, "SELECT COUNT(*) FROM model_requests WHERE"
               " request_id = ?", (req["request_id"],)) == 1
    ledger2.store.close()


def test_request_legal_controls_kept(tmp_path: Path) -> None:
    """S3A-04 r3 正控:合法 B2 pending(claim 中、attempt open)照常
    暴露 pending/unknown;同键同内容幂等 unchanged;非 expand 合法空
    attempt 登记并发送(scripted 网络 0)。"""
    name = "r3c-ok"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    base = dict(run_id=name, action_id=out["action_id"],
                attempt_id=receipt["attempt_refs"][0],
                provider_kind=PROVIDER_KIND_SCRIPTED, request_key="rk")
    req = ledger.register_model_request(**base)
    again = ledger.register_model_request(**base)
    assert again["registered"] is False and again["unchanged"]
    report = ledger.recover_run(name)
    pending = report["pending_requests"]
    assert len(pending) == 1
    assert "不默发第二请求" in pending[0]["note"]
    assert "reference_integrity" not in pending[0]
    # 非 expand 合法空 attempt + 发送(scripted 恒 0)
    dec = _claimed_action(ledger, name)
    req2 = ledger.register_model_request(
        run_id=name, action_id=dec["action_id"], attempt_id="",
        provider_kind=PROVIDER_KIND_SCRIPTED, request_key="rk2")
    ledger.record_request_sent(req2["request_id"])
    assert ledger.request(req2["request_id"])["status"] == \
        REQUEST_STATUS_SENT
    assert ledger.request(req2["request_id"])["network_request_count"] == 0
    store.close()


# ------------------------------------------------------------ S3A-02 正控


def test_legal_completion_positive_control(tmp_path: Path) -> None:
    """S3A-02 r3 正控:合法链(claim→submit→complete→done 复用)在新
    内容判据下全部通过 —— 预约 units=1/状态合法、attempt open→
    recorded、共享 alternatives 主体识别、done 四口复用合法;不能把
    存量正确行为改成全面拒绝。"""
    name = "r3a-ok"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    event, ev_args = done_action(ledger, name, out["action_id"])
    # done 四口合法复用
    receipt = ledger.claim_action(out["action_id"], worker_id="w-other")
    assert receipt["reason"] == "already_completed"
    late = ledger.complete_action(out["action_id"], worker_id="w1",
                                  event_id=event.event_id)
    assert late["completed"] is False and late["unchanged"]
    again = ledger.submit_action_event(out["action_id"], event,
                                       worker_id="w1", **ev_args)
    assert again["created"] is False
    assert again["event_id"] == event.event_id
    report = ledger.recover_run(name)
    entry = [a for a in report["actions"]
             if a["action_id"] == out["action_id"]][0]
    assert entry["boundary"] == "B4_verified"
    assert entry["disposition"] == "done_commit_verified"
    # 预算恰好 consume 一次
    rows = ledger.conn.execute(
        "SELECT status FROM budget_reservations WHERE action_id = ? AND"
        " limit_key = 'max_total_search_actions'",
        (out["action_id"],)).fetchall()
    assert rows[0]["status"] == "consumed"
    snap = ledger.budget_snapshot(name)
    assert snap["run_level"]["max_total_search_actions"]["used"] == 1
    store.close()


def test_shared_alternative_reservation_positive_control(
        tmp_path: Path) -> None:
    """S3A-02 r3 正控:主体共享 alternative 预约(同 hypothesis 不同
    revision 的两个 action 引用同一行)在行级内容判据下合法 —— 共享
    行 scope=parent、subject=attempt hypothesis,不要求共享行由本
    action 创建;两个 action 都可完成。"""
    name = "r3a-shared"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    run = name
    _, _, hyp, event, ev_args = make_fixture(run, "p1", "k1", "ctx1")
    out1 = enqueue(ledger, run, hyp.hypothesis_id, revision=0,
                   task_key="tk1")
    receipt1 = ledger.claim_action(out1["action_id"], worker_id="w1")
    commit_search_event(ledger, out1["action_id"], event, worker_id="w1",
                        attempt_id=receipt1["attempt_refs"][0],
                        task_key="tk1", **ev_args)
    # 第二个 action:同 hypothesis、revision 前进(共享 alt 预约行)
    out2 = enqueue(ledger, run, hyp.hypothesis_id, revision=1,
                   task_key="tk2")
    receipt2 = ledger.claim_action(out2["action_id"], worker_id="w1")
    alt = [r for r in ledger.action(out2["action_id"])
           ["budget_reservation_ref"]
           if one(ledger, "SELECT limit_key FROM budget_reservations WHERE"
                  " reservation_id = ?", (r,))
           == "max_alternative_hypotheses_per_parent"][0]
    assert one(ledger, "SELECT action_id FROM budget_reservations WHERE"
               " reservation_id = ?", (alt,)) == out1["action_id"]  # 共享
    ledger.submit_action_event(out2["action_id"], event, worker_id="w1",
                               **ev_args)
    ledger.complete_action(out2["action_id"], worker_id="w1",
                           event_id=event.event_id)
    assert action_status(ledger, out2["action_id"]) == "done"
    snap = ledger.budget_snapshot(run)
    assert snap["scoped"][
        "max_alternative_hypotheses_per_parent"]["p1"]["used"] == 1
    assert snap["run_level"]["max_total_search_actions"]["used"] == 2
    store.close()
