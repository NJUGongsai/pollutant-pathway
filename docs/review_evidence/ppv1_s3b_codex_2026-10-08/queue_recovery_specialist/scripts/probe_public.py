#!/usr/bin/env python3
"""Independent synthetic S3b public start/resume/queue probe. No provider/network.
Every run has explicit persisted JSON input, child stdout/stderr/return code,
read-only all-table/artifact snapshots; source files are never edited.
"""
from pathlib import Path
import argparse,sys,json,os,sqlite3,subprocess,time,hashlib,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
PY=sys.executable

def dump(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True))
def spec(key='B',product='CC=O',**kw):
 d={'key':key,'product_smiles':product,'coefficient':1,'transformation_ref':'donor-'+key,'origin_group_key':'donor-'+key,'edits':[{'op':'change_bond_order','atom1':'S_C_2','atom2':'S_O_1','from_order':'single','to_order':'double'}],'donor':{'center_atom_ids':['S_C_2','S_O_1']},'alignment':{'status':'resolved','donor_to_current':{'S_C_2':'S_C_2','S_O_1':'S_O_1'},'ref':'align-A'},'expectation':{'target_smiles':product}}
 d.update(kw);return d

def plan(**kw):
 d={'pools':{'CCO':[spec()]}};d.update(kw);return d

def snapshot(run_dir):
 out={'tables':{},'artifacts':{},'identity':None}
 db=run_dir/'pollutant.sqlite'
 if db.exists():
  con=sqlite3.connect(f'file:{db}?mode=ro',uri=True);con.row_factory=sqlite3.Row
  for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
   rows=[]
   for row in con.execute('SELECT * FROM "'+r[0]+'"'):
    v=dict(row)
    for key,value in list(v.items()):
     if isinstance(value,str) and value[:1] in '[{':
      try:v[key]=json.loads(value)
      except ValueError:pass
    rows.append(v)
   out['tables'][r[0]]=rows
  con.close()
 for p in sorted((run_dir/'results').rglob('*.json')) if (run_dir/'results').exists() else []:
  try:v=json.loads(p.read_text())
  except Exception:v={'unparseable':True}
  out['artifacts'][str(p.relative_to(run_dir))]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'content':v}
 if (run_dir/'run_identity.json').exists():out['identity']=json.loads((run_dir/'run_identity.json').read_text())
 return out

