# pollutant_pathway_v1 化学判据冻结稿（ppv1-criteria-v1）

- **冻结版本**：ppv1-criteria-v1
- **冻结日期**：2026-10-08（Asia/Shanghai）
- **冻结范围**：判据一～五（S0–S2 化学判据，ppv1-*-8 契约族）+ 0d/0e S3 生产/
  恢复/调度消费契约（ppv1-search-6 / ppv1-store-9 / ppv1-profile-14 /
  search-limits-3 / format-feedback-1 / model-proposals-2 / ppv1-runflow-3 /
  ppv1-frozen-plan-1 登记面）。规则级表述，自包含，无任何金标/题面/封存
  逐题数据。
- **底本**：`docs/mimo_ppv1_chem_review_request.md`（v15，S3b 回修 r3 版；
  原文不回写、留作历史）。本冻结稿在其正文上应用 S3b-r3 Codex 终审
  （`docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_R3_2026-10-08.md`）§6 全部
  改字与判据五两句、§5 若干许可范围表述；逐项语义判定（全部仅文案精度、
  不改判据正文语义/范围/硬门）见冻结记录
  `docs/POLLUTANT_PATHWAY_CRITERIA_FREEZE_RECORD_V1_2026-10-08.md`。
- **冻结依据**：Codex S3b-r3 终审通过（S3 工程完成，P1=[]）+ R3 §6 改字
  清单与 §7.1 交接顺序第一条 + mimo v15 回应（"改字后无需新增化学评审
  轮次，除非更正过程中触碰判据一–五正文"）+ 用户 2026-10-08 拍板冻结。
- **冻结时锚定**：实际 HEAD `adf0287abef0c4803962fee0df0065d8e6f3793d`；
  正文所引源码行号均由冻结批次在该 HEAD 只读复核（复核清单见冻结记录
  §9）。
- **冻结后变更**：判据正文任何改动＝新版本（ppv1-criteria-v2 起），须按
  AGENTS.md mimo 三触发点与既有版本规范另行化学评审；工程实现偏离冻结
  判据属违约，须修实现或升判据版本，不得静默改判据。工程数字不当化学
  证据；工程完成与判据冻结分开声明（见冻结记录 §5）。

> **正文标记约定**：正文内 v9–v15 / 0c-v13/v14/v15 "落字"标记为历史评审
> 轮次的精度落字出处，保留作文本溯源（其中"复审 R3 §6①"等指 S3a 时代
> 评审轮次，与本次依据的 S3b-r3 Codex 终审不是同一轮）。〔冻结改字N〕
> 标记专指本冻结同步依据 R3 终审报告 §6 的第 N 项更正；〔冻结补写〕指
> 同报告 §6 末段/§5 及 mimo v15 已采纳落字建议的同步。各判据原"请评审"
> 段属评审请求、非判据正文，冻结稿不再保留（其承载的边界表述已并入
> 正文，见判据一第 2 条 preview 划界）。

---

## 0. 范围、定位与边界声明

本判据族的目标：可能降解路径与条件相容路径的**诚实表示**。unknown 不
升格；verified 不靠模型或调用方自报字符串；账平、物种同 CN 或一份正确
局部诊断不能代替整条声明的覆盖与追溯；停止不是化学终点；搜索记录/
合成图不是终点结论；旁证不叠加升格。

适用与不适用：判据一–五为化学判定口径（分子身份、参与物计量、admission
决策、条件相容、供体一致性诊断）；0d/0e 为把这些判据接进固定生产链与
调度/恢复的消费契约（契约不是新化学判据）。chemical endpoint 评估属
S4，本判据族不产出任何终点/矿化/解毒结论。搜索层不构造/不修改任何
化学对象。

对外数字必须带题域标签：本判据族的工程证据是合成规则级契约结果，不
代表 dev（B1 环境路径中间步骤）或 298（RHEA 通用酶学）科学性能，也不
是性能增长曲线。科学性能保持 pending。真实 provider 默认 off。

---

## 1. 判据一：分子身份（v12 文本，自包含）

**1. 身份键**：`state_id` = **化学 CX 事实子集**的规范化 canonical
CXSMILES 的稳定哈希。生成前移除非化学 CX 元数据：坐标（conformer）、
原子标签（atomLabel）、任意 atomProp（绘图/注释不改严格分子图身份）；
保留增强立体组（AND/OR/绝对）、自由基层、基串内的同位素/电荷/
立体。无组且无自由基层注解的分子输出与普通 canonical isomeric
SMILES 逐字相同（自由基分子带 `|^n:…|` 后缀是例外：身份层区分
自由基，保真轴为已登记缺口）。与 RDKit RegistrationHash 的一致性
限定在整组翻转/部分反转/排列/kekulé/映射号子集；plain≡`|a:…|`
同键是本仓归一设计，与 RegistrationHash 的 CANONICAL_SMILES 层
存在已登记分歧。

**2. 输入侧注册感知校验（原始串词法守卫）**：解析**之前**对原始
结构串逐项词法 —— RDKit 解析会静默丢弃 `|r|`、`|Ln:1|`、`|c:1|`、
`|wU:1.5|` 等未登记块（之后与裸输入同 state_id，输出侧守卫永远
看不到），故输入侧按真实 CX 类边界逐项分派：项序列由 ','/空格
分隔；登记类（atomProp/SgD=移除类；Sg=保留类；`$…$` 标签值块与
`(...)` 坐标块=移除类；增强立体与自由基层注解=保留类）各自耗尽
自己的字段（字段内逗号/空格是内容，**登记内容含空格放行**，如
`atomProp:0.note.hello world`）；未登记首头（含并列位置，如
`atomProp:0.n,r` 的 `r`）显式拒绝；DAT（SgD）值内逗号继续受
保护（DAT 剥离有适配器前提，只剥已登记 SgD 形态）。同一守卫覆盖
**全部原始 CX 入口**：工厂 build、strict_identity_of、判据五的
四个原始字符串字段、恢复入口与 audit 直接对象（2b）。
不产生身份或 verified 证据的诊断入口（池输入 preview 的 conservation
诊断、冻结执行器内部解析）按 C2 划界在守卫外，其结果**不得回流为
身份或核实证据**（preview 保持 pool_unchanged/diagnostic_only）；
preview 侧守卫调用关系未逐行核到（读码未覆盖，登记于冻结记录未核
事项清单）。〔冻结补写：该划界原在 v15 请评审段，为边界规则正文，
非新增门。〕
**v12 落字（真实 token）**：登记保留的立体/自由基层注解头按**实际
CX token** 写 —— `a:`（绝对/ABS）、`o<N>:`与`&<N>:`（相对增强组）、
`^<N>:`（自由基层）及已登记 Sg 类；**and/or/rad 是英文类名，不是
输入字面**（RDKit 2026.03.6 实际写出 ABS/AND/OR/自由基并保持严格
身份往返——〔冻结改字⑥：工具行为，已由 Codex R3 复审独立执行证成：
2026-10-08 本机 RDKit 2026.03.6 五正控 + and/or/rad 三别名×工厂/
strict 两入口六负控；仅证本机该版本，非跨版本兼容或酶学机制认证；
mimo v15 该句为只读推断、其原回应不执行，原文不改〕；以三字面别名
作为输入串传入均按 unregistered_cx_class 拒；词法正则
`_CX_STEREO_ITEM_HEAD_RE` 实为 `(a|o\d+|&\d+|\^\d+):`，
chemstate.py:266）。"接受/拒绝"只是输入表示层契约结果，**不构成
样品认证**（见 2b 的 r 不反推条款）。

