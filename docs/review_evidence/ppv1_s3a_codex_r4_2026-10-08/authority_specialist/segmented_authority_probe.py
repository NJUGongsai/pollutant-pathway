#!/usr/bin/env python3
"""Independent synthetic public chains, complete captures, no provider/network."""
from pathlib import Path
from dataclasses import asdict
import json, hashlib, sys, copy, sqlite3
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P/'repo/src'),str(P/'repo/tests')]
from s3a_worker import make_fixture
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.search import SearchLedger, search_policy_version, SEARCH_COMMIT_BUNDLE_VERSION
from pathway_v43.storage.artifact_store import ArtifactStore

ROOT=P/'segmented_cases'; ROOT.mkdir(exist_ok=False)
TABLES=['meta','states','state_appearances','hypotheses','events','report_projections',
        'expansion_plans','event_appearance_links','search_runs','search_actions',
        'search_attempts','budget_reservations','model_requests','search_commit_records']
ROWS=[]
def snapshot(l):
    return {t:[dict(r) for r in l.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in TABLES}
def cap(fn):
    try:return {'returned':fn()}
    except Exception as e:return {'error':type(e).__name__,'detail':getattr(e,'detail',{}),'text':str(e)}
def mk(name,run=None):
    d=ROOT/name;d.mkdir();r=run or name
    s=PollutantPathwayStore(d/'run.sqlite');art=ArtifactStore(d/'runs',r);l=SearchLedger(s,art,r)
    pol=build_profile_identity_block();l.register_search_run(r,pol)
    sub,prod,h,e,args=make_fixture(r,'p1','k1','ctx1')
    aid=l.enqueue_action(run_id=r,parent_path_id='p1',context_ref='ctx1',subject_ref=h.hypothesis_id,
        action_kind='expand_hypothesis',parent_search_revision=0,policy_version=search_policy_version(),
        payload={'task_key':'task1','frozen_pool_digest':'pool1'},depth=1)['action_id']
    receipt=l.claim_action(aid,worker_id='w1')
    return d,r,l,art,pol,sub,prod,h,e,args,aid,receipt
def fresh(d,r):return SearchLedger(PollutantPathwayStore(d/'run.sqlite'),ArtifactStore(d/'runs',r),r)
def emit(name,inp,out,correct_contract):
    row={'case':name,'inputs':inp,'output':out,'correct_contract':correct_contract}
    (ROOT/name/'input_output.json').write_text(json.dumps(row,ensure_ascii=False,indent=2,default=str)+'\n')
    ROWS.append(row)
    print(json.dumps({'case':name,'result':out.get('result'),'changed':out.get('before')!=out.get('after'),
                     'correct_contract':correct_contract},ensure_ascii=False,default=str),flush=True)
def bundle(event,args,aid,attempt,task='task1'):
    return {'bundle_version':SEARCH_COMMIT_BUNDLE_VERSION,'action_id':aid,'attempt_id':attempt,
            'event':asdict(event),**args,'task_key':task}
def input_rec(pol,e,args,aid,receipt):
    return {'policy':pol,'event':asdict(e),'event_args':args,'action_id':aid,'receipt':receipt}

# Same old independent event identities: write/submit and B3 each captured separately.
for change in ['run','parent','context','hypothesis']:
    name='identity_'+change;d,r,l,art,pol,sub,prod,h,e,args,aid,rec=mk(name,run='bundle_'+change)
    foreign={'run_id':r,'parent':'p1','origin':'k1','context':'ctx1'}
    foreign[{'run':'run_id','parent':'parent','context':'context','hypothesis':'origin'}[change]]='foreign_'+change if change!='hypothesis' else 'foreign_origin'
    _,_,_,fe,fa=make_fixture(foreign['run_id'],foreign['parent'],foreign['origin'],foreign['context'])
    before=snapshot(l)
    direct=cap(lambda:l.submit_action_event(aid,fe,worker_id='w1',**fa))
    write=cap(lambda:l.write_commit_bundle(action_id=aid,attempt_id=rec['attempt_refs'][0],event=fe,task_key='task1',**fa))
    after_write=snapshot(l);path=art._path('task1','search_commit_bundle');write_file_exists=path.exists()
    payload=bundle(fe,fa,aid,rec['attempt_refs'][0]);art.write('task1','search_commit_bundle',payload)
    artifact_original=path.read_bytes();l.store.close();l=fresh(d,r)
    b3_before=snapshot(l);first=cap(lambda:l.recover_run(r,policy_block=pol));after_first=snapshot(l)
    second=cap(lambda:l.recover_run(r,policy_block=pol));after_second=snapshot(l)
    emit(name,{'identity_change':change,'foreign_event':asdict(fe),'foreign_args':fa,'artifact_payload':payload,
               'action_receipt':rec,'policy':pol},
         {'direct':direct,'write':write,'write_file_exists':write_file_exists,'before':before,'after_write':after_write,
          'b3_before':b3_before,'result':first,'after':after_first,'second':second,'after_second':after_second,
          'artifact_sha256':hashlib.sha256(artifact_original).hexdigest(),'artifact_preserved':artifact_original==path.read_bytes()},
         'write/submit reject, B3 rejects before event/commit/consume; exact same valid artifact preserved')
    assert direct.get('error')=='SearchContractError' and write.get('error')=='SearchContractError'
    assert not write_file_exists and before==after_write and b3_before==after_first==after_second
    assert first['returned']['actions'][0]['disposition']['kind']=='bundle_event_identity_not_frozen'
    assert artifact_original==path.read_bytes();l.store.close()

for change in ['clean','empty','missing','foreign_parent']:
    name='first_complete_'+change;d,r,l,art,pol,sub,prod,h,e,args,aid,rec=mk(name)
    eid=e.event_id
    if change=='clean':l.submit_action_event(aid,e,worker_id='w1',**args)
    elif change=='empty':eid=''
    elif change=='missing':eid='nonexistent-event'
    else:
        _,_,_,fe,fa=make_fixture(r,'foreign-parent','k1','ctx1');l.store.submit_event(fe,**fa);eid=fe.event_id
    before=snapshot(l);result=cap(lambda:l.complete_action(aid,worker_id='w1',event_id=eid));after=snapshot(l)
    second=cap(lambda:l.complete_action(aid,worker_id='w1',event_id=eid));after_second=snapshot(l)
    emit(name,{**input_rec(pol,e,args,aid,rec),'supplied_event_id':eid},{'before':before,'result':result,'after':after,'second':second,'after_second':after_second},
         'clean completes once; empty/nonexistent/foreign event reject with zero success writes')
    if change=='clean':assert result['returned']['completed'] and second['returned']['unchanged'] and after==after_second
    else:assert 'error' in result and before==after==after_second
    l.store.close()

def mutate(l,kind,aid,rec,sub,prod,e):
    conn=l.conn
    rid=conn.execute("SELECT reservation_id FROM budget_reservations WHERE action_id=? AND limit_key='max_total_search_actions'",(aid,)).fetchone()[0]
    att=rec['attempt_refs'][0]
    if kind=='reservation_delete':conn.execute('DELETE FROM budget_reservations WHERE reservation_id=?',(rid,))
    elif kind=='reservation_units_zero':conn.execute('UPDATE budget_reservations SET units=0 WHERE reservation_id=?',(rid,))
    elif kind=='reservation_status_unknown':conn.execute("UPDATE budget_reservations SET status='unregistered-status' WHERE reservation_id=?",(rid,))
    elif kind=='reservation_scope_wrong':conn.execute("UPDATE budget_reservations SET scope='wrong-scope' WHERE reservation_id=?",(rid,))
    elif kind=='attempt_delete':conn.execute('DELETE FROM search_attempts WHERE expansion_attempt_id=?',(att,))
    elif kind=='attempt_abandoned':conn.execute("UPDATE search_attempts SET status='abandoned' WHERE expansion_attempt_id=?",(att,))
    elif kind=='attempt_hypothesis_wrong':conn.execute("UPDATE search_attempts SET hypothesis_id='other-hypothesis' WHERE expansion_attempt_id=?",(att,))
    elif kind=='attempt_task_wrong':conn.execute("UPDATE search_attempts SET task_key='other-task' WHERE expansion_attempt_id=?",(att,))
    elif kind=='commit_attempt_wrong':conn.execute("UPDATE search_commit_records SET attempt_id='missing-attempt' WHERE action_id=?",(aid,))
    elif kind=='commit_run_wrong':conn.execute("UPDATE search_commit_records SET run_id='other-run' WHERE action_id=?",(aid,))
    elif kind in ['projection_foreign_product','plan_foreign_product','plan_invalid_status','event_payload']:
        table='report_projections' if kind.startswith('projection') else 'events' if kind=='event_payload' else 'expansion_plans'
        payload=json.loads(conn.execute('SELECT payload FROM '+table+' WHERE event_id=?',(e.event_id,)).fetchone()[0])
        if kind=='projection_foreign_product':payload['product_ranks'][0]['state_ref']='nonexistent-state'
        elif kind=='plan_foreign_product':payload['entries'][0]['state_ref']='nonexistent-state'
        elif kind=='plan_invalid_status':payload['entries'][0]['status']='invalid-status'
        else:payload['participants']=[]
        conn.execute('UPDATE '+table+' SET payload=? WHERE event_id=?',(json.dumps(payload),e.event_id))
    elif kind=='clean':pass
    else:raise ValueError(kind)
    conn.commit()

# Frozen search references: every applicable public consumption path, including legal controls.
kinds=['clean','reservation_delete','reservation_units_zero','reservation_status_unknown','reservation_scope_wrong',
       'attempt_delete','attempt_abandoned','attempt_hypothesis_wrong','attempt_task_wrong']
for phase in ['first_complete','B4_recover','done_recover','done_claim','done_complete','done_submit','B1_recover','B3_recover']:
    for kind in kinds:
        name=phase+'__'+kind;d,r,l,art,pol,sub,prod,h,e,args,aid,rec=mk(name)
        if phase=='B3_recover':l.write_commit_bundle(action_id=aid,attempt_id=rec['attempt_refs'][0],event=e,task_key='task1',**args)
        elif phase!='B1_recover':l.submit_action_event(aid,e,worker_id='w1',**args)
        if phase.startswith('done_'):l.complete_action(aid,worker_id='w1',event_id=e.event_id)
        original=snapshot(l);mutation=cap(lambda:mutate(l,kind,aid,rec,sub,prod,e));before=snapshot(l)
        l.store.close();l=fresh(d,r)
        if phase=='first_complete' or phase=='done_complete':fn=lambda:l.complete_action(aid,worker_id='w1',event_id=e.event_id)
        elif phase=='done_claim':fn=lambda:l.claim_action(aid,worker_id='new-worker')
        elif phase=='done_submit':fn=lambda:l.submit_action_event(aid,e,worker_id='w1',**args)
        else:fn=lambda:l.recover_run(r,policy_block=pol)
        result=cap(fn);after=snapshot(l)
        emit(name,{**input_rec(pol,e,args,aid,rec),'phase':phase,'mutation':kind},
             {'mutation_result':mutation,'original':original,'before':before,'result':result,'after':after,
              'budget_after':cap(lambda:l.budget_snapshot(r))},
             'legal control allowed; corrupted frozen search reference must be refused before success consumption')
        assert 'error' not in mutation
        if kind=='clean':assert 'returned' in result
        l.store.close()

# Full event authority: stored projection/plan content must not validate by comparing to itself.
for phase in ['first_complete','B4_recover','done_recover','done_claim','done_complete','done_submit']:
    for kind in ['projection_foreign_product','plan_foreign_product','plan_invalid_status','event_payload']:
        name=phase+'__'+kind;d,r,l,art,pol,sub,prod,h,e,args,aid,rec=mk(name)
        l.submit_action_event(aid,e,worker_id='w1',**args)
        if phase.startswith('done_'):l.complete_action(aid,worker_id='w1',event_id=e.event_id)
        original=snapshot(l);mutate(l,kind,aid,rec,sub,prod,e);before=snapshot(l)
        if phase=='first_complete' or phase=='done_complete':fn=lambda:l.complete_action(aid,worker_id='w1',event_id=e.event_id)
        elif phase=='done_claim':fn=lambda:l.claim_action(aid,worker_id='other-worker')
        elif phase=='done_submit':fn=lambda:l.submit_action_event(aid,e,worker_id='w1',**args)
        else:fn=lambda:l.recover_run(r,policy_block=pol)
        result=cap(fn);after=snapshot(l);writer=cap(lambda:l.store.submit_event(e,**args));writer_after=snapshot(l)
        emit(name,{**input_rec(pol,e,args,aid,rec),'phase':phase,'mutation':kind},
             {'original':original,'before':before,'result':result,'after':after,'public_writer_original_input':writer,'writer_after':writer_after},
             'bad attached product/status or event payload rejected by search authority, zero write; original writer replay rejects')
        assert 'error' in writer and after==writer_after
        l.store.close()

# A valid commit hash does not establish unrelated commit row identity or attempt reference.
for phase in ['done_recover','done_claim','done_complete','done_submit']:
    for kind in ['commit_attempt_wrong','commit_run_wrong']:
        name=phase+'__'+kind;d,r,l,art,pol,sub,prod,h,e,args,aid,rec=mk(name)
        l.submit_action_event(aid,e,worker_id='w1',**args);l.complete_action(aid,worker_id='w1',event_id=e.event_id)
        original=snapshot(l);mutate(l,kind,aid,rec,sub,prod,e);before=snapshot(l)
        if phase=='done_complete':fn=lambda:l.complete_action(aid,worker_id='w1',event_id=e.event_id)
        elif phase=='done_claim':fn=lambda:l.claim_action(aid,worker_id='other-worker')
        elif phase=='done_submit':fn=lambda:l.submit_action_event(aid,e,worker_id='w1',**args)
        else:fn=lambda:l.recover_run(r,policy_block=pol)
        result=cap(fn);after=snapshot(l)
        emit(name,{**input_rec(pol,e,args,aid,rec),'phase':phase,'mutation':kind},{'original':original,'before':before,'result':result,'after':after},
             'commit run and attempt belong to frozen action; invalid references refused at reuse')
        l.store.close()

# H07 and H08 retain old failure behavior independently of the new semantic probes.
for kind in ['hash_bytes','invalid_json','bundle_version','bundle_task','bundle_attempt','event_delete','commit_delete','commit_event_tamper']:
    name='H07H08_'+kind;d,r,l,art,pol,sub,prod,h,e,args,aid,rec=mk(name)
    if kind.startswith('bundle') or kind in ['hash_bytes','invalid_json']:
        payload=bundle(e,args,aid,rec['attempt_refs'][0])
        if kind=='bundle_version':payload['bundle_version']='future'
        elif kind=='bundle_task':payload['task_key']='other-task'
        elif kind=='bundle_attempt':payload['attempt_id']='other-attempt'
        art.write('task1','search_commit_bundle',payload);path=art._path('task1','search_commit_bundle')
        if kind=='hash_bytes':
            x=json.loads(path.read_text());x['payload']['event']['context_hash']='tampered';path.write_text(json.dumps(x))
        elif kind=='invalid_json':path.write_text('{broken-json')
        original_bytes=path.read_bytes()
    else:
        l.submit_action_event(aid,e,worker_id='w1',**args);l.complete_action(aid,worker_id='w1',event_id=e.event_id)
        if kind=='event_delete':l.conn.execute('DELETE FROM events WHERE event_id=?',(e.event_id,))
        elif kind=='commit_delete':l.conn.execute('DELETE FROM search_commit_records WHERE action_id=?',(aid,))
        else:l.conn.execute("UPDATE search_commit_records SET event_id='other-event' WHERE action_id=?",(aid,))
        l.conn.commit();path=None
    before=snapshot(l);l.store.close();l=fresh(d,r);result=cap(lambda:l.recover_run(r,policy_block=pol));after=snapshot(l)
    emit(name,input_rec(pol,e,args,aid,rec),{'before':before,'result':result,'after':after,'artifact_preserved':True if path is None else original_bytes==path.read_bytes()},
         'integrity failure is explicit; original artifact/ledger preserved; zero success writes')
    assert before==after
    if path is None:assert 'error' in result
    else:assert result['returned']['actions'][0]['disposition']['error']=='SearchArtifactIntegrityError' and original_bytes==path.read_bytes()
    l.store.close()

(P/'segmented_observations.json').write_text(json.dumps(ROWS,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'summary':{'cases':len(ROWS),'capture_completed':True,'network_calls':0}}),flush=True)
