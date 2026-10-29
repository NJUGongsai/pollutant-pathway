# mimo 化学评审回应 r34（2026-10-11）

- 通道：opencode run -m opencode/mimo-v2.6-flash-free（免费档，通道 A；主会话转发落盘）
- 请求：docs/mimo_ppv1_chem_review_request_r34.md（D2 共底物参与物实施采纳核对 D1-D6）
- 只读 provenance：评审员以读取工具核对源码/文档，无 shell 执行权限；执行类断言均自带"待执行验证"
- 原始流：docs/review_evidence/ppv1_r34_mimo_2026-10-11/raw.txt
- 采信原则：与程序证据互证为准
- 注：本回应评的是 D2 原始交付（2e679b31）；其后 Codex 复审发现 S5B-D2-01（NC-10 双删绕过）并已回修 ea00297e（触发条件改挂记录侧声明）——r34 的 D3 面结论按互证原则由主会话对照回修后代码另行核对，不预填

---


✱ Glob "docs/mimo_ppv1_chem_review_request_r34.md" 1 match
✱ Glob "src/pathway_v43/pollutant/*.py" 32 matches
✱ Glob "docs/*COSUBSTRATE*" 1 match
✱ Glob "docs/S5B_D2*" 0 matches
✱ Glob "docs/*D2*.md" 2 matches
✱ Glob "docs/mimo_ppv1_chem_review_response_r3*.md" 5 matches
✱ Glob "docs/*DELIVERY*.md" 37 matches
→ Read docs/mimo_ppv1_chem_review_request_r34.md 
✱ Grep "ppv1-criteria-v1" in . · 100 matches
✱ Grep "coproduct_ignore_tier" in . · 100 matches
✱ Grep "_classify_cosubstrate_candidate" in . · 6 matches
→ Read docs/POLLUTANT_PATHWAY_S5B_COSUB_D2_DELIVERY_2026-10-10.md 
→ Read docs/S5B_COSUBSTRATE_PARTICIPANT_SEMANTICS_DESIGN_2026-10-10.md 
✱ Grep "^#{1,4} |R32-CS|NC-1[012]|PC-[45]" in docs/mimo_ppv1_chem_review_response_r32.md · 76 matches
✱ Grep "def |ProductionContractError" in src/pathway_v43/pollutant/production.py · 33 matches
✱ Grep "def _classify_cosubstrate_candidate|def _attach_cosubstrate_spec_fields|def _executed_components_strict_unified|def compile_recorded_reaction|def _flatten_product_entries|def _build_state_or_fail|declared_copy_mismatch|product_set_mismatch|cosubstrate_bonded_contribution_unsupported|cosubstrate_atom_source_unattributable|cosubstrate_no_executable_product_subset|cosubstrate_executable_add_atom_regression_guard|copy_component_unparseable|key_space_consistency|_executed_components_strict_unified|cosubstrate_unparseable" in src/pathway_v43/pollutant · 41 matches
→ Read src/pathway_v43/pollutant/recorded_source.py [offset=60, limit=260]
→ Read src/pathway_v43/pollutant/recorded_source.py [limit=360, offset=740]
→ Read src/pathway_v43/pollutant/recorded_source.py [limit=280, offset=1200]
→ Read src/pathway_v43/pollutant/recorded_source.py [limit=290, offset=1480]
→ Read src/pathway_v43/pollutant/recorded_source.py [limit=240, offset=1766]
→ Read src/pathway_v43/pollutant/recorded_source.py [limit=210, offset=2005]
→ Read src/pathway_v43/pollutant/production.py [limit=370, offset=152]
✱ Grep "def strict_identity_of|def build_chemical_state|smiles_isomeric|state_id|def _identity_key" in src/pathway_v43/pollutant/chemstate.py · 61 matches
→ Read src/pathway_v43/pollutant/chemstate.py [limit=60, offset=175]
→ Read src/pathway_v43/pollutant/chemstate.py [limit=30, offset=913]
✱ Grep "pool-policy|POOL_POLICY|n_cosubstrate_declared_specs|cosubstrate_pool_labels" in src/pathway_v43/pollutant/s5b_builder.py · 13 matches
✱ Grep "def find_recorded_exact|def find_corpus_recorded_exact|def infer_reaction_mapping|def _any_bond_query|def _strict_of" in src/pathway_v43/pollutant/recorded_source.py · 5 matches
✱ Grep "declared_copy|def net_reaction_signature" in src/pathway_v43/pollutant/s5b_compiler.py · 3 matches
→ Read src/pathway_v43/pollutant/recorded_source.py [limit=100, offset=1100]
→ Read src/pathway_v43/pollutant/s5b_compiler.py [limit=45, offset=160]
✱ Grep "^def test_|^class |NC-1[012]|matched_strict|PC-1|PC-4|PC-5" in tests/test_ppv1_s5b_cosub_d2.py · 41 matches
✱ Glob "tests/test_ppv1_s5b_*.py" 16 matches
→ Read tests/test_ppv1_s5b_cosub_d2.py [limit=180, offset=363]
→ Read tests/test_ppv1_s5b_cosub_d2.py [limit=145, offset=682]
→ Read src/pathway_v43/pollutant/evaluation.py [limit=90, offset=1029]
✱ Grep "^#{1,3} |^判据|0d|0e" in docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md · 26 matches
→ Read docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md [limit=130, offset=56]
→ Read docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md [limit=150, offset=392]
→ Read docs/TEACHER_T1_COPRODUCT_CALIBER_DECISION_2026-10-11.md 
→ Read docs/mimo_ppv1_chem_review_response_r32.md [limit=105, offset=101]
→ Read src/pathway_v43/pollutant/s5b_builder.py [limit=60, offset=640]
→ Read src/pathway_v43/pollutant/s5b_scoring.py [limit=40, offset=1]
→ Read tests/test_ppv1_s5b_cosub_d2.py [limit=128, offset=555]
→ Read src/pathway_v43/pollutant/recorded_source.py [limit=115, offset=632]
# mimo 化学评审回应 r34 —— D2 共底物参与物语义实施采纳核对（场景 1，判据冻结 ppv1-criteria-v1）

