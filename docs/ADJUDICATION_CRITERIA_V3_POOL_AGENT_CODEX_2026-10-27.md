# 判分口径、reaction_type 与池前 Agent：Codex 方向裁决

> **[298 域]：RHEA 通用酶学／已见题（post-hoc），不向 dev 域或未见题外推。**
> 日期：2026-10-27。评审对象：[评审请求](/Volumes/CC/Enzyme_Agent/dependingv43/docs/REVIEW_REQUEST_CRITERIA_V3_POOL_AGENT_2026-10-27.md:1)。
> 本文是方向评审，不实施、不冻结判据。统计取自请求与已有聚合文档；本会话没有独立重算，没有逐题化学复核。
> 核查 HEAD：`2aa45021897d3ec0685f35cdcf47421bec0966ee`；原请求 SHA256：`0233dff173b87a2449119f68e6f440a9851e3c86f3838da3828998efb6064e3a`。

【总裁定】**分三步：先把判分指标说清并重算旧输出，再小样本验证人话字段，最后先做排序、另行小试生成；不支持三项同时上线后把涨分归给 Agent。**

保留已定约束：新旧读数双列、保留 `transformation_ref` 并新增字段、DeepSeek、混合模式与来源标记；本裁决建议调整验证顺序，并指出新机器版本号须避开既有含义。

【Q1】结论：**有缺陷；作为“声明主产物全部命中”指标有条件成立，作为完整反应正确性不成立。**

