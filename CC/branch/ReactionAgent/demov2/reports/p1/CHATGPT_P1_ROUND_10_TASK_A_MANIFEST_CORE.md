# P1 Round 10 — Task A：Manifest Core Validator

> 执行角色：核心实现 agent  
> 项目根目录：`/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`  
> 执行顺序：A → B → C；Task B 必须等待本任务完成  
> 本任务性质：P1 manifest type-authority 最小整改，不是 P2  
> 文件所有权：仅 loader、一个新的独立测试文件、Task A handoff

---

## 1. 目标

修复 ChatGPT 对 P1 Round 9 独立审核确认的 manifest 类型权威漏洞：

1. `record_count: true` 在单记录 snapshot 中被真实 `load_snapshot` 接受；
2. `failure_counts_by_reason={reason: true}` 在真实计数为 1 时被接受；
3. 缺失或错误类型的 `build_status` 绕过 required/type validator；
4. lane count 使用 boolean 时由下游 Pydantic 抛错，而不是 loader 的稳定 token；
5. `_validate_manifest_authority` 名义上返回 verified values，实际仍返回 raw manifest values。

本任务完成后，只允许声明 Task A core ready。不得声明 P1、G09、Round 10 或 P2 已通过。

---

## 2. 开始前必须阅读

完整阅读：

1. `reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_9.md`
2. `reports/p1/P1_ROUND_9_AUDIT_EVIDENCE.json`
3. `reports/p1/P1_REMEDIATION_WORKLOG.md` 的 Round 9 章节
4. `reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_9.md`
5. `reaction_agent/snapshot/loader.py`
6. `reaction_agent/snapshot/builder.py`
7. `reaction_agent/schemas/p1_entities.py`
8. `reaction_agent/schemas/common.py`
9. `tests/p1/test_snapshot_nested_evidence.py`
10. `tests/p1/test_snapshot_builder.py`
11. `tests/p1/test_snapshot_complete_evidence.py`

先记录开工前的 branch、HEAD、dirty status。工作树原有改动属于用户，不得清理、reset 或覆盖。

---

## 3. 本 agent 的独占文件

允许修改：

```text
reaction_agent/snapshot/loader.py
tests/p1/test_manifest_authority_type_integrity.py   # 新建
reports/p1/ROUND_10_TASK_A_HANDOFF.md                # 新建
```

禁止修改：

```text
scripts/run_p1_gate.py
scripts/run_p1_mutations.py
reports/p1/P1_REMEDIATION_WORKLOG.md
reports/p1/P1_GATE_REPORT.*
reports/p1/P1_ROUND_10_AUDIT_EVIDENCE.json
reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_10.md
plan/final_design.md
plan/final_plan.md
reaction_agent/snapshot/builder.py
reaction_agent/eligibility/engine.py
reaction_agent/schemas/*
reaction_agent/policies/*
P0 contracts / ADRs
../benchmark
../core
```

Task B 负责 Gate/mutations；Task C 负责最终 evidence/worklog/submission。

---

## 4. 开工前冻结基线

只运行，不修改代码：

```bash
.venv/bin/python -m pytest -q tests/contracts
.venv/bin/python -m pytest -q tests/p1
.venv/bin/python -m pytest -q
```

预期 Round 9 基线：

```text
contracts = 290 passed
P1 = 556 passed
full = 846 passed
0 skipped / 0 xfailed / 0 xpassed
```

若不一致，在 handoff 中如实记录；不得为匹配数字删除测试。

---

## 5. 必须先写 RED tests

所有新增测试放在：

```text
tests/p1/test_manifest_authority_type_integrity.py
```

禁止继续把 Round 10 测试堆进已经很大的 `test_snapshot_nested_evidence.py`。

至少实现以下明确命名的测试：

```text
test_loader_rejects_manifest_record_count_bool
test_loader_rejects_manifest_included_strict_count_bool
test_loader_rejects_manifest_conditional_count_bool
test_loader_rejects_manifest_diagnostic_count_bool
test_loader_rejects_manifest_quarantine_count_bool
test_loader_rejects_manifest_source_count_bool
test_loader_rejects_manifest_source_count_float
test_loader_rejects_manifest_failure_count_bool
test_loader_rejects_manifest_failure_count_float
test_loader_rejects_missing_manifest_build_status
test_loader_rejects_manifest_build_status_wrong_type
test_loader_rejects_non_object_manifest
test_loader_rejects_manifest_versions_nested_wrong_type
test_loader_rejects_manifest_source_files_nested_wrong_type
test_loader_rejects_manifest_record_hash_list_nested_wrong_type
test_loader_returns_recomputed_manifest_counts
test_loader_returns_recomputed_source_counts
test_loader_accepts_round10_verified_manifest_all_four_lanes
```

另外加入参数化 required-field 删除测试，覆盖 Round 9 冻结的全部 20 个字段。每个字段缺失都必须由真实 public `load_snapshot` 拒绝，并包含：

```text
manifest_required_field_missing
```

每个 negative test 必须：

