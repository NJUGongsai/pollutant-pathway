# §12.1 AgentProposedHypothesis 落盘报告

> 父任务：HID-32（P9 全案）。本报告补 final_plan §12.1 的落盘文档，不新增实现。
> 数据源：`reaction_agent/p9/agent_proposed/`（`schemas.py` / `policy.py` / `report.py`）+ `tests/p9/test_agent_proposed_chain.py`（**38 tests**）。
> 边界铁律：agent_proposed 是物理隔离的探索性 **NON-production** lane，只 ADD 新文件，绝不 import / modify strict channel（P3-P6）、P7、P8。

## 1. 概述

agent_proposed lane 让 agent 能在 strict channel 之外提出**假设性候选**（bond cleavage / attribute change），但这些候选永远不能冒充 strict `Candidate`、永远不进 production ranking。一条 `AgentProposedHypothesis`（消费 §19.2 locked schema，字段集不变）必须通过**完整八步 validation chain** 才能产出 lane-pinned 的 `AgentProposedCandidate`；消费侧再跑一次 chain（`revalidate_agent_proposed_candidate`），**绝不信任内嵌的 validation 记录**。

实现锚点（final_plan §12.1 / final_design §19.2 / ADR-0002）：
- `reaction_agent/p9/agent_proposed/schemas.py:1`（schema + 八步 chain + builder + consumption gate）
- `reaction_agent/p9/agent_proposed/policy.py:1`（frozen chain policy + content hash）
- `reaction_agent/p9/agent_proposed/report.py:1`（六指标独立报告）

## 2. AgentProposedHypothesis schema + validation chain

### 2.1 消费的 locked schema（不重写）

`AgentProposedHypothesis` 直接从 `reaction_agent.schemas.hypothesis` 导入（`schemas.py:37-43`），字段集即 §19.2 frozen 集：`hypothesis_id`、`hypothesis_origin="agent_proposed"`、`support_reaction_ids`、`support_lineage_ids`、`transformation_family_id`、`typed_target_atom_or_bond_set`（`AtomTarget` / `BondTarget`）、`relaxation_policy_id`、`allowed_relaxation_ids`、`rationale_summary`、`policy_version`。lane 不重定义、不放松 strict schema。

### 2.2 八步 validation chain（frozen 顺序）

`policy.py:27-36` 把 chain 顺序冻死：

| Step | 名称 | 失败异常类型 | 证据测试 |
|---|---|---|---|
| 1 | `support_validation` | `UnknownReferenceError` | `test_step1_rejects_unknown_support_reaction_id` / `..._lineage_id` |
| 2 | `registered_vocabulary` | `UnknownReferenceError` | `test_step2_rejects_unknown_transformation_family_id` / `..._unregistered_relaxation_id` |
| 3 | `compiler` | `AgentProposedValidationError` | `test_compile_targets_deterministic_and_order_invariant` / `..._rejects_empty_set` |
| 4 | `site_validation` | `UnknownReferenceError` | `test_step4_rejects_atom_target_not_in_query` / `..._bond_target...` |
| 5 | `graph_edit` | `AgentProposedValidationError` | `test_step5_applies_bond_deletion_and_produces_fragments` / `..._missing_query_molecule_context` |
| 6 | `molecule_validation` | `AgentProposedValidationError` | `test_step6_rejects_broken_valence` / `..._heavy_atom_gain` |
| 7 | `dual_ledger_validation` | `UnknownReferenceError` / `AgentProposedValidationError` | `test_step7_accepts_clean_agent_scoped_ledger` / `..._lane_contamination...` / `..._unknown_source_ledger_id` |
| 8 | `grounding_validation` | `AgentProposedValidationError` | `test_step8_rejects_ungrounded_family` / `..._family_not_grounded_by_cited_support` |

错误分类（`schemas.py:65-72`）镜像 P8 R1-05：reference 违规用 `UnknownReferenceError`，非 reference 违规用 `AgentProposedValidationError`（`ContractViolation` 子类）。reject 词汇是受控枚举 `AgentProposedRejectReasonCode`（`schemas.py:80-90`，8 个 code 一一对应 chain step，无 free text）。

