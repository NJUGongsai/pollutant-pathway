# P1 Round 6 严格整改任务书

> **交付对象：** 新开的 AI coding agent（Claude、Qwen、Codex 等）  
> **项目根目录：** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`  
> **依据：** ChatGPT 对 `SUBMISSION_TO_CHATGPT_P1_ROUND_5.md` 的独立只读审核  
> **本轮性质：** P1 strict scientific boundary 的最小整改，不是 P2 开发  
> **最终验收人：** ChatGPT  
> **日期：** 2026-07-31

---

## 0. 正式审核结论

Round 5 未通过 ChatGPT 只读审核。

正式状态：

```text
CHATGPT_P1_ROUND_5_READ_ONLY_AUDIT = REJECTED
rejection_class = IMPLEMENTATION_FAILURE
P1-G08_EFFECTIVE_STATUS = FAIL
P1_STATUS = BLOCKED
P2_STATUS = BLOCKED
```

注意：

- Round 5 报告中的既有测试数字大体真实；
- 不是因为既有 57 个 G08 节点没有运行；
- 不是因为 M1–M72 没有运行；
- 不是因为 P0 Gate 回退；
- 是因为 G08 mandatory manifest 没有覆盖任务书已经明确要求的全部 invariant；
- ChatGPT 额外构造的 schema-valid 反例仍能进入 `strict_eligible`；
- 这些反例也能通过公开 `build_snapshot()` 路径进入 `records.jsonl` 的 `strict` lane。

因此当前不得进入 P2。

本轮唯一目标：

```text
复现并修复 Round 6 五类 confirmed strict fail-open
→ 补充 direct RED tests
→ 补充 public snapshot RED tests
→ 扩展 G08 mandatory nodes
→ 增加 M73–M77
→ 保留 M1–M72
→ 完整回归
→ 重新提交 ChatGPT 只读审核
```

---

## 1. 先完整阅读这些文件

不要依赖当前聊天记忆。开始修改前，必须按顺序完整阅读：

### 1.1 最终设计与实施权威

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_design.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_plan.md
```

### 1.2 P1 原始训练任务

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/chatgpt_p1_train.md
```

如果文件名或位置有轻微变化，先在 `training/` 内定位实际 P1 任务书，不要跳过。

### 1.3 Round 5 任务、提交与证据

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_5.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_5.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_5_AUDIT_EVIDENCE.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
```

### 1.4 当前核心实现

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/eligibility/engine.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/ledger.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/mapping.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/p1_entities.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/loader.py
```

### 1.5 当前 strict tests、Gate 与 mutations

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_cross_invariants.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_reference_integrity.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_engine.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_nested_evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_complete_evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_gate.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_mutations.py
```

完成阅读后，先在 worklog 记录：

```text
当前 branch
当前 HEAD
working tree 是否 dirty
既有改动是否属于用户
本轮预计修改的文件
本轮不会修改的文件
```

不得使用：

```text
git reset --hard
git checkout --
git clean
```

不得覆盖或丢弃用户已有修改。

---

## 2. 必须保留的 Round 5 正确成果

ChatGPT 已在保持相对目录结构的隔离副本中独立复跑，确认：

```text
P0 contract tests = 290 passed
P1 tests = 471 passed
full suite = 761 passed
skip/xfail/xpass = 0
P0 Gate = 10/10 PASS
P1 Gate = 7 PASS / 3 BLOCKED
P1-G08 current registered nodes = 57/57 passed
P1-G09 = 11/11 passed
M1–M72 = 72/72 caught
```

以下成果必须无回退：

- P0 六个 ADR 和 contract freeze；
- P0 Gate 10/10；
- Round 3 complete canonical snapshot/hash/loader；
- canonical snapshot hash 行为；
- G09 11 个 mandatory nodes；
- M56b 的 G09 deletion protection；
- participant ID uniqueness；
- controlled participant side；
- within-participant map uniqueness；
- same-side cross-participant map uniqueness；
- reactant/product 两侧允许对应使用相同 formal map number；
- actual formal-pair coverage；
- one source → one target；
- one target ← one source；
- exact duplicate formal pair rejection；
- element negative-count 与 delta consistency；
- partial/unbalanced non-zero delta 的诚实分类；
- embedded lineage duplicate；
- reordered-map semantic duplicate lineage；
- public snapshot 已有五类防绕过；
- G08 mandatory-node deletion protection；
- M1–M72 全部原目标。

