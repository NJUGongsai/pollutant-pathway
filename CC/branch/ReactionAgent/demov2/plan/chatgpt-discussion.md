> **HISTORICAL / NON-AUTHORITATIVE**
> This document is retained for decision history only.
> Current implementation authority: `plan/final_design.md`, `plan/final_plan.md`, `plan/final_discussion.md`.

# ChatGPT Discussion — demov2 三模型 Design/Plan 联合评审

> 日期：2026-07-29  
> 评审对象：Claude、Qwen、ChatGPT 三套 design/plan  
> 评审方式：主审逐份通读 + 化学/数据审阅 Agent + MCP/Agent 架构审阅 Agent + 工程实施审阅 Agent  
> 结论状态：形成推荐融合路线；现有三套计划均不建议原样开工  

---

## 1. 本次阅读范围

完整阅读了以下六个文件：

1. `CLAUDE_DESIGN_LLM_LATENT_STAGE_REASONING_2026-07-29.md`
2. `CLAUDE_PLAN_LLM_LATENT_STAGE_REASONING_2026-07-29.md`
3. `qwen_design.md`
4. `qwen_plan.md`
5. `chatgpt-reaction-analogy-agent-design.md`
6. `chatgpt-reaction-analogy-agent-plan.md`

本次讨论基于用户已经确认的产品边界：

- 用户运行时只输入 X；
- A→B 由系统自适应检索 donor 得到；
- 输出是结构类比候选，不声称真实酶活性或环境发生概率；
- donor 使用自适应集合；
- 输出 ranked top-K；
- 每个候选同时提供主产物 Y 和完整反应账本；
- LLM 是受约束混合 Agent；
- strict/generalized 双通道；
- 版本化本地证据快照为主，外部证据可选增强；
- 首个可靠版本只做单步。

## 2. 结论先行

### 2.1 推荐决策

最终系统应：

1. **以修订后的 ChatGPT 方案作为生产主架构；**
2. **吸收 Claude 的 `T→S→Δ→Y` 分阶段漏斗、donor 多样性和 selective evaluation；**
3. **吸收 Qwen 的 `analyze_structure`、`analyze_diff`、`get_reaction_details` 等只读工具，以及低成本 pilot 思想；**
4. **保留一个隔离的 LLM hypothesis research mode，但不得让它直接进入生产候选或排名；**
5. **在修复 ChatGPT plan 自身的 lineage、ledger、counterevidence、多答案 benchmark、MCP 合同和测试错误之前，不按当前 plan 直接开工。**

### 2.2 为什么不是简单三选一

- Claude 最忠实于“LLM 自己推理”，但生产可靠性和可复现性不足。
- Qwen 在 LLM 与 RDKit 之间取得了中间平衡，工具设计直观，但继承了旧数据地基错误并过早做多步。
- ChatGPT 的数据、化学和 MCP 治理最完整，但计划偏重、缺少快速垂直验证，而且部分伪代码和 schema 仍有严重缺陷。

因此正确策略不是平均折中，而是分层组合：

```text
ChatGPT：数据地基 + 科学内核 + 生产治理
Claude：阶段化潜变量与漏斗
Qwen：只读分析工具 + 快速、非 oracle pilot
```

## 3. 总体评分

评分采用 1–5 分，评价的是“能否作为当前已确认产品的实施地基”，不是语言模型能力高低。

| 维度 | Claude | Qwen | ChatGPT |
|---|---:|---:|---:|
| 与当前产品边界一致 | 2 | 3 | 5 |
| 反应化学严谨性 | 1 | 2 | 4 |
| A/B 角色与原子谱系 | 1 | 1 | 4 |
| 完整反应/辅因子账本 | 1 | 2 | 4 |
| donor 检索设计 | 3 | 3 | 4 |
| LLM 防幻觉边界 | 1 | 3 | 5 |
| MCP 合同完整性 | 2 | 3 | 4 |
| benchmark 与防泄漏 | 2 | 2 | 4 |
| 可复现性与审计 | 1 | 2 | 5 |
| 快速 MVP 能力 | 5 | 4 | 2 |
| 实施计划完整度 | 2 | 3 | 4 |
| 适合作生产主线 | 否 | 否 | 是，但必须修订 |

## 4. Claude 方案评审

### 4.1 值得保留的部分

#### A. 潜变量分阶段表达清楚

Claude 将过程拆为：

