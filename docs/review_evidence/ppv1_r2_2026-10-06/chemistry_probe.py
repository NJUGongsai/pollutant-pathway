"""Read-only synthetic PPV1 R2 review at 0002f71; no assets, model, or experiment."""
import sys, json, random, traceback
sys.dont_write_bytecode = True
from fractions import Fraction
from rdkit import Chem
from rdkit.Chem.rdMolDescriptors import CalcMolFormula
from pathway_v43.pollutant.chemstate import build_chemical_state, strict_identity_of, build_chemical_state_from_cn_only
from pathway_v43.pollutant.substrate_profile import build_substrate_profile
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission, check_edit_against_donor, element_counts_full
from pathway_v43.pollutant.path_context import build_path_context, build_condition_fact, build_requirement
from pathway_v43.services.atom_tool import roundtrip, validate_edits, execute_edits

def out(case, data):
    print(json.dumps({'case':case, **data}, ensure_ascii=False, sort_keys=True, default=str))

def st(s, fidelity=None):
    return build_chemical_state(s,'raw_input', fidelity=fidelity)

def hyp_for(reactants, products, sig='verified', list_status='declared_complete'):
    ss = [st(s) for s in reactants + products]
    parts = [Participant(x.state_id, 'reactant' if i < len(reactants) else 'product', 'primary_substrate' if i==0 else ('cosubstrate' if i<len(reactants) else 'principal_product'), Fraction(1), 'known') for i,x in enumerate(ss)]
    h = build_hypothesis(parent_path_id='synthetic', substrate_state_ref=ss[0].state_id, participants=parts, participant_list_status=list_status, step_scope='net_reaction', transformation_signature_status=sig, step_scope_evidence_refs=['synthetic:declared'])
    return h, {x.state_id:x for x in ss}

def check_dict(a):
    return {c.name:{'status':c.status, 'reason':c.reason_code, 'detail':c.detail} for c in a.checks}

def diag(current, result, edits, center_ids, eq=None, expected=None):
    return check_edit_against_donor(current=current, donor={'center_atom_ids':['d'+str(i) for i in range(len(center_ids))]}, alignment={'status':'resolved','donor_to_current':{'d'+str(i):a for i,a in enumerate(center_ids)},'equivalence_classes':eq or [],'ref':'synthetic:alignment'}, expectation={'target_smiles':expected or result.get('product_smiles')}, result=result, edits=edits).to_dict()

def fake_result(smiles, ids):
    m=Chem.MolFromSmiles(smiles)
    for a in m.GetAtoms():
        a.SetAtomMapNum(a.GetIdx()+1)
    return {'ok':True,'product_smiles':smiles,'product_mapped_smiles':Chem.MolToSmiles(m), 'atom_id_map':ids}

# F01 corrections and explicitly tested counting scope.
for s in ['CCO','[CH3][CH2][OH]','C([H])([H])([H])[H]','[H][H]','O','[NH4+]','[2H]OC(C)C']:
    m=Chem.MolFromSmiles(s)
    out('f01_full_hydrogen_control', {'input':s,'counts':element_counts_full(m),'formula':CalcMolFormula(m)})
for reactants, products in [(['CCO'],['CC=O']),(['CCO'],['CC=O','[H][H]']),(['CCO','O=O'],['CC(=O)O','O'])]:
    h, ss=hyp_for(reactants,products)
    a=audit_hypothesis(h,states=ss)
    out('f01_balance_control',{'reactants':reactants,'products':products,'checks':check_dict(a),'admission':decide_admission(a)})

# New: strict identity SG exists in state_id, but structure output loses it.
for s in ['F[C@H](Cl)Br','F[C@H](Cl)Br |&1:1|','F[C@H](Cl)Br |o1:1|','F[C@H](Cl)Br |a:1|']:
    state=st(s)
    profile=build_substrate_profile(state)
    rebuilt=st(profile.structure_smiles)
    out('f05_enhanced_stereo_export_roundtrip',{'input':s,'state_id':state.state_id,'raw':state.structure_smiles_raw,'identity':strict_identity_of(s),'smiles_isomeric':state.smiles_isomeric,'profile_structure':profile.structure_smiles,'rebuilt_id':rebuilt.state_id,'roundtrip_same':rebuilt.state_id==state.state_id,'fidelity':profile.representation_fidelity})

