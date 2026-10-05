# mimo 化学评审请求:pollutant_pathway_v1 首批化学判据(S0–S2)

- 日期:2026-10-05
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或发布前)
- 评审对象:本仓新 profile `pollutant_pathway_v1` 在 S0–S2 实施中引入的
  **新化学判据草案**(尚未冻结)
- 自包含性:本文只含规则级表述与人工构造的规则级夹具(简单小分子,
  无任何金标/题面/封存逐题数据)
- 用途:由用户转交 mimo;回复原文落盘 `docs/`;结论采信到与程序证据
  互证的程度为止(AGENTS.md;teacher 批复 §八.5)

## 0. 背景(一段话)

本仓 v4.3 原模式(legacy_v43)做"单步反应答题"。现按实施书
`docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md`
升级为"有界污染物路径探索":目标输出是**可能降解路径**与
**与已知条件相容的可能路径**,不是实际主导路线。S0–S2 交付了领域
契约(ChemicalState/ReactionHypothesis/事件-报告-展开分离)、
上下文与条件评估(PathContext)、化学审计(ChemicalAudit)与
admission 策略。下面是需要化学复核的判据草案,全部只做**声明与
核算的诚实性**检查,不涉及性能预测。

## 1. 判据一:分子身份(ChemicalState.state_id)

**规则**:
1. state_id 由"去除原子映射号后的 canonical isomeric SMILES"哈希生成;
   保留形式电荷、同位素、立体信息;
2. 原子映射号([CH3:1])不属于分子身份——改映射号不改变 state_id;
3. 旧口径 CN(电荷归一化 + 立体盲 canonical,引擎/评分冻结口径)仅作
   评分/资产键适配,不作为结构事实;严格结构与 CN 分开保存;
4. 历史只剩 CN 的分子标 `legacy_cn_only`:立体/同位素状态记 unknown、
   formal_charge 记不可知,不猜回结构;
5. 存档产物串(product_smiles_full)可恢复"存档形"状态,但标注
   representation_fidelity=archive_recovered——存档串不含立体/同位素
   不代表原实验没有。

**请评审**:
- (a) "去映射号 + 保留电荷/立体/同位素的 canonical 串"作为分子身份
  键,是否有化学上不妥的合并或分裂风险(例如互变异构体、芳香 kekulé
  表示、互变 protonation)?
- (b) 对映体(手性相反)与"可中和电荷差异"(如质子化胺 vs 游离胺)
  得到不同 state_id、相同 CN——这个分轴是否符合"结构事实与评分键
  分开"的意图?
- (c) CN-only 不猜立体、存档形不冒称全知,是否有遗漏的诚实性缺口?

## 2. 判据二:参与物计量与元素/电荷核算

**规则**:
1. 已知系数必须是正有限有理数;零/负/非有限一律拒绝(且拒绝只表示
   **输入表示违反契约**,不宣称反应本身化学不可能);
2. 系数未知时记 null+unknown,不得参与配平核算;
3. **只有**参与物列表为 source_complete/declared_complete 且全部系数
   known 时才核全反应元素账与形式电荷账:
   - 元素账:Σ(系数×反应物元素计数) 必须等于 Σ(系数×产物元素计数);
   - 电荷账:Σ(系数×原始 formal_charge) 必须为零;**不允许先做电荷
     中和再验守恒**;**不允许自动补 H₂O/O₂/辅酶凑平**;
4. 参与物不完整(partial/unknown)时可以核局部结构差值,但
   full_balance 一律 unknown——不以局部核算冒充全反应配平;
5. 元素/电荷账核实 ≠ 氧化还原转移、辅酶循环、机制、酶催化、热力学、
   速率已核实(生物支持另轴,默认 unknown);
6. 酶/催化剂记 catalytic_support,不进净反应计量。

**请评审**:
- (a) "禁止先中和再验电荷守恒 + 禁止自动补水/氧/辅酶"是否正确?
  现实中生物反应常涉及未列出的 H₂O/O₂/NAD⁺——我们的立场是:
  未声明的参与物导致 unknown,而不是替用户补齐。这会不会把大量
  真实生物反应错判为"元素账 violated"?(注意:我们只在全参与物
  声明完整时才核账,不完整时是 unknown 而非 violated。)
- (b) 局部差值(partial 时)与全账的边界是否清晰?
- (c) 有没有必须补的第 7 条?

## 3. 判据三:admission 决策表(P0-4)

**规则**(有序,首中即决;任何 unknown 不自动 reject):

| 规则 | 条件 | 处置 | 理由码 |
|---|---|---|---|
| R1 | 结构无法解析(parse violated) | reject | structure_unparseable |
| R2 | 活动门禁显式拒绝(仅经评审的名单:方向/资格/SMILES 门) | reject | active_gate_rejected |
| R3 | 当前场景有来源的必要条件冲突(如无氧 vs 必需 O₂) | defer(blocked) | current_scenario_conflict |
| R4 | 预算/等待状态 | defer | budget_or_wait |
| R5 | 条件/完整账/映射/step_scope 未知 | retain_conditional | unknown_checks_present |
| R6 | 全部核实且无冲突 | expand | all_verified |

