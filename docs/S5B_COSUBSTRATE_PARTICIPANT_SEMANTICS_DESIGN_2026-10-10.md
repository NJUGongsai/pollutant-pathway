# PPV1 S5b 共底物参与物显式语义设计书（设计轮，零代码）

- **编号**：S5B-COSUB-DS-1（规则级设计，非实施交付）
- **日期**：2026-10-10（Asia/Shanghai）
- **状态**：`design_draft_for_review` —— 主会话 + teacher + mimo（r32，通道 A）三级审阅对象
- **基线**：实际 HEAD `8d92f3aa0e1a16ba454aa97702a076f319195aed`（chain11 收口提交）；本轮**零代码、零测试、零既有文档改动**，只读本仓源码/文档；不启动任何真实批。**行号锚定说明**：本设计书全部源码行号按 HEAD 8d92f3a 只读核验；设计成稿时工作树另含**未提交的 v4b 并行线在飞改动**（recorded_source.py/s5b_compiler.py，枚举预算升档 + 编译器侧 stereo 消解——与本设计零依赖正交，见 §八.2），实施轮开工时须按届时实际 HEAD 重锚并核对行号。
- **上游依据**（按约束力排序）：
  1. 冻结判据 `docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md`（ppv1-criteria-v1，判据一～五 + 0d/0e）
  2. Codex v4 复审 `docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_CODEX_REVIEW_2026-10-10.md` §4（唯一 P1=S5B-V4-01 配平反例）/§4.3（最低收口）/§8（有限回修提示词，"完整显式参与物及贡献映射属后续设计方案；如选该方向，应先形成规则级方案并送化学评审"）
  3. mimo r30 `docs/mimo_ppv1_chem_review_response_r30.md` G2/R2-2（P1 级条款）+ G2-c（编译层结构性发现）
  4. mimo r28 `docs/mimo_ppv1_chem_review_response_r28.md` 总裁定（coproduct_ignore_tier T1′ 九条件）
  5. mimo r31 `docs/mimo_ppv1_chem_review_response_r31.md` H1–H3（诚实拒许可范围；H3 设计轮四项必答）
  6. v4-R1 交付 `docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_R1_DELIVERY_2026-10-10.md`（现行诚实拒实现）；v4-R1 复审（P1 清零放行）；`docs/S5B_V4_RETEST_REGISTRATION_2026-10-10.md`（chain11 登记 + r31 措辞护栏）
  7. 源码现状（只读）：`src/pathway_v43/pollutant/{recorded_source,s5b_compiler,production,hypothesis,evaluation,s5b_scoring,s5b_builder}.py`
- **红线声明**：本设计**零金标、零题面、零逐题内容**——只使用已披露聚合计数与合成例（CCO、CC=O 级，见附录 A 泄露扫描）；任何方案**不得暗改冻结判据**，口径级变更一律显式标注"须 teacher 裁定 + 新预注册"；本设计**不要求 v4b（编译墙消融线）改其范围**（§八接口边界）；对外数字一律带 **298 题域标签**，不外推 dev。

---

## 一、问题陈述与设计目标（自包含）

### 1.1 供给锁现状（chain11 实测，聚合数）

chain11（v4 复测批，封存只读）终判分：**hit@1=76/298（目标 119 未达，与登记预期 76± 一致）、hit@5=103、U=106 与 v3 持平**；零失败、298 调用（commit 8d92f3a 收口记录）。corpus 整串子集净增益≈0——**大头锁在两处**：编译墙（v4b 消融线，另行推进）与**共底物参与物语义缺口（本设计轮）**。

缺口机制：RHEA 组分级记录是"底物 A + 共底物 B → 产物们"（净方程完整声明全部参与物）。现行实现（S5B-V4-01 回修，corpus-retrieval-2/pool-policy-3）把**有共底物的 component 候选一律编译前结构化拒**（`corpus_cosubstrate_participants_unsupported`，298 题检索面内 **1,323** 候选，raw_top=24 截断后计数）。诚实拒是 R2-2 允许的保守处置（mimo r31 裁定"满足最低要求"），但它锁死了供给：**供给面 267 题中 204 题携带有机/辅因子样共底物**（碳数零否的**代理统计**，非已执行 partial——Codex v4 复审 §6 订正在案）、63 题仅有零碳书写平衡项；组分级频次 balance_like 4,878 / organic_like 11,052，其中 NAD(P) 系 1,138+245+111 次高频。

### 1.2 为什么不能直接放行（反例实锤）

把共底物 B 折掉、按单组分 LHS=A 编译时，产物里 B 来源的原子会经 `add_atom` 折成"新增原子"（无中生有）、事件不声明 B，冻结判分链反而授 `matched_strict`——Codex v4 复审 §4.2 公开反例族实证（合成例：`CCO.CC → CCOCC`，底物 CCO，两个新增碳均 add_atom，事件只声明 CCO→CCOCC，冻结匹配 matched_strict；**配平增强案 `CCO.C=C=O → CCOC(C)=O` 同根**，证明"源记录配平"不能自救）。产物多重集 gate 只回答"做出了什么"、不回答"原子从哪来"（mimo r31 H1a 反证：修前 42 个最终池 corpus spec——整串 14/组分 28、strict 层 38——全部通过该 gate 且 strict 层拿到 matched_strict，同时组分形态的原子是伪造的）。

### 1.3 设计必须兑现的裁定（mimo r30 R2-2，P1 级，逐条映射）

| R2-2 要点 | 本设计章节 |
|---|---|
| 共底物来源产物组分**必须**以事件参与物显式声明（含来源记录字段） | §四（事件表示，选项 a） |
| **禁止**仅条件字段单处置 | §四选项 b 被降级为守门基底层，禁作独立表示 |
| 共底物来源组分**不得**经 add_atom 执行通道从底物原子生成 | §五（原子级守门） |
| 产物多重集 gate 的任何扩展须**同源实现并配"共底物原子伪装新增"负控** | §五（gate 扩展 + 负控矩阵） |
| 诚实披露：partial 不可升 strict 的子集，不得按全额外推 | §七（计量语义）+ §十二（unknown 登记） |

mimo r31 H3 给设计轮的四个必答问题：① 声明式拷贝的组分身份来源与 provenance 字段（§四.3）；② gate 扩展同源 + 伪造原子负控（§五.3）；③ 诚实声明共底物 ⇒ 相对剥除参考边判 partial 的供给预期落字（§七）；④ 激励倒挂（声明环境水=partial、省略=strict 可达）如何处理（§六.4 + §九长线）。

### 1.4 设计目标（排序）

