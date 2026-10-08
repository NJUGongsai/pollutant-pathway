from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--source', required=True)
a = parser.parse_args()
source = Path(a.source).resolve()
sys.path.insert(0, str(source/'src'))
spec = importlib.util.spec_from_file_location('r7conditions', source/'tests/test_ppv1_r7_conditions.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
from pathway_v43.pollutant.path_context import ConditionContractError, PathContext, derive_child_context, _recompute_context_hash
from pathway_v43.pollutant.profile import PPV1_CONTEXT_SCHEMA_VERSION

results=[]
def run(name, f):
    try:
        value=f()
        row={'name':name,'outcome':'completed','value':value}
    except Exception as e:
        row={'name':name,'outcome':'rejected','exception_type':type(e).__name__,'detail':getattr(e,'detail',{}),'message':str(e)}
    results.append(row)
    print(json.dumps(row,ensure_ascii=False,sort_keys=True))

def audit(c):
    h, ss, ev=t._oxygen_hyp()
    return t._audit(h,ss,c,ev)

def legal_unknown():
    c=t._ph_unknown_child()
    restored=PathContext.from_dict(c.to_dict())
    derived=derive_child_context(restored)
    return {'audit':audit(derived),'roundtrip_identity_equal':restored.context_id==c.context_id,'row_signature_set_equal':set(c.phase_history[0]['covered_requirement_signatures'])=={r['requirement_signature'] for r in c.phase_history[0]['per_requirement']}}

run('legal_unknown_restore_derive_audit',legal_unknown)
run('legal_conflict_control_public_chain',lambda:(t.test_r6_03_legal_conflict_history_roundtrip_kept() or 'test completed all assertions'))
run('legal_satisfied_transition_grandchild_public_chain',lambda:(t.test_r6_03_legal_satisfied_history_and_transition_kept() or 'test completed all assertions'))

def damaged(shape,entry):
    c=t._ph_unknown_child()
    snap=c.phase_history[0]
    if shape=='remove_rows_keep_signature':
        t._tamper_snapshot(c)
    elif shape=='remove_signature_keep_rows':
        snap['covered_requirement_signatures']=[]
    elif shape=='mutate_fact_keep_id':
        object.__setattr__(c.condition_facts[0],'value','anaerobic')
    elif shape=='invent_signature':
        snap['covered_requirement_signatures'].append('unassessed:invented_signature')
    else: raise AssertionError(shape)
    if entry=='derive': return derive_child_context(c).to_dict()
    if entry=='restore': return PathContext.from_dict(c.to_dict()).to_dict()
    if entry=='audit': return audit(c)
    raise AssertionError(entry)

for shape in ('remove_rows_keep_signature','remove_signature_keep_rows','mutate_fact_keep_id'):
    for entry in ('derive','restore','audit'):
        run(shape+'_'+entry,lambda s=shape,e=entry:damaged(s,e))
run('invented_signature_restore',lambda:damaged('invent_signature','restore'))

def orphan():
    c=t._ph_unknown_child()
    t._tamper_snapshot(c,drop_signature=True)
    rebuilt=t._rebuild_self_consistent(c)
    restored=PathContext.from_dict(rebuilt.to_dict())
    result=audit(derive_child_context(restored))
    return result
run('self_consistent_empty_snapshot_orphan_unknown',orphan)

def flag_correct_order():
    c=t._ph_unknown_child()
    c.phase_history[0]['has_gate_requirements']=False
    return audit(c)
run('flag_tampering_correct_call_order',flag_correct_order)

def original_bad_order():
    child2=t._ph_unknown_child()
    child2.phase_history[0]['has_gate_requirements']=False
    return t._audit(*t._oxygen_hyp(),child2)
run('original_r7_test_bad_argument_order',original_bad_order)
assert len(results)==16
assert results[0]['value']['audit']['condition_status']=='unknown'
assert results[0]['value']['audit']['admission'][0]=='retain_conditional'
assert results[1]['outcome']==results[2]['outcome']=='completed'
for r in results[3:13]:
    assert r['outcome']=='rejected' and r['exception_type']=='ConditionContractError',r
assert results[13]['value']['condition_status']=='unknown'
assert results[13]['value']['admission'][0]=='retain_conditional'
assert results[14]['detail']['check']=='gate_flag_mismatch'
assert results[15]['detail']['kind']=='context_object_invalid_type'
print(json.dumps({'meta':{'schema':PPV1_CONTEXT_SCHEMA_VERSION,'source':str(source),'case_count':len(results),'expected_control_assertions':'all passed'}},ensure_ascii=False))
