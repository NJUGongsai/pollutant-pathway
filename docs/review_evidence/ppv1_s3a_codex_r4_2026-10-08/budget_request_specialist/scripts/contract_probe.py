#!/usr/bin/env python3
"""Independent S3A-03/04/05 rule matrix. Synthetic; no network/provider calls."""
from pathlib import Path
import copy, hashlib, itertools, json, sys
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'source/src'),str(ROOT/'source/tests')]
from s3a_worker import make_fixture
from pathway_v43.pollutant.profile import build_profile_identity_block, PPV1_SEARCH_SCHEMA_VERSION, PPV1_PROFILE_SCHEMA_VERSION, SEARCH_LIMITS_VERSION
from pathway_v43.pollutant.store import PollutantPathwayStore, PPV1_STORE_SCHEMA_VERSION
from pathway_v43.pollutant.search import SearchLedger,search_policy_version,resolve_search_stop,STOP_REASON_PRIORITY,COMMIT_KIND_OUTCOME
from pathway_v43.storage.artifact_store import ArtifactStore
DATA=ROOT/'contract_data';DATA.mkdir(exist_ok=False)
TABLES=['search_runs','search_actions','search_attempts','budget_reservations','model_requests','search_commit_records','events']
OUT=[]
def rows(l):return {t:[dict(r) for r in l.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in TABLES}
def cap(fn):
 try:return {'accepted':True,'result':fn()}
 except Exception as e:return {'accepted':False,'exception':type(e).__name__,'detail':getattr(e,'detail',{}),'message':str(e)}
def emit(name,group,expect,observed,inp=None,before=None,after=None,checks=None,note=''):
 checks=checks or {}
 row={'case':name,'group':group,'expected':expect,'observed':observed,'input':inp or {},'before':before,'after':after,'checks':checks,'contract_passed':all(checks.values()),'note':note,'actual_network_requests':0,'external_model_calls':0}; OUT.append(row); print(json.dumps(row,ensure_ascii=False,sort_keys=True,default=str),flush=True)
def fixture(name,limits=None,kind='expand_hypothesis',claim=True):
 d=DATA/name;d.mkdir();s=PollutantPathwayStore(d/'run.sqlite');l=SearchLedger(s,ArtifactStore(d/'runs',name),name);p=build_profile_identity_block(search_limits=limits);l.register_search_run(name,p)
 _,_,h,e,args=make_fixture(name,'p1','k1','ctx1');a=l.enqueue_action(run_id=name,parent_path_id='p1',context_ref='ctx1',subject_ref=h.hypothesis_id if kind=='expand_hypothesis' else 'pool_A',action_kind=kind,policy_version=search_policy_version(),payload={'task_key':'task_'+name,'frozen_pool_digest':'pool_A'},depth=1)['action_id'];receipt=l.claim_action(a,worker_id='w') if claim else None
 att=receipt['attempt_refs'][0] if receipt and receipt['attempt_refs'] else '';return s,l,p,a,att,e,args
def reg(l,a,att,key='rk',provider='scripted',payload=None,purpose='rank',retry_of=''):
 return l.register_model_request(run_id=l.run_id,action_id=a,attempt_id=att,provider_kind=provider,request_key=key,payload=payload or {'prompt':'original'},purpose=purpose,retry_of=retry_of)
def reject(name,group,l,fn,inp=None,note=''):
 b=rows(l);o=cap(fn);af=rows(l);emit(name,group,'structured reject before success writes',o,inp,b,af,{'rejected':not o['accepted'],'structured':not o['accepted'] and bool(o.get('detail')),'zero_write':b==af},note);return o
def mutation(l,sql,params):l.conn.execute(sql,params);l.conn.commit()
print(json.dumps({'case':'metadata','actual_HEAD':json.loads((ROOT/'evidence/input_snapshot.json').read_text())['metadata']['actual_HEAD'],'schema':{'search':PPV1_SEARCH_SCHEMA_VERSION,'profile':PPV1_PROFILE_SCHEMA_VERSION,'store':PPV1_STORE_SCHEMA_VERSION,'search_limits':SEARCH_LIMITS_VERSION},'python':sys.version,'synthetic_only':True,'network_requests':0,'external_model_calls':0},sort_keys=True),flush=True)
# 03: capped public submit -> defer -> second claim, plus legitimate unexecuted release.
s,l,p,a,att,e,args=fixture('event_cap',{'max_total_search_actions':1,'max_alternative_hypotheses_per_parent':1,'max_attempts_per_hypothesis':1});l.submit_action_event(a,e,worker_id='w',**args)
b=rows(l);o=cap(lambda:l.defer_action(a,worker_id='w',reason='after event'));af=rows(l);budget=l.budget_snapshot(l.run_id)
emit('event_cap_defer','S3A-03','already executed event never refunds quota',{'defer':o,'budget':budget},{'policy':p,'event':vars(e),'submit_args':args},b,af,{'rejected':not o['accepted'],'zero_write':b==af,'used_stays_one':budget['run_level']['max_total_search_actions']['used']==1})
_,_,h2,_,_=make_fixture(l.run_id,'p1','k2','ctx1');a2=l.enqueue_action(run_id=l.run_id,parent_path_id='p1',context_ref='ctx1',subject_ref=h2.hypothesis_id,action_kind='expand_hypothesis',parent_search_revision=1,policy_version=search_policy_version(),payload={'task_key':'t2'},depth=1)['action_id'];reject('event_cap_second_claim','S3A-03',l,lambda:l.claim_action(a2,worker_id='w'),{'policy':p,'second_action':a2});s.close()
s,l,p,a,att,e,args=fixture('unexecuted');b=rows(l);o=cap(lambda:l.defer_action(a,worker_id='w',reason='not executed'));af=rows(l);budget=l.budget_snapshot(l.run_id)
emit('unexecuted_release','S3A-03','legal defer releases only unexecuted reservations',o,{'action':a},b,af,{'accepted':o['accepted'],'used_zero':budget['run_level']['max_total_search_actions']['used']==0,'reservations_released':all(r['status']=='released' for r in af['budget_reservations']),'attempt_abandoned':af['search_attempts'][0]['status']=='abandoned','action_deferred':af['search_actions'][0]['status']=='deferred'});s.close()
s,l,p,a,att,e,args=fixture('registered_real_defer',{'max_real_model_requests':1});r=reg(l,a,att,provider='real');b=rows(l);o=cap(lambda:l.defer_action(a,worker_id='w',reason='not sent'));af=rows(l);budget=l.budget_snapshot(l.run_id)
emit('registered_real_defer','S3A-03','unsent can defer but real registration quota retained',o,{'provider_kind':'real','registration_only':True},b,af,{'accepted':o['accepted'],'real_used_one':budget['run_level']['max_real_model_requests']['used']==1,'action_used_zero':budget['run_level']['max_total_search_actions']['used']==0,'request_abandoned':af['model_requests'][0]['status']=='abandoned'});s.close()
for status in ['sent','responded','failed']:
 s,l,p,a,att,e,args=fixture('defer_request_'+status);r=reg(l,a,att)
 if status=='failed':l.mark_request_failed(r['request_id'])
 else:
  l.record_request_sent(r['request_id'])
  if status=='responded':l.record_request_response(r['request_id'],'response_A')
 reject('defer_request_'+status,'S3A-03',l,lambda:l.defer_action(a,worker_id='w',reason='after request'),{'status':status,'provider':'scripted'});s.close()
for status in ['recorded','failed']:
 s,l,p,a,att,e,args=fixture('defer_attempt_'+status);mutation(l,'UPDATE search_attempts SET status=? WHERE expansion_attempt_id=?',(status,att));reject('defer_attempt_'+status,'S3A-03',l,lambda:l.defer_action(a,worker_id='w',reason='after attempt'),{'attempt_status':status});s.close()
# No assignment evidence for the same frozen event is a documented conservative rejection.
s,l,p,a,att,e,args=fixture('unattributed_event');s.submit_event(e,**args);reject('unattributed_event_conservative','S3A-03',l,lambda:l.defer_action(a,worker_id='w',reason='no execution by this worker'),{'public_store_event':vars(e)},'Conservative refusal when no action commit assigns event; disclosed boundary, not a new blocking requirement.');s.close()
# 03: all four original malformed values at registration and every consuming read.
bad_values={'bool':{'max_total_search_actions':True},'out_of_range':{'max_total_search_actions':1001},'unknown':{'made_up_limit':1},'negative':{'max_total_search_actions':-1}}
for kind,changes in bad_values.items():
 d=DATA/('register_policy_'+kind);d.mkdir();s=PollutantPathwayStore(d/'run.sqlite');l=SearchLedger(s,None,'register_policy_'+kind);p=build_profile_identity_block();p['search_limits'].update(changes);reject('register_policy_'+kind,'S3A-03',l,lambda:l.register_search_run(l.run_id,p),{'policy':p});s.close()
 for entry in ['budget','enqueue','claim','request_register','recover']:
  s,l,p,a,att,e,args=fixture('read_policy_'+kind+'_'+entry,claim=entry!='claim');p['search_limits'].update(changes);mutation(l,'UPDATE search_runs SET policy_block=? WHERE run_id=?',(json.dumps(p),l.run_id))
  f={'budget':lambda:l.budget_snapshot(l.run_id),'enqueue':lambda:l.enqueue_action(run_id=l.run_id,parent_path_id='p2',context_ref='ctx2',subject_ref='pool2',action_kind='decide',policy_version=search_policy_version(),payload={'task_key':'other'}),'claim':lambda:l.claim_action(a,worker_id='w'),'request_register':lambda:reg(l,a,att),'recover':lambda:l.recover_run(l.run_id)}[entry]
  reject('read_policy_'+kind+'_'+entry,'S3A-03',l,f,{'mutation':changes,'entry':entry});s.close()
# Same registered block loses its required version or becomes null: first reads must not invent defaults.
for damage in ['missing_version','null_limits']:
 for entry in ['budget','claim','recover']:
  s,l,p,a,att,e,args=fixture('read_policy_'+damage+'_'+entry,{'max_total_search_actions':0},claim=False)
  if damage=='missing_version':del p['search_limits']['version']
  else:p['search_limits']=None
  mutation(l,'UPDATE search_runs SET policy_block=? WHERE run_id=?',(json.dumps(p),l.run_id));f={'budget':lambda:l.budget_snapshot(l.run_id),'claim':lambda:l.claim_action(a,worker_id='w'),'recover':lambda:l.recover_run(l.run_id)}[entry];reject('read_policy_'+damage+'_'+entry,'S3A-03',l,f,{'damaged_policy':p,'entry':entry});s.close()
# 04: content conflicts use legitimate claimed non-expand empty attempts.
for damage in ['payload','purpose','action','retry_of','payload_hash']:
 s,l,p,a,att,e,args=fixture('identity_'+damage,kind='decide');r=reg(l,a,att);kw={'payload':{'prompt':'original'},'purpose':'rank','retry_of':''}
 if damage=='payload':kw['payload']={'prompt':'changed'}
 elif damage=='purpose':kw['purpose']='changed'
 elif damage=='retry_of':kw['retry_of']='other_request'
 elif damage=='payload_hash':mutation(l,'UPDATE model_requests SET payload_hash=? WHERE request_id=?',('0'*64,r['request_id']))
 elif damage=='action':
  a2=l.enqueue_action(run_id=l.run_id,parent_path_id='p2',context_ref='ctx2',subject_ref='pool2',action_kind='decide',policy_version=search_policy_version(),payload={'task_key':'other'})['action_id'];l.claim_action(a2,worker_id='w');a=a2
 reject('identity_'+damage,'S3A-04',l,lambda:reg(l,a,att,**kw),{'damage':damage,'caller_action':a,'caller_attempt':att,'caller_request':kw});s.close()
# Request execution references at all applicable intake/consumption/recovery entries.
damages=['missing_action','unclaimed_action','foreign_action_run','missing_attempt','foreign_attempt_action','foreign_attempt_run','closed_attempt','empty_expand_attempt']
for damage in damages:
 for entry in ['register','sent','response','failed','recover']:
  name='references_'+damage+'_'+entry;s,l,p,a,att,e,args=fixture(name,{'max_real_model_requests':1});r=reg(l,a,att) if entry!='register' else None
  if entry=='response':l.record_request_sent(r['request_id'])
  # Mutation of persistent execution reference; retain identities and all other facts.
  if damage=='missing_action':mutation(l,'DELETE FROM search_actions WHERE action_id=?',(a,))
  elif damage=='unclaimed_action':mutation(l,"UPDATE search_actions SET status='pending' WHERE action_id=?",(a,))
  elif damage=='foreign_action_run':mutation(l,'UPDATE search_actions SET run_id=? WHERE action_id=?',('foreign_run',a))
  elif damage=='missing_attempt':mutation(l,'DELETE FROM search_attempts WHERE expansion_attempt_id=?',(att,))
  elif damage=='foreign_attempt_action':mutation(l,'UPDATE search_attempts SET action_id=? WHERE expansion_attempt_id=?',('foreign_action',att))
  elif damage=='foreign_attempt_run':mutation(l,'UPDATE search_attempts SET run_id=? WHERE expansion_attempt_id=?',('foreign_run',att))
  elif damage=='closed_attempt':mutation(l,"UPDATE search_attempts SET status='abandoned' WHERE expansion_attempt_id=?",(att,))
  elif damage=='empty_expand_attempt':
   if entry=='register':att=''
   else:mutation(l,"UPDATE model_requests SET attempt_id='' WHERE request_id=?",(r['request_id'],))
  if entry=='register':f=lambda:reg(l,a,att,provider='real')
  elif entry=='sent':f=lambda:l.record_request_sent(r['request_id'])
  elif entry=='response':f=lambda:l.record_request_response(r['request_id'],'response_A')
  elif entry=='failed':f=lambda:l.mark_request_failed(r['request_id'])
  else:f=lambda:l.recover_run(l.run_id)
  reject(name,'S3A-04',l,f,{'damage':damage,'entry':entry,'registered_request':r,'provider_for_state_consumption':'scripted','provider_for_register':'real_registration_only'});s.close()
# Reuse must validate stored execution identity too, not only caller execution identity.
for field,value in [('run_id','foreign_run'),('attempt_id','missing_attempt')]:
 s,l,p,a,att,e,args=fixture('request_reuse_'+field);r=reg(l,a,att);mutation(l,'UPDATE model_requests SET '+field+'=? WHERE request_id=?',(value,r['request_id']));reject('request_reuse_'+field,'S3A-04',l,lambda:reg(l,a,att),{'damaged_stored_field':field,'value':value,'correct_caller_action':a,'correct_caller_attempt':att});s.close()
# Released action cannot resume request, even if lifecycle status is independently damaged back.
for entry,status in [('sent','registered'),('response','sent'),('failed','registered'),('recover','registered')]:
 s,l,p,a,att,e,args=fixture('released_'+entry);r=reg(l,a,att);l.defer_action(a,worker_id='w',reason='unsent');mutation(l,'UPDATE model_requests SET status=? WHERE request_id=?',(status,r['request_id']));f={'sent':lambda:l.record_request_sent(r['request_id']),'response':lambda:l.record_request_response(r['request_id'],'response_A'),'failed':lambda:l.mark_request_failed(r['request_id']),'recover':lambda:l.recover_run(l.run_id)}[entry];reject('released_'+entry,'S3A-04',l,f,{'entry':entry,'damaged_request_status':status});s.close()
# Positive same-key/scoped lifecycle/non-expand empty/fake/network-zero/retry/real-zero controls.
for provider in ['scripted','fake']:
 for kind in ['expand_hypothesis','decide','retrieve']:
  s,l,p,a,att,e,args=fixture('legal_'+provider+'_'+kind,kind=kind);r=reg(l,a,att,provider=provider);b=rows(l);repeat=cap(lambda:reg(l,a,att,provider=provider));repeat_rows=rows(l);l.record_request_sent(r['request_id']);l.record_request_response(r['request_id'],'response_A');af=rows(l);emit('legal_'+provider+'_'+kind,'S3A-04','same key zero new writes and legal scoped lifecycle network zero',{'repeat':repeat,'request':l.request(r['request_id'])},{'provider':provider,'action_kind':kind,'attempt':att},b,af,{'repeat_accepted':repeat['accepted'],'repeat_zero_writes':b==repeat_rows,'responded':af['model_requests'][0]['status']=='responded','network_zero':af['model_requests'][0]['network_request_count']==0,'real_used_zero':l.budget_snapshot(l.run_id)['run_level']['max_real_model_requests']['used']==0});s.close()
s,l,p,a,att,e,args=fixture('retry_real',{'max_real_model_requests':2});r1=reg(l,a,att,key='k1',provider='real');rec=cap(lambda:l.recover_run(l.run_id));b=rows(l);r2=cap(lambda:reg(l,a,att,key='k2',provider='real',retry_of=r1['request_id']));af=rows(l);budget=l.budget_snapshot(l.run_id);emit('retry_real','S3A-04','explicit retry different ID uses remaining registration quota; no send',{'retry':r2,'recover':rec,'budget':budget},{'provider':'real_registration_only','retry_of':r1['request_id']},b,af,{'retry_accepted':r2['accepted'],'new_id':r2['accepted'] and r2['result']['request_id']!=r1['request_id'],'real_used_two':budget['run_level']['max_real_model_requests']['used']==2,'recovery_no_implicit_send':all(x['status']=='registered' and x['network_request_count']==0 for x in af['model_requests'])});reject('retry_real_third_capped','S3A-04',l,lambda:reg(l,a,att,key='k3',provider='real',retry_of=r1['request_id']),{'provider':'real_registration_only'});s.close()
s,l,p,a,att,e,args=fixture('real_zero');reject('real_zero','S3A-04',l,lambda:reg(l,a,att,provider='real'),{'provider':'real_registration_only','max_real_model_requests':0});s.close()
# 05: empty, inflight, recovered B1, complete, deferred, pending, blocked, request pending controls.
s,l,p,a,att,e,args=fixture('stop_inflight');b=rows(l);o=l.stop_report(l.run_id);rec=cap(lambda:l.recover_run(l.run_id));u=l.stop_report(l.run_id,user_stop=True);emit('stop_inflight','S3A-05','inflight counts shown; primary None; user_stop dominates',{'stop':o,'recovery':rec,'user_stop':u},{'action':a,'attempt':att},b,rows(l),{'not_exhausted':o['primary'] is None,'claimed_one':o['unexplored']['claimed_actions']==1,'open_one':o['unexplored']['open_attempts']==1,'recover_B1':rec['accepted'] and rec['result']['actions'][0]['boundary']=='B1_claimed_pending_completion','user_stop':u['primary']=='user_stop'});l.complete_action(a,worker_id='w',outcome_kind=COMMIT_KIND_OUTCOME);o=l.stop_report(l.run_id);emit('stop_completed','S3A-05','finished action honest exhaustion',o,checks={'exhausted':o['primary']=='exhausted_search','claimed_zero':o['unexplored']['claimed_actions']==0,'open_zero':o['unexplored']['open_attempts']==0});s.close()
for state in ['empty','pending','deferred','blocked','pending_request','empty_pool']:
 s,l,p,a,att,e,args=fixture('stop_'+state,claim=state not in ['empty','pending','empty_pool'])
 if state in ['empty','empty_pool']:mutation(l,'DELETE FROM search_actions WHERE action_id=?',(a,))
 if state=='deferred':l.defer_action(a,worker_id='w',reason='waiting')
 if state=='blocked':mutation(l,"UPDATE search_actions SET status='blocked' WHERE action_id=?",(a,));mutation(l,"UPDATE search_attempts SET status='abandoned' WHERE expansion_attempt_id=?",(att,))
 if state=='pending_request':reg(l,a,att)
 b=rows(l);o=l.stop_report(l.run_id,no_local_candidate=state=='empty_pool');expected={'empty':'exhausted_search','pending':None,'deferred':None,'blocked':None,'pending_request':'awaiting_prediction','empty_pool':'no_local_candidate'}[state];emit('stop_'+state,'S3A-05','six existing reason semantics retained',o,{'state':state},b,rows(l),{'primary_correct':o['primary']==expected,'zero_writes':b==rows(l)});s.close()
# Priority checks all 63 nonempty reason subsets against fixed original six-order contract.
priority=['user_stop','budget_limit','depth_limit','awaiting_prediction','no_local_candidate','exhausted_search'];checks={};results=[]
for size in range(1,7):
 for subset in itertools.combinations(priority,size):
  o=resolve_search_stop(set(subset));checks[','.join(subset)]=o['primary']==subset[0] and set(o['other_reasons'])==set(subset[1:]);results.append({'input':subset,'output':o})
emit('stop_six_reason_priority','S3A-05','all six reasons priority and other reasons preserved',results,{'fixed_priority':priority,'actual_constant':list(STOP_REASON_PRIORITY)},checks=checks)
# Independent zero-resource fixtures: never stop global work merely because unused resource is zero.
for resource in ['real','retrieval','transition','total','depth','width']:
 limits={'real':{'max_real_model_requests':0},'retrieval':{'max_retrievals_total':0,'max_retrievals_per_parent':0},'transition':{'max_scenario_transitions':0},'total':{'max_total_search_actions':0},'depth':{'max_search_depth':0},'width':{'max_product_expansion_width':0}}[resource]
 name='zero_'+resource;d=DATA/name;d.mkdir();s=PollutantPathwayStore(d/'run.sqlite');l=SearchLedger(s,None,name);p=build_profile_identity_block(search_limits=limits);l.register_search_run(name,p)
 def en(kind,**kw):return l.enqueue_action(run_id=name,parent_path_id='p1',context_ref='ctx1',subject_ref='h' if kind=='expand_hypothesis' else kind,action_kind=kind,policy_version=search_policy_version(),payload={'task_key':'t_'+kind},**kw)
 refusals=[];observed={};b=rows(l)
 if resource in ['depth','width']:
  observed['target_enqueue']=en('expand_hypothesis',depth=1,source_event_id='source' if resource=='width' else '');refusals.append(observed['target_enqueue']);observed['decide_enqueue']=en('decide');observed['decide_claim']=cap(lambda:l.claim_action(observed['decide_enqueue']['action_id'],worker_id='w'));expected_reason='depth_limit' if resource=='depth' else 'product_width_limit';ck={'target_refused':not observed['target_enqueue']['created'] and observed['target_enqueue']['reason']==expected_reason,'decide_works':observed['decide_claim']['accepted']}
 elif resource=='real':
  d1=en('decide');l.claim_action(d1['action_id'],worker_id='w');observed['scripted_registration']=cap(lambda:reg(l,d1['action_id'],'',provider='scripted'));observed['real_registration']=cap(lambda:reg(l,d1['action_id'],'',key='real',provider='real'));ck={'scripted_works':observed['scripted_registration']['accepted'],'real_refused':not observed['real_registration']['accepted']}
 else:
  target='retrieve' if resource=='retrieval' else 'scenario_transition' if resource=='transition' else 'decide';t1=en(target);observed['target_claim']=cap(lambda:l.claim_action(t1['action_id'],worker_id='w'));refusals.append({'reason':'budget_limit','limit_key':observed['target_claim'].get('detail',{}).get('limit_key')});ck={'target_refused':not observed['target_claim']['accepted']}
  if resource!='total':d1=en('decide');observed['decide_claim']=cap(lambda:l.claim_action(d1['action_id'],worker_id='w'));ck['decide_works']=observed['decide_claim']['accepted']
 observed['stop']=l.stop_report(name,refusals=refusals);ck['stop_reason_correct']=observed['stop']['primary']==('budget_limit' if resource in ['retrieval','transition','total'] else 'depth_limit' if resource=='depth' else 'awaiting_prediction' if resource=='real' else None)
 emit(name,'S3A-05','resource-specific zero guards and stop semantics',observed,{'policy':p},b,rows(l),ck);s.close()
summary={'cases':len(OUT),'pass':sum(x['contract_passed'] for x in OUT),'failed_cases':[x['case'] for x in OUT if not x['contract_passed']],'groups':{g:{'cases':sum(x['group']==g for x in OUT),'pass':sum(x['group']==g and x['contract_passed'] for x in OUT)} for g in ['S3A-03','S3A-04','S3A-05']},'network_requests':0,'external_model_calls':0}
(ROOT/'evidence/contract_observations.json').write_text(json.dumps(OUT,ensure_ascii=False,indent=2,default=str)+'\n');(ROOT/'evidence/contract_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'summary':summary},sort_keys=True),flush=True)
