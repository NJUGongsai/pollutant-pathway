# mimo 化学评审回应 r33（2026-10-10）

- 通道：opencode run -m opencode/mimo-v2.6-flash-free（免费档，通道 A；主会话转发落盘）
- 请求：docs/mimo_ppv1_chem_review_request_r33.md（v4b stereo 消解实施采纳核对 S1-S3）
- 只读 provenance：评审员以读取工具核对源码/文档，无 shell 执行权限；执行类断言均自带"待执行验证"
- 原始流：docs/review_evidence/ppv1_r33_mimo_2026-10-10/raw.txt
- 采信原则：与程序证据互证为准

---


✱ Glob "docs/mimo_ppv1_chem_review_*r33*.md" 1 match
✱ Glob "src/pathway_v43/pollutant/*.py" 32 matches
✱ Glob "docs/mimo_ppv1_chem_review_*r28*.md" 2 matches
→ Read docs/mimo_ppv1_chem_review_response_r28.md 
→ Read docs/mimo_ppv1_chem_review_request_r33.md 
✱ Grep "stereo_dissolution|stereo_derived_mismatch|W-V4b" in tests · 29 matches
✱ Grep "W-V4b|stereo_dissolution|stereo_derived_mismatch|dissolution" in src · 31 matches
→ Read src/pathway_v43/pollutant/s5b_compiler.py [offset=200, limit=220]
→ Read src/pathway_v43/pollutant/s5b_compiler.py [limit=130]
→ Read src/pathway_v43/pollutant/s5b_compiler.py [limit=180, offset=840]
→ Read src/pathway_v43/pollutant/s5b_compiler.py [limit=130, offset=430]
→ Read .git/HEAD 
→ Read src/pathway_v43/pollutant/s5b_compiler.py [limit=140, offset=559]
→ Read src/pathway_v43/services/atom_tool.py [limit=150, offset=400]
$ cat .git/refs/heads/v4.3 2>/dev/null || true; grep -m1 "refs/heads/v4.3" .git/packed-refs 2>/dev/null || true
9a0a60ea0a426fcfe0df3c82de5a9ab1fcbdaa46
Error: Connection lost while reading the response: ECONNRESET: The socket connection was closed unexpectedly. For more information, pass `verbose: true` in the second argument to fetch()
→ Read tests/test_ppv1_s5b_hit50_v4b.py 
→ Read tests/test_ppv1_s5b_hit50_v3_wv3.py [offset=180, limit=80]
✱ Grep "stereo|unsupported|capability" in src/pathway_v43/pollutant/real_model.py · 5 matches
✱ Grep "stereo_created|显式氢价态墙|纯立体翻转.*(8|维持)|1 \+ 24|24.*8.*5" in docs · 60 matches
✱ Glob "docs/*V4B*" 1 match
✱ Grep "stereo 38|stereo: 38|= 38|38 =|38 面|stereo_edit.*38|38/228|228.*stereo" in docs · 40 matches
→ Read docs/POLLUTANT_PATHWAY_S5B_HIT50_V4B_DELIVERY_2026-10-10.md 
→ Read src/pathway_v43/domain/identity.py [limit=60]
✱ Grep "stereo_dissolved|stereo_changed|_changed_maps" in src/pathway_v43/pollutant/recorded_source.py · 2 matches
→ Read src/pathway_v43/pollutant/chemstate.py [limit=35, offset=905]
→ Read src/pathway_v43/pollutant/evaluation.py [limit=50, offset=800]
✱ Grep "def _identity_key" in src/pathway_v43/pollutant/chemstate.py · 1 match
→ Read src/pathway_v43/pollutant/evaluation.py [limit=115, offset=849]
→ Read tests/test_ppv1_s5b_hit50_v4_wv41.py [limit=70, offset=580]
→ Read src/pathway_v43/pollutant/chemstate.py [limit=40, offset=180]
→ Read src/pathway_v43/pollutant/real_model.py [limit=100, offset=195]
✱ Grep "stereo_edits" in src · 2 matches
✱ Grep "stereo_dissolution_applied|_is_stereo_dissolution|stereo_dissolved" in src/pathway_v43 · 19 matches
✱ Grep "coproduct_ignore_tier" in src · 0 matches
# mimo 化学评审回应 r33 —— v4b stereo 消解实施采纳核对

