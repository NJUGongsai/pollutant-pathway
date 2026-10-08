"""Read-only synthetic review probes for PPV1 R3 HEAD af14fb2.
All states/conditions are invented; no assets, runs or model calls.
"""
import copy
import json
import tempfile
from dataclasses import FrozenInstanceError
from pathlib import Path

from pathway_v43.pollutant.path_context import (
    ConditionFact, Requirement, PathContext,
    build_condition_fact as fact, build_requirement as req,
    build_path_context as ctx, derive_child_context as child,
    aggregate_environment_fit as aggregate, assess_conditions,
    build_dependency, resolve_dependency, detect_circular_dependencies,
)
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis, ReactionHypothesis
from pathway_v43.pollutant.chemstate import build_chemical_state, archive_recovered_fidelity
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission
from pathway_v43.pollutant.profile import PPV1_DONOR_DIAGNOSTIC_VERSION
from pathway_v43.pollutant.store import PollutantPathwayStore

OUT = {}
def save(key, result):
    OUT[key] = result.to_dict() if hasattr(result, "to_dict") else result

def f(key, value, **kw):
    return fact(key=key, value=value, status="known_present", **kw)

def r(key, value, **kw):
    return req(key=key, value=value, level="essential", source_refs=["src:synthetic"], **kw)

# Full element/charge bookkeeping fixture, not an assertion of mechanism.
states = {s: build_chemical_state(s, origin="raw_input")
          for s in ("CCO", "O=O", "CC(=O)O", "O")}
state_map = {s.state_id: s for s in states.values()}
def h(requirements=None, deps=None, **kw):
    participants = [Participant(state_ref=states[s].state_id, side=side, role=role,
        coefficient=1, coefficient_status="known")
        for s, side, role in (("CCO","reactant","primary_substrate"),
            ("O=O","reactant","cosubstrate"),
            ("CC(=O)O","product","principal_product"),
            ("O","product","principal_product"))]
    return build_hypothesis(parent_path_id="synthetic:p", substrate_state_ref=states["CCO"].state_id,
        participants=participants, participant_list_status="declared_complete", step_scope="net_reaction",
        origin_group_key="synthetic:source", requirements=requirements or [], dependency_refs=deps or [], **kw)

center = {"checker_version": PPV1_DONOR_DIAGNOSTIC_VERSION,
    "center_match": True, "declaration_mismatch": False,
    "center_match_basis": "direct", "evidence_refs": ["synthetic:checker_output"]}

def audit(hyp, context, **kw):
    args = dict(states=state_map, context=context, center_evidence=center)
    args.update(kw)
    a = audit_hypothesis(hyp, **args)
    return {"input_hash": a.input_hash, "audit_id": a.audit_id,
        "checks": {c.name:{"status":c.status,"reason":c.reason_code,"refs":c.evidence_refs} for c in a.checks},
        "admission": decide_admission(a)}

normal_ctx = ctx(condition_facts=[f("oxygen_regime","aerobic")], assessment_scope=["oxygen_regime"])
normal_h = h([r("oxygen_regime","aerobic").to_dict()])
save("baseline_full_audit", audit(normal_h, normal_ctx))

# R2 original phase controls, now also compare the actual audit route.
phase_facts = [f("oxygen_regime","aerobic",phase_id="p0",subject_scenario_ref="s"),
               f("oxygen_regime","anaerobic",phase_id="p1",subject_scenario_ref="s")]
parent = ctx(condition_facts=phase_facts, phase_id="p0", scenario_ref="s",
    accumulated_requirements=[r("oxygen_regime","aerobic")], assessment_scope=["oxygen_regime"])
c = child(parent, step_requirements=[r("oxygen_regime","anaerobic")],
    scenario_transition={"new_phase_id":"p1","source_ref":"user:transition"})
save("old_phase_false_conflict_fixed", {"route":c.route_assessment().environment_fit,
    "current":c.current_step_assessment().environment_fit,
    "audit":audit(h([r("oxygen_regime","anaerobic").to_dict()]),c)})
