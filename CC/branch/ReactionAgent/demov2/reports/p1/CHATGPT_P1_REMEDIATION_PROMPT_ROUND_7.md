# P1 Round 7 严格整改任务书

> **交付对象：** 新开的 AI coding agent（Claude、Qwen、Codex 等）  
> **项目根目录：** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`  
> **依据：** ChatGPT 对 `SUBMISSION_TO_CHATGPT_P1_ROUND_6.md` 的独立只读审核  
> **本轮性质：** P1 strict mapping/ledger/public-index 科学边界的最小整改，不是 P2 开发  
> **最终验收人：** ChatGPT  
> **日期：** 2026-07-31

---

## 0. 正式审核结论

Round 6 未通过 ChatGPT 只读审核。

当前正式状态：

```text
CHATGPT_P1_ROUND_6_READ_ONLY_AUDIT = REJECTED
rejection_class = IMPLEMENTATION_FAILURE
P1-G08_EFFECTIVE_STATUS = FAIL
P1_STATUS = BLOCKED
P2_STATUS = BLOCKED
```

Round 6 的真实进展必须承认并保留：

```text
P0 contract tests = 290 passed
P1 tests = 496 passed
full suite = 786 passed
skip/xfail/xpass = 0
P0 Gate = 10/10 PASS
P1 Gate 脚本输出 = 7 PASS / 3 BLOCKED
G08 current mandatory nodes = 82/82 passed
G09 mandatory nodes = 11/11 passed
M1–M77 = 77/77 caught
snapshot hash = a54fc0a46b3055e560ac2127f8e6464e6a5ab51675879f97cfe21d811e5bc103
```

Round 6 已知修复也已由 ChatGPT 独立确认：

- uncontrolled cofactor direction 已 fail closed；
- duplicate/conflicting stoichiometric authority 已 fail closed；
- mechanistic target 改用 product-side map registry；
- empty/within-assignment duplicate FAT maps 已 fail closed；
- heavy-atom participant 完全空 map 已 fail closed；
- non-formal AddedAtomSource 且无 mechanism 已 fail closed；
- empty MechanisticOriginEvidence target 已 fail closed；
- 上述五个主要 public 反例当前确实进入 diagnostic index，而非 production。

但 Round 6 仍有内部 implementation failure：

1. heavy-atom validator 只检查 map list 是否为空，没有验证 map 数量与 molecule/mapped claim 相容；
2. 当前所谓“fully mapped positive baseline”本身是 `CCO + [1,2]`，并非真正 fully mapped；
3. 非正 atom-map identifiers（`0`、负数）可进入 strict；
4. AddedAtomSource、RemovedAtomSink、FormalAtomTransferAssignment、MechanisticOriginEvidence target maps 的 collection/list duplicate 仍可进入 strict；
5. `RemovedAtomSink(formal_assignment=False)` 没有任何 formal/mechanistic authority，仍可 strict；
6. public boundary tests 只读 `records.jsonl`，没有检查 production/diagnostic/quarantine indexes；
7. 因此 G08 的 82 个节点仍未覆盖完整任务要求。

本轮唯一目标：

```text
修复 R7-01–R7-06
→ 重建真正科学一致的 strict baseline
→ 增加 direct RED tests
→ 增加 public records + indexes RED tests
→ 扩展 G08 mandatory nodes
→ 增加 M78–M83
→ 保留 M1–M77
→ 完整回归
→ 重新提交 ChatGPT 只读审核
```

P2 继续 BLOCKED。

---

## 1. 开始前必须完整阅读

不要依赖聊天记忆。按以下顺序完整阅读。

### 1.1 最终设计与计划

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_design.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_plan.md
```

### 1.2 P1 原始任务

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/chatgpt_p1_train.md
```

### 1.3 Round 6 任务、提交和证据

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_6.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_6.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_6_AUDIT_EVIDENCE.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
```

### 1.4 当前核心实现

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/eligibility/engine.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/mapping.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/ledger.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/p1_entities.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/loader.py
```

### 1.5 当前 tests、Gate 与 mutations

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_reference_integrity.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_cross_invariants.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_fail_closed.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_engine.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_nested_evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_complete_evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_gate.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_mutations.py
```

