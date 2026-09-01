#!/bin/bash
#SBATCH -J rempnn_v3_train_A
#SBATCH -p wzhcnormal
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --time=04:00:00
cd /work/home/aclhl3hbth/rxn6
source /work/home/aclhl3hbth/anaconda3/etc/profile.d/conda.sh 2>/dev/null
conda activate rxn
echo "rempnn_v3_train_A start Tue Sep  1 10:42:48 CST 2026"
python gnn_phase6_rempnn.py --preds train_preds_v3.jsonl --train train.txt --shards 'v3loop/shards_train_v3_A/shard_*.json' > v3loop/logs/rempnn_train_A.log 2>&1
echo "rempnn_v3_train_A end Tue Sep  1 10:42:48 CST 2026"
tail -2 v3loop/logs/rempnn_train_A.log
