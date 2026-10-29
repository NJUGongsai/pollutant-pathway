# mimo 化学评审回应 r29（2026-10-10）

- 通道：opencode run -m opencode/mimo-v2.6-flash-free（免费档，通道 A；主会话转发落盘）
- 请求：docs/mimo_ppv1_chem_review_request_r29.md（短轮：r28 条款项与 P2 订正的采纳核对 F1-F7）
- 只读 provenance：评审员以读取工具核对源码/文档，无 shell 执行权限；执行类断言均自带"待执行验证"
- 原始流：docs/review_evidence/ppv1_r29_mimo_2026-10-10/raw.txt
- 采信原则：与程序证据互证为准

---


⚙ execute {"code":"const results = await Promise.all([\n  tools.grep({pattern: \"coproduct_ignore_tier\", path: \"/Volumes/CC/Enzyme_Agent/dependingv43\"}),\n  tools.grep({pattern: \"trigger_equivalence\", path: \"/Volumes/CC/Enzyme_Agent/dependingv43\"}),\n  tools.grep({pattern: \"stereo_edit_unsupported\", path: \"/Volumes/CC/Enzyme_Agent/dependingv43\"}),\n  tools.grep({pattern: \"至少一候选映射\", path: \"/Volumes/CC/Enzyme_Agent/dependingv43\"}),\n]);\nfor (const r of results) { text(r); text(\"-----\"); }\n"} 
⚙ execute {"code":"const results = await Promise.all([\n  tools.grep({pattern: \"集合相等\", path: \"/Volumes/CC/Enzyme_Agent/dependingv43\"}),\n  tools.grep({pattern: \"恰一可复现\", path: \"/Volumes/CC/Enzyme_Agent/dependingv43\"}),\n  tools.glob({pattern: \"docs/*R29*\", path: \"/Volumes/CC/Enzyme_Agent/dependingv43\"}),\n  tools.glob({pattern: \"docs/mimo_ppv1_chem_review_response_r*.md\", path: \"/Volumes/CC/Enzyme_Agent/dependingv43\"}),\n]);\nfor (const r of results) { text(r); text(\"-----\"); }\n"} 
✱ Grep "trigger_equivalence" in . · 90 matches
✱ Grep "coproduct_ignore_tier" in . · 44 matches
✱ Grep "stereo_edit_unsupported" in . · 38 matches
→ Read docs/mimo_ppv1_chem_review_response_r28.md 
→ Read docs/mimo_ppv1_chem_review_request_r29.md 
→ Read docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_R1_DELIVERY_2026-10-10.md 
✱ Grep "多重集语义|集合相等|等价映射合并" in . · 100 matches
✱ Grep "gate_scope|bases_by_graph" in src · 19 matches
✱ Grep "重复组分天然塌缩|参与物比较" in . · 9 matches
✱ Grep "至少一可复现|确定性选首|恰一可复现" in . · 7 matches
→ Read src/pathway_v43/pollutant/s5b_scoring.py [offset=300, limit=130]
→ Read src/pathway_v43/pollutant/evaluation.py [offset=2300, limit=80]
✱ Grep "W-V2|恰一" in . · 100 matches
✱ Grep "W-V2|恰一" in docs · 100 matches
→ Read src/pathway_v43/pollutant/recorded_source.py [limit=75, offset=530]
✱ Grep "reactants ==|products == to_states|多重集|集合相等" in src/pathway_v43/pollutant · 11 matches
→ Read docs/TASK_V43_PPV1_S5B_HIT50_V3_2026-10-10.md [limit=55, offset=122]
→ Read src/pathway_v43/pollutant/evaluation.py [limit=60, offset=1030]
✱ Grep "def _record_products_strict|def _executed_components_strict" in src/pathway_v43/pollutant/recorded_source.py · 2 matches
✱ Grep "E1–E3|E1-E3|待复审清单|随新登记" in docs · 18 matches
→ Read docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_CODEX_REVIEW_2026-10-10.md 
→ Read src/pathway_v43/pollutant/recorded_source.py [limit=40, offset=340]
✱ Grep "9-4|9-④|qid_strict|同步" in docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md · 6 matches
✱ Grep "stereo|unsupported|charge_edits" in src/pathway_v43/pollutant/real_model.py · 2 matches
→ Read docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md [limit=45, offset=488]
→ Read docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md [limit=20, offset=86]
→ Read src/pathway_v43/pollutant/s5b_compiler.py [limit=30, offset=373]
✱ Grep "bases_by_graph_missing|bases_by_graph_empty|foreign|missing_keys|gate_scope|def test_" in tests/test_ppv1_s5b_hit50_v3r1_scope.py · 26 matches
✱ Grep "resolve_data_scope|data_scope_invalid" in src · 16 matches
# mimo 化学评审回应 r29（v3 回修轮 R1 采纳核对，短轮）

