"""红验证:对审核基线 0002f71 断言 v3 预期行为,应逐项失败。"""
import sys
sys.path.insert(0, "/private/tmp/ppv1-r3-red.10mlBj/src")
from pathway_v43.pollutant.chemstate import build_chemical_state, STRUCTURE_ORIGIN_RAW_INPUT
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission, check_edit_against_donor
from pathway_v43.pollutant.hypothesis import build_hypothesis, Participant, PARTICIPANT_LIST_DECLARED_COMPLETE, COEFFICIENT_KNOWN
from pathway_v43.pollutant.path_context import build_path_context, build_condition_fact, build_requirement, CONDITION_KEY_OXYGEN, FACT_STATUS_KNOWN_PRESENT, REQUESTED_SCOPE_CONDITION_COMPATIBLE
from pathway_v43.services.atom_tool import roundtrip, execute_edits

results = []
def check(name, fn):
    try:
        fn()
        results.append((name, "PASS(意外!基线已满足 v3 预期)"))
    except AssertionError:
        results.append((name, "FAIL(v2 基线缺陷仍在,红 ✓)"))
    except Exception as e:
        results.append((name, f"ERROR({type(e).__name__},红 ✓)"))

# R2-02: plain=ABS
def t1():
    a = build_chemical_state("F[C@H](Cl)Br", STRUCTURE_ORIGIN_RAW_INPUT)
    b = build_chemical_state("F[C@H](Cl)Br |a:1|", STRUCTURE_ORIGIN_RAW_INPUT)
    assert a.state_id == b.state_id
check("R2-02 plain=ABS 同身份", t1)

# R2-02: AND 整组反转
def t2():
    a = build_chemical_state("C[C@H](O)CC |&1:1|", STRUCTURE_ORIGIN_RAW_INPUT)
    b = build_chemical_state("C[C@@H](O)CC |&1:1|", STRUCTURE_ORIGIN_RAW_INPUT)
    assert a.state_id == b.state_id
check("R2-02 AND 整组反转同身份", t2)

# R2-02: 公开表示往返
def t3():
    s = build_chemical_state("F[C@H](Cl)Br |&1:1|", STRUCTURE_ORIGIN_RAW_INPUT)
    r = build_chemical_state(s.smiles_isomeric, STRUCTURE_ORIGIN_RAW_INPUT)
    assert r.state_id == s.state_id
check("R2-02 公开表示往返重建同 id", t3)

# R2-01: 零净变化不为 True
def t4():
    render = roundtrip("CCO", name="S")
    edits = [{"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1",
              "from_order": "single", "to_order": "single"}]
    ex = execute_edits(render, edits)
    diag = check_edit_against_donor(
        current={"smiles": render.smiles, "atom_id_map": dict(render.atom_id_map)},
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved", "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "z"},
        expectation={"target_smiles": ex["product_smiles"]},
        result=ex, edits=edits)
    assert diag.reaction_center_match is not True
check("R2-03 零净变化不判 True", t4)

# R2-01: 缺 context 不进 R6
ETHANOL, O2, ACETIC, WATER = "CCO", "O=O", "CC(=O)O", "O"
def _st(s):
    return build_chemical_state(s, "source_product")
def t5():
    states = {s: _st(s) for s in (ETHANOL, O2, ACETIC, WATER)}
    sub = states[ETHANOL]
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[
            Participant(state_ref=sub.state_id, side="reactant", role="primary_substrate",
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            Participant(state_ref=states[O2].state_id, side="reactant", role="cosubstrate",
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            Participant(state_ref=states[ACETIC].state_id, side="product", role="principal_product",
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            Participant(state_ref=states[WATER].state_id, side="product", role="coproduct",
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="red")
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=hyp.participants,
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="red",
        transformation_signature_status="verified")  # 复审场景:自报签名
    audit = audit_hypothesis(hyp, states={s.state_id: s for s in states.values()}, context=None)
    d, _ = decide_admission(audit)
    assert d != "expand"
check("R2-01 缺 context+自报签名 不 expand", t5)

# R2-01: 窄 scope 不进 R6
def t6():
    states = {s: _st(s) for s in (ETHANOL, O2, ACETIC, WATER)}
    sub = states[ETHANOL]
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[
            Participant(state_ref=sub.state_id, side="reactant", role="primary_substrate",
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            Participant(state_ref=states[O2].state_id, side="reactant", role="cosubstrate",
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            Participant(state_ref=states[ACETIC].state_id, side="product", role="principal_product",
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            Participant(state_ref=states[WATER].state_id, side="product", role="coproduct",
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="red")
    audit = audit_hypothesis(hyp, states={s.state_id: s for s in states.values()},
                             context=None, audit_scope={"structure_parse_valence"})
    d, _ = decide_admission(audit)
    assert d != "expand"
check("R2-01 窄 scope 不 expand", t6)

# R2-12: 逐产物拒绝被消费
def t7():
    states = {s: _st(s) for s in (ETHANOL, O2, ACETIC, WATER)}
    sub = states[ETHANOL]
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[
            Participant(state_ref=sub.state_id, side="reactant", role="primary_substrate",
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            Participant(state_ref=states[O2].state_id, side="reactant", role="cosubstrate",
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            Participant(state_ref=states[ACETIC].state_id, side="product", role="principal_product",
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            Participant(state_ref=states[WATER].state_id, side="product", role="coproduct",
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="red",
        transformation_signature_status="verified")
    audit = audit_hypothesis(hyp, states={s.state_id: s for s in states.values()}, context=None)
    d, _ = decide_admission(audit, gate_decisions={
        "per_product_verdicts": [
            {"position": 0, "accepted": False, "reasons": ["element_gate_rejected"]},
            {"position": 1, "accepted": False, "reasons": ["element_gate_rejected"]}]})
    assert d == "reject"
check("R2-12 全产物被拒 ⇒ reject", t7)

# R2-03: 联合中心对称反例
def t8():
    render = roundtrip("C1CCCCC1", name="S")
    edits = [{"op": "form_bond", "atom1": "S_C_1", "atom2": "S_C_4"}]
    ex = execute_edits(render, edits)
    diag = check_edit_against_donor(
        current={"smiles": render.smiles, "atom_id_map": dict(render.atom_id_map)},
        donor={"center_atom_ids": ["dA", "dB"]},
        alignment={"status": "resolved", "donor_to_current": {"dA": "S_C_1", "dB": "S_C_2"},
                   # 复审场景:六个碳各自同轨道(合法等价类,全同 canonical rank)
                   "equivalence_classes": [["S_C_1", "S_C_2", "S_C_3", "S_C_4", "S_C_5", "S_C_6"]],
                   "ref": "c"},
        expectation={"target_smiles": ex["product_smiles"]},
        result=ex, edits=edits)
    assert diag.reaction_center_match is not True
check("R2-03 联合对称反例(含轨道类)不判 True", t8)

for name, res in results:
    print(f"{res:45} | {name}")
n_red = sum(1 for _, r in results if "红" in r)
print(f"\n红验证: {n_red}/{len(results)} 项在基线 0002f71 上失败/报错(预期全部非 PASS)")
