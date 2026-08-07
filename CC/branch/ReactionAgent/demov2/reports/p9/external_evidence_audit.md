# §12.3 External Evidence 落盘报告

> 父任务：HID-32（P9 全案）。本报告补 final_plan §12.3 的落盘文档，不新增实现。
> 数据源：`reaction_agent/p9/external/`（8 个文件）+ `tests/p9/test_external_*.py`（8 个测试文件，**57 tests**）。
> 边界铁律：external evidence 是 post-hoc、append-only 的 augmentation 源；与 strict channel（P3-P6）/ frozen primary run 严格隔离；只 ADD 新 p9 代码，复用 `schemas.common.StrictModel`，不 modify strict channel / hypothesis union / P4 run store。

## 1. 概述

external evidence 让系统在 frozen primary run 之外**追加**证据（不覆盖、不篡改 frozen 产物）。每条记录：携带 source allowlist 条目（source_id / license / version）；携带 license + provenance（source_version / retrieval_date / content_hash）；lane 钉死 `"external"`（永不进 strict lane）；是 `StrictModel`（`extra="forbid"`，未知字段无法注入）。单一 fail-closed intake pipeline 串起全部前置检查。

实现锚点（final_plan §12.3 / ADR-0006 / final_design §22 / Phase A criteria 1-8）：

| 模块 | 路径 | 职责 |
|---|---|---|
| schemas | `reaction_agent/p9/external/schemas.py:1` | `ExternalEvidenceSource` / `EvidenceProvenance` / `ExternalEvidenceRecord`（lane 钉死） |
| allowlist | `reaction_agent/p9/external/allowlist.py:1` | `SourceAllowlist` / `UnregisteredSourceError` |
| cache | `reaction_agent/p9/external/cache.py:1` | `EvidenceCache` / `CacheKey`（put-if-absent） |
| conflict | `reaction_agent/p9/external/conflict.py:1` | `ConflictResolution` / `resolve_record_conflict`（snapshot authoritative） |
| injection | `reaction_agent/p9/external/injection.py:1` | `scan_content` / `assert_content_inert`（defense in depth） |
| ingest | `reaction_agent/p9/external/ingest.py:1` | `IngestPipeline`（单一 fail-closed 入口，5 步有序） |
| child_run | `reaction_agent/p9/external/child_run.py:1` | `ChildAugmentation` / `ExternalEvidenceAugmenter` / `FrozenParentError` |
| benchmark | `reaction_agent/p9/external/benchmark.py:1` | `BenchmarkConfig`（`include_external=False` 默认） |

## 2. Phase A 八项前置条件（criterion 1-8）

### 2.1 Criterion 1 — Source allowlist

`SourceAllowlist`（`allowlist.py:20-51`）：`register` 把 source 快照成 frozen `SourceEntry`；`require` 返回 entry 或抛 `UnregisteredSourceError`（`UnknownReferenceError` 子类，符合 ADR-0002 错误分类）。未注册源 = reference violation，fail-closed。`ExternalEvidenceSource`（`schemas.py:31-50`）`license` + `source_version` 必填（无 license/version 不能信 provenance）。
证据：`tests/p9/test_external_allowlist.py`（5 tests）—— `test_register_and_require_registered_source:30`、`test_unregistered_source_rejected:39`、`test_unregistered_source_requires_unknown_reference_type:45`、`test_duplicate_register_rejected:52`、`test_allowlist_requires_license_and_version_on_source:59`。

### 2.2 Criterion 2 — License / provenance

`EvidenceProvenance`（`schemas.py:63-100`）：`source_version` + `retrieval_date` + `content_hash` 三必填，`content_hash` 非空。`retrieval_date` 严格 ISO-8601（`YYYY-MM-DD`），且**语义校验**拒绝不可能日期（`2026-13-45`、`2026-02-30`）。`ExternalEvidenceRecord`（`schemas.py:103-125`）`license` 非空，且在 ingest 时与注册源 license 交叉校验。
证据：`tests/p9/test_external_record_cache.py`（10 tests）—— `test_record_requires_license:59`、`test_record_requires_provenance:64`、`test_record_requires_content_hash_in_provenance:69`、`test_record_requires_retrieval_date_in_provenance:74`；`tests/p9/test_external_round2.py` —— `test_ingest_license_mismatch_blocked:143`、`test_retrieval_date_rejects_non_iso_format:125`、`test_retrieval_date_rejects_partial_iso:137`、`test_retrieval_date_rejects_impossible_date:296`。

### 2.3 Criterion 3 — Cache + date/version

