# SUBMISSION TO CHATGPT — P1 REMEDIATION ROUND 4

本封面逐项回答 `CHATGPT_P1_REMEDIATION_PROMPT_ROUND_4_FOR_CLAUDE.md` §17.3 的 36 个问题。
所有数字与状态均来自本轮真实运行产物（pytest / P0 Gate / P1 Gate / mutation runner），非手工推断。

配套结构化证据：`reports/p1/P1_ROUND_4_AUDIT_EVIDENCE.json`
工作日志：`reports/p1/P1_REMEDIATION_WORKLOG.md`（Round 4 章节）

---

## 环境与提交上下文

1. **branch**：`main`
2. **HEAD**：`4eb463368e38f2faa3d3656a05974c4b1c1211a6`
3. **working tree**：dirty。保留开工前已存在的工作区修改，未执行任何 `git reset`/`git checkout --`（遵守提示词 §2）。
4. **本轮 changed files**：
   - 引擎/管线代码
     - `reaction_agent/eligibility/engine.py`（14 个 fail-open 收敛为 fail-closed 的跨对象校验）
   - Gate / mutation / producer 脚本
     - `scripts/run_p1_gate.py`（G08/G09 强制节点清单接线）
     - `scripts/run_p1_mutations.py`（新增 M42–M56 + Round 4 拆分 JSON 输出）
     - `scripts/legacy_lineage_audit.py`（rdkit runtime 文案改为 data-driven）
     - `scripts/p1_preflight.py`（新增 P1_PREFLIGHT.md 渲染器，data-driven）
     - `scripts/regenerate_snapshot_sample.py`（real_source_snapshot 改为 live rdkit probe）
   - 新增测试（G08/G09 保护对象）
     - `tests/p1/test_eligibility_cross_invariants.py`（20 节点）
     - `tests/p1/test_eligibility_fail_closed.py`
     - `tests/p1/test_snapshot_complete_evidence.py`（11 节点）
     - `tests/p1/test_snapshot_nested_evidence.py`
   - 重新生成的权威证据
     - `reports/p1/P1_GATE_REPORT.{json,md}`、`reports/p0/P0_GATE_REPORT.{json,md}`
     - `reports/p1/P1_PREFLIGHT.{json,md}`、`reports/p1/snapshot_build_sample.json`
     - `reports/data_audit/legacy_lineage_audit.{json,md}`
     - `reports/p1/mutation_results.json`、`eligibility_semantic_invariant_results_round_4.json`、`gate_false_positive_mutation_results_round_4.json`
   - 本轮交付物
     - `reports/p1/P1_ROUND_4_AUDIT_EVIDENCE.json`
     - `reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_4.md`（本文件）
     - `reports/p1/P1_REMEDIATION_WORKLOG.md`（Round 4 章节）

---

## 测试与 Gate 结果

5. **tests/contracts 统计**：`290 passed`（`.venv/bin/python -m pytest tests/contracts -q`）
6. **tests/p1 统计**：`434 passed`（`.venv/bin/python -m pytest tests/p1 -q`）
7. **full suite 统计**：`724 passed`（`.venv/bin/python -m pytest tests -q`）
   - 环境：Python 3.11.15，RDKit 2026.03.4
8. **P0 Gate 结果**：`10/10 PASS`，Status = `READY_FOR_CHATGPT_AUDIT`
9. **P1 Gate 逐 Gate 结果**（`7 PASS / 3 BLOCKED / 0 FAIL`，overall = **BLOCKED**）：

   | Gate | 结果 |
   |---|---|
   | P1-G01 package/runtime/lock + config & snapshot | PASS |
   | P1-G02 strict schemas/IDs/provenance + P0 green | PASS |
   | P1-G03 legacy lineage audit complete | BLOCKED |
   | P1-G04 mapping adapter integration | BLOCKED |
   | P1-G05 participant preservation/roles | PASS |
   | P1-G06 lineage graph bipartite/split-merge-transfer | PASS |
   | P1-G07 dual ledgers valid | PASS |
   | P1-G08 eligibility/quarantine policy | PASS |
   | P1-G09 snapshot reproducibility | PASS |
   | P1-G10 manual audit + full tests | BLOCKED |

   snapshot_id = `snap_a54fc0a46b30`，snapshot_hash = `a54fc0a46b3055e560ac2127f8e6464e6a5ab51675879f97cfe21d811e5bc103`

