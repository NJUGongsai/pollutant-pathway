#!/usr/bin/env python3
from pathlib import Path
import json
import protocol_probe as q
p=q.p;ROOT=q.ROOT
OBS=json.loads((ROOT/'supplemental_observations.json').read_text())
def collect(name,check,detail):
 OBS.append({'case':name,'check':bool(check),'detail':detail});p.dump(ROOT/'supplemental_observations.json',OBS);print(json.dumps(OBS[-1],ensure_ascii=False),flush=True)
# Read-only adjudication of already completed tool failure child; previous controller field oracle was wrong.
x=json.loads((ROOT/'logs/novel_tool_failed.execution.json').read_text());s=json.loads((ROOT/'tables/novel_tool_failed.json').read_text());tr=json.loads((ROOT/'logs/novel_tool_failed.trace.json').read_text())
tool=[z for z in tr['trace'] if z.get('call')=='execute_atomtool_expansion'];audit=[z for z in tr['trace'] if z.get('call')=='audit_hypothesis'];diag=tool[0]['execution']['diagnostic']
collect('novel_tool_failed',x['returncode']==0 and not p.tables(s,'events') and not audit and all(diag[k] is None for k in ('reaction_center_match','strict_target_match','legacy_cn_match')) and diag['center_evidence']=={}, {'read_only_adjudication':True,'controller_failure':'old field name edit_center_consistent_with_donor does not exist; correct three fields reaction_center_match,strict_target_match,legacy_cn_match','counts':p.counters(s),'execution':x,'trace':tr,'diagnostic':diag})
# Remaining two planned cases were not executed before observer KeyError.
inp=json.loads((ROOT/'source_inputs/novel_empty.json').read_text());res=json.loads(inp['plan']['model']['responses'][0]);res['proposals'][0]['reaction_spec']['alignment']={'status':'unresolved','donor_to_current':{}};inp['plan']['model']['responses']=[json.dumps(res)]
rc,out,s,tr=q.launch('novel_alignment_unknown',inp);reports=p.artifacts(s,'production_report');aa=[r['audit'] for r in reports if r.get('audit')];cc=[c for r in aa for c in r['checks'] if c['name']=='transformation_center']
collect('novel_alignment_unknown',rc==0 and len(p.tables(s,'events'))==1 and bool(cc) and cc[0]['status']=='unknown',{'counts':p.counters(s),'out':out,'reports':reports,'trace':tr,'center_checks':cc})
inp=json.loads((ROOT/'source_inputs/novel_empty.json').read_text());inp['plan']['model']['responses']=['{"proposals": []}'];inp['policy']={'search_limits':{'max_retrievals_per_parent':2}}
rc,out,s,tr=q.launch('empty_abstain',inp)
collect('empty_abstain_no_local',rc==0 and not p.tables(s,'events') and out['result']['stop']['primary']=='no_local_candidate' and len(p.tables(s,'model_requests'))==1,{'counts':p.counters(s),'out':out,'trace':tr})
p.dump(ROOT/'supplemental_observations.json',OBS)
