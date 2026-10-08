#!/usr/bin/env python3
"""Synthetic sequential guards plus deterministic concurrent corruption injection."""
from pathlib import Path
from dataclasses import asdict
import sys,json,os,time,subprocess,sqlite3,copy
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P/'repo/src'),str(P/'repo/tests')]

def waiting(path):
    deadline=time.monotonic()+15
    while not path.exists():
        if time.monotonic()>deadline:raise TimeoutError(str(path))
        time.sleep(0.005)

def mutator(db,state_id,gate,kind):
    g=Path(gate);conn=sqlite3.connect(db,timeout=2)
    conn.row_factory=sqlite3.Row
    original=dict(conn.execute('SELECT * FROM states WHERE state_id=?',(state_id,)).fetchone())
    (g/'READY').write_text('ready\n');waiting(g/'GO')
    before=time.monotonic();result={'pid':os.getpid(),'argv':sys.argv,'cwd':os.getcwd(),'kind':kind,'original':original,'sql':[]}
    try:
        if kind=='corrupt':
            payload=json.loads(original['payload']);payload['formal_charge']=99
            result['sql']=[{'sql':'BEGIN IMMEDIATE','params':[]},{'sql':'UPDATE states SET payload=? WHERE state_id=?','params':[json.dumps(payload,sort_keys=True),state_id]},{'sql':'COMMIT','params':[]}]
            conn.execute('BEGIN IMMEDIATE');conn.execute('UPDATE states SET payload=? WHERE state_id=?',(json.dumps(payload,sort_keys=True),state_id));conn.commit()
        else:
            result['sql']=[{'sql':'SELECT payload FROM states WHERE state_id=?','params':[state_id]}]
            conn.execute('SELECT payload FROM states WHERE state_id=?',(state_id,)).fetchone()
        result['returned']=True
    except Exception as e:result.update(error=type(e).__name__,text=str(e),busy='locked' in str(e).lower())
    result['elapsed_seconds']=time.monotonic()-before
    result['after']=dict(conn.execute('SELECT * FROM states WHERE state_id=?',(state_id,)).fetchone())
    conn.close();(g/'mutator_result.json').write_text(json.dumps(result,indent=2)+'\n');(g/'DONE').write_text('done\n')
    print(json.dumps(result),flush=True);return 0

if len(sys.argv)>1 and sys.argv[1]=='--mutator':
    raise SystemExit(mutator(*sys.argv[2:]))

from s3a_worker import make_fixture
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.search import SearchLedger,search_policy_version
from pathway_v43.storage.artifact_store import ArtifactStore
ROOT=P/'supplementary_cases';ROOT.mkdir(exist_ok=False)
TABLES=['meta','states','state_appearances','hypotheses','events','report_projections','expansion_plans','event_appearance_links',
        'search_runs','search_actions','search_attempts','budget_reservations','model_requests','search_commit_records']
def snap(l):return {t:[dict(r) for r in l.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in TABLES}
def cap(fn):
    try:return {'returned':fn()}
    except Exception as e:return {'error':type(e).__name__,'detail':getattr(e,'detail',{}),'text':str(e)}
def mk(name):
    d=ROOT/name;d.mkdir();s=PollutantPathwayStore(d/'run.sqlite');a=ArtifactStore(d/'runs',name);l=SearchLedger(s,a,name)
    pol=build_profile_identity_block();l.register_search_run(name,pol);sub,prod,h,e,args=make_fixture(name,'p1','k1','ctx1')
    aid=l.enqueue_action(run_id=name,parent_path_id='p1',context_ref='ctx1',subject_ref=h.hypothesis_id,action_kind='expand_hypothesis',
        policy_version=search_policy_version(),payload={'task_key':'tk1'},depth=1)['action_id'];rec=l.claim_action(aid,worker_id='w1')
    return d,l,a,pol,sub,prod,h,e,args,aid,rec
def emit(d,row):
    (d/'input_output.json').write_text(json.dumps(row,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'case':d.name,'result':row.get('result'),'changed':row['before']!=row['after']},ensure_ascii=False),flush=True)

for kind in ['projection_foreign_product','plan_foreign_product','plan_invalid_status']:
    name='normal_first_submit_'+kind;d,l,a,pol,sub,prod,h,e,args,aid,rec=mk(name);bad=copy.deepcopy(args)
    if kind=='projection_foreign_product':bad['report_projection']['product_ranks'][0]['state_ref']='nonexistent-state'
    elif kind=='plan_foreign_product':bad['expansion_plan']['entries'][0]['state_ref']='nonexistent-state'
    else:bad['expansion_plan']['entries'][0]['status']='invalid-status'
    before=snap(l);res=cap(lambda:l.submit_action_event(aid,e,worker_id='w1',**bad));after=snap(l)
    emit(d,{'case':name,'inputs':{'event':asdict(e),'bad_event_args':bad,'policy':pol,'claim':rec},'before':before,'result':res,'after':after})
    assert 'error' in res and before==after;l.store.close()

for kind in ['clean','corrupt']:
    name='TOCTOU_'+kind;d,l,a,pol,sub,prod,h,e,args,aid,rec=mk(name);l.submit_action_event(aid,e,worker_id='w1',**args)
    gate=d/'barrier';gate.mkdir();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(P/'repo/src')+':'+str(P/'repo/tests'))
    argv=[sys.executable,'-B',str(Path(__file__).resolve()),'--mutator',str(d/'run.sqlite'),prod.state_id,str(gate),kind]
    proc=subprocess.Popen(argv,cwd=P/'repo',env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);waiting(gate/'READY')
    hook=[];original=l._preverify_completion
    def pausing_after_original(*args,**kwargs):
        item={'pid':os.getpid(),'start_monotonic':time.monotonic(),'original_in_transaction_before':l.conn.in_transaction}
        result=original(*args,**kwargs)
        item.update(original_return=result,original_in_transaction_after=l.conn.in_transaction,original_finished_monotonic=time.monotonic(),before_pause=snap(l))
        (gate/'GO').write_text('go\n');waiting(gate/'DONE')
        item.update(resume_monotonic=time.monotonic(),after_pause=snap(l));hook.append(item)
        return result
    l._preverify_completion=pausing_after_original
    before=snap(l);complete=cap(lambda:l.complete_action(aid,worker_id='w1',event_id=e.event_id));after=snap(l)
    stdout,stderr=proc.communicate(timeout=15);worker={'argv':argv,'cwd':str(P/'repo'),'env':{k:env[k] for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE')},'returncode':proc.returncode,'stdout':stdout,'stderr':stderr,
        'decoded':json.loads((gate/'mutator_result.json').read_text())}
    replay=cap(lambda:l.store.submit_event(e,**args));replay_after=snap(l)
    emit(d,{'case':name,'inputs':{'policy':pol,'event':asdict(e),'event_args':args,'claim':rec,'injection_kind':kind},'before':before,'result':complete,'after':after,'preverify_pause_hook':hook,
        'independent_process':worker,'public_writer_original_input':replay,'writer_after':replay_after,
        'scope':'Active concurrent bad-store injection, not shown to arise from legal immutable public writers; sequential single-consumer flow not interleaved.'})
    assert proc.returncode==0 and worker['decoded'].get('returned') and complete['returned']['completed'] and after==replay_after
    if kind=='clean':assert replay['returned']['created'] is False
    else:assert replay['error']=='Ppv1EventConflict' and replay['detail']['kind']=='state_semantic_conflict'
    l.store.close()
print(json.dumps({'summary':{'cases':5,'capture_completed':True,'network_calls':0}}),flush=True)