bad_parent = ctx(condition_facts=phase_facts, phase_id="p0", scenario_ref="s",
    accumulated_requirements=[r("oxygen_regime","anaerobic")], assessment_scope=["oxygen_regime"])
bad_child = child(bad_parent, step_requirements=[r("oxygen_regime","anaerobic")],
    scenario_transition={"new_phase_id":"p1","source_ref":"user:transition"})
save("old_phase_past_conflict_fixed", {"route":bad_child.route_assessment().environment_fit,
    "current":bad_child.current_step_assessment().environment_fit,
    "audit":audit(h([r("oxygen_regime","anaerobic").to_dict()]),bad_child)})

# Two separately declared scenarios can reuse local phase labels.
# Historical sA:p0 conflict must not be evaluated with sB:p0 facts after adopting sB:p1.
scenario_facts = [f("oxygen_regime","aerobic",phase_id="p0",subject_scenario_ref="sA"),
    f("oxygen_regime","anaerobic",phase_id="p0",subject_scenario_ref="sB"),
    f("oxygen_regime","anaerobic",phase_id="p1",subject_scenario_ref="sB")]
for old_required in ("anaerobic","aerobic"):
    p = ctx(condition_facts=scenario_facts, phase_id="p0",scenario_ref="sA",
        accumulated_requirements=[r("oxygen_regime",old_required)],assessment_scope=["oxygen_regime"])
    c = child(p,step_requirements=[r("oxygen_regime","anaerobic")],
        scenario_transition={"new_phase_id":"p1","new_scenario_ref":"sB","source_ref":"user:transition"})
    save("scenario_switch_old_req_"+old_required,{"parent":p.route_assessment().environment_fit,
        "route":c.route_assessment().environment_fit,"current":c.current_step_assessment().environment_fit,
        "assess_conditions":assess_conditions(c,h([r("oxygen_regime","anaerobic").to_dict()])).to_dict(),
        "audit":audit(h([r("oxygen_regime","anaerobic").to_dict()]),c)})

# Hypothesis's own requirement pre-bound to a foreign old phase bypasses current conditions.
foreign = r("oxygen_regime","anaerobic").to_dict()
foreign.update(introduced_phase_id="p0",introduced_scenario_ref="s",introduced_edge="another:hypothesis")
foreign_ctx = ctx(condition_facts=[f("oxygen_regime","anaerobic",phase_id="p0",subject_scenario_ref="s"),
    f("oxygen_regime","aerobic",phase_id="p1",subject_scenario_ref="s")],phase_id="p1",scenario_ref="s",
    assessment_scope=["oxygen_regime"])
save("own_step_foreign_phase_binding",audit(h([foreign]),foreign_ctx))

# Inherited context dependency references are not read by provenance_dependency.
dep_ctx = ctx(condition_facts=[f("oxygen_regime","aerobic")],assessment_scope=["oxygen_regime"],
    dependency_refs=["dep:unresolved_upstream"])
save("inherited_context_dependency_default",audit(normal_h,dep_ctx))
save("inherited_context_dependency_explicit_unresolved",audit(normal_h,dep_ctx,
    unresolved_dependency_ids=["dep:unresolved_upstream"]))

# R2 point, absence, units and scope controls; matrix and absent unit ambiguity.
for name, fv, rv, unit in (("point_inside",{"lo":6.8,"hi":7.2},7,""),
                          ("point_singleton",{"lo":7,"hi":7},7,"")):
    save(name,aggregate(facts=[f("pH",fv,unit=unit)],requirements=[r("pH",rv,value_basis="point")],declared_scope=["pH"]))
save("foreign_entity_absent_fixed",aggregate(facts=[fact(key="electron_donor",value="acetate",status="known_absent")],
    requirements=[r("electron_donor","NADH")],declared_scope=["electron_donor"]))
