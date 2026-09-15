#!/bin/bash
#SBATCH -J v3loop_verify
#SBATCH -p wzhcnormal
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --time=02:00:00
cd /work/home/aclhl3hbth/rxn6/v3loop
source /work/home/aclhl3hbth/anaconda3/etc/profile.d/conda.sh 2>/dev/null
conda activate rxn
echo '=== 1. A/B byte-diff (determinism) ==='
python3 - << 'PYEOF'
import glob, hashlib, os
def fhash(p, n=64*1024):
    h = hashlib.md5()
    with open(p, 'rb') as fh:
        while True:
            b = fh.read(n)
            if not b: break
            h.update(b)
    return h.hexdigest()
for split in ['train', 'test']:
    A = sorted(glob.glob(f'shards_{split}_v3_A/shard_*.json'))
    B = sorted(glob.glob(f'shards_{split}_v3_B/shard_*.json'))
    assert len(A) == len(B), (split, len(A), len(B))
    ndiff = 0; diffs = []
    for a, b in zip(A, B):
        sa, sb = os.path.getsize(a), os.path.getsize(b)
        if sa != sb or fhash(a) != fhash(b):
            ndiff += 1
            if len(diffs) < 5: diffs.append((os.path.basename(a), sa, sb))
    print(f'{split}: {len(A)} shards A/B byte-diff mismatch={ndiff} {diffs}')
PYEOF
echo '=== 2. v3 vs v1 mpnn spot-check (5 shards, distribution shift) ==='
python3 - << 'PYEOF'
import json
def stats(path):
    d = json.load(open(path))
    vals = [c['mpnn'] for case in d['dump'] for c in case['cands']]
    pos = [c['mpnn'] for case in d['dump'] for c in case['cands'] if c['l'] == 1]
    import statistics as st
    if vals:
        sv = sorted(vals)
        med = sv[len(sv)//2]
    else:
        med = 0
    return (len(vals), sum(1 for v in vals if v > 0)/max(1,len(vals)),
            sum(vals)/max(1,len(vals)), med,
            sum(pos)/max(1,len(pos)), sum(1 for v in pos if v >= 0.9)/max(1,len(pos)))
for f in ['shard_0.json', 'shard_1.json', 'shard_500.json']:
    o = stats(f'/work/home/aclhl3hbth/rxn6/shards_train3/{f}')
    n = stats(f'/work/home/aclhl3hbth/rxn6/v3loop/shards_train_v3_A/{f}')
    print(f'TRAIN {f}:')
    print(f'  v1: n={o[0]} mpnn>0={o[1]:.3f} mean={o[2]:.4f} med={o[3]:.4f} posmean={o[4]:.4f} pos>=0.9={o[5]:.3f}')
    print(f'  v3: n={n[0]} mpnn>0={n[1]:.3f} mean={n[2]:.4f} med={n[3]:.4f} posmean={n[4]:.4f} pos>=0.9={n[5]:.3f}')
for f in ['shard_0.json', 'shard_100.json']:
    o = stats(f'/work/home/aclhl3hbth/rxn6/shards_test3/{f}')
    n = stats(f'/work/home/aclhl3hbth/rxn6/v3loop/shards_test_v3_A/{f}')
    print(f'TEST {f}:')
    print(f'  v1: n={o[0]} mpnn>0={o[1]:.3f} mean={o[2]:.4f} med={o[3]:.4f} posmean={o[4]:.4f} pos>=0.9={o[5]:.3f}')
    print(f'  v3: n={n[0]} mpnn>0={n[1]:.3f} mean={n[2]:.4f} med={n[3]:.4f} posmean={n[4]:.4f} pos>=0.9={n[5]:.3f}')
PYEOF
echo '=== VERIFY DONE ==='
