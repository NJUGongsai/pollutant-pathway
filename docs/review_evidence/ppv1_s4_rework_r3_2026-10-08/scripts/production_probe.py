from pathlib import Path
import sys,json,copy,traceback
from unittest.mock import patch
from rdkit import Chem
from pathway_v43.pollutant import production as pm
from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.search import SearchLedger,search_policy_version
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.queue import schedule_hypotheses
from pathway_v43.pollutant.path_context import build_path_context,build_condition_fact,build_requirement
from pathway_v43.storage.artifact_store import ArtifactStore
OUT=Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=False)
EDITS=[{'op':'change_bond_order','atom1':'S_C_2','atom2':'S_O_1','from_order':'single','to_order':'double'}]

def tables(store):
    ts=[r[0] for r in store.conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name") if not r[0].startswith('sqlite_')]
    return {t:[dict(r) for r in store.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in ts}

def run(name,substrate,product,inject=False):
    home=OUT/name;home.mkdir()
    store=PollutantPathwayStore(home/'run.sqlite')
    art=ArtifactStore(home/'runs',name)
    ledger=SearchLedger(store,art,name)
    policy=build_profile_identity_block()
    ledger.register_search_run(name,policy)
    sub=build_chemical_state(substrate,'raw_input',[{'record':'synthetic:'+name}]);store.put_state(sub.to_dict())
    product_state=build_chemical_state(product,'source_product',[{'record':'synthetic:product'}])
    hydrogen=build_chemical_state('[H][H]','source_product',[{'record':'synthetic:hydrogen'}])
    context=build_path_context(condition_facts=[build_condition_fact(key='oxygen_regime',value='aerobic',status='known_present')],accumulated_requirements=[build_requirement(key='oxygen_regime',level='essential',value='aerobic',source_refs=['synthetic:rule'])],assessment_scope=['oxygen_regime'])
    cref=pm.persist_context(art,context)
    participants=[{'state_ref':sub.state_id,'side':'reactant','role':'primary_substrate','coefficient':1,'coefficient_status':'known'},{'state_ref':product_state.state_id,'side':'product','role':'principal_product','coefficient':1,'coefficient_status':'known'},{'state_ref':hydrogen.state_id,'side':'product','role':'coproduct','coefficient':1,'coefficient_status':'known'}]
    spec={'key':'B','product_smiles':product,'coproducts':['[H][H]'],'participants':participants,'participant_list_status':'declared_complete','coefficient':1,'transformation_ref':'synthetic:donor','origin_group_key':'synthetic:'+name,'edits':copy.deepcopy(EDITS),'donor':{'center_atom_ids':['dC','dO']},'alignment':{'status':'resolved','donor_to_current':{'dC':'S_C_2','dO':'S_O_1'},'equivalence_classes':[],'ref':'synthetic:align'},'expectation':{'target_smiles':product}}
    prepared=pm.prepare_hypothesis(spec,parent_path_id='synthetic:path',substrate_state=sub,transformation_ref=spec['transformation_ref'])
    q=schedule_hypotheses(ledger,run_id=name,parent_path_id='synthetic:path',context_ref=cref,parent_search_revision=0,pool=[{'hypothesis_key':'B','hypothesis_id':prepared['hypothesis'].hypothesis_id,'rank':1,'payload':{'task_key':'tk-B','spec':spec,'substrate_smiles':substrate,'context_ref':cref,'parent_path_id':'synthetic:path','depth':1}}],policy_version=search_policy_version(),depth=1)
    aid=q['selected'][0]['action_id'];receipt=ledger.claim_action(aid,worker_id='synthetic:w');attempt=receipt['attempt_refs'][0]
    before=tables(store);calls=[]
    real=pm.execute_edits
    def controlled(current,edits):
        raw=real(current,edits);changed=copy.deepcopy(raw)
        if inject:
            m=Chem.MolFromSmiles(changed['product_mapped_smiles'])
            a=next(a for a in m.GetAtoms() if a.GetAtomMapNum()-1==current.atom_id_map['S_C_1']);a.SetIsotope(13)
            plain=Chem.Mol(m)
            for a in plain.GetAtoms():a.SetAtomMapNum(0)
            changed['product_mapped_smiles']=Chem.MolToSmiles(m);changed['product_smiles']=Chem.MolToSmiles(plain)
        calls.append({'actual_atomtool_result':raw,'consumer_result':changed,'synthetic_isotope_mutation':inject})
        return changed
    with patch.object(pm,'execute_edits',controlled):
        output=pm.expand_hypothesis_production(ledger,aid,prepared=prepared,context=context,worker_id='synthetic:w',attempt_id=attempt,task_key='tk-B',substrate_state=sub,limits=ledger._limits(name),depth=1)
    after=tables(store)
    artifacts={str(p.relative_to(home)):p.read_text() for p in home.rglob('*.json')}
    record={'name':name,'spec':spec,'sub_state':sub.to_dict(),'context':context.to_dict(),'prepared_hypothesis':prepared['hypothesis'].to_dict(),'queue':q,'claim_receipt':receipt,'controlled_tool_calls':calls,'ledger_before':before,'ledger_after':after,'production_output':output,'artifact_json_text':artifacts,'network_calls':0,'proof_scope':'self_contained_recompute','limit':'Synthetic result substitution after true AtomTool call; does not prove unmodified AtomTool changes isotope.'}
    (OUT/(name+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str)+'\n')
    center=next(c for c in output['audit']['checks'] if c['name']=='transformation_center')
    summary={'name':name,'status':output['status'],'admission':output['admission'],'center_status':center['status'],'center_coverage':center['detail'].get('product_coverage'),'completed':output.get('completed'),'event_count':len(after['events']),'commit_count':len(after['search_commit_records']),'action_status':ledger.action(aid)['status'],'tool_calls':len(calls),'synthetic_tool_result_mutation':inject}
    print(json.dumps(summary,ensure_ascii=False,default=str),flush=True)
    store.conn.close()
    return summary
summaries=[]
for name,sub,prod,inj in [('production_bond_control','CCO','CC=O',False),('production_isotope_retained_control','[13CH3]CO','[13CH3]C=O',False),('production_mixed_outside_isotope','CCO','[13CH3]C=O',True)]:
    try:summaries.append(run(name,sub,prod,inj))
    except Exception as e:
        traceback.print_exc();summaries.append({'name':name,'exception':type(e).__name__,'message':str(e),'detail':getattr(e,'detail',None),'phase':'not completed; do not claim downstream success'})
(OUT/'summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2,default=str)+'\n')
assert not any('exception' in s for s in summaries)
