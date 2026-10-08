#!/usr/bin/env python3
"""Correct reviewer-only parent/worker v3 path mismatch; preserve initial attempts."""
import os,json,subprocess,time,xml.etree.ElementTree as ET,hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
PY='/Users/cc/miniconda3/envs/depending43/bin/python'
cmds=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
if not (OUT/'baseline_source').is_dir():raise RuntimeError('initial source copy not ready')
for label,root,files in [('ppv1_corrected',OUT/'current_source',sorted(str(p.relative_to(OUT/'current_source')) for p in (OUT/'current_source/tests').glob('test_ppv1*.py'))),('baseline_new_corrected',OUT/'baseline_source',['tests/test_ppv1_s3b_r2.py'])]:
 folder=OUT/label
 folder.mkdir(exist_ok=False)
 # Minimum-env worker resolve_config default is <isolated source parent>/dependingv3.
 # Use identical nonexistent/ordinary-code-only path in parent; no original data is read.
 env=dict(os.environ)|{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root/'src'),'BBD_DATA_ROOT':str(OUT/'empty_external_data'),'V3_CODE_ROOT':str(OUT/'dependingv3'),'DEPENDING_V3_ROOT':str(OUT/'dependingv3'),'V43_ASSET_ROOT':str(OUT/'absent_assets')}
 cmd=[PY,'-B','-m','pytest','-p','no:cacheprovider','-q','-rs','--junitxml',str(folder/'junit.xml'),'--basetemp',str(OUT/(label+'_pytest_tmp')),*files]
 t=time.monotonic()
 with (folder/'stdout.txt').open('w') as so,(folder/'stderr.txt').open('w') as se:r=subprocess.run(cmd,cwd=root,env=env,stdout=so,stderr=se)
 tree=ET.parse(folder/'junit.xml').getroot()
 ss=[tree] if tree.tag=='testsuite' else list(tree.findall('testsuite'))
 totals={k:sum(int(s.get(k,0)) for s in ss) for k in ['tests','errors','failures','skipped']};totals['passed']=totals['tests']-totals['errors']-totals['failures']-totals['skipped']
 cases=[]
 for c in tree.iter('testcase'):
  state=next((k for k in ['failure','error','skipped'] if c.find(k) is not None),'passed');row={'classname':c.get('classname'),'name':c.get('name'),'state':state}
  if state!='passed':n=c.find(state);row.update(message=n.get('message'),body=n.text)
  cases.append(row)
 dump(folder/'summary.json',{'totals':totals,'cases':cases,'exit_code':r.returncode})
 rec={'name':label,'argv':cmd,'cwd':str(root),'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-t,'environment':{k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPATH','BBD_DATA_ROOT','V3_CODE_ROOT','DEPENDING_V3_ROOT','V43_ASSET_ROOT']},'stdout_sha256':sha(folder/'stdout.txt'),'stderr_sha256':sha(folder/'stderr.txt'),'totals':totals}
 cmds.append(rec);dump(OUT/'corrected_execution_commands.json',cmds);print(json.dumps(rec),flush=True)
dump(OUT/'environment_correction.json',{'initial_ppv1_result':'861 passed, 10 failed; every failure stopped early at v3_engine_code IdentityMismatch','cause':'reviewer parent pinned absent_v3 vs subprocess worker clears environment and resolves sibling dependingv3','correction':'parent V3_CODE_ROOT/DEPENDING_V3_ROOT aligned to the same isolated default sibling path; production inputs/tests/source bytes unchanged','only_repeated':'PPV1 full to meet full-suite requirement and affected parent new20 set','unrepeated':'parent updated3 file set, G01 once','initial_logs_retained':True,'not_account_quota':True})
