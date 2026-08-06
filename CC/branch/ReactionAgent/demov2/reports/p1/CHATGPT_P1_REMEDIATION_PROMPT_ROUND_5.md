# P1 Round 5 严格整改任务书

> **交付对象：** 任意新的 AI coding agent（Claude、Qwen、Codex 等）  
> **项目根目录：** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`  
> **依据：** ChatGPT 对 `SUBMISSION_TO_CHATGPT_P1_ROUND_4.md` 的独立只读审核  
> **本轮性质：** P1 内部科学正确性整改，不是 P2 开发  
> **最终验收人：** ChatGPT  
> **日期：** 2026-07-31

---

## 0. 正式结论

Round 4 未通过 ChatGPT 审核。

当前正式状态：

```text
CHATGPT_P1_ROUND_4_AUDIT = REJECTED_REMEDIATION_REQUIRED
P1_IMPLEMENTATION_STATUS = INCOMPLETE
P1_SCIENTIFIC_GATE_STATUS = NOT_READY_FOR_CHATGPT_AUDIT
P2_STATUS = BLOCKED
```

Round 4 的实际进展必须承认并保留：

- Round 3 complete canonical snapshot/hash/loader 方案保持正确；
- R4-01–R4-14 原始反例已经修复；
- G08 mandatory-node 机制已经真实接线；
- G09 mandatory-node 机制已经真实接线；
- M1–M56 按现有定义全部 caught；
- stale `rdkit_absent` 已从当前权威 evidence 清除；
- P0 Gate 仍为 10/10；
- 724 tests 可独立复现为全绿。

但 Round 4 仍有内部 implementation failure：

- ledger reference integrity 只验证了少数 participant ID；
- atom-map references、side、reactant/product entries、removed sinks、cofactor/mechanistic refs 未完整验证；
- negative element counts 仍可进入 strict；
- partial/unbalanced ledger 被错误 quarantine；
- participant map uniqueness 仍信任自报；
- embedded duplicate lineage IDs 和语义重复 lineage content 可绕过；
- public snapshot API 仍可把 dangling atom-source map 写入 strict lane；
- G08 mandatory manifest 没覆盖这些任务书明确要求的 invariants。

因此，Round 4 审核后的正确 Gate 矩阵至少应是：

| Gate | Round 4 审核结论 |
|---|---:|
| P1-G01 | PASS |
| P1-G02 | PASS |
| P1-G03 | BLOCKED |
| P1-G04 | BLOCKED |
| P1-G05 | PASS |
| P1-G06 | PASS |
| P1-G07 | PASS |
| P1-G08 | **FAIL** |
| P1-G09 | PASS |
| P1-G10 | BLOCKED |

正确统计：

```text
6 PASS
1 FAIL
3 BLOCKED
```

本轮的唯一目标是：

```text
修复剩余 strict scientific boundary
→ 扩展 G08 mandatory coverage
→ 增加 M57–M72
→ 保持所有已通过内容无回退
→ 重新提交 ChatGPT 只读审核
```

P2 继续 BLOCKED。

---

## 1. 你的角色和工作方式

你是 P1 Round 5 remediation implementer。

必须按以下顺序执行：

```text
完整阅读指定材料
→ 记录工作区和可复现基线
→ 独立复现本任务书中的 fail-open
→ 先写 RED tests
→ 证明 RED tests 修复前失败
→ 做最小、集中、fail-closed 的实现
→ 扩展 G08 mandatory node manifest
→ 增加 M57–M72
→ 完整回归
→ 重新生成 Gate/evidence/worklog
→ 生成 Round 5 提交材料
→ P2 保持 BLOCKED
```

本轮要遵守：

- 只改与确认问题直接相关的代码；
- 不重写已经正确的 snapshot canonicalization；
- 不重写 Gate 框架；
- 不重构无关模块；
- 不用修改报告掩盖实现问题；
- 不用宽松 fixture 让测试变绿；
- 不使用字符串关键词猜测化学语义；
- 不把 synthetic fixture 冒充真实 evidence；
- 不自行宣布 P1 accepted；
- 不启动 P2。

---

## 2. 用户的核心科学目标

最终系统必须可靠完成：

```text
完整 donor reaction A→B
        +
与 query X 结构相似的 donor A
        +
经过验证的 transformed lineage 与 reaction delta
        ↓
类比推断 X→Y
```

关键原则：

1. `A→B` 是同一完整反应中的 resolved transformed lineage；
2. 不允许分别检索 A 和 B 后拼接；
3. 辅酶、共底物、小分子、coproduct 必须保留在 complete reaction；
4. COFACTORS 只能作为 role/retrieval prior，不能作为删除规则；
5. source reaction ledger 是 donor 事实；
6. candidate analogy ledger 是 X→Y 类比假设；
7. donor cofactor/stoichiometry 不等于 X→Y 已被证明使用相同条件；
8. strict donor truth 必须没有悬空引用、映射矛盾、身份歧义或自报但无内容支持的 completeness。

本轮所有整改都服务于最后一条。

---

## 3. 开工前必须完整阅读

不要只读提交封面。

### 3.1 冻结设计和计划

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_design.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_plan.md
```

