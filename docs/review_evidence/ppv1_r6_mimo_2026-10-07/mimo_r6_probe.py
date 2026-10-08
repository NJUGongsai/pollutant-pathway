#!/usr/bin/env python
"""mimo 第六轮独立探针(规则级合成夹具,公开链,无金标/封存数据)。

Run A (HEAD):     PROBE_SRC=<repo>/src python mimo_r6_probe.py
Run B (baseline): BASELINE=1 PROBE_SRC=<wt>/src python mimo_r6_probe.py
   (baseline 只跑 A1/A2/A3 覆盖反例与3b 镜像观察,v6 专属段跳过)
"""
import json
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.environ.get("PROBE_SRC", "src"))
BASELINE = os.environ.get("BASELINE") == "1"

from rdkit import Chem  # noqa: E402

from pathway_v43.pollutant.audit import (  # noqa: E402
    ADMISSION_EXPAND,
    CHECK_ELEMENT_ACCOUNTING,
    CHECK_FORMAL_CHARGE_ACCOUNTING,
    CHECK_TRANSFORMATION_CENTER,
    CHECK_UNKNOWN,
    CHECK_VERIFIED,
    audit_hypothesis,
    center_evidence_from_donor_diagnostic,
    check_edit_against_donor,
    decide_admission,
)
from pathway_v43.pollutant.chemstate import (  # noqa: E402
    ChemicalStateError,
    STRUCTURE_ORIGIN_RAW_INPUT,
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
    CONDITION_KEY_ELECTRON_DONOR,
    CONDITION_KEY_MATRIX,
    CONDITION_KEY_OXYGEN,
    CONDITION_KEY_PH,
    CONDITION_KEY_TEMPERATURE,
    ConditionContractError,
    PathContext,
    aggregate_environment_fit,
    build_condition_fact,
    build_dependency,
    build_path_context,
    build_requirement,
    derive_child_context,
    detect_circular_dependencies,
    resolve_dependency,
)
from pathway_v43.services.atom_tool import (  # noqa: E402
    execute_edits,
    render,
    roundtrip,
)

OUT = {}


def rec(key, value):
    OUT[key] = value
    print(f"{key} = {json.dumps(value, ensure_ascii=False, default=str)}",
          flush=True)


ETHANOL, ACETALDEHYDE, HYDROGEN, EPOXIDE = "CCO", "CC=O", "[H][H]", "C1CO1"
SRC = ["src:rule-r6-mimo"]


# ------------------------------------------------------------ 夹具(合成)
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


def _states(*smiles):
    return {s: build_chemical_state(s, STRUCTURE_ORIGIN_RAW_INPUT)
            for s in smiles}


def _hyp(states, reactants, products, group="mimo-r6"):
    participants = (
        [_sub(states[smi].state_id, coeff)
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
    rr = roundtrip(substrate, name="S")
    edits = [{"op": "change_bond_order", "atom1": a1, "atom2": a2,
              "from_order": from_order, "to_order": to_order}]
    ex = execute_edits(rr, edits)
    assert ex["ok"], ex
    diag = check_edit_against_donor(
        current={"smiles": rr.smiles, "atom_id_map": dict(rr.atom_id_map)},
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": a1, "dO": a2},
                   "equivalence_classes": [], "ref": "mimo-r6"},
        expectation={"target_smiles": ex["product_smiles"]},
        result=ex, edits=edits)
    assert diag.reaction_center_match is True
    return center_evidence_from_donor_diagnostic(diag)


def _oxidation_evidence():
    return _donor_evidence(ETHANOL, "S_C_2", "S_O_1", "single", "double")


def _reduction_evidence():
    return _donor_evidence(ACETALDEHYDE, "S_C_2", "S_O_1", "double",
                           "single")


def _addO_evidence():
    """真实 add_atom 证据:CCO 甲基碳挂 O ⇒ OCCO(乙二醇)。"""
    rr = roundtrip(ETHANOL, name="S")
    edits = [{"op": "add_atom", "element": "O", "atom1": "S_C_1",
              "new_atom_id": "S_O_9"}]
    ex = execute_edits(rr, edits)
    assert ex["ok"] and ex["product_smiles"] == "OCCO", ex
    diag = check_edit_against_donor(
        current={"smiles": rr.smiles, "atom_id_map": dict(rr.atom_id_map)},
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_1", "dO": "S_O_9"},
                   "equivalence_classes": [], "ref": "mimo-r6-addo"},
        expectation={"target_smiles": ex["product_smiles"]},
        result=ex, edits=edits)
    assert diag.reaction_center_match is True, diag.missing_info_reasons
    return center_evidence_from_donor_diagnostic(diag), ex


