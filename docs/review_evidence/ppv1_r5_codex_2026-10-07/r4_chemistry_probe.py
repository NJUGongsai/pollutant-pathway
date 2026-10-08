"""R4 independent synthetic chemistry boundary probes. No repository writes."""
import sys, json, traceback
sys.dont_write_bytecode = True
from rdkit import Chem, rdBase
from pathway_v43.pollutant.chemstate import build_chemical_state, strict_identity_of, normalized_structure_smiles
from pathway_v43.pollutant.audit import check_edit_against_donor, _atom_property_diffs, _stereo_config_delta, _joint_symmetric_image
from pathway_v43.services.atom_tool import roundtrip, render, validate_edits, execute_edits

def out(case, **data):
    print(json.dumps(dict(case=case, **data), ensure_ascii=False, sort_keys=True, default=str))

def run(case, fn):
    try: out(case, **fn())
    except Exception as e: out(case, exception_type=type(e).__name__, exception=str(e), traceback=traceback.format_exc())

def diagnosis(r, result, edits, centers, target=None):
    return check_edit_against_donor(
        current={'smiles':r.smiles,'atom_id_map':dict(r.atom_id_map)},
        donor={'center_atom_ids':['d'+str(i) for i in range(len(centers))]},
        alignment={'status':'resolved','donor_to_current':{'d'+str(i):a for i,a in enumerate(centers)},'ref':'synthetic:r4:alignment'},
        expectation={'target_smiles':target or result['product_smiles']},
        result=result, edits=edits)

def consistent_result(m, mapping, n_edits=0):
    plain=Chem.Mol(m)
    for a in plain.GetAtoms(): a.SetAtomMapNum(0)
    return {'ok':True,'reasons':[],'product_smiles':Chem.MolToSmiles(plain),
        'product_mapped_smiles':Chem.MolToSmiles(m),'atom_id_map':dict(mapping),
        'n_edits':n_edits,'protocol_version':'v43-editproto-2'}

def mapped_copy(r):
    m=Chem.MolFromSmiles(r.smiles)
    for a in m.GetAtoms(): a.SetAtomMapNum(a.GetIdx()+1)
    return m

def property_result(r, result):
    changed, records=_atom_property_diffs(Chem.MolFromSmiles(r.smiles),Chem.MolFromSmiles(result['product_mapped_smiles']),r.atom_id_map,result['atom_id_map'])
    return {'changed':sorted(changed),'records':records}

out('meta', head='e80f4594ea44b5f2bf8c78360dc2ed2368dd94ae', rdkit=rdBase.rdkitVersion,
    scope='synthetic public API and real AtomTool controls; no assets/model/run experiments')

def chain_add():
    r=roundtrip('C',name='A')
    es=[{'op':'add_atom','atom1':'A_C_1','element':'O','new_atom_id':'A_O_1'},
        {'op':'add_atom','atom1':'A_O_1','element':'C','new_atom_id':'A_C_2'}]
    ex=execute_edits(r,es)
    return {'nature':'real executor','input':r.smiles,'edits':es,'validation':validate_edits(r,es),
        'execution':ex,'diagnostic':diagnosis(r,ex,es,list(ex['atom_id_map'])).to_dict()}
run('real_add_then_add_anchor_new_atom',chain_add)

def change_added():
    r=roundtrip('C',name='B')
    es=[{'op':'add_atom','atom1':'B_C_1','element':'C','new_atom_id':'B_C_2'},
        {'op':'change_bond_order','atom1':'B_C_1','atom2':'B_C_2','from_order':'single','to_order':'double'}]
    ex=execute_edits(r,es)
    return {'nature':'real executor','input':r.smiles,'edits':es,'validation':validate_edits(r,es),
        'execution':ex,'diagnostic':diagnosis(r,ex,es,list(ex['atom_id_map'])).to_dict()}
run('real_add_then_change_new_bond',change_added)

def wrong_from():
    r=roundtrip('CCO',name='F')
    actual=[{'op':'change_bond_order','atom1':'F_C_2','atom2':'F_O_1','from_order':'single','to_order':'double'}]
    bad=[dict(actual[0],from_order='double')]
    ex=execute_edits(r,actual)
    return {'nature':'genuine output re-used with interface-declared wrong precondition','input':r.smiles,
        'actual_edits':actual,'declared_edits':bad,'genuine_execution':ex,
        'declared_validation':validate_edits(r,bad),'declared_real_execution':execute_edits(r,bad),
        'diagnostic_with_wrong_declaration':diagnosis(r,ex,bad,['F_C_2','F_O_1']).to_dict()}
run('interface_wrong_from_order_not_replayed',wrong_from)

