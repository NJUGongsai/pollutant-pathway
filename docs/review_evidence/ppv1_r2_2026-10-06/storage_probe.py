import copy
import hashlib
import json
import sqlite3
import tempfile
from dataclasses import replace
from pathlib import Path

from pathway_v43.pollutant.chemstate import build_chemical_state, archive_recovered_fidelity
from pathway_v43.pollutant.events import build_pathway_event, build_report_projection, build_expansion_plan
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.legacy_reader import import_legacy_run, import_legacy_event, read_legacy_events
from pathway_v43.pollutant.pool_audit import record_pool_stage, build_pool_audit
from pathway_v43.pollutant.audit import ChemicalAudit, AuditCheck, legacy_validation_to_gate_decisions, decide_admission
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.storage.pathway_store import PathwayStore
from pathway_v43.storage.run_identity import check_resume_identity

ROOT = Path(tempfile.mkdtemp(prefix='synthetic_', dir=Path(__file__).parent))

def out(name, **fields):
    print(json.dumps({'probe': name, **fields}, ensure_ascii=False, sort_keys=True))

def ps(smi, origin='source_product', refs=None, fidelity=None):
    return build_chemical_state(smi, origin, refs, fidelity=fidelity)

def fixture(name):
    sub, prod = ps('CCO', 'raw_input'), ps('CC=O')
    hyp = build_hypothesis(parent_path_id='p1', substrate_state_ref=sub.state_id,
        participants=[Participant(state_ref=sub.state_id, side='reactant', role='primary_substrate', coefficient=None, coefficient_status='unknown'),
                      Participant(state_ref=prod.state_id, side='product', role='principal_product', coefficient=None, coefficient_status='unknown')],
        participant_list_status='partial', step_scope='net_reaction', origin_group_key=name)
    event = build_pathway_event(hyp, run_id=name, context_hash='ctx')
    args = {'report_projection': build_report_projection(hyp, max_reportable=1, ranked_state_refs=[prod.state_id]).to_dict(),
            'expansion_plan': build_expansion_plan(hyp, expanded=[prod.state_id], deferred=[], not_tracked=[]).to_dict(),
            'states': [sub.to_dict(), prod.to_dict()], 'hypothesis_dict': hyp.to_dict()}
    return PollutantPathwayStore(ROOT / (name + '.sqlite')), sub, prod, hyp, event, args

# F04: two valid appearances of the same strict structure differ only in source fidelity.
s1 = ps('CCO', 'raw_input', [{'source': 'root'}])
s2 = ps('OCC', 'source_product', [{'source': 'archive'}], archive_recovered_fidelity())
store = PollutantPathwayStore(ROOT / 'fidelity.sqlite')
store.put_state(s1.to_dict())
try:
    store.put_state(s2.to_dict())
    out('same_structure_source_fidelity', accepted=True)
except Exception as exc:
    out('same_structure_source_fidelity', accepted=False, same_id=s1.state_id == s2.state_id,
        error=type(exc).__name__, detail=getattr(exc, 'detail', {}), counts=store.counts())
store.close()

# F07: the separately stored state-ref list can omit a real product participant.
store, sub, prod, hyp, event, args = fixture('missing_product_refs')
event = replace(event, participant_state_refs=[sub.state_id])
args['states'] = [sub.to_dict()]
result = store.submit_event(event, **args)
out('event_refs_omit_real_product', result=result, product_exists=store.get_state(prod.state_id) is not None,
    participants=event.participants, participant_state_refs=event.participant_state_refs, counts=store.counts())
store.close()

# F07: fresh transactions accept event vs hypothesis semantics that disagree.
store, sub, prod, hyp, event, args = fixture('mismatch_hyp')
args['hypothesis_dict'] = copy.deepcopy(hyp.to_dict())
args['hypothesis_dict']['parent_path_id'] = 'different_parent'
args['hypothesis_dict']['substrate_state_ref'] = prod.state_id
args['hypothesis_dict']['participants'] = []
result = store.submit_event(event, **args)
out('event_hypothesis_mismatch', result=result, saved_hypothesis=store.get_hypothesis(hyp.hypothesis_id))
store.close()