def worker(inp):
 from pathway_v43.config import resolve_config
 from pathway_v43.workflow.runner import start_run,resume_run
 from pathway_v43.pollutant import runflow
 from pathway_v43.pollutant.search import SearchCrashInjection,SearchLedger
 from pathway_v43.storage.run_identity import PROFILE_POLLUTANT_PATHWAY_V1
 cfg=resolve_config(v3_code_root=ROOT/'absent_v3',assets_root=ROOT/'absent_assets')
 run_id=inp['run_id'];runs_root=Path(inp['runs_root']);inj=inp.get('injection')
 def hard(tag,details=None):
  print(json.dumps({'hard_kill':tag,'detail':details or {},'pid':os.getpid()},ensure_ascii=False),flush=True);sys.stderr.flush();os._exit(77)
 if inj=='after_transition_enqueued_before_attach':
  orig=runflow.enqueue_scenario_transition
  def f(*a,**k):
   v=orig(*a,**k);hard(inj,v)
  runflow.enqueue_scenario_transition=f
 if inj=='after_transition_followups_before_complete':
  orig=runflow.enqueue_coproduct_followups
  def f(*a,**k):
   v=orig(*a,**k)
   if str(k.get('context_ref')) != inp.get('old_context_ref',''):
    hard(inj,v)
   return v
  runflow.enqueue_coproduct_followups=f
 if inj=='after_two_followups':
  orig=SearchLedger.enqueue_action;count=[0]
  def f(self,*a,**k):
   v=orig(self,*a,**k)
   if k.get('action_kind')=='retrieve' and k.get('source_event_id'):
    count[0]+=1
    if count[0]==2:hard(inj,{'result':v,'n':count[0]})
   return v
  SearchLedger.enqueue_action=f
 if inj=='before_decide_claim':
  orig=SearchLedger.claim_action
  def f(self,action_id,*a,**k):
   row=self.action(action_id)
   if row['action_kind']=='decide':hard(inj,{'action_id':action_id})
   return orig(self,action_id,*a,**k)
  SearchLedger.claim_action=f
 if inp['mode']=='barrier-start':
  barrier=Path(inp['barrier']);barrier.mkdir(exist_ok=True,parents=True)
  (barrier/(inp['worker']+'.ready')).write_text('ready')
  until=time.monotonic()+30
  while not (barrier/'GO').exists():
   if time.monotonic()>until:raise RuntimeError('barrier timeout')
   time.sleep(.02)
 if inp['mode']=='barrier-claim':
  from pathway_v43.pollutant.store import PollutantPathwayStore
  from pathway_v43.storage.artifact_store import ArtifactStore
  db=runs_root/run_id/'pollutant.sqlite';store=PollutantPathwayStore(db);ledger=SearchLedger(store,ArtifactStore(runs_root,run_id),run_id)
  barrier=Path(inp['barrier']);barrier.mkdir(exist_ok=True,parents=True);(barrier/(inp['worker']+'.ready')).write_text('ready')
  until=time.monotonic()+30
  while not (barrier/'GO').exists():
   if time.monotonic()>until:raise RuntimeError('barrier timeout')
   time.sleep(.02)
  result=ledger.claim_action(inp['action_id'],worker_id=inp['worker']);print(json.dumps({'result':result,'pid':os.getpid()},ensure_ascii=False),flush=True);return
 try:
  if inp['mode'] in ('start','barrier-start'):
   out=start_run(config=cfg,runs_root=runs_root,run_id=run_id,smiles=inp.get('smiles','CCO'),max_depth=3,max_expansions=10,max_frontier_width=2,finder=object(),scripted=True,profile=PROFILE_POLLUTANT_PATHWAY_V1,ppv1_plan=inp.get('plan'),profile_policy=inp.get('policy'),crash_after=inp.get('crash_after'))
  else:
   out=resume_run(config=cfg,runs_root=runs_root,run_id=run_id,finder=object(),ppv1_plan=inp.get('plan'),crash_after=inp.get('crash_after'))
  print(json.dumps({'result':out,'pid':os.getpid()},ensure_ascii=False),flush=True)
 except SearchCrashInjection as exc:hard(inp.get('crash_after'),exc.detail)
 except Exception as exc:
  print(json.dumps({'exception':type(exc).__name__,'detail':getattr(exc,'detail',{}),'message':str(exc),'pid':os.getpid()},ensure_ascii=False),flush=True);traceback.print_exc();sys.exit(3)

def launch(label,inp):
 file=ROOT/'inputs'/(label+'.json');dump(file,inp)
 cmd=[PY,'-B',str(Path(__file__).resolve()),'worker',str(file)]
 env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'src')}
 p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,env=env,timeout=90)
 (ROOT/'logs'/(label+'.stdout.txt')).write_text(p.stdout);(ROOT/'logs'/(label+'.stderr.txt')).write_text(p.stderr)
 parsed=None
 for line in p.stdout.splitlines():
  try:parsed=json.loads(line)
  except ValueError:pass
 v={'label':label,'command':cmd,'environment':env,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'parsed':parsed}
 dump(ROOT/'logs'/(label+'.execution.json'),v)
 snap=snapshot(Path(inp['runs_root'])/inp['run_id']);dump(ROOT/'tables'/(label+'.json'),snap)
 return v,snap

def tables(s,n):return s['tables'].get(n,[])
def artifacts(s,name):return [v['content']['payload'] for k,v in s['artifacts'].items() if k.endswith(name+'.json')]
def eventids(s):return [r['event_id'] for r in tables(s,'events')]
def counters(s):
 return {n:len(v) for n,v in s['tables'].items()}
