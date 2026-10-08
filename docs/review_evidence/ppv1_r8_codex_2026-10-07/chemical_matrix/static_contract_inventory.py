"""Read-only AST/grep inventory of isolated src, no import or execution."""
import ast, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
results={'actual_HEAD':json.loads((ROOT/'metadata.json').read_text())['actual_HEAD'],'calls':[],'assignments':[],'audit_contract_raises':[],'source_catches':[]}
for p in sorted((ROOT/'src').rglob('*.py')):
 text=p.read_text();tree=ast.parse(text);parents={id(child):node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
 def ancestors(n):
  a=[]
  while id(n) in parents:n=parents[id(n)];a.append(n)
  return a
 def name(n):
  if isinstance(n,ast.Name):return n.id
  if isinstance(n,ast.Attribute):return name(n.value)+'.'+n.attr
  return ast.unparse(n) if n is not None else 'bare'
 def context(n):
  return {'path':str(p.relative_to(ROOT)),'line':n.lineno,'functions':[a.name for a in ancestors(n) if isinstance(a,(ast.FunctionDef,ast.AsyncFunctionDef))],'ancestor_try_catches':[{'line':a.lineno,'handlers':[name(h.type) for h in a.handlers],'inside_try_body': any(n is c or n in ast.walk(c) for c in a.body)} for a in ancestors(n) if isinstance(a,ast.Try)]}
 for n in ast.walk(tree):
  if isinstance(n,ast.Call) and name(n.func).split('.')[-1] in ['ChemicalState','MolFromSmiles','audit_hypothesis','check_edit_against_donor']:
   results['calls'].append(dict(context(n),call=name(n.func)))
  if isinstance(n,(ast.Assign,ast.AnnAssign,ast.AugAssign)):
   targets=n.targets if isinstance(n,ast.Assign) else [n.target]
   for target in targets:
    if isinstance(target,ast.Attribute) and target.attr in ['smiles_isomeric','structure_smiles_raw']:
     results['assignments'].append(dict(context(n),target=ast.unparse(target)))
  if isinstance(n,ast.Raise) and isinstance(n.exc,ast.Call) and name(n.exc.func).split('.')[-1]=='AuditContractError':
   results['audit_contract_raises'].append(context(n))
  if isinstance(n,ast.ExceptHandler):
   if name(n.type) in ['AuditContractError','Exception','bare']:
    results['source_catches'].append(dict(context(n),catch=name(n.type)))
r=subprocess.run(['rg','-n','except AuditContractError',str(ROOT/'src')],text=True,capture_output=True)
results['literal_grep']={'command':['rg','-n','except AuditContractError',str(ROOT/'src')],'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
results['summary']={'ChemicalState_calls':sum(x['call'].split('.')[-1]=='ChemicalState' for x in results['calls']),'audit_hypothesis_calls':sum(x['call'].split('.')[-1]=='audit_hypothesis' for x in results['calls']),'check_edit_against_donor_calls':sum(x['call'].split('.')[-1]=='check_edit_against_donor' for x in results['calls']),'state_field_attribute_assignments':len(results['assignments']),'AuditContractError_raises':len(results['audit_contract_raises'])}
print(json.dumps(results,ensure_ascii=False,sort_keys=True,indent=2))
