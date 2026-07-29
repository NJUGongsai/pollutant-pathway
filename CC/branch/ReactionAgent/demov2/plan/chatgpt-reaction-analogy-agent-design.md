> **HISTORICAL / NON-AUTHORITATIVE**
> This document is retained for decision history only.
> Current implementation authority: `plan/final_design.md`, `plan/final_plan.md`, `plan/final_discussion.md`.

# ChatGPT Design — 受约束的反应类比 MCP Agent（demov2）

> 日期：2026-07-29  
> 状态：设计定稿，待用户复核后实施  
> 工作范围：`CC/branch/ReactionAgent/demov2/`  
> 用户已确认：自适应 donor 集；ranked top-K；主产物 + 完整反应账本；受约束混合 Agent；strict/generalized 双通道；版本化本地证据快照 + 外部证据增强。  
> 本文取代旧的“LLM 直接写 SMILES / 自行给置信度”和“继续冻结当前 benchmark/core”的路线。

---

## 1. 一句话目标

只给未知分子 `X`，系统从版本化反应库中自适应检索结构相似 donor `A`，读取其完整反应 `A→B`，提取可迁移的反应算子，在 `X` 上确定性地生成并验证候选产物 `Y`，最终由 LLM 通过 MCP 编排证据并解释 ranked top-K；证据不足时返回“没有可靠的结构类比候选”。

## 2. 产品承诺与非承诺

### 2.1 本系统承诺

系统回答：

> 如果 X 发生与所检索 donor A→B 相同或受控泛化的结构变化，可能形成哪些 Y？

输出是**结构类比候选**，每个候选必须可追溯到：

- 具体 donor 分子 A；
- 具体完整反应 A→B；
- A 与 B 的原子谱系；
- 被迁移的反应中心和图编辑；
- X 上的应用位点；
- 新增、删除或改变的原子/键；
- 共底物、辅因子与副产物账本；
- 化学验证结果、支持证据、反证和适用域。

### 2.2 本系统不承诺

本版本不声称：

- 某个酶一定能催化 X；
- X 在真实环境中一定发生该反应；
- 候选排名等于生物发生概率；
- 能预测转化率、产率、`Km`、`kcat` 或主次产物比例；
- 数据库没有记录就等于无反应；
- 单步候选可以无条件递归成可靠多步路径。

因此接口中只能使用 `ranking_score`。只有经过独立校准后才允许增加 `calibrated_probability`；不得输出未经校准的 `confidence` 或 `biological_probability`。

## 3. 严格审阅结论

### 3.1 现有代码解决的是传统检索—模板问题

当前实际代码主体是：

```text
X
→ 全分子 Morgan top-5 donor
→ SMARTS / align 模板迁移
→ DRFP-酶反应族相似度排序
```

`ReactionAgent` 当前没有可运行的 MCP server、Agent runtime、正式工具 schema、运行清单或 Agent benchmark。LLM+MCP 只存在于旧设计文档中。

### 3.2 当前 A/B 选择会构造错误监督标签

`benchmark/canonical_identity.py` 在反应物侧和产物侧分别独立选择“带中心且较大的非辅酶片段”，没有沿原子映射或 fragment lineage 配对 A 与 B。

现有报告已出现：

```text
2-氧戊二酸 + 脯氨酸 + O2
→ 琥珀酸 + 羟脯氨酸 + CO2
```

却被标成：

```text
X = 2-氧戊二酸
Y = 羟脯氨酸
```

所以当前 `group_key`、`edit_key`、A1/A2、generation recall 和 top-K 都必须视为 provisional，不能继续作为冻结地基。

### 3.3 当前 benchmark 还有关键证据问题

- `splits.build_groups()` 在拆分前丢弃无法构造 group 的反应，“全部 X 进分母”并未真正覆盖原始论域。
- scorer 参考反应没有严格限制为 train fold；只排当前 test group，仍可能读取其他测试反应。
- 同一个 X 可对应多个合理 Y；单标签 exact-match 会把其他条件下的真实产物记错。
- `EditScript.key()` 只保留粗粒度元素和键级变化，不能代表 canonical transformation identity。
- `generated_true→top5` 高不能单独证明排序已解决；需要 random、生成顺序和候选数控制基线。
- `COFACTORS` 只能帮助角色识别，不能通过删除片段来替代完整原子账本。

### 3.4 旧 CLAUDE 方案不可作为生产路线

旧方案让 LLM：

- 自己判断反应位点；
- 自己写产物 SMILES；
- 自己生成置信度；
- 在校验失败后重写结构；
- 使用仍有标签与泄漏问题的旧 benchmark 验收。

