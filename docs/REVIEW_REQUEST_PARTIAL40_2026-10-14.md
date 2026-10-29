# REVIEW REQUEST — chain12 40 题 superset partial 现况（mimo 化学面 + Codex 工程面双评审，2026-10-14）

> 请求方：主窗口（CC 拍板「把 40 道题的情况写成 md 让 codex 和 mimo
> review」）。本文自包含；两节评审问题分别对应两个评审通道。
> 题域标签：**298=RHEA 通用酶学/已见题**，与 dev 不互推。
> 红线：**零金标、零题面、零逐题内容**——全部数字为判分面聚合计数
> 与已裁定规则级表述；模拟数字≠实施成绩。
> 采信原则：评审独立性不做背书，结论采信到与程序证据互证的程度；
> 执行类断言（标注处）待验证后采信。

## 一、现状全景（chain12，冻结判分）

chain12 主口径 hit@1/3/5=**92/126/130**；桶 strict130 / partial43 /
uncovered125（三桶合计 298）。partial 43 三拆（T3 离线重跑实证）：
**superset 40**（40/40 事件带 coproduct 参与物，D2 诚实保留语义的
直接产物）+ partial_subset 3（缺物种，结构性不可救）+ 身份差异 0。

**本评审对象 = 40 题 superset partial**：事件两侧参与物覆盖为
superset 形态（`from_states ⊆ reactants ∧ to_states ⊆ products` 且
两侧存在 extras），维持 partial 桶。失分机制 = "多写了参考里没有
的参与物"——不是化学判错，是判分面"超出可核验范围"。

## 二、40 题拆分与去向（裁定链已走完，待兑现）

| 子集 | 题数 | 多写的身份 | 去向 | 状态 |
|---|---:|---|---|---|
| **纯簿记袋** | 16 | H₂O/H⁺/Pi/PPi | 进 criteria-v2 豁免面（teacher b 档裁定+mimo r36 有条件放行+冻结批复三项全批）；严格三谓词+元素账后 **N1''=13**（剔 3 道"无中生水"=反应物侧 O 计数 0 而产物侧有水，pred2 拦截实证） | 判分侧已实施（84a9eb4）；**存量批解锁 0**（见 §三）；模拟下界 hit@1 +3 / hit@3 +9 / hit@5 +0 |
| **机制共底物** | 24 | NH₃/O₂/H₂O₂/OTHER（老师裁定"辅因子与机制共底物一律不进 v1 清单"） | **保持拦截（不救）**：参考图 root-only 构图（参考边只保留 root+principal_product，不保留共底物节点）⇒ 金标侧对这些参与物**无信息可核**；豁免=宣布机制成分不重要=洗白 | 裁定冻结；诚实落点=partial（"超出可核验范围"非化学判错） |

上位裁定链：teacher 裁定（`TEACHER_DECISION_PPV1_T1_COSUBSTRATE_TIER_2026-10-12.md`，b 档收窄）→ CS2c 探针 N1=16 → mimo r36（`mimo_ppv1_chem_review_response_r36.md`，九条件）→ 补证 N1''=13 → 冻结拍板包（`TEACHER_T1_FREEZE_DECISION_PACKAGE_2026-10-13.md`）→ teacher 批复三项全批（`TEACHER_REPLY_PPV1_T1_FREEZE_APPROVAL_2026-10-13.md`，SHA 76c4f7d2…）。豁免清单（冻结）：产物侧 H₂O/H⁺/Pi/PPi + 反应物侧仅 H₂O/H⁺（方向限定防磷酰化塌缩）；辅因子硬拒绝族（NAD(P)/ATP/CoA/FAD/THF/O₂/NH₃/HCN/…）正面清单。

## 三、为什么 13 题一题还没兑现（关键缺口）

v2 三谓词之一 pred1（记录已声明）要求事件载荷带**声明链**：
`event.hypothesis_id → hypothesis.provenance_refs →
payload.provenance_records 行（record_id 匹配）→ 行 payload 的
record_equation`。实测（84a9eb4 交付）：chain12 全 298 载荷的
`provenance_records` 行数=0、hypothesis `provenance_refs` 非空数=0、
`put_provenance` 零调用方——**41 个 superset 事件声明链全
no_chain ⇒ pred1 unknown ⇒ fail-closed 零豁免**（探针的 13 用了
题卷侧数据，判分面红线不可消费=实现更诚实）。

