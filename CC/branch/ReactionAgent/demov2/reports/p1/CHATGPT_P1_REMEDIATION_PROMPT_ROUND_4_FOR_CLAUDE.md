# Claude 执行任务书：P1 Round 4 严格整改

> **交付对象：** Claude  
> **项目根目录：** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`  
> **依据：** ChatGPT 对 `SUBMISSION_TO_CHATGPT_P1_ROUND_3.md` 的独立只读审计  
> **本轮性质：** P1 内部正确性整改，不是 P2 开发  
> **最终复核人：** ChatGPT  
> **日期：** 2026-07-31

---

## 0. 结论先行

Round 3 **不能通过审核**。

当前正式结论是：

```text
CHATGPT_P1_ROUND_3_AUDIT = REJECTED_REMEDIATION_REQUIRED
P1_IMPLEMENTATION_STATUS = INCOMPLETE
P1_SCIENTIFIC_GATE_STATUS = NOT_READY_FOR_CHATGPT_AUDIT
P2_STATUS = BLOCKED
```

ChatGPT 独立复核后的真实 Gate 矩阵应解释为：

| Gate | Round 3 审计结论 | 原因 |
|---|---:|---|
| P1-G01 | PASS | package/runtime/lock 基础要求满足 |
| P1-G02 | PASS | schemas/IDs/P0 contracts 满足 |
| P1-G03 | BLOCKED | 缺真实 reaction source 和指定真实案例；同时存在 stale evidence |
| P1-G04 | BLOCKED | real mapper adapter 尚未完成 |
| P1-G05 | PASS | participant/role 基础验证满足 |
| P1-G06 | PASS | lineage graph 基础验证满足 |
| P1-G07 | PASS | dual-ledger 基础验证满足 |
| P1-G08 | **FAIL** | strict eligibility 仍有多条 fail-open；Gate 也未运行新增 cross-invariant suite |
| P1-G09 | **FAIL** | Gate 未运行 `test_snapshot_complete_evidence.py`；提交材料关于 Gate wiring 的陈述不真实 |
| P1-G10 | BLOCKED | 真实数据与独立人工审核条件未满足 |

因此 Round 3 的正确统计是：

```text
5 PASS
2 FAIL
3 BLOCKED
```

本轮目标不是扩大范围，也不是重写 P1，而是完成以下三项：

1. 修复 strict eligibility 的剩余 fail-open；
2. 让 P1-G08/P1-G09 真正执行并保护新增测试；
3. 从所有当前生成证据中清除已经失效的 `rdkit_absent` blocker。

Round 3 已正确完成的 complete canonical snapshot/hash/loader 工作应保留。

---

## 1. 你的角色

你是本轮 **P1 remediation implementer**。

请按以下顺序工作：

```text
完整阅读指定材料
→ 冻结当前可复现基线
→ 把 ChatGPT 反例转成 RED tests
→ 证明 RED tests 在修复前确实失败
→ 做最小、可解释、fail-closed 的实现
→ 将测试接入正式 Gate
→ 扩展 mutation runner
→ 重新生成机器证据和人类报告
→ 完整回归
→ 生成 Round 4 提交封面
→ 保持 P2 BLOCKED，等待 ChatGPT 只读复核
```

不要：

- 重新设计整个 P1；
- 重写已经通过的 canonical snapshot 方案；
- 用修改报告文本代替修代码；
- 用更宽松的 fixture 让测试变绿；
- 使用字符串关键词猜测科学语义；
- 在内部 implementation failure 尚存在时声称 Gate 只是 BLOCKED；
- 自行宣布 P1 accepted 或启动 P2。

---

## 2. 用户的科学目标不得偏离

系统最终要可靠执行：

```text
完整 donor reaction A→B
        +
与 query X 结构相似的 donor A
        +
经过验证的 transformed lineage 与 reaction delta
        ↓
类比推断 X→Y
```

这里的 `A→B` 必须是同一个完整反应中的真实 transformed lineage，而不是分别找一个 A 和一个 B。

辅酶、共底物、小分子和 coproduct：

- 必须在完整 source reaction 中保留；
- 可以影响角色识别、检索、平衡和解释；
- 不得被当作 primary donor；
- 不得通过静态 `COFACTORS` 表做不可逆删除；
- donor source ledger 不等于 query `X→Y` 已被证明使用同样的辅酶或计量。

P1 strict lane 是后续 P2–P5 的科学数据基础。任何结构合法但科学上矛盾、引用悬空、映射不完备或身份不确定的记录，都不得进入 strict。

---

## 3. 开工前必须完整阅读

必须完整阅读，不得只看摘要。

### 3.1 冻结设计和计划

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_design.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_plan.md
```

### 3.2 上轮任务、提交和证据

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_3.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_3.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_3_AUDIT_EVIDENCE.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
```

注意：`P1_ROUND_3_AUDIT_EVIDENCE.json` 是 Round 3 implementer 生成的提交证据，不等于 ChatGPT 的验收结论。

### 3.3 必须审查的实现

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/eligibility/engine.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/loader.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/mapping.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/ledger.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/p1_entities.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_gate.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_mutations.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/p1_preflight.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/legacy_lineage_audit.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/regenerate_snapshot_sample.py
```

