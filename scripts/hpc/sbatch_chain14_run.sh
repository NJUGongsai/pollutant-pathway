#!/usr/bin/env bash
# chain14 跑题作业(A/B 双臂;ARM=a|b 环境变量前置;冒烟 2→10→全量)。
# - A 臂 evidence_card_enabled=false / B 臂 true(映射在 chain14_run_
#   wrapper.py 单一写死;发车参数冻结进批根 orchestration.json);
# - 每题≤3 真实调用经 profile_policy 覆盖(沿 chain13 wrapper 同一
#   CHAIN13_PROFILE);no-cap;同批断点续跑=同参重投;
# - transport 失败自动重试双臂共享(real_model 内装载,非差分变量)。
#SBATCH --job-name=chain14-run
#SBATCH --partition=wzhcnormal
#SBATCH --cpus-per-task=12
#SBATCH --time=24:00:00
#SBATCH --mem=32G
#SBATCH --output=chain14_run_%j.out

set -euo pipefail

WS="${WS:-/work/home/aclhl3hbth/ppv1_hpc}"
CODE="${CODE:-$HOME/EnzymeAgent/v43c14}"
ARM="${ARM:?CHAIN14-RUN-FAIL: 缺 ARM(须 a 或 b;环境变量前置)}"
BATCH_ROOT="${BATCH_ROOT:-$WS/batch/chain14${ARM}_s5b_20261015}"
RUNS_ROOT="${RUNS_ROOT:-$WS/runs/chain14${ARM}_s5b_20261015}"
ENV_FILE="${ENV_FILE:-$WS/env/llm.env}"
PY="${PY:-$WS/venv_v44run/bin/python}"

fail() { echo "CHAIN14-RUN-FAIL: $*" >&2; exit 1; }

case "$ARM" in a|b) ;; *) fail "ARM 非法:$ARM(须 a 或 b)";; esac
[ -f "$BATCH_ROOT/batch_manifest.json" ] || fail "批根未构建"
[ -f "$BATCH_ROOT/preregistration_approval.json" ] || fail "缺批准记录"
[ -f "$BATCH_ROOT/budget_no_cap.json" ] || fail "缺 no-cap 标记"
[ -f "$ENV_FILE" ] || fail "缺凭证 env"

ulimit -n 4096 2>/dev/null || true
export PYTHONPATH="$CODE/src"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
unset S5B_MODEL_STUB_SCRIPT || true
cd "$CODE"

run_phase() {
  local label="$1"
  shift
  echo "== chain14 run [arm=$ARM $label] @ $(date -u +%FT%TZ) node=$(hostname) =="
  if [ "$#" -gt 0 ]; then
    "$PY" -B scripts/hpc/chain14_run_wrapper.py \
      --arm "$ARM" \
      --batch-root "$BATCH_ROOT" --runs-root "$RUNS_ROOT" \
      --env-file "$ENV_FILE" "$@" \
      || fail "wrapper run 失败($label)"
  else
    "$PY" -B scripts/hpc/chain14_run_wrapper.py \
      --arm "$ARM" \
      --batch-root "$BATCH_ROOT" --runs-root "$RUNS_ROOT" \
      --env-file "$ENV_FILE" \
      || fail "wrapper run 失败($label)"
  fi
  "$PY" -B scripts/hpc/chain13_gate.py run-gate \
    --batch-root "$BATCH_ROOT" --label "$label" \
    || fail "终态门不过($label)"
}

run_phase smoke2 --limit 2
run_phase smoke10 --limit 10
run_phase full

echo "CHAIN14-RUN-PASS (arm=$ARM)"