**执行边界声明（先行）**：本轮只用读取类工具（glob/grep/read）核对了 `docs/mimo_ppv1_chem_review_request_r29.md`、`docs/mimo_ppv1_chem_review_response_r28.md`、`docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_R1_DELIVERY_2026-10-10.md`、`docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_CODEX_REVIEW_2026-10-10.md`、`docs/TASK_V43_PPV1_S5B_HIT50_V3_2026-10-10.md`、`docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md`，以及源码 `evaluation.py`（:1030-1089、:2304-2350 等实读区）、`s5b_scoring.py`（:319-429）、`recorded_source.py`（:340-369、:530-590）、`s5b_compiler.py`（:373-402），grep 级核对 `real_model.py`、`tests/test_ppv1_s5b_hit50_v3r1_scope.py`。**未运行任何测试/脚本、未访问 git（无 shell 权限）**，行为类断言一律标"待执行验证"；行号均为本轮实读或 grep 实证；未访问金标/题面/gitignored 目录。**先例校正一处**：r28 回应引用的 `evaluation.py:2245-2248`（trigger_equivalence）现位于 **:2337-2340**（本轮 `resolve_data_scope` 等新增使行号下移），下引均为当前行号。

**来源声明小注**（不影响化学结论）：请求头部"本轮变更集中在 {evaluation,s5b_scoring,s5b_builder,s5b_orchestrator}.py + rate_gate.py"与交付书 §九 提交构成（8 源文件：adapters/{rate_gate,**llm_client**}、pollutant/{evaluation,s5b_scoring,s5b_orchestrator,**s5b_cli,s5b_worker,real_model**}，无 s5b_builder）**不一致**；两者均非化学判据文件，化学面无影响。提交构成核对属程序面（归 Codex），我未核验 fecb00055 的 git 构成——**待执行验证**。

---

## F1（集合/多重集二分表述）

**结论：同意——二分表述达到"二选一写死"的要求；"同组分写两次塌缩"在本判分契约下化学上诚实，确认合理，无需反例级修改；仅需报告层措辞护栏（见下）。**

核对到的落点：交付书 §七.1（`POLLUTANT_PATHWAY_S5B_HIT50_V3_R1_DELIVERY_2026-10-10.md:162-169`）明确"判分侧参与物比较 = 集合语义……**禁止静默改冻结判据为 multiset**；recorded 编译墙的产物核对 = 严格多重集，两口径分别写真、不混用"——这就是写死的二分，且把"冻结判据不许为文字改代码"的方向也钉死了，正确。实现侧证据：evaluation 参与物两侧确为集合（`evaluation.py:1032-1035` 以 `state_ref` 建 set；:1062-1068 exact/superset/partial_subset 三分类均按集合运算；注释 :1058-1061 自称"集合两侧相等"）；预注册侧表述一致（grep 证据：`POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md:240`"全金标产物集合相等"、:286"参与物集合相等 + step_scope 一致"）。recorded 侧确为多重集：`recorded_source.py:351-358`（`_record_products_strict` 逐条保序保重）、:361-369（`GetMolFrags` 逐碎片出现，同结构两碎片 ⇒ 两条目）、:563-566（sorted list `!=` 比较 = 多重集相等）。"状态 ID 按严格身份内容寻址"沿用 r28 读码结论（chemstate.py 本轮未重读——**未确认级别：r28 已证，本轮未复核**）。

化学上为何塌缩合理（确认请求方理解，无改变判定的反例）：①判分契约本就不核计量（系数仅披露，r28 A6 已核 `evaluation.py` 该口径）——两份不可信的份数事实做多重集比较只会制造假失配、惩罚诚实模型，**集合是这对事实下唯一诚实的比较**；②塌缩是对称的（参考侧同结构双 occurrence 同样按内容寻址塌缩），不会单边制造假 strict；③"同结构共同产物份数不在判分面"已是 r25 冻结裁定（要求披露 coverage_statement、不得声称模型漏报第二份），本轮表述与之同源，不是新放宽。唯一边界情形——参考声明 2 份、模型写 1 份判 strict——是 r25 裁定的既知既受口径，不构成新误导面。

**可落规则文字**：在 §七.1 二分句尾补一句引用——"`份数不在判分面`（r25 coverage_statement 裁定）；集合相等**不得**复述为'参与物清单/份数与参考完全一致'"。

