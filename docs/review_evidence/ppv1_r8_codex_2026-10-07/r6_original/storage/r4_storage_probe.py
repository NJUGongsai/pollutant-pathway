import copy
import json
import sqlite3
import tempfile
from dataclasses import replace
from pathlib import Path

from pathway_v43.domain.models import content_hash
from pathway_v43.pollutant.chemstate import build_chemical_state, build_chemical_state_from_cn_only
from pathway_v43.pollutant.events import build_pathway_event, build_report_projection, build_expansion_plan, event_id_for
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis, recompute_hypothesis_id
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.legacy_reader import import_legacy_event, import_legacy_run, read_legacy_events
from pathway_v43.storage.pathway_store import PathwayStore

ROOT = Path(tempfile.mkdtemp(prefix='synthetic_r4_', dir=Path(__file__).parent))

def emit(name, **fields):
    print(json.dumps({'probe':name, **fields}, ensure_ascii=False, sort_keys=True, default=str))

def capture(name, fn):
    try:
        emit(name, **fn())
    except Exception as exc:
        emit(name, error=type(exc).__name__, detail=getattr(exc,'detail',{}), message=str(exc))

def state(smi, origin='source_product', refs=None):
    return build_chemical_state(smi, origin, refs)

def fixture(name):
    sub = state('CCO','raw_input',[{'record':'sub-A'}])
    prod = state('CC=O',refs=[{'record':'prod-A'}])
    hyp = build_hypothesis(parent_path_id='p1', substrate_state_ref=sub.state_id,
        participants=[Participant(state_ref=sub.state_id, side='reactant', role='primary_substrate', coefficient=None, coefficient_status='unknown'),
                      Participant(state_ref=prod.state_id, side='product', role='principal_product', coefficient=None, coefficient_status='unknown')],
        participant_list_status='partial',step_scope='net_reaction',origin_group_key=name)
    event = build_pathway_event(hyp,run_id=name,context_hash='ctx')
    args = {'report_projection':build_report_projection(hyp,max_reportable=1,ranked_state_refs=[prod.state_id]).to_dict(),
            'expansion_plan':build_expansion_plan(hyp,expanded=[prod.state_id],deferred=[],not_tracked=[]).to_dict(),
            'states':[sub.to_dict(),prod.to_dict()],'hypothesis_dict':hyp.to_dict()}
    return PollutantPathwayStore(ROOT/(name+'.sqlite')),sub,prod,hyp,event,args

def put_state_variant(kind):
    store = PollutantPathwayStore(ROOT/(kind+'.sqlite'))
    original = state('[13CH3][C@H](O)CC') if kind in ('isotope_status','stereo_status') else state('CCO')
    payload = original.to_dict()
    if kind == 'cn_identity':
        payload['cn_identity'] = 'CCN'
    elif kind == 'isotope_status':
        payload['isotope_information_status'] = 'not_applicable'
    elif kind == 'stereo_status':
        payload['stereo_information_status'] = 'not_applicable'
    elif kind == 'fidelity_unknown_enum':
        payload['representation_fidelity'] = {'formal_charge':'confirmed_by_magic'}
    elif kind == 'fidelity_missing_axes':
        payload['representation_fidelity'] = {}
    elif kind == 'source_raw_mismatch':
        payload['structure_smiles_raw'] = 'CCN'
    elif kind == 'source_raw_unparseable':
        payload['structure_smiles_raw'] = 'not-a-smiles'
    elif kind == 'executed_raw_mismatch':
        payload['structure_origin'] = 'executed_product'
        payload['structure_smiles_raw'] = 'CCN'
    elif kind == 'same_graph_alternate_raw':
        payload['structure_smiles_raw'] = 'OCC'
    elif kind == 'cn_only_forged_identity_and_facts':
        payload = build_chemical_state_from_cn_only('CCN').to_dict()
        payload['state_id'] = original.state_id
        payload['formal_charge'] = 99
        payload['original_structure_available'] = True
        payload['representation_fidelity'] = copy.deepcopy(original.representation_fidelity)
        payload['stereo_information_status'] = 'not_applicable'
        payload['isotope_information_status'] = 'not_applicable'
    store.put_state(payload)
    result = {'accepted':True,'original':original.to_dict(),'saved':store.get_state(payload['state_id']),'counts':store.counts()}
    store.close()
    return result

for kind in ('cn_identity','isotope_status','stereo_status','fidelity_unknown_enum','fidelity_missing_axes',
             'source_raw_mismatch','source_raw_unparseable','executed_raw_mismatch','same_graph_alternate_raw',
             'cn_only_forged_identity_and_facts'):
    capture('put_state_'+kind,lambda kind=kind:put_state_variant(kind))