1. **化学诚实优先于覆盖**：事件不得声称底物单体净转化出共底物原子（S5B-V4-01 类假单步永不再产）；
2. **在 1 的约束下解锁最大诚实供给**：整组分贡献（辅因子对型）解锁，键合贡献保守拒并如实计数；
3. **冻结判据零触碰**：P1 参与物集合语义、判分尺子、分母、排序全部不动；口径级选项只走预注册路径（§九）；
4. **机器可强制**：所有边界都是编译器/执行器可判定的结构化规则 + 正负控，不依赖文档自觉。

---

## 二、现行机器事实（设计基线；本 HEAD 只读摘录）

| 层 | 入口/事实 | 对设计的含义 |
|---|---|---|
| 检索/装配 | `recorded_source.find_corpus_recorded_exact`（:719）——CN 宽检索、strict/CN 分层同源、component 候选装配 + corpus-retrieval-2 许可拒（:878–905，保留源行/方向/master/共底物 SMILES+严格身份/产物/permission_note） | 许可拒的**可追溯 detail 已在**，设计轮把"拒"改写为"有条件放行 + 守门"，拒因类目随之迁移（§七） |
| 编译 | `recorded_source.compile_recorded_reaction`（:1009）：推断映射（有界枚举、键差≤2、预算 200/512）→ `compile_donor_template` → **产物多重集 gate**（:1085–1113，执行组分严格身份多重集 == 记录产物多重集） | gate 是编译层判据（非冻结尺子）；扩展须**同源函数 + 版本登记**（r31 H3 ②） |
| 新原子 | `s5b_compiler._place_new_atoms`（:540–624）：新增原子按锚点拓扑序 `add_atom`；**无锚 ⇒ `new_atom_unanchorable` 拒**；带电新原子拒 | 断连辅因子（NADH 型）天然无锚——这正是"整组分声明式拷贝"要接管的面；**键合共底物原子恰好可锚**——这正是 add_atom 伪装通道，必须机器封死 |
| 执行 | AtomTool 执行图 = `render(substrate_smiles)`——**执行图里只有底物**（production.py:288；冻结 0d.1 固定链） | 物理边界：B 不在执行图内 ⇒ **B 原子键合进产物在现行执行契约下无诚实表达**（设计必须如实钉死，见 §四选项 a 的键合子集处置） |
| 事件产物身份 | 0d.1：事件产物身份 = 池声明 `product_smiles` 内容派生 state_id（production.py:417）；工具执行输出是**核验轴输入**，不改写产物身份；两者不一致经中心轴落 unknown/violated | "声明式拷贝"有既定契约落点：声明产物可含拷贝组分，执行只核可执行子集，拷贝部分中心 **unknown**（判据五：缺映射 ⇒ 中心 unknown，不猜） |
| 参与物协议 | `hypothesis.Participant`：role 枚举**已含 `cosubstrate`**（:83）；系数 known/unknown 契约（unknown ⇒ null）；`participant_list_status` ∈ {source_complete, declared_complete, partial, unknown} | 角色与系数协议**已备**，无需新协议字段 |
| 参与物装配 | `production.prepare_hypothesis`：**`spec["participants"]` 显式覆盖已支持**（:209–212）；缺省装配 = 底物（reactant/primary_substrate）+ 主产物 + coproducts（:217–232）；states 映射 = 底物+产物+coproducts（:246–249） | 实现面主要工作量 = 装配语义 + states 扩（共底物/拷贝产物 state 需入 states 映射）+ 守门，**协议层零新发明** |
| 判分 | `evaluation.match_reference_edges`（:1062–1068）：exact ⇔ `reactants == from_states 且 products == to_states`（state_ref/state_id **集合**）；超集/子集 ⇒ `matched_participant_coverage_partial`；参考边系统性剥除无机/辅因子（r28 P3 口径） | 诚实声明 B ⇒ 事件反应物侧 ⊋ 参考侧 ⇒ **partial（既定行为，非冲突）**；rank 只认 matched_strict（s5b_scoring.py:11–16），partial 事件不进命中 |
| 计量 | 判据二：未知系数 ⇒ coverage/元素账/电荷账 **unknown**（"两侧对称漏写参与物在本轴不可见"——unknown 是无守门的既定性质） | 共底物事件系数全 unknown ⇒ 账面诚实 unknown；**不得**把 unknown 读成"已核平"（r30 G2-c） |

---

## 三、设计总则（冻结锚，任何方案不得暗改）

1. **P1 参与物完整集合语义不动**：集合相等 ⇒ exact；事件多出组分 ⇒ superset ⇒ partial。本设计产出的诚实事件对单底物参考边**必然 partial**，这是预期行为不是缺陷（落字见 §七）。
2. **T1′ 边界（r28 裁定）不动且显式重申**：coproduct_ignore_tier 仍是 proposed 未实施；其九条件（白名单仅无机小分子、只作用产物侧差集、反应物侧仅 H₂O 特例、逐项元素可追溯、O₂ 出产物侧白名单、CN⁻/SCN⁻/H₂O₂/NH₂OH/NO 恒不忽略、cn 身份层版本化哈希、post-hoc 敏感性表、T2 否决/T3 暂缓）对本设计构成**外部边界**——本设计不得以"完整产物集语义"倒逼其放宽（§六）。
3. **r31 措辞护栏不动**（chain11 登记 §三已冻结）：add_atom 伪装禁令范围 = 记录**已声明**的共底物（corpus 组分级）；记录未声明的隐式来源（EAWAG 型水/受体/氧）不在禁令内、仍合法经 add_atom 产生、元素账 unknown；**任何"事件不再出现无声明来源原子"的表述 = 错误**。
4. **G2-c 闭合定性不改口**：现行是"通道级断供闭合（corpus 组分级）"，判据二 unknown=无守门是冻结判据既定性质；本设计把断供改为**有条件放行**，是供给许可变化（新版本登记），**不是**判据二的修复，也不得宣称机制级闭合。
5. **计量不外推**：204/1,323/1,138 等是检索/池面聚合计数（碳数零否代理），不冒充命中数、不外推 strict 收益、不带 dev 标签。

---

## 四、设计问题一：事件表示——共底物 B 在候选事件里怎么出现

### 4.1 三个选项的对照（每项四问：P1 行为 / 化学诚实性 / 204 题影响 / 实现面）

#### 选项 a：B 进反应物侧参与物集合 + 共底物来源**整组分产物**声明式拷贝（事件 = A + B → 记录全部产物）