**执行边界声明（先行）**：本轮只用读取类工具（glob/grep/read；另只读打开了 `.git/refs` 一处核对 HEAD）核对 `src/pathway_v43/pollutant/s5b_compiler.py`、`recorded_source.py`（grep 级）、`real_model.py`、`evaluation.py`、`chemstate.py`、`src/pathway_v43/domain/identity.py`、`src/pathway_v43/services/atom_tool.py`、`tests/test_ppv1_s5b_hit50_{v4b,v3_wv3,v4_wv41}.py`、交付书与 v2 尸检等 docs；**未运行任何测试/脚本/git 写操作**，所有行为类断言（测试红绿、RDKit 具体行为、漏斗数字）一律标"待执行验证"；引用行号均为本轮实读；未访问金标/题面/gitignored 目录。

**范围口径（先行，P3 级提示）**：来函引导语描述的是"三个判断面（coproduct_ignore_tier 主面 / r27 采纳核对 / stereo 设计草案）"，那是 **r28 请求**的三判断面模板，与所附 r33 请求（S1–S3 实施采纳核对，内容与 `docs/mimo_ppv1_chem_review_request_r33.md` 一致）不匹配；"附面二为设计草案（未实施）"在本轮也已过期（v4b 已实施）。**本回应按所附 r33 全文（S1–S3）评审**。另核：HEAD = `9a0a60ea0a426fcfe0df3c82de5a9ab1fcbdaa46`（读 `.git/refs/heads/v4.3`，与请求所记 9a0a60ea 一致 ✓）；`coproduct_ignore_tier` 在 src 中零匹配（未实施，与引导语一致，不在本轮范围）；`stereo_dissolved*` 消费方仅 `s5b_compiler.py`（grep 证据），与交付书 §二入口矩阵自述一致。

---

## S1 — 四条件谓词对 r28 E1–E3 边界的覆盖

**一句话结论：有条件同意——四个反例族在代码里全部有拒（E/Z 两头处置与我 r28 预期一致），但"反例族全拒"的自述在一个子族上过强：E1-2 断/成键家族只拒了"标签变化形态"，同标签形态（及模板无声明而底物有声明的形态）现状仍可编译——这是交付书 §十.3 已如实登记的残留，请求正文没有按该口径收窄。**

展开（逐族，行号均实读）：

