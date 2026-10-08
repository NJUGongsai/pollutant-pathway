> **通道与 provenance（主会话 ZCode 记录，非 mimo 回应正文）**
>
> - 2026-10-08 上午（S3b 回修 r3 轮，按 AGENTS.md「评审-回修自动循环」轮内第③步自动送审）：请求经 **opencode 免费模型 `opencode/mimo-v2.6-flash-free`** 只读评审；opencode 会话 `ses_ee6f27063ffe4W4kSYyM5xaSZX`（标题 "mimo ppv1 v15 chem review"）。与手机 mimo 应用是否同一实例未经证实，采信按本通道口径区分。
> - 本轮一次运行完整输出（无断流、无续跑）。
> - 评审为**只读**：执行类声明（如 RDKit 2026.03.6 往返取证）标注"待执行验证"，部分分支标注"未确认/探查读取"。其中 PPV1 879 passed 已由主会话本机独立复跑证实（2026-10-08）；G01 安全隔离 1481/8/17 为交付方隔离证据，留 Codex 复核。
> - 请求原文：`docs/mimo_ppv1_chem_review_request.md`（v15，S3b r3 版，自包含、无金标）。运行证据与原始输出：`docs/review_evidence/ppv1_s3b_r3_mimo_2026-10-08/`。
> - 以下为 mimo 回应原文（仅清理终端控制字符，未做任何内容改动）。

---
# mimo 化学评审回应：pollutant_pathway_v1 判据草案 v15（S3b 回修 r3 后，未冻结）

**执行边界声明**：本轮仅用只读方式浏览仓库源码/文档核对请求表述（仓库根 `/Volumes/CC/Enzyme_Agent/dependingv43`，实现 `src/pathway_v43/pollutant/`）；**无执行权限，未跑任何测试/探针，凡执行类数字与运行行为一律标"待执行验证"，不编造结果**。引用行号均为本轮实际读到的行号；仅由本轮只读探查代读、我未亲自复核到具体行的，标 `[探查读取]`；未核到的标"未确认"。未访问任何 gitignored 金标/题面/封存 run。**总体定位先行**：同意"r3 是工程回修、不新增化学判据"这一定位——0e.1 与 0c-v15 我逐条核后均属消费契约/精度文字，判据一–五正文与 v12/v13 相同，本轮不改化学口径。

---

## 一、判据一：分子身份

**(a) v12 落字（真实 token 表 / 外层-内因两维更正 / 同源非独立算法）+ 2b 三处 v9 落字**

1. **结论：同意**（附一条件：RDKit 工具行为部分待执行验证）。核对：`_CX_STEREO_ITEM_HEAD_RE` 实为 `(a|o\d+|&\d+|\^\d+):`（chemstate.py:266），登记类文案含 `atomProp/SgD/Sg/a/oN/&N/^N/$(…)$/(…)`（chemstate.py:469），故 `and:`/`or:`/`rad:` 不命中、落兜底 `raise _cx_unregistered_item_error`（chemstate.py:456、466-476，kind=unregistered_cx_class）——"英文类名不是输入字面、按 unregistered_cx_class 拒"在**代码路径上成立**；但"RDKit 2026.03.6 实际写出 ABS/AND/OR/自由基并保持严格身份往返"是工具执行行为，**待执行验证**（需跑往返正控，锁定 2026.03.6）。外层-内因两维更正：工厂入口 kind 直挂 `detail.kind`（unregistered_cx_class chemstate.py:473；unparseable_smiles chemstate.py:692、927），恢复入口外层 kind 为 `state_structure_unparseable`/`raw_structure_rejected` 且内因在 `detail.reason`（chemstate.py:846/849、896/899），writer 外层 `Ppv1StateContractError`（store.py:398）——与 v12 落字一致，v11 那句括注确属错误、不应再出现。"同源确定性重推导是同一算法复算、不是第二套独立证明"：`from_dict`/直接对象复用 `build_chemical_state`/`strict_identity_of` 同源推导（chemstate.py:837-880、889-910），同意。
2. **可落字建议**：① 把"(RDKit 2026.03.6 实际写出 ABS/AND/OR/自由基…)"这半句加"（工具行为，**待执行验证**：冻结前以 2026.03.6 跑 plain/ABS/AND/OR/自由基往返正控与三别名负控）"；② 2b 处补一句"writer 侧 raw 失败机读码为 `raw_structure_unparseable` 且不带 reason 内因（store.py:632），与恢复入口 `raw_structure_rejected` 不同名"——防下游把两个 kind 当同一个。
3. **"程序上诚实但化学上误导"风险点**：输入守卫"接受"只证明表示层契约通过——若读者把它读成"样品/异构体已被鉴定"，就是程序诚实、化学误导；正文已有"不构成样品认证"句，建议该句在冻结稿中紧跟 token 表（不要隔段）。

**(b) 入口清单闭合性（工厂/strict/判据五四字段/恢复/直接对象/搜索层；preview 按 C2 划界）**

1. **结论：有条件同意**。已核到守卫调用点：build（chemstate.py:687-688 区间 `[探查读取]`）、strict（:923-924 `[探查读取]`）、恢复 `from_dict→validate_state_object` raw 分支（chemstate.py:889-899）、audit 直接对象（audit.py:474-475 `[探查读取]`）、供体诊断四个原始串在解析前统一过 `_guard_input_cx_classes`（audit.py:2572-2592，解析在其后 :2596 起）。**池输入 preview 的 conservation 诊断按 C2 划界**一项，我未逐行核到 preview 侧调用关系——标**未确认**，请实施方给出行号或在冻结稿标"读码未覆盖"。
2. **可落字建议**：入口清单后加括注逐条附行号（如上），preview 划界条注明"（本轮未核到行号，标未确认，冻结前补）"。
3. **风险点**：把"守卫覆盖全部入口"读成"全仓不存在能产生身份/verified 证据的旁路"——只要还有一个未列明入口（如 preview、未来 caller），该句就从"诚实清单"变成"过度承诺"。

