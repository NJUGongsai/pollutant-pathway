# T-H r2 阶段 2b 执行报告（full 段跑到终态并核验收尾）

> 执行窗口 2026-10-20 11:39–15:15（北京时间）。依据
> `docs/T_H_R2_OPERATIONS_2026-10-20.md` §5 与阶段 2b 任务书。
> 只读盯跑与产物消费；未改 src/tests/scripts，未 score，未 push，未重投/杀作业，
> 未读题卷/金标/`llm.env`/逐题 case 正文。题域：298＝RHEA 通用酶学／已见题（post-hoc）。

## 0. 结论

**STAGE2B = PASS。**

作业 `46958084`（th-r2-run）终态 **COMPLETED 0:0**，Elapsed 03:52:23；
full 段门禁全绿：`th_full_status.json` 为 `passed=true / zero_cx=true /
unresolved_failures=0 / wrapper_exit_code=0`（checked=298），日志出现
`TH-RUN-PASS`，`progress.json` 为 terminal=298 / failed=0，
`batch_report.json` 为 n_completed=298 / n_failed=0 / failed_qids=[]。

`failure_register.json` 存在 2 条登记，**无 `hard_stop_cx`**；2 条均为
`last_status=other_failed_terminal_registered`、`failure_kind=null`、
`retry_count=0`、`last_phase=full`。按任务书停点判据（failed 计数>0 且
guard `passed=false`）未触发 STOP；但该 2 条与 batch_report 的
“completed / model_calls=0”并存，属需主窗口复核的观察项，详见 §6。

异常标记扫描：`TH-RUN-FAIL`=0、`unregistered_cx_class`=0、`Traceback`=0、
`hard_stop_cx`=0。completed=298；batch any-failed=0；failure_register
登记失败=2（分母仍为 298，未剔题）。

## 1. 时间线

| 时刻（北京） | 事件 |
|---|---|
| 11:10:56 | 作业提交；11:10:58 开跑，节点 `a02r4n16` |
| 11:36:53 | smoke10 门禁通过，full 段开始（`[full] @ 03:36:53Z`） |
| 11:39:15 | 阶段 2a 交接点：terminal=10、in_flight=8、pending=280、failed=0 |
| 11:42–15:01 | 约每 10 分钟轮询一次：squeue、progress、日志标记、failure_register |
| 15:01:56 | 最后一个 case 仍在跑：terminal=297、in_flight=1 |
| 15:03:17 | `progress.json` 终态：terminal=298、in_flight=0、pending=0、failed=0 |
| 15:03:19.86 / 15:03:20.16 | failure_register 2 条登记落盘（见 §5） |
| 15:03:20.20 | `th_full_status.json` 落盘：passed=true |
| 15:03:20 | full 门禁通过：`[full] completed=298 failed=0`、`GATE-OK`、`TH-RUN-PASS` |
| 15:03:21 | 作业结束（sacct End），COMPLETED 0:0 |

耗时：full 段 11:36:53→15:03:20 约 **3h26m27s**（batch `wall_clock_s=12383.2`，
即 3h26m23.2s）；作业总 Elapsed **03:52:23**（含 smoke2/smoke10）。
轮询 25 次有效读数，序列见证据 `18_poll_series.txt`；05:24 前后一次
操作侧 SSH 调用因 sleep+ssh 超过 600s 工具时限未取到数据（无写入、无影响），
05:32 起恢复正常轮询。8 小时上限未触及。

## 2. 终态核验（任务书门禁逐项）

