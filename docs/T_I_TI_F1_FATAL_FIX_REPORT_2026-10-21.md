# T-I TI-F1 fatal 门定点回修报告（2026-10-21）

> **题域标签：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只含操作脚本、
> 调度补丁与本机合成回归，不含真实成绩、真实调用或 HPC 读数；298 与 dev 双向不外推。
>
> **状态：TI-F1 的 completed+run_error fatal 分类与运行中停派发已回修；TI-F2 保持关闭。**
> 未连接 HPC、未提交作业、未调用模型、未读真实 env/key/金标/题面/封存 run、未 push。
> 本报告不宣布发车；当前仍 NO-GO。

## 1. 复审缺陷与回修范围

Codex `docs/T_I_CODEX_REREVIEW_2026-10-21.md` §2.1 指出：真实 worker 可产出
`status=completed` + `run_error` 内嵌 `forbidden_permanent`；原 `classify_case`
completed 分支提前返回，把它降为普通 `run_failure`，full 门和 monitor 错误接受；
实际协调循环收割后仍派发新 qid。仅修此 TI-F1 原致命门，不新增阈值、恢复类别或科学改动。

## 2. 共用分类（`scripts/hpc/ti_operations.py`）

- `classify_case`（第 549 行起）现在在 completed 分支提前返回**之前**调用
  `case_failure` 生成失败文本（含 `failure_kind`/`error`/`run_error`/`stderr_tail`），
  用小写文本匹配原 `FATAL_MARKERS`；命中即返回
  `failure_class="fatal"` + `fatal_markers` + `reason="completed_with_fatal_signal"`。
- 非致命 completed+run_error 仍按 `run_failure`；合法同因 NC-9
  （`ProductionContractError / cosubstrate_copy_in_expectation`、`counts.events=0`）
  仍先走 `structural_zero_call` 豁免，不误杀。
- 连续故障统计改为按分类事实：`evaluate_stage` 与新增
  `scan_dispatch_fatal` 对 `fatal`/`recoverable`/`run_failure`/`unregistered_zero_call`
  的 `outage` 计 streak，不再只认 `status=failed`；completed+transport run_error
  也进入连续故障判定。
- full 门：实际 worker 产物现在 `n_fatal=1`、`passed=false`；monitor 同源识别并写停点。

## 3. 运行中停派发（隔离 worktree 补丁，主树未合并）

- 补丁：`docs/review_evidence/ti_f1_fatal_2026-10-21/orchestrator_stop_dispatch.patch`
  （SHA `ee218f71…beb152`），在独立 worktree
  `/tmp/ti_f1_orchestrator_patch` 生成；`git apply --check` 对主树 HEAD 通过，
  主树 `src/` 零 diff、未合并。
- 补丁内容：`run_s5b_batch(..., stop_check=None)` 与 `_run_batch_loop(..., stop_check=None)`；
  默认 None 完全保持其它批行为。每轮收割后、下一次派发前调用回调；返回真值 ⇒
  `pending.clear()`、不再派发新 qid，已在途 worker 继续到终态并保全；批报告追加
  `dispatch_stopped` / `dispatch_stop_reason`。回调异常 ⇒
  `S5bOrchestratorError(kind=s5b_stop_check_failed)`，不静默继续。
- T-I 侧：`ti_run_wrapper.py` 增加 `--phase-label`；用
  `inspect.signature(run_s5b_batch)` 检测部署树是否支持 `stop_check`，支持时传入
  `dispatch_stop_check`（`scan_dispatch_fatal` → `write_stop(reason=dispatch_fatal)` →
  返回 2）。`sbatch_ti_run.sh` 在 smoke2/smoke10/full 都传 `--phase-label`。
  未打补丁的树仍由 phase/monitor 末端兜底，但不满足“收割后立即停派发”。

## 4. 回归（实际 worker 产物）

来源：`docs/review_evidence/t_i_codex_rereview_2026-10-21/f1/actual_worker_result.json`
（SHA `56fe74c8…28bbbe`），只换合成 qid/run_id 与验证必需信封，保留
`status=completed`、`model_calls=1`、`run_error` 的 `forbidden_permanent` 文本。

