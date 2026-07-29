> **HISTORICAL / NON-AUTHORITATIVE**
> This document is retained for decision history only.
> Current implementation authority: `plan/final_design.md`, `plan/final_plan.md`, `plan/final_discussion.md`.

# ChatGPT Plan v2 — Reaction Analogy MCP Agent Implementation Plan

> 日期：2026-07-29  
> 状态：可执行的权威实施计划  
> 配套设计：`chatgpt-reaction-analogy-agent-design-v2.md`  
> 工作根目录：`CC/branch/ReactionAgent/demov2/`  
> 首版目标：只输入 `X`，自动检索 donor `A` 和完整反应，可靠生成、验证并排序 one-step strict structural analogy 候选 `Y`，或 typed abstain。  
> 执行纪律：测试先行；数据地基不过门，不进入正式 MCP/Agent；旧 benchmark 数字在重建前不得作为验收承诺。

---

## 0. 计划如何使用

### 0.1 权威关系

实现过程中：

1. 产品语义、科学边界和职责划分以 design v2 为准；
2. 任务顺序、交付物、测试和质量门以本 plan v2 为准；
3. 旧 ChatGPT、Claude、Qwen design/plan/discussion 仅作为背景资料；
4. 现有 `UNIFIED_*` 文件是过程草案，不覆盖本 v2；
5. 如果实现发现设计与真实数据冲突，先写 decision record，再修订 v2，不能静默改变口径。

### 0.2 最短关键路径

```text
P0 契约冻结
→ P1 mapping / participant / lineage / ledger / snapshot
→ P2 mini snapshot / fold isolation / evaluation skeleton
→ P3 strict one-step kernel
→ P4 support / ranking / applicability / abstention
→ P5 full snapshot / rebuilt benchmark
→ P6 MCP
→ P7 production LLM Agent
```

后置：

```text
P8 generalized
P9 research hypothesis / external evidence / multi-step
```

### 0.3 Gate 原则

每个 Phase 都有进入条件和退出条件。未通过 Gate：

- 可以修 bug、补测试、完善该 Phase；
- 可以并行做不依赖科学结论的 schema/fixture/tooling；
- 不得对外宣称后续能力已可靠；
- 不得用后续模块掩盖地基问题。

---

## 1. 目标目录结构

计划采用隔离的 `demov2/reaction_agent/` 包，不直接在旧核心代码上大规模改写：

```text
CC/branch/ReactionAgent/demov2/
├── pyproject.toml
├── README.md
├── plan/
│   ├── chatgpt-reaction-analogy-agent-design-v2.md
│   └── chatgpt-reaction-analogy-agent-plan-v2.md
├── reaction_agent/
│   ├── __init__.py
│   ├── config.py
│   ├── schemas/
│   │   ├── common.py
│   │   ├── evidence.py
│   │   ├── lineage.py
│   │   ├── transform.py
│   │   ├── candidate.py
│   │   ├── result.py
│   │   └── errors.py
│   ├── chemistry/
│   │   ├── normalize.py
│   │   ├── mapping_adapter.py
│   │   ├── roles.py
│   │   ├── lineage.py
│   │   ├── ledger.py
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
│   │   └── provenance.py
│   ├── inference/
│   │   ├── baseline.py
│   │   ├── support.py
│   │   ├── counterevidence.py
│   │   ├── features.py
│   │   ├── rank.py
│   │   ├── applicability.py
│   │   ├── abstain.py
│   │   └── predictor.py
│   ├── runtime/
│   │   ├── lifecycle.py
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
│   │   └── research_hypothesis.py
│   └── evaluation/
│       ├── truth.py
│       ├── splits.py
│       ├── metrics.py
│       ├── funnel.py
│       ├── baselines.py
│       └── reports.py
├── scripts/
│   ├── audit_legacy_labels.py
│   ├── build_snapshot.py
│   ├── audit_snapshot.py
│   ├── build_mini_benchmark.py
│   ├── run_pilot.py
│   ├── run_benchmark.py
│   └── replay_run.py
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   ├── contracts/
│   ├── regression/
│   └── evaluation/
└── reports/
    ├── data_audit/
    ├── pilot/
    ├── benchmark/
    └── manifests/
```

目录可在实现时小幅调整，但模块边界不得把：

- evidence ingestion；
- scientific chemistry；
- ranking/decision；
- MCP；
- LLM Agent；
- evaluation

重新混成一个不可测试文件。

---

## 2. 全局实施规则

### 2.1 代码与数据

- 新实现优先放在 `demov2`，旧代码默认只读。
- 复用旧函数前先写 characterization test。
- 原始来源数据和规范化 snapshot 分开保存。
- Snapshot immutable、content-addressed。
- Quarantine 是显式数据集，不是异常垃圾桶。
- 任何过滤都必须记录过滤前后数量和 reason。

### 2.2 类型和失败

- 核心 schema 使用严格类型，未知字段默认拒绝。
- 每个科学阶段返回 typed success 或 typed scientific failure。
- 基础设施异常返回 typed system failure。
- 禁止捕获异常后静默返回 `[]`。
- `failed` 不得被转换为 `abstained`。

### 2.3 化学结构权

- 只有 `chemistry.generate` 可以创建候选分子结构。
- LLM、MCP reporter 和 ranking 模块不得构造或修改 SMILES。
- 每个 candidate 必须引用 transform ID、site ID、generation report 和 validation report。
- strict candidate 必须可从 snapshot evidence 重放。