### 3.4 必须审查并扩展的测试

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_engine.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_fail_closed.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_cross_invariants.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_nested_evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_complete_evidence.py
```

### 3.5 必须核对的 stale evidence

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/data_audit/legacy_lineage_audit.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/data_audit/legacy_lineage_audit.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_PREFLIGHT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_PREFLIGHT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/snapshot_build_sample.json
```

---

## 4. 工作区和授权边界

### 4.1 开工记录

开工前记录：

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
git status --short
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
.venv/bin/python --version
```

当前工作区可能包含用户或其他模型尚未提交的修改。

必须：

- 保留现有修改；
- 不清理工作区；
- 不运行 `git reset --hard`；
- 不运行 `git checkout -- <path>`；
- 不删除用户文件；
- 不覆盖与本轮无关的改动；
- changed-files 中区分本轮修改和开工前已存在修改。

### 4.2 禁止修改的范围

未经用户明确授权，不得修改：

```text
plan/final_design.md
plan/final_plan.md
P0 contracts
P0 Gate 语义
P0 ADR
legacy source
P2–P6 实现
```

不得为了让当前实现通过测试而降低冻结设计标准。

### 4.3 依赖和网络

本轮已知 `.venv` 中 RDKit 可用。

未经用户明确授权：

- 不安装依赖；
- 不升级依赖；
- 不联网；
- 不下载真实反应数据；
- 不调用外部 mapper 服务；
- 不伪造第二位 annotator；
- 不把 synthetic fixture 标成 real evidence。

如果发现新的外部 blocker，诚实记录，不要自行扩权。

---

## 5. Round 3 已经正确完成的部分：必须保留

Round 3 的 snapshot canonicalization 基本正确，本轮不得推倒重来。

必须保留以下语义：

```jsonc
{
  "reaction_evidence": "<complete ReactionEvidence except centralized runtime/circular exclusions>",
  "source_ledger": "<complete external SourceReactionLedger or null>",
  "resolved_lineages": ["<complete typed ResolvedTransformedLineage>"],
  "eligibility_decision": "<complete EligibilityDecision>",
  "quarantine_record": "<complete QuarantineRecord or null>",
  "lane": "<production|research_diagnostic|quarantine>"
}
```

必须继续满足：

1. `reaction_evidence` 使用完整 typed object 的 canonical JSON；
2. 唯一集中式 hash exclusion 为循环字段 `snapshot_id`；
3. builder hash、`records.jsonl` writer 和 loader tamper verification 使用同一个 canonical payload；
4. external source ledger 是明确 authority；
5. embedded ledger 与 external ledger 同时存在但不一致时 fail closed；
6. eligibility decision、quarantine record、lane 都进入 hash；
7. loader 重新计算完整 record hash；
8. lane 从 authoritative decision 重新推导并验证；
9. mutation 改变 scientific/audit content 时 hash 改变；
10. snapshot public API 不能绕过 eligibility boundary。

除非新 RED test 证明上述实现仍有具体 bug，否则不要重构：

```text
reaction_agent/snapshot/builder.py::_canonical_record_payload
reaction_agent/snapshot/builder.py::_resolve_ledger_authority
reaction_agent/snapshot/loader.py 的 canonical tamper verification
```

这是本轮“最小、外科式修改”的硬边界。

---

## 6. ChatGPT 独立复现的 Critical-3：strict eligibility 仍 fail-open

Round 3 新增了若干 cross-invariants，但只覆盖了部分关系。

ChatGPT 使用 schema-valid 对象调用：

```python
decide_eligibility(reaction_evidence, ledger, lineages)
```

以下反例全部错误返回：

```text
strict_eligible
```

### 6.1 已确认的 14 个 fail-open

| 编号 | 反例 | Round 3 错误结果 | 正确要求 |
|---|---|---|---|
| R4-01 | participant `mapped_fraction=0.25` | strict | never strict |
| R4-02 | participant 声明 2 个 map，但 formal pairs 只覆盖 1 个；MappingReport 自报 1.0 | strict | never strict |
| R4-03 | 两个 reactant atom 映射到同一个 product atom | strict | never strict |
| R4-04 | `ElementBalance(C, reactant=2, product=3, delta=1)` | strict | quarantine/never strict |
| R4-05 | `AddedAtomSource` 引用 ghost participant/map | strict | never strict |
| R4-06 | `RoleAssignment` 引用 ghost participant | strict | never strict |
| R4-07 | `StoichiometricEntry` 引用 ghost participant | strict | never strict |
| R4-08 | `FormalAtomTransferAssignment` 引用 ghost participant | strict | never strict |
| R4-09 | generic `ledger.unknowns` 含 identity-critical unknown | strict | never strict |
| R4-10 | 重复 lineage ID 和重复 lineage content | strict | never strict |
| R4-11 | `ReactionEvidence.quarantine` 非空 | strict | quarantine |
| R4-12 | `ReactionEvidence.ambiguity_sets` 含 identity-critical tie | strict | never strict |
| R4-13 | embedded lineage IDs 与 external typed lineages 冲突 | strict | never strict |
| R4-14 | `direction="sideways"` | strict | never strict |

### 6.2 public snapshot API 也可被绕过

ChatGPT 还通过：

```text
SnapshotEvidenceItem
→ build_snapshot(...)
→ 读取生成 lane
```

确认以下记录仍被写入 strict/production：

1. 明确存在 non-zero element imbalance 的记录；
2. `ReactionEvidence.quarantine` 已显式标记 quarantine 的记录。

因此不能只在某个私有 helper 上补测试。

必须证明：

```text
public build_snapshot API
也不能把这些反例写入 production strict lane
```

---

## 7. Strict boundary 的完整最小整改要求

本节要求的是 cross-object consistency，不是重新发明反应化学。

实现可以拆成小 helper，但不要创建无必要的框架。

### 7.1 Evidence-level authority

在授予 `strict_eligible` 之前必须验证：

#### A. 显式 quarantine

```text
ReactionEvidence.quarantine is not None
```

必须优先进入 quarantine。

禁止：

- 忽略显式 quarantine；
- 因 ledger 自报 fully balanced 而覆盖 quarantine；
- 先生成 strict decision、再只在报告层附加 quarantine 文本。

#### B. ambiguity sets

当前 `ReactionEvidence.ambiguity_sets` 是：

```python
list[dict[str, str]]
```

它没有足够 typed authority 来证明某个 ambiguity 与 donor identity 无关。

保守规则：

```text
ambiguity_sets 非空
→ 不得 strict
```

如果能从冻结设计和已有 schema 证明已有明确的非 identity-critical typed 分类，可按该类型处理；否则不得使用字符串关键词猜测。

#### C. embedded/external resolved lineage

当前 authoritative lineage 输入是：

```python
list[ResolvedTransformedLineage]
```

`ReactionEvidence.resolved_transformed_lineages` 是 embedded lineage ID 列表。

最小一致性要求：

- external typed lineage ID 唯一；
- exact duplicate lineage content 不得重复；
- embedded ID 列表如果非空，必须与 external typed lineage IDs 一致；
- embedded 列表含未知 ID、缺少 external ID、重复 ID 或冲突时不得 strict；
- 不得静默选择其中一个表示并忽略另一个。

如果 embedded 列表为空而现有冻结设计把 external typed list 定义为 authority，可保留 external authority；必须在代码注释和测试中明确该兼容语义。

#### D. direction

`direction` 目前只是 `NonEmptyStr`，因此：

```text
"sideways"
"foo"
"known-ish"
```

都能通过 schema。

strict 只能接受冻结的受控值。

最小实现建议：

```python
_ALLOWED_STRICT_DIRECTIONS = {"forward", "reverse"}
```

如果项目已存在更严格的受控词表，复用它。`unknown`、空值、可逆但未解析方向以及所有未知字符串都不得进入 directional strict prediction。

不要仅判断：

```python
direction != "unknown"
```

### 7.2 Element/charge balance

当前代码只看：

```python
ledger.charge_balance != 0
```

但不看 `element_balance`。

必须验证每个 `ElementBalance`：

```text
delta == product_count - reactant_count
```

并且在：

```text
balance_status == fully_balanced_explicit_reaction
```

时：

```text
delta == 0
```

还必须拒绝：

- 同一个 element 的重复/互相冲突条目；
- 负的 reactant/product element count；
- count 与 delta 自相矛盾；
- fully balanced 状态与 non-zero element delta 同时出现。

这些属于 explicit scientific contradiction，应使用现有 critical contradiction/quarantine policy，不得只降成普通 warning。

本轮不要求凭空从 SMILES 重建一套新的元素计数引擎；但凡 ledger 已提供 explicit balance，就必须验证，不能信任自报状态。

### 7.3 Mapping coverage 必须由内容支撑

当前实现信任：

```text
MappingReport.mapped_heavy_atom_fraction == 1.0
MappingReport.changed_atom_coverage == 1.0
MappingReport.map_number_uniqueness == True
```

但这些是自报 summary，不能覆盖实际 pair/participant contradiction。

至少必须满足：

1. strict 所涉及 participant 的 `mapped_fraction` 不得低于 strict threshold；
2. participant 声明的 atom maps 必须由 formal mapped pairs 真实覆盖；
3. reactant 侧每个 atom reference 最多映射到一个 product target；
4. product 侧每个 atom target 最多被一个 reactant source 占用；
5. exact duplicate pair 拒绝；
6. 同侧 participant map-number 冲突拒绝；
7. formal pair 中的 participant、side 和 atom map 均存在；
8. lineage transformed maps 继续必须由对应 formal edge 支撑；
9. summary fields 与实际内容矛盾时 fail closed；
10. 不得因为 summary 自报 `1.0/True` 就跳过实际覆盖验证。

特别要修复 Round 3 只做了单向检查的问题：

```text
one reactant atom → two product atoms
```

已经被拒绝，但：

```text
two reactant atoms → one product atom
```

仍被错误接受。

formal strict mapping 必须是可审计的一对一对应，除非 schema 中存在明确、typed、被验证的 split/merge authority。当前没有该 authority，因此必须 fail closed。

如果现有 schema 缺少重建某个百分比所需的分母，不得捏造分母。此时应：

- 验证当前 schema 能证明的内容一致性；
- 对无法证明“完整”的记录 fail closed；
- 在 worklog 记录 schema limitation；
- 不得用自报 summary 替代证据。

### 7.4 Ledger reference integrity

在 strict 前，验证所有可解析的 participant/map references。

至少包括：

#### Participant entries

```text
reactant_entries[].participant_id
product_entries[].participant_id
stoichiometry[].participant_id
role_assignments[].participant_id
cofactor_changes[].participant_id
```

要求：

- participant 存在；
- reactant/product entry 的 side 正确；
- stoichiometric entry 的 side 与 participant side 一致；
- 不允许 ghost participant。

#### Formal atom transfer

```text
formal_atom_transfer_assignments[].source_participant_id
formal_atom_transfer_assignments[].target_participant_id
formal_atom_transfer_assignments[].transferred_atom_map_numbers
```

要求：

- source/target participant 存在；
- side 语义正确；
- transferred maps 能在相应 participant/mapping 中找到；
- 与 formal mapped pairs 不得矛盾。

#### Added/removed atom references

```text
added_atom_sources[]
removed_atom_sinks[]
```

要求：

- participant reference 存在；
- atom map reference 存在于相应可验证对象；
- `"unknown_source"` 继续不得 strict；
- 任意其他 ghost string 也不得因为不等于 `"unknown_source"` 而漏过。

#### Mechanistic references

如果存在：

```text
mechanistic_origin_evidence[]
mechanistic_evidence_id
```

继续遵守 formal mapping 与 mechanistic origin 分离，验证可用的 evidence/participant 引用，不得由 generic mapper 自动生成“mechanistic proof”。

不要构造项目中不存在的全局 registry。对于当前 schema 无法验证的引用，strict 应 fail closed，并在 worklog 中记录缺少的 authority。

### 7.5 Generic unknowns

`SourceReactionLedger.unknowns` 当前是：

```python
list[NonEmptyStr]
```

它没有 typed criticality。

因此禁止使用：

```python
if "critical" in unknown_text
```

或类似关键词匹配。

保守规则：

```text
generic unknowns 非空
→ 不得 strict
```

非关键 cofactor stoichiometry 的 conditional path 已有专用 typed 字段：

```text
cofactor_changes[].direction == "unknown"
```

不要把 generic unknown 自动当成这个专用 conditional case。

### 7.6 Duplicate and contradiction policy

必须拒绝：

- duplicate lineage ID；
- exact duplicate lineage scientific content；
- duplicate exact formal pair；
- reverse-collision formal pair；
- duplicate element balance key；
- mutually contradictory embedded/external representations；
- fully balanced status 与 explicit imbalance 同时出现。

返回 reason 必须：

- 稳定；
- typed；
- 可定位具体 invariant；
- 不包含随机顺序；
- 不把 implementation exception 泄漏成普通用户文案。

---

## 8. 必须先写的 RED tests

优先扩展：

```text
tests/p1/test_eligibility_cross_invariants.py
```

如为清晰性需要，可新增：

```text
tests/p1/test_eligibility_semantic_fail_closed.py
```

但不要复制大量 fixture。复用已有合法 strict baseline helper，或提取一个最小共享 helper。

必须先写并确认修复前失败的测试：

```text
test_participant_low_mapped_fraction_never_strict
test_self_reported_full_mapping_with_incomplete_actual_pair_coverage_never_strict
test_reverse_collision_many_to_one_mapping_never_strict
test_nonzero_element_balance_never_strict
test_element_delta_inconsistent_with_counts_never_strict
test_duplicate_element_balance_entry_never_strict
test_added_atom_source_ghost_reference_never_strict
test_role_assignment_ghost_participant_never_strict
test_stoichiometry_ghost_participant_never_strict
test_formal_atom_transfer_ghost_participant_never_strict
test_generic_unknowns_never_strict
test_duplicate_lineage_id_or_content_never_strict
test_explicit_reaction_evidence_quarantine_routes_to_quarantine
test_identity_ambiguity_set_never_strict
test_embedded_external_lineage_mismatch_never_strict
test_uncontrolled_direction_value_never_strict
```

还必须有 public API tests：

```text
test_public_snapshot_api_cannot_promote_element_imbalance_to_strict
test_public_snapshot_api_cannot_promote_explicit_quarantine_to_strict
test_public_snapshot_api_cannot_promote_mapping_reverse_collision_to_strict
```

测试必须检查：

1. decision 不是 `strict_eligible`；
2. production/strict lane 中不存在该记录；
3. quarantine 语义适用时记录确实进入 quarantine；
4. reason 包含稳定的具体 invariant；
5. 不是仅因另一个无关 baseline blocker 而“碰巧不 strict”。

每个 mutation 的 baseline 必须先证明：

```text
baseline == strict_eligible
```

然后只改变一个字段，证明目标 mutation 自身被捕获。

不得用本来就不 strict 的 fixture 测“never strict”。

---

## 9. 最小实现策略

推荐顺序：

### R4-T1：冻结基线

记录：

- branch/HEAD；
- working tree；
- Python/RDKit；
- contracts/P1/full test counts；
- P0 Gate；
- P1 Gate；
- M1–M41。

### R4-T2：加入 RED tests

先只加测试，不修实现。

保存精简的 RED 证据：

```text
测试名
预期
修复前实际
失败原因
```

不要把几千行 pytest 输出全部复制进报告。

### R4-T3：修 evidence/balance policy

优先修：

- explicit quarantine；
- ambiguity sets；
- controlled direction；
- embedded/external lineage consistency；
- element balance contradiction；
- duplicate lineages。

### R4-T4：修 mapping/ledger cross-invariants

再修：

- participant mapped fraction；
- actual formal pair coverage；
- bidirectional uniqueness；
- ledger participant/map references；
- generic unknowns。

### R4-T5：public snapshot boundary

证明 `SnapshotEvidenceItem → build_snapshot` 会重新执行 authoritative eligibility，并且不会把反例写进 strict lane。

### R4-T6：Gate wiring

将新增测试真正接入 P1-G08/P1-G09。

### R4-T7：mutations

新增 M42–M56，并证明每个 mutation 是由自己的预期失败捕获。

### R4-T8：evidence freshness

修生成器中的 stale runtime 文案，重新生成相关 evidence。

### R4-T9：完整回归和提交

所有内部实现测试通过后，生成 Round 4 证据和提交封面。

---

## 10. P1-G08 Gate wiring 必须修复

Round 3 提交声称：

```text
P1-G08 executes test_eligibility_cross_invariants.py
```

但实际 `scripts/run_p1_gate.py` 只运行：

```python
[
    "tests/p1/test_eligibility_fail_closed.py",
    "tests/p1/test_eligibility_engine.py",
]
```

它没有运行：

```text
tests/p1/test_eligibility_cross_invariants.py
```

ChatGPT 已在隔离副本中移走该文件，G08 仍然：

```text
PASS
37/37
```

这证明当前 G08 是 false-positive-prone。

整改要求：

1. G08 必须显式执行 `test_eligibility_cross_invariants.py`；
2. 如果新增 `test_eligibility_semantic_fail_closed.py`，也必须执行；
3. 必须验证本轮关键 test node 被实际 collection/execution；
4. 缺少必需测试文件或必需 test node 时 G08 必须 FAIL；
5. pytest collection 数下降不能被解释成 PASS；
6. G08 失败不得被 G03/G04/G10 的 BLOCKED 掩盖。

推荐使用明确的 required test manifest 或明确 node IDs，而不是只依赖“某个目录里当前有多少测试”。

最低限度必须覆盖本轮 §8 的所有 strict semantic tests。

---

## 11. P1-G09 Gate wiring 必须修复

Round 3 提交声称：

```text
P1-G09 executes test_snapshot_complete_evidence.py
```

但实际只运行：

```python
[
    "tests/p1/test_snapshot_nested_evidence.py",
    "tests/p1/test_snapshot_builder.py",
]
```

它没有运行：

```text
tests/p1/test_snapshot_complete_evidence.py
```

ChatGPT 在隔离副本中移走该文件后，G09 仍然：

```text
PASS
43/43
```

整改要求：

1. G09 必须显式执行 `test_snapshot_complete_evidence.py`；
2. 缺少该文件或关键 test node 时 G09 必须 FAIL；
3. complete evidence hash/tamper tests 必须属于正式 Gate，而不是只存在于 full suite；
4. public snapshot boundary tests 如果放在 snapshot suite，也必须被 G09 运行；
5. G09 报告必须列出实际运行的文件、collected/passed 数和 mandatory node 结果；
6. 不得只检查预生成 JSON。

注意：Round 3 的 complete canonical snapshot 实现本身基本正确。本节主要修 Gate wiring 和防删除保护，不是要求重写 hash。

---

## 12. 新增 mutation M42–M56

保留并继续运行：

```text
M1–M41
```

新增：

| Mutation | 单一变化 | 必须捕获的失败 |
|---|---|---|
| M42 | fully-balanced ledger 加入 non-zero element delta | never strict / quarantine |
| M43 | `ReactionEvidence.quarantine` 设为非空 | quarantine，不得 production strict |
| M44 | 增加 identity ambiguity set | never strict |
| M45 | embedded lineage ID 与 external lineage 冲突 | never strict |
| M46 | direction 改为 `sideways` | never strict |
| M47 | participant mapped_fraction 改为 0.25 | never strict |
| M48 | 删除一个实际 formal pair，但 summary 保持 1.0/True | never strict |
| M49 | 两个 reactant atom 指向同一 product atom | never strict |
| M50 | AddedAtomSource 指向 ghost participant/map | never strict |
| M51 | RoleAssignment 指向 ghost participant | never strict |
| M52 | StoichiometricEntry 指向 ghost participant | never strict |
| M53 | FormalAtomTransferAssignment 指向 ghost participant | never strict |
| M54 | generic ledger unknowns 加入 identity/source unknown | never strict |
| M55 | 重复 lineage ID/content | never strict |
| M56 | 移除/屏蔽 G08 或 G09 mandatory test 文件/node | 对应 Gate 必须 FAIL |

M56 必须至少包含两个子项：

```text
M56a: G08 mandatory cross-invariant test 缺失 → G08 FAIL
M56b: G09 complete-evidence test 缺失 → G09 FAIL
```

mutation runner 要求：

1. 使用临时目录或可逆 monkeypatch；
2. 不破坏真实工作区；
3. 每个 mutation 从合法 strict baseline 开始；
4. 每个 mutation 只改变一个目标条件；
5. 记录 expected failure；
6. 记录 actual failure；
7. 只有具体目标 failure 出现才算 caught；
8. 不能因 unrelated BLOCKED 算 caught；
9. M1–M41 不能回退；
10. 结果写入结构化 JSON。

建议新增输出：

```text
reports/p1/gate_false_positive_mutation_results_round_4.json
reports/p1/eligibility_semantic_invariant_results_round_4.json
reports/p1/P1_ROUND_4_AUDIT_EVIDENCE.json
```

可以继续由 `reports/p1/mutation_results.json` 汇总 M1–M56，但必须能看到每项的独立 expected/actual/caught。

---

## 13. stale `rdkit_absent` evidence 必须修复

Round 3 提交声称已经移除 stale `rdkit_absent`，但 ChatGPT 找到：

```text
reports/data_audit/legacy_lineage_audit.json
  audit_scope 仍写 rdkit absent

