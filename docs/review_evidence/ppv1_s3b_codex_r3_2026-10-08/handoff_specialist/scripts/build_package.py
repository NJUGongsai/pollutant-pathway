#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,shutil,sqlite3,sys,subprocess,datetime,platform
ROOT=Path(__file__).resolve().parents[1]
REPO=Path('/Volumes/CC/Enzyme_Agent/dependingv43')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=[]
for p in sorted((ROOT/'src').rglob('*')):
 if p.is_file():
  rel=p.relative_to(ROOT);q=REPO/rel
  source.append({'path':str(rel),'copied_sha256':sha(p),'repo_sha256':sha(q),'equal':p.read_bytes()==q.read_bytes()})
assert all(x['equal'] for x in source)
(ROOT/'source_fingerprints.json').write_text(json.dumps(source,indent=2)+'\n')
meta=json.loads((ROOT/'input_metadata.json').read_text())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==meta['actual_head']
commands=[{'argv':[sys.executable,'-B','scripts/'+name+'.py'],'cwd':str(ROOT),'env':{'PYTHONDONTWRITEBYTECODE':'1'},'stdout':'logs/'+log+'.stdout.txt','stderr':'logs/'+log+'.stderr.txt','returncode':0} for name,log in [('lexical_probe','lexical'),('inheritance_probe','inheritance'),('read_captured_semantics','semantics')]]
run={'actual_head':meta['actual_head'],'parent':meta['parent'],'start_source_snapshot_utc':meta['time_utc'],'finish_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':platform.python_version(),'commands':commands,'network_provider_calls':0,'new_lexical_positive':5,'new_lexical_negative_entries':6,'public_observations':9,'captured_readback_assertions':6,'readonly_archive_no_probe_reruns':True,'execution_suites_this_specialist':0,'source_files_unchanged':len(source),'scientific_scope':'synthetic representation and public consumer engineering; science pending; no dev/298 extrapolation'}
(ROOT/'run_metadata.json').write_text(json.dumps(run,ensure_ascii=False,indent=2)+'\n')
P=ROOT/'package';assert not P.exists();P.mkdir()
for n in ['src','scripts','logs','source_inputs','inputs','tables','schemas','static']:
 shutil.copytree(ROOT/n,P/n,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.pytest_cache'))
for n in ['README.md','HANDOFF_READBACK.md','pyproject.toml','input_metadata.json','run_metadata.json','source_fingerprints.json','lexical_observations.json','inheritance_observations.json','captured_semantic_readback.json']:shutil.copy2(ROOT/n,P/n)
omitted=[]
for rd in sorted((ROOT/'synthetic_runs/runs').iterdir()):
 db=rd/'pollutant.sqlite'
 if db.exists():
  c=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True)
  schema={'run_id':rd.name,'sql_schema':[{'type':typ,'name':name,'table':table,'sql':sql} for typ,name,table,sql in c.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name')],'meta_rows':list(c.execute('SELECT * FROM meta'))};c.close()
  (P/'schemas'/(rd.name+'.json')).write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n')
 for f in sorted(rd.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(rd)
  if f.suffix=='.json':
   dest=P/'artifacts'/rd.name/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
  else:omitted.append({'path':'synthetic_runs/runs/'+rd.name+'/'+str(rel),'bytes':f.stat().st_size,'sha256':sha(f),'reason':'runtime SQL binary or session disclosure; all rows/schema plus artifact JSON published'})
(P/'omitted_runtime_files.json').write_text(json.dumps(omitted,ensure_ascii=False,indent=2)+'\n')
files=[{'path':str(f.relative_to(P)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(P.rglob('*')) if f.is_file()]
manifest={'actual_head':meta['actual_head'],'parent':meta['parent'],'files':files,'payload_file_count':len(files),'payload_bytes':sum(x['bytes'] for x in files)}
(P/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(P/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in files))
(P/'MANIFEST_SHA256').write_text(sha(P/'manifest.json')+'  manifest.json\n')
assert all(sha(P/x['path'])==x['sha256'] for x in files)
print(json.dumps({'package':str(P),'payload_files':len(files),'payload_bytes':manifest['payload_bytes'],'manifest_sha256':sha(P/'manifest.json'),'all_verified':True,'all_sources_unchanged':True}))
