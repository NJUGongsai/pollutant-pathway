# FINAL DESIGN — Evidence-Grounded Reaction Analogy MCP Agent

> 日期：2026-07-29  
> 状态：**FINAL / 三模型一致批准**  
> 批准方：Qwen、Claude、ChatGPT  
> 工作范围：`CC/branch/ReactionAgent/demov2/`  
> 配套实施计划：`final_plan.md`  
> 决策记录：`final_discussion.md`  
> 当前执行授权：完成本文与 `final_plan.md` 后进入 P0 契约冻结；P0 Gate 通过后才进入 P1 数据地基实现。

---

## 0. 权威关系

本文件是 demov2 最终产品语义、科学边界、系统架构、数据对象、Agent 权限和 MCP 契约的唯一权威设计。

配套权威文件：

```text
final_design.md
final_plan.md
final_discussion.md
```

旧文件处置：

| 文件 | 地位 |
|---|---|
| `chatgpt-reaction-analogy-agent-design-v2.md` | 本文件的主要基线，降级为历史参考 |
| `chatgpt-reaction-analogy-agent-plan-v2.md` | `final_plan.md` 的主要基线，降级为历史参考 |
| `FUSION_DESIGN_V5.md` | Qwen 过程方案，历史参考 |
| `UNIFIED_DESIGN_REACTION_ANALOGY_AGENT_2026-07-29.md` | Claude 概念 quick reference，历史参考 |
| `UNIFIED_PLAN_REACTION_ANALOGY_AGENT_2026-07-29.md` | Claude 过程计划，历史参考 |
| ChatGPT v1 design/plan | 历史参考 |
| 三份早期 discussion | 审阅证据，不是实施规范 |

若旧文档与本文件冲突，以本文件为准。

---

## 1. 一句话目标

用户只输入未知分子 `X`。系统从冻结、版本化、可审计的反应证据中自适应检索与 `X` 结构相似的 donor 分子 `A`，读取 `A` 所参与的完整反应，沿 atom mapping 和 fragment-lineage graph 解析真实 transformed lineage `A→B`，把有证据支持的结构变化迁移到 `X` 的兼容位点，确定性生成和验证 one-step 候选产物 `Y`，最终输出 ranked strict top-K 或 typed abstention。

LLM 通过 MCP 真正参与：

- evidence action policy；
- donor/reaction evidence 扩展；
- 证据空间内 transformation/site 假设的选择、定型和优先级；
- 冲突证据比较；
- 停止检索决策；
- grounded explanation。

LLM 不拥有：

- 化学结构创建权；
- atom mapping 权；
- graph-edit 执行权；
- candidate identity 权；
- rank/lane/ledger/validation 修改权；
- structured abstention 最终裁决权；
- probability 自报权。

---

## 2. 产品问题与输出语义

### 2.1 系统回答的问题

> “在版本化反应库中，与 `X` 结构相似的 donor 分子发生过哪些完整反应？这些反应中哪些 `A→B` transformed lineage 具有可信映射？如果把其中可重放的结构变化迁移到 `X` 的兼容位点，能够生成哪些严格结构类比候选 `Y`？”

形式化表示：

```text
Input:
  X

Retrieve:
  A such that sim(X, A) is high
  and A is an eligible transformed participant

Donor evidence:
  R_donor:
  reactants(A, co_substrates, cofactors, ...)
  → products(B, coproducts, ...)

Resolve:
  A → B transformed lineage
  T = transformation hypothesis
  S_A = donor site
  Δ = canonical mapped graph edit
  L_source = SourceReactionLedger

Transfer:
  enumerate S_X conditioned on X, T, Δ and donor environment
  compile Δ at S_X
  generate Y deterministically
  construct L_candidate = CandidateAnalogyLedger

Decide:
  validated strict candidates
  → support/conflict
  → ranking/applicability
  → ranked top-K or typed abstention
```

### 2.2 条件性而非开放世界预测

输出语义是：

> “如果 `X` 发生与这些 donor 完整反应中已解析结构变化相同的 one-step structural analogy，则这些 `Y` 是可重放、可审计的候选。”

系统不声称穷尽真实世界所有反应，也不声称候选一定发生。

### 2.3 产品承诺

第一可靠版本承诺：

- 用户只输入 `X`；
- `A` 和完整 donor reactions 自动检索；
- donor 集自适应，不押注单一最近邻；
- `A→B` 沿完整反应的 fragment lineage 解析；
- strict candidates 来自确定性 graph edit；
- 每个候选有 donor/reaction/lineage/transform/site/ledger/provenance；
- 输出 ranked strict top-K；
- 无可靠候选时 typed abstain；
- snapshot、运行配置和 kernel 结果可重放；
- LLM 输出受 stable IDs 和 grounding guard 约束。

### 2.4 非承诺

第一可靠版本不承诺：

