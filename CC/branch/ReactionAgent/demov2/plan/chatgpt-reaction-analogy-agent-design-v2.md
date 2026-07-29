> **HISTORICAL / NON-AUTHORITATIVE**
> This document is retained for decision history only.
> Current implementation authority:
> - plan/final_design.md
> - plan/final_plan.md
> - plan/final_discussion.md


# ChatGPT Design v2 — Evidence-Grounded Reaction Analogy MCP Agent

> 日期：2026-07-29  
> 状态：三模型 design、plan 与 discussion 融合后的权威设计  
> 工作范围：`CC/branch/ReactionAgent/demov2/`  
> 配套计划：`chatgpt-reaction-analogy-agent-plan-v2.md`  
> 取代关系：本文件取代 ChatGPT v1 design，并作为 Claude、Qwen、ChatGPT 三套方案的统一裁决。旧 design、plan 与 discussion 只保留为决策过程记录。  
> 首版范围：可靠、可审计、可拒答的 **one-step structural reaction analogy**；generalized、外部开放世界证据和 multi-step 后置。

---

## 0. 执行摘要

### 0.1 一句话目标

用户只输入未知分子 `X`。系统从版本化本地反应证据中自适应检索与 `X` 结构相似的 donor 分子 `A`，读取 `A` 参与的完整反应，沿原子映射和 fragment lineage 解析其中的 `A→B` 变化，把可迁移的结构变化应用到 `X` 的兼容位点，确定性生成和验证 ranked top-K 候选产物 `Y`；证据不足、谱系歧义或结构迁移不成立时可靠拒答。

### 0.2 最终架构裁决

本系统不是“LLM 自由写产物”，也不是“传统管线算完、LLM 只复述”。最终权责是：

> **LLM Agent 负责受约束的证据策略和假设管理；确定性化学内核负责结构执行、硬约束验证和候选身份；版本化证据层负责可追溯事实；校准后的决策层负责排序与拒答。**

### 0.3 三模型融合结果

| 来源 | 正式吸收 | 明确否决或修正 |
|---|---|---|
| ChatGPT | fragment-lineage 修复、完整 Reaction Ledger、snapshot/quarantine、防泄漏、strict/generalized、grounding、分层评估 | v1 中把 LLM 过度限制为最后解释器；单一 primary lineage；过弱 ledger；过早 generalized/MCP |
| Claude | `D→T→S→Δ→Y→L→R/A` 阶段变量、漏斗归因、selective evaluation、单步优先 | LLM 直接写 SMILES；LLM 自报置信度；把六跳当固定 chain-of-thought |
| Qwen | 结构化分析工具、adaptive evidence exploration、低成本 pilot、成本/延迟观测 | 人工挑 donor 的 oracle pilot；默认全量旧数据可信；把酶支持设为结构候选的强制闸 |

### 0.4 不可协商的原则

1. `A→B` 来自检索到的完整 donor 反应证据，不由 LLM 编造。
2. 完整反应是事实单位；`A→B` 是其中一条经过谱系解析的 transformed lineage，不是两侧各挑一个分子。
3. `COFACTORS` 只能作为 participant-role 和 donor-retrieval 先验，不能从完整反应证据中破坏性删除。
4. LLM 不直接创建、修复或修改 SMILES、原子映射、图编辑结果、候选 ID、分数或概率。
5. 未通过确定性 compiler/validator 的结构不得获得 `candidate_id`。
6. 数据库缺失不是负证据；没有 assay negative 时不声称酶不活跃。
7. `strict` 表示结构类比严格，不表示该酶一定催化或环境中一定发生。
8. benchmark 的检索、support 和 ranking reference 必须严格 train-only。
9. 旧 A1/A2、41.5%、23.5%、79.5% 等数字在数据和 benchmark 重建前全部为 provisional。
10. 第一个可靠版本只做 one-step；一步未达标前不进入多步。

---

## 1. 任务定义

### 1.1 用户真正提出的问题

本系统回答：

> “在版本化反应库中，与未知分子 `X` 结构相似的 donor 分子发生过哪些完整反应？如果把其中有可靠原子谱系支持的结构变化迁移到 `X` 的兼容位点，`X` 可能形成哪些结构类比产物？”

形式化表示：

```text
输入：
  X

检索：
  retrieve A such that sim(X, A) is high and A is an eligible transformed participant

donor 事实：
  R_donor:
  reactants(A, co_substrates, cofactors, ...) 
  → products(B, coproducts, ...)

解析：
  A → B
  T = transformation family
  S_A = donor reaction site
  Δ = atom-mapped graph edit
  L = complete reaction ledger

迁移：
  enumerate S_X conditioned on X and T
  compile Δ at S_X
  deterministically generate Y

输出：
  ranked top-K {Y_i}
  + donor evidence
  + transformation/site/edit evidence
  + ledger
  + lane
  + applicability
  + typed abstention when needed
```

### 1.2 条件性而非开放世界预测

输出语义是：

> “如果 `X` 发生与已检索 donor 反应相同或明确受控泛化的结构变化，则这些 `Y` 是可验证的结构类比候选。”

系统不是从所有可能化学反应中无约束搜索，也不声称穷尽真实世界所有产物。

### 1.3 产品承诺

首版承诺：

