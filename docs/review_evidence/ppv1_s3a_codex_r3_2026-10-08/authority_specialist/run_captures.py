from pathlib import Path
import subprocess,sys,os,json,time,datetime
P=Path(__file__).resolve().parent;PY='/Users/cc/miniconda3/envs/depending43/bin/python'
ENV=dict(os.environ,PYTHONPATH=str(P/'repo/src')+':'+str(P/'repo/tests'),PYTHONDONTWRITEBYTECODE='1')
items=[('inheritance',[PY,'-B',str(P/'inheritance_as_executed.py'),'--out',str(P/'authority_cases')]),('segmented',[PY,'-B',str(P/'segmented_authority_probe.py')]),('done_result',[PY,'-B',str(P/'done_result_reuse_probe.py')]),('supplementary',[PY,'-B',str(P/'supplementary_probe.py')]),('crash',[PY,'-B',str(P/'crash_concurrency_as_executed.py')]),('old_observed',[PY,'-B',str(P/'probe_original.py')])]
logs=[]
for name,argv in items:
 start=time.monotonic();r=subprocess.run(argv,cwd=P/'repo',env=ENV,text=True,capture_output=True,timeout=180)
 (P/(name+'.stdout.jsonl')).write_text(r.stdout);(P/(name+'.stderr.txt')).write_text(r.stderr)
 log={'name':name,'argv':argv,'cwd':str(P/'repo'),'env':{k:ENV[k] for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE')},'exit':r.returncode,'elapsed':time.monotonic()-start,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stdout':name+'.stdout.jsonl','stderr':name+'.stderr.txt'};logs.append(log);print(json.dumps(log),flush=True)
 (P/'capture_commands.json').write_text(json.dumps(logs,indent=2)+'\n')
