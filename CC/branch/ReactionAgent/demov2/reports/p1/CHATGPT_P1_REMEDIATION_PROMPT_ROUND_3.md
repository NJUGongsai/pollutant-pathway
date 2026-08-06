# P1 Round 3 严格整改任务书

> **用途：** 将本文件完整交给负责整改的 Qwen/coding agent。  
> **项目根目录：** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`  
> **上一轮提交：** `reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_2.md`  
> **ChatGPT Round 2 审核结论：** `REJECTED_REMEDIATION_REQUIRED`  
> **当前授权边界：** 只整改 P1 Round 2 审核确认的内部实现、测试、Gate 和证据报告；不得进入 P2 业务实现。  
> **最终接受权：** 属于 ChatGPT 后续只读审核；实现 agent 不得自行宣布 P1 accepted 或 P2 authorized。

---

## 0. 任务结论先行

Round 2 不是“只剩外部资源 BLOCKED”。

ChatGPT 在隔离副本中重新执行了：

```text
tests:              669 passed
P0 Gate:            10/10 PASS
P1 Gate 自报:       7 PASS / 3 BLOCKED / 0 FAIL
mutation runner:    25/25 caught
```

但额外独立反例证明：

```text
P1-G08 必须为 FAIL
P1-G09 必须为 FAIL
```

因此 Round 2 的正确状态应为：

```text
5 PASS
2 FAIL
3 BLOCKED

implementation_failures:
- P1-G08
- P1-G09

external_blockers:
- P1-G03
- P1-G04
- P1-G10

overall_status:
NOT_READY_FOR_CHATGPT_AUDIT

P2:
BLOCKED
```

本轮必须先修复两个内部 Critical：

1. snapshot 仍然是有损投影，没有冻结完整科学证据；
2. 多种不可靠或相互矛盾的 mapping/lineage 仍会进入 `strict_eligible`。

修复后，如果真实 source、真实 mapper 和独立双标注仍未完成，允许的最终状态是：

```text
P1 IMPLEMENTATION REMEDIATION COMPLETE
P1 SCIENTIFIC INTEGRATION BLOCKED
P2 BLOCKED
```

不得为了得到 10/10 而伪造真实 evidence。

---

## 1. 你的角色和工作方式

你是 P1 Round 3 remediation implementation agent。

你的职责是：

```text
读取冻结设计和 Round 2 审核证据
→ 复现独立反例为 RED tests
→ 做最小、可解释、可审计的修复
→ 扩展 Gate 和 mutation 防止假阳性
→ 运行完整回归
→ 生成 Round 3 提交材料
→ 保持 P2 BLOCKED 等待 ChatGPT
```

遵守以下实现纪律：

- 先理解现有 authority 和数据流，再改代码；
- 每个修复先写能复现缺陷的 RED test；
- 修改范围必须与本任务逐项对应；
- 不重构无关模块；
- 不修改冻结设计或 ADR 来迁就现有实现；
- 不删除、跳过或降低既有测试；
- 不用预填 JSON 布尔值代替实际运行；
- 不用 synthetic fixture 解除真实资源 blocker；
- 不隐藏 assumptions、deviations 或仍然存在的 blocker；
- 不因“669 tests 已绿”而跳过独立反例；
- 不把测试数量当作正确性的替代品。

---

## 2. 开工前必须完整阅读

必须按顺序完整阅读，不得只 grep 关键词或只读摘要。

### 2.1 冻结设计和实施计划

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_design.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_plan.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/chatgpt_p1_train.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/superpowers/specs/2026-07-29-p1-multi-agent-team-design.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/superpowers/plans/2026-07-29-p1-data-foundation.md
```

重点理解：

```text
完整反应是事实单位
A→B 必须来自同一完整反应中的 resolved transformed lineage
strict = reliable mapping + reliable lineage + complete cross-object invariants
snapshot = 完整、无损、版本化、可重放的数据 authority
fixture 只能验证实现，不能冒充真实科学证据
```

### 2.2 上一轮整改任务和 Round 2 提交

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_2.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_2.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_2_AUDIT_EVIDENCE.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/mutation_results.json
```

### 2.3 当前 source/preflight/manual-audit 证据

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_PREFLIGHT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_PREFLIGHT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/data_audit/legacy_lineage_audit.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/data_audit/legacy_lineage_audit.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_report.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_report.json
```

### 2.4 必须审查的 implementation

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/loader.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/eligibility/engine.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/mapping.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/ledger.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/p1_entities.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/lineage/resolver.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/mapping/adapter.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_gate.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_mutations.py
```

### 2.5 必须审查和扩展的 tests

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_nested_evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_fail_closed.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_engine.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_lineage_graph.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_mapping_adapter.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_p1_gate_contract.py
```

