from pathlib import Path
import json,hashlib,shutil,subprocess,sys,datetime
ROOT=Path(__file__).resolve().parent;REPO=Path('/Volumes/CC/Enzyme_Agent/dependingv43');PACK=ROOT/'package';PACK.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True))
obs=json.loads((ROOT/'observations_r2.json').read_text())+json.loads((ROOT/'additional_observations.json').read_text());summary={'top_level_observations':len(obs),'contract_satisfied_observations':sum(x['current_contract_observed'] for x in obs),'residual_groups':['S3B-01'],'cases':[]}
for o in obs:
 case={'case':o['case'],'current_contract_observed':o['current_contract_observed']}
 if o['case'].startswith('self_consistent_replaced_plan_'):
  n=o['case'];original=json.loads((ROOT/'tables'/(n+'_start.json')).read_text());mutated=json.loads((ROOT/'tables'/(n+'_mutated.json')).read_text());after=json.loads((ROOT/'tables'/(n+'_resume.json')).read_text());h=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest();case.update({'classification':'same_S3B01_residual','db_logical_hash_before_artifact_mutation':h(original['tables']),'db_logical_hash_after_artifact_mutation':h(mutated['tables']),'db_logical_hash_after_resume':h(after['tables']),'artifact_only_mutation_kept_db_tables':original['tables']==mutated['tables'],'root_digest':o['detail']['root_frozen_digest'],'new_plan_digest':o['detail']['new_frozen_digest'],'transition_count':len(o['detail']['transition_actions']),'plan_version':json.loads((ROOT/'inputs'/(n+'_mutation.json')).read_text())['new_envelope']['payload']['plan_version']})
 summary['cases'].append(case)
write(ROOT/'adjudicated_summary.json',summary)
from importlib.metadata import version
import sqlite3
metadata={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'parent':subprocess.check_output(['git','rev-parse','HEAD^'],cwd=REPO,text=True).strip(),'date_local':'2026-10-08','assembled_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'sqlite':sqlite3.sqlite_version,'rdkit':version('rdkit'),'command_first':[sys.executable,'-B',str(ROOT/'scripts/review_recovery.py')],'command_additional':[sys.executable,'-B',str(ROOT/'scripts/review_additional.py')],'controllers_exit_codes':[0,0],'environment':{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'src')},'network_calls':0,'external_model_calls':0,'pytest_runs':0,'source_checks':[],'interruption':None,'source_main_repo_modified':False}
for v in json.loads((ROOT/'input_manifest.json').read_text())['sources']:
 p=ROOT/v['path'];q=REPO/v['path'];metadata['source_checks'].append({'path':v['path'],'same_as_input':sha(p)==v['sha256'],'same_as_repo':sha(p)==sha(q)})
assert all(v['same_as_input'] and v['same_as_repo'] for v in metadata['source_checks']);write(ROOT/'execution_metadata.json',metadata)
source=ROOT/'src/pathway_v43/pollutant/runflow.py';lines=source.read_text().splitlines();segs=[(211,253),(364,494),(566,581),(1000,1035),(1093,1143),(1250,1290),(1350,1403)]
(ROOT/'source_review_lines.txt').write_text('\n\n'.join('\n'.join(f'{i+1:5}: {lines[i]}' for i in range(a-1,min(b,len(lines)))) for a,b in segs))
for d in ('src','scripts','raw_old_scripts','original_inputs','inputs','logs','tables'):shutil.copytree(ROOT/d,PACK/d)
for name in ('pyproject.toml','README.md','input_manifest.json','observations_r2.json','additional_observations.json','adjudicated_summary.json','execution_metadata.json','source_review_lines.txt','finalize_package.py'):shutil.copy2(ROOT/name,PACK/name)
omit=[]
for run in sorted((ROOT/'synthetic_runs/runs').iterdir()):
 for p in sorted(run.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(ROOT/'synthetic_runs/runs');binary=p.name in ('pollutant.sqlite','pollutant.sqlite-wal','pollutant.sqlite-shm')
  if binary:omit.append({'path':str(rel),'bytes':p.stat().st_size,'sha256':sha(p),'reason':'synthetic_binary_db_complete_logical_before_after_tables_preserved'})
  else:q=PACK/'artifacts_final'/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
# Barrier files contain only ephemeral coordination; receipts already preserved in observation JSON.
for p in sorted((ROOT/'synthetic_runs').rglob('*')):
 if p.is_file() and not p.is_relative_to(ROOT/'synthetic_runs/runs'):omit.append({'path':str(p.relative_to(ROOT/'synthetic_runs')),'bytes':p.stat().st_size,'sha256':sha(p),'reason':'barrier_coordination_receipts_preserved_in_observations'})
write(PACK/'omitted_binary_inventory.json',omit)
files=[]
for p in sorted(PACK.rglob('*')):
 if p.is_file():files.append({'path':str(p.relative_to(PACK)),'bytes':p.stat().st_size,'sha256':sha(p)})
write(PACK/'manifest.json',{'schema':'ppv1-independent-evidence-sha256-v1','head':metadata['head'],'files':files});msha=sha(PACK/'manifest.json');(PACK/'manifest.sha256').write_text(msha+'  manifest.json\n');(PACK/'SHA256SUMS').write_text(''.join(f"{x['sha256']}  {x['path']}\n" for x in files)+msha+'  manifest.json\n');print(json.dumps({'package':str(PACK),'manifest_sha256':msha,'payload_files':len(files),'payload_bytes':sum(x['bytes'] for x in files),'observations':len(obs),'satisfied':sum(x['current_contract_observed'] for x in obs),'residual_groups':['S3B-01']}))
