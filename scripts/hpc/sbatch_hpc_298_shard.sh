#!/usr/bin/env bash
# PPV1 298 HPC 分片跑题作业(多作业分片:同一批根上各分片持不相交
# qid 白名单并发;批级闸门 RPM/TPM/max_calls/在途/金额帽经
# FileRateGate 跨进程共享;断点续跑天然支持——失败重启=重投本脚本
# 同参数,已完成 qid SKIP)。
#
# 分片协议(s5b-orchestrator-3 白名单域锁):
#   - 建议以作业数组一次提交全部分片:sbatch --array=1-5 本脚本
#     (SHARD_INDEX/SHARD_TOTAL 自动取 SLURM_ARRAY_TASK_ID/COUNT);
#   - **所有分片必须同参发车**(workers/gate 参数进 orchestration.json
#     冻结副本;不同参后到者被 s5b_orchestration_conflict 结构化拒);
#   - 首批建议全部分片约束同一节点(重投时统一加 --nodelist=<节点>):
#     跨节点时死亡占位回收按本机 pid 判死会误回收他节点在途 worker
#     (在途帽放松、金额侧保守不漏),且 flock 跨节点语义未实测;
#   - 每分片缺省 20 workers(按 128 核节点定;分片数×(workers+4)
#     ≤ 单节点核数)。
#
# 前置:build 作业完成;approve/budget/price 三步已做(real 批
# budget_guard.json 是发车硬门,缺席直接拒)。
# 依赖串接示例(deploy.md §9):
#   BUILD_ID=$(sbatch --parsable scripts/hpc/sbatch_hpc_298_build.sh)
#   sbatch --dependency=afterok:$BUILD_ID --array=1-5 \
#     scripts/hpc/sbatch_hpc_298_shard.sh
# 提交(乌镇 wuzh02.hpccube.com;分区名以乌镇 sinfo -a 实测为准):

#SBATCH --job-name=ppv1-shard
#SBATCH --partition=hx1hdnormal
#SBATCH --cpus-per-task=24
#SBATCH --time=24:00:00
#SBATCH --output=ppv1_shard_%A_%a.out

set -euo pipefail

WS="${WS:-$HOME/ppv1_hpc}"
CODE="$WS/dependingv43"
BATCH_ROOT="${BATCH_ROOT:-$WS/batch/s5b_298_hpc}"
RUNS_ROOT="${RUNS_ROOT:-$WS/runs/s5b_298_hpc}"
ENV_FILE="${ENV_FILE:-$WS/env/llm.env}"
WORKERS="${WORKERS:-20}"
GATE_MAX_CALLS="${GATE_MAX_CALLS:-1490}"
# 数组作业自动分片;非数组提交 = 单分片全量(SHARD_INDEX=SHARD_TOTAL=1)
SHARD_TOTAL="${SHARD_TOTAL:-${SLURM_ARRAY_TASK_COUNT:-1}}"
SHARD_INDEX="${SHARD_INDEX:-${SLURM_ARRAY_TASK_ID:-1}}"

if [ -n "${PY:-}" ]; then
  :
elif [ -x /usr/local/python3.12/bin/python3 ]; then
  PY=/usr/local/python3.12/bin/python3
else
  PY="$(command -v python3)"
fi

fail() { echo "SHARD-FAIL(shard ${SHARD_INDEX}/${SHARD_TOTAL}): $*" >&2; exit 1; }

case "$SHARD_INDEX" in
  ''|*[!0-9]*) fail "SHARD_INDEX 非法:$SHARD_INDEX(1 起)";;
esac
[ "$SHARD_TOTAL" -ge 1 ] || fail "SHARD_TOTAL 非法:$SHARD_TOTAL"
[ "$SHARD_INDEX" -ge 1 ] && [ "$SHARD_INDEX" -le "$SHARD_TOTAL" ] \
  || fail "SHARD_INDEX 须 1..SHARD_TOTAL(当前 $SHARD_INDEX/$SHARD_TOTAL)"

[ -f "$BATCH_ROOT/batch_manifest.json" ] \
  || fail "批根未构建:$BATCH_ROOT(先跑 build 作业)"
[ -f "$ENV_FILE" ] || fail "缺凭证 env 文件:$ENV_FILE(按 deploy.md §5 放置;值不入仓)"
[ -f "$BATCH_ROOT/budget_guard.json" ] \
  || fail "real 批缺金额守卫 $BATCH_ROOT/budget_guard.json(先 s5b_cli budget;60 CNY 帽不自动升)"

# qid 域锁 fd 余量(每 qid 一把锁;含尾分片的余量题)
ulimit -n 4096 2>/dev/null || true
export OMP_NUM_THREADS=1
export PYTHONPATH="$CODE/src"
export PYTHONDONTWRITEBYTECODE=1

# ---- 按冻结注册序切白名单(连续切片;尾分片吃余量) ----
QIDS="$("$PY" - "$BATCH_ROOT/batch_manifest.json" \
  "$SHARD_INDEX" "$SHARD_TOTAL" <<'PYEOF'
import json
import sys

manifest = json.loads(open(sys.argv[1], encoding="utf-8").read())
order = [str(q) for q in manifest.get("registration_order") or []]
index, total = int(sys.argv[2]), int(sys.argv[3])
assert 1 <= index <= total, (index, total)
per = (len(order) + total - 1) // total
lo = (index - 1) * per
hi = min(index * per, len(order))
shard = order[lo:hi]
assert shard, f"空分片({index}/{total};per={per},len={len(order)})"
print(",".join(shard))
PYEOF
)" || fail "白名单切分失败"

echo "== shard ${SHARD_INDEX}/${SHARD_TOTAL} @ $(date -u +%FT%TZ) node=$(hostname) =="
echo "workers=$WORKERS gate_max_calls=$GATE_MAX_CALLS n_qids=$(echo "$QIDS" | tr ',' '\n' | wc -l | tr -d ' ')"

"$PY" -B -m pathway_v43.pollutant.s5b_cli run \
  --batch-root "$BATCH_ROOT" \
  --runs-root "$RUNS_ROOT" \
  --qids "$QIDS" \
  --workers "$WORKERS" \
  --gate-max-calls "$GATE_MAX_CALLS" \
  --python-bin "$PY" \
  --env-file "$ENV_FILE" \
  || fail "s5b_cli run 失败(看上方结构化输出;断点续跑=重投同参)"

echo "SHARD-PASS(shard ${SHARD_INDEX}/${SHARD_TOTAL})"
