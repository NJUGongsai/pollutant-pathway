#!/usr/bin/env python3
"""R3 finite inherited policy-consumption and request-lifecycle boundary controls."""
from pathlib import Path
import copy,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'source/src'),str(ROOT/'source/tests')]
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.search import SearchLedger,search_policy_version
from pathway_v43.pollutant.store import PollutantPathwayStore
from s3a_worker import make_fixture
D=ROOT/'extra_data';D.mkdir(exist_ok=False)
TABLES=['search_runs','search_actions','search_attempts','budget_reservations','model_requests','search_commit_records','events'];OUT=[]
def rows(l):return {t:[dict(r) for r in l.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in TABLES}
def cap(f):
 try:return {'accepted':True,'result':f()}
 except Exception as e:return {'accepted':False,'exception':type(e).__name__,'kind':getattr(e,'detail',{}).get('kind'),'detail':getattr(e,'detail',{}),'message':str(e)}
def emit(row):OUT.append(row);print(json.dumps(row,ensure_ascii=False,sort_keys=True,default=str),flush=True)
def fixture(name,limits=None,kind='expand_hypothesis'):
 d=D/name;d.mkdir();s=PollutantPathwayStore(d/'run.sqlite');l=SearchLedger(s,None,name);p=build_profile_identity_block(search_limits=limits);l.register_search_run(name,p);_,_,h,e,args=make_fixture(name,'p1','k1','ctx1');a=l.enqueue_action(run_id=name,parent_path_id='p1',context_ref='ctx1',subject_ref=h.hypothesis_id if kind=='expand_hypothesis' else 'pool_A',action_kind=kind,policy_version=search_policy_version(),payload={'task_key':'task_'+name,'frozen_pool_digest':'pool_A'},depth=1)['action_id'];r=l.claim_action(a,worker_id='w');att=r['attempt_refs'][0] if r['attempt_refs'] else '';return s,l,p,a,att

def reg(l,a,att):return l.register_model_request(run_id=l.run_id,action_id=a,attempt_id=att,provider_kind='scripted',request_key='rk',payload={'prompt':'original'},purpose='rank')
def mutate(l,sql,args):l.conn.execute(sql,args);l.conn.commit()
def statusfn(l,r,entry):return {'sent':lambda:l.record_request_sent(r['request_id']),'response':lambda:l.record_request_response(r['request_id'],'response_A'),'failed':lambda:l.mark_request_failed(r['request_id'])}[entry]
# All inputs registered lawfully first; only the already frozen policy is damaged.
for damage in ['null_limits','missing_version','bool','out_of_range','unknown_key','negative','legal']:
 for entry in ['sent','response','failed']:
  name='policy_request_'+damage+'_'+entry;s,l,p,a,att=fixture(name);r=reg(l,a,att)
  if entry=='response':l.record_request_sent(r['request_id'])
  frozen=copy.deepcopy(p)
  if damage=='null_limits':p['search_limits']=None
  elif damage=='missing_version':del p['search_limits']['version']
  elif damage=='bool':p['search_limits']['max_total_search_actions']=True
  elif damage=='out_of_range':p['search_limits']['max_total_search_actions']=1001
  elif damage=='unknown_key':p['search_limits']['unregistered_key']=1
  elif damage=='negative':p['search_limits']['max_total_search_actions']=-1
  if damage!='legal':mutate(l,'UPDATE search_runs SET policy_block=? WHERE run_id=?',(json.dumps(p),name))
  b=rows(l);o=cap(statusfn(l,r,entry));af=rows(l);expected='accepted lawful local lifecycle' if damage=='legal' else 'structured policy rejection before any success write'
  ck={'accepted':o['accepted'],'network_zero':all(x['network_request_count']==0 for x in af['model_requests'])} if damage=='legal' else {'rejected':not o['accepted'],'policy_guard':not o['accepted'] and o.get('kind')=='search_policy_block_corrupt','zero_writes':b==af}
  emit({'case':name,'group':'S3A-03','expected':expected,'input':{'original_frozen_policy':frozen,'stored_policy':p,'damage':damage,'entry':entry,'request':r},'before':b,'observed':o,'after':af,'checks':ck,'contract_passed':all(ck.values()),'actual_network_requests':0});s.close()
# Same legal request row, enum-foreign status: each consumer is tested in isolation.
for entry in ['sent','response','failed','register','recover']:
 name='unknown_status_'+entry;s,l,p,a,att=fixture(name);r=reg(l,a,att);mutate(l,'UPDATE model_requests SET status=? WHERE request_id=?',('corrupt-status',r['request_id']));b=rows(l)
 f=statusfn(l,r,entry) if entry in ['sent','response','failed'] else (lambda:reg(l,a,att)) if entry=='register' else (lambda:l.recover_run(name));o=cap(f);af=rows(l)
 emit({'case':name,'group':'S3A-04','expected':'unknown stored lifecycle may be rejected or preserved as explicit integrity failure, never migrated to a successful known state','input':{'mutation':'model_requests.status=corrupt-status','entry':entry,'same_original_request':r},'before':b,'observed':o,'after':af,'checks':{'rejected':not o['accepted'],'zero_writes':b==af,'network_zero':all(x['network_request_count']==0 for x in af['model_requests'])},'actual_network_requests':0});s.close()
# Explicit delivered boundary: stored request run points elsewhere, never broadens a successful execution right.
for entry in ['sent','response','failed','register','recover']:
 name='foreign_request_run_'+entry;s,l,p,a,att=fixture(name);r=reg(l,a,att)
 if entry=='response':l.record_request_sent(r['request_id'])
 mutate(l,'UPDATE model_requests SET run_id=? WHERE request_id=?',('foreign_run',r['request_id']));b=rows(l)
 f=statusfn(l,r,entry) if entry in ['sent','response','failed'] else (lambda:reg(l,a,att)) if entry=='register' else (lambda:l.recover_run(name));o=cap(f);af=rows(l);stop=cap(lambda:l.stop_report(name))
 emit({'case':name,'group':'S3A-04','expected':'state/refreuse must reject; run-scoped recovery omission is disclosed scope boundary and must not grant success execution','input':{'mutation':'model_requests.run_id=foreign_run','entry':entry,'same_original_request':r},'before':b,'observed':o,'after':af,'stop':stop,'checks':{'zero_writes':b==af,'state_or_reuse_rejected':not o['accepted'] if entry!='recover' else True,'network_zero':all(x['network_request_count']==0 for x in af['model_requests'])},'actual_network_requests':0});s.close()
# Stored complete block, legal partial override assembly, equality of effective configuration.
for name,partial in [('legal_override',{'max_total_search_actions':0}),('legal_empty',{})]:
 d=D/name;d.mkdir();s=PollutantPathwayStore(d/'run.sqlite');l=SearchLedger(s,None,name);p=build_profile_identity_block();p['search_limits']=partial;b=rows(l);first=cap(lambda:l.register_search_run(name,p));stored=l.search_policy_block(name);same=copy.deepcopy(p);same['search_limits']=copy.deepcopy(stored['search_limits']);repeat=cap(lambda:l.register_search_run(name,same));rec=cap(lambda:l.recover_run(name,policy_block=p));budget=cap(lambda:l.budget_snapshot(name));af=rows(l);ck={'first_accepted':first['accepted'],'complete_11_keys':len(stored['search_limits'])==11,'version_present':bool(stored['search_limits'].get('version')),'same_effective_unchanged':repeat['accepted'] and repeat['result'].get('unchanged')==True,'recover_partial_accepted':rec['accepted'],'budget_accepted':budget['accepted']}
 emit({'case':name,'group':'S3A-03','expected':'legal partial user overrides assemble into full frozen block; same effective partial/full configuration reuses lawfully','input':{'submitted_policy':p,'effective_full_policy':same},'before':b,'observed':{'first':first,'repeat':repeat,'recover':rec,'budget':budget},'after':af,'checks':ck,'contract_passed':all(ck.values()),'actual_network_requests':0});s.close()
(ROOT/'evidence/extra_observations.json').write_text(json.dumps(OUT,ensure_ascii=False,indent=2)+'\n');emit({'case':'summary','case_controls':len(OUT),'network_requests':0,'external_model_calls':0})
