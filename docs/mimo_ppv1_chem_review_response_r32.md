# mimo 化学评审回应 r32（2026-10-10）

- 通道：opencode run -m opencode/mimo-v2.6-flash-free（免费档，通道 A；主会话转发落盘）
- 请求：docs/mimo_ppv1_chem_review_request_r32.md（共底物参与物语义设计评审 CS1-CS6）
- 只读 provenance：评审员以读取工具核对源码/文档，无 shell 执行权限；执行类断言均自带"待执行验证"
- 原始流：docs/review_evidence/ppv1_r32_mimo_2026-10-10/raw.txt
- 采信原则：与程序证据互证为准

---


我先读取设计书与相关源码核对，再输出评审回应。
✱ Glob "docs/mimo_ppv1_chem_review_*_r3*.md" 6 matches
✱ Glob "tests/test_ppv1_s5b_hit50_v3_*.py" 4 matches
✱ Glob "docs/S5B_COSUBSTRATE_PARTICIPANT_SEMANTICS_DESIGN_*.md" 1 match
✱ Glob "src/pathway_v43/pollutant/*.py" 32 matches
→ Read docs/S5B_COSUBSTRATE_PARTICIPANT_SEMANTICS_DESIGN_2026-10-10.md 
→ Read docs/mimo_ppv1_chem_review_request_r32.md 
✱ Glob "docs/mimo_ppv1_chem_review_*_r2*.md" 21 matches
→ Read docs/mimo_ppv1_chem_review_response_r31.md 
✱ Grep "G4-2|R2-2|R2-4|G2-b" in docs/mimo_ppv1_chem_review_response_r30.md · 8 matches
→ Read docs/mimo_ppv1_chem_review_response_r30.md 
✱ Grep "九条件|T1′|白名单|反应物侧" in docs/mimo_ppv1_chem_review_response_r28.md · 22 matches
→ Read src/pathway_v43/pollutant/recorded_source.py [offset=840, limit=160]
→ Read src/pathway_v43/pollutant/recorded_source.py [limit=150, offset=1000]
✱ Grep "participants|render\(|state_id|build_product_state|coproduct" in src/pathway_v43/pollutant/production.py · 31 matches
✱ Grep "def _place_new_atoms|new_atom_unanchorable|add_atom|stereo_edit_unsupported|def compile_donor_template" in src/pathway_v43/pollutant/s5b_compiler.py · 13 matches
✱ Grep "COSUBSTRATE|cosubstrate|coefficient_status|participant_list_status|class Participant" in src/pathway_v43/pollutant/hypothesis.py · 28 matches
✱ Grep "matched_strict|partial|rank" in src/pathway_v43/pollutant/s5b_scoring.py · 41 matches
✱ Grep "matched_participant_coverage_partial|reactants == |from_states|superset|def match_reference_edges" in src/pathway_v43/pollutant/evaluation.py · 12 matches
→ Read src/pathway_v43/pollutant/evaluation.py [limit=75, offset=1030]
✱ Grep "def _record_products_strict|def _executed_components_strict|def strict_identity_of|def _strict_of" in src/pathway_v43/pollutant/recorded_source.py · 3 matches
✱ Grep "corpus|co_substrate|cosubstrate" in src/pathway_v43/pollutant · 0 matches
✱ Grep "corpus|co_substrate|cosubstrate|find_corpus" in src/pathway_v43/pollutant · 0 matches
→ Read src/pathway_v43/pollutant/recorded_source.py [limit=40, offset=645]
✱ Grep "find_corpus_recorded_exact|corpus_cosubstrate|_record_failure|n_cosubstrate" in src/pathway_v43/pollutant/s5b_builder.py · 9 matches
✱ Grep "def strict_identity_of|def cn_identity|MolToSmiles|isomericSmiles|RemoveStereochemistry" in src/pathway_v43/domain/identity.py · 3 matches
✱ Grep "expectation|target_smiles|execution|verify|unknown" in src/pathway_v43/pollutant/production.py · 28 matches
→ Read src/pathway_v43/pollutant/production.py [limit=80, offset=395]
✱ Grep "^### |^## |S5B-V4-01|最低收口" in docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_CODEX_REVIEW_2026-10-10.md · 14 matches
✱ Grep "未知系数|unknown|缺.*映射|中心 unknown|判据二|判据五" in docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md · 40 matches
→ Read docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_CODEX_REVIEW_2026-10-10.md [limit=50, offset=57]
✱ Grep "PARTICIPANT_LIST_STATUSES = |PARTICIPANT_LIST_STATUS_" in src/pathway_v43/pollutant/hypothesis.py · 1 match
→ Read src/pathway_v43/pollutant/hypothesis.py [limit=70, offset=578]
→ Read src/pathway_v43/pollutant/hypothesis.py [limit=75, offset=75]
→ Read src/pathway_v43/domain/identity.py [limit=60, offset=1]
✱ Grep "from ..domain|import strict_identity_of|strict_identity_of" in src/pathway_v43/pollutant/recorded_source.py · 4 matches
✱ Grep "def strict_identity_of" in src · 1 match
→ Read src/pathway_v43/pollutant/chemstate.py [limit=30, offset=905]
✱ Grep "def _identity_key" in src/pathway_v43/pollutant/chemstate.py · 1 match
→ Read src/pathway_v43/pollutant/chemstate.py [limit=25, offset=180]
✱ Grep "transform_no_change|def compile_donor_template|target_smiles" in src/pathway_v43/pollutant/s5b_compiler.py · 5 matches
✱ Grep "coproduct_ignore_tier|composition_only_hydrogen_equivalents" in src · 3 matches
→ Read src/pathway_v43/pollutant/audit.py [limit=40, offset=300]
✱ Grep "^def test_" in tests · 21 matches
# mimo 化学评审回应 r32 —— S5b 共底物参与物显式语义设计（CS1–CS6）

**执行边界声明（先行）**：本轮只用读取类工具（glob/grep/read）核对仓库源码与文档；未运行任何测试或脚本，一切行为类断言标"待执行验证"；引用行号均为**本轮实读**；未访问任何金标/题面/gitignored 目录；未修改任何文件。核对范围：设计书全文、r32 请求原文、Codex v4 复审 §4/§4.3、r28/r30/r31 已裁条款、`recorded_source.py`、`s5b_compiler.py`、`s5b_builder.py`、`production.py`、`hypothesis.py`、`evaluation.py`、`s5b_scoring.py`、`audit.py`、`chemstate.py`、`domain/identity.py`、冻结判据稿相关行、`tests/test_ppv1_s5b_hit50_v3_*.py`（测试名层）。

**两处透明披露（请求体例，与 r29/r30/r31 同款）**：

