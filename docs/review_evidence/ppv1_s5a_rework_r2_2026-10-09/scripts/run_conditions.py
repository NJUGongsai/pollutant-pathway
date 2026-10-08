from pathlib import Path
import os,sys,subprocess,json,time,hashlib
R=Path(sys.argv[1]);P=R/'package';TREE=R/'current';label=sys.argv[2]
V3ROOT=Path(sys.argv[3])
env=dict(os.environ);pin={'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(TREE/'src'),'BBD_DATA_ROOT':str(V3ROOT.parent/'empty_external_data'),'V3_CODE_ROOT':str(V3ROOT),'DEPENDING_V3_ROOT':str(V3ROOT),'V43_ASSET_ROOT':str(TREE/'assets')};env.update(pin)
argv=['/Users/cc/miniconda3/envs/depending43/bin/python','-B',str(P/'scripts'/'mimo_conditions_probe.py'),str(R),'conditions']
log=P/'logs'/label;log.mkdir(exist_ok=False);before=time.monotonic()
with (log/'stdout.txt').open('w') as out,(log/'stderr.txt').open('w') as err:cp=subprocess.run(argv,cwd=TREE,env=env,stdout=out,stderr=err)
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
(log/'command.json').write_text(json.dumps({'argv':argv,'cwd':str(TREE),'env':pin,'exit_code':cp.returncode,'elapsed_seconds':time.monotonic()-before,'stdout_sha256':sha(log/'stdout.txt'),'stderr_sha256':sha(log/'stderr.txt')},indent=2)+'\n')
print(label,'exit',cp.returncode,'stdout',log/'stdout.txt',flush=True);sys.exit(cp.returncode)
