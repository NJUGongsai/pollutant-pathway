# S5b H 桶 120 题逐题归因（T7）交付书（2026-10-12）

> 任务来源：一轮评审 [S5B_CHAIN12_LOSS_ATTRIBUTION_ROUND1_REVIEW_2026-10-12.md](S5B_CHAIN12_LOSS_ATTRIBUTION_ROUND1_REVIEW_2026-10-12.md)（P1 题级主桶≠候选级损失账 / P2 漏斗工具 F 桶缺陷 / §6.1 拒因分类 / §8 小勘误）→ 主会话起草任务书 [TASK_S5B_HBUCKET_ATTRIBUTION_T7_2026-10-12.md](TASK_S5B_HBUCKET_ATTRIBUTION_T7_2026-10-12.md) → 单实施子代理执行 → 主会话逐项核对（数字独立复算、diff 抽查、金标外带扫描、红绿）。题域标签：**298 / RHEA 通用酶学 / 已见题**，全部结论不外推 dev。

## 0. 一页结论

H 桶 120 题（已提交但不匹配）逐题归因闭合，**失配形态单一指向供给**：

| 失配类 | 判据（程序口径一行） | 题数 |
|---|---|---:|
| C1 单 gap·unmatched | 唯一必要乘积参考节点零严格命中 | 64 |
| C2 单 gap·cn_only | 唯一必要乘积参考节点仅达 CN 同值层（分子式同、结构层未命中） | 42 |
| C3 双 gap·双 unmatched | 两个乘积参考节点均零命中 | 12 |
| C4 双 gap·混合 | 一 unmatched 一 cn_only | 1 |
| C5 双 gap·双 cn_only | 两节点均仅 CN 层 | 1 |

三条硬事实（全部 120/120 或全批核对）：

1. **没有一题是"覆盖错配"**：H120 全体 `coverage_mismatch_events=0`、`matched_events=0`、`strict_hit_positions` 空——丢分形态全部是"该给的必要乘物没给对"（unmatched/cn_only 型），不是"多写了参与物"（那是 partial-superset 的形态）。**这直接支持 RR A/B 供给线对症**：新反应供给补的就是"零命中"的产物。
2. **D2 在 H 桶几乎不在场**：指纹题 1/120（C1 类），占比 0.8%，低于 strict 6.2% 与 partial 9.3%——H 桶丢分不是 D2 双刃造成的。
3. **候选级损耗痕迹并存但不为主**：21/120（17.5%）有 ≥1 痕迹（method_failed 12 题、novel 预校验拒 9、调度/预算 defer 1、dedup 0、准入 reject/defer 0）；其余 99 题无任何候选级失败/截断痕迹。口径（评审 P1 原文）：痕迹存在不证明丢了正确候选，也不能反推零损失；H120 仅支持"已提交集合在当前尺子下未严格覆盖"。

池层聚合对照（pool_layer_aggregate_only）：H 桶编译存活每题 0.45（中位 0）< strict 0.78（中位 1）；`mapping_enumeration_truncated` 拒因 H 桶题均 0.92 vs strict 0.13（聚合相关、不作因果解读）。cn_only 42 题单列观察点：分子式同层命中、结构层未过——可能与表示/互变异构身份差异有关，属下一步（谱系 A/B + 表达层）验证面，本单不下结论。

## 1. 任务执行表

