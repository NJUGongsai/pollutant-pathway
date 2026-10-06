# pollutant_pathway_v1 S0–S2 第三轮独立复审（R3）

日期：2026-10-06。审核仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。锁定 HEAD：`af14fb2bb66e8afbbbbecd38722a9cacbd0699c3`；R2 基线：`0002f71af23a2d00db7734e15bf1142c64c85145`。

**结论：R3 有实质修复，但 S0–S2 尚未通过，不放行 S3，不冻结化学判据或契约。** 当前问题已经超出“补一些工具”的层面：审计接口可以把另一反应的证据当成本反应的证明，遗漏路线条件和继承依赖；结构诊断存在立体误判；公共写入和重放仍不能保证化学身份与账本内容一致。这些缺口一旦接入搜索，会把不充分的证明扩大成整条路径的“全部核实”。

现有 **226 个 ppv1 测试独立复跑全部通过，0 skipped**，但新增公共 API 反例仍出现错误 R6 放行。本轮只进行代码审核和合成夹具验证，不改实现、不运行真实路径实验、不调用模型、不读 gold 或封存逐题材料。审核时原工作区只有用户已有的未跟踪 `docs/mimo_ppv1_chem_review_response_r3.md`；结束前 HEAD 未变化。

## 1. 依据、证据与采信范围

本轮读取：

- [实施书及第 17 节最终裁定](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md:761)。
- [R2 独立复审](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R2_2026-10-06.md)。
- [R3 回修交付书](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R3_2026-10-06.md)。
- [mimo R3 化学意见原文](/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r3.md)及实际代码、七个 ppv1 测试文件。

化学、条件与科学前提、存储与适配三线分别审核；主审另做证据绑定与门禁探针，并独立复跑三线探针。永久证据入口：[README](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r3_codex_2026-10-06/README.md)。附件含化学 40 条 JSONL、条件 36 个顶层案例、存储 29 条 JSONL、主审核绑定探针、独立测试日志及 SHA-256 清单。记录数包含控制与环境记录，**不是新增失败测试数**。

| 核查 | 实际证据 | 结论范围 |
| --- | --- | --- |
| ppv1 单测 | 隔离复制 src 与七个 ppv1 测试，`pytest -p no:cacheprovider -q -rs tests`：226 passed in 1.91s | 独立复跑；无跳过；不证明路径科学性能 |
| 全量非 slow | 交付书报告 837 passed / 16 deselected | 实施方提供；本轮未独立重跑 837 项，不写成主审核实 |
| 代码改动范围 | 对比 R2 基线，实施改动在 pollutant 包、ppv1 测试与文档 | 未发现本轮改写冻结 legacy 执行链；不把静态范围核查等同全量行为证明 |
| 新 profile 执行 | [runner.py:135](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/workflow/runner.py:135) 继续拒绝未交付的 S3 | 正确阶段边界；本轮不要求提前建搜索/队列/终点评测 |
| 化学意见 | mimo 意见与合成程序证据逐项互证，补查 RDKit 官方文档 | 意见不是独立性背书；冲突处以明确契约和可复现证据裁定 |

探针性质必须区分：真实 AtomTool 执行例保留 validation/execution 输出；中心内手性反转的一个例子是接口合成，不声称冻结执行器会产生该反转。条件/依赖探针使用合成的已登记 checker 载荷隔离条件逻辑，不声称该载荷证明真实生物反应。存储损坏探针在临时 SQLite 操作，不动旧库或任何实际 run。所有合成反应只检验程序口径，不证明机制或酶选择性。

## 2. 对 R2 修复的实际判定

交付书“十二项 P1 与 P2 全部处置”不能解释为全部验收关闭。原反例有许多确已翻转，但对应公共边界还有残余或相邻反例。

