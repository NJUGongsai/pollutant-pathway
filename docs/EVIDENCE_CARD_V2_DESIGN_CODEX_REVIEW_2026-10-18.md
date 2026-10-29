# 证据卡 v2 设计冻结前置代审（2026-10-18）

**结论：回修后再申请设计冻结；v2 方向可继续。未发现 P0。** 本轮发现三组 P1 设计合同缺口，不是三个已实施程序漏洞：A，source 干预与实验身份未冻结；B，新字段事实与计算合同未冻结；C，验收与判读合同未闭合。以下子项不重复计漏洞。无需本轮调用真实模型、证明科学收益或实施全部代码。

## 范围、快照与证据等级

对象为[设计任务书](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md:1)，不是代码交付。实际 HEAD 为 `f222096087031543eb4d0b7ac98dbb24306dffed`；任务书与 mimo 场景3回应当时均为未跟踪文件，不能说它们已包含在该提交。任务书 SHA-256 为 `0bcde2200186f82ff083aa43577aa462d5577e98c8519a3ad9a7048b1a5e1542`；其他输入哈希见[快照](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ec_v2_design_codex_2026-10-18/snapshot_metadata.json)。

上游批数字均为 **298=RHEA 通用酶学/已见题** 的许可汇总报告自述。本轮未读金标、题面、reports/ 或封存逐题 run，未复算真实归因、判分或批结果；没有网络、外部模型、pytest、git 写操作。只在全新 tmp 中运行纯构造 helper 与数学逻辑程序。证据目录内脚本供复跑，实际执行位置不在永久证据目录。

| 本轮独立执行 | 结果与证明范围 |
|---|---|
| 完整归档当前 src（含 vendor）与 metadata 后运行两个 helper 程序 | 均退出 0、内置断言通过；90 个归档文件前后哈希相同，无 pyc/pytest 缓存。验证当前事实接口，不代表未实施的 v2 已通过。 |
| 合法 prepare_hypothesis → 证据卡 | 系数 2 输出两侧 `["2","2"]`；None 输出 `["unknown","unknown"]`；输入与对象未改。 |
| 六组构造结构各双跑 | 中性酸/胺命中；羧酸根/质子化胺合法渲染但相应 FG 空；非法 SMILES 也为空但 render=false；10 份 CCO 的 n_hits=10、渲染 matches 仅8条。 |
| 三种合成用户 JSON | 无 evidence／有 source／删 source 三种均仍有顶层 transformation_ref。 |
| 数学逻辑程序 | 报告给定 15:2 的双侧精确二项 p=0.002349853515625，与 0.0024 舍入相符；只核算式，不核真实计数。另证联合方向门可与覆盖停点同时成立。 |

可复跑资料：[feature_findings](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ec_v2_design_codex_2026-10-18/feature_findings.md)、[feature_probe_result](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ec_v2_design_codex_2026-10-18/feature_probe_result.json)、[source_surface_probe_result](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ec_v2_design_codex_2026-10-18/source_surface_probe_result.json)、[design_logic_output](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ec_v2_design_codex_2026-10-18/design_logic_output.json)。环境为 Python 3.11.16、RDKit 2026.03.6；当前 schema=`candidate-evidence-2`、descr=`candidate-evidence-descr-2`、prompt=`fe9eaf770deb19f8c6eec9aee14febe83f6b2d47f53e1c60002bb808eb3b0f4e`。

## Q1 三源合流忠实性：不通过设计冻结（P1-A/B；伴随 P2 措辞纠正）

裁剪方向大体忠实：任务书15–18、21–25行对应 mimo Q3 的减负、保留紧凑事实、加 FG delta 与条件性负证据。但 source 和 participants 两行已超出“实施细化”而未形成可验收合同。

**P1-A：source 处置须覆盖完整模型可见面，并选定实验身份。** [任务书19行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md:19)保留“全盲／仅通道大类”两方案；[47行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md:47)交实施单决定。现有[source 对象](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/candidate_evidence.py:183)还含 origin_group_key；[用户载荷263行](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:263)无条件渲染顶层 transformation_ref。合成探针确认删卡 source 后记录引用仍可见，故不能称“不携任何记录身份”。A 对单个 v2 的双臂设计也不能比较两个 source 备选本身。

