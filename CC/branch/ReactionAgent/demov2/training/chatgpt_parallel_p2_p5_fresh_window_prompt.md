# ChatGPT → Qwen 新窗口零上下文启动提示词：四 Agent 并行推进 P2–P5

> **用途：** 将本文件完整交给一个没有任何历史聊天记忆的新 Qwen 窗口  
> **主窗口角色：** Qwen Orchestrator / Integrator  
> **工作团队：** 四个并行 worker agents  
> **项目目录：** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`  
> **工作原则：** 并行开发、顺序集成验收；真实证据优先；fixture 与 real evidence 绝对隔离；上游缺失则 fail-closed  
> **最终审核：** ChatGPT read-only audit  
> **当前日期背景：** 2026-07-30；但所有状态必须以本地磁盘重新核验为准

---

## 0. 先理解你的身份和任务

你是一个新开的 Qwen 主窗口，没有之前对话记忆。

你必须：

1. 把自己当作 orchestrator/integrator，而不是第五个随意写代码的 worker；
2. 阅读本提示词列出的全部权威文件；
3. 核验仓库当前真实状态，不能假设 P1 未开始；
4. 创建四个逻辑角色明确、文件所有权隔离的 worker agents；
5. 并行推进 P2–P5 的可独立工作包；
6. 对正式集成和 Gate 继续遵守 P1 → P2 → P3 → P4 → P5 的依赖顺序；
7. 不得用 synthetic fixture 或 schema skeleton 冒充真实阶段完成；
8. 最终将统一的、可审计的提交材料交给 ChatGPT。

本任务的核心口径：

```text
允许并行开发 P2–P5，
不允许并行伪造 P2–P5 的完成状态。
```

---

## 1. 项目根路径

先执行只读确认：

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
pwd
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git log -1 --oneline
git status --short
```

预期项目目录：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
```

预期 Git repository root：

```text
/Volumes/CC/Enzyme_Agent/depending
```

不要因为 Git root 位于更上层，就扩大修改范围。

所有新实现仍必须限制在：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
```

legacy 路径只读：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/benchmark
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/core
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/reports
/Volumes/CC/Enzyme_Agent/depending/data
```

---

## 2. 当前已知状态：必须重新核验，不能盲信

本提示词生成时，本地磁盘状态如下。

### 2.1 P0

```text
P0 contract freeze：ChatGPT 第四轮已接受
P0 contract tests：290 passed
P0 Gate：10/10 PASS
ADRs：6 份 Approved
P1：已授权
```

### 2.2 P1 当前进度

P1 已经开始，不得从零重做。

当前 Git recent commits 包含：

```text
d47d83b  P1 Task 0 Preflight
02d90bc  P1-T1 Package bootstrap
4cbdd79  P1-T1 security fixes
429ad72  P1-T2 Strict domain schemas
befc419  P1-T2 fixes
d3c7761  P1-T3 Legacy lineage audit
2371d30  P1-T4 Atom-mapping adapter
```

本提示词生成时的最新提交：

```text
2371d30 feat(p1): Task 4 T4 Atom-mapping adapter — UNIT_CONTRACT_COMPLETE/INTEGRATION_BLOCKED
```

### 2.3 P1 checkpoint

```text
Preflight：BLOCKED
P1-T1：完成 package/config/hash/provenance/lock 的离线部分
P1-T2：完成 strict domain schema 的当前范围
P1-T3：PARTIAL；真实数据 audit 被阻断
P1-T4：UNIT_CONTRACT_COMPLETE / INTEGRATION_BLOCKED
P1-T5–T11：尚未完成
```

### 2.4 当前 blockers

```text
rdkit_absent
real_reaction_source_not_confirmed
required_case_missing
real atom mapper integration unavailable
second independent annotator unavailable
```

当前 `.venv` 已知：

```text
Python 3.11.15
Pydantic 2.13.4
pytest 9.1.1
rdkit absent
numpy absent
networkx absent
scipy absent
rxnmapper absent
rxn4chemistry absent
```

### 2.5 当前测试

本提示词生成时，独立运行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  tests/contracts tests/p1 \
  -q -p no:cacheprovider -ra
```

结果：

```text
420 passed
```

其中：

```text
P0 contracts = 290
P1 tests = 130
```

### 2.6 当前工作树

本提示词生成时，`demov2` 内存在未提交的：

```text
reports/p0/P0_GATE_REPORT.md
reports/p0/P0_GATE_REPORT.json
```

它们可能只是 Gate 重跑生成的时间戳/报告变化。

规则：

