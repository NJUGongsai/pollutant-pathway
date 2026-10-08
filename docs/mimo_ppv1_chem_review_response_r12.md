> **通道与 provenance（主会话 ZCode 记录，非 mimo 回应正文）**
>
> - 2026-10-08 凌晨（S3a 回修 r4 轮，按 AGENTS.md「评审-回修自动循环」轮内第③步自动送审）：请求经 **opencode 免费模型 `opencode/mimo-v2.6-flash-free`** 只读评审；opencode 会话 `ses_ee84b51c7ffeAEOEEOPvKxRcZF`（标题 "mimo ppv1 v12 chem review"）。与手机 mimo 应用是否同一实例未经证实，采信按本通道口径区分。
> - 本轮一次运行完整输出（无断流、无续跑）。
> - 评审为**只读**：模型自述未执行任何测试/探针，执行类声明一律标注"待执行验证"。其中 PPV1 787 passed 已由主会话本机独立复跑证实（2026-10-08 凌晨）；G01 安全隔离 1389/8/17 为交付方隔离证据，留 Codex 复核。
> - 本轮提示词保留读码事实纠错警示；v12 回应多处自标"待执行验证/局部未确认"，引用行号与源码一致性留 Codex 互证。
> - 请求原文：`docs/mimo_ppv1_chem_review_request.md`（v12，S3a r4 版，自包含、无金标）。运行证据与原始输出：`docs/review_evidence/ppv1_s3a_r4_mimo_2026-10-08/`。
> - 以下为 mimo 回应原文（仅清理终端控制字符，未做任何内容改动）。

---
# mimo 化学评审回应:pollutant_pathway_v1 判据 v12(S3a 回修 r4 后)

**执行边界声明**:本轮只用读取类工具(读文件、内容检索)浏览仓库;**没有运行任何测试、探针或模型**,不产生任何执行数字。凡依赖执行的判断一律标 **"待执行验证"** 并写明需要跑什么。下列行号与名称均为**本轮我实际读到的位置**;只检索到行、没读上下文的会注明"仅检索命中"。

我实际通读/核对的文件:`src/pathway_v43/pollutant/{chemstate,audit,hypothesis,path_context,store,search,profile,pool_audit}.py` 的相关段落、`src/pathway_v43/__main__.py`、tests/test_ppv1_*.py 文件清单(仅确认存在,未运行)。

---

## 0b / 0c / §6(工程披露、八条件清单、程序证据)

**1) 结论:同意(有条件)** — 条件:§6 全部执行数字保持"待执行验证";0c-⑧ 已写死。

- 0b 三组残余的**函数与字面**我核到存在:`_verify_action_references`(search.py:1734)、`record_request_sent`(:1454)、`mark_request_failed`(:1524)、`_reserve`(:884)、`search_policy_block_corrupt`(:748、:1462)、`request_status_unknown`(:1293、:1553)、`unknown_status_requests`(:2767、:2803)、retrieve 按 cache_hit 的创建条件(:996、:1746–1747、:2047–2049)。契约字面:`ppv1-profile-12`/`ppv1-store-9`/`ppv1-search-4`/`ppv1-search-limits-3`(profile.py:114、:118、:163、:233)与 §6 一致。
- "消费侧权威核验 = 写账前只读复核、与公共 writer 重放同源"与我读到的 search.py:2084–2104、:2232–2306、:2325 一致;`verify_event_attachment_content` 自述"只读、零写入"(store.py:1989–2000)。
- 0c-⑦ 更正**属实**:工厂入口下两种内因的外层同为 `ChemicalStateError`,分别带 `kind=unregistered_cx_class`(chemstate.py:466–476)与 `kind=unparseable_smiles`(:690–693);跨入口才不同——公共 writer 外层 `Ppv1StateContractError`(store.py:398、:562–568)。v11 那句括注确系错误,不得回潮。
- 0c-③ RDKit **2026.03.6** 与仓内文档一致(docs/ASSET_WIRING_REPORT.md:97、docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R2_2026-10-07.md:139),我上一轮(r11:32、r11:184)的核对口径可复用。

