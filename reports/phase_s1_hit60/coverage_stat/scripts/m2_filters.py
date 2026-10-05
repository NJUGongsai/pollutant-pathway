"""M2: E3 rank questions — funnel decomposition + mimo §B2 filters ①–④.

Populations:
  CAND = actual rank candidates (eligible recorded cards; 4/2/2)
  P1_8 = retrieval_rank positions 1–8 (old window if eligibility were relaxed)
  P9_16 = retrieval_rank positions 9–16 (the 'extra' cards under window 16)
Filters (operationalized; ⑤ needs human review, skipped):
  ① substrate source: cn(card substrate)==cn(question) -> same;
     else Tanimoto(Morgan r2, 2048) >= 0.55 -> analog (proxy);
     else -> different_source (filter hit)
  ② needs co-substrate: adds P (ATP/CoA/NAD all carry P) or dO >= +2 (O2 equivalents)
  ③ dC(card products vs card substrate) not in {0,-1,-2} -> hit
     (specified cleavage cannot be auto-judged -> flagged subset marked需人审)
  ④ heteroatom add/remove beyond {O,H} -> hit
"""
import json, sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, '/Volumes/CC/Enzyme_Agent/dependingv43/src')
WORK = Path('/Volumes/CC/Enzyme_Agent/dependingv43/reports/phase_s1_hit60/dev_gold/coverage_stat_work')
REPO = Path('/Volumes/CC/Enzyme_Agent/dependingv43/reports/phase_s1_hit60')

from rdkit import Chem, RDLogger
RDLogger.DisableLog('rdApp.*')
from pathway_v43.domain.identity import cn_identity

from rdkit.Chem import AllChem

def formula_counts(smiles):
    """Element counts summed over dot-separated components; None if unparseable."""
    if not smiles:
        return None
    total = Counter()
    for part in smiles.split('.'):
        m = Chem.MolFromSmiles(part)
        if m is None:
            return None
        for atom in m.GetAtoms():
            total[atom.GetSymbol()] += 1
    return total

def fp_bits(smiles):
    m = Chem.MolFromSmiles(smiles) if smiles else None
    if m is None:
        return None
    fp = AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048)
    return fp

def tanimoto(a, b):
    fa, fb = fp_bits(a), fp_bits(b)
    if fa is None or fb is None:
        return None
    return AllChem.DataStructs.TanimotoSimilarity(fa, fb)

# question substrates
qsub = {}
for line in (REPO / 'dev_questions.jsonl').read_text(encoding='utf-8').splitlines():
    if line.strip():
        rec = json.loads(line)
        qsub[rec['qid']] = rec['root_smiles']

d = json.loads((WORK / 'm1_dump' / 'e3_rank_retrieval.json').read_text(encoding='utf-8'))

def analyze_card(ev, qsmiles):
    sub = ev.get('reactant_smiles') or ''
    prods = [p.get('product_smiles', '') for p in (ev.get('products') or [])]
    prod_str = '.'.join(p for p in prods if p)
    sub_f = formula_counts(sub)
    prod_f = formula_counts(prod_str)
    q_f = formula_counts(qsmiles)
    out = {'kind': ev['kind'], 'match_type': ev['match_type'],
           'retrieval_rank': ev.get('retrieval_rank'),
           'parse_ok': sub_f is not None and prod_f is not None}
    if not out['parse_ok']:
        out.update({'f1': None, 'f2': None, 'f3': None, 'f4': None, 'sim': None,
                    'dC_sub': None, 'dC_q': None, 'dO_sub': None,
                    'elem_added': None, 'elem_removed': None})
        return out
    sim = tanimoto(sub, qsmiles)
    sub_cn, q_cn = cn_identity(sub), cn_identity(qsmiles)
    same = sub_cn is not None and q_cn is not None and sub_cn == q_cn
    analog = (not same) and sim is not None and sim >= 0.55
    out['same_substrate'] = same
    out['analog'] = analog
    out['sim'] = round(sim, 3) if sim is not None else None
    out['f1'] = (not same) and (not analog)  # ① hit
    dC_sub = prod_f.get('C', 0) - sub_f.get('C', 0)
    dC_q = prod_f.get('C', 0) - q_f.get('C', 0)
    dO_sub = prod_f.get('O', 0) - sub_f.get('O', 0)
    out['dC_sub'], out['dC_q'], out['dO_sub'] = dC_sub, dC_q, dO_sub
    out['f3'] = dC_sub not in (0, -1, -2)
    out['f3_human_cleave'] = out['f3'] and dC_sub <= -3  # possible specified cleavage
    added = {e for e in prod_f if prod_f[e] > sub_f.get(e, 0)}
    removed = {e for e in sub_f if sub_f[e] > prod_f.get(e, 0)}
    out['elem_added'] = sorted(added)
    out['elem_removed'] = sorted(removed)
    out['f4'] = bool((added | removed) - {'O', 'H'})
    out['f2'] = ('P' in added) or (dO_sub >= 2)
    out['f2_reason'] = ('adds_P' if 'P' in added else '') + \
                       ('|dO>=2' if dO_sub >= 2 else '')
    return out

