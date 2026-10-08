#!/usr/bin/env python3
"""Synthetic public S3a interfaces vs the established writer/replay contract.

Run only with isolated source in PYTHONPATH and a fresh --out directory.
No real questions, gold, assets, network, or production runner success path.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, sys
from dataclasses import asdict
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True)
    args=ap.parse_args(); out=Path(args.out)
    out.mkdir(parents=True,exist_ok=False)
    from s3a_worker import make_fixture
    from pathway_v43.pollutant.profile import build_profile_identity_block
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.pollutant.search import SearchLedger,search_policy_version
    from pathway_v43.storage.artifact_store import ArtifactStore

    def snapshot(store):
        tables=['meta','states','state_appearances','hypotheses','events',
          'report_projections','expansion_plans','event_appearance_links',
          'search_runs','search_actions','search_attempts','budget_reservations',
          'model_requests','search_commit_records']
        return {t:[dict(r) for r in store.conn.execute(f'SELECT * FROM {t} ORDER BY rowid').fetchall()] for t in tables}
    def capture(fn):
        try:return {'returned':fn()}
        except Exception as e:return {'error':type(e).__name__,'detail':getattr(e,'detail',{}),'message':str(e)}
    def mutate(store,kind,sub,prod,hyp,event):
        conn=store.conn
        def edit(table,keycol,key,fn):
            r=conn.execute(f'SELECT payload FROM {table} WHERE {keycol}=?',(key,)).fetchone()
            p=json.loads(r['payload']); fn(p)
            conn.execute(f'UPDATE {table} SET payload=? WHERE {keycol}=?',(json.dumps(p,ensure_ascii=False,sort_keys=True),key))
        if kind=='state_charge':edit('states','state_id',prod.state_id,lambda p:p.update(formal_charge=99))
        elif kind=='state_schema':edit('states','state_id',prod.state_id,lambda p:p.update(schema_version='chemstate-future'))
        elif kind=='appearance_source':edit('state_appearances','state_id',prod.state_id,lambda p:p.update(source_refs=[{'record':'tampered'}]))
        elif kind=='appearance_raw':edit('state_appearances','state_id',sub.state_id,lambda p:p.update(structure_smiles_raw='CCO |r|'))
        elif kind=='hypothesis_origin':edit('hypotheses','hypothesis_id',hyp.hypothesis_id,lambda p:p.update(origin_group_key='tampered-origin'))
        elif kind=='event_payload':edit('events','event_id',event.event_id,lambda p:p.update(participants=[]))
        elif kind=='event_manifest':edit('events','event_id',event.event_id,lambda p:p.update(event_appearance_manifest=[]))
        elif kind in ('projection_delete','plan_delete','links_delete'):
            table={'projection_delete':'report_projections','plan_delete':'expansion_plans','links_delete':'event_appearance_links'}[kind]
            conn.execute(f'DELETE FROM {table} WHERE event_id=?',(event.event_id,))
        elif kind in ('state_delete','appearance_delete'):
            table={'state_delete':'states','appearance_delete':'state_appearances'}[kind]
            conn.execute(f'DELETE FROM {table} WHERE state_id=?',(prod.state_id,))
        elif kind=='hypothesis_delete':conn.execute('DELETE FROM hypotheses WHERE hypothesis_id=?',(hyp.hypothesis_id,))
        elif kind!='clean':raise ValueError(kind)
        conn.commit()
    kinds=['clean','state_charge','state_schema','appearance_source','appearance_raw',
      'hypothesis_origin','event_manifest','projection_delete',
      'plan_delete','links_delete','state_delete','appearance_delete','hypothesis_delete']
    for phase in ('B4_before_bookkeeping','done_before_recover'):
      for kind in kinds:
        case=out/(phase+'__'+kind);case.mkdir();run=phase+'-'+kind
        db=case/'synthetic.sqlite'; store=PollutantPathwayStore(db)
        ledger=SearchLedger(store,ArtifactStore(case/'runs',run),run)
        policy=build_profile_identity_block();ledger.register_search_run(run,policy)
        sub,prod,hyp,event,evargs=make_fixture(run,'parent-A','origin-A','context-A')
        enq=ledger.enqueue_action(run_id=run,parent_path_id='parent-A',context_ref='context-A',
          subject_ref=hyp.hypothesis_id,action_kind='expand_hypothesis',depth=1,
          policy_version=search_policy_version(),payload={'task_key':'task-A'})
        claim=ledger.claim_action(enq['action_id'],worker_id='worker-A')
        submitted=ledger.submit_action_event(enq['action_id'],event,worker_id='worker-A',**evargs)
        if phase=='done_before_recover':ledger.complete_action(enq['action_id'],worker_id='worker-A',event_id=event.event_id)
        original=snapshot(store); mutate(store,kind,sub,prod,hyp,event)
        before=snapshot(store); store.close()
        store=PollutantPathwayStore(db);ledger=SearchLedger(store,ArtifactStore(case/'runs',run),run)
        recovery=capture(lambda:ledger.recover_run(run,policy_block=policy))
        after=snapshot(store)
        # Exact same stored authority is consumed by old public writer replay:
        # incoming payload never repairs missing/corrupted rows.
        replay=capture(lambda:store.submit_event(event,**evargs))
        replay_after=snapshot(store)
        row={'case':case.name,'phase':phase,'mutation':kind,
          'inputs':{'policy':policy,'action':enq,'claim':claim,'event':asdict(event),**evargs},
          'first_submit':submitted,'original':original,'before':before,
          'recovery':recovery,'after':after,'public_writer_replay':replay,
          'replay_after':replay_after,'recovery_changed':before!=after,
          'replay_changed':after!=replay_after}
        (case/'input_output.json').write_text(json.dumps(row,indent=2,ensure_ascii=False))
        print(json.dumps({'case':case.name,'recovery':recovery,'public_writer_replay':replay,
          'recovery_changed':before!=after,'replay_changed':after!=replay_after},ensure_ascii=False),flush=True)
        store.close()

    # Direct submit refuses invalid raw and preserves no-success / zero-write.
    case=out/'first_submit_raw_guard';case.mkdir();run='direct-raw'
    store=PollutantPathwayStore(case/'synthetic.sqlite');ledger=SearchLedger(store,None,run)
    policy=build_profile_identity_block();ledger.register_search_run(run,policy)
    sub,prod,hyp,event,evargs=make_fixture(run,'parent-A','origin-A','context-A')
    enq=ledger.enqueue_action(run_id=run,parent_path_id='parent-A',context_ref='context-A',
      subject_ref=hyp.hypothesis_id,action_kind='expand_hypothesis',depth=1,
      policy_version=search_policy_version(),payload={'task_key':'task-A'})
    ledger.claim_action(enq['action_id'],worker_id='worker-A')
    bad=copy.deepcopy(evargs);bad['states'][0]['structure_smiles_raw']='CCO |r|'
    before=snapshot(store);res=capture(lambda:ledger.submit_action_event(enq['action_id'],event,worker_id='worker-A',**bad));after=snapshot(store)
    row={'case':case.name,'event':asdict(event),'inputs':bad,'before':before,'result':res,'after':after,'changed':before!=after}
    (case/'input_output.json').write_text(json.dumps(row,indent=2,ensure_ascii=False))
    print(json.dumps({'case':case.name,'result':res,'changed':before!=after},ensure_ascii=False),flush=True)
    store.close()

if __name__=='__main__':main()
