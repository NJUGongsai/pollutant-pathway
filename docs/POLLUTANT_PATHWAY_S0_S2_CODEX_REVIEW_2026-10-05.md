# pollutant_pathway_v1 S0–S2 实现与化学判据复核

- 日期：2026-10-05
- 审核仓库：/Volumes/CC/Enzyme_Agent/dependingv43
- 审核提交：7fb198ff5a1fde7425e1a66e6d5ef2a86370734c
- 实施基线：536c977b6f23531a0f65e69e93a7a2799bf7e3a0
- 结论：**S0–S2 暂不通过冻结审核，暂不放行 S3；先完成本报告回修，再提交复核。**
- 优先级：本文 P1 指新 profile 启用前必须修复的阻塞项。新执行流尚未启用，不将这些缺陷描述为已经发生的生产事故。

## 1. 审核结论与证据边界

整体方向可保留：新旧 profile 分开、严格结构身份与 CN 评分身份分开、备选反应与共同产物分开、事件／报告投影／展开计划分开、诊断与 admission 分开。这些抽象符合污染物降解路径预测的目标。

但当前实现还不能保证一条路径的结构、条件、计量和证据沿途保持真实。已经复现的后果包括：未配平反应得到 full_balance verified；已知条件冲突在下一步变成 compatible；同一中间物再次出现导致导入失败；事件提交成功但产物引用不存在。**这些是 S0–S2 底座缺陷，不能等 S3 搜索跑起来后再补。**

本审核核对了升级规格、交付书、mimo 请求／回应和当前源码，使用并行专项审核后由主审核复跑边界脚本：

| 证据 | 本轮结果及解释 |
|---|---|
| 三个新增测试文件 | 在仅复制 src 与三个测试文件的可写隔离目录中，主审核复跑：88 passed in 1.89s |
| 化学计量／严格身份／供体复现 | 主审核复跑成功；发现假 verified、增强立体身份碰撞等 |
| 条件／上下文／来源复现 | 主审核复跑成功；11 个反例全部重现 |
| 存储／导入复现 | 主审核复跑成功；连续两步导入失败、未知 schema 写入、悬空引用等重现 |
| 全套 699 passed, 16 deselected | 是交付书报告的结果；本轮未独立复跑全部 699 个测试 |
| 路径科学性能 | 未验收；合成测试不能证明真实降解路径准确率、生物学可行性或费用优势 |

隔离测试目录为 /private/tmp/ppv1_code_review_h38khtzn。最初在原仓库直接测试时，身份测试要向源码目录写临时探针，被本会话文件权限阻止；隔离副本全部通过。这个权限失败不计作实现回归。

本轮没有修改源码、没有读取 gold／封存逐题材料、没有发起真实模型请求，也没有运行真实题目实验。独立复现脚本见 §5。

## 2. 必须先回修的实现问题

### F01 [P1] 完整元素账漏算氢；参与物歧义仍被当作完整计量

位置：[audit.py:174](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:174)、[audit.py:303](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:303)、[audit.py:322](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:322)、[substrate_profile.py:97](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/substrate_profile.py:97)。

元素计数只遍历 RDKit 图中的原子顶点，漏掉隐式氢及重原子上的显式氢计数。因此 CCO → CC=O 在声明计量完整时，实际 ΔH=+2，却被判元素／电荷 verified、participant_accounting=full，并进入 R6 expand。隐式 H、括号显式 H、独立 H 顶点输入经过规范化后都能复现。

反向错误也存在：CCO → CC=O + [H][H] 的完整元素差为零，当前实现反而报 H:-2。正确计量对照 CCO + O=O → CC(=O)O + O 的元素差为零。这些例子仅验证元素账，不能证明反应或酶在指定环境中可发生。

更严重的是，[test_ppv1_s2.py:365](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_s2.py:365)将 2 C2H6O + O2 → 2 C2H4O2 写成“配平”，[同文件:396](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_s2.py:396)断言 verified；该式实际缺 4 个氢。现有正例在保护错误。

此外，ambiguous_participants=True 时，完整度与 full_known 不检查该标记；未确认重复条目是否为并行计量贡献，也能被计成 full／verified／expand。

回修与验收：