**评审方式与证据边界（先行声明）**：本轮为只读评审。我实读了 `docs/mimo_ppv1_chem_review_request_r34.md`、D2 交付书（`POLLUTANT_PATHWAY_S5B_COSUB_D2_DELIVERY_2026-10-10.md`）、设计书（`S5B_COSUBSTRATE_PARTICIPANT_SEMANTICS_DESIGN_2026-10-10.md` 含 §12）、r32 回应、冻结判据稿、teacher T-1 裁定包（2026-10-11）及源码 `recorded_source.py` / `production.py` / `chemstate.py` / `s5b_compiler.py` / `s5b_builder.py` / `s5b_scoring.py` / `evaluation.py` 与 `tests/test_ppv1_s5b_cosub_d2.py`，全部引用行号为实读行号。**我没有执行权限**：测试通过数、隔离子进程字节等价、漏斗/G01 数字一律标"待执行验证"，我不复述为已证事实。

**范围口径（透明披露，沿 r30/r31/r32/r33 体例）**：发来的边界头写"三个判断面（coproduct_ignore_tier 主面 / r27 条款项采纳核对 / stereo 消解设计复审）"与"变更集中在 {search,evaluation,…}.py 与 tests/test_ppv1_s5b_hit50_v3_*.py"，那是 r28 请求的模板残留，与所附 r34 请求（D1–D6，与 `docs/mimo_ppv1_chem_review_request_r34.md` 实读 29 行一致）不匹配；"主面为 proposed 裁定选项、附面二为未实施草案"在本轮也已过期（D2 已实施、v4b stereo 已实施）。**本回应按所附 r34 全文（D1–D6）评审**。另核：`coproduct_ignore_tier` 全仓 `src/` 零命中（未实施，与 r28/r29/r30/r31/r32 状态一致，不重开庭）；`evaluation.py`/`s5b_scoring.py` 实读内容与冻结 P1 语义一致（字节级零改动属 Codex 执行面，待执行验证）。

---

## D1（三分类守门忠实性）

### 1) 结论

**同意——三分类实现忠实于设计书 §五.1/§五.2 且在若干处比设计字面更保守；键合拒 74.4% 是"保守面既定"的预期形态；请求自报里"不可归属保守拒（22）"与交付书账目不符（真 298 面不可归属实测为 0），须更正——这是本轮唯一记账级错误，不影响守门方向。**

### 2) 展开（读码证据）

