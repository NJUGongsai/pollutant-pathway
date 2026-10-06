"""R4 红验证:对审核基线 af14fb2 断言 v4 预期行为,应逐项失败。"""
import sys
sys.path.insert(0, "/private/tmp/ppv1-r4-red.FnjuTR/src")
from pathway_v43.pollutant.chemstate import build_chemical_state, strict_identity_of, STRUCTURE_ORIGIN_RAW_INPUT
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission, check_edit_against_donor, center_evidence_from_donor_diagnostic
from pathway_v43.pollutant.hypothesis import build_hypothesis, Participant, PARTICIPANT_LIST_DECLARED_COMPLETE, COEFFICIENT_KNOWN
from pathway_v43.services.atom_tool import roundtrip, execute_edits

results = []
def check(name, fn):
    try:
        fn()
        results.append((name, "PASS(意外!基线已满足 v4 预期)"))
    except AssertionError:
        results.append((name, "FAIL(基线缺陷仍在,红 ✓)"))
    except Exception as e:
        results.append((name, f"ERROR({type(e).__name__},红 ✓)"))

# R3-04: 非化学 CX 元数据不入身份
def t1():
    ids = {strict_identity_of(s) for s in
           ["CO", "CO |$|", "CO |(0,0,1,0)|", "CO |atomProp:0.note.hello|"]}
    assert len(ids) == 1
check("R3-04 非化学 CX 元数据同键", t1)

# R3-04: 混合 ABS 归一
def t2():
    assert strict_identity_of("C[C@H](Cl)[C@H](F)Cl |a:1,&1:3|") ==         strict_identity_of("C[C@H](Cl)[C@H](F)Cl |&1:3|")
check("R3-04 混合 ABS 归一", t2)

# R3-02: 手性盲联合映射(meso 换位)
def t3():
    render = roundtrip("C[C@H](Cl)[C@H](Cl)C", name="S")
    ex = execute_edits(render, [{"op": "break_bond", "atom1": "S_C_3_R", "atom2": "S_C_4"}])
    diag = check_edit_against_donor(
        current={"smiles": render.smiles, "atom_id_map": dict(render.atom_id_map)},
        donor={"center_atom_ids": ["dA", "dB"]},
        alignment={"status": "resolved", "donor_to_current": {"dA": "S_C_1", "dB": "S_C_2_S"},
                   "equivalence_classes": [], "ref": "r"},
        expectation={"target_smiles": ex["product_smiles"]}, result=ex,
        edits=[{"op": "break_bond", "atom1": "S_C_3_R", "atom2": "S_C_4"}])
    assert diag.reaction_center_match is not True
check("R3-02 手性盲联合映射不判 True", t3)

# R3-03: CIP 优先级重排非构型变化
def t4():
    render = roundtrip("CCC[C@H](O)CC", name="S")
    ex = execute_edits(render, [{"op": "change_bond_order", "atom1": "S_C_5", "atom2": "S_C_6",
                                 "from_order": "single", "to_order": "double"}])
    diag = check_edit_against_donor(
        current={"smiles": render.smiles, "atom_id_map": dict(render.atom_id_map)},
        donor={"center_atom_ids": ["dA", "dB"]},
        alignment={"status": "resolved", "donor_to_current": {"dA": "S_C_5", "dB": "S_C_6"},
                   "equivalence_classes": [], "ref": "r"},
        expectation={"target_smiles": ex["product_smiles"]}, result=ex,
        edits=[{"op": "change_bond_order", "atom1": "S_C_5", "atom2": "S_C_6",
                "from_order": "single", "to_order": "double"}])
    assert diag.reaction_center_match is True
check("R3-03 优先级重排不误报构型变化", t4)

# R3-05: add_atom 隐含锚键
def t5():
    render = roundtrip("C", name="A")
    edits = [{"op": "add_atom", "atom1": "A_C_1", "element": "O", "new_atom_id": "A_O_1"}]
    ex = execute_edits(render, edits)
    diag = check_edit_against_donor(
        current={"smiles": render.smiles, "atom_id_map": dict(render.atom_id_map)},
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved", "donor_to_current": {"dC": "A_C_1", "dO": "A_O_1"},
                   "equivalence_classes": [], "ref": "r"},
        expectation={"target_smiles": ex["product_smiles"]}, result=ex, edits=edits)
    assert diag.declaration_mismatches == []
