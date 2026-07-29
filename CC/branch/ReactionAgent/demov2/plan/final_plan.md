# FINAL PLAN — Reaction Analogy MCP Agent Implementation Plan

> 日期：2026-07-29  
> 状态：**FINAL / 三模型一致批准**  
> 配套设计：`final_design.md`  
> 三方裁决：`final_discussion.md`  
> 工作根目录：`CC/branch/ReactionAgent/demov2/`  
> 当前允许执行：P0 契约冻结。P0 Gate 通过后才进入 P1 数据地基。

---

## 0. 执行规则

### 0.1 权威关系

实现只能依据：

```text
final_design.md
final_plan.md
final_discussion.md
```

旧 ChatGPT/Claude/Qwen design、plan、discussion 全部为历史参考。

实现发现设计与真实数据冲突时：

1. 停止相关实现；
2. 写 ADR；
3. 更新 final design/plan；
4. 重新通过对应 Gate；
5. 不允许静默改变产品语义、schema 或 benchmark 口径。

### 0.2 最短关键路径

```text
P0 Contract freeze
→ P1 Data foundation
→ P2 Mini snapshot / truth / isolation / pilot
→ P3 Strict one-step kernel
→ P4 Support / ranking / applicability / abstention
→ P5 Full snapshot / rebuilt benchmark
→ P6 MCP
→ P7 Production grounded Agent
```

后置：

```text
P8 Generalized lane
P9 Agent-proposed graduation / external evidence / multi-step
```

### 0.3 Gate 原则

未通过当前 Gate：

- 可以修当前 Phase；
- 可以并行做不依赖科学结果的 schema、fixtures、protocol tooling；
- 不得宣称后续能力已可靠；
- 不得用 LLM/MCP UI 掩盖数据或 kernel 问题；
- 不得跳级进入 generalized、external evidence 或 multi-step。

### 0.4 第一版 Definition

第一版目标：

```text
X only
→ automatic donor retrieval
→ complete donor reaction
→ correct mapped A→B lineage
→ strict transform
→ conditioned query site
→ deterministic Y
→ dual-ledger validation
→ ranked strict top-K or typed abstention
```

---

## 1. 目标目录结构

```text
CC/branch/ReactionAgent/demov2/
├── pyproject.toml
├── README.md
├── docs/
│   ├── decisions/
│   │   ├── ADR-0001-authority-and-scope.md
│   │   ├── ADR-0002-hypothesis-lanes.md
│   │   ├── ADR-0003-ledger-and-source-semantics.md
│   │   ├── ADR-0004-partial-eligibility.md
│   │   ├── ADR-0005-scientific-decision-authority.md
│   │   └── ADR-0006-mcp-side-effects.md
│   ├── audit_protocol.md
│   └── benchmark_protocol.md
├── plan/
│   ├── final_design.md
│   ├── final_plan.md
│   └── final_discussion.md
├── reaction_agent/
│   ├── __init__.py
│   ├── config.py
│   ├── schemas/
│   │   ├── common.py
│   │   ├── evidence.py
│   │   ├── mapping.py
│   │   ├── lineage.py
│   │   ├── ledger.py
│   │   ├── transform.py
│   │   ├── hypothesis.py
│   │   ├── candidate.py
│   │   ├── result.py
│   │   └── errors.py
│   ├── chemistry/
│   │   ├── normalize.py
│   │   ├── mapping_adapter.py
│   │   ├── roles.py
│   │   ├── lineage.py
│   │   ├── source_ledger.py
│   │   ├── candidate_ledger.py
│   │   ├── transform.py
│   │   ├── sites.py
│   │   ├── generate.py
│   │   └── validate.py
│   ├── evidence/
│   │   ├── ingest.py
│   │   ├── snapshot.py
│   │   ├── quarantine.py
│   │   ├── store.py
│   │   ├── fold_view.py
│   │   ├── retrieve.py
│   │   ├── identity.py
│   │   └── provenance.py
│   ├── inference/
│   │   ├── deterministic_baseline.py
│   │   ├── production_selection.py
│   │   ├── agent_proposed.py
│   │   ├── support.py
│   │   ├── counterevidence.py
│   │   ├── features.py
│   │   ├── rank.py
│   │   ├── applicability.py
│   │   ├── abstain.py
│   │   └── predictor.py
│   ├── runtime/
│   │   ├── lifecycle.py
│   │   ├── trace.py
│   │   ├── manifest.py
│   │   ├── run_store.py
│   │   ├── idempotency.py
│   │   └── budgets.py
│   ├── mcp/
│   │   ├── server.py
│   │   ├── tools.py
│   │   ├── resources.py
│   │   └── contracts.py
│   ├── agent/
│   │   ├── provider.py
│   │   ├── policy.py
│   │   ├── grounding.py
│   │   ├── reporter.py
│   │   └── research.py
│   └── evaluation/
│       ├── truth.py
│       ├── splits.py
│       ├── isolation.py
│       ├── metrics.py
│       ├── funnel.py
│       ├── baselines.py
│       ├── calibration.py
│       └── reports.py
├── scripts/
│   ├── audit_legacy_lineage.py
│   ├── build_snapshot.py
│   ├── audit_snapshot.py
│   ├── build_mini_benchmark.py
│   ├── run_pilot.py
│   ├── run_benchmark.py
│   └── replay_run.py
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── property/
│   ├── regression/
│   ├── integration/
│   ├── contracts/
│   └── evaluation/
└── reports/
    ├── data_audit/
    ├── pilot/
    ├── benchmark/
    └── manifests/
```

