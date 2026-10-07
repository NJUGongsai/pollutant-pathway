"""R4 化学与证据线回归(Codex R3 复审 R3-01~05 + §4;v4)。

规则级合成夹具;模型 off,无金标/封存材料。每个用例对应复审反例或
验收边界;探针基线(af14fb2)见 docs/review_evidence/ppv1_r3_codex_2026-10-06/。

R3-01:证据绑定本反应/各轴消费/checker scope(跨反应复用与注册名
-only 不得 verified;区域 True 与 strict False 分别保留,适用失败不
消失于 all_verified)。
R3-02:联合映射保手性(meso 换位拒、真 C2 对称保持、增强立体
unsupported)。
R3-03:构型比较按映射配体奇偶法(CIP 标签仅披露;两组真实反例:
远端标签翻转非构型变化)。
R3-04:化学 CX 事实子集(坐标/标签/atomProp 不入身份;混合 ABS 归一)。
R3-05:声明净效应对账(add_atom 隐含锚键、有序操作净效应;中心原子
属性披露 center_property_deltas)。
R3-06/07/08:audit 真实消费链(候选级条件评估/依赖并集/完整
input_hash)。
§4:per-product off 披露。
"""

from __future__ import annotations

import sys
from pathlib import Path
from fractions import Fraction

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rdkit import Chem  # noqa: E402

from pathway_v43.pollutant.audit import (  # noqa: E402
    ADMISSION_EXPAND,
    ADMISSION_RETAIN_CONDITIONAL,
    AdmissionPolicy,
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
    STRUCTURE_ORIGIN_RAW_INPUT,
    STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    archive_recovered_fidelity,
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
    DEPENDENCY_SUPPORTED,
    build_condition_fact,
    build_dependency,
    build_path_context,
    build_requirement,
    derive_child_context,
    resolve_dependency,
)
from pathway_v43.services.atom_tool import (  # noqa: E402
    execute_edits,
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


def _prod(ref, coefficient=1, role=PARTICIPANT_ROLE_PRINCIPAL_PRODUCT):
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_PRODUCT,
                       role=role, coefficient=coefficient,
                       coefficient_status=COEFFICIENT_KNOWN)


def _states(*smiles, origin=STRUCTURE_ORIGIN_SOURCE_PRODUCT):
    return {s: build_chemical_state(s, origin) for s in smiles}


def _bound_hyp(states):
    """CCO → CC=O + [H][H](配平;绑定乙醇 C–O 诊断)。"""
    return build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      _prod(states[ACETALDEHYDE].state_id),
                      _prod(states[HYDROGEN].state_id, role="coproduct")],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="r4-chem")


def _aerobic_context():
    return build_path_context(
        requested_scope="condition_compatible",
        condition_facts=[
            build_condition_fact(key=CONDITION_KEY_OXYGEN,
                                 value="aerobic",
                                 status="known_present")],
        accumulated_requirements=[
            build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                              value="aerobic", source_refs=SRC)],
        assessment_scope=[CONDITION_KEY_OXYGEN])