兑现钥匙=**生成侧声明链发射**（事件提交时把来源记录方程写进
provenance，消费契约已冻结在 v2 预注册 §二.1）——正在 C 线实施轮
同轮装配（与共底物伴生供给同一数据源：analog 候选装配时的
record_equation 声明）。v2 生效链还差最后一轮 Codex 终裁（appearance
首次消费闭合修复在途，前序 P1/P2 已终裁关闭）。

## 四、关联集合（防混淆，如实登记）

- **C 线供给解锁面（≠本 40 题存量）**：COSUB-GATE 454 行 167 题
  （analog 模板共底物袋被元素门拦）语义 a 伴生供给解锁 45 行/35 题
  （探针实心口径）——其中 11 行/11 题纯 H₂O/H⁺/Pi/PPi 袋（新事件
  将走 v2 豁免，与存量 13 题同一判据）、34 行/28 题机制类（新事件
  走分档诚实 partial，与存量 24 题同一逻辑）。
- **参考侧 root-only 构图**：298 张参考图全量核过（参考侧聚合探针
  2026-10-14）——这是"金标无信息可核"论断的实证基础，对存量 24 题
  与 C 线新事件同源成立。
- 供给解锁面≠hit 预测（位次/选择/提交折损未知）；13 题模拟下界
  ≠实施成绩（探针仅覆盖 43 道 partial 桶，已有 strict 题位次效应
  未模拟）。

---

## 五、mimo 评审问题（化学判据面）

**Q1（拆分公允性）**：16 簿记袋 / 24 机制共底物的拆分与豁免面
（产物侧 H₂O/H⁺/Pi/PPi + 反应物侧仅 H₂O/H⁺）边界，化学上是否
公允？（r36 有条件放行后新增证据=参考侧 root-only 构图实证——
该证据是否改变你对边界的判断？）

**Q2（24 题不救论断）**："机制共底物多写 ⇒ 金标无信息可核 ⇒ 诚实
partial"的论断在 root-only 构图实证下是否完全成立？有无你认为
应该重开的身份（例如某 OTHER 家族实际是簿记噪音）？

**Q3（跨集合一致性）**：存量 40 题与 C 线供给解锁面（新事件）走
同一豁免/分档体系，语义上是否一致（同一把尺子量新旧两种来源的
共底物参与物）？

**Q4（预期管理）**：13 题的 +3/+9/+0 模拟下界与"修尺子不修分数"
的表述是否如实（不包装为进展）？

## 六、Codex 评审问题（工程/程序面）

**Q1（声明链可满足性）**：pred1 消费契约（v2 预注册 §二.1）在
C 线发射器实现下是否可满足且 fail-closed 完整（声明链悬空/方程
缺失/条目不可解析 ⇒ unknown ⇒ 不豁免——四路径是否闭合）？

**Q2（存量解锁 0 路径）**：no_chain ⇒ pred1 unknown ⇒ 零豁免的
判定路径是否正确执行（chain12 只读重算下 v2≡v1 逐位相同——
双口径重判证据 `v44/reports/ppv1_s5b/hpc2_a/v44_dual_caliber_rescore_v2.json`）？

**Q3（数字链可复核）**：16→13 的三谓词+元素账剔除（3 道无中生水）
与 +3/+9/+0 模拟下界的程序可复核性（探针→预注册→实现三层数字
一致性）。

**Q4（复测批接线）**：双口径判分（headline v1 + v2 敏感性并列）
在新批次的接线是否完备（criteria_v2 块含 tier 计数与豁免披露）。

## 七、两通道共同纪律

- 只读评审：可用读取工具核对仓内文档/源码/聚合 json；**mimo 无执行
  权限不得编造执行结果；Codex 可执行探针但只新增自己的报告与证据
  目录**（mimo 回应原文不落盘由主窗口搬运；Codex 报告落 docs/）；
- 不改 src/tests/既有 docs/AGENTS.md；不访问金标/题面
  （questions.jsonl、reference_graphs/、逐题 metrics、gitignored
  reports 逐题数据）；不 push；不调用外部模型（评审通道本身除外）；
- 回复格式：逐 Q 编号+意见类型标注（【化学实质】/【工程】/【口径】）
  + 总判定三选一（支持现状读法/部分支持列修正点/不支持列反对理由）
  + 不确定处写"不确定+需要什么证据"。
