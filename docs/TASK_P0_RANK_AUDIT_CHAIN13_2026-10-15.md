# 任务书 — P0② rank 传递审计（模型第一名有没有半路丢，2026-10-15）

> 派单：CC。执行者：分析执行代理。上游：GPT hit50 诊断 §5 P1b（条件性源码
> 风险）+ CC 拍板 P0 三件套。题域标签：**298=RHEA 通用酶学/已见题**；
> 探针≠预注册≠成绩；本审计只读旧数据，不改任何行为。
> 一句话：阅卷只看每题第一个交的事件——查模型排的第一名，从排名表到
> 最终交卷顺序，中间每一道转手（去重折叠/调度/执行/准入/提交时序）有没有
> 把名次弄丢。

## 一、背景与怀疑点（自包含）

hit@1 口径：反应物侧含根严格命中的已提交事件按 `(created_at,event_id)`
升序，首个严格命中的位次决定 hit@K（`s5b_scoring.py:631`）。模型 decide
时产出 `model_rank_by_id` 排名。**GPT 读码推演的条件性风险（未证实）**：
池装配先装 prepared 池条目再装 novel（`runflow.py:868/917`）；净反应去重
保留较早条目、rank 表仅保留幸存键（`runflow.py:995`）、显式 rank 先于
fallback（`runflow.py:1025`）——若带模型首位的 novel 被折叠进无显式 rank
的早期池条目，其首位可能没有转给幸存者，另一显式候选便可能先执行。
另有执行失败/准入拒绝/defer 不提交事件（`runflow.py:1346`）也会让正式
first ≠ 模型第一。事件时间用微秒墙钟（`events.py:89`），无单调下界——
同微秒碰撞另计。

**本审计=拿 chain13 旧 payload 离线验这条链，不跑任何新实验。**

## 二、红线

1. 零金标零题面零模型零网络；判分状态只用既有 metrics（v1/v2）。
2. 不动 src/tests；不 commit 不 push；`PYTHONDONTWRITEBYTECODE=1`；
   产物落 gitignored。
3. 只读诊断：结论分类如实，推演不写成已证实；拼不出=unknown。
4. 对外数字带 298 标签；探针≠预注册≠成绩。

## 三、数据面（全部本地已验证）

| 件 | 位置 |
|---|---|
| chain13 payload | `reports/ppv1_s5b/chain13_glm/synced/runs/<run_id>/native_export/<digest>/payload.json`（298 件；关键节：`search_actions`（decide 的 model_rank_by_id/novel_proposals/dedup_rejections）、`deferred_entries`、`alternatives`、`hypotheses`、`events`（created_at/event_id）、`audit_production_reports`） |
| 题目↔run 映射 | synced `cases/<qid>.json`（run_id/export_digest） |
| 判分 | synced `metrics.json(.v1)`（main.rank/match_status） |
| 重点题清单 | `analysis/attr_chain13_c.json → C1.hit1_v2_decomposition`（lost_to_rank_gt1_qids 8 题 + strict 且 rank>1 全集） |
| 源码引用（只读） | `src/pathway_v43/pollutant/{runflow.py,search.py,events.py,queue.py,real_model.py}`（行号见 §一） |
| 解释器 | `/Users/cc/miniconda3/envs/depending43/bin/python` |
| 仓根 | `/Volumes/CC/Enzyme_Agent/dependingv43`（HEAD `461844e`，收尾不变+树零 diff） |

## 四、分步

1. **逐题抽取**：每题一行——model_first（rank=1 的候选 id+来源 pool/novel）
   → 是否 selected/deferred/blocked → 是否被去重折叠（dedup_rejections/
   merged 键）→ 是否执行成功（production status）→ 准入 disposition →
   是否产出事件；再取**提交序第一事件**（(created_at,event_id) 升序首条），
   回溯其 hypothesis/spec 是否就是 model_first（或其折叠幸存者）。
2. **分类**（互斥）：传递完整（model_first=提交首事件来源）/ 折叠丢位
   （model_first 被去重折叠且 rank 未继承）/ 执行失败 / 准入拒 / 未选中
   （deferred/blocked）/ 调用失败（10 题 transport）/ 模型弃权或格式轮 /
   其他-unknown（如实列）。
3. **重点两组深挖**：①hit@1 分解的 lost_to_rank_gt1 8 题（仍 strict 但
   掉出第一）：逐题给「模型第一名是谁/实际首事件是谁/差在哪一类」；
   ②strict 且 rank>1 全部 32 题（重排空间）：model_first 的严格命中性
   （用 metrics 的 per-qid rank 与事件匹配面，不重算判分——若需事件级
   匹配身份，从 payload 事件字段+判分产物既有披露取，拼不出标 unknown）。
4. **微秒碰撞计数**：同题内 created_at 相同的事件对计数（聚合披露，不定性）。
5. **聚合表**：分类×题数（对 298 + 对 119 strict + 对 87 hit@1 三口径），
   「折叠丢位」单独一行——这是 GPT 推演风险的实测裁决数。

## 五、自检锚点（对不上=停并报告）

| # | 锚 |
|---|---|
| 1 | 298 题全抽齐（payload 缺失=0）；10 题 transport failure 与调用账 failed=10 对应 |
| 2 | metrics：hit@1=87、strict(v2)=119、hit1 分解 kept74/lost10(覆盖)/lost8(rank)/new13 |
| 3 | lost_to_rank_gt1 8 题与 attr JSON qid 清单一致 |
| 4 | 交付红线自查（判分/金标零触碰、树零 diff、HEAD 不变） |

## 六、产物

```
reports/ppv1_s5b/p0_rank_audit_2026-10-15/
  rank_audit.py
  rank_audit_data.json      # 逐题行+分类+重点两组明细+微秒碰撞+meta
  rank_audit_summary.md     # 大白话+聚合表（298 标签）
```

## 七、回传义务（≤25 行）

①分类×题数聚合表（三口径）；②「折叠丢位」实测数（GPT 风险裁决：是/否/
多大规模）；③8 题 rank 损失逐题一行归因；④32 题重排空间的 model_first
严格命中性汇总；⑤微秒碰撞计数；⑥锚点核对；⑦产物路径。主会话抽查：
分类互斥闭合（各类和=298）、8 题逐题行、抽 2 题 payload 人工对链。

## 八、排障表

| 症状 | 处置 |
|---|---|
| payload 中找不到 model_rank_by_id | 读 `search_actions` 的 decide action detail（outcome_payload.outcome.detail.model）；结构不符停下报告不猜 |
| 事件→hypothesis→spec 回溯断链 | 如实标 unknown（回溯链字段以 search/production 代码为准） |
| 分类不互斥/不闭合 | 重读 §四.2 分类定义；仍不闭合=停下报告 |
