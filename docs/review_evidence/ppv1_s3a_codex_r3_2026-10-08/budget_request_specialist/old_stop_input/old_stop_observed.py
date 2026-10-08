#!/usr/bin/env python
"""Only synthetic cases; run with isolated source/vendor and fresh output root."""
import sys,json,hashlib,subprocess,os,time
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P/'repo/src'),str(P/'repo/tests')]
from s3a_worker import make_fixture
from pathway_v43.pollutant.profile import build_profile_identity_block
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.search import SearchLedger,search_policy_version,commit_search_event,SearchCrashInjection
from pathway_v43.storage.artifact_store import ArtifactStore
from pathway_v43.domain.models import content_hash
DATA=P/'generated_run2';DATA.mkdir(exist_ok=False)
OUT=[]
def emit(name,inp,out,assertion):
    row={'case':name,'input':inp,'output':out,'observed_assertion':assertion};OUT.append(row);print(json.dumps(row,ensure_ascii=False,default=str),flush=True)
def capture(fn):
    try:return {'returned':fn()}
    except Exception as e:return {'error':type(e).__name__,'detail':getattr(e,'detail',{}),'text':str(e)}
def mk(name,limits=None):
    d=DATA/name;d.mkdir();store=PollutantPathwayStore(d/'run.sqlite');art=ArtifactStore(d/'runs',name);ledger=SearchLedger(store,art,name);policy=build_profile_identity_block(search_limits=limits) if limits else build_profile_identity_block();ledger.register_search_run(name,policy);return store,ledger,art,policy,d
def enqueue(l,r,hyp,*,parent='p1',ctx='ctx1',tk='task1',rev=0,depth=1):
    return l.enqueue_action(run_id=r,parent_path_id=parent,context_ref=ctx,subject_ref=hyp.hypothesis_id,action_kind='expand_hypothesis',parent_search_revision=rev,policy_version=search_policy_version(),payload={'task_key':tk,'frozen_pool_digest':'pool1'},depth=depth)['action_id']
def counts(l):
    return {t:l.conn.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['events','search_actions','search_attempts','budget_reservations','search_commit_records','model_requests']}
def rows(l):
    return {t:[dict(r) for r in l.conn.execute('SELECT * FROM '+t)] for t in ['events','search_actions','search_attempts','budget_reservations','search_commit_records','model_requests']}
# Held action is unseen by H05 unexplored; held default budgets not exhausted.
r='stop_claimed_only';s,l,a,policy,d=mk(r);_,_,h,ev,args=make_fixture(r,'p1','k1','ctx1');aid=enqueue(l,r,h);rec=l.claim_action(aid,worker_id='w1');stop=l.stop_report(r);assert stop['primary']=='exhausted_search'
emit('stop_claimed_only',{'claimed_action':rec},{'stop':stop,'rows':rows(l)},'in-flight unrecovered claimed action omitted, exhausted_search reported');s.close()
