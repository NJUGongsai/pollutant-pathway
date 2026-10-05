"""M1 + M3 offline computation (zero LLM; gold opened only in this process).

Inputs (gitignored work dir): m1_dump/answers_*.jsonl, m1_dump/meta_*.json,
m1_dump/pools_*.json; dev_gold/dev_gold.jsonl; dev_questions.jsonl.
Output: m1_m3_detail.json (per-question flags, may contain counts/ranks only,
no SMILES except intermediate identities used locally).
"""
import json, sys
from pathlib import Path

sys.path.insert(0, '/Volumes/CC/Enzyme_Agent/dependingv43/src')
WORK = Path('/Volumes/CC/Enzyme_Agent/dependingv43/reports/phase_s1_hit60/dev_gold/coverage_stat_work')
REPO = Path('/Volumes/CC/Enzyme_Agent/dependingv43/reports/phase_s1_hit60')

from pathway_v43.exam_v2 import load_gold, agent_candidates, first_hit_rank
from pathway_v43.domain.identity import cn_identity

TAGS = ['C0a', 'C0b', 'E1', 'E2a', 'E2b', 'E3']

gold = load_gold(REPO / 'dev_gold' / 'dev_gold.jsonl')
# question substrate identities (for later M2-style analyses; local only)
substrate = {}
for line in (REPO / 'dev_questions.jsonl').read_text(encoding='utf-8').splitlines():
    if line.strip():
        rec = json.loads(line)
        substrate[rec['qid']] = cn_identity(rec['root_smiles'])

def gold_exact(g):
    out = set()
    for p in g['products_smiles']:
        out.add(p)
    return out

out = {}
for tag in TAGS:
    answers = {}
    for line in (WORK / 'm1_dump' / f'answers_{tag}.jsonl').read_text(encoding='utf-8').splitlines():
        if line.strip():
            rec = json.loads(line)
            answers[rec['route_id']] = rec
    meta = json.loads((WORK / 'm1_dump' / f'meta_{tag}.json').read_text(encoding='utf-8'))
    pools = json.loads((WORK / 'm1_dump' / f'pools_{tag}.json').read_text(encoding='utf-8'))
    rows = []
    for qid in sorted(gold):
        g = gold[qid]
        route = meta['routes'].get(qid, '?')
        products = agent_candidates(answers[qid])
        rank_w = first_hit_rank(products, g['gold_ids'], component_mode=False)
        rank_c = first_hit_rank(products, g['gold_ids'], component_mode=True)
        # position of first whole-string gold hit
        pos_whole = rank_w
        # component-level positions: positions whose candidate has a component identity in gold
        comp_positions = []
        for i, p in enumerate(products, 1):
            idents = [cn_identity(part) for part in p.split('.')] if '.' in p else [cn_identity(p)]
            if any(i2 in g['gold_ids'] for i2 in idents if i2):
                comp_positions.append(i)
        # which gold ids are covered as components (any position)
        covered = set()
        for p in products:
            idents = [cn_identity(part) for part in p.split('.')] if '.' in p else [cn_identity(p)]
            for i2 in idents:
                if i2 and i2 in g['gold_ids']:
                    covered.add(i2)
        # evidence pool membership (audit caliber: cn identity OR exact string)
        pool = pools.get(qid, {})
        pool_ids = set(pool.get('ids', []))
        pool_smis = set(pool.get('smiles', []))
        gold_in_pool_ids = bool(g['gold_ids'] & pool_ids)
        gold_in_pool_exact = bool(gold_exact(g) & pool_smis)
        gold_in_pool = gold_in_pool_ids or gold_in_pool_exact
        n_gold_covered = len(covered)
        rows.append({
            'qid': qid, 'route': route, 'n_pred': len(products),
            'rank_whole': rank_w, 'rank_comp': rank_c,
            'gold_in_answer_whole': rank_w is not None,
            'gold_in_answer_component': rank_c is not None,
            'n_gold_components_covered': n_gold_covered,
            'n_gold_ids': len(g['gold_ids']),
            'gold_in_pool': gold_in_pool,
            'gold_in_pool_ids': gold_in_pool_ids,
            'gold_in_pool_exact': gold_in_pool_exact,
            'n_pool_cards': pool.get('n_cards', 0),
        })
    out[tag] = rows