**(c) 判据 1–4 不重评**：**同意**，文本自包含展开无新口径；身份键=规范化 CX 子集+ABS 剥离+稳定哈希、移除坐标/atomLabel/atomProp、保留增强立体/自由基/同位素电荷立体（chemstate.py:180-226、211-215、237-238 `[探查读取]`）与文字一致。

---

## 二、判据二：参与物计量与元素/电荷核算

1. **结论：同意**（v12 两处落字均核到实现）。
   - 系数句：非法系数在构造/提交边界拒（hypothesis.py:136-173 `[探查读取]`）；`coefficient_binding_mismatch` 只在 audit.py:923-933 产生、只 append 进 `coverage_violations`（audit.py:1025），`decide_admission` 不读该字段（audit.py:1643-1807 我通读，无 coverage_violations 消费）⇒ **属覆盖轴、不直接决定 R 行**成立；绑定失配 ⇒ `binding_ok=False` ⇒ 中心检查记 **unknown**（audit.py:1164-1174），最终走 R5 而非 R5d/R2b——"不能固定写成 R2b、也不能固定写成 R5"这句我核到的实现是**实际落 R5**，文字用"依首中规则"是更保守的正确写法，同意。全 src 无"从结构重推导系数再比对"的入口（探查清单核过），"不可虚称入口在比对系数与结构重推导值"属实。
   - known_absent 轴归属：实现在 path_context.py（物种同值 conflict `required_entity_known_absent` :732、字符串同值 conflict `required_value_known_absent` :828、异值 unknown `other_value_known_absent_not_determining` :833、数值/区间 unknown `numeric_absence_semantics_undefined` :822），不进元素账——成立。
2. **可落字建议**：① 在"最终处置依…首中规则"后补一句实测指向"（当前实现下该 kind ⇒ 中心 unknown ⇒ R5；如未来扩表须升版本）"，把行为与原则都钉住；② 元素账侧补 0c-v13.3 的 `full_known` 行号（audit.py:628、641/648、673/679）使两处同源可核。
3. **风险点**：数值账"平"被读成质量/电子守恒已核——全氢账合并 D/T、自由基电子不入账两个盲区必须与"账平"同屏出现，否则是典型的"程序诚实、化学误导"（把组成闭合冒充守恒定律级结论）。

---

## 三、判据三：admission 决策表与中心证据契约

**(a) v12 落字（R2b caller 映射 / 中心 partial 分开 / 入口划界）+ v11 恒入/复用分写 + v10 四点**

1. **结论：有条件同意**（两处需冻结前更正，见下）。
   - R2b：`contract_violation` 由调用方传入（audit.py:1649、1748-1755，docstring:1664-1667 明写"不传则 R2b 不可达"）——"缺映射不得当化学已核"成立。
   - 中心 partial：`binding_ok=False` ⇒ 中心 **unknown** + `coverage="mapping_dependent"`（audit.py:1164-1174），覆盖枚举在 detail、中心结论是 unknown——"无裸 partial、两套名词分开"与实现一致。
   - 入口划界：`store.verify_event_attachment_content` 在 store.py:1988 起，只核附随投影/展开计划（:1989-2021 `[探查读取]`），不碰 states 行——"不单独证明 state 身份"成立。
   - **⚠️ 必须更正 1：⑤ 中"substrate_profile 无生产 caller"在当前源码不成立**——`build_substrate_profile` 生产调用在 runflow.py:809，产物写持久 artifact runflow.py:812-814（我实际读到）。这与本文 0e.5"空池仍组装底物档案"自相矛盾，属过时事实。
   - **⚠️ 必须更正 2：决策表 R3 行"action=blocked"与实现不符**——audit 文档串 :1528-1529 与代码注释 :1757 确实都写 "(blocked)"，但展开路径对 defer 的实际结算是 `OUTCOME_KIND_ADMISSION_DEFERRED` + `put_hypothesis` 留痕（runflow.py:1122-1133），`status=blocked` 的写点只有 `record_blocked_hypothesis`（search.py:1145）与恢复隔离（search.py:1213）——R3 冲突**不写 blocked 行**。deferred 是可激活的、blocked 是不可执行的（0e.6），两者混写会误导。
   - 跨假设未绑定 ⇒ 中心 unknown（audit.py:1131-1148 `[探查读取]`）、篡改复算不一致 ⇒ AuditContractError 本次无成功 admission（audit.py:1110-1116，其上无 try 包裹）——"两种情形分写"同意。
2. **可落字建议**：① ⑤ 改为"substrate_profile 在 S0–S2 时点无生产 caller；**S3b 起由驱动在决定层调用（runflow.py:809）并写持久 artifact（runflow.py:812-814），其输出不构成身份/核实证据，档案输出前置验证仍划界 P2**"；② R3 行改为"→ defer（当前场景不展开；动作结算为 admission_deferred、假设留痕；**与 0e.6 的持久 blocked 行不是同一状态**）"，并请实施方同步改 audit.py:1528-1529 注释（列 P2 文本同步，同 0c-v15.5 口径）；③ "恒入"语序调整见 (b)。
3. **风险点**：R3 的"blocked"若不改，读者会以为场景冲突是不可逆阻断（化学上等于"此路永久不通"），而实现是可换场景再激活的 defer——这正是"程序上诚实但化学上误导"；⑤ 的过时无 caller 声明同理，会让读者低估档案输出已有生产路径。

**(b) v9 scope 归属与"恒入≠已适用"+三条件判定**