目录可局部调整，但不得混合：

- evidence/data；
- chemistry；
- decision/ranking；
- runtime；
- MCP；
- Agent；
- evaluation。

---

## 2. 全局实施纪律

### 2.1 代码

- 新代码只写在 `demov2`；
- Legacy 默认只读；
- 复用旧函数前写 characterization tests；
- 每个 Phase 先写测试和 fixtures，再实现；
- 每个科学组件版本化；
- 不在 core 中硬编码某个 LLM provider。

### 2.2 数据

- 原始来源和规范化 snapshot 分开；
- Snapshot immutable/content-addressed；
- Quarantine 是显式数据集；
- 每个过滤有 before/after counts 和 reason；
- Source provenance 不得丢失；
- Test labels 与 evidence APIs 物理/逻辑隔离。

### 2.3 类型与失败

- Strict schemas；
- Unknown fields 默认拒绝；
- Scientific failures 与 system failures 分开；
- 禁止异常后 silent `[]`；
- `failed` 不得伪装为 `abstained`；
- Result cross-field invariants 必须在 schema 层执行。

### 2.4 化学结构权

- 只有 `chemistry.generate` 创建 candidate structure；
- Agent、reporter、MCP text 层不能创建/修改 SMILES；
- Strict candidate 必须 replayable；
- 每个 candidate 必须引用 transform/site/generation/validation/dual-ledger。

### 2.5 Mapping 表述

- Mapper 输出只默认表示 formal correspondence；
- Mechanistic origin 需要独立 evidence；
- UI/report 不得把 formal assignment 写成实验机制事实。

### 2.6 Benchmark

- 运行时只给 X；
- Donor 自动检索；
- Retrieval/support/ranking references train-only；
- All X 进分母；
- Multi-answer truth；
- Metrics 带 N/CI；
- Old metrics provisional；
- Oracle donor 只作 upper-bound diagnostic。

### 2.7 Agent

- Production 必须先运行 deterministic baseline；
- Agent 只引用真实 opaque IDs；
- ProductionSelectionHypothesis 与 AgentProposedHypothesis 分开；
- AgentProposed 不进入主 production rank，除非 graduation；
- Prompt/model/tool hashes 进入 manifest；
- Provider 通过 adapter 注入。

---

## 3. P0 — Contract Freeze

### 3.1 目标

把三方讨论裁决写成可执行的 ADR、schema 契约和权威关系；此阶段不实现 prediction kernel。

### 3.2 P0-T1：Authority 与 scope

创建：

```text
docs/decisions/ADR-0001-authority-and-scope.md
```

写明：

- final design/plan/discussion 权威；
- 旧文档历史地位；
- 输入只给 X；
- 输出 one-step strict structural analogy；
- 非 enzyme/environment probability；
- first version 不做 generalized/external/multi-step；
- old metrics provisional。

验收：

- README 只指向 final docs；
- 无旧文件仍自称实施权威；
- Scope 不存在互相矛盾的承诺。

### 3.3 P0-T2：Hypothesis lanes

创建：

```text
ADR-0002-hypothesis-lanes.md
```

冻结：

```text
ProductionSelectionHypothesis
AgentProposedHypothesis
```

明确：

- Production selection 只能引用已存在 transform/site IDs；
- AgentProposed 可提交 typed atoms/bonds，但进入独立 lane；
- Relaxations 只能用 registered IDs；
- AgentProposed 不覆盖 baseline；
- Graduation 需要 benchmark + ADR + human approval。

测试规范：

- unknown support ID reject；
- unknown transform/site ID reject；
- free-text relaxation reject；
- candidate origin required；
- lane mixing reject。

### 3.4 P0-T3：Mapping/source semantics

创建：

```text
ADR-0003-ledger-and-source-semantics.md
```

冻结：

```text
formal_mapped_source_assignment
mechanistic_atom_origin
source_assignment_method
source_assignment_quality
source_assignment_ambiguity
mechanistic_origin_evidence_ids
```

禁止 mapper output 自动升级为 mechanism。

### 3.5 P0-T4：Dual ledgers

在 ADR-0003 冻结：

```text
SourceReactionLedger
CandidateAnalogyLedger
```

明确：

- Source ledger = 来源记录事实/缺失；
- Candidate ledger = donor-derived analogy assumptions；
- Candidate cofactor/stoichiometry 不得写成真实事实；
- Source→candidate linkage required。

### 3.6 P0-T5：Partial eligibility

创建：

```text
ADR-0004-partial-eligibility.md
```

冻结 final design §10.4 矩阵：

- fully balanced；
- heavy-atom balanced；
- missing noncritical cofactor stoichiometry；
- unknown changed-heavy-atom source；
- critical contradiction；
- role ambiguity；
- lineage ambiguity；
- unknown direction。

每格必须有：

```text
strict eligibility
required warnings
quarantine behavior
evaluation bucket
```

### 3.7 P0-T6：Scientific decision authority

创建：

```text
ADR-0005-scientific-decision-authority.md
```

冻结：

