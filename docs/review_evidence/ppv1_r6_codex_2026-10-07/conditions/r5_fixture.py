"""R5 read-only synthetic condition/axis review, HEAD 293bc627.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python -B probe.py
"""
import copy
import json
from pathlib import Path
from pathway_v43.pollutant.path_context import (
    PathContext, Requirement, build_condition_fact as fact, build_requirement as req,
    build_path_context as ctx, derive_child_context as child,
    assess_candidate_conditions as assess, aggregate_environment_fit as aggregate,
    build_dependency, resolve_dependency as resolve, detect_circular_dependencies as circular,
)
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis
from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission, check_edit_against_donor, center_evidence_from_donor_diagnostic
from pathway_v43.services.atom_tool import roundtrip, execute_edits

OUT={}
def capture(name,fn):
    try: OUT[name]={"completed":True,"result":fn()}
    except Exception as e: OUT[name]={"completed":False,"error_type":type(e).__name__,"message":str(e),"detail":getattr(e,"detail",None)}
def f(key,value,**kw): return fact(key=key,value=value,status="known_present",**kw)
def r(key,value,**kw): return req(key=key,value=value,level="essential",source_refs=["src:synthetic_rule"],**kw)
states={s:build_chemical_state(s,"raw_input") for s in ("CCO","CC=O","[H][H]")}
state_map={s.state_id:s for s in states.values()}
render=roundtrip("CCO",name="S")
edits=[{"op":"change_bond_order","atom1":"S_C_2","atom2":"S_O_1","from_order":"single","to_order":"double"}]
execution=execute_edits(render,edits)
assert execution["ok"]
diag=check_edit_against_donor(current={"smiles":render.smiles,"atom_id_map":dict(render.atom_id_map)},
    donor={"center_atom_ids":["dC","dO"]},
    alignment={"status":"resolved","donor_to_current":{"dC":"S_C_2","dO":"S_O_1"},"equivalence_classes":[],"ref":"synthetic:alignment"},
    expectation={"target_smiles":execution["product_smiles"]},result=execution,edits=edits)
center=center_evidence_from_donor_diagnostic(diag)
def h(requirements=None):
    return build_hypothesis(parent_path_id="synthetic:parent",substrate_state_ref=states["CCO"].state_id,
        participants=[Participant(state_ref=states[s].state_id,side=side,role=role,coefficient=1,coefficient_status="known")
          for s,side,role in (("CCO","reactant","primary_substrate"),("CC=O","product","principal_product"),("[H][H]","product","coproduct"))],
        participant_list_status="declared_complete",step_scope="net_reaction",origin_group_key="synthetic:r5",
        requirements=requirements or [])
def audit(hyp,context):
    a=audit_hypothesis(hyp,states=state_map,context=context,center_evidence=center)
    return {"input_hash":a.input_hash,"checks":{c.name:{"status":c.status,"reason":c.reason_code,"detail":c.detail} for c in a.checks},"admission":decide_admission(a)}
def view(c,hyp):
    return {"context_id":c.context_id,"route":c.route_assessment().to_dict(),"current":c.current_step_assessment().to_dict(),
        "candidate":assess(c,hyp).to_dict(),"audit":audit(hyp,c)}
normal_h=h([r("oxygen_regime","aerobic").to_dict()])
normal_c=ctx(condition_facts=[f("oxygen_regime","aerobic")],assessment_scope=["oxygen_regime"])
capture("baseline_R6",lambda:view(normal_c,normal_h))

def unit_controls():
    out={}
    for unit in ("","C","°C","K"):
        c=ctx(condition_facts=[f("temperature_C",25,unit=unit,origin="curated_source",source_ref="src:synthetic_source",subject_scenario_ref="s")],scenario_ref="s",assessment_scope=["temperature_C"])
        out[unit or "missing"]=view(c,h([r("temperature_C",{"lo":20,"hi":30}).to_dict()]))
    out["dimensionless_pH"]=view(ctx(condition_facts=[f("pH",7)],assessment_scope=["pH"]),h([r("pH",{"lo":6,"hi":8}).to_dict()]))
    return out
capture("units_positive_negative",unit_controls)

def absent_enum():
    out={}
    for key,value,unit in (("oxygen_regime","aerobic",""),("matrix","soil",""),("temperature_C",25,"C")):
        a=fact(key=key,value=value,unit=unit,status="known_absent",source_ref="src:synthetic_absence")
        reqvalue={"lo":20,"hi":30} if key=="temperature_C" else value
        c=ctx(condition_facts=[a],assessment_scope=[key])
        out[key]=view(c,h([r(key,reqvalue).to_dict()]))
    return out
