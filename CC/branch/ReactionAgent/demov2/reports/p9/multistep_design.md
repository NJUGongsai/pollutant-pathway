# §12.4 Multi-step Candidate Graph 落盘报告

> 父任务：HID-32（P9 全案）。本报告补 final_plan §12.4 的落盘文档，不新增实现。
> 数据源：`reaction_agent/p9/multistep/`（5 个文件）+ `tests/p9/test_multistep_*.py`（2 个测试文件，**36 tests**）。
> 边界铁律：每条 edge 满足 one-step contract（P3 kernel 或 P8 lane 作 validator）；只 ADD 新文件，不 modify strict channel / P7 / P8 / external 包（只消费 `EvidenceCache`）。

## 1. 概述

multi-step candidate graph 是一张有向图：**nodes = canonical molecule SMILES（RDKit 归一化、identity 去重）**，**edges = validated one-step reaction edges（带 contract hash 校验）**。beam search 在图上探索多步路径，受 depth/cost/risk budgets + stop rules 约束；路径带 per-edge lineage（evidence/lane/ledger/contract hash）；path dedup + uncertainty 跟踪；external evidence 必须经 `IngestPipeline.ingest` 入 cache 后才能被 search 消费。

实现锚点（final_plan §12.4 / final_design §22 / Phase D checklist）：

| 模块 | 路径 | 职责 |
|---|---|---|
| schemas | `reaction_agent/p9/multistep/schemas.py:1` | `MultiStepNode` / `MultiStepEdge` / `Step` / `MultiStepPath` / `SearchConfig` / `Budget` / `StopRule` / `PathUncertainty` |
| graph | `reaction_agent/p9/multistep/graph.py:1` | `MultiStepGraph`（add_node / add_edge / has_cycle / get_edge） |
| path | `reaction_agent/p9/multistep/path.py:1` | `canonical_path_signature` / `PathDedup` |
| search | `reaction_agent/p9/multistep/search.py:1` | `MultiStepSearch`（beam search + budgets + stop rules） |
| validator | `reaction_agent/p9/multistep/validator.py:1` | `EdgeValidator` protocol + `EdgeValidationResult` + `MockEdgeValidator` |

## 2. Nodes / Edges / per-edge evidence / dual-ledger / lane

### 2.1 MultiStepNode（canonical molecule，identity 去重）

`MultiStepNode`（`schemas.py:23-50`）：`node_id` content-addressed（`stable_id("msn", canonical_smiles)`，`schemas.py:36-42`）—— 同分子永远映到同 node。`MultiStepGraph.add_node`（`graph.py:45-74`）用 RDKit `MolToSmiles(canonical=True)` 归一化，invalid SMILES 直接抛 `ValueError`（fail-closed，P9D-R1-04）。同 canonical SMILES 幂等（不重复建 node）。
证据：`test_multi_step_node_created`、`test_graph_add_node`、`test_same_canonical_smiles_same_node`（`tests/p9/test_multistep_phase_d.py:104/117/132`）；Round 2 `test_same_molecule_different_smiles_same_node:265`（`CC(=O)OCC` 与 `CCOC(=O)C` 归一化到同 node）、`test_invalid_smiles_rejected:275`、`test_explicit_node_id_overridden_by_canonical:282`。

### 2.2 MultiStepEdge（validated one-step reaction edge）

`MultiStepEdge`（`schemas.py:69-86`）：`edge_id` 唯一；`from_node` / `to_node` = canonical SMILES；`lane` 标记哪条 lane 验证了此 edge；`evidence_ids` / `ledger_ids` 带 evidence + dual-ledger 上下文；`one_step_contract_hash` 是 one-step contract 指纹；`cost ≥ 0`、`risk ∈ [0,1]`。每条 edge 满足 one-step contract。
证据：`test_multi_step_edge_created:110`、`test_edge_carries_evidence:144`、`test_edge_carries_lane:149`、`test_edge_carries_ledger:154`、`test_edge_lane_isolated:159`（不同 lane 的 edge 可在同图共存）。

