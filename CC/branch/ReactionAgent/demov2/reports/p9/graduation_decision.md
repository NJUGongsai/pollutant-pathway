# §12.2 Graduation 落盘报告

> 父任务：HID-32（P9 全案）。本报告补 final_plan §12.2 的落盘文档，不新增实现。
> 数据源：`reaction_agent/p9/graduation/`（`schemas.py` / `gate.py`）+ `tests/p9/test_graduation.py`（**47 tests**）。
> 边界铁律：graduation 是 evidence-based、NOT declaration-based 的 gate；lane 是 probability-free；只 ADD 新文件，不 modify strict channel（P3-P6）/P7/P8/Phase B agent_proposed lane（只消费其报告口径）/deepseek external 包。

## 1. 概述

graduation gate 是 agent_proposed hypothesis class 进入 production ranking 的**唯一裁决点**。一个 hypothesis class 只有在 `GraduationPackage`（九要素 + version pin）通过 gate 后才能被 `admit_to_production_ranking` 转成 `ProductionRankingAdmission`。**未毕业不进入 production ranking** —— blocked outcome 在 admit 时抛 `GraduationBlockedError`，结构上封死。

实现锚点（final_plan §12.2 / final_design §19.3 / ADR-0002 graduation gate）：
- `reaction_agent/p9/graduation/schemas.py:1`（九要素 package + outcome + admission + thresholds）
- `reaction_agent/p9/graduation/gate.py:1`（evidence-based gate + admission attestation + demo builders）

## 2. 九要素 GraduationPackage（content-hashed，无 self-declared status）

### 2.1 EVIDENCE-BASED, NOT DECLARATION-BASED（ADR-0002 核心）

`GraduationPackage`（`schemas.py:372-477`）**不携带** `status` / `graduated` / `approved` 自声明字段 —— 只装证据。gate（`evaluate_graduation`）是唯一裁决者，重算证据对阈值。证据：`test_graduation_package_has_no_self_declared_status_field`（`tests/p9/test_graduation.py:300`）断言 `status`/`graduated`/`approved`/`is_graduated` 均不在 dump 中。

### 2.2 九要素 + version pin

| # | 组件 | 类型 | 关键约束 | 证据测试 |
|---|---|---|---|---|
| 1 | hypothesis class | `HypothesisClass` | `chain_policy_version` 严格 semver | `test_allowlist_is_frozen_and_content_hashed:163` |
| 2 | allowlist | `HypothesisClassAllowlist` | frozen + content-hashed；未注册 class 不能毕业 | `test_allowlist_is_frozen_and_content_hashed` |
| 3 | held-out results | `HeldOutResults` | §19.3 九指标，probability-free | `test_held_out_results_covers_nine_section_19_3_metrics:217` / `test_held_out_results_has_no_probability_calibration_fields:231` |
| 4 | shift results | `ShiftResults` | family/scaffold shift；`max_recall_drop` | `test_gate_blocks_when_excessive_shift:392` |
| 5 | risk/coverage | `RiskCoverage` | `risk_at_fixed_coverage` + typed `CoveragePoint` 曲线 | `test_coverage_curve_typed_model:788` |
| 6 | grounding | `GroundingRecord` | `grounding_score ∈ [0,1]` | `test_gate_blocks_when_grounding_insufficient:405` |
| 7 | cost | `CostRecord` | mock provider（`llm_calls`/`tool_calls`/`latency_ms`），不烧真实 API | `test_held_out_results_covers_nine_section_19_3_metrics` |
| 8 | ADR | `ADRRecord` | frozen + content-hashed；demo 用 `status="proposed"`（非 accepted = blocker） | `test_adr_is_frozen_and_content_hashed:199` / `test_gate_blocks_when_adr_not_accepted:329` |
| 9 | human approval | `HumanApproval \| None` | `None` → demo BLOCKED；`package_content_hash` 绑定包证据 | `test_gate_blocks_when_human_approval_missing:322` |
| + | version pin | `VersionPin` | policy/model/tool 版本 + `chain_policy_content_hash` 链接 Phase B | `test_graduation_package_has_nine_components_and_content_hash:271` |

`GraduationPackage.content_hash` 由 `model_validator` 重算校验（`schemas.py:394-402`），tamper 即抛 `ValidationError`。证据：`test_graduation_package_content_hash_tamper_detection:287`。

