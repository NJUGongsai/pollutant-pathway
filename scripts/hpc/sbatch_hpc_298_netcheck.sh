#!/usr/bin/env bash
# PPV1 298 HPC 首作业:站点自证 netcheck(分区开通后的第一作业,硬门)。
#
# 用途:在计算节点上实测 ①计算节点外网出口(dashscope LLM API 路由,
# 侦察遗留风险项)②flock 互斥语义(整条管线的锁基元:qid 域协调锁/
# 闸门锁/driver.lock 全靠它)③rdkit 可导入 ④python 版本与包根
# ⑤家目录可写。任一项不过 ⇒ 作业非零退出 ⇒ 不发第一真批。
#
# 站点说明:脚本缺省为乌镇 wuzh02.hpccube.com:65091;其中 python
# 路径/rdkit pip 路线/分区名等事实来自 zzeshell 侦察
# (docs/HPC_SHUGUANG_SURVEY_2026-10-12.md),乌镇节点由本作业逐项
# 同款实测,不假设两站环境相同。
#
# 提交(分区名以乌镇 sinfo -a 实测为准;可 sbatch --partition= 覆盖):
#   ssh -i <key> -p 65091 aclhl3hbth@wuzh02.hpccube.com
#   cd ~/ppv1_hpc/dependingv43
#   WS=$HOME/ppv1_hpc sbatch scripts/hpc/sbatch_hpc_298_netcheck.sh
# 判定:作业退出码 0 且日志含 NETCHECK-PASS 全行。
#
# 分区权限未开通前本脚本不会被提交(无权限 sbatch 直接被拒)。

#SBATCH --job-name=ppv1-netcheck
#SBATCH --partition=hx1hdnormal
#SBATCH --cpus-per-task=2
#SBATCH --time=00:10:00
#SBATCH --output=ppv1_netcheck_%j.out

set -euo pipefail

WS="${WS:-$HOME/ppv1_hpc}"
CODE="$WS/dependingv43"

# python 定位:优先 zzeshell 侦察确认的系统 python3.12 路径;乌镇上
# 若不存在则回退 PATH 中的 python3(并在下方打印实际版本供核对)
if [ -n "${PY:-}" ]; then
  :
elif [ -x /usr/local/python3.12/bin/python3 ]; then
  PY=/usr/local/python3.12/bin/python3
else
  PY="$(command -v python3)"
fi

fail() { echo "NETCHECK-FAIL: $*" >&2; exit 1; }

echo "== netcheck @ $(date -u +%FT%TZ) node=$(hostname) =="
echo "python: $PY"
"$PY" --version || fail "python 不可用"
echo "ulimit -n (soft)=$(ulimit -Sn)"

# ---- ① rdkit(部署步骤已 pip install --user rdkit;注意包名是 rdkit
# 非 rdkit-pypi——zzeshell 实测教训) ----
"$PY" -c "import rdkit; print('rdkit', rdkit.__version__)" \
  || fail "rdkit 导入失败(先 pip3 install --user rdkit)"

# ---- ② 本仓代码布局(PYTHONPATH 指 src,包可导入) ----
if [ -d "$CODE/src" ]; then
  PYTHONPATH="$CODE/src" "$PY" -c "import pathway_v43; \
print('pathway_v43 import ok')" \
    || fail "pathway_v43 导入失败(检查解包布局 $CODE/src)"
else
  fail "缺 $CODE/src(先按 deploy.md 解包)"
fi

# ---- ③ 家目录可写(Lustre /public;zzeshell 事实,乌镇实测) ----
mkdir -p "$WS" || fail "WS 目录建不了:$WS"
probe_file="$WS/.netcheck_write_probe"
echo "probe" > "$probe_file" || fail "家目录写失败:$WS"
grep -q probe "$probe_file" || fail "家目录读回失败:$WS"
rm -f "$probe_file"
echo "df: $(df -h "$WS" | tail -1)"

# ---- ④ flock 互斥(锁基元自证:父持锁 ⇒ 子进程再取必拒;父放 ⇒ 子得) ----
export WS
"$PY" - <<'PYEOF' || fail "flock 互斥语义不成立(管线锁基元失效)"
import fcntl
import os
import subprocess
import sys

path = os.path.join(os.environ["WS"], ".flock_probe")
fh = open(path, "a+")
fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
child = (
    "import fcntl, sys\n"
    f"path = {path!r}\n"
    "f = open(path, 'a+')\n"
    "try:\n"
    "    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
    "except OSError:\n"
    "    sys.exit(3)\n"
    "sys.exit(0)\n"
)
proc = subprocess.run([sys.executable, "-c", child])
if proc.returncode == 0:
    print("flock: 子进程未被互斥(异常!)")
    sys.exit(1)
fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
fh.close()
proc = subprocess.run([sys.executable, "-c", child])
if proc.returncode != 0:
    print("flock: 父释放后子进程取不到锁(异常!)")
    sys.exit(1)
print("flock: 互斥/释放语义成立")
PYEOF
rm -f "$WS/.flock_probe"

# ---- ⑤ 计算节点外网出口:dashscope 端到端路由(硬门,侦察遗留风险项;
# 不带 key,期望 API 层 JSON 应答=链路通;真 key 在正式批才用) ----
resp="$(curl -sS -m 60 -X POST \
  https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation \
  -H 'Content-Type: application/json' -d '{}' 2>&1 || true)"
echo "dashscope resp(head): $(echo "$resp" | head -c 200)"
if echo "$resp" | grep -Eq 'InvalidApiKey|request_id'; then
  echo "dashscope: 计算节点出口通(API 层应答)"
else
  fail "计算节点到 dashscope 无 API 层应答(出口不通;考虑登录节点代理方案)"
fi

echo "NETCHECK-PASS: python/rdkit/layout/disk/flock/dashscope 全过"
