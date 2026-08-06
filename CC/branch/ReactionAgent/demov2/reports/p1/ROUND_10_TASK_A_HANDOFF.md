# Round 10 — Task A Handoff：Manifest Core Validator

> **执行角色：** Task A（manifest core validator + 独立 RED/GREEN tests）
> **执行顺序：** A → B → C；本文件供 Task B 读取（mandatory-node 清单见 §12）
> **性质：** P1 manifest type-authority 最小整改，不是 P2
> **项目根：** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`
> **日期：** 2026-08-01

---

## 1. branch / HEAD / dirty status

| 项 | 值 |
|---|---|
| branch | `main` |
| HEAD | `4eb463368e38f2faa3d3656a05974c4b1c1211a6`（未提交，未 commit） |
| dirty | dirty（开工前已存在 Round 7/8/9 未提交改动 + 本任务新增 2 个文件） |

工作树原有改动属于用户，未清理、未 reset、未覆盖。

## 2. changed files

本任务独占文件（任务书 §3）：

```text
reaction_agent/snapshot/loader.py                              (M)
tests/p1/test_manifest_authority_type_integrity.py             (new, 623 lines, 38 tests)
reports/p1/ROUND_10_TASK_A_HANDOFF.md                          (new, 本文件)
```

说明：`loader.py` 的 git diffstat 较大（+678/-50）是因为 HEAD 是最后一次 commit，工作树里包含了此前从未提交的 Round 7/8/9 loader 改动。本任务实际新增的是 **Round 10 manifest type-authority 区块**（§R10-1.1 顶层 object 确认、§R10-1.2 build_status gate + 精确类型、§R10-1.3 递归 shape 校验、§R10-1.4 返回重建值）。

## 3. RED 结果（旧实现，真实运行）

运行命令：

```bash
.venv/bin/python -m pytest -q tests/p1/test_manifest_authority_type_integrity.py
```

结果：**16 failed / 22 passed**。失败明细全部命中 ChatGPT Round 9 独立审核确认的漏洞：

| # | 失败原因 | 测试节点（简写） | 旧实现实际行为 |
|---|---|---|---|
| 1 | **DID NOT RAISE** | `test_loader_rejects_manifest_record_count_bool` | `True` 通过 `isinstance(int)`，且 `True == 1`，完全被接受 |
| 2 | 下游 Pydantic 抛错 | `test_loader_rejects_manifest_included_strict_count_bool` | loader 放行，`SnapshotManifest` 构造时 `ValidationError` |
| 3 | 下游 Pydantic 抛错 | `test_loader_rejects_manifest_conditional_count_bool` | 同上 |
| 4 | 下游 Pydantic 抛错 | `test_loader_rejects_manifest_diagnostic_count_bool` | 同上 |
| 5 | 下游 Pydantic 抛错 | `test_loader_rejects_manifest_quarantine_count_bool` | 同上 |
| 6 | 下游 Pydantic 抛错 | `test_loader_rejects_manifest_source_count_bool` | `{src: True}` 与 `{src: 1}` 相等，放行，Pydantic 抛错 |
| 7 | 下游 Pydantic 抛错 | `test_loader_rejects_manifest_source_count_float` | `{src: 1.0}` 与 `{src: 1}` 相等，放行，Pydantic 抛错 |
| 8 | **DID NOT RAISE** | `test_loader_rejects_manifest_failure_count_bool` | `{reason: True} == {reason: 1}`，完全被接受 |
| 9 | **DID NOT RAISE** | `test_loader_rejects_manifest_failure_count_float` | `{reason: 1.0} == {reason: 1}`，完全被接受 |
| 10 | 错误异常类型 | `test_loader_rejects_missing_manifest_build_status` | `.get()` 默认 "unknown" → `SnapshotIncompleteError`（应为 `manifest_required_field_missing`） |
| 11 | 错误异常类型 | `test_loader_rejects_manifest_build_status_wrong_type` | `True != "complete"` → `SnapshotIncompleteError`（应为 `manifest_field_type_invalid`） |
| 12 | **AttributeError** | `test_loader_rejects_non_object_manifest` | `[]` 无 `.get` → `AttributeError`（应为 `manifest_field_type_invalid`） |
| 13 | generic token | `test_loader_rejects_manifest_versions_nested_wrong_type` | versions 进 canonical 导致 generic hash mismatch |
| 14 | generic token | `test_loader_rejects_manifest_source_files_nested_wrong_type` | `manifest_source_hash_mismatch` 而非 `manifest_field_type_invalid` |
| 15 | generic token | `test_loader_rejects_manifest_record_hash_list_nested_wrong_type` | `manifest_record_hashes_mismatch` 而非 `manifest_field_type_invalid` |
| 16 | 错误异常类型 | `test_loader_rejects_missing_required_manifest_field[build_status]` | `SnapshotIncompleteError`（应为 `manifest_required_field_missing`） |

22 个 pass = 3 个正面保护测试 + 19/20 个 required-field 删除参数化（除 `[build_status]` 外的全部已通过，因为 Round 9 已实现 required-field presence 检查）。

> RED 证明满足任务书 §5 最低要求：`record_count=true` 与 failure-count boolean 均在旧实现上 **DID NOT RAISE**。

## 4. GREEN 结果

```bash
.venv/bin/python -m pytest -q tests/p1/test_manifest_authority_type_integrity.py
```

**38 passed**（0 failed / 0 skipped / 0 xfailed / 0 xpassed）。

## 5. 新增测试完整 pytest node ID（38 个）

```text
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_record_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_included_strict_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_conditional_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_diagnostic_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_quarantine_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_source_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_source_count_float
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_failure_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_failure_count_float
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_manifest_build_status
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_build_status_wrong_type
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_non_object_manifest
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_versions_nested_wrong_type
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_source_files_nested_wrong_type
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_record_hash_list_nested_wrong_type
tests/p1/test_manifest_authority_type_integrity.py::test_loader_returns_recomputed_manifest_counts
tests/p1/test_manifest_authority_type_integrity.py::test_loader_returns_recomputed_source_counts
tests/p1/test_manifest_authority_type_integrity.py::test_loader_accepts_round10_verified_manifest_all_four_lanes
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[snapshot_id]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[schema_version]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[included_strict_count]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[conditional_count]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[diagnostic_count]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[quarantine_count]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[build_status]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[snapshot_hash]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[build_id]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[source_counts]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[policy_version]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[record_count]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[versions]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[source_files]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[failure_counts_by_reason]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[record_content_hashes]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[production_index_hash]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[diagnostic_index_hash]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[quarantine_index_hash]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[build_config_hash]
```

## 6. strict type / shape contract（冻结）

- **顶层 object**：`json.load` 后必须 `type(manifest) is dict`；非 object（list/str/number/null）→ `manifest_field_type_invalid`（fail closed，绝不进入 `.get()` / AttributeError）。
- **精确 primitive 类型**：整数 authority 字段必须 `type(value) is int`（**禁止** `isinstance(value, int)`，因 `isinstance(True, int) is True`）；str/dict/list 同样使用 JSON 精确顶层类型 `type(value) is ...`。错误统一 `manifest_field_type_invalid`。
- **递归 shape**：
  ```text
  source_counts            = dict[str, exact int >= 0]
  failure_counts_by_reason = dict[str, exact int >= 0]
  source_files             = dict[str, non-empty str]
  versions                 = dict[str, non-empty str]
  record_content_hashes    = list[non-empty str]
  ```
  `true` / `false` / `1.0` 一律不得作为整数计数通过。

## 7. build_status 顺序（冻结语义）

```text
parse JSON
→ confirm top-level object (manifest_field_type_invalid)
→ build_status presence   (missing → manifest_required_field_missing)
→ build_status exact str  (non-str → manifest_field_type_invalid)
→ interpret build_status  (!= "complete" → SnapshotIncompleteError)
→ full required presence + exact top-level types (all 20 fields)
→ nested shape/type checks
→ COMPLETE marker
→ index partition
→ canonical hash
→ manifest authority comparisons
→ construct returned record
```

语义：

```text
missing build_status   → manifest_required_field_missing
build_status=true      → manifest_field_type_invalid
build_status="partial" → SnapshotIncompleteError
build_status="complete" → continue
```

> **设计说明（assumption）**：任务书 §6.4 的字面顺序是 "required presence → strict types → interpret build_status"。为同时满足（a）新语义 "missing build_status → `manifest_required_field_missing`" 与（b）保留 §16.5 契约 —— `test_load_snapshot_rejects_incomplete`（test_snapshot_builder.py:801）构建 `build_status="partial"` 且缺失多个 required 字段的 manifest 并必须得到 `SnapshotIncompleteError` —— 本实现把 **build_status 自身的 presence + exact-str 检查** 置于 interpret 之前，把 **全量 required/type/nested 检查** 置于 interpret 之后。若按字面顺序先做全量 required 检查，该 partial manifest 会先抛 `manifest_required_field_missing` 而破坏既有契约。此为唯一偏离，其余严格遵循 §6.4。

## 8. reconstructed returned fields（`_validate_manifest_authority` 返回值）

不再复制可重建的 raw manifest 值：

```text
snapshot_id            ← expected_snapshot_id ("snap_" + snapshot_hash[:12])
snapshot_hash          ← recomputed_snapshot_hash
included_strict_count  ← rebuilt lane_counts["strict"]
conditional_count      ← rebuilt lane_counts["conditional"]
diagnostic_count       ← rebuilt lane_counts["diagnostic"]
quarantine_count       ← rebuilt lane_counts["quarantine"]
build_status           ← verified literal "complete"
source_counts          ← dict(sorted(rebuilt src_counts.items()))
```

Trust-root 字段（`schema_version` / `build_id` / `policy_version` / `build_config_hash`）无法从 records/indexes 重建，但已被 canonical hash 保护 —— 在严格类型校验 + hash 校验后返回 manifest 值。`SnapshotManifest` / `SnapshotRecord` 全部由该 verified dict 构造，杜绝 `SnapshotManifest(**raw_manifest_values_without_cross_verify)`。

## 9. contracts / P1 / full 实际数字（§8 顺序串行）

| 套件 | Round 9 基线 | Round 10 最终 |
|---|---|---|
| contracts | 290 passed | **290 passed** |
| P1 | 556 passed | **594 passed**（556 + 38） |
| full | 846 passed | **884 passed**（846 + 38） |
| skip / xfail / xpass | 0 / 0 / 0 | **0 / 0 / 0** |

回归命令（全部通过）：

```bash
.venv/bin/python -m pytest -q tests/p1/test_manifest_authority_type_integrity.py
.venv/bin/python -m pytest -q tests/p1/test_snapshot_nested_evidence.py tests/p1/test_snapshot_builder.py tests/p1/test_snapshot_complete_evidence.py   # 89 passed
.venv/bin/python -m pytest -q tests/contracts          # 290 passed
.venv/bin/python -m pytest -q tests/p1                 # 594 passed
.venv/bin/python -m pytest -q                          # 884 passed
```

`git diff --check`：**我的 3 个文件全部 clean（exit=0）**。唯一 flag 是 `reports/p1/P1_PREFLIGHT.md:75 new blank line at EOF` —— 该文件是既有文件（git status 已为 M，d47d83b 引入），不在 Task A 独占范围（属 Task C 的 report 域），本任务未修改它，仅在 handoff 如实记录。

## 10. assumptions 与 unresolved items

- **build_status gate 顺序偏离**：见 §7 设计说明，为保留 `test_load_snapshot_rejects_incomplete` 的 §16.5 契约而做，已用既有测试验证（89 passed 中覆盖）。
- **negative test 的 "records/indexes/hash/COMPLETE 不变"**：每个测试只写 `manifest.json`（`_write_manifest`），records/indexes/COMPLETE 与 snapshot_hash 在构造上未被触碰。mutation runner 级别的严格 artifact-不变断言属于 Task B 的 M 系列。
- **P1_PREFLIGHT.md:75**：既存 `git diff --check` flag，非本任务引入，未修改。
- **未运行 / 未修改正式 P1 Gate 与 mutation runner**（`scripts/run_p1_gate.py`、`scripts/run_p1_mutations.py`）—— 属 Task B。
- **只读行为**：loader 依旧只读，未引入任何写操作。
- **依赖/联网**：无（未安装依赖、未联网）。

## 11. 未修改的 Gate / mutations / reports / frozen files

本任务**未修改**以下文件（任务书 §3 禁止清单逐项确认）：

```text
scripts/run_p1_gate.py
scripts/run_p1_mutations.py
reports/p1/P1_REMEDIATION_WORKLOG.md
reports/p1/P1_GATE_REPORT.{json,md}
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