### 2.4 Benchmark

- 测试时只提供 `X`，不提供 oracle donor。
- 检索、support、counterevidence、ranking reference 全部 train-only。
- 所有输入 `X` 进入总分母；无法构造 group 的记录不能无声消失。
- 多答案、tautomer、盐、中性化和 stereo policy 必须预注册。
- 每个指标报告 `N` 和置信区间。

### 2.5 分数

- `ranking_score` 不是 probability。
- 固定权重只是 baseline。
- 校准必须使用独立 validation/calibration data。
- 在 Brier/ECE/risk–coverage 验证前禁止 `calibrated_probability` 字段。

### 2.6 Agent

- 生产 Agent 必须先调用确定性 baseline。
- Agent 只引用真实 IDs。
- Agent prompt、model、provider、revision、temperature、seed、tool schema hash 都进入 manifest。
- Provider 通过 adapter 注入，不在核心逻辑中固定某一家模型。

---

## 3. Phase 0 — 契约冻结与旧结论降级

### 3.1 目标

在写科学实现前消除 design/plan 内部矛盾，冻结第一版产品边界。

### 3.2 任务

#### P0-T1：建立 v2 决策记录

交付：

- `docs/decisions/` 或 plan 内 decision register；
- 明确 design v2/plan v2 权威；
- 列出被取代文档；
- 记录首版只做 strict one-step。

验收：

- README 指向 v2；
- 不再把旧 design 称为当前定稿。

#### P0-T2：冻结产品术语

统一：

```text
query molecule X
donor molecule A
complete donor reaction
transformed lineage A→B
strict structural analogy
generalized structural analogy
ranking_score
typed abstention
reaction_ledger
manifest_uri
```

删除或降级模糊词：

```text
confidence
enzyme probability
primary A/B pair
cofactor stripping
LLM-generated product
```

#### P0-T3：冻结非目标

明确不在 MVP：

- multi-step；
- external open-world retrieval；
- generalized generation；
- research LLM hypothesis；
- enzyme activity probability；
- kinetics；
- environmental occurrence。

#### P0-T4：旧指标标记 provisional

在相关报告/README 中标记：

- 旧 A1/A2；
- retrieval ceiling；
- generation recall；
- 79.5% 等旧结果

均需重跑，不可作为 v2 KPI。

### 3.3 Gate P0

- v2 术语无冲突；
- design/plan 字段统一；
- 旧指标无正式承诺；
- scope 被写入 README；
- 团队知道第一条科学关键路径是 lineage/ledger，不是 MCP UI。

---

## 4. Phase 1 — 数据地基

### 4.1 目标

建立可信的完整反应表示、atom-mapping adapter、fragment-lineage graph、Reaction Ledger、snapshot 和 quarantine。

### 4.2 P1-T1：严格 domain schemas

创建：

- `ReactionParticipant`
- `MappingReport`
- `LineageEdge`
- `LineageHypothesis`
- `LineageResolution`
- `ReactionLedger`
- `QualityReport`
- `ReactionEvidence`
- `QuarantineRecord`

关键测试：

- unknown field 被拒绝；
- stable ID 可重复生成；
- 同一规范化输入产生相同 content hash；
- 不允许空 provenance；
- strict lineage 必须有 mapping report；
- ledger status 只能使用 v2 三个正式值。

退出条件：

- schemas 能表示 single、multi-reactant、multi-product、split、merge、ambiguous lineage；
- 不再要求每条反应只有一个 primary pair。

### 4.3 P1-T2：Legacy label audit

实现只读审计：

1. 重放现有 `canonical_identity.transformed_pair`；
2. 统计每条反应选中的 reactant/product；
3. 与 mapping overlap/changed atoms 对比；
4. 检测 cross-lineage mismatch；
5. 输出按 reaction class、participant count、cofactor pattern 分层的发生率；
6. 输出具体样例和 source IDs。

必须包含回归案例：

```text
2-oxoglutarate + proline + O2
→ succinate + hydroxyproline + CO2
```

报告：

```text
reports/data_audit/legacy_lineage_audit.json
reports/data_audit/legacy_lineage_audit.md
```

注意：

- 无论 bug 占比高低，v2 label 都必须按正确 lineage 重建；
- 发生率只决定迁移成本，不决定是否允许保留错误算法。

### 4.4 P1-T3：Atom-mapping adapter

实现：

- 统一 mapper 输入输出；
- 记录 mapper name/version/parameters；
- 验证 map-number uniqueness；
- 计算 mapped heavy atom fraction；
- 计算 changed-atom coverage；
- 标记 ambiguity；
- 支持明确的 fallback status。

测试矩阵：

- fully mapped；
- partial mapping；
- duplicate map numbers；
- missing maps；
- mapper failure；
- atom-order permutation；
- salts/multiple fragments；
- mapped reactants but unmapped products。

质量门：

- strict lane 不接受 unmapped/MCS-only evidence；
- mapper failure 进入 typed quarantine；
- center pairs 不会被误称为完整 mapping。

### 4.5 P1-T4：Participant roles 与 donor eligibility

实现 role hypotheses：

- transformed substrate/product；
- co-substrate；
- cofactor/carrier；
- coproduct；
- spectator；
- unknown。

输入特征：

- mapping retention；
- changed atom participation；
- transferred atoms；
- size/complexity；
- stoichiometry；
- source annotations；
- static `COFACTORS` prior；
- reaction side/direction。