- 输入只需要 `X`；用户不需要提供 `A→B`。
- donor `A` 和完整反应由系统自动检索。
- donor 集自适应扩展，不押注单一最近邻或固定 top-K。
- 每个候选 `Y` 都来自可重放的结构生成过程。
- 每个候选都能追溯到具体 snapshot、reaction、lineage、transform、site 和 validation。
- 输出 ranked top-K，默认展示 top 5。
- 能明确区分 strict structural analogy 和 generalized structural analogy。
- 数据或证据不足时能够 typed abstain。
- 相同 snapshot、配置和固定运行参数可重放。

### 1.4 非承诺

首版不承诺：

- 某个具体酶一定接受 `X`；
- 反应在细胞、土壤、水体或其他环境中一定发生；
- 候选排名是生物发生概率；
- 预测反应速率、产率、主次产物比例、`Km` 或 `kcat`；
- 数据库没有记录就代表不能反应；
- generalized 候选和 strict 候选具有相同证据强度；
- 单步候选可无条件递归成可靠多步降解路径；
- 不完整来源反应能够被自动补成真实完整计量反应。

接口在完成独立校准前只允许使用：

```text
ranking_score
support_tier
applicability_label
```

不得把它们命名为：

```text
confidence
biological_probability
enzyme_activity_probability
```

---

## 2. 统一术语和科学对象

### 2.1 Query molecule

`X`：用户输入、需要预测结构类比产物的分子。

### 2.2 Donor molecule

`A`：从 evidence snapshot 中检索到、与 `X` 结构相似、并在某条完整反应中具有 transformed participant lineage 的分子。

donor 检索的基本单位先是 **distinct molecule identity**，再加载该分子的完整反应集合。不能让同一高频分子的重复记录淹没 donor 多样性。

### 2.3 Complete donor reaction

`R_donor`：包含全部已知 reactants、products、stoichiometry、方向、来源、原子映射和 participant-role hypotheses 的完整来源反应记录。

### 2.4 Transformed lineage

`A→B`：在完整反应中由 fragment-lineage graph 支持的一条 transformed participant 关系。一个完整反应可以有：

- 一条主 transformed lineage；
- 多条并行 transformed lineage；
- 多底物汇合到一个产物；
- 一个底物裂解为多个产物；
- 无法唯一解析的歧义 lineage。

因此，不再假设每条反应都有唯一的全局 `primary_pair`。

### 2.5 Transformation

`T`：可解释的 transformation family，例如 oxidation、hydroxylation、hydrolysis、dealkylation。它是分组和解释层概念，不等于完整图编辑。

`Δ`：从 mapped `A→B` 中提取的具体、可重放 atom/bond graph edit。

### 2.6 Site

`S_A`：donor `A` 上发生变化的 mapped atom/bond 集。

`S_X`：在 `X` 上满足 `T` 和 `Δ` 前提条件的候选应用位点。

### 2.7 Candidate product

`Y`：由确定性 graph-edit compiler 在 `X` 的 `S_X` 上生成并通过验证的候选结构。

### 2.8 Reaction Ledger

`L`：完整 donor 反应及类比候选反应的参与者、计量、原子来源、元素/电荷、质子/电子策略和完整性状态账本。

### 2.9 Lane

- `strict`：可信 mapped lineage 上的精确结构变化回放，且查询位点满足全部 strict preconditions。
- `generalized`：只放宽预注册约束并显式记录距离的探索性类比。

### 2.10 Evidence、support 和 provenance

- `evidence`：支持系统中某个事实的可定位记录。
- `support`：支持某个候选的独立 transformed lineage 或来源。
- `provenance`：证据的来源、版本、许可、导入时间和变换记录。

重复数据库条目、同一论文的镜像记录或同一反应的派生版本不能被错误计作多条独立支持。

---

## 3. 总体架构

```text
┌────────────────────────────────────────────────────────────────────┐
│ User / Client                                                     │
│ input: X; optional display preferences                            │
└──────────────────────────────┬─────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│ Constrained LLM Agent Policy                                      │
│ - decide which evidence action to take next                       │
│ - compare returned donor/transform hypotheses                     │
│ - request structured expansion within budget                      │
│ - report only validated IDs                                       │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ high-level MCP
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│ Prediction Service / Scientific Lifecycle                         │
│ request hashing · state invariants · budgets · immutable run       │
└──────────────────────────────┬─────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│ Deterministic Reaction-Analogy Kernel                             │
│ normalize → retrieve → lineage → transform → sites → generate     │
│ → validate → support/conflict → rank → applicability/abstain      │
└──────────────────────────────┬─────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│ Versioned Reaction Evidence Snapshot                              │
│ complete participants · mappings · lineage graph · ledger          │
│ source provenance · quality · quarantine · fold-specific views     │
└────────────────────────────────────────────────────────────────────┘
```

### 3.1 四类权威

| 权威 | 负责内容 |
|---|---|
| Evidence authority | snapshot 中有哪些来源事实、完整反应和 provenance |
| Chemical execution authority | mapping、lineage、graph edit、molecule/ledger validation |
| Agent policy authority | 下一步查什么、是否扩展 donor、如何比较受约束假设 |
| Decision authority | 基于验证结果的 tier、ranking、applicability 和 typed abstention |

### 3.2 强制 deterministic baseline

任何生产预测都必须先运行最小确定性 baseline：