### 3.2 Round 3–5 审核链

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_3.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_3.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_4_FOR_CLAUDE.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_4.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_4_AUDIT_EVIDENCE.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_5.md
```

### 3.3 当前 Gate、worklog 和证据

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/mutation_results.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/eligibility_semantic_invariant_results_round_4.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results_round_4.json
```

### 3.4 必须审查的实现

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/eligibility/engine.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/loader.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/ledger.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/mapping.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/p1_entities.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_gate.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_mutations.py
```

### 3.5 必须扩展的 tests

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_cross_invariants.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_fail_closed.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_engine.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_complete_evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_nested_evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_builder.py
```

---

## 4. 工作区和授权边界

### 4.1 开工前记录

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
git status --short
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
.venv/bin/python --version
.venv/bin/python -c "import rdkit; print(rdkit.__version__)"
```

工作区是 dirty，包含用户和前几轮模型修改。

必须：

- 不清理工作区；
- 不执行 `git reset --hard`；
- 不执行 `git checkout -- <path>`；
- 不删除用户文件；
- 不覆盖无关修改；
- 不改 legacy source；
- changed-files 区分本轮修改和开工前已有修改。

### 4.2 禁止修改

未经用户明确授权，不得修改：

```text
plan/final_design.md
plan/final_plan.md
P0 contracts
P0 ADR
P0 Gate 语义
legacy source
P2–P6 implementation
```

不得通过修改冻结设计来迁就当前代码。

### 4.3 依赖和网络

未经用户明确授权：

- 不安装依赖；
- 不升级依赖；
- 不联网；
- 不下载反应数据；
- 不调用外部 mapper；
- 不伪造真实 source；
- 不伪造第二 annotator。

RDKit 当前已安装，不要重复处理 `rdkit_absent`。

---

## 5. 必须保留的 Round 3/4 正确实现

本轮不是重写任务。

### 5.1 Complete canonical snapshot

继续保留：

```jsonc
{
  "reaction_evidence": "<complete canonical ReactionEvidence>",
  "source_ledger": "<complete external SourceReactionLedger or null>",
  "resolved_lineages": ["<complete typed lineage>"],
  "eligibility_decision": "<complete EligibilityDecision>",
  "quarantine_record": "<complete QuarantineRecord or null>",
  "lane": "<production|research_diagnostic|quarantine>"
}
```

继续满足：

- complete typed object canonicalization；
- 唯一 centralized exclusion 为 circular `snapshot_id`；
- builder/writer/loader 共用 canonical payload；
- complete decision/quarantine/lane 进入 hash；
- external source ledger 为 authority；
- embedded/external ledger 不一致时 fail closed；
- loader 重算 hash 并拒绝 tamper；
- public snapshot API 重新执行 authoritative eligibility。

### 5.2 R4-01–R4-14

继续保留：

- participant mapped_fraction threshold；
- actual formal-pair coverage；
- forward/reverse mapping uniqueness；
- fully-balanced explicit element imbalance quarantine；
- explicit ReactionEvidence quarantine 优先；
- ambiguity_sets fail closed；
- embedded/external lineage ID mismatch fail closed；
- controlled direction；
-现有 ghost-participant checks；
- generic unknowns fail closed；
- duplicate external lineage basic check；
-三条 public snapshot boundary tests。

### 5.3 G08/G09 mandatory-node 机制

继续保留：

- pytest JSON report；
- explicit node IDs；
- missing mandatory node → Gate FAIL；
- skipped/xfail/xpass → Gate FAIL；
- M56a/M56b deletion/shadow protection。

### 5.4 stale evidence

当前权威 evidence 已正确表达：

```text
RDKit available
G03 blocker = real source/proline-2OG record missing
G04 blocker = RealMapperAdapter skeleton
G10 blocker = independent annotation not produced
```

不得重新引入 stale `rdkit_absent`。

---

## 6. ChatGPT 独立复现的剩余 fail-open

以下对象均能通过当前 schema。

ChatGPT 独立调用：

```python
decide_eligibility(evidence, ledger, lineages)
```

并对代表性反例运行：

```text
SnapshotEvidenceItem
→ build_snapshot(...)
→ records.jsonl lane
```

### 6.1 对抗探针结果

| 编号 | Schema-valid 反例 | 当前错误结果 |
|---|---|---|
| R5-01 | AddedAtomSource participant=`r1` 存在，但 atom_map_number=999 不存在 | `strict_eligible` |
| R5-02 | `reactant_entries[]` 引用 ghost participant | `strict_eligible` |
| R5-03 | `product_entries[]` 引用 ghost participant | `strict_eligible` |
| R5-04 | stoichiometry 引用真实 r1，但 side 错写 product | `strict_eligible` |
| R5-05 | stoichiometric coefficient=-2 | `strict_eligible` |
| R5-06 | FormalAtomTransfer 两端 participant 存在，但 source/target side 反转且 map=999 | `strict_eligible` |
| R5-07 | RemovedAtomSink 引用 ghost participant/map | `strict_eligible` |
| R5-08 | CofactorChange 引用 ghost participant | `strict_eligible` |
| R5-09 | MechanisticOriginEvidence 引用 ghost participant/map | `strict_eligible` |
| R5-10 | ElementBalance 的 reactant/product count 为负，delta=0 | `strict_eligible` |
| R5-11 | partial/unbalanced ledger 的一致 non-zero delta | 错误 `quarantine`，reason 还声称 fully-balanced |
| R5-12 | participant 内 atom_map_numbers=[1,1,2]，summary 自报 uniqueness=True | `strict_eligible` |
| R5-13 | side=`middle` 的 participant，empty maps，mapped_fraction=1.0 | `strict_eligible` |
| R5-14 | 同 participant 同时有互相矛盾的 role assignments | `strict_eligible` |
| R5-15 | embedded lineage IDs 重复，但 set 后与 external IDs 一致 | `strict_eligible` |
| R5-16 | 相同 lineage edge/maps，仅 map 顺序从 [1,2] 改为 [2,1] | `strict_eligible` |

### 6.2 Public snapshot API 绕过

以下对象：

```text
AddedAtomSource(
    source_participant_id="r1",
    atom_map_number=999
)
```

其中 participant 存在，但 atom map 不存在。

当前通过：

```text
SnapshotEvidenceItem
→ build_snapshot
→ records.jsonl
```

得到：

```text
lane = "strict"
```

因此不能只修 direct decision helper，必须证明 public snapshot path 无法提升这些反例。

---

## 7. Critical-4A：完整 ledger participant/map reference integrity

当前 `engine.py` 只检查了少数 participant ID。

本轮必须建立一个集中、可复用、最小的 cross-object validator。

可以在 `engine.py` 中新增小 helper，例如：

```python
_validate_participant_registry(...)
_validate_ledger_references(...)
_validate_mapping_registry(...)
```

不要创建新框架；helper 只为去除重复和保证一致性。

### 7.1 Participant registry

在 strict 前建立：

```text
participant_by_id
reactant participant IDs
product participant IDs
reactant map registry
product map registry
maps by participant
```

必须验证：

1. participant ID 非重复；
2. participant side 在受控词表：

```text
reactant
product
```

3. 同一 participant 内 atom map number 不重复；
4. 同一 side 上 atom map number 不得被不同 participant 重复声明；
5. `mapped_fraction` 与可验证 map evidence 不矛盾；
6. 无法证明合法的 participant 状态不得 strict。

注意：

- reactant 和 product 两侧允许同一个 formal map number，因为 formal mapping 连接两侧；
-冲突检查是同一 side 内唯一；
-不要将全部 maps 扁平化后错误禁止 reactant/product 对应使用同一 map。

### 7.2 Reactant/product entries

验证：

```text
ledger.reactant_entries[]
ledger.product_entries[]
```

要求：

- participant 存在；
- reactant entry 的 participant.side == reactant；
- product entry 的 participant.side == product；
- entry.side 与 collection 和 participant side 一致；
- coefficient 必须为正；
- duplicate/conflicting entry fail closed；
-不得接受 ghost participant。

本轮不要求强制非空；现有合法 strict fixtures 可能仍使用空 entries。只验证已提供内容。

### 7.3 Stoichiometry

验证：

```text
ledger.stoichiometry[]
```

要求：

- participant 存在；
- side 与 participant side 一致；
- coefficient > 0；
-同一 participant/side 的互相冲突条目不得 strict；
-不能只检查 participant ID。

### 7.4 Role assignments

验证：

```text
ledger.role_assignments[]
```

要求：

- participant 存在；
-同一 participant 的 mutually contradictory assignments 不得在没有 typed ambiguity authority 时进入 strict；
- exact duplicates 不得静默重复计数；
- transformed_substrate 与 resolved reactant lineage 一致；
- transformed_product 与 resolved product lineage 一致；
-如果角色与 side/lineage 冲突，fail closed；
- cofactor/carrier/catalytic role 的兼容性必须依据冻结词表，不得凭字符串猜测。

不要把 `role_hypotheses` 与 authoritative `role_assignments` 混为一谈。

### 7.5 Cofactor changes

验证：

```text
ledger.cofactor_changes[]
```

要求：

- participant 存在；
-不得引用 ghost participant；
-如果 direction=unknown，继续使用已有 conditional policy；
-未知 direction 不能通过非空字符串绕过；
-不要把 donor cofactor change 变成 X→Y proven fact。

### 7.6 AddedAtomSource

验证：

```text
ledger.added_atom_sources[]
```

至少要求：

- source_participant_id 存在；
- atom_map_number 在可验证的 participant/mapping registry 中存在；
- map 与 declared source participant 一致；
-如果 `mechanistic_evidence_id` 非空，必须解析到已有 mechanistic evidence；
- `"unknown_source"` 继续不得 strict；
-任意其他 ghost participant/map 同样不得 strict。

不得只验证 source participant ID。

### 7.7 RemovedAtomSink

验证：

```text
ledger.removed_atom_sinks[]
```

至少要求：

- sink_participant_id 存在；
- atom_map_number 存在于可验证 registry；
- map 与 sink/transfer 语义不矛盾；
- ghost sink 或 ghost map 不得 strict。

如果当前 schema 无法证明 sink 与哪个 participant/map authority 对应：

```text
strict fail closed
并在 worklog 明确 schema limitation
```

不要默认放行。

### 7.8 FormalAtomTransferAssignment

验证：

```text
source_participant_id
target_participant_id
transferred_atom_map_numbers
assignment_method
```

要求：

- source/target participant 存在；
- source side 和 target side 符合 frozen formal transfer semantics；
- transferred maps 存在；
- transferred maps 与 formal mapped pairs 一致；
-不得与 MappingReport formal assignment 冲突；
- empty/unknown/uncontrolled assignment method 不得 strict；
- participant 存在但 map=999 仍必须失败。

### 7.9 MechanisticOriginEvidence

继续保持：

```text
formal mapping ≠ mechanistic origin
```

验证：

- evidence_id 唯一；
- source_participant_id 非空时 participant 必须存在；
- target_atom_map_numbers 能在 product/map registry 中解析；
- AddedAtomSource.mechanistic_evidence_id 必须引用已有 evidence_id；
- generic mapper 不得自动生成 mechanistic proof；
- ghost participant/map/evidence ID 不得 strict。

---

## 8. Critical-4B：element balance 语义修复

当前 `_element_balance_contradiction()` 有两个问题：

1. 不拒绝负 counts；
2. 对所有 balance status 无条件要求 delta=0。

### 8.1 所有 ledger 都必须满足的结构一致性

对每个 `ElementBalance`：

```text
reactant_count >= 0
product_count >= 0
delta == product_count - reactant_count
element key 唯一
```

任何违反都是内部数据矛盾。

### 8.2 Fully balanced 额外要求

只有当：

```text
ledger.balance_status == fully_balanced_explicit_reaction
```

才额外要求：

```text
delta == 0
```

如果 fully-balanced 自报与 non-zero delta 冲突：

```text
quarantine
```

### 8.3 Partial/unbalanced 正确语义

如果：

```text
balance_status == partial_or_unbalanced_source
reactant_count=2
product_count=3
delta=1
```

并且：

```text
delta == product_count-reactant_count
```

这不是“fully-balanced contradiction”。

它仍然：

-不得 strict；
-应走已有 partial/diagnostic/fail-closed policy；
-不能仅因 non-zero delta 被 quarantine；
-reason 不能谎称 fully-balanced。

### 8.4 Stoichiometric counts

对：

```text
reactant_entries
product_entries
stoichiometry
```

要求 coefficient > 0。

因为 side 已独立表达方向，负 coefficient 在当前 schema 语义下没有 authority，不得 strict。

---

## 9. Critical-4C：map uniqueness 必须由内容推导

当前代码仍信任：

```text
MappingReport.map_number_uniqueness = True
```

本轮必须从 participant 和 formal pair 内容独立验证。

### 9.1 Participant-level uniqueness

拒绝：

```text
participant.atom_map_numbers = [1, 1, 2]
```

即使 summary 自报：

```text
map_number_uniqueness = True
```

### 9.2 Same-side global uniqueness

拒绝：

```text
reactant r1 declares map 1
reactant r2 also declares map 1
```

除非 schema 中存在明确 typed authority；当前没有。

Product side 同理。

### 9.3 Formal-pair consistency

继续保留 Round 4 已正确实现的：

- one source → one target；
- one target ← one source；
- exact duplicate pair rejection；
- pair participant exists；
- pair side correct；
- pair map belongs to participant；
- actual pair coverage。

新增检查不得破坏这些规则。

### 9.4 Empty map lists

不要简单规定所有 participant 都必须有 heavy-atom maps，因为质子/电子政策可能产生零 heavy-atom participant。

正确做法：

-先验证 side vocabulary；
-使用现有 heavy-atom/mapping evidence；
-如果 schema 无法证明一个含重原子的 molecule 合法无 maps，strict fail closed；
-如果无法在不引入新 parser 的情况下可靠判断，明确记录 schema limitation；
-不得让 `side="middle"` + empty maps + mapped_fraction=1.0 进入 strict。

---

## 10. Critical-4D：lineage duplicate canonicalization

### 10.1 Embedded IDs

禁止在验证唯一性之前直接：

```python
set(reaction_evidence.resolved_transformed_lineages)
```

必须先验证原始列表：

```text
len(ids) == len(set(ids))
```

如果 embedded IDs 重复：

```text
never strict
```

然后再比较 embedded/external ID 集合。

### 10.2 External typed lineage IDs

继续要求：

- lineage_id 唯一；
- participant edge 合法；
- resolution_quality resolved；
- ambiguity none；
- transformed maps 被 formal mapping 支撑。

### 10.3 Scientific content signature

当前 duplicate content 使用：

```python
tuple(transformed_atom_maps)
```

导致：

```text
[1,2]
[2,1]
```

被视为不同。

如果 transformed maps 是集合语义，应使用 canonical signature：

```text
reactant_participant_id
product_participant_id
sorted unique transformed_atom_maps
```

并拒绝：

- maps 内部重复；
- map 顺序变化形成的语义重复 lineage；
-相同 edge/maps 用不同 lineage_id 重复计数。

如果认为 map 顺序具有科学语义，必须指出冻结 schema/design 中的明确 authority。没有 authority 时，按集合语义 fail closed。

---

## 11. 必须先写的 RED tests

优先扩展：

```text
tests/p1/test_eligibility_cross_invariants.py
```

如文件过大，可新增：

```text
tests/p1/test_eligibility_reference_integrity.py
```

但 G08 必须显式接入新增文件和 mandatory nodes。

### 11.1 Ledger reference tests

至少新增：

```text
test_added_atom_source_existing_participant_unknown_map_never_strict
test_reactant_entry_ghost_participant_never_strict
test_product_entry_ghost_participant_never_strict
test_reactant_entry_wrong_side_never_strict
test_product_entry_wrong_side_never_strict
test_stoichiometry_existing_participant_wrong_side_never_strict
test_negative_stoichiometric_coefficient_never_strict
test_formal_transfer_existing_participants_wrong_sides_never_strict
test_formal_transfer_unknown_map_never_strict
test_formal_transfer_conflicts_with_formal_pairs_never_strict
test_removed_atom_sink_ghost_participant_never_strict
test_removed_atom_sink_unknown_map_never_strict
test_cofactor_change_ghost_participant_never_strict
test_mechanistic_evidence_ghost_participant_never_strict
test_mechanistic_evidence_unknown_target_map_never_strict
test_added_atom_mechanistic_evidence_id_must_resolve
test_contradictory_role_assignments_never_strict
```

### 11.2 Element/stoichiometry tests

```text
test_negative_element_reactant_count_never_strict
test_negative_element_product_count_never_strict
test_element_delta_must_equal_product_minus_reactant
test_fully_balanced_nonzero_delta_routes_to_quarantine
test_partial_consistent_nonzero_delta_not_mislabeled_quarantine
test_partial_consistent_nonzero_delta_never_strict
```

### 11.3 Participant/map registry tests

```text
test_duplicate_participant_id_never_strict
test_uncontrolled_participant_side_never_strict
test_duplicate_atom_map_within_participant_never_strict
test_same_side_cross_participant_atom_map_collision_never_strict
test_reactant_product_matching_map_number_remains_valid
```

最后一个是正向保护测试，防止错误地把 reactant/product 两侧合法对应 map 当成冲突。

### 11.4 Lineage tests

```text
test_duplicate_embedded_lineage_ids_never_strict
test_duplicate_lineage_content_with_reordered_maps_never_strict
test_duplicate_transformed_maps_within_lineage_never_strict
```

### 11.5 Public snapshot boundary

至少新增：

```text
test_public_snapshot_cannot_promote_added_atom_unknown_map
test_public_snapshot_cannot_promote_ledger_ghost_entry
test_public_snapshot_cannot_promote_formal_transfer_map_conflict
test_public_snapshot_cannot_promote_duplicate_participant_map
test_public_snapshot_cannot_promote_embedded_duplicate_lineage
```

每个 public test 必须读取真实生成的：

```text
records.jsonl
production_index
diagnostic_index
quarantine_index
```

不能只检查 direct decision。

### 11.6 RED test 质量要求

每个 negative test 必须：

1. 从真正 `strict_eligible` 的 baseline 开始；
2. 先 assert baseline strict；
3. 只修改一个目标条件；
4. assert 结果不是 strict；
5. assert reason 含 invariant-specific token；
6.适用时 assert 正确 lane；
7.不能因为另一个 unrelated blocker “碰巧不 strict”；
8.保留正向 valid tests，防止全拒绝式修复。

---

## 12. 新增 mutations：M57–M72

保留并运行：

```text
M1–M56
```

新增：

| Mutation | 目标反例 | 必须捕获 |
|---|---|---|
| M57 | AddedAtomSource participant 存在但 atom map 不存在 | never strict；public lane 非 strict |
| M58 | reactant_entries ghost/wrong-side | never strict |
| M59 | product_entries ghost/wrong-side | never strict |
| M60 | stoichiometry wrong-side / coefficient≤0 / contradictory role assignment | never strict |
| M61 | FormalAtomTransfer endpoints 存在但 side 反转 | never strict |
| M62 | FormalAtomTransfer transferred map 不存在或与 formal pairs 冲突 | never strict |
| M63 | RemovedAtomSink ghost participant/map | never strict |
| M64 | CofactorChange ghost participant | never strict |
| M65 | MechanisticOriginEvidence ghost participant/map/evidence linkage | never strict |
| M66 | negative element counts | never strict |
| M67 | partial ledger 的一致 non-zero delta | 非 strict但不能误 quarantine/不能谎称 fully-balanced |
| M68 | participant 内 duplicate atom map | never strict |
| M69 | same-side cross-participant map collision | never strict |
| M70 | duplicate participant ID 或 uncontrolled participant side | never strict |
| M71 | duplicate embedded lineage IDs | never strict |
| M72 | reordered-map semantic duplicate lineage；代表性 public API 防绕过 | never strict；public lane 非 strict |

允许 M60/M65/M70/M72 使用子结果：

```text
M60a/M60b/M60c
M65a/M65b/M65c
M70a/M70b
M72a/M72b
```

但总 mutation authority 仍按 M1–M72 报告，并在结构化 evidence 中保留 sub-results。

Mutation runner 要求：

-临时目录或可逆 monkeypatch；
-不得破坏真实工作区；
-每项从真实 strict baseline 开始；
-每项只改变目标条件；
-记录 expected；
-记录 actual；
-记录 invariant-specific reason；
- unrelated failure 不算 caught；
- M1–M56 不得回退；
- M56a/M56b 继续证明 Gate deletion protection。

建议输出：

```text
reports/p1/eligibility_reference_integrity_results_round_5.json
reports/p1/eligibility_semantic_invariant_results_round_5.json
reports/p1/gate_false_positive_mutation_results_round_5.json
reports/p1/mutation_results.json
```

---

## 13. G08 mandatory-node manifest 必须扩展

Round 4 的 mandatory-node mechanism 是正确的，保留它。

本轮必须：

1. 保留现有 20 个 G08 mandatory nodes；
2. 加入本轮所有 ledger/map/element/lineage RED tests；
3. 如果新增 test 文件，G08 显式运行；
4. 将关键节点加入 `_G08_REQUIRED_NODES`；
5. missing file/node → G08 FAIL；
6. failed/skipped/xfail/xpass → G08 FAIL；
7.报告实际 collected/passed mandatory nodes；
8. G08 不能只报告总数量；
9.新增 Gate mutation，证明至少一个 Round 5 node 缺失会 FAIL；
10. G08 implementation failure 不能被 G03/G04/G10 BLOCKED 掩盖。

关键区别：

```text
M56 证明“已列节点不能删除”
Round 5 必须同时证明“列表覆盖完整任务要求”
```

不能只把新增 tests 放进 full suite 而不进入 G08 mandatory manifest。

---

## 14. G09 和 snapshot 要求

G09 当前 complete canonical/hash/tamper 接线已通过。

本轮：

-不重写 G09；
-不改 canonical snapshot payload；
-不删 11 个 mandatory nodes；
-保留 M56b；
-只为 public boundary 新增必要测试；
-如果 public boundary tests 放在 snapshot suite，必须决定由 G08 或 G09 哪个 Gate authority 执行，并明确记录；
- eligibility semantic failure 主要归 G08；
- snapshot hash/reproducibility 主要归 G09。

正确实现应：

```text
faithfully持久化正确 decision
```

而不是 faithfully 持久化错误 strict decision。

---

## 15. TDD 执行顺序

### R5-T1：冻结基线

运行并记录：

```text
contracts
tests/p1
full tests
P0 Gate
P1 Gate
M1–M56
```

### R5-T2：复现 ChatGPT 反例

在不修代码时运行 §6 反例，保存精简 RED evidence：

```text
case
schema-valid input
expected
actual
reason/lane
```

### R5-T3：Participant/map registry RED

先加入：

- participant ID/side；
- within-participant map duplicate；
- same-side map collision；
- reactant/product positive map correspondence。

确认 RED。

### R5-T4：Ledger references RED

加入 entries、stoich、role、cofactor、added/removed、formal/mechanistic tests。

确认 RED。

### R5-T5：Element/partial policy RED

加入 negative counts 和 partial nonzero-delta classification tests。

确认 RED。

### R5-T6：Lineage canonical duplicate RED

加入 embedded duplicates 和 reordered maps tests。

确认 RED。

### R5-T7：最小实现

集中实现 participant/map registries 和 ledger reference validator。

不要散落几十个不一致的 if。

### R5-T8：Public API boundary

运行 public snapshot tests，确保 bad record 不进入 strict。

### R5-T9：Gate/mutations

-扩展 G08 required nodes；
-实现 M57–M72；
-保留 M1–M56。

### R5-T10：完整回归

运行所有 tests/Gates/mutations。

### R5-T11：报告和提交

更新 worklog，生成 Round 5 evidence 和 submission。

---

## 16. 必须运行的验收命令

项目根目录：

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
```

