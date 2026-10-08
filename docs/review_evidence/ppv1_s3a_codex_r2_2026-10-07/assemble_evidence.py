#!/usr/bin/env python3
"""Archive only manifest-listed immutable evidence. Never execute probes or open databases."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,os,shutil,time
ROOT=Path(__file__).resolve().parent
PACKS=[('execution_specialist',Path('/private/tmp/ppv1_s3a_r2_execution_review_MxKd0B/package'),'artifacts'),('authority_specialist',Path('/private/tmp/ppv1_s3a_r2_authority_0561kdd4'),'attachments'),('budget_request_specialist',Path('/private/tmp/ppv1_s3a_r2_budget_resumed_0rxegzu0/package'),'files')]
ap=argparse.ArgumentParser();ap.add_argument('--preserve-listed-synthetic-db',action='store_true');a=ap.parse_args();stage=ROOT/'evidence_stage';stage.mkdir(exist_ok=True)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def norm(name):
 p=PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts:raise ValueError('unsafe manifest path:'+name)
 return str(p)
def parse_sha(p):
 out={}
 for line in p.read_text().splitlines():
  if not line.strip():continue
  h,name=line.split(maxsplit=1);name=norm(name.lstrip('*'))
  if name in out and out[name]!=h:raise ValueError('conflicting SHA entry:'+name)
  out[name]=h
 return out
reports=[]
for label,source,key in PACKS:
 t=time.monotonic();manifest=json.loads((source/'manifest.json').read_text());payload=manifest[key];mapping={x['path']:x['sha256'] for x in payload} if isinstance(payload,list) else dict(payload);mapping={norm(k):v for k,v in mapping.items()};sha=parse_sha(source/'SHA256SUMS');roots=['manifest.json','SHA256SUMS']+(['manifest.sha256'] if (source/'manifest.sha256').exists() else []);selected=sorted(set(mapping)|set(roots));issues=[];symlinks=[];listed_db=[];listed_cache=[]
 for name in selected:
  p=source/name
  for i in range(1,len(PurePosixPath(name).parts)+1):
   q=source/Path(*PurePosixPath(name).parts[:i])
   if q.is_symlink():symlinks.append(str(q.relative_to(source)))
  if not p.is_file():issues.append({'path':name,'issue':'missing_or_nonfile'});continue
  actual=digest(p)
  if name in mapping and actual!=mapping[name]:issues.append({'path':name,'issue':'manifest_sha_mismatch','actual':actual,'expected':mapping[name]})
  if name in sha and actual!=sha[name]:issues.append({'path':name,'issue':'SHA256SUMS_mismatch','actual':actual,'expected':sha[name]})
  if p.suffix in ['.sqlite','.sqlite3','.db'] or p.name.endswith(('-wal','-shm','-journal')):listed_db.append(name)
  if p.suffix=='.pyc' or any(n in ['__pycache__','.pytest_cache'] for n in PurePosixPath(name).parts):listed_cache.append(name)
 for name in sha:
  if name not in selected:issues.append({'path':name,'issue':'SHA_entry_not_in_manifest_or_root_list'})
  elif not (source/name).is_file():issues.append({'path':name,'issue':'SHA_entry_file_missing'})
 if source.joinpath('manifest.sha256').exists():
  for name,expected in parse_sha(source/'manifest.sha256').items():
   if name!='manifest.json' or digest(source/name)!=expected:issues.append({'path':name,'issue':'manifest_sha_root_mismatch'})
 # Filesystem-name inventory only; excluded files are never read, copied, or opened as SQLite.
 unlisted_cache=[];unlisted_symlinks=[];unlisted_count=0
 for d,dirs,files in os.walk(source,followlinks=False):
  for name in dirs+files:
   p=Path(d)/name;rel=str(p.relative_to(source))
   if p.is_symlink() and rel not in selected:unlisted_symlinks.append(rel)
   if (name in ['__pycache__','.pytest_cache'] or p.suffix=='.pyc') and rel not in selected:unlisted_cache.append(rel)
   if p.is_file() and rel not in selected:unlisted_count+=1
 can_copy=not issues and not symlinks and not listed_cache and not unlisted_cache and (not listed_db or a.preserve_listed_synthetic_db)
 record={'source':str(source),'destination':str(stage/label),'manifest_payload_count':len(mapping),'root_control_files':roots,'selected_file_count':len(selected),'selected_bytes':sum((source/n).stat().st_size for n in selected if (source/n).is_file()),'manifest_sha256':digest(source/'manifest.json'),'SHA256SUMS_sha256':digest(source/'SHA256SUMS'),'sha_entry_count':len(sha),'precopy_hash_issues':issues,'selected_symlinks':sorted(set(symlinks)),'listed_db_files':listed_db,'listed_cache_files':listed_cache,'unlisted_cache_names':unlisted_cache,'unlisted_symlink_names':unlisted_symlinks,'unlisted_files_not_copied_count':unlisted_count,'db_policy':'listed synthetic databases preserved by parent instruction' if listed_db and a.preserve_listed_synthetic_db else 'listed DB copying pending parent direction' if listed_db else 'none listed','copied':False}
 if can_copy:
  dest=stage/label
  if dest.exists():
   existing=sorted(str(x.relative_to(dest)) for x in dest.rglob('*') if x.is_file())
   if existing!=selected:raise ValueError('Existing destination differs from approved exact selected list:'+str(dest))
  else:dest.mkdir()
  for name in selected:
   p=dest/name;p.parent.mkdir(parents=True,exist_ok=True)
   if p.exists():
    if digest(p)!=digest(source/name):raise ValueError('Existing stage file differs:'+str(p))
   else:shutil.copy2(source/name,p)
  after=[]
  for name in selected:
   p=dest/name
   if p.is_symlink() or digest(p)!=digest(source/name):after.append({'path':name,'issue':'copied_file_identity_mismatch'})
  after_sha=parse_sha(dest/'SHA256SUMS')
  for name,expected in after_sha.items():
   if digest(dest/name)!=expected:after.append({'path':name,'issue':'copied_nested_SHA_mismatch'})
  record.update({'copied':True,'postcopy_issues':after,'postcopy_all_original_manifest_and_SHA_verified':not after,'copied_file_count':len(selected),'copied_bytes':sum((dest/n).stat().st_size for n in selected)})
 record['elapsed_s']=time.monotonic()-t;reports.append(record)
result={'assembly_script':str(Path(__file__)),'stage':str(stage),'probe_execution_count':0,'database_open_count':0,'source_packages_modified':False,'copy_scope':'original manifest payload files plus root manifest/SHA control files only','packages':reports,'all_copied':all(r['copied'] for r in reports),'no_hash_or_symlink_or_cache_issues':all(not r['precopy_hash_issues'] and not r['selected_symlinks'] and not r['listed_cache_files'] and not r['unlisted_cache_names'] for r in reports)}
(ROOT/'package_assembly.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'all_copied':result['all_copied'],'packages':[{'name':Path(r['destination']).name,'copied':r['copied'],'files':r['selected_file_count'],'bytes':r['selected_bytes'],'sha_issues':len(r['precopy_hash_issues']),'symlinks':len(r['selected_symlinks']),'listed_db':len(r['listed_db_files']),'unlisted_cache':len(r['unlisted_cache_names'])} for r in reports]},sort_keys=True))