def _center(audit):
    return next(c for c in audit.checks
                if c.name == CHECK_TRANSFORMATION_CENTER)


def _run(states, hyp, evidence):
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        context=_aerobic_context(), center_evidence=evidence)
    c = _center(audit)
    try:
        d, _ = decide_admission(audit, gate_decisions={
            "gate_direction_source": {"ok": True}})
    except TypeError:
        d, _ = decide_admission(audit)
    return {
        "center": c.status,
        "reason": c.reason_code[:160],
        "coverage": c.detail.get("product_coverage"),
        "coverage_rule": c.detail.get("coverage_rule"),
        "substrate_scale": c.detail.get("substrate_scale"),
        "atom_delta": c.detail.get("atom_delta"),
        "uncovered_reactant_elements": c.detail.get(
            "uncovered_reactant_elements"),
        "uncovered_product_elements": c.detail.get(
            "uncovered_product_elements"),
        "violations": c.detail.get("coverage_violations"),
        "elements": audit.check_status(CHECK_ELEMENT_ACCOUNTING),
        "charge": audit.check_status(CHECK_FORMAL_CHARGE_ACCOUNTING),
        "admission": d,
        "expand": d == ADMISSION_EXPAND,
    }


# ================================================================ A 覆盖
def probe_coverage():
    ox, red = _oxidation_evidence(), _reduction_evidence()

    # A1 Codex 反例 1
    s1 = _states(ETHANOL, ACETALDEHYDE, EPOXIDE, HYDROGEN)
    h1 = _hyp(s1, [(ETHANOL, 1)],
              [(ACETALDEHYDE, Fraction(1, 2)), (EPOXIDE, Fraction(1, 2)),
               (HYDROGEN, 1)], group="mimo-a1")
    rec("A1_codex_one_sided_half", _run(s1, h1, ox))

    # A2 Codex 反例 2
    s2 = _states(ACETALDEHYDE, EPOXIDE, HYDROGEN, ETHANOL)
    h2 = _hyp(s2, [(ACETALDEHYDE, 1), (EPOXIDE, 1), (HYDROGEN, 2)],
              [(ETHANOL, 2)], group="mimo-a2")
    rec("A2_codex_cosubstrate_scaled", _run(s2, h2, red))

    # A3 正控制:合法氧化
    s3 = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    h3 = _hyp(s3, [(ETHANOL, 1)], [(ACETALDEHYDE, 1), (HYDROGEN, 1)],
              group="mimo-a3")
    rec("A3_control_oxidation", _run(s3, h3, ox))

    # A4 正控制:合法氢化
    h4 = _hyp(s2, [(ACETALDEHYDE, 1), (HYDROGEN, 1)], [(ETHANOL, 1)],
              group="mimo-a4")
    rec("A4_control_hydrogenation", _run(s2, h4, red))

    # A5 无未覆盖参与物但缺 H2:覆盖 full、元素账 violated、retain
    s5 = _states(ETHANOL, ACETALDEHYDE)
    h5 = _hyp(s5, [(ETHANOL, 1)], [(ACETALDEHYDE, 1)], group="mimo-a5")
    rec("A5_missing_H2_coverage_full_element_violated", _run(s5, h5, ox))

    # A6 add-O 证据 + 计量补全(½O2 与 [O] 两个身份)
    addo, ex6 = _addO_evidence()
    glycol = ex6["product_smiles"]
    s6 = _states(ETHANOL, glycol, "O=O", "[O]")
    h6a = _hyp(s6, [(ETHANOL, 1), ("O=O", Fraction(1, 2))],
               [(glycol, 1)], group="mimo-a6a")
    rec("A6a_completion_half_O2", _run(s6, h6a, addo))
    h6b = _hyp(s6, [(ETHANOL, 1), ("[O]", 1)], [(glycol, 1)],
               group="mimo-a6b")
    rec("A6b_completion_atomic_O_identity_freedom", _run(s6, h6b, addo))
    h6c = _hyp(s6, [(ETHANOL, 1)], [(glycol, 1)], group="mimo-a6c")
    rec("A6c_no_cosubstrate_element_axis_only", _run(s6, h6c, addo))

    # A7 旁观溶剂入参与物表(水进出两侧)⇒ 保守 partial
    s7 = _states(ETHANOL, ACETALDEHYDE, HYDROGEN, "O")
    h7 = _hyp(s7, [(ETHANOL, 1), ("O", 1)],
              [(ACETALDEHYDE, 1), (HYDROGEN, 1), ("O", 1)], group="mimo-a7")
    rec("A7_spectator_water_conservative_partial", _run(s7, h7, ox))

    # A8 未知系数 ⇒ coverage unknown
    s8 = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    parts = [
        _sub(s8[ETHANOL].state_id, 1),
        _prod(s8[ACETALDEHYDE].state_id, 1),
        Participant(state_ref=s8[HYDROGEN].state_id,
                    side=PARTICIPANT_SIDE_PRODUCT,
                    role=PARTICIPANT_ROLE_COPRODUCT, coefficient=None,
                    coefficient_status=COEFFICIENT_UNKNOWN)]
    h8 = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=s8[ETHANOL].state_id,
        participants=parts,
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="mimo-a8")
    rec("A8_unknown_coefficients", _run(s8, h8, ox))


