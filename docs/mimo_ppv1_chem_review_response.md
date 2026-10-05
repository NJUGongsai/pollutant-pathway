# mimo 化学评审回应:pollutant_pathway_v1 首批化学判据(S0–S2)

- 评审对象:`docs/mimo_ppv1_chem_review_request.md`(2026-10-05,五条判据草案)
- 范围:只评规则级表述与规则级夹具;不接触题面/金标/封存数据;结论采信到与程序证据互证的程度为止
- 格式:逐条给 结论 / 可直接落进规则的文字 / "程序上诚实但化学上误导"的风险点;不作总体评价
- 前置事实采信:88 个 ppv1 测试全绿(§6);判据未冻结,本轮意见应在冻结前处置

---

## 1. 判据一:分子身份(ChemicalState.state_id)

### 1.1 结论:**有条件同意**

条件(四条,缺一则身份键会在边界上静默错判):

- **C1 身份必须定义在 sanitize 成功之后**,sanitize 失败不生成 state_id(与 admission R1 对齐);
- **C2 representation_fidelity 必须分轴**,不是单旗标;
- **C3 扩展立体(enhanced stereo, AND/OR 组)要么显式纳入、要么登记为超范围**——普通 isomeric SMILES 会把它静默丢掉;
- **C4 互变/质子化/对映体只能作"派生等价类"标签,永不并入身份**,且展开去重键必须是 state_id,不得用 CN。

### 1.2 具体修改建议

**(1) 身份生成补一句(落进判据一第 1 条后):**

> state_id 仅对 **sanitize 成功、芳香性已感知**的分子生成;sanitize/芳香感知失败 ⇒ 不生成 state_id,该结构不得入图(归 admission R1)。canonical 在芳香感知后输出,故 Kekulé 写法差异不产生分裂;`[nH]`/`N` 之类互写差异由感知统一,不入身份键。

理由:身份键的分裂风险不在 Kekulé(芳香感知已归一),而在"未感知就 canonical"与"失败仍哈希原始串"。后者会让同一分子的两种写法拿到两个 state_id——这是最现实的分裂源。

**(2) representation_fidelity 改为分轴声明(替换原第 5 条口径):**

> `representation_fidelity` 按轴记录:`stereo / isotope / formal_charge / protonation_basis / radical`,每轴 ∈ {as_written, absent_in_archive, unknown}。
> - `legacy_cn_only`:`stereo=unknown, isotope=unknown, formal_charge=unknown, protonation_basis=neutralized_by_cn`(CN 已中和,电荷不可猜回);
> - `archive_recovered`:`stereo=absent_in_archive, isotope=absent_in_archive, formal_charge=as_written, protonation_basis=as_written`。
> 存档串可能本身就是旧 CN 形(已中和)——此时 `formal_charge` 须记 unknown 而非 as_written,以存档串是否带电荷分离形式判定。

理由:单旗标 `archive_recovered` 会把"缺立体"与"缺电荷"混在一起;而**电荷轴直接决定判据二的电荷账能不能算**(见 2.2(2))。这是一个跨判据的诚实性口子。

**(3) 扩展立体补一条:**

> 输入含 enhanced stereo(AND/OR 组)时:若输出格式不含该信息(CXSMILES 之外的普通 SMILES),该轴记 `unknown` 并登记"扩展立体超 v1 范围";**不得**以丢组后的串充当完整立体事实。同理,Enhanced stereo 下两个不同立体事实可能得到同一 isomeric SMILES——这是合并风险,须以 unknown 标注而非默认相同。

**(4) 派生等价类(新增小节,身份与展示分离):**

> 派生键(只用于展示/提示,**永不用于合并状态、永不用于展开去重**):
> - `tautomer_group_id`:互变异构归组(TautomerEnumerator,仅派生);
> - `neutral_parent_id`:去质子化后母体归组(即 CN 的结构语义);
> - 展开去重与"已见状态"判定一律用 `state_id`;**明令禁止用 CN 去重**——否则对映体分支、质子化分支在探索阶段被静默折叠,与判据一 (b) 的分轴意图自相矛盾。
> - 仅质子化/互变差异构成的边,标 `edge_kind = protonation_equivalent / tautomer_equivalent`,**不得以"降解转化"面目出现在路径里**(也不计作新转化)。

**(5) (b) 分轴答复:** 对映体不同 state_id、同 CN;质子化态不同 state_id、同 CN——**符合"结构事实与评分键分开"的意图,同意**。且对降解题域是必要的:手性污染物(芳氧羧酸类除草剂等)的对映体选择性是真实化学,评分键合并、事实键分开正是该有的形状。唯一纪律:CN 只许出现在评分/资产键,出现处必须标 `basis=scoring_key`,防止下游把 CN 相同读成"同一物质"。

