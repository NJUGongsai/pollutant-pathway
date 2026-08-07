# Generalized Lane Report（P8，final_plan §14.6 Post-MVP）

> **状态：PASS** · **Lane：`generalized`** · **Output semantics：`exploratory_non_production`**
> **Branch：** `worktree-p8-generalized-lane` · **Issued：** 2026-08-07
> 本报告对应 final_plan §14.6 Post-MVP 第 1 项 `generalized_lane_report.md`，是 P8 generalized lane 的**阶段总报告**，汇总 Stage A（T1/T2）+ Stage B（T3/T4）落盘证据。**只读复用已有实测产物，不新增代码、不改测试、不动 frozen 产物。**

---

## 0. 结论（结论先行）

| 维度 | 结果 | 可复核证据 |
|---|---|---|
| Relaxation policy 版本化 | ✅ frozen + semver + content_hash + tamper-detect | `relaxation_policy_p8-generalized-relaxation_v1.0.0.json` + `tests/p8/test_policy.py` |
| strict 未污染 | ✅ 物理隔离 + 结构独立 + 无 strict masquerade | `P8_STAGE_A_REPORT.md` + `tests/p8/` 隔离/反伪装测试簇 |
| 独立 rank/abstain | ✅ lane-only + 不信嵌入 status + 独立输出类型 + 受控 abstain | `tests/p8/test_rank.py`（24 tests） |
| Stage B 实测指标 | ✅ 6 类指标全齐 + 全部从 registered policy 派生 | `p8_stage_b_benchmark.json` + `tests/p8/test_benchmark.py` |
| 报告可复现性 | ✅ committed report 钉 frozen artifact + deterministic 生成 | `tests/p8/test_benchmark_report_generation.py` |
| 测试全绿 | ✅ `tests/p8/` = **87 passed**（0.14s） | §8 测试矩阵 + 本 issue 评论贴 pytest 实测输出 |

**铁律遵守：** 无新增代码、无测试改动、无 frozen 产物修改、无 commit/push/merge（工作区保持未提交）。

---

## 1. 范围与定位

- **报告归属：** final_plan §14.6 Post-MVP 第 1 项 `generalized_lane_report.md`。
- **lane 性质：** `generalized`，输出语义 `exploratory_non_production` —— 本 lane 的结果**不是生产决策**，只量化 generalized（放松结构）lane 在 strict baseline 之外额外带来了什么。
- **物理隔离：** 与 strict 通道（P5 gate / P7 three-way eval）结构独立，不共享报告骨架、不共享输出类型、不共享 metrics 结构。
- **设计出处：** T1→final_plan §11.2、T2→§11.3、T3 rank/abstain→§11.4（final_design §18.1 / §19.2）、T4 benchmark→§11.5。

---

## 2. 交付物与证据来源

| 产物 | 路径（相对 `demov2/`） | 角色 |
|---|---|---|
| Frozen relaxation policy | `reports/p8/relaxation_policy_p8-generalized-relaxation_v1.0.0.json` | T1 frozen artifact |
| Stage B benchmark 数据 | `reports/p8/p8_stage_b_benchmark.json` | T4 实测指标来源 |
| Stage A 报告 | `reports/p8/P8_STAGE_A_REPORT.md` | T1/T2 + Round 2 remediation 证据 |
| Stage B benchmark 报告 | `reports/p8/P8_STAGE_B_BENCHMARK_REPORT.md` | T4 指标 human-readable 视图 |
| 本报告（总报告） | `reports/p8/generalized_lane_report.md` | §14.6 Post-MVP 阶段落盘 |
| 源码 | `reaction_agent/p8/{policy,schemas,rank,benchmark,__init__}.py` | T1–T4 实现 |
| 测试 | `tests/p8/test_{policy,generalized_hypothesis,rank,benchmark,benchmark_report_generation}.py` | 可复核证据 |

---

## 3. Relaxation policy 版本化（T1，final_plan §11.2）

Frozen artifact `relaxation_policy_p8-generalized-relaxation_v1.0.0.json` 的 pin 字段：