- 某个具体酶一定催化 `X→Y`；
- `X→Y` 在细胞、土壤、水体或其他环境中一定发生；
- 候选排序是生物发生概率；
- 预测 `Km`、`kcat`、转化率、产率或主次产物比例；
- 数据库未记录即“无反应”；
- generalized 与 strict 具有相同证据强度；
- 自动发现开放世界新反应；
- 单步结果可无条件递归成可靠多步路径。

校准前只允许：

```text
ranking_score
support_tier
evidence_strength
applicability_label
```

禁止：

```text
LLM confidence
biological_probability
enzyme_activity_probability
environmental_occurrence_probability
```

---

## 3. 不可协商的科学原则

1. 完整反应是事实单位；`A→B` 是其中一条 resolved transformed lineage。
2. 不允许在 reactant 和 product 两侧独立挑片段构造 `A/B`。
3. 一个反应可贡献多个 transformed lineages、split、merge 和 ambiguity sets。
4. `COFACTORS` 只能是 role/retrieval prior，不是删除规则。
5. 完整 reaction evidence 无损保留所有已记录 participants。
6. Atom mapping 是 formal correspondence；除非有机制证据，不自动等于 mechanistic atom origin。
7. Source reaction ledger 和 candidate analogy ledger 是两个不同对象。
8. Strict candidates 必须来自可信 mapping/lineage、满足 preconditions、可重放。
9. LLM 不直接生成或修复 SMILES。
10. 未通过 deterministic compiler/validator 的结构不得获得 candidate ID。
11. 数据库缺失不是 negative。
12. 没有 assay negatives 时不声称 enzyme inactivity。
13. `strict` 表示结构类比严格，不表示生物真实。
14. Benchmark retrieval/support/ranking reference 必须严格 train-only。
15. 旧 A1/A2、41.5%、23.5%、79.5% 等数字全部 provisional。
16. 第一个可靠版本只做 one-step strict lane。
17. Generalized、external evidence、research novel hypothesis graduation 和 multi-step 后置。
18. Scientific abstention 和 infrastructure failure 必须分开。
19. 多 LLM 投票不能替代独立数据、工具或实验验证。
20. 可审计 trace 不等于暴露 LLM chain-of-thought。

---

## 4. 统一术语

### 4.1 Query molecule

`X`：用户输入、需要预测 one-step structural analogy candidates 的分子。

### 4.2 Donor molecule

`A`：与 `X` 结构相似、在完整反应中拥有 eligible transformed lineage 的分子。

检索首先返回 distinct donor molecule identities，再加载每个 donor 的完整反应集合。

### 4.3 Complete donor reaction

`R_donor`：完整来源反应，包含所有已记录 participants、方向、stoichiometry、mapping、source 和 provenance。

### 4.4 Transformed lineage

`A→B`：fragment-lineage graph 中一条 transformed participant relation。

它不是：

- 两侧独立选择的“主分子”；
- 永远唯一的 primary pair；
- 整条完整反应的替代品。

### 4.5 Transformation

`T`：可解释 transformation family 或具体 transformation hypothesis。

`Δ`：canonical、可重放的 mapped graph edit，包含 preconditions 和 ledger requirements。

### 4.6 Site

`S_A`：donor 上发生变化的 mapped atom/bond set。

`S_X`：`X` 上满足 `T/Δ` preconditions 的候选应用位点。

### 4.7 Candidate

`Y`：由 deterministic graph-edit compiler 生成并通过 molecule 和 reaction-analogy validation 的候选结构。

### 4.8 Evidence lane

- `strict`：可信 mapped lineage、完整 strict preconditions 和可重放 graph edit。
- `generalized`：显式使用已注册 relaxation policy 的探索性候选，后置。
- `agent_proposed`：LLM 提出的 evidence space 外新 hypothesis，独立研究 lane。

### 4.9 Support 与 provenance

- `support`：支持某个 transformed lineage/transform/site/candidate 的独立证据。
- `provenance`：来源、版本、记录、许可和构建链。

重复数据库镜像、同一论文派生记录或同一 canonical reaction 不得伪造成多条独立支持。

---

## 5. 最终总体架构

```text
┌──────────────────────────────────────────────────────────────┐
│ User / Client                                               │
│ Input: X                                                    │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Constrained LLM Agent Policy                                │
│ evidence actions · evidence-space T/S selection · conflicts │
│ stop-search decision · grounded explanation                 │
└──────────────────────────────┬───────────────────────────────┘
                               │ high-level MCP
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Prediction Service / Versioned Decision Policy              │
│ request hash · lifecycle · budgets · immutable run           │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Deterministic Reaction-Analogy Kernel                       │
│ normalize → retrieve → lineage → transform → sites          │
│ → generate → validate → support/conflict → rank/abstain     │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Versioned Reaction Evidence Snapshot                        │
│ complete participants · mappings · lineage graph · ledgers  │
│ quality · provenance · quarantine · fold views              │
└──────────────────────────────────────────────────────────────┘
```

