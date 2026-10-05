# 污染物降解路径预测：架构升级实施书

版本：v1.2，2026-10-05。状态：实施交接规格；新的化学判据尚未冻结，本文件不表示路径科学性能已经得到验证。

修订记录：
- v1（2026-10-05）：GPT 参考既有评审意见起草本实施书。
- v1.1（2026-10-05）：**Claude Opus 5.5（tokeasy/claude-opus-5-5）**审查全文后追加第 16 节"追加审查意见与实施前置条件"（5 个 P0 前置问题、分两阶段放行建议、P1 非阻塞建议、交付包要求与实施约束），并按第 16.5 节修订第 2 节"证据类型完全没有区分"一行的表述。

- v1.2（2026-10-05）：Codex 与架构、化学子代理复核追加意见；统一两阶段交接，增加第 17 节明确采纳边界、阶段验收依赖及负面场景的正确预期。第 16 节保留 Claude 原文，执行以正文修订和第 17 节裁定为准。

实施仓库：/Volumes/CC/Enzyme_Agent/dependingv43
实施负责人：用户交接的另一个 agent。
Review：本会话负责架构、化学语义与验收复核；实施 agent 提交阶段成果后由用户交回本会话，勿自行假设有跨会话消息授权。

审查基线：源码 HEAD=536c977b6f23531a0f65e69e93a7a2799bf7e3a0；Claude 文档 SHA256=b66107e8a9d4c5739cc45a0d27a5e2395abd90e0055d14eaadeb859d32dffcd6。该文档在审查时是用户工作区的未跟踪文件，不纳入提交也不得删除；实施前记录实际工作区差异。

## 1. 要交付什么

本次从“单步反应答题”升级为**保留来路、条件和未解决假设的有界污染物路径探索**。继续使用 LangGraph，不重建一个自由调用工具的多 agent 系统。

首版支持两档结果：

- **可能降解路径**：给出可审计的反应假设、来源、连接关系和未知条件。
- **与已知条件相容的可能路径**：在声明的条件维度内检查路径一致性，同时披露未满足或未知的催化、共代谢及反应账目依赖。

实际主导路线、速率、产物积累量、菌群通量和解毒结论不属于首版。缺少菌株或动力学不阻止提出可能路径；也不能因此把可能路径称为实际发生的路线。

首版完成必须同时满足：反应假设与共同产物分开；事件不被报告 top-K 截断；备选路线能有界探索；原始化学状态和上下文沿路径保留；停止原因与化学终点分账；有路径原生导出与独立评测接口。仅完成 C2/C4 输入增强，不算完成本升级。

本轮不预设任何命中率涨幅或费用数值。工程验收与科学泛化验收是两件事。

## 2. 对 Claude 评审的处理结论

输入文档：[Claude 独立评审](/Volumes/CC/Enzyme_Agent/dependingv43/docs/HIT60_ARCH_PROTOCOL_INDEPENDENT_REVIEW_2026-10-05.md)。

| 意见 | 本规格处理 |
|---|---|
| 当前守恒检查不足以证明完整化学可行性 | 采纳。称为“有限规则筛查”，完整参与物配平和生物支持分项表达 |
| C2 在 novel 空候选上空转 | 采纳。底物档案独立于候选列表 |
| C4 改变任务组装和候选池 | 采纳。单独版本化，不再统称纯 prompt 改动 |
| G2 顺序、排序及截断须披露 | 采纳。记录实际调用顺序、输入范围及每层数量 |
| 证据类型完全没有区分 | 部分采纳（2026-10-05 Claude Opus 5.5 修订，原表述"不采纳"及其问题分析见第 16.5 节）。已有 kind、source_id、asset_sources、哈希等字段，但实测/规则/类比/模板的证据类型细分标注与贯通需要补充；实施 agent 须在 S0 阶段明确现有标注状态，在 S2 阶段完成细分和贯通（见第 5.4 节与第 16.2 节 P0-1），不能重做成另一套无来源分类 |
| 完全没有路径、只是检索系统 | 不采纳绝对表述。已有事件及 PathInstance，缺的是化学语义和路径搜索能力 |
| 实测 > 规则 > 类比 > 模板应成为固定全局排序 | 不采用。来源、底物适用性、条件和独立支持分轴评估，来源标签不是发生概率 |
| 必须先建完整酶机制库 | 不作为首版前置条件。可复用现有反应和规则，未知机制如实挂牌 |
| dev 没有价值或某准确率跨度必然不可达 | 不采纳。dev 可开发和排查，不能确证泛化；当前证据不能给出架构性能上限 |
| 用 CN 对比供体目标即可 | 修正。严格分子状态和变换中心为主，CN 仅作冻结口径旁证 |
| unclassified/未知条件统一进入 downgrade | 修正。覆盖未知、条件未知、冻结 G2 档位是不同轴，不新增降位 |
| SMILES 修复就是格式修复 | 修正。JSON 契约修复与重新提出分子结构分开，不得掩盖化学失败 |

现有分级依据见 [ReactionFinder](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/reaction_finder.py:1)及[任务候选字段](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/prediction.py:550)。本文件不采信 Claude 的逐题例子或聚合数字作为新架构验收依据，也不据此检查金标。

## 3. 实施边界与兼容策略

以下 profile 名称和新接口是待实施设计，不是现有功能。

### 3.1 新旧模式分开

- **legacy_v43**：现有默认行为。冻结的 HIT60 门禁、rank 资格、排序、预算含义、提示词、任务结构和 v3 评测保持既有口径。
- **pollutant_pathway_v1**：显式启用的新路径模式；独立 schema、策略、任务身份、导出和搜索预算。首版可用现有本地冻结资产与 scripted model 验收。
- 所有新模式开关进入 run identity。旧 run 不允许原地切换 profile 后 resume；旧模式自身的同版本恢复继续可用。
- 封存 run、原资产和原评测程序不回写。旧数据只读适配到新表示，输出写新根目录；任何历史导入都保留原始引用和不确定字段。
- 新增 schema 未知时明确失败。历史无版本数据只能走专用 legacy reader，不能被新模式默认当作完整新契约。
- 不修改用户已有 Claude 文档；不顺便更新模型、训练参数、依赖版本或来源资产。

### 3.2 化学门禁另有版本

新领域模型和搜索可以先使用 frozen_hit60_gate，并披露它的覆盖限制。新增 chemical audit 第一阶段提供诊断。

扩大原子供体范围、把供体失配变成 hard reject、改变 recorded 资格等，须在新规则 profile 中单列实现、测试与评审；不得隐含启用，也不得修改旧门禁的真假决定。新路径模式的条件冲突调度规则单独版本化，不能混入旧模式。

按[仓库约定](/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md:21)，新增化学判据在冻结或发布前，实施 agent 应产出自包含的 mimo 化学评审请求；由用户转交，默认只用规则级假想夹具。此规格提出判据范围，尚未替代这项化学复核。

## 4. 目标架构与数据流

~~~mermaid
flowchart TD
  A["输入 → ChemicalState + PathContext"] --> Q["持久搜索队列：选择下一 action"]
  Q --> R["复用检索/规则执行 → 来源标注 → 候选池冻结"]
  R --> H["构造 ReactionHypothesis 集合"]
  H --> D["确定性诊断 + 条件/依赖检查"]
  D --> T["组装模型任务：底物档案 + 有界假设上下文"]
  T --> M["可选：假设排序或受约束新假设"]
  M --> V["核验新输出；记录该 attempt"]
  D -->|无需模型| V
  V -->|已获准展开，含条件性可能假设| C["提交完整已知事件；独立安排产物展开"]
  V -->|明确拒绝/暂缓/方法失败| F["记录原因；安排剩余备选或暂缓"]
  C --> E["更新子路径上下文、依赖与终点评估"]
  E --> Q
  F --> Q
  Q -->|预算耗尽或无可执行 action| O["路径原生导出；搜索停止与化学终点分别报告"]
