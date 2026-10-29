# T-I TI-F1 定点回修复审（qwen3.8max 代 Codex，2026-10-21）

> **题域：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只核
> 工程控制与批准包身份，不生成真实成绩，不外推 dev、闭卷或通用能力；
> 合成绿不等于真实可发车。
>
> **provenance：本报告是 qwen3.8max 代 Codex 复审，按 CC 2026-10-21 指示
> 与 `docs/QWEN3_8MAX_REREVIEW_PACKAGE_2026-10-21.md` 授权执行；不冒充
> Codex 本人。** Codex 复审 `docs/T_I_CODEX_REREVIEW_2026-10-21.md`
> 保留为历史意见；若 Codex 自动重试产出新报告，两套并存，采信顺序归 CC。
>
> **审核对象：** 实际 HEAD `c9c6c7a7ae02b46769add09fbc2536323ce8a985`；
> `scripts/hpc/ti_operations.py`、`ti_run_wrapper.py`、`sbatch_ti_run.sh`
> （untracked 操作件，按脚本锁核身份）；orchestrator 停派发补丁
> `docs/review_evidence/ti_f1_fatal_2026-10-21/orchestrator_stop_dispatch.patch`
> （主树未合并，主树 `src/` 零 diff——本轮 git status 与 stop_check 计数 0 实测）。
> **审核纪律：** 只读主树与永久证据；三项回归的独立复跑用复制到
> `docs/review_evidence/qwen_rereview_2026-10-21/task_b/` 的脚本副本执行
> （修正 parents 深度后运行），不在提供方证据目录原地写；未连 HPC、
> 未提交/取消真实作业、未调模型、未读真实 env/key/题面/金标/
> reference_graphs/封存 run；不输出凭证值或结构正文。

## 1. 总裁定

**[298域] 总裁定：TI-F1 允许关闭（工程控制面）；TI-F2 维持关闭，不重开；
当前真实发车仍为 NO-GO（C0–C8 未闭合，见 §6）。**
Codex §2.1 的同一缺陷——真实 worker 可达的 `status=completed` 内嵌
`forbidden_permanent` 被降级、full 放行、巡检不停、收割后仍派新 qid——
已按原固定面回修，且本轮**独立复跑**（非采信提供方读数）确认：
full 不授通过（`exit=1`、`n_fatal=1`、无 full 回执、停点 `fatal_signal`）、
monitor 识别并停（`monitor_stopped=true`、停点 `monitor_stage_gate`）、
实际协调循环收割后零新派发（`calls=["fresh-1"]`、`second_fresh_dispatch=false`、
`dispatch_stopped=true`、`dispatch_stop_reason=fatal_signal:fresh-1`）、
双臂停点 `dispatch_fatal` 生效且现场保全；正常 2 题正控不受误伤。
原 63 项保留（扩展为 helper 55/55 + 公共链 15/15 + 调度探针 2 场景），
NC-9、普通非致命 ≤15、诚实 unknown 正控全在。脚本锁 14/14、批准包
身份链全部独立复算吻合。

## 2. fatal 分类四项固定回归（本轮独立执行）

回归输入 = Codex 证据中的**实际 worker 产物**
（`t_i_codex_rereview_2026-10-21/f1/actual_worker_result.json`，
SHA `56fe74c8…28bbbe` 本轮实测吻合；`status=completed`、`model_calls=1`、
`run_error` 内嵌 `forbidden_permanent`），只换合成 qid/run_id。

| # | 回归 | 提供方声明 | 本轮独立复跑 | 结论 |
|---|---|---|---|---|
| 1 | full 不授通过 | exit=1、full.passed=false、n_fatal=1、无回执、stop=fatal_signal | `negative_actual_worker_fatal`：**逐项相同**（rc=1、full_passed=False、n_fatal=1、full_receipt=False、forced_stop=fatal_signal、stop.details=q010:['forbidden']） | **闭合** |
| 2 | monitor 识别 fatal | stopped=true、n_fatal=1、停点 monitor_stage_gate、两臂 require_no_stop 拒绝 | `actual_worker_fatal_monitor`：**逐项相同**（monitor_stopped=True、n_fatal=1、reasons=['fatal_signal:q010']、stop.reason=monitor_stage_gate） | **闭合** |
| 3 | 收割后无第二个 fresh 派发 | calls=["fresh-1"]、second_fresh_dispatch=false、dispatch_stopped=true、reason=fatal_signal:fresh-1、n_pending=2 | 实际 `_run_batch_loop(workers=1)` 探针：**场景读数与提供方全等**（程序化比对 equal=True） | **闭合** |
| 4 | 双臂停点/现场保全 | stop.json=dispatch_fatal、glm/deepseek 均阻断、fresh-1 case 保留、正常 2 题正控照常派发 | 探针 fatal 场景：stop.reason=dispatch_fatal、`no_stop_both_arms={glm:true, deepseek:true}`、case 保全；`normal_two` 正控：calls=["normal-1","normal-2"]、无停点 | **闭合** |