| 检查项 | 要求 | 实测 | 结果 |
|---|---|---|---|
| sacct 主作业 | COMPLETED 0:0 | `46958084 th-r2-run COMPLETED 0:0 03:52:23` | PASS |
| sacct 子步 | — | `.batch`、`.extern` 均 COMPLETED 0:0 | PASS |
| squeue | 已离队 | `Invalid job id specified`（无该作业） | PASS |
| 日志 | 含 `TH-RUN-PASS` | 第 16 行 `TH-RUN-PASS`（1 次） | PASS |
| th_full_status | passed/zero_cx/unresolved 三项 | `true / true / 0`（checked=298，rc=0） | PASS |
| progress | terminal=298、failed=0 | `n_terminal=298, n_failed=0, n_in_flight=0, n_pending=0` | PASS |
| 失败标记 | 无 TH-RUN-FAIL / unregistered_cx_class | 均为 0；Traceback=0 | PASS |
| failure_register | 无 hard_stop_cx | 0；但存在 2 条 other 登记（见 §5） | PASS（附观察项） |

## 3. progress.json 四数（终态）

`updated_at = 2026-10-20T07:03:17Z`（= 15:03:17 北京）：

| 字段 | 值 |
|---|---:|
| `n_total` | 298 |
| `n_terminal` | **298** |
| `n_in_flight` | 0 |
| `n_pending` | 0 |
| `n_failed` | **0** |

`elapsed_s = 12382.5`。

## 4. batch_report.json 汇总

`generated_at = 2026-10-20T07:03:20Z`：

| 项 | 值 |
|---|---|
| n_total / n_completed / n_failed / n_pending | 298 / **298** / **0** / 0 |
| failed_qids | `[]` |
| skipped_already_terminal | 10（smoke2+smoke10 复用） |
| case status 分布 | completed=298 |
| failure_kind 分布 | 空=298 |
| stop_reason 分布 | budget_limit=298（既有正常终止口径） |
| model_calls 分布 | 1 次=294、2 次=2、0 次=2 |
| gate 计数器 | total_requests=298、429=0、forbidden=0、peak_in_flight=8、stopped=null |
| wall_clock_s / worker_timeout_s | 12383.2 / 0.0 |
| usage | input 821,107；output 5,894,306；total 6,715,413；missing_calls=0 |
| 费用 | `cost_status=no_snapshot`、`cost_known_cny=null`（无金额快照，不报金额） |

`model_calls=2` 的 2 题（重试后 completed，未进 failure_register）：
`RXNG_20b83d4f…`、`RXNG_80f2f3ae…`。

## 5. failure_register 摘要

文件存在（707 字节），共 **2 条**，`hard_stop_cx` 命中 **0**。

| qid（前缀） | last_phase | last_status（失败 kind） | retry | batch status | model_calls |
|---|---|---|---|---:|---|
| `RXNG_7a886593dd026a4573…` | full | `other_failed_terminal_registered`（`failure_kind=null`） | 0 | completed | 0 |
| `RXNG_ed3d70729ea7c22061…` | full | `other_failed_terminal_registered`（`failure_kind=null`） | 0 | completed | 0 |

两条登记的 `evidence.json` 均注明“完整现场在本目录；不删改 runstate/driver；
不是 flake 放行”，recorded_at 分别为 15:03:19.86 / 15:03:20.16（北京）。
full 门禁的 `unresolved_failures=0` 表明 guard 未将其计为 unresolved，
故不触发本阶段 STOP；但其在 batch_report 中呈 completed 且零模型调用，
建议评分前由主窗口复核（§6 第 1 条）。

## 6. 异常与观察

| # | 事项 | 事实与处置 |
|---|---|---|
| 1 | **2 题零模型调用且登记失败** | 上述 2 条 register 与 2 个 `model_calls=0` 的 completed case 一一对应（qid 集合完全相同）。runs 根 298 个 run_id 目录均有 `native_result.json`，其中 296 个有 `s5b_real_calls.jsonl`，恰好这 2 个没有；其 `native_result.json` 为 11,397 字节（对照重试题 119,441 字节）。未读 case 正文/native_result 内容。门禁 passed=true、failed=0，按任务书不停；建议评分前复核这 2 题是否应按失败/abstain 处理（分母仍为 298）。 |
| 2 | 2 题有模型重试 | `model_calls=2`，最终 completed，未进 register；gate 429=0、forbidden=0。 |
| 3 | 全批 `stop_reason=budget_limit` | 既有正常终止口径（search/调用预算触顶），非失败；与阶段 2a 观察一致。 |
| 4 | 操作侧轮询超时 1 次 | 05:24 前后 sleep+ssh 超过 600s 工具时限，无远端写入、未取到数据；05:32 恢复。后台 monitor 约 50 分钟后被工具侧停止，改为主窗口手工 ~10 分钟轮询；均不影响作业。 |
| 5 | 远端 shell perl locale 警告 | 仅 stderr 提示，不影响命令 RC。 |
| 6 | 费用 | `cost_status=no_snapshot`；本阶段无金额可报，token 用量见 §4（题域 298）。 |

