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

print(json.dumps({'tag':TAG,'store_transaction_all_or_none':True,'runner_start_resume_failclosed':True},ensure_ascii=False))