1. 标准化 `X`；
2. train/snapshot 范围内自动 donor retrieval；
3. 加载完整反应；
4. 构造可用 strict transform；
5. 枚举兼容位点；
6. 生成和验证候选。

Agent 可以请求扩展或收紧证据，但不能跳过 baseline 后凭语言直觉作答。

---

## 4. 无损反应表示与 `COFACTORS` 政策

### 4.1 两个必须分离的视图

#### Retrieval projection

用于从 `X` 找 donor `A`。可以：

- 降低常见 carrier/cofactor 的 donor eligibility；
- 排除明显无机 spectator；
- 使用分子大小、复杂度、反应中心覆盖和 participant role；
- 避免 NAD(P)、ATP、H2O、O2 等抢占主要 donor 排名。

#### Complete reaction evidence

用于科学推理和 ledger。必须无损保留：

- 所有 reactants/products；
- cofactor、co-substrate、carrier、spectator；
- O2、H2O、CO2、NH3、H+、电子；
- 金属离子和其他已记录物种；
- stoichiometry、方向、来源；
- atom maps 和 atom transfers。

### 4.2 `COFACTORS` 列表的正式定位

`benchmark/canonical_identity.py` 第 101–128 行附近的 `COFACTORS` 只能作为：

```text
participant_role_prior
donor_eligibility_prior
retrieval_downweighting_prior
```

不得作为：

```text
destructive reaction stripping rule
ground-truth participant role
atom-balance exclusion rule
```

相同分子在不同反应中可能承担不同角色。静态名单不能替代：

- mapping coverage；
- changed-atom participation；
- atom-transfer contribution；
- stoichiometry；
- source annotation；
- reaction-specific role inference。

### 4.3 小分子不等于不重要

小分子可能是：

- 新增 O/N/C/S 原子的来源；
- leaving group；
- 真正被转化的底物；
- 决定 oxidation state 的共底物；
- 完整守恒所需的副产物。

因此“小于某个原子数”只能作为弱特征，不能作为删除规则。

---

## 5. Evidence Snapshot

### 5.1 Snapshot 目标

Snapshot 必须：

- immutable；
- content-addressed；
- 可重建；
- 可审计；
- 保存原始来源与规范化结果；
- 保存 mapper、resolver 和 schema 版本；
- 支持 fold-specific train-only views；
- 把问题记录隔离到 quarantine，而非静默丢弃。

### 5.2 ReactionEvidence 核心 schema

```text
ReactionEvidence
├── reaction_id
├── source_record_id
├── source_name
├── source_version
├── source_uri_or_citation
├── source_reaction
├── normalized_reaction
├── direction
├── participants[]
├── mapping_report
├── fragment_lineage_graph
├── transformed_lineage_hypotheses[]
├── transformation_hypotheses[]
├── reaction_ledger
├── quality_report
├── provenance
├── snapshot_id
└── quarantine
```

### 5.3 Participant schema

```text
ReactionParticipant
├── participant_id
├── molecule_id
├── canonical_smiles
├── side: reactant | product
├── stoichiometry
├── charge
├── atom_map_numbers[]
├── mapped_fraction
├── changed_atom_fraction
├── role_hypotheses[]
│   ├── role
│   ├── score
│   └── evidence_codes[]
├── donor_eligibility
└── provenance
```

建议角色词表：

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

角色可以有多个 hypotheses；不应在数据不足时伪造唯一真值。

### 5.4 Atom-mapping adapter

所有 mapping 必须经过显式 adapter，记录：

```text
mapper_name
mapper_version
mapper_parameters
input_hash
output_hash
mapping_status
mapped_heavy_atom_fraction
map_number_uniqueness
changed_atom_coverage
ambiguity_flags
fallback_method
```

`reacting_center.pkl` 或 center atom pairs 不能被当成完整 atom mapping。

mapping 状态至少包括：

```text
fully_mapped
partially_mapped
unmapped
mapping_failed
mapping_ambiguous
```

strict lane 默认要求可信 mapping；MCS fallback 不得伪装成 mapped strict evidence。

### 5.5 Quarantine

典型 reason code：

```text
REACTION_PARSE_FAILED
PARTICIPANT_PARSE_FAILED
MAPPING_FAILED
MAPPING_AMBIGUOUS
LOW_MAPPING_COVERAGE
LINEAGE_UNRESOLVED
LINEAGE_CATASTROPHIC_MISMATCH
ROLE_UNRESOLVED
SOURCE_DIRECTION_UNKNOWN
SOURCE_STOICHIOMETRY_INCOMPLETE
LEDGER_CONTRADICTION
DUPLICATE_CONFLICT
```

Quarantine 记录：

- 仍保留在 snapshot manifest；
- 不进入生产 donor index；
- 不从评估分母中静默消失；
- 在报告中按 reason 统计。

---

## 6. Fragment-Lineage Graph

### 6.1 为什么不能再用独立片段选择

在多反应物、多产物反应中，分别在两侧选择“较大且带反应中心”的分子可能把不同物质的谱系拼成错误的 `A→B`。

已知回归案例：

```text
2-oxoglutarate + proline + O2
→ succinate + hydroxyproline + CO2
```

必须解析出至少：

```text
proline → hydroxyproline
2-oxoglutarate → succinate
O2 → transferred oxygen / coproduct accounting
```

不能得到：

```text
2-oxoglutarate → hydroxyproline
```

### 6.2 图定义

