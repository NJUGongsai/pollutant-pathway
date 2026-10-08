"""R8 independent fixed-contract storage matrix. Only fresh synthetic databases.

Copy this script to a new tmp BEFORE running. argv[1] is an isolated root
containing src (including vendor) and pyproject.toml. SQL only constructs
the explicit single-row corruption fixtures; no real benchmark input.
"""
from pathlib import Path
import sys, json, tempfile
from dataclasses import asdict

SOURCE = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(SOURCE / 'src'))
from pathway_v43.pollutant.chemstate import build_chemical_state, ChemicalState
from pathway_v43.pollutant.events import build_pathway_event, build_report_projection, build_expansion_plan
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.profile import PPV1_STORE_SCHEMA_VERSION
ROOT = Path(tempfile.mkdtemp(prefix='r8_matrix_synthetic_', dir=Path(__file__).parent))

def dump(case, **out):
    print(json.dumps({'case': case, **out}, sort_keys=True, ensure_ascii=False))

def fixture(name):
    sub = build_chemical_state('CCO', 'raw_input', [{'record': 'sub-A'}])
    prod = build_chemical_state('CC=O', 'source_product', [{'record': 'prod-A'}])
    hyp = build_hypothesis(parent_path_id='synthetic-p', substrate_state_ref=sub.state_id,
        participants=[Participant(state_ref=sub.state_id, side='reactant', role='primary_substrate', coefficient=None, coefficient_status='unknown'),
                      Participant(state_ref=prod.state_id, side='product', role='principal_product', coefficient=None, coefficient_status='unknown')],
        participant_list_status='partial', step_scope='net_reaction', origin_group_key=name)
    event = build_pathway_event(hyp, run_id=name, context_hash='synthetic-ctx')
    args = {'report_projection': build_report_projection(hyp, max_reportable=1, ranked_state_refs=[prod.state_id]).to_dict(),
            'expansion_plan': build_expansion_plan(hyp, expanded=[prod.state_id], deferred=[], not_tracked=[]).to_dict(),
            'states': [sub.to_dict(), prod.to_dict()], 'hypothesis_dict': hyp.to_dict()}
    return PollutantPathwayStore(ROOT / (name + '.sqlite')), sub, prod, hyp, event, args

def observed(store, operation):
    before = store.counts()
    try:
        result = operation()
        outcome = {'returned': result}
    except Exception as exc:
        outcome = {'error': type(exc).__name__, 'kind': getattr(exc, 'detail', {}).get('kind'), 'detail': getattr(exc, 'detail', {}), 'message': str(exc)}
    after = store.counts()
    return {'outcome': outcome, 'before': before, 'after': after, 'zero_write': before == after}

def submit(store, event, args):
    return observed(store, lambda: store.submit_event(event, **args))

def mutation(store, sid, table, field, value):
    row = store.conn.execute(f'SELECT * FROM {table} WHERE state_id=?', (sid,)).fetchone()
    payload = json.loads(row['payload'])
    original = dict(payload)
    payload[field] = value
    store.conn.execute(f'UPDATE {table} SET payload=? WHERE state_id=?', (json.dumps(payload), sid))
    store.conn.commit()
    return {'table': table, 'state_id': sid, 'field': field,
            'before_payload': original, 'after_payload': payload,
            'appearance_hash_unchanged': row['appearance_hash'] if table == 'state_appearances' else None}

dump('metadata', schema=PPV1_STORE_SCHEMA_VERSION, python=sys.executable, source=str(SOURCE), synthetic_database_root=str(ROOT))

# Corrupt the same-hash SUBSTRATE row as well as the original product example:
# supply-none / sub-only / prod-only / all all consume the actual bad occurrence.
for supply in ('none', 'sub_only', 'prod_only', 'all'):
    name = 'corrupt_substrate_' + supply
    store, sub, prod, hyp, event, args = fixture(name)
    for state in args['states']: store.put_state(state)
    changed = mutation(store, sub.state_id, 'state_appearances', 'source_refs', [{'record': 'tampered-synthetic-only'}])
    states = [] if supply == 'none' else [sub.to_dict()] if supply == 'sub_only' else [prod.to_dict()] if supply == 'prod_only' else args['states']
    record = submit(store, event, dict(args, states=states))
    assert record['outcome'].get('error') == 'Ppv1LedgerCorrupt', record
    assert record['outcome'].get('kind') == 'appearance_hash_corrupt', record
    assert record['zero_write'] and store.get_event(event.event_id) is None, record
    dump(name, mutation=changed, input_event=asdict(event), input_states=states, first=record)
    store.close()