- **P1 参与物集合比较行为**：事件反应物侧 = {A, B}、产物侧 = 记录全部产物（含 B 来源整组分，如还原型辅因子）。单底物题参考边 from={A}、to={剥除后产物} ⇒ 事件两侧均超集 ⇒ `matched_participant_coverage_partial`（evaluation.py:1065–1068 超集分支）。**不产 strict**——与现行诚实拒同为"无 strict 通路"，但事件本身化学诚实。
- **化学诚实性**：事件声明的是记录自己的净反应（A+B→产物们），不冒充单底物反应；B 来源产物组分以**声明式拷贝**进入事件（身份 = 记录产物组分的严格身份，经 `strict_identity_of` 同源派生 state_id），**不经执行通道**；可执行子集（A 原子可溯的产物组分，如主产物 P）照常推断映射 + 编译 + AtomTool 执行；拷贝组分在供体诊断里落**中心 unknown**（判据五：缺/歧义映射 ⇒ 中心 unknown，不猜对应），决策表走 R5（retain_conditional）——**不虚授 verified、不冒充执行**。
- **204 题影响**：204 题仍无 strict 通路（P1 既定）；其中"整组分贡献"子集（辅因子对型：B 以断连整组分出现在产物侧，如脱氢酶的 NAD(P)H、酰化酶的 AMP/PPi 类）解锁为**诚实 partial 供给**；"键合贡献"子集（B 原子键合进主产物，如基团转移 A+B→A–B 融合产物）**继续结构化拒**（§五——执行图物理上没有 B，add_atom 即伪装，R2-2 禁止）。两个子集在 1,323 内的占比**未知**（§十二登记；可做只读聚合计数探针，不碰金标）。
- **实现面（分层清单）**：
  - *compile*：corpus component 候选许可规则从"一律拒"改为三分支（整组分拷贝可编译 / 键合贡献拒 / 不可归属原子拒）；spec 新增 `participants` 显式装配 + `co_substrate_states`（B 的 state 装配，SMILES 不可解析 ⇒ 结构化拒 `cosubstrate_unparseable`）+ 拷贝组分的来源字段（record_key/line_no/master/direction/provenance_sha256 + `component_source: "record_declared_copy"`）；`expectation.target_smiles` = 可执行子集（A→P 可执行部分）；拷贝组分**不进** edits/alignment 通道；
  - *atom_tool*：**零改动**（拷贝组分根本不生成编辑；可执行子集照常）；
  - *store/events*：participants 已持久化；states 映射需扩（B 与拷贝产物的 state 入 `prepare_hypothesis` 的 states——production.py:246–249 现只含底物+产物+coproducts，需加 B 与拷贝组分，同 build_product_state 同源构建）；
  - *production*：`spec["participants"]` 覆盖路径已支持（:209–212），工作量在装配与 states 扩，**固定链顺序零改动**；
  - *events/evaluation/s5b_scoring*：**零改动**（P1 匹配、rank、分母全部原样）；
  - *版本*：corpus-retrieval-2→3（许可语义）、pool-policy-3→4（池成员）；若 gate 扩展落在公共编译函数则 recorded-source-1→2（§五.3）。

#### 选项 b：B 的产物贡献原子显式标注来源（原子级 provenance），参与物集合按标注推导

- **P1 行为**：分两种子形态——b1：B 原子标注 `from=co_substrate[B]` **且 B 进参与物集合**（此时与选项 a 的差别只在标注粒度：原子级 vs 组分级）；b2：仅标注、B 不进参与物集合——**这是 r30 R2-2 点名禁止的"条件字段单处置"变体**：事件元素账因系数 unknown 而无守门（判据二），"原子有出处标签"不能替代参与物声明，事件仍主张了"底物单体 → 含 B 原子产物"的假单步。
- **化学诚实性**：b2 化学误导（R2-2 P1 级禁止，不可选）；b1 化学诚实但**原子级 provenance 对整组分拷贝没有增量信息**（拷贝组分身份即来源），对键合贡献则**无法兑现**（执行通道被封死后，键合产物根本产不出来，标注无处安放）。
- **204 题影响**：b1 ≈ a（无增量覆盖）；b2 违规。
- **实现面**：原子级标注要求编辑协议/执行器携带新元数据（atom_tool 层新字段），**改动面比 a 大而收益为零**。
- **定位结论**：**b 不作为独立事件表示**；其"来源标注"思想降级为 §五的**机器守门基底层**（编译器内部原子归属分类，用于判定拷贝/拒/伪装负控）与诊断披露字段（`n_atoms_attributed_to_co_substrate` 类聚合计数），**不进事件协议**。

#### 选项 c：B 作为"条件参与物"声明但**升级判分面**（口径级变更，须 teacher 裁定）

- **形态**：预注册新字段（如 `co_substrate_participant_tier`），P1 比较时豁免"已声明共底物参与物"（反应物侧）与"其来源整组分产物"（产物侧）——即比较"净共底物"参与物集合，使诚实声明事件可回 strict。
- **P1 行为**：判分尺子语义变更（evaluation 集合比较的豁免规则）——**触碰冻结判据邻接面**（P1 是冻结口径），且方向正是 r30 G4-2 警告的滑坡：反应物侧豁免有机共底物 = 系统性主张"脱氢酶反应不需要电子受体"（r28 T1′ 反应物侧只豁 H₂O 特例正是为此设防）。
- **化学诚实性**：取决于豁免范围；无守门的宽豁免 = 化学倒退；带四元组护栏的窄豁免 = 可辩论的口径选择。
- **204 题影响**：唯一能让 204 子集回 strict 的路径；但收益归属必须 post-hoc 敏感性表披露，且**不得回填 headline**。
- **定位结论**：**本轮不实施、不给预支批准**（Codex v4 复审 §4.3："不以当前'方向无冲突'预支批准"）；只按 §九出**预注册独立字段草案**，交 teacher 裁定。mimo r32 仅评审其护栏设计（CS6），不评审其实施。

### 4.2 推荐：**选项 a（整组分声明式拷贝）+ b 降级为守门基底层 + 键合子集保守拒 + c 仅预注册**

理由（一句版）：a 是唯一同时满足 R2-2 全部五要点且不动冻结判据的表示；b 无增量且 b2 违规；c 是口径级变更，收益真实但风险方向已两次被裁定为滑坡高发区（r28 T1′ 反应物侧边界、r30 G4-2），必须走 teacher + 独立预注册，不搭设计轮车。

### 4.3 事件形状细则（选项 a 的完整规则文字草案）

