import json, glob, os, sys, tarfile, base64
from collections import Counter

BASE = '/usrdata/EnzymeCAGE_data/workspaces/dependingv43_s1/runs'
BATCHES = [
    ('C0a', 's1_dev_C0_20260929T182619Z'),
    ('C0b', 's1_dev_C0_20260929T190054Z'),
    ('E2a', 's1_dev_E2_20260929T192739Z'),
    ('E2b', 's1_dev_E2_20260929T201603Z'),
    ('E3',  's1_dev_E3_20260929T204506Z'),
    ('E1',  's1_dev_E1_20260930T023702Z'),
]
E3_RANK_QIDS = {'b1_BIOPATH150_008__S01__BSY-r00616',
                'b1_BIOPATH150_010__S02__BSY-r01369',
                'b1_BIOPATH150_010__S04__BSY-r01371'}

def qid_of(dirname):
    parts = dirname.split('_', 2)
    return parts[2] if len(parts) == 3 else dirname

def main():
    outdir = '/tmp/m1_dump'
    os.makedirs(outdir, exist_ok=True)
    for tag, b in BATCHES:
        root = os.path.join(BASE, b)
        ans = open(os.path.join(root, 'merged', 'predictions.jsonl'),
                   encoding='utf-8').read()
        with open(os.path.join(outdir, f'answers_{tag}.jsonl'), 'w',
                  encoding='utf-8') as f:
            f.write(ans)
        routes, pools, task_hashes = {}, {}, {}
        for qdir in sorted(glob.glob(os.path.join(root, 'runs', '*'))):
            qid = qid_of(os.path.basename(qdir))
            mode_seen = ''
            for df in glob.glob(os.path.join(qdir, 'results', '*', 'decision.json')):
                try:
                    pl = json.load(open(df)).get('payload', {})
                except Exception:
                    continue
                m = pl.get('prediction_mode', '')
                if m:
                    mode_seen = m
            routes[qid] = mode_seen or 'recorded'
            ids, smis = set(), set()
            ncards, n_verd, n_acc = 0, 0, 0
            kinds = Counter()
            for cf in glob.glob(os.path.join(qdir, 'results', '*', 'cardval.*.json')):
                ncards += 1
                try:
                    pl = json.load(open(cf)).get('payload', {})
                except Exception:
                    continue
                kinds[pl.get('kind', '?')] += 1
                for v in (pl.get('verdicts') or []):
                    n_verd += 1
                    if v.get('accepted'):
                        n_acc += 1
                    pi = v.get('product_identity')
                    if pi:
                        ids.add(pi)
                    ps = v.get('product_smiles')
                    if ps:
                        smis.add(ps)
            pools[qid] = {'n_cards': ncards, 'kinds': dict(kinds),
                          'n_verdicts': n_verd, 'n_accepted': n_acc,
                          'ids': sorted(ids), 'smiles': sorted(smis)}
            for tf in glob.glob(os.path.join(qdir, 'results', '*', 'prediction_task.json')):
                try:
                    t = json.load(open(tf))
                except Exception:
                    continue
                pl = t.get('payload', {}) or {}
                task_hashes[qid] = {'mode': pl.get('mode'),
                                    'n_cand': len(pl.get('candidates') or []),
                                    'payload_hash': t.get('payload_hash'),
                                    'task_id': t.get('task_id')}
        with open(os.path.join(outdir, f'meta_{tag}.json'), 'w', encoding='utf-8') as f:
            json.dump({'routes': routes, 'task_hashes': task_hashes},
                      f, ensure_ascii=False, sort_keys=True)
        with open(os.path.join(outdir, f'pools_{tag}.json'), 'w', encoding='utf-8') as f:
            json.dump(pools, f, ensure_ascii=False, sort_keys=True)
        sys.stderr.write(f'done {tag} routes={len(routes)} pools={len(pools)}\n')
    # E3 rank-question retrieval evidence detail (full funnel)
    e3detail = {}
    root = os.path.join(BASE, 's1_dev_E3_20260929T204506Z')
    for qdir in sorted(glob.glob(os.path.join(root, 'runs', '*'))):
        qid = qid_of(os.path.basename(qdir))
        if qid not in E3_RANK_QIDS:
            continue
        for rf in glob.glob(os.path.join(qdir, 'results', '*', 'retrieval.json')):
            pl = json.load(open(rf)).get('payload', {})
            evs = []
            for e in pl.get('evidences', []):
                evs.append({k: e.get(k) for k in (
                    'evidence_id', 'kind', 'retrieval_rank', 'match_type',
                    'mapping_status', 'reactant_smiles', 'reactant_identity',
                    'products', 'asset_file', 'source_id', 'score',
                    'score_semantics')})
            e3detail[qid] = evs
    with open(os.path.join(outdir, 'e3_rank_retrieval.json'), 'w', encoding='utf-8') as f:
        json.dump(e3detail, f, ensure_ascii=False, sort_keys=True)
    # C0a same detail for payload identity comparison
    c0detail = {}
    root = os.path.join(BASE, 's1_dev_C0_20260929T182619Z')
    for qdir in sorted(glob.glob(os.path.join(root, 'runs', '*'))):
        qid = qid_of(os.path.basename(qdir))
        if qid not in E3_RANK_QIDS:
            continue
        for tf in glob.glob(os.path.join(qdir, 'results', '*', 'prediction_task.json')):
            t = json.load(open(tf))
            pl = t.get('payload', {}) or {}
            c0detail[qid] = {'mode': pl.get('mode'),
                             'n_cand': len(pl.get('candidates') or []),
                             'payload_hash': t.get('payload_hash')}
    with open(os.path.join(outdir, 'c0a_rank_task.json'), 'w', encoding='utf-8') as f:
        json.dump(c0detail, f, ensure_ascii=False, sort_keys=True)
    tarpath = '/tmp/m1_dump.tar.gz'
    with tarfile.open(tarpath, 'w:gz') as tf:
        for fn in sorted(os.listdir(outdir)):
            tf.add(os.path.join(outdir, fn), arcname=fn)
    raw = open(tarpath, 'rb').read()
    b64 = base64.b64encode(raw).decode('ascii')
    sys.stderr.write(f'tar.gz bytes={len(raw)} b64={len(b64)}\n')
    print('===BEGIN_B64===')
    for i in range(0, len(b64), 4000):
        print(b64[i:i+4000])
    print('===END_B64===')

main()