### 2.3 PROBABILITY-FREE LANE（§19.3：没有 probability 时不伪造 calibration）

`HeldOutResults`（`schemas.py:242-264`）钉死 `probability_introduced: Literal[False]`，且**没有** Brier/ECE/calibration 字段（`extra="forbid"` 拒绝）。一个声称 `probability_introduced=True` 的包在构造时被拒。证据：`test_held_out_results_has_no_probability_calibration_fields`（附加 `brier=0.1` 抛 `ValidationError`；`probability_introduced=True` 抛 `ValidationError`）+ `test_no_fake_calibration_when_no_probability:501`。

## 3. Evidence-based gate（唯一裁决者，self-consistent at every consumption point）

`evaluate_graduation`（`gate.py:115-225`）的 self-consistency：

| 审计点 | 行为 | Blocker code | 证据测试 |
|---|---|---|---|
| R1-03 重算 package hash | `canonical_hash(model_dump(exclude=content_hash))`，不信任内嵌；`model_copy` desync → blocked | `content_hash_mismatch` | `test_gate_recomputes_package_hash_desync_blocked:663` |
| R1-03 重算 allowlist hash | 同上 | `allowlist_content_hash_mismatch` | `test_gate_recomputes_allowlist_hash_desync_blocked:674` |
| R1-03 重算 ADR hash | 同上 | `adr_content_hash_mismatch` | `test_gate_recomputes_adr_hash_desync_blocked:683` |
| R1-05 allowlist content match | 按 `class_id` 查找后比**完整内容**（不只 id）；同 id 不同 families/policy version → drift | `class_not_in_allowlist` / `class_content_drift` | `test_gate_blocks_when_class_not_in_allowlist:368` / `test_gate_blocks_class_content_drift:731` |
| held-out metrics | `incremental_recall=None` → unmeasured；`<min` → insufficient；`invented_id_or_structure_mutations≠0` → blocker | `incremental_recall_unmeasured` / `..._insufficient` / `invented_id_or_structure_mutation_nonzero` | `test_gate_blocks_when_incremental_recall_unmeasured:381` / `test_gate_blocks_when_invented_mutation_nonzero:338` |
| R1-04 worst-case dual-copy | `effective_risk = max(held_out.risk, risk_coverage.risk)`；`effective_grounding = min(...)`；`effective_shift_drop = max(...)` | `risk_exceeds_threshold` / `grounding_insufficient` / `excessive_family_scaffold_shift` | `test_gate_blocks_when_risk_exceeds_threshold:347` / `test_gate_blocks_when_grounding_insufficient:405` / `test_gate_blocks_shift_inconsistency_worst_case:714` |
| repeated run agreement | `<min_repeated_run_agreement` → blocker | `repeated_run_agreement_below_threshold` | `test_gate_blocks_when_repeated_run_agreement_low:359` |
| ADR accepted | `status != "accepted"` → blocker | `adr_not_accepted` | `test_gate_blocks_when_adr_not_accepted:329` |
| R1-02 human approval | `None` → missing；`approver_id` 不在 registry → not registered；`package_content_hash != package_evidence_hash(pkg)` → binding mismatch | `missing_human_approval` / `approver_not_registered` / `approval_package_binding_mismatch` | `test_gate_blocks_forged_approver_not_in_registry:622` / `test_gate_blocks_approval_bound_to_wrong_package:638` |

Blockers 用受控枚举 `BlockerReasonCode`（`schemas.py:67-93`，无 free text），dedup 保序。outcome 绑定**重算后**的 package hash（`gate.py:224`），不信内嵌。lane 钉死 `"agent_proposed"`、`output_semantics="graduation_gate"`，无 production rank 字段（`test_gate_outcome_is_lane_pinned_exploratory:429`）。

`package_evidence_hash`（`gate.py:64-74`）：包证据 hash（排除 `content_hash` + `human_approval`），`HumanApproval.package_content_hash` 绑定它 —— 偷来的 approval 无法 replay 到别的包（R1-02）。

## 4. Production ranking admission（结构强制，未毕业封死）

### 4.1 admit 重跑 gate，不信传入 outcome