最小补齐：冻结前选定一个假设方案，列 B 臂完整可见字段的删/留/中性化表，含顶层引用与 origin_group_key。若仅裁卡内重复来源，应如实命名；若比较两方案，分别编号、预注册，不能跑后择优当作同一预定实验。无需先付费找出最优方案才允许冻结。

**P1-B 的 participants 子项：保真与展示目标不一致。** [任务书20行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md:20)要求“系数一律 unknown”，而[当前 helper](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/candidate_evidence.py:147)保留已知值，[提示词188/190行](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:188)明定 unknown=系统不可得、系数未记录。mimo“unknown 留一词”不是所有系数都未知的证据。可删该字段，或明确“未展示”并同步提示词；不能把已知写成未记录。

保留 side/role/smiles 全列表仍可数行，紧凑化本身不能保证“不渲染行数差”。最小方案是删 coefficient_status 等冗余完整度提示、保留真实组分与共底物方向；如坚持隐藏行数差，需明确格式，不能补假条目或删真实共底物凑齐。

**P2：证据强度用语须收窄。** [归因报告13–18行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN14_ATTR_PROBE_RESULT_2026-10-17.md:13)的15:2是全卡 on/off 下第一名来源构成翻转，足以重议 source，未隔离 source 字段因果。该报告25–27行自述损失题12/14同通道；10/14参与物行数更多、p=0.078是待试方向，非完整度因果证明。机制乙未获支持，不能说位点锚获证；Gasteiger 裁剪可由题内零方差与成本支持。任务书17行还应明确是否保留 mimo 建议的 alignment status；conditions 合并仍要保留 requirements 缺席/unknown 与 participant_list_status 的语义；页头历史数字应补 298 题域及单批单档限制。逐行核对见[source_table_findings](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ec_v2_design_codex_2026-10-18/source_table_findings.md)。

## Q2 预注册边界：不通过设计冻结（P1-C；版本项归 P1-B）

[任务书29–32行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md:29)包含必要方向，但“有一句约束”尚不等于能验收。设计书不必现在写完整预注册；应明确下列必备参数由后续预注册填完，未填不得发车。

| 必备合同 | 最小补齐 |
|---|---|
| 冻结面与兼容 | 冻结模型调用前的池/检索输入；不把受处理影响的 novel 输出强行冻结。A 用户 JSON 字节兼容、两臂共用同一新版 prompt 可以共存，应明确比较对象。不能把用户 JSON 兼容扩称整请求与旧批同字节。 |
| token ≤+13% 硬门 | 预先定义同输入 A 基线、system/user 计量范围、tokenizer及版本或保守上界、逐题/批合计、反馈/重试/失败口径，区分发车前离线门与发车后实际费用账。上游 +26% 是不同调用数下的实际聚合，不自动等同固定载荷增量。 |
| novel 第一名指标 | 明定是模型声明首选、去重后 effective 第一还是实际首提交；冻结分母、无首选处理与折叠口径。T-F 可将 novel 第一位继承给池反应，不能混同“偏好被挤出”。这是行为指标，CC 可事前选作工程防退化线；不等于化学正确性正控，需写与 hit/strict 冲突时优先级，不能靠来源配额或偏爱 novel 规则做过线。 |
| 覆盖停点与版本 | 明确已有全局/分族 strict 停点优先；如更改，须新预注册事前显式说明并获 CC 确认。除 prompt 哈希外，列 schema、descriptor、RDKit 身份与断言规则。 |

旧[预注册37行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN14_EVIDENCE_AB_PREREG_2026-10-15.md:37)规定全局或任一族 strict 净失≤−3停点；[结果报告31行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN14_EVIDENCE_AB_RESULT_2026-10-16.md:31)按此触发。任务书39行“含停点”不能被30行的新联合门静默取代。版本依据见[candidate_evidence27行](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/candidate_evidence.py:27)与[45行](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/candidate_evidence.py:45)。现在不要求替未定稿字段提前编版本号。

## Q3 判读分界：不通过设计冻结（P1-C，同组不重计）

