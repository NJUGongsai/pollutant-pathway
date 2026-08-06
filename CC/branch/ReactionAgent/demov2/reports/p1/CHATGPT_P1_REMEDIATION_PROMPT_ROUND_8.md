# P1 Round 8 严格整改任务书

> **交付对象：** 新开的 AI coding agent（Claude、Qwen、Codex 等）  
> **项目根目录：** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`  
> **依据：** ChatGPT 对 `SUBMISSION_TO_CHATGPT_P1_ROUND_7.md` 的独立只读审核  
> **本轮性质：** P1 snapshot-index authority 的最小整改，不是 P2 开发  
> **最终验收人：** ChatGPT  
> **日期：** 2026-07-31

---

## 0. 正式审核结论

Round 7 未通过 ChatGPT 独立只读审核。

正式状态：

```text
CHATGPT_P1_ROUND_7_READ_ONLY_AUDIT = REJECTED
rejection_class = IMPLEMENTATION_FAILURE

P1-G08_EFFECTIVE_STATUS = FAIL
P1-G09_EFFECTIVE_STATUS = FAIL

P1_STATUS = BLOCKED
P2_STATUS = BLOCKED
```

注意：

- Round 7 的 direct strict eligibility 修复大部分是正确的；
- 本轮禁止重新设计或重写 eligibility engine；
- 当前剩余 implementation failure 集中在 snapshot indexes 的真实 public authority；
- 不能因为 pytest、Gate 脚本或 mutation runner 自报全绿而跳过本任务书；
- 必须先独立复现本任务书列出的三个 fail-open。

---

## 1. Round 7 已确认有效且必须保留的成果

ChatGPT 已独立串行复现：

```text
P0 contract tests = 290 passed
P1 tests = 526 passed
full suite = 816 passed
skip / xfail / xpass = 0 / 0 / 0
P0 Gate = 10/10 PASS
P1 Gate 脚本输出 = 7 PASS / 0 FAIL / 3 BLOCKED
G08 mandatory nodes = 112/112 passed
mutation runner 报告 = 83/83 caught
```

下列 Round 7 修复必须保持：

1. heavy-atom map count underflow fail closed；
2. heavy-atom map count overflow fail closed；
3. participant/global `mapped_fraction=1.0` 不得覆盖真实 map-count 矛盾；
4. atom map identifier 必须为正整数；
5. duplicate/conflicting `AddedAtomSource` fail closed；
6. duplicate/conflicting `RemovedAtomSink` fail closed；
7. duplicate/conflicting `FormalAtomTransferAssignment` fail closed；
8. single `MechanisticOriginEvidence` 内 duplicate target maps fail closed；
9. unbacked `RemovedAtomSink(formal_assignment=False)` fail closed；
10. genuine strict baseline = `CC + [1,2]`；
11. proton `[H+]` zero-heavy policy；
12. G08 既有 112 个 mandatory nodes；
13. G09 既有 11 个 mandatory nodes；
14. M1–M82 的真实保护；
15. P0 290 contracts 与 P0 Gate 10/10；
16. synthetic fixture 不冒充 real evidence；
17. G03/G04/G10 的诚实 BLOCKED；
18. snapshot、ledger、mapping、lineage 已有 fail-closed invariant。

不得通过删除上述测试、放宽 reason assertion、降低 Gate 或修改 frozen authority 来完成 Round 8。

---

## 2. 开始前必须完整阅读

不要只读本任务书。必须按以下顺序完整阅读。

### 2.1 Final authority

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_design.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_plan.md
```

重点：

- P1 Data foundation；
- P1 Gate；
- snapshot replayability；
- production index exclusion；
- P2 mini snapshot / truth / fold isolation；
- P1 未通过不得做 candidate performance 承诺。

### 2.2 P1 authority 与历史整改

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/p1_train.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_7.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_7.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_7_AUDIT_EVIDENCE.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
```

### 2.3 当前实现

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/loader.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/p1_entities.py
```

重点读取：

```text
builder._compute_canonical_snapshot_content
builder._build_on_disk_manifest
builder._record_to_jsonl
builder.build_snapshot

loader._read_jsonl
loader._recompute_record_hash
loader._recompute_snapshot_hash
loader.load_snapshot
```