### 1.3 "程序上诚实但化学上误导"风险点

1. **质子化/互变边被读成降解步骤**:图里 pH 造成的胺/铵边若与真实转化边同列,路径会被读出"假反应"。(4) 的 edge_kind 是解法。)
2. **CN 去重折叠对映体分支**:程序上省了重复,化学上抹掉了对映体选择性。
3. **存档中和形被当作生理形态**:archive 串若是旧中和形,拿它谈"该 pH 下的物种分布"是无据推断——分轴 fidelity 就是防这个。
4. **enhanced stereo 静默丢组 = 静默合并**,错误方向是最难发现的"两个事实变一个"。

---

## 2. 判据二:参与物计量与元素/电荷核算

### 2.1 结论:**有条件同意**

条件(三条):

- **C1 电荷账只对"原始电荷可知"的输入可算**——凡 CN 形/中和形输入,电荷账必须 `unknown`,不得拿中和后的电荷算(算了必得 0,是假通过);
- **C2 账不平必须输出缺口向量与诊断子类**,但不改判、不自动补物;
- **C3 局部差值必须禁词**:不得以"配平/守恒/平衡"字样呈现,且未声明 1:1 计量假设时不得作定量解释。

(a) 的直答:**"禁止先中和再验 + 禁止自动补水/氧/辅酶"是对的,同意**——先中和会把质子账销毁(缺 H⁺ 的反应经中和后假平),自动补物会把"声明不完整"伪装成"已配平"。你们"不完整 ⇒ unknown 而非 violated"的三态设计也是对的,错判方向被挡住了。
**但 violated 侧有一个真实误伤面**:文献/数据库大量把水解写成 **不含 H₂O 的转化式**(`RCOOR' → RCOOH + R'OH`),来源又标 declared_complete ⇒ 元素账必然 violated。你们不 reject(落 retain_conditional),伤害有界,**但 violated 标签在展示上会把"书写惯例"读成"化学不守恒"**——这是本判据最大的误导点,解法在 (2)。

### 2.2 具体修改建议

**(1) 第 7 条(请评审 (c) 的答案,建议直接补入):**

> 7. **缺口向量与诊断子类(不改判)**:full_balance 核算失败时,输出每元素缺口 `Δ = Σ(反应物) − Σ(产物)` 与电荷缺口,并附加诊断标注:`imbalance_matches ∈ {H2O, 2H(+2e), O2, H+, none}`(缺口向量与该闭合小模式**逐元素精确相符**才标注)。标注**只作展示**:不修改账、不自动补参与物、不改变 violated 判定;但 displayed reason 须区分
> `declared_account_violated_convention_suspect`(缺口匹配 H2O/2H+2e/O2/H+ 模式,高度疑似书写惯例漏项)
> 与 `declared_account_violated`(真不平)。
> 另:输入为 `legacy_cn_only` / 中和形时,**电荷账恒为 unknown**(原始 formal_charge 不可知),元素账按 as_written 计并标 `element_basis=neutralized_form`。

理由:这把"诚实的 violated"从"误导的 violated"里分出来——仍然不替用户补齐(立场不变),但审阅者一眼看出是惯例漏项还是真错。夹具建议:水解式(缺 H₂O)、铵盐反应(缺 H⁺)、脱氢(缺 2H+2e)三个 Δ 模式各钉一例。

**(2) 第 3 条补一句(完整性语义):**

> `declared_complete` 须区分 `complete_stoichiometric`(净反应计量式,元素/电荷账适用)与 `complete_transformation`(转化级书写,H₂O/H⁺/e⁻ 记账明确出scope ⇒ full_balance 记 `not_applicable`,不记 violated)。来源未声明子型时按 `complete_stoichiometric` 从严处理,并接受其 violated 可能源于惯例(靠第 7 条诊断区分)。

(若不想引入子型,至少保留 (1) 的诊断子类——两者取一,不能都不做。)

**(3) 第 4 条补禁词与计量前提(局部 vs 全账边界,b 问):**

> 局部结构差值 = **具名反应物与具名产物之间逐分子差**,三重限制:① 呈现与日志中禁用"配平/守恒/平衡/配对"等词,一律写"逐分子结构差";② 参与物系数未知或非 1:1(二聚、歧化)时,**不得作定量原子解释**,只报方向(增/减/不变);③ 局部差值永不升格为 full_balance,`full_balance` 与 `local_delta` 两个字段互斥可见,不得同屏并列造成"账已核"的读感。

