# Round 10 — Task B Handoff：G09 Wiring 与 Mutations

> **执行角色：** Task B（gate/mutation agent）
> **执行顺序：** A → B → C；本文件供 Task C 读取
> **性质：** 把 Task A 的 manifest type-authority 契约接入 G09 和 mutation 防线，不修改核心 loader
> **项目根：** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`
> **日期：** 2026-08-01

---

## 1. 前置 Task A 验证

| 项 | 值 |
|---|---|
| ROUND_10_TASK_A_HANDOFF.md | 存在，末尾 `TASK_A_MANIFEST_CORE_READY_FOR_TASK_B` + `P2 BLOCKED`（status = READY） |
| 任务书启动命令 | `.venv/bin/python -m pytest -q tests/p1/test_manifest_authority_type_integrity.py` |
| 结果 | **38 passed**（0 failed / 0 skipped / 0 xfailed / 0 xpassed），与 Task A §4 一致 |
| pytest 实际 collection | **38 tests collected**，node ID 与 Task A §12 逐条一致（含 20 个 required-field 参数化） |

启动条件满足，未擅自修改 loader。

## 2. changed files

本任务独占文件（任务书 §2）：

```text
scripts/run_p1_gate.py                                              (M)  G09 mandatory wiring
scripts/run_p1_mutations.py                                         (M)  M56j/M56k/M56l + M89–M91
reports/p1/manifest_type_authority_results_round_10.json            (new) M89–M91 逐子项证据
reports/p1/gate_false_positive_mutation_results_round_10.json       (new) M56j–M56l 删除保护证据
reports/p1/ROUND_10_TASK_B_HANDOFF.md                               (new) 本文件
```

运行脚本自然生成的派生产物（刷新，非手工伪造）：

```text
reports/p1/P1_GATE_REPORT.json      (gate 运行刷新，内嵌 mutation_results=91/91)
reports/p1/P1_GATE_REPORT.md        (gate 运行刷新)
reports/p1/mutation_results.json    (mutation runner 运行刷新，total=91 caught=91)
```

禁止清单逐项确认**未修改**：`loader.py` / `builder.py` / `engine.py` / `tests/p1/*`（含 Task A tests）/ `schemas/*` / `policies/*` / `plan/*` / `P1_REMEDIATION_WORKLOG.md` / `P1_ROUND_10_AUDIT_EVIDENCE.json` / `SUBMISSION_TO_CHATGPT_P1_ROUND_10.md` / P0 contracts / ADRs。Task A 的 loader.py（M）与 `tests/p1/test_manifest_authority_type_integrity.py`（new）在会话开始前已是工作树状态，未由本任务触碰。

## 3. G08 / G09 总数

| Gate | previous | final | 说明 |
|---|---|---|---|
| G08 | 117 mandatory | **117 mandatory, passed=117** | 无减少（实际 gate 报告读取） |
| G09 | 33 mandatory | **71 mandatory, passed=71** | 33（complete-evidence 11 + index-partition 10 + R9 manifest-authority 12）+ 38（Task A） |

G09 报告数来自真实 gate 运行的 `nested_mutation_pytest_stats`：

```text
G09 previous mandatory total = 33
G09 final mandatory total   = 71   (实际 collected，非猜测)
G09 final mandatory passed  = 71   (同一整数)
G09 collected               = 127  passed = 127
```

Gate 证明节点被实际 collected 和 passed（`_run_targeted_tests` 强制 node manifest，缺失/失败即 G09 FAIL），不是检查测试文件存在或 substring。

## 4. 新增 mandatory node IDs（38 个，G09）

G09 新增 `_G09_MANIFEST_AUTHORITY_FILE = "tests/p1/test_manifest_authority_type_integrity.py"`，并把以下 38 个节点加入 `_G09_REQUIRED_NODES`（来自实际 pytest collection，非猜测）：

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
test_loader_rejects_missing_required_manifest_field[snapshot_id]
test_loader_rejects_missing_required_manifest_field[schema_version]
test_loader_rejects_missing_required_manifest_field[included_strict_count]
test_loader_rejects_missing_required_manifest_field[conditional_count]
test_loader_rejects_missing_required_manifest_field[diagnostic_count]
test_loader_rejects_missing_required_manifest_field[quarantine_count]
test_loader_rejects_missing_required_manifest_field[build_status]
test_loader_rejects_missing_required_manifest_field[snapshot_hash]
test_loader_rejects_missing_required_manifest_field[build_id]
test_loader_rejects_missing_required_manifest_field[source_counts]
test_loader_rejects_missing_required_manifest_field[policy_version]
test_loader_rejects_missing_required_manifest_field[record_count]
test_loader_rejects_missing_required_manifest_field[versions]
test_loader_rejects_missing_required_manifest_field[source_files]
test_loader_rejects_missing_required_manifest_field[failure_counts_by_reason]
test_loader_rejects_missing_required_manifest_field[record_content_hashes]
test_loader_rejects_missing_required_manifest_field[production_index_hash]
test_loader_rejects_missing_required_manifest_field[diagnostic_index_hash]
test_loader_rejects_missing_required_manifest_field[quarantine_index_hash]
test_loader_rejects_missing_required_manifest_field[build_config_hash]
```

保护族覆盖（任务书 §3 全部接入）：record_count / lane-count / source-count / failure-count boolean+float rejection、missing + wrong-type build_status、top-level non-object rejection、nested versions/source_files/record-hash type rejection、recomputed returned counts / source_counts、all-four-lanes positive protection、全部 required fields deletion coverage。

## 5. M56a–M56l 结果（deletion protection）

M56 扩展至 12 个子项，全部在 temp copy 中执行、`finally` 恢复、失败原因是 mandatory node missing（真实 Gate 结果，`mandatory_node_missing_hits` 来自 `_run_targeted_tests` 的 impl 列表，非 substring 假装）：

| sub | 删除目标 | Gate 结果 | caught |
|---|---|---|---|
| M56a | G08 cross-invariant file shadowed | G08 FAIL | ✓ |
| M56b | G09 complete-evidence file shadowed | G09 FAIL | ✓ |
| M56c | G08 reference-integrity file shadowed | G08 FAIL | ✓ |
| M56d | G08 R6 `test_uncontrolled_cofactor_direction_never_strict` | G08 FAIL | ✓ |
| M56e | G08 R7 `test_heavy_atom_map_count_underflow_never_strict` | G08 FAIL | ✓ |
| M56f | G08 R8 `test_loader_rejects_hash_coherent_diagnostic_in_production` | G08 FAIL | ✓ |
| M56g | G09 R8 `test_snapshot_manifest_persists_diagnostic_index_hash` | G09 FAIL | ✓ |
| M56h | G09 R9 `test_loader_rejects_missing_manifest_diagnostic_index_hash` | G09 FAIL | ✓ |
| M56i | G09 R9 `test_loader_rejects_snapshot_identity_mismatch` | G09 FAIL | ✓ |
| **M56j** | G09 R10 `test_loader_rejects_manifest_record_count_bool`（record_count boolean node） | **G09 FAIL** | ✓ |
| **M56k** | G09 R10 `test_loader_rejects_missing_manifest_build_status`（build_status required/type node） | **G09 FAIL** | ✓ |
| **M56l** | G09 R10 `test_loader_returns_recomputed_manifest_counts`（reconstructed-return node） | **G09 FAIL** | ✓ |

M56j 实际 evidence（真实 Gate impl 输出）：

```text
P1-G09 passed=False mandatory_node_missing_hits=1: P1-G09 MANDATORY test node not
collected/executed (deleted or renamed?): tests/p1/test_manifest_authority_type_
integrity.py::test_loader_rejects_manifest_record_count_bool
```

M56a–M56l 全部继续 caught（无回归）。

## 6. M1–M91 总数与 caught（真实 mutation_results.json）

```text
M1–M88 preserved
final top-level total = 91   (来自 reports/p1/mutation_results.json，非手工)
final caught          = 91
not caught            = []
```

## 7. M89 / M90 / M91 逐子项 evidence

三个新 mutation 全部调用真实 public `load_snapshot`，pre-mutation 合法 snapshot 必先被接受；仅改写 manifest.json，非 manifest 工件（records / indexes / snapshot_hash / COMPLETE）经 `_snapshot_fingerprint` 证明字节不变；失败 token 为真实 loader 异常。

### M89 — boolean record_count

```text
build one-record valid snapshot (_g09_item_strict)
→ pre-mutation real load_snapshot succeeds
→ manifest.record_count=true (records/indexes/hash/COMPLETE 字节不变)
→ REAL loader rejects: manifest_field_type_invalid: record_count expected int got bool
caught=True
```

### M90 — nested failure-count type（真实 builder 产出的 key 值被改写）

| sub | mutation | 真实 loader 结果 | caught |
|---|---|---|---|
| M90a | `failure_counts_by_reason[<真实key>]=true` | `manifest_field_type_invalid: failure_counts_by_reason['unknown_changed_heavy_atom_source...'] expected exact int got bool` | ✓ |
| M90b | `failure_counts_by_reason[<真实key>]=1.0` | `manifest_field_type_invalid: failure_counts_by_reason['unknown_changed_heavy_atom_source...'] expected exact int got float` | ✓ |

### M91 — build_status authority order

| sub | mutation | 真实 loader 结果 | 语义 | caught |
|---|---|---|---|---|
| M91a | delete `build_status` | `manifest_required_field_missing: build_status` | presence 门控 | ✓ |
| M91b | `build_status=true` | `manifest_field_type_invalid: build_status expected str got bool` | exact-str 类型门控 | ✓ |
| M91c | `build_status="partial"` | `SnapshotIncompleteError: snapshot ... is not complete (build_status='partial')` | 语义保护（合法类型非 complete，**未**误报为 manifest type failure） | ✓ |

M91c 是合法类型但非 complete 的语义保护，证明 build_status presence → exact-str → interpret 的 authority 顺序正确。

## 8. P0 / P1 / full 实际数字

| 套件 | 结果 |
|---|---|
| Task A manifest authority（独立） | 38 passed |
| contracts | **290 passed** |
| P1 | **594 passed** |
| full | **884 passed** |
| skip / xfail / xpass | 0 / 0 / 0 |

G02 内嵌 P0 gate 子进程 10/10 green（`reports/p0/P0_GATE_REPORT.json` status=READY_FOR_CHATGPT_AUDIT）。

## 9. P1 Gate matrix（真实 gate 运行）

```text
[PASS]    P1-G01 package/runtime/lock + config & snapshot + no legacy write
[PASS]    P1-G02 strict schemas/IDs/provenance + P0 contract green
[BLOCKED] P1-G03 legacy lineage audit (external: real source not confirmed / proline-2OG case)
[BLOCKED] P1-G04 mapping adapter (external: RealMapperAdapter.map_reaction skeleton)
[PASS]    P1-G05 participant preservation/roles
[PASS]    P1-G06 lineage graph
[PASS]    P1-G07 dual ledgers valid
[PASS]    P1-G08 eligibility/quarantine (117/117 mandatory)
[PASS]    P1-G09 snapshot reproducibility (71/71 mandatory)
[BLOCKED] P1-G10 manual audit + full tests (external: no independent annotator/adjudicator)
```

```text
implementation failure = 0
external blockers     = 3   (G03, G04, G10)
overall               = BLOCKED
exit code             = 1   (非零为诚实结果：有 blocker 时 gate 返回 1)
```

G09 FAIL 未被 overall BLOCKED 掩盖（G09 passed=True）。Gate 报告 `fail_count=0`。

## 10. assumptions、failures、blocked items

**assumptions**
- M89/M90/M91 只改写 manifest.json，非 manifest 工件字节不变由 `_snapshot_fingerprint`（对除 manifest.json 外所有文件做 SHA-256）证明；若改写非 manifest 工件则记 caught=False + SETUP ERROR。
- M90 改写真实 builder 产出的 `failure_counts_by_reason` 既有 key 的值，证明 nested 精确类型检查（而非外来 key 注入）是拒绝原因。
- M91c `build_status="partial"` 期望 `SnapshotIncompleteError`（语义），与 Task A §7 冻结顺序一致，不属于 manifest type failure。
- G09 targeted test 文件列表加入 `_G09_MANIFEST_AUTHORITY_FILE`（4 个文件），与既有 complete-evidence / nested-evidence / builder 无冲突。
- 只读性：本任务未引入任何写操作到实现代码；gate / mutation runner 保持只读证据验证模式。
- 依赖/联网：无（未安装依赖、未联网）。

**failures**
- implementation failure = 0（gate `fail_count=0`）。

**blocked items（既有外部 blocker，非本任务引入）**
- G03：`real_reaction_source_not_confirmed` + `required_case_missing_proline_2og`（真实 reaction source / proline-2OG case 待用户确认）。
- G04：`RealMapperAdapter.map_reaction()` 为 skeleton（T4 follow-up）。
- G10：独立 annotator A/B + adjudication 未产出（单 LLM session 无法提供第二个独立标注者）。
- `git diff --check`：唯一 flag 是 `reports/p1/P1_PREFLIGHT.md:75 new blank line at EOF` —— 既存文件（d47d83b 引入，Task A §10 已记录），非本任务引入，不在本任务独占范围。

## 11. 提供给 Task C 的产物路径

```text
scripts/run_p1_gate.py                                     (G09 71/71 mandatory wiring)
scripts/run_p1_mutations.py                                (M56a–M56l + M89–M91)
reports/p1/P1_GATE_REPORT.json / .md                       (7/10 pass, 3 blocked, BLOCKED)
reports/p1/mutation_results.json                           (total=91 caught=91)
reports/p1/manifest_type_authority_results_round_10.json   (M89/M90a/M90b/M91a/M91b/M91c evidence)
reports/p1/gate_false_positive_mutation_results_round_10.json (M56j/M56k/M56l evidence)
reports/p1/ROUND_10_TASK_B_HANDOFF.md                      (本文件)
```

---

```
TASK_B_GATE_MUTATIONS_READY_FOR_TASK_C

P2 BLOCKED
```