不允许通过弱化这些规则换取新测试通过。

---

## 3. 本轮禁止事项

本轮禁止：

- 启动或实现 P2；
- 声称 P1 accepted/complete；
- 修改 P0 ADR、final design 或 final plan 来迁就代码；
- 改旧报告数字让 Gate 看起来通过；
- 删除、rename 或放宽既有 tests；
- 从 `_G08_REQUIRED_NODES` 删除已有节点；
- 修改 G08 使其忽略 failed/skipped/xfail/xpass；
- 修改 mutation runner 让 `caught=true` 与真实 invariant 脱钩；
- 用 unrelated blocker 让 negative test “碰巧非 strict”；
- 让所有输入一律 non-strict 的全拒绝式修复；
- fixture-specific participant ID；
- hard-code `r1`、`p1`、proline 或 2OG；
- 用字符串关键词猜测 participant 是否为 cofactor 或 substrate；
- synthetic fixture 冒充 real reaction evidence；
- 安装依赖或联网，除非用户另行明确授权；
- 重写 snapshot canonical payload；
- 无关重构、格式化整个代码库或创建新框架。

每个改动必须能直接追溯到本任务书中的 confirmed fail-open。

---

## 4. 核心科学目标

系统最终目标不是“找到一个类似反应字符串”，而是：

```text
完整 donor reaction evidence
→ 解析 donor 中真实 transformed lineage A→B
→ 使用结构相似性寻找与 query X 对应的 donor A
→ 将 donor transformation 作为受证据约束的 analogy
→ 推测 X 可能转变成哪些 Y
→ 输出完整 provenance、mapping、ledger、assumptions 和 abstention
```

P1 strict donor authority 必须满足：

```text
participant、side、maps、formal pairs、lineage、ledger references、
stoichiometry、cofactor state、atom transfer、mechanistic evidence
均能由 typed evidence 交叉验证。
```

任何不完整、悬空、互相矛盾或只能靠自报字段成立的证据，都不得进入 strict donor truth。

---

## 5. ChatGPT 独立复现结果

以下每个反例：

1. 从 Round 5 的真实 strict baseline 开始；
2. baseline 实际为 `strict_eligible`；
3. 只改变目标条件；
4. 输入符合当前 Pydantic schema；
5. direct decision 错误返回 `strict_eligible`；
6. public `build_snapshot()` 错误写入 `records.jsonl` 的 `strict` lane。

独立结果：

| 反例 | Direct decision | Public lane | 正确预期 |
|---|---|---|---|
| existing cofactor participant + `direction="sideways"` | `strict_eligible` | `strict` | conditional 或 fail-closed，绝不能 strict |
| same reactant entry + coefficients 1 和 2 | `strict_eligible` | `strict` | conflict，never strict |
| same stoichiometry participant/side + coefficients 1 和 2 | `strict_eligible` | `strict` | conflict，never strict |
| mechanistic target map 只存在于 reactant side | `strict_eligible` | `strict` | target 必须由 product map registry 解析 |
| formal transfer assignment 的 transferred maps 为空 | `strict_eligible` | `strict` | 空壳 assignment，never strict |
| `CCO` participant 无 maps，但 `mapped_fraction=1.0` | `strict_eligible` | `strict` | mapped claim 无证据，never strict |

这五类问题按科学 invariant 计为：

```text
R6-01 uncontrolled cofactor direction
R6-02 duplicate/conflicting stoichiometric authority
R6-03 mechanistic target uses wrong side registry
R6-04 empty formal atom transfer assignment
R6-05 heavy-atom participant with empty map evidence
```

---

## 6. R6-01：CofactorChange.direction 必须受控

### 6.1 当前缺陷

当前 schema：