- 统一包含全部氢的组成核算；显式氢、隐式氢不得漏算或重复计数，同位素信息不得在身份中丢失。底物档案的 formula 与 element_counts 使用一致、明确的计数基准。
- 修正上述错误正例，并同时测试完整正例与缺氢反例；不能只改一个断言以维持全绿。
- 未解决的重复参与物／计量歧义不得授予完整账 verified。未知完整性保持 unknown；不得靠自动加水、O2、H+ 或辅酶凑平。
- 输出可机器读取的元素／电荷差值及核算范围。不要求将所有元素 violated 一律 reject，但它必须保持可见，绝不能进入“全部核实”的 R6。

### F02 [P1] 同键条件要求被覆盖或丢失，冲突不能沿路径保持

位置：[path_context.py:381](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:381)、[path_context.py:603](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:603)。

assess_conditions 按 key 保留最后一条要求；derive_child_context 遇到同键不同要求只写文字 assumption，没有保存新要求。636–637 行“保留双方”的注释与代码行为相反。

已复现两种错误：

1. 当前 45°C，父步骤要求 20–30°C，父路径 conflicted；新增步骤要求 40–50°C 后，评估变成 compatible。
2. 当前 25°C，父步骤要求 20–30°C；新增步骤要求 40–50°C，本步 conflict，但派生子上下文又成为 condition_compatible。

交付书 §9.4 所述“同键以假设侧为准”**不接受**。它破坏了规格中累积约束与冲突继承的要求，不能以“合并次序未逐字规定”解释。

回修与验收：保存每步、每阶段的要求和来源；同一固定场景按全部适用要求的合取评估。只有语义相同的要求可去重。记录不同、引用不同或区间不完全相同不一定代表真实冲突；不得将所有同键差异一律判冲突。上面两个已知冲突都必须保持，文字 assumption 不能代替判据。

### F03 [P1] 条件事实忽略缺席、场景、阶段和必要性来源，产生假相容与假冲突

位置：[path_context.py:267](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:267)、[path_context.py:312](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:312)、[path_context.py:325](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:325)、[path_context.py:618](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:618)。

已复现：

- NADH 事实为 known_absent，但值与必需 NADH 匹配，结果 satisfied／compatible。
- essential 条件的 source_refs 为空，仍可证明 compatible。
- 历史实验事实标为 historical-scenario／historical-phase，当前 phase-0 仍使用该事实证明相容。
- essential temperature_C="mesophilic" 与事实 25°C 比较，被判 conflict。

回修与验收：

- 区分“物质身份相同”与“供应存在”；必需物已知缺席为冲突，未列出为未知。
- 显式保存当前 scenario 身份，按场景／阶段／来源适用性选择事实；历史实验只能作为来源场景事实，除非明确采用该场景。
- 场景转换须有可追溯依据及后续事实作用域；保留此前边的评估，不能回溯消除旧冲突。
- 无来源支持的必要性声明只能作为未核实假设，不能证明相容，也不能产生“来源已证必需”的硬门禁。非空 source_ref 本身也不等于来源确实支持该声明。
- 必要范围、观察条件、最适值、定性标签分语义。最适值偏离不推出不可发生；标签缺少可用范围证据时为 unknown。数值与单位需校验有限性和维度。
- compatible 只表示明确评估范围内相容；未评估维度须披露。

### F04 [P1] 严格分子身份与来源记录混在同一不可变 payload，普通连续路径失败

位置：[chemstate.py:154](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:154)、[store.py:121](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:121)、[legacy_reader.py:174](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:174)、[legacy_reader.py:196](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:196)。

state_id 按结构生成，但 put_state 比较包括原始串、origin、source_refs 的整个 payload。同一产物在下一步作为底物，其来源引用必然不同，于是被当成身份冲突。

已复现：同一 CCO、两个 source_refs，第二次 put_state 抛 Ppv1EventConflict；合成两步旧路径在共享中间物处导入失败，新库只留下第一事件。旧库字节未变。

回修与验收：明确“可复用的严格结构身份”与“原始表示／来源／出现位置记录”的关系。相同结构可复用，多次来源都要保留，既不能冲突，也不能用后一来源覆盖前一来源。不能简单忽略 provenance 冲突后丢掉信息；表示保真和可知性须留在可追溯记录中。连续路径、汇合路径和同结构不同原始写法都应验收。

### F05 [P1] 增强立体事实被合并；CN-only 的未知与非法混淆

位置：[chemstate.py:63](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:63)、[chemstate.py:151](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:151)、[audit.py:236](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:236)。

以下三个输入的 RDKit StereoGroups 不同，但当前都得到 cs_bfc4ac69054e81d064fd、specified、full_parse：