save("kelvin_fact_fixed",aggregate(facts=[f("temperature_C",25,unit="K")],
    requirements=[r("temperature_C",{"lo":20,"hi":30})],declared_scope=["temperature_C"]))
save("source_temperature_unit_unknown",aggregate(facts=[f("temperature_C",25,origin="curated_source",
    source_ref="src:unit_not_reported",subject_scenario_ref="s")],requirements=[r("temperature_C",{"lo":20,"hi":30})],
    scenario_ref="s",declared_scope=["temperature_C"]))
save("matrix_overlap",aggregate(facts=[f("matrix","sandy soil")],requirements=[r("matrix","soil")],declared_scope=["matrix"]))
save("scope_actual_fixed",aggregate(facts=[f("oxygen_regime","aerobic")],requirements=[r("oxygen_regime","aerobic")],
    declared_scope=["oxygen_regime","pH","temperature_C"]))
save("scope_narrowing_does_not_hide_unknown",aggregate(facts=[f("oxygen_regime","aerobic")],
    requirements=[r("oxygen_regime","aerobic"),r("pH",{"lo":6,"hi":8})],declared_scope=["oxygen_regime"]))

# R2 branch alias is repaired, but frozen fields contain mutable nested containers.
parent = ctx(condition_facts=[f("temperature_C",25)],assessment_scope=["temperature_C"],
    accumulated_requirements=[r("temperature_C",{"lo":20,"hi":30})])
a,b = child(parent),child(parent)
aid=a.context_id
a.accumulated_requirements[0].value.update(lo=40,hi=50)
save("branch_alias_fixed_but_self_hash_stale",{"parent":parent.assessed_scope,"sibling":b.assessed_scope,
    "child":a.assessed_scope,"child_id_unchanged":aid==a.context_id})
unsourced = req(key="oxygen_regime",value="aerobic",level="essential")
uc = ctx(condition_facts=[f("oxygen_regime","aerobic")],accumulated_requirements=[unsourced],assessment_scope=["oxygen_regime"])
before=uc.assessed_scope; before_id=uc.context_id
before_audit=audit(normal_h,uc)
uc.accumulated_requirements[0].source_refs.append("src:added_after_hash")
save("frozen_nested_source_refs_mutable",{"before":before,"after":uc.assessed_scope,"id_unchanged":before_id==uc.context_id,
    "before_audit":before_audit,"after_audit":audit(normal_h,uc)})
raw_req=r("temperature_C",{"lo":20,"hi":30}).to_dict()
hh=h([raw_req]); hid=hh.hypothesis_id
raw_req["value"].update(lo=40,hi=50)
save("hypothesis_nested_caller_alias",{"changed_hypothesis_value":hh.requirements[0]["value"],"id_unchanged":hid==hh.hypothesis_id})

# Regeneration-only now retains startup unknown; supported initial supply clears it.
deps=[build_dependency(kind="cosubstrate_supply",statement=s) for s in ("supplies:A:B","supplies:B:C","supplies:C:A")]
regen=[resolve_dependency(d,new_evidence=["src:regen"],resolution="supported",support_axis="regeneration") for d in deps]
save("regeneration_only_fixed",detect_circular_dependencies(regen))
initial=list(regen);initial[0]=resolve_dependency(initial[0],new_evidence=["src:initial_pool"],resolution="supported",support_axis="initial_supply")
save("startup_evidence_control",detect_circular_dependencies(initial))
later=list(initial);later[0]=resolve_dependency(later[0],new_evidence=["src:later_regen"],resolution="supported",support_axis="regeneration")
save("later_regeneration_overwrites_initial_axis",detect_circular_dependencies(later))

# Hash covers some IDs/versions, but omits outcome-bearing input values.
dep_h=h([r("oxygen_regime","aerobic").to_dict()],deps=["dep:1"])
save("hash_dependency_resolution",{
    "resolved":audit(dep_h,normal_ctx,unresolved_dependency_ids=[]),
    "unresolved":audit(dep_h,normal_ctx,unresolved_dependency_ids=["dep:1"])})
