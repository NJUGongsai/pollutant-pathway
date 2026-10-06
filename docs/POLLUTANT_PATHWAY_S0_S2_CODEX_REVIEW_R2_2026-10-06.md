# pollutant_pathway_v1 S0–S2 第二轮独立复审

- 审核日期：2026-10-06（Asia/Shanghai）。
- 审核仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。
- 审核 HEAD：`0002f71af23a2d00db7734e15bf1142c64c85145`。
- 对象：`mimo_ppv1_chem_review_response_r2.md`、`POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_2026-10-05.md`，以及其对应实现、测试和原实施书。
- 裁定：**本轮有实质修复，但 S0–S2 尚未验收通过；不放行 S3，不冻结新化学判据。交付书“F01–F11 全部修复”的结论需要撤回，改成逐项、分范围的事实说明。**

## 1. 审核依据与证据范围

审核以原实施书正文及第 17 节、首轮 Codex 复审为约束。mimo 回应是独立意见，只有得到程序证据支持的部分才采纳。

三个专项分别复核化学、条件与依赖、存储与兼容边界；主审核复跑其合成探针，并补做 admission 和有效断键对照。所有复现使用合成分子、合成条件、临时合成 SQLite；没有读取 gold、封存逐题 runs，也没有运行模型或真实路径预测实验。审核没有修改实现和被审文档；本报告及复现附件是新增审核材料。

独立复跑四个 ppv1 测试文件：**129 passed，1 skipped**。条件专项回归：**28 passed，48 deselected**，是前述测试集合的子集，不能相加。交付书的“740 passed，1 skipped，16 deselected”是实施方记录，本轮未独立复跑全部通用测试。

129 项通过证明旧反例的一部分已经修复，不证明底座契约的全部边界正确。下面的残余均有源码位置和新增反例，不能用测试数量抵销。