### 5.1 四类权威

| 权威 | 负责内容 |
|---|---|
| Evidence authority | snapshot 中存在的来源事实、完整反应和 provenance |
| Chemical execution authority | normalization、mapping、lineage、graph edit、validation |
| Agent policy authority | evidence actions、证据空间内 T/S 选择、冲突比较、何时停止检索 |
| Scientific decision authority | rank、lane、applicability、predicted/partial/abstained/failed |

### 5.2 强制 deterministic baseline

任何 production prediction 必须先运行：

```text
normalize X
→ automatic distinct-donor retrieval
→ complete reaction loading
→ eligible lineages/transforms
→ conditioned sites
→ deterministic candidate generation
→ validation
```

Agent 不能跳过 baseline 后凭自然语言作答。

---

## 6. 完整反应表示与 `COFACTORS`

### 6.1 Retrieval projection

用于找 donor `A`，可以：

- 降低常见 cofactor/carrier 的 donor eligibility；
- 排除明显无机 spectator；
- 使用大小、复杂度、mapping coverage 和 role；
- 防止 NAD(P)、ATP、H2O、O2 等抢占主要 donor 排名。

### 6.2 Complete reaction evidence

必须无损保留：

- 所有 reactants/products；
- cofactor、co-substrate、carrier、spectator；
- O2、H2O、CO2、NH3、H+、电子；
- 金属离子；
- stoichiometry；
- 方向；
- atom maps；
- source record；
- provenance。

### 6.3 `COFACTORS` 正式定位

允许：

```text
participant_role_prior
donor_eligibility_prior
retrieval_downweighting_prior
```

禁止：

```text
destructive reaction stripping rule
ground-truth participant role
atom-balance exclusion rule
```

小分子不等于不重要；它可能是 transferred atom source、leaving group、真实底物或副产物。

---

## 7. Evidence Snapshot

### 7.1 Snapshot 要求

Snapshot 必须：

- immutable；
- content-addressed；
- deterministic rebuild；
- source/provenance complete；
- 保存原始与规范化记录；
- 保存 mapper/resolver/schema versions；
- 支持 fold-specific train-only views；
- 显式保存 quarantine；
- 记录全部过滤前后数量和 reasons。

### 7.2 ReactionEvidence

```text
ReactionEvidence
├── reaction_id
├── source_record_id
├── source_name/version
├── source_uri_or_citation
├── raw_reaction
├── normalized_reaction
├── direction
├── participants[]
├── mapping_report
├── fragment_lineage_graph
├── resolved_transformed_lineages[]
├── ambiguity_sets[]
├── transformation_hypotheses[]
├── source_reaction_ledger
├── quality_report
├── provenance
├── snapshot_id
└── quarantine
```

不存在默认全局唯一的：

```text
primary_substrate
primary_product
```

如为兼容旧代码保留，只能标为：

```text
derived_legacy_projection
```

不得作为 canonical truth。

### 7.3 Participant

```text
ReactionParticipant
├── participant_id
├── molecule_id
├── canonical_smiles
├── side
├── stoichiometry
├── formal_charge
├── atom_map_numbers[]
├── mapped_fraction
├── changed_atom_fraction
├── role_hypotheses[]
├── donor_eligibility
└── provenance
```

角色词表：

```text
transformed_substrate
transformed_product
co_substrate
cofactor
carrier
coproduct
spectator
catalytic_species
unknown
```

角色可保留多个 hypotheses，不强迫伪造唯一真值。

---

## 8. Atom-Mapping Adapter

### 8.1 MappingReport

```text
MappingReport
├── mapper_name
├── mapper_version
├── mapper_parameters
├── input_hash
├── output_hash
├── mapping_status
├── mapped_heavy_atom_fraction
├── map_number_uniqueness
├── changed_atom_coverage
├── symmetry_ambiguity
├── resonance_tautomer_ambiguity
├── fallback_method
└── quality_flags[]
```

状态：

```text
fully_mapped
partially_mapped
unmapped
mapping_failed
mapping_ambiguous
```

`reacting_center.pkl` 或 center pairs 不能被称为完整 atom mapping。

MCS fallback 不能伪装成 strict mapped evidence。

### 8.2 Formal mapping 与 mechanism

Schema 必须区分：

```text
formal_mapped_source_assignment
source_assignment_method
source_assignment_quality
source_assignment_ambiguity
mechanistic_origin_evidence_ids
```

只有存在 curated mechanistic mapping、isotope tracing 或明确机制证据时，才允许：

```text
mechanistic_atom_origin
```

普通 mapper 的形式分配不得在 UI 中被写成已证明的机理事实。

---

## 9. Fragment-Lineage Graph

