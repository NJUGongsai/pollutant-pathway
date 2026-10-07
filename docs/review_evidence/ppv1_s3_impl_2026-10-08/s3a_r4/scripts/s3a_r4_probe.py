#!/usr/bin/env python3
"""S3a-r4 finite probe (Codex R3 residual S3A-02/03/04; synthetic only).

Replicates the R3 review's counterexample matrices on the r4 source with
full before/after table snapshots per case:
- S3A-02 necessary-reference subset: 9 entrances x 3 necessary reservation
  keys x {clean, remove_ref_only, remove_ref_and_row} (same construction as
  authority_specialist/necessary_reference_probe.py);
- S3A-03 request status entries under 6 damaged frozen policy blocks x
  {sent, response, failed} + legal control (same damages as
  budget_request_specialist/extra_probe.py);
- S3A-04 unknown-status lifecycle at {sent, response, failed, register,
  recover}.

All inputs synthetic (CCO -> CC=O). Zero network, zero external model.
Writes only to --out (fresh dir outside the repo); no DB files archived
(they stay in the tmp root, listed in omitted_databases.json).
"""
from pathlib import Path
from dataclasses import asdict
import json
import sys
import time

P = Path(__file__).resolve().parent
sys.path[:0] = [str(P / 'repo' / 'src'), str(P / 'repo' / 'tests')]

from s3a_worker import make_fixture  # noqa: E402
from pathway_v43.pollutant.profile import build_profile_identity_block  # noqa: E402
from pathway_v43.pollutant.search import (  # noqa: E402
    SearchLedger, search_policy_version)
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402

TABLES = ['meta', 'states', 'state_appearances', 'hypotheses', 'events',
          'report_projections', 'expansion_plans', 'event_appearance_links',
          'search_runs', 'search_actions', 'search_attempts',
          'budget_reservations', 'model_requests', 'search_commit_records']


def snap(ledger):
    return {t: [dict(r) for r in ledger.conn.execute(
        'SELECT * FROM ' + t + ' ORDER BY rowid')] for t in TABLES}


def cap(fn):
    try:
        return {'accepted': True, 'result': fn()}
    except Exception as e:  # noqa: BLE001
        return {'accepted': False, 'exception': type(e).__name__,
                'kind': getattr(e, 'detail', {}).get('kind'),
                'message': str(e)}


def emit(OUT, ROWS, row):
    ROWS.append(row)
    print(json.dumps(row, ensure_ascii=False, sort_keys=True,
                     default=str), flush=True)


def mk(name, limits=None):
    d = OUT / name
    d.mkdir(parents=True)
    ledger = SearchLedger(PollutantPathwayStore(d / 'run.sqlite'),
                          ArtifactStore(d / 'runs', name), name)
    policy = build_profile_identity_block(
        search_limits=limits) if limits else build_profile_identity_block()
    ledger.register_search_run(name, policy)
    sub, prod, hyp, event, args = make_fixture(name, 'p1', 'k1', 'ctx1')
    aid = ledger.enqueue_action(
        run_id=name, parent_path_id='p1', context_ref='ctx1',
        subject_ref=hyp.hypothesis_id, action_kind='expand_hypothesis',
        depth=1, policy_version=search_policy_version(),
        payload={'task_key': 'tk1'})['action_id']
    rec = ledger.claim_action(aid, worker_id='w1')
    return d, ledger, policy, event, args, aid, rec


def reg(ledger, action_id, attempt_id, request_key='rk'):
    return ledger.register_model_request(
        run_id=ledger.run_id, action_id=action_id, attempt_id=attempt_id,
        provider_kind='scripted', request_key=request_key,
        purpose='rank', payload={'prompt': 'original'})


def mutate(ledger, sql, params):
    ledger.conn.execute(sql, params)
    ledger.conn.commit()


def statusfn(ledger, request_id, entry):
    return {
        'sent': lambda: ledger.record_request_sent(request_id),
        'response': lambda: ledger.record_request_response(
            request_id, 'response_A'),
        'failed': lambda: ledger.mark_request_failed(request_id),
    }[entry]()


