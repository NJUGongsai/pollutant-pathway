# DELIVERY — no-cap budget 模式移植 v44→v43（2026-10-14）

> 任务书：`docs/TASK_NOCAP_PORT_V43_2026-10-14.md`。执行：实施子代理。
> v44 子目录全程只读，零改动。随轮本地 commit，不 push。

## 一、结论

v44 支线 P4c no-cap budget 运营壳（批级标记装载 + CLI 登记 + run 入口
guard∨marker 互斥 + worker 侧同判据核对）已逐字移植到 v43 主线；
新增 4 测全绿，全量 not-slow **2139 passed / 0 failed / 16 deselected
（slow）**，对基线 2135/0/16 零翻转（2135 既有 + 4 新增）。

## 二、文件清单

| 文件 | 状态 | 行数 |
|---|---|---|
| `src/pathway_v43/pollutant/s5b_orchestrator.py` | 修改 | 1047（原 919） |
| `src/pathway_v43/pollutant/s5b_cli.py` | 修改 | 554（原 418） |
| `src/pathway_v43/pollutant/s5b_worker.py` | 修改 | 405（原 366） |
| `tests/test_ppv1_s5b_no_cap_budget.py` | 新增 | 318 |
| `docs/NOCAP_PORT_V43_DELIVERY_2026-10-14.md` | 新增 | 本文件 |

工作树其它在途未跟踪文件（历史 docs/assets 等）一律未触碰、未入提交。

## 三、移植语义对照表（v44 行号 ↔ v43 行号）

### 1. s5b_orchestrator.py

| 件 | v44 参考 | v43 落点 | 说明 |
|---|---|---|---|
| 模块头 P4c 职责 bullet | :21-27 | :21-27 | 逐字 |
| `S5B_BUDGET_NO_CAP_FILE`/`S5B_BUDGET_NO_CAP_SCHEMA`（`v44-budget-no-cap-1`） | :251-252 | :407-408 | schema 串逐字保留 `v44-budget-no-cap-1`（任务书明示） |
| `BUDGET_MODE_NO_CAP` | v44 自 `v44_task_budget` 导入（:53） | :406 本地定义 | 偏差见 §五.1：v43 无任务级账本模块，值逐字一致 |
| `no_cap_marker_string` | :255-257 | :411-413 | 逐字 |
| `load_budget_no_cap_marker`（缺席 None/六类坏形状 fail-closed） | :260-334 | :416-490 | 逐字（docstring 中调用方清单去"发车器 preflight"，v43 无该件） |
| run 入口 P4c 注释块 | :445-449 | :611-616 | 逐字 |
| marker 装载+并存互斥拒（`s5b_budget_mode_conflict`） | :452-461 | :618-628 | 逐字 |
| real 批 guard∨marker 二选一（两者皆无 ⇒ `s5b_budget_guard_missing` 不变） | :462-472 | :629-640 | 逐字（嵌套 if 结构同 v44） |
| `budget_mode` 传参入 `_run_batch_loop` | :536-537 | :694-695 | 逐字 |
| `_run_batch_loop` 签名 `budget_mode: str = "numeric"` + docstring | :546-556 | :698-709 | 逐字 |
| `report["budget_mode"]` 披露 | :653-658 | :806-812 | 逐字（v43 落在 `report["gate"]` 与 `worker_timeout_s` 之间，同 v44 位序） |

### 2. s5b_cli.py

| 件 | v44 参考 | v43 落点 | 说明 |
|---|---|---|---|
| 模块头 budget bullet P4c 段 | :31-34 | :31-35 | 逐字 |
| orchestrator 导入扩充（5 名） | :59-72 | :54-69 | 逐字 |
| `cmd_budget` docstring（P4c 段） | :154-166 | :153-166 | 逐字 |
| no-cap 分发 `if str(args.budget_mode…)==BUDGET_MODE_NO_CAP` | :168-169 | :168-170 | 逐字 |
| 数值模式必填校验（input/output 价 None ⇒ 结构化拒 exit 2） | :170-177 | :171-178 | 逐字（v43 原为 argparse required，见 §五.2） |
| 数值默认补齐（cap 60/bound 30000/maxout 8192，None 才补） | :178-183 | :179-184 | 逐字；写入 budget_guard.json 的数值与 v43 原行为逐字节一致 |
| `_cmd_budget_no_cap`（必填/日期格式/数值参数互斥/既有数值守卫拒/同决定幂等/改决定拒/落盘含决定原文） | :252-345 | :251-344 | 逐字 |
| argparse：数值参数 default=None 化 | :498-509 | :485-497 | 见 §五.2 |
| argparse：`--budget-mode`/`--user-decision-date`/`--user-decision-record` | :511-520 | :499-508 | 逐字 |

