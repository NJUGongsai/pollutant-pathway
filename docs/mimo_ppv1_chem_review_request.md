# mimo 化学评审请求:pollutant_pathway_v1 化学判据(S0–S2 回修版 v3)

- 日期:2026-10-06(R3 回修版;替换 2026-10-05 v2 请求)
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或发布前)
- 评审对象:S0–S2 第三轮回修后的化学判据草案 v3(实现于
  `src/pathway_v43/pollutant/`,ppv1-*-3 版本族);**尚未冻结**
- 与 v2 的差异来源:第二轮 mimo 回应
  (`docs/mimo_ppv1_chem_review_response_r2.md`)+ Codex R2 复审
  (`docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R2_2026-10-06.md`
  R2-01～R2-12 与 §5 采纳边界)。mimo 第二轮全部"有条件同意"的
  条件已按 Codex 裁定处置;不采纳两条(见 §6 处置表):"中心
  verified 仅由供体诊断生成"(过窄,改为注册 checker 制)与
  "scope 只由可用事实键派生"(不足,改为按实际执行检查派生)。
- 自包含性:规则级表述与合成规则级夹具,无任何金标/题面/封存
  逐题数据;由用户转交,回复原文落盘 `docs/`

## 0. 背景(一段话)

v2 判据经第二轮代码复审发现底座缺陷(R6 可在零条件评估下达成、
增强立体公开表示丢注解、供体诊断把声明当执行、条件无阶段绑定、
存储参照不校验等),已全部回修并有行为级红绿回归。本轮请评审
**回修后的判据文本 v3**。目标不变:可能降解路径与条件相容路径的
诚实表示,不是实际主导路线预测;unknown 不升格,verified 不靠
模型或调用方自报字符串。

## 1. 判据一:分子身份(v3 文本)

1. state_id 仅对 sanitize 成功、芳香性已感知的分子生成;sanitize
   失败不生成 state_id(归 admission R1,仅实际语法/价态非法)。
2. 身份键 = **规范化 canonical CXSMILES**(剥原子映射号 + 剥 ABS
   冗余注解段):
   - **plain 与 |a:…| 同键**(ABS 注解与 isomeric SMILES 默认绝对
     构型是同一立体事实,mimo 1.3(1) 归一分支);
   - AND/OR 组**整组翻转**同键(相对立体事实的等价类:AND 组=未知
     何者对映体的单一非对映体声明;OR 组=两组分混合物声明,均对
     组内全中心整体反转不变);**部分翻转**(组内只翻一个中心)
     保持不同键;AND 与 OR 不合并;原子排列归一;
   - 无组分子输出与普通 canonical isomeric SMILES 逐字相同。
3. **公开表示往返闭合**:state 的 smiles_isomeric = 同一规范化
   串(带 |&…|/|o…| 注解),重新解析重建同一 state_id;底物档案
   structure_smiles 同源。原始输入串(含注解差异)保留在
   structure_smiles_raw(出现记录层)。
4. representation_fidelity 分轴(stereo/isotope/formal_charge/
   protonation_basis);**任一轴 ≠ as_written ⇒ identity_fidelity
   检查 unknown 并列轴**(不再 verified+reason 注记混读,mimo
   1.4(4))。存档形电荷轴 as_written 立场不变(中性是合法结构
   事实;是否丢失按来源转换历史)。**radical 保真轴登记为已知
   缺口**(身份层区分自由基;本轴未实现,mimo 2.2(a))。
5. CN 只出现在评分/资产键(cn_identity);其 basis=scoring_key
   标记 = contract clause, implementation pending(S3;未落地前
   不得在报告呈现该字段)。edge_kind(互变/质子化边)同 pending。

**请评审**:(a) 整组翻转归一/部分反转保持区分的化学正确性
(与 RDKit RegistrationHash 的增强立体等价语义一致性);(b) 公开
表示 = 身份键同一串的取舍;(c) radical 轴缺口登记是否足够。

## 2. 判据二:参与物计量与元素/电荷核算(v3 文本)

1. 系数正有限有理数;零/负/非有限拒绝(R2b)。
2. 元素账计入全部氢(重原子 GetTotalNumHs + 独立氢顶点);
   **D/T 并入元素 H**(同位素差异只在身份/同位素轴体现,不入本
   账);**自由基未配对电子不入账**;verified 仅指元素与形式电荷
   的数值闭合,不指同位素计量、电子转移、机制(mimo 2.2(a))。
3. 完整声明才核全账;未声明完整性保持 unknown(不默认
   complete_stoichiometric 子型,同 v2)。
