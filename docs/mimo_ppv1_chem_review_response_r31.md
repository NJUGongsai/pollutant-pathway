# mimo 化学评审回应 r31（2026-10-10）

- 通道：opencode run -m opencode/mimo-v2.6-flash-free（免费档，通道 A；主会话转发落盘）
- 请求：docs/mimo_ppv1_chem_review_request_r31.md（v4-R1 共底物诚实拒许可范围，H1-H3）
- 只读 provenance：评审员以读取工具核对源码/文档，无 shell 执行权限；执行类断言均自带"待执行验证"
- 原始流：docs/review_evidence/ppv1_r31_mimo_2026-10-10/raw.txt
- 采信原则：与程序证据互证为准

---


✱ Glob "docs/mimo_ppv1_chem_review_*r3*.md" 4 matches
✱ Glob "docs/mimo_ppv1_chem_review_request_*.md" 12 matches
→ Read docs/mimo_ppv1_chem_review_request_r31.md 
✱ Grep "corpus_cosubstrate_participants_unsupported" in . · 100 matches
✱ Grep "coproduct_ignore_tier" in . · 100 matches
→ Read src/pathway_v43/pollutant/recorded_source.py [offset=60, limit=200]
→ Read src/pathway_v43/pollutant/recorded_source.py [offset=600, limit=360]
✱ Grep "compile_recorded_reaction" in src/pathway_v43/pollutant · 7 matches
✱ Grep "find_corpus_recorded_exact|find_recorded_exact" in src · 12 matches
→ Read src/pathway_v43/pollutant/recorded_source.py [limit=240, offset=960]
→ Read src/pathway_v43/pollutant/s5b_builder.py [limit=240, offset=370]
→ Read docs/mimo_ppv1_chem_review_response_r30.md 
✱ Grep "compile_status|compile_reason|co_substrates" in src/pathway_v43/pollutant · 23 matches
✱ Grep "add_atom|new_atom" in src/pathway_v43/pollutant · 18 matches
→ Read src/pathway_v43/pollutant/recorded_source.py [limit=340, offset=260]
✱ Glob "tests/test_ppv1_s5b_hit50_*.py" 11 matches
✱ Grep "^#+ |^\*\*判据|^### " in docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md · 10 matches
✱ Grep "corpus|unsupported" in src/pathway_v43/pollutant · 0 matches
✱ Grep "corpus|recorded" in src/pathway_v43/pollutant · 2 matches
✱ Grep "cosubstrate|co_substrate" in src/pathway_v43/pollutant · 23 matches
→ Read docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md [limit=50, offset=143]
✱ Grep "compile_failure_histogram|n_strict_exact|corpus_diagnostics" in src · 7 matches
✱ Grep "def test_|positive|正控" in tests/test_ppv1_s5b_hit50_v4_wv41.py · 39 matches
✱ Grep "record_self_unbalanced|substrate_identity_no_change|opposite_direction_no_alignment|cn_charge_normalization_fallback" in src · 0 matches
→ Read tests/test_ppv1_s5b_hit50_v4_wv41.py [limit=120, offset=312]
→ Read tests/test_ppv1_s5b_hit50_v4_wv41.py [limit=80, offset=836]
✱ Grep "§六|## 六|分层计数|检索候选" in docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_R1_DELIVERY_2026-10-10.md · 10 matches
→ Read docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_R1_DELIVERY_2026-10-10.md [limit=80, offset=142]
✱ Grep "corpus|mapped_lhs|def templates_similar_to|co_substrate|RHEA" in src/pathway_v43/services/analog_source.py · 52 matches
→ Read src/pathway_v43/services/analog_source.py [limit=120, offset=355]
✱ Grep "template_elements_fit|def compile_donor_template|full.*落位|完整.*落位" in src/pathway_v43/pollutant/s5b_compiler.py · 4 matches
✱ Grep "corpus_templates_v1" in . · 40 matches
✱ Grep "lhs|reactant|component" in src/pathway_v43/adapters/analog_index.py · 5 matches
✱ Grep "lhs|rhs|co.?substrate|reactant" in scripts/build_analog_v2.py · 43 matches
✱ Grep "templates_v1|template_id|build.*template" in scripts · 7 matches
✱ Grep "corpus_templates_v1(如何|构造|生成|来源|由)|模板来源|analog 通道.*共底物|analog.*co.?substrate" in . · 7 matches
✱ Grep "template_id|lhs|donor" in scripts/phase_d_asset_stats.py · 3 matches
✱ Grep "corpus_templates_v1" in docs · 12 matches
→ Read src/pathway_v43/pollutant/production.py [limit=55, offset=195]
→ Read src/pathway_v43/pollutant/evaluation.py [limit=70, offset=1020]
→ Read src/pathway_v43/pollutant/s5b_builder.py [limit=75, offset=610]
✱ Grep ""mapped_lhs": "[^"]*\.[^"]*"" in assets/analog/corpus_templates_v1.jsonl · 5 matches
✱ Grep "new_atom_unanchorable|完整模板落位|no_alignment\(" in src/pathway_v43/pollutant/s5b_compiler.py · 2 matches
✱ Grep "donor_A_smiles.*字段|corpus_v1 (行|schema|字段)|product_B_smiles" in docs · 20 matches
Error: Connection lost while reading the response: ECONNRESET: The socket connection was closed unexpectedly. For more information, pass `verbose: true` in the second argument to fetch()
✱ Grep "matched_strict|rank|tier" in src/pathway_v43/pollutant/s5b_scoring.py · 41 matches
✱ Grep "n_cosubstrate_participants_unsupported|n_strict_exact|n_cn_candidate" in src/pathway_v43/pollutant/recorded_source.py · 5 matches
# mimo 化学评审回应 r31 —— v4-R1 共底物诚实拒的许可范围与边界（H1–H3）

