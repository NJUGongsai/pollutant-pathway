# chain13 为什么下降，以及 hit@1 50% 还缺什么（2026-10-15）

> 题域：**本文全部成绩、题数、候选数及其推导，均限定为 298＝RHEA 通用酶学/已见题**，与 dev、新题泛化及其他题域双向不外推。这里的题域标签不证明逐题数据来源。
>
> 性质：依据既有安全聚合报告和公开源码作只读诊断；新写本文，没有修改旧报告、源码、配置、池规则或判分。**本会话没有新增模型调用，没有运行探针、测试、真实实验或评分，没有访问远端；既有报告的“实测”属于原报告的执行声明，不作本会话独立复现背书。**文中用“事实”“推断”“建议”区分证据强度。下文的离线材料骨架是待审任务范围，不是实施、读金标或发车授权。

## 1. 给 CC 的结论

**chain13 的下降是真的，但“C 新功能把分弄坏了”和“全是服务器抽卡”都说得太满。**同一把 v1 尺子下，严格覆盖从 130 变成 114；改用已生效的 v2 尺子后恢复到 119。C 实际介入的 35 题，v2 后严格覆盖回到原来的 24；剩下的净损失在非 C 分组。已有证据表明实际生成、展开的候选内容变了，也有真实传输失败；没有同协议重复批，尚不能把多少分分别归给 C、模型采样或服务端行为。数字及识别限制见第 2 节。

**距离至少 50%，现在差的是 62 道净首位命中，不能靠再补几个声明解决。**目前首位严格命中 87/298，严格覆盖总共只有 119/298。即使把当前119道已覆盖题中的正确事件都理想地排到各题第一，也只有119道首位命中，离149仍缺至少30道严格覆盖。数学上必须扩大“能生成并提交正确严格事件”的覆盖；工程上建议并行改善“已有正确事件能否落在第一”的转化，以减少所需覆盖增量。实际重排能兑现多少尚未测。这里的30是极端理想条件下的最低新增覆盖要求，32是理想重排空间，都不是收益预测。[现有成绩](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_MODEL_CMP_TABLE_2026-10-15.md:13)、[覆盖定义](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_scoring.py:448)

**下一步先把真实漏斗和漏入口查清，再选一个实质干预。**L3“给普通门候选补声明”已经查到真新增 0 行/0 题，旧收益估计撤销；上次 L1 分档方案的新增资格条件也未证明非空。现在最有价值的方向是：按通道分别找出完整对齐与记录映射的真实损耗，同时核对模型排序是否实际传到正式提交位次。不要把旧代理数字直接搬进下一批预算。[L3 结项](/Volumes/CC/Enzyme_Agent/dependingv43/docs/L3_IMPL_DELIVERY_2026-10-15.md:10)、[上次 L1 新资格条件](/Volumes/CC/Enzyme_Agent/dependingv43/docs/L1_TIERING_DESIGN_RESPONSE_GPT_2026-10-15.md:26)

## 2. chain13 究竟下降了多少，能归因到哪一层

### 2.1 先统一尺子和分母

下表全部为 298＝RHEA 通用酶学/已见题。strict 是“至少有一个已提交事件严格命中”；partial 是部分匹配；uncovered 是未覆盖。strict 覆盖不是 hit@1。

| 指标 | chain12 v1 | chain13 v1 | chain13 v2 | chain13 v2 相对 chain12 v1 |
|---|---:|---:|---:|---:|
| strict 覆盖 | 130 | 114 | 119 | −11 |
| partial | 43 | 52 | 47 | +4 |
| uncovered | 125 | 132 | 132 | +7 |
| hit@1 | 92 | 83 | 87 | −5 |

