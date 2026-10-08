from pathlib import Path
import json, copy, dataclasses, traceback, sqlite3, hashlib, sys
from rdkit import Chem
from pathway_v43.pollutant.audit import check_edit_against_donor, center_evidence_from_donor_diagnostic, audit_hypothesis, decide_admission
from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis
from pathway_v43.pollutant.path_context import build_path_context, build_condition_fact, build_requirement
from pathway_v43.pollutant.events import build_pathway_event, build_report_projection, build_expansion_plan
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.services.atom_tool import render, execute_edits
from pathway_v43.pollutant import profile

OUT=Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=False)

def normalize_result(molecule, idmap, base):
    plain=Chem.Mol(molecule)
    for a in plain.GetAtoms(): a.SetAtomMapNum(0)
    result=copy.deepcopy(base)
    result['product_smiles']=Chem.MolToSmiles(plain)
    result['product_mapped_smiles']=Chem.MolToSmiles(molecule)
    result['atom_id_map']=dict(idmap)
    return result

def db_snapshot(store):
    tables=[r[0] for r in store.conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name") if not r[0].startswith('sqlite_')]
    return {t:[dict(r) for r in store.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in tables}

def make_case(name, substrate='CCO', mutation=None, center='bond', stereo=False, mismatch=False):
    rendered=render(substrate,name='S')
    ids=dict(rendered.atom_id_map)
    current={'smiles':rendered.smiles,'atom_id_map':ids}
    if stereo:
        edits=[]
        mapped=Chem.MolFromSmiles(rendered.smiles)
        for a in mapped.GetAtoms(): a.SetAtomMapNum(a.GetIdx()+1)
        pt=next(a for a in mapped.GetAtoms() if a.GetSymbol()=='Pt')
        pt.SetIntProp('_chiralPermutation',2)
        result=normalize_result(mapped,ids,{'ok':True,'reasons':[],'n_edits':0,'protocol_version':'v43-editproto-2'})
        center_ids=[next(k for k,v in ids.items() if v==pt.GetIdx())]
        tool=None
    else:
        edits=[] if mutation=='only' else [{'op':'change_bond_order','atom1':'S_C_2','atom2':'S_O_1','from_order':'single','to_order':'double'}]
        tool=execute_edits(rendered,edits)
        assert tool['ok'] is True,tool
        result=copy.deepcopy(tool)
        if mutation in ('only','outside','inside'):
            mapped=Chem.MolFromSmiles(result['product_mapped_smiles'])
            target_idx=ids['S_O_1'] if mutation=='inside' else ids['S_C_1']
            atom=next(a for a in mapped.GetAtoms() if a.GetAtomMapNum()-1==target_idx)
            atom.SetIsotope(18 if mutation=='inside' else 13)
            result=normalize_result(mapped,ids,result)
        center_ids=['S_C_2','S_O_1'] if center=='bond' else sorted(ids)
    donor={'center_atom_ids':[f'd{i}' for i in range(len(center_ids))]}
    alignment={'status':'resolved','donor_to_current':dict(zip(donor['center_atom_ids'],center_ids)),'equivalence_classes':[],'ref':'synthetic:review:'+name}
    target=result['product_smiles'] if not mismatch else tool['product_smiles']
    expectation={'target_smiles':target}
    diag=check_edit_against_donor(current=current,donor=donor,alignment=alignment,expectation=expectation,result=result,edits=edits)
    evidence=center_evidence_from_donor_diagnostic(diag)
    smi=[rendered.smiles,result['product_smiles']]
    if edits: smi.append('[H][H]')
    states=[build_chemical_state(s,'source_product',[{'record':'synthetic:'+name}]) for s in smi]
    participants=[Participant(state_ref=states[0].state_id,side='reactant',role='primary_substrate',coefficient=1,coefficient_status='known'),Participant(state_ref=states[1].state_id,side='product',role='principal_product',coefficient=1,coefficient_status='known')]
    if edits:participants.append(Participant(state_ref=states[2].state_id,side='product',role='coproduct',coefficient=1,coefficient_status='known'))
    hyp=build_hypothesis(parent_path_id='synthetic:path',substrate_state_ref=states[0].state_id,participants=participants,participant_list_status='declared_complete',step_scope='net_reaction',origin_group_key='synthetic:'+name)
    context=build_path_context(condition_facts=[build_condition_fact(key='oxygen_regime',value='aerobic',status='known_present')],accumulated_requirements=[build_requirement(key='oxygen_regime',level='essential',value='aerobic',source_refs=['synthetic:rule'])],assessment_scope=['oxygen_regime'])
    audit=audit_hypothesis(hyp,states={s.state_id:s for s in states},context=context,center_evidence=evidence)
    admission,reasons=decide_admission(audit,gate_decisions={'gate_direction_source':{'ok':True}})
    center_check=next(c for c in audit.checks if c.name=='transformation_center')
    before=Chem.MolFromSmiles(current['smiles']);after=Chem.MolFromSmiles(result['product_mapped_smiles'])
    actual_isotope=[]
    for aid,idx in ids.items():
        b=before.GetAtomWithIdx(idx);a=next(a for a in after.GetAtoms() if a.GetAtomMapNum()-1==idx)
        if b.GetIsotope()!=a.GetIsotope():actual_isotope.append({'atom_id':aid,'before':b.GetIsotope(),'after':a.GetIsotope(),'outside_declared_center':aid not in center_ids})
    record={'name':name,'current':current,'edits':edits,'actual_atomtool_output_before_mutation':tool,'result_consumed_by_donor':result,'synthetic_tool_result_mutation':mutation,'donor':donor,'alignment':alignment,'expectation':expectation,'actual_isotope_changes':actual_isotope,'diagnostic':dataclasses.asdict(diag),'evidence':evidence,'states':[s.to_dict() for s in states],'hypothesis':hyp.to_dict(),'context':context.to_dict(),'audit':audit.to_dict(),'admission':admission,'admission_reasons':reasons,'center_status':center_check.status,'center_detail':center_check.detail,'ledger_before':None,'ledger_after':None,'submit_receipt':None,'replay_receipt':None}
    if admission=='expand':
        store=PollutantPathwayStore(OUT/(name+'.sqlite'))
        record['ledger_before']=db_snapshot(store)
        event=build_pathway_event(hyp,run_id='synthetic:'+name,context_hash=context.context_id)
        projection=build_report_projection(hyp,max_reportable=1,ranked_state_refs=[states[1].state_id])
        plan=build_expansion_plan(hyp,expanded=[states[1].state_id],deferred=[],not_tracked=[s.state_id for s in states[2:]],reasons={s.state_id:'synthetic coproduct' for s in states[2:]})
        kwargs={'report_projection':projection.to_dict(),'expansion_plan':plan.to_dict(),'states':[s.to_dict() for s in states],'hypothesis_dict':hyp.to_dict()}
        record['event']=dataclasses.asdict(event);record['projection']=projection.to_dict();record['expansion_plan']=plan.to_dict()
        record['submit_receipt']=store.submit_event(event,**kwargs)
        record['ledger_after']=db_snapshot(store)
        record['replay_receipt']=store.submit_event(event,**kwargs)
        record['ledger_after_replay']=db_snapshot(store)
        assert record['ledger_after']==record['ledger_after_replay']
        store.conn.close()
    else:record['not_submitted_reason']='admission did not expand; caller respected actual decision'
    (OUT/(name+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str)+'\n')
    summary={k:record[k] for k in ('name','actual_isotope_changes','admission','admission_reasons','center_status','submit_receipt','replay_receipt')}
    summary['center_product_coverage']=center_check.detail.get('product_coverage')
    summary['diagnostic_center_match']=diag.reaction_center_match
    summary['diagnostic_strict_target_match']=diag.strict_target_match
    summary['declaration_mismatches']=diag.declaration_mismatches
    summary['diagnostic_missing']=diag.missing_info_reasons
    print(json.dumps(summary,ensure_ascii=False,default=str),flush=True)
    return summary

cases=[('isotope_only',dict(mutation='only')),('bond_control',{}),('isotope_retained_bond_control',dict(substrate='[13CH3]CO')),('mixed_outside_isotope',dict(mutation='outside')),('mixed_inside_isotope',dict(mutation='inside')),('mixed_outside_isotope_all_center_control',dict(mutation='outside',center='all')),('mixed_outside_wrong_target_control',dict(mutation='outside',mismatch=True)),('non_tetra_stereo_only_control',dict(substrate='Cl[Pt@SP1](Br)(I)F',stereo=True))]
summaries=[]
for name,kw in cases:
    try:summaries.append(make_case(name,**kw))
    except Exception as exc:
        traceback.print_exc()
        failure={'name':name,'exception':type(exc).__name__,'message':str(exc),'detail':getattr(exc,'detail',None),'phase':'uncompleted case; no later stage claimed'}
        summaries.append(failure)
        (OUT/(name+'.failed.json')).write_text(json.dumps(failure,ensure_ascii=False,indent=2)+'\n')
(OUT/'summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2,default=str)+'\n')
print(json.dumps({'python':sys.version,'rdkit':__import__('rdkit').__version__,'sqlite':sqlite3.sqlite_version,'versions':{k:v for k,v in vars(profile).items() if k.startswith('PPV1_') and 'VERSION' in k and isinstance(v,str)}},ensure_ascii=False),flush=True)
assert not any('exception' in s for s in summaries),'Some probe cases failed before completion'
