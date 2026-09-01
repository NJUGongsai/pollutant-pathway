#!/bin/bash
#SBATCH -J rempnn_v3_test_A
#SBATCH -p wzhcnormal
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --time=04:00:00
cd /work/home/aclhl3hbth/rxn6
source /work/home/aclhl3hbth/anaconda3/etc/profile.d/conda.sh 2>/dev/null
conda activate rxn
echo "rempnn_v3_test_A start Tue Sep  1 10:42:48 CST 2026"
python gnn_phase6_rempnn.py --preds test_preds_v3.jsonl --train test.txt.proc --shards 'v3loop/shards_test_v3_A/shard_*.json' > v3loop/logs/rempnn_test_A.log 2>&1
echo "rempnn_v3_test_A end Tue Sep  1 10:42:48 CST 2026"
tail -2 v3loop/logs/rempnn_test_A.log