---

## 3. 工作区保护和授权边界

### 3.1 开工前记录，不得清理用户内容

先记录：

```bash
git status --short
git log -1 --oneline
```

当前工作区存在大量未提交和未跟踪内容，可能属于用户或其他 agent。

禁止：

```text
git reset --hard
git checkout --
git clean
删除或覆盖不属于本轮的文件
擅自 add/commit/push
```

本轮仅修改与 Round 3 缺陷直接相关的文件。

### 3.2 禁止修改

不得修改：

```text
plan/final_design.md
plan/final_plan.md
docs/decisions/ADR-*.md
tests/contracts/
../benchmark/
../core/
任何 legacy source
P0 frozen semantics
```

如果发现实现与冻结设计冲突，应修实现；不得改设计来让错误代码合法化。

### 3.3 外部依赖和联网

当前 `.venv` 已有：

```text
rdkit
numpy
networkx
scipy
pydantic
pytest
```

本轮没有安装新依赖的必要。

禁止未经用户明确授权：

- 安装或升级依赖；
- 联网下载 mapper、模型或数据；
- 写入外部数据库；
- 把 candidate pickle 擅自提升为 source authority。

### 3.4 本轮不要求解除的外部 blocker

以下可以继续诚实 BLOCKED：

```text
P1-G03:
真实 reaction source 未经用户确认；
真实 proline/2OG source record 尚未定位。

P1-G04:
RealMapperAdapter.map_reaction() 仍是 skeleton；
本轮不自动扩大为真实 mapper 实现任务。

P1-G10:
第二位独立 annotator 和独立 adjudicator 尚未提供。
```

不要把它们伪装成 PASS，也不要让它们掩盖 P1-G08/P1-G09 的 implementation failure。

---

## 4. 开工基线

在正式修改前运行并记录真实结果：

```bash
.venv/bin/python -m pytest tests/contracts -q -p no:cacheprovider -ra
.venv/bin/python -m pytest tests/p1 -q -p no:cacheprovider -ra
.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra
.venv/bin/python scripts/run_p0_gate.py
.venv/bin/python scripts/run_p1_mutations.py
.venv/bin/python scripts/run_p1_gate.py
```

ChatGPT Round 2 隔离复核的参考基线是：

```text
tests/contracts: 290 passed
tests/p1:        379 passed
tests full:      669 passed
P0 Gate:         10/10 PASS
mutations:       25/25 caught
P1 Gate 自报:    7 PASS / 3 BLOCKED
```

如果当前 collection 已变化，记录实际数字；不得复制旧统计。

正式 Gate 会重写报告。建议先在隔离副本验证，确认修复后再在正式目录运行一次，生成最终 evidence。

---

## 5. Critical-1：snapshot 仍然是有损投影

### 5.1 已确认根因

当前：

```text
reaction_agent/snapshot/builder.py
::_canonical_record_payload
```

手工拼接少量字段，并把结果称为“完整 evidence”。

它已经包含：

```text
基础 reaction/source IDs
raw/normalized reaction
direction
participants
mapping_report
外部 source_ledger
外部 resolved_lineages
部分 EligibilityDecision 字段
quarantine_record_id
```

但它没有包含完整 `ReactionEvidence.model_dump(mode="json")`。

下列 `ReactionEvidence` 科学/审计字段被丢失：

```text
source_uri_or_citation
fragment_lineage_graph
resolved_transformed_lineages
ambiguity_sets
transformation_hypotheses
source_reaction_ledger
quality_report
provenance
quarantine
```

`snapshot_id` 也没有进入 payload。它可能涉及 snapshot hash 循环引用，因此不能简单盲目加入；必须在集中 exclusion policy 中说明如何处理，而不是静默遗漏。

当前 payload 也没有包含完整 `EligibilityDecision`：

```text
participant_id
evidence_ids
required_warnings
research_diagnostic_eligibility
policy_version
```

当前 payload 也没有包含完整 `QuarantineRecord`：

```text
reason
category
evidence_ids
source_record_id
quarantine_behavior
notes
```

当前 `quarantine_reason` 被列入 `_RECORD_META_FIELDS`，loader 重算 record hash 时会排除，因此它不是受 record content hash 保护的冻结内容。

### 5.2 ChatGPT 已复现的 hash 反例

合法 strict fixture 的 baseline snapshot hash：

```text
30261902ce0e4fb7d33e214ee4c6cbcb27ca12dbd97136675ae1327e404e9f2b
```

逐项只修改一个字段后，hash 均保持完全相同：

