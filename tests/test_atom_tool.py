"""AtomTool — MoleCode 往返能力边界与编辑核验(任务书 §3)。

探明并固定表示能力:手性、电荷、芳香性、多组分可无损往返;同位素有损 →
必须拒绝(representation_lossy),不得以未经验证的 SMILES 替代。断键/成键
编辑经原子/键引用核验;vendor 子集完整性自检。
"""

from __future__ import annotations

import pytest
from rdkit import Chem

from pathway_v43.services.atom_tool import (
    AtomToolError,
    align_donor_mapping,
    check_edit_references,
    check_target_molecode,
    element_delta,
    execute_edits,
    molecode_to_smiles,
    parse_atom_ids,
    render,
    roundtrip,
    verify_vendor_integrity,
)


def _roundtrip_ok(smi: str) -> bool:
    r = roundtrip(smi)
    return r.canonical_smiles == Chem.MolToSmiles(Chem.MolFromSmiles(smi))


def test_vendor_integrity_self_check():
    """vendor 子集哈希自检通过(实现被改即 fail-closed)。"""
    info = verify_vendor_integrity()
    assert info["upstream_commit"].startswith("a4df3b04")
    assert len(info["files"]) == 7


def test_roundtrip_aromatic_and_phenol():
    assert _roundtrip_ok("Oc1ccccc1O")
    assert _roundtrip_ok("CC(=O)Oc1ccccc1C(=O)O")  # aspirin(芳香+酯)


def test_roundtrip_chirality_preserved():
    r = roundtrip("C[C@H](N)C(=O)O")
    assert "@" in r.canonical_smiles
    assert _roundtrip_ok("C[C@H](N)C(=O)O")
    assert _roundtrip_ok("C/C=C/C")  # E/Z 双键立体


def test_roundtrip_charge_preserved():
    assert _roundtrip_ok("C[NH3+]")
    assert _roundtrip_ok("CC(=O)[O-]")


def test_roundtrip_multicomponent_salt():
    assert _roundtrip_ok("CC(=O)[O-].[Na+]")


def test_roundtrip_isotope_is_lossy_and_refused():
    """探明的表示边界:同位素在 MoleCode 标签中丢失 → 往返身份不一致 → 拒。

    这是任务书要求的"有损即拒绝并给原因",不是支持能力。
    """
    with pytest.raises(AtomToolError) as ei:
        roundtrip("[13CH4]")
    assert ei.value.reason == "representation_lossy"


def test_render_exposes_stable_atom_ids():
    r = render("Oc1ccccc1O", name="Cat")
    ids = r.atom_ids
    assert ids, "必须有原子 ID"
    assert all(i.startswith("Cat_") for i in ids)
    assert set(ids) == parse_atom_ids(r.molecode)
    # 原子 ID ↔ RDKit idx 双向对照
    assert {v: k for k, v in r.atom_id_map.items()} == {
        int(k): v for k, v in r.idx_atom_map.items()
    }


def test_molecode_to_smiles_round_channel():
    r = render("Oc1ccccc1O")
    assert molecode_to_smiles(r.molecode) == r.canonical_smiles
    assert molecode_to_smiles("graph TB\n    garbage") is None  # 如实 None


def test_edit_reference_unknown_atom_rejected():
    r = roundtrip("Oc1ccccc1O")
    ok, reasons = check_edit_references(
        r, [{"op": "break_bond", "atom1": "M_O_1", "atom2": "Nope_C_9"}]
    )
    assert not ok
    assert any("unknown_atom:Nope_C_9" in x for x in reasons)