**3. 混合并列 ABS 归一**：ABS（绝对立体）注解剥离为令牌级语法
解析（`a:1,&1:3` ≡ `|&1:3|`、`^1:0,a:1` ≡ `|^1:0|`；段级正则对
逗号并列形态匹配不上会造成同一立体事实分裂成两个 state_id——
已修复）。plain 与 ABS 归一后的分子同键。

**4. 公开表示往返闭合**：`smiles_isomeric` = 身份键同串（往返
无损）；`structure_smiles_raw` 保留原始串与 structure_origin/
source_refs/分轴 representation_fidelity 一起存出现记录（appearance），
语义块（states 行）只存严格分子事实 —— representation_fidelity
不是语义成分，同图不同来源保真度共存、互不升级/降级；需要某来源
保真度必须按出现取。

**2b. 恢复/直接对象首消费同源验证（v8 新增，v9 落字三处，v11
再落一处，v12 更正一处）**：恢复入口（`ChemicalState.from_dict`）与
audit 直接 states 对象在首次授信前共用与公共 writer 同源的纯状态
验证（`validate_state_object`）：(i) 版本门 + fidelity 分轴契约 +
structure_origin 合法；(ii) 结构态：raw 非空且过判据一第 2 条
同一输入守卫（未登记项 ⇒ 拒，不静默清洗信息再授 full）；(iii)
raw 重推严格身份 == smiles_isomeric（同图异拼写如 OCC 接受；跨
分子如 H2 状态挂 CC=O 拒）；(iv) smiles_isomeric 须为身份键规范形，
state_id/formal_charge/cn_identity/立体/同位素状态按工厂同源重推导
一致；(v) CN-only 走专用命名空间身份（cs(cn-only,cn)）+ 未知
事实契约（不重推导结构）。v9 三处落字保持（同源验证非独立双算；
`r` 标记存在与含义均不采纳也不反驳；canonical+r 的上层错误名
语义须读内因）。**v12 落字（更正 v11 括注，外层-内因两维）**：
同一入口下 canonical+r 与真坏 canonical 两种内因的外层**同为
ChemicalStateError 的不同 kind**，按 `detail.reason.kind` 区分
（unregistered_cx_class / unparseable_smiles）—— v11 所写"工厂
未登记 vs 真解析是不同异常类"的括注**错误**，不得沿用；**跨入口**
的外层才确不同（恢复入口外层 ChemicalStateError、公共 writer 外层
Ppv1StateContractError）。不能把所有外层写成同一类，也不能把同入口
内因写成不同异常类；"同源确定性重推导拒篡改"是同一算法的复算
（不是第二套独立证明）；v10 ②③的精度句保持。
**冻结补写（writer raw 机读码，防跨入口串味）**：writer 侧 raw
失败机读码为 `raw_structure_unparseable`（store.py:632，不带
reason 内因），与恢复入口的 `raw_structure_rejected`（带内因）
不同名——两个 kind 不是同一个，不得互串。
- 自报 formal_charge/stereo/isotope 与结构重推导一致的声明，
  限定"经首消费验证的入口"（2b 覆盖的 from_dict/直接对象/工厂/
  writer），不是所有裸 dataclass 对象的无条件性质。

---

## 2. 判据二：参与物计量与元素/电荷核算（v12 文本，自包含；
v12 落字两处）

- **全氢账**：元素核算按全氢（分子式含 H）；D/T 合并计 H（已
  登记披露，不区分同位素）；**自由基电子不计入元素/电荷账**（数值
  账"平"在这两类有系统盲区，不得读成质量/电子守恒已核）。
- **系数契约（v12 落字）**：非法表示系数（零/负/非有限/bool）在
  **构造/提交边界拒绝**；coefficient_binding_mismatch **属覆盖轴
  违例**（按判据三处理：partial_unchecked_transformation/中心
  unknown，**最终处置依其他轴与决策表首中规则，不能固定写成自动
  reject/R2b，也不能固定写成 R5**）；〔冻结补写（实测指向，行为
  与原则并钉）：当前实现下该 kind ⇒ binding_ok=False ⇒ 中心记
  unknown、最终处置走 R5（mimo v15 实读核到）；如未来扩表须升
  版本。〕**不可虚称"入口在比对系数与结构重推导值"** —— 系数
  绑定核的是声明与补全/覆盖核算的对应，不是对结构重推导数值的
  比对；caller 侧须如实报告映射、不吞错改写处置；R2b（表示契约
  违反）的判定还须 caller 映射 detail（缺映射不当化学已核，见
  判据三 v12 落字）。
- **完整性 unknown**：未知系数 ⇒ coverage unknown_coefficients
  （中心结论 unknown，不猜数值）；full_known 不成立时**元素账与
  电荷账同样直接记 unknown**（不只是 coverage 的
  unknown_coefficients）—— verified 只覆盖**调用方声明清单**的
  数值闭合，两侧对称漏写参与物在本轴不可见。〔冻结补写：0c-v13.3
  落字并入正文。〕
- **known_absent 轴归属（v12 落字；冻结稿同步为实现真实值）**：
  known_absent 类语义**属条件评估轴，不是元素账的判据**；实体缺席
  与非物种字符串的**同值缺席** ⇒ conflict（reason 码：
  `required_entity_known_absent`，path_context.py:732；
  `required_value_known_absent`，path_context.py:828）；非物种字符
  串**异值** known_absent 或未列出 ⇒ unknown（
  `other_value_known_absent_not_determining`，path_context.py:833）；
  **数值/区间缺席 ⇒ unknown（`numeric_absence_semantics_undefined`，
  path_context.py:822，不跨值域泛化物种字符串的规则）**。
- **电荷轴前提**：formal_charge 判定以经首消费验证的结构重推导
  值为前提（2b 后不可被直传对象伪造）；电荷与元素分轴，不互相
  抵消解释。
- **结构化 omission_pattern_matches**：缺参与物按模式匹配结构化
  报告（不静默）；`omission_pattern_matches` 只说"差额与某模式
  数值相符"，不证明实际缺该物质、不含电子/质子计量；R5d 触发集
  合显式限定 {element_accounting, formal_charge_accounting}，其
  他 violated 走 R5v 独立码（防新增检查静默挂进"声明账不一致"）。
- **恒等 ≠ 落点**：净反应两侧同分子（恒等变换）不因元素/电荷平
  而获得任何"转化已核实"结论；数值配平只证明组成闭合，不证明
  转化身份、机理或未覆盖参与物初始图的键变化（与判据三的 full
  两根据互锁）。

---

