# T-I 实施准备报告（两臂版，2026-10-20）

> **题域标签：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本文件只描述操作脚本与
> 合成验收，不含任何真实成绩；298 与 dev 双向不外推。
>
> **状态：实施完成 + 本机合成验收 71 项通过；尚未真实发车。**
> 合成绿 ≠ 真实可跑：本报告未调用任何模型、未提交 sbatch、未连接 HPC、未读真实
> env/key、未碰封存批/题面/金标。
>
> **CC 2026-10-20 晚变更已落地：** Kimi 臂已按 CC 决定移除（成本原因），T-I 改为两臂
> **A=GLM-5.3-Flash（基线）**、**B=deepseek-v4.1-flash-1017（挑战臂）**；统计口径改为
> **单一主比较 B−A、不做多重校正**；5pp 阈=15/298=5.03pp 不变；M2 主判定 + M1 敏感性、
> A 同批重跑、两臂 no-cap 不变。
>
> **DeepSeek 模型 ID 已定 `deepseek-v4.1-flash-1017`，并已由主窗口/运维写入 HPC
> `llm_ds.env`（只改 `V43_LLM_MODEL` 行，base 仍 dashscope）。本代理未连 HPC，
> 未独立复核该行内容或 key；发车前只读核对模型名与 base host 即可。**

## 1. 文件清单与 SHA256

| 文件 | SHA256 | 说明 |
|---|---|---|
| `scripts/hpc/ti_operations.py` | `cfdabc01b48f5974638bc64541eda9b8e8325ec5e7624d0920d831482938a5b9` | 两臂操作入口；prepare/launch/score/seal/verify-identity/no-cap/arm-env |
| `scripts/hpc/ti_run_wrapper.py` | `0bf9ef489da3fb313e7bffb3a4509343dd7b6b5558f7877d45ba25a6b60504fb` | 单臂 run wrapper；环境/模型/身份前置检查 |
| `scripts/hpc/sbatch_ti_build.sh` | `dcbb49ca189812a7ebf8a9e3f0f3a77a7e7e4a44d8f916c83a1b6d6a674a866a` | 单臂 build 作业 |
| `scripts/hpc/sbatch_ti_run.sh` | `0db1dc4be8538650a233aab0d78c66de998c9b54d4e94460e56b1dc004325b1a` | 单臂 run 作业（smoke2→smoke10→full） |
| `scripts/hpc/sbatch_ti_score.sh` | `2d33ee3dd90cbf4140db53126f66ad4019d2ae137375177d1a0efe945d2539b5` | 单臂 score 作业（默认 v1+v2） |
| `scripts/hpc/ti_arm_config.json` | `858d00aa27a08c0e054a99180820cf1281fc98ac82a790f06cdf480a686626b0` | 两臂配置（schema `ti-arm-config-2`） |
| `docs/T_I_PREREG_2026-10-20.md` | `2e45d40721168a19016e1488539e76b40ba55020a2f15a9c8b108646b84921b3` | 两臂预注册（仍待签字） |
| `docs/TASK_T_I_LAUNCH_2026-10-20.md` | `1fc94b66bda5f14a2851e8324d4e9376916821e3cbc1df5c15511e7a6f7d192a` | 两臂任务书；§6/§7.2 已更新 |

两臂命名（`ti_arm_config.json`）：

| 臂 | 模型 ID | env | batch 根 | runs 根 | job 前缀 |
|---|---|---|---|---|---|
| A glm | `ZHIPU/GLM-5.3-Flash` | `llm.env` | `t_i_298_20261020_glm` | 同名 | `ti-glm` |
| B deepseek | `deepseek-v4.1-flash-1017` | `llm_ds.env` | `t_i_298_20261020_deepseek` | 同名 | `ti-deepseek` |

`batch_name` / `runs_name` / `job_prefix` / `env_file_basename` 四组两臂均无冲突；
`batch_tag=t-i-298-20261020` 两臂同值；`source_commit=c9c6c7a…`（D7 技术默认）。

## 2. 合成验收（71 项通过）

命令（零模型、零 HPC；夹具在系统 temp 目录）：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts/hpc python3 -B \
  docs/review_evidence/ti_prep_2026-10-20/synthetic_check.py