**2) 修改建议(可直接落字)**
- 0b 的"cache_hit 同构"披露建议补一句可核事实:"检索预约行的创建条件是 claim 非 cache_hit(search.py:2047–2049),因此'合法缓存认领'与'认领后删行'在存储上不可区分,本轮不加 schema 列"——现在这句已有,建议把行号一并写进交付书,免得下轮再被当"未读码"。
- §6 数字前统一加前缀"**待执行验证(读码仅确认 tests/test_ppv1_s3a_rework_r4.py 等文件存在,未核计数)**"。

**3) 风险点**:红绿/787/1389 这类数字若不标"待执行验证"直接进冻结材料,下一轮很容易被当成"已独立复核的事实"复读;0c-⑧ 已经挡了一半,建议把"**测试计数与红绿结论同属执行证据**"也写进 0c 清单,与"读码行号须与实际源码交叉核对"并列。

---

## 判据一:分子身份

### (a) v12 落字(真实 token / 外层-内因两维 / 同源非独立)+ v9 三处

**1) 结论:有条件同意** — 两个条件:
- **条件 A(必须改)**:2b 的"按 `detail.reason.kind` 区分"是**按入口分裂的两条事实,不能合成一句**。工厂/strict 入口:顶层就是 `detail.kind`(chemstate.py:473、:692),**没有 `reason` 子层**;恢复入口(from_dict→validate_state_object)才把内因塞进 `detail.reason`(:842–849、:891–899),且**外层 kind 是包装名** `state_structure_unparseable`(:846)/`raw_structure_rejected`(:896)。现在的写法在工厂入口读是错字段、在恢复入口读是错外层。
- **条件 B(标待执行验证)**:"RDKit 2026.03.6 实际写出 ABS/AND/OR/自由基并保持严格身份往返"是执行结论,我只能读到侧面痕迹:登记正则确为 `(a|o\d+|&\d+|\^\d+):`(chemstate.py:266)、输出登记表 `^(Sg|SgD|a|o\d+|&\d+|\^\d+)!?:`(:237–238)、许可身份字面含 `[H] |^1:0|`(audit.py:273–276)。**待执行验证**:用 RDKit 2026.03.6 对 ABS/AND/OR 组与自由基分子跑 `MolToCXSmiles`,逐 token 对照登记表,再过 `_guard_input_cx_classes` 往返比 state_id。

**读码为真、可采信的部分**:真实 token 表 ✓;三字面别名 `and/or/rad` 落到 chemstate.py:452–456 的兜底显式拒绝(我按正则逐个推演:非法)✓;同源非独立 ✓(validate_state_object 内直接复用 `build_chemical_state`/`strict_identity_of`,chemstate.py:840、:890,docstring :754–775 自述"只核对象内部可确定的一致性,不认证来源真伪/历史执行/机制")✓。

**2) 修改建议**
- 把 0c-⑦ 改成分入口两句:"**工厂/strict**:外层 `ChemicalStateError`,`detail.kind` ∈ {unregistered_cx_class, unparseable_smiles};**恢复入口**:外层 `ChemicalStateError`,`detail.kind` ∈ {raw_structure_rejected, state_structure_unparseable},内因读 `detail.reason.kind`。"
- 把"RDKit 写出 ABS/AND/OR/自由基"改写成"**写出 `a:`/`&N:`/`oN:`/`^N:` 注解块(语义分别为 ABS/AND/OR/自由基)**",消除"是不是字面单词"的歧义(同段又说 and/or/rad 不是输入字面,两句并读会打架)。

**3) 风险点**
- **身份键的"稳定哈希"只在锁定 RDKit 2026.03.6 内成立**:仓内只有 `checkenv` 打印版本(`src/pathway_v43/__main__.py:41–60`),**没有运行期版本断言**(grep 全包 `rdkitVersion/rdBase` 仅命中该处,读码事实)。换 RDKit 版本可能"同一物质换 state_id",程序完全诚实、化学上会被读成"物质变了"。建议规则正文写明"身份可比性以锁定 RDKit 版本为前提,冻结时加运行期断言(**待执行验证**:需跑一次跨版本对照)"。

### (b) 入口清单与诊断入口划界