明确测试：

- `COFACTORS` 名单中的物质不会从完整 reaction evidence 删除；
- O2/H2O/CO2 被 ledger 保留；
- 小分子可在合适案例成为 transformed substrate；
- NAD(P) 等在 retrieval projection 中可降权，但原始 participants 不丢失；
- role ambiguity 被保留。

### 4.6 P1-T5：Bipartite fragment-lineage graph

实现：

- reactant participant → product participant bipartite graph；
- mapped overlap；
- retention/origin fractions；
- changed-atom participation；
- transfer edges；
- split/merge hypotheses；
- ambiguity sets；
- stable lineage IDs。

禁止：

- 两侧独立挑片段；
- 使用 tuple `max()` 静默解 tie；
- 强迫单一 primary lineage。

回归测试：

- proline hydroxylation；
- oxidation with NAD(P)；
- transferase；
- decarboxylation；
- hydrolysis；
- cleavage into two products；
- condensation of two substrates；
- participant tie；
- partial mapping；
- MCS fallback。

质量门：

- 已知 cross-lineage mismatch 不进入生产 index；
- ambiguous case 返回 ambiguity 或 quarantine；
- 多条可确定 lineage 可并存。

### 4.7 P1-T6：Reaction Ledger

实现：

- complete participant entries；
- stoichiometry；
- atom-transfer sources/sinks；
- element balance；
- charge balance；
- H/proton/electron policy；
- cofactor changes；
- source completeness；
- mapping completeness；
- unknowns；
- source-to-candidate linkage。

正式状态：

```text
fully_balanced_explicit_reaction
heavy_atom_balanced_with_implicit_h_e_policy
partial_or_unbalanced_source
```

测试：

- oxidation/reduction；
- oxygen incorporation from O2；
- hydrolysis；
- decarboxylation；
- transfer reaction；
- charge mismatch；
- missing stoichiometry；
- incomplete source；
- unknown atom source；
- candidate-derived ledger。

质量门：

- 不再只比较 `X/Y` 分子式；
- 新增重原子来源可追踪或明确 unknown；
- 来源不完整不会被伪装成 fully balanced。

### 4.8 P1-T7：Snapshot builder 与 quarantine

实现：

- source loader；
- normalization；
- mapping；
- role/lineage/ledger；
- quality gate；
- production index；
- quarantine index；
- manifest；
- content hash；
- deterministic rebuild。

Snapshot manifest 至少记录：

```text
source files/hashes
schema versions
mapper/resolver/ledger versions
normalization policy
included counts
quarantine counts by reason
build configuration
snapshot hash
```

测试：

- 相同输入和版本产生相同 snapshot hash；
- 源数据变化导致新 hash；
- quarantine 记录仍出现在 manifest；
- 生产索引不包含 quarantine；
- build 中断不留下伪完整 snapshot；
- snapshot 可只读加载。

### 4.9 P1-T8：分层人工审计协议

文档必须定义：

- 分层变量；
- 样本抽取；
- 双人审计；
- disagreement resolution；
- catastrophic error 定义；
- role/lineage/ledger 的判定表；
- 报告格式；
- 通过阈值。

最低覆盖：

- reaction class；
- participant count；
- mapping quality；
- cofactor pattern；
- source；
- ledger status；
- quarantine reason。

### 4.10 Gate P1

必须同时满足：

1. 已知 proline/2-oxoglutarate 案例正确解析或 quarantine；
2. catastrophic mismatch 不进入生产 index；
3. unresolved critical tie 不被静默选择；
4. `COFACTORS` 不造成完整反应信息丢失；
5. mapper/snapshot 可重放；
6. ledger status 正确；
7. 人工审计报告完成；
8. 所有过滤有数量和 reason。

Gate P1 未通过时，不做正式候选性能承诺。

---

## 5. Phase 2 — Mini snapshot、真值策略与评估骨架

### 5.1 目标

在全量工程之前，用小而可信的 evidence snapshot 和非 oracle 流程验证端到端科学链。

### 5.2 P2-T1：Mini evidence snapshot

构建 20–50 个经过人工审计的测试案例，并有足够 train donor evidence。

覆盖：

- single/multi reactant；
- single/multi product；
- oxidation/reduction；
- hydroxylation；
- hydrolysis；
- transfer；
- cleavage；
- multiple compatible sites；
- no compatible site；
- OOD；
- ambiguous lineage；
- invalid input；
- equivalent SMILES；
- stereochemistry；
- 已知回归案例。

要求：

- test X 和 labels 独立保存；
- train evidence 不包含 test reactions；
- 不因难例无法构造 group 而删除。

### 5.3 P2-T2：Multi-answer truth policy

实现：

- `allowed_product_set`；
- context tags；
- tautomer equivalence；
- salt/neutralization；
- stereo-sensitive；
- stereo-agnostic；
- multi-product target；
- incomplete annotation flag。

测试：

- 同一个 X 的多个真实 Y 不互相判错；
- equivalent SMILES 匹配；
- stereo policy 可切换；
- 未标注 generalized 产品不被误当严格 precision 真值。

### 5.4 P2-T3：Fold-specific evidence views

实现：

```text
train evidence store
validation/calibration store
test label store
```

静态检查和运行时 guard：

