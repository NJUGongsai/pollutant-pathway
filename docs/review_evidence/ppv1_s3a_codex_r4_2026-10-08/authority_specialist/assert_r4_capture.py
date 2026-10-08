#!/usr/bin/env python3
"""Read-only actual-contract assertions. Residual cases explicitly failed, not passed."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
legacy=[json.loads(x) for x in (P/'inheritance.stdout.jsonl').read_text().splitlines()];assert len(legacy)==27
for r in legacy:
 if r['case']=='first_submit_raw_guard':assert r['result']['error']=='Ppv1StateContractError' and not r['changed']
 elif r['case'].endswith('__clean'):assert r['recovery']['returned'] and r['public_writer_replay']['returned']['created'] is False and not r['replay_changed']
 else:assert r['recovery']['error']=='SearchIntegrityError' and not r['recovery_changed'] and not r['replay_changed'] and r['public_writer_replay']['error'] in ('Ppv1LedgerCorrupt','Ppv1EventConflict')
seg=json.loads((P/'segmented_observations.json').read_text());assert len(seg)==120
fixed=[];controls=[]
for r in seg:
 c=r['case'];o=r['output'];res=o['result']
 if c.startswith('identity_'):
  assert o['direct']['error']=='SearchContractError' and o['write']['error']=='SearchContractError';assert not o['write_file_exists'] and o['before']==o['after_write'] and o['b3_before']==o['after']==o['after_second'];assert res['returned']['actions'][0]['disposition']['kind']=='bundle_event_identity_not_frozen' and o['artifact_preserved'];fixed.append(c)
 elif c.endswith('__clean') or c=='first_complete_clean':assert res['returned'];controls.append(c)
 elif c.startswith('H07H08_'):
  assert o['before']==o['after'] and o['artifact_preserved'];assert 'error' in res or res['returned']['actions'][0]['disposition']['error']=='SearchArtifactIntegrityError';fixed.append(c)
 else:
  assert 'error' in res and o['before']==o['after'];fixed.append(c)
  if 'public_writer_original_input' in o:assert 'error' in o['public_writer_original_input'] and o['after']==o['writer_after']
assert len(fixed)==111 and len(controls)==9
sup=[json.loads(x.read_text()) for x in sorted((P/'supplementary_cases').glob('*/input_output.json'))];assert len(sup)==3
for r in sup:assert r['result']['error'] and r['before']==r['after']
done=[json.loads(x.read_text()) for x in sorted((P/'done_result_reuse_cases').glob('*/input_output.json'))];assert len(done)==2
for r in done:
 assert r['before']==r['after']
 if r['case']=='done_result_same_event':assert r['result']['reason']=='already_completed' and r['result']['event_id']==r['recorded_completed_event_id'] and r['returned_event_exists_in_current_store']
 else:assert r['result']['error']=='SearchContractError' and r['result']['detail']['kind']=='event_identity_not_frozen_to_action' and r['foreign_event_validated_separate_public_store']['created']
crash=json.loads((P/'crash_observations.json').read_text());assert len(crash)==5
nec=json.loads((P/'necessary_reference_observations.json').read_text());assert len(nec)==63
bad=[];nc=[]
for r in nec:
 assert r['artifact_preserved']
 if r['inputs']['mutation']=='clean':assert r['result']['returned'];nc.append(r['case']);continue
 bad.append(r['case'])
 assert r['result']['error']=='SearchIntegrityError' and r['before']==r['after']
 expected='necessary_reservation_ref_missing' if r['inputs']['mutation']=='remove_ref_only' else 'reservation_row_missing'
 assert r['result']['detail']['kind']==expected
 if r['inputs']['phase']=='B3_recover':assert len(r['before']['events'])==len(r['after']['events'])==0 and len(r['before']['search_commit_records'])==len(r['after']['search_commit_records'])==0
assert len(bad)==54 and len(nc)==9
chain=[json.loads(x.read_text()) for x in sorted((P/'one_action_chain_cases').glob('*/input_output.json'))];assert len(chain)==2
for r in chain:
 assert r['budget']['run_level']['max_total_search_actions']['used']==1 and len(r['final']['search_commit_records'])==1
 if r['case']=='upper1_clean':assert r['steps'][1]['claim']['error']=='SearchBudgetExhausted' and len(r['final']['events'])==1
 else:
  assert r['steps'][0]['complete']['error']=='SearchIntegrityError' and r['steps'][0]['complete']['detail']['kind']=='reservation_row_missing'
  assert r['steps'][0]['before_complete']==r['steps'][0]['after_complete'] and r['steps'][1]['complete']['returned']['completed'] and len(r['final']['events'])==2
cache=json.loads((P/'cache_boundary_observations.json').read_text());assert cache['summary']['assertions_passed'] and len(cache['rows'])==7
extra=json.loads((P/'defer_control_observations.json').read_text());assert len(extra)==13
for r in extra:
 if r['case'].startswith('defer_row__') and r['case']!='defer_row__clean':assert r['result']['error']=='SearchIntegrityError' and r['before']==r['after']
 else:assert r['result']['returned']
out={'capture_readonly_assertions':'passed','old_27':{'bad_authority_rejected':24,'legal_controls':2,'raw_guard':1},'old_segmented120':{'rejected_bad':111,'legal_controls':9},'done2':{'legal_actual_reference':1,'foreign_explicit_conflict':1},'normal_first_submit_controls':3,'hard_kill_barrier_controls':5,'upper1_chain_cases':2,'cache_boundary_cases':7,'cache_hit_boundary_classification':'P2 fixed-range disclosed limitation','additional_defer_controls':{'bad_rows_rejected':9,'legal_controls':4},'necessary_reference_subset':{'bad_cases_rejected_zero_write':54,'legal_controls':9,'closed_group':'S3A-02','bad_case_names':bad},'no_test_count_sum_or_science_performance':True}
(P/'contract_results.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='necessary_reference_subset'},ensure_ascii=False));print(json.dumps({'authority_P1_closed':'S3A-02','necessary_reference_subset_rejected':len(bad),'legal_controls':len(nc)}))
