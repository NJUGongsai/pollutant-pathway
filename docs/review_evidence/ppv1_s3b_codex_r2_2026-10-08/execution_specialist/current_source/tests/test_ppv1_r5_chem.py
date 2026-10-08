"""R5 化学与证据线回归(Codex R4 复审 R4-01/06/07/08 + §4;v5)。

规则级合成夹具;模型 off,无金标/封存材料。每个用例对应 R4 复审
反例或验收边界;探针基线(e80f459)见
docs/review_evidence/ppv1_r4_codex_2026-10-07/。先红后绿:红验证在
基线工作树(git worktree)复跑本文件,全部失败;v5 实现后全绿。

R4-01:证据证明链(proof_record 内部重算;类型契约结构化拒绝;
产物集合覆盖:整分子/碎片两级 + 部分覆盖挡 R6)。
R4-06:镜像活 ID 表(先增后引)+ 逐操作前置复核(错误 from_order 拒)。
R4-07:键级立体入变化集;非四面体 unsupported 公开;身份不同图轴空
不称零变化;联合映射非四面体门。
R4-08:DATA SGroup 分子级剥离;SRU 保留;未登记 CX 类拒绝。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rdkit import Chem  # noqa: E402

from pathway_v43.pollutant.audit import (  # noqa: E402
    ADMISSION_EXPAND,
    AuditContractError,
    CHECK_TRANSFORMATION_CENTER,
    CHECK_UNKNOWN,
    CHECK_VERIFIED,
    CHECK_VIOLATED,
    audit_hypothesis,
    center_evidence_from_donor_diagnostic,
    check_edit_against_donor,
    decide_admission,
)
from pathway_v43.pollutant.chemstate import (  # noqa: E402
    ChemicalStateError,
    STRUCTURE_ORIGIN_RAW_INPUT,
    STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    build_chemical_state,
    strict_identity_of,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    PARTICIPANT_LIST_DECLARED_COMPLETE,
    PARTICIPANT_ROLE_COSUBSTRATE,
    PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
    PARTICIPANT_SIDE_PRODUCT,
    PARTICIPANT_SIDE_REACTANT,
    COEFFICIENT_KNOWN,
    Participant,
    build_hypothesis,
)
from pathway_v43.pollutant.path_context import (  # noqa: E402
    CONDITION_KEY_OXYGEN,
    build_condition_fact,
    build_path_context,
    build_requirement,
)
from pathway_v43.services.atom_tool import (  # noqa: E402
    execute_edits,
    render,
    roundtrip,
)

ETHANOL = "CCO"
ACETALDEHYDE = "CC=O"
HYDROGEN = "[H][H]"
SRC = ["src:rule-1"]


def _sub(ref, coefficient=1):
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_REACTANT,
                       role="primary_substrate", coefficient=coefficient,
                       coefficient_status=COEFFICIENT_KNOWN)


def _cosub(ref):
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_REACTANT,
                       role=PARTICIPANT_ROLE_COSUBSTRATE, coefficient=1,
                       coefficient_status=COEFFICIENT_KNOWN)


def _prod(ref, role=PARTICIPANT_ROLE_PRINCIPAL_PRODUCT):
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_PRODUCT,
                       role=role, coefficient=1,
                       coefficient_status=COEFFICIENT_KNOWN)


def _states(*smiles, origin=STRUCTURE_ORIGIN_SOURCE_PRODUCT):
    return {s: build_chemical_state(s, origin) for s in smiles}


def _hyp(states, reactants, products, group="r5-chem"):
    return build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[reactants[0]].state_id,
        participants=[_sub(states[reactants[0]].state_id)]
        + [_cosub(states[s].state_id) for s in reactants[1:]]
        + [_prod(states[s].state_id) for s in products],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key=group)


def _aerobic_context():
    return build_path_context(
        condition_facts=[build_condition_fact(
            key=CONDITION_KEY_OXYGEN, value="aerobic",
            status="known_present")],
        accumulated_requirements=[build_requirement(
            key=CONDITION_KEY_OXYGEN, level="essential", value="aerobic",
            source_refs=SRC)],
        assessment_scope=[CONDITION_KEY_OXYGEN])


def _ethanol_co_execution():
    r = roundtrip(ETHANOL, name="S")
    edits = [{"op": "change_bond_order", "atom1": "S_C_2",
              "atom2": "S_O_1", "from_order": "single",
              "to_order": "double"}]
    execution = execute_edits(r, edits)
    assert execution["ok"] is True
    return {"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)}, \
        edits, execution


def _diag(current, edits, execution, donor_centers, mapping,
          target=None):
    return check_edit_against_donor(
        current=current, donor={"center_atom_ids": donor_centers},
        alignment={"status": "resolved", "donor_to_current": mapping,
                   "equivalence_classes": [], "ref": "r5"},
        expectation={"target_smiles": target
                     if target is not None
                     else execution["product_smiles"]},
        result=execution, edits=edits)


def _center(audit):
    return next(c for c in audit.checks
                if c.name == CHECK_TRANSFORMATION_CENTER)


# ============================================================ R4-01 证明链


def test_r4_01_genuine_bound_control_stays_verified() -> None:
    """正控制:真实乙醇→乙醛诊断(完整 proof_record)绑定一致假设
    ⇒ 中心 verified、可 R6;证明链不误杀合法路径。"""
    current, edits, execution = _ethanol_co_execution()
    diag = _diag(current, edits, execution, ["dC", "dO"],
                 {"dC": "S_C_2", "dO": "S_O_1"})
    assert diag.reaction_center_match is True
    evidence = center_evidence_from_donor_diagnostic(diag)
    assert evidence["proof_record"]["current"] == current
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [ETHANOL], [ACETALDEHYDE, HYDROGEN])
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=evidence)
    assert _center(audit).status == CHECK_VERIFIED
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert d == ADMISSION_EXPAND


def test_r4_01_two_identity_strings_no_proof_unknown() -> None:
    """复审反例 1:仅注册版本/scope/轴结论 + 两条身份字符串(无
    proof_record)⇒ unknown,不到 R6(v4 曾直达 R6)。"""
    current, edits, execution = _ethanol_co_execution()
    diag = _diag(current, edits, execution, ["dC", "dO"],
                 {"dC": "S_C_2", "dO": "S_O_1"})
    evidence = center_evidence_from_donor_diagnostic(diag)
    minimal = {k: evidence[k] for k in (
        "checker_version", "checker_scope", "center_match",
        "strict_target_match", "declaration_mismatch")}
    minimal["bound_inputs"] = {
        k: evidence["bound_inputs"][k] for k in (
            "substrate_identity", "product_identity")}
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [ETHANOL], [ACETALDEHYDE, HYDROGEN])
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=minimal)
    assert _center(audit).status == CHECK_UNKNOWN
    assert "center_evidence_proof_missing" in _center(audit).reason_code
    d, _ = decide_admission(audit)
    assert d != ADMISSION_EXPAND


def test_r4_01_six_claimed_fields_no_execution_unknown() -> None:
    """复审反例 2:六条绑定字段全部伪造(edits/指纹/中心/对齐)
    仍无 proof_record ⇒ unknown(补字段不构成 checker 曾执行的证明;
    只有 input_hash 变化不够)。"""
    current, edits, execution = _ethanol_co_execution()
    diag = _diag(current, edits, execution, ["dC", "dO"],
                 {"dC": "S_C_2", "dO": "S_O_1"})
    evidence = center_evidence_from_donor_diagnostic(diag)
    fabricated = dict(evidence)
    fabricated.pop("proof_record")
    fabricated["bound_inputs"] = dict(evidence["bound_inputs"])
    fabricated["bound_inputs"].update(
        edits_signature="fictional:no-edits",
        execution_fingerprint="fictional:no-result",
        donor_centers=["fictional:carbon"],
        alignment_ref="fictional:no-mapping")
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [ETHANOL], [ACETALDEHYDE, HYDROGEN])
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=fabricated)
    assert _center(audit).status == CHECK_UNKNOWN
    d, _ = decide_admission(audit)
    assert d != ADMISSION_EXPAND


@pytest.mark.parametrize("field", ["edits_signature",
                                   "execution_fingerprint",
                                   "donor_centers", "alignment_ref"])
def test_r4_01_mutated_evidence_field_structured_reject(field) -> None:
    """复审反例 3:改真实诊断的任一绑定字段 ⇒ integrity 复算不一致
    ⇒ AuditContractError(结构化拒绝;v4 仅 input_hash 变化、结论
    照常 verified)。"""
    current, edits, execution = _ethanol_co_execution()
    diag = _diag(current, edits, execution, ["dC", "dO"],
                 {"dC": "S_C_2", "dO": "S_O_1"})
    evidence = center_evidence_from_donor_diagnostic(diag)
    altered = dict(evidence)
    altered["bound_inputs"] = dict(evidence["bound_inputs"])
    altered["bound_inputs"][field] = (
        ["fake:other-center"] if field == "donor_centers"
        else "fake:other-input")
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [ETHANOL], [ACETALDEHYDE, HYDROGEN])
    with pytest.raises(AuditContractError) as ei:
        audit_hypothesis(
            hyp, states={s.state_id: s for s in states.values()},
            context=_aerobic_context(), center_evidence=altered)
    assert ei.value.detail["kind"] == "center_evidence_integrity_mismatch"


@pytest.mark.parametrize("value", ["false", 0, {}, []])
def test_r4_01_strict_axis_type_violation_structured_reject(value) -> None:
    """复审反例 4:strict 轴类型违约(字符串'false'/整数 0/空容器
    绕过 is False/is None)⇒ 结构化拒绝(表示契约,不是化学未知)。"""
    current, edits, execution = _ethanol_co_execution()
    diag = _diag(current, edits, execution, ["dC", "dO"],
                 {"dC": "S_C_2", "dO": "S_O_1"})
    evidence = center_evidence_from_donor_diagnostic(diag)
    evidence["strict_target_match"] = value
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [ETHANOL], [ACETALDEHYDE, HYDROGEN])
    with pytest.raises(AuditContractError) as ei:
        audit_hypothesis(
            hyp, states={s.state_id: s for s in states.values()},
            context=_aerobic_context(), center_evidence=evidence)
    assert ei.value.detail["kind"] == "center_evidence_type_violation"


def test_r4_01_strict_false_from_real_diagnostic_r5v() -> None:
    """合法 strict=False 来自真实诊断(期望 ≠ 实际产物)⇒ violated
    → R5v(类型契约不误杀合法 False;复算轴与声明轴一致)。"""
    current, edits, execution = _ethanol_co_execution()
    diag = _diag(current, edits, execution, ["dC", "dO"],
                 {"dC": "S_C_2", "dO": "S_O_1"},
                 target=ACETALDEHYDE)  # 与实际一致
    assert diag.strict_target_match is True
    # 期望不同 ⇒ 真实 strict=False(产物比对轴的适用失败)
    diag_false = _diag(current, edits, execution, ["dC", "dO"],
                       {"dC": "S_C_2", "dO": "S_O_1"},
                       target="CCO")
    assert diag_false.strict_target_match is False
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [ETHANOL], [ACETALDEHYDE, HYDROGEN])
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(),
        center_evidence=center_evidence_from_donor_diagnostic(diag_false))
    assert _center(audit).status == CHECK_VIOLATED
    d, reasons = decide_admission(audit)
    assert d == "retain_conditional"
    assert any(r.startswith("R5v:") for r in reasons)


def test_r4_01_fragment_products_bind_separately() -> None:
    """复审反例 5:真实断裂分列产物(实际 C.CO;假设产物 C、CO 各为
    参与物)⇒ 碎片两级映射绑定成功(v4 因 C.CO 不等于任一单个产物
    而 unknown/retain);不要求把碎片拼成一个物种过门。"""
    r = roundtrip(ETHANOL, name="S")
    edits = [{"op": "break_bond", "atom1": "S_C_1", "atom2": "S_C_2"}]
    execution = execute_edits(r, edits)
    assert execution["ok"] is True
    assert execution["product_smiles"] == "C.CO"
    diag = _diag({"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)},
                 edits, execution, ["d1", "d2"],
                 {"d1": "S_C_1", "d2": "S_C_2"})
    assert diag.reaction_center_match is True
    evidence = center_evidence_from_donor_diagnostic(diag)
    states = _states(ETHANOL, HYDROGEN, "C", "CO")
    hyp = _hyp(states, [ETHANOL, HYDROGEN], ["C", "CO"],
               group="r5-frag")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=evidence)
    center = _center(audit)
    assert center.status == CHECK_VERIFIED
    assert center.detail["coverage_mode"] == "fragments"
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert d == ADMISSION_EXPAND


def test_r4_01_fragment_lumped_control_unchanged() -> None:
    """对照:分列/合并两种表示行为一致(合并单参与物 C.CO 同样
    verified;整分子映射通道)。"""
    r = roundtrip(ETHANOL, name="S")
    edits = [{"op": "break_bond", "atom1": "S_C_1", "atom2": "S_C_2"}]
    execution = execute_edits(r, edits)
    diag = _diag({"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)},
                 edits, execution, ["d1", "d2"],
                 {"d1": "S_C_1", "d2": "S_C_2"})
    evidence = center_evidence_from_donor_diagnostic(diag)
    states = _states(ETHANOL, HYDROGEN, "C.CO")
    hyp = _hyp(states, [ETHANOL, HYDROGEN], ["C.CO"], group="r5-lump")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=evidence)
    center = _center(audit)
    assert center.status == CHECK_VERIFIED
    assert center.detail["coverage_mode"] == "whole_molecule"


def test_r4_01_unchecked_additional_transformation_partial() -> None:
    """复审反例 6:真实乙醇诊断复用于 CCO+C1CC1→CC=O+H2+CC=C
    ⇒ 未覆盖共底物与未覆盖产物并存 = 额外未核实转化 ⇒ 部分覆盖
    unknown,不借一个产物达 all_verified(v4 曾 R6)。"""
    current, edits, execution = _ethanol_co_execution()
    diag = _diag(current, edits, execution, ["dC", "dO"],
                 {"dC": "S_C_2", "dO": "S_O_1"})
    evidence = center_evidence_from_donor_diagnostic(diag)
    states = _states(ETHANOL, "C1CC1", ACETALDEHYDE, HYDROGEN, "CC=C")
    hyp = _hyp(states, [ETHANOL, "C1CC1"],
               [ACETALDEHYDE, HYDROGEN, "CC=C"], group="r5-extra")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=evidence)
    center = _center(audit)
    assert center.status == CHECK_UNKNOWN
    assert "partial_coverage_unchecked_transformation" in center.reason_code
    assert center.detail["product_coverage"] == \
        "partial_unchecked_transformation"
    d, _ = decide_admission(audit)
    assert d != ADMISSION_EXPAND


def test_r4_02_finite_rule_diagnostic_in_input_hash() -> None:
    """R4-02:有限规则诊断(实际审核入参)入 input_hash —— 默认
    not_run(合法 NA)与 diagnostic_only(unknown/retain)不同 hash
    (v4 两次同 hash)。"""
    current, edits, execution = _ethanol_co_execution()
    diag = _diag(current, edits, execution, ["dC", "dO"],
                 {"dC": "S_C_2", "dO": "S_O_1"})
    evidence = center_evidence_from_donor_diagnostic(diag)
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [ETHANOL], [ACETALDEHYDE, HYDROGEN])
    kwargs = dict(states={s.state_id: s for s in states.values()},
                  context=_aerobic_context(), center_evidence=evidence)
    baseline = audit_hypothesis(hyp, **kwargs)
    active = audit_hypothesis(
        hyp, finite_rule_diagnostic={"status": "diagnostic_only",
                                     "reason": "synthetic:active"}, **kwargs)
    assert baseline.input_hash != active.input_hash


def test_r4_section4_audit_scope_not_shadowed() -> None:
    """§4:audit.scope 不被证据门局部 checker scope 遮蔽 —— 显式
    scope='synthetic:review-scope' 如实返回(v4 返回 region_net_change)。"""
    current, edits, execution = _ethanol_co_execution()
    diag = _diag(current, edits, execution, ["dC", "dO"],
                 {"dC": "S_C_2", "dO": "S_O_1"})
    evidence = center_evidence_from_donor_diagnostic(diag)
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [ETHANOL], [ACETALDEHYDE, HYDROGEN])
    audit = audit_hypothesis(
        hyp, scope="synthetic:review-scope", **dict(
            states={s.state_id: s for s in states.values()},
            context=_aerobic_context(), center_evidence=evidence))
    assert audit.scope == "synthetic:review-scope"


# ============================================================ R4-06 镜像


def test_r4_06_add_then_add_anchor_new_atom() -> None:
    """复审反例:C 先 add O、用新 O 再 add C(先增后引)⇒ 执行器
    validation/execution True;镜像活 ID 表 ⇒ 零失配、strict/center
    可判(v4 误报 declared_edits_not_simulable)。"""
    r = roundtrip("C", name="A")
    edits = [
        {"op": "add_atom", "atom1": "A_C_1", "element": "O",
         "new_atom_id": "A_O_1"},
        {"op": "add_atom", "atom1": "A_O_1", "element": "C",
         "new_atom_id": "A_C_2"}]
    execution = execute_edits(r, edits)
    assert execution["ok"] is True
    all_ids = list(execution["atom_id_map"])
    diag = _diag({"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)},
                 edits, execution,
                 ["d%d" % i for i in range(len(all_ids))],
                 {"d%d" % i: a for i, a in enumerate(all_ids)})
    assert diag.declaration_mismatches == []
    assert diag.strict_target_match is True
    assert diag.reaction_center_match is True


def test_r4_06_add_then_change_new_bond() -> None:
    """复审反例:C 先 add C、引用新键改双 ⇒ 镜像活 ID 表零失配
    (v4 因新原子不在 before 表而误报不可模拟)。"""
    r = roundtrip("C", name="B")
    edits = [
        {"op": "add_atom", "atom1": "B_C_1", "element": "C",
         "new_atom_id": "B_C_2"},
        {"op": "change_bond_order", "atom1": "B_C_1", "atom2": "B_C_2",
         "from_order": "single", "to_order": "double"}]
    execution = execute_edits(r, edits)
    assert execution["ok"] is True
    diag = _diag({"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)},
                 edits, execution, ["d1", "d2"],
                 {"d1": "B_C_1", "d2": "B_C_2"})
    assert diag.declaration_mismatches == []
    assert diag.reaction_center_match is True


def test_r4_06_wrong_from_order_rejected_by_mirror() -> None:
    """复审反例:真实乙醇 single→double 输出 + 接口声明错误
    from_order=double ⇒ 冻结执行器拒绝该声明;镜像同样拒绝
    (declared_precondition_violated:bond_order_mismatch)⇒ strict/
    center None(v4 零失配通过、strict/center True)。"""
    current, edits, execution = _ethanol_co_execution()
    bad = [dict(edits[0], from_order="double")]
    re_exec = execute_edits(roundtrip(ETHANOL, name="S"), bad)
    assert re_exec["ok"] is False  # 冻结执行器拒绝错误前置
    diag = _diag(current, bad, execution, ["dC", "dO"],
                 {"dC": "S_C_2", "dO": "S_O_1"})
    assert any("bond_order_mismatch" in m
               for m in diag.declaration_mismatches)
    assert diag.strict_target_match is None
    assert diag.reaction_center_match is None


# ============================================================ R4-07 立体轴


def _ez_interface_result(r, stereo=Chem.BondStereo.STEREOZ):
    """接口合成 E/Z 结果(零操作;标注来源,不冒称执行器行为)。"""
    m = Chem.MolFromSmiles(r.smiles)
    for atom in m.GetAtoms():
        atom.SetAtomMapNum(atom.GetIdx() + 1)
    b = next(b for b in m.GetBonds()
             if b.GetBondType() == Chem.BondType.DOUBLE)
    b.SetStereo(stereo)
    Chem.SetDoubleBondNeighborDirections(m)
    plain = Chem.Mol(m)
    for atom in plain.GetAtoms():
        atom.SetAtomMapNum(0)
    return {"ok": True, "reasons": [], "n_edits": 0,
            "product_smiles": Chem.MolToSmiles(plain),
            "product_mapped_smiles": Chem.MolToSmiles(m),
            "atom_id_map": dict(r.atom_id_map),
            "protocol_version": "v43-editproto-2"}


def test_r4_07_ez_only_change_detected_not_empty() -> None:
    """复审反例:接口合成 E/Z 变化(身份不同、图轴空)⇒ 立体入
    变化集(bond_stereo_change)、声明对账失配;不再报"实际净变化
    为空"(v4 理由码断言身份轴已证伪的事)。"""
    r = render("C/C=C/C", name="E")
    result = _ez_interface_result(r)
    assert strict_identity_of(r.smiles) != strict_identity_of(
        result["product_smiles"])
    ids = {v: k for k, v in r.atom_id_map.items()}
    diag = _diag({"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)},
                 [], result, ["d1", "d2"],
                 {"d1": ids[1], "d2": ids[2]})
    stereo_changes = [c for c in diag.executed_bond_changes
                      if c["kind"] == "bond_stereo_change"]
    assert stereo_changes, "E/Z 变化必须入实际变化集"
    assert diag.net_change_empty is False
    assert not any("no_executed_change(实际净变化为空" in m
                   for m in diag.missing_info_reasons)
    # 零操作声明下出现立体变化 ⇒ 声明对账失配(接口合成 ≠ 执行器)
    assert diag.declaration_mismatches


def test_r4_07_off_center_ez_not_center_true() -> None:
    """复审反例:真实远端编辑输出 + 接口注入中心外 E/Z ⇒ center
    不得 True(v4 center=True、extra 空);注入经声明对账/变化集检出。"""
    r = render("C/C=C/C.CCO", name="Z")
    ids = {v: k for k, v in r.atom_id_map.items()}
    es = [{"op": "change_bond_order", "atom1": ids[5], "atom2": ids[6],
           "from_order": "single", "to_order": "double"}]
    ex = execute_edits(r, es)
    assert ex["ok"] is True
    m = Chem.MolFromSmiles(ex["product_mapped_smiles"])
    b = next(b for b in m.GetBonds()
             if {b.GetBeginAtom().GetAtomMapNum(),
                 b.GetEndAtom().GetAtomMapNum()} == {2, 3})
    b.SetStereo(Chem.BondStereo.STEREOZ)
    Chem.SetDoubleBondNeighborDirections(m)
    plain = Chem.Mol(m)
    for atom in plain.GetAtoms():
        atom.SetAtomMapNum(0)
    modified = {"ok": True, "reasons": [], "n_edits": len(es),
                "product_smiles": Chem.MolToSmiles(plain),
                "product_mapped_smiles": Chem.MolToSmiles(m),
                "atom_id_map": dict(ex["atom_id_map"]),
                "protocol_version": "v43-editproto-2"}
    diag = _diag({"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)},
                 es, modified, ["d5", "d6"],
                 {"d5": ids[5], "d6": ids[6]})
    assert diag.reaction_center_match is not True


def test_r4_07_real_ez_inverse_control_identity_equal() -> None:
    """对照:真实 double→single→double 净效应 ⇒ E/Z 保留、身份相等、
    无伪立体变化(执行器不产生该分歧;E/Z 轴是潜伏缺口的检出通道)。"""
    r = render("C/C=C/C", name="K")
    ids = {v: k for k, v in r.atom_id_map.items()}
    es = [{"op": "change_bond_order", "atom1": ids[1], "atom2": ids[2],
           "from_order": "double", "to_order": "single"},
          {"op": "change_bond_order", "atom1": ids[1], "atom2": ids[2],
           "from_order": "single", "to_order": "double"}]
    ex = execute_edits(r, es)
    assert ex["ok"] is True
    assert strict_identity_of(r.smiles) == strict_identity_of(
        ex["product_smiles"])
    diag = _diag({"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)},
                 es, ex, ["d1", "d2"],
                 {"d1": ids[1], "d2": ids[2]})
    assert not any(c["kind"] == "bond_stereo_change"
                   for c in diag.executed_bond_changes)
    # 净效应为零(键级/立体/身份全部还原)⇒ center=None(no_executed_
    # change;声明触及≠已发生,R2-03 控制)——不是 stereo 误报
    assert diag.net_change_empty is True
    assert diag.reaction_center_match is None
    assert any("no_executed_change" in x
               for x in diag.missing_info_reasons)


def test_r4_07_non_tetrahedral_unsupported_not_retained() -> None:
    """复审反例:两侧非四面体标签(平面/四方/三角双锥)⇒
    _stereo_config_delta 返回 None(unsupported),不返回""(构型
    保持);unsupported 原子进公开清单(v4 先命中"都不是四面体⇒保持"
    且标志无公开通道)。"""
    from pathway_v43.pollutant.audit import _stereo_config_delta

    before = Chem.MolFromSmiles("Cl[Pt@SP1](Br)(I)F")
    after = Chem.MolFromSmiles("Cl[Pt@SP2](Br)(I)F")
    b_atom = next(a for a in before.GetAtoms() if a.GetSymbol() == "Pt")
    a_atom = next(a for a in after.GetAtoms() if a.GetSymbol() == "Pt")
    assert _stereo_config_delta(b_atom, a_atom) is None
    # 一侧非四面体、另一侧 UNSPECIFIED 同样 unsupported
    m = Chem.MolFromSmiles("Cl[Pt@SP1](Br)(I)F")
    m.GetAtomWithIdx(1).SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
    assert _stereo_config_delta(
        b_atom, m.GetAtomWithIdx(1)) is None


def test_r4_07_non_tetrahedral_identity_differs_honest_reason() -> None:
    """复审反例:非四面体置换变化(身份不同、图轴空)⇒ 理由为
    net_change_only_in_stereo_representation + 公开 unsupported 清单,
    不称"实际净变化为空"(v4 两个字段对"净变化是否为空"互相矛盾)。"""
    r = render("Cl[Pt@SP1](Br)(I)F", name="P")
    m = Chem.MolFromSmiles(r.smiles)
    for atom in m.GetAtoms():
        atom.SetAtomMapNum(atom.GetIdx() + 1)
    pt = next(a for a in m.GetAtoms() if a.GetSymbol() == "Pt")
    pt.SetIntProp("_chiralPermutation", 2)
    plain = Chem.Mol(m)
    for atom in plain.GetAtoms():
        atom.SetAtomMapNum(0)
    result = {"ok": True, "reasons": [], "n_edits": 0,
              "product_smiles": Chem.MolToSmiles(plain),
              "product_mapped_smiles": Chem.MolToSmiles(m),
              "atom_id_map": dict(r.atom_id_map),
              "protocol_version": "v43-editproto-2"}
    ids = {v: k for k, v in r.atom_id_map.items()}
    diag = _diag({"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)},
                 [], result, ["d1"], {"d1": ids[1]})
    assert diag.net_change_empty is False
    assert any("net_change_only_in_stereo_representation" in x
               for x in diag.missing_info_reasons)
    assert not any("no_executed_change(实际净变化为空" in x
                   for x in diag.missing_info_reasons)
    assert diag.stereo_comparison_unsupported_atoms  # 公开清单


def test_r4_07_non_tetrahedral_joint_mapping_unsupported() -> None:
    """复审反例:非四面体底物(C[C@...改 P@TB1)声明中心在左、实际
    断右 ⇒ 联合映射须 unsupported ⇒ center None(v4 useChirality 忽略
    非四面体标签,把可区分位点判等价、center 误 True)。"""
    s = "CC[P@TB1](CC)(Br)(I)F"
    r = render(s, name="Q")
    ids = {v: k for k, v in r.atom_id_map.items()}
    es_right = [{"op": "change_bond_order", "atom1": ids[3],
                 "atom2": ids[4], "from_order": "single",
                 "to_order": "double"}]
    ex_right = execute_edits(r, es_right)
    assert ex_right["ok"] is True
    diag = _diag({"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)},
                 es_right, ex_right, ["d0", "d1"],
                 {"d0": ids[0], "d1": ids[1]})
    assert diag.reaction_center_match is None
    assert any("joint_mapping_stereo_unsupported" in x
               for x in diag.missing_info_reasons)


def test_r4_07_unsupported_stereo_outside_center_blocks_true() -> None:
    """R4-07 验收:中心外存在 unsupported 立体轴原子(非四面体)⇒
    区域约束对该轴不可核 ⇒ center 不可判 True(公开清单 + missing
    理由);中心内不阻断(立体变化本就允许,只披露)。"""
    # 铂平面手性在另一碎片;编辑 CCO 的 C–O(图变化全在中心内)
    r = render("Cl[Pt@SP1](Br)(I)F.CCO", name="X")
    ids = {v: k for k, v in r.atom_id_map.items()}
    es = [{"op": "change_bond_order", "atom1": ids[6], "atom2": ids[7],
           "from_order": "single", "to_order": "double"}]
    ex = execute_edits(r, es)
    assert ex["ok"] is True
    diag = _diag({"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)},
                 es, ex, ["d6", "d7"],
                 {"d6": ids[6], "d7": ids[7]})
    assert "X_Pt_1_S" in diag.stereo_comparison_unsupported_atoms
    assert diag.reaction_center_match is None
    assert any("stereo_comparison_unsupported_outside_center" in x
               for x in diag.missing_info_reasons)


# ============================================================ R4-08 CX


def test_r4_08_data_sgroup_note_not_in_identity() -> None:
    """复审反例:任意 DATA SGroup 注记(review_note)不改化学图 ⇒
    与裸 CO 同 state_id(v4 三输入三个 id);注记保留在 raw 串。"""
    plain = build_chemical_state("CO", STRUCTURE_ORIGIN_RAW_INPUT)
    for text in ("review_note_foo", "review_note_bar"):
        m = Chem.MolFromSmiles("CO")
        sg = Chem.CreateMolDataSubstanceGroup(m, "review_note", text)
        sg.SetAtoms([0])
        cx = Chem.MolToCXSmiles(m)
        st = build_chemical_state(cx, STRUCTURE_ORIGIN_RAW_INPUT)
        assert st.state_id == plain.state_id
        assert text in st.structure_smiles_raw  # 出现元数据另存


def test_r4_08_data_sgroup_value_with_comma() -> None:
    """边界:DATA 值含逗号(SgD:0:note:a,b::::)⇒ 分子级剥离仍稳
    (字符串级令牌解析对值内逗号不可靠 —— R5 实测依据)。"""
    m = Chem.MolFromSmiles("CO")
    sg = Chem.CreateMolDataSubstanceGroup(m, "note", "a,b")
    sg.SetAtoms([0])
    st = build_chemical_state(Chem.MolToCXSmiles(m),
                              STRUCTURE_ORIGIN_RAW_INPUT)
    plain = build_chemical_state("CO", STRUCTURE_ORIGIN_RAW_INPUT)
    assert st.state_id == plain.state_id


def test_r4_08_sru_sgroup_retained() -> None:
    """SRU/聚合物组承载化学事实 ⇒ 保留在身份(不盲目剥 SGroup);
    往返重建同 id。"""
    bare = build_chemical_state("CCCCCC", STRUCTURE_ORIGIN_RAW_INPUT)
    m = Chem.MolFromSmiles("CCCCCC")
    sg = Chem.CreateMolSubstanceGroup(m, "SRU")
    sg.SetAtoms([1, 2, 3])
    sg.SetProp("CONNECT", "HT")
    sg.SetProp("LABEL", "3")
    cx = Chem.MolToCXSmiles(m)
    st = build_chemical_state(cx, STRUCTURE_ORIGIN_RAW_INPUT)
    assert st.state_id != bare.state_id  # 化学事实保留 ⇒ 身份不同
    # 往返:公开表示重建同 id
    st2 = build_chemical_state(st.smiles_isomeric,
                               STRUCTURE_ORIGIN_RAW_INPUT)
    assert st2.state_id == st.state_id


def test_r4_08_unregistered_cx_class_rejected() -> None:
    """未登记 CX 类(如 w:/LN:/旗标块 r)⇒ ChemicalStateError(拒绝
    该表示,不默认进身份;登记表 Sg/SgD/a/oN/&N/^N)。

    守卫在**身份键生成路径**上(防御层:RDKit 写出器只产登记类,
    属性/坐标在生成前清除 —— 本仓生成路径不产未登记类,R5 交付
    §登记表实测);直接调用守卫验证拒绝语义与登记类不误伤。"""
    from pathway_v43.pollutant.chemstate import _guard_registered_cx_classes

    with pytest.raises(ChemicalStateError) as ei:
        _guard_registered_cx_classes("CCCCC |w:1:0.0|")
    assert ei.value.detail["kind"] == "unregistered_cx_class"
    with pytest.raises(ChemicalStateError) as ei2:
        _guard_registered_cx_classes("CCCCC |LN:1 3 2 1 2 3|")
    assert ei2.value.detail["kind"] == "unregistered_cx_class"
    # 无冒号旗标块(如 |r|):目前无登记类 ⇒ 同样拒绝
    with pytest.raises(ChemicalStateError):
        _guard_registered_cx_classes("CC(C)O |r|")
    # 登记类不误伤(增强组/自由基/Sg)
    _guard_registered_cx_classes("C[C@H](Cl)[C@H](F)Cl |a:1,&1:3|")
    _guard_registered_cx_classes("CO |^1:0|")
    _guard_registered_cx_classes("CCCCCC |Sg:n:1,2,3:3:ht:::|")
