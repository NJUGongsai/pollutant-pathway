#!/usr/bin/env bash
# scripts/case2_realrun.sh
# ============================================================
# 晨羽端 Case 2 全链路真跑 (DRY_RUN=0)
# ============================================================
# 结构：nohup launch + 本端轮询
# 预算：mmap ESM ~11min(首次) + predict ~5-60s + 其它 <30s = ~12min 上限
# 归档：晨羽 /root/projects/enzymecage_crew/reports/dryrun/case_2_<ts>/
# ============================================================

set -euo pipefail

if [ -z "${SSHPASS:-}" ]; then
  echo "[ERR] 请先: export SSHPASS='<password>'" >&2
  exit 1
fi

SSH_OPTS=(
  -o ConnectTimeout=10
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=20
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -p 20234
)

HOST="root@30c1b91fe059488f946c1b15bda3560c71.gz15.chenyu.cn"
LOG_REMOTE="/tmp/case2_realrun.log"
PID_REMOTE="/tmp/case2_realrun.pid"
POLL_MAX=30          # 30 × 60s = 30 min
POLL_INTERVAL=60

echo "[LAUNCH] $(date -u +%FT%TZ) 启动 Case 2 全链路真跑"

# ------------- 启动 -------------
LAUNCH_SCRIPT=$(cat <<'REMOTE_EOF'
set -e
source /usrdata/EnzymeCAGE_envs/enzymecage_py312/bin/activate
cd /root/projects/enzymecage_crew
# 清理旧痕
rm -f /tmp/case2_realrun.log /tmp/case2_realrun.pid
# 用 setsid 让 python 脱离 shell 会话
nohup setsid python -u scripts/run/run_case_dryrun.py --case case_2_realrun \
  > /tmp/case2_realrun.log 2>&1 &
echo $! > /tmp/case2_realrun.pid
sleep 1
cat /tmp/case2_realrun.pid
REMOTE_EOF
)

PID=$(sshpass -e ssh "${SSH_OPTS[@]}" "$HOST" "$LAUNCH_SCRIPT" | tail -1 | tr -d '[:space:]')
echo "[LAUNCH] remote PID=${PID}"

# ------------- 轮询 -------------
echo "[POLL] 每 ${POLL_INTERVAL}s 轮询一次，最多 ${POLL_MAX} 轮..."
for i in $(seq 1 ${POLL_MAX}); do
  sleep ${POLL_INTERVAL}
  ELAPSED=$((i * POLL_INTERVAL))
  STATUS=$(timeout 25 sshpass -e ssh "${SSH_OPTS[@]}" "$HOST" "
    if [ -f ${PID_REMOTE} ]; then PID=\$(cat ${PID_REMOTE}); else PID=NONE; fi
    if [ \"\$PID\" != \"NONE\" ] && kill -0 \$PID 2>/dev/null; then
      RSS=\$(awk '/VmRSS/{print \$2}' /proc/\$PID/status 2>/dev/null || echo 0)
      STAT=\$(ps -o stat= -p \$PID 2>/dev/null || echo ?)
      WCHAN=\$(ps -o wchan= -p \$PID 2>/dev/null || echo ?)
      GPU=\$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null || echo ?)
      echo \"ALIVE pid=\$PID stat=\$STAT wchan=\$WCHAN rss_kb=\$RSS gpu_mib=\$GPU\"
    elif [ \"\$PID\" != \"NONE\" ]; then
      RC=\$(wait \$PID 2>/dev/null; echo \$?)
      echo \"EXITED pid=\$PID\"
    else
      echo \"NO_PID_FILE\"
    fi
    echo '---TAIL---'
    tail -8 ${LOG_REMOTE} 2>/dev/null || echo '(no log yet)'
  " 2>&1)
  echo ""
  echo "=== [POLL #${i}] elapsed=${ELAPSED}s ==="
  echo "$STATUS"

  # 完成条件
  if echo "$STATUS" | grep -qE "^EXITED|\[VERDICT\] (PASS|FAIL)|\[SUMMARY\]|Traceback|SystemExit"; then
    echo ""
    echo "[POLL] 检测到结束标志，抓完整日志:"
    sshpass -e ssh "${SSH_OPTS[@]}" "$HOST" "cat ${LOG_REMOTE}" > /tmp/case2_full.log
    echo "[POLL] 完整日志保存到本地 /tmp/case2_full.log"
    tail -100 /tmp/case2_full.log
    exit 0
  fi
done

echo ""
echo "[TIMEOUT] ${POLL_MAX} × ${POLL_INTERVAL}s = $((POLL_MAX * POLL_INTERVAL / 60)) min 内未完成"
echo "[TIMEOUT] 抓最新日志:"
sshpass -e ssh "${SSH_OPTS[@]}" "$HOST" "cat ${LOG_REMOTE}" > /tmp/case2_full.log
tail -50 /tmp/case2_full.log
exit 2