来源：[归因任务书第 17–18 行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_CHAIN13_C_ATTRIBUTION_2026-10-15.md:17)。v1 同口径比较得到 strict −16、hit@1 −9；同一份 chain13 输出从 v1 改用 v2，得到 strict +5、hit@1 +4。后一个差值是判据作用，不能叫作生成能力提升。chain13 预注册已明确：C 供给、声明链、v2 判据、调用上限一起变，跨批不得称单变量归因。[预注册](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_S5B_298_PREREG_2026-10-14.md:31)

### 2.2 C 与非 C 的账可以闭合，但不是因果实验

| 分组，298 题域 | chain12 strict | chain13 v1 strict | v1 净变化 | chain13 v2 strict | v2 净变化 |
|---|---:|---:|---:|---:|---:|
| C 暴露 35 题 | 24 | 19 | −5 | 24 | 0 |
| 非 C 分组 263 题 | 106 | 95 | −11 | 95 | −11 |
| 全部 | 130 | 114 | −16 | 119 | −11 |

事实：C 组 v1 的旧 strict 损失为 5，没有新增 strict；非 C 组损失 18 个旧 strict，新增 7 个 strict，因此净 −11。全局 `−5−11=−16`。v2 的 5 个回收全部在 C 组，其中 3 个原来就是 strict，另外 2 个原来是 uncovered。因此 C 组 v2 **仍损失 2 个旧 strict，由 2 个新增 strict 抵消**，全局 `0−11=−11`。v2 这列是相对 chain12 v1 参考的跨协议观察账，不是同尺子下的单变量实验。不能说“旧 strict 丢的 5 个全救回”，也不能把“暴露组观察净零”升格为“C 的因果净效应已证为零”。[迁移表](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_C_NETNEG_ATTRIBUTION_2026-10-15.md:27)、[5 个回收的来源](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_CHAIN13_C_ATTRIBUTION_2026-10-15.md:38)

对 hit@1，原来的 92 个首位命中里，74 个保留，10 个掉出 strict，8 个仍 strict 但掉出第一；chain13 新增 13 个首位命中，得到 `74+13=87`。这说明既有正确覆盖流失，也有部分旧首位命中后移；仅凭这8题不能判定整体排序能力变差。[首位命中拆账](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_C_NETNEG_ATTRIBUTION_2026-10-15.md:53)

### 2.3 C 做成了工程闭环，但没有兑现预想的新增覆盖

事实：35 个 C 暴露题中，供给动作存在、执行完成、事件含共底物角色、manifest 有声明，四层均为 35/35；新执行契约的运行错误为 0/35。它支持“新供给和声明路径确实运行”，没有支持“新增门普遍误拒”的证据。[安全聚合追踪](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_C_NETNEG_ATTRIBUTION_2026-10-15.md:71)

另一件事是预期中的模拟 13 题：实际兑现 **0/13**，并非 5/13。这个集合中，救援计数与声明计数均为零，事件中共底物角色参与物也为零；其 297 个候选中，289 编译拒绝、6 compiled 但未触发救援、2 合并。实际救回的 5 题是另一个集合，不能拿来充当模拟面的兑现率。安全聚合只支持“供给资格与编译没有接通”，不等于已经证明某一修复能把这些题变成首位命中。[模拟面复核](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_C_NETNEG_ATTRIBUTION_2026-10-15.md:115)

### 2.4 候选输出确实变化，随机性贡献仍未识别

事实：非 C 的 18 个旧 strict 损失题，两批规范化扩展候选内容均改变，compiled 候选计数均相等。**计数相等不等于候选池内容相同**；这能反对“只是池里件数变多所以掉分”的简单解释，不能单独证明真实输入和模型可见信息完全相同，更不能给出纯随机损失比例。[扩展面差分](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_C_NETNEG_ATTRIBUTION_2026-10-15.md:96)

身份还有一处未闭合：C 交付书的同树开关差分为 262 题输入字节相同、35 题纯新增、1 题 W4 补位互动；归因报告却把非 C 263 题统称输入零变化。仅凭已读聚合材料，不能确认该补位互动与 35/263 分组的对应关系。**本报告保留“非 C 分组”的统计，不背书“263 题实际调用输入逐字相同”。**[交付差分](/Volumes/CC/Enzyme_Agent/dependingv43/docs/C_COSUB_SUPPLY_IMPL_DELIVERY_2026-10-14.md:69)