### 1.6 当前 Gate/evidence

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/mutation_results.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/eligibility_reference_integrity_results_round_6.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results_round_6.json
```

阅读后先在 worklog 记录：

```text
branch
HEAD
working tree dirty status
开工前已有 modified/untracked files
本轮预计修改文件
本轮明确不修改文件
当前 Python/RDKit 只读 probe
```

不得使用：

```text
git reset --hard
git checkout --
git clean
```

不得覆盖、删除或丢弃用户已有修改。

---

## 2. 本轮必须遵守的工作方式

严格按：

```text
完整阅读
→ 冻结并记录基线
→ 独立复现 R7-01–R7-06
→ 先写 RED tests
→ 保存修复前 RED 证据
→ 做最小、集中、fail-closed 实现
→ 重建真正 strict-valid positive baseline
→ public records + indexes boundary
→ G08 mandatory nodes
→ M78–M83
→ M1–M77 回归
→ 完整 tests/Gates
→ evidence/worklog/submission
→ 等待 ChatGPT
```

本轮禁止：

- 开始或实现 P2；
- 修改 P0 ADR、P0 contracts、final design、final plan 来迁就代码；
- 修改报告数字掩盖实现缺陷；
- 删除、rename 或放宽既有测试；
- 从 `_G08_REQUIRED_NODES` 删除已有 82 个节点；
- 从 G09 删除 11 个节点；
- 弱化 M1–M77；
- 使用 unrelated blocker 让 negative test “碰巧非 strict”；
- 使用全拒绝式实现；
- 用 fixture-specific ID 或 hard-coded molecule；
- 用字符串关键词猜测化学角色；
- 在 strict validator 中 silently repair maps；
- synthetic fixture 冒充 real reaction evidence；
- 未经用户明确授权安装依赖、联网或修改 legacy source；
- 无关重构、全库格式化或创建新 validation framework；
- 并行运行会写同一 Gate/pytest JSON 的命令。

Gate 与 full-suite 验收必须串行运行，避免多个进程同时写：

```text
.pytest_gate_contract_report.json
.pytest_gate_report.json
.pytest_gate_p1_report.json
```

---

## 3. 必须保留的既有正确成果

以下不得回退：

### 3.1 P0 / snapshot

- P0 290 contracts；
- P0 Gate 10/10；
- P0 六个 ADR；
- dual ledger boundary；
- snapshot canonical payload；
- snapshot deterministic hash；
- snapshot complete-evidence hashing；
- G09 11 mandatory nodes；
- M56b G09 deletion protection；
- snapshot hash `a54fc0…c103`，除非真正 canonical fixture 被有依据地修改；
- 如果 snapshot hash 必须变化，必须明确解释，不能偷偷改 stored hash。

### 3.2 Mapping/participant

- participant ID uniqueness；
- participant side vocabulary；
- within-participant map uniqueness；
- same-side cross-participant map uniqueness；
- reactant/product 两侧可合法对应使用相同 map number；
- formal-pair participant/side/map membership；
- one source → one target；
- one target ← one source；
- exact duplicate formal-pair rejection；
- actual declared-map pair coverage；
- mapped fraction threshold；
- mapped heavy atom summary threshold；
- assignment method/quality/ambiguity；
- MCS/center-pair 不得伪装 strict。

### 3.3 Ledger/lineage

- stoichiometric ghost/side/coefficient/duplicate/conflict；
- role ghost/duplicate/conflict/lineage consistency；
- cofactor ghost/uncontrolled direction；
- AddedAtomSource ghost/map/dangling evidence/unbacked non-formal；
- RemovedAtomSink ghost/map；
- FAT method/side/map/edge/empty/within-list duplicate；
- MechanisticOriginEvidence duplicate ID/ghost/product map/empty target；
- element negative count/delta/partial semantics；
- embedded lineage duplicate；
- external lineage ID/content duplicate；
- transformed maps internal duplicate；
- reordered-map semantic duplicate；
- actual mapping support；
- forbidden pairing。

### 3.4 Gate/mutations

- G08 现有 82 个 mandatory nodes；
- G08 missing node → FAIL；
- G09 11 nodes；
- M1–M77 77/77 caught；
- implementation failure 不能被 G03/G04/G10 BLOCKED 掩盖；
- zero skip/xfail/xpass。

---

## 4. ChatGPT 独立复现摘要

以下所有新反例：

1. 符合当前 Pydantic schema；
2. 使用受控 side；
3. 使用存在的 participant；
4. MappingReport 自报 fully mapped；
5. direct decision 返回 `strict_eligible`；
6. `records.jsonl` lane 为 `strict`；
7. 实际出现在 `production_index.jsonl`；
8. 不出现在 diagnostic/quarantine index。

| 编号 | 反例 | Direct | Production index |
|---|---|---|---|
| R7-01a | `CC` 有 2 heavy atoms，只声明 1 个 map，mf=1 | strict | 泄漏 |
| R7-01b | `C` 有 1 heavy atom，声明 2 个 maps，mf=1 | strict | 泄漏 |
| R7-02 | `CC` 使用 maps `[-1,0]` | strict | 泄漏 |
| R7-03a | duplicate AddedAtomSource | strict | 泄漏 |
| R7-03b | duplicate RemovedAtomSink | strict | 泄漏 |
| R7-03c | duplicate FAT assignment | strict | 泄漏 |
| R7-03d | duplicate mechanistic target maps `[1,1]` | strict | 泄漏 |
| R7-04 | RemovedAtomSink `formal_assignment=False` | strict | 泄漏 |

此外：

- 当前 Round 6 public tests 只检查 `records.jsonl` lane；
- 没有检查 production/diagnostic/quarantine membership；
- 因此 index-only leakage mutation 不会被这些 mandatory tests 捕获。

---

## 5. R7-01：heavy-atom map 数量必须与 fully-mapped claim 相容

### 5.1 当前缺陷

当前：

```python
heavy = RDKit heavy atom count

