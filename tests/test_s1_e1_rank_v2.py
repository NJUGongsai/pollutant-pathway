"""S1 E1(HIT60)协议臂测试 — 密度截断 / 提示词枚举一致性 / 开关身份。

E1_DESIGN §5.3/§5.4/§5.1(开关子项)的落地:

- 密度预算:单条 full SMILES >300 字符截字段留痕;单卡序列化 >1600
  字符按 DENSITY_DROP_ORDER 逐级裁,never-drop 字段(evidence_id/engine/
  condition/verification 聚合/product_identity)存活;截断全留痕;
  同输入重放同输出(确定性);
- 提示词一致性:ranker_v2.md 含 HOLD_KINDS 全部枚举值与完整 order 契约
  文本;prompt_versions() 四键(含 rank_candidates_v2);v2 装载
  ranker_v2.md、v1/analogy/novel 不变(单一事实源在代码,prompt 镜像);
- 开关:值域 fail-closed(v3/null/数字装配期 ValueError);取值进
  ModelSetup.identity_block()["policy"](跨配置 resume 拒绝链路);
- E1 臂配置纳入三臂 diff 纪律的部分在 test_s1_arm_switches.py。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.services.prediction import (  # noqa: E402
    DENSITY_DROP_ORDER,
    DENSITY_PER_CANDIDATE_CHAR_CAP,
    DENSITY_PRODUCT_SMILES_FULL_CHAR_CAP,
    HOLD_KINDS,
    _apply_density_cap,
    _rank_v2_candidate_card,
)
from wf_helpers import CATECHOL  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def _card(full_smiles: str, n_products: int = 1,
          identity: str | None = None) -> dict:
    """构造一张最小合格 recorded 证据卡(字段与检索卡同构)。

    identity:覆盖规范身份(默认由 full 重算;真实卡二者同源,夹具允许
    分离以单独驱动密度预算的各字段)。
    """
    from pathway_v43.domain.identity import cn_identity

    return {
        "evidence_id": "E-btX#r1",
        "source_id": "btX#r1",
        "kind": "recorded_reaction",
        "match_type": "exact_donor_cn_match",
        "condition_fit": "unknown",
        "retrieval_rank": 1,
        "score": 0.71,
        "score_semantics": "eawag_lookup_tanimoto",
        "products": [
            {"position": i,
             "product_smiles": "CCO",
             "product_smiles_full": full_smiles,
             "product_identity": identity or (
                 cn_identity(full_smiles) or full_smiles),
             "ion_filtered": False,
             "cofactor_filtered": True}
            for i in range(n_products)
        ],
        "source_record": {"n_evidence": 4, "donor_exact_match": True},
        "asset_sources": [{"role": "recorded", "asset_file": "a.jsonl",
                           "asset_sha256": "0" * 64}],
    }


# ------------------------------------------------ 密度规则 1:full SMILES 上限


def test_overlong_full_smiles_dropped_with_trace():
    long_full = "C" * (DENSITY_PRODUCT_SMILES_FULL_CHAR_CAP + 1)
    card, drops = _rank_v2_candidate_card(_card(long_full), [])
    p = card["verification"]["products"][0]
    assert "product_smiles_full" not in p          # 截字段
    assert p["product_smiles"] == "CCO"            # 短形保留
    assert p["product_identity"]                   # 规范身份保留(决策键)
    assert drops == [{"field": "product_smiles_full",
                      "action": "dropped_over_char_cap",
                      "chars": len(long_full)}]


def test_full_smiles_at_cap_kept():
    ok_full = "C" * DENSITY_PRODUCT_SMILES_FULL_CHAR_CAP
    card, drops = _rank_v2_candidate_card(_card(ok_full), [])
    assert card["verification"]["products"][0][
        "product_smiles_full"] == ok_full
    assert all(d["field"] != "product_smiles_full" for d in drops)


# ------------------------------------------------ 密度规则 2:单卡预算逐级裁


def test_card_over_char_cap_cascades_drop_order_deterministic():
    # 构造一张超 1600 字符的卡:6 条 ≤300 字符合规 full SMILES 堆出超预算
    # (规范身份用短占位,单独驱动 full 字段的密度行为);裁到预算内
    full = "C" * 290
    e = _card(full, n_products=6,
              identity=None)  # identity 由下方逐产物短占位
    for i, p in enumerate(e["products"]):
        p["product_identity"] = f"cn-short-{i}"
    card, drops = _rank_v2_candidate_card(e, [])
    body = {k: v for k, v in card.items() if k != "density"}
    assert len(json_dumps(body)) <= DENSITY_PER_CANDIDATE_CHAR_CAP
    # never-drop 字段全部存活
    assert card["evidence_id"] and card["engine"]["reference_rank"] == 1
    assert card["condition"] == "unknown"
    assert card["verification"]["all_products_parse_ok"] in (True, False)
    assert all(p["product_identity"] for p in
               card["verification"]["products"])
    # 逐级裁顺序与 DENSITY_DROP_ORDER 前缀一致,留痕完整
    card_drops = [d["field"] for d in drops
                  if d.get("action") == "dropped_over_card_cap"]
    assert card_drops and card_drops == list(
        DENSITY_DROP_ORDER)[:len(card_drops)]
    # 确定性:同输入重放同输出
    e2 = _card(full, n_products=6)
    for i, p in enumerate(e2["products"]):
        p["product_identity"] = f"cn-short-{i}"
    card2, drops2 = _rank_v2_candidate_card(e2, [])
    assert json_dumps(card) == json_dumps(card2) and drops == drops2


def test_pathological_card_exhausts_drop_order_keeps_decision_fields():
    """never-drop 字段(规范身份)自身超预算的病态卡:逐级裁完整耗尽
    DENSITY_DROP_ORDER 后仍超帽也**不裁决策字段**(E1_DESIGN R3:卡间
    可区分性不因预算受损),全部截断留痕、结果确定性。"""
    full = "C" * 280
    e = _card(full, n_products=12)   # 真实形状:identity=cn(full),很长
    card, drops = _rank_v2_candidate_card(e, [])
    card_drops = [d["field"] for d in drops
                  if d.get("action") == "dropped_over_card_cap"]
    assert card_drops == list(DENSITY_DROP_ORDER)   # 三级全裁
    assert all(p["product_identity"] for p in
               card["verification"]["products"])    # 决策键仍在
    assert card["engine"]["reference_rank"] == 1 and card["condition"]
    card2, drops2 = _rank_v2_candidate_card(_card(full, n_products=12), [])
    assert json_dumps(card) == json_dumps(card2) and drops == drops2


def json_dumps(obj) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def test_apply_density_cap_never_drops_decision_fields():
    card = _card_like_big()
    drops: list[dict] = []
    _apply_density_cap(card, drops)
    assert "engine" in card and "condition" in card
    assert "verification" in card and "evidence_id" in card
    assert all("product_identity" in p
               for p in card["verification"]["products"])
    assert card["density"]["per_candidate_char_cap"] \
        == DENSITY_PER_CANDIDATE_CHAR_CAP
    assert card["density"]["truncated"] is drops


def _card_like_big() -> dict:
    """绕过 full-SMILES 规则、直接构造超卡上限的四层卡(单测预算函数)。"""
    filler = "C" * 260
    products = [{"position": i, "product_smiles": "CCO",
                 "product_smiles_full": filler,
                 "product_identity": f"cn-{i}",
                 "parse_ok": True, "identity_match": True,
                 "ion_filtered": False, "cofactor_filtered": False}
                for i in range(10)]
    return {
        "evidence_id": "E-btY#r2", "engine": {"reference_rank": 2,
                                              "score": 0.5,
                                              "score_semantics": "s"},
        "source": {"source_id": "btY#r2", "n_evidence": 9},
        "condition": "unknown",
        "verification": {"products": products,
                         "all_products_parse_ok": True,
                         "all_identity_match": True,
                         "any_in_path_cycle": False},
    }


# ------------------------------------------------ 提示词与枚举一致性(镜像锁)


def test_prompt_versions_has_four_keys_including_v2():
    from pathway_v43.adapters.llm_client import prompt_versions

    import hashlib

    root = REPO / "configs" / "prompts"
    pv = prompt_versions(root)
    assert set(pv) == {"rank_candidates", "rank_candidates_v2",
                       "analogy_edit", "novel_proposal"}
    v2_sha = hashlib.sha256(
        (root / "ranker_v2.md").read_bytes()).hexdigest()
    assert pv["rank_candidates_v2"] == v2_sha
    assert pv["rank_candidates"] != v2_sha   # 两版提示词必然不同


def test_ranker_v2_prompt_mirrors_hold_kinds_and_order_contract():
    text = (REPO / "configs" / "prompts" / "ranker_v2.md").read_text(
        encoding="utf-8")
    for kind in HOLD_KINDS:
        assert kind in text, f"枚举值 {kind} 未出现在 ranker_v2.md"
    # 完整 order 契约文本(漏卡即解析失败;hold 不得携带 order)
    assert "全部" in text and "order" in text
    assert "hold" in text and "不得携带" in text
    # 去锚定声明:引擎位次不是裁决结论
    assert "不是裁决" in text or "不是裁决结论" in text


def test_prompt_for_selects_by_presentation_switch():
    from pathlib import Path as _P

    from pathway_v43.services.prediction import RANK_PRESENTATION_V2
    from pathway_v43.workflow.nodes import _prompt_for

    class _Model:
        prompts_root = REPO / "configs" / "prompts"

    class _Svc:
        model = _Model()

    v2 = _prompt_for(_Svc(), "rank_candidates", RANK_PRESENTATION_V2)
    v1 = _prompt_for(_Svc(), "rank_candidates", "v1")
    assert v2 == (_P(REPO / "configs" / "prompts" / "ranker_v2.md")
                  ).read_text(encoding="utf-8")
    assert v1 == (_P(REPO / "configs" / "prompts" / "ranker.md")
                  ).read_text(encoding="utf-8")
    # 其余模式不受开关影响(同一文件)
    assert _prompt_for(_Svc(), "analogy_edit",
                       RANK_PRESENTATION_V2) == _prompt_for(
        _Svc(), "analogy_edit", "v1")


# ------------------------------------------------ 开关:值域 fail-closed + 身份


@pytest.mark.parametrize("bad", ["v3", "V2", "2", 2, 2.0, True, None, ""])
def test_rank_presentation_invalid_values_fail_closed(bad):
    """v3/大小写变体/数字/bool/null/空串一律装配期 ValueError,不静默回退。"""
    from pathway_v43.domain.policy import prediction_policy

    with pytest.raises(ValueError):
        prediction_policy({"rank_candidate_presentation": bad})


def test_rank_presentation_default_v1_and_v2_override():
    from pathway_v43.domain.policy import (
        PREDICTION_POLICY_DEFAULTS, prediction_policy,
    )

    assert PREDICTION_POLICY_DEFAULTS["rank_candidate_presentation"] == "v1"
    assert prediction_policy()["rank_candidate_presentation"] == "v1"
    pol = prediction_policy({"rank_candidate_presentation": "v2"})
    assert pol["rank_candidate_presentation"] == "v2"


def test_rank_presentation_enters_run_identity_and_rejects_resume():
    """开关取值进 prediction.policy;跨呈现版本 resume → IdentityMismatch。"""
    from pathway_v43.adapters.llm_client import resolve_model_setup
    from pathway_v43.storage.run_identity import (
        IdentityMismatch, build_run_identity, check_resume_identity,
        scripted_asset_identity,
    )

    setup_v1 = resolve_model_setup("fake", policy=prediction_policy_v1())
    setup_v2 = resolve_model_setup(
        "fake", policy=prediction_policy_v2())
    blk_v1 = setup_v1.identity_block()
    assert blk_v1["policy"]["rank_candidate_presentation"] == "v1"
    assert setup_v2.identity_block()["policy"][
        "rank_candidate_presentation"] == "v2"

    def ident(blk):
        return build_run_identity(
            run_id="r1", root_smiles=CATECHOL, root_cn=CATECHOL,
            strategy={"version": "v43-policy-1", "max_depth": 1,
                      "max_expansions": 1, "max_frontier_width": 5},
            asset_identity=scripted_asset_identity(),
            v3_code_identity={"git_commit": "x"},
            prediction=blk,
        )

    base = ident(blk_v1)
    check_resume_identity(base, ident(blk_v1))   # 同身份不抛
    with pytest.raises(IdentityMismatch) as ei:
        check_resume_identity(base, ident(setup_v2.identity_block()))
    assert "prediction" in ei.value.detail["differences"]


def prediction_policy_v1():
    from pathway_v43.domain.policy import prediction_policy

    return prediction_policy()


def prediction_policy_v2():
    from pathway_v43.domain.policy import prediction_policy

    return prediction_policy({"rank_candidate_presentation": "v2"})
