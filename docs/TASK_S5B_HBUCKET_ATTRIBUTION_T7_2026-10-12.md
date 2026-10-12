# 任务书 T7：H 桶 120 题逐题归因 + 漏斗工具修复 + 一轮文书更正（2026-10-12）

> 主会话起草，交单个实施子代理串行执行。零上下文可接。
> 上游：chain12 丢分归因第一轮评审 [S5B_CHAIN12_LOSS_ATTRIBUTION_ROUND1_REVIEW_2026-10-12.md](S5B_CHAIN12_LOSS_ATTRIBUTION_ROUND1_REVIEW_2026-10-12.md)（必读，P1/P2 原文与本任务 §2 的修复/更正要求一一对应）+ 第一轮交付书 [S5B_CHAIN12_LOSS_ATTRIBUTION_ROUND1_DELIVERY_2026-10-12.md](S5B_CHAIN12_LOSS_ATTRIBUTION_ROUND1_DELIVERY_2026-10-12.md)。
> 题域标签：**298 / RHEA 通用酶学 / 已见题**，一切数字不外推 dev。

## 0. 一句话目标

把 chain12 的 **H 桶 120 题（已提交但不匹配）** 从"主战场"一个数变成逐题归因账：**错在哪（判分器视角的失配形态）+ 损耗痕迹（候选级失败/截断并存，回应评审 P1"不能证明执行链零损耗"）+ 供给差在哪（池层聚合对照）**；同时完成评审 P2 的漏斗工具修复与 P1/P2 的文书更正。全程零模型零网络零 LLM，判分代码零调用零改动。

## 1. 数据与代码位置（本地已就位，全部只读除脚本/测试）

| 项 | 路径 | 说明 |
|---|---|---|
| H 桶清单 | `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/funnel_chain12.json` → 顶层 `bucket_qids.H` | T2 产物，120 qid |
| 事件级判分明细 | 同目录 `analysis/rescore_detail.json`（T3 产物，298/298 对齐率 1.0） | `per_qid[qid]`：`edge_matches[]`（match_status/coverage_mismatch_events/matched_events）、`node_matches_min[]`（node_id/role/match_status）、`strict_hit_positions`、`d2_declared_copy_components_occurrences`、`n_candidate_events`。**本任务只消费这份已落盘明细，不重跑评测器** |
| 逐题全链行 | 同目录 `analysis/funnel_chain12.json`（修复后以重跑版为准） | 候选级痕迹字段：`method_failed_outcomes`、`dedup_rejections`、`novel_rejections`、`deferred_*`、`admission_dispositions`、`pool_compile_fail_hist` 等 |
| 真实批池聚合 | `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/synced/batch_manifest.json` → `entries[].pool_diagnostics` | **无逐候选行**（T1a 谱系只属于 v43 0e463335 重建探针与未来批）；有逐题 `compile_failure_histogram`（按 reason）、`n_pool_returned`、`corpus_diagnostics`、`recorded_diagnostics` 等聚合 |
| 对照桶 | 130 strict + 43 partial qid 清单同在 `bucket_qids` | 池层对照用 |
| chain11 对照批 | `reports/ppv1_s5b/chain11_s5b_298_v4_20261010/synced/…` 同构 | 工具修复重跑对照 |
| 待修工具 | `scripts/s5b_offline_funnel.py` | bug：第 195–196 行读 `rejected/deferred`（错枚举），`classify()`（222–257 行）无 F 分支 |
| 准入枚举权威 | `src/pathway_v43/pollutant/audit.py:327-333` | `expand / retain_conditional / defer / reject`（只读引用，不改） |
| 评审探针（正负控原料） | `docs/review_evidence/chain12_loss_round1_codex_2026-10-12/probe.py` + `probe_result.json` | 评审 §4 已复现的两用例：`disposition=reject` 漏计 F；H 桶与候选损耗并存标志 |
| 一轮交付书（待更正） | `docs/S5B_CHAIN12_LOSS_ATTRIBUTION_ROUND1_DELIVERY_2026-10-12.md` | §2 第 2/4/5 步更正对象 |
| T6 D2 竞争产物 | `analysis/t6_d2_contention.md` | 文书更正引用评审 §6.2 口径，不重做分析 |