### 16.1 定向 strict tests

```bash
.venv/bin/python -m pytest \
  tests/p1/test_eligibility_cross_invariants.py \
  -q
```

如新增 reference-integrity 文件：

```bash
.venv/bin/python -m pytest \
  tests/p1/test_eligibility_reference_integrity.py \
  -q
```

### 16.2 Snapshot tests

```bash
.venv/bin/python -m pytest \
  tests/p1/test_snapshot_builder.py \
  tests/p1/test_snapshot_nested_evidence.py \
  tests/p1/test_snapshot_complete_evidence.py \
  -q
```

### 16.3 P1 tests

```bash
.venv/bin/python -m pytest tests/p1 -q
```

### 16.4 Contracts

```bash
.venv/bin/python -m pytest tests/contracts -q
```

### 16.5 Full suite

```bash
.venv/bin/python -m pytest tests -q
```

必须报告：

- collected；
- passed；
- failed；
- errors；
- skipped；
- xfailed；
- xpassed。

### 16.6 P0 Gate

```bash
.venv/bin/python scripts/run_p0_gate.py
```

必须保持：

```text
10/10 PASS
READY_FOR_CHATGPT_AUDIT
```

### 16.7 P1 mutations

```bash
.venv/bin/python scripts/run_p1_mutations.py
```

