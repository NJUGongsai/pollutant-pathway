#!/usr/bin/env python3
"""Run only explicit local synthetic scripts; capture real invocation metadata."""
from pathlib import Path
import argparse, hashlib, json, os, sqlite3, subprocess, time
ROOT = Path(__file__).resolve().parents[1]
PY = '/Users/cc/miniconda3/envs/depending43/bin/python'
ap = argparse.ArgumentParser(); ap.add_argument('name'); ap.add_argument('script'); a = ap.parse_args()
script = ROOT / a.script
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(ROOT/'source/src')+':'+str(ROOT/'source/tests'))
t = time.monotonic(); result = subprocess.run([PY, '-B', str(script)], cwd=ROOT, env=env, capture_output=True, text=True)
out = ROOT/'evidence'/a.name; out.mkdir(exist_ok=True)
(out/'stdout.txt').write_text(result.stdout); (out/'stderr.txt').write_text(result.stderr)
meta = json.loads((ROOT/'evidence/input_snapshot.json').read_text())['metadata']
record = {'argv':[PY, '-B', str(script)],'cwd':str(ROOT),'env_overrides':{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':env['PYTHONPATH']},'elapsed_s':time.monotonic()-t,'exit_code':result.returncode,'input_script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(), 'metadata':meta,'stdout_sha256':hashlib.sha256(result.stdout.encode()).hexdigest(),'stderr_sha256':hashlib.sha256(result.stderr.encode()).hexdigest()}
# Original observed assert reads sibling logs; copy current raw output only into scratch.
if a.name in ('old_request','old_policy'):
 (ROOT/'old_root'/('request_probe.stdout.jsonl' if a.name=='old_request' else 'policy_probe.stdout.jsonl')).write_text(result.stdout)
db_rows = {}
for p in script.parent.rglob('*.sqlite'):
 if 'source' in p.parts: continue
 con = sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
 tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
 db_rows[str(p.relative_to(ROOT))] = {n:[dict(r) for r in con.execute('SELECT * FROM '+n+' ORDER BY rowid')] for n in tables};con.close()
if db_rows:(out/'postexecution_db_rows.json').write_text(json.dumps(db_rows,ensure_ascii=False,indent=2)+'\n')
(out/'run.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'run':a.name,'exit_code':result.returncode,'elapsed_s':record['elapsed_s'],'stdout_lines':len(result.stdout.splitlines()),'evidence':str(out)},sort_keys=True))
