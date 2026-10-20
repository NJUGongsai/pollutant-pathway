# T-H r2 操作补充与接续入口（2026-10-20）

这是已授权发车的操作补充，不是新预注册、不代签、不改已签文本。题域：**298＝RHEA 通用酶学／已见题（post-hoc）**。原事故批 `t_h_s5b_298_20261020` 保持只读。

## 授权、身份和当前停点

| 项 | 已落字与消费方式 |
|---|---|
| 原预注册／付费 | `reports/ppv1_s5b/t_h_2026-10-20/record/preregistration_approval.json` 已确认；no-cap 旁块在同目录；不重写其签发时间、文本 SHA 或原文 |
| 原批准文本 | PREP SHA256 `48ee237bf0485ed96b92e5fe2aba0fc565892de05b419f134b22c7a02a317512`；TASK 原批准快照来自 `git show abbfa39:docs/T_H_LAUNCH_TASK_2026-10-20.md`，SHA256 `b3984bbe98eb99e6b909af49b9a01b5890ab47d2fd7d2fa9ecd7b08b01fd5e25`。当前 TASK 已追加事故注记，不冒充原批准文本 |
| r2 续跑 | `docs/HANDOFF_T_H_RELAUNCH_2026-10-20.md`：CC 已授权两 delta 放行后自动续跑；新批必须重新 build，旧批不覆盖 |
| 科学源码 | `c360e7428a9b765636922282f27c65e917071460`（两 delta＋五测试）；compiler SHA `f917762bf9ec43d70b85ef3740ab7f22b866b42c06a1461ec336882eb2685dfc`；evaluation SHA `37c092310d34d9f417234ccacd508942b3ce3edef640c73ab94022fd8dc75ad8`；有限范围复核见 `docs/T_H_DEPLOY_FIX2_REVIEW_2026-10-20.md` |
| 操作脚本 | 以 `docs/T_H_R2_SCRIPT_LOCK_2026-10-20.json` 文件 SHA 清单核本地和部署态；这些操作改动不改 src/tests 科学判据，不改原审批 |
| 站点 | 乌镇 wuzh02，分区 `wzhcnormal`；代码 `/work/home/aclhl3hbth/EnzymeAgent/v43cTH`；Python `~/ppv1_hpc/venv_v44run/bin/python`（远端已独立核 compiler-6、v3 available；netcheck 46954668 完成 Exit0） |
| 作业参数 | **单 job、workers/max_in_flight＝8/8**，每题最多三次真实逻辑调用、两轮格式反馈，attempts/hypothesis＝1；gate＝4470 HTTP attempts、RPM 200、TPM 3M；证据卡关；同 chain13/14。原 TASK 中旧通用“20 workers×5 shards”由最新重启移交 §3.5 明确替代；不是新增科学变量 |
| 批根 | `/work/home/aclhl3hbth/ppv1_hpc/batch/t_h_s5b_298_20261020r2`；runs 同名；首次核查 r2 不存在、squeue 空；以后以实时状态为准 |

## 一次设定（远端 shell）

以下变量仅为命令参数，不读凭证正文。不要把 `llm.env` 打印到日志。

```bash
TH_WS=/work/home/aclhl3hbth/ppv1_hpc
TH_CODE=/work/home/aclhl3hbth/EnzymeAgent/v43cTH
TH_PY="$TH_WS/venv_v44run/bin/python"
TH_BATCH="$TH_WS/batch/t_h_s5b_298_20261020r2"
TH_RUNS="$TH_WS/runs/t_h_s5b_298_20261020r2"
TH_RECORDS="$TH_WS/operations/t_h_approved_record_20261020"
export PYTHONPATH="$TH_CODE/src"
export PYTHONDONTWRITEBYTECODE=1
cd "$TH_CODE"
```

`TH_RECORDS` 由部署者预放四文件：两份原审批 JSON、原批准 TASK 快照、当前未改的 PREP，文件名与原 docs basename 一致。目录放在 operations 下，**不预创建 r2 批根**。`prepare` 会按原批准 JSON 校验两快照完整 SHA 后复制，不改原审批。

## 可重用执行链（每次接续先查状态）

统一入口：`scripts/hpc/th_operations.py`。调度状态在 `$TH_WS/operations/t_h_s5b_298_20261020r2.json`，含每阶段 job id、history 和提交前意图；其锁也在 operations，故 build 前不会污染新批根。

1. **先查，不重复提交**：读取上面操作状态的安全作业字段，然后对已记 job id 运行 `squeue -h -j JOB_ID -o '%i %T'`；作业离队后用 `sacct -n -X -j JOB_ID --format=JobIDRaw,JobName,State,ExitCode` 核终态。作业仍 pending/running 就保持安静，约 15 分钟后再查。未变状态无需用户通知。
2. **build**（预计约 66 分钟）：

   ```bash
   "$TH_PY" -B scripts/hpc/th_operations.py launch --phase build \
     --batch-root "$TH_BATCH" --runs-root "$TH_RUNS" --ws "$TH_WS" --code "$TH_CODE"
   ```

   `launch` 返回 job id 后存状态；已有活作业返回原 id，不新建；已有 manifest 不重 build；非空不完整根停报，不删除覆盖。**sbatch 前先落 pending_submission 意图**，断流或退出后未可靠记录 job id 时，后续入口停报，先查 `th-r2-build/run/score` 的 squeue/sacct，禁止盲重投。确证同参中断可 `--resume` 一次；连续失败停报。