## 3. 判据三：admission 决策表与中心证据契约（v12 文本，自包含；
有序，首中即决）

决策表（评估顺序固定，首中即决）：

```
R1  structure_unparseable      → reject  (实际输入语法非法;CN-only 等
    合法缺结构走 unknown,悬空引用走 R1b,不进本行)
R1b participant_state_missing  → reject  (参与物 state 引用悬空 = 账本/
    引用完整性问题,理由码保留,不压平成"结构不可解析")
R2  active_gate_rejected       → reject  (活动门禁显式拒绝;仅 reject_gates
    名单内 —— 不暗改冻结判据,新门禁须独立评审)
R2p per_product_gate_rejected  → reject(全部共同产物被拒)/
    retain_conditional(部分被拒:被拒产物保留拒因、不可展开,不删除
    被拒共同产物凑合法事件)
R2b contract_violated_representation → reject (表示契约违反:零/负/
    非有限系数、酶计入净计量、结构性违约;理由码 representation =
    非化学)
R3  current_scenario_conflict  → defer   (有来源 essential 条件与当前
    场景已知事实冲突;当前场景不展开——动作结算为 admission_deferred、
    假设留痕;与 0e.6 的持久 blocked 行不是同一状态:deferred 可激活、
    blocked 不可执行)
R4  budget_or_wait             → defer   (独立原因)
R5d declared_account_violated  → retain_conditional(触发集合显式限定
    {element_accounting, formal_charge_accounting};账不平只证明声明
    内部矛盾,不证明反应不存在;绝不进入 R6)
R5v declared_violated_other    → retain_conditional(其他检查 violated
    的独立码,如确定性 checker 的中心偏离)
R5c required_check_coverage_missing → retain_conditional(必需适用检查
    未被执行/不在审计内:窄 audit_scope 只能作诊断,R6 覆盖核算
    不通过)
R5  unknown_checks_present     → retain_conditional(检查 unknown/因缺
    输入未执行;继承未解决依赖)
R6  default_all_verified       → expand(全部必需适用检查覆盖且
    verified,无 unknown/violated/缺输入未执行;语义 NA 白名单除外)
R7  no_applicable_checks       → retain_conditional(无适用检查:保守
    保留,不冒充核实)
```

〔冻结改字②：R3 行 v15 原文写"action=blocked"，与实现不符——实际
结算为 `OUTCOME_KIND_ADMISSION_DEFERRED` + `put_hypothesis` 留痕
（runflow.py:1122-1133，本冻结批次已核），blocked 行写点仅
search.py:1145（record_blocked_hypothesis）与 :1213（恢复隔离）；
audit.py:1528-1529 docstring 与 :1757 注释仍含旧"(blocked)"表述，
属冻结前登记的 P2 源码文本同步项（不改行为，见冻结记录），以本
冻结稿表述为准。R3 触发条件与处置（defer、不称化学不可能）不变。〕

任何 unknown 不自动 reject；新增"诊断转拒绝"必须扩表并升版本；
chemical_reproposal 首版 off。实现锚点：`decide_admission` 于
audit.py:1643 起，评估顺序固定、首中即决逐行 return（本冻结批次
已核）。R1 为防御行——坏结构通常在首消费守卫即异常逃逸，不落
任何 R 行；R2b 表示契约违反由调用方传入 contract_violation 触发
（不传则该分支不可达）。〔冻结补写：0c-v13.5 落字并入正文。〕

类型契约/内部重算：center_evidence 的判定字段由**内部重算**（不采
信自报签名/字符串）产生；无 proof_record ⇒ unknown（不猜）；复算
比对含 center_match_basis 披露；proof_record 载荷不可变 + 入口身份
复算（改前提不换 ID ⇒ 拒）。**v11 落字（"复用"分写）**："跨假设
复用 proof ⇒ 拒"按实际行为分写：跨假设**未绑定** proof 通常产出
**中心 unknown**；**篡改自报与复算不一致**抛契约异常、**本次无
成功 admission**（异常逃逸，不落任何 R 行）—— 两种情形不混成
同一种"拒"。audit.scope/proof_scope+basis 分轴披露：缺 proof/映射/
参与物覆盖时 unknown/partial（center_checker_scope_unknown 等），
字段存在不等于适用。**v12 落字（③④⑤）**：
- **R2b caller 映射依赖（③）**：R2b（表示契约违反）的最终判定依赖
  caller 侧如实提供映射 detail —— **缺映射不得当成化学已核**；
  caller 映射义务由 S3b 生产链承担（0d.2/0c-v13.7 落字），不在本
  判据预先虚称闭合；
- **中心 partial 的表述（④）**：中心结论层面**没有"裸 partial"**
  —— 未满足核（center）按**映射理由码/中心 unknown** 表述
  （center_checker_scope_unknown 等），与覆盖轴枚举
  （partial_unchecked_transformation）分开，不得把覆盖枚举当作中心
  结论名词用；四个原始字符串守卫（判据五）限定**执行成功路径的
  解析之前**；失败早退未解析、不消费其任何轴；None 非通过；
- **入口划界（⑤）**：公共 writer 清单可补；**搜索层的结构权威依
  公共 writer 重放，store.verify_event_attachment_content（store.py:
  1988）只核附随投影/计划内容，不单独证明 state 身份**（state 身份
  的事实源仍是 states/appearance 行与首消费同源验证）；
  substrate_profile 在 S0–S2 时点无生产 caller；**S3b 起由驱动在
  决定层调用（runflow.py:809）并写持久 artifact（runflow.py:812-814），
  为只读组装**，其输出不构成身份/核实证据，档案输出前置验证仍划
  界为 P2，不重开旧 S0–S2 门。〔冻结改字①：v15 原文"无生产
  caller"为 S0–S2 时点的过时事实，与 0e.5"空池仍组装底物档案"
  自相矛盾；化学边界（不构成身份/核实证据、P2、不重开门）三要素
  逐字保留。〕
- **strict 轴判定范围（⑦c，冻结补写）**：strict 目标偏离 ⇒ 中心
  **violated**（决策表走 R5v；audit.py:1188-1203，strict None ⇒
  unknown，audit.py:1204-1213，本冻结批次已核）——该判定在**前置
  绑定/覆盖核验通过后的中心证据分段内**成立（绑定失配先行落中心
  unknown、依首中即决），**不能无条件全称**；violated 强于 unknown，
  不得弱读成 unknown 错走 R5。

