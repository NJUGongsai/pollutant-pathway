# mimo 化学评审请求:pollutant_pathway_v1 化学判据(S0–S2 回修版 v4)

- 日期:2026-10-06(R4 回修版;替换同日 v3 请求)
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或发布前)
- 评审对象:S0–S2 第四轮回修后的化学判据草案 v4(实现于
  `src/pathway_v43/pollutant/`,ppv1-*-4 版本族);**尚未冻结**
- 与 v3 的差异来源:第三轮 mimo 回应
  (`docs/mimo_ppv1_chem_review_response_r3.md`)+ Codex R3 复审
  (`POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R3_2026-10-06.md` R3-01～12
  与 §5 采纳边界)。mimo R3 的全部条件已按 Codex 裁定处置;两条修法
  被修正采纳:①"换 rdCIPLabeler 即可"——新真实反例证明准确 R/S 标签
  也会配体优先级翻转,构型判定改用**映射配体奇偶法**,准确标签仅
  披露;②"单开 useChirality 即可宣称解决"——手性感知映射**声明
  支持范围**(绝对四面体;增强立体组 unsupported)。
- 自包含性:规则级表述与合成规则级夹具,无任何金标/题面/封存
  逐题数据;由用户转交,回复原文落盘 `docs/`

## 0. 背景(一段话)

v3 判据经第三轮代码复审发现底座缺陷(证据不绑定本反应、手性盲
联合映射、CIP 标签误当构型变化、CX 身份混入绘图注释、声明对账
未守执行器协议、路线快照未消费、writer 不重推导、重放只查存在
等),已全部回修并有行为级红绿回归(基线 8/8 红)。本轮请评审
**回修后的判据文本 v4**。目标不变:可能降解路径与条件相容路径的
诚实表示;unknown 不升格;verified 不靠模型或调用方自报字符串。

## 1. 判据一:分子身份(v4 文本)

1. state_id 仅对 sanitize 成功、芳香性已感知的分子生成;失败归
   R1(仅实际语法/价态非法)。
2. 身份键 = **化学 CX 事实子集**的规范化 canonical CXSMILES:
   - **移除非化学 CX 元数据**:坐标(conformer)、原子标签
     (atomLabel)、任意 atomProp —— 绘图/注释不改严格分子图身份
     (普通 CO 与带标签/坐标/注记的 CO 同键);
   - **保留化学事实**:增强立体组、自由基层(^n:idx)、基串内的
     同位素/电荷/立体;
   - **混合并列 ABS 令牌级归一**:`a:1,&1:3` ≡ `|&1:3|`、
     `a:1,o1:3` ≡ `|o1:3|`、`^1:0,a:1` ≡ `|^1:0|`(注解头 token
     与其后的原子列表延续 token 一并剥除;逗号既分隔注解也分隔
     组内原子,不做逗号盲拆、不剥全部 CX);
   - **立体语义(RDKit Book)**:AND=两组分(该手性分子及其镜像)
     都在的**混合物**声明;OR=二者**未知何者**的单一未定物质声明;
     ABS=单一确定构型声明;AND/OR 对组内全中心**整组翻转**不变
     (镜像化的混合物/未知集与原声明同义),**部分翻转**(组内只翻
     一个中心)为不同键;不同组类型不合并;原子排列/kekulé 归一;
   - 与 RDKit RegistrationHash 的一致性**限定**在整组翻转/部分
     反转/排列/kekulé/映射号子集;plain≡|a:…| 同键是本仓归一设计,
     与 RegistrationHash 的 CANONICAL_SMILES 层存在**已登记分歧**。
3. **公开表示往返闭合**:smiles_isomeric = 身份键同一串(带组
   注解,重解析重建同 id)。无组**且无自由基层**的分子输出与
   普通 canonical isomeric SMILES 逐字相同;**自由基分子带
   |^n:…| 后缀是例外**(radical 保真轴为已登记缺口,身份层区分
   自由基)。
4. representation_fidelity 分轴;任一轴 ≠ as_written ⇒
   identity_fidelity 检查 unknown 并列轴。

**请评审**:(a) CX 事实子集的划分(保留/移除清单);(b) 令牌级
ABS 归一的语法口径;(c) AND/OR 语义句与整组翻转不变性。