def submit_raw_mismatch():
    store,sub,prod,hyp,event,args = fixture('submit_raw_mismatch')
    args['states'][1]['structure_smiles_raw'] = 'CCN'
    result = store.submit_event(event,**args)
    data = {'result':result,'saved':store.get_state(prod.state_id)}
    store.close()
    return data
capture('submit_raw_mismatch',submit_raw_mismatch)

def hypothesis_variant(kind):
    store,sub,prod,hyp,event,args = fixture(kind)
    mutated = copy.deepcopy(args['hypothesis_dict'])
    mutated['assumptions'] = ['a new scientific premise']
    rederived = recompute_hypothesis_id(mutated)
    if kind == 'put_hypothesis_changed_premise_old_id':
        store.put_hypothesis(mutated)
        result = {'accepted':True}
    elif kind == 'submit_hypothesis_changed_premise_old_id':
        args['hypothesis_dict'] = mutated
        result = store.submit_event(event,**args)
    elif kind == 'replay_hypothesis_changed_premise_old_id':
        store.submit_event(event,**args)
        store.conn.execute('UPDATE hypotheses SET payload=? WHERE hypothesis_id=?',(json.dumps(mutated),hyp.hypothesis_id))
        store.conn.commit()
        args['hypothesis_dict'] = None
        result = store.submit_event(event,**args)
    data = {'result':result,'supplied_id':hyp.hypothesis_id,'rederived_id':rederived,'stored':store.get_hypothesis(hyp.hypothesis_id)}
    store.close()
    return data
for kind in ('put_hypothesis_changed_premise_old_id','submit_hypothesis_changed_premise_old_id','replay_hypothesis_changed_premise_old_id'):
    capture(kind,lambda kind=kind:hypothesis_variant(kind))

def replay_missing_appearance_no_states():
    store,sub,prod,hyp,event,args = fixture('replay_missing_appearance_no_states')
    store.submit_event(event,**args)
    alternate = state('O=CC',refs=[{'record':'unrelated-prod-B'}])
    store.put_state(alternate.to_dict())
    row = store.conn.execute('SELECT appearance_hash FROM state_appearances WHERE state_id=? ORDER BY rowid LIMIT 1',(prod.state_id,)).fetchone()
    store.conn.execute('DELETE FROM state_appearances WHERE state_id=? AND appearance_hash=?',(prod.state_id,row['appearance_hash']))
    store.conn.commit()
    args['states'] = []
    args['hypothesis_dict'] = None
    result = store.submit_event(event,**args)
    data = {'result':result,'remaining_appearances':store.state_appearances(prod.state_id),'counts':store.counts()}
    store.close()
    return data
capture('replay_missing_appearance_no_states',replay_missing_appearance_no_states)

def replay_stored_state_uncalculated_fact(kind):
    store,sub,prod,hyp,event,args = fixture('replay_stored_state_'+kind)
    store.submit_event(event,**args)
    payload = json.loads(store.conn.execute('SELECT payload FROM states WHERE state_id=?',(prod.state_id,)).fetchone()['payload'])
    if kind == 'cn':
        payload['cn_identity']='CCN'
    elif kind == 'inner_state_id':
        payload['state_id']='cs_different'
    elif kind == 'blank_structure':
        payload['smiles_isomeric']=''
        payload['formal_charge']=99
    store.conn.execute('UPDATE states SET payload=? WHERE state_id=?',(json.dumps(payload),prod.state_id))
    store.conn.commit()
    args['states']=[]
    args['hypothesis_dict']=None
    result=store.submit_event(event,**args)
    data={'result':result,'stored':store.get_state(prod.state_id)}
    store.close()
    return data
for kind in ('cn','inner_state_id','blank_structure'):
    capture('replay_stored_state_'+kind,lambda kind=kind:replay_stored_state_uncalculated_fact(kind))

