#!/usr/bin/env python3
"""Read-only assertion of archived engineering results; no tests rerun."""
from pathlib import Path
import json,re,sys,xml.etree.ElementTree as ET

def main():
    root=Path(sys.argv[1]).resolve()
    results=json.loads((root/'execution_summary.json').read_text())
    assert results['ppv1_full']['totals']==dict(tests=594,errors=0,failures=0,skipped=0,passed=594)
    assert results['s3a_current']['totals']==dict(tests=58,errors=0,failures=0,skipped=0,passed=58)
    assert results['baseline_collection']['exit_code']==2
    assert results['baseline_collection']['totals']==dict(tests=2,errors=2,failures=0,skipped=0,passed=0)
    for c in results['baseline_collection']['cases']:
        assert c['state']=='error' and 'ModuleNotFoundError' in c['body']
        assert 'pathway_v43.pollutant.search' in c['body']
    assert results['baseline_profile']['exit_code']==1
    assert results['baseline_profile']['totals']==dict(tests=23,errors=0,failures=2,skipped=0,passed=21)
    failed=[c for c in results['baseline_profile']['cases'] if c['state']=='failure']
    assert {c['name'] for c in failed}=={'test_ppv1_identity_block_contract_versions','test_ppv1_identity_block_default_switches'}
    assert all('AssertionError' in c['body'] for c in failed)
    assert all(not re.search(r'KeyError|no such table|no such column',c['body']) for c in failed)
    assert results['g01']['exit_code']==0
    assert results['g01']['totals']==dict(tests=1204,errors=0,failures=0,skipped=8,passed=1196)
    g01=json.loads((root/'g01_safe_isolation/execution_result.json').read_text())
    assert any('1196 passed, 8 skipped, 17 deselected' in s for s in g01['summary_lines'])
    prep=json.loads((root/'g01_safe_isolation/preparation.json').read_text())
    assert prep['actual_input_head']=='9b78f4279cc6fa50b3b51c31a5c8e07abbeda207'
    assert len(prep['input_sha256'])==274 and prep['original_v3_assets_not_read'] is True
    assert len(g01['skip_lines'])==8
    slow=json.loads((root/'g01_slow_collection/result.json').read_text())
    assert slow['n_slow']==16 and slow['test_bodies_executed'] is False and slow['exit_code']==0
    equal=json.loads((root/'test_byte_equality.json').read_text())
    assert all(len(set(v.values()))==1 for v in equal.values())
    clean=json.loads((root/'worktree_cleanup.json').read_text())
    assert clean['exit_code']==0 and not clean['worktree_exists']
    assert clean['worktree_list'].count('worktree ')==1
    legacy=json.loads((root/'legacy_identity/summary.json').read_text())
    assert legacy['all_assertions_passed'] and legacy['legacy_changed_source_files']==['pathway_v43/workflow/runner.py']
    assert legacy['runner_AST_excluding_PPv1_refusal_function_unchanged']
    assert legacy['same_legacy_refusal_return_None']
    print(json.dumps(dict(artifact_assertions_passed=True,PPV1='594/0',S3a='58/0',baseline='2 collection files;58 unexecuted;2 behavior red/21 green',G01='1196/8/17',legacy_identity_confirmed=True,pytest_or_probe_bodies_rerun=False)))
    return 0
if __name__=='__main__':raise SystemExit(main())
