> 生成通道：本任务书由 opencode tokeasy/gpt-6-sol 于 2026-10-08 撰写（用户裁定交给 tokeasy 的 gpt 写），基于仓内规格 §12/§13/§17、S3B-R3 终审 §7.3 与 AGENTS 红线生成；主会话落盘。采信与执行前由用户/主会话复核。

# pollutant_pathway_v1：S5 数据与科学验收规格任务书

日期：2026-10-08  
建议文件名：`docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md`  
仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`  
适用 profile：`pollutant_pathway_v1`  
阶段：S5  
状态：设计规格；本轮只出规格，不实施代码、数据集、真实评测或模型实验。

---

## 1. 任务定位

S5 的定位是**数据与科学性能验收**，不是工程功能验收。

S3 工程交接已经完成，R3 明确指出：

- S3 工程通过不表示污染物路径科学性能通过；
- 工程绿数不能倒推出 dev 或 298 的科学通过线；
- 工程夹具通过不能证明真实路径命中率、反应机制、环境相容性、终点或矿化能力；
- 判据尚未由本任务自动冻结，最终冻结权属于用户和 teacher；
- 若没有独立路径数据，S5 可以先完成评测器接口、数据格式和预注册草案，但科学性能必须保持 `pending`。

S5 的目标是建立一套可独立复核的科学验收规格，回答以下问题：

1. PPV1 是否能够重建有来源支持的已知路径边和关键中间体？
2. PPV1 是否能在明确冻结排除范围内提出未见路径推演？
3. 输出路径是否保留条件、来源、假设、依赖、终点和未知状态？
4. 工程输出与参考路径图之间如何进行零 LLM、可重放、可审计的比较？
5. dev 与 298 两个题域分别表现如何，是否存在题域内的性能差异？
6. 检索支持与未见推演是否被分开报告，避免把来源重建能力误报为科学泛化能力？

S5 不负责证明：

- 真实环境中某条路径一定发生；
- 路径是主导路线；
- 反应速率、通量、产物积累量或菌群贡献；
- 解毒效果；
- 完整酶机制、热力学可行性或生物活性；
- 路径终点必然是矿化；
- 工程测试绿数对应某个科学命中率。

---

## 2. 必读依据与交接约束

本任务书依据以下材料编写：

1. `docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md`
   - §12：既定阶段内容与工程验收边界；
   - §13：科学验收及题源不足时的 `pending` 规则；
   - §17：阶段裁定、P0-5、S4/S5 关系和科学声明边界。
2. `docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_R3_2026-10-08.md`
   - §7.3：S3 工程完成后的 S4/S5 交接约束。
3. `AGENTS.md`
   - 金标、题面、封存 run、费用、判分和 mimo 三触发点红线。
4. `docs/POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md`
   - 任务书结构、交付、证据、权限和边界风格范本。

如本任务书与 `AGENTS.md` 冲突，以 `AGENTS.md` 为准。  
如本任务书与 S3 评审报告的科学边界冲突，以 R3 和用户/teacher 后续裁定为准。

---

## 3. 与 S4 的关系

S5 的规格设计可以与 S4 并行进行，但 S5 的正式执行依赖 S4 交付的输出接口。

### 3.1 S4 必须提供的消费接口

S4 需要提供或冻结以下可供 S5 消费的接口：

- 路径原生导出；
- `ChemicalState`、`PathContext`、`PathInstance` 的可追溯引用；
- 全部反应假设和完整事件；
- 共同产物与备选反应的区分；
- 产品角色和展开状态；
- 条件事实、条件未知和条件冲突；
- provenance 和 support group；
- dependency 和 unresolved 状态；
- `ChemicalAudit` 及其 `proof_scope`；
- endpoint 分账；
- search stop reason；
- 预算、深度、未展开和 deferred 记录；
- v3 有损适配与原生结果之间的引用关系。

S5 不得从旧 v3 report projection 反推完整路径。若消费 v3 适配结果，必须标记：

- `lossy_projection=true`；
- 原生结果引用；
- 已丢失字段；
- 该投影不得用于需要完整路径语义的科学指标。

### 3.2 S5 对 S4 的依赖边界

在 S4 接口未交付前：

- 可以冻结 S5 数据清单、参考图 schema、划分规则、评测器输入输出契约和预注册模板；
- 可以使用规则级合成路径验证评测器接口；
- 不得宣称已经完成真实路径评测；
- 不得用 S3 或 S4 的工程数字填充科学指标；
- 科学状态保持 `pending`。

---

## 4. 权限与数据红线

### 4.1 必须逐次授权的材料

以下材料每一次触碰都需要用户逐次授权：

- 真实题面；
- 金标或标准答案；
- 含金标的派生数据；
- 封存逐题结果；
- 真实评测结果；
- 真实模型调用；
- 任何会产生模型费用的 provider 请求；
- 将题面、金标或封存结果发送到外部评审通道。

本任务书本身不包含真实题面、金标、封存结果或收费模型输入。

### 4.2 金标和封存材料

- 金标永不入仓；
- 含金标的产物只能写入 gitignored 目录；
- 封存 run 只读，不得原地修改；
- 新实验必须使用新批次根；
- 不得通过重新计算 ID、重新导出或迁移来覆盖历史身份；
- 不得将金标内容写入提交、永久证据目录、任务书或普通测试 fixture。

### 4.3 判分边界

科学判分必须为零 LLM：

- LLM 可以在被明确授权时生成模型输出；
- LLM 不得参与参考图构建后的最终判分；
- LLM 不得决定边是否命中；
- LLM 不得决定来源是否独立；
- LLM 不得决定条件是否冲突；
- LLM 不得决定终点或矿化指标；
- LLM 不得对评测结果做二次裁判后覆盖程序结果。

化学结构、参考图和金标口径需要人工或 teacher 判断时，按 `AGENTS.md` 的 mimo 三触发点执行：

1. 题源或结构判据冻结前的化学评审；
2. 出题前对考卷的化学抽审；
3. 出题后对答题结果的后置化学复核。

mimo 的意见不替代源码、数据和程序证据；只能采信到与独立程序证据互证的程度。

---

## 5. 题域与评测轨道

S5 必须同时沿两个维度拆分报告。

### 5.1 题域拆分

#### dev

`dev` 指 B1 环境路径中间步骤题域。

报告内容可以包括：

- 环境条件下的路径中间步骤；
- 条件事实和必要条件的相容性；
- 中间体和反应边；
- 条件冲突、未知条件和依赖继承；
- 路径深度和预算对展开的影响。

#### 298

`298` 指 RHEA 通用酶学题域。

报告内容可以包括：

- RHEA 来源支持的反应边；
- 反应物、产物和共同产物；
- enzyme/reaction provenance；
- 反应假设和 step scope；
- 参考来源支持与未见推演。

`dev` 和 `298` 必须分别报告：

- 样本数；
- 研究来源组数量；
- 各项指标；
- 置信区间；
- 缺失和未知比例；
- 评测失败数；
- 预算导致的未展开比例；
- 通过/不通过状态。

不得把 dev 的结果外推到 298，也不得把 298 的结果外推到 dev。对外数字必须带题域标签。

### 5.2 评测轨道拆分

#### 轨道 A：`known_evidence_reconstruction`

衡量利用已知反应先例、检索来源和冻结支持重建路径的能力。

该轨道可以使用：

- 参考路径对应的已公开研究来源；
- 允许纳入开发或检索支持范围的反应记录；
- 已冻结且有来源的中间体和反应边；
- 参考图中的 provenance 和 support group。

该轨道不等于泛化能力。它回答的是：

> 系统能否在已有来源支持下重建或连接路径？

#### 轨道 B：`unseen_path_inference`

衡量在冻结排除范围内对未见路径的有界推演能力。

必须在评测前冻结：

- 哪些直接对应路径或反应证据被排除；
- 排除的是精确反应、精确底物、精确边，还是整条研究路线；
- 相邻边、同研究路线、同实验组数据是否一并排除；
- 哪些知识仍然允许作为背景或规则支持；
- “未见”的范围不包括未被明确排除的所有邻近知识。

不能把“训练集没有相同字符串”称为未见。  
不能把同一研究的拆分记录分别放入开发和独立确证。  
不能把同一路线换一个数据库 ID 后当成独立未见样本。

两条轨道不得合并成单一总分。

---

## 6. 评测单位与数据分组

### 6.1 最小评测单位

最小科学评测单位为：

> 根污染物或根底物 + 环境场景 + 研究来源组 + 题域 + 评测轨道

其中：

- 根污染物/根底物确定评测对象；
- 环境场景确定条件事实和适用范围；
- 研究来源组确定独立性；
- 题域确定 dev 或 298；
- 评测轨道确定 known reconstruction 或 unseen inference。

同一根底物的多个分支不能自动视为多个独立样本。

### 6.2 研究来源组

`source_group_id` 是独立性边界，不等于数据库记录 ID。

同一来源组至少应合并：

- 同一研究论文或实验报告；
- 同一实验系列；
- 同一菌株、酶、底物和路线的重复数据库记录；
- 同一研究衍生出的多个反应边；
- 明确属于同一研究路线的相邻步骤；
- 同一来源的不同格式、镜像或版本。

若原始研究身份未知：

- `source_group_id` 保持未知；
- `independence_status=unknown`；
- 不把多个数据库记录计为多个独立支持；
- 该样本不得用于需要独立重复支持的精确率或置信区间，除非预注册另有规定。

### 6.3 防泄漏划分

划分必须在生成模型输入和任何调参前完成，并保存不可变清单。

最小划分层级：

- `development`：允许用于接口开发、规则调试和参数选择；
- `tuning`：允许用于预注册前确定实现参数；
- `held_out`：冻结后不得用于调整；
- `independent_confirmation`：仅用于最终独立确证；
- `unseen_exclusion_manifest`：明确记录未见轨道排除的直接证据范围。

同一 `source_group_id` 不得跨开发、留出和独立确证集合。  
同一研究的相邻边和高度相关路线不得拆到不同集合。  
同一根污染物若其研究来源高度相关，应按预注册的 group split 规则整体划分。

划分脚本必须：

- 输入数据清单和版本；
- 读取 source group、root entity、route identity、domain 和轨道字段；
- 生成确定性划分；
- 输出每个集合的样本、来源组和根对象摘要；
- 检查跨集合泄漏；
- 对重复结构、重复边、同研究相邻边进行检测；
- 失败时终止，不生成“近似无泄漏”的结果；
- 保存输入 hash、规则版本、输出 hash 和检查结果。

评测运行时只能消费冻结划分清单，不得根据当前输出重新划分。

---

## 7. 参考图规格

参考图是科学评测的权威输入之一。它不是模型输出，也不能由评测程序根据模型结果反向生成。

建议 schema 名称：`ppv1_reference_graph_v1`

### 7.1 顶层字段

```text
ReferenceGraph:
  schema_version
  reference_graph_id
  domain: dev | 298
  track: known_evidence_reconstruction | unseen_path_inference
  root_entity
  scenario
  nodes[]
  edges[]
  endpoint_annotations[]
  source_groups[]
  split_assignment
  coverage_statement
  provenance_manifest
  creation_review
