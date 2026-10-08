"""Independent R7 fixed-contract probes. Synthetic molecules/SQLite only.
Run in a fresh tmp; uses public build/put/submit/replay, SQL only prepares corruption.
"""
from pathlib import Path
import sys, json, tempfile, hashlib
from dataclasses import asdict
REPO=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(REPO/'src'))
from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.events import build_pathway_event,build_report_projection,build_expansion_plan
from pathway_v43.pollutant.hypothesis import Participant,build_hypothesis
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.profile import PPV1_STORE_SCHEMA_VERSION
ROOT=Path(tempfile.mkdtemp(prefix='r7_independent_storage_db_'))

def fixture(name):
 sub=build_chemical_state('CCO','raw_input',[{'record':'sub-A'}])
 prod=build_chemical_state('CC=O','source_product',[{'record':'prod-A'}])
 hyp=build_hypothesis(parent_path_id='p1',substrate_state_ref=sub.state_id,participants=[Participant(state_ref=sub.state_id,side='reactant',role='primary_substrate',coefficient=None,coefficient_status='unknown'),Participant(state_ref=prod.state_id,side='product',role='principal_product',coefficient=None,coefficient_status='unknown')],participant_list_status='partial',step_scope='net_reaction',origin_group_key=name)
 event=build_pathway_event(hyp,run_id=name,context_hash='ctx')
 args={'report_projection':build_report_projection(hyp,max_reportable=1,ranked_state_refs=[prod.state_id]).to_dict(),'expansion_plan':build_expansion_plan(hyp,expanded=[prod.state_id],deferred=[],not_tracked=[]).to_dict(),'states':[sub.to_dict(),prod.to_dict()],'hypothesis_dict':hyp.to_dict()}
 return PollutantPathwayStore(ROOT/(name+'.sqlite')),sub,prod,hyp,event,args

def observe(store,event,args):
 before=store.counts()
 try: result=store.submit_event(event,**args);out={'created':result['created']}
 except Exception as exc:out={'error':type(exc).__name__,'kind':getattr(exc,'detail',{}).get('kind'),'detail':getattr(exc,'detail',{})}
 return {'outcome':out,'before':before,'after':store.counts(),'zero_write':before==store.counts()}

def dump(name,**record):print(json.dumps({'case':name,**record},sort_keys=True,ensure_ascii=False))

def appearance_corrupt(store,sid):
 row=store.conn.execute('SELECT appearance_hash,payload FROM state_appearances WHERE state_id=?',(sid,)).fetchone()
 payload=json.loads(row['payload']);old=payload['source_refs'];payload['source_refs']=[{'record':'tampered-only-in-new-synthetic-db'}]
 store.conn.execute('UPDATE state_appearances SET payload=? WHERE state_id=? AND appearance_hash=?',(json.dumps(payload),sid,row['appearance_hash']));store.conn.commit()
 return {'target':'appearance.source_refs','old':old,'new':payload['source_refs'],'appearance_hash_unchanged':row['appearance_hash']}

dump('metadata',schema=PPV1_STORE_SCHEMA_VERSION,python=sys.executable,source=str(REPO),database_root=str(ROOT))
for supplied in ('none','prod_only','all'):
 for corrupt in (False,True):
  name=f'first_existing_appearance_{supplied}_{"corrupt" if corrupt else "valid"}'
  store,sub,prod,hyp,event,args=fixture(name)
  for state in (sub,prod):store.put_state(state.to_dict())
  mutation=appearance_corrupt(store,prod.state_id) if corrupt else None
  provided=[] if supplied=='none' else [prod.to_dict()] if supplied=='prod_only' else args['states']
  first=observe(store,event,dict(args,states=provided))
  replay=observe(store,event,dict(args,states=[],hypothesis_dict=None)) if first['outcome'].get('created') else None
  dump(name,mutation=mutation,first=first,replay=replay,input_states=provided,input_event=asdict(event),input_hypothesis=hyp.to_dict())
  store.close()
# Old direct stored facts corrupt, no supplied state: must now reject first.
for field,value in (('cn_identity','CCN'),('schema_version','ppv1-chemstate-future'),('state_id','cs-corrupt-inner')):
 name=f'first_reused_semantic_{field}'
 store,sub,prod,hyp,event,args=fixture(name)
 for state in (sub,prod):store.put_state(state.to_dict())
 row=store.conn.execute('SELECT payload FROM states WHERE state_id=?',(prod.state_id,)).fetchone();data=json.loads(row['payload']);old=data[field];data[field]=value
 store.conn.execute('UPDATE states SET payload=? WHERE state_id=?',(json.dumps(data),prod.state_id));store.conn.commit()
 dump(name,mutation={'field':field,'old':old,'new':value},first=observe(store,event,dict(args,states=[])))
 store.close()
# v6 baseline has no links table; preceding first-submit probes still execute independently.
if PPV1_STORE_SCHEMA_VERSION == 'ppv1-store-6':
 dump('baseline_links_not_available',schema=PPV1_STORE_SCHEMA_VERSION)
 raise SystemExit(0)
# Distinct appearance set integrity. One-side changes only; no whole-ledger forgery.
for mutation in ('none','manifest_A_only','manifest_and_row_A','row_A_only','link_A_only','reverse_manifest'):
 name='multi_occurrence_'+mutation
 store,sub,prod,hyp,event,args=fixture(name);other=build_chemical_state('O=CC','source_product',[{'record':'prod-B'}])
 created=observe(store,event,dict(args,states=[sub.to_dict(),prod.to_dict(),other.to_dict()]))
 ep=json.loads(store.get_event(event.event_id)['payload']);manifest=ep['event_appearance_manifest'];a_hash=next(e['appearance_hash'] for e in manifest if e['state_id']==prod.state_id and json.loads(store.conn.execute('SELECT payload FROM state_appearances WHERE state_id=? AND appearance_hash=?',(prod.state_id,e['appearance_hash'])).fetchone()['payload'])['source_refs']==[{'record':'prod-A'}])
 if mutation in ('manifest_A_only','manifest_and_row_A'):
  ep['event_appearance_manifest']=[e for e in manifest if e['appearance_hash']!=a_hash]
  store.conn.execute('UPDATE events SET payload=? WHERE event_id=?',(json.dumps(ep),event.event_id))
 if mutation in ('row_A_only','manifest_and_row_A'):store.conn.execute('DELETE FROM state_appearances WHERE state_id=? AND appearance_hash=?',(prod.state_id,a_hash))
 if mutation=='link_A_only':store.conn.execute('DELETE FROM event_appearance_links WHERE event_id=? AND state_id=? AND appearance_hash=?',(event.event_id,prod.state_id,a_hash))
 if mutation=='reverse_manifest':
  ep['event_appearance_manifest']=list(reversed(manifest));store.conn.execute('UPDATE events SET payload=? WHERE event_id=?',(json.dumps(ep),event.event_id))
 store.conn.commit();replay=observe(store,event,dict(args,states=[],hypothesis_dict=None))
 dump(name,first=created,manifest_before=manifest,manifest_after=ep['event_appearance_manifest'],links=[dict(r) for r in store.conn.execute('SELECT * FROM event_appearance_links WHERE event_id=?',(event.event_id,))],replay=replay)
 store.close()