| 字段 | 实测值 | 含义 |
|---|---|---|
| `policy_id` | `p8-generalized-relaxation` | 策略身份 |
| `version` | `1.0.0` | semver，内容变更必须 bump |
| `content_hash` | `540b875f8508d3578319199fcd2ef63a9d92260651329cbed7cc0888b865e7b3` | SHA-256 over canonical body，load 时复验，篡改→`ValidationError` |

**版本化机制（可复核）：**

- **Frozen + tamper-detect：** `RelaxationPolicy` 是 `frozen=True` StrictModel；`content_hash` 在 load 时复验 → `tests/p8/test_policy.py::test_policy_is_immutable_frozen` / `::test_content_hash_detects_tamper` / `::test_load_detects_tamper`。
- **semver 强制：** `version` 必须是 semver → `::test_version_must_be_semver`。
- **Round-trip 一致：** save/load 不破坏 frozen 性质 → `::test_save_load_roundtrip`。

**Registered vocabulary（D6，无 free-text relaxation）：** 3 条 typed `RelaxationRule`，每条带 `rule_id` / `description` / `applies_to[]` / `distance_weight`（严格 `> 0`）：

| `rule_id` | `applies_to` | `distance_weight` |
|---|---|---:|
| `relax_donor_site_precision` | `donor_site_definite` | 0.3 |
| `relax_precondition_completeness` | `preconditions_complete` | 0.5 |
| `relax_ambiguity_margin` | `no_critical_ambiguity` | 0.2 |

- 唯一性 → `::test_duplicate_rule_id_rejected`；`distance_weight > 0` → `::test_zero_distance_weight_rejected`；relaxable 与 forbidden 精确划分且不相交 → `::test_vocabulary_partition_is_exhaustive_and_disjoint`。

**Forbidden hard constraints（final_design §12.2，永不放松）：**

| `forbidden_hard_constraints` |
|---|
| `changed_heavy_atom_conservation` |
| `graph_edit_replayable` |
| `trusted_mapped_lineage` |

- 不可放松 → `::test_cannot_relax_forbidden_hard_constraint` / `::test_forbidden_hard_constraints_frozen_on_policy`。

**OOD boundary（fail-closed）：** 声明一个 generalized hypothesis 若引用 registered vocabulary 之外的 relaxation 即为 OOD，行为是 `reject`（`boundary: outside_registered_vocabulary`）→ `::test_ood_declared` / `::test_is_ood_flags_unknown_relaxation`。

**Version pinning：** hypothesis 钉 `policy_id + version`；任何内容变更 bump `version` 并产生新 `content_hash`（见 §4 的 anti-masquerade 链）。

---

## 4. strict 未污染（strict untouched）—— 可复核证据

「strict 未污染」从**三个独立层面**给出可复核证据，每一层都有具体测试名或报告原文支撑，不靠断言。

### 4.1 物理层：只增不改

`P8_STAGE_A_REPORT.md` 原文（§Scope）：

> strict untouched: only NEW files under `reaction_agent/p8/`, `tests/p8/`, `reports/p8/` were added; no existing file was modified.

即 P8 全部产物落在**新目录** `reaction_agent/p8/`、`tests/p8/`、`reports/p8/`，未触碰任何既有文件。Stage A 全套回归 1918 passed，唯一 1 个 pre-existing failure（`tests/p1/test_p1_gate_contract.py::test_zero_skip_xfail_in_full_suite`）是 P1 quarantine 导致的 fail-closed，与 P8 无关（详见 Stage A 报告 §Test results）。

### 4.2 结构层：不共享 strict 报告骨架

`tests/p8/test_benchmark.py` 顶部 acceptance pin（§11.5）原文：

> separate report: the benchmark report is written to `reports/p8/` and does NOT reuse the strict report structure (P5 gate / P7 three-way eval).

`P8_STAGE_B_BENCHMARK_REPORT.md` 末尾原文：

