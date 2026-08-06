# ReactionAgent — 真实数据接入 P2/P3/P4 任务书

**目标：** 把 50 条真实反应案例接入 P2/P3 管道，产出 real evidence，解锁 P4 G12/G13/G14（当前因 synthetic-only 而 BLOCKED）。

**生成日期：** 2026-08-06
**背景：** kimi-k3 已完成 P4 Round 8 审核（裁决 BLOCKED）。3601 条真实 Rhea 数据存在，但从未被 P2/P3 消费。已清洗出 50 条 audited cases 候选集。

---

## 一、代码树地理（关键，必须先对齐）

**P2/P3/P4 代码不在同一个目录！** 它们是独立 git worktree：

| 阶段 | 代码位置 | 产物位置 | 分支 |
|---|---|---|---|
| P2 | `/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2` | 该 worktree 的 `reports/p2/` | `codex/p2-orchestra` |
| P3 | `/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2` | 该 worktree 的 `reports/p3/` | `codex/p3-strict-kernel` |
| P4 | `/Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2` | 该 worktree 的 `reports/p3/` + `reports/p2/` | `worktree-p4-strict-kernel` |
| P5/demov2 主 | `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2` | 只有 P0/P1/P5 代码 | `main` |

**注意：** demov2 主目录**没有** P2/P3 代码。要接入必须跨 3 个 worktree 操作（或先合并代码）。

---

## 二、数据文件位置

| 文件 | 路径 | 说明 |
|---|---|---|
| **50 条候选集** | `/Volumes/CC/Enzyme_Agent/depending/data/audited_cases/audited_cases_50.json` | 已清洗，含 case_id / reaction_smiles / enzyme_annotations / ec_subclass / reacting_center / drfp / audit_status |
| 候选集摘要 | `/Volumes/CC/Enzyme_Agent/depending/data/audited_cases/audited_cases_50_summary.md` | 分层表 + 抽样方法 |
| 清洗脚本 | `/tmp/clean_real_cases.py` | 可复查清洗逻辑 |
| 质量报告 | `/tmp/real_data_quality_report.md` | 完整数据质量分析 |
| 原始数据 | `/Volumes/CC/Enzyme_Agent/depending/data/rxn2enzyme_positives.pkl` | 3601 条真实 Rhea 反应（勿修改，只读） |
| 特征 | `/Volumes/CC/Enzyme_Agent/depending/data/feature/reaction/reacting_center/reacting_center.pkl` | 中心原子索引 |
| 特征 | `/Volumes/CC/Enzyme_Agent/depending/data/feature/reaction/drfp/rxn2fp.pkl` | 2048-d DRFP |

---

## 三、P2 输入 Schema（要生成的产物）

### 3a. `mini_snapshot_manifest.json`（`MiniSnapshotManifest`，P2 worktree `reaction_agent/evidence/mini_snapshot.py:120`）

```
manifest_id, snapshot_id, snapshot_hash, schema_version, requires_real_audit, manifest_hash
cases: [MiniSnapshotCaseRecord]
```

`MiniSnapshotCaseRecord`（mini_snapshot.py:58）必填字段：
- `case_id`, `query_id`, `fold_id`, `snapshot_id`, `snapshot_hash`（NonEmptyStr）
- `evidence_kind`: **`real`**（不能是 synthetic_fixture）
- `source_reaction_ids: list[str]`
- `coverage_tags: list[CoverageTag]`（枚举：single_reactant, multi_reactant, single_product, multi_product, oxidation, reduction, hydroxylation, hydrolysis, transfer, cleavage, multiple_compatible_sites, no_compatible_site, ood, mapping_ambiguity, invalid_input, equivalent_smiles, stereo, known_lineage_regression）
- `audit_record_ids: list[str]` — **real case 必须 ≥1**（validator line 86）
- `provenance`, `audit_status`, `case_hash`（content-addressed 自动填充）

**约束：** `requires_real_audit=True` 时 `real_case_count` 必须在 **[20, 50]**（validator line 150）。

### 3b. `truth_records.json`（`TruthRecord`，P2 worktree `reaction_agent/schemas/evaluation.py:152`）

```
case_id, query_id, fold_id, snapshot_id, snapshot_hash, truth_policy_version,
annotation_completeness(complete|incomplete), allowed_product_set[], context_tags[],
source_provenance, incomplete_reason?, audit_status
```

`AllowedProductTarget`（evaluation.py:142）= `target_id` + `AuditedProductIdentity`。
`AuditedProductIdentity`（evaluation.py:100）关键：**必须用 RDKit 预计算 `exact_key` / `stereo_aware_key` / `stereo_agnostic_key` / `tautomer_family_key` / `salt_neutralized_family_key` / `component_set_key`** —— 禁止 raw SMILES 字符串 fallback。

