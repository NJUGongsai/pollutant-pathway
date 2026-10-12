#!/usr/bin/env bash
# PPV1 298 HPC score 作业:全分片终态后单次判分(零 LLM;金标只在
# 判分进程进入;依赖 ①② 完成后由 sbatch --dependency 串接保证)。
#
# 提交(全部分片终态后;乌镇 wuzh02.hpccube.com;分区名以乌镇
# sinfo -a 实测为准,可 sbatch --partition= 覆盖):
#   BUILD_ID=$(sbatch --parsable scripts/hpc/sbatch_hpc_298_build.sh)
#   SHARD_ID=$(sbatch --parsable --dependency=afterok:$BUILD_ID \
#     --array=1-5 scripts/hpc/sbatch_hpc_298_shard.sh)
#   sbatch --dependency=afterok:$SHARD_ID scripts/hpc/sbatch_hpc_298_score.sh
#   (数组作业 ID 的 afterok = 等全部数组元素成功)
# 产物:$WS/batch/s5b_298_hpc/metrics.json + report*.md(数字带 298
# 题域标签;判分口径/金标只读,本作业零改动)。

#SBATCH --job-name=ppv1-score
#SBATCH --partition=hx1hdnormal
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=ppv1_score_%j.out

set -euo pipefail

WS="${WS:-$HOME/ppv1_hpc}"
CODE="$WS/dependingv43"
BATCH_ROOT="${BATCH_ROOT:-$WS/batch/s5b_298_hpc}"
RUNS_ROOT="${RUNS_ROOT:-$WS/runs/s5b_298_hpc}"
DATA_SCOPE="${DATA_SCOPE:-real}"

if [ -n "${PY:-}" ]; then
  :
elif [ -x /usr/local/python3.12/bin/python3 ]; then
  PY=/usr/local/python3.12/bin/python3
else
  PY="$(command -v python3)"
fi

fail() { echo "SCORE-FAIL: $*" >&2; exit 1; }

[ -f "$BATCH_ROOT/batch_manifest.json" ] \
  || fail "批根未构建:$BATCH_ROOT"

ulimit -n 4096 2>/dev/null || true
export OMP_NUM_THREADS=1
export PYTHONPATH="$CODE/src"
export PYTHONDONTWRITEBYTECODE=1

# ---- 发车前自检:冻结注册序全 qid 终态(依赖串接之外的第二道门;
# 有 pending/缺 case ⇒ 拒发判分,不把未跑完的题当未命中) ----
"$PY" - "$BATCH_ROOT" <<'PYEOF' || fail "全批未终态(先让分片跑完/重投断点续跑)"
import json
import sys
from pathlib import Path

batch_root = Path(sys.argv[1])
manifest = json.loads(
    (batch_root / "batch_manifest.json").read_text(encoding="utf-8"))
order = [str(q) for q in manifest.get("registration_order") or []]
pending, invalid = [], []
for qid in order:
    path = batch_root / "cases" / f"{qid}.json"
    if not path.is_file():
        pending.append(qid)
        continue
    try:
        case = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        invalid.append(qid)
        continue
    if str(case.get("status") or "") not in ("completed", "failed"):
        pending.append(qid)
if pending or invalid:
    print(f"pending={len(pending)} head={pending[:5]} "
          f"invalid={len(invalid)} head={invalid[:5]}")
    sys.exit(1)
n_failed = sum(
    1 for qid in order
    if str((json.loads(
        (batch_root / "cases" / f"{qid}.json").read_text(
            encoding="utf-8")) or {}).get("status")) == "failed")
print(f"SCORE-GATE-OK: n_terminal={len(order)} n_failed={n_failed} "
      "(失败题留分母)")
PYEOF

echo "== score @ $(date -u +%FT%TZ) node=$(hostname) data_scope=$DATA_SCOPE =="
"$PY" -B -m pathway_v43.pollutant.s5b_cli score \
  --batch-root "$BATCH_ROOT" \
  --runs-root "$RUNS_ROOT" \
  --data-scope "$DATA_SCOPE" \
  || fail "s5b_cli score 失败(看上方结构化输出)"

echo "SCORE-PASS"
