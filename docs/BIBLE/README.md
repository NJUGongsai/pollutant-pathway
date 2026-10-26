# BIBLE — 评测工程方法论九条（L1 资产）

> 用途：把弓赛线验证过的评测工程纪律沉淀成九条可执行 skill。
> 契约（slug、模板、红线）：[`_CONTRACT.md`](_CONTRACT.md)。
> 2026-10-26 CC 拍板先做 L1（方法论）；L2（检查脚本全量）/L3（agent 化）后续。
> 骨架来源：`docs/PROPOSAL_SELF_ITERATING_AGENT_BIBLE_2026-10-22.md` §二。

## 一、九条一览

| slug | 一句话规则 | 适用阶段 | 检查脚本 | 脚本状态 |
|---|---|---|---|---|
| [prereg-first](prereg-first.md) | 判定线、身份、发车登记先写死签字，再花钱 | 立项/发车 | `check_prereg_first.py` | ✅ 已实现（第一批） |
| [zero-llm-scoring](zero-llm-scoring.md) | 判分零 LLM、金标隔离、封存只读、泄漏自查 | 判分/交付 | `check_zero_llm_scoring.py` | ✅ 已实现（第一批） |
| [anchored-numbers](anchored-numbers.md) | 一切数字带锚：commit + 口径 + 批次/出处 | 全程（写文档即适用） | `check_anchored_numbers.py` | ✅ 已实现（第一批） |
| [probe-before-build](probe-before-build.md) | 零 LLM 探针先行：召回/误拒实测过门才立项 | 立项 | `check_probe_before_build.py` | ✅ 已实现（第二批） |
| [batch-discipline](batch-discipline.md) | 单变量成臂、同批对照、方差基线、事后标签 | 实验设计/发车 | `check_batch_discipline.py` | ✅ 已实现（第二批） |
| [loss-attribution](loss-attribution.md) | 失分桶闭合=分母、逐题配对 diff、换手分析 | 归因/交付 | `check_loss_attribution.py` | ✅ 已实现（第二批） |
| [stop-loss-gate](stop-loss-gate.md) | 未达线强制回查，净增益不足不宣称有效 | 出分/汇报 | `check_stop_loss_gate.py` | ✅ 已实现（第二批） |
| [dual-caliber](dual-caliber.md) | 口径变更走新版本，双口径并列，历史不覆写 | 判据变更/对外 | `check_dual_caliber.py` | ✅ 已实现（第二批） |
| [review-loop](review-loop.md) | 正链复审+化学评审双通道，代审标注，互证采信 | 交付/发车 | `check_review_loop.py` | ✅ 已实现（第二批） |

文档状态：九条 L1 文档**全部完成**（七节结构、反例均带已核实行号）。
脚本状态：第一批 3 个已实现（见 `scripts/bible_checks/`），其余 6 个待
第二批（契约 §五）。脚本调用与 pass/fail 形态见各文档 §6，汇总入口
`scripts/bible_checks/run_all.py`（随第二批交付）。

## 二、怎么用（按场景三组）

**开工前（立项一轮新工作）读：**
`prereg-first`（判定线与边界先落字）→ `probe-before-build`（方案前提
先过探针）→ `batch-discipline`（变量与对照设计）。
一句话：先想清楚"怎么算赢、怎么止损、一批改几个变量"，再动手。

**发车前（花钱前最后一道）读：**
`prereg-first` §5 发车段 → `batch-discipline` §5 发车段 →
`zero-llm-scoring` §5（阶段门与判分器锁）→ `review-loop` §5（评审链
额度与 provenance 准备）。
一句话：四文书 SHA、前置件、评审通道、停点耦合，逐项打勾才 launch。

**交付前（出报告/对外数字前）读：**
`anchored-numbers`（每个数字带锚）→ `dual-caliber`（同口径对比、双
口径并列）→ `loss-attribution`（桶闭合 + 配对 diff）→
`stop-loss-gate`（未达线不虚宣）→ `zero-llm-scoring` §5 交付段（泄漏
自查）→ `review-loop` §5（评审与代审收口）。
一句话：数字可溯源、口径不混、账能闭合、宣称不超过证据。

## 三、与 AGENTS.md 的关系

- 本 bible 是 `AGENTS.md` 各条红线的**展开与机器化**：AGENTS.md 给
  规则原文（金标不入仓、判分零 LLM、对外数字带题域标签、评审-回修
  循环等），bible 每条给"为什么 + 反例 + 清单 + 机器检查"。
- **冲突时以 AGENTS.md 红线为准**；bible 只收窄不放宽。
- bible 的反例全部来自仓内真实文档（每条带 `docs/xxx.md:行号`），
  反例是本资产的价值所在——新增反例须同样可定位、可核实。

## 四、状态表

| 项 | 状态 |
|---|---|
| 九条 L1 文档 | ✅ 全部完成（2026-10-26） |
| 第一批 3 个 check 脚本（prereg-first / zero-llm-scoring / anchored-numbers） | ✅ 已实现（并行交付，见 `scripts/bible_checks/`） |
| 其余 6 个 check 脚本 | ✅ 已实现（2026-10-26 第二批，契约 §五） |
| `run_all.py` 汇总入口 | ✅ 已实现（9 项汇总；全仓回溯 6 pass / 3 存量 fail） |
| L2（脚本全量 + CI 化）/ L3（agent 迭代回路） | ⏳ 未开工，见构想方案 §三/§六 |

## 五、维护约定

1. 反例可追加（每条 §4 是活节），但必须真实、可定位、经 `grep -n`
   或 Read 核实行号；查不到就写"待补"，不编造。
2. 数字带口径标签；"应该"不写成"已经"；不确定写"待核"。
3. 每条 ≤250 行，宁短勿空；改模板（§7）不影响七节结构。