### 9.1 图定义

构建 reactant participants 到 product participants 的 bipartite graph。边特征至少包括：

```text
shared_mapped_heavy_atoms
reactant_retention_fraction
product_origin_fraction
changed_mapped_atoms
bond_edit_participation
transferred_atom_sets
scaffold_continuity
role_compatibility
mapping_quality
```

### 9.2 输出

```text
LineageResolution
├── graph
├── resolved_transformed_lineages[]
├── split_hypotheses[]
├── merge_hypotheses[]
├── atom_transfer_edges[]
├── ambiguity_sets[]
├── quality
└── failure_reason
```

规则：

- 不允许两侧独立挑片段；
- 不允许 tuple `max()` 静默解 tie；
- 多条明确 transformed lineage 可同时进入索引；
- 关键 ambiguity 进入 quarantine 或 non-strict diagnostic；
- 每条 lineage 有稳定 `lineage_id`。

### 9.3 必须覆盖的回归

```text
2-oxoglutarate + proline + O2
→ succinate + hydroxyproline + CO2
```

必须解析出：

```text
proline → hydroxyproline
2-oxoglutarate → succinate
formal O transfer assignment with method/ambiguity
```

不得构造：

```text
2-oxoglutarate → hydroxyproline
```

---

## 10. 双 Ledger 设计

### 10.1 SourceReactionLedger

表达来源数据库实际记录：

```text
SourceReactionLedger
├── reactant_entries[]
├── product_entries[]
├── role_assignments[]
├── stoichiometry
├── formal_atom_transfer_assignments[]
├── mechanistic_origin_evidence[]
├── added_atom_sources[]
├── removed_atom_sinks[]
├── element_balance
├── charge_balance
├── hydrogen_policy
├── proton_policy
├── electron_policy
├── cofactor_changes[]
├── source_completeness
├── mapping_completeness
├── balance_status
├── unknowns[]
└── evidence_ids[]
```

### 10.2 CandidateAnalogyLedger

表达 `X→Y` 结构类比在 donor context 下的形式账本：

```text
CandidateAnalogyLedger
├── source_ledger_id
├── query_candidate_adaptation_map
├── inherited_donor_context[]
├── inherited_assumptions[]
├── formal_atom_transfer_assignments[]
├── formal_balance_under_assumptions
├── unknown_actual_co_substrates[]
├── unknown_actual_cofactors[]
├── unknown_actual_stoichiometry[]
├── candidate_balance_status
├── unknowns[]
└── evidence_ids[]
```

Donor 使用某 cofactor 或计量，不等于真实 `X→Y` 已被证明使用相同条件。

### 10.3 正式状态

```text
fully_balanced_explicit_reaction
heavy_atom_balanced_with_implicit_h_e_policy
partial_or_unbalanced_source
```

### 10.4 Strict eligibility matrix

| 来源/账本状态 | Strict donor eligibility |
|---|---|
| fully balanced + reliable mapping/lineage | 允许 |
| heavy-atom balanced，仅 H+/e− policy 不完整 | 条件允许；保留状态 |
| 缺非关键 cofactor 计量，但 changed heavy atoms 可追踪 | 条件允许；标 partial 和缺失 |
| 新增/删除 changed heavy atom 无 formal source/sink | 禁止 strict |
| critical element/charge contradiction | quarantine |
| role ambiguity 不影响某条 resolved lineage | 允许局部使用该 lineage |
| lineage ambiguity 影响 A→B 身份 | 禁止 strict |
| direction unknown | 禁止 directional strict prediction |

每个新增 heavy atom 必须有 formal source assignment，或明确 `unknown_source`；需要明确来源而无法追踪时不得通过 strict。

---

## 11. Adaptive Donor Retrieval

### 11.1 两阶段单位

```text
X
→ retrieve distinct eligible donor molecules A
→ load complete reactions associated with each A
```

不能按 reaction rows 固定 top-K。

### 11.2 Eligibility

Donor 必须：

- 来自非 quarantine transformed lineage；
- 满足当前 lane 的 mapping/lineage quality；
- benchmark 中属于当前 fold 的 train evidence；
- 没有 identity leakage；
- 具有可解析 transform。

### 11.3 Baseline features

可以包括：

- Morgan/Tanimoto；
- scaffold similarity；
- functional-group overlap；
- size/heteroatom/charge compatibility；
- local environment similarity；
- role/donor eligibility；
- source quality；
- transformation diversity；
- donor identity diversity。

固定权重只能是 baseline；调整只能在 train/validation 上完成并做 ablation。

### 11.4 Adaptive stopping

可以依据：

- similarity gap；
- transformation stability；
- candidate stability；
- independent source diversity；
- evidence conflict；
- OOD；
- donor/tool/time budget。

必须保存：

```text
retrieval_rounds
retrieved_donor_ids
loaded_reaction_ids
stop_reason
budget_usage
```