理由:系数未知时按 1:1 算差值会把"2A → B"算成"丢了 2 个碳"——这是把计量无知算成化学结论的典型路径。边界本身(1 与 4)是清晰的,缺的是呈现纪律。

**(4) 第 1/2 条保留不动**(系数契约拒绝 = 表示层拒绝,不宣称反应不可能 ✓);但见 3.2(1):这个 reject 在判据三决策表里**没有落点**,需补行。

### 2.3 "程序上诚实但化学上误导"风险点

1. **惯例水解式被判 violated**:读起来像"来源化学错了",实际是来源没写 H₂O。
2. **中和形输入的电荷账**:若实现拿 CN 电荷去算,账"恒平"是假通过——比 violated 更危险,必须按 2.2(1) 强制 unknown。
3. **局部差值标着"守恒已核"**:系数未知时的 1:1 假设计量差,是把无知算成事实。
4. **"元素账核实"被读成"反应已验证"**:第 5 条已挡,但展示层须让 `element_account=verified` 与 `biological_support=unknown` 同屏,防局部读取。

---

## 3. 判据三:admission 决策表(P0–4)

### 3.1 结论:**同意**(含 (a)(b) 两个直答),另需补两行/两个理由码,否则与判据二存在映射缺口

### 3.2 具体修改建议

**(1) 补一行 R2b(闭合与判据二的映射):**

| 规则 | 条件 | 处置 | 理由码 |
|---|---|---|---|
| R2b | **契约表示违反**(判据二第 1 条的零/负/非有限系数;酶/催化剂被计入净反应计量;参与物列表结构性违约) | reject | `contract_violated_representation` |

理由:判据二第 1 条明文"一律拒绝",而判据三的 reject 只认 R1(解析)与 R2(活动门禁)——**判据二的 reject 在决策表里无处落地**。补 R2b 并在理由码里写死 `representation`(非化学),正好落实判据二"只表示输入违反契约"的语义,防止实现者把它并进 R2 的"化学门禁"读。

**(2) (a) 直答——元素账 violated 不进 reject,当前立场正确,但必须与 unknown 分家:**

> violated ⇒ `retain_conditional`,理由码 **`declared_account_violated`**(独立于 R5 的 `unknown_checks_present`,两者不得同码)。
> 语义:violated = **声明与结构不一致**(有证据的发现),unknown = **无证据**。二者同码会让"来源记错了"与"我们不知道"在下游不可区分——前者恰恰是最该被看见的信号。仍不 reject:账不平只证明声明内部矛盾,不能证明反应不存在(见 2.2 惯例水解例),reject 就把文书缺陷升格成了化学不可能的宣称。
> 展示层:`declared_account_violated` 必须与 `unknown` 分栏;配合 2.2(1) 的诊断子类区分"疑似惯例"与"真不平"。

**(3) (b) 直答——R3 只认 source 明示 essential,**同意**,但要登记覆盖率后果与一个边界:

> R3 的 essential 判据为**封闭短语集**(如 requires / requirement is / only in the presence of / obligate / strict(ly) aerobic / anaerobic only / 需氧 / 严格厌氧 / 依赖……),命中且来源明示为必要条件 ⇒ essential;**一切观察性表述**(25°C observed、"at pH 7 activity was high"、研究设置的培养条件)⇒ `observed_condition_reference`,不进门禁。
> **边界补充**:来源的"培养/实验设置"(如"孵育于 30°C 有氧")既不是 reaction-essential 也不是可忽略参考,记 `scenario_fact_of_source`——它是来源场景的事实,不得自动当作当前场景事实,也不得当作反应必需。
> **覆盖率登记**:文献极少用 essential 字面,R3 实际触发会偏低,真实必要条件会大量落 unknown(R5)→ retain_conditional。这是安全方向(无假冲突),但须在预注册里写明"R3 触发率预期偏低属已知覆盖特性",防止日后把它读成"条件冲突罕见"。

### 3.3 "程序上诚实但化学上误导"风险点

1. **violated 与 unknown 同码** = 把"有证据的不一致"展示成"无证据"——最实质的一条,见 3.2(2)。
2. **判据二的 reject 无落点**(映射缺口):实现者只能自行归类,可能被并进"活动门禁"而显示成化学拒绝。
3. **R3 低触发被读成"条件不冲突"**:unknown ≠ compatible,第 4 判据第 2 条已守空列表,此处再声明一次同族纪律。

---

## 4. 判据四:条件相容聚合(环境轴)

