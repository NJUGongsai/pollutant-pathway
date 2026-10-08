"""R6 synthetic storage boundaries; no repository writes, no real assets.

SQL mutations below only prepare damage in newly-created synthetic databases.
All actual acceptance/rejection is observed through public put/submit APIs.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

EXPECTED_HEAD = '00e509a974b40a7c9779fcd35e53b16637a13d60'
REPO = Path('/Volumes/CC/Enzyme_Agent/dependingv43')
SOURCE_ROOT = Path(__file__).parent / 'src'
actual_head = subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
assert actual_head == EXPECTED_HEAD
assert sys.dont_write_bytecode
print(json.dumps({'type':'metadata','expected_head':EXPECTED_HEAD,'actual_head':actual_head,
  'source_root':str(SOURCE_ROOT),'bytecode_disabled':True,
  'source_sha256':{name:hashlib.sha256((SOURCE_ROOT/name).read_bytes()).hexdigest()
    for name in ['pathway_v43/pollutant/store.py','pathway_v43/pollutant/legacy_reader.py']},
  'scope':'Synthetic SQLite only; SQL prepares damage, then public API is observed'},sort_keys=True))

from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.events import build_pathway_event, build_report_projection, build_expansion_plan
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis, recompute_hypothesis_id
from pathway_v43.pollutant.store import PollutantPathwayStore

ROOT = Path(tempfile.mkdtemp(prefix='synthetic_r6_',dir=Path(__file__).parent))

def emit(name,**data):
    print(json.dumps({'probe':name,**data},sort_keys=True,ensure_ascii=False,default=str))

def capture(name,fn):
    try:emit(name,**fn())
    except Exception as exc:emit(name,error=type(exc).__name__,detail=getattr(exc,'detail',{}),message=str(exc))

def state(smi,origin='source_product',refs=None):
    return build_chemical_state(smi,origin,refs)

def fixture(name):
    sub=state('CCO','raw_input',[{'record':'sub-A'}])
    prod=state('CC=O',refs=[{'record':'prod-A'}])
    hyp=build_hypothesis(parent_path_id='p1',substrate_state_ref=sub.state_id,
      participants=[Participant(state_ref=sub.state_id,side='reactant',role='primary_substrate',coefficient=None,coefficient_status='unknown'),
                    Participant(state_ref=prod.state_id,side='product',role='principal_product',coefficient=None,coefficient_status='unknown')],
      participant_list_status='partial',step_scope='net_reaction',origin_group_key=name)
    event=build_pathway_event(hyp,run_id=name,context_hash='ctx')
    args={'report_projection':build_report_projection(hyp,max_reportable=1,ranked_state_refs=[prod.state_id]).to_dict(),
      'expansion_plan':build_expansion_plan(hyp,expanded=[prod.state_id],deferred=[],not_tracked=[]).to_dict(),
      'states':[sub.to_dict(),prod.to_dict()],'hypothesis_dict':hyp.to_dict()}
    return PollutantPathwayStore(ROOT/(name+'.sqlite')),sub,prod,hyp,event,args

def observed_submit(store,event,args):
    before=store.counts()
    try:out={'result':store.submit_event(event,**args)}
    except Exception as exc:out={'error':type(exc).__name__,'detail':getattr(exc,'detail',{})}
    after=store.counts()
    return {**out,'counts_before':before,'counts_after':after,'counts_preserved':before==after,
      'event_present':store.get_event(event.event_id) is not None}

def replay(store,event,args):
    return observed_submit(store,event,dict(args,states=[],hypothesis_dict=None))

def existing_state_first(field,value):
    name='existing_state_first_'+field
    store,sub,prod,hyp,event,args=fixture(name)
    for s in args['states']:store.put_state(s)
    if field!='valid':
        saved=json.loads(store.conn.execute('SELECT payload FROM states WHERE state_id=?',(prod.state_id,)).fetchone()[0])
        saved[field]=value
        store.conn.execute('UPDATE states SET payload=? WHERE state_id=?',(json.dumps(saved),prod.state_id));store.conn.commit()
    first=observed_submit(store,event,dict(args,states=[]))
    out={'field':field,'mutated_value':value,'first':first,'replay':replay(store,event,args)}
    store.close();return out

for field,value in [('valid',None),('cn_identity','CCN'),('schema_version','ppv1-chemstate-99'),('state_id','fake:inner-state')]:
    capture('existing_state_first_'+field,lambda f=field,v=value:existing_state_first(f,v))

def existing_appearance_bad_hash_first():
    store,sub,prod,hyp,event,args=fixture('existing_appearance_bad_hash_first')
    for s in args['states']:store.put_state(s)
    row=store.conn.execute('SELECT appearance_hash,payload FROM state_appearances WHERE state_id=?',(prod.state_id,)).fetchone()
    payload=json.loads(row['payload']);payload['source_refs']=[{'record':'modified_without_hash'}]
    store.conn.execute('UPDATE state_appearances SET payload=? WHERE state_id=? AND appearance_hash=?',(json.dumps(payload),prod.state_id,row['appearance_hash']));store.conn.commit()
    out={'first':observed_submit(store,event,dict(args,states=[])),'replay':replay(store,event,args)}
    store.close();return out
capture('existing_appearance_bad_hash_first',existing_appearance_bad_hash_first)

def existing_hypothesis_first(kind):
    store,sub,prod,hyp,event,args=fixture('existing_hyp_first_'+kind)
    store.put_hypothesis(hyp.to_dict())
    payload=hyp.to_dict()
    if kind=='assumptions':payload['assumptions']=['modified premise']
    elif kind=='inner_id':payload['hypothesis_id']='fake:inner-hyp'
    elif kind=='schema':payload['schema_version']='ppv1-hypothesis-99'
    elif kind=='participant_entry':payload['participants'][0]['entry_id']='fake:entry'
    if kind!='valid':
        store.conn.execute('UPDATE hypotheses SET payload=? WHERE hypothesis_id=?',(json.dumps(payload),hyp.hypothesis_id));store.conn.commit()
    out={'mutated':kind,'provided_row_id':hyp.hypothesis_id,'rederived_payload_id':recompute_hypothesis_id(payload),
      'first':observed_submit(store,event,dict(args,hypothesis_dict=None))}
    if kind=='valid':out['replay']=replay(store,event,args)
    store.close();return out
for kind in ['valid','assumptions','inner_id','schema','participant_entry']:
    capture('existing_hypothesis_first_'+kind,lambda k=kind:existing_hypothesis_first(k))

def existing_hypothesis_self_consistent_bad_participant():
    store,sub,prod,hyp,event,args=fixture('existing_hyp_self_consistent_bad_participant')
    store.put_hypothesis(hyp.to_dict())
    payload=hyp.to_dict();payload['participants'][0]['entry_id']='fake:entry'
    new_id=recompute_hypothesis_id(payload);payload['hypothesis_id']=new_id
    # Damage prepared in the synthetic row; ID equality alone is not enough.
    store.conn.execute('UPDATE hypotheses SET hypothesis_id=?,payload=? WHERE hypothesis_id=?',
      (new_id,json.dumps(payload),hyp.hypothesis_id));store.conn.commit()
    event=build_pathway_event(replace(hyp,hypothesis_id=new_id),run_id='existing_hyp_self_consistent_bad_participant',context_hash='ctx')
    out={'row_id':new_id,'inner_id':payload['hypothesis_id'],'rederived_payload_id':recompute_hypothesis_id(payload),
      'first':observed_submit(store,event,dict(args,hypothesis_dict=None))}
    store.close();return out
capture('existing_hypothesis_self_consistent_bad_participant',existing_hypothesis_self_consistent_bad_participant)

def ambiguous_first(explicit):
    store,sub,prod,hyp,event,args=fixture('ambiguous_first_'+str(explicit))
    other=state('O=CC',refs=[{'record':'prod-B'}])
    store.put_state(prod.to_dict());store.put_state(other.to_dict())
    first=observed_submit(store,event,dict(args,states=args['states'] if explicit else [sub.to_dict()]))
    out={'explicit_product_A':explicit,'first':first}
    if first.get('result',{}).get('created'):out['replay']=replay(store,event,args)
    store.close();return out
capture('ambiguous_first_without_explicit_state_rejected',lambda:ambiguous_first(False))
capture('ambiguous_first_explicit_state_control',lambda:ambiguous_first(True))

def multi_occurrence_manifest(mode):
    store,sub,prod,hyp,event,args=fixture('multi_occurrence_manifest_'+mode)
    other=state('O=CC',refs=[{'record':'prod-B'}])
    first=observed_submit(store,event,dict(args,states=[sub.to_dict(),prod.to_dict(),other.to_dict()]))
    original=json.loads(store.get_event(event.event_id)['payload'])
    normal=replay(store,event,args)
    product_entries=[x for x in original['event_appearance_manifest'] if x['state_id']==prod.state_id]
    appearances=store.state_appearances(prod.state_id)
    a_hash=next(row['appearance_hash'] for row in store.conn.execute('SELECT appearance_hash,payload FROM state_appearances WHERE state_id=?',(prod.state_id,))
      if json.loads(row['payload'])['source_refs']==[{'record':'prod-A'}])
    payload=json.loads(json.dumps(original))
    if mode in ['remove_manifest_A_only','remove_manifest_and_row_A']:
        payload['event_appearance_manifest']=[x for x in original['event_appearance_manifest'] if x['appearance_hash']!=a_hash]
        store.conn.execute('UPDATE events SET payload=? WHERE event_id=?',(json.dumps(payload),event.event_id))
    if mode in ['remove_row_A_only','remove_manifest_and_row_A']:
        store.conn.execute('DELETE FROM state_appearances WHERE state_id=? AND appearance_hash=?',(prod.state_id,a_hash))
    store.conn.commit()
    out={'first':first,'normal_replay':normal,'original_manifest':original['event_appearance_manifest'],
      'product_entries_count':len(product_entries),'distinct_source_refs':appearances,
      'removed_A_hash':a_hash if mode!='normal' else None,'saved_manifest':payload['event_appearance_manifest'],
      'remaining_product_appearances':store.state_appearances(prod.state_id),'replay':replay(store,event,args)}
    store.close();return out
for mode in ['normal','remove_manifest_A_only','remove_row_A_only','remove_manifest_and_row_A']:
    capture('multi_occurrence_manifest_'+mode,lambda m=mode:multi_occurrence_manifest(m))
