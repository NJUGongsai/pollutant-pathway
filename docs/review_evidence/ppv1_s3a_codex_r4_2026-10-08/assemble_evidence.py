#!/usr/bin/env python3
"""Byte copy only manifest-declared frozen attachments. No probe/DB execution."""
from pathlib import Path,PurePosixPath
import argparse,datetime,hashlib,json,shutil,tarfile
ROOT=Path(__file__).resolve().parent;STAGE=ROOT/'evidence_stage';SIDECARS=['manifest.json','SHA256SUMS','manifest.sha256']
SOURCES={
 'authority_specialist':(Path('/private/tmp/ppv1_s3a_r4_authority_inolg6_c/package'),'138bd42e4028c7b8394285c70420a870671431bfe5f9c7f72724ad36e4ef103c'),
 'budget_request_specialist':(Path('/private/tmp/ppv1_s3a_r4_budget_etb34fix/package'),'50267c2b370b5d4bb13b150ba5884b1cc2cc4eb2a0fca6d8b3e3a50cfc46db95')}
ap=argparse.ArgumentParser();ap.add_argument('--execution-package');ap.add_argument('--execution-manifest-sha256');a=ap.parse_args()
if a.execution_package:
 assert a.execution_manifest_sha256,'Need the pinned execution manifest hash'
 SOURCES['execution_specialist']=(Path(a.execution_package),a.execution_manifest_sha256)
STAGE.mkdir(exist_ok=True);records={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safe_rel(rel):
 p=PurePosixPath(rel);assert not p.is_absolute() and '..' not in p.parts and str(p)==rel and rel,rel
 forbidden={'__pycache__','.pytest_cache','.git'}
 assert not forbidden.intersection(p.parts) and not p.name.endswith(('.pyc','.sqlite','.sqlite-wal','.sqlite-shm','.db','.db-wal','.db-shm')),rel
 return p

def tar_audit(p):
 # Safe reading only; never extract or open member content outside this tar.
 listed=[]
 with tarfile.open(p,'r:*') as tf:
  for m in tf.getmembers():
   rel=str(PurePosixPath(m.name));safe_rel(rel)
   assert not (m.issym() or m.islnk() or m.isdev() or m.isfifo()),m.name
   if not m.isfile():
    assert m.isdir(),m.name;continue
   f=tf.extractfile(m);assert f is not None,m.name
   h=hashlib.sha256();size=0
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b);size+=len(b)
   assert size==m.size,m.name;listed.append({'path':m.name,'bytes':size,'sha256':h.hexdigest()})
 return {'path':p.name,'sha256':sha(p),'file_count':len(listed),'members':listed,'no_extraction':True}

for label,(src,expected_sha) in SOURCES.items():
 assert src.is_dir() and not src.is_symlink(),src
 mp=src/'manifest.json';assert sha(mp)==expected_sha,(label,'manifest SHA')
 d=json.loads(mp.read_text())
 if 'files' in d:
  f=d['files'];files=[dict(v,path=k) for k,v in f.items()] if isinstance(f,dict) else f
 else:
  files=[{'path':k,'sha256':h,'bytes':(src/k).stat().st_size} for k,h in d['sha256'].items()]
  assert len(files)==d['attachment_count'] and sum(x['bytes'] for x in files)==d['attachment_bytes'],(label,'declared attachment count/bytes')
 sidecars=[n for n in SIDECARS if (src/n).exists()]
 assert 'manifest.json' in sidecars and 'SHA256SUMS' in sidecars,(label,'required sidecars')
 assert isinstance(files,list) and files,label
 dst=STAGE/label;exists=dst.exists()
 if not exists:dst.mkdir()
 expected_names={x['path'] for x in files}|set(sidecars);assert len(expected_names)==len(files)+len(sidecars),(label,'sidecar duplicate')
 byte_total=0
 for entry in files:
  rel=entry['path'];safe_rel(rel);sp=src/rel;dp=dst/rel
  assert sp.is_file() and not sp.is_symlink() and all(not q.is_symlink() for q in [sp,*sp.parents] if q!=Path('/')),rel
  assert sha(sp)==entry['sha256'] and sp.stat().st_size==entry['bytes'],(label,rel,'source hash/size')
  if not exists:dp.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(sp,dp)
  assert dp.is_file() and not dp.is_symlink() and sha(dp)==entry['sha256'] and dp.stat().st_size==entry['bytes'],(label,rel,'copied hash/size')
  byte_total+=entry['bytes']
 for rel in sidecars:
  sp=src/rel;dp=dst/rel;assert sp.is_file() and not sp.is_symlink(),sp
  if not exists:shutil.copy2(sp,dp)
  assert sp.read_bytes()==dp.read_bytes(),(label,rel,'sidecar bytes')
 actual_names={str(p.relative_to(dst)) for p in dst.rglob('*') if p.is_file()};assert actual_names==expected_names,(label,'extra/missing staged attachments')
 assert not any(p.is_symlink() for p in dst.rglob('*')),(label,'staged symlink')
 rec={'source':str(src),'stage':str(dst),'manifest_sha256':expected_sha,'attachments':len(files),'payload_bytes':byte_total,'sidecars':len(sidecars),'source_sha256_verified':True,'copied_sha256_verified':True,'no_unlisted_files_copied':True,'no_db_reads':True,'no_hash_or_symlink_or_cache_issues':True}
 tars=[p for p in dst.rglob('*') if p.is_file() and p.name.endswith(('.tar.gz','.tgz','.tar'))]
 if tars:
  rec['tar_member_audits']=[tar_audit(p) for p in tars]
  if label=='execution_specialist':
   manifest_inputs=json.loads((dst/'g01/input_sha256.json').read_text())
   archived_original_verification=json.loads((dst/'g01_archive_members_verified.json').read_text())
   after_inputs=json.loads((dst/'g01_input_integrity_after.json').read_text())['copy_hashes_after']
   assert len(manifest_inputs)==277 and manifest_inputs==after_inputs==archived_original_verification['members'],(label,'277 before/after manifest')
   audits=rec['tar_member_audits'];assert len(audits)==1 and audits[0]['path']=='g01_inputs.tar.gz',(label,'one pinned input archive')
   computed={x['path']:x['sha256'] for x in audits[0]['members']}
   assert len(computed)==277 and computed==manifest_inputs,(label,'tar member SHA/input manifest mismatch')
   rec['g01_tar_277_member_hashes_match_before_after_manifest']=True
 records[label]=rec
# Any already staged execution package can be verified only once pinned source provided.
complete=set(records)=={'authority_specialist','budget_request_specialist','execution_specialist'}
result={'stage_root':str(STAGE),'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'all_copied':complete,'no_hash_or_symlink_or_cache_issues':all(x['no_hash_or_symlink_or_cache_issues'] for x in records.values()),'no_probe_execution':True,'no_db_reads':True,'packages':records}
(ROOT/'package_assembly.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'all_copied':complete,'packages':{k:{'attachments':v['attachments'],'payload_bytes':v['payload_bytes'],'manifest_sha256':v['manifest_sha256']} for k,v in records.items()}},ensure_ascii=False,sort_keys=True))