- 不得覆盖、恢复或提交这些变化；
- 先读取 diff 并记录归属；
- 它们不属于 P2–P5 worker 的文件所有权；
- 如果需要清理或归档，先向用户请求；
- 不得使用 `git checkout --`、`git reset` 或删除来“弄干净”。

### 2.7 第一条硬规则

上面所有状态都必须重新核验。

如果磁盘状态不同：

```text
以磁盘为准
→ 写入 current-state audit
→ 不得静默使用本提示词中的旧数字
```

---

## 3. 必须完整阅读的文件

不得只读标题或摘要。

### 3.1 三份唯一 final authority

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_design.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_plan.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_discussion.md
```

重点章节：

```text
final_design：
  system objective
  complete reaction representation
  COFACTORS
  Evidence Snapshot
  Atom-Mapping Adapter
  Fragment-Lineage Graph
  Dual Ledgers
  Eligibility
  Retrieval
  Evidence/ranking/abstention
  benchmark/evaluation

final_plan：
  §4 P1
  §5 P2
  §6 P3
  §7 P4
  §8 P5
  P1–P5 Gate
```

### 3.2 六份 ADR

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0001-authority-and-scope.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0002-hypothesis-lanes.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0003-ledger-and-source-semantics.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0004-partial-eligibility.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0005-scientific-decision-authority.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0006-mcp-side-effects.md
```

### 3.3 P1 完整执行提示词

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/chatgpt_p1_train.md
```

这是 P1-T1–T11 和 P1 Gate 的完整约束。

P2–P5 worker 不能绕过其中冻结的：

```text
snapshot
mapping
lineage
participant roles
dual ledgers
eligibility/quarantine
manual audit
```

### 3.4 P0 审核证据

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/SUBMISSION_TO_CHATGPT_ROUND_4.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/V4_REMEDIATION_WORKLOG.md
```

### 3.5 P1 当前证据

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_BASELINE.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_BASELINE.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_PREFLIGHT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_PREFLIGHT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_T1_PACKAGE_BOOTSTRAP.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_T2_DOMAIN_SCHEMAS.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_T3_LEGACY_AUDIT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_T4_MAPPING_ADAPTER.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/mapping_integration_sample.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/data_audit/legacy_lineage_audit.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/data_audit/legacy_lineage_audit.json
```

### 3.6 当前实现

完整阅读：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/pyproject.toml
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/requirements.lock.txt
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/README.md

/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/config.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/hashing.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/provenance.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/mapping/base.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/mapping/adapter.py

/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/common.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/mapping.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/lineage.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/ledger.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/hypothesis.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/candidate.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/result.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/p1_entities.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/__init__.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/policies/partial_eligibility.py
```

### 3.7 当前测试和 Gate

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/contracts/
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/fixtures/p1/
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p0_gate.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/p1_preflight.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/legacy_lineage_audit.py
```

### 3.8 Legacy 只读参考

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/benchmark/canonical_identity.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/benchmark/
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/core/
```

重点：

```text
canonical_identity.py:60–77   pick_main
canonical_identity.py:96–128  COFACTORS
canonical_identity.py:131–157 _pick_transformed
canonical_identity.py:161–185 transformed_pair
```

这些是 audit target，不是 canonical truth。

---

## 4. 必读后的第一份产出：Current State Audit

主窗口先创建：

```text
reports/integration/current_state_audit.md
reports/integration/current_state_audit.json
```

必须记录：

```text
current commit
current branch
dirty files
P0 test stats
P1 test stats
P0 Gate result
Preflight verdict
P1 T1/T2/T3/T4 verdict
dependency availability
real data availability
mapper availability
proline/2OG case availability
manual annotator availability
safe-to-parallelize verdict
```

必须重新运行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  tests/contracts tests/p1 \
  -q -p no:cacheprovider -ra

