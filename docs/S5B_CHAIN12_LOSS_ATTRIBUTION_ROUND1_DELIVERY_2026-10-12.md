# S5b chain12 丢分归因第一轮交付书（2026-10-12）

> 任务来源：GPT chain11 丢分分析（v44/docs/SYSTEM_PROBLEMS_AND_298_LOSS_ANALYSIS_2026-10-12.md）→ CC 六项拍板（双线并行/先干不受影响项/P0+P1 五项/漏斗两步走/重排先零模型/谱系先行 A/B 带账）。主会话派单、六代理实施、主会话逐单核对。题域标签：**298 / RHEA 通用酶学 / 已见题**，全部结论不外推 dev。

## 0. 一页结论

chain12（D2+显式氢墙等多因子合批）判分 **92/126/130，U=130、L=0**，失分 206 题全账：

| 失分构成 | 题数 | 可救性 |
|---|---:|---|
| 后位答案（rank2=23 大头） | 38 | 排序线——**T6 证明机械规则全负**，真模型期望收益薄 |
| partial：superset（诚实多写） | 40 | 现行口径结构性不可转 strict（判分语义，非缺陷） |
| partial：partial_subset（真缺物种） | 3 | 可修缺口 |
| 无候选/准备失败 | 5 | 小缺口（2 无候选+3 准备失败） |
| **已提交但不匹配（H 桶）** | **120** | **主战场：供给的反应内容不对，非执行链损耗** |

执行链零损耗（去重/落选/准入/预算四桶全 0）；293/298 题都有提交、三组宽度无差；池层 96% 编译拒绝（5316/5551 rejected）首次可见。**119 的净增 27 主力只能来自 H 桶的新反应供给（RR A/B、编译拒因补能力），排序与 partial 线合计贡献有限。**

## 1. 任务执行表（六单+两事件，全部主会话核对）

| 单 | 结果 | 关键证据 |
|---|---|---|
| 数据同步 | chain11/12 白名单产物 81MB 回本地，md5 抽查全过，金标零拉取 | reports/ppv1_s5b/*/synced/ |
| chain12 对账 | 六项聚合数全对上；迁移矩阵/退步清单/归因指纹 | [对账报告](S5B_CHAIN11_TO_CHAIN12_RECON_2026-10-12.md)（含勘误节） |
| mimo r35 | 化学面放行，无可疑命中；P1-P4 优先级建议 | [回应](mimo_ppv1_chem_review_response_r35.md)+[验证记录](MIMO_R35_EXEC_VERIFY_2026-10-12.md) |
| T1a 池层谱系 | pool_diagnostics.candidates 逐候选行，pool-policy-6；v43 提交 **0e463335** | [交付书](POLLUTANT_PATHWAY_S5B_POOL_LINEAGE_T1A_DELIVERY_2026-10-12.md) |
| T2 拼账 | 125=2+3+120 闭合；chain11 155 对照 | analysis/funnel_summary.md |
| T3 重跑三拆 | 298/298 对齐；40 superset/3 sub/0 身份；自由基 11 阳性 | analysis/partial_breakdown.md |
| T6 重排摸底 | 机械规则全负（最好 −2）；D2 竞争 4/14；hwall 位点 17/20 醇→羰基 | analysis/t6_rerank_matrix.md 等 |
| T4 v44 同步 | 三件套+T1a 全入 v44（提交 af0fd26）；RR 通道同 schema 谱系行 | v44 git log af0fd26 |

## 2. 当日勘误（2 处，均已打进原文档）

1. **D2 指纹口径**：题级 8 strict/4 partial/1 uncovered（多数 D2 陪跑+他通道命中）vs 事件级 35 新 strict 命中事件 0 道来自 D2——两口径都成立，原行文"零道进 strict"省略"新"字，已勘误；NC-12 熔断经命中事件 coproduct_participants=[] 验证安全。
2. **mimo r35 请求文档**沿用上述松表述；mimo 回应原文不动，采信以勘误为准（其 M3/M5 结论依据事件级数字+设计线，不受影响）。

## 3. 待 CC 拍板 / 协调（三项）

| # | 事项 | 建议 |
|---|---|---|
| 1 | **真 RankLLM 上不上** | **不上**（或最低优先级）：机械规则全负+现有排序已强信息量（反向对照崩到 6）；资源转向供给线 |
| 2 | **RR A/B 发车基线协调** | 兄弟会话已将 A/B 预注册钉到 b7be4d1 并备远端重传；按"谱系先行带账发车"拍板，**A/B 应再钉 af0fd26（含 T1a 谱系）重 build 后发车**——需与兄弟会话协调避免双发车/旧基线发车 |
| 3 | mimo P4 hwall 边界硬化（自由基硬负控+H 消费披露） | 下轮预注册材料已备（11 阳性事件+位点统计），建议随 A/B 后首轮实施 |

## 4. 产物索引

- 任务书：docs/TASK_S5B_POOL_LINEAGE_T1A / TASK_S5B_OFFLINE_FUNNEL_T2 / TASK_S5B_PARTIAL_BREAKDOWN_T3 / TASK_V44_SYNC_T4 / TASK_S5B_RERANK_PROBE_T6（均 2026-10-12）
- 脚本（随本交付提交）：scripts/s5b_offline_funnel.py、s5b_offline_rescore.py、s5b_t6_rerank_probe.py、s5b_t6_hwall_sites.py
- 分析产物（gitignored，reports/ppv1_s5b/chain12_…/analysis/）：funnel_*、rescore_detail、partial_breakdown、radical_scan、t6_*；chain11 侧 funnel_chain11.*
- 远端证据：/tmp/s5b_t1a_lineage、/tmp/s5b_t2_funnel、/tmp/s5b_t3_rescore、/tmp/v44_redgreen_t4（易失，关键结论已入本文档与各交付书）

Provenance：全程零模型零网络零 LLM（判分重跑为冻结判据程序复算）；金标仅判分进程内消费、零外带零入仓；封存 run 只读；不 push。