```

### 7.2 根对象

```text
root_entity:
  entity_id
  structure_smiles_raw
  strict_structure_identity
  formal_charge
  stereo_information_status
  isotope_information_status
  source_refs[]
```

缺少完整结构时必须标明：

- `identity_scope=cn_only` 或其他有限范围；
- 缺失的结构维度；
- 该样本不得被当作严格结构确证；
- 可使用的指标范围。

### 7.3 节点

```text
ReferenceNode:
  node_id
  state_identity
  structure_smiles
  structure_identity_scope
  role:
    root
    intermediate
    principal_product
    coproduct
    terminal_product
    unknown
  occurrence_id
  source_group_refs[]
  condition_scope[]
  provenance_refs[]
  node_status:
    observed
    inferred_from_source
    reference_only
    unknown
```

同一分子在不同来路、不同场景或不同研究来源中的出现必须保留 distinct occurrence。  
不能仅凭 CN 或结构相同把不同路径来路合并为一个真实节点。

### 7.4 边

```text
ReferenceEdge:
  edge_id
  from_node_ids[]
  to_node_ids[]
  transformation_ref
  transformation_signature_status
  participants[]
  participant_list_status:
    source_complete
    declared_complete
    partial
    unknown
  coefficient_status
  step_scope:
    net_reaction
    elementary_step
    multistep_summary
    unknown
  condition_requirements[]
  scenario_scope
  provenance_refs[]
  source_group_refs[]
  evidence_basis
  edge_status:
    observed
    supported_inference
    reference_only
    unknown
