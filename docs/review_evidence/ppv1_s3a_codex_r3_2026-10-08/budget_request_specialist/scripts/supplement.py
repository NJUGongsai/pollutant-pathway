#!/usr/bin/env python3
"""Correct the audit priority oracle; verify damaged policy kind and exact old stop input."""
from pathlib import Path
import copy,itertools,json,sqlite3,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'source/src'),str(ROOT/'source/tests')]
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.search import SearchLedger,search_policy_version,resolve_search_stop,STOP_REASON_PRIORITY
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.storage.artifact_store import ArtifactStore
from s3a_worker import make_fixture
D=ROOT/'supplement_data';D.mkdir(exist_ok=False)
TABLES=['search_runs','search_actions','search_attempts','budget_reservations','model_requests','search_commit_records','events']
def rows(l):return {t:[dict(r) for r in l.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in TABLES}
def cap(fn):
 try:return {'accepted':True,'result':fn()}
 except Exception as e:return {'accepted':False,'exception':type(e).__name__,'kind':getattr(e,'detail',{}).get('kind'),'detail':getattr(e,'detail',{}),'message':str(e)}
def emit(row):print(json.dumps(row,ensure_ascii=False,sort_keys=True,default=str),flush=True)
priority=['user_stop','budget_limit','depth_limit','no_local_candidate','awaiting_prediction','exhausted_search'];out=[]
for size in range(1,7):
 for subset in itertools.combinations(priority,size):
  result=resolve_search_stop(set(subset));out.append({'input':list(subset),'output':result,'passed':result['primary']==subset[0] and set(result['other_reasons'])==set(subset[1:])})
emit({'case':'priority_corrected_original_order','fixed_original_order':priority,'actual_constant':list(STOP_REASON_PRIORITY),'subcases':out,'passed':all(r['passed'] for r in out),'correction':'Initial independent script swapped awaiting_prediction/no_local_candidate in expected list. Current and direct parent order unchanged; original 2 failed subset assertions were audit input error.'})
for damage in ['missing_version','null_limits']:
 for entry in ['budget','claim','recover_default','recover_frozen_expected','recover_damaged_expected']:
  name='policy_'+damage+'_'+entry;d=D/name;d.mkdir();s=PollutantPathwayStore(d/'run.sqlite');l=SearchLedger(s,None,name);p=build_profile_identity_block(search_limits={'max_total_search_actions':0});l.register_search_run(name,p)
  a=l.enqueue_action(run_id=name,parent_path_id='p1',context_ref='ctx1',subject_ref='pool_A',action_kind='decide',policy_version=search_policy_version(),payload={'task_key':'t'})['action_id'];frozen=copy.deepcopy(p)
  if damage=='missing_version':del p['search_limits']['version']
  else:p['search_limits']=None
  s.conn.execute('UPDATE search_runs SET policy_block=? WHERE run_id=?',(json.dumps(p),name));s.conn.commit();b=rows(l);fn={'budget':lambda:l.budget_snapshot(name),'claim':lambda:l.claim_action(a,worker_id='w'),'recover_default':lambda:l.recover_run(name),'recover_frozen_expected':lambda:l.recover_run(name,policy_block=frozen),'recover_damaged_expected':lambda:l.recover_run(name,policy_block=p)}[entry];o=cap(fn);af=rows(l)
  expected_kind='search_policy_identity_mismatch' if entry=='recover_frozen_expected' else 'search_policy_block_corrupt'
  checks={'expected_policy_guard':not o['accepted'] and o.get('kind')==expected_kind,'zero_success_writes':b==af}
  emit({'case':name,'group':'S3A-03','input':{'registered_total_action_limit':0,'original_frozen_policy':frozen,'damaged_policy':p,'mutation_only':'search_limits.version removed' if damage=='missing_version' else 'search_limits set null','entry':entry,'expected_policy_argument':frozen if entry=='recover_frozen_expected' else p if entry=='recover_damaged_expected' else None,'expected_error_kind':expected_kind},'before':b,'observed':o,'after':af,'checks':checks,'contract_passed':all(checks.values()),'network_requests':0});s.close()
# Capture the exact historical stop input (no preceding foreign bundle cases).
name='stop_claimed_only';d=D/name;d.mkdir();s=PollutantPathwayStore(d/'run.sqlite');art=ArtifactStore(d/'runs',name);l=SearchLedger(s,art,name);policy=build_profile_identity_block();l.register_search_run(name,policy);_,_,h,e,args=make_fixture(name,'p1','k1','ctx1');a=l.enqueue_action(run_id=name,parent_path_id='p1',context_ref='ctx1',subject_ref=h.hypothesis_id,action_kind='expand_hypothesis',parent_search_revision=0,policy_version=search_policy_version(),payload={'task_key':'task1','frozen_pool_digest':'pool1'},depth=1)['action_id'];rec=l.claim_action(a,worker_id='w1');b=rows(l);stop=l.stop_report(name);checks={'primary_none':stop['primary'] is None,'claimed_one':stop['unexplored']['claimed_actions']==1,'open_one':stop['unexplored']['open_attempts']==1,'no_writes':b==rows(l)}
emit({'case':'exact_old_stop_claimed_only_correct_contract','group':'S3A-05','input':{'policy':policy,'claimed_action':rec},'before':b,'observed':stop,'after':rows(l),'checks':checks,'contract_passed':all(checks.values()),'network_requests':0});s.close()
emit({'case':'runtime','python':sys.version,'sqlite':sqlite3.sqlite_version,'network_requests':0,'external_model_calls':0})
