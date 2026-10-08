"""R6 synthetic public-API coverage probe. No assets/models/mechanism claims."""
import json
import runpy
from pathlib import Path
from pathway_v43.services.atom_tool import roundtrip, validate_edits, execute_edits
from pathway_v43.pollutant.audit import check_edit_against_donor, center_evidence_from_donor_diagnostic

base=runpy.run_path(str(Path(__file__).with_name('r5_admission_coverage_probe.py')))
emit,run=base['emit'],base['run']
r=roundtrip('C',name='S')
edits=[
 {'op':'add_atom','atom1':'S_C_1','element':'C','new_atom_id':'S_C_2'},
 {'op':'add_atom','atom1':'S_C_2','element':'C','new_atom_id':'S_C_3'},
 {'op':'add_atom','atom1':'S_C_3','element':'O','new_atom_id':'S_O_1'},
]
validation=validate_edits(r,edits)
result=execute_edits(r,edits)
assert validation['ok'] and result['ok'],(validation,result)
assert result['product_smiles']=='CCCO',result
diag=check_edit_against_donor(
 current={'smiles':r.smiles,'atom_id_map':r.atom_id_map},
 donor={'center_atom_ids':['d'+str(i) for i in range(len(result['atom_id_map']))]},
 alignment={'status':'resolved','donor_to_current':{'d'+str(i):aid for i,aid in enumerate(result['atom_id_map'])},'ref':'synthetic:r6:added-atoms'},
 expectation={'target_smiles':result['product_smiles']},result=result,edits=edits)
emit('real_atom_addition_diagnostic',validation=validation,result=result,diagnostic=diag.to_dict(),
 nature='real AtomTool adds atoms to methane; does not execute or map the co-reactant graph')
assert diag.reaction_center_match is True and diag.strict_target_match is True,diag.to_dict()
ev=center_evidence_from_donor_diagnostic(diag)
for donor in ('CC=O','C1CO1','C=CO'):
 run('unmapped_organic_completion_'+donor,[('C',1),(donor,1)],[('CCCO',1)],ev)
ev=base['evidence']('CCO','single','double')[0]
run('unmapped_radical_completion',[('CCO',1)],[('CC=O',1),('[H]',2)],ev)