- versioned decision policy 是 status/rank/lane/validation/applicability authority；
- Agent 只能停止检索并请求 decision；
- no qualitative confidence；
- official abstention enums；
- system failure enums；
- cross-field invariants。

### 3.8 P0-T7：MCP side effects

创建：

```text
ADR-0006-mcp-side-effects.md
```

冻结：

- predict = run-store append/write + idempotent request semantics；
- get = read-only；
- local expand = immutable child run；
- external = post-MVP network I/O；
- same key/same request reuse；
- same key/different request conflict；
- concurrency atomic dedup。

### 3.9 P0-T8：Schema skeletons

先定义而不实现算法：

- ReactionEvidence；
- MappingReport；
- LineageResolution；
- SourceReactionLedger；
- CandidateAnalogyLedger；
- TransformationHypothesis；
- SiteHypothesis；
- ProductionSelectionHypothesis；
- AgentProposedHypothesis；
- Candidate；
- PredictionResult；
- errors/enums。

### 3.10 Gate P0

必须全部满足：

1. Six ADRs approved；
2. Final docs/README 权威一致；
3. 两种 hypothesis schema 无歧义；
4. Dual ledgers 无歧义；
5. Partial eligibility matrix 完成；
6. Mapping vs mechanism 语义冻结；
7. Decision authority 冻结；
8. MCP side effects 冻结；
9. Old metrics marked provisional；
10. Pydantic/JSON schema skeletons 可通过 contract tests。

只有 Gate P0 通过，才进入 P1。

---

## 4. P1 — Data Foundation

### 4.1 目标

建立可信 mapping、participant roles、multi-lineage graph、dual ledgers、snapshot、quarantine 和人工审计。

### 4.2 P1-T1：Package bootstrap

交付：

- `pyproject.toml`；
- isolated package；
- dependency lock；
- test runner；
- configuration；
- logging/redaction；
- version endpoint。

测试：

- package import；
- explicit snapshot requirement；
- deterministic seed/config；
- no legacy write。

### 4.3 P1-T2：Strict domain schemas

实现 P0 skeletons。

测试：

- unknown field reject；
- enum enforcement；
- stable ID；
- content hash；
- required provenance；
- ledger statuses；
- PredictionResult invariants；
- candidate origin；
- lane separation。

### 4.4 P1-T3：Legacy lineage audit

只读重放：

1. 现有 `canonical_identity.transformed_pair`；
2. 现有 main substrate/product；
3. mapping overlap/changed atoms；
4. cross-lineage mismatch detection；
5. 分 reaction class/participant/cofactor/source 统计；
6. 输出 examples/source IDs。

必须包含：

```text
2-oxoglutarate + proline + O2
→ succinate + hydroxyproline + CO2
```

报告：

```text
reports/data_audit/legacy_lineage_audit.json
reports/data_audit/legacy_lineage_audit.md
```

Bug prevalence 只影响工期，不影响 correctness requirement。

### 4.5 P1-T4：Atom-mapping adapter

实现：

- mapper adapter；
- name/version/parameters；
- map uniqueness；
- heavy-atom coverage；
- changed-atom coverage；
- symmetry ambiguity；
- resonance/tautomer ambiguity；
- timeout/failure；
- fallback status。

测试：

- fully/partially/unmapped；
- duplicate map IDs；
- missing maps；
- mapper failure；
- atom-order permutation；
- multi-fragment；
- symmetric atoms；
- mapped reactants/unmapped products。

Gate：

- MCS-only 不进入 strict；
- center pairs 不称 full mapping；
- formal mapping 不称 mechanism。

### 4.6 P1-T5：Participant roles 与 donor eligibility

实现：

- transformed substrate/product；
- co-substrate；
- cofactor/carrier；
- coproduct；
- spectator；
- unknown。

特征：

- mapping retention；
- changed atoms；
- transferred atoms；
- size/complexity；
- stoichiometry；
- source annotations；
- `COFACTORS` prior；
- direction。

测试：

- COFACTORS 不删除 participants；
- O2/H2O/CO2 保留；
- 小分子可为真实 transformed substrate；
- NAD(P) retrieval 降权但 evidence 保留；
- role ambiguity 保留。

### 4.7 P1-T6：Bipartite fragment-lineage graph

实现：

- reactant→product graph；
- mapped overlap；
- retention/origin fractions；
- changed-atom participation；
- transfer edges；
- split/merge；
- ambiguity sets；
- stable lineage IDs。

禁止：

- independent side picking；
- tuple max tie；
- forced primary pair。

回归：

- proline hydroxylation；
- redox with NAD(P)；
- oxygen incorporation；
- hydrolysis；
- transferase；
- decarboxylation；
- cleavage；
- condensation；
- tie；
- partial mapping；
- MCS fallback。

### 4.8 P1-T7：SourceReactionLedger

实现：

- complete participants；
- stoichiometry；
- formal atom transfer；
- mechanism evidence separation；
- source/sink；
- element/charge；
- H/proton/electron policy；
- cofactor changes；
- source/mapping completeness；
- unknowns；
- status。

测试：

- redox；
- O2 incorporation；
- hydrolysis；
- decarboxylation；
- transfer；
- charge mismatch；
- missing stoichiometry；
- incomplete source；
- ambiguous formal assignment。

### 4.9 P1-T8：CandidateAnalogyLedger skeleton

实现 source→candidate adaptation schema：