- **三分类落点**：`recorded_source._classify_cosubstrate_candidate`（:837-1074）在同源 `infer_reaction_mapping` 上划分——A-可溯（映射覆盖，:926-937）、B-可溯（全 new 断连组分 + 元素 ⊆ B 并集 + 单一 B any-bond 子结构对应，:897-918、:944-954）、不可归属（元素超出 A∪B，:949-952）、键合融合（同组分混 A-可溯与 new 原子，:938-943；或全 new 非单一 B 对应 ⇒ `skeleton_merge`，:955-958）。确定性"首个干净二分映射 + 无二分按首映射证据 bonded 优先"与设计 §五.2 一致（:868-870、:981-1074）。`mapping_fallback` 分列（R32-CS3-1）在 :1573-1581；标准枚举映射键空间无 `n_bond_diff`（:712-714、:733-735 实读），fallback 检测键判据成立。
- **比设计更保守的三处（正向）**：①B-可溯要求整组分对应**单一** B（多 B 并合 ⇒ 骨架并拒，:953-958），设计字面是原子级归属，实现收窄；②可执行子集为空单独拒（NC-8，:960-972）；③放行 spec 若含任何 `add_atom` 即结构化拒（NC-3 守卫，:1498-1531）。
- **键合拒 74.4% 的化学读法**：984/1,323（=74.38%✓）大头与 CS2c 探针"键合转移强代理 1,276"方向一致；三类损失化学（已声明水的水解/水合、已声明 O₂ 键合氧插入、转移基键合进底物）在拒因 detail 里逐条点名且"氧化酶/脱氢酶断连型不在损失面"如实分写（:1051-1066，R32-CS2-1/2 落字）。**这些拒在现行执行契约 + R2-2 字面下是化学上正确的保守处置**——执行图 = render(底物)，B-键合原子无诚实表达路径，放行即伪装。
- **记账核对（须更正）**：请求写"不可归属保守拒（22）"，但交付书 §七漏斗账目为 984 键合 + 317 编译层拒 + 22 放行 = 1,323，**不可归属/不可解析/空子集/add_atom 守卫真面实测 0**（:184）；"22"在 CS2c 探针里是"rhs_excess 含 A∪B 外元素不可归属**强代理**"的 22 条（交付书 :154-155），与放行 22 spec 纯属数字巧合。按交付书数字为准。
- **该放行而拒 / 该拒而放行的类**：前者我只找到"预算墙"而非"化学墙"——317 编译层拒里 `mapping_enumeration_truncated` 219（迁移表 5→224，:197-201）是枚举预算触顶，属 v4b 预算调优领地，不是本守门错杀；键合混合记录（B 贡献一个整组分同时贡献一个键合原子）整候选拒是设计明文的无例外条款（§五.2.3），我同意维持。后者：放行面的唯一宽松面是"重原子骨架级归属"（`_element_counts` 排除 H，:792-802；any-bond 子结构，:907-917）——这正是 NAD(P)⁺/H 对得以配对的必要设计，配合"全 new 原子 + 单 B + 元素包含 + union gate"四重约束，我读码未找到可放行的错误类；但 22 条放行 spec 的逐条化学形态我无法在本请求内抽审（规则级评审，零金标）。

### 3) 可直接落进规则文字的修改建议

- **R34-D1-1（记账更正）**："D2 三分支漏斗账目以交付书 §七为准：键合融合拒 984（74.4%）/ 可执行子集编译层拒 317（24.0%）/ 放行 22 spec（1.7%，15 题）/ 不可归属、不可解析、空可执行子集、add_atom 守卫真面实测 0（CS2c 探针的不可归属强代理 22 条为**探针代理计数**，非守门拒计数，两者不得混列）。"
- **R34-D1-2（拒因直方图子拆）**：`cosubstrate_bonded_contribution_unsupported` 的直方图条目建议同时输出 `bonded_kind` 子拆分（mixed-A 的 single_atom_insertion/group_transfer vs 全 new 的 skeleton_merge——四轴 detail 已在，:990-1017，只是直方图层未拆），防"984 全是 B-键合进产物"的单读法。
- **R34-D1-3（归属 H 盲区落字）**："原子归属在重原子图层面进行（隐式 H 不进归属判定）——该盲区是辅因子对（NAD(P)⁺/H 同骨架异还原态）可配对的必要条件；拷贝组分自身的身份不受影响（严格身份含 H 计量，逐组分精确），归属判定与组分身份是两个轴，不得互读。"

### 4) "程序上诚实但化学上误导"风险点

- **风险 1（最实）**：`bonded` 拒因名下藏着"全 new 非单一 B 对应 ⇒ skeleton_merge"子形态（:955-958、:1011-1017）——这些组分**没有**与 A 键合，是 B-B 并合或归属歧义；报告若把 984 统读为"共底物原子键合进底物产物"，化学图景失真。靠 R34-D1-2 子拆分解决。
- **风险 2**：`mapping_fallback` 分列只在"不可归属"拒因下进直方图分列键（:1573-1581）；键合拒同样带 `mapping_fallback` 字段（:1044）但无分列计数——回退映射伪影对 bonded 面的灌水效应未被同款披露。建议同款分列（P3）。
- **风险 3**：请求自报的"不可归属保守拒（22）"若进入下游叙述，会形成"源数据缺原子面存在 22 条实拒"的错误事实（实际为代理计数）——归因层面的化学误导，按 R34-D1-1 更正。

---

## D2（声明式拷贝语义的化学诚实性）

### 1) 结论

