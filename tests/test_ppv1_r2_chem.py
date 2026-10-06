"""R3 化学与审计线回归(Codex R2 复审 R2-01/02/03/12 + mimo 采纳;v3)。

规则级合成夹具;模型 off,无金标/封存材料。每个用例对应复审可复现
反例或验收边界;探针复现基线(HEAD 0002f71)见
docs/review_evidence/ppv1_r2_2026-10-06/。

R2-01:admission 必需覆盖/缺 state 不崩溃/R1b 与 R1 分离/自报签名不
授信/center 证据门/R5d 限定/input_hash 覆盖实际输入。
R2-02:增强立体规范化(plain=ABS、AND/OR 整组反转归一、部分反转保持
不同)与公开表示往返(smiles_isomeric 携带注解,重建同 id)。
R2-03:实际净变化判定(零净变化永不 True)、声明–执行对账、联合中心
对称映射(单原子轨道不冒充)、extra_changes ΔH/Δ立体、plain/mapped
对账、ABS 注解差异不冤枉供体 strict 轴。
R2-12:冻结门禁逐产物拒绝被 decide_admission 真实消费。
mimo 采纳:H+_count1 结构化模式、元素账口径注记、等价类 basis 披露。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rdkit import Chem  # noqa: E402

from pathway_v43.pollutant.audit import (  # noqa: E402
    ADMISSION_EXPAND,
    ADMISSION_REJECT,
    ADMISSION_RETAIN_CONDITIONAL,
    AdmissionPolicy,
    CHECK_CONDITION_CHECK,
    CHECK_ELEMENT_ACCOUNTING,
    CHECK_FORMAL_CHARGE_ACCOUNTING,
    CHECK_NOT_APPLICABLE,
    CHECK_PARTICIPANT_STATE_REFS,
    CHECK_STRUCTURE_PARSE_VALENCE,
    CHECK_TRANSFORMATION_CENTER,
    CHECK_UNKNOWN,
    CHECK_VERIFIED,
    CHECK_VIOLATED,
    PREREQUISITE_FAILED,
    audit_hypothesis,
    center_evidence_from_donor_diagnostic,
    check_edit_against_donor,
    decide_admission,
    element_counts_full,
    legacy_validation_to_gate_decisions,
)
from pathway_v43.pollutant.chemstate import (  # noqa: E402
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
    FACT_STATUS_KNOWN_PRESENT,
    REQUESTED_SCOPE_CONDITION_COMPATIBLE,
    build_condition_fact,
    build_path_context,
    build_requirement,
)
from pathway_v43.pollutant.substrate_profile import (  # noqa: E402
    build_substrate_profile,
)
from pathway_v43.services.atom_tool import (  # noqa: E402
    execute_edits,
    roundtrip,
)

ETHANOL = "CCO"
ACETALDEHYDE = "CC=O"
ACETIC_ACID = "CC(=O)O"
O2 = "O=O"
WATER = "O"
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


def _balanced_hypothesis(states):
    """CCO + O=O → CC(=O)O + O(全氢配平正例,系数已知)。"""
    return build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[
            _sub(states[ETHANOL].state_id),
            Participant(state_ref=states[O2].state_id,
                        side=PARTICIPANT_SIDE_REACTANT,
                        role=PARTICIPANT_ROLE_COSUBSTRATE,
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            _prod(states[ACETIC_ACID].state_id),
            _prod(states[WATER].state_id, role="coproduct")],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="r2-chem")


def _aerobic_context():
    return build_path_context(
        requested_scope=REQUESTED_SCOPE_CONDITION_COMPATIBLE,
        condition_facts=[
            build_condition_fact(key=CONDITION_KEY_OXYGEN,
                                 value="aerobic",
                                 status=FACT_STATUS_KNOWN_PRESENT)],
        accumulated_requirements=[
            build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                              value="aerobic", source_refs=SRC)],
        assessment_scope=["oxygen_regime"])


def _ethanol_co_execution():
    """真实 AtomTool 协议:乙醇 C–O single→double(F11 复现场景)。"""
    render = roundtrip(ETHANOL, name="S")
    edits = [{"op": "change_bond_order",
              "atom1": "S_C_2", "atom2": "S_O_1",
              "from_order": "single", "to_order": "double"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True
    return {"smiles": render.smiles,
            "atom_id_map": dict(render.atom_id_map)}, edits, execution


def _diag(current, edits, execution, donor_centers, mapping,
          equivalence=None, target=None):
    return check_edit_against_donor(
        current=current, donor={"center_atom_ids": donor_centers},
        alignment={"status": "resolved", "donor_to_current": mapping,
                   "equivalence_classes": equivalence or [], "ref": "a"},
        expectation={"target_smiles":
                     target if target is not None
                     else execution["product_smiles"]},
        result=execution, edits=edits)


# ============================================================ R2-02 身份规范化


def test_r2_02_plain_and_abs_same_identity() -> None:
    """plain 与 ABS 注解是同一立体事实 ⇒ 同 state_id(公开表示同为 plain)。"""
    plain = build_chemical_state("F[C@H](Cl)Br", STRUCTURE_ORIGIN_RAW_INPUT)
    absgrp = build_chemical_state("F[C@H](Cl)Br |a:1|",
                                  STRUCTURE_ORIGIN_RAW_INPUT)
    assert plain.state_id == absgrp.state_id
    assert plain.smiles_isomeric == absgrp.smiles_isomeric
    # 原始串保真:各出现保留原始写法
    assert plain.structure_smiles_raw == "F[C@H](Cl)Br"
    assert absgrp.structure_smiles_raw == "F[C@H](Cl)Br |a:1|"


def test_r2_02_and_group_whole_inversion_same_identity() -> None:
    """单中心 AND 组整组翻转(对映体对)= 同一相对事实 ⇒ 同 id(R2-02)。"""
    a = build_chemical_state("C[C@H](O)CC |&1:1|",
                             STRUCTURE_ORIGIN_RAW_INPUT)
    b = build_chemical_state("C[C@@H](O)CC |&1:1|",
                             STRUCTURE_ORIGIN_RAW_INPUT)
    assert a.state_id == b.state_id
    assert a.smiles_isomeric == b.smiles_isomeric


def test_r2_02_or_group_whole_inversion_same_identity() -> None:
    """OR 组整组翻转 = 同一混合物声明 ⇒ 同 id。"""
    a = build_chemical_state("C[C@H](O)CC |o1:1|",
                             STRUCTURE_ORIGIN_RAW_INPUT)
    b = build_chemical_state("C[C@@H](O)CC |o1:1|",
                             STRUCTURE_ORIGIN_RAW_INPUT)
    assert a.state_id == b.state_id


def test_r2_02_double_center_partial_inversion_stays_distinct() -> None:
    """双中心 AND 组:整组翻转同 id;**部分翻转**(组内只翻一个中心)
    是不同相对立体事实 ⇒ 不同 id(控制例,R2-02)。"""
    whole = "C[C@H](O)C[C@H](O)CC |&1:1,4|"
    flipped = "C[C@@H](O)C[C@@H](O)CC |&1:1,4|"
    partial = "C[C@@H](O)C[C@H](O)CC |&1:1,4|"
    s1 = build_chemical_state(whole, STRUCTURE_ORIGIN_RAW_INPUT)
    s2 = build_chemical_state(flipped, STRUCTURE_ORIGIN_RAW_INPUT)
    s3 = build_chemical_state(partial, STRUCTURE_ORIGIN_RAW_INPUT)
    assert s1.state_id == s2.state_id
    assert s3.state_id != s1.state_id


def test_r2_02_and_or_group_types_not_merged() -> None:
    """AND 与 OR 是不同组类型,不得误合并(与 plain 三身份)。"""
    plain = build_chemical_state("F[C@H](Cl)Br", STRUCTURE_ORIGIN_RAW_INPUT)
    andgrp = build_chemical_state("F[C@H](Cl)Br |&1:1|",
                                  STRUCTURE_ORIGIN_RAW_INPUT)
    orgrp = build_chemical_state("F[C@H](Cl)Br |o1:1|",
                                 STRUCTURE_ORIGIN_RAW_INPUT)
    assert len({plain.state_id, andgrp.state_id, orgrp.state_id}) == 3


def test_r2_02_public_representation_roundtrip_rebuilds_identity() -> None:
    """公开表示往返:smiles_isomeric 携带组注解,重解析重建同一 id。

    v2 的 smiles_isomeric 用普通 MolToSmiles 丢注解,重建变 plain 身份
    (R2-02 复审反例 f05_enhanced_stereo_export_roundtrip)。
    """
    for smiles in ("F[C@H](Cl)Br |&1:1|", "F[C@H](Cl)Br |o1:1|",
                   "C[C@H](O)C[C@H](O)CC |&1:1,4|",
                   "C[C@H](O)CC |o1:1|"):
        state = build_chemical_state(smiles, STRUCTURE_ORIGIN_RAW_INPUT)
        assert "|" in state.smiles_isomeric  # 注解保留在公开表示
        rebuilt = build_chemical_state(state.smiles_isomeric,
                                       STRUCTURE_ORIGIN_SOURCE_PRODUCT)
        assert rebuilt.state_id == state.state_id
        # 幂等:规范化表示再规范化不变
        assert rebuilt.smiles_isomeric == state.smiles_isomeric


def test_r2_02_strict_identity_same_normalization_for_donor_axis() -> None:
    """strict 轴(供体 strict 比对)同一规范化:ABS/plain 互相命中,
    AND 组整组翻转互相命中,部分反转不命中。"""
    assert strict_identity_of("F[C@H](Cl)Br") == \
        strict_identity_of("F[C@H](Cl)Br |a:1|")
    assert strict_identity_of("C[C@H](O)CC |&1:1|") == \
        strict_identity_of("C[C@@H](O)CC |&1:1|")
    assert strict_identity_of("C[C@H](O)C[C@H](O)CC |&1:1,4|") == \
        strict_identity_of("C[C@@H](O)C[C@@H](O)CC |&1:1,4|")
    assert strict_identity_of("C[C@H](O)C[C@H](O)CC |&1:1,4|") != \
        strict_identity_of("C[C@@H](O)C[C@H](O)CC |&1:1,4|")


def test_r2_02_atom_map_numbers_not_identity() -> None:
    """原子映射号不属于分子身份(v3 保持 v2 语义)。"""
    assert strict_identity_of("F[C@H:7](Cl)Br |&1:1|") == \
        strict_identity_of("F[C@H](Cl)Br |&1:1|")


def test_r2_02_substrate_profile_carries_stereo_annotation() -> None:
    """底物档案 structure_smiles 用同一公开表示(带注解),可往返。"""
    state = build_chemical_state("C[C@H](O)CC |&1:1|",
                                 STRUCTURE_ORIGIN_SOURCE_PRODUCT)
    profile = build_substrate_profile(state)
    assert profile.structure_smiles == state.smiles_isomeric
    assert "|" in profile.structure_smiles
    rebuilt = build_chemical_state(profile.structure_smiles,
                                   STRUCTURE_ORIGIN_SOURCE_PRODUCT)
    assert rebuilt.state_id == state.state_id


# ============================================================ R2-01 admission


def test_r2_01_missing_state_structured_not_crash() -> None:
    """缺参与物 state:不 AttributeError;账本轴单列 violated;依赖项
    unknown + prerequisite_failed_not_run;admission R1b 拒绝(非 R1)。"""
    states = _states(ETHANOL)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      _prod(build_chemical_state(
                          ACETALDEHYDE, STRUCTURE_ORIGIN_SOURCE_PRODUCT
                      ).state_id)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="missing-state")
    audit = audit_hypothesis(hyp, states={states[ETHANOL].state_id:
                                          states[ETHANOL]})
    refs_check = next(c for c in audit.checks
                      if c.name == CHECK_PARTICIPANT_STATE_REFS)
    assert refs_check.status == CHECK_VIOLATED
    assert refs_check.reason_code == "participant_state_missing"
    parse_check = next(c for c in audit.checks
                       if c.name == CHECK_STRUCTURE_PARSE_VALENCE)
    assert parse_check.status == CHECK_UNKNOWN  # 不能核,不是语法非法
    # 依赖结构的后续项不执行
    elem = next(c for c in audit.checks
                if c.name == CHECK_ELEMENT_ACCOUNTING)
    assert elem.status == CHECK_UNKNOWN
    assert elem.reason_code == PREREQUISITE_FAILED
    d, reasons = decide_admission(audit)
    assert d == ADMISSION_REJECT
    assert reasons[0].startswith("R1b:participant_state_missing")
    assert "structure_unparseable" not in reasons[0]  # 理由码不压平


def test_r2_01_no_context_is_unknown_not_not_applicable() -> None:
    """缺 context ⇒ condition_check=unknown(condition_assessment_not_run),
    不得记 not_applicable/mo_context;全配平假设不得进 R6(mimo 3.2(1))。"""
    states = _states(ETHANOL, O2, ACETIC_ACID, WATER)
    hyp = _balanced_hypothesis(states)
    audit = audit_hypothesis(hyp, states={
        s.state_id: s for s in states.values()}, context=None)
    cond = next(c for c in audit.checks if c.name == CHECK_CONDITION_CHECK)
    assert cond.status == CHECK_UNKNOWN
    assert "condition_assessment_not_run" in cond.reason_code
    d, reasons = decide_admission(audit)
    assert d == ADMISSION_RETAIN_CONDITIONAL
    assert any(r.startswith("R5:unknown_checks_present") for r in reasons)
    assert d != ADMISSION_EXPAND  # 复审反例:配平+无 context 曾直达 R6


def test_r2_01_narrow_audit_scope_cannot_reach_expand() -> None:
    """窄 audit_scope({parse})只是诊断:必需覆盖缺口 ⇒ R5c,不得 R6。"""
    states = _states(ETHANOL, O2, ACETIC_ACID, WATER)
    hyp = _balanced_hypothesis(states)
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(),
        audit_scope={CHECK_STRUCTURE_PARSE_VALENCE})
    d, reasons = decide_admission(audit)
    assert d == ADMISSION_RETAIN_CONDITIONAL
    assert any(r.startswith("R5c:required_check_coverage_missing")
               for r in reasons)
    # 复审反例:窄 scope + 一条 verified 曾返回 expand/R6


def test_r2_01_self_reported_signature_not_center_evidence() -> None:
    """自报 transformation_signature_status=verified 无证据 ⇒ 中心
    unknown(center_evidence_missing);有氧上下文下也不进 R6。"""
    states = _states(ETHANOL, O2, ACETIC_ACID, WATER)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      Participant(state_ref=states[O2].state_id,
                                  side=PARTICIPANT_SIDE_REACTANT,
                                  role=PARTICIPANT_ROLE_COSUBSTRATE,
                                  coefficient=1,
                                  coefficient_status=COEFFICIENT_KNOWN),
                      _prod(states[ACETIC_ACID].state_id),
                      _prod(states[WATER].state_id, role="coproduct")],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="self-report",
        transformation_ref="",
        transformation_signature_status="verified")  # 自报,无证据
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context())
    center = next(c for c in audit.checks
                  if c.name == CHECK_TRANSFORMATION_CENTER)
    assert center.status == CHECK_UNKNOWN
    assert "center_evidence_missing" in center.reason_code
    d, _ = decide_admission(audit)
    assert d != ADMISSION_EXPAND


def test_r2_01_center_evidence_with_real_donor_diagnostic_reaches_verified(
        ) -> None:
    """注册确定性 checker(供体诊断)证据 ⇒ 中心 verified;合法全核实
    路径(真实编辑协议)可达 R6 expand。"""
    current, edits, execution = _ethanol_co_execution()
    diag = _diag(current, edits, execution, ["dC", "dO"],
                 {"dC": "S_C_2", "dO": "S_O_1"})
    assert diag.reaction_center_match is True
    evidence = center_evidence_from_donor_diagnostic(diag)
    assert evidence["checker_version"] == "ppv1-donor-diagnostic-4"
    states = _states(ETHANOL, O2, ACETIC_ACID, WATER)
    hyp = _balanced_hypothesis(states)
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=evidence)
    center = next(c for c in audit.checks
                  if c.name == CHECK_TRANSFORMATION_CENTER)
    assert center.status == CHECK_VERIFIED
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert d == ADMISSION_EXPAND


def test_r2_01_unregistered_center_checker_rejected() -> None:
    """未注册 checker 版本的证据 ⇒ unknown(center_checker_not_registered)。"""
    states = _states(ETHANOL, O2, ACETIC_ACID, WATER)
    hyp = _balanced_hypothesis(states)
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(),
        center_evidence={"checker_version": "some-model-said-so",
                         "center_match": True})
    center = next(c for c in audit.checks
                  if c.name == CHECK_TRANSFORMATION_CENTER)
    assert center.status == CHECK_UNKNOWN
    assert "center_checker_not_registered" in center.reason_code


def test_r2_01_center_mismatch_is_violated_r5v_not_r5d() -> None:
    """center_match=False(确定性 checker 偏离)⇒ violated + R5v
    declared_violated_other;不落 R5d(集合显式限定元素/电荷,mimo 3.2(4))。"""
    states = _states(ETHANOL, O2, ACETIC_ACID, WATER)
    hyp = _balanced_hypothesis(states)
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(),
        center_evidence={"checker_version": "ppv1-donor-diagnostic-4",
                         "center_match": False,
                         "declaration_mismatch": False})
    center = next(c for c in audit.checks
                  if c.name == CHECK_TRANSFORMATION_CENTER)
    assert center.status == CHECK_VIOLATED
    d, reasons = decide_admission(audit)
    assert d == ADMISSION_RETAIN_CONDITIONAL
    assert any(r.startswith("R5v:declared_violated_other") for r in reasons)
    assert not any(r.startswith("R5d:") for r in reasons)


def test_r2_01_r5d_limited_to_element_and_charge() -> None:
    """元素 violated ⇒ R5d(R5d 触发集合限定的正例钉住)。"""
    states = _states(ETHANOL, ACETALDEHYDE)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      _prod(states[ACETALDEHYDE].state_id)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="r5d-limit")
    audit = audit_hypothesis(hyp, states={
        s.state_id: s for s in states.values()})
    d, reasons = decide_admission(audit)
    assert any(r.startswith("R5d:declared_account_violated") for r in reasons)


def test_r2_01_input_hash_covers_actual_inputs() -> None:
    """input_hash 覆盖实际科学输入:同 hypothesis 不同 context/前提/
    scope ⇒ 不同 hash;相同输入重放幂等(R2-07 audit 侧)。"""
    states = _states(ETHANOL, O2, ACETIC_ACID, WATER)
    hyp = _balanced_hypothesis(states)
    state_map = {s.state_id: s for s in states.values()}
    a1 = audit_hypothesis(hyp, states=state_map, context=None)
    a2 = audit_hypothesis(hyp, states=state_map,
                          context=_aerobic_context())
    a3 = audit_hypothesis(hyp, states=state_map, context=None,
                          audit_scope={CHECK_STRUCTURE_PARSE_VALENCE})
    assert a1.input_hash == audit_hypothesis(
        hyp, states=state_map, context=None).input_hash  # 幂等
    assert len({a1.input_hash, a2.input_hash, a3.input_hash}) == 3
    # 前提变化(同反应不同条件要求)也改变 hash:requirements 进入
    # hypothesis 语义载荷(cond 线 R2-07),audit 直接复利
    hyp2 = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      Participant(state_ref=states[O2].state_id,
                                  side=PARTICIPANT_SIDE_REACTANT,
                                  role=PARTICIPANT_ROLE_COSUBSTRATE,
                                  coefficient=1,
                                  coefficient_status=COEFFICIENT_KNOWN),
                      _prod(states[ACETIC_ACID].state_id),
                      _prod(states[WATER].state_id, role="coproduct")],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="r2-chem",
        requirements=[{"key": "oxygen_regime", "level": "essential",
                       "value": "anaerobic", "source_refs": SRC}])
    a4 = audit_hypothesis(hyp2, states=state_map, context=None)
    assert a4.input_hash != a1.input_hash


# ============================================================ R2-03 供体诊断


def test_r2_03_zero_net_change_never_true() -> None:
    """真实执行器零净变化(single→single;复审 f11_real_executor_
    zero_net_change):center=unknown(no_executed_change),永不 True。"""
    render = roundtrip(ETHANOL, name="S")
    edits = [{"op": "change_bond_order", "atom1": "S_C_2",
              "atom2": "S_O_1", "from_order": "single",
              "to_order": "single"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    diag = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "z"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.reaction_center_match is None
    assert diag.net_change_empty is True
    assert diag.executed_bond_changes == []
    assert any("no_executed_change" in r
               for r in diag.missing_info_reasons)
    # 声明触及但未发生的原子单列,不参与判定
    assert set(diag.declaration_only) == {"S_C_2", "S_O_1"}


def test_r2_03_round_trip_edit_zero_net_change() -> None:
    """single→double→single(净变化为零):center=unknown(真实执行器
    复审场景 f11_declared_change_executed_unchanged 同族)。"""
    render = roundtrip(ETHANOL, name="S")
    edits = [{"op": "change_bond_order", "atom1": "S_C_2",
              "atom2": "S_O_1", "from_order": "single",
              "to_order": "double"},
             {"op": "change_bond_order", "atom1": "S_C_2",
              "atom2": "S_O_1", "from_order": "double",
              "to_order": "single"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    diag = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "z2"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.reaction_center_match is None
    assert diag.net_change_empty is True


def test_r2_03_declaration_execution_mismatch_unknown() -> None:
    """声明改 A 键、实际执行改 B 键 ⇒ declaration_mismatches,
    strict/center 至少 unknown(声明–执行对账,mimo 5.2(a))。"""
    current, _, exec_a = _ethanol_co_execution()  # 实际改 C–O
    # 声明却指向 C–C 键(执行结果与声明不一致)
    declared_edits = [{"op": "change_bond_order", "atom1": "S_C_1",
                       "atom2": "S_C_2", "from_order": "single",
                       "to_order": "double"}]
    diag = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "m"},
        expectation={"target_smiles": exec_a["product_smiles"]},
        result=exec_a, edits=declared_edits)
    assert diag.declaration_mismatches  # 对账失败有明细
    assert diag.reaction_center_match is None
    assert diag.strict_target_match is None


def test_r2_03_joint_symmetric_equivalent_proven_by_mapping() -> None:
    """联合对称:丁烷反转 —— 中心 {C1,C2}(idx 0,1),实际变化 {C3,C4}
    (idx 2,3):存在单一自同构(链反转)整体映射 ⇒ True +
    symmetric_equivalent + joint_mapping 证据。"""
    render = roundtrip("CCCC", name="S")
    edits = [{"op": "change_bond_order", "atom1": "S_C_3",
              "atom2": "S_C_4", "from_order": "single",
              "to_order": "double"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    diag = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dA", "dB"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dA": "S_C_1", "dB": "S_C_2"},
                   "equivalence_classes": [], "ref": "j"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.reaction_center_match is True
    assert diag.center_match_basis == "symmetric_equivalent"
    assert diag.joint_mapping.get("center_image") == [2, 3]
    assert "图等价≠酶识别" in diag.joint_mapping.get(
        "equivalence_note", "")


def test_r2_03_single_atom_orbits_not_joint_symmetry() -> None:
    """联合反例(复审 f11_independent_orbits_not_joint_symmetry):
    环己烷中心相邻对 {0,1},实际成键 {0,3}(对位)。六个碳各自同轨道,
    但不存在单一自同构把 {0,1} 整体映到 {0,3} ⇒ False(不冒充)。"""
    render = roundtrip("C1CCCCC1", name="S")
    edits = [{"op": "form_bond", "atom1": "S_C_1", "atom2": "S_C_4"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    diag = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dA", "dB"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dA": "S_C_1", "dB": "S_C_2"},
                   # 复审场景:六个碳各自同轨道(合法等价类,全同 rank);
                   # v3 中等价类不参与判定,联合映射给出诚实 False
                   "equivalence_classes": [["S_C_1", "S_C_2", "S_C_3",
                                            "S_C_4", "S_C_5", "S_C_6"]],
                   "ref": "cyclo"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    assert diag.reaction_center_match is False
    assert diag.center_match_basis == ""  # 非 True 不声称 basis
    assert not diag.joint_mapping


def test_r2_03_symmetry_broken_after_first_substitution() -> None:
    """第一次取代/成键后对称破:第二次编辑按**新图**自身的对称判定,
    不外推旧图等价(第一次成功之后环己烷图已变)。"""
    render = roundtrip("C1CCCCC1", name="S")
    first_edits = [{"op": "change_bond_order", "atom1": "S_C_1",
                    "atom2": "S_C_2", "from_order": "single",
                    "to_order": "double"}]  # 中心内合法变化
    first_exec = execute_edits(render, first_edits)
    assert first_exec["ok"] is True
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    diag1 = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dA", "dB"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dA": "S_C_1", "dB": "S_C_2"},
                   "equivalence_classes": [], "ref": "s1"},
        expectation={"target_smiles": first_exec["product_smiles"]},
        result=first_exec, edits=first_edits)
    assert diag1.reaction_center_match is True
    # 第二次:在**产物图**(双环,对称已破)上继续,同一中心不再有
    # 把变化映到对位轨道的联合映射 ⇒ 不因旧图曾对称而 True
    render2 = roundtrip(first_exec["product_smiles"], name="T")
    second_edits = [{"op": "form_bond", "atom1": "T_C_1",
                     "atom2": "T_C_4"}]
    second_exec = execute_edits(render2, second_edits)
    current2 = {"smiles": render2.smiles,
                "atom_id_map": dict(render2.atom_id_map)}
    diag2 = check_edit_against_donor(
        current=current2, donor={"center_atom_ids": ["dA", "dB"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dA": "T_C_1", "dB": "T_C_2"},
                   "equivalence_classes": [], "ref": "s2"},
        expectation={"target_smiles": second_exec["product_smiles"]},
        result=second_exec, edits=second_edits)
    # 产物图自身无 {0,1}→{0,3} 的联合映射 ⇒ False/None(诚实),不外推
    assert diag2.reaction_center_match in (False, None)


def test_r2_03_plain_vs_mapped_product_disagreement() -> None:
    """plain 产物与 mapped 执行图不一致 ⇒ strict/center 均 unknown
    (复审 f11_plain_product_mapped_product_disagree)。"""
    current, edits, execution = _ethanol_co_execution()
    tampered = dict(execution)
    # 对外产物串换成另一个分子(与 mapped 图不一致)
    tampered["product_smiles"] = "CCCO"
    diag = check_edit_against_donor(
        current=current, donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "pm"},
        expectation={"target_smiles": ACETALDEHYDE},
        result=tampered, edits=edits)
    assert diag.strict_target_match is None
    assert diag.reaction_center_match is None
    assert any("plain_product_mapped_product_disagreement" in r
               for r in diag.missing_info_reasons)


def _crafted_result(product_smiles: str, atom_id_map: dict[str, int]):
    """按构造索引手工生成带映射号的产物图(合成不一致输出探针同型)。"""
    mol = Chem.MolFromSmiles(product_smiles)
    assert mol is not None, product_smiles
    idx_to_id = {i: aid for aid, i in atom_id_map.items()}
    for atom in mol.GetAtoms():
        aid = idx_to_id.get(atom.GetIdx())
        if aid is not None:
            atom.SetAtomMapNum(atom.GetIdx() + 1)
    mapped = Chem.MolToSmiles(mol)
    return {"ok": True, "reasons": [], "product_smiles": product_smiles,
            "product_mapped_smiles": mapped,
            "atom_id_map": dict(atom_id_map)}


def test_r2_03_charge_only_change_visible() -> None:
    """仅形式电荷变化(v2 不可见,复审 f11_nonbond_actual_change_
    invisible):变化集可见;在中心内 ⇒ center=True(direct);在中心
    外 ⇒ False + extra_changes 带 before/after 电荷。"""
    render = roundtrip("NCC", name="S")
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    id_map = dict(render.atom_id_map)  # S_N_1:0, S_C_2:1, S_C_3:2
    result = _crafted_result("[NH3+]CC", id_map)
    edits = []
    # 电荷变化原子 = S_N_1
    inside = _diag(current, edits, result, ["dN"],
                   {"dN": "S_N_1"}, target="[NH3+]CC")
    assert inside.reaction_center_match is True
    assert inside.center_match_basis == "direct"
    outside = _diag(current, edits, result, ["dC"],
                    {"dC": "S_C_2"}, target="[NH3+]CC")
    assert outside.reaction_center_match is False
    n_entry = next(e for e in outside.extra_changes
                   if e["atom_id"] == "S_N_1")
    assert n_entry["formal_charge"] == {"before": 0, "after": 1}
    assert "formal_charge" in n_entry["delta"]


def test_r2_03_stereo_only_change_visible() -> None:
    """仅对映体翻转(v2 不可见):CIP 变化可见;中心外 ⇒ extra 带
    before/after CIP。"""
    render = roundtrip("C[C@H](O)CC", name="S")
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    id_map = dict(render.atom_id_map)
    result = _crafted_result("C[C@@H](O)CC", id_map)
    edits = []
    # 手性中心的 MoleCode ID 带立体后缀(从渲染图取真实 ID)
    center_atom = next(aid for aid, idx in id_map.items() if idx == 1)
    inside = _diag(current, edits, result, ["dC"],
                   {"dC": center_atom}, target="C[C@@H](O)CC")
    assert inside.reaction_center_match is True
    outside = _diag(current, edits, result, ["dO"],
                    {"dO": "S_O_1"}, target="C[C@@H](O)CC")
    assert outside.reaction_center_match is False
    stereo_entry = next(e for e in outside.extra_changes
                        if e["atom_id"] == center_atom)
    assert stereo_entry["stereo"]["before_cip"] != \
        stereo_entry["stereo"]["after_cip"]
    assert stereo_entry["stereo"]["before_cip"] in ("R", "S")
    assert stereo_entry["stereo"]["after_cip"] in ("R", "S")


def test_r2_03_extra_changes_carry_h_delta() -> None:
    """extra_changes 逐原子 ΔH(mimo 5.2(a)):乙醇 C–O 双键化,O 在
    中心外 ⇒ h_count before/after(1→0)。"""
    current, edits, execution = _ethanol_co_execution()
    diag = _diag(current, edits, execution, ["dC"], {"dC": "S_C_2"})
    assert diag.reaction_center_match is False
    o_entry = next(e for e in diag.extra_changes if e["atom_id"] == "S_O_1")
    assert o_entry["h_count"]["before"] == 1
    assert o_entry["h_count"]["after"] == 0
    assert "h_count" in o_entry["delta"]


def test_r2_03_abs_annotation_difference_not_strict_failure() -> None:
    """供体被冤枉反例(mimo 1.4(1)):预期 plain、产物带 |a:1|(同一
    立体事实)⇒ strict=True(规范化吸收注解差异);零变化 ⇒ center
    如实 unknown。"""
    render = roundtrip("F[C@H](Cl)Br", name="S")
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    result = _crafted_result("F[C@H](Cl)Br |a:1|",
                             dict(render.atom_id_map))
    diag = _diag(current, [], result, ["dF"],
                 {"dF": "S_F_1"}, target="F[C@H](Cl)Br")
    assert diag.strict_target_match is True  # 注解差异不是化学差异
    assert diag.reaction_center_match is None  # 零净变化,如实 unknown


def test_r2_03_equivalence_classes_disclosed_not_used() -> None:
    """等价类:被拒的类披露(rejected);采信口径带
    equivalence_basis=canonical_rank_breakTies_false;v3 等价类不参与
    center 判定(联合映射取代)。"""
    current, edits, execution = _ethanol_co_execution()
    diag = _diag(current, edits, execution, ["dC"], {"dC": "S_C_2"},
                 equivalence=[["S_C_2", "S_O_1"]])  # C/O 非等价 ⇒ 拒
    assert any("equivalence_class_rejected" in r
               for r in diag.missing_info_reasons)
    assert diag.equivalence_basis == "canonical_rank_breakTies_false"
    # 判定走实际变化与联合映射(等价类拒用不影响判定路径)
    assert diag.reaction_center_match is False


# ============================================================ R2-12 门禁消费


def _gate_mapper_payload(per_product):
    return legacy_validation_to_gate_decisions({
        "evidence_id": "E-r2-12",
        "gates": {
            "direction_source": {"ok": True, "reason": ""},
            "recorded_eligibility": {"ok": True, "reason": ""},
        },
        "verdicts": per_product,
    })


def _all_verified_audit():
    current, edits, execution = _ethanol_co_execution()
    diag = _diag(current, edits, execution, ["dC", "dO"],
                 {"dC": "S_C_2", "dO": "S_O_1"})
    states = _states(ETHANOL, O2, ACETIC_ACID, WATER)
    hyp = _balanced_hypothesis(states)
    return audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(),
        center_evidence=center_evidence_from_donor_diagnostic(diag))


def test_r2_12_all_products_gate_rejected_rejects() -> None:
    """全部共同产物被活动门禁拒绝 ⇒ R2p reject(保留逐产物拒因)。"""
    audit = _all_verified_audit()
    gates = _gate_mapper_payload([
        {"position": 0, "accepted": False,
         "reasons": ["element_gate_rejected"]},
        {"position": 1, "accepted": False,
         "reasons": ["element_gate_rejected"]}])
    d, reasons = decide_admission(audit, gate_decisions=gates)
    assert d == ADMISSION_REJECT
    assert reasons[0].startswith(
        "R2p:per_product_gate_rejected:all_products_gate_rejected")
    assert "element_gate_rejected" in reasons[0]
    assert "position:0" in reasons[0] and "position:1" in reasons[0]


def test_r2_12_some_products_gate_rejected_retains_with_reasons() -> None:
    """部分共同产物被拒 ⇒ retain_conditional;被拒产物拒因可追溯、
    不可展开;不删除被拒共同产物凑合法事件(R2-12 复审反例
    mapped_per_product_reject_ignored:v2 曾 expand/R6)。"""
    audit = _all_verified_audit()
    gates = _gate_mapper_payload([
        {"position": 0, "accepted": True, "reasons": []},
        {"position": 1, "accepted": False,
         "reasons": ["element_gate_rejected"]}])
    d, reasons = decide_admission(audit, gate_decisions=gates)
    assert d == ADMISSION_RETAIN_CONDITIONAL  # 不再 expand
    assert reasons[0].startswith(
        "R2p:per_product_gate_rejected:some_products_gate_rejected")
    assert "position:1" in reasons[0]
    assert "element_gate_rejected" in reasons[0]


def test_r2_12_product_state_refs_surface_in_reasons() -> None:
    """逐产物拒因可落到具体产物 state_ref(product_state_refs)。"""
    audit = _all_verified_audit()
    states = _states(ETHANOL, O2, ACETIC_ACID, WATER)
    gates = _gate_mapper_payload([
        {"position": 0, "accepted": True, "reasons": []},
        {"position": 1, "accepted": False,
         "reasons": ["element_gate_rejected"]}])
    d, reasons = decide_admission(
        audit, gate_decisions=gates,
        product_state_refs=[states[ACETIC_ACID].state_id,
                            states[WATER].state_id])
    assert d == ADMISSION_RETAIN_CONDITIONAL
    assert states[WATER].state_id in reasons[0]


def test_r2_12_per_product_consumption_policy_versioned() -> None:
    """消费开关由策略显式版本化:off 时逐产物拒绝不改变处置
    (diagnostic-only,与"未被消费"的区别:off 是显式声明)。"""
    audit = _all_verified_audit()
    gates = _gate_mapper_payload([
        {"position": 0, "accepted": False,
         "reasons": ["element_gate_rejected"]}])
    policy = AdmissionPolicy(
        per_product_gate_consumption="off")
    d, _ = decide_admission(audit, policy=policy, gate_decisions=gates)
    assert d == ADMISSION_EXPAND  # off ⇒ 不消费(显式声明,非遗漏)
    # 策略往返保留开关;非法值拒绝
    restored = AdmissionPolicy.from_dict(policy.to_dict())
    assert restored.per_product_gate_consumption == "off"
    with pytest.raises(Exception):
        AdmissionPolicy.from_dict({
            "policy_version": policy.policy_version,
            "per_product_gate_consumption": "maybe"})


def test_r2_12_all_products_accepted_no_effect() -> None:
    """逐产物全 accepted ⇒ 无 R2p 效果,合法路径仍 expand。"""
    audit = _all_verified_audit()
    gates = _gate_mapper_payload([
        {"position": 0, "accepted": True, "reasons": []},
        {"position": 1, "accepted": True, "reasons": []}])
    d, _ = decide_admission(
        audit, gate_decisions=gates,
        product_state_refs=["cs_x", "cs_y"])
    assert d == ADMISSION_EXPAND


# ======================================================== mimo 采纳(字段级)


def test_mimo_h_plus_pattern_structured_and_renamed() -> None:
    """H+ 模式输出名 H+_count1(仅 H 计数,不含质子/电子计量)且为
    结构化字段(mimo 2.3(2))。NH4+ → NH3:ΔH=+1。"""
    states = _states("[NH4+]", "N")
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states["[NH4+]"].state_id,
        participants=[_sub(states["[NH4+]"].state_id),
                      _prod(states["N"].state_id)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="hplus")
    audit = audit_hypothesis(hyp, states={
        s.state_id: s for s in states.values()})
    check = next(c for c in audit.checks
                 if c.name == CHECK_ELEMENT_ACCOUNTING)
    assert check.detail["omission_pattern_matches"] == [{
        "pattern": "H+_count1", "excess_on": "reactant_side",
        "missing_from": "product_side", "element_delta": {"H": "1"}}]


def test_mimo_element_accounting_notes_disclosed() -> None:
    """元素账口径注记:同位素并入 H、自由基不入账、verified 仅指
    元素+形式电荷数值闭合(mimo 2.2(a))。"""
    mol = Chem.MolFromSmiles("[2H]OC(C)C")
    counts = element_counts_full(mol)
    assert counts["H"] == 8  # D 并入 H([2H]OC(C)C = C3H8O 的全氢口径)
    states = _states(ETHANOL, O2, ACETIC_ACID, WATER)
    hyp = _balanced_hypothesis(states)
    audit = audit_hypothesis(hyp, states={
        s.state_id: s for s in states.values()})
    check = next(c for c in audit.checks
                 if c.name == CHECK_ELEMENT_ACCOUNTING)
    assert "isotopes_D_T_counted_as_H" in check.detail["accounting_notes"]
    assert "radical_electrons_not_counted" in check.detail[
        "accounting_notes"]


def test_mimo_identity_fidelity_axes_not_as_written_unknown() -> None:
    """身份保真分轴呈现(mimo 1.4(4)):任一轴非 as_written(存档形)
    ⇒ identity_fidelity=unknown 并列轴,不再 verified+注记混读。"""
    archive = build_chemical_state(
        ACETALDEHYDE, STRUCTURE_ORIGIN_SOURCE_PRODUCT,
        fidelity={"stereo": "absent_in_archive",
                  "isotope": "absent_in_archive",
                  "formal_charge": "as_written",
                  "protonation_basis": "as_written"})
    plain = build_chemical_state(ETHANOL, STRUCTURE_ORIGIN_SOURCE_PRODUCT)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=plain.state_id,
        participants=[_sub(plain.state_id), _prod(archive.state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL
        if False else PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="fidelity-axes")
    audit = audit_hypothesis(hyp, states={
        archive.state_id: archive, plain.state_id: plain})
    check = next(c for c in audit.checks if c.name == "identity_fidelity")
    assert check.status == CHECK_UNKNOWN
    assert "stereo=absent_in_archive" in check.reason_code
    assert check.detail["fidelity_axis_notes"]


# 未落地条款标注(pending,不冒充已实现):检查公开 docstring 声明
def test_pending_clauses_declared_not_implemented() -> None:
    """local_delta/edge_kind/scoring_key 为 contract clause pending;
    模块 docstring 显式声明未落地,不得与已实现条款并列(§7 mimo)。"""
    from pathlib import Path as _Path

    audit_src = _Path(__file__).resolve().parents[1] / \
        "src/pathway_v43/pollutant/audit.py"
    chemstate_src = _Path(__file__).resolve().parents[1] / \
        "src/pathway_v43/pollutant/chemstate.py"
    audit_doc = audit_src.read_text(encoding="utf-8")
    assert "implementation pending" in audit_doc
    assert "local_delta" in audit_doc
    chemstate_doc = chemstate_src.read_text(encoding="utf-8")
    assert "implementation pending" in chemstate_doc
    assert "scoring_key" in chemstate_doc
