# COSUB24 可救性裁定：工程与来源数据面（2026-10-14）

**工程总裁定：存在可救的正路，优先 R1 参考侧补全；来源数据和合成比较链都支持这条路。不能据此判定 24 题全部可救，也不能把 12 个同 cn 身份碰撞直接算作收益。** R1 需要新的参考口径确认、预注册及新评测批；R2/R3 必须回 teacher/师姐重裁。R4 与 R1 互补，单独的声明链不能让机制 extras 在当前参考下获豁免。

这纠正了“24 题保持 partial＝在冻结合同下永远救不了”的读法：**现参考输入不变时不能靠豁免救；经裁定补齐来源支持的参考信息后，可以沿现有逐侧比较规则正面核验。** 本报告不推翻 teacher b 档，也不裁定机制共底物该不该豁免。

## 对象、输入和证据边界

本次承接 [裁决请求](/Volumes/CC/Enzyme_Agent/dependingv43/docs/ADJUDICATION_REQUEST_COSUB24_RESCUE_2026-10-14.md)，按 Q1–Q6 回答。对象标签为 **298 / RHEA 通用酶学 / 已见题 / chain12 事后诊断**。请求所述 24 题、12 个同 cn 碰撞、298 张真实参考图等，是输入文档的聚合声明，本轮没有读取真实题面/金标/逐题结果来重核这些分母。

用户已明确补充：**“没有，先按允许的现有资料裁定”**，指没有安全的“24 题→来源记录”关联索引。因此 Q6 为**未核定，不是 0**。依据见 [用户补充记录](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/user_clarification.json)。

| 路径 | 工程裁定 | 当前合同下如何推进 | 不能承诺 |
|---|---|---|---|
| R1 来源参考补全 | **可行，优先**；不靠豁免，补齐两侧后可以真实匹配 | 先统一来源/构图范围，teacher+用户确认，满足化学专业确认边界，冻结新参考输入和新批；执行豁免退出 | 24 全救、只补一个字段即上线、总 hit 必然增加 |
| R2 身份不计侧/净零抵消 | **口径级，必须回裁** | 定义新数学语义、净零证据范围和反例矩阵，走新版本 | 同 cn 在产物侧出现＝反应物已覆盖；12 题直接受益 |
| R3 机制身份扩豁免 | **触碰 b 档明示禁区，必须逐项重裁** | 逐身份/方向/角色提交化学证据与新挡板合同，工程侧不自决 | 常量扩展加原三谓词就足够；OTHER 全族放行 |
| R4 C 供给+声明链 | **与 R1 互补**；当前实施件未在本轮验收 | 在原授权 C 线范围完成供给/声明及工程复审，用新批与 R1 组合验证 | 回填旧事件/成绩；单靠 resolved 声明链消除机制 partial |

本轮源码比较基线为 `7e7855cb3ead11c7153f57b8e47a5b018f9e4ba3`。工作仓已有他人进行中的 C 线和 appearance 修复，未提交源码只用于接口快照，不当作已验收交付。下文源码链接指向**固定 HEAD 的永久副本**，避免在途改动使行号漂移；输入与哈希见 [inputs.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/inputs.json)、[reviewed_source_manifest.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/reviewed_source_manifest.json)。

## Q1【工程/数据】：R1 的来源存在性与工程可行性

### 来源确实保留了两侧数据，但尚未关联到目标 24 题

独立读取的是来源资产 `assets/v3_reactions/corpus_env/corpus_v1.jsonl` 及来源/模板元数据，不是题卷或参考答案。来源版本声明为 dependingv3 v3.5 frozen assets（2026-09-18），source commit=`eb24c1e50a94966c77fd108152d4ebff2d65032e`。来源文件哈希与两份资产 manifest 对得上，读取前后未变；来源解析代码也与登记的冻结 commit 字节一致。没有重新生成资产或认证源数据库化学完整性。

以下分母是**来源全库，绝非 COSUB24 覆盖数或成绩**：

