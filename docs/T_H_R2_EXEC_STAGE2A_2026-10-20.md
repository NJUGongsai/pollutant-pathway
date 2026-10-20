# T-H r2 阶段 2a 执行报告（发 run → smoke2 → smoke10）

> 执行窗口 2026-10-20 11:10–11:40（北京时间）。依据
> `docs/T_H_R2_OPERATIONS_2026-10-20.md` §4/§5 与阶段 2a 任务书。
> 只读操作＋批根既有产物消费；未改 src/tests/scripts，未 score，未 push，
> 未读题卷/金标/`llm.env`/逐题 case 正文。题域：298＝RHEA 通用酶学／已见题（post-hoc）。

## 0. 结论

**STAGE2A = PASS。**

run 作业 `46958084` 一次提交成功；smoke2、smoke10 均
`passed=true / zero_cx=true / unresolved_failures=0 / wrapper_exit_code=0`；
`failure_register.json` 未生成（无任何失败，故无 `hard_stop_cx`）；
run 日志 `TH-RUN-FAIL` 与 `unregistered_cx_class` 命中均为 0。
full 段已于 11:36:53 自动开始，按任务书**不等完**，交阶段 2b 继续盯。

## 1. 时间线

| 时刻（北京） | 事件 |
|---|---|
| 11:10:52 | 发车前核 opsstate（仅 build 46954982）与 squeue（空），无 run 作业 |
| 11:10:56 | `launch --phase run` RC=0，job **46958084**（th-r2-run）PENDING |
| 11:10:59 | 作业开跑，节点 `a02r4n16`；smoke2 开始 |
| 11:21:57 | smoke2 状态落盘：2/2 completed，passed |
| 11:21:58 | smoke10 开始（复用 smoke2 的 2 题，共 10 题） |
| 11:36:53 | smoke10 状态落盘：10/10 completed，passed；full 开始 |
| 11:39:15 | `progress.json`：n_terminal=10、n_in_flight=8、n_pending=280、n_failed=0 |
| 11:40 | 阶段 2a 核验完成，报告退出（作业保持 RUNNING，full 继续） |

轮询：smoke2 每 120s 共 6 次（均在 45 分钟内出结果）；smoke10 每 120s
共 8 次（均在 60 分钟内出结果）。无重试、无改投。

## 2. run 作业

| 项 | 值 |
|---|---|
| job id | `46958084` |
| job name | `th-r2-run` |
| 状态（报告时） | RUNNING，Elapsed 28:05，节点 a02r4n16 |
| 提交方式 | `th_operations.py launch --phase run`（未手工 sbatch） |
| 排队 | 约 3 秒（PENDING→RUNNING） |

## 3. smoke2

`th_smoke2_status.json`（recorded_at 2026-10-20T03:21:57.452Z）：

| 字段 | 值 |
|---|---|
| `passed` | **true** |
| `zero_cx` | **true** |
| `unresolved_failures` | **0** |
| `checked` / wrapper rc | 2 / 0 |

日志：`[smoke2] completed=2 failed=0 pending=0`、`[smoke2] GATE-OK`。
`monitoring/` 目录未生成，`failure_register.json` 不存在 ⇒ 无 `hard_stop_cx`。

## 4. smoke10

`th_smoke10_status.json`（recorded_at 2026-10-20T03:36:53.021Z）：

| 字段 | 值 |
|---|---|
| `passed` | **true** |
| `zero_cx` | **true** |
| `unresolved_failures` | **0** |
| `checked` / wrapper rc | 10 / 0 |

日志：`[smoke10] completed=10 failed=0 pending=0`、`[smoke10] GATE-OK`。
`failure_register.json` 仍不存在 ⇒ 无 `hard_stop_cx`。

## 5. run 日志异常标记扫描

`$TH_CODE/th_run_46958084.out`（报告时 2014 字节）：

| 标记 | 命中数 |
|---|---:|
| `TH-RUN-FAIL` | 0 |
| `unregistered_cx_class` | 0 |

无命中，故不附上下文摘录。

## 6. full 段当前进度（不等完）

`$TH_BATCH/progress.json`（updated_at 2026-10-20T03:39:15Z）：

| 字段 | 值 |
|---|---:|
| `n_total` | 298 |
| `n_terminal` | 10（即 smoke2+smoke10 已完成的 qid，full 直接复用） |
| `n_in_flight` | 8 |
| `n_pending` | 280 |
| `n_failed` | 0 |

旁证：runs 根已有 18 个 qid 目录（10 个含 `native_result.json`，8 个为
full 新开在跑）；`batch_report.json` 当前为 smoke10 版（10 cases）。
full 的 `th_full_status.json` 尚未生成，属预期。

## 7. 异常与观察

| # | 事项 | 处置 |
|---|---|---|
| 1 | 无阻塞异常 | — |
| 2 | `batch_report` 中 completed case 的 `stop_reason=budget_limit` | 既有正常终止口径（search/调用预算触顶），非失败；登记供阶段 2b 参考 |
| 3 | 远端 shell 的 perl locale 警告 | 仅提示性 stderr，不影响任何命令 RC |
| 4 | 部署目录 `$TH_CODE` 无 `.git` | 部署副本形态，build_identity 已由阶段 1 核过；非本阶段异常 |

红线遵守：未改 src/tests/scripts；未 score；未 push；未读题卷/金标/
`llm.env`/逐题 case 正文；未删除/覆盖任何批根或旧批产物。

## 8. 证据目录

`docs/review_evidence/t_h_r2_stage2a_2026-10-20/`

| 文件 | 内容 |
|---|---|
| `01_run_launch.txt` | 发车前状态、launch 输出 RC=0、job id、squeue |
| `02_smoke2_poll.log` | smoke2 每 120s 轮询记录（含 STATE/FAILREG） |
| `03_smoke2_verify.txt` | smoke2 状态 JSON、failure_register 缺失、日志标记、作业状态 |
| `04_smoke10_poll.log` | smoke10 每 120s 轮询记录 |
| `05_smoke10_verify.txt` | smoke10 状态 JSON、日志标记、full 起始行、full 进度计数 |
| `06_full_progress.txt` | progress.json、batch_report 头部、runs 目录计数 |
| `07_opsstate_run.txt` | 调度状态：run 作业 46958084 已可靠落账 |
| `SHA256SUMS` | 本目录证据文件哈希 |

## 9. 交接（阶段 2b）

1. 继续盯同一作业 `46958084`，终态门：sacct COMPLETED 0:0、日志出现
   `TH-RUN-PASS`、`th_full_status.json.passed=true`；
2. 每轮检查 `monitoring/failure_register.json`：任一 `hard_stop_cx` 立即停报，
   完整现场已在批根 monitoring；
3. full 期间按操作书 §5 处理恢复类失败（保全→登记→同参重投一次），
   二败或身份/预算/完整性异常直接停报 CC；
4. 完成后再进 score（操作书 §6），本阶段不启动。