10. **M1–M56 逐项结果**：`56/56 caught`（`all_caught = true`）。
    - M1–M41 全部保留并继续通过（无回退）。
    - M42–M55：eligibility 语义不变量（见下 12–22）。
    - M56：Gate 接线保护（M56a → G08 FAIL，M56b → G09 FAIL）。
    - 明细：`reports/p1/mutation_results.json`（汇总）、`eligibility_semantic_invariant_results_round_4.json`（M42–M55 独立 expected/actual/caught）、`gate_false_positive_mutation_results_round_4.json`（M56a/M56b）。

11. **Round 3 complete canonical snapshot 是否保留**：是。未重写 canonical snapshot；snapshot_hash 与 Round 3 一致（`a54fc0a46b30…`），仅重跑校验其可复现性。

---

## Strict scientific boundary（12–22）

以下每条均由 `engine.py` 的跨对象校验强制，并各有对应的 G08 强制测试节点与 mutation：

12. **participant mapped_fraction 是否进入 strict validation**：是。任一 participant `mapped_fraction < 1.0` → 非 strict（fail-closed）。对应 `test_participant_low_mapped_fraction_never_strict` / M47。
13. **actual formal pair coverage 是否验证**：是。summary 自报 1.0/complete 但实际 formal pair 未覆盖全部原子 → 非 strict。对应 `test_self_reported_full_mapping_with_incomplete_actual_pair_coverage_never_strict` / M48。
14. **reverse many-to-one mapping 是否拒绝**：是。两个 reactant atom 指向同一 product atom（反向非唯一）→ 非 strict。对应 `test_reverse_collision_many_to_one_mapping_never_strict` / M49。
15. **explicit element imbalance 是否 quarantine/never strict**：是。fully-balanced ledger 出现 non-zero element delta → 非 strict。对应 `test_nonzero_element_balance_never_strict` / M42（另含 delta 与 counts 不一致、重复 element 条目：M-level tests 13/6/7 节点）。
16. **explicit ReactionEvidence quarantine 是否优先**：是。`ReactionEvidence.quarantine` 非空 → 路由到 quarantine，绝不 production strict。对应 `test_explicit_reaction_evidence_quarantine_routes_to_quarantine` / M43。
17. **ambiguity_sets 是否禁止未经证明的 strict**：是。存在 identity ambiguity set → 非 strict。对应 `test_identity_ambiguity_set_never_strict` / M44。
18. **embedded/external lineage mismatch 是否拒绝**：是。embedded lineage id 与 external lineage 冲突 → 非 strict（embedded 非空时才校验，authority 见 Q… 一致性）。对应 `test_embedded_external_lineage_mismatch_never_strict` / M45。
19. **uncontrolled direction 是否拒绝**：是。direction 非受控值（如 `sideways`）→ 非 strict。对应 `test_uncontrolled_direction_value_never_strict` / M46。
20. **ledger ghost references 是否拒绝**：是。AddedAtomSource / RoleAssignment / StoichiometricEntry / FormalAtomTransferAssignment 指向不存在的 participant 或 map → 非 strict。对应 4 个 ghost-reference 测试节点 / M50–M53。
21. **generic unknowns 是否禁止 strict**：是。generic ledger unknowns 含 identity/source unknown → 非 strict。对应 `test_generic_unknowns_never_strict` / M54。
22. **duplicate lineage 是否拒绝**：是。重复 lineage id/content → 非 strict。对应 `test_duplicate_lineage_id_or_content_never_strict` / M55。

23. **public snapshot API 是否不能绕过**：是。通过 public snapshot 构建路径（而非直接调 `decide_eligibility`）注入 element imbalance / explicit quarantine / reverse-collision mapping，同样无法被提升为 strict。对应 3 个 `test_public_snapshot_api_cannot_promote_*` 节点。

---

## Gate 接线与强制测试（24–26）