- adaptation map；
- inherited donor context；
- assumptions；
- formal balance；
- unknown actual co-substrates/cofactors/stoichiometry；
- source ledger linkage。

此阶段可先用 fixtures，不需要完整 generator。

### 4.10 P1-T9：Eligibility/quarantine engine

实现 P0 matrix：

- strict eligible；
- partial eligible；
- diagnostic only；
- quarantine；
- reason codes；
- warnings。

测试每个矩阵单元。

### 4.11 P1-T10：Snapshot builder

流程：

```text
source load
→ normalization
→ mapping
→ roles
→ lineage
→ source ledger
→ eligibility
→ production index/quarantine
→ manifest/hash
```

Manifest：

- source hashes；
- schemas；
- mapper/resolver/ledger versions；
- policies；
- included/quarantine counts；
- reasons；
- snapshot hash。

测试：

- deterministic rebuild；
- source change → new hash；
- quarantine in manifest；
- production excludes quarantine；
- interrupted build not marked complete；
- read-only load。

### 4.12 P1-T11：Manual audit protocol

定义：

- stratification；
- sample size；
- double annotation；
- disagreement；
- catastrophic error；
- mapping/role/lineage/ledger rubrics；
- confidence interval；
- pass threshold。

覆盖：

- reaction class；
- participant count；
- mapping quality；
- cofactor pattern；
- source；
- ledger status；
- quarantine reason。

### 4.13 Gate P1

1. Proline/2OG correctly resolved or quarantined；
2. catastrophic mismatch not indexed；
3. critical tie not silently selected；
4. COFACTORS no data loss；
5. mapping/snapshot replayable；
6. formal/mechanistic labels correct；
7. dual-ledger schemas valid；
8. eligibility matrix enforced；
9. audit complete；
10. all filters counted/reasoned。

P1 未通过，不做 candidate performance 承诺。

---

## 5. P2 — Mini Snapshot、Truth、Isolation、Pilot

### 5.1 目标

用小而可信的 train/test evidence 验证端到端科学链和评估工具，不使用 oracle donor。

### 5.2 P2-T1：Mini snapshot

20–50 个 audited cases，覆盖：

- single/multi reactant；
- single/multi product；
- oxidation/reduction；
- hydroxylation；
- hydrolysis；
- transfer；
- cleavage；
- multiple sites；
- no site；
- OOD；
- mapping ambiguity；
- invalid input；
- equivalent SMILES；
- stereo；
- known lineage regressions。

要求：

- test X/labels 独立；
- train evidence 不含 test reactions；
- 难例不因 group 构造失败而删除。

### 5.3 P2-T2：Multi-answer truth

实现：

```text
allowed_product_set
context tags
tautomer equivalence
salt/neutralization
stereo-sensitive
stereo-agnostic
multi-product target
annotation completeness
```

测试：

- multiple true Y；
- equivalent SMILES；
- stereo switch；
- incomplete annotation。

### 5.4 P2-T3：Fold-specific views

```text
train evidence
validation/calibration
test labels
```

Guards：

- test IDs inaccessible；
- scorer/reference train-only；
- cache key includes fold；
- Agent resources hide labels。

### 5.5 P2-T4：Stage funnel

记录：

```text
input_valid
donor_retrieved
correct_donor_available
lineage_resolved
correct_transform_built
correct_site_enumerated
correct_candidate_generated
candidate_validated
candidate_ranked_top_k
answered_or_abstained
```

每个 miss 有 primary reason。

### 5.6 P2-T5：Baselines

至少：

1. random order；
2. generation order；
3. nearest donor；
4. fixed Morgan top-K；
5. legacy template；
6. deterministic strict kernel；
7. oracle donor upper bound，仅诊断。

### 5.7 P2-T6：Non-oracle pilot

正式 pilot：

- 只输入 X；
- automatic train-only donor；
- no human T/site hints；
- 记录 stage/cost/tool failures；
- oracle upper bound 分开。

Pilot 之前允许的只是 UI/protocol smoke test。

不预设未经数据证明的：

```text
T accuracy >= 70%
Y accuracy >= 40%
```

Go/No-Go 根据：

- data integrity；
- retrieval availability；
- failure funnel；
- deterministic slice viability；
- Agent research value

形成报告后再定。

### 5.8 Gate P2

1. Mini snapshot audited；
2. leakage = 0；
3. multi-answer truth operational；
4. all X denominator；
5. funnel operational；
6. donor automatic；
7. oracle separated；
8. pilot report and decision。

---

## 6. P3 — Strict One-Step Kernel

### 6.1 目标

实现不依赖 LLM 的 mandatory baseline：

```text
X
→ normalize
→ adaptive donor retrieval
→ complete reaction load
→ mapped lineage
→ strict transform
→ conditioned sites
→ deterministic product
→ validation + dual ledger
→ canonical candidates
```

### 6.2 P3-T1：Query normalization

版本化：

- parse/sanitize；
- canonical SMILES；
- charge；
- salt/mixture；
- tautomer；
- isotope；
- stereo；
- identity hash。

测试：

- equivalent SMILES；
- atom permutation；
- invalid；
- salts；
- multi-fragment；
- explicit/implicit H；
- charge；
- stereo。

### 6.3 P3-T2：Adaptive distinct-donor retrieval

实现：

```text
X → distinct A → complete reactions
```

Baseline：

