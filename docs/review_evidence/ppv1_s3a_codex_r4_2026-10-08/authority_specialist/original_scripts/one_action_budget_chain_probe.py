#!/usr/bin/env python3
"""Upper 1 public chain: ordinary guard vs missing mandatory total reservation proof."""
from pathlib import Path
from dataclasses import asdict
import sys,json
P=Path(__file__).resolve().parent;sys.path[:0]=[str(P/'repo/src'),str(P/'repo/tests')]
from s3a_worker import make_fixture
from pathway_v43.pollutant.profile import build_profile_identity_block,validate_search_limits
from pathway_v43.pollutant.search import SearchLedger,search_policy_version
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.storage.artifact_store import ArtifactStore
ROOT=P/'one_action_chain_cases';ROOT.mkdir(exist_ok=False);ROWS=[]
TABLES=['meta','states','state_appearances','hypotheses','events','report_projections','expansion_plans','event_appearance_links','search_runs','search_actions','search_attempts','budget_reservations','model_requests','search_commit_records']
def snap(l):return {t:[dict(x) for x in l.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in TABLES}
def cap(fn):
 try:return {'returned':fn()}
 except Exception as exc:return {'error':type(exc).__name__,'detail':getattr(exc,'detail',{}),'text':str(exc)}
for mutation in ['clean','remove_total_ref_and_row']:
 name='upper1_'+mutation;d=ROOT/name;d.mkdir();l=SearchLedger(PollutantPathwayStore(d/'run.sqlite'),ArtifactStore(d/'runs',name),name);pol=build_profile_identity_block();pol['search_limits']=validate_search_limits({'max_total_search_actions':1});l.register_search_run(name,pol);steps=[]
 for i in range(2):
  _,_,h,e,args=make_fixture(name,'p1','origin'+str(i),'ctx1');a=l.enqueue_action(run_id=name,parent_path_id='p1',context_ref='ctx1',subject_ref=h.hypothesis_id,action_kind='expand_hypothesis',parent_search_revision=i,depth=1,policy_version=search_policy_version(),payload={'task_key':'tk'+str(i)})['action_id'];before=snap(l);receipt=cap(lambda:l.claim_action(a,worker_id='w1'));after_claim=snap(l)
  if 'error' in receipt:steps.append({'index':i,'event':asdict(e),'event_args':args,'action_id':a,'before_claim':before,'claim':receipt,'after_claim':after_claim});continue
  if mutation!='clean' and i==0:
   rid=l.conn.execute("SELECT reservation_id FROM budget_reservations WHERE action_id=? AND limit_key='max_total_search_actions'",(a,)).fetchone()[0];refs=l.action(a)['budget_reservation_ref'];refs.remove(rid);l.conn.execute('UPDATE search_actions SET budget_reservation_ref=? WHERE action_id=?',(json.dumps(refs),a));l.conn.execute('DELETE FROM budget_reservations WHERE reservation_id=?',(rid,));l.conn.commit()
  before_submit=snap(l);submitted=cap(lambda:l.submit_action_event(a,e,worker_id='w1',**args));before_complete=snap(l);completion=cap(lambda:l.complete_action(a,worker_id='w1',event_id=e.event_id));after_complete=snap(l);steps.append({'index':i,'event':asdict(e),'event_args':args,'action_id':a,'before_claim':before,'claim':receipt,'after_claim':after_claim,'mutation':mutation if i==0 else None,'before_submit':before_submit,'submit':submitted,'before_complete':before_complete,'complete':completion,'after_complete':after_complete,'budget':l.budget_snapshot(name)})
 row={'case':name,'inputs':{'policy':pol,'mutation':mutation,'operations':'two distinct hypothetical pathways, local scripted/no network'},'steps':steps,'final':snap(l),'budget':l.budget_snapshot(name)};(d/'input_output.json').write_text(json.dumps(row,indent=2,ensure_ascii=False)+'\n');ROWS.append(row);print(json.dumps({'case':name,'second_claim':steps[1]['claim'],'events':len(row['final']['events']),'commits':len(row['final']['search_commit_records']),'total_budget':row['budget']['run_level']['max_total_search_actions']},ensure_ascii=False),flush=True)
 if mutation=='clean':assert steps[1]['claim']['error']=='SearchBudgetExhausted' and len(row['final']['events'])==1 and len(row['final']['search_commit_records'])==1
 else:assert steps[1]['complete']['returned']['completed'] and len(row['final']['events'])==2 and len(row['final']['search_commit_records'])==2 and row['budget']['run_level']['max_total_search_actions']['used']==1
 l.store.close()
(P/'one_action_chain_observations.json').write_text(json.dumps(ROWS,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'summary':{'cases':2,'network_calls':0,'capture_complete':True}}))