> This report is structurally independent of the strict P5 gate report and the P7 three-way evaluation; it covers only the generalized exploratory lane.

验证测试：`::test_metrics_not_strict_p7_metrics`（断言 P8 metrics 不是 strict P7 three-way metrics 结构）/ `::test_report_has_generalized_lane_semantics`。

### 4.3 运行时层：无 strict masquerade（runtime pin）

rank 输出类型**不是** strict 的 `Candidate` / `PredictionResult` / `Abstention`，`lane` Literal-pinned 到 `generalized`。验证测试簇（`tests/p8/test_rank.py` + `tests/p8/test_generalized_hypothesis.py`）：

| 测试 | 证明的隔离点 |
|---|---|
| `test_rank_entry_is_not_a_strict_candidate` | rank entry ≠ strict `Candidate` |
| `test_rank_entry_rejects_strict_candidate_fields` | `extra="forbid"`：strict `Candidate` 的 `ranking_score` 无法塞入 |
| `test_rank_result_is_not_strict_prediction_result` | rank result 不含 strict `PredictionResult` 的 `run_id`/`normalized_query`/`snapshot_id`/`decision` |
| `test_abstention_is_not_strict_abstention` | generalized abstention 不带 strict `Abstention` 的 `stage` 字段 |
| `test_rejects_strict_lane_input` | 输入侧也隔离：strict `Candidate`（`lane=strict`）被拒收 |
| `test_cannot_put_generalized_output_in_strict_lane` | generalized hypothesis 不能放进 `lane="strict"` |
| `test_empty_failed_strict_conditions_rejected` | D5 anti-masquerade：无 failed strict condition 即为 strict 伪装，构造+校验双拒 |
| `test_lane_is_generalized` / `test_arbitrary_lane_rejected` | `lane` 是 Literal，不能任意取值 |

> 上述测试名均可在 `tests/p8/test_rank.py` 与 `tests/p8/test_generalized_hypothesis.py` 中 `grep` 复核；§8 给出实测通过计数。

---

## 5. 独立 rank/abstain（T3，final_plan §11.4 / final_design §18.1 / §19.2）

`reaction_agent/p8/rank.py` 实现 `rank_generalized`，满足 Stage B acceptance pins（`tests/p8/test_rank.py` 顶部原文）：

| Pin | 实测证据（测试名） |
|---|---|
| **lane-only ranking**：只排 generalized hypothesis，绝不与 strict candidate 的 raw score 跨 lane 比较 | `test_rejects_strict_lane_input`（输入侧拒 strict）/ `test_score_is_function_of_distance_only`（score 仅由 distance 决定，无跨 lane raw score） |
| **consumption gate**：ranker 必须重跑 `validate_generalized_hypothesis`，**不得信任**嵌入的 `validation.status` / `checks` | `test_does_not_trust_embedded_status_lie_distance` / `::test_does_not_trust_embedded_status_lie_ood` / `::test_does_not_trust_embedded_status_lie_version_pin`（三组 anti-lie：嵌入伪造的 distance/OOD/version pin 都被重跑识破） |
| **exploratory output semantics**：每个输出钉 `exploratory_non_production`（Gate P8 "user semantics clear"） | `test_rank_entry_exploratory_is_pinned_true` / `test_rank_result_lane_and_semantics_pinned` |
| **no strict masquerade runtime pin** | §4.3 测试簇（`test_rank_entry_lane_is_literal_generalized` 等） |
| **abstain path**：空/全拒输入 → typed abstention + 受控词汇 reason code | `test_abstention_reason_code_is_controlled_vocab` / `test_empty_input_abstains_no_hypotheses` / `test_all_rejected_abstains_no_validated_hypotheses` / `test_all_beyond_max_distance_abstains_with_max_distance_reason` / `test_empty_ranked_requires_abstention` |

**打分与排序（独立于 strict）：**

