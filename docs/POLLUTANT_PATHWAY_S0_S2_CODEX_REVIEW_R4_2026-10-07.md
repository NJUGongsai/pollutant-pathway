# pollutant_pathway_v1 S0–S2 第四轮独立复审（R4）

审核日期：2026-10-07。仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。锁定 HEAD：`e80f4594ea44b5f2bf8c78360dc2ed2368dd94ae`；上一轮审核基线：`af14fb2bb66e8afbbbbecd38722a9cacbd0699c3`。

**结论：R4 有实质修复，但 S0–S2 尚未通过，不放行 S3，不冻结化学判据或契约。** 独立隔离测试 **312 passed，0 skipped**；新增实际接口反例仍证明：无需真实诊断即可获得“全部核实”，必要条件和依赖反驳可以被漏掉，账本身份/出现记录及旧来源关系仍未闭合。此时接搜索会放大错误证明、错误剪枝和不可追溯状态。

本轮只读审核实现，所有探针使用合成结构、条件和临时 SQLite，不读 gold、真实题目资产或封存逐题 run，不调用模型、不做真实路径实验。原工作区只有用户已有的未跟踪 `docs/mimo_ppv1_chem_review_response_r4.md`；审核结束前 HEAD 未变。

## 1. 依据与证据范围

必读依据：

- [原实施书，第 17 节最终裁定](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md:761)。
- [R3 独立复审](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R3_2026-10-06.md)。
- [R4 回修交付书](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R4_2026-10-06.md)。
- [mimo R4 意见原文](/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r4.md)及本次代码/测试。

化学、条件与科学前提、存储与适配三线独立核查；主审检查证据真实消费，并再次执行三线新探针及旧化学/存储探针。永久证据入口：[README](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r4_codex_2026-10-07/README.md)。附件包括主审核 23 条 JSONL、化学新边界 17 条/旧控制 40 条、条件 19 个顶层案例、存储新边界 21 条/旧控制 29 条、312 项测试日志及 SHA-256 清单。**记录数含控制和环境记录，不是失败测试数。**

条件旧脚本按 AST 顶层块捕获拒绝后继续复跑；四个已修构造/冻结/版本拒绝块不算“通过”。旧中心载荷不符合 v4，因此新条件全链探针另用真实 AtomTool→真实 v4 诊断→audit→admission。脚本复制到临时目录执行；不在永久证据目录创建 SQLite 或覆盖日志。

| 核查 | 实际结果与采信范围 |
| --- | --- |
| 独立 ppv1 单测 | 复制 src 与全部 10 个 ppv1 测试到隔离目录，312 passed in 1.95s，0 skipped |
| 全量非 slow | 交付和 mimo 分别报告 923 passed / 16 deselected；本审核未独立重跑全量，不写成主审核实 |
| 修改范围 | R3→R4 实施源码在 pollutant 包和 ppv1 测试；未见改写冻结 legacy 执行链，不以静态 diff 代替全量行为证明 |
| S3 入口 | 仍 fail-closed，符合阶段边界；不要求本轮提前实现搜索、队列、终点或评测 |
| 外部化学依据 | 只补查 RDKit 官方文档；mimo 的观点以程序证据互证为限，不作独立性背书 |

真实执行器例与接口合成例分别标记。H2 等合成参与物只用于数值闭合；不证明机制、速率、酶选择性或实际降解路线。立体差异接口合成不等于冻结执行器会产生该差异。

## 2. 上一轮关闭状态