# Canonicalization independence: only synthetic CXSMILES permutation, no input assets.
rng=random.Random(0)
for s in ['F[C@H](Cl)Br |&1:1|','C[C@H](O)[C@H](C)O |&1:1,3|','F[C@H](Cl)[C@H](Br)I |&1:1,3|','C[C@H](O)[C@H](C)O |&1:1,&2:3|']:
    m=Chem.MolFromSmiles(s)
    keys={}
    for j in range(60):
        order=list(range(m.GetNumAtoms()));rng.shuffle(order)
        p=Chem.RenumberAtoms(m,order)
        cx=Chem.MolToCXSmiles(p,canonical=False)
        keys.setdefault(strict_identity_of(cx),cx)
    out('f05_cx_permutation_identity',{'input':s,'n_distinct_keys':len(keys),'examples':keys})

# No context and self-reported transformation center: no diagnostic evidence needed.
h,ss=hyp_for(['CCO','O=O'],['CC(=O)O','O'])
a=audit_hypothesis(h,states=ss)
out('admission_no_context',{'checks':check_dict(a),'transformation_ref':h.transformation_ref,'admission':decide_admission(a)})
ctx=build_path_context(requested_scope='condition_compatible',condition_facts=[build_condition_fact(key='oxygen_regime',value='aerobic',status='known_present')],accumulated_requirements=[build_requirement(key='oxygen_regime',level='essential',value='aerobic',source_refs=['synthetic:source'])],assessment_scope=['oxygen_regime'])
a=audit_hypothesis(h,states=ss,context=ctx)
out('admission_self_report_verified_without_donor',{'checks':check_dict(a),'transformation_ref':h.transformation_ref,'admission':decide_admission(a)})
# Select just parse via audit_scope: missing mandatory checks do not prevent R6.
a=audit_hypothesis(h,states=ss,audit_scope={'structure_parse_valence'})
out('admission_narrow_audit_scope',{'checks':check_dict(a),'admission':decide_admission(a)})