1. **结论：同意**（附措辞条件）。`completion_license`/`completion_license_scope` 只在走到覆盖判定完成的 detail 里写入（audit.py:1009-1013），早退点不携带（unknown_coefficients 早退 audit.py:889-897；unverifiable :908-910、:949-952 我读到其结构）；三条件组合（product_coverage=full + uncovered 两 refs 非空 + unlicensed 为空）与代码字段名一致（audit.py:1004-1025）。scope 字面 :1011 不含"不区分键断裂方式与电子去向"句、该句归规则正文——属实，同意"本请求不再要求改 scope 字面"。
2. **可落字建议**：把"**恒入 center detail**"改为"**凡完成覆盖判定的 center detail 必带**（full/partial 均携带；早退不携带）"——现句把"恒入"放前面、限定放后面，快速阅读会记成"所有 detail 都有"。
3. **风险点**：字段"存在"被读成"本结论用了补全许可"（反向误导）：看到 completion_license 字样就以为数值补全参与过判定；三条件组合句必须与字段名同屏。

**(c) 决策表与覆盖核算展开文本与实现一致**

1. **结论：同意**。我实际通读 `decide_admission`（audit.py:1643-1807）：R1 :1672 → R1b :1679 → R2 :1689 → R2p :1700（off 分支只披露 :1730-1746）→ R2b :1748 → R3 :1757 → R4 :1763 → R5d :1769 → R5v :1779 → R5c :1788 → R5 :1796 → R6 :1805 →（R7 兜底在其后），**首中即决逐行 return**；R5d 触发集 `R5D_TRIGGER_CHECKS`={element_accounting, formal_charge_accounting}（audit.py:227-228 `[探查读取]`，消费 :1771-1772）；λ_s×Δ 对账在 audit.py:973-980（产物侧 973-976、反应物侧 977-980，请求写"973-979 一带"覆盖到）；coverage 枚举三值与四种 kind 均核到（:896、:1004-1005、:929、:962-963、:993）；chemical_reproposal 默认 off（:1553 `[探查读取]`）。
2. **可落字建议**：把"973-979 一带"写全为"973-980"；决策表后附一行"实现：decide_admission audit.py:1643 起、规则表 docstring :1510-1549"。
3. **风险点**：R5d"绝不进入 R6"与 R5v 独立码若被下游合并成一个"账不平"桶，新增 violated 检查会静默挂进"声明账不一致"（化学上把非计量问题冒充计量矛盾）——现文本已防，保持即可。

---

## 四、判据四：条件相容聚合

**(a) v11 三处落字 + v12 known_absent 轴归属**

1. **结论：同意**。孤儿两方向：已有要求无按签名快照 ⇒ unknown（`requirement_binding_not_in_route_snapshot`，path_context.py:1245-1269 `[探查读取]`）；行/签名无对应要求或集合不一致 ⇒ `context_snapshot_inconsistent` 拒（:1470-1499 `[探查读取]`）——与"方向更正、以本版为准"一致。入口限定：`validate_context_object` 调用仅在 from_dict/derive 父对象/audit 直接对象（探查 grep 清单），`assess_conditions`(:1117)/`assess_candidate_conditions`(:1172)/`route_assessment`(:2112) **自身无 validate**——"需上游纪律、新 S3b 必须接真实守卫"的如实披露成立。重建半边：derive_child_context 产新 context_id 并留 parent_context_ref（:2402-2427 `[探查读取]`），旧 ID+新内容 ⇒ mismatch 拒（:1540-1548、:2082-2091 `[探查读取]`）。known_absent 补写与判据二同源一致（path_context.py:732/822/828/833，我核到 grep 行）。
2. **可落字建议**：在"入口限定"清单后补"（上述行号为本轮只读核对；冻结稿附行号）"；known_absent 处保留"两处同源一致"声明即可。
3. **风险点**：把"给定事实集相容"读成"事实为真"（0c-v13.6 同款）——conflict/satisfied 只是相容性结论，绝不可升级为"环境条件已被实验证实"；这是条件轴最容易被下游化学叙事滥用的点。

**(b) 其余文本与实现一致**：**同意**。快照双向、两种不可变机制分写（ConditionFact/Requirement frozen，PathContext 非 frozen 靠内容身份重算）、场景转换 source_ref 必需（derive 拒 :2328-2332、调度拒 :539-544 `[探查读取]`）、旧边冻结 phase_history——均与实现一致；v9/r2/r3/r4 无进一步变化的说法与我读到的文件内容不矛盾（r3 变更仅 runflow/profile）。

---

## 五、判据五：供体一致性诊断

**(a) 8b"三个 None + converter 元数据"与 v12"失败 diagnostic 与下游 audit 各轴分开"**

1. **结论：同意**。我实际读到：`execution_ok=False` 早退把三判定字段全置 None 且不传 center_evidence（audit.py:2553-2562）；converter 兼容分支仍返回 `checker_version`、`center_match= None（来自 reaction_center_match）`、`declaration_mismatch`、`center_match_basis`、`evidence_refs=[alignment_ref]`（audit.py:2983-2993）——"版本/来源元数据 + center_match=None"精确成立；四个原始串守卫在早退之后、解析（:2596 起）之前（:2572-2592），"限定执行成功路径的解析之前"成立。中心 unknown 与其他轴 verified 不互斥：中心 unknown 走 R5（audit.py:1796-1803），其他轴状态由各自检查独立给出——"同一次 audit 仍可给其他轴 verified 并按首中规则处置"成立。
2. **可落字建议**：在 8b 补行号（2553-2562 / 2983-2993 / 2572-2592）；"三个 None"处加"（实现处 audit.py:2556-2557）"。
3. **风险点**：反向风险——把"其他轴 verified"读成"这次失败执行仍整体可信"；必须强调失败诊断下**中心不可 verified、事件不得凭它提交**（0d.1 的"声明酸/实际醛仍带声明结构提交但中心不可 verified"句要与 8b 交叉引用）。

