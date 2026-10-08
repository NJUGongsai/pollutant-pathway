#!/usr/bin/env python3
"""Copy fixed evidence into NEW temp; static syntax checked only this review."""
from pathlib import Path
import json,os,shutil,subprocess,tempfile
P=Path(__file__).resolve().parents[1];T=Path(tempfile.mkdtemp(prefix='ppv1_s3a_r4_budget_replay_',dir='/private/tmp'));PY='/Users/cc/miniconda3/envs/depending43/bin/python'
for name in ['source','scripts']:shutil.copytree(P/name,T/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.sqlite'))
(T/'evidence').mkdir();snapshot=json.loads((P/'evidence/input_snapshot.json').read_text());snapshot['metadata']['scratch']=str(T);snapshot['metadata']['execution_source']='frozen packaged r4 source; no live repo reads';(T/'evidence/input_snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n');env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
for name,script in [('contract','scripts/contract_probe.py'),('supplement','scripts/supplement.py'),('extra','scripts/extra_probe.py'),('legal_assembly','scripts/legal_assembly.py'),('sent_failed_control','scripts/sent_failed_control.py'),('full_status','scripts/full_table_status_probe.py'),('runtime','scripts/runtime.py'),('adjudicate_r4','scripts/adjudicate_r4.py')]:subprocess.run([PY,'-B',str(T/'scripts/run_recorded.py'),name,script],cwd=T,env=env,check=True)
print(json.dumps({'scratch':str(T),'note':'raw extra prep failure and history oracle preserved; adjudication only reads logs; actual_HEAD denotes frozen source version'},sort_keys=True))
