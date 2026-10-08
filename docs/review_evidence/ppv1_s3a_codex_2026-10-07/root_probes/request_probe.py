"""Independent synthetic S3a request identity/lifecycle observations. No provider calls."""
import hashlib,json,sys
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'src'));sys.path.insert(0,str(P/'tests'))
from pathway_v43.pollutant.profile import build_profile_identity_block,PPV1_SEARCH_SCHEMA_VERSION,SEARCH_LIMITS_VERSION
from pathway_v43.pollutant.search import SearchLedger,search_policy_version
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.domain.models import content_hash
from pathway_v43.storage.artifact_store import ArtifactStore
from s3a_worker import make_fixture
TABLES=['search_runs','search_actions','search_attempts','budget_reservations','model_requests','search_commit_records','events']
def rows(s):return {t:[dict(r) for r in s.conn.execute('SELECT * FROM '+t+' ORDER BY rowid').fetchall()] for t in TABLES}
def capture(f):
 try:return {'accepted':True,'result':f()}
 except Exception as e:return {'accepted':False,'exception':type(e).__name__,'detail':getattr(e,'detail',{}),'message':str(e)}
def emit(case,**kw):print(json.dumps({'case':case,**kw},ensure_ascii=False,sort_keys=True,default=str))
def fixture(name, *, claim=True, real_limit=2):
 s=PollutantPathwayStore(P/(name+'.sqlite'));l=SearchLedger(s,ArtifactStore(P/'runs',name),name)
 policy=build_profile_identity_block(search_limits={'max_real_model_requests':real_limit})
 l.register_search_run(name,policy)
 _,_,h,e,args=make_fixture(name,'p1','k1','ctx1')
 a=l.enqueue_action(run_id=name,parent_path_id='p1',context_ref='ctx1',subject_ref=h.hypothesis_id,action_kind='expand_hypothesis',policy_version=search_policy_version(),payload={'task_key':'task_'+name,'frozen_pool_digest':'pool_A'},depth=1)['action_id']
 receipt=l.claim_action(a,worker_id='w1') if claim else None
 att=receipt['attempt_refs'][0] if receipt else 'sattempt_unregistered'
 return s,l,a,att,e,args

def reg(l,a,att,payload,**kw):return l.register_model_request(run_id=l.run_id,action_id=a,attempt_id=att,provider_kind=kw.pop('provider_kind','scripted'),request_key=kw.pop('request_key','request_A'),payload=payload,**kw)
meta=json.loads((P/'input_snapshot.json').read_text())
emit('metadata',actual_HEAD=meta['actual_head'],parent_HEAD=meta['parent_head'],schema=PPV1_SEARCH_SCHEMA_VERSION,limits_version=SEARCH_LIMITS_VERSION,python=sys.version,actual_external_model_calls=0,synthetic_only=True)
# Same request content identity and rightful idempotence.
for label,change in [('clean_repeat',None),('payload_changed',{'prompt':'DIFFERENT'}),('purpose_changed','DIFFERENT')]:
 s,l,a,att,e,args=fixture(label);payload={'prompt':'original','task_key':'task_A'}
 r=reg(l,a,att,payload,purpose='rank');before=rows(s)
 op=lambda:reg(l,a,att,change if isinstance(change,dict) else payload,purpose=change if isinstance(change,str) else 'rank')
 emit(label,input={'action_id':a,'attempt_id':att,'first_payload':payload,'next_payload':change if isinstance(change,dict) else payload,'next_purpose':change if isinstance(change,str) else 'rank'},first=r,observation=capture(op),before=before,after=rows(s));s.close()
# Same ID aliases a different legal claimed action when reusing first attempt ref.
s,l,a,att,e,args=fixture('action_changed')
r=reg(l,a,att,{'prompt':'original'});b=l.enqueue_action(run_id=l.run_id,parent_path_id='p2',context_ref='ctx2',subject_ref='pool_B',action_kind='decide',policy_version=search_policy_version(),payload={'task_key':'task_B'})['action_id'];l.claim_action(b,worker_id='w2');before=rows(s)
emit('same_request_different_action',input={'original_action':a,'new_action':b,'reused_attempt':att},observation=capture(lambda:reg(l,b,att,{'prompt':'original'})),before=before,after=rows(s));s.close()
# Fresh request despite nonexistent/unclaimed/foreign attempt; protocol-only real registration, no sending or network.
for label,claim,foreign in [('unclaimed_action',False,False),('nonexistent_action',True,True),('foreign_attempt',True,False)]:
 s,l,a,att,e,args=fixture(label,claim=claim)
 action='sact_missing' if foreign else a
 attempt='sattempt_foreign' if label=='foreign_attempt' else att
 before=rows(s);obs=capture(lambda:reg(l,action,attempt,{'prompt':'bounded_test'},provider_kind='real'))
 emit(label,input={'action_id':action,'attempt_id':attempt,'provider_kind':'real','note':'ledger registration only; no provider or send call'},observation=obs,before=before,after=rows(s),actual_network_request_count=0);s.close()
# Existing request payload hash damage is accepted on repeat and recovery.
s,l,a,att,e,args=fixture('request_hash_corrupt');r=reg(l,a,att,{'prompt':'original'});rid=r['request_id']
s.conn.execute('UPDATE model_requests SET payload_hash=? WHERE request_id=?',('0'*64,rid));s.conn.commit();before=rows(s)
emit('request_hash_corrupt',mutation={'table':'model_requests','field':'payload_hash','value':'0'*64},observation=capture(lambda:reg(l,a,att,{'prompt':'original'})),recovery=capture(lambda:l.recover_run(l.run_id)),before=before,after=rows(s));s.close()
# A request can be first sent after its action has been deferred and execution budget released.
s,l,a,att,e,args=fixture('sent_after_defer');r=reg(l,a,att,{'prompt':'original'},provider_kind='scripted');l.defer_action(a,worker_id='w1',reason='not_executed');before=rows(s)
emit('request_sent_after_defer',request_id=r['request_id'],observation=capture(lambda:l.record_request_sent(r['request_id'])),before=before,after=rows(s),actual_network_request_count=0);s.close()
# Positive: legal state transitions and explicit real-zero guard both remain honest.
s,l,a,att,e,args=fixture('legal_lifecycle');r=reg(l,a,att,{'prompt':'original'});before=rows(s);l.record_request_sent(r['request_id']);l.record_request_response(r['request_id'],'immutable_response_ref')
emit('legal_lifecycle',before=before,after=rows(s),request=l.request(r['request_id']),actual_network_request_count=0);s.close()
s,l,a,att,e,args=fixture('real_zero',real_limit=0);before=rows(s)
emit('real_zero_control',observation=capture(lambda:reg(l,a,att,{'prompt':'original'},provider_kind='real')),before=before,after=rows(s),actual_network_request_count=0);s.close()