```text
X → T → S → Δ → Y → E → confidence
```

这非常适合转化为：

- 状态机阶段；
- typed stage output；
- 失败 reason code；
- benchmark 漏斗；
- per-stage error attribution。

最终应保留这条链，但 T、S、Δ、Y 必须来自确定性工具或独立评估模型，而不是 LLM 自由文本。

#### B. donor 多样化检索思想正确

Claude 提出的：

- 高全局结构相似；
- 高局部位点相似；
- 远程同类转化；
- MMR/多样性采样；

可以吸收进 adaptive donor retrieval。

#### C. selective evaluation 值得保留

Claude 强调：

- 所有测试 X 进入分母；
- top-K 端到端；
- selective accuracy；
- abstention rate；
- risk/coverage 曲线。

这些指标应保留。

#### D. 单步优先

Claude 没有在 M0 直接默认多步，这比 Qwen 更稳妥。

### 4.2 必须否决的部分

#### A. LLM 直接写结构编辑和产物 SMILES

Claude Design §2、§3.2 和 Plan M0 明确要求 LLM 自己写 Y。

RDKit 能 parse/sanitize 一个 SMILES，只能证明它是一个可构造的分子图，不能证明：

- 它来自 donor A→B 的可迁移编辑；
- 原子来源正确；
- 反应方向正确；
- 共底物/辅因子支持变化；
- 元素、电荷、氢/电子账本合理；
- 立体和芳香性变化正确。

“LLM 猜 Y → RDKit 合法性检查 → 不合法就重写”会把化学错误变成形式合法的化学错误。

#### B. LLM 自报“校准置信度”

Claude 让 LLM 综合证据给 confidence。语言模型自报分数不是统计校准。

在独立 calibration fold、Brier/ECE 和 risk–coverage 验证前，只能输出：

```text
ranking_score
support_tier
applicability
```

#### C. 无条件 `check_reaction_center(X)`

反应位点不是 X 的固有唯一属性。它至少应条件化为：

```text
p(S | X, Δ, donor environment, reaction type)
```

`reaction_center_from_chenyu` 还可能依赖已知完整反应或真值，在 test X 上使用会造成泄漏。

#### D. 冻结旧 benchmark/core

Claude 继续冻结：

- `canonical_identity.transformed_pair()`；
- `splits.py`；
- scorer；
- `honest_eval`；

但这些部位已经发现 A/B 错配、split 前过滤、scorer reference 非 train-only、多答案缺失等问题，不能冻结。

#### E. 把 DRFP max 当酶学可行性

DRFP 邻近度最多是反应典型性或弱排序特征，不能证明某酶接受 X，更不应进入本版本的结构类比“概率”。

### 4.3 对 Claude 方案的最终处置

保留：

- `T/S/Δ/Y` 阶段漏斗；
- 多 donor、多样性；
- typed stage failures；
- selective/risk–coverage；
- 单步优先。

否决：

- LLM 写/修复 Y；
- LLM 自报 confidence；
- 无条件 site；
- 冻结旧标签与 benchmark；
- 把 DRFP 解释为酶学概率；
- 将 reasoning chain 当成科学证据。

## 5. Qwen 方案评审

### 5.1 值得保留的部分

#### A. LLM 不直接生成 SMILES

Qwen 让 `apply_transformation` 负责产物生成，安全边界明显优于 Claude。

#### B. 工具接口直观

Qwen 的以下工具很适合作为内部调试或只读 evidence 工具：

```text
analyze_structure
analyze_diff
get_reaction_details
search_enzymes
```

其中 `get_reaction_details` 强调 full reaction、cofactor、center、EC/UniProt，是值得吸收的设计。

#### C. 结构化工具返回

工具返回 dict 而非自然语言，有利于 schema 化和测试。

#### D. 快速 pilot 思想有价值

先做小规模 Go/No-Go 可以减少无效工程投入，但当前 pilot 必须改成自动检索、预注册和无 oracle 的版本。

#### E. 成本/延迟可观测性

Qwen 在 state 中保留 token、tool call 和延迟统计，这应并入最终 manifest/trace。

### 5.2 必须否决的部分

#### A. 原样复用 `transformed_pair/main_substrate/main_product`

Qwen Plan Phase 1.1 明确“保持原样”移植旧 `canonical_identity`。这会继承已确认的 A/B 独立挑片段错误。

