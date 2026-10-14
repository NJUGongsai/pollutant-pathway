#!/usr/bin/env bash
# chain13 跑题作业(冒烟 2→10→全量;每题≤3 真实调用经 profile_policy
# 覆盖[max_real_model_requests=3+format_feedback 2];no-cap;同批断点
# 续跑=同参重投)。
#SBATCH --job-name=chain13-run
#SBATCH --partition=wzhcnormal
#SBATCH --cpus-per-task=12
#SBATCH --time=24:00:00
#SBATCH --mem=32G
#SBATCH --output=chain13_run_%j.out

set -euo pipefail

WS="${WS:-/work/home/aclhl3hbth/ppv1_hpc}"
CODE="${CODE:-$HOME/EnzymeAgent/v43c13}"
BATCH_ROOT="${BATCH_ROOT:-$WS/batch/chain13_s5b_20261014}"
RUNS_ROOT="${RUNS_ROOT:-$WS/runs/chain13_s5b_20261014}"
ENV_FILE="${ENV_FILE:-$WS/env/llm.env}"
PY="${PY:-$WS/venv_v44run/bin/python}"

fail() { echo "CHAIN13-RUN-FAIL: $*" >&2; exit 1; }

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
  echo "== chain13 run [$label] @ $(date -u +%FT%TZ) node=$(hostname) =="
  if [ "$#" -gt 0 ]; then
    "$PY" -B scripts/hpc/chain13_run_wrapper.py \
      --batch-root "$BATCH_ROOT" --runs-root "$RUNS_ROOT" \
      --env-file "$ENV_FILE" "$@" \
      || fail "wrapper run 失败($label)"
  else
    "$PY" -B scripts/hpc/chain13_run_wrapper.py \
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

echo "CHAIN13-RUN-PASS"