**覆盖核算与补全许可（composition_only_hydrogen_equivalents）**：
绑定核验按复算的底物/产物身份做整组覆盖；产物覆盖判定输出
`product_coverage` ∈ {full, partial_unchecked_transformation,
unknown_coefficients} 与逐条 `coverage_violations`（kind 如
coefficient_binding_mismatch[系数与声明不符]、completion_surplus/
deficit[补全规则数值不符]、completion_license_unregistered_identity
[未覆盖参与物严格结构身份未登记许可]）。completion_surplus/deficit
的差额核算 = 未覆盖参与物的元素和与结构重推导的 **λ_s×Δ 对账**
（源式 audit.py:973-980：产物侧 973-976、反应物侧 977-980，本冻结
批次已核〔冻结改字⑤：v15 作"973-979 一带"〕）；coefficient_
binding_mismatch 只比声明系数绑定——两者分写，不互相冒充。
**覆盖 full 的两个互不替代根据**：① 无未覆盖参与物；② 注册补全
规则（H2/[H] 按 2[H] 氢当量）数值精确相等且未覆盖参与物身份全部
在登记许可内。**二者都只解除覆盖轴** —— 补全（无论是否持许可）
只证明组成闭合，不证明转化身份、机理或共底物初始图的键变化已
核实；身份归 strict 轴、元素/电荷归判据二、转化核实归证据门。
系数绑定核对与补全数值对账分开：声明清单账平不认证漏项/电子/
质子实际计量。

**v9 落字两处 + v10 精度更正一处 + v11 落字一处**：
- **scope 归属（v9，⑤已落地）**：当前代码 `completion_license_
  scope` 字面**不含**"不区分键断裂方式与电子去向"句；该表述归属
  **许可定义/本规则正文**（composition-only 许可不区分该参与物的
  键断裂方式与电子去向，是许可的语义边界）。字段字面未改、无版本
  身份影响；本判据不要求改代码 scope 字面。
- **恒入 ≠ 已适用（v9；v11 精度补写；冻结改字④）**：**凡完成覆盖
  判定的 center detail 必带** `completion_license`/`completion_
  license_scope`（full/partial 均携带；写入点 audit.py:1009-1013，
  本冻结批次已核）；**unknown_coefficients/unverifiable 的早退例外
  不携带**（早退发生在覆盖判定之前；早退点 audit.py:889-897，本
  冻结批次已核）；字段存在不等于本结论使用了补全许可；判定"本
  结论依据含许可补全"须同时看 **product_coverage=full、
  uncovered_reactant_refs/uncovered_product_refs 非空、
  unlicensed_uncovered_identities 为空** 三条件组合；license_applied
  标志/顶层别名/同屏渲染列属后续 API/展示层（P2，不作判据门）。
  〔冻结改字④：v15 原句"恒入 center detail,full/partial 完成分支
  携带…早退例外不携带"两限定均已具备，改字仅把限定语序前置、
  防止快速阅读把"恒入"读成所有 detail 恒带；携带范围与例外逐字
  保留。〕
- **v10 精度更正（mimo v9 回应 ⑥ 的判负口径，保持）**：mimo 曾
  概括"partial = 许可本身判负"—— 不精确，不得照抄：(a) 实际枚举
  是 `partial_unchecked_transformation`（存在额外未核实转化/未
  核实结构贡献），不是裸 "partial"；(b) uncovered+partial 组合下
  `coverage_violations` 可能是 `coefficient_binding_mismatch`（系数
  与声明不符）或补全数值不符，与许可是否登记无关 —— **不能一律称
  "许可本身判负"**，须读 coverage_violations 的逐条 kind；(c)
  `unknown_coefficients` 等早退（coverage unknown）发生在覆盖判定
  之前，**尚未使用许可**，不得称"已使用许可后判负"；(d) 许可未
  登记身份的 case（completion_license_unregistered_identity）才直接
  关联"数值配平不证明未登记多原子共底物初始图的结构贡献"这句
  规则正文。
- **v11 落字（恒入/复用分写）**：见上文类型契约段 —— full/partial
  完成分支携带 license/scope、早退例外、跨假设未绑定 proof 与篡改
  复算不一致两种情形分写，不再用单一"拒"概括。

---

## 4. 判据四：条件相容聚合（v12 文本，自包含；v11 落字三处保持，
v12 补一处轴归属）

- **快照一致性**：路径上下文快照由已验证父对象派生，派生先验
  validate 父对象；快照的 covered_requirement_signatures 与已记录
  的 per_requirement 评估行**双向对应**（签名↔行双向：删行/改
  签名都拒）。**v11 落字（孤儿方向，更正 v10 方向）**：两个方向
  的处置分写 —— **已有必要要求绑定旧作用域但无按签名快照 ⇒
  unknown**（证据不足，不猜；kind：requirement_binding_not_in_
  route_snapshot）；**评估行/签名无对应要求或集合不一致 ⇒
  `context_snapshot_inconsistent` 拒**（引用完整性/一致性失败，
  不是 unknown；v10 把后一种写成 unknown 且方向写反，以本版为准）。
- **内容身份**：PathContext 内容身份同源重算；**两种不可变机制
  分写（v9 落字）**：Requirement/ConditionFact 由 frozen（嵌套冻结）
  强制；PathContext 本体**非 frozen**，其不可变性由消费前 validate
  的内容身份同源重算兜底（就地改语义字段保留原 context_id ⇒
  `context_content_identity_mismatch` 拒）。不得把两种机制写成同一
  类不可变；任何派生/评估/审核入口消费前必须先 validate（绕过
  validate 直读字段属违约）。**v11 落字（入口限定）**：已**强制**
  validate 的入口 = 恢复/from_dict、derive 的父对象、audit 直接
  对象；`assess_conditions`/`assess_candidate_conditions`/
  `route_assessment` 自身**没有**该调用，**需上游纪律**（生产
  caller 经 `load_context→from_dict` 内容身份核验接真实守卫，不以
  上游纪律替代入口强制）。
- **重建半边（v11 落字）**：合法**新内容重建**的语义 context 使用
  **新 context_id** 并保留 `parent_context_ref` 链（旧引用不复用）
  —— 新内容重建**不是篡改**，不得被 content_identity 判据拒绝；
  篡改是"旧 ID + 新内容"的组合（见上文 mismatch 拒）。
- **三分与矛盾**：条件评估三分为 satisfied/conflict/unknown；已知
  事实与要求冲突为**单向矛盾**（conflict 只阻止当前场景，不反推
  全局）。**v12 落字（known_absent 轴归属；冻结稿同步为实现真实
  值）**：known_absent 类缺席语义**属本条件评估轴，不是元素账
  判据** —— 实体缺席/非物种字符串同值 ⇒ conflict
  （`required_entity_known_absent`，path_context.py:732；
  `required_value_known_absent`，path_context.py:828）；非物种字符
  串异值 known_absent 或未列出 ⇒ unknown
  （`other_value_known_absent_not_determining`，path_context.py:833）；
  数值/区间缺席 ⇒ unknown（`numeric_absence_semantics_undefined`，
  path_context.py:822，不跨值域泛化物种字符串规则；该句与判据二
  v12 落字同源，两处一致表述）。
- **场景评估口径**：文献观察环境、矩阵"污水"标签、工具隐式
  O2/H2O、transformation_class 标签都**不能**构造当前条件事实；
  请求 condition_compatible 不是已相容；空要求/未知覆盖不自动
  compatible（相容判断需实际评估）。satisfied/conflict 是**给定
  事实集的相容性结论，不核事实真实性**（不认证环境事实已被实验
  证实）。〔冻结补写：0c-v13.6 落字并入正文。〕
