# ChatGPT → Qwen：Reaction Analogy Agent P1 Data Foundation 完整执行提示词

> **执行模型：** Qwen  
> **最终审核：** ChatGPT  
> **项目目录：** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`  
> **阶段：** P1 — Data Foundation  
> **前置状态：** P0 已由 ChatGPT 第四轮审核正式接受，P1 已授权  
> **禁止越界：** 不得进入 P2，不得实现或宣称 candidate performance，不得把 P1 当作最终 X→Y 预测系统  
> **工作方式：** 最小实现、测试先行、真实数据优先、缺证据即 fail-closed、阶段 Gate 后再推进

---

## 0. 任务目标

本轮不是做一个看起来能够生成产物的 demo，也不是继续在旧的：

```text
主底物 A
→ 主产物 B
```

单对投影上打补丁。

P1 的唯一目标是建立可信、可重放、可审计的数据地基：

```text
完整来源反应
→ normalization
→ formal atom mapping
→ participant role hypotheses
→ bipartite fragment-lineage graph
→ resolved transformed lineages
→ SourceReactionLedger
→ eligibility / diagnostic / quarantine
→ immutable evidence snapshot
→ manual audit
```

最终必须能回答：

1. donor `A` 来自哪条完整反应；
2. 反应中所有 reactants/products 是什么；
3. 哪些 participant 只是 role prior，哪些真正发生了结构变化；
4. `A→B` 是否由同一条 mapped fragment-lineage 支持；
5. 是否发生 split、merge、atom transfer 或关键 ambiguity；
6. formal mapping 的质量和局限是什么；
7. donor reaction 是否允许进入 strict production index；
8. 哪些记录进入 quarantine，为什么；
9. snapshot 是否能够确定性重建；
10. 所有过滤前后数量是否有机器可读 reason。

P1 不负责：

- 给用户未知分子 X 检索 donor；
- 把 A→B transformation 应用到 X；
- 生成 Y；
- 排序 candidate；
- MCP tools；
- LLM hypothesis orchestration；
- benchmark candidate top-K performance；
- enzyme activity probability；
- environmental occurrence；
- kinetics、yield；
- multi-step pathway。

这些属于后续阶段。P1 未通过前，不得提前实现来“展示进展”。

---

## 1. 权威文件与优先级

编码前必须完整阅读：

```text
plan/final_design.md
plan/final_plan.md
plan/final_discussion.md
docs/decisions/ADR-0001-authority-and-scope.md
docs/decisions/ADR-0002-hypothesis-lanes.md
docs/decisions/ADR-0003-ledger-and-source-semantics.md
docs/decisions/ADR-0004-partial-eligibility.md
docs/decisions/ADR-0005-scientific-decision-authority.md
docs/decisions/ADR-0006-mcp-side-effects.md
reports/p0/P0_GATE_REPORT.md
reports/p0/P0_GATE_REPORT.json
reports/p0/V4_REMEDIATION_WORKLOG.md
```

P1 实施权威顺序：

```text
final_design.md
→ final_plan.md
→ final_discussion.md
→ ADRs
→ P0 frozen schemas/policies
→ 本提示词
```

如本提示词与前三份 final 权威文件冲突，以 final 权威文件为准，并在 P1 worklog 中明确记录冲突，不得静默选择。

历史文件只能作为问题来源，不能作为 P1 实施权威：

```text
../benchmark/canonical_identity.py
../benchmark/*.py
../core/*.py
plan/qwen_*.md
plan/CLAUDE_*.md
plan/chatgpt-*-v1/v2.md
FUSION_DESIGN_V5.md
UNIFIED_*.md
旧 P0 benchmark reports
```

---

## 2. 现有 legacy 代码的已知危险

必须只读检查：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/benchmark/canonical_identity.py
```

特别关注：

```text
第 60–77 行：pick_main
第 96–128 行：COFACTORS
第 131–157 行：_pick_transformed
第 161–185 行：transformed_pair
第 188–202 行：group_key/main_substrate/main_product
```

旧逻辑的核心风险：

```text
一侧选一个片段
另一侧再独立选一个片段
→ 强行形成单一 X/Y pair
```

以及：

```text
exclude = COFACTORS | spectators
```

旧模块可以作为 audit target 和兼容性输入，但不得继续作为 canonical truth。

必须明确：

```text
legacy transformed_pair
≠ verified fragment-lineage

legacy main_substrate/main_product
≠ authoritative A→B

COFACTORS membership
≠ participant deletion

reaction center pairs
≠ complete atom mapping
```

P1-T3 必须用新的完整反应、mapping 和 lineage 视角审计这些旧输出。

不得原地修改：

```text
../benchmark/
../core/
../reports/
```

它们在 P1 中是只读 legacy source。所有新实现和报告必须落在 `demov2/`。

---

## 3. P0 冻结合同必须保持全绿

任何 P1 修改都不得破坏 P0。

开始前运行：

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2

PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  tests/contracts -q -p no:cacheprovider -ra

.venv/bin/python scripts/run_p0_gate.py
```

预期 baseline：

```text
290 passed
P0 Gate 10/10 PASS
```

把实际结果写入：

```text
reports/p1/P1_BASELINE.md
reports/p1/P1_BASELINE.json
```

每完成一个 P1 task，都必须重新运行 P0 contract tests。

如果 P0 任何测试失败：

```text
立即停止当前 task
→ 修复回归
→ 不得继续下一个 task
```

不得通过修改 P0 测试、ADR 或 final docs 来消除失败。

---

## 4. 权限与安全边界

### 4.1 允许

允许在：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
```

内创建和修改 P1 所需的：

```text
reaction_agent/
tests/
scripts/
reports/p1/
reports/data_audit/
docs/
pyproject.toml
dependency lock
README.md
```

### 4.2 禁止

禁止：

- 写入 `../benchmark/`、`../core/` 或其他 legacy 路径；
- 修改原始数据；
- 覆盖用户已有 source records；
- 删除未知文件；
- 使用 `git reset --hard`、`git clean`、`git checkout --`；
- 未授权执行 `git add/commit/push`；
- 静默联网下载数据；
- 将 fixture、toy reaction 或合成结果冒充真实数据 audit；
- 将 mapper 输出称为 mechanism；
- 将 MCS 或 center pairs 称为 full mapping；
- 将 COFACTORS 用作 destructive stripping；
- 将未知信息填成默认事实；
- 用 `skip/xfail` 掩盖 P1 Gate 失败；
- 为了过 Gate 改写权威设计；
- 进入 retrieval/candidate/LLM/MCP 阶段。

### 4.3 外部依赖

当前 `.venv` 预检状态：

```text
rdkit    absent
numpy    absent
networkx absent
scipy    absent
```

P1-T1 必须先做依赖决策。

要求：

- 只加入真正需要的依赖；
- 使用与 Python 3.11 兼容的版本；
- 生成真实 lock；
- 记录安装命令和 resolved version；
- 不得仅在系统环境“碰巧可用”；
- 测试和 Gate 必须使用项目 `.venv`；
- 如果安装需要联网或额外权限，向用户请求，不得静默改用未知系统环境；
- 不得把一个无法安装的 mapper 假装成可用。

允许使用 fixture/fake mapper 测试 adapter contract，但：

> 没有真实 mapper 和真实数据运行证据时，P1 Gate 不得 PASS。

---

## 5. 总体实施顺序

必须严格按以下顺序：

```text
P1-Preflight
→ P1-T1 Package bootstrap
→ P1-T2 Strict domain schemas
→ P1-T3 Legacy lineage audit
→ P1-T4 Atom-mapping adapter
→ P1-T5 Participant roles / donor eligibility
→ P1-T6 Bipartite fragment-lineage graph
→ P1-T7 SourceReactionLedger
→ P1-T8 CandidateAnalogyLedger skeleton
→ P1-T9 Eligibility / quarantine
→ P1-T10 Snapshot builder
→ P1-T11 Manual audit protocol and execution
→ P1 Gate
→ ChatGPT read-only audit
```

不得并行编写依赖关系尚未冻结的下游模块。

每个 task 使用：

```text
READ
→ ASSUMPTIONS
→ RED tests
→ minimal implementation
→ GREEN targeted tests
→ full P0 + P1 regression
→ artifact/report
→ task checkpoint
```

如前一 task 未通过 checkpoint，不得开始后一 task。

---

## 6. P1-Preflight：真实资源盘点

在写实现前，新增：

```text
scripts/p1_preflight.py
```

输出：

```text
reports/p1/P1_PREFLIGHT.md
reports/p1/P1_PREFLIGHT.json
```

必须机器可读记录：

### 6.1 Runtime

```text
Python version
Pydantic version
pytest version
RDKit availability/version
NumPy availability/version
graph dependency availability/version
mapper backend availability/version
platform
working directory
package version
```

### 6.2 Legacy source inventory

至少盘点：

```text
../benchmark/canonical_identity.py
../benchmark/*.py
../core/*.py
../reports/*.json
../reports/p0_attrib/*.json
```

对可能作为数据输入的文件记录：

```text
absolute path
exists
size
SHA-256
record format
record count（能安全读取时）
schema/keys sample
read-only status
```

### 6.3 Real reaction source

必须找到真实完整反应记录来源。

如果只找到 benchmark 汇总 JSON、没有完整 reaction rows：

```text
P1 data source = BLOCKED
```

不得从结果报告反推或伪造完整反应。

如数据依赖环境变量或外部数据根：

- 只读取变量是否存在和路径；
- 不在报告输出密钥或敏感值；
- 记录 resolved data root 的 hash/manifest；
- 不允许默认扫描用户整个 home。

### 6.4 Proline/2OG case discovery

必须搜索真实 source record：

```text
2-oxoglutarate + proline + O2
→ succinate + hydroxyproline + CO2
```

记录：

```text
source name
source record ID
raw reaction representation
participants
direction
atom mapping availability
stoichiometry availability
provenance
```

如果找不到真实 record：

- 明确标记 `required_case_missing`；
- fixture 只能用于算法单元测试；
- P1 Gate #1 不得通过。

### 6.5 Preflight stop condition

以下任一情况发生，停止真实 P1 pipeline 实施，只允许完成接口/fixture 测试，并向用户报告：

```text
真实完整反应源不可访问
核心依赖无法安装
没有任何可用 atom mapper
原始 reaction 许可/权限不明确
写入范围需要超出 demov2
```

不得用“先假设数据存在”继续并最终宣称完成。

---

## 7. P1-T1：Package bootstrap

### 7.1 目标

把 P0 schema skeleton 扩展为可安装、可配置、可重放的 P1 package，而不引入 P2 业务逻辑。

### 7.2 建议最小结构

可根据现有代码调整，但避免无必要层级：

```text
reaction_agent/
├── __init__.py
├── config.py
├── hashing.py
├── provenance.py
├── schemas/
├── mapping/
│   ├── __init__.py
│   ├── base.py
│   └── adapter.py
├── roles/
│   ├── __init__.py
│   └── resolver.py
├── lineage/
│   ├── __init__.py
│   └── resolver.py
├── ledgers/
│   ├── __init__.py
│   └── source_builder.py
├── eligibility/
│   ├── __init__.py
│   └── engine.py
└── snapshot/
    ├── __init__.py
    ├── builder.py
    └── loader.py
```

如一个模块即可完成，不得为了“架构感”拆成十几个空文件。

### 7.3 配置合同

配置必须显式包含：

```text
input source path/manifest
output snapshot root
mapper backend
mapper version/parameters
normalization version
role policy version
lineage resolver version
ledger version
eligibility policy version
random seed
timeout
strict mode
```

禁止：

```text
隐式当前目录数据
隐式最新 snapshot
隐式系统 mapper
隐式随机种子
隐式写 legacy source
```

### 7.4 Logging/redaction

要求：

- structured logging；
- 不输出 secrets；
- 不把完整敏感路径或环境值无条件写日志；
- 每个 build 有 run ID/correlation ID；
- error 中保留 source record ID；
- 不吞异常。

### 7.5 Version endpoint

实现轻量只读函数，例如：

```python
get_build_info() -> BuildInfo
```

包含：

```text
package version
schema version
mapper/resolver/ledger/policy versions
Python/runtime
```

不需要 HTTP server。

### 7.6 T1 测试

至少：

```text
package import
explicit snapshot path required
deterministic config serialization
seed required and stable
unknown config field rejected
legacy source path read-only
no implicit write
redaction
version endpoint deterministic
lock file exists
```

### 7.7 T1 checkpoint

交付：

```text
reports/p1/P1_T1_PACKAGE_BOOTSTRAP.md
```

未满足依赖 lock 和 no-legacy-write，不得进入 T2。

---

## 8. P1-T2：Strict domain schemas

### 8.1 原则

实现 P0 skeleton，不得破坏已经冻结的字段语义。

优先扩展已有：

```text
reaction_agent/schemas/evidence.py
reaction_agent/schemas/mapping.py
reaction_agent/schemas/lineage.py
reaction_agent/schemas/ledger.py
reaction_agent/schemas/candidate.py
reaction_agent/schemas/result.py
reaction_agent/schemas/common.py
```

不得复制第二套同名 truth models。

### 8.2 必须具备的 P1 对象

至少：

```text
SourceRecordProvenance
NormalizedReactionRecord
ReactionParticipant
MappingReport
FormalMappedAtomPair
MechanisticAtomOrigin
ParticipantRoleHypothesis
DonorEligibilityAssessment
LineageEdge
FragmentLineageGraph
ResolvedTransformedLineage
LineageResolution
SourceReactionLedger
CandidateAnalogyLedger
EligibilityDecision
QuarantineRecord
SnapshotManifest
SnapshotRecord
ManualAuditRecord
```

如已有对象覆盖，不得重复创建。

### 8.3 Stable ID

所有 canonical P1 entity ID 必须：

```text
deterministic
namespaced
content-derived or source-identity-derived
stable across atom ordering where chemistry is equivalent
version-aware where semantics affect identity
```

建议格式：

```text
rxn_<hash>
participant_<hash>
lineage_<hash>
ledger_<hash>
snapshot_<hash>
```

必须记录 ID preimage contract。

禁止：

```text
Python hash()
随机 UUID 作为 canonical identity
依赖 dict insertion order
依赖输入 atom order
依赖运行时间
```

### 8.4 Content hash

统一 canonical serialization：

- UTF-8；
- sorted keys；
- 明确 list 顺序语义；
- 非语义集合排序；
- 不包含生成时间、绝对临时路径；
- 版本字段显式；
- SHA-256 或等价稳定 hash。

必须测试：

```text
同内容不同 dict key order → same hash
非语义 participant input order变化 → canonical result按合同处理
source change → different hash
policy version change → appropriate derived hash change
timestamp change → canonical content hash unchanged
```

### 8.5 Provenance

canonical record 必须有：

```text
source name/version
source record ID
source file/hash
raw record hash
normalizer version
created-by build/run ID
```

unknown provenance 不得静默填 `"unknown"` 后进入 strict。

### 8.6 T2 测试

至少：

```text
unknown field reject
enum enforcement
stable ID
content hash
required provenance
lossless participant count
duplicate stoichiometric participant preservation
ledger statuses
PredictionResult invariants
candidate origin
hypothesis lane separation
JSON schema freshness
P0 290 tests unchanged
```

### 8.7 T2 checkpoint

交付：

```text
reports/p1/P1_T2_DOMAIN_SCHEMAS.md
schemas/json/ P1 exports（仅冻结对象）
```

不得把仍在探索的内部对象全部导出为公共 schema。

---

## 9. P1-T3：Legacy lineage audit

### 9.1 目标

只读重放 legacy：

```text
canonical_identity.transformed_pair
main_substrate
main_product
group_key
```

并与新的完整反应/mapping/lineage证据对比。

### 9.2 不得先改 legacy

audit 必须先保存旧行为。

不得为了减少 mismatch：

- 修改 `canonical_identity.py`；
- 更改 legacy reports；
- 删除失败 records；
- 只抽取成功案例。

### 9.3 Audit record

每条 reaction 至少记录：

```text
source_record_id
raw reaction
complete reactant participants
complete product participants
legacy selected A
legacy selected B
legacy excluded cofactors/spectators
mapping availability
new lineage candidates
new resolved lineages
legacy A→B supported_by_same_lineage: true/false/unknown
mismatch category
severity
strict eligibility impact
example atom maps/changed atoms
```

### 9.4 Mismatch categories

至少：

```text
cross_lineage_pair
cofactor_selected_as_main
true_small_substrate_stripped
spectator_misclassified
split_collapsed
merge_collapsed
multiple_lineages_collapsed
tie_silently_resolved
mapping_missing
mapping_partial
direction_unknown
unparseable
legacy_pair_supported
insufficient_evidence
```

### 9.5 统计

必须按以下分层统计：

```text
reaction class
participant count
reactant fragment count
product fragment count
COFACTORS pattern
source
mapping status
direction
mismatch category
severity
```

输出数量和分母，不得只报百分比。

### 9.6 必需案例

必须包含真实：

```text
2-oxoglutarate + proline + O2
→ succinate + hydroxyproline + CO2
```

如果真实 mapping 足够，预期至少识别：

```text
proline → hydroxyproline
2-oxoglutarate → succinate
formal O transfer assignment with method and ambiguity
```

严禁：

```text
2-oxoglutarate → hydroxyproline
```

如果 mapping 不足：

```text
不得猜测
→ 标记 insufficient_mapping
→ diagnostic/quarantine
```

### 9.7 输出

必须生成：

```text
reports/data_audit/legacy_lineage_audit.json
reports/data_audit/legacy_lineage_audit.md
```

JSON 包含完整机器可读 counts/categories/examples/source IDs。

MD 是 JSON 的人类可读视图，数字必须一致。

### 9.8 T3 checkpoint

Audit 可以发现高 prevalence bug，但不能因此降低 correctness requirement。

未找到真实 source 或没有可验证 mapping 时：

```text
T3 = PARTIAL/BLOCKED
P1 Gate = BLOCKED
```

不得用 fixture 报告替代真实 audit。

---

## 10. P1-T4：Atom-mapping adapter

### 10.1 Adapter，而不是 mapper 神化

实现一个最小 protocol：

```python
class AtomMapper(Protocol):
    def map_reaction(self, reaction: NormalizedReactionRecord) -> MappingReport:
        ...
```

必须捕获：

```text
mapper_name
mapper_version
parameters
input_hash
output_hash
runtime
timeout
status
quality flags
```

### 10.2 Mapping 状态

严格使用冻结状态：

```text
fully_mapped
partially_mapped
unmapped
mapping_failed
mapping_ambiguous
```

不得把：

```text
调用成功
```

等同于：

```text
fully_mapped
```

### 10.3 质量验证

至少计算：

```text
map number uniqueness
mapped heavy atom fraction
changed atom coverage
reactant/product map consistency
duplicate map IDs
unmapped changed atoms
symmetry ambiguity
resonance/tautomer ambiguity
```

### 10.4 Formal vs mechanistic

普通 mapper 只能输出：

```text
formal_mapped_source_assignment
```

不得自动输出：

```text
mechanistic_atom_origin
```

只有独立 curated/isotope/mechanistic evidence 才允许 mechanistic object。

### 10.5 Fallback

允许：

```text
MCS fallback
center-pair diagnostic
unmapped diagnostic
```

但必须：

- 明确 `fallback_method`；
- 降低 mapping status/quality；
- 不进入 strict mapped evidence；
- 不伪装成 full atom correspondence。

### 10.6 T4 测试

至少：

```text
fully mapped
partially mapped
unmapped
mapper failure
timeout
duplicate map IDs
missing maps
mapped reactants/unmapped products
atom-order permutation
multi-fragment
symmetric atoms
resonance/tautomer ambiguity
MCS-only not strict
center pairs not full mapping
mapper does not create mechanism evidence
typed/flat mapping consistency
```

必须包含 deterministic fake mapper 单元测试。

P1 Gate 前还必须有真实 mapper adapter 集成测试。

### 10.7 T4 checkpoint

交付：

```text
reports/p1/P1_T4_MAPPING_ADAPTER.md
reports/p1/mapping_integration_sample.json
```

真实 mapper 不可用时，T4 只能标记：

```text
UNIT_CONTRACT_COMPLETE
INTEGRATION_BLOCKED
```

不能标 PASS。

---

## 11. P1-T5：Participant roles 与 donor eligibility

### 11.1 完整 participant 不可丢失

输入完整反应后，输出 participant records 必须一一可追溯。

必须保留：

```text
所有 reactants
所有 products
重复 stoichiometric entries
O2
H2O
CO2
NH3
H+
electrons
metal ions
NAD(P)
ATP/ADP/AMP
CoA
SAM/SAH
FAD/FMN
small organic co-substrates
unknown participants
```

不得用 `set/frozenset` 作为 canonical complete reaction representation，因为会丢失重复项和计量。

### 11.2 Role vocabulary

使用冻结词表：

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

Role 应是带证据的 hypothesis：

```text
role
score or ordered evidence strength
evidence codes
policy version
ambiguity
```

不得把 heuristic score 解释为真实概率。

### 11.3 COFACTORS 的唯一合法作用

从 legacy：

```text
../benchmark/canonical_identity.py:101-128
```

读取并 canonicalize COFACTORS list，记录 source hash。

只允许用于：

```text
participant_role_prior
donor_eligibility_prior
retrieval_downweighting_prior
```

绝不允许：

```text
删除 participant
直接赋 ground-truth role
从 atom balance 排除
阻止其作为 transformed lineage
```

特别测试：

- O2 可以是 formal atom source；
- H2O 可以参与 hydrolysis；
- CO2 可以是 coproduct；
- NAD(P) 证据完整保留；
- 小分子可以是 transformed substrate；
- 2-oxoglutarate 不得因“小/常见共底物”被删除；
- COFACTORS prior 与 mapping evidence 冲突时保留冲突/ambiguity。

### 11.4 Donor eligibility

Donor eligibility 不是 role 的同义词。

至少考虑：

```text
mapped atom retention
changed mapped atoms
transferred atoms
size/complexity
stoichiometry
source annotation
COFACTORS prior
reaction direction
mapping quality
lineage ambiguity
```

输出：

```text
eligible
conditionally eligible
not eligible
unknown
reason codes
supporting evidence IDs
```

### 11.5 T5 checkpoint

交付：

```text
reports/p1/P1_T5_PARTICIPANT_ROLES.md
reports/p1/participant_role_sample.json
```

必须证明：

```text
input participant multiset == persisted participant multiset
```

canonicalization 的可解释变化除外，但必须有 mapping。

---

## 12. P1-T6：Bipartite fragment-lineage graph

### 12.1 Graph 定义

构建：

```text
reactant participant nodes
↕ mapped lineage edges
product participant nodes
```

Edge 至少包含：

```text
shared_mapped_heavy_atoms
reactant_retention_fraction
product_origin_fraction
changed_mapped_atoms
bond_edit_participation
transferred_atom_sets
scaffold_continuity
role compatibility
mapping quality
evidence IDs
```

### 12.2 核心禁止

严禁：

```text
reactant side 独立 pick one
product side 独立 pick one
然后强行配对
```

严禁：

```text
tuple max() 静默解 tie
```

严禁：

```text
始终强制一个 primary pair
```

### 12.3 Resolution

输出必须支持：

```text
zero lineage
one lineage
multiple independent transformed lineages
split
merge
atom transfer
ambiguity set
unresolved
```

关键 ambiguity：

```text
不得进入 strict
→ diagnostic or quarantine
```

role ambiguity 不影响某一条明确 lineage 时，可以局部保留该 lineage，但必须记录 ambiguity。

### 12.4 Stable lineage ID

lineage identity 至少基于：

```text
reaction identity
reactant participant identity
product participant identity
mapped atom correspondence/edit identity
resolver semantic version
```

不得依赖：

```text
输入 participant 顺序
atom enumeration 顺序
运行时间
随机 tie
```

### 12.5 必需回归

至少：

```text
proline hydroxylation with 2OG/O2
redox with NAD(P)
oxygen incorporation
hydrolysis
transferase
decarboxylation
cleavage
condensation
split
merge
equal-score tie
partial mapping
MCS fallback
atom-order permutation
```

### 12.6 Proline/2OG 硬 Gate

对于真实案例，以下之一必须成立：

```text
A. 正确解析：
   proline → hydroxyproline
   2OG → succinate
   O transfer 有 formal assignment/ambiguity
```

或：

```text
B. 因 mapping/ambiguity 不足明确 quarantine
```

绝不能：

```text
2OG → hydroxyproline
```

且绝不能在错误配对后仍进入 production index。

### 12.7 T6 checkpoint

交付：

```text
reports/p1/P1_T6_LINEAGE_GRAPH.md
reports/p1/lineage_regression_cases.json
```

报告必须展示每个 regression 的 nodes、edges、resolution、ambiguity 和 eligibility，而不只是最终 pair。

---

## 13. P1-T7：SourceReactionLedger

### 13.1 目标

Ledger 表达来源数据库实际记录和能够形式验证的内容，不表达 X→Y 猜测。

### 13.2 必须实现

```text
complete reactant entries
complete product entries
role assignments
stoichiometry
formal atom transfer assignments
mechanistic origin evidence（仅独立证据）
added atom sources
removed atom sinks
element balance
charge balance
hydrogen policy
proton policy
electron policy
cofactor changes
source completeness
mapping completeness
balance status
unknowns
evidence IDs
```

### 13.3 Balance

正式状态：

```text
fully_balanced_explicit_reaction
heavy_atom_balanced_with_implicit_h_e_policy
partial_or_unbalanced_source
```

每个新增 changed heavy atom：

- 有 formal source assignment；
- 或明确 `unknown_source`；
- 若 strict 需要来源而无法追踪，不得 strict eligible。

### 13.4 不得伪造

缺少 stoichiometry：

```text
unknown
```

不是：

```text
默认 1 且当作来源事实
```

缺少 H+/electron：

```text
明确 policy
```

不是：

```text
静默补平
```

formal mapper：

```text
formal assignment
```

不是：

```text
proven mechanistic origin
```

### 13.5 T7 测试

至少：

```text
redox
O2 incorporation
hydrolysis
decarboxylation
transfer
charge mismatch
missing stoichiometry
incomplete source
ambiguous formal assignment
unknown atom source
mechanistic evidence absent
unbound mechanistic evidence reject
complete participant preservation
```

### 13.6 T7 checkpoint

交付：

```text
reports/p1/P1_T7_SOURCE_LEDGER.md
reports/p1/source_ledger_samples.json
```

---

## 14. P1-T8：CandidateAnalogyLedger skeleton

本阶段只实现 schema/builder skeleton 和 fixtures，不实现完整 X→Y generator。

必须表达：

```text
source_ledger_id
candidate_id
query candidate adaptation
inherited donor context
inherited assumptions
formal atom transfer assignments
formal balance under assumptions
unknown actual co-substrates
unknown actual cofactors
unknown actual stoichiometry
candidate balance status
unknowns
evidence IDs
```

关键不变量：

```text
donor context is assumption = true
source ledger link exists
candidate ID belongs current context
donor cofactor ≠ proven X→Y cofactor
formal balance under assumptions ≠ observed balance
```

允许 fixtures：

- 构造候选 adaptation；
- 验证 source→candidate boundary；
- 验证 unknowns 保留。

禁止：

- 真正生成 Y；
- candidate 排名；
- LLM rationale；
- 把 fixture candidate 当预测结果。

交付：

```text
reports/p1/P1_T8_CANDIDATE_LEDGER_SKELETON.md
```

---

## 15. P1-T9：Eligibility / quarantine engine

### 15.1 唯一 policy authority

复用：

```text
reaction_agent/policies/partial_eligibility.py
docs/decisions/ADR-0004-partial-eligibility.md
```

不得复制另一套字符串判断。

### 15.2 输出

对每条 reaction/lineage 输出 typed：

```text
strict eligibility
required warnings
quarantine behavior
evaluation bucket
research/diagnostic eligibility
reason codes
evidence IDs
policy version
```

### 15.3 Matrix

必须覆盖 8 行：

```text
fully balanced + reliable mapping/lineage
heavy atom balanced + implicit H/e policy
missing noncritical cofactor stoichiometry
unknown changed heavy atom source
critical element/charge contradiction
role ambiguity not affecting lineage
lineage ambiguity affecting identity
reaction direction unknown
```

### 15.4 Fail-closed

如果决定 strict eligibility 所需字段缺失：

```text
不得默认 eligible
```

应：

```text
diagnostic/strict_prohibited/quarantine
```

按 policy 决定。

### 15.5 Production index boundary

必须证明：

```text
quarantined records never enter production index
strict_prohibited records never enter strict production index
conditional records carry required warnings
diagnostic records remain auditable
```

### 15.6 T9 checkpoint

交付：

```text
reports/p1/P1_T9_ELIGIBILITY.md
reports/p1/eligibility_matrix_execution.json
```

JSON 必须包含每个 matrix row 的正例和反例。

---

## 16. P1-T10：Immutable snapshot builder

### 16.1 Pipeline

必须实现：

```text
source load
→ raw record preservation
→ normalization
→ mapping
→ participant roles
→ lineage graph/resolution
→ source ledger
→ eligibility
→ production index / diagnostic / quarantine
→ manifest
→ snapshot hash
→ atomic finalize
```

### 16.2 Snapshot 属性

必须：

```text
immutable
content-addressed
deterministic rebuild
source/provenance complete
raw + normalized records preserved
mapper/resolver/schema/policy versions recorded
quarantine explicit
all filter counts/reasons recorded
```

### 16.3 Manifest

至少包含：

```text
snapshot schema version
source files and hashes
source record count
normalization version
mapper name/version/parameters
role resolver version
lineage resolver version
ledger version
eligibility policy version/hash
included strict count
conditional count
diagnostic count
quarantine count
failure counts by reason
record content hashes
production index hash
quarantine index hash
snapshot hash
build status
```

### 16.4 Atomicity

构建必须：

```text
write temporary build directory
→ validate all artifacts
→ compute final hash
→ atomic finalize
→ mark complete only last
```

中断 build：

- 不得出现 `complete=true`；
- loader 不得当成有效 snapshot；
- 不覆盖已有 immutable snapshot。

### 16.5 Loader

loader 必须：

- 需要显式 snapshot ID/path；
- read-only；
- verify manifest/hash；
- 拒绝 incomplete snapshot；
- 拒绝 hash mismatch；
- 不自动选择“最新”；
- 不修改 snapshot。

### 16.6 Determinism

同 source + 同 versions + 同 config：

```text
snapshot hash identical
record IDs identical
index content identical
```

source、policy 或 semantic version 变化：

```text
相应 hash 必须变化
```

不得把：

```text
timestamp
temporary path
run ID
unordered iteration
```

纳入 canonical snapshot content hash。

它们可以存在于 non-canonical build metadata。

### 16.7 T10 测试

至少：

```text
deterministic rebuild
source change → new hash
policy change → new hash
quarantine included in manifest
production excludes quarantine
all filters counted
interrupted build not complete
hash mismatch rejected
read-only load
explicit snapshot required
existing snapshot not overwritten
input record ordering stability
```

### 16.8 T10 checkpoint

交付：

```text
reports/p1/P1_T10_SNAPSHOT.md
reports/p1/snapshot_build_sample.json
```

真实 source snapshot 和 fixture snapshot 必须明确分开。

---

## 17. P1-T11：Manual audit protocol

### 17.1 不能只写 protocol 不执行

P1 Gate 要求 audit complete。

必须同时提供：

```text
protocol
sample manifest
annotation form/schema
independent annotations
adjudication
metrics
pass/fail decision
```

如果缺少第二位独立 annotator 或人工审核资源：

```text
P1 Gate = BLOCKED_PENDING_MANUAL_AUDIT
```

不得让同一个执行过程复制两份答案冒充 double annotation。

### 17.2 Stratification

覆盖：

```text
reaction class
participant count
mapping quality
cofactor pattern
source
ledger status
eligibility/quarantine reason
single/multiple lineage
split/merge/transfer
ambiguity
```

数据集较小时做全量 audit；较大时给出样本量依据和随机种子。

### 17.3 Rubric

分别标注：

```text
participant preservation
mapping correctness
formal/mechanistic labeling
role evidence
lineage identity
split/merge/transfer
ledger completeness
balance status
eligibility
quarantine correctness
catastrophic mismatch
```

### 17.4 Catastrophic error

至少包括：

```text
cross-lineage A→B indexed as strict
participant evidence destructively removed
critical ambiguity silently resolved
unmapped/MCS-only labeled fully mapped
formal mapping labeled mechanism
quarantined record in production index
snapshot hash/replay failure
source record mismatch
```

### 17.5 Agreement

报告：

```text
raw agreement
per-field agreement
disagreement count
adjudication outcomes
catastrophic error count
confidence interval where applicable
```

不得把 LLM 自评 confidence 当作 audit confidence。

### 17.6 Pass threshold

在 protocol 中预先冻结阈值，不能看结果后调整。

最低硬条件：

```text
catastrophic errors in production index = 0
proline/2OG correct or quarantined
critical tie silently selected = 0
quarantine leakage = 0
participant destructive loss = 0
formal→mechanistic false upgrade = 0
snapshot replay/hash failure = 0
```

其余 field-level threshold 必须在执行前写明依据。

### 17.7 T11 输出

```text
docs/manual_audit_protocol.md
schemas/json/ManualAuditRecord.json
reports/p1/manual_audit_sample_manifest.json
reports/p1/manual_audit_annotations_a.json
reports/p1/manual_audit_annotations_b.json
reports/p1/manual_audit_adjudication.json
reports/p1/manual_audit_report.md
reports/p1/manual_audit_report.json
```

如人工审核尚未完成，不得生成虚假的 annotations。

---

## 18. P1 Gate 实现

新增：

```text
scripts/run_p1_gate.py
tests/p1/test_p1_gate_contract.py
```

输出：

```text
reports/p1/P1_GATE_REPORT.md
reports/p1/P1_GATE_REPORT.json
```

### 18.1 十项 Gate

#### P1-G01：Package/runtime/lock

验证：

```text
package import
supported Python
dependency lock
explicit config/snapshot
no legacy write
```

#### P1-G02：Strict schemas/IDs/provenance

验证：

```text
strict schema
stable IDs
content hashes
required provenance
P0 contract still green
```

#### P1-G03：Legacy lineage audit complete

验证：

```text
真实 source used
counts/denominators
mismatch categories
source IDs/examples
proline/2OG included
```

#### P1-G04：Mapping adapter

验证：

```text
real adapter integration
quality metrics
failure states
MCS not strict
formal not mechanism
```

#### P1-G05：Participant preservation/roles

验证：

```text
complete participant multiset
COFACTORS no deletion
small molecule can be substrate/source
ambiguity retained
```

#### P1-G06：Lineage graph

验证：

```text
bipartite graph
split/merge/transfer
no independent picking
no silent tie
stable IDs
proline/2OG correct or quarantined
```

#### P1-G07：Dual ledgers

验证：

```text
SourceReactionLedger valid
CandidateAnalogyLedger skeleton valid
unknowns preserved
formal/mechanistic separated
source linkage valid
```

#### P1-G08：Eligibility/quarantine

验证：

```text
all 8 policy rows
warnings
quarantine behavior
production index excludes prohibited/quarantine
all reasons typed
```

#### P1-G09：Snapshot reproducibility

验证：

```text
deterministic rebuild
content hash
manifest complete
all filters counted
interrupted build invalid
read-only loader
```

#### P1-G10：Manual audit and full tests

验证：

```text
double annotation complete
adjudication complete
threshold frozen before results
catastrophic errors = 0
all P0/P1 tests pass
zero fail/error/skip/xfail/xpass
```

### 18.2 Gate 不得只检查文件存在

禁止：

```python
passed = report_file.exists()
```

Gate 必须读取并验证机器可读 evidence。

例如：

- 对 snapshot 重建两次并比较 hash；
- 读取 production/quarantine index 检查交集为空；
- 构造 critical tie，确认不返回单一 strict lineage；
- 构造 COFACTORS participant，确认完整反应仍保留；
- 检查 MappingReport 不自动生成 mechanism；
- 检查 manual audit annotations 来自两个不同 annotator IDs；
- 结构化读取 pytest stats。

### 18.3 Mutation / anti-false-positive

在隔离副本中至少验证：

```text
删除 participant preservation check → Gate fail
让 critical tie 取 max → Gate fail
让 MCS 标 full mapping → Gate fail
让 mapper 自动填 mechanism → Gate fail
把 quarantine record 放进 production → Gate fail
让 snapshot hash 非确定 → Gate fail
删除 proline/2OG required case → Gate fail
加入一个 skipped/xfailed test → Gate fail
```

Mutation 只能在临时副本中进行，不得污染正式代码。

Gate 任一失败：

```text
exit code != 0
status = NOT_READY_FOR_CHATGPT_AUDIT
P2 = BLOCKED
```

---

## 19. 测试布局

建议：

```text
tests/
├── contracts/          # P0 frozen tests
├── p1/
│   ├── test_config.py
│   ├── test_hashing_ids.py
│   ├── test_source_loader.py
│   ├── test_mapping_adapter.py
│   ├── test_participant_roles.py
│   ├── test_lineage_graph.py
│   ├── test_source_ledger.py
│   ├── test_candidate_ledger_skeleton.py
│   ├── test_eligibility_engine.py
│   ├── test_snapshot_builder.py
│   ├── test_manual_audit_contract.py
│   └── test_p1_gate_contract.py
└── fixtures/
    └── p1/
```

Fixtures 必须标明：

```text
synthetic
curated
real-source-derived
license/provenance
```

不得把 synthetic fixture 混入真实 audit counts。

### 19.1 每 task 测试命令

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  tests/p1/<target_file>.py \
  -q -p no:cacheprovider -ra
```

### 19.2 全部 P1 测试

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  tests/p1 -q -p no:cacheprovider -ra
```

### 19.3 全部回归

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  tests -q -p no:cacheprovider -ra
```

要求：

```text
failed = 0
errors = 0
skipped = 0
xfailed = 0
xpassed = 0
passed = collected
```

---

## 20. P1 执行报告

整个 P1 期间维护：

```text
reports/p1/P1_REMEDIATION_WORKLOG.md
```

每个 task 记录：

```text
timestamp
assumptions
input files/hashes
RED tests
implementation decision
changed files
targeted GREEN
full regression
real vs fixture evidence
deviations
risks
blocked items
next task authorization
```

不得只写：

```text
implemented successfully
```

必须提供精确命令、统计和 artifact path。

---

## 21. P1 最终提交材料

全部完成后，生成：

```text
reports/p1/SUBMISSION_TO_CHATGPT_P1.md
reports/p1/P1_GATE_REPORT.md
reports/p1/P1_GATE_REPORT.json
reports/p1/P1_REMEDIATION_WORKLOG.md
reports/data_audit/legacy_lineage_audit.md
reports/data_audit/legacy_lineage_audit.json
reports/p1/manual_audit_report.md
reports/p1/manual_audit_report.json
```

提交封面必须包含：

1. P1 十项 Gate；
2. P0 baseline 和最终回归；
3. P1 targeted/full test 精确统计；
4. runtime/dependency versions；
5. real source manifest/hash；
6. mapper backend/version；
7. proline/2OG 实际结果；
8. participant preservation统计；
9. lineage mismatch统计；
10. eligibility/quarantine统计；
11. snapshot deterministic rebuild 证据；
12. manual audit 样本、agreement、adjudication；
13. catastrophic error count；
14. changed files；
15. deviations/risks；
16. git/user-files protection；
17. P2 状态。

最后只允许写：

```text
READY_FOR_CHATGPT_P1_READ_ONLY_AUDIT
P2 BLOCKED pending ChatGPT audit
```

不得自行写：

```text
P1 finally accepted
P2 authorized
system can reliably predict X→Y
```

---

## 22. P1 最终完成清单

只有以下全部满足，才允许提交 ChatGPT：

### P0 preservation

- [ ] P0 290 个 baseline contracts 保持全绿；
- [ ] P0 Gate 10/10；
- [ ] P0 fail-closed hypothesis relations 未弱化；
- [ ] P0 dual-ledger/mapping/mechanism/eligibility/MCP contracts 未弱化。

### Runtime/package

- [ ] package 可安装/导入；
- [ ] Python/依赖版本满足约束；
- [ ] dependency lock 存在；
- [ ] config 显式；
- [ ] snapshot 显式；
- [ ] deterministic seed；
- [ ] no legacy write；
- [ ] logging/redaction 验证。

### Real data

- [ ] 完整真实 reaction source 可访问；
- [ ] source files 有 hash/manifest；
- [ ] raw reaction 不丢 participants；
- [ ] fixture 与 real evidence 严格分离；
- [ ] proline/2OG 真实 source record 已找到。

### Mapping

- [ ] real mapper adapter 可运行；
- [ ] mapper name/version/parameters 保存；
- [ ] fully/partial/unmapped/failure/ambiguous 状态真实；
- [ ] map uniqueness/coverage 验证；
- [ ] MCS 不进入 strict；
- [ ] center pairs 不称 full mapping；
- [ ] formal mapping 不称 mechanism；
- [ ] ambiguity 保留。

### Roles/participants

- [ ] complete participant multiset preserved；
- [ ] COFACTORS 不删除 participant；
- [ ] O2/H2O/CO2/NAD(P)/metal/small molecules 保留；
- [ ] role hypotheses 有 evidence；
- [ ] role ambiguity 保留；
- [ ] donor eligibility 与 role 分开。

### Lineage

- [ ] bipartite graph 完成；
- [ ] edge features 完成；
- [ ] multiple lineage 支持；
- [ ] split/merge/transfer 支持；
- [ ] no independent side picking；
- [ ] no tuple-max tie；
- [ ] no forced primary pair；
- [ ] stable lineage IDs；
- [ ] proline→hydroxyproline 正确或 quarantine；
- [ ] 2OG→succinate 正确或 quarantine；
- [ ] 2OG→hydroxyproline 不进入 index。

### Ledgers

- [ ] SourceReactionLedger 构建；
- [ ] CandidateAnalogyLedger skeleton；
- [ ] source linkage 有效；
- [ ] unknowns 不伪造；
- [ ] balance status 正确；
- [ ] atom source/sink 明确；
- [ ] formal/mechanistic 分离；
- [ ] donor assumptions 不变成 X→Y facts。

### Eligibility/snapshot

- [ ] 8 行 eligibility matrix 实际执行；
- [ ] conditional warnings 保留；
- [ ] strict prohibited 不进入 strict index；
- [ ] quarantine 不进入 production；
- [ ] diagnostic 仍可审计；
- [ ] immutable content-addressed snapshot；
- [ ] deterministic rebuild；
- [ ] source/policy change 改变 hash；
- [ ] interrupted build invalid；
- [ ] read-only loader；
- [ ] all filter counts/reasons 完整。

### Audit/Gate

- [ ] manual audit protocol 预先冻结；
- [ ] stratified sample；
- [ ] two independent annotators；
- [ ] disagreement/adjudication；
- [ ] catastrophic errors = 0；
- [ ] P1 Gate 10/10；
- [ ] Gate anti-false-positive mutations 能失败；
- [ ] 全部 tests 零 fail/error/skip/xfail/xpass；
- [ ] P2 保持 BLOCKED；
- [ ] 未修改 final docs/ADRs 迁就实现；
- [ ] 未写 legacy source；
- [ ] 未执行未授权 git 写操作；
- [ ] 未删除用户文件。

---

## 23. 必须诚实报告的阻断状态

以下状态都比假 PASS 更正确：

```text
BLOCKED_MISSING_REAL_REACTION_SOURCE
BLOCKED_MAPPER_UNAVAILABLE
BLOCKED_DEPENDENCY_INSTALLATION
BLOCKED_REQUIRED_CASE_MISSING
BLOCKED_MANUAL_AUDIT_INCOMPLETE
BLOCKED_CATASTROPHIC_MISMATCH
BLOCKED_SNAPSHOT_NONDETERMINISTIC
```

如果被阻断：

- 完成所有仍可安全完成的 read-only 诊断；
- 提交 blocker evidence；
- 给出需要用户提供的具体输入；
- 不得构造虚假成功数据；
- 不得自行扩大权限；
- 不得进入下一阶段。

---

## 24. 最后提醒：本项目真正的科学主线

用户目标是：

```text
输入未知分子 X
→ 找结构相似 donor A
→ 读取 A 所参与的完整反应
→ 从可信 mapped lineage 得到 A→B
→ 把有证据的 transformation 应用到 X
→ 得到候选 Y
```

P1 只负责把中间最容易出错、也最关键的证据层建对：

```text
完整反应
mapping
participant roles
A→B lineage
ledger
eligibility
snapshot
audit
```

如果 P1 仍然把完整反应压成一个“最大底物—最大产物”pair，后续无论 LLM、MCP、检索或排序多复杂，都无法可靠回答 X 可以转变成什么。

因此本轮的最高优先级不是代码量，而是：

```text
不丢反应
不跨 lineage
不伪造 mapping
不误删 cofactor/小分子
不静默解 ambiguity
不让 quarantine 泄漏
所有结果可追溯、可重放、可审计
```

只有 P1 Gate 经 ChatGPT 只读审核正式接受后，才允许进入 P2。