~~~

这是新 profile 的逻辑流程，不要求每个方框都成为一个 LangGraph node。确定性函数优先在既有职责清晰的 node 内固定调用；State 仍只持有 ref、当前阶段和预算快照。不得让模型直接修改 SQLite、frontier、条件事实或策略。

当前挂接点为[prepare_prediction](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/workflow/nodes.py:376)、[编辑执行](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/workflow/nodes.py:723)、[验证](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/workflow/nodes.py:1014)、[提交](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/workflow/nodes.py:1290)和[执行图](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/workflow/graph.py:35)。新 profile 的事件裁决不变量须重建，不能继续沿用 committed ⇒ reportable。

## 5. 领域契约：实施 agent 必须实现的最小对象

### 5.1 ChemicalState：化学状态与 CN 分开

~~~text
ChemicalState:
  schema_version, state_id
  structure_smiles_raw, smiles_isomeric, cn_identity
  structure_origin: raw_input | source_product | executed_product | legacy_cn_only
  original_structure_available
  formal_charge
  stereo_information_status: specified | partly_unspecified | unknown | not_applicable
  isotope_information_status
  source_refs[], representation_version
~~~

state_id 按保留形式电荷、同位素和立体信息的确定性分子图生成；原子映射号不属于分子身份。原始结构与解析后的图都保留。形式电荷是结构事实，不表示已知某 pH 下的质子化分布。

新路径检索和模型输入使用对应事件产物的完整结构，CN 仅用于旧评分/资产键适配。若冻结引擎内部必须用 CN，适配器应记录这一限制并保存严格输入，不能将 CN 精确命中称为严格结构一致。

历史只剩 CN 时标 legacy_cn_only，不猜回立体信息。有存档 product_smiles_full 时可以恢复存档形，但不能冒称原实验全部结构细节已知。状态、PathContext、PathInstance 分开：同分子不同来路不能共享并覆盖上下文。

现状参见[身份归一](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/domain/identity.py:18)和[检索用 CN 作底物](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/workflow/nodes.py:242)。

### 5.2 ReactionHypothesis：先定义反应假设，再提交事件

~~~text
ReactionHypothesis:
  schema_version, hypothesis_id, parent_path_id
  substrate_state_ref
  transformation_ref, transformation_signature_status
  participants[]:
    state_ref, side: reactant | product
    role: primary_substrate | cosubstrate | principal_product | coproduct | unknown
    coefficient, coefficient_status: known | unknown
  participant_list_status: source_complete | declared_complete | partial | unknown
  step_scope: net_reaction | elementary_step | multistep_summary | unknown
  step_scope_evidence_refs[]
  provenance_refs[], support_group_refs[]
  requirements[], assumptions[], dependency_refs[]
  audit_ref, model_decision_ref
~~~

模型新输出使用 proposals[]，每项是一条独立反应假设，里面才是该反应的产品集合。不同假设是本次转化的备选解释；不能据此断言它们在所有真实环境中绝对互斥。

已知计量系数必须是正有理数；未知系数为 null。禁止 known+null、零、负数或非有限数。重复相同参与物的处理须保留计量，不用集合去重丢掉系数。

同一已知裂解反应的共同产物属于一个事件。未提供副产物或共底物可以保留 partial 假设，但完整配平必须未知。模型 declared_complete 只是声明，须与来源完整度、程序验算分开。

历史 novel 平列表语义不明确时，保留 legacy_relationship_unspecified；不能静默拆成若干单产物反应，也不能把它重解释为已证实共同产物。新模式要求明确分组；旧模式解析不变。

step_scope=multistep_summary 的边保留为汇总边，不得冒充一个净酶反应；不能没有来源地拆出“隐含中间体”。unknown 可作为研究假设展示，但不得进入已确认单步主指标。

### 5.3 事件、报告与搜索：三个集合

- 事件保存该假设**全部已知参与物和产物**，包括不展开的副产物、已知共底物及系数。
- report projection 只决定展示/评分的主产物位次，保存自己的版本与理由。
- expansion plan 只决定哪些产物继续探索，保存 deferred 或不追踪原因。
- 改报告 K 或展开宽度，不得删改完整事件。某共同产物本身格式非法时不得静默丢掉它，须拒绝或挂起该假设并报告整体问题。
- 酶/催化剂另存为催化支持，不强行塞进净反应计量。
- 事件提交、子路径、展开计划及必要搜索记录在同一事务边界内一致；artifact 可以先写，恢复须能识别尚未提交的草稿。

现有[提交集被报告位次截断](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/workflow/nodes.py:1344)和[旧裁决约束](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/report_adjudication.py:594)是明确需要改造的新模式边界。

### 5.4 Provenance：复用既有标签，补信息而非升格

保留当前 kind、source_id、asset_sources、哈希、score_semantics；新增 source_origin 细分 curated_reaction、biotransformation_rule、analog_transfer、patent_template、model_proposal、unknown。组合来源保存每个成分，不根据一个模糊字符串包装为“实测”。

recorded 表示库中记录，不自动表示本场景直接实测。相同来源记录重复引用只算一个支持组；原研究身份未知时，独立支持数也应未知，不能把多个数据库 ID 当多次独立实验。

归并相同产物可用于报告去重；反应假设归并不能仅凭 CN 对。机制、计量或方向无法确认时保留不同假设/支持关系。有限池截断须披露被截掉的数量、来源分布和原因。

## 6. PathContext、条件与证据依赖

~~~text
PathContext:
  schema_version, context_id, parent_context_ref, phase_id
  requested_scope: possible | condition_compatible
  assessed_scope: possible | condition_compatible | conflicted
  condition_facts[]:
    key, value_or_interval, unit
    status: known_present | known_absent | unknown
    origin: user_input | curated_source | scenario_transition
    source_ref, subject_scenario_ref, phase_id
  accumulated_requirements[]
  assumptions[], dependency_refs[]
  context_hash
~~~

第一版条件键限定为 oxygen_regime、pH、temperature_C、matrix、electron_donor、electron_acceptor、growth_substrate。未列出某共底物不等于已证实没有它；“土壤/污水”不推出氧条件。条件缺失不得从有限守恒工具的隐式 H₂O/O₂ 中补造。

历史文献条件进入候选 source_conditions，不能直接进入当前 condition_facts；只有来源确实描述当前场景，或用户明确采用该场景时才可作当前事实。记录某反应在 25°C 被观察到，也不能自动推出“必需 25°C”；观察条件与有来源的 essential 要求分开保存。

每个 requirement 有 essential/preference、来源和适用维度。单项评估 satisfied/conflict/unknown/not_applicable；汇总：

- 有来源的 essential 要求与明确已知事实矛盾：conflict。
- 在**声明覆盖的环境维度**中，全部必要要求有来源并满足：compatible，同时输出 assessment_scope 与 requirement_coverage。
- 缺事实、要求覆盖未知或要求列表为空：unknown；不能以空列表自动判相容。
- pH/温度范围无交集为冲突；部分交集但实际值不确定为未知；输入点位于支持范围才判满足。
- preference 只提示，不变成冲突门。模型推测的要求属于假设，不得悄悄变成来源事实。

