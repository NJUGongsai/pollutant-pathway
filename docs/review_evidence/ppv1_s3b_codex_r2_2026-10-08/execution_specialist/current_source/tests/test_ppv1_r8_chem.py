"""R8 化学与证据线回归(Codex R7 复审 R7-01;v8)。

规则级合成夹具;无金标/封存材料。先红后绿:红验证在基线 858dd94
工作树复跑本文件(与 R7 同口径);v8 实现后全绿。

R7-01:状态恢复/直接对象首次授信前的同源验证 —— 正常乙醇氧化证明
不动,只改序列化状态 raw(如 CCO |r|、H2 挂 CC=O),基线
ChemicalState.from_dict 接受、恢复对象经 audit_hypothesis→
decide_admission 全 verified/full/R6 expand;H2 raw 换成 CC=O(跨
分子)同样 R6(原始串与规范身份的一致性完全未核)。v8:from_dict
恢复与 audit 直接 states(含 dataclass 绕路)共用与公共 writer 同源
的纯状态验证(raw 登记守卫 + raw→strict 身份一致 + 规范身份/结构
事实重推导 + CN-only 专用契约)—— 非法对象结构化拒绝、零授信,不
静默清洗信息再授 full;clean/同图异拼写(OCC)/登记 atomProp 含
空格/指定手性正常链/CN-only 诚实未知/存档 fidelity 边界保持。
只核对象内部可确定的一致性,不认证来源真伪/历史执行/机制。

本文件顶层 import 只用基线已存在的符号(新入口 validate_state_object
不经测试直接引用),基线红逐条为行为红(DID NOT RAISE / 错误结论),
不是收集错误。
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.audit import (  # noqa: E402
    ADMISSION_EXPAND,
    ADMISSION_RETAIN_CONDITIONAL,
    CHECK_IDENTITY_FIDELITY,
    CHECK_UNKNOWN,
    audit_hypothesis,
    center_evidence_from_donor_diagnostic,
    check_edit_against_donor,
    decide_admission,
)
from pathway_v43.pollutant.chemstate import (  # noqa: E402
    FIDELITY_ABSENT_IN_ARCHIVE,
    ChemicalState,
    ChemicalStateError,
    STRUCTURE_ORIGIN_RAW_INPUT,
    STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    archive_recovered_fidelity,
    build_chemical_state,
    build_chemical_state_from_cn_only,
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
)

ETHANOL = "CCO"
ACETALDEHYDE = "CC=O"
HYDROGEN = "[H][H]"
CHIRAL_SUBSTRATE = "F[C@H](Cl)CCO"
SRC = ["src:rule-r8"]


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


def _hyp(states, reactants, products, group="r8-chem"):
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
                   "equivalence_classes": [], "ref": "r8"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.reaction_center_match is True
    assert diag.strict_target_match is True
    return center_evidence_from_donor_diagnostic(diag)


def _oxidation_evidence():
    """真实乙醇 C–O single→double 诊断(乙醇氧化证据,R7-01 基准不动)。"""
    return _donor_evidence(ETHANOL, "S_C_2", "S_O_1", "single", "double")


def _audit(states, hyp, evidence):
    return audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=evidence)


def _admission(audit):
    return decide_admission(audit)


def _oxidation_base():
    """R7-01 基准公共链:CCO/CC=O/[H][H] + 真实乙醇氧化证明。"""
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = _hyp(states, [(ETHANOL, 1)],
               [(ACETALDEHYDE, 1), (HYDROGEN, 1)], group="r7-01-base")
    return states, hyp, _oxidation_evidence()


# ==================================================== R7-01 反例(恢复入口)

@pytest.mark.parametrize("smiles", [ETHANOL, ACETALDEHYDE, HYDROGEN])
def test_r7_01_from_dict_raw_unregistered_cx_rejected(smiles) -> None:
    """R7 复审反例,基线 858dd94 红:序列化状态只改
    structure_smiles_raw=<smiles> |r|(state_id/规范串/版本/四轴
    as_written 全保留)—— 基线 from_dict 接受;v8:恢复入口共用
    writer 同源验证,raw 未过输入守卫 ⇒ ChemicalStateError,机器码
    披露违规项(不静默清洗信息再授 full)。"""
    state = build_chemical_state(smiles, STRUCTURE_ORIGIN_SOURCE_PRODUCT)
    payload = state.to_dict()
    payload["structure_smiles_raw"] = smiles + " |r|"
    with pytest.raises(ChemicalStateError) as ei:
        ChemicalState.from_dict(payload)
    detail = ei.value.detail
    assert detail["kind"] == "raw_structure_rejected"
    assert detail["reason"]["kind"] == "unregistered_cx_class"
    assert detail["reason"]["item"] == "r"


def test_r7_01_from_dict_raw_different_molecule_rejected() -> None:
    """R7 复审同根辅助反例,基线 858dd94 红:H2 状态 raw 改 CC=O
    (canonical/ID 仍 H2)—— 基线恢复/审核均接受;v8:raw 重推严格
    身份 != smiles_isomeric ⇒ raw_identity_mismatch(同图异拼写接受,
    跨分子拒绝)。"""
    state = build_chemical_state(HYDROGEN, STRUCTURE_ORIGIN_SOURCE_PRODUCT)
    payload = state.to_dict()
    payload["structure_smiles_raw"] = ACETALDEHYDE
    with pytest.raises(ChemicalStateError) as ei:
        ChemicalState.from_dict(payload)
    detail = ei.value.detail
    assert detail["kind"] == "raw_identity_mismatch"
    assert detail["expected_identity"] == state.smiles_isomeric
    assert detail["raw_identity"] == ACETALDEHYDE


def test_r7_01_from_dict_structured_fact_mismatch_rejected() -> None:
    """同源验证的规范身份/结构事实轴:载荷 formal_charge 被改(结构
    未变)—— 基线 from_dict 接受、audit 电荷轴用假值;v8:工厂同源
    重推导不一致 ⇒ state_fact_rederivation_mismatch。"""
    state = build_chemical_state(ETHANOL, STRUCTURE_ORIGIN_SOURCE_PRODUCT)
    payload = state.to_dict()
    payload["formal_charge"] = 99
    with pytest.raises(ChemicalStateError) as ei:
        ChemicalState.from_dict(payload)
    assert ei.value.detail["kind"] == "state_fact_rederivation_mismatch"
    assert "formal_charge" in ei.value.detail["mismatches"]


def test_r7_01_from_dict_unknown_origin_rejected() -> None:
    """同源验证的 origin 轴:载荷 structure_origin 改为未知值 ——
    基线 from_dict 接受(dataclass 无校验);v8:invalid_structure_
    origin 拒绝(与公共 writer 同口径)。"""
    state = build_chemical_state(ETHANOL, STRUCTURE_ORIGIN_SOURCE_PRODUCT)
    payload = state.to_dict()
    payload["structure_origin"] = "bogus-origin"
    with pytest.raises(ChemicalStateError) as ei:
        ChemicalState.from_dict(payload)
    assert ei.value.detail["kind"] == "invalid_structure_origin"


def test_r7_01_restored_tainted_states_recovery_rejected() -> None:
    """R7 复审反例(恢复入口),基线 858dd94 红:恢复对象经
    audit_hypothesis→decide_admission 全 verified/full/R6 expand;
    v8:恢复入口(from_dict)在构造期即结构化拒绝,篡改对象不再到达
    audit;模拟绕过 from_dict 的 dataclass 构造(ChemicalState(**payload))
    时,audit 首次消费同源验证同样拒绝 —— 两入口闭合,不产出任何
    disposition(不吞异常后按 retain/verified 记录)。"""
    states, hyp, evidence = _oxidation_base()
    payload = states[ETHANOL].to_dict()
    payload["structure_smiles_raw"] = ETHANOL + " |r|"
    with pytest.raises(ChemicalStateError):
        ChemicalState.from_dict(payload)  # v8:恢复入口即拒
    bypassed = dict(states)
    bypassed[ETHANOL] = ChemicalState(**payload)  # dataclass 绕路
    with pytest.raises(ChemicalStateError):
        _audit(bypassed, hyp, evidence)


def test_r7_01_restored_h2_different_molecule_rejected() -> None:
    """R7 复审同根反例(完整公共链),基线 858dd94 红:H2 恢复对象
    raw=CC=O(身份仍 H2)经公共链审核 full/R6;v8:恢复入口与 audit
    首次消费均 raw_identity_mismatch 拒绝。"""
    states, hyp, evidence = _oxidation_base()
    payload = states[HYDROGEN].to_dict()
    payload["structure_smiles_raw"] = ACETALDEHYDE
    with pytest.raises(ChemicalStateError) as ei:
        ChemicalState.from_dict(payload)
    assert ei.value.detail["kind"] == "raw_identity_mismatch"
    bypassed = dict(states)
    bypassed[HYDROGEN] = ChemicalState(**payload)
    with pytest.raises(ChemicalStateError) as ei:
        _audit(bypassed, hyp, evidence)
    assert ei.value.detail["kind"] == "raw_identity_mismatch"


# ============================================ R7-01 反例(直接对象绕路)

def test_r7_01_direct_dataclass_raw_tampered_audit_rejected() -> None:
    """R7 复审反例,基线 858dd94 红:**直接 dataclass 绕路** —— 不经
    from_dict,就地改工厂构建对象的 structure_smiles_raw,基线
    audit_hypothesis(states=...) 全 verified/full/R6 expand;v8:audit
    入口对每个被消费 state 同源验证(不只补 from_dict),非法对象
    结构化拒绝、不 R6。"""
    states, hyp, evidence = _oxidation_base()
    tampered = dict(states)
    tampered[ETHANOL] = copy.copy(states[ETHANOL])
    tampered[ETHANOL].structure_smiles_raw = ETHANOL + " |r|"
    with pytest.raises(ChemicalStateError) as ei:
        _audit(tampered, hyp, evidence)
    assert ei.value.detail["reason"]["kind"] == "unregistered_cx_class"


def test_r7_01_direct_dataclass_h2_raw_swap_audit_rejected() -> None:
    """R7 复审同根反例(直接对象),基线 858dd94 红:H2 对象 raw 就地
    改 CC=O,基线公共链 verified/full/R6;v8:首次消费 raw_identity_
    mismatch。"""
    states, hyp, evidence = _oxidation_base()
    tampered = dict(states)
    tampered[HYDROGEN] = copy.copy(states[HYDROGEN])
    tampered[HYDROGEN].structure_smiles_raw = ACETALDEHYDE
    with pytest.raises(ChemicalStateError) as ei:
        _audit(tampered, hyp, evidence)
    assert ei.value.detail["kind"] == "raw_identity_mismatch"


def test_r7_01_direct_dataclass_fact_tampered_audit_rejected() -> None:
    """直接对象的结构事实轴,基线 858dd94 红:就地改 formal_charge,
    基线 audit 用假电荷记账(verified);v8:重推导不一致拒绝。"""
    states, hyp, evidence = _oxidation_base()
    tampered = dict(states)
    tampered[ACETALDEHYDE] = copy.copy(states[ACETALDEHYDE])
    tampered[ACETALDEHYDE].formal_charge = 99
    with pytest.raises(ChemicalStateError) as ei:
        _audit(tampered, hyp, evidence)
    assert ei.value.detail["kind"] == "state_fact_rederivation_mismatch"


# ==================================================== 指定手性反例

def test_r7_01_chiral_substrate_raw_tamper_rejected() -> None:
    """R7 复审反例,基线 858dd94 红:指定手性表示 F[C@H](Cl)CCO 的
    远端氧化,真实供体诊断证明保持,仅恢复/直接对象 substrate raw
    加 |r| —— 基线同样 R6;v8:恢复入口与 audit 直接对象均同源守卫
    拒绝。"""
    evidence = _donor_evidence(CHIRAL_SUBSTRATE, "S_C_3", "S_O_1",
                               "single", "double")
    product = evidence["bound_inputs"]["product_identity"]
    states = _states(CHIRAL_SUBSTRATE, product, HYDROGEN)
    hyp = _hyp(states, [(CHIRAL_SUBSTRATE, 1)],
               [(product, 1), (HYDROGEN, 1)], group="r7-01-chiral")
    payload = states[CHIRAL_SUBSTRATE].to_dict()
    payload["structure_smiles_raw"] = CHIRAL_SUBSTRATE + " |r|"
    with pytest.raises(ChemicalStateError):
        ChemicalState.from_dict(payload)
    with pytest.raises(ChemicalStateError):
        _audit({**states, CHIRAL_SUBSTRATE: ChemicalState(**payload)},
               hyp, evidence)
    direct = copy.copy(states[CHIRAL_SUBSTRATE])
    direct.structure_smiles_raw = CHIRAL_SUBSTRATE + " |r|"
    with pytest.raises(ChemicalStateError):
        _audit({**states, CHIRAL_SUBSTRATE: direct}, hyp, evidence)


# ==================================================== 正控(基线亦绿)

def test_r7_01_clean_restore_and_audit_control() -> None:
    """正控:干净状态的 to_dict→from_dict 往返 + 直接对象公共链 ——
    全 verified/full/R6 expand(合法链路不被新校验误拒)。"""
    states, hyp, evidence = _oxidation_base()
    restored = {k: ChemicalState.from_dict(s.to_dict())
                for k, s in states.items()}
    audit = _audit(restored, hyp, evidence)
    assert _admission(audit) == (ADMISSION_EXPAND,
                                 ["R6:all_verified_no_conflict"])
    audit = _audit(states, hyp, evidence)
    assert _admission(audit) == (ADMISSION_EXPAND,
                                 ["R6:all_verified_no_conflict"])


def test_r7_01_same_graph_alternate_raw_spelling_accepted() -> None:
    """正控(R7 复审明示保留):raw OCC 与 canonical CCO 同图异拼写
    —— 接受(身份一致),恢复/公共链仍 full/R6;不因新校验过拒。"""
    states, hyp, evidence = _oxidation_base()
    payload = states[ETHANOL].to_dict()
    payload["structure_smiles_raw"] = "OCC"
    restored = dict(states)
    restored[ETHANOL] = ChemicalState.from_dict(payload)
    audit = _audit(restored, hyp, evidence)
    assert _admission(audit)[0] == ADMISSION_EXPAND


def test_r7_01_registered_atomprop_with_spaces_raw_accepted() -> None:
    """正控(R7 复审明示保留):登记 atomProp 含空格的 raw
    (CCO |atomProp:0.note.hello world|)—— 输入守卫按真实类边界
    放行,身份同 CCO,公共链 full/R6。"""
    states, hyp, evidence = _oxidation_base()
    payload = states[ETHANOL].to_dict()
    payload["structure_smiles_raw"] = \
        "CCO |atomProp:0.note.hello world|"
    restored = dict(states)
    restored[ETHANOL] = ChemicalState.from_dict(payload)
    audit = _audit(restored, hyp, evidence)
    assert _admission(audit)[0] == ADMISSION_EXPAND


def test_r7_01_chiral_clean_chain_control() -> None:
    """正控(R7 复审明示保留):指定手性底物正常链(真实供体证明、
    raw 不动)—— verified/full/R6 expand。"""
    evidence = _donor_evidence(CHIRAL_SUBSTRATE, "S_C_3", "S_O_1",
                               "single", "double")
    product = evidence["bound_inputs"]["product_identity"]
    states = _states(CHIRAL_SUBSTRATE, product, HYDROGEN)
    hyp = _hyp(states, [(CHIRAL_SUBSTRATE, 1)],
               [(product, 1), (HYDROGEN, 1)], group="r7-01-chiral-ctl")
    audit = _audit(states, hyp, evidence)
    assert _admission(audit)[0] == ADMISSION_EXPAND


def test_r7_01_cn_only_honest_unknown_control() -> None:
    """正控(R7 复审明示保留):CN-only 状态(专用只读工厂)—— 恢复
    与直接对象合法,条件/结构轴诚实 unknown、retain,不因新校验
    误拒(不从 CN 猜结构)。"""
    states, _, evidence = _oxidation_base()
    legacy = dict(states)
    legacy[ETHANOL] = ChemicalState.from_dict(
        build_chemical_state_from_cn_only(ETHANOL).to_dict())
    hyp = _hyp(legacy, [(ETHANOL, 1)],
               [(ACETALDEHYDE, 1), (HYDROGEN, 1)],
               group="r7-01-cn-only")
    audit = _audit(legacy, hyp, evidence)
    assert _admission(audit)[0] == ADMISSION_RETAIN_CONDITIONAL


def test_r7_01_archive_fidelity_boundary_control() -> None:
    """正控(R7 复审明示保留):存档形 fidelity(立体/同位素
    absent_in_archive)状态 —— 恢复合法,identity_fidelity 轴诚实
    unknown(轴声明不升级不清洗),不误拒。"""
    archived = build_chemical_state(
        ACETALDEHYDE, STRUCTURE_ORIGIN_SOURCE_PRODUCT,
        [{"record": "archive"}], fidelity=archive_recovered_fidelity())
    restored = ChemicalState.from_dict(archived.to_dict())
    assert restored.representation_fidelity["stereo"] == \
        FIDELITY_ABSENT_IN_ARCHIVE
    plain = build_chemical_state(ETHANOL, STRUCTURE_ORIGIN_SOURCE_PRODUCT)
    states = {ACETALDEHYDE: restored, ETHANOL: plain}
    hyp = _hyp(states, [(ETHANOL, 1)], [(ACETALDEHYDE, 1)],
               group="r7-01-archive-ctl")
    audit = _audit(states, hyp, None)
    check = next(c for c in audit.checks
                 if c.name == CHECK_IDENTITY_FIDELITY)
    assert check.status == CHECK_UNKNOWN
    assert "stereo=absent_in_archive" in check.reason_code
    center = next(c for c in audit.checks
                  if c.name == "transformation_center")
    assert center.status == CHECK_UNKNOWN  # 无证据不冒充 verified


def test_r7_01_validation_source_discloses_not_writer_only() -> None:
    """机读披露:恢复入口拒绝与公共 writer 同源 —— store.put_state 对
    相同篡改载荷同样零写入拒绝(不声称错误状态已入账或产生真实
    S3 路线;两入口共用同一验证事实)。"""
    import tempfile

    from pathway_v43.pollutant.store import (
        Ppv1StateContractError,
        PollutantPathwayStore,
    )
    state = build_chemical_state(ETHANOL, STRUCTURE_ORIGIN_SOURCE_PRODUCT)
    payload = state.to_dict()
    payload["structure_smiles_raw"] = ETHANOL + " |r|"
    with tempfile.TemporaryDirectory(prefix="r8_chem_store_") as tmp:
        store = PollutantPathwayStore(Path(tmp) / "w.sqlite")
        before = store.counts()
        with pytest.raises(Ppv1StateContractError) as ei:
            store.put_state(payload)
        assert ei.value.detail["kind"] == "raw_structure_unparseable"
        assert store.counts() == before  # 零写入
        store.close()
    payload2 = state.to_dict()
    payload2["structure_smiles_raw"] = ACETALDEHYDE
    with tempfile.TemporaryDirectory(prefix="r8_chem_store_") as tmp:
        store = PollutantPathwayStore(Path(tmp) / "w2.sqlite")
        before = store.counts()
        with pytest.raises(Ppv1StateContractError) as ei:
            store.put_state(payload2)
        assert ei.value.detail["kind"] == "raw_identity_mismatch"
        assert store.counts() == before  # 零写入
        store.close()