建立 reactant fragments 到 product fragments 的 bipartite graph。边特征至少包括：

```text
shared_mapped_heavy_atoms
reactant_atom_retention_fraction
product_atom_origin_fraction
changed_mapped_atoms
bond_edit_participation
transferred_atom_sets
scaffold_continuity
role_compatibility
mapping_quality
```

### 6.3 输出不是单一 primary pair

Resolver 输出：

```text
LineageResolution
├── graph
├── transformed_lineage_hypotheses[]
├── split_hypotheses[]
├── merge_hypotheses[]
├── atom_transfer_edges[]
├── ambiguity_sets[]
├── quality
└── failure_reason
```

规则：

- 不允许用 tuple `max()` 静默打破化学意义相同的 tie；
- tie 必须保留为 ambiguity set；
- 可确定的多条 transformed lineage 可以同时进入索引；
- 无法解析的反应进入 quarantine；
- 每个 lineage 有稳定 `lineage_id`。

### 6.4 人工审计

抽样必须覆盖：

- 单底物/单产物；
- 多反应物；
- 多产物；
- redox cofactor；
- hydroxylation；
- transferase；
- cleavage；
- condensation；
- mapping 不完整；
- MCS fallback；
- 静态 `COFACTORS` 误分类风险。

---

## 7. Reaction Ledger

### 7.1 Ledger 目的

Ledger 不是为了把所有来源反应强行补齐，而是准确表达：

- 来源记录已明确什么；
- 原子和电荷能追踪到什么程度；
- 哪些依赖 implicit H/proton/electron policy；
- 哪些信息缺失；
- 候选类比继承了哪些 donor 条件。

### 7.2 Schema

```text
ReactionLedger
├── reactant_entries[]
├── product_entries[]
├── role_assignments[]
├── stoichiometry
├── atom_transfer_records[]
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

### 7.3 Balance status

统一采用：

```text
fully_balanced_explicit_reaction
heavy_atom_balanced_with_implicit_h_e_policy
partial_or_unbalanced_source
```

这些状态描述来源与账本完整性，不直接等于候选是否“真实发生”。

### 7.4 Candidate ledger

候选 `X→Y` 的 ledger 由 donor ledger 派生，但必须明确：

- 哪些 participants 是直接继承的类比条件；
- 哪些原子来源由 donor transfer 映射支持；
- 哪些计量只是假设性复制；
- 哪些来源未知；
- 是否仅能做 heavy-atom accounting；
- candidate ledger 与 source ledger 的 linkage。

### 7.5 新增重原子规则

每个新增 heavy atom 必须：

- 有 donor atom-transfer source；
- 或明确标记 `unknown_source`；
- strict lane 中若 transformation 需要明确来源而来源不可追踪，则候选不得通过 strict validation。

---

## 8. Adaptive Donor Retrieval

### 8.1 正确检索单位

两阶段检索：

```text
X
→ retrieve distinct donor molecule identities A
→ load complete reaction records associated with each A
```

不能直接按 reaction rows 做固定 top-K，否则：

- 同一 A 的重复记录会占满结果；
- 高频数据库条目会伪造证据多样性；
- donor molecule 与 donor reaction 被混为一谈。

### 8.2 Eligibility

donor molecule 必须：

- 来自非 quarantine transformed lineage；
- 满足当前 lane 的 mapping/lineage 质量要求；
- 在 benchmark 中属于当前 fold 的 train evidence；
- 不与测试 evidence 发生身份泄漏；
- 具有可解析的 transformation hypothesis。

### 8.3 Baseline retrieval features

首版可使用：

- Morgan/Tanimoto；
- scaffold similarity；
- functional-group overlap；
- size/heteroatom/charge compatibility；
- local environment similarity；
- participant role/donor eligibility；
- source quality；
- transformation diversity；
- donor identity diversity。

固定权重只能标记为 baseline。权重若学习或调节，只能在 train/validation 上完成，并进行 ablation。

### 8.4 Adaptive stopping

停止扩展 donor 的条件可以包括：

- similarity gap 明显；
- transformation family 已稳定；
- 新 donor 不再新增 validated candidate；
- independent source diversity 达标；
- evidence conflict 已解决或确认不可解决；
- 达到 donor/tool/time budget；
- 已判定 OOD。

必须保存：

```text
retrieval_rounds
retrieved_donor_ids
loaded_reaction_ids
stop_reason
budget_used
```

### 8.5 非 oracle 原则

评估和 pilot 中：

- 只向系统提供 `X`；
- donor 必须自动检索；
- 禁止人工按真值挑 support；
- 人工可审计 labels，但不能在运行时提示正确 donor、T 或 site。

---

## 9. Transformation Hypotheses

### 9.1 Transformation 不等于粗 `edit_key`

完整 hypothesis 至少包括：

```text
TransformationHypothesis
├── transformation_id
├── source_lineage_ids[]
├── family
├── mapped_atom_edits[]
├── bond_deletions[]
├── bond_additions[]
├── bond_order_changes[]
├── atom_attribute_changes[]
├── transferred_atoms[]
├── donor_site
├── local_environment
├── strict_preconditions[]
├── generalizable_constraints[]
├── ledger_requirements[]
├── mapping_quality
└── canonical_transform_hash
```

旧 `EditScript.key()` 可作为粗分桶或 baseline feature，不得作为 canonical transformation identity。

### 9.2 Support aggregation

多个 donor lineage 支持同一 transformation 时，需要：

- canonicalize transform；
- 保留所有 source lineage；
- 去除镜像和派生重复；
- 计算 independent support identity；
- 保留局部环境差异。

“两条支持”不能自动等于“高置信”，因为两条可能来自同一底层记录。

### 9.3 Strict hypothesis

要求：

- 可信 mapped lineage；
- edit 可完全回放；
- donor site 明确；
- preconditions 完整；
- 原子来源满足 strict ledger policy；
- 无未解决关键 ambiguity。

### 9.4 Generalized hypothesis

必须明确：

```text
relaxed_constraints[]
failed_strict_conditions[]
generalization_distance
generalization_policy_version
```

只能放宽预注册规则，不能由 LLM 用自然语言临时创造未版本化的放宽标准。

---

## 10. Transformation-Conditioned Site Enumeration

### 10.1 条件化原则

位点搜索必须近似：

```text
p(S_X | X, T, Δ, donor environment)
```

不能无条件先枚举所有“反应性位点”，再与 transformation 随机组合。

### 10.2 SiteHypothesis

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

### 10.3 稳定身份

Site ID 必须基于 canonicalized query identity 和规范化 atom/bond reference 创建，避免输入 SMILES 原子顺序改变后候选身份变化。

### 10.4 多位点和对称性

- 多个有效位点分别生成候选；
- 对称等价位点应 canonical deduplicate；
- 保留支持证据和 site ambiguity；
- 不通过人为顺序只保留第一个匹配位点。

---

## 11. Deterministic Candidate Generation

### 11.1 结构生成权

所有产物结构只能来自：

```text
validated TransformationHypothesis
+ eligible SiteHypothesis
→ deterministic graph-edit compiler
→ molecule sanitizer
→ canonical candidate
```

LLM 不得直接把文本或 SMILES 注入 candidate store。

### 11.2 GenerationReport

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

### 11.3 Candidate deduplication

结构等价候选合并为一个 canonical candidate，但保留：

- 所有 donor supports；
- 所有 transformation/site paths；
- strict/generalized 来源；
- 独立证据集合；
- 最佳和冲突 ledger reports。

### 11.4 回归示例

1-octanol：

```text
input:  CCCCCCCCO
product: CCCCCCCC=O
```

不得误写为少一个碳的：

```text
CCCCCCC=O
```

---

## 12. Validation

### 12.1 Molecule validation

至少包括：

- parse；
- sanitize；
- valence；
- aromaticity；
- formal charge；
- fragment count；
- atom count；
- stereochemistry policy；
- forbidden/disconnected product policy；
- canonicalization；
- input atom-order invariance。

### 12.2 Reaction-analogy validation

至少包括：

- graph edit 是否与 transform 一致；
- site preconditions 是否全部满足；
- donor-to-query atom correspondence；
- transferred atom accounting；
- candidate ledger 状态；
- charge/element policy；
- strict/generalized lane invariants；
- transformation scope 是否越界。

### 12.3 失败语义

科学拒答与基础设施失败必须分开：

```text
scientific_abstention:
  NO_IN_DOMAIN_DONOR
  NO_RESOLVED_LINEAGE
  NO_TRANSFERABLE_TRANSFORM
  NO_COMPATIBLE_SITE
  ALL_CANDIDATES_CHEMICALLY_INVALID
  EVIDENCE_CONFLICT
  INSUFFICIENT_SUPPORT

