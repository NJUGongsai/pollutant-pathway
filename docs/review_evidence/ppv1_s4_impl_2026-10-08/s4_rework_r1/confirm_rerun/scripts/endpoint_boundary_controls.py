from pathlib import Path
import json,sys,socket,sqlite3,hashlib,traceback
iso=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=False);sys.path.insert(0,str(iso/'src'));sys.path.insert(0,str(iso/'tests'))
from test_ppv1_s4a_endpoint import spec,mineralization_evidence,ledger_for
from pathway_v43.config import resolve_config
from pathway_v43.workflow.runner import start_run
from pathway_v43.storage.run_identity import PROFILE_POLLUTANT_PATHWAY_V1
from pathway_v43.pollutant.endpoint import consume_run_endpoint
from pathway_v43.pollutant.native_export import read_native_export
from pathway_v43.pollutant.v3_projection import read_v3_projection
calls=[]
def no_network(self,address):calls.append(repr(address));raise RuntimeError('network disabled in review')
socket.socket.connect=no_network
base={'pools':{'CCO':[spec('B','CC=O','donor-B')]}}; ev=mineralization_evidence();dup=dict(ev,source_refs=['src:study-A','src:study-A']);other=mineralization_evidence('src:study-B');model=dict(ev,evidence_basis='model_prediction');incomplete=dict(ev,root_carbon_fate_check_scope='')
cases=[('f01_zero_actions_no_evidence',base,{'search_limits':{'max_total_search_actions':0}},'unknown',0),('f01_zero_actions_valid_evidence',dict(base,endpoint_evidence=[ev]),{'search_limits':{'max_total_search_actions':0}},'supported_mineralization',1),('f03_duplicate_reference_wrappers',dict(base,endpoint_evidence=[ev,dup]),None,'supported_mineralization',1),('f03_distinct_sources_with_model_repeat',dict(base,endpoint_evidence=[ev,other,model,model]),None,'supported_mineralization',2),('endpoint_missing_root_carbon_scope',dict(base,endpoint_evidence=[incomplete]),None,'unknown',1)]
records=[]
for name,plan,policy,expected,count in cases:
 result={'case':name,'plan':plan,'profile_policy':policy,'expected_assessment':expected,'expected_source_count':count}
 try:
  actual=start_run(config=resolve_config(),runs_root=out/'runs',run_id=name,smiles='CCO',max_depth=3,max_expansions=10,max_frontier_width=2,finder=object(),scripted=True,profile=PROFILE_POLLUTANT_PATHWAY_V1,ppv1_plan=plan,profile_policy=policy);result['start']=actual
  ledger=ledger_for(out/'runs',name);endpoint=consume_run_endpoint(ledger,name); native=read_native_export(ledger,out/'runs'/name,actual['native_export']['export_digest']);projection=read_v3_projection(out/'runs'/name,actual['v3_projection']['projection_digest']);result.update(endpoint=endpoint,native_export=native,v3_projection=projection)
  result['tables']={r[0]:[dict(v)for v in ledger.conn.execute('SELECT * FROM "'+r[0]+'"')]for r in ledger.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")};ledger.store.close();db=out/'runs'/name/'pollutant.sqlite';result['omitted_database_sha256']=hashlib.sha256(db.read_bytes()).hexdigest()
  assert endpoint['chemical_endpoint_assessment']==expected
  assert endpoint['evidence_summary']['independent_source_support_count']==count
  assert native['payload']['endpoint_record']['chemical_endpoint_assessment']==expected
  assert projection['unprojectable_summaries']['endpoint_assessment']==expected
  if name.startswith('f01'):
   assert actual['counts']['events']==0 and endpoint['search_stop_reason']['primary']=='budget_limit'
  if name=='f03_duplicate_reference_wrappers':
   assert endpoint['evidence_summary']['distinct_observation_claims']==1 and len(endpoint['endpoint_evidence'])==2
  if name=='f03_distinct_sources_with_model_repeat':
   assert len(endpoint['endpoint_evidence'])==4 and endpoint['evidence_summary']['basis_counts']['model_prediction']==1
  if name=='endpoint_missing_root_carbon_scope':
   assert endpoint['evidence_summary']['missing_field_disclosures'][0]['missing_fields']==['root_carbon_fate_check_scope']
  result['assertions_passed']=True
 except Exception as exc:
  result['exception']={'class':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};result['assertions_passed']=False
 records.append(result);print(json.dumps({'case':name,'assertions_passed':result['assertions_passed'],'assessment':result.get('endpoint',{}).get('chemical_endpoint_assessment'),'sources':result.get('endpoint',{}).get('evidence_summary',{}).get('independent_source_support_count'),'exception':result.get('exception')},ensure_ascii=False))
(out/'results.json').write_text(json.dumps({'network_calls':calls,'cases':records},ensure_ascii=False,indent=2,default=str));assert calls==[];assert all(r['assertions_passed']for r in records)
