#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,shutil,datetime,sqlite3,sys,subprocess
ROOT=Path(__file__).resolve().parents[1];REPO=Path('/Volumes/CC/Enzyme_Agent/dependingv43')
P=ROOT/'package';P.mkdir(exist_ok=True)
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False,sort_keys=True))
for n in ('src','scripts','inputs','logs','tables','source_inputs'):
 shutil.copytree(ROOT/n,P/n,ignore=shutil.ignore_patterns('__pycache__','*.pyc'),dirs_exist_ok=True)
for n in ('input_metadata.json','observations.json','supplemental_observations.json','legal_unknown_observations.json'):
 shutil.copy2(ROOT/n,P/n)
for n in ('POLLUTANT_PATHWAY_S3B_DELIVERY_R2_2026-10-08.md','mimo_ppv1_chem_review_response_r14.md','POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_2026-10-08.md','POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md','mimo_ppv1_chem_review_request.md'):
 shutil.copy2(REPO/'docs'/n,P/'source_inputs'/n)
# Preserve exact current synthetic artifact inputs/outputs and read-only schema, not opaque SQLite binaries.
omitted=[]
for run in sorted((ROOT/'synthetic_runs/runs').iterdir()):
 if not run.is_dir():continue
 db=run/'pollutant.sqlite'
 if db.exists():
  con=sqlite3.connect(f'file:{db}?mode=ro',uri=True)
  rows=con.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
  dump(P/'schemas'/(run.name+'.json'),[dict(zip(('type','name','tbl_name','sql'),x)) for x in rows]);con.close()
 for f in sorted(run.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(ROOT)
  if f.suffix in ('.json',) or f.name=='driver.lock':
   dst=P/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
  else:omitted.append({'path':str(rel),'bytes':f.stat().st_size,'sha256':h(f),'reason':'synthetic runtime DB/sidecar excluded; all SQL tables captured as JSON'})
dump(P/'omitted_runtime_files.json',omitted)
# Static readback anchors support Mimo mutual confirmation without unrun execution claims.
anchors={
 'src/pathway_v43/pollutant/runflow.py':[(211,321),(364,440),(512,556),(566,604),(648,828),(919,986),(1350,1391)],
 'src/pathway_v43/pollutant/production.py':[(174,208),(260,307),(392,416)],
 'src/pathway_v43/pollutant/model_protocol.py':[(188,216)],
 'src/pathway_v43/pollutant/search.py':[(1078,1153),(1155,1224),(2995,3064),(3170,3235)],
 'src/pathway_v43/pollutant/queue.py':[(222,260)],
 'src/pathway_v43/pollutant/audit.py':[(628,683),(973,1014),(1185,1210),(2544,2573),(2702,2713),(2980,2993)],
 'src/pathway_v43/pollutant/store.py':[(1988,2040)],
 'src/pathway_v43/pollutant/path_context.py':[(797,846),(1550,1661),(2080,2158)],
 'src/pathway_v43/workflow/runner.py':[(214,228),(305,320)]}
rb=[]
for f,spans in anchors.items():
 lines=(REPO/f).read_text().splitlines();rb.append({'path':f,'sha256':h(REPO/f),'sections':[{'start':a,'end':b,'numbered_lines':'\n'.join(f'{i}: {lines[i-1]}' for i in range(a,min(b,len(lines))+1))}for a,b in spans]})
dump(P/'static_readback.json',rb)
meta=json.loads((ROOT/'input_metadata.json').read_text());after=[]
for x in meta['copied_sources']:
 file=REPO/'src'/x['path'];after.append({'path':x['path'],'before_sha256':x['sha256'],'after_sha256':h(file),'unchanged':h(file)==x['sha256']})
assert all(x['unchanged'] for x in after)
requests=[]
for file in sorted((P/'logs').glob('*.execution.json')):
 v=json.loads(file.read_text());requests.append({'path':str(file.relative_to(P)),'command':v['command'],'environment':v['environment'],'returncode':v['returncode']})
# controller reused label old_zero_depth, exact initial stop/counts survives observations/stdout; repeat execution file overwrote old start file.
rootobs=json.loads((ROOT/'observations.json').read_text());zero=next(o for o in rootobs if o['case']=='zero_depth_persisted_disclosure')
dump(P/'zero_depth_initial_extraction.json',{'source':'controller stdout and observations before resume; extracted read-only','initial_observation':zero,'capture_limit':'initial old_zero_depth child stdout/execution/trace/table filenames reused by repeat-resume; last files represent resume, initial detail preserved here and controller stdout. Do not count those files as two separate receipts.'})
metadata={'head':meta['head'],'parent':meta['parent'],'started_utc':meta['utc'],'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'sqlite':sqlite3.sqlite_version,'source_unchanged':after,'execution_receipts':requests,'behavior_child_count':21,'observations_raw':{'main':len(rootobs),'main_true':sum(x['check'] for x in rootobs),'supplemental':4,'supplemental_raw_false':1,'legal_unknown':2},'observer_issues':['supplemental field oracle KeyError after second child; read-only correction, no completed child rerun','unresolved alignment is outside enum; no unknown-path claim, separate unavailable legal fixture executed','zero_depth resume reused receipt label; initial detail in extraction and controller stdout'], 'network':'socket connect/create_connection blocked in worker; all captured traces network_attempts=[]','forbidden_actions':'no external model/gold/question/sealed run/source edits/pytest/push','evidence_database_policy':'all tables in snapshots; read-only schema; runtime DB omitted with hashes'}
dump(P/'run_metadata.json',metadata)
files=[]
for f in sorted(P.rglob('*')):
 if f.is_file() and f.name not in ('manifest.json','SHA256SUMS'):
  files.append({'path':str(f.relative_to(P)),'bytes':f.stat().st_size,'sha256':h(f)})
dump(P/'manifest.json',{'head':meta['head'],'parent':meta['parent'],'files':files,'payload_file_count':len(files)})
(P/'SHA256SUMS').write_text(''.join(f"{x['sha256']}  {x['path']}\n" for x in files)+f"{h(P/'manifest.json')}  manifest.json\n")
print(json.dumps({'package':str(P),'payload_files':len(files),'payload_bytes':sum(x['bytes'] for x in files),'manifest_sha256':h(P/'manifest.json'),'SHA256SUMS_sha256':h(P/'SHA256SUMS'),'all_source_unchanged':True}))
