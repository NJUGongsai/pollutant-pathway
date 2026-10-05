#!/usr/bin/env python3
"""Gate 1 remote extraction (read-only). Compacts retrieval.json + cardval.*.json
for 6 sealed S1 batches x 56 dev questions into /tmp/gate1_dump.tar.gz, prints b64.

Remote side: stdlib only. No writes outside /tmp. Runs dirs are read-only inputs.
"""
import json, glob, os, sys, tarfile, base64
from collections import Counter

BASE = '/usrdata/EnzymeCAGE_data/workspaces/dependingv43_s1/runs'
BATCHES = [
    ('C0a', 's1_dev_C0_20260929T182619Z'),
    ('C0b', 's1_dev_C0_20260929T190054Z'),
    ('E1',  's1_dev_E1_20260930T023702Z'),
    ('E2a', 's1_dev_E2_20260929T192739Z'),
    ('E2b', 's1_dev_E2_20260929T201603Z'),
    ('E3',  's1_dev_E3_20260929T204506Z'),
]

OUT = '/tmp/gate1_extract'
os.makedirs(OUT, exist_ok=True)


def qid_of(dirname):
    parts = dirname.split('_', 2)
    return parts[2] if len(parts) == 3 else dirname


def compact_evidence(e):
    ee = e.get('source_record', {}).get('engine_edge', {}) or {}
    donors = []
    for d in (e.get('donor_refs') or [])[:3]:
        donors.append({
            'reactant_smiles': d.get('reactant_smiles'),
            'similarity': d.get('similarity'),
            'find_channels': d.get('find_channels'),
            'mapping_status': d.get('mapping_status'),
        })
    products = []
    for p in (e.get('products') or []):
        products.append({
            'position': p.get('position'),
            'product_smiles': p.get('product_smiles'),
            'product_smiles_full': p.get('product_smiles_full'),
            'product_identity': p.get('product_identity'),
            'score': p.get('score'),
            'ion_filtered': p.get('ion_filtered'),
            'cofactor_filtered': p.get('cofactor_filtered'),
        })
    return {
        'evidence_id': e.get('evidence_id'),
        'retrieval_rank': e.get('retrieval_rank'),
        'kind': e.get('kind'),
        'match_type': e.get('match_type'),
        'source_id': e.get('source_id'),
        'asset_file': e.get('asset_file'),
        'score': e.get('score'),
        'score_semantics': e.get('score_semantics'),
        'mapping_status': e.get('mapping_status'),
        'reactant_smiles': e.get('reactant_smiles'),
        'reactant_identity': e.get('reactant_identity'),
        'deduped': (e.get('source_record') or {}).get('deduped_from_merged_pool'),
        'engine_edge': {k: ee.get(k) for k in (
            'layer', 'source', 'v34_regime', 'p_uspto', 'p_envipath',
            'p_retrieval', 'tanimoto', 'edge_score', 'score_semantics')},
        'donors': donors,
        'products': products,
    }


def main():
    stats = {}
    for tag, b in BATCHES:
        root = os.path.join(BASE, b)
        batch = {}
        for qdir in sorted(glob.glob(os.path.join(root, 'runs', '*'))):
            qid = qid_of(os.path.basename(qdir))
            q = {'tasks': [], 'cardvals': {}}
            for rf in sorted(glob.glob(os.path.join(qdir, 'results', '*', 'retrieval.json'))):
                try:
                    doc = json.load(open(rf))
                except Exception:
                    continue
                pl = doc.get('payload', {}) or {}
                q['tasks'].append({
                    'task_id': doc.get('task_id'),
                    'substrate_smiles': (pl.get('query') or {}).get('substrate_smiles'),
                    'substrate_identity': (pl.get('query') or {}).get('substrate_identity'),
                    'engine_meta': pl.get('engine_meta'),
                    'evidences': [compact_evidence(e) for e in (pl.get('evidences') or [])],
                })
            for cf in sorted(glob.glob(os.path.join(qdir, 'results', '*', 'cardval.*.json'))):
                try:
                    doc = json.load(open(cf))
                except Exception:
                    continue
                pl = doc.get('payload', {}) or {}
                verdicts = [{
                    'position': v.get('position'),
                    'product_identity': v.get('product_identity'),
                    'product_smiles': v.get('product_smiles'),
                    'accepted': v.get('accepted'),
                    'identity_match': v.get('identity_match'),
                } for v in (pl.get('verdicts') or [])]
                ev = pl.get('evidence_id')
                q['cardvals'][ev] = {
                    'task_id': doc.get('task_id'),
                    'retrieval_rank': pl.get('retrieval_rank'),
                    'kind': pl.get('kind'),
                    'source_file': pl.get('source_file'),
                    'entry_layer': pl.get('entry_layer'),
                    'card_eligible': pl.get('card_eligible'),
                    'n_accepted': pl.get('n_accepted'),
                    'n_total': pl.get('n_total'),
                    'verdicts': verdicts,
                }
            batch[qid] = q
        fn = os.path.join(OUT, f'gate1_{tag}.json')
        with open(fn, 'w', encoding='utf-8') as f:
            json.dump(batch, f, ensure_ascii=False)
        n_ev = sum(len(t['evidences']) for q in batch.values() for t in q['tasks'])
        n_cv = sum(len(q['cardvals']) for q in batch.values())
        stats[tag] = {'questions': len(batch), 'evidences': n_ev, 'cardvals': n_cv,
                      'bytes': os.path.getsize(fn)}
        sys.stderr.write(f"done {tag}: {stats[tag]}\n")
    with open(os.path.join(OUT, 'extract_stats.json'), 'w') as f:
        json.dump(stats, f)
    tarpath = '/tmp/gate1_dump.tar.gz'
    with tarfile.open(tarpath, 'w:gz') as tf:
        for fn in sorted(os.listdir(OUT)):
            tf.add(os.path.join(OUT, fn), arcname=fn)
    raw = open(tarpath, 'rb').read()
    b64 = base64.b64encode(raw).decode('ascii')
    sys.stderr.write(f"tar.gz bytes={len(raw)} b64={len(b64)}\n")
    print('===BEGIN_B64===')
    for i in range(0, len(b64), 4000):
        print(b64[i:i + 4000])
    print('===END_B64===')


main()