| 来源全库核验项 | 本轮独立结果 | 对 R1 的意义 |
|---|---:|---|
| corpus 总行数 | 43,177：RHEA 37,100，enviPath 6,077 | 真实来源资产存在；来源域分开 |
| RHEA 非空 reaction_smiles，双侧可解析 | 37,098 / 37,100 | 可以提取记录声明的两侧结构 |
| 方程两侧与 donor_A/product_B 组分多重集一致 | 37,098 | 方程与适配结构字段方向一致；按探针规范化结构键核对 |
| RHEA 多组分反应物行 | 33,718 | 来源未只保留单个主底物 |
| LR/RL master 配对 | 18,550；其中 18,549 对双侧可解析且精确反转 | 方向可追溯；另 1 对缺结构；行数不是独立反应数 |
| RHEA 泛化 `*` 组分行 | 8,502 | 可解析不等于具体严格结构可得 |
| RHEA 同侧重复结构 / 两侧有相同结构行 | 5,688 / 3,420 | 保留多重集与侧别，不默认系数 1，不自动抵消 |
| 专用 roles/coefficients/record_equation 字段、原生 atom mapping | 专用字段不存在；全 corpus mapping absent/null | 需适配声明合同；不宣称角色、系数或机制已核 |

enviPath 与 RHEA不能混为一个方程可得性结论：enviPath 的 6,077 行 reaction_smiles 全空，其中 5,497 行 donor/product 两侧结构可解析，另 580 行缺失或不可解析。

另发现 corpus 有 303 个重复 record_id 组、531 个额外重复行。后续关联应使用**来源文件 SHA+行号+record_id+方向/master_id**，不能仅凭 record_id 或任选 master 的一个方向。

证据：[source_schema_aggregate.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/data/source_schema_aggregate.json)、[source_equation_aggregate.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/data/source_equation_aggregate.json)、[asset_identity.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/data/asset_identity.json)、[来源代码与执行说明](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/data/notes.md)。证据只保存聚合、代码和文件身份，没有复制真实方程或题目名单。

### 工程路径已由合成比较链证明

现 [参考构建器:179](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/reviewed_head/src/pathway_v43/pollutant/s5b_builder.py:179) 只消费 qid、substrate_smiles、products_smiles，构建 root 与 principal products，不消费完整来源方程。它也没有保存题目→corpus 行的关联。**root-only 是当前构图政策的限制，不是来源语料必然缺少共底物。**

现 [参考 schema](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/reviewed_head/src/pathway_v43/pollutant/reference_graph.py:50) 能表示额外结构节点、两侧端点和参与物。固定 [比较器:1589](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/reviewed_head/src/pathway_v43/pollutant/evaluation.py:1589) 本来就是两侧集合比较。合成事件 `S+B→P+C` 在 root-only 参考 `S→P` 下为 superset partial；同一事件对完整两侧参考变为 participant exact、matched_strict，**无需机制身份豁免**。

反控也执行了：只增加 participants 元数据、不扩 from/to，仍 partial；参考补齐 C 而生成缺 C，必要节点未覆盖；C 只在错误一侧出现，维持 partial_subset；严格身份权限不足/立体不合不能因 cn 或文本近似升 strict；参与物 exact 但 step_scope 不合，只有 matched_structure_only。因此 **“来源带某个共底物”不是“全部 extras 与参考都对上”，更不是“24 全救”。**

R1 需要来源关联适配器，将原记录两侧全声明同步装入 nodes、from_node_ids、to_node_ids、participants、distinct occurrences、provenance、覆盖/unknown 和 scope，再生成新图哈希与 manifest。模板主变换 `S→P`、声明式 copy components 和完整来源方程 `S+B→P+C` 是三种数据，不能互相代替。

### 两处必须写入 R1 设计的接口限定

