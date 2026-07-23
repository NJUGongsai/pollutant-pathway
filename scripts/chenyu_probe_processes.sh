#!/bin/bash
# 学生进程与 GPU 占用状况探测（避免共享资源冲突）
# 严格边界：只看进程 meta / GPU 占用 / 已交付输出目录时间戳
# 不看：bash_history / codex / 私人文件

set +e

echo "=========================================="
echo "[A] 当前 GPU 占用（含进程 PID）"
echo "=========================================="
nvidia-smi
echo ""

echo "=========================================="
echo "[B] Python / EnzymeCAGE 相关活跃进程"
echo "=========================================="
ps -ef --sort=-%cpu | head -20
echo ""
echo "--- Python 相关进程（含命令行）："
ps -eo pid,user,pcpu,pmem,etime,command | grep -iE "python|enzymecage|torch" | grep -v grep | head -20
echo ""

echo "=========================================="
echo "[C] HPC_Returned_Result_Summaries/ 目录最近交付时间戳"
echo "     （按修改时间倒序，只看目录名，判断学生工作进度）"
echo "=========================================="
ls -la --time-style=long-iso \
  /root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/ \
  2>/dev/null | sort -k6,7 -r | head -30
echo ""

echo "=========================================="
echo "[D] HPC_Inputs/ 目录时间戳（学生正在准备的输入）"
echo "=========================================="
ls -la --time-style=long-iso /usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Inputs/ 2>/dev/null | head -20
echo ""

echo "=========================================="
echo "[E] 最近 24 小时被修改的目录（学生活跃工作区，只看目录名）"
echo "=========================================="
find /usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Returned_Result_Summaries -maxdepth 2 -type d -mtime -1 2>/dev/null | head -20
echo ""

echo "=========================================="
echo "[F] GPU 4090D 详细规格（显存版本判断）"
echo "=========================================="
nvidia-smi --query-gpu=name,memory.total,memory.free,memory.used,driver_version,compute_cap --format=csv
echo ""

echo "=========================================="
echo "[G] 系统总体负载"
echo "=========================================="
uptime
echo "--- 内存："
free -h | head -3
echo "--- 磁盘 /root & /usrdata："
df -h /root /usrdata 2>/dev/null
echo ""

echo "=========================================="
echo "PROBE COMPLETE"
echo "=========================================="
