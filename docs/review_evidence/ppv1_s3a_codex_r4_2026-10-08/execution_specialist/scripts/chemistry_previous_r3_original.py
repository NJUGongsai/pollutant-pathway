#!/usr/bin/env python3
"""No external assets/network. Run with the fresh isolated src/tests tree."""
from __future__ import annotations
import argparse,ast,hashlib,json,sys,copy
from dataclasses import asdict
from pathlib import Path

def capture(fn):
    try:
        v=fn()
        if hasattr(v,'to_dict'):v=v.to_dict()
        elif hasattr(v,'__dataclass_fields__'):v=asdict(v)
        return {'returned':v}
    except Exception as e:return {'error':type(e).__name__,'detail':getattr(e,'detail',{}),'message':str(e)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--inputs',required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False);inputs=Path(a.inputs)
    from rdkit import Chem,rdBase
    from pathway_v43.pollutant.chemstate import build_chemical_state,ChemicalState,strict_identity_of
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.pollutant.audit import check_edit_against_donor,center_evidence_from_donor_diagnostic,audit_hypothesis
    from pathway_v43.storage.run_identity import build_run_identity,write_run_identity,code_identity,PROFILE_POLLUTANT_PATHWAY_V1
    from pathway_v43.config import resolve_config
    from pathway_v43.workflow.runner import start_run,resume_run
    from s3a_worker import make_fixture
    src=Path(sys.modules['pathway_v43'].__file__).parent
    rows=[]
    def emit(row):rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    clean=build_chemical_state('CCO','raw_input').to_dict()
    for label,field,value in [('raw_r','structure_smiles_raw','CCO |r|'),('canonical_r','smiles_isomeric','CCO |r|'),('canonical_bad','smiles_isomeric','INVALID_STRUCTURE')]:
        payload=copy.deepcopy(clean);payload[field]=value
        # Raw RDKit parse is observed directly, not inferred from source comments.
        mol=Chem.MolFromSmiles(value)
        rdkit={'parsed':mol is not None,'written':Chem.MolToCXSmiles(mol) if mol is not None else None}
        store=PollutantPathwayStore(out/(label+'.sqlite'));before=store.counts()
        writer=capture(lambda:store.put_state(payload));after=store.counts()
        emit({'case':label,'input':payload,'rdkit':rdkit,'restore':capture(lambda:ChemicalState.from_dict(payload)),
          'writer':writer,'writer_changed':before!=after,'counts_before':before,'counts_after':after})
        store.close()
    # Registered metadata retention/removal controls, actual locked-version roundtrip.
    structures=['CCO |atomProp:0.note.hello world|','CCO |atomProp:0.note.x:1.foo.y|',
      'CCO |SgD:0:note:a,b hello world::::|','CCO |SgD:0:note:hello world::::|',
      'CCO |$a b;c;d$|','CCO |(0,0,;1,0,;2,0,)|',
      'F[C@H](Cl)[C@H](Br)I |&1:1,3|','F[C@H](Cl)[C@H](Br)I |o1:1,3|',
      '[CH3] |^1:0|']
    for i,s in enumerate(structures):
        result=capture(lambda:build_chemical_state(s,'raw_input'))
        if 'returned' in result:
            canonical=result['returned']['smiles_isomeric'];result['canonical_reparse']=capture(lambda:build_chemical_state(canonical,'source_product'))
            result['id_equal']=result['returned']['state_id']==result['canonical_reparse'].get('returned',{}).get('state_id')
        emit({'case':'registered_roundtrip_'+str(i),'input':s,'result':result})
    # Failure early-return does not parse unusable strings; converter is metadata only.
    fail_inputs={'current':{'smiles':'unparseable |r|','atom_id_map':{}},
      'donor':{'center_atom_ids':['dC']},'alignment':{'status':'resolved','donor_to_current':{'dC':'x'},'ref':'synthetic-a'},
      'expectation':{'target_smiles':'unparseable |r|'},'result':{'ok':False,'reasons':['synthetic-failure'],'product_smiles':'unparseable |r|','product_mapped_smiles':'unparseable |r|','atom_id_map':{},'n_edits':1},'edits':[]}
    diag=check_edit_against_donor(**fail_inputs);evidence=center_evidence_from_donor_diagnostic(diag)
    sub,prod,hyp,_,_=make_fixture('diag-run','parent','origin','context')
    audit=audit_hypothesis(hyp,states={sub.state_id:sub,prod.state_id:prod},center_evidence=evidence)
    emit({'case':'failure_three_none_converter_scope','inputs':fail_inputs,'diagnostic':asdict(diag),'converter':evidence,'hypothesis':hyp.to_dict(),
      'states':[sub.to_dict(),prod.to_dict()],'audit':audit.to_dict()})
    # Public PPV1 endpoints reject before any legacy fallback, even with model object.
    runs=out/'runner_runs';config=resolve_config()
    start=capture(lambda:start_run(config=config,runs_root=runs,run_id='ppv1-refused',smiles='CCO',max_depth=2,
      max_expansions=5,max_frontier_width=3,finder=object(),scripted=True,profile=PROFILE_POLLUTANT_PATHWAY_V1,model=object()))
    absent=not(runs/'ppv1-refused').exists()
    identity=build_run_identity(run_id='ppv1-refused',root_smiles='CCO',root_cn='CCO',strategy={'max_depth':2,'max_expansions':5,'max_frontier_width':3},
      asset_identity={'mode':'scripted_fixture'},v3_code_identity={'mode':'scripted_fixture'},prediction=None,profile=PROFILE_POLLUTANT_PATHWAY_V1)
    write_run_identity(runs,identity)
    path=runs/'ppv1-refused/run_identity.json';before=path.read_bytes()
    resume=capture(lambda:resume_run(config=config,runs_root=runs,run_id='ppv1-refused',finder=object(),model=object()))
    emit({'case':'runner_public_failclosed','start':start,'start_run_dir_absent':absent,'resume':resume,'saved_identity_unchanged':before==path.read_bytes(),
      'directory_files':[str(p.relative_to(runs)) for p in runs.rglob('*') if p.is_file()]})
    # Static claims: audit caller and broad-handler reachability, full src scope.
    treefiles=sorted(src.rglob('*.py')); raises=[];calls=[];specific=[];search_calls=[]
    for file in treefiles:
        tree=ast.parse(file.read_text());parents={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        def ancestry(node):
            out=[]
            while node in parents:node=parents[node];out.append(node)
            return out
        for node in ast.walk(tree):
            name=None
            if isinstance(node,ast.Call):name=node.func.id if isinstance(node.func,ast.Name) else getattr(node.func,'attr',None)
            if name in ('audit_hypothesis','check_edit_against_donor'):
                calls.append({'file':str(file.relative_to(src)),'line':node.lineno,'call':name,'try_ancestors':[n.lineno for n in ancestry(node) if isinstance(n,ast.Try)]})
            if isinstance(node,ast.Raise) and isinstance(node.exc,ast.Call) and isinstance(node.exc.func,ast.Name) and node.exc.func.id=='AuditContractError':
                handlers=[]
                child=node
                for anc in ancestry(node):
                    if isinstance(anc,ast.Try) and child in anc.body:
                        for h in anc.handlers:
                            if h.type is None or isinstance(h.type,ast.Name) and h.type.id in ('Exception','BaseException'):
                                handlers.append({'try_line':anc.lineno,'handler_line':h.lineno,'bare':h.type is None,'body':ast.unparse(h)})
                    child=anc
                raises.append({'file':str(file.relative_to(src)),'line':node.lineno,'enclosing_broad_handlers':handlers})
            if isinstance(node,ast.ExceptHandler) and isinstance(node.type,ast.Name) and node.type.id=='AuditContractError':specific.append({'file':str(file.relative_to(src)),'line':node.lineno})
            if str(file.relative_to(src))=='pollutant/search.py' and name in ('build_chemical_state','strict_identity_of','MolFromSmiles','audit_hypothesis','submit_event'):
                search_calls.append({'line':node.lineno,'call':name})
    oldrunner=(inputs/'baseline_workflow_runner.py').read_text();newrunner=(src/'workflow/runner.py').read_text()
    oldtree=ast.parse(oldrunner);newtree=ast.parse(newrunner)
    oldtree.body=[n for n in oldtree.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) or n.name!='_refuse_undelivered_profile']
    newtree.body=[n for n in newtree.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) or n.name!='_refuse_undelivered_profile']
    identity=code_identity();oldhashes=dict(identity['files']);key='pathway_v43/workflow/runner.py';oldhashes[key]=hashlib.sha256(oldrunner.encode()).hexdigest()
    oldagg=hashlib.sha256('\n'.join(f'{k}:{v}' for k,v in sorted(oldhashes.items())).encode()).hexdigest()
    oldprofile=ast.parse((inputs/'baseline_pollutant_profile.py').read_text());newprofile=ast.parse((src/'pollutant/profile.py').read_text())
    def value(tree,name):
        for n in tree.body:
            if isinstance(n,ast.AnnAssign) and getattr(n.target,'id',None)==name:
                v=copy.deepcopy(n.value)
                for k,val in zip(v.keys,v.values) if isinstance(v,ast.Dict) else []:
                    if isinstance(val,ast.Name) and val.id=='SEARCH_LIMITS_VERSION':val.id='__VERSION_UNUSED__'
                if isinstance(v,ast.Dict):v.values=[ast.Constant('__VERSION_UNUSED__') if isinstance(val,ast.Name) and val.id=='__VERSION_UNUSED__' else val for val in v.values]
                return ast.literal_eval(v)
        raise ValueError(name)
    olddefaults=value(oldprofile,'SEARCH_LIMITS_DEFAULTS');newdefaults=value(newprofile,'SEARCH_LIMITS_DEFAULTS')
    olddefaults.pop('version');newdefaults.pop('version')
    static={'actual_rdkit':rdBase.rdkitVersion,'audit_raises':raises,'caller_inventory':calls,'except_AuditContractError':specific,'search_calls':search_calls,
      'runner_AST_except_refuse_function_equal':ast.dump(oldtree)==ast.dump(newtree),'legacy_aggregate_current':identity['aggregate_sha256'],
      'legacy_aggregate_baseline_runner_only':oldagg,'legacy_aggregate_changed':oldagg!=identity['aggregate_sha256'],'legacy_included_changed_files':(['workflow/runner.py'] if hashlib.sha256(oldrunner.encode()).hexdigest()!=hashlib.sha256(newrunner.encode()).hexdigest() else []), 'actual_HEAD':'41d0cd55f3def050a62325f00235cf22da302d2e', 'actual_baseline_HEAD':'dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03',
      'limits_defaults_except_version_equal':olddefaults==newdefaults,'limits_ranges_equal':value(oldprofile,'SEARCH_LIMITS_RANGES')==value(newprofile,'SEARCH_LIMITS_RANGES')}
    (out/'static_inventory.json').write_text(json.dumps(static,indent=2,ensure_ascii=False))
    emit({'case':'static_inventory','result':static})
    assert all(not r['enclosing_broad_handlers'] for r in raises)
    assert not specific
    assert not [c for c in calls if c['call']=='audit_hypothesis']
    assert static['runner_AST_except_refuse_function_equal']
    assert static['limits_defaults_except_version_equal'] and static['limits_ranges_equal']
    assert all(v is None for v in (diag.reaction_center_match,diag.strict_target_match,diag.legacy_cn_match)) and diag.center_evidence=={}
    assert 'checker_scope' not in evidence and 'proof_record' not in evidence and evidence['center_match'] is None
    assert absent and before==path.read_bytes() and start.get('error')=='RunError' and resume.get('error')=='RunError'
    print(json.dumps({'assertions':'complete','cases':len(rows)},ensure_ascii=False))

if __name__=='__main__':main()
