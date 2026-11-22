"""v1.3 T4-A 小修补单测（零调用）。

覆盖三个默认关闭的开关：

1. ``enable_v13_stereo_dissolution_extended`` —— ``_is_stereo_dissolution``
   扩展面（断键/芳香化后手性标签消失），以及「新成键落中心一律不消解」
   的负控；
2. ``enable_v13_declared_product_consistency`` —— ``_declared_consistency_report``
   严格身份多重集包含（正/负控）；
3. ``enable_v13_tolerant_model_parse`` —— ``parse_model_proposals(
   drop_invalid_proposals=True)`` 逐条容错（一坏一合法是正控；全坏与
   顶层结构错误仍抛；关闭时返回键集合与改前逐字同）。

只测纯逻辑，不跑完整 runflow（重放正控由 ``v13_t1b_replay.py`` 覆盖）。
"""

from __future__ import annotations

import pytest

from pathway_v43.pollutant.model_protocol import (
    ModelProtocolError,
    parse_model_proposals,
)
from pathway_v43.pollutant.runflow import _declared_consistency_report
from pathway_v43.pollutant import s5b_compiler as _compiler
from pathway_v43.pollutant.s5b_compiler import (
    extract_mapped_transform,
)


# ---------------------------------------------------------------- A1 立体


def _transform(lhs: str, rhs: str, *, extended: bool):
    return extract_mapped_transform(
        lhs, rhs, extended_stereo_dissolution=extended)


def test_stereo_dissolution_break_bond_base_rejects_extended_accepts():
    """断键让手性 sp3 碳变成 CH2：默认关 ⇒ 不消解（落 stereo_changed）；开 ⇒ 消解。"""
    lhs = "[C@@H:1]([CH3:2])([CH2:3])[OH:4]"
    rhs = "[CH2:1]([CH3:2])[CH2:3].[OH2:4]"
    base = _transform(lhs, rhs, extended=False)
    assert base["stereo_dissolved_maps"] == []
    assert 1 in base["stereo_changed_maps"]

    ext = _transform(lhs, rhs, extended=True)
    assert ext["stereo_dissolved_maps"] == [1]
    assert 1 not in ext["stereo_changed_maps"]


def test_stereo_dissolution_new_bond_to_center_still_rejected():
    """扩展面不放行新成键落中心（手性生成/改写不是派生消解）。

    键变化表直接构造：谓词只核 ``order_lhs``/``order_rhs`` 与 lhs 手性/
    键级，不交叉核表(表由同一映射提取产生)。四价碳上加第 5 根键的
    SMILES 本身不可解析,故此处不走 SMILES 路径。
    """
    lhs = _compiler._parse_mapped_side(
        "[C@@H:1]([CH3:2])([CH2:3])[OH:4]", "lhs")
    rhs = _compiler._parse_mapped_side(
        "[CH2:1]([CH3:2])[CH2:3].[OH2:4]", "rhs")
    formed = [{"map1": 1, "map2": 2,
               "order_lhs": _compiler._NONE, "order_rhs": "single"}]
    assert _compiler._is_stereo_dissolution(
        lhs, rhs, 1, formed, extended=True) is False
    broken = [{"map1": 1, "map2": 2,
               "order_lhs": "single", "order_rhs": _compiler._NONE}]
    assert _compiler._is_stereo_dissolution(
        lhs, rhs, 1, broken, extended=True) is True


def test_stereo_dissolution_pure_flip_without_bond_change_rejected():
    """纯立体翻转（无键变化）在扩展面同样不消解。"""
    lhs = _compiler._parse_mapped_side(
        "[C@@H:1]([CH3:2])([CH2:3])[OH:4]", "lhs")
    rhs = _compiler._parse_mapped_side(
        "[C:1]([CH3:2])([CH2:3])[OH:4]", "rhs")
    assert _compiler._is_stereo_dissolution(
        lhs, rhs, 1, [], extended=True) is False


def test_stereo_dissolution_bond_order_change_unchanged_by_extension():
    """既有 sp3→sp2 消解面在扩展开关下判据不变。"""
    lhs = "[C@@H:1]([CH3:2])([CH3:3])[OH:4]"
    rhs = "[C:1]([CH3:2])([CH3:3])=[O:4]"
    for extended in (False, True):
        out = _transform(lhs, rhs, extended=extended)
        assert out["stereo_dissolved_maps"] == [1], extended


def test_extended_disabled_by_default_raises_same_code():
    """默认参数（不传开关）与显式 False 路径一致。"""
    lhs = "[C@@H:1]([CH3:2])([CH2:3])[OH:4]"
    rhs = "[CH2:1]([CH3:2])[CH2:3].[OH2:4]"
    default = extract_mapped_transform(lhs, rhs)
    explicit = _transform(lhs, rhs, extended=False)
    for key in ("retained_maps", "added_maps", "removed_maps",
                "bond_changes", "charge_changed_maps",
                "stereo_changed_maps", "stereo_dissolved_maps"):
        assert default[key] == explicit[key], key


# ------------------------------------------------ A3 声明产物一致性披露


def _prepared(*smiles: str):
    from types import SimpleNamespace
    return {"product_states": [SimpleNamespace(smiles_isomeric=s)
                               for s in smiles]}


def test_declared_consistency_exact_multiset_covered():
    rep = _declared_consistency_report(
        _prepared("CCO", "O"), "CCO", ["O"],
        {"product_smiles": "CCO", "coproducts": []})
    assert rep["covered"] is True
    assert rep["reason"] == "covered"
    assert rep["stored_products"] == ["CCO", "O"]


