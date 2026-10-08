#!/usr/bin/env python3
import sys,json,os,time,subprocess,sqlite3,hashlib,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import probe_public as p
import probe_supplemental as s
ROOT=p.ROOT;OBS=[];PY=sys.executable

def record(name,check,detail):
 d={'case':name,'current_contract_observed':bool(check),'detail':detail};OBS.append(d);p.dump(ROOT/'observations_r2.json',OBS);print(json.dumps({'case':name,'current_contract_observed':bool(check)},ensure_ascii=False),flush=True)

def run_resume(name,pp,**kw):return p.launch(name+'_resume',dict(p.base(name,pp),mode='resume',**kw))

def main():
 for boundary in ('after_claim','after_request_registered','after_bundle_written','after_event_submitted'):
  pp=p.plan();name='old_crash_'+boundary
  if boundary=='after_request_registered':pp['model']={'provider_kind':'scripted','responses':['{"proposals": "not-a-list"}']}
  a,b=p.launch(name+'_start',p.base(name,pp,crash_after=boundary));c,d=run_resume(name,pp);e,f=p.launch(name+'_again',dict(p.base(name,pp),mode='resume'))
  record(name,a['returncode']==77 and c['returncode']==0 and e['returncode']==0 and p.counters(d)==p.counters(f) and (len(p.tables(d,'model_requests'))==1 if boundary=='after_request_registered' else len(p.eventids(d))==1),{'before':p.counters(b),'after':p.counters(d),'again':p.counters(f),'start':a['parsed'],'resume':c['parsed'],'reservations_before':p.tables(b,'budget_reservations'),'reservations_after':p.tables(d,'budget_reservations'),'attempts_before':p.tables(b,'search_attempts'),'attempts_after':p.tables(d,'search_attempts')})
 for variant in ('same','omitted','changed','decide_changed'):
  name='frozen_plan_'+variant;pp=p.plan();kw={'crash_after':'after_claim'} if variant!='decide_changed' else {'injection':'before_decide_claim'}
  a,b=p.launch(name+'_start',p.base(name,pp,**kw));rp=pp if variant=='same' else (None if variant=='omitted' else p.plan(pools={'CCO':[p.spec('X')]}));inp=dict(p.base(name,rp),mode='resume')
  if variant=='omitted':inp.pop('plan',None)
  c,d=p.launch(name+'_resume',inp);ok=(c['returncode']==0 and len(p.eventids(d))==1) if variant in ('same','omitted') else (c['returncode']==3 and c['parsed'].get('detail',{}).get('kind')=='frozen_plan_mismatch' and b['tables']==d['tables'])
  record(name,ok,{'before':p.counters(b),'after':p.counters(d),'resume':c['parsed'],'unchanged_tables':b['tables']==d['tables'],'hypotheses':p.tables(d,'hypotheses')})
 for tag in ('artifact_hash_bad','artifact_json_bad','event_ledger_bad','reservation_missing'):
  name='public_'+tag;pp=p.plan();boundary='after_event_submitted' if tag=='event_ledger_bad' else 'after_bundle_written';a,b=p.launch(name+'_start',p.base(name,pp,crash_after=boundary));run=Path(p.base(name)['runs_root'])/name;target=None
  if tag.startswith('artifact_'):
   target=next((run/'results').rglob('search_commit_bundle.json'));before=target.read_bytes()
   if tag=='artifact_json_bad':target.write_text('{not-json')
   else:
    data=json.loads(before);data['payload']['review_marker']='tampered';target.write_text(json.dumps(data))
   bad=target.read_bytes();mutation={'path':str(target.relative_to(run)),'old_sha':hashlib.sha256(before).hexdigest(),'bad_sha':hashlib.sha256(bad).hexdigest()}
  else:
   con=sqlite3.connect(run/'pollutant.sqlite')
   if tag=='event_ledger_bad':eid=con.execute('SELECT event_id FROM events').fetchone()[0];con.execute('UPDATE events SET context_hash=? WHERE event_id=?',('ctx-forged',eid));mutation={'table':'events','context_hash':'ctx-forged','event_id':eid}
   else:
    aid=con.execute("SELECT action_id FROM search_actions WHERE action_kind='expand_hypothesis'").fetchone()[0];rid=con.execute('SELECT reservation_id FROM budget_reservations WHERE action_id=? LIMIT 1',(aid,)).fetchone()[0];con.execute('DELETE FROM budget_reservations WHERE reservation_id=?',(rid,));mutation={'table':'budget_reservations','deleted_reservation_id':rid,'action_id':aid}
   con.commit();con.close()
  sm=p.snapshot(run);p.dump(ROOT/'tables'/(name+'_mutated.json'),sm);c,d=run_resume(name,pp)
  preserve=(target.read_bytes()==bad) if target else sm['tables']==d['tables'];blocked=[r for r in p.tables(d,'search_actions') if r['status']=='blocked']
  ok=(c['returncode']==0 and not p.eventids(d) and len(p.tables(d,'search_commit_records'))==2 and len(blocked)==1 and preserve) if target else c['returncode']==3 and preserve
  record(name,ok,{'mutation':mutation,'before':p.counters(sm),'after':p.counters(d),'resume':c['parsed'],'blocked':blocked,'evidence_preserved':preserve})
 # Current boundary: altered frozen plan wrapper with valid own hashes, original action ledger left untouched.
 for boundary in ('after_bundle_written','after_event_submitted'):
  name='self_consistent_replaced_plan_'+boundary;pp=p.plan();a,b=p.launch(name+'_start',p.base(name,pp,crash_after=boundary));run=Path(p.base(name)['runs_root'])/name;target=run/'results/run-plan/frozen_plan.json';before=target.read_bytes();data=json.loads(before)
  from pathway_v43.domain.models import content_hash
  newp=p.plan(scenario_transitions=[{'after_hypothesis_key':'B','transition':{'source_ref':'injected:changed-plan','new_phase_id':'phase-injected','new_scenario_ref':'scenario-injected'}}]);data['payload']['plan']=newp;data['payload']['plan_digest']=content_hash(newp);data['payload_hash']=content_hash(data['payload']);target.write_text(json.dumps(data));p.dump(ROOT/'inputs'/(name+'_mutation.json'),{'before_envelope':json.loads(before),'new_envelope':data,'reason':'Only frozen artifact changed; root task plan_digest, run identity, ledger and event remain original. Recomputed local wrapper hashes to test content source binding.'});sm=p.snapshot(run);p.dump(ROOT/'tables'/(name+'_mutated.json'),sm)
  inp=dict(p.base(name,pp),mode='resume');inp.pop('plan');c,d=p.launch(name+'_resume',inp);trans=[r for r in p.tables(d,'search_actions') if r['action_kind']=='scenario_transition'];root=next(r for r in p.tables(d,'search_actions') if r['action_kind']=='retrieve' and not r['payload'].get('source_event_id'))
  record(name,c['returncode']==3 and sm['tables']==d['tables'],{'resume':c['parsed'],'root_frozen_digest':root['payload']['plan_digest'],'new_frozen_digest':data['payload']['plan_digest'],'transition_actions':trans,'before':p.counters(sm),'after':p.counters(d),'unchanged_tables':sm['tables']==d['tables']})
 # Transition 0/queued/after-followups and repeated all-complete controls.
 tp=p.plan(scenario_transitions=[{'after_hypothesis_key':'B','transition':{'source_ref':'user:switch','new_phase_id':'phase-1','new_scenario_ref':'scenario-new'}}])
 for variant in ('normal','after_transition_enqueued_before_attach','after_event_submitted','after_transition_followups_before_complete'):
  name='transition_'+variant;kw={} if variant=='normal' else ({'crash_after':variant} if variant=='after_event_submitted' else {'injection':variant});a,b=p.launch(name+'_start',p.base(name,tp,**kw));c,d=(a,b) if variant=='normal' else run_resume(name,tp);e,f=p.launch(name+'_again',dict(p.base(name,tp),mode='resume'))
  trans=[r for r in p.tables(d,'search_actions') if r['action_kind']=='scenario_transition'];fu=[r for r in p.tables(d,'search_actions') if r['action_kind']=='retrieve' and r['payload'].get('source_event_id')];cs=p.artifacts(d,'path_context');ph={v['context_id']:v['phase_id'] for v in cs};phases=[ph.get(r['context_ref']) for r in fu]
  record(name,c['returncode']==0 and len(trans)==1 and trans[0]['status']=='done' and phases==['phase-1'] and p.counters(d)==p.counters(f),{'start':a['parsed'],'resume':c['parsed'],'transitions':trans,'followups':fu,'phases':phases,'before':p.counters(b),'after':p.counters(d),'again':p.counters(f),'contexts':cs})
 pp=p.plan(pools={'CCO':[p.spec(coproducts=['[H][H]','O'])]});policy={'search_limits':{'max_product_expansion_width':3,'max_total_search_actions':30}}
 for variant in ('normal','after_two_corrected'):
  name='three_products_'+variant;a,b=s.launch(name+'_start',p.base(name,pp,policy=policy,**({} if variant=='normal' else {'supplemental_injection':'after_two_followups'})));c,d=(a,b) if variant=='normal' else s.launch(name+'_resume',dict(p.base(name,pp),mode='resume'));e,f=s.launch(name+'_again',dict(p.base(name,pp),mode='resume'))
  products=[q['state_ref'] for ev in p.tables(d,'events') for q in ev['payload']['participants'] if q['side']=='product'];fu=[r for r in p.tables(d,'search_actions') if r['action_kind']=='retrieve' and r['payload'].get('source_event_id')];missing=sorted(set(products)-{r['subject_ref'] for r in fu})
  record(name,c['returncode']==0 and (a['returncode']==77 if variant!='normal' else a['returncode']==0) and len(products)==3 and len(fu)==3 and not missing and p.counters(d)==p.counters(f),{'start':a['parsed'],'resume':c['parsed'],'products':products,'followups':fu,'missing':missing,'before':p.counters(b),'after':p.counters(d),'again':p.counters(f)})
 # True public double resume from same expansion B1, winning child holds flock inside expansion until loser returns.
 name='public_concurrent_resume';pp=p.plan();a,b=s.launch(name+'_setup',p.base(name,pp,supplemental_injection='after_expand_claim'));bar=ROOT/'synthetic_runs'/(name+'_barrier');procs=[]
 for w in ('first','second'):
  inp=dict(p.base(name,pp),mode='resume',supplemental_injection='concurrent_expand',barrier=str(bar));f=ROOT/'inputs'/(name+'_'+w+'.json');p.dump(f,inp);cmd=[PY,'-B',str(ROOT/'scripts/probe_supplemental.py'),'worker',str(f)];env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'src')};pr=subprocess.Popen(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env);procs.append((w,cmd,env,pr))
 deadline=time.monotonic()+20
 while time.monotonic()<deadline:
  ready=list(bar.glob('*.ready.json')) if bar.exists() else []
  if len(ready)==1 and any(pr.poll() is not None for _,_,_,pr in procs):break
  time.sleep(.02)
 overlap={'ready_receipts':[json.loads(x.read_text()) for x in ready],'peer_exited_while_winner_waits':any(pr.poll() is not None for _,_,_,pr in procs),'pid_status_before_release':{str(pr.pid):pr.poll() for _,_,_,pr in procs}};bar.mkdir(parents=True,exist_ok=True);(bar/'GO').write_text('go');res=[]
 for w,cmd,env,pr in procs:
  so,se=pr.communicate(timeout=90);parsed=[]
  for line in so.splitlines():
   try:parsed.append(json.loads(line))
   except ValueError:pass
  v={'command':cmd,'environment':env,'returncode':pr.returncode,'stdout':so,'stderr':se,'parsed':parsed};p.dump(ROOT/'logs'/(name+'_'+w+'.execution.json'),v);(ROOT/'logs'/(name+'_'+w+'.stdout.txt')).write_text(so);(ROOT/'logs'/(name+'_'+w+'.stderr.txt')).write_text(se);res.append(v)
 d=p.snapshot(Path(p.base(name)['runs_root'])/name);p.dump(ROOT/'tables'/(name+'_final.json'),d);tool=[json.loads(x.read_text()) for x in sorted(bar.glob('*.tool_entered.json'))];e,f=s.launch(name+'_again',dict(p.base(name,pp),mode='resume'));loser=next((v for v in res if v['returncode']==3),{})
 record(name,len(tool)==1 and len(ready)==1 and overlap['peer_exited_while_winner_waits'] and sorted(v['returncode'] for v in res)==[0,3] and 'driver_session_active' in loser.get('stdout','') and p.counters(d)==p.counters(f),{'setup':a['parsed'],'before':p.counters(b),'after':p.counters(d),'again':p.counters(f),'overlap':overlap,'actual_tool_entries':tool,'results':res,'attempts_before':p.tables(b,'search_attempts'),'attempts_after':p.tables(d,'search_attempts'),'reservations_before':p.tables(b,'budget_reservations'),'reservations_after':p.tables(d,'budget_reservations')})
if __name__=='__main__':
 try:main()
 finally:p.dump(ROOT/'observations_r2.json',OBS)