必须：

```text
M1–M72 全部被各自预期 invariant 捕获
```

### 16.8 P1 Gate

```bash
.venv/bin/python scripts/run_p1_gate.py
```

内部修复完成后的合理预期：

```text
G01 PASS
G02 PASS
G03 BLOCKED
G04 BLOCKED
G05 PASS
G06 PASS
G07 PASS
G08 PASS
G09 PASS
G10 BLOCKED

7 PASS / 0 FAIL / 3 BLOCKED
overall = BLOCKED
```

只允许因真实外部输入缺失而 BLOCKED。

### 16.9 Mandatory node deletion protection

使用临时副本或可逆 mutation：

```text
缺 Round 4 G08 mandatory node → G08 FAIL
缺 Round 5 G08 mandatory node → G08 FAIL
缺 G09 mandatory node → G09 FAIL
```

验证后必须恢复，不得破坏真实测试文件。

---

## 17. Gate 聚合规则

继续使用单一 authority。

规则：

```text
implementation_failures 非空
→ FAIL / NOT_READY
```

即使 external_blockers 也存在。

只有：

```text
implementation_failures == []
external_blockers != []
```

才允许：

```text
BLOCKED
```

不得使用：

- G03 external blocker；
- G04 mapper blocker；
- G10 annotator blocker；