服务失败也确实存在：后出归因记录 298 个 issued、288 个 responded、10 个 failed，并与 10 个 transport failure 对应；chain12 缺少同类调用及身份快照，采样参数未显式设置，不能补想出来。批级“全部终态齐了”不等于每题模型都成功；**10 次失败也不等于可以恢复 10 道 hit@1**。[调用留痕](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_C_NETNEG_ATTRIBUTION_2026-10-15.md:145)

同协议纯重复批缺失，因而无法将 C、采样、服务失败各自的分数占比定量拆开，也无法给随机波动置信区间。hpc2 A/B 的 34/298 状态翻转含 RR 真实干预，不能当作 A/A 噪声分布；不能据此宣布“超过正常波动”，也不能把一定范围内的损失都算噪声。[参照的自身限制](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_C_NETNEG_ATTRIBUTION_2026-10-15.md:163)

### 2.5 D 与调用预算没有贡献出已证成绩

已读材料中，D 映射线仍是 draft，规定 C 后先重跑覆盖探针，再决定接入和单变量评价；没有 chain13 实际消费该新模板库的证据，不能把“已经建好映射资产”当作本批已提升能力。[D 状态](/Volumes/CC/Enzyme_Agent/dependingv43/docs/D_RXNMAPPER_SCALEUP_DESIGN_PREREG_2026-10-14.md:3)、[D 依赖与接入顺序](/Volumes/CC/Enzyme_Agent/dependingv43/docs/D_RXNMAPPER_SCALEUP_DESIGN_PREREG_2026-10-14.md:66)

补源有一份可用的**历史储备证据**：原 D 侦察在 chain12 的 H=120 分组中，将86题归为收录范围外，版本差、表示差均为0，正控34/34通过。这不是“chain13当前86题都缺源”，更不是可加86分。报告自己也说明补源只抬供给上限，下游元素、电荷、立体等编译闸仍在，C后需复核。[历史分组来源](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_D_RXNMAPPER_COVERAGE_2026-10-14.md:13)、[零结构取值的聚合报告](/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/d_align_recon_2026-10-14/D_ALIGN_RECON_REPORT_2026-10-14.md:4)、[历史缺口数字](/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/d_align_recon_2026-10-14/D_ALIGN_RECON_REPORT_2026-10-14.md:12)、[下游闸门限制](/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/d_align_recon_2026-10-14/D_ALIGN_RECON_REPORT_2026-10-14.md:73)

每题调用上限 1→3，消费路径是最多 1 次主调用加 2 次**格式修复**，不是三次化学探索。旧表报告额外格式修复未触发；它不构成新的生成收益。[预算定义](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_S5B_298_PREREG_2026-10-14.md:23)、[格式修复报告](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_MODEL_CMP_TABLE_2026-10-15.md:27)

## 3. 距离 hit@1 50%，需要跨过多大的缺口

用户当前目标“hit@1 至少 50%”对应 `149/298=50%`；若要求严格超过50%，则要 `150/298≈50.34%`，多1题。**这不是把历史hit@1门从150降到149。**10月9日的150是hit@5门；10月10日主列已改为hit@1≥119（约40%档），hit@5≥150仅参考。本文按用户当前新目标149分析，不追改历史冻结目标。[10月9日目标](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_V43_PPV1_S5B_HIT50_UPGRADE_AND_RETEST_2026-10-09.md:10)、[10月10日目标](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_V43_PPV1_S5B_HIT50_V3_2026-10-10.md:24)