| 项 | 结果 | 关键证据 |
|---|---|---|
| 漏斗工具修复（评审 P2） | 枚举 `rejected/deferred`→`reject/defer`（对齐 audit.py:327-333）；classify() 补 F 分支（最深阶段语义、E/G/D 零翻转）+ 交集标志 `has_admission_reject_or_defer` | git diff；评审原始负控复验：修复前 计数 0+主桶 I → 修复后 1+F |
| 新测试 | 3 用例（reject 负控 / H+并存痕迹 / retain_conditional 正控）全绿；全量 not slow **2101 passed / 0 failed / 16 deselected**（基线 2098+新增 3，零翻转） | tests/test_s5b_offline_funnel_controls.py |
| 重跑对照（r2，r1 零覆盖） | chain12：A2 B3 H120 F=0、逐 qid diff=0；chain11：A4 B2 E8 H141 F=0、diff=0 | analysis/funnel_chain12_r2.json 等；F=0 有实际分布支撑（chain12 准入 disposition 全批=retain_conditional 1478+None 21，reject/defer=0；chain11=1423+84） |
| H120 失配形态归因 | 五类闭合 120（表见 §0）；共性 120/120；15 题复合形态（部分乘物命中其余缺失）；D2 交叉 1/120 | analysis/hbucket_attribution.{json,md} |
| 候选级损耗账 | 21/120，四类痕迹+组合分布 | 同上 §4 |
| 池层对照 | 三桶×reason 聚合表+池宽；拒因四分类**分析性映射**（合理不适用/表达未支持/工具缺陷/超时与身份），工具缺陷档无 reason 级个案（需逐候选谱系，留 A/B 批） | 同上 §5 |
| 一轮交付书更正 | 六处+同族一处（前→后备份节留存），评审 §3/§5/§8 建议文案逐处落地 | docs/S5B_CHAIN12_LOSS_ATTRIBUTION_ROUND1_DELIVERY_2026-10-12.md §5 勘误备份 |

## 2. 对下游决策的含义（不新增结论，只摆方向）

- **RR A/B（T5/兄弟线）**：H120 形态=必要乘物零命中为主（C1/C3/C4 共 77 题）→ 新反应供给直接对症；cn_only 42 题靠供给能否救未知（若为身份表示差异，供给新反应救不动）。
- **排序线**：维持更正后口径——机械规则全负不直接上线，真模型净增 pending，暂缓=资源优先级。
- **编译墙**：拒因聚合已按 reason 摆开（聚合级）；逐候选级归因等带谱系批（pool-policy-6 起有 candidates 行）。

## 3. 主会话核对记录

1. 改动范围=允许清单（funnel 脚本/新测试/一轮交付书/analysis r2 与归因产物）；兄弟会话活文件 docs/HANDOFF_RR_AB_HPC_2026-10-12.md（16:31，RR A/B 发车交接）不在本单范围、未纳入提交。
2. 关键数字独立复算全对：五类 64+42+12+1+1=120；D2 1；coverage 合计 0；痕迹 21/120（11 mf+8 novel+1 mf+novel+1 defer）；disposition 1478+21。
3. 金标外带扫描：归因 md/json 仅含 qid、计数、状态枚举与口径文字，零 SMILES/结构内容（正则命中行人工复核全为说明文字）。
4. 新测试本机复跑 3 passed；判分代码零调用（只消费 T3 已落盘 rescore_detail.json）。

## 4. 产物索引

- 任务书：docs/TASK_S5B_HBUCKET_ATTRIBUTION_T7_2026-10-12.md
- 修改：scripts/s5b_offline_funnel.py；docs/S5B_CHAIN12_LOSS_ATTRIBUTION_ROUND1_DELIVERY_2026-10-12.md（勘误）
- 新增：tests/test_s5b_offline_funnel_controls.py
- 分析产物（gitignored，reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/）：hbucket_attribution.{json,md}、funnel_chain12_r2.{json,_summary.md}、funnel_chain11_r2.{json,_summary.md}、funnel_summary_r2.md
- 工作目录（易失）：/tmp/s5b_t7_hbucket/

Provenance：离线分析零预测模型零网络零 LLM；判分代码零调用零改动，只消费 T3 冻结判据复算明细；金标仅统计计数间接体现、结构/SMILES 零外带；封存 run 与 synced/ 只读、r1 产物零覆盖；不 push。

已知边界：pool_layer_aggregate_only（真实批无逐候选谱系，四分类映射为分析性非权威）；痕迹≠因果；D2 交叉为关联非因果（沿用 t6_d2_contention.md 边界）；cn_only 亚型机理未判定；真模型排序净增 pending。