## 2. 五步走

### 2.1 修 `s5b_offline_funnel.py`（评审 P2 最小修复）

1. 第 195–196 行 `admission_rejected_or_deferred` 枚举对齐 `ADMISSION_REJECT/ADMISSION_DEFER`（`reject`/`defer`）；`admission_dispositions` 原样保留。
2. `classify()` 补 F 分支：题级 `selected>0`、`events==0`、无执行产出、且候选止步于准入 `reject/defer` → `"F"`。插入位置按"最深到达阶段"语义自定，但**必须**保留 E/G/D 既有语义不翻转；执行失败与准入拒并存的歧义按既有惯例进交集表不硬归。
3. 新测试 `tests/test_s5b_offline_funnel_controls.py`（新文件）：合成 payload 用例覆盖——①`disposition=reject` 且 selected=1 无事件 → F 且拒绝计数=1（评审复现的漏计负控）；②一题有提交事件+执行失败+dedup+预算 defer 并存 → 主桶 H 且对应交集标志 true；③`retain_conditional` 正控：不计入拒绝、不落 F。
4. 重跑 chain12 与 chain11 → 修复前后桶账对照表。真实批 F 若=0 就如实 F=0（以重跑为准，禁止为闭合硬凑）；若有题在 B/I↔F 间迁移，逐 qid 列出并给 payload 证据。
5. 全量 `pytest -m "not slow"` 红绿（既有测试零翻转预期；新测试全绿）。

### 2.2 H120 事件级失配形态归因（核心产出）

只用 `rescore_detail.json` 已落盘明细（冻结判据程序复算产物）。已知事实底：H120 题的题级 match_status 全部为 `unmatched_required_node_uncovered`；node 级（全 293 有提交题合计）strict_structure 501 / unmatched 89 / cn_only 45。要做：

- 逐题统计：提交事件数、未匹配边数、`node_matches_min` 各 match_status 计数（按 role/side 分）、`coverage_mismatch_events` 计数、`required_node_gaps` 计数。
- 数据驱动归类：按上述字段的组合把 120 题分成可数类（先报组合分布再定类，类名用程序口径不用化学断言）；每类给 qid 清单 + 一行程序语义解释。
- 交叉核对：与 `d2_declared_copy_components_occurrences`（D2 指纹）交叉——H120 里 D2 指纹题多少、失配形态是否偏向覆盖类。
- 输出：`analysis/hbucket_attribution.json`（逐题原始行）+ `analysis/hbucket_attribution.md`（分布表+qid 清单+类解释）。

### 2.3 H120 候选级损耗账（评审 P1 的"痕迹账"）

用修复后 funnel 逐题行，对 H120 逐题数四类候选级痕迹：执行失败（method_failed）、去重折叠（dedup_rejections）、novel 预校验拒（novel_rejections）、调度落选/预算（deferred/blocked）+ 准入拒（reject/defer disposition）。产出"有 ≥1 痕迹的题数 / 120"与痕迹类型分布表。**口径写死（评审原话）**：这证明痕迹存在，不证明丢了正确候选，也不能反推正确候选零损失；H120 仅支持"已提交集合在当前尺子下未严格覆盖"。

### 2.4 池层供给对照（评审 §6.1 聚合级）

H120 vs strict130 vs partial43 三桶对照：逐题 `compile_failure_histogram` 按 reason 聚合（桶×reason 表）、`n_pool_returned`/池宽描述统计。评审建议的四分类映射（合理不适用/表达能力未支持/工具缺陷/超时与身份）作为**分析性映射表**给出（reason→大类的映射与理由写成 md 表，标注"分析性归类非权威分类"；含 pregate/no_alignment 属编译前必要条件不算编译器能力缺口的口径）。逐候选级谱系缺失照旧标 `pool_layer_aggregate_only`。

