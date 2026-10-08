"""Read-only synthetic S0-S2 R4 review. No assets/models; bytecode disabled.
Run: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python probe.py
"""
import ast
import copy
import json
import tempfile
from pathlib import Path

from pathway_v43.pollutant.path_context import (
    Requirement, PathContext, build_condition_fact as fact,
    build_requirement as req, build_path_context as ctx,
    derive_child_context as child, assess_candidate_conditions as assess,
    aggregate_environment_fit as aggregate, build_dependency,
    resolve_dependency as resolve, detect_circular_dependencies as circular,
)
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis, recompute_hypothesis_id
from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission, check_edit_against_donor, center_evidence_from_donor_diagnostic
from pathway_v43.services.atom_tool import roundtrip, execute_edits
from pathway_v43.pollutant.store import PollutantPathwayStore

OUT={}
def capture(name, fn):
    try: OUT[name] = {"completed":True,"result":fn()}
    except Exception as e: OUT[name] = {"completed":False,"error_type":type(e).__name__,"message":str(e),"detail":getattr(e,"detail",None)}
def f(key,value,**kw): return fact(key=key,value=value,status="known_present",**kw)
def r(key,value,**kw): return req(key=key,value=value,level="essential",source_refs=["src:synthetic"],**kw)

states={s:build_chemical_state(s,"raw_input") for s in ("CCO","CC=O","[H][H]")}
state_map={s.state_id:s for s in states.values()}
render=roundtrip("CCO",name="S")
edits=[{"op":"change_bond_order","atom1":"S_C_2","atom2":"S_O_1","from_order":"single","to_order":"double"}]
execution=execute_edits(render,edits)
assert execution["ok"]
diagnostic=check_edit_against_donor(current={"smiles":render.smiles,"atom_id_map":dict(render.atom_id_map)},
    donor={"center_atom_ids":["dC","dO"]},
    alignment={"status":"resolved","donor_to_current":{"dC":"S_C_2","dO":"S_O_1"},"equivalence_classes":[],"ref":"synthetic:alignment"},
    expectation={"target_smiles":execution["product_smiles"]},result=execution,edits=edits)
center=center_evidence_from_donor_diagnostic(diagnostic)
assert center["center_match"] is True and center["strict_target_match"] is True
def h(requirements=None,deps=None):
    return build_hypothesis(parent_path_id="synthetic:parent",substrate_state_ref=states["CCO"].state_id,
        participants=[Participant(state_ref=states[s].state_id,side=side,role=role,coefficient=1,coefficient_status="known")
            for s,side,role in (("CCO","reactant","primary_substrate"),("CC=O","product","principal_product"),("[H][H]","product","coproduct"))],
        participant_list_status="declared_complete",step_scope="net_reaction",origin_group_key="synthetic:r4",
        requirements=requirements or [],dependency_refs=deps or [])
def audit(hyp,context,**kw):
    a=audit_hypothesis(hyp,states=state_map,context=context,center_evidence=center,**kw)
    return {"hypothesis_id":hyp.hypothesis_id,"input_hash":a.input_hash,
        "checks":{c.name:{"status":c.status,"reason":c.reason_code,"detail":c.detail} for c in a.checks},
        "admission":decide_admission(a)}
def view(c,hyp):
    a=assess(c,hyp)
    return {"route_helper":c.route_assessment().environment_fit,"current_helper":c.current_step_assessment().environment_fit,
        "candidate":a.to_dict(),"audit":audit(hyp,c)}
normal_h=h([r("oxygen_regime","aerobic").to_dict()])
normal_c=ctx(condition_facts=[f("oxygen_regime","aerobic")],assessment_scope=["oxygen_regime"])
capture("baseline_full_R6",lambda:audit(normal_h,normal_c))

def legacy_segmented():
    """Every old top-level statement captured. A rejected block is not a pass.
    Legacy center payload is obsolete v4; only check-specific old controls
    are compared; new probes above/below supply actual bound diagnostics.
    """
    p=Path("/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r3_codex_2026-10-06/conditions_probe.py")
    # The archived probe uses __file__.parent for synthetic SQLite. Keep all
    # writes in this scratch directory without altering the archived source.
    namespace={"__name__":"legacy_review","__file__":str(Path(__file__).with_name("legacy_probe_location.py"))}
    errors=[]
    for node in ast.parse(p.read_text()).body:
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=="print": continue
        try: exec(compile(ast.Module(body=[node],type_ignores=[]),str(p),"exec"),namespace)
        except Exception as e: errors.append({"line":node.lineno,"statement":type(node).__name__,"type":type(e).__name__,"message":str(e),"detail":getattr(e,"detail",None)})
    return {"results":namespace.get("OUT",{}),"caught_blocks":errors,"note":"No caught block is treated as passed; obsolete center evidence prevents legacy R6. Independently bound full-audit probes replace it."}
