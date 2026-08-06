# SUBMISSION TO CHATGPT — P1 REMEDIATION ROUND 5

本封面逐项回答 `CHATGPT_P1_REMEDIATION_PROMPT_ROUND_5.md` §19.3 的 45 个问题。
所有数字与状态均来自本轮真实运行产物（pytest / P0 Gate / P1 Gate / mutation runner / 结构化 evidence），非手工推断。

配套结构化证据：`reports/p1/P1_ROUND_5_AUDIT_EVIDENCE.json`
工作日志：`reports/p1/P1_REMEDIATION_WORKLOG.md`（Round 5 章节）

---

## 环境与提交上下文

1. **branch**：`main`
2. **HEAD**：`4eb463368e38f2faa3d3656a05974c4b1c1211a6`
3. **working tree**：dirty。保留开工前已存在的用户与前几轮模型修改，未执行任何 `git reset`/`git checkout --`（遵守任务书 §4.1）。
4. **本轮 changed files**：
   - 实现代码
     - `reaction_agent/eligibility/engine.py`（participant/map registry + 集中 ledger reference validator + element/partial 语义修复 + lineage canonical duplicate）
     - `scripts/run_p1_gate.py`（G08 mandatory manifest 20 → 57 nodes；`test_eligibility_reference_integrity.py` 接入 G08 实际运行）
     - `scripts/run_p1_mutations.py`（M56 增加 M56c + 新增 M57–M72 + Round 5 拆分 JSON 输出）
   - 新增测试
     - `tests/p1/test_eligibility_reference_integrity.py`（37 个 G08 保护节点）
   - 重新生成的权威证据
     - `reports/p1/P1_GATE_REPORT.{json,md}`、`reports/p0/P0_GATE_REPORT.{json,md}`
     - `reports/p1/mutation_results.json`、`eligibility_semantic_invariant_results_round_4.json`、`gate_false_positive_mutation_results_round_4.json`
     - `reports/p1/eligibility_reference_integrity_results_round_5.json`、`eligibility_semantic_invariant_results_round_5.json`、`gate_false_positive_mutation_results_round_5.json`
   - 本轮交付物
     - `reports/p1/P1_ROUND_5_AUDIT_EVIDENCE.json`、`SUBMISSION_TO_CHATGPT_P1_ROUND_5.md`（本文件）、`P1_REMEDIATION_WORKLOG.md`（Round 5 章节）

---

## 测试与 Gate 结果

5. **tests/contracts 统计**：`290 passed`（collected=290，0 failed / 0 errors / 0 skipped / 0 xfailed / 0 xpassed）
6. **tests/p1 统计**：`471 passed`（collected=471，0 failed / 0 errors / 0 skipped / 0 xfailed / 0 xpassed）
7. **full suite 统计**：`761 passed`（collected=761，0 failed / 0 errors / 0 skipped / 0 xfailed / 0 xpassed）
   - 环境：Python 3.11.15，RDKit 2026.03.4
8. **P0 Gate 结果**：`10/10 PASS`，Status = `READY_FOR_CHATGPT_AUDIT`
9. **P1 Gate 逐 Gate 结果**（`7 PASS / 0 FAIL / 3 BLOCKED`，overall = **BLOCKED**）：

   | Gate | 结果 |
   |---|---|
   | P1-G01 package/runtime/lock + config & snapshot | PASS |
   | P1-G02 strict schemas/IDs/provenance + P0 green | PASS |
   | P1-G03 legacy lineage audit complete | BLOCKED |
   | P1-G04 mapping adapter integration | BLOCKED |
   | P1-G05 participant preservation/roles | PASS |
   | P1-G06 lineage graph bipartite/split-merge-transfer | PASS |
   | P1-G07 dual ledgers valid | PASS |
   | P1-G08 eligibility/quarantine policy | **PASS（57/57 mandatory nodes）** |
   | P1-G09 snapshot reproducibility | PASS（11/11 + independent rebuild + cross-verify） |
   | P1-G10 manual audit + full tests | BLOCKED |

   snapshot_id = `snap_a54fc0a46b30`；snapshot_hash = `a54fc0a46b3055e560ac2127f8e6464e6a5ab51675879f97cfe21d811e5bc103`（与 Round 3/4 一致，G09 独立重建交叉验证通过）

10. **M1–M72 逐项结果**：`72/72 caught`（`all_caught = true`）。
    - M1–M41 保留并继续通过（无回退）。
    - M42–M56 保留并继续通过（无回退）；M56 现含 M56a/M56b/M56c 三个子结果。
    - M57–M72：Round 5 新增（含 sub-results M57a/b、M60a/b/c、M62a/b、M63a/b、M65a/b/c、M70a/b、M72a/b）。
    - 明细：`reports/p1/mutation_results.json`（汇总）、`eligibility_reference_integrity_results_round_5.json`、
      `eligibility_semantic_invariant_results_round_5.json`、`gate_false_positive_mutation_results_round_5.json`。