1. **参与物装配**（corpus component 候选编译成功时 spec 必带 `participants`）：
   - 底物 A：`side=reactant, role=primary_substrate, coefficient_status=unknown`（库记录无配平系数）；
   - 共底物 B（逐个，全部声明组分，**不静默丢弃**）：`side=reactant, role=cosubstrate, coefficient_status=unknown`；
   - 可执行主产物：`side=product, role=principal_product`；
   - 其余 A 来源可执行组分：`role=coproduct`；
   - **拷贝组分**（B 来源整组分产物，逐个）：`side=product, role=coproduct` + 组分级来源字段（`component_source="record_declared_copy"`、来源 record_key/provenance_sha256）——角色复用 coproduct（协议枚举不扩），**来源进 provenance 层不混入计量层**（Participant docstring 纪律）；
   - `participant_list_status`：**待 teacher 裁定的口径级决策点 T-2**（§十一）——corpus 净方程是源侧完整清单，语义上近 `source_complete`；但完整清单 + 系数全 unknown 的组合在审计轴的含义须 teacher 确认；保守替代 `declared_complete`。
2. **状态装配**：B 与拷贝组分经同源 state 构建（严格身份内容寻址）；SMILES 不可解析 ⇒ 候选级结构化拒（`cosubstrate_unparseable` / `copy_component_unparseable`），不猜不清洗。
3. **执行与诊断**：edits/alignment/expectation 只覆盖可执行子集（A 原子全部可溯的产物组分）；`expectation.target_smiles` = 可执行子集；供体诊断对拷贝组分**无映射 ⇒ 中心 unknown**（判据五），决策表 R5；审计 detail 披露 `declared_copy_components` 列表（身份 + 来源）。
4. **禁止事项（直接落字）**：拷贝组分不得出现在任何 edits/alignment/expectation 字段里；不得用 composition_only_hydrogen_equivalents 许可为有机共底物组分补全（该许可仅 H₂/[H] 氢当量，判据三既定）；不得从被拒条目的 compile_detail 重建可用 spec（R31-8 沿用）。
5. **同净反应去重**：池侧同签名合并（s5b_builder 现行）自然覆盖——拷贝组分进 `product_smiles` 全串 ⇒ 净反应签名含共底物贡献，与整串/其他通道同签名时合并留痕（不双占槽）。

### 4.4 风险与缓解（选项 a）

| 风险 | 缓解 |
|---|---|
| partial 桶膨胀被读成"设计缺陷"，反推忽略档放宽 | §六边界句 + §七供给预期落字（R2-4 疫苗）；首批必须单列 partial 新增计数 |
| 拷贝组分被下游读成"已执行/已核实" | 中心 unknown + `declared_copy_components` 机读披露 + "拷贝组分中心恒 unknown，非 verified"落字（判据五 8b None=未评估纪律） |
| B 状态与拷贝产物状态把 states 映射灌大（池/事件体积） | 拷贝产物 state 与 coproduct 同轨（既有 0e.5 coproduct followup 消费链）；体积上限与披露照池宽纪律 |
| 激励倒挂显性化（诚实水解 partial、EAWAG 简写 strict 可达） | 不在本设计内修（判据冻结）；如实落字（§六.4）+ 长线参考侧方案登记（§九.3） |
| 参考边未来若补声明共底物，旧 partial 事件口径漂移 | 不回写、不反向要求；新参考版本属新批新登记（r28 C1 ④ 中性条款同款） |

---

## 五、设计问题二：原子级守门——"共底物原子不得经 add_atom 伪装新增"的机器强制

### 5.1 原子归属三分类（编译器内部规则，守门基底层）

对 component 候选（LHS=A，记录产物 = 全量产物组分的并集），推断映射后把**产物并集原子**分为：

- **A-可溯**：经 donor_to_union 映射到 A 的原子（现有 `new_union` 的补集）；
- **B-可溯**：new_union 中可归属到某共底物组分 B 的原子（原子级归属判定：对每个产物组分，若其原子集 = A-可溯 ∪ 空 ⇒ 纯可执行组分；若其原子集 ∩ new_union ≠ ∅ 且这些原子可对应 B 的原子（元素一致 + 有界子结构对应枚举，预算沿用映射枚举纪律）⇒ 含 B 贡献）；
- **不可归属**：new_union 中既不能归属 A 也不能归属任何 B 的原子（记录自身不配平/简写——corpus 记录**已声明** B 时出现此形态 ⇒ 源数据问题，R3-2 领地）。

### 5.2 机器规则（编译层，全部结构化、零例外）

1. **纯可执行组分**（原子全部 A-可溯，如主产物 P）：照常编译执行（含合法 add_atom 的只有一种情形——A 自身重排/ record 未声明来源的隐式原子；见规则 4）。
2. **B 来源整组分**（断连、原子全部 B-可溯，如还原型辅因子）：**声明式拷贝**（§四.3），**编辑通道零参与**——机器保证：该组分的任何原子不出现在 edits 里；执行产物多重集 = 可执行组分多重集（不含拷贝）。
3. **键合融合组分**（同一组分内混 A-可溯与 B-可溯原子，或 B 原子键合进 A 骨架——合成例 `CCO.CC→CCOCC`、配平例 `CCO.C=C=O→CCOC(C)=O` 均此形态）：**结构化拒 `cosubstrate_bonded_contribution_unsupported`**。机理落字：执行图 = render(底物)（0d.1 固定链），B 不在执行图内；表达键合融合的唯一途径是 add_atom 生成 B 原子再成键——即 R2-2 禁止的伪装通道；"声明融合产物 + 只执行 A 部分"不可行（同一连通组分的执行输出 ≠ 声明产物 ⇒ 诊断真失配，非 unknown）。**该拒因覆盖同根 LR/RL、可锚/不可锚、有机/辅因子、未知角色、配平/不配平，无例外**（Codex v4 复审 §4.3 同根覆盖要求）。
4. **不可归属原子**（component 记录里既非 A 也非 B 来源的 new_union 原子）：**保守拒 `cosubstrate_atom_source_unattributable`**。子选项：i) 保守拒（推荐）；ii) 允许并按 r31 R31-1 隐式来源披露（EAWAG 型待遇）。**推荐 i 的理由**：r31 的隐式来源许可是给"记录根本没写"的形态；corpus component 记录**写了** B——仍有不可归属原子意味着记录自身不配平，属 R3-2（v4b 记录自洽配平门）领地；本设计不依赖 v4b（§八），先行保守拒是自包含的诚实处置，v4b 若落地则两门正交叠合（R3-2 在适配层管方程平衡，本门在编译层管原子归属，互不替代）。**此选择交 mimo r32 CS3 裁定**。
5. **add_atom 伪装负控（机器断言，非文档）**：任何 component 候选产出的 spec，其 edits 中**不得存在**可归属 B 的 add_atom 原子——因规则 2/3 已结构性排除（B 整组分无编辑、键合融合整候选被拒），该断言作为**回归负控**存在（防未来实现漂移），触发即测试红。

### 5.3 产物多重集 gate 扩展（同源 + 版本登记）

