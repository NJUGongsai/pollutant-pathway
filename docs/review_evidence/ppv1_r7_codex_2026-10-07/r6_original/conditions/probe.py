"""Read-only R6 condition probes. Bootstrap the archived genuine fixture only.
Run with python -B, PYTHONPATH=<repo>/src. No assets/models/source mutations.
"""
import ast
import json
from pathlib import Path

FIXTURE=Path(__file__).with_name('r5_fixture.py')
prefix=[]
for node in ast.parse(FIXTURE.read_text()).body:
    if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='capture':
        break
    prefix.append(node)
exec(compile(ast.Module(body=prefix,type_ignores=[]),str(FIXTURE),'exec'),globals())
OUT={}

def historical(old_value='anaerobic'):
    p=ctx(condition_facts=[f('oxygen_regime','aerobic',phase_id='p0',subject_scenario_ref='sA'),
        f('oxygen_regime','anaerobic',phase_id='p1',subject_scenario_ref='sB')],
        phase_id='p0',scenario_ref='sA',accumulated_requirements=[r('oxygen_regime',old_value)],assessment_scope=['oxygen_regime'])
    c=child(p,step_requirements=[r('oxygen_regime','anaerobic')],scenario_transition={'new_phase_id':'p1','new_scenario_ref':'sB','source_ref':'user:synthetic_transition'})
    return c,h([r('oxygen_regime','anaerobic').to_dict()])

def valid_roundtrip():
    c,hyp=historical()
    restored=PathContext.from_dict(c.to_dict())
    return {'same_id':c.context_id==restored.context_id,'same_payload':c.to_dict()==restored.to_dict(),'audit':audit(hyp,restored)}
capture('legal_historical_conflict_roundtrip',valid_roundtrip)
capture('legal_historical_satisfied_roundtrip',lambda:view(*historical('aerobic')))

def snapshot_tamper(field,value,direct=False):
    c,hyp=historical()
    if direct:
        c.phase_history[0][field]=value
        return audit(hyp,c)
    raw=c.to_dict();raw['phase_history'][0][field]=value
    return audit(hyp,PathContext.from_dict(raw))
capture('summary_tamper_from_dict_rejected',lambda:snapshot_tamper('environment_fit','compatible'))
capture('flag_tamper_from_dict_rejected',lambda:snapshot_tamper('has_gate_requirements',False))
capture('summary_tamper_direct_audit_rejected',lambda:snapshot_tamper('environment_fit','compatible',True))
capture('flag_tamper_direct_audit_rejected',lambda:snapshot_tamper('has_gate_requirements',False,True))

def fact_tamper_direct():
    c=copy.deepcopy(normal_c)
    c.condition_facts=[f('oxygen_regime','anaerobic')]
    return audit(normal_h,c)
capture('fact_changed_kept_context_id_rejected',fact_tamper_direct)

def foreign_signature():
    c,hyp=historical()
    raw=c.to_dict();raw['phase_history'][0]['covered_requirement_signatures'].append('unassessed:invented_signature')
    return PathContext.from_dict(raw).to_dict()
capture('signature_not_in_requirements_rejected',foreign_signature)

def erased_rows_parent():
    p=ctx(condition_facts=[f('oxygen_regime','aerobic')],phase_id='p0',scenario_ref='s',
        accumulated_requirements=[r('pH',{'lo':6,'hi':8})],assessment_scope=['oxygen_regime','pH'])
    c=child(p,step_requirements=[r('oxygen_regime','aerobic')],step_edge_ref='hyp:current',
        scenario_transition={'new_phase_id':'p1','source_ref':'user:synthetic_transition'})
    return c

def derive_launders_unassessed_signature():
    c=erased_rows_parent()
    before=view(c,normal_h)
    old_sig=list(c.phase_history[0]['covered_requirement_signatures'])
    snap=c.phase_history[0]
    snap['per_requirement']=[]
    snap['requirement_coverage']={k:[] for k in snap['requirement_coverage']}
    snap['has_gate_requirements']=False
    # Recorded fit remains unknown, but signature still claims the old pH was
    # covered despite there being no evaluation row for it.
    try:
        direct=audit(normal_h,c)
    except Exception as e:
        direct={'error_type':type(e).__name__,'detail':getattr(e,'detail',None)}
    c2=child(c)  # public API re-hashes the invalid parent without validation
    after=view(c2,normal_h)
    restored=PathContext.from_dict(c2.to_dict())
    return {'before':before,'invalid_parent_audit':direct,'after_public_derive':after,
        'new_child_id':c2.context_id,'old_parent_id':c.context_id,
        'retained_signature':old_sig,'history':c2.phase_history,
        'accepted_roundtrip':audit(normal_h,restored)}
capture('derive_launders_empty_evaluation_with_existing_signature',derive_launders_unassessed_signature)

def signature_rows_control():
    c=erased_rows_parent()
    return view(c,normal_h)
capture('genuine_unknown_historical_requirement_retained',signature_rows_control)

Path(__file__).with_name('results.json').write_text(json.dumps(OUT,ensure_ascii=False,sort_keys=True,indent=2))
print(json.dumps({k:{'completed':v['completed'],'error_type':v.get('error_type'),'kind':v.get('detail',{}).get('kind') if isinstance(v.get('detail'),dict) else None} for k,v in OUT.items()},ensure_ascii=False,indent=2))