[任务书30行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md:30)忠实保留 mimo Q5 联合正向条件；但任务书实际写的“仍负”未定义混合结果，用户请求中概括的“否则升级”也不是联合正向条件的逻辑补集，不能覆盖原停点。独立算术反例：纯构造 A 为 hit@1=3、strict=7、rank>1=4；B 为3、3、0。联合方向条件通过，strict却−4触发旧停点。该反例不涉及真实题或新性能要求。

所有读法先服从冻结的覆盖/费用/纪律停点；未触发停点时至少写清四象限：

| hit@1 B−A | rank>1 B−A | 本批允许读法 |
|---|---|---|
| ≥0 | ≤0 | 探索性支持字段修正方向；不认证完整因果或科学收益。 |
| ≥0 | >0 | 混合结果，待归因；不直接判档位不适。 |
| <0 | ≤0 | hit@1仍未兑现，不因rank改善宣布修复。 |
| <0 | >0 | 两面仍负；满足最小有效集等前提后可讨论结构/档位，不据单批判普遍不适。 |

[mimo98–101行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_chain14_scene3_review_response.md:98)明确单批噪声与外推限制。“设计问题确认”应收窄为当前任务/协议下方向获支持；“仍负”允许开启结构/档位议题，不等于已证明不可修。

## Q4 实施前置：不通过设计冻结（P1-B，同组不重计）

先修 SMARTS 质子化容忍是必要前置，合成输入确认现有漏检，但这不赋予“未命中⇒必需官能团缺失”的通用许可。应先冻结新字段合同，再实施 SMARTS 与确定性锚，最后消费负证据；不是要求本轮设计审先改源码。

1. **required FG 来源与 unknown。**现有[conditions helper](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/candidate_evidence.py:215)直读 spec.requirements；[Requirement定义](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:438)是环境/供给条件，不能直接当必需 FG。冻结来源、支持词表与许可范围；来源缺失、词表外、解析/映射失败都 unknown，不能当 requirement_missing。不要求机制库；当前无权威来源时可暂缓负证据，只呈现可复算局部事实，且不新增候选硬筛。
2. **delta 与编辑落点 scope。**明确比较指定主产物、所有产物还是已知系数净反应；[编译器主产物选择](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_compiler.py:1107)不等于完整产物集。部分参与物/未知系数时仅给限定图级差值或 unknown，不扩称配平/机制/氧化态证明。FG得失是类集合还是命中数变化、跨类重叠怎样处理，也须固定。
3. **最低确定性锚。**设计应列：中性/带电对；无变化/单得失/多命中/重叠；主副产物与次序置换；部分表/未知系数；新增原子/不可映射；解析失败与真实零命中区分；双跑一致及输入只读。编辑落点必须用完整内部匹配，不能用[仅前8条的渲染数组](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/candidate_evidence.py:319)。这些是后续实施验收锚，不要求本轮提前认证全化学表示或真实收益。

## Q5 决策归属：不通过设计冻结（P1-A，同组不重计）

source 处置应由**设计轮**在冻结前落字，再交实施单执行、评审链核对。设计者可先选择一个待证假设，不必等付费 A/B 找最优；评审也不替 CC 拍科学方向。当前47行“交实施单+评审链定”与“设计轮第一决策”同时存在，尚未完成本次冻结前置。补齐 P1-A 的方案与可见面表即可，不另加审批链。

## 收口清单

| 编号 | 回修后复核边界 |
|---|---|
| P1-A | 一个明确 source 方案／或分别编号的实验；B完整可见面表；A兼容与共享prompt关系；因果表述有限。 |
| P1-B | participants保真/格式；requiredFG来源与unknown；delta/落点scope；有限确定性锚；三类版本承载。 |
| P1-C | 必备测量参数与未填不发车；覆盖停点优先或事前显式变更；四象限；novel行为指标及冲突顺序。 |

回修只需修订设计合同和其冻结清单，不要求新增科学显著性门、真实模型验证或本轮代码实施。本轮不认证 v2 收益，也不重开已放行的 T-F 修复。

**总体裁定：回修（设计冻结暂不放行；按 P1-A/B/C 补齐后同范围复审）。**
