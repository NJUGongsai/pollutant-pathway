"""scripts/s5b_offline_funnel.py 准入枚举与 F 桶控制用例（T7）。

对应 chain12 丢分归因第一轮评审 P2（docs/S5B_CHAIN12_LOSS_ATTRIBUTION_ROUND1_
REVIEW_2026-10-12.md §4）：修复前工具读错准入枚举（rejected/deferred）且
classify() 无 F 分支，admission disposition=reject 被漏计、题目误归 I。
本文件全部为公开合成 payload 程序事实用例：不含真实批数据、金标、题面，
零模型零网络，不运行评测器。

用例：
1. reject 负控（漏计修复）：disposition=reject、selected=1、无事件
   → 拒绝计数=1 且主桶 F。
2. H 与候选损耗并存：一题有提交事件 + method_failed + dedup + 预算 defer
   并存 → 主桶 H，对应交集标志均 true（主桶单列、歧义进交集表）。
3. retain_conditional 正控：不计入拒绝合计、不落 F。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "s5b_offline_funnel.py"
_spec = importlib.util.spec_from_file_location("s5b_offline_funnel_test", _SCRIPT)
funnel = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(funnel)


def _case(qid="synthetic_public_q1"):
    return {
        "qid": qid,
        "run_id": "synthetic_public_run",
        "status": "completed",
        "stop_reason": "complete",
        "endpoint": {"execution_status": "completed"},
    }


def _metric():
    return {"main": {"match_status": "unmatched_required_node_uncovered"}}


def test_admission_reject_counts_and_lands_in_F():
    """负控：reject 准入被正确计数且题目落 F 桶（修复前：计数 0、主桶 I）。"""
    case = _case()
    case["stop_reason"] = "budget_limit"  # 两批真实批恒为 budget_limit，同口径
    payload = {
        "expansion_outcomes": [{
            "outcome_payload": {"outcome": {
                "kind": "scheduled",
                "detail": {"selected": 1,
                           "model": {"parsed_proposals": 1}},
            }},
        }],
        "audit_production_reports": [{
            "production_payload": {
                "status": "rejected",
                "admission": {"disposition": "reject"},
                "submitted": {"created": False},
            },
        }],
        "events": [],
    }
    f = funnel.extract_funnel(case, payload, {"pool_size": 1}, _metric())
    assert f["admission_dispositions"] == {"reject": 1}
    assert f["admission_rejected_or_deferred"] == 1
    bucket, why = funnel.classify(f)
    assert bucket == "F", why
    assert funnel.intersect_flags(f)["has_admission_reject_or_defer"] is True


def test_submitted_bucket_H_with_candidate_loss_intersection():
    """H 与候选级损耗并存：主桶仍 H，各损耗交集标志为 true。"""
    case = _case()
    payload = {
        "expansion_outcomes": [
            {"outcome_payload": {"outcome": {
                "kind": "scheduled",
                "detail": {
                    "selected": 2,
                    "deferred": 1,
                    "model": {
                        "parsed_proposals": 3,
                        "dedup_rejections": [
                            {"logical_proposal_id": "synthetic_duplicate"},
                        ],
                    },
                },
            }}},
            {"outcome_payload": {"outcome": {"kind": "method_failed"}}},
        ],
        "audit_production_reports": [
            {"production_payload": {"status": "method_failed",
                                    "admission": None}},
            {"production_payload": {
                "status": "submitted",
                "admission": {"disposition": "retain_conditional"},
                "submitted": {"created": True},
            }},
        ],
        "events": [{"event_id": "synthetic_event"}],
        "deferred_entries": [{"deferred_type": "hypothesis_deferred",
                              "reason": "alternatives_budget"}],
    }
    f = funnel.extract_funnel(case, payload, {"pool_size": 2}, _metric())
    bucket, why = funnel.classify(f)
    assert bucket == "H", why
    assert f["method_failed_productions"] == 1
    assert f["dedup_rejections"] == 1
    assert f["alternatives_budget_deferrals"] == 1
    flags = funnel.intersect_flags(f)
    assert flags["has_dedup_rejections"] is True
    assert flags["has_method_failed"] is True
    assert flags["has_alternatives_budget_defer"] is True


def test_retain_conditional_not_rejected_not_F():
    """正控：retain_conditional 不计入拒绝合计、不落 F。"""
    # (a) 有提交事件 → 主桶 H，拒绝合计 0
    case = _case()
    payload = {
        "expansion_outcomes": [{
            "outcome_payload": {"outcome": {
                "kind": "scheduled",
                "detail": {"selected": 1,
                           "model": {"parsed_proposals": 1}},
            }},
        }],
        "audit_production_reports": [{
            "production_payload": {
                "status": "submitted",
                "admission": {"disposition": "retain_conditional"},
                "submitted": {"created": True},
            },
        }],
        "events": [{"event_id": "synthetic_event"}],
    }
    f = funnel.extract_funnel(case, payload, {"pool_size": 1}, _metric())
    assert f["admission_dispositions"] == {"retain_conditional": 1}
    assert f["admission_rejected_or_deferred"] == 0
    bucket, _ = funnel.classify(f)
    assert bucket == "H"
    assert funnel.intersect_flags(f)["has_admission_reject_or_defer"] is False

    # (b) 无提交事件、仅 retain_conditional：不落 F（同口径落预算/未知侧，
        # 此处 stop=budget_limit → G），拒绝合计仍 0
    case2 = _case("synthetic_public_q2")
    case2["stop_reason"] = "budget_limit"
    payload2 = {
        "expansion_outcomes": [{
            "outcome_payload": {"outcome": {
                "kind": "scheduled",
                "detail": {"selected": 1,
                           "model": {"parsed_proposals": 1}},
            }},
        }],
        "audit_production_reports": [{
            "production_payload": {
                "status": "retain_conditional",
                "admission": {"disposition": "retain_conditional"},
                "submitted": {"created": False},
            },
        }],
        "events": [],
    }
    f2 = funnel.extract_funnel(case2, payload2, {"pool_size": 1}, _metric())
    assert f2["admission_rejected_or_deferred"] == 0
    bucket2, why2 = funnel.classify(f2)
    assert bucket2 != "F", why2
    assert funnel.intersect_flags(f2)["has_admission_reject_or_defer"] is False
