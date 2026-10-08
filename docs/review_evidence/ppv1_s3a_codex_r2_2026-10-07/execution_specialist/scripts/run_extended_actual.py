#!/usr/bin/env python3
import os,json,subprocess,time,hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
PY='/Users/cc/miniconda3/envs/depending43/bin/python'
records=[]
for tag in ['baseline','current']:
    root=OUT/(tag+'_source');folder=OUT/(tag+'_extended')
    env=dict(os.environ)|{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root/'src'),'BBD_DATA_ROOT':str(OUT/'empty_external_data'),
        'V3_CODE_ROOT':str(OUT/'absent_v3'),'DEPENDING_V3_ROOT':str(OUT/'absent_v3'),'V43_ASSET_ROOT':str(OUT/'absent_assets')}
    cmd=[PY,'-B',str(OUT/'scripts/extended_controls.py'),str(folder),tag];start=time.monotonic()
    with (OUT/(tag+'_extended.stdout.txt')).open('w') as so,(OUT/(tag+'_extended.stderr.txt')).open('w') as se:
        r=subprocess.run(cmd,cwd=root,env=env,stdout=so,stderr=se)
    record={'tag':tag,'argv':cmd,'cwd':str(root),'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-start,
        'environment':{k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPATH','BBD_DATA_ROOT','V3_CODE_ROOT','DEPENDING_V3_ROOT','V43_ASSET_ROOT']},
        'stdout_sha256':hashlib.sha256((OUT/(tag+'_extended.stdout.txt')).read_bytes()).hexdigest(),
        'stderr_sha256':hashlib.sha256((OUT/(tag+'_extended.stderr.txt')).read_bytes()).hexdigest()}
    records.append(record);(OUT/'extended_commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    if r.returncode:raise RuntimeError(tag+' extended controls failed')