check("R3-05 add_atom 隐含锚键不误报失配", t5)

# R3-05: 有序操作净效应
def t6():
    render = roundtrip("CCO", name="S")
    edits = [{"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1",
              "from_order": "single", "to_order": "double"},
             {"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1",
              "from_order": "double", "to_order": "single"},
             {"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1",
              "from_order": "single", "to_order": "double"}]
    ex = execute_edits(render, edits)
    diag = check_edit_against_donor(
        current={"smiles": render.smiles, "atom_id_map": dict(render.atom_id_map)},
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved", "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "r"},
        expectation={"target_smiles": ex["product_smiles"]}, result=ex, edits=edits)
    assert diag.declaration_mismatches == []
check("R3-05 有序操作净效应不误报失配", t6)

# R3-01: 跨反应证据复用拒绝(审核 admission_binding 场景)
def t7():
    render = roundtrip("CCO", name="S")
    edits = [{"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1",
              "from_order": "single", "to_order": "double"}]
    ex = execute_edits(render, edits)
    diag = check_edit_against_donor(
        current={"smiles": render.smiles, "atom_id_map": dict(render.atom_id_map)},
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved", "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "r"},
        expectation={"target_smiles": ex["product_smiles"]}, result=ex, edits=edits)
    # 乙酸假设(不同反应)用乙醛诊断证据:不得 expand
    ev = center_evidence_from_donor_diagnostic(diag)
    states = {s: build_chemical_state(s, "source_product")
              for s in ("CCO", "O=O", "CC(=O)O", "O")}
    sub = states["CCO"]
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[Participant(state_ref=sub.state_id, side="reactant", role="primary_substrate",
                                  coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
                      Participant(state_ref=states["O=O"].state_id, side="reactant", role="cosubstrate",
                                  coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
                      Participant(state_ref=states["CC(=O)O"].state_id, side="product", role="principal_product",
                                  coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
                      Participant(state_ref=states["O"].state_id, side="product", role="coproduct",
                                  coefficient=1, coefficient_status=COEFFICIENT_KNOWN)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="red4")
    from pathway_v43.pollutant.path_context import build_path_context, build_condition_fact, build_requirement, CONDITION_KEY_OXYGEN
    ctx = build_path_context(
        condition_facts=[build_condition_fact(key=CONDITION_KEY_OXYGEN, value="aerobic",
                                              status="known_present")],
        accumulated_requirements=[build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                                                    value="aerobic", source_refs=["src:1"])],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    audit = audit_hypothesis(hyp, states={s.state_id: s for s in states.values()},
                             context=ctx, center_evidence=ev)
    d, _ = decide_admission(audit, gate_decisions={"gate_direction_source": {"ok": True}})
    assert d != "expand"
check("R3-01 跨反应证据复用不 expand", t7)

# R3-01: 注册名-only 证据
def t8():
    states = {s: build_chemical_state(s, "source_product")
              for s in ("CCO", "CC=O", "[H][H]")}
    sub = states["CCO"]
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[Participant(state_ref=sub.state_id, side="reactant", role="primary_substrate",
                                  coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
                      Participant(state_ref=states["CC=O"].state_id, side="product", role="principal_product",
                                  coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
                      Participant(state_ref=states["[H][H]"].state_id, side="product", role="coproduct",
                                  coefficient=1, coefficient_status=COEFFICIENT_KNOWN)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="red4b")
    from pathway_v43.pollutant.path_context import build_path_context, build_condition_fact, build_requirement, CONDITION_KEY_OXYGEN
    ctx = build_path_context(
        condition_facts=[build_condition_fact(key=CONDITION_KEY_OXYGEN, value="aerobic",
                                              status="known_present")],
        accumulated_requirements=[build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                                                    value="aerobic", source_refs=["src:1"])],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    audit = audit_hypothesis(hyp, states={s.state_id: s for s in states.values()},
                             context=ctx,
                             center_evidence={"checker_version": "ppv1-donor-diagnostic-3",
                                              "center_match": True})
    d, _ = decide_admission(audit, gate_decisions={"gate_direction_source": {"ok": True}})
    assert d != "expand"
check("R3-01 注册名-only 证据不 expand", t8)

for name, res in results:
    print(f"{res:42} | {name}")
n_red = sum(1 for _, r in results if "红" in r)
print(f"红验证: {n_red}/{len(results)} 项在基线 af14fb2 上失败/报错")