**1) 结论:同意(局部未确认)** — 工厂(chemstate.py:687)、strict(:923)、恢复(:648)、audit 直接对象(audit.py:474–475)、判据五四字段(audit.py:2572–2592)**五处闭合我读码确认**;preview 按 C2 划界 ✓(pool_audit.py:248–302,`diagnostic_only` + `pool_unchanged=True`,:302)。
**未确认两处**:`search.py` 全文我用检索确认**无任何 RDKit/chemstate 工厂调用**(检索 `MolFromSmiles|strict_identity_of|_guard_input_cx_classes|Chem\.` 于 search.py 零命中),但"搜索层**全部**消费入口"逐行矩阵(search.py:103–116)我只读了表格文字、未逐行对实现;冻结执行器内部解析我只**检索命中** `services/atom_tool.py:177/295/410/599`、`validation/conservation.py:491` 的裸 `MolFromSmiles`,**未读上下文**,故"结果不回流"目前是"未发现回流路径",不是穷尽证明。

**2) 修改建议**:在 C2 条款里补一句可核断言——"**执行器/preview 的输出若要成为 state_id 或 verified 证据,必须再过工厂或四字段守卫**;本轮已核:供体诊断四字段在解析前过同一守卫(audit.py:2572–2592)、执行器产物进入对账前先守卫后解析(:2596–2600)"。

**3) 风险点**:`pool_unchanged/diagnostic_only` 诚实,但"诊断输出"与"筛选结果"在数据结构上同处一个返回块(pool_audit.py:275–302),下游若整块透传,可能把"诊断"读成"该候选已被规则采纳"。建议字段名/文档保留"结果不被消费"的显式句(现有 :302 注释已写,建议同步进判据正文)。

### (c) 判据 1–4 文本不重评

**1) 结论:同意**;**2) 建议**:无;**3) 风险点**:无新增——但 1(身份键)里"与 RegistrationHash 的一致性限定在整组翻转/部分反转/排列/kekulé/映射号子集"属 RDKit 源码/行为事实,**待执行验证**(需跑 RegistrationHash 对照)。

---

## 判据二:参与物计量与元素/电荷核算

**1) 结论:同意(两处 v12 落字均准确反映实现)**

- **系数句 ✓**:零/负/非有限/bool/known+null 全在构造与提交边界拒——`parse_coefficient`(hypothesis.py:136–173,bool :142、非有限 :149–152、非正 :168–172)、`Participant.__post_init__`(:202–224)、`_validate_participant`(:255–277)、store 侧"每条参与物过 Participant 构造校验"(store.py:649,仅检索命中行)。`coefficient_binding_mismatch` 确属**覆盖轴**:产出于 audit.py:928–933,导致检查 `status=unknown`(:1164–1174)并写 `product_coverage=partial_unchecked_transformation`(:1004–1005),**不是** R2b——R2b 只由调用方传入的 `contract_violation` 触发(:1749–1755),与"不能固定写成 R2b、也不能固定写成 R5"的写法一致(R5 只是首中顺序下的常见结局)。"入口不在比对系数与结构重推导值"也属实:λ_s 来自**声明**反应物系数和(:911–912),重数来自绑定产物身份(:852、:870–874)。
- **known_absent 轴归属 ✓**:数值/区间缺席 → `numeric_absence_semantics_undefined` 的 unknown(path_context.py:819–825);非物种字符串同值 → conflict `required_value_known_absent`(:826–831);异值 → unknown(:832–837);未列出 → unknown `no_applicable_fact`(:764–766);物种实体缺席 → conflict(docstring :706,函数 :701–735)。与元素账分属两文件、互不调用 ✓。

**2) 修改建议(可直接落字)**
1. **补"未知系数同时使元素/电荷账不执行"**:代码里 `full_known` 不成立时元素账与电荷账直接记 unknown(audit.py:628–651、:645–651、:676–681),不只是 coverage unknown_coefficients。现在判据二"完整性 unknown"只写 coverage,建议补一句。
2. **区分两类数值比较**:coefficient_binding_mismatch 不比结构重推导值,但 `completion_surplus/deficit` **确实**拿未覆盖参与物的元素和去比结构重推导的 λ_s×Δ(audit.py:915–918、:973–980)。建议把"不可虚称入口在比对系数与结构重推导值"限定为"**系数绑定**"四个字,避免反过来被读成"覆盖核算与结构无关"。
3. **给"结构化 omission_pattern_matches"补一句语义边界**:现有 detail 注释已写"不证明实际缺该物质、不含电子/质子计量"(audit.py:1442–1446),建议同步进规则正文。