- Morgan；
- size/charge；
- donor eligibility；
- source/lineage quality；
- identity diversity。

可扩：

- scaffold；
- functional groups；
- local environment；
- transform diversity。

测试：

- duplicate reaction rows not crowding；
- quarantine excluded；
- fold isolation；
- deterministic ties；
- stop reason；
- config/version manifest。

### 6.4 P3-T3：Complete reaction loader

返回：

- donor；
- eligible complete reactions；
- participants；
- mapping；
- lineages；
- source ledger；
- transforms；
- provenance。

禁止：

- only A/B SMILES；
- cofactor stripping；
- mirror records as independent。

### 6.5 P3-T4：Strict transformation extraction

提取：

- mapped edits；
- bond delete/add/order；
- atom attributes；
- transferred atoms；
- donor site；
- local environment；
- strict preconditions；
- ledger requirements；
- canonical transform hash。

测试：

- replay；
- atom-order invariance；
- canonicalization；
- duplicate support；
- partial-map rejection；
- source trace。

### 6.6 P3-T5：Conditioned sites

实现：

- transform precondition matching；
- stable site IDs；
- symmetry dedup；
- ambiguity groups；
- local environment；
- failed preconditions。

测试：

- multiple/symmetric/no site；
- wrong group；
- aromatic/aliphatic；
- charge；
- atom-order。

### 6.7 P3-T6：Deterministic graph-edit generation

实现：

- transform + site；
- versioned compiler；
- edit application；
- sanitize；
- canonicalize；
- dedup；
- GenerationReport；
- typed failures。

回归：

```text
CCCCCCCCO → CCCCCCCC=O
```

测试：

- bond changes；
- atom properties；
- transferred atom；
- multi-fragment；
- invalid valence；
- aromaticity；
- duplicate products；
- multiple paths。

### 6.8 P3-T7：Candidate validation

实现：

- molecule validation；
- transform fidelity；
- precondition recheck；
- formal source accounting；
- CandidateAnalogyLedger；
- strict invariants。

Reject：

- invalid molecule；
- edit mismatch；
- missing required heavy-atom source；
- critical ledger contradiction；
- relaxation in strict；
- critical ambiguity。

### 6.9 P3-T8：Canonical candidate store

```text
candidate_id
canonical_product
lane
origin
generation_paths[]
support_lineage_ids[]
transformation_ids[]
site_ids[]
validation
source_ledger_ids[]
candidate_analogy_ledger
provenance
```

相同结构合并，证据不丢失。

### 6.10 P3-T9：Deterministic predictor

生命周期到：

```text
RECEIVED
NORMALIZED
BASELINE_EVIDENCE_LOADED
HYPOTHESES_COMPILED
SITES_ENUMERATED
CANDIDATES_VALIDATED
```

此阶段可输出 unranked validated strict candidates + stage trace。

### 6.11 Gate P3

1. X-only automatic end-to-end；
2. strict candidate replayable；
3. donor/reaction/lineage/transform/site/dual-ledger complete；
4. equivalent SMILES invariant；
5. no LLM structure creation；
6. system failure/abstention separate；
7. pilot funnel operational；
8. octanol carbon regression correct；
9. formal mapping not mechanism；
10. candidate donor context labeled assumptions。

---

## 7. P4 — Evidence、Ranking、Applicability、Abstention

### 7.1 P4-T1：Independent evidence identity

去重：

- source lineage；
- database mirrors；
- same publication；
- same normalized reaction；
- mapper duplicates；
- same donor-transform evidence。

测试 duplication 不增加 support count。

### 7.2 P4-T2：Support aggregation

聚合：

- donor similarity；
- transform recurrence；
- site compatibility；
- mapping/lineage；
- source quality；
- ledger；
- independent support；
- retrieval stability。

每特征引用 evidence IDs。

### 7.3 P4-T3：Counterevidence

仅：

- competing transform；
- failed preconditions；
- site incompatibility；
- invalid generation；
- ledger contradiction；
- provenance/direction/role conflict。

测试：

- database absence not negative；
- no second enzyme not negative；
- train-only。

### 7.4 P4-T4：Baseline ranker

- versioned feature vector；
- configurable weights；
- strict-only ranking；
- ablations；
- not probability。

### 7.5 P4-T5：Applicability

```text
in_domain
near_domain
out_of_domain
conflicted
unknown
```

Structural only。

### 7.6 P4-T6：Typed abstention

实现 official precedence：

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

System failures 走 `failed`。

### 7.7 P4-T7：PredictionResult

Enforce：

```text
completed/predicted → >=1 candidate
abstained → 0 candidate + reason
partial → partial_reason
failed → infrastructure error
```

### 7.8 P4-T8：Immutable run、trace、manifest

实现：

- request hash；
- snapshot/config；
- component versions；
- D/T/S/Δ/Y/L/R/A trace；
- result hash；
- freeze；
- replay。

测试：

- same request result hash；
- frozen immutable；
- child run preserves parent。

### 7.9 Gate P4

- ranked strict top-K or typed abstention；
- absence not negative；
- support/conflict traceable；
- no probability label；
- system failure separate；
- selective metrics computable；
- full trace persisted。

---

## 8. P5 — Full Snapshot and Rebuilt Benchmark

### 8.1 P5-T1：Full snapshot

输出：

