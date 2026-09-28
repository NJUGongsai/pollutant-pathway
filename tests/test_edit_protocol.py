"""AtomTool 编辑协议 v2(Phase C 任务书 §4/C2,验收 §6.2)。

核心断言:编辑在**真实分子图副本上按列表顺序执行**并逐步核验前提;
目标 MoleCode 独立解析后与执行结果图逐项对账(ID/元素/电荷/键/键级/
canonical SMILES),文本里正则搜到 ID 不算结构相符;
``bond_already_present`` 对 form_bond 仍是硬拒绝;一切失配 fail-closed。
"""

from __future__ import annotations

import pytest

from pathway_v43.services.atom_tool import (
    EDIT_PROTOCOL_VERSION,
    check_target_consistency,
    execute_edits,
    render,
    validate_edits,
)


def _ids(r, elem: str) -> list[str]:
    return sorted(a for a in r.atom_ids if f"_{elem}_" in a)


def _mol_line(r, atom_id: str) -> str:
    return f"        {atom_id}"


# ------------------------------------------------------------ 结构校验


def test_validate_accepts_protocol_ops():
    r = render("CCO", name="S")
    c = _ids(r, "C")
    v = validate_edits(r, [
        {"op": "change_bond_order", "atom1": c[1], "atom2": "S_O_1",
         "from_order": "single", "to_order": "double"},
        {"op": "break_bond", "atom1": c[0], "atom2": c[1]},
    ])
    assert v["ok"] and v["protocol_version"] == EDIT_PROTOCOL_VERSION


def test_validate_rejects_unknown_op_and_missing_fields():
    r = render("CCO", name="S")
    c = _ids(r, "C")
    # 未知操作(含旧协议的 remove_atom —— v2 明确废除)
    for op in ("remove_atom", "frobnicate", ""):
        v = validate_edits(r, [{"op": op, "atom1": c[0]}])
        assert not v["ok"]
        assert any("unknown_op" in x for x in v["reasons"])
    # change_bond_order 缺 from/to、非法键级
    v = validate_edits(r, [{"op": "change_bond_order", "atom1": c[1],
                            "atom2": "S_O_1", "to_order": "double"}])
    assert any("missing_field:from_order" in x for x in v["reasons"])
    v = validate_edits(r, [{"op": "change_bond_order", "atom1": c[1],
                            "atom2": "S_O_1", "from_order": "single",
                            "to_order": "quintuple"}])
    assert any("bad_bond_order" in x for x in v["reasons"])
    # 引用不存在原子
    v = validate_edits(r, [{"op": "break_bond", "atom1": c[0],
                            "atom2": "Nope_C_9"}])
    assert any("unknown_atom:Nope_C_9" in x for x in v["reasons"])


def test_validate_new_atom_id_rules():
    r = render("CCO", name="S")
    anchor = _ids(r, "C")[0]
    # 缺 new_atom_id
    v = validate_edits(r, [{"op": "add_atom", "element": "O",
                            "atom1": anchor}])
    assert any("missing_field:new_atom_id" in x for x in v["reasons"])
    # ID 内嵌元素与声明不一致
    v = validate_edits(r, [{"op": "add_atom", "element": "O",
                            "atom1": anchor, "new_atom_id": "S_N_9"}])
    assert any("new_atom_id_element_mismatch" in x for x in v["reasons"])
    # 与既有 ID 冲突
    existing = _ids(r, "O")[0]
    v = validate_edits(r, [{"op": "add_atom", "element": "O",
                            "atom1": anchor, "new_atom_id": existing}])
    assert any("new_atom_id_conflict" in x for x in v["reasons"])
    # 列表内重复
    v = validate_edits(r, [
        {"op": "add_atom", "element": "O", "atom1": anchor,
         "new_atom_id": "S_O_9"},
        {"op": "add_atom", "element": "O", "atom1": anchor,
         "new_atom_id": "S_O_9"}])
    assert any("new_atom_id_conflict" in x for x in v["reasons"])
    # 合法新 ID 通过
    v = validate_edits(r, [{"op": "add_atom", "element": "O",
                            "atom1": anchor, "new_atom_id": "S_O_9"}])
    assert v["ok"]