```python
class CofactorChange(StrictModel):
    participant_id: NonEmptyStr
    oxidized_form: NonEmptyStr | None = None
    reduced_form: NonEmptyStr | None = None
    direction: NonEmptyStr = "unknown"
```

当前 `_validate_cofactor_changes()` 只验证 participant 是否存在。

当前 `_classify_state()` 只在：

```python
cc.direction == "unknown"
```

时进入 conditional。

因此：

```python
CofactorChange(participant_id="r1", direction="sideways")
```

绕过了 unknown policy 并进入 strict。

### 6.2 正确要求

- participant 必须存在；
- `direction="unknown"` 保留已有 conditional policy；
- 任意没有 frozen typed authority 的 direction 不得 strict；
- 不能因为它是非空字符串就当作已知方向；
- 不得自行凭感觉发明 direction vocabulary；
- 先查 final design、P0 schema/ADR、现有 builder 和 tests；
- 如果没有冻结的已知方向词表，本轮采取保守策略：

```text
unknown → conditional
其他无 authority 的值 → strict fail closed
```

- 如果最终确实需要已知 direction vocabulary，必须在 worklog 写明：

```text
词表来源
现有 schema authority
为什么某值可被 strict 接受
```

不得通过修改 final design 或 P0 ADR 临时创造 authority。

### 6.3 必须先写的 RED tests

至少：

```text
test_uncontrolled_cofactor_direction_never_strict
test_unknown_cofactor_direction_remains_conditional
test_public_snapshot_cannot_promote_uncontrolled_cofactor_direction
```

negative test 必须使用真实存在的 participant，避免由 ghost participant blocker “碰巧捕获”。

reason 必须包含稳定 token，例如：

```text
cofactor_change_direction
```

---

## 7. R6-02：同一 stoichiometric authority 的冲突条目必须 fail closed

### 7.1 当前缺陷

当前：

```python
key = (entry.participant_id, entry.side, entry.coefficient)
```

这只捕获完全相同的三元组。

以下两条会被视为不同 key：

```text
(r1, reactant, 1)
(r1, reactant, 2)
```

但它们对同一 participant/side 声明了互相冲突的 coefficient。

### 7.2 正确 authority

对：

```text
ledger.reactant_entries
ledger.product_entries
ledger.stoichiometry
```

至少使用：

```text
(participant_id, side)
```

作为单条 stoichiometric authority key。

必须区分：

```text
同 key + 同 coefficient → duplicate
同 key + 不同 coefficient → conflict
```

两者均不得静默重复计数，也不得 strict。

不要强制 collection 非空；空 collection 的既有合法语义保持。

不要无依据地要求：

```text
reactant_entries 与 stoichiometry 必须逐项完全相等
```

本轮只修复每个 collection 内部已确认的 duplicate/conflict fail-open。若发现跨 collection authority 冲突，先记录并说明现有 design authority，再决定是否纳入，不得静默扩大范围。

### 7.3 必须先写的 RED tests

至少：

```text
test_duplicate_reactant_entry_never_strict
test_conflicting_reactant_entry_coefficients_never_strict
test_duplicate_product_entry_never_strict
test_conflicting_product_entry_coefficients_never_strict
test_duplicate_stoichiometry_entry_never_strict
test_conflicting_stoichiometry_coefficients_never_strict
test_public_snapshot_cannot_promote_conflicting_reactant_entries
test_public_snapshot_cannot_promote_conflicting_stoichiometry
```

每个 test：

- 先 assert baseline strict；
- 只增加目标 duplicate/conflict；
- participant 存在；
- side 正确；
- coefficients 都为正；
- 避免被 wrong-side/negative coefficient 捕获；
- assert invariant-specific reason。

建议 reason tokens：

```text
reactant_entry_duplicate
reactant_entry_conflict
product_entry_duplicate
product_entry_conflict
stoichiometry_duplicate
stoichiometry_conflict
```

---

## 8. R6-03：MechanisticOriginEvidence target 必须使用 product map registry

### 8.1 当前缺陷

任务书要求：

```text
target_atom_map_numbers 能在 product/map registry 中解析
```

当前实现却将所有 participant maps 合并：

```python
all_maps = union(all participant maps)
```