---

## 12. Transformation Hypotheses

### 12.1 Canonical object

```text
TransformationHypothesis
├── transformation_id
├── source_lineage_ids[]
├── family_id
├── mapped_atom_edits[]
├── bond_deletions[]
├── bond_additions[]
├── bond_order_changes[]
├── atom_attribute_changes[]
├── transferred_atoms[]
├── donor_site
├── local_environment
├── strict_preconditions[]
├── allowed_relaxation_ids[]
├── ledger_requirements[]
├── mapping_quality
└── canonical_transform_hash
```

旧 coarse `edit_key` 只能命名为：

```text
legacy_edit_bucket
```

不能作为 canonical transformation identity。

### 12.2 Strict transform

要求：

- 可信 mapped lineage；
- graph edit 完全可重放；
- donor site 明确；
- preconditions 完整；
- formal changed-heavy-atom accounting；
- 无关键 ambiguity。

### 12.3 Generalized transform

后置，必须记录：

```text
relaxation_policy_id
allowed_relaxation_ids[]
failed_strict_conditions[]
generalization_distance
policy_version
```

LLM 不得用自由文本临时创造 relaxation rules。

---

## 13. Transformation-Conditioned Site Enumeration

位点近似：

```text
p(S_X | X, T, Δ, donor environment)
```

禁止无条件先枚举所有“反应性位点”再随机组合。

```text
SiteHypothesis
├── site_id
├── query_atom_ids[]
├── query_bond_ids[]
├── transformation_id
├── matched_preconditions[]
├── failed_preconditions[]
├── local_environment_similarity
├── symmetry_class
├── ambiguity_group
└── eligibility
```

要求：

- Stable site IDs；
- atom-order invariance；
- symmetric-site dedup；
- multiple valid sites 保留；
- 不只取第一个匹配。

---

## 14. Deterministic Candidate Generation

唯一允许的候选创建路径：

```text
validated TransformationHypothesis
+ eligible SiteHypothesis
→ versioned deterministic graph-edit compiler
→ molecule sanitizer
→ canonical candidate
```

具体 RDKit API 是实现细节。若使用 RunReactants/SMARTS，必须证明：

- 与 canonical edit 一致；
- site preconditions 一致；
- ledger requirements 一致；
- 输出可重放。

```text
GenerationReport
├── generation_id
├── transformation_id
├── site_id
├── edit_application_log[]
├── raw_product
├── canonical_product
├── changed_atoms[]
├── changed_bonds[]
├── sanitize_report
├── dedup_key
├── failure_code
└── component_version
```

相同 canonical product 合并，但保留所有 support paths。

必备回归：

```text
1-octanol: CCCCCCCCO
→ octanal: CCCCCCCC=O
```

不得少碳。

---

## 15. Validation

### 15.1 Molecule validation

- parse；
- sanitize；
- valence；
- aromaticity；
- formal charge；
- fragment policy；
- atom count；
- stereochemistry policy；
- canonicalization；
- input atom-order invariance。

### 15.2 Reaction-analogy validation

- edit 与 transform 一致；
- site preconditions 满足；
- donor/query correspondence；
- formal atom-source accounting；
- SourceReactionLedger linkage；
- CandidateAnalogyLedger；
- strict/generalized invariants；
- transformation scope 不越界。

### 15.3 Typed scientific abstention

```text
INVALID_INPUT
NO_IN_DOMAIN_DONOR
NO_RESOLVED_LINEAGE
NO_TRANSFERABLE_TRANSFORM
NO_COMPATIBLE_SITE
ALL_CANDIDATES_CHEMICALLY_INVALID
EVIDENCE_CONFLICT
INSUFFICIENT_SUPPORT
OUT_OF_DOMAIN
```

### 15.4 Typed system failure

```text
SNAPSHOT_UNAVAILABLE
MAPPER_UNAVAILABLE
TOOL_PROTOCOL_ERROR
STORAGE_FAILURE
BUDGET_CONFIGURATION_ERROR
```

System failure 不得变成 scientific abstention。

---

## 16. Support、Counterevidence 与 Applicability

### 16.1 Support

可包含：

- donor/query similarity；
- transform consistency；
- site environment similarity；
- independent donor/source count；
- mapping/lineage quality；
- ledger completeness；
- source provenance；
- candidate stability across retrieval rounds。

### 16.2 Counterevidence

第一版只允许：

- high-similarity donor 支持 competing transform；
- X 不满足 transform preconditions；
- site environment conflict；
- invalid generation；
- ledger contradiction；
- source direction/role/lineage conflict；
- supports 全部低质量或同源重复；
- strict 失败、只能显著 relaxation。

### 16.3 非 counterevidence

- 数据库没有记录；
- 没找到第二个酶；
- 相似分子未收录；
- 来源未报告阴性；
- 低频。

