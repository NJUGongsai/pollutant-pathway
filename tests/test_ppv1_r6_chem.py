"""R6 化学与证据线回归(Codex R5 复审 R5-01/02/08 + §4 披露项 1;v6)。

规则级合成夹具;模型 off,无金标/封存材料。每个用例对应 R5 复审
反例或验收边界;探针基线(293bc62)见
docs/review_evidence/ppv1_r5_codex_2026-10-07/。先红后绿:红验证在
基线工作树(git worktree)复跑本文件,反例全部失败;v6 实现后全绿。

R5-01:证据覆盖绑定被审参与物的系数/贡献;未覆盖部分只有注册计量
补全规则(COVERAGE_COMPLETION_RULE = atom_delta_stoichiometric_
completion)数值相符才算覆盖;单侧空/账平不再自动 full;整类 H2/
水/共底物不按名称免审。
R5-02:原始 CX 输入在解析**之前**做注册感知验证(|r|、|Ln:1| 等被
RDKit 静默丢弃的未登记类 ⇒ 构造即拒,不再与裸串同 id/as_written)。
R5-08:镜像终态与冻结执行器同一归一(写出/重解析),正确 σ 断键的
自然 E/Z 消失不再称漏申报。
P2(§4-1):center_match_basis / proof_scope=self_contained_recompute
同源披露,空 basis= 消除;篡改 basis ⇒ integrity 结构化拒绝。

全部走公开链:roundtrip/render → execute_edits →
check_edit_against_donor → center_evidence_from_donor_diagnostic →
audit_hypothesis → decide_admission / build_chemical_state /
strict_identity_of;不直接断言私有守卫。
"""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.audit import (  # noqa: E402
    ADMISSION_EXPAND,
    ADMISSION_RETAIN_CONDITIONAL,
    AuditContractError,
    CHECK_ELEMENT_ACCOUNTING,
    CHECK_FORMAL_CHARGE_ACCOUNTING,
    CHECK_TRANSFORMATION_CENTER,
    CHECK_UNKNOWN,
    CHECK_VERIFIED,
    COVERAGE_COMPLETION_RULE,
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
    COEFFICIENT_KNOWN,
    COEFFICIENT_UNKNOWN,
    PARTICIPANT_LIST_DECLARED_COMPLETE,
    PARTICIPANT_ROLE_COSUBSTRATE,
    PARTICIPANT_ROLE_COPRODUCT,
    PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
    PARTICIPANT_SIDE_PRODUCT,
    PARTICIPANT_SIDE_REACTANT,
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
EPOXIDE = "C1CO1"
SRC = ["src:rule-r6"]


# ---------------------------------------------------------------- 夹具

def _sub(ref, coefficient=1, known=True):
    return Participant(
        state_ref=ref, side=PARTICIPANT_SIDE_REACTANT,
        role="primary_substrate", coefficient=coefficient,
        coefficient_status=(COEFFICIENT_KNOWN if known
                            else COEFFICIENT_UNKNOWN))


def _cosub(ref, coefficient=1):
    return Participant(
        state_ref=ref, side=PARTICIPANT_SIDE_REACTANT,
        role=PARTICIPANT_ROLE_COSUBSTRATE, coefficient=coefficient,
        coefficient_status=COEFFICIENT_KNOWN)


def _prod(ref, coefficient=1, role=PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
          known=True):
    return Participant(
        state_ref=ref, side=PARTICIPANT_SIDE_PRODUCT, role=role,
        coefficient=(coefficient if known else None),
        coefficient_status=(COEFFICIENT_KNOWN if known
                            else COEFFICIENT_UNKNOWN))


def _states(*smiles, origin=STRUCTURE_ORIGIN_SOURCE_PRODUCT):
    return {s: build_chemical_state(s, origin) for s in smiles}


def _hyp(states, reactants, products, group="r6-chem"):
    """reactants/products 均为 (smiles, coefficient) 元组列表。"""
    participants = ([_sub(states[smi].state_id, coeff)
                     for smi, coeff in reactants[:1]]
                    + [_cosub(states[smi].state_id, coeff)
                       for smi, coeff in reactants[1:]]
                    + [_prod(states[smi].state_id, coeff,
                             role=(PARTICIPANT_ROLE_PRINCIPAL_PRODUCT
                                   if i == 0 else PARTICIPANT_ROLE_COPRODUCT))
                       for i, (smi, coeff) in enumerate(products)])
    return build_hypothesis(
        parent_path_id="p1",
        substrate_state_ref=states[reactants[0][0]].state_id,
        participants=participants,
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key=group)


def _hyp_with_unknown(states, reactants, products, group="r6-unk"):
    """reactants 为 (smiles, coefficient, known) 元组;products 同。"""
    participants = ([_sub(states[smi].state_id, coeff, known)
                     for smi, coeff, known in reactants]
                    + [_prod(states[smi].state_id, coeff, known=known)
                       for smi, coeff, known in products])
    return build_hypothesis(
        parent_path_id="p1",
        substrate_state_ref=states[reactants[0][0]].state_id,
        participants=participants,
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


def _donor_evidence(substrate, a1, a2, from_order, to_order):
    """真实 AtomTool 执行 + 真实供体诊断(公开链,零篡改)。"""
    render_result = roundtrip(substrate, name="S")
    edits = [{"op": "change_bond_order", "atom1": a1, "atom2": a2,
              "from_order": from_order, "to_order": to_order}]
    execution = execute_edits(render_result, edits)
    assert execution["ok"] is True
    diag = check_edit_against_donor(
        current={"smiles": render_result.smiles,
                 "atom_id_map": dict(render_result.atom_id_map)},
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": a1, "dO": a2},
                   "equivalence_classes": [], "ref": "r6"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.reaction_center_match is True
    assert diag.strict_target_match is True
    return center_evidence_from_donor_diagnostic(diag)


def _oxidation_evidence():
    """真实乙醇 C–O single→double 诊断(乙醇氧化证据)。"""
    return _donor_evidence(ETHANOL, "S_C_2", "S_O_1",
                           "single", "double")


def _reduction_evidence():
    """真实乙醛 C=O double→single 诊断(氢化证据)。"""
    return _donor_evidence(ACETALDEHYDE, "S_C_2", "S_O_1",
                           "double", "single")


def _audit(states, hyp, evidence):
    return audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=evidence)


def _center(audit):
    return next(c for c in audit.checks
                if c.name == CHECK_TRANSFORMATION_CENTER)


# ============================================================ R5-01 覆盖

def test_r5_01_half_declared_products_partial() -> None:
    """R5 复审反例,基线 293bc62 红:真实 CCO→CC=O 证据用于
    CCO → 1/2 CC=O + 1/2 C1CO1 + H2 —— 数值完全配平(元素/电荷账
    verified),但额外环氧乙烷产物从未核验、乙醛只申报半份(声明
    1/2 ≠ λ_s=1)⇒ 覆盖 partial、中心 unknown、不 R6(基线曾
    full/verified/expand)。"""
    evidence = _oxidation_evidence()
    states = _states(ETHANOL, ACETALDEHYDE, EPOXIDE, HYDROGEN)
    hyp = _hyp(states, [(ETHANOL, 1)],
               [(ACETALDEHYDE, Fraction(1, 2)),
                (EPOXIDE, Fraction(1, 2)),
                (HYDROGEN, 1)], group="r6-half")
    audit = _audit(states, hyp, evidence)
    center = _center(audit)
    assert center.status == CHECK_UNKNOWN
    assert "partial_coverage_unchecked_transformation" in center.reason_code
    assert center.detail["product_coverage"] == \
        "partial_unchecked_transformation"
    # 覆盖轴独立:元素/电荷账仍 verified(账平不能兜底覆盖判定)
    assert audit.check_status(CHECK_ELEMENT_ACCOUNTING) == CHECK_VERIFIED
    assert audit.check_status(
        CHECK_FORMAL_CHARGE_ACCOUNTING) == CHECK_VERIFIED
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert d == ADMISSION_RETAIN_CONDITIONAL
    assert d != ADMISSION_EXPAND
    # 关断点:系数绑定(乙醛声明 1/2,要求 λ_s×1=1)
    violations = center.detail["coverage_violations"]
    coeff = [v for v in violations
             if v["kind"] == "coefficient_binding_mismatch"]
    assert coeff and coeff[0]["identity"] == ACETALDEHYDE
    assert coeff[0]["declared_total"] == "1/2"
    assert coeff[0]["required"] == "1"
    # 额外环氧乙烷 + H2 的补全盈余(Σ 未覆盖产物元素超 λ_s×Δ⁺)
    surplus = [v for v in violations
               if v["kind"] == "completion_surplus" and v["side"] ==
               "product"]
    assert surplus


def test_r5_01_cosubstrate_to_scaled_product_partial() -> None:
    """R5 复审反例,基线 293bc62 红:真实 CC=O→CCO 证据用于
    CC=O + C1CO1 + 2H2 → 2CCO —— 数值配平,但额外环氧乙烷开环/还原
    未进入编辑证据,且覆盖产物 CCO 声明 2 ≠ λ_s×1=1 ⇒ partial/
    unknown、不 R6(基线曾 full/verified/expand)。"""
    evidence = _reduction_evidence()
    states = _states(ACETALDEHYDE, EPOXIDE, HYDROGEN, ETHANOL)
    hyp = _hyp(states, [(ACETALDEHYDE, 1), (EPOXIDE, 1), (HYDROGEN, 2)],
               [(ETHANOL, 2)], group="r6-scale2")
    audit = _audit(states, hyp, evidence)
    center = _center(audit)
    assert center.status == CHECK_UNKNOWN
    assert "partial_coverage_unchecked_transformation" in center.reason_code
    assert center.detail["product_coverage"] == \
        "partial_unchecked_transformation"
    assert audit.check_status(CHECK_ELEMENT_ACCOUNTING) == CHECK_VERIFIED
    assert audit.check_status(
        CHECK_FORMAL_CHARGE_ACCOUNTING) == CHECK_VERIFIED
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert d != ADMISSION_EXPAND
    # 关断点:系数绑定(CCO 声明 2,要求 1)+ 未覆盖反应物侧盈余
    coeff = [v for v in center.detail["coverage_violations"]
             if v["kind"] == "coefficient_binding_mismatch"]
    assert coeff and coeff[0]["identity"] == ETHANOL
    assert coeff[0]["declared_total"] == "2"
    assert coeff[0]["required"] == "1"
    assert center.detail["uncovered_reactant_elements"] == \
        {"C": "2", "H": "8", "O": "1"}


def test_r5_01_genuine_oxidation_control_full() -> None:
    """正控制(基线 293bc62 绿,须保持):真实乙醇氧化证据绑定
    CCO→CC=O+H2(λ_s=1;未覆盖产物 H2 == λ_s×Δ⁺=2H)⇒ full、
    verified、expand。"""
    evidence = _oxidation_evidence()
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [(ETHANOL, 1)],
               [(ACETALDEHYDE, 1), (HYDROGEN, 1)])
    audit = _audit(states, hyp, evidence)
    center = _center(audit)
    assert center.status == CHECK_VERIFIED
    assert center.detail["product_coverage"] == "full"
    assert center.detail["substrate_scale"] == "1"
    assert center.detail["atom_delta"] == {"H": "2"}
    assert center.detail["uncovered_product_elements"] == {"H": "2"}
    assert center.detail["coverage_violations"] == []
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert d == ADMISSION_EXPAND


def test_r5_01_genuine_hydrogenation_control_full() -> None:
    """正控制(基线绿,须保持):真实乙醛氢化证据绑定
    CC=O+H2→CCO(Δ=H:−2;未覆盖反应物 H2 == λ_s×(−Δ)⁺=2H)
    ⇒ full、verified、expand。"""
    evidence = _reduction_evidence()
    states = _states(ACETALDEHYDE, HYDROGEN, ETHANOL)
    hyp = _hyp(states, [(ACETALDEHYDE, 1), (HYDROGEN, 1)],
               [(ETHANOL, 1)])
    audit = _audit(states, hyp, evidence)
    center = _center(audit)
    assert center.status == CHECK_VERIFIED
    assert center.detail["product_coverage"] == "full"
    assert center.detail["atom_delta"] == {"H": "-2"}
    assert center.detail["uncovered_reactant_elements"] == {"H": "2"}
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert d == ADMISSION_EXPAND


def test_r5_01_fragment_split_control_full() -> None:
    """正控制(基线绿,须保持):真实断裂分列产物(执行器产物
    C.CO;假设产物 C、CO 各为参与物)⇒ fragments 两级映射 + 注册
    补全规则(Δ=H:−2;未覆盖反应物 H2 == (−Δ)⁺=2H)⇒ full、
    verified、expand。"""
    render_result = roundtrip(ETHANOL, name="S")
    edits = [{"op": "break_bond", "atom1": "S_C_1", "atom2": "S_C_2"}]
    execution = execute_edits(render_result, edits)
    assert execution["ok"] is True
    assert execution["product_smiles"] == "C.CO"
    diag = check_edit_against_donor(
        current={"smiles": render_result.smiles,
                 "atom_id_map": dict(render_result.atom_id_map)},
        donor={"center_atom_ids": ["d1", "d2"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"d1": "S_C_1", "d2": "S_C_2"},
                   "equivalence_classes": [], "ref": "r6-frag"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.reaction_center_match is True
    evidence = center_evidence_from_donor_diagnostic(diag)
    states = _states(ETHANOL, HYDROGEN, "C", "CO")
    hyp = _hyp(states, [(ETHANOL, 1), (HYDROGEN, 1)], [("C", 1), ("CO", 1)],
               group="r6-frag")
    audit = _audit(states, hyp, evidence)
    center = _center(audit)
    assert center.status == CHECK_VERIFIED
    assert center.detail["coverage_mode"] == "fragments"
    assert center.detail["product_coverage"] == "full"
    assert center.detail["substrate_scale"] == "1"
    assert center.detail["atom_delta"] == {"H": "-2"}
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert d == ADMISSION_EXPAND


def test_r5_01_fragment_lumped_control_whole_molecule() -> None:
    """正控制(基线绿,须保持):合并单参与物 C.CO ⇒ whole_molecule
    整分子映射;补全规则同过(H2 == (−Δ)⁺)⇒ full。"""
    render_result = roundtrip(ETHANOL, name="S")
    edits = [{"op": "break_bond", "atom1": "S_C_1", "atom2": "S_C_2"}]
    execution = execute_edits(render_result, edits)
    diag = check_edit_against_donor(
        current={"smiles": render_result.smiles,
                 "atom_id_map": dict(render_result.atom_id_map)},
        donor={"center_atom_ids": ["d1", "d2"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"d1": "S_C_1", "d2": "S_C_2"},
                   "equivalence_classes": [], "ref": "r6-lump"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    evidence = center_evidence_from_donor_diagnostic(diag)
    states = _states(ETHANOL, HYDROGEN, "C.CO")
    hyp = _hyp(states, [(ETHANOL, 1), (HYDROGEN, 1)], [("C.CO", 1)],
               group="r6-lump")
    audit = _audit(states, hyp, evidence)
    center = _center(audit)
    assert center.status == CHECK_VERIFIED
    assert center.detail["coverage_mode"] == "whole_molecule"
    assert center.detail["product_coverage"] == "full"


def test_r5_01_two_sided_isomer_no_cancellation() -> None:
    """R5-01 关断点(复审双侧反例,基线曾借'单侧空'误 full;
    v5 已拦双侧并存,v6 补数值语义):CCO+C1CC1→CC=O+H2+CC=C ——
    环丙烷→丙烯为同式量异构(C3H6→C3H6,净差可抵消),但两侧各自
    超出 Δ⁺/(−Δ)⁺(补全盈余)⇒ partial、unknown、不 R6。"""
    evidence = _oxidation_evidence()
    states = _states(ETHANOL, "C1CC1", ACETALDEHYDE, HYDROGEN, "CC=C")
    hyp = _hyp(states, [(ETHANOL, 1), ("C1CC1", 1)],
               [(ACETALDEHYDE, 1), (HYDROGEN, 1), ("CC=C", 1)],
               group="r6-iso")
    audit = _audit(states, hyp, evidence)
    center = _center(audit)
    assert center.status == CHECK_UNKNOWN
    assert "partial_coverage_unchecked_transformation" in center.reason_code
    assert center.detail["product_coverage"] == \
        "partial_unchecked_transformation"
    # 两侧各自的补全盈余(不许互相抵消)
    sides = {v["side"] for v in center.detail["coverage_violations"]
             if v["kind"] == "completion_surplus"}
    assert sides == {"product", "reactant"}
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert d != ADMISSION_EXPAND


def test_r5_01_legal_ratio_scaling_full() -> None:
    """正控制(v6 新增建议):合法比例缩放 2CCO→2CC=O+2H2(真实
    1×CCO→CC=O 证据;λ_s=2;覆盖产物声明 2 == λ_s×1;未覆盖 H2×2
    == λ_s×Δ⁺=4H)⇒ full、verified、expand。"""
    evidence = _oxidation_evidence()
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [(ETHANOL, 2)],
               [(ACETALDEHYDE, 2), (HYDROGEN, 2)], group="r6-scale-ok")
    audit = _audit(states, hyp, evidence)
    center = _center(audit)
    assert center.status == CHECK_VERIFIED
    assert center.detail["product_coverage"] == "full"
    assert center.detail["substrate_scale"] == "2"
    assert center.detail["uncovered_product_elements"] == {"H": "4"}
    assert center.detail["coverage_violations"] == []
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert d == ADMISSION_EXPAND


def test_r5_01_h2_not_exempt_by_name() -> None:
    """R5-01 验收:整类 H2/水/共底物不按名称免审 ——
    CCO→CC=O+2H2 的未覆盖产物元素(H:4)超出 λ_s×Δ⁺(H:2)=>
    补全盈余 ⇒ partial、中心 unknown(元素账另轴 violated,不在此
    重复,但覆盖轴按注册规则如实关断)。"""
    evidence = _oxidation_evidence()
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [(ETHANOL, 1)],
               [(ACETALDEHYDE, 1), (HYDROGEN, 2)], group="r6-h2x2")
    audit = _audit(states, hyp, evidence)
    center = _center(audit)
    assert center.status == CHECK_UNKNOWN
    assert center.detail["product_coverage"] == \
        "partial_unchecked_transformation"
    surplus = [v for v in center.detail["coverage_violations"]
               if v["kind"] == "completion_surplus" and v["element"] == "H"]
    assert surplus and surplus[0]["declared_total"] == "4"
    assert surplus[0]["required"] == "2"
    d, _ = decide_admission(audit)
    assert d != ADMISSION_EXPAND


def test_r5_01_unknown_coefficient_coverage_unknown() -> None:
    """R5-01 语义 6:参与物系数未知 ⇒ 覆盖结果 unknown_coefficients
    (λ_s/贡献规模不可算,不冒充已覆盖;中心 unknown、不 R6)。"""
    evidence = _oxidation_evidence()
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp_with_unknown(
        states,
        [(ETHANOL, 1, True)],
        [(ACETALDEHYDE, 1, True), (HYDROGEN, None, False)],
        group="r6-unkcoeff")
    audit = _audit(states, hyp, evidence)
    center = _center(audit)
    assert center.status == CHECK_UNKNOWN
    assert "unknown_coefficients" in center.reason_code
    assert center.detail["product_coverage"] == "unknown_coefficients"
    d, _ = decide_admission(audit)
    assert d != ADMISSION_EXPAND


def test_r5_01_completion_rule_registered_and_disclosed() -> None:
    """R5-01 披露:补全规则以注册常量名入 detail(coverage_rule);
    substrate_scale/atom_delta/两侧未覆盖元素/逐条 violations 全部
    机器可读。"""
    evidence = _oxidation_evidence()
    states = _states(ETHANOL, ACETALDEHYDE, EPOXIDE, HYDROGEN)
    hyp = _hyp(states, [(ETHANOL, 1)],
               [(ACETALDEHYDE, Fraction(1, 2)),
                (EPOXIDE, Fraction(1, 2)), (HYDROGEN, 1)],
               group="r6-disc")
    audit = _audit(states, hyp, evidence)
    center = _center(audit)
    detail = center.detail
    assert detail["coverage_rule"] == COVERAGE_COMPLETION_RULE
    assert detail["coverage_rule"] == \
        "atom_delta_stoichiometric_completion"
    assert detail["substrate_scale"] == "1"
    assert detail["atom_delta"] == {"H": "2"}
    assert detail["uncovered_reactant_elements"] == {}
    assert detail["uncovered_product_elements"] == \
        {"C": "1", "H": "4", "O": "1/2"}
    kinds = {v["kind"] for v in detail["coverage_violations"]}
    assert "coefficient_binding_mismatch" in kinds
    assert "completion_surplus" in kinds
    # 每条 violation 带数值
    for violation in detail["coverage_violations"]:
        assert violation.get("declared_total") is not None
        assert violation.get("required") is not None


# ============================================================ R5-02 原始 CX

def test_r5_02_raw_r_flag_rejected_not_same_id() -> None:
    """R5 复审反例,基线 293bc62 红:build_chemical_state(
    'C[C@@H](N)C(=O)O |r|') —— |r| 被 RDKit MolFromSmiles 静默丢弃后
    与裸串同 state_id/as_written;v6 输入侧注册感知校验 ⇒ 构造即拒
    (unregistered_cx_class);strict_identity_of 同拒(公共入口一致)。"""
    bare = build_chemical_state("C[C@@H](N)C(=O)O",
                                STRUCTURE_ORIGIN_RAW_INPUT)
    with pytest.raises(ChemicalStateError) as ei:
        build_chemical_state("C[C@@H](N)C(=O)O |r|",
                             STRUCTURE_ORIGIN_RAW_INPUT)
    assert ei.value.detail["kind"] == "unregistered_cx_class"
    with pytest.raises(ChemicalStateError) as ei_strict:
        strict_identity_of("C[C@@H](N)C(=O)O |r|")
    assert ei_strict.value.detail["kind"] == "unregistered_cx_class"
    assert bare.state_id  # 裸输入正常(对照)


def test_r5_02_raw_ln_block_rejected() -> None:
    """R5 复审反例,基线 293bc62 红:'C1CCCCC1 |Ln:1|' 被解析器丢弃
    后与裸环己烷同 ID ⇒ 构造即拒;strict_identity_of 同拒。"""
    bare = build_chemical_state("C1CCCCC1", STRUCTURE_ORIGIN_RAW_INPUT)
    with pytest.raises(ChemicalStateError) as ei:
        build_chemical_state("C1CCCCC1 |Ln:1|",
                             STRUCTURE_ORIGIN_RAW_INPUT)
    assert ei.value.detail["kind"] == "unregistered_cx_class"
    with pytest.raises(ChemicalStateError):
        strict_identity_of("C1CCCCC1 |Ln:1|")
    assert bare.state_id


@pytest.mark.parametrize("structure", [
    "CO |c:1|", "CO |wU:1.5|", "CO |o:1|", "CO |O:1|",
    "CO |d:1|", "CO |n:1|", "CO |F:1|", "C[C@H](F)Cl |w:1.0|",
])
def test_r5_02_other_dropped_classes_rejected(structure) -> None:
    """R5-02 拒绝表:其余被解析器静默丢弃的未登记类(c/wU/o/O/d/
    n/F/Ln 等)⇒ 输入侧构造即拒,不默认丢弃后称 as_written。"""
    with pytest.raises(ChemicalStateError) as ei:
        build_chemical_state(structure, STRUCTURE_ORIGIN_RAW_INPUT)
    assert ei.value.detail["kind"] == "unregistered_cx_class"


@pytest.mark.parametrize("structure", [
    "CO |atomProp:0.note.hello|",
    "CO |$_AV:one;two$|",
    "CO |$mylabel$|",
    "CO |(0.5,0.8,;1,0.1,0.2,)|",
])
def test_r5_02_registered_removal_classes_same_id(structure) -> None:
    """R5-02 正控制(基线绿,须保持):登记移除类(atomProp/
    $_AV/$标签$/坐标)与裸输入同 state_id(生成前清除,合法)。"""
    bare = build_chemical_state("CO", STRUCTURE_ORIGIN_RAW_INPUT)
    st = build_chemical_state(structure, STRUCTURE_ORIGIN_RAW_INPUT)
    assert st.state_id == bare.state_id


def test_r5_02_sgD_comma_value_passes_input_guard() -> None:
    """R5-02 边界:SgD 值含逗号 ⇒ 登记移除类按**类级**放行(不按
    逗号拆整段查内容);与裸输入同 id。"""
    bare = build_chemical_state("CO", STRUCTURE_ORIGIN_RAW_INPUT)
    st = build_chemical_state("CO |SgD:0:note:a,b::::|",
                              STRUCTURE_ORIGIN_RAW_INPUT)
    assert st.state_id == bare.state_id


def test_r5_02_sru_retained_input_and_roundtrip() -> None:
    """R5-02 正控制:SRU(Sg,登记保留类)⇒ 输入放行、化学事实保留
    (与裸串不同 id)、往返重建同 id。"""
    bare = build_chemical_state("CCCCCC", STRUCTURE_ORIGIN_RAW_INPUT)
    st = build_chemical_state("CCCCCC |Sg:n:1,2,3:3:ht:::|",
                              STRUCTURE_ORIGIN_RAW_INPUT)
    assert st.state_id != bare.state_id
    st2 = build_chemical_state(st.smiles_isomeric,
                               STRUCTURE_ORIGIN_RAW_INPUT)
    assert st2.state_id == st.state_id


def test_r5_02_enhanced_group_radical_mapping_inputs_pass() -> None:
    """R5-02 正控制:增强立体组/自由基层(登记保留注记类)与原子
    映射号输入正常构造;增强组/自由基保留为化学事实。"""
    st = build_chemical_state("C[C@H](Cl)[C@H](F)Cl |a:1,&1:3|",
                              STRUCTURE_ORIGIN_RAW_INPUT)
    # ABS 组是冗余注记(剥离);AND 组保留为化学事实
    assert st.smiles_isomeric == "C[C@H](Cl)[C@H](F)Cl |&1:3|"
    radical = build_chemical_state("CO |^1:0|",
                                   STRUCTURE_ORIGIN_RAW_INPUT)
    bare_co = build_chemical_state("CO", STRUCTURE_ORIGIN_RAW_INPUT)
    assert radical.state_id != bare_co.state_id  # 自由基是化学事实
    mapped = build_chemical_state("[CH3:1][CH2:2][OH:3]",
                                  STRUCTURE_ORIGIN_RAW_INPUT)
    bare_ethanol = build_chemical_state("CCO", STRUCTURE_ORIGIN_RAW_INPUT)
    assert mapped.state_id == bare_ethanol.state_id  # 映射号不入身份


def test_r5_02_double_pipe_segment_rejected() -> None:
    """R5-02 双管道段:串中全部 |...| 段都被提取校验 —— 合法段 +
    非法段(如 'CC |a:1| |r|')同样拒绝(解析器只静默丢 r)。"""
    with pytest.raises(ChemicalStateError) as ei:
        build_chemical_state("CC |a:1| |r|", STRUCTURE_ORIGIN_RAW_INPUT)
    assert ei.value.detail["kind"] == "unregistered_cx_class"
    with pytest.raises(ChemicalStateError):
        build_chemical_state("CO |r| |atomProp:0.n.x|",
                             STRUCTURE_ORIGIN_RAW_INPUT)


def test_r5_02_annotation_token_level_guard() -> None:
    """R5-02 注记类 token 级校验:a/oN/&N/^N 块内 token 须为注记头
    或裸数字原子列表延续;混合未登记头(如 a:1,x:2)⇒ 拒绝。"""
    st = build_chemical_state("C[C@H](Cl)[C@H](F)Cl |a:1,&1:3|",
                              STRUCTURE_ORIGIN_RAW_INPUT)
    assert st.state_id
    with pytest.raises(ChemicalStateError) as ei:
        build_chemical_state("CC |a:1,x:2|", STRUCTURE_ORIGIN_RAW_INPUT)
    assert ei.value.detail["kind"] == "unregistered_cx_class"
    with pytest.raises(ChemicalStateError):
        build_chemical_state("CC |a:1,2x|", STRUCTURE_ORIGIN_RAW_INPUT)


def test_r5_02_unparseable_smiles_still_own_kind() -> None:
    """R5-02 机读码分列:语法整体不可解析且无违规 CX 块 ⇒ 维持
    unparseable_smiles(与 unregistered_cx_class 同为拒绝、码不同)。"""
    with pytest.raises(ChemicalStateError) as ei:
        build_chemical_state("not-a-smiles", STRUCTURE_ORIGIN_RAW_INPUT)
    assert ei.value.detail["kind"] == "unparseable_smiles"


# ============================================================ R5-08 镜像

def _sigma_break_diag(substrate, pair, name="U"):
    """真实 render → execute_edits → 诊断(全体原子为中心,公开链)。"""
    rendered = render(substrate, name=name)
    ids = {idx: aid for aid, idx in rendered.atom_id_map.items()}
    edits = [{"op": "break_bond", "atom1": ids[pair[0]],
              "atom2": ids[pair[1]]}]
    execution = execute_edits(rendered, edits)
    assert execution["ok"] is True
    diag = check_edit_against_donor(
        current={"smiles": rendered.smiles,
                 "atom_id_map": dict(rendered.atom_id_map)},
        donor={"center_atom_ids": [f"d{i}" for i in range(len(ids))]},
        alignment={"status": "resolved",
                   "donor_to_current": {f"d{i}": ids[i] for i in ids},
                   "equivalence_classes": [], "ref": "r6-mirror"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    return execution, diag


def test_r5_08_adjacent_sigma_break_zero_mismatch() -> None:
    """R5 复审反例,基线 293bc62 红:真实 C/C=C/C 断邻位 σ 键
    (render 后 0–1 号原子键)—— 执行器产物 C.C=CC 被序列化后消费,
    双键端烯化 E/Z 自然消失;内存镜像残留陈旧 STEREOE 曾误报
    undeclared_bond_change U_C_2–U_C_3。v6 镜像同走写出/重解析 ⇒
    零失配,center/strict 可 True。"""
    execution, diag = _sigma_break_diag("C/C=C/C", (0, 1))
    assert execution["product_smiles"] == "C.C=CC"
    assert diag.declaration_mismatches == []
    assert diag.reaction_center_match is True
    assert diag.strict_target_match is True


def test_r5_08_distal_tail_break_control() -> None:
    """正控制(基线绿,须保持):远端断尾(C/C=C/CCC 断 4–5)——
    双键 E/Z 保留;零失配、center/strict True。"""
    _, diag = _sigma_break_diag("C/C=C/CCC", (4, 5))
    assert diag.declaration_mismatches == []
    assert diag.reaction_center_match is True


def test_r5_08_alkene_order_change_control() -> None:
    """正控制(基线绿,须保持):双键改单键 —— 零失配、center True。"""
    rendered = render("C/C=C/C", name="V")
    ids = {idx: aid for aid, idx in rendered.atom_id_map.items()}
    edits = [{"op": "change_bond_order", "atom1": ids[1], "atom2": ids[2],
              "from_order": "double", "to_order": "single"}]
    execution = execute_edits(rendered, edits)
    assert execution["ok"] is True
    diag = check_edit_against_donor(
        current={"smiles": rendered.smiles,
                 "atom_id_map": dict(rendered.atom_id_map)},
        donor={"center_atom_ids": [f"d{i}" for i in range(len(ids))]},
        alignment={"status": "resolved",
                   "donor_to_current": {f"d{i}": ids[i] for i in ids},
                   "equivalence_classes": [], "ref": "r6-order"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.declaration_mismatches == []
    assert diag.reaction_center_match is True


def test_r5_08_alkene_bond_break_control() -> None:
    """正控制(基线绿,须保持):断双键本身(1–2)—— 零失配、
    center True。"""
    _, diag = _sigma_break_diag("C/C=C/C", (1, 2))
    assert diag.declaration_mismatches == []
    assert diag.reaction_center_match is True


# ============================================================ P2 披露

def test_p2_basis_and_proof_scope_disclosed() -> None:
    """P2(§4 披露项 1,基线 293bc62 红:reason 码 basis= 空串、
    detail 无 proof_scope):真实诊断载荷披露 center_match_basis=
    direct 与 proof_scope=self_contained_recompute;audit 复算分支
    同源披露,verified 理由码 basis= 非空。"""
    evidence = _oxidation_evidence()
    assert evidence["center_match_basis"] == "direct"
    assert evidence["proof_scope"] == "self_contained_recompute"
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [(ETHANOL, 1)],
               [(ACETALDEHYDE, 1), (HYDROGEN, 1)], group="r6-p2")
    audit = _audit(states, hyp, evidence)
    center = _center(audit)
    assert center.status == CHECK_VERIFIED
    assert center.detail["proof_scope"] == "self_contained_recompute"
    assert center.detail["center_match_basis"] == "direct"
    assert "basis=direct" in center.reason_code
    assert "basis=" not in center.reason_code.replace("basis=direct", "")


def test_p2_tampered_basis_integrity_reject() -> None:
    """P2:篡改 basis(声称 symmetric_equivalent,复算为 direct)
    ⇒ center_evidence_integrity_mismatch 结构化拒绝(自报 basis ≠
    复算 basis)。"""
    evidence = _oxidation_evidence()
    tampered = dict(evidence)
    tampered["center_match_basis"] = "symmetric_equivalent"
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [(ETHANOL, 1)],
               [(ACETALDEHYDE, 1), (HYDROGEN, 1)], group="r6-p2t")
    with pytest.raises(AuditContractError) as ei:
        audit_hypothesis(
            hyp, states={s.state_id: s for s in states.values()},
            context=_aerobic_context(), center_evidence=tampered)
    assert ei.value.detail["kind"] == "center_evidence_integrity_mismatch"
    assert any("center_match_basis" in m
               for m in ei.value.detail["mismatches"])