然后只判断 target map 是否存在于任意 participant。

这会接受：

```text
target map 只存在于 reactant side
product side 不存在该 map
```

### 8.2 必须复现的具体反例

使用：

```text
reactant r1 maps = [1, 2, 3]
product  p1 maps = [1, 2, 4]
```

formal pairs：

```text
r1:1 → p1:1
r1:2 → p1:2
r1:3 → p1:4
```

lineage transformed reactant maps：

```text
[1, 2, 3]
```

mechanistic evidence：

```python
MechanisticOriginEvidence(
    evidence_id="me_r_only",
    evidence_type="isotope_tracing",
    source_participant_id="r1",
    target_atom_map_numbers=[3],
)
```

map 3 存在于 reactant，但不存在于 product。

修复前必须证明它为 RED。

### 8.3 正确要求

- evidence ID 唯一；
- source participant 非空时必须存在；
- target maps 必须由 product-side map authority 解析；
- 不能使用 reactant/product 全局 map union；
- 不能只检查 map number 在某处出现；
- 已有 completely unknown map=999 test 必须保留；
- AddedAtomSource → mechanistic evidence ID linkage 必须保留；
- formal mapping 仍然不等于 mechanistic origin。

最小实现优先使用已经建立的：

```text
registry["product_map_registry"]
```

不要创建第二套漂移的 map registry。

### 8.4 必须先写的 RED tests

至少：

```text
test_mechanistic_target_map_must_exist_on_product_side
test_mechanistic_target_product_map_remains_valid
test_public_snapshot_cannot_promote_reactant_only_mechanistic_target_map
```

正向 test 必须证明真实 product map 不会被全拒绝式修复破坏。

建议 reason token：

```text
mechanistic_evidence_product_map
```

---

## 9. R6-04：FormalAtomTransferAssignment 不得是空壳

### 9.1 当前缺陷

当前 schema 允许：

```python
transferred_atom_map_numbers: list[int] = []
```

validator 只循环检查列表中的 maps。

空列表会以 vacuous truth 通过：

```text
不存在 unknown map
不存在 unsupported map
不存在 pair conflict
```

但一条没有转移任何 atom 的 formal atom transfer assignment 不应成为 strict evidence。

### 9.2 正确要求

- 整个 `formal_atom_transfer_assignments` collection 可以为空；
- 但只要 collection 中存在 assignment：
  - transferred map list 必须非空；
  - map list 内不得重复；
  - 每个 map 必须属于 source participant；
  - 每个 map 必须由 exact source→target formal edge 支撑；
  - assignment method 必须为冻结的 formal value；
  - source 必须是 reactant；
  - target 必须是 product。

不要错误要求所有 strict reaction 都必须有 formal-transfer assignment；这是 assignment-level validation，不是 collection requiredness。

### 9.3 必须先写的 RED tests

至少：

```text
test_empty_formal_transfer_maps_never_strict
test_duplicate_formal_transfer_maps_never_strict
test_valid_nonempty_formal_transfer_remains_strict
test_public_snapshot_cannot_promote_empty_formal_transfer
```

建议 reason tokens：

```text
formal_atom_transfer_empty
formal_atom_transfer_duplicate_map
```

---

## 10. R6-05：含重原子的 participant 不能靠 mapped_fraction 自报绕过

### 10.1 当前缺陷

当前代码：

```python
if p.mapped_fraction < 1.0:
    fail
```

但后面的 actual map coverage 对空列表执行：

```python
if not p.atom_map_numbers:
    continue
```

因此：

```text
canonical_smiles = CCO
atom_map_numbers = []
mapped_fraction = 1.0
```

仍可进入 strict。

### 10.2 科学边界

不能简单规定所有 participant 必须有 heavy-atom maps，因为：

- proton；
- electron；
- 零重原子 participant；
- hydrogen/proton/electron policy；

可能有合法空 map 情形。

但明显含重原子的可解析 molecule：

```text
CCO
```

不能：

```text
atom_map_numbers=[]
mapped_fraction=1.0
```

仍被当成 fully mapped。

### 10.3 正确要求

