#!/usr/bin/env python3
from pathlib import Path
import sys,json,platform
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rdkit import Chem,rdBase
from pathway_v43.pollutant.chemstate import build_chemical_state,strict_identity_of,ChemicalState,ChemicalStateError,STRUCTURE_ORIGIN_RAW_INPUT
cases=[('plain','CO',None),('ABS','F[C@H](Cl)Br |a:1|','a:'),('AND','C[C@H](O)CC |&1:1|','&1:'),('OR','C[C@H](O)CC |o1:1|','o1:'),('radical','[CH3] |^1:0|','^1:')]
negative=[('and','C[C@H](O)CC |and:1|'),('or','C[C@H](O)CC |or:1|'),('rad','[CH3] |rad:0|')]
inputs={'positives':cases,'negatives':negative};(ROOT/'inputs/lexical.json').write_text(json.dumps(inputs,indent=2)+'\n')
obs=[]
for label,raw,token in cases:
 m=Chem.MolFromSmiles(raw);assert m is not None
 written=Chem.MolToCXSmiles(m)
 s=build_chemical_state(raw,STRUCTURE_ORIGIN_RAW_INPUT)
 restored=ChemicalState.from_dict(s.to_dict())
 written_state=build_chemical_state(written,STRUCTURE_ORIGIN_RAW_INPUT)
 ident=strict_identity_of(raw)
 assertions={'writer_token':token is None or token in written,'id_smiles':ident==s.smiles_isomeric,'id_roundtrip':strict_identity_of(s.smiles_isomeric)==ident,'state_dict_roundtrip':restored.to_dict()==s.to_dict(),'writer_identity':written_state.state_id==s.state_id}
 if label=='ABS':assertions['ABS_plain_normalized']=ident==strict_identity_of('F[C@H](Cl)Br')
 if label=='radical':assertions['radical_distinct_plain']=ident!=strict_identity_of('C')
 obs.append({'case':label,'input':raw,'rdkit_written':written,'identity':ident,'state':s.to_dict(),'assertions':assertions})
 assert all(assertions.values()),obs[-1]
for label,raw in negative:
 for entry,fn in [('factory',lambda:build_chemical_state(raw,STRUCTURE_ORIGIN_RAW_INPUT)),('strict',lambda:strict_identity_of(raw))]:
  try:fn()
  except ChemicalStateError as e:
   row={'case':label,'entry':entry,'input':raw,'exception_type':type(e).__name__,'detail':e.detail,'check':e.detail.get('kind')=='unregistered_cx_class'}
   obs.append(row);assert row['check'],row
  else:raise AssertionError((label,entry,'not rejected'))
result={'rdkit':rdBase.rdkitVersion,'python':platform.python_version(),'positive_count':5,'negative_entry_count':6,'observations':obs,'all_checks':True,'scientific_scope':'representation/identity contract only; no sample/stereochemistry identification certificate'}
(ROOT/'lexical_observations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False),flush=True)
