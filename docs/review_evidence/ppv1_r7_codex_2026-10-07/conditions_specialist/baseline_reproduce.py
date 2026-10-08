"""Replay R7's 57 regressions at R6 HEAD using a fresh detached worktree.

Copy this script and original_tests to a new tmp directory before running.
No gold/assets/sealed runs/model access. Worktree is removed in finally.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess
from pathlib import Path
BASE='6d9020130a481866ce2f3b79933907a33d8cfc9e'
TESTS=['test_ppv1_r7_chem.py','test_ppv1_r7_conditions.py','test_ppv1_r7_storage.py']
p=argparse.ArgumentParser()
p.add_argument('--repo',required=True)
p.add_argument('--out',required=True)
p.add_argument('--python',default='/Users/cc/miniconda3/envs/depending43/bin/python')
a=p.parse_args()
repo=Path(a.repo).resolve(); out=Path(a.out).resolve()
if out.exists(): raise SystemExit('out must not exist; use a new tmp directory')
out.mkdir(parents=True)
wt=out/'baseline_worktree'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
commands=[]
def command(argv,cwd,log):
    r=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,text=True)
    (out/log).write_text(r.stdout+r.stderr)
    commands.append({'argv':argv,'cwd':str(cwd),'exit_code':r.returncode,'log':log})
    return r
r=command(['git','worktree','add','--detach',str(wt),BASE],repo,'worktree_add.log')
if r.returncode: raise SystemExit(r.returncode)
try:
    src=Path(__file__).resolve().parent/'original_tests'
    hashes={}
    (out/'baseline_tests').mkdir()
    for f in TESTS:
        data=(src/f).read_bytes()
        hashes[f]=hashlib.sha256(data).hexdigest()
        (wt/'tests'/f).write_bytes(data)
    chem=wt/'tests'/TESTS[0]
    text=chem.read_text()
    assert '    COMPLETION_LICENSE,\n' in text
    text=text.replace('    COMPLETION_LICENSE,\n','')
    assert '\nSRC = ' in text
    text=text.replace('\nSRC = ','\nCOMPLETION_LICENSE = "composition_only_hydrogen_equivalents"\n\nSRC = ',1)
    chem.write_text(text)
    for f in TESTS: shutil.copy2(wt/'tests'/f,out/'baseline_tests'/f)
    r=command([a.python,'-B','-m','pytest','-p','no:cacheprovider','-q','-rs',*[str(Path('tests')/f) for f in TESTS]],wt,'baseline_pytest_full.log')
    assert r.returncode==1
    assert '33 failed, 24 passed' in (out/'baseline_pytest_full.log').read_text()
    (out/'metadata.json').write_text(json.dumps({'base':BASE,'tests_sha256':hashes,'import_adapter':'COMPLETION_LICENSE same literal only','expected':'33 failed /24 passed'},ensure_ascii=False,indent=2)+'\n')
finally:
    clean=command(['git','worktree','remove','--force',str(wt)],repo,'worktree_remove.log')
    (out/'commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
    if clean.returncode: raise RuntimeError('Failed to remove temporary worktree; inspect worktree_remove.log')
print('baseline reproduced: 33 failed /24 passed; detached worktree removed')