### 3. s5b_worker.py（任务书表外补充，见 §五.3）

| 件 | v44 参考 | v43 落点 | 说明 |
|---|---|---|---|
| `_verify_budget_guard` docstring P4c bullet | :220-224 | :220-224 | 逐字（"协调器"→"协调者"沿 v44） |
| marker 装载（坏标记 ⇒ `budget_guard_invalid` fail-closed） | :242-253 | :246-257 | 逐字 |
| 闸门无金额配置分支（无标记 ⇒ missing 原样；有标记 ⇒ 通过） | :256-267 | :258-271 | 逐字 |
| 数值闸门+标记并存 ⇒ `budget_guard_mismatch` | :268-274 | :272-278 | 逐字 |
| 数值路径（batch sha 比对段） | :276-316 | :280-320 | 未动（v43 原文，与 v44 一致） |

### 4. tests/test_ppv1_s5b_no_cap_budget.py（新增）

| 件 | v44 源（test_v44_p4_launch_gate.py） | v43 落点 |
|---|---|---|
| NO_CAP_USER_DECISION/NO_CAP_DECISION_DATE 合成替身 | :112-118 | :57-61 |
| `clean_llm_env` 夹具 | :139-149 | :68-77 |
| `budget_guard_raw` 合成数值守卫 | :189-198 | :80-90 |
| `write_no_cap_marker`（合法+六类坏形状） | :320-353 | :93-129 |
| `test_no_cap_marker_loader_validation` | :1400-1425 | :132-157 |
| `test_cli_budget_no_cap_mode_write_idempotent_and_conflicts` | :1428-1496 | :160-228 |
| `test_run_s5b_batch_no_cap_marker_gates` | :1499-1550 | :231-282 |
| `test_worker_verify_budget_guard_no_cap_marker` | :1553-1588 | :285-318 |

## 四、测试红绿

| 项 | 数 |
|---|---|
| 新增测试 | 4 全绿（loader 负控×6 形状并入首测） |
| 全量 not-slow | **2139 passed / 0 failed / 16 deselected(slow)**，334.66s |
| 基线对照 | 2135/0/16 → 零翻转（2135 既有 + 4 新增） |
| 命令 | `PYTHONPATH=src ~/miniconda3/envs/depending43/bin/python -m pytest -q -p no:cacheprovider -m "not slow"` |

既有关键回归确认：`test_cli_budget_writes_machine_config`（v3r1_cost，
数值模式幂等/改值拒）随数值参数 None 化后仍绿——budget_guard.json
数值语义逐字节不变。

## 五、偏差与范围说明（如实）

1. **`BUDGET_MODE_NO_CAP` 本地定义**：v44 从 `v44_task_budget` 导入；
   v43 无任务级账本模块（任务书移植面不含它），故在 orchestrator
   金额守卫节本地定义，值逐字一致（`no_monetary_cap_user_decision`）。
2. **CLI 数值参数 default=None 化**：v43 原 argparse 将
   `--cap-cny/--input-tokens-bound/--max-output-tokens` 带默认值、
   `--input-per-mtok/--output-per-mtok` required=True——该形态下
   `_cmd_budget_no_cap` 的"数值参数互斥拒"永远触发（默认值非 None），
   no-cap 分支不可达；v44 参考实现本就一并改了此块，故照搬。合法
   数值调用写入 budget_guard.json 逐字节不变；唯一行为差 = 缺价时
   由 argparse usage 错改为结构化 JSON 拒（同 exit 2），v44 同款。
3. **worker 侧 `_verify_budget_guard` 一并移植（任务书表外）**：
   v44 P4c 的 no-cap 语义含 worker 同判据核对（单一验证源
   `load_budget_no_cap_marker`）；若不移植，no-cap 批在编排器放行后
   每个 real worker 会在闸门无金额配置处按旧判据拒发
   (`budget_guard_missing`)，三臂实际发不了车——与本轮移植目的
   （"落地后三臂才能过 budget 闸门发车"）直接冲突，且移植后
   run 入口测试③的端到端语义才与 v44 同构。数值路径逐字节未动。
4. **批报告新增 `budget_mode` 披露字段**：v44 同款（numeric 批 =
   `"numeric"`）；属 run 入口分支的组成部分，新增测试③断言它。
5. **schema 串保持 `v44-budget-no-cap-1`**：任务书明示照搬；
   v43 侧 CLI 落盘与 orchestrator/worker 装载自洽，且与 v44 标记
   文件字节兼容。
6. v44 仓（`v44/` 子目录）零改动；evaluation/s5b_scoring 判分侧
   零触碰；零模型零网络；金标/题面零触碰。

## 六、commit

随轮本地 commit（不 push）：见 git log 本次提交哈希；仅含 §二
五个文件。