`admit_to_production_ranking`（`gate.py:258-305`）：**重跑 `evaluate_graduation`**，比对传入 outcome 的 `status` + `package_content_hash`，不匹配抛 `GraduationBlockedError`（R1-01）。blocked package 直接抛错，**不存在**从非毕业包产出 `ProductionRankingAdmission` 的路径。证据：`test_admit_to_production_ranking_rejects_blocked_outcome:445` + `test_admit_reruns_gate_rejects_forged_graduated_outcome:552`（伪造 graduated outcome 给 demo 包 → 拒）+ `test_admit_reruns_gate_rejects_outcome_hash_mismatch:565`。

### 4.2 recomputable attestation

`_attestation`（`gate.py:233-250`）= `canonical_hash({graduated_package_hash, human_approval_id, adr_id, status, blockers_digest})`。任何人可重算（consistency proof，非 MAC）；授权来自 `verify_production_admission` 重跑 gate，不靠 attestation 保密。

### 4.3 verify 拒绝伪造/直接构造的 admission

`verify_production_admission`（`gate.py:308-342`）：重跑 gate + 重派 attestation。直接手构的 `ProductionRankingAdmission`（attestation 伪造）或指向 blocked 包的 admission 都被拒。证据：`test_verify_rejects_directly_constructed_admission:574` + `test_verify_rejects_admission_pointing_at_blocked_package:590` + `test_admission_attestation_is_deterministic_and_recomputable:606`。

### 4.4 结构互斥 strict Candidate

`ProductionRankingAdmission`（`schemas.py:506-525`）lane 钉死、`admitted=True`，无 `canonical_product`/`ranking_score`。证据：`test_production_ranking_admission_structurally_distinct_from_strict_candidate:473` 断言 `Candidate.model_validate(admission.model_dump())` 抛 `ValidationError`。

## 5. Demo terminal state：BLOCKED（无 faked PASS）

`build_demo_graduation_package`（`gate.py:457-476`）构造一个**除 human approval 外全有效**的包（`human_approval=None`）。gate 评估结果是 `blocked` + `missing_human_approval`，admit 抛 `GraduationBlockedError`。**demo 没有真实 human approver，终态就是 BLOCKED，绝不伪造 PASS。** 证据：`test_demo_terminal_state_blocked_without_human_approval:489`。

`DEFAULT_APPROVER_REGISTRY = frozenset({"human_cc"})`（`gate.py:56`）：demo 只校验 membership + package binding，无密码学签名（documented follow-up：approver registry + token derivation）。gate 不信自声 "signed" token。

## 6. Thresholds（可配置，content-pinned）

`GraduationThresholds`（`schemas.py:537-547`）：`max_risk=0.3`、`min_repeated_run_agreement=0.9`、`min_grounding=0.8`、`min_incremental_recall=0.1`、`max_recall_drop=0.2`。可注入 `evaluate_graduation(thresholds=...)`。证据：`test_default_thresholds_are_sensible:515` + `test_gate_respects_custom_thresholds:524`（strict `min_repeated_run_agreement=0.999` 把默认通过的包打成 blocked）。

## 7. Round 2 整改（kimi Phase-C Round-1 findings P9C-R1-01..07）

| Finding | 优先级 | 整改 | 证据测试 |
|---|---|---|---|
| R1-01 | P0 | admit 重跑 gate；admission 带 recomputable attestation；verify 拒直接构造/伪造 admission | `test_admit_reruns_gate_rejects_forged_graduated_outcome:552` / `test_verify_rejects_directly_constructed_admission:574` / `test_admission_attestation_is_deterministic_and_recomputable:606` |
| R1-02 | P1 | human approval：approver registry + package binding（demo scope：presence + binding） | `test_gate_blocks_forged_approver_not_in_registry:622` / `test_gate_blocks_approval_bound_to_wrong_package:638` / `test_default_approver_registry_contains_demo_approver:653` |
| R1-03 | P1 | gate 重算 package/allowlist/ADR content hash，`model_copy` desync → blocked | `test_gate_recomputes_package_hash_desync_blocked:663` / `..._allowlist...:674` / `..._adr...:683` |
| R1-04 | P1 | dual-copy evidence consistency：构造时 validator + 消费时 gate worst-case | `test_package_validator_rejects_inconsistent_shift:698` / `test_package_validator_rejects_inconsistent_cost:707` / `test_gate_blocks_shift_inconsistency_worst_case:714` |
| R1-05 | P1 | allowlist content match（同 id 不同内容 → drift） | `test_gate_blocks_class_content_drift:731` |
| R1-06 | P2 | `added_incorrect` required（无默认 0 伪装成 measured zero） | `test_added_incorrect_required_no_default:752` |
| R1-07 | P2 | hygiene：blockers dedup、coverage_curve typed、ShiftResult.risk ∈ [0,1] | `test_blockers_deduplicated:774` / `test_coverage_curve_typed_model:788` / `test_shift_result_risk_upper_bound:801` / `test_dead_blocker_codes_not_emitted:807` |

