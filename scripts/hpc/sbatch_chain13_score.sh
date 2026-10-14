#!/usr/bin/env bash
# chain13 判分作业(双口径:v1 敏感性+v2 headline[生效后首个新批];
# 零 LLM;全 qid 终态门)。
#SBATCH --job-name=chain13-score
#SBATCH --partition=wzhcnormal
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --mem=8G
#SBATCH --output=chain13_score_%j.out

set -euo pipefail

WS="${WS:-/work/home/aclhl3hbth/ppv1_hpc}"
CODE="${CODE:-$HOME/EnzymeAgent/v43c13}"
BATCH_ROOT="${BATCH_ROOT:-$WS/batch/chain13_s5b_20261014}"
RUNS_ROOT="${RUNS_ROOT:-$WS/runs/chain13_s5b_20261014}"
PY="${PY:-$WS/venv_v44run/bin/python}"

fail() { echo "CHAIN13-SCORE-FAIL: $*" >&2; exit 1; }

[ -f "$BATCH_ROOT/batch_manifest.json" ] || fail "批根未构建"

export PYTHONPATH="$CODE/src"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
cd "$CODE"

# ---- 全 qid 终态门 ----
"$PY" -B scripts/hpc/chain13_gate.py score-gate \
  --batch-root "$BATCH_ROOT" \
  || fail "全批未终态"

# ---- v1 口径(敏感性;产物改名 .v1)----
echo "== chain13 score v1(sensitivity) @ $(date -u +%FT%TZ) =="
"$PY" -B -m pathway_v43.pollutant.s5b_cli score \
  --batch-root "$BATCH_ROOT" \
  --runs-root "$RUNS_ROOT" \
  --data-scope real \
  || fail "v1 判分失败"
for f in metrics.json report.md report_plain.md; do
  [ -f "$BATCH_ROOT/$f" ] && mv "$BATCH_ROOT/$f" "$BATCH_ROOT/$f.v1"
done

# ---- v2 口径(headline)----
echo "== chain13 score v2(headline) @ $(date -u +%FT%TZ) =="
"$PY" -B scripts/hpc/chain13_score_v2.py \
  "$BATCH_ROOT" "$RUNS_ROOT" \
  || fail "v2 判分失败"

echo "CHAIN13-SCORE-PASS"
