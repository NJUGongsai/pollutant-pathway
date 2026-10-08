#!/usr/bin/env python3
"""Synthetic single-version execution; no monkeypatch, no provider/network."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
from s3a_worker import make_fixture
from pathway_v43.pollutant.chemstate import build_chemical_state,strict_identity_of
from pathway_v43.pollutant.audit import audit_hypothesis,decide_admission
from rdkit import rdBase
out=Path(sys.argv[1]);out.mkdir(exist_ok=False);rows=[]
def capture(fn):
 try:
  v=fn();return {'returned':v.to_dict() if hasattr(v,'to_dict') else v}
 except Exception as e:return {'error':type(e).__name__,'message':str(e),'detail':getattr(e,'detail',{})}
def emit(x):rows.append(x);print(json.dumps(x,ensure_ascii=False),flush=True)
for entry,fn in [('factory',lambda s:build_chemical_state(s,'raw_input')),('strict',strict_identity_of)]:
 for label,value,kind in [('unregistered_r','CCO |r|','unregistered_cx_class'),('bad_smiles','INVALID_STRUCTURE','unparseable_smiles')]:
  got=capture(lambda:fn(value));emit({'case':entry+'_'+label,'input':value,'result':got});assert got['error']=='ChemicalStateError' and got['detail']['kind']==kind and 'reason' not in got['detail']
sub,prod,hyp,_,_=make_fixture('r1-run','parent','origin','context')
for label,value,kind in [('empty_isomeric','','structured_state_missing_isomeric'),('bad_isomeric','INVALID_STRUCTURE','state_structure_unparseable')]:
 bad=copy.deepcopy(prod);bad.smiles_isomeric=value
 got=capture(lambda:audit_hypothesis(hyp,states={sub.state_id:sub,prod.state_id:bad}));emit({'case':label,'hypothesis':hyp.to_dict(),'input_states':[sub.to_dict(),bad.to_dict()],'audit_result':got,'admission_not_called':True});assert got['error']=='ChemicalStateError' and got['detail']['kind']==kind and 'returned' not in got
clean=capture(lambda:audit_hypothesis(hyp,states={sub.state_id:sub,prod.state_id:prod}));emit({'case':'intact_audit_control','hypothesis':hyp.to_dict(),'input_states':[sub.to_dict(),prod.to_dict()],'audit_result':clean});assert 'returned' in clean
(out/'observations.json').write_text(json.dumps({'actual_rdkit':rdBase.rdkitVersion,'cases':rows,'assertions':'complete','scope':'Only literal bad object public audit chain; not proof of R1 universal unreachability or cross-version identity stability'},ensure_ascii=False,indent=2)+'\n');print(json.dumps({'cases':len(rows),'assertions':'complete'}))