**误导风险**：报告层把"集合相等"复述成"参与物完全一致（含份数/计量）"——程序诚实、化学误导（判分二并不看系数）。二分表述本身已防住规则层误读，风险只在下游复述，故加如上护栏句即可。

## F2（W-V2 "恰一可复现"修词）

**结论：有条件同意——交付书层的改写忠实且与代码行为一致（不再暗示唯一性）；但"恰一"措辞仍残留在一处活源码注释与一处历史交付文稿，修词未落到措辞的两个原始出处。**

核对：代码行为与新表述一致——`recorded_source.py:546-551` `reproducible` 是列表（至少一语义）、`chosen = reproducible[0]`（确定性选首）、:583 `n_equivalent_mappings` 机读披露等价映射数、`s5b_compiler.py:812` 注释"等价映射合并（取首个确定性对齐）"（grep 证据）。交付书 §七.2（:170-172）登记的规范措辞"至少一可复现、同严格多重集合并、确定性选首"与复审 §3.2（CODEX 报告 :65）逐字对应。**残留**：①活源码注释 `recorded_source.py:541-543` 仍写"择产物集可复现者(**恰一** executed 组分多重集 == 库记录产物多重集;等价映射同集合并取首)"——前半句"恰一"与后半句"等价映射合并取首"自相矛盾（合并后可复现者可多个）；②v3 交付书 `POLLUTANT_PATHWAY_S5B_HIT50_V3_DELIVERY_2026-10-10.md:176-177` 仍写"映射中**恰一** executed 组分多重集……者被选中"。R1 变更清单不含 recorded_source.py（交付 §九），故注释未修。

**可落规则文字**：下一小修把 `recorded_source.py:541-543` 注释改为"至少一候选映射可复现该严格多重集；同严格多重集的等价映射合并；确定性选首（`reproducible[0]`）"；v3 交付书 :176-177 加勘误指针指向 R1 §七.2（历史文稿不静默改写，指针制）。

**误导风险**：活源码注释是未来维护者最常读的规范来源——残留"恰一"可能诱使下一个人写出"`len(reproducible)==1` 才放行"的错误断言/测试（把确定性选首的工程事实冒充唯一性证明），或在报告里宣称"编译器验证了映射唯一"。化学上等价映射本可多个，"唯一性"不可证也不需要，此误读属于"程序诚实、化学误导"。

## F3（§9-4 门 D1 附条件采纳）

**结论：同意——与我 r28 D1 的附条件对齐，三件均落地；两处措辞级精度差建议随下轮文字订正（非阻塞）。**

逐条核对（`s5b_scoring.py:338-399` 实读）：①缺 coverage/缺 pairing/缺 bases ⇒ `bases_by_graph_missing` 拒（:339-347，pairing 非 dict 同路径）✓；空 bases ⇒ `bases_by_graph_empty` 拒（:350-351）✓——**堵住了 r28 指出的"空集空真放行"口子** ✓；②键集精确覆盖注册图：missing_keys/foreign_keys 分别拒（:353-360），并机读披露 expected/missing/foreign（:382-390）✓；③值类型+全 qid_strict：非字符串或非 `qid_strict` ⇒ `bases_not_all_qid_strict`（:361-368）✓；④门位于 `evaluate_scientific` 产出之后、逐题聚合循环（:400-421）与 metrics 落盘之前——"先拒零 metrics"位置正确（静态读码；**行为待执行验证**）；⑤"核档位与覆盖、不核映射"已落字 ✓，但精确位置是 **detail.gate_scope 机读字段**（:391-396"本门只核配对档位与键覆盖……不核 qid↔图映射正确性——映射由评测器权威链（evaluation-4/5 配对守卫）负责；本门不证明 qid 真值"），**detail.note（:397-399）并不含此 caveat**——请求 F3 写"门 note 落字"措辞不准（实质已达成，落在 gate_scope）；⑥data_scope 白名单：`resolve_data_scope`（`evaluation.py:269` 起，kind=data_scope_invalid）与 `score_s5b_batch` 入口同源消费（`s5b_scoring.py:204-220`，kind=s5b_data_scope_invalid，先于批装载）——r28 D1-③ 的入口校验建议已落 ✓；负控测试 grep 证据在案（`tests/test_ppv1_s5b_hit50_v3r1_scope.py:278-354`：missing/empty/缺键/foreign/非字符串值/非 strict + gate_scope 断言；**行为待执行验证**）。