1. 发来的边界头写"三个判断面（coproduct_ignore_tier 主面 / r27 条款项采纳核对 / stereo 消解型编辑设计复审）"，但附在后面的请求原文是 **r32 的 CS1–CS6**（与 `docs/mimo_ppv1_chem_review_request_r32.md` 实读 184 行逐字比对一致）。该三判断面头系模板复用残留（r30 `:49`、r31 `:63` 已披露同文）。我按**附后的请求原文（CS1–CS6）**逐条作答。coproduct_ignore_tier 本轮全仓 grep `src/` 零命中（仅 `audit.py` 命中 `composition_only_hydrogen_equivalents`，与本评审 CS4b 相关），仍是 proposed 未实施，T1′ 九条件维持 r28 已裁状态不重开庭；stereo 附面不在这份请求里。
2. **行号基准**：设计书自declare行号锚 HEAD `8d92f3a`、成稿时工作树含未提交 v4b 在飞改动（设计书 `:6`）。本轮实读即**当前工作树**，与设计书引用存在同物异行：例如 corpus-retrieval-2 许可拒设计书引 `:878–905`，本轮实读在 `recorded_source.py:931-958`；产物 gate 设计书引 `:1085–1113`，实读在 `:1130-1149`。不判设计错（它自己声明了须重锚），实施轮 D2 必须按届时实际 HEAD 重锚——我下列引用一律为本轮实读行号。

---

## CS1（事件表示与声明式拷贝的化学诚实性）

### 1) 结论

**有条件同意——"声明式拷贝 + 不执行 + 中心 unknown"是现行判据下唯一诚实的表达，相对执行式生成缺的东西被 unknown 如实标注而不是被冒充；但"中心 unknown"作为唯一标签不够，拷贝组分必须另带逐组分"声明未执行"机读状态，且系数全 unknown 在共底物事件上新增三条读法风险须逐条钉死。条件 = R32-CS1-1/2/3。**

### 2) 机理展开

**a) 相对"执行式生成"缺了什么，中心 unknown 够不够。** 缺三样，且三样都被现有 unknown 语义覆盖、没被冒充：① B→拷贝组分这半步**没有被任何执行核验**——事件主张"记录说 NADH 会出来"，不是"系统看着它出来"；判据五"缺/歧义映射 ⇒ 中心 unknown，不猜"（冻结稿 `:407` 实读转引；本轮 grep 实读 `:406-407` 段）+ 决策 R5→retain_conditional（冻结稿 `:222` 实读）是正确的落点，Codex v4 §4.2 `:78` 已实证过同构情形下 audit 不虚授 verified/full/R6（新通道同样预期 unknown/R5，**待执行验证**）。② A→P 与 B→拷贝之间的**计量耦联**（几分子 A 对几分子 B、电子当量是否配）不可核——系数全 unknown ⇒ 判据二元素/电荷账直接 unknown（冻结稿 `:161-164` 实读），设计如实披露 ✓。③ 拷贝组分的**身份**倒是有强事实支撑：它 = 记录产物组分严格身份（`strict_identity_of`→`_identity_key` 同 state_id 事实源，`chemstate.py:913-929` 实读）——所以诚实的完整表述是**"身份=记录声明（可核）、生成=未执行（unknown）"双轴**，单说"中心 unknown"只覆盖第二轴，读者若只看产物清单会把第一轴的可核性脑补成第二轴。

**b) role=coproduct 会不会造成"执行产物"误读——会，且是结构性的，不是教育问题。** 判分 payload 已有一个**纯按 role 聚合**的字段 `coproduct_participants`（`evaluation.py:1054-1057` 实读：`role == "coproduct"` 即入列），下游消费者无从区分"假说内部 coproduct"与"记录声明拷贝"。更要紧的代码事实：现行 expectation 覆盖**全组分**（`s5b_compiler.py:816`"canonical 全组分"、`:981` 实读），即本系统至今"出现在 expectation 里的产物"与"声明产物"是同一批；本设计把拷贝组分挪出 expectation（设计 `:125`）——拷贝组分将成为**第一批带产物角色却不在执行期望内的参与物**，旧读者的默认解读恰好是错的。协议枚举不扩、来源进 provenance 层的路线我认（`hypothesis.py:82-91` 角色枚举、`:96-103` 列表状态实读，无须发明新角色），但披露必须**进数据不进文档**（r31 R31-4 体例）。

**c) 系数全 unknown 在共底物事件上比 EAWAG 型隐式水**多**的读法风险，三条：**

- **"声明齐了"被读成"账配平了"。** EAWAG 型是"一个没写的水"，未知点局部；共底物事件是**两侧多个物种、两侧同时 unknown**，且 union gate 通过 + 产物完整转写（执行 ∪ 拷贝 == 记录）在报告里长得极像"方程已核"。gate 是**组分身份转写核对**，不是配平核验——Codex §4.1 `:5` 对旧 gate 的同一警告原样适用到扩展后 gate。
- **氢/电子账在图上不可见。** 原子归属是重原子图层面的（RDKit 隐式 H、映射在显式原子上——读码推断）；NAD(P)⁺/NAD(P)H 差一个氢负离子、醌/醇差 2e⁻+2H，这些恰是该类反应**机制诊断性最强**的账，全部 unknown。电荷形态（NAD⁺/NADH、NH₄⁺/NH₃）随严格身份保真（`strict_identity_of` 含电荷与立体，`chemstate.py:180-204` 实读），但**总电荷账**同样 unknown。
- **PC-1 自己就踩在这条上**：`CCO.c1ccncc1→CC=O+C1CCNCC1` 按氢计不配平——乙醇→乙醛释放 2H，吡啶→哌啶需要 6H，差 4H（化学计量核算，非执行断言）。重原子归属看不见隐式 H ⇒ 该例**会**走通分类器——这不是设计错（判据二 unknown 正确覆盖），但正控说明文字若不标注"该例元素账 unknown、非已配平"，PC-1 会被读成"配平通过的形态"。附带一个 T-2 相关事实：`participant_list_status` 构造层只校验枚举成员资格（`hypothesis.py:621-624` 实读），无任何配平语义——`source_complete/declared_complete` 的字面（"完整"）在审计轴极易被读成"计量完整"。

### 3) 可直接落进规则文字的修改建议

- **R32-CS1-1（逐组分执行状态进数据，必加）**："拷贝组分在事件/假设载荷携带机读字段 `component_source='record_declared_copy'`，并随事件输出可核对的 `expectation_covered_state_refs`（或逐产物参与物 `execution_status: executed|declared_not_executed`）；判分 payload 的 `coproduct_participants` 字段说明中写明'按 role 聚合，不表示执行覆盖'。拷贝组分身份轴表述为'与记录产物严格身份一致（provenance 可核）'，生成轴表述为'未执行、formation 未核'，两轴不得合并成'已生成/已核实'。"
- **R32-CS1-2（gate 非配平，必加）**："产物多重集 gate（含扩展后 union 语义）只核对组分身份的完整转写，不是元素/电荷配平核验；凡 gate 通过处不得表述为'配平通过/元素账已核/来源已闭合'，配平轴状态恒为判据二 unknown（系数全 unknown）。"
- **R32-CS1-3（T-2 措辞，随 T-2 一并交 teacher）**："无论 `participant_list_status` 取 source_complete 或 declared_complete，均只描述**参与物清单完整度**，不描述计量/配平完整性；报告中该字段必须与 `stoichiometry_status=unknown` 类机读注记同位出现。"（设计倾向 declared_complete 我附议：`source_complete` 的'源侧完整'字面对'系数全 unknown 的清单'是过强声明。）

### 4) "程序上诚实但化学上误导"风险点