### 3c. `split_manifest.json`（`SplitManifest`，`reaction_agent/evaluation/isolation.py`）

```
snapshot_id, snapshot_hash, fold_id, split_version, audit_complete, split_manifest_hash
train_query_ids[] / train_reaction_ids[] / train_evidence_ids[]
validation_*[] / test_*[]
provenance
```

### 3d. `case_registry.json` + `funnel_records.json` + `fixture_vs_real_evidence_manifest.json`

- `case_registry.json`: `{registered_cases: [query_id...], all_x_authoritative_cases: [query_id...]}`
- `funnel_records.json`: `[{case_id, outcome}]`
- `fixture_vs_real_evidence_manifest.json`（`RealFixtureEvidenceManifest`，mini_snapshot.py:191）：**必须把 split/truth/registry/funnel 声明为 `evidence_kind=real`**，否则 P2 Gate 判 BLOCKED（gate.py:334）

---

## 四、P3 输入 Schema（`current_run_artifact.json`）

**P4 把它当 `KernelResult` 读**（P3 worktree `reaction_agent/p3/schemas.py:900`）。**当前没有任何生产者**——必须跑 `run_kernel(mode="real")` 后 dump。

必填字段（`_KERNEL_RESULT_REQUIRED`，P4 worktree `reaction_agent/adapters/p3_consumer.py:70`）：
```
run_id, status(completed|failed|blocked), query_id, case_id, fold_id,
snapshot_id, snapshot_hash, manifest, normalized_query, capability_status,
candidates[], trace, failures[], evidence_kind(real|synthetic_fixture|blocked|diagnostic)
```

嵌套（所有嵌套都必须带**相同 run namespace** → `_namespace_consistent`，p3_consumer.py:232）：
- `manifest`: `KernelRunManifest`（schemas.py:178）
- `normalized_query`: `NormalizedQuery`（schemas.py:209）
- `capability_status`: `CapabilityStatus`（schemas.py:229）— **`real_snapshot_available`, `automatic_donor_available`, `chemistry_backend_available`, `explicit_map_validator_available` 全 true** 才能 `evidence_kind=real`（`_verify_real_capability`，p3_consumer.py:330）
- `candidates[]`: `StrictCandidate`（schemas.py:625）
- `trace`: `CandidateTrace`（schemas.py:834）— ID 集合必须与 candidates 完全匹配
- `failures[]`: `KernelFailure`（schemas.py:892）

**P4 hash 校验严格**（`_verify_artifact_hashes`，p3_consumer.py:256）：`manifest_hash`, `request_hash`, `identity_hash`, 每个 candidate `content_hash`, 每个 `path_hash` 必须从内容重算匹配（preimage 函数在 p3_consumer.py:98-154）。`evidence_kind` 必须在 header + 所有嵌套记录一致（`_verify_nested_classification`）。

**生产入口：** `run_kernel(input_smiles=..., case_id=..., fold_id=..., mode="real", snapshot_path=..., train_view=...)`（`reaction_agent/p3/kernel.py:110`）。real 模式 fail-closed：
- `capability_status` 不能有 `CAPABILITY_UNAVAILABLE`（kernel.py:214-241）
- 需要 `train_view.authority_manifest` 是 `ProductionAuthorityHandle`（kernel.py:273-287）— **唯一创建方式是 `_build_production_authority_handle(snapshot_id, snapshot_hash, reaction_hashes)`（`reaction_agent/p3/fixtures.py:522`），要求先验证真实 P1/P2 snapshot。当前没有公共适配器** — 这是需要补的代码缺口。

---

## 五、P4 需要的 5 个文件（G12/G13/G14 依赖）

| 文件 | 路径（P4 worktree） | 现状 |
|---|---|---|
| `p3_p4_interface_manifest.json` | `reports/p3/` | ✅ 存在（version p3-p4-3） |
| `current_run_artifact.json` | `reports/p3/` | ❌ **缺失，无生产者** |
| `p3_p4_interface_pin.json` | `reports/p3/` | ❌ **缺失**；`status` 必须 `"accepted"`，`content_sha256`/`schema_hash` 匹配 manifest（`verify_interface_pin`，p3_interface_pin.py:111） |
| `P2_GATE_REPORT.json` | `reports/p2/` | ❌ 缺失（P4 worktree 内） |
| `P1_GATE_REPORT.json` | `reports/p1/` | 存在但 `status=NOT_READY_FOR_CHATGPT_AUDIT` |

**G12**（run_p4_gate.py:702）：`resolve_bundle()` 产出 `capability_available=True` + seal 验证 + registry-bound。
**G13**（run_p4_gate.py:732）：bundle `evidence_kind == P4Classification.real`。
**G14**（run_p4_gate.py:752）：`P2ReceiptVerifier().verify(...)` 零 issues。