若 substrate/product 错了，后续：

- edit；
- reaction type；
- function group in/out；
- site；
- candidate；
- benchmark；

都会被污染。

#### B. 用 substrate/product 两分子做反应守恒

Qwen 的 `validate_chemistry(substrate, product)` 不能正确处理：

- O₂/H₂O 引入氧；
- NAD(P)/FAD 氧化还原；
- CO₂ 羧化/脱羧；
- 氨基、酰基、糖基、磷酸基转移；
- 裂解多产物。

必须验证完整反应账本，而不是只比较 X/Y 分子式差。

#### C. Phase 0.5 手工挑 support 是 oracle

Qwen 的 pilot 人工给每个测试 X 挑 3–5 条相关 A→B，并人工写差异。这只能测“给定正确证据后的上界”，不能测：

- 自动 donor retrieval；
- 错误证据鲁棒性；
- 冲突证据；
- end-to-end top-K；
- abstention。

可保留 oracle upper-bound，但必须另做 blind、自动检索 pilot，且不能把 oracle pilot 作为生产路线验收。

#### D. “4541 条全部入库”不是质量目标

错误或歧义记录必须 quarantine。生产索引需要：

- mapping confidence；
- lineage ambiguity；
- source version；
- duplicate identity；
- balance status；
- role uncertainty；
- snapshot hash。

#### E. “两条支持 = 高置信”不成立

两条记录可能是同一个反应的不同字符串、同一论文重复、同一 donor 的重复注释。必须定义 independent evidence unit，而且多条 support 也只能增加结构类比支持，不能转成生物概率。

#### F. 过早默认多步

Qwen 从第一版就递归到 5 步，且是单线继续。第一步错误会成为下一步确定输入，误差快速放大。

多步应后置并使用候选图、canonical node 去重、cycle detection、branch/depth/cost budget 和逐边 provenance。

#### G. 直接沿用旧 benchmark 数字

41.5%、23.5%、60%、35% 等目标在修复 A/B、泄漏和多答案前只能视为 provisional。

### 5.3 对 Qwen 方案的最终处置

保留：

- LLM 不写结构；
- 结构化只读化学工具；
- full reaction details；
- 工具组合测试；
- 成本、token、延迟统计；
- 快速 pilot 思想。

否决：

- 旧 canonical identity 原样复用；
- X/Y 两分子守恒；
- 手选 evidence 作为端到端验证；
- 两条 evidence 自动高置信；
- 无 quarantine 全量入库；
- 首版多步；
- 旧 benchmark 数字作为承诺。

## 6. ChatGPT 方案评审

### 6.1 适合作为主骨架的原因

#### A. 任务被定义为完整反应证据迁移

ChatGPT 方案要求：

- 完整 reaction record；
- participant roles；
- atom mapping；
- fragment lineage；
- donor A 沿原子谱系找到 B；
- 共底物、辅因子、副产物不删除；
- ambiguity/quarantine。

这是三套方案中最重要的正确地基。

#### B. 正确识别旧 benchmark 的阻断项

包括：

- 2-氧戊二酸 → 羟脯氨酸的错误配对；
- scorer 非 train-only；
- split 前样本丢失；
- 一个 X 对应多个 Y；
- 粗 `edit_key` 不是 canonical transformation；
- 旧 generation/ranking 数字不能冻结。

#### C. donor 单位正确

先选 distinct donor molecules A，再加载每个 A 的全部合格完整反应，而不是让重复 reaction rows 占满 top-K。

#### D. site 条件化正确

采用：

```text
p(S | X, Δ, donor environments, reaction type)
```

而不是先无条件猜 X 的“反应热点”。

#### E. strict/generalized 双 lane 合理

- strict：完整 precondition、确定性回放；
- generalized：显式记录放宽项，独立标记 exploratory；
- 不跨 lane 比较 raw score。

#### F. LLM 权限最安全

LLM 不生成结构、不做 mapping、不判断守恒、不改写排名和 abstention。Host 从 candidate/evidence IDs 渲染科学结果，并拒绝未知 ID。

#### G. benchmark 最完整

包含 data、retrieval、transform/site、generation、ranking/abstention、Agent/MCP 六层，以及 exact-X、scaffold、transform-family、source、time 等拆分。

### 6.2 ChatGPT 方案自身必须修正的问题

#### A. 辛醇→辛醛测试少了一个碳