```

覆盖类别与结果：

| 类别 | 项数 | 结果 |
|---|---:|---|
| 两臂配置/路径零冲突/schema 2 | 7 | 全过 |
| env fail-closed（缺 env、旧名、错模型、无 key、无 base、温度键、600、TBD） | 10 | 全过；无静默回退 GLM |
| run_identity 模型 ID + prediction 块一致/漂移 | 3 | 全过 |
| no-cap schema/mode/marker/date/decision + 互斥 + 幂等 | 7 | 全过 |
| prepare（批准件/文本 SHA/P2/record/arm_config/预注册 SHA/两臂） | 6 | 全过 |
| D6 两臂身份门（manifest/fingerprint/逐题 sha/缺指纹/引用不符） | 4 | 全过 |
| sealed/immutable 拒写（ti_sealed 等 + probe/score/no-cap/launch） | 11 | 全过 |
| launch 幂等/防重/pending/重投一次/两臂 job 名/squeue 错误 | 10 | 全过 |
| score v1/v2 并列、根 v2、v3 可选、稳定字段差异、回执 SHA | 6 | 全过 |
| seal（未评分拒、444/555、二次 no-op、回执 SHA） | 4 | 全过 |
| bash score 脚本空数组（bash 3.2 + `set -u`） | 1 | 全过 |
| 静态：代码无 T-H 路径/旧 commit/旧批名；Docs 无 Kimi | 2 | 全过 |
| **合计** | **71** | **全过** |

证据：`docs/review_evidence/ti_prep_2026-10-20/02_synthetic_acceptance.txt`（全文）与
`02b_synthetic_summary.txt`（逐项清单）；夹具根见输出 JSON（每次运行不同）。

## 3. 验收中发现并修复的缺陷（均在 `ti_*` 白名单内）

| # | 缺陷 | 风险 | 修复 |
|---|---|---|---|
| 1 | `prepare --source-commit` 只写入 `record/ti_operations.json`，`arm_config.code_commit` 仍取 config 值 | 操作记录与实际 prepare commit 不一致 | `write_arm_config` 接收并记录实际 `source_commit`；与 config 不同时 run 前置 fail-closed |
| 2 | D6 `verify-identity` 在 `build_identity_fingerprint` 缺失/为空、`run_input_sha256` 为空时，两臂同为 `None`/空串会误判通过 | **身份门假绿** | `check_build_identity` 强制 fingerprint 为 64 hex、逐条 qid/sha 非空、qid 集合=注册序、manifest 引用指纹一致 |
| 3 | `require_env` 只查 model/key，不查 `V43_LLM_BASE_URL` | 不完整 env 到 worker 才逐题失败 | launch 前置强制 base URL 存在（只报布尔，不打印值） |
| 4 | `active_job` 对已滚出 squeue 的作业调用 `squeue -j` 收到 `Invalid job id` 时直接抛异常 | 同阶段 resume/幂等被误判为调度器故障 | 仅把 `Invalid job id`/`not found` 视为“不活跃”；其它 squeue 错误仍 fail-closed |
| 5 | `sbatch_ti_score.sh` 用 `"${EXTRA[@]}"` 展开空数组；bash <4.4 + `set -u` 会 `unbound variable` | 默认不跑 v3 时 score 作业起不来 | 改为非空 `SCORE_CMD` 数组 + 条件追加 `--include-v3`；本机 bash 3.2 实测通过 |
| 6 | `arm_config.json` 缺任务书 §4.3 要求的 `preregistration_sha256` | smoke 身份核对缺批准文本绑定 | prepare 写入该字段；run 前置与批根批准件 SHA 比对 |
| 7 | `verify_run_identity_models` 只核 `prediction.model_id` | request_params/timeout/prompt 漂移不被发现 | 前两个 run 的整个 `prediction` 块逐字比较；不一致停臂 |
| 8 | no-cap 只核 mode/schema/date/marker，未核 `user_decision_record` | 可能与冻结决定不一致 | 增加逐字校验 |
| 9 | `launch` 状态文件路径由 batch 名推导，忽略 config `operations_state` | 配置与状态路径可能漂移 | 改用 `paths["state_path"]`（配置驱动） |
| 10 | `sbatch_ti_*` 的 `eval "$(arm-env)"` 失败时 `eval ""` 返回 0，错误信息不清晰 | 观感/排障 | 先赋值并检查 arm-env 退出码，再 eval |
| 11 | 旧事故批名硬编码在 `mutable()` | 静态检查出现 T-H 批名 | 移到 config `immutable_batch_names`（数据项），代码零硬编码 |

`phase_guard` / `snapshot` / `case_failure` 与 T-H 对照：`case_failure` 完全相同；
`snapshot` 仅 `th_`→`ti_` 日志名与 `Path()` 强制转换；`phase_guard` 仅命名、锁名、
sealed marker 参数与缩进差异，恢复家族白名单/重试一次/二败停逻辑未改。
证据：`docs/review_evidence/ti_prep_2026-10-20/03_phase_guard_diff.txt`。

## 4. fail-closed 设计点（两臂）

1. **模型身份**：`expected_model_id` 必须非空且非 `TBD`；env 的 `V43_LLM_MODEL`
   必须逐字相同；DeepSeek 旧名 `deepseek-v4.1-flash` 会停，不会静默回退 GLM。
2. **env 完整性**：文件存在、权限 600、`V43_LLM_BASE_URL`/`V43_LLM_API_KEY` 存在
   （只报布尔）、`V43_LLM_REQUEST_PARAMS` 不得含 temperature/thinking 键。
3. **两臂区分**：batch/runs/env/state/job 名全部由 config 按臂解析；两臂不共享
   runs 根；`ti_sealed.json` 后 `mutable()` 拒绝任何写命令。
4. **D6 身份门**：两臂独立 build 后 `verify-identity` 比较 batch_tag、manifest SHA、
   fingerprint、逐题 `(qid, run_input_sha256)`；缺指纹/空 sha 直接停。
5. **发车防重**：提交前写 `pending_submission`；活跃作业不重复提交；同阶段结束作业
   需显式 `--resume`，且同参重投最多一次；`squeue` 状态未知时禁止盲重投。
6. **评分口径**：默认 v1+v2，根 headline=v2；`--include-v3` 才跑 v3 纯披露，
   v3/v2 稳定字段差异即停交付；回执 SHA 不符不封存。
7. **预算**：`budget_no_cap.json` 必须含 `budget_mode=no_monetary_cap_user_decision`
   + 日期 marker + `user_decision_record`；与 `budget_guard.json` 互斥。

## 5. 两臂发车命令示例

在 HPC 登录节点、仓库根目录执行（重活由 `launch` 提交 sbatch）：

```bash
TI_WS="$HOME/ppv1_hpc"
TI_CODE="$HOME/EnzymeAgent/v43cTH"
TI_PY="$TI_WS/venv_v44run/bin/python"
export PYTHONPATH="$TI_CODE/src" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
cd "$TI_CODE"

