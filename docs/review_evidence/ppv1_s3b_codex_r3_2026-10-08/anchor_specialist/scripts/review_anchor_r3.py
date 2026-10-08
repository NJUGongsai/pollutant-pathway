#!/usr/bin/env python3
"""Independent bounded S3B-01 first-consume anchor checks; public wrappers.
No provider/network. Old inputs are recipes only; every run is new scratch.
"""
import sys,json,sqlite3,hashlib,subprocess,os,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import probe_public as p
ROOT=p.ROOT;PY=sys.executable;OBS=[]

def worker(inp):
 from pathway_v43.pollutant.search import SearchLedger
 from pathway_v43.pollutant import runflow,production
 for owner,key in ((SearchLedger,'recover_run'),(runflow._Driver,'drive'),(production,'execute_atomtool_expansion')):
  orig=getattr(owner,key)
  def wrap(*a,_orig=orig,_name=key,**kw):
   print(json.dumps({'consumer_entered':_name,'pid':os.getpid()}),flush=True)
   return _orig(*a,**kw)
  setattr(owner,key,wrap)
 p.worker(inp)

def launch(label,inp):
 f=ROOT/'inputs'/(label+'.json');p.dump(f,inp)
 cmd=[PY,'-B',str(Path(__file__).resolve()),'worker',str(f)]
 env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'src')}
 pr=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,env=env,timeout=90)
 parsed=[]
 for line in pr.stdout.splitlines():
  try:parsed.append(json.loads(line))
  except ValueError:pass
 out={'command':cmd,'environment':env,'returncode':pr.returncode,'stdout':pr.stdout,'stderr':pr.stderr,'parsed':parsed}
 p.dump(ROOT/'logs'/(label+'.execution.json'),out)
 (ROOT/'logs'/(label+'.stdout.txt')).write_text(pr.stdout);(ROOT/'logs'/(label+'.stderr.txt')).write_text(pr.stderr)
 snap=p.snapshot(Path(inp['runs_root'])/inp['run_id']);p.dump(ROOT/'tables'/(label+'.json'),snap)
 return out,snap

def record(name,ok,detail):
 OBS.append({'case':name,'current_contract_observed':bool(ok),'detail':detail})
 p.dump(ROOT/'anchor_observations_r3.json',OBS)
 print(json.dumps({'case':name,'current_contract_observed':bool(ok)}),flush=True)

def kind(v):
 return next((q.get('detail',{}).get('kind') for q in v['parsed'] if 'exception' in q),None)

def mutate_plan(target,variant):
 from pathway_v43.domain.models import content_hash
 before=target.read_bytes();data=json.loads(before)
 if variant=='unknown_plan_version':data['payload']['plan_version']='ppv1-frozen-plan-999'
 elif variant=='missing_plan_version':data['payload'].pop('plan_version',None)
 else:
  newp=p.plan(scenario_transitions=[{'after_hypothesis_key':'B','transition':{'source_ref':'injected:changed-plan','new_phase_id':'phase-injected','new_scenario_ref':'scenario-injected'}}])
  data['payload']['plan']=newp;data['payload']['plan_digest']=content_hash(newp)
 data['payload_hash']=content_hash(data['payload']);target.write_text(json.dumps(data))
 return before,data,target.read_bytes()