### P2 receipt 格式（G14 要的 `P2_GATE_REPORT.json`）

`authority/receipts.py` — `P2_ACCEPTED_STATUS = "READY_FOR_CHATGPT_P2_AUDIT"`, `P2_GATE_VERSION = "p2-gate-1"`。必填字段（receipts.py:66-84）：
```
kind, run_id, session_nonce, status, gate_version, checks, all_passed,
gate_items_hash, receipt_hash,
case_id, query_id, fold_id, snapshot_id, snapshot_hash, artifact_root
```

Verifier 检查（fail-closed）：
- `status` 精确匹配、`gate_version` 精确匹配
- `receipt_hash` 从内容重算 **且** 注册在 `PRODUCTION_ISSUANCE_REGISTRY`（issuance.py:69）
- `gate_items_hash` 从 `PRODUCTION_GATE_EXECUTION_REGISTRY` 重算（gate_execution.py:83）
- 六身份字段 + `artifact_root` **精确 cross-bind** 到 P3 bundle namespace（`_cross_bind`，receipts.py:241）
- **两个 registry 都是 process-local 单例，当前为空** — 真实 P2 gate 必须通过 opaque capability 注册进去，否则 G14 永远 BLOCKED

**Schema 不匹配要注意：** P2 worktree 的 `P2GateReport` 输出 `overall`/`item_results`/`report_hash`——**不是** P4 receipt 要的 `status`/`checks`/`all_passed`/`receipt_hash`/六身份字段。P2 gate 报告必须扩展成 receipt 格式（或加适配器）。

---

## 六、字段映射（audited_cases_50 → P2 → P3）

| audited_cases_50 字段 | → P2 `MiniSnapshotCaseRecord` | → P2 `TruthRecord` | → P3 `KernelResult` |
|---|---|---|---|
| `case_id` | `case_id` | `case_id` | `case_id` |
| —（派生） | `query_id`（如 `query_{i}`） | `query_id` | `query_id` |
| —（派生） | `fold_id`（如 `fold_real_0`） | `fold_id` | `fold_id` |
| —（P1 snapshot） | `snapshot_id`/`snapshot_hash` | 同 | 同 |
| `reaction_smiles`（`>>` 左侧） | — | — | `input_smiles`/`canonical_smiles` |
| `reaction_smiles`（`>>` 右侧） | — | `allowed_product_set[].identity.original_representation` + RDKit keys | expected product |
| `enzyme_annotations`（如 `[["D7UQ40","1.1.3.42"]]`） | — | `source_provenance`/`context_tags` | — |
| `ec_subclass`（如 `1.1.3`） | `coverage_tags`（映射到枚举） | `context_tags` | — |
| `source`（`rhea_real`） | `provenance` | `source_provenance` | — |
| `audit_status`（`candidate`） | —（须变 `audited` + audit_record_ids） | `audit_status` | — |
| `reacting_center` | — | — | site preconditions |
| `drfp`（2048 floats） | — | — | donor retrieval 相似度输入 |
| —（**缺失**） | `audit_record_ids`（real 必须 ≥1） | audit record refs | — |
| —（**缺失**） | P1 `source_reaction_ids` | — | `manifest.request` |

---

## 七、缺口清单（必须逐条补）

1. **P2/P3 代码不在 demov2 主目录** — 必须从对应 worktree 跑（或先合并代码）
2. **`current_run_artifact.json` 无生产者** — 需新脚本跑 `run_kernel(mode="real")` + dump
3. **`p3_p4_interface_pin.json` 不存在** — 需创建（integrator-owned, `status: "accepted"`）
4. **50 案例缺** `query_id`/`fold_id`/`snapshot_id`/`snapshot_hash`/`evidence_kind=real`/`source_reaction_ids`/`coverage_tags`/`audit_record_ids`/`provenance`
5. **无 audited identity keys** — `TruthRecord.allowed_product_set` 需 RDKit 预计算 `exact_key`/`stereo_*`/`tautomer_*`（禁止 raw SMILES fallback）
6. **P1 real snapshot 是 BLOCKED** — `reports/p1/snapshot_build_sample.json` → `pipeline_blocked_at: "validated complete atom mapping and independently audited lineage resolution are required"`。P3 `probe_real_snapshot` 要求 on-disk snapshot `build_status == "complete"`
7. **P2 Gate 报告格式不匹配** — 需扩展成 receipt 格式 + 注册进 `PRODUCTION_ISSUANCE_REGISTRY` + `PRODUCTION_GATE_EXECUTION_REGISTRY`
8. **P1 receipt 也不合规** — `status=NOT_READY_FOR_CHATGPT_AUDIT`，连 `P1ReceiptVerifier` 都过不了
9. **donor/transformation/site 机制只支持 fixture** — 真实反应需走 P1 snapshot/lineage/ledger 管道成为 `TrainView` donors + `StrictTransformation`