| Mutation | Hash changed? |
|---|---|
| `ReactionEvidence.provenance` | NO |
| `source_uri_or_citation` | NO |
| `fragment_lineage_graph` | NO |
| `ambiguity_sets` | NO |
| `transformation_hypotheses` | NO |
| `quality_report` | NO |
| `quarantine` | NO |

这不是未来优化，而是 Round 2 明确要求仍未完成的 Critical。

### 5.3 正确的最小实现方向

优先使用简单、单一 authority 的 canonical content。

推荐结构：

```text
FrozenSnapshotRecordContent
├── reaction_evidence
├── source_ledger
├── resolved_lineages
├── eligibility_decision
├── quarantine_record
└── lane
```

规范化 payload 的逻辑应等价于：

```python
{
    "reaction_evidence": evidence.model_dump(mode="json"),
    "source_ledger": (
        ledger.model_dump(mode="json")
        if ledger is not None
        else None
    ),
    "resolved_lineages": [
        lineage.model_dump(mode="json")
        for lineage in lineages
    ],
    "eligibility_decision": decision.model_dump(mode="json"),
    "quarantine_record": (
        quarantine_record.model_dump(mode="json")
        if quarantine_record is not None
        else None
    ),
    "lane": lane,
}
```

不要求为了单一用途创建复杂抽象；可以使用一个 P1 严格 schema，也可以使用一个集中 canonical serializer。关键要求是：

1. 不能继续手工白名单复制部分 `ReactionEvidence` 字段；
2. builder hash、records persistence、loader recompute 必须使用同一 content object；
3. 除明确 runtime/circular 字段外，所有科学证据必须被持久化并影响 hash；
4. exclusion policy 必须集中定义、逐字段说明、通过测试冻结；
5. `lane` 必须被 hash，或由完整 decision 重新推导并在 loader 严格比对；
6. index entry 必须与完整 frozen record 的 ID、lane、decision、hash 一致；
7. 完整 quarantine/diagnostic evidence 必须可审计；
8. `source_files/source_content_hashes` 必须最终受完整 record hashes 影响。

### 5.4 解决双 ledger authority

当前同时存在：

```text
ReactionEvidence.source_reaction_ledger
SnapshotEvidenceItem.source_ledger
```

但 builder 实际使用外部 `SnapshotEvidenceItem.source_ledger`，忽略 embedded ledger。

必须选择并明确实现以下一种最简单方案：

#### 方案 A：单一 authority

```text
SnapshotEvidenceItem.source_ledger 是唯一 authority；
ReactionEvidence.source_reaction_ledger 必须为 null，
或在 ingestion 前统一规范化为同一个对象。
```

#### 方案 B：双表示但强一致

```text
两者均允许存在；
如果都存在，canonical model_dump 必须完全一致；
不一致时 fail closed，禁止进入 snapshot；
如果仅一个存在，按冻结规则规范化。
```

不得：

- 静默忽略其中一个；
- 两者不一致仍构建 snapshot；
- 一个参与 eligibility、另一个参与 hash；
- 用“当前 fixture 不会这样构造”作为保证。

### 5.5 必须先写的 RED tests

至少新增：

```text
test_snapshot_hash_changes_when_reaction_provenance_changes
test_snapshot_hash_changes_when_source_citation_changes
test_snapshot_hash_changes_when_fragment_lineage_graph_changes
test_snapshot_hash_changes_when_reaction_ambiguity_sets_change
test_snapshot_hash_changes_when_transformation_hypotheses_change
test_snapshot_hash_changes_when_quality_report_changes
test_snapshot_hash_changes_when_reaction_quarantine_changes

test_snapshot_persists_complete_reaction_evidence_model
test_snapshot_persists_complete_eligibility_decision
test_snapshot_persists_complete_quarantine_record
test_loader_rejects_tampered_reaction_level_provenance
test_loader_rejects_tampered_decision_warning_or_evidence_ids
test_loader_rejects_tampered_quarantine_record

test_embedded_and_external_ledgers_cannot_disagree
test_snapshot_id_or_runtime_exclusion_policy_is_explicit
test_lane_is_hashed_or_rederived_and_verified
```

必须继续保留并通过 Round 2 已增加的 participant/mapping/ledger/lineage mutation tests。

### 5.6 Critical-1 验收条件

以下全部成立才可称 snapshot implementation remediation complete：

```text
修改任意反应级 scientific evidence → record/snapshot hash 改变
修改完整 decision → hash 改变
修改完整 quarantine record → hash 改变
records.jsonl 可重建完整 frozen evidence
loader 从完整记录重算 hash
loader 拒绝核心 evidence tampering
embedded/external ledger 不一致不能构建 snapshot
index 与完整 record 的 lane/decision/hash 一致
```

---

## 6. Critical-2：不可靠 mapping/lineage 仍进入 strict