- **扩展语义**：`执行组分多重集 ∪ 声明拷贝组分多重集 == 记录产物多重集`（严格身份、多重集、同源 `strict_identity_of`/`_executed_components_strict`/`_record_products_strict` 函数族——**不另写比较器**）；拷贝组分身份 ≠ 记录对应组分严格身份 ⇒ `declared_copy_mismatch` 拒；并集不齐 ⇒ 沿用 `product_set_mismatch` 语义。
- **落点子选项**：i) 公共函数 `compile_recorded_reaction` 加可选参数 `declared_copies`（缺省空 ⇒ **EAWAG/整串路径字节等价行为**，负控断言回归）（推荐——单一 gate 现场，符合"判据单一来源"纪律）；ii) corpus 侧包装函数自做并集核对（公共函数零字节改动，但比较逻辑出现两处）。**推荐 i**，代价是 recorded-source 版本升 2 并须交付"EAWAG 路径行为零变化"的字节级/行为级负控证据（r31：gate 改动须随版本登记；v4-R1 交付曾承诺"不借设计轮放宽 gate"——本扩展是**收窄式扩展**（多一道拷贝核对），不是放宽）。
- **版本**：corpus-retrieval-3（许可三分支）、pool-policy-4（池成员变化）、recorded-source-2（gate 扩展，若选 i）；三冻结 SHA、scorer/evaluator/AtomTool/判据一～五零触碰。

### 5.4 正负控矩阵（实施轮验收面；合成例全部 CCO、CC=O 级）

| 编号 | 形态 | 期望 |
|---|---|---|
| NC-1 | 键合融合 LR/RL（`CCO.CC→CCOCC` 两方向）| 结构化拒（`cosubstrate_bonded_contribution_unsupported`），零 spec 零 event（父基线 corpus-retrieval-2 同拒——**该两案从"许可拒"迁移为"守门拒"，拒因标签变化如实分类**） |
| NC-2 | 键合融合配平增强（`CCO.C=C=O→CCOC(C)=O`）| 同上拒（配平不可自救，Codex §4.2 原案保持红） |
| NC-3 | 手工构造"拷贝组分走 add_atom"的 spec | gate/机器断言拒（伪装负控——R2-2 负控条款的机器兑现） |
| NC-4 | 拷贝组分身份 ≠ 记录产物组分（篡改 SMILES）| `declared_copy_mismatch` 拒 |
| NC-5 | 不可归属原子形态 | 保守拒（5.2.4；mimo r32 CS3 可推翻） |
| NC-6 | 共底物 SMILES 不可解析 | `cosubstrate_unparseable` 拒，detail 保留声明 |
| NC-7 | 从被拒条目 detail 重建 spec | 违反许可边界（R31-8 落字沿用，测试断言 permission_note 在） |
| PC-1 | 辅因子对型（`CCO.c1ccncc1→CC=O+C1CCNCC1` 合成形：底物 CCO，共底物吡啶，产物乙醛+哌啶）：断连 B 来源整组分 | **编译成功 + 事件参与物 = {CCO(底物), 吡啶(cosubstrate,reactant)} / {乙醛, 哌啶(copy,coproduct)} + 中心 unknown + 冻结匹配 ⇒ matched_participant_coverage_partial（断言 partial，不断言 strict）**——这是本设计最重要的正控：解锁的是诚实 partial，不是 strict |
| PC-2 | 整串氧化（`CCO→CC=O`）、whole 多组分（`CCO.CC→CCOCC` 底物=全串）、EAWAG 水解（单组分 donor 酯，记录自身不声明共底物）| 全部照旧编译/执行/matched_strict（零回退；EAWAG gate 行为字节等价证据） |
| PC-3 | 池侧同签名合并（拷贝型 spec 与整串 spec 同净反应）| 合并留痕不双占槽 |

---

## 六、设计问题三：T1′ 边界重申——产物侧完整性核对不得倒逼忽略档放宽

### 6.1 要封死的洗白路径（逐条）

r30 G2-b 通道 2 / R2-4 警告的完整路径："A→P+NADH 被洗成 strict" 需要两步豁免，**两步都被既有裁定挡死**：

1. **产物侧**（忽略 NADH 型拷贝组分）：r28 T1′ ①②③——白名单只作用产物侧差集、仅无机小分子、逐项元素可追溯；辅因子（AMP/ADP/ATP/NAD(P)(H)/FAD/FMN/CoA/THF）**恒不忽略**（r28 A6："任何无碳规则都碰不到它们——留在 partial 是对的"）。本设计的拷贝组分是**声明参与物**，不是 ignore-tier 的 extras——两者身份不同，**不得**把声明参与物重分类为可忽略差集。
2. **反应物侧**（忽略 NAD⁺ 型 B）：r28 T1′ ②——反应物侧仅 H₂O 特例（溶剂活度簿记噪音），其余反应物侧无机（O₂/NADH/NH₃/Pi）**一律不豁免**（共底物=机制主张）；有机共底物更不在任何已裁定豁免面内。

**落字条款 D-T1′-1（规则文字，必加）**："本设计产出的共底物事件（含声明式拷贝组分）相对剥除共底物的参考边判 partial 是既定 P1 行为；coproduct_ignore_tier（proposed，未实施）的既有边界——白名单仅无机小分子、只作用产物侧差集、反应物侧仅 H₂O 特例、辅因子恒不忽略——在本设计落地后**不得以 partial 桶压力、完整产物集语义或供给收益为由放宽**；任何放宽都是口径级变更，须 teacher 裁定 + 新预注册（§九）。"

### 6.2 判据三补全许可不延伸（落字条款 D-T1′-2）

composition_only_hydrogen_equivalents 许可（注册补全规则）限定 H₂/[H] 氢当量（判据三既定）；**共底物来源整组分（有机/辅因子）不得登记为补全许可对象**，λ_s×Δ 补全对账不得为有机共底物组分给出覆盖 full——拷贝组分的覆盖语义只有"声明参与物 + 系数 unknown ⇒ coverage unknown_coefficients"一条路。

### 6.3 产物侧完整性核对的新形态（本设计自身）

事件产物集合 = 记录全部产物（含拷贝）——这是**比现行 EAWAG 面更强的完整性声明**（记录侧完整转写）；gate 扩展（§五.3）保证声明集与记录集多重集相等。落字条款 D-T1′-3："本设计的产物完整性 = 记录净方程的完整转写（执行 ∪ 拷贝 == 记录），与 coproduct_ignore_tier 的'忽略差集'语义互斥；报告并排出现两概念时必须分栏，不得合并叙述。"

### 6.4 激励倒挂如实落字（不修，只钉）

