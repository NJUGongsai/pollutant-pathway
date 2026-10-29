# T-I TI-F1 定点回修复审请求（2026-10-21）

> **题域标签：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本请求只请复核
> TI-F1 原致命门回修，不新增题域/科学结论；298 与 dev 双向不外推。
>
> **来源**：依据 `docs/T_I_CODEX_REREVIEW_2026-10-21.md` §2.1/§2.2/§6 的固定面结论
> （TI-F1 不关闭、TI-F2 关闭）与 §6 最小回修要求。TI-F2 不重开。

## 1. 本轮只改 TI-F1

| 改动 | 位置 | 说明 |
|---|---|---|
| completed 内嵌 fatal 分类 | `scripts/hpc/ti_operations.py` `classify_case`（第 549 行起） | completed 提前返回前先消费 `failure_kind`/`error`/`run_error`/`stderr_tail` 文本；命中原 `FATAL_MARKERS` ⇒ `failure_class=fatal` + `fatal_markers`，reason `completed_with_fatal_signal`。非致命仍 run_failure；NC-9 同因豁免保留 |
| 连续故障按分类事实 | 同文件 `evaluate_stage`、新增 `scan_dispatch_fatal` | completed+transport run_error 也进入 streak；不再只认 `status=failed`；不新增阈值 |
| 运行中停派发 | 隔离 worktree 补丁 `docs/review_evidence/ti_f1_fatal_2026-10-21/orchestrator_stop_dispatch.patch` | `run_s5b_batch(..., stop_check=None)` 默认关闭；每轮收割后、下次派发前调用；真值 ⇒ 不再派发新 qid，已在途 worker 继续到终态并保全；报告加 `dispatch_stopped`/`dispatch_stop_reason`；回调异常 fail-closed |
| T-I 消费入口 | `scripts/hpc/ti_run_wrapper.py` + `sbatch_ti_run.sh` | wrapper 增加 `--phase-label`；`inspect.signature` 检测部署树是否支持 `stop_check`，支持时传入 `scan_dispatch_fatal` + `write_stop(dispatch_fatal)`；sbatch 逐阶段传 label |
| 主树状态 | `src/pathway_v43/pollutant/s5b_orchestrator.py` | **主树未改、未合并**；补丁在独立 worktree 生成，`git apply --check` 对 HEAD 通过 |

未改科学判据、池/检索/排序/评分/prompt/模型/分母；未改 T-H 脚本、P0b worktree。

## 2. 身份与路径

| 项 | 值 |
|---|---|
| 实际 HEAD | `c9c6c7a7ae02b46769add09fbc2536323ce8a985` |
| 主树 orchestrator SHA | `3cadb285b0ea55a6a3e418e564fd017c77f491eebd684857c77cb447ef84e684` |
| 补丁 worktree | `/tmp/ti_f1_orchestrator_patch`（易失；可用 `git worktree add --detach <tmp> c9c6c7a && git apply <patch>` 复建） |
| 补丁文件 SHA | `ee218f717242bd54971e3a1343eeb5f9bf597f089f0d7a61601f53b789beb152` |
| 补丁后 orchestrator SHA | `a95bb8beee864c8815b565e97facf98ec9adafc2ca5dccf9786a7757b3385d62` |
| 实际 worker 产物 | `docs/review_evidence/t_i_codex_rereview_2026-10-21/f1/actual_worker_result.json`，SHA `56fe74c8e904e08323c3ffc102866efa05b3d9df277b4563d75fabefbf28bbbe` |
| 脚本锁 | `docs/T_I_SCRIPT_LOCK_2026-10-20.json`，14/14、`missing=[]`，锁 SHA `f0a43420003ba130fbf48ae41527abb991cfd796738e6650ba2e973110625f46` |
| 批准包 | `docs/T_I_APPROVAL_PACKAGE_2026-10-20/`，批准 JSON SHA `190e42a5f0178fa9b18336da9881cb09b7c3f191b82fdff9d5aacb8da4a50ae7`；文本 SHA 仍 `2e45d407…b84921b3`，`no_cap_ack=true` |

## 3. 四项固定回归（实际 worker 产物）

