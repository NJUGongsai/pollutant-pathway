#!/usr/bin/env python3
"""Replay synthetic R7 review only into a fresh external directory.
Full G01 has a separate explicit allowlist script; this controller never reads it.
"""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
from rdkit import rdBase
EXPECTED='858dd94c7c6c8fc387940242403d67b6b36b5313'
p=argparse.ArgumentParser();p.add_argument('--repo',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
p.add_argument('--allow-head-change',action='store_true');p.add_argument('--skip-ppv1',action='store_true');p.add_argument('--baseline',action='store_true')
a=p.parse_args();bundle=Path(__file__).resolve().parent;repo=a.repo.resolve();out=a.out.resolve()
if out.exists():raise RuntimeError('Output must not exist; use a fresh tmp directory')
if out.is_relative_to(repo) or out.is_relative_to(bundle) or repo.is_relative_to(out):raise RuntimeError('Output must be separate from repo and permanent evidence')
actual=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
if actual!=EXPECTED and not a.allow_head_change:raise RuntimeError('Reviewed HEAD changed; require --allow-head-change and inspect all outputs')
before=subprocess.check_output(['git','-C',str(repo),'status','--short'],text=True)
out.mkdir();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');commands=[]
def run(cmd,cwd,stem,expected=0):
    so=out/(stem+'.stdout.txt');se=out/(stem+'.stderr.txt')
    with so.open('w') as o,se.open('w') as e:r=subprocess.run(cmd,cwd=cwd,env=env,stdout=o,stderr=e)
    commands.append({'argv':cmd,'cwd':str(cwd),'exit_code':r.returncode,'expected_exit_code':expected,'stdout':so.name,'stderr':se.name})
    if r.returncode!=expected:raise RuntimeError(f'{stem}: exit {r.returncode}; inspect {se}')
    return so,se
run([sys.executable,'-B',str(bundle/'r6_original/reproduce.py'),'--repo',str(repo),'--out',str(out/'r6_replay'),'--allow-head-change','--skip-pytest'],out,'r6_replay')
run([sys.executable,'-B',str(bundle/'assert_r7_replay.py'),'--out',str(out/'r6_replay'),'--reference',str(bundle/'r6_selected_outcome_reference.json')],out,'assert_r7_replay')
if actual==EXPECTED:
    run([sys.executable,'-B',str(out/'r6_replay/assert_observed.py')],out/'r6_replay','r6_assert_expected_failure',expected=1)
    assert 'AssertionError' in (out/'r6_assert_expected_failure.stderr.txt').read_text()
for lane in ['chemistry_current','conditions_current','storage_current']:
    dst=out/lane;dst.mkdir();(dst/'src').symlink_to(out/'r6_replay/src',target_is_directory=True)
    for f in (bundle/lane).glob('*.py'):shutil.copy2(f,dst/f.name)
    if (bundle/lane/'tests').exists():shutil.copytree(bundle/lane/'tests',dst/'tests')
chem=out/'chemistry_current'
so,se=run([sys.executable,'-B',str(chem/'chemical_boundary_probe.py')],chem,'chemical_boundary_probe')
shutil.copy2(so,chem/'chemical_boundary_output.jsonl')
storage=out/'storage_current'
so,se=run([sys.executable,'-B',str(storage/'storage_contract_probe.py'),str(out/'r6_replay')],storage,'storage_contract_probe')
shutil.copy2(so,storage/'storage_contract_probe.output.jsonl')
conditions=out/'conditions_current'
run([sys.executable,'-B',str(conditions/'conditions_public_probe.py'),'--source',str(conditions)],conditions,'conditions_public_probe')
if actual==EXPECTED:
    run([sys.executable,'-B',str(chem/'assert_chemical_observed.py')],chem,'chemical_observed_assert')
    run([sys.executable,'-B',str(storage/'storage_assert_observed.py'),str(storage/'storage_contract_probe.output.jsonl')],storage,'storage_observed_assert')
if not a.skip_ppv1:
    tests=out/'ppv1/tests';tests.mkdir(parents=True)
    for f in sorted((repo/'tests').glob('test_ppv1_*.py')):shutil.copy2(f,tests/f.name)
    for name in ['pyproject.toml']:
        if (repo/name).exists():shutil.copy2(repo/name,tests.parent/name)
    (tests.parent/'src').symlink_to(out/'r6_replay/src',target_is_directory=True)
    env['PYTHONPATH']=str(out/'r6_replay/src')
    run([sys.executable,'-B','-m','pytest','-p','no:cacheprovider','-q','-rs','tests'],tests.parent,'ppv1_full')
if a.baseline:
    run([sys.executable,'-B',str(bundle/'conditions_specialist/baseline_reproduce.py'),'--repo',str(repo),'--out',str(out/'baseline'),'--python',sys.executable],out,'baseline_reproduce')
after=subprocess.check_output(['git','-C',str(repo),'status','--short'],text=True)
assert before==after,'Repository status changed'
metadata={'expected_head':EXPECTED,'actual_head':actual,'python':sys.version,'rdkit':rdBase.rdkitVersion,
 'commands':commands,'git_status_before':before,'git_status_after':after,
 'synthetic_only':True,'G01_executed':False,'baseline_executed':a.baseline,'PPV1_executed':not a.skip_ppv1,
 'changed_head_note':'At a new HEAD defect-observation assertions are skipped; repaired-control replay and per-case outputs still need review.',
 'copied_source_sha256':{str(f.relative_to(out/'r6_replay/src')):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((out/'r6_replay/src').rglob('*')) if f.is_file()}}
(out/'reproduction_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'out':str(out),'actual_head':actual,'commands_completed':len(commands),'synthetic_only':True},ensure_ascii=False))
