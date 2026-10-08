#!/usr/bin/env python3
from pathlib import Path
from dataclasses import asdict
import sys,json
P=Path(__file__).resolve().parent;sys.path[:0]=[str(P/'repo/src'),str(P/'repo/tests')]
from s3a_worker import make_fixture
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.search import SearchLedger,search_policy_version,commit_search_event
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.storage.artifact_store import ArtifactStore
TABLES=['meta','states','state_appearances','hypotheses','events','report_projections','expansion_plans','event_appearance_links','search_runs','search_actions','search_attempts','budget_reservations','model_requests','search_commit_records']
ROOT=P/'defer_control_cases';ROOT.mkdir(exist_ok=False);ROWS=[]
def snap(l):return {t:[dict(x) for x in l.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in TABLES}
def cap(fn):
 try:return {'returned':fn()}
 except Exception as e:return {'error':type(e).__name__,'detail':getattr(e,'detail',{}),'text':str(e)}
def mk(name):
 d=ROOT/name;d.mkdir();l=SearchLedger(PollutantPathwayStore(d/'run.sqlite'),ArtifactStore(d/'runs',name),name);pol=build_profile_identity_block();l.register_search_run(name,pol);sub,prod,h,e,args=make_fixture(name,'p1','k1','ctx1');return d,l,pol,h,e,args

def enqueue(l,r,h,rev=0,tk='tk1',kind='expand_hypothesis'):
 return l.enqueue_action(run_id=r,parent_path_id='p1',context_ref='ctx1',subject_ref=h,action_kind=kind,depth=1,parent_search_revision=rev,policy_version=search_policy_version(),payload={'task_key':tk})['action_id']
def emit(d,row):
 (d/'input_output.json').write_text(json.dumps(row,indent=2,ensure_ascii=False)+'\n');ROWS.append(row);print(json.dumps({'case':row['case'],'result':row.get('result'),'changed':row.get('before')!=row.get('after')},ensure_ascii=False),flush=True)
for kind in ['clean','reservation_delete','reservation_units_zero','reservation_status_unknown','reservation_scope_wrong','alternative_subject_wrong','attempt_delete','attempt_abandoned','attempt_hypothesis_wrong','attempt_task_wrong']:
 name='defer_row__'+kind;d,l,pol,h,e,args=mk(name);aid=enqueue(l,name,h.hypothesis_id);rec=l.claim_action(aid,worker_id='w1');original=snap(l);rid=l.conn.execute("SELECT reservation_id FROM budget_reservations WHERE action_id=? AND limit_key='max_total_search_actions'",(aid,)).fetchone()[0];att=rec['attempt_refs'][0]
 if kind=='reservation_delete':l.conn.execute('DELETE FROM budget_reservations WHERE reservation_id=?',(rid,))
 elif kind=='reservation_units_zero':l.conn.execute('UPDATE budget_reservations SET units=0 WHERE reservation_id=?',(rid,))
 elif kind=='reservation_status_unknown':l.conn.execute("UPDATE budget_reservations SET status='invalid-status' WHERE reservation_id=?",(rid,))
 elif kind=='reservation_scope_wrong':l.conn.execute("UPDATE budget_reservations SET scope='wrong-scope' WHERE reservation_id=?",(rid,))
 elif kind=='alternative_subject_wrong':l.conn.execute("UPDATE budget_reservations SET subject='other-hyp' WHERE action_id=? AND limit_key='max_alternative_hypotheses_per_parent'",(aid,))
 elif kind=='attempt_delete':l.conn.execute('DELETE FROM search_attempts WHERE expansion_attempt_id=?',(att,))
 elif kind=='attempt_abandoned':l.conn.execute("UPDATE search_attempts SET status='abandoned' WHERE expansion_attempt_id=?",(att,))
 elif kind=='attempt_hypothesis_wrong':l.conn.execute("UPDATE search_attempts SET hypothesis_id='other-hyp' WHERE expansion_attempt_id=?",(att,))
 elif kind=='attempt_task_wrong':l.conn.execute("UPDATE search_attempts SET task_key='other-task' WHERE expansion_attempt_id=?",(att,))
 l.conn.commit();before=snap(l);result=cap(lambda:l.defer_action(aid,worker_id='w1',reason='no_new_information'));after=snap(l);emit(d,{'case':name,'inputs':{'policy':pol,'receipt':rec,'event':asdict(e),'args':args,'mutation':kind},'original':original,'before':before,'result':result,'after':after,'budget_after':cap(lambda:l.budget_snapshot(name))})
 if kind=='clean':assert result['returned']['deferred'] and before!=after
 else:assert result.get('error')=='SearchIntegrityError' and before==after
 l.store.close()
name='legal_shared_alternative';d,l,pol,h,e,args=mk(name);a1=enqueue(l,name,h.hypothesis_id);rec1=l.claim_action(a1,worker_id='w1');first=commit_search_event(l,a1,e,worker_id='w1',attempt_id=rec1['attempt_refs'][0],task_key='tk1',**args);a2=enqueue(l,name,h.hypothesis_id,rev=1,tk='tk2');rec2=l.claim_action(a2,worker_id='w1');before=snap(l);submit=l.submit_action_event(a2,e,worker_id='w1',**args);result=cap(lambda:l.complete_action(a2,worker_id='w1',event_id=e.event_id));after=snap(l);recovery=cap(lambda:l.recover_run(name,policy_block=pol));budget=l.budget_snapshot(name);emit(d,{'case':name,'inputs':{'policy':pol,'receipt1':rec1,'receipt2':rec2,'event':asdict(e),'args':args},'first':first,'submit':submit,'before':before,'result':result,'after':after,'recovery':recovery,'budget':budget});assert result['returned']['completed'] and budget['scoped']['max_alternative_hypotheses_per_parent']['p1']['used']==1 and budget['run_level']['max_total_search_actions']['used']==2 and recovery['returned'];l.store.close()
for kind in ['decide_empty_attempt','expand_failed_attempt']:
 name='legal_'+kind;d,l,pol,h,e,args=mk(name);a=enqueue(l,name,h.hypothesis_id,kind='decide' if kind=='decide_empty_attempt' else 'expand_hypothesis');rec=l.claim_action(a,worker_id='w1');before=snap(l);result=cap(lambda:l.complete_action(a,worker_id='w1',outcome_kind='outcome_recorded',outcome_ref='honest-no-event',attempt_status='failed'));after=snap(l);recover=cap(lambda:l.recover_run(name,policy_block=pol));second=cap(lambda:l.complete_action(a,worker_id='w1',outcome_kind='outcome_recorded',outcome_ref='honest-no-event',attempt_status='failed'));emit(d,{'case':name,'inputs':{'policy':pol,'receipt':rec,'outcome_kind':'outcome_recorded','outcome_ref':'honest-no-event','attempt_status':'failed'},'before':before,'result':result,'after':after,'recover':recover,'second':second,'after_second':snap(l)});assert result['returned']['completed'] and recover['returned'] and second['returned']['unchanged'] and after==snap(l);l.store.close()
(P/'defer_control_observations.json').write_text(json.dumps(ROWS,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'summary':{'cases':len(ROWS),'all_current_contract_assertions_passed':True,'network_calls':0}}))
