import copy
import json
import sqlite3
import tempfile
from dataclasses import replace
from pathlib import Path

from pathway_v43.domain.models import content_hash
from pathway_v43.pollutant.chemstate import build_chemical_state, archive_recovered_fidelity
from pathway_v43.pollutant.events import build_pathway_event, build_report_projection, build_expansion_plan
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.legacy_reader import import_legacy_run, import_legacy_event, read_legacy_events
from pathway_v43.pollutant.provenance import build_support_groups
from pathway_v43.pollutant.pool_audit import record_pool_stage, build_pool_audit
from pathway_v43.storage.pathway_store import PathwayStore

ROOT = Path(tempfile.mkdtemp(prefix='r3_boundaries_', dir=Path(__file__).parent))

def out(name, **fields):
    print(json.dumps({'probe': name, **fields}, ensure_ascii=False, sort_keys=True, default=str))

def capture(name, fn):
    try:
        out(name, **fn())
    except Exception as exc:
        out(name, error=type(exc).__name__, detail=getattr(exc, 'detail', {}), message=str(exc))

def ps(smi, origin='source_product', refs=None, fidelity=None):
    return build_chemical_state(smi, origin, refs, fidelity=fidelity)

def fixture(name):
    sub, prod = ps('CCO', 'raw_input', [{'record':'sub-A'}]), ps('CC=O', refs=[{'record':'prod-A'}])
    hyp = build_hypothesis(parent_path_id='p1', substrate_state_ref=sub.state_id,
        participants=[Participant(state_ref=sub.state_id, side='reactant', role='primary_substrate', coefficient=None, coefficient_status='unknown'),
                      Participant(state_ref=prod.state_id, side='product', role='principal_product', coefficient=None, coefficient_status='unknown')],
        participant_list_status='partial', step_scope='net_reaction', origin_group_key=name)
    event = build_pathway_event(hyp, run_id=name, context_hash='ctx')
    args = {'report_projection': build_report_projection(hyp, max_reportable=1, ranked_state_refs=[prod.state_id]).to_dict(),
            'expansion_plan': build_expansion_plan(hyp, expanded=[prod.state_id], deferred=[], not_tracked=[]).to_dict(),
            'states': [sub.to_dict(), prod.to_dict()], 'hypothesis_dict': hyp.to_dict()}
    return PollutantPathwayStore(ROOT / (name + '.sqlite')), sub, prod, hyp, event, args

def put_forged(kind):
    store = PollutantPathwayStore(ROOT / ('put_forged_' + kind + '.sqlite'))
    ethanol = ps('CCO')
    payload = ethanol.to_dict()
    if kind == 'state_id':
        payload = ps('CCN').to_dict()
        payload['state_id'] = ethanol.state_id
    elif kind == 'formal_charge':
        payload['formal_charge'] = 99
    elif kind == 'raw_structure':
        payload['structure_smiles_raw'] = 'CCN'
    elif kind == 'isomeric_structure':
        payload['smiles_isomeric'] = 'not-a-smiles'
    store.put_state(payload)
    saved = store.get_state(payload['state_id'])
    result = {'accepted': True, 'saved_state': saved, 'expected_ethanol_id': ethanol.state_id,
              'actual_raw_structure_id': ps(payload['structure_smiles_raw']).state_id, 'counts':store.counts()}
    store.close()
    return result

for kind in ('state_id', 'formal_charge', 'raw_structure', 'isomeric_structure'):
    capture('put_forged_' + kind, lambda kind=kind: put_forged(kind))

def submit_forged_state():
    store, sub, prod, hyp, event, args = fixture('submit_forged_state')
    wrong = ps('CCN').to_dict()
    wrong['state_id'] = prod.state_id
    args['states'][1] = wrong
    result = store.submit_event(event, **args)
    data = {'result':result, 'event_product_ref':prod.state_id, 'actual_structure_id':ps('CCN').state_id,
            'saved_product':store.get_state(prod.state_id), 'counts':store.counts()}
    store.close()
    return data