| 回归项 | 结果 |
|---|---|
| 完整公共阶段链（sbatch→wrapper→phase→run-gate→barrier→full） | **full 不授通过**：`exit=1`，`full.passed=false`，`n_fatal=1`，`full_receipt` 不存在，`stop.reason=fatal_signal` |
| monitor | **识别 fatal**：`monitor_once` 返回 `stopped=true`、`n_fatal=1`、停点 `monitor_stage_gate`；两臂 `require_no_stop` 均拒绝 |
| 实际协调循环 `_run_batch_loop(workers=1)` | **收割后无第二个 fresh 派发**：`calls=["fresh-1"]`，`second_fresh_dispatch=false`，`dispatch_stopped=true`，`dispatch_stop_reason=fatal_signal:fresh-1`，`n_pending=2` |
| 双臂停点/现场保全 | `stop.json` 为 `dispatch_fatal`；glm/deepseek 两臂均被阻断；`fresh-1` case 文件保留；正常 2 题正控仍派发 `["normal-1","normal-2"]` 且无停点 |
| 原 63 项正负控 | 原 50 项 + 13 场景全部保留并通过；扩展后 helper **55/55**、公共链 **15/15**（新增 5+2）、调度探针 **2/2**；NC-9、普通非致命 ≤15、诚实 unknown 正控保留 |

证据：`docs/review_evidence/ti_f1_fatal_2026-10-21/`
（`actual_dispatch_stop_result.json`、`public_chain_results/`、`unit_controls_summary.json`、
`static_checks.txt`、`SHA256SUMS`）。

## 5. 锁与批准包（重新绑定）

- 脚本锁 `docs/T_I_SCRIPT_LOCK_2026-10-20.json` 重算 14 文件，`missing=[]`，
  锁 SHA `f0a43420…10625f46`；`ti_operations.py` `931966a8…ffefdfa7`、
  `ti_run_wrapper.py` `4fb6e8bb…682d6cdf`、`sbatch_ti_run.sh` `d4591e74…9b43b42`、
  任务书 `0b9b0557…6c7b456`。
- 批准包 `docs/T_I_APPROVAL_PACKAGE_2026-10-20/` 按新任务书/锁重新生成并自校验；
  批准 JSON SHA `190e42a5…a50ae7`，文本 SHA 仍 `2e45d407…b84921b3`，
  `no_cap_ack=true`、代决来源/授权链不变。
- 补丁不在主树锁内（主树未合并）；补丁 SHA 由本报告与新证据清单绑定。

## 6. 仍缺的 C0–C8 事实

| 条件 | 状态 |
|---|---|
| C0 有效批准包 | 本地包已重绑并自校验；HPC 记录目录部署/外部清单未核 |
| C1 两阻塞关闭及部署锁定 | TI-F2 已关闭；TI-F1 本次回修待 Codex 复审；补丁 HPC 部署与逐件锁核未做 |
| C2 真实作业能力/净环境 | 未核 |
| C3 netcheck | 未跑 |
| C4 两臂文件与有效请求预检 | 未读真实 env/有效参数 |
| C5 两臂最小真实调用 | 未调用 |
| C6 同题集与两臂 build 身份 | 无真实 build 读数 |
| C7 prepare 与 P2-face 探针 | 无真实 prepare/读数 |
| C8 协调/阶段放行/回传 | 只有本地实现/合成；真实 monitor 作业、双臂 smoke 与回执未核 |

## 7. 边界与结论

- 本报告不认证真实 HPC、真实模型、真实失败频率或科学收益；调度探针的
  worker 进程创建/结果与 passive reporting 是本地替身，实际 worker 产物来自 Codex 证据，
  未在本轮重新执行真实 worker。实际协调循环、case 校验、stop_check 路径与 T-I 操作链为真实代码。
- 未改 `src/` 主树、T-H 脚本、评分/prompt/模型/分母/池/检索/排序；未 push。
- **具备交 Codex 做 TI-F1 定点复审的条件**；复核关闭且 C0–C8 全绿前，发车仍 NO-GO。

## 8. 路径

- 本报告：`docs/T_I_TI_F1_FATAL_FIX_REPORT_2026-10-21.md`
- 复审请求：`docs/T_I_CODEX_F1_REREVIEW_REQUEST_2026-10-21.md`
- 证据：`docs/review_evidence/ti_f1_fatal_2026-10-21/`
- 补丁：`docs/review_evidence/ti_f1_fatal_2026-10-21/orchestrator_stop_dispatch.patch`
- 锁/批准包：`docs/T_I_SCRIPT_LOCK_2026-10-20.json`、`docs/T_I_APPROVAL_PACKAGE_2026-10-20/`