**代码级核对（与行为证据互证）：**

- `classify_case`（`ti_operations.py:549` 起）：`case_failure(case)` 在
  completed 分支**之前**统一生成失败文本（`failure_kind`/`error`/
  `run_error`/`stderr_tail` 四字段 JSON 小写），fatal 标记命中即返回
  `failure_class="fatal"` + `fatal_markers` + `reason="completed_with_fatal_signal"`；
  Codex §2.1 指出的“completed 提前返回先于 fatal 检测（原 565–594 vs
  595–602 行）”的顺序缺陷已消除。
- NC-9 豁免次序：fatal 检查在 `_structural_zero_call` 之前，但 NC-9 合法
  文本（`ProductionContractError`/`cosubstrate_copy_in_expectation`）不含
  任何 `FATAL_MARKERS` 子串，`positive_nc9`（rc=0）与 helper NC-9 正控
  实测未误杀。
- streak 按分类事实：`evaluate_stage` 与新增 `scan_dispatch_fatal` 的连续
  故障统计对 `fatal/recoverable/run_failure/unregistered_zero_call` 且带
  `outage` 的行计数，**不再只认 `status=failed`**；completed+transport
  run_error 进入 streak；阈值沿用 `MONITORING_THRESHOLDS`，未新增。
- `scan_dispatch_fatal` 与阶段门共用 `classify_case` 单一来源；输出
  `ti-dispatch-scan-1`，只按原已定义 fatal/连续故障决定 stop。

## 3. 运行中停派发（补丁面）

| 核点 | 证据 |
|---|---|
| 默认不变 | `run_s5b_batch(..., stop_check=None)`/`_run_batch_loop(..., stop_check=None)`；`_check_stop` 在 None 时恒返 ""，派发路径与基线逐语句等价。主树 orchestrator（SHA `3cadb285…e684` 实测吻合）`stop_check` 计数为 0，未合并 |
| 停点时机 | 循环开始前先查一次（批启动前已有致命产物 ⇒ pending 清空、零派发）；此后**每轮收割发生（harvested=True）后、下一次派发前**再查；真值 ⇒ `pending.clear()`，已在途 worker 继续到终态并保全（`while pending or running` 保留收割臂） |
| fail-closed | 回调异常 ⇒ `S5bOrchestratorError(kind=s5b_stop_check_failed)`，不静默继续派发 |
| 披露 | 批报告追加 `dispatch_stopped`/`dispatch_stop_reason` |
| T-I 消费入口 | `ti_run_wrapper.py`：`--phase-label`（smoke2/smoke10/full）；`inspect.signature` 检测部署树支持 `stop_check` 才传入 `dispatch_stop_check`（`scan_dispatch_fatal` → `write_stop(reason="dispatch_fatal", cancel=True)` 双臂停点）；`sbatch_ti_run.sh` 三阶段均传 label（`bash -n` 通过） |
| 身份 | 补丁 SHA `ee218f71…beb152`、补丁后 orchestrator SHA `a95bb8be…5d62`、wrapper SHA `4fb6e8bb…682d6cdf` 均本轮实测吻合；`git apply --check` 对 HEAD 通过 |

**部署条件（并入 C1，不是新阻塞）：** wrapper 对未打补丁的树静默回退到
“阶段末兜底”（回修报告 §3 已如实披露），该形态**不满足**“收割后立即停
派发”的 TI-F1 原验收。因此真实发车所用 HPC 部署树的 orchestrator 必须
含本补丁（逐件 SHA 对上 `a95bb8be…5d62` 或证明等价），否则 C1 不绿。

