# P1 Round 10 — Task B：G09 Wiring 与 Mutations

> 执行角色：Gate/mutation agent  
> 项目根目录：`/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`  
> 前置依赖：Task A 必须完成且 handoff 状态为 READY  
> 执行顺序：A → B → C；Task C 必须等待本任务完成  
> 本任务性质：把 Task A 的新契约接入 G09 和 mutation 防线，不修改核心 loader

---

## 1. 启动条件

必须先完整阅读：

1. `reports/p1/CHATGPT_P1_ROUND_10_TASK_A_MANIFEST_CORE.md`
2. `reports/p1/ROUND_10_TASK_A_HANDOFF.md`
3. `reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_9.md`
4. `reports/p1/P1_ROUND_9_AUDIT_EVIDENCE.json`
5. `scripts/run_p1_gate.py`
6. `scripts/run_p1_mutations.py`
7. `tests/p1/test_manifest_authority_type_integrity.py`
8. `tests/p1/test_snapshot_nested_evidence.py`
9. `reports/p1/P1_GATE_REPORT.json`
10. `reports/p1/mutation_results.json`

验证以下命令成功后才能修改：

```bash
.venv/bin/python -m pytest -q tests/p1/test_manifest_authority_type_integrity.py
```

若 Task A handoff 不存在、状态不是 READY、或测试不绿，停止并生成 BLOCKED handoff；不得擅自修改 loader 代替 Task A。

---

## 2. 本 agent 的独占文件

允许修改：

```text
scripts/run_p1_gate.py
scripts/run_p1_mutations.py
reports/p1/manifest_type_authority_results_round_10.json
reports/p1/gate_false_positive_mutation_results_round_10.json
reports/p1/ROUND_10_TASK_B_HANDOFF.md
```

运行脚本自然生成的以下派生产物允许刷新，但不得手工伪造：

```text
reports/p1/P1_GATE_REPORT.md
reports/p1/P1_GATE_REPORT.json
reports/p1/mutation_results.json
```

禁止修改：

```text
reaction_agent/snapshot/loader.py
reaction_agent/snapshot/builder.py
tests/p1/test_manifest_authority_type_integrity.py
tests/p1/test_snapshot_nested_evidence.py
reaction_agent/eligibility/engine.py
reaction_agent/schemas/*
reaction_agent/policies/*
plan/final_design.md
plan/final_plan.md
reports/p1/P1_REMEDIATION_WORKLOG.md
reports/p1/P1_ROUND_10_AUDIT_EVIDENCE.json
reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_10.md
P0 contracts / ADRs
```

---

## 3. G09 mandatory wiring

Round 9 的 33 个 G09 mandatory nodes 必须全部保留。

从 Task A handoff 和实际 pytest collection 读取完整 node IDs，不得猜测参数化 node ID：

```bash
.venv/bin/python -m pytest --collect-only -q tests/p1/test_manifest_authority_type_integrity.py
```

至少把以下保护族接入 G09：

```text
record_count boolean rejection
lane-count boolean rejection
source-count boolean/float rejection
failure-count boolean/float rejection
missing build_status rejection
wrong-type build_status rejection
top-level non-object rejection
nested versions/source_files/record-hash type rejection
recomputed returned counts
recomputed returned source_counts
all-four-lanes positive protection
all required fields deletion coverage
```

Gate 必须证明节点被实际 collected 和 passed。不能只检查测试文件存在或 substring 存在。

报告：

```text
G09 previous mandatory total = 33
G09 final mandatory total = actual collected integer > 33
G09 final mandatory passed = same integer
```

G08 117/117 不得减少。

---

## 4. Deletion protection

扩展 M56，至少新增：

```text
M56j: 删除/遮蔽 record_count boolean mandatory node → G09 FAIL
M56k: 删除/遮蔽 build_status required/type mandatory node → G09 FAIL
M56l: 删除/遮蔽 reconstructed-return mandatory node → G09 FAIL
```

要求：

1. 在 temp copy 中执行；
2. `finally` 恢复；
3. 失败原因必须是 mandatory node missing/not collected；
4. 不能由 syntax error、import error 或 collection crash 假装捕获；
5. M56a–M56i 全部继续 caught。

---

## 5. 新增真实 loader mutations

保留 M1–M88，新增：

### M89 — boolean record_count

```text
build one-record valid snapshot
→ pre-mutation real load_snapshot succeeds
→ set manifest.record_count=true
→ keep records/indexes/hash/COMPLETE unchanged
→ real load_snapshot rejects
→ token manifest_field_type_invalid
```

### M90 — nested failure-count type

至少包含两个子项：

```text
M90a failure_counts_by_reason count=true
M90b failure_counts_by_reason count=1.0
```

两项都必须由真实 loader 拒绝：

```text
manifest_field_type_invalid
```

### M91 — build_status authority order

至少包含：

```text
M91a delete build_status
     → manifest_required_field_missing

M91b build_status=true
     → manifest_field_type_invalid

M91c build_status="partial"
     → SnapshotIncompleteError
```

M91c 是合法类型但非 complete 的语义保护，不得错误改成 manifest type failure。

每个 mutation 必须调用真实 public `load_snapshot`，不得由 mutation runner 自己比较后直接写 `caught=true`。

预期总数：

```text
M1–M88 preserved
M89 caught
M90 caught（全部子项）
M91 caught（全部子项）
final top-level total = 91
final caught = 91
```

实际总数必须从真实 `mutation_results.json` 读取。

---

## 6. Round 10 拆分证据

运行 mutation runner 后，从同一真实结果对象生成：

```text
reports/p1/manifest_type_authority_results_round_10.json
reports/p1/gate_false_positive_mutation_results_round_10.json
```

第一份至少包含 M89–M91 的所有子结果、expected、actual、exception、reason token、caught。

第二份至少包含 M56j–M56l 的删除目标、真实 Gate 结果、mandatory missing evidence、caught。

不得手工输入与 runner 不一致的计数。

---

## 7. 验证命令

按顺序运行：

```bash
.venv/bin/python -m pytest -q tests/p1/test_manifest_authority_type_integrity.py
.venv/bin/python scripts/run_p1_gate.py
.venv/bin/python scripts/run_p1_mutations.py
.venv/bin/python -m pytest -q tests/contracts
.venv/bin/python -m pytest -q tests/p1
.venv/bin/python -m pytest -q
git diff --check
```

P1 Gate 因 G03/G04/G10 外部 blocker 返回非零是诚实结果。必须区分：

```text
implementation failure = 0
external blockers = 3
overall = BLOCKED
```

若 G09 FAIL，不得用 overall BLOCKED 掩盖。

---

## 8. Task B handoff

生成：

```text
reports/p1/ROUND_10_TASK_B_HANDOFF.md
```

必须包含：

1. 前置 Task A 验证；
2. changed files；
3. G08/G09 previous/final totals；
4. 新增 mandatory node IDs；
5. M56a–M56l 结果；
6. M1–M91 总数与 caught；
7. M89/M90/M91 逐子项 evidence；
8. P0/P1/full tests；
9. P1 Gate matrix；
10. assumptions、failures、blocked items；
11. 提供给 Task C 的全部产物路径。

成功结尾：

```text
TASK_B_GATE_MUTATIONS_READY_FOR_TASK_C

P2 BLOCKED
```

失败结尾：

```text
TASK_B_BLOCKED

P2 BLOCKED
```

