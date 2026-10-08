from pathlib import Path
import sys, json, sqlite3, hashlib, socket, traceback
sys.path.insert(0, str(Path(sys.argv[1])/'src'));sys.path.insert(0,str(Path(sys.argv[1])/'tests'))
from test_ppv1_s4a_endpoint import spec, oxygen_req, mineralization_evidence, cyclic_dep
from pathway_v43.config import resolve_config
from pathway_v43.workflow.runner import start_run,resume_run
from pathway_v43.storage.run_identity import PROFILE_POLLUTANT_PATHWAY_V1
out=Path(sys.argv[2]);out.mkdir(exist_ok=False); runs=out/'runs'; calls=[]
orig=socket.socket.connect
def reject(self,address):
 calls.append(repr(address));raise RuntimeError('network forbidden in synthetic review')
socket.socket.connect=reject

def snapshot(db):
 con=sqlite3.connect(db);con.row_factory=sqlite3.Row
 tables={r[0]:[dict(row) for row in con.execute('SELECT * FROM "'+r[0]+'"')] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")}
 schema=list(con.execute('SELECT name,sql FROM sqlite_master ORDER BY name'));con.close()
 return {'tables':tables,'schema':[(r[0],r[1])for r in schema], 'database_sha256':hashlib.sha256(db.read_bytes()).hexdigest()}
base=spec('B','CC=O','donor-B'); ev=mineralization_evidence()
cases={
 'legal_supported_source':{'pools':{'CCO':[base]},'endpoint_evidence':[ev]},
 'unknown_essential_condition':{'pools':{'CCO':[spec('B','CC=O','donor-B',requirements=oxygen_req())]},'endpoint_evidence':[ev]},
 'explicit_unknown_essential_condition':{'condition_facts':[{'key':'oxygen_regime','value':None,'status':'unknown','source_ref':'src:synthetic'}],'pools':{'CCO':[spec('B','CC=O','donor-B',requirements=oxygen_req())]},'endpoint_evidence':[ev]},
 'conflict_essential_condition':{'condition_facts':[{'key':'oxygen_regime','value':'anaerobic','status':'known_present','source_ref':'src:synthetic'}],'pools':{'CCO':[spec('B','CC=O','donor-B',requirements=oxygen_req())]},'endpoint_evidence':[ev]},
 'known_essential_condition':{'condition_facts':[{'key':'oxygen_regime','value':'aerobic','status':'known_present','source_ref':'src:synthetic'}],'pools':{'CCO':[spec('B','CC=O','donor-B',requirements=oxygen_req())]},'endpoint_evidence':[ev]},
 'unresolved_cyclic_dependency':{'pools':{'CCO':[spec('B','CC=O','donor-B',dependencies=cyclic_dep('missing'))]},'endpoint_evidence':[ev]},
 'supported_cyclic_dependency':{'pools':{'CCO':[spec('B','CC=O','donor-B',dependencies=cyclic_dep('supported'))]},'endpoint_evidence':[ev]},
}
results=[]
for key,plan in cases.items():
 rec={'case':key,'plan':plan}
 try:
  first=start_run(config=resolve_config(),runs_root=runs,run_id=key,smiles='CCO',max_depth=3,max_expansions=10,max_frontier_width=2,finder=object(),scripted=True,profile=PROFILE_POLLUTANT_PATHWAY_V1,ppv1_plan=plan)
  rec['first']=first;rec['snapshot_first']=snapshot(runs/key/'pollutant.sqlite')
  second=resume_run(config=resolve_config(),runs_root=runs,run_id=key)
  rec['resume']=second;rec['snapshot_resume']=snapshot(runs/key/'pollutant.sqlite')
 except Exception as ex:
  rec['exception']={'class':type(ex).__name__,'message':str(ex),'detail':getattr(ex,'detail',None),'traceback':traceback.format_exc()}
 results.append(rec);print(json.dumps({'case':key,'endpoint':rec.get('first',{}).get('endpoint'),'exception':rec.get('exception'),'counts':rec.get('first',{}).get('counts')},ensure_ascii=False))
(out/'results.json').write_text(json.dumps({'network_connect_calls':calls,'cases':results},ensure_ascii=False,indent=2,default=str))
assert calls==[],calls
