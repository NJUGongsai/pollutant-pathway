#!/usr/bin/env python3
import json
from pathlib import Path
import protocol_probe as q
p=q.p;ROOT=q.ROOT
# Read-only classify malformed alignment already executed. 'unresolved' is outside documented enum.
x=json.loads((ROOT/'logs/novel_alignment_unknown.trace.json').read_text());s=json.loads((ROOT/'tables/novel_alignment_unknown.json').read_text());bad={'case':'novel_invalid_alignment_contract_aborted','check':not p.tables(s,'events') and any(z.get('exception',{}).get('type')=='AuditContractError' for z in x['trace']),'read_only_adjudication':True,'prior_wrong_oracle':'unresolved is invalid; legal unavailable/ambiguous are unknown states','trace':x,'counts':p.counters(s)}
# Distinct legal enum fixture, not rerun of completed invalid case.
inp=json.loads((ROOT/'source_inputs/novel_empty.json').read_text());rsp=json.loads(inp['plan']['model']['responses'][0]);rsp['proposals'][0]['reaction_spec']['alignment']={'status':'unavailable','donor_to_current':{}};inp['plan']['model']['responses']=[json.dumps(rsp)]
rc,out,s,tr=q.launch('novel_legal_alignment_unavailable',inp);reports=p.artifacts(s,'production_report');cc=[c for r in reports if r.get('audit') for c in r['audit']['checks'] if c['name']=='transformation_center']
legal={'case':'novel_legal_alignment_unavailable_unknown','check':rc==0 and len(p.tables(s,'events'))==1 and len(cc)==1 and cc[0]['status']=='unknown','counts':p.counters(s),'out':out,'reports':reports,'trace':tr,'center_checks':cc}
p.dump(ROOT/'legal_unknown_observations.json',[bad,legal]);print(json.dumps([bad,legal],ensure_ascii=False),flush=True)
