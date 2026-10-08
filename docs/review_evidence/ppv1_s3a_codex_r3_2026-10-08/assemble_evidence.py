#!/usr/bin/env python3
"""Pure manifest-listed copy and byte verification. Does not run probes or write repository."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,shutil,tarfile,datetime
ROOT=Path(__file__).resolve().parent
STAGE=ROOT/'evidence_stage'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def norm(manifest):
 source=manifest.get('files',manifest.get('attachments'))
 if isinstance(source,dict):return {k:({'sha256':v} if isinstance(v,str) else dict(v)) for k,v in source.items()}
 if isinstance(source,list):
  out={}
  for v in source:
   k=v.get('path',v.get('name',v.get('relative_path')))
   assert k and k not in out,(k,'duplicate/no path')
   out[k]=dict(v)
  return out
 raise AssertionError('unsupported manifest file collection')
def safe_rel(name):
 p=PurePosixPath(name)
 assert name and not p.is_absolute() and '..' not in p.parts and name==str(p),(name,'unsafe relative name')
 assert not any(v in ['__pycache__','.pytest_cache'] for v in p.parts) and not name.endswith('.pyc'),(name,'cache disallowed')
 return p
ap=argparse.ArgumentParser();ap.add_argument('--name',required=True);ap.add_argument('--source',required=True);ap.add_argument('--expected-manifest',required=True);a=ap.parse_args();src=Path(a.source);assert src.is_dir() and not src.is_symlink()
assert digest(src/'manifest.json')==a.expected_manifest
m=json.loads((src/'manifest.json').read_text());files=norm(m)
assert a.name in ['execution_specialist','budget_request_specialist','authority_specialist']
# Validate original payload and sidecar claims before any copy.
for name,v in files.items():
 rel=safe_rel(name);p=src/str(rel)
 assert p.is_file() and not p.is_symlink(),(name,'non-file/link')
 assert digest(p)==v['sha256'],(name,'source sha mismatch')
 if 'bytes' in v:assert p.stat().st_size==v['bytes'],(name,'size mismatch')
 elif 'size_bytes' in v:assert p.stat().st_size==v['size_bytes'],(name,'size mismatch')
sidecars=[n for n in ['manifest.json','manifest.sha256','SHA256SUMS'] if (src/n).is_file()]
for name in sidecars:assert not (src/name).is_symlink()
if (src/'manifest.sha256').is_file():assert (src/'manifest.sha256').read_text().split()[0]==a.expected_manifest
if (src/'SHA256SUMS').is_file():
 for line in (src/'SHA256SUMS').read_text().splitlines():
  if not line.strip():continue
  h,name=line.split(None,1);name=name.lstrip('* ');safe_rel(name);p=src/name
  assert p.is_file() and not p.is_symlink() and digest(p)==h,(name,'SHA256SUMS mismatch')
archive_checks=[]
for name in files:
 if not name.endswith('.tar.gz'):continue
 expected=json.loads((src/'g01/input_sha256.json').read_text()) if name=='g01_inputs.tar.gz' else None
 seen={}
 with tarfile.open(src/name,'r:gz') as t:
  for member in t:
   safe_rel(member.name);assert member.isfile() and not member.issym() and not member.islnk(),(member.name,'archive nonordinary member')
   assert member.name not in seen,(member.name,'duplicate tar member')
   assert not member.name.endswith(('.sqlite','.sqlite3','.db','.pyc')),(member.name,'archive DB/cache disallowed')
   f=t.extractfile(member);h=hashlib.sha256()
   for b in iter(lambda:f.read(1<<20),b''):h.update(b)
   seen[member.name]=h.hexdigest()
 assert expected is not None and seen==expected,(name,'archive inner hashes not exact white list')
 archive_checks.append({'archive':name,'members':len(seen),'all_white_list_hashes_match':True,'safe_file_members_only':True,'no_archive_extraction':True})
STAGE.mkdir(exist_ok=True);dst=STAGE/a.name;dst.mkdir(exist_ok=False)
for name in sorted(set(files)|set(sidecars)):
 p=src/name;q=dst/name;q.parent.mkdir(parents=True,exist_ok=True)
 with p.open('rb') as f,q.open('xb') as g:shutil.copyfileobj(f,g,1<<20)
 assert digest(q)==digest(p),(name,'copied bytes differ')
assert {str(p.relative_to(dst)) for p in dst.rglob('*') if p.is_file()}==set(files)|set(sidecars)
assert not any(p.is_symlink() for p in dst.rglob('*'))
listed_databases=[n for n in files if n.endswith(('.sqlite','.sqlite3','.db'))]
record={'specialist':a.name,'original_package':str(src),'destination':str(dst),'manifest_sha256':a.expected_manifest,'manifest_format':type(m.get('files',m.get('attachments'))).__name__,'payload_files':len(files),'payload_bytes':sum((src/n).stat().st_size for n in files),'root_sidecars':sidecars,'total_copied_files':len(set(files)|set(sidecars)),'total_copied_bytes':sum((dst/n).stat().st_size for n in set(files)|set(sidecars)),'sha256_before_after_all_match':True,'no_links_or_cache':True,'unlisted_files_copied':0,'listed_database_files':listed_databases,'archive_checks':archive_checks}
log=ROOT/'package_assembly.json'
records=json.loads(log.read_text()) if log.exists() else {'operation':'pure byte copy; no execution or repository writes','stage':str(STAGE),'packages':{}}
assert a.name not in records['packages']
records['packages'][a.name]=record;records['all_copied']=set(records['packages'])=={'execution_specialist','budget_request_specialist','authority_specialist'};records['no_hash_or_symlink_or_cache_issues']=all(v['sha256_before_after_all_match'] and v['no_links_or_cache'] and v['unlisted_files_copied']==0 for v in records['packages'].values());records['updated_UTC']=datetime.datetime.now(datetime.timezone.utc).isoformat();log.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n');print(json.dumps(record,ensure_ascii=False,sort_keys=True))