这会把不可复现的语言模型猜测放到化学内核中。新设计明确禁止 LLM 创造或修改结构、原子映射、排名分数和拒答状态。

## 4. 已批准的设计决策

| 决策 | 定稿 |
|---|---|
| 用户输入 | 只输入 X；A→B 由系统检索 |
| donor | 自适应 donor 集，不押注单一最近邻 |
| 输出 | 分层 ranked top-K，默认 top 5，可展开全部通过验证的候选 |
| 反应表示 | 主产物 Y + 完整反应账本 |
| LLM 权限 | 受约束混合 Agent；不创造结构和分数 |
| 泛化 | strict analogy + generalized analogy 双通道 |
| 数据源 | 版本化本地证据快照为主，外部 MCP 证据为可选增强 |
| 多步 | 架构预留；首个可靠版本只实现单步 |

## 5. 三种总体方案及取舍

### 方案 A：LLM-first 自由推理

LLM 阅读 donor、判断位点并直接写 Y。优点是开发快、表面上“智能”；缺点是结构幻觉、不可复现、无法校准、无法区分语言合理性和化学证据。否决。

### 方案 B：完全确定性流水线

固定检索、模板、排序和报告。优点是稳定；缺点是难以管理冲突证据、扩展外部来源和进行人机解释。可作为 baseline，不作为最终交互架构。

### 方案 C：受约束混合 Agent

确定性/可训练内核生成科学结果；LLM 调用少量高层 MCP 工具、请求更多证据并解释。兼顾可靠性、可扩展性和 Agent 体验。采用。

## 6. 总体架构

```text
用户输入 X
   │
   ▼
Conversation Agent
   │ 只能调用高层 MCP；不得创造候选
   ▼
reaction.predict_analogical_products_v1
   │
   ▼
确定性 Reaction Analogy State Machine
   │
   ├─ 1. normalize X
   ├─ 2. adaptive donor retrieval
   ├─ 3. load complete A→B records
   ├─ 4. role assignment + atom mapping + fragment lineage
   ├─ 5. extract strict/generalized transformation hypotheses
   ├─ 6. enumerate sites p(S | X, Δ, support)
   ├─ 7. apply graph edits
   ├─ 8. validate molecule + reaction ledger
   ├─ 9. retrieve support/counterevidence
   ├─10. rank within tiers + applicability gate
   └─11. freeze immutable run
   │
   ▼
ranked top-K / abstained / partial
   │
   ▼
LLM 只引用 candidate_id/evidence_id 解释
```

## 7. 核心组件

### 7.1 Reaction Evidence Store

保存冻结、版本化、可重放的完整反应记录。

```python
class ReactionRecord:
    reaction_id: str
    source: str
    source_record_id: str
    raw_reaction_smiles: str
    canonical_reaction_smiles: str
    reactants: list[ReactionParticipant]
    products: list[ReactionParticipant]
    atom_mapping: list[AtomMapPair]
    fragment_lineage: list[FragmentLineage]
    reaction_type: list[str]
    provenance: list[str]
    quality_flags: list[str]
    snapshot_id: str
```

`ReactionParticipant.role` 必须区分：

```text
target_substrate
co_substrate
cofactor
spectator
target_product
byproduct
unknown
```

不能再把 `COFACTORS` 当作删除列表。它是角色分类先验；完整记录始终保留。

### 7.2 Reaction Role and Lineage Resolver

职责：

1. 规范化完整反应；
2. 验证或建立 atom mapping；
3. 沿原子对应建立反应物片段到产物片段的 lineage；
4. 识别 donor 主底物 A；
5. 沿 lineage 确定其主产物 B；
6. 保存映射歧义，不静默选错。

决策顺序：

```text
可信原子映射
→ fragment atom-overlap lineage
→ mass/charge/role consistency
→ reacting-center support
→ MCS fallback（低可信，必须带 warning）
```

若 A/B 无法形成一致谱系，记录进入 `quarantine`，不得进入生产 donor 索引。

### 7.3 Adaptive Donor Retrieval

两阶段检索：

1. **宽召回**：全分子 Morgan/其他全局指纹取较大池，例如 100–300 条。
2. **受控选择**：根据全局相似度、骨架、官能团覆盖、局部环境和多样性选择 donor 分子集合。

输出单位是不同的 donor 分子 A，而不是反应行。选中 A 后读取 A 的全部合格完整反应。

建议初始特征：

```text
global_morgan_similarity
scaffold_similarity
functional_group_coverage
local_environment_best_similarity
donor_quality_score
source_diversity
```