---

## 八、推荐接入路径（分两步，先打通最小闭环）

### Step 1（最小单案例闭环，证明链路通）
1. **建真实 P1 snapshot**：从 50 反应选 1 条（如 `real_audit_case_001`, EC 1.1.3.42），建 `build_status=complete` 的 snapshot（可先只用最小的 1 条，验证 atom mapping + lineage 能过）→ 得到 `snapshot_id`/`snapshot_hash`
2. **P2 单 case**：扩展 `build_mini_benchmark.py`（或新 `build_real_mini_benchmark.py`）产出 1 条真实 case 的 `mini_snapshot_manifest` + `truth_records`（RDKit keys）+ `split_manifest` + `case_registry` + `funnel_records` + `fixture_vs_real_evidence_manifest`（全 `evidence_kind=real`）
3. **P2 receipt**：扩展 P2 gate runner 输出 receipt 格式 + 注册 registry
4. **P3 kernel real**：新增公共适配器建 `ProductionAuthorityHandle`，跑 `run_kernel(mode="real")` 产出 1 条 `current_run_artifact.json`
5. **创建 pin**：`p3_p4_interface_pin.json`（status=accepted）
6. **P4 gate 重跑**：G12/G13/G14 从 BLOCKED → PASS（哪怕只 1 条 case，证明链路通）

### Step 2（扩到 50 条）
1. 50 条全部走 P1 snapshot + P2 + P3 + P4
2. 全量 gate + mutations + probes 重跑
3. 提交 kimi Round 9 复审

---

## 九、验证标准

- [ ] `mini_snapshot_manifest.json` 的 `requires_real_audit=True`, `real_case_count ∈ [20, 50]`
- [ ] 每条 real case 有 `audit_record_ids`（≥1）
- [ ] `truth_records.json` 用 RDKit 预计算身份键，无 raw SMILES fallback
- [ ] `fixture_vs_real_evidence_manifest.json` 声明 split/truth/registry/funnel 全 `evidence_kind=real`
- [ ] `current_run_artifact.json` 的 `evidence_kind=real` + `capability_status` 四标志全 true
- [ ] `p3_p4_interface_pin.json` 存在且 `status=accepted`, hash 匹配 manifest
- [ ] P2 receipt：`status=READY_FOR_CHATGPT_P2_AUDIT` + 注册进两个 registry
- [ ] P4 gate：G12/G13/G14 全 PASS, exit 0
- [ ] P4 全量测试 + mutations + probes 无回归

---

## 十、禁止事项

- 不得修改上游合同 / frozen 文件 / P0 ADR / final_design / final_plan
- 不得伪造 real evidence（synthetic 重标 real 属于 P0 违规）
- 不得放宽 gate 判定逻辑来"关闭"
- 不得修改原始 pkl 数据文件（只读加载）
- 不得 commit / push / merge（除非明示授权）

---

## 十一、参考入口（file:line 速查）

| 功能 | P2 worktree | P3 worktree | P4 worktree |
|---|---|---|---|
| P2 构建 | `scripts/build_mini_benchmark.py:84,137` | — | — |
| MiniSnapshot | `reaction_agent/evidence/mini_snapshot.py:58,112,120,150,170` | — | — |
| P2 Gate | `reaction_agent/evaluation/gate.py:201,334,342` | — | — |
| P2 Gate 脚本 | `scripts/run_p2_gate.py:31` | — | — |
| truth schema | `reaction_agent/schemas/evaluation.py:100,142,152` | — | — |
| P3 kernel | — | `reaction_agent/p3/kernel.py:110,214-241,273-287` | — |
| P3 capability | — | `reaction_agent/p3/capability.py:112,176` | — |
| P3 fixtures | — | `reaction_agent/p3/fixtures.py:522,871` | — |
| P3 gate | — | `reaction_agent/p3/gate.py:1267,1318` | — |
| P3 报告 | — | `scripts/generate_p3_reports.py:430` | — |
| P4 consumer | — | — | `reaction_agent/adapters/p3_consumer.py:70,98-154,232,256,330,457,537,582,664` |
| P4 pin | — | — | `reaction_agent/adapters/p3_interface_pin.py:46,111` |
| P4 receipts | — | — | `reaction_agent/authority/receipts.py:66-84,161,241` |
| P4 gate | — | — | `scripts/run_p4_gate.py:702,732,752` |

---

*Generated by Claude（基于 Explore 子代理对 P2/P3/P4 代码的全量探索 + 50 条真实案例清洗）。*