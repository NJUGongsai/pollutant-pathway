# P1 严格整改任务书（ChatGPT Read-Only Audit Round 2）

> **用途：** 将本文件完整交给负责整改的 coding agent。  
> **项目根目录：** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`  
> **审核结论：** `CHATGPT_P1_AUDIT_VERDICT = REJECTED_REMEDIATION_REQUIRED`  
> **当前授权边界：** 只整改 P1；不得进入 P2 业务实现，不得宣称 P1 已通过。  
> **核心原则：** 修复实现和 Gate，不得通过修改冻结设计、ADR 或手工篡改 evidence 状态来迁就现有代码。

---

## 0. 你现在的角色

你是 P1 remediation implementation agent。

你需要修复 ChatGPT 第二轮只读审核发现的实现缺陷和 Gate 假阳性问题，并提交一套可复核、可反作弊、不会把 fixture 冒充真实证据的整改结果。

本轮不是让你：

- 重写最终设计；
- 进入 P2/P3/P4/P5；
- 安装未授权依赖；
- 手工把 `BLOCKED` 改为 `PASS`；
- 只修改报告或测试来适配错误实现；
- 用 synthetic fixture 代替真实 reaction source、真实 mapper 或真实 manual audit。

本轮完成后，若真实 source、真实 mapper、独立 annotator 仍未就绪，正确结果仍然可以是：

```text
P1 IMPLEMENTATION REMEDIATION COMPLETE
P1 SCIENTIFIC INTEGRATION BLOCKED
P2 BLOCKED
```

不得为了得到 10/10 而伪造证据。

---

## 1. 开工前必须完整阅读

按顺序完整阅读以下文件，不得只 grep 摘要：

### 1.1 冻结设计与实施约束

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_design.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_plan.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/chatgpt_p1_train.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/superpowers/specs/2026-07-29-p1-multi-agent-team-design.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/superpowers/plans/2026-07-29-p1-data-foundation.md
```

### 1.2 当前提交与证据

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_PREFLIGHT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_PREFLIGHT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/data_audit/legacy_lineage_audit.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/data_audit/legacy_lineage_audit.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_report.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_report.json
```

### 1.3 必须审查和整改的实现

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/loader.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/eligibility/engine.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/ledger.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/p1_entities.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/mapping/adapter.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/lineage/resolver.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_gate.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_mutations.py
```