# F07: passing mismatching hypothesis content is ignored if its ID already exists.
store, sub, prod, hyp, event, args = fixture('preexisting_mismatch_hyp')
store.put_hypothesis(hyp.to_dict(), context_hash='different_context')
args['hypothesis_dict'] = copy.deepcopy(hyp.to_dict())
args['hypothesis_dict']['participants'] = []
result = store.submit_event(event, **args)
out('existing_hypothesis_payload_ignored', result=result,
    hypothesis_context=store.conn.execute('SELECT context_hash FROM hypotheses').fetchone()[0], event_context=event.context_hash)
store.close()

# F07: projection references and mutually exclusive expansion statuses are not checked by actual commit API.
store, sub, prod, hyp, event, args = fixture('bad_projection_plan')
args['report_projection']['product_ranks'][0]['state_ref'] = 'cs_missing_nonproduct'
args['expansion_plan']['entries'].append({'state_ref': prod.state_id, 'status': 'deferred', 'reason': 'conflicting_status'})
args['expansion_plan']['entries'].append({'state_ref': 'cs_missing_nonproduct', 'status': 'expanded', 'reason': 'dangling'})
result = store.submit_event(event, **args)
out('commit_invalid_projection_and_expansion', result=result,
    saved_report=store.report_projection(event.event_id), saved_plan=store.expansion_plan(event.event_id))
store.close()

# F07: replay checks only attached projection/plan; deleting structural ledger data is not detected or repaired.
for table in ('states', 'hypotheses', 'state_appearances'):
    store, sub, prod, hyp, event, args = fixture('replay_missing_' + table)
    store.submit_event(event, **args)
    store.conn.execute('DELETE FROM ' + table)
    store.conn.commit()
    result = store.submit_event(event, **args)
    out('replay_missing_' + table, result=result, counts=store.counts())
    store.close()

# F08: top-level unknown database schema is correctly rejected without modifying bytes.
path = ROOT / 'future_store.sqlite'
conn = sqlite3.connect(path)
conn.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)')
conn.execute("INSERT INTO meta VALUES ('schema_version','future-store-999')")
conn.commit(); conn.close()
before = path.read_bytes()
try:
    PollutantPathwayStore(path)
except Exception as exc:
    out('future_store_schema', error=type(exc).__name__, bytes_unchanged=before == path.read_bytes())

# F08: serialized object version checks are not enforced by the writer API.
store, sub, prod, hyp, event, args = fixture('future_payload')
args['states'][0]['schema_version'] = 'future-chemstate-999'
args['hypothesis_dict']['schema_version'] = 'future-hypothesis-999'
event = replace(event, schema_version='future-event-999')
result = store.submit_event(event, **args)
out('future_object_schemas_written', result=result, saved_state_schema=store.get_state(sub.state_id)['schema_version'],
    saved_hypothesis_schema=store.get_hypothesis(hyp.hypothesis_id)['schema_version'], saved_event=store.get_event(event.event_id))
store.close()

# P2-5: skipping a named protocol stage allows broken chain with default from_previous=True and no reason.
a, b = [{'evidence_id': 'A'}], [{'evidence_id': 'B'}]
stages = [record_pool_stage(stage='retrieved_raw', input_items=[], output_items=a),
          record_pool_stage(stage='structure_screened', input_items=b, output_items=b)]
record = build_pool_audit(run_id='r', path_id='p', stages=stages, input_preview_policy='off')
out('skipped_pool_stage_breaks_hash_without_reason', accepted=True, stages=record.to_dict()['stages'])

# P2-2: true global gates do not consume a rejected per-product verdict.
mapped = legacy_validation_to_gate_decisions({'evidence_id':'old-evidence',
    'gates':{'direction_source':{'ok':True}, 'recorded_eligibility':{'ok':True}, 'atom_mapping':{'ok':True}},
    'verdicts':[{'position':0, 'accepted':False, 'reasons':['element_gate_rejected']} ]})
audit = ChemicalAudit(audit_id='synthetic_verified', scope='full_balance', input_hash='synthetic',
    checks=[AuditCheck(name=name, status='verified') for name in
            ('structure_parse_valence','element_accounting','formal_charge_accounting','condition_check')])
out('mapped_per_product_reject_ignored', mapped=mapped, admission=decide_admission(audit, gate_decisions=mapped))

# P2 profile configuration round-trip, distinct counting units, and independent zero budgets succeed.
block = build_profile_identity_block(search_limits={'max_search_depth': 0, 'max_total_search_actions': 0})
out('profile_limits_correct', round_trip=build_profile_identity_block(search_limits=block['search_limits'])['search_limits'] == block['search_limits'], limits=block['search_limits'])

