#!/usr/bin/env python3
"""Actual public retrieve claim/outcome control, equivalent stored shapes; synthetic."""
from pathlib import Path
from dataclasses import asdict
import sys,json,copy
P=Path(__file__).resolve().parent;sys.path[:0]=[str(P/'repo/src'),str(P/'repo/tests')]
from s3a_worker import make_fixture
from pathway_v43.pollutant.profile import build_profile_identity_block,validate_search_limits
from pathway_v43.pollutant.search import SearchLedger,search_policy_version
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.storage.artifact_store import ArtifactStore
ROOT=P/'cache_boundary_cases';ROOT.mkdir(exist_ok=False)
TABLES=['meta','states','state_appearances','hypotheses','events','report_projections','expansion_plans','event_appearance_links','search_runs','search_actions','search_attempts','budget_reservations','model_requests','search_commit_records']
def snap(l):return {t:[dict(r) for r in l.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in TABLES}
def cap(fn):
 try:return {'returned':fn()}
 except Exception as e:return {'error':type(e).__name__,'detail':getattr(e,'detail',{}),'text':str(e)}
def normalize(rows):
 o=copy.deepcopy(rows)
 for table,rs in o.items():
  for r in rs:
   for key in ['created_at','claimed_at','consumed_at','released_at','completed_at','updated_at','registered_at','sent_at','responded_at']:r.pop(key,None)
 return o
ROWS=[]
for case,cache,mutation in [('legal_cache_hit',True,'clean'),('legal_non_cache',False,'clean'),('noncache_remove_refs_only',False,'remove_ref_only'),('noncache_remove_rows_only',False,'remove_rows_only'),('noncache_remove_refs_and_rows',False,'remove_refs_and_rows')]:
 d=ROOT/case;d.mkdir();r='same-retrieve-identity';l=SearchLedger(PollutantPathwayStore(d/'run.sqlite'),ArtifactStore(d/'runs',r),r);pol=build_profile_identity_block();pol['search_limits']=validate_search_limits({'max_retrievals_per_parent':1,'max_retrievals_total':1});l.register_search_run(r,pol)
 a=l.enqueue_action(run_id=r,parent_path_id='p1',context_ref='ctx1',subject_ref='retrieve-query',action_kind='retrieve',depth=1,policy_version=search_policy_version(),payload={'task_key':'retrieve-task','frozen_pool_digest':'same-pool'})['action_id'];receipt=l.claim_action(a,worker_id='w1',cache_hit=cache);original=snap(l);ids=[x['reservation_id'] for x in original['budget_reservations'] if x['limit_key'].startswith('max_retrievals')]
 if mutation in ['remove_ref_only','remove_refs_and_rows']:
  refs=l.action(a)['budget_reservation_ref'];refs=[x for x in refs if x not in ids];l.conn.execute('UPDATE search_actions SET budget_reservation_ref=? WHERE action_id=?',(json.dumps(refs),a))
 if mutation in ['remove_rows_only','remove_refs_and_rows']:
  for rid in ids:l.conn.execute('DELETE FROM budget_reservations WHERE reservation_id=?',(rid,))
 l.conn.commit();before=snap(l);recovery=cap(lambda:l.recover_run(r,policy_block=pol));after_recover=snap(l)
 complete=cap(lambda:l.complete_action(a,worker_id='w1',outcome_kind='outcome_recorded',outcome_ref='retrieval-local-outcome'));after=snap(l);reuse=cap(lambda:l.recover_run(r,policy_block=pol));after_reuse=snap(l);budget=l.budget_snapshot(r)
 row={'case':case,'inputs':{'policy':pol,'claim_cache_hit':cache,'claim_receipt':receipt,'action_id':a,'mutation':mutation,'removed_reservation_ids':ids,'public_completion':{'outcome_kind':'outcome_recorded','outcome_ref':'retrieval-local-outcome'},'network_calls':0},'original':original,'before':before,'before_normalized_excluding_timestamps':normalize(before),'recovery':recovery,'after_recovery':after_recover,'completion':complete,'after':after,'done_reuse':reuse,'after_done_reuse':after_reuse,'budget':budget}
 (d/'input_output.json').write_text(json.dumps(row,indent=2,ensure_ascii=False)+'\n');ROWS.append(row);print(json.dumps({'case':case,'action_id':a,'result':complete,'recovery':recovery,'budget_retrieval_total':budget['run_level']['max_retrievals_total']},ensure_ascii=False),flush=True)
 if mutation in ['remove_ref_only','remove_rows_only']:assert complete['error']=='SearchIntegrityError' and before==after==after_reuse
 else:assert complete['returned']['completed'] and reuse['returned'] and after==after_reuse
 l.store.close()
legal=ROWS[0];tampered=ROWS[4]
assert legal['inputs']['action_id']==tampered['inputs']['action_id'];assert legal['before_normalized_excluding_timestamps']==tampered['before_normalized_excluding_timestamps']
for case,cache in [('zero_retrieval_cache_hit',True),('zero_retrieval_non_cache',False)]:
 d=ROOT/case;d.mkdir();r=case;l=SearchLedger(PollutantPathwayStore(d/'run.sqlite'),ArtifactStore(d/'runs',r),r);pol=build_profile_identity_block();pol['search_limits']=validate_search_limits({'max_retrievals_per_parent':0,'max_retrievals_total':0});l.register_search_run(r,pol);a=l.enqueue_action(run_id=r,parent_path_id='p1',context_ref='ctx1',subject_ref='retrieve-query',action_kind='retrieve',depth=1,policy_version=search_policy_version(),payload={'task_key':'retrieve-task'})['action_id'];before=snap(l);receipt=cap(lambda:l.claim_action(a,worker_id='w1',cache_hit=cache));after=snap(l);row={'case':case,'inputs':{'policy':pol,'cache_hit':cache,'action_id':a},'before':before,'result':receipt,'after':after}
 (d/'input_output.json').write_text(json.dumps(row,indent=2,ensure_ascii=False)+'\n');ROWS.append(row);print(json.dumps({'case':case,'result':receipt},ensure_ascii=False),flush=True)
 if cache:assert receipt['returned']['claimed'] and len(after['budget_reservations'])==1
 else:assert receipt['error']=='SearchBudgetExhausted' and before==after
 l.store.close()
summary={'cases':len(ROWS),'legal_cache_hit_equivalent_to_noncache_deleted_two_refs_and_rows_after_ignoring_only_timestamps':True,'same_action_id_and_policy_payload':True,'persisted_cache_hit_column':False,'claim_inputs_cache_hit_not_in_any_persisted_row':True,'noncache_ref_only_and_rows_only_bad_controls_rejected':True,'legitimate_cache_hit_at_retrieval_zero':True,'noncache_retrieval_zero_rejected':True,'network_calls':0,'assertions_passed':True}
(P/'cache_boundary_observations.json').write_text(json.dumps({'summary':summary,'rows':ROWS},indent=2,ensure_ascii=False)+'\n');print(json.dumps({'summary':summary},ensure_ascii=False))
