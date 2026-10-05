# v4.3 hit@1 → 60% 执行索引（teacher Huang 指导书拆解）

> 状态（2026-09-30）：**teacher 批复已收**（[TEACHER_REPLY_V43_HIT60_S0S1_VERDICT_2026-09-30.md](TEACHER_REPLY_V43_HIT60_S0S1_VERDICT_2026-09-30.md)）：S0/S1/T4 全部验收通过；四项裁决全下（§4 表后）；**双轨口径即时生效**（闭卷轨道 15–16%→先到 30%；60% 只挂覆盖轨道）；**口径 v3+金标体检获批立即开工（T6）**；题源 mibPOPdb 首选+EAWAG 留出（T7）；深位召回门 1+三先决（T8）；编辑路径重测加项（T9）。E3 判定已按批复改写为「无效应、不可判」并同步 S1 报告两版。
> 来源：teacher Huang 2026-09-29 指导书
> [TEACHER_PLAN_V43_HIT60_MASTERPLAN_2026-09-29.md](TEACHER_PLAN_V43_HIT60_MASTERPLAN_2026-09-29.md)
> （入仓副本，与微信原件同文）。本索引是各 HIT60 任务书的总入口。

## 1. 目标与总架构

**目标（2026-09-30 teacher 裁决双轨，即时生效，取代原单一「盲测 60%」）**：

- **闭卷轨道**（泛化能力）：基线 **15–16%**（dev 56，口径 v2）→ 里程碑
  **先到 30%** → 判定场所 mibPOPdb / EAWAG 留出盲测（题源解决后）；
- **覆盖轨道**（覆盖+排序能力）：基线 45.6%（298 post-hoc 参照，
  **不得单独引用**）→ **60% 只许挂此轨**（S3 语料扩充后新考 + 泄漏审计）。

原「真 60% = 闭卷」定义作废（闭卷 15%→60% 是 4 倍差距，teacher 原文
语义：写了也是自欺）。S3 地位不变——后备，不因题源红灯提前；若启用，
口径降级声明同步发生。

指导书回路不变：**S0 归因划界 → S1 变更集施工 → S2 盲测判定 →
（不达标才）S3 后备降级**。

四条核心不变量全程有效（任何阶段不得违反）：

- **I1 信号源隔离**：298 只读观测、dev 集调参、盲测定论，三者永不串用；
- **I2 判决先于数据**：配对实验的判定规则先于跑分冻结（预注册）；
- **I3 gold 盲性**：gold 复核人不见模型输出；翻转 gold 须逐题理由 + 双人确认；
- **I4 多维监控**：hit@1 为主指标，hit@3/5、空答率、spurious 率同步盯。

## 2. 任务书清单与依赖

