"""v1.3 T1-C 机理排序规则单测（默认关闭、零漂移、触发条件）。"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pathway_v43.services.ranking_rules_v13 import (  # noqa: E402
    RANK_RULES_VERSION,
    RULE_COPRODUCT_COMPLETENESS,
    apply_v13_rank_rules,
)


def _rec(src, *, undeclared=(), raw_sim=0.0, prior=0.0, eff_rk=1):
    return {
        "src": src,
        "undeclared": list(undeclared),
        "raw_sim": raw_sim,
        "prior": prior,
        "eff_rk": eff_rk,
    }


def test_disabled_returns_same_list_object():
    top5 = [_rec("a", undeclared=["x"], prior=10.0),
            _rec("b", raw_sim=1.0, prior=80.0)]
    out, note = apply_v13_rank_rules(top5, enabled=False)
    assert out is not top5  # 列表浅拷贝，但顺序不变
    assert [c["src"] for c in out] == ["a", "b"]
    assert note["enabled"] is False
    assert note["promoted_src"] is None


def test_empty_or_single_candidate_unchanged():
    out, note = apply_v13_rank_rules([], enabled=True)
    assert out == []
    assert note["promoted_src"] is None
    single = [_rec("a", undeclared=["x"])]
    out, note = apply_v13_rank_rules(single, enabled=True)
    assert [c["src"] for c in out] == ["a"]
    assert note["promoted_src"] is None


def test_rule_promotes_exact_anchor_over_incomplete_weak_top1():
    top5 = [
        _rec("s5-weak", undeclared=["frag"], raw_sim=0.0, prior=90.0),
        _rec("tpl-mid", raw_sim=1.0, prior=70.0, eff_rk=2),
        _rec("tpl-low", raw_sim=0.99, prior=60.0, eff_rk=3),
        _rec("s5-other", raw_sim=0.0, prior=95.0, eff_rk=4),
    ]
    out, note = apply_v13_rank_rules(top5, enabled=True)
    assert [c["src"] for c in out] == [
        "tpl-mid", "s5-weak", "tpl-low", "s5-other"]
    assert note["promoted_src"] == "tpl-mid"
    assert note["triggered_rules"] == [RULE_COPRODUCT_COMPLETENESS]
    assert note["version"] == RANK_RULES_VERSION


def test_rule_no_trigger_when_top1_has_no_undeclared():
    top5 = [
        _rec("s5-clean", raw_sim=0.0, prior=90.0),
        _rec("tpl", raw_sim=1.0, prior=70.0),
    ]
    out, note = apply_v13_rank_rules(top5, enabled=True)
    assert [c["src"] for c in out] == ["s5-clean", "tpl"]
    assert note["promoted_src"] is None


def test_rule_no_trigger_when_top1_similarity_high():
    top5 = [
        _rec("s5-strong", undeclared=["frag"], raw_sim=0.85, prior=90.0),
        _rec("tpl", raw_sim=1.0, prior=70.0),
    ]
    out, note = apply_v13_rank_rules(top5, enabled=True)
    assert [c["src"] for c in out] == ["s5-strong", "tpl"]
    assert note["promoted_src"] is None


def test_rule_no_trigger_when_candidate_has_undeclared_or_low_sim():
    top5 = [
        _rec("s5-weak", undeclared=["frag"], raw_sim=0.0, prior=90.0),
        _rec("tpl-incomplete", undeclared=["frag"], raw_sim=1.0, prior=80.0),
        _rec("tpl-analog", raw_sim=0.90, prior=85.0),
    ]
    out, note = apply_v13_rank_rules(top5, enabled=True)
    assert [c["src"] for c in out] == [
        "s5-weak", "tpl-incomplete", "tpl-analog"]
    assert note["promoted_src"] is None


def test_rule_picks_highest_prior_among_qualified():
    top5 = [
        _rec("s5-weak", undeclared=["frag"], raw_sim=None, prior=90.0),
        _rec("tpl-a", raw_sim=0.95, prior=83.0, eff_rk=2),
        _rec("tpl-b", raw_sim=1.0, prior=83.0, eff_rk=3),
    ]
    out, note = apply_v13_rank_rules(top5, enabled=True)
    # 同先验时按 eff_rk（更靠前）取 tpl-a
    assert note["promoted_src"] == "tpl-a"
    assert [c["src"] for c in out] == ["tpl-a", "s5-weak", "tpl-b"]


def test_rule_respects_target_slots():
    top5 = [
        _rec("s5-weak", undeclared=["frag"], raw_sim=0.0, prior=90.0),
        _rec("tpl", raw_sim=1.0, prior=70.0),
        _rec("x2"), _rec("x3"), _rec("x4"),
    ]
    out, _ = apply_v13_rank_rules(top5, enabled=True, target_slots=3)
    assert len(out) == 3