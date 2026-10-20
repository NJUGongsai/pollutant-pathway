#!/usr/bin/env bash
# T-H 修复批跑题作业(单臂;冒烟 2→10→全量;断点续跑=同参重投)。
# - 证据卡关卡级关闭(映射在 th_run_wrapper.py 单一写死;
#   发车参数冻结进批根 orchestration.json);
# - 每题≤3 真实调用经 profile_policy 覆盖(沿 chain13/14 同一
#   CHAIN13_PROFILE);no-cap(CC 2026-10-20 发车指令;usage 照记);
# - transport 失败自动重试(real_model 内装载)。
#SBATCH --job-name=th-run
#SBATCH --partition=wzhcnormal
#SBATCH --cpus-per-task=12
#SBATCH --time=24:00:00
#SBATCH --mem=32G
#SBATCH --output=th_run_%j.out

set -euo pipefail

WS="${WS:-/work/home/aclhl3hbth/ppv1_hpc}"
CODE="${CODE:-$HOME/EnzymeAgent/v43cTH}"
BATCH_ROOT="${BATCH_ROOT:-$WS/batch/t_h_s5b_298_20261020r2}"
RUNS_ROOT="${RUNS_ROOT:-$WS/runs/t_h_s5b_298_20261020r2}"
ENV_FILE="${ENV_FILE:-$WS/env/llm.env}"
PY="${PY:-$WS/venv_v44run/bin/python}"

fail() { echo "TH-RUN-FAIL: $*" >&2; exit 1; }

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
"$PY" -B scripts/hpc/th_operations.py check-mutable --batch-root "$BATCH_ROOT" \
  || fail "旧批/封存批不得发车"

run_phase() {
  local label="$1"
  local wrapper_status=0
  shift
  echo "== T-H run [$label] @ $(date -u +%FT%TZ) node=$(hostname) =="
  if [ "$#" -gt 0 ]; then
    "$PY" -B scripts/hpc/th_run_wrapper.py \
      --batch-root "$BATCH_ROOT" --runs-root "$RUNS_ROOT" \
      --env-file "$ENV_FILE" "$@" \
      || wrapper_status=$?
  else
    "$PY" -B scripts/hpc/th_run_wrapper.py \
      --batch-root "$BATCH_ROOT" --runs-root "$RUNS_ROOT" \
      --env-file "$ENV_FILE" \
      || wrapper_status=$?
  fi
  "$PY" -B scripts/hpc/th_operations.py phase \
    --batch-root "$BATCH_ROOT" --runs-root "$RUNS_ROOT" \
    --env-file "$ENV_FILE" --label "$label" --wrapper-status "$wrapper_status" \
    || fail "T-H 零 CX/失败留证恢复门不过($label)"
  "$PY" -B scripts/hpc/chain13_gate.py run-gate \
    --batch-root "$BATCH_ROOT" --label "$label" \
    || fail "终态门不过($label)"
}

run_phase smoke2 --limit 2
run_phase smoke10 --limit 10
run_phase full

echo "TH-RUN-PASS"
