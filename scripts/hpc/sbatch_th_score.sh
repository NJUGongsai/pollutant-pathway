#!/usr/bin/env bash
# T-H 判分作业(单臂;v1 敏感性+v3 档 A 披露+v2 headline;零 LLM;
# 全 qid 终态门)。判分侧零改动,沿 chain13_score_v2 语义。
#SBATCH --job-name=th-score
#SBATCH --partition=wzhcnormal
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --mem=8G
#SBATCH --output=th_score_%j.out

set -euo pipefail

WS="${WS:-/work/home/aclhl3hbth/ppv1_hpc}"
CODE="${CODE:-$HOME/EnzymeAgent/v43cTH}"
BATCH_ROOT="${BATCH_ROOT:-$WS/batch/t_h_s5b_298_20261020r2}"
RUNS_ROOT="${RUNS_ROOT:-$WS/runs/t_h_s5b_298_20261020r2}"
PY="${PY:-$WS/venv_v44run/bin/python}"

fail() { echo "TH-SCORE-FAIL: $*" >&2; exit 1; }

[ -f "$BATCH_ROOT/batch_manifest.json" ] || fail "批根未构建"

export PYTHONPATH="$CODE/src"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
cd "$CODE"

# ---- 全 qid 终态门 ----
"$PY" -B scripts/hpc/chain13_gate.py score-gate \
  --batch-root "$BATCH_ROOT" \
  || fail "全批未终态"

# v1→保存 .v1；v3→保存 .v3；v2→保存 .v2 并保留根 headline。
# API 固定写三文件；全部在最终封存前完成，不重写旧批。
"$PY" -B scripts/hpc/th_operations.py score \
  --batch-root "$BATCH_ROOT" --runs-root "$RUNS_ROOT" \
  || fail "三版判分/披露/稳定科学字段对账失败"

echo "TH-SCORE-PASS"