system_failure:
  SNAPSHOT_UNAVAILABLE
  MAPPER_UNAVAILABLE
  TOOL_PROTOCOL_ERROR
  STORAGE_FAILURE
  BUDGET_CONFIGURATION_ERROR
```

系统失败不得转换成“没有可靠产物”。

---

## 13. Support、Counterevidence 与 Applicability

### 13.1 支持证据

支持特征可以包括：

- donor/query structure similarity；
- mapped transform 一致性；
- site environment similarity；
- independent donor count；
- independent source count；
- mapping/lineage quality；
- ledger completeness；
- source provenance quality；
- transformation recurrence；
- candidate stability across retrieval rounds。

### 13.2 第一版可用的 counterevidence

- 高相似 donor 支持竞争 transformation；
- `X` 不满足 donor transformation 的结构前提；
- 候选 site 局部环境明显冲突；
- graph edit 产生非法结构；
- ledger 无法解释必需的新增重原子；
- source direction、role 或 lineage 冲突；
- 关键支持全部来自低质量或同源重复证据；
- strict 失败，只能显著放宽约束。

### 13.3 不能当 counterevidence 的情况

- 数据库没有记录；
- 没找到第二个酶；
- 相似分子没有被收录为底物；
- 来源没有报告阴性结果；
- 单纯的低频。

真正的 enzyme inactivity 需要 assay negative。

### 13.4 Applicability

首版 applicability 只描述结构类比适用域：

```text
in_domain
near_domain
out_of_domain
conflicted
unknown
```

不得把它解释成 enzyme activity。

### 13.5 酶信息的定位

酶/EC/UniProt 信息可作为：

- donor reaction provenance；
- reaction class context；
- 可选展示证据；
- 后续 enzyme applicability 模块输入。

“没有额外酶支持”不是 strict structural analogy 的强制拒答条件。

---

## 14. Tiered Ranking 与 Abstention

### 14.1 分层原则

先按 evidence tier 分层，再在 tier 内排序：

```text
Tier S: strict, high-quality mapped lineage
Tier G: generalized exploratory
```

不能直接用一个 raw score 把 generalized 候选排到 strict 候选之上，却不向用户说明证据类型不同。

### 14.2 Ranking features

可包含：

- donor similarity；
- transform support；
- site compatibility；
- lineage quality；
- mapping quality；
- ledger completeness；
- evidence independence；
- source quality；
- conflict penalty；
- generalization penalty；
- retrieval stability。

固定权重仅为 baseline。不得把手工权重包装成概率。

### 14.3 Abstention precedence

建议顺序：

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

基础设施错误走 `failed`，不走上述 precedence。

### 14.4 Selective prediction

系统必须报告：

- coverage；
- risk at coverage；
- abstention rate；
- wrong-answer rate among answered；
- false confident prediction rate；
- reason-code distribution。

首版不先承诺固定 top-1 百分比；先重建可信 benchmark 后再设置门槛。

---

## 15. LLM Agent 权限边界

### 15.1 Production grounded mode

生产 Agent 可以：

- 调用高层预测工具；
- 查看 donor、完整反应、transformation、site、ledger 和 conflict；
- 请求在预定义结构化过滤条件内扩大或收紧 evidence；
- 比较已返回的 `donor_id`、`transformation_id`、`site_id` 和 `candidate_id`；
- 决定是否需要更多证据；
- 解释为什么某候选是 strict/generalized；
- 解释 abstention reason；
- 生成面向用户的证据摘要。

生产 Agent 不可以：

- 直接输出工具未返回的产物结构；
- 构造或修改 SMILES；
- 创建 atom maps；
- 修改图编辑；
- 创建未知 `candidate_id` 或 `evidence_id`；
- 改写 kernel 的 rank、lane、validation 或 abstention；
- 自报概率；
- 把来源缺失解释为反证。

### 15.2 Agent 的真实推理空间

Agent 不是最后的“嘴”。它负责：

- evidence action policy；
- donor/reaction expansion strategy；
- 冲突证据比较；
- 选择需要深入验证的已有 transform/site hypothesis；
- 在预算内决定何时停止继续检索；
- 把结构化事实组合成可理解的科学说明。

每次生产运行仍必须执行 deterministic baseline，避免 Agent 因提示漂移遗漏基本候选。

### 15.3 Research LLM-hypothesis mode

研究模式允许 LLM 提交：

```text
support_reaction_ids
transformation_family
target_site
relaxed_constraints
rationale_summary
```

但必须：

1. 引用真实 support IDs；
2. 通过同一 deterministic compiler；
3. 通过 site 和 ledger validation；
4. 通过后才获得 candidate ID；
5. 标记为 `agent_proposed`；
6. 与生产 baseline 分开 benchmark；
7. 不进入 production calibrated ranking。

该模式用于测量 LLM 的增量研究价值，不是 MVP 必需项。

### 15.4 不要求暴露 chain-of-thought

系统保存的是：

```text
D: donor evidence
T: transformation
S: site
Δ: graph edit
Y: product
L: ledger
R: rank/applicability
A: abstention
```

对用户展示 evidence card、结构化理由和引用，不要求保存或显示模型内部完整思维过程。

---

## 16. Scientific Lifecycle 与 Agent Policy

### 16.1 内部生命周期

内部状态用于安全不变式：

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

失败状态：

```text
ABSTAINED
PARTIAL
FAILED
```

### 16.2 Agent 不必线性走 14 步

Agent 可以在预算内循环：

```text
retrieve
↔ inspect reaction
↔ inspect transform
↔ expand evidence
↔ inspect conflicts
↔ request decision
```

因此：

> 生命周期是服务端安全协议；`D→T→S→Δ→Y→L→R/A` 是可审计科学变量；二者都不是强迫 LLM 输出固定思维链。

### 16.3 Freeze

一旦 run `FROZEN`：

- candidate set 不可修改；
- ranking 不可修改；
- manifest 和 resources 可重复读取；
- 外部增强必须创建新 run 或显式 child run；
- Agent 报告只能引用 frozen IDs。

---

## 17. MCP Surface

### 17.1 生产高层工具

MVP 建议四个：

```text
reaction.predict_analogical_products_v1
reaction.get_run_v1
reaction.get_candidate_evidence_v1
reaction.expand_evidence_v1
```

`expand_external_evidence` 后置，不能与本地 snapshot 扩展混用同一副作用声明。

### 17.2 内部/调试工具

```text
chem.analyze_structure_v1
reaction.analyze_diff_v1
reaction.get_details_v1
evidence.search_structured_v1
reaction.validate_hypothesis_v1
chem.validate_candidate_v1
enzyme.get_provenance_v1
```

生产 Agent 默认优先使用高层工具，避免直接操纵底层图编辑。

### 17.3 PredictRequest

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

### 17.4 PredictionResult

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
├── stage_summary
├── manifest_uri
└── resource_uris[]
```

