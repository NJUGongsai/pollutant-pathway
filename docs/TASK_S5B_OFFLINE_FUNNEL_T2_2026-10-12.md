# 任务书 T2：chain11/12 离线全链拼账工具（2026-10-12）

> 主会话起草，交实施子代理。零上下文可接。
> 上游：GPT 丢分分析 §6.1 P0-2（按题闭合漏斗账）+ 侦察结论 + 对账报告 docs/S5B_CHAIN11_TO_CHAIN12_RECON_2026-10-12.md（必读，含 bucket 迁移与归因上界）。

## 0. 一句话目标

写一个**离线只读拼账工具**（scripts/ 下新脚本），消费本地已同步的 chain11/12 封存产物，对每题每个候选拼出"走到哪一步、死在哪一步"的全链账，重点产出 **chain12 的 125 道 uncovered 逐题主因分桶**（互斥主桶+交集单列），并顺带覆盖 43 partial 与 38 道后位答案的供给面视图。零模型、零网络、不改任何管线代码。

## 1. 数据位置与形态（本地已就位）

| 数据 | 路径 | 形态 |
|---|---|---|
| 判分逐题 | `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/synced/metrics.json` | per_qid 298 行：qid/run_id/main.match_status/main.rank |
| 逐题账本投影 | `…/synced/runs/<run_id>/native_export/<case>/payload.json` | 全量事实：search_actions(entry_payload 含 spec key/rank/signature)/expansion_outcomes(含 no_local_candidate、dedup_rejections、novel_rejections)/audit_production_reports/deferred_entries/blocked_entries/expansion_plans/budget/events/states/hypotheses/model_requests/stop_reason_records/endpoint_record 等 |
| 逐题终态 | `…/synced/cases/<qid>.json` | status/stop_reason/counts/usage |
| 批级 | `…/synced/batch_manifest.json`、batch_report.json、progress.json | entries[].pool_diagnostics（**聚合直方图**——旧批池层只有聚合，这是已知边界） |
| chain11 对照 | `reports/ppv1_s5b/chain11_s5b_298_v4_20261010/synced/…` | 同构 |

注意：run_inputs/<qid>.json（含冻结 plan.pools）**未同步**，池 spec 全集从 payload 的 search_actions/entry_payload 与 manifest pool_diagnostics 重建；池层编译失败在旧批只有聚合计数（candidates 明细是 T1a 给未来批的），拼不出来就诚实标 `pool_layer_aggregate_only`。

## 2. 候选全链阶段定义（谱系语义，分阶段落桶）

对每 qid，从 payload 重建候选清单与各阶段状态：

```
池供给(specs) → decide 入口(prepared) → 去重折叠(dedup_rejections) → 排序(effective_rank)
→ 调度(schedule_hypotheses：selected / deferred[selection_cap|alternatives_budget] / blocked[depth])
→ 执行(method_failed?) → 准入(admission rejected/deferred/conditional?) → 事件提交(events)
→ 提交后匹配(从 metrics 桶拿题级；逐事件匹配细分不在本任务，属 T3 评测器重跑)
```

## 3. 125 uncovered 主因分桶（核心产出）

每题归一个**互斥主桶**（按最深到达阶段），多原因交集单列：

| 主桶 | 判据（从 payload 可判） |
|---|---|
| A. 无池候选 | expansion_outcomes 有 kind=no_local_candidate，或 specs=0 |
| B. 有候选但全部死在 decide 前 | specs>0 但无 prepared 事件且无 dedup/调度痕迹（注意：池 spec prepare 失败会导致 decide run 级失败，从 cases failure_kind 判） |
| C. 去重折叠损失 | 全部候选被 dedup 吞（幸存者也失败） |
| D. 调度落选 | 候选止步 deferred/blocked（alternatives_budget=2/父、selection_cap） |
| E. 执行失败 | method_failed |
| F. 准入拒绝 | admission_rejected/deferred 未转正 |
| G. 预算截断 | stop_reason=budget_limit 且有候选未展开（budget 表 used/remaining 对账） |
| H. 已提交但不匹配 | 有提交事件但题级 uncovered（提交事件数/候选数/参与物规模给计数；逐事件为何不匹配= T3） |
| I. 其他/拼不出 | 诚实标 unknown，写明缺什么 |

**闭合验收**：主桶之和=125；每桶给 qid 清单；A–I 各桶与 chain11 同桶对照（155 题里同因多少）。同时给 43 partial、130 strict 的同口径供给面视图（宽度/深度/审计 unknown 计数等描述统计，不判分）。

## 4. 红线

1. 零模型零网络零 LLM；不跑评测器、不重算匹配（那是 T3）。
2. 只读：不改 synced/ 任何文件；脚本与输出落 `reports/ppv1_s5b/chain12_…/analysis/`（新建子目录，gitignored）与 `/tmp/s5b_t2_funnel/`；脚本本身若入库放 `scripts/`（新文件，不碰既有脚本）。
3. 不读金标（本地也没有）；题域标签 298/RHEA 已见题写进输出头。
4. 数字诚实：拼不出的标 unknown/aggregate_only，禁止把聚合数当逐题数、禁止把 stop_reason 全是 budget_limit 直接写成"G 桶 298 题"（需与候选展开状态交叉）。
5. 不 push、不 commit。

## 5. 分步

1. 读对账报告（背景与归因上界）→ 抽 2 个 qid 的 payload 人工走一遍全链（一个 uncovered 一个 strict），确认字段理解；关键结构不确定性列出来。
2. 写脚本（建议单文件 `scripts/s5b_offline_funnel.py`，参数：批根路径、输出目录；纯标准库+json）。
3. 跑 chain12 全量 → 桶闭合自检 → 跑 chain11 对照。
4. 产出：`funnel_chain12.json`（逐题逐桶原始）+ `funnel_summary.md`（分桶表+qid 清单+对照+known limits）。
5. 抽查 5 题（每主桶至少 1 题如有）人工核对脚本判桶与 payload 原文一致。

## 6. 排障表

| 症状 | 处置 |
|---|---|
| payload 键与预期不符（侦察清单缺漏） | 以实际 payload 为准，调整阶段判据并在 known limits 记录偏差 |
| 阶段归属歧义（如候选既 deferred 又有旧 attempt） | 主桶取最深到达阶段；歧义案进交集表不硬归 |
| 桶不闭合 | 先查 qid 映射（run_id↔qid 从 cases/metrics 双向），修映射不修数据 |

## 7. 回传义务

1. 脚本路径+用法一行；2. chain12 主桶表（A–I×题数，闭合 125）+ 逐桶 qid 计数；3. chain11 155 对照表；4. partial/strict 供给面描述统计；5. 5 题人工抽查结果；6. known limits 清单（含 pool_layer_aggregate_only）；7. 产出文件路径。最终消息按此七项回报，不贴大段原始 JSON。