催化能力支持和共代谢支持另有 supported/inferred/unknown/conflict，不揉进 environment_fit。新模式有明确环境冲突时保留假设与理由，阻止在当前场景下继续展开；可展示为需不同条件的备选，不能自行更换场景。未知仍可输出条件性可能路径。

每条完整路线的 environment_fit 按该路线已选边及其所属阶段聚合：任何明确冲突→conflict；无冲突但任一必要要求/覆盖未知→unknown；全部满足且覆盖明确→compatible。不同备选路线分别聚合。assessed_scope 由这个结果派生，不能继承 requested_scope：请求条件相容但评估未知时，最终仍是 possible；compatible 也只说明声明的环境维度，催化和共代谢未知另列。

子路径上下文＝父路径事实/必要依赖＋本步新增要求。分支之间不可相互污染。同一固定场景中新增需求矛盾须显式记录；只有用户/来源提供的 scenario_transition 才允许阶段变化。阶段转换不是反应边，不计作酶反应命中，但须受独立转换次数与 action 预算限制。

依赖对象至少有 dependency_id、kind、statement、status、source_refs、introduced_at_hypothesis_id；status 固定为 supported/contradicted/unresolved。子路径继承依赖集合；下游精确匹配不能消除上游猜测。只有有来源的新证据或显式阶段转换才能解决对应依赖，并保留更新轨迹。阶段转换只影响后续步骤，不能追溯改写此前反应的环境冲突。重复引用不升级支持，不乘原始分数生成“路径概率”。