掩盖 G08 内部 fail-open。

---

## 18. 必须更新的工作日志

更新：

```text
reports/p1/P1_REMEDIATION_WORKLOG.md
```

追加 Round 5 章节，不改历史。

至少包含：

1. Round 4 rejection；
2.开工 branch/HEAD/status；
3.开工前已有修改；
4. R5-01–R5-16 独立复现；
5. RED tests；
6. RED 运行结果；
7. participant registry policy；
8. map registry/uniqueness policy；
9. reactant/product entry policy；
10. stoichiometry policy；
11. role conflict policy；
12. cofactor reference policy；
13. added/removed atom policy；
14. formal transfer policy；
15. mechanistic evidence policy；
16. element/partial balance policy；
17. lineage canonical duplicate policy；
18. public API boundary results；
19. G08 mandatory nodes 前后对比；
20. M57–M72；
21. M1–M56 regression；
22. tests/contracts；
23. tests/p1；
24. full suite；
25. P0 Gate；
26. P1 Gate；
27. remaining external blockers；
28. dependency/network actions；
29. assumptions/deviations；
30. changed files；
31. P2 BLOCKED。

---

## 19. Round 5 必须生成的提交材料

### 19.1 提交封面

生成：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_5.md
```

### 19.2 结构化证据

生成：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_5_AUDIT_EVIDENCE.json
```