report = {}
for qid, evs in d.items():
    qs = qsub[qid]
    evs_sorted = sorted(evs, key=lambda e: e['retrieval_rank'])
    cand = [e for e in evs_sorted if e['kind'] == 'recorded_reaction']
    p1_8 = evs_sorted[:8]
    p9_16 = evs_sorted[8:16]
    rows = {'n_total': len(evs),
            'kinds': dict(Counter(e['kind'] for e in evs)),
            'n_recorded': len(cand),
            'n_rank_task_candidates': len(cand),
            'cards': {}}
    for label, pop in (('CAND', cand), ('P1_8', p1_8), ('P9_16', p9_16)):
        analyses = [analyze_card(e, qs) for e in pop]
        rows['cards'][label] = analyses
        rows[f'{label}_summary'] = {
            'n': len(analyses),
            'n_parse_fail': sum(1 for a in analyses if not a['parse_ok']),
            'n_same_substrate': sum(1 for a in analyses if a.get('same_substrate')),
            'n_analog': sum(1 for a in analyses if a.get('analog')),
            'f1_different_source': sum(1 for a in analyses if a.get('f1')),
            'f2_cosubstrate': sum(1 for a in analyses if a.get('f2')),
            'f3_dC_violation': sum(1 for a in analyses if a.get('f3')),
            'f3_of_which_possible_cleavage': sum(1 for a in analyses if a.get('f3_human_cleave')),
            'f4_heteroatom': sum(1 for a in analyses if a.get('f4')),
            'any_of_f1_f3_f4': sum(1 for a in analyses
                                   if a.get('f1') or a.get('f3') or a.get('f4')),
            'pass_hard_f3_f4': sum(1 for a in analyses
                                   if not a.get('f3') and not a.get('f4')),
            'sims': [a['sim'] for a in analyses if a.get('sim') is not None],
            'dC_sub_list': [a['dC_sub'] for a in analyses if a.get('dC_sub') is not None],
            'dC_q_list': [a['dC_q'] for a in analyses if a.get('dC_q') is not None],
        }
    report[qid] = rows

(WORK / 'm2_detail.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True), encoding='utf-8')

# console summary
for qid, rows in report.items():
    print('=====', qid.replace('b1_BIOPATH150_', '').replace('__BSY-r', '#'))
    print(' total ev:', rows['n_total'], 'kinds:', rows['kinds'],
          'recorded(=candidates):', rows['n_recorded'])
    for label in ('CAND', 'P1_8', 'P9_16'):
        s = rows[f'{label}_summary']
        print(f"  {label}: n={s['n']} parse_fail={s['n_parse_fail']} "
              f"same={s['n_same_substrate']} analog={s['n_analog']} "
              f"f1={s['f1_different_source']} f2={s['f2_cosubstrate']} "
              f"f3={s['f3_dC_violation']}(cleavage?{s['f3_of_which_possible_cleavage']}) "
              f"f4={s['f4_heteroatom']} any(1,3,4)={s['any_of_f1_f3_f4']} "
              f"pass(3,4)={s['pass_hard_f3_f4']}")
        print('    dC_sub:', s['dC_sub_list'][:16])
        print('    dC_q:', s['dC_q_list'][:16])
        print('    sims:', s['sims'][:16])