4. 电荷账前提(轴 == as_written)与不补水/氧/辅酶,同 v2。
5. 账不平 ⇒ violated + 逐元素 Δ 向量;**omission_pattern_matches
   为结构化字段** {pattern, excess_on(多出侧), missing_from
   (缺写侧), element_delta}(mimo 2.3(2));H+ 模式输出名
   **H+_count1**(仅表示 H 计数为 1 的模式名,不含质子/电子计量);
   语义声明:仅数值相符,不证明缺项原因。
6. violated ⇒ retain_conditional(R5d,触发集合显式限定
   {element_accounting, formal_charge_accounting};其他检查
   violated 走 R5v declared_violated_other 独立码,mimo 3.2(4))。
7. 局部结构差 local_delta = contract clause, implementation
   pending(本轮显式排除出冻结范围;S3/展示层二选一后定)。

**请评审**:(a) 结构化模式字段与 H+_count1 命名;(b) R5d 触发
集合限定;(c) 同位素/自由基口径注记是否充分。

## 3. 判据三:admission 决策表(v3 文本;有序,首中即决)

| 规则 | 条件 | 处置 | 理由码 |
|---|---|---|---|
| R1 | 实际输入语法非法(parse violated=unparseable_smiles) | reject | structure_unparseable |
| R1b | 参与物 state 引用悬空(账本/引用完整性,非语法) | reject | participant_state_missing(理由码不压平) |
| R2 | 活动门禁显式拒绝(reject_gates 名单;旧门禁经版本化 mapper ppv1-gate-mapper-2) | reject | active_gate_rejected |
| R2p | 逐产物冻结门禁 verdict 被真实消费:全部共同产物被拒 ⇒ reject;部分被拒 ⇒ retain(被拒产物保留拒因、不可展开) | reject / retain | per_product_gate_rejected(逐产物拒因可追溯) |
| R2b | 表示契约违反(构造期 HypothesisContractError.detail 须由调用方映射传入) | reject | contract_violated_representation |
| R3 | 有来源 essential 条件与当前场景已知事实冲突 | defer | current_scenario_conflict |
| R4 | 预算/等待 | defer | budget_or_wait |
| R5d | {元素,电荷}账 violated | retain | declared_account_violated |
| R5v | 其他检查 violated(如确定性 checker 的中心偏离) | retain | declared_violated_other |
| R5c | 必需适用检查覆盖缺口(窄 audit_scope 只是诊断;语义 NA 白名单:关闭的有限规则诊断/汇总边) | retain | required_check_coverage_missing |
| R5 | 检查 unknown/因缺输入未执行 | retain | unknown_checks_present |
| R6 | 全部必需适用检查覆盖且 verified,无 unknown/violated/缺输入未执行 | expand | all_verified |
| R7 | 无适用检查 | retain | 保守,不冒充核实 |

关键定义:
- **因缺输入未执行的检查记 unknown(reason=*_not_run),不得记
  not_applicable**;context 缺失 ⇒ condition_check=unknown
  (condition_assessment_not_run),mimo 3.2(1);
- **R6 不含缺输入跳过**:必需适用检查的覆盖核算(不在审计内/
  非白名单 NA ⇒ 覆盖缺口 ⇒ 不得 R6);
- **自报签名不授信**:transformation_signature_status=verified 只是
  声明;中心检查 verified 须 center_evidence = 注册版本化确定性
  checker(CENTER_CHECKER_REGISTRY,现含 ppv1-donor-diagnostic-3;
  其他 checker 须独立列项评审后注册)的输出,含 center_match 与
  declaration_mismatch;缺证据 ⇒ unknown(center_evidence_missing);
- **input_hash 覆盖实际科学输入**:hypothesis 完整语义载荷(含
  requirements/assumptions/dependency_refs)、参与物 state 身份、
  context 身份、audit_scope、checker 版本。

**请评审**:(a) R1b/R2p/R5v/R5c 四行的边界;(b) 中心证据注册制
(替代 mimo"仅供体诊断"提案);(c) R6 覆盖核算定义。

## 4. 判据四:条件相容聚合(v3 文本)

1. 条件键封闭 7 键 + 登记缺口键随相容结论输出 unassessed_dimensions
   (同 v2)。