- F[C@H](Cl)Br
- F[C@H](Cl)Br |&1:1|
- F[C@H](Cl)Br |o1:1|

这是严格身份的静默碰撞；供体 strict_target_match 也使用普通 MolToSmiles，发生同样丢失。

另有相反方向的错误：有效 CN-only CCO 因无原始 smiles_isomeric，被 audit 判 unparseable_smiles／R1 reject；但通用 build_chemical_state 又允许 origin=legacy_cn_only，返回 original_structure_available=True、formal_charge=0、full_parse。

回修与验收：

- 增强立体纳入可重复的严格身份表示；若首版不支持，则显式阻止其作为已知严格结构进入图，或使用不会碰撞的超范围表示。只把 fidelity 改成 unknown 而继续合并身份不够。
- 通用工厂不得将 CN-only 来源伪装为原始结构可知。合法投影缺原始结构与实际输入语法非法分开，前者保留 unknown／导入只读限制，不能显示成结构化学非法。
- 按来源转换历史声明各轴保真；已知经过中和、立体／同位素信息丢失时不得恢复成已知。
- 中性串没有 +/- 不证明电荷丢失；形式电荷为零可以是合法结构事实。as_written 电荷、原始表示保真和该 pH 下的物种分布须分开。
- 不同互变异构体／质子化态保留不同严格身份是正确方向；不为了去重将其并入 CN 身份。

### F06 [P1] 上下文身份漏语义字段；共底物供给诊断漏环

位置：[path_context.py:568](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:568)、[path_context.py:638](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:638)、[path_context.py:462](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:462)。

根 context_id 未包含 assessment_scope、assumptions、dependency_refs 等；子身份也未包含依赖。已复现：同事实要求、scope=[] 与 scope=['pH'] 身份相同，结论却分别 possible／condition_compatible；追加 depX 与 depY 的子分支身份也相同。

供给循环检测仅保存每个节点一条出边并识别二元环。未解决的 A→B→C→A 返回 cycles=[]、unresolved_initial_supply=[]。将环上反应依赖 supported 也不等于已经证明启动供给。

回修与验收：冻结语义身份字段，把影响科学前提、评估范围和继承依赖的字段纳入身份；不能让 S3 缓存或图节点混用不同前提。供给关系采用结构化多边图，识别任意长度环，分别表示初始供给、再生支持和反应证据。未知启动供给保留 unresolved，不能称化学不可能；下游命中不得自动解决上游依赖。依赖引用存在但状态无法解析时，也不得因调用方没传 unresolved 列表而视为已解决。

### F07 [P1] 事件事务缺少参照完整性，提交与重放成功不代表完整账本

位置：[hypothesis.py:393](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/hypothesis.py:393)、[events.py:151](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/events.py:151)、[store.py:218](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:218)、[store.py:226](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:226)、[events.py:245](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/events.py:245)。

已复现：

- 事件有底物和产物，只提交底物 state，返回 created=True，产物不存在。
- 为某 state_ref 提供另一分子的结构，build_event_states 返回不同 state_id 而不拒绝。
- substrate_state_ref 不属于反应物锚点，假设仍可构造并审计为全核实。
- 删除已提交事件的 report projection 后重放，返回 created=False，缺失记录未被识别。
- 同一产物可以同时 expanded 与 deferred。
- submit_event 用 INSERT OR IGNORE 跳过已存 state 内容核对，与 put_state 的冲突行为不一致。

回修与验收：在提交事务内验证底物锚点、参与物与实际结构身份、引用齐全、已有结构内容相容、事件与假设关联、投影／展开参照及展开状态互斥。若选择假设内嵌而非外键引用，也须保证能重建其完整语义。任一缺项或不一致应失败并回滚；重放遇残缺记录应报告账本损坏或执行明确恢复策略，不能默默成功。以实际提交 API 测试，不只测试上层 helper。

### F08 [P1] 未知 schema 校验不是自动门槛，会先写后验

位置：[store.py:85](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:85)、[store.py:99](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:99)、[run_identity.py:210](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/storage/run_identity.py:210)、[run_identity.py:226](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/storage/run_identity.py:226)。

PollutantPathwayStore 构造先建表、提交，verify_schema 只是可选调用。含 future-store-999 的合成已有库被构造函数修改，put_state 仍成功；手动 verify_schema 才拒绝。顶层 future-identity-999 在其他字段相同时也能通过 resume 身份比较。

