# Qwen P0 Gate 执行提示词

> 用途：将本文件从“提示词正文”开始完整交给 Qwen。  
> 分工：Qwen 负责实施并运行 P0 Gate；ChatGPT 只在 Qwen 完成交付后进行独立审核，不参与本轮编码。

---

## 提示词正文

你现在是 ReactionAgent `demov2` 的 **P0 Gate 主实施者**。你的任务不是继续讨论方案，也不是实现预测系统，而是把已经达成一致的最终设计冻结为：

1. 六份具有明确约束力的 ADR；
2. 一套最小、严格、可导出 JSON Schema 的 Pydantic 数据合同；
3. 一组能够证明这些合同成立的自动化合同测试；
4. 一个可重复执行、失败即返回非零退出码的 P0 Gate；
5. 一份供 ChatGPT 独立审核的、逐项可追溯的证据报告。

**ChatGPT 本轮只负责后续审核。你必须独立完成实现、自检和证据整理，不要要求 ChatGPT 替你修改代码，也不要把未完成项标记为通过。**

---

# 1. 唯一工作目录与权限边界

唯一允许写入的目录是：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
```

所有新增或修改的代码、配置、文档、测试、Schema 导出文件和 Gate 报告，都必须位于这个目录内部。

必须遵守以下边界：

- `demov2` 以外的所有代码和文档一律视为只读参考，不得修改。
- 不得修改 legacy/旧版 ReactionAgent 的任何文件。
- 不得为了复用旧逻辑而把实现写回旧目录。
- 不得删除、覆盖、移动或重命名用户已有文件。
- 当前工作树可能包含未提交或未跟踪内容；它们都属于用户。只修改本任务明确需要且不存在内容冲突的文件。
- 不要执行 `git add`、`git commit`、`git push`、重置、清理或删除操作。
- 如果发现仓库级 `AGENTS.md` 或其他有效的项目指令，必须先完整阅读并遵守；如果它与本文或最终设计冲突，停止实施并报告冲突，不得自行决定优先级。

---

# 2. 开始编码前必须完整阅读的权威文件

按以下顺序完整阅读，不得只看标题、摘要或局部段落：

1. `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_design.md`
2. `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_plan.md`
3. `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_discussion.md`

这三份文件共同构成 P0 的权威输入，其中：

- `final_design.md` 定义系统语义、对象边界和科学合同；
- `final_plan.md` 定义 P0 任务、交付物和 Gate 验收条件；
- `final_discussion.md` 记录三模型融合时保留的约束、异议和最终裁决。

除非发现三份权威文件之间存在无法兼容的实质冲突，否则不得修改这三份文件。若发现冲突：

1. 停止所有会固化该冲突的实现；
2. 精确引用冲突文件、标题和行号；
3. 说明它会影响哪个 Schema、ADR 或 Gate 条件；
4. 将状态报告为 `BLOCKED_BY_AUTHORITY_CONFLICT`；
5. 不得静默选择其中一种解释。

旧 design、旧 plan、模型各自的讨论稿和早期指标只能作为历史背景，不能覆盖上述三份最终文件。

---

# 3. 先复述任务，再实施

编码前，在你的工作日志中先用简短文字确认以下理解：

- 用户输入是单一目标底物 `X`。
- donor 检索的目标是找到与 `X` 核心化学结构相似的 source substrate `A`。
- `A → B` 是从数据表读取的完整来源反应证据，不是临时拼出的半反应。
- 辅酶、常见小分子和非目标组分的处理必须服从最终设计中的 canonical identity、角色、来源反应和 ledger 语义。
- 系统最终要回答的是：基于严格的一步结构类比，`X` 可以转变成什么。
- P0 **不实现** donor 检索、`A → B` 变换抽取、`X → Y` 迁移、候选排序或真实预测，只冻结后续实现必须遵守的合同。

如果你的理解与最终权威文件不一致，以权威文件为准，并在报告中说明。

---

# 4. P0 严格范围

P0 只允许完成以下类型的工作：

- 权威性与范围 ADR；
- hypothesis lane ADR；
- mapping、source assignment、atom origin 与双 ledger ADR；
- partial eligibility matrix ADR；
- scientific decision authority ADR；
- MCP side-effect 与幂等语义 ADR；
- Pydantic v2 Schema skeleton；
- JSON Schema 导出；
- 合同测试；
- README 权威入口迁移；
- P0 Gate 执行器和证据报告。

P0 明确禁止实现：

- donor 结构检索算法；
- `canonical_identity.py` 的业务重写或迁移；
- RDKit 反应映射或图编辑算法；
- atom mapper、mechanistic atom origin 推断器；
- source reaction snapshot 构建器；
- transformation 抽取器；
- site 枚举或 site compatibility 算法；
- `X → Y` 候选生成；
- 化学有效性检查算法；
- 排序、评分、置信度模型；
- 预测 kernel；
- MCP server 或真正的 MCP tool handler；
- LLM Agent、LLM 调用或 prompt orchestration；
- generalized transfer；
- external retrieval；
- multistep search；
- 性能优化或 benchmark 结果声明；
- 用 placeholder、空列表或硬编码“假通过”模拟上述能力。

不要写 `TODO` 函数并返回 `[]`、`None`、虚构结果或 `pass` 来伪装这些能力已经存在。P0 没有业务算法就不要暴露相应的可调用业务接口。

---

# 5. 最小交付结构

你可以在不改变语义的情况下细化模块名，但必须保持结构简单、可读、可审核。建议的最小结构如下：

```text
demov2/
├── README.md
├── pyproject.toml
├── docs/
│   └── decisions/
│       ├── ADR-0001-authority-and-scope.md
│       ├── ADR-0002-hypothesis-lanes.md
│       ├── ADR-0003-ledger-and-source-semantics.md
│       ├── ADR-0004-partial-eligibility.md
│       ├── ADR-0005-scientific-decision-authority.md
│       └── ADR-0006-mcp-side-effects.md
├── reaction_agent/
│   ├── __init__.py
│   └── schemas/
│       ├── __init__.py
│       ├── common.py
│       ├── evidence.py
│       ├── mapping.py
│       ├── lineage.py
│       ├── ledger.py
│       ├── hypothesis.py
│       ├── candidate.py
│       ├── result.py
│       └── errors.py
├── schemas/
│   └── json/
├── scripts/
│   ├── export_json_schemas.py
│   └── run_p0_gate.py
├── tests/
│   └── contracts/
│       ├── test_authority_contract.py
│       ├── test_schema_strictness.py
│       ├── test_hypothesis_lanes.py
│       ├── test_ledger_contracts.py
│       ├── test_result_invariants.py
│       ├── test_partial_eligibility_contract.py
│       ├── test_mcp_side_effect_contract.py
│       └── test_json_schema_exports.py
└── reports/
    └── p0/
        ├── P0_GATE_REPORT.md
        └── P0_GATE_REPORT.json