- score = f(generalization_distance) only → `test_score_is_function_of_distance_only`。
- score 对 distance **严格单调递减** → `test_score_is_strictly_monotonic_decreasing_in_distance`。
- 按 score 降序排列 → `test_ranks_in_score_desc_order`；等距 deterministic tiebreak → `test_deterministic_tiebreak_on_equal_distance`。
- 混合 valid/rejected 只排 valid → `test_mixed_valid_and_rejected_only_ranks_valid`。
- exploratory lane 不能被关闭 → `test_exploratory_cannot_be_turned_off`。

---

## 6. Stage B 实测指标（T4，final_plan §11.5）

数据源：`reports/p8/p8_stage_b_benchmark.json`。**全部从 registered policy 派生（无 free text）**，OOD + distance 由 policy 重新计算。

### 6.1 Population

| 项 | 值 |
|---|---:|
| `n_hypotheses` | 5 |
| `n_predictions` | 5 |
| `n_truth`（held-out） | 4 |
| `n_strict_baseline` | 1 |

### 6.2 六类指标（JSON 字段 → 实测值 → 验证测试）

| 指标 | JSON 字段 | 实测值 | 验证测试（`tests/p8/test_benchmark.py`） |
|---|---|---|---|
| Incremental recall | `metrics.incremental_recall` | `1.0` | `test_recovers_part_of_what_strict_missed` / `test_zero_when_strict_already_complete` / `test_full_recall_of_missed` |
| False additions | `metrics.false_additions` | `2` | `test_counts_predictions_not_in_truth` |
| False addition rate | `metrics.false_addition_rate` | `0.4` | `test_zero_false_additions_when_all_in_truth` / `test_risk_is_false_addition_rate` |
| Coverage | `metrics.coverage` | `1.0` | `test_coverage_includes_strict_and_generalized` |
| Risk | `metrics.risk` | `0.4` | `test_risk_is_false_addition_rate` |
| Risk @ 90% coverage | `metrics.risk_at_90pct_coverage` | `0.25` | `test_risk_at_90pct_coverage_present` |
| OOD ratio | `metrics.ood_ratio` | `0.2` | `test_ood_ratio_counts_ood_predictions` / `test_ood_ratio_zero_when_all_in_vocab` |
| OOD count | `metrics.ood_count` | `1` | 同上 |
| Cost — provider calls | `metrics.cost.provider_calls` | `24` | `test_cost_carried_through` |
| Cost — token count | `metrics.cost.token_count` | `8200` | `test_cost_carried_through` |
| Cost — wall clock | `metrics.cost.wall_clock_seconds` | `52.3` | `test_cost_carried_through` |

### 6.3 Risk–coverage curve（`metrics.risk_coverage_curve`，coverage 单调非递减）

| k | coverage | risk |
|---|---|---|
| 1 | 0.5000 | 0.0000 |
| 2 | 0.7500 | 0.0000 |
| 3 | 0.7500 | 0.3333 |
| 4 | 1.0000 | 0.2500 |
| 5 | 1.0000 | 0.4000 |

- 验证：`test_risk_coverage_curve_present_and_monotonic_coverage`（presence + coverage 单调）。
- 语义：risk 是每个 k 处的 false-addition rate，**不要求 risk 单调**；coverage 单调非递减（0.5→0.75→0.75→1.0→1.0）。

### 6.4 Distance buckets（`metrics.distance_buckets`，按 `generalization_distance`）

| Bucket | 区间 | count | correct | incorrect |
|---|---|---:|---:|---:|
| `0.0-0.2` | [0.0, 0.2) | 0 | 0 | 0 |
| `0.2-0.5` | [0.2, 0.5) | 4 | 3 | 1 |
| `0.5-1.0` | [0.5, 1.0) | 1 | 0 | 1 |
| `1.0+` | [1.0, +∞) | 0 | 0 | 0 |

- 验证：`test_bucket_edges_are_registered_and_ordered`（edges 来自 registered policy，有序）/ `test_buckets_partition_population`（分桶划分总体）/ `test_bucket_assigns_distance_correctly`（按 distance 正确分桶）。
- 一致性：4 个分桶 count 之和 = 5 = `n_predictions` ✓；`distance_weight > 0`（§3）保证分桶良定义。

