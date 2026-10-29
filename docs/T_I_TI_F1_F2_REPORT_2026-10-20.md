# T-I TI-F1/TI-F2 回修报告（2026-10-20）

> **题域标签：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只含操作脚本与
> 本机合成正负控，不含任何真实成绩、真实调用、真实 HPC 读数；298 与 dev 双向不外推。
>
> **状态：TI-F1、TI-F2 已实施并有本机正负控通过；尚未真实发车，未过 Codex 固定面复核。**
> 本代理未连接 HPC、未提交作业、未调用模型、未读真实 env/key、未碰金标/题面/封存 run、未 push。
> 合成绿 ≠ 真实可跑；本报告不宣布 GO。

## 1. 改动范围与身份

| 项 | 值 |
|---|---|
| 实际 HEAD | `c9c6c7a7ae02b46769add09fbc2536323ce8a985` |
| 科学源码 diff | `src/` 零差异（`git diff --stat -- src/` 为空） |
| 改动脚本 | `scripts/hpc/ti_operations.py`、`ti_run_wrapper.py`、`sbatch_ti_run.sh`、`sbatch_ti_score.sh`、`ti_arm_config.json`；新增 `sbatch_ti_monitor.sh` |
| 未改共享脚本 | `chain13_gate.py`、`chain13_run_wrapper.py` 原样（T-H/chain13 语义不变；T-I run gate 改由 `ti_operations.py run-gate` 执行） |
| 未改 | `src/`、T-H 脚本、P0b worktree、评分/prompt/模型/分母/证据卡/池检索排序 |
| 脚本锁 | `docs/T_I_SCRIPT_LOCK_2026-10-20.json` 已重算，14 文件全匹配、`missing=[]`，锁 SHA `1ed4f278…5528d13d0` |
| 批准包 | `docs/T_I_APPROVAL_PACKAGE_2026-10-20/`（批准 JSON + 四份原字节快照 + `SHA256SUMS`） |

## 2. TI-F1：监控/双臂阶段硬停

### 2.1 阈值落位（`scripts/hpc/ti_operations.py`，按唯一 qid 计数）

| 阶段/信号 | 冻结阈值（`MONITORING_THRESHOLDS`，第 49 行） | 执行位置 |
|---|---|---|
| smoke2 | ≥1 题 completed **且 `model_calls>0`**；所检 2 题均终态；模型/`prediction` 身份符合冻结；usage 可解析；无 fatal | `evaluate_stage`（第 638 行）label=smoke2；`verify_run_identity_models` |
| **smoke10** | **非豁免 `failed>0`，或未登记结构性零调用 `>0`，或 pending>0** ⇒ 停该臂并停另一臂，不进 full | `evaluate_stage` label=smoke10；`barrier_full`（第 986 行） |
| **full** | **非模型内容运行失败 `>15`，第 16 个失败 qid 起停两臂**；pending=0；fatal 立即停 | `evaluate_stage` label=full |
| 致命信号 | auth/权限/欠费/配额不可用；模型/身份/完整性/no-cap marker 错误；未登记 CX；连续 2 个不同 qid 的限流/传输故障未恢复 | `classify_case`（第 549 行）fatal / `max_consecutive_outage` |
| 恢复 | 仅原 prediction_recovery 白名单、同题同参一次、先保全；二败停 | `phase_guard`（第 1513 行）`retry_count` / `recovery_second_failure` |
| token/金额 | **无 token/金额硬停**；超规划带只告警登记；金额 unknown 不估造 | `token_projection`（第 794 行，`action=warn_only`） |

失败分类保留：`raw failed`、`n_run_failures`、`n_content_failures`、
`n_structural_zero_calls`、`n_unregistered_zero_calls`、`n_fatal`、
`n_completed_run_errors`、`pending_qids`、`run_failure_qids`、`max_consecutive_outage`。
unknown/坏 case 一律按运行面失败计至查清；已知 NC-9 只在
`ProductionContractError / cosubstrate_copy_in_expectation`、`counts.events=0`、
`stop_reason` 在场时豁免。

### 2.2 两臂协调与可执行停点

- `barrier_full`：两臂 smoke10 都写入并通过回执后，才写 `barrier_full_<arm>.json`；
  任一臂未过则超时写 `stop.json`，两臂都不得进入 full。
- `write_stop`（第 876 行）：首个写入者生效、不覆盖；停点落
  `coordination_dir/stop.json`；`phase`/`launch`/`ti_run_wrapper`/`stop-check` 均 fail-closed。
- `monitor`（第 2084 行）+ `sbatch_ti_monitor.sh`：每 900 秒（15 分钟）巡检两臂，
  单协调者 flock；越线自动写停点并（可执行时）`scancel` 两臂 run 作业。