- **排名主底物锚。** [s5b_scoring.py:618](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/reviewed_head/src/pathway_v43/pollutant/s5b_scoring.py:618) 目前把全部 from_node_ids 当作“root states”，再按任一反应物相交选排名候选。新增共底物 B 后，一个较早的 B-only 事件也被纳入；合成正匹配事件排名变为 2，而只按主 root 的候选域只有 1 个事件。R1 要明确保留主底物排名域，或对有意改变的排名语义另行登记，不能把参考补全称为指标接线完全无变化。
- **exact 的证明范围。** 现比较是严格状态的逐侧**集合**与 step_scope，不独立核角色相等、系数或重复份数。合成改 role、重复同 state 条目仍可 matched_strict。这是已有程序口径的范围，不是本轮要求追加机制门；R1 不应把此 strict 宣传为角色/计量/机制完整证明。

详细源码、19 个合成分支及输出：[engineering/notes.md](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/engineering/notes.md)、[probe.py](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/engineering/probe.py)、[root_engineering_summary.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/root_engineering_summary.json)。这不是完整 S4 原生链/C 实施件验收，也没有真实 hit 成绩。

## Q2【合同/工程】：R1 的版本、新批、退出与裁定义务

**不是只知会 teacher。** [共底物设计书:270](/Volumes/CC/Enzyme_Agent/dependingv43/docs/S5B_COSUBSTRATE_PARTICIPANT_SEMANTICS_DESIGN_2026-10-10.md:270) 明确参考侧/金标侧变更“须 teacher + 用户裁定”；T-5 仍是参考侧立项项。b 档支持把机制信息补进参考的方向，不等于已授权本次构建/改金标。冻结批复的 [权责边界:8](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TEACHER_REPLY_PPV1_T1_FREEZE_APPROVAL_2026-10-13.md:8) 又把化学实质留给师姐确认。本工程裁定不代替该确认，也不认定已有其他化学确认是否完成。

| 约束 | R1 所需动作及依据 |
|---|---|
| 来源先于结果 | 统一登记来源/适用范围、方向、身份权限、遗漏与未知；禁止按这24题预测 extras 反填金标。S5 任务书 [参考权威规则:307](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md:307) |
| 参考口径人工确认 | 确认可评分节点/边、共同产物、角色、step scope、覆盖缺口与 strict/CN 范围，符合已有 teacher/师姐边界。S5 [正式裁定项:693](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md:693) |
| 内容版本与 schema 分开 | 新来源构图政策、内容身份、参考图哈希与清单必须登记。现 shape 可容纳额外端点；若新增正式角色/字段或 schema 常量，则实现相应版本迁移，未知字段/版本当前拒绝。S5 [预注册字段:731](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md:731)；固定参考校验器 [:192](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/reviewed_head/src/pathway_v43/pollutant/reference_graph.py:192) |
| 新批与绑定 | 新评测批根、图/题/导出配对、新 manifest/hash；旧参考、run、已判文件不覆盖。合成旧 hash、错 qid 对照均被既有守卫拒绝 |
| 豁免退出 | v2 [§九:86](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md:86)：“参考侧 omitted_coproduct_scope … 落地即废止本豁免”。新参考发布须明确停用/废止与适用 scope；分批补全时的退出范围须裁定，不能自发逐题开关 |
| 隔离参考效应与供给效应 | 建议登记“同一冻结导出×旧/新参考”及“同一新参考×旧/新供给”的对照。旧导出只读敏感性须另按真实材料授权；报告升档、降档、未核和位次变化，不能只报救活数 |
| 科学读法 | 新根/换参考不恢复盲性；298仍是已见来源重建域，标 post-hoc。正式科学放行仍按 S5 [参考冻结与评审条件:820](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md:820)，本轮只下工程裁定 |

**退出信号不是自动熔断。** 固定 [evaluation.py:3238](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/reviewed_head/src/pathway_v43/pollutant/evaluation.py:3238) 只统计参考节点中的四类豁免身份，随后披露 signal；没有在匹配前关豁免。合成水参考触发 `EXIT_CONDITION_SIGNAL_nonzero` 时，H⁺ 仍获豁免 strict，`exemption_enabled=true`、`events_exempted_strict=1`。只补 O₂/NH₃ 还可能根本不触发四族统计，故 signal=ok 也不证明未触合同退出。