### 2.3 Step（per-edge lineage）

`Step`（`schemas.py:53-66`）：路径中单次 edge 遍历的完整 lineage —— `edge_id` + `from_node` + `to_node` + `lane` + `evidence_ids` + `ledger_ids` + `one_step_contract_hash`。每条 edge 的 evidence/dual-ledger/lane 都可审计。
证据：`test_path_carries_per_edge_steps:198`（`tests/p9/test_multistep_round2.py`）、`test_search_path_has_lineage:223`（search 产出的路径每步带 full lineage）。

### 2.4 EdgeValidator + contract hash provenance

`EdgeValidator`（`validator.py:23-33`）是 `@runtime_checkable Protocol`：`validate(from_smiles) -> list[EdgeValidationResult]`。`EdgeValidationResult`（`validator.py:40-82`）在 `__post_init__` 计算确定性 `one_step_contract_hash = canonical_hash({contract_version, edge_id, from_node, to_node, lane, sorted evidence_ids, sorted ledger_ids})`（P9D-R1-02），并校验 `cost ≥ 0`、`risk ∈ [0,1]`。`MockEdgeValidator`（`validator.py:85-130`）接受预定义 valid edges，产出 validator-issued hash。
证据：`test_edge_validation_result_emits_contract_hash:137`、`test_mock_validator_emits_contract_hash:150`（同输入 → 同 hash）、`test_edge_validation_result_bounds:314`（cost/risk 越界抛错）。

## 3. MultiStepGraph（add_node / add_edge / cycle detection）

`MultiStepGraph`（`graph.py:31-146`）：
- `add_node`：见 §2.1（RDKit 归一化、幂等、invalid SMILES fail-closed）。
- `add_edge`（`graph.py:76-115`）：**validator 必填**（`validator is None` → `TypeError`，P9D-R2-02 sentinel）；`from_node`/`to_node` 必须已建；调用 `validator.validate` 重算 contract hash 与 edge 的 `one_step_contract_hash` 比对，forged/非 validator-issued hash 拒绝（fail-closed，P9D-R1-02）。
- `has_cycle`（`graph.py:133-140`）：node 序列出现重复即 cycle。
- `get_edge`（`graph.py:117-119`）：按 edge_id 查（lineage query）。
证据：`test_graph_add_edge:124`、`test_cycle_detection:174`、`test_no_cycle_for_linear_path:183`；Round 2 `test_forged_contract_hash_edge_rejected:162`、`test_validator_issued_hash_edge_accepted:173`、`test_add_edge_without_validator_rejected:348`、`test_add_edge_explicit_none_validator_rejected:372`。

## 4. Branch/Beam search + budgets + cycle detection + stop rules

`MultiStepSearch`（`search.py:41-175`）beam search：
- 初始化 beam 为 start node；按 `max_depth` 迭代；每轮从 beam 各 state 调 `validator.validate` 取候选 edges。
- **cycle 检查**：`has_cycle(state.nodes + [result.to_node])` 跳过回环。
- **budget**：`new_cost > budget.max_cost` 或 `new_risk > budget.max_risk` 跳过。
- **beam**：按 `total_cost` 升序取 top `beam_width`。
- **stop rules**：`StopRule.type == "max_paths"` 且路径数达 `value` 即停。
- **external evidence 校验**（P9D-R1-01）：`external_evidence_ids` 必须全部在 `evidence_cache` 中（`has_evidence_id`），un-ingested ID 抛 `ValueError`（"has not been ingested"）。
- 产出 `MultiStepPath`（nodes + edge_ids + steps + total_cost + total_risk），按 `total_cost` 升序返回。

