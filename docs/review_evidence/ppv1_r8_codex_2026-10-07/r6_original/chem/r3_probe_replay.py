"""Independent synthetic chemistry review, read-only repo at af14fb2."""
import sys,json,traceback,random
sys.dont_write_bytecode=True
from rdkit import Chem,rdBase
from rdkit.Chem import rdCIPLabeler,RegistrationHash
from fractions import Fraction
from pathway_v43.pollutant.chemstate import build_chemical_state,strict_identity_of,normalized_structure_smiles
from pathway_v43.pollutant.substrate_profile import build_substrate_profile
from pathway_v43.pollutant.audit import (check_edit_against_donor,center_evidence_from_donor_diagnostic,audit_hypothesis,decide_admission,_atom_property_diffs,_joint_symmetric_image)
from pathway_v43.pollutant.hypothesis import Participant,build_hypothesis
from pathway_v43.pollutant.path_context import build_path_context,build_condition_fact,build_requirement
from pathway_v43.services.atom_tool import roundtrip,validate_edits,execute_edits
records=[]
def out(case,**data):
    item={'case':case,**data};records.append(item);print(json.dumps(item,ensure_ascii=False,sort_keys=True,default=str))
def state(s):return build_chemical_state(s,'raw_input')
def current(r):return {'smiles':r.smiles,'atom_id_map':dict(r.atom_id_map)}
def diag(r,result,edits,centers,target=None,ref='synthetic:alignment'):
    return check_edit_against_donor(current=current(r),donor={'center_atom_ids':['d'+str(i) for i in range(len(centers))]},alignment={'status':'resolved','donor_to_current':{'d'+str(i):a for i,a in enumerate(centers)},'ref':ref},expectation={'target_smiles':target if target is not None else result['product_smiles']},result=result,edits=edits)
def break_at(r,i,j):
    ids={v:k for k,v in r.atom_id_map.items()};es=[{'op':'break_bond','atom1':ids[i],'atom2':ids[j]}]
    return es,execute_edits(r,es)
def snapshot(m,mapped=False):
    c=Chem.Mol(m)
    for a in c.GetAtoms():
        for key in ['_CIPCode','_CIPRank']:
            if a.HasProp(key):a.ClearProp(key)
    legacy=Chem.Mol(c);Chem.AssignStereochemistry(legacy,cleanIt=True,force=True)
    modern=Chem.Mol(c);rdCIPLabeler.AssignCIPLabels(modern)
    def idx(a):return a.GetAtomMapNum()-1 if mapped else a.GetIdx()
    res=[]
    for a in c.GetAtoms():
        i=a.GetIdx();l=legacy.GetAtomWithIdx(i);n=modern.GetAtomWithIdx(i)
        ids=[idx(x) for x in a.GetNeighbors()]
        # Valid orientation witness only when neighbor IDs/H count are unchanged.
        sign={'CHI_TETRAHEDRAL_CW':1,'CHI_TETRAHEDRAL_CCW':-1}.get(str(a.GetChiralTag()),0)
        inversions=sum(ids[ii]>ids[jj] for ii in range(len(ids)) for jj in range(ii+1,len(ids)))
        res.append({'identity_idx':idx(a),'parsed_idx':i,'element':a.GetSymbol(),'tag':str(a.GetChiralTag()),'neighbors':ids,'orientation_by_sorted_neighbor_ids':sign*((-1)**inversions),'total_h':a.GetTotalNumHs(),'legacy_cip':l.GetProp('_CIPCode') if l.HasProp('_CIPCode') else '', 'modern_cip':n.GetProp('_CIPCode') if n.HasProp('_CIPCode') else '', 'radicals':a.GetNumRadicalElectrons()})
    return res

def aerobic_context():
    return build_path_context(requested_scope='condition_compatible',condition_facts=[build_condition_fact(key='oxygen_regime',value='aerobic',status='known_present')],accumulated_requirements=[build_requirement(key='oxygen_regime',level='essential',value='aerobic',source_refs=['synthetic:source'])],assessment_scope=['oxygen_regime'])