| R2 项 | 本轮认可的修复 | 关闭状态 |
| --- | --- | --- |
| R2-01 覆盖/缺状态/自报签名 | 无 context 为 unknown；窄 scope 不到 R6；缺 state 得 R1b 而不崩溃；自报签名不再授信 | 部分关闭；证据只认注册名字，未绑定输入/完整范围，见 R3-01 |
| R2-02 严格身份/公开表示 | 简单 plain≡ABS；AND/OR 整组反转归一、部分反转区分；公开增强立体往返 | 部分关闭；混合 ABS 和非结构 CX 元数据仍进入错误身份，见 R3-04 |
| R2-03 实际净变化/联合中心 | noop/逆操作零净变化为 unknown；环己烷相邻与对位共同映射反例正确拒用；plain/mapped 不同为 unknown | 部分关闭；手性、CIP、编辑协议净效应、证据轴消费见 R3-01/02/03/05 |
| R2-04 阶段/分支 | 原同一 scenario 的阶段反例及父/兄弟分支隔离修复 | 部分关闭；跨 scenario 同名阶段和自身可变载荷见 R3-06/08 |
| R2-05 条件比较 | point×interval/退化区间、显式 K unknown、无关供体 absent unknown、多供体共存修复 | 部分关闭；matrix 字符串及来源单位契约见 R3-12、§4 |
| R2-06 依赖循环 | 再生-only 保留启动未知；有初始供给支持可清除；环不自动 reject | 旧假绿已关闭；继承依赖消费与后续支持轴覆盖见 R3-07、§4 |
| R2-07 科学前提身份 | 同反应不同条件/依赖产生不同 hypothesis_id，可共存 | 部分关闭；真实输入 hash、可变载荷、排序幂等见 R3-08 |
| R2-08 state/appearance | 同图不同 fidelity 共存；root-return 两事件；同事件同图不同位置不再覆盖 | 主要旧反例关闭；不据此宣布整个账本完整，重放见 R3-10 |
| R2-09 公共事务/重放 | 少报参与物、假设关系不符、非法投影/互斥计划被拒；整类必要记录缺失直接重放报损坏 | 部分关闭；state 科学事实和部分出现/内容损坏见 R3-09/10 |
| R2-10 版本门 | writer 首次写入显式未知对象版本拒绝；未知库版本在写前拒绝 | 已测写入边界关闭；直接 audit/单事件导入和已存载荷版本仍有绕过，见 R3-08/10/11 |
| R2-11 旧导入 | 子路径两个指针为空正确 CN-only，不借根串；旧文件只读 | 部分关闭；非空错指针、根 raw/CN 矛盾见 R3-11 |
| R2-12 逐产物门禁 | 默认 on：全拒 reject，部分拒 retain 且保留逐产物拒因 | 原默认消费漏洞关闭；显式 off 的结果披露见 §4，不称默认拒绝又被绕过 |

P2 原项中，真实断键夹具与 skip、实际相邻池哈希链、scope/coverage、同值多来源、basis 形状、study count 下界、新 provenance 可解析引用等已有有效修复。SearchLimits 草案往返和零预算保持正确。以下残余不会撤销这些已确认修复。

## 3. 阻塞 S3 的问题与 R4 最小验收

### R3-01 [P1] 中心证据没有绑定本反应，受限区域检查仍可冒充完整核实

位置：[audit.py:544](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:544)、[证据助手:1840](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1840)。当前只校验 checker_version 在注册表；`center_match=True` 即授予中心 verified。助手丢弃 strict 轴、实际输入绑定和检查范围。

**真实诊断复用反例：** AtomTool 对乙醇 C–O 单键改双键，实际产物 CC=O，strict=True、区域=True。原样取其中心证据分别审计 `CCO+O=O→CC(=O)O+O` 和完全不同的 `CC=C→C1CC1`，两者都得到 `expand/R6:all_verified_no_conflict`。只给 `{checker_version:'ppv1-donor-diagnostic-3', center_match:True}` 也可到 R6。证据没有核对 hypothesis、输入/产物、映射/编辑及执行结果。

现有 [test_ppv1_r2_chem.py:361](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_r2_chem.py:361) 恰以乙醛诊断支持乙酸假设，并把 expand 当正例。226 项通过包含这个过强断言，必须修正夹具和断言，不能继续拿它证明“真实 checker 已验证本反应”。

**同反应独立反例：** R3-02 的真实产物与同一个合成假设配套，补 `[H]` 仅闭合数值账，诊断 strict=False、区域=True；助手丢弃 strict 后仍 R6。不是只有跨反应复用才会出错。

