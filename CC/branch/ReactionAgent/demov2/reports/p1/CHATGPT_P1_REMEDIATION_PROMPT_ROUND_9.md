# P1 Round 9 严格整改任务书

> 交付对象：新开的 AI coding agent（Claude、Qwen、Codex 等）  
> 项目根目录：/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2  
> 依据：ChatGPT 对 SUBMISSION_TO_CHATGPT_P1_ROUND_8.md 的独立只读审核  
> 本轮性质：P1 manifest-authority envelope 最小完整整改，不是 P2 开发  
> 最终验收人：ChatGPT  
> 日期：2026-07-31

---

## 0. 正式审核结论

Round 8 的 index-partition 修复已经通过独立验证，但 P1 Round 8 最终审核仍未通过。

~~~text
ROUND_8_TARGETED_INDEX_PARTITION_REMEDIATION = ACCEPTED
CHATGPT_P1_ROUND_8_READ_ONLY_AUDIT = REJECTED
rejection_class = IMPLEMENTATION_FAILURE
remaining_failure_class = MANIFEST_AUTHORITY_INTEGRITY
P1-G08_EFFECTIVE_STATUS = PASS
P1-G09_EFFECTIVE_STATUS = FAIL
P1_STATUS = BLOCKED
P2_STATUS = BLOCKED
~~~

Round 9 不得推翻 Round 8。Round 8 exact index partition、diagnostic hash、index-entry rehash、M83–M85 必须全部保留。

---

## 1. Round 8 已确认有效且必须保留

ChatGPT 独立复现：

~~~text
P0 contract tests = 290 passed
P1 tests = 541 passed
full suite = 831 passed
skip / xfail / xpass = 0 / 0 / 0
P0 Gate = 10/10 PASS
P1 Gate = 7 PASS / 0 FAIL / 3 BLOCKED
G08 = 117/117 mandatory nodes
G09 = 21/21 mandatory nodes
M1–M85 = 85/85 caught
git diff --check = clean
~~~

必须保持：

1. production 只允许 strict / conditional；
2. diagnostic 只允许 diagnostic；
3. quarantine 只允许 quarantine；
4. 三个 index exact、complete、unique、pairwise-disjoint；
5. 每个 index entry 重新计算 payload hash；
6. index entry 与 records full record canonical payload 完全一致；
7. diagnostic_index_hash 进入 canonical snapshot content；
8. M83/M84/M85 真实调用 load_snapshot；
9. M1–M85 不得减少或回退；
10. P0、P1 strict eligibility、G08/G09 既有 mandatory nodes 全部保留。

---

## 2. 开始前必须完整阅读

~~~text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_design.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/plan/final_plan.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_8.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_8.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_8_AUDIT_EVIDENCE.json
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/loader.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reaction_agent/schemas/p1_entities.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_builder.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_nested_evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_complete_evidence.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_gate.py
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/scripts/run_p1_mutations.py
~~~

重点阅读：

~~~text
_validate_index_partition
_recompute_snapshot_hash
load_snapshot
diagnostic_index_hash
M83 / M84 / M85
G08 117-node manifest
G09 21-node manifest
~~~

---

## 3. 允许和禁止的范围

默认允许修改：