`EvidenceCache`（`cache.py:22-61`）+ `CacheKey(source_id, content_hash)`（`cache.py:14-19`）。**put-if-absent**：已有 key 永不覆盖（保留原始 record + date/version stamp，可复现）。不同 content_hash 是不同 key —— 永不静默覆盖同 content_hash。`has_evidence_id`（`cache.py:56-58`）支撑 multistep search 的 ingestion 校验（P9D-R1-01）。
证据：`tests/p9/test_external_record_cache.py` —— `test_cache_put_and_get_roundtrip:79`、`test_cache_hit_preserves_date_version_stamp:88`、`test_cache_miss_returns_none:99`、`test_different_content_hash_is_distinct_entry:104`、`test_cache_key_is_hashable:120`、`test_unknown_fields_rejected:126`；`tests/p9/test_external_round2.py` —— `test_cache_put_if_absent_preserves_original:81`、`test_cache_put_if_absent_new_key_accepts:110`。

### 2.4 Criterion 4 — Conflict policy（snapshot authoritative）

`resolve_record_conflict`（`conflict.py:57-82`）：snapshot 按 `source_id` 索引。源不在 snapshot → `external_accepted`；同 content_hash → `consistent`；不同 hash → `snapshot_wins`（external suppressed）。`ConflictPolicy`（`conflict.py:33-54`）fail-closed —— 无法决断时绝不接受 external。external evidence 永不静默覆盖 frozen snapshot。
证据：`tests/p9/test_external_conflict.py`（5 tests）—— `test_snapshot_authoritative_on_conflict:36`、`test_no_conflict_when_absent_from_snapshot:44`、`test_no_conflict_when_snapshot_matches:51`、`test_conflict_policy_fails_closed:58`、`test_snapshot_key_uses_source_id:67`。

### 2.5 Criterion 5 — Injection isolation（铁律）

分层防御（`injection.py:9-21`）：
1. **Schema 层（primary, authoritative）**：`ExternalEvidenceRecord` **无** permission/tool/role 字段 —— external text 无处可写以改权限；`extra="forbid"` 拒绝未知字段。
2. **Content scanner（best-effort, secondary）**：`scan_content` 归一化空白后查 `CONTROL_DIRECTIVES`（权限提升 / 指令覆盖 / schema bypass）+ 词边界匹配 `SCHEMA_FIELD_NAMES`。benign 化学 text（含 "role"/"ranking"/"decision" 等常见词）**不**误拦。

`assert_content_inert`（`injection.py:106-112`）：blocked 即抛 `ValueError`（fail-closed）。
证据：`tests/p9/test_external_injection.py`（8 tests）—— `test_benign_content_passes_scan:43`、`test_permission_grant_directive_blocked:49`、`test_instruction_override_blocked:56`、`test_schema_field_smuggling_blocked:62`、`test_unknown_field_rejected_by_schema:69`、`test_assert_content_inert_raises_on_blocked:86`、`test_assert_content_inert_passes_on_benign:91`、`test_external_evidence_never_carries_permission_field:95`（断言 schema 无 `permissions`/`tools`/`role` 属性）。

### 2.6 Criterion 6 — Child-run separation

`ExternalEvidenceAugmenter.augment`（`child_run.py:55-76`）：external augmentation **必须走 child run**。`parent_frozen=True` → 抛 `FrozenParentError`（frozen parent 永不 augment）。parent evidence list 永不 mutate（immutability）—— child 带 parent + external 的 union。`child_run_id` content-addressed（`_compute_child_run_id:38-45`）：`{parent_run_id}-ext-{evidence_hash[:12]}`，同 parent + 同 evidence set → 同 id（幂等），不同 evidence set → 不同 id（无碰撞）。模块只定义 augmentation 语义，**不 modify P4 run store**（strict-untouched）。
证据：`tests/p9/test_external_child_run.py`（5 tests）—— `test_child_augmentation_records_parent_and_evidence:40`、`test_child_augmentation_requires_parent:51`、`test_augmenter_rejects_frozen_parent:61`、`test_augmenter_builds_child_manifest_for_active_parent:72`、`test_augmenter_never_mutates_parent:84`；`tests/p9/test_external_round2.py` —— `test_different_evidence_sets_different_child_run_id:199`、`test_same_evidence_set_same_child_run_id:218`。

### 2.7 Criterion 7 — Benchmark default off

`BenchmarkConfig`（`benchmark.py:13-16`）`include_external: bool = False`。`is_external_in_benchmark`（`benchmark.py:19-22`）默认 False —— external evidence **不**进默认 benchmark，必须显式 opt-in。
证据：`tests/p9/test_external_benchmark_lane.py`（5 tests）—— `test_external_benchmark_default_off:32`、`test_is_external_in_benchmark_default_false:37`、`test_explicitly_enabled:41`、`test_strict_benchmark_never_pulls_external:46`、`test_lane_non_contamination_property:56`。

### 2.8 Criterion 8 — Lane non-contamination

`ExternalEvidenceRecord.lane: Literal["external"] = "external"`（`schemas.py:117`）—— external record 永不被提升进 strict lane 的 candidate set。与 `Lane.strict` 是不同值，record 不能二者皆是。
证据：`tests/p9/test_external_benchmark_lane.py:test_lane_non_contamination_property:56`（`rec.lane == "external"` 且 `rec.lane != Lane.strict.value`）。

## 3. IngestPipeline：单一 fail-closed 入口（5 步有序）