```

参考图必须区分：

- 共同产物；
- 备选反应；
- 主产物；
- 副产物；
- 未展开但属于完整事件的参与物；
- 多步汇总边；
- 未知 step scope。

未画出的边不能自动判为化学错误。  
参考图本身不完备时，评测结果必须披露覆盖范围。

### 7.5 条件与来源

```text
ConditionScope:
  key
  value_or_interval
  unit
  status:
    known_present
    known_absent
    unknown
  required:
    essential
    preference
  subject_scenario_ref
  source_refs[]
```

```text
ProvenanceRecord:
  provenance_id
  source_group_id
  source_origin
  evidence_basis
  citation_ref
  structure_match_scope
  observation_scope
  source_conditions[]
  independent_status
```

`recorded` 只能表示库中有记录，不能自动表示该场景直接实测。  
source origin 与 evidence basis 分开保存，不得仅凭数据库类型或模糊标签把规则、类比或模板升格为实测。

---

## 8. 评测器输入与输出

建议评测器名称：`ppv1_scientific_evaluator_v1`

### 8.1 输入

```text
EvaluationInput:
  evaluator_schema_version
  run_identity
  profile_version
  export_schema_version
  native_path_exports[]
  reference_graph_manifest
  split_manifest
  domain
  track
  metric_policy_version
  preregistration_id
  scoring_policy_version
  missingness_policy_version
