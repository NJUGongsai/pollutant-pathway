#!/usr/bin/env python3
"""Supplement only: unmet original barrier capture, planned deferred controls,
public same-action resume concurrency, corrected multi-product fault injection.
Completed public probes are not rerun. Source remains untouched.
"""
import sys,json,os,time,subprocess,sqlite3,hashlib,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import probe_public as p
ROOT=p.ROOT;PY=sys.executable;OBS=[]

def worker(inp):
 from pathway_v43.pollutant.search import SearchLedger
 from pathway_v43.pollutant import runflow,production
 inj=inp.get('supplemental_injection')
 def hard(kind,v=None):
  print(json.dumps({'hard_kill':kind,'detail':v,'pid':os.getpid()}),flush=True);os._exit(77)
 if inj=='after_expand_claim':
  orig=SearchLedger.claim_action
  def claim(self,*a,**kw):
   r=orig(self,*a,**kw)
   if r['action_kind']=='expand_hypothesis':hard(inj,r)
   return r
  SearchLedger.claim_action=claim
 if inj=='after_two_followups':
  orig=SearchLedger.enqueue_action;count=[0]
  def enqueue(self,*a,**kw):
   r=orig(self,*a,**kw)
   if kw.get('action_kind')=='retrieve' and (kw.get('payload') or {}).get('source_event_id'):
    count[0]+=1
    if count[0]==2:hard(inj,{'count':count[0],'result':r})
   return r
  SearchLedger.enqueue_action=enqueue
 if inj=='concurrent_expand':
  b=Path(inp['barrier']);b.mkdir(exist_ok=True,parents=True);orig=runflow._Driver._run_expand;tool=production.execute_atomtool_expansion
  def expansion(self,receipt):
   data={'action_id':receipt['action_id'],'attempt_refs':receipt['attempt_refs'],'claimed_by':self.worker_id,'pid':os.getpid()};p.dump(b/f'{os.getpid()}.ready.json',data);print(json.dumps({'entered_expansion':data}),flush=True)
   until=time.monotonic()+30
   while not (b/'GO').exists():
    if time.monotonic()>until:raise RuntimeError('execution barrier timeout')
    time.sleep(.02)
   return orig(self,receipt)
  def actual_tool(*a,**kw):
   p.dump(b/f'{os.getpid()}.tool_entered.json',{'pid':os.getpid(),'substrate_smiles':kw.get('substrate_smiles'),'tool_inputs':kw.get('tool_inputs')});return tool(*a,**kw)
  runflow._Driver._run_expand=expansion;production.execute_atomtool_expansion=actual_tool
 p.worker(inp)

