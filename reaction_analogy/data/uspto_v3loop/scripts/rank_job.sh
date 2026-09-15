#!/bin/bash
#SBATCH -p wzhcnormal
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=64G
#SBATCH --time=12:00:00
cd /work/home/aclhl3hbth/rxn6
source /work/home/aclhl3hbth/anaconda3/etc/profile.d/conda.sh 2>/dev/null
conda activate rxn
export OMP_NUM_THREADS=64
SCRIPT=$1; TRAIN=$2; TEST=$3; OUT=$4; shift 4
echo "rank job start $(date): $SCRIPT train=$TRAIN test=$TEST out=$OUT extra=$@"
python $SCRIPT --train-cands "$TRAIN" --test-cands "$TEST" --procs 64 --out "$OUT" $@ 2>&1 | tee "${OUT%.json}.log" | tail -20
echo "rank job end $(date)"
