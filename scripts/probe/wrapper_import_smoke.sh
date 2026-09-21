#!/usr/bin/env bash
# ============================================================
# 晨羽 wrapper import 冒烟脚本（层 1：不吃 GPU）
# ============================================================
# 目标：在晨羽 Python 3.12.3 冻结环境里，验证：
#   1. enzymecage_wrapper 能被 import
#   2. 拿到 wrapper 的 version / signature
#   3. torch.cuda 报告（不分配显存）
#
# 严格边界：不 load 模型 / 不构造 dataset / 不调 predict / 不写晨羽任何文件
# 传输方式：python 脚本 base64 编码走 stdin（彻底避开 shell 引号问题）
# ============================================================

set -euo pipefail

SSH_HOST="30c1b91fe059488f946c1b15bda3560c71.gz15.chenyu.cn"
SSH_PORT="20234"
SSH_USER="root"

if [ -z "${SSHPASS:-}" ]; then
  echo "[ERR] 请先: export SSHPASS='<password>'" >&2
  exit 1
fi

SSH_OPTS=(
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
  -o ConnectTimeout=15
  -p "${SSH_PORT}"
)

# --- 远端 Python 冒烟脚本（在此本地文件内 heredoc） ---
read -r -d '' REMOTE_PY <<'PYEOF' || true
import sys, os, importlib, traceback

print("=" * 60)
print("[SMOKE] Python:", sys.version.split()[0])
print("[SMOKE] executable:", sys.executable)
print("=" * 60)

D4   = "/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/d4b1a_wrapper_hash_relative_path_final_package_correction_20260716"
V1   = "/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/enzymecage_v1_20260714"
CODE = "/usrdata/EnzymeCAGE_data/EnzymeCAGE-master"

for p in [D4, V1, CODE]:
    print(f"[PATH] exists={os.path.isdir(p)} : {p}")

# 加 sys.path
wrapper_pkg_dir = os.path.join(D4, "enzymecage_wrapper")
for p in [wrapper_pkg_dir, D4, CODE]:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
        print(f"[PATH+] {p}")

print("-" * 60)

# 尝试 import wrapper 顶层（多个候选名）
wrapper_candidates = ["enzymecage_wrapper", "wrapper", "d4_wrapper"]
imported = None
for name in wrapper_candidates:
    try:
        m = importlib.import_module(name)
        fp = getattr(m, "__file__", "?")
        print(f"[IMPORT OK] {name} @ {fp}")
        for attr in ["__version__", "VERSION", "SIGNATURE", "predict", "run_inference", "rank_enzymes"]:
            if hasattr(m, attr):
                v = getattr(m, attr)
                print(f"  .{attr} = {v if not callable(v) else '<callable>'}")
        imported = m
        break
    except Exception as e:
        print(f"[IMPORT --] {name}: {type(e).__name__}: {str(e)[:150]}")

# 探测 wrapper package 目录结构
if os.path.isdir(wrapper_pkg_dir):
    print(f"[TREE] {wrapper_pkg_dir}:")
    try:
        for name in sorted(os.listdir(wrapper_pkg_dir))[:40]:
            full = os.path.join(wrapper_pkg_dir, name)
            kind = "d" if os.path.isdir(full) else "f"
            print(f"  {kind} {name}")
    except Exception as e:
        print(f"  [ERR] {e}")

# 尝试 enzymecage 主库
try:
    import enzymecage
    print(f"[IMPORT OK] enzymecage @ {enzymecage.__file__}")
except Exception as e:
    print(f"[IMPORT --] enzymecage: {type(e).__name__}: {str(e)[:150]}")

# torch/cuda 报告
try:
    import torch
    print(f"[TORCH] version={torch.__version__}")
    print(f"[TORCH] cuda.is_available={torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"[TORCH] cuda.device_count={torch.cuda.device_count()}")
        print(f"[TORCH] cuda.name(0)={torch.cuda.get_device_name(0)}")
        # 不分配显存
except Exception as e:
    print(f"[TORCH] {type(e).__name__}: {e}")

print("=" * 60)
print("[SMOKE] DONE (no model loaded, no GPU allocated)")
PYEOF

# base64 编码脚本，远端解码执行
PY_B64=$(printf '%s' "$REMOTE_PY" | base64 -w0)

REMOTE_CMD="source /usrdata/EnzymeCAGE_envs/enzymecage_py312/bin/activate && \
python -c \"import base64,sys; exec(base64.b64decode(sys.argv[1]).decode())\" \"${PY_B64}\""

echo ">>> SSH → 晨羽（激活 Python 3.12.3 env → 跑冒烟）"
sshpass -e ssh "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" "${REMOTE_CMD}"