capture('submit_forged_state', submit_forged_state)

def submit_zero_coefficient():
    store, sub, prod, hyp, event, args = fixture('submit_zero_coefficient')
    event.participants[1]['coefficient'] = '0'
    event.participants[1]['coefficient_status'] = 'known'
    args['hypothesis_dict']['participants'] = copy.deepcopy(event.participants)
    result = store.submit_event(event, **args)
    data = {'result':result, 'saved_participants':json.loads(store.get_event(event.event_id)['payload'])['participants']}
    store.close()
    return data

capture('submit_zero_coefficient', submit_zero_coefficient)

def replay_input_identity_mismatch():
    store, sub, prod, hyp, event, args = fixture('replay_input_identity_mismatch')
    store.submit_event(event, **args)
    changed = replace(event, run_id='different-run', context_hash='different-context')
    result = store.submit_event(changed, **args)
    data = {'result':result, 'submitted_run':changed.run_id, 'submitted_context':changed.context_hash,
            'stored_run':store.get_event(event.event_id)['run_id'], 'stored_context':store.get_event(event.event_id)['context_hash']}
    store.close()
    return data

capture('replay_input_identity_mismatch', replay_input_identity_mismatch)

def replay_variant(kind):
    store, sub, prod, hyp, event, args = fixture('replay_' + kind)
    store.submit_event(event, **args)
    if kind == 'one_appearance_missing':
        alternate = ps('O=CC', refs=[{'record':'prod-B-unrelated'}])
        store.put_state(alternate.to_dict())
        first_hash = store.conn.execute('SELECT appearance_hash FROM state_appearances WHERE state_id=? ORDER BY rowid LIMIT 1',(prod.state_id,)).fetchone()[0]
        store.conn.execute('DELETE FROM state_appearances WHERE state_id=? AND appearance_hash=?',(prod.state_id,first_hash))
    elif kind == 'appearance_payload_tampered':
        row = store.conn.execute('SELECT appearance_hash,payload FROM state_appearances WHERE state_id=?',(prod.state_id,)).fetchone()
        payload = json.loads(row['payload'])
        payload['structure_smiles_raw'] = 'CCN'
        store.conn.execute('UPDATE state_appearances SET payload=? WHERE state_id=? AND appearance_hash=?',(json.dumps(payload),prod.state_id,row['appearance_hash']))
    elif kind in ('event_payload_tampered', 'event_schema_tampered'):
        payload = json.loads(store.get_event(event.event_id)['payload'])
        if kind == 'event_payload_tampered':
            payload['participants'] = []
        else:
            payload['schema_version'] = 'future-event-999'
        store.conn.execute('UPDATE events SET payload=? WHERE event_id=?',(json.dumps(payload),event.event_id))
    elif kind == 'event_columns_tampered':
        store.conn.execute("UPDATE events SET run_id='wrong-run',parent_path_id='wrong-parent',context_hash='wrong-context' WHERE event_id=?",(event.event_id,))
    elif kind in ('hypothesis_id_tampered', 'hypothesis_schema_tampered'):
        payload = store.get_hypothesis(hyp.hypothesis_id)
        field = 'hypothesis_id' if kind == 'hypothesis_id_tampered' else 'schema_version'
        payload[field] = 'hyp_unrelated' if field == 'hypothesis_id' else 'future-hypothesis-999'
        store.conn.execute('UPDATE hypotheses SET payload=? WHERE hypothesis_id=?',(json.dumps(payload),hyp.hypothesis_id))
        args['hypothesis_dict'] = None
    elif kind in ('state_semantic_tampered_no_provided_states', 'state_schema_tampered_no_provided_states'):
        payload = json.loads(store.conn.execute('SELECT payload FROM states WHERE state_id=?',(prod.state_id,)).fetchone()[0])
        field = 'formal_charge' if kind.startswith('state_semantic') else 'schema_version'
        payload[field] = 99 if field == 'formal_charge' else 'future-chemstate-999'
        store.conn.execute('UPDATE states SET payload=? WHERE state_id=?',(json.dumps(payload),prod.state_id))
        args['states'] = []
    store.conn.commit()
    result = store.submit_event(event, **args)
    data = {'result':result, 'event_row':store.get_event(event.event_id), 'hypothesis':store.get_hypothesis(hyp.hypothesis_id),
            'product_state':store.get_state(prod.state_id), 'product_appearances':store.state_appearances(prod.state_id), 'counts':store.counts()}
    store.close()
    return data