def hyp(reactants,products,sig='verified'):
    rr=[state(s) for s in reactants];pp=[state(s) for s in products]
    ps=[Participant(s.state_id,'reactant','primary_substrate' if i==0 else 'cosubstrate',Fraction(1),'known') for i,s in enumerate(rr)] + [Participant(s.state_id,'product','principal_product' if i==0 else 'coproduct',Fraction(1),'known') for i,s in enumerate(pp)]
    h=build_hypothesis(parent_path_id='synthetic:path',substrate_state_ref=rr[0].state_id,participants=ps,participant_list_status='declared_complete',step_scope='net_reaction',transformation_signature_status=sig,step_scope_evidence_refs=['synthetic:net_scope'])
    return h,{s.state_id:s for s in rr+pp}
def checks(a):return {c.name:{'status':c.status,'reason':c.reason_code,'detail':c.detail} for c in a.checks}
def audit_result(h,ss,**kwargs):
    a=audit_hypothesis(h,states=ss,context=aerobic_context(),**kwargs)
    return {'checks':checks(a),'admission':decide_admission(a)}

out('meta',head='af14fb2bb66e8afbbbbecd38722a9cacbd0699c3',rdkit=rdBase.rdkitVersion)
# Existing identity fixes and mixed ABS gap.
for left,right,expected_equal in [
 ('F[C@H](Cl)Br','F[C@H](Cl)Br |a:1|',True),
 ('C[C@H](O)CC |&1:1|','C[C@@H](O)CC |&1:1|',True),
 ('C[C@H](O)CC |o1:1|','C[C@@H](O)CC |o1:1|',True),
 ('F[C@H](Cl)[C@H](Br)I |&1:1,3|','F[C@@H](Cl)[C@@H](Br)I |&1:1,3|',True),
 ('F[C@H](Cl)[C@H](Br)I |&1:1,3|','F[C@@H](Cl)[C@H](Br)I |&1:1,3|',False),
 ('C[C@H](Cl)[C@H](F)Cl |a:1,&1:3|','C[C@H](Cl)[C@H](F)Cl |&1:3|',True),
 ('C[C@H](Cl)[C@H](F)Cl |a:1,o1:3|','C[C@H](Cl)[C@H](F)Cl |o1:3|',True),
 ('[CH2][C@H](C)O |^1:0,a:1|','[CH2][C@H](C)O |^1:0|',True)]:
    l=state(left);r=state(right)
    out('identity_pair',left=left,right=right,expected_equal=expected_equal,actual_equal=l.state_id==r.state_id,left_id=l.state_id,right_id=r.state_id,left_output=l.smiles_isomeric,right_output=r.smiles_isomeric,rdkit_canonical_left=Chem.MolToCXSmiles(Chem.CanonicalizeStereoGroups(Chem.MolFromSmiles(left))),rdkit_canonical_right=Chem.MolToCXSmiles(Chem.CanonicalizeStereoGroups(Chem.MolFromSmiles(right))))
for s in ['F[C@H](Cl)Br |&1:1|','F[C@H](Cl)Br |o1:1|','C[C@H](Cl)[C@H](F)Cl |a:1,&1:3|','[CH3]']:
    x=state(s);p=build_substrate_profile(x)
    out('identity_export_roundtrip_control',input=s,state_id=x.state_id,structure=p.structure_smiles,roundtrip_equal=state(p.structure_smiles).state_id==x.state_id)
# Real noop/inverse controls.
r=roundtrip('CCO',name='S')
for es in [[{'op':'change_bond_order','atom1':'S_C_2','atom2':'S_O_1','from_order':'single','to_order':'single'}],[{'op':'change_bond_order','atom1':'S_C_2','atom2':'S_O_1','from_order':'single','to_order':'double'},{'op':'change_bond_order','atom1':'S_C_2','atom2':'S_O_1','from_order':'double','to_order':'single'}]]:
    result=execute_edits(r,es);d=diag(r,result,es,['S_C_2','S_O_1'])
    out('zero_net_change_control',validation=validate_edits(r,es),execution=result,diagnostic=d.to_dict())