语义要点:
- reject 只因"结构非法"或"经评审的活动门禁显式拒绝"——化学上
  **未知**的东西不产生 reject;
- 条件冲突(当前场景事实 vs 反应有来源的必需条件)→ defer:假设
  保留、不在此场景展开,可展示为"需不同条件的备选";
- retain_conditional 允许有界探索,未知依赖沿途继承;
- step_scope=multistep_summary 保留为汇总边,不冒充净酶反应。

**请评审**:
- (a) "元素账 violated"是否应进入 R2 类 reject?(当前设计:完整
  声明配平后元素不守恒 → violated → 落在 R5 之前的哪个位置?
  实际当前实现里元素 violated 会让 audit 有 violated 检查但 admission
  只对"结构非法/活动门禁"reject,元素 violated 走 retain_conditional
  ——这是**故意的保守**(violated 的账目说明声明有问题,但我们
  不宣称反应不可能)。这个立场对吗?)
- (b) R3 的"有来源的必需条件冲突"边界:观察条件(文献说 25°C
  观察到)不算必需条件,只有来源明确声明 essential 才算——对吗?

## 4. 判据四:条件相容聚合(环境轴)

**规则**:
1. 首版条件键限定:oxygen_regime、pH、temperature_C、matrix、
   electron_donor、electron_acceptor、growth_substrate;
2. 聚合:有来源 essential 要求与明确已知事实矛盾 → conflict;
   声明覆盖维度内全部必要要求有来源并满足 → compatible;
   缺事实/覆盖未知/要求列表空 → unknown(**空列表不自动相容**);
3. pH/温度:范围无交集 → conflict;部分相交但实际值不确定 →
   unknown;**输入点**位于支持范围才判满足;
4. 文献观察条件只作参考(basis=observed_condition_reference),
   不参与门禁,不自动成为当前场景事实;
5. preference 只提示,不作冲突门;
6. assessed_scope 由聚合派生不继承请求:请求 condition_compatible
   但有未知 → 最终 possible;
7. 未列出某共底物 ≠ 已证实没有它(unknown ≠ known_absent);
   "土壤/污水"不推出氧条件。

**请评审**:
- (a) 第 3 条区间语义(无交集=冲突/部分交集+不确定=未知/点在范围内
  =满足)是否与生物降解文献的常见表述相容?
- (b) 有没有应该在首版键集合里但缺失的条件键(会显著影响
   条件相容性判断的)?

## 5. 判据五:供体一致性诊断分轴

**规则**(类比编辑结果 vs 供体预期):
- strict_target_match:实际产物与预期产物的严格 isomeric canonical
  一致(合法编辑但偏离预期 → False);
- legacy_cn_match:CN 一致,仅作旁证,不升格为结构一致;
- reaction_center_match:仅在原子对齐 resolved 时判定;对称等价
  (对齐等价类内的原子替换)不判 False;对齐不可得/歧义 → unknown
  (不猜中心);立体信息未知不使已有充分映射支持的 center 判定
  变 unknown;
- extra_changes:不属于中心(及等价类)的编辑原子列表。

**请评审**:
- (a) "对称等价类内的中心替换视为 center 匹配"是否正确?
- (b) strict/cn/center 三轴分离是否足以避免"CN 相同冒充结构一致"和
  "映射缺失伪造中心核实"两类错误?

## 6. 程序证据与状态

- 以上判据全部有规则级单元测试(简单小分子夹具:乙醇/乙酸/O₂/
  丙氨酸对映体/水杨酸裂解占位等),88 个 ppv1 测试全绿;
- 判据**尚未冻结**:采纳与否待本评审与本仓 review 会话复核;
- 实施书 §8 的参考立场:本仓已知 G2(v43-cons-2)是 H/O 自由的
  有限规则筛查,unclassified=覆盖未知不惩罚;元素/电荷账是
  **新增**的分项,不改变 G2 语义;
- 参考(仅外部常识,非本仓资产):IUBMB 乙酰苯羧化酶(EC 6.4.1.8,
  厌氧乙苯降解增碳)说明"新增碳/辅底物反应不能被元素白名单否定
  为普遍不可能"——本仓未因该例修改任何旧门禁。

## 7. 请求的回复格式

对每条判据给出:
1. 结论:同意 / 不同意 / 有条件同意(条件是什么);
2. 具体修改建议(若有),请给出可直接落进规则表述的文字;
3. 明确指出任何"程序上诚实但化学上误导"的风险点。

不接受"总体看起来不错"式回复;逐条表态。