### 6.1 已确认根因

当前：

```text
reaction_agent/eligibility/engine.py
::_validate_strict_preconditions
```

检查了部分状态字段，但没有验证完整的 mapping/lineage 交叉关系。

目前缺少：

```text
mapped_heavy_atom_fraction strict threshold
formal assignment ambiguity
formal mapped pair participant references
formal mapped pair side references
formal mapped pair atom-map references
formal mapped pair uniqueness/consistency
lineage resolution_quality
lineage 与 formal mapping edge 的支持关系
lineage transformed_atom_maps 与 mapping 的支持关系
两个 reactants 竞争同一个 transformed product
embedded/external ledger consistency
```

### 6.2 ChatGPT 已复现的 strict fail-open

下列对象都使用现有公开 schema 构造，并能通过 schema validation：

| Schema-valid input | Current decision |
|---|---|
| `mapped_heavy_atom_fraction = 0.25` | `strict_eligible` |
| formal assignment `assignment_ambiguity = true` | `strict_eligible` |
| formal pair 引用不存在的 reactant participant | `strict_eligible` |
| formal pair 引用 participant 中不存在的 atom map `999999` | `strict_eligible` |
| lineage `resolution_quality = unresolved` | `strict_eligible` |
| lineage `ambiguity = partial` | `strict_eligible` |
| 两个 reactants 同时指向一个 transformed product | `strict_eligible` |

这些均为阻断级错误。

### 6.3 当前 forbidden cross-lineage 检查逻辑错误

当前检查：

```python
lineage_reactants = {...}
lineage_products = {...}
cross = lineage_reactants & lineage_products
```

它只能检测：

```text
某 participant 同时是 lineage reactant 和 lineage product
```

它检测不到需要阻止的典型错误：

```text
r1 → p1
r2 → p1
```

因为：

```text
reactants = {r1, r2}
products  = {p1}
intersection = {}
```

这正是 `2OG → hydroxyproline` 类错误能够绕过 snapshot/eligibility ingestion 的原因。

正确的基本检查至少需要：

```text
product_participant_id
→ strict transformed reactant participant IDs
```

若一个 product 被多个 transformed reactants 声称：

- 没有 typed merge evidence：禁止 strict；
- 有 merge evidence：仍需验证 merge 的 mapped atoms、身份语义和设计允许性；
- 当前 `ResolvedTransformedLineage` 输入没有足够 merge authority 时：默认 fail closed。

不要通过字符串搜索 `"merge"` 或说明文本放行。

### 6.4 strict mapping cross-invariants

进入 `strict_eligible` 前至少必须验证：

#### MappingReport 层

```text
mapping_report exists
mapping_status == fully_mapped
mapped_heavy_atom_fraction meets frozen strict threshold
map_number_uniqueness is true
changed_atom_coverage meets frozen strict threshold
fallback_method is null
symmetry_ambiguity is false
resonance_tautomer_ambiguity is false
formal_mapped_source_assignment exists
assignment_method == formal_mapped
assignment_ambiguity is false
assignment_quality meets strict policy
```

如果冻结设计没有单独给出 mapped-heavy-atom threshold，P1 strict 默认采用保守值：

```text
mapped_heavy_atom_fraction == 1.0
changed_atom_coverage == 1.0
```

不要静默发明宽松阈值。若认为需要其他阈值，记录为设计问题并保持 fail closed。

#### Formal mapped pairs 层

每个 pair 必须验证：

```text
reactant_participant_id exists
product_participant_id exists
reactant participant.side == reactant
product participant.side == product
reactant_atom_map exists in reactant participant.atom_map_numbers
product_atom_map exists in product participant.atom_map_numbers
pair is not duplicated
one map is not assigned to contradictory targets
```

不能只验证字符串非空。

#### Resolved lineage 层

每条进入 strict 的 lineage 必须验证：

```text
reactant participant exists and side == reactant
product participant exists and side == product
resolution_quality == resolved
ambiguity == none
lineage pair is supported by formal mapped pairs
transformed_atom_maps are supported by valid mapped atoms
no unsupported competing transformed lineage
no forbidden two-reactants-to-one-product pairing
```

如果 `ambiguity == partial` 确实不影响 transformed identity，必须有一个 typed、可验证的 reason/category 来证明；在当前 schema 没有这种 authority 时，不能进入 strict。

#### Ledger/evidence/lineage 层

继续验证：

```text
ledger.reaction_evidence_id == evidence.reaction_id
source_completeness == complete
mapping_completeness == complete
balance_status 与 completeness 相互一致
identity/balance-critical unknown 不存在
lineage/mapping/ledger participant references 一致
embedded/external ledger 不矛盾
```

### 6.5 fail-closed 结果