**(b) 8d"未闭合但如实披露"作为 S3a/r4 边界**：**结论：同意，可接受**。静态事实我复核：`raise AuditContractError` 共 **10 处、全在 audit.py**（464、739、1076、1110、1589、1596、1603、1607、2547、2584，grep 实读）；audit.py 内 6 处 `except Exception`（1956、2054、2214、2316、2331、2491）**无一词法上包住这些抛点**（:857/:2581 的 try 只捕 ChemicalStateError，我读到其结构）；runflow.py 全文 **无 `except Exception`**（grep 实读），AuditContractError 窄捕获在 runflow.py:1091-1102（我实读）。**建议**：把"10 个抛点…无 enclosing 宽捕获"这句标为"静态证据（本轮 grep/read 实读行号）；动态闭合待执行验证（S3b caller + 宽捕获负控）"。**风险点**：静态无宽捕获被读成"任意第三方调用也不会吞异常"——通用动态安全仍未证，披露句不能缩。

**(c) v11 落字 + 0c 清单防再犯**：**结论：同意**。区域净变化不认证模板/机制、图等价非酶识别、legacy_cn_match 仅旁证——与实现（净变化判定在 `check_edit_against_donor`，strict 与 `strict_identity_of` 同源 audit.py:2676-2677 `[探查读取]`）相容；0c-v13.2 的 kind 层次我逐一核到（工厂 :473/:692、恢复 :846/:896+reason、writer store.py:398），足以防"分支名/版本/异常类张冠李戴"。**建议**：0c 清单每条后附上我核到的行号（见上），使"读码事实"可复核而非转述。**风险点**：旁证（legacy CN、图等价）在下游被累计成"多证合一"的伪强证据——建议在 8b 旁加一句"旁证不叠加升格"。

**(d) 其余条款**：**结论：同意**。奇偶构型比较/非四面体 unsupported、缺/歧义映射 ⇒ 中心 unknown、proof 内嵌不可变（proof_record_hash 入 input_hash audit.py:1382-1390 `[探查读取]`；改前提换 ID 的入口复算在 store.py:98-103/876-887 `[探查读取]`）——与文字一致。**建议**："proof_record 载荷不可变 + 入口身份复算"处注明"身份复算在 store 层（store.py:876-887），audit 层是复算比对+integrity 抛点（audit.py:1110）"，避免读者去 audit.py 找 ID 复算找不到。**风险点**：无。

---

## 六、0d 八条（生产链与调度消费契约）逐条

**0d.1 固定调用链与产品来源**：1. **结论：同意**（链路核到：production.py:396 执行 → :406 audit → :409 decide → :434 build event → :456 submit → :465 complete，我实读 390-475；产物 refs 来自 `prepared["product_states"]`（:417），与"产物身份=冻结池声明结构经内容派生"一致）。**待执行验证**：AtomTool 真实执行、冻结字节零改动。2. **建议**：v14 产品来源句后附 :417/:434 行号。3. **风险点**：把"工具真实执行输出"读成产物身份权威（v14 落字已防，务必保留"不改写产物身份"四字）。

**0d.2 生产 caller 异常义务**：1. **结论：有条件同意**——**行号需补正**：0c-v14.3 的"窄捕获 runflow.py:955-972"是 r2 标签；**当前 r3 源码窄捕获在 runflow.py:1091-1102**（我实读：`except AuditContractError` :1091、contract_aborted 落账 :1096-1101、return :1102），而 955-972 现为 `_derive_branch_context`/`_model_proposals`（:949-1050 我实读）。三类 RuntimeError（ChemicalStateError chemstate.py:172、HypothesisContractError hypothesis.py:117、ConditionContractError path_context.py:248，均 `RuntimeError` 子类，grep 实读）不在 drive 的捕获元组内 ⇒ 原样逃逸、action 保持 claimed——与文字一致；runflow 无宽捕获（grep 实读）。2. **建议**：在 0d.2 与 0c-v14.3 加"r3 行号：1091-1102（r2 标签 955-972 保留为历史）"，与 0c-v15.6 对冻结计划段的处理同口径。3. **风险点**："AuditContractError 已闭合"被外推成"所有契约异常都有失败结算"——正文已收窄并如实登记三类逃逸面，这句是本条最重要的诚实处，不得在冻结稿里被压缩。

**0d.3 三个 None 与缺 proof 语义**：1. **结论：同意**（行号同判据五 (a)；"None=未评估非通过"与 converter 元数据核到一致）。2. **建议**：无（可加行号）。3. **风险点**：把"缺证据不是执行失败"读成"可以按无事发生继续"——unknown 仍进 R5 阻断 R6，须保留这半句。

**0d.4 中心证据分段负控语义**：1. **结论：同意**。strict False ⇒ **violated**（audit.py:1188-1203，我实读，reason `center_evidence_strict_target_mismatch`）、strict None ⇒ unknown（:1204-1213，我实读）；proof 复算不一致 ⇒ AuditContractError（:1110）；跨假设未绑定 ⇒ 中心 unknown（:1131-1148 `[探查读取]`，"注册名+True 不构成核实"一致）；配平不升级（COMPLETION_LICENSE 许可边界 audit.py:272-276 `[探查读取]`）。2. **建议**：把 0c-v14.1 的 violated/R5v 结论行号（1188-1203）直接写进 0d.4。3. **风险点**：把 violated 弱读成 unknown ⇒ 错走 R5、少扣一档处置强度——这正是 0c-v14.1 要防的，行号必须随句。

