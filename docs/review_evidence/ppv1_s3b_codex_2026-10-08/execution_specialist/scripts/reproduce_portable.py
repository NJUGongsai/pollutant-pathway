#!/usr/bin/env python3
"""Reproduce ONLY in a new external scratch; no writes in evidence."""
import argparse,ast,os,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();out=a.out.expanduser().resolve();evidence=Path(__file__).resolve().parents[1];repo=Path('/Volumes/CC/Enzyme_Agent/dependingv43')
if out.exists() or evidence in out.parents or out in evidence.parents or repo in out.parents or out in repo.parents:raise RuntimeError('fresh external output required')
out.mkdir();(out/'scripts').mkdir();(out/'allowlists').mkdir()
for name in ['run_actual.py','safe_g01_supplied.py']:
    shutil.copy2(evidence/'scripts'/name,out/'scripts'/name)
for name in ['input_hashes.json','g01_v3_source_addition_hashes.json']:
    shutil.copy2(evidence/'allowlists'/name,out/'allowlists'/name)
env=dict(os.environ)|{'PYTHONDONTWRITEBYTECODE':'1'}
raise SystemExit(subprocess.run(['/Users/cc/miniconda3/envs/depending43/bin/python','-B',str(out/'scripts/run_actual.py')],cwd=out,env=env).returncode)