| 当前 GLM v2，298 题域 | 已有聚合数 | 对 50% 目标意味着什么 |
|---|---:|---|
| H1：第一位严格命中 | 87（29.2%） | 至少净增 62 |
| H3 / H5 | 112 / 118 | 往前搬现有正确事件有空间，但不是已证收益 |
| U：全部已提交严格事件覆盖 | 119（39.9%） | 固定事件集合的理想排序上限仍低于149 |
| U−H1 | 32 | 极端理想重排空间，不是原始检索池上限 |
| 149−U | 30 | 所有现有 strict 都排第一时，仍需至少新增30个严格覆盖 |

成绩来源：[三模型表第 13–19 行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_MODEL_CMP_TABLE_2026-10-15.md:13)。上表差值和百分比为公开聚合数字的纯算术，无新实验。其成立前提是固定当前已提交事件、严格匹配定义和分母；若原候选中发生“已 matched 但不在正式候选序列”的异常，应单列核实，不能默认任何覆盖都能无条件变成第一。[分母与单调性](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_scoring.py:434)、[rank 与异常披露](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_scoring.py:657)

源码把正式候选定义为：反应物侧含根严格命中状态的**已提交事件**，按 `(created_at,event_id)` 排序，首个严格命中的事件位次决定 hit@K。因此这里说的“排序”，最后必须改变正式提交顺序；只改展示顺序或另加一张排名表不一定有效。[正式位次定义](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_scoring.py:631)

anyof 的 145 不能解释为“离149只差4”。老口径以产物字符串为候选，并有多组分探索表；正式主口径核的是根事件严格匹配。二者命中对象、K 槽含义不同，差额不代表可以通过调尺子合法兑换。[两种口径](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_scoring.py:11)、[老口径字符串定义](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_scoring.py:509)

三模型的首位命中 87/83/79，只支持这次探索批的观察排序；预注册明确“不做模型选型结论”。没有证据显示换成已测另一个模型能补上 62。tokens 较少也不是实际费用必然更低，缺模型单价、计费与重试账时不能这么推断。不同批、不同模型各取最高项拼成“现有最好系统”同样不成立。[三模型成绩](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_MODEL_CMP_TABLE_2026-10-15.md:13)、[探索纪律](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_MODEL_CMP_PREREG_2026-10-14.md:29)

## 4. 先撤掉已经失效的机会，再讨论新提升

### 4.1 L3 已结项，不能再报潜在收益

L3 交付记录：207 条 compiled 行按精确“反应物侧额外组分”条件复核，真新增为 **0 行/0 题**；已有反应物侧额外组分的 46 行已在既有声明面。实现、回归、新测试、版本升版均未发生。它否定的是这一批、这一资产版本下“普通门还有未声明共底物”的原方案前提，不是证明整个系统没有缺口。[结项结论](/Volumes/CC/Enzyme_Agent/dependingv43/docs/L3_IMPL_DELIVERY_2026-10-15.md:10)、[精确分类](/Volumes/CC/Enzyme_Agent/dependingv43/docs/L3_IMPL_DELIVERY_2026-10-15.md:25)、[未交付范围](/Volumes/CC/Enzyme_Agent/dependingv43/docs/L3_IMPL_DELIVERY_2026-10-15.md:22)

原先 55 题代理面、10 题新增潜力、19 题 partial 受益面和 3～8 题收益估计均已撤销，不能继续加进 hit50 路线账。上次方向无关的族扫描，把产物侧参与物也算进“反应物侧待声明”机会，代理数字没有回答真正的实施问题。[chain14 顶部勘误](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN14_LEVER_DECISION_2026-10-15.md:1)

### 4.2 R0 的资格件数也不是新增命中数

R0 在模拟 13 题内：全通道族合格 186 件、覆盖 12 题；限定 corpus/recorded 为 93 件、覆盖 11 题。这些是“编译拒件中的族资格”，不是编译存活，也不是能被模型用上的正确候选。[R0 口径](/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/chain13_glm/analysis/r0_probe_p1p3_summary.md:145)

