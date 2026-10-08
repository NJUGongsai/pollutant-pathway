#!/usr/bin/env python3
import os,sys,json,subprocess,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));import probe_public as p
ROOT=p.ROOT;PY=sys.executable;OBS=[]
def worker(inp):
 from pathway_v43.pollutant import runflow,production
 original_expand=runflow._Driver._run_expand;original_tool=production.execute_atomtool_expansion;current={}
 def expand(self,receipt):
  current['action_id']=receipt['action_id'];current['hypothesis_id']=receipt['subject_ref'];return original_expand(self,receipt)
 def tool(*a,**kw):
  v={**current,'pid':os.getpid(),'tool_inputs':kw.get('tool_inputs')};print(json.dumps({'actual_tool_entered':v}),flush=True);return original_tool(*a,**kw)
 runflow._Driver._run_expand=expand;production.execute_atomtool_expansion=tool;p.worker(inp)
def launch(label,inp):
 f=ROOT/'inputs'/(label+'.json');p.dump(f,inp);cmd=[PY,'-B',str(Path(__file__).resolve()),'worker',str(f)];env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'src')};pr=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,env=env,timeout=90);parsed=[]
 for line in pr.stdout.splitlines():
  try:parsed.append(json.loads(line))
  except ValueError:pass
 v={'command':cmd,'environment':env,'returncode':pr.returncode,'stdout':pr.stdout,'stderr':pr.stderr,'parsed':parsed};p.dump(ROOT/'logs'/(label+'.execution.json'),v);(ROOT/'logs'/(label+'.stdout.txt')).write_text(pr.stdout);(ROOT/'logs'/(label+'.stderr.txt')).write_text(pr.stderr);ss=p.snapshot(Path(inp['runs_root'])/inp['run_id']);p.dump(ROOT/'tables'/(label+'.json'),ss);return v,ss
def record(name,ok,detail):
 OBS.append({'case':name,'current_contract_observed':bool(ok),'detail':detail});p.dump(ROOT/'additional_observations.json',OBS);print(json.dumps({'case':name,'current_contract_observed':bool(ok)}),flush=True)
def main():
 name='bad_bundle_independent_task';pp=p.plan(pools={'CCO':[p.spec('B'),p.spec('C')]});a,b=launch(name+'_start',p.base(name,pp,crash_after='after_bundle_written'));run=Path(p.base(name)['runs_root'])/name;target=next((run/'results').rglob('search_commit_bundle.json'));old=target.read_bytes();data=json.loads(old);badhyp=data['payload']['event']['hypothesis_id'];data['payload']['mutation_marker']='bad';target.write_text(json.dumps(data));bad=target.read_bytes();sm=p.snapshot(run);p.dump(ROOT/'tables'/(name+'_mutated.json'),sm);c,d=launch(name+'_resume',dict(p.base(name,pp),mode='resume'));e,f=launch(name+'_again',dict(p.base(name,pp),mode='resume'));tools=[x['actual_tool_entered'] for x in c['parsed'] if 'actual_tool_entered' in x];blocked=[r for r in p.tables(d,'search_actions') if r['status']=='blocked'];events=p.tables(d,'events');record(name,c['returncode']==0 and e['returncode']==0 and len(tools)==1 and all(x['hypothesis_id']!=badhyp for x in tools) and len(blocked)==1 and len(events)==1 and all(x['hypothesis_id']!=badhyp for x in events) and target.read_bytes()==bad and p.counters(d)==p.counters(f),{'start':a,'resume':c,'bad_hypothesis_id':badhyp,'tool_entries_resume':tools,'blocked':blocked,'events':events,'before':p.counters(sm),'after':p.counters(d),'again':p.counters(f),'original_sha256':hashlib.sha256(old).hexdigest(),'bad_sha256':hashlib.sha256(bad).hexdigest(),'bad_file_preserved':target.read_bytes()==bad})
 for variant in ('missing','unparseable','payload_changed'):
  name='frozen_artifact_'+variant;pp=p.plan();a,b=launch(name+'_start',p.base(name,pp,crash_after='after_bundle_written'));run=Path(p.base(name)['runs_root'])/name;target=run/'results/run-plan/frozen_plan.json';old=target.read_bytes()
  if variant=='missing':target.unlink();bad=None
  elif variant=='unparseable':target.write_text('{bad');bad=target.read_bytes()
  else:data=json.loads(old);data['payload']['plan']['pools']['CCO']=[];target.write_text(json.dumps(data));bad=target.read_bytes()
  sm=p.snapshot(run);p.dump(ROOT/'tables'/(name+'_mutated.json'),sm);inp=dict(p.base(name,pp),mode='resume');inp.pop('plan');c,d=launch(name+'_resume',inp);tools=[x for x in c['parsed'] if 'actual_tool_entered' in x];preserved=(not target.exists()) if bad is None else target.read_bytes()==bad
  record(name,c['returncode']==3 and sm['tables']==d['tables'] and not tools and preserved,{'resume':c,'before':p.counters(sm),'after':p.counters(d),'all_tables_identical':sm['tables']==d['tables'],'bad_file_preserved':preserved})
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='worker':worker(json.loads(Path(sys.argv[2]).read_text()))
 else:main()
