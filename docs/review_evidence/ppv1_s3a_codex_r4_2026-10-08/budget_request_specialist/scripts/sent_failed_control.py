#!/usr/bin/env python3
"""One untested lawful sent->failed control for the unknown-status contrast."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'source/src'),str(ROOT/'source/tests')]
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.search import SearchLedger,search_policy_version
from pathway_v43.pollutant.store import PollutantPathwayStore
from s3a_worker import make_fixture
D=ROOT/'sent_failed_control_data';D.mkdir(exist_ok=False);s=PollutantPathwayStore(D/'run.sqlite');l=SearchLedger(s,None,'legal_sent_failed');p=build_profile_identity_block();l.register_search_run(l.run_id,p);_,_,h,e,args=make_fixture(l.run_id,'p1','k1','ctx1');a=l.enqueue_action(run_id=l.run_id,parent_path_id='p1',context_ref='ctx1',subject_ref=h.hypothesis_id,action_kind='expand_hypothesis',policy_version=search_policy_version(),payload={'task_key':'task_legal_sent_failed','frozen_pool_digest':'pool_A'},depth=1)['action_id'];receipt=l.claim_action(a,worker_id='w');att=receipt['attempt_refs'][0];r=l.register_model_request(run_id=l.run_id,action_id=a,attempt_id=att,provider_kind='scripted',request_key='rk',payload={'prompt':'original'},purpose='rank');l.record_request_sent(r['request_id']);TABLES=['search_runs','search_actions','search_attempts','budget_reservations','model_requests','search_commit_records','events']
def rows():return {t:[dict(r) for r in l.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in TABLES}
b=rows();o=l.mark_request_failed(r['request_id']);af=rows();ck={'sent_to_failed':b['model_requests'][0]['status']=='sent' and af['model_requests'][0]['status']=='failed','network_zero':af['model_requests'][0]['network_request_count']==0,'reservation_not_refunded':b['budget_reservations']==af['budget_reservations']};assert all(ck.values());print(json.dumps({'case':'legal_sent_to_failed','group':'S3A-04','input':{'policy':p,'request':r},'before':b,'observed':{'accepted':True,'result':o},'after':af,'checks':ck,'contract_passed':True,'actual_network_requests':0},ensure_ascii=False,sort_keys=True));s.close()