- **风险 1（最实）**：`coproduct_participants` 按 role 聚合 + 拷贝不进 expectation，程序两侧各自诚实、合起来给下游"coproduct=执行产物"的默认解读——字段语义与新形态脱节，必须靠 R32-CS1-1 的 in-band 标签。
- **风险 2**："声明完整（source_complete）+ gate 通过"并排出现 ⇒ 读成"该步已配平核验"；实际上 H/e⁻/电荷三本账全 unknown。
- **风险 3**：PC-1 合成例氢不配平却被断言为"编译成功+partial 正控"——正控本身诚实（unknown 覆盖），说明文字缺标注即成误导样板。

**不确定项**：新通道下 audit/admission 的实际 disposition（预期 R5/retain_conditional，同 Codex §4.2 先例）——待执行验证；隐式 H 是否绝对不进归属枚举——读码推断（RDKit 图语义），待实施核对。

---

## CS2（键合贡献保守拒）

### 1) 结论

**有条件同意——在"现行执行契约 + r30 R2-2 已裁字面"下整候选保守拒是本轮正确的保守选择，无例外放行；但设计的理由文字把"物理不可能"与"规则禁止"混为一谈（须改写），错杀的化学类目必须显式点名并披露与 EAWAG 面的书写风格不对称，拒因三分不足以支撑机制轮立项决策（须四轴细分），另有一条设计未覆盖的形态（可执行子集为空）须补规则。**

### 2) 机理展开

**a) 理由链完整性与错杀审查。**

理由链逐环核：执行图 = render(底物)（`production.py:288` 实读，冻结 0d.1 固定链）⇒ B 不在图内 ⇒ 想让 B 原子进产物只能 add_atom（`s5b_compiler.py:727` 实读：新原子一律 `add_atom`，无锚则 `:711` new_atom_unanchorable）⇒ R2-2（r30 `:119`："共底物来源组分不得经 add_atom 执行通道从底物原子生成"）禁之 ⇒ 键合融合在**现契约+现裁定**下无诚实表达。"声明融合产物+部分执行 ⇒ 诊断真失配"一环也成立：执行输出 ≠ 声明产物是 violated/方法失败级（比 unknown 更差），设计选拒正确。

**但文字要修**："add_atom 即伪装/无中生有"在**来源未声明**时严格成立（Codex §4.2 反例：事件根本没写 CC）；在**来源已声明**（B 已进反应物侧）时，add_atom 实为"有来源的执行"，其被禁是 **R2-2 字面的无条件禁止**，不是物理不可能。两者混写，未来若要给"已声明来源的单原子插入"开例外，就找不到准确病灶——那需要**独立修订 R2-2 的评审轮**，本轮不开口。

**你认得的、被错杀而"整组分拷贝"救不回的形态（三类，全部同根拒，设计未点名）**：

1. **已声明水的水解/水合**：RHEA 平衡式把 H₂O 写进 donor 时，水的一个氧以**键合**形式落入酸/醇类组分（酯水解：产物 3 个 O = 酯 2 + 水 1，水氧必在某个含 A 原子的组分内）⇒ 混合组分 ⇒ 拒。离去侧对应组分仍是整组分（醇）的事实救不了含水氧的那个组分——**"整组分拷贝"只覆盖断连对应物，不覆盖同组分内的键合贡献**，设计这点没说透。
2. **已声明 O₂ 的单加氧酶/羟化酶 O 插入**：插入氧来自 B、键合进 A 骨架 ⇒ 混合 ⇒ 拒。注意氧化酶型（A+O₂→A′+H₂O₂，H₂O₂ 断连）**可解锁**（H₂O₂ 全 O 可溯 O₂ ⇒ copy）——同是"加氧"化学，断连产物者开、键合插入者拒，这个分界必须进披露。
3. **转移酶**：SAM→SAH、Acetyl-CoA→CoA、ATP→AMP+PPi 这些"离去侧整组分"确实被 copy 覆盖 ✓，但**转移基键合进底物产物**的那半步照旧拒——甲基化/酰化/腺苷酰化全在拒面。

**关键披露义务（r31 R31-3 的延伸，P1 级措辞）**：同一条"酯→酸+醇"化学，corpus 面（记录写了水）在本设计下**bonded 拒**，EAWAG 面（记录没写水）**照旧 add_atom 放行且授 matched_strict**（r31 H1b `:86` 实读转引、本仓 `tests/…_wv2.py:67` hydrolysis 型正控名实读）。treatment 仍随记录书写风格翻转——诚实拒轮如此、本设计落地后仍如此，报告并列时必须同句披露。

**设计未覆盖的形态**：可执行子集为空（全部产物组分含 B 原子，或产物全是拷贝）⇒ `expectation.target_smiles` 无对象、编译无处落——设计通篇未写该分支的处置（`transform_no_change` 在 `s5b_compiler.py:285` 管的是"整体无变化"，相邻但不同）。须补结构化拒类目。

**b) 拒因三分够不够支撑"哪类该立项机制轮"——不够。** 键合/不可锚/不可归属只回答"拒在哪道门"，不回答"机制轮该先做哪个"。立项要看的至少四轴：①键合内部拆**单原子插入 vs 多原子转移基 vs 骨架并入**（前者未来只需"已声明来源 add_atom"的 R2-2 修订案，后者需要 B 入执行图/模板扩展——两种完全不同的工程）；②记录配平态（配平者是源数据可信的真化学，不平者先修数据）；③B 类别（辅因子对/有机转移体/无机小分子——NAD(P) 系已在整组分面解锁，键合面的主力是转移酶与氧ase）；④B 身份是否原样出现在产物（旁观/往返 vs 被消耗）。不可锚类现在已被整组分拷贝路径**吸收**（断连辅因子不再靠 unanchorable 拒），该类目会从直方图迁移消失，须注明"是放行不是消失"。

**c) 我要什么探针才裁"保守拒的供给代价可接受"。** 只读聚合、零金标、隔离副本执行（AGENTS.md 审核隔离纪律），对 1,323 个 component-with-cosubstrate 候选跑**分子式配平 + 身份配对**代理分类（不需要原子映射，不需要逐题内容）：

- 四分类交叉：①元素配平（A+全部 B vs 全部产物，全元素含 H；系数无则按 1 记并标 unknown）三态；②是否存在产物组分严格身份 == 某 B 身份（整组分往返/拷贝形态强代理）；③产物中是否含 A∪B 不存在的元素（不可归属强代理）；④配平但无任何产物组分等于 B（⇒ 键合转移强代理）。
- 输出全部为聚合计数：1,323 条目的四分类计数 × **题级 distinct 覆盖数**（204/267 内各子类各覆盖多少题）× B 类别（balance_like/organic_like/NAD(P) 系）交叉；再加"这些题当前池是否已有 strict 供给"的聚合差值（供给边际，v4-R1 §六体例）。
- **最低证据线**：拿到"可解锁子集（②形态且配平）的题级 distinct 覆盖数"之前，任何"代价可接受"都是猜——§十二.1 已登记 unknown 是对的，D2 前置执行该探针我认作**裁供给代价的必要条件**（探针结果只进聚合计数，不碰金标）。

### 3) 可直接落进规则文字的修改建议