- test reaction/evidence ID 不出现在 retrieval；
- scorer/reference 不能读取 test；
- cache key 包含 fold/view；
- snapshot 资源 URI 不泄露 test labels 给 Agent。

### 5.5 P2-T4：六层漏斗

为每个 X 记录：

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

每个 miss 有唯一主要 reason 和可选 secondary reasons。

### 5.6 P2-T5：Baseline 定义

至少建立：

1. random candidate ordering；
2. generation order；
3. nearest-donor only；
4. fixed Morgan top-K；
5. legacy template transfer；
6. deterministic strict kernel，不含 LLM；
7. oracle donor upper bound，仅作诊断、不作生产结果。

### 5.7 P2-T6：非 oracle pilot protocol

运行时：

- 只输入 X；
- donor 自动检索；
- 不能人工提示 T/site；
- 记录每阶段结果；
- 记录工具调用、耗时和失败；
- 单独保存 oracle upper-bound 但不混入主指标。

### 5.8 Gate P2

- mini snapshot 人工审计完成；
- train/test evidence leakage 为零；
- 多答案策略可运行；
- 所有 X 进入分母；
- 六层漏斗能定位失败；
- 自动 donor retrieval 被证明，而不是人工供给。

---

## 6. Phase 3 — Strict One-Step Scientific Kernel

### 6.1 目标

实现不依赖 LLM 的可靠科学 baseline：

```text
X
→ normalize
→ adaptive donor retrieval
→ complete reaction load
→ mapped lineage
→ strict transform
→ conditioned sites
→ deterministic products
→ validation + ledger
→ canonical candidates
```

这既是生产系统的强制 baseline，也是评估 LLM 增量价值的对照组。

### 6.2 P3-T1：Query normalization

明确并版本化：

- parse/sanitize；
- canonical SMILES；
- charge policy；
- salt/mixture policy；
- tautomer policy；
- isotope policy；
- stereo policy；
- molecule identity hash。

测试：

- equivalent SMILES；
- atom-order permutation；
- invalid SMILES；
- salts；
- multi-fragment query；
- explicit/implicit H；
- charged forms；
- stereoisomers。

失败：

```text
INVALID_INPUT
UNSUPPORTED_QUERY_FORM
```

### 6.3 P3-T2：Adaptive distinct-donor retrieval

实现两阶段检索：

```text
X → distinct eligible A → complete reactions for A
```

最低 baseline 特征：

- Morgan similarity；
- structure size/charge compatibility；
- role/donor eligibility；
- source/lineage quality；
- donor identity diversity。

后续可加：

- scaffold；
- local environment；
- functional-group；
- transformation diversity。

停止条件：

- similarity gap；
- candidate/transform stability；
- diversity；
- OOD；
- budget。

测试：

- 同一 A 的重复 reaction 不占满 donor list；
- quarantine 不可检索；
- fold view 隔离；
- tie deterministic；
- stop reason 被记录；
- retrieval 权重和版本进入 manifest。

### 6.4 P3-T3：Complete reaction loader

返回：

- donor molecule；
- 全部 eligible complete reactions；
- participants；
- lineage；
- ledger；
- transformation hypotheses；
- provenance。

禁止：

- 只返回 A/B 两个 SMILES；
- 因 `COFACTORS` 删除完整 participant；
- 把多个来源镜像当独立反应。

### 6.5 P3-T4：Strict transformation extraction

从可信 lineage 提取：

- mapped atom edits；
- bond deletes/adds/order changes；
- atom attribute changes；
- transferred atoms；
- donor site；
- local environment；
- strict preconditions；
- ledger requirements；
- canonical transform hash。

测试：

- edit replay；
- input atom-order invariance；
- transform canonicalization；
- duplicate support aggregation；
- partial mapping rejection；
- source lineage traceability。

### 6.6 P3-T5：Transformation-conditioned sites

实现：

- 根据 transform preconditions 在 X 上枚举 site；
- stable site IDs；
- symmetry dedup；
- ambiguity groups；
- local environment matching；
- failed preconditions。

测试：

- multiple sites；
- symmetric sites；
- no site；
- wrong functional group；
- aromatic vs aliphatic mismatch；
- charge mismatch；
- atom-order invariance。

### 6.7 P3-T6：Deterministic graph-edit generation

实现：

- validated transform + eligible site；
- deterministic edit application；
- sanitize；
- canonicalize；
- deduplicate；
- GenerationReport；
- typed failure。

回归：

```text
1-octanol CCCCCCCCO
→ octanal CCCCCCCC=O
```

必须防止少碳错误。

测试：

- bond delete/add/change；
- atom property change；
- transferred atom；
- multi-fragment；
- illegal valence；
- aromaticity；
- duplicate products；
- multiple support paths。

### 6.8 P3-T7：Candidate molecule 和 reaction-analogy validation

实现：

- molecule validation；
- transform fidelity；
- site precondition recheck；
- atom-source accounting；
- candidate ledger；
- strict lane invariants。

strict rejection：

- invalid molecule；
- edit mismatch；
- missing required atom source；
- critical ledger contradiction；
- unapproved relaxation；
- unresolved critical ambiguity。

### 6.9 P3-T8：Canonical candidate store

每个 candidate：

```text
candidate_id
canonical_product
lane
generation_paths[]
support_lineage_ids[]
transformation_ids[]
site_ids[]
validation_report
reaction_ledger
provenance
```

相同结构合并，证据不丢失。

### 6.10 P3-T9：Deterministic predictor assembly