发现交叉不变量失败时：

- 绝不能返回 `strict_eligible`；
- 绝不能进入 strict production index；
- 根据冻结 partial eligibility matrix，进入 typed conditional、diagnostic、strict_prohibited 或 quarantine；
- reason 必须明确指出失败的不变量；
- 不得用 free-text warning 继续放入 strict。

不要求所有坏输入都 quarantine；要求它们不进入 strict，并保留正确的 typed 状态。

### 6.6 必须先写的 RED tests

至少新增：

```text
test_low_mapped_heavy_atom_fraction_never_strict
test_ambiguous_formal_assignment_never_strict
test_low_quality_formal_assignment_never_strict

test_formal_pair_unknown_reactant_participant_never_strict
test_formal_pair_unknown_product_participant_never_strict
test_formal_pair_wrong_participant_side_never_strict
test_formal_pair_unknown_reactant_atom_map_never_strict
test_formal_pair_unknown_product_atom_map_never_strict
test_contradictory_or_duplicate_mapping_pairs_never_strict

test_unresolved_lineage_never_strict
test_failed_lineage_never_strict
test_partially_resolved_lineage_never_strict
test_partial_identity_ambiguity_never_strict
test_lineage_pair_must_be_supported_by_formal_mapping
test_lineage_transformed_maps_must_be_supported_by_mapping
test_two_reactants_claiming_same_transformed_product_fail_closed
test_forbidden_2og_to_hydroxyproline_cannot_enter_snapshot_strict

test_embedded_external_ledger_mismatch_never_strict
test_public_snapshot_api_cannot_bypass_new_cross_invariants
```

至少一个测试必须通过公开 API：

```text
SnapshotEvidenceItem
→ build_snapshot
→ production_index
```

证明错误对象不仅在 `decide_eligibility()` 返回 non-strict，而且确实不会写入 strict production lane。

### 6.7 修复现有“合法 strict fixture”

当前部分 test fixture 使用：

```text
ResolvedTransformedLineage.resolution_quality 默认值 = unresolved
```

却把该对象作为合法 strict baseline。

这相当于把错误语义固化在测试里。

修复 fixture 时必须：

- 明确为合法 strict fixture 设置 `resolution_quality=resolved`；
- 明确设置 `ambiguity=none`；
- 提供与 lineage 一致的 formal mapping pairs；
- 不得仅修改期望值让 unresolved 继续 strict；
- 保留单独 negative test 证明 unresolved 不得 strict。

---

## 7. Gate 修复要求

### 7.1 P1-G08 必须从 PASS 变为真实验证

G08 不能只验证：

```text
8 行 policy manifest
existing test files green
```

它必须实际执行第 6 节新增的 fail-closed tests，至少覆盖：

```text
low mapped fraction
assignment ambiguity
unknown mapping participant
unknown atom map
wrong participant side
unresolved/partial lineage
lineage unsupported by mapping
two reactants → one transformed product
embedded/external ledger mismatch
public snapshot ingestion boundary
```

任一反例得到 `strict_eligible` 或进入 strict production：

```text
P1-G08 = FAIL
implementation_failures 非空
```

### 7.2 P1-G09 必须验证完整 evidence，而不是部分 nested fields

G09 当前已经检查：

```text
participant
participant provenance
mapping pair
external source ledger
external resolved lineage
```

还必须增加：

```text
reaction-level provenance
source URI/citation
fragment lineage graph
reaction ambiguity sets
transformation hypotheses
quality report
reaction quarantine
complete EligibilityDecision
complete QuarantineRecord
embedded/external ledger consistency
```

任一 scientific mutation 不改变 record/snapshot hash：

```text
P1-G09 = FAIL
```

### 7.3 Gate 不得隐藏 implementation failure

保留现有正确聚合语义：

```text
implementation_failures 非空
→ Gate = FAIL
→ overall = NOT_READY_FOR_CHATGPT_AUDIT
```

即使同一个 Gate 还有 external blocker，也不能只显示 BLOCKED。

### 7.4 G03 stale dependency evidence

当前 P1 preflight 已显示：

```text
rdkit/numpy/networkx/scipy installed
```

但 legacy lineage audit/G03 evidence 仍引用：

```text
rdkit_absent_runtime_unable_to_execute_legacy_transformed_pair
```

必须重新运行或重新生成相关只读 audit evidence，使 blocker 状态与当前环境一致。

允许保留：

```text
real_reaction_source_not_confirmed
required_case_missing_proline_2og
```

不得继续把已经解除的 `rdkit_absent` 当作当前 blocker。

重新审计不得：

- 把 candidate pickle 擅自设为 source authority；
- 把 keyword 0 hits 当作完整化学检索；
- 用 fixture 填充真实 source record；
- 写入 legacy/benchmark/core。