Plan Task 7 和 schema 示例把：

```text
CCCCCCCCO
```

的产物写成：

```text
CCCCCCC=O
```

正确应是：

```text
CCCCCCCC=O
```

若不修，TDD 会把碳损失错误固化成预期行为。

必须增加：

- 分子式检查；
- heavy-atom lineage；
- carbon count regression；
- donor/input/output atom-map regression。

#### B. `resolve_primary_lineage()` 伪代码仍会静默误选

Plan Task 3 使用：

```python
max(pairs)
```

按 mapped overlap 和 heavy atom 数选单一 pair。问题是：

- tie 会被 tuple 后续字段静默打破；
- 最大 overlap 不等于 target substrate；
- 一个反应可同时转化多个 participant；
- co-substrate/cofactor 也可能有更大 overlap；
- 计划声称 ambiguity 会报错，但伪代码没有实现。

应改成完整 bipartite fragment-lineage graph：

```text
reactant participant
→ product participant(s)
→ mapped overlap fraction
→ changed mapped atoms
→ role hypotheses
→ ambiguity set
```

同一完整反应可以贡献多个可类比 transformed participant lineage，不强制只有一个全局 primary A。

#### C. ReactionLedger schema 太弱

当前 schema 缺少：

- participant ID、role 和 stoichiometry；
- atom-map coverage；
- atom transfer source/destination；
- explicit/implicit H policy；
- proton/electron bookkeeping；
- isotope；
- per-participant formal charge；
- reaction direction；
- mapping confidence；
- spectator policy；
- donor ledger 与 adapted X→Y ledger 的对应关系。

建议拆为：

```text
ReactionParticipantLedger
AtomTransferLedger
ElementBalance
ChargeBalance
HydrogenElectronPolicy
Stoichiometry
MappingCoverage
SourceBalanceStatus
AdaptationSubstitutionMap
```

账本状态至少分：

```text
fully_balanced_explicit_reaction
heavy_atom_balanced_with_implicit_H_e_policy
partial_or_unbalanced_source
```

#### D. counterevidence 只存在于设计，计划没有完整任务

需要单独增加：

- support 聚合索引；
- independent evidence identity；
- counterevidence 的允许定义；
- 数据库未收录不得当 negative；
- source/annotation bias；
- counterevidence retrieval tests。

#### E. 多答案真值未落到 plan

需要定义：

- X 对应的允许 Y 集合；
- context/酶/方向是否拆分；
- tautomer、盐、中性形式等价；
- stereo-sensitive/agnostic 两套指标；
- multi-product target set；
- incomplete annotation 下 precision 的解释边界。

#### F. mapping adapter 没有实化

必须定义：

- mapper 和版本；
- 原始 map 与标准化 map；
- symmetric/resonance/tautomer ambiguity；
- 多 mapper disagreement；
- mapping confidence；
- quarantine 门；
- transform identity 如何对称性不变。

#### G. retrieval 固定权重只能是 baseline

`0.45/0.20/...` 权重需要：

- 显式标记为 baseline；
- 版本化；
- 只用 train/validation 调整；
- 对比 Morgan-only、无 local、无 MMR 等消融。

#### H. MCP 字段命名漂移

Design/Plan 中存在：

- `run_manifest_uri` vs `manifest_uri`；
- `reaction_ledger` vs `ledger`。

实施前必须统一。

#### I. MCP 副作用与幂等声明不准确

`predict` 会冻结并保存 run；`expand_external_evidence` 会进行外部 I/O 并记录时间，不能笼统声明所有工具严格 read-only/idempotent。

需要：

- `idempotency_key/client_request_id`；
- request hash → run 复用；
- 明确 corpus-read-only、run-log-writing、external-I/O；
- 正确 tool annotations。

#### J. PredictionResult 缺跨字段 invariant

必须保证：

```text
predicted → candidates 非空
abstained → candidates 为空且 reason_code 非空
partial → 只有 generalized 或依赖部分失败
status 与 decision.kind 一致
```

#### K. 计划太重，缺快速非 oracle 垂直切片

ChatGPT 计划 14 个任务、外部证据和完整 manifest 较重。应吸收 Qwen pilot 思想，但改成：

- 预注册测试集；
- 自动 train-only donor retrieval；
- 禁止人工按真值挑 support；
- 同时报 retrieval/transform/site/generation miss；
- 只验证 strict one-step；
- generalized、外部证据和 LLM Agent 后置。