### 16.4 Structural applicability

```text
in_domain
near_domain
out_of_domain
conflicted
unknown
```

它描述结构类比适用域，不描述 enzyme activity。

---

## 17. Enzyme 与 DRFP

Enzyme/EC/UniProt 在 MVP 中只作为：

- donor provenance；
- reaction-class context；
- 用户可选证据；
- future enzyme-applicability input。

DRFP 若保留，命名为：

```text
reaction_space_similarity
drfp_reference_similarity
```

不得：

- 称 enzyme feasibility/probability；
- 因 DRFP 低否决 strict structural candidate；
- 把同一反应的多个 UniProt 计作独立 support；
- 访问 test fold reference。

未来 enzyme-applicability 模块独立设计，至少需要：

- enzyme identity/sequence；
- assay context；
- positive/negative activity；
- substrate scope；
- OOD/calibration。

---

## 18. Ranking 与 Scientific Decision

### 18.1 Tier-first

首版只有 strict production lane。

未来：

```text
Tier S: strict
Tier G: generalized exploratory
Lane A: agent_proposed experimental
```

不同 lane raw score 不横向混排。

### 18.2 Ranking features

- donor similarity；
- transform support；
- site compatibility；
- mapping/lineage quality；
- ledger completeness；
- evidence independence；
- source quality；
- conflict penalty；
- retrieval stability；
- generalized penalty（未来）。

固定权重是 baseline，不是概率。

### 18.3 Scientific decision authority

Versioned decision policy 是以下字段唯一权威：

```text
status
decision
reason_code
rank
lane
validation
applicability
```

Agent 可以停止检索并请求 decision，但不能覆盖 decision。

---

## 19. 两级 LLM Hypothesis 权限

### 19.1 ProductionSelectionHypothesis

用于 evidence-derived hypothesis space：

```text
ProductionSelectionHypothesis
├── support_reaction_ids[]
├── support_lineage_ids[]
├── transformation_id
├── site_id
├── rationale_summary
├── hypothesis_origin = agent_selected_from_evidence_space
└── policy_version
```

允许：

- 选择/定型/优先级；
- 证据扩展；
- 冲突比较；
- 决定何时停止检索。

不允许：

- 创建新 transform/site identity；
- 修改结构；
- 修改 rank/lane/ledger/abstention。

### 19.2 AgentProposedHypothesis

```text
AgentProposedHypothesis
├── support_reaction_ids[]
├── support_lineage_ids[]
├── transformation_family_id
├── typed_target_atom_or_bond_set
├── relaxation_policy_id | null
├── allowed_relaxation_ids[]
├── rationale_summary
├── hypothesis_origin = agent_proposed
└── policy_version
```

必须经过：

```text
support validation
→ registered vocabulary
→ compiler
→ site validation
→ graph edit
→ molecule validation
→ dual-ledger validation
→ grounding validation
```

通过后也只获得 `agent_proposed` candidate，不自动进入 production rank。

### 19.3 Graduation gate

独立 held-out 至少评估：

- incremental recall；
- added incorrect candidates；
- risk at fixed coverage；
- abstention impact；
- repeated-run agreement；
- grounding；
- invented ID/structure mutation = 0；
- cost/latency/tool calls；
- family/scaffold shift。

若引入 probability，再要求 Brier/ECE；没有 probability 时不伪造 calibration。

毕业需要：

- hypothesis class allowlist；
- policy/model/tool versions；
- benchmark evidence；
- ADR；
- human approval。

---

## 20. 强制审计 Trace

每个 frozen run 保存：

```text
D = donor/reaction evidence IDs
T = transformation hypothesis IDs
S = site hypothesis IDs
Δ = compiled graph-edit IDs
Y = candidate IDs
L = SourceReactionLedger/CandidateAnalogyLedger IDs
R = ranking/applicability
A = final decision/abstention
```

每阶段保存：

- typed input/output；
- evidence IDs；
- component/schema/policy versions；
- input/output hashes；
- failure code；
- metrics；
- timestamp/budget。

对用户展示 evidence card 和 rationale summary；不保存或暴露完整 chain-of-thought。

---

## 21. Scientific Lifecycle

```text
RECEIVED
→ NORMALIZED
→ BASELINE_EVIDENCE_LOADED
→ HYPOTHESES_COMPILED
→ SITES_ENUMERATED
→ CANDIDATES_VALIDATED
→ EVIDENCE_FUSED
→ DECIDED
→ FROZEN
```

终止：

```text
ABSTAINED
PARTIAL
FAILED
```

Agent 可循环：

```text
retrieve
↔ inspect reaction
↔ inspect transform/site
↔ expand evidence
↔ inspect conflicts
↔ request decision
```

生命周期是安全协议，不是强制 LLM chain-of-thought。

Frozen run：