| R3 项 | 本轮确认已修 | 判定 |
| --- | --- | --- |
| 01 证据绑定/strict/scope | 原乙醛证据支持乙酸或丙烯、名字-only 均 unknown；合法绑定正例及 strict False/None 消费正确；旧过强正例已改 | 部分关闭：自造证据、实际编辑/执行及产物集合绑定见 R4-01 |
| 02 指定手性联合映射 | meso 错位不再等价；真 C2/环己烷保持；增强组有 unknown 门 | 绝对四面体旧反例关闭；非四面体支持范围见 R4-07 |
| 03 CIP 当构型变化 | 两组真实配置保持/CIP 重排反例通过；准确标签只披露；真实反转可见 | 旧反例关闭，不撤销；未覆盖立体轴另见 R4-07 |
| 04 CX 身份 | 五个 CO 绘图/原子注释输入同 ID；混合 ABS 三组及公开往返通过 | 部分关闭：DATA SGroup 非结构注记仍改变身份，见 R4-08 |
| 05 编辑协议/净效应 | 单次 add_atom 隐含锚键与旧键连续操作净效应正确；中心电荷/构型披露新增 | 部分关闭：新增 ID 后续引用、显式错 from_order 见 R4-06 |
| 06 路线消费/外来绑定 | 原 sA:p0→sB:p1 两行 audit/admission 正确；候选外来绑定构造拒绝 | 部分关闭：同名阶段跨场景、空快照覆盖见 R4-04 |
| 07 继承依赖 | context/hypothesis 并集消费，context unresolved 不被显式 [] 洗掉 | 原遗漏关闭；初始供给反驳被再生覆盖见 R4-05 |
| 08 hash/前提/排序/契约 | 原五类输入进入 hash；调用方原字典隔离、context已冻结容器的普通 append/update 拒绝、排序存储幂等、requirements/context 版本门有效 | 部分关闭：finite_rule 输入遗漏、对象自身/持久身份见 R4-02 |
| 09 公共 writer | 完整结构伪 ID、电荷错、非法公开串及旧事务反例拒绝；event 身份重算有效 | 部分关闭：CN-only/出现事实、hypothesis ID 见 R4-09/02 |
| 10 重放 | 原事件/hash/版本/身份列、部分状态损坏和带完整 states 的出现缺失均拒绝；导入不再先补已删依赖 | 部分关闭：无重复输入的出现集合、内 ID/空结构见 R4-10 |
| 11 旧导入 | 错但不同 CN 的指针、根 raw/CN 矛盾降级；单事件未知版本也拒绝，旧字节不变 | 部分关闭：同 CN 错父事件及记录间矛盾见 R4-11 |
| 12 matrix | sandy soil/soil 不再硬 conflict，改 unknown | 本项旧反例关闭；来源单位仍见 R4-03 |

§4 中空展开计划、同 hash 跳阶段理由、per-product off 披露确认关闭；普通初始支持→再生支持不再覆盖也有效。全 H/电荷账、保真分轴、同图多出现、provenance 引用/支持计数下界及 SearchLimits 草案旧控制保持。不据此宣称路径科学验收通过。

## 3. 阻塞 S3 的问题与最小验收

### R4-01 [P1] 证据仍可自造到 R6；绑定只覆盖底物与任一产物，无法诚实处理完整产物集合

位置：[audit.py:589](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:589)、[603](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:603)、[643](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:643)、[687](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:687)。

主审真实乙醇→乙醛诊断为正控制。对同一个配平合成假设 CCO→CC=O+H2，仅提交注册版本/scope、中心=True、strict=True 和两条身份字符串，无编辑/执行/供体中心/对齐，仍 **verified→R6**。补四条虚构字段，或逐项改真实诊断的 edits_signature/execution_fingerprint/donor_centers/alignment_ref，仍 R6；只有 hash 改变。注册名和多填字段不证明确定性 checker 曾对本次输入执行。

strict 字段还未校验类型：字符串 `'false'`、整数 0、空 dict/list 均绕过 `is False/is None`，得到 R6；合法 bool False 和 None 正确 retain。是表示契约漏洞，不是化学“未知就拒绝”。

**完整产物方向的真实反例：**AtomTool 断乙醇 C–C，实际 `C.CO`，诊断 strict/center 均 True。合法分列假设 CCO+H2→C+CO 各参与物和数值账正确，却因 `C.CO` 不等于任一单个产品被 unknown/retain；把两个产品塞为一个 `C.CO` 参与物才 R6。另一方面，真实乙醇诊断复用于 CCO+C1CC1→CC=O+H2+CC=C 也 R6，额外转化未验证。后者是合成完整账对照，不声称该反应生物可行。

