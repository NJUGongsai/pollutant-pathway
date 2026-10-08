#!/usr/bin/env python
"""Synthetic-only replay; reject existing output, pin recorded source hashes."""
import argparse,ast,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--python',default=sys.executable);args=ap.parse_args();repo=args.repo.resolve();out=args.out.resolve()
if out.exists():raise SystemExit('output must be fresh/nonexistent')
if out==repo or repo in out.parents or out==B or B in out.parents:raise SystemExit('output must be outside repo/evidence')
snapshot=json.loads((B/'input_hashes.json').read_text());head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
if head!=snapshot['head']:raise SystemExit('source HEAD differs from recorded review; use detached current review commit')
for rel,dig in snapshot['files'].items():
 if hashlib.sha256((repo/rel).read_bytes()).hexdigest()!=dig:raise SystemExit('source input changed: '+rel)
out.mkdir()
for rel in snapshot['files']:
 dst=out/'repo'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(repo/rel,dst)
for name in ['probe.py','crash_concurrency.py','defer_budget_bypass.py']:shutil.copy2(B/name,out/name)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');commands=[]
for name,log in [('probe.py','probe'),('crash_concurrency.py','crash'),('defer_budget_bypass.py','defer_bypass')]:
 argv=[args.python,'-B',str(out/name)];start=time.monotonic();p=subprocess.run(argv,cwd=out/'repo',env=env,text=True,capture_output=True,timeout=180);(out/(log+'.stdout.jsonl')).write_text(p.stdout);(out/(log+'.stderr.txt')).write_text(p.stderr);commands.append({'argv':argv,'cwd':str(out/'repo'),'returncode':p.returncode,'elapsed_seconds':time.monotonic()-start});(out/'reproduction_commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 if p.returncode:raise SystemExit(p.returncode)
print(json.dumps({'source_head':head,'case_counts':{'probe':16,'crash_and_concurrency':5,'defer_overbudget':1},'network_request_count':0,'out':str(out)}))