```

每个 `native_path_export` 至少必须包含：

- 根对象和严格结构身份；
- 路径节点和 distinct occurrence；
- 完整事件；
- 反应假设；
- 参与物、角色和系数；
- 备选关系；
- 条件事实与条件未知；
- provenance、support group 和 source refs；
- dependency；
- `ChemicalAudit`；
- endpoint assessment；
- search stop reason；
- 未展开、deferred、预算和深度记录；
- `lossy_projection` 标记及原生引用。

输入校验失败必须产生结构化错误并停止该样本评测，不能静默删除字段或自动补全。

### 8.2 输出

```text
EvaluationOutput:
  evaluator_schema_version
  evaluation_id
  run_identity
  domain
  track
  split
  sample_results[]
  aggregate_metrics[]
  uncertainty_intervals[]
  coverage_report
  missingness_report
  budget_omission_report
  leakage_checks
  invalid_input_count
  scoring_provenance
  status
```

单样本结果至少包含：

```text
SampleResult:
  sample_id
  root_entity_id
  source_group_id
  predicted_node_matches[]
  predicted_edge_matches[]
  key_intermediate_matches[]
  false_or_unverified_edges[]
  environment_conflicts[]
  endpoint_claim_checks[]
  mineralization_claim_checks[]
  depth_metrics[]
  budget_omission
  unknown_or_partial_summary
  scoring_status
