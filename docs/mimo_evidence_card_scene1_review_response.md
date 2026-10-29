# mimo 回应 — 证据卡内容判据面复核（场景 1，随 chain14 预注册冻结，2026-10-15）

> 通道：A（opencode/mimo-v2.6-flash-free，免费网关）；只读评审（可用读取
> 工具核对、无执行权限、不得编造执行结果）。请求：
> `docs/mimo_evidence_card_scene1_review_request.md`。
> 采信原则：与程序证据互证为止，不做独立性背书；执行类声明一律视为
> 待执行验证。原始运行 exit 0 无断流。

---

---

**Q1 编辑摘要语义**
**结论：部分**——载荷里字段本身是纯记账（`candidate_evidence.py:90-128` 只渲染 op/键级/计数），但提示词规则段（`real_model.py:157-161`）只说了「informational context、不改输出契约」，**没有一句明确"这是执行器账本，不是机制声明"**，边界留给模型自己猜。
**化学论据**：`change_bond_order single→double` 在化学上至少有三种读法——氧化脱氢、水合物/互变异构的净结果、非氧化的键级重排；记账层面完全等价。且这些 edits 对 recorded_inferred 候选是从记录净反应编译来的（记录本身也不是机制），模型把它读成「脱氢酶机制」是双重过度解读。另一个具体的坑：`bonds_broken/bonds_formed` 不计隐式氢，「0 断 0 成但 C–O 变双键」的表面不一致，可能诱导模型认为账本不平衡或自行脑补机理补丁。
**最小改法**：规则段加一句（不重写）：*"the edit summary is a deterministic ledger of graph operations already recorded for that pool entry — executor bookkeeping, not a mechanism, catalytic cycle, or proton/electron balance; hydrogen changes are implicit in the execution graph and not counted."*

**Q2 参与物角色证据**
**结论：部分**——role 命名本身是结构槽位（`hypothesis.py:82-91`：primary_substrate/cosubstrate/principal_product/coproduct/unknown），不暗示反应类型，方向性也对；但有两处真实误导面。
**化学论据**：(a) cosubstrate 的 **SMILES** 才是同底物歧义题（108 题）最有化学区分力的信号——NAD⁺ 对 NADH 决定底物被氧化还是被还原，H₂O/O₂ 决定水解还是氧化，这是正确用法，不是误导；风险点是 `role="unknown"` 与提示词里"字面 unknown=系统不可得"**共用同一个词**（`hypothesis.py:86` vs `candidate_evidence.py:43`），而 role unknown 的真实含义是"该参与物在场、角色未指派"——模型可能把整条参与物当"事实不可得"丢掉。(b) 系数全 unknown 时，化学直觉强的模型可能读成"未配平/不可靠"而降权；实际是记录源无配平系数的诚实状态（`candidate_evidence.py:151-157` 注释）。另外"完整角色表"与 `participant_list_status=partial` 实际并存（探针输出即为 partial），两条字段分居 `participants` 和 `conditions_and_scope` 两处，模型容易只见局部当完整。
**最小改法**：规则段补一句：*"role 'unknown' means the role was not assigned to a present species (not a missing fact); coefficient unknown means stoichiometry unrecorded, not unbalanced; the participant list may be partial — check participant_list_status."*（改 role 字面量属载荷编码变化需升 schema，非最小，不建议本批做。）

**Q3 描述符纪律**
**结论：是（纪律线划得对），但官能团表有两处化学口径不一致**。
**化学论据**：Gasteiger 是拓扑加和估算，不看质子化态、溶剂、活性位点静电——把它的"逐原子前 3 低"当反应位点在化学上是常见过度解读，而现纪律（`_reference` 后缀+提示词明示"非位点非证明、执行图唯一可编辑结构事实"+非有限整体降 unknown，`candidate_evidence.py:337-347`）恰好把这三类风险各堵了一句，方向正确。对单步酶促排序的价值/风险我的读法是：**底物级描述符对同一题的所有候选同值，本身零区分力**，只有间接价值（帮模型判断"这个候选动的原子是否化学上可极化/可进攻"）；风险是模型拿 mean 电荷这种近乎零信息的数字做跨题比较（中性分子 mean≈0，无排序意义），以及质子化形式按题面所绘算、酶实际作用在另一形态时方向会反过来。**官能团表两处不一致**：①`hydroxyl_oh=[OX2H][#6]` 会命中羧酸自身的 –OH（`candidate_evidence.py:61`），酸+醇双标签可能诱导把酸 OH 当可氧化醇读（类间重叠是设计书 §二声明的许可行为，但这一条语义上最贵）；②`amine_tertiary` 有 `!$(NC=[OX1])` 酰胺排除，`amine_primary/amine_secondary` **没有**（:65-66），一级/二级酰胺 –NH₂ 会被标成 amine_primary——同类三种处理不一致，是表内口径问题而非设计选择。`alkene [CX3]=[CX3]` 对四取代双键的覆盖边界我只读未跑，**未核对**。
**最小改法**：给 `amine_primary`/`amine_secondary` 补上与 tertiary 同款的 `!$(NC=[OX1])`（一条 SMARTS 后缀）；`hydroxyl_oh` 加羧酸排除（形如 `!$(C=[OX1])` 作用于相邻碳，需 RDKit 双跑核验后再钉）或在规则段注明"重叠如实报告、按主官能团优先读"；规则段补半句 *"charges are computed on the substrate as drawn (protonation/tautomer form as given); environment and active site are not modeled."*