回修与验收：读取已有文件时，任何 DDL／写入之前验证 schema；未知版本拒绝且文件字节不变。区分新库初始化与已有库读取。身份读取只接受明确支持的版本，旧 v1 legacy 兼容不得扩展成“任意未知版本按旧版解释”。检查对象 from_dict／载荷读取边界，禁止未知版本静默变成当前默认版本。

### F09 [P1] 旧子路径结构缺失时，根污染物被冒充当前底物

位置：[legacy_reader.py:129](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:129)、[legacy_reader.py:170](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:170)。

找不到子路径来源产物时，导入器无条件退到 root_smiles，并标 is_root=True。合成子底物为 CC=O，删除其存档产物行后，导入底物变成根 CCO，标 raw_input／full_parse／original_structure_available=True，且无未知说明。

回修与验收：只有经路径关系确认的根节点能使用根输入。子节点缺原始档案时保存其 CN-only 与未知状态，或结构化失败；绝不借根结构补子结构。测试真实根、正常子节点、缺档案子节点及不一致引用；旧库必须保持字节不变。

### F10 [P1] 来源类型与独立支持数被升格，导入时模型来源丢失

位置：[provenance.py:149](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/provenance.py:149)、[provenance.py:224](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/provenance.py:224)、[legacy_reader.py:246](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:246)。

已复现：

- 未标识来源的 rule 被标 biotransformation_rule；组合来源的 corpus 成分也被当生物转化规则。
- 同一原始论文的两个数据库 ID，origin_study_known=True 后得到两组、每组 independent_support_count=2，origin_study_ref=None。
- 合成旧模型类比在导入时丢失 model_ref／模型判别信息，被标 analog_transfer／analog_transferred；返回的 provenance 没有随导入作为可解析记录保存。

回修与验收：按明确来源映射保留各成分，未知生物来源保持 unknown；rule_derived 不代表生物来源已知。区分记录去重与原研究独立性，按实际可追溯原研究身份计数，未知时为 null；不要用一个布尔开关代替研究身份。模型提出的类比与库中类比证据分开；新账本须持久保存 provenance，或提供明确、完整的只读原档案引用以重建它。

### F11 [P1] 供体中心诊断没有消费实际编辑协议，并接受不充分／伪造等价关系

位置：[atom_tool.py:76](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/atom_tool.py:76)、[audit.py:711](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:711)、[audit.py:729](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:729)、[audit.py:736](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:736)。

真实 AtomTool 操作使用 atom1／atom2，新诊断却只读虚构的 atom_id。实际乙醇 C–O single→double 编辑已通过 validate／execute 并得到 CC=O，中心诊断却为 None；改为只上报一个中心 atom_id 又变成 True。

另已复现：供体中心缺一部分映射，仍 True；调用方把非等价 C／O 放进 equivalence_classes，仍 True。当前函数基本是在判断“编辑原子是否落入允许原子集合”，没有比较实际键变化、键级及其他结构变化。它不能被称为完整供体变换一致性诊断。

回修与验收：

- 与实际编辑协议对接，依据执行前后结构和可追溯映射核对键变化、原子增删、形式电荷／氢／立体变化；编辑声明与执行结果不一致时不能授予 verified。
- 缺关键中心映射、对齐不充分或多解结论不一致时相应轴 unknown，不能因为部分中心命中就 True。
- 等价关系从实际相关分子／变换的图映射中验证，带 direct／symmetric_equivalent 等依据；不采信调用方自报任意集合。
- 图等价不代表酶识别／机制等价。strict 轴须使用与 ChemicalState 一致的严格表示；CN 仅旁证。
- 同中心原子但不同键操作、额外改变、断键／成键／加原子、对称与破对称结构均应覆盖。

## 3. S3 接口消费前还须明确的 P2 项

