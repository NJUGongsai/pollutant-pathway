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


# ------------------------------------------------ fable5 P1c 拒因枚举钉住
#
# 评审 §1.1[P1]/§7-3:domain/policy 的类比回退判据与 services/
# donor_applicability 的拒因产出曾靠字面量隐性对齐。现单一事实源在
# domain/models(DONOR_FALLBACK_*),产出方与消费方共用 —— 本节逐值钉住
# "每个拒因枚举值 → decide_prediction_route 对应分支"的映射,并钉住
# 两侧常量集合相等(任一侧改值/加值都必须有意识地同时改这里)。

from pathway_v43.domain.models import (  # noqa: E402
    DONOR_FALLBACK_APPLICABILITY_FAILED,
    DONOR_FALLBACK_APPLICABILITY_UNKNOWN,
    DONOR_FALLBACK_COMPETING_TRANSFORMS,
    DONOR_FALLBACK_MAPPING_AMBIGUOUS,
    DONOR_FALLBACK_NO_MAPPING,
    DONOR_FALLBACK_REASONS,
)
from pathway_v43.domain.policy import (  # noqa: E402
    PREDICTION_MODE_ANALOGY,
    PREDICTION_MODE_NOVEL,
    _ANALOGY_FALLBACKS,
    decide_prediction_route,
    prediction_policy,
)
from pathway_v43.services.donor_applicability import (  # noqa: E402
    EMITTED_FALLBACK_REASONS,
    FALLBACK_APPLICABILITY_FAILED,
    FALLBACK_APPLICABILITY_UNKNOWN,
    FALLBACK_COMPETING_TRANSFORMS,
    FALLBACK_MAPPING_AMBIGUOUS,
    FALLBACK_NO_MAPPING,
)


def _analog_card(*, with_refs: bool = False) -> dict:
    extra = {"donor_refs": [{"record_id": "r1", "asset_sha256": "h",
                             "line_no": 1}]} if with_refs else None
    return evidence("E-analog", "analog_reaction", CN, ["CC(O)=O"],
                    match_type="other", extra=extra)


def _elig(status: str, fallback: str) -> dict:
    return {"status": status, "fallback_reason": fallback,
            "selected": None}


def test_fallback_constants_single_source():
    """产出方(services)与消费方(domain)共用同一常量集合 —— 逐字面量
    钉住:policy 接受集 == models 全集 == donor_applicability 产出值域。"""
    assert set(DONOR_FALLBACK_REASONS) == {
        "no_mapping", "mapping_ambiguous", "applicability_failed",
        "applicability_unknown", "multiple_competing_transforms",
    }
    assert set(_ANALOGY_FALLBACKS) == set(DONOR_FALLBACK_REASONS)
    assert EMITTED_FALLBACK_REASONS == set(DONOR_FALLBACK_REASONS)
    # 产出方别名与常量逐一同值(字面量即落盘机读码,不得漂移)
    assert FALLBACK_NO_MAPPING == DONOR_FALLBACK_NO_MAPPING
    assert FALLBACK_MAPPING_AMBIGUOUS == DONOR_FALLBACK_MAPPING_AMBIGUOUS
    assert FALLBACK_APPLICABILITY_FAILED == DONOR_FALLBACK_APPLICABILITY_FAILED
    assert FALLBACK_APPLICABILITY_UNKNOWN == DONOR_FALLBACK_APPLICABILITY_UNKNOWN
    assert FALLBACK_COMPETING_TRANSFORMS == DONOR_FALLBACK_COMPETING_TRANSFORMS


def test_route_each_fallback_value_pinned():
    """每个拒因枚举值 → 受约束 novel(带该拒因)或显式停留(<值>_hold)。"""
    for value in DONOR_FALLBACK_REASONS:
        elig = _elig("inapplicable", value)
        mode, reason = decide_prediction_route(
            "awaiting_prediction", [_analog_card()], CN, prediction_policy(),
            model_enabled=True, llm_remaining=5, proposals_remaining=5,
            eligibility=elig)
        assert mode == PREDICTION_MODE_NOVEL, (value, mode)
        assert reason.startswith(f"{value}:"), (value, reason)
        pol = prediction_policy({"allow_novel_on_mapping_failure": False})
        mode, reason = decide_prediction_route(
            "awaiting_prediction", [_analog_card()], CN, pol,
            model_enabled=True, llm_remaining=5, proposals_remaining=5,
            eligibility=elig)
        assert mode == "" and reason == f"{value}_hold", (value, reason)


def test_route_inferred_fallback_paths():
    """资格块未评估(纯函数直调)时的回退触发路径:有 donor_refs →
    applicability_unknown;无 refs → no_mapping(枚举常量,非字面量)。"""
    mode, reason = decide_prediction_route(
        "awaiting_prediction", [_analog_card(with_refs=True)], CN,
        prediction_policy(), model_enabled=True, llm_remaining=5,
        proposals_remaining=5)
    assert mode == PREDICTION_MODE_NOVEL
    assert reason.startswith(f"{DONOR_FALLBACK_APPLICABILITY_UNKNOWN}:")
    mode, reason = decide_prediction_route(
        "awaiting_prediction", [_analog_card()], CN, prediction_policy(),
        model_enabled=True, llm_remaining=5, proposals_remaining=5)
    assert mode == PREDICTION_MODE_NOVEL
    assert reason.startswith(f"{DONOR_FALLBACK_NO_MAPPING}:")
    pol = prediction_policy({"allow_novel_on_mapping_failure": False})
    _, reason = decide_prediction_route(
        "awaiting_prediction", [_analog_card()], CN, pol,
        model_enabled=True, llm_remaining=5, proposals_remaining=5)
    assert reason == f"{DONOR_FALLBACK_NO_MAPPING}_hold"


def test_route_applicable_donor_to_analogy():
    """通过适用性门禁 → analogy_edit(拒因枚举之外的正向分支钉住)。"""
    elig = {"status": "applicable", "fallback_reason": "",
            "selected": {"record_id": "r1", "evidence_id": "E-analog"}}
    mode, reason = decide_prediction_route(
        "awaiting_prediction", [_analog_card()], CN, prediction_policy(),
        model_enabled=True, llm_remaining=5, proposals_remaining=5,
        eligibility=elig)
    assert mode == PREDICTION_MODE_ANALOGY and "applicable_donor" in reason