### 2.3 Step 3 compiler：确定性 + order-invariant

`compile_typed_targets`（`schemas.py:261-290`）把 typed target set 编译成 `CompiledGraphEdit`：atom targets → sorted atom IDs（attribute-change sites，无移除），bond targets → sorted `(min, max)` endpoint pairs。`compile_hash = canonical_hash(body)`，对输入顺序不变 —— 同一 target set 永远编出同一 hash（可复现）。空 target set 在 compiler 步直接 fail（schema 也强制非空）。
证据：`test_compile_targets_deterministic_and_order_invariant`（`tests/p9/test_agent_proposed_chain.py:183`）断言两种输入顺序产出同一 `compile_hash`。

### 2.4 Step 5/6：graph edit + molecule validation

`apply_graph_edit`（`schemas.py:324-385`）直接用 RDKit（不经 P3 kernel，物理隔离）：bond targets → bond **deletions**（`RWMol.RemoveBond`），atom targets → attribute-change sites（仅记录，不结构移除）。`EditedMolecule` 记录 `heavy_atom_count_before/after` + `sanitized`。`validate_molecule`（`schemas.py:393-405`）强制 sanitization 通过 + 重原子守恒（agent-proposed edit 改键/属性，绝不增删重原子）。
证据：`test_step5_applies_bond_deletion_and_produces_fragments` 断言 `sanitized is True` 且 `heavy_atom_count_before == after`；`test_step6_rejects_broken_valence`（五价碳）+ `test_step6_rejects_heavy_atom_gain`（CCO→CCCO）断言两路 fail-closed。

### 2.5 Step 7：dual-ledger validation（MANDATORY，无静默跳过）

`validate_dual_ledger`（`schemas.py:466-494`）：lane non-contamination（`underlying.candidate_id` 不能是 strict candidate id）+ existence（`source_ledger_id` 必须在 context 注册）。当 context 未提供 scoped ledger（builder 正常路径，新候选的 ledger 无法预注册）时，`_synthesize_agent_lane_ledger`（`schemas.py:413-463`）从 cited support reaction 的 source ledger 合成一个 agent-lane ledger —— **chain 必跑 step 7**，`dual_ledger_validation` 这个 check 是真实 attestation 而非虚假声明。

### 2.6 Step 8：grounding validation

`validate_grounding`（`schemas.py:502-522`）：fail-closed —— family 必须在 `family_grounding` 有证据，且至少一个 cited support reaction 出现在该 grounding set 内。

## 3. Lane-pinned 输出（NOT strict Candidate）

`AgentProposedCandidate`（`schemas.py:160-183`）用 Literal 把 `lane="agent_proposed"`、`output_semantics="exploratory_non_production"`、`exploratory=True` 全部钉死。产品 SMILES 落在 `edited_product_smiles`（**不是** `canonical_product`），且**没有** `ranking_score` / `run_id` / `decision` 字段 —— 与 strict `Candidate` 结构互斥。
证据：`test_candidate_is_structurally_distinct_from_strict_candidate`（`tests/p9/test_agent_proposed_chain.py:410`）断言 `Candidate.model_validate(cand.model_dump())` 抛 `ValidationError`。

`AgentProposedValidation`（`schemas.py:139-152`）lane 钉死 `"agent_proposed"`、status 钉死 `"validated"`，并带 `chain_policy_content_hash` —— 消费者必须凭指纹匹配，不信裸 status。

## 4. Consumption gate（re-run，永不信任内嵌记录）

`revalidate_agent_proposed_candidate`（`schemas.py:647-700`）：
- **lane guard**：拒绝任何 lane ≠ `"agent_proposed"` 的输入（strict `Candidate` 被拒，防 cross-lane raw-score 混入 / strict 冒充）。证据：`test_lane_mixing_strict_candidate_rejected_by_agent_proposed_consumer`。
- **re-run**：从 `compiled_graph_edit` 重建 typed targets → 重建 hypothesis → 重跑全 chain。**内嵌 `validation.status` / `checks` 永不被信任**。
- **lie detection**：重算的 `edited_product_smiles` 必须与存储值一致 —— 篡改 SMILES 但保留 "validated" 记录的候选在此被抓。证据：`test_consumption_gate_reruns_chain_and_catches_lying_candidate`。