建议结构：

```jsonc
{
  "round": 5,
  "branch": "...",
  "head": "...",
  "working_tree": "...",
  "python": "...",
  "rdkit": "...",
  "tests": {
    "contracts": {},
    "p1": {},
    "full": {}
  },
  "p0_gate": {},
  "p1_gate": {},
  "round5_adversarial_cases": {
    "R5-01": {},
    "R5-02": {},
    "R5-03": {},
    "R5-04": {},
    "R5-05": {},
    "R5-06": {},
    "R5-07": {},
    "R5-08": {},
    "R5-09": {},
    "R5-10": {},
    "R5-11": {},
    "R5-12": {},
    "R5-13": {},
    "R5-14": {},
    "R5-15": {},
    "R5-16": {}
  },
  "mutations": {
    "total": 72,
    "caught": 72,
    "all_caught": true,
    "sub_results": {}
  },
  "gate_wiring": {
    "g08_round4_nodes_preserved": true,
    "g08_round5_required_nodes": [],
    "g09_nodes_preserved": true,
    "missing_round5_node_causes_fail": true
  },
  "public_snapshot_boundary": {},
  "external_blockers": [],
  "dependency_or_network_actions": [],
  "p2_status": "BLOCKED"
}
```

必须从真实运行产物生成，不能手填与实际不一致的全绿 JSON。