- **R32-CS2-1（理由文字改写）**："键合融合拒的机理分两层如实分写：物理层——执行图不含 B，现行执行契约下不存在产生 B-键合原子的执行路径；规则层——R2-2（r30 已裁）禁止共底物来源原子经 add_atom 通道产生，该禁令**无条件适用于已声明来源**（'伪装'一词严格限定于来源未声明的伪造形态）。两层各自独立成立，任何一层的未来修订都须独立评审轮，不得以另一层为由放宽。"
- **R32-CS2-2（错杀类目点名 + 不对称披露）**："保守拒覆盖并须在诊断/报告中点名三类已知损失化学：已声明水的水解/水合、已声明 O₂ 的键合氧插入（单加氧酶/羟化酶型）、转移基键合进底物的转移酶型；氧化酶型（断连 H₂O₂ 产物）与脱氢酶型（断连辅因子对）不在损失面。同化学在 EAWAG 面（记录未声明参与物）与 corpus 面（已声明）treatment 不同的事实，沿 R31-3 同句披露。"
- **R32-CS2-3（拒因四轴细分，工程级零判据）**：在 `cosubstrate_bonded_contribution_unsupported` 下挂机读子标签 `bonded_kind: single_atom_insertion|group_transfer|skeleton_merge`、`record_balance_status`、`b_class`、`b_identity_in_products`，供机制轮立项排序。
- **R32-CS2-4（补缺失分支）**："可执行子集为空（无任何产物组分原子全部 A-可溯）⇒ 结构化拒（建议类目 `cosubstrate_no_executable_product_subset`），不得产空 expectation 事件、不得把整产物集降级为拷贝绕行（那等于纯记录转写冒充预测）。"

### 4) "程序上诚实但化学上误导"风险点

- **风险 1**："add_atom 即伪装"若原样落字，读者会以为**所有** B-键合形态都是化学上不可表达——真话是"在 R2-2 现字面下不许可"；把规则状态写成物理状态，会封死未来合法修订的讨论空间（且反向暗示现在放行的 EAWAG add_atom 水氧"是伪装"——按 R31-1 它不是，是记录简写）。
- **风险 2**：拒因直方图三分不带四轴子类 ⇒ 下一轮立项者拿"键合拒 800 条"既论证不了机制轮方案，也论证不了"数据都坏了"。
- **风险 3**：锁在 §十二.1 的 unknown（整组分/键合占比）若被口头填补成"应该大多是整组分"之类印象数——在探针跑出来前，任何口头占比都违 §三.5（计量不外推）。

**不确定项**：1,323 内三类损失化学的实际占比——unknown，缺上述探针；RHEA 行实际把 H₂O 写进 donor 的频率——读码+经验推断，未确认，探针②可顺带产出。

---

## CS3（原子级守门与 gate 扩展）

### 1) 结论

**a) 保守拒（子选项 i）是化学上对的处置，同意——但"不可归属"含一种映射回退伪影成因必须子类披露；b) union gate 方向安全、拷贝篡改挡得住，但我实读到一处"同源"声明与代码不符的键空间问题，且 gate 只核 spec 层不核事件层，须补事件级端到端不变量；c) PC-1 断言方向（partial 非 strict）认，且应加强为断言具体桶；另必加 4 条正控、5 条负控。**

### 2) 机理展开

**a) 子选项裁决：i（保守拒）。** 三重理由：①分界正确——记录**已声明** B 仍缺原子，不是 R31-1（r31 `:98`）的"记录根本没写"形态；放行（ii）等于系统替记录**补来源主张**，而判据二对系数 unknown 只给 unknown、无守门（r30 G2-c `:112` 的结构弱点原样在场）——缺的原子要么被推断映射错归给 A、要么悬空，两种都是化学上替源数据圆谎。②与 R3-2 正交同意：R3-2 管两侧元素平衡（适配层），本门管产物原子归属（编译层），两门对"记录自坏"都拒、方向都是收紧，不互相替代（设计 §八.2 `:246` 我认）。③**但要拆一个第三成因**：`infer_reaction_mapping` 有 bond-diff 回退分支（`recorded_source.py:645` `_infer_bond_diff_fallback` 实读）——回退映射产生伪 `new_union` 的可能与"源数据真缺原子"在拒因上不可区分。直方图若不带 `mapping_fallback` 标注，"源数据不配平"的立项结论会被映射伪影灌水。

**b) union gate 漏洞审查，四处：**

1. **键空间不同源（实读发现，设计"同源"声明有一处不实）**：设计称三函数族同源（`strict_identity_of`/`_executed_components_strict`/`_record_products_strict`）。实读：记录侧 `_record_products_strict` 走 `strict_identity_of`（`recorded_source.py:649-656`），但执行侧 `_executed_components_strict` 走**裸 `Chem.MolToSmiles(frag)`**（`:659-667`），不经 `_identity_key` 的 CX 规范化与未登记 CX 类拒绝（`chemstate.py:180-204` 实读）。普通分子两键重合；含 CX 注记/增强立体/同位素注记的输入可能不等。拷贝并入 union 后比较的**两侧键必须统一**（执行侧改走 `strict_identity_of`，或加键一致性断言）——实施轮必核。
2. **"拷贝串被换"挡得住**：拷贝身份与记录产物同源派生，严格身份多重集对账足以挡（NC-4 ✓；并集不齐/交叠超集皆 fail-closed，`declared_copy_mismatch`/`product_set_mismatch` 语义够）。
3. **gate 只核 spec 层，不核事件层（真正的口子）**：链是 spec→`prepare_hypothesis`→event；gate 过了不等于提交事件带齐参与物。后果不对称可利用：**只丢产物拷贝** ⇒ 反应物 B 还在 ⇒ 仍 partial（无害）；**B 与拷贝同丢**（states 扩展漏、装配分支漏）⇒ 事件退化为 A→P ⇒ 可 exact ⇒ **恰好回到 R2-2 要禁的形态**，且 add_atom 负控抓不到（B 若对产物零贡献
Error: Connection lost while reading the response: ECONNRESET: The socket connection was closed unexpectedly. For more information, pass `verbose: true` in the second argument to fetch()
→（B 若对产物零贡献，edits 里根本没有 B 原子，add_atom 负控对这条退化路径**空转**）。所以必须补**事件级端到端不变量**（不只是 spec 级 gate）：凡 component-with-cosubstrate 候选产出的已提交事件，`记录 co_substrates 的严格身份 ⊆ 事件 reactant 侧 role=cosubstrate 的 state_refs` 且 `记录产物多重集 == 事件 products 多重集（执行 ∪ 拷贝）`，触发即红。PC-1 只在单个合成形态上断言了这件事，要升为对全候选类的通用断言。

4. **fail-closed 方向核对（读码推断）**：实现若忘传 `declared_copies`（走缺省空），执行侧子集 ≠ 记录全集 ⇒ `product_set_mismatch` 拒——忘传的方向是**安全的拒**，不是漏放；反向（拷贝误入执行侧）由 union 超集拒 + NC-3 挡。方向性设计（子选项 i 缺省空 ⇒ EAWAG/整串字节等价，`recorded_source.py:1062-1149` 实读该函数无任何 corpus/共底物分支）我认，"字节等价"本身待执行验证。

另记一条口径纪律：gate 是**多重集**比较（`:1130-1141` 实读，list 保留重复），P1 判分是**集合**语义（`evaluation.py:1062-1068` 实读 set 比较；r28 A4 已订正过一次两口径混写）——报告不得把"多重集相等"措辞溢出到判分面。

