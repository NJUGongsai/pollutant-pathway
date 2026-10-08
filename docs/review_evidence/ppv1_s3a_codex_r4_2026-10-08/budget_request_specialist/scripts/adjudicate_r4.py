#!/usr/bin/env python3
"""Read only completed logs. This never calls production code or reruns probes."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];E=R/'evidence';adj=[]
raw=json.loads((E/'contract_observations.json').read_text());valid=[]
for x in raw:
 if x['case']=='stop_six_reason_priority':
  adj.append({'case':x['case'],'decision':'Exclude the historical incorrect priority oracle; use corrected63 below.'});continue
 ok=x['contract_passed']
 if x['group']=='S3A-04' and x['case'].endswith('_recover') and x['observed']['accepted']:
  pending=x['observed']['result']['pending_requests'];ok=x['before']==x['after'] and bool(pending) and all(p.get('reference_integrity',{}).get('kind') for p in pending)
  if not x['contract_passed']:adj.append({'case':x['case'],'decision':'Original minimum permits explicit structural reference-integrity disclosure instead of top-level throw.','kinds':[p['reference_integrity']['kind'] for p in pending]})
 assert ok,x['case'];valid.append(x)
assert len(valid)==114
sup=[json.loads(x) for x in (E/'supplement/stdout.txt').read_text().splitlines()];priority=next(x for x in sup if x['case']=='priority_corrected_original_order');assert len(priority['subcases'])==63 and all(x['passed'] for x in priority['subcases']);policies=[x for x in sup if x['case'].startswith('policy_')];assert len(policies)==10
for x in policies:
 assert not x['observed']['accepted'] and x['observed']['kind']=='search_policy_block_corrupt' and x['before']==x['after']
 if not x['contract_passed']:adj.append({'case':x['case'],'decision':'Strict frozen block fails before optional expected comparison; old identity-mismatch-only oracle no longer required.','actual_kind':x['observed']['kind']})
extras=[json.loads(x) for x in (E/'extra/stdout.txt').read_text().splitlines()];assert len(extras)==31
bad=[x for x in extras if x['case'].startswith('policy_request_') and not x['case'].startswith('policy_request_legal_')];legal=[x for x in extras if x['case'].startswith('policy_request_legal_')];assert len(bad)==18 and all(x['contract_passed'] for x in bad);assert len(legal)==3 and all(x['contract_passed'] for x in legal)
unknown=[x for x in extras if x['case'].startswith('unknown_status_')];assert len(unknown)==5
for x in unknown:
 assert x['before']==x['after']
 if x['case']=='unknown_status_recover':
  o=x['observed'];assert o['accepted'] and len(o['result']['unknown_status_requests'])==1 and o['result']['unknown_status_requests'][0]['status']=='corrupt-status' and not o['result']['pending_requests'];adj.append({'case':x['case'],'decision':'Explicit unknown_status_requests disclosure is the specified repair; top-level accepted report is not successful request execution.'})
 else:
  assert not x['observed']['accepted']
  if x['case'] in ['unknown_status_failed','unknown_status_register']:assert x['observed']['kind']=='request_status_unknown'
foreign=[x for x in extras if x['case'].startswith('foreign_request_run_')];assert len(foreign)==5 and all(all(x['checks'].values()) for x in foreign)
assembly=[json.loads(x) for x in (E/'legal_assembly/stdout.txt').read_text().splitlines()];assert len(assembly)==2 and all(x['contract_passed'] for x in assembly)
sent=[json.loads(x) for x in (E/'sent_failed_control/stdout.txt').read_text().splitlines()];assert len(sent)==1 and sent[0]['contract_passed']
full=json.loads((E/'full_status_observations.json').read_text());assert len(full)==35 and all(x['contract_passed'] for x in full)
summary={'actual_HEAD':json.loads((E/'input_snapshot.json').read_text())['metadata']['actual_HEAD'],'old_raw115':{'passed':sum(x['contract_passed'] for x in raw),'failed':sum(not x['contract_passed'] for x in raw)},'effective_inherited_matrix':{'cases':114,'conform':114,'groups':{g:sum(x['group']==g for x in valid) for g in ['S3A-03','S3A-04','S3A-05']}},'corrected_priority':{'cases':63,'passed':63},'frozen_read_recover':{'cases':10,'rejected_zero_write':10},'original_R3_extra_completed':{'cases':31,'bad_policy_state_consumers':18,'legal_state_controls':3,'unknown_status_entries':5,'foreign_request_run':5,'all_contract_conform':31},'extra_prep_error':'Historical script drops required limits.version at last two assembly cases. Neither executes. Preserved exit1 stderr; valid-version legal_assembly controls2 separately once. No failed internal controls relabeled pass.','legal_partial_assembly':2,'lawful_sent_to_failed':1,'additional_full_table_matrix':{'cases':35,'passed':35,'table_count':len(full[0]['before']),'decide_policy_refusals':18,'unknown_status_entries':5,'real_bookkeeping_controls':3,'known_closed_refusals':9},'closed_P1_groups':['S3A-03','S3A-04'],'S3A-05':'closed; priority/zero resources/inflight/exhaustion unchanged','adjustments':adj,'actual_network_requests':0,'external_model_calls':0,'counts_not_new_defects_or_scientific_performance':True}
(E/'adjudicated_summary_r4.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
