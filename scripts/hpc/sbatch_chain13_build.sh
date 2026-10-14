#!/usr/bin/env bash
# chain13 build 作业(v43@HEAD,policy-7 共底物伴生供给;零模型零网络)。
# 部署树 ~/EnzymeAgent/v43c13;PY=venv_v44run(rdkit 2026.03.5+lightgbm)。
#SBATCH --job-name=chain13-build
#SBATCH --partition=wzhcnormal
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --mem=16G
#SBATCH --output=chain13_build_%j.out

set -euo pipefail

WS="${WS:-/work/home/aclhl3hbth/ppv1_hpc}"
CODE="${CODE:-$HOME/EnzymeAgent/v43c13}"
BATCH_ROOT="${BATCH_ROOT:-$WS/batch/chain13_s5b_20261014}"
BATCH_TAG="${BATCH_TAG:-chain13}"
QUESTIONS="${QUESTIONS:-$WS/questions.jsonl}"
PY="${PY:-$WS/venv_v44run/bin/python}"

fail() { echo "CHAIN13-BUILD-FAIL: $*" >&2; exit 1; }

[ -f "$QUESTIONS" ] || fail "缺题卷"
[ -d "$CODE/src" ] || fail "缺代码根"

ulimit -n 4096 2>/dev/null || true
export PYTHONPATH="$CODE/src"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
cd "$CODE"

echo "== chain13 build @ $(date -u +%FT%TZ) node=$(hostname) =="
"$PY" -B -m pathway_v43.pollutant.s5b_cli build \
  --questions "$QUESTIONS" \
  --batch-root "$BATCH_ROOT" \
  --batch-tag "$BATCH_TAG" \
  --provider-kind real \
  --pool-mode template \
  --recorded-source \
  --max-pool 8 \
  --pool-threshold 0.45 \
  --v3-code-root "$HOME/EnzymeAgent/dependingv3" \
  --assets-root "$CODE/assets" \
  || fail "s5b_cli build 失败"

"$PY" -B scripts/hpc/chain13_gate.py build-gate \
  --batch-root "$BATCH_ROOT" \
  || fail "build 产物自检不过"
echo "CHAIN13-BUILD-PASS"