优先复用当前环境中已经存在的 chemistry/molecule evidence。

ChatGPT 独立运行时检测到：

```text
rdkit = 2026.03.4
```

但不要仅根据这行文字假设。实现前重新运行当前 `.venv` 的只读 probe。

建议最小语义：

```text
SMILES 可解析且 heavy_atom_count > 0：
    atom maps 必须存在；
    unique map count 必须与可验证 heavy-atom mapping claim 相容；

SMILES 可解析且 heavy_atom_count == 0：
    按 hydrogen/proton/electron policy 和现有 schema authority 处理；

SMILES 无法解析或无法证明：
    strict fail closed；
    reason 说明无法验证，而不是猜测。
```

必须同时保留：

- participant side vocabulary；
- same-side map uniqueness；
- formal-pair actual coverage；
- reactant/product 对应 map 合法；
- mapped fraction threshold；
- global mapped-heavy-atom summary 不覆盖 participant-level contradiction。

不要只加：

```python
if not maps:
    fail
```

因为这可能错误拒绝合法质子/电子。

不要在 strict validator 内 silently repair maps。

### 10.4 必须先写的 RED tests

至少：

```text
test_heavy_atom_participant_with_empty_maps_never_strict
test_mapped_fraction_one_cannot_override_empty_heavy_atom_maps
test_valid_fully_mapped_heavy_atom_participant_remains_strict
test_zero_heavy_atom_policy_does_not_get_accidentally_broken
test_public_snapshot_cannot_promote_unmapped_heavy_atom_participant
```

如果现有 schema 无法构造一个合法 zero-heavy-atom positive case：

- 不要伪造；
- 在 worklog 记录 schema limitation；
- 至少保证 heavy-atom case fail closed；
- 不要声称 zero-heavy-atom 语义已完整验证。

建议 reason token：

```text
participant_heavy_atom_map_evidence
```

---

## 11. 两个额外需要冻结的空壳 evidence 风险

这两项不是 ChatGPT 否决 Round 5 的唯一依据，但已被独立复现，应在 Round 6 明确处理或给出设计约束。

### 11.1 AddedAtomSource 非 formal 且无 mechanism

当前：

```python
AddedAtomSource(
    atom_map_number=1,
    source_participant_id="r1",
    formal_assignment=False,
    mechanistic_evidence_id=None,
)
```

仍会 `strict_eligible`。

必须查明冻结语义：

```text
formal_assignment=False 时，是否必须有可解析 mechanistic evidence？
如果没有任何 authority，为什么可以 strict？
```

如果 final design 没有允许其 strict 的 typed authority，fail closed。

建议 RED：

```text
test_nonformal_added_atom_source_without_mechanism_never_strict
```

### 11.2 MechanisticOriginEvidence 空 target

当前：

```python
MechanisticOriginEvidence(
    evidence_id="me1",
    evidence_type="isotope_tracing",
    source_participant_id="r1",
    target_atom_map_numbers=[],
)
```

仍会 `strict_eligible`。

必须冻结：

```text
一条 mechanistic origin evidence 是否必须至少指向一个 product atom？
```

如果没有非空 target，它不能靠 vacuous truth 成为 strict mechanism authority。

建议 RED：

```text
test_empty_mechanistic_target_maps_never_strict
```

如果你认为这两条依据不足，不得静默忽略。必须在 worklog 明确写：

```text
查阅了哪些 design/schema authority
最终采用何种语义
为什么不会把 unproven evidence 变成 strict truth
```

---

## 12. RED test 质量合同

每个 negative test 必须：

1. 使用真正 strict 的 baseline；
2. 在 mutation 前 assert baseline 为 `strict_eligible`；
3. 只修改一个目标条件；
4. 输入必须符合当前 schema；
5. assert direct result 不是 strict；
6. assert reason 含 invariant-specific token；
7. 适用时 assert 正确 lane；
8. 不得由 unrelated blocker 捕获；
9. 不得通过删除 positive evidence 让它自然 non-strict；
10. 保留对应 positive protection test。

每个 public test 必须：

