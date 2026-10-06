# mimo 化学评审请求:pollutant_pathway_v1 化学判据(S0–S2 回修版 v5)

- 日期:2026-10-07(R5 回修版;替换 2026-10-06 v4 请求)
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或发布前)
- 评审对象:S0–S2 第五轮回修后的化学判据草案 v5(实现于
  `src/pathway_v43/pollutant/`,ppv1-*-5 版本族);**尚未冻结**
- 与 v4 的差异来源:第四轮 mimo 回应
  (`docs/mimo_ppv1_chem_review_response_r4.md`)+ Codex R4 复审
  (`POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R4_2026-10-07.md` R4-01～11
  与 §5 采纳边界)。Codex 已互证并采纳的 v4 缺陷:证明链可自造
  (R4-01)、finite_rule_diagnostic 漏 hash(R4-02)、单位未知仍
  satisfied(R4-03)、快照按阶段存在即覆盖(R4-04)、反驳不撤销
  支持轴(R4-05)、镜像漏活 ID/前置(R4-06)、键立体与非四面体
  静默缺席(R4-07)、DATA SGroup 仍分裂身份(R4-08)等 11 项。
- 自包含性:规则级表述与合成规则级夹具,无任何金标/题面/封存
  逐题数据;由用户转交,回复原文落盘 `docs/`

## 0. 背景(一段话)

v4 判据经第四轮代码复审发现底座缺陷(证据可自造到 R6、载荷可变
不改身份、快照空掩盖孤儿要求、镜像不守执行器前置、键立体/非四面体
轴静默缺席等),已全部回修并有行为级红绿回归(基线 e80f459 新增
回归 58/69 红;G01 全量 992 passed/0 failed)。本轮请评审**回修后
的判据文本 v5**。目标不变:可能降解路径与条件相容路径的诚实表示;
unknown 不升格;verified 不靠模型或调用方自报字符串。

## 1. 判据一:分子身份(v5 文本)

1. state_id 仅对 sanitize 成功、芳香性已感知的分子生成;失败归
   R1(仅实际语法/价态非法)。
2. 身份键 = **化学 CX 事实子集**的规范化 canonical CXSMILES,
   按三类**逐类登记表**处理(R4 复审/mimo R4 1.1 的拒绝表口径):
   - **移除类**:坐标(conformer)、原子标签(atomLabel)、任意
     atomProp(含 $_AV/molLnkNode,实测以属性承载,R4 复审核对)、
     原子映射号、**DATA SGroup(SgD)**——纯出现/注记元数据(如
     review_note;实测裸 CO 与两种 DATA 注记曾分裂三个 id;
     值可含逗号 ⇒ 分子级按 SubstanceGroup 类型剥离,不做字符串级
     令牌解析);
   - **保留类**:增强立体组(a/oN/&N)、自由基层(^N)、基串内
     同位素/电荷/立体、**SRU/聚合物等非 DAT SGroup(Sg:)**
     (承载化学事实,不盲目剥掉;实测与裸骨架不同 id、往返重建
     同 id);
   - **未登记类 ⇒ 显式拒绝该表示**(unregistered_cx_class,如
     w:/LN:/atomProp/旗标块 r;ChemicalStateError,不默认进身份
     也不默认剥掉)。bond prop 实测不被 MolToCXSmiles 外写
     (登记测试钉住);
   - **混合并列 ABS 令牌级归一**:`a:1,&1:3` ≡ `|&1:3|`、
     `a:1,o1:3` ≡ `|o1:3|`、`^1:0,a:1` ≡ `|^1:0|`;**ABS 原子
     同时是组成员**的矛盾输入按"组成员资格覆盖 ABS 声明"解析
     (登记规则;与 RDKit 保留两个组的表示层差异为已登记分歧);
   - **立体语义(RDKit Book)**:AND=两组分混合物;OR=未知何者的
     单一未定;ABS=单一确定;整组翻转不变、部分翻转为不同键;
     不同组类型不合并;排列/kekulé 归一;
   - 与 RDKit RegistrationHash 的一致性限定在整组翻转/部分反转/
     排列/kekulé/映射号子集;plain≡|a:…| 同键与混合并列 ABS 剥离
     均为本仓归一设计(与 RegistrationHash 的 CANONICAL_SMILES 层
     及 RDKit 立体组集合存在**已登记分歧**,mimo R4 边界 1)。