| 回归 | 读数 |
|---|---|
| full 不授通过 | 完整 sbatch→wrapper→phase→run-gate→barrier→full：`exit=1`，`full.passed=false`，`n_fatal=1`，`full_receipt` 不存在，`stop.reason=fatal_signal` |
| monitor 识别 fatal | `monitor_once`：`stopped=true`，`n_fatal=1`，停点 `monitor_stage_gate`；两臂 `require_no_stop` 均拒绝 |
| 收割后无第二个 fresh 派发 | 实际 `_run_batch_loop(workers=1)`：`calls=["fresh-1"]`，`second_fresh_dispatch=false`，`dispatch_stopped=true`，`dispatch_stop_reason=fatal_signal:fresh-1`，`n_pending=2` |
| 双臂停点/现场保全 | `stop.json`=`dispatch_fatal`；glm/deepseek 都阻断；`fresh-1` case 保留；正常 2 题正控仍派发 `["normal-1","normal-2"]` 且无停点 |

原 63 项保留并通过：helper **55/55**（原 50 + 新增 5）、公共链 **15/15**（原 13 + 新增 2）、
调度探针 **2/2**。NC-9、普通非致命 ≤15、诚实 unknown 正控保留。

## 4. 复现命令

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43

# 原 50 + 新增 5 helper
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts/hpc python3 -B \
  docs/review_evidence/ti_f1f2_2026-10-20/synthetic_check_f1f2.py

# 原 13 + 新增 2 公共链
PYTHONDONTWRITEBYTECODE=1 python3 -B \
  docs/review_evidence/ti_f1f2_2026-10-20/public_chain_f1f2.py

# 实际协调循环（需 rdkit 环境；worktree 不存在时先复建）
git worktree add --detach /tmp/ti_f1_orchestrator_patch c9c6c7a
git -C /tmp/ti_f1_orchestrator_patch apply \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ti_f1_fatal_2026-10-21/orchestrator_stop_dispatch.patch
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  docs/review_evidence/ti_f1_fatal_2026-10-21/actual_dispatch_stop_probe.py \
  --patch-src /tmp/ti_f1_orchestrator_patch/src

# 静态/锁/批准包
bash -n scripts/hpc/sbatch_ti_run.sh
git apply --check docs/review_evidence/ti_f1_fatal_2026-10-21/orchestrator_stop_dispatch.patch
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts/hpc python3 -B \
  scripts/hpc/ti_operations.py approval-package \
  --record-dir docs/T_I_APPROVAL_PACKAGE_2026-10-20 --docs-root .
```

## 5. 证据

- `docs/review_evidence/ti_f1_fatal_2026-10-21/actual_dispatch_stop_result.json`
- `docs/review_evidence/ti_f1_fatal_2026-10-21/public_chain_results/`
- `docs/review_evidence/ti_f1_fatal_2026-10-21/unit_controls_summary.json`
- `docs/review_evidence/ti_f1_fatal_2026-10-21/static_checks.txt`
- `docs/review_evidence/ti_f1_fatal_2026-10-21/SHA256SUMS`
- 技术报告：`docs/T_I_TI_F1_FATAL_FIX_REPORT_2026-10-21.md`

## 6. 请复核的问题

1. completed 分支在提前返回前消费 `run_error` 原 fatal 标记的顺序，是否闭合
   `docs/T_I_CODEX_REREVIEW_2026-10-21.md` §2.1 的同一缺陷？
2. `run_s5b_batch(stop_check=None)` 的默认 None 是否确实保持其它批既有行为；
   收割后清空 pending、已在途 worker 继续到终态并保全，是否满足“立即不再派发新 qid”？
3. 独立 worktree 补丁（主树未合并）是否属于本轮允许的最小调度消费面；是否需再缩范围？
4. 四项回归 + 原 63 项保留，是否足以关闭 TI-F1？TI-F2 是否保持关闭、无需重开？
5. 若仍有缺口，请只按原固定面指出需要补的最小证据/代码位置。

## 7. 边界

未连接 HPC、未提交/取消真实作业、未调用模型/网络、未读真实 env/key/题面/金标；
调度探针的 worker 进程创建/结果与 passive reporting 是本地替身，实际 worker 产物来自
Codex 证据，本轮未重新执行真实 worker。合成绿不等于真实可跑；C0–C8 事实仍按原表待核。