r31 H1b 指出的结构性倒挂（corpus 声明水 ⇒ 拒/未来 partial；EAWAG 简写 ⇒ strict 可达）在本设计落地后扩展为："声明共底物的诚实事件判 partial、省略共底物的简写记录 strict 可达"——**这是冻结判据既定性质 + 参考侧剥除口径的联合后果，本设计不修、不掩盖**；报告层落字 + 长线解法（参考侧 omitted_coproduct_scope，§九.3）登记为唯一根治路径。

---

## 七、设计问题四：计量语义——分母、桶归属与分层披露

### 7.1 判分面（零变更）

- **分母**：298 不变；无新分母。
- **桶归属**：本设计产出的事件落**既有** `matched_participant_coverage_partial` 桶（超集分支）；**不设新判分桶**——"共底物声明 partial"在判分面就是 partial，不因成因特殊而单列（成因分层属供给诊断，见 7.2）。
- **命中**：rank 只认 matched_strict（s5b_scoring.py:11–16）——partial 事件不进 hit@K；**hit@1 期望不变（76/298 注册基线口径），hit@5/partial 覆盖诊断改善**；任何命中数改善只能由新批同口径零 LLM 判分判定。
- **期望管理落字（D-M-1）**："共底物含计量性有机物/辅因物的子集在现行 P1 下无 strict 通路；本设计解锁的是诚实 partial 供给与审计链完整性，不是 strict 收益；204 是碳数零否的代理统计，不证明 204 题将 partial 命中（Codex v4 复审 §6 订正在案）。"

### 7.2 供给诊断分层（工程级披露，非判分）

1. **拒因直方图迁移披露**：`corpus_cosubstrate_participants_unsupported`（现 1,323 单类）分裂为 `cosubstrate_bonded_contribution_unsupported` / `cosubstrate_atom_source_unattributable` / `cosubstrate_unparseable` / （编译成功子集不再计拒）——直方图名附 `includes_precompile_permission_rejects` 同款机读标签（R31-4 体例）；**迁移是通道开放不是错误修复**，headline 禁句沿用 R31-6。
2. **tier 计数语义标签**：`n_strict_exact`/`n_cn_candidate`/`n_corpus_*` 继续携带 `tier_count_semantics: "retrieval_candidates_including_precompile_rejected; not compiled/supply counts"`（R31-4 沿用）。
3. **"共底物含辅因子"子集单列**（分层披露的机读字段，供给诊断层）：
   - `n_cosubstrate_declared_events`（本通道产出事件数）；
   - `cosubstrate_class_profile`：按已披露代理分类复用（balance_like/organic_like 频次 4,878/11,052；NAD(P) 系 1,138+245+111），**标签必须写明"碳数零否代理，非化学生物角色规则"**（Codex v4 复审 §6：CO₂ 含碳被归 organic_like、铵无碳被归 balance_like 的已知失真）；
   - `n_cosubstrate_partial_matches`（判分后聚合：本通道事件的 partial 命中数）——**带 partial 语义标签，不与 hit 混列**。
4. **机读"拷贝组分"披露**：每事件审计 detail 的 `declared_copy_components`（§四.3）+ 聚合计数 `n_events_with_declared_copy_components`——防"拷贝=已执行"误读的最小机读面。
5. **同题位次效应**（若未来选项 c 落地才相关）：r28 B4 位次/新覆盖分离计数条款预置进 §九预注册草案，本轮不启用。

### 7.3 供给预期落字（R2-2 第五要点的兑现）

"诚实声明共底物的事件相对剥除共底物的参考边判 partial——组分级供给面 204 题子集在现行 P1 下无 strict 通路，其占比按 unknown 登记，不得按 204 全额外推 strict 收益；+84（v4 检索供给面数字）不是 strict 可达数字"（mimo r30 R2-2 原句沿用 + Codex v4 §6 订正合并）。

---

## 八、设计问题五：实施分期与 v4b 接口边界

### 8.1 分期（三轮，每轮验收面固定）

| 轮 | 内容 | 验收面 | 产物 |
|---|---|---|---|
| **D1 规则文字轮（本轮）** | 本设计书 + mimo r32 评审 + teacher 裁定 | 三方评审收口：r32 回应与程序证据互证；teacher 对 §十一口径级决策点逐项拍板（或明确挂起+归属）；设计冻结为 DS-1 | 本文件 + `docs/mimo_ppv1_chem_review_request_r32.md`（+后续 r32 回应落盘） |
| **D2 编译实现轮** | §四/§五 全部规则：许可三分支、participants/states 装配、gate 扩展（recorded-source-2）、正负控矩阵 NC-1..7/PC-1..3、直方图/诊断字段、版本登记（corpus-retrieval-3/pool-policy-4） | ①入口消费矩阵先行（AGENTS.md 返工教训 1）；②父基线（corpus-retrieval-2）红绿：PC-1 形态真行为红（父拒、新编译）、NC-1/2 保持拒（拒因标签迁移单列）、PC-2 零回退；③EAWAG/整串路径行为等价证据（gate 扩展不改变无拷贝路径）；④池深探针前后对照（298 底物 substrate_smiles 批准字段，同 v4-R1 §六体例）；⑤G01 隔离 + 金额回归零回退 | 实施交付书 + 测试 + 新证据目录 |
| **D3 评审轮** | Codex 复审（公开链探针：原生事件参与物/拷贝披露/负控族/池深）+ mimo 化学评审（实施交付随轮，场景 1）；通过后**才可**考虑新批登记 | P1 清零 + mimo 回应互证；发车义务沿 Codex v4 复审 §7 六条清单（新登记/新身份/双门/冒烟/金额/终局归因）——**chain11 封存批零回写，新批新根** | 复审报告 + mimo 回应 + 新登记草案 |

### 8.2 与 v4b（编译墙消融线）的接口边界（本设计**不要求 v4b 改其范围**）

- v4b 登记范围（维持不动）：R1-2（CN 归一失败回退计数）、R3-1（通配拒因三子类细分）、R3-2（记录自洽配平门）、R3-3（底物组分必须变化门）、stereo 消解设计轮、编译墙预算调优。
- **依赖方向：零依赖**。本设计的原子归属门（§五.1–5.2）与 R3-2（方程平衡门）是**两个正交轴**：本门管"产物原子归谁"（编译层、corpus component 专用），R3-2 管"方程两侧元素账"（适配层、全记录通用）；R3-2 未落地时本设计自包含运行（NC-5 保守拒兜底不可归属形态），R3-2 落地后两门叠合（R3-2 会更早拒掉自不平记录——行为是收紧不是冲突）。R3-3 同理：底物恒等仅共组分变的候选在本设计下走"可执行子集 transform_no_change ⇒ 编译拒"，与 R3-3 专用诊断不冲突不依赖。
- **不反向要求**：本设计不要求 v4b 交付任何项作为前置；v4b 也不消费本设计的任何新字段（拷贝披露字段是 corpus 通道私有诊断）。
- **并行纪律**：两线各自独立版本登记、独立归因；若同批落地，池深对照须各出单变量臂（v3 臂体例）。