1. **stereo_created（E1-1）✓ 全覆盖**：进入条件 `s5b_compiler.py:275-276`，条件 1 要求 lhs 真四面体（`:324-325`）∧ rhs UNSPECIFIED（`:326-327`）——lhs 无声明→rhs 有声明在 `:326` 处返回 False ⇒ 落 `stereo_changed` ⇒ `_compile_edits:504-510` 结构化 `stereo_edit_unsupported`。负控在案（`v4b:191-202`、`wv3:243-249`）。注释与实现一致（`:313`）。
2. **仍四面体中心的断/成键（E1-2）◐ 半覆盖**：条件 3（`:334-339`）确实把 form/break/芳香/降阶落在**该原子**上的变化全部挡在消解外（order_lhs≠"single" 或 order_rhs∉{double,triple} ⇒ False），这是"标签变化 + 断/成键"形态 ✓。**但条件 3 只在"模板 lhs/rhs 标签不同"这一分支里被评估**（`:275` 的守卫）：若模板双侧写**同一标签**（SN2 同 [@H] 书写、记录未更新构型），立体差异不存在 ⇒ 不进消解评估、不受条件 3 约束 ⇒ 断/成键落在手性中心**现状即可编译**——这正是 r28 E1-2 的核心机理（RDKit 四面体标签锚定键表顺序，`RemoveBond`/`AddBond`（`atom_tool.py:441/:450`）移动邻居序 ⇒ 标签保留而解读可能翻转 = 静默对映体翻转）。同理，模板双侧**均无声明**而底物原子有声明时，同一机制同样无门。**交付书 §十.3 已如实登记同标签形态为既有残留、守门属判据扩展待复审**——残留披露本身诚实，但请求正文写"反例族全拒……一律维持 stereo_edit_unsupported"（请求 :16-17）**没有带这个限定**，按请求原文读会高估封闭面。判级：**P2（采纳核对的条件项，非 P1——预存行为、非 v4b 引入、与冻结判据无冲突）**。
3. **E/Z（E1-3）✓ 与"两头如实"预期一致**，四条链本轮全部读到：①检测面只在原子四面体标签（`_chiral_token:381-386`、谓词 `:324`），键立体不在放行面也不在拒面；②边界文字两头都写（模块头 `:51-53`，交付 §3.1 E1-3/E2-⑤ 行）；③参考声明 E/Z ⇒ 严格身份（`chemstate.py:180-205` 保留立体基串，`:913-929`）与执行产物未指派 E/Z 不等 ⇒ 落 `cn_only`（`evaluation.py:911-925`，cn 为立体盲 `identity.py:40-55`，`isomericSmiles=False` `:43`）⇒ 不授 strict ✓；④消解不改分层（`wv41:593-617` 实读断言：消解编译通过但 tier 仍 `recorded_cn_candidate`）。**一处措辞建议**：头注"不静默断言"只在"参考声明 E/Z"一侧成立；参考也未声明时是"无声明对无声明 ⇒ strict 相等"，这个相等不是"E/Z 已证一致"，建议落字区分。
4. **非四面体/累积烯（E1-4）✓ 代码覆盖、测试归因有误**：条件 1（仅 `_TETRAHEDRAL_TAGS` `:302-305`）+ 条件 2（该原子全部 lhs 键须单键 `:328-332`，含未映射端点的键）在读码层面挡住非四面体与累积烯中央原子。但负控夹具 `v4b:224-238` 的原子 2 全键皆单、且 rhs 写了 `@@` 标签——它实际在**条件 1（rhs 有声明）**处被拒，docstring 却声称"谓词第 2/3 条不满足"（`:231-232`）；SN2 夹具 `v4b:205-221` 同样先在条件 1（rhs 有标签）被拒，而注释写"第 3 条不满足"（`:212-213`）。**结局都对，归因都错，且条件 2、条件 3（rhs 无声明 + 断/成键这一最贴近有机磷/硫水解数据形态的组合）没有隔离负控**——"四条件逐条拒"目前缺逐条件可证性（P3，测试文档/覆盖问题，非代码问题）。
5. **E2-⑥（capability 同步改版）◐ 本轮明确不采纳**（交付 §3.1:73、§十.2:314-317）。我接受其理由：`real_model.py:280-285` 的 `unsupported` 串描述的是**模型侧 novel 编辑协议面**，执行器确实无立体 op（`atom_tool.py:431-496` 仅 break/form/change_bond_order/add_atom），该句对其作用域仍为真；编译侧消解不经模型提议（池模板来自 recorded/corpus/analog 语料），供给面变化由池漏斗直接测得（交付 §五），我 r28 的原始顾虑（"否则测不到供给面变化"）在此通路下不成立。**建议加一句 scope 注记**（见下）。

**可直接落进规则文字的修改建议**：
- (S1-a) 把请求/边界文字"反例族全拒……一律维持 stereo_edit_unsupported"收窄为："**标签变化形态**的反例族全拒（stereo_created / 标签变化∧断成键 / 非四面体标签 / 纯翻转）；**同标签与模板无声明的断/成键落底物手性中心为已登记残留（交付 §十.3），现状可编译，守门（执行后同源复核扩展到全部手性保留原子）列入下轮扩展选项**。"
- (S1-b) E/Z 段补一句："参考亦无 E/Z 声明时 strict 相等成立，该相等是**无声明对无声明**，非'E/Z 已核一致'。"
- (S1-c) 测试侧：非四面体夹具与 SN2 夹具的 docstring 归因改正（实为条件 1 拒），并补两个隔离负控——条件 2（rhs 无声明 ∧ 带标签原子在 lhs 含非单键）与条件 3（rhs 无声明 ∧ 断/成键落该原子）。若 RDKit 解析即清掉 sp2 原子标签导致条件 2 形态进不了判定环，把该事实本身写进测试（**RDKit 解析行为待执行验证**）。

**"程序上诚实但化学上误导"风险点**：
1. 同标签断/成键残留若不随请求收窄披露，事件层可能把**无证据的绝对构型**（键序副作用产物）写进记录与 provenance——判据一"不伪造特异性"精神层面的失真，与我 r28 E3 点名的残余风险同型（方向：多为 strict miss 被 `cn_only` 兜住，但"恰好对上参考"的假 strict 通道理论存在，量级未知，**待执行验证/聚合面未统计**）。
2. 诊断字符串 `chiral_sp3_center_dissolved_by_bond_order_change_sp3_to_sp2`（`:995-1000`）是元素无关的字面——若谓词将来在非碳中心（见 S2）触发，该标签是**事实错误的化学陈述**（中心可能仍为四面体）。

