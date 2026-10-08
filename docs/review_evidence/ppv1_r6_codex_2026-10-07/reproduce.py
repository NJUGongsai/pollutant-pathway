"""Copy synthetic R6 evidence to fresh temporary output; never mutate originals."""
import argparse, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
from rdkit import rdBase

HEAD='6d9020130a481866ce2f3b79933907a33d8cfc9e'
BASELINE='293bc627f57b1f778aa433750f7f61d00b4a9d18'
p=argparse.ArgumentParser()
p.add_argument('--repo',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--allow-head-change',action='store_true')
p.add_argument('--skip-pytest',action='store_true')
p.add_argument('--baseline',action='store_true')
a=p.parse_args()
bundle=Path(__file__).resolve().parent
repo=a.repo.resolve();out=a.out.resolve()
if out.is_relative_to(repo) or out.is_relative_to(bundle):
    raise RuntimeError('Output must be outside repository and permanent evidence')
out.mkdir(parents=True,exist_ok=True)
if any(out.iterdir()):raise RuntimeError('Output must be a new empty directory')
actual=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
if actual!=HEAD and not a.allow_head_change:
    raise RuntimeError('Reviewed HEAD changed; explicitly use --allow-head-change for a new review')
status_before=subprocess.check_output(['git','-C',str(repo),'status','--short'],text=True)
shutil.copytree(repo/'src',out/'src',ignore=shutil.ignore_patterns('__pycache__'))
for lane in ['chem','conditions','storage']:
    shutil.copytree(bundle/lane,out/lane,ignore=shutil.ignore_patterns('*.json','*.jsonl','*.txt','__pycache__'))
for name in ['admission_completion_probe.py','r5_admission_coverage_probe.py','assert_observed.py']:
    shutil.copy2(bundle/name,out/name)
# The unchanged storage script hashes a sibling source directory. A local link
# keeps that provenance check on the same isolated source as every other probe.
(out/'storage/src').symlink_to(out/'src',target_is_directory=True)
storage_script=out/'storage/r6_storage_boundary_probe.py'
s=storage_script.read_text()
s=s.replace("Path('/Volumes/CC/Enzyme_Agent/dependingv43')",'Path('+repr(str(repo))+')')
if actual!=HEAD:
    s=s.replace("EXPECTED_HEAD = '"+HEAD+"'","EXPECTED_HEAD = '"+actual+"'")
storage_script.write_text(s)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(out/'src'))
metadata={'reviewed_head':HEAD,'actual_head':actual,'baseline_head':BASELINE,
    'python':sys.version,'rdkit':rdBase.rdkitVersion,'source_root':str(out/'src'),
    'synthetic_only':True,'git_status_before':status_before,'commands':[],
    'copied_source_sha256':{str(f.relative_to(out/'src')):hashlib.sha256(f.read_bytes()).hexdigest()
        for f in sorted((out/'src').rglob('*')) if f.is_file()}}
def run(script,output,stderr):
    path=out/script;cmd=[sys.executable,'-B',str(path)]
    with (out/output).open('w') as so,(out/stderr).open('w') as se:
        result=subprocess.run(cmd,cwd=path.parent,env=env,stdout=so,stderr=se)
    metadata['commands'].append({'argv':cmd,'cwd':str(path.parent),'exit_code':result.returncode})
    if result.returncode:raise RuntimeError('Probe process failed: '+script)
    print('completed',script,flush=True)
jobs=[
 ('admission_completion_probe.py','admission_completion_probe.output.jsonl','admission_completion_probe.stderr.txt'),
 ('chem/cx_boundary_probe.py','chem/cx_boundary_probe.output.jsonl','chem/cx_boundary_probe.stderr.txt'),
 ('chem/r5_focused_replay.py','chem/r5_focused_replay.output.jsonl','chem/r5_focused_replay.stderr.txt'),
 ('chem/r4_boundary_replay.py','chem/r4_boundary_replay.output.jsonl','chem/r4_boundary_replay.stderr.txt'),
 ('chem/r3_probe_replay.py','chem/r3_probe_replay.output.jsonl','chem/r3_probe_replay.stderr.txt'),
 ('conditions/probe.py','conditions/summary.json','conditions/stderr.txt'),
 ('conditions/r5_replay/probe.py','conditions/r5_replay/summary.json','conditions/r5_replay/stderr.txt'),
 ('conditions/r4_replay/probe.py','conditions/r4_replay/summary.json','conditions/r4_replay/stderr.txt'),
 ('storage/r6_storage_boundary_probe.py','storage/r6_storage_boundary_probe.output.jsonl','storage/r6_storage_boundary_probe.stderr.txt'),
 ('storage/storage_boundary_probe.py','storage/r5_storage_output.jsonl','storage/r5_storage.stderr.txt'),
 ('storage/r4_storage_probe.py','storage/r4_storage_output.jsonl','storage/r4_storage.stderr.txt'),
 ('storage/r3_storage_probe.py','storage/r3_storage_output.jsonl','storage/r3_storage.stderr.txt')]
for args in jobs:run(*args)
if not a.skip_pytest:
    (out/'tests').mkdir()
    for test in sorted((repo/'tests').glob('test_ppv1*.py')):shutil.copy2(test,out/'tests'/test.name)
    cmd=[sys.executable,'-B','-m','pytest','-p','no:cacheprovider','-q','-rs','tests']
    with (out/'pytest_output.txt').open('w') as so:
        result=subprocess.run(cmd,cwd=out,env=env,stdout=so,stderr=subprocess.STDOUT)
    metadata['commands'].append({'argv':cmd,'cwd':str(out),'exit_code':result.returncode})
    if result.returncode:raise RuntimeError('PPV1 regression failed')
if a.baseline:
    base=out/'baseline';base.mkdir()
    archive=subprocess.check_output(['git','-C',str(repo),'archive',BASELINE,'src'])
    subprocess.run(['tar','-x','-C',str(base)],input=archive,check=True)
    shutil.copytree(bundle/'baseline_tests',base/'tests')
    cmd=[sys.executable,'-B','-m','pytest','-p','no:cacheprovider','-q','-rs','tests']
    with (out/'baseline_red_output.txt').open('w') as so:
        result=subprocess.run(cmd,cwd=base,env=dict(env,PYTHONPATH=str(base/'src')),stdout=so,stderr=subprocess.STDOUT)
    metadata['commands'].append({'argv':cmd,'cwd':str(base),'exit_code':result.returncode,'expected_red':True})
    assert result.returncode==1 and '44 failed, 26 passed' in (out/'baseline_red_output.txt').read_text()
if actual==HEAD:
    subprocess.run([sys.executable,'-B',str(out/'assert_observed.py')],cwd=out,env=env,check=True)
else:
    print('New HEAD: R6 observation assertions skipped; inspect behavior changes and add target acceptance assertions.',flush=True)
metadata['git_status_after']=subprocess.check_output(['git','-C',str(repo),'status','--short'],text=True)
assert metadata['git_status_after']==status_before,'Repository status changed during read-only reproduction'
(out/'run_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
print('completed synthetic reproduction:',str(out),flush=True)
