from pathlib import Path
import json,hashlib,shutil,subprocess,sys,datetime,sqlite3
from importlib.metadata import version
ROOT=Path(__file__).resolve().parent;REPO=Path('/Volumes/CC/Enzyme_Agent/dependingv43');PACK=ROOT/'package'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
if PACK.exists():raise SystemExit('existing package: refuse overwrite')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip();parent=subprocess.check_output(['git','rev-parse','HEAD^'],cwd=REPO,text=True).strip()
assert head=='adf0287abef0c4803962fee0df0065d8e6f3793d';assert parent=='2bedfc060a9b19019ba44aa2a56dcacb88450c3b'
inp=json.loads((ROOT/'input_manifest.json').read_text());checks=[{'path':v['path'],'same_as_input':sha(ROOT/v['path'])==v['sha256'],'same_as_current_repo':sha(ROOT/v['path'])==sha(REPO/v['path'])} for v in inp['sources']]
assert all(v['same_as_input'] and v['same_as_current_repo'] for v in checks)
old=json.loads((ROOT/'observations_r2.json').read_text());new=json.loads((ROOT/'anchor_observations_r3.json').read_text());cases=[]
for v in old+new:
 name=v['case'];d=v['detail'];c={'case':name,'raw_observed':v['current_contract_observed'],'adjudicated_contract_observed':v['current_contract_observed'],'classification':'existing_contract_control','detail_file':'observations_r2.json' if v in old else 'anchor_observations_r3.json'}
 if name.startswith('protocol_novel'):
  n=2 if 'nonempty' in name else 1;c['adjudicated_contract_observed']=d['execution']['returncode']==0 and len(d['events'])==n and d['actual_tool_count']==n and len(d['requests'])>=1 and all(q['network_request_count']==0 for q in d['requests']);c['classification']='raw_oracle_request_count_corrected_from_existing_output';c['correction']='one initial decide plus legal product-followup decides creates 3/2 requests; original exactly1 assertion is not contracted';c['actual_event_tool_request_counts']=[len(d['events']),d['actual_tool_count'],len(d['requests'])]
 if 'unknown_plan_version' in name or 'missing_plan_version' in name:
  c['classification']='P2_header_only_metadata_boundary_scope_for_root_adjudication';c['adjudicated_contract_observed']=None;c['facts']={'same_plan_digest':d['old_plan_digest']==d['new_plan_digest'],'actual_public_resume_returncode':d['resume']['returncode'],'no_new_transformation_plan_content':True,'actual_tool_entries_resume':d['consumer_entries_resume'].count('execute_atomtool_expansion'),'consumer_entries':d['consumer_entries_resume'],'note':'loader does not interpret plan_version header; valid original bundle under original task/hypothesis succeeds; not evidence of changed plan content admission'}
 if name.startswith('self_consistent_replaced_plan'):
  q=ROOT/'tables'/(name+'_mutated.json');b=json.loads(q.read_text());a=json.loads((ROOT/'tables'/(name+'_resume.json')).read_text());m=json.loads((ROOT/'inputs'/(name+'_mutation.json')).read_text());rel='results/run-plan/frozen_plan.json';c['mutated_artifact_sha256_before_after']=[b['artifacts'][rel]['sha256'],a['artifacts'][rel]['sha256']];assert c['mutated_artifact_sha256_before_after'][0]==c['mutated_artifact_sha256_before_after'][1];orig=json.loads((ROOT/'original_inputs'/(name+'_mutation.json')).read_text());c['original_R2_plan_recipe_identical']=(m['before_envelope']['payload']['plan']==orig['before_envelope']['payload']['plan'] and m['new_envelope']['payload']['plan']==orig['new_envelope']['payload']['plan']);assert c['original_R2_plan_recipe_identical'];c['root_digest']=d['root_frozen_digest'];c['replacement_plan_digest']=d['new_frozen_digest'];c['all_tables_identical']=d['unchanged_tables']
 cases.append(c)
assert len(old)==21 and all(v['current_contract_observed'] for v in old);assert len(new)==17
summary={'top_level_observations':38,'raw_true':sum(v['current_contract_observed'] for v in old+new),'raw_false':sum(not v['current_contract_observed'] for v in old+new),'adjudicated_existing_contract_controls':sum(c['adjudicated_contract_observed'] is True for c in cases),'P2_header_metadata_boundaries':sum(c['adjudicated_contract_observed'] is None for c in cases),'root_must_adjudicate_scope':True,'specialist_recommendation':'S3B-01 plan-content anchor closes; metadata header only boundary P2 (not a new plan-consumer counterexample); root owns final verdict','cases':cases};write(ROOT/'adjudicated_summary.json',summary)
schema=[]
for run in sorted((ROOT/'synthetic_runs/runs').iterdir()):
 db=run/'pollutant.sqlite'
 if not db.exists():continue
 con=sqlite3.connect(f'file:{db}?mode=ro',uri=True);con.row_factory=sqlite3.Row
 schema.append({'run_id':run.name,'meta':[dict(r) for r in con.execute('SELECT * FROM meta')],'table_names':[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]});con.close()
