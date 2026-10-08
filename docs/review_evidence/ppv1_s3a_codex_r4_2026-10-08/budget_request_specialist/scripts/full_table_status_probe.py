#!/usr/bin/env python3
"""All-table confirmation of finite policy/lifecycle rules, with lawful controls.
No external provider is invoked. 'real' examples exercise bookkeeping only.
"""
from pathlib import Path
import copy,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'source/src'),str(ROOT/'source/tests')]
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.search import SearchLedger,search_policy_version
from pathway_v43.pollutant.store import PollutantPathwayStore
from s3a_worker import make_fixture
D=ROOT/'full_status_data';D.mkdir(exist_ok=False);OUT=[]
def rows(l):
 tables=[r[0] for r in l.conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
 return {t:[dict(x) for x in l.conn.execute('SELECT * FROM "'+t+'" ORDER BY rowid')] for t in tables}
def cap(f):
 try:return {'accepted':True,'result':f()}
 except Exception as e:return {'accepted':False,'exception':type(e).__name__,'kind':getattr(e,'detail',{}).get('kind'),'detail':getattr(e,'detail',{}),'message':str(e)}
def emit(x):OUT.append(x);print(json.dumps(x,ensure_ascii=False,sort_keys=True,default=str),flush=True)
def make(name,kind='decide',provider='scripted'):
 d=D/name;d.mkdir();s=PollutantPathwayStore(d/'run.sqlite');l=SearchLedger(s,None,name);p=build_profile_identity_block(search_limits={'max_real_model_requests':1});l.register_search_run(name,p);_,_,h,e,args=make_fixture(name,'p1','k1','ctx1');a=l.enqueue_action(run_id=name,parent_path_id='p1',context_ref='ctx1',subject_ref=h.hypothesis_id if kind=='expand_hypothesis' else 'pool_A',action_kind=kind,policy_version=search_policy_version(),payload={'task_key':'task_'+name,'frozen_pool_digest':'pool_A'},depth=1)['action_id'];rec=l.claim_action(a,worker_id='w');att=rec['attempt_refs'][0] if rec['attempt_refs'] else ''
 kwargs={'run_id':name,'action_id':a,'attempt_id':att,'provider_kind':provider,'request_key':'rk','payload':{'prompt':'original'},'purpose':'rank'};req=l.register_model_request(**kwargs);return s,l,p,a,req,kwargs

def fn(l,q,entry):
 return {'sent':lambda:l.record_request_sent(q['request_id']),'response':lambda:l.record_request_response(q['request_id'],'response_A'),'failed':lambda:l.mark_request_failed(q['request_id'])}[entry]
for damage in ['null_limits','missing_version','bool','out_of_range','unknown_key','negative']:
 for entry in ['sent','response','failed']:
  name='decide_bad_'+damage+'_'+entry;s,l,p,a,q,k=make(name)
  if entry=='response':l.record_request_sent(q['request_id'])
  original=copy.deepcopy(p)
  if damage=='null_limits':p['search_limits']=None
  elif damage=='missing_version':del p['search_limits']['version']
  elif damage=='unknown_key':p['search_limits']['unregistered_key']=1
  else:p['search_limits']['max_total_search_actions']={'bool':True,'out_of_range':1001,'negative':-1}[damage]
  l.conn.execute('UPDATE search_runs SET policy_block=? WHERE run_id=?',(json.dumps(p),name));l.conn.commit();b=rows(l);o=cap(fn(l,q,entry));af=rows(l);ck={'rejected':not o['accepted'],'policy_kind':o.get('kind')=='search_policy_block_corrupt','all_table_preserved':b==af}
  emit({'case':name,'group':'S3A-03','input':{'policy_original':original,'stored_policy':p,'request':q,'action_kind':'decide','empty_attempt_lawful':True,'entry':entry},'before':b,'observed':o,'after':af,'checks':ck,'contract_passed':all(ck.values()),'actual_network_requests':0});s.close()
for entry in ['sent','response','failed','register','recover']:
 name='alltable_unknown_'+entry;s,l,p,a,q,k=make(name,kind='expand_hypothesis');l.conn.execute('UPDATE model_requests SET status=? WHERE request_id=?',('corrupt-status',q['request_id']));l.conn.commit();b=rows(l);f=fn(l,q,entry) if entry in ['sent','response','failed'] else (lambda:l.register_model_request(**k)) if entry=='register' else (lambda:l.recover_run(name));o=cap(f);af=rows(l)
 if entry=='recover':
  ck={'structured_disclosure':o['accepted'] and len(o['result']['unknown_status_requests'])==1 and o['result']['unknown_status_requests'][0]['request_id']==q['request_id'] and o['result']['unknown_status_requests'][0]['status']=='corrupt-status','not_ordinary_pending':o['accepted'] and not o['result']['pending_requests'],'all_table_preserved':b==af}
 else:ck={'rejected':not o['accepted'],'all_table_preserved':b==af,'unknown_kind_failed_register':o.get('kind')=='request_status_unknown' if entry in ['failed','register'] else True}
 emit({'case':name,'group':'S3A-04','input':{'request':q,'mutated_status':'corrupt-status','entry':entry},'before':b,'observed':o,'after':af,'checks':ck,'contract_passed':all(ck.values()),'actual_network_requests':0});s.close()
for final in ['sent','response','failed']:
 name='real_registration_only_'+final;s,l,p,a,q,k=make(name,kind='expand_hypothesis',provider='real')
 if final=='response':l.record_request_sent(q['request_id'])
 b=rows(l);o=cap(fn(l,q,final));af=rows(l);budget=l.budget_snapshot(name);ck={'accepted':o['accepted'],'quota_not_repeated_or_refunded':budget['run_level']['max_real_model_requests']['used']==1,'reservations_preserved':b['budget_reservations']==af['budget_reservations'],'status_correct':af['model_requests'][0]['status']=={'sent':'sent','response':'responded','failed':'failed'}[final]}
 emit({'case':name,'group':'S3A-03/04','input':{'request':q,'entry':final,'provider_kind':'real bookkeeping only; actual provider never called; sent bookkeeping counter may be1'},'before':b,'observed':o,'after':af,'budget':budget,'checks':ck,'contract_passed':all(ck.values()),'actual_network_requests':0});s.close()
for status in ['responded','failed','abandoned']:
 for entry in ['sent','response','failed']:
  name='closed_'+status+'_'+entry;s,l,p,a,q,k=make(name,kind='expand_hypothesis')
  if status=='responded':l.record_request_sent(q['request_id']);l.record_request_response(q['request_id'],'old_response')
  elif status=='failed':l.mark_request_failed(q['request_id'])
  else:l.defer_action(a,worker_id='w',reason='unsent')
  b=rows(l);o=cap(fn(l,q,entry));af=rows(l);ck={'rejected':not o['accepted'],'all_table_preserved':b==af,'stored_status_kept':af['model_requests'][0]['status']==status};emit({'case':name,'group':'S3A-04','input':{'request':q,'terminal_status_from_public_api':status,'entry':entry},'before':b,'observed':o,'after':af,'checks':ck,'contract_passed':all(ck.values()),'actual_network_requests':0});s.close()
summary={'cases':len(OUT),'passed':sum(x['contract_passed'] for x in OUT),'failed':[x['case'] for x in OUT if not x['contract_passed']],'all_table_count':len(OUT[0]['before']),'network_requests':0,'external_model_calls':0,'same_root_controls_not_new_bugs':True};(ROOT/'evidence/full_status_observations.json').write_text(json.dumps(OUT,ensure_ascii=False,indent=2)+'\n');emit({'summary':summary});assert not summary['failed'],summary