环境范围的设计参考：[enviPath 场景说明](https://wiki.envipath.com/doku.php?id=scenarios)。它支持分别记录研究环境和规则适用条件，不替代本系统的来源数据。

## 7. 固定函数、模型契约及候选处理审计

### 7.1 固定调用的函数接口

~~~text
build_chemical_state(structure, origin, source_refs) -> ChemicalState
build_substrate_profile(state, context, feature_policy) -> SubstrateProfile
build_hypothesis_pool(retrieval_ref, state, context, pool_policy) -> FrozenPool
assess_conditions(context, hypothesis) -> ConditionAssessment
audit_hypothesis(hypothesis, audit_scope, audit_policy) -> ChemicalAudit
check_edit_against_donor(current, donor, alignment, expectation, result, edits)
    -> DonorConsistencyDiagnostic
assess_endpoint(root, path_graph, context, evidence_refs) -> EndpointAssessment
~~~

名称可以按现有模块风格调整，职责和契约不能合并成一个含糊的“化学通过”。先复用现有特征、AtomTool、来源适配和不可变产物设施；不接新在线答案服务。

底物档案独立于 candidates，所有模型路由都能读到。候选来源、严格身份差异、位点/映射可得性、有限规则诊断及条件未知分别呈现。

### 7.2 模型职责与新模式

legacy rank_candidates 继续只选旧合格 recorded。新模式新增 rank_hypotheses：可比较已标来源、适用范围和诊断状态的推演假设；选择后仍是原证据类型的假设，不升为 recorded。

novel 新模式可以参考有界 proposal_context，也可提出候选外假设；两条通道必须明确，记录 reference_hypothesis_ids 与 output_origin，禁止伪造来源。空列表/弃权合法。对确定性工具已经执行出的产物，模型选择只引用稳定 hypothesis_id，不允许悄悄改写产品。

只有 JSON 字段/类型、允许 ID、语法契约错误可进有界格式反馈。SMILES 无法解析时记录结构失败；若允许重新提案，使用独立 chemical_reproposal policy/attempt/预算，本首版默认关闭。不得重试到产物通过化学门禁。

### 7.3 候选池处理必须可重放

记录实际发生的阶段，不伪造一个原代码没有的统一顺序：

~~~text
retrieved_raw
→ typed_and_grouped
→ structure_screened
→ finite_rule_preview
→ deduped
→ ordered
→ bounded
→ injected_to_model
~~~

各阶段保存 input/output hash、计数、逐项处置码、来源分布、排序键版本、字符/token 预算和截断原因。先结构解析再做新输入 preview；输出侧现有 G2 可能在 call_model 内、最终 validate_products 前执行，legacy 顺序不得偷改。

首版新池采用稳定的原检索位次、来源/假设 ID 作 tie-break，不把未经验证的分数跨来源解释为概率。若要换排序策略，应单独版本化和做对照，不把“前 N”描述为中性全量。截断后的有限池可以不覆盖全检索池，必须诚实报告。

## 8. ChemicalAudit：检查范围明确，未知不可冒充核实

~~~text
ChemicalAudit:
  schema_version, audit_id, scope, input_hash, checker_versions
  checks[]:
    name
    status: verified | violated | unknown | not_applicable
    reason_code, evidence_refs[], coverage
  legacy_gate_result_ref
  participant_accounting_status
  biological_support_status
  admission_disposition: expand | retain_conditional | defer | reject
  admission_policy_ref, admission_reasons[]
~~~

必需分项：结构解析/价态、身份信息保真、冻结有限规则诊断、参与物完整度、元素核算、形式电荷核算、映射/变换中心、step_scope、条件检查、来源依赖。

- 分子明确无法解析是 parse_check=violated；依赖该解析的后续项是 status=unknown、reason_code=prerequisite_failed_not_run，不伪装全部通过。
- 完整已知参与物和系数才核全反应元素与形式电荷。不能先电荷中和再验电荷守恒，不能自动补水/氧/辅酶凑平。
- 声明不完整时可以核局部结构差值，但 full_balance=unknown。
- 元素及电荷账核实不等于氧化还原转移、辅酶循环、机制、酶催化、热力学或速率已核实。首版不要求给所有反应实现完整机制模拟。
- 当前 H/O 自由、以元素计数与有限碎片规则为主的 G2 结果仅保留为旧规则诊断；unclassified 是覆盖未知，不新增惩罚。
- 输入 preview 不改变旧资格或门禁决定。新增 hard reject 的启用必须有独立策略和对应 review 结论。

供体诊断须输出 strict_target_match、legacy_cn_match、reaction_center_match、extra_changes、alignment_ref、信息缺失原因。严格目标相同也不能单独证明中心一致；对称等价对齐应正确处理。映射不可得、对齐搜索截断或预期结构有损时，受影响的核验轴返回 unknown，不能猜一个中心后称已核实；立体信息未知不必使已有充分映射支持的变化中心也变成未知。

诊断状态与展开决定分开：活动 gate profile 明确拒绝或结构非法则 reject；当前场景有来源的必要条件冲突则 defer、reason=current_scenario_conflict，对应 action 标 blocked，保存假设而不在此场景展开。仅条件、参与物完整账、映射或 step_scope 未知，不自动拒绝，可 retain_conditional 并按可能路径策略有界展开，继承未解决依赖；未知步长不进确认单步指标。预算/等待状态用 defer 并保留独立原因。任何新诊断转拒绝必须由 admission_policy 显式规定，不得写成“有 unknown 就停”。

新增碳/辅底物反应是覆盖扩展议题，不能被当前元素白名单否定为普遍不可能。公开例子是[IUBMB 乙酰苯羧化酶](https://iubmb.qmul.ac.uk/enzyme/EC6/4/1/8.html)参与厌氧乙苯降解、利用碳酸氢根增碳；此例不证明仓内已误杀任何具体样本，也不授权修改旧门禁。

## 9. 有界搜索与恢复：必须一起设计任务身份

### 9.1 搜索持久对象与接口

~~~text
SearchAction:
  action_id, run_id, parent_path_id, context_ref
  hypothesis_id_or_pool_ref
  action_kind: retrieve | decide | expand_hypothesis | activate_deferred | scenario_transition
  parent_search_revision, policy_version
  status: pending | claimed | done | deferred | blocked
  attempt_refs[], outcome_ref, budget_reservation_ref

schedule_hypotheses(parent, frozen_pool, context, budget)
  -> selected / deferred / blocked + reasons
record_expansion_outcome(attempt_id, outcome, evidence_refs)
  -> durable_search_result
activate_deferred(parent, trigger, expected_parent_revision, budget)
  -> activated_ids / unchanged + reasons
~~~

队列不再只依赖 PathInstance 是否 frontier。父路径已提交一个事件，仍可拥有尚未探索的备选反应 action。完整产物的 deferred 激活与父底物备选反应激活是不同操作，各自保存理由。

首次失败/下游知识受阻，可按稳定次序尝试剩余假设；不会删除原事件。**下游查不到不能证明上游反应为假**，应标 unresolved_continuation 并继续其他备选；明确条件冲突或检查违规另行归因。

首版调度不承诺找出最优路线：按冻结优先级和稳定 tie-break 有界探索，记录未探索部分。每父 action、每父备选、产物宽度、总 action、深度、重开次数、阶段转换及真实模型请求全部有限。无新信息时不能反复重开同一假设；不得循环到找到答案为止。

建议以配置显式指定上限，测试固定小值，不硬编码一个声称最优的 top-N。真实模型 provider 默认 off；本实施书不自动授权付费在线基准。

### 9.2 身份和幂等

当前[task_id_for](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/workflow/nodes.py:107)主要绑定 run、父路径、phase、CN 和版本。同父换反应若不换任务身份，会读到旧 decision/validation 或触发[ArtifactConflict](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/storage/artifact_store.py:1)。

新模式必须做到：

- hypothesis_id 来自冻结反应语义；无法确认等价的来源不强制合并。
- 每个语义尝试有持久 expansion_attempt_id，恢复继续同一 attempt；新备选产生新 attempt。
- 决策任务键包含 frozen_pool_digest、父上下文和局部搜索快照；单假设验证/裁决键包含 hypothesis_id 与 attempt 引用。
- 原始严格结构、条件、候选池/工具/提示词/反馈契约版本进入相关缓存键。
- 只在真正依赖局部搜索状态的任务中加入 parent_search_revision，不能把全图 revision 随意塞入底物特征缓存，造成无意义重算。
- 事件幂等键绑定 run、父路径、hypothesis、上下文及事件语义；重放同一事件不因重试号不同而新增一个事件。
- 同键异内容仍明确冲突；不得靠覆盖旧 artifact 实现回退。

### 9.3 预算、事务和恢复

旧 used_expansions 的语义保持不变。新模式另记 used_search_actions、实际检索数、真实模型请求数和重提案数，全部来自持久记录；复用检索不能使新的搜索尝试“免费无限”。

action 认领、预算预约及状态转换须有事务和唯一约束。模型发出前登记 request；失败、超时、悬空请求也计额度。恢复不承诺外部请求恰好一次；须暴露未知请求状态并按已登记额度处理。

恢复 claimed action 时读取已冻结快照、attempt 和预算预约，不用当前 revision 重算任务键，不重复扣预约。恢复注册但无响应的模型请求不能默默再次发出；若明示允许重试，需新 request 记录和剩余额度。

恢复测试至少覆盖：action 已认领、模型请求已登记但无响应、输出 artifact 已写但事件未提交、事件已提交但队列/导出尚未更新。重放不得重复事件、重复扩展或漏记模型费用；事件提交事务内需包含对应搜索状态的更新或可确定恢复的提交记录。

## 10. 搜索停止、化学终点与原生输出

分别输出 execution_status、search_stop_reason、chemical_endpoint_assessment。

search_stop_reason 至少包括 budget_limit、depth_limit、no_local_candidate、awaiting_prediction、exhausted_search、user_stop。存在未处理 deferred 或知识缺口时，completed 也不能表述为所有路线已搜索完毕。

chemical_endpoint 类型：

- unknown：无终点证据，包括搜不到、预算结束、模型弃权。
- metabolic_handoff：有来源的常规代谢衔接；不等于矿化。
- supported_terminal_transformation_product：来源在特定环境/观察窗口报告的终产物；不推断永久持久。
- supported_mineralization：来源支持根污染物在相应范围内矿化，必须保留证据、条件、时间范围和根碳去向的核查范围。

另有 bookkeeping_status 表示所选路径的参与物/根碳账是否闭合，不把账目闭合称为实际矿化。缺映射或共底物供碳时，根碳去向可未知。不能把不同备选反应生成的 CO₂ 相加以证明同一路线矿化。

终点源证据与模型推断分开；若沿路径仍有未解决必要依赖，最终声明不能被提升为本场景已观察事实。首版不自动推出解毒结论。参考[OECD 309 对初级降解、转化产物与矿化的区分](https://www.oecd.org/content/dam/oecd/en/publications/reports/2004/11/test-no-309-aerobic-mineralisation-in-surface-water-simulation-biodegradation-test_g1gh4b4a/9789264070547-en.pdf)。

新增路径原生导出必须保留 ChemicalState、PathInstance、全部反应假设/事件、备选关系、产品角色、上下文、依赖、audit、已展开/仅报告/暂缓状态、预算及停止原因。保留不同来路，不能按 CN 父节点首现合并成唯一真实路线。

旧[v3 导出](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/output/export_v3.py:11)继续服务冻结评测。新模式如提供 v3 适配，必须标 lossy_projection、原生结果引用及信息损失；不能直接把旧报告位置约束移植为新事件事实。

## 11. 分阶段实施与 review 交付

| 阶段 | 必须交付 | Review 重点 |
|---|---|---|
| S0：基线与设计定位 | 新旧 profile/版本清单、源码映射、当前基线行为的通用夹具；不运行付费实验 | 未曲解已有能力；不读金标；scope 明确 |
| S1：领域模型与存储 | ChemicalState、ReactionHypothesis、参与物、事件/报告/展开分离、只读 legacy 适配 | 同反应共同产物与备选分开；信息保真；事件不被 K 截断 |
| S2：上下文与固定诊断 | PathContext、底物档案、来源细分、依赖、条件、供体及有限规则诊断、候选池审计 | unknown 不升格；输入/输出顺序有程序证据；没有新增隐含门禁 |
| S3：模型任务与有界搜索 | 新假设协议、格式反馈边界、SearchAction、deferred 激活、任务身份/预算/恢复 | 同父换假设不复用旧裁决；不重复请求/事件；下游未知不反证上游 |
| S4：终点与原生导出 | endpoint 分账、路径原生结果、v3 有损适配、端到端 scripted 场景 | 不伪造终点；保留来路、未知和未展开集合 |
| S5：独立科学验收规格 | 路径评测器、数据清单格式、分组留出规则、阈值/统计预注册草案 | 判分零 LLM；工程通过不冒称科学通过 |

S1 → S2 → S3 → S4 是主链；S5 的数据规范可并行设计。每阶段可单独形成可 review 的 diff，不把所有改动塞进一个大重写。

首次交接仅实施 S0–S2，完成后提交阶段交付包，由用户交回本会话 review；通过后再实施 S3–S5。第一阶段可设计后续接口，不提前实施后续搜索、终点或评测逻辑。五个 P0 的阶段归属与具体要求按第 17 节执行。任何阶段发现契约矛盾、必须新增 hard gate 或需要改冻结评分，就将问题及可 review 的选项单独报告。涉及化学判据冻结按第 3 节办理。

每阶段交付包至少包含：

1. 对照本规格的完成项、未完成项和偏离理由。
2. 当前实现 diff/提交引用及 schema/策略/资产版本清单。
3. 实际测试命令、输出摘要、预算/事件/任务身份检查结果。
4. 只含规则级夹具的端到端结果及原生图，不含金标或封存逐题材料。
5. 遗留科学未知、范围限制和需要化学复核的事项。

## 12. 最小工程验收矩阵

以下均用自包含规则级假想夹具或现有通用测试设施，模型采用 scripted/off；不是污染物性能实测。

| ID | 场景 | 必须观察到的结果 |
|---|---|---|
| A01 | A→B 或 A→C | 两个反应假设/事件，不把 B+C 当同一反应 |
| A02 | A 裂解共同生成 B+C | 一个事件保存两产物；报告 K=1 也不丢 C |
| A03 | 某共同产物不继续追踪 | 完整事件仍保留；展开计划有独立原因 |
| A04 | 旧 novel 平列表导入 | 原语义不确定明确挂牌，不猜分组 |
| B01 | 对映体或可中和电荷差异 | 严格状态不同；允许旧 CN 相同；下步输入保持完整结构 |
| B02 | 映射号改动/只有旧 CN | 映射号不改分子身份；CN-only 不伪造已知手性 |
| C01 | 无条件、没列供体、pH 部分相交 | unknown；不能把没列供体判 absent |
| C02 | 明确无氧 vs 有来源的必需 O₂ | conflict；当前环境相容路线不展开；留原因 |
| C03 | 分支上下文与显式阶段切换 | 两分支不污染；转换须有来源，不追改此前步骤 |
| C04 | 文献有氧，当前场景无条件 | 当前氧状态仍未知；历史观察环境不变成当前事实 |
| C05 | 请求 condition_compatible，路径一条必要条件未知 | assessed_scope=possible；不得继承请求标签 |
| C06 | 结构有效、活动 gate 接受，但条件/完整账目未知 | 可有界探索可能路径；未知依赖沿途保留，不自动拒绝 |
| D01 | 合法编辑但偏离供体预期 | strict 识别目标偏离；center 依映射分别报告；旧门禁不被暗改 |
| D02 | 对称等价/映射缺失/立体未知 | 对称等价不误拒；受影响轴未知，不连带抹掉其他已核实轴 |
| D03 | 参与物/系数缺失；完整人工配平 | 前者 full_balance 未知；后者只核命名账目，不称酶可行 |
| E01 | 首选 B 后续受阻，备选 C 可继续 | 在上限内探索 C，保留 B 的 unresolved 状态和尝试记录 |
| E02 | 共同产物 deferred/备选 reaction deferred | 两类均能按接口激活，预算不足时给未展开原因 |
| E03 | 同父两假设与崩溃重放 | 新任务身份互不复用；重放不增加事件/请求计数 |
| E04 | 所有预算为小上限、存在循环提案 | 稳定终止，不反复重开；预算可由持久记录复算 |
| F01 | no_candidate/depth/budget；仅提出一项 CO₂ 且缺根碳去向和来源终点证据 | 缺独立终点证据时未知；不能声称根污染物矿化，也不抹掉已有有效证据 |
| F02 | 上游模型假设，下游 recorded | 上游未核实依赖继承到末端，不被洗成观测路线 |
| F03 | 共同来源多个引用、不同来路同 CN | 不增加独立支持；原生导出保留来路 |
| G01 | legacy profile 回归 | 通用夹具旧门禁、输入、报告及预算口径一致 |
| G02 | 原生导出重复生成 | 同一版本/图修订确定性相同；派生结果过期可识别 |

按修改模块运行相关旧测试和新测试；最终运行项目通用单测。真实资产慢测、真实模型请求、金标评测另列执行范围，不能以“全部测试”之名默认触发。本次写规格没有执行这些测试。

## 13. 科学验收：题源不足时明确 pending

两轨结果分开：

- known_evidence_reconstruction：允许利用已知反应先例，衡量重建与连接能力。
- unseen_path_inference：冻结排除直接对应路径/反应证据，衡量未见路径推演。声明实际排除范围，不能称所有邻近知识都未见。

评测单位为根污染物＋环境场景＋研究来源组；同研究、相邻边和高度相关路线不能拆到开发与独立确证两边。标准结构、参考图、step_scope、产物投影和数据划分在测试前冻结。不同题域和不同轨道不混报。

最小指标：确认参考边召回、关键中间体召回、确认错误率、参考外未验证边比例、环境冲突率、错误终点/矿化声明率、按深度表现、预算导致漏展开。参考文献图常不完备，未画出的边不能自动当化学错误；科学精确率只在有独立正负复核依据的子集报告，并给审查覆盖率。

判分程序零 LLM；预冻结来源/化学抽审另行完成。同题多次模型采样只估计随机变化，不是新增独立路径。样本量、通过线和区间估计方法须预注册，不能从当前 dev 结果倒推一个易过阈值。

若暂时没有独立路径数据：S5 交评测器及规则级测试，科学性能标 pending；不得以工程夹具通过宣称命中率提升。本阶段代码可以 review，路径科学能力不能冒充已通过。

## 14. 给实施 agent 的交接提示词

~~~text
请在 /Volumes/CC/Enzyme_Agent/dependingv43 按以下实施书完成架构升级：
/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md

先读该仓 AGENTS.md 和实施书，特别是第 17 节最终复核裁定；检查工作区状态，保留用户已有文档。本次只实施 S0–S2：新 profile/版本定位、领域契约与存储、上下文和固定诊断。完成后提交阶段包并停止跨阶段实施，由用户交回本会话 review；通过后再实施 S3–S5 的有界搜索、任务身份/恢复、终点和原生导出/评测。最终目标是可能路径与已知条件相容的可能路径，不能扩成未经支持的实际主路径预测。

保留 legacy_v43 的冻结行为和评测口径。新模式显式启用；旧 run 不原地迁移或换语义 resume；不读金标/封存逐题结果，不改来源资产，不执行付费在线实验。模型默认 scripted/off。没有独立路径题源时交付评测器和规格，并把科学验收标 pending。

每阶段留下可 review 的 diff、版本清单、测试摘要和规则级产物。第一阶段回答 P0-1/P0-2/P0-4，提交 P0-3 配置与计数设计草案；S2 的 C06 是 admission 策略级验收，完整搜索在 S3 集成验收。P0-5 在 S5 交付，科学状态可保持 pending。各阶段只要求其已实施范围内的证据，不提前要求后续测试通过。
新增化学 hard gate 或扩大反应范围按本书独立列项并提供化学评审请求，不暗改冻结判据。

S0–S2 实施完将阶段交付包交给用户，用户交回本会话进行架构和化学 review。通过后再执行第二阶段。不要自行向其他会话发送消息或发布性能结论。
~~~

## 15. 参考与本次审查范围

- [原单步协议提案](/Volumes/CC/Enzyme_Agent/dependingv43/docs/HIT60_ARCH_PROTOCOL_REVISION_PROPOSAL.md)
- [Claude 独立评审](/Volumes/CC/Enzyme_Agent/dependingv43/docs/HIT60_ARCH_PROTOCOL_INDEPENDENT_REVIEW_2026-10-05.md)
- [化学与实验设计评审](/private/tmp/HIT60_ARCH_PROTOCOL_CHEMISTRY_REVIEW_2026-10-05.md)
- [LangGraph 固定函数接入建议](/private/tmp/HIT60_LANGGRAPH_TOOL_RECOMMENDATIONS_2026-10-05.md)
- [污染物路径目标严厉评审](/private/tmp/POLLUTANT_PATHWAY_ARCHITECTURE_CRITICAL_REVIEW_2026-10-05.md)
- [v4.3 架构设计](/Volumes/CC/Enzyme_Agent/dependingv43/ARCHITECTURE.md)

临时评审材料只用于解释来源，本实施书自身包含全部强制契约与验收要求；临时文件丢失不影响实施。

本轮仅核对文档及通用源码，未读取金标或封存逐题结果，未实施代码、运行实验或确认科学指标。Review 的判断以实际 diff、契约、通用测试与独立数据支持为准，不能只凭新增文档或测试数量放行。

---

## 16. Claude Opus 5.5 (tokeasy/claude-opus-5-5) 追加审查意见与实施前置条件

**审查日期**：2026-10-05  
**审查模型**：Claude Opus 5.5 (tokeasy/claude-opus-5-5)  
**审查范围**：本实施书全文 + 源码头部映射 + 通用架构设计  

### 16.1 总体判断

**可以放行，但必须分两阶段执行，且必须回答 5 个前置问题。**

本实施书是严肃、系统性的架构重构方案，核心设计正确：
- 正视根本问题（可能路径 vs 实际路线）
- 领域契约清晰（ChemicalState、ReactionHypothesis、PathContext 分离）
- 化学语义正确（unknown 不升格、共同产物与备选分开）
- 工程设计合理（新旧 profile 分开、分阶段实施）
- 边界诚实（工程验收与科学验收分开、题源不足时 pending）

比原 C2/C4 补丁方案好几个数量级。

### 16.2 必须明确的 5 个前置条件（P0 级，阻塞实施）

#### P0-1：现有检索系统的证据类型是否已区分？

**矛盾点**：
- 第 2 节声称"已有 kind、source_id、asset_sources、哈希"
- 第 5.4 节要求"新增 source_origin 细分 curated_reaction、biotransformation_rule..."

**要求实施 agent 在 S0 阶段必须明确**：
1. 当前检索产物中哪些字段已标注证据类型？
2. 现有 kind/source_id 的取值范围和含义是什么？
3. 与规格书要求的 source_origin 枚举如何映射？
4. 如果现有标注不足，补标注的逻辑是什么？

**验收标准**：提供代码位置（文件:行号）+ 实际取值样例 + 映射表。

---

#### P0-2：G2 守恒检查在输入侧的实际执行顺序是什么？

**问题**：
- C4 要在输入侧注入候选时复用 G2
- 规格书第 7.3 节要求"输出侧现有 G2 可能在 call_model 内...legacy 顺序不得偷改"
- 输入侧 G2 与输出侧 G2 是同一个函数吗？参数、开关是否一致？

**要求实施 agent 在 S2 阶段必须提供**：
1. 输入侧候选池处理的实际代码调用顺序（带文件:行号）
2. 输入侧 G2 与输出侧 G2 的参数、开关、返回值对比表
3. 如果有差异，差异是什么，为什么合理？
4. 用测试用例证明"legacy 顺序未被偷改"（G01 回归测试必须通过）

**验收标准**：调用链路图 + 参数对比表 + G01 测试通过截图。

---

#### P0-3：有界搜索的"有界"具体数值是什么？

**规格书第 9.1 节列出的上限**：
- 每父 action、每父备选、产物宽度、总 action、深度、重开次数、阶段转换、真实模型请求

**问题**：这些上限的具体数值是什么？谁来决定？

**要求实施 agent 在 S3 阶段必须提供**：
1. 每个上限的配置键名、默认值、允许范围
2. 用于工程验收的固定小值（建议：每父备选=2，产物宽度=2，深度=3，总 action=10）
3. 超出上限时的 search_stop_reason 和 deferred 原因（枚举完整）
4. 用测试用例证明 E04："所有预算为小上限、存在循环提案 → 稳定终止，不反复重开"

**验收标准**：配置 schema + 默认值清单 + E04 测试通过截图。

---

#### P0-4：ChemicalAudit 的 admission_disposition 决策逻辑是什么？

**规格书第 8 节定义**：expand | retain_conditional | defer | reject

**规格书第 8 节要求**："任何新诊断转拒绝必须由 admission_policy 显式规定，不得写成'有 unknown 就停'"

**问题**：admission_policy 的具体规则是什么？

**要求实施 agent 在 S2 阶段必须提供**：
1. admission_policy 的配置结构（JSON schema 或 dataclass 定义）
2. 默认 policy 的完整规则表（例如：parse_check=violated → reject；condition_conflict → defer；其他 unknown → retain_conditional）
3. 用测试用例覆盖 C06："结构有效、活动 gate 接受，但条件/完整账目未知 → 可有界探索可能路径"

**验收标准**：policy schema + 规则决策表 + C06 测试通过截图。

---

#### P0-5：科学验收的"pending"状态如何转为"通过"？

**规格书第 13 节**："若暂时没有独立路径数据：S5 交评测器及规则级测试，科学性能标 pending；不得以工程夹具通过宣称命中率提升"

**问题**：
1. 什么样的数据才算"独立路径数据"？
2. 需要多少样本？
3. 评测器的输入/输出格式是什么？
4. 通过的标准是什么？

**要求实施 agent 在 S5 阶段必须提供**：
1. 评测器的完整规格（输入 schema：路径原生导出 + 参考图；输出 schema：指标 + 诊断）
2. 参考图的 schema（nodes、edges、step_scope、conditions、provenance 必须字段）
3. 数据划分规则（如何确保"冻结排除直接对应路径/反应证据"）
4. 预注册的最小样本量和通过线（哪怕是"待定，由用户和 teacher 裁定"）

**验收标准**：评测器规格文档 + 参考图 schema + 数据划分脚本 + 预注册草案。

---

### 16.3 分阶段放行建议

#### 第一阶段：立即放行 S0-S2（领域模型 + 诊断）

**理由**：
- S0-S2 不涉及搜索、模型调用、付费实验
- 主要是数据结构、存储、适配、诊断函数
- 风险低，可以快速验证契约设计

**交付要求**：
- S0：新旧 profile 清单、源码映射、当前行为基线（用规则级夹具）
- S1：ChemicalState、ReactionHypothesis、事件/报告/展开分离的实现 + 单测（A01-A04、B01-B02 必须通过）
- S2：PathContext、底物档案、来源细分、诊断函数的实现 + 单测（C01-C06、D01-D03 必须通过）
- **必须回答 P0-1 到 P0-4**

**关键验收点**：
- A01-A03：共同产物与备选反应不混
- C06：条件/完整账目未知 → 可有界探索可能路径（unknown 不升格）
- D01：供体诊断分项（strict/cn/center 分开报告）
- G01：legacy profile 回归（通用夹具旧门禁一致）

---

#### 第二阶段：S0-S2 review 通过后再放行 S3-S5（搜索 + 终点 + 评测）

**理由**：
- S3-S5 涉及搜索调度、任务身份、预算、恢复——整个系统的控制逻辑
- 必须在领域契约稳定后再实施，否则返工成本高
- S5 的评测器设计依赖 S1-S4 的实际输出格式

**交付要求**：
- S3：SearchAction、任务身份、预算、恢复的实现 + 端到端测试（E01-E04 必须通过）
- S4：终点分账、原生导出、v3 适配的实现 + 端到端测试（F01-F03 必须通过）
- S5：评测器规格、数据清单格式、预注册草案
- **必须回答 P0-3、P0-5**

**关键验收点**：
- E03：同父换假设不复用旧裁决
- E04：预算小上限 + 循环提案 → 稳定终止
- F01：搜索停止不被叫作矿化（unknown 终点诚实保留）
- F02：上游模型假设 → 下游 recorded，未核实依赖继承到末端

---

### 16.4 非阻塞性建议（P1 级，可在实施中采纳）

#### S1：source_origin 枚举应该再细分一级

**现有枚举**（第 5.4 节）：curated_reaction、biotransformation_rule、analog_transfer、patent_template、model_proposal、unknown

**建议增加**：
- `curated_reaction` 细分为：
  - `experimentally_observed_exact`（该底物的实测反应）
  - `curated_enzyme_reaction_related`（该酶的已知反应，但底物不完全一致）
- `biotransformation_rule` 标注规则库来源（enviPath、EAWAG BBD、UM-PPS 等）
- `analog_transfer` 记录底物相似度（Tanimoto 系数或子结构匹配度）

**理由**：这些细分对条件相容性评估和依赖建模至关重要。实测反应的条件要求可直接采用，规则推演的条件要求需要验证底物匹配。

---

#### S2：PathContext 应该包含"搜索意图"字段

**现有字段**（第 6 节）：requested_scope: possible | condition_compatible

**建议增加**：
- `search_intent`: exploration | verification | gap_filling
  - exploration：探索可能路径
  - verification：验证已知路径的条件相容性
  - gap_filling：寻找连接已知中间体的缺失步骤

**理由**：不同意图影响候选池过滤、模型任务设计、终点评估。例如 verification 模式应该优先使用高可信度证据，gap_filling 模式可以放宽候选范围。

---

#### S3：ReactionHypothesis 应该包含"机制类型"字段

**现有字段**（第 5.2 节）：transformation_ref, transformation_signature_status

**建议增加**：
- `mechanism_type`: oxidation | reduction | hydrolysis | conjugation | rearrangement | unknown
- `mechanism_evidence_refs[]`

**理由**：即使没有完整机制库，标注粗粒度机制类型有助于条件检查（氧化需要电子受体、还原需要电子供体）和路径一致性评估（连续氧化 → 还原 → 氧化需要不同电子载体）。

---

#### S4：endpoint_assessment 应该包含"证据强度"字段

**现有类型**（第 10 节）：unknown、metabolic_handoff、supported_terminal_transformation_product、supported_mineralization

**建议增加**：
- `evidence_strength`: direct_observation | inferred_from_pathway | model_prediction | no_evidence
- `observation_timeframe`（如果是 supported_terminal_transformation_product，记录观察时长）
- `mineralization_completeness`（如果是 supported_mineralization，记录根碳去向的核查范围：complete | partial | unknown）

**理由**：终点声明的可信度对风险评估至关重要。14 天培养终产物 vs 6 个月野外观察终产物，可信度不同。

---

#### S5：工程验收矩阵应该增加"负面场景"

**现有场景**（第 12 节）：42 条，主要是正向功能

**建议增加**：
- 非法输入：
  - H01：SMILES 解析失败 → parse_check=violated，后续项 status=unknown/prerequisite_failed
  - H02：负系数或零系数 → hypothesis 拒绝，explicit 错误原因
  - H03：重复 participant 但系数不同 → hypothesis 拒绝或保留歧义
- 循环依赖：
  - H04：A 需要 B 的产物作共底物，B 需要 A 的产物 → 检测循环，defer 并记录原因
- 资源耗尽：
  - H05：预算为 0、深度为 0、候选池为空 → 各自独立的 search_stop_reason
- 并发冲突：
  - H06：两个 action 同时认领同一假设 → 唯一约束触发，一个失败并重试
- 数据损坏：
  - H07：artifact 存在但无法反序列化 → 明确错误，不静默跳过
  - H08：事件已提交但 SQLite 记录缺失 → 恢复检测不一致，报告并修复或失败

**理由**：负面场景是稳定性和可恢复性的关键测试。第 9.3 节要求"恢复测试至少覆盖..."，但第 12 节矩阵没有对应测试用例。

---

### 16.5 修正规格书的一处表述

**第 2 节"证据类型完全没有区分"处理**："不采纳。已有 kind、source_id、asset_sources、哈希；需补细分来源和贯通，不能重做成另一套无来源分类"

**修正建议**：改为"部分采纳。现有检索系统包含 kind、source_id 等字段，但证据类型细分（实测/规则/类比/模板）的标注和贯通需要补充。实施 agent 须在 S0 阶段明确现有标注状态，在 S2 阶段完成细分和贯通（见 P0-1）。"

**理由**：原表述"完全没有区分"与"已有 kind"矛盾；"不采纳"让实施 agent 以为不需要做证据类型区分，与第 5.4 节"新增 source_origin"冲突。

---

### 16.6 实施交付包必须包含的材料

每阶段交付包至少包含（第 11 节已列，此处细化）：

1. **对照清单**：本规格的完成项（带章节号）、未完成项、偏离理由、P0 问题回答
2. **代码证据**：diff/提交引用、schema 定义、策略配置、资产版本清单
3. **测试证据**：
   - 测试命令（可重现）
   - 测试输出摘要（通过/失败/跳过统计）
   - 关键测试用例的详细输出（A01-A04、C06、E03-E04、F01、G01 必须包含）
   - 预算/事件/任务身份检查结果（用断言或专用检查脚本）
4. **端到端产物**：规则级夹具的原生图导出（JSON 或其他格式）、可视化（可选）、预期行为说明
5. **遗留清单**：科学未知、范围限制、需要化学复核的事项（明确哪些是首版不做、哪些是后续扩展）

---

### 16.7 给实施 agent 的额外约束

**不得做的事**（补充第 3.1 节）：
1. 不得在 S0-S2 阶段实施 S3-S5 的内容（即使"顺手"）
2. 不得在未回答 P0-1 到 P0-4 的情况下提交 S2 交付包
3. 不得在未回答 P0-3、P0-5 的情况下提交 S3、S5 交付包
4. 不得在 legacy profile 回归测试（G01）未通过的情况下声称任何阶段完成
5. 不得使用真实付费模型、读取金标、执行封存 run 评测来"验证"工程实现

**必须做的事**：
1. 每个阶段交付前，运行 legacy profile 回归测试（G01）并截图
2. 每个 P0 问题的回答必须包含：代码位置（文件:行号）+ 实际样例 + 测试用例编号
3. 任何偏离规格书的设计决策，必须在交付包的"偏离理由"中明确说明、提供备选方案
4. 发现规格书矛盾或无法实现的契约时，立即停止并报告，不要"猜一个合理实现"

---

### 16.8 审查模型的最终结论

**可以放行执行，建议分两阶段**：

1. **第一阶段**：S0-S2（领域模型 + 诊断），交付后回本会话 review
2. **第二阶段**：S0-S2 通过后再执行 S3-S5（搜索 + 终点 + 评测）

**关键验收点**：
- S1：A01-A03 测试通过（共同产物与备选反应不混）
- S2：C06 测试通过（unknown 不升格为事实）
- S3：E03-E04 测试通过（任务身份 + 预算稳定终止）
- S4：F01 测试通过（搜索停止不叫作矿化）
- 全局：G01 测试通过（legacy profile 回归）

**必须回答的 5 个 P0 问题**：
- P0-1：证据类型现状与补标注方案
- P0-2：G2 输入侧与输出侧执行顺序
- P0-3：有界搜索的具体上限配置
- P0-4：admission_policy 的完整规则
- P0-5：科学验收的评测器规格与通过标准

这份实施书的设计质量远超原 C2/C4 方案，是严肃的系统性重构。分阶段执行可以降低风险，确保每一层的契约稳定后再构建上层。

---

## 17. Codex 复核裁定与最终交接规则（v1.2）

复核日期：2026-10-05。本节核对第 16 节与正文的冲突，不改变旧化学门禁，也不声称新实现已经通过测试。第 16 节保留 Claude 原文作为评审记录；本节明确的阶段边界和限定为执行依据，其他要求继续按第 1–15 节办理。

**结论：可以开始第一阶段 S0–S2。** 完成后由用户将交付包交回本会话 review；通过后再实施 S3–S5。五个 P0 是对应阶段的验收交付项，不共同阻塞 S0 启动；科学验收未具备数据时保持 pending，不阻塞工程实现及 review。

### 17.1 消除阶段循环依赖

| 条件 | 必须完成的阶段 | 交付要求 |
|---|---|---|
| P0-1 来源类型现状 | S0 | 实际代码位置、规则级字段样例、既有 kind/source 到新 source_origin 的映射；不可用金标/封存逐题材料作样例 |
| P0-2 输入 preview 与输出 G2 | S2 | 实际调用链、scope/参数/开关/返回值用途、legacy 回归；若某项尚未启用，明确 off，不伪造调用证据 |
| P0-3 有界搜索配置 | S2 交设计草案；S3 完整验收 | S2 列配置键、有限默认值、允许范围、计数单位、优先级及测试小值；S3 补实际计数/恢复代码与 E04 |
| P0-4 admission_policy | S2 | schema、完整决策表和 C06 策略级测试；unknown 不自动变成 reject |
| P0-5 科学验收接口 | S5 | 输入/参考图/指标 schema、分组留出及防泄漏脚本、预注册草案；未冻结样本量或通过线时标 pending |

S2 的 C06 验证 admission_policy 允许 retain_conditional、保留未知依赖，**不要求此时实现完整有界搜索**。S3 再验实际展开、依赖继承及预算。S3 不以完成 P0-5 为前提；第一阶段可设计后续接口，不能提前实施搜索、终点或评测执行逻辑。

P0-3 的建议合成验收小值为每父备选 2、产物宽度 2、深度 3、总 search action 10；必须结合实际计数单位写出预期过程，必要的夹具调整有理由和版本。其余上限也必须显式有限。真实模型默认 off，不借默认预算授权付费请求。这组小值不代表生产场景最优策略。

测试证据以可复现命令、日志和断言为准，截图可选。尚未实施的阶段不要求出具该阶段的“已通过截图”；新规范的草案须明确标 proposed。

### 17.2 输入侧 G2 的审计要求不能变成隐含筛选

新增 input_preview_policy 取 off 或 diagnostic，并进入任务/策略身份：

- off：记录该检查未执行及原因，不冒称“已做 G2”。
- diagnostic：只附有限规则诊断，不根据其结果改写候选池成员、档位或原顺序。
- 若复用完整 conservation_filter_and_rank，必须将“获得诊断”与“消费其筛选/排序结果”分开；首版 preview 不直接消费后者。
- 输入结构合法性检查、来源分组、明确的 admission 决策和 bounded 截断继续各有自身规则及审计，不能统称 G2。
- 新增按 G2 过滤或排序的策略另行设计和 review；legacy 输出侧 G2 开关及实际顺序保持既有口径。

这是对第 16.2 节 P0-2 的限定，不削弱参数、顺序和回归核验。

### 17.3 化学建议的采纳边界

1. **来源细分。** 可以补观察支持及底物匹配状态，但 source_origin 与 evidence_basis 分轴保存。experimentally_observed_exact 必须有可追溯观察记录、明确匹配范围和结构信息；不能仅凭 curated/kind/CN 标签推定。原始来源不充分时保持未知。
2. **历史实验条件。** 保存为 source_conditions；只有来源明确支持的必要条件才进入 essential requirements。它们不自动成为当前场景事实，仍按第 6 节 subject_scenario_ref 检查。
3. **转化类别。** 若补粗分类，优先命名 transformation_class；oxidation/reduction 等不等于机制已核实，不能单凭标签推定需 O₂、特定供受体或不同电子载体。连续氧化—还原不自动形成路径冲突，具体约束须有来源。
4. **搜索意图。** search_intent 首版可作说明字段；verification/gap_filling 不得隐含放宽门禁、改变 source 支持、排序或预算。新增意图策略需单独版本化，未实现的意图明确 unsupported。
5. **终点证据。** 建议用 evidence_basis 表示 direct_observation/inferred_from_pathway/model_prediction/no_evidence，表示依据类型而非固定强度次序。观察时间、环境和检测范围另存，较长观察期不自动更可信。推断/模型预测不能单独产生 supported 终点。
6. **矿化范围。** 使用 root_carbon_accounting_coverage 表示账目核查范围；来源报告的矿化比例另存数值、计量基础和证据引用。账目完整不能等同所有根碳已矿化。

这些限定优先于第 16.4 节相应解释，不要求先建完整机制库，也不扩大首版科学声明。

### 17.4 负面场景的正确预期与阶段归属

第 12 节当前有 24 个验收编号，第 16.4 节所称 42 条不作为计数依据。补充测试按受改动模块归属，不把所有负面场景都拖到 S5：

| 编号 | 阶段 | 正确的验收预期 |
|---|---|---|
| H01 | S1/S2 | 结构无法解析为 violated；后续受影响项 status=unknown、reason_code=prerequisite_failed_not_run |
| H02 | S1 | 零/负/非有限系数违反输入契约；拒绝该表示，不宣称反应本身化学不可能 |
| H03 | S1 | 同侧、同物种、同角色且已明确为并列计量贡献的重复项可求和；保留原条目及规范化轨迹。来源重复引用不得重复加计量；含义/系数未知则保留歧义 |
| H04 | S2 建依赖诊断；S3 验调度 | 共底物循环有启动/再生支持时不得自动阻断；未知时标 unresolved_initial_supply，依显式策略处理，不称化学不可能 |
| H05 | S3 | 预算零、深度零、池为空分别做独立夹具；多原因同时发生时按冻结优先级给主原因，保留其他原因 |
| H06 | S3 | 同一 action 身份只有一方获执行权/预算预约；竞争方返回 already_claimed/unchanged 或复用完成结果，不新建模型请求、不再扣额度。不同路径或上下文不按 hypothesis 全局互斥 |
| H07 | S3/导出读取 | artifact 无法反序列化或哈希不符时明确完整性失败并保全，不静默跳过 |
| H08 | S3 | 已提交事实与账本不一致时保全证据、明确失败/隔离，不默认补造事件或自动修补旧/封存 run |

S3 还必须覆盖第 9.3 节四个崩溃边界：认领后、请求登记未响应、输出已写未提交、事件已提交未完成后续状态。并发、预算预约和崩溃恢复是强制工程验收；不可降为 P1 可选项。

若新活动 run 需要自动恢复，仅能按显式恢复策略，使用完整且校验通过的权威记录重建并留轨迹；无充分记录则失败，不能猜数据补齐。

### 17.5 本次交接和后续 review

首次交付：S0–S2 实现、通用单测、P0-1/P0-2/P0-4 回答、P0-3 设计草案、G01 回归结果。保留 schema/版本、变更 diff、规则级样例和未完成项。完成后不继续跨阶段实施，由用户交回本会话 review。

阶段二交付：review 通过后实施 S3–S5，重点交付搜索身份、预算/恢复、备选路线、终点、原生导出和科学验收接口。科学性能可明确 pending；不得把通用夹具通过写成路径泛化通过。

遇到真正阻塞的契约矛盾时报告具体问题、可 review 的方案及影响范围；只停受影响工作，继续已明确且独立的任务。不要因可解决的工程细节停止整轮实施，也不能自行改变本节的阶段边界。