统一使用：

```text
manifest_uri
reaction_ledger
```

不再并存：

```text
run_manifest_uri
ledger
```

### 17.5 跨字段不变式

```text
status=completed
  decision=predicted
  candidates.length >= 1
  abstention is null

status=abstained
  decision=abstained
  candidates.length == 0
  abstention.reason_code is not null

status=partial
  decision=partial
  partial_reason is not null

status=failed
  decision=failed
  failure is dependency/protocol/storage error
  failure must not masquerade as abstention
```

### 17.6 幂等和副作用

`predict`：

- 会创建或复用 immutable run；
- 是 append/write 操作，不应标成 read-only；
- 使用 canonical request hash + snapshot/version + idempotency key；
- 相同请求返回同一 run。

`get_run`、`get_candidate_evidence`：

- read-only。

本地 `expand_evidence`：

- 可能创建 child run；
- 不修改父 run。

未来外部证据：

- open-world network I/O；
- 单独权限、缓存、来源许可和 provenance。

### 17.7 Grounding guard

Host 必须验证：

- Agent 引用的 candidate/evidence/run ID 属于本次 frozen run；
- 产物结构和分数从 `PredictionResult` 渲染；
- 未知 ID 被拒绝；
- Agent 文本不能覆盖结构化字段；
- 提示注入不能改变工具权限和 snapshot 边界。

