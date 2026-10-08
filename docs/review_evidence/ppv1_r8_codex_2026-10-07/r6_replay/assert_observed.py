"""Assert observed R6 outcomes, including gaps; not post-fix acceptance tests."""
import json, subprocess, sys
from pathlib import Path
P=Path(__file__).resolve().parent
def records(path):return [json.loads(x) for x in (P/path).read_text().splitlines()]
raw=records('admission_completion_probe.output.jsonl')
assert len(raw)==14
r={x['probe']:x for x in raw}
for key in ['genuine_bound_control','genuine_hydrogenation_control']:
    assert r[key]['center']['status']=='verified'
    assert r[key]['admission'][0]=='expand'
for key in ['old_two_sided_unchecked_control','one_sided_product_unchecked_isomer_half','one_sided_cosubstrate_unchecked_to_same_product']:
    assert r[key]['center']['status']=='unknown'
    assert r[key]['admission'][0]=='retain_conditional'
d=r['real_atom_addition_diagnostic']
assert d['validation']['ok'] and d['result']['ok']
assert d['result']['product_smiles']=='CCCO'
for smi in ['CC=O','C1CO1','C=CO']:
    x=r['unmapped_organic_completion_'+smi]
    assert x['center']['status']=='verified'
    assert x['center']['detail']['product_coverage']=='full'
    assert x['admission'][0]=='expand'
    checks={c['name']:c for c in x['audit']['checks']}
    assert checks['element_accounting']['status']=='verified'
    assert checks['formal_charge_accounting']['status']=='verified'
for lane,script in [('chem','cx_assert_observed.py'),('conditions','assert_observed.py'),('storage','storage_assert_observed.py')]:
    subprocess.run([sys.executable,'-B',str(P/lane/script)],cwd=P/lane,check=True)
for path,n in [('chem/r5_focused_replay.output.jsonl',6),('chem/r4_boundary_replay.output.jsonl',17),('chem/r3_probe_replay.output.jsonl',40),('storage/r5_storage_output.jsonl',9),('storage/r4_storage_output.jsonl',21),('storage/r3_storage_output.jsonl',29)]:
    assert len(records(path))==n
assert not any('exception_type' in x for x in records('chem/cx_boundary_probe.output.jsonl'))
if (P/'pytest_output.txt').exists():assert '451 passed' in (P/'pytest_output.txt').read_text()
print('R6 repaired controls and all five grouped residual observations confirmed.')