- **行↔签名对应的契约前提**：绑定字段一经冻结不得后改；变更须
  走新评估/新快照（将来引入要求可变性，旧快照整体拒绝是故意
  fail-closed，不当 bug 修）。

---

## 5. 判据五：供体一致性诊断（v12 文本，自包含）

- **判定基础 = 实际净变化集**：供体编辑一致性以键 diff ∪ 电荷/
  立体/同位素变化集的实际净变化判定（含 bond_stereo_change 与
  键级立体入变化集；非四面体公开列项按标签类型分开），不采信
  声明的"编辑列表"与实际不一致的自报。**v11 落字**：区域净变化
  不认证**供体模板/机制**（净变化判定是表示层契约，不是机理
  证明）；**图等价不是酶识别**；legacy_cn_match 仅**旁证**（不是
  反应身份判定）。**旁证不叠加升格**——legacy CN、图等价等多份
  旁证不能累计成"多证合一"的强证据。〔冻结补写：R3 §6 末段采纳
  mimo v15 建议。〕
- **奇偶构型比较与非四面体 unsupported**：四面体手性按奇偶
  （parity）构型比较；非四面体立体（_at 等）公开列
  unsupported（不冒充核实也不静默拒）；E/Z 与非四面体轴分开。
- **联合映射三类支持范围**：原子映射支持范围（完全/部分/缺失）
  与歧义映射分列；缺/歧义映射 ⇒ 中心 unknown（partial），不猜
  对应。
- **中心属性披露/strict 同源**：诊断输出的中心属性（参与物/键/
  电荷/立体）按 proof_scope 分轴披露；strict 目标比较与
  strict_identity_of 同源（与身份键同一推导，不是第二套）。strict
  False ⇒ 中心 violated 的判定范围见判据三（前置绑定/覆盖先行分支
  内，不能无条件全称）。
- **证据载荷内嵌**：check 结果（含 proof_record）内嵌进审核证据
  载荷（不可变、入口身份复算）；跨假设未绑定 proof ⇒ 中心
  unknown；篡改自报与复算不一致 ⇒ 契约异常（本次无成功
  admission；见判据三 v11 落字）。
- **四个原始字符串入口与工厂同源守卫**：供体诊断的四个原始结构
  串字段与工厂共用判据一第 2 条输入守卫（未登记 CX 项 ⇒ 契约
  拒绝；守卫在执行成功路径解析之前，audit 侧供体诊断四个原始串
  于解析前统一过守卫）。
- **声明–执行净效应对账 + 镜像终态归一**：声明编辑与实际执行
  对账（镜像活 ID 表 + 前置复核）；终态序列化与冻结执行器对齐。
- **8b 拒绝与失败早退（v9 落字，精度保持；v12 补一处；冻结补写
  两句）**：失败诊断是**三个**判定字段 reaction_center_match/
  strict_target_match/legacy_cn_match 均为 None（实现处
  audit.py:2553-2562）、`diagnostic.center_evidence={}`；
  **converter 仍返回版本/来源元数据与 center_match=None**（兼容
  分支 audit.py:2983-2993；本冻结批次已核两处行号）（不是
  "四轴 None"，也不是"converter 整个 evidence 为空"）。None=未
  评估，**不等于通过**（三个 None 不是通过；legacy_cn_match 单
  True 也不是任何 R 行的通过依据）；`execution_ok=False` 早退
  路径不解析三字段亦不消费其任何轴，无 verified 泄漏面。拒绝为
  契约性拒绝 ⇒ 本次诊断/审核不产生任何轴结论与 disposition；
  调用方不得吞异常后按 retain/verified/any-R 行记录（异常≠处置
  行）。两处表述边界：拒绝原始 `r` 不构成"已证实实验精确消旋"；
  裸指定 SMILES 只声明表示事实，不称实验纯品/对映纯；strict=
  True = 同一化学身份，不是同一样品/同一立体纯度。
  **v12 落字（失败 diagnostic 与下游 audit 各轴分开）**：失败
  diagnostic 的三个 None/`center_evidence={}` **不等于**下游 audit
  所有轴/所有 R 行都不存在 —— converter 仍返回版本/来源元数据与
  center_match=None，缺 scope/proof 进 audit 中心 UNKNOWN；**同一次
  audit 仍可以给其他轴 verified 并由决策表处置**（中心 unknown 与
  其他轴的 verified 不互斥，按决策表首中规则合成整体处置）；不得
  把"诊断失败"扩大成"整个 audit 无结论"。同源重放/输入守卫也
  **不证明来源真实性、历史执行、酶识别或供体机制**。四个原始
  字符串守卫限定**执行成功路径的解析之前**（失败早退未解析）。
  **冻结补写（R3 §6 判据五两句）**：① **standalone audit 被调用时
  可分轴判定** —— audit_hypothesis 被独立调用（非固定生产链短路
  路径）时，中心 unknown 与其他轴 verified 按上段不互斥规则分轴
  合成；② **固定生产链中，工具 execution_ok=False 在 audit 之前
  短路**（production.py:399-404：**工具执行失败**短路 →
  method_failed，非 AuditContractError 短路；本冻结批次已核），
  **零 audit/零 event** —— 8b 的三个 None 与 converter 元数据描述
  的是诊断/audit 层行为（含 standalone 调用路径），固定生产链的
  失败执行不进入 audit（与 0d.3 一致）。失败诊断下**中心不可
  verified、事件不得凭它提交**（与 0d.1"声明酸/实际醛仍带声明
  结构提交但中心不可 verified"交叉引用）。
- **8d caller 义务（义务不变；闭合状态冻结稿同步）**：S3 新
  caller 必须承担"让 AuditContractError 逃逸并中止本次 admission
  计算/提交"的义务，不得吞异常继续。**该义务已由 S3b 生产链
  交付闭合**（0d.2：驱动窄捕获 runflow.py:1091-1102 结算
  contract_aborted、attempt 落 failed，零事件/零提交/零完成；
  Codex R3 复审以真实 caller 坏 proof 经真工具/audit 抛
  AuditContractError、窄捕获 contract_aborted/failed 落账、零 event
  互证）。静态无宽捕获仍**不是任意第三方 caller 的动态安全
  证书**（通用动态闭合未认证）；ChemicalStateError/
  HypothesisContractError/ConditionContractError 三类契约异常当前
  原样逃逸至 run 进程级终止（见 0d.2 披露），不以"AuditContractError
  闭合"外推全部异常都有失败结算。〔冻结补写：v15 原文 8d 状态
  为"S3a/r4 未新增生产 caller、尚未闭合"，系 S3a 时点事实；义务
  条款逐字保留，闭合状态按 v15 自身 0d.2 落字与 R3 执行证据同步。〕

---

## 6. 0d. S3b 生产链与调度消费契约（v15 文本，冻结稿同步 r3 行号；
全部为消费/调度契约，不是新化学判据）

S3b 把 S0–S2/S3a 的判据接进**固定生产调用链与调度**。

