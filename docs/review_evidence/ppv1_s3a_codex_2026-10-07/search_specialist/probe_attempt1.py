#!/usr/bin/env python
"""Only synthetic cases; run with isolated source/vendor and fresh output root."""
import sys,json,hashlib,subprocess,os,time
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P/'repo/src'),str(P/'repo/tests')]
from s3a_worker import make_fixture
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.search import SearchLedger,search_policy_version,commit_search_event,SearchCrashInjection
from pathway_v43.storage.artifact_store import ArtifactStore
from pathway_v43.domain.models import content_hash
DATA=P/'generated';DATA.mkdir(exist_ok=False)
OUT=[]
def emit(name,inp,out,assertion):
    row={'case':name,'input':inp,'output':out,'observed_assertion':assertion};OUT.append(row);print(json.dumps(row,ensure_ascii=False,default=str),flush=True)
def capture(fn):
    try:return {'returned':fn()}
    except Exception as e:return {'error':type(e).__name__,'detail':getattr(e,'detail',{}),'text':str(e)}
def mk(name,limits=None):
    d=DATA/name;d.mkdir();store=PollutantPathwayStore(d/'run.sqlite');art=ArtifactStore(d/'runs',name);ledger=SearchLedger(store,art,name);policy=build_profile_identity_block(search_limits=limits) if limits else build_profile_identity_block();ledger.register_search_run(name,policy);return store,ledger,art,policy,d
def enqueue(l,r,hyp,*,parent='p1',ctx='ctx1',tk='task1',rev=0,depth=1):
    return l.enqueue_action(run_id=r,parent_path_id=parent,context_ref=ctx,subject_ref=hyp.hypothesis_id,action_kind='expand_hypothesis',parent_search_revision=rev,policy_version=search_policy_version(),payload={'task_key':tk,'frozen_pool_digest':'pool1'},depth=depth)['action_id']
def counts(l):
    return {t:l.conn.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['events','search_actions','search_attempts','budget_reservations','search_commit_records','model_requests']}
def rows(l):
    return {t:[dict(r) for r in l.conn.execute('SELECT * FROM '+t)] for t in ['events','search_actions','search_attempts','budget_reservations','search_commit_records','model_requests']}
# Legal bundle positive and four independently valid foreign event identities.
for change in ['positive','run','parent','context','hypothesis']:
    r='bundle_'+change;s,l,a,policy,d=mk(r);_,_,h,ev,args=make_fixture(r,'p1','k1','ctx1');aid=enqueue(l,r,h);receipt=l.claim_action(aid,worker_id='w1');att=receipt['attempt_refs'][0]
    foreign={'run_id':r,'parent':'p1','origin':'k1','context':'ctx1'}
    if change=='run':foreign['run_id']='foreign_run'
    if change=='parent':foreign['parent']='foreign_parent'
    if change=='context':foreign['context']='foreign_context'
    if change=='hypothesis':foreign['origin']='foreign_origin'
    _,_,fh,fe,fa=make_fixture(foreign['run_id'],foreign['parent'],foreign['origin'],foreign['context'])
    direct=capture(lambda:l.submit_action_event(aid,fe,worker_id='w1',**fa)) if change!='positive' else {'not_run':'preserve B3 positive'}
    bundle=l.write_commit_bundle(action_id=aid,attempt_id=att,event=fe,task_key='task1',**fa)
    before=counts(l);path=a._path('task1','search_commit_bundle');bh=hashlib.sha256(path.read_bytes()).hexdigest();s.close()
    s=PollutantPathwayStore(d/'run.sqlite');l=SearchLedger(s,ArtifactStore(d/'runs',r),r)
    recovered=capture(lambda:l.recover_run(r,policy_block=policy));after=counts(l);state=rows(l)
    if change=='positive':assert 'returned' in recovered and after['events']==1 and l.action(aid)['status']=='done'
    else:assert direct.get('error')=='SearchContractError' and 'returned' in recovered and after['events']==1 and l.action(aid)['status']=='done'
    emit('b3_'+change,{'action':receipt,'foreign_event':fe.to_dict() if hasattr(fe,'to_dict') else vars(fe),'submit_args':fa,'bundle_payload':bundle['payload']},{'direct':direct,'recovery':recovered,'counts_before':before,'counts_after':after,'rows':state,'bundle_original_sha256':bh,'bundle_preserved':bh==hashlib.sha256(path.read_bytes()).hexdigest()},'foreign current-action binding refused direct, accepted recovery' if change!='positive' else 'legal B3 consumed once')
    s.close()
# Complete nonexistent/mismatched event; public writes then late H08 catches.
for change in ['positive','missing','foreign_event']:
    r='complete_'+change;s,l,a,policy,d=mk(r);_,_,h,ev,args=make_fixture(r,'p1','k1','ctx1');aid=enqueue(l,r,h);receipt=l.claim_action(aid,worker_id='w1')
    if change=='positive':l.submit_action_event(aid,ev,worker_id='w1',**args);eid=ev.event_id
    elif change=='missing':eid='does_not_exist'
    else:
        _,_,fh,fe,fa=make_fixture(r,'foreign_parent','k1','ctx1');s.submit_event(fe,**fa);eid=fe.event_id
    before=counts(l);res=capture(lambda:l.complete_action(aid,worker_id='w1',event_id=eid));after=counts(l);recovered=capture(lambda:l.recover_run(r,policy_block=policy))
    assert 'returned' in res and res['returned']['completed'] and l.action(aid)['status']=='done'
    if change=='positive':assert 'returned' in recovered
    else:assert recovered.get('error')=='SearchIntegrityError'
    emit('complete_'+change,{'action':receipt,'event_id':eid},{'complete':res,'recover':recovered,'counts_before':before,'counts_after':after,'rows':rows(l)},'first completion accepted inconsistent event; only later recovery rejects' if change!='positive' else 'legal completion verifies')
    s.close()