### 4.1 结论:**有条件同意**

条件:**optimum 不产生 conflict**;标签→区间的映射须注册表化,禁止现推;"观测条件不进门禁""空列表不自动相容""unknown ≠ known_absent""土壤/污水不推氧"四条**同意,原样保留**。

### 4.2 具体修改建议

**(1) 第 3 条改写(落文字):**

> pH/温度按 `basis` 分语义:
> - `range`(支持区间):无交集 ⇒ conflict;部分相交且实际值不确定 ⇒ unknown;输入点在区间内 ⇒ satisfied;点在区间外但来源同时给了更宽的容忍区间 ⇒ 按容忍区间判,不按 optimum 判;
> - `optimum`(最适值,文献最常见形态):**永不产生 conflict**,只作 satisfied(点=最适)或 preference 提示;
> - `label`(mesophilic / psychrophilic / neutrophilic 等类标):必须经**注册表**(仓库内封闭表)映射为区间后才参与判定;无注册映射 ⇒ unknown,**禁止现推区间**(那是编造精度);
> - 来源只给单一数值且 basis 不明 ⇒ 按 `optimum` 处理(从严方向是不产生 conflict,而是 unknown/preference)。

理由:文献里"optimum pH 7"、"mesophilic"是主流写法。把最适值当支持区间,会出现"6.5 在区间外 ⇒ conflict"这种假冲突——把最适值读成生存边界是环境微生物文献里最常见的误读,判据不该复刻它。

**(2) (b) 首版键集合缺口(按对相容性判断的影响排序):**

必须进 v1(否则相容性会给出系统性偏乐观的读数):
1. **`biotic_abiotic`**(生物/非生物):光解、水解、自由基与酶促是不同归属;缺它会让"可能路径"把非生物过程当生物转化展示;
2. **`light_regime`**:直接光解/光敏化是许多污染物的首步,黑暗条件下的结论不能默认成立;
3. **`salinity / ionic_strength`**:海水/淡水/盐田差异显著影响可培养性与卤代物还原脱卤;
4. **`redox_regime`(Eh)**:oxygen_regime 只是它的粗投影;Fe(III)/硫酸盐/硝酸盐终端接受体的分化靠 electron_acceptor 部分覆盖,Eh 本身仍是独立事实轴。

建议留 v2 但**现在登记为已知缺口**(否则等于宣称"这些不影响相容性"):
5. **`required_trace_elements/cofactors`**:corrinoid(B₁₂ 类)对还原脱卤、Mo/W 对甲酰化/甲酸脱氢、Se 对硒代半胱氨酸酶——正是"某转化在此环境不可能"的高频真实约束;
6. **`substrate_concentration/toxicity_threshold`**:高浓度抑制(甲苯、酚)使"能降解"与"该浓度下能降解"分裂;
7. **`inoculum_source`**(活性污泥/纯培养/沉积物):影响"可发生"的经验基础;
8. **`phase/bioavailability`**(溶解相/吸附相):影响实际可达性,对"可能路径"影响小于上者,登记即可。

落文字建议(补进第 1 条后):

> 首版条件键封闭枚举;**已登记的 v2 缺口键**({required_trace_elements/cofactors, substrate_concentration, inoculum_source, phase_bioavailability})缺位 ⇒ `assessed_scope` 必须把这些维度列为 `unassessed`,相容结论不得显示为"全维度相容",只显示"已评估维度内相容"。

理由:这把"键集合不全"从隐含假设变成显式 scope——正是本判据自己的"覆盖未知 ⇒ unknown"纪律在键集合层面的延伸。

### 4.3 "程序上诚实但化学上误导"风险点

1. **最适值当边界**:optimum→conflict 的假冲突,方向是错杀真可能路径。
2. **标签现推区间**:把 mesophilic 私下映成 20–40°C 是编造精度,注册表化后才可审计。
3. **键集合不全 ⇒ "相容"读感偏乐观**:缺 biotic_abiotic/light/salinity 时的 compatible 会被读成"环境上站得住",实际只评了三个轴——须靠 `unassessed` scope 标注兜住。
4. **来源场景事实当当前事实**:第 4 条已挡,须在展示上给 `basis` 字段,防局部读取。

---

## 5. 判据五:供体一致性诊断分轴

### 5.1 结论:**有条件同意**

条件:对齐等价类的求值必须**在自同构像上取一致结论**;"中心匹配"必须带 `match_basis` 而非裸 True;strict 失败时须区分"互变/质子化差异"与"真偏离"。

### 5.2 具体修改建议