# ------------------------------------------------------------ 顺序执行


def test_change_bond_order_both_directions():
    # SINGLE→DOUBLE:乙醇→乙醛
    r = render("CCO", name="S")
    c = _ids(r, "C")
    o = _ids(r, "O")[0]
    e = execute_edits(r, [{"op": "change_bond_order", "atom1": c[1],
                           "atom2": o, "from_order": "single",
                           "to_order": "double"}])
    assert e["ok"] and e["product_smiles"] == "CC=O"
    # DOUBLE→SINGLE:乙醛→乙醇
    r2 = render("CC=O", name="S")
    e2 = execute_edits(r2, [{"op": "change_bond_order",
                             "atom1": _ids(r2, "C")[1],
                             "atom2": _ids(r2, "O")[0],
                             "from_order": "double", "to_order": "single"}])
    assert e2["ok"] and e2["product_smiles"] == "CCO"


def test_form_bond_on_existing_bond_still_hard_rejected():
    """``bond_already_present`` 仍是 form_bond 的硬拒绝 —— 不得通过忽略
    该错误放行单→双键;键级变化必须显式 change_bond_order。"""
    r = render("CCO", name="S")
    c = _ids(r, "C")
    o = _ids(r, "O")[0]
    e = execute_edits(r, [{"op": "form_bond", "atom1": c[1], "atom2": o}])
    assert not e["ok"]
    assert any("bond_already_present" in x for x in e["reasons"])
    assert e["product_smiles"] == ""  # 无产物(不假装成功)


def test_break_then_form_in_order_and_reverse_fails():
    """先断后成依序可行;反向顺序(先成后断同键)在成键步即拒。"""
    r = render("COC", name="S")
    c = _ids(r, "C")
    o = _ids(r, "O")[0]
    # 顺序:断 O-C2 → 成 C1-C2(新环外连接)
    e = execute_edits(r, [
        {"op": "break_bond", "atom1": o, "atom2": c[1]},
        {"op": "form_bond", "atom1": c[0], "atom2": c[1]},
    ])
    assert e["ok"], e["reasons"]
    # 反向:不先断,直接把同一对 C2–O 重复成键 → 拒
    e2 = execute_edits(r, [
        {"op": "form_bond", "atom1": o, "atom2": c[1]},
    ])
    assert not e2["ok"]
    assert any("bond_already_present" in x for x in e2["reasons"])


def test_break_nonexistent_and_add_atom_execution():
    r = render("CCO", name="S")
    c = _ids(r, "C")
    # 断不存在的键
    e = execute_edits(r, [{"op": "break_bond", "atom1": c[0],
                           "atom2": "S_O_1"}])
    assert not e["ok"]
    assert any("bond_not_present" in x for x in e["reasons"])
    # 新原子引用:挂到既有原子上,ID 入图
    e2 = execute_edits(r, [{"op": "add_atom", "element": "O",
                            "atom1": c[0], "new_atom_id": "S_O_9"}])
    assert e2["ok"]
    assert "S_O_9" in e2["atom_id_map"]
    assert e2["product_smiles"] == "OCCO"  # 乙二醇骨架


def test_illegal_valence_fails_at_sanitize():
    """价态非法:O 已两键再成键 → sanitize 失败 fail-closed。"""
    r = render("COC", name="S")
    o = _ids(r, "O")[0]
    e = execute_edits(r, [
        {"op": "form_bond", "atom1": _ids(r, "C")[0],
         "atom2": _ids(r, "C")[1]}])
    # C0–C1 成键后 O 仍两键 —— 这是合法的(环氧乙烷骨架)
    assert e["ok"], e["reasons"]
    # 真正价态崩溃:醚 O 上再加一个键(三键 O)
    e2 = execute_edits(r, [{"op": "add_atom", "element": "C",
                            "atom1": _ids(r, "C")[0],
                            "new_atom_id": "S_C_9"},
                           {"op": "form_bond", "atom1": "S_C_9",
                            "atom2": o}])
    # O 现有三根键且为中性 → sanitize 失败或价态异常 → 拒
    assert not e2["ok"] or e2["product_smiles"] == ""