---

## 8. Mutation runner 扩展

### 8.1 保留 M1–M25

不得删除或弱化已有 M1–M25。

必须确认它们仍按正确语义 caught。

注意：

- `actual_passed=true` 不应被含糊地用作多种相反语义；
- mutation report 字段应清楚区分“被测 Gate 是否通过”和“mutation 是否被捕获”；
- M25 不应只在 mutation runner 中复制一份聚合算法。

### 8.2 修正 M25 验证方式

M25 当前手工复制 Gate aggregation 逻辑，不能证明真实 report aggregation 不会回归。

应把 aggregation 提取为可测试的最小真实函数，或通过真实 `generate_report`/等价公开入口验证：

```text
一个 Gate 同时有 external_blocker + implementation_failure
→ counted as FAIL
→ overall NOT_READY
→ not counted only as BLOCKED
```

不要为测试创建第二套 aggregation authority。

### 8.3 新增 M26–M41

至少增加以下 mutation：

```text
M26  reaction-level provenance changes but hash stays unchanged
M27  source citation changes but hash stays unchanged
M28  fragment-lineage/ambiguity evidence changes but hash stays unchanged
M29  quality/quarantine evidence changes but hash stays unchanged
M30  EligibilityDecision warning/evidence changes but hash stays unchanged
M31  QuarantineRecord changes but hash stays unchanged

M32  mapped_heavy_atom_fraction < strict threshold enters strict
M33  formal assignment ambiguity enters strict
M34  formal pair unknown participant enters strict
M35  formal pair unknown atom map enters strict
M36  formal pair wrong-side participant enters strict
M37  unresolved/failed lineage enters strict
M38  partial identity ambiguity enters strict
M39  lineage unsupported by formal mapping enters strict
M40  two reactants claim one transformed product and enter strict
M41  embedded/external source ledgers disagree but snapshot builds strict
```

成功标准：

```text
M1–M41 全部 caught
```

“caught”必须表示 mutation 触发了预期的明确失败，而不是：

- 原 Gate 本来就 BLOCKED；
- unrelated failure；
- 手工写 `caught=true`；
- 只检查说明字符串；
- 调用一份复制的假实现。

---

## 9. TDD 执行顺序

严格按以下顺序：

### R3-T1：冻结基线

```text
记录 git state
运行现有 tests/Gates/mutations
记录准确统计
```

### R3-T2：Critical-1 RED

```text
先写 reaction-level/decision/quarantine hash tests
运行 targeted tests
保存 RED 原因
```

预期 RED 原因必须是：

```text
scientific field changed but hash unchanged
或 records.jsonl missing complete object
```

### R3-T3：Critical-1 最小修复

```text
统一 canonical content
统一 builder/write/loader
解决双 ledger authority
运行 targeted GREEN
```

### R3-T4：Critical-2 RED

```text
先写 mapping/lineage cross-invariant tests
运行 targeted tests
保存 strict fail-open 证据
```

### R3-T5：Critical-2 最小修复

```text
扩展 strict cross-validator
修正 forbidden pairing
修正合法 strict fixtures
运行 targeted GREEN
```

### R3-T6：Gate 和 mutations

```text
G08 接入新 fail-closed tests
G09 接入完整 evidence mutations
M25 使用真实 aggregation
增加 M26–M41
```

### R3-T7：evidence freshness

```text
更新 G03 当前 dependency 状态
重新生成 snapshot sample/hash
重新生成 Gate/mutation evidence
```

### R3-T8：完整回归

```text
P0 contracts
P1 tests
full tests
P0 Gate
M1–M41
P1 Gate
```

每一步都记录：

```text
assumption
RED evidence
changed files
GREEN result
remaining blocker
```

---

## 10. 必须运行的验收命令

至少运行：

```bash
.venv/bin/python -m pytest tests/contracts -q -p no:cacheprovider -ra
.venv/bin/python -m pytest tests/p1 -q -p no:cacheprovider -ra
.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra
.venv/bin/python scripts/run_p0_gate.py
.venv/bin/python scripts/run_p1_mutations.py
.venv/bin/python scripts/run_p1_gate.py
```

还必须单独运行新增 targeted tests，确保失败原因可定位：

```bash
.venv/bin/python -m pytest \
  tests/p1/test_snapshot_nested_evidence.py \
  tests/p1/test_snapshot_builder.py \
  -q -p no:cacheprovider -ra

.venv/bin/python -m pytest \
  tests/p1/test_eligibility_fail_closed.py \
  tests/p1/test_eligibility_engine.py \
  tests/p1/test_lineage_graph.py \
  -q -p no:cacheprovider -ra

.venv/bin/python -m pytest \
  tests/p1/test_p1_gate_contract.py \
  -q -p no:cacheprovider -ra
```

