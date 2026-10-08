"""Synthetic public search-policy first-consumer vs same-source profile guard."""
import copy,json,sys
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P/'src'))
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.search import SearchLedger,search_policy_version
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.storage.artifact_store import ArtifactStore

def cap(f):
 try:return {'accepted':True,'result':f()}
 except Exception as e:return {'accepted':False,'exception':type(e).__name__,'detail':getattr(e,'detail',{}),'message':str(e)}
def emit(case,**kw):print(json.dumps({'case':case,**kw},ensure_ascii=False,sort_keys=True,default=str))
for label,change in [('clean',{}),('out_of_range',{'max_total_search_actions':1001}),('bool_limit',{'max_total_search_actions':True}),('unknown_key',{'made_up_limit':1}),('negative',{'max_total_search_actions':-1})]:
 s=PollutantPathwayStore(P/('policy_'+label+'.sqlite'));l=SearchLedger(s,ArtifactStore(P/'policy_runs',label),label)
 policy=copy.deepcopy(build_profile_identity_block());policy['search_limits'].update(change)
 source_guard=cap(lambda:build_profile_identity_block(search_limits=change))
 reg=cap(lambda:l.register_search_run(label,policy))
 enqueue=cap(lambda:l.enqueue_action(run_id=label,parent_path_id='p1',context_ref='ctx1',subject_ref='pool_A',action_kind='decide',policy_version=search_policy_version(),payload={'task_key':'task_A'}))
 action=enqueue.get('result',{}).get('action_id');claim=cap(lambda:l.claim_action(action,worker_id='w1')) if action else None
 data={t:[dict(r) for r in s.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in ['search_runs','search_actions','budget_reservations']}
 emit(label,input_policy=policy,same_source_profile_guard=source_guard,register=reg,enqueue=enqueue,claim=claim,rows=data,snapshot=cap(lambda:l.budget_snapshot(label)),actual_external_model_calls=0)
 s.close()