1. 使用 public `build_snapshot` 建立合法 snapshot；
2. mutation 前真实 `load_snapshot` 成功；
3. 只修改一个 manifest 条件；
4. records/indexes/snapshot hash/COMPLETE 保持不变；
5. 调用真实 public `load_snapshot`；
6. 断言具体异常类型与稳定 token；
7. 使用 `tmp_path`；
8. 不得通过 JSON parse error、missing file 或下游 Pydantic error 假装捕获。

先运行新增文件并记录真实 RED。至少 `record_count=true` 和 failure count boolean 必须在旧实现上显示 `DID NOT RAISE`。

---

## 6. 最小实现要求

### 6.1 顶层 manifest

`json.load()` 后立即确认结果是 JSON object/dict。非 object 必须 fail closed，并使用：

```text
manifest_field_type_invalid
```

不得让 list/null/string 进入 `.get()` 或字段循环后产生 `AttributeError`。

### 6.2 精确 primitive 类型

不能使用会接受 boolean-as-int 的逻辑：

```python
isinstance(value, int)
```

整数 authority 字段必须满足：

```python
type(value) is int
```

字符串、dict、list 同样使用 JSON 精确顶层类型。错误统一使用：

```text
manifest_field_type_invalid
```

### 6.3 递归 shape/type

至少校验：

```text
source_counts            = dict[str, exact int >= 0]
failure_counts_by_reason = dict[str, exact int >= 0]
source_files             = dict[str, non-empty str]
versions                 = dict[str, non-empty str]
record_content_hashes    = list[non-empty str]
```

不得让 `true`、`false`、`1.0` 作为整数计数通过。

### 6.4 校验顺序

冻结顺序：

```text
parse JSON
→ confirm top-level object
→ required presence
→ strict top-level and nested types
→ interpret build_status
→ COMPLETE marker
→ index partition
→ canonical hash
→ manifest authority comparisons
→ construct returned record
```

语义必须是：

```text
missing build_status   → manifest_required_field_missing
build_status=true      → manifest_field_type_invalid
build_status="partial" → SnapshotIncompleteError
build_status="complete" → continue
```

### 6.5 返回真正重建的值

`_validate_manifest_authority` 的返回 dict 不得继续复制可重建的 raw manifest 值。

至少返回：

```text
snapshot_id            ← expected_snapshot_id
snapshot_hash          ← recomputed_snapshot_hash
included_strict_count  ← rebuilt lane_counts["strict"]
conditional_count      ← rebuilt lane_counts["conditional"]
diagnostic_count       ← rebuilt lane_counts["diagnostic"]
quarantine_count       ← rebuilt lane_counts["quarantine"]
build_status           ← verified literal "complete"
source_counts          ← rebuilt sorted source counts
```

无法从 records/indexes 重建但已经被 canonical hash 保护的 trust-root 字段，可以在严格类型校验和 hash 校验后返回 manifest 值。

不要新增复杂 class hierarchy；优先使用少量 pure helpers。

---

## 7. 必须保持的行为

不得破坏：

```text
R9-01 missing diagnostic_index_hash
R9-02 diagnostic_count=999
R9-03 forged snapshot_id
Round 8 exact index partition
M83–M88 所依赖的 loader tokens
合法 strict/conditional/diagnostic/quarantine snapshot 加载
read-only loader 行为
```

不得修改 frozen design、schemas 或 builder 来绕过 loader 问题。

---

## 8. GREEN 与回归

按顺序运行：

```bash
.venv/bin/python -m pytest -q tests/p1/test_manifest_authority_type_integrity.py
.venv/bin/python -m pytest -q tests/p1/test_snapshot_nested_evidence.py tests/p1/test_snapshot_builder.py tests/p1/test_snapshot_complete_evidence.py
.venv/bin/python -m pytest -q tests/contracts
.venv/bin/python -m pytest -q tests/p1
.venv/bin/python -m pytest -q
git diff --check
```

所有新增测试必须 GREEN；原 846 个测试不得减少；不得出现 skip/xfail/xpass。

本任务不运行或修改正式 P1 Gate/mutation wiring，那属于 Task B。

---

## 9. Task A handoff

生成：

```text
reports/p1/ROUND_10_TASK_A_HANDOFF.md
```

内容必须包括：

1. branch、HEAD、dirty status；
2. changed files；
3. RED 结果；
4. GREEN 结果；
5. 每个新 test node 的完整 pytest node ID；
6. strict type/shape contract；
7. build_status 顺序；
8. reconstructed returned fields；
9. contracts/P1/full 实际数字；
10. assumptions 与 unresolved items；
11. 明确说明未修改 Gate/mutations/reports/frozen files；
12. 提供给 Task B 的 mandatory-node 清单。

文件结尾必须是：

```text
TASK_A_MANIFEST_CORE_READY_FOR_TASK_B

P2 BLOCKED
```

若任何新增测试或回归失败，结尾改为：

```text
TASK_A_BLOCKED

P2 BLOCKED
```