# ------------------------------------------------------------ 目标对账


def test_target_consistency_matches_execution():
    r = render("CCO", name="S")
    c = _ids(r, "C")
    target = render("CC=O", name="S").molecode
    e = execute_edits(r, [{"op": "change_bond_order", "atom1": c[1],
                           "atom2": _ids(r, "O")[0],
                           "from_order": "single", "to_order": "double"}])
    t = check_target_consistency(r, e, target)
    assert t["ok"] and t["target_smiles"] == "CC=O"


def test_target_vs_edits_mismatch_rejected():
    """目标与编辑不符 → target_edit_mismatch(不止解析成功)。"""
    r = render("CCO", name="S")
    c = _ids(r, "C")
    e = execute_edits(r, [{"op": "change_bond_order", "atom1": c[1],
                           "atom2": _ids(r, "O")[0],
                           "from_order": "single", "to_order": "double"}])
    # 目标:丙醛(多一个 C)—— ID 集与执行结果不同
    bad = render("CCC=O", name="S").molecode
    t = check_target_consistency(r, e, bad)
    assert not t["ok"]
    assert any("target_edit_mismatch" in x for x in t["reasons"])
    # 目标:同原子但键级未变(乙醇)—— canonical 不一致
    bad2 = render("CCO", name="S").molecode
    t2 = check_target_consistency(r, e, bad2)
    assert not t2["ok"]


def test_forged_atom_id_in_text_fails():
    """文本伪造 ID:目标文本声明了执行图里不存在的新原子 ID。"""
    r = render("CCO", name="S")
    c = _ids(r, "C")
    e = execute_edits(r, [{"op": "change_bond_order", "atom1": c[1],
                           "atom2": _ids(r, "O")[0],
                           "from_order": "single", "to_order": "double"}])
    # 在目标文本里塞一个执行图中不存在的原子节点(伪造成功假象)
    forged = e["product_smiles"]  # CC=O(执行图,2C1O)
    target = render(forged, name="S").molecode.replace(
        "    end", "        S_Cl_9[Cl]\n    end")
    t = check_target_consistency(r, e, target)
    assert not t["ok"]
    assert any("atom_id_sets_differ" in x for x in t["reasons"])


def test_charge_and_element_difference_rejected():
    """电荷/元素差异 fail-closed:执行图 N vs 目标 N(+)/不同元素。"""
    r = render("CN", name="S")
    e = execute_edits(r, [])  # 空 编辑:执行图=当前(用于对账差异)
    # 目标带电:目标 [NH3+]C 与中性执行图电荷不一致
    target = render("C[NH3+]", name="S").molecode
    t = check_target_consistency(r, e, target)
    assert not t["ok"]
    assert any("target_edit_mismatch:formal_charge" in x
               for x in t["reasons"])
    # 元素差异:目标把 O 换成 S(ID 内嵌元素随之变化)
    r2 = render("CO", name="S")
    e2 = execute_edits(r2, [])
    target2 = render("CS", name="S").molecode
    t2 = check_target_consistency(r2, e2, target2)
    assert not t2["ok"]
    assert any("mapping_inconsistent:atom_removed" in x
               or "target_edit_mismatch:element" in x
               for x in t2["reasons"])


def test_unparseable_target_rejected():
    r = render("CCO", name="S")
    e = execute_edits(r, [])
    t = check_target_consistency(r, e, "this is not molecode")
    assert not t["ok"]
    assert t["reasons"][0].startswith("molecode_unparseable")


# ---------------------------------------------------- Phase C R3 补钉


