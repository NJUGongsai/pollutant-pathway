"""S5a 搭车 P2 常驻回归 —— R4 isotope_contract 已执行合成控制转常驻
(任务书授权:从 docs/review_evidence/ppv1_s4_codex_r4_2026-10-08/
isotope_contract/ 的脚本与 JSON 取口径写成常驻测试,不复制旧证据文件
进交付)。

口径来源(逐案对照 R4 §3/§3.1 执行数字):
- **对称四分案**(check_edit_against_donor 真实消费,非 raw matcher):
  ①无标对称断键 FCCF ⇒ True/symmetric_equivalent;②单 13C 破缺对称
  后的镜像断键 F[13CH2]CF ⇒ False(不能借图镜像放行);③双 13C 对称
  F[13CH2][13CH2]F ⇒ True/symmetric_equivalent(带标签仍合法对称的
  正控);④单 13C 背景上中心外新 isotope 差异 ⇒ False + extra_changes
  isotope(不被图镜像洗白);
- **raw matcher 方向控制**:FCCF 自匹配 2 / F[13CH2]CF 自匹配 1 /
  F[13CH2][13CH2]F 自匹配 2 / 带标 query 对无标 target 0 匹配;
- **标签方向控制**(真实 render→execute_edits→诊断→audit→admission):
  纯同位素且中心覆盖该原子 ⇒ verified/R6 expand;13→0 中心外 ⇒
  violated/R5v retain_conditional;[2H]OC→[3H]OC 同映射 D/T 差异中心
  外 ⇒ violated/R5v、中心内 ⇒ verified/R6(D/T 两轴结论不互推);
- **篡改拒绝**:混合案(真实 C–O 键变 + 中心外 S_C_1 合成 13C 标签)
  自报 center_match=True ⇒ audit 内部复算结构化拒绝
  (center_evidence_integrity_mismatch);
- **S5a 新披露(P2-2/P2-3,登记 donor-diagnostic-10)**:被增原子
  records 补 isotope 单侧值;audit center 检查 axis_detail 携带复算
  extra_changes/center_property_deltas(含 isotope before/after)。

固定 AtomTool 无 isotope op;合成输出防御验证不证明正常工具会改标签;
isotope 表示结构标签整数差异(0=未标),不断言样品实测同位素组成或
核过程(R4 §5 交接常驻披露)。
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
from rdkit import Chem

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.audit import (  # noqa: E402
    AuditContractError,
    CHECK_TRANSFORMATION_CENTER,
    audit_hypothesis,
    center_evidence_from_donor_diagnostic,
    check_edit_against_donor,
    decide_admission,
)
from pathway_v43.pollutant.chemstate import (  # noqa: E402
    build_chemical_state,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    Participant,
    build_hypothesis,
)
from pathway_v43.pollutant.path_context import (  # noqa: E402
    build_condition_fact,
    build_path_context,
    build_requirement,
)
from pathway_v43.services.atom_tool import (  # noqa: E402
    execute_edits,
    render,
)


# ---------------------------------------------------- raw matcher 方向控制


@pytest.mark.parametrize("smiles,n_matches", [
    ("FCCF", 2),
    ("F[13CH2]CF", 1),
    ("F[13CH2][13CH2]F", 2),
])
def test_symmetry_raw_self_matches(smiles: str, n_matches: int) -> None:
    """R4 §3.1 raw 控制:无标/双标对称恢复两个自同构;单标只剩恒等。"""
    mol = Chem.MolFromSmiles(smiles)
    matches = mol.GetSubstructMatches(
        mol, uniquify=False, useChirality=True, maxMatches=10000)
    assert len(matches) == n_matches


def test_labeled_query_unlabeled_target_no_match() -> None:
    """R4 §3.1 raw 控制:带标 query 对同骨架无标 target 无匹配。"""
    query = Chem.MolFromSmiles("F[13CH2]CF")
    target = Chem.MolFromSmiles("FCCF")
    matches = target.GetSubstructMatches(
        query, uniquify=False, useChirality=True, maxMatches=10000)
    assert matches == ()


# ---------------------------------------------------- 对称四分案


def _symmetry_case(smiles: str):
    rendered = render(smiles, name="S")
    ids = dict(rendered.atom_id_map)
    edits = [{"op": "break_bond", "atom1": "S_C_2", "atom2": "S_F_2"}]
    result = execute_edits(rendered, edits)
    assert result["ok"] is True, result
    current = {"smiles": rendered.smiles, "atom_id_map": ids}
    donor = {"center_atom_ids": ["d1", "d2"]}
    alignment = {"status": "resolved",
                 "donor_to_current": {"d1": "S_C_1", "d2": "S_F_1"},
                 "equivalence_classes": [],
                 "ref": "synthetic:s5a-resident:symmetry"}
    expectation = {"target_smiles": result["product_smiles"]}
    return check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation=expectation, result=result, edits=edits)


def test_symmetric_unlabeled_bond_break_center_true() -> None:
    """①无标对称断键:联合对称像放行(True/symmetric_equivalent)。"""
    diag = _symmetry_case("FCCF")
    assert diag.reaction_center_match is True
    assert diag.center_match_basis == "symmetric_equivalent"
    assert diag.strict_target_match is True
    assert diag.extra_changes == []


def test_asymmetric_label_blocks_mirror_center_false() -> None:
    """②单 13C 破缺对称:镜像断键不能借图镜像放行(False;中心外
    h_count 变化逐原子披露)。"""
    diag = _symmetry_case("F[13CH2]CF")
    assert diag.reaction_center_match is False
    assert diag.center_match_basis == ""
    assert diag.joint_mapping == {}
    assert diag.strict_target_match is True
    atoms = {entry["atom_id"] for entry in diag.extra_changes}
    assert "S_C_2" in atoms and "S_F_2" in atoms
    for entry in diag.extra_changes:
        assert "h_count" in entry["delta"]


def test_symmetric_double_label_keeps_mirror_center_true() -> None:
    """③双 13C 对称:带标签仍合法对称的正控保留(True)。"""
    diag = _symmetry_case("F[13CH2][13CH2]F")
    assert diag.reaction_center_match is True
    assert diag.center_match_basis == "symmetric_equivalent"
    assert diag.extra_changes == []


def test_asymmetric_label_outside_isotope_not_laundered() -> None:
    """④单 13C 背景上中心外新 isotope 差异:False + extra_changes
    isotope(图镜像不能洗白中心外同位素变化)。"""
    rendered = render("F[13CH2]CF", name="S")
    ids = dict(rendered.atom_id_map)
    result = execute_edits(rendered, [])
    assert result["ok"] is True
    mapped = Chem.MolFromSmiles(result["product_mapped_smiles"])
    atom = next(a for a in mapped.GetAtoms()
                if a.GetAtomMapNum() - 1 == ids["S_C_2"])
    atom.SetIsotope(13)
    plain = Chem.Mol(mapped)
    for a in plain.GetAtoms():
        a.SetAtomMapNum(0)
    result["product_mapped_smiles"] = Chem.MolToSmiles(mapped)
    result["product_smiles"] = Chem.MolToSmiles(plain)
    current = {"smiles": rendered.smiles, "atom_id_map": ids}
    donor = {"center_atom_ids": ["d1"]}
    alignment = {"status": "resolved", "donor_to_current": {"d1": "S_C_1"},
                 "equivalence_classes": [],
                 "ref": "synthetic:s5a-resident:outside-isotope"}
    expectation = {"target_smiles": result["product_smiles"]}
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation=expectation, result=result, edits=[])
    assert diag.reaction_center_match is False
    assert diag.joint_mapping == {}
    assert diag.strict_target_match is True
    (extra,) = diag.extra_changes
    assert extra["atom_id"] == "S_C_2"
    assert "isotope" in extra["delta"]
    assert extra["isotope"] == {"before": 0, "after": 13}


# ---------------------------------------------------- 标签方向控制


def _label_direction_case(substrate: str, new_label: int,
                          changed_id: str, center_ids: list[str]):
    """真实 render→execute_edits→合成标签变异→诊断→audit→admission
    (口径同 R4 supplemental_probe;固定 AtomTool 无 isotope op,标签
    为合成防御变异)。"""
    rendered = render(substrate, name="S")
    ids = dict(rendered.atom_id_map)
    current = {"smiles": rendered.smiles, "atom_id_map": ids}
    result = execute_edits(rendered, [])
    assert result["ok"] is True
    mapped = Chem.MolFromSmiles(result["product_mapped_smiles"])
    atom = next(a for a in mapped.GetAtoms()
                if a.GetAtomMapNum() - 1 == ids[changed_id])
    atom.SetIsotope(new_label)
    plain = Chem.Mol(mapped)
    for a in plain.GetAtoms():
        a.SetAtomMapNum(0)
    result["product_mapped_smiles"] = Chem.MolToSmiles(mapped)
    result["product_smiles"] = Chem.MolToSmiles(plain)
    donor = {"center_atom_ids": [f"d{i}" for i in range(len(center_ids))]}
    alignment = {
        "status": "resolved",
        "donor_to_current": dict(zip(donor["center_atom_ids"],
                                     center_ids)),
        "equivalence_classes": [],
        "ref": f"synthetic:s5a-resident:{substrate}:{changed_id}"}
    expectation = {"target_smiles": result["product_smiles"]}
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation=expectation, result=result, edits=[])
    evidence = center_evidence_from_donor_diagnostic(diag)
    states = [build_chemical_state(
        s, "source_product", [{"record": "synthetic:s5a-resident"}])
        for s in (substrate, result["product_smiles"])]
    participants = [
        Participant(state_ref=states[0].state_id, side="reactant",
                    role="primary_substrate", coefficient=1,
                    coefficient_status="known"),
        Participant(state_ref=states[1].state_id, side="product",
                    role="principal_product", coefficient=1,
                    coefficient_status="known")]
    hypothesis = build_hypothesis(
        parent_path_id="synthetic:path",
        substrate_state_ref=states[0].state_id,
        participants=participants,
        participant_list_status="declared_complete",
        step_scope="net_reaction",
        origin_group_key="synthetic:s5a-resident")
    context = build_path_context(
        condition_facts=[build_condition_fact(
            key="oxygen_regime", value="aerobic",
            status="known_present")],
        accumulated_requirements=[build_requirement(
            key="oxygen_regime", level="essential", value="aerobic",
            source_refs=["synthetic:rule"])],
        assessment_scope=["oxygen_regime"])
    audit = audit_hypothesis(
        hypothesis, states={s.state_id: s for s in states},
        context=context, center_evidence=evidence)
    admission, reasons = decide_admission(
        audit, gate_decisions={"gate_direction_source": {"ok": True}})
    center_check = next(c for c in audit.checks
                        if c.name == CHECK_TRANSFORMATION_CENTER)
    return diag, evidence, audit, admission, reasons, center_check


def test_pure_isotope_center_covers_atom_verified() -> None:
    """方向控制:纯同位素且中心覆盖该原子 ⇒ center verified/R6
    expand(许可范围正控)。"""
    diag, _, _, admission, reasons, center = \
        _label_direction_case("CCO", 13, "S_C_1", ["S_C_1"])
    assert diag.reaction_center_match is True
    assert diag.center_match_basis == "direct"
    assert center.status == "verified"
    assert admission == "expand"
    assert reasons == ["R6:all_verified_no_conflict"]


def test_isotope_loss_outside_center_violated() -> None:
    """方向控制:13→0 中心外 ⇒ center violated/R5v retain_conditional。"""
    diag, _, _, admission, reasons, center = \
        _label_direction_case("[13CH3]CO", 0, "S_C_1",
                              ["S_C_2", "S_O_1"])
    assert diag.reaction_center_match is False
    assert center.status == "violated"
    assert admission == "retain_conditional"
    assert any("R5v" in r for r in reasons)


def test_deuterium_to_tritium_outside_center_violated() -> None:
    """方向控制:[2H]OC→[3H]OC 同映射 D/T 差异,中心外 ⇒ violated/
    R5v(D/T 元素账计 H,身份/同位素轴区分,两结论不互推)。"""
    diag, _, _, admission, _, center = \
        _label_direction_case("[2H]OC", 3, "S_H_1", ["S_O_1"])
    assert diag.reaction_center_match is False
    assert center.status == "violated"
    assert admission == "retain_conditional"


def test_deuterium_to_tritium_center_covers_atom_verified() -> None:
    """方向控制:D/T 差异在中心内 ⇒ verified/R6(表示层范围许可)。"""
    diag, _, _, admission, reasons, center = \
        _label_direction_case("[2H]OC", 3, "S_H_1", ["S_H_1"])
    assert diag.reaction_center_match is True
    assert diag.center_match_basis == "direct"
    assert center.status == "verified"
    assert admission == "expand"
    assert reasons == ["R6:all_verified_no_conflict"]


# ---------------------------------------------------- 篡改拒绝


def _hybrid_outside_isotope_case():
    """混合案(口径同 R4 probe.py mixed_outside_isotope):真实 C–O
    键变 + 中心外 S_C_1 合成 13C 标签 —— 正常键变通过、中心外标签
    拒绝的真实消费链。"""
    rendered = render("CCO", name="S")
    ids = dict(rendered.atom_id_map)
    current = {"smiles": rendered.smiles, "atom_id_map": ids}
    edits = [{"op": "change_bond_order", "atom1": "S_C_2",
              "atom2": "S_O_1", "from_order": "single",
              "to_order": "double"}]
    result = execute_edits(rendered, edits)
    assert result["ok"] is True, result
    mutated = copy.deepcopy(result)
    mapped = Chem.MolFromSmiles(mutated["product_mapped_smiles"])
    atom = next(a for a in mapped.GetAtoms()
                if a.GetAtomMapNum() - 1 == ids["S_C_1"])
    atom.SetIsotope(13)
    plain = Chem.Mol(mapped)
    for a in plain.GetAtoms():
        a.SetAtomMapNum(0)
    mutated["product_mapped_smiles"] = Chem.MolToSmiles(mapped)
    mutated["product_smiles"] = Chem.MolToSmiles(plain)
    donor = {"center_atom_ids": ["d1", "d2"]}
    alignment = {"status": "resolved",
                 "donor_to_current": {"d1": "S_C_2", "d2": "S_O_1"},
                 "equivalence_classes": [],
                 "ref": "synthetic:s5a-resident:mixed"}
    expectation = {"target_smiles": mutated["product_smiles"]}
    diag = check_edit_against_donor(
        current=current, donor=donor, alignment=alignment,
        expectation=expectation, result=mutated, edits=edits)
    evidence = center_evidence_from_donor_diagnostic(diag)
    states = [build_chemical_state(
        s, "source_product", [{"record": "synthetic:s5a-resident"}])
        for s in (rendered.smiles, mutated["product_smiles"], "[H][H]")]
    participants = [
        Participant(state_ref=states[0].state_id, side="reactant",
                    role="primary_substrate", coefficient=1,
                    coefficient_status="known"),
        Participant(state_ref=states[1].state_id, side="product",
                    role="principal_product", coefficient=1,
                    coefficient_status="known"),
        Participant(state_ref=states[2].state_id, side="product",
                    role="coproduct", coefficient=1,
                    coefficient_status="known")]
    hypothesis = build_hypothesis(
        parent_path_id="synthetic:path",
        substrate_state_ref=states[0].state_id,
        participants=participants,
        participant_list_status="declared_complete",
        step_scope="net_reaction",
        origin_group_key="synthetic:s5a-resident:mixed")
    context = build_path_context(
        condition_facts=[build_condition_fact(
            key="oxygen_regime", value="aerobic",
            status="known_present")],
        accumulated_requirements=[build_requirement(
            key="oxygen_regime", level="essential", value="aerobic",
            source_refs=["synthetic:rule"])],
        assessment_scope=["oxygen_regime"])
    return diag, evidence, hypothesis, states, context


def test_hybrid_outside_isotope_center_violated_retain() -> None:
    """混合案:诊断 center False + audit center violated/R5v
    retain_conditional(正常键变不因中心外标签整体通过)。"""
    diag, evidence, hypothesis, states, context = \
        _hybrid_outside_isotope_case()
    assert diag.reaction_center_match is False
    assert diag.strict_target_match is True
    outside = [e for e in diag.extra_changes
               if e["atom_id"] == "S_C_1"]
    assert outside and "isotope" in outside[0]["delta"]
    audit = audit_hypothesis(
        hypothesis, states={s.state_id: s for s in states},
        context=context, center_evidence=evidence)
    admission, reasons = decide_admission(
        audit, gate_decisions={"gate_direction_source": {"ok": True}})
    center = next(c for c in audit.checks
                  if c.name == CHECK_TRANSFORMATION_CENTER)
    assert center.status == "violated"
    assert admission == "retain_conditional"
    assert any("R5v" in r for r in reasons)


def test_tampered_center_match_true_rejected_by_rerun() -> None:
    """篡改拒绝:自报 center_match=True ⇒ audit 内部复算结构化拒绝
    (center_evidence_integrity_mismatch,不改输入即不改结论)。"""
    diag, evidence, hypothesis, states, context = \
        _hybrid_outside_isotope_case()
    assert evidence["center_match"] is False  # 复算基准
    tampered = copy.deepcopy(evidence)
    tampered["center_match"] = True
    with pytest.raises(AuditContractError) as excinfo:
        audit_hypothesis(
            hypothesis, states={s.state_id: s for s in states},
            context=context, center_evidence=tampered)
    assert excinfo.value.detail["kind"] == \
        "center_evidence_integrity_mismatch"
    mismatch = excinfo.value.detail["mismatches"][0]
    assert "center_match:claimed=True:recomputed=False" == mismatch


# ---------------------------------------------------- P2-2/P2-3 新披露


def test_presence_records_carry_isotope_disclosure() -> None:
    """P2-2(donor-diagnostic-10):被增原子 records 补 isotope 单侧值
    (presence 摘要可见性;不改判定 —— presence 原子已入 changed 集)。"""
    from pathway_v43.pollutant.audit import _atom_property_diffs

    rendered = render("CCO", name="S")
    ids = dict(rendered.atom_id_map)
    # add_atom 协议(真实执行器):新 O 原子挂到 S_O_1
    edits = [{"op": "add_atom", "element": "O", "atom1": "S_O_1",
              "new_atom_id": "S_O_9"}]
    result = execute_edits(rendered, edits)
    assert result["ok"] is True, result
    after_map = {str(k): int(v)
                 for k, v in result["atom_id_map"].items()}
    # 合成标签变异:新增原子带 13 标签(防御验证口径)
    mapped = Chem.MolFromSmiles(result["product_mapped_smiles"])
    new_idx = after_map["S_O_9"]
    atom = next(a for a in mapped.GetAtoms()
                if a.GetAtomMapNum() - 1 == new_idx)
    atom.SetIsotope(13)
    plain = Chem.Mol(mapped)
    for a in plain.GetAtoms():
        a.SetAtomMapNum(0)
    result["product_mapped_smiles"] = Chem.MolToSmiles(mapped)
    result["product_smiles"] = Chem.MolToSmiles(plain)
    before = Chem.MolFromSmiles(rendered.smiles)
    changed, records = _atom_property_diffs(
        before, mapped, ids, after_map)
    assert "S_O_9" in changed
    assert records["S_O_9"]["presence"] == "atom_added"
    assert records["S_O_9"]["element"] == "O"
    assert records["S_O_9"]["isotope"] == 13  # P2-2 单侧披露
    # 被删原子(id 映射缺一侧)补 before 侧 isotope
    removed_map = {k: v for k, v in after_map.items() if k != "S_C_1"}
    changed2, records2 = _atom_property_diffs(
        before, mapped, ids, removed_map)
    assert "S_C_1" in changed2
    assert records2["S_C_1"]["presence"] == "atom_removed"
    assert records2["S_C_1"]["isotope"] == 0  # before 侧未标


def test_axis_detail_carries_recomputed_disclosures() -> None:
    """P2-3(donor-diagnostic-10,披露级零语义变化):audit center 检查
    axis_detail 携带复算 extra_changes/center_property_deltas(含
    isotope before/after)—— 读者在 center 检查第一眼即见标签轴。"""
    # 中心内 isotope(verified 案):center_property_deltas 含 isotope
    diag, _, _, _, _, center = \
        _label_direction_case("CCO", 13, "S_C_1", ["S_C_1"])
    assert center.status == "verified"
    detail = center.detail
    assert detail["center_match"] is True
    deltas = detail["center_property_deltas"]
    assert any(d["atom_id"] == "S_C_1" and d.get("isotope") == [0, 13]
               for d in deltas)
    assert detail["extra_changes"] == []
    # 中心外 isotope(violated 案):extra_changes 含 isotope before/after
    diag2, _, _, _, _, center2 = \
        _label_direction_case("[13CH3]CO", 0, "S_C_1",
                              ["S_C_2", "S_O_1"])
    assert center2.status == "violated"
    detail2 = center2.detail
    assert detail2["center_match"] is False
    extras = detail2["extra_changes"]
    assert any(e["atom_id"] == "S_C_1" and e.get("isotope") ==
               {"before": 13, "after": 0} for e in extras)
    # 披露级零语义变化:状态/理由码与 v9 行为一致(violated/R5v)
    assert "center_mismatch" in center2.reason_code


def test_donor_diagnostic_version_registered() -> None:
    """契约身份登记:donor-diagnostic-10(S5a 搭车 P2 披露承载;语义
    零变化),profile 随登记升 -20(见 test_ppv1_profile.py)。"""
    diag, evidence, *_ = _hybrid_outside_isotope_case()
    assert evidence["checker_version"] == "ppv1-donor-diagnostic-10"
    assert diag.schema_version == "ppv1-donor-diagnostic-10"