# ================================================================ B CX 输入
def _cx(structure):
    try:
        st = build_chemical_state(structure, STRUCTURE_ORIGIN_RAW_INPUT)
        return {"accept": True, "state_id": st.state_id[:16],
                "identity": st.smiles_isomeric}
    except ChemicalStateError as e:
        return {"accept": False, "kind": e.detail.get("kind"),
                "msg": str(e)[:100]}


def probe_cx():
    bare = _cx("CCO")
    rec("B1_r_flag_build", _cx("CCO |r|"))
    try:
        strict_identity_of("CCO |r|")
        rec("B1b_r_flag_strict", {"accept": True})
    except ChemicalStateError as e:
        rec("B1b_r_flag_strict", {"accept": False,
                                  "kind": e.detail.get("kind")})
    rec("B2_Ln", _cx("C1CCCCC1 |Ln:1|"))
    rec("B3_atomProp_dots_same_id",
        {"bare": bare, "x": _cx("CO |atomProp:0.note.hello|")})
    rec("B4_label_same_id", {"x": _cx("CO |$_AV:one;two$|")})
    rec("B5_coords_same_id", {"x": _cx("CO |(0.5,0.8,;1,0.1,0.2,)|")})
    rec("B6_sgD_comma_same_id", {"x": _cx("CO |SgD:0:note:a,b::::|")})
    sru = _cx("CCCCCC |Sg:n:1,2,3:3:ht:::|")
    rt = _cx(sru["identity"]) if sru.get("accept") else None
    rec("B7_Sg_retained_roundtrip", {"first": sru, "roundtrip": rt})
    rec("B8_enhanced_group", _cx("C[C@H](Cl)[C@H](F)Cl |a:1,&1:3|"))
    # 边界(过拒方向,非身份谎言):含空格的登记类内容
    rec("B9a_label_with_space", _cx("CO |$_foo bar$|"))
    rec("B9b_coords_with_space", _cx("CO |(0.5, 0.8,)|"))
    rec("B9c_atomProp_with_space", _cx("CO |atomProp:0.note:hello world|"))
    rec("B10_plain_ok", _cx("CCO"))


# ================================================================ C known_absent
def _row(result, key):
    return {p["key"]: p for p in result.per_requirement}[key]