## 4. 原 63 项与正控保留（本轮独立复跑）

| 层 | 提供方声明 | 本轮独立复跑 |
|---|---|---|
| helper | 55/55（原 50 + 新 5） | **passed=55**（副本脚本、mkdtemp 隔离、禁字节码） |
| 公共链 | 15/15（原 13 + 新 2） | **15 场景逐项与提供方读数一致**：4 正控 rc=0/full_passed=True/有回执；11 负控全部 fail-closed（smoke10 三停、full16、CX、quota、transport2、批准包两负、actual_worker_fatal 两场景） |
| 调度探针 | 2/2 | fatal + normal 两场景读数与提供方**全等**（§2 表） |
| 正控保留 | NC-9、普通非致命 ≤15、诚实 unknown | `positive_nc9`、`positive_full15`、`positive_full_content16`、`positive_completed` 全过；未见“全面拒绝换通过” |

## 5. 锁与批准包（本轮独立复算）

- **脚本锁**：`t-i-script-lock-1`，14 文件逐件 SHA256 复算**全部吻合**、
  `missing=[]`、`source_commit` = 实际 HEAD；锁自身 SHA
  `f0a43420…10625f46` 吻合。T-I 操作件为 untracked，锁是其在案身份
  （Codex §4 的 unknown 限制照旧：锁不能重建全仓未跟踪文件历史）。
- **批准包**：`approval-package` 校验模式（无 `--create`，只读）通过：
  批准 JSON SHA `190e42a5…a50ae7`、预注册文本 SHA `2e45d407…b84921b3`、
  `no_cap_ack=true`、`approval_source_kind=codex_delegated_cc_shijie`、
  `approved_at=2026-10-20T15:49:53Z`、四文书（prereg/task/final_review/
  script_lock）快照 SHA 逐件吻合。TI-F2 的首消费拒绝矩阵在 Codex 轮已
  关闭，本轮批准包重绑未触及其结论，**不重开**。
- 补丁不在主树锁内（主树未合并）——与回修报告 §5 登记一致；补丁身份由
  本报告 §3 的 SHA 实测与证据清单绑定。

## 6. TI-F1 关闭裁定与关闭后 C0–C8 最小清单

**TI-F1：允许关闭。** 依据：Codex §2.1 最小回修要求的全部四要素
（共用分类 completed 前消费 fatal、运行监督/调度消费链执行同一规则、
收割后不再派新 qid + 立即写双臂停点 + 保全、不只改阶段末 gate）均有
代码位置 + 本轮独立行为证据；补充回归用了指定的实际 worker 来源产物
走完整公共阶段链与真实调度消费入口；原 63 项、NC-9、≤15、诚实 unknown
保留；未新增阈值/恢复类别，未触科学面。
**关闭的性质：工程控制面关闭。** 不认证真实站点权限、scancel 效果、
真实失败频率或科学收益。

**TI-F2：维持关闭**，本轮批准包重绑核验一致，无重开证据。

**关闭后 C0–C8 最小清单（沿用 Codex §5 原表，仅更新 C1 状态）：**

| 条件 | 最小事实 | 当前状态 |
|---|---|---|
| C0 有效批准包 | 四文书快照/逐件 SHA、代决来源/时间/授权链、no_cap_ack=true、两臂 no-cap | 本地包本轮独立校验通过；**HPC 记录目录部署与外部清单绑定未核** |
| C1 两阻塞关闭+部署锁定 | 同消费入口复核关闭、现行操作件锁、HPC 逐件同值、科学源码/冻结参数不变 | TI-F2 已关、TI-F1 本报告关闭；**新增：部署树 orchestrator 须含停派发补丁（§3 部署条件）；远端逐件锁核未做** |
| C2 真实作业能力/净环境 | 凭证可用布尔、权限/分区/路径/磁盘/flock、无 V43_LLM_* 覆盖残留 | 未核；不得回传凭证值 |
| C3 netcheck | 实际作业号、COMPLETED 0:0、NETCHECK-PASS | 未跑 |
| C4 两臂文件与有效请求预检 | env 在位/600、模型/base host、request params 逐字同值、无禁用键 | 未读真实 env/有效请求 |
| C5 两臂最小真实调用 | 批准+站点核验后各模型最小调用、usage 可解析、入 preflight_calls | 未调用（付费，须先 C0） |
| C6 同题集+双臂 build 身份 | 题卷远端安全核行数/冻结 SHA、D6 manifest/fingerprint/逐题输入 SHA 全同 | 无真实 build 读数 |
| C7 prepare + P2-face 探针 | 合法包/no-cap/arm_config、冻结工程身份读数（files=298、specs_total=531 等，Codex §5） | 无真实 prepare/读数 |
| C8 协调/阶段放行/回传 | 单协调者、失败分类/取消路径、双臂 smoke barrier、full 前双臂 smoke2/smoke10 实际通过 | 只有本地实现/合成证据；真实 monitor 作业与回执未核 |