def ez_only():
    r=render('C/C=C/C',name='E')
    m=mapped_copy(r)
    b=next(b for b in m.GetBonds() if b.GetBondType()==Chem.BondType.DOUBLE)
    before=str(b.GetStereo());b.SetStereo(Chem.BondStereo.STEREOZ)
    Chem.SetDoubleBondNeighborDirections(m)
    result=consistent_result(m,r.atom_id_map)
    return {'nature':'interface synthetic E/Z change, zero operations','input':r.smiles,
        'before_bond_stereo':before,'after_bond_stereo':str(b.GetStereo()),'execution_shape':result,
        'identities_different':strict_identity_of(r.smiles)!=strict_identity_of(result['product_smiles']),
        'property_diff':property_result(r,result),'diagnostic':diagnosis(r,result,[],list(r.atom_id_map)).to_dict()}
run('interface_ez_only_missing_diff',ez_only)

def ez_outside():
    r=render('C/C=C/C.CCO',name='Z');ids={v:k for k,v in r.atom_id_map.items()}
    es=[{'op':'change_bond_order','atom1':ids[5],'atom2':ids[6],'from_order':'single','to_order':'double'}]
    ex=execute_edits(r,es)
    m=Chem.MolFromSmiles(ex['product_mapped_smiles'])
    b=next(b for b in m.GetBonds() if {b.GetBeginAtom().GetAtomMapNum(),b.GetEndAtom().GetAtomMapNum()}=={2,3})
    before=str(b.GetStereo());b.SetStereo(Chem.BondStereo.STEREOZ)
    Chem.SetDoubleBondNeighborDirections(m)
    modified=consistent_result(m,ex['atom_id_map'],len(es))
    return {'nature':'real remote bond edit, then interface-synthetic off-center E/Z change','input':r.smiles,
        'edits':es,'validation':validate_edits(r,es),'genuine_execution':ex,'modified_execution_shape':modified,
        'before_bond_stereo':before,'after_bond_stereo':str(b.GetStereo()),
        'product_identities_different':strict_identity_of(ex['product_smiles'])!=strict_identity_of(modified['product_smiles']),
        'property_diff':property_result(r,modified),'diagnostic':diagnosis(r,modified,es,[ids[5],ids[6]]).to_dict()}
run('interface_off_center_ez_false_center_true',ez_outside)

def ez_real_control():
    r=render('C/C=C/C',name='K');ids={v:k for k,v in r.atom_id_map.items()}
    es=[{'op':'change_bond_order','atom1':ids[1],'atom2':ids[2],'from_order':'double','to_order':'single'},
        {'op':'change_bond_order','atom1':ids[1],'atom2':ids[2],'from_order':'single','to_order':'double'}]
    ex=execute_edits(r,es)
    return {'nature':'real executor, control only','input':r.smiles,'edits':es,
        'validation':validate_edits(r,es),'execution':ex,'identity_equal':strict_identity_of(r.smiles)==strict_identity_of(ex['product_smiles']),
        'diagnostic':diagnosis(r,ex,es,[ids[1],ids[2]]).to_dict()}
run('real_ez_inverse_control',ez_real_control)

def non_tet(which):
    r=render('Cl[Pt@SP1](Br)(I)F',name='P')
    m=mapped_copy(r);a=next(a for a in m.GetAtoms() if a.GetSymbol()=='Pt')
    orig=a.GetIntProp('_chiralPermutation')
    if which=='different':a.SetIntProp('_chiralPermutation',2 if orig!=2 else 1)
    elif which=='unspecified':a.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
    result=consistent_result(m,r.atom_id_map)
    b=Chem.MolFromSmiles(r.smiles).GetAtomWithIdx(1)
    parsed=Chem.MolFromSmiles(result['product_mapped_smiles']);aa=next(x for x in parsed.GetAtoms() if x.GetSymbol()=='Pt')
    return {'nature':'interface synthetic non-tetrahedral result','variant':which,'input':r.smiles,'execution_shape':result,
        'before_tag':str(b.GetChiralTag()),'after_tag':str(aa.GetChiralTag()),'direct_config_delta':_stereo_config_delta(b,aa),
        'identities_different':strict_identity_of(r.smiles)!=strict_identity_of(result['product_smiles']),
        'property_diff':property_result(r,result),'diagnostic':diagnosis(r,result,[],list(r.atom_id_map)).to_dict()}
for variant in ['same','different','unspecified']:
    run('interface_non_tetra_'+variant,lambda variant=variant:non_tet(variant))

