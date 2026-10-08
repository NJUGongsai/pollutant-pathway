from pathlib import Path
import json,ast,hashlib,subprocess,sys
repo=Path(sys.argv[1]);pkg=Path(sys.argv[2]); frozen='docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md'; records=[]
def git(*a):
 p=subprocess.run(['git',*a],cwd=repo,text=True,capture_output=True); records.append({'argv':['git',*a],'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr});return p
head=git('rev-parse','HEAD','HEAD^').stdout.splitlines(); existence={}
for ref in ['adf0287abef0c4803962fee0df0065d8e6f3793d','0e345e83de27e7369334fe092da7a6ccbc8afd6c','fc40605819201ae4a7101fc500b19083d78383b0',head[0]]:
 p=git('show',ref+':'+frozen);existence[ref]={'exists':p.returncode==0,'sha256':hashlib.sha256(p.stdout.encode()).hexdigest() if p.returncode==0 else None}
assert existence[head[0]]['sha256']==existence['0e345e83de27e7369334fe092da7a6ccbc8afd6c']['sha256']
assert not git('diff','0e345e83de27e7369334fe092da7a6ccbc8afd6c',head[0],'--',frozen).stdout
assert not git('diff','adf0287abef0c4803962fee0df0065d8e6f3793d','0e345e83de27e7369334fe092da7a6ccbc8afd6c','--','src','tests').stdout
modules=['endpoint.py','native_result.py','native_export.py','v3_projection.py','runflow.py']; module_details={}
for m in modules:
 rel='src/pathway_v43/pollutant/'+m;p=repo/rel;tree=ast.parse(p.read_text());imports=[{'line':n.lineno,'module':getattr(n,'module',None),'names':[a.name for a in n.names]}for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))];calls=[];stateidassign=[]
 for n in ast.walk(tree):
  if isinstance(n,ast.Call):
   name=ast.unparse(n.func)
   if any(x in name for x in ['chemical_state','ChemicalState','strict_identity','build_product_state','MolFrom','state_id','stable_id']):calls.append({'line':n.lineno,'call':ast.unparse(n)})
  if isinstance(n,(ast.Assign,ast.AnnAssign)):
   targets=n.targets if isinstance(n,ast.Assign) else [n.target]
   if any(isinstance(x,ast.Name) and x.id=='state_id' for x in targets):stateidassign.append({'line':n.lineno,'assignment':ast.unparse(n)})
 diff=git('diff','adf0287abef0c4803962fee0df0065d8e6f3793d',head[0],'--',rel).stdout
 module_details[m]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'imports':imports,'potential_identity_calls':calls,'local_state_id_assignments':stateidassign,'diff':diff,'comment':'local assignment of existing row ID is reading, not generation; runflow keeps existing S3 chemistry factory calls; inspect only S4 diff for new chemistry behavior.'}
 if m!='runflow.py': assert not [c for c in calls if any(x in c['call']for x in ['ChemicalState','build_chemical_state','build_product_state','strict_identity','MolFrom'])]
 else:
  added=[line for line in diff.splitlines()if line.startswith('+')and not line.startswith('+++')]
  assert not [line for line in added if any(x in line for x in ['build_chemical_state(', 'build_product_state(', 'MolFrom','strict_identity('])]
# Exact current line anchors sampled from r17, not text claims treated as execution.
anchors=[('endpoint.py',177,186,'_CLAIM_REQUIRED_FIELDS'),('endpoint.py',192,212,'def _evidence_dedup_key'),('endpoint.py',732,742,'EXECUTION_STATUS_COMPLETED'),('endpoint.py',745,749,'fate_reported'),('native_result.py',88,141,'stable_id("soutc", action_id)'),('native_export.py',370,377,'[:24]'),('native_export.py',438,496,'read_run_endpoint'),('v3_projection.py',278,278,'"lossy_projection": True'),('runflow.py',1347,1393,'read_native_export')]
checked=[]
for name,lo,hi,token in anchors:
 text='\n'.join((repo/'src/pathway_v43/pollutant'/name).read_text().splitlines()[lo-1:hi]);checked.append({'source':name,'lines':[lo,hi],'token':token,'match':token in text,'excerpt':text})
 assert token in text,(name,lo,hi)
out={'head':head,'frozen_comparisons':existence,'modules':module_details,'mimo_r17_anchor_spotcheck':checked,'git_commands':records,'scope_note':'Confirms immutable criteria text and absence of new state identity-generation in S4 diff; does not certify S4 endpoint semantic conformance.'}
(pkg/'logs/static_contract_result.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({'head':head,'frozen_sha256':existence[head[0]]['sha256'],'criteria_unchanged':True,'mimo_anchor_checks':len(checked),'new_identity_generation_found':False},ensure_ascii=False))
