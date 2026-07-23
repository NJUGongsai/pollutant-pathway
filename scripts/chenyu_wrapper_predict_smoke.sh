#!/usr/bin/env bash
# ============================================================
# 晨羽 wrapper.predict 空跑冒烟（层 2：真跑一次 predict，吃 GPU）
# ============================================================
# 改造：nohup 后台启动 + 本端轮询（避免 SSH 长静默 broken pipe）
# ============================================================

set -euo pipefail

SSH_HOST="30c1b91fe059488f946c1b15bda3560c71.gz15.chenyu.cn"
SSH_PORT="20234"
SSH_USER="root"
LOG="/tmp/chenyu_wrapper_predict_smoke.log"
PIDFILE="/tmp/chenyu_wrapper_predict_smoke.pid"
POLL_INTERVAL=20        # 秒
POLL_MAX_ROUNDS=30      # 30 × 20s = 10 分钟上限

if [ -z "${SSHPASS:-}" ]; then
  echo "[ERR] 请先: export SSHPASS='<password>'" >&2
  exit 1
fi

SSH_OPTS=(
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
  -o ConnectTimeout=15
  -o ServerAliveInterval=10
  -p "${SSH_PORT}"
)

read -r -d '' REMOTE_PY <<'PYEOF' || true
import os, sys, time, gzip, csv, traceback, threading

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# 心跳线程：每 15s 打一次 tick + 显存
def _heartbeat():
    try:
        import torch
    except Exception:
        torch = None
    i = 0
    while True:
        try:
            mem = torch.cuda.memory_allocated() / 1024**2 if torch else -1
        except Exception:
            mem = -1
        print(f"[HEARTBEAT] tick={i} cuda_alloc={mem:.1f} MiB t={time.time():.1f}", flush=True)
        i += 1
        time.sleep(15)

threading.Thread(target=_heartbeat, daemon=True).start()

D4   = "/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/d4b1a_wrapper_hash_relative_path_final_package_correction_20260716"
V1   = "/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/enzymecage_v1_20260714"
CODE = "/usrdata/EnzymeCAGE_data/EnzymeCAGE-master"
ASSETS = "/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/m3_agent_data_assets/assets"

for p in [D4, CODE, V1]:
    if p not in sys.path:
        sys.path.insert(0, p)