附件目录：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r2_2026-10-06/`。其中保留 38 条化学输出、条件探针结果、17 条存储输出、admission 补充输出、测试日志和断键对照；复跑方式见附件 README。附件中的临时路径只是合成夹具位置。

这里的 **P1** 指进入 S3 前必须修复的底座问题，**不表示这些问题已经影响线上 legacy 执行流**。ppv1 入口仍 fail-closed，保持这一阶段边界是正确行为。

## 2. 首轮 F01–F11 的实际关闭状态

| 原编号 | 本轮确实修好的部分 | 本轮裁定 |
|---|---|---|
| F01 | 全氢计数、显式氢正反例、错误配平正例纠正、歧义参与物阻止 full、元素差值与 unknown 分码 | 原主缺陷已关闭；同位素/自由基/电子核算覆盖另行说明 |
| F02 | 固定场景下同键要求合取，父冲突不再被新增要求覆盖 | 固定场景反例已修；跨阶段仍未关闭，见 R2-04 |
| F03 | 来源场景/事实阶段过滤、匹配物种 absent、无源 essential、optimum/不明点值的主要反例 | 部分修复；区间、单位、物种缺席与覆盖仍有缺口，见 R2-05、P2 |
| F04 | 同图、相同 fidelity、不同来源可保留多个 appearance；普通两步导入成功 | 部分修复；不同来源 fidelity 冲突和出现记录覆盖仍在，见 R2-08 |
| F05 | 初始 plain/AND/OR 碰撞消除；CN-only 专用工厂及未知轴正确 | 部分修复；公开结构丢增强立体、等价表示分裂，见 R2-02 |
| F06 | context_id 纳入 scope/依赖等字段，三元及更长供给环可检测 | 部分修复；启动证据混淆、分支可变对象共享，见 R2-04、R2-06 |
| F07 | 正常 helper 构造的缺状态回滚、锚点/互斥检查、缺报告投影重放报损坏 | 部分修复；真实提交入口与完整重放未闭合，见 R2-09 |
| F08 | 未知数据库 schema 在 DDL 前拒绝；显式未知 run identity 和部分 from_dict 版本门有效 | 部分修复；writer 接受未知对象版本，见 R2-10 |
| F09 | 正常子路径缺存档时降为 CN-only，旧库只读 | 部分修复；损坏来源指针仍能冒充根，见 R2-11 |
| F10 | 无标识 rule 不升格、组合 retrieval 分类修正、完整 study_map 归并、model_ref 和来源记录持久保存 | 主要旧反例已修；部分研究映射计数和新旧引用解析见 P2 |
| F11 | 消费真实编辑协议、普通键级变化 diff、部分映射 unknown、明显非等价类拒用 | 部分修复；零净变化、联合中心对称与实际变化覆盖未闭合，见 R2-03 |

## 3. 阻塞 S3 的问题与最小验收要求

### R2-01 [P1] “全部核实”不检查覆盖；自报签名可以授予 verified；缺状态审计还会崩溃

位置：`src/pathway_v43/pollutant/audit.py:255`、`:414`、`:438`、`:475`、`:782`；`hypothesis.py:436`。

配平夹具 `CCO + O=O → CC(=O)O + O`：

- 不传 context，条件项是 `not_applicable/no_context`，admission 却返回 `expand/R6:all_verified_no_conflict`。
- 仅请求 `audit_scope={structure_parse_valence}`，只产生一条 parse=verified，也返回同一 R6；完整度、计量、中心、条件、依赖均未被检查。
- 给出匹配有氧条件，但 `transformation_ref=''`、没有 checker 证据，仅设置 `transformation_signature_status='verified'`，中心即 verified，仍能进入 R6。
- 合法 `CCO→CC=O` 假设只提供乙醇 state，默认审计先记录 `participant_state_missing`，随后读取 None 的 fidelity 抛 `AttributeError`。complete 和 partial 均可触发；parse-only 绕开崩溃后，又将缺引用称为 `R1:structure_unparseable`。

这不是预测精度问题，而是“已核实”标签没有可靠生成条件。缺少输入应 unknown/not_run；窄 scope 可用于诊断，但不能满足 admission 的必需检查覆盖。verified 中心须有版本化确定性检查和可追溯证据，不能把模型/调用方字符串当作检查结果。

**验收：**上述四类输入都不得进入 R6；缺状态返回结构化契约/账本问题，受影响后续项不执行，不能以普通 AttributeError 中断。R1 限实际结构语法/价态问题。真正语义不适用的项仍可 NA，例如关闭的有限规则诊断；不要求所有诊断无例外都 verified。unknown 继续允许按显式策略保留/有界探索，不自动变 reject。

证据：`chemistry_probe.output.jsonl` 中 `admission_*`、`missing_state_*`；`admission_probe.json`。

### R2-02 [P1] 严格身份与公开结构不一致，增强立体事实既会丢失又会错误分裂

位置：`chemstate.py:104`、`:117`、`:127`、`:269`；`substrate_profile.py:118`；`audit.py:1058`。

`F[C@H](Cl)Br |&1:1|` 与 `|o1:1|` 有不同 state_id，但 `smiles_isomeric` 和 profile 的 `structure_smiles` 都输出 plain `F[C@H](Cl)Br`；重建全部变成 plain 身份，fidelity.stereo 仍写 as_written。原串保存在另一个字段，不能补救已交给下游的“完整结构”字段丢事实。

同时，`C[C@H](O)CC |&1:1|` 与 `C[C@@H](O)CC |&1:1|` 当前得到不同 ID，strict_target_match=False；OR 和双中心整组反转也同样分裂。本地 RDKit 规范化与 RegistrationHash 对照均相等；只反转双中心组内一个中心的控制例仍不等。这是表示差异归一要求，不是任意合并立体异构体。RDKit 官方文档也直接给出单中心 AND 这一等价例：[RegistrationHash](https://www.rdkit.org/docs/source/rdkit.Chem.RegistrationHash.html)。增强组的语义与规范化见 [RDKit Book](https://www.rdkit.org/docs/RDKit_Book.html#support-for-enhanced-stereochemistry)。

**验收：**身份、供体 strict、profile 结构输出使用同一套规范化事实；完整公开表示可重解析并重建同一身份。plain/ABS 冗余、AND/OR 整组反转、原子排列应正确处理；不同组类型和不同相对立体关系不得误合并。不支持的表达须明确 unknown/unsupported，不能剥掉事实后仍说 full/as_written。不得直接用可能合并互变体等状态的通用 hash 替换本项目严格身份而不审查其层与语义。

证据：`f05_enhanced_stereo_export_roundtrip`、`f05_whole_enhanced_group_inversion_split`、`f05_relative_stereo_control`。

### R2-03 [P1] 供体诊断仍把声明当执行；逐原子对称轨道被误用为联合中心等价

位置：`audit.py:875`、`:885`、`:956`、`:1080`、`:1110`、`:1114`、`:1142`。

真实 `validate_edits` 和 `execute_edits` 可成功执行乙醇 C–O 单→单，以及单→双→单。两者产物都仍是 CCO，`executed_bond_changes=[]`，诊断却中心 True/direct、缺信息为空。原因是实际变化集仍并入 `_edit_atom_ids(edits)`：声明触及某原子就足以命中。

联合对称反例也使用真实执行器：环己烷供体中心映到相邻碳 `{0,1}`，实际在 `{0,3}` 成键，执行成功；六个碳各自同轨道后，诊断给 symmetric_equivalent=True。独立枚举自同构证明不存在把这两个中心集合同时映射的单一变换；邻接距离本就不同。各原子分别可替换不等于整个中心存在一个一致替换。

此外，公开结果接口对电荷/H/立体单独变化没有实际 delta；声明与执行、plain 产物与 mapped graph 的一致性未核对。后几项使用接口合成不一致输出，不宣称旧四操作编辑器能直接产生独立电荷/立体操作。`extra_changes` 目前仅列产物元素/电荷及 present，不是 before/after 差值。

**验收：**中心判定仅使用真实净变化；零净变化不能 True；声明与执行、两种产物表示必须对账。变化类型分轴，未支持的类型明确未知。symmetric_equivalent 须存在对整个相关中心/变化一致的图映射；只有单原子候选轨道时不能授予这一结论。

完整供体反应模板的变化比较可以按阶段方案在 S3 接线，但 **S2 当前的区域诊断必须命名准确、覆盖诚实，不能用区域包含关系冒充变换一致**。本项不要求提前改写 frozen legacy 编辑协议或实现所有变化类型。

证据：`f11_real_executor_zero_net_change`、`f11_independent_orbits_not_joint_symmetry`、`f11_declared_change_executed_unchanged`、`f11_nonbond_actual_change_invisible`、`f11_plain_product_mapped_product_disagree`。

### R2-04 [P1] 条件要求没有所属边/阶段；转换能错杀合法路线或洗掉历史冲突；分支仍共享可变对象

位置：`path_context.py:248`、`:851`、`:874`。

事实有 phase，Requirement 没有所属 phase/scenario/edge。derive_child 累积全部要求，却用新阶段事实重评它们。

- p0 有氧事实+有氧要求相容，显式转 p1 无氧并新增无氧要求：child 变 conflicted，因为旧有氧要求被拿到新阶段比较。
- p0 有氧事实+无氧要求已经冲突，显式转 p1 无氧：child 变 condition_compatible。parent 对象仍 conflicted，问题是派生路线结论丢掉旧边冲突，不能描述成 parent 被改写。
- 两个 children 共享 parent 的 Requirement 对象；把 A 的温度要求字典从 20–30 改成 40–50，会改变 parent 和 B 的结果，parent.context_id 却不变。

**验收：**每边要求和评估绑定原阶段/场景，保留历史快照，路线按选定边聚合；当前步骤相容与全路线相容分开。转换只影响后续。要求/事实/依赖的嵌套科学前提采用不可变对象或完整隔离，兄弟修改不能改变父和其他分支。固定场景 F02 的旧正反例继续通过。

证据：`phase_transition_false_conflict`、`phase_transition_erases_past_conflict`、`requirement_branch_alias`。

### R2-05 [P1] 数值、单位和实体作用域不足以支撑条件冲突/相容判断

位置：`path_context.py:187`、`:335`、`:395`、`:420`、`:432`。

| 输入 | 当前结果 | 正确边界 |
|---|---|---|
| pH 事实 [6.8,7.2]；有来源必需点 7 | conflict | unknown，不能证明当前点恰为 7，也不能证明不可能为 7 |
| pH 事实 [7,7]；必需点 7 | conflict | satisfied |
| temperature_C=25，unit=K；要求 20–30°C | compatible | 拒绝矛盾单位、规范化后比较，或 unsupported/unknown；不能按 25°C 算 |
| acetate known_absent；必要供体 NADH | conflict | NADH 状态未知；缺一种供体不能证明另一种缺席 |

现有字符串不相等也直接判冲突；对互斥的氧制度枚举可以成立，对可共存的物种/供体不成立。必须区分实体缺席、整个维度已穷尽的库存和普通开放事实集合。

**验收：**补齐区间×点双向及退化区间语义，校验单位/维度并明确转换范围；实体身份先匹配再判断 absent，多种已知供体可并存。无需新增全部环境维度或所有单位，未支持的输入保持明确未知/契约错误。不能为让测试通过而将所有字符串一律 unknown；可验证氧枚举和已识别实体仍应正常比较。

证据：`point_interval_*`、`temperature_kelvin_compared_as_celsius`、`unrelated_donor_absence`、`multiple_present_donors`。

### R2-06 [P1] 再生关系的支持被当成初始供给已解决

位置：`path_context.py:637`、`:680`。

A→B→C→A 三条再生关系都有来源支持，解析轨迹明确只有再生证据、没有初始池；诊断仍返回 `unresolved_initial_supply=[]`。当前实现只看环上所有 dependency.status 是否 supported，没有区分支持的是再生关系还是初始供给。

三元环检出确已修复；这不证明启动条件已知。原规格“有启动/再生支持时不得自动阻断”也不授权把初始供给未知删除。再生支持可影响保留/探索策略，同时仍披露启动未知。

**验收：**分别表达反应/再生支持与启动供给状态；明确新证据能解决哪一依赖。仅再生有证据时保留初始供给 unknown；补足可追溯的启动供给证据后才能解决该未知。不得因循环自动 reject 或宣称化学不可能。修正现有“全部边 supported→启动未知为空”的过强正例。

证据：`regeneration_only_cycle_loses_startup_unknown`、`three_node_unresolved_control`。

### R2-07 [P1] 不同科学前提共用 hypothesis_id，审计 input_hash 也不代表真实输入

位置：`hypothesis.py:424`；`audit.py:538`；`store.py:276`。

同父路径、结构、来源键的三条假设，分别要求有氧、无氧、有氧+未解决依赖，全部得到 `hyp_25890824e08f297c5809`。同一有氧 context 内前两条 admission 分别 expand/defer，但 audit.input_hash 相同。第二条 put_hypothesis 抛幂等键冲突，无法同时落账。

身份哈希遗漏 requirements/dependency_refs 等影响假设语义的字段；input_hash 仅由 hypothesis_id 生成，不能标识实际参与状态、条件、依赖解析及 checker 输入。

**验收：**区分不同条件/依赖前提的假设变体，或采用明确稳定主体+不可变版本关系。影响判定的前提不能静默覆盖/合并；相同语义重放仍幂等。审计输入哈希须覆盖实际科学输入及适用版本，不把一个引用 ID 当完整输入证明。加入同反应不同条件、不同依赖、不同解析上下文可共存与重放测试。

证据：`hypothesis_condition_dependency_identity_collision`。

### R2-08 [P1] 结构状态与来源出现拆分不彻底；导入阶段仍先覆盖记录

位置：`store.py:98`、`:216`；`legacy_reader.py:202`、`:259`。

同图 CCO 的 raw_input/full fidelity 与 OCC 的 archive fidelity 有同一 state_id，却因 `representation_fidelity` 仍属于不可变 semantic payload 被判冲突。合成旧路径 `CCO→CC=O→CCO` 第二步导入失败，只留下一个事件；旧库字节未变。

另一个同事件产物 position 0=`CC=O`、position 1=`O=CC`，导入先按 state_id 建字典，只保留 position 1 的原串/来源；appearance 表无法恢复此前已覆盖的 position 0。

**验收：**严格分子事实可复用，每次来源出现的原串、位置、信息可知性单独保存。相同图不同来源 fidelity 不应冲突，也不能将某来源的未知自动升级为另一来源的完整。导入保留全部 occurrence 后再去重分子身份；root 再出现、同事件同图不同位置、同图多来源保真度均正常导入并可追溯。

证据：`same_structure_source_fidelity`、`legacy_cycle_import`、`legacy_same_structure_two_positions`。

### R2-09 [P1] 真实提交入口没有落实完整参照校验；重放仍能对损坏账本报成功

位置：`store.py:378`、`:419`、`:437`、`:468`。

以下公共 API 输入都成功 `created=True`：

1. event.participants 仍包含乙醛，但将独立 participant_state_refs 改为仅乙醇，随事务只给乙醇状态；产物 state 实际不存在。
2. 同 ID hypothesis_dict 改成其他 parent、错误底物锚点、participants=[]；事件与假设仍被保存。已有 hypothesis 时，随事务提交的同 ID 不同内容也被忽略。
3. report_projection 指向不存在的非产物，expansion_plan 同一产物同时 expanded/deferred，并另含悬空引用；全部落账。

合法提交后分别删 states、hypotheses、state_appearances，再原参数重放：都 `created=False`，既不报损坏也不恢复。新重放检查只覆盖 report_projections/expansion_plans。

**验收：**以真实参与物为准派生引用；校验实际 state 身份、底物锚点、事件/假设内容关系、投影与计划产物范围和状态互斥。不能只要求调用者先经过正确 helper。首次提交或重放任一违约均有结构化结果；首次失败零写入回滚，重放核验所有必要记录，选择明确的报损坏或版本化修复策略，不能默默成功。

证据：`event_refs_omit_real_product`、`event_hypothesis_mismatch`、`existing_hypothesis_payload_ignored`、`commit_invalid_projection_and_expansion`、`replay_missing_*`。

### R2-10 [P1] 对象 schema 版本门没有接入 writer，事件版本号持久化时丢失

位置：`store.py:399`、`:448`、`:462`。

submit_event 同时收到 `future-chemstate-999`、`future-hypothesis-999`、`future-event-999`，仍 `created=True`。前两种未知版本可读出；event 持久 payload 根本不保存 schema_version。

**验收：**所有公开写入/重建边界校验显式未知对象版本，并保留足以重建、核验原对象的版本信息；拒绝前不写账。适用对象包括 state、hypothesis、event、投影与计划等。已有 from_dict 门必须被真实入口消费，不能仅有 isolated helper 单测。legacy 缺版本字段按明确兼容适配处理，不照搬“凡缺版本均拒绝”而破坏旧模式。

证据：`future_object_schemas_written`；数据库未知版本正确拒绝的对照为 `future_store_schema`。

### R2-11 [P1] 子路径丢来源指针后仍能借根结构，且冒充完整保真

位置：`legacy_reader.py:121`。

合成旧 child 的 parent_path_id 明确非空，只将 event_id/product_position 设空。其旧底物仍是 CC=O，导入却认定 root，使用根 CCO，origin=raw_input、各轴 as_written、没有 uncertainty_note。

原正常缺档反例已修；这条损坏引用边界仍违反“子路径不能借根结构”。

**验收：**根身份须依据实际父关系、来源关系及身份一致性确认；非根/矛盾关系不能仅凭两个空指针判 root。结构不足采用 CN-only/unknown，或明确结构化失败，保留原因；旧库字节不变。

证据：`child_missing_archive_pointers_as_root`。

### R2-12 [P1：冻结门禁适配边界] 逐产物拒绝仅保存为附带列表，admission 没有消费

位置：`audit.py:734`、`:835`。

总体 direction/recorded eligibility 为 true，逐产物 verdict 为 accepted=False、reason=element_gate_rejected。mapper 全量保留列表后原样传给 decide_admission，配合全 verified 合成 audit，仍 expand/R6。

这是新适配器的消费缺口，**不是 legacy 原门禁被修改或已在线绕过**。旧拒因保存了，拒绝语义却没有进入新决策。

**验收：**定义活动旧门禁拒绝到新 hypothesis/event/共同产物处置的映射并实际消费；每个共同产物的拒因可追溯。不能删除被拒共同产物来凑“合法事件”，不能改变冻结门禁真假，也不能把明确拒绝降成普通诊断 unknown。策略允许哪些门禁非活动应显式版本化，不能靠列表未被消费来实现。

证据：`mapped_per_product_reject_ignored`。

## 4. P2 与交付证据需要修正的事项

| 项目 | 源码/证据 | 修正要求 |
|---|---|---|
| 断键 skip 的理由不实 | `tests/test_ppv1_s2.py:1254`、`:1257`；`skip_control.json` | CCOCC 的 O ID 是 S_O_1，不是 S_O_3。错夹具失败原因为 bond_not_present；同环境正确 S_C_2–S_O_1 断键执行成功。修夹具并恢复断言，不能对任意执行失败以“环境”skip，也不能将这一例列为已完成验收 |
| 处理池跳阶段可绕过哈希链 | `pool_audit.py:185`、`:194`；`skipped_pool_stage_breaks_hash_without_reason` | retrieved_raw→structure_screened 跳过协议阶段时，from_previous=True、前后 hash 不同、无 reason 仍成功。连续性应核相邻实际记录，不只核协议索引相邻；跳过/注入须明确审计 |
| 声明 scope 冒充实际已评估 scope | `path_context.py:508`；`scope_claim_without_evaluation` | 只评氧要求却输出氧+pH+温度已评估。实际覆盖从执行检查及适用要求产生；有事实不等于已检查，缩 scope 也不能隐藏必需未知维度 |
| coverage 按同键最后一项覆盖 | `path_context.py:509`；`coverage_conflict_then_satisfied` | 当前 covered 的实现条件是 satisfied，却能与 conflict 同键。明确区分 assessed/satisfied，按完整集合聚合；“评过且冲突”本身合理，不得把汇报问题误说成当前总判定回退为 compatible |
| 同值不同来源误标为事实不一致并降为 unknown | `path_context.py:387`；`identical_facts_distinct_sources` | 相同 pH、不同来源被标 conflicting_applicable_facts，返回 unknown，并非硬 conflict。按值/实体/作用域比较，保留所有来源；多供体并存也须正确表示 |
| basis 与形状不一致 | `path_context.py:305`；`basis_*` | 显式 point+dict 被静默改 range，range+scalar 被接受。构造/from_dict 一致校验；若允许规范化，记录轨迹且不静默改变来源声明的点值/最适语义 |
| 标签规则文字范围过宽 | 回修交付书及 mimo 标签建议 | 无注册映射的区间定性标签 unknown；氧制度枚举/可识别物种另行验证。不能把所有字符串都写成一律 unknown |
| 部分 study_map 的数是已知下界 | `provenance.py:280`；`partial_study_map` | 一条已知+一条未知输出 count=1、unresolved=1；已有未知披露，未发现“隐藏未知/虚增研究”的证据。exact 与 known lower bound 分轴，或明确重命名，不把下界叫精确独立研究数 |
| legacy provenance_refs 无新账本解析链接 | `legacy_reader.py:229`、`:269`；`legacy_provenance_ref_resolution` | 新记录确已保存，但 hypothesis 引旧 evidence_id，get_provenance 该 ID 为 None。明确 typed external ref+resolver，或映射新 record_id；不能宣称新引用链已验收 |
| pending 化学子句的实施状态 | mimo 的 local_delta、edge_kind、scoring_key 等意见 | 明确哪些属于 S2已交付、哪些 S3 pending；未实现不能写成程序已检查。全元素账不覆盖电子/自由基/独立同位素守恒，不推出机制、生物或环境可行性 |

这些 P2 不单独等同全部阻塞项；涉及 S3 消费的覆盖、门禁、处理池和来源引用应在对应接口启用前完成。搜索上限拆分、配置 round-trip、零预算/零深度及负 limit 门本轮确认已修，保留其回归。

## 5. 对 mimo R2 意见的独立裁定

**接受并补强：**缺 context 仍 R6、声明原子混入实际变化、未核声明/执行一致性、非键变化缺轴、自报 verified、point×interval、ABS/plain 分裂、理由码压平、覆盖范围文本不实。真实执行器的零净变化反例已经补齐，不能再称“是否真实可达尚未知”。

**新增而 mimo 未覆盖：**窄 audit_scope 直通 R6；公开结构丢增强立体；AND/OR 整组反转分裂；联合中心对称性未证；缺 state 默认崩溃；阶段历史、单位、物种缺席、启动供给、假设身份碰撞、分支共享；writer/重放/旧导入边界。

**不照搬的修法：**

- 不机械照搬“全部检查 verified”的字面；mimo 原文也允许真正语义不适用的诊断项为 NA。R6 要验证必需适用项的覆盖，区分真实语义不适用与缺输入未执行。
- “中心 verified 必须仅由供体诊断生成”过窄。其他注册、版本化、可追溯的确定性中心 checker 也可提供证据；任何自报字符串都不够。
- “scope 只由可用事实键生成”仍不足。事实可用不代表该项要求实际审过，不能用缩范围隐藏必要未知。
- mimo 提议补近似口径说明和夹具，但这些不足以解决本轮新增联合中心反例。已经输出的 symmetric_equivalent=True 必须由共同图映射证明。
- 单纯剥 ABS 不能解决 AND/OR 规范化，也不能修复公开结构往返丢信息。

不撤销 F01 的有效修复，也不因 isotope/radical/机制尚未实现而指控普通元素账错误。原始化学电荷未知须依来源转换历史判断，不能见中性串就假定丢电荷。

## 6. 回修顺序与验收组织

建议分三条并行实施线，最后在真实公共边界合并验证：

1. **化学与审计：**R2-01/02/03/12；修身份表示后再验证 profile→重建→strict，修实际变化后再验证中心证据→audit→admission。保留 full hydrogen、CN-only、partial、语义 NA 和 unknown 允许保留的正反例。
2. **条件与科学前提：**R2-04/05/06/07；先定义每边作用域、历史评估与不可变前提，再定义假设变体和 audit 输入 hash；阶段转换不写成反应边。
3. **存储与旧数据适配：**R2-08/09/10/11；以真实提交/重放入口验收，不能只测工厂；合成损坏库和同图多出现正例都要覆盖。来源记录真实保存与引用可解析分别验收。

最低新增回归必须包括：窄 scope/缺 context/无证据签名；AND/OR 表示往返及整组/部分反转对照；真实零净变化与共同对称映射反例；跨阶段正例及历史冲突保留；分支嵌套对象隔离；区间点值/单位/物种作用域；仅再生支持与初始池支持区别；不同科学前提假设共存；不同 fidelity 同图再出现和同事件多位置；公共 submit 的全部参照/互斥/版本门；删必要记录后的重放；非根指针损坏降级；逐产物冻结门禁拒绝的实际消费；有效断键与处理池跳阶段断链。

合成夹具不证明酶机制或生物可行性。先用它们证明系统不会错说“核实”、不会抹掉前提、不会写入不自洽账本，然后再开展 S3 搜索接线。

## 7. 阶段边界与交付口径

- S3 入口继续 fail-closed；不提前实现搜索、终点、评测执行、预算恢复等后续阶段。待本会话明确复审通过，再放行。
- 保持 legacy 默认模式、冻结 CN/G2/活动门禁判定及现有资产口径；不要顺手改模型、依赖或数据来源。
- 新语义如需升版，列出实际变化、兼容策略和读写边界；只升版本号不能替代版本门验收。
- 更新回修交付书：逐项写“已修的哪一范围、仍未知的哪一范围”；更正 skip 原因；区分实施方全量测试日志与独立复跑证据。
- 新化学判据保持未冻结。必要时准备 v3 评审请求，内容自包含、使用合成正反例，交由用户转交 mimo；不自行给其他会话发送消息。
- 本次没有真实污染物路径科学验收结论，S5 继续 pending。不能把 129/740 项工程测试转换为路径泛化或降解成功声明。

## 8. 可交给实施 agent 的下一轮回修提示词

```text
你负责 pollutant_pathway_v1 的 S0–S2 第三轮底座回修；本会话负责后续架构、化学和验收 review。目前尚未放行 S3。

