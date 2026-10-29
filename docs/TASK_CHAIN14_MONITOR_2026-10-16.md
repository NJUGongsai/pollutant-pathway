# 任务书 — chain14 双臂值守监控（OCAgent，2026-10-16）

> 执行者：OCAgent（值守监控，**零代码零 git**——不建分支、不 commit、
> 不 push、不改任何仓库文件）。主会话已停自建轮询器，监控权全在本任务书。
> 性质：纯机械决策表，**零自由裁量**——每个分支的命令写死，异常即写报告
> 退出，不自行处置。

## 一、监控对象与通道（全部写死）

| 件 | 值 |
|---|---|
| SSH | `ssh -i ~/.ssh/hpc_wuzh02_key -p 65091 -o BatchMode=yes -o ConnectTimeout=20 aclhl3hbth@wuzh02.hpccube.com`（本地 Mac 发起；输出里 perl locale 警告无害） |
| 代码树（HPC） | `~/EnzymeAgent/v43c14` |
| build 作业 | **46690064（arm a）/ 46690065（arm b）**，日志 `~/EnzymeAgent/v43c14/chain14_build_<jobid>.out`，成功标志行 `CHAIN14-BUILD-PASS`、失败 `CHAIN14-BUILD-FAIL` |
| 批根 | `~/ppv1_hpc/batch/chain14{a,b}_s5b_20261015`；runs 根 `~/ppv1_hpc/runs/chain14{a,b}_s5b_20261015` |
| PY | `~/ppv1_hpc/venv_v44run/bin/python` |
| env | `~/ppv1_hpc/env/llm.env`（只查存在，**永不打印内容**） |
| 本地监控日志 | `/tmp/chain14_monitor.log`（追加写）；最终报告 `reports/ppv1_s5b/chain14_monitor_2026-10-16/monitor_report.md`（仓库 gitignored 区，监控报告是唯一允许新建的文件） |

## 二、循环与超时

- 每 **20 分钟**一轮（`sleep 1200`），最多 **40 轮**（≈13 小时）；超时→写报告退出。
- SSH 连不上：连续 **3 轮**失败→写报告退出（单轮失败=下一轮重试，日志记一笔）。
- 每轮动作：squeue 查作业态 + tail 相应 .out 尾部，按 §三状态机走。

## 三、状态机（机械执行，命令逐字）

### 状态 1：BUILD（当前状态，两作业已提交）

每轮：`squeue -h -j 46690064,46690065 -o "%i %T"` + `tail -3` 两个 build .out。
- 两 .out 均含 `CHAIN14-BUILD-PASS` → 进入状态 2（一次性）。
- 任一含 `CHAIN14-BUILD-FAIL`，或作业离开队列且无 PASS 行 → **写报告退出**（报告含两 .out 尾部 20 行）。
- 仍在跑 → 日志记 `poll N: building`，继续。

### 状态 2：GATES+RUN 提交（仅执行一次）

对 arm ∈ {a,b}，在**登录节点**逐条执行（cd ~/EnzymeAgent/v43c14；PYTHONPATH=~/EnzymeAgent/v43c14/src；PY 同上表）：

```bash
# 1) approve（幂等）
# 2026-10-16 修正：补必填 --user-authorization（首版漏参 → arm=a RC1=2/rc=11，run 未提交；
# build 双 PASS 不受影响；授权串沿用 s5b 先例格式 launch-authorized-<CC 确认日>）
$PY -B -m pathway_v43.pollutant.s5b_cli approve \
  --batch-root ~/ppv1_hpc/batch/chain14${ARM}_s5b_20261015 \
  --preregistration-id prereg-chain14-evidence-ab-2026-10-15 \
  --user-authorization launch-authorized-2026-10-15
# 2) no-cap 标记（幂等；除下列参数外不得传任何金额参数）
$PY -B -m pathway_v43.pollutant.s5b_cli budget \
  --batch-root ~/ppv1_hpc/batch/chain14${ARM}_s5b_20261015 \
  --budget-mode no_monetary_cap_user_decision \
  --user-decision-date 2026-10-15 \
  --user-decision-record "CC 2026-10-15 确认 chain14 证据卡 A/B 双臂预注册(docs/CHAIN14_EVIDENCE_AB_PREREG_2026-10-15.md): no-cap 沿用 chain13 同款(双臂约 12.6M tokens), 并授权主会话代确认与自动推进发车流水"
# 3) 验证两文件在位（不在=失败）
ls ~/ppv1_hpc/batch/chain14${ARM}_s5b_20261015/preregistration_approval.json \
   ~/ppv1_hpc/batch/chain14${ARM}_s5b_20261015/budget_no_cap.json
# 4) 提交 run（ARM 环境变量放 sbatch 前面——sbatch 快照语义）
cd ~/EnzymeAgent/v43c14 && ARM=${ARM} sbatch scripts/hpc/sbatch_chain14_run.sh
```

- 4 条命令任何一步非零退出/文件不在 → **写报告退出**（含完整命令输出；不重试、不 scancel）。
- 两臂 run job id 记入日志（run .out 在 `~/EnzymeAgent/v43c14/chain14_run_<jobid>.out`）→ 进入状态 3。

### 状态 3：RUN

每轮查两 run 作业 + tail 两 run .out（成功行 `CHAIN14-RUN-PASS`、失败 `CHAIN14-RUN-FAIL`）。
- 两 PASS → 进入状态 4。
- 任一 FAIL / 作业消失无 PASS → **写报告退出**（含 .out 尾部 30 行）。
- run 作业单臂超过 **9 小时**仍在跑 → 写报告退出（报告标注疑似卡死，不 scancel）。

### 状态 4：SCORE 提交与终态

对 arm ∈ {a,b}：`cd ~/EnzymeAgent/v43c14 && ARM=${ARM} sbatch scripts/hpc/sbatch_chain14_score.sh`，记录 job id（score .out 同目录 `chain14_score_<jobid>.out`）。
- 每轮查 score 作业；两作业完成 → 检查
  `~/ppv1_hpc/batch/chain14{a,b}_s5b_20261015/metrics.json` 与 `metrics.json.v1` 四件在位 → 写**最终报告**退出（报告含：各臂 metrics.json 的 buckets 与 main_caliber hit@1/3/5、score .out 尾部 10 行、全程时间线、tokens 账目行如有）。
- 任一 score FAIL → 写报告退出。

## 四、红线（违反=立即停止并报告）

1. **只报不动**：除 §三写死的命令外，不执行任何其它远端命令；**永不 scancel 任何作业**。
2. 零 git（不建分支/不 commit/不 push/不 status 改动）；不改仓库任何既有文件；唯一允许新建=监控日志与最终报告。
3. 不碰批根内部数据（只 ls 检查与读 .out/metrics 顶层字段）；不打印 env/密钥内容；金标/题面永不读取。
4. 判分零干预：score 作业的参数与提交方式只按本任务书，不改判分口径。
5. 任何状态机未覆盖的情况 → 写报告退出（含现象描述），不自行判断处置。

## 五、回传义务

退出时（正常完成/异常/超时三选一）回报：①终态一句话（双臂判分产物齐/卡在哪）；②关键数字（若到状态 4：两臂 hit@1 与 buckets）；③时间线（build/run/score 各阶段起止与 job id）；④异常原文尾部。最终报告文件路径。