## 5. 六指标独立报告（lane-pinned，NOT production rank）

`AgentProposedReport`（`report.py:56-90`）lane 钉死、`output_semantics="exploratory_non_production"`、`exploratory=True`，无 `run_id`/`status`/`decision`/`snapshot_id` —— 与 strict `PredictionResult` 结构互斥。`build_agent_proposed_report`（`report.py:98-169`）产出六组指标：

| 指标组 | 字段 | 计算口径 | 关键证据测试 |
|---|---|---|---|
| 1 new valid/correct/incorrect | `new_valid` / `new_correct` / `new_incorrect` | valid=通过 chain 的候选数；correct/incorrect 仅对**有 GT 标签**的候选打分（R1-02） | `test_report_six_metric_groups_complete` / `test_new_incorrect_excludes_candidates_without_ground_truth` |
| 2 reject reasons | `reject_reasons: dict[str,int]` | 受控枚举 code 计数，无 free text | `test_report_reject_reasons_tallied_by_code` |
| 3 incremental recall | `incremental_recall: float \| None` | `(production_valid + new_correct) / ground_truth_total`，truth-set 分母；未提供 → `None` | `test_report_incremental_recall_and_risk_computed` / `test_incremental_recall_none_when_ground_truth_total_not_provided` |
| 4 risk | `risk: float` | `new_incorrect / (new_correct + new_incorrect)`，固定 coverage；分母 0 → 0.0 | 同上 |
| 5 cost | `cost: AgentProposedCostReport` | mock provider（`llm_calls`/`tool_calls`/`latency_ms`），绝不烧真实 API | `test_report_six_metric_groups_complete` |
| 6 reproducibility | `reproducibility: AgentProposedReproducibility` | **REQUIRED** 输入（`repeated_run_agreement` + `seed` + `chain_policy_version`），无默认 1.0 | `test_reproducibility_required_no_default_fabrication` |

可复现性另有端到端断言：`test_reproducibility_same_input_same_compile_hash_and_smiles`（同输入 → 同 `compile_hash` + 同 `edited_product_smiles` + 同 `chain_policy_content_hash`）。

## 6. Frozen chain policy（content-hashed）

`AgentProposedChainPolicy`（`policy.py:58-107`）：`policy_id` 稳定逻辑身份、`version` 严格 semver `X.Y.Z`、`chain_steps` 顺序冻死（重排/扩展 = 不同 policy，必须 bump version）。`content_hash` 指纹精确 chain artifact，`model_validator` 重算校验，tamper 即抛 `ValidationError`。`create()` 工厂计算 hash；`DEFAULT_AGENT_PROPOSED_CHAIN_POLICY = create(version="1.0.0")`。
证据：`test_chain_policy_default_has_eight_steps_and_semver` + `test_chain_policy_content_hash_is_verified`（重建复现同一 hash；tampered hash 抛错）。

## 7. Round 2 整改（kimi Round-1 audit P9B-R1-01..05）

| Finding | 优先级 | 整改 | 证据测试 |
|---|---|---|---|
| R1-01 | P0 | step 7 dual-ledger MANDATORY：未提供 scoped ledger 时 chain 从 cited support reaction 合成 agent-lane ledger 并跑 `validate_dual_ledger`；cited reaction 无 source ledger 时 fail-closed；不存在"跳过 step 7 仍发 validated candidate"的路径 | `test_step7_chain_synthesizes_ledger_when_none_supplied_and_runs_validate` / `test_step7_chain_fails_when_cited_reaction_has_no_source_ledger` / `test_step7_chain_propagates_contamination_failure` / `test_step7_no_false_attestation_when_skipped_is_impossible` |
| R1-02 | P1 | `new_incorrect` 仅计**有 GT 且不匹配**的候选；无 GT 候选既非 correct 也非 incorrect（仍计 `new_valid`） | `test_new_incorrect_excludes_candidates_without_ground_truth` |
| R1-03 | P1 | atom-target-only hypothesis 在 graph_edit 步拒绝（attribute-change 词表未实现，防 identity edit 冒充 new_valid） | `test_atom_target_only_hypothesis_rejected_at_graph_edit` / `test_identity_edit_not_emitted_as_new_valid` |
| R1-04 | P2 | `incremental_recall` 用 truth-set 分母；未提供 `ground_truth_total` → `None`，绝不伪造数字 | `test_incremental_recall_none_when_ground_truth_total_not_provided` |
| R1-05 | P2 | reproducibility 是 REQUIRED 输入，无默认 1.0 / seed=0 伪造 | `test_reproducibility_required_no_default_fabrication` |