**验收：**证据携带规范化输入绑定、checker 版本/支持范围、实际轴结论及可复查依据；真实消费验证绑定，而非仅检查字段有值。跨反应、改产物/编辑/映射、无依据 True 均不得认证。区域匹配 True 和 strict False 可以分别成立；适用的失败/未核实轴不能在完整 transformation/all_verified 语义下消失。其他确定性 checker 可独立注册，**不强制所有 checker 都做 donor strict，不一律把区域 True 改 False**。完整供体变换模板仍可排 S3，S2 受限区域证据必须诚实限定其覆盖。

### R3-02 [P1] 联合对称映射忽略指定手性，把不同严格产物说成等价

位置：[audit.py:1508](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1508) 明确 `useChirality=False`；[1754](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1754) 据此授予 symmetric_equivalent。

真实执行：底物 `C[C@H](Cl)[C@H](Cl)C`，供体指定中心 idx {0,1}，实际断另一端 {3,5}；声明与执行对账无失配。实际产物 `C.C[C@H](Cl)[CH]Cl` 与指定位点预期 `C.C[C@@H](Cl)[CH]Cl` 是不同 strict 身份。忽略手性有两个自匹配，考虑指定手性只有 identity；当前仍 center=True、strict=False，extra/missing 均空。

**验收：**对完全指定的绝对四面体夹具，不能使用不保留这些立体事实的映射授予等价；同时保留真 C2 对称体和环己烷的正控制。声明支持的手性/增强立体范围及搜索截断行为；不支持或截断为 unknown。`useChirality=True` 能修上述例，但不能未经验证宣称一个开关覆盖全部立体表达。图对称不证明酶识别等价。[RDKit 官方增强立体匹配说明](https://www.rdkit.org/docs/RDKit_Book.html#support-for-enhanced-stereochemistry)列有 chirality/enhanced stereo 选项。

### R3-03 [P1] CIP 标签变化被当构型变化；换准确 CIP 算法仍不够

位置：[audit.py:1289](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1289)、[1308](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1308)、[1355](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1355)。程序把 CIP 前后不等直接写为 stereo 改变并加入实际变化中心。

两组真实执行反例：

1. mimo E-ii：`C[C@H](Cl)[C@H](Cl)C` 正确断 idx 0–1，远端 idx 3 的映射邻居/H/四面体配置保持；legacy CIP R→S，准确 CIP R→R。当前 strict=True，却因假远端 stereo 变化 center=False。
2. 本轮新增：`CCC[C@H](O)CC` 的 idx 5–6 单键改双键，产物 `C=C[C@@H](O)CCC`。未编辑 idx 3 的映射邻居与配置保持；**legacy 和准确 CIP 都 R→S**，是配体优先级改变。当前仍 strict=True、center=False，误报中心外构型变化。

**验收：**比较映射配体下的配置保留/反转、手性创建/丢失，并区分描述符优先级重排；邻居序变化时不能直接比较 `@/@@` 或 chiral tag。准确 CIP 用于标签，不把 raw R/S diff 当反转证明；复杂/不支持情形保持 unknown。必须同时测试上述两组和真实反转控制，不能仅替换 API。[RDKit 立体章节](https://www.rdkit.org/docs/RDKit_Book.html#stereochemistry)及[准确 CIP API](https://www.rdkit.org/docs/source/rdkit.Chem.rdCIPLabeler.html)支持区别标签计算与立体表达。

### R3-04 [P1] CX 身份混入绘图注释，混合 ABS 冗余仍造成身份分裂

位置：[chemstate.py:136](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:136) 默认输出全部 CX；[141](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:141) ABS 正则只处理有限边界；[301](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:301) 据该串派生身份。

混合例 `C[C@H](Cl)[C@H](F)Cl |a:1,&1:3|` 与 `|&1:3|` 分裂，OR 混合与 radical+ABS 同样分裂；RDKit 类型化组规范化对照得到相同结果。另有五个 ordinary graph 都为 CO 的输入：普通 CO、原子标签、两套二维坐标、任意 atomProp note，产生五个 state_id。改变绘图坐标或注释不应改变本仓严格分子图身份。

**验收：**定义化学身份保留的 CX 事实子集，出现/显示元数据另存；规范处理混合 ABS，保留增强立体、同位素、电荷、自由基等已支持事实；公开完整结构及 strict 同源、重建同身份。不要剥全部 CX，也不要按逗号随意切段删 ABS，逗号同样用于组内原子列表。原简单 ABS、AND/OR 整组及部分反转控制持续通过。[官方 CXSMILES 说明](https://www.rdkit.org/docs/RDKit_Book.html#cxsmiles-cxsmarts-extensions)确认默认写出内容包括坐标、标签及原子属性。

### R3-05 [P1] 声明对账没有遵守真实 add_atom 协议及有序操作的净效应

位置：[audit.py:1391](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1391)、[1411](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1411)、[1439](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:1439)。冻结执行器 [atom_tool.py:482](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/atom_tool.py:482) 的 add_atom 会自动形成 anchor 单键。

- C 上合法 `add_atom(atom1=A_C_1, element=O, new_atom_id=A_O_1)`，validation/execution True，产物 CO；当前误报隐含 anchor 键 undeclared_bond_change，strict/center 均 None。
- 乙醇同键按序 single→double→single→double，三个操作合法，最终 CC=O、净变化非零；当前要求中间 single 也等于最终 double，误报声明失配，strict/center 均 None。

**验收：**按既有编辑协议解释有序操作及隐含键，核对执行过程和最终净效应；中间操作不必每条留在最终 diff。无需改冻结执行器，不增加协议不需要的重复 form_bond。保留零净变化为 unknown。中心内/外实际非键属性变化须可公开核查；不支持的属性声明按 checker scope 明示，不能在“对账完整”语义下抹掉。中心内手性反转披露案例是接口合成，不能写成真实执行器会执行未支持操作。

### R3-06 [P1] 条件 helper 的正确路线快照未被实际审计消费，外来绑定还能绕过本步冲突

位置：[audit.py:623](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:623)、[path_context.py:530](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:530)、[730](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:730)、[851](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:851)。audit 直接重评累积要求；事实缓存只按 phase，要求匹配当前 scenario，不消费完整历史作用域。

合法显式场景转换：sA:p0 有氧；sB:p0、sB:p1 无氧。父在 sA:p0，用户有来源地转至 sB:p1，子步要求无氧。

| 父要求 | child current / route helper | 实际 audit→admission |
| --- | --- | --- |
| 父必需无氧，旧边已冲突 | compatible / conflict | **verified→expand/R6**，洗掉旧冲突 |
| 父必需有氧，旧边满足 | compatible / compatible | **violated→defer/R3**，错杀合法路线 |

另一个公共输入：当前 p1 有氧，新假设必需无氧，但 requirement 预填 `introduced_phase_id=p0`、`introduced_edge=another:hypothesis`；p0 无氧，当前代码保留外来绑定，仍 verified/R6。

**验收：**事实按场景/阶段适用性筛选；要求与评估绑定所属边及场景/阶段。明确跨阶段的事实可以服务多条边，不强制每条事实逐边绑定。已选旧边采用可核查快照，本候选新增要求在自己的当前作用域评估，再合取路线。继承旧要求保留原绑定，新假设自身要求不能自称属于另一边。错绑定结构化拒绝；不能只把 audit 接到 route_assessment 而漏掉新候选要求。两行表和错绑定均测试完整 `audit_hypothesis→decide_admission`，不只 helper。

### R3-07 [P1] 继承依赖被审计遗漏，缺解析被解释成“没有依赖”

位置：[audit.py:643](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:643)、[662](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:662)。代码只取 hypothesis.dependency_refs。

context 含 `dep:unresolved_upstream`，本假设无新增依赖；未传外部 unresolved 列表时得到 verified/no_unresolved_dependencies 和 R6。补传同一个未解决引用才变 unknown/retain。

**验收：**审计 context 与 hypothesis 引用并集，逐项有明确解析状态/依据；解析未提供不等于引用不存在。context-only、hypothesis-only、并集、None、空列表、仍 unresolved、明确支持均通过真实消费接口测试。不能要求未来 S3 调用者手工重复复制引用来补洞；unknown 仍可 retain/按显式策略探索，不自动 reject。

### R3-08 [P1] input_hash 遗漏真实科学输入，前提载荷可变却不换身份，排序幂等只做了半套

位置：[audit.py:682](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:682)、[hypothesis.py:433](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/hypothesis.py:433)、[449](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/hypothesis.py:449)、[store.py:358](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:358)。

以下每对只改变实际输入，检查/放行改变，input_hash 却相同：依赖已解决 vs unresolved；同 checker 的中心 True vs False；同 state_id 的 raw vs archive fidelity；charge as_written vs unknown。它们是调用前已存在的输入，不可仅改名“判定前输入 hash”来解释。

`frozen_nested_source_refs_mutable` 对 context 中 frozen Requirement 的 source_refs 列表 append 引用，条件 unknown→verified/R6，context_id 与 input_hash 不变。分支深拷贝已经修好；这里是对象自身前提改变后身份仍旧。hypothesis 的 caller-owned nested dict 也能改变内容而保留旧 ID。相同 oxygen/pH 要求仅调换顺序，hypothesis_id 相同，payload 未归一，第二次 put 却报冲突。

构造边界还有：缺 level/value 可生成假设，audit 才裸 TypeError；非法 level/反向区间可入假设；直接对象的缺/未来 context 版本可到 R6，虽然 from_dict 正确拒绝。是否支持 Requirement 对象由接口决定，但不支持时也应结构化契约错误。

**验收：**实际使用的证据、解析状态、state appearance/fidelity、完整上下文科学载荷、范围及版本均进入规范化 audit 输入身份；同语义重放稳定，不同有效输入不可同 hash。前提真实冻结或在入口复算验证，修改即拒绝/换身份；排序同时落实到 payload 与存储语义比较。requirements 完整校验和版本门接到真实对象入口；None 与 [] 的解析语义不混同。结构指纹可另设，不能替代完整输入 hash。

### R3-09 [P1] 公共 writer 仍可把另一结构挂到合法 state_id 下

位置：[store.py:263](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:263)、[539](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:539)。writer 校验版本/已有字段相等，但不重新校验新 state 身份与科学事实。

`put_state` 接收 CCN 内容配 CCO state_id、CCO 的 formal_charge=99、CCO 语义配 CCN raw、非法 smiles_isomeric。事务反例：合法 CCO→CC=O 事件仅替换提交产物为 CCN 内容并保留乙醛 state_id，`submit_event` 仍 created=True，存下 CCN。参与物/假设相互一致，未阻止身份欺骗。

辅助零系数例同步修改 event/hypothesis 参与物，保留原派生 ID，仍提交成功；它证明 writer 没有重验构造契约/身份，不单独声称是仅系数算法出错。

**验收：**公共 put/submit 对完整 strict 状态按规范重推身份和结构事实，核对表示层；按来源/fidelity/CN-only 类型合法处理未知，不强行从中和 CN 重建完整结构。参与物、hypothesis、event 派生身份与合法系数在提交边界复核；不一致结构化拒绝、零写入。工厂校验不能代替接受任意 dict 的公共 writer。交付承认 store 未硬接重推导，这属于当前 S1 事务，不应转列 S3 排期。

### R3-10 [P1] 重放只确认存在，没有校验已存内容、完整事件身份及本事件出现集合

位置：[store.py:639](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:639)、[661](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:661)、[681](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:681)。

临时库先完整提交，再删本事件 prod-A appearance，只留无关 prod-B；带原全部 states 重放仍 created=False 成功。以下内容损坏同样被当成功：appearance raw 改 CCN 不改 hash；event participants 清空/未来 schema/身份列改错；hypothesis 内 ID 或 schema 改错（不随请求重复提供 dict）；state charge/schema 改错（states=[]）。不改 SQL、仅 replace 输入 event 的 run/context 而保留 event_id，也直接幂等成功。

辅助导入管线例：删新账本 states/appearances/hypotheses/provenance 后，`import_legacy_run` 先 put 补回依赖，再返回 n_replayed=1，无损坏说明；绕过直接 submit 已修的缺行检测，见 [legacy_reader.py:358](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:358)。

**验收：**复算保存 payload/hash、schema/载荷 ID/完整事件身份与引用关系，核对本次提交的全部期望 appearance 及其内容；不能以“有一条同物种出现”代替完整集合。检查不依赖调用者重新提供每份 dict。损坏结构化拒绝并保全，不静默补写；若另外设计恢复必须显式版本化、权威记录校验和留轨迹，本轮保持已声明的无自动修补策略。保留整类记录缺失直接 submit 已修控制。

### R3-11 [P1] 旧导入相信非空错来源引用/矛盾根串，单事件入口还能绕版本门

位置：[legacy_reader.py:114](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:114)、[144](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:144)、[157](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:157)、[194](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:194)。

CCO→CC=O→乙酸的子底物原 CN 为 CC=O，来源指针改为确实存在但错误的乙酸产物行，直接 import 仍返回乙酸/source_product、无 uncertainty。根保存 CN 为 CCO、root_smiles 为 CCN，也返回 CCN/raw_input、无 uncertainty。当前只确认引用存在或比较两个保存 CN 声明，未核 raw 与身份及父事件产品关系。

旧库 meta 显式 future-legacy-store-999 时，`import_legacy_run` 正确拒绝，公开 `import_legacy_event` 却接受；run_identity 显式未来版本同样被接受。所有探针旧库字节不变。

**验收：**所有公开导入入口共同执行版本门；根 raw 重算旧身份并核声明，archive 来源同时核父事件/产物位置/底物身份。矛盾引用结构化拒绝或有依据 CN-only，保留原因/未知轴；兼容合法旧无新增字段格式，不借根串补非根。保持正常两步、root-return、同图多位置及空指针降级的控制。

### R3-12 [P1] 无语义约束的 matrix 字符串不等被当必要条件硬冲突

位置：[path_context.py:648](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:648)。事实 sandy soil、来源必要 soil，程序仅因字符串不同输出 conflict/value_mismatch。未定义互斥枚举、实体映射或范围关系，文本不等不能证明环境不相容。

**验收：**同词、来源支持的同义/包含关系、确定互斥和不可解析标签分开处理；未解析 matrix 可先 unknown/unsupported，不要求本轮建完整环境本体。氧的明确互斥枚举及已经修好的实体 present/absent 保留。不能照搬“任意开放字符串精确不等⇒硬 conflict”。

## 4. 应一并整理的边界与披露项

| 项目 | 证据/限度 | R4 要求 |
| --- | --- | --- |
| 来源单位未知 | 显式 K→unknown 已修；无 unit 的来源温度目前按 temp_C 的 °C 比较 | 可采用明确的规范输入单位契约，但必须区分已归一输入与原来源单位未知，适配器校验；注记不能把未知来源变成 verified，不要求支持所有单位换算 |
| 支持轴覆盖 | initial_supply supported 后再加 regeneration supported，最近 support_axis 覆盖前轴，启动未知重新出现 | 按轴保存/消费支持；方向是保守误降级，不称旧再生假绿原样存在 |
| per-product off 披露 | 同部分拒绝输入，on 正确 retain/R2p；显式 off 只返回 R6，没有逐产物拒因 | off 是允许的版本化 diagnostic 策略，但报告仍保留结果与未消费范围；不撤销默认 on 修复，也不提前要求 S3 展开执行 |
| 空展开计划 | 有产物的事件提交 entries=[] 被接受 | 对每个产品明确 expanded/deferred/not_tracked 与原因，或明示计划不完整；只补载荷契约，不实施 S3 队列 |
| 跳处理阶段 | 不同 hash 断链已拒；同 hash 跳阶段、空 transition_reason 仍通过 | 与“跳过须显式登记”文字统一，保留跳过原因；不把同 hash 连续记录说成哈希链已断 |
| 中心属性披露 | 内部 atom_records 有变化，公开 center/extra 列表可清掉它 | 随 R3-01/05 暴露实际属性及 scope；区域包含关系和完整操作对账分别命名 |
| AND/OR 文字 | 请求文档 34–35 行倒置；测试 186–187 行把 OR 写作 mixture | AND 是同时存在的混合声明，OR 是未指定具体成员的单一未定声明；多组组合不要一律简化成全分子只有两个构型；实际整组反转程序控制已通过 |
| identity 说明 | RegistrationHash 无条件一致、无组一定逐字 plain 的表述过宽 | 限定已验证层/子集，列 CX radical 等例外；本仓 plain≡ABS 是明确设计，不能用 registration hash 一概替换 strict identity |

## 5. mimo R3 意见的采纳裁定

混合 ABS、该 legacy CIP 远端反例、手性盲共同映射、strict/scope 丢失、中心属性漏披露、hash 漏中心/依赖、requirements 构造缺口均获程序互证。其“不冻结”的结论方向正确，但以下修法不能原样交给实施 agent：

1. **准确 CIP 不等于构型判据。**新真实执行反例证明准确 R/S 也会随配体优先级变；必须按映射配置比较。
2. **strict=False 不必把区域=True 改成 False。**分别保存事实；完整验证不能忽略适用失败；其他独立注册 checker 可以验证自己的范围。
3. **ABS 不能简单按逗号拆删。**优先使用类型化组/正确 CX 解析，并控制非结构元数据。
4. **input_hash 不能靠改名免责。**已传入的解析状态、证据和 fidelity 是真实科学输入，要绑定和规范化。
5. **matrix 文本不同不证明不相容。**规范键单位也不证明原来源单位已知；单位和标签的输入契约应明确。
6. **阶段 helper 正确不等于 admission 正确。**跨场景及新候选要求绑定必须测真实调用链。

AND/OR 的文字按 [RDKit 官方定义](https://www.rdkit.org/docs/RDKit_Book.html#support-for-enhanced-stereochemistry)改正；这不表示本轮身份程序行为也倒置。当前核算的全 H、形式电荷与同位素等控制通过，不把它们说成电子/自由基、机理或环境可行性已证明。

## 6. R4 实施组织与验收口径

只回修 S0–S2，可继续三线并行：化学/证据（R3-01～05）、条件/前提（R3-06～08、12）、存储/适配（R3-09～11）。**先对齐证据结构、规范身份与载荷接口，再独立实施**，避免不同线各做一个看似正确但互不消费的 helper。

每个 P1 至少有一个小型公共边界回归，修复前失败、修复后通过；必须保留本轮认可的控制。优先验证 `真实执行结果→诊断→证据→audit→admission`、`历史上下文+候选→audit→admission`、`公共 put/submit→重开/重放` 和单事件/整 run 导入。字段存在、注册字符串、docstring、schema 升版不能替代行为测试。

要求：

- 对证据伪造/错绑定、表示违约给结构化失败；科学信息不充分为 unknown，可 retain，不能一律变成化学不可能/reject。
- 科学载荷、版本、身份及实际审计输入 canonicalization 同源；顺序无关在真实存储与重放也成立。
- 改变科学语义或持久格式时，交付明确版本与支持/拒绝/迁移策略；不能只全族机械升版而不修消费者。
- 继续 S3 fail-closed，不建真实搜索/终点评测，不改冻结 legacy 行为；不使用 gold/封存逐题材料，不启真实模型实验。
- 将本轮合成反例转成受控回归，附件复制到临时目录再运行，不能在审核证据目录写 SQLite/覆盖日志。
- 更新自包含、规则级、无金标的 mimo 请求，由用户转交；mimo 回复须与程序证据互证，不自动冻结。
- 交付逐项记录 R3-01～12 与 §4 的代码/测试、前后行为、版本和剩余限度；独立证据和实施方声明分列。报告全量测试时给完整命令及真实日志摘要，不把 fixture 通过写成污染物路径科学性能。

## 7. 审核放行结论

当前为 **S0–S2 继续回修，S3 不放行；化学判据/契约不冻结，路径科学性能 pending**。不要求因后续 S5 数据尚未齐备而停止本轮工程回修。

要放行的是可以诚实表示未知、不会给错反应发证明、条件/依赖不漏消费、身份和重放一致的底座。R3 已修复一批具体问题，但上述公共边界未达到这一要求。完成 R4 后由用户把交付及新化学回应交回本会话 review，不自行跨阶段。

## 8. 可直接复制给实施 agent 的 R4 提示词

```text
请在 /Volumes/CC/Enzyme_Agent/dependingv43 回修 pollutant_pathway_v1 的 S0–S2。先读 AGENTS.md，检查 HEAD 和工作区，保留用户已有文件。本次不放行 S3，不实现搜索/终点评测，不改冻结 legacy 行为，不读 gold/封存逐题材料，不启真实模型实验。

必读绝对路径：
1. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md（第 17 节裁定优先）
2. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R2_2026-10-06.md
3. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R3_2026-10-06.md
4. /Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r3.md
5. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R3_2026-10-06.md（本轮 R3-01～12、§4、§5、§6 为回修要求）
6. /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r3_codex_2026-10-06/README.md

审核版本 af14fb2bb66e8afbbbbecd38722a9cacbd0699c3；若 HEAD 已变，先说明差异，不回退或覆盖用户工作。现有 226 项 ppv1 测试全部通过仍不能放行；正例中把乙醛诊断用于乙酸假设的过强断言必须纠正。先在临时目录复跑附件；附件含合成 SQLite 脚本，不能直接在证据目录执行或覆盖审核输出。

完成全部 R3-01～12 和 §4 的处置，并保留确已修复控制：
- 证据绑定本假设的结构/产物/映射/编辑/执行结果，明确 checker scope 和各轴；不能凭注册版本+True 授信。区域 True 与 strict False 分别保留，完整 all_verified 不忽略适用失败。完整 donor 模板仍可排 S3，限定区域 checker 不冒充完整验证。
- 指定手性的联合映射、映射配体下的配置变化、CIP 优先级改写分别处理。换 rdCIPLabeler 或单开 useChirality 不足以宣称全范围解决；保留真实对称正例和 unsupported/truncated unknown。
- 化学身份使用化学 CX 事实子集，移走绘图/任意注释，正确处理混合 ABS；不要逗号盲拆或剥全部 CX。公开结构、strict、state 身份同源往返。
- 遵守现有 add_atom 隐含锚键和有序操作净效应，不改冻结 executor，不增加多余 form_bond。公开中心内/外非键属性及限制范围。
- 实际 audit 消费旧边路线快照与本候选新增要求；要求及评估绑定 scenario+phase+edge，事实按场景/阶段适用性筛选，明确跨阶段事实可服务多边。新要求不能冒称属于另一旧边。合并 context/hypothesis 依赖，缺解析不等于没有依赖。
- 实际科学输入完整入 hash；嵌套载荷冻结或入口复核身份；同语义排序同时归一 payload 与存储比较；requirements 和对象版本在真实入口结构化校验。
- 公共 put/submit 重验 state/参与物/假设/事件身份及事实，按来源和 CN-only 保留未知；违规零写入。重放校验已存内容/hash/版本/完整身份及本事件全部 appearance，不依赖调用者重复提供 dict，不静默补账；导入入口不得先 put 绕过损坏检测。
- 旧导入核根 raw/CN 与父事件产品关系，所有公开入口守版本门；错但存在的引用不能当完整结构。保持旧库字节不变与已修合法导入控制。
- matrix 无语义关系先 unknown；来源单位未知不冒充规范 °C；依赖支持分轴保留；显式 per-product off 仍披露结果；空展开计划和跳阶段留痕契约闭合；AND/OR 与 RegistrationHash 文字按范围纠正。

可三线并行，但先统一证据/规范身份/载荷接口。每个 P1 用合成公共 API 回归先红后绿，重点测真实消费者链，禁止改断言掩盖科学输入变化或只用文档/版本字符串测试代替行为。科学未知可以 retain，不一律 reject，不把计量闭合/图对称等同反应可行性或酶特异性。

交付 /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R4_2026-10-06.md，逐项列代码、前后反例、测试命令与日志、版本/兼容策略和剩余边界。更新自包含无金标的 mimo 评审请求，由用户送评；不自行外发，不宣称化学冻结或路径科学性能通过。完成后停止跨阶段实施，交回本会话独立 review，review 通过再讨论 S3。
```
