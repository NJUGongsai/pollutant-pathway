#!/usr/bin/env python3
"""Pin current S3a observations; this is NOT a desired-contract pass test."""
import argparse,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);a=ap.parse_args();p=Path(a.root)
rows=[json.loads(l) for l in (p/'inheritance.stdout.jsonl').read_text().splitlines()]
assert len(rows)==27
bad=0
for r in rows:
    if r['case']=='first_submit_raw_guard':
        assert r['result']['error']=='Ppv1StateContractError' and not r['changed']
        continue
    recovery=r['recovery']; replay=r['public_writer_replay']
    assert 'returned' in recovery and not r['replay_changed']
    if r['case'].endswith('__clean'):
        assert replay['returned']['created'] is False
    else:
        bad+=1
        assert replay['error'] in ('Ppv1LedgerCorrupt','Ppv1EventConflict')
    entry=recovery['returned']['actions'][0]
    if r['case'].startswith('B4_before_bookkeeping__'):
        assert r['recovery_changed'] and entry['disposition']=='bookkeeping_completed_idempotent'
    else:
        assert not r['recovery_changed'] and entry['disposition']=='done_commit_verified'
assert bad==24
chem=[json.loads(l) for l in (p/'chemistry_v2.stdout.jsonl').read_text().splitlines()]
assert chem[-1]=={'assertions':'complete','cases':15}
by={r.get('case'):r for r in chem[:-1]}
assert by['raw_r']['rdkit']['parsed'] and by['canonical_r']['rdkit']['parsed']
assert by['raw_r']['restore']['detail']['kind']=='raw_structure_rejected'
assert by['canonical_r']['restore']['detail']['kind']=='state_structure_unparseable'
assert by['canonical_r']['restore']['detail']['reason']['kind']=='unregistered_cx_class'
assert by['canonical_bad']['restore']['detail']['reason']['kind']=='unparseable_smiles'
for k in ['raw_r','canonical_r','canonical_bad']:assert not by[k]['writer_changed']
f=by['failure_three_none_converter_scope']
assert all(f['diagnostic'][k] is None for k in ['reaction_center_match','strict_target_match','legacy_cn_match'])
assert f['diagnostic']['center_evidence']=={}
assert f['converter']['center_match'] is None and 'checker_scope' not in f['converter'] and 'proof_record' not in f['converter']
center=next(c for c in f['audit']['checks'] if c['name']=='transformation_center')
assert center['status']=='unknown' and center['reason_code'].startswith('center_checker_scope_unknown')
st=by['static_inventory']['result'];assert len(st['audit_raises'])==10 and not st['except_AuditContractError']
assert all(not r['enclosing_broad_handlers'] for r in st['audit_raises'])
assert st['runner_AST_except_refuse_function_equal'] and st['legacy_aggregate_changed']
assert st['limits_defaults_except_version_equal'] and st['limits_ranges_equal']
cx=[json.loads(l) for l in (p/'cx_controls.stdout.jsonl').read_text().splitlines()]
assert cx[-1]['retained_cases']==6 and cx[-1]['removed_cases']==3 and len(cx)==10
assert all(r['same_identity'] for r in cx[:-1])
print(json.dumps({'observation_assertions':'complete','authority_cases':26,'bad_authority_wrongly_recovered':24,
  'first_submit_raw_guard_cases':1,'chemistry_static_cases':15,'frozen_cx_controls':9,
  'claim':'Current gaps pinned; synthetic counts are not chemistry performance.'}))