- `halt --cancel`：手工急停路径；`stop-check` 供各阶段前阻断。
- `sbatch_ti_run.sh`：smoke2→smoke10→barrier→full；任一阶段前查停点；
  `phase` 与 `run-gate` 双重复核，阶段末再验计数与 `cases_digest`。
- `score_all`：full 门回执必须 `schema=ti-stage-gate-1`、`cases_digest` 与现存 case 一致，
  否则拒绝评分。

## 3. TI-F2：批准包首消费校验

### 3.1 批准包字段（`docs/T_I_APPROVAL_PACKAGE_2026-10-20/preregistration_approval.json`）

| 字段 | 实际值 |
|---|---|
| `approval_status` | `preregistration_confirmed` |
| `approval_basis` | `原预注册+任务书+本终审增补` |
| `approval_source_kind` | `codex_delegated_cc_shijie` |
| `approval_source` | `Codex 代 CC/师姐（依据 CC 2026-10-20 会话授权：需我/师姐裁决的由 Codex 代为裁决，Codex 的裁决即为最终裁决）` |
| `approval_authorization_chain` | CC 2026-10-20 授权 → Codex 代 CC/师姐终审 → 终审报告决议 `2026-10-20T15:49:53Z` |
| `approved_at` | `2026-10-20T15:49:53Z`（终审决议时间） |
| `preregistration_id` | `prereg-t-i-298-2026-10-20` |
| `budget_mode` / `user_decision_date` | `no_monetary_cap_user_decision` / `2026-10-20` |
| `no_cap_ack` | `true` |
| `cost_cap_cny` | `null` |
| `preregistration_docs` | `prereg`、`task`、`final_review`、`script_lock` 四键，各带仓库相对 path + 64 位 SHA |
| `preregistration_text_sha256` | `2e45d407…b84921b3`（预注册文本快照 SHA，**不是批准 JSON 哈希**） |
| 批准 JSON 自身 SHA | `1766734b…07fa6b1` |

四份快照（原字节）：`T_I_PREREG_2026-10-20.md`、`TASK_T_I_LAUNCH_2026-10-20.md`、
`T_I_CODEX_FINAL_REVIEW_2026-10-20.md`、`T_I_SCRIPT_LOCK_2026-10-20.json`。
源文件保持历史草案；生效批准=完整文书包。

### 3.2 校验入口（共用）

- `validate_approval_package`（第 1126 行）：四文书存在、basename/路径对应、SHA 格式与实值、
  代决来源/授权链、`approved_at`、`no_cap_ack=true`、文本 SHA 与批准 JSON SHA 分列、
  脚本锁 schema/source_commit/arms/missing、锁内 prereg/task SHA 互证。
- `prepare`（第 1395 行）：先校验完整包，再复制四份快照、批准 JSON、写
  `record/approval_manifest.json` 与 `arm_config`（`preregistration_text_sha256` /
  `approval_package_sha256` 分列）。
- `require_arm_config`（第 1329 行）/ `_launch_preconditions(run)` / `ti_run_wrapper`：
  首付费消费前 `validate_batch_approval`（第 1261 行）复核批根副本，并与源记录目录逐件互证；
  缺件、SHA 不符、`no_cap_ack=false`、来源不是 Codex 代决链 ⇒ 非零退出，不提交 sbatch。
- `approval-package` 命令：生成/校验规范包（不覆盖既有不同内容）。

## 4. 正负控（本机合成，零模型/零 HPC）

| 套件 | 项数 | 结果 | 覆盖 |
|---|---:|---|---|
| `synthetic_check_f1f2.py` | **50** | **50/50 通过** | 阈值冻结、分类、smoke2 身份/usage、smoke10 failed/未登记零调用/pending/内容 failed/completed-run_error、full 15 vs 16、内容 16 只登记、NC-9 正控、连续 vs 非连续传输、fatal、pending、token 超规划只告警、回执 digest/计数、停点首写、barrier 正/超时、monitor full16、monitor flock、halt、恢复一次/二败、批准包正控与 9 类负控、prepare/首消费拒绝 |
| `public_chain_f1f2.py` | **13** | **13/13 通过** | 实际 sbatch→wrapper→phase→run-gate→barrier；正控 completed/NC-9/full15/content16；负控 smoke10 1 failed/未登记零调用/pending/full16/CX/quota/连续 transport2/批准包缺件/`no_cap_ack=false` |
| **合计** | **63** | **63/63** | 合成操作控制流，不是真实模型或科学结论 |

关键读数：

- smoke10 1 个 failed：只执行 smoke2+smoke10（limits `[2,10]`），退出 1，`stop.reason=stage_gate`；
- full 16 个失败：执行到 full（limits `[2,10,null]`），`full_passed=false`，
  `first_over_threshold_qid=q015`，`stop.reason=stage_gate`；