reports/p1/P1_PREFLIGHT.md
  仍列 rdkit_absent blocker

reports/p1/snapshot_build_sample.json
  real_snapshot reason 仍写 Preflight BLOCKED: rdkit absent

reports/p1/P1_GATE_REPORT.json
  G09 real_snapshot_reason 继续继承该 stale reason
```

当前 `.venv` 的真实情况是 RDKit 已安装并可 import。

必须：

1. 修 producer script 中的 stale/hard-coded runtime 文案；
2. 重新运行 runtime probe；
3. 重新生成 JSON 和 Markdown；
4. 重新生成 snapshot sample；
5. 重新运行 P1 Gate；
6. 搜索所有 current evidence 中的 `rdkit_absent`；
7. 区分历史任务书/历史提交文本与当前 authoritative evidence。

建议核验：

```bash
rg -n "rdkit_absent|RDKit.*absent|rdkit.*absent" \
  reports/data_audit \
  reports/p1/P1_PREFLIGHT.json \
  reports/p1/P1_PREFLIGHT.md \
  reports/p1/snapshot_build_sample.json \
  reports/p1/P1_GATE_REPORT.json \
  reports/p1/P1_GATE_REPORT.md
```

允许历史文件保留过去审计结论，例如：

```text
CHATGPT_P1_REMEDIATION_PROMPT_ROUND_3.md
SUBMISSION_TO_CHATGPT_P1_ROUND_3.md
```

但当前 authoritative/generated evidence 不得继续把已安装的 RDKit 报为 absent。

不要直接手工改生成结果来掩盖 producer bug。修 producer，再生成。

### 13.1 G03 正确 blocker

若环境状态没有发生新变化，G03 应保持：

```text
BLOCKED
```

正确 blocker 是：

```text
real_reaction_source_not_confirmed
required real proline/2OG source record not located
```

不是：

```text
rdkit_absent
```

### 13.2 G04 正确 blocker

若没有获得真实 mapper：

```text
P1-G04 = BLOCKED
```

原因是：

```text
RealMapperAdapter.map_reaction() 尚未形成真实 integration
```

不得用 synthetic fixture 冒充真实 mapper integration。

### 13.3 G10 正确 blocker

若没有真实 source 和第二位独立 annotator：

```text
P1-G10 = BLOCKED
```

不得伪造 inter-annotator agreement。

---

## 14. Gate 聚合规则

继续保持单一聚合 authority。

规则必须是：

```text
任何 implementation failure
→ overall NOT_READY / FAIL
```

即使同一 Gate 还有外部 blocker：

```text
implementation failure 优先于 BLOCKED
```

只有在：

```text
所有内部实现检查通过
且仅剩真实外部输入缺失
```

时，才允许 overall：

```text
BLOCKED
```

本轮完成后的合理预期是：

```text
P1-G01 PASS
P1-G02 PASS
P1-G03 BLOCKED
P1-G04 BLOCKED
P1-G05 PASS
P1-G06 PASS
P1-G07 PASS
P1-G08 PASS
P1-G09 PASS
P1-G10 BLOCKED

