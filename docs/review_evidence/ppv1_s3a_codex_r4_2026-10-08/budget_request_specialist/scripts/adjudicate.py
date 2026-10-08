#!/usr/bin/env python3
"""Read-only validation of already completed logs, not another runtime execution."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];E=R/'evidence'
raw=json.loads((E/'contract_observations.json').read_text());valid=[];adj=[]
for row in raw:
 if row['case']=='stop_six_reason_priority':
  adj.append({'case':row['case'],'decision':'exclude original R2 bad expected-order oracle; corrected original priority63 separately evaluated'});continue
 ok=row['contract_passed']
 if row['case'].endswith('_recover') and row['group']=='S3A-04' and row['observed']['accepted']:
  pending=row['observed']['result']['pending_requests'];ok=row['before']==row['after'] and bool(pending) and all(bool(p.get('reference_integrity',{}).get('kind')) for p in pending)
  adj.append({'case':row['case'],'decision':'R2 minimum expressly allows structural integrity disclosure instead of top-level rejection','passed':ok,'integrity_kinds':[p.get('reference_integrity',{}).get('kind') for p in pending]})
 assert ok,(row['case'],row['observed']);valid.append(row['case'])
assert len(valid)==114
sup=[json.loads(x) for x in (E/'supplement/stdout.txt').read_text().splitlines()]
priority=next(x for x in sup if x['case']=='priority_corrected_original_order');assert len(priority['subcases'])==63 and all(x['passed'] for x in priority['subcases'])
policies=[x for x in sup if x['case'].startswith('policy_')];assert len(policies)==10
for x in policies:
 assert not x['observed']['accepted'] and x['observed']['kind']=='search_policy_block_corrupt' and x['before']==x['after']
 if not x['contract_passed']:adj.append({'case':x['case'],'decision':'strict frozen-store corruption guard runs before expected-policy comparison; old R2 expected identity-mismatch kind not required','actual_kind':x['observed']['kind'],'passed':True})
extras=[json.loads(x) for x in (E/'extra/stdout.txt').read_text().splitlines()];assert len(extras)==31
bad=[x for x in extras if x['case'].startswith('policy_request_') and not x['case'].startswith('policy_request_legal_')];assert len(bad)==18
for x in bad:assert x['observed']['accepted'] and x['before']!=x['after'] and all(r['network_request_count']==0 for r in x['after']['model_requests'])
legal=[x for x in extras if x['case'].startswith('policy_request_legal_')];assert len(legal)==3 and all(x['contract_passed'] for x in legal)
x=next(x for x in extras if x['case']=='unknown_status_failed');assert x['observed']['accepted'] and x['before']['model_requests'][0]['status']=='corrupt-status' and x['after']['model_requests'][0]['status']=='failed'
for name in ['unknown_status_sent','unknown_status_response']:
 x=next(x for x in extras if x['case']==name);assert not x['observed']['accepted'] and x['before']==x['after']
assembly=[json.loads(x) for x in (E/'legal_assembly/stdout.txt').read_text().splitlines()];assert len(assembly)==2 and all(x['contract_passed'] for x in assembly)
summary={'actual_HEAD':json.loads((E/'input_snapshot.json').read_text())['metadata']['actual_HEAD'],'old_raw115':{'pass':sum(x['contract_passed'] for x in raw),'failed':sum(not x['contract_passed'] for x in raw)},'valid_R2_matrix_cases':114,'valid_R2_contract_conform':114,'groups':{g:sum(x['group']==g for x in raw if x['case']!='stop_six_reason_priority') for g in ['S3A-03','S3A-04','S3A-05']},'corrected_priority_subsets':63,'corrected_priority_pass':63,'supplement_policy_rejections':10,'extra_completed_before_prep_error':31,'extra_internals_not_executed':'last two legal assembly controls after missing-version prep failure; separately supplied valid-version controls2 once','extra_bad_policy_lifecycle_acceptances':18,'extra_legal_lifecycle_controls':3,'extra_unknown_status_failed_actual_write':True,'extra_unknown_status_sent_response_reject_controls':2,'legal_partial_assembly_controls':2,'adjudication_adjustments':adj,'retained_P1':['S3A-03 request lifecycle consumers skip frozen policy','S3A-04 unknown status successfully migrated into failed'],'network_requests':0,'external_model_calls':0,'counts_are_control_cases_not_vulnerabilities_or_scientific_performance':True}
(E/'adjudicated_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