1. **固定调用链与顺序**：`AtomTool 真实执行输出（render+execute_
   edits）→ check_edit_against_donor（供体诊断，含 proof_record）
   → center_evidence_from_donor_diagnostic（converter，不另手造
   verified 中心结论）→ audit_hypothesis（首消费守卫）→
   decide_admission → build/submit_event（公共 writer）→
   complete_action（搜索记账）`。实现锚点（本冻结批次已核）：
   production.py:396 执行 → :406 audit → :409 decide → :417 产物
   refs → :456 submit → :465 complete。合成合法编辑必须实际调用
   冻结 AtomTool（渲染、映射/编辑执行及现有约束），保存真实执行
   前后/atom_id_map/edits/donor/alignment/expectation/result；对工具
   已确定的产品只能引用（状态身份由结构内容派生），不暗改结构。
   **产品来源精度（v14 落字）**：事件产物身份 = **冻结池声明的
   product_smiles 经内容派生的 state_id**（产物 refs 来自
   `prepared["product_states"]`，production.py:417）；工具真实执行
   输出是核验轴输入（donor/center 诊断），**不改写产物身份**；
   两者不一致经中心轴落 unknown/violated 按决策表处置（声明酸/
   实际醛时事件仍带声明结构提交、中心不可 verified）。
2. **生产 caller 的异常义务（R8 P2 ⑧ 落字，S3 首个生产 caller）**：
   AuditContractError 不得吞成 verified/R6/成功提交 —— 生产链在
   audit+admission 之后才写事件，契约异常上抛 ⇒ 零事件/零提交/零
   完成；调用方（runflow 驱动）只**窄捕获**以记录方法失败
   （contract_aborted，attempt 落 failed）并调度独立备选，宽捕获
   （except Exception）下同样零写入，无"捕获后成功"路径。**窄捕获
   r3 行号：runflow.py:1091-1102**（`except AuditContractError`
   :1091、contract_aborted 落账 :1096-1101、return :1102；本冻结
   批次已核）。〔冻结改字③：r2 标签 955-972 保留为历史，955-972
   现为 `_derive_branch_context`/`_model_proposals` 区间（r3 源码
   :949-1050），勿按旧号取证。〕**闭合范围如实收窄（v14 落字）**：
   已闭合范围 = AuditContractError（驱动窄捕获 ⇒ 结构化失败结算：
   artifact + action 以 contract_aborted 结算、attempt failed，事件
   零提交）；失败结算与"再调度独立备选"须分开读——**已排队的其余
   独立条目继续执行，deferred 不因本次 aborted 自动激活**（激活
   仍须显式指令/activate_deferred）；真实驱动**不存在**宽捕获
   （宽捕获仅负控测试语境）；ChemicalStateError/
   HypothesisContractError/ConditionContractError 三类契约异常当前
   **原样逃逸至 run 进程级终止**（零事件写入成立、无 stop report/
   run_error 披露、action 保持 claimed）—— 如实登记为已披露边界，
   不以"AuditContractError 闭合"外推全部异常都有失败结算。
3. **三个 None 与缺 proof 的语义（与判据五 8b 一致，现为生产链
   实际行为）**：工具 execution_ok=False ⇒ 诊断三判定字段
   （reaction_center_match/strict_target_match/legacy_cn_match）
   全 None、diagnostic.center_evidence 空字典，converter 仍返回
   版本/来源元数据与 center_match=None（None = 未评估，不是
   通过）；记方法失败（method_failed），不伪装成功工具结果。
   **该短路在固定生产链发生于 audit 之前（production.py:399-404，
   工具执行失败短路；零 audit/零 event）**；standalone audit 调用
   的分轴判定见判据五 8b 冻结补写。〔冻结补写：R3 §6 判据五两句
   的 0d 侧落字。〕缺证据/映射的 None 或空 payload 不是契约异常
   也不是执行失败：audit 保留 unknown/partial，admission 按既有
   R5 有界探索，不授 verified。
4. **中心证据分段负控语义**（与判据三一致）：缺/歧义映射 ⇒ 中心
   unknown；strict 目标偏离 ⇒ 中心 **violated**（强于 unknown；
   决策表走 R5v，不弱读成 unknown 错走 R5；audit.py:1188-1203；
   strict None ⇒ unknown，audit.py:1204-1213，本冻结批次已核）——
   violated 判定在前置绑定/覆盖核验通过后的中心证据分段内成立，
   不能无条件全称（判据三 ⑦c 落字）；proof 更改（自报字段与
   proof_record 复算不一致）⇒ AuditContractError 结构化拒；跨假设
   复用 ⇒ 绑定不匹配中心 unknown（注册名+True 不构成核实）；
   复杂共底物不能只凭配平升级（completion_license 组成型氢当量
   边界由 audit 既有判据保留，production 不另造许可）。
5. **队列与两类 deferred**：schedule_hypotheses 产 selected/
   deferred/blocked+原因（池 digest/排序/截断可重放；池成员/档位/
   原顺序不被筛选结果改写）；备选反应 deferred（alternative_
   reaction_deferred，对象=假设 ID）与共同产物 deferred（
   coproduct_deferred，对象=事件产物 state_ref）**分别有类型、
   对象、触发条件/未展开原因**；激活（activate_deferred）幂等、
   trigger 与冻结记录一致、expected_parent_revision 匹配（旧
   revision ⇒ unchanged stale）、预算不足留独立未展开原因不改
   状态、不重复安排同 action。无新信息不无限重开（持久上限）；
   **持久上限来源（v14 落字）**：持久计数来源 = claim 事务内的
   预约行（max_reopens_per_hypothesis 与 max_attempts_per_
   hypothesis 双重约束，预约 ID 确定性派生 ⇒ 重放/恢复同 ID 复用
   不重复扣）与 already_expanded/done 幂等键（同身份 done ⇒ 不再
   安排）；blocked 计数不是防循环证书。**S3b-r2 起深度阻断对象以
   blocked 行持久化（见 0e.6），blocked 不可执行（claim/激活均
   拒）**；deferred（可激活）与 blocked（不可执行）在对外报告与
   调度语义中分开，不得合并展示；首选下游无候选记
   unresolved_continuation（不反证上游；按稳定次序继续可用备
   选）；完整事件保存全部已知参与物/产物，报告 K/展开宽度或预算
   不足不删事件事实。
6. **条件依赖与场景转换进调度**：子路径继承父事实/要求/假设/
   依赖，分支互不污染（带自身要求/依赖的假设经 derive_child_
   context 派生专属上下文）；环境 essential conflict 阻当前场景
   展开（假设保留留痕，不称化学不可能）；共底物循环有启动供应/
   再生支持不自动阻断，缺支持标 unresolved_initial_supply（按
   显式、版本化策略处理，不称化学不可能）；场景转换只由用户/
   来源明确支持（source_ref 必需；不从文献观察/矩阵"污水"/工具
   隐式 O2/H2O/transformation_class 标签造当前条件），独立
   action/预算/记录，仅改变后续阶段（旧边评估冻结于
   phase_history，不重写）。
