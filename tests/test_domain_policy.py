"""证据分级与选择策略纯函数(任务书 §1.3)—— 竞争反应不靠分数自动淘汰。"""

from __future__ import annotations

from pathway_v43.domain.identity import cn_identity
from pathway_v43.domain.policy import (
    classify_evidence,
    schedule_products,
    select_frontier,
    stop_reason,
)

from wf_helpers import CATECHOL, evidence

CN = cn_identity(CATECHOL)


def _recorded(rid="bt0001#r0001", **kw):
    return evidence(rid, "recorded_reaction", CN, ["CC(O)=O"], **kw)


def test_unique_recorded_commits():
    d = classify_evidence([_recorded()], "r", "p", CN)
    assert d.outcome == "commit_recorded"
    assert d.accepted_evidence_id == "E-bt0001#r0001"


def test_competing_recorded_awaits_without_score_elimination():
    a = _recorded("bt0001#r0001", rank=1, score=0.95)
    b = _recorded("bt0002#r0002", rank=2, score=0.30)
    d = classify_evidence([a, b], "r", "p", CN)
    assert d.outcome == "awaiting_prediction"
    assert "competitive" in d.reason and "2" in d.reason
    # 分数低的竞争反应不被淘汰:两张卡都在 considered 里
    assert {c["evidence_id"] for c in d.considered} == {a["evidence_id"], b["evidence_id"]}
    assert d.accepted_evidence_id is None


def test_rule_only_awaits_not_recorded():
    d = classify_evidence(
        [evidence("envipath-rule", "rule_application", CN, ["CC=O"],
                  match_type="rule_template")], "r", "p", CN)
    assert d.outcome == "awaiting_prediction"
    assert "only_rule_or_analog" in d.reason


def test_analog_only_awaits_not_recorded():
    d = classify_evidence(
        [evidence("corpus-neighbor", "analog_reaction", CN, ["CCO"],
                  match_type="retrieval_neighbor_transfer")], "r", "p", CN)
    assert d.outcome == "awaiting_prediction"


def test_condition_conflict_recorded_is_dead_end_with_reason():
    d = classify_evidence(
        [_recorded(condition_fit="conflict")], "r", "p", CN)
    assert d.outcome == "dead_end"
    assert "recorded_not_usable" in d.reason
    assert d.considered[0]["tier"] == "recorded_not_usable"


def test_unknown_condition_still_usable():
    d = classify_evidence([_recorded(condition_fit="unknown")], "r", "p", CN)
    assert d.outcome == "commit_recorded"


def test_no_evidence_dead_end():
    d = classify_evidence([], "r", "p", CN)
    assert d.outcome == "dead_end" and "no_evidence" in d.reason


def test_recorded_with_mismatched_substrate_not_usable():
    other = cn_identity("CCOc1ccccc1O")
    ev = _recorded()
    ev["query_identity"] = other
    ev["reactant_identity"] = other
    d = classify_evidence([ev], "r", "p", CN)
    assert d.outcome == "dead_end"


def test_select_frontier_budget_and_order():
    paths = [{"path_id": "p2", "depth": 1, "seq": 2},
             {"path_id": "p1", "depth": 0, "seq": 1}]
    # 预算未尽:按 seq 顺序选
    nxt, note = select_frontier(paths, 0, 3, 3)
    assert nxt["path_id"] == "p1"
    # 预算耗尽
    nxt, note = select_frontier(paths, 3, 3, 3)
    assert nxt is None and note == "budget_exhausted"


def test_select_frontier_skips_depth_capped():
    paths = [{"path_id": "pdeep", "depth": 2, "seq": 1}]
    nxt, _ = select_frontier(paths, 0, 3, 2)
    assert nxt is None


def test_schedule_products_width_defers_rest_in_order():
    prods = [{"position": i} for i in range(4)]
    expandable, deferred = schedule_products(prods, 2)
    assert [p["position"] for p in expandable] == [0, 1]
    assert [p["position"] for p in deferred] == [2, 3]


def test_stop_reason_priority():
    assert stop_reason(any_awaiting=True, used_expansions=0,
                       max_expansions=3, frontier_remaining=5) == "awaiting_prediction"
    assert stop_reason(any_awaiting=False, used_expansions=3,
                       max_expansions=3, frontier_remaining=2) == "budget_exhausted"
    assert stop_reason(any_awaiting=False, used_expansions=1,
                       max_expansions=3, frontier_remaining=0) == "completed"