def test_validate_rejects_fake_element_and_execute_stays_structured():
    """P1-3:形似元素的 ``Xx`` 必须在预校验被拒(周期表事实源);即使绕过
    校验直调执行器,也必须返回结构化 rejected,不得抛未捕获异常。"""
    r = render("CCO", name="S")
    edits = [{"op": "add_atom", "atom1": "S_C_1", "element": "Xx",
              "new_atom_id": "S_Xx_1"}]
    v = validate_edits(r, edits)
    assert not v["ok"]
    assert any("edit_invalid:bad_element" in x for x in v["reasons"])
    # 执行层防御(双层 fail-closed):同输入直调 → 结构化拒因而非 RuntimeError
    e = execute_edits(r, edits)
    assert not e["ok"]
    assert any("edit_execution_failed:bad_element:Xx" in x
               for x in e["reasons"])
    # 通配哑原子 "*" 同样拒绝(add_atom 不造占位原子)
    v2 = validate_edits(r, [{"op": "add_atom", "atom1": "S_C_1",
                             "element": "*", "new_atom_id": "S_X_1"}])
    assert not v2["ok"]
    assert any("edit_invalid:bad_element" in x for x in v2["reasons"])


def test_add_atom_then_reference_in_later_edit_is_valid():
    """先增后引:add_atom 声明的新 ID 可被后续操作引用(与执行器的列表
    时点语义一致);引用先于声明的 ID 仍按 unknown_atom 拒。"""
    r = render("CCO", name="S")
    edits = [
        {"op": "add_atom", "atom1": "S_C_1", "element": "O",
         "new_atom_id": "S_O_9"},
        {"op": "form_bond", "atom1": "S_O_9", "atom2": "S_C_2"},
    ]
    v = validate_edits(r, edits)
    assert v["ok"], v["reasons"]
    assert v["new_atom_ids"] == ["S_O_9"]
    e = execute_edits(r, edits)
    assert e["ok"], e["reasons"]
    # 反向时序:引用先于声明 → 拒
    v2 = validate_edits(r, [
        {"op": "form_bond", "atom1": "S_O_8", "atom2": "S_C_2"},
        {"op": "add_atom", "atom1": "S_C_1", "element": "O",
         "new_atom_id": "S_O_8"},
    ])
    assert not v2["ok"]
    assert any("unknown_atom:S_O_8" in x for x in v2["reasons"])


def test_validate_rejects_undeclared_fields_and_legacy_aliases():
    """R2 复核 P2:编辑协议 v2 严格四操作 —— 未声明字段
    (edit_invalid:unknown_field)与旧别名 remove_bond/add_bond
    (edit_invalid:unknown_op)一律显式拒绝,不再宽松接受。"""
    r = render("CCO", name="S")
    # add_atom 带未声明字段
    v = validate_edits(r, [{"op": "add_atom", "atom1": "S_C_1",
                            "element": "O", "new_atom_id": "S_O_9",
                            "unexpected": "ignore_me"}])
    assert not v["ok"]
    assert any("edit_invalid:unknown_field:unexpected" in x
               for x in v["reasons"])
    # change_bond_order 带未声明字段
    c = _ids(r, "C")
    v2 = validate_edits(r, [{"op": "change_bond_order", "atom1": c[1],
                             "atom2": "S_O_1", "from_order": "single",
                             "to_order": "double", "note": "why"}])
    assert not v2["ok"]
    assert any("edit_invalid:unknown_field:note" in x for x in v2["reasons"])
    # 旧别名按未知操作拒
    for op in ("remove_bond", "add_bond"):
        v3 = validate_edits(r, [{"op": op, "atom1": c[0], "atom2": c[1]}])
        assert not v3["ok"]
        assert any(f"edit_invalid:unknown_op:{op}" in x
                   for x in v3["reasons"])
    # 四操作的合法最小字段集仍然通过(不因严格化误伤)
    ok = validate_edits(r, [
        {"op": "break_bond", "atom1": c[0], "atom2": c[1]},
    ])
    assert ok["ok"], ok["reasons"]