**验收：**用可核验诊断记录或内部重算建立证明链，锁定真实输入、编辑/映射/执行及产物范围；不得仅增加可自报字段或收窄文字。类型错误结构化拒绝；没有可验证依据为 unknown。产物按来源映射的集合/计量/覆盖表示，支持真实断裂的分列产物，不要求把碎片拼成一个物种过门。限定区域证据不能覆盖额外未核实转化；可明确部分覆盖而 retain，不强制本轮实现 S3 完整供体模板。区域与 strict 分轴仍保留。

### R4-02 [P1] 实际审计输入仍漏 hash；科学载荷可变、假设派生身份也未接到 writer/replay

位置：[audit.py:446](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:446)、[839](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:839)、[path_context.py:186](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:186)、[hypothesis.py:332](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/hypothesis.py:332)、[store.py:560](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:560)、[1108](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1108)。

主审只改 finite_rule_diagnostic：默认 not_run 为合法 NA，admission expand；输入 diagnostic_only 后检查 unknown、admission retain。两次 **input_hash 同为 ain_62e14e274111a6756612**。该实际使用参数没进 fingerprint。原五类 hash 漏项确已修，不能据此宣称覆盖所有实际输入；“不能用相同 hash 推断可缓存”的注记不能替代正确输入身份。

另有两个身份问题，**它们的 input_hash 已改变，不能说原 hash 漏项原样复现**：

- frozen value dict 漏继承的 `__ior__`；普通 `alias |= {'lo':20,'hi':30}` 能改必要区间，使同 context_id 的 defer→R6。父/兄弟分支不变，隔离修复仍认可。
- hypothesis 自身 requirements 是普通嵌套 dict，update 改科学前提但保留 hypothesis_id。公开 put/submit/replay 也未调用已交付的 `recompute_hypothesis_id`：合法新增 assumptions 配旧 ID，首次 put/事务成功；仅改已存 assumptions、重放不提供假设 dict，仍 created=False。

**验收：**所有实际消费者参数进入规范化输入身份，含有限规则诊断及有效版本/范围。科学前提真正不可变，或入口复算身份并拒绝旧 ID 新载荷；正常操作必须先拒绝再修改。put/submit/已存 replay 同源复算 hypothesis 身份和契约，不以载荷 ID=SQL 键替代。保持同语义排序与重放稳定、调用方原字典隔离的控制。

### R4-03 [P1] 来源温度单位未知仍以 assumed_canonical 支持 R6

位置：[path_context.py:94](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:94)、[697](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:697)、[705](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:705)。curated_source 温度25、unit=''、source_unit_unreported；有来源必要区间20–30°C。实际 satisfied/within_range + assumed_canonical，audit verified→R6。交付登记和注记没有解决 R3 的验收要求。

**验收：**量纲事实明确已归一及单位依据，或来源单位未知为 unknown/入口拒绝该表示；不能靠注记升级 satisfied/conflict。不要求自动单位换算，不把 pH、氧枚举、matrix 等无单位键一概判未知。明确规范°C输入可 verified，显式K不匹配保持 unknown。

### R4-04 [P1] 场景未进入 live 筛选，空阶段快照还能漏掉未记录的必要要求

位置：[path_context.py:1049](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1049)、[1072](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1072)、[1657](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1657)、[1902](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1902)。

合法 sA:p0 有氧旧边满足→显式 sB:p0 无氧新边满足，旧要求因 phase 同名又被当前场景重评，产生 conflict→defer；sB:p1 对照正常。接口允许只转 scenario，没有 phase 全局唯一约定，不能强迫改阶段名规避。

纯公共 derive 另一例：父p0无必要要求，转p1时带一个已绑定p0/缺失旧边的 essential pH6–8要求；父正常生成的空快照 has_gate_requirements=False、per_requirement=[]，仍因阶段/场景相同被当作 covered，该必要pH从评估中消失，audit verified/R6。删空快照对照才 unknown/retain。

**验收：**以完整要求引入作用域区分 live/历史，至少含 scenario+phase；快照覆盖证明具体要求/边的评估，不仅证明阶段存在。孤儿必要要求拒绝错误引入或显式 unknown。旧边真实快照不重评，本候选新增要求仍评当前；跨阶段事实按适用性服务多边，不要求事实逐边绑定。