不修改 frozen design / schemas / builder 来绕过 loader 问题；Round 8 exact index partition、diagnostic hash、M83–M85、R9-01/02/03 全部保留（89 passed 回归覆盖）。

## 12. 提供给 Task B 的 mandatory-node 清单

Task B 接入 Gate / G09 / mutation 时，以下 **38 个节点** 是本任务的 mandatory 测试（要求全部真实调用 public `load_snapshot`，断言稳定 token）：

```text
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_record_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_included_strict_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_conditional_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_diagnostic_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_quarantine_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_source_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_source_count_float
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_failure_count_bool
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_failure_count_float
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_manifest_build_status
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_build_status_wrong_type
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_non_object_manifest
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_versions_nested_wrong_type
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_source_files_nested_wrong_type
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_manifest_record_hash_list_nested_wrong_type
tests/p1/test_manifest_authority_type_integrity.py::test_loader_returns_recomputed_manifest_counts
tests/p1/test_manifest_authority_type_integrity.py::test_loader_returns_recomputed_source_counts
tests/p1/test_manifest_authority_type_integrity.py::test_loader_accepts_round10_verified_manifest_all_four_lanes
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[snapshot_id]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[schema_version]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[included_strict_count]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[conditional_count]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[diagnostic_count]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[quarantine_count]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[build_status]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[snapshot_hash]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[build_id]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[source_counts]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[policy_version]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[record_count]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[versions]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[source_files]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[failure_counts_by_reason]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[record_content_hashes]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[production_index_hash]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[diagnostic_index_hash]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[quarantine_index_hash]
tests/p1/test_manifest_authority_type_integrity.py::test_loader_rejects_missing_required_manifest_field[build_config_hash]
```

---

```
TASK_A_MANIFEST_CORE_READY_FOR_TASK_B

P2 BLOCKED
```