7. **模型假设协议（proposals[]）**：每项一条独立反应假设（内部
   共同产物集合与 participants/来源/条件/依赖按既有契约）；
   rank_hypotheses 引稳定 ID，**模型选择不升成 recorded**；novel
   有界 proposal_context（reference_hypothesis_ids/output_origin
   明示，不伪造来源）—— **novel 池外提案必须另携带 reaction_spec
   完整反应内容（与冻结池条目同形状的假设载荷；缺 ⇒ json_field
   格式错误可进有界反馈；无足够内容不授有效 hypothesis、不伪造
   内容），并由驱动构造独立假设消费（见 0e.5）**；空列表/弃权
   合法（脚本响应耗尽 = 合法弃权，不猜内容）。**有界格式反馈**
   （独立策略 ppv1-format-feedback-1，默认 0 轮、范围 0-4、计数
   单位=同任务 JSON 格式修复轮数，**不是 hypothesis 语义
   attempt**、非 S2 十搜索上限旧字段）：只有 JSON 字段/类型/
   允许 ID/语法契约错误可进反馈；结构无法解析记结构失败，不能
   以格式反馈改分子再试到通过；**默认 0 轮 = 可反馈错误首次即
   结构失败（model_structure_failure，run 如实停止）；反馈机制
   仅在配置 1–4 轮时生效；反馈轮的 scripted 重试不发网络，真实
   provider 的反馈重试属付费路径，默认 off/0 下不可达**；
   chemical_reposal 首版 off（化学重提案数 0/路径 unsupported 如实
   披露）。模型不直接写 SQLite/frontier/条件事实/策略；真实
   provider 默认 off、max_real_model_requests=0，传入模型对象不
   自动启用/补预算；scripted/fake 恒 network 0。
8. **PPV1 独立 runner 分流**：公开 start_run/resume_run 按 profile
   分流到独立执行/存储（**分流代码在 `workflow/runner.py:214-228/
   305-320`（实调 start_ppv1_run runner.py:218-219、
   resume_ppv1_run :316-317，本冻结批次已核）；runflow 同区间
   （:209-223）实为 `_complete_action` 尾部/冻结计划锚定段
   （:226 注释、:274-390），**非分流代码，勿引**；reconcile 实为
   runflow.py:500-558、drive :629 起〔冻结改字③：mimo v13 误写
   runflow.py:214-223/315-319 且 v15 沿用"runflow 同区间是
   reconcile/drive"的过时表述，r3 源码为准〕**）；严格状态/搜索
   ledger/事件账；不落 legacy CN/PathwayStore/预算派生）；resume
   验完整身份后经四崩溃恢复（B4 补账/B3 消费同一 output/B1 同
   worker 幂等续跑/B2 pending 披露不默发）；事件已提交而
   followup 未调度的 B4 残余由权威记录（事件+展开计划附件）幂等
   补调度，不重发事件。停止报告按冻结优先级取主因，deferred/
   知识缺口存在时不称"所有路线都探索完"。**冻结计划/池输入内容
   绑定、恢复坏 artifact 隔离、后续/转换集合逐对象补齐、执行会话
   互斥、novel 独立假设消费、blocked 持久披露（S3b-r2/r3 增量
   见 0e 节）**；公开入口真子进程复验四硬杀/新进程恢复/二次幂等
   恢复/并发控制。

---

## 7. 0e. S3b 恢复/调度/协议消费契约（v15 文本，冻结稿同步 r3
行号；全部是恢复/调度/协议的消费契约，不是新化学判据；生产化学
链 production.py 两批零改动）

1. **冻结输入身份（S3B-01；v15 补后段锚定）**：计划（池/模型
   响应/转换意图/激活指令/条件事实）在 start 时持久化为**冻结
   输入来源**（run-plan/frozen_plan artifact，plan_digest 内容
   绑定）。resume 的 retrieve/decide/模型请求/expand/followup/
   转换全部消费该冻结来源：**旧任务不消费新输入**。三类拒因
   分栏：
   - **读取侧**（artifact 完整性/自洽）：H07 完整性包装 + 内容
     身份核验 —— 缺/坏/digest 不符 ⇒ frozen_plan_missing/
     frozen_plan_corrupt/frozen_plan_integrity_failure/
     frozen_plan_digest_mismatch（保全原文件，不猜）；
   - **传入比对侧**：不传 plan ⇒ 沿冻结输入（**缺输入不变空
     池**，不当 no_local_candidate 合法完成）；传入计划内容
     不符 ⇒ frozen_plan_mismatch（差异须显式新 revision/新
     任务登记，不复用旧裁决键）；
   - **后段锚定（S3b-r3 新增）**：resume **首消费前**（任何
     recover 补账/事件提交/新调度/预算 consume 之前）把读取的
     冻结计划与**独立既存权威**核对 —— start 落账的根 retrieve
     行（DB 通道 payload.plan_digest；task_key 经同一
     `decision_task_key` 单一来源按行内冻结字段重算比对）。
     **artifact 文件内自算的信封 payload_hash/plan_digest 是
     自洽证书，不能单独证明仍是该 run/root/task 的原输入**；
     覆盖 root retrieve 已 done 的 B3/B4（执行层核验后段不可
     达）。缺锚 ⇒ frozen_plan_anchor_missing；坏锚（锚行载荷
     不可解析/task_key 重算不同源）⇒ frozen_plan_anchor_
     corrupt；锚摘要 ≠ 冻结计划摘要 ⇒ frozen_plan_binding_
     mismatch —— 均先结构化拒，业务表/event/commit/consume
     零新增，原资料保全。不做密码学签名、不抗全库协同改写
     （复审明示范围外）；正常同计划/省略 plan/显式同计划/合法
     原计划转换恢复全保持。
   实现锚点（冻结批次已核，r3 行号拆分〔冻结改字③〕）：冻结
   计划持久化/读取 `_persist_frozen_plan` runflow.py:229、
   `_load_frozen_plan` :242-271；后段锚定核对
   `_verify_frozen_plan_binding` :274-390（锚行 SELECT :304-309，
   锚行扫描**跳过无 plan_digest 的 followup retrieve 行**
   （:329-330，缺锚判定=无任何携带 plan_digest 的 retrieve 行，
   防误读为"所有 retrieve 行都是锚"）；task_key 经同一
   decision_task_key 按行内冻结字段重算 :332 起）；执行会话锁
   `_DriverSession` 段 :392 起（勿把锁段误标为计划段）；resume
   中锚定调用 :1521 **先于** recover_run :1522（隔离/驱动在其
   后）。第二层（纵深防御）：retrieve 任务 plan_digest 与
   decide 冻结 pool_digest 同源重算核验（入口锚定后正常流不可
   达，保持为防 DB 侧输入漂移）。
2. **恢复裁定接执行门（S3B-02）**：recover 已诚实识别的坏
   artifact（hash 不符/不可反序列化）action，在恢复后**明确
   隔离**（claimed → blocked，defer_reason=recovery_failure:
   <kind>；隔离写点 search.py:1213，UPDATE 仅限 status=claimed）：
   **零猜重算、零坏任务 event/成功 commit/consume**；坏原文件/
   attempt/预约行保全（不释放不猜补；隔离=不执行、不释放、保全
   证据，不是"已恢复正常"）；blocked 不可执行（claim/激活均
   拒）；其他合法 B1–B4 与明确独立任务继续驱动。H08（提交事实
   与 ledger 不一致）仍为恢复前置结构化失败（整 resume 拒），
   不自动补事件/修库。