**执行边界声明（先行）**：本轮只用读取类工具（glob/grep/read）核对仓库源码与文档；未运行任何测试或脚本，一切行为类断言标"待执行验证"；引用行号均为本轮实读；未访问任何金标/题面/gitignored 目录；未修改任何文件。核对范围：`recorded_source.py`（全文关键段）、`s5b_builder.py`、`s5b_compiler.py`（grep 行级）、`production.py`、`evaluation.py`（`match_reference_edges` 段）、`s5b_scoring.py`（grep）、`search.py`（grep）、`tests/test_ppv1_s5b_hit50_v4_wv41.py`、冻结判据稿判据二段、v4-R1 交付书 §六、你 r30 的 G2/R2-2 回应全文。

**一处透明披露（请求体例，与 r29/r30 同款）**：发来的边界头写"三个判断面（coproduct_ignore_tier 主面 / r27 条款项采纳核对 / stereo 消解型设计复审）"，但附在后面的请求原文是 **r31 的 H1–H3**（与 `docs/mimo_ppv1_chem_review_request_r31.md` 实读 89 行逐字比对一致）。该三判断面头系模板复用残留（`docs/review_evidence/ppv1_r30_mimo_2026-10-10/header.md:1`、`ppv1_r29_mimo_2026-10-10/header.md:1` 实读同文）。我按**附后的请求原文（H1–H3）**逐条作答。coproduct_ignore_tier 维持 r28 T1′ 九条件已裁定状态（`mimo_ppv1_chem_review_response_r28.md:150`、r29 复核），本轮全仓 grep 其在 `src/` 零命中、仍是 proposed 未实施；stereo 附面不在这份请求里。若确需对三判断面另开一轮，请重新送审对应请求原文。

---

## H1（诚实拒的许可范围）

### 1) 结论

**有条件同意：范围恰当，本轮无例外正确——不存在"必须例外放行"的形态；但 H1b 的分界规则文字必须按"记录保真边界"重写，现在的表述方式若被读成"原子来源问题已解决"即构成化学误导。条件 = 三条规则文字（R31-1/2/3）落字。**

### 2) 机理展开

