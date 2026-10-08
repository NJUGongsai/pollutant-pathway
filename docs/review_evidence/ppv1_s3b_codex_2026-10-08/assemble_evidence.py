#!/usr/bin/env python3
"""Copy only frozen manifest attachments, without executing any probe/test.
This script writes only this review's scratch staging directory.
"""
from __future__ import annotations
import argparse,hashlib,json,shutil,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
STAGE=ROOT/'evidence_stage'
EXPECTED_ROLES={'execution_specialist','production_specialist','queue_recovery_specialist'}
CONTROLS=('manifest.json','SHA256SUMS','manifest.sha256','manifest.json.sha256')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safe_rel(s):
    p=Path(s)
    if p.is_absolute() or '..' in p.parts or not p.parts:raise RuntimeError(f'unsafe relative path {s!r}')
    return p

def allowed_file(p,root):
    if p.is_symlink() or not p.is_file():raise RuntimeError(f'not a regular file: {p}')
    if root.resolve() not in p.resolve().parents:raise RuntimeError(f'path escape {p}')
    if '__pycache__' in p.parts or '.pytest_cache' in p.parts or p.suffix in {'.sqlite','.db','.pyc','.pyo'} or p.name.endswith(('-wal','-shm')):raise RuntimeError(f'database/cache forbidden {p}')

def entries(m):
    fs=m.get('files',m.get('sha256'))
    if isinstance(fs,list):
        for r in fs:
            if not isinstance(r,dict):raise RuntimeError('list file descriptor must be object')
            name=r.get('path',r.get('name')); digest=r.get('sha256',r.get('hash'));size=r.get('bytes',r.get('size'))
            if not name or not digest:raise RuntimeError('missing manifest path/hash')
            yield str(name),str(digest),size
    elif isinstance(fs,dict):
        for name,r in fs.items():
            if isinstance(r,str):yield str(name),r,None
            elif isinstance(r,dict):
                digest=r.get('sha256',r.get('hash'));size=r.get('bytes',r.get('size'))
                if not digest:raise RuntimeError('missing file sha256')
                yield str(name),str(digest),size
            else:raise RuntimeError('unknown file descriptor')
    else:raise RuntimeError('manifest files/sha256 container unknown')