~~~text
reaction_agent/snapshot/loader.py
reaction_agent/snapshot/builder.py
tests/p1/test_snapshot_nested_evidence.py
tests/p1/test_snapshot_builder.py
tests/p1/test_snapshot_complete_evidence.py
scripts/run_p1_gate.py
scripts/run_p1_mutations.py
reports/p1/*
reports/p0/P0_GATE_REPORT.{md,json}
~~~

优先新增集中 pure helper：

~~~text
_validate_manifest_authority
~~~

除非先证明无法在 snapshot 层修复，否则禁止修改：

~~~text
reaction_agent/eligibility/engine.py
reaction_agent/schemas/evidence.py
reaction_agent/schemas/mapping.py
reaction_agent/schemas/ledger.py
reaction_agent/schemas/lineage.py
reaction_agent/policies/*
~~~

绝对禁止修改：

~~~text
plan/final_design.md
plan/final_plan.md
P0 ADRs
P0 frozen contracts
legacy source
../benchmark
../core
~~~

禁止删除或降低 G08 117 / G09 21 mandatory nodes，禁止删除 M1–M85，禁止把 required manifest field 改成 optional，禁止 fixture 冒充 real evidence，禁止安装依赖、联网、自动 commit/push/merge/reset/stash/clean，禁止进入 P2 或生成 P2 performance。

---

## 4. 开工前冻结 Round 8 基线

必须串行执行：

~~~bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
.venv/bin/python -m pytest tests/contracts -q -ra
.venv/bin/python -m pytest tests/p1 -q -ra
.venv/bin/python -m pytest tests/contracts tests/p1 -q -ra
.venv/bin/python scripts/run_p0_gate.py
.venv/bin/python scripts/run_p1_gate.py
.venv/bin/python scripts/run_p1_mutations.py
~~~

预期：

~~~text
contracts = 290 passed
P1 = 541 passed
full = 831 passed
P0 Gate = 10/10 PASS
P1 Gate = 7 PASS / 0 FAIL / 3 BLOCKED
G08 = 117/117
G09 = 21/21
M1–M85 = 85/85 caught
0 skipped / 0 xfailed / 0 xpassed
~~~

如果基线不同，先记录并停止，禁止手工覆盖数字。

---

## 5. ChatGPT 独立确认的 Round 9 fail-open

### 5.1 R9-01：删除 required diagnostic_index_hash 仍被接受

步骤：

1. builder 构建合法 diagnostic snapshot；
2. 确认 manifest.json 有 diagnostic_index_hash；
3. 只删除该字段；
4. 不修改 records、indexes、snapshot hash、COMPLETE；
5. 调用真实 load_snapshot。

Round 8 实际结果：

~~~json
{"missing_manifest_diagnostic_index_hash": {"accepted": true}}
~~~

根因：loader 使用 manifest.get，并在字段缺失时跳过验证。

Round 9 要求：字段是 current manifest contract 的 required field，缺失必须 fail closed。

建议 token：

~~~text
manifest_required_field_missing
~~~

### 5.2 R9-02：manifest counts 可被篡改并返回 downstream

只把 manifest.json 的 diagnostic_count 改为 999，其他 artifacts 不变，然后调用真实 load_snapshot。

Round 8 实际结果：

~~~json
{"tampered_manifest_diagnostic_count": {"accepted": true, "loaded_manifest_diagnostic_count": 999}}
~~~

必须从 verified records 重建并比较：

~~~text
record_count
included_strict_count
conditional_count
diagnostic_count
quarantine_count
~~~

建议 token：

~~~text
manifest_count_mismatch
~~~

### 5.3 R9-03：manifest snapshot identity 可被伪造

只把 manifest.snapshot_id 改为 snap_forged000000，不修改 snapshot hash、COMPLETE、records、indexes，然后用真实 path 调用 load_snapshot。

Round 8 实际结果：

~~~json
{"tampered_manifest_snapshot_id": {"accepted": true, "loaded_id": "snap_forged000000"}}
~~~

必须验证：

~~~text
manifest.snapshot_id == "snap_" + snapshot_hash[:12]
manifest.snapshot_id == resolved snapshot directory basename
~~~

建议 token：

~~~text
snapshot_identity_mismatch
~~~

### 5.4 同源 manifest fields 必须一起审计

以下字段都不得被 raw manifest 篡改后直接返回：

~~~text
record_content_hashes
production_index_hash
diagnostic_index_hash
quarantine_index_hash
source_counts
source_files / source_content_hashes
failure_counts_by_reason
record_count
included_strict_count
conditional_count
diagnostic_count
quarantine_count
snapshot_id
~~~

必须从 verified artifacts 重建并比较这些字段，或从 verified values 构造返回对象。

---

## 6. Round 9 冻结的 manifest authority contract

### 6.1 Required fields

以下字段都是 current on-disk manifest 的 required fields：

~~~text
snapshot_id
schema_version
included_strict_count
conditional_count
diagnostic_count
quarantine_count
build_status
snapshot_hash
build_id
source_counts
policy_version
record_count
versions
source_files
failure_counts_by_reason
record_content_hashes
production_index_hash
diagnostic_index_hash
quarantine_index_hash
build_config_hash
~~~

缺失任何 authority field 必须 fail closed，不能用 .get(..., None) 静默跳过。

### 6.2 Identity

~~~text
build_status == "complete"
manifest.snapshot_hash == COMPLETE marker
manifest.snapshot_hash == recomputed canonical snapshot hash
manifest.snapshot_id == "snap_" + manifest.snapshot_hash[:12]
manifest.snapshot_id == resolved snapshot directory basename
~~~

### 6.3 Counts

从 verified records 重建并精确比较：

~~~text
manifest.included_strict_count == strict_count
manifest.conditional_count == conditional_count
manifest.diagnostic_count == diagnostic_count
manifest.quarantine_count == quarantine_count
manifest.record_count == len(records)
manifest.record_count == sum(four lane counts)
~~~

### 6.4 Record hash list

~~~text
manifest.record_content_hashes == sorted(verified records record_content_hashes)
~~~

不得信任 manifest 自报 list。

### 6.5 Index hashes

~~~text
manifest.production_index_hash == canonical_hash(sorted(production entry hashes))
manifest.diagnostic_index_hash == canonical_hash(sorted(diagnostic entry hashes))
manifest.quarantine_index_hash == canonical_hash(sorted(quarantine entry hashes))
~~~

三个字段都 required，全部必须有 stable token。

### 6.6 Source summaries

从 verified records 重建 source_counts 与 source_files/source_content_hashes。

至少要求：

- source counts 总和等于 record_count；
- source hash key 集合与 records source 集合相等；
- 每个 source hash 与 records 内容重算结果相等。

建议 token：

~~~text
manifest_source_counts_mismatch
manifest_source_hash_mismatch
~~~

### 6.7 Failure summaries

如果 failure_counts_by_reason 是当前 on-disk manifest audit authority，则必须从 verified diagnostic/quarantine decisions 重建并比较。

建议 token：

~~~text
manifest_failure_counts_mismatch
~~~

不要删除该字段或将其降级为 optional。

### 6.8 Returned object

load_snapshot 返回的 SnapshotRecord.manifest 必须使用 verified/recomputed values。

禁止：

~~~python
SnapshotManifest(**raw_manifest_values_without_cross_verify)
~~~

---

## 7. 建议的最小实现结构

新增集中 pure helper，例如：

~~~python
def _validate_manifest_authority(
    *,
    manifest: dict,
    snap_dir: str,
    recomputed_snapshot_hash: str,
    records: list[dict],
    production_records: list[dict],
    diagnostic_records: list[dict],
    quarantine_records: list[dict],
) -> dict:
    """Return verified manifest values or fail closed."""
~~~

建议顺序：

~~~text
read manifest
→ required field/type checks
→ COMPLETE marker check
→ index partition validator
→ record/index hash recomputation
→ snapshot hash comparison
→ identity validation
→ counts validation
→ record hash list validation
→ index hash validation
→ source summary validation
→ failure summary validation
→ verified SnapshotManifest construction
~~~

建议 stable tokens：

~~~text
manifest_required_field_missing
manifest_field_type_invalid
manifest_count_mismatch
manifest_record_hashes_mismatch
manifest_index_hash_mismatch
manifest_source_counts_mismatch
manifest_source_hash_mismatch
manifest_failure_counts_mismatch
snapshot_identity_mismatch
~~~

不要把 diagnostic_index_hash 重新做成 optional。

---

## 8. 必须先写的 RED tests

建议放在 tests/p1/test_snapshot_nested_evidence.py。至少新增：

~~~text
test_loader_rejects_missing_manifest_diagnostic_index_hash
test_loader_rejects_manifest_diagnostic_index_hash_wrong_type
test_loader_rejects_manifest_diagnostic_index_hash_wrong_value
test_loader_rejects_manifest_count_mismatch
test_loader_rejects_manifest_record_count_mismatch
test_loader_rejects_manifest_record_hashes_mismatch
test_loader_rejects_manifest_production_index_hash_mismatch
test_loader_rejects_manifest_diagnostic_index_hash_mismatch
test_loader_rejects_manifest_quarantine_index_hash_mismatch
test_loader_rejects_manifest_source_counts_mismatch
test_loader_rejects_manifest_source_hash_mismatch
test_loader_rejects_manifest_failure_counts_mismatch
test_loader_rejects_snapshot_identity_mismatch
test_loader_accepts_verified_manifest_authority
test_loader_accepts_verified_manifest_with_all_four_lanes
~~~

每个 negative test 必须：

1. 从合法 Round 8 snapshot 开始；
2. mutation 前真实 load_snapshot 成功；
3. 只修改一个 manifest authority 条件；
4. 调用真实 load_snapshot；
5. assert SnapshotHashMismatchError 或冻结兼容错误；
6. assert specific manifest token；
7. 不由 JSON parse、missing file 或 generic hash mismatch 捕获；
8. 在 temp directory 中运行；
9. 保留 positive protection。

具体要求：

- 删除 diagnostic_index_hash → manifest_required_field_missing；
- 改 diagnostic_count/record_count/included_strict_count → manifest_count_mismatch；
- 改 snapshot_id → snapshot_identity_mismatch；
- 合法 manifest → load 成功且所有 verified fields 一致。

---

## 9. G09 mandatory authority

Round 8 G09 21 个节点必须全部保留。

至少加入：

~~~text
test_loader_rejects_missing_manifest_diagnostic_index_hash
test_loader_rejects_manifest_count_mismatch
test_loader_rejects_manifest_record_count_mismatch
test_loader_rejects_manifest_record_hashes_mismatch
test_loader_rejects_manifest_production_index_hash_mismatch
test_loader_rejects_manifest_diagnostic_index_hash_mismatch
test_loader_rejects_manifest_quarantine_index_hash_mismatch
test_loader_rejects_manifest_source_counts_mismatch
test_loader_rejects_manifest_source_hash_mismatch
test_loader_rejects_manifest_failure_counts_mismatch
test_loader_rejects_snapshot_identity_mismatch
test_loader_accepts_verified_manifest_authority
~~~

必须报告：

~~~text
G09 previous mandatory total = 21
G09 final mandatory total = actual integer > 21
G09 final mandatory passed = same integer
~~~

G08 的 117 个节点不得减少。Round 9 不是 G08 eligibility/index-partition 重做。

---

## 10. Deletion protection

至少加入：

~~~text
M56h:
删除 Round 9 manifest-required-field mandatory node → G09 FAIL

M56i:
删除 Round 9 snapshot-identity mandatory node → G09 FAIL
~~~

必须 temp copy、finally restore，failure 来自 missing mandatory node，而不是 syntax/import/collection error。

---

## 11. Mutations：M86–M88

### M86：required diagnostic hash deletion

~~~text
build valid diagnostic snapshot
→ loader pre-mutation succeeds
→ delete manifest diagnostic_index_hash
→ keep every other artifact unchanged
→ real loader rejects with manifest_required_field_missing
~~~

### M87：manifest summary mutation

至少覆盖：

~~~text
diagnostic_count = 999
record_count = 999
source_counts = forged mapping
production_index_hash = forged hash
~~~

可以拆成 M87a–M87d，但 structured evidence 必须列出每个子结果。真实 loader 必须拒绝并使用具体 manifest token。

### M88：snapshot identity forgery

~~~text
build valid snapshot
→ change only manifest.snapshot_id
→ keep snapshot hash/COMPLETE/indexes/records unchanged
→ real loader rejects with snapshot_identity_mismatch
~~~

最终必须：

~~~text
M1–M85 preserved
M86 caught
M87 caught（或 M87a–M87d 全部 caught）
M88 caught
~~~

实际 mutation 总数必须从 JSON 产物读取，禁止手填。

---

## 12. 不得擅自扩展 semantic-risk 三项

Round 8 deferred 的内容继续保持：

~~~text
same AddedAtomSource formal=True/False
identical MechanisticOriginEvidence with different IDs
overlapping FAT assignments on same edge
~~~

本轮不修改这些 chemistry ledger semantics，除非另有 frozen authority。worklog 继续标记：

~~~text
must be frozen before P4 evidence aggregation/ranking
~~~

---

## 13. 实现顺序

~~~text
R9-T1 读取 final authority 与 Round 8 artifacts
R9-T2 冻结 Round 8 baseline
R9-T3 独立复现 R9-01 / R9-02 / R9-03
R9-T4 盘点 manifest fields 的真实 source of truth
R9-T5 写 RED tests
R9-T6 运行 RED 并记录具体失败
R9-T7 实现集中 manifest-authority validator
R9-T8 定向 GREEN
R9-T9 扩展 G09 mandatory manifest
R9-T10 扩展 M56h/M56i
R9-T11 新增 M86–M88
R9-T12 运行 M1–M88
R9-T13 串行完整回归
R9-T14 生成 evidence
R9-T15 更新 worklog
R9-T16 生成 Round 9 submission
R9-T17 等待 ChatGPT
~~~

禁止只更新 submission/evidence 不改 loader，禁止把 required field 改 optional，禁止让 raw manifest values 直接进入 downstream，禁止并发覆盖相同 reports 文件。

---

## 14. 最终验收命令

不得并发：

~~~bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
.venv/bin/python -m pytest tests/contracts -q -ra
.venv/bin/python -m pytest tests/p1 -q -ra
.venv/bin/python -m pytest tests/contracts tests/p1 -q -ra
.venv/bin/python scripts/run_p0_gate.py
.venv/bin/python scripts/run_p1_gate.py
.venv/bin/python scripts/run_p1_mutations.py
git diff --check
~~~

必须满足：

~~~text
contracts >= 290 passed
P1 >= 541 passed
full = contracts + P1
0 failed
0 errors
0 skipped
0 xfailed
0 xpassed
P0 Gate = 10/10 PASS
G08 = 117/117 or larger, no regression
G09 = 21/21 plus Round 9 nodes, no regression
M1–M85 preserved
M86–M88 caught
git diff --check = clean
~~~

---

## 15. 有效 Gate 矩阵

Round 8 独立审核后的有效矩阵：

~~~text
P1-G01 PASS
P1-G02 PASS
P1-G03 BLOCKED
P1-G04 BLOCKED
P1-G05 PASS
P1-G06 PASS
P1-G07 PASS
P1-G08 PASS
P1-G09 FAIL
P1-G10 BLOCKED

6 PASS
1 FAIL
3 BLOCKED
overall = BLOCKED
~~~

Round 9 预期：

~~~text
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
~~~

G03/G04/G10 仍必须是诚实外部 blocker，不得用 synthetic fixture、FakeAtomMapper 或单模型自注释解除。

---

## 16. 必须更新或生成的产物

更新：

~~~text
reports/p1/P1_REMEDIATION_WORKLOG.md
reports/p1/P1_GATE_REPORT.md
reports/p1/P1_GATE_REPORT.json
reports/p0/P0_GATE_REPORT.md
reports/p0/P0_GATE_REPORT.json
reports/p1/mutation_results.json
reports/p1/snapshot_build_sample.json
~~~

新增：

~~~text
reports/p1/manifest_authority_integrity_results_round_9.json
reports/p1/gate_false_positive_mutation_results_round_9.json
reports/p1/P1_ROUND_9_AUDIT_EVIDENCE.json
reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_9.md
~~~

不得删除 Round 2–8 历史 evidence。

---

## 17. Structured evidence 最低字段

P1_ROUND_9_AUDIT_EVIDENCE.json 至少包含：

~~~text
round
branch
head
working_tree
python
rdkit
changed_files
unchanged_frozen_files
round8_baseline_counts
round9_final_counts
zero_skip_xfail_xpass
p0_gate
p1_gate
g08_previous_mandatory_total
g08_final_mandatory_total
g08_final_mandatory_passed
g09_previous_mandatory_total
g09_final_mandatory_total
g09_final_mandatory_passed
snapshot_id
snapshot_hash
diagnostic_index_hash
manifest_required_fields
manifest_verified_fields
manifest_identity_verified
manifest_counts_verified
manifest_record_hashes_verified
manifest_index_hashes_verified
manifest_source_summaries_verified
manifest_failure_summaries_verified
R9-01_before
R9-01_after
R9-02_before
R9-02_after
R9-03_before
R9-03_after
M1-M85_preserved
M86_result
M87_result
M88_result
mutations_total
mutations_caught
external_blockers
dependency_or_network_actions
synthetic_fixture_usage
deferred_semantic_decisions
p2_status
~~~

每个 R9 evidence 必须记录 fixture reaction_id、field mutated、pre/post loader result、exception type、reason token、whether artifacts changed、whether snapshot hash/COMPLETE changed、whether failure was generic hash mismatch、verified downstream value。

---

## 18. Worklog Round 9 必须记录

至少包括：

1. Round 8 targeted remediation accepted；
2. Round 8 final audit rejected；
3. Round 8 baseline freeze；
4. R9-01/R9-02/R9-03 reproduction；
5. manifest source-of-truth table；
6. RED tests 与实际失败；
7. centralized manifest validator；
8. required-field、identity、counts、record-hash、index-hash、source-summary、failure-summary checks；
9. verified returned SnapshotRecord；
10. GREEN 结果；
11. G09 mandatory expansion；
12. M56h/M56i；
13. M86/M87/M88；
14. M1–M85 preservation；
15. contracts/P1/full counts；
16. P0/P1 Gate；
17. external blockers；
18. synthetic vs real boundary；
19. deferred semantic decisions；
20. changed files；
21. dependency/network actions；
22. git diff --check；
23. P2 remains BLOCKED。

必须写真实 RED→GREEN，不得只写 tests added and passed。

---

## 19. Round 9 submission

生成：

~~~text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_9.md
~~~

至少回答：

1. 项目根、branch、HEAD、dirty status；
2. changed-files 与 frozen files；
3. Round 8 baseline；
4. R9-01/R9-02/R9-03 pre/post；
5. required manifest fields；
6. identity/count/record-hash/index-hash/source-summary/failure-summary contracts；
7. verified returned object；
8. G08/G09 totals；
9. M56h/M56i；
10. M86/M87/M88；
11. M1–M85 preservation；
12. final mutation total/caught；
13. contracts/P1/full counts；
14. zero skip/xfail/xpass；
15. P0/P1 Gate matrix；
16. snapshot ID/hash 与 diagnostic index hash；
17. external blockers；
18. deferred semantic risks；
19. structured evidence/worklog paths；
20. dependency/network actions；
21. P2 status。

---

## 20. 不接受的伪修复

以下任一项直接拒绝：

1. 继续使用 if field is not None 跳过 required manifest field；
2. 只检查 diagnostic hash，不检查 counts/identity；
3. 只检查 field 存在，不检查 value；
4. 只验证 raw manifest，不重建 source of truth；
5. 只更新返回对象，不拒绝坏 snapshot；
6. 只更新 tests/evidence，不修改 loader；
7. 删除 snapshot identity contract；
8. 接受 manifest counts 后声称 overall hash 已保护它；
9. 让 downstream 继续读取未经验证的 raw manifest；
10. 删除 G09 mandatory nodes；
11. 删除 M1–M85；
12. 把 G09 FAIL 改成 BLOCKED；
13. 用 generic hash mismatch 替代 manifest-specific token；
14. fixture 冒充 real evidence；
15. 修改 P0/final design/final plan；
16. 安装依赖、联网、自动 commit/push/merge/reset/clean；
17. 进入 P2 或生成 P2 performance。

---

## 21. 最终科学验收语义

Round 9 完成后必须真实证明：

~~~text
required manifest fields 缺失 → fail closed
manifest snapshot_id 与 content hash/path 不一致 → fail closed
manifest lane counts 与 verified records 不一致 → fail closed
manifest record hash list 与 verified records 不一致 → fail closed
manifest production/diagnostic/quarantine hashes 与 verified indexes 不一致 → fail closed
manifest source summaries 与 verified records 不一致 → fail closed
manifest failure summaries 与 verified decisions 不一致 → fail closed
返回给 downstream 的 SnapshotRecord 只包含 verified values
Round 8 exact index partition、diagnostic hash、M83–M85 全部保持
P0、G08、G09 既有 mandatory nodes 全部保持
~~~

---

## 22. 最终提交状态规则

全部完成后，Round 9 submission 末尾才允许写：

~~~text
READY_FOR_CHATGPT_P1_ROUND_9_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
~~~

如果任何 manifest-authority implementation failure 仍存在：

~~~text
NOT_READY_FOR_CHATGPT_P1_ROUND_9_AUDIT

P2 BLOCKED
~~~

如果只剩 G03/G04/G10 真实外部 blocker，仍必须：

~~~text
READY_FOR_CHATGPT_P1_ROUND_9_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
~~~

执行 agent 无权自行宣布 P1 ACCEPTED 或 P2 AUTHORIZED。

---

## 23. 给执行 agent 的最终指令

~~~text
先完整读取
→ 冻结 Round 8 baseline
→ 独立复现 R9-01 / R9-02 / R9-03
→ 盘点 manifest source of truth
→ 写 manifest-level RED tests
→ 实现集中 manifest-authority validator
→ 验证 required fields
→ 验证 identity
→ 验证 counts
→ 验证 record hash list
→ 验证三 index hashes
→ 验证 source summaries
→ 验证 failure summaries
→ 构造 verified SnapshotRecord
→ 定向 GREEN
→ 扩展 G09 与 M56h/M56i
→ 新增 M86–M88
→ 保持 M1–M85
→ 串行完整回归
→ evidence/worklog/submission
→ 等待 ChatGPT
~~~

本轮仍然不是 P2。

P2 继续 BLOCKED。