---

## 九、设计问题六：预注册路径（选项 c 的独立字段草案；本轮零实施）

### 9.1 字段草案（预注册独立字段，不并入任何现行判分口径）

- **字段名（草案）**：`co_substrate_participant_tier`（事件/参考边比较层的豁免档）。
- **四元组结构**（沿 r28 C1 体例，防档位定义漂移）：
  1. `tier` ∈ {"none"(默认), "declared_cosubstrate_exempt"}（豁免范围：**仅限**"来源记录字段完整 + 声明式拷贝 + 中心 unknown"的共底物事件——本设计 §四.3 产物；无来源字段的共底物声明永不豁免）；
  2. `exempt_identity_hash`：豁免对象身份集的 cn 身份层版本化哈希（无机小分子白名单同款机制；含辅因子对如 NAD(P)⁺/H 的身份清单显式列入并版本化——**这正是须 teacher 逐项拍板的清单**）；
  3. `direction_policy`：豁免仅反应物侧声明共底物 + 产物侧其来源整组分（两侧绑定，禁单侧——防"A→P+NADH 单侧豁免"洗白）；
  4. `disclosure_switch`：机读披露开关（豁免发生时逐边记 `exempted_participants` + 首批 post-hoc 敏感性表）。
- **生效护栏**：teacher 裁定前置（唯一入口）；旧批/旧线**零回写**（headline 恒为现行口径直到裁定；封存 run 只读）；首个生效批双口径并列 + post-hoc 标签 + 位次效应/新覆盖效应分离计数（r28 B4/C1 ⑧ 全套）；r30 G4-2 滑坡警告原文引用进预注册正文；mimo 场景 1 评审前置（判据级变更）。

### 9.2 语义草案（净共底物比较，一段）

比较时从事件与参考边双方参与物集合中**剔除"已豁免身份清单内 + 带完整来源声明字段"的共底物及其来源整组分产物**，再按 P1 集合语义比较；剔除记录逐边机读；参考侧未声明的组分永不因本档被加入（不反向要求参考图）。**该语义变更触碰 P1 冻结口径邻接面——判据正文或评测语义的任何改动须走 ppv1-criteria-v2 起的新版本流程（冻结稿"冻结后变更"条款），本草案只是设计件，不构成任何现行批的判分依据。**

### 9.3 长线替代方案（登记，更干净）

r28 C1 ⑤ 原案：参考图提取对每边显式声明 `omitted_coproduct_scope`（剥了什么），判分只豁免参考**自己声明剥掉**的那类——根治"声明口径差"（A1 错配），豁免漂移风险消失。属**参考侧/金标侧变更**，须 teacher + 用户裁定（参考图构建在金标侧路径），本设计仅登记不推进。激励倒挂（§六.4）的唯一根治路径也在此（参考侧声明剥除范围后，"声明水"与"简写"两侧口径对齐）。

---

## 十、推荐方案汇总（六问题各一句）

1. **事件表示**：选项 a——B 进反应物侧参与物（role=cosubstrate、系数 unknown）、B 来源**整组分**产物声明式拷贝（来源字段完整、中心 unknown）、键合融合子集保守拒；b 降级为守门基底层不作事件表示；c 仅出预注册草案交 teacher。
2. **原子级守门**：编译器原子归属三分类（A-可溯/B-可溯/不可归属）+ 三条机器规则（整组分无编辑、键合融合拒、不可归属保守拒）+ add_atom 伪装机器断言负控 + gate 同源扩展（执行 ∪ 拷贝 == 记录，recorded-source-2 版本登记，EAWAG 字节等价负控）。
3. **T1′ 边界**：三条落字条款（D-T1′-1 边界不得倒逼放宽 / D-T1′-2 补全许可不延伸有机共底物 / D-T1′-3 完整转写与忽略差集互斥分栏）+ 激励倒挂如实落字不修不掩盖。
4. **计量语义**：判分面零变更（partial 桶、298 分母、rank 不动）；供给诊断分层（拒因迁移披露、辅因子子集单列、拷贝组分机读披露、碳代理标签钉死）；hit@1 期望不变如实登记。
5. **实施分期**：D1 规则文字轮（本文件+mimo r32+teacher）→ D2 编译实现轮（三分支+守门+正负控+版本矩阵+父红绿）→ D3 评审轮（Codex+mimo+新登记）；与 v4b 零依赖正交（原子归属门 ≠ R3-2 配平门），不要求 v4b 改范围。
6. **预注册路径**：co_substrate_participant_tier 四元组草案（tier/身份哈希/双侧绑定方向策略/披露开关）+ 旧批零回写 + teacher 前置 + 滑坡警告引用；长线登记参考侧 omitted_coproduct_scope。

---

## 十一、需 teacher 裁定的口径级决策点清单

| 编号 | 决策点 | 选项 | 本设计倾向 | 级别 |
|---|---|---|---|---|
| **T-1** | 选项 c（判分面豁免）是否立项 | 立项走 §九预注册 / 不立项（维持 partial） | **不立项**（先解锁 a，观察首批 partial 分布再议） | 口径级（P1 邻接面） |
| **T-2** | corpus 净方程事件的 `participant_list_status` | source_complete / declared_complete / partial | declared_complete（保守：声明完整但系数全 unknown 的审计轴含义未经裁定的最窄声明）——**source_complete 与 declared_complete 的判据二/三消费差异须 teacher 确认** | 口径级（审计轴输入） |
| **T-3** | 不可归属原子处置（§五.2.4） | 保守拒 / 允许带披露（EAWAG 型待遇） | 保守拒（记录已声明 B 仍有不可归属原子 = 源数据问题）；**mimo r32 CS3 先裁，teacher 终裁** | 化学边界（非判分口径） |
| **T-4** | 供给诊断分层字段是否随 D2 一并机读（§七.2） | 一并 / 后置 | 一并（防误读优先） | 工程披露级（非口径） |
| **T-5** | 长线参考侧 omitted_coproduct_scope 是否立项（§九.3） | 立项 / 挂起 | 挂起登记（金标/参考侧变更，须用户逐次拍板） | 参考侧（须用户） |

（T-1 若立项，其豁免身份清单（哪些辅因子/共底物身份进 exempt_identity_hash）逐项拍板是 teacher 的后续义务，不在本表展开。）

---

## 十二、诚实边界与 unknown 登记