---

## S2 — 执行后同源复核（stereo_derived_mismatch）是否达到 E2-③

**一句话结论：同意——E2-③ 的字面要求（执行产物在该 map 的立体状态 == rhs 声明，不等 ⇒ 结构化拒）逐点达成且 fail-closed；但"消解后仍为立体中心不放行"只是被"谓词的碳 sp3→sp2 结构性保证 + 已指派标签复核"联合隐式覆盖，对"仍为潜在立体中心但未指派"的残差未覆盖，建议补一条显式断言或按此口径收窄落字（P2）。**

展开：

1. **E2-③ 字面达成 ✓**：复核置于每条对齐的 target 赋值之前（`:909-923`）；判据 = 执行产物该 map 标签 ≠ CHI_UNSPECIFIED，且**映射缺失/产物不可解析按失配报告**（`:376-377`：`tag is None or tag != _UNSPECIFIED_TAG` ⇒ 入 mismatched）——fail-closed 方向正确；rhs 侧被谓词钉死为 UNSPECIFIED（`:326-327`），故"== rhs 声明"与"== UNSPECIFIED"等价 ✓；结构化拒因 `stereo_derived_mismatch`（`:917-923`）；机读证明测试在案（`v4b:255-297`，monkeypatch 残留标签产物 ⇒ 拒 + helper 三态直测 :283-297；**测试行为待执行验证**）。
2. **"仍为立体中心"的隐式覆盖分三层**：
   - **碳、已放行面（本轮回读的全部正控）**：真正的保证来自**谓词**而非复核——条件 3+4（该原子至少一个 single→double 且全部为此型，`:334-341`）⇒ 执行后该原子 sp2 ⇒ 四面体立体中心**结构上不存在**。复核在此的作用是防御执行器/序列化残留标签（测试 docstring 自己写了"真实化学路径下该门为防御性——显式氢价态墙先行，隐性标签由 sanitize 清理"，`v4b:258-259`）。
   - **底物有声明、执行后中心幸存**：标签保留 ⇒ 复核失配 ⇒ 拒 ✓ 隐式覆盖成立（这也正是非碳中心如 P 的"底物已指派"情形的兜底）。
   - **未覆盖的残差**：执行产物该原子**仍为潜在立体中心但标签为未指派**——复核查的是"无已指派标签"，不是 r28 E2 谓词原文的"该原子**非立体中心**"。可发生的情形：非 p-block 中心上 single→double 不消灭四面体几何（如 P：全单键 lhs + 单→双后仍 4 配位四面体，**中性 4 价 P 能否过 RDKit 解析/价态待执行验证**），且底物该中心未指派（此时复核恒真、纯空窗）。碳面上两种表述等价（sp2 论证），故无现行行为冲突。
3. **该复核在生产通路中几乎是空窗的，应如实落字**：放行面 = 底物未指派中心（见下）⇒ 产物必未指派 ⇒ 复核恒过；底物已指派（`[C@H]` 括号氢）⇒ 先撞执行价态墙（`atom_tool.py:503-510` sanitize 拒 ⇒ `s5b_compiler.py:904-908` execution_failed，复核根本不起跑）。再叠加对齐 `useChirality=False`（`:404-406`，模板立体声明从不与底物立体比对）——**当前真正的安全垫是"谓词 + 价态墙"，不是复核**。复核的价值在机读可证性与未来执行器行为漂移的防御，这是合格的定位，但规则文字不能把它写成"立体中心已验证不存在"。

**可直接落进规则文字的修改建议**：
- (S2-a) 边界文字加一句："**执行后同源复核 = '该 map 无已指派四面体标签' 轴，非潜在立体中心感知；'消解后仍不为立体中心'在碳中心由谓词（sp3→sp2）结构性保证，非碳四面体中心（P/S/Si 等，single→double 后仍可能四面体）为已知未断言残差。**"
- (S2-b) 二选一（下轮，不本轮动码）：① 显式断言——复核扩展为"该 map 不出现在执行产物的四面体潜在立体中心清单（含未指派）"，范围只限该原子（碳面预期零行为变化，**FindPotentialStereo/FindMolChiralCenters 实际行为待执行验证**）；或② 元素范围守卫（谓词限 C/N 等 single→double 必失四面体的元素）。
- (S2-c) `stereo_dissolution_semantics` 字符串（`:995-1000`）补元素/轴限定，防止 `sp3_to_sp2` 字面被外推到非碳中心。

