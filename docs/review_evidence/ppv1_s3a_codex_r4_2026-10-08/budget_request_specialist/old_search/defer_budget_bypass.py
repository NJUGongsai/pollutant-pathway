#!/usr/bin/env python
"""Public deterministic positive of budget reuse after committed-event defer."""
import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path[:0]=[str(P/'repo/src'),str(P/'repo/tests')]
from s3a_worker import make_fixture
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.search import SearchLedger,search_policy_version
D=P/'defer_bypass_generated';D.mkdir(exist_ok=False);S=PollutantPathwayStore(D/'run.sqlite');L=SearchLedger(S,None,'defer_budget_loop');POL=build_profile_identity_block(search_limits={'max_total_search_actions':1,'max_alternative_hypotheses_per_parent':1,'max_attempts_per_hypothesis':1});L.register_search_run('defer_budget_loop',POL);STEPS=[]
for i in range(3):
 sub,prod,h,e,args=make_fixture('defer_budget_loop','p1','new_alternative_'+str(i),'ctx1')
 a=L.enqueue_action(run_id='defer_budget_loop',parent_path_id='p1',context_ref='ctx1',subject_ref=h.hypothesis_id,action_kind='expand_hypothesis',parent_search_revision=i,policy_version=search_policy_version(),payload={'task_key':'tk'+str(i),'frozen_pool_digest':'pool'},depth=1)['action_id'];claim=L.claim_action(a,worker_id='worker');submitted=L.submit_action_event(a,e,worker_id='worker',**args);before=L.budget_snapshot('defer_budget_loop');deferred=L.defer_action(a,worker_id='worker',reason='explicitly after actual submission');after=L.budget_snapshot('defer_budget_loop');STEPS.append({'input':{'hypothesis':h.to_dict(),'event':vars(e),'submit_args':args},'output':{'claim':claim,'submit':submitted,'budget_before_defer':before,'defer':deferred,'budget_after_defer':after}})
rows={t:[dict(r) for r in L.conn.execute('SELECT * FROM '+t)] for t in ['events','search_actions','search_attempts','budget_reservations','search_commit_records']};assert len(rows['events'])==3 and len(rows['search_attempts'])==3 and L.budget_snapshot('defer_budget_loop')['run_level']['max_total_search_actions']['used']==0
row={'case':'defer_overbudget_three_events','input':{'policy':POL,'steps':STEPS},'output':{'rows':rows,'stop':L.stop_report('defer_budget_loop'),'actual_committed_events':3,'per_parent_distinct_hypotheses_explored':3},'observed_assertion':'limits total_actions=1 and parent_alternatives=1, yet 3 real committed events retained, 3 distinct explored hypotheses, used=0 via submit->defer'};print(json.dumps(row,ensure_ascii=False));(P/'defer_bypass_observation.json').write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n');S.close()