# R2 cyclic joint-image counterexample fixed.
r=roundtrip('C1CCCCC1',name='S');ids={v:k for k,v in r.atom_id_map.items()};es=[{'op':'form_bond','atom1':ids[0],'atom2':ids[3]}];result=execute_edits(r,es)
out('ring_joint_image_control',validation=validate_edits(r,es),execution=result,diagnostic=diag(r,result,es,[ids[0],ids[1]]).to_dict())
# Mimo remote CIP control, both declared endpoints actual execute.
r=roundtrip('C[C@H](Cl)[C@H](Cl)C',name='R');ids={v:k for k,v in r.atom_id_map.items()}
for i,j in [(0,1),(3,5)]:
    es,result=break_at(r,i,j);d=diag(r,result,es,[ids[i],ids[j]])
    bm=Chem.MolFromSmiles(r.smiles);am=Chem.MolFromSmiles(result['product_mapped_smiles']);changed,props=_atom_property_diffs(bm,am,r.atom_id_map,result['atom_id_map'])
    out('real_break_cip_control',actual_indices=[i,j],validation=validate_edits(r,es),execution=result,before_atoms=snapshot(bm),after_atoms=snapshot(am,True),property_changed=sorted(changed),property_records=props,diagnostic=d.to_dict())
# Strict mismatch on actual opposite-end cleavage, same result with supplied different donor center.
es,declared=break_at(r,0,1);es_actual,actual=break_at(r,3,5)
d=diag(r,actual,es_actual,[ids[0],ids[1]],target=declared['product_smiles'],ref='synthetic:meso:wrong_site')
bm=Chem.MolFromSmiles(r.smiles)
blind=bm.GetSubstructMatches(bm,uniquify=False,useChirality=False,maxMatches=1024)
aware=bm.GetSubstructMatches(bm,uniquify=False,useChirality=True,maxMatches=1024)
out('stereo_blind_joint_false_positive',substrate=r.smiles,declared_endpoint_product=declared['product_smiles'],actual_endpoint_product=actual['product_smiles'],product_identity_equal=state(declared['product_smiles']).state_id==state(actual['product_smiles']).state_id,validation=validate_edits(r,es_actual),execution=actual,blind_matches=blind,aware_matches=aware,diagnostic=d.to_dict(),center_evidence=center_evidence_from_donor_diagnostic(d))
# Direct strict=False nevertheless evidence verified and R6: unrelated balanced event is explicit.
h,ss=hyp(['CCO','O=O'],['CC(=O)O','O'])
out('strict_false_center_evidence_e2e',diagnostic=d.to_dict(),center_evidence=center_evidence_from_donor_diagnostic(d),hypothesis=h.to_dict(),audit=audit_result(h,ss,center_evidence=center_evidence_from_donor_diagnostic(d)))
# Registered genuine normal diagnostic not bound to reaction/hypothesis.
r_e=roundtrip('CCO',name='S');es_e=[{'op':'change_bond_order','atom1':'S_C_2','atom2':'S_O_1','from_order':'single','to_order':'double'}];exec_e=execute_edits(r_e,es_e);d_e=diag(r_e,exec_e,es_e,['S_C_2','S_O_1'])
out('genuine_different_reaction_center_evidence_reused',diagnostic_substrate='CCO',diagnostic_product=exec_e['product_smiles'],hypothesis_products=['CC(=O)O','O'],diagnostic=d_e.to_dict(),center_evidence=center_evidence_from_donor_diagnostic(d_e),audit=audit_result(h,ss,center_evidence=center_evidence_from_donor_diagnostic(d_e)))
# Correct new R2 admission controls.
a0=audit_hypothesis(h,states=ss);a1=audit_hypothesis(h,states=ss,audit_scope={'structure_parse_valence'});a2=audit_hypothesis(h,states=ss,context=aerobic_context())
out('admission_legacy_bug_controls',no_context={'checks':checks(a0),'admission':decide_admission(a0)},narrow_scope={'checks':checks(a1),'admission':decide_admission(a1)},self_report={'checks':checks(a2),'admission':decide_admission(a2)})
# Actual local retained configuration yet CIP legitimately changes due remote priority swap.
r_p=roundtrip('CC[C@H](O)C',name='P');ids_p={v:k for k,v in r_p.atom_id_map.items()}
es_p=[{'op':'add_atom','atom1':ids_p[4],'element':'F','new_atom_id':'P_F_1'}]
exec_p=execute_edits(r_p,es_p);d_p=diag(r_p,exec_p,es_p,[ids_p[4],'P_F_1'])
bm=Chem.MolFromSmiles(r_p.smiles);am=Chem.MolFromSmiles(exec_p['product_mapped_smiles']);changed,props=_atom_property_diffs(bm,am,r_p.atom_id_map,exec_p['atom_id_map'])
out('real_priority_swap_not_configuration_inversion',input=r_p.smiles,edits=es_p,validation=validate_edits(r_p,es_p),execution=exec_p,before_atoms=snapshot(bm),after_atoms=snapshot(am,True),property_changed=sorted(changed),property_records=props,diagnostic=d_p.to_dict())
# Report property facts at center separately; construct internally consistent result with inversion.
r_s=roundtrip('C[C@H](O)CCC',name='T');ids_s={v:k for k,v in r_s.atom_id_map.items()};es_s,exec_s=break_at(r_s,4,5)
m=Chem.MolFromSmiles(exec_s['product_mapped_smiles']);center_atom=next(a for a in m.GetAtoms() if a.GetAtomMapNum()==2);center_atom.InvertChirality();Chem.SanitizeMol(m)
modified=dict(exec_s);modified['product_mapped_smiles']=Chem.MolToSmiles(m);plain=Chem.Mol(m)
for a in plain.GetAtoms():a.SetAtomMapNum(0)
modified['product_smiles']=Chem.MolToSmiles(plain)
d_s=diag(r_s,modified,es_s,[ids_s[1],ids_s[4],ids_s[5]])
bm=Chem.MolFromSmiles(r_s.smiles);changed,props=_atom_property_diffs(bm,m,r_s.atom_id_map,modified['atom_id_map'])
out('center_property_inversion_no_public_delta',input=r_s.smiles,actual_operation='crafted_after_real_break_then_invert_existing_stereo',original_execution=exec_s,modified_execution=modified,property_changed=sorted(changed),property_records=props,diagnostic=d_s.to_dict(),center_evidence=center_evidence_from_donor_diagnostic(d_s))
# End result file manifest is outside repo.
# Correct, accurate CIP labels change after branch reprioritization despite stable local parity.
r_q=roundtrip('CCC[C@H](O)CC',name='Q');ids_q={v:k for k,v in r_q.atom_id_map.items()}
es_q=[{'op':'change_bond_order','atom1':ids_q[5],'atom2':ids_q[6],'from_order':'single','to_order':'double'}]
exec_q=execute_edits(r_q,es_q);d_q=diag(r_q,exec_q,es_q,[ids_q[5],ids_q[6]])
bm=Chem.MolFromSmiles(r_q.smiles);am=Chem.MolFromSmiles(exec_q['product_mapped_smiles']);changed,props=_atom_property_diffs(bm,am,r_q.atom_id_map,exec_q['atom_id_map'])
out('real_bond_priority_swap_accurate_cip_not_inversion',input=r_q.smiles,edits=es_q,validation=validate_edits(r_q,es_q),execution=exec_q,before_atoms=snapshot(bm),after_atoms=snapshot(am,True),property_changed=sorted(changed),property_records=props,diagnostic=d_q.to_dict())
# add_atom implicitly forms its anchor bond per real protocol; disjoint synthetic control.
r_a=roundtrip('C',name='A');ids_a={v:k for k,v in r_a.atom_id_map.items()}
es_a=[{'op':'add_atom','atom1':ids_a[0],'element':'O','new_atom_id':'A_O_1'}]
exec_a=execute_edits(r_a,es_a)
out('real_add_atom_anchor_bond_false_mismatch',input=r_a.smiles,edits=es_a,validation=validate_edits(r_a,es_a),execution=exec_a,diagnostic=diag(r_a,exec_a,es_a,[ids_a[0],'A_O_1']).to_dict())
# Strict false diagnostic used in same balanced actual reaction, no unrelated center binding confound.
r_b=roundtrip('C[C@H](Cl)[C@H](Cl)C',name='B');ids_b={v:k for k,v in r_b.atom_id_map.items()};es_decl,ex_decl=break_at(r_b,0,1);es_actual,ex_actual=break_at(r_b,3,5)
d_b=diag(r_b,ex_actual,es_actual,[ids_b[0],ids_b[1]],target=ex_decl['product_smiles'],ref='synthetic:bound_wrong_site')
h_b,ss_b=hyp([r_b.smiles,'[H]'],[ex_actual['product_smiles']])
out('strict_false_same_reaction_full_account_e2e',diagnostic=d_b.to_dict(),hypothesis=h_b.to_dict(),audit=audit_result(h_b,ss_b,center_evidence=center_evidence_from_donor_diagnostic(d_b)),scope_note='Synthetic elemental/charge closure only; no chemical feasibility claim')
# Stereo-aware automorphism control: genuinely C2 symmetric absolute substrate remains interchangeable.
for s in ['C[C@H](Cl)[C@H](Cl)C','C[C@H](Cl)[C@@H](Cl)C','C1CCCCC1']:
    m=Chem.MolFromSmiles(s)
    out('stereo_automorphism_controls',input=s,blind_matches=m.GetSubstructMatches(m,uniquify=False,useChirality=False,maxMatches=1024),aware_matches=m.GetSubstructMatches(m,uniquify=False,useChirality=True,maxMatches=1024),atoms=snapshot(m))
