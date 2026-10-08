#!/usr/bin/env python3
"""R2 S3A-02 necessary-reference subset and common defer guard; synthetic only."""
from pathlib import Path
from dataclasses import asdict
import json,sys,hashlib
P=Path(__file__).resolve().parent;sys.path[:0]=[str(P/'repo/src'),str(P/'repo/tests')]
from s3a_worker import make_fixture
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.search import SearchLedger,search_policy_version
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.storage.artifact_store import ArtifactStore
TABLES=['meta','states','state_appearances','hypotheses','events','report_projections','expansion_plans','event_appearance_links','search_runs','search_actions','search_attempts','budget_reservations','model_requests','search_commit_records']
ROOT=P/'necessary_reference_cases';ROOT.mkdir(exist_ok=False);ROWS=[]
def snap(l):return {t:[dict(x) for x in l.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in TABLES}
def cap(fn):
 try:return {'returned':fn()}
 except Exception as e:return {'error':type(e).__name__,'detail':getattr(e,'detail',{}),'text':str(e)}
def mk(name):
 d=ROOT/name;d.mkdir();l=SearchLedger(PollutantPathwayStore(d/'run.sqlite'),ArtifactStore(d/'runs',name),name);pol=build_profile_identity_block();l.register_search_run(name,pol);sub,prod,h,e,args=make_fixture(name,'p1','k1','ctx1')
 aid=l.enqueue_action(run_id=name,parent_path_id='p1',context_ref='ctx1',subject_ref=h.hypothesis_id,action_kind='expand_hypothesis',depth=1,policy_version=search_policy_version(),payload={'task_key':'tk1'})['action_id'];rec=l.claim_action(aid,worker_id='w1');return d,l,pol,e,args,aid,rec
for phase in ['first_complete','B4_recover','B1_recover','B3_recover','done_recover','done_claim','done_complete','done_submit','defer']:
 for mutation in ['clean','remove_ref_only','remove_ref_and_row']:
  keys=['max_total_search_actions'] if mutation=='clean' else ['max_total_search_actions','max_alternative_hypotheses_per_parent','max_attempts_per_hypothesis']
  for key in keys:
   name=phase+'__'+mutation+'__'+key;d,l,pol,e,args,aid,rec=mk(name);artifact=None;originalartifact=None
   if phase=='B3_recover':
    l.write_commit_bundle(action_id=aid,attempt_id=rec['attempt_refs'][0],event=e,task_key='tk1',**args);artifact=l.artifact_store._path('tk1','search_commit_bundle');originalartifact=artifact.read_bytes()
   elif phase not in ['B1_recover','defer']:l.submit_action_event(aid,e,worker_id='w1',**args)
   if phase.startswith('done_'):l.complete_action(aid,worker_id='w1',event_id=e.event_id)
   original=snap(l);rid=l.conn.execute('SELECT reservation_id FROM budget_reservations WHERE action_id=? AND limit_key=?',(aid,key)).fetchone()[0]
   if mutation!='clean':
    refs=json.loads(l.conn.execute('SELECT budget_reservation_ref FROM search_actions WHERE action_id=?',(aid,)).fetchone()[0]);refs.remove(rid);l.conn.execute('UPDATE search_actions SET budget_reservation_ref=? WHERE action_id=?',(json.dumps(refs),aid))
    if mutation=='remove_ref_and_row':l.conn.execute('DELETE FROM budget_reservations WHERE reservation_id=?',(rid,))
    l.conn.commit()
   before=snap(l);l.store.close();l=SearchLedger(PollutantPathwayStore(d/'run.sqlite'),ArtifactStore(d/'runs',name),name)
   if phase in ['first_complete','done_complete']:fn=lambda:l.complete_action(aid,worker_id='w1',event_id=e.event_id)
   elif phase=='done_claim':fn=lambda:l.claim_action(aid,worker_id='new-worker')
   elif phase=='done_submit':fn=lambda:l.submit_action_event(aid,e,worker_id='w1',**args)
   elif phase=='defer':fn=lambda:l.defer_action(aid,worker_id='w1',reason='no_new_information')
   else:fn=lambda:l.recover_run(name,policy_block=pol)
   result=cap(fn);after=snap(l)
   row={'case':name,'inputs':{'policy':pol,'event':asdict(e),'event_args':args,'action_id':aid,'receipt':rec,'phase':phase,'mutation':mutation,'removed_limit_key':key,'removed_reservation_id':rid},'original':original,'before':before,'result':result,'after':after,'artifact_preserved':True if artifact is None else artifact.read_bytes()==originalartifact,'budget_after':cap(lambda:l.budget_snapshot(name))}
   (d/'input_output.json').write_text(json.dumps(row,indent=2,ensure_ascii=False)+'\n');ROWS.append(row);print(json.dumps({'case':name,'result':result,'changed':before!=after,'events_before':len(before['events']),'events_after':len(after['events']),'commit_before':len(before['search_commit_records']),'commit_after':len(after['search_commit_records'])},ensure_ascii=False),flush=True);l.store.close()
(P/'necessary_reference_observations.json').write_text(json.dumps(ROWS,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'summary':{'cases':len(ROWS),'network_calls':0,'all_cases_captured':True}}))
