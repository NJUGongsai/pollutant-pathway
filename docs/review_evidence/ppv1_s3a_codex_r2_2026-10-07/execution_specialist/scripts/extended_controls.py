#!/usr/bin/env python3
"""Supplemental public controls. Synthetic inputs, copied ordinary source only."""
from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,str(Path.cwd()/'tests'))
from s3a_worker import make_fixture
from test_ppv1_s3a_rework_r2 import make_run,enqueue,fresh_ledger,bundle_path
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.workflow.runner import start_run,resume_run,RunError
from pathway_v43.config import resolve_config

OUT=Path(sys.argv[1]);TAG=sys.argv[2];OUT.mkdir(parents=True)
def dump(name,x):(OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def table_rows(store):
    tables=[r[0] for r in store.conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {t:[dict(r) for r in store.conn.execute('SELECT * FROM "'+t+'" ORDER BY rowid')] for t in tables}
def error(exc):return {'type':type(exc).__name__,'message':str(exc),'detail':getattr(exc,'detail',{})}
def tree(p):return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(p.rglob('*')) if f.is_file()}

# Public store.submit_event must retain a real all-or-none transaction, including supplied state rows.
store=PollutantPathwayStore(OUT/'public_store.sqlite')
sub,prod,hyp,event,args=make_fixture('transaction-'+TAG,'p1','k1','ctx1')
bad_args=dict(args);bad_args['states']=[sub.to_dict()]
before=table_rows(store);trace=[];store.conn.set_trace_callback(trace.append)
try:store.submit_event(event,**bad_args)
except Exception as exc:bad={'error':error(exc)}
else:bad={'unexpected_success':True}
after=table_rows(store);bad.update(before=before,after=after,all_tables_equal=(before==after),trace=trace)
assert 'error' in bad and bad['all_tables_equal']
assert any(t=='BEGIN IMMEDIATE' for t in trace) and 'ROLLBACK' in trace
trace=[];store.conn.set_trace_callback(trace.append)
first=store.submit_event(event,**args);first_rows=table_rows(store);first_trace=trace
trace=[];store.conn.set_trace_callback(trace.append)
replay=store.submit_event(event,**args);replay_rows=table_rows(store)
assert first_rows==replay_rows
dump('public_store_transaction.json',{'bad_missing_product_state':bad,'first_result':first,'first_rows':first_rows,
     'first_trace':first_trace,'replay_result':replay,'replay_rows':replay_rows,'replay_trace':trace,'all_assertions_passed':True})
store.close()

# Both production runner entry points must refuse PPV1 before opening its execution graph.
config=resolve_config();root=OUT/'synthetic_runner'
start_before=tree(root)
try:start_run(config=config,runs_root=root,run_id='start',smiles='CCO',max_depth=2,max_expansions=5,max_frontier_width=3,
              finder=object(),scripted=True,profile='pollutant_pathway_v1')
except RunError as exc:start_error=error(exc)
else:raise AssertionError('PPV1 start accepted')
assert tree(root)==start_before and not (root/'start').exists()
resume_dir=root/'resume';resume_dir.mkdir(parents=True)
identity={'profile':{'name':'pollutant_pathway_v1'},'synthetic_review_fixture':True}
(resume_dir/'run_identity.json').write_text(json.dumps(identity))
resume_before=tree(root)
try:resume_run(config=config,runs_root=root,run_id='resume',finder=object())
except RunError as exc:resume_error=error(exc)
else:raise AssertionError('PPV1 resume accepted')
assert tree(root)==resume_before
dump('runner_refusal.json',{'start_error':start_error,'start_no_directory':not (root/'start').exists(),
     'resume_input':identity,'resume_error':resume_error,'resume_before':resume_before,'resume_after':tree(root),
     'all_assertions_passed':True,'scope':'synthetic PPV1 identity only; no historical actual run loaded'})

# Bare same-byte pytest baseline cases stop on return shape/kind. Here every B3 internal segment is captured separately.
cases=[]
for mutate in ['run','parent','context','hypothesis']:
    case_root=OUT/('b3_'+mutate);case_root.mkdir()
    name='b3-'+TAG+'-'+mutate
    store,ledger,art,policy,db,runs_root=make_run(case_root,name)
    _,_,hyp_a,_,_=make_fixture(name,'p1','k1','ctx1')
    out=enqueue(ledger,name,hyp_a.hypothesis_id);receipt=ledger.claim_action(out['action_id'],worker_id='w1')
    attempt=receipt['attempt_refs'][0]
    _,_,_,ev,evargs=make_fixture('other-run' if mutate=='run' else name,'p2' if mutate=='parent' else 'p1',
                                'k2' if mutate=='hypothesis' else 'k1','ctx2' if mutate=='context' else 'ctx1')
    payload={'bundle_version':'ppv1-search-commit-bundle-1','action_id':out['action_id'],'attempt_id':attempt,
             'event':{'schema_version':ev.schema_version,'event_id':ev.event_id,'run_id':ev.run_id,'parent_path_id':ev.parent_path_id,
                      'hypothesis_id':ev.hypothesis_id,'context_hash':ev.context_hash,'participants':list(ev.participants),
                      'participant_state_refs':list(ev.participant_state_refs),'catalytic_support':list(ev.catalytic_support)},
             **evargs,'task_key':'tk1'}
    art.write('tk1','search_commit_bundle',payload);path=bundle_path(runs_root,name,'tk1');artifact_before=path.read_bytes()
    before=table_rows(store)
    try:submit_return=ledger.submit_action_event(out['action_id'],ev,worker_id='w1',**evargs)
    except Exception as exc:submit={'error':error(exc)}
    else:submit={'return':submit_return}
    after_submit=table_rows(store)
    other=fresh_ledger(db,runs_root,name)
    try:recover={'return':other.recover_run(name)}
    except Exception as exc:recover={'error':error(exc)}
    after=table_rows(other.store)
    counts={t:len(rows) for t,rows in after.items()}
    record={'mutate':mutate,'input':payload,'before':before,'normal_submit':submit,'after_submit':after_submit,'recover':recover,
            'after_recover':after,'after_counts':counts,'artifact_preserved':path.read_bytes()==artifact_before,
            'all_internal_segments_executed':True,'normal_submit_zero_write':before==after_submit}
    dump('b3_'+mutate+'.json',record)
    cases.append({'mutate':mutate,'normal_submit':submit,'recover':recover,'after_counts':counts,
                  'artifact_preserved':record['artifact_preserved'],'all_internal_segments_executed':True})
    other.store.close();store.close()
dump('b3_summary.json',cases)
print(json.dumps({'tag':TAG,'store_transaction_all_or_none':True,'runner_start_resume_failclosed':True,'b3_cases':cases},ensure_ascii=False))