# CX nonchemical labels/coordinates are not strict molecular-graph facts.
for s in ['CO','CO |$carbon;oxygen$|','CO |(0,0,;1,0,)|','CO |(0,0,;2,0,)|','CO |atomProp:0.note.foo|']:
    x=state(s)
    out('cx_nonstructural_annotation_identity',input=s,state_id=x.state_id,structure=x.smiles_isomeric,ordinary_smiles=Chem.MolToSmiles(Chem.MolFromSmiles(s)))
# Existing S2 prerequisite and H balance controls without running full suite.
for reactants,products in [(['CCO'],['CC=O']),(['CCO'],['CC=O','[H][H]'])]:
    h_c,ss_c=hyp(reactants,products);a_c=audit_hypothesis(h_c,states=ss_c)
    out('full_hydrogen_controls',reactants=reactants,products=products,checks=checks(a_c),admission=decide_admission(a_c))
h_m,ss_m=hyp(['CCO'],['CC=O']);missing_id=next(p.state_ref for p in h_m.participants if p.side=='product');del ss_m[missing_id]
a_m=audit_hypothesis(h_m,states=ss_m)
out('missing_state_prerequisite_control',checks=checks(a_m),admission=decide_admission(a_m))
bad_exec=dict(exec_e);bad_exec['product_smiles']='CCO'
out('plain_mapped_disagreement_control',execution=bad_exec,diagnostic=diag(r_e,bad_exec,es_e,['S_C_2','S_O_1'],target='CCO').to_dict())
# Sequential declarations describe intermediate graph states, not independent final changes.
r_seq=roundtrip('CCO',name='U')
es_seq=[{'op':'change_bond_order','atom1':'U_C_2','atom2':'U_O_1','from_order':'single','to_order':'double'},{'op':'change_bond_order','atom1':'U_C_2','atom2':'U_O_1','from_order':'double','to_order':'single'},{'op':'change_bond_order','atom1':'U_C_2','atom2':'U_O_1','from_order':'single','to_order':'double'}]
exec_seq=execute_edits(r_seq,es_seq)
out('real_sequence_final_net_change_false_mismatch',input=r_seq.smiles,edits=es_seq,validation=validate_edits(r_seq,es_seq),execution=exec_seq,diagnostic=diag(r_seq,exec_seq,es_seq,['U_C_2','U_O_1'],target='CC=O').to_dict())