### 2.5 一轮交付书文书更正（打进原文档，保留原文备份节）

按评审建议文案逐处替换/追加勘误（每处把"前→后"原文录进 T7 回传）：

1. §0"执行链零损耗…"（交付书第 17 行段）→ 评审 §3 建议替换文案（125 uncovered 最深阶段互斥分账口径）。
2. §0"净增 27 主力只能来自 H 桶"→"当前优先验证的方向"口径（评审 §5/§9）。
3. §3 表第 1 行 RankLLM"机械规则全负…期望收益薄"→"机械规则全负不直接上线；真实模型排序净增未测（pending），暂缓=资源优先级"。
4. §4 provenance"全程零模型零网络零 LLM"→ 限定为"离线分析与冻结程序复算零预测模型；远端同步与 mimo 外审单列 provenance"。
5. 顺带 §0 表"无候选/准备失败 5"行加注：2 无候选+2 prepare 契约失败+1 模型传输失败（评审 §8）。
6. 文档头部加一行勘误指引："2026-10-12 评审后按 T7 更正，见 docs/POLLUTANT_PATHWAY_S5B_HBUCKET_T7_DELIVERY_2026-10-12.md"。

## 3. 红线

1. **判分零触碰**：不调用 evaluate_scientific/s5b_scoring，不改 `src/` 任何文件；audit.py 只读引用。
2. **金标纪律**：rescore_detail 统计计数可进交付物；金标结构/SMILES/参考图内容零外带 docs/ 与最终消息；不把金标文件复制进新目录。
3. 零模型零网络零 LLM；`synced/` 与既有 `analysis/` 产物只读（重跑 funnel 输出写新文件名 `funnel_chain12_r2.json` 等，不覆盖原文件）。
4. 封存 run 只读；不 commit 不 push（主会话核对后统一提交）。
5. 数字诚实：拼不出/字段空如实 unknown；桶迁移如实列；禁止把聚合当逐题、禁止把痕迹当因果。
6. 对外数字一律带题域标签 298/RHEA 已见题。

## 4. 排障表

| 症状 | 处置 |
|---|---|
| 修复后桶账迁移超预期 | 逐 qid diff 找 payload 证据；无法解释的迁移如实列出并标 unknown，不硬归 |
| 真实批准入 disposition 里根本没有 reject/defer | 如实 F=0 并引用实际分布（哪几个枚举值各多少），不造负例 |
| rescore_detail 字段为空/缺键 | 按实际产物统计，空值计数单列，不猜不补 |
| H120 清单在重跑后变化 | 以修复后输出为准，报告两清单差集与迁移去向 |
| 交付书原文段落定位对不上 | 按语义就近替换，替换位置与前后文录进回传，不整段重写无关内容 |
| pytest 全量超时 | 先跑新测试+tests/ 下 funnel/scoring 相关子集，全量改后台跑并如实报状态 |

## 5. 回传义务（最终消息按此八项，不贴大段 JSON/金标内容）

1. 修复 diff 摘要（行级）+ 新测试用例数与结果 + 既有测试翻转清单（预期空）。
2. chain12/chain11 重跑桶账前后对照表 + 迁移题清单（如有）。
3. H120 失配形态分布表（类×题数）+ 分类判据一行/类 + qid 清单文件路径 + D2 交叉结果。
4. 候选级损耗账分布（四/五类痕迹×题数，有痕迹题数/120）+ 口径声明原文。
5. 池层对照表（桶×reason 聚合 + 池宽统计）+ reason 四分类映射表。
6. 文书更正六处的前→后文案对照。
7. known limits 清单（含 pool_layer_aggregate_only、未测真模型排序等）。
8. 产物文件路径清单（analysis/ 新文件、/tmp 工作目录、修改的 docs/）。