**3) 风险点(程序诚实、化学可能误读)**
- **元素/电荷 verified 的前提"清单完整"是调用方声明的**:`full_known` 只看 `participant_list_status ∈ {source_complete, declared_complete}` + 系数全 known + 无 ambiguous(audit.py:628–632),**没有独立核验清单完整性**。两侧对称漏写的参与物在本轴完全不可见。代码 docstring 已有"verified 仅指元素与形式电荷数值闭合"(:138–140),建议判据二正文也带上"**verified 只覆盖已声明清单**"这半句。
- **D/T 并 H、自由基电子不入账**两条披露已在(:138–140、:1437–1440)✓;风险仅剩下游摘录时丢注记——建议任何引用 `elements_balanced_all_hydrogen` 的地方强制带上 `accounting_notes` 字面。

---

## 判据三:admission 决策表与中心证据契约

### (a) v12 三处 + v11 恒入/复用 + v10 (a)–(d)

**1) 结论:同意(附两条落字建议)**

- **R2b caller 映射依赖 ✓**:decide_admission docstring 明写"构造期异常 detail 必须由调用方映射传入(不传则 R2b 不可达)"(audit.py:1664–1667),实现只读 `contract_violation`(:1749–1755)。"缺映射不当化学已核"成立——缺映射时该分支根本不触发,坏假设也到不了这里(构造期已拒)。
- **中心 partial 分写 ✓**:中心结论只有 verified/violated/unknown/not_applicable 四态(audit.py:283–286);覆盖违例落 `status=unknown` + 理由 `center_evidence_partial_coverage_unchecked_transformation`(:1028–1035)+ detail 枚举(:1004);scope 未登记 → `center_checker_scope_unknown` 的 unknown(:1064–1071);类型违约/复算不一致**抛异常、不落 R 行**(:1074–1083、:1109–1116);跨假设未绑定 → unknown(:1131–1148)。四守卫在**成功路径解析之前**、失败早退在其之前(audit.py:2553–2562 早退 → :2572–2592 守卫 → :2596 解析)✓;None 非通过(:1175–1234 各分支)✓。
- **入口划界 ✓**:`verify_event_attachment_content` 只核版本门/投影范围/展开计划(store.py:2013–2021),**不碰 state 身份**;state 身份权威在 `_verify_state_payload_facts`(store.py:475–496)与 `validate_state_object`。`substrate_profile` 无生产 caller ✓(仅定义 substrate_profile.py:71 + schema 登记 profile.py:274)。
- **v11 恒入/复用 ✓**:`completion_license/scope` 只在 full/partial 分支出现(audit.py:1009–1013);unknown_coefficients(:891–897)与各 unverifiable 早退(:831、:838、:861、:907、:949)**均不带**这两个字段 ✓。
- **v10 (a)–(d) ✓**:枚举是 `partial_unchecked_transformation` 不是裸 partial(:1004);violations 逐条 kind 为 coefficient_binding_mismatch(:929)/completion_surplus、completion_deficit(:962–963)/completion_license_unregistered_identity(:993);unknown_coefficients 早退在覆盖判定之前(:888–897);未登记身份 case 的 note 与规则正文对应(:996–999)。

**2) 修改建议**
1. **R2b 行补半句**:决策表里 R2b 目前只写"理由码 representation = 非化学",建议补实现里已有的**"非结构不可解析、非化学不可能"**(audit.py:1754–1755、hypothesis.py:170–171)。否则"酶计入净计量被判 reject"会被读成"程序认为该反应化学不成立"。
2. **"proof_record 载荷不可变 + 入口身份复算(改前提不换 ID ⇒ 拒)"要指明对象**:audit_id 是**内部按输入现算**(audit.py:1386–1388、:1398–1399),不是"外部给 ID、复算不符就拒";外部 ID 复算拒绝实际在 state_id/hypothesis_id/context_id(chemstate.py:851–880、store.py:690–707、path_context.py:2082–2091)。建议拆成两个分句。