### 1.4 必须审查和扩展的测试

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_engine.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_lineage_graph.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_mapping_adapter.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_manual_audit_contract.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_p1_gate_contract.py
```

---

## 2. 开工前保护与基线

### 2.1 先检查工作区

记录：

```text
git status --short
git log -1 --oneline
```

现有未提交修改和未跟踪文件可能属于用户或其他 agent。不得删除、覆盖、reset、clean 或擅自纳入本轮提交。

### 2.2 禁止修改的内容

除非 ChatGPT 审核任务明确要求，否则不得修改：

```text
plan/final_design.md
plan/final_plan.md
docs/decisions/ADR-*.md
tests/contracts/
reaction_agent/schemas/ 中已经冻结的 P0 语义
../benchmark/
../core/
任何 legacy source
```

允许新增 P1 专用 schema 或 validator，但不得改变 P0 已冻结字段的含义来迁就实现。

### 2.3 运行并记录基线

使用项目 `.venv`：

```bash
.venv/bin/python -m pytest tests/contracts tests/p1 -q -p no:cacheprovider -ra
.venv/bin/python scripts/run_p0_gate.py
.venv/bin/python scripts/run_p1_gate.py
```

预期当前基线：

```text
P0 Gate = 10/10 PASS
P1 tests = green
P1 Gate = BLOCKED
```

如果实际数字不同，记录真实数字，不得复制旧报告中的 `634/619/15`。ChatGPT 独立审核当前看到的是：

```text
638 passed
621 tests in G10 after excluding gate-contract file
17 gate-contract tests
```

以整改完成后的实际 collection 为最终权威。

---

## 3. 必须修复的 Critical-1：snapshot 未覆盖完整科学证据

### 3.1 已确认的缺陷

当前 `SnapshotEvidenceItem` 输入包含：

```text
ReactionEvidence
SourceReactionLedger
ResolvedTransformedLineage[]
```

但当前 `_record_content_hash()` 和 `records.jsonl` 没有覆盖或持久化：

```text
完整 participants
participant provenance
atom maps
mapping report
SourceReactionLedger
element/charge/stoichiometry ledger
resolved lineages
transformed atom maps
lineage evidence IDs
```

ChatGPT 独立探针已经确认：

```text
修改 ledger unknowns/evidence IDs             → snapshot hash 不变
修改 lineage transformed_atom_maps/evidence → snapshot hash 不变
修改 participant maps/provenance             → snapshot hash 不变
```

这是正式缺陷，不是未来优化项。

### 3.2 正确目标

snapshot 必须真正冻结：

```text
完整 ReactionEvidence
+ 完整 SourceReactionLedger（允许显式 null）
+ 完整 resolved lineages
+ eligibility decision
+ quarantine record（允许显式 null）
+ 所有内容影响版本/config
```

同一份规范化 canonical payload 必须同时用于：

1. record content hash；
2. snapshot content hash；
3. `records.jsonl` 或等价完整记录资源；
4. loader 的重新计算和 tamper verification。

禁止 builder 哈希一种精简对象、writer 写另一种对象、loader 再验证第三种对象。

### 3.3 推荐实现边界

可新增 P1 专用严格 schema，例如：

```text
SnapshotEvidencePayload
FrozenSnapshotRecord
```

它至少应包含：

```text
reaction_evidence
source_ledger
resolved_lineages
eligibility_decision
quarantine_record
record_content_hash
lane
```

要求：

- `extra="forbid"`；
- canonical serialization 稳定；
- 列表顺序中有语义的保留顺序；
- 无语义的集合/映射在哈希前规范化；
- 不把 timestamp、temp path、run ID 加入 content hash；
- mapper/resolver/ledger/policy/schema 版本必须影响 snapshot hash；
- `source_files` 不能只是 source name 下的 eligibility 摘要 hash；
- 完整 source/provenance change 必须改变 hash。

production/diagnostic/quarantine index 可以存完整记录或稳定引用，但必须：

- 每条 index entry 可唯一关联完整 frozen record；
- loader 验证 index entry 与完整 records 的 lane/decision/hash 一致；
- production index 不得包含不存在于完整 records 中的悬空引用；
- quarantine/diagnostic 记录保持可审计。

### 3.4 必须先写的 RED tests

至少新增以下测试，并先证明它们在旧实现上 RED：

```text
test_snapshot_hash_changes_when_participant_changes
test_snapshot_hash_changes_when_participant_provenance_changes
test_snapshot_hash_changes_when_mapping_report_changes
test_snapshot_hash_changes_when_mapping_pair_changes
test_snapshot_hash_changes_when_source_ledger_changes
test_snapshot_hash_changes_when_lineage_pair_changes
test_snapshot_hash_changes_when_transformed_atom_maps_change
test_snapshot_hash_changes_when_lineage_evidence_changes
test_snapshot_hash_changes_when_policy_or_content_version_changes
test_snapshot_records_persist_complete_reaction_evidence
test_snapshot_records_persist_source_ledger
test_snapshot_records_persist_resolved_lineages
test_loader_rejects_tampered_nested_participant
test_loader_rejects_tampered_mapping_report
test_loader_rejects_tampered_source_ledger
test_loader_rejects_tampered_lineage
test_index_entry_must_reference_existing_full_record
test_index_lane_must_match_full_record_decision
```

不得只断言预计算布尔值，例如：

```python
assert evidence["same_hash_3way"] is True
```

Gate/test 必须实际修改嵌套内容并重新计算 hash。

---

## 4. 必须修复的 Critical-2：不完整 mapping/source 可进入 strict production

### 4.1 已确认的缺陷

ChatGPT 已构造合法严格 schema 输入：

```text
source_completeness = "incomplete"
mapping_completeness = "failed"
balance_status = "fully_balanced_explicit_reaction"
```

当前 `decide_eligibility()` 输出：

```text
eligibility = strict_eligible
evaluation_bucket = production
required_warnings = []
```

这是 fail-open，必须修复。

### 4.2 strict eligibility 的最低交叉不变量

进入 `strict_eligible` 前至少必须验证：

```text
ledger is not None
ledger.reaction_evidence_id == reaction_evidence.reaction_id
ledger.source_completeness == "complete"
ledger.mapping_completeness == "complete"
reaction_evidence.mapping_report is not None
mapping_report.mapping_status == "fully_mapped"
mapping_report.fallback_method is None
formal assignment exists
formal assignment is not MCS/center-pair/unknown fallback
mapping_report.map_number_uniqueness is true
mapping_report.changed_atom_coverage meets strict threshold
mapping_report has no identity-critical ambiguity
lineages is not empty
all lineage participant IDs exist in the complete participant multiset
no lineage has ambiguity == "critical"
no forbidden cross-lineage pairing
no identity/balance-critical unknown
balance status and completeness fields are mutually consistent
```

不要简单写成“`unknowns` 必须为空”，因为某些非关键 unknown 可能属于 conditional/diagnostic；应建立明确 typed reason/category 或保守分类函数。

### 4.3 schema/validator 要求

禁止以下矛盾组合静默通过：

```text
mapping_completeness != complete
+ fully_balanced_explicit_reaction