(WORK / 'm1_m3_detail.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True), encoding='utf-8')

# ---- integrity cross-check: rank_whole vs official per_question.tsv
print('=== integrity: rank_whole vs official scoring tsv')
BASE = REPO / 'artifacts_remote'
batchdirs = {'C0a': 's1_dev_C0_20260929T182619Z', 'C0b': 's1_dev_C0_20260929T190054Z',
             'E1': 's1_dev_E1_20260930T023702Z', 'E2a': 's1_dev_E2_20260929T192739Z',
             'E2b': 's1_dev_E2_20260929T201603Z', 'E3': 's1_dev_E3_20260929T204506Z'}
for tag in TAGS:
    official = {}
    for line in (BASE / batchdirs[tag] / 'scoring' / 'per_question.tsv').read_text(encoding='utf-8').splitlines()[1:]:
        fs = line.split('\t')
        official[fs[0]] = fs[2]
    diff = 0
    for r in out[tag]:
        ov = official[r['qid']]
        ov = None if ov == '' else int(ov)
        if ov != r['rank_whole']:
            diff += 1
            print('DIFF', tag, r['qid'], ov, r['rank_whole'])
    print(tag, 'rank diffs vs official:', diff)

# ---- headline tables
print()
print('=== M3 dual track @1/@3/@5 (whole vs component)')
for tag in TAGS:
    rows = out[tag]
    def hits(key, k):
        return sum(1 for r in rows if r[key] is not None and r[key] <= k)
    print(f"{tag}: whole @1/@3/@5 = {hits('rank_whole',1)}/{hits('rank_whole',3)}/{hits('rank_whole',5)}"
          f"  component @1/@3/@5 = {hits('rank_comp',1)}/{hits('rank_comp',3)}/{hits('rank_comp',5)}"
          f"  delta@1={hits('rank_comp',1)-hits('rank_whole',1)}")

print()
print('=== M1 route x position cross-tab')
for tag in TAGS:
    rows = out[tag]
    from collections import Counter
    c = Counter()
    for r in rows:
        if r['rank_whole'] == 1:
            bucket = '@1'
        elif r['rank_whole'] is not None and r['rank_whole'] <= 5:
            bucket = '2-5'
        else:
            bucket = 'not_in_5'
        c[(r['route'], bucket)] += 1
    print(tag, dict(c))

print()
print('=== gold@2-5 questions and their routes')
for tag in ['C0a', 'C0b', 'E1']:
    lst = [(r['qid'], r['route'], r['rank_whole']) for r in out[tag]
           if r['rank_whole'] is not None and 2 <= r['rank_whole'] <= 5]
    print(tag, len(lst), lst)

print()
print('=== pool membership totals (audit caliber cn-or-exact)')
for tag in TAGS:
    n_pool = sum(1 for r in out[tag] if r['gold_in_pool'])
    n_pool_ids = sum(1 for r in out[tag] if r['gold_in_pool_ids'])
    print(tag, 'gold_in_pool:', n_pool, '(ids-only:', n_pool_ids, ')')

print()
print('=== C0b 2x2 (pool x top5) for audit reconciliation')
rows = out['C0b']
from collections import Counter
c2 = Counter()
for r in rows:
    hit5 = r['rank_whole'] is not None and r['rank_whole'] <= 5
    c2[(r['gold_in_pool'], hit5)] += 1
print('in_pool&hit:', c2[(True, True)], 'in_pool&miss:', c2[(True, False)],
      'not_pool&hit:', c2[(False, True)], 'not_pool&miss:', c2[(False, False)])
for tag in TAGS:
    rows = out[tag]
    c3 = Counter()
    for r in rows:
        hit5 = r['rank_whole'] is not None and r['rank_whole'] <= 5
        c3[(r['gold_in_pool'], bool(hit5))] += 1
    print(tag, dict(c3))