### 19.3 提交封面必须逐项回答

1. branch；
2. HEAD；
3. working tree；
4. changed files；
5. contracts 统计；
6. P1 tests 统计；
7. full tests 统计；
8. P0 Gate；
9. P1 Gate 逐项；
10. M1–M72；
11. Round 3 canonical snapshot 是否保持；
12. R4-01–R4-14 是否无回退；
13. AddedAtomSource map refs 是否验证；
14. reactant_entries refs/side 是否验证；
15. product_entries refs/side 是否验证；
16. stoichiometry refs/side/coefficient 是否验证；
17. role contradictions 是否验证；
18. cofactor refs 是否验证；
19. FormalAtomTransfer side/map/formal-pair consistency 是否验证；
20. RemovedAtomSink refs 是否验证；
21. MechanisticOriginEvidence refs 是否验证；
22. mechanistic evidence ID linkage 是否验证；
23. negative element counts 是否拒绝；
24. partial consistent nonzero delta 是否避免误 quarantine；
25. participant ID uniqueness 是否验证；
26. participant side vocabulary 是否验证；
27. within-participant map uniqueness 是否验证；
28. same-side cross-participant map uniqueness 是否验证；
29. reactant/product 对应 map 是否仍允许；
30. embedded duplicate IDs 是否拒绝；
31. reordered-map lineage duplicate 是否拒绝；
32. public snapshot API 是否不能绕过；
33. G08 Round 4 nodes 是否保留；
34. G08 Round 5 nodes 是否 mandatory；
35.删除 Round 5 node 后 G08 是否 FAIL；
36. G09 nodes 是否无回退；
37. stale RDKit evidence 是否未回归；
38. G03 blocker；
39. G04 blocker；
40. G10 blocker；
41.是否安装依赖；
42.是否联网；
43. synthetic fixtures 的用途和标记；
44. assumptions/deviations；
45. P2 状态。

---

## 20. Round 5 Definition of Done

### 20.1 Ledger references