source_completeness != complete
+ strict_eligible

fallback_method in {mcs, center_pair}
+ strict_eligible

mapping_failed/unmapped
+ production strict lane
```

可在以下任一层或多层实现：

- `SourceReactionLedger` model-level validator；
- eligibility engine cross-object validator；
- snapshot ingestion validator。

仅依赖 builder “正常情况下不会这样生成”不够，因为 schema 对象可以来自：

- JSON 反序列化；
- 外部 import；
- 未来真实 source adapter；
- migration；
- 手工构造；
- 旧 snapshot replay。

### 4.4 必须先写的 RED tests

至少新增：

```text
test_incomplete_source_never_strict_eligible
test_failed_mapping_never_strict_eligible
test_partial_mapping_never_strict_eligible
test_unmapped_never_strict_eligible
test_mcs_fallback_never_strict_eligible
test_center_pair_fallback_never_strict_eligible
test_missing_mapping_report_never_strict_eligible
test_ledger_reaction_id_mismatch_fails_closed
test_lineage_unknown_participant_fails_closed
test_contradictory_balance_and_mapping_state_rejected
test_incomplete_mapping_never_enters_production_index
test_direct_deserialization_cannot_bypass_strict_boundary
```

至少一个测试必须通过公开 API 构造 `SnapshotEvidenceItem`，证明坏 ledger 无法进入 snapshot production index。

---

## 5. 必须修复的 Critical-3：P1 Gate 假阳性

### 5.1 总体状态模型

当前 G03/G04/G10 会让 `BLOCKED` 覆盖同一 Gate 内的 implementation issues。

必须改为分别统计：

```text
external_blockers
implementation_failures
```

聚合规则：

```text
implementation_failures 非空
→ Gate = FAIL 或 FAIL_WITH_BLOCKERS

implementation_failures 为空 且 external_blockers 非空
→ Gate = BLOCKED