MMR/分层配额用于去近重复；不得仅按反应记录出现频率堆满 top-K。

### 7.4 Transformation Hypothesis Builder

从每条完整 A→B 抽取：

```text
changed atoms and bonds
bond formation/break/order changes
atom additions/deletions and source participant
formal charge / hydrogen changes
aromaticity changes
stereochemical changes
reaction-center environment
edit preconditions
co-reactant/cofactor ledger
```

#### Strict hypothesis

- 来自可审计 atom mapping；
- edit preconditions 完整；
- X 位点满足元素、键型、芳香性、电荷、环/立体和局部拓扑约束；
- 由确定性图编辑回放。

#### Generalized hypothesis

- 共享反应类型或核心 edit；
- 明确记录放宽项，例如 radius、取代模式或局部拓扑；
- 独立排序并标记 `exploratory`；
- 不得与 strict 候选共享“可靠”描述。

### 7.5 Transformation-Conditioned Site Enumerator

禁止无条件预测 `p(site | X)`。位点必须条件化：

```text
p(S | X, Δ, donor environments, reaction type)
```

第一阶段采用可解释枚举：

1. 从 strict edit preconditions 构造查询；
2. 枚举 X 的全部匹配位点；
3. 对称位点 canonical 去重；
4. 计算 donor 中心与 X 位点的局部相似度；
5. 保留 competing sites。

学习型 site model 后续只能作为排序特征，不能绕过 edit preconditions。

### 7.6 Deterministic Candidate Generator

候选只能由工具生成：

- atom-mapped graph-edit replay；
- validated reaction SMARTS/template；
- generalized generator 仅输出到 generalized lane。

LLM 不得直接写或修改 SMILES。每个产物必须带：

```text
candidate_id
origin_transform_id
origin_donor_reaction_ids
query_site
applied_edit
canonical_product_smiles
generation_method
```

### 7.7 Chemical Validator and Reaction Ledger

验证分两层。

**分子层：**

- RDKit parse/sanitize；
- 价态；
- 芳香性；
- 形式电荷；
- 断裂片段政策；
- 立体化学政策；
- canonical identity。

**反应层：**

- atom mapping coverage；
- 元素/电荷账本；
- 新增原子来源；
- 共底物、辅因子与副产物；
- 反应方向；
- donor 源反应是否本身 unbalanced。

完整反应无法重建时可保留主产物，但只能标记：

```text
partial_reaction
unbalanced_source
unknown_atom_source
```

### 7.8 Evidence Fusion and Tiered Ranking

候选先分 tier，再在 tier 内排序。

Strict lane 可用特征：

```text
donor_global_similarity
site_local_similarity
edit_precondition_coverage
mapping_quality
reaction_record_quality
independent_support_count
counterexample_penalty
ledger_completeness
```

Generalized lane另加：

```text
generalization_distance
relaxed_constraint_count
reaction_type_support
```

初始规则分只能叫 `ranking_score`。每个特征必须原样输出，避免一个不可解释的总分。

### 7.9 Abstention

以下为正常业务结果，不是异常：

```text
NO_DONOR_IN_DOMAIN
NO_VALID_REACTION_RECORD
AMBIGUOUS_FRAGMENT_LINEAGE
NO_APPLICABLE_SITE
ALL_CANDIDATES_INVALID
ONLY_OUT_OF_DOMAIN_GENERALIZATIONS
CONFLICTING_EVIDENCE
INSUFFICIENT_EVIDENCE
```

“没有可靠候选”不等于“无反应”。

## 8. MCP 架构

### 8.1 面向 LLM 的高层工具

生产 Agent 默认只暴露：

```text
reaction.predict_analogical_products_v1
reaction.get_run_v1
reaction.get_candidate_evidence_v1
reaction.expand_external_evidence_v1
```

核心预测输入：

```json
{
  "query": {"structure": "CCCCCCCCO", "format": "smiles"},
  "mode": "database_augmented",
  "max_candidates": 5,
  "include_generalized": true,
  "stereochemistry_policy": "preserve_when_defined",
  "evidence_snapshot": "reaction-evidence-v1"
}
```

输出：

```json
{
  "schema_version": "1.0",
  "run_id": "run_...",
  "status": "completed",
  "canonical_query": "CCCCCCCCO",
  "candidates": [],
  "decision": {
    "kind": "predicted",
    "reason_code": null
  },
  "run_manifest_uri": "reactionagent://runs/run_.../manifest"
}
```

### 8.2 内部开发工具

