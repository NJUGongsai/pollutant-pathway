#!/usr/bin/env python3
"""Read-only hashes of stage snapshots and explicitly allowlisted G01 archive; no extraction."""
from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parent;STAGE=ROOT/'evidence_stage'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
out={}
for label,prefix,file in [('execution_specialist','sources/','input_hashes.json'),('authority_specialist','','input_hashes.json'),('budget_request_specialist','','evidence/input_snapshot.json')]:
 p=STAGE/label;data=json.loads((p/file).read_text());entries={v['path']:v['sha256'] for v in data['inputs']} if label=='budget_request_specialist' else data;missing=[];bad=[];verified=0
 for name,expected in entries.items():
  path=PurePosixPath(name)
  if path.is_absolute() or '..' in path.parts:missing.append({'name':name,'reason':'not a safe package-relative reference'});continue
  target=p/(prefix+str(path))
  if not target.is_file():missing.append({'name':name,'package_candidate':str(target)});continue
  actual=digest(target)
  if actual!=expected:bad.append({'name':name,'expected':expected,'actual':actual})
  else:verified+=1
 out[label]={'nested_input_manifest':file,'entries':len(entries),'verified':verified,'unresolved':missing,'hash_mismatches':bad,'all_package_relative_input_hashes_verified':not missing and not bad}
p=STAGE/'execution_specialist';expected=json.loads((p/'g01/input_sha256.json').read_text());members={};bad=[];nonfiles=[];symlinks=[];database_names=[];cache_names=[]
with tarfile.open(p/'g01_inputs.tar.gz','r:gz') as archive:
 for member in archive.getmembers():
  path=PurePosixPath(member.name)
  if path.is_absolute() or '..' in path.parts:bad.append({'member':member.name,'issue':'unsafe archive path'});continue
  if not member.isfile():nonfiles.append(member.name)
  if member.issym() or member.islnk():symlinks.append(member.name)
  if path.suffix in ['.sqlite','.sqlite3','.db'] or path.name.endswith(('-wal','-shm','-journal')):database_names.append(member.name)
  if path.suffix=='.pyc' or any(v in ['__pycache__','.pytest_cache'] for v in path.parts):cache_names.append(member.name)
  if member.isfile():
   if path.parts[0]!='g01_inputs':bad.append({'member':member.name,'issue':'unexpected container prefix'});continue
   input_name=str(path.relative_to('g01_inputs'))
   if input_name in members:bad.append({'member':member.name,'issue':'duplicate member'});continue
   f=archive.extractfile(member);h=hashlib.sha256()
   for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
   members[input_name]=h.hexdigest()
for name,h in members.items():
 if name not in expected:bad.append({'member':name,'issue':'not in explicit 275-input manifest'})
 elif h!=expected[name]:bad.append({'member':name,'issue':'nested input SHA mismatch','actual':h,'expected':expected[name]})
for name in expected:
 if name not in members:bad.append({'member':name,'issue':'missing archive input'})
out['execution_specialist']['G01_archive']={'archive':'g01_inputs.tar.gz','archive_sha256':digest(p/'g01_inputs.tar.gz'),'archive_container_prefix':'g01_inputs/','manifest_name_mapping':'remove only the fixed g01_inputs/ container prefix; retain each explicit allowlist-relative name','inner_manifest':'g01/input_sha256.json','expected_input_count':len(expected),'regular_member_count':len(members),'nonfile_members':nonfiles,'symlink_or_hardlink_members':symlinks,'database_named_members':database_names,'cache_named_members':cache_names,'issues':bad,'all_275_explicit_allowlist_inputs_verified':len(expected)==275 and len(members)==275 and not bad and not symlinks,'archive_extracted':False,'original_sensitive_directories_accessed':False}
path=ROOT/'package_assembly.json';assembly=json.loads(path.read_text());assembly['nested_manifest_verification']=out;assembly['authority_listed_synthetic_db_parent_authorization']='Parent explicitly authorized preservation of 162 manifest-listed synthetic SQLite input/output snapshots; only raw byte hashing/copying, no SQLite open or in-place execution; unlisted DB/wal/shm/cache/links excluded.';assembly['all_nested_input_manifests_verified']=all(v['all_package_relative_input_hashes_verified'] for v in out.values()) and out['execution_specialist']['G01_archive']['all_275_explicit_allowlist_inputs_verified'];assembly['nested_check_preparation_correction']='Initial checksum-name mapping omitted the fixed tar g01_inputs/ container prefix and therefore falsely reported 550 name mismatches; no byte hash mismatch was observed. First metadata/script preserved in root nested_verification_first_attempt.json and verify_nested_archives_initial.py. Corrected mapping verifies all 275 inner file hashes; no source/stage attachments modified.';path.write_text(json.dumps(assembly,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'all_nested_input_manifests_verified':assembly['all_nested_input_manifests_verified'],'packages':{k:{'entries':v['entries'],'verified':v['verified'],'unresolved':len(v['unresolved']),'hash_mismatches':len(v['hash_mismatches'])} for k,v in out.items()},'G01':{'member_count':len(members),'issues':len(bad),'verified':out['execution_specialist']['G01_archive']['all_275_explicit_allowlist_inputs_verified']}},sort_keys=True))
