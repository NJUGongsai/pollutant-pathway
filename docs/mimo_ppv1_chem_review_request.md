# mimo 化学评审请求:pollutant_pathway_v1 首批化学判据(S0–S2 回修版 v2)

- 日期:2026-10-05(回修版;替换同日 v1 请求)
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或发布前)
- 评审对象:S0–S2 回修后的化学判据草案 v2(实现于
  `src/pathway_v43/pollutant/`,ppv1-*-2 版本族);**尚未冻结**
- 与 v1 的差异来源:第一轮 mimo 回应
  (`docs/mimo_ppv1_chem_review_response.md`)已逐条处置;Codex 源码
  复核(`docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_2026-10-05.md` §4)
  对 mimo 意见做了采纳/纠偏裁定,本请求按该裁定修订判据文本
  (不整段照搬 mimo 原文)
- 自包含性:规则级表述与人工构造的规则级夹具,无任何金标/题面/
  封存逐题数据;由用户转交,回复原文落盘 `docs/`

## 0. 背景(一段话)

v1 判据经代码复核发现实现层缺陷(氢计数漏算、条件覆盖丢失、身份
碰撞等),已全部回修;同时 mimo 第一轮意见按 Codex 裁定吸收。本轮
请评审**回修后的判据文本**。目标不变:可能降解路径与条件相容路径
的诚实表示,不是实际主导路线预测。

## 1. 判据一:分子身份(v2 文本)

1. state_id 仅对 sanitize 成功、芳香性已感知的分子生成(canonical
   在感知后输出,Kekulé 写法差异不入键);sanitize 失败不生成
   state_id(归 admission R1)。
2. 身份键 = canonical 重排后的 isomeric SMILES **+ 增强立体组
   (StereoGroups AND/OR/ABS)显式序列化**;普通/AND/OR/ABS 四种
   立体事实得到四个不同身份(不再静默合并)。原子映射号不属于身份。
3. representation_fidelity **分轴**:stereo / isotope /
   formal_charge / protonation_basis,每轴 ∈ {as_written,
   absent_in_archive, unknown, neutralized_by_cn}:
   - CN-only:四轴 = unknown/unknown/unknown/neutralized_by_cn;
   - 存档形:stereo/isotope=absent_in_archive;formal_charge=
     **as_written**(Codex 纠偏:中性串电荷为零是合法结构事实,
     不从中性猜"电荷丢失";电荷是否曾丢失按**来源转换历史**判定,
     不看字符串长相)。
4. 互变异构体/质子化态/对映体保留**不同**严格身份;派生等价类
   (互变组/中性母体)只用于展示提示,永不并入身份;展开去重键 =
   state_id,**禁止 CN 去重**;仅质子化/互变差异的边标
   edge_kind(S3 落地),不以降解转化面目出现。
5. CN 只出现在评分/资产键,出现处标 basis=scoring_key。

**请评审**:(a) 增强立体序列化的键设计是否还有碰撞/分裂风险;
(b) 分轴 fidelity 的 archive 电荷轴 as_written 立场(Codex 纠偏
后)是否成立;(c) 合法投影缺结构(CN-only)与语法非法在
admission 分开处理(R1 只收语法非法)是否正确。

## 2. 判据二:参与物计量与元素/电荷核算(v2 文本)

1. 系数正有限有理数;零/负/非有限拒绝(reject 落 R2b,见判据三)。
2. 元素账**计入全部氢**:重原子隐式+显式属性氢(GetTotalNumHs)
   与独立氢顶点都入账;底物档案 formula/element_counts 同一基准。
   (v1 只数图顶点导致 CCO→CC=O 假 verified,已修复并有正反例。)
3. 完整声明(列表 complete 且全系数 known 且无歧义重复)才核全账;
   否则 full_balance=unknown。**未声明完整性子型不默认
   complete_stoichiometric**(Codex 裁定:未说明就保持完整性
   unknown,不把缺信息升级为完整净反应)。
4. 电荷账前提:参与物 formal_charge 轴 == as_written 才可算;
   CN/中和形输入 ⇒ unknown(不得拿中和后电荷算出假通过)。
   不先中和再验;不自动补水/氧/辅酶。
5. 账不平 ⇒ violated,输出**逐元素 Δ 向量**与电荷缺口;与常见
   漏项模式(H2O/H+/O2/2H)的**数值相符**单独标注
   (omission_pattern_matches,含方向 reactant_side/product_side),
   语义声明:仅数值相符,**不证明实际缺该物质、不推断遗漏原因、
   不含电子/质子计量**(Codex 收紧:缺 2H 不标 +2e)。
6. violated ⇒ retain_conditional(独立理由码
   declared_account_violated),不 reject(账不平只证明声明内部
   矛盾);绝不进入"全部核实"。
7. 局部结构差 = 具名反应物与产物之间的逐分子差;系数未知/非 1:1
   时只报方向,不作定量解释;与 full_balance 并列时各自带状态、
   系数假设与适用范围标注(便于审阅发现缺项,不实施"永不同屏"
   或词语禁令,Codex 裁定)。

**请评审**:(a) 全氢计数的口径;(b) 模式标注的"仅数值相符"
语义边界;(c) violated→retain_conditional(不 reject)的立场。

## 3. 判据三:admission 决策表(v2 文本;有序,首中即决)

