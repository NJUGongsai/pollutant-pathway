"""R6 independent synthetic public API probes. No repository mutations.
Run using depending43 python -B and repo/src in PYTHONPATH.
"""
import copy, json, sys, traceback
sys.dont_write_bytecode=True
from rdkit import Chem, rdBase
from pathway_v43.pollutant.chemstate import build_chemical_state, strict_identity_of
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis
from pathway_v43.pollutant.path_context import build_condition_fact, build_requirement, build_path_context
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission, check_edit_against_donor, center_evidence_from_donor_diagnostic
from pathway_v43.services.atom_tool import render, execute_edits

def emit(case, **kw):
    print(json.dumps(dict(case=case, **kw), ensure_ascii=False, sort_keys=True, default=str))

def run(case, fn):
    try: emit(case, **fn())
    except Exception as e: emit(case, exception_type=type(e).__name__,exception=str(e),traceback=traceback.format_exc())

def call(fn):
    try: return {'accepted':True,'value':fn()}
    except Exception as e: return {'accepted':False,'error_type':type(e).__name__,'error':str(e),'detail':getattr(e,'detail',{})}

def state_case(s):
    m=Chem.MolFromSmiles(s)
    return {'input':s,'rdkit_parsed':m is not None,'rdkit_reemitted':Chem.MolToCXSmiles(m) if m else None,
        'rdkit_atom_props':[a.GetPropsAsDict(includePrivate=False,includeComputed=False) for a in m.GetAtoms()] if m else [],
        'build':call(lambda:build_chemical_state(s,'raw_input').to_dict()),
        'strict':call(lambda:strict_identity_of(s))}

emit('meta',head='6d9020130a481866ce2f3b79933907a33d8cfc9e',rdkit=rdBase.rdkitVersion,
     scope='synthetic public APIs; chemistry statements are structural/contract claims, not experiment or biology')

run('cx_registered_head_comma_appended_unknown',lambda:{'rows':[state_case(s) for s in [
    'C[C@@H](N)C(=O)O |r|',
    'C[C@@H](N)C(=O)O |atomProp:0.note.hello|',
    'C[C@@H](N)C(=O)O |atomProp:0.note.hello,r|',
    'C1CCCCC1 |atomProp:0.note.hello,Ln:1|',
    'CO |SgD:0:note:hello::::|', 'CO |SgD:0:note:hello::::,r|',
    'CO |SgD:0:note:a,b::::,r|',
    'CCCCCC |Sg:n:1,2,3:3:ht:::,r|',
    'CO |atomProp:0.note.hello,w:1.0|'] ]})

def generated_metadata():
    rows=[]
    for mode in ['label_space','atomprop_space','dat_space','dat_comma','label_no_space','atomprop_no_space']:
        m=Chem.MolFromSmiles('CO')
        if mode=='label_space':m.GetAtomWithIdx(0).SetProp('atomLabel','foo bar')
        elif mode=='atomprop_space':m.GetAtomWithIdx(0).SetProp('note','hello world')
        elif mode=='dat_space':Chem.CreateMolDataSubstanceGroup(m,'review_note','hello world').SetAtoms([0])
        elif mode=='dat_comma':Chem.CreateMolDataSubstanceGroup(m,'review_note','hello,world').SetAtoms([0])
        elif mode=='label_no_space':m.GetAtomWithIdx(0).SetProp('atomLabel','foobar')
        elif mode=='atomprop_no_space':m.GetAtomWithIdx(0).SetProp('note','helloworld')
        s=Chem.MolToCXSmiles(m);row=state_case(s);row['generation']=mode;rows.append(row)
    return {'nature':'RDKit generated CXSMILES from registered metadata, then public factory/strict inputs', 'rows':rows}
run('rdkit_writer_generated_registered_content_spaces',generated_metadata)

ctx=build_path_context(condition_facts=[build_condition_fact(key='oxygen_regime',value='aerobic',status='known_present')],
    accumulated_requirements=[build_requirement(key='oxygen_regime',level='essential',value='aerobic',source_refs=['synthetic:requirement'])],
    assessment_scope=['oxygen_regime'])

def diagnostic_case(s, mode):
    r=render(s,name='D');m=Chem.MolFromSmiles(s);ids={v:k for k,v in r.atom_id_map.items()}
    oxygen=next(a for a in m.GetAtoms() if a.GetSymbol()=='O' and a.GetDegree()==1)
    carbon=oxygen.GetNeighbors()[0];centers=[ids[carbon.GetIdx()],ids[oxygen.GetIdx()]]
    edits=[{'op':'change_bond_order','atom1':centers[0],'atom2':centers[1],'from_order':'single','to_order':'double'}]
    real=execute_edits(r,edits);assert real['ok'],real
    current={'smiles':s,'atom_id_map':dict(r.atom_id_map)};result=copy.deepcopy(real)
    target=real['product_smiles']
    if mode=='current_r':current['smiles']+=' |r|'
    elif mode=='mapped_r':result['product_mapped_smiles']+=' |r|'
    elif mode=='plain_r':result['product_smiles']+=' |r|'
    elif mode=='target_r':target+=' |r|'
    diag=check_edit_against_donor(current=current,donor={'center_atom_ids':['dC','dO']},
        alignment={'status':'resolved','donor_to_current':{'dC':centers[0],'dO':centers[1]},'ref':'synthetic:r6:alignment'},
        expectation={'target_smiles':target},result=result,edits=edits)
    states={};parts=[]
    for side,rows in [('reactant',[(s,1)]),('product',[(real['product_smiles'],1),('[H][H]',1)])]:
        for i,(structure,coeff) in enumerate(rows):
            st=build_chemical_state(structure,'raw_input');states[st.state_id]=st
            role='primary_substrate' if side=='reactant' else 'principal_product' if i==0 else 'coproduct'
            parts.append(Participant(state_ref=st.state_id,side=side,role=role,coefficient=coeff,coefficient_status='known'))
    hyp=build_hypothesis(parent_path_id='synthetic:r6:root',substrate_state_ref=parts[0].state_ref,participants=parts,
        participant_list_status='declared_complete',step_scope='net_reaction',origin_group_key='synthetic:r6:cx:'+mode)
    ev=center_evidence_from_donor_diagnostic(diag)
    audit=audit_hypothesis(hyp,states=states,context=ctx,center_evidence=ev)
    admission=decide_admission(audit,gate_decisions={'gate_direction_source':{'ok':True}})
    return {'nature':'real base AtomTool output; only the named structural string receives interface-added raw CX r, proof axes are not tampered',
        'mode':mode,'input':s,'current':current,'real_execution':real,'diagnostic_input_result':result,'edits':edits,
        'diagnostic':diag.to_dict(),'hypothesis':hyp.to_dict(),'audit':audit.to_dict(),'admission':admission}

for mode in ['clean','current_r','mapped_r','plain_r','target_r']:
    run('donor_public_ethanol_'+mode,lambda mode=mode:diagnostic_case('CCO',mode))
run('donor_public_specified_stereo_current_r',lambda:diagnostic_case('F[C@H](Cl)CCO','current_r'))