def copy_one(role,source,expected_manifest):
    source=Path(source).resolve();destination=STAGE/role
    allowed_file(source/'manifest.json',source)
    actual=sha(source/'manifest.json')
    if expected_manifest and actual!=expected_manifest:raise RuntimeError(f'{role} manifest SHA differs')
    m=json.loads((source/'manifest.json').read_text());declared=list(entries(m));seen=set();records=[]
    destination.mkdir(parents=True,exist_ok=True)
    for name,digest,size in declared:
        rel=safe_rel(name)
        if str(rel) in seen:raise RuntimeError('duplicate manifest entry')
        seen.add(str(rel));src=source/rel;dst=destination/rel
        allowed_file(src,source)
        if sha(src)!=digest or (size is not None and src.stat().st_size!=int(size)):raise RuntimeError(f'source attachment mismatch {role}/{name}')
        dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists():
            allowed_file(dst,destination)
            if sha(dst)!=digest or dst.stat().st_size!=src.stat().st_size:raise RuntimeError('existing staged copy mismatch')
        else:shutil.copy2(src,dst)
        if sha(dst)!=digest or dst.stat().st_size!=src.stat().st_size or sha(src)!=digest:raise RuntimeError('copied attachment mismatch')
        records.append({'path':name,'bytes':dst.stat().st_size,'sha256':digest})
    controls=[]
    for name in CONTROLS:
        src=source/name
        if not src.exists():continue
        allowed_file(src,source);digest=sha(src);dst=destination/name
        if dst.exists():
            allowed_file(dst,destination)
            if sha(dst)!=digest:raise RuntimeError('control mismatch')
        else:shutil.copy2(src,dst)
        if sha(dst)!=digest:raise RuntimeError('sidecar copy mismatch')
        controls.append({'path':name,'bytes':src.stat().st_size,'sha256':digest})
    if sha(source/'manifest.json')!=actual:raise RuntimeError('source manifest modified')
    for name in ['manifest.sha256','manifest.json.sha256']:
        if (destination/name).exists():
            if (destination/name).read_text().split()[0]!=actual:raise RuntimeError('manifest sidecar digest mismatch')
    sums=destination/'SHA256SUMS'
    if sums.exists():
        for line in sums.read_text().splitlines():
            if not line.strip():continue
            digest,name=line.split(maxsplit=1);name=name.lstrip('* ');rel=safe_rel(name);p=destination/rel
            allowed_file(p,destination)
            if sha(p)!=digest:raise RuntimeError('SHA256SUMS mismatch')
    tarchecks=[]
    for r in records:
        if not r['path'].endswith(('.tar.gz','.tgz','.tar')):continue
        p=destination/r['path'];members={}
        with tarfile.open(p,'r:*') as tar:
            for member in tar.getmembers():
                if not member.isfile():raise RuntimeError('tar link/directory forbidden')
                safe_rel(member.name)
                if member.name in members:raise RuntimeError('duplicate tar entry')
                if '__pycache__' in Path(member.name).parts or Path(member.name).suffix in {'.sqlite','.db','.pyc','.pyo'}:raise RuntimeError('forbidden tar payload')
                members[member.name]=hashlib.sha256(tar.extractfile(member).read()).hexdigest()
        expectedfile=destination/'g01/input_sha256.json'
        match=None
        if role=='execution_specialist' and r['path']=='g01_inputs.tar.gz':
            if not expectedfile.is_file():raise RuntimeError('missing G01 input whitelist')
            expected=json.loads(expectedfile.read_text())
            match=members==expected
            if len(expected)!=286 or not match:raise RuntimeError('286-member G01 tar SHA differs')
        tarchecks.append({'path':r['path'],'member_count':len(members),'regular_files_only':True,'read_only_no_extraction':True,'matches_286_inputs':match,'member_sha256':members})
    actual_paths={p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}
    allowed_paths={r['path'] for r in records+controls}
    if actual_paths!=allowed_paths:raise RuntimeError('unlisted staged file')
    for p in destination.rglob('*'):
        if p.is_symlink():raise RuntimeError('staged link')
    return {'source':str(source),'destination':str(destination),'source_manifest_sha256':actual,'declared_attachment_count':len(records),'copied_control_count':len(controls),'copied_bytes':sum(r['bytes'] for r in records+controls),'all_declared_and_controls_match':True,'files':records,'controls':controls,'tar_checks':tarchecks}

def main():
    a=argparse.ArgumentParser();a.add_argument('--package',action='append',default=[]);a.add_argument('--manifest-sha',action='append',default=[]);args=a.parse_args()
    previous=ROOT/'package_assembly.json';sources={};expected={}
    if previous.exists():
        old=json.loads(previous.read_text())
        for role,r in old.get('packages',{}).items():sources[role]=r['source'];expected[role]=r['source_manifest_sha256']
    for s in args.package:
        role,path=s.split('=',1)
        if role not in EXPECTED_ROLES:raise RuntimeError('unknown role')
        if role in sources and str(Path(path).resolve())!=sources[role]:raise RuntimeError('role source cannot change')
        sources[role]=path
    for s in args.manifest_sha:
        role,value=s.split('=',1)
        if role not in EXPECTED_ROLES:raise RuntimeError('unknown role SHA')
        expected[role]=value
    STAGE.mkdir(exist_ok=True)
    result={role:copy_one(role,path,expected.get(role)) for role,path in sorted(sources.items())}
    output={'root':str(ROOT),'stage':str(STAGE),'expected_roles':sorted(EXPECTED_ROLES),'packages':result,'all_copied':set(result)==EXPECTED_ROLES,'pending_roles':sorted(EXPECTED_ROLES-set(result)),'no_hash_or_symlink_or_cache_issues':True,'pure_archiving_no_suite_or_probe_run':True}
    previous.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k!='packages'},ensure_ascii=False))
if __name__=='__main__':main()