两处精度差：a)"expected graphIds 非空"没有显式检查——是**结构性不可通过**（注册图空 ⇒ 非空 bases 全算 foreign、空 bases 走 empty 拒），fail-closed 成立但 reason 里无专属项；b)键经 `str()` 归一比对（:353），非字符串键（如整数）会被强转而非拒绝，"类型核"若涵盖键类型则与实现有一丝口径差（值类型严格核 ✓）。

**可落规则文字**：①"expected graphIds 非空"补一个显式检查或把文字写成"注册图集合为空/与 bases 键集不等时结构上不可能通过（fail-closed）"；②键比对口径写明"键经字符串归一比对、**值**类型严格核"，或补非字符串键负控；③请求与交付文稿中"note 落字"统一改为"gate_scope 机读落字"，避免与 `detail.note` 字段混淆。

**误导风险**："双保险"被复述成"qid 映射已独立核过"——gate_scope 文字已防，但下游引用时若只提"双保险"不提"不核映射"，就把档位核对冒充映射核对；任何报告引用本门时必须连"映射正确性由 evaluator 权威链负责"一起引。

## F4（trigger_equivalence 落字与 §9-④ 同步句）

**结论：有条件满足——代码侧两义务均在位且我 r28 已核实其为真；文档侧"随新登记落字"是冻结纪律下的合理安排，但义务无机器强制点，须在发车清单把待插句原文写死，否则有被遗忘的现实风险。**

核对：`evaluation.py:2316-2321`（W-V6.3 注释：触发 ⇔ 两个 qid 映射皆空 + "配对档若改逐图混合，本守卫须同步改为逐图判定，不得沿用整批判"）与 detail 字段 :2337-2340（机读 trigger_equivalence 同句）——r27/r28 要求的同步义务声明在位 ✓；测试断言内容子串（`tests/test_ppv1_s5b_hit50_v3_wv6.py:260-262`，grep 证据，**行为待执行验证**）。预注册为冻结稿（`POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md:523-527` 状态行：本稿为唯一预注册依据、首跑不可因分数改写），其 §9-④（:497-503）现文只写"bases_by_graph 全 = qid_strict ⇒ 阻断"，**确无**整批二档触发等价句——本轮未改冻结稿、将其登记为"随新登记落字"义务（交付 §七.7 :185-188、§十.3 :227-228；CODEX 报告 §5 D3 :117 亦同）✓。我 r28 的原建议是"搬进 §9-④ 文字"；采纳走了"不改冻结稿 + 登记义务"路径，实质等价于把落字时点移到下一次新登记——可接受，但**义务只存在于交付书/复审报告的叙述里，没有机器检查点**，与 F5/E 设计轮的"待复审清单"同一遗忘风险类。

**可落规则文字**：在发车清单（CODEX 报告 §7 的六条清单或其后继登记文）中新增一条硬门项，逐字引用待插入句原文（"真实批配对为整批二档：触发 ⇔ manifest_qids 与 export_qids 皆空；若配对档改逐图混合，§9-④ 与 evaluation-5 守卫须同步改为逐图判定"），并指定核对步骤（登记文档 SHA 里含该句）——义务从"叙述"升为"可核对项"。

**误导风险**：低但存在一种——未来把"配对档改逐图混合"当成纯工程改动，只改评测器守卫、忘了判分门（§9-4 是全局 qid_strict 断言，逐图混合下其语义会悄悄变成只核剩余严格图），两边判据分叉而无红灯。同步句落字即为封此风险。

## F5（stereo 消解设计未实施确认）

**结论：确认——本轮未暗改 stereo_edit_unsupported 边界；E1–E3 结论已登记，但登记只到抽象层，四类反例的具体危险机理建议随设计轮任务书逐条带入，防止登记丢失细节。**

核对：①`s5b_compiler.py:381-395` 电荷/手性变化结构化 unsupported 与 v3 快照同位同文（`:391` stereo_edit_unsupported，与 CODEX 报告 §3.4 :75 引用行号一致；R1 交付 §九 变更清单不含 s5b_compiler.py）✓；②`real_model.py:216/:283`（grep 证据）capability `unsupported` 仍含 `stereo_edits`——r28 E2-⑥ 要求的能力面未动 ✓；③测试断言维持（`tests/test_ppv1_s5b_hit50_v3_wv3.py:220`，grep 证据）✓。登记核对：E1–E3 与 E/Z 盲区登记在 CODEX 报告 §3.4（:77"消解须另批证明执行后确实不再为立体中心、rhs 无手性声明、仍有中心/新建中心不放行、执行后 rhs 立体同源复核与机器诊断；E/Z、非四面体等未支持范围明确"）与 §5 表（:120），交付 §十.3（:227-228）登记"stereo/E-Z 能力边界披露随新登记/下一小修落字" ✓——"留待独立设计轮"属实。**缺口**：登记文字覆盖了"仍有中心/新建中心不放行"，但 r28 E1 反例 2 的**具体机理**（RDKit 四面体 CW/CCW 键定在键表顺序上，RemoveBond/AddBond 移动邻居序 ⇒ 标签保留而解读翻转 = 静默对映体翻转；有机磷/SN2 型是本域核心底物形态）不在任何登记文本中——抽象表述"仍有中心不放行"保不住"为什么不能放行"。