## 8. 实测证据汇总

| 证据来源 | 路径 | 测试数 |
|---|---|---|
| chain + report 全链路 | `tests/p9/test_agent_proposed_chain.py` | **38** |

按行为分类的关键断言（全部位于 `tests/p9/test_agent_proposed_chain.py`）：

- **frozen policy**：`test_chain_policy_default_has_eight_steps_and_semver:155`、`test_chain_policy_content_hash_is_verified:163`
- **compiler 确定性**：`test_compile_targets_deterministic_and_order_invariant:183`、`test_compile_targets_rejects_empty_set:196`
- **step 1-2 reference fail-closed**：`test_step1_rejects_unknown_support_reaction_id:206`、`test_step2_rejects_unregistered_relaxation_id:231`（ADR-0002：free-text relaxation 被拒）
- **step 4 site 归属**：`test_step4_rejects_atom_target_not_in_query:245`、`test_step4_rejects_bond_target_not_in_query:255`
- **step 5/6 chemistry**：`test_step5_applies_bond_deletion_and_produces_fragments:279`、`test_step6_rejects_broken_valence:294`、`test_step6_rejects_heavy_atom_gain:307`
- **step 7 dual-ledger**：`test_step7_rejects_lane_contamination_with_strict_candidate_id:336`、`test_step7_accepts_clean_agent_scoped_ledger:357`
- **step 8 grounding**：`test_step8_rejects_ungrounded_family:375`、`test_step8_rejects_family_not_grounded_by_cited_support:382`
- **full chain happy path**：`test_full_chain_happy_path_emits_lane_pinned_candidate:396`（8 checks 在 chain 通过后烧入）、`test_builder_burns_checks_only_after_chain_passes:419`
- **consumption gate**：`test_consumption_gate_reruns_chain_and_catches_lying_candidate:435`、`test_consumption_gate_accepts_honest_candidate:450`、`test_lane_mixing_strict_candidate_rejected_by_agent_proposed_consumer:460`
- **六指标报告**：`test_report_six_metric_groups_complete:478`、`test_report_reject_reasons_tallied_by_code:506`、`test_report_incremental_recall_and_risk_computed:526`、`test_reproducibility_same_input_same_compile_hash_and_smiles:554`
- **R1-01..05 整改**：`test_step7_chain_synthesizes_ledger_when_none_supplied_and_runs_validate:576` 等 9 项（见 §7 表）

## 9. 风险与边界

- **物理隔离**：lane 直接用 RDKit，不经 P3 kernel；只 ADD 文件，不 import/modify strict channel（P3-P6）/P7/P8。
- **结构互斥**：`AgentProposedCandidate` / `AgentProposedReport` / `AgentProposedValidation` 三者的 lane Literal 钉死，与 strict `Candidate` / `PredictionResult` 结构互斥，跨 lane 混入被消费 gate 拒绝。
- **fail-closed**：chain 每步、consumption gate、policy hash 校验全 fail-closed；不存在跳过 step 7 仍发 validated candidate 的路径。
- **不伪造**：incremental_recall 未测 → `None`；reproducibility 必填；cost 用 mock provider。

## 10. 结论

agent_proposed lane 的 schema、八步 validation chain、lane-pinned candidate、consumption gate、六指标独立报告均已实现并经 `tests/p9/test_agent_proposed_chain.py`（38 tests）覆盖；Round 2 五项 audit findings（P9B-R1-01..05）全部整改并有对应 RED 测试。lane 物理隔离、结构互斥、fail-closed、不伪造四条铁律由测试直接断言。本报告仅落盘，不新增实现。
