#!/usr/bin/env python3
"""Check R8 independent execution logs and preparation boundary, not science."""
import hashlib,json,re,sys
from pathlib import Path

root=Path(sys.argv[1]).resolve()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
baseline=root/'ppv1_baseline'
metadata=json.loads((baseline/'execution_metadata.json').read_text())
assert metadata['actual_head']=='00e509a974b40a7c9779fcd35e53b16637a13d60'
assert metadata['actual_baseline_head']=='858dd94c7c6c8fc387940242403d67b6b36b5313'
assert metadata['baseline_summary']=={'failed':14,'passed':14,'field_missing_red':0,'behavior_red':14}
assert all(metadata['new_tests_unmodified_no_adapter'].values())
assert metadata['commands']['ppv1_full']['exit_code']==0
assert metadata['commands']['current_28']['exit_code']==0
assert metadata['commands']['baseline_28']['exit_code']==1
assert not metadata['worktree_still_exists']
assert metadata['commands']['worktree_remove']['exit_code']==0
assert metadata['no_bytecode_or_pytest_cache_in_source']
assert '536 passed' in (baseline/'ppv1_full.stdout.txt').read_text()
assert '28 passed' in (baseline/'current_28.stdout.txt').read_text()
assert '14 failed, 14 passed' in (baseline/'baseline_28.stdout.txt').read_text()
for lane in ['current','baseline']:
    assert metadata[lane+'_schema_versions']['PPV1_PROFILE_SCHEMA_VERSION']=='ppv1-profile-'+('8' if lane=='current' else '7')
    for name,digest in metadata[lane+'_input_hashes'].items():
        assert sha(baseline/lane/name)==digest,(lane,name)

prep=json.loads((root/'g01_safe/preparation.json').read_text())
run=json.loads((root/'g01_safe/execution_result.json').read_text())
assert prep['actual_input_head']==metadata['actual_head']
assert run['exit_code']==0
assert len(run['summary_lines'])==1
assert run['summary_lines'][0].startswith('1138 passed, 8 skipped, 17 deselected, 1 warning in ')
assert len(run['skip_lines'])==8
assert sum('v3 冻结基准不可用' in line for line in run['skip_lines'])==5
assert sum('v4 对照代码根不可用' in line for line in run['skip_lines'])==1
assert sum('v2 provenance 未生成' in line or 'v2 summary 未生成' in line for line in run['skip_lines'])==2
assert prep['explicit_deselected_case']=='tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden'
inputs=json.loads((root/'g01_safe/input_sha256.json').read_text())
assert len(inputs)==270
assert sum(k.startswith('repo/') for k in inputs)==210
assert sum(k.startswith('dependingv3/src/') for k in inputs)==42
assert sum(k.startswith('dependingv3/assets/') for k in inputs)==18
for name,digest in inputs.items():
    assert not any(part in Path(name).parts for part in ['evaluation','reports','data','gold','benchmark','dependingv4'])
    assert sha(root/'g01_safe'/name)==digest,name
assert all(not Path(p).exists() for p in prep['excluded_trees'])
for name in ['stdout','stderr']:
    assert sha(root/'g01_safe'/run[name])==run[name+'_sha256']
slow=(root/'slow_collection.stdout.txt').read_text()
selected=[line for line in slow.splitlines() if line.startswith('tests/') and '::' in line]
assert len(selected)==16,selected
assert '16/1163 tests collected (1147 deselected)' in slow
assert prep['explicit_deselected_case'] not in selected
(root/'slow_deselected_cases.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2)+'\n')
print('R8 execution evidence checked: PPV1 536/0; new 28/0; baseline behavior 14 red + 14 green; safe G01 1138/8/17; 270 inputs and 16 slow cases; no source cache/worktree remains.')
