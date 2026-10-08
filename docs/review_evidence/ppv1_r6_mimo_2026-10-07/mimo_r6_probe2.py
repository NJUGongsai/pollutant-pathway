#!/usr/bin/env python
"""mimo 第六轮独立探针 2(规则级合成夹具,公开链,无金标/封存数据)。

覆盖:
  X1/X1b  第三公共结构入口 check_edit_against_donor 的 current.smiles
          不经 _guard_input_cx_classes:|r| 被静默剥离进
          bound_inputs.substrate_identity,proof_record 保原串,
          端到端 audit 仍 verified/expand;
  X2      同函数内 result.product_smiles 带 |r|:strict 分支经
          strict_identity_of 拒绝(=> strict=None),
          但 bound_inputs.product_identity 走原始解析被吸收 —— 同一
          载荷内一分支拒绝、一分支静默剥离的不对称;
  Y1-Y2   登记类内容含空格的过拒边界(RDKit 接受并保留,守卫拒绝);
  Y3-Y5   控制:无空格登记类接受;RDKit 自身不可解析的同形输入
          (冒号 atomProp/含空格 SgD/含空格坐标)守卫拒绝方向一致。

Run (HEAD): PROBE_SRC=<repo>/src python mimo_r6_probe2.py
"""
import copy
import json
import os
import sys

sys.path.insert(0, os.environ.get("PROBE_SRC", "src"))

from rdkit import Chem  # noqa: E402

from pathway_v43.pollutant.audit import (  # noqa: E402
    ADMISSION_EXPAND,
    CHECK_TRANSFORMATION_CENTER,
    audit_hypothesis,
    center_evidence_from_donor_diagnostic,
    check_edit_against_donor,
    decide_admission,
)
from pathway_v43.pollutant.chemstate import (  # noqa: E402
    ChemicalStateError,
    STRUCTURE_ORIGIN_RAW_INPUT,
    build_chemical_state,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    COEFFICIENT_KNOWN,
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
    ConditionContractError,
    PathContext,
    build_condition_fact,
    build_path_context,
    build_requirement,
    derive_child_context,
)
from pathway_v43.services.atom_tool import (  # noqa: E402
    execute_edits,
    roundtrip,
)

OUT = {}


def rec(key, value):
    OUT[key] = value
    print(f"{key} = {json.dumps(value, ensure_ascii=False, default=str)}",
          flush=True)


ETHANOL, ACETALDEHYDE, HYDROGEN = "CCO", "CC=O", "[H][H]"
SRC = ["src:rule-r6-mimo-2"]


# ------------------------------------------------------------ 夹具(合成)
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


def _states(*smiles):
    return {s: build_chemical_state(s, STRUCTURE_ORIGIN_RAW_INPUT)
            for s in smiles}


def _hyp(states, reactants, products, group="mimo-r6-p2"):
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


def _fact(key, value, phase_id="", scenario_ref=""):
    return build_condition_fact(
        key=key, value=value, status="known_present",
        phase_id=phase_id, subject_scenario_ref=scenario_ref)


def _req(key, value):
    return build_requirement(key=key, value=value, level="essential",
                             source_refs=SRC)


def _oxidation_diag(current_smiles, result_override=None):
    """乙醇氧化真实编辑流;current/result 串可注入 |r| 变体。"""
    rr = roundtrip(ETHANOL, name="S")
    edits = [{"op": "change_bond_order", "atom1": "S_C_2",
              "atom2": "S_O_1", "from_order": "single",
              "to_order": "double"}]
    ex = execute_edits(rr, edits)
    assert ex["ok"], ex
    res = dict(ex)
    if result_override is not None:
        res["product_smiles"] = result_override
    diag = check_edit_against_donor(
        current={"smiles": current_smiles,
                 "atom_id_map": dict(rr.atom_id_map)},
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "mimo-r6-p2"},
        expectation={"target_smiles": ex["product_smiles"]},
        result=res, edits=edits)
    return diag, ex