### R4-05 [P1] 分轴只累积支持，反驳不撤销旧支持；再生支持重新洗绿初始供给

位置：[path_context.py:1428](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1428)、[1503](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1503)、[audit.py:781](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:781)。合成A→B→A供给环，同一依赖 initial_supply supported→该轴 contradicted→仅 regeneration supported。日志保留反驳，support_axes 却永久保留初始支持，最近全局 status=supported；启动未知被清空，audit all_dependency_refs_reported_resolved→R6。

**验收：**按轴保存当前有效支持/反驳/未知及依据，不能只保存“曾经支持过”的集合；再生支持不重新证明已反驳的初始供给。恢复某轴须有该轴新证据。保留普通 initial_supply supported→regeneration supported 正控制。仅要求 S2 诊断诚实；依实施书§17.4，环不自动 reject/defer，S3调度未在此实施。

### R4-06 [P1] 执行器镜像漏新增 ID 与显式前置条件，既误拒合法编辑又放过错误声明

位置：[audit.py:1618](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1618)、[1650](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1650)、[1660](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1660)。

两条真实 AtomTool validation/execution 均 True：C先add O、用新O再add C→COC；C先add C、引用新键改双→C=C。镜像始终用 before ID 表，二者均 declared_edits_not_simulable、strict/center None。另取真实乙醇 single→double 输出，接口声明改成错误的 double→double；冻结执行器实际拒绝该声明，镜像不验 from_order，诊断却零声明失配、strict/center True。后者是错声明接口合成，不是冻结执行器执行错误。

**验收：**镜像维护顺序执行后的 ID/键状态，复核协议显式前置条件；失败不能 sanitize 后继续冒称完整对账。保持单次 add_atom、旧键连续净效应和真正零净变化控制。只修诊断适配，不改冻结 executor；测试真实公共执行与诊断同向，而非仅净终态字符串。

### R4-07 [P1] 键立体与非四面体轴静默缺失，中心可在漏变化时 True

位置：[audit.py:1522](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1522)、[1593](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1593)、[1828](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1828)、[2027](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:2027)、[2106](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:2106)。

- 接口合成E/Z变化：strict身份不同，键级/原子属性 diff 空，net_change_empty=False，却报 no_executed_change“实际净变化为空”。在真实远端编辑输出上接口注入中心外E/Z变化，诊断 center=True、extra空、strict=True（期望设为该接口产物）；证明漏轴，不证明冻结执行器生成此反转。
- 两侧非四面体标签先命中“都不是四面体⇒保持”，未到 unsupported；即便内部置 unsupported，公开中心/extra 过滤会丢掉该标志。
- 非四面体真实联合映射控制可给 center=True/strict=False，而代码只 gate增强组，未 gate其声明不支持的非四面体。**本例 strict False 已被审核消费，不声称它直接达到R6。**