**唯一 GO/NO-GO 判据不变：`GO(当前阶段) = 该阶段全部必须前置均有实证
为真 AND 无活动停点`；任一 false/unknown 即 NO-GO。**
**[298域] 当前判读：C2–C8 全部未核（unknown），C0/C1 各有未核项 ⇒
真实发车 NO-GO。** TI-F1 关闭只解锁 C1 的“两阻塞关闭”子项，不解锁任何
真实作业动作；C5 付费调用仍须 C0 先行，顺序不因此改变。

## 7. 对请求 §6 五问的逐条回答

1. **completed 分支消费 fatal 的顺序是否闭合 §2.1 同一缺陷：是。**
   代码顺序（fatal 先于全部 completed 提前返回）+ 实际 worker 产物
   经完整公共链 `n_fatal=1`/full 拒绝 + monitor 停点，双路互证。
2. **`stop_check=None` 默认是否保持其它批行为：是。** 未打补丁树无此
   参数（wrapper 用 signature 检测回退）；打补丁树 None ⇒ `_check_stop`
   恒 ""，派发语句与基线等价。**收割后清空 pending、在途继续到终态并
   保全满足“立即不再派发新 qid”**：检查点在每轮收割后、派发 while 前，
   且派发循环带 `not dispatch_stop_reason` 条件。
3. **worktree 补丁是否最小消费面：是，可接受。** 只加可选参数 + 两个
   检查点 + 报告披露字段，未改编排语义/worker/评分；主树零 diff。
   不需再缩范围；但**部署条件并入 C1**（§3），防止真实发车跑在未打
   补丁树上退化为“阶段末兜底”。
4. **是否足以关闭 TI-F1：是（工程控制面）；TI-F2 保持关闭、无需重开。**
   四项固定回归 + 63 项保留 + 锁/批准包身份全部独立复现。
5. **剩余缺口：固定面无阻塞缺口。** 非阻塞留档两条：(a) 调度探针的
   worker 进程创建/结果与 passive reporting 是本地替身（提供方已如实
   披露；实际协调循环、case 校验、stop_check 路径为真实代码）；
   (b) 本地 scancel 替身不能认证站点取消权限（Codex 原 unknown 照旧）。

## 8. unknown / 本审核未覆盖

| 项 | 限制 |
|---|---|
| 真实站点/HPC | 未登录、未提交/取消真实作业、未做 netcheck/build/run/score；本报告不宣称已发车 |
| 真实模型与费用 | 未调用模型；金额/单价/账单 unknown，不估造；no-cap 政策签字仍归 CC/老师 |
| 部署一致性 | HPC 实际使用的 orchestrator/wrapper/脚本逐件 SHA 未核（C1 义务）；`source_commit` 不含 untracked 操作件 |
| 真实失败频率 | fatal/连续故障阈值行为只在合成与实际 worker 来源产物上验证；不外推真实批失败率 |
| 在途取消 | 已消费请求不可撤回；真实停点时在途与取消时点须照实记录（照旧） |
| 科学面 | 未触池/检索/排序/评分/prompt/分母；两臂模型选择与判据变更仍归 CC/老师 |

**裁决效力：本报告为 qwen3.8max 代 Codex 的 TI-F1 定点复审裁决
（允许关闭，附 §3 部署条件与 §6 NO-GO 判读），按 CC 2026-10-21 指示
出具；与 Codex 正链报告并存，最终采信顺序归 CC。判据变更、付费批、
真实题面外发不在本报告授权内。**
