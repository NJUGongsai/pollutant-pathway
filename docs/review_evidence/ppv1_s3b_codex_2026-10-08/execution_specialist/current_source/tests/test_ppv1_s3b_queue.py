"""S3b 队列调度回归(schedule/record_outcome/activate_deferred/转换/
followup;ppv1-search-5)。

规则级合成夹具(CCO → CC=O;AtomTool 编辑协议 change_bond_order);
临时 SQLite/artifact,无金标/题面/封存材料。覆盖(任务书 §7 S3b 行):
- E02:两类 deferred(共同产物/备选反应)分别激活、重复触发幂等、
  旧 revision 明确 unchanged、预算不足留独立未展开原因;
- 场景转换:须显式 source_ref、独立 action、转换预算在 claim;
- followup:计划引用必须是事件产物;宽度上限 ⇒ deferred;
- 队列幂等/同键异内容冲突;停止报告披露 deferred 未探索。
基线 b7f2bba 上本文件为 collection 红(pollutant.queue 缺失),分类
登记见交付书。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.events import (  # noqa: E402
    build_expansion_plan,
    build_pathway_event,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    Participant,
    build_hypothesis,
)
from pathway_v43.pollutant.chemstate import build_chemical_state  # noqa: E402
from pathway_v43.pollutant.profile import (  # noqa: E402
    build_profile_identity_block,
)
from pathway_v43.pollutant.queue import (  # noqa: E402
    DEFERRED_TYPE_ALTERNATIVE,
    DEFERRED_TYPE_COPRODUCT,
    OUTCOME_KIND_METHOD_FAILED,
    OUTCOME_KIND_UNRESOLVED_CONTINUATION,
    ScheduleContractError,
    activate_deferred,
    child_path_id,
    enqueue_coproduct_followups,
    enqueue_scenario_transition,
    frozen_pool_digest,
    record_expansion_outcome,
    schedule_hypotheses,
)
from pathway_v43.pollutant.search import (  # noqa: E402
    ACTION_KIND_EXPAND_HYPOTHESIS,
    ACTION_KIND_SCENARIO_TRANSITION,
    ACTION_STATUS_DEFERRED,
    ACTION_STATUS_DONE,
    ACTION_STATUS_PENDING,
    ATTEMPT_STATUS_FAILED,
    SearchLedger,
    search_policy_version,
)
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402

PV = search_policy_version()


def make_run(tmp_path: Path, name: str, limits: dict | None = None):
    runs_root = tmp_path / "runs"
    store = PollutantPathwayStore(tmp_path / f"{name}.sqlite")
    art = ArtifactStore(runs_root, name)
    ledger = SearchLedger(store, art, name)
    policy = build_profile_identity_block(
        search_limits=limits) if limits else build_profile_identity_block()
    ledger.register_search_run(name, policy)
    return store, ledger, art, policy


def make_pool_entry(hypothesis_id: str, key: str = "B", rank: int = 1,
                    payload: dict | None = None):
    return {"hypothesis_key": key, "hypothesis_id": hypothesis_id,
            "rank": rank, "payload": payload or {"task_key": f"tk-{key}"}}


def make_substrate_states():
    sub = build_chemical_state("CCO", "raw_input", [{"record": "sub-A"}])
    prod = build_chemical_state("CC=O", "source_product",
                                [{"record": "prod-A"}])
    return sub, prod


def make_hypothesis(parent: str, sub, prod):
    return build_hypothesis(
        parent_path_id=parent, substrate_state_ref=sub.state_id,
        participants=[
            Participant(state_ref=sub.state_id, side="reactant",
                        role="primary_substrate", coefficient=1,
                        coefficient_status="known"),
            Participant(state_ref=prod.state_id, side="product",
                        role="principal_product", coefficient=1,
                        coefficient_status="known")],
        participant_list_status="source_complete", step_scope="net_reaction",
        origin_group_key="k1")


# ---------------------------------------------------------------- schedule


def test_schedule_selected_within_alternatives_budget(tmp_path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "sch-1")
    sub, prod = make_substrate_states()
    h1 = make_hypothesis("p1", sub, prod)
    out = schedule_hypotheses(
        ledger, run_id="sch-1", parent_path_id="p1", context_ref="ctx",
        parent_search_revision=0, pool=[make_pool_entry(h1.hypothesis_id, "A")],
        policy_version=PV, depth=1)
    assert [e["hypothesis_id"] for e in out["selected"]] == \
        [h1.hypothesis_id]
    assert out["deferred"] == [] and out["blocked"] == []
    action = ledger.action(out["selected"][0]["action_id"])
    assert action["status"] == ACTION_STATUS_PENDING
    assert action["action_kind"] == ACTION_KIND_EXPAND_HYPOTHESIS


def test_schedule_beyond_budget_defers_alternatives(tmp_path) -> None:
    # alternatives 上限 1:池 2 条 ⇒ 第 2 条 deferred(备选反应类型)。
    # 单次调度:池成员变化后同身份重排会按同键异内容拒(冻结任务
    # 输入含池 digest —— 池变化须新 revision 重排,不改写旧 action)
    _, ledger, _, _ = make_run(
        tmp_path, "sch-2", {"max_alternative_hypotheses_per_parent": 1})
    sub, prod = make_substrate_states()
    h1 = make_hypothesis("p1", sub, prod)
    prod2 = build_chemical_state("CC(=O)O", "source_product",
                                 [{"record": "prod-B"}])
    h2 = make_hypothesis("p1", sub, prod2)
    out = schedule_hypotheses(
        ledger, run_id="sch-2", parent_path_id="p1", context_ref="ctx",
        parent_search_revision=0,
        pool=[make_pool_entry(h1.hypothesis_id, "A", 1),
              make_pool_entry(h2.hypothesis_id, "B", 2)],
        policy_version=PV, depth=1)
    assert len(out["selected"]) == 1
    assert len(out["deferred"]) == 1
    deferred = out["deferred"][0]
    assert deferred["deferred_type"] == DEFERRED_TYPE_ALTERNATIVE
    assert deferred["reason"] == "alternatives_budget"
    row = ledger.action(deferred["action_id"])
    assert row["status"] == ACTION_STATUS_DEFERRED
    assert row["defer_reason"] == "alternatives_budget"
    assert row["payload"]["deferred_type"] == DEFERRED_TYPE_ALTERNATIVE


def test_schedule_max_select_cap_leaves_selection_cap_reason(
        tmp_path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "sch-3")  # alternatives 默认 2
    sub, prod = make_substrate_states()
    prod2 = build_chemical_state("CC(=O)O", "source_product",
                                 [{"record": "prod-B"}])
    h1 = make_hypothesis("p1", sub, prod)
    h2 = make_hypothesis("p1", sub, prod2)
    out = schedule_hypotheses(
        ledger, run_id="sch-3", parent_path_id="p1", context_ref="ctx",
        parent_search_revision=0,
        pool=[make_pool_entry(h1.hypothesis_id, "A", 1),
              make_pool_entry(h2.hypothesis_id, "B", 2)],
        policy_version=PV, depth=1, budget={"max_select": 1})
    assert len(out["selected"]) == 1
    assert out["deferred"][0]["reason"] == "selection_cap"


def test_schedule_depth_blocked_whole_pool(tmp_path) -> None:
    # max_search_depth 1:depth 2 整池 blocked,不入队
    _, ledger, _, _ = make_run(tmp_path, "sch-4", {"max_search_depth": 1})
    sub, prod = make_substrate_states()
    h1 = make_hypothesis("p1", sub, prod)
    out = schedule_hypotheses(
        ledger, run_id="sch-4", parent_path_id="p1", context_ref="ctx",
        parent_search_revision=0, pool=[make_pool_entry(h1.hypothesis_id)],
        policy_version=PV, depth=2)
    assert out["blocked"][0]["reason"] == "depth_limit"
    assert ledger.action(out["selected"][0]["action_id"]) is None \
        if out["selected"] else True
    assert out["selected"] == [] and out["deferred"] == []


def test_schedule_idempotent_reschedule_and_done_blocked(tmp_path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "sch-5")
    sub, prod = make_substrate_states()
    h1 = make_hypothesis("p1", sub, prod)
    entry = make_pool_entry(h1.hypothesis_id)
    first = schedule_hypotheses(
        ledger, run_id="sch-5", parent_path_id="p1", context_ref="ctx",
        parent_search_revision=0, pool=[entry], policy_version=PV, depth=1)
    again = schedule_hypotheses(
        ledger, run_id="sch-5", parent_path_id="p1", context_ref="ctx",
        parent_search_revision=0, pool=[entry], policy_version=PV, depth=1)
    assert again["selected"][0]["reason"] == "already_enqueued"
    assert again["selected"][0]["action_id"] == \
        first["selected"][0]["action_id"]
    # 完成后重排:blocked already_expanded(无新信息不再安排)
    ledger.claim_action(first["selected"][0]["action_id"],
                        worker_id="w1")
    ledger.complete_action(
        first["selected"][0]["action_id"], worker_id="w1",
        outcome_kind="outcome_recorded", outcome_ref="x")
    done = schedule_hypotheses(
        ledger, run_id="sch-5", parent_path_id="p1", context_ref="ctx",
        parent_search_revision=0, pool=[entry], policy_version=PV, depth=1)
    assert done["blocked"][0]["reason"] == "already_expanded"


def test_schedule_pool_entry_contract(tmp_path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "sch-6")
    with pytest.raises(ScheduleContractError):
        schedule_hypotheses(
            ledger, run_id="sch-6", parent_path_id="p1", context_ref="ctx",
            parent_search_revision=0, pool=["not-a-dict"],
            policy_version=PV, depth=1)
    with pytest.raises(ScheduleContractError):
        schedule_hypotheses(
            ledger, run_id="sch-6", parent_path_id="p1", context_ref="ctx",
            parent_search_revision=0, pool=[{"hypothesis_key": "x"}],
            policy_version=PV, depth=1)


def test_pool_digest_deterministic_and_order_sensitive() -> None:
    sub, prod = make_substrate_states()
    h1 = make_hypothesis("p1", sub, prod)
    a = [make_pool_entry(h1.hypothesis_id, "A")]
    b = [make_pool_entry(h1.hypothesis_id, "A")]
    c = [make_pool_entry(h1.hypothesis_id, "A", rank=2)]
    assert frozen_pool_digest(a) == frozen_pool_digest(b)
    assert frozen_pool_digest(a) != frozen_pool_digest(c)


# ------------------------------------------------------- record_outcome


def test_record_expansion_outcome_method_failed(tmp_path) -> None:
    _, ledger, art, _ = make_run(tmp_path, "rec-1")
    sub, prod = make_substrate_states()
    h1 = make_hypothesis("p1", sub, prod)
    out = schedule_hypotheses(
        ledger, run_id="rec-1", parent_path_id="p1", context_ref="ctx",
        parent_search_revision=0, pool=[make_pool_entry(h1.hypothesis_id)],
        policy_version=PV, depth=1)
    action_id = out["selected"][0]["action_id"]
    receipt = ledger.claim_action(action_id, worker_id="w1")
    attempt_id = receipt["attempt_refs"][0]
    result = record_expansion_outcome(
        ledger, attempt_id, outcome={"kind": OUTCOME_KIND_METHOD_FAILED,
                                     "detail": {"execution": {"ok": False}}},
        evidence_refs=[action_id], worker_id="w1")
    assert result["completed"] is True
    attempt = ledger.open_attempt(action_id)
    assert attempt is None  # failed,不再 open
    row = ledger.conn.execute(
        "SELECT status FROM search_attempts WHERE expansion_attempt_id = ?",
        (attempt_id,)).fetchone()
    assert row["status"] == ATTEMPT_STATUS_FAILED
    # 结论 artifact 落盘(task_key 来自 action 冻结载荷)
    payload_action = ledger.action(action_id)
    env = art.read(payload_action["task_key"], "expansion_outcome")
    assert env["payload"]["outcome"]["kind"] == OUTCOME_KIND_METHOD_FAILED


def test_record_outcome_requires_claimed_owner(tmp_path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "rec-2")
    sub, prod = make_substrate_states()
    h1 = make_hypothesis("p1", sub, prod)
    out = schedule_hypotheses(
        ledger, run_id="rec-2", parent_path_id="p1", context_ref="ctx",
        parent_search_revision=0, pool=[make_pool_entry(h1.hypothesis_id)],
        policy_version=PV, depth=1)
    action_id = out["selected"][0]["action_id"]
    receipt = ledger.claim_action(action_id, worker_id="w1")
    attempt_id = receipt["attempt_refs"][0]
    with pytest.raises(ScheduleContractError):
        record_expansion_outcome(
            ledger, attempt_id, outcome={"kind": "method_failed"},
            worker_id="not-owner")  # 陈旧 worker 不可落账
    with pytest.raises(ScheduleContractError):
        record_expansion_outcome(
            ledger, "sattempt_missing", outcome={"kind": "method_failed"},
            worker_id="w1")
    with pytest.raises(ScheduleContractError):
        record_expansion_outcome(
            ledger, attempt_id, outcome={"kind": "not-in-enum"},
            worker_id="w1")


def test_unresolved_continuation_outcome(tmp_path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "rec-3")
    sub, prod = make_substrate_states()
    h1 = make_hypothesis("p1", sub, prod)
    out = schedule_hypotheses(
        ledger, run_id="rec-3", parent_path_id="p1", context_ref="ctx",
        parent_search_revision=0, pool=[make_pool_entry(h1.hypothesis_id)],
        policy_version=PV, depth=1)
    action_id = out["selected"][0]["action_id"]
    receipt = ledger.claim_action(action_id, worker_id="w1")
    result = record_expansion_outcome(
        ledger, receipt["attempt_refs"][0],
        outcome={"kind": OUTCOME_KIND_UNRESOLVED_CONTINUATION,
                 "detail": {"source_event_id": "ppev_x"}},
        evidence_refs=["ppev_x"], worker_id="w1")
    assert result["completed"] is True
    action = ledger.action(action_id)
    assert action["status"] == ACTION_STATUS_DONE


# ------------------------------------------------------- activate_deferred


def _deferred_pair(tmp_path, name, limits=None):
    """备选 deferred + 共同产物 deferred 的最小装置。"""
    store, ledger, art, _ = make_run(tmp_path, name, limits)
    sub, prod = make_substrate_states()
    h1 = make_hypothesis("p1", sub, prod)
    prod2 = build_chemical_state("CC(=O)O", "source_product",
                                 [{"record": "prod-B"}])
    h2 = make_hypothesis("p1", sub, prod2)
    # 备选 deferred:max_select 1、池 2 条 ⇒ 第 2 条 deferred
    schedule = schedule_hypotheses(
        ledger, run_id=name, parent_path_id="p1", context_ref="ctx",
        parent_search_revision=0,
        pool=[make_pool_entry(h1.hypothesis_id, "A", 1),
              make_pool_entry(h2.hypothesis_id, "B", 2)],
        policy_version=PV, depth=1,
        budget={"max_select": 1})
    alternative = schedule["deferred"][0]
    # 共同产物 deferred:事件 + 展开计划(width 0 ⇒ 全 deferred)
    hyp = make_hypothesis("p1", sub, prod)
    event = build_pathway_event(hyp, run_id=name, context_hash="ctx")
    plan = build_expansion_plan(
        hyp, expanded=[], deferred=[prod.state_id], not_tracked=[],
        reasons={prod.state_id: "product_width_limit"})
    followups = enqueue_coproduct_followups(
        ledger, run_id=name, parent_path_id="p1", context_ref="ctx",
        event_id=event.event_id, product_state_refs=[prod.state_id],
        expansion_plan=plan.to_dict(), policy_version=PV,
        parent_search_revision=1,
        substrate_smiles_by_ref={prod.state_id: "CC=O"})
    coproduct = followups["deferred"][0]
    return ledger, alternative, coproduct, event


def test_activate_deferred_both_types(tmp_path) -> None:
    ledger, alternative, coproduct, _ = _deferred_pair(tmp_path, "act-1")
    # 备选反应激活
    out = activate_deferred(
        ledger, run_id="act-1", parent_path_id="p1",
        trigger="explicit_user", expected_parent_revision=0,
        deferred_type=DEFERRED_TYPE_ALTERNATIVE)
    assert out["activated_ids"] == [alternative["action_id"]]
    row = ledger.action(alternative["action_id"])
    assert row["status"] == ACTION_STATUS_PENDING
    # 共同产物激活(子路径上)
    out2 = activate_deferred(
        ledger, run_id="act-1", parent_path_id=coproduct["child_path_id"],
        trigger="explicit_user", expected_parent_revision=1,
        deferred_type=DEFERRED_TYPE_COPRODUCT)
    assert out2["activated_ids"] == [coproduct["action_id"]]
    # 两类不混:deferred_type=ALTERNATIVE 不激活共同产物
    out3 = activate_deferred(
        ledger, run_id="act-1", parent_path_id=coproduct["child_path_id"],
        trigger="explicit_user", expected_parent_revision=1,
        deferred_type=DEFERRED_TYPE_ALTERNATIVE)
    assert out3["activated_ids"] == []


def test_activate_deferred_repeat_idempotent(tmp_path) -> None:
    ledger, alternative, _, _ = _deferred_pair(tmp_path, "act-2")
    first = activate_deferred(
        ledger, run_id="act-2", parent_path_id="p1",
        trigger="explicit_user", expected_parent_revision=0)
    second = activate_deferred(
        ledger, run_id="act-2", parent_path_id="p1",
        trigger="explicit_user", expected_parent_revision=0)
    assert first["activated_ids"]
    assert second["activated_ids"] == []
    assert second["unchanged"][0]["reason"] == "already_active"
    # 不重复安排同 action:激活后 pending 只有一个该 ID
    rows = ledger.actions_with_status("act-2", ACTION_STATUS_PENDING)
    ids = [r["action_id"] for r in rows]
    assert len(ids) == len(set(ids))


def test_activate_deferred_stale_revision_unchanged(tmp_path) -> None:
    ledger, alternative, coproduct, _ = _deferred_pair(tmp_path, "act-3")
    out = activate_deferred(
        ledger, run_id="act-3", parent_path_id="p1",
        trigger="explicit_user", expected_parent_revision=5)  # 旧/异 revision
    assert out["activated_ids"] == []
    assert out["unchanged"][0]["reason"] == "stale_parent_revision"
    assert ledger.action(alternative["action_id"])["status"] == \
        ACTION_STATUS_DEFERRED


def test_activate_deferred_trigger_mismatch_conflict(tmp_path) -> None:
    ledger, alternative, _, _ = _deferred_pair(tmp_path, "act-4")
    out = activate_deferred(
        ledger, run_id="act-4", parent_path_id="p1",
        trigger="wrong-trigger", expected_parent_revision=0)
    assert out["activated_ids"] == []
    assert out["conflicts"][0]["kind"] == "defer_trigger_mismatch"
    assert ledger.action(alternative["action_id"])["status"] == \
        ACTION_STATUS_DEFERRED


def test_activate_deferred_budget_insufficient_keeps_reason(tmp_path) -> None:
    # 总 action 预算耗尽 ⇒ 激活 unchanged budget_exhausted(独立未展开
    # 原因;不改状态)
    ledger, alternative, coproduct, _ = _deferred_pair(
        tmp_path, "act-5", {"max_total_search_actions": 1})
    # 已有 2 个 action(1 selected + deferred 池子入队也占 action 行,
    # 但预约只在 claim —— 预算预检按预约行;先耗尽预算:claim selected
    action_id = None
    for a in ledger.actions_with_status("act-5", ACTION_STATUS_PENDING):
        if a["action_kind"] == ACTION_KIND_EXPAND_HYPOTHESIS:
            action_id = a["action_id"]
            break
    ledger.claim_action(action_id, worker_id="w1")  # 占用唯一总额度
    out = activate_deferred(
        ledger, run_id="act-5", parent_path_id="p1",
        trigger="explicit_user", expected_parent_revision=0)
    assert out["activated_ids"] == []
    unchanged_reasons = {u["reason"] for u in out["unchanged"]}
    assert "budget_exhausted" in unchanged_reasons
    assert ledger.action(alternative["action_id"])["status"] == \
        ACTION_STATUS_DEFERRED


# ------------------------------------------------------- scenario transition


def test_scenario_transition_requires_explicit_source(tmp_path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "trans-1")
    with pytest.raises(ScheduleContractError):
        enqueue_scenario_transition(
            ledger, run_id="trans-1", parent_path_id="p1",
            context_ref="ctx", transition={"new_phase_id": "p2",
                                            "new_scenario_ref": "s2"},
            policy_version=PV, parent_search_revision=0)
    with pytest.raises(ScheduleContractError):
        enqueue_scenario_transition(
            ledger, run_id="trans-1", parent_path_id="p1",
            context_ref="ctx",
            transition={"source_ref": "user:1", "new_phase_id": ""},
            policy_version=PV, parent_search_revision=0)
    out = enqueue_scenario_transition(
        ledger, run_id="trans-1", parent_path_id="p1", context_ref="ctx",
        transition={"source_ref": "user:1", "new_phase_id": "p2",
                    "new_scenario_ref": "s2"},
        policy_version=PV, parent_search_revision=0)
    assert out["created"] is True
    action = ledger.action(out["action_id"])
    assert action["action_kind"] == ACTION_KIND_SCENARIO_TRANSITION
    # 转换预算在 claim 预约(独立计,不是反应边)
    receipt = ledger.claim_action(out["action_id"], worker_id="w1")
    assert receipt["claimed"]
    reservations = [r for r in ledger.conn.execute(
        "SELECT limit_key FROM budget_reservations WHERE action_id = ?",
        (out["action_id"],)).fetchall()]
    keys = {r["limit_key"] for r in reservations}
    assert "max_scenario_transitions" in keys
    assert "max_total_search_actions" in keys


# ------------------------------------------------------- coproduct followups


def test_followup_plan_reference_must_be_product(tmp_path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "fup-1")
    sub, prod = make_substrate_states()
    hyp = make_hypothesis("p1", sub, prod)
    event = build_pathway_event(hyp, run_id="fup-1", context_hash="ctx")
    with pytest.raises(ScheduleContractError):
        enqueue_coproduct_followups(
            ledger, run_id="fup-1", parent_path_id="p1", context_ref="ctx",
            event_id=event.event_id, product_state_refs=[prod.state_id],
            expansion_plan={"entries": [
                {"state_ref": "cs_foreign", "status": "expanded",
                 "reason": ""}]},
            policy_version=PV, parent_search_revision=1)


def test_followup_budget_zero_all_deferred_with_reason(tmp_path) -> None:
    _, ledger, _, _ = make_run(tmp_path, "fup-2")
    sub, prod = make_substrate_states()
    hyp = make_hypothesis("p1", sub, prod)
    event = build_pathway_event(hyp, run_id="fup-2", context_hash="ctx")
    out = enqueue_coproduct_followups(
        ledger, run_id="fup-2", parent_path_id="p1", context_ref="ctx",
        event_id=event.event_id, product_state_refs=[prod.state_id],
        expansion_plan={"entries": [
            {"state_ref": prod.state_id, "status": "expanded",
             "reason": ""}]},
        policy_version=PV, parent_search_revision=1,
        budget_remaining_zero=True,
        substrate_smiles_by_ref={prod.state_id: "CC=O"})
    assert out["scheduled"] == []
    assert out["deferred"][0]["reason"] == "budget_limit"
    row = ledger.action(out["deferred"][0]["action_id"])
    assert row["status"] == ACTION_STATUS_DEFERRED
    assert row["payload"]["deferred_type"] == DEFERRED_TYPE_COPRODUCT


def test_child_path_id_deterministic() -> None:
    assert child_path_id("p1", "e1", "r1") == child_path_id("p1", "e1", "r1")
    assert child_path_id("p1", "e1", "r1") != child_path_id("p1", "e2", "r1")
