#!/usr/bin/env python3
"""Verify narrow baseline docstring correction without claiming a P1."""
import json,sys
from pathlib import Path
rows=[json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
assert len(rows)==3
meta,clean,tainted=rows
assert clean['case']=='clean'
assert tainted['case']=='product_formal_charge_99_only'
assert clean['input']['center_evidence']==tainted['input']['center_evidence']
assert clean['input']['hypothesis']==tainted['input']['hypothesis']
assert clean['input']['context']==tainted['input']['context']
for name,payload in clean['input']['states'].items():
    second=tainted['input']['states'][name]
    assert payload==({**second,'formal_charge':payload['formal_charge']} if name=='CC=O' else second)
assert tainted['input']['states']['CC=O']['formal_charge']==99
checks=lambda row:{c['name']:c for c in row['audit']['checks']}
a=checks(clean);b=checks(tainted)
for name in ['element_accounting','formal_charge_accounting','identity_fidelity','transformation_center']:
    assert a[name]['status']=='verified'
assert clean['admission']==['expand',['R6:all_verified_no_conflict']]
for name in ['element_accounting','identity_fidelity','transformation_center']:
    assert b[name]['status']=='verified'
assert b['formal_charge_accounting']['status']=='violated'
assert b['formal_charge_accounting']['detail']['charge_delta']=='-99'
assert b['transformation_center']['detail']['product_coverage']=='full'
assert tainted['admission'][0]=='retain_conditional'
assert tainted['admission'][1][0].startswith('R5d:')
print('Two unchanged-proof baseline public chains verified: clean expands R6; product charge=99 retains R5d with charge axis violated/-99. The test docstring verified-charge claim is false; no new P1 inferred.')
