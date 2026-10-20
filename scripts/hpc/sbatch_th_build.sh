#!/usr/bin/env bash
# T-H 修复批 build 作业(单臂;零模型零网络)。
# 部署树 ~/EnzymeAgent/v43cTH(HEAD d4cc871 后含 T-H 部署轮修复);
# PY=venv_v44run(rdkit 2026.03.5,与 chain13/14 基线同引擎)。
# 批=T-H 单臂(预注册 hit@1 35-40%/<32% 回查;任务书 docs/T_H_LAUNCH_TASK_2026-10-20.md)。
#SBATCH --job-name=th-build
#SBATCH --partition=wzhcnormal
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --mem=16G
#SBATCH --output=th_build_%j.out

set -euo pipefail

WS="${WS:-/work/home/aclhl3hbth/ppv1_hpc}"
CODE="${CODE:-$HOME/EnzymeAgent/v43cTH}"
BATCH_ROOT="${BATCH_ROOT:-$WS/batch/t_h_s5b_298_20261020r2}"
BATCH_TAG="${BATCH_TAG:-t-h-s5b-298-20261020r2}"
QUESTIONS="${QUESTIONS:-$WS/questions.jsonl}"
PY="${PY:-$WS/venv_v44run/bin/python}"

fail() { echo "TH-BUILD-FAIL: $*" >&2; exit 1; }

[ -f "$QUESTIONS" ] || fail "缺题卷"
[ -d "$CODE/src" ] || fail "缺代码根"

ulimit -n 4096 2>/dev/null || true
export PYTHONPATH="$CODE/src"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
cd "$CODE"
"$PY" -B scripts/hpc/th_operations.py prebuild --batch-root "$BATCH_ROOT" \
  || fail "新批根非空或旧批/封存批，拒绝覆盖 build"

echo "== T-H build @ $(date -u +%FT%TZ) node=$(hostname) =="
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
echo "TH-BUILD-PASS (batch_root=$BATCH_ROOT)"