#### L. 人工审计质量门未量化

至少应规定：

- 分层抽样；
- 样本量；
- 审计者与一致性；
- catastrophic mismatch 和一般 uncertainty 的门槛；
- multi-reactant/product、redox、transferase、cleavage、MCS fallback 分层。

## 7. 三套方案的融合架构

### 7.1 生产主线

```text
X
→ normalize
→ adaptive donor molecule retrieval
→ load complete A→B reactions
→ participant roles + mapped fragment-lineage graph
→ build strict transformation hypotheses
→ transformation-conditioned site enumeration
→ deterministic graph-edit generation
→ molecule validation + complete reaction ledger
→ support/counterevidence aggregation
→ tiered ranking + applicability + typed abstention
→ immutable run
→ MCP structured result
→ LLM grounded explanation
```

### 7.2 把 Claude 的潜变量变成结构化 trace

保存：

```text
Donor
T: transformation
S: query site
Δ: atom-mapped edit
Y: generated product
L: reaction ledger
R: rank/applicability
A: abstention decision
```

每个阶段必须有：

- typed input/output；
- failure code；
- component version；
- input/output hash；
- stage metric。

不要求暴露完整 chain-of-thought。对用户展示 evidence card 和阶段事实。

### 7.3 吸收 Qwen 的只读工具

内部/调试工具：

```text
chem.analyze_structure_v1
reaction.analyze_diff_v1
reaction.get_details_v1
evidence.search_structured_v1
enzyme.get_provenance_v1
```

限制：

- `analyze_diff` 必须基于 mapped lineage；
- 自然语言搜索先编译成 structured query；
- benchmark 主检索不得依赖不可复现的自然语言 query；
- `search_enzymes` 只作为 provenance；
- production LLM 不直接调用底层 `apply_transform`。

### 7.4 两种 Agent 模式

#### Production grounded mode

- 候选只由 deterministic kernel 生成；
- LLM 只能请求预测、查看证据、请求外部增强和解释；
- Host 从工具结果渲染结构与分数；
- 适合正式用户和 benchmark。

#### Research LLM-hypothesis mode

- LLM 可以提交 typed hypothesis：

```text
support_reaction_ids
transformation_type
target_site
relaxed_constraints
rationale_summary
```

- hypothesis 必须进入同一 deterministic compiler/validator；
- 未通过验证不得获得 candidate_id；
- 结果单独标记、单独 benchmark；
- 不进入 production calibrated ranking；
- LLM 仍不得直接写最终 Y。

这样既保留“LLM 是否能像化学家提出假设”的研究价值，也不牺牲生产可靠性。

## 8. MCP 合并意见

### 8.1 面向生产 LLM 的高层工具

建议保留：

```text
reaction.predict_analogical_products_v1
reaction.get_run_v1
reaction.get_candidate_evidence_v1
reaction.expand_external_evidence_v1
```

但外部增强可移出 MVP。

### 8.2 必须统一的字段

统一采用：

```text
manifest_uri
reaction_ledger
```

不要在 design/plan 中并存别名。

### 8.3 跨字段 invariant

```text
status=completed + decision=predicted + candidates≥1
status=abstained + decision=abstained + candidates=0 + reason_code
status=partial + decision=partial + 明确 partial_reason
status=failed + dependency/protocol error，不冒充 abstention
```

### 8.4 幂等与副作用

`predict` 输入增加：

```text
client_request_id
idempotency_key
snapshot_id
```

服务端使用：

```text
canonical request hash + snapshot/version
→ existing run or create exactly one run
```

真实标注：

- evidence corpus：read-only；
- run store：append/write；
- external evidence：open-world network I/O；
- resource read：read-only。

### 8.5 运行清单补充

manifest 还应记录：

- Agent prompt hash；
- model/provider/revision；
- temperature/seed；
- tool schema versions；
- tool response hashes；
- cache policy；
- per-run tool/time/token budget；
- trace/correlation ID；
- redaction policy。

## 9. 不可协商的否决项

以下主张不得进入最终生产设计：