**c) 控件矩阵审查。** **PC-1 的断言方向（断言 partial、不断言 strict）我认，且是本设计最重要的正控**——它把"解锁的是诚实 partial 不是 strict 收益"从文档承诺变成机器事实。加强两点：断言要钉到**具体桶**（`match_status == matched_participant_coverage_partial` 且 `!= matched_strict` 且 `!= unmatched/matched_structure_only`）——只断言"非 strict"会把"掉出匹配"误读成 partial；以及 PC-1 说明文字补 R32-CS1-2 的"元素账 unknown 非已配平"注记（该例按氢计不配平，见 CS1c）。

必加控件（缺的）：

- **PC-4 旁观已声明共底物**：B 在反应物侧声明、产物集不含任何 B 原子、全部产物 A-可溯 ⇒ 编译成功、零拷贝、事件含 B、冻结匹配落 partial、断言不落 strict。这是 r31 R31-2 登记形态在本设计下的正解落点，现在矩阵里没有它。
- **PC-5 多共底物记录**：A+B1+B2 → P+copy1+copy2，两个 B 全声明、两个拷贝全带来源字段，partial——防实现只装配首个 co_substrate。
- **NC-8 可执行子集空** ⇒ 结构化拒（配套 R32-CS2-4 的缺失分支）。
- **NC-9 拷贝注入 expectation/edits**：把拷贝组分串塞进 `expectation.target_smiles` 或 edits ⇒ 拒——NC-3 只覆盖 add_atom 通道，设计 §四.3.4 禁止事项（`拷贝不得出现在任何 edits/alignment/expectation 字段`）没有对应控件。
- **NC-10 事件级不变量**（CS3b-3 的机器兑现）。
- **NC-11 拷贝身份用 cn 派生**（电荷归一/立体盲，`domain/identity.py:46-55`）⇒ 必须 `declared_copy_mismatch` 拒——拷贝只认 strict，防实现图省事走 cn。
- **NC-12 批级熔断**：本通道 `matched_strict` 计数恒 == 0（现行 P1 下的结构性不变量，出数即口径漂移或实现 bug，红）。
- **键空间一致性断言**（CS3b-1）并入 NC 族。

PC-2（零回退）、PC-3（同签名合并）认可，无增补。

### 3) 可直接落进规则文字的修改建议

- **R32-CS3-1（子选项裁定落字）**："不可归属原子处置裁定为保守拒（子选项 i）：记录已声明 B 仍有产物原子归不进 A∪B ⇒ 源数据缺来源，非 R31-1 隐式来源许可范围（该许可仅覆盖记录未声明参与物的形态）；拒因子类必须带 `mapping_fallback: true|false` 标注，区分 bond-diff 回退映射伪影与源记录真实缺原子，两类计数分列，不得合并为'源数据不配平'单一结论。"
- **R32-CS3-2（键空间同源）**："union gate 两侧身份键统一到 `strict_identity_of`（`_identity_key` CX 规范键）：执行侧组件提取（现行裸 `Chem.MolToSmiles(frag)`）必须同源化或附键一致性断言；'同源不另写比较器'的交付证据含该断言。"
- **R32-CS3-3（事件级端到端不变量，必加）**："component-with-cosubstrate 事件提交前断言：记录声明的全部共底物严格身份 ⊆ 事件 reactant 侧 cosubstrate state_refs，且记录产物多重集 == 事件产物参与物多重集（执行组分 ∪ 声明拷贝组分）；spec 层 gate 通过不替代事件层核对，任一不满足即测试红（NC-10）。"
- **R32-CS3-4（控件矩阵增补）**：PC-4/PC-5、NC-8..NC-12 按上文 c 节纳入设计书 §五.4 矩阵；PC-1 断言加强为具体桶 + 元素账 unknown 注记。

### 4) "程序上诚实但化学上误导"风险点

- **风险 1**：直方图把 bond-diff 回退伪影与真实源数据缺陷混进 `cosubstrate_atom_source_unattributable` 单类 ⇒ 下游读成"corpus 源数据大面积不配平"——程序诚实（确实拒了），归因化学上误导。
- **风险 2**：报告写"三分类守门闭合原子来源"——闭合的是**已声明组分**的归属核对；未声明来源（EAWAG 面水氧）照旧经 add_atom、元素账 unknown（R31-1 边界原样适用），任何"事件不再有无来源原子"表述 = P1 级错误（r31 R31-6 禁句沿用）。
- **风险 3**：gate 过 + 事件级不变量缺位时，"gate 通过"被读成"参与物声明已消费"——恰是 Codex S5B-V4-01 的教训（gate 不回答声明是否进事件，Codex §4.1 `:68`：`production.py:209-245` 不消费 corpus 元数据——本轮 `:209-212` 实读确认显式覆盖路径存在但**消费与否取决于装配实现**，待实施验证）。

**不确定项**：键空间两函数在普通输入下的实际一致率——待执行验证；事件级不变量在现行 builder/production 链的落点——未确认（须实施轮入口矩阵先行，AGENTS.md 返工教训 1）。

---

## CS4（T1′ 边界与激励倒挂）

### 1) 结论

**a) 两步洗白已被"设计条款 + r28 T1′ 边界"联合封死，但剩三个口子（白名单内容缺机器挡板、D-T1′-3 与 T1′① 在声明拷贝子集上读法分叉、方向绑定与 H₂O 特例的冲突）须落字；b) 补全许可不延伸条款必要，且可直接锚到已存在的机器对象，但要补反应物侧对称句；c) 防线不该只有落字——还差三条机器/报告层防线（通道归因、批级熔断、同表并排），全部不触冻结判据。**

### 2) 机理展开

**a) "A→P+NADH 洗成 strict"两步的封死状态与剩余口子。**

- **产物侧（忽略 NADH 型拷贝）**：NADH 是含碳辅因子，r28 T1′①⑥（白名单仅无机小分子、辅因子恒不忽略，r28 `:150`）文本挡住——白名单碰不到它。**封死成立，但只是文本封死**：真正的机器动作是"往 `exempt_identity_hash` 里加身份"，唯一挡板是白名单内容规则的执行。
- **反应物侧（忽略 NAD⁺ 型 B）**：T1′② 反应物侧仅 H₂O 特例（r28 `:60`），NAD⁺ 不在任何豁免面。**封死成立。**
- **剩余口子三条**：
  1. **白名单内容缺机器断言**：建议把 T1′①⑥ 机械化——`exempt_identity_hash` 内任何**含碳身份**即非法（机器断言），辅因子身份（NAD(P)(H)/FAD/FMN/AMP/ADP/ATP/CoA/THF 系）硬拒绝表，不依赖 teacher 每次手读。"声明参与物重分类为可忽略差集"的实际发生方式就是"把某身份加进白名单"——身份即闸门。
  2. **D-T1′-3 与 T1′① 的读法分叉**：设计 `:199` 说声明拷贝与"可忽略差集"**互斥**；但 T1′① 的 extras 定义 = 事件组分 − 参考边声明组分（r28 `:105`），声明拷贝（如 H₂O/CO₂/卤离子型）**本来就是** extras。两读法后果不同：按 D-T1′-3 字面，tier 对声明事件**更严**（连白名单水都不豁）；按 T1′① 字面，诚实声明水的拷贝可豁——后者恰是修复倒挂的方向（诚实声明反而拿到豁免）。这不是我已裁条款的冲突，是**新歧义**，须在 T-1 裁定时二选一落死，否则实现者任选都不算违反设计书。
  3. **方向绑定与 H₂O 特例冲突**（详见 CS6b）：水解 A+H₂O→P 时水无产物侧对应组分，"必须成对"字面使 T1′② 特例永不可用。
  - 附带把 pairing 的作用说准：**单侧豁免在数学上到不了 strict**（exact 要求两侧集合同时相等，`evaluation.py:1062-1068` 实读——只清反应物侧则产物侧仍超集、只清产物侧则反应物侧仍超集）。pairing 真正防的是披露/语义不对称与未来参考侧部分声明时的单侧豁免，**不是洗分的唯一闸**——主闸永远是白名单内容。别把 pairing 当充分条件写。