1. 使用公开 `SnapshotEvidenceItem`；
2. 调用真实 `build_snapshot()`；
3. 读取真实生成的 `records.jsonl`；
4. 同时检查适用的 production/diagnostic/quarantine index；
5. bad record 不得出现在 strict production；
6. 不能只调用 `decide_eligibility()` 假装 public boundary 已验证；
7. 临时输出只能写测试临时目录。

---

## 13. 最小实现原则

优先修改：

```text
reaction_agent/eligibility/engine.py
tests/p1/test_eligibility_reference_integrity.py
scripts/run_p1_gate.py
scripts/run_p1_mutations.py
```

只有存在明确必要性时才修改 schema。

理由：

- Round 6 问题主要是 cross-object strict validation；
- 当前 schema 允许表达 incomplete/diagnostic evidence，并不一定应该在 Pydantic construction 时全部拒绝；
- strict/non-strict authority 主要属于 eligibility engine；
- 不应为了让 strict tests 通过而破坏 diagnostic lane 对原始不完整 evidence 的保存能力。

如果修改 schema：

- 必须说明为何 engine-level fail closed 不足；
- 必须检查所有 snapshot/loader/serialization contract；
- 必须保持 backward evidence readability；
- 必须证明不是为了隐藏 strict decision bug。

不要新建 validation framework。复用现有：

```text
participant registry
reactant/product map registry
maps_by_participant
central ledger-reference validator
formal edge registry
```

---

## 14. G08 mandatory-node manifest

当前 G08 的 deletion-protection 机制正确，必须保留。

Round 6 必须：

1. 保留现有 57 个节点；
2. 将本轮所有关键 RED tests 显式加入 `_G08_REQUIRED_NODES`；
3. G08 继续真实运行新增 test 文件；
4. 不允许只依赖 full suite；
5. missing file/node → G08 FAIL；
6. failed/skipped/xfail/xpass → G08 FAIL；
7. 报告实际 mandatory total、collected、passed；
8. 增加 deletion mutation，证明至少一个 Round 6 节点被删会使 G08 FAIL；
9. G08 implementation failure 不得被 G03/G04/G10 BLOCKED 掩盖。

本轮必须理解：

```text
M56/M56c 只证明“已列出的节点不能删除”
Round 6 仍必须证明“新增列表覆盖本任务书的 confirmed fail-open”
```

不能只增加总数量，不列出具体 nodes。

---

## 15. 新增 mutations：M73–M77

保留：

```text
M1–M72
```

新增建议：

| Mutation | 目标反例 | 必须捕获 |
|---|---|---|
| M73 | existing cofactor participant + uncontrolled direction | never strict；public lane 非 strict |
| M74 | same participant/side 的 duplicate/conflicting coefficients | never strict |
| M75 | mechanistic target map 只存在于 reactant side | never strict；必须由 product registry 捕获 |
| M76 | FormalAtomTransferAssignment transferred maps 为空 | never strict；public lane 非 strict |
| M77 | heavy-atom participant maps 为空但 mapped_fraction=1 | never strict；public lane 非 strict |

允许使用子结果：

```text
M74a reactant_entries conflict
M74b product_entries conflict
M74c stoichiometry conflict
M76a empty maps
M76b duplicate maps
M77a direct
M77b public
```

但 mutation authority 仍按：

```text
M1–M77
```

汇总。

每项必须记录：

```text
mutation_id
schema-valid mutated input summary
baseline eligibility
expected
actual eligibility
actual reason
public lane（适用时）
caught
```

`caught=true` 必须来自目标 invariant-specific reason，不能来自 unrelated failure。

Mutation runner 必须：

- 使用临时目录或可逆 monkeypatch；
- 不修改真实 workspace source；
- 不覆盖真实 Gate evidence；
- 异常时恢复；
- M1–M72 无回退。

---

## 16. 执行顺序

严格按以下顺序：

### R6-T1：冻结当前基线

运行并记录：

```text
contracts
tests/p1
full tests
P0 Gate
P1 Gate
M1–M72
```

基线必须与 Round 5 提交相符；如不符，先报告差异，不能带着未知基线修改。

### R6-T2：独立复现五类反例

在不修代码时复现：