**H1a——先否掉请求里隐含的前提：产物多重集 gate 无法"闭合来源"。** gate 比较的是执行产物组分严格身份多重集 == 记录产物多重集（`recorded_source.py:1085-1113` 实读），它只回答"做出了什么"，不回答"原子从哪来"——它结构上没有原子来源信息。反证就在本批数字里：修前 42 个组分 spec 全部通过了这道 gate 并拿到 matched_strict（交付书 :84 实读："1 compiled spec + 1 事件(水折成 add_atom 新原子)+ matched_strict(v4 正控即此形态)"）。gate 通过 + matched_strict 授予，同时原子是伪造的——这证明**gate 不是来源守门，任何"gate 能闭合共底物来源"的例外设计都不成立**。

再按形态逐类看，哪些即使放行也编译不出坏事件、哪些会出：

- **共底物恒等留存在产物（催化剂样）**：X 在 donor 与 products 中同为断连组分 ⇒ 单组分 LHS 执行长不出断连 X ⇒ `new_atom_unanchorable`（`s5b_compiler.py:596` 实读）或 product_set_mismatch 诚实拒——这类**编译链本来自会拒**，编译前拒只是提前、统一（读码推断，待执行验证）。
- **共底物原子进入产物（可锚有机、水、乙烯酮）**：必须经 add_atom 伪造才能过 gate——正是被禁的形态（8 案反例族，`tests/…_v4_wv41.py:412-422` 实读；探针 `probe_stdout.log:1-8` 显示 0 池 spec，执行面待执行验证）。
- **唯一机器可判定的"零伪造"候选形态**：全候选映射 `new_union == ∅`（所有产物原子可溯至被匹配底物组分）且 共底物严格身份 ∉ 记录产物多重集 ⇒ 事件一个伪造原子都没有，共底物只是被省略的"声明了但对产物零贡献"的旁观/环境反应物。**但这不是必须例外**：(i) 它违反本轮"无例外条款"；(ii) 它违反 R2-2 字面（已声明反应物仍被剔除出事件）；(iii) 供给上无必要——修后池深/空池率已回到 v3 臂基线（交付 §六.1 实读），corpus 组分级本来净贡献 0（与既有池同签名合并）。故**本轮不豁免**，仅作未来登记（见 R31-2）。真正损失的化学能力是"水/质子已声明的水合、水解、缩合"这一类——但注意 EAWAG 面同化学照旧供给（见 H1b），所以损失被记录写法差异部分对冲，不构成 must-exempt。

**H1b——两个形态化学语义确实不同，但不同的维度是"记录保真"，不是"原子来源"。** 先给代码事实：

- 分界的现行实现是：corpus 侧 `kind == "component" and co_comps` ⇒ 编译前拒（`recorded_source.py:878-905` 实读）；整串语义 donor 全串进 LHS（:829-839、:906-912），底物必须 CN 命中 donor **全串**（:772-783）或 donor 本身单组分（:785-788）——**没有任何已声明组分被剔除**。
- EAWAG 侧 `find_recorded_exact` 无共底物逻辑（:620-706 实读），donor 全串作 LHS 编译（:675-679）。酯水解记录（donor=酯，产物=酸+醇）本身不配平（+H2O），`n_donor < n_union` 走加成分支，缺的那个氧落进 `new_union` ⇒ **add_atom 伪造**，测试注释自己写着"跨组分断裂+新原子"（`tests/…_v4_wv41.py:839、863` 实读），且该正控拿 matched_strict（交付 §四实读；断言细节测试内未逐字确认处标未确认）。

所以对请求问的"是否冲突"：**与 r30 R2-2 字面不冲突**——R2-2 的禁止对象是"共底物来源组分"，前提是记录**声明了**共底物（G2 语境）。EAWAG 型记录根本没写水，系统没有丢弃任何声明，事件忠实转写记录自己的净变换简写，属"记录自身省略"（record-shorthand），不是"系统删改记录"（record-falsification）。**但两者在事件层是同一类原子来源缺陷**：同一条酯→酸+醇化学，corpus 侧因 donor 里打了 `.O` 被拒，EAWAG 侧因没打 `.O` 放行并授 matched_strict——**被执行事件的化学内容完全相同， treatment 只随记录书写风格翻转**。这就是必须落字的地方：分界保护的是记录保真，不是原子来源闭合。

