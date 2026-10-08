#!/usr/bin/env python3
import ast,hashlib,json,sys,copy
from pathlib import Path
from rdkit import rdBase
from pathway_v43.storage.run_identity import code_identity
import pathway_v43
inputs=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=False,parents=True)
src=Path(pathway_v43.__file__).parent
def emit(row):print(json.dumps(row,ensure_ascii=False),flush=True)
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
  'legacy_aggregate_baseline_runner_only':oldagg,'legacy_aggregate_changed':oldagg!=identity['aggregate_sha256'],'legacy_included_changed_files':['workflow/runner.py'],
  'limits_defaults_except_version_equal':olddefaults==newdefaults,'limits_ranges_equal':value(oldprofile,'SEARCH_LIMITS_RANGES')==value(newprofile,'SEARCH_LIMITS_RANGES')}
(out/'static_inventory.json').write_text(json.dumps(static,indent=2,ensure_ascii=False))
emit({'case':'static_inventory','result':static})
assert all(not r['enclosing_broad_handlers'] for r in raises)
assert not specific
assert not [c for c in calls if c['call']=='audit_hypothesis']
assert static['runner_AST_except_refuse_function_equal']
assert static['limits_defaults_except_version_equal'] and static['limits_ranges_equal']
print(json.dumps({'assertions':'complete','scope':'static inventory only; prior chemistry/public runner logs reused'}))