1. LLM 直接生成或修复产物 SMILES。
2. LLM 自己生成 confidence 或 biological probability。
3. “RDKit 能解析/RunReactants 能生成”即反应正确。
4. 只比较 substrate/product 质量与元素差作为完整反应守恒。
5. 原样使用旧 `main_substrate/main_product/transformed_pair`。
6. 把 `reaction_center_from_chenyu(X)` 当无条件 site predictor。
7. 把 DRFP max 当酶可行概率。
8. “两条类似记录”自动等于高置信。
9. 人工挑正确 evidence 后声称验证了端到端能力。
10. 4541 条记录无 quarantine 全部进入生产索引。
11. 修复 A/B、泄漏、多答案前引用旧 benchmark 数字作为承诺。
12. 首版默认递归 3–5 步线性路径。
13. 数据库没有 evidence 就表述为“无反应”。
14. 把 strict structural analogy 表述为环境发生概率或酶活性。
15. 多 LLM 投票代替独立工具、模型或实验验证。

## 10. 修订后的实施顺序

### Phase 0：立即修订文档与冻结旧承诺

交付：

- 统一产品术语为 `strict structural analogy` / `generalized structural analogy`；
- 旧 P0、A1/A2、79.5% 标记 provisional；
- 修正 octanol/octanal 示例；
- 统一 MCP schema 字段；
- 把 external evidence 和多步移出 MVP。

验收：

- design/plan 无已知内部矛盾；
- 不再引用未经修复 benchmark 数字作为目标。

### Phase 1：数据审计与反应表示

交付：

- participant schema；
- atom-mapping adapter 与版本；
- fragment-lineage graph；
- role hypotheses；
- ambiguity/quarantine；
- stratified manual audit protocol；
- versioned snapshot。

必须覆盖：

- multi-reactant；
- multi-product；
- redox cofactor；
- transferase；
- cleavage；
- unmapped/MCS fallback；
- 已知 2-氧戊二酸/羟脯氨酸错误案例。

验收重点：

- catastrophic A/B mismatch 不进入生产索引；
- unresolved lineage 有明确 quarantine reason；
- atom mapping 与 snapshot 可重放。

### Phase 2：先重建 benchmark 地基

交付：

- multi-answer/equivalence truth policy；
- fold-specific evidence store；
- train-only retrieval/ranking references；
- exact-X/scaffold/transform-family/source/time split；
- data/retrieval/generation/ranking 分层指标；
- legacy baselines 重跑。

验收重点：

- test evidence leakage 为零；
- split 前过滤数量明确进入报告；
- strict/generalized 分开报告；
- 每个指标带 N 和置信区间。

### Phase 3：非 oracle strict one-step vertical slice

交付：

```text
X
→ automatic adaptive donor retrieval
→ complete A→B records
→ strict transform
→ conditioned sites
→ deterministic products
→ molecule + reaction ledger
→ ranked top-K or typed abstention
```

pilot 要求：

- 测试集预注册；
- donor 自动从 train-only snapshot 检索；
- 禁止按真值人工挑 support；
- 记录 retrieval/lineage/transform/site/generation/validation miss；
- 包含 invalid、ambiguous 和 OOD 案例。

验收重点：

- 等价 SMILES 输入不改变 canonical candidate set；
- 每个 candidate 有 donor/transform/site/ledger/evidence；
- 所有新增 heavy atom 有来源或明确 unknown；
- infrastructure failure 不转成 abstention。

### Phase 4：support、counterevidence、ranking 与 abstention

交付：

- independent support identity；
- counterevidence policy/index；
- baseline feature weights；
- ablations；
- applicability gates；
- risk–coverage；
- typed abstention。

注意：

- 数据库缺失不是 negative；
- fixed weights 是 baseline，不是最优或概率；
- strict 只表示结构类比严格，不表示生物真实。

### Phase 5：generalized exploratory lane

交付：

- 明确可放宽约束列表；
- generalization distance；
- generalized-only ranking；
- 与 strict 完全分报；
- out-of-domain gate。

### Phase 6：高层 MCP

交付：

- 四个生产工具；
- strict JSON schema；
- stable IDs/resource URIs；
- idempotency；
- typed errors；
- resource access control；
- trace/run manifest；
- contract/chaos tests。

### Phase 7：受约束 LLM Agent

交付：

- grounded reporting；
- unknown candidate/evidence ID rejection；
- prompt-injection tests；
- token/tool/time budgets；
- no-invention benchmark；
- 可选 research LLM-hypothesis mode。

### Phase 8：单步达标后另行设计多步

多步不是线性递归。未来应采用：