3. **后续/转换集合完整性（S3B-03）**：B4 恢复的期望后续集合从
   **已核权威**（提交记录 event_id → 事件行参与物产物全集 ×
   展开计划 expanded/deferred/not_tracked + 冻结计划的显式转换
   意图）派生，**逐对象幂等补齐**（0/部分/全部），不以"payload
   引用计数>1"当完整性证书；转换 action 的 pending_followup
   （事件/产物全集/父路径/上下文/revision/深度）**创建时一次
   冻结入载荷**（消除"先入队后 UPDATE 附加"的两写窗口；实现：
   `_ensure_transition_followup` runflow.py:577-615，pending_
   followup 载荷在入队调用内一次写入，本冻结批次已核）；转换
   执行后按新上下文调度 followup（只后效，旧边评估冻结）；不
   重发事件、不重复扣额；完整共同产物事件不截断。一般产物
   补齐 `_Driver.reconcile_followups` runflow.py:500-558〔冻结
   改字③：v15 旧指认 209-226/304-321 已非该两函数〕。
4. **执行会话互斥（S3B-04）**：公开 start/resume 以 run 目录
   driver.lock 的 flock（LOCK_EX|LOCK_NB）取得**可验证执行权**：
   双进程同时驱动同一 run 只有一方进入恢复/认领/请求/工具执行，
   竞争方在任何执行前结构化拒（driver_session_active；不创建新
   attempt/event、不重复扣额；持有方退出后再次 resume 即幂等
   复用完成结果）；崩溃（进程死亡）⇒ OS 自动释放 ⇒ 新进程接管
   （原 attempt/预约/claim 行原样保留，B1 同 worker 幂等 reclaim
   续跑，不永久锁死）。**同机文件锁语义；不宣称分布式锁或
   外部 provider exactly-once**。并发验证用两个真实公开 resume
   进程 + 真实工具入口计数（patched 包装调用冻结工具）+
   barrier，不以最终 event 幂等为唯一断言。
5. **novel 独立假设消费者（S3B-05）**：novel 池外提案（协议
   model-proposals-2）必须携带**完整反应内容**（reaction_spec：
   product_smiles/edits/donor/alignment/expectation 等与冻结池
   条目同形状；缺 ⇒ json_field 格式错误可进有界反馈）与**来源**
   （proposal_context：reference_hypothesis_ids/output_origin 明
   示，不伪造）。驱动经 prepare_hypothesis 单一构建源构造独立
   假设（结构身份/参与物/系数/共同产物/条件/依赖沿既有契约；
   来源入冻结任务输入与产物 source_refs），按预算入队走**固定
   AtomTool→供体诊断→converter→audit→admission→submit** 生产
   链（与池内假设同一链；proposal_context 披露）；无足够内容 ⇒
   构造侧结构化拒（run_error 如实停止，不以反馈改分子再试）。
   空池仍**组装底物档案**（独立于候选，持久 artifact，substrate
   只读组装，见判据三⑤）并消费模型响应（novel/合法弃权）；
   池内选择/弃权合法，弃权与规则池并行；不启 chemical_reposal、
   不发真实 provider/付费；scripted 网络 0。**来源标签精度
   （0c-v15.4/R3 §5，冻结补写）**：decide 侧 prepare 传入
   model proposal 的 source_refs，expand 重建未传而用默认
   synthetic-pool-spec，实际 event appearance 使用后者；
   state_id/hypothesis ID 不受这些 refs 影响；冻结 plan 含原
   响应、action proposal_context 保留，来源可追溯，无身份洗坏/
   错误 verified。**不宣称来源标签逐字全链一致，也不宣称已
   认证现实来源**（文字/来源一致性设计仍 P2，登记于冻结记录
   未核事项清单）。
6. **blocked 持久披露（S3B-06）**：调度深度阻断的假设对象以
   search_actions **blocked 行**持久化（status=blocked +
   defer_reason=原因 + 冻结任务输入；写点
   record_blocked_hypothesis search.py:1078 起、blocked 行写入
   :1145 一带；幂等不重数；不可执行）；公开 stop 从持久行
   **同源派发**：depth_limit 停止原因 + unexplored.blocked_
   objects 对象清单（action/假设/原因，有界 100 条），不是只存
   计数；**主因优先级不动**（user_stop > budget_limit >
   depth_limit > …；零深度+预算复合时主因 budget_limit 合法、
   depth_limit 入其他原因，摘要展示同屏披露，不改优先级只改
   展示纪律）；正常运行/恢复同源、不丢/不重数；blocked 对象
   存在 ⇒ 不称 exhausted_search。

---

## 8. 程序证据采信边界（冻结记录的组成部分，随判据冻结）

- **采信分级**：工程数字与执行行为证据**只由独立执行证成**——
  Codex S3b-r3 终审（2026-10-08）独立执行：ppv1 全量 879 passed/
  0 skipped/0 failed、直接父 2bedfc0 同字节对照 5 行为红+3 正控
  绿、G01 安全隔离 1481 passed/8 skipped/17 deselected（288 输入
  SHA 前后一致）、公开入口真子进程探针 15/15、锚/恢复公共链 38
  顶层观察（36 契约符合+2 header-only P2 边界）、本机 RDKit
  2026.03.6 五正控+三别名×两入口六负控、production/legacy 与父
  逐字节一致核验；证据入口
  `docs/review_evidence/ppv1_s3b_codex_r3_2026-10-08/README.md`。
  mimo v15 回应为**只读评审**：其执行类声明一律保持"待执行
  验证"原文、不回写、不改称模型已跑；其读码事实采信到与程序
  证据互证的程度为止（AGENTS.md 采信限度）。mimo 待执行五类
  已由 R3 复审全部独立执行闭合（逐项见冻结记录 §7）。
- **工程数字不当化学证据**：上述全部为合成规则级契约结果，不
  代表 dev（B1 环境路径中间步骤）或 298（RHEA 通用酶学）科学
  性能，不是性能增长曲线，也不证明判据的科学正确性——判据
  冻结是**文本/口径/门的版本冻结**（实现与判据文本的互证已达
  R3/mimo 采信线），科学性能保持 pending（S4/S5 另行验收）。
- **行号锚定**：正文全部行号在冻结时 HEAD
  `adf0287abef0c4803962fee0df0065d8e6f3793d` 下由冻结批次只读
  复核（复核范围见冻结记录 §9）；后续源码变更须重锚并核对
  判据与实现的一致性，偏离冻结判据属违约。
- 参考（外部常识，非本仓资产）：RDKit Book（CXSMILES 扩展/
  增强立体/立体化学章节）、rdCIPLabeler API；CXSMILES 解析器
  行为经 Release_2026_03_6 源码取证与实证用例校准（本机往返/
  负控已由 R3 独立执行证成）。