由两张交叉表相减，analog 的 93 件为 91 个 no_alignment 加 2 个 ambiguous_alignment；全通道 56 个 mapping_enumeration_truncated 全在 corpus/recorded。**不能把56个枚举截断归到analog，再建议统一提高analog枚举预算。**[全通道表](/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/chain13_glm/analysis/r0_probe_p1p3_summary.md:165)、[限定通道表](/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/chain13_glm/analysis/r0_probe_p1p3_summary.md:185)

全批 L1 裸资格面为245题，与现有C取并集为248题；新增暴露历史稳/宽strict为74/92题。chain14旧表的249是联合L3面，不是单独L1。暴露表示可能影响旧成功的范围，不等于必然损失；但它也远大于一个可以凭“净零先例”放心开启的小改动。[集合定义](/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/chain13_glm/analysis/r0_probe_p1p3_summary.md:204)、[正确表行](/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/chain13_glm/analysis/r0_probe_p1p3_summary.md:218)

### 4.3 上次 L1 分档回应需要补一个更前置的问题

上次本会话给出的新增条件包含 `analog & front_gate_rejected & !current_C_eligible`。本次读源码后的**推断**是：现行 C 已对元素前门失败的 analog 候选调用伴生供给 helper；helper 对可解析、多组分、非裸通配的合法袋补齐供给。因此，如果维持相同语义并排除未知与裸通配，这个“新增”mask **可能是空集**。本会话未执行面数探针，不能把“可能空”写成已实测为零，也不能继续把它当已证可行方案。[上次方案](/Volumes/CC/Enzyme_Agent/dependingv43/docs/L1_TIERING_DESIGN_RESPONSE_GPT_2026-10-15.md:26)、[现行调用入口](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_builder.py:1082)、[供给规则](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_builder.py:559)

更值得先查的真实漏入口是：**元素门通过，完整结构对齐却失败，于是没有触发当前 C 救援**。元素计数只是必要条件，满足并不保证键连通性、完整袋或子结构能落位；普通编译入口仍可能报 no_alignment。这个方向必须先按聚合交叉表证明非空，再评估精确供给后能否编译、进入最终payload、被下游实际消费。它是源码提示的待证机会，不是已确认缺陷或收益。[必要条件边界](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_compiler.py:138)、[普通编译入口](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_builder.py:1173)

保留上次设计稿作历史材料；其分档、预算和先证存活原则仍可供后续设计参考，但不能跳过“新增面非空”这一步。本报告不扩大任何豁免许可。

## 5. 进一步提升的优先级

| 优先级 | 先解决什么 | 进入下一步的证据 |
|---|---|---|
| P0 | 指标、身份与真实漏斗统一；调用失败与候选错误分账 | 固定输入、代码/资产/模型/prompt/编译/池配置身份；逐层聚合闭合，快照缺失保留unknown |
| P1a | 按通道修真实编译损耗 | analog完整lhs落位与recorded供体到产物映射分别定位；各有合法正控、必要拒绝负控与实际下游机会 |
| P1b | 与覆盖并行核正式首位转化 | 模型rank确实影响执行提交次序；只用线上可得信息，提出可验证的单一变化 |
| P2 | 真实非空的窄L1入口 | 新资格非空、当前编译存活>0、实际消费payload变化>0、暴露预算可接受，再进入预注册 |
| P3 | 漏斗证明缺记录后补源；必要时新执行契约 | 证明现源池没有对应可用机会；来源与接入边界合法、独立评审；不能靠映射率或族件数报成绩 |

**P0 不需要先花新模型调用。**先把现有登记、快照缺口和安全聚合核清，设计不消费答案的全链漏斗与新增面探针；这一步可能直接排除空方案。实际探针仍须独立任务书明确输入权限、输出边界及写入位置，不在本次诊断中执行。

