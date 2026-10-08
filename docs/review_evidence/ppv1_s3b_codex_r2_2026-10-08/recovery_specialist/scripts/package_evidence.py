#!/usr/bin/env python3
"""Only archive current specialist scratch into a NEW package; no probe rerun."""
from pathlib import Path
import hashlib,json,shutil,sys,subprocess
root=Path(__file__).resolve().parents[1];package=root/'package'
if package.exists():raise SystemExit('package already exists, refuse overwrite')
package.mkdir()
for rel in ['src','scripts','inputs','logs','tables']:
 shutil.copytree(root/rel,package/rel,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
for name in ['pyproject.toml','README.md','SPECIALIST_REVIEW.md','input_manifest.json','execution_metadata.json','observations.json','supplemental_observations.json','adjudicated_summary.json','zero_depth_existing_extraction.json','source_review_lines.txt']:
 shutil.copy2(root/name,package/name)
omitted=[]
for path in sorted((root/'synthetic_runs').rglob('*')):
 if not path.is_file():continue
 rel=path.relative_to(root/'synthetic_runs')
 if path.name.endswith('.sqlite') or '.sqlite-' in path.name:
  omitted.append({'path':str(path.relative_to(root)),'kind':'synthetic_sqlite_binary','bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 elif path.name=='run_identity.json' or 'results' in rel.parts:
  target=package/'artifacts_final'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
 elif path.suffix=='.json':
  target=package/'runtime_barrier_receipts'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
 else:
  omitted.append({'path':str(path.relative_to(root)),'kind':'synthetic_barrier_sync_marker','bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(package/'omitted_binary_inventory.json').write_text(json.dumps(omitted,ensure_ascii=False,indent=2,sort_keys=True))
files=[]
for path in sorted(package.rglob('*')):
 if path.is_symlink():raise RuntimeError('unexpected symlink '+str(path))
 if path.is_file():
  if path.suffix in ('.pyc','.sqlite') or '__pycache__' in path.parts:raise RuntimeError('unexpected cache/db '+str(path))
  files.append({'path':str(path.relative_to(package)),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
manifest={'kind':'ppv1_s3b_queue_recovery_independent_codex_evidence','actual_head':'c1211183c0874b12c5b5461845d3c61f0a84719c','parent':'b7f2bba02ca49edd0a45a13bc9b8434909d99175','date':'2026-10-08','files':files,'payload_file_count':len(files),'payload_bytes':sum(f['bytes'] for f in files),'external_calls':0,'repo_writes':0,'sqlite_binary_omitted_count':sum(x['kind']=='synthetic_sqlite_binary' for x in omitted),'control_error_honestly_preserved':True}
(package/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+'\n');mh=hashlib.sha256((package/'manifest.json').read_bytes()).hexdigest();(package/'manifest.sha256').write_text(mh+'  manifest.json\n');(package/'SHA256SUMS').write_text(''.join(f["sha256"]+'  '+f['path']+'\n' for f in files)+mh+'  manifest.json\n')
print(json.dumps({'package':str(package),'payload_files':len(files),'total_files':len(files)+3,'manifest_sha256':mh,'files_structure':'list(path,bytes,sha256)','payload_bytes':manifest['payload_bytes'],'omitted_sqlite_count':manifest['sqlite_binary_omitted_count']},ensure_ascii=False,indent=2))
