import copy
import json
import sqlite3
import tempfile
from pathlib import Path

from pathway_v43.pollutant.chemstate import build_chemical_state, build_chemical_state_from_cn_only
from pathway_v43.pollutant.events import build_pathway_event, build_report_projection, build_expansion_plan
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis, recompute_hypothesis_id
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.legacy_reader import import_legacy_event, read_legacy_events
from pathway_v43.storage.pathway_store import PathwayStore, product_path_id

ROOT=Path(tempfile.mkdtemp(prefix='synthetic_r5_',dir=Path(__file__).parent))

def emit(name,**fields):
    print(json.dumps({'probe':name,**fields},ensure_ascii=False,sort_keys=True,default=str))

def capture(name,fn):
    try: emit(name,**fn())
    except Exception as exc: emit(name,error=type(exc).__name__,detail=getattr(exc,'detail',{}),message=str(exc))

def state(smi,origin='source_product',refs=None):
    return build_chemical_state(smi,origin,refs)

def fixture(name):
    sub=state('CCO','raw_input',[{'record':'sub-A'}])
    prod=state('CC=O',refs=[{'record':'prod-A'}])
    hyp=build_hypothesis(parent_path_id='p1',substrate_state_ref=sub.state_id,
      participants=[Participant(state_ref=sub.state_id,side='reactant',role='primary_substrate',coefficient=None,coefficient_status='unknown'),
                    Participant(state_ref=prod.state_id,side='product',role='principal_product',coefficient=None,coefficient_status='unknown')],
      participant_list_status='partial',step_scope='net_reaction',origin_group_key=name)
    event=build_pathway_event(hyp,run_id=name,context_hash='ctx')
    args={'report_projection':build_report_projection(hyp,max_reportable=1,ranked_state_refs=[prod.state_id]).to_dict(),
          'expansion_plan':build_expansion_plan(hyp,expanded=[prod.state_id],deferred=[],not_tracked=[]).to_dict(),
          'states':[sub.to_dict(),prod.to_dict()],'hypothesis_dict':hyp.to_dict()}
    return PollutantPathwayStore(ROOT/(name+'.sqlite')),sub,prod,hyp,event,args

def replay(store,event,args):
    replay_args=dict(args,states=[],hypothesis_dict=None)
    before=store.counts()
    try:
        result=store.submit_event(event,**replay_args)
        return {'result':result,'counts_preserved':store.counts()==before}
    except Exception as exc:
        return {'error':type(exc).__name__,'detail':getattr(exc,'detail',{}),'counts_preserved':store.counts()==before}

def pre_stored_all():
    store,sub,prod,hyp,event,args=fixture('pre_stored_all')
    for payload in args['states']: store.put_state(payload)
    first=store.submit_event(event,**dict(args,states=[]))
    saved=json.loads(store.get_event(event.event_id)['payload'])
    result={'first':first,'manifest':saved['event_appearance_manifest'],'replay':replay(store,event,args)}
    store.close();return result
capture('pre_stored_all_first_success_replay_corrupt',pre_stored_all)

def pre_stored_partial(delete_actual=False):
    name='pre_stored_partial_'+str(delete_actual)
    store,sub,prod,hyp,event,args=fixture(name)
    store.put_state(prod.to_dict())
    actual_hash=store.conn.execute('SELECT appearance_hash FROM state_appearances WHERE state_id=?',(prod.state_id,)).fetchone()[0]
    first=store.submit_event(event,**dict(args,states=[sub.to_dict()]))
    payload=json.loads(store.get_event(event.event_id)['payload'])
    if delete_actual:
        store.put_state(state('O=CC',refs=[{'record':'unrelated-prod-B'}]).to_dict())
        store.conn.execute('DELETE FROM state_appearances WHERE state_id=? AND appearance_hash=?',(prod.state_id,actual_hash))
        store.conn.commit()
    result={'first':first,'manifest':payload['event_appearance_manifest'],'product_ref':prod.state_id,
            'actual_deleted':delete_actual,'product_appearances':store.state_appearances(prod.state_id),'replay':replay(store,event,args)}
    store.close();return result
capture('pre_stored_partial_normal_control',lambda:pre_stored_partial(False))
capture('pre_stored_partial_actual_source_deleted_replay_success',lambda:pre_stored_partial(True))

def supplied_all_control():
    store,sub,prod,hyp,event,args=fixture('supplied_all_control')
    first=store.submit_event(event,**args)
    saved=json.loads(store.get_event(event.event_id)['payload'])
    normal=replay(store,event,args)
    row=store.conn.execute('SELECT appearance_hash FROM state_appearances WHERE state_id=?',(prod.state_id,)).fetchone()
    store.put_state(state('O=CC',refs=[{'record':'unrelated-prod-B'}]).to_dict())
    store.conn.execute('DELETE FROM state_appearances WHERE state_id=? AND appearance_hash=?',(prod.state_id,row[0]))
    store.conn.commit()
    result={'first':first,'manifest':saved['event_appearance_manifest'],'normal_replay':normal,'damaged_replay':replay(store,event,args)}
    store.close();return result
capture('supplied_all_manifest_control',supplied_all_control)