**P1a 应拆成两条能力路径。**analog 编译要求完整供体反应物落在当前执行图上，no_alignment 是没有完整子结构匹配，触顶则另报 alignment_limit_exceeded。recorded 的 mapping_enumeration_truncated 来自 donor→product 的推断映射枚举；它不是同一个枚举入口。应分别查精确袋、主组分、对齐覆盖、等价映射与歧义，不能统一“加cap”或全部放行。[analog对齐](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_compiler.py:487)、[analog拒因](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_compiler.py:934)、[recorded分类](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/recorded_source.py:933)、[recorded映射触顶](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/recorded_source.py:2095)

**P1b 不应被“覆盖优先”完全挤掉。**119−87的32个理想空间证明排序有可研究对象，却没有给出任何现实可兑现题数。先核模型原rank到行动队列、执行次序、准入及提交时序的传递，再考虑单次调用内证据表达和线上可得特征；不能调用答案、逐题oracle或正确事件ID去指挥模型。只改评分后顺序不算合法提升。[正式排序与保护边界](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_scoring.py:497)

源码已提供有效rank升序调度、同步驱动和action微秒单调时间，并不是已经证实“同秒哈希乱序”导致下降。事件时间使用微秒墙钟，没有action那样的单调下界；未见实际同微秒或时钟回退证据，不能据此报bug。[rank调度](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/queue.py:211)、[同步驱动](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:666)、[action时间](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/search.py:707)、[事件时间](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/events.py:89)

但存在一个应优先核查的**条件性源码风险，未实测、未量化**：prepared先装池条目、再装novel；净反应去重保留较早条目，随后rank表仅保留幸存键，所有显式rank先于fallback。若一个合法提案能到达此分支，且带模型首位的novel被折叠到无显式rank的早期池条目，其首位可能没有转给幸存者，另一显式候选便可能先执行。这是源码推演，不是chain13已证根因。另有执行失败、准入拒绝、defer不提交事件，也会使正式first不同于原模型第一。[池与novel装配](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:868)、[novel追加](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:917)、[去重与rank过滤](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:995)、[显式rank优先](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1025)、[不提交分支](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1346)

若rank传递无损而首位转化仍低，可再把线上可计算的主变换、完整共底物角色、来源匹配与编译完整性组织为可比较字段，供原有单次调用排序。当前prompt只确认传入候选ID、产物、变换ref和共产物，不能声称完整声明链已进模型。应冻结候选集，只改变候选信息表达作单变量评价；不增加LLM调用、不输入答案，也不预报收益。[当前候选白名单](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:204)

**P2 要等真实增量和L2存活。**若资格放宽后全部编译失败，先做L2；若compiled新增被去重或截断全部吞掉，则先定位池消费；若只有诊断hash变化而原执行、准入或判分实际消费内容没变，也不发车。编译器与L1都要改时，应先独立验收并冻结共同编译版本，再只切一个L1开关，不把混合差值当L1收益。

**P3 的键合贡献需要新契约，不能当预算小修。**当前recorded执行图不含共底物B的原子；B原子键合进入主产物不是多写一段声明能表达，现规则对借add_atom引入它有硬拒绝。因此L4涉及联合执行图、原子来源、元素账及歧义治理，应独立立项；不能把已有bonded拒件数直接换算成短期strict收益。[结构边界](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/recorded_source.py:1148)、[执行编辑负控](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/recorded_source.py:1594)、[L4设计边界](/Volumes/CC/Enzyme_Agent/dependingv43/docs/C_COSUB_SUPPLY_REDESIGN_PREREG_2026-10-15.md:52)

模型更换和增加格式修复次数不作为主押方向。首先证明信息、候选和执行机会真正进入系统，再评价模型能不能利用；如果某层没有可执行机会，换模型不能绕过那层。

### 5.1 还有一项应先核的任务限制：模型是否得到足够的区分信息