| 规则 | 条件 | 处置 | 理由码 |
|---|---|---|---|
| R1 | 实际输入语法非法(parse violated) | reject | structure_unparseable |
| R2 | 活动门禁显式拒绝(经评审名单;旧门禁经版本化 mapper 接入,逐产物 verdict 保留) | reject | active_gate_rejected |
| R2b | 表示契约违反(零/负/非有限系数;酶计入净计量;结构性违约) | reject | contract_violated_representation(非化学) |
| R3 | 有来源 essential 条件与当前场景已知事实冲突 | defer(blocked) | current_scenario_conflict |
| R4 | 预算/等待 | defer | budget_or_wait |
| R5d | 元素/电荷账 violated(声明与结构不一致,有证据) | retain_conditional | declared_account_violated(与 unknown 分码) |
| R5 | 条件/完整账/映射/step_scope 未知 | retain_conditional | unknown_checks_present |
| R6 | 全部核实且无冲突 | expand | all_verified |
| R7 | 无适用检查 | retain_conditional | 保守,不冒充核实 |

R3 的 essential 判据:仅来源明示必需(封闭短语集;一切观察性表述
与来源培养/实验设置不进门禁);无来源 essential = 未核实假设
(necessity_unsourced):不产生冲突、不能证明相容。已知覆盖率
特性:文献极少用 essential 字面,R3 触发率预期偏低属已知特性,
不得读成"条件冲突罕见"。

**请评审**:(a) R2b 的落点与措辞;(b) R5d 与 R5 分码;
(c) R7 空审计的保守保留。

## 4. 判据四:条件相容聚合(v2 文本)

1. 条件键首版封闭 7 键;oxygen_regime/pH/temperature_C/matrix/
   electron_donor/electron_acceptor/growth_substrate。
2. 已登记 v2 缺口键 {biotic_abiotic, light_regime,
   salinity_ionic_strength, redox_regime_eh,
   required_trace_elements_cofactors, substrate_concentration,
   inoculum_source, phase_bioavailability}:相容结论**必须**附
   unassessed_dimensions,只显示"已评估维度内相容"(遇具体路径
   已知涉及的条件须显式处理,不宣称全维度相容)。
3. 值语义分 basis:range(显式区间)/point(声明必需点)/optimum
   (最适值:永不产生 conflict,偏离只作 preference;**来源单点
   basis 不明不自动推为 optimum**,按 unknown 处理 —— Codex 纠偏)/
   label(定性标签:须经注册表映射;首版注册表为空 ⇒ 一律
   unknown,禁止现推区间;且通用类别范围不能替代该反应/酶的来源
   支持范围)。
4. 事实适用性:curated_source 事实仅当 subject_scenario_ref 匹配
   当前场景才适用;phase_id 非空的事实只在对应阶段适用;必需物
   known_absent ⇒ conflict(未列出 ⇒ unknown ≠ absent);同键多条
   适用事实互不一致 ⇒ unknown。
5. 聚合:全部适用必要要求**合取**(同键多条要求不覆盖:父子要求
   并存,各与事实评估);任一冲突 → conflict;否则任一 unknown
   (含无源必要性/值语义未声明/标签无映射/要求空)→ unknown;
   全部 satisfied 且声明覆盖完整 → compatible(未评估维度另列)。
6. 观察条件不进门禁;preference 只提示;assessed_scope 派生不
   继承请求;"土壤/污水"不推氧。

**请评审**:(a) 未评估维度的显式化是否足以防偏乐观读数;
(b) optimum/label/basis 不明的三态处理;(c) 合取聚合。

## 5. 判据五:供体一致性诊断(v2 文本)

诊断**消费真实 AtomTool 编辑协议**(v43-editproto-2:
op/atom1/atom2/from_order/to_order;execute_edits 的
product_mapped_smiles + atom_id_map):

1. 实际键变化集合 = 执行前后结构的键 diff(成键/断键/键级变化,
   原子增删另列)——不是"编辑原子是否落入允许集合";
2. strict_target_match:与 ChemicalState 同源的严格身份(含增强
   立体)比对;
3. reaction_center_match:供体中心(经对齐映射)与**实际键变化**
   比对;全部中心原子须有映射(部分缺 ⇒ unknown,不部分 True);
   命中带 center_match_basis ∈ {direct, symmetric_equivalent};
4. **等价关系从分子图自同构验证**(canonical rank 对称类),
   调用方自报的非等价类被整体拒用(不部分采信);
5. symmetric_equivalent 不升格为"机制已证"(图等价 ≠ 酶识别等价,
   前手性面/对映面专一无法由图等价给出);
6. legacy_cn_match 仅旁证(corroborating),任何汇总/计数/门禁
   不得以 CN 计"一致数";
7. extra_changes 附逐原子 Δ 摘要(元素语言可读);
8. 编辑声明与执行结果不一致时不授予 verified;执行失败 ⇒ 全轴
   unknown(execution_failed)。

**请评审**:(a) 键变化集合作为 center 判定基础是否充分;
(b) 等价类图自同构验证的口径;(c) 部分中心缺映射 ⇒ unknown。

## 6. 程序证据与状态

- 回修后的规则级测试:129 passed / 1 显式 skip(合成分子夹具;
  含 v1 错误正例的修正与全部复核反例的仓库化回归);
- 判据未冻结;上一轮 mimo 意见的处置表见回修交付书;
- 元素/电荷账是新增分项;G2(v43-cons-2)仅旧规则诊断,
  unclassified=覆盖未知,语义未动;
- 参考(外部常识,非本仓资产):IUBMB EC 6.4.1.8 说明新增碳/辅
  底物反应不能被元素白名单否定为普遍不可能 —— 本仓未因此改旧门禁。

## 7. 请求的回复格式

对每条判据:1) 结论(同意/不同意/有条件同意+条件);2) 可直接
落进规则文字的修改建议;3) "程序上诚实但化学上误导"风险点。
逐条表态,不接受总体评价式回复。