def manifest_subset_tampered():
    store,sub,prod,hyp,event,args=fixture('manifest_subset_tampered')
    store.submit_event(event,**args)
    payload=json.loads(store.get_event(event.event_id)['payload'])
    original_manifest=payload['event_appearance_manifest']
    payload['event_appearance_manifest']=[e for e in original_manifest if e['state_id']!=prod.state_id]
    store.conn.execute('UPDATE events SET payload=? WHERE event_id=?',(json.dumps(payload),event.event_id))
    store.conn.commit()
    result={'original_manifest':original_manifest,'saved_manifest':payload['event_appearance_manifest'],
            'replay':replay(store,event,args)}
    store.close();return result
capture('manifest_nonempty_subset_tampered_replay_success',manifest_subset_tampered)

def existing_hypothesis_invalid_first_submit():
    store,sub,prod,hyp,event,args=fixture('existing_hypothesis_invalid_first_submit')
    store.put_hypothesis(hyp.to_dict())
    payload=hyp.to_dict()
    payload['assumptions']=['changed premise after initial put']
    rederived_id=recompute_hypothesis_id(payload)
    store.conn.execute('UPDATE hypotheses SET payload=? WHERE hypothesis_id=?',(json.dumps(payload),hyp.hypothesis_id))
    store.conn.commit()
    first=store.submit_event(event,**dict(args,hypothesis_dict=None))
    result={'first':first,'supplied_id':hyp.hypothesis_id,'rederived_id':rederived_id,'replay':replay(store,event,args)}
    store.close();return result
capture('existing_hypothesis_invalid_first_submit',existing_hypothesis_invalid_first_submit)

def cn_only_valid_control():
    store=PollutantPathwayStore(ROOT/'cn_only_valid_control.sqlite')
    cn=build_chemical_state_from_cn_only('CCO')
    store.put_state(cn.to_dict())
    saved=store.get_state(cn.state_id)
    result={'accepted':True,'saved':saved}
    store.close();return result
capture('cn_only_valid_control',cn_only_valid_control)

def legacy_sibling_relation(wrong_pointer):
    name='legacy_sibling_relation_'+str(wrong_pointer)
    rd=ROOT/name;rd.mkdir()
    old=PathwayStore(rd/'pathway.sqlite')
    root_cn=state('CCO').cn_identity
    root=old.ensure_run(name,'CCO',root_cn)
    (rd/'run_identity.json').write_text(json.dumps({'schema_version':'v43-identity-1','inputs':{'root_smiles':'CCO','root_identity':root_cn}}))
    left,right='C[C@H](O)CC','C[C@@H](O)CC'
    def submit(label,pid,cn,smi):
        products=[{'position':0,'product_smiles':smi,'product_smiles_full':smi,'product_identity':state(smi).cn_identity}]
        evidence={'evidence_id':name+'-'+label,'source_id':name+'-'+label,'kind':'recorded_reaction','condition_fit':'unknown','products':products}
        return old.submit_event(run_id=name,parent_path_id=pid,substrate_identity=cn,evidence=evidence,products=products,expandable_path_ids=[],deferred_path_ids=[])
    branch_a=submit('branch-a',root,root_cn,left)
    branch_b=submit('branch-b',root,root_cn,right)
    consumer=submit('consume-a',branch_a['path_ids'][0],state(left).cn_identity,'CC=O')
    old.close()
    if wrong_pointer:
        conn=sqlite3.connect(rd/'pathway.sqlite')
        conn.execute('UPDATE path_instances SET event_id=? WHERE path_id=?',(branch_b['event_id'],branch_a['path_ids'][0]))
        conn.commit();conn.close()
    ev=next(e for e in read_legacy_events(rd) if e['event_id']==consumer['event_id'])
    conn=sqlite3.connect(rd/'pathway.sqlite')
    path=conn.execute('SELECT run_id,parent_path_id,event_id,product_position FROM path_instances WHERE path_id=?',(ev['parent_path_id'],)).fetchone()
    source=conn.execute('SELECT run_id,parent_path_id FROM reaction_events WHERE event_id=?',(path[2],)).fetchone()
    children=[r[0] for r in conn.execute('SELECT path_id FROM path_instances WHERE event_id=? AND product_position=?',(path[2],path[3]))]
    conn.close()
    before=(rd/'pathway.sqlite').read_bytes()
    imported=import_legacy_event(rd,ev,new_run_id='new-'+name)
    substrate=next(s for s in imported['states'] if s['state_id']==imported['hypothesis'].substrate_state_ref)
    return {'wrong_pointer':wrong_pointer,'accepted':True,'expected_raw':left,'imported_substrate':substrate,
            'same_cn':state(left).cn_identity==state(right).cn_identity,'same_strict_id':state(left).state_id==state(right).state_id,
            'path_parent':path[1],'source_event_parent':source[1],'actual_path_id':ev['parent_path_id'],
            'expected_path_id_from_source':product_path_id(path[0],path[2],path[3]),'queried_children':children,
            'uncertainty_notes':imported['uncertainty_notes'],'old_bytes_unchanged':before==(rd/'pathway.sqlite').read_bytes()}
capture('legacy_correct_sibling_source_control',lambda:legacy_sibling_relation(False))
capture('legacy_same_parent_wrong_sibling_source_accepted',lambda:legacy_sibling_relation(True))