11. **Round 3 complete canonical snapshot 是否保留**：是。未重写 canonical snapshot / builder / loader；
    snapshot_hash 与 Round 3/4 一致（`a54fc0a46b30…`），G09 独立重建 + 交叉验证通过。

---

## Round 5 科学边界（12–32）

以下每条均由 `engine.py` 的集中 registry / ledger-reference validator 强制，并各有 G08 强制测试节点与 mutation：

12. **AddedAtomSource map refs 是否验证**：是。participant 存在但 atom_map_number 不存在 → 非 strict（`added_atom_source_map`）。`test_added_atom_source_existing_participant_unknown_map_never_strict` / M57。
13. **reactant_entries refs/side 是否验证**：是。ghost participant / wrong side → 非 strict（`reactant_entry_ghost/side`）。对应 2 个测试节点 / M58。
14. **product_entries refs/side 是否验证**：是。ghost participant / wrong side → 非 strict（`product_entry_ghost/side`）。对应 2 个测试节点 / M59。
15. **stoichiometry refs/side/coefficient 是否验证**：是。wrong-side / coefficient≤0 → 非 strict（`stoichiometry_side/coefficient`）。对应 2 个测试节点 / M60a/M60b。
16. **role contradictions 是否验证**：是。同 participant 矛盾 role、duplicate、side/lineage 冲突 → 非 strict（`role_assignment_conflict/duplicate`）。`test_contradictory_role_assignments_never_strict` / M60c。
17. **cofactor refs 是否验证**：是。ghost cofactor → 非 strict（`cofactor_change_ghost`）。`test_cofactor_change_ghost_participant_never_strict` / M64。
18. **FormalAtomTransfer side/map/formal-pair consistency 是否验证**：是。side 反转 / transferred map 不存在 / 与 formal pairs 冲突 → 非 strict（`formal_atom_transfer_side/map/pair`）。对应 3 个测试节点 / M61/M62。
19. **RemovedAtomSink refs 是否验证**：是。ghost sink / unknown map → 非 strict（`removed_atom_sink_ghost/map`）。对应 2 个测试节点 / M63。
20. **MechanisticOriginEvidence refs 是否验证**：是。ghost source participant / unknown target map → 非 strict（`mechanistic_evidence_ghost/map`）。对应 2 个测试节点 / M65a/M65b。
21. **mechanistic evidence ID linkage 是否验证**：是。`AddedAtomSource.mechanistic_evidence_id` 非空必须解析到已有 evidence_id（`added_atom_source_evidence`）。`test_added_atom_mechanistic_evidence_id_must_resolve` / M65c。
22. **negative element counts 是否拒绝**：是。negative reactant/product count → 结构矛盾 → quarantine（`element_balance_contradiction … negative`）。对应 2 个测试节点 / M66。
23. **partial 一致 non-zero delta 是否避免误 quarantine**：是。partial/unbalanced 一致 delta 不再被当成 fully-balanced 矛盾 quarantine，reason 诚实标注 `partial_or_unbalanced_source`，仍 fail-closed 不 strict。`test_partial_consistent_nonzero_delta_not_mislabeled_quarantine` / M67。
24. **participant ID uniqueness 是否验证**：是。duplicate participant_id → 非 strict（`participant_duplicate_id`）。`test_duplicate_participant_id_never_strict` / M70a。
25. **participant side vocabulary 是否验证**：是。side 非 {reactant, product}（如 middle）→ 非 strict（`participant_side`）。`test_uncontrolled_participant_side_never_strict` / M70b。
26. **within-participant map uniqueness 是否验证**：是。`atom_map_numbers=[1,1,2]` + summary 自报 uniqueness=True → 仍非 strict（`participant_map_duplicate`）。`test_duplicate_atom_map_within_participant_never_strict` / M68。
27. **same-side cross-participant map uniqueness 是否验证**：是。两个 reactant 声明同一 map → 非 strict（`participant_map_collision`）。`test_same_side_cross_participant_atom_map_collision_never_strict` / M69。
28. **reactant/product 对应 map 是否仍允许**：是。正向保护测试 `test_reactant_product_matching_map_number_remains_valid` 保持 strict（formal mapping 连接两侧，不是 same-side 冲突）。
29. **embedded duplicate IDs 是否拒绝**：是。先检查 `len(raw)==len(set(raw))`（`embedded_lineage_duplicate`）再比较 embedded/external set。`test_duplicate_embedded_lineage_ids_never_strict` / M71。
30. **reordered-map lineage duplicate 是否拒绝**：是。content signature 用 sorted unique maps，`[1,2]` vs `[2,1]` 视为同一 lineage 重复计数（`duplicate_lineage`）；lineage 内 map 重复单独拒绝（`lineage_map_duplicate`）。对应 2 个测试节点 / M72a。
31. **public snapshot API 是否不能绕过**：是。5 个 `test_public_snapshot_cannot_promote_*`（added_atom map / ledger ghost entry / FAT map conflict / duplicate participant map / embedded duplicate lineage）读取真实 `records.jsonl` lane，全部非 strict。M57b/M72b 同样验证 public lane。
32. **strict 语义原因**：每条 fail-closed 都带 invariant-specific reason token，防止“因无关 blocker 碰巧不 strict”的假绿（§11.6）。