1. **admission 理由码不实。** [audit.py:602](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:602)只单列 unknown；非空审计的元素 violated 可落到 empty_audit_no_evidence_to_expand。处置仍可 retain_conditional，但理由必须保留已知矛盾；表示契约失败也应有稳定的专属错误／处置映射，不能冒称结构不可解析或化学不可能。
2. **旧门禁结果到新 admission 缺明确适配。** 旧 validation 的 gates 使用 direction_source／atom_mapping／recorded_eligibility，元素门禁体现在逐产物最终 verdict；新默认名单使用 gate_ 前缀，不能直接透传旧字典。提供版本化 mapper，保留每个共同产物的 accepted／拒因，不把总体 gate_ref 当全量结果。当前旧执行流没有被改判；手工传旧函数名不被消费只证明接口缺口。
3. **搜索上限单位混淆。** [profile.py:67](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/profile.py:67)把每父备选数解释成每个假设的语义尝试次数。父路径上的备选假设数、单假设尝试／重开次数须独立计数，不能相互代替。
4. **配置往返与零夹具。** [profile.py:164](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/profile.py:164)默认输出含字符串 version，校验却把传入 version 当整数预算；version=1 触发 KeyError。须规定覆盖配置与完整序列化配置的输入方式并测试往返。当前 max_search_depth=0、max_total_search_actions=0 被拒绝；S3 前明确如何满足独立零深度／零预算验收，不能笼统写“零模型预算已覆盖所有零边界”。
5. **候选池哈希链未校验。** [pool_audit.py:144](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/pool_audit.py:144)只验证阶段顺序，前阶段输出 a、下一阶段输入 b 也能生成成功审计。相邻已执行阶段应有连续性校验；若阶段跳过或发生显式注入，必须登记转换及原因。排序 limit=-1 也会按 Python 切片静默保留一部分，需校验数值域。

这些项目的“实现／设计澄清”应在 S0–S2 回修书中列清；真正的队列消费、预算预约和崩溃恢复仍留在 S3。不应在这轮顺便实现整个搜索器。

## 4. 对 mimo 意见的裁定

mimo 提出了有价值的方向，但它审核的是规则文字，不能替代代码验收。它没有指出当前氢计数错误、条件覆盖、连续落账失败等已复现缺陷。

| 建议 | 本轮裁定 |
|---|---|
| 严格身份不使用 CN；增强立体不能丢；来源保真分轴 | 接受。增强立体必须解决身份碰撞，只改 unknown 标签不足 |
| 原始电荷未知时账为 unknown；不自动补物 | 接受。依据必须是来源转换历史，而不是字符串看起来是否中性 |
| 元素／电荷差值与 violated／unknown 分码 | 接受。差值模式只表示与某种漏项相符，不能证明实际缺了该物或反应不存在 |
| 未声明完整性子型，默认 complete_stoichiometric | 不接受。未说明就保持完整性／核算适用性 unknown，不把缺少信息升级为完整净反应 |
| 缺 2H 就标 +2e，或缺口“高度疑似惯例” | 需收紧。元素差不能独立证明电子计量或遗漏原因；电子／质子依据必须另外提供 |
| [nH]／N 一般可由芳香感知统一 | 不接受泛化。氢数、芳香性和价态可能是不同化学事实，只归一确属同一分子图的表示差异 |
| 存档串没有电荷标记就认定电荷丢失 | 不接受。合法中性分子本来可以电荷为零 |
| optimum 不产生不可发生的硬冲突 | 接受。但命中最适值只能给偏好信息；来源单点 basis 不明不能自动推为 optimum |
| mesophilic 等注册表标签可直接参与硬判 | 修改。通用类别范围不能替代该反应／酶的来源支持范围；没有适用性证据仍 unknown |
| 首版必须加入光照、盐度、Eh 等所有条件键 | 不作为本轮一刀切门槛。登记未评估维度；遇具体路径已知涉及的条件须显式处理，不能宣称全维度相容 |
| 中心匹配带 basis；不充分／多解不一致为 unknown | 接受；须先对接实际编辑和真实变换 |
| 仅依产物自同构即可证明迁移中心等价 | 修改。应明确当前底物、供体、变换及产物间的映射语义；产物图等价不能证明酶机制等价 |
| 所有七项都只改文字、理由码和展示，不动判据语义 | 不接受。严格身份、条件适用性和中心判定均可改变决策，须修改代码、测试与相应版本说明 |

局部结构差值与完整计量账需要清楚命名和范围，不必实施“永不同时显示”或广泛词语禁令；将它们并列且明确状态、系数假设和适用范围，可以帮助审阅者发现缺项。

## 5. 可重跑的边界证据

脚本均只使用合成结构／合成账本，不读题库或金标。临时文件是审核证据；执行 agent 应把必要反例转成仓库回归测试，不能依赖 /private/tmp 长期存在。

