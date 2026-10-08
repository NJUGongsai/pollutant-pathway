#!/usr/bin/env python3
"""Portable template, static-checked only; replay in another fresh /private/tmp."""
from pathlib import Path
import json,os,shutil,subprocess,tempfile
PACKAGE=Path(__file__).resolve().parents[1]
TARGET=Path(tempfile.mkdtemp(prefix='ppv1_s3a_budget_replay_',dir='/private/tmp'))
PY='/Users/cc/miniconda3/envs/depending43/bin/python'
for name in ['source','scripts','old_root','old_search','old_stop_input']:
 shutil.copytree(PACKAGE/name,TARGET/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.sqlite','generated*','runs','policy_runs','src','tests') if name=='old_root' else shutil.ignore_patterns('__pycache__','*.pyc','*.sqlite','generated*','repo','defer_bypass_generated'))
(TARGET/'old_root/src').symlink_to(TARGET/'source/src',target_is_directory=True)
(TARGET/'old_root/tests').symlink_to(TARGET/'source/tests',target_is_directory=True)
for name in ['old_search','old_stop_input']:(TARGET/name/'repo').symlink_to(TARGET/'source',target_is_directory=True)
(TARGET/'evidence').mkdir();snap=json.loads((PACKAGE/'evidence/input_snapshot.json').read_text());snap['metadata']['scratch']=str(TARGET);snap['metadata']['execution_source']='pinned packaged source snapshot; no live repo used';(TARGET/'evidence/input_snapshot.json').write_text(json.dumps(snap,ensure_ascii=False,indent=2)+'\n')
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
for name,script in [('old_request','old_root/request_probe.py'),('old_policy','old_root/policy_probe.py'),('old_defer','old_search/defer_budget_bypass.py'),('old_search_observed','old_search/probe.py'),('old_root_observed','old_root/assert_root_observed.py'),('old_stop_observed','old_stop_input/old_stop_observed.py'),('contract','scripts/contract_probe.py'),('supplement','scripts/supplement.py')]:
 subprocess.run([PY,'-B',str(TARGET/'scripts/run_recorded.py'),name,script],cwd=TARGET,env=env,check=True)
print(json.dumps({'scratch':str(TARGET),'note':'raw contract output preserves known audit oracle errors; use package adjudicated_summary and corrected supplement to interpret; no aggregate pass assertion'},sort_keys=True))
