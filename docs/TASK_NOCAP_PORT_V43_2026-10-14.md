# TASK — no-cap budget 模式移植 v44→v43（2026-10-14）

> 派单：主窗口。执行：实施子代理。时限敏感：qwen/ds 两路 build
> 约 35 分钟后完成，本移植落地后三臂才能过 budget 闸门发车。
> 背景：chain13 三模型批跑在 v43 主线（policy-7+v2+声明链只在
> v43）；v44 支线的 no-cap 运营壳（P4c 已评审实现）是 v43 缺的
> 最后一块。

## 一、移植面（v44=参考实现只读，v43=目标仓）

| 件 | v44 参考位置 | v43 目标 |
|---|---|---|
| CLI budget no-cap 分发+参数（--budget-mode/--user-decision-date/--user-decision-record） | `v44/src/pathway_v43/pollutant/s5b_cli.py`（dispatch ~:168-169，`_cmd_budget_no_cap` ~:252+，argparse 参数块） | 同名文件 |
| no-cap 标记装载（S5B_BUDGET_NO_CAP_FILE/SCHEMA `v44-budget-no-cap-1` + `load_budget_no_cap_marker`，fail-closed 坏标记拒） | `v44/src/pathway_v43/pollutant/s5b_orchestrator.py`（~:251-303） | 同名文件 |
| run 入口守卫分支 | v44 `run_s5b_batch` 的 budget gate 段（guard 与 marker 互斥：数值守卫与标记并存拒、两者皆无拒、marker 合法=金额检查跳过） | v43 现行 :506-512 段（`real 批必须 budget_guard` 改为 guard∨marker 二选一） |
| 对应测试 | v44 tests 里 budget no-cap 正负控（幂等/互斥/坏标记 fail-closed） | 移植到 v43 tests 同构 |

## 二、要求

1. **语义逐字照搬 v44**（幂等：同决定重跑跳过、改决定拒；互斥：
   guard+marker 并存拒；schema 校验 fail-closed；用户决定原文/
   日期落盘）——不重设计，v44 是已评审参考；
2. **数值模式零行为差**（既有 budget_guard 路径字节不变语义）；
3. 全量 not-slow 零翻转（当前 HEAD 基线 **2135/0/16**，移植后
   +新增测试全绿零翻转）；
4. 新增测试（no-cap 正控/幂等/互斥/坏标记负控/数值模式回归）；
5. 随轮本地 commit **不 push**；不夹带工作树其它在途文件；
6. 不碰 v44 仓（只读参考）。

## 三、回传义务

文件清单+行数、移植语义对照表（v44 行号↔v43 行号）、测试红绿
（新增 N+全量数）、commit hash、一切偏差如实。

## 四、红线

零模型零网络；金标/题面零触碰；不改 evaluation/s5b_scoring
（判分侧）；v44 只读。