**3) 风险点**
- **R6 的 `expand` 字面易被读成"反应成立"**:R6 只代表"必需适用检查覆盖且全 verified"(audit.py:1805–1813),元素账本身也只证明数值闭合(:138–140、:1470–1473)。建议规则正文补"expand = 本层证据覆盖齐全的展开许可,不等于反应真实/可行(机制、速率、热力学另轴,见 audit.py:158–160 不变量)"。
- **R1 可达性(静态读码推断,待执行验证)**:经 `audit_hypothesis` 时所有 state 已过 `validate_state_object`,结构态空/坏 isomeric 会在 chemstate.py:822–929 先抛异常,故"parse 检查 violated → R1"这条(audit.py:518–524、:1676–1677)静态看**难以到达**;且 `audit_hypothesis`/`decide_admission` 在 src 内**无调用方**(检索仅命中定义 audit.py:417、:1643)。**待执行验证**:构造一个空 isomeric 且非 CN-only 的对象直接喂 audit,看是抛异常还是落 R1。若为前者,建议在表下注明"R1 为防御行;实际坏结构在首消费即异常逃逸、**不落任何 R 行**"(与判据五 8b 的"异常≠处置行"同口径)。

### (b) v9 scope 归属与"恒入≠已适用"

**1) 结论:同意(确认后不再列入后续请求)** — `completion_license_scope` 字面为 `"registered:composition_only_hydrogen_equivalents(H2/[H] 按 2[H] 氢当量;数值配平不证明未登记多原子共底物初始图的结构贡献)"`(audit.py:1010–1013),**确不含**"不区分键断裂方式与电子去向"句;该句在本轮请求 §3 内联为规则正文 ✓。许可定义注释(:260–271)含"键变化不区分""不新增电子/自由基轴"的**同义语义**但无该字面——"归属许可定义/规则正文"如实。"恒入≠已适用"三条件与代码分支完全对齐:full + uncovered 非空(:876–887)+ unlicensed 空(:985–1001)才是"用过许可且成立"。
**2) 建议**:把"许可定义注释 audit.py:260–271 亦承载同义语义"写进该条,免得下轮又被问"归属的许可定义在哪"。**3) 风险点**:无新增。

### (c) 决策表与覆盖核算 vs 实现

**1) 结论:同意** — 表的行序与字面逐行对齐(audit.py:1513–1548、:1555–1571、:1672–1818);R5d 触发集合就是 {element_accounting, formal_charge_accounting}(:227–228);语义 NA 白名单只有两项且窄(:231–237);`chemical_reproposal` 首版 off(:1553)。
**2) 建议**:见 (a) 的两条 + R1 防御行说明。**3) 风险点**:见 (a) 第 2 点 expand/R1。

---

## 判据四:条件相容聚合

**1) 结论:同意(a) 三处落字与 v12 补写均如实,与 v10 的差异登记清楚)**

- **孤儿方向 ✓**:已绑定旧作用域、无按签名快照承载 → 显式 unknown 行并计入整体 unknown(path_context.py:1245–1269、:1277);快照签名不属于累积要求、或签名↔评估行集合不一致 → `context_snapshot_inconsistent` **拒**(:1470–1478、:1487–1499)。方向与 v11 落字一致。
- **入口清单 ✓**:from_dict(:2060、:2082–2091)、derive 的父对象(:2327)、audit 直接对象(audit.py:455–458)强制 validate;`assess_conditions`(:1117–1169)、`assess_candidate_conditions`(:1172–1354)、`route_assessment`(:2112–2177)**确实没有**该调用 ✓ 落字准确。
- **重建半边 ✓**:derive 产物 `context_id` 按新内容现算、`parent_context_ref=parent.context_id`(path_context.py:2402–2427);"旧 ID + 新内容"在 :1540–1548 与 :2082–2091 被拒 ✓。
- **两种不可变分写 ✓**:Requirement/ConditionFact `@dataclass(frozen=True)`(:333、:438)、PathContext **非** frozen(:1942–1943),本体靠 `_recompute_context_hash`(:2213–2231)兜底 ✓。
- **known_absent 轴归属 ✓**:与判据二同源同字面(见前),两处一致 ✓。

**2) 修改建议**
1. **把两句话并排放**:规则里"任何派生/评估/审核入口消费前必须先 validate"与落字"assess_* 自身无强制、靠上游纪律"同时存在,建议合成一条:"**入口强制 = from_dict / derive 父对象 / audit 直接对象;assess_conditions、assess_candidate_conditions、route_assessment 目前靠上游纪律,S3b 必须接真实守卫**",否则前一句会被当成已实现的保证。
2. **补事实真实性边界**:快照校验自述"不认证用户事实真实性"(path_context.py:1391–1392),建议规则正文也写"**satisfied/conflict 只反映'给定事实集与要求'的一致性,不认证事实来源真实性**"。

