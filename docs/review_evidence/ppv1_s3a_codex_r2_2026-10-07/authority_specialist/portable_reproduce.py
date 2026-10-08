#!/usr/bin/env python3
"""Static-only new portable controller; reproduce this historical HEAD in a NEW tmp."""
import tempfile,shutil,subprocess,sys,os,json
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
DEST=Path(tempfile.mkdtemp(prefix='ppv1_s3a_r2_authority_repro_',dir='/private/tmp'))
shutil.copytree(SOURCE/'repo',DEST/'repo')
shutil.copytree(SOURCE/'old_scripts',DEST/'old_scripts')
for name in ['inheritance_as_executed.py','crash_concurrency_as_executed.py','probe_original.py',
             'segmented_authority_probe.py','portable_supplementary_probe.py','done_result_reuse_probe.py','assert_current_capture.py']:
    shutil.copy2(SOURCE/name,DEST/name)
ENV=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(DEST/'repo/src')+':'+str(DEST/'repo/tests'))
records=[]
items=[('inheritance',[sys.executable,'-B',str(DEST/'inheritance_as_executed.py'),'--out',str(DEST/'authority_cases')]),
       ('crash',[sys.executable,'-B',str(DEST/'crash_concurrency_as_executed.py')]),
       ('old_probe_observed',[sys.executable,'-B',str(DEST/'probe_original.py')]),
       ('segmented',[sys.executable,'-B',str(DEST/'segmented_authority_probe.py')]),
       ('supplementary',[sys.executable,'-B',str(DEST/'portable_supplementary_probe.py')]),
       ('done_result_reuse',[sys.executable,'-B',str(DEST/'done_result_reuse_probe.py')])]
for name,argv in items:
    r=subprocess.run(argv,cwd=DEST/'repo',env=ENV,text=True,capture_output=True,timeout=180)
    (DEST/(name+'.stdout.jsonl')).write_text(r.stdout);(DEST/(name+'.stderr.txt')).write_text(r.stderr)
    records.append({'name':name,'argv':argv,'cwd':str(DEST/'repo'),'returncode':r.returncode})
shutil.copy2(DEST/'inheritance.stdout.jsonl',DEST/'inheritance_v2.stdout.jsonl')
argv=[sys.executable,'-B',str(DEST/'old_scripts/inheritance_specialist/assert_observed.py'),'--root',str(DEST)]
r=subprocess.run(argv,cwd=DEST/'repo',env=ENV,text=True,capture_output=True,timeout=30)
(DEST/'old_inheritance_observed.stdout.jsonl').write_text(r.stdout);(DEST/'old_inheritance_observed.stderr.txt').write_text(r.stderr)
records.append({'name':'old_inheritance_observed','argv':argv,'cwd':str(DEST/'repo'),'returncode':r.returncode})
argv=[sys.executable,'-B',str(DEST/'assert_current_capture.py')]
r=subprocess.run(argv,cwd=DEST/'repo',env=ENV,text=True,capture_output=True,timeout=30)
(DEST/'assert_current_capture.stdout.jsonl').write_text(r.stdout);(DEST/'assert_current_capture.stderr.txt').write_text(r.stderr)
records.append({'name':'assert_current_capture','argv':argv,'cwd':str(DEST/'repo'),'returncode':r.returncode})
(DEST/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps({'fresh_root':str(DEST),'commands':records}))