由此带出一个设计轮必须正视的激励问题：参考侧系统性剥除无机/环境参与物（r28 P3 口径；`evaluation.py:1062-1068` 实读超集⇒partial），**诚实声明水 ⇒ partial，省略水（简写）⇒ 可 strict**——现行结构在奖励简写、惩罚诚实声明。这不是本轮要修的（判据已冻结），但显式参与物设计轮若不解决它，水解类诚实事件将系统性判 partial 而简写版判 strict。

**R2-2 字面边界一句给死**："共底物原子经 add_atom 伪装新增"的禁令覆盖**记录已声明**的共底物；记录未声明的隐式来源（水/受体/氧）不在禁令内、仍会经 add_atom 产生（EAWAG 水解正控即此），其元素账按判据二 unknown 登记。任何"本轮后事件不再出现无声明来源原子"的表述 = 错误，P1 级。

**与冻结判据冲突检查（P1 义务）**：未发现冲突。拒因在供给侧、编译前，不触碰判据一~五任何事件侧判定路径；`compile_recorded_reaction` 内部无 corpus/共底物逻辑（:1009-1129 实读）；版本登记属实（retrieval-2 :112、pool-policy-3 `s5b_builder.py:396`）。"字节零改动"类断言无 shell 不可验，待执行验证。

### 3) 可直接落进规则文字的修改建议

- **R31-1（H1b 分界文字，必加，替换现有含混表述）**："本轮禁止的形态 = 记录**已声明**的反应物组分被剔除出事件（记录保真违例，其原子进入产物必经伪造通道）；继续放行的形态 = 记录**自身**以净变换简写、未声明隐式参与物（水/受体/氧），事件忠实转写记录声明，产物中原子来源按判据二记 unknown（coefficient unknown，`recorded_source.py:1115` 弹除系数）。两种形态的事件都可能含无声明来源的原子；本轮消除的是前者（记录保真），**不是**后者（原子来源闭合）。禁止将本轮收口表述为'事件不再出现无来源原子'或'原子伪造通道已全部关闭'。"
- **R31-2（H1a 未来豁免候选，仅登记不生效）**："本轮无例外。唯一机器可判定的未来豁免候选形态登记如下、本轮禁止实现：全候选映射 `new_union=∅` 且 共底物严格身份 ∉ 记录产物多重集（⇒ 事件零伪造原子、共底物对产物零贡献）；生效须独立评审 + 预注册（档位+白名单哈希+方向策略+披露开关四元组，同 r28 T1′ 体例）+ 机读披露字段 `omitted_declared_reactants` + 首批 post-hoc 敏感性表；不得以元素/角色/分子白名单形式变相提前实现。"
- **R31-3（对称性披露）**："同一条'酯→酸+醇'化学，corpus 面（记录声明水）拒、EAWAG 面（记录未声明水）放行并可授 matched_strict——treatment 差异仅源于记录书写风格，报告中并列出现时必须同句披露该事实，不得只呈现其中一面。"

### 4) "程序上诚实但化学上误导"风险点

- **风险 1（最实）**："共底物原子伪造通道已关闭"——EAWAG 水解正控保留的正是 add_atom 伪造一个水氧（`tests/…_v4_wv41.py:839` "跨组分断裂+新原子"）。headline 若这么写，是把通道关闭说成化学闭合。
- **风险 2**："EAWAG 记录 donor 均单组分"是事实前提，库资产本轮未读、**未确认**；但安全不依赖它——即使存在多组分 EAWAG donor，严格身份全串相等（:664）+ 编译完整落位（`s5b_compiler.py:289、733`）也会把它挡成全串语义或 no_alignment（读码推断，待执行验证）。
- **风险 3**："组分级供给归零 = 能力删除"与反向的"归零 = v4 接线失败"都错：这是许可收缩，能力恢复唯一路径 = 显式参与物设计轮 + 独立评审；修后净池贡献 0 是与既有池同签名合并的结果，不是检索面消失（交付 §六.2 实读）。