**0d.5 队列与两类 deferred**：1. **结论：同意**（`schedule_hypotheses` selected/deferred/blocked queue.py:150 `[探查读取]`；两类 deferred 常量 queue.py:60-61 `[探查读取]`；activate 幂等/旧 revision ⇒ unchanged stale search.py:1026-1033 `[探查读取]`；双上限 search.py:1425-1433、预约 ID 确定性派生 :588-594 `[探查读取]`）。2. **建议**：在"blocked 计数不是防循环证书"后直接列两个上限的行号。3. **风险点**：把 deferred（可激活）与 blocked（不可执行）在对外报告里合并展示——化学上会让"暂缓路线"看起来"死路"或反之。

**0d.6 条件依赖与场景转换进调度**：1. **结论：同意**（source_ref 必需 path_context.py:2328-2332 与 queue.py:539-544 `[探查读取]`；旧边冻结 phase_history `[探查读取]`；unresolved_initial_supply path_context.py:1919-1929 / production.py:106-137 `[探查读取]`）。2. **建议**：无实质修改。3. **风险点**：把"essential conflict ⇒ 化学不可能"或"缺启动供应 ⇒ 循环不可行"读成终局化学结论——两句"不称化学不可能"是本条的化学护栏，须保留原样。

**0d.7 模型假设协议与有界格式反馈**：1. **结论：同意**。我实读 runflow.py:996-1050：可反馈错误类进 `register_format_feedback_round`、策略 0 轮 ⇒ `SearchBudgetExhausted` ⇒ `model_structure_failure`（:1010-1022）；不可解析直接结构失败（:1027-1034）；反馈重试取本地 scripted 响应 `self._next_model_response()`（:1024），无网络调用；弃权 `{"proposals": []}`（:1052-1057）；rank 只定次序不升 recorded（:1035-1045）。format-feedback-1 默认 0/范围 0-4（profile.py:323-328 `[探查读取]`）。2. **建议**：把"反馈轮的 scripted 重试不发网络"补行号（runflow.py:1024 + search.py 登记点 1666-1673 `[探查读取]`）。3. **风险点**：把"有界格式反馈"读成"可以改分子重试到通过"或把"scripted 网络 0"读成"真实 provider 也 0"——两句都已在正文，保持同段。

**0d.8 PPV1 独立 runner 分流**：1. **结论：有条件同意**（行号更正确认 + 一处子句需改）。分流我实读 grep：`start_run` 在 runner.py:214 判断、218-219 调 `start_ppv1_run`；`resume_run` 在 runner.py:315-317 调 `resume_ppv1_run`——**214-228 / 305-320 区间说法成立**。**⚠️ 但"runflow 同区间是 reconcile/drive"在 r3 源码不成立**：我实读 runflow.py:214-223 是 `_complete_action` 尾部（:209-223）、:226 是 S3B-01 段注释；:305-320 是 `_verify_frozen_plan_binding` 的锚行 SELECT（:304-321 我实读）。reconcile 在 :500-558、drive 在 :629-698 `[探查读取]`。2. **建议**：把该子句改为"runflow 同区间为 `_complete_action`/冻结计划锚定段（非分流代码），勿引"，0d.8 与 0c-v14.3 两处同步。3. **风险点**：行号张冠李戴会让后续复审按错文件取证（这已在 v13 犯过一次，不能再犯）。

---

## 七、0e 六条（恢复/调度/协议消费契约）逐条

**0e.1 冻结输入身份（含 v15 后段锚定）**：1. **结论：同意**（本条为 v15 受审重点，我逐行核）。读取侧四种拒因全核到：`frozen_plan_integrity_failure` runflow.py:254、`frozen_plan_missing` :259、`frozen_plan_corrupt` :266、`frozen_plan_digest_mismatch` :270（内容 hash 复核 :267）；传入比对 `frozen_plan_mismatch` :1504-1514；**后段锚定** `_verify_frozen_plan_binding` 定义 :274-390，三拒因 `frozen_plan_anchor_corrupt` :319/:326/:350、`frozen_plan_anchor_missing` :364、`frozen_plan_binding_mismatch` :377；锚只读 DB（SELECT search_actions :304-309）、task_key 经同一 `decision_task_key` 按行内字段重算（:333-342，函数定义 search.py:379 `[探查读取]`）；docstring 明写自洽证书不独立证明（:281-283）；**调用顺序核到**：resume 中锚定 :1521 **先于** `recover_run` :1522、隔离 :1528-1535、drive :1536-1538（我实读 1495-1549）——"首消费前、零新增、原资料保全"的顺序声称成立。范围声明（不做密码学签名、不抗全库协同改写）诚实，同意按此范围。**待执行验证**：15/15 真子进程探针、8 个新 r3 测试、879 全量。2. **建议**：① 三类拒因后附上述行号；② 补一句"锚行扫描中无 plan_digest 的 followup retrieve 被跳过（runflow.py:329-330），缺锚判定=无任何携带 plan_digest 的 retrieve 行"——把我读到的这条边界写进正文，防误读为"所有 retrieve 行都是锚"。3. **风险点**：把摘要比对读成"内容未被改"——实际是"读取侧内容 hash 核（:267）+ 锚摘要核（:369-382）"两层拼接，单独任何一层都不是完整证明；也不要让"锚定通过"被叙述成"冻结输入已认证为原始输入"（只在既有 DB 记录未被协同改写的前提下成立）。

**0e.2 恢复裁定接执行门（S3B-02）**：1. **结论：同意**（`isolate_recovered_failure` search.py:1155 起、claimed→blocked :1163-1164、`recovery_failure:<kind>` :1180、UPDATE 仅限 status=claimed :1210-1214 `[探查读取]`；blocked 激活拒 :1000-1006、认领拒 :1318-1325 `[探查读读取]`；H08 整 resume 拒 `[探查读取]`——后者我未亲读，标 `[探查读取]`）。2. **建议**：H08 条补行号。3. **风险点**：把"隔离"读成"坏 artifact 已被清理/修复"——它是不执行、不释放、保全证据；对外措辞须是"隔离"而非"已恢复正常"。