negative_center=copy.deepcopy(center);negative_center["center_match"]=False
save("hash_center_payload",{"positive":audit(normal_h,normal_ctx),
    "negative":audit(normal_h,normal_ctx,center_evidence=negative_center)})
alt_states=dict(state_map)
alt=build_chemical_state("CCO",origin="source_product",fidelity=archive_recovered_fidelity())
alt_states[alt.state_id]=alt
save("hash_state_fidelity",{"same_state_id":alt.state_id==states["CCO"].state_id,
    "raw":audit(normal_h,normal_ctx),"archive":audit(normal_h,normal_ctx,states=alt_states)})
charge_alt=build_chemical_state("CCO",origin="source_product",fidelity={"formal_charge":"unknown"})
charge_states=dict(state_map);charge_states[charge_alt.state_id]=charge_alt
save("hash_state_charge_fidelity",{"same_state_id":charge_alt.state_id==states["CCO"].state_id,
    "raw":audit(normal_h,normal_ctx),"unknown_charge":audit(normal_h,normal_ctx,states=charge_states)})

# Public hypothesis factory/raw read paths do not validate condition schema.
for name, reqs in (("requirement_object",[r("oxygen_regime","aerobic")]),
    ("missing_fields",[{"key":"temperature"}]),
    ("invalid_level",[{"key":"oxygen_regime","level":"bogus","value":"aerobic","source_refs":["src:e"]}]),
    ("invalid_interval",[{"key":"pH","level":"essential","value":{"lo":8,"hi":6},"source_refs":["src:e"]}])):
    try:
        hh=h(reqs)
        result={"constructed":True,"id":hh.hypothesis_id}
        try: result["audit"]=audit(hh,normal_ctx)
        except Exception as e: result["audit_error"]={"type":type(e).__name__,"message":str(e),"detail":getattr(e,"detail",None)}
    except Exception as e:
        result={"constructed":False,"error_type":type(e).__name__,"message":str(e),"detail":getattr(e,"detail",None)}
    save("contract_"+name,result)

# Hypothesis condition/dep IDs now differ; requirements list order remains same hash but payload order differs.
hs=[h([r("oxygen_regime",v).to_dict()]) for v in ("aerobic","anaerobic")]
hs.append(h([r("oxygen_regime","aerobic").to_dict()],deps=["dep:unknown"]))
save("hypothesis_scientific_identity_fixed",[x.hypothesis_id for x in hs])
q1=r("oxygen_regime","aerobic").to_dict();q2=r("pH",{"lo":6,"hi":8}).to_dict()
ha,hb=h([q1,q2]),h([q2,q1])
with tempfile.TemporaryDirectory(prefix="synthetic_",dir=Path(__file__).parent) as tmp:
    store=PollutantPathwayStore(Path(tmp)/"synthetic.sqlite")
    store.put_hypothesis(ha.to_dict())
    try:
        store.put_hypothesis(hb.to_dict());result="accepted"
    except Exception as e: result={"type":type(e).__name__,"message":str(e)}
    store.close()
save("hypothesis_order_invariant_id_conflicts_payload",{"same_id":ha.hypothesis_id==hb.hypothesis_id,"second_put":result})

for version in (None,"future-context-999"):
    dc=normal_ctx.to_dict()
    if version is None:dc.pop("schema_version")
    else:dc["schema_version"]=version
    try:result=PathContext.from_dict(dc).to_dict()
    except Exception as e:result={"type":type(e).__name__,"message":str(e)}
    save("from_dict_context_version_"+str(version),result)
    badctx=copy.deepcopy(normal_ctx);badctx.schema_version=version
    save("direct_audit_context_version_"+str(version),audit(normal_h,badctx))

print(json.dumps(OUT,ensure_ascii=False,sort_keys=True,indent=2))
