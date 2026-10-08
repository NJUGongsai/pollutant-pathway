from pathlib import Path
import json,sys,sqlite3,hashlib,traceback
iso=Path(sys.argv[1]);root=Path(sys.argv[2]);out=Path(sys.argv[3]);sys.path.insert(0,str(iso/'src'))
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.storage.artifact_store import ArtifactStore
from pathway_v43.pollutant.search import SearchLedger
from pathway_v43.pollutant.endpoint import consume_run_endpoint
from pathway_v43.pollutant.native_export import read_native_export
from pathway_v43.pollutant.v3_projection import read_v3_projection
from pathway_v43.pollutant.production import load_context
src=json.loads((root/'results.json').read_text());captured=[]
for case in src['cases']:
 name=case['case'];rd=root/'runs'/name;db=rd/'pollutant.sqlite'
 store=PollutantPathwayStore(db);a=ArtifactStore(root/'runs',name);ledger=SearchLedger(store,a,name)
 rows=ledger.conn.execute("SELECT DISTINCT context_ref FROM search_actions WHERE context_ref != '' ORDER BY context_ref").fetchall()
 contexts=[]
 for row in rows:
  c=load_context(a,row[0]);assessment=c.route_assessment()
  contexts.append({'ref':row[0],'payload':c.to_dict(),'route_assessment':assessment.to_dict()})
 endpoint=consume_run_endpoint(ledger,name)
 export=read_native_export(ledger,rd,case['resume']['native_export']['export_digest'])
 projection=read_v3_projection(rd,case['resume']['v3_projection']['projection_digest'])
 rec={'case':name,'contexts':contexts,'endpoint':endpoint,'native_export':export,'v3_projection':projection,'network_calls':src['network_connect_calls']}
 captured.append(rec)
 print(json.dumps({'case':name,'endpoint_assessment':endpoint['chemical_endpoint_assessment'],'context_assessments':[{'ref':c['ref'],'assessment':c['route_assessment']}for c in contexts],'export_endpoint':export['payload']['endpoint_record']['chemical_endpoint_assessment'],'projection_endpoint':projection['unprojectable_summaries'].get('chemical_endpoint_assessment')},ensure_ascii=False))
 store.close()
out.write_text(json.dumps(captured,ensure_ascii=False,indent=2,default=str))
