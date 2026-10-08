#!/usr/bin/env python3
from pathlib import Path
import sys,json,subprocess,hashlib,os,traceback,socket,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import probe_public as p
OBS=[]
def rec(name,ok,detail):
 x={'case':name,'check':bool(ok),'detail':detail};OBS.append(x);p.dump(ROOT/'observations.json',OBS);print(json.dumps(x,ensure_ascii=False),flush=True)
def worker(inp):
 from pathway_v43.pollutant import runflow,production
 from pathway_v43.pollutant.audit import AuditContractError
 trace=[];network=[]
 def no_network(*args,**kw):network.append({'args':str(args)});raise RuntimeError('Network forbidden in synthetic reviewer probe')
 socket.socket.connect=no_network;socket.create_connection=no_network
 def wrap(mod,name):
  original=getattr(mod,name)
  def fn(*a,**k):
   e={'call':name};trace.append(e)
   if name=='prepare_hypothesis':
    e.update({'spec':a[0],'source_refs_argument':k.get('source_refs')})
   if name=='audit_hypothesis':
    e.update({'hypothesis':a[0].to_dict(),'states':{sid:s.to_dict() for sid,s in k['states'].items()}})
   try:
    result=original(*a,**k)
    if name=='prepare_hypothesis':e.update({'hypothesis_id':result['hypothesis'].hypothesis_id,'product_states':[s.to_dict() for s in result['product_states']]})
    elif name=='audit_hypothesis':e['result']=result.to_dict()
    elif name=='decide_admission':e['result']=result
    elif name=='execute_atomtool_expansion':e['execution']=result
    return result
   except Exception as ex:e['exception']={'type':type(ex).__name__,'detail':getattr(ex,'detail',{})};raise
  setattr(mod,name,fn)
 wrap(runflow,'prepare_hypothesis')
 for name in ('execute_atomtool_expansion','audit_hypothesis','decide_admission'):wrap(production,name)
 if inp.get('inject')=='prepared_bad_raw':
  orig_expand=runflow.expand_hypothesis_production
  def corrupted_prepared(*a,**k):
   ps=k['prepared']['product_states'][0]
   trace.append({'call':'inject_prepared_bad_raw','old_state':ps.to_dict()})
   ps.structure_smiles_raw=ps.structure_smiles_raw+' |r|'
   return orig_expand(*a,**k)
  runflow.expand_hypothesis_production=corrupted_prepared
 if inp.get('inject')=='audit_bad_raw':
  original=production.execute_atomtool_expansion
  def corrupt(*a,**k):
   v=original(*a,**k)
   # Mutate actual diagnostic proof after real tool/diagnostic/converter.
   pr=v['center_evidence'].get('proof_record',{})
   trace.append({'call':'inject_audit_bad_raw','before_proof':copy.deepcopy(pr)})
   pr.setdefault('current',{})['smiles']='CCO |r|'
   return v
  production.execute_atomtool_expansion=corrupt
 try:p.worker(inp)
 finally:p.dump(ROOT/'logs'/(inp['_label']+'.trace.json'),{'trace':trace,'network_attempts':network})
def launch(label,inp):
 inp=copy.deepcopy(inp);inp['runs_root']=str(ROOT/'synthetic_runs'/'runs');inp['run_id']=label;inp['_label']=label
 p.dump(ROOT/'inputs'/(label+'.json'),inp)
 cmd=[sys.executable,'-B',str(Path(__file__).resolve()),'worker',str(ROOT/'inputs'/(label+'.json'))]
 env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'src')}
 v=subprocess.run(cmd,cwd=ROOT,env=env,text=True,capture_output=True,timeout=90)
 parsed=None
 for line in v.stdout.splitlines():
  try:parsed=json.loads(line)
  except ValueError:pass
 p.dump(ROOT/'logs'/(label+'.execution.json'),{'command':cmd,'environment':env,'returncode':v.returncode,'stdout':v.stdout,'stderr':v.stderr,'parsed':parsed})
 (ROOT/'logs'/(label+'.stdout.txt')).write_text(v.stdout);(ROOT/'logs'/(label+'.stderr.txt')).write_text(v.stderr)
 snap=p.snapshot(ROOT/'synthetic_runs'/'runs'/label);p.dump(ROOT/'tables'/(label+'.json'),snap)
 tr=json.loads((ROOT/'logs'/(label+'.trace.json')).read_text())
 return v.returncode,parsed,snap,tr