- production index；
- quarantine；
- manifest；
- quality distributions；
- mapping/lineage/ledger audit。

报告：

- source counts；
- pre/post normalization；
- included/quarantine；
- duplicate；
- unresolved。

### 8.2 P5-T2：Rebuilt examples

从正确 lineage 构造：

- X；
- allowed Y set；
- context；
- donor availability；
- transform/site truth；
- ambiguity；
- provenance；
- fold eligibility。

### 8.3 P5-T3：Splits

```text
exact-X
scaffold
transformation-family
source
time
OOD challenge
```

Source/time provenance 不足则报告 unavailable，不伪造。

### 8.4 P5-T4：Legacy baselines

同数据同 split：

- Morgan；
- template；
- DRFP feature；
- random/order；
- nearest donor；
- v2/final deterministic strict。

### 8.5 P5-T5：Six-layer reports

每 split：

- data；
- retrieval；
- transform/site；
- generation；
- rank/abstention；
- cost/runtime。

全部 N/CI/coverage/reasons。

### 8.6 P5-T6：Formal performance gates

看结果后冻结：

- donor recall；
- candidate recall；
- valid rate；
- top-K；
- risk at coverage；
- catastrophic error；
- unexplained failure。

不复制旧目标。

### 8.7 Gate P5

1. Leakage = 0；
2. all filters reported；
3. multi-answer active；
4. strict metrics complete；
5. baselines fair；
6. formal KPIs recorded；
7. go/no-go for service。

---

## 9. P6 — MCP Service

### 9.1 Entry

P1–P5 全通过。

### 9.2 P6-T1：High-level contracts

```text
reaction.predict_analogical_products_v1
reaction.get_run_v1
reaction.get_candidate_evidence_v1
reaction.expand_evidence_v1
```

### 9.3 P6-T2：Strict JSON schemas

- additionalProperties false；
- enums/versions；
- required fields；
- limits；
- typed errors；
- cross-field validation；
- golden schemas。

### 9.4 P6-T3：Idempotency

Request：

```text
client_request_id
idempotency_key
snapshot_id
budgets
```

Server：

```text
canonical request hash + snapshot/version + engine version
→ reuse or exactly one run
```

测试：

- repeat；
- concurrent duplicate；
- same key/different payload；
- interrupted write；
- child expansion。

### 9.5 P6-T4：Side effects

- predict = run write；
- get = read；
- local expand = child run；
- external absent from MVP。

### 9.6 P6-T5：Resources

Opaque URI、access control、tenant binding、retention。

### 9.7 P6-T6：Contract/chaos

- malformed；
- unknown；
- stale snapshot；
- missing resource；
- storage interruption；
- budgets；
- concurrency；
- protocol mismatch；
- large payload；
- partial tool failure。

### 9.8 Gate P6

- schemas match；
- invariants；
- idempotency；
- immutable；
- side effects accurate；
- typed failures；
- usable without LLM。

---

## 10. P7 — Production Grounded LLM Agent

### 10.1 目标

让 LLM 在 evidence-derived hypothesis space 中进行真实 T/S 选择、证据策略和冲突推理，同时不拥有结构和 scientific decision authority。

### 10.2 P7-T1：Provider adapter

- provider/model/revision；
- messages/tools；
- temperature/seed；
- budgets；
- structured output；
- retries。

Kernel 不固定 provider。

### 10.3 P7-T2：Mandatory baseline

Agent 首步必须获得 deterministic baseline run。

不能：

- 跳过 baseline；
- 直接调用低层 structure generator；
- 访问 test labels。

### 10.4 P7-T3：ProductionSelectionHypothesis

实现：

- ID validation；
- transform/site exists；
- support exists；
- rationale summary；
- policy version；
- priority only。

Agent 可：

- expand local evidence；
- compare IDs；
- choose T/S；
- prioritize；
- stop retrieval/request decision。

Agent 不可：

- create structure；
- mutate rank/lane/ledger；
- write abstention。

### 10.5 P7-T4：Grounding guard

- IDs belong to run；
- structures from typed result；
- rank/lane/ledger immutable；
- unsupported claims rejected/marked；
- unknown IDs error。

### 10.6 P7-T5：Reporter

输出：

- normalized X；
- decision；
- strict top-K；
- donor/reaction/transform/site；
- Source/Candidate Ledger summaries；
- applicability；
- support/conflicts；
- limitations；
- abstention。

Host 渲染 structure/scores/IDs。

### 10.7 P7-T6：No-invention/adversarial

诱导：

- invented candidates；
- score changes；
- generalized→strict；
- unknown evidence；
- evidence prompt injection；
- absence→negative；
- enzyme probability；
- tool failure guessing；
- abstention override。

硬门：

```text
invented candidate ID = 0
invented evidence ID = 0
structure mutation = 0
abstention override = 0
failed→abstained confusion = 0
schema adherence = 100%
```

### 10.8 P7-T7：Agent incremental evaluation

比较：

1. deterministic baseline；
2. Agent evidence expansion/selection；
3. fixed non-agent expansion。

指标：

- candidate recall；
- ranking/risk；
- abstention；
- evidence quality；
- tool calls；
- latency/token/cost；
- repeated-run agreement。

### 10.9 Gate P7

- No invention；
- measurable policy contribution；
- baseline mandatory；
- kernel replayable；
- provider failure typed；
- report matches result；
- permissions resist injection。

