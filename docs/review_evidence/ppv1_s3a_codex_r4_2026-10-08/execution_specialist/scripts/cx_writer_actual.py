#!/usr/bin/env python3
from pathlib import Path
import json,ast,re
from rdkit import Chem,rdBase
from pathway_v43.pollutant.chemstate import build_chemical_state
OUT=Path(__file__).resolve().parents[1]
rows=[]
for label,raw in [('ABS','F[C@H](Cl)[C@H](Br)I |a:1,3|'),('AND','F[C@H](Cl)[C@H](Br)I |&1:1,3|'),('OR','F[C@H](Cl)[C@H](Br)I |o1:1,3|'),('radical','[CH3]')]:
 mol=Chem.MolFromSmiles(raw);written=Chem.MolToCXSmiles(mol)
 a=build_chemical_state(raw,'raw_input');b=build_chemical_state(written,'source_product')
 row={'case':label,'raw':raw,'RDKit':rdBase.rdkitVersion,'writer':written,'cx_block':written.split('|')[1] if '|' in written else None,'raw_state':a.to_dict(),'written_state':b.to_dict(),'identity_equal':a.state_id==b.state_id};assert row['identity_equal'];rows.append(row)
for head in ['and','or','rad']:
 raw='F[C@H](Cl)[C@H](Br)I |'+head+':1,3|'
 try:build_chemical_state(raw,'raw_input')
 except Exception as e:row={'case':'alias_'+head,'input':raw,'error':type(e).__name__,'detail':e.detail};assert e.detail['kind']=='unregistered_cx_class'
 else:raise AssertionError('Alias accepted: '+head)
 rows.append(row)
(OUT/'cx_writer_actual_results.json').write_text(json.dumps({'actual_rdkit':rdBase.rdkitVersion,'cases':rows,'assertions':'complete'},ensure_ascii=False,indent=2)+'\n');print(json.dumps({'cases':len(rows),'assertions':'complete','actual_rdkit':rdBase.rdkitVersion,'written':{r['case']:r.get('writer') for r in rows}},ensure_ascii=False))
