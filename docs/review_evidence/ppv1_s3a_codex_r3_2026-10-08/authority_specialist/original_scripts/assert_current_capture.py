#!/usr/bin/env python3
"""Read-only correct assertions on repaired cases; label remaining contract failures."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
legacy=[json.loads(x) for x in (P/'inheritance.stdout.jsonl').read_text().splitlines()]
assert len(legacy)==27
for r in legacy:
    if r['case']=='first_submit_raw_guard':
        assert r['result']['error']=='Ppv1StateContractError' and not r['changed']
    elif r['case'].endswith('__clean'):
        assert 'returned' in r['recovery'] and r['public_writer_replay']['returned']['created'] is False
        assert not r['replay_changed']
    else:
        assert r['recovery']['error']=='SearchIntegrityError'
        assert not r['recovery_changed'] and not r['replay_changed']
        assert r['public_writer_replay']['error'] in ('Ppv1LedgerCorrupt','Ppv1EventConflict')
seg=json.loads((P/'segmented_observations.json').read_text());assert len(seg)==120
accepted=[];late=[];fixed=[];controls=[]
for r in seg:
    c=r['case'];o=r['output'];res=o['result']
    if c.startswith('identity_'):
        assert o['direct']['error']=='SearchContractError' and o['write']['error']=='SearchContractError'
        assert not o['write_file_exists'] and o['before']==o['after_write'] and o['b3_before']==o['after']==o['after_second']
        assert res['returned']['actions'][0]['disposition']['kind']=='bundle_event_identity_not_frozen'
        assert o['artifact_preserved'];fixed.append(c)
    elif c.startswith('first_complete_') and '__' not in c:
        if c.endswith('_clean'):
            assert res['returned']['completed'] and o['second']['returned']['unchanged'] and o['after']==o['after_second'];controls.append(c)
        else:
            assert 'error' in res and o['before']==o['after']==o['after_second'];fixed.append(c)
    elif c.startswith('H07H08_'):
        assert o['before']==o['after'] and o['artifact_preserved']
        assert 'error' in res or res['returned']['actions'][0]['disposition']['error']=='SearchArtifactIntegrityError';fixed.append(c)
    elif c.endswith('__clean'):
        assert 'returned' in res;controls.append(c)
    elif '__' in c:
        if 'public_writer_original_input' in o:
            assert 'error' in o['public_writer_original_input'] and o['after']==o['writer_after']
        if 'returned' in res:accepted.append(c)
        elif o['before']!=o['after']:late.append(c)
        else:fixed.append(c)
assert len(accepted)==81 and late==['B3_recover__reservation_delete','B3_recover__attempt_delete']
sup=[]
for d in sorted((P/'supplementary_cases').iterdir()):
    r=json.loads((d/'input_output.json').read_text());sup.append(r)
    if d.name.startswith('normal_first_submit_'):assert 'error' in r['result'] and r['before']==r['after']
    else:
        assert r['result']['returned']['completed'] and r['independent_process']['returncode']==0
        assert r['independent_process']['decoded']['returned'] and r['after']==r['writer_after']
        assert not r['preverify_pause_hook'][0]['original_in_transaction_after']
        if d.name=='TOCTOU_clean':assert r['public_writer_original_input']['returned']['created'] is False
        else:assert r['public_writer_original_input']['error']=='Ppv1EventConflict' and r['public_writer_original_input']['detail']['kind']=='state_semantic_conflict'
assert len(sup)==5
out={'capture_readonly_assertions':'passed','legacy_authority_cases':26,'legacy_bad_authority_fixed':24,'raw_guard_cases':1,
     'segmented_cases':120,'segmented_fixed_or_legal_control_rows':len(fixed)+len(controls),'accepted_corrupt_rows':accepted,
     'late_rejected_but_event_written_rows':late,'supplementary_cases':5,
     'claim':'Capture completion and repaired cases verified; accepted corrupt rows are contract failures, not passes or vulnerability/performance counts.'}
(P/'contract_results.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['accepted_corrupt_rows','late_rejected_but_event_written_rows']},ensure_ascii=False))