实现完整 strict pipeline 和内部 lifecycle：

```text
RECEIVED
NORMALIZED
BASELINE_EVIDENCE_LOADED
HYPOTHESES_COMPILED
SITES_ENUMERATED
CANDIDATES_VALIDATED
```

此阶段可先输出未排序 candidate set 和 stage report。

### 6.11 Gate P3

必须满足：

1. 只给 X 可自动完成端到端；
2. 每个 strict candidate 可重放；
3. 每个 candidate 有 donor/reaction/lineage/transform/site/ledger；
4. 等价 SMILES 得到相同 canonical candidate set；
5. LLM 不参与结构创建；
6. invalid/system failure/abstention 语义分开；
7. mini pilot 漏斗可运行；
8. 已知 octanol 回归正确保留 8 个碳。

---

## 7. Phase 4 — Support、Counterevidence、Ranking、Applicability、Abstention

### 7.1 P4-T1：Independent evidence identity

实现去重：

- source record lineage；
- database mirror；
- same publication；
- same normalized reaction；
- same mapper-derived duplicate；
- same donor-transform evidence。

测试：

- 镜像条目不增加 independent support count；
- 同一论文多个真正独立实验可按 policy 处理；
- identity policy 版本进入 manifest。

### 7.2 P4-T2：Support aggregation

为 candidate 聚合：

- donor similarity；
- transform recurrence；
- site compatibility；
- mapping/lineage quality；
- source quality；
- ledger completeness；
- independent support count；
- retrieval stability。

保留 per-feature evidence IDs。

### 7.3 P4-T3：Counterevidence

实现首版受限 counterevidence：

- competing transform；
- failed preconditions；
- site incompatibility；
- invalid generation；
- ledger contradiction；
- provenance conflict；
- source direction/role conflict。

测试：

- database absence 不产生 negative；
- no second enzyme 不产生 negative；
- conflict 可追溯；
- counterevidence 不能引用 test fold。

### 7.4 P4-T4：Baseline ranking

建立版本化 feature vector 和 baseline weights。

要求：

- weights 在配置中；
- 不称 probability；
- report 中可做 feature ablation；
- strict tier 内排序；
- generalized 尚未启用。

### 7.5 P4-T5：Applicability

实现：

```text
in_domain
near_domain
out_of_domain
conflicted
unknown
```

基于结构类比适用域，不基于未经验证的 enzyme activity。

### 7.6 P4-T6：Typed abstention

实现 precedence：

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

系统错误：

```text
SNAPSHOT_UNAVAILABLE
MAPPER_UNAVAILABLE
TOOL_PROTOCOL_ERROR
STORAGE_FAILURE
```

走 `failed`。

### 7.7 P4-T7：PredictionResult invariants

严格测试：

```text
completed/predicted → candidates >= 1
abstained → candidates == 0 and reason_code
partial → partial_reason
failed → system failure, not scientific abstention
```

### 7.8 P4-T8：Immutable run 和 manifest

实现：

- request hash；
- snapshot/version；
- configs；
- component versions；
- stage hashes；
- result hash；
- resource URIs；
- freeze。

重放测试：

- 相同 request/snapshot/config 得到相同 kernel result hash；
- frozen run 不可修改；
- child run 不修改 parent。

### 7.9 Gate P4

- ranked strict top-K 或 typed abstention；
- database absence 不被当 negative；
- strict 候选的证据和冲突可追溯；
- ranking_score 未被称为概率；
- system failure 不冒充拒答；
- selective metrics 可计算。

---

## 8. Phase 5 — 全量 Snapshot 和重建 Benchmark

### 8.1 目标

用通过 P1–P4 的实现重建完整 snapshot、labels、splits 和基线，正式设置性能门。

### 8.2 P5-T1：全量 snapshot build

输出：

- production evidence index；
- quarantine；
- manifest；
- source/quality distributions；
- mapping/lineage/ledger audit。

报告所有：

- source counts；
- pre/post normalization counts；
- included counts；
- quarantine counts；
- duplicate counts；
- unresolved counts。

### 8.3 P5-T2：重建 benchmark examples

从正确 lineage 构造：

- X；
- allowed Y set；
- context；
- donor availability；
- transform/site truth；
- ambiguity；
- source provenance；
- fold eligibility。

不能复用旧错误 A/B labels。

### 8.4 P5-T3：Splits

实现：

- exact-X；
- scaffold；
- transformation-family；
- source；
- time；
- OOD/abstention challenge。

source/time 数据质量不足时：

- 明确报告 unavailable；
- 不用猜测字段构造伪 split。

### 8.5 P5-T4：Legacy baselines 重跑

在相同新数据、相同 split 上重跑：

- legacy Morgan retrieval；
- template generation；
- DRFP ranking；
- random/generation order；
- nearest donor；
- v2 deterministic strict kernel。

### 8.6 P5-T5：六层报告

每个 split 分别报告：

- Layer 0 data；
- Layer 1 retrieval；
- Layer 2 transform/site；
- Layer 3 generation；
- Layer 4 ranking/abstention；
- cost/runtime。

全部带：

- N；
- confidence interval；
- coverage；
- reason distributions。

### 8.7 P5-T6：性能门设定

只有看到新 benchmark 后，才冻结：

- minimum donor recall；
- minimum candidate recall；
- minimum valid rate；
- target top-K；
- maximum risk at target coverage；
- maximum catastrophic error；
- maximum unexplained failure。