**3) 风险点(程序诚实、化学可能误读)**
- **"compatible"极易被读成"该环境已被实测相容"**:事实由调用方给,来源引用只作追溯;`request condition_compatible 不是已相容`已写,但缺"**事实本身未被独立核实**"这半句——这是本判据最容易在下游变成化学结论的一处。
- **conflict 只挡当前场景**:单向语义已写 ✓;风险在于下游把某场景 conflict 存成"永久不可行"——建议在 conflict 理由码旁固定带作用域字面(现有 reason 未带 scenario/phase,读码所见 path_context.py:826–837;**是否在别处补作用域未确认**)。

---

## 判据五:供体一致性诊断

### (a) 8b 表述与早退边界 + v12"失败 diagnostic 与下游 audit 分开"

**1) 结论:同意**

- **失败三 None + center_evidence={} ✓**:execution_ok=False 早退返回 `strict_target_match/legacy_cn_match/reaction_center_match = None`(audit.py:2553–2562),`center_evidence` 走默认 `{} `(:1919),`schema_version`、`alignment_ref` 照常有值。
- **converter 仍返回版本/来源元数据与 center_match=None ✓**:`center_evidence_from_donor_diagnostic` 在证据为空时走兼容路径,返回 checker_version + center_match(=None)+ evidence_refs(audit.py:2983–2993);下游因缺 `checker_scope` 落 `center_checker_scope_unknown` 的 **unknown**(:1064–1071),缺 proof 落 `center_evidence_proof_missing` 的 unknown(:1085–1102)。
- **各轴分开、互不排斥 ✓**:元素/电荷/完整度等检查独立产出(audit.py:628–681 等),中心 unknown 不吞其他轴的 verified;同时**整体不会因此 expand**——unknown 会命中 R5(:1796–1803),R6 要求全 verified(:1805–1813)。
- **早退先于守卫与解析 ✓**(顺序见判据三 (a))。

**2) 修改建议**:在 v12 那段末尾补半句防误读——"**中心 unknown 时整体最高 retain_conditional,不得 expand**"。这样"同一次 audit 仍可给其他轴 verified"就不会被读成"诊断失败不影响整体结论"。

**3) 风险点**:同上——"分开"与"整体仍受 unknown 阻断 expand"必须成对出现,否则是本判据最大的误读面。

### (b) 8d 未闭合但如实披露,是否可作为 S3a/r4 边界

**1) 结论:同意(可接受,闭合路径 = S3b caller + 正负控回归)**
我静态复核与请求一致:全 src `raise AuditContractError` 共 **10 处、全在 audit.py**(:464、:739、:1076、:1110、:1589、:1596、:1603、:1607、:2547、:2584);**包内无 `except AuditContractError`**(检索零命中);`check_edit_against_donor` 源内唯一调用在 audit.py:746,处在 `_rerun_proof_record`(:727–751)内、调用点(:1105)无 try 祖先;`audit_hypothesis`/`decide_admission` 在 src 无 caller(:417、:14643→:1643 仅定义)。**结论:静态证据与文本披露相符;文本也已声明"不是动态安全的通用证明"**,同意以此为边界。
**2) 建议**:把"10 处行号"直接列进 0b/交付书,免得下轮再数一遍。**3) 风险点**:无——只要"静态≠动态"这句保留(已写)。

### (c) v11 落字与 0c 清单是否足以防止再次出现读码事实错误

**1) 结论:同意(补一条纪律)** — 净变化不认证模板/图等价非酶识别/legacy_cn_match 仅旁证,均有源:audit.py:1882–1887(区域诊断、不核模板)、:1887 与 :2793(图等价≠酶识别)、:1890 与 :1898(legacy_cn_match 旁证、不进计数)。0c-③ 已把版本钉死、⑦ 已禁用错误括注、⑧ 要求行号与源码交叉核对。
**2) 建议**:0c 再加一条"**跨轮复用的行号/分支名必须本轮重读**"(行号会随回修漂移,上一轮正确的行号这一轮可能已不对应)。
**3) 风险点**:无新增。

### (d) 其余条款是否与实现一致

