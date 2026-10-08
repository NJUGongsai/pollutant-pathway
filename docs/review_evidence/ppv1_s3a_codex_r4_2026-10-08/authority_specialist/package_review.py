#!/usr/bin/env python3
from pathlib import Path
import os,json,sys,hashlib,subprocess,sqlite3,shutil,datetime
P=Path(__file__).resolve().parent;R=Path('/Volumes/CC/Enzyme_Agent/dependingv43');sys.path[:0]=[str(P/'repo/src'),str(P/'repo/tests')]
from rdkit import rdBase
from pathway_v43.pollutant import profile
original=json.loads((P/'source_inputs.json').read_text());current={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in original['source']};assert current==original['source'];head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();parent=subprocess.check_output(['git','rev-parse','HEAD^'],cwd=R,text=True).strip();assert head==original['head'] and parent==original['parent'];assert all(hashlib.sha256((P/'repo'/p).read_bytes()).hexdigest()==v for p,v in current.items())
(P/'final_source_integrity.json').write_text(json.dumps({'head':head,'parent':parent,'source_files':len(current),'all_source_bytes_unchanged':True,'source_sha256':current,'local_src_matches':True,'bytecode_files':[str(p.relative_to(P)) for p in P.rglob('*.pyc')],'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
conn=sqlite3.connect('file:'+str(P/'necessary_reference_cases/first_complete__clean__max_total_search_actions/run.sqlite')+'?mode=ro',uri=True);conn.row_factory=sqlite3.Row
schema={'meta':[dict(r) for r in conn.execute('SELECT * FROM meta')],'sqlite_master':[dict(r) for r in conn.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name')],'sqlite_user_version':conn.execute('PRAGMA user_version').fetchone()[0]};conn.close()
(P/'runtime_schema.json').write_text(json.dumps({'python':sys.version,'executable':sys.executable,'rdkit':rdBase.rdkitVersion,'sqlite':sqlite3.sqlite_version,'versions':{k:getattr(profile,k) for k in ('PPV1_PROFILE_SCHEMA_VERSION','PPV1_SEARCH_SCHEMA_VERSION','PPV1_STORE_SCHEMA_VERSION','SEARCH_LIMITS_VERSION')},'schema':schema,'head':head,'parent':parent,'isolated_source_root':str(P/'repo'),'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
lines=(P/'repo/src/pathway_v43/pollutant/search.py').read_text().splitlines();(P/'search_source_excerpts.txt').write_text('\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines) if (570<=i+1<=584 or 973<=i+1<=987 or 2018<=i+1<=2083))+'\n')
(P/'preparation_notes.json').write_text(json.dumps({'readonly_stat_output_serializer_error':{'action':'Counter of tuple keys passed to json.dumps while inspecting saved necessary observations','exception':'TypeError: keys must be str, int, float, bool or None, not tuple','side_effects':'none; no model code/test/probe executed','correction':'display existing saved observations as a list; never reran probes'},'inherited_last_assertion_expectation_errors':['done_result expects SearchIdentityConflict instead of actual SearchContractError after full two-case IO captured','upper1 expects original vulnerability commits2 instead of actual repaired commits1 after full two-case IO captured'],'account_quota_interruptions_this_specialist_turn':0,'test_or_probe_reruns':0},indent=2)+'\n')
omitted=[]
for p in sorted(P.rglob('*')):
 if p.is_file() and (p.suffix in ('.sqlite','.db') or p.name.endswith(('.sqlite-wal','.sqlite-shm','.db-wal','.db-shm','.sqlite-journal'))):omitted.append({'path':str(p.relative_to(P)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'reason':'synthetic binary omitted; complete JSON table snapshots, input and representative full schema retained; old crash/observed retain original six-table snapshots and full worker logs'})
(P/'omitted_databases.json').write_text(json.dumps(omitted,indent=2)+'\n')
Q=P/'package';Q.mkdir(exist_ok=False);excluded=set(r['path'] for r in omitted)
for p in sorted(P.rglob('*')):
 rel=p.relative_to(P)
 if rel.parts[0]=='package' or not p.is_file() or str(rel) in excluded or '__pycache__' in rel.parts or p.suffix=='.pyc':continue
 assert not p.is_symlink();dst=Q/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
entries=[{'path':str(p.relative_to(Q)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(Q.rglob('*')) if p.is_file()]
manifest={'review':'PPV1 S3a-r4 authority independent','date':'2026-10-08','head':head,'parent':parent,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':entries,'excluded':['manifest.json','SHA256SUMS','manifest.sha256'],'input_source_sha256_count':len(current),'file_count':len(entries),'bytes':sum(x['bytes'] for x in entries)}
(Q/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(Q/'SHA256SUMS').write_text(''.join(f"{x['sha256']}  {x['path']}\n" for x in entries));mh=hashlib.sha256((Q/'manifest.json').read_bytes()).hexdigest();(Q/'manifest.sha256').write_text(mh+'  manifest.json\n')
for x in entries:assert hashlib.sha256((Q/x['path']).read_bytes()).hexdigest()==x['sha256']
print(json.dumps({'package':str(Q),'manifest_field':'files list path/bytes/sha256','payload_files':len(entries),'payload_bytes':manifest['bytes'],'manifest_sha256':mh,'full_source_input_files':len(current),'omitted_synthetic_DB_count':len(omitted),'all_package_sha_verified':True}))