红线遵守：只读；未 score；未 push；未改 src/tests/scripts；未读题卷/金标/
`llm.env`/逐题 case 正文；未杀作业、未重投；未改批根产物。

## 7. 证据目录

`docs/review_evidence/t_h_r2_stage2b_2026-10-20/`

| 文件 | 内容 |
|---|---|
| `01_progress.json` | 远端终态 progress.json 原件 |
| `02_th_full_status.json` | full 门禁状态原件 |
| `03_batch_report.json` | 批报告原件（298 cases，元数据） |
| `04_failure_register.json` | 失败登记原件（2 条） |
| `05_th_run_46958084.out` | run 日志原件（2942 字节） |
| `06_gate.json` | 批级 rate gate 状态原件 |
| `07/08_th_smoke*_status.json` | smoke2/smoke10 状态原件 |
| `09_orchestration.json`、`10_profile_policy.json` | 编排与 profile 原件 |
| `11_sacct.txt` | sacct 终态（主作业+子步） |
| `12_squeue_check.txt` | 离队确认（Invalid job id） |
| `13_log_markers.txt` | 日志四标记计数与 full 行号 |
| `14_batch_report_summary.txt` | batch_report 聚合（status/kind/stop_reason/model_calls/usage） |
| `15_failure_register_summary.txt` | register 2 条与 batch case 对照（仅元数据） |
| `16_monitoring_listing.txt` | monitoring 目录文件清单（名称/大小） |
| `17_remote_sha256.txt` | 远端源文件 SHA256（与本地副本逐一相符） |
| `18_poll_series.txt` | full 段 25 次轮询的 terminal/in_flight/pending/failed 序列 |
| `SHA256SUMS` | 本目录证据文件哈希 |

## 8. 交接（阶段 3 / 评分前）

1. run 终态已闭合：COMPLETED 0:0、`TH-RUN-PASS`、full 门禁三项全绿、298/298 terminal。
2. 评分（操作书 §6）**未启动**，由主窗口决定；评分时注意分母仍为 298，
   且 §6 第 1 条 2 题零调用登记项需先定性。
3. 本阶段无 STOP 级异常；如需复核，完整现场在
   `$TH_BATCH/monitoring/RXNG_7a88…/attempt1/` 与 `…/RXNG_ed3d…/attempt1/`。

## 9. 主窗口定性（2026-10-20 15:20，评分前）

对 §6 第 1 条两题（`RXNG_7a88…` / `RXNG_ed3d…`）的元数据核查与历史对账：

- 两题 run_error 均为 `ProductionContractError / cosubstrate_copy_in_expectation`
  （NC-9：拷贝组分不得出现在执行期望；结构化 fail-closed，零事件零提交），
  `status=completed`、`stop_reason=budget_limit`、`model_calls=0`。
- **历史对账（只读 cases 元数据）**：chain13、chain13d、chain13q、chain14a、
  chain14b、v44_glm_298_hpc2_a/b **全部同形态**（同一 kind、0 调用、completed）。
  ⇒ 属**既有基线失败形态**，非本轮 compiler-6/D1.2 回归；基线对照同口径少这两题。
- 两题均**不在** 21 题身份门名单，也**不是** 60 个空池题。
- 定性：批有效，分母 298 不变；两题按既有口径计未命中，交付时作为「既有结构性
  零调用终止」披露（不是模型未答，也不是本轮修复损耗）。
- 裁定：**进入 score**，不再要求修复或重跑。