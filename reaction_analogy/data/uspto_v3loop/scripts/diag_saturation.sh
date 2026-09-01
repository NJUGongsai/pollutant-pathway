#!/bin/bash
#SBATCH -J v3diag_sat
#SBATCH -p wzhcnormal
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --time=04:00:00
cd /work/home/aclhl3hbth/rxn6/v3loop
source /work/home/aclhl3hbth/anaconda3/etc/profile.d/conda.sh 2>/dev/null
conda activate rxn
python3 << 'PYEOF'
import glob, json
import numpy as np

# ---- full test-set ranker-visible feature stats: v1 vs v3 ----
def shard_stats(paths):
    P = []; L = []  # mpnn values, labels
    argmax_hits = 0; n_case = 0
    sep = []  # per-case: mpnn(true) - max mpnn(neg)
    for p in paths:
        d = json.load(open(p))
        for case in d['dump']:
            cands = case['cands']
            if not cands: continue
            n_case += 1
            vals = [c['mpnn'] for c in cands]
            labs = [c['l'] for c in cands]
            P.extend(vals); L.extend(labs)
            # mpnn-argmax top-1 (pure feature ranking)
            bi = int(np.argmax(vals))
            if labs[bi] == 1: argmax_hits += 1
            # separability
            tv = [v for v, l in zip(vals, labs) if l == 1]
            nv = [v for v, l in zip(vals, labs) if l == 0]
            if tv and nv: sep.append(min(tv) - max(nv))
    P = np.array(P); L = np.array(L, dtype=bool)
    pos = P[L]; neg = P[~L]
    return dict(n_cand=len(P), n_case=n_case,
        pos_mean=float(pos.mean()), pos_ge90=float((pos>=0.9).mean()), pos_ge99=float((pos>=0.99).mean()),
        neg_mean=float(neg.mean()), neg_median=float(np.median(neg)), neg_ge90=float((neg>=0.9).mean()),
        mpnn_argmax_top1=argmax_hits/n_case,
        sep_mean=float(np.mean(sep)), sep_pos=float(np.mean([s for s in sep if s>0])) if any(s>0 for s in sep) else 0.0,
        sep_frac_pos=float(np.mean([s>0 for s in sep])))

tv1 = shard_stats(sorted(glob.glob('/work/home/aclhl3hbth/rxn6/shards_test3/shard_*.json')))
tv3 = shard_stats(sorted(glob.glob('/work/home/aclhl3hbth/rxn6/v3loop/shards_test_v3_A/shard_*.json')))
out = {'test_v1': tv1, 'test_v3': tv3}
json.dump(out, open('/work/home/aclhl3hbth/rxn6/v3loop/results/diag_saturation_test.json','w'), indent=2)
print(json.dumps(out, indent=2))
PYEOF
