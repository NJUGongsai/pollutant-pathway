"""S4 confirmation public-chain probes. Run only in a fresh isolated tmp source.
No real provider, gold, questions, sealed runs, repository writes or LLM scoring.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, os, shutil, sqlite3, subprocess, sys
from pathlib import Path

def sha(b): return hashlib.sha256(b).hexdigest()
def dump(p,obj): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')

def main():
 p=argparse.ArgumentParser(); p.add_argument('--source',required=True); p.add_argument('--workspace',required=True); p.add_argument('--out',required=True); args=p.parse_args()
 source=Path(args.source).resolve(); workspace=Path(args.workspace).resolve(); out=Path(args.out).resolve(); workspace.mkdir(parents=True,exist_ok=False); out.mkdir(parents=True,exist_ok=True)
 sys.path[:0]=[str(source/'src'),str(source/'tests')]
 from test_ppv1_s4a_endpoint import spec, mineralization_evidence
 from pathway_v43.config import resolve_config
 from pathway_v43.domain.models import content_hash,canonical_json,stable_id
 from pathway_v43.workflow.runner import start_run,resume_run
 from pathway_v43.storage.run_identity import PROFILE_POLLUTANT_PATHWAY_V1
 from pathway_v43.storage.artifact_store import ArtifactStore
 from pathway_v43.pollutant.store import PollutantPathwayStore
 from pathway_v43.pollutant.search import SearchLedger,read_search_artifact
 from pathway_v43.pollutant.endpoint import read_run_endpoint
 from pathway_v43.pollutant.native_result import build_native_result,artifact_reference_index
 from pathway_v43.pollutant.native_export import export_native_result,read_native_export,list_native_exports
 from pathway_v43.pollutant.v3_projection import read_v3_projection,list_v3_projections_for_native,build_v3_projection,persist_v3_projection
 runs=workspace/'runs'; results={}
 plan={'pools':{'CCO':[spec('B','CC=O','donor-B',coproducts=['[H][H]']),spec('C','CC=O','donor-C')]},'schedule_budget':{'max_select':1},'endpoint_evidence':[mineralization_evidence()]}
 dump(out/'input_plan.json',plan)
 def start(run):
  summary=start_run(config=resolve_config(),runs_root=runs,run_id=run,smiles='CCO',max_depth=3,max_expansions=10,max_frontier_width=2,finder=object(),scripted=True,profile=PROFILE_POLLUTANT_PATHWAY_V1,ppv1_plan=plan)
  ledger=SearchLedger(PollutantPathwayStore(runs/run/'pollutant.sqlite'),ArtifactStore(runs,run),run)
  d=summary['native_export']['export_digest']; ed=runs/run/'native_export'/d[:24]
  return summary,ledger,d,ed
 def tables(ledger):
  names=[r[0] for r in ledger.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
  return {name:content_hash(sorted([{k:r[k] for k in r.keys()} for r in ledger.conn.execute('SELECT * FROM '+name)],key=canonical_json)) for name in names}
 def call(fn):
  try:
   value=fn(); return {'accepted':True,'type':type(value).__name__}
  except Exception as e:
   return {'accepted':False,'exception':type(e).__name__,'message':str(e),'detail':getattr(e,'detail',{})}
 def recordfiles(dst,paths):
  dst.mkdir(parents=True,exist_ok=True)
  return {name:{'sha256':sha(path.read_bytes()),'path':str(path)} for name,path in paths.items() if path.is_file()}
 # Public chain and exact file determinism. No custom construction of chemistry.
 summary,l,d,ed=start('public-chain'); before=tables(l); verified=read_native_export(l,runs/'public-chain',d); native=build_native_result(l,endpoint_record=read_run_endpoint(l,'public-chain'))
 payload0=(ed/'payload.json').read_bytes(); manifest0=(ed/'manifest.json').read_bytes(); repeat=export_native_result(l,native,runs/'public-chain')
 code="""import json,sys\nfrom pathlib import Path\nfrom pathway_v43.storage.artifact_store import ArtifactStore\nfrom pathway_v43.pollutant.store import PollutantPathwayStore\nfrom pathway_v43.pollutant.search import SearchLedger\nfrom pathway_v43.pollutant.endpoint import read_run_endpoint\nfrom pathway_v43.pollutant.native_result import build_native_result\nfrom pathway_v43.pollutant.native_export import export_native_result\nroot=Path(sys.argv[1]);run=sys.argv[2]\nledger=SearchLedger(PollutantPathwayStore(root/run/'pollutant.sqlite'),ArtifactStore(root,run),run)\nnative=build_native_result(ledger,endpoint_record=read_run_endpoint(ledger,run))\nprint(json.dumps(export_native_result(ledger,native,root/run),sort_keys=True))\n"""
 dump(out/'subprocess_input.json',{'code':code,'argv':[sys.executable,'-B','-c','<code>',str(runs),'public-chain']})
 proc=subprocess.run([sys.executable,'-B','-c',code,str(runs),'public-chain'],cwd=workspace,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(source/'src')},capture_output=True,text=True)
 (out/'subprocess.stdout.txt').write_text(proc.stdout); (out/'subprocess.stderr.txt').write_text(proc.stderr); assert proc.returncode==0
 sub=json.loads(proc.stdout); projection=read_v3_projection(runs/'public-chain',summary['v3_projection']['projection_digest'])
 native_outcome_keys=sorted((x['task_key'],x['action_id']) for x in native['expansion_outcomes'])
 existing_outcome_keys=[];both_entries=[]
 for action in ledger_actions(l):
  candidates=[action['task_key'],stable_id('soutc',action['action_id'])]
  both_entries.append({'action_id':action['action_id'],'action_kind':action['action_kind'],'candidate_keys':candidates})
  for key in candidates:
   env=read_search_artifact(l.artifact_store,key,'expansion_outcome')
   if env is not None: existing_outcome_keys.append((key,action['action_id']))
 aggregation_complete = sorted(existing_outcome_keys)==native_outcome_keys
 assert any(key.startswith('soutc:') or key.startswith('soutc_') for key,_ in existing_outcome_keys),existing_outcome_keys
 assert repeat['export_digest']==sub['export_digest']==d
 assert repeat['created']==sub['created']=={'payload':False,'manifest':False}
 assert (ed/'payload.json').read_bytes()==payload0 and (ed/'manifest.json').read_bytes()==manifest0
 assert tables(l)==before
 assert verified['payload']==native and projection['lossy_projection'] is True
 results['positive_public_chain']={'summary':summary,'same_process':repeat,'subprocess':sub,'payload_sha256':sha(payload0),'manifest_sha256':sha(manifest0),'table_hash_before':before,'table_hash_after':tables(l),'both_key_entries':both_entries,'existing_outcome_keys':existing_outcome_keys,'aggregated_outcome_keys':native_outcome_keys,'aggregation_complete':aggregation_complete,'missing_outcomes':[{'task_key':key,'action_id':aid,'artifact':read_search_artifact(l.artifact_store,key,'expansion_outcome')} for key,aid in existing_outcome_keys if (key,aid) not in native_outcome_keys],'projection':projection,'reverse_lookup':list_v3_projections_for_native(runs/'public-chain',native_export_digest=d),'network_requests':l.conn.execute('SELECT COALESCE(SUM(network_request_count),0) FROM model_requests').fetchone()[0]}
 # Three independently reset parseable manifest mutations, original digest left unchanged.
 s,l,d,ed=start('manifest-field'); orig=(ed/'manifest.json').read_bytes(); orig_obj=json.loads(orig); before=tables(l)
 cases={
  'run_id_foreign':lambda m:m.update(run_id='FOREIGN_RUN'),
  'contract_version_foreign':lambda m:m['contract_versions'].update(profile='ppv1-profile-CORRUPT'),
  'policy_body_foreign':lambda m:m['export_policy'].update(version='ppv1-native-export-policy-CORRUPT'),
  'all_artifact_references_omitted':lambda m:m.update(artifact_references={}),
 }
 observed=[]
 for name,mutate in cases.items():
  m=copy.deepcopy(orig_obj); mutate(m); changed=(canonical_json(m)+'\n').encode(); (ed/'manifest.json').write_bytes(changed)
  before_call=sha((ed/'manifest.json').read_bytes()); response=call(lambda:read_native_export(l,runs/'manifest-field',d))
  recomputed=content_hash({k:v for k,v in m.items() if k!='export_digest'})
  observed.append({'case':name,'requested_digest':d,'manifest_declared_digest':m['export_digest'],'actual_core_digest':recomputed,'core_digest_matches_declared':recomputed==d,'response':response,'modified_manifest_sha256':before_call,'preserved':sha((ed/'manifest.json').read_bytes())==before_call,'tables_unchanged':tables(l)==before})
  dump(out/'manifest_mutations'/f'{name}.json',m); (ed/'manifest.json').write_bytes(orig)
 results['manifest_mutations']=observed
 results['manifest_restore_positive']=call(lambda:read_native_export(l,runs/'manifest-field',d))
 # Omit all dependency refs and correctly recompute export identity. Corrupt only one report artifact; DB/native artifact untouched.
 s,l,d,ed=start('reference-omission'); before=tables(l); m=json.loads((ed/'manifest.json').read_bytes()); original_refs=copy.deepcopy(m['artifact_references'])
 report_key=next(k for k in original_refs if k.endswith('/production_report')); task,name=report_key.rsplit('/',1); reportpath=runs/'reference-omission'/'results'/task/(name+'.json'); raw=reportpath.read_bytes(); env=json.loads(raw); env['payload']['codex_corrupt_dependency']='bad-authority-input'; reportpath.write_text(canonical_json(env)+'\n')
 damaged_sha=sha(reportpath.read_bytes()); original_response=call(lambda:read_native_export(l,runs/'reference-omission',d))
 m['artifact_references']={}; m.pop('export_digest'); fake_d=content_hash(m); m['export_digest']=fake_d; fake_dir=runs/'reference-omission'/'native_export'/fake_d[:24];fake_dir.mkdir();shutil.copy2(ed/'payload.json',fake_dir/'payload.json'); (fake_dir/'manifest.json').write_text(canonical_json(m)+'\n')
 fake_response=call(lambda:read_native_export(l,runs/'reference-omission',fake_d))
 results['necessary_reference_omission']={'original_export_digest':d,'original_response':original_response,'fake_export_digest':fake_d,'fake_response':fake_response,'removed_refs':original_refs,'corrupted_report_key':report_key,'corrupted_report_sha256':damaged_sha,'corrupted_report_preserved':sha(reportpath.read_bytes())==damaged_sha,'tables_unchanged':tables(l)==before,'payload_bytes_unchanged':(fake_dir/'payload.json').read_bytes()==(ed/'payload.json').read_bytes()}
 dump(out/'reference_omission'/'fake_manifest.json',m);dump(out/'reference_omission'/'corrupt_production_report.json',env)
 reportpath.write_bytes(raw);results['dependency_restore_positive']=call(lambda:read_native_export(l,runs/'reference-omission',d))
 # Public adapter receives forged self-consistent object that is not the anchored native result.
 s,l,d,ed=start('projection-binding');before=tables(l);native=read_native_export(l,runs/'projection-binding',d)['payload']; fake_native=copy.deepcopy(native); fake_native['deferred_entries']=[];fake_native['events']=[];fake_native.pop('content_digest');fake_native['content_digest']=content_hash(fake_native)
 proj=build_v3_projection(l,fake_native,native_export=s['native_export'],run_dir=runs/'projection-binding');persist=persist_v3_projection(runs/'projection-binding',proj);response=call(lambda:read_v3_projection(runs/'projection-binding',persist['projection_digest']))
 results['projection_binding']={'response':response,'source_has_events':len(native['events']),'projection_steps':len(proj['route']['steps']),'source_deferred_count':len(native['deferred_entries']),'projection_deferred_count':proj['unprojectable_summaries'].get('deferred_entry_count'),'native_reference_digest_matches_real':proj['native_reference']['native_result_content_digest']==native['content_digest'],'projection_native_reference':proj['native_reference'],'real_content_digest':native['content_digest'],'tables_unchanged':tables(l)==before}
 dump(out/'projection_binding'/'forged_projection.json',proj)
 dump(out/'results.json',results)
 print(json.dumps({'positive_public_chain':True,'focus_suite':'separate 18-pass JUnit','manifest_mutations':observed,'necessary_reference_omission':results['necessary_reference_omission'],'projection_binding':results['projection_binding']},ensure_ascii=False,indent=2))

def ledger_actions(l):
 return [{k:r[k] for k in r.keys()} for r in l.conn.execute('SELECT action_id,action_kind,task_key FROM search_actions ORDER BY action_id')]
if __name__=='__main__':main()