if heavy > 0 and not p.atom_map_numbers:
    fail
```

只处理：

```text
heavy > 0
maps == []
```

没有处理：

```text
heavy = 2
maps = [1]
mapped_fraction = 1.0
```

或：

```text
heavy = 1
maps = [1,2]
mapped_fraction = 1.0
```

### 5.2 必须复现的 underflow

构造：

```text
reactant participant:
canonical_smiles = CC
heavy_atom_count = 2
atom_map_numbers = [1]
mapped_fraction = 1.0

product participant:
canonical_smiles = CC
heavy_atom_count = 2
atom_map_numbers = [1]
mapped_fraction = 1.0

formal pair:
r1:1 → p1:1

mapping_status = fully_mapped
mapped_heavy_atom_fraction = 1.0
changed_atom_coverage = 1.0
map_number_uniqueness = true
```

修复前：

```text
direct = strict_eligible
records lane = strict
production membership = true
```

### 5.3 必须复现的 overflow

构造：

```text
reactant participant:
canonical_smiles = C
heavy_atom_count = 1
atom_map_numbers = [1,2]
mapped_fraction = 1.0

product participant:
canonical_smiles = C
heavy_atom_count = 1
atom_map_numbers = [1,2]
mapped_fraction = 1.0

formal pairs:
r1:1 → p1:1
r1:2 → p1:2
```

修复前同样进入 strict production。

### 5.4 正确 strict 语义

当前 strict path 已要求：

```text
p.mapped_fraction == 1.0
mapping_report.mapped_heavy_atom_fraction == 1.0
```

因此对 RDKit 可解析、heavy_atom_count > 0 的 participant，至少要求：

```text
len(unique(atom_map_numbers)) == heavy_atom_count
```

否则：

```text
strict fail closed
```

建议 reason token：

```text
participant_heavy_atom_map_count
```

必须区分：

```text
count < heavy_atom_count → underflow
count > heavy_atom_count → overflow
```

reason 应携带：

```text
participant_id
heavy_atom_count
unique_map_count
mapped_fraction
```

### 5.5 Zero-heavy-atom policy

对：

```text
heavy_atom_count == 0
```

不要强制 map count 等于普通 heavy-atom规则。

但也不能允许零重原子 participant 携带任意多个“heavy atom maps”并被当成 fully mapped。

必须查阅：

- hydrogen_policy；
- proton_policy；
- electron_policy；
- final design 的 heavy-atom mapping 语义；

然后采用最小、可证明策略。

至少保留：

```text
[H+] + no heavy-atom maps
```

不会被错误拒绝。

如果 electron `[e-]` 无法由 RDKit 解析：

- 明确记录 limitation；
- 不伪造；
- 不声称 electron policy 已完整验证；
- unparseable strict 继续 fail closed。

### 5.6 必须先写的 RED tests

至少：

```text
test_heavy_atom_map_count_underflow_never_strict
test_heavy_atom_map_count_overflow_never_strict
test_mapped_fraction_one_cannot_override_map_count_underflow
test_global_mapped_fraction_one_cannot_override_participant_count_mismatch
test_public_snapshot_cannot_promote_heavy_map_count_underflow
test_public_snapshot_cannot_promote_heavy_map_count_overflow
```

Positive：

```text
test_genuinely_fully_mapped_heavy_atom_participant_remains_strict
test_zero_heavy_atom_proton_policy_remains_valid
```

---

## 6. R7-01B：重建真正 strict-valid test baseline

### 6.1 当前 baseline 不合格

当前 helper 默认：

```text
canonical_smiles = CCO
atom_map_numbers = [1,2]
mapped_fraction = 1.0
```

`CCO` 有三个重原子，因此不是 fully mapped。

当前 positive test：

```text
test_valid_fully_mapped_heavy_atom_participant_remains_strict
```

只是验证“maps 非空”，不是“fully mapped”。

### 6.2 必须修复

建立一个在 molecule/map/formal-pair/lineage 层都一致的 baseline。

建议最小 baseline：

```text
reactant:
canonical_smiles = CC
heavy atoms = 2
atom_map_numbers = [1,2]
mapped_fraction = 1.0

product:
canonical_smiles = CC
heavy atoms = 2
atom_map_numbers = [1,2]
mapped_fraction = 1.0

formal pairs:
r1:1 → p1:1
r1:2 → p1:2

