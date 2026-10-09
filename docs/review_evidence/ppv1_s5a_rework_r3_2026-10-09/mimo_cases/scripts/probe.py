from __future__ import annotations
import copy, hashlib, json, sqlite3, sys
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
SCRATCH=HERE.parent
sys.path[:0]=[str(SCRATCH/'iso'/'src'),str(SCRATCH/'iso'/'tests')]
from pathway_v43.pollutant.path_context import (ConditionFact,PathContext,
    build_condition_fact,build_requirement,build_path_context,
    aggregate_environment_fit,validate_context_object,_recompute_context_hash)
from pathway_v43.pollutant.evaluation import _classify_condition_requirement_detailed
from pathway_v43.pollutant.production import persist_context,load_context,CONTEXT_ARTIFACT_NAME
from pathway_v43.storage.artifact_store import ArtifactStore
from pathway_v43.domain.models import content_hash
from pathway_v43.config import resolve_config
from pathway_v43.workflow.runner import start_run,resume_run
from pathway_v43.storage.run_identity import PROFILE_POLLUTANT_PATHWAY_V1
from test_ppv1_s4a_endpoint import spec

def save(name,obj):
    p=HERE/'results'/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=str)+'\n')
def cap(fn,*args,**kwargs):
    try:return {'ok':True,'return':fn(*args,**kwargs)}
    except Exception as e:return {'ok':False,'type':type(e).__name__,'error':str(e),'detail':getattr(e,'detail',None)}
def table_snapshot(path):
    c=sqlite3.connect(path);c.row_factory=sqlite3.Row
    d={}
    for row in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        n=row[0];d[n]=[dict(x) for x in c.execute('SELECT * FROM '+n+' ORDER BY rowid')]
    c.close();return d

def checked_scope():
    cases=[]
    for key,value,unit in [('electron_acceptor','O2',''),('electron_donor','acetate',''),
        ('growth_substrate','glucose',''),('temperature_C',25,'C'),('pH',7,''),
        ('oxygen_regime','aerobic',''),('matrix','activated_sludge','')]:
        requirement={'key':key,'value_or_interval':str(value),'unit':unit,'status':'known_present',
          'required':'essential','source_refs':['src:synthetic-requirement'],'subject_scenario_ref':''}
        for known_status in (['known_present','known_absent'] if key in ('electron_acceptor','electron_donor','growth_substrate') else ['known_present']):
            raw=[{'key':key,'value':value,'unit':unit,'status':known_status,'source_ref':'src:known'},
                 {'key':key,'value':value,'unit':unit,'status':'unknown','source_ref':'src:unknown'}]
            for order in ('known_first','unknown_first'):
                facts=raw if order=='known_first' else list(reversed(raw))
                checked=[build_condition_fact(**f) for f in facts]
                result=_classify_condition_requirement_detailed(requirement,facts)
                cases.append({'key':key,'known_status':known_status,'order':order,
                  'requirement':requirement,'raw_facts':facts,'checked_facts':[f.to_dict() for f in checked],'result':result})
    save('checked_key_families.json',cases)
    for a,b in zip(cases[::2],cases[1::2]):
        assert a['result']['classification']==b['result']['classification']
        expected=('compatible' if a['known_status']=='known_present' else 'essential_conflict') if a['key'] in ('electron_acceptor','electron_donor','growth_substrate') else 'condition_unknown'
        assert a['result']['classification']==expected,(a['key'],a['result'])
    unit_fact={'key':'electron_acceptor','value':'O2','unit':'mg/L','status':'known_present','source_ref':'src:synthetic-fact'}
    unit_req={'key':'electron_acceptor','value_or_interval':'O2','unit':'','status':'known_present',
      'required':'essential','source_refs':['src:synthetic-requirement'],'subject_scenario_ref':''}
    observed=_classify_condition_requirement_detailed(unit_req,[unit_fact])
    save('species_fact_unit_narrow_semantics.json',{'requirement':unit_req,'fact':unit_fact,'result':observed,
      'scope':'public single-condition classification; entity presence only, no concentration threshold claimed'})
    assert observed['classification']=='compatible'
    return len(cases)

def restore_scope():
    rows=[]
    req=build_requirement(key='electron_acceptor',level='essential',value='O2',source_refs=['src:synthetic-necessity'])
    known=build_condition_fact(key='electron_acceptor',value='O2',status='known_present',source_ref='src:known')
    # Deliberate low-level bypass: UNKNOWN is supplied a value that the checked builder removes.
    bad=ConditionFact(key='electron_acceptor',value='O2',status='unknown',source_ref='src:unknown')
    for order in ('known_first','unknown_first'):
        facts=[known,bad] if order=='known_first' else [bad,known]
        ctx=build_path_context(condition_facts=facts,accumulated_requirements=[req],assessment_scope=['electron_acceptor'])
        payload=ctx.to_dict();restored=PathContext.from_dict(payload)
        validate_context_object(restored)
        artifacts=ArtifactStore(SCRATCH/'low_runs',order)
        ref=persist_context(artifacts,ctx);persisted=load_context(artifacts,ref)
        fit=persisted.current_step_assessment().to_dict()
        rows.append({'order':order,'entry':'typed-direct -> build_path_context -> to_dict/from_dict -> persist_context/load_context',
          'payload':payload,'restored_payload':persisted.to_dict(),'assessment':fit,'validated':True,
          'source_scope':'self-consistent fixture originally created through deliberately unchecked typed fact; not an ordinary checked-plan output'})
    save('typed_restore.json',rows)
    assert rows[0]['assessment']['environment_fit']=='compatible'
    assert rows[1]['assessment']['environment_fit']=='unknown'
    normal=build_path_context(condition_facts=[build_condition_fact(key='electron_acceptor',value='O2',status='unknown')],accumulated_requirements=[req],assessment_scope=['electron_acceptor'])
    payload=normal.to_dict();payload['condition_facts'][0]['value']='O2'
    direct=cap(PathContext.from_dict,payload)
    artifacts=ArtifactStore(SCRATCH/'low_runs','tamper');ref=persist_context(artifacts,normal)
    path=artifacts._path('ctx:'+ref,CONTEXT_ARTIFACT_NAME);envelope=json.loads(path.read_text())
    envelope['payload']=payload;envelope['payload_hash']=content_hash(payload)
    path.write_text(json.dumps(envelope,indent=2)+'\n')
    loaded=cap(load_context,artifacts,ref)
    save('old_identity_resealed_tamper.json',{'normal':normal.to_dict(),'tampered':payload,'direct':direct,'production_load':loaded,
      'artifact_after':json.loads(path.read_text())})
    assert direct['ok'] is False and direct['detail']['kind']=='context_content_identity_mismatch'
    assert loaded['ok'] is False and loaded['detail']['kind']=='context_content_identity_mismatch'
    return 2