if __name__ == '__main__':
    OUT = Path(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=False)
    ROWS = []
    OMITTED = []
    start = time.monotonic()

    # ---- S3A-02: necessary-reference subset (9 x {clean,2 modes} x 3) ----
    for phase in ['first_complete', 'B4_recover', 'B1_recover',
                  'B3_recover', 'done_recover', 'done_claim',
                  'done_complete', 'done_submit', 'defer']:
        for mutation in ['clean', 'remove_ref_only',
                         'remove_ref_and_row']:
            keys = (['max_total_search_actions'] if mutation == 'clean'
                    else ['max_total_search_actions',
                          'max_alternative_hypotheses_per_parent',
                          'max_attempts_per_hypothesis'])
            for key in keys:
                name = phase + '__' + mutation + '__' + key
                d, l, pol, e, args, aid, rec = mk(name)
                artifact = None
                if phase == 'B3_recover':
                    l.write_commit_bundle(
                        action_id=aid, attempt_id=rec['attempt_refs'][0],
                        event=e, task_key='tk1', **args)
                    artifact = l.artifact_store._path(
                        'tk1', 'search_commit_bundle')
                    original_artifact = artifact.read_bytes()
                elif phase not in ['B1_recover', 'defer']:
                    l.submit_action_event(aid, e, worker_id='w1', **args)
                if phase.startswith('done_'):
                    l.complete_action(aid, worker_id='w1',
                                      event_id=e.event_id)
                original = snap(l)
                rid = l.conn.execute(
                    'SELECT reservation_id FROM budget_reservations WHERE'
                    ' action_id = ? AND limit_key = ?', (aid, key)
                ).fetchone()[0]
                if mutation != 'clean':
                    refs = json.loads(l.conn.execute(
                        'SELECT budget_reservation_ref FROM search_actions'
                        ' WHERE action_id = ?', (aid,)).fetchone()[0])
                    refs.remove(rid)
                    l.conn.execute(
                        'UPDATE search_actions SET budget_reservation_ref'
                        ' = ? WHERE action_id = ?',
                        (json.dumps(refs), aid))
                    if mutation == 'remove_ref_and_row':
                        l.conn.execute(
                            'DELETE FROM budget_reservations WHERE'
                            ' reservation_id = ?', (rid,))
                    l.conn.commit()
                before = snap(l)
                l.store.close()
                l = SearchLedger(PollutantPathwayStore(d / 'run.sqlite'),
                                 ArtifactStore(d / 'runs', name), name)
                if phase in ['first_complete', 'done_complete']:
                    fn = lambda: l.complete_action(  # noqa: E731
                        aid, worker_id='w1', event_id=e.event_id)
                elif phase == 'done_claim':
                    fn = lambda: l.claim_action(  # noqa: E731
                        aid, worker_id='new-worker')
                elif phase == 'done_submit':
                    fn = lambda: l.submit_action_event(  # noqa: E731
                        aid, e, worker_id='w1', **args)
                elif phase == 'defer':
                    fn = lambda: l.defer_action(  # noqa: E731
                        aid, worker_id='w1', reason='no_new_information')
                else:
                    fn = lambda: l.recover_run(name, policy_block=pol)  # noqa: E731
                result = cap(fn)
                after = snap(l)
                expected = ('accepted lawful behavior' if mutation == 'clean'
                            else 'structured refusal before any new'
                                 ' successful consumption')
                ok = (result['accepted'] if mutation == 'clean'
                      else (not result['accepted'] and result.get('kind') in
                            ('reservation_row_missing',
                             'necessary_reservation_ref_missing')
                            and before['search_actions'] ==
                            after['search_actions']
                            and before['search_commit_records'] ==
                            after['search_commit_records']
                            and before['events'] == after['events']))
                emit(OUT, ROWS, {
                    'case': name, 'group': 'S3A-02', 'expected': expected,
                    'input': {'phase': phase, 'mutation': mutation,
                              'removed_limit_key': key,
                              'removed_reservation_id': rid,
                              'action_id': aid, 'receipt': rec,
                              'event': asdict(e), 'event_args': args,
                              'policy': pol},
                    'original': original, 'before': before,
                    'result': result, 'after': after,
                    'artifact_preserved': (
                        True if artifact is None
                        else artifact.read_bytes() == original_artifact),
                    'checks': {'contract_passed': bool(ok)},
                    'actual_network_requests': 0})
                OMITTED.append({'case': name,
                                'db': str(d / 'run.sqlite'),
                                'bytes': (d / 'run.sqlite').stat().st_size})
                l.store.close()

    # ---- S3A-03: request status entries under damaged frozen policy ----
    for damage in ['null_limits', 'missing_version', 'bool',
                   'out_of_range', 'unknown_key', 'negative', 'legal']:
        for entry in ['sent', 'response', 'failed']:
            name = 'policy_request_' + damage + '_' + entry
            d, l, pol, e, args, aid, rec = mk(name)
            r = reg(l, aid, rec['attempt_refs'][0])
            if entry == 'response':
                l.record_request_sent(r['request_id'])
            frozen = json.loads(json.dumps(pol))
            stored = json.loads(json.dumps(pol))
            if damage == 'null_limits':
                stored['search_limits'] = None
            elif damage == 'missing_version':
                stored['search_limits'] = {
                    k: v for k, v in stored['search_limits'].items()
                    if k != 'version'}
            elif damage == 'bool':
                stored['search_limits'][
                    'max_total_search_actions'] = True
            elif damage == 'out_of_range':
                stored['search_limits'][
                    'max_total_search_actions'] = 1001
            elif damage == 'unknown_key':
                stored['search_limits']['unregistered_key'] = 1
            elif damage == 'negative':
                stored['search_limits'][
                    'max_total_search_actions'] = -1
            if damage != 'legal':
                mutate(l, 'UPDATE search_runs SET policy_block = ? WHERE'
                       ' run_id = ?', (json.dumps(stored), name))
            b = snap(l)
            o = cap(lambda: statusfn(l, r['request_id'], entry))  # noqa: E731
            af = snap(l)
            status_before = b['model_requests'][0]['status']
            expected = ('accepted lawful local lifecycle'
                        if damage == 'legal'
                        else 'structured policy rejection before any'
                             ' success write')
            ok = (o['accepted'] if damage == 'legal'
                  else (not o['accepted']
                        and o.get('kind') == 'search_policy_block_corrupt'
                        and b == af))
            emit(OUT, ROWS, {
                'case': name, 'group': 'S3A-03', 'expected': expected,
                'input': {'original_frozen_policy': frozen,
                          'stored_policy': stored, 'damage': damage,
                          'entry': entry, 'request': r,
                          'status_before': status_before},
                'before': b, 'observed': o, 'after': af,
                'checks': {'contract_passed': bool(ok)},
                'actual_network_requests': 0})
            OMITTED.append({'case': name, 'db': str(d / 'run.sqlite'),
                            'bytes': (d / 'run.sqlite').stat().st_size})
            l.store.close()

    # ---- S3A-04: unknown stored status at every consumer ----
    for entry in ['sent', 'response', 'failed', 'register', 'recover']:
        name = 'unknown_status_' + entry
        d, l, pol, e, args, aid, rec = mk(name)
        base = dict(run_id=name, action_id=aid,
                    attempt_id=rec['attempt_refs'][0],
                    provider_kind='scripted', request_key='rk',
                    purpose='rank', payload={'prompt': 'original'})
        r = l.register_model_request(**base)
        mutate(l, 'UPDATE model_requests SET status = ? WHERE request_id'
               ' = ?', ('corrupt-status', r['request_id']))
        b = snap(l)
        if entry in ['sent', 'response', 'failed']:
            fn = lambda: statusfn(l, r['request_id'], entry)  # noqa: E731
        elif entry == 'register':
            fn = lambda: l.register_model_request(**base)  # noqa: E731
        else:
            fn = lambda: l.recover_run(name)  # noqa: E731
        o = cap(fn)
        af = snap(l)
        recovered_unknown = []
        if entry == 'recover' and o['accepted']:
            recovered_unknown = [
                u['request_id']
                for u in (o['result'].get('unknown_status_requests') or [])]
        ok = (not o['accepted'] and b == af) if entry != 'recover' else (
            o['accepted'] and b == af
            and recovered_unknown == [r['request_id']]
            and all(p['request_id'] != r['request_id']
                    for p in o['result']['pending_requests']))
        emit(OUT, ROWS, {
            'case': name, 'group': 'S3A-04',
            'expected': 'unknown stored lifecycle is rejected or disclosed'
                        ' as explicit integrity failure, never migrated to'
                        ' a successful known state',
            'input': {'mutation': 'model_requests.status=corrupt-status',
                      'entry': entry, 'same_original_request': r},
            'before': b, 'observed': o, 'after': af,
            'disclosed_unknown_status': recovered_unknown,
            'checks': {'contract_passed': bool(ok)},
            'actual_network_requests': 0})
        OMITTED.append({'case': name, 'db': str(d / 'run.sqlite'),
                        'bytes': (d / 'run.sqlite').stat().st_size})
        l.store.close()

    (OUT / 'probe_observations.json').write_text(
        json.dumps(ROWS, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'omitted_databases.json').write_text(
        json.dumps(OMITTED, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'summary': {'cases': len(ROWS),
                                  'network_requests': 0,
                                  'external_model_calls': 0,
                                  'elapsed_seconds': round(
                                      time.monotonic() - start, 3)}}))