- CX/quota：smoke2 内即停（limits `[2]`），`stop.reason=fatal_signal`；
- 批准包缺件/`no_cap_ack=false`：wrapper 在首付费调用前拒绝，`synthetic_calls=[]`；
- token 外推 29.8M > 规划带：`over_plan_band=true`、`action=warn_only`，阶段仍通过。

证据：`docs/review_evidence/ti_f1f2_2026-10-20/`（`unit_controls_full.txt`、
`unit_controls_summary.json`、`public_chain_full.txt`、`public_chain_results/`、
`static_checks.txt`、`SHA256SUMS`）。

## 5. 脚本锁（重新计 SHA）

`docs/T_I_SCRIPT_LOCK_2026-10-20.json`（锁 SHA `1ed4f278…5528d13d0`）：

| 文件 | SHA256 |
|---|---|
| `scripts/hpc/ti_operations.py` | `4c43578d4d50b3a4301e9872f06689e13af90fb83abdfcaaf8157642b1890daa` |
| `scripts/hpc/ti_run_wrapper.py` | `1aaf9eaa487edf5b567ee40e207b8f2714114b097628fa9205e5e7602737c757` |
| `scripts/hpc/sbatch_ti_run.sh` | `3db2b3d9bcf141b6eedad274539e83587402d7ea7c55417bc162911d10827e72` |
| `scripts/hpc/sbatch_ti_score.sh` | `90b640398f66d58be129329ffe468f129e28778e91ad547bd86f80f405deb1a5` |
| `scripts/hpc/sbatch_ti_monitor.sh` | `50aeed16feef975c8be5e0c2716c0efd3286e506464063a29a72ac113a4e3c12` |
| `scripts/hpc/sbatch_ti_build.sh` | `dcbb49ca189812a7ebf8a9e3f0f3a77a7e7e4a44d8f916c83a1b6d6a674a866a` |
| `scripts/hpc/ti_arm_config.json` | `99ac34bb0f3e7d2228b5c9f64a3ec44b02b6a874e19b07969f7bcbcc2817965d` |
| `scripts/hpc/chain13_gate.py` | `59b5fbc6…357ed84e`（未改） |
| `scripts/hpc/chain13_run_wrapper.py` | `d56597fc…11cb445`（未改） |
| 两科学源码 + 三文档 | 见锁文件（`src` 两文件与旧锁相同） |

## 6. 仍缺的 C0–C8 事实（不能由本报告替代）

| 条件 | 当前状态 |
|---|---|
| C0 有效批准包 | 本地完整包已生成并自校验；**HPC 记录目录部署 + 外部 SHA 清单绑定 + Codex 复核**未完成 |
| C1 两阻塞关闭及部署锁定 | TI-F1/F2 已实施、锁已重算；**Codex 复核未过**；HPC 逐件同值部署未核 |
| C2 真实作业能力/净环境 | 未核（无 HPC 登录；凭证布尔、分区/路径/磁盘/flock、有效 `V43_LLM_*` 均未知） |
| C3 netcheck | 未跑（无真实作业号/`NETCHECK-PASS`） |
| C4 两臂文件与有效请求预检 | 未读真实 env；`V43_LLM_REQUEST_PARAMS` 逐字同值、无 `max_tokens`/temperature、timeout/重试有效值均待现场核 |
| C5 两臂最小真实调用 | 未跑（付费调用；usage/model 身份待实核） |
| C6 同题集与两臂 build 身份 | 未跑真实 build；D6 指纹/逐题输入身份无现场读数 |
| C7 prepare 与 P2-face 探针 | 未在真实批跑；`files=298`、`specs_total=531`、`remap_applied=242` 等期望值无现场读数 |
| C8 协调/阶段放行/回传 | 代码与脚本已备；真实两臂 smoke2/smoke10 回执、monitor 作业号、回传责任尚未落现场 |

## 7. 边界与结论

- 本报告不认证真实 HPC 环境、真实模型行为、真实失败频率或任何科学收益；
  合成替身只证明脚本/阶段门/协调控制流。
- 未修改 `src/` 科学代码、T-H 脚本、P0b worktree；未跑 sbatch/HPC、未调模型、
  未读 key/金标/题面/封存 run；未 push。
- **具备交 Codex 按固定面复核的条件**（TI-F1/TI-F2 + 正负控 + 锁 + 批准包）；
  **不具备发车条件**：Codex 复核关闭与 C0–C8 全绿前，仍为 NO-GO。

## 8. 证据路径

- 本报告：`docs/T_I_TI_F1_F2_REPORT_2026-10-20.md`
- 合成正负控：`docs/review_evidence/ti_f1f2_2026-10-20/`
- 脚本锁：`docs/T_I_SCRIPT_LOCK_2026-10-20.json`
- 批准包：`docs/T_I_APPROVAL_PACKAGE_2026-10-20/`
- 任务书 §7.1/§7.2：`docs/TASK_T_I_LAUNCH_2026-10-20.md`