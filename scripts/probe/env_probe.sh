#!/bin/bash
# Chenyu HPC 只读探测脚本
# 目标：验证学生 stable_runtime_context.json 里 6 类路径的存在性
# 严格约束：只读、不 activate 环境、不 import wrapper、不 load 模型、不消耗 GPU

set +e

echo "=========================================="
echo "[0] Host & Uptime"
echo "=========================================="
hostname; uptime; whoami
echo ""

echo "=========================================="
echo "[1] D4 Wrapper Root"
echo "=========================================="
for p in \
  "/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/d4b1a_wrapper_hash_relative_path_final_package_correction_20260716" \
  "/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Returned_Result_Summaries/d4b1a_wrapper_hash_relative_path_final_package_correction_20260716"; do
  echo "--- $p ---"
  [ -d "$p" ] && { echo "[OK] exists"; ls -la "$p" | head -20; } || echo "[MISS] not found"
done
echo ""

echo "=========================================="
echo "[2] EnzymeCAGE v1 Package Root"
echo "=========================================="
for p in \
  "/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/enzymecage_v1_20260714" \
  "/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Returned_Result_Summaries/enzymecage_v1_20260714"; do
  echo "--- $p ---"
  if [ -d "$p" ]; then
    echo "[OK] exists"
    ls -la "$p" | head -20
    echo "-- size:"; du -sh "$p" 2>/dev/null
  else
    echo "[MISS] not found"
  fi
done
echo ""

echo "=========================================="
echo "[3] EnzymeCAGE Code Root"
echo "=========================================="
p="/usrdata/EnzymeCAGE_data/EnzymeCAGE-master"
[ -d "$p" ] && { echo "[OK] exists"; ls -la "$p" | head -20; } || echo "[MISS] not found"
echo ""

echo "=========================================="
echo "[4] Python 3.12.3 Frozen Env (only --version, NO activate, NO import wrapper)"
echo "=========================================="
PY="/usrdata/EnzymeCAGE_envs/enzymecage_py312/bin/python"
if [ -x "$PY" ]; then
  echo "[OK] executable exists"
  "$PY" --version
  "$PY" -c "import sys; print('sys.executable:', sys.executable); print('sys.version:', sys.version)"
  echo "-- realpath:"; readlink -f "$PY"
  echo "-- site-packages first 20:"
  ls /usrdata/EnzymeCAGE_envs/enzymecage_py312/lib/python3.12/site-packages 2>/dev/null | head -20
else
  echo "[MISS] python executable not found"
fi
echo ""

echo "=========================================="
echo "[5] GPU Availability (nvidia-smi -L only, NO model load)"
echo "=========================================="
if command -v nvidia-smi &> /dev/null; then
  nvidia-smi -L
  echo "-- header:"; nvidia-smi | head -5
else
  echo "[MISS] nvidia-smi not available"
fi
echo ""

echo "=========================================="
echo "[6] M3 Data Assets"
echo "=========================================="
for p in \
  "/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/m3_agent_data_assets" \
  "/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Returned_Result_Summaries/m3_agent_data_assets"; do
  echo "--- $p ---"
  if [ -d "$p" ]; then
    echo "[OK] exists"
    ls -la "$p" 2>/dev/null | head -20
    echo "-- total size:"; du -sh "$p" 2>/dev/null
    echo "-- deep structure (2 levels):"
    find "$p" -maxdepth 2 -type d 2>/dev/null
  else
    echo "[MISS] not found"
  fi
done
echo ""

echo "=========================================="
echo "[7] Working directory candidates"
echo "=========================================="
for d in /root /home /workspace /tmp; do
  echo "--- $d ---"; ls -la "$d" 2>/dev/null | head -10
done
echo ""

echo "=========================================="
echo "[8] Disk & Memory"
echo "=========================================="
df -h | head -10
echo ""
free -h
echo ""

echo "=========================================="
echo "PROBE COMPLETE — All operations were READ-ONLY."
echo "=========================================="
