#!/usr/bin/env bash
# chain14 build 作业(v43@b4b89dc+,A/B 双臂同构构建;零模型零网络)。
# 部署树 ~/EnzymeAgent/v43c14;PY=venv_v44run(rdkit 2026.03.5+lightgbm)。
# ARM=a|b(环境变量前置;两臂批根分立、构建参数与题卷完全同构 ——
# 题卷同 sha,单差分变量只在发车开关,见 chain14_run_wrapper.py)。
#SBATCH --job-name=chain14-build
#SBATCH --partition=wzhcnormal
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --mem=16G
#SBATCH --output=chain14_build_%j.out

set -euo pipefail

WS="${WS:-/work/home/aclhl3hbth/ppv1_hpc}"
CODE="${CODE:-$HOME/EnzymeAgent/v43c14}"
ARM="${ARM:?CHAIN14-BUILD-FAIL: 缺 ARM(须 a 或 b;环境变量前置)}"
BATCH_ROOT="${BATCH_ROOT:-$WS/batch/chain14${ARM}_s5b_20261015}"
BATCH_TAG="${BATCH_TAG:-chain14${ARM}}"
QUESTIONS="${QUESTIONS:-$WS/questions.jsonl}"
PY="${PY:-$WS/venv_v44run/bin/python}"

fail() { echo "CHAIN14-BUILD-FAIL: $*" >&2; exit 1; }

case "$ARM" in a|b) ;; *) fail "ARM 非法:$ARM(须 a 或 b)";; esac
[ -f "$QUESTIONS" ] || fail "缺题卷"
[ -d "$CODE/src" ] || fail "缺代码根"

ulimit -n 4096 2>/dev/null || true
export PYTHONPATH="$CODE/src"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
cd "$CODE"

echo "== chain14 build [arm=$ARM] @ $(date -u +%FT%TZ) node=$(hostname) =="
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
echo "CHAIN14-BUILD-PASS (arm=$ARM batch_root=$BATCH_ROOT)"