def make_legacy(name,steps):
    rd=ROOT/name
    rd.mkdir()
    store=PathwayStore(rd/'pathway.sqlite')
    root_cn=state('CCO').cn_identity
    root_pid=store.ensure_run(name,'CCO',root_cn)
    (rd/'run_identity.json').write_text(json.dumps({'schema_version':'v43-identity-1','inputs':{'root_smiles':'CCO','root_identity':root_cn}}))
    pid,cn=root_pid,root_cn
    created=[]
    for i,smis in enumerate(steps):
        products=[{'position':j,'product_smiles':smi,'product_smiles_full':smi,'product_identity':state(smi).cn_identity} for j,smi in enumerate(smis)]
        evidence={'evidence_id':name+'-e'+str(i),'source_id':name+'-e'+str(i),'kind':'recorded_reaction','condition_fit':'unknown','products':products}
        result=store.submit_event(run_id=name,parent_path_id=pid,substrate_identity=cn,evidence=evidence,products=products,expandable_path_ids=[],deferred_path_ids=[])
        created.append(result)
        pid,cn=result['path_ids'][0],products[0]['product_identity']
    store.close()
    return rd,root_pid,created

def legacy_same_cn_wrong_relation():
    left,right='C[C@H](O)CC','C[C@@H](O)CC'
    rd,root_pid,created=make_legacy('legacy_same_cn_wrong_relation',[[left],[right],['CC=O']])
    events=read_legacy_events(rd)
    second=next(e for e in events if e['parent_path_id']==created[0]['path_ids'][0])
    conn=sqlite3.connect(rd/'pathway.sqlite')
    conn.execute('UPDATE path_instances SET event_id=? WHERE path_id=?',(second['event_id'],second['parent_path_id']))
    conn.commit()
    row=conn.execute('SELECT parent_path_id,event_id,product_position FROM path_instances WHERE path_id=?',(second['parent_path_id'],)).fetchone()
    source_event_parent=conn.execute('SELECT parent_path_id FROM reaction_events WHERE event_id=?',(row[1],)).fetchone()[0]
    conn.close()
    before=(rd/'pathway.sqlite').read_bytes()
    imported=import_legacy_event(rd,second,new_run_id='new-wrong-same-cn')
    sub=next(s for s in imported['states'] if s['state_id']==imported['hypothesis'].substrate_state_ref)
    return {'accepted':True,'expected_raw':left,'actual_raw':sub['structure_smiles_raw'],
            'same_cn':state(left).cn_identity==state(right).cn_identity,'same_strict_id':state(left).state_id==state(right).state_id,
            'path_parent':row[0],'source_event_parent':source_event_parent,'imported':sub,'uncertainty_notes':imported['uncertainty_notes'],
            'old_bytes_unchanged':before==(rd/'pathway.sqlite').read_bytes()}
capture('legacy_same_cn_wrong_relation',legacy_same_cn_wrong_relation)

def legacy_event_vs_path_substrate_mismatch():
    rd,root_pid,created=make_legacy('legacy_event_vs_path_substrate_mismatch',[['CC=O']])
    conn=sqlite3.connect(rd/'pathway.sqlite')
    conn.execute('UPDATE reaction_events SET substrate_identity=? WHERE event_id=?',(state('CCN').cn_identity,created[0]['event_id']))
    conn.commit();conn.close()
    ev=read_legacy_events(rd)[0]
    before=(rd/'pathway.sqlite').read_bytes()
    imported=import_legacy_event(rd,ev,new_run_id='new-event-vs-path')
    sub=next(s for s in imported['states'] if s['state_id']==imported['hypothesis'].substrate_state_ref)
    return {'accepted':True,'event_declared_substrate_cn':ev['substrate_identity'],'imported':sub,'uncertainty_notes':imported['uncertainty_notes'],
            'old_bytes_unchanged':before==(rd/'pathway.sqlite').read_bytes()}
capture('legacy_event_vs_path_substrate_mismatch',legacy_event_vs_path_substrate_mismatch)

def legacy_product_declared_vs_raw_mismatch():
    rd,root_pid,created=make_legacy('legacy_product_declared_vs_raw_mismatch',[['CC=O']])
    conn=sqlite3.connect(rd/'pathway.sqlite')
    conn.execute('UPDATE event_products SET product_identity=? WHERE event_id=?',(state('CCN').cn_identity,created[0]['event_id']))
    conn.commit();conn.close()
    ev=read_legacy_events(rd)[0]
    before=(rd/'pathway.sqlite').read_bytes()
    imported=import_legacy_event(rd,ev,new_run_id='new-product-vs-raw')
    prod=next(s for s in imported['states'] if any(r.get('role')=='legacy_event_product' for r in s['source_refs']))
    return {'accepted':True,'declared_product_cn':ev['products'][0]['product_identity'],'imported_product':prod,
            'uncertainty_notes':imported['uncertainty_notes'],'old_bytes_unchanged':before==(rd/'pathway.sqlite').read_bytes()}
capture('legacy_product_declared_vs_raw_mismatch',legacy_product_declared_vs_raw_mismatch)