**0e.3 后续/转换集合完整性（S3B-03）**：1. **结论：有条件同意**。`_Driver.reconcile_followups`（runflow.py:500 def `[探查读取]`）与 `_ensure_transition_followup`（:577 def `[探查读取]`）存在；"从已核权威逐对象幂等补齐、不以 payload 引用计数>1 当证书、pending_followup 创建时一次冻结"——**我未逐行核到创建时冻结与逐对象补齐的实现细节，标 `[探查读取]/未亲读`**。2. **建议**：实施方给这两函数内"创建时一次冻结 pending_followup"与"逐对象补齐"的精确行号，冻结稿附上；否则本条降级为"读码未全覆盖"。3. **风险点**：把"补齐完成"读成"事件事实被重新生成"——补齐只排 followup/转换 action，不重发事件；"完整共同产物事件不截断"是化学事实完整性条款，不能被工程去重逻辑误伤。

**0e.4 执行会话互斥（S3B-04）**：1. **结论：同意**。我实读 resume 以 `with _DriverSession(run_dir)` 进入（runflow.py:1498）；flock(LOCK_EX|LOCK_NB) 与 `driver_session_active` 拒在 :420、:430-435 `[探查读取]`；崩溃 OS 释放注释 :402-403/437 `[探查读取]`；"同机文件锁、不宣称分布式锁/exactly-once"边界声明诚实。2. **建议**：把"不宣称分布式锁或外部 provider exactly-once"提到第一条（边界先行）。3. **风险点**：互斥被读成"数据不会出现并发损坏"——它只保证单机单驱动者，跨外部 SQL 改库仍不保证（0b 已披露同款边界，两处口径要一致）。

**0e.5 novel 独立假设消费者（S3B-05）**：1. **结论：同意**。novel 必带 reaction_spec（缺 ⇒ `json_field_error` 可进反馈）与 proposal_context：model_protocol.py:200-209、184-198 `[探查读取]`；`prepare_hypothesis` 单一构建源（runflow.py:818、:1069 我实读）；无足够内容 ⇒ 构造侧结构化拒（run_error）；空池仍组装底物档案（runflow.py:807-814 我实读）。**注意**：本条的"空池仍组装底物档案"与判据三⑤"substrate_profile 无生产 caller"冲突——以本条（实现）为准，⑤ 须改（见判据三）。2. **建议**：在"单一构建源"处补 runflow.py:818/:1069 行号。3. **风险点**：把"novel 走同一生产链"读成"模型提案内容已被模型外证据核实"——链相同只保证消费纪律相同，来源仍是模型；proposal_context 披露不得省略。

**0e.6 blocked 持久披露（S3B-06）**：1. **结论：同意**。`record_blocked_hypothesis` 写 status=blocked+defer_reason（search.py:1078/1136-1147 `[探查读取]`）；stop 报告 `unexplored.blocked_objects` 有界 100（search.py:3049-3053 `[探查读取]`）；主因优先级 `STOP_REASON_PRIORITY` user_stop > budget_limit > depth_limit（search.py:312-320 `[探查读取]`，取主因 :544）；blocked 存在 ⇒ 不称 exhausted_search（:3037-3041 `[探查读取]`）。2. **建议**：无实质修改（可附行号）。3. **风险点**：零深度+预算复合时主因报 budget_limit、depth_limit 藏进"其他原因"——对外读报告的人可能据此低估深度不足的影响；建议"其他原因"在摘要展示中同屏（不改优先级，只改展示纪律）。

---

## 八、0c-v13 七条落字逐条

1. **11+1 父绿精度**：**结论：有条件同意**——分类是执行类事实，**待执行验证**（需跑父基线）；"11 合法正控 + 1 已关闭坏输入拒绝控制"的**语义**我同意（正控/负控分开计数是正确口径）。**建议**：加"（待执行验证：父基线复跑）"。**风险点**：把"12 绿"读成 12 个合法正控、掩盖其中含已关闭坏输入控制。
2. **各入口 kind/reason 层次**：**结论：同意**（全部核到：工厂/strict `detail.kind`∈{unregistered_cx_class:473, unparseable_smiles:692/927}；恢复外层 kind∈{state_structure_unparseable:846, raw_structure_rejected:896} 内因读 `detail.reason` :849/:899；writer 外层 store.py:398；三别名落兜底 :456+:266 正则不命中）。**建议**：补 writer raw 码 `raw_structure_unparseable`（store.py:632，不带 reason）防跨入口串味。**风险点**：无（本条正是防风险条）。
3. **未知系数使元素/电荷账亦 unknown**：**结论：同意**（`full_known` audit.py:628，元素账 :641/:648、电荷账 :673/:679，我 grep 实读）。**建议**：附行号。**风险点**："两侧对称漏写在本轴不可见"若丢失，读者会以为账目天然完备——这句是防"账平=完备"的关键，须保留。
4. **omission 及声明清单边界**：**结论：同意**（`omission_pattern_matches` 只在 element_accounting detail、按 `COMMON_OMISSION_PATTERNS` 逐元素带符号相等标注 `[探查读取]`；completion 类对账是 λ_s×Δ（audit.py:973-980 实读），与 coefficient_binding_mismatch（:923-933 实读）分写）。**建议**：无。**风险点**：`omission_pattern_matches` 被读成"确认缺了该物质"——它只说"差额与某模式数值相符"。
5. **R2b/R1 对象范围**：**结论：同意**（R2b 依赖 caller 传 `contract_violation`：audit.py:1649/1748-1755 实读；R1 由 check 状态触发 :1672-1677，坏结构通常在首消费守卫异常逃逸——与 2b 一致）。**建议**：附行号。**风险点**：把 R1 当成"结构问题的主要防线"——主防线是首消费守卫（异常、非 R 行），R1 只是防御行。
6. **条件事实真实性**：**结论：同意**（assess 入口无 validate、只核相容性：path_context.py:1117/1172 `[探查读取]`；生产 caller 经 `load_context→from_dict` 内容身份核 production.py:327-335 `[探查读取]`）。**建议**：无。**风险点**：见判据四 (a) 第 3 点——相容≠真实。
7. **异常不当 R 行**：**结论：同意**（AuditContractError 抛点不落 R 行：audit.py:1110 抛出后 decide_admission 拿不到 audit；复合探针"首处拒绝后未执行内部段不报通过"是正确测试纪律）。**建议**：无。**风险点**：把"异常不落 R 行"读成"异常无需记录"——runflow:1091-1102 的 contract_aborted 落账就是记录口，两句话要成对出现。