def ligand_replacement_unsupported_hidden():
    r=roundtrip('N[C@@H](C)C(=O)O',name='L');ids={v:k for k,v in r.atom_id_map.items()}
    es=[{'op':'break_bond','atom1':ids[0],'atom2':ids[1]},
        {'op':'add_atom','atom1':ids[1],'element':'F','new_atom_id':'L_F_1'}]
    ex=execute_edits(r,es)
    return {'nature':'real executor ligand replacement control; no claim of retention/inversion',
        'input':r.smiles,'edits':es,'validation':validate_edits(r,es),'execution':ex,
        'property_diff':property_result(r,ex),'diagnostic':diagnosis(r,ex,es,[ids[0],ids[1],'L_F_1']).to_dict()}
run('real_ligand_set_change_unsupported_disclosure',ligand_replacement_unsupported_hidden)

def data_sgroup():
    all_rows=[]
    for text in ['', 'review_note_foo','review_note_bar']:
        m=Chem.MolFromSmiles('CO')
        if text:
            sg=Chem.CreateMolDataSubstanceGroup(m,'review_note',text);sg.SetAtoms([0])
        s=Chem.MolToCXSmiles(m);st=build_chemical_state(s,'raw_input')
        all_rows.append({'input':s,'ordinary_smiles':Chem.MolToSmiles(m),'state_id':st.state_id,
            'public_structure':st.smiles_isomeric,'sgroup_types':[g.GetProp('TYPE') for g in Chem.GetMolSubstanceGroups(m)]})
    return {'nature':'RDKit DATA annotation only, not SRU/polymer/mixture','rows':all_rows}
run('data_sgroup_arbitrary_note_identity',data_sgroup)

def atom_values():
    rows=[]
    for s in ['CO','CO |$_AV:valueA;valueB$|','CO |$_AV:otherA;otherB$|']:
        m=Chem.MolFromSmiles(s);st=build_chemical_state(s,'raw_input')
        rows.append({'input':s,'canonical_cx':Chem.MolToCXSmiles(m),'ordinary_smiles':Chem.MolToSmiles(m),
            'props':[a.GetPropsAsDict(includePrivate=True,includeComputed=False) for a in m.GetAtoms()],
            'state_id':st.state_id,'public_structure':st.smiles_isomeric})
    return {'nature':'atomic value display metadata only','rows':rows}
run('atomic_value_annotation_identity_control',atom_values)

def stereo_scope(s):
    r=render(s,name='J');ids={v:k for k,v in r.atom_id_map.items()}
    es=[{'op':'break_bond','atom1':ids[3],'atom2':ids[5]}];ex=execute_edits(r,es)
    m=Chem.MolFromSmiles(s)
    return {'nature':'real executor; as-written partial/undefined stereo controls','input':s,
        'validation':validate_edits(r,es),'execution':ex,
        'blind_matches':m.GetSubstructMatches(m,uniquify=False,useChirality=False),
        'aware_matches':m.GetSubstructMatches(m,uniquify=False,useChirality=True),
        'diagnostic':diagnosis(r,ex,es,[ids[0],ids[1]]).to_dict()}
for s in ['C[C@H](Cl)[CH](Cl)C','C[CH](Cl)[CH](Cl)C','C[C@H](Cl)[C@@H](Cl)C']:
    run('joint_scope_control',lambda s=s:stereo_scope(s))

def non_tetra_joint():
    s='CC[P@TB1](CC)(Br)(I)F';r=render(s,name='Q');ids={v:k for k,v in r.atom_id_map.items()}
    es_left=[{'op':'change_bond_order','atom1':ids[0],'atom2':ids[1],'from_order':'single','to_order':'double'}]
    es_right=[{'op':'change_bond_order','atom1':ids[3],'atom2':ids[4],'from_order':'single','to_order':'double'}]
    ex_left=execute_edits(r,es_left);ex_right=execute_edits(r,es_right);m=Chem.MolFromSmiles(s)
    return {'nature':'real execute_edits using render(smiles), no roundtrip acceptance claim','input':s,
        'left_edits':es_left,'right_edits':es_right,'left_execution':ex_left,'right_execution':ex_right,
        'right_validation':validate_edits(r,es_right),
        'ordinary_atom_tags':[str(a.GetChiralTag()) for a in m.GetAtoms()],
        'product_identities_different':strict_identity_of(ex_left['product_smiles'])!=strict_identity_of(ex_right['product_smiles']),
        'chirality_aware_matches':m.GetSubstructMatches(m,uniquify=False,useChirality=True),
        'joint_result':_joint_symmetric_image(m,{0,1},{3,4}),
        'diagnostic':diagnosis(r,ex_right,es_right,[ids[0],ids[1]],target=ex_left['product_smiles']).to_dict()}
run('non_tetra_joint_declared_outside_scope_still_certified',non_tetra_joint)
