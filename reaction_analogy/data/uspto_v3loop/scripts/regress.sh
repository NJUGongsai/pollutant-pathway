#!/bin/bash
#SBATCH -J rempnn_regress
#SBATCH -p wzhcnormal
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --time=02:00:00
cd ~/rxn6/v3loop/regress
source /work/home/aclhl3hbth/anaconda3/etc/profile.d/conda.sh 2>/dev/null
conda activate rxn
echo '=== A. TRAIN shards x3 recompute with v1 preds (index=train.txt) ==='
python ~/rxn6/gnn_phase6_rempnn.py --preds ~/rxn6/train_preds.jsonl --train ~/rxn6/train.txt --shards 'train/shard_*.json' 2>&1 | tail -5
echo '=== B. TEST shards x2 recompute with v1 preds (index=test.txt.proc) ==='
python ~/rxn6/gnn_phase6_rempnn.py --preds ~/rxn6/test_preds.jsonl --train ~/rxn6/test.txt.proc --shards 'test/shard_*.json' 2>&1 | tail -5
echo '=== C. compare vs originals ==='
python compare.py ~/rxn6/shards_train3 train 'shard_0.json,shard_1.json,shard_500.json'
python compare.py ~/rxn6/shards_test3 test 'shard_0.json,shard_100.json'
echo '=== REGRESS DONE ==='
