#!/usr/bin/env python3
from pathlib import Path
import json,copy
import protocol_probe as q
p=q.p;ROOT=q.ROOT
OBS=[]
def collect(name,check,detail):
 OBS.append({'case':name,'check':bool(check),'detail':detail});p.dump(ROOT/'supplemental_observations.json',OBS);print(json.dumps(OBS[-1],ensure_ascii=False),flush=True)
def run(name,inp):
 rc,out,s,tr=q.launch(name,inp);details={'returncode':rc,'out':out,'counts':p.counters(s),'trace':tr,'events':p.tables(s,'events'),'attempts':p.tables(s,'search_attempts'),'actions':p.tables(s,'search_actions'),'reports':p.artifacts(s,'production_report')}
 return rc,out,s,tr,details
# New actual novel chain state corruption injected at production boundary. Uses original audit first consumer.
worker=ROOT/'scripts/protocol_probe.py'
text=worker.read_text()
needle=" if inp.get('inject')=='audit_bad_raw':"
new=""" if inp.get('inject')=='prepared_bad_raw':
  orig_expand=runflow.expand_hypothesis_production
  def corrupted_prepared(*a,**k):
   ps=k['prepared']['product_states'][0]
   trace.append({'call':'inject_prepared_bad_raw','old_state':ps.to_dict()})
   ps.structure_smiles_raw=ps.structure_smiles_raw+' |r|'
   return orig_expand(*a,**k)
  runflow.expand_hypothesis_production=corrupted_prepared
"""
# Copy version adds injector; original completed protocol source remains frozen.
newworker=ROOT/'scripts/protocol_supplemental_worker.py';newworker.write_text(text.replace(needle,new+needle))
# launch helper redirected locally only, execute different injector in separate process.
exec_source=q.launch.__code__
# q.launch has __file__ reference; temporarily alter module filename to select separate worker.
q.__file__=str(newworker)
inp=json.loads((ROOT/'source_inputs/novel_empty.json').read_text());inp['inject']='prepared_bad_raw'
rc,out,s,tr,d=run('novel_prepared_bad_raw',inp)
collect('novel_state_first_consumer_reject',rc==3 and out.get('exception')=='ChemicalStateError' and not p.tables(s,'events'),d)
q.__file__=str(worker)
for n in ('tool_failed','alignment_unknown'):
 inp=json.loads((ROOT/'source_inputs/novel_empty.json').read_text());res=json.loads(inp['plan']['model']['responses'][0]);sp=res['proposals'][0]['reaction_spec']
 if n=='tool_failed':sp['edits'][0]['atom1']='S_DOES_NOT_EXIST'
 else:sp['alignment']={'status':'unresolved','donor_to_current':{}}
 inp['plan']['model']['responses']=[json.dumps(res)]
 rc,out,s,tr,d=run('novel_'+n,inp)
 audit_calls=[x for x in tr['trace'] if x.get('call')=='audit_hypothesis'];toolcalls=[x for x in tr['trace'] if x.get('call')=='execute_atomtool_expansion']
 if n=='tool_failed':ok=rc==0 and not p.tables(s,'events') and not audit_calls and toolcalls[0]['execution']['diagnostic']['edit_center_consistent_with_donor'] is None
 else:
  aa=[r['audit'] for r in d['reports'] if r.get('audit')];d['audit_reports']=aa
  ok=rc==0 and len(p.tables(s,'events'))==1 and bool(aa) and aa[0]['checks']['center_consistency']['status']=='unknown'
 collect('novel_'+n,ok,d)
# Empty pool explicit abstention, independent no-budget exhaustion fixture.
inp=json.loads((ROOT/'source_inputs/novel_empty.json').read_text());inp['plan']['model']['responses']=['{"proposals": []}'];inp['policy']={'search_limits':{'max_retrievals_per_parent':2}}
rc,out,s,tr,d=run('empty_abstain',inp)
collect('empty_abstain_no_local',rc==0 and not p.tables(s,'events') and out['result']['stop']['primary']=='no_local_candidate' and len(p.tables(s,'model_requests'))==1,d)
p.dump(ROOT/'supplemental_observations.json',OBS)