lineage transformed maps:
[1,2]
```

如果 transformation 必须非 identity，选择另一个 heavy-atom count 一致、formal mapping 完整、无需缺失 co-substrate 的简单 fixture。

不要继续使用：

```text
CCO → CC(=O)O
```

同时只声明两个 maps 并自报 fully mapped。

### 6.3 Test quality

每个 negative test 必须：

1. 在 mutation 前 assert baseline `strict_eligible`；
2. baseline 还必须经独立 RDKit count 检查证明 molecule/map 一致；
3. 只修改一个目标条件；
4. reason 必须来自目标 invariant；
5. 不能用化学不一致 fixture 规避前置 validator。

Round 6 中将某个 FAT test 的 participant 改成 `[H+]` 以避免 empty-map validator 提前触发的做法，可以保留“单缺陷测试”思想，但整个其余 baseline 仍必须科学一致。

禁止使用不可能的：

```text
zero-heavy-atom proton + 多个 heavy atom map IDs
```

作为 positive authority。

---

## 7. R7-02：atom map identifier 必须为正整数

### 7.1 当前缺陷

当前 schema 使用普通：

```python
int
```

participant registry 只检查：

- duplicates；
- same-side collisions；
- participant side。

它接受：

```text
-1
0
```

### 7.2 必须复现

构造：

```text
reactant CC maps = [-1,0]
product  CC maps = [-1,0]

formal pairs:
r1:-1 → p1:-1
r1:0  → p1:0

lineage transformed maps:
[-1,0]
```

修复前进入 strict production。

### 7.3 正确要求

strict participant/map authority 中所有 atom map identifiers 必须：

```text
isinstance(int)
value > 0
```

Pydantic strict model 已防止普通字符串自动转换时，继续遵守现有 strict schema。

建议在 central participant registry 最早检查：

```text
participant.atom_map_numbers
```

一旦 central participant authority 拒绝非正 map：

- formal pair membership；
- lineage map membership；
- AddedAtomSource；
- RemovedAtomSink；
- FAT；
- mechanistic target；

都会由已有 reference checks 继承。

但仍要增加 direct tests，证明其他对象不能用未声明非正 map 绕过。

建议 reason token：

```text
participant_map_identifier
```

### 7.4 必须先写的 RED tests

至少：

```text
test_zero_atom_map_identifier_never_strict
test_negative_atom_map_identifier_never_strict
test_nonpositive_formal_pair_map_never_strict
test_nonpositive_lineage_map_never_strict
test_positive_atom_map_identifiers_remain_strict
test_public_snapshot_cannot_promote_nonpositive_atom_maps
```

---

## 8. R7-03：ledger evidence collection-level duplicate 必须 fail closed

当前各 entry 内部验证不等于 collection-level uniqueness。

没有 typed aggregation authority 时，重复 evidence 会造成：

- double counting；
- 多次累加同一 atom source/sink；
- 重复 formal transfer；
- 重复 mechanism target。

本轮不得静默接受。

### 8.1 AddedAtomSource duplicates

复现：

```python
source = AddedAtomSource(
    atom_map_number=1,
    source_participant_id="r1",
    formal_assignment=True,
)

added_atom_sources = [source, source]
```

修复前：

```text
strict_eligible
production membership = true
```

建议 canonical signature：

```text
(
  atom_map_number,
  source_participant_id,
  formal_assignment,
  mechanistic_evidence_id
)
```

完全重复 → `added_atom_source_duplicate`。

对于同一 atom map 指向不同 source participant/mechanistic authority：

```text
没有 typed ambiguity authority时 → conflict / fail closed
```

建议进一步建立：

```text
atom_map_number → single added-source authority
```

如果同一 atom 出现两个不同 authority，使用：

```text
added_atom_source_conflict
```

### 8.2 RemovedAtomSink duplicates

复现：

```python
sink = RemovedAtomSink(
    atom_map_number=1,
    sink_participant_id="r1",
    formal_assignment=True,
)