**b) 补全许可不延伸——必要，且设计文字可以锚到真机器对象。** `COMPLETION_LICENSED_IDENTITIES` 现仅 `[H][H]` 与 `[H] |^1:0|`（`audit.py:310-313` 实读），未登记身份 ⇒ `partial(completion_license_unregistered_identity)`（`:304-307` 实读）——即**今天**有机共底物组分本来就拿不到覆盖 full。D-T1′-2（设计 `:195`）的真实作用是**封死未来扩列**（供给压力下把 NADH 身份注册进集合 = 判据三许可边界变更，源码注释自declare"许可边界变化待审" `:308`）。表述缺口两处：①没点名机器对象（扩列动作没有落点句）；②只对**拷贝组分**写死"coverage unknown_coefficients 一条路"，**反应物侧 B** 没有对称句（B 的系数同样恒 unknown，同样不得经任何补全许可拿 known/full）。

**c) partial 桶膨胀的防线——不该只有落字，四条全部可加且零触冻结判据：**

1. **通道归因进判分输出**（供给/报告层）：本通道事件带机读 channel 标签，`matched_participant_coverage_partial` 可按成因分解（含 `cosubstrate_declared_superset` 计数）——防"partial=设计缺陷"归因，也让 R2-4 疫苗（r30 `:121`）可机读核查。
2. **批级熔断断言**（机器层，同 NC-12）：本通道 matched_strict 恒 == 0。这是**现行口径的不变量断言**不是新判据——出数只可能来自口径漂移或实现 bug，红即停。落字防人、断言防代码漂移，两者不可互替。
3. **D-M-1 与 partial 计数同表并排**：`hit@1 预期贡献=0` 不许脚注化——任何发布 partial 计数的表，同行同位给 D-M-1 句与通道标签。
4. **拒因迁移前后对照保留**（1,323 分裂可见，R31-6 禁句沿用）：防"解锁"被读成"错误修复"。

不建议的"防线"（明确否掉）：压发事件、延迟入桶、给本通道 partial 单独降权——都是以诚实换数字，违 R2-2 第五要点与判据一。

### 3) 可直接落进规则文字的修改建议

- **R32-CS4-1（白名单机器挡板，随 T1′ 实施生效）**："coproduct_ignore_tier 若裁定实施，`exempt_identity_hash` 内含碳身份即构造非法（机器断言，触发即红）；辅因子恒不忽略（r28 ⑥）落地为硬拒绝身份表，不依赖逐批复核。"
- **R32-CS4-2（D-T1′-3 歧义消解，随 T-1 落定）**："声明拷贝组分与忽略差集的关系二选一写死并进预注册：（读法 A）声明参与物永不可被 ignore-tier 豁免——tier 对声明事件更严；（读法 B）tier 按身份作用于产物侧 extras、与来源无关——声明的白名单无机拷贝可豁。两读法后果差异（诚实声明水的 strict 可达性）须在 T-1 裁定记录中显式声明，不得留给实现者选择。"
- **R32-CS4-3（D-T1′-2 补两处）**："……不得向 `COMPLETION_LICENSED_IDENTITIES`（audit.py 现仅 H₂/[H]）新增任何含碳或辅因子身份；该集合任何新增 = 判据三许可边界变更，须先经 mimo 场景 1 评审 + teacher 裁定。**对称句**：反应物侧已声明共底物参与物的 coverage 语义同样只有 unknown_coefficients 一条路，不因'记录声明了它'而给 known。"
- **R32-CS4-4（四条防线落字）**：按上文 c 节 1–4 逐条进设计书 §六/§七（工程与报告层，零判据变化）。

### 4) "程序上诚实但化学上误导"风险点

- **风险 1（最实）**："T1′ 已封死洗白"作为结论出现——真实状态是**文本封死 + 一台未装配的机器**（tier 未实施、白名单哈希未生成）；将来实施时若没有 R32-CS4-1 的构造非法断言，"加一个身份"就是一次静默滑坡，报告层看不出任何违规。
- **风险 2**：D-T1′-3 的"互斥"被实现者读成 T1′① 的同义重复（毕竟两处都在说产物侧）——两种实现都合规、行为相反，首批生效批的 strict 计数会差一截，事后无法归因。
- **风险 3**：partial 膨胀期若报告只给 partial 总数不给通道分解，下一轮任务书起草者拿"partial 大涨"当缺陷清单，直接推动忽略档扩列——r30 G4-2（`:182`）警告的滑坡就是这条传导链，防线 1/3 是它的断链点。

**不确定项**：tier 实施形态（若立项）的 extras 计算位置与消费链——未确认（零实施）；四条防线的落点字段名——建议级，实施轮定。

---

## CS5（计量与披露语义）

### 1) 结论

**a) 对——落既有 partial 桶、不设新判分桶是唯一与冻结口径零冲突的选择，成因分层只进供给诊断正确；b) 现有披露防得住"partial=设计缺陷"的一半，防不住"拷贝=已执行"（须逐组分执行状态字段）与单位混排；c) 还需五处措辞/标签钉死（含两处新增禁句）。**

### 2) 机理展开

**a) 桶归属核对（读码确认）**：事件反应物侧 ⊋ 参考 from_states、产物侧 ⊋ 参考 to_states ⇒ `participant_coverage = "superset"`（`evaluation.py:1062-1068` 实读）⇒ `coverage_mismatch_events` ⇒ `matched_participant_coverage_partial`（`:1077-1080` 实读）；rank 只认 matched_strict、非 strict 一律 rank=None（`s5b_scoring.py:654` 实读）。另有两条边界情形也落同一 partial 桶、不出桶：参考侧含事件未声明的组分 ⇒ `partial_subset`（`:1068`）；必要节点由超集天然覆盖（`:1036-1040` 侧别敏感预过滤实读）。**不设新桶的判断正确**——新桶 = 判分口径变更 = P1 邻接面，成因信息属诊断层。须同时落字一句：本通道"结构性无 strict 通路"是 P1 集合相等语义的**推论**，不是本通道判定缺陷（防反向解读成"该通道命中能力坏了"）。

**b) 三类误读的防护缺口**：