24. **G08 实际运行哪些文件/node**：文件 `tests/p1/test_eligibility_cross_invariants.py`，强制 **20** 个节点（valid strict baseline + 上述 12–23 全部不变量，含 3 个 public snapshot API 节点）。完整节点清单见 `P1_ROUND_4_AUDIT_EVIDENCE.json` → `gate_wiring.g08_required_tests`。
25. **G09 实际运行哪些文件/node**：文件 `tests/p1/test_snapshot_complete_evidence.py`，强制 **11** 个节点（hash 随 provenance/ambiguity/quarantine 变化、完整持久化、loader 拒篡改、双 ledger 不可分歧、runtime 排除策略显式）。完整清单见 `gate_wiring.g09_required_tests`。
26. **删除 mandatory test 后 Gate 是否 FAIL**：是。G08/G09 从 pytest json-report 校验每个强制节点被 collection 且 pass；任一缺失 → “MANDATORY test node not collected” → implementation_failures → Gate FAIL。M56a（G08）与 M56b（G09）用占位模块屏蔽对应节点后重跑，均得到 FAIL（`gate_false_positive_mutation_results_round_4.json`），随后恢复原文件。

---

## stale evidence 与外部 blocker（27–30）

27. **current evidence 是否仍含 stale `rdkit_absent`**：否。对 `reports/data_audit`、`P1_PREFLIGHT.{json,md}`、`snapshot_build_sample.json`、`P1_GATE_REPORT.{json,md}` 扫描，当前权威证据中 stale `rdkit_absent` = 0。
    - 修复方式为改 producer 后重新生成（非手工改结果）：
      - `regenerate_snapshot_sample.py` 的 real_source_snapshot 改为 live rdkit probe；
      - `p1_preflight.py` 的 P1_PREFLIGHT.md 改为 data-driven 渲染（`absent: none`）；
      - `legacy_lineage_audit.py` 的 docstring/proline note/audit_scope 改为 data-driven。
    - 剩余匹配均为 benign：legacy audit 的 `mapping_missing` 类别**定义**文本、Gate 报告中“rdkit available at runtime: G03 no longer reports rdkit_absent”的**更正说明**、preflight 的“absent: none”。
28. **G03 当前 blocker**：`real_reaction_source_not_confirmed`；`required real proline/2OG source record not located`。**不是** `rdkit_absent`。
29. **G04 当前 blocker**：`RealMapperAdapter.map_reaction()` 仍是 skeleton — backend 可用（非 rdkit_absent），但真实 mapping integration 尚未接入（scoped T4 follow-up）。
30. **G10 当前 blocker**：`annotator_a_status=NOT_PRODUCED`、`annotator_b_status=NOT_PRODUCED`、`adjudication_status=NOT_PRODUCED`；未伪造 inter-annotator agreement。

---

## 依赖 / 网络 / fixture / 结论（31–36）

31. **是否安装依赖**：否。未执行任何依赖安装（RDKit 2026.03.4 已在 `.venv` 中就绪）。
32. **是否联网**：否。全程离线。
33. **是否使用 synthetic fixture**：是（仅限单元契约与 mutation baseline）。`FakeAtomMapper` 与 `_strict_inputs()` 合法 strict baseline 用于契约/变异测试。
34. **synthetic fixture 是否明确标记**：是。命名显式含 `Fake`/synthetic，绝不冒充真实 mapper integration 或真实 reaction source；G04 正因缺乏真实 mapper 而保持 BLOCKED。
35. **assumptions/deviations**：
    - G03/G04/G10 的 BLOCKED 属预期（缺真实外部输入：真实反应源、真实 mapper、第二独立 annotator），非实现缺陷。
    - `contracts` 契约测试位于 `tests/contracts`（本仓库无独立 `tests/p0` 目录，P0 契约即 contracts）。
    - 未重设计 P1、未重写 canonical snapshot、未用宽松 fixture 骗绿。
36. **P2 状态**：**BLOCKED**（P1 overall 仍为 BLOCKED，未进入 P2）。

---

## 结论

本轮达成提示词 §14 的合理预期：

```
P1-G01 PASS   P1-G02 PASS   P1-G03 BLOCKED
P1-G04 BLOCKED P1-G05 PASS   P1-G06 PASS
P1-G07 PASS   P1-G08 PASS   P1-G09 PASS
P1-G10 BLOCKED
overall = BLOCKED
```

- 14 个 fail-open 全部收敛为 fail-closed，并被 G08/G09 强制测试与 M42–M56 双重保护。
- 3 个剩余 BLOCKED 均因真实外部输入缺失，implementation failure = 0，符合“implementation failure 优先于 BLOCKED；仅剩外部输入缺失时才允许 overall BLOCKED”的聚合规则。