3. **公开表示往返闭合**:smiles_isomeric = 身份键同一串。无组、
   无自由基层、**无 SGroup、无原子映射号**的分子输出与普通
   canonical isomeric SMILES 逐字相同(mimo R4 1.3 的映射号例外
   已补:映射号被剥离,只存在于 raw 与编辑 ID 通道);自由基带
   |^n:…| 后缀(radical 保真轴已登记缺口)。
4. representation_fidelity 分轴;任一轴 ≠ as_written ⇒
   identity_fidelity 检查 unknown 并列轴。

**请评审**:(a) 逐类登记表(移除/保留/未登记拒绝)的划分,
尤其 **SgD 全类剥离**与 **Sg 全类保留**两条边界;(b) 未登记类
拒绝的默认行为;(c) 往返句的映射号例外;(d) "组覆盖 ABS"的
矛盾输入解析规则。

## 2. 判据二:参与物计量与元素/电荷核算(v5 文本)

1–8 同 v4(全氢账/系数契约/完整性 unknown/电荷轴前提/结构化
omission_pattern_matches/H+_count1 命名;R5d 触发集合限定
{元素,电荷};恒等≠落点口径句;local_delta pending 排除声明)。
v5 无变化。

**请评审**:确认 v4 已同意条款不需重评;仅复核恒等≠落点句与
落点指路(判据五 center_property_deltas + 身份轴)的分工。

## 3. 判据三:admission 决策表(v5 文本;有序,首中即决)

R1/R1b/R2/R2p(on/off 披露)/R2b/R3/R4/R5d{元素,电荷}/R5v/
R5c/R5/R6/R7。行语义同 v4,v5 重写中心证据契约:

- **中心证据契约(R4-01,证明链内部重算)**:证据 =
  {checker_version ∈ 注册表, checker_scope ∈ 已声明范围(现仅
  region_net_change;full_template 预留 S3),center_match,
  declaration_mismatch,strict_target_match,bound_inputs 六项,
  **proof_record**=诊断完整输入集(current/donor/alignment/
  expectation/result/edits)}。audit 的证据门:
  1) **类型契约**:center_match/strict_target_match 须 bool|None,
     declaration_mismatch 须 bool,bound_inputs 六项分型 —— 违约
     ⇒ **结构化拒绝**(AuditContractError,kind=center_evidence_
     type_violation;字符串'false'/整数 0/空容器不得绕过
     is False/is None);表示违约是契约问题,不是化学"未知就拒绝";
  2) **内部重算**:audit 复跑 check_edit_against_donor(证明
     记录的完整输入)⇒ 自报轴/绑定字段须与复算值一致;不一致 ⇒
     **结构化拒绝**(center_evidence_integrity_mismatch —— 改
     真实诊断的任一绑定字段不得仅换 input_hash 后照常 verified);
  3) **无 proof_record ⇒ unknown**(center_evidence_proof_
     missing):两条身份字符串或六条自报字段不构成 checker 曾对
     本次输入执行的证明;不增加可自报字段、不收窄文字;
  4) **绑定核验(复算值)**:底物身份==primary substrate;产物
     按**集合覆盖**——整分子或碎片两级映射(执行图产物多碎片时
     逐碎片对产物参与物比对;真实断裂的分列产物正确绑定,不要求
     把碎片拼成一个物种);碎片映射到无参与物 ⇒ 未申报碎片 ⇒
     unknown;**未覆盖产物与未覆盖共底物同时存在 ⇒ 部分覆盖 ⇒
     unknown**(额外未核实转化不得借一个产物达到 all_verified);
     仅未覆盖产物(底物脱除原子的计量共产物)或仅未覆盖共底物
     (原子并入已覆盖产物)⇒ 完全覆盖;
  5) strict 轴消费同 v4(False ⇒ violated R5v;None ⇒ unknown
     阻断 all_verified;区域 True 与 strict False 分列);
- **input_hash 覆盖实际科学输入**(R4-02 补齐):v4 域 +
  **finite_rule_diagnostic(实际审核入参;默认 not_run 合法 NA
  与 diagnostic_only 的 unknown 是不同输入状态,不同 hash)** +
  proof_record/bound_inputs 的 content_hash;