- [ ] AddedAtomSource participant/map 有效；
- [ ] AddedAtomSource mechanistic ID 可解析；
- [ ] RemovedAtomSink participant/map 有效；
- [ ] reactant entries refs/side/coefficients 有效；
- [ ] product entries refs/side/coefficients 有效；
- [ ] stoichiometry refs/side/coefficients 有效；
- [ ] role assignments 不矛盾；
- [ ] cofactor changes 不悬空；
- [ ] FormalAtomTransfer endpoints/side/maps/formal pairs 一致；
- [ ] MechanisticOriginEvidence refs/evidence IDs 有效；
- [ ] formal mapping 与 mechanistic origin 继续分离。

### 20.2 Element/stoichiometry

- [ ] negative element counts 拒绝；
- [ ] delta/count consistency 验证；
- [ ] duplicate element row 拒绝；
- [ ] fully-balanced nonzero delta quarantine；
- [ ] partial consistent nonzero delta 不误 quarantine；
- [ ] partial 仍不得 strict；
- [ ] coefficient≤0 不得 strict。

### 20.3 Participant/map

- [ ] participant ID 唯一；
- [ ] side vocabulary 受控；
- [ ] participant 内 map 唯一；
- [ ] same-side maps 全局唯一；
- [ ] reactant/product 对应 map 合法；
- [ ] actual coverage 保持；
- [ ] bidirectional pair uniqueness 保持；
- [ ] summary 自报不能覆盖 contradiction。

### 20.4 Lineage

- [ ] embedded raw IDs 先查重复再 set comparison；
- [ ] external IDs 唯一；
- [ ] transformed maps 内部唯一；
- [ ] reordered maps 的语义 duplicate 被捕获；
- [ ] unsupported maps/edges 继续拒绝；
- [ ] ambiguity/resolution rules 保持。

### 20.5 Public API

- [ ] AddedAtomSource ghost map 不进入 strict；
- [ ] ledger ghost entries 不进入 strict；
- [ ] FormalAtomTransfer conflict 不进入 strict；
- [ ] duplicate participant map 不进入 strict；
- [ ] duplicate lineage 不进入 strict。

### 20.6 Gate/mutations

- [ ] G08 原 20 nodes 保留；
- [ ] Round 5 nodes 全部 mandatory；
- [ ] missing Round 5 node → G08 FAIL；
- [ ] G09 11 nodes 保留；
- [ ] M1–M56 无回退；
- [ ] M57–M72 全部目标捕获；
- [ ] implementation FAIL 不被 BLOCKED 掩盖。

### 20.7 Regression/evidence

- [ ] contracts 全绿；
- [ ] P1 tests 全绿；
- [ ] full suite 全绿；
- [ ] zero skip/xfail/xpass；
- [ ] P0 Gate 10/10；
- [ ] current evidence 无 stale RDKit blocker；
- [ ] JSON/Markdown 数字一致；
- [ ] worklog 完整；
- [ ] Round 5 submission 完整；
- [ ] P2 BLOCKED。

---

## 21. 如果发现 schema limitation

不要猜。

按以下规则：

1.先查 final design/plan；
2.复用已有 typed authority；
3.如果现有对象能 cross-validate，做最小验证；
4.如果无法证明 strict 合法，fail closed；
5.在 worklog 说明：

```text
缺少什么 typed authority
为什么现有 schema 无法验证
当前如何 fail closed
未来在哪个阶段解决
```

禁止用：

-关键词匹配；
- fixture-specific ID；
-默认 participant/map；
- test-only bypass；
-报告层 post-processing；
- hard-coded proline/2OG；
- synthetic evidence 冒充 real；

代替真实 invariant。

---

## 22. 允许的最终提交结尾

只有当：

- R5-01–R5-16 全部修复；
- public snapshot boundary 全部通过；
- G08 mandatory manifest 已扩展；
- M1–M72 全部被各自目标 invariant 捕获；
- contracts/P1/full tests 全绿；
- P0 Gate 10/10；
- G08/G09 无内部 failure；
- current evidence 无 stale blocker；

才允许：

```text
READY_FOR_CHATGPT_P1_ROUND_5_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
```

而且这两行必须是：

```text
SUBMISSION_TO_CHATGPT_P1_ROUND_5.md
```

的最后两条状态语句。

如果任何内部反例仍失败：

```text
NOT_READY_FOR_CHATGPT_P1_AUDIT

P2 BLOCKED
```

禁止自行写：

```text
P1 ACCEPTED
P1 COMPLETE
P2 READY
P2 STARTED
ALL GATES PASS
```

---

## 23. 最终科学验收语义

本轮完成后必须能够证明：

```text
participant 存在但 atom map 不存在
不会 strict

participant ID 存在但 side/role/stoichiometry 矛盾
不会 strict

ledger collection 中任何 dangling reference
不会 strict

formal transfer 与 formal mapping 冲突
不会 strict

mechanistic evidence 悬空
不会 strict

负 element count 或不一致 delta
不会 strict

普通 partial imbalance
不会被伪装成 fully-balanced contradiction

self-reported map uniqueness
不能覆盖真实 duplicate maps

embedded/external lineage 的重复和语义重复
不会 strict

上述对象通过 public build_snapshot
也不会进入 strict donor truth
```

请坚持：

```text
先 RED
后最小实现
再 public boundary
再 mandatory Gate
再 mutations
最后完整回归和提交
```

P2 继续等待 ChatGPT 只读审核。