## 2. 判据二:参与物计量与元素/电荷核算(v4 文本)

1–6 同 v3(全氢账/系数契约/完整性 unknown/电荷轴前提/结构化
omission_pattern_matches{pattern,excess_on,missing_from,
element_delta}/H+_count1 命名;R5d 触发集合限定{元素,电荷})。
7. 电荷账口径钉死(mimo 2.3(1) 采纳):电荷账是**全账恒等**的
   数值闭合,**不核对电荷落点与声明是否一致**;落点/归属的一致性
   归判据五的声明–执行对账与身份轴。
8. 局部结构差 local_delta = contract clause, implementation
   pending(S3/展示层定案后入册)。

**请评审**:(a) 恒等≠落点的口径句;(b) pending 条款的排除声明。

## 3. 判据三:admission 决策表(v4 文本;有序,首中即决)

R1/R1b/R2/**R2p**(on:全拒 reject/部分拒 retain;**off 只关消费
不关披露**——决策可为 expand 但被拒产物以 R2p_disclosure 留痕)/
R2b(构造期一切契约违反——含 requirements 非 dict/缺必填/level
枚举外/外来绑定——一律 HypothesisContractError(detail),无裸
TypeError)/R3/R4/R5d{元素,电荷}/R5v(其他 violated)/
R5c(必需覆盖缺口)/R5/R6/R7。行语义同 v3,新增与收紧:

- **中心证据契约(R3-01)**:证据 = {checker_version ∈ 注册表,
  checker_scope ∈ 已声明范围(现仅 region_net_change;完整模板
  full_template 预留 S3 独立注册),center_match,declaration_
  mismatch,**strict_target_match**,**bound_inputs**(底物身份/
  产物身份/edits 签名/执行指纹/供体中心/对齐引用)}。audit
  **绑定核验**:底物身份==被审假设 primary substrate 的公开表示;
  产物身份==某产物参与物——跨反应复用/改产物/映射编辑/无依据
  True ⇒ unknown,不得认证。**strict 轴消费**:False ⇒
  violated(R5v);None ⇒ unknown(阻断 all_verified);区域 True
  与 strict False 在 detail 分列,不互相覆盖;
- **input_hash 覆盖实际科学输入**(R3-08):hypothesis 载荷+
  参与物 state 完整内容(fidelity/appearance 层)+ context 全
  科学载荷 content_hash+audit_scope+checker 版本+证据规范化
  摘要(各轴结论+绑定 hash)+依赖解析状态。同输入幂等;依赖
  已解决 vs unresolved、中心证据 True vs False、fidelity/电荷轴
  差异 ⇒ 不同 hash。**不能用 input_hash 相同推断两次审计可互换
  或缓存结论**(决策层理由码单独记录);
- **审计消费(R3-06/07)**:条件检查走**候选级评估**(旧边
  phase_history 记录值合取不重评+本候选新增要求在当前作用域);
  依赖并集 hypothesis.dependency_refs ∪ context 依赖(缺解析≠
  没有依赖;None 与 [] 语义不混同)。

**请评审**:(a) 证据绑定契约的字段与核验范围;(b) R2p off
披露;(c) input_hash 覆盖域与禁互换推理句。

## 4. 判据四:条件相容聚合(v4 文本)

1–4 同 v3(封闭 7 键+unassessed_dimensions;区间×点三态/单位
unknown;实体身份先匹配;label 仅区间键+注册表;合取)。v4 收紧:

5. **候选级评估与路线快照**(R3-06):旧边评估取 phase_history
   记录值合取(**不拿当前事实重评**);本候选新增要求在当前
   scenario+phase 作用域评估;父冲突在子路线保持(合法分阶段
   路线不冤杀);跨阶段事实(空 phase)可服务多边;要求绑定
   引入边/阶段/场景,**外来绑定构造期结构化拒绝**;展示层两层
   (当前步/路线)并列;
6. **单位契约**(§4 行 1):要求值恒为键规范单位(构造器不接受
   unit 字段);**无单位事实**按规范单位比较+`unit_basis:
   "assumed_canonical"` 注记(区分已归一输入与来源单位未知;
   注记不改变判定状态;显式错误单位仍 unknown);
7. **matrix 键定案**(R3-12):开放文本键,无语义关系的字符串
   不等 ⇒ **unknown**(matrix_value_unresolved;同词 satisfied);
   同义/包含/互斥须注册语义方可升级(首版不建环境本体);氧
   枚举与物种实体的既有硬判保留;
8. **依赖**(R3-07/§4 行 2):支持按**轴集合**累积
   (initial_supply 后 regeneration 不覆盖,启动未知不回退;
   仅再生支持 ⇒ unresolved_initial_supply 保留);
9. hypothesis_id 纳入 requirements/assumptions/dependency_refs
   (排序归一;同反应不同前提=可共存变体;相同语义重放幂等);
   **嵌套载荷冻结**(构造期深拷贝不可变;caller 修改不影响)。

**请评审**:(a) 候选级评估的两层语义;(b) 单位/matrix 契约;
(c) 轴集合累积。

## 5. 判据五:供体一致性诊断(v4 文本)

诊断消费真实编辑协议与 execute_edits 输出;**命名 = 实际净变化
区域诊断,checker scope = region_net_change**(不冒充完整变换一致;
完整模板预留 S3):

1. 判定基础 = 实际净变化集合(键 diff∪原子增删∪逐原子(形式
   电荷/ΔH/**构型**)diff);声明原子单列 declaration_only;
2. **构型比较 = 映射配体下的奇偶法**(R3-03):配体集合相同的
   原子,构型由(手性标签,邻居序置换奇偶)判定——**CIP 标签
   (legacy 或准确)不得作构型变化证明**(配体优先级重排也会
   翻转 R/S;两组真实反例:断键远端原子标签翻而构型保持;双键
   化使配体优先级重排)。准确 CIP(rdCIPLabeler)仅入披露
   (cip_labels);非四面体手性 ⇒ unsupported 不入变化集;
3. **联合映射保手性**(R3-02):useChirality=True(单一保手性
   自同构把整个中心集合映到实际变化集合);**支持范围 = 绝对
   四面体指定/无手性骨架;底物带增强立体组 ⇒ unsupported ⇒
   unknown**(不冒称全范围);单原子轨道不冒充联合等价;截断 ⇒
   unknown;
4. **声明–执行净效应对账**(R3-05):镜像执行器路径模拟
   (编辑前 kekulize(clearAromaticFlags)、有序应用 4 操作、
   add_atom 隐含 anchor 单键、终态 sanitize)→ 声明终态键变化
   vs 实际 diff 的**净效应**比较(中间态不逐条相等:
   s→d→s→d 终态=double);原子属性不在 ops 对账(声明语言无
   对应操作);
5. **中心原子属性披露**:center_property_deltas(电荷/ΔH/构型/
   准确 CIP,before/after 成对)——ops 对账外的可见通道(E-iii);
   只披露不判 center;
6. strict 轴与 ChemicalState 同源规范化;执行失败 ⇒ 全轴
   unknown;legacy_cn_match 仅旁证(立体盲,不同立体种可
   cn=True);
7. **证据载荷内嵌**:诊断携带 center_evidence(绑定输入+各轴
   结论+scope),供判据三证据门消费——strict=False 的证据不得
   注册为 verified。

**请评审**:(a) 奇偶构型比较的化学正确性(含配体集合改变的
边界);(b) 保手性联合映射的支持范围声明;(c) 净效应对账的
执行器镜像口径;(d) center_property_deltas 披露范围。

## 6. 程序证据与状态

- 规则级测试:312 passed/0 新增 skip(合成夹具;R3 复审全部反例
  的仓库化回归;基线 af14fb2 行为级红 8/8;
  G01 全量 not slow 923 passed/16 deselected/0 failed);
- 判据未冻结;mimo R3 的条件处置表见 R4 交付书 §4;
- 被修正采纳的两条(准确 CIP 不充分/单开关不宣称全范围)已按
  程序反证具体化,不整段照搬原文;
- 参考(外部常识,非本仓资产):RDKit Book(CXSMILES 扩展/增强
  立体/立体化学章节)、rdCIPLabeler API。

## 7. 请求的回复格式

对每条判据:1) 结论(同意/不同意/有条件同意+条件);2) 可直接
落进规则文字的修改建议;3) "程序上诚实但化学上误导"风险点。
逐条表态,不接受总体评价式回复。
