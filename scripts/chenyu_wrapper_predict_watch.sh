#!/usr/bin/env bash
# 后台轮询晨羽 wrapper.predict 进度（本地跑，写到 reports/probe/）
set -euo pipefail

SSH_HOST="30c1b91fe059488f946c1b15bda3560c71.gz15.chenyu.cn"
SSH_PORT="20234"
SSH_USER="root"
OUT="/home/axlhuang/projects/enzymecage_crew/reports/probe/wrapper_predict_progress.log"
mkdir -p "$(dirname "$OUT")"

if [ -z "${SSHPASS:-}" ]; then
  echo "[ERR] 需要 SSHPASS" >&2; exit 1
fi

SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=10 -p "${SSH_PORT}")

echo "[$(date -u +%FT%TZ)] 开始轮询" > "$OUT"
for i in $(seq 1 120); do  # 最多 120 × 60s = 2 小时
  TS="$(date -u +%FT%TZ)"
  STATUS=$(timeout 25 sshpass -e ssh "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" '
    PY_PID=$(ps -eo pid,comm,args | awk "\$2==\"python\" && /base64/ {print \$1; exit}")
    if [ -z "$PY_PID" ]; then
      echo "PY_PID=NONE"
      echo "---LOG_TAIL---"
      tail -5 /tmp/chenyu_wrapper_predict_smoke.log 2>&1
    else
      RSS=$(grep VmRSS /proc/$PY_PID/status | awk "{print \$2}")
      STAT=$(ps -o stat= -p $PY_PID)
      WCHAN=$(ps -o wchan= -p $PY_PID)
      ETIME=$(ps -o etime= -p $PY_PID)
      GPU_MEM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
      GPU_UTIL=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits)
      echo "PY_PID=$PY_PID etime=$ETIME stat=$STAT wchan=$WCHAN rss_kb=$RSS gpu_mem_mib=$GPU_MEM gpu_util_pct=$GPU_UTIL"
      echo "---LOG_TAIL---"
      tail -3 /tmp/chenyu_wrapper_predict_smoke.log 2>&1
    fi
  ' 2>&1)
  echo "[$TS] round=$i" >> "$OUT"
  echo "$STATUS" >> "$OUT"
  echo "---" >> "$OUT"
  # 结束条件
  if echo "$STATUS" | grep -qE "\[SMOKE\] LAYER-2 DONE|\[STAGE-C\] predict OK|\[STAGE-C\] predict FAILED|PY_PID=NONE"; then
    echo "[$TS] STOP: 触发结束条件" >> "$OUT"
    break
  fi
  sleep 60
done
echo "[$(date -u +%FT%TZ)] 轮询结束" >> "$OUT"