**不确定项**：1,323 个拒因里"水/质子类 vs 计量有机类"的分层占比——未确认，缺只读聚合计数探针（不碰金标）；探针/交付书全部执行数字——待执行验证。

---

## H2（拒因与披露语义）

### 1) 结论

**有条件同意：代码层披露基本到位（compile_status="unsupported" + compile=None + permission_note 足以防住程序误读），但计数语义只写在交付文档、没进数据结构本身——三处 in-band 标签必须钉死，否则文档外的任何消费者都会把检索层计数读成供给数。**

### 2) 机理展开

**a) "declared but not consumed" 够不够？** 程序消费端：被拒条目 `compile=None, compile_status="unsupported", compile_reason=corpus_cosubstrate_participants_unsupported`，detail 含 record_key/行号/donor 整串/方向/master/共底物 SMILES+严格身份/记录产物/permission_note（`recorded_source.py:882-905` 实读）；builder 拿到 None 走 `_record_failure` 不入池（`s5b_builder.py:520-524`）；判分/公共链只消费池 spec，不消费候选条目（evaluation/s5b_scoring grep 实读，rank 只认 matched_strict，不消费 tier：`s5b_scoring.py:12-14、443`）。**这条链是闭的，"待编译"误读在代码层挡住了。** 三处残留：

1. **tier 先计数、后拒因**：`n_strict_exact`/`n_cn_candidate` 在 :861-866 计数，:878 才拒——被拒候选**确实**计入分层（请求自述属实）；builder 侧同理（`s5b_builder.py:515-519` 先按 tier 计、:520 才处理 None）⇒ `n_corpus_strict_exact`（:616）也含被拒条目。文档标了"检索候选分层,非编译/供给数"（交付 §六.2 实读），但**标签在文档里、不在数据里**——manifest 消费者只看 JSON 时无从知道。
2. **"declared but not consumed" 字样住在一个死分支里**：spec 级 `co_substrate_semantics = "declared_conditional_participants_not_consumed_as_substrate…"`（:940-948）只在 `co_comps` 非空时走到，而 component+非空 co_comps 现在**永远**在 :878 被拒——component 必然伴随非空 co_comps（:784-792、:848 构造保证）。即该字段第一分支在 corpus 面已不可达（读码推断，待执行验证），真正的披露字段是 permission_note。死代码里的旧语义字符串会误导后续读码者以为组分 spec 还能编译。
3. **"unsupported" 一词承担两种语义**：编译能力不足（product_set_mismatch 等）与许可拒绝（本轮拒因）共用 compile_status="unsupported"，靠 reason 区分。直方图已分（:971），状态词未分。

**b) 还有哪些报告层措辞要钉死**（含请求已标的一条 + 我补的）：

- 请求已标：strict/cn 分层计数 = "检索候选分层,非编译/供给数" ✓——但须**进数据**（见 R31-4），且 builder 的 `n_corpus_strict_exact/n_corpus_cn_candidate` 同样含被拒条目，标签必须同步覆盖。
- `compile_failure_histogram` 这个**名字**暗示"编译被尝试过"，而 corpus_cosubstrate 类目从未送编译——须注明"含编译前许可拒，非编译尝试失败"。
- 直方图迁移（stereo_edit 310→18、new_atom_* 归零）是**通道关闭**不是错误修复（交付 §六.3 已述 ✓）——headline 不得说"编译错误消失/质量改善"。
- "1,323" 是**题×候选条目**计数（raw_top=24 截断后，交付已标 ✓），不是唯一损坏记录数。
- EAWAG 水解正控的 matched_strict 必须带"记录不配平、coefficient unknown ⇒ 元素账 unknown"注脚，防"元素账已核"误读。
- 排序细节：被拒候选占满 `max_reactions` 名额（:858 检查的 `len(candidates)` 含 :882 追加的拒条目），且排序为 strict-component 先于 cn-whole（:852 键 = tier_rank, kind_rank…）——极端情形同层在前的拒条目可挤出可编译的 cn 整串候选。修前修后同序（非回归），但"检索面零变化"的口径建议补一句"排序键含拒条目占额"（交付"raw_top=24 截断后"已部分覆盖）。