新 R1 参考可明确使用豁免关闭的 v1，或在经批准的新合同下实现拒绝/关闭门；**不能仅留下退出字样继续照跑 v2。** 具体退出 scope、适用口径与冻结状态由 teacher/用户确认，不由本报告替其决定。合同逐条索引见 [contract/notes.md](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/contract/notes.md)。

## Q3【口径】：R2 必须回裁，12 个碰撞不能直接兑现

现规则按两侧分别构集合，要求 reactants=from_states 且 products=to_states；v2 extras 和声明检查又绑定身份、侧与可用角色。[v2 预注册:34](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md:34)、[:46](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md:46)。将它改成无侧身份并集或净参与物，是**改变所测主张**，不是等价工程修正。

合成 `S→P` 与 `S+P→P` 的联合身份集合相同，现逐侧比较却明确有一个额外反应物。程序已证不计侧会改变判定；该对照不评价哪种化学口径应被采纳。

具体回裁清单：

1. 比较双侧完整参与物、联合身份还是净方程？适用 net/elementary/multistep 的范围是什么？
2. 净零需要严格身份还是 cn；已知且相等的系数、方向、角色、distinct occurrence 有何最低证据？系数 unknown 怎么保持 unknown？
3. spectator、机制参与后再生与错误附挂如何区分？即便真实净零，是否允许不计入仍属 teacher/师姐裁定。
4. 如何保留两侧错位、不等份数、cn同值但严格范围有限、缺声明/缺系数、乱挂机制身份等负控？
5. 与 b 档硬拒绝、方向限定清单、退出条件如何相容？采用新版本/新批、双口径/post-hoc，旧批不回写。

请求中“12 个缺失共底物 cn 与参考产物相同”仅说明身份碰撞，不证明等系数消耗再生、净零、严格身份或正确角色；本轮未重核该12子集，也不把它写成12题收益。回裁依据含 [C 设计精确多重集/spectator/声明边界:68](/Volumes/CC/Enzyme_Agent/dependingv43/docs/C_COSUB_SUPPLY_DESIGN_PREREG_2026-10-14.md:68)。

## Q4【口径/工程】：R3 的重裁门槛与新证据

[teacher b 档:24](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TEACHER_DECISION_PPV1_T1_COSUBSTRATE_TIER_2026-10-12.md:24) 明排 O₂/NH₃/H₂O₂ 等机制身份，并要求任何增补为清单新版本+老师逐项裁定。工程面无权改这个结果；化学实质遵守师姐确认边界。

“常量扩展+原三谓词照跑”不足以构成安全交付：同时触碰硬拒绝表、逐侧许可、零碳/身份不交断言、追溯账适用范围和完整二分。原 P/O 账不自动成为 N/H/电子或键级机制验证器；pred1 同源记录声明也不是独立化学认可。

| 重裁对象 | 需要的新证据类别 |
|---|---|
| 每个具体结构身份/方向/角色/step scope | 来源记录与已知结构、条件、角色范围；不能按 OTHER 或“24题”整袋申请 |
| 三谓词与追溯账是否适用 | 新身份的适用性、unknown/失败边界和机制错收反例，化学专业确认；工程不自行定义新化学规则 |
| 冻结挡板如何改 | 硬拒绝/零碳/completion license 不交/侧别/完备二分与声明缺失正负控；涉及CO₂/HCO₃⁻还须满足冻结批复的冲突消解条款 |
| 为何需要免验而非 R1 正面核验 | 来源参考补全可得性与剩余未核范围的安全聚合证据；参考足以核验时按退出合同比较 |
| 生效与审计 | 新 criteria 版本、判据级化学评审与程序互证、teacher/用户确认、新批双口径/post-hoc，旧批不回写 |