---

## 18. Reproducibility、Manifest 与安全

### 18.1 Run manifest

至少记录：

```text
run_id
parent_run_id
request_hash
snapshot_id/hash
fold/view_id
query normalization policy/version
mapper/resolver/generator/validator/ranker versions
retrieval configuration
ranking configuration
abstention policy version
tool schema versions
tool response hashes
agent prompt hash
model/provider/revision
temperature/seed
cache policy
budgets and actual usage
trace/correlation ID
timestamps
redaction policy
result hash
```

### 18.2 数据和日志

- 原始来源与规范化记录分开保存；
- 不在普通日志中泄露 provider secrets；
- tool payload 按 schema 做日志脱敏；
- 外部来源许可证和引用要求必须进入 provenance；
- benchmark test labels 不得暴露给 Agent 工具。

### 18.3 可重放级别

区分：

```text
kernel_replayable
agent_trace_replayable
externally_non_replayable
```

生产 benchmark 至少要求 kernel 可完全重放。

---

## 19. 评估设计

### 19.1 Layer 0：数据正确性

指标：

- reaction parse rate；
- participant parse rate；
- mapping coverage；
- map uniqueness；
- fragment-lineage accuracy；
- catastrophic mismatch rate；
- role accuracy/ambiguity；
- ledger completeness；
- quarantine rate/reasons；
- 人工审计一致性。

### 19.2 Layer 1：Donor retrieval

指标：

- donor molecule recall@K；
- donor reaction recall@K；
- transformation-family coverage；
- distinct donor diversity；
- independent source diversity；
- adaptive rounds/cost；
- OOD detection；
- automatic retrieval success。

### 19.3 Layer 2：Transformation 和 site

指标：

- transformation family recall；
- exact edit recovery；
- transformed-lineage recall；
- target-site recall；
- strict precondition precision；
- site ambiguity calibration。

### 19.4 Layer 3：Generation 和 validation

指标：

- valid molecule rate；
- canonical candidate recall；
- top-K candidate recall；
- graph-edit fidelity；
- equivalent-SMILES invariance；
- input atom-order invariance；
- atom-source accounting；
- ledger status distribution。

### 19.5 Layer 4：Ranking 和 abstention

指标：

- top-1/top-3/top-K；
- MRR；
- risk–coverage；
- selective accuracy；
- abstention rate；
- abstention precision/recall；
- false confident prediction rate；
- strict/generalized 分报；
- 每个指标的 N 和置信区间。

### 19.6 Layer 5：Agent/MCP

指标：

- invented candidate IDs；
- invented evidence IDs；
- unsupported claim rate；
- grounding rejection rate；
- tool protocol failures；
- repeated-run agreement；
- tool calls；
- latency；
- tokens/cost；
- Agent 增量 evidence gain；
- research hypothesis incremental candidate recall/error。

### 19.7 Multi-answer truth

同一个 `X` 可能在不同反应、条件或酶中产生多个真实 `Y`。Benchmark 需要：

```text
allowed_product_set
reaction_context
source_context
tautomer policy
salt/neutralization policy
stereo-sensitive metric
stereo-agnostic metric
multi-product target policy
annotation completeness flag
```

不能继续用单标签 exact match 把另一个真实产物判错。

### 19.8 Splits

至少：

```text
exact-X split
scaffold split
transformation-family split
source split
time split
OOD/abstention challenge set
```

`source/time split` 只有在 provenance 和时间字段质量达标时启用；否则必须标记 capability unavailable。

### 19.9 防泄漏

每个 fold 单独创建：

```text
train evidence view
validation view
test labels
```

检索、support、counterevidence、ranking reference 和校准都不能读取 test evidence。

---

## 20. Pilot 与验收哲学

### 20.1 非 oracle pilot

冻结 20–50 个经过人工审计的 mini snapshot 案例，覆盖：

- single reactant/product；
- multi-reactant；
- multi-product；
- oxidation/reduction；
- hydroxylation；
- hydrolysis；
- transfer；
- cleavage；
- multiple sites；
- no compatible site；
- invalid input；
- OOD；
- mapping ambiguity；
- 已知 2-oxoglutarate/proline 错配。

运行时只给 `X`，donor 自动从 train-only mini snapshot 检索。

### 20.2 人工可以做什么