| ID | 任务书 | 内容 | 执行方 | 依赖 | API 预算 | 完成门 |
|---|---|---|---|---|---|---|
| T0 | [TASK_V43_HIT60_S0_BOUNDARY_AND_REVIEW.md](TASK_V43_HIT60_S0_BOUNDARY_AND_REVIEW.md) | L1–L5 精确边界表 + 人工化学复核清单与流程 | 程序部分**已完成**（[S0 报告](HIT60_S0_BOUNDARY_REPORT.md)）；复核**已闭环 2026-09-29**：签字 **44/56**（三方一致 43 ∪ suspect 6 补签，详见 `manual_review/CONSOLIDATED_REVIEW_SUMMARY.md` 决策日志）、6 道 suspect 溯源坐实"出题口径漏列共底物"（金标不动，口径登记 `manual_review/gold_convention_registry.md`）、门禁误杀案（b978fd0b）坐实且**修复合入**（T4）；剩 12 道 B 分歧题（内含 5 undetermined）——2026-09-30 用户拍板**挂起，等 teacher 裁决**（非翻转项，不阻塞）。**T0 完成** | 无 | 0 | ✅ 边界表+复核闭环；S1 可开工 |
| T1 | [TASK_V43_HIT60_S1_CHANGESET.md](TASK_V43_HIT60_S1_CHANGESET.md) | dev 集冻结 + 判定预注册 + E1 协议/E2 噪声/E3 窗口/E4 模型四臂 + 止损门 | **四臂全部判定完毕 2026-09-30，止损门坐实**（E1 臂详情 [ARMS_C0_E2_E3_RESULT.md](../reports/phase_s1_hit60/ARMS_C0_E2_E3_RESULT.md) §10）：C0 基线 @1≈15–16%（闭卷）；**E1 rejected**（净赢 +2/+1 < 3 门线）——关键发现：E1 机制在 dev 上**无承载面**（48 调用=42 novel+3 analogy+仅 3 rank，S0 池级前提 L1-rank/L2-rank 在闭卷卷不成立；非机制证伪）；E2/E3 亦 rejected；累计 +2.7pp < +8pp。费用记账 ¥21.18/¥50（另有作废批 ≤¥6 占位：真实账单 2026-09-30 核定**不可回填**，见 [RUN_JOURNAL.md](../reports/phase_s1_hit60/RUN_JOURNAL.md) §11）。E4 等五模型裸测。**[S1 收官报告](HIT60_S1_CHANGESET_REPORT.md)（+通俗版）已落盘 2026-09-30**，含 coverage_stat 三处归因修正（E3 载荷层 no-op 等） | T0 ✅；D1 ✅ D2 ✅ D3 等裸测 | <¥50（记账 ¥21.18） | ✅ 止损结论已产出；S1 冲刺结束；**结论已随 2026-09-30 teacher 回信上报（四项待裁决）** |
| T2 | [TASK_V43_HIT60_S2_BLIND_TEST.md](TASK_V43_HIT60_S2_BLIND_TEST.md) | 新题卷 100–150 盲测：先引擎基线后 agent；298 同批 post-hoc 参照 | ⚠️ **preflight 红灯（2026-09-29）**：B1 重叠/泄漏排除后盲测预留=0；RHEA broad-87 有 84/85 题"题面→金标"直接命中 v1 检索语料（结构性泄漏，对以 v1 为底的系统不构成盲测）；BRENDA 213 未修复维持排除；放宽口径也只有 77 可用。**已裁决（2026-09-30 teacher 批复 §三.①）**：首选 mibPOPdb + EAWAG 留出差集核查（两路见 T7）；ECREACT 后置情报储备、BRENDA extra-213 不修；两路不达回报缺口再议放宽。。审计留痕与重算脚本在远端 `v43_hit60_d2_question_assembly_20260929/` | T1 过止损门 + 版本冻结 + 题源解决 | ¥10–20/模型 | 盲测报告；hit@1 ≥ 60% 判定（唯一判定场所） |
| T3 | [TASK_V43_HIT60_S3_FALLBACK.md](TASK_V43_HIT60_S3_FALLBACK.md) | 语料扩充 + 口径降级（「覆盖+排序」） | 程序 | 条件触发：T1+T2 不达标且拍板启用 | 另计 | 双口径报告（数字与声明同步改） |
| T4 | [TASK_V43_HIT60_PARALLEL_FABLE5_P1.md](TASK_V43_HIT60_PARALLEL_FABLE5_P1.md) | fable5 三 P1：FileRateGate 竞态 / 证据卡 schema 版本 / 拒因枚举解耦；+门禁误杀修复（b978fd0b 已坐实） | **已完成 2026-09-29**（评审原文 [FABLE5_REVIEW_RESPONSE.md](FABLE5_REVIEW_RESPONSE.md)；修复报告 [P1A+P1B](FABLE5_P1A_P1B_FIX_REPORT.md)、[P1C+门禁](FABLE5_P1C_GATE_FIX_REPORT.md)；全仓 456→**508** 绿（T4 时点；E1 施工后最新 541）；改动留在工作树未提交；核查发现评审 P1a/P1b 两处在 HEAD 已部分过时，实修缺口=原子写入+并发测试、消费端版本校验） | — | 小 | ✅ 三 P1+门禁修复合入 + 回归绿；不背指标 |
| T5 | （无任务书，单独排期） | 任务七：192MB 数据出库、恢复 enzyme_cage_v1 / 主线资产 | 用户排期 | **死线已定（teacher §三.③）：下次主线交付前整改方案必须送审（方案级）** | 0 | 资产恢复；不占本回路 |
| **T6** | [TASK_V43_HIT60_S15_DETERMINISTIC_FIX.md](TASK_V43_HIT60_S15_DETERMINISTIC_FIX.md) | **判分口径 v3（component-aware）+ 金标体检**（性质=判分勘误非策略臂）：全主产物组分命中=对、partial 单列、禁 any-of；错配注入测试；v1→v2→v3 对齐附录；dev 六批+C0 重刷封存、298 post-hoc 双轨（≈149 参照）；金标 **quarantine**（剔分母不改题卷） | 程序（零 API）——**已获批立即开工**（teacher §五.4） | 无；规则判据过 [mimo 评审](mimo_gold_rules_review_request.md)（采信到程序互证为止） | 0 | 预注册四条件+重刷封存值+quarantine 表+口径 v3 报告（+通俗版） |
| **T7** | [TASK_V43_HIT60_S2PRE_POOL_RESCUE.md](TASK_V43_HIT60_S2PRE_POOL_RESCUE.md) | **题源两路**（teacher §三.①）：mibPOPdb 首选（许可/泄漏审计/**路由占比选题指标**/金标人工核对冻结）+ EAWAG 包级差集留出核查；ECREACT 后置情报储备、BRENDA extra-213 不修 | 程序（零 API） | 无 | 0 | 两路评估+冻结流程预案；两路不达→回报缺口 |
| **T8** | [TASK_V43_HIT60_S1R2_GENERATION_ARMS.md](TASK_V43_HIT60_S1R2_GENERATION_ARMS.md) | **深位召回（门 1 零 LLM 先行 + 三先决条件）+ novel 守恒过滤/自排序合并设计（REAP 可选辅助）**；失败分支预声明（门1不过退纯检索优化） | 门 1 零 LLM（口径 v3 冻结后做）；付费臂=预注册+用户授权 | T6 口径 v3 冻结；守恒判据过 [mimo 评审](mimo_conservation_rules_review_request.md) | 深位付费臂帽发车另定 | 门 1 召回率报告 → 预注册冻结 → 臂判定 |
| **T9** | [TASK_V43_HIT60_T9_EDIT_REPLAY.md](TASK_V43_HIT60_T9_EDIT_REPLAY.md) | **编辑路径修复后重测**（老师侧加项，零 LLM）：旧 8 题+dev analogy 题确定性重放，回答「编辑路径从全灭能否活过来」；数据回执口，类比线封存不解 | 程序（零 LLM，随时可插） | 无 | 0 | 重放对照表+回执报告（+通俗版） |