**可落规则文字**：独立设计轮任务书须直接引用 r28 E1 反例①–④（stereo_created、SN2/仍为四面体中心的断成键、E/Z、非四面体/累积烯）与 E2 的①–⑥窄化条款为验收面，登记粒度从"结论"升到"结论+机理+反例"。

**误导风险**：设计轮若只拿到"仍有中心/新建中心不放行"一句，可能把"键级变化 ⇒ 手性派生"重新泛化（r28 已证的最干净反例是 stereo_created 与有机磷中心），在立体盲参考下转化为假严格命中——"程序诚实、化学误导"，且残余风险在事件记录层（无证据绝对构型写进 provenance）。

## F6（coproduct_ignore_tier 未实施确认）

**结论：确认——本轮零实施、零预注册字段新增；T1′ 九条件确实仅存在于裁定选项登记层。**

核对：全仓 grep `coproduct_ignore_tier` 零 `src/` 命中（仅 docs 与 review_evidence）；预注册稿无该字段（grep 零命中）；T1′ 九条件登记在 r28 回应总裁定（`mimo_ppv1_chem_review_response_r28.md:150`）、CODEX 报告 §3.4（:79"V4 当前仅请求稿，没有启用……本报告不代做裁定"）与 V4 请求稿（`MIMO_PPV1_S5B_HIT50_V4_COPRODUCT_IGNORE_TIER_REVIEW_REQUEST_2026-10-10.md`）✓。chemistry_supply README :27 亦记"源码未实现 coproduct_ignore_tier"。与冻结判据零冲突（该档本就是 proposed、面向产物侧差集的裁定选项，不触碰任何现行判定路径）。

**可落规则文字**：无需新文字；维持既有纪律句即可——"若 teacher/用户裁定启用，走独立新预注册字段（四元组：档位+白名单 cn 身份哈希+方向策略+追溯开关），不升本批 partial、不回填旧分数、首生效批 post-hoc 敏感性表 + 纯位次/新覆盖效应分离计数"（r28 条件⑦⑧，CODEX :79 已逐项登记）。

**误导风险**：唯一要防的是裁定前有人把"已登记 T1′ 九条件"读成"该档已获批/已就绪"——登记 ≠ 授权，任何批要启用须先过独立预注册与用户逐次拍板。

## F7（总判定与误读模式）

**总判定：一句话——r28 条款项与 P2 事实订正的采纳总体成立、无新增化学阻塞（零 P1）；附两项条件：F2 残留"恰一"活注释须下一小修订正（`recorded_source.py:541-543`）+ v3 交付文稿加勘误指针，F4 的 §9-④ 同步句义务须在发车清单写死待插句原文与核对步骤。** 判据一~五、0d/0e 与本轮全部改动零冲突；F1–F7 均未发现"程序上诚实但化学上误导"级别的现行实现，风险集中在措辞层（F2/F7 两条）与义务登记层（F4/F5 两条）。

**最值得警惕的两个表述误读模式**：

1. **"集合相等"被复述成"参与物清单/份数与参考完全一致"**——判分契约不核计量（系数仅披露）、份数不在判分面（r25 裁定），把集合语义讲成"完全一致"就是拿未核过的轴冒充已核轴；一切下游文字引用 evaluation 集合语义时必须连带"集合比较、份数不核"限定（F1 护栏句）。
2. **"恰一可复现"残留被读成"映射唯一性保证"**——确定性选首是工程事实，不是唯一性证明；等价映射可多个且无化学意义，凡"恰一"式断言（测试或报告）都把可复现性偷换成不可证的唯一性，属"程序诚实、化学误导"（F2；`recorded_source.py:542` 注释是该误读的现存载体）。

（所有执行类断言——门/守卫行为红绿、测试负控实际执行、提交构成 git 核验、`GetMolFrags`/strict_identity 具体运行行为——维持"待执行验证"；程序/存储事实以 Codex 复核为准。）
