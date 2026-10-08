#!/usr/bin/env python3
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
def snap(n):return json.loads((R/f'tables/r3_{n}.json').read_text())
def trace(n):return json.loads((R/f'logs/r3_{n}.trace.json').read_text())['trace']
def outcomes(s):return [v['content']['payload']['outcome'] for k,v in s['artifacts'].items() if k.endswith('/expansion_outcome.json') and 'outcome' in v.get('content',{}).get('payload',{})]
obs=[]
e=snap('essential_conflict');adms=[z['result'] for z in trace('essential_conflict') if z['call']=='decide_admission']
x={'case':'R3_actual_defer_not_persistent_blocked','admissions':adms,'action_status':[(a['action_kind'],a['status']) for a in e['tables']['search_actions']],'outcomes':outcomes(e),'event_count':len(e['tables']['events']),'hypothesis_count':len(e['tables']['hypotheses'])}
x['check']=adms[0][0]=='defer' and adms[0][1][0].startswith('R3:') and any(o['kind']=='admission_deferred' for o in x['outcomes']) and all(a['status']=='done' for a in e['tables']['search_actions']) and not e['tables']['events'] and len(e['tables']['hypotheses'])==1;obs.append(x)
x={'case':'novel_source_labels_P2','preparations':[{'source_refs_argument':z.get('source_refs_argument'),'product_states':z.get('product_states')} for z in trace('novel_empty') if z['call']=='prepare_hypothesis']}
a,b=x['preparations'];x['check']=a['source_refs_argument']==[{'record':'novel-model-proposal:novel_outside_pool'}] and b['source_refs_argument'] is None and a['product_states'][0]['state_id']==b['product_states'][0]['state_id'] and b['product_states'][0]['source_refs']==[{'record':'synthetic-pool-spec'}];obs.append(x)
for n,expected in [('h04_missing','unknown'),('h04_supported','verified')]:
 audit=next(z['result'] for z in trace(n) if z['call']=='audit_hypothesis');check=next(z for z in audit['checks'] if z['name']=='provenance_dependency');x={'case':n+'_initial_supply','dependency_check':check,'events':len(snap(n)['tables']['events'])};x['check']=check['status']==expected and x['events']==1;obs.append(x)
audit=next(z['result'] for z in trace('novel_empty') if z['call']=='audit_hypothesis');adm=next(z['result'] for z in trace('novel_empty') if z['call']=='decide_admission');x={'case':'C06_unknown_bounded_conditional','unknown_axes':[c['name'] for c in audit['checks'] if c['status']=='unknown'],'admission':adm,'event_count':len(snap('novel_empty')['tables']['events'])};x['check']='condition_check' in x['unknown_axes'] and 'element_accounting' in x['unknown_axes'] and adm[0]=='retain_conditional' and x['event_count']==1;obs.append(x)
b=snap('novel_audit_bad_raw');x={'case':'AuditContractError_failure_not_success','events':len(b['tables']['events']),'hypotheses':len(b['tables']['hypotheses']),'attempt_statuses':[v['status'] for v in b['tables']['search_attempts']],'action_statuses':[(v['action_kind'],v['status']) for v in b['tables']['search_actions']],'commit_count':len(b['tables']['search_commit_records']),'outcomes':outcomes(b)};x['check']=x['events']==0 and x['hypotheses']==0 and x['attempt_statuses']==['failed'] and any(o['kind']=='contract_aborted' for o in x['outcomes']);obs.append(x)
for x in obs:assert x['check'],x
(R/'captured_semantic_readback.json').write_text(json.dumps(obs,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'readback_checks':len(obs),'all':True,'probe_rerun_count':0}))