# Semantic conflict rejection with explicitly supplied product/all is retained.
for field, value in (('cn_identity', 'CCN'), ('schema_version', 'ppv1-chemstate-future'), ('state_id', 'cs-corrupt-inner')):
    for supply in ('prod_only', 'all'):
        name = 'supplied_semantic_' + field + '_' + supply
        store, sub, prod, hyp, event, args = fixture(name)
        for state in args['states']: store.put_state(state)
        changed = mutation(store, prod.state_id, 'states', field, value)
        states = [prod.to_dict()] if supply == 'prod_only' else args['states']
        record = submit(store, event, dict(args, states=states))
        assert record['outcome'].get('error') == 'Ppv1EventConflict', record
        assert record['outcome'].get('kind') == 'state_semantic_conflict', record
        assert record['zero_write'] and store.get_event(event.event_id) is None, record
        dump(name, mutation=changed, input_event=asdict(event), input_states=states, first=record)
        store.close()

# Legal partial/all prior persistence, supplied permutations, and no-input replay.
for prior in ('none', 'sub_only', 'prod_only', 'all'):
    name = 'legal_prior_' + prior
    store, sub, prod, hyp, event, args = fixture(name)
    persisted = [] if prior == 'none' else [sub.to_dict()] if prior == 'sub_only' else [prod.to_dict()] if prior == 'prod_only' else args['states']
    for state in persisted: store.put_state(state)
    supplied = args['states'] if prior == 'none' else [prod.to_dict()] if prior == 'sub_only' else [sub.to_dict()] if prior == 'prod_only' else []
    first = submit(store, event, dict(args, states=supplied))
    assert first['outcome']['returned']['created'] is True, first
    replay = submit(store, event, dict(args, states=[], hypothesis_dict=None))
    assert replay['outcome']['returned']['created'] is False and replay['zero_write'], replay
    supplied_replay = submit(store, event, dict(args, states=list(reversed(args['states'])), hypothesis_dict=None))
    assert supplied_replay['outcome']['returned']['created'] is False and supplied_replay['zero_write'], supplied_replay
    dump(name, input_event=asdict(event), input_states=supplied, prior_states=persisted, first=first, replay=replay, reversed_supplied_replay=supplied_replay)
    store.close()

# Registered boundary: put_state itself does not affirm/recompute an existing
# same-hash occurrence. Public submit MUST still reject before event authority.
for field, value in (('source_refs', [{'record': 'tampered-synthetic-only'}]),
                     ('structure_smiles_raw', 'CCN')):
    name = 'put_state_same_hash_boundary_' + field
    store, sub, prod, hyp, event, args = fixture(name)
    for state in args['states']: store.put_state(state)
    changed = mutation(store, prod.state_id, 'state_appearances', field, value)
    put = observed(store, lambda: store.put_state(prod.to_dict()))
    assert put['outcome'] == {'returned': None} and put['zero_write'], put
    after_payload = json.loads(store.conn.execute('SELECT payload FROM state_appearances WHERE state_id=?', (prod.state_id,)).fetchone()[0])
    assert after_payload == changed['after_payload'], after_payload
    readback = store.get_state(prod.state_id)
    # get_state is a semantic+appearances envelope, not a direct ChemicalState
    # payload: use its documented first-occurrence mirror without envelope key.
    restore_payload = {k: v for k, v in readback.items() if k != 'appearances'}
    restore = observed(store, lambda: ChemicalState.from_dict(restore_payload).to_dict())
    if field == 'structure_smiles_raw':
        assert restore['outcome'].get('error') == 'ChemicalStateError' and restore['outcome'].get('kind') == 'raw_identity_mismatch', restore
    else:
        assert 'returned' in restore['outcome'], restore
    first = submit(store, event, dict(args, states=[prod.to_dict()]))
    assert first['outcome'].get('error') == 'Ppv1LedgerCorrupt' and first['outcome'].get('kind') == 'appearance_hash_corrupt' and first['zero_write'], first
    assert store.get_event(event.event_id) is None
    dump(name, mutation=changed, input_event=asdict(event), input_states=[prod.to_dict()], put=put,
         actual_row_after_put=after_payload, readback=readback, restore_payload=restore_payload, restore=restore, first=first)
    store.close()

# Normal same-hash put remains idempotent, and subsequent public submit/replay
# is accepted. This is a legal positive control for the preceding boundary.
name = 'put_state_clean_idempotence_control'
store, sub, prod, hyp, event, args = fixture(name)
for state in args['states']: store.put_state(state)
put = observed(store, lambda: store.put_state(prod.to_dict()))
assert put['outcome'] == {'returned': None} and put['zero_write'], put
first = submit(store, event, dict(args, states=[prod.to_dict()]))
replay = submit(store, event, dict(args, states=[], hypothesis_dict=None))
assert first['outcome']['returned']['created'] is True
assert replay['outcome']['returned']['created'] is False and replay['zero_write']
dump(name, input_event=asdict(event), input_states=[prod.to_dict()], put=put, first=first, replay=replay)
store.close()
dump('matrix_assertions', cases_checked=17, status='pass', claims='event first-consumer closure only; put_state boundary remains disclosed')