**1) 结论:同意** — 奇偶法 `_stereo_config_delta`(audit.py:2063–2064);非四面体公开列项、中心外存在即不可判 True(:1926–1930);`bond_stereo_change` 入变化集与对账签名(:1960–1976);供体中心部分缺映射 → unknown、不部分判定(:2541–2542);alignment 三态 resolved/ambiguous/unavailable 与非法值拒(:2519–2522、:2546–2549);strict 与 `strict_identity_of` 同源(:2676–2677);镜像终态写出再重解析(:2319–2328);证据载荷内嵌 proof_record 完整输入集(:2869–2892)。
**2) 建议**:"原子映射支持范围(完全/部分/缺失)"我在代码里没找到同名字段,实际是 `alignment.status` 三态 + "供体中心全映射否则 unknown"两条**行为**——建议落字改成"**按 alignment.status 三态与'供体中心是否全部有映射'两维表达**,字段名待核(**未确认**)";另外"region 净变化"的 checker scope 只登记了 `region_net_change`(audit.py:244–248),规则正文若出现"完整模板一致"字样须同时注明这是**未注册**范围。
**3) 风险点**:`symmetric_equivalent` 的 True 是"保手性图上的联合自同构像"(audit.py:2793、:1892–1894),它排除了"区域外不可比立体轴"的干扰(:1926–1930),但**仍不认证酶对该对映/区域选择性的识别**——文本已写"图等价不是酶识别",建议在 `center_evidence_verified` 的理由码解读处固定复述一次(理由码本身只有 checker/scope/basis,audit.py:1218–1224,读起来像"已核实")。

---

## 汇总(逐条结论一览)

| 受审项 | 结论 | 关键条件 / 修改建议 | 头号"程序诚实、化学误导"风险 |
|---|---|---|---|
| 0b/0c/§6 | 同意(有条件) | §6 全部数字标"待执行验证";0c 增列"测试计数属执行证据""跨轮行号须重读" | 红绿/787 被当下轮"已复核事实"复读 |
| 判据一 (a) | **有条件同意** | A:2b 按入口分写 `detail.kind` vs `detail.reason.kind`(chemstate.py:466/690 vs 846/896);B:RDKit 写出与往返标待执行验证 | state_id 稳定性实绑 RDKit 2026.03.6,无运行期版本断言(`__main__.py:41–60`) |
| 判据一 (b) | 同意(局部未确认) | C2 补"执行器/preview 输出须再过工厂/守卫" | 诊断输出与筛选结果同块返回,易被整块当采纳依据 |
| 判据一 (c) | 同意 | — | RegistrationHash 对照属执行事实(待执行验证) |
| 判据二 | 同意 | 补"未知系数→元素/电荷账也不执行";限定"系数绑定"不比结构重推导;补 omission 语义 | verified 只覆盖**调用方声明完整**的清单(audit.py:628–632) |
| 判据三 (a) | 同意 | R2b 补"非化学不可能"半句;ID 复算指明对象 | `expand` 被读成"反应成立" |
| 判据三 (b) | 同意(本项关闭) | 补"许可定义注释 audit.py:260–271 承载同义语义" | — |
| 判据三 (c) | 同意 | R1 加"防御行/坏结构先抛异常不落 R 行"(待执行验证可达性) | 读者期待账内出现 R1 记录而实际是异常逃逸 |
| 判据四 (a) | 同意 | "入口强制清单"与"assess_* 靠上游纪律"并排成一条 | `compatible` 被读成"环境已实测";事实真实性不被验证 |
| 判据四 (b) | 同意 | conflict 理由码补作用域(现未见,未确认) | 某场景 conflict 被存成永久不可行 |
| 判据五 (a) | 同意 | 8b 补"中心 unknown ⇒ 整体最高 retain" | "各轴分开"被读成"诊断失败不影响整体" |
| 判据五 (b) | 同意(边界可接受) | 10 个抛点行号直接入交付书 | — |
| 判据五 (c)(d) | 同意 | 0c 增"跨轮行号重读";映射支持范围按行为描述、字段名未确认 | `center_evidence_verified` 理由码字面像"已核实",不含"非酶识别"提示 |

**"待执行验证"清单(我不跑,需在冻结前执行取证)**:① RDKit 2026.03.6 对 ABS/AND/OR/自由基的 CX 写出形态与逐 token 往返;② RegistrationHash 对照范围;③ §6 全部测试计数与基线红绿;④ 空/坏 isomeric 对象喂 audit 时 R1 的可达性;⑤ 跨 RDKit 版本 state_id 稳定性;⑥ cache_hit"删行"反例探针是否覆盖(交付书已登记为残留,同意保持披露)。
