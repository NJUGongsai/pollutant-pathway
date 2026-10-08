from pathlib import Path
import json,os,subprocess,sys,time,datetime
pkg=Path(sys.argv[1]);label=sys.argv[2];argv=sys.argv[3:];t=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(argv,text=True,capture_output=True)
(pkg/'logs'/f'{label}.stdout').write_text(p.stdout);(pkg/'logs'/f'{label}.stderr').write_text(p.stderr)
meta={'argv':argv,'cwd':str(Path.cwd()),'exit':p.returncode,'start_utc':start,'elapsed_seconds':time.monotonic()-t,'env':{k:os.environ.get(k) for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPATH','BBD_DATA_ROOT','V43_ASSET_ROOT']}}
(pkg/'logs'/f'{label}.command.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta));print(p.stdout[-1400:]);print(p.stderr[-500:]);sys.exit(0)
