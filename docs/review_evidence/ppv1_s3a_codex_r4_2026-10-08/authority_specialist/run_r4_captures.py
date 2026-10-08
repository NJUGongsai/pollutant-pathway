from pathlib import Path
import subprocess,os,json,time,datetime
P=Path(__file__).resolve().parent;PY='/Users/cc/miniconda3/envs/depending43/bin/python';ENV=dict(os.environ,PYTHONPATH=str(P/'repo/src')+':'+str(P/'repo/tests'),PYTHONDONTWRITEBYTECODE='1')
items=[('necessary_reference',[PY,'-B',str(P/'necessary_reference_probe.py')]),('one_action_chain',[PY,'-B',str(P/'one_action_budget_chain_probe.py')]),('inheritance',[PY,'-B',str(P/'inheritance_as_executed.py'),'--out',str(P/'authority_cases')]),('segmented',[PY,'-B',str(P/'segmented_authority_probe.py')]),('done_result',[PY,'-B',str(P/'done_result_reuse_probe.py')]),('supplementary',[PY,'-B',str(P/'supplementary_probe.py')]),('defer_control',[PY,'-B',str(P/'defer_and_controls_probe.py')]),('crash',[PY,'-B',str(P/'crash_concurrency_as_executed.py')]),('old_observed',[PY,'-B',str(P/'probe_original.py')])]
logs=[]
for name,argv in items:
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();r=subprocess.run(argv,cwd=P/'repo',env=ENV,text=True,capture_output=True,timeout=180)
 (P/(name+'.stdout.jsonl')).write_text(r.stdout);(P/(name+'.stderr.txt')).write_text(r.stderr)
 item={'name':name,'argv':argv,'cwd':str(P/'repo'),'env':{k:ENV[k] for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE')},'exit':r.returncode,'elapsed_seconds':time.monotonic()-t,'timestamp_utc':started,'stdout':name+'.stdout.jsonl','stderr':name+'.stderr.txt'};logs.append(item);(P/'capture_commands.json').write_text(json.dumps(logs,indent=2)+'\n');print(json.dumps(item),flush=True)