```

要求：

- 如果合并某些 Python 模块能明显减少复杂度，可以合并，但不能漏掉任何合同。
- 不得创建多层抽象框架、插件系统、数据库层或运行时服务。
- P0 依赖应保持最小，优先只使用 Python 标准库、Pydantic v2 和 pytest。
- 不要因为 P0 Schema 不需要真实化学计算而引入 RDKit、数据库、向量库、Web 框架或 MCP SDK。
- `pyproject.toml` 必须提供明确、可重复的测试配置和 Python 版本约束。
- `run_p0_gate.py` 必须是检查器，不是修改器；Gate 运行时不得偷偷修复、重写或生成缺失的权威文档。
- JSON Schema 的导出可以由独立脚本显式执行；导出结果必须可重复、路径稳定，并纳入 Gate 检查。

---

# 6. 六份 ADR 的不可缺失内容

每份 ADR 至少包含：

- 标题；
- 状态；
- 日期；
- 背景；
- 决策；
- 明确不做什么；
- 数据或接口约束；
- 失败/拒绝行为；
- 后果与风险；
- 验收标准；
- 与权威设计和相关 Schema 的可追溯链接。

ADR 不得只复制任务清单，必须把语义写成后续开发者能够执行和测试的正式决策。

## ADR-0001：Authority and Scope

必须冻结：

- `final_design.md`、`final_plan.md`、`final_discussion.md` 是当前实现权威；
- 旧 design、旧 plan、讨论草稿和旧指标均为历史参考；
- 输入为单一目标底物 `X`；
- 输出目标是一跳、严格结构类比下的候选产物；
- 系统预测的是结构转化类比，不是酶可实现概率、环境可行性或实验成功概率；
- v1 不包含 generalized、external 和 multistep；
- 历史版本中的指标、阈值和性能声明在重新基准测试前均为 provisional。

README 必须只把三份最终文件列为权威入口。历史材料可以列在“非权威历史资料”中，但必须明确不能指导实现。

## ADR-0002：Hypothesis Lanes

必须冻结两个彼此独立且不可混用的 lane：

### `ProductionSelectionHypothesis`

至少表达：

- `support_reaction_ids`
- `support_lineage_ids`
- `transformation_id`
- `site_id`
- `rationale_summary`
- `origin = agent_selected_from_evidence_space`
- `policy_version`

规则：

- 只能选择证据空间中已经存在的 reaction、lineage、transformation 和 site ID；
- 不得携带自由形式的新变换或新位点；
- 不得引用不存在的 support ID。

### `AgentProposedHypothesis`

至少表达：

- `support_reaction_ids`
- `support_lineage_ids`
- `transformation_family_id`
- `typed_target_atom_or_bond_set`
- `relaxation_policy_id`，允许为空；
- `allowed_relaxation_ids`
- `rationale_summary`
- `origin = agent_proposed`
- `policy_version`

规则：

- 它是独立研究 lane，不是 production selection 的宽松写法；
- typed atom/bond target 必须由结构化字段表达，不能用自由文本替代；
- relaxation 只能使用注册 ID；
- AgentProposed 不得覆盖 production baseline；
- 未经 benchmark、ADR 和人工批准，不得进入 production ranking。

至少用合同测试证明：

- 未知 support ID 被拒绝；
- 未知 transformation/site ID 被拒绝；
- 自由文本 relaxation 被拒绝；
- 缺少或错误 `origin` 被拒绝；
- 两个 lane 的字段混用被拒绝；
- unknown fields 被拒绝。

如果“已注册 ID”的存在性不能仅靠单对象 Schema 判断，应设计最小的验证上下文或显式 registry contract，不要假装普通字符串类型已经完成存在性验证。

## ADR-0003：Ledger and Source Semantics

必须同时冻结 mapping/source 语义和双 ledger。

以下概念必须彼此独立：

- `formal_mapped_source_assignment`
- `mechanistic_atom_origin`
- `source_assignment_method`
- `source_assignment_quality`
- `source_assignment_ambiguity`
- `mechanistic_origin_evidence_ids`

强制原则：

- mapper 输出只能作为 formal mapping 或 source assignment 证据；
- mapper 输出不得自动升级为 mechanistic atom origin；
- mechanistic origin 必须有独立证据 ID；
- mapping quality、source ambiguity 和 mechanistic evidence 不得被压成一个“confidence”字符串。

必须定义两个 ledger：

### `SourceReactionLedger`

只记录 source reaction 的事实、显式缺失、平衡状态、角色、来源和证据。不得把 donor-derived 类比假设写成 source fact。

### `CandidateAnalogyLedger`

只记录从 donor/source 向目标 `X` 转移时形成的类比假设、变换引用、位点引用、来源关联、保留/丢弃的组分和警告。

必须冻结：

- source ledger 与 candidate ledger 的字段边界；
- candidate ledger 必须显式链接 source reaction/ledger；
- 辅酶、共底物、小分子和化学计量处理不能被凭空认定为 source fact；
- source 中的未知信息必须保留为未知，不能在 candidate 中静默补全；
- “被视为 spectator”与“已知不参与反应”不是同一事实。

## ADR-0004：Partial Eligibility

必须给出完整、机器可读或能够由测试解析的 eligibility matrix。至少覆盖：

- `fully_balanced`
- `heavy_atom_balanced`
- `missing_noncritical_cofactor_stoichiometry`
- `unknown_changed_heavy_atom_source`
- `critical_contradiction`
- `role_ambiguity`
- `lineage_ambiguity`
- `unknown_direction`

每一行必须明确：

- strict production eligibility；
- 必需 warnings；
- quarantine behavior；
- evaluation bucket；
- 是否可以进入非 production 的研究/诊断流程。

矩阵不能出现“视情况而定”但没有结构化判定依据的条目。若最终设计已经给出更准确的枚举名称，使用最终设计名称并在 ADR 中记录术语映射。

Source reaction 的 ledger 状态至少应覆盖或等价表达：

- `fully_balanced_explicit_reaction`
- `heavy_atom_balanced_with_implicit_h_e_policy`
- `partial_or_unbalanced_source`

## ADR-0005：Scientific Decision Authority

必须冻结：

- versioned decision policy 是 `status`、排序、lane、validation 和 applicability 的唯一最终裁决者；
- Agent 只能提出检索停止、补充证据或请求决策，不能自行宣布科学状态；
- 不允许 `"high" / "medium" / "low"` 等无合同的定性 confidence；
- 科学 abstention 与系统 failure 必须严格分离；
- 所有跨字段不变量必须由 Schema validator 和测试执行。

官方科学 abstention 枚举至少包括：

- `INVALID_INPUT`
- `NO_IN_DOMAIN_DONOR`
- `NO_RESOLVED_LINEAGE`
- `NO_TRANSFERABLE_TRANSFORM`
- `NO_COMPATIBLE_SITE`
- `ALL_CANDIDATES_CHEMICALLY_INVALID`
- `EVIDENCE_CONFLICT`
- `INSUFFICIENT_SUPPORT`
- `OUT_OF_DOMAIN`

官方系统 failure 枚举至少包括：

- `SNAPSHOT_UNAVAILABLE`
- `MAPPER_UNAVAILABLE`
- `TOOL_PROTOCOL_ERROR`
- `STORAGE_FAILURE`
- `BUDGET_CONFIGURATION_ERROR`

`PredictionResult` 至少执行下列不变量：

- `completed` 或等价 predicted 状态：至少一个 candidate，且没有 abstention reason；
- `abstained`：零 candidate，且必须有科学 abstention reason；
- `partial`：必须有结构化 `partial_reason`；
- `failed`：只能使用 dependency/protocol/storage/configuration 类 failure，不得伪装成科学 abstention；
- 不允许同一结果同时宣称 predicted 和 abstained；
- 不允许空列表同时配上成功状态。

## ADR-0006：MCP Side Effects

P0 不实现 MCP server，但必须冻结未来工具的副作用合同：

- `predict` 创建不可变 run；
- 每个 mutation request 必须携带 idempotency key；
- `get` 是只读操作；
- local expansion 创建 child run，不得改写 parent run；
- external retrieval 属于 post-MVP，并且是显式网络 I/O；
- 同一 idempotency key + 同一规范化请求必须复用同一结果；
- 同一 idempotency key + 不同请求必须返回冲突；
- 并发相同请求必须原子去重；
- 已完成 run 不得原地改写；
- side-effect、read-only、child-run 和 post-MVP network behavior 必须可由合同测试或结构化规范验证。

由于 P0 不实现 MCP handler，这里的测试应验证 ADR/Schema 中的正式合同，不得通过实现一个假 MCP 服务来“证明”合同存在。

---

# 7. 必须提供的 Schema skeleton

至少提供以下 Pydantic v2 模型、枚举或等价的严格 Schema：

- `ReactionEvidence`
- `MappingReport`
- `LineageResolution`
- `SourceReactionLedger`
- `CandidateAnalogyLedger`
- `TransformationHypothesis`
- `SiteHypothesis`
- `ProductionSelectionHypothesis`
- `AgentProposedHypothesis`
- `Candidate`
- `PredictionResult`
- scientific abstention enums
- system failure enums
- result status enums
- ledger/eligibility/source-assignment 相关 enums

Schema 必须遵守：

- 使用 Pydantic v2；
- 默认拒绝未知字段，例如统一基类采用 `extra="forbid"`；
- 尽可能启用 strict validation，避免 `"1"` 静默转为 `1`；
- ID、版本号和必填摘要不得接受空字符串；
- 枚举值稳定且可导出；
- 使用 discriminated union 或同等严格方式区分 hypothesis lane；
- lane 的固定 `origin` 必须由类型系统强制，而不是靠注释；
- 不允许把 typed atom/bond target 降级为自由文本；
- 不允许把 warning、reason、status、source quality 全部塞进任意字符串；
- 跨字段不变量必须使用 model validator 或同等机制执行；
- 每个顶层模型必须能够导出确定的 JSON Schema；
- JSON Schema 必须保留 `additionalProperties: false` 或同等 unknown-field 拒绝语义；
- Schema skeleton 只描述数据合同，不实现化学推理。

对 ID 是否存在的验证应区分两层：

1. **形状验证**：非空、类型正确、格式稳定；
2. **引用完整性验证**：ID 必须存在于本次 evidence/registry 上下文。

不要用正则表达式冒充引用完整性检查。为合同测试提供一个最小、明确的 registry/context validator 即可，不要建设数据库或 repository framework。

---

# 8. 合同测试最低覆盖要求

测试必须既有正例，也有反例。仅测试“模型可以实例化”不够。

至少覆盖：

## Authority

- README 只把三份 final 文件标记为权威；
- 六份 ADR 均存在并且状态明确；
- README 不把旧 design/plan/讨论稿标记为当前实现依据；
- 旧指标被明确标记为 provisional。

## Strict Schema

- unknown field 拒绝；
- 缺少必填字段拒绝；
- 空 ID 拒绝；
- 非法 enum 拒绝；
- 不安全的隐式类型转换拒绝；
- 所有顶层 Schema 成功导出为 JSON Schema。

## Hypothesis Lanes

- production 正例；
- agent-proposed 正例；
- lane mixing 反例；
- 错误 origin 反例；
- 未知 support ID 反例；
- 未知 transformation/site ID 反例；
- 未注册 relaxation ID 反例；
- 自由文本 relaxation 或自由文本 target 反例。

## Mapping and Ledger

- formal mapping 不会自动填充 mechanistic origin；
- mechanistic origin 没有 evidence ID 时拒绝；
- source 和 candidate ledger 不可混用字段；
- candidate ledger 缺少 source linkage 时拒绝；
- source 未知项不能被 Schema 默认为已知事实；
- ledger state 与 partial eligibility 语义一致。

## Prediction Result

- completed/predicted + 非空 candidates 通过；
- completed/predicted + 空 candidates 拒绝；
- completed/predicted + abstention 拒绝；
- abstained + 零 candidates + 科学 reason 通过；
- abstained + 非空 candidates 拒绝；
- abstained + system failure reason 拒绝；
- partial 缺少 partial reason 拒绝；
- failed 使用科学 abstention reason 拒绝；
- failed 使用系统 failure reason 通过。

## Partial Eligibility

- 矩阵中的每个规定行均存在；
- 每行都有 eligibility、warnings、quarantine 和 evaluation bucket；
- 不允许遗漏或重复状态；
- strict production eligibility 与最终设计一致。

## MCP Side Effects

- mutation、read-only、child run、external/post-MVP 四类语义均有正式定义；
- same key/same request = reuse；
- same key/different request = conflict；
- concurrent identical requests = atomic dedup；
- immutable parent/completed run 约束存在。

MCP 部分可以测试结构化 contract model、固定 policy spec 或 ADR 中的机器可核验标记；不得为了测试而写虚假的网络/MCP 实现。

---

# 9. P0 Gate 的执行合同

必须提供一个从 `demov2` 根目录可执行的单一 Gate 命令，例如：

```bash
python scripts/run_p0_gate.py
```

也可以额外提供等价的 project script，但 README 必须给出唯一推荐命令。

Gate 必须：

1. 检查六份 ADR 和三份权威文件；
2. 检查 README 权威链接；
3. 检查必要 Schema 可导入；
4. 重新导出或验证 JSON Schema；
5. 执行全部 P0 合同测试；
6. 对每一项 Gate 输出明确的 `PASS` 或 `FAIL`；
7. 任一检查失败时返回非零退出码；
8. 不捕获错误后仍返回成功；
9. 不依赖之前终端输出或人工口头判断；
10. 不修改权威文档、源码或测试来使自己通过。

P0 Gate 的十项总验收条件是：

1. 六份 ADR 完整且批准状态明确；
2. final docs 与 README 的权威关系一致；
3. 两条 hypothesis lane 的 Schema 无歧义且不可混用；
4. SourceReactionLedger 与 CandidateAnalogyLedger 边界无歧义；
5. partial eligibility matrix 完整；
6. formal mapping 与 mechanistic origin 的语义已冻结；
7. scientific decision authority 已冻结；
8. MCP side-effect 与幂等语义已冻结；
9. 旧指标均被标记为 provisional；
10. Pydantic/JSON Schema skeleton 通过全部合同测试。

禁止通过以下方式让 Gate 假通过：

- 跳过失败测试；
- 使用 `xfail`、`skip` 或捕获异常后继续；
- 把失败项只打印成 warning；
- 使用永远为真的占位检查；
- 只搜索一个关键词就宣称整份 ADR 合格；
- 生成空 JSON Schema；
- 在 Gate 执行过程中覆盖 expected 文件；
- 把未实现的算法结果硬编码进测试。

---

# 10. 实施顺序

按以下顺序工作：

1. 完整阅读权威文件和项目指令；
2. 盘点 `demov2` 现有文件和工作树状态；
3. 写一份简短的 P0 traceability checklist；
4. 先写六份 ADR；
5. 更新/创建 README 权威入口；
6. 写严格 Schema skeleton；
7. 写负例优先的合同测试；
8. 导出 JSON Schema；
9. 实现只读的 P0 Gate runner；
10. 运行格式/导入检查和全部合同测试；
11. 从干净的新进程再次运行单一 P0 Gate 命令；
12. 逐项核对最终设计，不因测试通过就跳过人工语义审阅；
13. 生成审核报告；
14. 停止，不进入 P1。

实现时优先简单、直接和可测试。不要建设 P0 不需要的抽象层。

---

# 11. P0 Gate 报告要求

生成：

```text
reports/p0/P0_GATE_REPORT.md
reports/p0/P0_GATE_REPORT.json
```

报告必须是实际执行结果，不是预先写好的模板。至少包含：

- 时间戳；
- Python 版本；
- Pydantic 和 pytest 版本；
- 工作目录；
- 权威文件列表；
- 修改/新增文件列表；
- 实际执行命令；
- 每条命令的退出码；
- 测试收集数、通过数、失败数、跳过数；
- 十项 P0 Gate 的逐项 `PASS`/`FAIL`；
- 每项对应的 ADR、Schema 和测试证据路径；
- 所有偏差、假设和已知风险；
- 是否存在未提交用户文件以及你如何避免覆盖；
- 最终结论。

JSON 报告必须结构化表达同样的 Gate 状态，不能只把 Markdown 全文塞进一个字符串字段。

只有全部条件真实通过时，结论才能写：

```text
READY_FOR_CHATGPT_AUDIT
```

只要有一项失败或没有证据，必须写：

```text
NOT_READY_FOR_CHATGPT_AUDIT
```

并列出阻塞项。

---

# 12. 最终回复格式

完成后，向用户提供以下内容：

## A. 实施摘要

说明 P0 做了什么，并明确声明没有进入 P1。

## B. 文件清单

列出所有新增和修改文件，不得省略生成的 JSON Schema 和报告。

## C. 验证证据

列出实际执行的命令、退出码、测试总数和 P0 Gate 最终退出码。

## D. 十项 Gate 结果

逐项给出：

```text
P0-G01 PASS/FAIL — 证据文件与测试
...
P0-G10 PASS/FAIL — 证据文件与测试
```

## E. 偏差、假设和风险

如果没有也要明确写“无”。不要隐藏你做出的解释性选择。

## F. 审核状态

仅在全部真实通过时输出：

```text
READY_FOR_CHATGPT_AUDIT
```

不得声称“生产就绪”“科学正确性已验证”“预测系统已完成”。P0 只证明设计合同已经被冻结并可自动验收。

---

# 13. 必须停止并报告的条件

出现以下任一情况，停止扩展实现并报告，不得自行越权：

- 三份权威文件存在会改变 Schema 或 Gate 结果的实质冲突；
- 需要修改 `demov2` 以外的文件才能继续；
- 现有用户修改与 P0 目标文件发生不可安全合并的重叠；
- 必须实现 P1 化学算法才能让当前测试通过；
- 关键依赖不可用且无法用现有环境运行验证；
- 需要联网下载、访问外部数据或调用外部模型；
- 某项 Gate 只能靠弱化最终设计才能通过；
- 无法证明某项检查真实执行。

停止时使用：

```text
BLOCKED_FOR_CHATGPT_REVIEW
```

并给出精确文件、行号、失败命令和最小待决问题。

---

# 14. 最终质量底线

你的产出必须满足：

- 语义忠于三份最终权威文件；
- P0 范围克制，不偷跑 P1；
- Schema 对非法输入默认拒绝；
- scientific abstention 与 system failure 完全分离；
- production selection 与 agent proposal 完全分 lane；
- formal mapping 不冒充 mechanistic evidence；
- source fact 不与 candidate analogy 混账；
- 所有成功状态都不能携带空结果；
- 所有 Gate 声明都有自动化证据；
- 所有结论都可以由 ChatGPT 在不修改代码的前提下独立复现。

现在开始：先阅读权威文件和项目指令，复述你的 P0 理解与文件计划，然后实施、运行 Gate、生成证据，最后停在 `READY_FOR_CHATGPT_AUDIT` 或明确的阻塞状态。