不能提前复制旧数字。

### 8.8 Gate P5

- test leakage 为零；
- 全部过滤有报告；
- multi-answer truth 生效；
- strict metrics 完整；
- legacy 与 v2 同数据对拍；
- 正式 KPI 已根据新结果记录；
- 数据地基和 scientific kernel 获得 go/no-go 结论。

---

## 9. Phase 6 — MCP Service

### 9.1 进入条件

P1–P5 通过；strict kernel 有明确性能和失败边界。

### 9.2 P6-T1：高层工具 contracts

实现：

```text
reaction.predict_analogical_products_v1
reaction.get_run_v1
reaction.get_candidate_evidence_v1
reaction.expand_evidence_v1
```

统一字段：

```text
manifest_uri
reaction_ledger
```

### 9.3 P6-T2：Strict JSON schemas

要求：

- `additionalProperties: false`；
- enum/version；
- required fields；
- length/range limits；
- typed errors；
- cross-field validation；
- schema golden files。

### 9.4 P6-T3：Idempotency

Predict request 包含：

```text
client_request_id
idempotency_key
snapshot_id
budgets
```

服务端：

```text
canonical request hash + snapshot/version
→ reuse existing immutable run or create exactly one run
```

测试：

- repeated call；
- concurrent duplicate；
- same idempotency key with different payload；
- interrupted write；
- child evidence expansion。

### 9.5 P6-T4：真实副作用标注

- snapshot/resource reads：read-only；
- predict：append/write immutable run；
- get tools：read-only；
- local evidence expansion：child-run write；
- future external retrieval：network I/O。

不得把所有工具统一标成 read-only/idempotent。

### 9.6 P6-T5：Resources

稳定 URI：

```text
reactionagent://runs/{run_id}
reactionagent://runs/{run_id}/manifest
reactionagent://runs/{run_id}/candidates/{candidate_id}
reactionagent://runs/{run_id}/evidence/{evidence_id}
reactionagent://snapshots/{snapshot_id}
```

IDs 和 URI 视为 opaque，不由 Agent 推导。

### 9.7 P6-T6：Contract 与 chaos tests

覆盖：

- malformed requests；
- unknown fields；
- unknown IDs；
- stale snapshot；
- missing resource；
- storage interruption；
- time/tool budget；
- concurrent requests；
- protocol version mismatch；
- large evidence payload；
- partial tool failure。

### 9.8 Gate P6

- schemas 和实现一致；
- invariants 全通过；
- predict 幂等；
- frozen run 不可改；
- side-effect annotation 正确；
- system failure 保持 typed；
- 无 LLM 也能完整使用工具。

---

## 10. Phase 7 — Production Grounded LLM Agent

### 10.1 目标

让 LLM 真正参与证据策略和冲突理解，同时不拥有结构创建权和科学字段覆盖权。

### 10.2 P7-T1：Provider adapter

统一接口：

- model/provider/revision；
- messages；
- tool schemas；
- temperature/seed；
- time/token budget；
- structured output；
- retry policy。

不要在 scientific kernel 固定 Kimi、OpenAI 或其他 provider。

### 10.3 P7-T2：Agent policy

允许动作：

```text
predict baseline
inspect run
inspect candidate evidence
expand local evidence with structured filters
compare returned IDs
stop and report
```

策略要求：

- baseline 必须先运行；
- Agent 不能跳过 hard gate；
- tool/time/token budget；
- 达到服务端 stop condition 时不能继续无限循环；
- 不能访问 test labels。

### 10.4 P7-T3：Grounding guard

校验：

- candidate IDs 属于 frozen run；
- evidence IDs 存在；
- product structure 来自 tool result；
- rank/lane/ledger 未被改写；
- 不支持的 claim 被标记或拒绝；
- unknown ID 触发 error。

### 10.5 P7-T4：Reporter

用户输出至少包括：

- normalized X；
- decision；
- strict top-K；
- 每个 candidate 的 donor/reaction/transform/site 摘要；
- Reaction Ledger 状态；
- applicability；
- support/conflict；
- limitation；
- abstention reason。

结构、分数、IDs 由 host 从 typed result 渲染，不依赖 LLM 手抄。

### 10.6 P7-T5：No-invention benchmark

测试：

- 诱导 Agent 编造候选；
- 诱导改分；
- 诱导把 generalized 称 strict；
- 诱导访问未知 evidence；
- 证据文本中的 prompt injection；
- 让 Agent 把数据库缺失说成 negative；
- 让 Agent 声称 enzyme probability；
- 工具失败时诱导其继续猜。

硬门：

```text
invented candidate ID = 0
invented evidence ID = 0
tool result structure mutation = 0
failed-as-abstained = 0
```

### 10.7 P7-T6：Agent 增量评估

比较：

1. deterministic baseline；
2. production Agent evidence expansion；
3. fixed non-agent expansion policy。

指标：

- candidate recall gain；
- ranking/risk change；
- abstention change；
- additional evidence quality；
- tool calls；
- latency；
- token/cost；
- repeated-run agreement。

### 10.8 Gate P7

- Agent 不编造；
- Agent 有可测量证据策略贡献；
- deterministic baseline 不被绕过；
- manifest 可重放 kernel；
- provider 失败保持 system failure；
- 用户解释与 structured result 一致。

---

## 11. Phase 8 — Generalized Exploratory Lane