def launch(label,inp):
 f=ROOT/'inputs'/(label+'.json');p.dump(f,inp);cmd=[PY,'-B',str(Path(__file__).resolve()),'worker',str(f)];env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'src')}
 proc=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,env=env,timeout=90)
 (ROOT/'logs'/(label+'.stdout.txt')).write_text(proc.stdout);(ROOT/'logs'/(label+'.stderr.txt')).write_text(proc.stderr)
 data=None
 for l in proc.stdout.splitlines():
  try:data=json.loads(l)
  except ValueError:pass
 out={'command':cmd,'environment':env,'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'parsed':data};p.dump(ROOT/'logs'/(label+'.execution.json'),out);s=p.snapshot(Path(inp['runs_root'])/inp['run_id']);p.dump(ROOT/'tables'/(label+'.json'),s);return out,s

def record(name,passed,detail):
 OBS.append({'case':name,'observed_check':bool(passed),'detail':detail});print(json.dumps(OBS[-1],ensure_ascii=False),flush=True);p.dump(ROOT/'supplemental_observations.json',OBS)

def run():
 # Carry forward, without rerun, incomplete distinct-worker claim barrier.
 name='barrier_claim';run=ROOT/'synthetic_runs'/'runs'/name;s=p.snapshot(run);p.dump(ROOT/'tables'/'barrier_claim_capture_after_controller_error.json',s)
 claim=[r for r in p.tables(s,'search_actions') if r['payload'].get('task_key')=='barrier-decision'];reservation=[r for r in p.tables(s,'budget_reservations') if r['action_id']==claim[0]['action_id']]
 err=(ROOT/'logs/barrier_claim_first.stderr.txt').read_text();record('barrier_distinct_worker_partial_capture',len(claim)==1 and claim[0]['claimed_by']=='second' and 'already_claimed' in err and len(reservation)==1,{'claim':claim,'reservation':reservation,'first_worker_error':err,'limitation':'Original controller aborted on empty first-worker stdout before capture of second-worker pipe. No complete second-worker output; conclusion limited to durable row + first refusal, not full two-worker execution receipt.'})
 # Correct only prior injector that never fired (its source_event_id is payload field).
 name='three_products_after_two_corrected';pp=p.plan(pools={'CCO':[p.spec(coproducts=['[H][H]','O'])]});policy={'search_limits':{'max_product_expansion_width':3,'max_total_search_actions':20}}
 first,s0=launch(name+'_start',p.base(name,pp,policy=policy,supplemental_injection='after_two_followups'));second,s1=launch(name+'_resume',dict(p.base(name,pp),mode='resume'))
 products=[x['state_ref'] for e in p.tables(s1,'events') for x in e['payload']['participants'] if x['side']=='product'];fu=[r for r in p.tables(s1,'search_actions') if r['action_kind']=='retrieve' and r['payload'].get('source_event_id')];missing=sorted(set(products)-{r['subject_ref'] for r in fu})
 record(name,first['returncode']==77 and second['returncode']==0 and len(products)==3 and len(fu)==2 and len(missing)==1,{'first':first['parsed'],'products':products,'followup_refs':[r['subject_ref'] for r in fu],'missing_product_followups':missing,'before':p.counters(s0),'after':p.counters(s1),'stop':second['parsed'],'classification':'B4_complete-distinct-products_missing'})
 # H06 public resume same action: two actual processes, ownership entered/tool call barrier.
 name='public_concurrent_resume';pp=p.plan();first,s0=launch(name+'_setup',p.base(name,pp,supplemental_injection='after_expand_claim'));b=ROOT/'synthetic_runs'/(name+'_barrier');procs=[]
 for w in ('first','second'):
  inp=dict(p.base(name,pp),mode='resume',supplemental_injection='concurrent_expand',barrier=str(b));f=ROOT/'inputs'/(name+'_'+w+'.json');p.dump(f,inp);cmd=[PY,'-B',str(Path(__file__).resolve()),'worker',str(f)];env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'src')};proc=subprocess.Popen(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env);procs.append((w,cmd,env,proc))
 until=time.monotonic()+20
 while time.monotonic()<until:
  if b.exists() and len(list(b.glob('*.ready.json')))==2:break
  time.sleep(.02)
 ready=[json.loads(x.read_text()) for x in sorted(b.glob('*.ready.json'))] if b.exists() else []
 b.mkdir(exist_ok=True,parents=True);b.joinpath('GO').write_text('go')
 res=[]
 for w,cmd,env,proc in procs:
  so,se=proc.communicate(timeout=90);label=name+'_'+w;(ROOT/'logs'/(label+'.stdout.txt')).write_text(so);(ROOT/'logs'/(label+'.stderr.txt')).write_text(se)
  parsed=[]
  for l in so.splitlines():
   try:parsed.append(json.loads(l))
   except ValueError:pass
  v={'command':cmd,'environment':env,'returncode':proc.returncode,'stdout':so,'stderr':se,'parsed':parsed};p.dump(ROOT/'logs'/(label+'.execution.json'),v);res.append(v)
 s1=p.snapshot(Path(p.base(name)['runs_root'])/name);p.dump(ROOT/'tables'/(name+'_final.json'),s1);tool=[json.loads(x.read_text()) for x in sorted(b.glob('*.tool_entered.json'))]
 record(name,len(ready)==2 and len(tool)==2 and ready[0]['action_id']==ready[1]['action_id'] and ready[0]['attempt_refs']==ready[1]['attempt_refs'],{'first':first['parsed'],'ready_receipts':ready,'actual_tool_entries':tool,'results':res,'before':p.counters(s0),'after':p.counters(s1),'classification':'H06_two_processes_same_action_execution'})
 # E02 public initial search -> public queue API activation -> public resume, not hidden driver helper.
 from pathway_v43.pollutant.store import PollutantPathwayStore
 from pathway_v43.storage.artifact_store import ArtifactStore
 from pathway_v43.pollutant.search import SearchLedger
 from pathway_v43.pollutant.queue import activate_deferred
 name='deferred_public';pp=p.plan(pools={'CCO':[p.spec('B',coproducts=['[H][H]']),p.spec('C'),p.spec('D')]},schedule_budget={'max_select':1});policy={'search_limits':{'max_alternative_hypotheses_per_parent':3,'max_product_expansion_width':1,'max_total_search_actions':20}}
 first,s0=launch(name+'_start',p.base(name,pp,policy=policy));runs=Path(p.base(name)['runs_root']);store=PollutantPathwayStore(runs/name/'pollutant.sqlite');ledger=SearchLedger(store,ArtifactStore(runs,name),name)
 deferred=[r for r in p.tables(s0,'search_actions') if r['status']=='deferred'];a=next(r for r in deferred if r['payload']['deferred_type']=='alternative_reaction_deferred');c=next(r for r in deferred if r['payload']['deferred_type']=='coproduct_deferred')
 operations=[('wrong_type',{'parent_path_id':c['parent_path_id'],'expected_parent_revision':1,'deferred_type':'alternative_reaction_deferred','trigger':'explicit_user'}),('stale_revision',{'parent_path_id':a['parent_path_id'],'expected_parent_revision':5,'deferred_type':'alternative_reaction_deferred','trigger':'explicit_user'}),('wrong_trigger',{'parent_path_id':a['parent_path_id'],'expected_parent_revision':0,'deferred_type':'alternative_reaction_deferred','trigger':'unproven'}),('alternative',{'parent_path_id':a['parent_path_id'],'expected_parent_revision':0,'deferred_type':'alternative_reaction_deferred','trigger':'explicit_user'}),('alternative_again',{'parent_path_id':a['parent_path_id'],'expected_parent_revision':0,'deferred_type':'alternative_reaction_deferred','trigger':'explicit_user'}),('coproduct',{'parent_path_id':c['parent_path_id'],'expected_parent_revision':1,'deferred_type':'coproduct_deferred','trigger':'explicit_user'}),('coproduct_again',{'parent_path_id':c['parent_path_id'],'expected_parent_revision':1,'deferred_type':'coproduct_deferred','trigger':'explicit_user'})]
 observed=[]
 for tag,kw in operations:
  before=p.snapshot(runs/name);out=activate_deferred(ledger,run_id=name,**kw);after=p.snapshot(runs/name);p.dump(ROOT/'tables'/(name+'_'+tag+'_before.json'),before);p.dump(ROOT/'tables'/(name+'_'+tag+'_after.json'),after);v={'tag':tag,'input':kw,'output':out,'before_counts':p.counters(before),'after_counts':p.counters(after)};observed.append(v)
 p.dump(ROOT/'inputs/deferred_operations.json',operations);p.dump(ROOT/'logs/deferred_operations.json',observed)
 second,s1=launch(name+'_resume',dict(p.base(name,pp),mode='resume'));record(name,first['returncode']==0 and second['returncode']==0 and len(p.eventids(s1))==3 and len(observed[3]['output']['activated_ids'])==2 and len(observed[5]['output']['activated_ids'])==1 and not observed[4]['output']['activated_ids'] and not observed[6]['output']['activated_ids'] and observed[1]['output']['unchanged'][0]['reason']=='stale_parent_revision' and observed[2]['output']['conflicts'][0]['kind']=='defer_trigger_mismatch',{'operations':observed,'after':p.counters(s1),'events':p.eventids(s1),'stop':second['parsed']})
 name='deferred_budget';pp=p.plan(pools={'CCO':[p.spec('B'),p.spec('C')]},schedule_budget={'max_select':1});first,s0=launch(name+'_start',p.base(name,pp,policy={'search_limits':{'max_alternative_hypotheses_per_parent':1}}));runs=Path(p.base(name)['runs_root']);store=PollutantPathwayStore(runs/name/'pollutant.sqlite');ledger=SearchLedger(store,ArtifactStore(runs,name),name);a=next(r for r in p.tables(s0,'search_actions') if r['status']=='deferred');out=activate_deferred(ledger,run_id=name,parent_path_id=a['parent_path_id'],expected_parent_revision=0,trigger='explicit_user',deferred_type='alternative_reaction_deferred');s1=p.snapshot(runs/name);p.dump(ROOT/'tables'/(name+'_after_activation.json'),s1);record(name,first['returncode']==0 and not out['activated_ids'] and out['unchanged'][0]['reason']=='budget_exhausted' and p.counters(s0)==p.counters(s1),{'activation':out,'before':p.counters(s0),'after':p.counters(s1),'rows':p.tables(s1,'search_actions')})
 # One bounded format fix is legal but scripted request status never advances.
 from pathway_v43.pollutant.production import prepare_hypothesis
 from pathway_v43.pollutant.chemstate import build_chemical_state
 from pathway_v43.domain.models import stable_id
 name='feedback_valid';sp=p.spec();sub=build_chemical_state('CCO','raw_input',[{'record':'synthetic'}]);h=prepare_hypothesis(sp,parent_path_id=stable_id('spath',name,'root'),substrate_state=sub,transformation_ref='donor-B')['hypothesis'].hypothesis_id
 pp=p.plan(model={'provider_kind':'scripted','responses':['{"proposals": "invalid"}',json.dumps({'proposals':[{'hypothesis_id':h}]})]});policy={'format_feedback_policy':{'max_format_feedback_rounds':1}}
 v,s=launch(name,p.base(name,pp,policy=policy));record(name,v['returncode']==0 and len(p.eventids(s))==1 and len(p.tables(s,'model_requests'))==2,{'requests':p.tables(s,'model_requests'),'outcomes':p.artifacts(s,'expansion_outcome'),'stop':v['parsed'],'classification':'legal_feedback_control_with_pending_status_observation'})

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='worker':worker(json.loads(Path(sys.argv[2]).read_text()))
 else:
  try:run()
  finally:p.dump(ROOT/'supplemental_observations.json',OBS)