两者都为空且全部条件满足
→ Gate = PASS
```

不得继续声称：

```text
3 BLOCKED, 0 FAIL
```

如果 blocked gate 中已经发现 implementation issue。

### 5.2 G03 必须验证真实 source，而不是状态字符串

ChatGPT 已证明以下假 evidence 会让旧 G03 PASS：

```text
verdict = COMPLETE
real_reaction_source_found = true
proline source_record_found = true
total_reactions = 0
audited_reactions = 0
source_ids = []
examples = []
```

修复后必须验证：

```text
source authority/config 明确
source manifest 存在且 schema 正确
source file hash 与实际文件重新计算一致
total_reactions > 0
audited_reactions > 0
audited_reactions <= total_reactions
所有分类计数与 denominator 一致
source_ids 非空且能关联 examples
examples 来自真实 source IDs
proline/2OG 真实 record 可定位，或按冻结协议明确 quarantine/BLOCKED
legacy source hash 与 Preflight frozen hash 一致
```

若真实 source 尚未由用户确认：

```text
G03 = BLOCKED
```

不得使用 synthetic fixture 解除。

### 5.3 G04 必须执行真实 adapter

ChatGPT 已证明：只把 JSON 中：

```text
INTEGRATION_BLOCKED
```

改为：

```text
INTEGRATION_COMPLETE
```

旧 G04 即可 PASS，而 `RealMapperAdapter.map_reaction()` 仍然抛 `NotImplementedError`。

修复后 G04 必须：

1. 从冻结 config 读取 mapper backend；
2. 实例化 `RealMapperAdapter`；
3. 证明 `is_available()`；
4. 对预注册的小型真实/curated integration reactions 实际调用 `map_reaction()`；
5. 验证 mapper name/version/parameters；
6. 验证输出不是 fake；
7. 验证 mapping pairs 引用真实 participant；
8. 验证 multi-fragment、partial、unmapped、failure、timeout；
9. 验证 MCS/center-pair 不成为 full/strict；
10. 验证 formal mapping 不生成 mechanism。

如果依赖未安装或 adapter 仍是 skeleton：

```text
G04 = BLOCKED
```

不得读取 fake sample 宣称 integration complete。

### 5.4 G06 必须验证实际 proline/2OG pairs

ChatGPT 已证明：

- 在保持 case count >= 14 时删除 proline case，旧 G06 仍 PASS；
- 向 `strict_eligible_pairs` 注入 `r2 -> p1` forbidden pair，旧 G06 仍 PASS。

修复后必须直接验证：

```text
proline case 必须存在
reactant/product participant chemical identities 明确
proline -> hydroxyproline 存在或整条 reaction quarantine
2OG -> succinate 存在或整条 reaction quarantine
2OG -> hydroxyproline 不得存在于 strict_eligible_pairs
critical ambiguity 不得进入 strict
说明字符串不能作为主要证据
```

不要依赖固定的 `r1/r2/p1/p2` 顺序；应通过 molecule/participant identity 或稳定 source-bound IDs 定位。

### 5.5 G08 必须实际测试 fail-closed

除 8 行 policy manifest 外，G08 必须运行并验证：

```text
incomplete source excluded from strict
failed/partial/unmapped mapping excluded from strict
MCS/center fallback excluded from strict
unknown participant reference excluded
contradictory ledger state excluded
quarantine and strict_prohibited never enter production
```

不得只读取预先写好的 `eligibility_matrix_execution.json`。

### 5.6 G09 必须检测嵌套证据 mutation

G09 必须实际运行第 3 节列出的 hash/tamper tests，并至少做独立 mutation：

```text
participant provenance mutation
mapping pair mutation
ledger mutation
lineage pair mutation
transformed atom maps mutation
```

任一 mutation 未改变 snapshot hash，G09 必须 FAIL。

### 5.7 G10 必须读取 A/B/adjudication 内容

ChatGPT 已证明以下状态可让旧 G10 PASS：

```text
annotator_a_status = COMPLETE
annotator_b_status = COMPLETE
adjudication_status = COMPLETE
catastrophic_error_count = 0
annotator_a_file = null
annotator_b_file = null
```

修复后 G10 必须验证：

```text
annotation A 文件存在、可解析、schema valid
annotation B 文件存在、可解析、schema valid
adjudication 文件存在、可解析、schema valid
annotator A ID 非空
annotator B ID 非空
A ID != B ID
adjudicator ID 与 A/B 独立
A/B 覆盖同一 frozen sample manifest
所有 sample IDs 完整且无重复/缺失
agreement 从 A/B 内容重新计算，不信任预填数字
disagreement count 从内容重新计算
adjudication 覆盖所有 disagreement
catastrophic error count 从 adjudicated result 重新计算
protocol hash/threshold 证明在结果前冻结
真实 snapshot ID/hash 与 sample manifest 一致
```

如果缺第二位独立 annotator：

```text
G10 = BLOCKED_MANUAL_AUDIT_INCOMPLETE
```

不得由同一执行过程复制两份 annotation。

---

## 6. 必须扩展 anti-false-positive mutations

保留现有 M1–M8，并新增至少以下 mutations：

```text
M9  G03 verdict COMPLETE but zero audited records
M10 G03 source IDs/examples empty
M11 G03 source file hash mismatch
M12 G04 status-only promotion while real adapter skeleton
M13 G04 all_backends_unavailable=true but status COMPLETE
M14 G06 remove proline case while keeping >=14 cases
M15 G06 inject forbidden 2OG->hydroxyproline strict pair
M16 G08 mapping_completeness=failed enters strict production
M17 G08 source_completeness=incomplete enters strict production
M18 G09 mutate participant provenance without hash change
M19 G09 mutate mapping pair without hash change
M20 G09 mutate source ledger without hash change
M21 G09 mutate transformed lineage without hash change
M22 G10 COMPLETE statuses with null annotation files
M23 G10 same annotator ID for A and B
M24 G10 missing adjudication for disagreement
M25 blocked Gate also contains implementation failure
```

每个 mutation 必须：

- 在隔离临时副本或进程内 monkeypatch 执行；
- 不污染正式源码/evidence；
- 记录 expected gate、actual status、caught/missed；
- 不能因为原 Gate 已 BLOCKED 就把 mutation 算作 caught；
- 只有对应实现错误被识别为 FAIL 才算 caught；
- 不能通过只搜索源码字符串来代替执行。

特别注意：

```text
not passed
```

不总等于 mutation caught。

例如 G04 原本就 BLOCKED，mutation 后仍 BLOCKED，不得算“成功抓住 implementation mutation”。必须证明该 mutation 触发了明确 implementation failure。

---

## 7. 真实 source、mapper、manual audit 的阻断处理

### 7.1 已发现但未确认的候选 source

当前仓库存在：

```text
/Volumes/CC/Enzyme_Agent/depending/data/rxn2enzyme_positives.pkl
/Volumes/CC/Enzyme_Agent/depending/data/feature/reaction/reacting_center/reacting_center.pkl
```

现有 audit 记录：

```text
candidate_rxn_count = 3601
candidate_proline_keyword_hits = 0
source_confirmed_by_env = false
usable_for_legacy_audit = false
```

你必须先只读检查：

- pickle schema；
- 字段含义；
- 是否包含完整 reaction；
- participant 是否完整；
- source version/authority；
- 是否只是训练派生物或缓存；
- `reacting_center.pkl` 是否是 ground truth、派生 feature 或潜在 leakage；
- 是否可作为 P1 authoritative reaction source。

然后向用户提交一份明确选择请求。

未经用户确认，不得自动把这两个文件升级为 real source authority。

### 7.2 依赖安装

当前缺少：

```text
rdkit
numpy
networkx
scipy
```

未经用户明确授权：

- 不得安装；
- 不得联网下载；
- 不得静默使用系统 Python；
- 不得把系统环境“碰巧可 import”写入项目证据；
- 不得伪造 lock。

即使用户授权安装，也必须在项目 `.venv` 中：

- 记录安装命令；
- 记录 resolved versions；
- 更新真实 lock；
- 运行真实 mapper adapter integration；
- 不能仅因 RDKit 可 import 就把 G04 标 PASS。

### 7.3 manual audit

manual audit 必须等待：

```text
真实 source snapshot
+ 修复后的完整 content hash
+ 真实 mapping/lineage/ledger
```

然后重新生成 sample manifest。

不能对当前 4 条 fixture 做双标后声称 real P1 audit complete。

---

## 8. TDD 和执行纪律

每组修复严格执行：

```text
READ
→ 写最小 RED test
→ 运行并记录 RED 原因
→ 最小实现
→ 运行 targeted GREEN
→ 运行 P0 + 全部 P1 regression
→ 运行对应 Gate/mutation
→ 记录 changed files/assumptions/deviations
```

禁止：

- 先修改测试期望让旧代码变绿；
- 删除失败测试；
- 使用 skip/xfail；
- conditional early return 掩盖必测分支；
- 仅测试 evidence JSON 中的自报布尔值；
- 只检查文件存在；
- 用字符串包含关系代替结构化语义验证；
- catch broad exception 后默认 PASS；
- BLOCKED 覆盖 implementation failure；
- 手工编辑 Gate report 数字。

---

## 9. 每轮必须运行的回归

至少运行：

```bash
.venv/bin/python -m pytest tests/contracts -q -p no:cacheprovider -ra
.venv/bin/python -m pytest tests/p1 -q -p no:cacheprovider -ra
.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra
.venv/bin/python scripts/run_p0_gate.py
.venv/bin/python scripts/run_p1_mutations.py
.venv/bin/python scripts/run_p1_gate.py
```

正式 Gate 会重写报告，因此最终审核前应：

1. 在隔离副本先运行；
2. 确认结果；
3. 再在正式目录运行一次生成最终报告；
4. 检查没有误写 P0、legacy、benchmark、core；
5. 记录所有 Gate side effects。

如果 P1 Gate 因真实资源仍 BLOCKED，exit code 应非 0，报告必须同时列出：

```text
implementation_failures = 0
external_blockers = [...]
```

若 implementation failures 非 0，不得只显示 BLOCKED。

---

## 10. 必须更新的工作日志

在：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
```