**验收：**E/Z按映射几何纳入差分，或明确该轴 unsupported、公开列项并诚实限定中心覆盖；身份不同而图轴空不能称零实际变化。非四面体先判支持范围，未知与“配置保持”分开，unsupported进入公共载荷和适用覆盖。部分/全未指定四面体按所写信息声明行为，不推断实际样品必然是另一物质；一个 useChirality 开关不证明所有立体类型。[RDKit 官方立体说明](https://www.rdkit.org/docs/RDKit_Book.html#support-for-non-tetrahedral-atomic-stereochemistry)。

### R4-08 [P1] 任意 DATA SGroup 注记仍改变严格身份，CX 子集没有闭合

位置：[chemstate.py:143](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:143)、[153](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:153)。清原子/分子prop与坐标后仍默认输出其他CX。

无歧义合成DATA SGroup仅含review_note=foo/bar，不改CO化学图；裸CO及两种注记形成三个state_id。旧五个CO注释确已修，但这个同族非结构注记仍分裂身份。$_AV本轮实测已被移除同ID，不能照搬mimo说它已构成反例。

**验收：**登记化学CX事实与非结构出现元数据及未登记默认行为；已证review_note不入身份。**不把SRU/聚合物/混合组或所有SGroup一概剥掉**，它们可能承载化学事实；未知类型可显式unsupported/拒绝该表示，不能丢事实后称完整。公开结构与strict/ID同源往返，保留增强立体/自由基等控制。[官方CX类型说明](https://www.rdkit.org/docs/RDKit_Book.html#cxsmiles-cxsmarts-extensions)区分Data与polymer SGroups等类型。

### R4-09 [P1] writer 对来源出现、CN-only及结构状态只验部分事实

位置：[store.py:281](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:281)、[303](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:303)、[339](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:339)。

source_product/executed_product 的合法CCO规范态配CCN或非法raw、原结构可用且全轴as_written，put成功；合法事件产物raw换CCN，submit created=True。同图OCC raw正控制合法；不同拼写不等于另一分子，不能为保留前者而允许后者。交付主动登记遗漏仍不满足R3验收。

CN-only CCN状态可改为完整CCO的ID、电荷99、original_available=True、全fidelity as_written后保存。当前空smiles即提前return；**不从CN猜完整结构≠不验CN-only隔离ID和未知契约**。另有规范结构与cn_identity、立体/同位素status不符、非法fidelity枚举/缺轴被保存。

**验收：**所有宣称原结构可得的来源核同源strict身份；合法同图异串/多来源及archive未知仍保留。完整态核CN/status与fidelity形状；CN-only按专用命名空间/未知事实重算和校验，不能占完整身份或虚构电荷/保真。put/submit所有公共路径不一致结构化拒绝、零写入。

### R4-10 [P1] 无完整重复输入的重放仍不能验本事件出现集合，空结构可逃过已存事实检查

位置：[store.py:885](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:885)、[905](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:905)、[924](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:924)、[1236](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1236)。

先提交本事件prod-A、另put同物种无关prod-B，删除A后给states=[]/hypothesis_dict=None重放仍created=False。R4只在caller再次提供states时验证期望集合，持久事件没有准确appearance manifest。保存state内ID改错，或完整产物结构清空+charge99，或CN改CCN，不提供states重放同样成功。空结构被直接跳过，不等于合法CN-only。假设已存前提旧ID问题另见R4-02。

**验收：**首次提交保存本事件准确appearance引用/哈希/位置集合或等价关联；重放从账本校验，不依赖caller重新提供每份dict。核已存载荷ID=行键及完整类型/事实/版本/关系，空串须满足CN-only专用契约。损坏结构化失败、保全不补账。带完整states的旧反例已修控制、无重复dict正常幂等和同图多位置继续通过。

### R4-11 [P1] 旧导入只核CN，没有验证真实父事件产品关系

位置：[legacy_reader.py:203](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:203)、[219](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:219)、[229](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:229)。

合成旧公共API多步：CCO→C[C@H](O)CC→C[C@@H](O)CC→CC=O。将子底物来源指针改为子事件自身的产物，父路径关系仍原样；两产物CN相同、strict不同。导入接受错误手性产物为底物，origin=source_product、无uncertainty；source_event_parent≠path_parent。旧字节不变、archive立体保真仍unknown，**不声称会直接科学verified/R6**；保真未知不能让错误来源关系合法。

同族辅助：被导入event底物声明CCN、path/raw CCO，或product声明CCN、raw CC=O，也未披露记录间矛盾。

**验收：**来源event所属run、parent/path、产品位置/child关系及声明raw/CN整体核对。错关系即使CN同也拒绝或有理由CN-only；不从CN恢复手性，不为服从错误CN丢可信raw。合法多步、root-return、多位置、空指针降级及版本门保留，旧库只读。

## 4. 非阻塞披露与文字项

- **audit.scope被覆盖：**[audit.py:571](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:571)局部checker_scope变量覆盖函数scope参数。显式scope='synthetic:review-scope'，返回仍region_net_change；区分审计用途与checker覆盖，保留调用者范围。该标签错误未单独作为新P1。
- center_evidence的scope与每轴状态结构化输出、展示/导出不截掉；当前理由码和detail已有scope，后续S3展示另验，不要求现在建UI。
- CIP标签不同但映射配置保持时，就地说明优先级重排不等于反转。现两组CIP行为正确，不把披露建议说成旧算法未修。
- plain≡ABS及混合ABS规范化的表示层差异、重叠矛盾组处理和映射号移除说明要明确；不因为RDKit保存显式ABS对象就判本仓规范化必然化学错误。
- 原子属性/键立体的声明语言范围、未指定四面体支持范围及所有未登记CX类型有明确规则；不虚构已实现的full_template/local_delta/equivalence评分。

## 5. mimo R4 的采纳限度

认可其单位未确认仍satisfied、非四面体分支顺序/unsupported漏披露、E/Z身份与理由码矛盾、证据只交叉核两身份等意见，已独立互证。认可全H/电荷账、准确CIP降为披露、旧真实映射和净效应控制方向；不撤销通过项。

以下不能直接照搬：

1. **绑定只补必填或改文字不够。**六个虚构字段照样R6；必须证明诊断针对当前输入执行及覆盖什么产物，hash变化不等于核验变化。
2. **SGroup/SRU不全是非化学。**本审核实证只针对DATA review_note；未成功的SGroup猜测不能报已证缺陷，$_AV本轮反例不成立。未知化学类不能盲剥。
3. **单位不是只改说明。**来源温度单位未知的全绿必须改变，规范键名/assumed注记不是适配校验证据；无量纲键不一律unknown。
4. **部分/未指定立体按所写信息比较。**拒绝指定与未指定互换不证明样品是不同真实物质；不将图表示限制升级成化学物种/酶识别结论。
5. **新变化必须落公共消费者。**unsupported、E/Z、快照覆盖、支持撤销要有实际audit/诊断链回归，不只内部helper/文字登记。

当前不冻结。mimo和交付的全量日志为外部提供材料，不替代本审核明确范围内的独立证据。

## 6. R5 实施与验收要求

仅回修S0–S2，先统一“规范载荷→身份→诊断记录→审核→事件/出现集合”接口，再三线实施。证据必须有真实输入依据，科学前提身份必须随内容变化，快照必须能证明记录了哪些要求，依赖必须按轴保留有效状态，事务必须保存足够信息用于无重复输入重放。这些属于现有底座，不转列尚未实现的S3。

每组P1至少一个小型公共接口先红后绿回归，保留§2通过控制。重点链：真实AtomTool→声明对账/诊断→绑定证据→audit→admission；context历史+候选→审核；put/submit→重开→省略重复dict重放；旧event/path/product来源→单事件及整run导入。接口合成仅用于验证表示/漏轴，标明来源，不冒称执行器行为。

表示违约、错来源和损坏给结构化失败；信息不充分为unknown，可retain，不能一律化学reject。供给环不自动阻断。不改冻结legacy，不启真实模型，不读gold/封存逐题材料，S3继续fail-closed。语义/持久格式变化给版本及兼容/拒绝/迁移策略，不以机械升版或字段存在测试代替行为。

更新自包含无金标mimo请求，由用户转交；意见与代码互证，不自动冻结。交付逐项代码、前后反例、测试命令与日志、版本策略及剩余边界；区分独立证据与实施方声明，不把通用夹具通过写成污染物路径科学性能。

## 7. 放行裁定

**S0–S2继续回修，S3不放行；化学判据/契约未冻结，路径科学性能pending。**后续科学数据不足不阻止当前工程回修，但当前证明链和账本基础缺陷不能用“后续阶段再处理”代替验收。

## 8. 可直接交给实施 agent 的 R5 提示词

```text
请在 /Volumes/CC/Enzyme_Agent/dependingv43 回修 pollutant_pathway_v1 的 S0–S2。先读AGENTS.md、检查HEAD及工作区，保留用户已有文件。仅底座回修，S3继续fail-closed，不实现搜索/终点评测、不改冻结legacy、不读gold/封存逐题材料、不启真实模型实验。

必读绝对路径：
1. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md（第17节裁定优先）
2. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R3_2026-10-06.md
3. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R4_2026-10-06.md
4. /Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r4.md
5. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R4_2026-10-07.md（R4-01～11、§4/5/6为本轮要求）
6. /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r4_codex_2026-10-07/README.md

审核HEAD e80f4594ea44b5f2bf8c78360dc2ed2368dd94ae。若版本已变先说明差异，不回退/覆盖用户工作。312项ppv1测试全过仍不能放行；本轮观察脚本退出0不等于缺陷已修，要转成正确断言的公共接口回归。脚本复制新临时目录再跑，不在证据目录写SQLite/覆盖日志。

完整处置R4-01～11，保留报告§2认可的控制：
- 建可核验的诊断证明链，真实绑定输入/编辑/映射/执行及产物范围；两身份或六条自报字段不够。中心/strict类型严格校验，区域与strict分轴保留。真实断裂分列产物能正确绑定，额外未核实转化不能借一个产物到all_verified；不要求本轮实现S3完整供体模板。
- finite_rule_diagnostic等全部实际审核输入入hash；科学载荷真实不可变或入口复核派生身份。冻结dict普通|=不得修改；hypothesis自身改前提旧ID不能沿用。put/submit/已存replay调用同源完整假设ID和契约验证，保持排序幂等、别名隔离。input_hash已变化的载荷问题不要误写成同hash漏洞。
- 有量纲来源单位未知不能靠assumed_canonical变satisfied；明确归一/依据或unknown，不强制支持换算，不把无量纲键一律unknown。
- live/历史筛选含scenario+phase；快照覆盖核具体要求/边，而非仅阶段存在，空快照不能掩盖孤儿必要要求。事实按适用性可跨阶段服务多边。
- 依赖按轴保留有效支持/反驳/未知，后续再生不洗掉初始供给反驳；恢复初始轴须该轴证据。环不自动reject/defer，S3调度不在此实施。
- 声明镜像维护新增ID和逐操作前置条件，合法新增后续编辑通过、错from_order拒；保持有序净效应及零变化控制，不改冻结executor。
- 键E/Z和非四面体轴支持范围诚实：实现映射差分或明确unsupported并公开披露/限制覆盖。身份不同而图轴空不得称实际零变化；一个chirality开关不证明全范围，接口合成不冒称真实执行器结果。
- 化学CX类型登记，已证DATA review_note不入严格身份；不能把SRU/polymer/所有SGroup盲剥，也不能照搬本轮实测不成立的$_AV反例。保持增强立体、自由基、混合ABS和公开往返控制。
- 所有原结构可得来源核raw与strict身份，同图OCC异拼写仍接受，CCN跨分子/非法raw拒。完整state的CN/status/fidelity契约闭合；CN-only按专用隔离ID及未知事实校验，不从CN猜完整结构，不能借空smiles逃逸。
- 首次提交持久本事件准确appearance集合/哈希/位置；states=[]/hyp=None重放仍校验已存完整内容、ID/版本/类型/关系。空结构不能自动当CN-only；损坏保全结构化失败，不静默补账。
- 旧导入核run、父路径/来源event、产品位置/child关系与raw/CN声明；CN相同不证明来源/strict一致。错关系拒绝或有理由CN-only，不为服从错误CN丢可信raw，旧库只读。
- §4审计scope变量覆盖、checker scope同屏、CIP披露、立体/ABS/CX范围说明一并整理；保留已修per-product off披露、空计划/跳阶段契约。

先统一载荷、身份、证明记录和出现集合接口，再三线并行。每组P1用合成公共链先红后绿，禁止改断言掩盖科学输入变化、只测字段/版本/docstring或把缺口改文字后宣称关闭。未知可retain，表示违约结构化失败，不将计量闭合/图对称当机制或酶选择性证明。

交付 /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R5_2026-10-07.md，逐项列代码、前后反例、测试命令/日志、版本兼容及剩余边界。更新自包含无金标mimo请求，由用户送评，不自行外发、不宣称冻结或路径科学性能通过。完成后停止跨阶段实施，交回本会话独立review，通过后再讨论S3。
```