removed_atom_sinks = [sink, sink]
```

建议 canonical signature：

```text
(
  atom_map_number,
  sink_participant_id,
  formal_assignment
)
```

完全重复 → `removed_atom_sink_duplicate`。

同一 atom map 指向不同 sink authority，没有 typed ambiguity authority时：

```text
removed_atom_sink_conflict
```

### 8.3 FormalAtomTransferAssignment duplicates

当前只检查单条 assignment 内：

```text
transferred_atom_map_numbers 无重复
```

没有检查 assignment list 中两条完全相同对象。

建议 canonical signature：

```text
(
  source_participant_id,
  target_participant_id,
  tuple(sorted(unique(transferred_atom_map_numbers))),
  assignment_method
)
```

完全重复 →：

```text
formal_atom_transfer_duplicate_assignment
```

同一 source atom map 被两个不同 target edge 的 FAT claim，但无 typed split authority：

```text
formal_atom_transfer_assignment_conflict
```

不要破坏现有：

- source side；
- target side；
- source map membership；
- formal edge support；
- list non-empty；
- within-list duplicate；
- method vocabulary。

### 8.4 MechanisticOriginEvidence target maps duplicates

复现：

```python
MechanisticOriginEvidence(
    evidence_id="me1",
    evidence_type="isotope_tracing",
    source_participant_id="r1",
    target_atom_map_numbers=[1,1],
)
```

当前 evidence ID 唯一，但 target list 内部重复。

必须：

```text
len(targets) == len(set(targets))
```

否则：

```text
mechanistic_evidence_duplicate_target_map
```

### 8.5 必须先写的 RED tests

至少：

```text
test_duplicate_added_atom_source_never_strict
test_conflicting_added_atom_sources_never_strict
test_duplicate_removed_atom_sink_never_strict
test_conflicting_removed_atom_sinks_never_strict
test_duplicate_formal_transfer_assignment_never_strict
test_conflicting_formal_transfer_assignments_never_strict
test_duplicate_mechanistic_target_maps_never_strict
test_distinct_valid_ledger_evidence_remains_valid
```

Public：

```text
test_public_snapshot_cannot_promote_duplicate_added_atom_source
test_public_snapshot_cannot_promote_duplicate_removed_atom_sink
test_public_snapshot_cannot_promote_duplicate_formal_transfer_assignment
test_public_snapshot_cannot_promote_duplicate_mechanistic_targets
```

如果某个 conflict case 需要 schema 尚未冻结的 split/merge authority：

- 不要猜；
- strict fail closed；
- worklog 记录缺少什么 typed authority。

---

## 9. R7-04：RemovedAtomSink non-formal 且无其他 authority 不得 strict

### 9.1 当前缺陷

schema 明确有：

```python
formal_assignment: bool
```

当前 validator 只检查：

```text
sink participant exists
map belongs to participant
```

因此：

```python
RemovedAtomSink(
    atom_map_number=1,
    sink_participant_id="r1",
    formal_assignment=False,
)
```

进入 strict production。

### 9.2 正确要求

这不是“无法知道是否 formal”：

```text
formal_assignment=False
```

已经明确声明它不是 formal assignment。

当前 RemovedAtomSink 又没有：

```text
mechanistic_evidence_id
```

或其他 typed sink authority。

因此没有 authority 证明该 sink，正确行为是：

```text
strict fail closed
```

建议 reason token：

```text
removed_atom_sink_unbacked
```

### 9.3 必须先写的 RED tests

```text
test_nonformal_removed_atom_sink_without_authority_never_strict
test_formally_backed_removed_atom_sink_remains_valid
test_public_snapshot_cannot_promote_unbacked_removed_atom_sink
```

不得通过删除 `formal_assignment` 字段或忽略其值解决。

---

## 10. R7-05：public boundary 必须检查真实 indexes

### 10.1 当前缺陷

当前 helper：

```text
_build_lanes(...)
```

只读取：

```text
records.jsonl
```

并返回：

```text
reaction_id → lane
```

它没有读取：

```text
production_index.jsonl
diagnostic_index.jsonl
quarantine_index.jsonl
```

所以一个 mutation 若：

```text
records lane = diagnostic
但错误写入 production index
```

当前 Round 6 public tests 会假绿。

### 10.2 正确 helper

可以最小扩展现有 helper，例如返回：

```python
{
  "record_lanes": {reaction_id: lane},
  "production_ids": set(...),
  "diagnostic_ids": set(...),
  "quarantine_ids": set(...),
}
```

不要创建 snapshot-testing framework。

每个 public negative test 必须 assert：

```text
records lane != strict
reaction_id not in production_ids
reaction_id in expected diagnostic_ids or quarantine_ids
reaction_id not in the other incompatible index
```

每个 public positive strict test必须 assert：

```text
records lane == strict
reaction_id in production_ids
reaction_id not in diagnostic_ids
reaction_id not in quarantine_ids
```

### 10.3 必须先写/更新的 tests

至少更新 Round 6 已有六个：

```text
test_public_snapshot_cannot_promote_uncontrolled_cofactor_direction
test_public_snapshot_cannot_promote_conflicting_reactant_entries
test_public_snapshot_cannot_promote_conflicting_stoichiometry
test_public_snapshot_cannot_promote_reactant_only_mechanistic_target_map
test_public_snapshot_cannot_promote_empty_formal_transfer
test_public_snapshot_cannot_promote_unmapped_heavy_atom_participant
```

并更新 Round 5 已有 public tests，使用同一 index-aware helper。

本轮新增 R7 public tests 也必须检查 indexes。

---

## 11. R7-06：Gate 必须能捕获 index-only leakage

### 11.1 为什么现有 deletion mutation 不够

M56a/c/d 证明：

```text
已列 mandatory node 被删除 → G08 FAIL
```

但不能证明：

```text
public test 自身能捕获 production-index-only leakage
```

### 11.2 必须增加的 mutation

新增一个最小、临时、可逆 mutation：

```text
保持 records.jsonl lane=diagnostic
但将该 diagnostic reaction ID 注入 production_index.jsonl
```

然后运行目标 public boundary authority，必须 FAIL。

这可以作为：

```text
M83
```

或 Gate-specific sub-result。

必须证明 failure 来自：

```text
unexpected production membership
```

不能来自：

- records lane 改成 strict；
- unrelated snapshot hash error；
- missing file；
- JSON parse error；
- test collection failure。

Mutation 完成后必须恢复临时 snapshot/monkeypatch，不修改真实 workspace。

---

## 12. RED test 质量合同

每个 negative test 必须：

1. 从真正科学一致的 strict baseline 开始；
2. mutation 前 assert engine decision 为 strict；
3. mutation 前 assert RDKit heavy count 与 map count 一致；
4. mutation 前 assert map IDs 全为正；
5. 只修改一个目标条件；
6. 输入符合当前 Pydantic schema；
7. assert result 不是 strict；
8. assert invariant-specific reason；
9. 适用时 assert records lane；
10. 适用时 assert production/diagnostic/quarantine membership；
11. 不得由 unrelated blocker 捕获；
12. 保留对应 positive protection test。

禁止：

- 使用错误 heavy-atom count baseline；
- 使用非法 map IDs 作为其他 negative test 的 baseline；
- 使用 `[H+]` 携带多个 heavy maps 规避 validator；
- 删除 mapping evidence 让 test 自然 non-strict；
- 只检查总测试数量；
- 用全拒绝实现。

---

## 13. 建议的最小实现位置

优先修改：

```text
reaction_agent/eligibility/engine.py
tests/p1/test_eligibility_reference_integrity.py
scripts/run_p1_gate.py
scripts/run_p1_mutations.py
```

如 test helper 更适合放入已有 snapshot test utility，可做最小复用，但不要创建新框架。

只有存在明确必要性时才修改：

```text
reaction_agent/schemas/mapping.py
reaction_agent/schemas/ledger.py
```

原因：

- incomplete/diagnostic evidence 可能仍需被 schema 保存；
- Pydantic construction success 不等于 strict eligibility；
- 本轮主要是 cross-object strict validation；
- 不应为了 strict Gate 把所有不完整 evidence 都变成无法反序列化。

如果修改 schema：

- 说明为什么 engine fail-closed 不足；
- 检查 snapshot/loader/backward readability；
- 保持 diagnostic lane 可保存原始 evidence；
- 不得用 schema error 掩盖 public decision bug。

复用现有：

```text
participant registry
reactant/product map registries
maps_by_participant
formal edge registry
central ledger-reference validator
RDKit heavy-atom parser
```

---

## 14. G08 mandatory nodes

当前 82 个节点全部保留。

本轮必须加入所有关键 Round 7 nodes，至少覆盖：

### R7-01

```text
heavy map underflow
heavy map overflow
genuine fully mapped positive
public underflow
public overflow
```

### R7-02

```text
zero map ID
negative map ID
positive map IDs positive protection
public nonpositive maps
```

### R7-03

```text
duplicate/conflicting AddedAtomSource
duplicate/conflicting RemovedAtomSink
duplicate/conflicting FAT assignments
duplicate mechanistic target maps
representative public duplicate evidence
```

### R7-04

```text
unbacked RemovedAtomSink
formally backed sink positive
public unbacked sink
```

### R7-05

所有 public nodes 必须真实检查 indexes。

要求：

1. `_G08_REQUIRED_NODES` 显式列出；
2. G08 实际运行对应 test 文件；
3. missing node → FAIL；
4. failed/skipped/xfail/xpass → FAIL；
5. 报告 mandatory total/collected/passed；
6. 保留 M56a/b/c/d；
7. 增加删除单个 Round 7 node 的 deletion protection；
8. implementation failure 不被外部 BLOCKED 掩盖。

---

## 15. 新增 mutations：M78–M83

保留：

```text
M1–M77
```

新增：

| Mutation | 目标 | 必须捕获 |
|---|---|---|
| M78 | heavy map count underflow/overflow | never strict；public 非 production |
| M79 | map IDs 包含 0/负数 | never strict；public 非 production |
| M80 | duplicate/conflicting AddedAtomSource/RemovedAtomSink | never strict |
| M81 | duplicate FAT assignment / duplicate mechanistic target maps | never strict |
| M82 | RemovedAtomSink formal_assignment=False | never strict；public 非 production |
| M83 | records diagnostic 但错误注入 production index | public boundary test/G08 必须 FAIL |

允许 sub-results：

```text
M78a underflow direct
M78b overflow direct
M78c underflow public
M78d overflow public