```

评分程序不得根据自然语言解释做模糊判断。  
匹配必须使用冻结的确定性规范化和身份规则，并记录：

- 严格结构匹配；
- 允许的等价规则；
- CN 仅作为旁证时的使用范围；
- 反应中心匹配；
- step scope 匹配；
- 条件范围匹配；
- provenance 和 source group 匹配；
- 证据覆盖范围；
- 未核查字段。

---

## 9. 指标规格

S5 最小指标如下。每项都必须按 dev/298、known/unseen、split 和必要的深度分层报告。

### 9.1 参考边召回

衡量参考图中已声明可评测的边，有多少被输出路径匹配。

必须分别报告：

- 严格反应边召回；
- 仅结构身份匹配的边；
- step scope 一致的边；
- 因参考覆盖不足而无法判断的边；
- 因预算或深度未展开的边。

### 9.2 关键中间体召回

关键中间体清单必须在评测前冻结。  
不得根据预测结果动态决定哪些节点算关键中间体。

报告：

- 节点召回；
- 严格身份召回；
- 仅 CN 对应但严格结构未知的比例；
- 来源支持和未见推演分别的召回。

### 9.3 确认错误率

该指标只能在有独立正负复核依据的子集上报告。

“确认”必须指：

- 输出明确将该边、节点或终点标为支持、确认或等价强声明；
- 不把 `unknown`、`partial`、`conditional` 当作确认；
- 不把模型提出但未验证的假设当作 confirmed；
- 不把工程 audit 通过当作科学观察事实。

报告时必须同时给：

- 评测覆盖率；
- 可判定样本数；
- 未知/不可判定样本数；
- 误确认数；
- 误确认类型。

### 9.4 参考外未验证边比例

衡量输出中没有参考来源、没有独立支持或不属于允许推演范围的边。

该指标不能直接等同错误率，因为：

- 参考图可能不完备；
- unseen 轨道允许提出未见边；
- 规则推演与模型假设可能是合法的条件性输出。

因此必须拆分：

- 参考外但有允许推演依据；
- 参考外且仅模型提出；
- 参考外且没有可审计依据；
- 因参考图覆盖不足无法判断。

### 9.5 环境冲突率

统计路径中出现明确条件冲突的比例。

必须区分：

- 明确 essential 条件冲突；
- 条件未知；
- 条件覆盖不足；
- preference 不满足；
- 历史来源条件不能映射到当前场景；
- 场景转换后条件发生变化。

未知不能计为冲突，满足也不能超出声明覆盖范围后升级为全路径相容。

### 9.6 错误终点或矿化声明率

单独统计：

- 将 `search_stop_reason` 错叫终点的比例；
- 将 `metabolic_handoff` 错叫矿化的比例；
- 缺根碳账目仍声称矿化的比例；
- 仅有模型推演仍声称已观察终点的比例；
- 将不同备选路线的 CO₂ 合并后声称同一路径矿化的比例；
- 未解决必要依赖仍被提升为本场景事实的比例。

终点分类必须沿用 S4 的分账：

- `unknown`；
- `metabolic_handoff`；
- `supported_terminal_transformation_product`；
- `supported_mineralization`。

`bookkeeping_status` 不能单独提升为矿化结论。

### 9.7 按深度表现

至少按以下深度报告：

- 根节点到第 1 条反应边；
- 第 2 条反应边；
- 第 3 条及以上；
- 超出深度预算未展开。

若样本量不足，必须显示 `insufficient_sample`，不能合并成看似稳定的总分。

### 9.8 预算导致漏展开

单独报告因以下原因未覆盖的内容：

- action budget；
- depth budget；
- product expansion width；
- per-parent alternative limit；
- retrieval limit；
- model request limit；
- deferred 未激活；
- awaiting prediction；
- 其他明确停止原因。

预算导致漏展开不能计为模型化学错误，也不能从科学命中分母中无声删除。分母定义必须在预注册中固定。

---

## 10. 阈值、样本量和统计预注册

S5 不得从当前 dev 结果倒推一个容易通过的阈值。

### 10.1 必须由用户/teacher 裁定的项目

正式执行前必须裁定：

1. 题源范围；
2. 金标口径；
3. 哪些反应边和节点属于可评分参考；
4. unknown、partial、conditional 的分母处理；
5. 研究来源组的独立性口径；
6. dev 与 298 的样本量；
7. known 与 unseen 两条轨道的样本量；
8. 参考图覆盖不足时的排除规则；
9. 严格结构、CN、反应中心和 step scope 的匹配规则；
10. 通过线；
11. 单项指标最低线；
12. 置信区间方法；
13. 多重比较处理；
14. 是否要求不同深度分别达线；
15. 预算漏展开是否作为性能指标、限制项或单独门槛；
16. 允许的评测失败率；
17. 模型调用预算和费用上限；
18. 失败、超时、悬空请求如何计入预算；
19. 是否允许人工化学抽审，以及抽审范围；
20. 最终科学状态枚举和放行语义。

### 10.2 预注册最低内容

预注册文档至少包含：

```text
Preregistration:
  preregistration_id
  approval_status
  domain_definitions
  track_definitions
  source_group_policy
  split_policy
  leakage_policy
  reference_graph_version
  identity_matching_policy
  edge_matching_policy
  step_scope_policy
  condition_policy
  unknown_partial_policy
  endpoint_policy
  denominator_policy
  sample_size
  threshold_policy
  confidence_interval_policy
  multiple_comparison_policy
  budget_policy
  missing_data_policy
  failure_policy
  model_provider_policy
  cost_limit
  stop_rule
  change_control