---

## 九、0c-v14 五条落字逐条

1. **strict False ⇒ violated（0d.4 行话更正）**：**结论：同意**（audit.py:1188-1203 violated、:1204-1213 None⇒unknown，我实读；测试佐证 test_ppv1_r4_chem.py:515/519 `[探查读取]`）。**建议**：落字处补行号。**风险点**：弱读成 unknown ⇒ 错走 R5（正文已防）。
2. **λ_s×Δ 源位置 973-979**：**结论：同意（微调）**——实际为 audit.py:973-980（产物侧 973-976、反应物侧 977-980，我实读）。**建议**：改"973-980"。**风险点**：mimo v13 的"未确认"被当成源码缺式——正确理解是当时只读边界，现已核到。
3. **0d.8 行号更正**：**结论：部分同意，需再更正**——runner.py:214/315-317 分流我实读成立；"runflow 同区间是 reconcile/drive"**在 r3 源码不成立**（见 0d.8）；"窄捕获 955-972"是 r2 标签、r3 实为 **1091-1102**（我实读）；恢复隔离 search.py:1155-1224、失败短路 production.py:399-404（我实读：是**工具执行失败**短路→method_failed，非 AuditContractError 短路）——后者措辞建议注明"工具执行失败短路"以免误读。**建议**：按上述三处改字。**风险点**：历史行号未标版本 ⇒ 下一轮复审按旧行号取证失败（工程风险，但也间接拖慢化学判据冻结）。
4. **测试集合与数字精度**：**结论：有条件同意**——851→871→879、1453→1473→1481 等全部**待执行验证**；"数 test 函数不证明参数化绿 case""两集合不相加"这两条口径**同意**（认知论上正确）。静态佐证我核到：`tests/` 下 ppv1 测试文件 **32 份**（glob 实数）；`test_ppv1_s3b_r3.py` 恰 **8 个测试函数**（grep 实读 :171-355，5 负控+3 正控，与 §6"四+一负控/三正控"结构吻合）。**建议**：数字旁统一标"（待执行验证）"直到有独立执行回执。**风险点**：879/1481 被当成本轮通过的化学证据——它们只证明合成契约测试绿，不代表 dev/298 科学性能（§0 已声明，冻结稿不得删）。
5. **mimo v13 的四条披露已落进 0d**：**结论：同意**（0d.1 产品来源、0d.2 闭合范围+三类逃逸、0d.5 持久上限来源、0d.7 默认 0 轮——逐条在 0d 文本中核到存在）。**建议**：无。**风险点**：无。

---

## 十、0c-v15 七条落字逐条（v15 新增受审）

1. **r2 父基线红绿分类更正（15→13 行为红+2 形态红；54→52 绿）**：**结论：有条件同意**——语义口径同意（形态红≠行为红、"未执行到断言点"不得说成"跑完旧行为"，这是正确的取证纪律）；**具体数字与两个形态红的到达描述全部待执行验证**（需在父 2bedfc0 worktree 复跑）。**建议**：标"（待执行验证）"。**风险点**：红绿分类被当成"父基线缺陷清单"对外传播，夸大或淡化父侧问题两头都失真。
2. **abstain 空池父红更正**：**结论：有条件同意**（测试名存在：test_ppv1_s3b_r2.py:571，我 grep 实读；"请求数 0≠1 是行为红"**待执行验证**）。**建议**：同上标待验证。**风险点**：函数名 positive/negative 被当红绿标签（正文已防）。
3. **r2/r3 证据 HEAD 采集时序（c1211183 脏树→2bedfc0；r3 实施时点 2bedfc0+脏树）**：**结论：有条件同意**——属 git 事实，**待执行验证**（本轮无执行权限）。**建议**：附 `git rev-parse`/`git status` 回执（由主会话执行）。**风险点**：把"实施时点 HEAD"说成"受审 HEAD"（正文已更正，保持）。
4. **novel 来源标签 P2 落字**：**结论：有条件同意**——"expand 重建用默认 synthetic-pool-spec、event appearance 用后者、hyp ID 不受影响、proposal_context 保留"我**未逐行核到，标未确认**；其结论方向（不宣称来源标签逐字一致、不宣称认证现实来源）诚实，可接受为 P2。**建议**：实施方给出 decide 侧传 source_refs 与 expand 侧默认值的行号后再冻结此条。**风险点**：来源标签不一致若被读成"事件来源已被核实"——正文"不宣称已认证现实来源"必须与该条同屏。
5. **audit.py:2980-2981 旧注释（strict False ⇒ 至少 unknown）**：**结论：同意**——我实读该 docstring 确含"strict_target_match=False ⇒ 该证据不得构成 verified(至少 unknown,mimo 3.3(3))"，与 :1188-1203 violated 实现不一致；列冻结前 P2 文本同步项正确。**建议**：改为"violated（决策表走 R5v）；None ⇒ unknown"，并把 :451 一带同款句一并核（audit.py:451 有 "strict 轴(False ⇒ violated…)" 字样 `[探查读取]`，若已正确则不动）。**风险点**：读者信注释不信实现 ⇒ 把 violated 当 unknown，弱读处置。
6. **行号拆分（229-272 / 274-390 / 392 锁段；followup 两函数；store.py:1988）**：**结论：同意**——我实读 `_persist_frozen_plan` :229、`_load_frozen_plan` :242-271、`_verify_frozen_plan_binding` :274 def 到 :390、S3B-04 段注释 :392，与拆分完全一致；`_Driver.reconcile_followups` :500 def、`_ensure_transition_followup` :577 def、`verify_event_attachment_content` store.py:1988 `[探查读取]`。**建议**：0d.8 的"runflow 同区间 reconcile/drive"同步修正（与本条并列后不再有矛盾）。**风险点**：无。
7. **r2 交付数字口径（不另加总/红绿分列/历史单列）**：**结论：有条件同意**——口径同意（集合不相加、形态红与行为红分列）；**所有数字待执行验证**。**建议**：标待验证。**风险点**：多轮历史数字被拼接成"增长曲线"暗示性能提升——它们是不同集合的测试计数。