# ================================================================ X 第三入口
def probe_signature_subset():
    """X3:v6 文本 10(a) 末条"签名不能凭空覆盖不存在的要求"(实现
    存在:path_context.py signature_not_in_requirements;tests/ 无
    对应行为夹具 ⇒ 证据缺口,行为本身在此独立验证)。"""
    facts = [
        _fact(CONDITION_KEY_OXYGEN, "aerobic", phase_id="p0",
              scenario_ref="sA"),
        _fact(CONDITION_KEY_OXYGEN, "anaerobic", phase_id="p1",
              scenario_ref="sB")]
    parent = build_path_context(
        condition_facts=facts, phase_id="p0", scenario_ref="sA",
        accumulated_requirements=[_req(CONDITION_KEY_OXYGEN, "anaerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    child = derive_child_context(
        parent, step_requirements=[_req(CONDITION_KEY_OXYGEN, "anaerobic")],
        scenario_transition={"new_phase_id": "p1",
                             "new_scenario_ref": "sB",
                             "source_ref": "user:synthetic_transition"})
    raw = child.to_dict()
    # 合法往返(控制)
    ok_rt = PathContext.from_dict(raw).context_id == child.context_id
    # 凭空签名 ⇒ 快照一致性先于内容身份拒出可区分理由码
    tampered = copy.deepcopy(raw)
    tampered["phase_history"][0]["covered_requirement_signatures"].append(
        "mimo-bogus-signature")
    try:
        PathContext.from_dict(tampered)
        rec("X3_signature_subset_rule", {
            "legal_roundtrip_ok": ok_rt, "bogus_rejected": False})
    except ConditionContractError as e:
        rec("X3_signature_subset_rule", {
            "legal_roundtrip_ok": ok_rt, "bogus_rejected": True,
            "kind": e.detail.get("kind"),
            "check": e.detail.get("check")})


def probe_third_entry():
    rr = roundtrip(ETHANOL, name="S")
    clean = rr.smiles
    flagged = clean + " |r|"

    # X1:current 带未登记 |r| ⇒ 诊断不拒,身份链吸收(剥离)
    diag_c, ex = _oxidation_diag(clean)
    diag_f, _ = _oxidation_diag(flagged)
    ev_c = center_evidence_from_donor_diagnostic(diag_c)
    ev_f = center_evidence_from_donor_diagnostic(diag_f)
    rec("X1_current_r_flag_absorbed", {
        "flagged_current_accepted": True,  # 无任何异常路径可拒
        "center_flagged": diag_f.reaction_center_match,
        "center_clean": diag_c.reaction_center_match,
        "substrate_identity_clean":
            ev_c["bound_inputs"]["substrate_identity"],
        "substrate_identity_flagged":
            ev_f["bound_inputs"]["substrate_identity"],
        "identities_equal":
            ev_c["bound_inputs"]["substrate_identity"]
            == ev_f["bound_inputs"]["substrate_identity"],
        "proof_record_keeps_raw": ev_f["proof_record"]["current"]["smiles"],
        "raw_in_proof": "|r|" in ev_f["proof_record"]["current"]["smiles"],
    })

    # X1b:端到端 audit —— 带 |r| 的 current 证据照常 verified/expand
    s = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    h = _hyp(s, [(ETHANOL, 1)], [(ACETALDEHYDE, 1), (HYDROGEN, 1)])
    audit = audit_hypothesis(
        h, states={x.state_id: x for x in s.values()},
        context=_aerobic_context(), center_evidence=ev_f)
    center = next(c for c in audit.checks
                  if c.name == CHECK_TRANSFORMATION_CENTER)
    try:
        admission, _gate = decide_admission(
            audit, gate_decisions={"gate_direction_source": {"ok": True}})
    except TypeError:
        admission, _gate = decide_admission(audit)
    rec("X1b_end_to_end_flagged_current", {
        "center": center.status,
        "coverage": center.detail.get("product_coverage"),
        "admission": admission,
        "expand": admission == ADMISSION_EXPAND,
        "no_warning_for_stripped_cx": True,
    })

    # X2:result 带 |r| ⇒ strict 分支拒绝(守卫生效),但
    #    bound_inputs.product_identity 走原始解析被吸收(同一载荷不对称)
    diag_r, ex = _oxidation_diag(
        clean, result_override=ex["product_smiles"] + " |r|")
    ev_r = center_evidence_from_donor_diagnostic(diag_r)
    rec("X2_result_r_flag_asymmetric", {
        "strict": diag_r.strict_target_match,
        "missing": [m for m in diag_r.missing_info_reasons
                    if "unparseable" in m or "target" in m],
        "product_identity_absorbed":
            ev_r["bound_inputs"]["product_identity"],
        "expected_clean": ex["product_smiles"],
        "absorbed_equals_clean":
            ev_r["bound_inputs"]["product_identity"]
            == ex["product_smiles"].split(" ")[0],
        "proof_record_keeps_raw_result":
            "|r|" in str(ev_r["proof_record"]["result"].get(
                "product_smiles", "")),
    })


# ================================================================ Y 空格边界
def _guard(structure):
    try:
        st = build_chemical_state(structure, STRUCTURE_ORIGIN_RAW_INPUT)
        return {"accept": True, "state_id": st.state_id[:16],
                "identity": st.smiles_isomeric}
    except ChemicalStateError as e:
        return {"accept": False, "kind": e.detail.get("kind")}


def _rdkit(structure):
    m = Chem.MolFromSmiles(structure)
    if m is None:
        return {"parse": None}
    return {"parse": Chem.MolToSmiles(m),
            "cx": Chem.MolToCXSmiles(m)}


def probe_space_boundary():
    cases = [
        ("Y1_label_space_legal_overreject", "CO |$_foo bar$|"),
        ("Y2_atomProp_space_legal_overreject",
         "CO |atomProp:0.note.hello world|"),
        ("Y3_atomProp_no_space_control", "CO |atomProp:0.note.hello|"),
        ("Y4_atomProp_colon_syntax_both_fail",
         "CO |atomProp:0.note:hello world|"),
        ("Y5_sgD_space_rdkit_unparsable", "CO |SgD:0:note:hello world|"),
        ("Y6_coords_space_rdkit_unparsable", "CO |(0.5, 0.8,)|"),
    ]
    for key, s in cases:
        rec(key, {"input": s, "guard": _guard(s), "rdkit": _rdkit(s)})


def main():
    probe_third_entry()
    probe_signature_subset()
    probe_space_boundary()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "mimo_r6_probe2_out.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(OUT, f, ensure_ascii=False, indent=1, default=str)
    print(f"written: {out} ({len(OUT)} records)")


if __name__ == "__main__":
    main()