M79a zero
M79b negative
M79c public

M80a duplicate AddedAtomSource
M80b conflicting AddedAtomSource
M80c duplicate RemovedAtomSink
M80d conflicting RemovedAtomSink

M81a duplicate FAT assignment
M81b conflicting FAT assignment
M81c duplicate mechanistic target maps

M82a direct
M82b public

M83a index-only leakage
```

总 mutation authority：

```text
M1–M83
83/83 caught
```

每项记录：

```text
mutation_id
baseline strict evidence
single target mutation
schema_valid
expected
actual eligibility
actual reason
records lane
production membership
diagnostic membership
quarantine membership
caught
```

`caught=true` 必须来自目标 invariant。

Mutation runner：

- 使用临时目录；
- 可逆 monkeypatch；
- 不修改真实 source/evidence；
- 异常时恢复；
- 不与 Gate/full suite 并发写报告。

---

## 16. 执行顺序

### R7-T1：冻结基线

串行运行并记录：

```text
contracts
tests/p1
full tests
P0 Gate
P1 Gate
M1–M77
```

预期 Round 6 基线：

```text
290 contracts
496 P1 tests
786 full tests
P0 10/10
P1 script 7 PASS / 3 BLOCKED
M1–M77 77/77
```

如不一致，先记录差异，不带未知基线修改。

### R7-T2：独立复现

修复前复现：

```text
R7-01 underflow/overflow
R7-02 nonpositive map IDs
R7-03 duplicate ledger evidence
R7-04 unbacked RemovedAtomSink
R7-05 public helper index gap
R7-06 index-only leakage mutation
```

### R7-T3：重建 genuine strict baseline

先让 positive baseline 在 molecule/map/formal-pair 层科学一致。

### R7-T4：写 direct RED tests

证明旧实现 fail-open。

### R7-T5：写 public index-aware RED tests

证明旧实现进入 production。

### R7-T6：最小实现

集中修 validator 与 helper。

### R7-T7：定向 GREEN

运行新增 tests，检查 reason 和 indexes。

### R7-T8：扩展 G08

加入 mandatory nodes 与 deletion protection。

### R7-T9：实现 M78–M83

保留 M1–M77。

### R7-T10：完整串行回归

按：

```text
contracts
P1
full
P0 Gate
P1 Gate
mutations
```

顺序运行。

### R7-T11：证据和提交

更新 worklog、结构化 evidence、submission。

---

## 17. 必须运行的验收命令

项目根：

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
```

