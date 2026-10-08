#!/usr/bin/env python3
"""Freeze existing execution artifacts; no suite/probe execution."""
import hashlib,json,shutil,tarfile
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];PACK=OUT/'package'
if PACK.exists():raise RuntimeError('package already exists')
PACK.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def cp(p,d):
    if p.is_symlink():raise RuntimeError('symlink forbidden')
    d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d)
    if sha(p)!=sha(d):raise RuntimeError('copy hash mismatch')
# Explicit all prior execution metadata and read-only observations.
for p in sorted(OUT.iterdir()):
    if p.is_file() and p.suffix in ['.json','.txt','.md']:cp(p,PACK/p.name)
folders=['scripts','allowlists','current_source','baseline_source','ppv1_full','baseline_updated_existing','baseline_new_collection','current_runtime','baseline_runtime','worktree_create','worktree_sparse_init','worktree_sparse_set','worktree_checkout','worktree_remove','g01_controller','captured_pytest_outputs']
omitted=[]
for folder in folders:
    for p in sorted((OUT/folder).rglob('*')):
        if p.is_symlink():continue
        if not p.is_file():continue
        if '__pycache__' in p.parts or p.suffix in ['.pyc','.pyo']:raise RuntimeError('unexpected cache')
        if p.suffix in ['.sqlite','.db'] or p.name.endswith(('-wal','-shm')):
            omitted.append({'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)});continue
        cp(p,PACK/p.relative_to(OUT))
# Safe controller's output metadata only. Source bytes explicitly packed from its 286-member allowlist.
for p in sorted((OUT/'g01').iterdir()):
    if p.is_file() and p.suffix in ['.json','.txt','.xml']:cp(p,PACK/'g01'/p.name)
inputs=json.loads((OUT/'g01/input_sha256.json').read_text());verified={}
with tarfile.open(PACK/'g01_inputs.tar.gz','w:gz') as tar:
    for name,digest in sorted(inputs.items()):
        p=OUT/'g01'/name
        if p.is_symlink() or sha(p)!=digest:raise RuntimeError('unsafe/mismatched safe G01 member')
        info=tarfile.TarInfo(name);info.size=p.stat().st_size;info.mode=0o644;info.mtime=0
        with p.open('rb') as f:tar.addfile(info,f)
with tarfile.open(PACK/'g01_inputs.tar.gz','r:gz') as tar:
    for member in tar.getmembers():
        if not member.isfile() or member.name not in inputs:raise RuntimeError('unexpected archive member')
        verified[member.name]=hashlib.sha256(tar.extractfile(member).read()).hexdigest()
if verified!=inputs:raise RuntimeError('G01 archive mismatch')
write(PACK/'g01_archive_integrity.json',{'member_count':len(verified),'members':verified,'all_members_match':True,'all_regular_files':True,'no_extraction_used':True})
obs=json.loads((OUT/'g01/pytest_observations.json').read_text())
write(PACK/'g01_exclusions_detail.json',{'skips':obs['skip_reports'],'deselected_nodeids':obs['deselected_nodeids'],'skipped_count':len(obs['skip_reports']),'deselected_count':len(obs['deselected_nodeids']),'category_counts':{'real_evaluation_missing':5,'v4_missing':1,'phase_d_derived_metadata_missing':2,'slow_deselected':16,'explicit_export_deselected':1},'selected_nodeids_is_collection_observation_not_completed_execution':True})
write(PACK/'omitted_binary_artifacts.json',{'reason':'runtime synthetic SQLite binaries omitted, tables and original SHA retained','files':omitted})
files=[]
for p in sorted(PACK.rglob('*')):
    if p.is_symlink():raise RuntimeError('package symlink')
    if p.is_file():
        if '__pycache__' in p.parts or p.suffix in ['.sqlite','.db','.pyc','.pyo']:raise RuntimeError('package binary/cache')
        files.append({'path':p.relative_to(PACK).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
write(PACK/'manifest.json',{'actual_HEAD':'c1211183c0874b12c5b5461845d3c61f0a84719c','parent':'b7f2bba02ca49edd0a45a13bc9b8434909d99175','scope':'independent S3b engineering execution specialist','files':files,'total_files':len(files),'total_bytes':sum(r['bytes'] for r in files),'self_excluded':['manifest.json','SHA256SUMS','manifest.sha256']})
manifest_sha=sha(PACK/'manifest.json')
(PACK/'SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['path']+'\n' for r in files))
(PACK/'manifest.sha256').write_text(manifest_sha+'  manifest.json\n')
print(json.dumps({'package':str(PACK),'payload_files':len(files),'physical_files':len(files)+3,'payload_bytes':sum(r['bytes'] for r in files),'manifest_sha256':manifest_sha,'g01_member_count':len(verified)},ensure_ascii=False))