2. 值语义分 basis:range/point/optimum/label/**entity**(新:物种/
   枚举键的实体比对,不走 label/注册表):
   - label 仅区间键 + 注册表(空 ⇒ unknown);物种键取值须可解析
     实体引用,不可解析 ⇒ unknown(非 conflict);
   - 区间事实 × 必需点:点 ∈ 区间 ⇒ **unknown**
     (point_in_uncertain_range,实际点值不确定);退化区间 [a,a]
     × 点=a ⇒ satisfied;点 ∉ 区间 ⇒ conflict
     (point_outside_interval,独立理由码);
   - 单位:与键规范单位不符 ⇒ **unknown(unit_mismatch)**,首版不
     做换算(可入账不参与数值比较);
   - 物种作用域:实体身份先匹配(他实体缺席 ≠ 本实体状态;多种
     已知供体并存;同实体 present+absent 才是不一致)。
3. 事实/要求**绑定所属边/阶段**(R2-04):Requirement 构造即绑定
   introduced_phase_id/scenario_ref/introduced_edge;评估用该要求
   **引入阶段**的适用事实,不拿新阶段事实重评旧要求;阶段转换冻结
   历史快照(phase_history),路线聚合 = 逐边合取——**旧边冲突在
   路线结果中保持**;转换只影响后续,不写成反应边;嵌套对象
   (Requirement/事实/依赖)不可变化,分支互不污染。
4. 聚合:合取(同键不覆盖);unknown 语义(无源必要性/值语义未
   声明/标签无映射/实体不可解析);assessment_scope 从**实际执行
   的必要检查**派生(有事实 ≠ 已检查),缩范围留痕。
5. 依赖分轴(support_axis:reaction/regeneration/initial_supply):
   仅再生关系有支持 ⇒ unresolved_initial_supply **保留**(再生支持
   ≠ 启动供给已解决);补 initial_supply 轴证据才解决;环不自动
   reject。
6. hypothesis_id 纳入 requirements/assumptions/dependency_refs:
   同反应不同条件/依赖前提 ⇒ **不同假设变体**,可共存落账;相同
   语义重放幂等。

**请评审**:(a) 阶段绑定+历史快照合取;(b) 区间×点三态与单位
边界;(c) entity basis 与物种作用域;(d) 再生/启动分轴。

## 5. 判据五:供体一致性诊断(v3 文本)

诊断消费真实 AtomTool 编辑协议(v43-editproto-2)与 execute_edits
输出;**命名 = 实际净变化区域诊断**(不冒充完整变换一致):

1. 判定基础 = **实际净变化集合** = 键 diff(成/断/键级,kekulé
   归一——芳香表示差异不是化学变化)∪ 原子增删 ∪ 逐原子(形式
   电荷/ΔH/CIP 立体)diff;**声明的编辑原子单列 declaration_only,
   不参与判定**;
2. **零净变化**(执行前后结构身份一致)⇒ center=unknown
   (no_executed_change),永不 True;
3. **声明–执行对账**:声明键变化(原子对+to_order)须实际出现,
   实际键变化须被声明覆盖,add_atom 原子须存在且被声明;失配 ⇒
   declaration_mismatches,strict/center 至少 unknown;
4. **plain 产物 vs mapped 执行图对账**:不一致 ⇒ 两轴 unknown +
   原因(执行图不可信);
5. reaction_center_match:实际变化 ⊆ 对齐中心(direct)或存在
   **联合图映射**(单一自同构把整个中心集合映到实际变化集合)
   ⇒ symmetric_equivalent;单原子各自同轨道**不冒充**联合等价;
   搜索截断 ⇒ unknown;全部中心原子须有映射(部分缺 ⇒ unknown);
6. extra_changes 逐原子 Δ 补 ΔH 与 ΔCIP(before/after 成对);
7. 等价类降为**披露**(canonical_rank_breakTies_false 口径;自报
   非等价类整体拒用并记录),不参与 v3 center 判定;
8. strict 轴与 ChemicalState 同源规范化(plain/ABS 互命中,整组
   反转互命中——注解差异不冤枉供体);执行失败 ⇒ 全轴 unknown;
   legacy_cn_match 仅旁证。

**请评审**:(a) 实际净变化集合的定义充分性;(b) 联合图映射判定
(环己烷 {相邻对} vs {对位} 反例:单原子轨道覆盖但无联合映射 ⇒
False);(c) 声明–执行对账的范围(仅键变化与原子增删双向覆盖,
属性 diff 不入对账)。

## 6. 程序证据与状态

- 规则级测试:226 passed / 0 新增 skip(合成分子夹具;含 R2 复审
  全部反例的仓库化回归与 8/8 行为级红验证);
- 判据未冻结;mimo 第二轮"有条件同意"的条件已全部处置或按 Codex
  裁定修正(处置表见 R3 交付书 §4);
- 不采纳两条及其理由:①"中心 verified 必须仅由供体诊断生成"——
  过窄,其他注册、版本化、可追溯的确定性 checker 也可提供证据,
  任何自报字符串都不够(Codex R2 复审 §5);②"scope 只由可用事实
  键生成"——事实可用不代表该项要求实际审过,改为按实际执行的
  检查派生(Codex 同 §5);
- 参考(外部常识,非本仓资产):IUBMB EC 6.4.1.8(新增碳/辅底物
  反应不被元素白名单否定)——本仓未因此改旧门禁。

## 7. 请求的回复格式

对每条判据:1) 结论(同意/不同意/有条件同意+条件);2) 可直接
落进规则文字的修改建议;3) "程序上诚实但化学上误导"风险点。
逐条表态,不接受总体评价式回复。