def negative_case(variant,boundary='after_bundle_written'):
 from pathway_v43.domain.models import content_hash
 name='anchor_'+variant+'_'+boundary;pp=p.plan()
 a,b=launch(name+'_start',p.base(name,pp,**({} if boundary=='done' else {'crash_after':boundary})))
 run=Path(p.base(name)['runs_root'])/name;target=run/'results/run-plan/frozen_plan.json';old=target.read_bytes();data=json.loads(old)
 con=sqlite3.connect(run/'pollutant.sqlite');con.row_factory=sqlite3.Row
 root=con.execute("SELECT * FROM search_actions WHERE action_kind='retrieve' AND parent_search_revision=0 ORDER BY created_at,action_id LIMIT 1").fetchone()
 rp=json.loads(root['payload']);mutation={'variant':variant,'anchor_before':dict(root),'old_plan_envelope':data}
 expect='frozen_plan_anchor_corrupt'
 if variant=='missing_anchor':rp.pop('plan_digest',None);con.execute('UPDATE search_actions SET payload=? WHERE action_id=?',(json.dumps(rp),root['action_id']));expect='frozen_plan_anchor_missing'
 elif variant=='deleted_root_anchor':con.execute('DELETE FROM search_actions WHERE action_id=?',(root['action_id'],));expect='frozen_plan_anchor_missing'
 elif variant=='corrupt_anchor_digest':
  old,data,bad=mutate_plan(target,variant);rp['plan_digest']=data['payload']['plan_digest'];con.execute('UPDATE search_actions SET payload=? WHERE action_id=?',(json.dumps(rp),root['action_id']))
 elif variant=='corrupt_task_key_column':con.execute('UPDATE search_actions SET task_key=? WHERE action_id=?',('forged-task',root['action_id']))
 elif variant=='corrupt_task_key_payload':rp['task_key']='forged-task';con.execute('UPDATE search_actions SET payload=? WHERE action_id=?',(json.dumps(rp),root['action_id']))
 elif variant=='unparseable_anchor_payload':con.execute('UPDATE search_actions SET payload=? WHERE action_id=?',('{bad',root['action_id']))
 elif variant=='non_mapping_anchor_payload':con.execute('UPDATE search_actions SET payload=? WHERE action_id=?',('[1]',root['action_id']))
 else:
  old,data,bad=mutate_plan(target,variant)
  expect='frozen_plan_binding_mismatch' if variant not in ('unknown_plan_version','missing_plan_version') else 'version_refusal'
 con.commit();con.close();mutated=target.read_bytes();mutation['new_plan_envelope']=json.loads(mutated);mutation['old_sha256']=hashlib.sha256(old).hexdigest();mutation['mutated_sha256']=hashlib.sha256(mutated).hexdigest()
 p.dump(ROOT/'inputs'/(name+'_mutation.json'),mutation)
 before=p.snapshot(run);p.dump(ROOT/'tables'/(name+'_mutated.json'),before)
 inp=dict(p.base(name,pp),mode='resume');inp.pop('plan',None)
 if variant=='replaced_with_matching_argument':inp['plan']=data['payload']['plan']
 c,after=launch(name+'_resume',inp);entered=[q['consumer_entered'] for q in c['parsed'] if 'consumer_entered' in q]
 tables_same=before['tables']==after['tables'];unchanged_artifact=target.read_bytes()==mutated
 rejected=c['returncode']==3 and kind(c)==expect if expect!='version_refusal' else c['returncode']==3
 record(name,rejected and tables_same and not entered and unchanged_artifact,{'expected_kind':expect,'start':a,'resume':c,'actual_kind':kind(c),'consumer_entries_resume':entered,'all_15_tables_identical':tables_same,'business_table_count':len(before['tables']),'mutated_artifact_preserved':unchanged_artifact,'before_counts':p.counters(before),'after_counts':p.counters(after),'anchor_status':root['status'],'old_plan_digest':json.loads(root['payload']).get('plan_digest'),'new_plan_digest':data['payload'].get('plan_digest')})

def protocol_controls():
 novel={'hypothesis_id':'novel:1','proposal_context':{'reference_hypothesis_ids':[],'output_origin':'novel_outside_pool'},'reaction_spec':p.spec('Novel')}
 for variant,pp,count in [('novel_nonempty',p.plan(model={'provider_kind':'scripted','responses':[json.dumps({'proposals':[novel]})]}),2),('novel_empty',{'pools':{},'model':{'provider_kind':'scripted','responses':[json.dumps({'proposals':[novel]})]}},1),('abstain_empty',{'pools':{},'model':{'provider_kind':'scripted','responses':['{"proposals":[]}']}},0)]:
  name='protocol_'+variant;a,b=launch(name+'_start',p.base(name,pp));tools=[x for x in a['parsed'] if x.get('consumer_entered')=='execute_atomtool_expansion'];reqs=p.tables(b,'model_requests')
  record(name,a['returncode']==0 and len(p.eventids(b))==count and len(tools)==count and len(reqs)==1 and all(x['network_request_count']==0 for x in reqs),{'execution':a,'counts':p.counters(b),'events':p.tables(b,'events'),'hypotheses':p.tables(b,'hypotheses'),'requests':reqs,'actual_tool_count':len(tools)})
 name='zero_depth_persisted';a,b=launch(name+'_start',p.base(name,p.plan(),policy={'search_limits':{'max_search_depth':0}}));c,d=launch(name+'_again',dict(p.base(name,p.plan()),mode='resume'));out=next(x['result'] for x in a['parsed'] if 'result' in x);out2=next(x['result'] for x in c['parsed'] if 'result' in x);stop=out['stop'];record(name,a['returncode']==0 and c['returncode']==0 and stop['primary']=='budget_limit' and 'depth_limit' in stop['other_reasons'] and bool(stop['unexplored']['blocked_objects']) and stop==out2['stop'],{'start':a,'resume':c,'stop':stop,'repeat_stop':out2['stop'],'counts':p.counters(d)})

def main():
 for boundary in ('after_bundle_written','after_event_submitted'):
  for variant in ('missing_anchor','corrupt_anchor_digest'):negative_case(variant,boundary)
 for variant in ('corrupt_task_key_column','corrupt_task_key_payload','unparseable_anchor_payload','non_mapping_anchor_payload','deleted_root_anchor','replaced_with_matching_argument','unknown_plan_version','missing_plan_version'):negative_case(variant)
 negative_case('self_consistent_replaced_plan','done')
 protocol_controls()

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='worker':worker(json.loads(Path(sys.argv[2]).read_text()))
 else:
  try:main()
  finally:p.dump(ROOT/'anchor_observations_r3.json',OBS)