- **audit.scope 不遮蔽**(§4):证据门局部 checker scope 不再
  覆盖函数 scope 参数,调用方范围(如 'synthetic:review-scope')
  如实返回;checker_scope 与"transformation_center: verified"
  同屏(理由码带 scope=region_net_change,不截断);
- 审计消费(候选级评估/依赖并集)同 v4。

**请评审**:(a) 证明链的内部重算口径(自报字段须与复算一致;
无记录即 unknown;类型违约结构化拒绝);(b) 产物集合覆盖的整
分子/碎片两级映射与"部分覆盖 ⇒ retain"语义;(c) **信任边界
声明**:证明记录是自包含输入集,自洽构造的记录复跑即通过(证明
链保证"该输入集上 checker 结论可复现",不证明"有人真实运行过
该编辑"——运行事实由执行器通道承担,S3 完整模板另议)。

## 4. 判据四:条件相容聚合(v5 文本)

1–4、7 同 v4(封闭 7 键/区间×点三态/实体身份/matrix unknown)。
v5 改三条:

5. **live 作用域与快照覆盖(R4-04)**:live 判定含 **scenario+phase
   二元组** —— 同阶段名不同场景的旧要求不被当前场景事实重评
   (旧边结论由 phase_history 快照承载;接口允许只转 scenario,
   不强迫改阶段名规避);快照冻结时记录
   **covered_requirement_signatures**(该次评估实际覆盖的要求
   集合)——覆盖核对**具体要求签名**,不是"阶段存在即覆盖";
   空快照不能掩盖孤儿必要要求(孤儿 ⇒ 显式 unknown);
6. **单位契约(R4-03,替换 v4 案)**:要求值恒为键规范单位;
   **必须显式单位的键(temperature_C)空单位事实 = 原来源单位
   未知 ⇒ 评估 unknown(unit_basis: source_unit_unknown),不按
   数值直比,不以 assumed_canonical 注记升级 satisfied/conflict**
   (v4 的 assumed_canonical+satisfied 是 Codex R4 点名缺陷);
   显式规范单位 ⇒ canonical+正常比较;显式错误单位(如 K)⇒
   unit_mismatch ⇒ unknown;pH 等无量纲键空单位合法;oxygen/
   matrix/物种键不受影响,不一概判未知;首版仍不支持单位换算;
8. **依赖支持按轴当前有效状态(R4-05,替换 v4 轴集合累积)**:
   每轴取其**最近一次**解决结论(contradicted **撤销该轴**此前
   的 supported;resolution_log 是唯一事实源);总体 status:
   任一轴当前 contradicted ⇒ contradicted,否则任一轴 supported
   ⇒ supported;**后续再生支持不重新证明已反驳的初始供给;
   恢复某轴须该轴新证据**;support_axes = 当前有效支持轴(不再
   "曾经支持永久保留");正控制 initial+regeneration 双支持不回退。
   9 同 v4(hypothesis_id 纳入前提;嵌套载荷冻结 + v5:requirement
   dict 顶层冻结映射、嵌套 value 递归冻结,|= /update/setitem 就地
   修改立即 TypeError)。

**请评审**:(a) scenario+phase live 作用域;(b) 快照签名覆盖
(具体要求,非阶段存在);(c) 单位未知 ⇒ unknown 的入口契约;
(d) 分轴撤销语义(反驳撤销该轴/恢复须该轴证据)。

## 5. 判据五:供体一致性诊断(v5 文本)

命名 = 实际净变化区域诊断,checker scope = region_net_change
(不冒充完整变换一致;完整模板预留 S3):

1. 判定基础 = 实际净变化集合(键 diff∪原子增删∪逐原子(形式
   电荷/ΔH/**构型**)diff ∪ **键级立体(cis/trans)diff**);
   声明原子单列 declaration_only;
2. **构型比较 = 映射配体下的奇偶法**(同 v4;CIP 标签仅披露);
   **非四面体手性标签(平面/四方/八面/三角双锥)⇒ 该原子立体轴
   unsupported(None)**——判据是**标签类型**,不是"是否四面体
   指定成功";两侧同为非四面体或一侧非四面体一侧 UNSPECIFIED
   均不得返回"构型保持"(mimo R4 5.2(a) 条件 1,v5 落实);
   unsupported 原子**公开列项**(stereo_comparison_unsupported_
   atoms;中心内的进 center_property_deltas,mimo R4 条件 2);
   **中心外存在 unsupported 立体轴 ⇒ center 不可判 True**(区域
   约束对该轴不可核);
3. **联合映射保手性**(v5 支持范围扩为三类,mimo R4 probe3):
   ①绝对四面体全指定;②无手性骨架;③部分指定/全未指定——按
   所写表示参与保手性匹配(指定↔未指定互换被拒,全未指定两端
   产物同一身份时可判 True);**增强立体组或非四面体手性标签
   ⇒ unsupported ⇒ unknown**(useChirality 只覆盖四面体标签,
   非四面体被其忽略会把可区分位点判等价);截断 ⇒ unknown;
4. **声明–执行净效应对账(v5,R4-06)**:镜像执行器路径模拟——
   **活 ID 表**(先增后引合法,与执行器一致:先前 add_atom 声明
   的新 ID 立即可被后续操作引用,含 anchor 引用新原子、
   change_bond_order 作用于新键)+ **逐操作前置复核**(键存在/
   不存在、**from_order == 列表时点实际键级**——错误 from_order
   被冻结执行器拒绝,镜像同样拒,机读码 declared_precondition_
   violated:bond_order_mismatch;失败结构化,不笼统
   not_simulable)+ 净效应比较(中间态不逐条相等)+ add_atom
   隐含 anchor 单键 + 终态 sanitize。原子属性与键级立体都**不在
   ops 对账范围**(声明语言两者皆无操作);**键级立体入实际
   变化集与声明对账签名**(映射原子对前后 GetStereo 不同 ⇒
   bond_stereo_change;执行图带未声明立体变化即为失配,接口合成
   不得冒称执行器结果);**身份键不同而图轴全空 ⇒ 理由码
   net_change_only_in_stereo_representation**(非四面体/未比较
   立体轴的差异不经图变化集承载),**不得称"实际净变化为空"**
   (mimo R4 5.2(c) 条件 4);
5. **中心原子属性披露**:center_property_deltas(电荷/ΔH/构型/
   准确 CIP + **stereo_comparison_unsupported 标志**,同通道公开
   不静默缺席);cip_labels 与空 delta 并排时载荷带
   cip_label_change_is_not_config_change 提示(标签 diff ≠ 构型
   变化,配体优先级重排;**建议项,mimo R4 5.3(5)**);
6. strict 轴与 ChemicalState 同源规范化;执行失败 ⇒ 全轴
   unknown;legacy_cn_match 仅旁证;
7. **证据载荷内嵌**:诊断携带 center_evidence(bound_inputs +
   各轴结论 + scope + **proof_record 完整输入集**),供判据三
   证据门内部重算消费。

**请评审**:(a) 非四面体 unsupported 的判据(标签类型)与公开
列项;(b) 联合映射三类支持范围;(c) 镜像活 ID 表与 from_order
前置;(d) 键级立体入变化集/声明对账签名;(e) "身份不同而图轴
空"的理由码;(f) center 外 unsupported 阻断 True。

## 6. 程序证据与状态

- 规则级测试:381 passed/0 skip(312 v4 存量 + 69 新增 R5 回归;
  全部合成夹具;新增回归在基线 e80f459 红 58/69,11 个为正控制
  ——正控制基线亦绿);G01 全量 not slow **992 passed/16
  deselected/0 failed**(611 legacy + 381 ppv1;legacy 零改动);
- R4 复审探针在 v5 复跑(临时目录,证据
  `docs/review_evidence/ppv1_r5_impl_2026-10-07/`):admission
  探针的篡改用例结构化拒绝退出(修复行为);化学/条件/存储探针
  关键反例逐项翻转,旧控制保持;
- 判据未冻结;mimo R4 的 9 条冻结前处置清单处置情况见 R5 交付
  书 §4(第 1/2/4/5/6/7/8/9 条已按程序证据落实;第 3 条为文本级
  已并入判据一);
- 参考(外部常识,非本仓资产):RDKit Book(CXSMILES 扩展/增强
  立体/立体化学章节/非四面体立体支持说明)、rdCIPLabeler API。

## 7. 请求的回复格式

对每条判据:1) 结论(同意/不同意/有条件同意+条件);2) 可直接
落进规则文字的修改建议;3) "程序上诚实但化学上误导"风险点。
逐条表态,不接受总体评价式回复。
