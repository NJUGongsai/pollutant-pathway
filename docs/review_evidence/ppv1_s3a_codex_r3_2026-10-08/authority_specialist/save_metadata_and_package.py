#!/usr/bin/env python3
from pathlib import Path
import os,json,sys,hashlib,subprocess,sqlite3,shutil,datetime
P=Path(__file__).resolve().parent;R=Path('/Volumes/CC/Enzyme_Agent/dependingv43');sys.path[:0]=[str(P/'repo/src'),str(P/'repo/tests')]
from rdkit import rdBase
from pathway_v43.pollutant import profile
original=json.loads((P/'source_inputs.json').read_text());current={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in original['source']};assert current==original['source'];head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();parent=subprocess.check_output(['git','rev-parse','HEAD^'],cwd=R,text=True).strip();assert head==original['head'] and parent==original['parent'];(P/'final_source_integrity.json').write_text(json.dumps({'head':head,'parent':parent,'source_files':len(current),'all_source_bytes_unchanged':True,'source_sha256':current,'local_src_matches':all(hashlib.sha256((P/'repo'/p).read_bytes()).hexdigest()==v for p,v in current.items()),'bytecode_files':list(str(p.relative_to(P)) for p in P.rglob('*.pyc')),'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
conn=sqlite3.connect('file:'+str(P/'necessary_reference_cases/first_complete__clean__max_total_search_actions/run.sqlite')+'?mode=ro',uri=True);conn.row_factory=sqlite3.Row
schema={'meta':[dict(r) for r in conn.execute('SELECT * FROM meta')],'sqlite_master':[dict(r) for r in conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name")],'sqlite_user_version':conn.execute('PRAGMA user_version').fetchone()[0]};conn.close()
(P/'runtime_schema.json').write_text(json.dumps({'python':sys.version,'executable':sys.executable,'rdkit':rdBase.rdkitVersion,'sqlite':sqlite3.sqlite_version,'versions':{k:getattr(profile,k) for k in ('PPV1_PROFILE_SCHEMA_VERSION','PPV1_SEARCH_SCHEMA_VERSION','PPV1_STORE_SCHEMA_VERSION','SEARCH_LIMITS_VERSION')},'schema':schema,'head':head,'parent':parent,'isolated_source_root':str(P/'repo'),'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
# Exclude only generated local DB binaries (all cases have full JSON inputs/outputs;
# schema and synthetic DB SHA retained); other artifact envelopes and logs kept.
omitted=[]
for p in sorted(P.rglob('*')):
 if p.is_file() and (p.suffix in ('.sqlite','.db') or p.name.endswith(('.sqlite-wal','.sqlite-shm','.db-wal','.db-shm','.sqlite-journal'))):omitted.append({'path':str(p.relative_to(P)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'reason':'synthetic binary omitted; complete JSON table snapshots, input and schema retained'})
(P/'omitted_databases.json').write_text(json.dumps(omitted,indent=2)+'\n')
Q=P/'package';Q.mkdir(exist_ok=False)
for p in sorted(P.rglob('*')):
 rel=p.relative_to(P)
 if rel.parts[0]=='package' or not p.is_file() or any(p==P/r['path'] for r in omitted) or '__pycache__' in rel.parts or p.suffix=='.pyc':continue
 assert not p.is_symlink();dst=Q/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
print(json.dumps({'package':str(Q),'omitted_synthetic_DB_count':len(omitted),'copied_files':sum(p.is_file() for p in Q.rglob('*')),'bytes':sum(p.stat().st_size for p in Q.rglob('*') if p.is_file())}))