# Missing state should return contract/unknown audit, rather than crash.
for ls in ['declared_complete','partial']:
    h,ss=hyp_for(['CCO'],['CC=O'],list_status=ls)
    removed=next(p.state_ref for p in h.participants if p.side=='product')
    del ss[removed]
    try:
        a=audit_hypothesis(h,states=ss)
        out('missing_state_default_audit',{'participant_list_status':ls,'checks':check_dict(a),'admission':decide_admission(a)})
    except Exception as e:
        out('missing_state_default_audit',{'participant_list_status':ls,'error_type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc()})
    a=audit_hypothesis(h,states=ss,audit_scope={'structure_parse_valence'})
    out('missing_state_parse_only_reason',{'participant_list_status':ls,'checks':check_dict(a),'admission':decide_admission(a)})

# Actual executor, nominal edits but zero net structure change.
r=roundtrip('CCO',name='S')
cur={'smiles':r.smiles,'atom_id_map':dict(r.atom_id_map)}
for label,edits in [('same_order',[{'op':'change_bond_order','atom1':'S_C_2','atom2':'S_O_1','from_order':'single','to_order':'single'}]),('inverse_order',[{'op':'change_bond_order','atom1':'S_C_2','atom2':'S_O_1','from_order':'single','to_order':'double'},{'op':'change_bond_order','atom1':'S_C_2','atom2':'S_O_1','from_order':'double','to_order':'single'}])]:
    validation=validate_edits(r,edits);execution=execute_edits(r,edits)
    out('f11_real_executor_zero_net_change',{'label':label,'validation':validation,'execution':execution,'diagnostic':diag(cur,execution,edits,['S_C_2','S_O_1'])})

# Normal real edit control.
edits=[{'op':'change_bond_order','atom1':'S_C_2','atom2':'S_O_1','from_order':'single','to_order':'double'}]
execution=execute_edits(r,edits)
out('f11_real_executor_edit_control',{'validation':validate_edits(r,edits),'execution':execution,'diagnostic':diag(cur,execution,edits,['S_C_2','S_O_1'],expected='CC=O')})
# Declaration mismatches returned executed graph; public interface trusts mismatch.
unchanged=execute_edits(r,[])
out('f11_declared_change_executed_unchanged',{'declaration':edits,'execution':unchanged,'diagnostic':diag(cur,unchanged,edits,['S_C_2','S_O_1'])})
false_product=dict(execution);false_product['product_smiles']='CCO'
out('f11_plain_product_mapped_product_disagree',{'execution':false_product,'diagnostic':diag(cur,false_product,edits,['S_C_2','S_O_1'],expected='CCO')})

# Nonbond changes ignored, using constructed but contract-shaped executor output.
for label,before,after,ids,centers in [('charge_and_h_only','CN','C[NH3+]',{'aC':0,'aN':1},['aN']),('stereo_only','F[C@H](Cl)Br','F[C@@H](Cl)Br',{'aF':0,'aC':1,'aCl':2,'aBr':3},['aC'])]:
    cur2={'smiles':before,'atom_id_map':ids}
    execution2=fake_result(after,ids)
    out('f11_nonbond_actual_change_invisible',{'label':label,'before':before,'after':after,'diagnostic':diag(cur2,execution2,[],centers,expected=after)})

# Orbit membership is insufficient for a simultaneous symmetry mapping of a center.
r2=roundtrip('C1CCCCC1',name='S')
ids=[k for k,v in sorted(r2.atom_id_map.items(),key=lambda kv:kv[1])]
edits2=[{'op':'form_bond','atom1':ids[0],'atom2':ids[3]}]
exec2=execute_edits(r2,edits2)
m=Chem.MolFromSmiles(r2.smiles)
automorphisms=m.GetSubstructMatches(m,uniquify=False,maxMatches=1000)
possible=any(set((p[0],p[1]))=={0,3} for p in automorphisms)
out('f11_independent_orbits_not_joint_symmetry',{'substrate':r2.smiles,'ids':ids,'donor_center_indices':[0,1],'executed_center_indices':[0,3],'joint_automorphism_exists':possible,'validation':validate_edits(r2,edits2),'execution':exec2,'diagnostic':diag({'smiles':r2.smiles,'atom_id_map':dict(r2.atom_id_map)},exec2,edits2,[ids[0],ids[1]],eq=[ids])})

# Enhanced stereo equivalence canonicalization: whole AND/OR group inversion.
from rdkit.Chem import RegistrationHash
for group in ['&1','o1']:
    pairs=[(f'C[C@H](O)CC |{group}:1|',f'C[C@@H](O)CC |{group}:1|'),(f'F[C@H](Cl)[C@H](Br)I |{group}:1,3|',f'F[C@@H](Cl)[C@@H](Br)I |{group}:1,3|')]
    for left,right in pairs:
        lmol=Chem.MolFromSmiles(left);rmol=Chem.MolFromSmiles(right)
        lc=Chem.MolToCXSmiles(Chem.CanonicalizeStereoGroups(lmol));rc=Chem.MolToCXSmiles(Chem.CanonicalizeStereoGroups(rmol))
        lh=RegistrationHash.GetMolHash(RegistrationHash.GetMolLayers(lmol));rh=RegistrationHash.GetMolHash(RegistrationHash.GetMolLayers(rmol))
        ids2={f'a{i}':i for i in range(lmol.GetNumAtoms())}
        out('f05_whole_enhanced_group_inversion_split',{'left':left,'right':right,'left_id':st(left).state_id,'right_id':st(right).state_id,'current_identity_equal':strict_identity_of(left)==strict_identity_of(right),'rdkit_canonical_left':lc,'rdkit_canonical_right':rc,'rdkit_canonical_equal':lc==rc,'rdkit_registration_hash_equal':lh==rh,'diagnostic':diag({'smiles':left,'atom_id_map':ids2},fake_result(right,ids2),[],['a1'],expected=left)})
# Distinct relative stereochemistry remains distinct under reference normalization.
left='F[C@H](Cl)[C@H](Br)I |&1:1,3|'
right='F[C@@H](Cl)[C@H](Br)I |&1:1,3|'
out('f05_relative_stereo_control',{'left':left,'right':right,'rdkit_canonical_equal':Chem.MolToCXSmiles(Chem.CanonicalizeStereoGroups(Chem.MolFromSmiles(left)))==Chem.MolToCXSmiles(Chem.CanonicalizeStereoGroups(Chem.MolFromSmiles(right))),'current_identity_equal':strict_identity_of(left)==strict_identity_of(right)})