def _ethanol_diag():
    render = roundtrip(ETHANOL, name="S")
    edits = [{"op": "change_bond_order",
              "atom1": "S_C_2", "atom2": "S_O_1",
              "from_order": "single", "to_order": "double"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    diag = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "r4"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    return diag


# ============================================================ R3-04 身份子集


def test_r3_04_nonchemical_cx_metadata_not_identity() -> None:
    """普通 CO / 原子标签 / 坐标 / atomProp note 五输入同键(R3-04)。"""
    inputs = ["CO", "CO |$Foo$|", "CO |(0,0,1,0)|",
              "CO |atomProp:0.note.hello|"]
    ids = {strict_identity_of(s) for s in inputs}
    assert len(ids) == 1


def test_r3_04_mixed_abs_annotations_normalized() -> None:
    """混合并列 ABS 归一(v3 段级正则漏剥):a:1,&1:3 ≡ &1:3 等
    (mimo A2b 三组 id 分裂反例)。"""
    assert strict_identity_of(
        "C[C@H](Cl)[C@H](F)Cl |a:1,&1:3|") == \
        strict_identity_of("C[C@H](Cl)[C@H](F)Cl |&1:3|")
    assert strict_identity_of(
        "[CH2][C@H](C)O |^1:0,a:1|") == \
        strict_identity_of("[CH2][C@H](C)O |^1:0|")
    # 控制保持:plain=ABS/整组反转/部分反转
    assert strict_identity_of("F[C@H](Cl)Br") == \
        strict_identity_of("F[C@H](Cl)Br |a:1|")
    assert strict_identity_of("C[C@H](O)CC |&1:1|") == \
        strict_identity_of("C[C@@H](O)CC |&1:1|")
    assert strict_identity_of("C[C@H](O)C[C@H](O)CC |&1:1,4|") != \
        strict_identity_of("C[C@@H](O)C[C@H](O)CC |&1:1,4|")


def test_r3_04_radical_fact_kept_public_repr_exception() -> None:
    """自由基是化学事实(保留 ^ 层,与普通甲烷分立);无组无自由基
    层的分子与普通 canonical 逐字相同(例外句,§4 行 8)。"""
    assert strict_identity_of("[CH3] |^1:0|") != strict_identity_of("C")
    state = build_chemical_state("CO", STRUCTURE_ORIGIN_RAW_INPUT)
    assert state.smiles_isomeric == "CO"
    radical = build_chemical_state("[CH3] |^1:0|",
                                    STRUCTURE_ORIGIN_RAW_INPUT)
    assert "^1:0" in radical.smiles_isomeric


# ============================================================ R3-02 手性感知


def _break_execution(smiles, pair, name="S"):
    render = roundtrip(smiles, name=name)
    edits = [{"op": "break_bond", "atom1": pair[0], "atom2": pair[1]}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True, execution.get("reasons")
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    return current, edits, execution, render


def test_r3_02_meso_stereodistinct_sites_not_equivalent() -> None:
    """R3-02 E-i 真实执行反例:meso 2,3-二氯戊烷(2S,3R),供体中心
    {C1,C2_S},实际断另一端 {C3_R,C4}。忽略手性有两个自匹配,保手性
    只有 identity ⇒ center **False**(v3 曾 True/symmetric_equivalent);
    实际产物与指定位点预期是不同 strict 身份(strict=False 由证据轴
    分开消费)。"""
    current, edits, execution, render = _break_execution(
        "C[C@H](Cl)[C@H](Cl)C", ("S_C_3_R", "S_C_4"))
    diag = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dA", "dB"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dA": "S_C_1", "dB": "S_C_2_S"},
                   "equivalence_classes": [], "ref": "meso"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.reaction_center_match is False  # v3 曾 True
    assert diag.center_match_basis == ""
    assert not diag.joint_mapping
    # 两个断键产物是不同严格身份(复审证据)
    _, _, other_exec, _ = _break_execution(
        "C[C@H](Cl)[C@H](Cl)C", ("S_C_1", "S_C_2_S"))
    assert strict_identity_of(execution["product_smiles"]) != \
        strict_identity_of(other_exec["product_smiles"])


def test_r3_02_true_c2_symmetric_swap_still_accepted() -> None:
    """真 C2 对称正控制:(2S,4S)-2,4-戊二醇的合法互换在保手性映射下
    保持接受(mimo:aware=2)。"""
    render = roundtrip("C[C@H](O)C[C@@H](O)C", name="S")
    # 中心 {C1,C2}(idx 0,1);编辑断镜像端键 C4–C5(idx 4,6)——
    # 保手性自同构的像(aware 实测 {(0,1),(4,6)})
    edits = [{"op": "break_bond", "atom1": "S_C_4_S",
              "atom2": "S_C_5"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True, execution.get("reasons")
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    diag = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dA", "dB"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dA": "S_C_1", "dB": "S_C_2_S"},
                   "equivalence_classes": [], "ref": "c2"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.reaction_center_match is True
    assert diag.center_match_basis == "symmetric_equivalent"


def test_r3_02_enhanced_stereo_joint_unsupported_unknown() -> None:
    """底物带增强立体组(AND/OR)⇒ 联合映射 unsupported ⇒ unknown
    (R3-02:声明支持的手性范围,不冒称全范围解决)。"""
    render = roundtrip("C[C@H](Cl)[C@H](F)Cl", name="S")
    edits = [{"op": "break_bond", "atom1": "S_C_3_R",
              "atom2": "S_F_1"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True, execution.get("reasons")
    # 诊断的 before mol 来自 current.smiles(带 |&1:3| 组输入),
    # 联合映射分支见组 ⇒ unsupported(声明支持范围,不冒称全范围)
    diag = check_edit_against_donor(
        current={"smiles": "C[C@H](Cl)[C@H](F)Cl |&1:3|",
                 "atom_id_map": dict(render.atom_id_map)},
        donor={"center_atom_ids": ["dA", "dB"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dA": "S_C_1", "dB": "S_C_2_S"},
                   "equivalence_classes": [], "ref": "enh"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.reaction_center_match is None
    # R5(R4-07):unsupported 消息覆盖增强组与非四面体两类
    assert any("joint_mapping_stereo_unsupported" in r
               for r in diag.missing_info_reasons)


# ============================================================ R3-03 构型比较


def test_r3_03_far_center_config_preserved_not_fake_change() -> None:
    """R3-03 反例 1(mimo E-ii):断正确键,远端手性原子构型保持
    (配体集合不变+奇偶法)⇒ 不产生假 stereo 变化、不误判
    center=False(v3 曾因 legacy CIP 伪翻 R→S 误报)。"""
    current, edits, execution, render = _break_execution(
        "C[C@H](Cl)[C@H](Cl)C", ("S_C_3_R", "S_C_4"))
    # 中心 = 被断键的两端:合法编辑,center 应 True(direct)
    diag = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dA", "dB"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dA": "S_C_3_R", "dB": "S_C_4"},
                   "equivalence_classes": [], "ref": "eii"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.reaction_center_match is True  # v3 曾 False(伪立体变化)
    assert diag.center_match_basis == "direct"
    # 远端原子 S_C_2_S 不在 extra_changes(构型保持,无变化)
    assert all(e["atom_id"] != "S_C_2_S" for e in diag.extra_changes)
    # 中心原子属性披露含断裂端原子(键断 ⇒ 立体丢失属真实变化)
    center_ids = {e["atom_id"] for e in diag.center_property_deltas}
    assert center_ids <= {"S_C_3_R", "S_C_4"} or center_ids == set()


def test_r3_03_ligand_priority_rerank_not_config_change() -> None:
    """R3-03 反例 2(复审新增):CCC[C@H](O)CC 的 C5–C6 单→双,
    原子 4(R,手性)配体集合不变;准确与 legacy CIP 都 R→S(优先级
    重排),构型实际保持 ⇒ 不得误报中心外构型变化(v3 曾
    center=False)。"""
    render = roundtrip("CCC[C@H](O)CC", name="S")
    edits = [{"op": "change_bond_order", "atom1": "S_C_5",
              "atom2": "S_C_6", "from_order": "single",
              "to_order": "double"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    diag = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dA", "dB"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dA": "S_C_5", "dB": "S_C_6"},
                   "equivalence_classes": [], "ref": "rerank"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.reaction_center_match is True  # v3 曾 False
    # 手性原子(远端)不在 extra(构型保持);标签重排不是变化
    chiral_atom = "S_C_4_R"
    assert all(e["atom_id"] != chiral_atom for e in diag.extra_changes)


def test_r3_03_real_inversion_detected_by_parity() -> None:
    """真实构型反转控制(接口合成结果):同配体集合下 @→@@ 翻转
    ⇒ 奇偶法判 stereo 变化可见;准确 CIP 标签进披露记录。"""
    render = roundtrip("C[C@H](Cl)[C@H](F)Cl", name="S")
    id_map = dict(render.atom_id_map)
    # 合成结果:第二个手性中心翻转(接口合成,不称执行器会产生)
    flipped = "C[C@H](Cl)[C@@H](F)Cl"
    mol = Chem.MolFromSmiles(flipped)
    idx_to_id = {i: aid for aid, i in id_map.items()}
    for atom in mol.GetAtoms():
        aid = idx_to_id.get(atom.GetIdx())
        if aid is not None:
            atom.SetAtomMapNum(atom.GetIdx() + 1)
    result = {"ok": True, "reasons": [],
              "product_smiles": flipped,
              "product_mapped_smiles": Chem.MolToSmiles(mol),
              "atom_id_map": dict(id_map)}
    diag = check_edit_against_donor(
        current={"smiles": render.smiles, "atom_id_map": dict(id_map)},
        donor={"center_atom_ids": ["dC"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_1"},
                   "equivalence_classes": [], "ref": "inv"},
        expectation={"target_smiles": flipped}, result=result, edits=[])
    assert diag.reaction_center_match is False  # 翻转原子在中心外
    entry = next(e for e in diag.extra_changes
                 if "stereo" in e.get("delta", []))
    assert entry["stereo"]["before_cip"] != entry["stereo"]["after_cip"]


# ============================================================ R3-05 净效应


def test_r3_05_add_atom_implicit_anchor_bond_accounted() -> None:
    """R3-05:合法 add_atom(atom1=C 锚, element=O)执行产物 CO;
    隐含锚键不再是 undeclared_bond_change(v3 曾误报声明失配)。"""
    render = roundtrip("C", name="A")
    edits = [{"op": "add_atom", "atom1": "A_C_1", "element": "O",
              "new_atom_id": "A_O_1"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True
    assert execution["product_smiles"] == "CO"
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    diag = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "A_C_1", "dO": "A_O_1"},
                   "equivalence_classes": [], "ref": "add"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.declaration_mismatches == []
    assert diag.reaction_center_match is True
    assert diag.center_match_basis == "direct"


def test_r3_05_ordered_ops_net_effect_accounted() -> None:
    """R3-05:同键按序 single→double→single→double(三个合法操作),
    最终 CC=O;净效应结算,中间态不要求逐条相等(v3 曾误报
    to_order 失配)。"""
    render = roundtrip(ETHANOL, name="S")
    edits = [
        {"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1",
         "from_order": "single", "to_order": "double"},
        {"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1",
         "from_order": "double", "to_order": "single"},
        {"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1",
         "from_order": "single", "to_order": "double"},
    ]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True
    assert execution["product_smiles"] == ACETALDEHYDE
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    diag = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "seq"},
        expectation={"target_smiles": ACETALDEHYDE},
        result=execution, edits=edits)
    assert diag.declaration_mismatches == []  # v3 曾 to_order 失配
    assert diag.reaction_center_match is True


def test_r3_05_center_property_deltas_disclosed() -> None:
    """R3-05/E-iii 电荷版:中心 N 原子未声明 +1(接口合成)——
    ops 对账不覆盖属性,但 center_property_deltas **披露**(v3
    全字段 verified 零披露)。"""
    render = roundtrip("NCC", name="S")
    id_map = dict(render.atom_id_map)
    result = {"ok": True, "reasons": [],
              "product_smiles": "[NH3+]CC",
              "product_mapped_smiles": _mapped("[NH3+]CC", id_map),
              "atom_id_map": dict(id_map)}
    diag = check_edit_against_donor(
        current={"smiles": render.smiles, "atom_id_map": dict(id_map)},
        donor={"center_atom_ids": ["dN"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dN": "S_N_1"},
                   "equivalence_classes": [], "ref": "eiii"},
        expectation={"target_smiles": "[NH3+]CC"},
        result=result, edits=[])
    assert diag.reaction_center_match is True  # 区域内
    deltas = {d["atom_id"]: d for d in diag.center_property_deltas}
    assert "S_N_1" in deltas
    assert deltas["S_N_1"]["formal_charge"] == [0, 1]
    assert "formal_charge" in deltas["S_N_1"]["property_delta"]


def _mapped(product_smiles: str, id_map: dict) -> str:
    """按构造索引生成带映射号的产物图(接口合成探针同型)。"""
    mol = Chem.MolFromSmiles(product_smiles)
    assert mol is not None, product_smiles
    idx_to_id = {i: aid for aid, i in id_map.items()}
    for atom in mol.GetAtoms():
        aid = idx_to_id.get(atom.GetIdx())
        if aid is not None:
            atom.SetAtomMapNum(atom.GetIdx() + 1)
    return Chem.MolToSmiles(mol)


def test_r3_05_center_stereo_inversion_disclosed_with_strict() -> None:
    """R3-05/E-iii 立体版(接口合成,不称真实执行器会产生未支持
    操作):中心内手性碳被注入未声明翻转 ⇒ 区域 True(变更集在中心
    内)+ center_property_deltas 披露 + strict=False(产物异种)——
    证据轴消费使 admission 不再全绿(R5v)。"""
    render = roundtrip("CCC[C@H](O)CC", name="S")  # 2-己醇骨架
    id_map = dict(render.atom_id_map)
    # 声明断末端键;真实执行得到声明产物(位点预期)
    edits = [{"op": "break_bond", "atom1": "S_C_5", "atom2": "S_C_6"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True
    expected_product = execution["product_smiles"]  # 声明位点产物
    # 接口合成(不称真实执行器会执行未支持操作):声明产物的键变化
    # 保持 + 中心原子注入未声明构型翻转 —— plain 与 mapped 同源
    flipped_mapped = Chem.MolFromSmiles(execution["product_mapped_smiles"])
    chiral_mapnum = id_map["S_C_4_R"] + 1
    for atom in flipped_mapped.GetAtoms():
        if atom.GetAtomMapNum() == chiral_mapnum:
            if atom.GetChiralTag() == Chem.ChiralType.CHI_TETRAHEDRAL_CW:
                atom.SetChiralTag(
                    Chem.ChiralType.CHI_TETRAHEDRAL_CCW)
            elif atom.GetChiralTag() == \
                    Chem.ChiralType.CHI_TETRAHEDRAL_CCW:
                atom.SetChiralTag(Chem.ChiralType.CHI_TETRAHEDRAL_CW)
    flipped_plain = Chem.Mol(flipped_mapped)
    for atom in flipped_plain.GetAtoms():
        atom.SetAtomMapNum(0)
    result = {"ok": True, "reasons": [],
              "product_smiles": Chem.MolToSmiles(flipped_plain),
              "product_mapped_smiles": Chem.MolToSmiles(flipped_mapped),
              "atom_id_map": dict(id_map)}
    diag = check_edit_against_donor(
        current={"smiles": render.smiles, "atom_id_map": dict(id_map)},
        donor={"center_atom_ids": ["dC", "dE", "dF"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_4_R", "dE": "S_C_5",
                                        "dF": "S_C_6"},
                   "equivalence_classes": [], "ref": "eiii-st"},
        expectation={"target_smiles": expected_product},  # 声明位点预期
        result=result, edits=edits)
    assert diag.reaction_center_match is True  # 区域内(区域轴保留)
    deltas = {d["atom_id"]: d for d in diag.center_property_deltas}
    assert "S_C_4_R" in deltas
    assert "stereo" in deltas["S_C_4_R"]["property_delta"]
    assert diag.strict_target_match is False  # 产物异种
    # 证据消费:strict=False ⇒ admission 不全绿(R5v,不到 R6)
    # 复审场景:合成假设与**实际执行(翻转)产物**配套(R3-02 同构);
    # 证据绑定核对实际产物,strict 轴对账声明位点预期 ⇒ False
    actual_product = result["product_smiles"]
    # 复审场景原句:"补 [H] 仅闭合数值账"(断键产物经 sanitize 调整
    # 隐式 H,数值上缺 2H ⇒ 加 H2 反应物闭合;不影响 strict 轴语义)
    states = _states("CCC[C@H](O)CC", actual_product, "[H][H]")
    hyp = build_hypothesis(
        parent_path_id="p1",
        substrate_state_ref=states["CCC[C@H](O)CC"].state_id,
        participants=[
            _sub(states["CCC[C@H](O)CC"].state_id),
            Participant(
                state_ref=states["[H][H]"].state_id,
                side=PARTICIPANT_SIDE_REACTANT,
                role=PARTICIPANT_ROLE_COSUBSTRATE,
                coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            _prod(states[actual_product].state_id)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="eiii")
    evidence = center_evidence_from_donor_diagnostic(diag)
    assert evidence["strict_target_match"] is False
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=evidence)
    center = next(c for c in audit.checks
                  if c.name == CHECK_TRANSFORMATION_CENTER)
    assert center.status == CHECK_VIOLATED
    # 区域 True 与 strict False 分别保留在 detail
    assert center.detail["center_match"] is True
    assert center.detail["strict_target_match"] is False
    d, reasons = decide_admission(audit)
    assert d == ADMISSION_RETAIN_CONDITIONAL
    assert any(r.startswith("R5v:") for r in reasons)


def test_r3_01_strict_axis_unknown_blocks_all_verified() -> None:
    """R3-01:证据 strict 轴未核实(产物比对缺失)⇒ 中心检查
    unknown —— 适用未核实轴不得计入全部核实(同反应独立反例:
    补 [H] 只闭合数值账、strict=False 的变体)。"""
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _bound_hyp(states)
    # R5(R4-01):真实诊断产生 strict=None(执行成功、区域核实,但
    # 期望产物未提供 ⇒ 产物比对轴未核实)——证据带完整 proof_record,
    # audit 复算一致后按复算轴消费;手写字段拼接不再可采信
    render = roundtrip(ETHANOL, name="S")
    edits = [{"op": "change_bond_order", "atom1": "S_C_2",
              "atom2": "S_O_1", "from_order": "single",
              "to_order": "double"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True
    diag = check_edit_against_donor(
        current={"smiles": render.smiles,
                 "atom_id_map": dict(render.atom_id_map)},
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "r5-strict"},
        expectation={"target_smiles": ""},  # 期望缺失 ⇒ strict=None
        result=execution, edits=edits)
    assert diag.reaction_center_match is True
    assert diag.strict_target_match is None
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(),
        center_evidence=center_evidence_from_donor_diagnostic(diag))
    center = next(c for c in audit.checks
                  if c.name == CHECK_TRANSFORMATION_CENTER)
    assert center.status == CHECK_UNKNOWN
    assert "center_evidence_strict_unknown" in center.reason_code
    d, _ = decide_admission(audit)
    assert d != ADMISSION_EXPAND


def test_r3_01_unknown_checker_scope_rejected() -> None:
    """R3-01:checker scope 未声明/未登记 ⇒ unknown(限定区域证据
    不得冒充完整变换验证)。"""
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _bound_hyp(states)
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(),
        center_evidence={"checker_version": "ppv1-donor-diagnostic-8",
                         "checker_scope": "full_template_visionary",
                         "center_match": True,
                         "bound_inputs": {
                             "substrate_identity": "CCO",
                             "product_identity": ACETALDEHYDE}})
    center = next(c for c in audit.checks
                  if c.name == CHECK_TRANSFORMATION_CENTER)
    assert center.status == CHECK_UNKNOWN
    assert "center_checker_scope_unknown" in center.reason_code


# ===================================================== R3-06/07/08 audit 接线


def _r(key, value):
    # hypothesis.requirements 契约(R3-08):传 dict(Requirement 对象
    # 由构造期结构化拒绝)
    return {"key": key, "value": value, "level": "essential",
            "source_refs": list(SRC)}


def _r_obj(key, value):
    return build_requirement(key=key, value=value, level="essential",
                             source_refs=SRC)


def _f(key, value, **kw):
    return build_condition_fact(key=key, value=value,
                                status="known_present", **kw)


def _switched_child(old_required):
    """R3-06 两行验收表夹具(与条件线同构;audit 级消费)。"""
    facts = [
        _f(CONDITION_KEY_OXYGEN, "aerobic", phase_id="p0",
           subject_scenario_ref="sA"),
        _f(CONDITION_KEY_OXYGEN, "anaerobic", phase_id="p0",
           subject_scenario_ref="sB"),
        _f(CONDITION_KEY_OXYGEN, "anaerobic", phase_id="p1",
           subject_scenario_ref="sB"),
    ]
    parent = build_path_context(
        condition_facts=facts, phase_id="p0", scenario_ref="sA",
        accumulated_requirements=[_r_obj(CONDITION_KEY_OXYGEN,
                                         old_required)],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    return derive_child_context(
        parent, step_requirements=[_r_obj(CONDITION_KEY_OXYGEN,
                                          "anaerobic")],
        scenario_transition={"new_phase_id": "p1",
                             "new_scenario_ref": "sB",
                             "source_ref": "user:transition"})


def _cand_hyp(requirements, states=None, dependency_refs=None):
    states = states or _states(ETHANOL, ACETALDEHYDE)
    sub, prod = states[ETHANOL], states[ACETALDEHYDE]
    return build_hypothesis(
        parent_path_id="p2", substrate_state_ref=sub.state_id,
        participants=[_sub(sub.state_id), _prod(prod.state_id)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="r4-audit",
        requirements=requirements,
        dependency_refs=dependency_refs or [])


def test_r3_06_audit_row1_old_conflict_kept_to_admission() -> None:
    """R3-06 表行 1(audit→admission 全链):父必需无氧旧边已冲突
    + sB:p1 子步无氧 ⇒ audit 条件 violated ⇒ defer/R3(v3 曾
    verified→expand/R6 洗掉旧冲突)。"""
    child = _switched_child("anaerobic")
    hyp = _cand_hyp([_r(CONDITION_KEY_OXYGEN, "anaerobic")])
    states = _states(ETHANOL, ACETALDEHYDE)
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()}, context=child)
    cond = next(c for c in audit.checks if c.name == "condition_check")
    assert cond.status == CHECK_VIOLATED  # v3 曾 verified
    d, reasons = decide_admission(audit)
    assert d == "defer"
    assert any(r.startswith("R3:current_scenario_conflict") for r in reasons)


def test_r3_06_audit_row2_satisfied_old_edge_not_falsely_killed() -> None:
    """R3-06 表行 2:父必需有氧旧边满足 + sB:p1 子步无氧 ⇒
    compatible(audit 不冤杀;v3 曾 violated→defer)。"""
    child = _switched_child("aerobic")
    hyp = _cand_hyp([_r(CONDITION_KEY_OXYGEN, "anaerobic")])
    states = _states(ETHANOL, ACETALDEHYDE)
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()}, context=child)
    cond = next(c for c in audit.checks if c.name == "condition_check")
    assert cond.status == CHECK_VERIFIED  # v3 曾 violated
    d, _ = decide_admission(audit)
    assert d != "defer"  # 不冤杀合法路线


def test_r3_07_context_only_dependency_consumed_by_audit() -> None:
    """R3-07:context 含 unresolved 依赖、本假设无新增依赖 ⇒ 审计
    **并集**消费 ⇒ unknown(不到 R6;v3 曾 verified/
    no_unresolved_dependencies)。"""
    ctx = build_path_context(
        condition_facts=[_f(CONDITION_KEY_OXYGEN, "aerobic")],
        accumulated_requirements=[
            _r_obj(CONDITION_KEY_OXYGEN, "aerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN],
        dependencies=[
            build_dependency(kind="cosubstrate_supply",
                             statement="上游模型假设的共底物供给")])
    hyp = _cand_hyp([])  # 本假设无依赖引用(context-only 依赖)
    states = _states(ETHANOL, ACETALDEHYDE)
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()}, context=ctx)
    dep = next(c for c in audit.checks
               if c.name == "provenance_dependency")
    assert dep.status == CHECK_UNKNOWN
    assert "unresolved_dependencies_inherited" in dep.reason_code
    d, reasons = decide_admission(audit)
    assert d != ADMISSION_EXPAND  # v3 曾 R6


def test_r3_07_explicit_empty_list_with_supported_context_verified() -> None:
    """R3-07:unresolved=[](显式空)+ context 依赖 supported ⇒
    verified;None 与 [] 语义不混同(不传时从 context 推导)。"""
    ctx = build_path_context(
        condition_facts=[_f(CONDITION_KEY_OXYGEN, "aerobic")],
        accumulated_requirements=[_r_obj(CONDITION_KEY_OXYGEN,
                                         "aerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN],
        dependencies=[
            resolve_dependency(
                build_dependency(kind="supply", statement="s"),
                new_evidence=["src:ok"],
                resolution=DEPENDENCY_SUPPORTED)])
    hyp = _cand_hyp([], dependency_refs=["dep:ok"])
    states = _states(ETHANOL, ACETALDEHYDE)
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()}, context=ctx,
        unresolved_dependency_ids=[])
    dep = next(c for c in audit.checks
               if c.name == "provenance_dependency")
    assert dep.status == CHECK_VERIFIED


def test_r3_08_input_hash_covers_real_inputs() -> None:
    """R3-08:依赖解析状态/中心证据结论/state fidelity/电荷轴为实际
    科学输入 —— 只改其一 ⇒ input_hash 变化;相同输入幂等。"""
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    state_map = {s.state_id: s for s in states.values()}
    hyp = _bound_hyp(states)
    ctx = _aerobic_context()
    evidence = center_evidence_from_donor_diagnostic(_ethanol_diag())
    a = audit_hypothesis(hyp, states=state_map, context=ctx,
                         center_evidence=evidence,
                         unresolved_dependency_ids=None)
    a_again = audit_hypothesis(hyp, states=state_map, context=ctx,
                               center_evidence=evidence,
                               unresolved_dependency_ids=None)
    assert a.input_hash == a_again.input_hash  # 幂等
    # ① 依赖解析状态
    b = audit_hypothesis(hyp, states=state_map, context=ctx,
                         center_evidence=evidence,
                         unresolved_dependency_ids=["dep:x"])
    # ② 中心证据结论(True vs False)——R5(R4-01):真实诊断产生
    # 不同结论(供体中心声明偏移 ⇒ center_match=False),不是改写
    # 自报字段(改写会被 integrity 复算结构化拒绝)
    render_off = roundtrip(ETHANOL, name="S")
    edits_off = [{"op": "change_bond_order", "atom1": "S_C_2",
                  "atom2": "S_O_1", "from_order": "single",
                  "to_order": "double"}]
    execution_off = execute_edits(render_off, edits_off)
    assert execution_off["ok"] is True
    diag_off = check_edit_against_donor(
        current={"smiles": render_off.smiles,
                 "atom_id_map": dict(render_off.atom_id_map)},
        donor={"center_atom_ids": ["d1", "d2"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"d1": "S_C_1", "d2": "S_C_2"},
                   "equivalence_classes": [], "ref": "r5-off"},
        expectation={"target_smiles": execution_off["product_smiles"]},
        result=execution_off, edits=edits_off)
    assert diag_off.reaction_center_match is False
    evidence_false = center_evidence_from_donor_diagnostic(diag_off)
    c = audit_hypothesis(hyp, states=state_map, context=ctx,
                         center_evidence=evidence_false,
                         unresolved_dependency_ids=None)
    # ③ 同 state_id 不同 fidelity(archive vs as_written)
    states_archive = dict(state_map)
    states_archive[states[ACETALDEHYDE].state_id] = build_chemical_state(
        ACETALDEHYDE, STRUCTURE_ORIGIN_SOURCE_PRODUCT,
        fidelity=archive_recovered_fidelity())
    d_ = audit_hypothesis(hyp, states=states_archive, context=ctx,
                          center_evidence=evidence,
                          unresolved_dependency_ids=None)
    # ④ 电荷轴 unknown
    states_charge = dict(state_map)
    states_charge[states[ACETALDEHYDE].state_id] = build_chemical_state(
        ACETALDEHYDE, STRUCTURE_ORIGIN_SOURCE_PRODUCT,
        fidelity={"stereo": "as_written", "isotope": "as_written",
                  "formal_charge": "unknown",
                  "protonation_basis": "as_written"})
    e = audit_hypothesis(hyp, states=states_charge, context=ctx,
                         center_evidence=evidence,
                         unresolved_dependency_ids=None)
    assert len({a.input_hash, b.input_hash, c.input_hash,
                d_.input_hash, e.input_hash}) == 5  # 各不相同


def test_r3_08_context_nested_mutation_changes_input_hash() -> None:
    """R3-08:嵌套前提真实冻结 —— 对 context 修改嵌套内容(绕过
    context_id)⇒ input_hash(内容哈希)变化;frozen 对象就地修改
    直接 TypeError。"""
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    state_map = {s.state_id: s for s in states.values()}
    hyp = _bound_hyp(states)
    ctx = build_path_context(
        condition_facts=[_f(CONDITION_KEY_OXYGEN, "aerobic")],
        accumulated_requirements=[
            build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                              value="aerobic", source_refs=["src:x"])],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    a = audit_hypothesis(hyp, states=state_map, context=ctx)
    # 就地修改 frozen 对象被拒(嵌套集合不可变)
    with pytest.raises((TypeError, AttributeError)):
        ctx.accumulated_requirements[0].source_refs.append("src:y")
    # 换一个内容不同的同形 context(不同嵌套载荷)⇒ 不同 input_hash
    ctx2 = build_path_context(
        condition_facts=[_f(CONDITION_KEY_OXYGEN, "aerobic")],
        accumulated_requirements=[
            build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                              value="aerobic",
                              source_refs=["src:x", "src:z"])],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    b = audit_hypothesis(hyp, states=state_map, context=ctx2)
    assert a.input_hash != b.input_hash


def test_r3_08_bad_context_object_structured_reject_at_audit() -> None:
    """R3-08:直接对象的缺/未来 context 版本 ⇒ audit 入口结构化
    拒绝(不到 R6)。"""
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    state_map = {s.state_id: s for s in states.values()}
    hyp = _bound_hyp(states)
    ctx = _aerobic_context()
    ctx.schema_version = "future-context-999"  # 就地伪造(对象可变)
    with pytest.raises(Exception) as excinfo:
        audit_hypothesis(hyp, states=state_map, context=ctx)
    assert "context" in str(excinfo.value) or "版本" in str(excinfo.value)


# ============================================================ §4 off 披露


def test_s4_per_product_off_discloses_not_consumed() -> None:
    """§4:per_product_gate_consumption=off ⇒ 决策可为 expand,但
    被拒产物与未消费范围以 R2p_disclosure 留痕(v3 曾零披露)。"""
    from pathway_v43.pollutant.audit import (
        legacy_validation_to_gate_decisions)

    diag = _ethanol_diag()
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    state_map = {s.state_id: s for s in states.values()}
    hyp = _bound_hyp(states)
    audit = audit_hypothesis(
        hyp, states=state_map, context=_aerobic_context(),
        center_evidence=center_evidence_from_donor_diagnostic(diag))
    gates = legacy_validation_to_gate_decisions({
        "evidence_id": "E-s4",
        "gates": {"direction_source": {"ok": True, "reason": ""},
                  "recorded_eligibility": {"ok": True, "reason": ""}},
        "verdicts": [
            {"position": 0, "accepted": True, "reasons": []},
            {"position": 1, "accepted": False,
             "reasons": ["element_gate_rejected"]}]})
    policy = AdmissionPolicy(per_product_gate_consumption="off")
    d, reasons = decide_admission(audit, policy=policy,
                                  gate_decisions=gates)
    assert d == ADMISSION_EXPAND  # off ⇒ 不阻断
    assert any(r.startswith("R2p_disclosure:") for r in reasons)
    assert any("element_gate_rejected" in r for r in reasons)
    # on(默认)对照:部分被拒 ⇒ retain(v3 修复保持)
    d_on, _ = decide_admission(audit, gate_decisions=gates)
    assert d_on == ADMISSION_RETAIN_CONDITIONAL