### 6.5 OOD 语义

`ood_count = 1`、`ood_ratio = 0.2`：5 条 prediction 中有 1 条引用了 registered vocabulary 之外的 relaxation，按 policy `behavior: reject` fail-closed 拒绝（§3 OOD boundary）。验证见 §6.2 OOD 行。

---

## 7. 报告可复现性（T4 Round 2，SB-R1-01 / SB-R1-02）

`tests/p8/test_benchmark_report_generation.py`（6 tests）钉死 committed benchmark report 的可复现性：

| 测试 | 钉的 Round 1 finding |
|---|---|
| `test_committed_report_hash_matches_frozen_artifact` | SB-R1-01：committed report 的 `policy.content_hash` 必须等于 **frozen artifact** 加载后的 hash，不是内存 twin |
| `test_committed_report_policy_id_and_version_match` | policy_id + version 与 frozen artifact 一致 |
| `test_generator_loads_frozen_artifact_not_twin` | 生成器加载 frozen artifact，不构造内存 twin |
| `test_generator_reproduces_committed_json` | 确定性重新生成 → 与 committed JSON 字节级一致 |
| `test_generator_reproduces_committed_md` | 同上，对 committed MD |
| `test_generator_is_deterministic_across_runs` | 多次运行结果一致 |

即：committed `p8_stage_b_benchmark.json` / `P8_STAGE_B_BENCHMARK_REPORT.md` 由 `reaction_agent/p8/benchmark.py::generate_stage_b_demo_report` 从 frozen policy artifact 确定性生成，任何人重跑可复现。

---

## 8. 测试矩阵（实测）

`tests/p8/` 实测：**87 passed in 0.14s**（本 issue 评论贴完整 pytest 输出）。

| 测试文件 | 设计出处 | 测试数 |
|---|---|---:|
| `tests/p8/test_policy.py` | T1 §11.2 | 16 |
| `tests/p8/test_generalized_hypothesis.py` | T2 §11.3 | 22 |
| `tests/p8/test_rank.py` | T3 §11.4 | 24 |
| `tests/p8/test_benchmark.py` | T4 §11.5 | 19 |
| `tests/p8/test_benchmark_report_generation.py` | T4 Round 2 SB-R1-01/02 | 6 |
| **合计** | | **87** |

> Stage A 时点为 38 passed（16 T1 + 22 T2，见 `P8_STAGE_A_REPORT.md`）；Stage B 增补 T3 rank（24）+ T4 benchmark（19）+ T4 报告生成（6）= 49，总计 87，与实测一致。

---

## 9. 复核方法

```bash
# 进入 worktree
cd /Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p8-generalized-lane/CC/branch/ReactionAgent/demov2

# P8 测试（本报告引用的实测）
python -m pytest tests/p8/ -q

# 验证 frozen policy artifact 完整性
python -c "from reaction_agent.p8.policy import load_policy; p=load_policy('reports/p8/relaxation_policy_p8-generalized-relaxation_v1.0.0.json'); print(p.policy_id, p.version, p.content_hash)"

# 确认报告生成确定性（复现 committed artifacts）
python -m pytest tests/p8/test_benchmark_report_generation.py -q
```

---

## 10. 铁律遵守声明

- ✅ 只写报告（本文件），未新增代码、未改测试、未改 frozen 产物（P0 ADR / final_design / final_plan / 上游合同）。
- ✅ 未 commit、未 push、未 merge（工作区保持未提交状态）。
- ✅ 全部数字引用已有实测证据：JSON 字段路径 + benchmark JSON 实测值 + 测试名 + 测试计数。
- ✅ 「strict 未污染」给出三层可复核证据（§4.1 物理层 / §4.2 结构层 / §4.3 运行时层），每条对应测试名或报告原文。
- ✅ 写完后跑 `pytest tests/p8` 保持全绿，实测输出见本 issue 评论。
- ✅ 未伪造任何 PASS / 证据 / 审计结果。