```text
R6-01
R6-02
R6-03
R6-04
R6-05
```

保存精简 RED evidence：

```text
case
schema-valid construction
baseline
expected
actual direct result
actual public lane
```

### R6-T3：先写 direct RED tests

确认新增测试在旧实现上真实失败。

### R6-T4：写 public boundary RED tests

确认 bad objects 真实进入了旧实现的 public strict lane。

### R6-T5：做最小集中实现

修复现有 validators，不创建新框架。

### R6-T6：运行定向 tests

确认：

- 所有新增 negative tests 变绿；
- 所有 positive protection tests 保持；
- reason 是目标 invariant；
- public lane 正确。

### R6-T7：扩展 G08

接入所有关键 Round 6 nodes，运行 deletion protection。

### R6-T8：增加 M73–M77

运行 M1–M77。

### R6-T9：完整回归

运行 contracts、P1、full suite、P0 Gate、P1 Gate、mutations。

### R6-T10：报告和提交

更新 worklog，生成 Round 6 evidence 和 submission。

---

## 17. 必须执行的验收命令

从项目根目录：

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
```

### 17.1 定向 reference-integrity tests

```bash
.venv/bin/python -m pytest \
  tests/p1/test_eligibility_reference_integrity.py \
  -q
```

### 17.2 其他 strict tests

```bash
.venv/bin/python -m pytest \
  tests/p1/test_eligibility_cross_invariants.py \
  tests/p1/test_eligibility_fail_closed.py \
  tests/p1/test_eligibility_engine.py \
  -q
```

### 17.3 Snapshot public boundary

```bash
.venv/bin/python -m pytest \
  tests/p1/test_snapshot_builder.py \
  tests/p1/test_snapshot_nested_evidence.py \
  tests/p1/test_snapshot_complete_evidence.py \
  -q
```

如果新增 public tests 位于 reference-integrity 文件，上述文件也必须一并运行。

### 17.4 P0 contracts

```bash
.venv/bin/python -m pytest tests/contracts -q
```

### 17.5 P1 tests

```bash
.venv/bin/python -m pytest tests/p1 -q
```

### 17.6 Full suite

```bash
.venv/bin/python -m pytest tests -q
```

必须记录：

```text
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

预期：

```text
G08 无 implementation failure
G09 无回退
G03/G04/G10 可继续因真实外部输入 BLOCKED
overall 仍可能 BLOCKED
```

不得把外部 BLOCKED 写成 PASS。

### 17.9 Mutations

```bash
.venv/bin/python scripts/run_p1_mutations.py
```

必须：

```text
M1–M77 = 77/77 caught
```

并保留所有 sub-results。

---

## 18. P1 Gate 正确聚合语义

修复前，ChatGPT 审核后的有效矩阵是：

| Gate | 有效状态 |
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

修复并完整回归后，合理预期是：

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
overall BLOCKED
```

即：

```text
7 PASS
0 FAIL
3 BLOCKED
```

但只有在新增反例、G08 nodes 和 mutations 全部真实通过后，才能这样报告。

---

## 19. 必须更新或生成的证据

至少更新：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/mutation_results.json
```

