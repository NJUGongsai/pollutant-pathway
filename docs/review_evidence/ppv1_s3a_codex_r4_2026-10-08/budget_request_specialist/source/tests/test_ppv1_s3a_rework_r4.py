"""S3a 回修 r4 回归(Codex S3a 复审 R3 残余三组 S3A-02/03/04;ppv1-search-4)。

先固定合法与坏输入,再断言修复后的正确行为(任务书 §9.1):本文件在
直接父基线 41d0cd55f3def050a62325f00235cf22da302d2e 上跑同字节时,
坏案断言按预期失败(行为红 = 修前缺口),合法控制保持绿 —— 红绿分类
见交付书;不用旧 collection 红或返回形态异常冒充行为红。

覆盖(复审 R3 报告 §4 三组残余 P1 的最低验收,§8 复跑矩阵):
- S3A-02 必要预约集合完整性:本审 9 入口(first complete/B4/B3 事件
  前/B1/defer/done 四口=claim/complete/submit/recover)× 3 必要预约
  (总 action/alternatives/attempts)× 仅删 ref/删 ref+row,共 54 坏
  分案全部结构化拒 —— 剩余清单非空不能代替必要集合齐全;B3 零
  event 新增、artifact 保全;done 不漏结算/不伪称 verified;9 入口
  合法对照保持;上限 1 双链(删总额度 ref+row 后第一次 complete
  拒、不再 used0/commits2);cache_hit retrieve 不强加检索预约
  (正控);scenario_transition 的必要 transitions 预约同规则;
- S3A-03 请求状态口接冻结策略守卫:sent/response/failed 写状态前
  消费同一严格冻结块校验 —— null/缺 version/四坏值(bool/越界/
  未知键/负数)× 3 状态口先结构化拒(search_policy_block_corrupt)
  且无成功状态变化;合法策略下状态机往返(scripted 网络 0、真实
  额度不重复扣)保持;
- S3A-04 非法来源状态不能改记合法 failed:mark_request_failed 正面
  限定 registered/sent 来源(枚举外未知状态结构化拒并保全);sent/
  response 口对未知状态照旧拒;register 同键复用不把坏状态当合法
  幂等 unchanged 返回;recover 对 run 范围枚举外行结构化披露(不改
  状态、不伪装合法 pending);合法 registered/sent→failed、终态不
  重发、显式 retry 新键、真实失败占额不释放保持。

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
    ACTION_KIND_RETRIEVE,
    ACTION_KIND_SCENARIO_TRANSITION,
    COMMIT_KIND_EVENT,
    COMMIT_KIND_OUTCOME,
    PROVIDER_KIND_REAL,
    PROVIDER_KIND_SCRIPTED,
    REQUEST_STATUS_FAILED,
    REQUEST_STATUS_REGISTERED,
    REQUEST_STATUS_RESPONDED,
    REQUEST_STATUS_SENT,
    SearchBudgetExhausted,
    SearchContractError,
    SearchIntegrityError,
    SearchLedger,
    SearchRecoveryError,
    commit_search_event,
    search_policy_version,
)
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402

PV = search_policy_version()

# ---- 本审 9 入口 × 2 模式 × 3 必要预约(复审 §4.1 反例矩阵) ----
PHASES = ("first_complete", "B4_recover", "B1_recover", "B3_recover",
          "done_recover", "done_claim", "done_complete", "done_submit",
          "defer")
MUTATIONS = ("remove_ref_only", "remove_ref_and_row")
NECESSARY_KEYS = ("max_total_search_actions",
                  "max_alternative_hypotheses_per_parent",
                  "max_attempts_per_hypothesis")


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
            revision=0, task_key="tk1", kind=ACTION_KIND_EXPAND_HYPOTHESIS,
            depth=1):
    return ledger.enqueue_action(
        run_id=run, parent_path_id=parent, context_ref=context,
        subject_ref=subject, action_kind=kind,
        parent_search_revision=revision, policy_version=PV,
        payload={"task_key": task_key, "frozen_pool_digest": "pool-A"},
        depth=depth)


def fresh_ledger(db: Path, runs_root: Path, run: str) -> SearchLedger:
    return SearchLedger(PollutantPathwayStore(db),
                        ArtifactStore(runs_root, run), run)


def one(ledger, sql, params=()):
    return ledger.conn.execute(sql, params).fetchone()[0]


def action_status(ledger, action_id) -> str:
    return one(ledger, "SELECT status FROM search_actions WHERE"
                " action_id = ?", (action_id,))


def refs_of(ledger, action_id):
    row = ledger.action(action_id)
    return row["budget_reservation_ref"], row["attempt_refs"]


class PhaseCase:
    """按复审探针的相位搭建合法链(与 necessary_reference_probe 同构):
    first_complete/B4/B3/done_* 提交事件(done_* 另完成记账);B3 写
    bundle;B1/defer 只认领。"""

    def __init__(self, tmp_path: Path, phase: str):
        self.phase = phase
        name = f"r4-{phase}".replace("_", "-").lower()
        store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
        _, _, hyp, event, ev_args = make_fixture(name, "p1", "k1", "ctx1")
        out = enqueue(ledger, name, hyp.hypothesis_id)
        self.action_id = out["action_id"]
        self.receipt = ledger.claim_action(self.action_id, worker_id="w1")
        self.artifact_path = None
        if phase == "B3_recover":
            ledger.write_commit_bundle(
                action_id=self.action_id,
                attempt_id=self.receipt["attempt_refs"][0], event=event,
                task_key="tk1", **ev_args)
            self.artifact_path = (
                runs_root / name / "results" / "tk1" /
                "search_commit_bundle.json")
            self.original_artifact = self.artifact_path.read_bytes()
        elif phase not in ("B1_recover", "defer"):
            ledger.submit_action_event(self.action_id, event,
                                       worker_id="w1", **ev_args)
        if phase.startswith("done_"):
            ledger.complete_action(self.action_id, worker_id="w1",
                                   event_id=event.event_id)
        self.store, self.ledger, self.policy = store, ledger, policy
        self.db, self.runs_root, self.run = db, runs_root, name
        self.event, self.ev_args = event, ev_args

    def event_submitted(self) -> bool:
        return self.phase not in ("B1_recover", "defer", "B3_recover")

    def done_before_entry(self) -> bool:
        return self.phase.startswith("done_")

    def expected_events(self) -> int:
        return 1 if self.event_submitted() else 0

    def expected_commits(self) -> int:
        return 1 if self.done_before_entry() else 0

    def entry(self, ledger: SearchLedger):
        if self.phase in ("first_complete", "done_complete"):
            return ledger.complete_action(self.action_id, worker_id="w1",
                                          event_id=self.event.event_id)
        if self.phase == "done_claim":
            return ledger.claim_action(self.action_id, worker_id="w-other")
        if self.phase == "done_submit":
            return ledger.submit_action_event(
                self.action_id, self.event, worker_id="w1", **self.ev_args)
        if self.phase == "defer":
            return ledger.defer_action(self.action_id, worker_id="w1",
                                       reason="no_new_information")
        return ledger.recover_run(self.run, policy_block=self.policy)


def mutate_necessary(ledger, action_id: str, limit_key: str,
                     mode: str) -> str:
    """按复审探针模式改坏必要预约:仅删冻结引用清单中的 ref,或同时
    删预约行(不重造 event/hypothesis/hash,不改其他权威)。"""
    rid = ledger.conn.execute(
        "SELECT reservation_id FROM budget_reservations WHERE"
        " action_id = ? AND limit_key = ?",
        (action_id, limit_key)).fetchone()[0]
    refs = json.loads(ledger.conn.execute(
        "SELECT budget_reservation_ref FROM search_actions WHERE"
        " action_id = ?", (action_id,)).fetchone()[0])
    refs.remove(rid)
    ledger.conn.execute(
        "UPDATE search_actions SET budget_reservation_ref = ? WHERE"
        " action_id = ?",
        (json.dumps(refs), action_id))
    if mode == "remove_ref_and_row":
        ledger.conn.execute(
            "DELETE FROM budget_reservations WHERE reservation_id = ?",
            (rid,))
    ledger.conn.commit()
    return rid


# ------------------------------------------------------------ S3A-02 必要集合


@pytest.mark.parametrize("key", NECESSARY_KEYS)
@pytest.mark.parametrize("mode", MUTATIONS)
@pytest.mark.parametrize("phase", PHASES)
def test_necessary_reservation_set_missing_refused(
        tmp_path: Path, phase: str, mode: str, key: str) -> None:
    """S3A-02 r4:合法 expand claim 本有总 action/alternatives/attempts
    三类必要预约;仅从冻结引用清单删其中一项(或再删该行)⇒ 9 入口
    全部结构化拒 —— 剩余清单非空/剩余行合法不能代替必要集合齐全;
    坏 action 零新 commit/consume/成功确认,B3 零 event 新增、artifact
    保全,done 不漏结算/不伪称 verified。"""
    case = PhaseCase(tmp_path, phase)
    mutate_necessary(case.ledger, case.action_id, key, mode)
    case.store.close()

    ledger2 = fresh_ledger(case.db, case.runs_root, case.run)
    with pytest.raises(SearchIntegrityError) as ei:
        case.entry(ledger2)
    assert ei.value.detail["kind"] == (
        "reservation_row_missing" if mode == "remove_ref_and_row"
        else "necessary_reservation_ref_missing")
    assert ei.value.detail["limit_key"] == key
    # 零新成功消费:事件/提交记录/action 状态与入口调用前一致
    assert ledger2.store.counts()["events"] == case.expected_events()
    assert one(ledger2, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (case.run,)) == case.expected_commits()
    expected_status = "done" if case.done_before_entry() else "claimed"
    assert action_status(ledger2, case.action_id) == expected_status
    if case.phase == "B3_recover":
        assert case.artifact_path.read_bytes() == case.original_artifact
    ledger2.store.close()


@pytest.mark.parametrize("phase", PHASES)
def test_necessary_reservation_set_clean_controls(
        tmp_path: Path, phase: str) -> None:
    """S3A-02 r4 正控:9 入口不改动必要集合时合法行为保持(不被必要
    集合判据误伤为全面拒绝)。"""
    case = PhaseCase(tmp_path, phase)
    case.store.close()

    ledger2 = fresh_ledger(case.db, case.runs_root, case.run)
    out = case.entry(ledger2)
    if phase == "first_complete":
        assert out["completed"] is True
    elif phase == "defer":
        assert out["deferred"] is True
    elif phase == "done_claim":
        assert out["claimed"] is False and out["reason"] == \
            "already_completed"
    elif phase == "done_complete":
        assert out["completed"] is False and out["unchanged"]
    elif phase == "done_submit":
        assert out["created"] is False and out["event_id"] == \
            case.event.event_id
    else:  # recover 系入口:结构化报告正常返回
        assert isinstance(out, dict) and out["run_id"] == case.run
        if phase == "done_recover":
            entry = [a for a in out["actions"]
                     if a["action_id"] == case.action_id][0]
            assert entry["disposition"] == "done_commit_verified"
        elif phase == "B3_recover":
            assert ledger2.store.counts()["events"] == 1
    if phase == "first_complete":
        snap = ledger2.budget_snapshot(case.run)
        assert snap["run_level"]["max_total_search_actions"]["used"] == 1
    ledger2.store.close()


def test_one_action_budget_chain_total_removal_refused(
        tmp_path: Path) -> None:
    """S3A-02 r4 上限 1 完整链(复审 §4.1 独立钉子):干净链第一次完成
    后第二 claim 按预算不足拒;仅第一次 claim 后删总额度 ref+row ⇒
    第一次 complete 被必要集合判据拒(不再 used0/commits2 骗过
    max_total=1);后续不同 hypothesis 的干净链仍可正常完成(损坏
    只钉死被删证据的 action,不扩大为全面拒绝)。"""
    name = "r4-chain"
    store, ledger, art, policy, db, runs_root = make_run(
        tmp_path, name, {"max_total_search_actions": 1})
    _, _, hyp_a, event_a, ev_a = make_fixture(name, "p1", "k1", "ctx1")
    out1 = enqueue(ledger, name, hyp_a.hypothesis_id, task_key="tk1")
    ledger.claim_action(out1["action_id"], worker_id="w1")
    ledger.submit_action_event(out1["action_id"], event_a,
                               worker_id="w1", **ev_a)
    # 删总额度 ref+row(第一次 claim 后)
    mutate_necessary(ledger, out1["action_id"],
                     "max_total_search_actions", "remove_ref_and_row")
    with pytest.raises(SearchIntegrityError) as ei:
        ledger.complete_action(out1["action_id"], worker_id="w1",
                               event_id=event_a.event_id)
    assert ei.value.detail["kind"] == "reservation_row_missing"
    assert action_status(ledger, out1["action_id"]) == "claimed"
    assert one(ledger, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == 0
    # 干净第二链:不同 hypothesis 正常 claim/submit/complete
    _, _, hyp_b, event_b, ev_b = make_fixture(name, "p1", "k2", "ctx1")
    out2 = enqueue(ledger, name, hyp_b.hypothesis_id, task_key="tk2")
    ledger.claim_action(out2["action_id"], worker_id="w1")
    ledger.submit_action_event(out2["action_id"], event_b,
                               worker_id="w1", **ev_b)
    ledger.complete_action(out2["action_id"], worker_id="w1",
                           event_id=event_b.event_id)
    assert action_status(ledger, out2["action_id"]) == "done"
    assert one(ledger, "SELECT COUNT(*) FROM search_commit_records WHERE"
               " run_id = ?", (name,)) == 1  # 只有干净链的提交
    snap = ledger.budget_snapshot(name)
    assert snap["run_level"]["max_total_search_actions"]["used"] == 1
    store.close()

    # 干净对照:两条完整链下第二个 claim 按预算不足拒(上限 1)
    name2 = "r4-chain-clean"
    store, ledger, _, _, db, runs_root = make_run(
        tmp_path, name2, {"max_total_search_actions": 1})
    _, _, hyp_a, event_a, ev_a = make_fixture(name2, "p1", "k1", "ctx1")
    out1 = enqueue(ledger, name2, hyp_a.hypothesis_id)
    receipt = ledger.claim_action(out1["action_id"], worker_id="w1")
    commit_search_event(ledger, out1["action_id"], event_a, worker_id="w1",
                        attempt_id=receipt["attempt_refs"][0],
                        task_key="tk1", **ev_a)
    _, _, hyp_b, _, _ = make_fixture(name2, "p1", "k2", "ctx1")
    out2 = enqueue(ledger, name2, hyp_b.hypothesis_id, task_key="tk2")
    with pytest.raises(SearchBudgetExhausted) as eb:
        ledger.claim_action(out2["action_id"], worker_id="w1")
    assert eb.value.detail["limit_key"] == "max_total_search_actions"
    store.close()


def test_cache_hit_retrieve_not_forced_necessary(tmp_path: Path) -> None:
    """S3A-02 r4 正控:cache_hit 认领不落检索预约(创建规则的条件参数),
    必要集合判据不强加未消费的资源预约 —— cache_hit retrieve 可完成;
    非 cache_hit retrieve(预约行在)删 ref 同样拒。"""
    name = "r4-cache"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    out = enqueue(ledger, name, "pool-1", kind=ACTION_KIND_RETRIEVE,
                  depth=None, task_key="tk1")
    ledger.claim_action(out["action_id"], worker_id="w1", cache_hit=True)
    refs, _ = refs_of(ledger, out["action_id"])
    assert refs  # 只有总 action 预约,无检索预约
    limit_keys = {one(ledger, "SELECT limit_key FROM budget_reservations"
                      " WHERE reservation_id = ?", (r,)) for r in refs}
    assert "max_retrievals_per_parent" not in limit_keys
    ledger.complete_action(out["action_id"], worker_id="w1",
                           outcome_kind=COMMIT_KIND_OUTCOME)
    assert action_status(ledger, out["action_id"]) == "done"

    # 非 cache_hit retrieve:删其中一条检索 ref ⇒ 完成前拒
    out2 = enqueue(ledger, name, "pool-1", kind=ACTION_KIND_RETRIEVE,
                   depth=None, revision=1, task_key="tk2")
    ledger.claim_action(out2["action_id"], worker_id="w1")
    mutate_necessary(ledger, out2["action_id"],
                     "max_retrievals_per_parent", "remove_ref_only")
    with pytest.raises(SearchIntegrityError) as ei:
        ledger.complete_action(out2["action_id"], worker_id="w1",
                               outcome_kind=COMMIT_KIND_OUTCOME)
    assert ei.value.detail["kind"] == "necessary_reservation_ref_missing"
    assert ei.value.detail["limit_key"] == "max_retrievals_per_parent"
    assert action_status(ledger, out2["action_id"]) == "claimed"
    store.close()


def test_scenario_transition_necessary_reservation(tmp_path: Path) -> None:
    """S3A-02 r4:scenario_transition 的必要 transitions 预约同规则
    (行存在 ⇒ 必须被引用);合法 transition 完成不受影响。"""
    name = "r4-trans"
    store, ledger, art, policy, db, runs_root = make_run(
        tmp_path, name, {"max_scenario_transitions": 1})
    out = enqueue(ledger, name, "scenario-x",
                  kind=ACTION_KIND_SCENARIO_TRANSITION, depth=None,
                  task_key="tk1")
    ledger.claim_action(out["action_id"], worker_id="w1")
    mutate_necessary(ledger, out["action_id"],
                     "max_scenario_transitions", "remove_ref_only")
    with pytest.raises(SearchIntegrityError) as ei:
        ledger.complete_action(out["action_id"], worker_id="w1",
                               outcome_kind=COMMIT_KIND_OUTCOME)
    assert ei.value.detail["kind"] == "necessary_reservation_ref_missing"
    assert action_status(ledger, out["action_id"]) == "claimed"

    out2 = enqueue(ledger, name, "scenario-y",
                   kind=ACTION_KIND_SCENARIO_TRANSITION, depth=None,
                   revision=1, task_key="tk2")
    # 转换额度 1 已被占用(上一条仍 reserved)⇒ 新 transition 认领拒
    with pytest.raises(SearchBudgetExhausted):
        ledger.claim_action(out2["action_id"], worker_id="w1")
    store.close()


# -------------------------------------------------------- S3A-03 状态口策略


POLICY_DAMAGES = ("null_limits", "missing_version", "bool",
                  "out_of_range", "unknown_key", "negative")
STATUS_ENTRIES = ("sent", "response", "failed")


def _claimed_expand_with_request(ledger, run, *, request_key="rk",
                                 revision=0, task_key="tk1"):
    """认领一个 expand action 并登记 scripted 请求(每条新链用不同
    revision/task_key —— revision 进 action 身份,同主体新链合法)。"""
    _, _, hyp, _, _ = make_fixture(run, "p1", "k1", "ctx1")
    out = enqueue(ledger, run, hyp.hypothesis_id, revision=revision,
                  task_key=task_key)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    return ledger.register_model_request(
        run_id=run, action_id=out["action_id"],
        attempt_id=receipt["attempt_refs"][0],
        provider_kind=PROVIDER_KIND_SCRIPTED, request_key=request_key,
        purpose="rank", payload={"prompt": "original"})


def _damage_stored_policy(ledger, run, damage: str) -> None:
    stored = json.loads(ledger.conn.execute(
        "SELECT policy_block FROM search_runs WHERE run_id = ?",
        (run,)).fetchone()[0])
    limits = stored["search_limits"]
    if damage == "null_limits":
        stored["search_limits"] = None
    elif damage == "missing_version":
        stored["search_limits"] = {k: v for k, v in limits.items()
                                   if k != "version"}
    elif damage == "bool":
        stored["search_limits"]["max_total_search_actions"] = True
    elif damage == "out_of_range":
        stored["search_limits"]["max_total_search_actions"] = 1001
    elif damage == "unknown_key":
        stored["search_limits"]["unregistered_key"] = 1
    else:  # negative
        stored["search_limits"]["max_total_search_actions"] = -1
    ledger.conn.execute(
        "UPDATE search_runs SET policy_block = ? WHERE run_id = ?",
        (json.dumps(stored, ensure_ascii=False, sort_keys=True), run))
    ledger.conn.commit()


def _status_entry_call(ledger, request_id, entry):
    if entry == "sent":
        return ledger.record_request_sent(request_id)
    if entry == "response":
        return ledger.record_request_response(request_id, "response-A")
    return ledger.mark_request_failed(request_id)


@pytest.mark.parametrize("entry", STATUS_ENTRIES)
@pytest.mark.parametrize("damage", POLICY_DAMAGES)
def test_request_status_entries_policy_guard(
        tmp_path: Path, damage: str, entry: str) -> None:
    """S3A-03 r4:合法先登记的请求,存储 search_limits 被改成 null/缺
    version/bool/越界/未知键/负数 ⇒ sent/response/failed 状态口在新
    status 写入之前结构化拒(search_policy_block_corrupt),无成功状态
    变化(与预算/claim/recover 同一守卫来源;不补默认、不依赖调用方
    预验)。"""
    name = f"r4-policy-{damage}-{entry}"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    req = _claimed_expand_with_request(ledger, name)
    status_before = REQUEST_STATUS_REGISTERED
    if entry == "response":  # 合法策略下先到 sent
        ledger.record_request_sent(req["request_id"])
        status_before = REQUEST_STATUS_SENT
    _damage_stored_policy(ledger, name, damage)

    with pytest.raises(SearchRecoveryError) as ei:
        _status_entry_call(ledger, req["request_id"], entry)
    assert ei.value.detail["kind"] == "search_policy_block_corrupt"
    # 无成功状态变化:状态/网络计数保持
    row = ledger.request(req["request_id"])
    assert row["status"] == status_before
    assert row["network_request_count"] == 0
    store.close()


def test_request_status_entries_legal_policy_controls(
        tmp_path: Path) -> None:
    """S3A-03 r4 正控:合法冻结块下请求状态机往返照常(registered→sent
    →responded;registered/sent→failed;scripted 网络 0;真实额度不
    因同键幂等复用重复扣)。"""
    name = "r4-policy-ok"
    store, ledger, art, policy, db, runs_root = make_run(
        tmp_path, name, {"max_real_model_requests": 2,
                         "max_attempts_per_hypothesis": 8,
                         "max_alternative_hypotheses_per_parent": 8})
    req = _claimed_expand_with_request(ledger, name, request_key="rk1")
    ledger.record_request_sent(req["request_id"])
    assert ledger.request(req["request_id"])["status"] == \
        REQUEST_STATUS_SENT
    ledger.record_request_response(req["request_id"], "resp")
    assert ledger.request(req["request_id"])["status"] == \
        REQUEST_STATUS_RESPONDED
    # sent→failed 合法(scripted;第二条请求,新 action 链)
    req2 = _claimed_expand_with_request(ledger, name, request_key="rk2",
                                        revision=1, task_key="tk2")
    ledger.record_request_sent(req2["request_id"])
    ledger.mark_request_failed(req2["request_id"])
    assert ledger.request(req2["request_id"])["status"] == \
        REQUEST_STATUS_FAILED
    assert ledger.request(req2["request_id"])["network_request_count"] == 0

    # 真实 provider:同键幂等复用不重复扣额度(一行占额)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id, revision=2,
                  task_key="tk3")
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    real = ledger.register_model_request(
        run_id=name, action_id=out["action_id"],
        attempt_id=receipt["attempt_refs"][0],
        provider_kind=PROVIDER_KIND_REAL, request_key="rk-real")
    again = ledger.register_model_request(
        run_id=name, action_id=out["action_id"],
        attempt_id=receipt["attempt_refs"][0],
        provider_kind=PROVIDER_KIND_REAL, request_key="rk-real")
    assert again["registered"] is False and again["unchanged"]
    assert one(ledger, "SELECT COUNT(*) FROM budget_reservations WHERE"
               " run_id = ? AND limit_key = 'max_real_model_requests'",
               (name,)) == 1  # 实际网络 0(仅登记占额)
    store.close()


# ------------------------------------------------ S3A-04 生命周期来源闭合


def test_mark_request_failed_unknown_status_refused_and_preserved(
        tmp_path: Path) -> None:
    """S3A-04 r4:合法登记行仅改 status 为枚举外值后,mark_request_
    failed 结构化拒(request_status_unknown)并保全 —— 未知生命周期
    不能被正常化成合法终态 failed(原状态保留、零状态写入)。"""
    name = "r4-unknown-failed"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    req = _claimed_expand_with_request(ledger, name)
    ledger.conn.execute(
        "UPDATE model_requests SET status = 'corrupt-status' WHERE"
        " request_id = ?", (req["request_id"],))
    ledger.conn.commit()
    with pytest.raises(SearchContractError) as ei:
        ledger.mark_request_failed(req["request_id"])
    assert ei.value.detail["kind"] == "request_status_unknown"
    assert ei.value.detail["status"] == "corrupt-status"
    assert ledger.request(req["request_id"])["status"] == "corrupt-status"
    store.close()


def test_sent_response_entries_reject_unknown_status(
        tmp_path: Path) -> None:
    """S3A-04 r4(保持):sent/response 状态口对枚举外状态照旧结构化拒
    (r3 已闭合;未知状态不得经任何状态口洗成已知状态)。"""
    name = "r4-unknown-sent"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    req = _claimed_expand_with_request(ledger, name)
    ledger.conn.execute(
        "UPDATE model_requests SET status = 'corrupt-status' WHERE"
        " request_id = ?", (req["request_id"],))
    ledger.conn.commit()
    with pytest.raises(SearchContractError) as e1:
        ledger.record_request_sent(req["request_id"])
    assert e1.value.detail["kind"] == "request_not_resendable"
    with pytest.raises(SearchContractError) as e2:
        ledger.record_request_response(req["request_id"], "resp")
    assert e2.value.detail["kind"] == "request_not_awaiting"
    assert ledger.request(req["request_id"])["status"] == "corrupt-status"
    store.close()


def test_register_same_key_unknown_stored_status_refused(
        tmp_path: Path) -> None:
    """S3A-04 r4:同键既有坏 status 的语义按完整性失败明确 —— 原参数
    重登记不把坏状态当合法幂等 unchanged 返回,结构化拒、零写入、
    坏行保全。"""
    name = "r4-unknown-reuse"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    base = dict(run_id=name, action_id=out["action_id"],
                attempt_id=receipt["attempt_refs"][0],
                provider_kind=PROVIDER_KIND_SCRIPTED, request_key="rk",
                purpose="rank", payload={"a": 1})
    req = ledger.register_model_request(**base)
    ledger.conn.execute(
        "UPDATE model_requests SET status = 'corrupt-status' WHERE"
        " request_id = ?", (req["request_id"],))
    ledger.conn.commit()
    with pytest.raises(SearchIntegrityError) as ei:
        ledger.register_model_request(**base)
    assert ei.value.detail["kind"] == "request_status_unknown"
    assert one(ledger, "SELECT COUNT(*) FROM model_requests WHERE"
               " request_id = ?", (req["request_id"],)) == 1
    assert ledger.request(req["request_id"])["status"] == "corrupt-status"
    store.close()


def test_recover_discloses_unknown_status_requests(tmp_path: Path) -> None:
    """S3A-04 r4:恢复对 run 范围状态枚举外的请求行结构化披露
    (unknown_status_requests)—— 不伪装合法 pending、不改状态、不
    猜补(跨 run 行不在本 run 扫描内是已登记作用域边界)。"""
    name = "r4-unknown-recover"
    store, ledger, art, policy, db, runs_root = make_run(tmp_path, name)
    req = _claimed_expand_with_request(ledger, name)
    ledger.conn.execute(
        "UPDATE model_requests SET status = 'corrupt-status' WHERE"
        " request_id = ?", (req["request_id"],))
    ledger.conn.commit()
    store.close()

    ledger2 = fresh_ledger(db, runs_root, name)
    report = ledger2.recover_run(name)
    assert all(p["request_id"] != req["request_id"]
               for p in report["pending_requests"])  # 不伪装合法 pending
    disclosed = report["unknown_status_requests"]
    assert [d["request_id"] for d in disclosed] == [req["request_id"]]
    assert disclosed[0]["status"] == "corrupt-status"
    # 零状态写入:行原样保全
    assert ledger2.request(req["request_id"])["status"] == "corrupt-status"
    ledger2.store.close()


def test_mark_request_failed_legal_lifecycle_controls(
        tmp_path: Path) -> None:
    """S3A-04 r4 正控:合法 registered→failed、sent→failed;真实请求
    失败占额不释放;终态(responded/failed)不可再改记 failed、不可
    重发;显式 retry = 新 request_key 合法登记。"""
    name = "r4-fail-ok"
    store, ledger, art, policy, db, runs_root = make_run(
        tmp_path, name, {"max_real_model_requests": 2,
                         "max_attempts_per_hypothesis": 8,
                         "max_alternative_hypotheses_per_parent": 8})
    # registered → failed(scripted)
    req = _claimed_expand_with_request(ledger, name, request_key="rk1")
    ledger.mark_request_failed(req["request_id"])
    assert ledger.request(req["request_id"])["status"] == \
        REQUEST_STATUS_FAILED
    # 终态不可重发/重败
    with pytest.raises(SearchContractError) as e1:
        ledger.record_request_sent(req["request_id"])
    assert e1.value.detail["kind"] == "request_not_resendable"
    with pytest.raises(SearchContractError) as e2:
        ledger.mark_request_failed(req["request_id"])
    assert e2.value.detail["kind"] == "request_not_failable"

    # sent → responded → 不可改记 failed(合法 closed 来源)
    req2 = _claimed_expand_with_request(ledger, name, request_key="rk2",
                                        revision=1, task_key="tk2")
    ledger.record_request_sent(req2["request_id"])
    ledger.record_request_response(req2["request_id"], "resp")
    with pytest.raises(SearchContractError) as e3:
        ledger.mark_request_failed(req2["request_id"])
    assert e3.value.detail["kind"] == "request_not_failable"

    # 真实 provider 失败:占额不释放(悬空/失败均占)
    _, _, hyp, _, _ = make_fixture(name, "p1", "k1", "ctx1")
    out = enqueue(ledger, name, hyp.hypothesis_id, revision=2,
                  task_key="tk3")
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    real = ledger.register_model_request(
        run_id=name, action_id=out["action_id"],
        attempt_id=receipt["attempt_refs"][0],
        provider_kind=PROVIDER_KIND_REAL, request_key="rk-real")
    ledger.mark_request_failed(real["request_id"])
    assert ledger.request(real["request_id"])["status"] == \
        REQUEST_STATUS_FAILED
    assert one(ledger, "SELECT status FROM budget_reservations WHERE"
               " run_id = ? AND limit_key = 'max_real_model_requests'",
               (name,)) == "consumed"  # 占额不释放

    # 显式 retry:新 request_key ⇒ 新请求合法登记(合法空 attempt 的
    # 非 expand action 同样支持)
    out_d = enqueue(ledger, name, "pool-1", kind="decide", depth=None,
                    task_key="tkD")
    ledger.claim_action(out_d["action_id"], worker_id="w1")
    retry = ledger.register_model_request(
        run_id=name, action_id=out_d["action_id"], attempt_id="",
        provider_kind=PROVIDER_KIND_SCRIPTED, request_key="rk-retry",
        retry_of=real["request_id"])
    assert retry["registered"] and retry["request_id"] != \
        real["request_id"]
    ledger.record_request_sent(retry["request_id"])  # 非 expand 空 attempt
    assert ledger.request(retry["request_id"])["network_request_count"] == 0
    store.close()
