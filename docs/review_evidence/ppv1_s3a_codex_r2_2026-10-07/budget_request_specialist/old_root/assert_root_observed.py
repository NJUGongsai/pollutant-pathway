#!/usr/bin/env python3
"""Read only archived observations; a pass affirms gaps, not their repair.

Does not import production modules, open SQLite or execute probe/test bodies.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

HEAD='9b78f4279cc6fa50b3b51c31a5c8e07abbeda207'
REQUEST_CASES={
    'clean_repeat','payload_changed','purpose_changed',
    'same_request_different_action','unclaimed_action','nonexistent_action',
    'foreign_attempt','request_hash_corrupt','request_sent_after_defer',
    'legal_lifecycle','real_zero_control'}
POLICY_CASES={'clean','out_of_range','bool_limit','unknown_key','negative'}

def load(p):
    rows=[json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    names=[r['case'] for r in rows]
    assert len(names)==len(set(names)),names
    return rows,{r['case']:r for r in rows}

def emit(kind,case,**kw):
    print(json.dumps(dict(kind=kind,case=case,observed_assertion_passed=True,**kw),ensure_ascii=False,sort_keys=True))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--logs',type=Path,default=Path(__file__).resolve().parent)
    a=ap.parse_args();p=a.logs.resolve()
    rows,r=load(p/'request_probe.stdout.jsonl')
    assert len(rows)==12 and set(r)==REQUEST_CASES|{'metadata'}
    m=r['metadata'];assert rows[0]['case']=='metadata'
    assert m['actual_HEAD']==HEAD and m['parent_HEAD']=='00e509a974b40a7c9779fcd35e53b16637a13d60'
    assert m['synthetic_only'] is True and m['actual_external_model_calls']==0
    assert m['schema']=='ppv1-search-1' and m['limits_version']=='ppv1-search-limits-3'
    # Three idempotence cases: two differing inputs are wrongly accepted.
    for name in ('clean_repeat','payload_changed','purpose_changed'):
        c=r[name];o=c['observation'];result=o['result']
        assert o['accepted'] is True and result['unchanged'] is True
        assert result['registered'] is False and result['reason']=='same_request_key'
        assert result['request_id']==c['first']['request_id']
        assert c['first']['registered'] is True and c['first']['network_request_count']==0
        assert c['before']==c['after'] and len(c['after']['model_requests'])==1
        if name=='payload_changed':assert c['input']['first_payload']!=c['input']['next_payload']
        elif name=='purpose_changed':assert c['input']['next_purpose']=='DIFFERENT'
        else:assert c['input']['first_payload']==c['input']['next_payload'] and c['input']['next_purpose']=='rank'
        emit('request',name,classification='legal_control' if name=='clean_repeat' else 'observed_identity_gap')
    c=r['same_request_different_action'];i=c['input'];o=c['observation']
    assert i['original_action']!=i['new_action'] and o['accepted']
    assert o['result']['unchanged'] and not o['result']['registered']
    assert c['before']==c['after']
    assert c['after']['model_requests'][0]['action_id']==i['original_action']
    assert c['after']['model_requests'][0]['attempt_id']==i['reused_attempt']
    assert o['result']['request_id']==c['after']['model_requests'][0]['request_id']
    assert len(c['after']['search_actions'])==2 and all(x['status']=='claimed' for x in c['after']['search_actions'])
    emit('request',c['case'],classification='observed_identity_gap')
    for name in ('unclaimed_action','nonexistent_action','foreign_attempt'):
        c=r[name];before=c['before'];after=c['after'];o=c['observation']
        assert o['accepted'] and o['result']['registered'] and o['result']['provider_kind']=='real'
        assert c['actual_network_request_count']==0 and o['result']['network_request_count']==0
        assert before['model_requests']==[] and len(after['model_requests'])==1
        request=after['model_requests'][0]
        assert request['action_id']==c['input']['action_id'] and request['attempt_id']==c['input']['attempt_id']
        assert request['network_request_count']==0 and request['status']=='registered'
        added=[x for x in after['budget_reservations'] if x['limit_key']=='max_real_model_requests']
        assert len(added)==1 and added[0]['status']=='consumed' and added[0]['units']==1
        assert after['search_actions']==before['search_actions'] and after['search_attempts']==before['search_attempts']
        if name=='unclaimed_action':
            assert before['search_actions'][0]['status']=='pending' and before['search_attempts']==[]
        elif name=='nonexistent_action':
            assert all(x['action_id']!=request['action_id'] for x in after['search_actions'])
        else:
            assert all(x['expansion_attempt_id']!=request['attempt_id'] for x in after['search_attempts'])
        emit('request',name,classification='observed_request_authority_gap',network_calls=0)
    c=r['request_hash_corrupt'];o=c['observation'];rec=c['recovery']
    assert c['before']==c['after'] and c['mutation']['value']=='0'*64
    assert c['after']['model_requests'][0]['payload_hash']=='0'*64
    assert o['accepted'] and o['result']['unchanged'] and not o['result']['registered']
    assert rec['accepted'] and len(rec['result']['pending_requests'])==1
    assert rec['result']['pending_requests'][0]['request_id']==o['result']['request_id']
    assert rec['result']['pending_requests'][0]['status']=='registered'
    emit('request',c['case'],classification='observed_existing_request_integrity_gap')
    c=r['request_sent_after_defer'];before=c['before'];after=c['after']
    assert c['observation']['accepted'] and c['observation']['result'] is None
    assert before['search_actions']==after['search_actions'] and before['search_actions'][0]['status']=='deferred'
    assert before['budget_reservations']==after['budget_reservations'] and all(x['status']=='released' for x in after['budget_reservations'])
    assert before['model_requests'][0]['status']=='registered' and after['model_requests'][0]['status']=='sent'
    assert c['actual_network_request_count']==0 and after['model_requests'][0]['network_request_count']==0
    emit('request',c['case'],classification='observed_request_lifecycle_gap',network_calls=0)
    c=r['legal_lifecycle'];before=c['before'];after=c['after']
    assert before['model_requests'][0]['status']=='registered'
    assert len(after['model_requests'])==1 and after['model_requests'][0]==c['request']
    assert c['request']['status']=='responded' and c['request']['response_ref']=='immutable_response_ref'
    assert c['request']['provider_kind']=='scripted' and c['request']['network_request_count']==0 and c['actual_network_request_count']==0
    assert before['budget_reservations']==after['budget_reservations']
    emit('request',c['case'],classification='legal_control')
    c=r['real_zero_control'];o=c['observation']
    assert not o['accepted'] and o['exception']=='SearchBudgetExhausted'
    assert o['detail']['limit_key']=='max_real_model_requests' and o['detail']['max']==0
    assert c['before']==c['after'] and c['after']['model_requests']==[] and c['actual_network_request_count']==0
    emit('request',c['case'],classification='legal_zero_guard')
    for c in rows[1:]:
        assert c['before']['events']==[] and c['after']['events']==[]
        assert all(x['network_request_count']==0 for x in c['after']['model_requests'])
    prows,pol=load(p/'policy_probe.stdout.jsonl')
    assert len(prows)==5 and set(pol)==POLICY_CASES
    for name in ('clean','out_of_range','bool_limit','unknown_key','negative'):
        c=pol[name];rows=c['rows'];snap=c['snapshot'];g=c['same_source_profile_guard']
        assert c['actual_external_model_calls']==0
        assert c['register']['accepted'] and c['register']['result'] is None and c['enqueue']['accepted']
        assert len(rows['search_runs'])==1 and len(rows['search_actions'])==1
        assert json.loads(rows['search_runs'][0]['policy_block'])==c['input_policy']
        assert snap['accepted'] and snap['result']['version']=='ppv1-search-limits-3'
        b=snap['result']['run_level']['max_total_search_actions']
        if name=='negative':
            assert not c['claim']['accepted'] and c['claim']['exception']=='SearchBudgetExhausted'
            assert b=={'max':-1,'used':0,'remaining':-1}
            assert rows['budget_reservations']==[] and rows['search_actions'][0]['status']=='pending'
        else:
            assert c['claim']['accepted'] and c['claim']['result']['claimed']
            assert len(rows['budget_reservations'])==1 and rows['budget_reservations'][0]['status']=='reserved'
            assert rows['search_actions'][0]['status']=='claimed' and b['used']==1
        if name=='clean':
            assert g['accepted'] and b=={'max':10,'used':1,'remaining':9}
        else:
            assert not g['accepted'] and g['exception']=='ValueError'
            if name=='out_of_range':assert b=={'max':1001,'used':1,'remaining':1000}
            elif name=='bool_limit':assert c['input_policy']['search_limits']['max_total_search_actions'] is True and b=={'max':1,'used':1,'remaining':0}
            elif name=='unknown_key':assert c['input_policy']['search_limits']['made_up_limit']==1 and b=={'max':10,'used':1,'remaining':9}
        emit('policy',name,classification='legal_control' if name=='clean' else 'observed_policy_first_consumer_gap')
    print(json.dumps(dict(all_observed_assertions_passed=True,request_cases=11,metadata_records=1,footer_records=0,policy_cases=5,
                         gaps_still_present=True,legal_controls_preserved=True,external_model_calls_observed=0,probe_or_pytest_bodies_executed_by_assertion=False),sort_keys=True))
    return 0
if __name__=='__main__':raise SystemExit(main())