事实：实际首调payload白名单只有底物、atom ID、执行图和候选的ID/产物/变换引用/共产物，没有酶、EC或真实题级条件；builder也登记condition_facts空及缺少每题条件元数据。system prompt要求按官能团提出合理中性酶促单步，禁止编造EC或条件。候选内容与引用仍可能提供区分信息，不能据“没有EC”直接宣布任务不可解。[实际payload](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1263)、[白名单序列化](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:191)、[实际调用](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:696)、[prompt任务](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:106)、[条件缺口](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_builder.py:351)

推断：如果完整可见输入相同却对应不同合法目标，缺区分信息可能限制首位成绩。建议在受保护本地判分边界内只输出聚合歧义统计，按**完整可见输入签名**分组，包含候选内容、顺序、变换ref、执行图与prompt配置；只按同底物分组不够。v2参考匹配可能重叠，不能拿多数目标频率直接当上界：须先证明目标类互斥，或由受保护scorer计算一个合法首事件最多同时匹配多少参考。条件未齐只报歧义计数，不编天花板。现无此探针结果，不能承诺50%可达或不可达；部署时不可得的酶/EC信息也不能当免费补丁塞给模型。

### 5.2 用漏斗结果选择工程，不靠机会件数押注

| 未来离线聚合若显示 | 下一动作 |
|---|---|
| 现有合法上游机会触达不足149题，且上界条件已证明 | 仅调排序不够，定位供给、资格或执行表示缺口 |
| 上游机会足够，编译后覆盖明显损耗 | 按通道修对应对齐/映射入口，先验收再进真实批 |
| 已提交集合有strict，但first转化低 | 查选择、去重rank继承、执行失败和准入，保持正式评分不动 |
| 完整输入歧义的认证上界低于目标 | 回任务定义与可得信息评审；不给答案、不放宽尺子 |

上述上游“上界”均为待证条件，不是现有实测。覆盖和首位两线可以并行离线查，真实批仍一次只改一个变量。

## 6. 下一份可审查材料：离线闭环漏斗骨架

**目的：不先预测能涨几题，而是找出“下一项变化到底在哪个入口产生新的、可实际消费的机会”。**这是建议材料，不代表本会话取得数据访问、目标匹配、模型调用或发车授权。

固定题集登记、score版本及分母；记录代码、资产、source corpus、候选身份、模型服务配置、prompt、编译器、指纹、池宽/检索/去重/截断规则hash。实际最终输入payload与候选prompt内容hash分别留证。历史缺快照就标不可比，不用当前重建身份冒充当时身份。

| 漏斗阶段 | 必补聚合字段/口径 | 结果决定什么 |
|---|---|---|
| 源记录可用→检索进入 | source/channel/family、记录身份版本、检索命中与截断、唯一候选数 | 源不存在才考虑补源；源有而未检索先查检索入口 |
| 资格触发→精确袋 | 元素前门结果、完整对齐结果、current_C_eligible、是否调用救援、完整多重集/主角色/方向核验状态 | 资格新增为零则撤该方案；元素门过但结构门败的交叉格另列 |
| 对齐→编译 | compiler身份、attempted/status/reason、对齐是否零匹配、哪条枚举触顶、歧义/键合/来源状态 | 区分analog落位与recorded映射，按真实入口排L2 |
| 去重→最终池 | 唯一候选身份、合并/截断原因、原候选被替位数、实际消费payload差异种类 | 编译有新增但池变化零，先查消费；不能把诊断变化当机会 |
| 模型选择/novel→行动 | 模型可见完整输入签名、去重前rank、净签名hash、幸存者ID、rank继承前后、effective_rank、调度状态、novel计数、格式修复/传输失败分列 | 有机会却没选查表达与选择；去重丢rank另计；调用失败独立归账 |
| 执行/准入→提交 | 执行序、拒因、事件数、提交时序、时间相同计数、首root事件的原rank、声明链消费状态 | 选择正确但未提交查执行准入；不能用“有动作”代表有效事件 |
| strict匹配→正式first | 受保护判分聚合、matched但不在候选序列计数、H1/H3/H5/U、同题gain/loss/net | 覆盖与首位转化分别评价；旧成功退步必须扣回 |