要求：

```text
fail = 0
error = 0
skip = 0
xfail = 0
xpass = 0
```

P0 必须继续：

```text
10/10 PASS
```

如果 G03/G04/G10 仍因真实资源 BLOCKED，P1 Gate exit code 应继续非 0；这是诚实结果，不得强行改成 0。

---

## 11. 必须更新的工作日志

在以下文件追加 Round 3，不得覆盖历史：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
```

必须包含：

1. Round 3 finding IDs；
2. 每个 finding 的 root cause；
3. ChatGPT 独立反例；
4. RED test 名称；
5. RED 实际失败信息；
6. 修复策略；
7. 为什么选择该最小方案；
8. changed files；
9. targeted GREEN 结果；
10. full test 精确统计；
11. P0 Gate 结果；
12. P1 Gate 结果；
13. M1–M41 结果；
14. snapshot canonical schema；
15. runtime/circular exclusion policy；
16. strict cross-invariants；
17. assumptions/deviations；
18. external blockers；
19. 是否安装依赖/联网；
20. P2 状态。

若本轮没有安装依赖或联网，明确写：

```text
No dependency installation performed.
No network access performed.
```

---

## 12. Round 3 必须生成的提交材料

### 12.1 提交封面

创建：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_3.md
```

### 12.2 建议新增结构化审核 evidence

创建或更新：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_3_AUDIT_EVIDENCE.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/snapshot_complete_evidence_mutation_results.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/eligibility_cross_invariant_results.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results_round_3.json
```

不要手工编数字；从实际执行结果生成。

### 12.3 提交封面必须列出

1. branch；
2. HEAD；
3. working-tree 状态；
4. changed files；
5. tests/contracts 精确统计；
6. tests/p1 精确统计；
7. full tests 精确统计；
8. P0 Gate；
9. P1 Gate；
10. M1–M41；
11. canonical frozen record 完整 schema；
12. runtime/circular exclusions 及理由；
13. reaction-level mutation hash 结果；
14. complete decision/quarantine mutation hash 结果；
15. loader tamper rejection 结果；
16. dual ledger authority 和一致性规则；
17. strict cross-invariant 列表；
18. low mapped fraction 是否被 strict 拒绝；
19. assignment ambiguity 是否被 strict 拒绝；
20. unknown participant/atom-map 是否被 strict 拒绝；
21. unresolved/partial lineage 是否被 strict 拒绝；
22. unsupported lineage 是否被 strict 拒绝；
23. two-reactants-to-one-product 是否被 strict 拒绝；
24. public snapshot API 是否能绕过；
25. G03 当前 source/blocker；
26. G04 当前 mapper/blocker；
27. G10 当前 manual-audit/blocker；
28. 是否安装依赖或联网；
29. assumptions/deviations；
30. P2 状态。

---

## 13. 外部 blocker 的正确报告格式

对于仍阻断项，使用：

```text
BLOCKED
reason:
required user input:
what was safely completed:
what was not fabricated:
```

### 13.1 G03

应类似：

```text
BLOCKED
reason:
  authoritative real reaction source not confirmed;
  required real proline/2OG record not located.
required user input:
  confirm source authority/version/path.
what was safely completed:
  read-only source inventory and structural audit.
what was not fabricated:
  no synthetic row promoted to real source evidence.
```

如果 RDKit 当前已安装，不得再写 `rdkit_absent`。

### 13.2 G04

应类似：

```text
BLOCKED
reason:
  RealMapperAdapter.map_reaction() remains a skeleton.
required user input:
  authorize/assign real mapper implementation in a separate scoped task,
  or accept G04 remains blocked.
what was safely completed:
  fake/curated mapping contracts and live skeleton detection.
what was not fabricated:
  no fake mapper output presented as real integration.
```

### 13.3 G10

应类似：

```text
BLOCKED
reason:
  independent annotator B and independent adjudicator not produced.
required user input:
  separate independent annotation/adjudication resources.
what was safely completed:
  protocol/schema/threshold checks.
what was not fabricated:
  no duplicated annotation presented as independent review.
