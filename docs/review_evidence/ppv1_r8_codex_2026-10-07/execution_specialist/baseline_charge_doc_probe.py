#!/usr/bin/env python3
"""Clarify one R8 test docstring, using unchanged R7 isolated public chain."""
import argparse,copy,hashlib,json,runpy,sys
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',type=Path,required=True)
args=parser.parse_args()
source=args.source.resolve()
sys.path.insert(0,str(source/'src'))
helper=source/'tests/test_ppv1_r8_chem.py'
mod=runpy.run_path(str(helper))
print(json.dumps({'case':'execution_metadata','baseline_head':'858dd94c7c6c8fc387940242403d67b6b36b5313','source_root':str(source),'helper_sha256':hashlib.sha256(helper.read_bytes()).hexdigest(),'audit_sha256':hashlib.sha256((source/'src/pathway_v43/pollutant/audit.py').read_bytes()).hexdigest(),'note':'R7 source remains isolated after detached worktree cleanup; helper is unchanged R8 synthetic test fixture.'},ensure_ascii=False))
for case in ['clean','product_formal_charge_99_only']:
    states,hyp,evidence=mod['_oxidation_base']()
    if case!='clean':
        key=mod['ACETALDEHYDE']
        states[key]=copy.copy(states[key])
        states[key].formal_charge=99
    audit=mod['_audit'](states,hyp,evidence)
    out={'case':case,'input':{'states':{name:s.to_dict() for name,s in states.items()},'hypothesis':hyp.to_dict(),'context':mod['_aerobic_context']().to_dict(),'center_evidence':evidence},'audit':audit.to_dict(),'admission':mod['_admission'](audit)}
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
