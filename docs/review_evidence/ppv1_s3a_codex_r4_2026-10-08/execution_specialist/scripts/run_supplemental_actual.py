#!/usr/bin/env python3
import os,json,subprocess,time,hashlib
from pathlib import Path
out=Path(__file__).resolve().parents[1];src=out/'current_source'
env=dict(os.environ)|{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(src/'src')+os.pathsep+str(src/'tests'),'BBD_DATA_ROOT':str(out/'empty_external_data'),'V3_CODE_ROOT':str(out/'absent_v3'),'DEPENDING_V3_ROOT':str(out/'absent_v3'),'V43_ASSET_ROOT':str(out/'absent_assets')}
rows=[]
for name,script,args in [('public_controls','public_controls.py',[str(out/'public_controls'),'r4']),('cx_writer_actual','cx_writer_actual.py',[]),('factory_r1','factory_r1_probe.py',[str(out/'factory_r1')])]:
 cmd=['/Users/cc/miniconda3/envs/depending43/bin/python','-B',str(out/'scripts'/script),*args];t=time.monotonic()
 with (out/(name+'.stdout.txt')).open('w') as so,(out/(name+'.stderr.txt')).open('w') as se:r=subprocess.run(cmd,cwd=src,env=env,stdout=so,stderr=se)
 rec={'name':name,'argv':cmd,'cwd':str(src),'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-t,'environment':{k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPATH','BBD_DATA_ROOT','V3_CODE_ROOT','DEPENDING_V3_ROOT','V43_ASSET_ROOT']},'stdout_sha256':hashlib.sha256((out/(name+'.stdout.txt')).read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((out/(name+'.stderr.txt')).read_bytes()).hexdigest()};rows.append(rec);(out/'supplemental_runs.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print(json.dumps(rec),flush=True)
 if r.returncode:raise RuntimeError(name+' failed')