**同意——"拷贝组分进事件产物参与物（声明转写）而非执行产物（中心 unknown、不执行、来源字段完整）"是冻结判据内唯一诚实的表达；诚实性边界落在"身份轴可核、生成轴未核"两轴不得合并，且该边界目前只在 spec/生产报告层机读、事件载荷本身无逐参与物拷贝标记——这是本面最实的残留风险，须落字消费纪律。`

### 2) 展开

- **表示层**：拷贝以 `product/coproduct` 参与物进事件（协议枚举复用，零新发明），来源字段 `component_source=record_declared_copy / record_key / provenance_sha256 / execution_status=declared_not_executed` 挂在 `declared_copy_components`（provenance 层，**不进 Participant 计量层字段**，:1811-1824、:1849-1855），`participant_list_status=declared_complete`（:1853）+ `stoichiometry_status=unknown` 注记（production :503-506，R32-CS1-3 落字）。拷贝不进 edits/alignment/expectation（NC-9 断言 :454-475；NC-3 断言 :1498-1531；PC-1 正控实读 tests :504-526）。
- **诚实性边界的确切位置**：拷贝的身份轴 = 记录产物组分的严格身份（`strict_identity_of` 同源，chemstate :913-929，与身份键同一事实源 :180-226）——这一轴**有证明**（provenance 可核 + NC-4 多重集对账 + NC-10 轴 2）；生成轴（该组分在这次反应中是否真的形成）——**无任何执行证据，中心 unknown、不冒充**（判据五"缺/歧义映射 ⇒ 中心 unknown"，冻结稿 :406-408）。"程序诚实但化学误导"的分界线就是：任何把两轴合并成"已生成/已核实"的下游表述越界；任何把"声明式拷贝"读成"事件主张 B 转化出了该组分"的表述越界——事件主张的只是**记录自己写的净方程完整转写**。
- **declared_copy_mismatch 拷贝拒够不够**：身份面**够**——NC-4 是多重集包含核对（:2084-2098，拷贝只认 strict、cn 派生/立体异构拒，NC-11 测试 :439-451），配合 union gate 恒等（:2099-2117），拷贝既不能是外来分子、记录组分也不能被静默丢弃（少拷贝 ⇒ product_set_mismatch，NC-12-gate 测试 :454-463）；state 引用与重建 ID 不一致在 prepare 期二道拒（production :260-267、:281-287）。**它不该够的部分也确实没冒充**：配平/元素账不在 gate 职责内（`verified_product_set_scope` 明写"非元素/电荷配平核验"，:2143-2145，R32-CS1-2）。
- **事件载荷标记缺口（本面主要发现）**：e2e 实读（tests :738-761）显示事件表里拷贝与执行 coproduct 同为 `role=coproduct`，`declared_copy_components` / `cosubstrate_disclosure` 只落生产报告 artifact（production :480-507；tests :797-808）——**只读事件表的消费者无法区分"执行产物"与"声明拷贝"**。交付书对此有披露（§八 R32-CS1-1 行：字段说明不进 evaluation.py，判分零触碰红线），但消费纪律没有落成规则文字。

### 3) 可直接落进规则文字的修改建议

- **R34-D2-1（事件消费者纪律，必加）**："凡只读事件载荷（participants 的 side/role）的消费者，不得把 `role=coproduct` 解读为'已执行/已核实生成'；执行覆盖的唯一机读来源是同批生产报告的 `cosubstrate_disclosure.expectation_covered_state_refs`（或 `declared_copy_components[].execution_status`），跨表联读是消费义务，不是可选增强。协议层本轮不扩字段（协议冻结尊重）；若未来协议升版，逐参与物 `execution_status` 应进事件载荷。"
- **R34-D2-2（旁观型披露）**：对零拷贝放行事件（PC-4 形态，tests :555-579），在 `cosubstrate_disclosure` 增加机读注记："声明共底物在产物侧无对应组分（记录声明形态）；该组分的消耗/催化角色未判定，系数 unknown——不得读成'事件主张该组分被消耗'。"
- **R34-D2-3（两轴合并禁句升级）**：把"身份轴='与记录产物严格身份一致（provenance 可核）'、生成轴='未执行、formation 未核'，两轴不得合并"从交付书/spec 注记（现 :1864-1872 invariant_note、production :492-498）同步进 D3 评审轮的对外报告模板禁句表。

### 4) "程序上诚实但化学上误导"风险点

- **风险 1**：见上——事件表单表读法把拷贝当执行产物（最实）。
- **风险 2**：`any-bond` 骨架级归属让"同骨架异氧化态"组分可互为拷贝（NAD⁺↔NADH 是设计意图，tests PC-1 :487-493 即此形态）；若报告以"拷贝组分与 B 同骨架"暗示"化学等价/可互换"，是身份层误导——拷贝自身严格身份精确，等价性无声明。
- **风险 3**：旁观型（PC-4）事件的净方程形如"A + B → P（B 无产物侧去向）"——记录自身如此声明，事件忠实转写；但读者可能读成"该反应消耗 B"。靠 R34-D2-2 消解。
- **风险 4**：映射选择自由度（首个干净二分）在同骨架多组分场景可翻转"哪个组分算拷贝、哪个算可执行"——产物多重集恒等（并集 gate 钉死），差异只在期望覆盖面；判据层诚实（mapping_origin=inferred 已标），但报告若把"选择"读成"归因证明"越界。

---

## D3（事件不变量 NC-10 是否封死 r28 R2-2 残余）

### 1) 结论

**同意——双断言（含其键空间同源性）把 R2-2 点名的"伪装通道"残余在事件层封死了：B 与拷贝同丢的退化路径、拷贝单丢路径、拷贝进执行期望路径、拷贝篡改路径各有独立机器闸且键空间与判分同源；两处残留是"声明层不变量"的范围披露与异常结算归属，均非化学口子。**

### 2) 展开

- **五轴断言实读**（production :359-507）：轴 1 声明共底物 ⊆ 事件 reactant cosubstate（:396-422）、轴 2 记录产物多重集 == 事件产物参与物多重集（:423-442）、轴 3 参与物状态全可解析（:387-395）、轴 4 拷贝全被产物侧引用 + 机读标签（:443-453）、轴 5 NC-9 拷贝不进 expectation（:454-475）。触发 ⇒ `ProductionContractError` ⇒ 零事件零提交，且在假设构造前执行（:338-340，早于执行与提交）。
- **键空间同源性（我专门核了这处）**：轴 1/轴 2 比较两侧分别是 `states[...].smiles_isomeric` 与 `strict_identity_of(记录串)`——实读 `chemstate.py:705-707`（smiles_isomeric = 身份键同串）与 :913-929（strict_identity_of = `_identity_key` 同源），**同一事实源，无 r32 CS3b-1 类键空间错位**。
- **R2-2 残余路径逐条**：①B+拷贝同丢（退化为可 exact 的 A→P）⇒ 轴 1 拒（测试两种退化形态 :393-436）；②单丢拷贝 ⇒ 轴 2 拒；③拷贝塞进 expectation ⇒ NC-9 拒（:363-390）；④B 原子经 add_atom 折进可执行子集 ⇒ NC-3 守卫拒（:1498-1531）+ 分类层键合拒结构性排除；⑤拷贝串被换 ⇒ NC-4（compile :2084-2098）+ state 重建失配（prepare :260-287）双闸；⑥add_atom 负控对"零产物贡献 B"空转的缺口（r32 CS3b-3 点名）——正是 NC-10 轴 1 补上的，我确认无旁路。
- **两处残留（披露级）**：其一，NC-10 是**声明层**不变量（提交前核参与者声明），不是执行后核——执行无法增删参与者（事件由 prepared states 写出，e2e 原生表实测 :741-761），链条闭合，但规则文字应写明其证明范围是"声明消费完整性"而非"执行保真"（AGENTS.md 返工教训 3：局部正确不扩大证明范围）。其二，轴 1 是子集核（⊆，与 r32 R32-CS3-3 原文一致），不禁止事件**多**声明记录没有的 cosubstrate——现管线 participants 全部由记录装配（:1838-1851），无产生路径；作为事件级不变量它是单向闸，建议把"事件 cosubstrate 数 == 声明数"作为披露计数补上（P3）。
- **异常结算归属（工程 P3）**：`ProductionContractError` 不在 0d.2 已披露的窄捕获（AuditContractError）清单内——若真触发，按现行披露是逃逸至 run 进程级终止（零事件成立，fail-closed 方向正确）。方向安全，但"熔断红"应有结构化失败结算而非进程终止，属工程轮事项，不阻断采纳。

### 3) 可直接落进规则文字的修改建议

- **R34-D3-1（证明范围落字）**："NC-10 是提交前的**声明层**端到端不变量：它证明记录声明的共底物与产物组分被事件参与物完整消费，不证明任何组分的执行生成或配平闭合（生成轴 unknown、配平轴 unknown，判据二/五不变）。"
- **R34-D3-2（键空间事实源落字）**："NC-10 各轴身份键与判分同源：事件侧取状态 `smiles_isomeric`（身份键同串，chemstate 工厂同源），记录侧取 `strict_identity_of`——两键同一 `_identity_key` 事实源，不存在第二套比较器。"（把这句写死，防下一轮再有人重开键空间之辩。）

### 4) "程序上诚实但化学上误导"风险点

- **风险 1**：把 NC-10 表述为"原子来源已闭合"——闭合的只是**已声明组分**的归属与消费；记录未声明的隐式来源（EAWAG 面水氧）照旧经 add_atom、元素账 unknown（r31 R31-1 边界原样适用，r32 风险 2 同句）。任何"事件不再有无来源原子"表述 = P1 级错误。
- **风险 2**："触发即红"读成"已发生且被拦截过"——本轮零真实批，NC-10 的拦截面目前只有合成负控证据（测试），真实批行为待执行验证。

---

## D4（union gate 键空间统一与 EAWAG 字节等价声明）

### 1) 结论

**有条件采信——代码层我实读确认缺省路径（declared_copies=None）行为性惰化与键空间统一实现成立，"8 真实底物零字节差"是隔离子进程执行证据，我无法复跑，维持待执行验证；"字节等价"一词对外表述必须永远带"剥离登记键"限定，且 8 例是抽查不是全称。**

### 2) 展开

- **缺省路径惰化（读码）**：`compile_recorded_reaction` 扩展分支整体在 `if declared_copies is not None` 内（:2067-2146）；缺省路径唯一新代码是 `if reproducible:` 内的内层条件（:2033-2043，None 时不进），选首逻辑与历史一致；`find_recorded_exact` 全函数无任何 D2 分支（:1100-1186 实读）；`net_reaction_signature` 仅在 spec 携带 `declared_copy_components` 时并入拷贝（s5b_compiler :180-183，无该字段的 spec 元组逐字节同形，PC-3 测试 :642-643 实证）。**代码结构与"缺省 ⇒ 行为等价"的声明自洽。**
- **键空间统一（R32-CS3-2）**：`_executed_components_strict_unified`（:767-789）对执行侧片段走 `strict_identity_of`，union 比较两侧（执行 ∪ 拷贝 vs 记录全量）全部同源键（:2099-2117），裸键仅留作一致性披露对照（:2118-2142，分歧不吞）。
- **两处需在报告里如实带上的限定**：①字节等价声明剥离了 `corpus_retrieval_version` 与 `co_substrate_semantics` 两个登记键（交付书 §五自述）——这是登记面文本变更，我认可其归类，但对外引用不得简写成裸"字节等价"；②D2 扩展模式下的**中间**两道门（reproducible 选择 :2027-2030、strict 最终门 :2056-2066）仍是"裸执行键 vs strict 记录键"混比——这是历史行为保留，分歧方向是**过拒**（fail-closed）不是漏放，如实登记即可。
- **执行证据**：8 真实底物零字节差、全量回归 2019 passed、G01 隔离 2008 passed、父基线红绿 25 failed/36 passed——全部待执行验证；采信路径是 D3 评审轮 Codex 执行面复核。

### 3) 可直接落进规则文字的修改建议

- **R34-D4-1（等价声明限定句）**："EAWAG/整串路径的等价声明全称为：'候选 compile spec 在剥离 D2 版本登记键（corpus_retrieval_version、co_substrate_semantics）后与父基线零字节差；该两键是登记面披露、非行为面'。抽查面 = 8 个真实 298 底物（抽查，非全称全量断言）；全量等价由既有测试族 + Codex 执行面复核承担。"
- **R34-D4-2（扩展模式中间门登记）**："recorded-source-3 扩展模式下 reproducible 选择与 strict 最终门保留历史裸键比较（行为零改动的代价）；其键空间分歧的后果方向为过拒（fail-closed），权威终门为统一键的 union gate。"

### 4) "程序上诚实但化学上误导"风险点

- **风险 1**：把"8 例零字节差"读成"EAWAG 面全量证明"——抽查冒充全称（数字单位纪律，R32-CS5-3 同款）。
- **风险 2**：`key_space_consistency` 的分歧示例用两个 sorted 列表逐位 zip（:2123-2125）——单一分歧会造成位移错配、示例可能指错分子；它是披露计数不是 gate，但示例字段名若被下游当证据引用会误导，建议注明"示例为逐位对照近似，非最小编辑对"（P3）。

---

## D5（NC-12 熔断 + T1′ 三条落字 vs r30 G2-b 洗白路径）

### 1) 结论

**同意（有条件）——"A→P+NADH 洗成 strict"所需的两步豁免在现行实现与裁定下均无通路：反应物侧 B 由 NC-10 轴 1 钉死、产物侧 NADH 要么声明拷贝（partial）要么键合拒、任何 add_atom 折叠被 NC-3 结构性排除、T1′ 仍是零实施（src 零命中）；条件只有一条——NC-12 的"恒 0"前提域必须在规则文字里写死（现行 P1 无豁免档 + 参考边剥除口径），否则将来 T-1 立项或参考侧声明变化时，这颗钉子会从"防漂移"翻转为"挡已裁定许可"或被静默拆除。**

### 2) 展开

- **G2-b 路径逐环**：要洗成 strict，事件须与参考边双侧集合相等（evaluation.py:1062-1068 实读，exact ⇔ 两侧 `==`）。现在：NAD⁺ 型 B 在反应物侧 ⇒ reactants ⊋ from_states；NADH 型产物若为断连整组分 ⇒ 声明拷贝进 products ⇒ products ⊋ to_states（参考边剥除无机/辅因子，设计 §二 :63）；若 NADH 原子键合进 P ⇒ 整候选 bonded 拒；若 B 与拷贝全丢 ⇒ NC-10 轴 1/轴 2 拒；若走 add_atom 折叠 ⇒ NC-3 拒 + 分类层不可能（该组分原子全 new 且非单一 B 可溯不会进 executable）。**四条路全封。** NC-12 e2e 在合成批上断言 `matched_strict` 不出现且落具体桶 partial（tests :790-793，PC-1 加强版落字 ✓）。
- **T1′ 三条落字**：D-T1′-1（不得以 partial 压力倒逼放宽，设计 :191）、D-T1′-2（补全许可不延伸 + 机器锚：COMPLETION_LICENSED_IDENTITIES 无碳守卫测试，tests :467-481）、D-T1′-3（完整转写与忽略差集互斥，设计 :199）——三条均在；`coproduct_ignore_tier` 未实施（src 零命中），CS6 系预注册义务登记不推进（交付书 §八 :232）。R32-CS4-2 读法分叉（D-T1′-3 互斥 vs T1′① extras 定义）登记"待裁"（交付书 :229），因其只在豁免档实施时才有行为后果，**休眠状态可接受**；且 2026-10-11 teacher T-1 裁定包 §3 b) 条件 7 已把"读法二选一落死"设为立项前置——闭环责任有归属。
- **teacher 裁定包交叉（登记事实，非本轮裁定对象）**：该包状态 `awaiting_teacher_decision`（:5），若未来裁定 b 档立项，`co_substrate_participant_tier` 会让本通道**故意**产 strict——届时 NC-12 现行文字"出数即口径漂移或实现 bug，红"（r32 :182、recorded_source :126-128）语义反转，必须在该档预注册内重定义熔断，且该档自己的 §5.5 已列"批级熔断随首批交付"（:133）——责任在彼不在此，但**本通道规则文字现在就要写上前提域**，防两轮文字打架。
- **NC-12 的结构性前提**："恒 0"的证明依赖**参考边剥除口径**（参考边 from={A} 单底物）。参考侧若按 T-5/CS6c 长线声明共底物，本通道事件可正当地回 strict——那不是漂移是新口径。熔断的红必须区分"实现 bug"与"口径变更生效"，靠前提域落字实现。
- **T1′ 三条 + NC-12 是否够防住 r30 G2-b 的**后续**变体**：豁免档（若立项）的主闸是 `exempt_identity_hash` 含碳构造非法断言 + 辅因子硬拒绝表（R32-CS4-1，登记待 T-1 实施生效）；本轮零实施，无新面。够。

### 3) 可直接落进规则文字的修改建议

- **R34-D5-1（NC-12 前提域，必加）**："NC-12 批级熔断（本通道 matched_strict 计数恒 == 0）是**现行口径下的结构性不变量断言**，其前提域 = ①P1 集合语义无任何豁免档生效（co_substrate_participant_tier / coproduct_ignore_tier 均为零实施）且②参考边维持剥除共底物口径。任一前提变化（豁免档经 teacher 裁定 + 新预注册生效、或参考侧声明共底物）⇒ 本熔断在新预注册内重定义，不得静默删除、不得让旧文字挡住已裁定许可。"
- **R34-D5-2（旁路方向声明）**："本通道回 strict 的唯一合法路径 = 口径级变更（T-1 裁定档或参考侧 omitted_coproduct_scope），各自走 ppv1-criteria-v2 起的新版本流程；工程侧不存在、也不得实现任何'绕过熔断的小修'。"

### 4) "程序上诚实但化学上误导"风险点

- **风险 1**："NC-12 熔断钉死"作为无条件结论出现——真实批熔断目前是 e2e 测试断言 + 结构论证，真实批的通道归因是后置零 LLM 聚合（交付书 §九，如实登记 ✓）；表述须带"合成批机器证据 + 结构论证"双限定，不得说成"真实批已验证"。
- **风险 2**：把"T1′ 三条落字"读成"洗白路径已由机器永久封死"——真实状态是"文本封死 + 三台机器（NC-10/NC-3/NC-12）现役 + 白名单挡板未装配（R32-CS4-1 随 T-1 实施生效）"，r32 风险 1 同句沿用。

---

## D6（总判定 + 与冻结判据一~五及 0d/0e 的冲突检查，P1 义务）

### 1) 结论

**采纳成立（有条件）——D2 编译实施忠实于设计书 §四/§五全部规则与 r32 十六条（逐条落点我实读核对，见下），与冻结判据一~五及 0d/0e 未发现 P1 级冲突；采纳条件 = 本回应 R34-D1-1 记账更正 + 四条落字（D2-1/D2-2/D5-1 及 D3 证明范围句）+ 全部执行类断言待 Codex 执行面复核。**

### 2) 冲突检查逐条（P1 义务）

| 冻结条款 | 本批接触面 | 判定 |
|---|---|---|
| 判据一（身份键，冻结稿 :58-67） | B/拷贝/A 状态全部经同一工厂内容寻址（production :221-288；chemstate :705-707）；strict_identity_of 同源 | 零冲突 |
| 判据二（系数未知 ⇒ coverage/元素/电荷账 unknown，:149-166） | 全参与物 `coefficient_status=unknown`（:1833-1851）；gate 明写非配平核验（:2143-2145）；`stoichiometry_status=unknown` 注记 | 零冲突（方向一致） |
| 判据三（补全许可 H₂/[H] 边界） | 零扩列 + 无碳机器守卫（tests :467-481；R32-CS4-3 对称句落字交付书 :230） | 零冲突 |
| 判据五（缺/歧义映射 ⇒ 中心 unknown，:406-408） | 拷贝中心 unknown、R5 语义（CORPUS 语义键 :222-233） | 零冲突 |
| 0d.1 产品来源精度（:492-497） | 事件产物身份 = 池声明结构内容派生 state_id；拷贝是**池声明的产物侧状态**（同一契约延伸），执行输出不改写身份；拷贝不进 expectation（NC-9）故无"声明 vs 执行"失配面 | 零冲突；建议加一句延伸落字（见下）防误读为"新产品身份来源" |
| P1 参与物集合语义 / rank 只认 strict（evaluation :1062-1068；s5b_scoring :11-16） | 零触碰（实读与冻结语义一致；字节级零改动待执行验证） | 零冲突 |

**建议的 0d.1 延伸落字（P3，非冲突）**："声明拷贝组分是池声明产物集的扩展成员，其 state_id 走 0d.1 同一内容派生契约；`component_source=record_declared_copy` 只改披露层，不构成新产品身份来源。"

### 3) r32 十六条采纳核对（抽核结论）

我逐条对照交付书 §八表与源码：CS1-1/1-2/1-3、CS2-1~2-4、CS3-1~3-4、CS4-1~4-4、CS5/CS6 登记全部有实读落点（关键锚：四轴子标签 :990-1050；两层理由 :1051-1066；空子集拒 :960-972；mapping_fallback 分列 :1573-1581；键空间统一 :767-789/:2099-2142；NC-10 production :359-507；控件矩阵 tests :176-812；T-1..T-5 默认档登记交付书 §九.4）。未发现"条款登记了但代码没有"或"代码有但条款没登记"的反向缺口（读码层面；测试实际通过数待执行验证）。

### 4) "程序上诚实但化学上误导"风险点（本面）

- **风险 1**：漏斗数字迁移表里 `mapping_enumeration_truncated` 5→224——若被读成"编译质量恶化"违反 R31-6 禁句；正确读法是"共底物面首次到达编译层，预算墙显形"（v4b 领地）。报告必须同句带迁移口径。
- **风险 2（跨文档，登记）**：teacher T-1 裁定包（2026-10-11）§2.3.5/§3b 仍写"CS2c 探针未跑、二分占比 unknown"，而 D2 交付书 §六/§七已产出该探针（1,323 四分类 + 漏斗 + 22 spec/15 题放行）——裁定包证据状态陈旧，**送 teacher 前应补一句"探针已跑、结果见 D2 交付书 §六/§七"**，否则裁定建立在"未知占比"前提上（这不改变三档并列，只更新证据状态）。
- **风险 3**：请求边界头把变更面写成含 evaluation/search/runflow——与判分零触碰红线矛盾（属模板残留，请求正文 :29 自己写对了）；若该错误范围进入 D3 评审任务书，会把 Codex 复审面引向不存在的变更。发车前更正。

---

## 汇总：采纳条件清单（全部为落字/记账级，无 P1）

1. **R34-D1-1**：三分支漏斗记账以交付书 §七为准（不可归属真面 0；"22"是探针代理计数与放行数巧合），更正请求自报。
2. **R34-D2-1**：事件消费者纪律落字（`role=coproduct` ≠ 已执行；联读生产报告披露是消费义务）。
3. **R34-D2-2**：旁观型（零拷贝）事件机读注记。
4. **R34-D3-1/D3-2**：NC-10 证明范围（声明层）与键空间同源事实源落字。
5. **R34-D5-1/D5-2**：NC-12 前提域 + 回 strict 唯一合法路径落字。
6. 全部执行类数字（字节等价、2019/2008 passed、红绿、漏斗 1,323/984/317/22、15 题供给）维持**待执行验证**，由 D3 评审轮 Codex 执行面互证；22 条放行 spec 的逐条化学抽审不在本请求范围，建议随 D3 公开探针面送（或按场景 3 在真实批复测后做后置化学复核）。

**一句话收口**：化学方向对、守门保守面成立、拷贝语义诚实、R2-2 残余在事件层封死、与冻结判据零冲突——有条件采纳，条件是把"记账一处、消费纪律两处、前提域一处"写进规则文字，别让下一轮读码的人重新考古。
