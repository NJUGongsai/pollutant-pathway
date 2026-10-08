#!/usr/bin/env python3
"""Two fresh synthetic completed-result reuse cases, no repeated matrix."""
from pathlib import Path
from dataclasses import asdict
import sys,json
P=Path(__file__).resolve().parent;sys.path[:0]=[str(P/'repo/src'),str(P/'repo/tests')]
from s3a_worker import make_fixture
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.search import SearchLedger,search_policy_version
from pathway_v43.storage.artifact_store import ArtifactStore
TABLES=['meta','states','state_appearances','hypotheses','events','report_projections','expansion_plans','event_appearance_links',
        'search_runs','search_actions','search_attempts','budget_reservations','model_requests','search_commit_records']
ROOT=P/'done_result_reuse_cases';ROOT.mkdir(exist_ok=False)
def snap(l):return {t:[dict(x) for x in l.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in TABLES}
for change in ['same_event','foreign_parent']:
    name='done_result_'+change;d=ROOT/name;d.mkdir();s=PollutantPathwayStore(d/'run.sqlite');l=SearchLedger(s,ArtifactStore(d/'runs',name),name)
    policy=build_profile_identity_block();l.register_search_run(name,policy);sub,prod,h,e,args=make_fixture(name,'p1','k1','ctx1')
    aid=l.enqueue_action(run_id=name,parent_path_id='p1',context_ref='ctx1',subject_ref=h.hypothesis_id,action_kind='expand_hypothesis',
        depth=1,policy_version=search_policy_version(),payload={'task_key':'tk1'})['action_id'];rec=l.claim_action(aid,worker_id='w1')
    l.submit_action_event(aid,e,worker_id='w1',**args);l.complete_action(aid,worker_id='w1',event_id=e.event_id)
    fe,fa=e,args;foreign_validated=None
    if change=='foreign_parent':
        _,_,_,fe,fa=make_fixture(name,'different-parent','k1','ctx1')
        other=PollutantPathwayStore(d/'separate_foreign_validity.sqlite');foreign_validated=other.submit_event(fe,**fa);other.close()
    before=snap(l)
    try:result=l.submit_action_event(aid,fe,worker_id='w1',**fa)
    except Exception as exc:result={'error':type(exc).__name__,'detail':getattr(exc,'detail',{}),'text':str(exc)}
    after=snap(l)
    committed=l.conn.execute('SELECT event_id FROM search_commit_records WHERE action_id=?',(aid,)).fetchone()[0]
    row={'case':name,'inputs':{'policy':policy,'claimed_action':rec,'original_event':asdict(e),'original_args':args,'supplied_event':asdict(fe),'supplied_args':fa},
        'foreign_event_validated_separate_public_store':foreign_validated,'before':before,'result':result,'after':after,
        'recorded_completed_event_id':committed,'returned_event_exists_in_current_store':l.store.get_event(result.get('event_id','')) is not None,
        'returned_completed_reference_correct':result.get('event_id')==committed,'changed':before!=after}
    (d/'input_output.json').write_text(json.dumps(row,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in row.items() if k not in ['inputs','before','after']},ensure_ascii=False),flush=True)
    assert before==after
    if change=='same_event':assert result['reason']=='already_completed' and not result['created'] and result['event_id']==committed
    else:assert result.get('error')=='SearchIdentityConflict' and foreign_validated['created']
    l.store.close()
print(json.dumps({'summary':{'cases':2,'capture_completed':True,'network_calls':0}}))
