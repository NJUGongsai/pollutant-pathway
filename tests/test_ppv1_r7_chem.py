"""R7 化学与证据线回归(Codex R6 复审 R6-01/R6-02;v7)。

规则级合成夹具;无金标/封存材料。先红后绿:红验证在基线 6d90201
工作树复跑本文件(与 R6 同口径);v7 实现后全绿。

R6-01:补全许可按严格结构身份注册 —— 真实 AtomTool C→CCCO(依次
新增 C/C/O,不载入任何共底物初始图)的证据用于 C+CC=O/C+C1CO1/
C+C=CO→CCCO:数值全配平不证明三种 C2H4O 初始图(乙醛 C=O/环氧
环键/乙烯醇 C=C)的贡献已核实 ⇒ partial/unknown、不 R6;H2/[H]
氢当量正控保持 full/verified/expand。
R6-02A:工厂/strict 输入侧守卫按真实 CX 类边界逐项词法 —— 登记头
(atomProp/SgD/Sg)之后的**并列未知项**(…,r / …,Ln:1 / …,w:1.0)
显式拒绝;DAT 值内逗号、登记内容含空格(§4-1 P2)继续受保护。
R6-02B:供体诊断 current/mapped/plain/target 四个原始字符串入口与
工厂/strict 同源守卫;未登记 CX 项 ⇒ 结构化拒绝,不得剥标记后当
verified 证据(基线:current/mapped 加 |r| 后仍 True/True、公共
audit→R6;指定手性底物远端编辑同样成立)。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.audit import (  # noqa: E402
    ADMISSION_EXPAND,
    ADMISSION_RETAIN_CONDITIONAL,
    AuditContractError,
    CHECK_TRANSFORMATION_CENTER,
    CHECK_UNKNOWN,
    CHECK_VERIFIED,
    COMPLETION_LICENSE,
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
    PARTICIPANT_LIST_DECLARED_COMPLETE,
    PARTICIPANT_ROLE_COPRODUCT,
    PARTICIPANT_ROLE_COSUBSTRATE,
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
    roundtrip,
    validate_edits,
)

METHANE = "C"
PROPANOL = "CCCO"
ETHANOL = "CCO"
ACETALDEHYDE = "CC=O"
HYDROGEN = "[H][H]"
ATOMIC_H = "[H]"
EPOXIDE = "C1CO1"
VINYL_ALCOHOL = "C=CO"
SRC = ["src:rule-r7"]


# ---------------------------------------------------------------- 夹具

def _sub(ref, coefficient=1):
    return Participant(
        state_ref=ref, side=PARTICIPANT_SIDE_REACTANT,
        role="primary_substrate", coefficient=coefficient,
        coefficient_status=COEFFICIENT_KNOWN)


def _cosub(ref, coefficient=1):
    return Participant(
        state_ref=ref, side=PARTICIPANT_SIDE_REACTANT,
        role=PARTICIPANT_ROLE_COSUBSTRATE, coefficient=coefficient,
        coefficient_status=COEFFICIENT_KNOWN)


def _prod(ref, coefficient=1, role=PARTICIPANT_ROLE_PRINCIPAL_PRODUCT):
    return Participant(
        state_ref=ref, side=PARTICIPANT_SIDE_PRODUCT, role=role,
        coefficient=coefficient, coefficient_status=COEFFICIENT_KNOWN)


def _states(*smiles, origin=STRUCTURE_ORIGIN_SOURCE_PRODUCT):
    return {s: build_chemical_state(s, origin) for s in smiles}


def _hyp(states, reactants, products, group="r7-chem"):
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
                   "equivalence_classes": [], "ref": "r7"},
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


def _methane_to_propanol_evidence():
    """真实 AtomTool C→CCCO(依次新增 C/C/O;不载入任何共底物图)。

    R6 复审 R6-01 的攻击基准:验证/执行成功、新增 ID 与中心映射完整、
    checker center/strict=True、未篡改 proof 轴 —— 但该执行**没有
    载入、映射或编辑任何共底物初始分子图**。
    """
    render_result = roundtrip(METHANE, name="S")
    edits = [
        {"op": "add_atom", "atom1": "S_C_1", "element": "C",
         "new_atom_id": "S_C_2"},
        {"op": "add_atom", "atom1": "S_C_2", "element": "C",
         "new_atom_id": "S_C_3"},
        {"op": "add_atom", "atom1": "S_C_3", "element": "O",
         "new_atom_id": "S_O_1"},
    ]
    validation = validate_edits(render_result, edits)
    execution = execute_edits(render_result, edits)
    assert validation["ok"] is True and execution["ok"] is True
    assert execution["product_smiles"] == PROPANOL
    diag = check_edit_against_donor(
        current={"smiles": render_result.smiles,
                 "atom_id_map": dict(render_result.atom_id_map)},
        donor={"center_atom_ids": [
            f"d{i}" for i in range(len(execution["atom_id_map"]))]},
        alignment={"status": "resolved",
                   "donor_to_current": {
                       f"d{i}": aid for i, aid in
                       enumerate(execution["atom_id_map"])},
                   "equivalence_classes": [],
                   "ref": "r7:added-atoms"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.reaction_center_match is True
    assert diag.strict_target_match is True
    return center_evidence_from_donor_diagnostic(diag)


def _audit(states, hyp, evidence):
    return audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=evidence)


def _center(audit):
    return next(c for c in audit.checks
                if c.name == CHECK_TRANSFORMATION_CENTER)


# ==================================================== R6-01 补全许可

@pytest.mark.parametrize("cosubstrate", ["CC=O", "C1CO1", "C=CO"])
def test_r6_01_complex_cosubstrate_completion_not_full(
        cosubstrate) -> None:
    """R6 复审反例,基线 6d90201 红:真实 AtomTool C→CCCO 证据用于
    C + C2H4O 异构体 → CCCO —— 数值全配平(Δ=C2H4O 恰为共底物
    组成),但乙醛 C=O/环氧环键/乙烯醇 C=C 的初始图贡献从未进入
    证明 ⇒ 补全许可未登记 ⇒ partial、中心 unknown、retain(基线曾
    元素/电荷/center 全 verified、full、R6 expand)。"""
    evidence = _methane_to_propanol_evidence()
    states = _states(METHANE, PROPANOL, cosubstrate)
    hyp = _hyp(states, [(METHANE, 1), (cosubstrate, 1)],
               [(PROPANOL, 1)], group=f"r7-license-{cosubstrate}")
    audit = _audit(states, hyp, evidence)
    center = _center(audit)
    assert center.status == CHECK_UNKNOWN
    assert center.reason_code.startswith(
        "center_evidence_partial_coverage")
    assert center.detail["product_coverage"] == \
        "partial_unchecked_transformation"
    license_violations = [
        v for v in center.detail["coverage_violations"]
        if v["kind"] == "completion_license_unregistered_identity"]
    assert license_violations, "未登记许可身份须入 coverage_violations"
    assert license_violations[0]["identities"] == [cosubstrate]
    assert center.detail["completion_license"] == COMPLETION_LICENSE
    assert center.detail["unlicensed_uncovered_identities"] == \
        [cosubstrate]
    admission = decide_admission(audit)
    assert admission[0] != ADMISSION_EXPAND
    assert admission[0] == ADMISSION_RETAIN_CONDITIONAL


def test_r6_01_license_scope_machine_disclosed() -> None:
    """R6-01 验收:规则 scope/依据机器披露 —— coverage_rule 与
    completion_license/作用域说明恒入 detail;数值配平不证明未登记
    多原子共底物初始图的结构贡献(说明文本明示)。"""
    evidence = _methane_to_propanol_evidence()
    states = _states(METHANE, PROPANOL, "CC=O")
    hyp = _hyp(states, [(METHANE, 1), ("CC=O", 1)], [(PROPANOL, 1)],
               group="r7-license-disc")
    center = _center(_audit(states, hyp, evidence))
    detail = center.detail
    assert detail["coverage_rule"] == COVERAGE_COMPLETION_RULE
    assert detail["completion_license"] == \
        "composition_only_hydrogen_equivalents"
    assert "composition_only_hydrogen_equivalents" in \
        detail["completion_license_scope"]
    assert detail["unlicensed_uncovered_identities"] == ["CC=O"]


def test_r6_01_hydrogen_equivalent_controls_stay_full() -> None:
    """正控(基线亦绿):H2 对 2[H] 的组成型氢当量在登记许可内 ——
    正常氧化(CCO→CC=O+H2)、氢化(CC=O+H2→CCO)与原子氢当量
    (CCO→CC=O+2[H])的数值补全保持 full、verified、expand
    (H2/[H] 只是 composition-only 作用域说明,不新增电子/自由基轴)。"""
    oxidation = _oxidation_evidence()
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [(ETHANOL, 1)],
               [(ACETALDEHYDE, 1), (HYDROGEN, 1)],
               group="r7-h2-ox")
    center = _center(_audit(states, hyp, oxidation))
    assert center.status == CHECK_VERIFIED
    assert center.detail["product_coverage"] == "full"
    assert decide_admission(_audit(states, hyp, oxidation))[0] == \
        ADMISSION_EXPAND

    reduction = _reduction_evidence()
    states = _states(ACETALDEHYDE, ETHANOL, HYDROGEN)
    hyp = _hyp(states, [(ACETALDEHYDE, 1), (HYDROGEN, 1)],
               [(ETHANOL, 1)], group="r7-h2-red")
    center = _center(_audit(states, hyp, reduction))
    assert center.status == CHECK_VERIFIED
    assert center.detail["product_coverage"] == "full"
    assert center.detail["unlicensed_uncovered_identities"] == []
    assert decide_admission(_audit(states, hyp, reduction))[0] == \
        ADMISSION_EXPAND

    states = _states(ETHANOL, ACETALDEHYDE, ATOMIC_H)
    hyp = _hyp(states, [(ETHANOL, 1)],
               [(ACETALDEHYDE, 1), (ATOMIC_H, 2)],
               group="r7-h-rad")
    center = _center(_audit(states, hyp, oxidation))
    assert center.status == CHECK_VERIFIED
    assert center.detail["product_coverage"] == "full"


def test_r6_01_license_binds_strict_identity_not_class_name() -> None:
    """R6-01 边界:许可以**严格结构身份**登记(不按整类名称免审)——
    同式量异构体 C1CC1(环丙烷)不在氢当量许可集内;数值上它不能
    配平此 Δ,但即便构造配平场景,非氢当量身份一律 partial。"""
    evidence = _methane_to_propanol_evidence()
    # C + C2H4O(环氧乙烷)数值恰配平 ⇒ 许可轴触发;换 C1CC1(C3H6)
    # 数值不配平 ⇒ 既有数值 violation + 许可 violation 并存
    states = _states(METHANE, PROPANOL, EPOXIDE, "C1CC1")
    hyp = _hyp(states, [(METHANE, 1), ("C1CC1", 1)], [(PROPANOL, 1)],
               group="r7-license-identity")
    center = _center(_audit(states, hyp, evidence))
    assert center.status == CHECK_UNKNOWN
    violations = {v["kind"] for v in
                  center.detail["coverage_violations"]}
    assert "completion_license_unregistered_identity" in violations
    assert center.detail["unlicensed_uncovered_identities"] == ["C1CC1"]


# ============================================== R6-02A 原始 CX 并列项

@pytest.mark.parametrize("structure", [
    # R6 复审原例:alanine atomProp 后并列 r
    "C[C@@H](N)C(=O)O |atomProp:0.note.hello,r|",
    # SgD 首头后并列 r(尾冒号后项边界)
    "CO |SgD:0:note:hello::::,r|",
    # DAT 值内逗号 + 尾部并列 r(值 'a,b' 受保护,r 是并列未知项)
    "CO |SgD:0:note:a,b::::,r|",
    # Sg 首头后并列 r
    "CCCCCC |Sg:n:1,2,3:3:ht:::,r|",
    # 登记头后并列其他未知类(Ln / w)
    "C1CCCCC1 |atomProp:0.note.hello,Ln:1|",
    "CO |atomProp:0.note.hello,w:1.0|",
    # 多个并列未知项
    "CO |SgD:0:note:hello::::,r,a:1|",
])
def test_r6_02a_parallel_unknown_after_registered_head_rejected(
        structure) -> None:
    """R6 复审反例,基线 6d90201 红:工厂与 strict 入口接受登记头后
    的并列未知项(RDKit 解析时静默丢弃 r/Ln/w,之后与裸串同
    state_id/as_written)⇒ v7 按真实 CX 类边界逐项词法,构造即拒
    (unregistered_cx_class,带并列项原文)。"""
    with pytest.raises(ChemicalStateError) as ei:
        build_chemical_state(structure, STRUCTURE_ORIGIN_RAW_INPUT)
    assert ei.value.detail["kind"] == "unregistered_cx_class"
    with pytest.raises(ChemicalStateError) as ei2:
        strict_identity_of(structure)
    assert ei2.value.detail["kind"] == "unregistered_cx_class"


@pytest.mark.parametrize("structure", [
    # DAT 值内逗号受保护(R5 既有正控,继续保留)
    "CO |SgD:0:note:a,b::::|",
    # SgD 之间逗号并列(真实解析器按项边界分派第二个 SgD)
    "CO |SgD:0:note:a::::,SgD:0:note:b::::|",
    # atomProp 重复头并列(解析器逐项分派)
    "CC |atomProp:0.a.x,atomProp:1.b.y|",
    # atomProp 写出器冒号形态(一项内多 prop)
    "CC |atomProp:0.a.x:1.b.y|",
    # 登记内容含空格(§4-1 P2 同修:值/字段/标签内容到真分隔符)
    "CC |atomProp:0.note.hello world|",
    "CO |SgD:0:note:hello world::::|",
    "C |$foo bar;$|",
    # 登记类正控:坐标、标签、增强立体、自由基层、SRU
    "C |(1,0,0;2,0,0)|",
    "C |$x$|",
    "C |$_AV:val1;val2$|",
    "C[C@H](Cl)[C@H](F)Cl |a:1,&1:3|",
    "CC |^1:0,1|",
    "CCCCCC |Sg:n:1,2,3:3:ht:::|",
    "CCCCCC |Sg:n:1,2,3:3:ht|",
])
def test_r6_02a_registered_content_passes(structure) -> None:
    """正控:登记类/受保护内容(DAT 逗号、含空格值、并列重复头、
    SgD/Sg/注记/标签/坐标)按真实类边界放行,可构造(语法不可解析
    的裸 CX 形态才走 unparseable_smiles)。"""
    try:
        build_chemical_state(structure, STRUCTURE_ORIGIN_RAW_INPUT)
        strict_identity_of(structure)
    except ChemicalStateError as exc:
        pytest.fail(f"登记内容被误拒:{exc.detail}")


def test_r6_02a_bare_unknown_still_rejected() -> None:
    """既有控制保持:单独未知旗标/类(基线已拒)继续拒绝。"""
    for structure in ("C |r|", "C |Ln:1|", "C |SgH:1:0|"):
        with pytest.raises(ChemicalStateError) as ei:
            build_chemical_state(structure, STRUCTURE_ORIGIN_RAW_INPUT)
        assert ei.value.detail["kind"] == "unregistered_cx_class"


# ============================================ R6-02B 供体诊断原始入口

def _oxidation_inputs():
    """真实乙醇氧化执行的完整诊断输入集(公开链,零篡改)。"""
    render_result = roundtrip(ETHANOL, name="S")
    edits = [{"op": "change_bond_order", "atom1": "S_C_2",
              "atom2": "S_O_1", "from_order": "single",
              "to_order": "double"}]
    execution = execute_edits(render_result, edits)
    assert execution["ok"] is True
    return render_result, edits, execution


def _check(current, edits, execution, target):
    return check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "r7"},
        expectation={"target_smiles": target},
        result=execution, edits=edits)


@pytest.mark.parametrize("field", ["current", "mapped", "plain", "target"])
def test_r6_02b_donor_raw_r_rejected_all_four_entries(field) -> None:
    """R6 复审反例,基线 6d90201 红(核心两轴):真实干净乙醇→乙醛
    执行,仅在接口原始字段加 |r| —— current 与 mapped product 基线
    诊断 True/True、公共 audit→R6(解析器剥标记后绑定身份);
    plain/target 基线 strict=None/retain(未误放行但不闭合)。
    v7:四个原始字符串入口统一走工厂同源守卫 ⇒ 结构化拒绝
    (raw_input_cx_class_unregistered,带字段名),任何轴不得以剥
    标记身份参与 verified 证据。"""
    render_result, edits, execution = _oxidation_inputs()
    current = {"smiles": render_result.smiles,
               "atom_id_map": dict(render_result.atom_id_map)}
    target = execution["product_smiles"]
    if field == "current":
        current = dict(current, smiles=current["smiles"] + " |r|")
    elif field == "mapped":
        execution = dict(execution,
                         product_mapped_smiles=(
                             execution["product_mapped_smiles"] + " |r|"))
    elif field == "plain":
        execution = dict(execution,
                         product_smiles=(
                             execution["product_smiles"] + " |r|"))
    else:
        target = target + " |r|"
    with pytest.raises(AuditContractError) as ei:
        _check(current, edits, execution, target)
    assert ei.value.detail["kind"] == "raw_input_cx_class_unregistered"
    assert ei.value.detail["field"] == {
        "current": "current.smiles",
        "mapped": "result.product_mapped_smiles",
        "plain": "result.product_smiles",
        "target": "expectation.target_smiles"}[field]


def test_r6_02b_audit_rerun_rejects_tainted_proof_record() -> None:
    """R6-02B 链条闭合:手工携带含 |r| 原始串的 proof_record 走公开
    audit 复算 ⇒ 复跑 checker 同守卫拒绝(结构化),不得经审计证据
    门洗成 verified/R6。"""
    render_result, edits, execution = _oxidation_inputs()
    evidence = {
        "checker_version": "ppv1-donor-diagnostic-9",
        "checker_scope": "region_net_change",
        "center_match": True, "center_match_basis": "direct",
        "declaration_mismatch": False, "strict_target_match": True,
        "proof_scope": "self_contained_recompute",
        "evidence_refs": ["r7"],
        "bound_inputs": {
            "substrate_identity": "CCO",
            "product_identity": "CC=O",
            "edits_signature": "x", "donor_centers": ["dC", "dO"],
            "alignment_ref": "r7", "execution_fingerprint": "x"},
        "proof_record": {
            "current": {"smiles": render_result.smiles + " |r|",
                        "atom_id_map": dict(
                            render_result.atom_id_map)},
            "donor": {"center_atom_ids": ["dC", "dO"]},
            "alignment": {"status": "resolved",
                          "donor_to_current": {"dC": "S_C_2",
                                               "dO": "S_O_1"},
                          "equivalence_classes": [], "ref": "r7"},
            "expectation": {"target_smiles":
                            execution["product_smiles"]},
            "result": dict(execution),
            "edits": list(edits),
        },
    }
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN,
                     origin=STRUCTURE_ORIGIN_RAW_INPUT)
    hyp = _hyp(states, [(ETHANOL, 1)],
               [(ACETALDEHYDE, 1), (HYDROGEN, 1)],
               group="r7-rerun-r")
    with pytest.raises(AuditContractError) as ei:
        audit_hypothesis(hyp,
                         states={s.state_id: s
                                 for s in states.values()},
                         context=_aerobic_context(),
                         center_evidence=evidence)
    assert ei.value.detail["kind"] == "raw_input_cx_class_unregistered"


def test_r6_02b_chiral_substrate_remote_edit_r_rejected() -> None:
    """R6 复审反例:指定手性底物 F[C@H](Cl)CCO 的远端氧化,仅在
    current 加 |r| —— 基线同样 R6(剥标记后远端编辑与手性无关);
    v7 入口守卫拒绝,不因中心远端而放行原始标记丢失。"""
    render_result = roundtrip("F[C@H](Cl)CCO", name="S")
    edits = [{"op": "change_bond_order", "atom1": "S_C_3",
              "atom2": "S_O_1", "from_order": "single",
              "to_order": "double"}]
    execution = execute_edits(render_result, edits)
    assert execution["ok"] is True
    current = {"smiles": render_result.smiles + " |r|",
               "atom_id_map": dict(render_result.atom_id_map)}
    with pytest.raises(AuditContractError) as ei:
        _check(current, edits, execution,
               execution["product_smiles"])
    assert ei.value.detail["kind"] == "raw_input_cx_class_unregistered"


def test_r6_02b_clean_diagnostic_controls_unchanged() -> None:
    """正控(基线亦绿):干净输入的诊断轴/绑定不变 —— True/True、
    basis=direct、绑定底物/产物身份同源。"""
    render_result, edits, execution = _oxidation_inputs()
    diag = _check({"smiles": render_result.smiles,
                   "atom_id_map": dict(render_result.atom_id_map)},
                  edits, execution, execution["product_smiles"])
    assert diag.reaction_center_match is True
    assert diag.strict_target_match is True
    assert diag.center_match_basis == "direct"
    assert diag.center_evidence["bound_inputs"][
        "substrate_identity"] == "CCO"
    assert diag.center_evidence["bound_inputs"][
        "product_identity"] == "CC=O"