# 一条命令（逐臂循环）：
for arm in glm deepseek; do
  "$TI_PY" -B scripts/hpc/ti_operations.py launch --phase build \
    --arm "$arm" --ws "$TI_WS" --code "$TI_CODE"
done
"$TI_PY" -B scripts/hpc/ti_operations.py verify-identity --ws "$TI_WS"
for arm in glm deepseek; do
  "$TI_PY" -B scripts/hpc/ti_operations.py prepare --arm "$arm" \
    --ws "$TI_WS" --code "$TI_CODE" --source-commit c9c6c7a7ae02b46769add09fbc2536323ce8a985
done
for arm in glm deepseek; do
  "$TI_PY" -B scripts/hpc/ti_operations.py launch --phase run \
    --arm "$arm" --ws "$TI_WS" --code "$TI_CODE"
done
for arm in glm deepseek; do
  "$TI_PY" -B scripts/hpc/ti_operations.py launch --phase score \
    --arm "$arm" --ws "$TI_WS" --code "$TI_CODE"
done
for arm in glm deepseek; do
  "$TI_PY" -B scripts/hpc/ti_operations.py seal --arm "$arm" --ws "$TI_WS"
done
```

单臂最小示例（DeepSeek）：

```bash
"$TI_PY" -B scripts/hpc/ti_operations.py launch --phase run \
  --arm deepseek --ws "$TI_WS" --code "$TI_CODE"
```

## 6. 仍缺的发车事实 / 未验证项

按 CC 2026-10-20 晚口径，发车前置只剩 **Codex 代决签字/预注册确认 + 真实作业凭证**；
本代理另列运行面实核/评审项，均不改科学判据：

1. **预注册确认**：`approval_status=preregistration_confirmed`、`approved_at`、
   `approval_source`、预注册/任务书文本 SHA 仍待 CC 回填；本报告不能代签。
2. **真实作业凭证**：HPC 登录/分区权限、netcheck、`llm.env`/`llm_ds.env` key 可用性
   需在发车前实核。本代理未连接 HPC。
3. **DeepSeek env 定名**：按 CC/主窗口回报，HPC 已备份 `llm_ds.env` 并只改
   `V43_LLM_MODEL=deepseek-v4.1-flash-1017`（base 仍 dashscope）。**本代理未独立复核
   该行内容或 key**；发车前请只读核对模型名与 base host。
4. **`V43_LLM_REQUEST_PARAMS` 两臂逐字同值/兼容性**：当前脚本只拒绝温度/思考键，
   **未做两臂跨文件逐字比较**；需发车前只读预检（不打印值）。不兼容则停批交 CC。
5. **P2 期望值**：`prepare` 会写 `p2_face_measure.json`，但**不自动断言**任务书 §5.3
   的期望值（`specs_total=531` 等）；需操作者按任务书核对，不符即停。
6. **失败阈值硬停缺口**：`phase_guard` 对非恢复类 `failed` 只登记、不并入
   `unresolved_failures`；`chain13_gate.run-gate` 的 full 门只要求 pending=0。
   因此“smoke10 失败 >0 停批”“full 失败 >15 题停批”目前依赖人工监控，未由脚本硬停；
   已在任务书 §7.1 标注，交 Codex/CC 决定是否加门（不改判分语义）。
7. **脚本锁文件**：`docs/T_I_SCRIPT_LOCK_2026-10-20.json` 尚未生成；本报告与
   `SHA256SUMS` 已给出当前 SHA，Codex 审核定稿后再落锁文件。
8. **D6/D7/D8**：任务书 §7.2 已标为“主窗口技术默认，CC 可改”；若 CC 改 D6 为
   seed build + 拷贝，需重写 build 命令并保持同一身份判据。

## 7. 结论

- 两臂脚本已参数化，合成验收 71 项通过；T-H 恢复/评分安全语义未被改写。
- 未改 `src/` 科学代码、未改 T-H 脚本、未跑 sbatch/HPC、未调模型、未 push。
- **具备交 Codex 审核的条件**（实现/操作面）；
- **不具备直接真实发车条件**：预注册签字、真实作业凭证、request_params 预检、
  P2 核对与脚本锁文件仍未闭环。