`SearchConfig`（`schemas.py:139-150`）：`beam_width ≥ 1`、`max_depth ≥ 1`、`Budget`（`max_cost`/`max_risk`/`max_paths`）、`stop_rules`。`StopRule`（`schemas.py:128-136`）`type: Literal["max_paths"]` —— 未知 type 构造时即拒（fail-closed，P9D-R1-05）。
证据：`test_beam_search_basic:191`、`test_beam_search_depth_limit:205`、`test_beam_search_budget_respected:220`、`test_stop_rule_max_paths:296`；Round 2 `test_unknown_stop_rule_type_rejected:296`、`test_known_stop_rule_accepted:302`、`test_uningested_evidence_id_rejected_by_search:83`、`test_ingested_evidence_id_accepted_by_search:101`。

## 5. Path deduplication + path uncertainty

`canonical_path_signature`（`path.py:15-25`）= `canonical_hash({nodes, edge_ids})` —— 同 nodes + 同 edges（同序）→ 同签名。`PathDedup`（`path.py:28-68`）：`add` 用签名去重（重复返回 False）；`alternative_paths(target)` 数到同一 target 的不同路径；`uncertainty(target)` 返回 `PathUncertainty`（`schemas.py:153-161`，`alternative_paths ≥ 0`）。中间 node 不计为 target（只 path 终点计）。
证据：`test_path_dedup_same_path:244`、`test_path_dedup_different_paths:263`、`test_path_uncertainty:282`（两条到 MOL_B 的路径 → `alternative_paths(MOL_B)=2`，中间 MOL_C=0）；Round 2 `test_path_uncertainty_wired_through_dedup:330`。

## 6. external evidence 消费约束

search 只接受**已 ingest** 的 evidence ID（经 `IngestPipeline.ingest` 入 `EvidenceCache`）。un-ingested ID fail-closed 拒绝。`EvidenceCache.has_evidence_id`（`external/cache.py:56-58`）是校验钩子。这把 multistep 与 external 模块的 ingestion 闸口焊死，防 placebo intake（P9D-R1-01）。
证据：`test_external_evidence_consumes_via_ingest:318`（`tests/p9/test_multistep_phase_d.py`）—— 完整跑 `IngestPipeline.ingest` 后 evidence ID 才能用；Round 2 `test_uningested_evidence_id_rejected_by_search:83`、`test_ingested_evidence_id_accepted_by_search:101`。

## 7. Round 2 整改（kimi Phase-D Round-1 findings P9D-R1-01..06）

| Finding | 优先级 | 整改 | 证据测试 |
|---|---|---|---|
| P9D-R1-01 | P1 | external evidence intake placebo：search 校验 evidence ID 必须在 cache；un-ingested 拒绝 | `test_uningested_evidence_id_rejected_by_search:83` / `test_ingested_evidence_id_accepted_by_search:101` |
| P9D-R1-02 | P1 | one-step contract provenance：validator 发 contract hash；forged hash edge 拒绝 | `test_edge_validation_result_emits_contract_hash:137` / `test_mock_validator_emits_contract_hash:150` / `test_forged_contract_hash_edge_rejected:162` / `test_validator_issued_hash_edge_accepted:173` |
| P9D-R1-03 | P2 | path lineage：per-edge `Step` 带 full evidence/lane/ledger/contract hash | `test_path_carries_per_edge_steps:198` / `test_search_path_has_lineage:223` |
| P9D-R1-04 | P2 | canonical node normalization：RDKit 归一化、invalid SMILES 拒、explicit node_id 被覆盖 | `test_same_molecule_different_smiles_same_node:265` / `test_invalid_smiles_rejected:275` / `test_explicit_node_id_overridden_by_canonical:282` |
| P9D-R1-05 | P2 | stop rule fail-closed：未知 type 构造时拒 | `test_unknown_stop_rule_type_rejected:296` / `test_known_stop_rule_accepted:302` |
| P9D-R1-06 | P2 | hygiene：cost/risk bounds、uncertainty 经 dedup 暴露 | `test_edge_validation_result_bounds:314` / `test_path_uncertainty_wired_through_dedup:330` |
| P9D-R3-01 sentinel | — | `add_edge` 无 validator 必抛 TypeError（防 validator 被静默改回 optional） | `test_add_edge_without_validator_rejected:348` / `test_add_edge_explicit_none_validator_rejected:372` |

