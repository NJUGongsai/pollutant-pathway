#!/usr/bin/env python3
"""Safely reproduce only two synthetic root probes in a fresh external tree.

No suites, original data, old runs or model providers are invoked. The recorded
assertion describes unresolved observed gaps, not repaired behavior. This new
wrapper was syntax/safety inspected only when archived, never runtime rerun.
"""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path

HEAD='9b78f4279cc6fa50b3b51c31a5c8e07abbeda207'
PARENT='00e509a974b40a7c9779fcd35e53b16637a13d60'
ORIGINAL_REPO=Path('/Volumes/CC/Enzyme_Agent/dependingv43')
INPUT_SNAPSHOT_SHA256='b813a232acde6299de331040fae73c29eeedd438c69049ae7018e338cbbcab9f'
SCRIPT_SHA256={
    'request_probe.py':'d87ced27fecfe367ad5ee07e36f2d9c67af6f5b9f776cc8e023b7c54046bd4e4',
    'policy_probe.py':'f76681453e0d012099ce333730aaadaffb7335a9db232b69a36c803389c593b7',
    'assert_root_observed.py':'469ba96177b89b9b0696eb1baed2592ebd4e209cab600c18f183ea4578dd7698',
}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def safe_relative(value):
    rel=Path(value)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:
        raise RuntimeError('unsafe relative input path')
    return rel

def verified_file(root,rel,expected):
    path=root/rel;real=path.resolve();bound=root.resolve()
    if not path.is_file() or bound not in real.parents:
        raise RuntimeError(f'input missing or escapes boundary: {path}')
    observed=sha(path)
    if observed!=expected:raise RuntimeError(f'pinned SHA mismatch: {path}')
    return path

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path,
                    help='Nonexistent directory, outside repo and evidence bundle')
    ap.add_argument('--python',type=Path,default=Path(sys.executable),
                    help='Use the depending43 Python')
    args=ap.parse_args();repo=args.repo.expanduser().resolve();out=args.out.expanduser().resolve()
    bundle=Path(__file__).resolve().parent;python=args.python.expanduser().resolve()
    if out.exists():raise RuntimeError('output must not exist; choose a new external directory')
    if repo==out or repo in out.parents or out in repo.parents:
        raise RuntimeError('output must be outside and separate from repository')
    if bundle==out or bundle in out.parents or out in bundle.parents:
        raise RuntimeError('output must be outside and separate from evidence bundle')
    if not python.is_file():raise RuntimeError('Python executable missing')
    # No output is created before all authority and content checks below.
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    parent=subprocess.check_output(['git','rev-parse','HEAD^'],cwd=repo,text=True).strip()
    if head!=HEAD or parent!=PARENT:raise RuntimeError('actual repository HEAD/parent differs from reviewed snapshot')
    snapshot_file=verified_file(bundle,Path('input_snapshot.json'),INPUT_SNAPSHOT_SHA256)
    snapshot=json.loads(snapshot_file.read_text())
    if snapshot['actual_head']!=HEAD or snapshot['parent_head']!=PARENT or not snapshot['synthetic_only']:
        raise RuntimeError('snapshot provenance mismatch')
    # The snapshot's ordinary src allowlist includes complete vendor. Other
    # documents in the broad original snapshot are neither hashed nor read here.
    source_hashes={}
    for name,digest in snapshot['isolated_source_sha256'].items():
        rel=safe_relative(name)
        if rel.parts[0]!='src':raise RuntimeError('unexpected source snapshot prefix')
        source_hashes[rel.as_posix()]=digest
    if not any(name.startswith('src/pathway_v43/vendor/') for name in source_hashes):
        raise RuntimeError('complete vendor source snapshot required')
    actual_source_paths={p.relative_to(repo).as_posix() for p in (repo/'src').rglob('*')
                         if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
    if actual_source_paths!=set(source_hashes):raise RuntimeError('source file set differs from original isolated snapshot')
    input_hashes=dict(source_hashes)
    for rel in ('pyproject.toml','tests/s3a_worker.py'):
        original_key=str(ORIGINAL_REPO/rel)
        if original_key not in snapshot['input_sha256']:raise RuntimeError('required metadata/worker snapshot missing')
        input_hashes[rel]=snapshot['input_sha256'][original_key]
    paths={name:verified_file(repo,safe_relative(name),digest) for name,digest in input_hashes.items()}
    scripts={name:verified_file(bundle,Path(name),digest) for name,digest in SCRIPT_SHA256.items()}
    out.mkdir(parents=True)
    for name,path in paths.items():
        target=out/safe_relative(name);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        if sha(target)!=input_hashes[name]:raise RuntimeError('copy SHA mismatch')
    shutil.copy2(snapshot_file,out/'input_snapshot.json')
    for name,path in scripts.items():shutil.copy2(path,out/name)
    pinned_env={
        'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':os.pathsep.join([str(out/'src'),str(out/'tests')]),
        'BBD_DATA_ROOT':str(out/'empty_external_data'),'V3_CODE_ROOT':str(out/'absent_dependingv3'),
        'DEPENDING_V3_ROOT':str(out/'absent_dependingv3'),'V43_ASSET_ROOT':str(out/'absent_assets'),
    }
    env=dict(os.environ)|pinned_env;commands=[]
    metadata={'actual_head':head,'actual_parent':parent,'repo':str(repo),'out':str(out),
              'actual_git_status':subprocess.check_output(['git','status','--short'],cwd=repo,text=True),
              'pinned_snapshot_sha256':INPUT_SNAPSHOT_SHA256,'input_sha256':input_hashes,'script_sha256':SCRIPT_SHA256,
              'pinned_environment':pinned_env,'synthetic_only':True,'suite_execution':False,
              'no_model_provider_or_network_send':True,'preparation_verified_before_output_creation':True}
    (out/'root_probe_reproduction.preparation.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    for name in ('request_probe','policy_probe','assert_root_observed'):
        argv=[str(python),'-B',str(out/(name+'.py'))]
        if name=='assert_root_observed':argv+=['--logs',str(out)]
        start=time.monotonic();stdout=out/(name+'.stdout.jsonl');stderr=out/(name+'.stderr.txt')
        with stdout.open('w') as so,stderr.open('w') as se:
            result=subprocess.run(argv,cwd=out,env=env,stdout=so,stderr=se)
        record={'argv':argv,'cwd':str(out),'pinned_environment':pinned_env,'exit_code':result.returncode,
                'elapsed_seconds':time.monotonic()-start,'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr)}
        commands.append(record);(out/(name+'.run.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
        (out/'root_probe_reproduction.commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
        if result.returncode:raise RuntimeError(f'{name} exited {result.returncode}; original output preserved')
    print(json.dumps({'out':str(out),'head':head,'probe_count':2,'assertion_exit_code':0,
                      'suites_executed':False,'observed_gaps_asserted_not_repair_certified':True},sort_keys=True))
    return 0
if __name__=='__main__':raise SystemExit(main())
