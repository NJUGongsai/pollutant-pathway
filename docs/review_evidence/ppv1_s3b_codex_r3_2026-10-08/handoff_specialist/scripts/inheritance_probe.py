#!/usr/bin/env python3
from pathlib import Path
import sys,json,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'src'))
import protocol_probe as q
import probe_public as p
OBS=[]
def rec(name,check,detail):
 row={'case':name,'check':bool(check),'detail':detail};OBS.append(row)
 (ROOT/'inheritance_observations.json').write_text(json.dumps(OBS,ensure_ascii=False,indent=2)+'\n');print(json.dumps(row,ensure_ascii=False),flush=True)
 assert check,row
for name in ('novel_empty','novel_nonempty','zero_depth','essential_conflict','e01','h04_missing','h04_supported','branch_isolation'):
 inp=json.loads((ROOT/'source_inputs'/(name+'.json')).read_text())
 rc,out,s,tr=q.launch('r3_'+name,inp)
 counts=p.counters(s);events=p.tables(s,'events');stop=(out or {}).get('result',{}).get('stop',{});callcounts={nm:sum(x.get('call')==nm for x in tr['trace']) for nm in ('execute_atomtool_expansion','audit_hypothesis','decide_admission')}
 d={'returncode':rc,'counts':counts,'stop':stop,'network_attempts':len(tr['network_attempts']),'calls':callcounts,'tracefile':'logs/r3_'+name+'.trace.json','event_ids':[x.get('event_id') for x in events]}
 if name.startswith('novel_'):
  expect=1 if name=='novel_empty' else 2
  d['substrate_profile_count']=len(p.artifacts(s,'substrate_profile'));d['production_report_count']=len(p.artifacts(s,'production_report'));d['proposal_actions']=[x for x in p.tables(s,'search_actions') if x.get('payload',{}).get('proposal_context')]
  check=rc==0 and len(events)==expect and all(callcounts[x]==expect for x in callcounts) and not tr['network_attempts']
 elif name=='zero_depth':
  d['blocked_objects']=stop.get('unexplored',{}).get('blocked_objects',[])
  check=rc==0 and stop.get('primary')=='budget_limit' and 'depth_limit' in stop.get('other_reasons',[]) and stop.get('unexplored',{}).get('blocked')==1 and bool(d['blocked_objects'])
 else:
  expect=0 if name=='essential_conflict' else 2 if name in ('e01','branch_isolation') else 1
  d['actions']=p.tables(s,'search_actions');d['attempts']=p.tables(s,'expansion_attempts')
  check=rc==0 and len(events)==expect and not tr['network_attempts']
 rec(name,check,d)
inp=json.loads((ROOT/'source_inputs/novel_empty.json').read_text());inp['inject']='audit_bad_raw'
rc,out,s,tr=q.launch('r3_novel_audit_bad_raw',inp)
check=rc==0 and not p.tables(s,'events') and any(x.get('exception',{}).get('type')=='AuditContractError' for x in tr['trace']) and not tr['network_attempts']
rec('novel_actual_AuditContractError_no_success',check,{'returncode':rc,'counts':p.counters(s),'out':out,'trace':tr,'actions':p.tables(s,'search_actions'),'attempts':p.tables(s,'expansion_attempts')})