## 3. 与既有文档的关系

- **S0 的归因部分已完成**：复测丢分归因
  [EC298_PD_RETEST_LOSS_ATTRIBUTION.md](EC298_PD_RETEST_LOSS_ATTRIBUTION.md)
  （产物 `reports/phase_d/retest/loss_audit/`，7 文件带 SHA 清单）就是指导书 S0
  要的"本轮 C0 162 题失分归因"。T0 只做剩余两件事：精确边界表 + 人工复核。
- **旧 Phase E 任务书**（[TASK_V43_EC298_PHASE_E_POST_RETEST.md](TASK_V43_EC298_PHASE_E_POST_RETEST.md)、
  [TASK_V43_PHASE_E_ISOLATED_DEV20_FINAL_EC298.md](TASK_V43_PHASE_E_ISOLATED_DEV20_FINAL_EC298.md)）：
  dev20 开发线。指导书 S1 把 dev 集改为 D2 拼合集（50–100 题）后，两文的
  单步口径、根节点一跳评分器、实验与采用门**方法论沿用到 T1**；dev 集本体与
  E1–E5 编号以本套任务书为准，两文视为被 T1 取代（不删除，引用以本索引为准）。
  dev20 误启动批次（`runs/phase_e_dev20_C0/`）继续封存：不续跑、不评分、不并入效果表。
- **Phase F 草案**（[TASK_V43_EC298_PHASE_F_HIT1.md](TASK_V43_EC298_PHASE_F_HIT1.md)）：
  F1a/F1b/F3a 的臂设计可作 T1/E1 施工参考；其 §0 红线全部继续有效。
  F 轨道并入 T1，不再单独发车。
- **类比线（D1 通道）**：三轮实证未证增益，正式封存——发布默认
  `reactant_similar_enabled=false`，本回路任何臂不得顺手打开。
- **多步路径（9–18 裁决线）**：下一阶段，不与单步指标混谈。

## 4. 拍板项（指导书 §6）