理由：参考清单不完整，不能仅因多写参与物就判主产物预测失败，也不能反过来认定多写的都正确。必须在同一合法执行事件中，题目底物位于反应物侧、全部声明主产物位于产物侧，保留严格身份与步骤范围限制。该规则仍可能放过错误额外产物、错误共底物或未配平反应，角色、系数、机制与额外参与物的未核部分须披露 unknown。建议另设 `principal_product_hit`，保留实际 `superset` 等覆盖事实，不把它改名 `exact`；旧 v2 strict 也不等于完整化学正确。Rhea 对反应有计量及质量、电荷平衡要求，主产物命中不足以证明整条反应正确（[Rhea 官方说明](https://www.rhea-db.org/help/reaction-side-direction)）。

风险等级：**中；若宣传成完整化学正确则高。**

| 纯抽象规则边界（零真实题） | 应如何解释 |
|---|---|
| 参考 `S → {P1,P2}`；事件 E1 只产 P1，E2 只产 P2 | 不得跨事件合并成全部命中。 |
| 单事件 `S → {P1,P2,Q}`，而 Q 实际错误 | 包含规则仍命中；整条反应可能错误，Q 的正确性不能由缺失的参考信息决定。 |
| 在一个事件塞入大量猜测产物 | 固定候选数、top-k 和输出预算，披露额外产物规模；不能把“命中更多”直接当精度更高。 |

【Q2】结论：**会产生后续激励风险，完整性应独立披露。**

理由：这次只重算旧输出，不会使已经生成的反应退化。风险出现在以后据此选提示、选模型或训练时，模型可能省略难写的参与物，或堆入多个猜测。完整性、配平、执行合法性等分别报告 verified／unknown／contradicted；不完整参考无法验证完整清单时应保留 unknown。不要按参与物数量奖励“完整”，也不要为补激励恢复参考本来不支持的恰好相等要求。

风险等级：**中。**

【Q3】结论：**值得做，先小样本配对验证。**

理由：把反应语义写成人话是可用特征，本身不构成作弊；风险是标签错误、答案泄漏及模型过度信任标签。标签只用推理时合法可见的候选信息生成，优先可靠元数据，不得用参考答案、判分或翻转结果；“加一个 O”不足以直接认定羟基化。冻结两级标签、来源、命名版本与置信度，无法可靠命名就写 unknown。用同模型、同池、同序、同预算的有／无标签配对比较，先筛查明显损害；小样本不能认证细小提升。IUBMB 按整体反应分类，需考虑底物、产物及供受体等信息，分类名也不证明机制（[IUBMB 官方建议](https://iubmb.qmul.ac.uk/enzyme/advice.html)）。

风险等级：**中。**

【Q4】结论：**混合模式可行，但先验证排序，生成放到隔离小试；干跑校验必要且不足。**

理由：8.6% 是在 140 道失分题上把参考反应逆向编译为协议的“可执行且产物正确”联合成功率，不是 DeepSeek 前向生成率或干跑通过率；34 道 PARTIAL 中有多少可执行也须另计，不能直接换算。新反应须复用既有 validate、execute 与 audit，并核对自称由编辑生成的全部产物组分与实际执行一致，其余声明参与物另列依据及未核范围；可执行仍不证明酶学可行，未核部分保持 unknown。首次排序保留全部原池成员，不强凑五条、不先裁剪；生成失败去重后回退，题目仍留在固定分母。保留 `from_database/synthesized`，同时保留原有来源细分和改写记录，数据库候选被实质改写后不能只沿用旧证据。现有流程已允许 novel 池外提案，应先核实新增 Agent 的增量职责，避免只是重复调用同一模型。

风险等级：**高（混合生成）；中（保留成员的排序）。**

【Q5】结论：**分三步，用最少改动保留可归因性。**

理由：A 可以对同一份旧输出重算，零模型调用即可与 B/C 分开。B/C 用固定样本的配对比较，不必铺开完整多因素试验。每步只改一个待检因素并保留失败；若坚持单臂直上，只能报告端到端探索性变化，不能把效果因果归给 B 或 C。

风险等级：**中；三项同时上线且宣称分项收益则高。**

| 阶段 | 最小动作 | 固定项与验证口径 |
|---|---|---|
| A：先定指标 | 对固定旧输出用新旧规则重算；同时零模型调用核查候选 ID → 去重 → `effective_rank` → 提交顺序。 | 保留旧输出与封存 run；版本隔离、同事件全覆盖、严格身份与步骤范围不漂移；主产物命中与完整性分列。 |
| B：验证人话字段 | 按空池、池大小等非答案特征预先选 40–60 题，有／无标签配对筛查。 | 同模型、同候选成员、同序与同预算，仅字段不同；标签先冻结，不能看本批答案后补名字；样本量仅作筛查。 |
| C：先排序后生成 | 固定 B 的标签，先对已提交事件 ID 输出新的 selector 预测文件；再在同样本验证池前排序且不改变成员；生成另做隔离小试。 | 不改旧事件时间和封存 run；单独核对排序是否传到最终输出；生成披露提案、通过、入选与新增命中率，执行失败照计。 |

所有阶段以 hit@1 为主，同时报告 hit@3／5、总体主产物命中、逐题升降、失败数与 tokens；分母固定为全 298 或事先固定样本，不能剔除新失败题。小样本后若做全量，沿用已固定规则，不挑出有收益的题再报告。

【Q6】结论：**有更简单方案：A + 独立完整性披露，再用 B 和已有输出做排序诊断。**

理由：先不改池成员，就能分开回答“旧分数是否低估主产物命中”和“正确候选是否被选到首位”。先核排序传递，再对已有事件做一次选择，可直接检验选择收益，无须立即生成新反应。B 的配对结果能判断人话字段是否值得保留，但不能替代对 C 的验证。混合模式保留为架构选项，待生成确有新增覆盖再扩大。

风险等级：**低。**

【Q7】结论：**优先定位为排序，但不能据此断言主要瓶颈已经转移。**

理由：[298 域] 156−109＝47 只是固定已提交事件集合中完美选择的上限，即最多增加 15.77 个百分点到 52.35%，实际收益未知，也可能为负。按已有读数，其中 39 题在第 2／3 位，8 题在第 4／5 位；另有 142 题未全部命中，生成与覆盖问题仍在。47 题未必都来自原池，池顺序也不等于最终事件位次，因此不能直接承诺 pool agent 可收回这 47 题。推荐先验证“已有事件选首位”再验证池前排序，使用全 298 或不看答案预选的样本，并同时看现有 109 道首位命中是否退化。生成理论上可突破固定输出的 156 上限，但成功率与新增收益均待测，当前没有依据给出预期涨分数。

风险等级：**中；把 47 当预计收益则高。**

【我认为请求方漏掉的问题】

| 问题 | 本次裁决 |
|---|---|
| 机器版本号已经占用 | 现有 `ppv1-criteria-v3` 是另一套互变／电荷归一披露口径；展示名可沿用用户所称 v3，机器 token 必须唯一或另设独立指标轴，不能覆盖旧语义。 |
| 模拟不等于生产实现 | 当前模拟把 partial／unknown／缺失完整度的包含覆盖直接升 exact，未加新开关，也未按主产物角色限定通用范围，并旁路原 v2 豁免披露；不能直接当作版本隔离已完成。 |
| 分类数字不闭合 | 请求首表 119＋37＋129＋6＝291；不要猜补余项或假定六道失败互斥。暂用 156＋2＋140＝298 主表；已有聚合文档将 140 分成 11＋129，六道失败与各桶是否重叠待核。 |
| 60 道空池的批次待核 | 现有可追溯出处中的 60 属 T-H r2（126 strict／89 hit@1），本次主表是 P2 A（119／86）；这不足以确认请求中的同一数字也属于 P2 A，未经批次对齐，不能与 47 做交叉计算。 |
| 40／53 单位与批次待统一 | 请求称 extras 来源，来源文档又写 partial 题数分层；须统一是题数还是参与物实例及来自哪批，不能当作 298 题比例。 |
| 底物不能唯一决定酶反应 | 同一底物可能对应不同酶、条件与正确产物；129 道“不匹配参考”不能直接升级为化学上的绝对错误。 |
| 选择与化学审核不是同一件事 | 两次同 DeepSeek 调用不构成独立化学复核；来源标签、可执行、命中参考也不能互相替代证明。 |
| 已见题调优仍是已见题结论 | 后续规则和提示若继续看这 298 题调优，仍只能报告 post-hoc；真正外推要在未见题上确认。 |

【我不同意的地方】

1. 不同意把“参考未声明的都不扣”表述成“额外参与物化学正确”；诚实落点是未核。
2. 不同意用“0 题变差”证明新规则安全；包含规则按定义单调放宽，这不是新增命中的化学验证。
3. 不同意把 8.6% 当成 DeepSeek 新反应生成率，也不同意用干跑通过替代化学可行性。
4. 不同意把 47 直接当 pool agent 的可收回收益，或据此认定生成已经不重要。
5. 不同意三项同上后宣称能分清收益；若维持单臂决策，结论必须限于探索性整体变化。
6. 不同意覆盖既有 `ppv1-criteria-v3` token，或把模拟中的 superset 改写为物理事实上的 exact。
7. 不同意仅凭 partial 就宣布原代码必错：审计 unknown 衡量完整性，集合 exact 衡量与已声明子图相等，两者不是形式逻辑矛盾；应修正的是评测目标对齐及“完整反应正确”的解释，旧指标可保留，新指标更贴合主产物预测但同样不扩大化学证明。

源码与文档依据（均为规则或聚合层，未据此独立认证逐题化学）：

| 依据 | 可支持的事实 |
|---|---|
| [旧版本登记](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/evaluation.py:867)、[旧 v3 披露约束](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/evaluation.py:1020) | 旧 v3 token 已有明确含义，归一轴只披露、不授 strict。 |
| [逐事件集合匹配](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/evaluation.py:2417)、[步骤范围检查](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/evaluation.py:2482) | 逐事件、按侧集合与步骤范围匹配；当前不以角色、系数比较证明完整化学正确。 |
| [参与物完整度](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:635)、[完整配平前提](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:664) | partial／unknown 的完整度与完整配平保留 unknown。 |
| [编译器校验与执行](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_compiler.py:1687) | 已有 `validate_edits` 后接 `execute_edits` 的路径，可复用执行门，但不能据此认证酶学可行。 |
| [流程载荷白名单](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1393)、[模型载荷白名单](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:259) | 两层模型载荷均显式选字段；新增标签须贯通渲染，不能只把字段写进候选对象。 |
| [假设身份生成](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/hypothesis.py:471) | `transformation_ref` 进入假设身份，须保留原有身份与溯源。 |
| [最终事件排序](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_scoring.py:641) | 最终事件排序使用 `created_at,event_id`，不能直接等同池输入顺序。 |
| [novel 通路](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:907)、[显式排名](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:987)、[原池回退](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1094)、[有效排名披露](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1144) | 已有 novel 通路、显式排名与原池回退，并披露模型排名及有效排名。 |
| [模拟包含规则](/Volumes/CC/Enzyme_Agent/dependingv43/docs/COVERAGE_V3_SIMULATION_2026-10-27.md:91)、[v2 披露旁路](/Volumes/CC/Enzyme_Agent/dependingv43/docs/COVERAGE_V3_SIMULATION_2026-10-27.md:138)、[汇总指标](/Volumes/CC/Enzyme_Agent/dependingv43/docs/COVERAGE_V3_SIMULATION_2026-10-27.md:196)、[位次分布](/Volumes/CC/Enzyme_Agent/dependingv43/docs/COVERAGE_V3_SIMULATION_2026-10-27.md:220) | 模拟包含规则、v2 披露旁路、汇总指标与首个匹配事件位次分布。 |
| [模型选择诊断批次](/Volumes/CC/Enzyme_Agent/dependingv43/docs/MODEL_CHOICE_LAYER_PROBE_2026-10-27.md:4)、[该诊断池统计](/Volumes/CC/Enzyme_Agent/dependingv43/docs/MODEL_CHOICE_LAYER_PROBE_2026-10-27.md:16)、[回放批次](/Volumes/CC/Enzyme_Agent/dependingv43/docs/L2_STAGE1_FULL298_REPLAY_2026-10-26.md:7)、[回放基线](/Volumes/CC/Enzyme_Agent/dependingv43/docs/L2_STAGE1_FULL298_REPLAY_2026-10-26.md:20)、[回放空池统计](/Volumes/CC/Enzyme_Agent/dependingv43/docs/L2_STAGE1_FULL298_REPLAY_2026-10-26.md:277) | 60 道空池的现有可追溯来源批次，尚不足以确认 P2 A 的同数统计。 |