### 17.1 Reference integrity

```bash
.venv/bin/python -m pytest \
  tests/p1/test_eligibility_reference_integrity.py \
  -q
```

### 17.2 Strict eligibility

```bash
.venv/bin/python -m pytest \
  tests/p1/test_eligibility_cross_invariants.py \
  tests/p1/test_eligibility_fail_closed.py \
  tests/p1/test_eligibility_engine.py \
  -q
```

### 17.3 Snapshot

```bash
.venv/bin/python -m pytest \
  tests/p1/test_snapshot_builder.py \
  tests/p1/test_snapshot_nested_evidence.py \
  tests/p1/test_snapshot_complete_evidence.py \
  -q
```

### 17.4 Contracts

```bash
.venv/bin/python -m pytest tests/contracts -q
```

### 17.5 P1

```bash
.venv/bin/python -m pytest tests/p1 -q
```

### 17.6 Full

```bash
.venv/bin/python -m pytest tests -q
```

记录：

```text
collected
passed
failed
errors
skipped
xfailed
xpassed
```

### 17.7 P0 Gate

```bash
.venv/bin/python scripts/run_p0_gate.py
```

必须：

```text
10/10 PASS
```

### 17.8 P1 Gate

```bash
.venv/bin/python scripts/run_p1_gate.py
```

合理预期：

```text
G08 无 implementation failure
G09 无回退
G03/G04/G10 可继续真实 BLOCKED
overall BLOCKED
```

### 17.9 Mutations

```bash
.venv/bin/python scripts/run_p1_mutations.py
```

必须：

```text
M1–M83 = 83/83 caught
```

---

## 18. 正确 Gate 矩阵

修复前 ChatGPT 有效判定：

| Gate | Round 6 审核后状态 |
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

即：

```text
6 PASS
1 FAIL
3 BLOCKED
```

修复完成后的合理预期：

```text
7 PASS
0 FAIL
3 BLOCKED
overall = BLOCKED
```

只有新增反例、public indexes、G08、M78–M83 全部真实通过后，才能报告 G08 PASS。

---

## 19. 必须更新或生成的产物

更新：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/mutation_results.json
```

新增：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/eligibility_reference_integrity_results_round_7.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/eligibility_semantic_invariant_results_round_7.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results_round_7.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_7_AUDIT_EVIDENCE.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_7.md
```

不得删除 Round 2–6 历史 evidence。

---

## 20. Round 7 structured evidence 最低字段

`P1_ROUND_7_AUDIT_EVIDENCE.json` 至少包含：

```text
round
branch
head
working_tree
python
rdkit
changed_files
unchanged_frozen_files
baseline_counts
final_test_counts
zero_skip_xfail_xpass
p0_gate
p1_gate
g08_mandatory_total
g08_mandatory_collected
g08_mandatory_passed
g08_round7_required_nodes
g09_mandatory_total
snapshot_id
snapshot_hash
M1-M77_preserved
mutations_total
mutations_caught
M78-M83_results
R7-01 underflow evidence
R7-01 overflow evidence
R7-02 nonpositive map evidence
R7-03 duplicate ledger evidence
R7-04 unbacked sink evidence
R7-05 records/index membership evidence
R7-06 index-only leakage mutation evidence
genuine_strict_baseline
external_blockers
dependency_or_network_actions
synthetic_fixture_usage
p2_status
```

`genuine_strict_baseline` 至少记录：

```text
participant IDs
canonical SMILES
RDKit heavy atom counts
atom map lists
unique map counts
mapped_fraction
formal pairs
lineage maps
baseline eligibility
```

Round 6 evidence 中：

```json
"M75": []
```

这一包装问题应修正：

- 单项 mutation 也写完整 result；
- 不要让 structured evidence 出现空数组暗示 evidence 缺失。

---