- 审计完整反应；
- 审计 participant roles；
- 审计 lineage；
- 审计 transformation/site/product truth；
- 定义等价产物集合；
- 记录 disagreement。

### 20.3 人工不能做什么

- 根据测试答案挑 donor；
- 提示正确 transformation；
- 提示正确 site；
- 在系统失败后手工补 candidate 再计为成功。

### 20.4 首个质量门

进入 MCP/Agent 之前必须证明：

1. 已知 catastrophic A/B 错配被修复或 quarantine；
2. unresolved lineage 不进入 strict index；
3. fold 内 test evidence leakage 为零；
4. strict candidate 全部来自可回放 graph edit；
5. 等价 SMILES 输入产生相同 canonical candidate set；
6. 新增重原子有来源或明确 unknown；
7. ledger status 语义完整；
8. system failure 不冒充 abstention；
9. pilot donor 自动检索；
10. 各阶段 miss 可归因。

---

## 21. 分阶段产品路线

### Phase 0：契约冻结

- 统一术语；
- 旧指标标记 provisional；
- 修正文档错误和 schema 漂移；
- 外部证据、多步和 generalized 移出 MVP。

### Phase 1：数据地基

- mapping adapter；
- participant/role schema；
- fragment-lineage graph；
- Reaction Ledger；
- snapshot/quarantine；
- 人工审计。

### Phase 2：Mini snapshot 与评估骨架

- 多答案真值；
- fold-specific views；
- 非 oracle pilot；
- stage-level evaluation；
- deterministic baselines。

### Phase 3：Strict one-step kernel

- normalization；
- adaptive donor retrieval；
- complete reaction loading；
- strict transform；
- conditioned sites；
- deterministic products；
- validation；
- immutable run。

### Phase 4：Support、ranking、applicability、abstention

- independent evidence；
- counterevidence；
- baseline ranking；
- selective prediction；
- typed abstention。

### Phase 5：全量 snapshot 和新 benchmark

- 全量重建；
- 重跑 legacy baselines；
- 设置正式性能门；
- strict 报告。

### Phase 6：MCP

- 高层工具；
- schemas；
- IDs/resources；
- idempotency；
- side-effect annotations；
- contract/chaos tests。

### Phase 7：Production LLM Agent

- evidence policy；
- grounded reporting；
- no-invention；
- budgets；
- prompt/tool/model manifest；
- prompt-injection tests。

### Phase 8：Generalized lane

- 版本化 relaxation policy；
- generalization distance；
- 独立排名和报告。

### Phase 9：Research mode、外部证据和 multi-step

- LLM typed hypothesis experiment；
- open-world provenance；
- candidate reaction graph；
- cycle/branch/budget；
- path-level uncertainty。

---

## 22. 现有资产处置

### 22.1 可复用但必须重验

- Morgan/Tanimoto substrate retrieval；
- RDKit normalization 和 fingerprint 工具；
- template/align generation primitives；
- DRFP 表示；
- 现有 split 框架；
- 现有 source data loaders。

### 22.2 必须重建或替换

- `canonical_identity.transformed_pair` 的独立片段选择；
- 以单一 A/B 为前提的 group/label；
- 不完整 train-only scorer evidence；
- 过粗 canonical `edit_key`；
- 单答案 benchmark；
- 只用 X/Y 分子式的反应守恒；
- 无 manifest 的预测结果。

### 22.3 降级为弱特征或 baseline

- DRFP max score；
- 固定 Morgan top-5；
- 固定 retrieval/ranking weights；
- 旧 A1/A2 诊断；
- 手工选择 support 的演示。

---

## 23. 正式设计决策记录

| 决策 | v2 定稿 |
|---|---|
| 用户输入 | 只输入 `X` |
| `A→B` 来源 | 自动 donor 检索后读取完整反应并沿 lineage 解析 |
| donor 集 | 自适应 distinct donor molecule set |
| 完整反应 | 无损保存全部 participants；A→B 只是 lineage |
| `COFACTORS` | role/retrieval prior，不是删除规则 |
| 产物生成 | deterministic graph edit |
| LLM | 生产中做 evidence policy/受约束假设管理/解释；研究模式可提交 typed hypothesis |
| 输出 | strict ranked top-K 或 typed abstention |
| generalized | 后置、分 lane |
| 酶证据 | provenance/context；不作为结构类比强制闸 |
| 分数 | ranking score，不称概率 |
| 证据源 | immutable local snapshot；外部增强后置 |
| benchmark | multi-answer、fold-specific、train-only、六层 |
| 多步 | 单步达标后用候选反应图实现 |

---

## 24. 最终结论

最终系统应被理解为：

> **完整、无损、版本化的 donor 反应证据地基，驱动原子谱系正确的 `A→B` 解析；自适应检索为未知 `X` 找到可类比 donor；LLM Agent 管理受约束的证据探索和科学假设；确定性化学内核在兼容位点生成、验证和冻结 `Y`；分层决策层输出 strict/generalized ranked top-K 或可靠拒答；MCP 提供可审计、可重放、不可编造的交互边界。**

这套设计同时保留了：

- LLM 的真实推理价值；
- 化学结构计算的确定性；
- 生化反应完整账本；
- 数据和 benchmark 的科学可信度；
- 用户需要的自动 `X→Y` 体验；
- 未来 generalized、外部证据和 multi-step 的扩展空间。