- [化学计量、增强立体、CN-only、供体复现](/private/tmp/ppv1_chemical_contract_repro_7fb198f.py)
- [化学复现完整 JSON](/private/tmp/ppv1_chemical_contract_repro_7fb198f.json)
- [条件、上下文、共底物循环与来源复现](/private/tmp/ppv1_context_provenance_review_repro.py)
- [条件复现完整输出](/private/tmp/ppv1_context_provenance_review_repro.txt)
- [存储、schema、连续旧路径导入复现](/private/tmp/ppv1_design_review_repro.py)
- [配置与候选池边界复现](/private/tmp/PPV1_REVIEW_PROFILE_POOL_PROBES_2026-10-05.py)

运行模板：

~~~bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python /private/tmp/ppv1_chemical_contract_repro_7fb198f.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python /private/tmp/ppv1_context_provenance_review_repro.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python /private/tmp/ppv1_design_review_repro.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python /private/tmp/PPV1_REVIEW_PROFILE_POOL_PROBES_2026-10-05.py
~~~

## 6. 交付书与阶段裁定

| 交付书项目 | 本轮裁定 |
|---|---|
| 新执行 CLI 因 S3 未实施而拒绝，且不建 run | 接受，这是阶段边界 |
| 旧 run 不原地迁移，导入旧库只读 | 接受方向；连续导入与缺存档处理须按 F04／F09 修复 |
| legacy 默认执行及冻结评分／门禁口径不变 | 源码审查未发现本轮主动改判；全量回归结果是提交者提供，不能据此证明新科学语义 |
| code_identity 升级导致升级前 run 跨版本 resume 拒绝 | 可接受为明确代码版本守卫；保留说明，不暗改旧身份绕过检查 |
| 导入默认 report／expansion 是有理由的占位 | 可接受；必须与真实决策区分，不把 not_tracked 当化学终点 |
| §9.4 同键新要求覆盖旧要求 | 不接受，按 F02 回修 |
| §2 “schema 未知失败、独立支持数诚实、契约完成”等 | 当前证据不足或被反例推翻，更新状态为待回修 |
| §11 接口／上限直接冻结供 S3 消费 | 暂缓；以本轮修复后的契约和版本清单重新提交 |
| 科学验收 pending | 接受；工程测试不得包装成路径预测准确率 |

再次交付至少应提供：逐项 F01–F11／P2 处置表、修改提交、影响契约及版本清单、有效正反例、旧默认模式回归证据、mimo 采纳／纠偏表、剩余未知。身份、存储或化学判定语义有变化时明确版本与兼容行为，旧 run 不静默迁移。新增化学判据重新走既有化学复核流程，未经复核不称冻结。

只有底座反例修复、阶段契约再次通过 review，才进入 S3 的有界搜索和任务身份／恢复。S3／S4／S5 本轮仍未验收。

## 7. 可直接交给执行 agent 的回修提示词

~~~text
请对 pollutant_pathway_v1 做 S0–S2 回修，暂不进入 S3–S5。先读取以下四份文件：

1. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md
2. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_DELIVERY_2026-10-05.md
3. /Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response.md
4. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_2026-10-05.md

第 4 份是当前提交 7fb198f 的源码复核和边界复现结果。逐项修复 F01–F11，并落实 §3 的 P2 设计／接口事项；不要以现有 88 个测试全绿作为通过依据。首先修正错误的氢计数正例，并把审核中的必要反例转成仓库回归测试。

保持 legacy_v43 默认行为、CN 评分身份、冻结门禁真假与既有输出口径；未知、冲突、表示契约失败分别保存，元素 violated 的保留策略不能变成“全部核实”。不读取 gold 或封存逐题材料、不运行真实模型或付费实验、不原地迁移旧 run。

分子严格身份与来源／出现记录需要同时保真；条件要求必须按步骤和阶段累积，不许覆盖；历史条件不得成为当前事实；供体诊断须消费真实 AtomTool 编辑和执行结果；事件提交／恢复必须检查完整引用和附随记录；未知 schema 在写前拒绝。

不要整段照搬 mimo 回应，按第 4 份文件 §4 的采纳与纠偏执行。影响身份、存储或判定语义的修改要列明版本及兼容行为，更新化学判据评审请求。若具体回修与原规格出现实质冲突，列明冲突和处理依据，不能默默改冻结标准。

完成后提交新的 S0–S2 回修交付书，附逐项处置表、提交号、版本清单、规则级正反例与 legacy 回归结果、mimo 处置表和剩余未知，交回本会话 review。未经复核，不解除新执行入口的 S3 边界，也不宣称契约或化学判据已冻结。
~~~

