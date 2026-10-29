# TASK — C 探针：COSUB-GATE 454 行逐行分类 + 供给侧解堵解锁面模拟（2026-10-14）

> 派单：主窗口（grill 拍板：C 线=供给侧解堵，探针先行）。执行：子代理。
> 目的：为"共底物供给"预注册级设计书供数——把 COSUB-GATE 拦截面
> 逐行拆开，模拟供给侧解堵能解锁多少，并核与 D2 声明语义的互动。

## 一、背景与数据源（先读这三个）

| 件 | 位置 |
|---|---|
| 决策备忘（COSUB-GATE 的定义与来源） | `/Volumes/CC/Enzyme_Agent/dependingv43/docs/S5B_COMPILE_FUNNEL_DECISION_MEMO_2026-10-13.md` |
| chain12 批分析产物（noalign 分层归因，COSUB-GATE 454 行所在） | 决策备忘 §三 所指 `analysis/noalign_layer_attribution*`（在 chain12 批目录下，先 find 定位；批根 `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/` 一带） |
| 元素门/共底物袋实现 | v43 `src/pathway_v43/pollutant/` 下 analog 模板与编译相关模块（`s5b_compiler.py`/`s5b_builder.py` 及共底物相关代码；自己 grep 定位元素门判定点） |

已知事实（决策备忘口径）：COSUB-GATE 454 行 167 题 = 池层编译拒绝
最大可修单项，形态=analog 模板的辅因子袋（共底物）被元素门拦
（候选缺共底物参与物 ⇒ 元素守恒不过）。

## 二、要做的事（三层）

1. **逐行分类**：454 行按"缺哪种共底物"分桶（从模板袋/候选 payload
   可提取的共底物 SMILES 或身份），输出每桶行数/题数/代表例
   （聚合+合成级示例，不外带题面原文）。零模型零网络。
2. **解锁面模拟（供给侧假设）**：假设供给侧解堵——共底物作为
   recorded/池候选参与物供给（或模板袋补齐，两种语义各模拟一版）：
   - 语义 a（伴生供给）：共底物进池参与物集合，元素门过；
   - 语义 b（模板袋补齐）：analog 模板执行时带共底物产出；
   模拟口径=判分进程内/离线重放（探针级，不解冻任何东西），
   输出：语义 a/b 各解锁多少行→多少题、与 strict/partial 口径的
   预期互动（只给解锁面，不预测分数）。
3. **D2 互动检查**：解锁后的事件会带共底物参与物 ⇒ D2 声明语义
   （declared_copy_components/teacher b 档"诚实保留"）如何互动——
   会不会落 superset/partial？给机制层结论+例证（聚合）。

## 三、红线

- 零模型零网络零 LLM；金标/参考图只在判分进程内消费，产物零外带
  （分析目录 gitignored）；
- 不改 src/tests/既有 docs；不 push 不提交；
- 模拟是探针级（口径如实标注"探针/模拟≠预注册"）；
- 产物只出聚合计数与合成级示例。

## 四、产物与回传义务

- 产物：`reports/ppv1_s5b/c_probe_cosubgate_2026-10-14/`（自建目录，
  gitignored）：`cosub_classification.json` + `unlock_simulation.json`
  + `cosub_probe_report.md`（大白话+表格）。
- 回传：分桶表（缺什么共底物×行数×题数）、语义 a/b 解锁面对比、
  D2 互动结论、对预注册设计书的 3 条建议（供给语义怎么选）。
- 排障：数据找不到/行数对不上 454/167 → 停下报告，不硬凑数。