## 21. Worklog Round 7 必须记录

至少包括：

1. ChatGPT Round 6 rejection；
2. 已确认保留的 Round 6 成果；
3. R7-01–R7-06 修复前 direct 结果；
4. 修复前 records lane；
5. 修复前 production/diagnostic/quarantine membership；
6. genuine strict baseline 旧问题；
7. genuine strict baseline 新定义；
8. RDKit heavy count；
9. map count underflow RED；
10. map count overflow RED；
11. nonpositive map RED；
12. duplicate AddedAtomSource RED；
13. duplicate RemovedAtomSink RED；
14. duplicate FAT assignment RED；
15. duplicate mechanistic target RED；
16. unbacked RemovedAtomSink RED；
17. public index-only leakage RED；
18. RED 实际失败数量；
19. 每个 validator 的最小修改；
20. public helper 的最小修改；
21. G08 新节点；
22. Round 7 deletion protection；
23. M78–M83；
24. M1–M77 回归；
25. contracts/P1/full counts；
26. P0/P1 Gate；
27. G09/snapshot hash；
28. changed files；
29. assumptions；
30. schema limitations；
31. remaining limitations；
32. external blockers；
33. dependency/network actions；
34. P2 BLOCKED。

必须记录 RED → GREEN，不能只写“已修复”。

---

## 22. Round 7 submission 封面

生成：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_7.md
```

至少逐项回答：

1. 项目根；
2. branch/HEAD/dirty；
3. changed files；
4. frozen files；
5. Round 6 已保留成果；
6. R7-01 underflow；
7. R7-01 overflow；
8. genuine strict baseline；
9. R7-02 zero map；
10. R7-02 negative map；
11. duplicate AddedAtomSource；
12. conflicting AddedAtomSource；
13. duplicate RemovedAtomSink；
14. conflicting RemovedAtomSink；
15. duplicate FAT assignment；
16. conflicting FAT assignment；
17. duplicate mechanistic target maps；
18. unbacked RemovedAtomSink；
19. direct negative evidence；
20. direct positive evidence；
21. records lane evidence；
22. production membership evidence；
23. diagnostic/quarantine membership evidence；
24. index-only leakage mutation；
25. G08 nodes；
26. deletion protection；
27. M1–M83；
28. contracts；
29. P1 tests；
30. full suite；
31. zero skip/xfail/xpass；
32. P0 Gate；
33. P1 Gate matrix；
34. G09；
35. snapshot ID/hash；
36. runtime probe；
37. G03 blocker；
38. G04 blocker；
39. G10 blocker；
40. known limitations；
41. structured evidence path；
42. worklog path；
43. P2 status。

不能只报告总数，必须列关键 node 和 mutation evidence。

---

## 23. 最终提交状态规则

只有同时满足：

- genuine strict baseline 在 molecule/map/pair/lineage 层一致；
- R7-01 underflow/overflow 不得 strict；
- R7-02 nonpositive maps 不得 strict；
- R7-03 duplicate/conflicting ledger evidence 不得 strict；
- R7-04 unbacked RemovedAtomSink 不得 strict；
- R7-05 public tests 检查 records + 所有 indexes；
- R7-06 index-only leakage mutation 被捕获；
- positive protection tests 全部通过；
- G08 包含全部 Round 7 关键 nodes；
- 删除代表性 Round 7 node → G08 FAIL；
- M1–M77 无回退；
- M78–M83 全部 caught；
- contracts 全绿；
- P1 tests 全绿；
- full suite 全绿；
- zero skip/xfail/xpass；
- P0 Gate 10/10；
- G08/G09 无 implementation failure；
- JSON/Markdown evidence 一致；
- current evidence 无 stale blocker；

才允许 `SUBMISSION_TO_CHATGPT_P1_ROUND_7.md` 最后两条状态为：

```text
READY_FOR_CHATGPT_P1_ROUND_7_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
```

两行中间保留一个空行。文件末尾不得追加解释。

如果任何内部问题仍失败：

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
CHATGPT APPROVED
```

---

## 24. 最终科学验收语义

完成后必须能够证明：

```text
fully mapped participant
不是“map list 非空”
而是 molecule heavy-atom content 与 unique map count 一致

mapped_fraction=1.0
不能覆盖 map underflow/overflow

global mapped_heavy_atom_fraction=1.0
不能覆盖 participant-level contradiction

atom map IDs
必须是有效正整数

同一 atom source/sink/transfer/mechanistic target
不能被重复计数

RemovedAtomSink formal_assignment=False
在无其他 authority 时不能 strict

records lane 非 strict
还必须证明没有泄漏到 production index

上述反例通过 public build_snapshot
不能进入 strict donor truth

Round 3–6 已正确 invariant
全部保持
```

请严格执行：

```text
先读取
→ 冻结基线
→ 复现
→ genuine baseline
→ RED
→ 最小实现
→ records + indexes
→ G08
→ M78–M83
→ M1–M77
→ 串行完整回归
→ evidence/worklog/submission
→ 等待 ChatGPT
```

P2 继续 BLOCKED。
