#!/usr/bin/env bash
# ============================================================
# 本地代码 → 晨羽同步（M3I6-A 部署路径）
# ============================================================
# 用途：把 /home/axlhuang/projects/enzymecage_crew 全量推到
#       晨羽 /root/projects/enzymecage_crew
# 手段：tar 流管道（避开 rsync 依赖），--exclude 黑名单
# .env：本地版是 DRY_RUN=1，晨羽版自动改为 DRY_RUN=0
# ============================================================

set -euo pipefail

LOCAL_ROOT="/home/axlhuang/projects/enzymecage_crew"
REMOTE_ROOT="/root/projects/enzymecage_crew"

SSH_HOST="30c1b91fe059488f946c1b15bda3560c71.gz15.chenyu.cn"
SSH_PORT="20234"
SSH_USER="root"

if [ -z "${SSHPASS:-}" ]; then
  echo "[ERR] 需要 SSHPASS" >&2; exit 1
fi

SSH_OPTS=(
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
  -o ConnectTimeout=15
  -o ServerAliveInterval=15
  -p "${SSH_PORT}"
)

# tar 黑名单
EXCLUDES=(
  --exclude='__pycache__'
  --exclude='*.pyc'
  --exclude='.git'
  --exclude='.venv'
  --exclude='venv'
  --exclude='.pytest_cache'
  --exclude='.coverage'
  --exclude='htmlcov'
  --exclude='reports'
  --exclude='EnzymeCAGE_ref'   # 学生原始 clone，晨羽已有 CODE_ROOT
  --exclude='.env'              # 本地版 DRY_RUN=1，晨羽需要 DRY_RUN=0
  --exclude='*.pt'
  --exclude='*.pth'
  --exclude='*.ckpt'
  --exclude='*.bin'
)

echo ">>> [1/3] 远端创建工作目录并清理旧内容（如果存在）"
sshpass -e ssh "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" "
  mkdir -p ${REMOTE_ROOT}
  # 仅清空非模型/非 .env 内容；保留 .env（若用户已改过）
  find ${REMOTE_ROOT} -mindepth 1 -maxdepth 1 ! -name '.env' -exec rm -rf {} +  2>&1 || true
  ls -la ${REMOTE_ROOT}
"

echo ""
echo ">>> [2/3] tar over ssh 推送（预计 <10s，6-10MB）"
cd "${LOCAL_ROOT}"
tar czf - "${EXCLUDES[@]}" . \
  | sshpass -e ssh "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" \
    "tar xzf - -C ${REMOTE_ROOT} && echo '[REMOTE] 解压完成' && du -sh ${REMOTE_ROOT}"

echo ""
echo ">>> [3/3] 生成晨羽版 .env（DRY_RUN=0，其他保留）"
# 从本地 .env.example 生成远端 .env，DRY_RUN 改为 0
# 注意：DASHSCOPE_API_KEY 保留为 TODO 占位，需人工填
CHENYU_ENV=$(sed \
  -e 's|ENZYMECAGE_DRY_RUN=1|ENZYMECAGE_DRY_RUN=0|' \
  -e 's|sk-your-dashscope-api-key-here|sk-TODO-fill-your-key-here|' \
  "${LOCAL_ROOT}/.env.example")

sshpass -e ssh "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" "
  # 若 .env 已存在（用户已改）则不覆盖，只提示
  if [ -f ${REMOTE_ROOT}/.env ]; then
    echo '[SKIP] ${REMOTE_ROOT}/.env 已存在，保留原文件'
  else
    cat > ${REMOTE_ROOT}/.env <<'ENVEOF'
${CHENYU_ENV}
ENVEOF
    echo '[WRITE] 已生成 ${REMOTE_ROOT}/.env（DRY_RUN=0）'
  fi
  echo '---LS---'
  ls -la ${REMOTE_ROOT}
  echo '---.env preview---'
  head -30 ${REMOTE_ROOT}/.env
"

echo ""
echo ">>> [DONE] 同步完成。远端目录：${REMOTE_ROOT}"