---

## Gate 接线与强制测试（33–36）

33. **G08 Round 4 nodes 是否保留**：是。原 20 个 cross-invariant nodes 全部保留并 pass（`g08_round4_nodes_preserved=true`）。
34. **G08 Round 5 nodes 是否 mandatory**：是。新增 `tests/p1/test_eligibility_reference_integrity.py` 的 37 个节点全部进入 `_G08_REQUIRED_NODES`；G08 实际运行该文件并强制校验（57/57 passed）。"列表覆盖完整任务要求"，而非仅总数量。
35. **删除 Round 5 node 后 G08 是否 FAIL**：是。M56c 用占位模块屏蔽 `test_eligibility_reference_integrity.py` 后重跑，得到 G08 `MANDATORY test node not collected` → FAIL（`gate_false_positive_mutation_results_round_5.json`），随后恢复原文件。
36. **G09 nodes 是否无回退**：是。11 个 complete-evidence nodes 全部保留并 pass；G09 独立重建两次哈希一致 + 与 stored hash 交叉验证通过（snapshot_hash 未变）。

---

## stale evidence 与外部 blocker（37–40）

37. **stale RDKit evidence 是否未回归**：是。当前权威证据中 stale `rdkit_absent` = 0；G03 blocker 为 `real_reaction_source_not_confirmed`，非 `rdkit_absent`。
38. **G03 当前 blocker**：`real_reaction_source_not_confirmed`；`required real proline/2OG source record not located`。
39. **G04 当前 blocker**：`RealMapperAdapter.map_reaction()` 仍 skeleton（backend 可用，非 rdkit_absent）。
40. **G10 当前 blocker**：`annotator_a_status=NOT_PRODUCED`、`annotator_b_status=NOT_PRODUCED`、`adjudication_status=NOT_PRODUCED`；未伪造 inter-annotator agreement。

---

## 依赖 / 网络 / fixture / 结论（41–45）

41. **是否安装依赖**：否。未执行任何依赖安装（RDKit 2026.03.4 已在 `.venv` 中就绪）。
42. **是否联网**：否。全程离线。
43. **synthetic fixtures 的用途和标记**：是（仅限单元契约与 mutation baseline）。`FakeAtomMapper`、`_strict_inputs`、reference-integrity 测试 fixture 命名显式含 Fake/synthetic，绝不冒充真实 mapper integration 或真实 reaction source；G04 正因缺乏真实 mapper 而保持 BLOCKED。
44. **assumptions/deviations**：
    - FAT `assignment_method` 受控词表 = `{"formal"}`（schema 默认值；final_design 未定义更细词表，按 fail-closed 保守收窄并在 worklog 记录）。
    - RemovedAtomSink 语义：schema 无更细 typed authority 证明 sink 与哪个 participant/map 对应，采用“participant 存在 + map 属于该 participant”的最强可证检查，无法证明时 fail closed（worklog §13 记录 schema limitation）。
    - G03/G04/G10 的 BLOCKED 属预期（缺真实外部输入：真实反应源、真实 mapper、第二独立 annotator），implementation failure = 0。
    - `contracts` 契约测试位于 `tests/contracts`（无独立 `tests/p0` 目录）。
    - 未重设计 P1、未重写 canonical snapshot、未用宽松 fixture 骗绿、未修改 `final_design.md`/`final_plan.md` 及 P0 冻结内容。
45. **P2 状态**：**BLOCKED**（P1 overall 仍为 BLOCKED，未进入 P2）。

---

## 结论

Round 5 达成任务书 §16.8 的合理预期：

```
P1-G01 PASS   P1-G02 PASS   P1-G03 BLOCKED
P1-G04 BLOCKED P1-G05 PASS   P1-G06 PASS
P1-G07 PASS   P1-G08 PASS   P1-G09 PASS
P1-G10 BLOCKED
overall = BLOCKED
```

- R5-01–R5-16 全部修复（独立复现 → RED → fail-closed 实现 → public boundary 全通过）。
- G08 mandatory manifest 扩展至 57 nodes（20 Round-4 + 37 Round-5），缺失任一 → G08 FAIL（M56a/M56c）。
- M1–M72 全部被各自目标 invariant 捕获（72/72，M1–M56 无回退）。
- contracts / P1 / full tests 全绿（290 / 471 / 761，零 skip/xfail/xpass）。
- P0 Gate 10/10；G08/G09 无内部 failure；当前 evidence 无 stale blocker。
- 3 个剩余 BLOCKED 均因真实外部输入缺失，符合“implementation failure 优先于 BLOCKED”的聚合规则。

READY_FOR_CHATGPT_P1_ROUND_5_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