本次只列条款和证明需求，不实施扩档，也不声称 O₂/NH₃ 化学上应该/不应该在未来版本豁免。

## Q5【工程】：优先序与 R4 对照

**优先 R1 的安全来源关联与统一构图立项，同时继续原授权 R4 工程；R2、R3分别留回裁。**

R1 修的是参考信息缺失，最符合 b 档“机制信息进参考”的正路；R4 修的是生成方供给/声明。两者在新批中相合才可能形成真实两侧 exact，不互相认证机制正确。完整参考也会让省略必要参与物的旧简写 strict 降为 subset/uncovered，必须报告净效应。

独立合成 R4 对照已把 event→hypothesis→provenance→record_equation 声明链置为 resolved；NH₃/O₂ extras 仍为 partial，因为身份不在豁免清单，pred3=false。**声明链不是改变参考范围的钥匙。**

对当前冻结存量，R4 不回填已提交事件、不覆盖已判文件，因此不会直接改变旧批成绩；这不是“C 对未来新批总体收益为零”的性能结论。已有完整事件若日后与经授权的新参考作新根只读敏感性比较，R1 理论上无需先把旧事件补声明，因为参与物 exact 不走豁免 pred1；实际是否相合仍需安全来源关联和正式授权，当前未执行。

C 线在途源码只做接口读码：声明方程与 provenance 发射位置记录在 [engineering notes](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/engineering/notes.md)，未认证其运行交付或真实成绩。C 探针35题供给面也不能替代本24题集合。

## Q6【数据】：24题覆盖数未核定

**当前答案：未核定。不能给 0、24、12 或任何范围内题数，也不能用来源全库 37,098 条推该子集比例。**

允许输入没有“这24个匿名成员→来源 corpus 行”的索引。构建器把 qid 用作来源引用/变换引用，没有保留对应 record_id/line/master/direction；真实 batch manifest 还含题面字段，本轮没有读取它。用户确认无安全索引后，本轮按该边界收口，未绕入 questions、金标图或逐题结果来反建。

若后续要核定，可由获授权的数据侧提供不含题面、结构取值、预测或分数的索引：匿名成员键、来源文件 SHA、行号、record_id、master_id/方向、fingerprint、关联唯一性/歧义及生成 provenance；主底物定位可用来源组件 ordinal。之后按完整两侧与身份权限统计“已关联、结构缺失/泛化、方向歧义、覆盖可核、仍未核”，只输出聚合。该索引本轮未取得，报告不将缺口写成来源无数据。

## 独立执行与交付纪律

三分支分别核合同、来源数据、工程。来源聚合实际执行并核资产身份；工程19个合成分支在新 `/tmp` 副本、无字节码/缓存环境执行，exit 0、stderr空；合同仅读规则与固定源码。未跑真实科学判分或真实24题重算，没有外部模型/网络。

初次脚本问题已如实记录：schema聚合 Counter 使用错误、含 dative bond 的反应串分隔误判，以及工程初次系统临时目录路径；采信修正后明确 `>>` 解析及显式 `/tmp` 重跑结果，未把搭建失败或首版分类当成真实缺数据。各分支命令、exit和限度见 [data/execution.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/data/execution.json)、[engineering/probe.command.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/engineering/probe.command.json)、[contract/execution.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/cosub24_adjudication_2026-10-14/contract/execution.json)。

只新增本裁定报告与本证据目录；没有修改 src/tests/既有 docs/AGENTS.md，没有访问真实金标、题面、逐题metrics/gitignored reports逐题数据或封存run；未commit/push。在途工作树与固定评审输入的差异登记于本证据目录 `final_integrity_check.json`，全证据/报告 SHA256 见 `SHA256SUMS.json`。

收尾时发现工作树继续变化，新增了 C/P1FIX2 交付与测试改动，因此没有声称整个工作树与开始时全等。本轮登记的规则文档未变，固定 HEAD 源码副本逐字节核对通过；这些后续变化不纳入本裁定，也不被本报告宣布验收。