for kind in ('one_appearance_missing', 'appearance_payload_tampered', 'event_payload_tampered', 'event_schema_tampered',
             'event_columns_tampered', 'hypothesis_id_tampered', 'hypothesis_schema_tampered',
             'state_semantic_tampered_no_provided_states', 'state_schema_tampered_no_provided_states'):
    capture('replay_' + kind, lambda kind=kind: replay_variant(kind))

def missing_expansion_entries():
    store, sub, prod, hyp, event, args = fixture('missing_expansion_entries')
    args['expansion_plan']['entries'] = []
    result = store.submit_event(event, **args)
    data = {'result':result, 'plan':store.expansion_plan(event.event_id), 'event_product_ref':prod.state_id}
    store.close()
    return data

capture('missing_expansion_entries', missing_expansion_entries)

def whole_missing_control(table):
    store, sub, prod, hyp, event, args = fixture('whole_missing_control_' + table)
    store.submit_event(event, **args)
    store.conn.execute('DELETE FROM ' + table)
    store.conn.commit()
    try:
        result = store.submit_event(event, **args)
        data = {'replay':result, 'detected':False}
    except Exception as exc:
        data = {'detected':True, 'error':type(exc).__name__, 'detail':getattr(exc, 'detail', {})}
    data['counts'] = store.counts()
    store.close()
    return data

for table in ('states','hypotheses','state_appearances','report_projections','expansion_plans'):
    capture('whole_missing_control_' + table, lambda table=table: whole_missing_control(table))

def make_legacy(name, steps):
    rd = ROOT / name
    rd.mkdir()
    store = PathwayStore(rd / 'pathway.sqlite')
    root_cn = ps('CCO').cn_identity
    root_pid = store.ensure_run(name, 'CCO', root_cn)
    (rd / 'run_identity.json').write_text(json.dumps({'schema_version':'v43-identity-1','inputs':{'root_smiles':'CCO','root_identity':root_cn}}))
    pid, cn = root_pid, root_cn
    created = []
    for i, smis in enumerate(steps):
        products = [{'position': j, 'product_smiles': smi, 'product_smiles_full': smi,
                    'product_identity':ps(smi).cn_identity} for j, smi in enumerate(smis)]
        evidence = {'evidence_id':name+'-e'+str(i), 'source_id':name+'-e'+str(i), 'kind':'recorded_reaction',
                    'condition_fit':'unknown', 'products':products}
        result = store.submit_event(run_id=name, parent_path_id=pid, substrate_identity=cn,
            evidence=evidence, products=products, expandable_path_ids=[], deferred_path_ids=[])
        created.append(result)
        pid, cn = result['path_ids'][0], products[0]['product_identity']
    store.close()
    return rd, root_pid, created