表内字段是**证据需求**，不是声称现有接口已经完整提供。各阶段必须同时报原始行数、既有身份去重后的唯一候选数、题级去重题数，再按 `channel × family × reject_reason` 分层；各阶段、各族、各模型重叠机会不能相加当收益。所有改动要报告同题旧成功损失与新增成功，净值才是可比较的提升。

诊断本身不直接读取或导出金标、题面、逐题答案或对错。如果未来要核对“源记录或候选是否目标相关”，只能在已有授权允许的受保护本地scorer进程内部计算、仅输出获准聚合；不能把目标/reference/正确source ID/oracle事件序回馈生成模型。当前授权不足的步骤应留空待批准，不能为了填满漏斗自行扩权限。[源码保护说明](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_scoring.py:497)

离线材料的出口应明确：新增资格零、当前编译存活零或最终有效payload变化零，都不进入真实批；身份无法闭合，不作因果结论；有真实机会且暴露可控，才写单变量预注册和正负控验收。真实模型批、费用及新增调用仍按既有批准流程走。本报告不把“双跑”含混地当成效应验证：同配置重复用于认识波动，处理/对照用于识别干预，两者的区别必须在实验设计中写清；未执行前不给CI或收益分摊。

## 7. 只在本文登记的勘误与未知项

| 旧材料中的说法 | 本文采用的边界 |
|---|---|
| C生成侧已证净负；C本身已证因果净零 | 多变量跨批；C组观察v2净零，非因果效应 |
| 非C损失题池完全一样 | 18/18只证明compiled计数相等；扩展内容18/18改变 |
| 模拟13兑现5 | 实际5与模拟13不同面；模拟面0/13 |
| 全部终态齐＝模型零失败 | 后出记录有10个transport failure；恢复命中数unknown |
| v1保持格S→S=115、U→U=110 | 按既有迁移表补全应为107、111；P→P=33，保持251+迁移47=298 |
| 单L1的C并集249 | R0单L1为248；249是联合L3面 |
| L3普通门补声明可带来既定收益 | 真新增0；未实现、未升版，旧代理收益撤销 |
| 上次analog前门失败的新mask已有机会 | 未证明非空；先查现C未触发的真实新入口 |
| hpc2的34翻转可作纯噪声基线 | 含RR干预，不能给纯随机CI或容忍损失阈值 |

保持格的更正来自公开聚合算术：初始strict130减S→P10、S→U13为107；初始uncovered125减U→S5、U→P9为111。原报告第37行与同文第41行“两批都strict107”不一致，本文按闭合值登记，原文件不回写。[原错误行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_C_NETNEG_ATTRIBUTION_2026-10-15.md:37)、[支持107的同文口径](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_C_NETNEG_ATTRIBUTION_2026-10-15.md:41)

仍需补证的核心未知项是：实际调用输入身份是否完全可比、1题W4互动的分组对应、各类失败的可恢复目标机会、真实新增资格面是否非空、编译新增能否存活到正式提交，以及模型rank到正式first位次的损耗在哪层。任何一个“候选很多”的数字都没有替代这些问题。

## 8. 给下一步的判断

**这已经不是再补几个声明就够的目标。**达到至少149个首位严格命中，必须扩大有效严格覆盖；并行改善第一位转化能减少所需覆盖增量，旧成功退步仍须扣回。现在没有证据承诺50%一定可达，也没有依据给各杠杆虚构收益或排一个确定时间表。

可执行的下一张材料是第6节的闭环漏斗，优先产出“真实漏入口非空、当前编译存活、最终payload被消费”的证据，并并行核首位排序传递；然后只选一项确实改变机会的干预进入正式设计。先证明系统下一步会多做成什么，再讨论真实批要花多少调用。
