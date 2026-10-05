import json
from pathlib import Path
WORK = Path('.')
OUT = Path('/Volumes/CC/Enzyme_Agent/dependingv43/reports/phase_s1_hit60/coverage_stat')
det = json.loads((WORK / 'm1_m3_detail.json').read_text(encoding='utf-8'))
TAGS = ['C0a', 'C0b', 'E1', 'E2a', 'E2b', 'E3']
cols = ['qid', 'route', 'n_pred', 'rank_whole', 'rank_comp', 'hit1_whole', 'hit3_whole',
        'hit5_whole', 'hit1_comp', 'hit3_comp', 'hit5_comp', 'gold_in_pool',
        'n_gold_ids', 'n_gold_components_covered', 'bucket']
def bucket(r):
    if r['rank_whole'] == 1:
        return 'at1'
    if r['rank_whole'] is not None and r['rank_whole'] <= 5:
        return 'gold_2to5'
    if r['rank_comp'] is not None and r['rank_comp'] <= 5:
        return 'B_component_rescuable'
    if r['gold_in_pool']:
        return 'C1_pool_but_missed'
    return 'C2_not_in_pool'
def fmt(v):
    if v is None: return ''
    if isinstance(v, bool): return 'true' if v else 'false'
    return str(v)
for tag in TAGS:
    rows = det[tag]
    lines = ['\t'.join(cols)]
    for r in rows:
        r2 = dict(r)
        r2['bucket'] = bucket(r)
        for k, kk in [('rank_whole','hit1_whole')]: pass
        r2['hit1_whole'] = r['rank_whole'] is not None and r['rank_whole'] <= 1
        r2['hit3_whole'] = r['rank_whole'] is not None and r['rank_whole'] <= 3
        r2['hit5_whole'] = r['rank_whole'] is not None and r['rank_whole'] <= 5
        r2['hit1_comp'] = r['rank_comp'] is not None and r['rank_comp'] <= 1
        r2['hit3_comp'] = r['rank_comp'] is not None and r['rank_comp'] <= 3
        r2['hit5_comp'] = r['rank_comp'] is not None and r['rank_comp'] <= 5
        lines.append('\t'.join(fmt(r2.get(c)) for c in cols))
    (OUT / f'qid_flags_{tag}.tsv').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(tag, 'written', len(rows))