def probe_absent():
    def agg(facts, reqs):
        return aggregate_environment_fit(
            facts=facts, requirements=reqs,
            declared_scope=[reqs[0].key])

    f = build_condition_fact
    r = build_requirement
    # 同值数值缺席(点)⇒ unknown(numeric_absence)而非 conflict
    res = agg([f(key=CONDITION_KEY_PH, value=7.0,
                 status="known_absent", source_ref="src:x")],
              [r(key=CONDITION_KEY_PH, level="essential", value={"lo": 6.0,
                                                                 "hi": 8.0},
                 source_refs=SRC)])
    rec("C1_numeric_absence_interval_req", _row(res, CONDITION_KEY_PH))
    # 点值数值缺席同样 unknown
    res = agg([f(key=CONDITION_KEY_TEMPERATURE, value=25, unit="C",
                 status="known_absent", source_ref="src:x")],
              [r(key=CONDITION_KEY_TEMPERATURE, level="essential", value=25,
                 source_refs=SRC)])
    rec("C2_numeric_absence_point_req",
        _row(res, CONDITION_KEY_TEMPERATURE))
    # 异词缺席 ⇒ unknown
    res = agg([f(key=CONDITION_KEY_MATRIX, value="forest",
                 status="known_absent", source_ref="src:x")],
              [r(key=CONDITION_KEY_MATRIX, level="essential", value="soil",
                 source_refs=SRC)])
    rec("C3_other_string_absent", _row(res, CONDITION_KEY_MATRIX))
    # 同词缺席 ⇒ conflict
    res = agg([f(key=CONDITION_KEY_MATRIX, value="soil",
                 status="known_absent", source_ref="src:x")],
              [r(key=CONDITION_KEY_MATRIX, level="essential", value="soil",
                 source_refs=SRC)])
    rec("C4_same_word_absent", _row(res, CONDITION_KEY_MATRIX))
    # 同值 present+absent 并存 ⇒ 保守 unknown(conflicting facts)
    res = agg([f(key=CONDITION_KEY_OXYGEN, value="aerobic",
                 status="known_present", source_ref="src:p"),
               f(key=CONDITION_KEY_OXYGEN, value="aerobic",
                 status="known_absent", source_ref="src:a")],
              [r(key=CONDITION_KEY_OXYGEN, level="essential",
                 value="aerobic", source_refs=SRC)])
    rec("C5_present_plus_absent_same_value",
        _row(res, CONDITION_KEY_OXYGEN))
    # 物种实体缺席 ⇒ conflict(保持)
    res = agg([f(key=CONDITION_KEY_ELECTRON_DONOR, value="NADH",
                 status="known_absent", source_ref="src:x")],
              [r(key=CONDITION_KEY_ELECTRON_DONOR, level="essential",
                 value="NADH", source_refs=SRC)])
    rec("C6_species_absent_control",
        _row(res, CONDITION_KEY_ELECTRON_DONOR))