capture("old_R3_probe_segmented",legacy_segmented)

def phase_case(old_required,newphase):
    facts=[f("oxygen_regime","aerobic",phase_id="p0",subject_scenario_ref="sA"),
        f("oxygen_regime","anaerobic",phase_id="p0",subject_scenario_ref="sB"),
        f("oxygen_regime","anaerobic",phase_id="p1",subject_scenario_ref="sB")]
    p=ctx(condition_facts=facts,phase_id="p0",scenario_ref="sA",accumulated_requirements=[r("oxygen_regime",old_required)],assessment_scope=["oxygen_regime"])
    c=child(p,step_requirements=[r("oxygen_regime","anaerobic")],scenario_transition={"new_phase_id":newphase,"new_scenario_ref":"sB","source_ref":"user:synthetic_transition"})
    return view(c,h([r("oxygen_regime","anaerobic").to_dict()]))
capture("old_cross_scenario_conflict_fixed",lambda:phase_case("anaerobic","p1"))
capture("old_cross_scenario_satisfied_fixed",lambda:phase_case("aerobic","p1"))
capture("new_same_local_phase_different_scenario",lambda:phase_case("aerobic","p0"))

def unit_unknown():
    c=ctx(condition_facts=[f("temperature_C",25,origin="curated_source",source_ref="src:source_unit_unreported",subject_scenario_ref="s")],
        phase_id="p0",scenario_ref="s",assessment_scope=["temperature_C"])
    return view(c,h([r("temperature_C",{"lo":20,"hi":30}).to_dict()]))
capture("source_unit_unknown_still_R6",unit_unknown)

def orphan_empty_snapshot():
    p=ctx(condition_facts=[f("oxygen_regime","aerobic")],phase_id="p0",scenario_ref="s",assessment_scope=["oxygen_regime","pH"])
    foreign=Requirement(**{**r("pH",{"lo":6,"hi":8}).to_dict(),"introduced_phase_id":"p0","introduced_scenario_ref":"s","introduced_edge":"hyp:missing_older_edge"})
    c=child(p,step_requirements=[foreign],scenario_transition={"new_phase_id":"p1","source_ref":"user:synthetic_transition"},step_edge_ref="hyp:new")
    with_empty=view(c,normal_h)
    c.phase_history=[]
    without_empty=view(c,normal_h)
    return {"with_empty_snapshot":with_empty,"without_snapshot_control":without_empty}
capture("orphan_covered_by_empty_unrelated_snapshot",orphan_empty_snapshot)

def dependency_controls():
    dep=build_dependency(kind="supply",statement="synthetic:unresolved")
    solved=resolve(dep,new_evidence=["src:observed_supply"],resolution="supported",support_axis="initial_supply")
    bad=resolve(dep,new_evidence=["src:contradiction"],resolution="contradicted",support_axis="reaction")
    result={}
    for name,d in (("unresolved",dep),("supported",solved),("contradicted",bad)):
        c=ctx(condition_facts=[f("oxygen_regime","aerobic")],assessment_scope=["oxygen_regime"],dependencies=[d])
        for suffix,ids in (("infer",None),("explicit_empty",[]),("explicit_unresolved",[d.dependency_id])):
            result[name+"_"+suffix]=audit(normal_h,c,unresolved_dependency_ids=ids)
    for suffix,ids in (("infer",None),("explicit_empty",[]),("explicit_unresolved",[dep.dependency_id])):
        result["hyp_only_"+suffix]=audit(h([r("oxygen_regime","aerobic").to_dict()],deps=[dep.dependency_id]),normal_c,unresolved_dependency_ids=ids)
    return result
capture("dependency_explicit_inputs_fixed",dependency_controls)