---

## 十一、§6 程序证据与状态（程序事实，不替代化学判断）

1. **结论：有条件同意**。**全部执行类声明待执行验证**：879 passed/0 skip、15/15 子进程探针、5 行为红+3 正控绿、G01 1481/8/17、父同字节、production.py 零改动、legacy 聚合 18007e6a…、git diff 仅 runflow+profile——本轮无 shell 权限，**一个数字都不背书，也不引用为已验证事实**。**静态可核且我已核到的**：① ppv1 测试文件 32 份（glob）；② `test_ppv1_s3b_r3.py` 8 个测试函数（grep :171/211/239/264/289/321/341/355），5 负控+3 正控结构与 §6 描述吻合；③ 三个被点名的 r2 测试存在（:175/:384/:571）；④ 契约版本字符串实读：`RUNFLOW_VERSION=ppv1-runflow-3` runflow.py:157、`FROZEN_PLAN_VERSION=ppv1-frozen-plan-1` :158、search-6/store-9/profile-14/search-limits-3/format-feedback-1/model-proposals-2 在 profile.py:240/168/164/310/323 与 model_protocol.py:58 `[探查读取]`；⑤ runflow 无宽捕获（grep 实读）、audit 10 个抛点（grep 实读）；⑥ 三类契约异常均 RuntimeError 子类（grep 实读）。
2. **可落字建议**：§6 每个数字后统一加"（待执行验证）"；把上面六项静态可核事实单列一段"本轮只读已核"，与执行类分开——这正是"来源声明与本会话独立执行分开"的落地。
3. **"程序上诚实但化学上误导"风险点（本节最大）**：879 绿 + 15/15 + 1481 绿是**合成规则级契约结果**，若在对外叙述里与"判据可冻结""化学结论可靠"并列，就是用测试计数冒充化学证据；工程数字不外推 dev/298 的声明必须与数字同屏（§0 已有，冻结稿与任何汇报都不得删）。

---

## 十二、冻结前必须更正清单（汇总，不替代上面逐条表态）

| # | 位置 | 问题 | 证据 |
|---|------|------|------|
| 1 | 判据三⑤ | "substrate_profile 无生产 caller"已过时，且与 0e.5 矛盾 | runflow.py:809 调用、:812-814 写 artifact（实读） |
| 2 | 判据三决策表 R3 行 | "action=blocked"与实现不符（实际结算 admission_deferred、不写 blocked 行；blocked 写点仅 search.py:1145/1213） | runflow.py:1122-1133、audit.py:1528-1529/1757（实读） |
| 3 | 0d.8 / 0c-v14.3 | "runflow 同区间是 reconcile/drive"在 r3 源码不成立 | runflow.py:209-226、:304-321（实读）；reconcile 实为 :500 起 |
| 4 | 0d.2 / 0c-v14.3 | 窄捕获行号 955-972 为 r2 标签，r3 实为 1091-1102，未标版本 | runflow.py:1091-1102、:949-1050（实读） |
| 5 | 判据三"恒入"句 | "恒入 center detail"语序易被读成全路径恒带 | license/scope 仅 audit.py:1009-1013；早退 :889-897 不带（实读） |
| 6 | 0c-v14.2 | λ_s×Δ 行号补全 973-979 → 973-980 | audit.py:973-980（实读） |
| 7 | 0d.2 等 | 一切执行类数字/红绿分类/HEAD/字节一致 → 标"待执行验证" | 本轮无执行权限 |

**待执行验证清单**（给主会话）：① PPV1 全量与 r3 新 8 项、父 2bedfc0 红绿分类复跑；② G01 全量；③ RDKit 2026.03.6 词法与往返正控（plain/ABS/AND/OR/自由基 + and/or/rad 负控）；④ `git diff 2bedfc0..HEAD -- src/pathway_v43/pollutant/production.py` 与 legacy 聚合哈希；⑤ 0c-v15.4 novel source_refs 两侧行号的读码补证。

**结论汇总（非评价式，仅索引）**：判据一–五及 0d/0e/0c 各条的**化学口径我逐条同意或有条件同意**，条件集中在上表 7 项（6 项文本更正 + 1 类待执行验证）；**在第 1、2、3、4 项改字并完成"待执行验证"清单之前，不建议冻结**；改字后无需新增化学评审轮次，除非更正过程中触碰判据一–五正文。