## 8. 实测证据汇总

| 证据来源 | 路径 | 测试数 |
|---|---|---|
| graduation package + gate + admission | `tests/p9/test_graduation.py` | **47** |

关键断言分布（全部位于 `tests/p9/test_graduation.py`）：

- **九要素 + content hash**：`test_graduation_package_has_nine_components_and_content_hash:271`、`test_graduation_package_content_hash_tamper_detection:287`、`test_graduation_package_has_no_self_declared_status_field:300`
- **frozen allowlist / ADR**：`test_allowlist_is_frozen_and_content_hashed:163`、`test_adr_is_frozen_and_content_hashed:199`
- **probability-free**：`test_held_out_results_covers_nine_section_19_3_metrics:217`、`test_held_out_results_has_no_probability_calibration_fields:231`、`test_no_fake_calibration_when_no_probability:501`
- **gate graduated/blocked 各路**：`test_gate_returns_graduated_for_complete_package:314`、`test_gate_blocks_when_human_approval_missing:322`、`..._adr_not_accepted:329`、`..._invented_mutation_nonzero:338`、`..._risk_exceeds_threshold:347`、`..._repeated_run_agreement_low:359`、`..._class_not_in_allowlist:368`、`..._incremental_recall_unmeasured:381`、`..._excessive_shift:392`、`..._grounding_insufficient:405`
- **controlled vocabulary + lane-pinned**：`test_gate_blockers_use_controlled_vocabulary:421`、`test_gate_outcome_is_lane_pinned_exploratory:429`
- **admission 结构强制**：`test_admit_to_production_ranking_rejects_blocked_outcome:445`、`test_admit_to_production_ranking_accepts_graduated_outcome:453`、`test_verify_production_admission_accepts_honest_admission:466`、`test_production_ranking_admission_structurally_distinct_from_strict_candidate:473`
- **demo 终态**：`test_demo_terminal_state_blocked_without_human_approval:489`
- **thresholds**：`test_default_thresholds_are_sensible:515`、`test_gate_respects_custom_thresholds:524`
- **R1-01..07 整改**：见 §7 表（`tests/p9/test_graduation.py:552` 起共 16 项）

## 9. 风险与边界

- **未毕业不进 production ranking**：blocked outcome 在 `admit_to_production_ranking` 抛 `GraduationBlockedError`，结构上封死；demo 终态 BLOCKED，绝不伪造 PASS。
- **evidence-based**：package 无自声明 status；gate 重算所有 hash、取 dual-copy worst-case、查 allowlist 完整内容、查 approver registry + binding。
- **probability-free**：`HeldOutResults` 钉死 `probability_introduced=False`，无 Brier/ECE/calibration，不伪造 calibration。
- **结构互斥**：`GraduationOutcome` / `ProductionRankingAdmission` lane Literal 钉死，与 strict `Candidate`/`PredictionResult` 结构互斥。
- **物理隔离**：只 ADD 文件；只消费 Phase B agent_proposed 报告口径；不 modify strict channel / P7 / P8 / external 包。

## 10. 结论

graduation 的九要素 package、evidence-based gate、production ranking admission 结构强制、probability-free lane、demo BLOCKED 终态均已实现并经 `tests/p9/test_graduation.py`（47 tests）覆盖；Round 2 七项 audit findings（P9C-R1-01..07）全部整改并有对应 RED 测试。**未毕业不进入 production ranking** 由 `admit_to_production_ranking` 重跑 gate + `GraduationBlockedError` 结构强制，并由 `test_admit_to_production_ranking_rejects_blocked_outcome` 直接断言。本报告仅落盘，不新增实现。