```

---

## 14. Round 3 Definition of Done

### Snapshot

- [ ] canonical payload 持久化完整 `ReactionEvidence`；
- [ ] canonical payload 持久化完整 `SourceReactionLedger | null`；
- [ ] canonical payload 持久化完整 resolved lineages；
- [ ] canonical payload 持久化完整 `EligibilityDecision`；
- [ ] canonical payload 持久化完整 `QuarantineRecord | null`；
- [ ] builder/hash/writer/loader 使用同一 canonical content；
- [ ] runtime/circular exclusions 集中、显式、有测试；
- [ ] reaction-level provenance mutation 改变 hash；
- [ ] source citation mutation 改变 hash；
- [ ] fragment-lineage/ambiguity mutation 改变 hash；
- [ ] quality/quarantine mutation 改变 hash；
- [ ] decision mutation 改变 hash；
- [ ] quarantine record mutation 改变 hash；
- [ ] loader 拒绝上述 tampering；
- [ ] embedded/external ledger 不一致 fail closed；
- [ ] index 与 full record 一致。

### Strict boundary

- [ ] low mapped-heavy-atom fraction 不进入 strict；
- [ ] assignment ambiguity 不进入 strict；
- [ ] low-quality/non-formal assignment 不进入 strict；
- [ ] unknown participant mapping pair 不进入 strict；
- [ ] wrong-side mapping pair 不进入 strict；
- [ ] unknown atom-map pair 不进入 strict；
- [ ] duplicate/contradictory mapping pair 不进入 strict；
- [ ] unresolved/failed/partially resolved lineage 不进入 strict；
- [ ] identity-relevant partial ambiguity 不进入 strict；
- [ ] unsupported lineage 不进入 strict；
- [ ] unsupported transformed atom maps 不进入 strict；
- [ ] two reactants claiming one transformed product 不进入 strict；
- [ ] forbidden 2OG→hydroxyproline 不进入 snapshot strict；
- [ ] public `SnapshotEvidenceItem → build_snapshot` 无法绕过。

### Gate/mutation/report

- [ ] P1-G08 执行新增 fail-closed tests；
- [ ] P1-G09 执行完整 evidence mutations；
- [ ] M25 验证真实 aggregation；
- [ ] M1–M41 全部按正确原因 caught；
- [ ] G03 不再报告 stale `rdkit_absent`；
- [ ] P0 contracts 无回归；
- [ ] P0 Gate 10/10；
- [ ] 全部 tests 零 fail/error/skip/xfail/xpass；
- [ ] fixture 未冒充 real evidence；
- [ ] 冻结设计/ADR 未被修改迁就实现；
- [ ] legacy/benchmark/core 未写入；
- [ ] 未删除或覆盖用户文件；
- [ ] 未经授权未安装依赖或联网；
- [ ] 提交统计来自当前工作树实际运行；
- [ ] P2 保持 BLOCKED。

---

## 15. 允许的最终提交结尾

### 15.1 内部 Critical 修完，但外部资源仍阻断

`SUBMISSION_TO_CHATGPT_P1_ROUND_3.md` 必须以：

```text
READY_FOR_CHATGPT_P1_ROUND_3_READ_ONLY_AUDIT
P1 SCIENTIFIC GATE BLOCKED — EXTERNAL INPUTS REQUIRED
P2 BLOCKED pending ChatGPT re-audit
```

结尾。

### 15.2 如果任何内部反例仍失败

必须诚实写：

```text
NOT_READY_FOR_CHATGPT_P1_AUDIT
P1 IMPLEMENTATION REMEDIATION INCOMPLETE
P2 BLOCKED
```

不得提交“implementation complete”。

### 15.3 禁止自行宣布

不得写：

```text
P1 accepted
P1 finally accepted
P2 authorized
P2 unblocked
system reliably predicts X→Y
production ready
```

即使自测全部通过，也只能提交给 ChatGPT 只读复审。

---

## 16. 最终科学验收语义

本任务不是追求更多绿色测试，而是保证：

```text
真实完整反应
→ 完整 participants/cofactors/small molecules 保留
→ formal atom mapping 可追溯
→ 正确解析同一反应中的 transformed A→B lineage
→ mapping/lineage/ledger/provenance 全部冻结且可重放
→ 任何矛盾、模糊、未解析或引用错误的证据不能进入 strict
→ 后续 P2 才能把可信 donor transform 用于 X→Y 类比
```

以下任何一项仍存在，都必须阻止 P1 implementation completion：

```text
科学证据字段改变但 snapshot hash 不变
完整 decision/quarantine 无法从 snapshot 重放
低 mapping coverage 仍 strict
ambiguous formal assignment 仍 strict
mapping pair 引用不存在 participant/atom map 仍 strict
unresolved/partial lineage 仍 strict
lineage 没有 formal mapping 支持仍 strict
两个 reactants 错误竞争同一个 transformed product 仍 strict
2OG→hydroxyproline 可进入 snapshot strict
fixture 被称作 real evidence
BLOCKED 掩盖 implementation FAIL
```

请先完成所有可内部修复的 Critical，再诚实保留真实 source、真实 mapper 和独立 manual audit 的外部 blocker。