- **拷贝=已执行**：`declared_copy_components` + 聚合计数是**最小机读面、不够**——它是 detail 里的来源清单，不回答"哪些产物被执行覆盖"。而判分 payload 里现成的 `coproduct_participants`（`evaluation.py:1054-1057`）按 role 聚合、天然被读成执行产物（CS1b 同源）。缺的是**逐事件的执行覆盖可核字段**（`expectation_covered_state_refs` 或逐产物 `execution_status`）。
- **partial=设计缺陷**：通道归因 + 同批对照（CS4c-1）是关键；设计 §4.4 风险表与 §六.4 落字是文档层，须升到数据层。
- **204=strict 可达面**：碳代理标签已钉 ✓（§七.2.3），§十二.1 的二分 unknown 登记 ✓——但**引用纪律**要写死：凡引 204，同句必须带"整组分/键合二分探针未跑、可解锁子集 unknown"，不得只带"碳代理"标签（只带代理标签仍可能被读成"里面大部分能解锁"）。**单位**：1,138+245+111 = 组分级频次（次）、204/267 = 题数、1,323 = 题×候选条目（r31 口径）——三个单位禁止同表混排，各带 `count_unit` 标签。

**c) 还需钉死的措辞（在设计已沿用 R31-4/R31-6 体例之上）**：

1. `n_cosubstrate_*` 系列字段一律带 `count_unit` 与 `count_basis`（检索面/池面/判分后）双标签；
2. 直方图迁移注明"编译成功子集从拒因直方图消失 = **放行不是消失**，其计数改由 `n_cosubstrate_declared_events` 承接"（防"键合拒/不可归属拒"之外的第三类被读成归零）；
3. 新增禁句：①"共底物通道解锁供给"（无限定词——必须带"子集占比 unknown"或具体探针数）；②"gate 通过 = 配平通过/来源闭合已核"；③"拷贝组分已生成/已验证"；④"partial 改善"单独出现（必须并排同批 strict 计数）；
4. `tier_count_semantics` 沿用 ✓（r31 R31-4），`includes_precompile_permission_rejects` 沿用 ✓——两标签须覆盖**拆分后**的全部新拒因类目；
5. hit@1 预期贡献=0 与 partial 计数同表（CS4c-3）。

### 3) 可直接落进规则文字的修改建议

- **R32-CS5-1（桶归属落字）**："本通道事件落既有 `matched_participant_coverage_partial` 桶（超集分支），不设新判分桶；分母 298、rank 口径、hit 定义零变更。本通道在现行 P1 下结构性无 strict 通路是集合相等语义的推论，不构成本通道判定缺陷；任何'该通道命中退步'类表述为禁句。"
- **R32-CS5-2（执行覆盖字段）**：并入 R32-CS1-1。
- **R32-CS5-3（单位与引用纪律）**：按上文 c-1/c-3 落字，含"引 204 必带二分 unknown 句"。
- **R32-CS5-4（迁移承接句）**：按 c-2 落字。

### 4) "程序上诚实但化学上误导"风险点

- **风险 1**：三个单位（次/题/题×条目）同表混排，读者做减法得出"解锁题数"——r30 G4-1 老病（`n_*` 与 `n_pool` 并排做减法）的同源复现。
- **风险 2**：拒因直方图里键合拒类目"越修越少"被读成质量改善——实为门的开关迁移，同 R31-6 的 310→18 教训。
- **风险 3**：`n_cosubstrate_partial_matches`（判分后 partial 计数）与 hit 数值近旁出现时被并读成"命中改善"——字段名带 partial 语义标签不够，须同表 D-M-1（CS4c-3）。

**不确定项**：判分 payload 实际会携带哪些事件级字段——未确认（实施轮定）；上述字段建议均为最小面，实施可增不可减。

---

## CS6（预注册路径与口径级护栏）

### 1) 结论

**a) 四元组草案缺一件已裁必需品——r28 T1′⑦ 的追溯开关被 disclosure_switch 顶掉了（与我已裁条款冲突，须恢复）；辅因子对 NAD(P)⁺/H 在 v1 下任何条件都不该进豁免清单（类别错误），只应走参考侧声明路线；b) 双侧绑定必要但不充分——主闸是白名单内容（CS4a），且成对要求与 H₂O 反应物特例正面冲突，须 carve-out；c) 长线参考侧 `omitted_coproduct_scope` 是本题域正解，短线豁免档只配当过渡件并写退出条件。**

### 2) 机理展开

**a) 四元组缺件与 NAD(P)⁺/H 裁定。**

- **冲突（规则级，与 r28 已裁条款）**：r28 C1 明文四元组 = 档位 + 白名单 cn 身份版本哈希 + 方向策略 + **追溯开关**（r28 `:102`、`:150` ⑦——追溯前提即 T1′③"杂原子须见于声明反应物侧"的载体）；设计 §9.1（`:257-261`）的四元组 = tier + exempt_identity_hash + direction_policy + **disclosure_switch**。追溯开关被披露开关顶替——而披露已由生效护栏 ⑧（post-hoc 敏感性表+逐边 `exempted_participants`）覆盖，追溯前提却**从结构里消失了**。无追溯前提的白名单 = r28 B1 点名的"元素不可能的计量洗 strict"通道（无卤底物的事件写 Cl⁻、无磷来源写 PPi）。**须恢复**：恢复追溯开关（回到 r28 原案）或改五元组，二选一，不得静默丢件。
- **辅因子对 NAD(P)⁺/H 该不该进 `exempt_identity_hash`：不该，且在 ppv1-criteria-v1 下不存在"什么条件下进"。** 化学理由：脱氢酶/氧化还原步的电子受体身份是**机制主张的核心变量**（NAD⁺ vs NADP⁺ vs 人工受体决定该步是否发生、选择性如何），豁免它 = 系统性主张"这步不需要电子受体"——r28 A6、r30 G4-2 同一根。且看通路：豁免的目的是让事件回 strict；参考边**剥除**辅因子是提取口径，正解是让参考边**声明**它们（CS6c 长线）——参考侧声明后两侧自然相等，**豁免不再被需要**。所以"进清单"不是有待调参的档位，是类别错误：正确的修复路线自动取消该需求。若 teacher 仍立此项，按设计 §9.2 `:266` 已写明的走 ppv1-criteria-v2 新版本流程——本设计不预支批准 ✓（我复核无预支）。
- 无机离子 cn 往返稳定性逐条验证（r28 `:102`）仍是落地前置，未验证——待执行验证。

**b) 双侧绑定够不够挡单侧洗白。** 数学上单侧豁免到不了 strict（CS4a 已证），所以 pairing **必要但不是主闸**；它挡的是另一半：有 copy 无 B 声明（或反之）的**披露不对称**，以及未来参考边部分声明时的单侧豁免怪形态。两处要补：

1. **与 T1′② 的正面冲突**：方向策略字面要求"反应物侧声明共底物 + 产物侧其来源整组分成对"（设计 `:260`）；水解 A+H₂O→P 中水是**被消耗**的反应物、产物侧无 H₂O 对应组分 ⇒ 成对要求使 T1′② 的 H₂O 特例（r28 `:60`，我给的理由就是水解类诚实声明的可达性）**永远不可用**。与已裁②冲突，须显式 carve-out："成对要求适用于存在来源产物组分的共底物；反应物侧 H₂O 特例（T1′②）不受成对约束。"
2. **旁观型共底物的后果要写明**：B 声明了但对产物零贡献（无 copy）⇒ 按成对规则不可豁 ⇒ 恒 partial。方向保守、可接受，但须如实落字（否则实现者会试图给它"造对"——比如把 A 产物里某个组分错标成 B 的来源组分，反而制造新漏洞）。

主闸重申（给足优先级）：白名单含碳构造非法（R32-CS4-1）+ 追溯开关恢复 + 辅因子硬拒绝表 —— 这三条是防洗分的实体；pairing、披露开关是纵深。