| # | 决策 | teacher 建议 | 阻塞谁 | 状态 |
|---|---|---|---|---|
| D1 | 双口径目标（盲测才算数，298 只作参照） | 确认 | T1/T2 报告口径 | **已拍板**（2026-09-29 确认：S2 盲测卷为唯一判定依据，298 仅回归参照、分开报告不混分） |
| D2 | 盲测/dev 题卷拼合（BIOSYSMOdb 121 拆单步 + RHEA/BRENDA 留出）；涉陈浩然线资产共享 | 可行，两人知会 | T1 dev 集冻结、T2 题卷 | **已拍板+已回复**（[陈浩然回复](REPLY_TO_GONGSAI_V43_D2_ASSET_SHARING_20260929.md)）：资产全在 Chenyu 只读可取（B1 冻结包 SHA `6858c165…`，121 路径/533 步/460 反应）；B1 可立即作题源；**盲卷冻结前须 D2 preflight**（三源统一去重+重叠审计）；BRENDA 213 不可直接用；许可 CC BY-NC-SA 4.0 |
| D3 | 模型选型等五模型裸测结果再定（与 E1 捆绑同轮） | 等 | T1/E4 臂（E1 可先用当前模型开工） | **继续等**：裸测未交付（G5 仅三题 smoke 且 FAIL——4 题 length 截断；改四家族一款：qwen3.8-max / deepseek-v4.1-flash / ZHIPU GLM-5.3 / kimi-k3，max_tokens=65536；G5-R2 未跑） |
| D4 | 74→刷新后人工复核的执行人 | 先定人再启动 | T0 的人工复核部分（全方案唯一非程序瓶颈） | **已拍板**（2026-09-29：用户自任主复核；翻转金标的第二确认人待定名） |

- **teacher 批复已收（2026-09-30）**：[TEACHER_REPLY_V43_HIT60_S0S1_VERDICT_2026-09-30.md](TEACHER_REPLY_V43_HIT60_S0S1_VERDICT_2026-09-30.md)，
  SHA256 `3e804e88a04fd8e000db5e572221172c72eb8a2e17bf12e7d3965541ce3c481d`
  （批复原文自称 approval_source，学生侧按用户指示执行视为确认）。四项裁决：
  ① 题源：**mibPOPdb 首选**（人工核对后冻结）+ EAWAG 未入 v1 语料 package
  差集留出核查并行；ECREACT 后置情报储备；BRENDA extra-213 不修；两路
  不达回报缺口再议放宽。② 60% 口径：**拆双轨即时生效**（§1）。③ 任务七
  死线：**下次主线交付（下次送审包）前，任务七整改方案必须送审**（方案级，
  不绑日历绑事件）。④ E4 不催：裸测按陈浩然线节奏、只作机制登记不承载
  冲刺；模型选型在 dev 集系统内配对补足。
- **提醒项登记（teacher §八，待办不遗忘）**：T6-2 旧盲测成色复查（v3.3
  72.2% vs BioTransformer 50% 的 18 例，按闭卷方法学重审题源-语料重叠）；
  题域标签（已入 AGENTS.md）；12 道 B 分歧题待 mibPOPdb 金标流程建立后
  回看；mimo 评审采信到程序互证为止（已入 AGENTS.md）。

## 5. 数字勘误登记（以 T0 重算落盘为准）

- 指导书引"引擎@5 209 vs agent 186"：**209 是引擎 hit@10**；引擎 hit@5 = 193。
  L3（引擎有 agent 无）按 @5 与 @10 两版都算，口径在 T0 冻结。
- 指导书 L2"直通答错 ~39"为首跑口径；复测归因 selected_wrong = 44
  （recorded 直通 31 + rank 选卡 13），T0 以复测为准。
- 指导书"74 题复核（27+39+8）"为首跑口径；复测刷新后预计约 56
  （rank 选卡 13 + recorded 31 + 编辑被拦 12），以 T0 落盘清单为准。
- 三档预算（保守/基准/乐观 +27/+40/+53 → 54.7%/59.1%/63.4%）是规划推演，
  不是承诺；基准情形差的一口气由 E4 模型升级或 S3 兜底补上。

## 6. 其他并行事项（不占本回路）

- 陈浩然线 G4–G6 照既有授权推进；
- 任务七（T5）单独排期但要有死线；
- 多步路径、类比线见 §3。