# 抽真实数据
route_c_csv = os.path.join(ASSETS, "route_c", "reference_reaction_index.csv.gz")
sample_rxn = None
if os.path.exists(route_c_csv):
    with gzip.open(route_c_csv, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for col in ("CANO_RXN_SMILES", "reaction_smiles", "rxn_smiles"):
                if col in row and row[col]:
                    sample_rxn = row[col]
                    break
            if sample_rxn:
                break

d4_csv = os.path.join(ASSETS, "d4", "uid_asset_availability.csv.gz")
sample_uids = []
if os.path.exists(d4_csv):
    with gzip.open(d4_csv, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        uid_col = None
        for cand in ("UniprotID", "uniprot_id", "uid", "UID"):
            if cand in header:
                uid_col = cand
                break
        if uid_col:
            for row in reader:
                u = (row.get(uid_col) or "").strip()
                if u:
                    sample_uids.append(u)
                if len(sample_uids) >= 5:
                    break

print(f"[PROBE] sample_rxn_len={len(sample_rxn) if sample_rxn else 0}, sample_uids_n={len(sample_uids)}", flush=True)
if not sample_rxn or not sample_uids:
    print("[ABORT]", flush=True)
    sys.exit(2)

print("=" * 60, flush=True)
print("[STAGE-A] import wrapper", flush=True)
t0 = time.time()
from enzymecage_wrapper import EnzymeCAGERequest, predict
print(f"[STAGE-A] import OK ({time.time()-t0:.2f}s)", flush=True)

print("=" * 60, flush=True)
print("[STAGE-B] build request", flush=True)
req = EnzymeCAGERequest(
    reaction_smiles=sample_rxn,
    enzyme_pool_uids=sample_uids,
    top_k=3,
    return_ci=True,
)
print(f"[STAGE-B] request built: reaction_len={len(sample_rxn)}, pool={len(sample_uids)}, top_k=3", flush=True)

print("=" * 60, flush=True)
print("[STAGE-C] predict()  ⚠️ 心跳 15s 一次；等 GPU 显存跳升就是真上 GPU 了", flush=True)
import torch
print(f"[STAGE-C] cuda memory before: {torch.cuda.memory_allocated()/1024**2:.1f} MiB", flush=True)
t0 = time.time()
try:
    response = predict(req)
    elapsed = time.time() - t0
    print(f"[STAGE-C] predict OK ({elapsed:.2f}s)", flush=True)
    print(f"[STAGE-C] cuda memory after:  {torch.cuda.memory_allocated()/1024**2:.1f} MiB", flush=True)
    print(f"[STAGE-C] cuda memory peak:   {torch.cuda.max_memory_allocated()/1024**2:.1f} MiB", flush=True)

    print("=" * 60, flush=True)
    print("[RESULT] model_version =", getattr(response, "model_version", "?"), flush=True)
    print("[RESULT] evidence_hash =", getattr(response, "evidence_hash", "?"), flush=True)
    ranked = getattr(response, "ranked_enzymes", None) or []
    print(f"[RESULT] ranked_enzymes count = {len(ranked)}", flush=True)
    for i, r in enumerate(ranked[:3], 1):
        uid = getattr(r, "uid", "?")
        sc = getattr(r, "score", "?")
        rk = getattr(r, "rank", "?")
        ci = getattr(r, "ensemble_ci", None)
        print(f"  #{i} uid={uid} score={sc} rank={rk} ci={ci}", flush=True)
except Exception as e:
    elapsed = time.time() - t0
    print(f"[STAGE-C] predict FAILED after {elapsed:.2f}s: {type(e).__name__}: {e}", flush=True)
    traceback.print_exc()
    sys.exit(3)

print("=" * 60, flush=True)
print("[SMOKE] LAYER-2 DONE", flush=True)
PYEOF

PY_B64=$(printf '%s' "$REMOTE_PY" | base64 -w0)

# 后台启动：立即返回 PID
LAUNCH_CMD="source /usrdata/EnzymeCAGE_envs/enzymecage_py312/bin/activate && \
export CUDA_VISIBLE_DEVICES=0 && \
export PYTHONUNBUFFERED=1 && \
export D4_WRAPPER_ROOT=/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/d4b1a_wrapper_hash_relative_path_final_package_correction_20260716 && \
export ENZYMECAGE_V1_PACKAGE_ROOT=/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/enzymecage_v1_20260714 && \
export ENZYMECAGE_CODE_ROOT=/usrdata/EnzymeCAGE_data/EnzymeCAGE-master && \
export M3_AGENT_DATA_ASSETS_ROOT=/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/m3_agent_data_assets/assets && \
rm -f ${LOG} ${PIDFILE} && \
nohup python -u -c \"import base64,sys; exec(base64.b64decode(sys.argv[1]).decode())\" \"${PY_B64}\" > ${LOG} 2>&1 & \
echo \$! > ${PIDFILE} && \
echo \"LAUNCHED pid=\$(cat ${PIDFILE})\""

echo ">>> [LAUNCH] 后台启动 wrapper.predict"
sshpass -e ssh "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" "${LAUNCH_CMD}"

echo ">>> [POLL] 每 ${POLL_INTERVAL}s 轮询日志，最多 ${POLL_MAX_ROUNDS} 轮（$((POLL_INTERVAL * POLL_MAX_ROUNDS / 60)) 分钟上限）"
for i in $(seq 1 ${POLL_MAX_ROUNDS}); do
  sleep ${POLL_INTERVAL}
  STATUS=$(sshpass -e ssh "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" "
    PID=\$(cat ${PIDFILE} 2>/dev/null)
    if [ -n \"\$PID\" ] && kill -0 \$PID 2>/dev/null; then STATE=RUNNING; else STATE=EXITED; fi
    GPU=\$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null)
    LAST=\$(tail -3 ${LOG} 2>/dev/null | tr '\n' '|')
    echo \"[POLL#${i}] state=\$STATE gpu_mem=\${GPU}MiB last3=\$LAST\"
  ")
  echo "${STATUS}"
  if echo "${STATUS}" | grep -q "state=EXITED"; then
    echo ">>> [DONE] 进程已退出，拉取完整日志："
    sshpass -e ssh "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" "cat ${LOG}"
    exit 0
  fi
  if echo "${STATUS}" | grep -qE "\[SMOKE\] LAYER-2 DONE|\[STAGE-C\] predict OK|\[STAGE-C\] predict FAILED"; then
    echo ">>> [FINISHED] 拉取完整日志："
    sshpass -e ssh "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" "cat ${LOG}"
    exit 0
  fi
done

echo ">>> [TIMEOUT] 达到轮询上限，拉取当前日志："
sshpass -e ssh "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" "cat ${LOG}"