- candidate set 不可修改；
- ranking 不可修改；
- manifest 可重复读取；
- expansion 创建 child run；
- report 只能引用 frozen IDs。

---

## 22. MCP Surface

### 22.1 MVP tools

```text
reaction.predict_analogical_products_v1
reaction.get_run_v1
reaction.get_candidate_evidence_v1
reaction.expand_evidence_v1
```

### 22.2 Internal/debug tools

```text
chem.analyze_structure_v1
reaction.analyze_diff_v1
reaction.get_details_v1
evidence.search_structured_v1
reaction.validate_hypothesis_v1
chem.validate_candidate_v1
enzyme.get_provenance_v1
```

`analyze_diff` strict 路径必须基于 mapped lineage；MCS 仅低可信 fallback。

### 22.3 PredictRequest

```json
{
  "query_smiles": "CCCCCCCCO",
  "snapshot_id": "snapshot_...",
  "requested_lanes": ["strict"],
  "top_k": 5,
  "client_request_id": "client_...",
  "idempotency_key": "idem_...",
  "budgets": {
    "max_donor_molecules": 20,
    "max_reactions": 100,
    "max_tool_calls": 12,
    "max_wall_time_ms": 30000
  }
}
```

### 22.4 PredictionResult

```text
PredictionResult
├── run_id
├── status
├── decision
├── normalized_query
├── snapshot_id
├── candidates[]
├── abstention
├── partial_reason
├── failure
├── stage_summary
├── manifest_uri
└── resource_uris[]
```

统一字段：

```text
manifest_uri
source_reaction_ledger
candidate_analogy_ledger
```

### 22.5 Invariants

```text
completed/predicted
  → candidates.length >= 1
  → abstention is null

abstained
  → candidates.length == 0
  → scientific reason_code present

partial
  → partial_reason present

failed
  → dependency/protocol/storage failure
  → not scientific abstention
```

### 22.6 Side effects

| Tool | Evidence corpus | Run store | Network | Idempotency |
|---|---|---|---|---|
| predict | read-only | append/write immutable run | no | request hash + snapshot/version + key |
| get_run | read-only | read-only | no | read-only |
| get_candidate_evidence | read-only | read-only | no | read-only |
| local expand_evidence | read-only | append child run | no | child request reuse |
| future external evidence | append augmentation provenance | append child/augmentation | yes | retrieval request/hash |

相同 key：

- same canonical request → same run；
- different request → typed conflict；
- concurrent calls → atomic dedup。

### 22.7 Resources

```text
reactionagent://runs/{run_id}
reactionagent://runs/{run_id}/manifest
reactionagent://runs/{run_id}/candidates/{candidate_id}
reactionagent://runs/{run_id}/evidence/{evidence_id}
reactionagent://snapshots/{snapshot_id}
```

IDs/URIs opaque；不得由 Agent 推导。

### 22.8 Grounding guard

- 所有 IDs 属于当前 frozen run；
- product/rank/ledger 从 typed result 渲染；
- unknown ID 拒绝；
- Agent 文本不能覆盖结构化字段；
- prompt injection 不能改变 snapshot/fold/permissions。

---

## 23. Reproducibility 与 Manifest

Manifest 至少记录：

```text
run_id / parent_run_id
request_hash
snapshot_id/hash
fold/view_id
normalization policy/version
mapper/resolver/compiler/validator/ranker versions
retrieval/ranking/abstention configs
hypothesis policy versions
tool schema/response hashes
agent prompt hash
model/provider/revision
temperature/seed
cache policy
budgets and usage
trace/correlation ID
timestamps
redaction policy
result hash
```

可重放级别：

```text
kernel_replayable
agent_trace_replayable
externally_non_replayable
```

Production benchmark 至少要求 kernel replayable。

---

## 24. Evaluation

### 24.1 Layer 0 — Data

- parse rate；
- mapping coverage/uniqueness；
- lineage accuracy；
- catastrophic mismatch；
- role accuracy/ambiguity；
- source/candidate ledger quality；
- quarantine；
- audit agreement。

### 24.2 Layer 1 — Retrieval

- donor molecule recall@K；
- donor reaction recall@K；
- transform-family coverage；
- donor/source diversity；
- adaptive cost；
- OOD detection。

### 24.3 Layer 2 — Transform/Site

- transform-family recall；
- exact edit recovery；
- lineage recall；
- site recall；
- strict precondition precision；
- site ambiguity。

### 24.4 Layer 3 — Generation/Validation

- valid molecule rate；
- canonical product recall；
- top-K candidate recall；
- graph-edit fidelity；
- equivalent-SMILES invariance；
- atom-order invariance；
- formal atom-source accounting；
- ledger status。

### 24.5 Layer 4 — Ranking/Abstention

- top-1/top-3/top-K；
- MRR；
- risk–coverage；
- selective accuracy；
- abstention rate/precision/recall；
- false confident answer rate；
- N/CI。