---

## 11. P8 — Generalized Lane

### 11.1 Entry

Strict one-step 达到 P5 gates；Production 不依赖 generalized 才可用。

### 11.2 P8-T1：Relaxation policy

冻结：

- allowed relaxations；
- forbidden hard constraints；
- distance；
- OOD；
- version。

### 11.3 P8-T2：Generalized hypothesis

记录：

```text
relaxation_policy_id
allowed_relaxation_ids
failed_strict_conditions
generalization_distance
source transforms
validation
```

### 11.4 P8-T3：Independent rank/abstain

- lane-only ranking；
- no cross-lane raw score；
- exploratory UI；
- no strict masquerade。

### 11.5 P8-T4：Benchmark

- incremental recall；
- false additions；
- risk–coverage；
- distance buckets；
- OOD；
- cost。

### 11.6 Gate P8

- policy versioned；
- strict untouched；
- separate report；
- user semantics clear。

---

## 12. P9 — Research、External、Multi-step

### 12.1 AgentProposedHypothesis

实现 final design schema 和 complete validation chain。

独立报告：

- new valid/correct/incorrect；
- reject reasons；
- incremental recall；
- risk；
- cost；
- reproducibility。

### 12.2 Graduation

Graduation package：

- hypothesis class；
- allowlist；
- held-out results；
- shift results；
- risk/coverage；
- grounding；
- cost；
- ADR；
- human approval。

未毕业不进入 production ranking。

### 12.3 External evidence

前置：

- source allowlist；
- license/provenance；
- cache；
- date/version；
- conflict policy；
- injection isolation；
- child-run separation；
- benchmark default off。

### 12.4 Multi-step candidate graph

```text
canonical molecule nodes
validated reaction edges
per-edge evidence/dual-ledger/lane
branch/beam
cycle detection
depth/cost/risk budgets
path deduplication
path uncertainty
stop rules
```

每条 edge 满足 one-step contract。

---

## 13. 测试矩阵

### 13.1 Unit

- schemas；
- normalize；
- mapping；
- roles；
- lineage；
- dual ledgers；
- eligibility；
- transform；
- sites；
- generation；
- validation；
- evidence identity；
- rank；
- abstain；
- request hash；
- hypothesis lanes。

### 13.2 Property/Metamorphic

- atom-order invariance；
- equivalent SMILES；
- duplicate evidence invariance；
- participant order invariance；
- snapshot hash；
- frozen run immutability；
- strict replay；
- lane non-contamination；
- formal/mechanistic label invariance。

### 13.3 Regression

- proline/2OG；
- octanol/octanal carbon count；
- leakage；
- all-X denominator；
- multiple Y；
- tie ambiguity；
- unknown heavy-atom source；
- source vs candidate ledger；
- system failure vs abstention；
- MCP naming；
- Result invariants；
- hypothesis lane origin。

### 13.4 Integration

- source→snapshot；
- snapshot→fold；
- X→strict candidates；
- X→abstention；
- predictor→run；
- MCP→resources；
- Agent→grounded report；
- AgentProposed isolation。

### 13.5 Evaluation

- multi-answer；
- CI；
- risk–coverage；
- lanes separated；
- all-X；
- fair baselines；
- label inaccessible；
- split capability gates；
- graduation metrics。

---

## 14. 必须生成的报告

### 14.1 P0

```text
ADR-0001..0006
schema_contract_report.md
authority_migration_report.md
```

### 14.2 Data

```text
legacy_lineage_audit.md/json
mapping_quality_report.md/json
snapshot_build_report.md/json
quarantine_report.md/json
manual_audit_report.md/json
source_ledger_quality.md/json
candidate_ledger_contract.md/json
```

### 14.3 Pilot

```text
mini_snapshot_manifest.json
pilot_preregistration.md
pilot_funnel.json
pilot_results.md
pilot_go_no_go.md
```

### 14.4 Benchmark

```text
benchmark_manifest.json
split_report.md/json
leakage_audit.md/json
baseline_comparison.md/json
strict_metrics.md/json
selective_metrics.md/json
error_taxonomy.md/json
```

### 14.5 MCP/Agent

```text
mcp_contract_report.md
idempotency_report.md
chaos_test_report.md
agent_grounding_report.md
agent_incremental_value.md
cost_latency_report.md
```

### 14.6 Post-MVP

```text
generalized_lane_report.md
agent_proposed_report.md
graduation_decision.md
external_evidence_audit.md
multistep_design.md
```

---

## 15. Stop Conditions

### 15.1 P0

- Authority conflict unresolved；
- hypothesis schemas ambiguous；
- ledger facts/assumptions mixed；
- no partial eligibility matrix；
- decision authority ambiguous；
- MCP side effects ambiguous。

### 15.2 Data

- catastrophic mismatch indexed；
- mapping not replayable；
- COFACTORS deletes participants；
- quarantine silently removed；
- partial source presented fully balanced；
- formal mapping presented mechanism；
- source/candidate ledger mixed。

### 15.3 Benchmark

- test evidence accessible；
- X silently dropped；
- single label mis-scores known multiple truth；
- no N；
- oracle in primary metrics；
- old numbers used as targets。

### 15.4 Kernel

- LLM/reporter creates structure；
- strict not replayable；
- required heavy atom no source；
- atom order changes candidates；
- system failure→abstention；
- donor assumptions presented candidate facts。

