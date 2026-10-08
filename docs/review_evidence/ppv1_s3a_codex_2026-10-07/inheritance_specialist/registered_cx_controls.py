#!/usr/bin/env python3
"""Nine retained/removed controls taken literally from the frozen R8 matrix.
Not the whole R8 matrix. All execution is isolated and synthetic.
"""
import argparse,json
from pathlib import Path
from pathway_v43.pollutant.chemstate import build_chemical_state,ChemicalState,validate_state_object
from pathway_v43.pollutant.store import PollutantPathwayStore
from rdkit import rdBase

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    retained=['CCCCCC |Sg:n:1,2,3:3:ht:::|','C[C@H](Cl)[C@H](F)Cl |a:1, &1:3|',
      'C[C@H](Cl)[C@H](F)Cl |&1:1, &2:3|','CC |^1:0,1|','CC |^1:0, ^2:1|','CC |^1:0 ^2:1|']
    removed=['CCO |atomProp:0.note.hello world|','CCO |SgD:0:note:a,b hello world::::|','CCO |$foo bar;;$|']
    for group,structures in [('retained',retained),('removed',removed)]:
        for i,raw in enumerate(structures):
            state=build_chemical_state(raw,'raw_input');restored=ChemicalState.from_dict(state.to_dict());validate_state_object(restored)
            canonical=build_chemical_state(state.smiles_isomeric,'source_product')
            store=PollutantPathwayStore(out/f'{group}_{i}.sqlite');store.put_state(restored.to_dict())
            read=store.get_state(state.state_id);counts=store.counts();store.close()
            row={'case':f'{group}_{i}','raw':raw,'rdkit_version':rdBase.rdkitVersion,
              'state':state.to_dict(),'restored':restored.to_dict(),'canonical_reparse':canonical.to_dict(),
              'stored_read':read,'stored_counts':counts,'same_identity':state.state_id==restored.state_id==canonical.state_id}
            if group=='removed':row['bare_identity_equal']=state.state_id==build_chemical_state(raw.split(' |')[0],'raw_input').state_id
            assert row['same_identity'] and counts['states']==1 and counts['state_appearances']==1
            if group=='removed':assert row['bare_identity_equal']
            print(json.dumps(row,ensure_ascii=False),flush=True)
    print(json.dumps({'assertions':'complete','retained_cases':6,'removed_cases':3,'scientific_performance':'not_evaluated'}))
if __name__=='__main__':main()