1. **整组分/键合两子集在 1,323（及 204）内的占比：unknown**——缺只读聚合计数探针（可隔离复跑，不碰金标；建议 D2 前置执行，结果只进聚合计数）。
2. **204 = 碳数零否代理统计**（Codex v4 §6 订正）：不证明 204 题已 partial、不证明全部无 strict 通路、不外推命中；NAD(P) 系 1,138+245+111 是频次计数非题数。
3. **本设计对 hit@1 的预期贡献 = 0**（现行 P1 下无 strict 通路）；对 hit@5 的贡献以新批复测为准；任何数字 298 题域标签。
4. **r32 回应的执行类断言**按 AGENTS.md 采信限度：与程序证据互证为止，"待执行验证"标注保持原文不回写。
5. **本设计书不构成实施批准**：D2 开工须以 D1 三方收口（含 teacher 对 T-1..T-5 的拍板或显式挂起）为前置；Codex v4 复审 §4.3"不以方向无冲突预支批准"条款适用。
6. **零金标自查**：全文只含已披露聚合计数与合成例（CCO、CC=O 级，与公开 Codex v4 复审反例族同源）；成稿泄露扫描见附录 A。

---

## 十三、参考件索引

- 判据：`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md`
- Codex：`docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_CODEX_REVIEW_2026-10-10.md`（§4/§4.3/§5/§6/§7/§8）；`docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_R1_CODEX_REVIEW_2026-10-10.md`（放行）
- mimo：`docs/mimo_ppv1_chem_review_response_r28.md`（T1′ 九条件）；`r30.md`（G2/R2-2/R2-3/R2-4/G4）；`r31.md`（H1/H2/H3、R31-1..R31-8）
- 交付/登记：`docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_WV41_DELIVERY_2026-10-10.md`（共底物构成谱）；`docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_R1_DELIVERY_2026-10-10.md`；`docs/S5B_V4_RETEST_REGISTRATION_2026-10-10.md`（r31 措辞护栏、chain11 期望）
- 任务书：`docs/TASK_V43_PPV1_S5B_HIT50_V4_DRAFT_2026-10-10.md`（§4.2 共底物声明化设计件占位）
- 源码（只读，本 HEAD）：`src/pathway_v43/pollutant/recorded_source.py`（:719/:878–905/:1009/:1085–1113）、`s5b_compiler.py`（:540–624 新原子落位）、`production.py`（:209–245 参与物装配）、`hypothesis.py`（:77–112 角色枚举、:578 构造校验）、`evaluation.py`（:1029–1109 match_reference_edges）、`s5b_scoring.py`（:11–16 主口径）

---

## 附录 A：金标泄露扫描记录（成稿后执行，2026-10-10）

- **扫描对象**：本文件与 `docs/mimo_ppv1_chem_review_request_r32.md`（成稿终版）。
- **比对靶**：`/Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/ec298_gold_readonly/questions.jsonl`（298 行；392 个 distinct substrate/product SMILES 取值。**仅扫描用**——靶文件的任何内容未写入两份成稿）。
- **方法**：①从两份成稿抽取全部**结构性 SMILES token**（反引号内全部反应例串，按 `→`/`+`/`.` 切分至组分级）；②泛扫正文中的类 SMILES 字符集连续串（防正文裸写结构）；③每个 token 经 RDKit 判定可解析性后，与金标全集做**四级比对**：整串相等 / 点式组分级相等 / RDKit canonical 相等 / 组分级 canonical 相等。
- **结果：结构性 token 四级比对 0 命中**。两文件全部结构性 token 为合成例族：CCO、CC、CCOCC、CC=O、C=C=O、CCOC(C)=O、c1ccncc1、C1CCNCC1 及其组合串（`CCO.CC`、`CCO.C=C=O`、`CCO.c1ccncc1` 等）——与公开 Codex v4 复审反例族同源；成稿刻意未使用任何命中金标的平凡 SMILES（已知金标含若干 ≤8 字符平凡串；v4-R1 交付 EAWAG 水解正控中的酸/醇产物串命中金标，故本设计书对该例一律以"酯→酸+醇（EAWAG 水解正控）"指代、不写出结构串）。
- **非结构性泛扫 token 逐条披露（文字缩写/变量，非结构串；其四级比对偶合命中为缩写巧合，不构成泄露）**：
  - **CN**（多处）：**电荷归一身份的仓内标准缩写**（"CN 检索/CN 身份/CN 分层"，与 mimo r30/r31 请求及全部 v4 文档同款用法）+ 规则文字 CN⁻（r28 T1′ 恒不忽略条款公开原文）——非氰基结构串、不来源于金标；
  - **CO**：CO₂（r28 公开规则文字）经 Unicode 下标截断的碎片——正文无裸 CO 结构串；
  - **A、B、P**：设计叙述变量（底物 A、共底物 B、主产物 P），非结构串。
- **扫描执行**：本地 python（RDKit 判定 + 四级比对，`-B`、无字节码/缓存写入、靶文件只读）；脚本与完整 token 清单随设计轮证据留存（tmp，不入仓）。
- **结论**：两份成稿对金标零泄露（结构性 token 四级 0 命中；泛扫命中项均为文字缩写偶合，已逐条披露）。

---

## §12 决策点处置记录（2026-10-10，主会话）

r32 回应（docs/mimo_ppv1_chem_review_response_r32.md）：**有条件通过 D1 设计轮**
（零判据冲突；16 条修改建议落字 + CS2c 探针为 D2 前置；T-1..T-5 维持
teacher 裁定不预支批准）。T 决策点弹窗用户未作答——**主会话按推荐档
先行执行，全部登记为"主会话默认、待用户/teacher 随时改判"**：

| 决策点 | 处置（默认档） | 依据 |
|---|---|---|
| T-1 判分面豁免档 | **暂不立项**——先按方案 a 落地观察 partial 分布 | 设计书+r32 双方倾向；防"以放宽换通过" |
| T-2 participant_list_status | declared_complete | 设计推荐（如实反映记录声明面） |
| T-3 不可归属原子 | **保守拒（子选项 i）**，拒因子分列 mapping_fallback 伪影/源数据真缺 | mimo r32 CS3 已裁（R32-CS3-1） |
| T-4 供给诊断字段 | 随 D2 一并机读 | 设计推荐 |
| T-5 参考侧 omitted_coproduct_scope | **挂起登记不立项** | 涉金标/参考图侧须用户单独授权 |

16 条 r32 修改建议与 NC/PC 控件矩阵增补（NC-8..12/PC-4/5）在 D2
实施轮落字；CS2c 探针（treatment 随记录书写风格翻转的披露计量）为
D2 前置门。D1 设计轮收口状态：`design_approved_with_conditions`。