```

### 10.3 样本量和通过线未冻结时

如果用户和 teacher 尚未裁定样本量或通过线：

- 可以交付完整预注册模板；
- 可以填写 `TBD_USER_TEACHER_DECISION`；
- 可以运行规则级 schema 和评分流程测试；
- 不得输出正式科学通过/不通过；
- 最终状态必须为 `pending_preregistration` 或 `pending_independent_data`；
- 不得使用当前 dev 结果反推样本量或通过线。

---

## 11. 判分流程

正式评测流程必须为确定性、可重放、零 LLM：

1. 读取冻结的评测 manifest；
2. 校验 run/profile/schema/policy identity；
3. 校验 native export 的内容身份和完整性；
4. 校验 reference graph 和 split manifest；
5. 执行泄漏检查；
6. 规范化结构、节点、边、参与物和条件表示；
7. 按冻结规则匹配节点；
8. 按冻结规则匹配反应边；
9. 检查 step scope；
10. 检查条件和场景范围；
11. 检查 provenance/source group；
12. 检查 endpoint、bookkeeping 和矿化声明；
13. 记录 unknown、partial、conditional 和未评估项；
14. 计算样本级指标；
15. 按预注册分层聚合；
16. 计算置信区间和覆盖率；
17. 输出误差分类和预算漏展开；
18. 生成确定性报告和 hash；
19. 由人工/teacher 按预注册结果裁定最终科学状态。

评测程序不得：

- 读取模型自由文本并进行语义裁判；
- 调用 LLM 修正答案；
- 根据预测结果修改参考图；
- 根据当前结果重新划分数据；
- 自动把 unknown 变成 negative；
- 自动把未画出的参考边变成错误；
- 自动把记录来源变成独立实验；
- 自动把部分结构匹配变成严格结构通过；
- 自动把工程 audit 结果变成科学观察结果。

---

## 12. 评测状态与放行语义

建议状态枚举：

```text
scientific_status:
  pending_no_independent_data
  pending_preregistration
  pending_user_teacher_decision
  interface_verified_only
  evaluated_not_passed
  evaluated_passed_with_scope
  blocked_data_integrity
  blocked_leakage
  blocked_scoring_contract