### 2.4 当前 tests / Gates / mutations

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_nested_evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_complete_evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_reference_integrity.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_cross_invariants.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_gate.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_mutations.py
```

重点读取：

```text
G08 mandatory-node manifest
G09 mandatory-node manifest
M56 deletion protection
M83 index-only leakage
Round 7 public helper
loader index-integrity tests
```

---

## 3. 本轮允许和禁止的修改

### 3.1 优先允许修改

```text
reaction_agent/snapshot/builder.py
reaction_agent/snapshot/loader.py
tests/p1/test_snapshot_builder.py
tests/p1/test_snapshot_nested_evidence.py
tests/p1/test_snapshot_complete_evidence.py
scripts/run_p1_gate.py
scripts/run_p1_mutations.py
reports/p1/*
reports/p0/P0_GATE_REPORT.{md,json}
```

如果确实需要一个内部 helper，可在 `snapshot` 模块内增加最小 pure function。

### 3.2 默认禁止修改

除非先证明无法在 snapshot 层修复，否则禁止修改：

```text
reaction_agent/eligibility/engine.py
reaction_agent/schemas/evidence.py
reaction_agent/schemas/mapping.py
reaction_agent/schemas/ledger.py
reaction_agent/schemas/lineage.py
reaction_agent/policies/*
```

### 3.3 绝对禁止修改

```text
plan/final_design.md
plan/final_plan.md
P0 ADRs
P0 frozen contracts
legacy source
../benchmark
../core
```

禁止：

- 修改 final authority 来迁就实现；
- 删除或改名既有 mandatory nodes；
- 减少 G08 112 个既有节点；
- 减少 G09 11 个既有节点；
- 删除 M1–M82；
- 把真实 failure 改成 BLOCKED；
- 把 fixture 当 real evidence；
- 安装依赖；
- 联网；
- 进入 P2；
- 生成 P2 performance；
- 自动 commit / push / merge / reset / stash / clean；
- 删除用户现有 dirty working-tree 内容。

---

## 4. 开工前冻结基线

必须串行运行，不得并发。

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2

.venv/bin/python -m pytest tests/contracts -q -ra
.venv/bin/python -m pytest tests/p1 -q -ra
.venv/bin/python -m pytest tests/contracts tests/p1 -q -ra
.venv/bin/python scripts/run_p0_gate.py
.venv/bin/python scripts/run_p1_gate.py
.venv/bin/python scripts/run_p1_mutations.py
```

预期基线：

```text
contracts = 290 passed
P1 = 526 passed
full = 816 passed
P0 Gate = 10/10 PASS
P1 Gate = 7 PASS / 0 FAIL / 3 BLOCKED
G08 = 112/112 mandatory nodes
G09 = 11/11 mandatory nodes
mutation runner = 83/83 reported caught
```

说明：

- `run_p1_gate.py` 因 overall BLOCKED 返回非零退出码是预期行为；
- 必须区分 expected BLOCKED 与 implementation FAIL；
- 如果基线与上述不同，先记录并停止，不得偷偷更新 baseline 数字；
- baseline freeze 必须写入 Round 8 worklog。

---

## 5. ChatGPT 已独立确认的三个 fail-open

以下结果不是猜测，必须由你在修复前独立复现。

### 5.1 R8-01：hash-coherent diagnostic record 可以进入 production

ChatGPT 对抗步骤：

1. 使用真实 `build_snapshot` 构建一个 diagnostic record；
2. 保持 `records.jsonl` 中：

   ```text
   lane = diagnostic
   eligibility = strict_prohibited
   ```

3. 将同一完整 record 注入 `production_index.jsonl`；
4. 按当前 canonical 规则重新生成 snapshot hash；
5. 同步 temp snapshot 的 manifest 与 COMPLETE marker；
6. 调用真实 `load_snapshot(temp_snapshot_path)`。

修复前实际结果：

```json
{
  "coherent_diagnostic_in_production_loader": {
    "accepted": true
  }
}
```

根因：

当前 loader 只检查：

```text
index reaction_id exists in records
index lane == full record lane
index record_content_hash == full record record_content_hash
```

但未检查：

```text
production_index 只允许 strict / conditional
diagnostic_index 只允许 diagnostic
quarantine_index 只允许 quarantine
```

因此：

```text
diagnostic entry in production
```

仍然满足：

```text
entry lane == full record lane
entry hash == full record hash
```

loader 会错误接受。

### 5.2 R8-02：diagnostic index 可被清空而不触发 hash/loader

ChatGPT 对抗步骤：

1. 使用真实 builder 生成含 diagnostic record 的合法 snapshot；
2. 确认 `diagnostic_index.jsonl` 非空；
3. 清空 `diagnostic_index.jsonl`；
4. 不修改 manifest；
5. 不修改 snapshot hash；
6. 不修改 COMPLETE marker；
7. 调用真实 `load_snapshot`。

修复前实际结果：

```json
{
  "accepted": true,
  "diagnostic_before_nonempty": true,
  "diagnostic_after_empty": true
}
```

根因：

当前 canonical snapshot content 包含：

```text
production_index_hash
quarantine_index_hash
```

但不包含：

```text
diagnostic_index_hash
```

loader 也没有验证：

```text
每个 records lane=diagnostic 的记录
必须恰好出现在 diagnostic_index
```

所以 diagnostic audit evidence 可以静默消失。

### 5.3 R8-03：index entry 嵌套内容可被篡改而 loader 接受

ChatGPT 对抗步骤：

1. 使用真实 builder 生成 strict snapshot；
2. 只修改 `production_index.jsonl` 中完整 entry 的嵌套内容，例如：

   ```text
   reaction_evidence.participants[0].canonical_smiles
   ```

3. 保持该 index entry 自报的 `record_content_hash` 不变；
4. 不修改 `records.jsonl`；
5. 不修改 manifest；
6. 不修改 snapshot hash；
7. 不修改 COMPLETE marker；
8. 调用真实 `load_snapshot`。

修复前实际结果：

```json
{
  "accepted": true,
  "mutated_nested_payload": true
}
```

根因：

loader 当前只比较 index entry 自报的：

```text
record_content_hash
```

与 full record 自报的：

```text
record_content_hash
```

它没有：

- 对 index entry 本身重新计算 content hash；
- 或 canonical 比较 index entry 与 records full record；
- 或禁止同 ID/hash 但嵌套 payload 不同。

这意味着 P2 如果直接读取 production index，可能读到与 frozen records authority 不同的反应结构。

---

## 6. R8-04：当前 M83 不能作为 Gate 捕获证据

当前 M83：

1. 在 temp snapshot 注入 diagnostic record 到 production；
2. 读取 production IDs；
3. 在 mutation runner 自己内部执行：

   ```python
   assert rid not in prod_after, "unexpected production membership"
   ```

4. 捕获自己产生的 `AssertionError`；
5. 将 M83 标为 caught。

它没有调用：

- `load_snapshot`；
- G08；
- G09；
- mandatory public test；
- reusable production-boundary authority。

所以修复前的 M83 只证明：

```text
mutation runner 能读到它自己刚写入 production 的 ID
```

不能证明：

```text
真实 public authority / Gate 会拒绝 index-only leakage
```

Round 7 报告中的：

```text
M83 proves index-only leakage is caught by the Gate/public boundary
```

目前不成立。

---

## 7. Round 8 冻结的 index partition contract

这是本轮唯一权威语义，不得自行改写。

### 7.1 records authority

`records.jsonl` 是完整记录 authority。

每个 record 必须：

- 有唯一 `reaction_id`；
- 有完整 nested payload；
- `record_content_hash` 可由完整 record 重新计算；
- stored lane 与 eligibility decision re-derived lane 一致。

### 7.2 expected index membership

从 `records.jsonl` 重建唯一 expected partition：

```text
record lane = strict
    → production_index exactly once

record lane = conditional
    → production_index exactly once

record lane = diagnostic
    → diagnostic_index exactly once

record lane = quarantine
    → quarantine_index exactly once
```

### 7.3 forbidden membership

```text
strict / conditional
    不得出现在 diagnostic_index
    不得出现在 quarantine_index

diagnostic
    不得出现在 production_index
    不得出现在 quarantine_index

quarantine
    不得出现在 production_index
    不得出现在 diagnostic_index
```

### 7.4 completeness

三个 index 的并集必须与 `records.jsonl` reaction IDs 完全相等：

```text
production_ids
∪ diagnostic_ids
∪ quarantine_ids
= record_ids
```

### 7.5 disjointness

三个 indexes 必须两两不相交：

```text
production ∩ diagnostic = ∅
production ∩ quarantine = ∅
diagnostic ∩ quarantine = ∅
```

### 7.6 uniqueness

必须拒绝：

- `records.jsonl` 中 duplicate reaction ID；
- 任一 index 内 duplicate reaction ID；
- 同一 reaction ID 跨 indexes 出现；
- 一个 expected member 缺失；
- 一个 unexpected member 多出。

### 7.7 payload equality

每个 index entry 必须与 `records.jsonl` 中对应 full record 完全一致。

至少必须同时做到：

1. 对 index entry 重新计算 record hash；
2. recomputed hash == entry stored hash；
3. entry stored hash == full record stored hash；
4. index entry canonical payload == full record canonical payload。

禁止只相信 index entry 自报的 `record_content_hash`。

### 7.8 diagnostic integrity

`diagnostic_index.jsonl` 必须进入 immutable snapshot integrity。

优先实现：

```text
diagnostic_hashes = sorted(record_content_hashes)
diagnostic_index_hash = canonical_hash(diagnostic_hashes)
```

并将其加入：

- builder canonical snapshot content；
- on-disk manifest extended fields；
- loader canonical recomputation；
- snapshot determinism tests；
- manifest completeness tests。

这不要求修改 frozen P0 schema。

`SnapshotManifest` public core model不必为此扩大；on-disk manifest 可以持久化 extended field。

如果你选择不新增 public schema field，仍必须保证：

- on-disk manifest 存在 `diagnostic_index_hash`；
- overall snapshot hash 绑定 diagnostic index；
- loader 精确重建并交叉验证。

---

## 8. 建议的最小实现结构

优先在 `reaction_agent/snapshot/loader.py` 增加一个集中、纯、可测试的 index authority validator。

示意：

```python
def _validate_index_partition(
    all_records: list[dict],
    production_records: list[dict],
    diagnostic_records: list[dict],
    quarantine_records: list[dict],
) -> None:
    ...
```

它必须在 snapshot hash 最终判定之前运行。

职责：

1. 验证 records IDs 唯一；
2. 验证每个 index IDs 唯一；
3. 对每个 full record 重算 hash；
4. 对每个 index entry 重算 hash；
5. exact compare index entry 与 full record；
6. 从 records lane 重建 expected membership；
7. 精确比较 actual vs expected；
8. 检查 disjointness；
9. 检查 missing/unexpected/duplicate/overlap；
10. 返回稳定、typed、可审计错误。

不要在多个 test helper、Gate 和 loader 里各自复制一套不同规则。

### 8.1 错误类型

为保持兼容，可继续抛：

```text
SnapshotHashMismatchError
```

但 message 必须含稳定 reason token。

建议：

```text
index_record_duplicate
index_entry_duplicate
index_entry_content_mismatch
index_entry_hash_mismatch
index_partition_wrong_lane
index_partition_missing
index_partition_unexpected
index_partition_overlap
diagnostic_index_hash_mismatch
```

测试必须 assert specific token，不能只写：

```python
with pytest.raises(Exception):
```

### 8.2 builder

builder 必须：

- 继续按 lane 构建三个 indexes；
- 加入 `diagnostic_index_hash`；
- 不改变 production = strict + conditional；
- 不改变 diagnostic/quarantine lane 分类；
- 不改变 record canonical payload；
- 同一 config + same items 仍 deterministic；
- snapshot hash 因新增 diagnostic authority 合理变化时，必须记录原因。

### 8.3 loader

loader 必须：

- 读取三个真实 index 文件；
- 在信任 index payload 之前完成完整验证；
- 不接受 hash-coherent semantic wrong partition；
- 不接受 missing diagnostic index member；
- 不接受 nested index payload mutation；
- 不把普通 partition failure 报成 generic unrelated error；
- 保持 read-only；
- 不自动修复 snapshot；
- 不重写任何 index。

---

## 9. 必须先写的 RED tests

以下 tests 必须先在旧实现上失败，再进行实现修改。

建议放在：

```text
tests/p1/test_snapshot_nested_evidence.py
```

如需复用 deterministic fixture helper，可有限修改：

```text
tests/p1/test_snapshot_builder.py
tests/p1/test_snapshot_complete_evidence.py
```

必须至少新增以下节点，名字不得无故改写：

```text
test_loader_rejects_hash_coherent_diagnostic_in_production
test_loader_rejects_hash_coherent_quarantine_in_production
test_loader_rejects_hash_coherent_strict_in_diagnostic
test_loader_rejects_missing_diagnostic_member_without_metadata_change
test_loader_rejects_missing_production_member
test_loader_rejects_missing_quarantine_member
test_loader_rejects_duplicate_records_reaction_id
test_loader_rejects_duplicate_index_reaction_id
test_loader_rejects_cross_index_membership
test_loader_rejects_mutated_nested_production_index_payload
test_loader_rejects_mutated_nested_diagnostic_index_payload
test_loader_accepts_exact_complete_index_partition
test_conditional_record_is_only_in_production_index
test_diagnostic_index_content_changes_snapshot_hash
test_snapshot_manifest_persists_diagnostic_index_hash
```

如果当前 fixture 无法构建某一 lane，可建立最小 synthetic fixture，但必须：

- 明确标记 synthetic；
- 不冒充 real reaction；
- 只改变目标条件；
- 不引入 unrelated hash failure；
- 不污染 workspace snapshot。

---

## 10. RED test 质量合同

每个 negative test 必须：

1. 从 loader 可以成功读取的合法 snapshot 开始；
2. mutation 前 assert `load_snapshot` 成功；
3. mutation 前 assert expected index membership；
4. 只修改一个目标条件；
5. mutation 发生在 temp directory；
6. 不修改真实 workspace snapshot；
7. 调用真实 public `load_snapshot` 或集中 production validator；
8. assert `SnapshotHashMismatchError` 或冻结的兼容 error；
9. assert invariant-specific token；
10. 证明 failure 来自 index authority；
11. 不得由 missing file、JSON parse、generic hash mismatch、collection failure 捕获；
12. 保留对应 positive protection。

对 hash-coherent wrong-partition tests：

- 允许在 temp snapshot 中按当前 canonical contract 重建 manifest/hash/COMPLETE；
- 目的不是模拟未授权攻击；
- 目的是证明 loader 能拒绝内部自洽但语义错误的 snapshot；
- failure 必须来自 `index_partition_*`，不能来自普通 stored/recomputed hash 不一致。

对 nested payload mutation tests：

- 不更新 entry 自报 `record_content_hash`；
- 不更新 records；
- 不更新 manifest/hash/COMPLETE；
- loader 必须通过重算 index entry payload 捕获；
- failure token 应为 `index_entry_content_mismatch` 或 `index_entry_hash_mismatch`。

对 missing diagnostic test：

- 只清空或删除该 member；
- manifest/hash/COMPLETE 保持不变；
- loader 必须拒绝；
- 不能再出现 Round 7 的 accepted behavior。

---

## 11. G08 mandatory authority

Round 7 已有：

```text
G08 = 112 mandatory nodes
```

这 112 个节点必须全部保留。

Round 8 至少将以下节点加入 G08 mandatory manifest：

```text
test_loader_rejects_hash_coherent_diagnostic_in_production
test_loader_rejects_hash_coherent_quarantine_in_production
test_loader_rejects_cross_index_membership
test_loader_accepts_exact_complete_index_partition
test_conditional_record_is_only_in_production_index
```

G08 需要证明：

- production exclusion 是实际 public authority；
- prohibited/diagnostic/quarantine 不会进入 production；
- conditional 仍合法进入 production；
- exact partition positive protection 不被全拒绝实现破坏。

必须报告：

```text
G08 previous mandatory total = 112
G08 new mandatory total = actual integer > 112
G08 mandatory passed = same integer
```

禁止只报告 pytest collected 总数。

---

## 12. G09 mandatory authority

Round 7 已有：

```text
G09 = 11 mandatory nodes
```

这 11 个节点必须全部保留。

Round 8 至少将以下节点加入 G09 mandatory manifest：

```text
test_loader_rejects_missing_diagnostic_member_without_metadata_change
test_loader_rejects_missing_production_member
test_loader_rejects_missing_quarantine_member
test_loader_rejects_duplicate_records_reaction_id
test_loader_rejects_duplicate_index_reaction_id
test_loader_rejects_mutated_nested_production_index_payload
test_loader_rejects_mutated_nested_diagnostic_index_payload
test_diagnostic_index_content_changes_snapshot_hash
test_snapshot_manifest_persists_diagnostic_index_hash
test_loader_accepts_exact_complete_index_partition
```

G09 需要证明：

- diagnostic index 是 immutable snapshot integrity 的一部分；
- loader 不信任 index 自报 hash；
- indexes 是 complete exact partition；
- same source/config/versions 仍 deterministic；
- valid snapshot 仍可加载；
- index content tampering 被拒绝。

必须报告：

```text
G09 previous mandatory total = 11
G09 new mandatory total = actual integer > 11
G09 mandatory passed = same integer
```

---

## 13. deletion protection

扩展 M56，至少加入：

```text
M56f:
删除一个 Round 8 G08 production-partition mandatory node
→ G08 FAIL

M56g:
删除一个 Round 8 G09 diagnostic-integrity mandatory node
→ G09 FAIL
```

要求：

- temp copy；
- 不修改 workspace；
- 恢复后原 Gate 仍按 expected matrix；
- failure 来自 missing mandatory node；
- 不是 collection error 或 syntax error。

---

## 14. Mutations：重写 M83，并新增 M84–M85

### 14.1 M83：真实 public authority 捕获 production index leak

必须替换当前自我断言版本。

流程：

1. build diagnostic temp snapshot；
2. 确认 mutation 前 `load_snapshot` 成功；
3. 注入 diagnostic record 到 production；
4. 保持 records lane=diagnostic；
5. 调用真实 `load_snapshot` 或唯一集中 validator；
6. 必须拒绝；
7. reason 必须包含：

   ```text
   index_partition_wrong_lane
   ```

   或同义冻结 token；

8. 不能由 generic hash mismatch 捕获；
9. 不能在 mutation runner 内仅依靠自写 `assert rid not in production`；
10. 必须证明 G08/G09 target authority 本身失败。

### 14.2 M84：diagnostic member deletion

流程：

1. build diagnostic temp snapshot；
2. mutation 前 loader 成功；
3. 从 diagnostic index 删除 expected member；
4. 不修改 manifest/hash/COMPLETE；
5. loader 必须拒绝；
6. reason：

   ```text
   index_partition_missing
   ```

   或：

   ```text
   diagnostic_index_hash_mismatch
   ```

7. 优先报告更具体 partition missing；
8. 不能由 missing file/JSON parse 捕获。

### 14.3 M85：index nested payload mutation

流程：

1. build strict temp snapshot；
2. mutation 前 loader 成功；
3. 只修改 production index entry 的 nested chemistry payload；
4. entry 自报 hash保持不变；
5. records/manifest/hash/COMPLETE 保持不变；
6. loader 必须拒绝；
7. reason：

   ```text
   index_entry_content_mismatch
   ```

   或：

   ```text
   index_entry_hash_mismatch
   ```

### 14.4 Mutation 最终要求

```text
M1–M82 preserved
M83 corrected
M84 added
M85 added
M1–M85 = 85/85 caught
```

每个 result 必须是完整对象，不得是空数组。

---

## 15. 次级 semantic risks：只记录，不在本轮擅自修

ChatGPT 还观察到：

```text
同一 AddedAtomSource：
formal_assignment=True / False
但 source + map + mechanistic evidence 相同
→ 当前 strict_eligible

两个 MechanisticOriginEvidence：
内容相同，仅 evidence_id 不同
→ 当前 strict_eligible

同一 FAT edge：
[1] 与 [1,2] 存在 map overlap
→ 当前 strict_eligible
```

本轮不要擅自修改这些语义。

原因：

- 当前 final authority 没有冻结它们是合法独立 evidence、冗余、冲突还是 split authority；
- 擅自 fail closed 可能破坏合法 evidence；
- 它们不是本轮拒绝 Round 7 的主因。

必须在 worklog 的 deferred design decisions 中记录：

```text
must be frozen before P4 evidence aggregation/ranking
not modified in Round 8 without authority
```

---

## 16. 实现顺序

必须按以下顺序：

```text
R8-T1 读取 authority
R8-T2 冻结 Round 7 baseline
R8-T3 独立复现 R8-01 / R8-02 / R8-03 / M83 weakness
R8-T4 写 RED tests
R8-T5 运行 RED，记录具体失败
R8-T6 实现集中 index-partition validator
R8-T7 加入 diagnostic_index_hash
R8-T8 定向 GREEN
R8-T9 扩展 G08/G09 mandatory manifests
R8-T10 扩展 M56f/M56g
R8-T11 重写 M83，新增 M84/M85
R8-T12 运行 M1–M85
R8-T13 串行完整回归
R8-T14 生成 structured evidence
R8-T15 更新 worklog
R8-T16 生成 Round 8 submission
R8-T17 等待 ChatGPT
```

禁止：

- 先写 submission 再补测试；
- 先把 Gate 状态改 PASS；
- 只改 mutation runner 不改 public authority；
- 只改 test helper；
- 只加入 diagnostic hash但不做 exact partition；
- 只做 exact partition但继续相信 index entry 自报 hash；
- 并发运行会写同一 reports 文件的命令。

---

## 17. 定向测试命令

先运行 Round 8 tests：

```bash
.venv/bin/python -m pytest \
  tests/p1/test_snapshot_nested_evidence.py \
  tests/p1/test_snapshot_builder.py \
  tests/p1/test_snapshot_complete_evidence.py \
  -q -ra
```

运行 G08/G09 authority：

```bash
.venv/bin/python scripts/run_p1_gate.py
```

运行 mutations：

```bash
.venv/bin/python scripts/run_p1_mutations.py
```

注意：

- P1 Gate overall BLOCKED 可返回非零；
- 只要 G08/G09 出现 implementation failure，本轮不得提交 ready；
- M83–M85 必须打印实际 typed failure evidence。

---

## 18. 最终串行验收命令

不得并行。

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2

.venv/bin/python -m pytest tests/contracts -q -ra
.venv/bin/python -m pytest tests/p1 -q -ra
.venv/bin/python -m pytest tests/contracts tests/p1 -q -ra
.venv/bin/python scripts/run_p0_gate.py
.venv/bin/python scripts/run_p1_gate.py
.venv/bin/python scripts/run_p1_mutations.py
git diff --check
```

必须：

```text
contracts = exactly 290 passed
P1 passed >= 526
full passed = contracts + P1
0 failed
0 errors
0 skipped
0 xfailed
0 xpassed
P0 Gate = 10/10 PASS
P1-G08 = PASS
P1-G09 = PASS
P1 Gate = 7 PASS / 0 FAIL / 3 BLOCKED
M1–M85 = 85/85 caught
git diff --check = clean
```

如果新增测试数量不是预期值，必须报告：

- collected；
- passed；
- 新增节点列表；
- 与 526 baseline 的差值。

不得手填测试数字。

---

## 19. 正确 Gate 矩阵

Round 7 ChatGPT 有效判定：

| Gate | 有效状态 |
|---|---:|
| P1-G01 | PASS |
| P1-G02 | PASS |
| P1-G03 | BLOCKED |
| P1-G04 | BLOCKED |
| P1-G05 | PASS |
| P1-G06 | PASS |
| P1-G07 | PASS |
| P1-G08 | FAIL |
| P1-G09 | FAIL |
| P1-G10 | BLOCKED |

即：

```text
5 PASS
2 FAIL
3 BLOCKED
```

Round 8 修复完成后的合理预期：

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

7 PASS
0 FAIL
3 BLOCKED
overall = BLOCKED
```

三个 BLOCKED 必须仍是真实外部 blocker：

```text
G03 real reaction source
G04 real mapper implementation
G10 independent double annotation/adjudication
```

不得用 fixture、FakeAtomMapper 或单模型自注释解除它们。

---

## 20. 必须更新或生成的产物

更新：

```text
reports/p1/P1_REMEDIATION_WORKLOG.md
reports/p1/P1_GATE_REPORT.md
reports/p1/P1_GATE_REPORT.json
reports/p0/P0_GATE_REPORT.md
reports/p0/P0_GATE_REPORT.json
reports/p1/mutation_results.json
reports/p1/snapshot_build_sample.json
```

新增：

```text
reports/p1/index_partition_integrity_results_round_8.json
reports/p1/gate_false_positive_mutation_results_round_8.json
reports/p1/P1_ROUND_8_AUDIT_EVIDENCE.json
reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_8.md
```

不得删除 Round 2–7 历史 evidence。

---

## 21. Round 8 structured evidence 最低字段

`P1_ROUND_8_AUDIT_EVIDENCE.json` 至少包含：

```text
round
branch
head
working_tree
python
rdkit
changed_files
unchanged_frozen_files
round7_baseline_counts
round8_final_counts
zero_skip_xfail_xpass
p0_gate
p1_gate
g08_previous_mandatory_total
g08_final_mandatory_total
g08_final_mandatory_passed
g08_round8_required_nodes
g09_previous_mandatory_total
g09_final_mandatory_total
g09_final_mandatory_passed
g09_round8_required_nodes
snapshot_id
snapshot_hash
diagnostic_index_hash
snapshot_hash_change_reason
M1-M82_preserved
M83_corrected
M84_result
M85_result
mutations_total
mutations_caught
R8-01_before
R8-01_after
R8-02_before
R8-02_after
R8-03_before
R8-03_after
index_partition_contract
records_unique
indexes_unique
indexes_disjoint
index_union_equals_records
index_entries_rehashed
index_entries_equal_full_records
diagnostic_hash_bound
external_blockers
dependency_or_network_actions
synthetic_fixture_usage
deferred_semantic_decisions
p2_status
```

每个 R8 evidence 必须包含：

```text
fixture reaction_id
records lane
actual index memberships
mutation
pre-fix loader result
post-fix loader result
exception type
reason token
whether manifest/hash/COMPLETE was changed
whether failure was generic hash mismatch
```

---

## 22. Worklog Round 8 必须记录

至少包括：

1. ChatGPT Round 7 rejection；
2. Round 7 已确认有效成果；
3. Round 7 baseline 冻结命令和结果；
4. R8-01 修复前复现；
5. R8-02 修复前复现；
6. R8-03 修复前复现；
7. 当前 M83 self-assert weakness；
8. RED tests 名称；
9. RED 实际失败；
10. centralized validator 设计；
11. expected partition contract；
12. records/index uniqueness；
13. index disjointness；
14. index completeness；
15. index payload rehash/equality；
16. diagnostic index hash；
17. snapshot hash 变化原因；
18. GREEN 结果；
19. G08 mandatory 扩展；
20. G09 mandatory 扩展；
21. M56f/M56g；
22. corrected M83；
23. M84；
24. M85；
25. M1–M82 preservation；
26. contracts/P1/full counts；
27. P0 Gate；
28. P1 Gate matrix；
29. external blockers；
30. synthetic vs real boundary；
31. deferred semantic decisions；
32. changed files；
33. dependency/network actions；
34. `git diff --check`；
35. P2 remains BLOCKED。

必须写真实 RED→GREEN，不得只写：

```text
tests added and passed
```

---

## 23. Round 8 submission 封面

生成：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_8.md
```

必须逐项回答：

1. 项目根；
2. branch；
3. HEAD；
4. dirty status；
5. changed-files；
6. 未修改 frozen files；
7. Round 7 baseline；
8. R8-01 pre-fix；
9. R8-01 post-fix；
10. R8-02 pre-fix；
11. R8-02 post-fix；
12. R8-03 pre-fix；
13. R8-03 post-fix；
14. partition contract；
15. production allowed lanes；
16. diagnostic allowed lanes；
17. quarantine allowed lanes；
18. completeness；
19. disjointness；
20. records uniqueness；
21. index uniqueness；
22. index entry rehash；
23. index/full-record equality；
24. diagnostic index hash；
25. diagnostic hash manifest field；
26. valid snapshot positive protection；
27. conditional production positive protection；
28. G08 previous/final totals；
29. G08 new nodes；
30. G09 previous/final totals；
31. G09 new nodes；
32. M56f/M56g；
33. corrected M83；
34. M84；
35. M85；
36. M1–M82 preservation；
37. final mutation count；
38. contracts count；
39. P1 count；
40. full count；
41. zero skip/xfail/xpass；
42. P0 Gate；
43. P1 Gate matrix；
44. snapshot ID/hash；
45. snapshot hash change reason；
46. G03 blocker；
47. G04 blocker；
48. G10 blocker；
49. deferred semantic risks；
50. structured evidence path；
51. worklog path；
52. dependency/network actions；
53. P2 status。

---

## 24. 不接受的伪修复

以下任何一种都直接拒绝：

1. 只给 diagnostic index 加 hash，不验证 partition；
2. 只验证 lane，不验证 membership completeness；
3. 只比较 ID/lane/stored hash，不重算 index payload；
4. 只修 loader tests，不修 loader；
5. M83 继续捕获 mutation runner 自己写出的 assertion；
6. M83 只触发 generic hash mismatch；
7. 删除 diagnostic index 文件让 loader 报 missing file；
8. 用 JSON parse error 冒充 integrity detection；
9. 把所有 index records 全拒绝；
10. 把 conditional 从 production 错误移除；
11. 将 diagnostic 放进 quarantine；
12. 改 records lane 来迁就 index；
13. 修改 eligibility decision 来迁就 index；
14. 修改 P0/final docs；
15. 降低 mandatory manifest；
16. 删除历史 mutation；
17. fixture 冒充 real evidence；
18. 声称 P2 已开始；
19. 未运行完整回归；
20. 手填报告数字。

---

## 25. 最终科学验收语义

Round 8 完成后，必须能够真实证明：

```text
records.jsonl 是完整 record authority

production_index
只能包含 strict / conditional

diagnostic_index
只能包含 diagnostic

quarantine_index
只能包含 quarantine

三个 indexes：
complete
exact
unique
pairwise disjoint

每个 index entry：
自身 payload hash 可重算
与 records full record 完全一致

diagnostic index：
进入 immutable snapshot integrity
删除/增加/修改都会被 loader 拒绝

hash-coherent semantic wrong partition：
仍被 public loader fail closed

M83：
由真实 public/Gate authority 捕获
不是 mutation runner 自我断言

P0、R7-01–R7-04、G08/G09 既有节点、M1–M82：
全部保持
```

---

## 26. 最终提交状态规则

只有全部完成后，Round 8 submission 末尾才允许写：

```text
READY_FOR_CHATGPT_P1_ROUND_8_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
```

必须严格：

- 第一行单独一行；
- 中间一个空行；
- 第二行单独一行；
- 文件末尾不得再追加“P2 started”“P2 ready”“Gate passed therefore P2”等声明。

如果有任一 implementation failure：

```text
NOT_READY_FOR_CHATGPT_P1_ROUND_8_AUDIT

P2 BLOCKED
```

如果只剩 G03/G04/G10 真实外部 blocker，仍然：

```text
READY_FOR_CHATGPT_P1_ROUND_8_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
```

最终由 ChatGPT 决定：

```text
ACCEPTED / REJECTED
```

你无权自行宣布 P1 accepted 或 P2 authorized。

---

## 27. 给执行 agent 的最终指令

```text
先完整读取
→ 冻结 Round 7 baseline
→ 独立复现三个 loader fail-open
→ 证明当前 M83 self-assert weakness
→ 写 loader-level RED tests
→ 实现集中 exact partition validator
→ 绑定 diagnostic index hash
→ 重算每个 index entry payload
→ 定向 GREEN
→ 扩展 G08/G09 mandatory nodes
→ 扩展 M56f/M56g
→ 重写 M83
→ 新增 M84/M85
→ 保持 M1–M82
→ 串行完整回归
→ evidence/worklog/submission
→ 等待 ChatGPT
```

本轮不是 P2。

P2 继续 BLOCKED。