def test_declared_consistency_substituted_coproduct_not_covered():
    """落库产物里没有声明的那条（被换成别的结构）⇒ 不覆盖（只披露）。"""
    rep = _declared_consistency_report(
        _prepared("CCO", "CC=O"), "CCO", ["O"], {})
    assert rep["covered"] is False
    assert rep["reason"] == "declared_component_not_stored"
    assert rep["missing_component"] == "O"


def test_declared_consistency_missing_principal_not_covered():
    rep = _declared_consistency_report(
        _prepared("CC=O", "O"), "CCO", ["O"], {})
    assert rep["covered"] is False


def test_declared_consistency_multiset_count_enforced():
    """多重集：声明两份 O 时落库只有一份 ⇒ 不覆盖。"""
    ok = _declared_consistency_report(
        _prepared("CCO", "O", "O"), "CCO", ["O", "O"], {})
    assert ok["covered"] is True
    bad = _declared_consistency_report(
        _prepared("CCO", "O"), "CCO", ["O", "O"], {})
    assert bad["covered"] is False


def test_declared_consistency_unparseable_fail_closed():
    bad = _declared_consistency_report(
        _prepared("not-a-smiles"), "CCO", [], {})
    assert bad["covered"] is False
    assert bad["reason"] == "stored_identity_failed"
    empty = _declared_consistency_report(_prepared(), "", [], {})
    assert empty["covered"] is False
    assert empty["reason"] == "no_declared_components"


# ------------------------------------------------ A2 逐条容错解析


_ALLOWED = ["hyp_pool_a", "hyp_pool_b"]


def _resp(items, rank=None):
    payload = {"proposals": items}
    if rank is not None:
        payload["rank_hypotheses"] = rank
    import json

    return json.dumps(payload)


def test_tolerant_parse_keeps_valid_and_drops_invalid():
    bad = {"hypothesis_id": "hyp_outside"}  # 缺 proposal_context
    good = {"hypothesis_id": "hyp_pool_a"}
    with pytest.raises(ModelProtocolError):
        parse_model_proposals(
            _resp([bad, good], rank=["hyp_outside", "hyp_pool_a"]),
            allowed_hypothesis_ids=_ALLOWED)
    out = parse_model_proposals(
        _resp([bad, good], rank=["hyp_outside", "hyp_pool_a"]),
        allowed_hypothesis_ids=_ALLOWED, drop_invalid_proposals=True)
    assert [p["hypothesis_id"] for p in out["proposals"]] == ["hyp_pool_a"]
    assert out["rank_hypotheses"] == ["hyp_pool_a"]
    assert out["rank_dropped_ids"] == ["hyp_outside"]
    assert out["dropped_proposals"][0]["hypothesis_id"] == "hyp_outside"
    assert out["dropped_proposals"][0]["error_kind"] == "json_field_error"
    assert out["abstained"] is False


def test_tolerant_parse_all_invalid_is_abstained_not_crash():
    bad1 = {"hypothesis_id": "hyp_outside"}  # 缺 proposal_context
    bad2 = {"nope": 1}  # 缺 hypothesis_id
    out = parse_model_proposals(
        _resp([bad1, bad2]),
        allowed_hypothesis_ids=_ALLOWED, drop_invalid_proposals=True)
    assert out["proposals"] == []
    assert out["abstained"] is True
    assert len(out["dropped_proposals"]) == 2


def test_tolerant_parse_top_level_structure_still_raises():
    with pytest.raises(ModelProtocolError):
        parse_model_proposals(
            "not json at all",
            allowed_hypothesis_ids=_ALLOWED, drop_invalid_proposals=True)
    with pytest.raises(ModelProtocolError):
        parse_model_proposals(
            '{"proposals": "not-a-list"}',
            allowed_hypothesis_ids=_ALLOWED, drop_invalid_proposals=True)


def test_tolerant_parse_unknown_rank_id_still_raises():
    """rank 引用既非已接受、也非被丢弃的 ID ⇒ 仍是格式错误。"""
    with pytest.raises(ModelProtocolError):
        parse_model_proposals(
            _resp([{"hypothesis_id": "hyp_pool_a"}],
                  rank=["hyp_never_seen"]),
            allowed_hypothesis_ids=_ALLOWED, drop_invalid_proposals=True)


def test_off_path_return_keys_unchanged():
    """开关关闭 ⇒ 返回键集合与改前逐字同（无新增披露键）。"""
    out = parse_model_proposals(
        _resp([{"hypothesis_id": "hyp_pool_a"}]),
        allowed_hypothesis_ids=_ALLOWED)
    assert set(out) == {"proposals", "rank_hypotheses", "abstained",
                        "protocol_version"}


def test_duplicate_after_drop_is_accepted():
    """被丢弃条目的 ID 不占位：后续同名合法引用不被判重复。"""
    bad = {"hypothesis_id": "hyp_pool_a"}  # 缺 hypothesis_id? 不,这里合法
    # 构造:第一条引用池外 ID 缺 context ⇒ 丢弃;第二条同 ID 带合法 context
    outside = {"hypothesis_id": "hyp_novel", }
    outside_ok = {
        "hypothesis_id": "hyp_novel",
        "proposal_context": {"reference_hypothesis_ids": [],
                             "output_origin": "novel_outside_pool"},
        "reaction_spec": {
            "product_smiles": "CCO",
            "edits": [{"op": "add_atom", "element": "O",
                       "new_atom_id": "SN_O_1", "atom1": "S_C_1"}],
        },
    }
    out = parse_model_proposals(
        _resp([outside, outside_ok]),
        allowed_hypothesis_ids=_ALLOWED, drop_invalid_proposals=True)
    assert [p["hypothesis_id"] for p in out["proposals"]] == ["hyp_novel"]
    assert bad  # 仅为可读性占位,无断言