def public_restore_scope():
    runs=SCRATCH/'public_runs'; results=[]
    for mode in ('control','old_id_resealed','new_id_resealed'):
        run_id='mimo23-'+mode
        plan={'condition_facts':[
          {'key':'electron_acceptor','value':'O2','status':'unknown','source_ref':'src:synthetic-unknown'},
          {'key':'electron_acceptor','value':'O2','status':'known_present','source_ref':'src:synthetic-present'}],
          'pools':{'CCO':[spec('A','CC=O','donor-A',coproducts=['[H][H]'],requirements=[
             {'key':'electron_acceptor','level':'essential','value':'O2','source_refs':['src:synthetic-necessity']}])]},
          'schedule_budget':{'max_select':1}}
        started=cap(start_run,config=resolve_config(),runs_root=runs,run_id=run_id,smiles='CCO',max_depth=2,
          max_expansions=5,max_frontier_width=2,finder=object(),scripted=True,
          profile=PROFILE_POLLUTANT_PATHWAY_V1,ppv1_plan=plan,crash_after='after_claim')
        assert started['ok'] is False and started['type']=='SearchCrashInjection',started
        artifacts=ArtifactStore(runs,run_id);contexts=list(artifacts.base.glob('ctx:*/'+CONTEXT_ARTIFACT_NAME+'.json'))
        assert len(contexts)==1,contexts
        path=contexts[0];envelope=json.loads(path.read_text());before=copy.deepcopy(envelope)
        assert envelope['payload']['condition_facts'][0]['value'] is None
        if mode!='control':
            envelope['payload']['condition_facts'][0]['value']='O2'
            if mode=='new_id_resealed':
                rawctx=copy.deepcopy(envelope['payload']);fake=PathContext.__new__(PathContext)
                # Recompute only this synthetic payload through the official identity function.
                for field,value in rawctx.items():
                    if field!='assessed_scope':setattr(fake,field,value)
                fake.condition_facts=[ConditionFact(**f) for f in rawctx['condition_facts']]
                from pathway_v43.pollutant.path_context import Requirement,Dependency
                fake.accumulated_requirements=[Requirement(**r) for r in rawctx['accumulated_requirements']]
                fake.dependencies=[Dependency(**d) for d in rawctx['dependencies']]
                envelope['payload']['context_id']=_recompute_context_hash(fake)
            envelope['payload_hash']=content_hash(envelope['payload']);path.write_text(json.dumps(envelope,indent=2)+'\n')
        old_ref=before['payload']['context_id'];loaded=cap(load_context,artifacts,old_ref)
        if loaded['ok']:
            loaded['return']=loaded['return'].to_dict()
        pre=table_snapshot(runs/run_id/'pollutant.sqlite')
        resumed=cap(resume_run,config=resolve_config(),runs_root=runs,run_id=run_id)
        post=table_snapshot(runs/run_id/'pollutant.sqlite')
        obs={'mode':mode,'plan':plan,'start':started,'old_reference':old_ref,'before_envelope':before,
          'mutation_envelope':envelope,'production_load':loaded,'resume':resumed,
          'business_tables_before':pre,'business_tables_after':post,'mutated_artifact_after':json.loads(path.read_text())}
        save('public_restore/'+mode+'.json',obs)
        results.append({'mode':mode,'load_ok':loaded['ok'],'restored_context_id':loaded.get('return',{}).get('context_id') if loaded['ok'] else None,
          'load_error':loaded.get('detail'),'resume_ok':resumed['ok'],'resume_error':resumed.get('detail'),
          'events':len(post.get('reaction_events',[])),'event_rows':post.get('reaction_events',[]),
          'audit_rows':post.get('audit_records',[]),'summary':resumed.get('return') if resumed['ok'] else None})
    save('public_restore_summary.json',results)
    assert results[0]['load_ok'] and results[0]['resume_ok'],results[0]
    assert results[1]['load_ok'] is False
    assert results[1]['load_error']['kind']=='context_content_identity_mismatch'
    return len(results)

if __name__=='__main__':
    n=checked_scope();r=restore_scope();p=public_restore_scope()
    print(json.dumps({'checked_key_cases':n,'typed_restore_cases':r,'public_start_resume_cases':p,'observation_completed':True},ensure_ascii=False))