def base(name,p=None,**kw):
 d={'mode':'start','run_id':name,'runs_root':str(ROOT/'synthetic_runs'/'runs'),'plan':p if p is not None else plan()};d.update(kw);return d

OBS=[]
def record(name,check,detail):
 OBS.append({'case':name,'observed_check':bool(check),'detail':detail});print(json.dumps(OBS[-1],ensure_ascii=False),flush=True)

def control_run():
 # Public lawful E01/H04/C06/branch/essential-conflict and true off/0 controls.
 p=plan(pools={'CCO':[spec('B'),spec('C')]})
 v,s=launch('e01',base('e01',p));outs=artifacts(s,'expansion_outcome');unres=[o for o in outs if o.get('outcome',{}).get('detail',{}).get('unresolved_continuation')]
 record('e01_two_independent_alternatives',v['returncode']==0 and len(eventids(s))==2 and len(unres)==2,{'events':eventids(s),'unresolved':unres,'attempts':tables(s,'search_attempts'),'stop':v['parsed']})
 req=[{'key':'oxygen_regime','level':'essential','value':'aerobic','source_refs':['src:synthetic']}]
 for supply in ('missing','supported'):
  p=plan(condition_facts=[{'key':'oxygen_regime','value':'aerobic','status':'known_present','source_ref':'src:synthetic'}],pools={'CCO':[spec(dependencies=[{'dependency_id':'dep-NAD','kind':'cosubstrate_supply','statement':'synthetic cycle','cyclic':True,'initial_supply':supply}],requirements=req)]})
  v,s=launch('h04_'+supply,base('h04_'+supply,p));ctx=artifacts(s,'path_context');withdeps=[c for c in ctx if c.get('dependencies')];reports=artifacts(s,'production_report')
  expected='unresolved' if supply=='missing' else 'supported';record('h04_'+supply,v['returncode']==0 and len(eventids(s))==1 and bool(withdeps) and withdeps[0]['dependencies'][0]['status']==expected,{'contexts':withdeps,'admissions':[r.get('admission') for r in reports],'events':eventids(s)})
 p=plan(condition_facts=[{'key':'oxygen_regime','value':'aerobic','status':'known_present','source_ref':'src:synthetic'}],pools={'CCO':[spec('B',requirements=req),spec('C')]})
 v,s=launch('branch_isolation',base('branch_isolation',p));contexts=artifacts(s,'path_context');record('branch_isolation',v['returncode']==0 and len(eventids(s))==2 and any(c['accumulated_requirements'] for c in contexts) and any(not c['accumulated_requirements'] for c in contexts),{'contexts':contexts,'events':eventids(s)})
 p=plan(condition_facts=[{'key':'oxygen_regime','value':'anaerobic','status':'known_present','source_ref':'src:synthetic'}],pools={'CCO':[spec(requirements=req)]})
 v,s=launch('essential_conflict',base('essential_conflict',p));record('essential_conflict',v['returncode']==0 and not eventids(s) and len(tables(s,'hypotheses'))==1,{'outcomes':artifacts(s,'expansion_outcome'),'counts':counters(s)})
 p=plan(model={'provider_kind':'real','responses':['{}']})
 v,s=launch('real_off_zero',base('real_off_zero',p));requests=tables(s,'model_requests');record('real_off_zero',v['returncode']==0 and not requests and not eventids(s),{'requests':requests,'outcomes':artifacts(s,'expansion_outcome'),'stop':v['parsed']})
 # Separate zero-resource / empty-pool cases (not compound early-stop).
 for tag,pp,policy in [('zero_actions',plan(),{'search_limits':{'max_total_search_actions':0}}),('zero_depth',plan(),{'search_limits':{'max_search_depth':0}}),('empty_pool',{'pools':{}},None),('nonzero',plan(),None)]:
  v,s=launch(tag,base(tag,pp,policy=policy));record(tag,v['returncode']==0 and (len(eventids(s))==1 if tag=='nonzero' else not eventids(s)),{'stop':v['parsed'],'counts':counters(s),'reservations':tables(s,'budget_reservations')})

 # Four supported hard kills are independent process start and new process public resume.
 for boundary in ('after_claim','after_request_registered','after_bundle_written','after_event_submitted'):
  p=plan()
  if boundary=='after_request_registered':p['model']={'provider_kind':'scripted','responses':['{"proposals": "not-a-list"}']}
  name='crash_'+boundary
  first,s0=launch(name+'_start',base(name,p,crash_after=boundary))
  second,s1=launch(name+'_resume',dict(base(name,p),mode='resume'))
  before_requests=tables(s0,'model_requests');after_requests=tables(s1,'model_requests')
  check=first['returncode']==77 and second['returncode']==0
  if boundary=='after_request_registered':check=check and len(after_requests)==len(before_requests)==1 and all(r['network_request_count']==0 for r in after_requests) and bool(second['parsed']['result']['recovery']['pending_requests'])
  else:check=check and len(eventids(s1))==1 and len(tables(s1,'search_commit_records'))==4
  record(name,check,{'first_pid':first['parsed']['pid'],'second_pid':second['parsed']['pid'],'initial_counts':counters(s0),'after_counts':counters(s1),'requests_before':before_requests,'requests_after':after_requests,'resume':second['parsed']})
  third,s2=launch(name+'_again',dict(base(name,p),mode='resume'))
  record(name+'_idempotent_again',third['returncode']==0 and counters(s1)==counters(s2),{'before':counters(s1),'after':counters(s2),'resume':third['parsed']})

 # Persisted pool/task policy input recovery: same control, empty and changed plan.
 for variant in ('same','omitted','changed','decide_changed'):
  name='frozen_plan_'+variant;p=plan();inj={'crash_after':'after_claim'} if variant!='decide_changed' else {'injection':'before_decide_claim'}
  first,s0=launch(name+'_start',base(name,p,**inj))
  rp=p if variant=='same' else (None if variant=='omitted' else plan(pools={'CCO':[spec('X')]}))
  inp=dict(base(name,rp),mode='resume')
  if variant=='omitted':inp.pop('plan',None)
  second,s1=launch(name+'_resume',inp)
  old=next(r for r in tables(s0,'search_actions') if r['action_kind']=='retrieve');new=next(r for r in tables(s1,'search_actions') if r['action_id']==old['action_id'])
  changed=old['task_key']==new['task_key'] and (variant=='omitted' and not eventids(s1) or variant in ('changed','decide_changed') and bool(eventids(s1)))
  record(name,(second['returncode']==0 and len(eventids(s1))==1) if variant=='same' else second['returncode']==0 and changed,{'historical_task_key':old['task_key'],'after_same_action_task_key':new['task_key'],'historical_action':old,'new_actions':tables(s1,'search_actions'),'hypotheses':tables(s1,'hypotheses'),'events':tables(s1,'events'),'resume':second['parsed'],'classification':'lawful_control' if variant=='same' else 'contract_gap_observed'})

 # Public model proposals[] consumers: novel from an empty pool and pool abstention.
 novel={'hypothesis_id':'novel:1','proposal_context':{'reference_hypothesis_ids':[],'output_origin':'novel_outside_pool'},'reaction_spec':spec('Novel')}
 for tag,p in [('novel_empty',{'pools':{},'model':{'provider_kind':'scripted','responses':[json.dumps({'proposals':[novel]})]}}),('novel_nonempty',plan(model={'provider_kind':'scripted','responses':[json.dumps({'proposals':[novel]})]})),('abstain',plan(model={'provider_kind':'scripted','responses':['{"proposals":[]}']}))]:
  v,s=launch(tag,base(tag,p));record('model_'+tag,v['returncode']==0,{'events':eventids(s),'hypotheses':tables(s,'hypotheses'),'requests':tables(s,'model_requests'),'outcomes':artifacts(s,'expansion_outcome'),'stop':v['parsed'],'classification':'consumer_evidence'})

 # Transition B4 public input: normal, exact registered-before-followup gap, and B4 prequeue gap.
 tp=plan(scenario_transitions=[{'after_hypothesis_key':'B','transition':{'source_ref':'user:switch','new_phase_id':'phase-1','new_scenario_ref':'scenario-new'}}])
 for variant in ('normal','after_transition_enqueued_before_attach','after_event_submitted'):
  name='transition_'+variant
  kwargs={} if variant=='normal' else ({'crash_after':variant} if variant=='after_event_submitted' else {'injection':variant})
  first,s0=launch(name+'_start',base(name,tp,**kwargs))
  if variant!='normal':second,s1=launch(name+'_resume',dict(base(name,tp),mode='resume'))
  else:second,s1=first,s0
  trans=[r for r in tables(s1,'search_actions') if r['action_kind']=='scenario_transition'];fu=[r for r in tables(s1,'search_actions') if r['action_kind']=='retrieve' and r['payload'].get('source_event_id')];cs=artifacts(s1,'path_context');phase_byid={c['context_id']:c['phase_id'] for c in cs};fu_phases=[phase_byid.get(r['context_ref']) for r in fu]
  record(name,second['returncode']==0,{'start':first['parsed'],'before':counters(s0),'after':counters(s1),'transition_actions':trans,'followup_actions':fu,'followup_phases':fu_phases,'contexts':cs,'classification':'lawful_control' if variant=='normal' else 'B4_contract_gap_observed','resume':second['parsed']})

 # B4 partially enqueued multi-product followup: 3 product identities, kill after second enqueue.
 pp=plan(pools={'CCO':[spec(coproducts=['[H][H]','O'])]})
 policy={'search_limits':{'max_product_expansion_width':3,'max_total_search_actions':20}}
 for variant in ('normal','after_two_followups'):
  name='three_products_'+variant
  first,s0=launch(name+'_start',base(name,pp,policy=policy,**({} if variant=='normal' else {'injection':variant})))
  if variant!='normal':second,s1=launch(name+'_resume',dict(base(name,pp),mode='resume'))
  else:second,s1=first,s0
  products=[p['state_ref'] for e in tables(s1,'events') for p in e['payload']['participants'] if p['side']=='product'];fu=[r for r in tables(s1,'search_actions') if r['action_kind']=='retrieve' and r['payload'].get('source_event_id')]
  record(name,second['returncode']==0,{'start':first['parsed'],'products':products,'followup_refs':[r['subject_ref'] for r in fu],'missing_product_followups':sorted(set(products)-{r['subject_ref'] for r in fu}),'before':counters(s0),'after':counters(s1),'stop':second['parsed'],'classification':'lawful_control' if variant=='normal' else 'B4_contract_gap_observed'})

 # H07/H08 public resume negative controls and original evidence preservation.
 for tag in ('artifact_hash_bad','artifact_json_bad','event_ledger_bad'):
  name='public_'+tag;boundary='after_bundle_written' if tag!='event_ledger_bad' else 'after_event_submitted'
  first,s0=launch(name+'_start',base(name,plan(),crash_after=boundary));run=Path(base(name)['runs_root'])/name
  if tag.startswith('artifact_'):
   ps=list((run/'results').rglob('*.json'));bundles=[p for p in ps if 'bundle' in p.name]
   target=bundles[0];before=target.read_bytes()
   if tag=='artifact_json_bad':target.write_text('{not-json')
   else:
    data=json.loads(target.read_text());data['payload']['review_marker']='tampered';target.write_text(json.dumps(data))
   tampered=target.read_bytes();mutation={'path':str(target.relative_to(run)),'original_sha':hashlib.sha256(before).hexdigest(),'tampered_sha':hashlib.sha256(tampered).hexdigest()}
  else:
   db=run/'pollutant.sqlite';conn=sqlite3.connect(db);event=conn.execute('SELECT event_id FROM events').fetchone()[0];conn.execute('UPDATE events SET context_hash=? WHERE event_id=?',('ctx-forged',event));conn.commit();conn.close();mutation={'table':'events','field':'context_hash','value':'ctx-forged','event_id':event};target=None
  sm=snapshot(run);dump(ROOT/'tables'/(name+'_mutated.json'),sm)
  second,s1=launch(name+'_resume',dict(base(name),mode='resume'))
  preserve=(target.read_bytes()==tampered) if target is not None else tables(sm,'events')==tables(s1,'events')
  record(name,second['returncode']==3 and preserve and counters(sm)==counters(s1),{'mutation':mutation,'error':second['parsed'],'before':counters(sm),'after':counters(s1),'evidence_preserved':preserve})

 dump(ROOT/'observations.json',OBS)

