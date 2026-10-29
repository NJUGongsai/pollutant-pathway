# 任务书 — P0① chain13 全链闭环漏斗（零模型零金标，2026-10-15）

> 派单：CC。执行者：分析执行代理。上游：GPT hit50 诊断
> `docs/CHAIN13_HIT50_DIAGNOSIS_GPT_2026-10-15.md` §6（漏斗骨架）+ CC 拍板
> P0 三件套先行。题域标签：**298=RHEA 通用酶学/已见题**；探针≠预注册≠成绩。
> 一句话：把「87 分到 149 分差 62 题」的机械损耗账，从检索到交卷逐站数清楚。

## 一、目标

对 chain13 GLM 臂 298 题做**逐站损耗账**（机械事实，零金标）：每题从
「语料记录可用→检索→池编译→去重/截断→模型选择→执行/准入→提交→判分」
每一站记数量与去向，输出逐题台账+全批聚合损耗表，标明**每站丢了多少件/题**。
判分面只消费既有 metrics（不重算）。

## 二、红线

1. 零金标零题面：不读 questions.jsonl/参考图；判分状态只用既有 metrics。
2. 零模型零网络；不动 src/tests（`scripts/s5b_offline_funnel.py` 只读复用，
   新脚本落分析目录）；不 commit 不 push；`PYTHONDONTWRITEBYTECODE=1`。
3. 拼不出=unknown，不硬归因；对外数字带 298 标签。
4. 本任务只出**机械损耗**（无候选/编译拒/去重折叠/未选中/执行失败/准入拒/
   提交未匹配），不评「正确候选损失」（那需要金标，禁止）。

## 三、数据面（全部本地已验证）

| 件 | 位置 |
|---|---|
| chain13 synced | `reports/ppv1_s5b/chain13_glm/synced/`（cases 298/payload 298/run_identity 298/calls 296/metrics.json(v2)+metrics.json.v1/batch_manifest.json） |
| 逐候选谱系 | manifest `entries[].pool_diagnostics.candidates`（5540 行）+ corpus_diagnostics 直方图 |
| 既有漏斗工具（必复用） | `scripts/s5b_offline_funnel.py`（extract_funnel/classify 已覆盖池→decide→调度→执行→准入→提交→匹配） |
| chain12 对照 | `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/synced/` |
| 分析目录先例 | `reports/ppv1_s5b/chain13_glm/analysis/`（attr/r0/base tables 族判定可复用） |
| 解释器 | `/Users/cc/miniconda3/envs/depending43/bin/python` |
| 仓根 | `/Volumes/CC/Enzyme_Agent/dependingv43`（HEAD `461844e`，收尾必须仍是它+工作树零 tracked diff） |

## 四、分步

1. **复用扩展**：以 `s5b_offline_funnel.py` 的 extract_funnel 为基座（import 或
   同构调用，禁复制粘贴改口径），新增既有工具没覆盖的三站：
   a. **检索站**：corpus_diagnostics（n_corpus_strict_exact/cn_candidate/
   wildcard_atom 直方图）逐题入账；
   b. **去重/截断站**：dedup_rejections/merged_into/pool_truncated 逐题入账
   （candidates 行 outcome 3/4 态 + decide 层 dedup）；
   c. **身份哈希列**：run_identity 的 code aggregate_sha256、语料三源 sha256
   （base tables 已算）、calls 的 issued/responded/failed（298/288/10）。
2. **逐题台账**：每题一行——各站件数+去向+终态（S/P/U）+rank+stop_reason。
   每站「该站损耗」定义写进 meta（如：执行站损耗=selected−method_failed−
   提交成功件，口径以代码为准并引用行号）。
3. **聚合损耗表**（本任务主交付）：298 题按站聚合「到达该站件数→通过件数→
   损耗件数→损耗题数」，另按 `channel × 拒因`、`族`（复用 base tables 族判定）
   分栏。对 uncovered 132 题、partial 47 题、rank>1 的 strict 32 题三组分别出
   「最深到达站」分布。
4. **chain12 对照行**：同口径可算的站（池/decide/执行/提交）出两批对照一行，
   字段缺失如实标「chain12 无此快照」。

## 五、自检锚点（对不上=停并报告）

| # | 锚 |
|---|---|
| 1 | 既有漏斗复跑闭合：uncovered 桶 A=1/B=12/H=119、全 298 桶 H=285、rows=298、mapping_issues=0 |
| 2 | metrics：v1 strict/partial/uncov=114/52/132；v2=119/47/132；hit@1=87 |
| 3 | 调用账：issued 298/responded 288/failed 10（10 个 transport failure case 对应） |
| 4 | 候选谱系：5540 行（compile_rejected 5266/compiled 207/merged 65/truncated 2） |
| 5 | 交付书红线自查：判分/金标零触碰、树零 diff、HEAD 不变 |

## 六、产物

```
reports/ppv1_s5b/p0_funnel_2026-10-15/
  p0_funnel.py            # 复用 s5b_offline_funnel 的扩展脚本
  p0_funnel_data.json     # 逐题台账+聚合+meta（口径定义/哈希/锚点核对）
  p0_funnel_summary.md    # 大白话+聚合损耗表（每表 298 标签+探针≠预注册≠成绩）
```

## 七、回传义务（≤25 行）

①各站聚合损耗一行表（到达/通过/损耗件数+题数）；②三组（uncovered/partial/
rank>1 strict）最深到达站分布；③与 chain12 对照行+字段缺失清单；④锚点核对
逐项；⑤产物路径。主会话抽查：锚点 1/2、逐题台账抽 3 题（1 strict+1 uncovered+
1 rank>1）、聚合表算术闭合（各站通过数=下站到达数）。

## 八、排障表

| 症状 | 处置 |
|---|---|
| rdkit 导入失败 | 解释器用错，回 conda depending43 |
| 站间数字不闭合 | 先查站定义口径（引代码行号），仍不闭合=如实报缺口不硬凑 |
| funnel 复跑与既有结果不一致 | 停，逐题列差异（既有结果为锚） |