def main():
 for n in ('novel_empty','novel_nonempty','abstain','zero_depth','zero_actions','empty_pool','nonzero','e01','h04_missing','h04_supported','branch_isolation','essential_conflict','real_off_zero'):
  inp=json.loads((ROOT/'source_inputs'/(n+'.json')).read_text());rc,out,s,tr=launch('old_'+n,inp)
  stop=(out or {}).get('result',{}).get('stop',{});counts=p.counters(s);events=p.tables(s,'events');calls={nm:sum(z.get('call')==nm for z in tr['trace']) for nm in ('execute_atomtool_expansion','audit_hypothesis','decide_admission')}
  detail={'returncode':rc,'counts':counts,'stop':stop,'calls':calls,'network_attempts':len(tr['network_attempts']),'hypotheses':p.tables(s,'hypotheses'),'events':events}
  if n.startswith('novel_'):
   exp=[a for a in p.tables(s,'search_actions') if a['action_kind']=='expand_hypothesis'];novel=[a for a in exp if a['payload'].get('proposal_context')]
   reports=p.artifacts(s,'production_report');profiles=p.artifacts(s,'substrate_profile')
   detail.update({'novel_actions':novel,'production_reports':reports,'substrate_profiles':profiles,'appearance_sources':[r for r in p.tables(s,'state_appearances')]})
   expected=1 if n=='novel_empty' else 2
   rec(n+'_public_chain',rc==0 and len(events)==expected and all(calls[x]==expected for x in calls) and not tr['network_attempts'],detail)
   ns=[z for z in tr['trace'] if z.get('call')=='prepare_hypothesis' and (z.get('source_refs_argument') or z.get('spec',{}).get('key')=='Novel')]
   rec(n+'_source_binding',all((ss.get('source_refs') or [])==[{'record':'novel-model-proposal:novel_outside_pool'}] for z in ns for ss in z.get('product_states',[])),{'prepared_trace':ns,'novel_action_source_context':[a['payload']['proposal_context'] for a in novel]})
  elif n=='zero_depth':
   rec('zero_depth_persisted_disclosure',rc==0 and stop.get('primary')=='budget_limit' and 'depth_limit' in stop.get('other_reasons',[]) and stop.get('unexplored',{}).get('blocked')==1,detail)
   inp['mode']='resume';rc2,out2,s2,tr2=launch('old_zero_depth',inp)
   stop2=out2.get('result',{}).get('stop',{})
   rec('zero_depth_repeat_resume',rc2==0 and p.counters(s2)==counts and stop2.get('unexplored',{}).get('blocked_objects')==stop.get('unexplored',{}).get('blocked_objects'),{'before_counts':counts,'after_counts':p.counters(s2),'stop':stop2})
  else:
   exp=2 if n in ('e01','branch_isolation') else 1 if n in ('nonzero','h04_missing','h04_supported','abstain') else 0
   rec(n+'_public_control',rc==0 and len(events)==exp and not tr['network_attempts'],detail)
 # Additional novel-specific failure proof through real tool, diagnostic, converter and real audit.
 inp=json.loads((ROOT/'source_inputs/novel_empty.json').read_text());inp['inject']='audit_bad_raw'
 rc,out,s,tr=launch('novel_audit_bad_raw',inp)
 rec('novel_actual_audit_exception_no_success',rc==0 and not p.tables(s,'events') and any(z.get('exception',{}).get('type')=='AuditContractError' for z in tr['trace']),{'returncode':rc,'counts':p.counters(s),'out':out,'trace':tr})
 # Missing novel reaction content is structured run-error, no fabricated hypothesis/event.
 inp=json.loads((ROOT/'source_inputs/novel_empty.json').read_text());payload=json.loads(inp['plan']['model']['responses'][0]);payload['proposals'][0]['reaction_spec']={'key':'bad','coefficient':1};inp['plan']['model']['responses']=[json.dumps(payload)]
 rc,out,s,tr=launch('novel_insufficient',inp)
 rec('novel_insufficient_rejected',rc==0 and not p.tables(s,'events') and out.get('result',{}).get('stop',{}).get('run_error',{}).get('kind')=='spec_missing_product',{'out':out,'counts':p.counters(s),'trace':tr})
 p.dump(ROOT/'observations.json',OBS)
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='worker':worker(json.loads(Path(sys.argv[2]).read_text()))
 else:main()
