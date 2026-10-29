# 任务书 — T-I B3 新批重建与发车准备（2026-10-21，可移交）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本任务书只做工程准备，不产生成绩。
> **当前执行者**：主窗口子代理（B3 代理）。**本文件用于移交其他模型/操作者接手。**
> **状态（2026-10-21 14:5x 北京）**：两臂 build **正在跑**——
> GLM `47061667`、DeepSeek `47061671`，已 21 分钟（build 约 1h/臂）。
> **B3 批根**：`~/ppv1_hpc/batch/t_i_298_20261021b3_{glm,deepseek}`；tag=`t-i-298-20261021b3`。

## 0. 一句话

B2 被一个越权子代理**直接 `sbatch sbatch_ti_run.sh`**（绕过 `launch`）污染，GLM runs 根残留
`run_already_exists`。B2 与 20261020 原批**全部只读保全**；现在建 **B3 新批**重走
“netcheck → 新 tag/根 → 重锁/重绑 → C2–C5 → 两臂 build → 身份 → prepare”，
**停在 run 之前**，run 由主窗口/CC 发。

## 1. 接管前必做（防二次撞车）

1. 查队列：`squeue -u $USER -h -o "%.10i %.18j %.8T %.10M"`。
   - 若 `ti-glm-build`/`ti-deepseek-build`（B3）仍 RUNNING ⇒ **等它结束**，不要重复提交。
   - 若 B3 代理仍在运行且你要接管 ⇒ 先让主窗口停掉该子代理，避免两个执行者同时写同一批根。
2. 查 B3 opsstate：
   `cat ~/ppv1_hpc/operations/t_i_298_20261021b3_glm.json`、
   `..._deepseek.json`；看 `jobs` 里最新 phase/job_id。
3. 查 B3 批根存在与内容：`ls ~/ppv1_hpc/batch/t_i_298_20261021b3_{glm,deepseek}`。
4. **绝对不许**再直接 `sbatch scripts/hpc/sbatch_ti_run.sh`；所有 build/run/score 只走
   `ti_operations.py launch`（netcheck 是唯一允许直接 sbatch 的共享脚本）。

## 2. 环境（HPC 登录节点）

```bash
KEY=/Volumes/CC/Enzyme_Agent/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt
ssh -i "$KEY" -p 65091 aclhl3hbth@wuzh02.hpccube.com
cd $HOME/EnzymeAgent/v43cTH
export TI_WS=$HOME/ppv1_hpc
export TI_CODE=$HOME/EnzymeAgent/v43cTH
export TI_PY=$TI_WS/venv_v44run/bin/python
export PYTHONPATH=$TI_CODE/src
export PYTHONDONTWRITEBYTECODE=1
```

## 3. 从当前状态续跑（推荐，B3 代理已做完 C3/配置/重锁/C2–C5，builds 在跑）

### 3.1 等两臂 build
```bash
squeue -j 47061667,47061671 -h -o "%i %T %M"
sacct -j 47061667,47061671 -n -X --format=JobID,JobName,State,ExitCode,Elapsed
```
判据：两臂 `COMPLETED 0:0`；日志 `~/EnzymeAgent/v43cTH/ti_build_<job>.out` 含
`TI-BUILD-PASS` + `BUILD-GATE-OK`。任一失败 ⇒ 停，拉日志尾部，报。

### 3.2 两臂身份门
```bash
"$TI_PY" -B scripts/hpc/ti_operations.py verify-identity --arm glm \
  --ws "$TI_WS" --code "$TI_CODE" --config "$TI_CODE/scripts/hpc/ti_arm_config.json"
"$TI_PY" -B scripts/hpc/ti_operations.py verify-identity --arm deepseek \
  --ws "$TI_WS" --code "$TI_CODE" --config "$TI_CODE/scripts/hpc/ti_arm_config.json"
```
判据：两臂 `TI-BUILD-IDENTITY-PASS`；fingerprint/manifest/298 条
`(qid,run_input_sha256)` **逐字相同**。新 fingerprint 应与 B2 不同（B3 新 tag 的预期），
但两臂必须相同；科学源码 `s5b_compiler.py=f917762b…`、`evaluation.py=37c09231…` 不变。