### 24.6 Layer 5 — Agent/MCP

- invented candidate/evidence IDs；
- unsupported claims；
- grounding rejection；
- protocol failures；
- repeated-run agreement；
- tool calls；
- latency/token/cost；
- evidence expansion gain；
- agent_proposed incremental value/error。

### 24.7 Multi-answer truth

```text
allowed_product_set
reaction/source context
tautomer policy
salt/neutralization policy
stereo-sensitive metric
stereo-agnostic metric
multi-product target policy
annotation completeness
```

### 24.8 Splits

```text
exact-X
scaffold
transformation-family
source
time
OOD/abstention challenge
```

Source/time 只有 provenance 质量达标才启用。

### 24.9 Leakage

每 fold：

```text
train evidence view
validation/calibration view
test labels
```

Retrieval、support、counterevidence、ranking reference 和 calibration 不得访问 test。

---

## 25. Pilot

正式 non-oracle pilot 必须在：

- audited mini snapshot；
- fixed mapping/lineage；
- frozen train/test split；
- train-only donor retrieval；
- multi-answer truth；
- automatic retrieval

之后运行。

人工可以审计 truth，不能在运行时挑 donor/T/site。

在此之前只允许：

- protocol/UI smoke test；
- prompt prototype；
- schema prototype；
- test preregistration。

---

## 26. 分阶段路线

```text
P0 Contract freeze
P1 Data foundation
P2 Mini snapshot / truth / fold isolation / pilot
P3 Strict one-step kernel
P4 Support / rank / applicability / abstention
P5 Full snapshot / rebuilt benchmark
P6 MCP
P7 Production grounded Agent
P8 Generalized
P9 Agent-proposed graduation / external evidence / multi-step
```

详细任务见 `final_plan.md`。

---

## 27. 首版验收门

进入 MCP/Agent 前至少：

1. 已知 A/B mismatch 修复或 quarantine；
2. critical ambiguity 不进入 strict；
3. `COFACTORS` 不造成 evidence 丢失；
4. formal mapping 不被表述为 mechanism；
5. dual ledgers 生效；
6. partial eligibility matrix 生效；
7. test evidence leakage = 0；
8. strict candidates 100% replayable；
9. equivalent SMILES/atom order invariance；
10. changed heavy atoms 有 formal source/sink；
11. system failure 不冒充 abstention；
12. all-X denominator；
13. multi-answer truth；
14. metrics 带 N/CI；
15. old metrics provisional。

进入 Production Agent 后还必须：

1. invented IDs = 0；
2. structure mutation = 0；
3. abstention override = 0；
4. failed→abstained confusion = 0；
5. schema adherence = 100%；
6. prompt injection 不改变权限；
7. budgets enforced。

---

## 28. 正式决策记录

| 决策 | FINAL |
|---|---|
| 输入 | 只输入 X |
| donor | adaptive distinct donor molecules |
| donor evidence | 完整反应，无损 participants |
| A→B | mapped fragment-lineage，不是独立片段选择 |
| COFACTORS | role/retrieval prior，不删除 |
| mapping source | formal assignment；mechanism 需额外证据 |
| ledger | SourceReactionLedger + CandidateAnalogyLedger |
| production LLM | evidence-derived T/S selection、evidence policy、conflict reasoning |
| novel LLM hypothesis | agent_proposed lane + graduation gate |
| structure generation | deterministic compiler |
| final decision | versioned deterministic decision policy |
| confidence | 禁止 LLM qualitative confidence |
| output | ranked strict top-K 或 typed abstention |
| enzyme | provenance/context；非 structural gate |
| generalized | 后置、独立 lane |
| external evidence | 后置、独立权限/provenance |
| multi-step | 单步达标后候选反应图 |
| audit trace | D→T→S→Δ→Y→L→R/A |
| benchmark | multi-answer、train-only、六层、N/CI |

---

## 29. 最终结论

最终系统是：

> **完整、无损、版本化的 donor 反应证据地基，驱动原子谱系正确的 `A→B` 解析；自适应检索为未知 `X` 找到可类比 donor；LLM 在真实 evidence-derived hypothesis space 中进行 T/S 选择、证据探索和冲突推理；确定性化学内核生成、验证和冻结 `Y`；新 LLM 假设进入独立 agent-proposed lane；版本化 decision policy 输出 ranked strict top-K 或 typed abstention；MCP 提供可审计、可重放、不可编造的交互边界。**

它同时满足：

- 用户只输入 `X` 的产品目标；
- `A→B` 来自自动 donor 检索和完整反应；
- LLM 真正参与推理；
- 化学结构生成可复现；
- 数据、账本和 benchmark 科学可信；
- 无可靠证据时诚实拒答；
- 后续 generalized、enzyme applicability、external evidence 和 multi-step 可独立扩展。