新增：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/eligibility_reference_integrity_results_round_6.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/eligibility_semantic_invariant_results_round_6.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results_round_6.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_6_AUDIT_EVIDENCE.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_6.md
```

不要删除 Round 2–5 的历史 evidence。

Round 6 JSON evidence 至少包含：

```text
round
branch
head
working_tree
changed_files
test_counts
zero_skip_xfail_xpass
p0_gate
p1_gate
g08_mandatory_total
g08_mandatory_collected
g08_mandatory_passed
g09_mandatory_total
mutations_total
mutations_caught
M1–M72_preserved
M73–M77_subresults
R6-01 evidence
R6-02 evidence
R6-03 evidence
R6-04 evidence
R6-05 evidence
public_snapshot_lanes
snapshot_hash
external_blockers
p2_status
```

JSON 与 Markdown 的数字必须来自同一次最终运行。

---

## 20. Worklog 必须记录

在 `P1_REMEDIATION_WORKLOG.md` 新增 Round 6 章节，至少包括：

1. ChatGPT Round 5 rejection；
2. 五类 confirmed fail-open；
3. 修复前 direct 结果；
4. 修复前 public lane；
5. RED tests 文件与 node IDs；
6. RED 阶段实际失败数量；
7. 每个 validator 的最小修改；
8. cofactor direction authority 决策；
9. stoichiometric authority key 决策；
10. product map registry 决策；
11. empty formal-transfer semantics；
12. heavy-atom empty-map semantics；
13. 两个额外空壳 evidence 风险的处理或明确 limitation；
14. G08 新增 mandatory nodes；
15. deletion mutation；
16. M73–M77；
17. M1–M72 回归；
18. contracts/P1/full tests；
19. P0/P1 Gates；
20. snapshot hash 是否变化及原因；
21. external blockers；
22. changed files；
23. assumptions；
24. remaining limitations；
25. P2 继续 BLOCKED。

禁止只写“已修复”而不记录 RED → GREEN 证据。

---

## 21. Round 6 submission 封面

生成：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_6.md
```

至少包含：

1. 项目根；
2. branch / HEAD / dirty status；
3. changed-files 清单；
4. 未修改的冻结文件；
5. 五类问题逐项修复说明；
6. 每类 direct negative evidence；
7. 每类 public snapshot lane evidence；
8. positive protection evidence；
9. G08 mandatory node 明细和数量；
10. G08 deletion mutation；
11. M1–M77 汇总；
12. M73–M77 sub-results；
13. contracts count；
14. P1 tests count；
15. full suite count；
16. zero skip/xfail/xpass；
17. P0 Gate 10/10；
18. P1 Gate 逐项矩阵；
19. snapshot ID/hash；
20. G09 无回退；
21. current runtime dependency probe；
22. G03 blocker；
23. G04 blocker；
24. G10 blocker；
25. worklog 路径；
26. structured evidence 路径；
27. known limitations；
28. P2 状态。

不得只给总数，必须给关键 node 名和关键 mutation evidence。

---

## 22. 最终提交状态规则

只有同时满足：

- R6-01–R6-05 全部修复；
- direct tests 全部通过；
- public snapshot tests 全部通过；
- positive protection tests 全部通过；
- G08 包含所有关键 Round 6 nodes；
- 删除任一代表性 Round 6 node 会使 G08 FAIL；
- M1–M72 无回退；
- M73–M77 全部由目标 invariant 捕获；
- contracts 全绿；
- P1 tests 全绿；
- full suite 全绿；
- zero skip/xfail/xpass；
- P0 Gate 10/10；
- G08/G09 无 implementation failure；
- JSON/Markdown evidence 一致；
- 没有 stale blocker；

才允许 `SUBMISSION_TO_CHATGPT_P1_ROUND_6.md` 以以下两条状态结束：

```text
READY_FOR_CHATGPT_P1_ROUND_6_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
```

这两行必须是文件最后两条状态语句，中间保留一个空行，文件末尾不得再追加解释。

如果任何内部反例仍失败，必须结束为：

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

## 23. 最终验收语义

本轮完成后必须能够证明：

```text
existing cofactor participant
+ arbitrary nonempty direction
不会绕过 unknown policy 进入 strict

同一 participant/side
+ duplicate/conflicting coefficient
不会重复计数或进入 strict

mechanistic target map
只存在于 reactant side
不能冒充 product atom target

formal transfer assignment
+ empty transferred maps
不能通过 vacuous truth 进入 strict

明显含重原子的 participant
+ empty atom maps
+ mapped_fraction=1.0
不能依靠自报 summary 进入 strict

上述反例经过 public build_snapshot
也不能进入 strict production lane

所有 Round 3–5 已正确 invariant
不得回退
```

请坚持：

```text
先完整阅读
→ 冻结基线
→ 独立复现
→ 先 RED
→ 最小集中实现
→ public boundary
→ G08 mandatory
→ M73–M77
→ M1–M72 回归
→ 完整 tests/Gates
→ evidence/worklog/submission
→ 等待 ChatGPT
```

P2 继续 BLOCKED。