### 11.1 进入条件

strict one-step 已达到 P5 性能门；生产 MCP/Agent 不依赖 generalized 才能可用。

### 11.2 P8-T1：Relaxation policy

预注册：

- 哪些 preconditions 可放宽；
- 放宽级别；
- 禁止放宽的硬约束；
- generalization distance；
- OOD threshold；
- policy version。

### 11.3 P8-T2：Generalized hypothesis

每个候选记录：

```text
relaxed_constraints
failed_strict_conditions
generalization_distance
source transforms
validation results
```

### 11.4 P8-T3：独立 ranking/abstention

- generalized 只在自身 lane 排序；
- 不用 raw score 跨 lane 混排；
- 用户界面明确 exploratory；
- strict 无结果不自动把 generalized 伪装成 strict。

### 11.5 P8-T4：独立 benchmark

报告：

- incremental recall；
- added false candidates；
- risk–coverage；
- distance buckets；
- OOD behavior；
- generalized-only cost。

### 11.6 Gate P8

- relaxation 全部版本化；
- strict invariants 不被破坏；
- generalized 分报；
- 用户不会误解为同等证据。

---

## 12. Phase 9 — 后置研究能力

### 12.1 Research LLM-hypothesis mode

允许 LLM 提交：

```text
support_reaction_ids
transformation_family
target_site
relaxed_constraints
rationale_summary
```

必须经过 deterministic compiler/validator。

独立报告：

- new valid candidates；
- new correct candidates；
- new incorrect candidates；
- compilation rejection reasons；
- cost；
- reproducibility。

不进入 production calibrated ranking。

### 12.2 External evidence

新增前必须完成：

- source allowlist；
- licensing/provenance；
- cache；
- retrieval date/version；
- source conflict policy；
- prompt-injection isolation；
- local snapshot 与 external child run 分离；
- benchmark 中默认关闭。

### 12.3 Multi-step candidate reaction graph

不能简单递归 top-1。

实现：

```text
canonical molecule nodes
validated candidate reaction edges
per-edge evidence/ledger/lane
branch/beam search
cycle detection
depth budget
cost budget
risk budget
path deduplication
path-level uncertainty propagation
terminal/stop rules
```

每条边仍必须满足 one-step contract。

---

## 13. 测试矩阵

### 13.1 Unit tests

- schemas/invariants；
- normalization；
- mapping adapter；
- participant roles；
- lineage graph；
- ledger；
- transform canonicalization；
- site enumeration；
- generation；
- validation；
- evidence identity；
- ranking；
- abstention；
- request hashing。

### 13.2 Property/metamorphic tests

- SMILES atom-order permutation 不改变 canonical result；
- equivalent SMILES 不改变 candidate set；
- duplicate evidence 不增加 independent count；
- input order 不改变 lineage；
- frozen snapshot 重建 hash 稳定；
- frozen run 不可修改；
- strict candidate 可 replay；
- generalized relaxation 不污染 strict。

### 13.3 Regression tests

至少：

- proline/2-oxoglutarate lineage；
- 1-octanol → octanal 8-carbon；
- test leakage；
- split denominator；
- multiple Y for same X；
- tuple tie ambiguity；
- unknown atom source；
- infrastructure failure vs abstention；
- MCP field naming；
- PredictionResult invariants。

### 13.4 Integration tests

- source → snapshot；
- snapshot → fold view；
- X → strict candidates；
- X → typed abstention；
- predictor → immutable run；
- MCP → resource reads；
- Agent → grounded report。

### 13.5 Evaluation tests

- multi-answer matching；
- CI computation；
- risk–coverage；
- strict/generalized separation；
- all-X denominator；
- baseline fairness；
- test labels inaccessible；
- time/source split capability gates。

---

## 14. 必须生成的报告

### 14.1 数据报告

```text
legacy_lineage_audit.md/json
snapshot_build_report.md/json
quarantine_report.md/json
manual_audit_report.md/json
mapping_quality_report.md/json
ledger_quality_report.md/json
```

### 14.2 Pilot 报告

```text
mini_snapshot_manifest.json
pilot_preregistration.md
pilot_funnel.json
pilot_results.md
pilot_go_no_go.md
```

### 14.3 Benchmark 报告

```text
benchmark_manifest.json
split_report.md/json
leakage_audit.md/json
baseline_comparison.md/json
strict_metrics.md/json
selective_metrics.md/json
error_taxonomy.md/json
```

### 14.4 MCP/Agent 报告

```text
mcp_contract_report.md
idempotency_report.md
chaos_test_report.md
agent_grounding_report.md
agent_incremental_value.md
cost_latency_report.md
```

---

## 15. Stop Conditions

出现以下情况必须停止进入下一阶段：

### 15.1 数据阻断

- catastrophic lineage mismatch 仍进入生产 index；
- mapping/lineage 无法重放；
- `COFACTORS` 仍造成完整 participants 丢失；
- quarantine 被静默从报告中删除；
- ledger 把不完整来源伪装成完整守恒。

### 15.2 Benchmark 阻断

- test evidence 可被 retrieval/scorer 访问；
- 部分 X 在 split 前无声丢失；
- 单标签把已知多答案记错；
- 指标没有 N；
- oracle donor 混入主结果；
- 旧 provisional 数字继续被当 KPI。

### 15.3 Kernel 阻断

