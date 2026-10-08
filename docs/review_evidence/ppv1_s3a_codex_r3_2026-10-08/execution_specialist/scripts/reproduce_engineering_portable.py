#!/usr/bin/env python3
"""Portable entry: fresh outside output only. Prepared/syntax-checked, NOT executed this review."""
import argparse,os,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();out=a.out.resolve();repo=Path('/Volumes/CC/Enzyme_Agent/dependingv43').resolve();bundle=Path(__file__).resolve().parents[1]
if out.exists() or repo==out or repo in out.parents or out in repo.parents:raise RuntimeError('Fresh separate output required')
out.mkdir();(out/'scripts').mkdir();shutil.copytree(bundle/'allowlists',out/'allowlists')
for n in ['run_actual.py','safe_g01_supplied.py']:shutil.copy2(bundle/'scripts'/n,out/'scripts'/n)
env=dict(os.environ)|{'PYTHONDONTWRITEBYTECODE':'1'}
raise SystemExit(subprocess.run(['/Users/cc/miniconda3/envs/depending43/bin/python','-B',str(out/'scripts/run_actual.py')],cwd=repo,env=env).returncode)