### 3) 可直接落进规则文字的修改建议

- **R31-4（计数标签进数据，必加）**：凡输出 `n_strict_exact`/`n_cn_candidate`/`n_corpus_strict_exact`/`n_corpus_cn_candidate` 的诊断字典必须同带键 `tier_count_semantics: "retrieval_candidates_including_precompile_rejected; not compiled/supply counts"`；`compile_failure_histogram` 同带 `includes_precompile_permission_rejects: true`。文档标签不替代机读标签。
- **R31-5（死分支清理）**：`:940-948` 第一分支字符串加"unreachable since corpus-retrieval-2（component 带共底物恒在编译前拒）"注释或改写，防止后续读码者据旧语义复活组分路径。
- **R31-6（headline 禁句）**：禁止出现——"原子伪造通道已全部关闭"（R31-1 已禁）、"1,323 条损坏记录"、"编译错误大幅下降（310→18）"、"供给归零=接线失败/能力删除"。

### 4) "程序上诚实但化学上误导"风险点

- **风险 1**：manifest 里 `n_corpus_strict_exact` 与 `n_pool_returned` 并排，无标签时读者自然做减法理解成"strict 供给漏斗"——实际前者含 100% 被拒条目，减法无意义。
- **风险 2**：正控"3 事件 matched_strict 保持"里的 EAWAG 水解事件带伪造氧；"保持"本身诚实，但与 R31-1 禁句并置时会读成"这类化学已被证实可单步发生"——元素账是 unknown 不是 verified。
- **风险 3**：retained 条目带全量 products + co_substrates，下游若有人从 detail 重建 spec（"数据都在，差个开关"）——permission_note 已写"future independent reviewed plan"，建议再加一句"从本条目重建可用 spec = 违反许可边界"（R31-7）。

**不确定项**：检索面/直方图全部执行数字——待执行验证；死分支不可达——读码推断，待执行验证。

---

## H3（与 R2-2 的关系收口）

### 1) 结论

**同意：诚实拒满足 r30 R2-2 的最低要求——corpus 组分级通道"根本不产事件"，假单步事件无从产生；但闭合是"通道级断供闭合"，不是"机制级闭合"，判据二 unknown=无守门的结构性弱点未变也不该在本轮变；本轮不给显式参与物设计任何预支批准，对。**

### 2) 机理展开

- **R2-2 最低要求达成**：R2-2 要的是"在完整显式参与物设计落地前，不产生 A→P+共底物原子型假单步事件"。本轮实现是不产池 spec、不产 event（:878-905；builder :520-524；探针 8 案 0 spec/0 事件，证据已读、执行待验证）——**无事件 ⇒ 无参与物声明 ⇒ 无从藏进条件字段**，最低要求在本通道成立。
- **G2-c 闭环的准确定性**：G2-c 的推论链是"共底物藏条件字段 ⇒ 判据二 unknown ⇒ 无守门"。本轮在**链条最上游**下刀（事件根本不产生），对 corpus 组分级通道是彻底闭合。但链条的中段——"未知系数 ⇒ 元素账/电荷账直接记 unknown、两侧对称漏写本轴不可见"（冻结稿 :161-166 实读）——**原样健在**，且它同时服务着两类被保留的形态：整串不配平记录（EAWAG 型，by design，unknown 已披露）与未来任何恢复参与物省略的通道。所以准确说法是：**G2-c 闭环 = corpus 组分级通道已断供闭合；判据二 unknown 无守门是冻结判据的既定性质，本轮不触碰、也不应宣称已修复**。任何文档若写"G2-c 已全局闭合"= P1 级夸大（结构上只有本通道闭合）。
- **顺带核实"统一生效、非 builder 单口"**：拒因在 `find_corpus_recorded_exact` 内（:878），该函数全仓调用点仅 `s5b_builder.py:512`（grep 实读）；`compile_recorded_reaction` 全仓调用点 :675（EAWAG）/:908（corpus，拒后）；search.py 零 corpus/unsupported 命中、runflow/evaluation/s5b_scoring 无 corpus 消费（grep 实读）——单一咽喉属实。
- **后续设计轮不预支批准**：对。且本回应仅登记了 R31-2 的"零伪造候选形态"为**未来登记项**，不构成对该形态或对显式参与物设计任何方向（声明式拷贝 vs 执行式生成、gate 扩展为"执行 ∪ 声明拷贝"）的认可。设计轮至少必须回答：① 声明式拷贝的组分身份来源与 provenance 字段；② gate 扩展的同源实现 + "伪造原子"负控（gate 是编译层判据、非冻结尺子，改动须随 `compile_recorded_reaction` 版本登记——本请求已承诺"不借本轮放宽 gate"，:67-68 实读 ✓）；③ **诚实声明共底物 ⇒ 相对剥除参考边判 partial 的供给预期落字**（`evaluation.py:1062-1068` 超集语义不变）；④ R31 附带发现的激励倒挂（声明环境水=partial、省略=strict 可达）如何处理——不解决它，设计轮产出的诚实水解事件会系统性输给简写事件。