**"程序上诚实但化学上误导"风险点**：
1. 把"复核通过"读成"已证明不再是立体中心"——空窗真值（底物未指派时恒过）会给人**验证强度高于实际**的印象；
2. 诊断标签对非碳中心的错误外推（同 S1 风险 2）；
3. "价态墙先行 + 复核防御性"这一结构意味着：若未来 RDKit sanitize/MolToSmiles 的残留标签清理行为变化，生产面**无任何信号**会变红（复核恰好被定义为只信产物标签）——建议在登记里写明该门依赖 RDKit 行为（**待执行验证**）。

---

## S3 — 诚实披露核对（1 + 24 + 8 + 5 分解）

**一句话结论：同意——分解内部自洽且与 v2 尸检的 38 例总量精确对账（1+24+8+5=38），与我 r28 E1-1 的"立体创建/非四面体是主流不可修面"预警方向一致；"应修而未修"的类我认为有一个且应优先排期：显式氢价态墙（跨通道共 14 例事件），它不是化学边界而是执行器记账限制。**

展开：

1. **对账 ✓**：v2 尸检 EAWAG 编译墙 `stereo_edit_unsupported = 38`（`docs/S5B_HIT50_V2_POSTMORTEM_2026-10-09.md:72`）；交付 §3.3 表：38 = 1 编译 + 5 价态墙 + 32 维持（24 stereo_created + 8 翻转/保留型）（交付 `:112-117`），与请求 S3 数字逐项一致；漏斗 38→32、execution_failed 3→8(+5)（交付 `:197/:201`）。**数字为交付方测量自报，我未执行复算（待执行验证）**；金标纪律下逐题形态未核（bt0002#r0032 等按请求/交付自报采信）。
2. **与 r28 E1-1 预警一致性 ✓**：不可修面 = stereo_created 24/38（63%）+ 翻转/保留 8 = 32/38（84%）——恰是 r28 E1-1/E1-2 判定"放行即假阳性"的两类，维持拒**就是**忠实采纳；非四面体类观测为 0，与我 r28 E1-4 自己"标不确定、缺该域供体模板证据"的措辞一致（不是漏统计的证据，是"该类在域内可能本就罕见"）。24 例 stereo_created 即便放行也会被产物多重集 gate 以 strict 立体身份拒（交付 §3.3:116 自述，与 r30 分层核对同源），**这一类明确不应修**。
3. **口径两处要补（P3）**：①**通道范围**——该分解是 **EAWAG 通道**的；analog 通道同轮 93→83（1 例编译成槽 + **9 例价态墙**）、corpus 18→18 全非消解型（交付 `:117/:124-125`、`:242-244`）。池层"净 +1 槽"（`:226-240`）下"只恢复 1 题"成立，但价态墙全局是 **5+9=14 例事件**，请求只写"5"，对外表述应标"EAWAG 口径"。②**5 vs 6 摇摆**——交付 §3.3 正文写"价态墙（6"（`:122`）而表为 +5；§十.1 写"5+1 例……6 例事件级"（`:308-313`）。推测"6 = 谓词通过总数（1 编译 + 5 墙）"，但字面挂到了"墙"上，建议统一口径再对外。
4. **应修而未修的类：显式氢价态墙（唯一推荐项）**。机理：底物手性中心写成 `[C@H]`（noImplicit + 括号氢计数），single→double 后显式价 5 ⇒ `SanitizeMol` 拒（`atom_tool.py:503-510`）——**是 SMILES 记账限制，不是化学限制**：与本轮唯一恢复的 1 例是同一化学类（二级醇→酮，中心随 sp3→sp2 真消解），且这批撞墙的是**手性声明底物（strict 层）**，修后预期恢复 strict 层供给（交付 §十.1 自估题级约 4-5），比已恢复的 cn 层 1 例价值更高；跨通道合计 14 例事件，是当前恢复量的十余倍。交付已把它登记为 §十.1 最小改动面（change_bond_order 路径允许端点显式氢随键级升高消耗，~3 行 + 正负控，AtomTool 红线内不擅改）——**登记姿态正确**。我的建议：**列为下轮优先项**，条件：①只动 `numExplicitHs` 记账，图中原子级 H/同位素 H 不受影响（仍诚实拒）；②负控须含"真实超价仍拒、novel 通道全量重跑"；③规则文字补"键级升高伴随显式氢消耗 = 脱氢记账语义"一句。其余类（24 stereo_created、8 翻转/保留）**不应修**，与 r28 边界一致。

