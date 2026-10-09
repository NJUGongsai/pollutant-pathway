from __future__ import annotations
import json

AFTER = '/private/tmp/ppv1_s5a_r3_mimo_r1_k4q7'
BEFORE = '/private/tmp/ppv1_s5a_r3_mimo_before_p39d739d'


def load(p):
    return json.load(open(p))


adj = {'round': 'S5a rework r3 five-case adjudication',
       'probe': {
           'source': ('docs/review_evidence/ppv1_s5a_codex_r3_2026-10-09/'
                      'mimo/scripts/probe.py copied byte-faithful (sha256 '
                      '4e0000f2ca8cc22ef870d991421a55d43c3b1e6c5f301241f'
                      '2dae2b0c07db9f2) to fresh tmp trees; cases 1-3 '
                      'reuse the review real public inputs; case 4/5 '
                      'scripts are r3-constructed and NOT claimed '
                      'review-executed'),
           'after_tree': AFTER, 'before_tree': BEFORE, 'cases': []}}
for mode in ('control', 'old_id_resealed', 'new_id_resealed'):
    a = load(f'{AFTER}/package/results/public_restore/{mode}.json')
    b = load(f'{BEFORE}/package/results/public_restore/{mode}.json')
    if mode in ('control', 'old_id_resealed'):
        verdict = 'preserved'
    else:
        verdict = ('FLIPPED: old-address self-consistent new identity '
                   'now rejected at first consumption (binding '
                   'mismatch), zero bad-context events')
    adj['probe']['cases'].append({
        'mode': mode,
        'before': {'load_ok': b['production_load']['ok'],
                   'resume_ok': b['resume']['ok'],
                   'load_kind': (b['production_load'].get('detail')
                                 or {}).get('kind'),
                   'events': len(b['business_tables_after'].get(
                       'events', []))},
        'after': {'load_ok': a['production_load']['ok'],
                  'resume_ok': a['resume']['ok'],
                  'load_kind': (a['production_load'].get('detail')
                                or {}).get('kind'),
                  'events': len(a['business_tables_after'].get(
                      'events', []))},
        'after_per_table_counts': {
            k: len(v) for k, v in a['business_tables_after'].items()},
        'verdict': verdict})
c4a = load(f'{AFTER}/package/results/'
           'r3_case4_checked_legal_old_address.json')
c4b = load(f'{BEFORE}/package/results/'
           'r3_case4_checked_legal_old_address.json.observe')
c5a = load(f'{AFTER}/package/results/'
           'r3_case5_legal_new_address_chain.json')
c5b = load(f'{BEFORE}/package/results/'
           'r3_case5_legal_new_address_chain.json.observe')
adj['case4'] = {
    'origin': ('r3-constructed (review R3 section 4.2 case 4 was NOT '
               'executed by the review; its planned fixture was '
               'platform-blocked there; not claimed review-executed)'),
    'before': {'old_address_load_ok': c4b['load']['old_address_load'][
                   'ok'],
               'public_resume_ok': c4b['public']['resume']['ok'],
               'events': c4b['public']['table_counts_after'].get(
                   'events')},
    'after': {'old_address_load_ok': c4a['load']['old_address_load'][
                  'ok'],
              'old_address_load_kind': c4a['load'][
                  'old_address_load']['detail']['kind'],
              'new_address_load_ok': c4a['load']['new_address_load'][
                  'ok'],
              'public_resume_ok': c4a['public']['resume']['ok'],
              'events': c4a['public']['table_counts_after'].get(
                  'events'),
              'table_deltas': c4a['public']['table_deltas'],
              'artifact_preserved': c4a['public']['artifact_preserved']},
    'verdict': ('FLIPPED: checked-legal new content at the old address '
                'rejected (same guard; content legality does not exempt '
                'address binding); the same payload at its own new '
                'address stays legal')}
adj['case5'] = {
    'origin': ('r3-constructed (review R3 section 8 case 5 must be '
               'constructed; positive control)'),
    'before': {'child_load_ok': c5b['load']['child_load']['ok'],
               'public_resume_ok': c5b['public']['resume']['ok'],
               'address_identity_all_match': all(
                   e['match'] for e in
                   c5b['public']['ctx_address_identity'])},
    'after': {'child_load_ok': c5a['load']['child_load']['ok'],
              'public_resume_ok': c5a['public']['resume']['ok'],
              'address_identity_all_match': all(
                  e['match'] for e in
                  c5a['public']['ctx_address_identity']),
              'followup_context_refs':
                  c5a['public']['followup_context_refs'],
              'child_ids': c5a['public']['child_ids'],
              'root_ids': c5a['public']['root_ids']},
    'verdict': ('PRESERVED: legal new content new ID new address + '
                'parent_context_ref chain allowed; scenario transition '
                'child context persisted at the new address and '
                'consumed via the new reference')}
open('/private/tmp/ppv1_s5a_r3_evidence/mimo_cases/'
     'five_case_adjudication.json', 'w').write(
    json.dumps(adj, ensure_ascii=False, indent=2) + '\n')
print('written')
print('case3 verdict:', adj['probe']['cases'][2]['verdict'][:80])
print('case3 after table counts:',
      json.dumps(adj['probe']['cases'][2]['after_per_table_counts'],
                 ensure_ascii=False)[:400])