仓库：/Volumes/CC/Enzyme_Agent/dependingv43
本轮审核 HEAD：0002f71af23a2d00db7734e15bf1142c64c85145

先读仓库 AGENTS.md，并完整读取以下绝对路径：
1. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md
2. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_2026-10-05.md
3. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_2026-10-05.md
4. /Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r2.md
5. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R2_2026-10-06.md
6. /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r2_2026-10-06/README.md

执行依据：原实施书正文及第17节，加本轮 Codex 复审的 R2-01～R2-12、P2处置和对 mimo 的采纳边界。不要把“有条件同意”当冻结通过，不整段照搬 mimo 建议。

先复跑附件合成探针，确认当前源码与审核版本的差异；把高置信反例转成有明确断言的仓库回归，再修实现。已有正确行为保留。可并行分为化学/审计、条件/身份、存储/适配三线，最后必须在公开API边界联合验证。

必须落实：admission必需项覆盖及确定性证据；增强立体规范化和公开表示往返；真实执行净变化及联合中心对称映射；条件要求绑定所属边/阶段，历史冲突不因未来转换消失，分支科学前提隔离；区间/点/单位/物种作用域；再生支持与启动供给未知分轴；不同科学前提的假设变体及完整审计输入hash；结构身份和所有来源出现保真分离；submit/replay的完整参照、互斥、语义及版本门；旧子路径损坏引用不得借根；冻结门禁逐产物拒绝真实消费。更正无效断键夹具、处理池跳阶段哈希链、覆盖/来源计数字段和引用解析。

unknown不自动reject；真实语义NA可保留；verified不得靠模型或调用方字符串。不能只补说明来保留程序已证伪的True。完整供体模板/所有变化类型可以按阶段排期，但当前S2诊断的命名、支持范围和未知必须诚实，不冒充完整变换一致。

只回修S0–S2，不解除S3入口，不提前做S3–S5。保持legacy默认行为和冻结CN/G2/门禁判定，不改模型、依赖或资产，不读gold或封存逐题runs，不调用真实模型或做真实题目实验。所有测试使用合成夹具，临时材料写新/tmp目录。遵守仓库禁止金标和封存运行污染的要求。

交付：提交/HEAD与diff；R2逐项处置（代码、测试、实际结果、未完成边界）；可复跑命令与日志；修正后的测试/skip说明；legacy G01回归；schema/语义版本与兼容策略；必要时更新自包含的mimo v3化学评审请求。不得改写Claude原始意见，不得将尚未实现写成已验收。

交付书保存为 /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R3_2026-10-06.md 。完成后停在阶段边界，由用户将交付书和化学评审回应交回本会话；不要自行发跨会话消息，不宣称已获S3许可或真实路径性能提升。
```