capture("known_absent_non_species_false_satisfied",absent_enum)
capture("known_absent_species_negative_control",lambda:aggregate(
    facts=[fact(key="electron_donor",value="NADH",status="known_absent")],
    requirements=[r("electron_donor","NADH")],declared_scope=["electron_donor"]).to_dict())

def historical_child(old_required="anaerobic"):
    facts=[f("oxygen_regime","aerobic",phase_id="p0",subject_scenario_ref="sA"),
           f("oxygen_regime","anaerobic",phase_id="p1",subject_scenario_ref="sB")]
    p=ctx(condition_facts=facts,phase_id="p0",scenario_ref="sA",accumulated_requirements=[r("oxygen_regime",old_required)],assessment_scope=["oxygen_regime"])
    return child(p,step_requirements=[r("oxygen_regime","anaerobic")],
       scenario_transition={"new_phase_id":"p1","new_scenario_ref":"sB","source_ref":"user:synthetic_transition"})
def snapshot_summary_tamper():
    c=historical_child()
    hyp=h([r("oxygen_regime","anaerobic").to_dict()])
    before=view(c,hyp)
    raw=c.to_dict()
    raw["phase_history"][0]["environment_fit"]="compatible"
    restored=PathContext.from_dict(raw)
    after=view(restored,hyp)
    raw2=c.to_dict();raw2["phase_history"][0]["has_gate_requirements"]=False
    suppressed=view(PathContext.from_dict(raw2),hyp)
    return {"before":before,"summary_changed":after,"has_gate_false":suppressed,
        "same_context_id":c.context_id==restored.context_id,
        "original_snapshot":c.phase_history[0],"restored_snapshot":restored.phase_history[0]}
capture("snapshot_from_dict_conflict_summary_and_flag_tamper",snapshot_summary_tamper)

def axis_controls_and_diagnostic():
    a,b=[build_dependency(kind="cosubstrate_supply",statement=s) for s in ("supplies:A:B","supplies:B:A")]
    regen_a=resolve(a,new_evidence=["src:regen"],resolution="supported",support_axis="regeneration")
    regen_b=resolve(b,new_evidence=["src:regen_b"],resolution="supported",support_axis="regeneration")
    initial=resolve(regen_a,new_evidence=["src:initial"],resolution="supported",support_axis="initial_supply")
    initial_no=resolve(initial,new_evidence=["src:initial_no"],resolution="contradicted",support_axis="initial_supply")
    later=resolve(initial_no,new_evidence=["src:later_regen"],resolution="supported",support_axis="regeneration")
    restored=resolve(later,new_evidence=["src:new_initial"],resolution="supported",support_axis="initial_supply")
    reaction_no=resolve(initial,new_evidence=["src:reaction_no"],resolution="contradicted",support_axis="reaction")
    out={}
    for name,d in (("regen_only",regen_a),("initial_supported",initial),("initial_contradicted_later_regen",later),("initial_restored",restored),("initial_supported_reaction_contradicted",reaction_no)):
        c=ctx(condition_facts=[f("oxygen_regime","aerobic")],assessment_scope=["oxygen_regime"],dependencies=[d,regen_b])
        out[name]={"dependency":d.to_dict(),"axis_states":c.dependency_states(),"circular":circular([d,regen_b]),"audit":audit(normal_h,c)}
    return out
capture("axis_controls_and_cross_axis_diagnostic",axis_controls_and_diagnostic)

def freeze_controls():
    c=ctx(condition_facts=[f("temperature_C",25,unit="C")],accumulated_requirements=[r("temperature_C",{"lo":40,"hi":50})],assessment_scope=["temperature_C"])
    before=c.to_dict();v=c.accumulated_requirements[0].value
    try: v |= {"lo":20,"hi":30};error=None
    except Exception as e:error=type(e).__name__
    hyp=h([r("temperature_C",{"lo":40,"hi":50}).to_dict()]);before_h=hyp.to_dict()
    try:hyp.requirements[0]["value"].update(lo=20,hi=30);error_h=None
    except Exception as e:error_h=type(e).__name__
    return {"ior_error":error,"unchanged_context":c.to_dict()==before,"hyp_update_error":error_h,"unchanged_hypothesis":hyp.to_dict()==before_h}
capture("frozen_normal_mutations_fixed",freeze_controls)

Path(__file__).with_name("results.json").write_text(json.dumps(OUT,ensure_ascii=False,sort_keys=True,indent=2))
print(json.dumps({k:{"completed":v["completed"],"error_type":v.get("error_type")} for k,v in OUT.items()},ensure_ascii=False,indent=2))