def axis_contradiction():
    ds=[build_dependency(kind="cosubstrate_supply",statement=s) for s in ("supplies:A:B","supplies:B:A")]
    regen=[resolve(d,new_evidence=["src:regen"],resolution="supported",support_axis="regeneration") for d in ds]
    initial=resolve(regen[0],new_evidence=["src:startup"],resolution="supported",support_axis="initial_supply")
    initial_negated=resolve(initial,new_evidence=["src:startup_absent"],resolution="contradicted",support_axis="initial_supply")
    later_regen=resolve(initial_negated,new_evidence=["src:regen_again"],resolution="supported",support_axis="regeneration")
    c=ctx(condition_facts=[f("oxygen_regime","aerobic")],assessment_scope=["oxygen_regime"],dependencies=[later_regen,regen[1]])
    return {"regeneration_only":circular(regen),"initial_supported":circular([initial,regen[1]]),
        "initial_contradicted":circular([initial_negated,regen[1]]),"after_later_regeneration":circular([later_regen,regen[1]]),
        "dependency":later_regen.to_dict(),"audit":audit(normal_h,c)}
capture("contradicted_initial_axis_restored_by_regeneration",axis_contradiction)

def frozen_ior():
    p=ctx(condition_facts=[f("temperature_C",25,unit="C")],accumulated_requirements=[r("temperature_C",{"lo":40,"hi":50})],assessment_scope=["temperature_C"])
    a,b=child(p),child(p)
    hyp=h([])
    before=view(a,hyp); ident=a.context_id
    value_alias=a.accumulated_requirements[0].value
    value_alias |= {"lo":20,"hi":30}
    return {"before":before,"after":view(a,hyp),"same_context_id":ident==a.context_id,
        "parent_fit":p.route_assessment().environment_fit,"sibling_fit":b.route_assessment().environment_fit,
        "mutated_value":a.accumulated_requirements[0].to_dict()["value"]}
capture("frozen_value_dict_ior_bypass",frozen_ior)

def hypothesis_live_mutability():
    hh=h([r("temperature_C",{"lo":40,"hi":50}).to_dict()])
    c=ctx(condition_facts=[f("temperature_C",25,unit="C")],assessment_scope=["temperature_C"])
    before=audit(hh,c); ident=hh.hypothesis_id
    hh.requirements[0]["value"].update(lo=20,hi=30)
    return {"before":before,"after":audit(hh,c),"same_hypothesis_id":ident==hh.hypothesis_id,
        "recomputed_id":recompute_hypothesis_id(hh.to_dict()),"payload_id":hh.to_dict()["hypothesis_id"]}
capture("hypothesis_live_nested_mutation",hypothesis_live_mutability)

def constructor_and_order():
    q1=r("oxygen_regime","aerobic").to_dict();q2=r("pH",{"lo":6,"hi":8}).to_dict()
    ha,hb=h([q1,q2]),h([q2,q1])
    with tempfile.TemporaryDirectory(prefix="synthetic_store_",dir=Path(__file__).parent) as td:
        store=PollutantPathwayStore(Path(td)/"synthetic.sqlite")
        store.put_hypothesis(ha.to_dict());store.put_hypothesis(hb.to_dict());store.close()
    input_alias=r("temperature_C",{"lo":20,"hi":30}).to_dict();hc=h([input_alias]);input_alias["value"].update(lo=40,hi=50)
    return {"same_id":ha.hypothesis_id==hb.hypothesis_id,"same_payload":ha.to_dict()==hb.to_dict(),"two_puts":"accepted","caller_alias_isolated":hc.requirements[0]["value"]=={"lo":20,"hi":30}}
capture("constructor_order_alias_fixed",constructor_and_order)

for name,requirements in (("foreign_binding",[{**r("oxygen_regime","aerobic").to_dict(),"introduced_phase_id":"p0","introduced_edge":"hyp:other"}]),
        ("requirement_object",[r("oxygen_regime","aerobic")]),("missing_fields",[{"key":"pH"}]),
        ("invalid_interval",[{"key":"pH","level":"essential","value":{"lo":8,"hi":6},"source_refs":["src:e"]}])):
    capture("contract_"+name,lambda requirements=requirements:h(requirements).to_dict())
for version in (None,"future-context-999"):
    cc=copy.deepcopy(normal_c);cc.schema_version=version
    capture("direct_context_version_"+str(version),lambda cc=cc:audit(normal_h,cc))
capture("matrix_text_inequality_fixed",lambda:aggregate(facts=[f("matrix","sandy soil")],requirements=[r("matrix","soil")],declared_scope=["matrix"]).to_dict())
Path(__file__).with_name("results.json").write_text(json.dumps(OUT,ensure_ascii=False,sort_keys=True,indent=2))
print(json.dumps({k:{"completed":v["completed"],"error_type":v.get("error_type")} for k,v in OUT.items()},ensure_ascii=False,indent=2))