**可直接落进规则文字的修改建议**：
- (S3-a) "本轮分解：EAWAG 通道 38 例 = 1 编译（cn 层）+ 5 显式氢价态墙（strict 层）+ 24 stereo_created + 8 翻转/保留；**analog 另有 1 编译 + 9 价态墙，corpus 18 例全非消解型**；全部为检索/编译面聚合自报，非命中数，待执行验证。"
- (S3-b) 统一"价态墙"计数口径（墙 = 5；谓词通过 = 6 = 1+5），修交付 §3.3 正文与 §十.1 的字面摇摆。
- (S3-c) 把"价态墙类 = 执行器记账假阴性，非化学不可修面，列为下轮优先登记项"写进规则文字的边界说明，与"stereo_created/翻转 = 化学上不可修面"分列，防止两混一类。

**"程序上诚实但化学上误导"风险点**：
1. 不标通道/口径的"5"会被读成"价态墙全封"（实际跨通道 14）；
2. "编译恢复 1 题"若脱离"不冒充命中数"的限定句（交付 §五末尾已有该句 ✓，请在对外回应里保留）会被读成"命中 +1"；
3. 把价态墙与 stereo_created 混在"不可修面"叙述里，会把**可修的执行器假阴性**永久固化成"化学边界"——这本身是一种化学上误导的归类。

---

## 总判定

**有条件采纳（无 P1；与冻结判据一~五、0d/0E 零冲突）**。冲突扫描：判分侧本轮零改动（src 内 `stereo_dissolution*` 消费方仅 `s5b_compiler.py`；`evaluation/chemstate/identity` 实读为既有严格身份/cn 分层，`:911-925` 无 W-V4b 引用），消解方向"只减不加立体、底物已指派先撞墙、参考声明立体恒落 cn_only"，判据一（不伪造特异性）与 strict 口径均未被侵蚀 ✓——**无 P1**。

采纳条件（全部为落字/登记/测试级，不阻塞已实施代码）：

1. **S1-a**：请求与边界文字把"反例族全拒/一律维持拒"限定为"标签变化形态"，同标签（及模板无声明-底物有声明）断/成键按交付 §十.3 口径列为已登记残留，守门扩展列下轮；
2. **S1-c**：改正两个负控夹具的条件归因 docstring，并补条件 2、条件 3 的隔离负控（否则"四条件逐条拒"缺逐条件可证性）；
3. **S2-a/b/c**：落字"复核 = 已指派标签轴 ≠ 潜在立体中心感知"，非碳残差披露；显式断言或元素守卫二选一列下轮；诊断字符串加轴/元素限定；
4. **S3-a/b**：分解标 EAWAG 口径、补 analog/corpus 行、统一 5 vs 6 计数；
5. **价态墙类**按 §十.1 登记升为下轮优先项（附负控与语义落字条件）；
6. **E2-⑥**：本轮不改 capability 我接受；建议在 `execution_graph_payload` 文档串（`real_model.py:215-216/:283`）加 scope 注记一句——"该 unsupported 为模型侧 novel 编辑协议面；编译侧 stereo 消解（S5b-stereo-dissolution-1）存在且以 `stereo_dissolution_applied` 机读披露"，防止全系统级误读。

## 不确定清单（全部待执行验证 / 未执行类）

- 测试红绿、G01、漏斗/池深数字：交付与请求自报，未复算；commit 9a0a60ea 的逐文件清单未跑 diff（仅 HEAD sha 只读核对 + 交付 §十一自报）。
- RDKit 行为：sanitize/MolToSmiles 对 sp2 残留四面体标签的清理、`FindPotentialStereo` 语义、带双键原子上手性标签的解析存留、中性 4 价 P 的解析/价态容忍——均未亲验。
- 同标签断/成键"可能静默翻转"的机理：两侧文档（r28 与交付 §十.3）同述"可能"，我未构造执行级复现。
- 逐题形态（bt0002#r0032、r1147、analog 9 例墙等）：金标纪律下零访问，按自报采信。
- 价态墙修复的预期恢复量（题级 4-5、strict 层）：交付 §十.1 自估，未验证。