def test_edit_reference_bond_presence_checked():
    r = roundtrip("OCCO")  # 两个 C 成键,O-C 成键,O-O 不成键
    c_ids = [a for a in r.atom_ids if "_C_" in a]
    o_ids = [a for a in r.atom_ids if "_O_" in a]
    assert len(c_ids) == 2 and len(o_ids) == 2
    # 成键核验:已存在的键不能重复成键;不存在的键(O-O)可以成
    ok, reasons = check_edit_references(
        r, [{"op": "form_bond", "atom1": c_ids[0], "atom2": c_ids[1]}])
    assert not ok and any("bond_already_present" in x for x in reasons)
    ok, reasons = check_edit_references(
        r, [{"op": "break_bond", "atom1": o_ids[0], "atom2": o_ids[1]}])
    assert not ok and any("bond_not_present" in x for x in reasons)
    # 引用存在的键:断 O-C 合法
    ok, reasons = check_edit_references(
        r, [{"op": "break_bond", "atom1": o_ids[0], "atom2": c_ids[0]}])
    assert ok, reasons


def test_target_molecode_must_not_drop_atoms():
    r = roundtrip("OCCO")
    # 合法目标:原分子 + 一个新 O 节点(新 ID,无键)—— 原子 ID 全保留
    target = r.molecode.replace("    end", "        M_O_9[O]\n    end")
    verdict = check_target_molecode(r, target)
    assert verdict["ok"], verdict
    # 丢失原子:目标少了一个 O(M_O_2)→ 拒(产物 CCO 的 ID 集 = M_C_1/2 + M_O_1)
    shorter = roundtrip("CCO", name="M")
    verdict = check_target_molecode(r, shorter.molecode)
    assert not verdict["ok"]
    assert any("atom_removed:M_O_2" in x for x in verdict["reasons"])


def test_target_molecode_unparseable_rejected():
    r = roundtrip("OCCO")
    verdict = check_target_molecode(r, "this is not molecode")
    assert not verdict["ok"]
    assert verdict["reasons"][0].startswith("molecode_unparseable")


def test_align_donor_mapping_full_and_center():
    from rdkit import RDLogger

    RDLogger.DisableLog("rdApp.*")
    donor = Chem.MolFromSmiles("[OH:1][CH2:2][CH2:3][CH3:4]")
    current = Chem.MolFromSmiles("CCCCCCO")  # 供体是当前分子的子结构
    match, _ = align_donor_mapping(donor, current)
    assert match is not None and len(match) == 4
    # 映射原子 1(OH)应对到当前分子的 O
    cur_o = {a.GetIdx() for a in current.GetAtoms() if a.GetSymbol() == "O"}
    assert match[0] in cur_o
    # 中心子图对齐:center_atoms=[1,2](O-CH2 映射编号)子结构
    match2, _ = align_donor_mapping(donor, current, center_map_nums=[1, 2],
                                    center_only=True)
    assert match2 is not None and len(match2) == 2
    assert match2[0] in cur_o
    # 完全不相似(芳香氮杂环 vs 脂肪醇)→ 对齐失败 None
    assert align_donor_mapping(Chem.MolFromSmiles("c1ccncc1"),
                               current)[0] is None


def test_element_delta_counts_heavy_atoms():
    delta = element_delta("Oc1ccccc1", "Oc1ccccc1O")  # 苯酚 → 苯二酚:+O
    assert delta.get("O") == 1
    delta2 = element_delta("Oc1ccccc1O", "Oc1ccc(Cl)cc1O")  # 凭空 +Cl
    assert delta2.get("Cl") == 1
    assert element_delta("Oc1ccccc1O", "Oc1ccccc1O") == {}


def test_execute_edits_unknown_to_order_refused_not_raised():
    """S5b 冒烟回归(2026-10-09,RXNG_22901c/RXNG_330df2):模型按旧提示词
    词汇输出 to_order=aromatic,执行器为凯库勒空间、词表不含 aromatic——
    旧实现 ``_BOND_TOKENS[to]`` 抛 KeyError 逃逸,整题崩溃。现必须落结构化
    拒因 fail-closed(与 unknown_op 防御同模式),不抛异常。"""
    r = render("CCO", name="S")
    a1, a2 = sorted(r.atom_id_map)[:2]
    edits = [{"op": "change_bond_order", "atom1": a1, "atom2": a2,
              "from_order": "single", "to_order": "aromatic"}]
    execution = execute_edits(r, edits)  # 不得抛异常
    assert execution["ok"] is False
    assert any("bad_bond_order" in m and "to_aromatic" in m
               for m in execution["reasons"])