仅调试/测试可见：

```text
chem.normalize_v1
reaction.resolve_roles_v1
reaction.extract_transform_v1
evidence.retrieve_donors_v1
chem.enumerate_sites_v1
chem.apply_edit_v1
chem.validate_candidate_v1
rank.rank_candidates_v1
```

### 8.3 MCP 结果纪律

- 使用严格 JSON Schema，`additionalProperties: false`；
- `structuredContent` 是权威结果，文本只作摘要；
- 所有工具只读、幂等；
- 业务 abstention 返回正常结果；
- 依赖故障返回明确可重试错误，不能伪装成“无候选”；
- 证据内容通过稳定 `evidence_id`/resource URI 引用；
- 外部数据库文本视为不可信数据，不能进入 system instructions。

## 9. LLM Agent 责任边界

### 9.1 允许

- 校验用户输入是否足够；
- 调用预测或证据扩展工具；
- 在 strict/generalized 候选之间解释差异；
- 引用工具生成的 candidate/evidence IDs；
- 解释警告和拒答原因；
- 建议用户查看哪项证据。

### 9.2 禁止

- 自己解析或修复 SMILES；
- 自己做原子映射；
- 自己决定合法价态、守恒或立体化学；
- 创造或修改候选 Y；
- 生成新 donor、EC、UniProt、文献或 evidence ID；
- 改写工具排名、分数或 abstention；
- 把 ranking score 表述为发生概率；
- 依靠多个 LLM 投票代替独立实验/模型证据。

最终答案中的每个结构必须引用本次 run 的 `candidate_id`。Host 在输出前验证 ID 存在。

## 10. 运行时状态机

```text
RECEIVE
→ NORMALIZE
→ RETRIEVE_DONOR_MOLECULES
→ LOAD_COMPLETE_REACTIONS
→ RESOLVE_ROLES_AND_LINEAGE
→ BUILD_TRANSFORMATION_HYPOTHESES
→ ENUMERATE_QUERY_SITES
→ APPLY_EDITS
→ VALIDATE_PRODUCTS_AND_LEDGER
→ RETRIEVE_SUPPORT_AND_COUNTEREVIDENCE
→ RANK_WITHIN_TIERS
→ APPLICABILITY_GATE
→ FREEZE_RUN
→ REPORT
```

每一状态保存输入、输出、版本、耗时、错误码和哈希。LLM 不推进科学状态，只触发高层动作。

## 11. 输出契约

```python
class Candidate:
    candidate_id: str
    tier: Literal["strict", "generalized"]
    product_smiles: str
    reaction_site: list[int]
    transformation_type: list[str]
    edit: AtomMappedEdit
    donor_reaction_ids: list[str]
    reaction_ledger: ReactionLedger
    validation: ValidationReport
    applicability: Literal["in_domain", "borderline", "out_of_domain"]
    ranking_score: float
    score_components: dict[str, float]
    evidence_ids: list[str]
    counterevidence_ids: list[str]
    warnings: list[str]
```

默认输出顺序：

1. strict / in-domain；
2. strict / borderline；
3. generalized / exploratory；
4. out-of-domain 候选默认不进 top-K，只在诊断中保留。

## 12. 数据策略

### 12.1 版本化快照

每个 snapshot 保存：

- 原始来源版本；
- 标准化代码版本；
- RDKit 版本；
- atom-mapping 版本；
- quarantine 记录；
- 质量统计；
- 内容 hash；
- 构建时间。

### 12.2 外部证据

Rhea、EnzymeMap 等可作为原始来源或运行时增强。外部新证据：

- 单独标记来源和时间；
- 不直接进入已校准主索引；
- 不在 benchmark 中读取隐藏答案；
- 审核后随下一版快照发布。

## 13. 评估设计

### 13.1 Layer 0：数据正确性

- participant role accuracy；
- A→B lineage accuracy；
- atom-map coverage；
- balanced/partial 分类准确率；
- 已知错误案例必须修复；
- 分层人工抽样审计及置信区间。

### 13.2 Layer 1：donor retrieval

- relevant donor molecule recall@K；
- transformation coverage@K；
- donor diversity；
- duplicate sensitivity；
- counterevidence recall。

不能再用粗 `edit_key` 单独定义“正确 donor”。

### 13.3 Layer 2：transformation/site

- strict edit exact match；
- site recall@K；
- edit precondition precision；
- mapping ambiguity rate；
- generalized distance 分桶。

### 13.4 Layer 3：candidate generation