追加本轮，不得覆盖历史。

至少包含：

1. 审核 finding ID；
2. root cause；
3. RED test 名称和旧实现失败证据；
4. 修复策略；
5. changed files；
6. targeted test 结果；
7. full regression 精确结果；
8. P0 Gate 结果；
9. P1 Gate 结果；
10. mutation 结果；
11. 外部 blocker；
12. deviation；
13. 未解决风险；
14. 是否触碰用户文件；
15. 是否安装依赖；
16. 是否修改冻结文档/ADR。

---

## 11. 重新提交给 ChatGPT 的文件

最终在：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/
```

至少生成：

```text
SUBMISSION_TO_CHATGPT_P1_ROUND_2.md
P1_GATE_REPORT.md
P1_GATE_REPORT.json
P1_REMEDIATION_WORKLOG.md
mutation_results.json
```

建议额外生成：

```text
P1_ROUND_2_AUDIT_EVIDENCE.json
snapshot_nested_mutation_results.json
eligibility_fail_closed_results.json
gate_false_positive_mutation_results.json
```

提交封面必须明确区分：

```text
implementation remediation status
real source status
real mapper status
real proline/2OG status
manual audit status
scientific Gate status
P2 status
```

---

## 12. 重新提交封面必须回答的 25 项

1. 当前 commit/working tree 状态；  
2. P0 tests 精确统计；  
3. P0 Gate 结果；  
4. P1 tests 精确统计；  
5. fail/error/skip/xfail/xpass 精确统计；  
6. snapshot 完整 record payload schema；  
7. snapshot hash 覆盖哪些嵌套证据；  
8. participant mutation 是否改变 hash；  
9. mapping mutation 是否改变 hash；  
10. ledger mutation 是否改变 hash；  
11. lineage mutation 是否改变 hash；  
12. loader 是否拒绝四类嵌套 tampering；  
13. incomplete source 是否能进入 strict；  
14. failed/partial/unmapped mapping 是否能进入 strict；  
15. MCS/center fallback 是否能进入 strict；  
16. G03 零记录假 COMPLETE mutation 是否 caught；  
17. G04 status-only promotion mutation 是否 caught；  
18. G06 missing proline mutation 是否 caught；  
19. G06 forbidden lineage mutation 是否 caught；  
20. G10 null annotation files mutation 是否 caught；  
21. blocked + implementation failure 是否分别报告；  
22. 真实 source manifest/hash；  
23. 真实 mapper backend/version/parameters；  
24. manual audit A/B/adjudication/agreement/catastrophic count；  
25. P2 是否仍 BLOCKED。

对于仍然阻断的项目，写：

```text
BLOCKED
reason
required user input
what was safely completed without fabrication
```

不得写虚假 `0`、空列表或 fixture 结果来代替。

---

## 13. 重新提交的允许结尾

### 13.1 如果真实 source/mapper/manual audit 仍阻断

必须以：

```text
READY_FOR_CHATGPT_P1_REMEDIATION_READ_ONLY_AUDIT
P1 SCIENTIFIC GATE BLOCKED — EXTERNAL INPUTS REQUIRED
P2 BLOCKED pending ChatGPT re-audit
```

结尾。

### 13.2 只有真实 Gate 10/10 时

即使 agent 自测得到 10/10，也只能写：

```text
READY_FOR_CHATGPT_P1_ROUND_2_READ_ONLY_AUDIT
P2 BLOCKED pending ChatGPT re-audit
```

不得自行写：

```text
P1 finally accepted
P1 accepted
P2 authorized
system can reliably predict X→Y
```

最终接受权属于 ChatGPT 只读审核。

---

## 14. Definition of Done

本轮整改 DoD：

- [ ] P0 contracts 未回归；  
- [ ] P0 Gate 10/10；  
- [ ] snapshot hash 覆盖完整 participant/mapping/ledger/lineage/provenance；  
- [ ] 修改任一核心嵌套证据都会改变 hash；  
- [ ] loader 会拒绝核心嵌套证据 tampering；  
- [ ] 完整 evidence 可以从 snapshot 审计/重放；  
- [ ] incomplete source 不进入 strict；  
- [ ] failed/partial/unmapped mapping 不进入 strict；  
- [ ] MCS/center fallback 不进入 strict；  
- [ ] ledger/evidence/lineage reference 全部验证；  
- [ ] G03 零记录假 COMPLETE 不能通过；  
- [ ] G04 status-only promotion 不能通过；  
- [ ] G06 缺 proline case 不能通过；  
- [ ] G06 forbidden 2OG→hydroxyproline 不能通过；  
- [ ] G10 没有真实 A/B/adjudication 文件不能通过；  
- [ ] BLOCKED 不再覆盖 implementation FAIL；  
- [ ] M1–M25 全部按正确语义 caught；  
- [ ] 全部 tests 零 fail/error/skip/xfail/xpass；  
- [ ] 未用 fixture 冒充 real evidence；  
- [ ] 未修改冻结设计/ADR 迁就实现；  
- [ ] 未写 legacy source；  
- [ ] 未删除或覆盖用户文件；  
- [ ] 未经授权未安装依赖、未联网；  
- [ ] 提交统计与当前 HEAD 完全一致；  
- [ ] P2 保持 BLOCKED，等待 ChatGPT 复审。

---

## 15. 最重要的验收语义

本项目的目标不是“让测试数量很多”，而是：

```text
从真实完整反应中找到 donor A
→ 正确解析同一条反应里的 A→B transformed lineage
→ 保留辅酶、小分子、多 lineage 和不确定性
→ 把完整 mapping/lineage/ledger/provenance 冻结为可重放 snapshot
→ 后续才允许对 X 做有证据的反应类比
```

因此任何以下行为都属于阻断级错误：

```text
错误 A→B 进入 production
mapping failed 仍 strict eligible
2OG→hydroxyproline 进入 strict
ledger/lineage 改变但 snapshot hash 不变
fixture 被当作 real evidence
修改状态字符串代替真实集成
同一 annotator 冒充双独立审核
BLOCKED 掩盖 implementation FAIL
```

请先完成内部可修复缺陷，再诚实报告仍需要用户提供的真实 source、依赖安装授权和独立 annotator 资源。