3. **build 完成门**：sacct 必须 COMPLETED／Exit0；日志 `$TH_CODE/th_build_JOB_ID.out` 必须有 `TH-BUILD-PASS`；执行：

   ```bash
   "$TH_PY" -B scripts/hpc/chain13_gate.py build-gate --batch-root "$TH_BATCH"
   "$TH_PY" -B scripts/hpc/th_operations.py prepare \
     --batch-root "$TH_BATCH" --record-dir "$TH_RECORDS"
   ```

   `prepare` 在任何写前要求 manifest 和 build_identity 可读；只复制原批准件与快照，再自动执行新探针。探针入口也可独立重测：`th_operations.py probe --batch-root "$TH_BATCH"`。它只消费显式 r2 的 run_inputs.plan.pools，读取 **spec 顶层 template_remap.applied** 与 edits.add_atom，按通道／题汇总，不读 reference_graphs/金标、不发模型。输出 `$TH_BATCH/p2_face_measure.json`；旧 261/222/96 不当作新批分母，r2 数字以实测为准。
4. **run**：核新批诊断 policy-9/compiler-6/formnorm、build_identity 和上述旁件后：

   ```bash
   "$TH_PY" -B scripts/hpc/th_operations.py launch --phase run \
     --batch-root "$TH_BATCH" --runs-root "$TH_RUNS" --ws "$TH_WS" --code "$TH_CODE"
   ```

   作业内自动 smoke2→smoke10→full。**每段先 wrapper，再 T-H 专用 phase guard，再沿用 chain13_gate**。wrapper 非零也先保全／登记现场再退出，不因 `set -e` 短路。任何错误字段（含 worker 死亡占位 stderr_tail）出现 `unregistered_cx_class`，立即停；不扫描模型自由文本判断 CX。
5. **恢复类失败**：guard 先把原 case、完整 run（含日志/state/validation）、batch 配置和 gate 复制进 `$TH_BATCH/monitoring/QID/attemptN/`，再登记 `failure_register.json`。仅明确 recovery/resume/crash/worker_exit/worker_timeout 家族且无身份／完整性／预算等拒绝原因时，通过公共 `run_s5b_batch(qids=[QID])` **同参重投一次**：完整保全后只把 active failed case 移至同证据目录，原 runstate／driver 原样交现有 worker resume。retry_count 先落盘，heartbeat 不会再次重试；二败继续留证、登记、非零停 full／score，交 CC。身份／预算／完整性异常直接停；其它合法 failed 终态仅登记并保留分母，不加未知拒绝门；普通 completed 未命中不受影响。重试后重新汇总当前 smoke/full 执行域，避免单题汇总冒充全批。
6. **score**：run 作业完成，`TH-RUN-PASS` 和 `th_full_status.json.passed=true` 后：

   ```bash
   "$TH_PY" -B scripts/hpc/th_operations.py launch --phase score \
     --batch-root "$TH_BATCH" --runs-root "$TH_RUNS" --ws "$TH_WS" --code "$TH_CODE"
   ```

   `sbatch_th_score.sh` 先核全 qid 终态，再调用 `th_operations.py score`，顺序固定：**v1→三文件保存 .v1；显式 v3→保存 .v3；显式 v2→保存 .v2 并保留根文件为 headline**。三文件为 metrics.json、report.md、report_plain.md。额外输出 `criteria_v3_disclosure.json` 和 `th_score_complete.json`（三版／根产物 SHA、稳定科学字段对照、其他差异字段名）。只比较主指标、strict 相关主轴、criteria_v2、分桶、逐题判分行等稳定字段，不要求生成时间／路径等元数据相同；V3 必须披露档、strict_promotion=false、hit_at_1_effect=none、tautomer_promoted_nodes=[]。任何科学差异留证停交付，不抬分。已完成评分且 SHA 对齐则不重跑。

   **评分并非纯只读 API**：它固定覆盖批根三文件，还会 RW 打开逐 run SQLite 并执行既有 CREATE IF NOT EXISTS／commit；read_native_export 自身为只读。全部评分必须在 r2 最终封存之前完成；已封存批只消费已有产物，不原地补评分。
7. **拉回与交付**：仅拉 metrics 三版／根、reports 三版／根、V3 聚合披露、完整性清单、batch_report、P2 聚合和原批准 record 到本地 gitignored 镜像；不拉题卷、reference_graphs、逐题 run/state。模型 usage／金额缺数如实 unknown；按原 TASK §5 出双口径、兑现表、P2 转化、human_review 义务、<32% 桶回查。全部完成再写 `th_sealed.json` 并只读封存；出结果交 CC 后停 heartbeat。不 push。

## 异常与回传

分区拒绝、CX 再现、费用异常、连续失败、完整性错误或范围外要求：留现场→停后续→报 CC，不临场改科学源码、冻结参数或审批。无可靠 job id 的 pending_submission 不自行清除；核清真实调度状态后另行登记处置。每个实际阶段完成更新本操作补充的状态、最新重启移交 §2 和主 TODO 行 8；未变化时保持安静。源码／脚本变更必须先有审阅与锁定，跑中零改动。

## 本机合成验收

无真实题／金标／模型调用。独立临时夹具覆盖：CX（含死亡占位 stderr_tail）立即停且现场保全；同 qid 同参数恢复一次／二败停；身份错误不重试；未知 failed 只登记；wrapper 非零先留证；三评分顺序和三套输出／根 v2／V3 不抬分；P2 顶层 remap 计数；调度活作业不重复、提交前意图中断不盲重投；prepare 缺 build 不创建任何根目录。证据留 `docs/review_evidence/t_h_operations_2026-10-20/`（按惯例不随操作提交）。