write(ROOT/'schema_snapshot.json',schema)
metadata={'actual_head':head,'parent':parent,'date_local':'2026-10-08','assembled_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'sqlite':sqlite3.sqlite_version,'rdkit':version('rdkit'),'command_recovery':[sys.executable,'-B',str(ROOT/'scripts/review_recovery.py')],'command_anchor':[sys.executable,'-B',str(ROOT/'scripts/review_anchor_r3.py')],'controllers_exit_codes':[0,0],'environment':{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'src')},'source_checks':checks,'public_wrappers':'workflow.runner.start_run/resume_run','worker_config_v3':str(ROOT/'absent_v3'),'worker_config_assets':str(ROOT/'absent_assets'),'network_calls':0,'external_model_calls':0,'pytest_runs':0,'interruption':None,'main_repo_existing_files_modified':False,'probe_reexecutions':0,'oracle_corrections_from_existing_output_only':2,'extra_readonly_crosscheck_mistake':{'error':'KeyError: task_key','actual_request_reference_field':'action_id','behavior_rerun':False,'original_behavior_logs_unchanged':True}};write(ROOT/'execution_metadata.json',metadata)
segments={'src/pathway_v43/pollutant/runflow.py':[(125,166),(229,390),(1328,1427),(1490,1552)],'src/pathway_v43/pollutant/search.py':[(379,399)]}
allsegs=[]
for rel,pairs in segments.items():
 ls=(ROOT/rel).read_text().splitlines()
 for a,b in pairs:allsegs.append(rel+f':{a}-{b}\n'+'\n'.join(f'{i+1:5}: {ls[i]}' for i in range(a-1,min(b,len(ls)))))
(ROOT/'source_review_lines.txt').write_text('\n\n'.join(allsegs)+'\n')
PACK.mkdir()
for d in ('src','scripts','raw_old_scripts','original_inputs','inputs','logs','tables'):shutil.copytree(ROOT/d,PACK/d)
for n in ('pyproject.toml','README.md','input_manifest.json','observations_r2.json','anchor_observations_r3.json','adjudicated_summary.json','execution_metadata.json','schema_snapshot.json','source_review_lines.txt','finalize_package.py'):shutil.copy2(ROOT/n,PACK/n)
omitted=[]
for f in sorted((ROOT/'synthetic_runs').rglob('*')):
 if not f.is_file():continue
 rel=f.relative_to(ROOT/'synthetic_runs')
 if f.name.endswith('.sqlite') or '.sqlite-' in f.name:
  omitted.append({'path':str(rel),'bytes':f.stat().st_size,'sha256':sha(f),'reason':'synthetic_SQLite_binary_omitted_complete_logical_snapshots_preserved'})
 elif f.is_relative_to(ROOT/'synthetic_runs/runs'):
  q=PACK/'artifacts_final'/f.relative_to(ROOT/'synthetic_runs/runs');q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,q)
 elif f.suffix=='.json':
  q=PACK/'barrier_receipts'/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,q)
 else:omitted.append({'path':str(rel),'bytes':f.stat().st_size,'sha256':sha(f),'reason':'ephemeral_barrier_sync_marker'})
write(PACK/'omitted_binary_inventory.json',omitted)
files=[]
for f in sorted(PACK.rglob('*')):
 if f.is_symlink():raise RuntimeError('unexpected symlink')
 if not f.is_file():continue
 if f.suffix in ('.pyc','.sqlite') or '__pycache__' in f.parts:raise RuntimeError('forbidden binary/cache')
 files.append({'path':str(f.relative_to(PACK)),'bytes':f.stat().st_size,'sha256':sha(f)})
manifest={'schema':'ppv1-independent-evidence-sha256-v1','actual_head':head,'parent':parent,'files':files};write(PACK/'manifest.json',manifest);h=sha(PACK/'manifest.json');(PACK/'manifest.sha256').write_text(h+'  manifest.json\n');(PACK/'SHA256SUMS').write_text(''.join(f"{v['sha256']}  {v['path']}\n" for v in files)+h+'  manifest.json\n')
assert all(sha(PACK/v['path'])==v['sha256'] for v in files)
print(json.dumps({'package':str(PACK),'manifest_sha256':h,'payload_files':len(files),'payload_bytes':sum(v['bytes'] for v in files),'top_level_observations':38,'adjudicated_contract_controls':summary['adjudicated_existing_contract_controls'],'P2_metadata_header_boundaries':2,'residual_P1_recommended':[],'all_payload_SHA_verified':True}))