# Legacy synthetic fixture via real public legacy API; it never touches real data.
def make_legacy(name, steps):
    rd = ROOT / name
    rd.mkdir()
    store = PathwayStore(rd / 'pathway.sqlite')
    root_cn = ps('CCO').cn_identity
    root_pid = store.ensure_run(name, 'CCO', root_cn)
    (rd / 'run_identity.json').write_text(json.dumps({'schema_version':'v43-identity-1','inputs':{'root_smiles':'CCO','root_identity':root_cn}}))
    pid, cn = root_pid, root_cn
    for i, smis in enumerate(steps):
        products = [{'position': j, 'product_smiles': smi, 'product_smiles_full': smi,
                    'product_identity':ps(smi).cn_identity} for j, smi in enumerate(smis)]
        evidence = {'evidence_id':name+'-e'+str(i), 'source_id':name+'-e'+str(i), 'kind':'recorded_reaction',
                    'condition_fit':'unknown', 'products':products}
        result = store.submit_event(run_id=name, parent_path_id=pid, substrate_identity=cn,
            evidence=evidence, products=products, expandable_path_ids=[], deferred_path_ids=[])
        pid, cn = result['path_ids'][0], products[0]['product_identity']
    store.close()
    return rd, root_pid, pid

# F04: normal root-returning cycle conflicts on fidelity (structure identity is reused correctly).
rd, root_pid, child = make_legacy('legacy_cycle', [['CC=O'], ['CCO']])
before = (rd/'pathway.sqlite').read_bytes()
store = PollutantPathwayStore(ROOT / 'legacy_cycle_new.sqlite')
try:
    out('legacy_cycle_import', result=import_legacy_run(rd, new_run_id='new-cycle', target_store=store))
except Exception as exc:
    out('legacy_cycle_import', error=type(exc).__name__, detail=getattr(exc,'detail',{}), counts=store.counts(),
        old_bytes_unchanged=before == (rd/'pathway.sqlite').read_bytes())
store.close()

# F04: repeated structure at two legacy positions silently discards raw spelling and first source position.
rd, _, _ = make_legacy('legacy_two_spellings', [['CC=O', 'O=CC']])
store = PollutantPathwayStore(ROOT / 'legacy_two_spellings_new.sqlite')
result = import_legacy_run(rd, new_run_id='new-dup', target_store=store)
out('legacy_same_structure_two_positions', result=result, product_appearances=store.state_appearances(ps('CC=O').state_id), counts=store.counts())
# provenance records exist, but hypothesis provenance_refs cannot resolve them by ID.
ev = store.list_events('new-dup')[0]
stored_hyp = store.get_hypothesis(ev['hypothesis_id'])
out('legacy_provenance_ref_resolution', provenance_refs=stored_hyp['provenance_refs'],
    resolved=[store.get_provenance(ref) for ref in stored_hyp['provenance_refs']],
    stored_provenance_ids=[row[0] for row in store.conn.execute('SELECT record_id FROM provenance_records')])
store.close()

# F09: missing child archive with intact parent relation but cleared event/position pointers is still misclassified root.
rd, _, _ = make_legacy('legacy_child_inconsistent', [['CC=O'], ['CC(=O)O']])
conn = sqlite3.connect(rd/'pathway.sqlite')
row = conn.execute('SELECT parent_path_id FROM reaction_events WHERE substrate_identity=?', (ps('CC=O').cn_identity,)).fetchone()
sub_path = row[0]
conn.execute('UPDATE path_instances SET event_id=NULL, product_position=NULL WHERE path_id=?', (sub_path,))
conn.commit(); conn.close()
before = (rd/'pathway.sqlite').read_bytes()
events = read_legacy_events(rd)
event2 = next(e for e in events if e['substrate_identity'] == ps('CC=O').cn_identity)
imported = import_legacy_event(rd, event2, new_run_id='new-inconsistent')
sub_state = next(s for s in imported['states'] if s['state_id']==imported['hypothesis'].substrate_state_ref)
out('child_missing_archive_pointers_as_root', old_substrate_cn=event2['substrate_identity'],
    imported_substrate=sub_state, uncertainty_notes=imported['uncertainty_notes'],
    old_bytes_unchanged=before == (rd/'pathway.sqlite').read_bytes())
