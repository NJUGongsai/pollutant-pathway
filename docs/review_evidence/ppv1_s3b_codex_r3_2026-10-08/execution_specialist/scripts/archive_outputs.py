#!/usr/bin/env python3
"""Archive already-completed synthetic pytest outputs, never execute tests."""
import base64,hashlib,json,shutil,sqlite3
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
D=OUT/'captured_pytest_outputs';D.mkdir(exist_ok=False)
entries=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def serial(v):return {'base64':base64.b64encode(v).decode()} if isinstance(v,bytes) else v
for folder in ['ppv1_pytest_tmp','baseline_new_regressions_pytest_tmp']:
    root=OUT/folder
    if not root.exists():continue
    for p in sorted(root.rglob('*')):
        if p.is_symlink():continue
        if not p.is_file():continue
        rel=p.relative_to(OUT).as_posix();record={'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)}
        head=p.open('rb').read(16)
        is_sqlite=head==b'SQLite format 3\x00'
        if is_sqlite:
            output={'source':record,'open_mode':'ro','tables':{}}
            try:
                con=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
                output['schema']=[dict(r) for r in con.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name")]
                for row in output['schema']:
                    table=row['name'];quoted='"'+table.replace('"','""')+'"'
                    output['tables'][table]=[{k:serial(v) for k,v in dict(r).items()} for r in con.execute('SELECT * FROM '+quoted)]
                con.close();output['read_succeeded']=True
            except Exception as exc:output.update(read_succeeded=False,error=type(exc).__name__,message=str(exc))
            dest=D/(rel+'.tables.json');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');record['archive']=dest.relative_to(OUT).as_posix();record['binary_omitted']=True
        elif p.suffix in ['.sqlite','.db','.sqlite-wal','.sqlite-shm'] or p.name.endswith(('-wal','-shm')):
            record['binary_omitted']=True
        else:
            dest=D/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);record['archive']=dest.relative_to(OUT).as_posix();record['binary_omitted']=False
        entries.append(record)
(OUT/'synthetic_pytest_artifacts.json').write_text(json.dumps({'scope':'only fresh scratch explicit pytest basetemp, already finished, no probe/test rerun; table JSON instead of SQLite binaries','files':entries},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'files':len(entries),'binary_omitted':sum(e['binary_omitted'] for e in entries),'archived':sum('archive' in e for e in entries),'bytes':sum(p.stat().st_size for p in D.rglob('*') if p.is_file())}))