### 15.5 MCP/Agent

- unknown IDs pass；
- duplicate retry creates inconsistent runs；
- frozen run mutable；
- Agent changes rank/lane/ledger；
- prompt injection crosses permission；
- invented IDs nonzero；
- abstention override nonzero。

---

## 16. 安全并行

| 主线 | 可并行 |
|---|---|
| P0 ADRs | schema skeleton tests、fixture inventory |
| Mapping/lineage | audit protocol、gold fixtures |
| Ledgers | snapshot manifest/quarantine schema |
| Mini snapshot | metrics unit tests、baseline characterization |
| Strict kernel | run manifest prototype、MCP schema draft |
| Benchmark | provider adapter interface tests |
| MCP | adversarial cases、resource contract tests |

不能：

- 未过 lineage 就调 rank；
- 未隔离就报性能；
- 未过 kernel 就把 LLM output 当 candidate；
- 未过 strict 就主线开发 generalized/multi-step；
- 未 graduation 就把 agent_proposed 混入 production。

---

## 17. 执行批次

### Batch 0 — Contract

1. Authority ADR；
2. Hypothesis ADR；
3. Mapping/Ledger ADR；
4. Partial matrix；
5. Decision ADR；
6. MCP ADR；
7. Schema skeletons。

### Batch 1 — Data identity

1. Package；
2. Legacy audit；
3. Mapping adapter；
4. Roles；
5. Lineage graph；
6. Proline regression。

### Batch 2 — Complete evidence

1. Source ledger；
2. Candidate ledger skeleton；
3. Eligibility/quarantine；
4. Snapshot；
5. Manual audit；
6. Fold views。

### Batch 3 — Mini benchmark

1. Mini snapshot；
2. Multi-answer；
3. Isolation；
4. Funnel；
5. Baselines；
6. Pilot。

### Batch 4 — Strict vertical slice

1. Normalize；
2. Retrieve；
3. Load；
4. Transform；
5. Sites；
6. Generate；
7. Validate；
8. Candidate store。

### Batch 5 — Decision

1. Independent support；
2. Counterevidence；
3. Rank；
4. Applicability；
5. Abstention；
6. Run/trace/manifest。

### Batch 6 — Full benchmark

1. Full snapshot；
2. Rebuilt truth；
3. Splits；
4. Baselines；
5. Reports；
6. KPI freeze。

### Batch 7 — Service/Agent

1. MCP contracts；
2. Idempotency/resources；
3. Chaos；
4. Provider；
5. Production selection；
6. Grounding/reporting；
7. Incremental evaluation。

---

## 18. Definition of Done

### 18.1 P0 done

- Final authority reflected in README；
- Six ADRs approved；
- schemas frozen；
- old docs historical；
- no unresolved contract ambiguity。

### 18.2 Data foundation done

- mapping/version/quality；
- multi-lineage graph；
- COFACTORS non-destructive；
- dual ledgers；
- partial matrix；
- snapshot/quarantine；
- audit。

### 18.3 Strict kernel done

- X-only；
- automatic donor；
- complete reaction；
- correct A→B；
- strict transform/site；
- deterministic Y；
- dual-ledger validation；
- top-K/abstain；
- replay。

### 18.4 Benchmark done

- multi-answer；
- train-only；
- all-X；
- splits；
- six layers；
- selective；
- N/CI；
- fair legacy comparison。

### 18.5 MCP done

- contracts；
- side effects；
- idempotency；
- immutable resources；
- typed errors；
- chaos。

### 18.6 Agent done

- mandatory baseline；
- evidence-space T/S selection；
- grounded IDs；
- no structure mutation；
- no decision override；
- provider/tool/prompt manifest；
- measurable incremental value。

---

## 19. 第一轮立即执行内容

获得用户开始实施授权后，第一轮只执行 P0：

1. 创建 `docs/decisions/`；
2. 写 ADR-0001 authority/scope；
3. 写 ADR-0002 hypothesis lanes；
4. 写 ADR-0003 mapping/dual-ledger semantics；
5. 写 ADR-0004 partial eligibility；
6. 写 ADR-0005 decision authority；
7. 写 ADR-0006 MCP side effects；
8. 创建 schema skeleton tests；
9. 更新 README 权威指向；
10. 运行 contract consistency checks。

P0 不做：

- MCP server；
- LLM prompt/policy；
- candidate predictor；
- generalized；
- external evidence；
- multi-step；
- performance claims。

---

## 20. 最终执行结论

实施路线冻结为：

> **先冻结三方共同契约，再修复反应事实和评估尺子；随后证明 strict one-step deterministic baseline；再建立 support/ranking/abstention 和正式 benchmark；之后封装 MCP，让 LLM 在 evidence-derived T/S space 中真实参与推理；novel LLM hypotheses 始终先进入独立 agent_proposed lane，并靠 held-out evidence graduation。**

第一版最终必须能够诚实回答：

```text
“根据这些版本化 donor 完整反应、
已解析的 A→B fragment lineage、
可重放 transformation 和兼容位点，
X 有这些 strict structural analogy candidates。

这是 SourceReactionLedger、CandidateAnalogyLedger、
support/conflict、适用边界和 provenance。

如果证据不足，系统明确拒答。
如果基础设施失败，系统明确报错而不是猜测。”
```