- LLM 或 reporter 能创建 candidate structure；
- strict candidate 不能重放；
- 新增重原子无来源且未标 unknown；
- atom-order 改变导致 candidate set 漂移；
- system failure 被返回为 scientific abstention。

### 15.4 MCP/Agent 阻断

- unknown ID 能通过 grounding；
- predict 重试创建多个不一致 run；
- frozen run 可被修改；
- Agent 能改 rank/lane/ledger；
- prompt injection 可越过 snapshot/fold 权限；
- Agent invented candidate/evidence 不为零。

---

## 16. 推荐执行批次

### Batch A：第一周重点——证明地基问题并建立 schemas

顺序：

1. P0 契约冻结；
2. P1-T1 schemas；
3. P1-T2 legacy audit；
4. P1-T3 mapping adapter；
5. P1-T4 roles；
6. P1-T5 lineage regression。

首个可见交付不是 Agent demo，而是：

```text
legacy lineage audit
+ proline regression
+ typed lineage graph
+明确 quarantine
```

### Batch B：完整证据

1. Ledger；
2. snapshot；
3. manual audit；
4. fold views；
5. mini snapshot。

### Batch C：Strict vertical slice

1. normalize；
2. donor retrieval；
3. complete reaction loader；
4. transform；
5. sites；
6. generate；
7. validate；
8. candidate store。

### Batch D：可靠决策

1. support identity；
2. counterevidence；
3. ranking；
4. applicability；
5. abstention；
6. manifest/replay。

### Batch E：正式 benchmark

1. full snapshot；
2. rebuilt labels；
3. splits；
4. baselines；
5. six-layer/selective reports；
6. KPI freeze。

### Batch F：MCP 和 Agent

1. tool contracts；
2. idempotency/resources；
3. chaos tests；
4. provider adapter；
5. agent policy；
6. grounding/reporting；
7. Agent incremental evaluation。

---

## 17. 可安全并行的工作

在不跨 Gate 的前提下可以并行：

| 主线 | 可并行工作 |
|---|---|
| Mapping/lineage | schemas、审计协议、fixture 建设 |
| Ledger | snapshot manifest 设计、quarantine schema |
| Mini snapshot | evaluation metric 单元测试、baseline characterization |
| Strict kernel | manifest/run-store 原型、MCP schema 草案 |
| Benchmark | Agent provider adapter 接口测试，但不接生产科学结果 |
| MCP | no-invention prompt cases、resource URI contract tests |

不能并行跳过：

- 用未通过 lineage 的数据训练/调 ranking；
- 在 benchmark 未隔离前报告性能；
- 在 kernel 未过门前把 LLM 输出当正式候选；
- 在 strict 未过门前开发 generalized/multi-step 作为主线。

---

## 18. Definition of Done

### 18.1 Strict scientific kernel 完成

- 只输入 X；
- donor 自动检索；
- 完整 reaction 无损加载；
- A→B 沿 lineage 解析；
- transform/site 可审计；
- Y 确定性生成；
- candidate ledger 完整表达已知和 unknown；
- top-K 或 typed abstain；
- 可重放。

### 18.2 Benchmark 完成

- multi-answer truth；
- train-only evidence；
- all-X denominator；
- exact-X/scaffold/transform/source/time 能力化 split；
- 六层指标；
- selective/risk–coverage；
- N/CI；
- legacy baseline 同数据对拍。

### 18.3 MCP 完成

- 高层工具 contracts 稳定；
- side effects 正确；
- idempotency；
- immutable runs；
- resource URIs；
- typed errors；
- chaos tests。

### 18.4 Production Agent 完成

- baseline 强制运行；
- 证据策略受约束；
- invented IDs 为零；
- 结构和分数不被改写；
- prompt injection 被限制；
- model/tool/prompt 记录完整；
- Agent 增量价值有量化对照。

---

## 19. 第一轮实现的具体起点

在 v2 文档批准后，第一轮不要从 MCP server 或 prompt 开始。按以下五步执行：

1. 创建 `demov2` 隔离包与 strict schemas；
2. 写 legacy lineage audit；
3. 固化 proline/2-oxoglutarate 回归 fixture；
4. 实现 mapping adapter 和 fragment-lineage graph；
5. 输出第一份数据审计报告，决定全量 snapshot 的质量门。

第一轮的验收问题只有三个：

```text
1. 我们能否可靠识别完整反应中的真实 transformed lineage？
2. 我们能否在不删除 cofactor/小分子的情况下建立可解释 ledger？
3. 我们能否构建可重放、可隔离、不会泄漏的 evidence snapshot？
```

只有三个答案都为“是”，才继续做 `X→A→B→Y` 的 strict vertical slice。

---

## 20. 最终执行结论

实施优先级不是“先做一个看起来像 Agent 的 demo”，而是：

> **先修正反应事实和评估尺子，再证明严格单步结构类比内核，随后把它封装成可审计 MCP，最后让 LLM 在受约束的证据策略空间中发挥作用。**

这样可以同时避免两种失败：

- 做出一个会说化学语言、却依赖错误 A/B 标签和幻觉结构的 LLM demo；
- 做出一个完全固定、没有 Agent 推理和证据探索能力的传统检索脚本。

本计划完成后的第一版产品，应当能够诚实地回答：

```text
“根据这些明确的 donor 完整反应和可回放结构变化，
X 有这些 strict structural analogy 候选；
这是它们的证据、账本和适用边界。
如果证据不够，系统明确拒答。”
```