def legacy_variant(kind):
    rd, root_pid, created = make_legacy('legacy_' + kind, [['CC=O'], ['CC(=O)O']])
    events = read_legacy_events(rd)
    first = next(e for e in events if e['parent_path_id']==root_pid)
    second = next(e for e in events if e['parent_path_id']!=root_pid)
    chosen = first
    if kind == 'unknown_schema_direct_import':
        conn = sqlite3.connect(rd/'pathway.sqlite')
        conn.execute("UPDATE meta SET value='future-legacy-store-999' WHERE key='schema_version'")
        conn.commit(); conn.close()
    elif kind == 'wrong_archive_pointer':
        conn = sqlite3.connect(rd/'pathway.sqlite')
        conn.execute('UPDATE path_instances SET event_id=? WHERE path_id=?',(second['event_id'],second['parent_path_id']))
        conn.commit(); conn.close()
        chosen = second
    elif kind == 'root_structure_cn_mismatch':
        payload = json.loads((rd/'run_identity.json').read_text())
        payload['inputs']['root_smiles'] = 'CCN'
        (rd/'run_identity.json').write_text(json.dumps(payload))
    elif kind == 'unknown_identity_schema':
        payload = json.loads((rd/'run_identity.json').read_text())
        payload['schema_version'] = 'future-identity-999'
        (rd/'run_identity.json').write_text(json.dumps(payload))
    before = (rd/'pathway.sqlite').read_bytes()
    imported = import_legacy_event(rd, chosen, new_run_id='new-' + kind)
    sub_state = next(s for s in imported['states'] if s['state_id']==imported['hypothesis'].substrate_state_ref)
    data = {'accepted':True, 'old_substrate_cn':chosen['substrate_identity'], 'imported_substrate':sub_state,
            'uncertainty_notes':imported['uncertainty_notes'], 'old_bytes_unchanged':before==(rd/'pathway.sqlite').read_bytes()}
    if kind == 'unknown_schema_direct_import':
        target = PollutantPathwayStore(ROOT/'unknown_legacy_target.sqlite')
        try:
            import_legacy_run(rd,new_run_id='new-run',target_store=target)
            data['run_import_accepted'] = True
        except Exception as exc:
            data['run_import_error'] = type(exc).__name__
        target.close()
    return data

for kind in ('unknown_schema_direct_import', 'wrong_archive_pointer', 'root_structure_cn_mismatch', 'unknown_identity_schema'):
    capture('legacy_' + kind, lambda kind=kind: legacy_variant(kind))

def legacy_import_replay_repairs_missing():
    rd, root_pid, created = make_legacy('legacy_import_replay_repairs_missing',[['CC=O']])
    target = PollutantPathwayStore(ROOT/'legacy_import_replay_repairs_missing_new.sqlite')
    first = import_legacy_run(rd,new_run_id='legacy-replay',target_store=target)
    target.conn.execute('DELETE FROM states')
    target.conn.execute('DELETE FROM state_appearances')
    target.conn.execute('DELETE FROM hypotheses')
    target.conn.execute('DELETE FROM provenance_records')
    target.conn.commit()
    before = target.counts()
    replay = import_legacy_run(rd,new_run_id='legacy-replay',target_store=target)
    data = {'first':first,'before_replay':before,'replay':replay,'after_replay':target.counts()}
    target.close()
    return data

capture('legacy_import_replay_repairs_missing',legacy_import_replay_repairs_missing)

def support_axes():
    cards = [{'kind':'recorded_reaction','source_id':'A','evidence_id':'EA'},
             {'kind':'recorded_reaction','source_id':'B','evidence_id':'EB'}]
    partial = [g.to_dict() for g in build_support_groups(cards,study_map={'recorded_reaction:A':'doi:one'})]
    exact = [g.to_dict() for g in build_support_groups(cards,study_map={'recorded_reaction:A':'doi:one','recorded_reaction:B':'doi:one'})]
    unknown = [g.to_dict() for g in build_support_groups(cards)]
    return {'partial':partial,'exact':exact,'unknown':unknown}

capture('support_count_axes_fixed', support_axes)

def pool_skipped_equal_hash():
    pool = [{'evidence_id':'A'}]
    stages = [record_pool_stage(stage='retrieved_raw',input_items=[],output_items=pool),
              record_pool_stage(stage='structure_screened',input_items=pool,output_items=pool)]
    record = build_pool_audit(run_id='r',path_id='p',stages=stages,input_preview_policy='off')
    return {'accepted':True,'stages':record.to_dict()['stages']}

capture('pool_skipped_equal_hash_without_reason', pool_skipped_equal_hash)
