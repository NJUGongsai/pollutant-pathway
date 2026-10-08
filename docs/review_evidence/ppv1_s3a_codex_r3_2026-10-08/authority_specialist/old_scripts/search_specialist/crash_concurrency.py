#!/usr/bin/env python
"""Independent hard-exit B1-B4 and two-process claim barrier; only synthetic."""
import json,subprocess,sys,os,time
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path[:0]=[str(P/'repo/src'),str(P/'repo/tests')]
from s3a_worker import make_fixture
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.search import SearchLedger,search_policy_version,commit_search_event
from pathway_v43.storage.artifact_store import ArtifactStore
ROOT=P/'crash_generated';ROOT.mkdir(exist_ok=False);LOG=[]
def counts(l):
 return {t:l.conn.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['events','search_actions','search_attempts','budget_reservations','search_commit_records','model_requests']}
def rows(l):
 return {t:[dict(r) for r in l.conn.execute('SELECT * FROM '+t)] for t in ['events','search_actions','search_attempts','budget_reservations','search_commit_records','model_requests']}
def open_l(d,r):return SearchLedger(PollutantPathwayStore(d/'run.sqlite'),ArtifactStore(d/'runs',r),r)
def init(r):
 d=ROOT/r;d.mkdir();l=open_l(d,r);pol=build_profile_identity_block();l.register_search_run(r,pol);_,_,h,e,args=make_fixture(r,'p1','k1','ctx1');a=l.enqueue_action(run_id=r,parent_path_id='p1',context_ref='ctx1',subject_ref=h.hypothesis_id,action_kind='expand_hypothesis',policy_version=search_policy_version(),payload={'task_key':'tk1','frozen_pool_digest':'pool'},depth=1)['action_id'];l.store.close();return d,a,pol,h,e,args
def cmd(mode,d,r,a,w='w1'):
 return [sys.executable,'-B',str(P/'repo/tests/s3a_worker.py'),mode,'--db',str(d/'run.sqlite'),'--runs-root',str(d/'runs'),'--run-id',r,'--action-id',a,'--worker',w,'--task-key','tk1']
def parsed(txt):
 return [json.loads(x) for x in txt.splitlines() if x.startswith('{')]
ENV=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');CMD=[]
for mode,b in [('claim-exit','B1'),('request-exit','B2'),('bundle-exit','B3'),('submit-exit','B4')]:
 r='hard_'+b;d,a,pol,h,e,args=init(r);argv=cmd(mode,d,r,a);start=time.monotonic();p=subprocess.run(argv,cwd=P/'repo',env=ENV,text=True,capture_output=True,timeout=60);info={'argv':argv,'cwd':str(P/'repo'),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'elapsed_seconds':time.monotonic()-start};CMD.append(info);assert p.returncode==1
 l=open_l(d,r);before=rows(l);bs=l.budget_snapshot(r);first=l.recover_run(r,policy_block=pol);afterfirst=rows(l)
 if b=='B1':
  assert counts(l)=={'events':0,'search_actions':1,'search_attempts':1,'budget_reservations':3,'search_commit_records':0,'model_requests':0};rec=l.claim_action(a,worker_id='w1');assert rec['reason']=='reclaimed_by_owner';commit_search_event(l,a,e,worker_id='w1',**args)
 elif b=='B2':
  assert len(first['pending_requests'])==1 and counts(l)['model_requests']==1;assert first['pending_requests'][0]['network_request_count']==0;req=first['pending_requests'][0]['request_id'];attempt=l.action(a)['attempt_refs'][0];retry=l.register_model_request(run_id=r,action_id=a,attempt_id=attempt,provider_kind='scripted',request_key='explicit-retry',retry_of=req,payload={'explicit':True});assert retry['registered'] and counts(l)['model_requests']==2
 else:
  assert counts(l)['events']==1 and counts(l)['search_commit_records']==1 and l.action(a)['status']=='done'
 second=l.recover_run(r,policy_block=pol);aftersecond=rows(l);assert counts(l)['search_attempts']==1 and counts(l)['budget_reservations']==3
 row={'case':b,'input':{'policy':pol,'event':vars(e),'submit_args':args,'worker_command':info},'output':{'rows_before':before,'first_recover':first,'rows_after_first':afterfirst,'second_recover':second,'rows_after_second':aftersecond,'budget_before':bs,'budget_after':l.budget_snapshot(r)},'assertion':'hard exit observed; original attempt/reservations retained; event/request semantics as boundary'};LOG.append(row);print(json.dumps(row,ensure_ascii=False),flush=True);l.store.close()
# Two independent processes simultaneous claim via worker's ready-file/GO barrier.
r='barrier_process';d,a,pol,h,e,args=init(r);bar=d/'barrier';bar.mkdir();procs=[]
for w in ['worker_A','worker_B']:
 argv=cmd('barrier-claim',d,r,a,w)+['--barrier-dir',str(bar),'--n-workers','2','--out-json',str(d/(w+'.json'))];procs.append((argv,subprocess.Popen(argv,cwd=P/'repo',env=ENV,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)))
deadline=time.monotonic()+50
while len(list(bar.glob('*.ready')))<2:
 if time.monotonic()>deadline:raise RuntimeError('two workers failed to reach ready barrier')
 time.sleep(0.01)
(bar/'GO').write_text('go\n')
workers=[]
for argv,p in procs:
 stdout,stderr=p.communicate(timeout=60);info={'argv':argv,'cwd':str(P/'repo'),'returncode':p.returncode,'stdout':stdout,'stderr':stderr,'decoded':parsed(stdout)};workers.append(info);CMD.append(info)
l=open_l(d,r);state=rows(l);assert counts(l)=={'events':0,'search_actions':1,'search_attempts':1,'budget_reservations':3,'search_commit_records':0,'model_requests':0};wins=sum(bool(x['decoded'][-1].get('claimed')) for x in workers);assert wins==1
row={'case':'H06_process_barrier','input':{'policy':pol,'same_action':a,'barrier_protocol':'two ready files then GO gate inside original worker'},'output':{'workers':workers,'rows':state,'counts':counts(l),'claim_winners':wins},'assertion':'one process winner, one already_claimed; attempts/requests/events/reservations not duplicated'};LOG.append(row);print(json.dumps(row,ensure_ascii=False));l.store.close()
(P/'crash_commands.json').write_text(json.dumps(CMD,ensure_ascii=False,indent=2)+'\n');(P/'crash_observations.json').write_text(json.dumps(LOG,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'summary':{'cases':len(LOG),'worker_processes':6,'hard_exits':4,'all_observed_assertions':'passed','network_request_count':0}}))