**Q4 unknown 语义**
**结论：是**——字面 unknown 优于"不喂该字段"，但需要补半句防弃权。
**化学论据**：化学上**缺席极易被读成断言**——不给 conditions，模型会默认"无特殊条件/无共底物"（这本身是一个未经证实的化学主张）；不给系数，模型会默认 1；不给 role，模型会脑补。显式 unknown 把"系统不可得"和"事实为空"分开，堵住的正是这类静默假设，这一点比省 token 的静默删除强。真实风险在另一侧：规则段同时存在两处 "unknown"——输入占位符（`real_model.py:160`）与弃权措辞（`:109` "abstain (unknown is legal and honest)"、`:154`）——高 unknown 密度的候选可能被模型的"诚实弃权"条款连带处理，弃权=不命中，直接吃掉 hit@1。这不是过度反应的想象题，是两处措辞共用一个词的结构风险。
**最小改法**：`:160` 那条尾部加一个从句：*"…never guess or invent a value for it; an unknown field is not negative evidence about that hypothesis and is not by itself a reason to abstain."*（一句，且顺手把输入占位符与输出弃权语义切开。）

**Q5 来源证据的化学指向性**
**结论：部分**——保守取舍（去 EC/酶名/条件）在红线内正确，但 `source_kind` 是**出处可信度**信号，不是**化学**信号，对"帮模型选对"只够撑一半。
**化学论据**：recorded_inferred（记录直通）比 analog_template（模板迁移）更接近"该净反应见过实证"，这对歧义题是合理的先验，且完全无金标问题。缺的最大一块是**候选相对底物的官能团得失（FG delta）**——歧义 108 题的本质是"同底物不同参考目标"，化学判据就是"从这底物的官能团出发，哪个产物在化学上走得通"，而这条事实**系统内已有全部原料**（底物 FG 表 × 候选 product_smiles，同一 SMARTS 表可确定性算），不需要语料侧供。若必须从语料侧补，优先级排序：①donor/cosubstrate 匹配层级（strict_exact/cn，设计书 §四已知在线但完整恢复未证明——恢复后它是共底物证据的置信度，化学意义直接）；②中性的转化家族标签（从记录自身平衡方程差分得出的"醇→醛"式描述，**不是** EC、不是酶名）；③"候选所需共底物种类 vs 情景可用性"的匹配位（条件键 oxygen/electron_donor 等在线时）。最不该做的是把 EC 换个马甲回来。
**最小改法**：本批 v1 不加字段（预注册已冻结），把 **FG delta 列为 v2 首选**，在设计书 §四追加一行登记即可；语料侧候选事实记"donor_match_level 待完整恢复证明"。

**Q6 禁词面/泄漏风险**
**结论：否（未发现金标侧新泄漏面），附两条须登记的注意项。**
**化学论据**：逐字段过一遍——`edit_summary/participants/alignment_quality` 全部来自候选自身 spec 与 prepared（候选来自语料检索，与金标=题卷参考来源不同，题目所述对照成立）；底物级 FG/分子式/电荷只吃 `substrate_smiles`（载荷本就携带底物）；`conditions_and_scope.requirements` 在池 spec 上通常缺位→unknown（`s5b_compiler.py:1059-1083` 的 spec 无 requirements 键，我只核了这一支，**recorded 直通支未逐支核对**）；`spec.expectation.target_smiles` 与 `spec.corpus` 块（含 EC，设计书 §四明令禁展示）都**没有**进证据卡——这两处"该没的确实没进"是本次核对里最让我放心的两点。注意项：①`source.transformation_ref/alignment_ref` 携带 record_id（如 rhea:NNNNN），模型可能借预训练记忆反查 Rhea 反应——但 `transformation_ref` 是**既有载荷白名单字段**（`real_model.py:232`），证据卡只是重复呈现，不构成新增泄漏类；②`condition_keys_known` 来自 `context.condition_facts`（`substrate_profile.py:108-113`），其来源若为题面场景条件则属题面侧——上游诊断文档记本批 condition_facts 为空，**实际批数据我未核对**，建议随批载荷探针顺手披露该字段的非 unknown 覆盖率以坐实零题面。

---

**总体读法（≤5 行）**：证据卡内容整体化学语义站得住，四条纪律线（记账非机制、角色槽位、描述符非证明、unknown 禁猜）方向都对，主要缺口不在"说了什么"而在"没说什么"——规则段缺四句各一行的边界补丁（记账非机制/role unknown≠事实不可得/unknown≠弃权理由/电荷按所绘形式算）。化学口径上真正要改代码的只有官能团表两处 SMARTS 不一致（酰胺-胺、羧酸-醇），属确定性小修，建议随本批一起修并升 descriptor 版本号。source 保守取舍认可，v2 首选补系统内可算的 FG delta 而非任何 EC 类语料事实。以上按与程序证据互证采信，不做独立性背书。