## 8. 实测证据汇总

| 证据来源 | 路径 | 测试数 |
|---|---|---|
| Phase D 基线（nodes/edges/lineage/beam/cycle/dedup/uncertainty/stop/external） | `tests/p9/test_multistep_phase_d.py` | 19 |
| Phase D Round 2 整改（P9D-R1-01..06 + R3-01 sentinel） | `tests/p9/test_multistep_round2.py` | 17 |
| **合计** | | **36** |

关键断言分布：
- **nodes**：`test_multi_step_node_created:104`、`test_graph_add_node:117`、`test_same_canonical_smiles_same_node:132`（phase_d）；`test_same_molecule_different_smiles_same_node:265`、`test_invalid_smiles_rejected:275`、`test_explicit_node_id_overridden_by_canonical:282`（round2）
- **edges + lineage**：`test_multi_step_edge_created:110`、`test_edge_carries_evidence:144`、`test_edge_carries_lane:149`、`test_edge_carries_ledger:154`、`test_edge_lane_isolated:159`（phase_d）；`test_path_carries_per_edge_steps:198`、`test_search_path_has_lineage:223`（round2）
- **contract hash**：`test_edge_validation_result_emits_contract_hash:137`、`test_mock_validator_emits_contract_hash:150`、`test_forged_contract_hash_edge_rejected:162`、`test_validator_issued_hash_edge_accepted:173`（round2）
- **beam/budget/cycle/stop**：`test_cycle_detection:174`、`test_no_cycle_for_linear_path:183`、`test_beam_search_basic:191`、`test_beam_search_depth_limit:205`、`test_beam_search_budget_respected:220`、`test_stop_rule_max_paths:296`（phase_d）；`test_unknown_stop_rule_type_rejected:296`、`test_known_stop_rule_accepted:302`（round2）
- **dedup/uncertainty**：`test_path_dedup_same_path:244`、`test_path_dedup_different_paths:263`、`test_path_uncertainty:282`（phase_d）；`test_path_uncertainty_wired_through_dedup:330`（round2）
- **external consumption**：`test_external_evidence_consumes_via_ingest:318`（phase_d）；`test_uningested_evidence_id_rejected_by_search:83`、`test_ingested_evidence_id_accepted_by_search:101`（round2）
- **bounds + validator sentinel**：`test_edge_validation_result_bounds:314`、`test_add_edge_without_validator_rejected:348`、`test_add_edge_explicit_none_validator_rejected:372`（round2）

## 9. 风险与边界

- **每条 edge 满足 one-step contract**：`add_edge` 必传 validator、重算 contract hash 比对、forged hash 拒绝；sentinel 测试防 validator 被改回 optional。
- **canonical 去重**：RDKit 归一化 + content-addressed node_id；invalid SMILES fail-closed；explicit node_id 被 canonical 覆盖（防伪造）。
- **fail-closed**：未知 stop rule type、un-ingested evidence ID、invalid SMILES、forged contract hash、缺 validator 全 fail-closed。
- **external 闸口**：multistep 只消费 `EvidenceCache` 中已 ingest 的 evidence，与 external ingestion pipeline 焊死。
- **隔离**：只 ADD 文件；只消费 `EvidenceCache`；不 modify strict channel / P7 / P8 / external 包。

## 10. 结论

multi-step candidate graph 的 canonical molecule nodes、validated reaction edges、per-edge evidence/dual-ledger/lane、branch/beam search、cycle detection、depth/cost/risk budgets、path deduplication、path uncertainty、stop rules均已实现；每条 edge 满足 one-step contract（validator 必填 + contract hash 校验）。`tests/p9/test_multistep_*.py`（2 文件，36 tests）覆盖；Round 2 六项 audit findings（P9D-R1-01..06）+ R3-01 sentinel 全部整改并有对应 RED 测试。本报告仅落盘，不新增实现。
