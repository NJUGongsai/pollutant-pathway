"""Copy to a new temporary output and reproduce synthetic R5 evidence only."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from rdkit import rdBase

p=argparse.ArgumentParser()
p.add_argument('--repo',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
bundle=Path(__file__).resolve().parent
a.out.mkdir(parents=True,exist_ok=True)
if any(a.out.iterdir()):raise RuntimeError('Output must be a new empty temporary directory')
shutil.copytree(a.repo/'src',a.out/'src',ignore=shutil.ignore_patterns('__pycache__'))
testdir=a.out/'tests';testdir.mkdir()
for test in sorted((a.repo/'tests').glob('test_ppv1*.py')):shutil.copyfile(test,testdir/test.name)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(a.out/'src'))
metadata={'reviewed_head':'293bc627f57b1f778aa433750f7f61d00b4a9d18',
 'actual_head':subprocess.check_output(['git','-C',str(a.repo),'rev-parse','HEAD'],text=True).strip(),
 'python':sys.version,'rdkit':rdBase.rdkitVersion,'test_files':len(list(testdir.glob('*.py')))}
(a.out/'run_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
jobs=[
 ('admission_coverage_probe.py','admission_coverage_probe.output.jsonl',None),
 ('r4_admission_probe_recheck.py','r4_admission_probe_recheck.output.jsonl',None),
 ('chemistry_boundary_probe.py','chemistry_boundary_probe.output.jsonl',None),
 ('r4_chemistry_probe.py','r4_chemistry_probe.output.jsonl',None),
 ('r3_chemistry_probe.py','r3_chemistry_probe.output.jsonl',None),
 ('conditions_probe.py','conditions_probe.summary.json','conditions_probe.results.json'),
 ('r4_conditions_probe.py','r4_conditions_probe.summary.json','r4_conditions_probe.results.json'),
 ('storage_boundary_probe.py','storage_boundary_probe.output.jsonl',None),
 ('r4_storage_probe.py','r4_storage_probe.output.jsonl',None),
 ('r3_storage_probe.py','r3_storage_probe.output.jsonl',None),
]
for script,output,result in jobs:
 lane=a.out/Path(script).stem;lane.mkdir()
 shutil.copyfile(bundle/script,lane/script)
 if script=='r4_admission_probe_recheck.py':shutil.copyfile(bundle/'r4_admission_probe.py',lane/'r4_admission_probe.py')
 with (a.out/output).open('w') as stdout,(a.out/(Path(script).stem+'.stderr.txt')).open('w') as stderr:
  subprocess.run([sys.executable,'-B',str(lane/script)],cwd=lane,env=env,stdout=stdout,stderr=stderr,check=True)
 if result:shutil.copyfile(lane/'results.json',a.out/result)
 print('completed',script,flush=True)
with (a.out/'pytest_output.txt').open('w') as stdout:
 subprocess.run([sys.executable,'-B','-m','pytest','-p','no:cacheprovider','-q','-rs','tests'],cwd=a.out,env=env,stdout=stdout,stderr=subprocess.STDOUT,check=True)
shutil.copyfile(bundle/'assert_observed.py',a.out/'assert_observed.py')
subprocess.run([sys.executable,'-B',str(a.out/'assert_observed.py')],cwd=a.out,env=env,check=True)
print('completed ppv1 and observation checks',flush=True)