# Existing B4 event payload corrupted: normal writer replay rejects but recover completes from identity columns.
for change in ['positive','event_payload','reservations_deleted','attempts_deleted']:
    r='b4_'+change;s,l,a,policy,d=mk(r);_,_,h,ev,args=make_fixture(r,'p1','k1','ctx1');aid=enqueue(l,r,h);receipt=l.claim_action(aid,worker_id='w1');l.submit_action_event(aid,ev,worker_id='w1',**args)
    edit=None
    if change=='event_payload':
        er=s.get_event(ev.event_id);original=er['payload'];bad=json.loads(original);bad['participants']=[];s.conn.execute('UPDATE events SET payload=? WHERE event_id=?',(json.dumps(bad),ev.event_id));s.conn.commit();edit={'before':json.loads(original),'after':bad}
    elif change=='reservations_deleted':
        edit={'before':[dict(x) for x in l.conn.execute('SELECT * FROM budget_reservations')]};s.conn.execute('DELETE FROM budget_reservations');s.conn.commit()
    elif change=='attempts_deleted':
        edit={'before':[dict(x) for x in l.conn.execute('SELECT * FROM search_attempts')]};s.conn.execute('DELETE FROM search_attempts');s.conn.commit()
    direct=capture(lambda:s.submit_event(ev,**args)) if change=='event_payload' else {'not_run':'irrelevant to deleted search records'}
    before=rows(l);s.close();s=PollutantPathwayStore(d/'run.sqlite');l=SearchLedger(s,ArtifactStore(d/'runs',r),r);recovered=capture(lambda:l.recover_run(r,policy_block=policy));after=rows(l)
    assert 'returned' in recovered and l.action(aid)['status']=='done'
    if change=='event_payload':assert direct.get('error')=='LedgerCorrupt'
    emit('b4_'+change,{'action':receipt,'submit_args':args,'edit':edit},{'normal_writer_replay':direct,'recovery':recovered,'rows_before':before,'rows_after':after},'recovery marks done using incomplete or corrupt authority' if change!='positive' else 'legal B4 completes')
    s.close()
# Defer after event submission releases already executed action/attempt/alt counts.
for change in ['unexecuted_positive','event_submitted']:
    r='defer_'+change;s,l,a,policy,d=mk(r,{'max_total_search_actions':1,'max_alternative_hypotheses_per_parent':1,'max_attempts_per_hypothesis':1});_,_,h,ev,args=make_fixture(r,'p1','k1','ctx1');aid=enqueue(l,r,h);receipt=l.claim_action(aid,worker_id='w1')
    if change=='event_submitted':l.submit_action_event(aid,ev,worker_id='w1',**args)
    b=l.budget_snapshot(r);before=counts(l);res=capture(lambda:l.defer_action(aid,worker_id='w1',reason='later'));after=counts(l);af=l.budget_snapshot(r)
    assert 'returned' in res and af['run_level']['max_total_search_actions']['used']==0
    emit('defer_'+change,{'action':receipt},{'defer':res,'budget_before':b,'budget_after':af,'counts_before':before,'counts_after':after,'rows':rows(l)},'completed chemical event retained, executed budgets released' if change=='event_submitted' else 'unexecuted defer legitimately releases')
    s.close()
# Held action is unseen by H05 unexplored; held default budgets not exhausted.
r='stop_claimed_only';s,l,a,policy,d=mk(r);_,_,h,ev,args=make_fixture(r,'p1','k1','ctx1');aid=enqueue(l,r,h);rec=l.claim_action(aid,worker_id='w1');stop=l.stop_report(r);assert stop['primary']=='exhausted_search'
emit('stop_claimed_only',{'claimed_action':rec},{'stop':stop,'rows':rows(l)},'in-flight unrecovered claimed action omitted, exhausted_search reported');s.close()
# Reopen max zero but repeated new revisions supplied no reopen_of: 3 attempts bypass max_reopens.
r='reopen_omitted';s,l,a,policy,d=mk(r,{'max_attempts_per_hypothesis':4,'max_reopens_per_hypothesis':0});_,_,h,ev,args=make_fixture(r,'p1','k1','ctx1');receipts=[]
for i in range(3):
    aid=enqueue(l,r,h,rev=i,tk='task'+str(i));rec=l.claim_action(aid,worker_id='w1');l.complete_action(aid,worker_id='w1',outcome_kind='outcome_recorded',outcome_ref='failed'+str(i),attempt_status='failed');receipts.append(rec)
budget=l.budget_snapshot(r);assert len(rows(l)['search_attempts'])==3 and not budget['scoped']['max_reopens_per_hypothesis']
emit('reopen_omitted',{'same_hypothesis':h.to_dict(),'receipts':receipts,'policy':policy},{'budget':budget,'rows':rows(l)},'repeat semantic attempts without reopen_of bypass max_reopens=0; revision change itself not evidence of new information');s.close()
(P/'observations.json').write_text(json.dumps(OUT,ensure_ascii=False,indent=2,default=str)+'\n')
print(json.dumps({'summary':{'cases':len(OUT),'assertions':'all observed assertions passed','network_request_count':0}},ensure_ascii=False))