7 PASS / 0 FAIL / 3 BLOCKED
overall = BLOCKED
```

这不等于 P1 accepted。

---

## 15. 必须运行的验收命令

在项目根目录执行。

### 15.1 定向 RED/GREEN tests

```bash
.venv/bin/python -m pytest \
  tests/p1/test_eligibility_cross_invariants.py \
  -q
```

如果新增 semantic suite：

```bash
.venv/bin/python -m pytest \
  tests/p1/test_eligibility_semantic_fail_closed.py \
  -q
```

Snapshot boundary：

```bash
.venv/bin/python -m pytest \
  tests/p1/test_snapshot_complete_evidence.py \
  tests/p1/test_snapshot_nested_evidence.py \
  tests/p1/test_snapshot_builder.py \
  -q
```

### 15.2 P1 全部测试

```bash
.venv/bin/python -m pytest tests/p1 -q
```

### 15.3 P0 contracts

```bash
.venv/bin/python -m pytest tests/contracts -q
```

### 15.4 Full suite

```bash
.venv/bin/python -m pytest -q
```

必须报告：

- collected；
- passed；
- failed；
- errors；
- skipped；
- xfailed/xpassed。

### 15.5 P0 Gate

```bash
.venv/bin/python scripts/run_p0_gate.py
```

必须保持：

```text
10/10 PASS
READY_FOR_CHATGPT_AUDIT
```

### 15.6 P1 mutations

```bash
.venv/bin/python scripts/run_p1_mutations.py
```

必须：

```text
M1–M56 全部被各自预期失败捕获
```

### 15.7 P1 Gate

```bash
.venv/bin/python scripts/run_p1_gate.py
```

预计因真实外部 blocker 返回非零是允许的，但报告必须准确：

```text
G08 PASS
G09 PASS
G03/G04/G10 BLOCKED
0 internal FAIL
overall BLOCKED
```

不能只看进程 exit code，必须核对 JSON/Markdown 的 per-gate status。

### 15.8 Gate deletion/collection resistance

必须以临时副本或 mutation harness 验证：

```text
mandatory G08 test 缺失 → G08 FAIL
mandatory G09 test 缺失 → G09 FAIL
```

验证后必须自动恢复，不得移动或删除真实工作区测试。

---

## 16. 必须更新的工作日志

更新：

```text
reports/p1/P1_REMEDIATION_WORKLOG.md
```

新增明确的 Round 4 章节，至少包含：

1. Round 3 rejection 摘要；
2. 开工 branch/HEAD/status；
3. 开工前已存在修改；
4. ChatGPT 14 个 fail-open 的复现结果；
5. RED tests 列表；
6. RED 运行结果；
7. 每项最小修复；
8. strict invariant 的最终规则；
9. quarantine/ambiguity/direction policy；
10. element balance consistency policy；
11. mapping bidirectional uniqueness/coverage policy；
12. ledger reference policy；
13. embedded/external lineage authority；
14. G08 wiring 前后对比；
15. G09 wiring 前后对比；
16. M42–M56 结果；
17. stale RDKit evidence 的 producer 根因和刷新结果；
18. tests/contracts、tests/p1、full suite；
19. P0 Gate；
20. P1 Gate；
21. remaining external blockers；
22. dependency/network actions；
23. deviations/assumptions；
24. changed files；
25. P2 仍 BLOCKED。

不得把手工推断数字写成“实际运行”。

---

## 17. Round 4 必须生成的提交材料

### 17.1 提交封面

生成：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_4.md
```

