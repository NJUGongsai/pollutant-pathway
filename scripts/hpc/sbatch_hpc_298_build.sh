#!/usr/bin/env bash
# PPV1 298 HPC build 作业:题卷 → 参考图/run 输入/清单(语料检索+编译,
# 单 python 进程,CPU 密集;scripted/real 批身份在此冻结)。
#
# 前置:netcheck 作业全过(deploy.md §6);$WS/questions.jsonl 已放置
# (含金标,只放 HPC 工作区,不入仓);依赖 rdkit 已 pip install --user。
#
# 提交(乌镇 wuzh02.hpccube.com;分区名以乌镇 sinfo -a 实测为准,
# 可 sbatch --partition= 覆盖;事实基准=zzeshell 侦察,乌镇同款核验):
#   ssh -i <key> -p 65091 aclhl3hbth@wuzh02.hpccube.com
#   cd ~/ppv1_hpc/dependingv43
#   WS=$HOME/ppv1_hpc sbatch scripts/hpc/sbatch_hpc_298_build.sh
# 产物:$WS/batch/s5b_298_hpc(batch_manifest.json/registration_order 冻结)。
# 之后的 approve/budget/price 三步是用户裁定步骤(deploy.md §8)。

#SBATCH --job-name=ppv1-build
#SBATCH --partition=hx1hdnormal
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --output=ppv1_build_%j.out

set -euo pipefail

WS="${WS:-$HOME/ppv1_hpc}"
CODE="$WS/dependingv43"
BATCH_ROOT="${BATCH_ROOT:-$WS/batch/s5b_298_hpc}"
BATCH_TAG="${BATCH_TAG:-s5b-298}"
QUESTIONS="${QUESTIONS:-$WS/questions.jsonl}"

if [ -n "${PY:-}" ]; then
  :
elif [ -x /usr/local/python3.12/bin/python3 ]; then
  PY=/usr/local/python3.12/bin/python3
else
  PY="$(command -v python3)"
fi

fail() { echo "BUILD-FAIL: $*" >&2; exit 1; }

[ -f "$QUESTIONS" ] || fail "缺题卷 $QUESTIONS(含金标;按 deploy.md §5 放置)"
[ -d "$CODE/src" ] || fail "缺代码根 $CODE/src(按 deploy.md §3 解包)"
"$PY" -c "import rdkit" || fail "rdkit 缺(先 pip3 install --user rdkit)"

# qid 域锁 fd 余量(298 题 + worker 管道;Linux 缺省 1024 够,再放宽)
ulimit -n 4096 2>/dev/null || true
export OMP_NUM_THREADS=1
export PYTHONPATH="$CODE/src"
export PYTHONDONTWRITEBYTECODE=1

echo "== build @ $(date -u +%FT%TZ) node=$(hostname) =="
"$PY" -B -m pathway_v43.pollutant.s5b_cli build \
  --questions "$QUESTIONS" \
  --batch-root "$BATCH_ROOT" \
  --batch-tag "$BATCH_TAG" \
  --pool-mode template \
  || fail "s5b_cli build 失败(看上方结构化输出)"

# 抽验产物在位 + 注册序计数(与题卷行数一致才放行)
"$PY" - "$BATCH_ROOT" "$QUESTIONS" <<'PYEOF' || fail "build 产物自检不过"
import json
import sys
from pathlib import Path

batch_root, questions = Path(sys.argv[1]), Path(sys.argv[2])
manifest = json.loads(
    (batch_root / "batch_manifest.json").read_text(encoding="utf-8"))
n_reg = len(manifest.get("registration_order") or [])
n_q = sum(1 for line in questions.read_text(encoding="utf-8").splitlines()
          if line.strip())
if n_reg != n_q or n_reg == 0:
    print(f"注册序 {n_reg} != 题卷行 {n_q}")
    sys.exit(1)
print(f"BUILD-OK: n_questions={n_reg} "
      f"questions_sha={manifest['questions_source_sha256'][:16]}…")
PYEOF
echo "BUILD-PASS"