**c) 长线 vs 短线：长线（参考侧 `omitted_coproduct_scope`）是本题域正解。** 化学理由：

- 豁免需求的本质是**参考提取口径与事件声明口径不一致**（A1 错配），不是分子的属性。分子白名单是**无上下文**规则：Cl⁻ 在脱卤步是必须出现的真实产物、在别的反应里是背景盐——同一身份两种化学命运，白名单只能二选一；追溯前提只是启发式补丁，补不齐方向、机制、生理背景这些上下文。
- 按边声明"剥了什么"把口径差**逐边记录并版本化**：不漂移（范围是参考自己的声明，不是判分子类别）、不反向要求（参考声明什么就比什么）、不需要每轮 teacher 重审白名单。
- **激励倒挂的根也在参考侧**：倒挂 = 参考简写与事件诚实声明的书写口径差。参考侧声明剥除范围后，"声明水"与"简写"两侧口径对齐，倒挂**消失**；短线豁免档只是绕开倒挂、还要持续付滑坡看守成本（白名单扩列、方向策略裁释、每批 post-hoc）。
- 短线档的正当定位：仅当 teacher 明确立项且把它写成**以参考侧落地为退出条件的过渡件**时才有价值；预注册正文应含该退出句。属参考侧/金标侧变更，须用户逐次拍板——本设计只登记不推进 ✓（§九.3 复核无预支）。

### 3) 可直接落进规则文字的修改建议

- **R32-CS6-1（四元组恢复追溯开关，冲突修正）**："co_substrate_participant_tier 四元组恢复 r28 C1 原案：tier + exempt_identity_hash（cn 层版本化）+ direction_policy + **traceability_switch**（豁免对象须满足 T1′③ 逐项元素可追溯）；披露义务由生效护栏 ⑧ 承载、不占四元组位。任何字段增删 = 与 r28 T1′⑦ 冲突，须重新评审。"
- **R32-CS6-2（H₂O 成对 carve-out）**：按 CS6b-1 落字，与 T1′② 绑定引用。
- **R32-CS6-3（旁观型落字）**：按 CS6b-2 落字（恒 partial、禁止为"造对"错标来源组分）。
- **R32-CS6-4（辅因子不进清单 + 退出条件）**："辅因子对及任何含碳身份不得进入 exempt_identity_hash（含碳构造非法断言 + 硬拒绝表）；若 teacher 立项净共底物比较，预注册须写明'参考侧 omitted_coproduct_scope 落地之日，本豁免档废止'的退出条款。"
- **R32-CS6-5（长线登记强化）**：§九.3 登记保持现状（须用户拍板、本轮不推进 ✓），建议把"激励倒挂唯一根治路径"从描述升为**前置依赖声明**：短线档立项评估必须并排长线方案的可行性说明，防止短线档先落地后失去长线动力。

### 4) "程序上诚实但化学上误导"风险点

- **风险 1**：四元组披露开关在、追溯开关不在——预注册读起来"护栏齐全"（披露、方向、哈希、teacher、post-hoc 一个不缺），唯独少了防"元素不可能的计量洗 strict"的那道，这是最典型的"程序上齐备、化学上开洞"。
- **风险 2**："双侧绑定挡单侧洗白"被写成充分条件——单侧豁免本就到不了 strict，pairing 是纵深不是主闸；把它当主闸，白名单内容审查就会松。
- **风险 3**：短线档先落地、长线方案无限期挂起——豁免档的存在本身会给"参考侧不要动了"提供惯性，激励倒挂被永久化成"靠每批 teacher 裁定维持的平衡"。

**不确定项**：无机离子 Uncharger 往返稳定性（r28 前置，未验证）；参考图剥除口径构建代码（金标侧，未读——按 r28 P3 采信，维持未确认）；T-1 若立项的实际 extras 计算位置——零实施、未确认。

---

## 冲突检查汇总（P1 义务）

| 检查项 | 对照 | 结论 |
|---|---|---|
| 事件表示 / partial 归属 / rank / 分母 | `evaluation.py:1062-1080`、`s5b_scoring.py:654` 实读 vs 冻结 P1/rank | 零冲突（读码一致；"字节零改动"待执行验证） |
| 中心 unknown / R5 | 冻结稿 `:406-407`（判据五）、`:222`（R5→retain_conditional） | 一致，设计 `:85/:125` 落点正确 |
| 判据二 unknown 披露 | 冻结稿 `:161-164`；G2-c 定性不改口（设计 `:73`） | 一致，未宣称机制级闭合 ✓ |
| gate 扩展 | r31 H3②（同源+版本登记）；`compile_recorded_reaction` 实读无 corpus 分支 | 版本登记义务兑现；**一处"同源"不实**（执行侧键非 `strict_identity_of`，R32-CS3-2 修正） |
| §9.1 四元组 vs r28 T1′⑦ | r28 `:102/:150` vs 设计 `:257-261` | **冲突（规则级）**：追溯开关被披露开关顶替 → R32-CS6-1 恢复 |
| §9.1 direction_policy vs r28 T1′② | 成对要求 vs 水解 H₂O 无产物对应组分 | **冲突（规则级）** → R32-CS6-2 carve-out |
| D-T1′-3"互斥" vs T1′① extras 定义 | 设计 `:199` vs r28 `:105` | **新歧义**（非已裁条款冲突）→ R32-CS4-2 二选一落死 |
| PC-1 合成例氢配平 | 化学计量核算（CCO→CC=O 释 2H、吡啶→哌啶吸 6H，差 4H） | 非判据冲突，**披露义务**：正控标"元素账 unknown 非已配平"或换例 |
| 可执行子集为空分支 | 设计全篇未覆盖 | 规则缺失 → R32-CS2-4 |
| 错杀类目 / EAWAG 不对称 | r31 R31-3（`:100`）延伸义务 | 须点名落字 → R32-CS2-2 |
| coproduct_ignore_tier 状态 | 本轮 grep `src/` 零命中 | proposed 未实施、未冻结，T1′ 九条件维持 r28/r29 状态不重开庭 |
| stereo 消解附面 / r27 采纳附面 | 不在附后的 r32 请求原文内 | 未评审；如需另送请求原文 |

**统一不确定项**：全部执行类断言（gate 行为、audit disposition、字节等价、控件红绿）——**待执行验证**；1,323 整组分/键合/不可归属三分类与题级覆盖探针——**未跑**（§十二.1 unknown，CS2c 给出探针规格，D2 前置）；行号——本轮实读工作树（v4b 在飞改动所致漂移，设计 `:6` 自declare，实施轮重锚）；EAWAG donor 单组分事实、参考图剥除构建代码——沿 r31 标未确认；隐式 H 不进原子归属——读码推断，待实施核对。

---

**总判定（一句话）**：设计方向与判据一~五及 0d/0e 零直接冲突，选项 a + 键合保守拒 + 原子三分类守门 + union gate 扩展 + T1′ 三条落字在规则层成立——**有条件通过 D1 设计轮**，条件 = 本轮 16 条修改建议落字（其中 R32-CS6-1/CS6-2 为与 r28 已裁条款的**冲突修正**，R32-CS2-4、R32-CS3-3 为规则缺失必补），外加 CS2c 探针作为 D2 前置；T-1..T-5 维持 teacher 裁定，本回应不预支任何口径级批准。
