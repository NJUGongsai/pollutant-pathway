#!/usr/bin/env python3
"""Reproduce only this synthetic specialty in a NEW directory; no suites/assets.
Archive controller written after probes: syntax checked, not itself executed.
"""
from __future__ import annotations
import argparse,json,os,shutil,subprocess,sys,time,hashlib
from pathlib import Path
EXPECTED='9b78f4279cc6fa50b3b51c31a5c8e07abbeda207'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True);ap.add_argument('--python',default=sys.executable)
    a=ap.parse_args();repo=Path(a.repo).resolve();out=Path(a.out).resolve();bundle=Path(__file__).resolve().parent
    if out.exists() or repo==out or repo in out.parents or bundle==out or bundle in out.parents:raise SystemExit('Use a fresh output outside the repo and permanent evidence.')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    if head!=EXPECTED:raise SystemExit(f'Historical reproducibility is pinned to {EXPECTED}; actual={head}. No guessed revision adaptation.')
    hashes=json.loads((bundle/'input_hashes.json').read_text())
    selected={k:v for k,v in hashes.items() if k.startswith('src/') or k in ('pyproject.toml','tests/s3a_worker.py')}
    for rel,sha in selected.items():
        if hashlib.sha256((repo/rel).read_bytes()).hexdigest()!=sha:raise SystemExit(f'Input drift: {rel}')
    out.mkdir(parents=True);iso=out/'isolated';iso.mkdir()
    shutil.copytree(repo/'src',iso/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (iso/'tests').mkdir();shutil.copy2(repo/'tests/s3a_worker.py',iso/'tests/s3a_worker.py');shutil.copy2(repo/'pyproject.toml',iso/'pyproject.toml')
    for name in ('baseline_workflow_runner.py','baseline_pollutant_profile.py'):shutil.copy2(bundle/name,out/name)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(iso/'src')+os.pathsep+str(iso/'tests'))
    commands=[]
    def run(name,argv,expected):
        start=time.time();p=subprocess.run([a.python,'-B',str(bundle/name),*argv],cwd=iso,env=env,capture_output=True,text=True)
        stdout={'inheritance_probe.py':'inheritance_v2.stdout.jsonl','chemistry_static_probe.py':'chemistry_v2.stdout.jsonl','registered_cx_controls.py':'cx_controls.stdout.jsonl','assert_observed.py':'assert_observed.stdout.json','assert_contract.py':'assert_contract.stdout.txt'}[name]
        stderr=stdout.replace('stdout.jsonl','stderr.txt').replace('stdout.json','stderr.txt').replace('stdout.txt','stderr.txt')
        (out/stdout).write_text(p.stdout);(out/stderr).write_text(p.stderr)
        commands.append({'argv':[a.python,'-B',str(bundle/name),*argv],'cwd':str(iso),'env':{k:env[k] for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE')},'exit_code':p.returncode,'expected_exit_code':expected,'elapsed_seconds':time.time()-start})
        (out/'run_metadata.json').write_text(json.dumps({'actual_head':head,'commands':commands,'source_hashes':selected},indent=2))
        if p.returncode!=expected:raise SystemExit(f'{name}: {p.returncode} != {expected}; evidence retained')
    run('inheritance_probe.py',['--out',str(out/'probe_run_v2')],0)
    run('chemistry_static_probe.py',['--inputs',str(out),'--out',str(out/'chemistry_run_v2')],0)
    run('registered_cx_controls.py',['--out',str(out/'cx_controls_run')],0)
    run('assert_observed.py',['--root',str(out)],0)
    run('assert_contract.py',['--root',str(out)],1)
    print(json.dumps({'completed':True,'actual_head':head,'out':str(out),'desired_contract_assert_exit1':'expected; this pins the established recovery gap'}))
if __name__=='__main__':main()
