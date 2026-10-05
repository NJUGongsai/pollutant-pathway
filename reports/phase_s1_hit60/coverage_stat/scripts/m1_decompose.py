"""M1 detailed decomposition: for @1-missed questions, rerankable vs generation-bound."""
import json
from pathlib import Path
from collections import Counter

WORK = Path('/Volumes/CC/Enzyme_Agent/dependingv43/reports/phase_s1_hit60/dev_gold/coverage_stat_work')
det = json.loads((WORK / 'm1_m3_detail.json').read_text(encoding='utf-8'))

def short(qid):
    return qid.replace('b1_BIOPATH150_', '').replace('__BSY-r', '#')

for tag in ['C0a', 'C0b', 'E1', 'E3']:
    rows = det[tag]
    print(f'===== {tag}: @1-miss decomposition (n={sum(1 for r in rows if r["rank_whole"]!=1)})')
    buckets = Counter()
    detail = {'A_2to5': [], 'B_comp': [], 'C1_pool_novel': [], 'C1_pool_other': [], 'C2_nopool': []}
    for r in rows:
        if r['rank_whole'] == 1:
            continue
        rw, rc, route = r['rank_whole'], r['rank_comp'], r['route']
        if rw is not None and rw <= 5:
            buckets[('A', route)] += 1
            detail['A_2to5'].append((short(r['qid']), route, rw))
        elif rc is not None and rc <= 5:
            buckets[('B', route)] += 1
            detail['B_comp'].append((short(r['qid']), route, rw, rc, r['n_gold_components_covered'], r['n_gold_ids']))
        elif r['gold_in_pool']:
            buckets[('C1', route)] += 1
            (detail['C1_pool_novel'] if route == 'novel_proposal' else detail['C1_pool_other']).append((short(r['qid']), route))
        else:
            buckets[('C2', route)] += 1
            detail['C2_nopool'].append((short(r['qid']), route))
    print(' bucket counts (bucket, route):', dict(buckets))
    for k, v in detail.items():
        print(f'  {k} ({len(v)}):', v)

print()
print('===== M3 rescued-at-@1 qid lists (component caliber)')
for tag in ['C0a', 'C0b', 'E1', 'E2a', 'E2b', 'E3']:
    rescued = [short(r['qid']) for r in det[tag] if r['rank_whole'] != 1 and r['rank_comp'] == 1]
    print(tag, len(rescued), rescued)

print()
print('===== mimo claim checks on E1 (review basis) and C0a')
def first_multi(tag):
    # first product multi-component questions
    answers = {}
    for line in (WORK / 'm1_dump' / f'answers_{tag}.jsonl').read_text(encoding='utf-8').splitlines():
        if line.strip():
            rec = json.loads(line)
            answers[rec['route_id']] = rec
    out = []
    for r in det[tag]:
        rec = answers[[k for k in answers if k == r['qid']][0]]
        prods = [p for s in rec['steps'] for p in s.get('predicted_products', [])]
        if prods and '.' in prods[0]:
            out.append((short(r['qid']), r['rank_whole'], r['rank_comp'], r['n_gold_components_covered'], r['n_gold_ids'], None))
    return out
for tag in ['E1', 'C0a']:
    print(tag, 'first-product multi-component:', [(a, b, c, d, e) for a, b, c, d, e, _ in first_multi(tag)])

print()
print('===== E1 L1-type sensitivity: C0a gold@2-5 band vs E1 outcome')
band = {r['qid']: r['rank_whole'] for r in det['C0a'] if r['rank_whole'] is not None and 2 <= r['rank_whole'] <= 5}
e1 = {r['qid']: r['rank_whole'] for r in det['E1']}
for qid in band:
    print(short(qid), 'C0a rank', band[qid], '-> E1 rank', e1[qid])