### 3.3 两臂 prepare + P2-face
```bash
"$TI_PY" -B scripts/hpc/ti_operations.py prepare --arm glm \
  --ws "$TI_WS" --code "$TI_CODE" --config "$TI_CODE/scripts/hpc/ti_arm_config.json"
"$TI_PY" -B scripts/hpc/ti_operations.py prepare --arm deepseek \
  --ws "$TI_WS" --code "$TI_CODE" --config "$TI_CODE/scripts/hpc/ti_arm_config.json"
```
判据（两臂逐项相同且符合）：
`files=298`、`specs_total=531`、`remap_applied=242`、`remap_add_atom_ge1=205`、
`remap_add_atom_ge2=78`、`questions_remap=151`、`questions_with_add=134`、
`questions_with_multi_add=65`。不符 ⇒ 停，不改探针口径。

### 3.4 交回
prepare/P2-face 全绿后**停**，把两臂指纹、prepare 产物、P2-face 表交主窗口；
run 由主窗口/CC 发（两条 `launch --phase run --arm glm|deepseek`）。

## 4. 从零重走（仅当 B3 代理已死/批根不完整）

1. **C3 netcheck**：
   `WS=$TI_WS sbatch --parsable $TI_CODE/scripts/hpc/sbatch_th_netcheck.sh`；等
   `COMPLETED 0:0` + `NETCHECK-PASS`。
2. **B3 配置**：`ti_arm_config.json` 的 `batch_tag=t-i-298-20261021b3`；批根/运行根
   `t_i_298_20261021b3_{glm,deepseek}`；协调目录 `t_i_coordination_t-i-298-20261021b3`；
   `immutable_batch_names` 必须含 **B2 两根**（`t_i_298_20261021b2_*`）与
   **20261020 两根**（`t_i_298_20261020_*`）。
3. **重锁**：重算 `docs/T_I_SCRIPT_LOCK_2026-10-20.json` 的 14 件 SHA（预期仅 config 变）；
   记录新锁 SHA。
4. **重绑批准包**：四文书原字节不变；绑定新锁；新增 `b3_rebatch` 说明（原因=B2 越权污染、
   B2/原批 100% 保全）；保留 `approval_basis`/`source_kind=codex_delegated_cc_shijie`/
   `approved_at=2026-10-20T15:49:53Z`/`no_cap_ack=true`；**不伪填 CC 本人**；
   同步 `~/ppv1_hpc/operations/t_i_approved_record_20261020/` 并核 SHA。
5. **C2**：两 env 600；作业环境无 `V43_LLM_*` 覆盖（只报变量名）；分区/路径/磁盘/flock。
6. **C4**：`arm-env` 两臂；`ZHIPU/GLM-5.3-Flash`、`deepseek-v4.1-flash-1017`；base 均
   dashscope；`REQUEST_PARAMS` 同值；无 temperature/max_tokens/禁用键。
7. **C5**（付费 2 次）：按任务书 §4.2 骨架，两臂各 1 次最小调用；记录
   `~/ppv1_hpc/operations/preflight_calls.json`（臂/模型/tokens/耗时/金额 unknown）。
   任一失败 ⇒ 停两臂。
8. **两臂 build**（`launch --phase build --arm glm|deepseek`）→ 3.2/3.3。
9. **不 run/score**。

## 5. 红线

1. **不许直接 sbatch `sbatch_ti_run.sh`**；run 只能 `launch --phase run`（防二次撞车）。
2. B2/20261020 原批**只读**；不改其 cases/runs/stop；不写旧根。
3. 不改 `src/` 科学源码/判据/池/检索/排序/评分；不改 T-H/T-I 既有证据。
4. 不读/打印 key、金标、题面、`reference_graphs`、`llm.env` 值；不输出 SMILES/结构正文。
5. 不 push；不封存 B3（封存留给主窗口）。
6. 任何 false/unknown ⇒ 停报，不自行处置、不重试付费调用。

## 6. 回传（≤20 行）

两臂 build job/终态/耗时；两臂 fingerprint/manifest/298 条是否逐字相同；prepare 是否成功；
P2-face 八项；B2/原批是否零触碰；发车条件（run 前置）是否满足；任何异常原文。