- product exact-match top-K；
- chemical validity；
- reaction ledger completeness；
- stereo-sensitive / stereo-agnostic 分报；
- invalid candidate rate；
- generation recall。

### 13.5 Layer 4：ranking/abstention

- MRR、nDCG、top-K；
- risk–coverage/selective accuracy；
- abstention reason precision；
- OOD detection；
- 若校准：Brier/ECE。

### 13.6 Layer 5：Agent/MCP

- 工具选择正确率；
- schema adherence；
- provenance completeness；
- tool-output grounding；
- hallucinated structure/evidence count 必须为 0；
- replay determinism；
- 故障时是否错误报告“无候选”。

### 13.7 拆分

至少包括：

- random sanity；
- query scaffold split；
- atom-mapped transformation-family split；
- exact-X isolation；
- source/database split；
- time split；
- 环境污染物外部集。

所有 scorer/reference evidence 必须严格来自 train snapshot/fold。

## 14. 处置现有资产

### 保留并重验

- RDKit pipeline；
- reacting center 原始资产；
- `align_transfer` 的 graph-edit replay 思路；
- 漏斗与失败归因原则；
- Morgan baseline；
- DRFP 作为一个弱排序特征；
- LLM 不直接生成 SMILES 的历史原则。

### 必须重建

- `canonical_identity.transformed_pair()`；
- fragment role/lineage；
- canonical reaction identity；
- split 前论域统计；
- train-only evidence 隔离；
- candidate hit policy；
- transformation identity；
- benchmark 和全部基线数字。

### 降级

- site-driven retrieval：一个候选召回特征，不是总架构；
- `EditScript.key()`：粗分桶键，不是真值；
- DRFP-酶 max：弱特征，不是置信度；
- MCS：低可信 fallback；
- EC/UniProt：provenance，不代表 X 会反应；
- 旧 `CLAUDE_DESIGN`：对照文档，不作为实施依据。

## 15. 分阶段交付

### Phase 0：数据与 benchmark 地基

修复角色、lineage、泄漏和多答案；产出 versioned snapshot 与数据审计报告。

### Phase 1：Strict analogy kernel

完成 adaptive donor、严格 transform、条件化 site、确定性 replay、验证、反应账本和 top-K。

### Phase 2：Generalized lane 与排序

增加受控泛化、独立评分、counterevidence、适用域和 abstention。

### Phase 3：MCP + LLM Agent

把已验证内核封装为高层 MCP；LLM 只做证据编排和解释；完成 Agent benchmark。

### Phase 4：多步候选图

只有单步达到验收后才实施。多步使用带 provenance 的分支图，并传播适用域和不确定性，不采用默认五步单线。

## 16. 第一版本验收门

进入 MCP/LLM 阶段前必须满足：

- 已知 A/B 错配案例全部进入回归测试；
- 分层人工审计达到预设角色/lineage 准确率；
- test scorer 证据严格 train-only；
- strict 候选 100% 来自确定性工具；
- invalid structure 不进入输出；
- 每个候选有 donor、edit、site、ledger 和 evidence IDs；
- top-K 指标在多种 leakage-safe split 上报告；
- 无可靠候选时能返回稳定 reason code；
- 旧 P0 与新 P0 不混用、不把 provisional 数字继续作为承诺。

## 17. 参考依据

- MCP Tools/structured output/error semantics：<https://modelcontextprotocol.io/specification/2025-11-25/server/tools>
- MCP Schema 与 tool annotations：<https://modelcontextprotocol.io/specification/2025-11-25/schema>
- EnzymeMap：<https://doi.org/10.1039/D3SC02048G>
- ECREACT：<https://www.nature.com/articles/s41467-022-28536-w>
- BioTransformer 3.0：<https://doi.org/10.1093/nar/gkac313>
- CATNIP substrate-scope study：<https://www.nature.com/articles/s41586-025-09519-5>
- Molecular Transformer：<https://doi.org/10.1021/acscentsci.9b00576>

---

## 18. 最终设计结论

新主线不是“让 LLM 比模板更会猜 SMILES”，也不是“继续提高粗 edit 的检索召回”，而是：

```text
X
→ 自适应检索可靠的完整 A→B 证据
→ 建立正确反应角色和原子谱系
→ 抽取可审计 transformation
→ 在 X 上做 transformation-conditioned site 匹配
→ 确定性生成 strict/generalized 候选
→ 分子与反应账本验证
→ 分层排序、适用域和拒答
→ MCP 暴露稳定结构化结果
→ LLM 只做证据编排与解释
```

这是与用户目标一致、可验证、可复现并能逐步扩展为多步路径的 demov2 架构。