```

只有在以下条件全部满足后，才允许进入 `evaluated_passed_with_scope`：

- 题源和金标口径已裁定；
- 参考图已冻结；
- 数据划分和防泄漏检查通过；
- 研究来源组边界已冻结；
- 样本量和通过线已预注册；
- 判分程序零 LLM；
- dev/298 分开达到各自预注册要求；
- known/unseen 分开达到各自预注册要求；
- 评测覆盖率满足预注册；
- unknown/partial/预算漏展开已如实报告；
- 终点和矿化错误声明率符合预注册；
- 独立结果已由用户/teacher 裁定；
- 如涉及化学结构或金标口径，已完成相应 mimo/人工评审和互证。

“接口已验证”“规则级 fixture 通过”“S3 工程通过”均不能单独进入科学通过状态。

---

## 13. S5 实施前置条件

以下事项必须在正式科学评测开工前由用户或 teacher 裁定。

### 13.1 题源

- 使用哪些公开来源、数据库或研究集合；
- dev 和 298 各自的来源范围；
- 是否允许规则库作为支持来源；
- 研究来源身份不完整时如何处理；
- 哪些数据属于封存材料，不得读取。

### 13.2 金标口径

- 根对象的严格结构身份；
- 正确产物、共同产物和副产物；
- 反应边和 step scope；
- 条件要求与场景范围；
- endpoint 和矿化证据的最低口径；
- unknown、partial、conditional 的标注；
- 参考图不完整时的审查和排除规则。

### 13.3 数据分组

- source group 的独立性定义；
- 同研究相邻边的归并规则；
- route identity 的归并规则；
- known 与 unseen 的排除范围；
- 开发、调参、留出和独立确证的划分；
- 是否采用按根对象或按研究组的 group split。

### 13.4 样本量和统计

- 各题域和各轨道的最低样本量；
- 各指标的通过线；
- 置信区间方法；
- 小样本处理；
- 多重比较处理；
- 缺失、失败和不可判定样本的分母规则；
- 是否要求按深度单独达线。

### 13.5 预算与模型

- 是否允许真实 provider；
- 模型费用上限；
- 失败、超时、悬空请求是否扣预算；
- 是否允许重复采样；
- 重复采样如何报告；
- 真实模型默认关闭期间是否只进行 scripted/off 评测。

没有这些裁定时，只能完成接口、文档和规则级测试，不能启动正式科学性能实验。

---

## 14. 工程侧可先行部分

在不触碰金标、题面、封存结果和收费模型的前提下，可以先实施以下内容。

### 14.1 评测接口的合成规则级测试

使用自包含合成图和规则级路径，验证：

- 输入 schema 校验；
- native export 读取；
- reference graph 读取；
- 节点和边的确定性匹配；
- 共同产物不被报告 K 删除；
- 备选反应不被合并；
- distinct occurrence 不被 CN 合并；
- step scope 分开；
- 条件 conflict/unknown/compatible 分开；
- endpoint 和 search stop 分开；
- 矿化声明负控；
- budget omission 分开；
- unknown/partial 保留；
- 输出 hash 稳定；
- 同一输入重复评测得到相同结果；
- 损坏输入明确失败；
- 参考图缺覆盖时不自动判错；
- unseen 轨道不误报为 known 轨道。

这些测试只能证明评测器契约和程序行为，不能证明科学性能。

### 14.2 报告与归档格式

可以先冻结：

- evaluation manifest；
- reference graph manifest；
- split manifest；
- preregistration 模板；
- scoring policy 版本；
- missingness policy；
- 结果报告 schema；
- leakage report；
- 预算漏展开报告；
- 运行 provenance；
- 输入、输出和规则 hash；
- 版本、命令、cwd、环境和依赖记录。

工程证据应使用新批次根，旧封存 evidence 只读，不在永久证据目录原地运行会写库或写日志的探针。

### 14.3 预注册文档模板

可以先交付含 `TBD` 字段的模板，但必须明确：

- 哪些字段是用户/teacher 裁定；
- 哪些规则只是 proposed；
- 哪些阈值尚未冻结；
- 哪些指标只有接口定义；
- 哪些结果不得在冻结前对外发布。

---

## 15. S5 任务分批建议

### S5a：接口与数据规格

交付：

- 评测输入 schema；
- 参考图 schema；
- source group 和 split manifest schema；
- leakage check 规格；
- native export 消费契约；
- 输出指标 schema；
- preregistration 模板；
- 规则级合成测试；
- 无金标、无题面、无收费请求的接口报告。

边界：

- 不读取真实科学数据；
- 不冻结真实金标；
- 不输出科学指标；
- 不宣布 dev 或 298 性能；
- 科学状态为 `interface_verified_only` 或 `pending`。

### S5b：独立数据评测

只有在用户/teacher 完成题源、金标、样本量、阈值、预算和统计裁定后启动。

交付：

- 冻结数据清单；
- 参考图版本；
- source group 清单；
- split 和 leakage 证据；
- 预注册版本；
- 零 LLM 评测日志；
- dev/298 分开结果；
- known/unseen 分开结果；
- 置信区间和覆盖率；
- unknown/partial/预算漏展开报告；
- endpoint/mineralization 误声明报告；
- 用户/teacher 最终裁定记录。

---

## 16. S5 验收矩阵

| 编号 | 场景 | 必须观察到的结果 |
|---|---|---|
| S5-01 | 合成 reference graph 读取 | schema、版本和字段完整性确定性校验；缺字段明确失败 |
| S5-02 | A→B 与 A→C 两个备选反应 | 两条边保留为备选，不合并成 B+C 单一事件 |
| S5-03 | A 裂解共同生成 B+C | 一个完整事件含 B、C；报告 K 或展开宽度不删 C |
| S5-04 | 不同来路生成同一结构 | distinct occurrence 保留，不按 CN 或结构首现合并 |
| S5-05 | 多条数据库记录来自同一研究 | 只计一个 source group，不虚增独立支持 |
| S5-06 | 研究身份未知 | independence 为 unknown，不进入要求独立支持的指标分母 |
| S5-07 | 同研究相邻边跨开发/留出 | leakage 检查失败并阻止正式评测 |
| S5-08 | known 与 unseen 直接证据重叠 | unseen exclusion 检查失败，不继续聚合 |
| S5-09 | 未画出的参考边 | 不自动判模型错误，计入 reference coverage 限制 |
| S5-10 | 结构严格匹配但中心未知 | 严格身份和中心证据分轴报告，不授完整确认 |
| S5-11 | CN 相同但严格结构不同 | 不能计为严格结构命中 |
| S5-12 | step_scope 不同 | net reaction、elementary step、multistep summary 不混作同一边 |
| S5-13 | 条件必要项缺失 | 报 unknown，不报 compatible |
| S5-14 | 明确 essential 条件冲突 | 报 conflict，不把 unknown 混入冲突 |
| S5-15 | 历史来源条件与当前场景不同 | 保留 source condition，不改写为当前事实 |
| S5-16 | 模型输出 unknown/partial/conditional | 不计为 confirmed，也不自动计为错误 |
| S5-17 | 仅提出 CO₂、无根碳账和终点证据 | endpoint 不得判为矿化 |
| S5-18 | search stop 为 budget/depth | 不得改写为 terminal product 或 mineralization |
| S5-19 | 上游模型假设、下游 recorded | 上游 unresolved 依赖继承到末端，不被 recorded 洗白 |
| S5-20 | 预算导致未展开 | 单独报告 budget omission，不静默从分母删除 |
| S5-21 | dev 与 298 输入混合 | 评测器拒绝或分开生成结果，不产生无题域标签总分 |
| S5-22 | known 与 unseen 输入混合 | 评测器拒绝合并，轨道分别报告 |
| S5-23 | 样本量或通过线为 TBD | 状态保持 pending，不生成科学通过结论 |
| S5-24 | 同一输入重复评测 | 结果、指标和输出 hash 确定性一致 |
| S5-25 | 评测器输出被自然语言改变 | 零 LLM 判分；自然语言不能改变程序结果 |
| S5-26 | 收费 provider 默认配置 | 无用户授权时网络请求为零、费用为零、正式科学评测不启动 |
| S5-27 | 含金标产物写入普通目录 | 流程拒绝；金标内容只能进入授权的 gitignored 目录 |
| S5-28 | S4 native export 未交付 | 可验证接口，不运行正式科学评测，状态 pending |

---

## 17. 证据与归档要求

正式交付或接口评审至少记录：

- 实际 HEAD 和工作区差异；
- schema、profile、policy、evaluator 版本；
- 输入 manifest hash；
- reference graph hash；
- split manifest hash；
- preregistration hash；
- 评测命令、cwd、环境和依赖；
- 评测器 stdout/stderr；
- 逐样本结果；
- leakage 检查结果；
- 输入校验失败；
- unknown/partial/conditional 统计；
- budget omission；
- 参考图 coverage；
- dev/298、known/unseen 的分组结果；
- 费用和模型请求记录；
- 是否触碰真实题面、金标、封存 run 或外部模型；
- 任何人工或 mimo 化学评审的授权和 provenance。

评测程序应在隔离目录运行。  
不得在永久 evidence 目录直接创建 SQLite、缓存、日志或临时结果。  
不得用旧脚本硬编码的 HEAD 冒充当前执行版本。  
不得以测试总数替代逐项科学判定证据。

---

## 18. 完成定义

本任务书对应的 S5 规格完成，至少满足：

1. 已明确 S5 是数据与科学性能验收，不是工程完成证明；
2. 已明确工程绿数不得倒推科学通过线；
3. 已定义参考图/schema；
4. 已定义研究来源分组和防泄漏划分；
5. 已定义 known reconstruction 与 unseen inference 两条轨道；
6. 已定义 dev 与 298 两个题域的分开报告；
7. 已定义检索支持与未见推演的分开报告；
8. 已定义最小科学指标及覆盖率、未知和预算漏展开报告；
9. 已规定判分零 LLM；
10. 已列出样本量、阈值和统计方案的预注册要求；
11. 已明确哪些事项需要用户/teacher 裁定；
12. 已明确真实题面、金标、封存结果和费用的逐次授权边界；
13. 已明确无独立路径数据时保持 `pending`；
14. 已明确 S4 导出/分账接口是正式执行前置条件；
15. 已列出不碰金标的工程侧先行工作；
16. 已保留合法 unknown/partial/conditional，不用全面拒绝换取通过；
17. 已保留终点、矿化、来源和条件的证明范围边界；
18. 已规定工程接口验证不能写成科学性能通过。

最终科学结论只能在独立数据、冻结预注册、零 LLM 判分、无泄漏分组和用户/teacher 裁定全部具备后生成。此任务书本身不宣布任何 dev、298、路径命中率、泛化能力或科学放行结论。