def parallel_controls():
 # Public start barrier and actual same-action ledger claim barrier, explicit independent PIDs.
 for kind in ('start','claim'):
  name='barrier_'+kind;runs=ROOT/'synthetic_runs'/'runs';barrier=ROOT/'synthetic_runs'/(name+'_barrier');inputs=[]
  if kind=='claim':
   launch(name+'_setup',base(name,plan(),crash_after='after_claim'));s=snapshot(runs/name);row=tables(s,'search_actions')[0]
   # Leave same legitimate pending action, unreserved: fresh queue via public ledger; no SQL owner edits.
   from pathway_v43.pollutant.store import PollutantPathwayStore
   from pathway_v43.pollutant.search import SearchLedger,search_policy_version
   from pathway_v43.storage.artifact_store import ArtifactStore
   store=PollutantPathwayStore(runs/name/'pollutant.sqlite');ledger=SearchLedger(store,ArtifactStore(runs,name),name)
   action=ledger.enqueue_action(run_id=name,parent_path_id='independent_parent',context_ref=row['context_ref'],subject_ref='independent_subject',action_kind='decide',parent_search_revision=0,policy_version=search_policy_version(),payload={'task_key':'barrier-decision'})
   action_id=action['action_id']
  procs=[]
  for w in ('first','second'):
   inp=base(name,plan(),mode='barrier-'+kind,barrier=str(barrier),worker=w)
   if kind=='claim':inp['action_id']=action_id
   f=ROOT/'inputs'/(name+'_'+w+'.json');dump(f,inp);cmd=[PY,'-B',str(Path(__file__).resolve()),'worker',str(f)];env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'src')}
   procs.append((w,cmd,env,subprocess.Popen(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)))
  until=time.monotonic()+40
  while time.monotonic()<until:
   if all((barrier/(w+'.ready')).exists() for w,_,_,_ in procs):barrier.joinpath('GO').write_text('go');break
   time.sleep(.02)
  else:raise RuntimeError('barrier readiness timeout')
  results=[]
  for w,cmd,env,p in procs:
   so,se=p.communicate(timeout=90);label=name+'_'+w;(ROOT/'logs'/(label+'.stdout.txt')).write_text(so);(ROOT/'logs'/(label+'.stderr.txt')).write_text(se)
   parsed=json.loads(so.strip().splitlines()[-1]);v={'command':cmd,'environment':env,'returncode':p.returncode,'stdout':so,'stderr':se,'parsed':parsed};dump(ROOT/'logs'/(label+'.execution.json'),v);results.append(v)
  s=snapshot(runs/name);dump(ROOT/'tables'/(name+'_final.json'),s)
  if kind=='start':check=sorted(r['returncode'] for r in results)==[0,3] and len(eventids(s))==1
  else:check=len([r for r in results if r['returncode']==0 and r['parsed'].get('result',{}).get('claimed')])==1
  record(name,check,{'results':results,'counts':counters(s),'reservations':tables(s,'budget_reservations'),'actions':tables(s,'search_actions')})
 dump(ROOT/'observations.json',OBS)

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='worker':worker(json.loads(Path(sys.argv[2]).read_text()))
 else:
  try:control_run();parallel_controls()
  finally:dump(ROOT/'observations.json',OBS)
