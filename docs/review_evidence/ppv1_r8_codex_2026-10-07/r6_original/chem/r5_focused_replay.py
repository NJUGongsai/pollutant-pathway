"""Independent R5 probes, synthetic public APIs; repository is read-only.

Run: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src \
     /Users/cc/miniconda3/envs/depending43/bin/python -B focused_probe.py
"""
import json
import sys
import traceback
sys.dont_write_bytecode = True
from rdkit import Chem, rdBase
from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.audit import check_edit_against_donor, _simulate_declared_edits, _bond_changes
from pathway_v43.services.atom_tool import render, execute_edits, validate_edits

HEAD = '293bc627f57b1f778aa433750f7f61d00b4a9d18'

def emit(case, **data):
    print(json.dumps(dict(case=case, **data), ensure_ascii=False, sort_keys=True, default=str))

def run(case, fn):
    try:
        emit(case, **fn())
    except Exception as e:
        emit(case, error_type=type(e).__name__, error=str(e), traceback=traceback.format_exc())

def state_case(s):
    try:
        st = build_chemical_state(s, 'raw_input')
        parsed = Chem.MolFromSmiles(s)
        return {'input':s, 'accepted':True, 'state':st.to_dict(), 'rdkit_reemitted_cx':Chem.MolToCXSmiles(parsed)}
    except Exception as e:
        return {'input':s, 'accepted':False, 'error_type':type(e).__name__, 'error':str(e), 'error_attributes':vars(e)}

emit('meta', head=HEAD, rdkit=rdBase.rdkitVersion, python=sys.version,
    nature='synthetic public API probes; no assets, models, or biological feasibility claims')
run('cx_raw_unregistered_r_and_Ln', lambda:{'rows':[state_case(s) for s in [
    'C[C@@H](N)C(=O)O', 'C[C@@H](N)C(=O)O |r|',
    'C1CCCCC1', 'C1CCCCC1 |Ln:1|',
    'C[C@H](F)Cl |w:1.0|', 'CO |atomProp:0.note.hello|',
    'CO |$_AV:one;two$|', 'CO'] ]})

def bond_snapshot(m):
    return [{'indices':[b.GetBeginAtomIdx(), b.GetEndAtomIdx()],
        'maps':[b.GetBeginAtom().GetAtomMapNum(),b.GetEndAtom().GetAtomMapNum()],
        'order':str(b.GetBondType()), 'stereo':str(b.GetStereo()),
        'stereo_atoms':list(b.GetStereoAtoms())} for b in m.GetBonds()]

def edit_case(s, op, pair, from_order=None, to_order=None):
    r=render(s, name='U')
    ids={i:a for a,i in r.atom_id_map.items()}
    edit={'op':op,'atom1':ids[pair[0]],'atom2':ids[pair[1]]}
    if from_order is not None: edit['from_order']=from_order
    if to_order is not None: edit['to_order']=to_order
    edits=[edit]
    validation=validate_edits(r,edits)
    ex=execute_edits(r,edits)
    assert validation['ok'] and ex['ok'], (validation,ex)
    diag=check_edit_against_donor(
        current={'smiles':r.smiles,'atom_id_map':dict(r.atom_id_map)},
        donor={'center_atom_ids':['d'+str(i) for i in range(len(ids))]},
        alignment={'status':'resolved','donor_to_current':{'d'+str(i):ids[i] for i in ids},
            'ref':'synthetic:r5:alignment'},
        expectation={'target_smiles':ex['product_smiles']}, result=ex, edits=edits)
    before=Chem.MolFromSmiles(r.smiles)
    actual=Chem.MolFromSmiles(ex['product_mapped_smiles'])
    simulated,failures=_simulate_declared_edits(before,edits,r.atom_id_map,ex['atom_id_map'])
    assert simulated is not None, failures
    serialized_sim=Chem.MolToSmiles(simulated)
    reparsed_sim=Chem.MolFromSmiles(serialized_sim)
    return {'nature':'REAL AtomTool render -> validate_edits -> execute_edits, then public donor diagnostic; private mirror inspection only explains the result',
        'input':s, 'rendered':r.smiles, 'atom_ids':r.atom_id_map, 'edits':edits,
        'validation':validation,'execution':ex,'diagnostic':diag.to_dict(),
        'mirror_failures':failures,'before_bonds':bond_snapshot(before),
        'actual_reparsed_bonds':bond_snapshot(actual),'mirror_in_memory_bonds':bond_snapshot(simulated),
        'mirror_serialized':serialized_sim,'mirror_reparsed_bonds':bond_snapshot(reparsed_sim),
        'actual_bond_diff':_bond_changes(before,actual,ex['atom_id_map']),
        'mirror_in_memory_bond_diff':_bond_changes(before,simulated,ex['atom_id_map']),
        'mirror_reparsed_bond_diff':_bond_changes(before,reparsed_sim,ex['atom_id_map'])}

run('real_adjacent_sigma_break_removes_EZ', lambda:edit_case('C/C=C/C','break_bond',(0,1)))
run('real_distal_tail_break_preserves_EZ_control', lambda:edit_case('C/C=C/CCC','break_bond',(4,5)))
run('real_alkene_order_change_control', lambda:edit_case('C/C=C/C','change_bond_order',(1,2),'double','single'))
run('real_alkene_bond_break_control', lambda:edit_case('C/C=C/C','break_bond',(1,2)))