# ================================================================ D 镜像
def _sigma(substrate, pair):
    r = render(substrate, name="U")
    ids = {idx: aid for aid, idx in r.atom_id_map.items()}
    edits = [{"op": "break_bond", "atom1": ids[pair[0]],
              "atom2": ids[pair[1]]}]
    ex = execute_edits(r, edits)
    assert ex["ok"], ex
    n = len(ids)
    diag = check_edit_against_donor(
        current={"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)},
        donor={"center_atom_ids": [f"d{i}" for i in range(n)]},
        alignment={"status": "resolved",
                   "donor_to_current": {f"d{i}": ids[i]
                                        for i in range(n)},
                   "equivalence_classes": [], "ref": "mimo-mirror"},
        expectation={"target_smiles": ex["product_smiles"]},
        result=ex, edits=edits)
    return ex, diag


def probe_mirror():
    ex, diag = _sigma("C/C=C/C", (0, 1))
    rec("D1_adjacent_sigma_break", {
        "product": ex["product_smiles"],
        "mismatches": diag.declaration_mismatches,
        "center": diag.reaction_center_match,
        "strict": diag.strict_target_match})
    ex, diag = _sigma("C/C=C/CCC", (4, 5))
    rec("D2_distal_break_control", {
        "product": ex["product_smiles"],
        "mismatches": diag.declaration_mismatches,
        "center": diag.reaction_center_match})
    ex, diag = _sigma("C/C=C(C)/C", (0, 1))
    rec("D3_trisubstituted_adjacent_break", {
        "product": ex["product_smiles"],
        "mismatches": diag.declaration_mismatches,
        "center": diag.reaction_center_match})

    # D4 声明≠执行:声明改键级、实际断 C-C ⇒ 失配仍检出
    rr = roundtrip(ETHANOL, name="S")
    ids = {idx: aid for aid, idx in rr.atom_id_map.items()}
    ex_bad = execute_edits(rr, [{"op": "break_bond", "atom1": ids[0],
                                 "atom2": ids[1]}])
    assert ex_bad["ok"]
    declared = [{"op": "change_bond_order", "atom1": ids[1],
                 "atom2": ids[2], "from_order": "single",
                 "to_order": "double"}]
    diag = check_edit_against_donor(
        current={"smiles": rr.smiles, "atom_id_map": dict(rr.atom_id_map)},
        donor={"center_atom_ids": ["d1", "d2", "d3"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"d1": ids[0], "d2": ids[1],
                                        "d3": ids[2]},
                   "equivalence_classes": [], "ref": "mimo-forged"},
        expectation={"target_smiles": ex_bad["product_smiles"]},
        result=ex_bad, edits=declared)
    rec("D4_undeclared_vs_declared_detected", {
        "mismatches": diag.declaration_mismatches[:4],
        "center": diag.reaction_center_match,
        "strict": diag.strict_target_match})

    # D5 接口合成 E→Z(零声明)⇒ 立体变化入集、声明对账失配(控制)
    r = render("C/C=C/C", name="E")
    m = Chem.MolFromSmiles(r.smiles)
    for a in m.GetAtoms():
        a.SetAtomMapNum(a.GetIdx() + 1)
    b = next(bd for bd in m.GetBonds()
             if bd.GetBondType() == Chem.BondType.DOUBLE)
    b.SetStereo(Chem.BondStereo.STEREOZ)
    Chem.SetDoubleBondNeighborDirections(m)
    plain = Chem.Mol(m)
    for a in plain.GetAtoms():
        a.SetAtomMapNum(0)
    synth = {"ok": True, "reasons": [], "n_edits": 0,
             "product_smiles": Chem.MolToSmiles(plain),
             "product_mapped_smiles": Chem.MolToSmiles(m),
             "atom_id_map": dict(r.atom_id_map),
             "protocol_version": "v43-editproto-2"}
    ids = {idx: aid for aid, idx in r.atom_id_map.items()}
    diag = check_edit_against_donor(
        current={"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)},
        donor={"center_atom_ids": ["d1", "d2"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"d1": ids[1], "d2": ids[2]},
                   "equivalence_classes": [], "ref": "mimo-ez"},
        expectation={"target_smiles": synth["product_smiles"]},
        result=synth, edits=[])
    stereo = [c for c in diag.executed_bond_changes
              if c["kind"] == "bond_stereo_change"]
    rec("D5_true_EZ_change_still_detected", {
        "stereo_changes": stereo,
        "mismatch_count": len(diag.declaration_mismatches),
        "center": diag.reaction_center_match})


# ================================================================ E 快照/身份
def _f(key, value, **kw):
    return build_condition_fact(key=key, value=value,
                                status="known_present", **kw)


def _r(key, value):
    return build_requirement(key=key, value=value, level="essential",
                             source_refs=SRC)


def _historical_child():
    facts = [
        _f(CONDITION_KEY_OXYGEN, "aerobic", phase_id="p0",
           subject_scenario_ref="sA"),
        _f(CONDITION_KEY_OXYGEN, "anaerobic", phase_id="p1",
           subject_scenario_ref="sB")]
    parent = build_path_context(
        condition_facts=facts, phase_id="p0", scenario_ref="sA",
        accumulated_requirements=[_r(CONDITION_KEY_OXYGEN, "anaerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    return derive_child_context(
        parent, step_requirements=[_r(CONDITION_KEY_OXYGEN, "anaerobic")],
        scenario_transition={"new_phase_id": "p1",
                             "new_scenario_ref": "sB",
                             "source_ref": "user:synthetic_transition"})


def probe_snapshot():
    child = _historical_child()
    # 合法往返
    raw = child.to_dict()
    restored = PathContext.from_dict(raw)
    rec("E1_legal_roundtrip", {
        "same_id": restored.context_id == child.context_id,
        "idempotent": restored.to_dict() == raw,
        "route_fit": restored.route_assessment().environment_fit})
    # 摘要篡改
    raw2 = child.to_dict()
    raw2["phase_history"][0]["environment_fit"] = "compatible"
    try:
        PathContext.from_dict(raw2)
        rec("E2_summary_tamper", {"rejected": False})
    except ConditionContractError as e:
        rec("E2_summary_tamper", {"rejected": True,
                                  "kind": e.detail.get("kind"),
                                  "check": e.detail.get("check")})
    # 旗标篡改
    raw3 = child.to_dict()
    raw3["phase_history"][0]["has_gate_requirements"] = False
    try:
        PathContext.from_dict(raw3)
        rec("E3_flag_tamper", {"rejected": False})
    except ConditionContractError as e:
        rec("E3_flag_tamper", {"rejected": True,
                               "kind": e.detail.get("kind")})
    # 事实篡改保 id
    raw4 = child.to_dict()
    raw4["condition_facts"][0]["value"] = "anaerobic"
    try:
        PathContext.from_dict(raw4)
        rec("E4_fact_tamper", {"rejected": False})
    except ConditionContractError as e:
        rec("E4_fact_tamper", {"rejected": True,
                               "kind": e.detail.get("kind")})
    # 全部满足但 scope 空 ⇒ 合法 unknown 快照往返(不误拒)
    scopeless = build_path_context(
        condition_facts=[_f(CONDITION_KEY_OXYGEN, "aerobic")],
        accumulated_requirements=[_r(CONDITION_KEY_OXYGEN, "aerobic")],
        assessment_scope=[])
    child2 = derive_child_context(
        scopeless, scenario_transition={"new_phase_id": "p1",
                                        "source_ref": "user:t"})
    snap = child2.phase_history[0]
    try:
        back = PathContext.from_dict(child2.to_dict())
        rec("E5_scopeless_unknown_snapshot_legal", {
            "fit": snap.get("environment_fit"),
            "roundtrip_ok": back.context_id == child2.context_id})
    except ConditionContractError as e:
        rec("E5_scopeless_unknown_snapshot_legal", {
            "fit": snap.get("environment_fit"),
            "rejected": str(e)[:120]})


# ================================================================ F 披露
def probe_disclosure():
    ox = _oxidation_evidence()
    s = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    h = _hyp(s, [(ETHANOL, 1)], [(ACETALDEHYDE, 1), (HYDROGEN, 1)],
             group="mimo-f")
    audit = audit_hypothesis(
        h, states={x.state_id: x for x in s.values()},
        context=_aerobic_context(), center_evidence=ox)
    c = _center(audit)
    rec("F1_disclosure", {
        "payload_proof_scope": ox.get("proof_scope"),
        "payload_basis": ox.get("center_match_basis"),
        "detail_proof_scope": c.detail.get("proof_scope"),
        "detail_basis": c.detail.get("center_match_basis"),
        "basis_in_reason": "basis=direct" in c.reason_code,
        "empty_basis_tail": c.reason_code.rstrip().endswith("basis="),
        "coverage_keys": sorted(
            k for k in ("coverage_rule", "substrate_scale", "atom_delta",
                        "uncovered_reactant_elements",
                        "uncovered_product_elements",
                        "coverage_violations") if k in c.detail)})


# ================================================================ G 环轴
def probe_cycle():
    def dep(stmt):
        return build_dependency(kind="cosubstrate_supply", statement=stmt)

    a, b = dep("supplies:A:B"), dep("supplies:B:A")
    regen_a = resolve_dependency(a, new_evidence=["src:ra"],
                                 resolution="supported",
                                 support_axis="regeneration")
    regen_b = resolve_dependency(b, new_evidence=["src:rb"],
                                 resolution="supported",
                                 support_axis="regeneration")
    initial = resolve_dependency(regen_a, new_evidence=["src:i"],
                                 resolution="supported",
                                 support_axis="initial_supply")
    reaction_no = resolve_dependency(initial, new_evidence=["src:x"],
                                     resolution="contradicted",
                                     support_axis="reaction")
    later = resolve_dependency(initial, new_evidence=["src:l"],
                               resolution="contradicted",
                               support_axis="initial_supply")
    later_regen = resolve_dependency(later, new_evidence=["src:lr"],
                                     resolution="supported",
                                     support_axis="regeneration")
    # 初始 supported + reaction contradicted
    r1 = detect_circular_dependencies([reaction_no, regen_b])
    rec("G1_initial_ok_reaction_contradicted", {
        "unresolved": r1["unresolved_initial_supply"],
        "unsupported": r1["unsupported_relation_cycles"]})
    # initial contradicted + regeneration supported
    r2 = detect_circular_dependencies([later_regen, regen_b])
    rec("G2_initial_contradicted_regen_supported", {
        "unresolved": r2["unresolved_initial_supply"],
        "unsupported": r2["unsupported_relation_cycles"]})
    # 双支持正控制
    r3 = detect_circular_dependencies([initial, regen_b])
    rec("G3_double_supported_control", {
        "unresolved": r3["unresolved_initial_supply"],
        "unsupported": r3["unsupported_relation_cycles"]})
    # 保守门:regeneration 被反驳 + reaction supported ⇒ 关系不成立
    regen_no = resolve_dependency(initial, new_evidence=["src:rn"],
                                  resolution="contradicted",
                                  support_axis="regeneration")
    r4 = detect_circular_dependencies([regen_no, regen_b])
    rec("G4_regen_contradicted_conservative_gate", {
        "unresolved": r4["unresolved_initial_supply"],
        "unsupported": r4["unsupported_relation_cycles"]})


# ================================================================ 3b baseline
def probe_3b():
    from pathway_v43.pollutant.audit import _simulate_declared_edits
    r = render("C/C=C/C", name="U")
    ids = {idx: aid for aid, idx in r.atom_id_map.items()}
    edits = [{"op": "break_bond", "atom1": ids[0], "atom2": ids[1]}]
    ex = execute_edits(r, edits)
    after = Chem.MolFromSmiles(ex["product_mapped_smiles"])
    actual = [str(bd.GetStereo()) for bd in after.GetBonds()
              if bd.GetBondType() == Chem.BondType.DOUBLE]
    before = Chem.MolFromSmiles(r.smiles)
    mirror, fails = _simulate_declared_edits(
        before, edits, dict(r.atom_id_map), dict(r.atom_id_map))
    mirror_st = ([str(bd.GetStereo()) for bd in mirror.GetBonds()
                  if bd.GetBondType() == Chem.BondType.DOUBLE]
                 if mirror is not None else None)
    n = len(ids)
    diag = check_edit_against_donor(
        current={"smiles": r.smiles, "atom_id_map": dict(r.atom_id_map)},
        donor={"center_atom_ids": [f"d{i}" for i in range(n)]},
        alignment={"status": "resolved",
                   "donor_to_current": {f"d{i}": ids[i]
                                        for i in range(n)},
                   "equivalence_classes": [], "ref": "mimo-3b"},
        expectation={"target_smiles": ex["product_smiles"]},
        result=ex, edits=edits)
    rec("H_3b_mirror_terminal", {
        "product": ex["product_smiles"],
        "actual_reparsed_double_stereo": actual,
        "mirror_terminal_double_stereo": mirror_st,
        "mirror_failures": fails,
        "declaration_mismatches": diag.declaration_mismatches,
        "center": diag.reaction_center_match,
        "strict": diag.strict_target_match})


def main():
    probe_3b()
    probe_coverage()
    if not BASELINE:
        probe_cx()
        probe_absent()
        probe_mirror()
        probe_snapshot()
        probe_disclosure()
        probe_cycle()
    out = os.environ.get("PROBE_OUT", "mimo_r6_probe_out.json")
    with open(out, "w") as fh:
        json.dump(OUT, fh, ensure_ascii=False, indent=1, default=str)
    print(f"PROBE_DONE baseline={BASELINE} n={len(OUT)} -> {out}")


if __name__ == "__main__":
    main()