### 3) 可直接落进规则文字的修改建议

- **R31-7（G2-c 闭合范围句，必加）**："G2-c 假单步闭环在 corpus 组分级通道以编译前断供方式闭合；判据二未知系数 ⇒ 元素/电荷账 unknown 的'无守门'性质属冻结判据既定语义，本轮零改动，对整串不配平记录（隐式水/受体）继续生效并披露。闭环声明仅限本通道，不得外推为全局闭合。"
- **R31-8（许可边界句）**："从被拒条目的 compile_detail（含记录产物与共底物声明）重建可用池 spec = 违反 corpus-retrieval-2 许可边界，同违规供述。"

### 4) "程序上诚实但化学上误导"风险点

- **风险 1**："R2-2 已满足"若被读成"R2-2 全部条件已兑现"——R2-2 的主体（显式声明义务、gate 扩展同源带负控、partial 不可升 strict 子集登记）是设计轮义务，本轮兑现的是其**替代分支**（诚实拒）；交付文字须写"R2-2 以诚实拒分支收口，显式声明义务挂起至设计轮"。
- **风险 2**："无事件 ⇒ 元素守恒问题消失"——问题随通道消失，机制未修；未来任何恢复参与物省略的通道（含 R31-2 若被提前实现）会原样复发。
- **风险 3**：供给预期倒挂不落字 ⇒ 设计轮落地后 partial 桶膨胀被归咎于"设计缺陷"，反过来推动忽略档滑坡（r30 G4 风险 2 同款滑坡，R2-4 疫苗继续有效）。

---

## 冲突检查汇总（P1 义务）

| 检查项 | 对照 | 结论 |
|---|---|---|
| 编译前许可拒 | 判据一~五均管事件侧；本轮不产事件 | 零冲突 |
| 版本登记 retrieval-1→2、pool-policy-2→3 | `recorded_source.py:112`、`s5b_builder.py:396` 实读 | 已登记，符合身份规则 |
| 冻结尺子/编译判据零改动 | `compile_recorded_reaction`（:1009-1129）无 corpus 逻辑；`evaluation.py:1029-1089`、`s5b_scoring.py` 与冻结文本一致 | 读码一致；"字节零改动"待执行验证 |
| 与 r28 T1′（coproduct_ignore_tier）| 全仓 grep `src/` 零命中，proposed 未实施未冻结 | 状态未变，不重开庭 |
| EAWAG `find_recorded_exact` 字节零改动 | :620-706 无共底物逻辑 | 读码一致；字节比对待执行验证 |

**统一不确定项**：全部执行类断言（8 案探针、207/1978 测试、池深 0.477 回基线、1,323 直方图、matched_strict 正控）均**待执行验证**；缺证据面 = EAWAG 库 donor 单组分事实、1,323 的共底物类型分层、analog 模板 record_id 全量来源（本轮只抽读 5 行、均为 env:EAWAG-*，未全量核对）——后两项可做只读聚合计数探针，不碰金标。