- canonical molecule node；
- candidate reaction edge；
- branch/beam；
- cycle detection；
- depth/cost/risk budget；
- per-edge provenance；
- 路径级不确定性传播。

## 11. 第一阶段真正的成功标准

现阶段不应先承诺某个 top-1 百分比。应先证明地基可信：

- 已知错误 A/B 案例全部修复或 quarantine；
- catastrophic lineage mismatch 不进入生产索引；
- fold 内 test evidence leakage 为零；
- strict candidate 全部来自可回放 transform；
- input atom order 不改变 canonical result；
- 每个新增 heavy atom 有来源；
- reaction ledger 状态语义明确；
- Agent invented candidate/evidence 数为 0；
- infrastructure failure 不冒充 abstention；
- strict/generalized 分报；
- 所有指标带样本量和置信区间。

完成这些之后，再根据新 benchmark 设置 top-K、coverage 和 risk 目标。

## 12. 立即需要修订 ChatGPT Design/Plan 的清单

在实施前至少完成：

1. 把辛醇→辛醛的 `CCCCCCC=O` 修为 `CCCCCCCC=O`。
2. 把单一 `resolve_primary_lineage()` 改为 fragment-lineage graph。
3. 实现 tie/ambiguity，不允许 tuple `max()` 静默选。
4. 扩展 ReactionLedger。
5. 明确 implicit H/proton/electron policy。
6. 新增 mapping adapter/quality task。
7. 新增 data audit protocol/quality gate。
8. 新增 multi-answer/equivalence benchmark task。
9. 新增 support/counterevidence task。
10. 将固定 retrieval/ranking 权重标为 baseline。
11. 统一 `manifest_uri` 和 `reaction_ledger`。
12. 增加 PredictionResult 跨字段 invariant。
13. 修正 MCP read-only/idempotent annotations。
14. 增加 idempotency key 和 request hash run reuse。
15. 将 external evidence 后移。
16. 将 generalized lane 放在 strict vertical slice 和 benchmark 之后。
17. 增加非 oracle 预注册 pilot。
18. 增加 prompt/model/tool response hash、预算和日志脱敏策略。

## 13. 最终推荐架构图

```text
Versioned reaction evidence snapshot
  │
  ├─ complete participants / roles / atom maps
  ├─ fragment-lineage graph
  ├─ quality / ambiguity / quarantine
  └─ fold-specific train-only views
  │
  ▼
Adaptive donor-molecule retrieval
  │
  ▼
Complete A→B support records
  │
  ▼
Typed transformation hypotheses (T, Δ)
  │
  ▼
Transformation-conditioned query sites (S)
  │
  ▼
Deterministic graph-edit candidates (Y)
  │
  ▼
Molecule validation + reaction ledger
  │
  ▼
Support / counterevidence / applicability
  │
  ├─ strict structural analogy
  └─ generalized structural analogy
  │
  ▼
Tiered ranking / typed abstention
  │
  ▼
Immutable run + evidence resources
  │
  ▼
High-level MCP tools
  │
  ▼
Grounded LLM explanation
```

## 14. 最终讨论结论

### 14.1 对三套方案的正式意见

- **Claude：**不作为生产主线；保留阶段漏斗、donor 多样性和 selective evaluation。
- **Qwen：**不作为生产主线；保留结构化只读工具、full reaction details、成本观测和快速 pilot。
- **ChatGPT：**作为主骨架，但必须完成第 12 节修订后才进入实施。

### 14.2 推荐形成的新文档

不要继续让三套 design/plan 并行演化。讨论确认后应生成一套权威文件：

```text
chatgpt-reaction-analogy-agent-design-v2.md
chatgpt-reaction-analogy-agent-plan-v2.md
```

v2 应：

- 合并本讨论中批准的 Claude/Qwen 优点；
- 修正 ChatGPT v1 的全部阻断项；
- 把 Phase 0–3 写成可立即执行的 MVP 计划；
- 把 generalized、external evidence、LLM research mode 和多步明确后置；
- 成为后续 implementation 的唯一权威 spec/plan。

### 14.3 一句话结论

> 选择“完整反应数据地基 + 确定性结构类比内核 + 高层 MCP + 受约束 LLM”作为主线；吸收 Claude 的阶段漏斗、Qwen 的工具化与快速 pilot，但不允许 LLM 直接创造化学结构或置信度，也不允许在修复 A/B 谱系和 benchmark 前继续沿用旧数字开工。