**(1) (a) 直答——对称等价类内替换不判 False:同意,但要三句限定:**

> - 等价类必须由**产物分子图自同构**(canonical rank / automorphism)在实际结构上算出,不得由底物侧想当然外推——**第一次取代后对称即破**(两个位置变非对映区分),第二次编辑必须可判;
> - 对齐解在自同构群下不唯一时:**对全部等价像求 center 结论;一致 ⇒ 按该结论,不一致 ⇒ unknown**(不许任取一个像就下判);
> - 判定输出带 `center_match_basis ∈ {direct, symmetric_equivalent}`;`symmetric_equivalent` **不得升格为"机制已证"**——结构层面无法区分 ≠ 生物学不区分(前手性面/对映面的酶识别是真实存在的,柠檬酸合酶型的立体专一无法由图等价给出)。

理由:结构层面等价 ⇒ 产物同一分子 ⇒ strict 轴本来就是 True,center 轴的等价处理真正防的是"供体侧带映射/标记"造成的假 False。所以"不判 False"是对的,但**必须留 basis 痕迹**,否则一个 graph-equivalent 的判定会被读成"反应中心经验证"。

**(2) (b) 直答——三轴基本足以挡两类错误,但补三条:**

> - **对齐质量前置**:center 只在对齐满足注册的充分条件(覆盖阈值、唯一性)时判定;否则 unknown——"映射缺失伪造中心"的堵点是对齐充分性判据本身,须写成注册条件而非实现细节;
> - **strict 失败须分型**:strict_target_match=False 且 `tautomer_group_id` 相同 ⇒ 标 `diff=tautomer_only`;CN 相同且差为质子 ⇒ 标 `diff=charge_state`。**两者都不升格为 strict True**,只在展示上把"偏离预期"细化为"差异仅互变/质子化"——否则供体会被冤枉成"产物猜错",而判据一已决定这两类差异在事实轴上确实不同(诚实)、在评分轴上等价(公平);
> - **CN 的角色写死**:`legacy_cn_match` 只作旁证字段 `corroborating`,任何汇总/计数/门禁不得以 CN 计"一致数"——"CN 相同冒充结构一致"的堵点是 CN **永不进入计数器**,不只是不升格。

理由:"映射缺失伪造中心"已被"alignment resolved 才判"挡住,剩下的漏洞是**resolved 但不充分**(对称底物上任意取像),(1) 的一致像求值补的就是这个。

**(3) extra_changes 建议补一列**:变化原子列表之外,附逐原子 `Δ元素/Δ形式电荷` 摘要,与判据二的词汇表统一——让"多改了什么"以元素语言可读,而不是只有原子下标。

### 5.3 "程序上诚实但化学上误导"风险点

1. **`symmetric_equivalent` 裸 True = 机制背书**:图等价判不出前手性面专一,读成"中心经验证"是过度声称。
2. **互变/质子化差异显示为"偏离预期"**:供体被冤枉,而两侧轴(事实不同/评分等价)本可无歧义表达。
3. **resolved-but-arbitrary 对齐**:对称底物任取像 ⇒ 中心判定看似有据实则任意——同像一致求值是解。
4. **CN 计数**:只要 CN 进过一次"一致"计数器,两类错误之一必然复活;计数口径必须物理隔离。

---

## 6. 跨判据小结(只列必须在冻结前处置的项,按误杀/误导风险排序)

1. **电荷账对中和形输入强制 unknown**(2.2(1))——否则假通过,方向比 violated 更糟;
2. **violated 与 unknown 分理由码 + 缺口向量诊断子类**(3.2(2)、2.2(1))——防"书写惯例"被读成"化学不守恒"、防"有证据"被读成"无证据";
3. **展开去重键 = state_id,禁用 CN;质子化/互变边打 edge_kind**(1.2(4))——防对映体分支折叠与假转化边;
4. **判据二 reject 在决策表补 R2b 行**(3.2(1))——闭合映射缺口;
5. **optimum 不进 conflict、标签映射注册表化、键集合缺口以 `unassessed` scope 显式化**(4.2)——防假冲突与偏乐观相容;
6. **center 判定的 basis 字段与等价像一致求值**(5.2)——防机制背书与任意对齐;
7. **enhanced stereo 与分轴 fidelity**(1.2(2)(3))——防静默合并。

以上 7 项均为规则文本/理由码/展示字段级改动,不需要动 88 个测试所依赖的判据语义骨架;第 1、2 项建议在冻结前实现并各补一个夹具(中和形电荷账 ⇒ unknown;缺 H₂O 水解式 ⇒ violated_convention_suspect)。