### 17.2 结构化审核证据

生成：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_4_AUDIT_EVIDENCE.json
```

至少包含：

```jsonc
{
  "round": 4,
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
  "strict_semantic_probes": {},
  "mutations": {
    "total": 56,
    "caught": 56,
    "all_caught": true
  },
  "gate_wiring": {
    "g08_required_tests": [],
    "g09_required_tests": [],
    "missing_required_test_causes_fail": true
  },
  "stale_evidence_scan": {},
  "external_blockers": [],
  "dependency_or_network_actions": [],
  "p2_status": "BLOCKED"
}
```

数据必须从真实运行产物生成，不得手填一个与实际不一致的“全绿 JSON”。

### 17.3 提交封面必须逐项回答

1. branch；
2. HEAD；
3. working tree；
4. 本轮 changed files；
5. tests/contracts 统计；
6. tests/p1 统计；
7. full suite 统计；
8. P0 Gate 结果；
9. P1 Gate 逐 Gate 结果；
10. M1–M56 逐项结果；
11. Round 3 complete canonical snapshot 是否保留；
12. participant mapped_fraction 是否进入 strict validation；
13. actual formal pair coverage 是否验证；
14. reverse many-to-one mapping 是否拒绝；
15. explicit element imbalance 是否 quarantine/never strict；
16. explicit ReactionEvidence quarantine 是否优先；
17. ambiguity_sets 是否禁止未经证明的 strict；
18. embedded/external lineage mismatch 是否拒绝；
19. uncontrolled direction 是否拒绝；
20. ledger ghost references 是否拒绝；
21. generic unknowns 是否禁止 strict；
22. duplicate lineage 是否拒绝；
23. public snapshot API 是否不能绕过；
24. G08 实际运行哪些文件/node；
25. G09 实际运行哪些文件/node；
26. 删除 mandatory test 后 Gate 是否 FAIL；
27. current evidence 是否仍含 stale `rdkit_absent`；
28. G03 当前 blocker；
29. G04 当前 blocker；
30. G10 当前 blocker；
31. 是否安装依赖；
32. 是否联网；
33. 是否使用 synthetic fixture；
34. synthetic fixture 是否明确标记；
35. assumptions/deviations；
36. P2 状态。

---

## 18. Round 4 Definition of Done

### 18.1 Strict scientific boundary

- [ ] participant low mapped fraction 不得 strict；
- [ ] summary 自报 complete 但 pair coverage 不完整时不得 strict；
- [ ] reactant→product 和 product←reactant 两个方向均唯一；
- [ ] non-zero/inconsistent explicit element balance 不得 strict；
- [ ] explicit ReactionEvidence quarantine 必须进入 quarantine；
- [ ] nonempty untyped ambiguity sets 不得未经证明进入 strict；
- [ ] embedded/external lineage conflict 不得 strict；
- [ ] uncontrolled direction 不得 strict；
- [ ] ledger participant/map ghost references 不得 strict；
- [ ] generic untyped unknowns 不得 strict；
- [ ] duplicate lineage ID/content 不得 strict；
- [ ] public snapshot API 不可绕过以上规则。

### 18.2 Snapshot preservation

- [ ] complete canonical payload 保持；
- [ ] centralized `snapshot_id` exclusion 保持；
- [ ] full decision/quarantine/lane hash 保持；
- [ ] dual-ledger disagreement fail closed 保持；
- [ ] loader 完整 tamper rejection 保持；
- [ ] Round 3 snapshot mutation tests 全绿。

### 18.3 Gate

- [ ] G08 显式运行 cross-invariant/semantic tests；
- [ ] G09 显式运行 complete-evidence tests；
- [ ] mandatory file/node 缺失会导致 Gate FAIL；
- [ ] implementation failure 不被 BLOCKED 掩盖；
- [ ] P0 Gate 仍 10/10；
- [ ] G03/G04/G10 blocker 诚实；
- [ ] G08/G09 内部修复后 PASS。

### 18.4 Mutations

- [ ] M1–M41 无回退；
- [ ] M42–M56 全部存在；
- [ ] 每项从合法 baseline 开始；
- [ ] 每项由目标 failure 捕获；
- [ ] M56a/M56b 证明 Gate 接线真实有效。

### 18.5 Evidence

- [ ] producer 已修复 stale RDKit 文案；
- [ ] authoritative current evidence 不再声称 RDKit absent；
- [ ] JSON/Markdown 数字一致；
- [ ] fixture 与 real evidence 明确分开；
- [ ] Round 4 worklog 完整；
- [ ] Round 4 submission 完整；
- [ ] P2 仍 BLOCKED。

---

## 19. 如果发现 schema limitation

不要静默猜测。

按以下规则处理：

1. 先确认冻结设计是否已有 authority；
2. 若已有，复用现有 typed object；
3. 若没有，但可以通过现有对象做 cross-validation，做最小验证；
4. 若无法证明 strict 条件，fail closed；
5. 在 worklog 中明确：

```text
缺少什么 typed authority
为什么不能可靠判断
当前如何 fail closed
后续应在哪个阶段解决
```

未经用户批准，不要修改 final design/plan 来迁就代码。

不要用：

- 任意字符串关键词；
- 默认值；
- fixture-specific ID；
- test-only bypass；
- 硬编码某个 proline/2OG 样本；
- 报告层 post-processing；

代替真实 invariant。

---

## 20. 允许的最终提交结尾

只有当：

- 所有本轮 RED tests 已转绿；
- G08/G09 真实接线；
- M1–M56 全部被各自目标失败捕获；
- contracts/P1/full tests 全绿；
- P0 Gate 10/10；
- 当前 evidence 不再含 stale RDKit blocker；
- 没有内部 implementation failure；

才允许 `SUBMISSION_TO_CHATGPT_P1_ROUND_4.md` 以：

```text
READY_FOR_CHATGPT_P1_ROUND_4_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
```

结尾。

如果任何内部反例、Gate wiring、mutation 或回归仍失败，必须改为：

```text
NOT_READY_FOR_CHATGPT_P1_AUDIT

P2 BLOCKED
```

禁止写：

```text
P1 ACCEPTED
P1 COMPLETE
P2 READY
P2 STARTED
ALL GATES PASS
```

除非未来 ChatGPT 完成只读复核并明确给出相应结论。

---

## 21. 最终提醒

本轮最重要的不是增加测试数量，而是证明：

```text
一个 scientific contradiction、
一个 unresolved authority、
一个 dangling reference、
一个 self-reported-but-unsupported mapping，
都不可能进入 strict donor truth。
```

请保持修改外科式、可审计、可复现：

```text
每个问题先有 RED
每个修复对应一个明确 invariant
每个 Gate 真实执行 mandatory tests
每个 evidence 来自实际运行
所有外部 blocker 诚实保留
P2 继续等待 ChatGPT 审核
```