`IngestPipeline.ingest`（`ingest.py:73-115`）强制确定性检查顺序：

| 步 | 检查 | 失败行为 | 证据测试 |
|---|---|---|---|
| 1 | allowlist：`SourceAllowlist.require` | `UnregisteredSourceError` | `test_intake_unregistered_source_rejected:241` |
| 2 | injection：`assert_content_inert` | `IngestRejectionError` | `test_intake_injection_payload_rejected:251` |
| 3 | license 交叉校验：`record.license != entry.license` | `IngestRejectionError` | `test_ingest_license_mismatch_blocked:143` |
| 4 | conflict：`resolve_record_conflict` → `snapshot_wins` | suppressed（不入 cache） | `test_intake_conflict_suppressed:261` |
| 5 | cache：`EvidenceCache.put`（put-if-absent） | accepted（入 cache） | `test_intake_benign_record_passes:277` |

`IngestResult`（`ingest.py:38-56`）：`resolution ∈ {accepted, snapshot_wins, rejected}` + `suppressed` 便捷布尔 + `cache`。无 external evidence 不经全检入系统。

## 4. Round 2 整改（kimi Phase-A Round-1 findings P9A-R1-01..05）

| Finding | 优先级 | 整改 | 证据测试 |
|---|---|---|---|
| P9A-R1-01 | P1 | intake pipeline wiring：allowlist → injection → license → conflict → cache 全串起来 | `test_intake_unregistered_source_rejected:241` / `test_intake_injection_payload_rejected:251` / `test_intake_conflict_suppressed:261` / `test_intake_benign_record_passes:277` |
| P9A-R1-02 | P1 | cache put-if-absent：re-put 同 key 返回 original，不覆盖 | `test_cache_put_if_absent_preserves_original:81` / `test_cache_put_if_absent_new_key_accepts:110` |
| P9A-R1-03 | P2 | scanner strength：空白混淆归一化后拦截；benign 化学 text（role/ranking/decision）不误拦；真指令仍拦 | `test_scanner_obfuscation_double_space_blocked:158` / `test_scanner_obfuscation_tab_blocked:164` / `test_scanner_benign_chemical_role_passes:170` / `test_scanner_benign_ranking_passes:176` / `test_scanner_benign_decision_passes:182` / `test_scanner_real_control_still_blocked:188` |
| P9A-R1-04 | P2 | child_run_id 碰撞：content-addressed，不同 evidence set → 不同 id | `test_different_evidence_sets_different_child_run_id:199` / `test_same_evidence_set_same_child_run_id:218` |
| P9A-R1-05 | P2 | date/license validation：ISO-8601 格式 + 语义校验（impossible date）+ license mismatch | `test_retrieval_date_rejects_non_iso_format:125` / `test_retrieval_date_accepts_iso_format:131` / `test_retrieval_date_rejects_partial_iso:137` / `test_ingest_license_mismatch_blocked:143` / `test_retrieval_date_rejects_impossible_date:296` |

## 5. 实测证据汇总

| 证据来源 | 路径 | 测试数 |
|---|---|---|
| source allowlist | `tests/p9/test_external_allowlist.py` | 5 |
| license / provenance / cache / date | `tests/p9/test_external_record_cache.py` | 10 |
| injection isolation | `tests/p9/test_external_injection.py` | 8 |
| conflict policy | `tests/p9/test_external_conflict.py` | 5 |
| child-run separation | `tests/p9/test_external_child_run.py` | 5 |
| benchmark default off + lane | `tests/p9/test_external_benchmark_lane.py` | 5 |
| Phase A Round 2 整改 | `tests/p9/test_external_round2.py` | 19 |
| **合计** | | **57** |

## 6. 风险与边界

- **post-hoc append-only**：external evidence 只追加，不覆盖 frozen snapshot（conflict policy snapshot authoritative）、不 mutate frozen parent（child-run separation + `FrozenParentError`）。
- **隔离**：lane 钉死 `"external"`，永不进 strict candidate set；schema 无 permission/tool/role 字段；`extra="forbid"`；不 modify P4 run store。
- **fail-closed**：未注册源、injection payload、license mismatch 全 fail-closed；conflict policy 无法决断时拒绝接受。
- **benchmark default off**：external evidence 默认不进 benchmark，显式 opt-in 才参与。
- **不伪造**：provenance 三字段必填；retrieval_date 严格 ISO + 语义校验；content_hash 非空；cache 保留原始 date/version stamp（可复现）。

## 7. 结论

external evidence 的 Phase A 八项前置条件（source allowlist / license-provenance / cache-date-version / conflict policy / injection isolation / child-run separation / benchmark default off / lane non-contamination）全部实现，并由 `IngestPipeline` 单一 fail-closed 入口串成 5 步有序检查。`tests/p9/test_external_*.py`（8 文件，57 tests）覆盖；Round 2 五项 audit findings（P9A-R1-01..05）全部整改并有对应 RED 测试。本报告仅落盘，不新增实现。