.venv/bin/python scripts/run_p0_gate.py
```

注意：

`run_p0_gate.py` 会重写 P0 reports。

为了避免污染正式工作树，优先在临时只读副本中运行 Gate；如果在正式目录运行，必须明确记录报告变化，不能偷偷提交。

预期当前回归基线：

```text
420 passed
P0 Gate 10/10
```

如不一致，停止并调查，不能继续创建 worker implementation。

---

## 5. 当前 Preflight 已完成，但仍需复核

不要重新声称“P1 未开始”。

当前 Preflight 报告的主要发现：

```text
status = BLOCKED
rdkit_absent
real_reaction_source_not_confirmed
required_case_missing
```

还发现：

```text
/Volumes/CC/Enzyme_Agent/depending/data/rxn2enzyme_positives.pkl
```

大约包含 3601 个 reaction SMILES → enzyme lists 映射。

但它当前：

- 未经用户确认是 P1 的真实完整反应数据源；
- 不包含已验证的完整 RHEA/BRENDA/MetaCyc provenance；
- 没有确认 stoichiometry/participant roles；
- 不得自动升级为 canonical source；
- 不得用于 P1/P2–P5 正式 Gate PASS。

当前 required case：

```text
2-oxoglutarate + proline + O2
→ succinate + hydroxyproline + CO2
```

尚未绑定真实 source record。

因此：

```text
四个 P2–P5 agents 可以进行 offline-safe 开发，
但 real integration 和正式 Gate 继续 BLOCKED。
```

---

## 6. 用户授予的并行边界

允许四个 agent 并行推进 P2–P5，但采用：

```text
并行开发
顺序集成验收
```

不得把 P2–P5 当作四个无依赖项目。

当前允许四个 agent 并行完成：

- design；
- writing-plans；
- frozen interfaces proposal；
- stage-local schemas；
- pure functions；
- synthetic/curated fixtures；
- contract tests；
- Gate skeletons；
- anti-false-positive mutation tests；
- offline-safe reference implementations；
- integration blockers 的 typed handling。

当前禁止：

- fixture 冒充 real evidence；
- 声称 P2/P3/P4/P5 Gate PASS；
- 提前生成或发布真实 performance；
- 修改 P0/final docs/ADRs 来适配代码；
- 多 agent 修改同一共享文件；
- 使用不同的同义 schema；
- 未经授权安装依赖；
- 未经授权联网；
- 写 legacy source；
- 把 `rxn2enzyme_positives.pkl` 自动当成 confirmed source；
- 用 fake mapper 输出做真实 lineage；
- 用单一 agent 复制两份 annotation 冒充 double annotation；
- 进入 P6；
- 宣称系统已经可靠预测 X→Y。

---

## 7. 四 Agent 团队结构

主 Qwen 窗口是：

```text
Integrator / Project Manager
```

创建四个 worker agents：

```text
Agent A — P2 Truth / Isolation / Funnel
Agent B — P3 Strict Kernel
Agent C — P4 Evidence / Ranking / Abstention
Agent D — P5 Benchmark / Leakage / Reporting
```

如果工具并发上限无法让四个 worker 与主窗口同时运行：

- 保留四个逻辑角色；
- 分两波调度；
- 不得合并角色语义；
- 每个角色仍提交独立报告。

禁止 worker 再无限递归创建子团队。需要额外 agent 必须由主窗口记录理由。

---

## 8. Git/worktree 安全规则

用户希望每个 agent 使用独立 worktree/branch，但必须先解决真实 Git 状态。

### 8.1 先检查 baseline 是否可继承

确认当前 P1 文件已经存在于 HEAD。

本提示词生成时：

```text
HEAD 已包含 P1 T0–T4 commits
```

因此从当前 HEAD 创建 worktree 应能继承 P1 T0–T4。

但正式工作树存在未提交 P0 report changes，它们不会自动进入新 worktree。

这不是问题，因为 P2–P5 worker 不拥有 P0 reports。

### 8.2 禁止处理用户无关 dirty files

不得：

```text
reset
checkout
stash unknown user changes
delete untracked files
clean repository
```

### 8.3 Branch/worktree

为每个 worker 使用独立本地分支/worktree。

建议逻辑名称：

```text
parallel/p2-truth-isolation
parallel/p3-strict-kernel
parallel/p4-evidence-decision
parallel/p5-benchmark
```

如果当前工具或仓库策略要求其他前缀，遵循本地规则，但在 manifest 中记录映射。

### 8.4 Commit/push

- 创建本地 worktree/branch 属于本次并行任务的正常步骤；
- 不得 push；
- 不得创建 PR；
- 如果用户没有明确授权 local commits，先请求；
- 未授权时，各 worker 只提交 patch/diff bundle 和报告，由 integrator 保留；
- 不得为了方便擅自提交用户的其他 dirty changes。

---

## 9. 文件所有权：避免四 Agent 冲突

### 9.1 Integrator 独占

只有主窗口可以修改：

```text
reaction_agent/schemas/__init__.py
reaction_agent/__init__.py
pyproject.toml
requirements.lock.txt
README.md
plan/final_design.md          # 实际上禁止修改
plan/final_plan.md            # 实际上禁止修改
plan/final_discussion.md      # 实际上禁止修改
docs/decisions/*
reports/integration/*
```

P0 frozen schema 文件原则上只读：

```text
reaction_agent/schemas/common.py
reaction_agent/schemas/evidence.py
reaction_agent/schemas/mapping.py
reaction_agent/schemas/lineage.py
reaction_agent/schemas/ledger.py
reaction_agent/schemas/hypothesis.py
reaction_agent/schemas/candidate.py
reaction_agent/schemas/result.py
```

如 worker 需要新增字段：

```text
先写 schema_delta_proposal.md
→ integrator 审核
→ 优先新增 stage-local model
→ 不得静默改变 P0 语义
```

### 9.2 Agent A 独占

```text
reaction_agent/evaluation/
tests/p2/
tests/fixtures/p2/
scripts/run_p2_gate.py
reports/p2/
proposals/p2/
```

### 9.3 Agent B 独占

```text
reaction_agent/kernel/
tests/p3/
tests/fixtures/p3/
scripts/run_p3_gate.py
reports/p3/
proposals/p3/
```

### 9.4 Agent C 独占

```text
reaction_agent/decision/
tests/p4/
tests/fixtures/p4/
scripts/run_p4_gate.py
reports/p4/
proposals/p4/
```

### 9.5 Agent D 独占

```text
reaction_agent/benchmarking/
tests/p5/
tests/fixtures/p5/
scripts/run_p5_gate.py
reports/p5/
proposals/p5/
```

### 9.6 Shared fixtures

不得让四个 agent 同时编辑一个共享 fixture 文件。

跨阶段 fixture：

```text
由 integrator 生成版本化 fixture bundle
→ workers 只读消费
```

建议：

```text
tests/fixtures/integration/v1/
```

但该目录仅由 integrator 写。

---

## 10. 必须先形成的五份共享文档

四个 worker 开始写实现前，主窗口必须创建：

```text
plan/parallel_p2_p5_team_design.md
plan/parallel_p2_p5_writing_plan.md
reports/integration/cross_stage_interface_manifest.json
reports/integration/dependency_matrix.md
reports/integration/merge_ownership.md
```

并持续维护：

```text
reports/integration/fixture_vs_real_evidence_manifest.json
reports/integration/integration_worklog.md
```

### 10.1 Team design

必须写：

```text
roles
scope
inputs/outputs
stage dependencies
file ownership
review boundaries
conflict resolution
merge authority
stop conditions
Gate order
```

### 10.2 Writing plan

每个 task 必须有：

```text
preconditions
allowed files
forbidden files
RED tests
minimal implementation
GREEN tests
artifacts
blocked behavior
checkpoint
integration consumer
```

### 10.3 Cross-stage interface manifest

机器可读记录：

```text
interface name
semantic version
producer
consumers
authoritative schema/module
required fields
stable ID contract
content hash contract
provenance contract
fixture status
real evidence status
blocked dependencies
```

至少包含：

```text
SnapshotRecord
SnapshotManifest
ReactionEvidence
ReactionParticipant
MappingReport
ResolvedTransformedLineage
LineageResolution
SourceReactionLedger
CandidateAnalogyLedger
EligibilityDecision
QuarantineRecord
MultiAnswerTruth
FoldView
StageFunnel
TransformationHypothesis
SiteHypothesis
Candidate
PredictionResult
RunManifest
BenchmarkExample
SplitManifest
```

### 10.4 Canonical IDs

必须统一：

```text
snapshot_id
reaction_id
source_record_id
participant_id
lineage_id
transformation_id
site_id
candidate_id
source_ledger_id
candidate_ledger_id
evidence_id
run_id
fold_id
benchmark_example_id
```

四个 agent 不能各自发明 ID。

### 10.5 Dependency matrix

明确：

```text
P1 snapshot/lineage/ledger/eligibility
  → P2/P3/P5

P2 truth/fold views
  → P3 evaluation isolation
  → P4 calibration/evaluation
  → P5 benchmark

P3 candidate/trace
  → P4 ranking/abstention
  → P5 performance

P1–P4
  → P5 full benchmark
```

### 10.6 Fixture vs real manifest

每个 artifact 必须标：

```text
synthetic
curated
real-source-derived
real-source-confirmed
```

并包含：

```text
source/path
hash
license/provenance
allowed uses
forbidden uses
Gate eligibility
```

默认规则：

```text
synthetic fixture Gate eligibility = unit only
```

---

## 11. Agent A Brief：P2 Truth / Isolation / Funnel

Agent A 必读：

```text
final_plan.md §5 P2
final_design evaluation/truth/fold sections
P1 snapshot/lineage/eligibility schemas
cross_stage_interface_manifest.json
fixture_vs_real_evidence_manifest.json
```

### 11.1 现在允许完成

```text
MultiAnswerTruth stage-local schema proposal
allowed_product_set logic
tautomer/salt/neutralization equivalence interfaces
stereo-sensitive/agnostic truth
multi-product truth
annotation completeness
FoldView
train/validation/test access guards
test label hiding
cache key includes fold
StageFunnel
primary failure reasons
baseline protocol
non-oracle pilot protocol
P2 Gate skeleton
anti-leakage mutation tests
```

### 11.2 当前不得声称完成

```text
20–50 real audited mini snapshot
real leakage=0
real multi-answer annotation complete
automatic donor pilot
P2 Gate PASS
```

原因：

```text
P1 real snapshot unavailable
P1 real source unavailable
P1 real mapping/lineage unavailable
```

### 11.3 必须测试

至少：

```text
test ID inaccessible from train view
test label inaccessible to retriever/scorer
cache key includes fold and snapshot
multi-answer accepts equivalent valid Y
stereo-sensitive case rejects wrong stereo
incomplete annotation typed
all X denominator retained
hard cases not dropped
oracle donor explicitly separated
fixture cannot be marked real
Gate reports upstream-blocked
```

### 11.4 Agent A 输出

```text
reports/p2/P2_AGENT_REPORT.md
reports/p2/P2_AGENT_REPORT.json
proposals/p2/schema_delta_proposal.md
proposals/p2/interface_consumption.md
```

允许最终状态：

```text
OFFLINE_CONTRACT_COMPLETE
UPSTREAM_P1_BLOCKED
P2_GATE_NOT_RUN_AS_PASS
```

---

## 12. Agent B Brief：P3 Strict Kernel

Agent B 必读：

```text
final_plan.md §6 P3
final_design kernel/retrieval/transformation/site/generation sections
P1 MappingReport/Lineage/Ledger/Eligibility
P2 proposed FoldView/Truth/Funnel
cross_stage_interface_manifest.json
```

### 12.1 现在允许完成

不依赖真实 source 的纯模块：

```text
query normalization interfaces
invalid input handling
equivalent SMILES contract
identity hash contract
distinct-donor retrieval interface
complete reaction loader interface
strict transform typed interface
conditioned site matcher pure logic
stable site IDs
symmetry dedup contract
deterministic graph-edit compiler
molecule validation interface
canonical candidate store
generation path aggregation
typed failures
deterministic predictor state machine skeleton
P3 Gate skeleton
mutation tests
```

### 12.2 依赖缺失时不得伪造

当前没有 RDKit。

因此：

- 可以用明确标注的 graph fixture 测试纯 edit semantics；
- 不得称其为真实 molecule sanitization；
- 不得用字符串替换冒充 chemistry graph edit；
- 不得输出真实 valid molecule rate；
- 不得用 FakeAtomMapper 创建 real lineage；
- 不得声明 X-only end-to-end 成功。

### 12.3 必须测试

至少：

```text
invalid input typed
normalization deterministic
atom-order-independent IDs（fixture contract）
duplicate reaction rows do not crowd donor interface
quarantine exclusion interface
fold ID required
deterministic tie behavior
complete reaction loader refuses A/B-only record
partial-map strict rejection
MCS-only strict rejection
site symmetry dedup
no compatible site typed
invalid edit typed
candidate evidence merge without loss
fake evidence cannot enter real mode
P3 Gate reports P1/P2 upstream blocked
```

### 12.4 Agent B 输出

```text
reports/p3/P3_AGENT_REPORT.md
reports/p3/P3_AGENT_REPORT.json
proposals/p3/schema_delta_proposal.md
proposals/p3/interface_consumption.md
```

允许最终状态：

```text
PURE_KERNEL_CONTRACT_COMPLETE
CHEMISTRY_INTEGRATION_BLOCKED
P1_P2_UPSTREAM_BLOCKED
P3_GATE_NOT_RUN_AS_PASS
```

---

## 13. Agent C Brief：P4 Evidence / Ranking / Abstention

Agent C 必读：

```text
final_plan.md §7 P4
final_design evidence/ranking/applicability/abstention/result sections
ADR-0005
P0 candidate/result schemas
P3 candidate/trace proposal
cross_stage_interface_manifest.json
```

### 13.1 现在允许完成

```text
IndependentEvidenceIdentity
mirror/publication/reaction dedup contract
SupportAggregation interface
feature→evidence IDs trace contract
CounterEvidence typed vocabulary
absence-is-not-negative rule
BaselineRanker pure feature vector
versioned weight config
not-probability labels
Applicability enum logic
TypedAbstention precedence
PredictionResult invariants
immutable run/trace/manifest
request/result hash
replay contract
P4 Gate skeleton
mutation tests
```

### 13.2 当前不得声称完成

```text
real support aggregation
real ranking calibration
real ablation
real selective metrics
real top-K
P4 Gate PASS
```

原因：

```text
P3 real candidates/traces unavailable
P2 real evaluation truth unavailable
```

### 13.3 必须测试

至少：

```text
duplicate mirror does not add support
same publication does not fake independence
database absence not counterevidence
missing second enzyme not negative
all feature values cite evidence IDs
ranking deterministic
rank score not exposed as probability
applicability structural only
abstention precedence exact
failed infrastructure separate from abstention
completed/predicted requires candidate
abstained requires zero candidates + reason
run immutable
same request/config/snapshot → same result hash
fixture evidence cannot be labeled real
P4 Gate reports P2/P3 upstream blocked
```

### 13.4 Agent C 输出

```text
reports/p4/P4_AGENT_REPORT.md
reports/p4/P4_AGENT_REPORT.json
proposals/p4/schema_delta_proposal.md
proposals/p4/interface_consumption.md
```

允许最终状态：

```text
DECISION_CONTRACT_COMPLETE
RANKING_INTEGRATION_BLOCKED
P2_P3_UPSTREAM_BLOCKED
P4_GATE_NOT_RUN_AS_PASS
```

---

## 14. Agent D Brief：P5 Benchmark / Leakage / Reporting

Agent D 必读：

```text
final_plan.md §8 P5
final_design benchmark/evaluation sections
P1 snapshot/provenance
P2 truth/fold/funnel proposal
P3 candidate/trace proposal
P4 prediction/ranking/abstention proposal
cross_stage_interface_manifest.json
```

### 14.1 现在允许完成

```text
BenchmarkExample schema proposal
SplitManifest
exact-X split
scaffold split interface
transformation-family split interface
source split interface
time split unavailable status
OOD challenge interface
identity leakage guards
baseline adapter interface
metric implementations
coverage/risk metrics
confidence interval utilities
six-layer report schema
all N/denominators/reasons
performance gate template
P5 Gate skeleton
mutation tests
```

### 14.2 当前不得声称完成

```text
full production snapshot
rebuilt real examples
actual leakage-free splits
legacy baseline results
real six-layer reports
formal KPI values
go/no-go for service
P5 Gate PASS
```

原因：

```text
P1–P4 real outputs unavailable
```

### 14.3 必须测试

至少：

```text
exact X leakage detected
same reaction/lineage leakage detected
train/test source overlap rule
time split reports unavailable when provenance missing
all filters have counts/reasons
all X denominator preserved
multi-answer metrics
coverage metrics
risk at coverage
abstention-aware metrics
baseline adapter same split/snapshot guard
oracle baseline labeled diagnostic only
fixture metrics cannot be labeled real
formal KPIs cannot freeze before real results
P5 Gate reports P1–P4 upstream blocked
```

### 14.4 Agent D 输出

```text
reports/p5/P5_AGENT_REPORT.md
reports/p5/P5_AGENT_REPORT.json
proposals/p5/schema_delta_proposal.md
proposals/p5/interface_consumption.md
```

允许最终状态：

```text
BENCHMARK_HARNESS_CONTRACT_COMPLETE
REAL_BENCHMARK_BLOCKED
P1_P2_P3_P4_UPSTREAM_BLOCKED
P5_GATE_NOT_RUN_AS_PASS
```

---

## 15. 每个 Worker 的统一执行协议

每个 agent 必须：

### 15.1 READ

- 完整读 role-specific 文件；
- 读 cross-stage manifest；
- 读 ownership；
- 读已有 P0/P1 schema；
- 不得凭记忆发明字段。

### 15.2 ASSUMPTIONS

先在报告中写：

```text
assumptions
known blockers
real vs fixture boundary
upstream interfaces consumed
shared files needed
```

### 15.3 RED

先写真实失败测试。

RED 必须因为功能不存在或不满足合同，而不是：

```text
测试语法错误
导入路径错误
故意 assert False
```

### 15.4 Minimal implementation

- 只实现本 agent scope；
- 不建设 speculative framework；
- 不顺手重构别人的代码；
- 每个改动可追溯到测试/合同；
- 没有真实依赖就实现 typed blocked behavior。

### 15.5 GREEN

运行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  <agent-owned-tests> \
  -q -p no:cacheprovider -ra
```

### 15.6 Full regression

每个 agent 提交前运行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  tests/contracts tests/p1 <agent-owned-tests> \
  -q -p no:cacheprovider -ra
```

要求：

```text
fail=0
error=0
skip=0
xfail=0
xpass=0
```

### 15.7 Report

每个报告必须包含：

```text
commit/base
changed files
RED evidence
GREEN evidence
full regression
interfaces consumed
interfaces proposed
fixture artifacts
real artifacts
blocked items
deviations
risks
stage status
```

---

## 16. Gate skeleton 的严格语义

四个 agent 可以写 Gate skeleton，但 Gate 必须区分：

```text
contract/unit checks passed
upstream integration unavailable
real evidence unavailable
formal stage Gate passed
```

不得把：

```text
unit contract passed
```

输出为：

```text
P2/P3/P4/P5 Gate PASS
```

建议 stage status：

```text
OFFLINE_CONTRACT_COMPLETE
UPSTREAM_BLOCKED
INTEGRATION_BLOCKED
NOT_READY_FOR_CHATGPT_STAGE_AUDIT
```

Gate 在 upstream-blocked 时：

- 可以用 exit code 2 表示 BLOCKED；
- 或非零 typed status；
- 不能 exit 0 + PASS；
- 不能把 `NotImplementedError` 吞掉后报绿；
- 不能用 skip/xfail；
- 不能只检查文件存在。

### 16.1 Gate anti-false-positive

每个 agent 在临时副本中验证至少一个 mutation。

P2：

```text
允许 test label 进入 train view → Gate fail
```

P3：

```text
允许 quarantine donor / A-B-only record → Gate fail
```

P4：

```text
重复 mirror 增加 support / rank label probability → Gate fail
```

P5：

```text
制造 train/test identity leakage / 丢 denominator → Gate fail
```

Mutation 不得污染正式工作树。

---

## 17. 并行开发的阶段波次

### Wave 0：状态核验

主窗口：

```text
READ
current-state audit
tests
P0 Gate isolated run
dirty-worktree assessment
```

没有通过 Wave 0，不创建实现 workers。

### Wave 1：团队设计和共享接口

四个 agents 可以并行提供 design proposal，但：

- 不编辑共享 schema；
- 主窗口汇总；
- 形成五份共享文档；
- 冻结 v1 offline interface manifest。

### Wave 2：Offline-safe 并行实现

四个 agents 在各自 worktree：

```text
schemas/proposals
pure functions
fixtures
contract tests
Gate skeleton
mutation tests
reports
```

### Wave 3：主窗口集成

只集成：

- 不改变 P0/P1 frozen semantics；
- tests 全绿；
- fixture/real 标注完整；
- 无 shared-file 冲突；
- 没有越过 upstream blockers；
- stage status 诚实。

### Wave 4：等待真实 P1 unblock

当前必须等待用户决定：

```text
真实完整 reaction source
RDKit/mapper 安装
proline/2OG source record
第二 annotator
```

在这些未解决前，不得进入 real P2–P5 integration。

### Wave 5：正式顺序 Gate

只有 P1 正式通过后：

```text
P2 real integration + Gate
→ P3 real integration + Gate
→ P4 real integration + Gate
→ P5 real integration + Gate
```

下游开发可以准备，但正式验收顺序不能改变。

---

## 18. Integrator 合并规则

### 18.1 Merge checklist

每个 agent 合并前：

- [ ] 文件只在 ownership 范围；
- [ ] 没有改 final docs/ADRs；
- [ ] 没有改 P0 frozen schema semantics；
- [ ] schema delta 有 proposal；
- [ ] fixture/real manifest 已更新；
- [ ] RED/GREEN 有证据；
- [ ] full regression 通过；
- [ ] stage status 没有假 PASS；
- [ ] 无 skip/xfail；
- [ ] blocker 明确。

### 18.2 每次合并后

运行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  tests -q -p no:cacheprovider -ra
```

并在隔离副本运行：

```bash
.venv/bin/python scripts/run_p0_gate.py
```

然后运行所有已经存在的 stage tests。

### 18.3 冲突裁决

优先级：

```text
final docs
→ ADRs
→ P0 frozen contracts
→ accepted P1 interfaces
→ cross-stage manifest
→ stage-local proposal
```

不得用“哪个 agent 代码更多”裁决。

---

## 19. 真实数据和依赖的 stop conditions

以下任何情况需要用户输入：

```text
需要安装 RDKit/NumPy/NetworkX/SciPy/rxnmapper
需要联网
需要确认 rxn2enzyme_positives.pkl 是否可作 source
需要 RHEA/BRENDA/MetaCyc path
需要 proline/2OG source record
需要人工第二 annotator
需要写出 demov2
需要修改 frozen schema
需要 local commit/push 未获授权
```

向用户报告时必须具体：

```text
需要什么
为什么需要
阻断哪个 stage/task
不提供时还能完成什么
提供后的验证命令
```

不得只说：

```text
缺数据，请提供。
```

---

## 20. 当前科学边界

用户最终目标：

```text
输入未知分子 X
→ 检索结构相似 donor A
→ 加载 A 的完整反应
→ 从 mapped fragment-lineage 读取真实 A→B
→ 将 transformation 应用到 X
→ 得到候选 Y
```

任何阶段都必须保持：

```text
complete reaction
not independent side picking
COFACTORS prior, not deletion
formal mapping ≠ mechanism
lineage ambiguity not silently resolved
quarantine not production
donor assumptions not X→Y facts
all IDs traceable
all filters counted
```

---

## 21. 本轮允许的最终产出边界

在当前 blockers 未解决的情况下，本轮最多允许交付：

```text
四 Agent team design
完整 writing plans
cross-stage interface manifest v1
dependency matrix
merge ownership
fixture-vs-real manifest
integration worklog
P2 offline contracts/tests/Gate skeleton
P3 pure kernel contracts/tests/Gate skeleton
P4 decision contracts/tests/Gate skeleton
P5 benchmark harness contracts/tests/Gate skeleton
四个 agent reports
统一集成测试
诚实的 upstream-blocked statuses
```

本轮不允许交付：

```text
P2 Gate PASS
P3 Gate PASS
P4 Gate PASS
P5 Gate PASS
真实 top-K
真实性能
P6
service go/no-go
```

---

## 22. 最终提交给 ChatGPT 的材料

主窗口最终生成：

```text
reports/integration/SUBMISSION_TO_CHATGPT_P2_P5_PARALLEL.md
reports/integration/current_state_audit.md
reports/integration/current_state_audit.json
reports/integration/cross_stage_interface_manifest.json
reports/integration/dependency_matrix.md
reports/integration/merge_ownership.md
reports/integration/fixture_vs_real_evidence_manifest.json
reports/integration/integration_worklog.md

reports/p2/P2_AGENT_REPORT.md
reports/p2/P2_AGENT_REPORT.json
reports/p3/P3_AGENT_REPORT.md
reports/p3/P3_AGENT_REPORT.json
reports/p4/P4_AGENT_REPORT.md
reports/p4/P4_AGENT_REPORT.json
reports/p5/P5_AGENT_REPORT.md
reports/p5/P5_AGENT_REPORT.json
```

提交封面必须包含：

1. 当前 commit/branch/dirty state；
2. 四个 agents 的身份和 worktree；
3. 每个 agent 的文件所有权；
4. shared interface version；
5. changed files；
6. P0/P1 baseline 和最终 tests；
7. 每个 agent targeted tests；
8. 合并后全部 tests；
9. P0 Gate 隔离复跑；
10. 每个 stage 的 honest status；
11. upstream blockers；
12. fixture/real evidence counts；
13. mutation results；
14. unresolved schema proposals；
15. merge conflicts及裁决；
16. 未安装/未联网声明；
17. 未写 legacy source；
18. P6 status。

只允许写：

```text
READY_FOR_CHATGPT_PARALLEL_OFFLINE_AUDIT
P1 REAL INTEGRATION BLOCKED
P2–P5 FORMAL GATES NOT PASSED
P6 BLOCKED
```

不得写：

```text
P2–P5 completed
P2–P5 approved
ready for P6
system predicts X→Y reliably
```

---

## 23. 启动顺序：新窗口收到本文件后立即执行

### Step 1

完整阅读 §3 文件。

### Step 2

生成 current-state audit，重跑 420-test baseline 和隔离 P0 Gate。

### Step 3

读取 dirty diff，确认不覆盖 P0 report changes。

### Step 4

创建团队 design、writing plan、interface manifest、dependency matrix、ownership。

### Step 5

先让四个 agents 各自提交只读 design/interface proposal。

### Step 6

由 integrator 解决同义 schema/ID/ownership 冲突，冻结 offline interface v1。

### Step 7

在独立 worktrees 启动四条 offline-safe implementation。

### Step 8

收集每个 agent RED/GREEN/full-regression/report。

### Step 9

按 merge checklist 顺序集成，每次合并后全量回归。

### Step 10

生成统一提交材料，停止并交给 ChatGPT 审核。

### Step 11

未获得用户对真实数据、依赖、mapper 和 annotator 的授权前：

```text
不得进入 real integration
不得宣布 stage Gate PASS
不得进入 P6
```

---

## 24. 一句话最终指令

```text
用四个 agent 并行把 P2–P5 的离线合同、纯模块、测试和 Gate 骨架做扎实；
以当前 P1 T0–T4 为真实起点；
所有真实化学、真实数据、真实性能继续被 P1 blockers 阻断；
四条线并行开发，但只按 P2→P3→P4→P5 顺序做正式集成验收；
最终统一交给 ChatGPT 只读审核。
```
