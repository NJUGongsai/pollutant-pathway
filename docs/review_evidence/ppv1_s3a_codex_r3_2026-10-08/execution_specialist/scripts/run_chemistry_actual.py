#!/usr/bin/env python3
import os,json,subprocess,time,hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];root=OUT/'current_source'
env=dict(os.environ)|{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root/'src')+os.pathsep+str(root/'tests'),
    'BBD_DATA_ROOT':str(OUT/'empty_external_data'),'V3_CODE_ROOT':str(OUT/'absent_v3'),'DEPENDING_V3_ROOT':str(OUT/'absent_v3'),'V43_ASSET_ROOT':str(OUT/'absent_assets')}
cmd=['/Users/cc/miniconda3/envs/depending43/bin/python','-B',str(OUT/'scripts/chemistry_static_probe_adapted.py'),
     '--inputs',str(OUT/'chemistry_inputs'),'--out',str(OUT/'chemistry_probe')]
start=time.monotonic()
with (OUT/'chemistry_probe.stdout.jsonl').open('w') as so,(OUT/'chemistry_probe.stderr.txt').open('w') as se:
    r=subprocess.run(cmd,cwd=root,env=env,stdout=so,stderr=se)
record={'argv':cmd,'cwd':str(root),'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-start,
    'environment':{k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPATH','BBD_DATA_ROOT','V3_CODE_ROOT','DEPENDING_V3_ROOT','V43_ASSET_ROOT']},
    'stdout_sha256':hashlib.sha256((OUT/'chemistry_probe.stdout.jsonl').read_bytes()).hexdigest(),
    'stderr_sha256':hashlib.sha256((OUT/'chemistry_probe.stderr.txt').read_bytes()).hexdigest()}
(OUT/'chemistry_probe.run.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print(json.dumps(record))
if r.returncode:raise RuntimeError('chemistry probe failed')
