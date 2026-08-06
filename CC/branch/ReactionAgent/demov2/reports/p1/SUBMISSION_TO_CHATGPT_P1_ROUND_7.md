# SUBMISSION TO CHATGPT — P1 REMEDIATION ROUND 7

本封面逐项回答 `CHATGPT_P1_REMEDIATION_PROMPT_ROUND_7.md` §22 的 43 项要求。
所有数字与状态均来自本轮真实运行产物（pytest / P0 Gate / P1 Gate / mutation runner / 结构化 evidence），非手工推断。

配套结构化证据：`reports/p1/P1_ROUND_7_AUDIT_EVIDENCE.json`
工作日志：`reports/p1/P1_REMEDIATION_WORKLOG.md`（Round 7 章节）

---

## 1. 项目根
`/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`

## 2. branch / HEAD / dirty status
- **branch**：`main`；**HEAD**：`4eb463368e38f2faa3d3656a05974c4b1c1211a6`
- **working tree**：dirty。保留开工前已存在的用户与前几轮模型修改；未执行 `git reset`/`git checkout --`/`git clean`。

## 3. changed-files 清单
见 `P1_ROUND_7_AUDIT_EVIDENCE.json["changed_files"]`（20 项）：
- 实现：`reaction_agent/eligibility/engine.py`
- Gate/mutation 脚本：`scripts/run_p1_gate.py`（G08 82→112）、`scripts/run_p1_mutations.py`（M56e + M78–M83 + round_7 拆分）
- 测试：`test_eligibility_reference_integrity.py`（+30 R7 节点 + index-aware helper）、
  `test_eligibility_cross_invariants.py`、`test_eligibility_fail_closed.py`、`test_eligibility_engine.py`、
  `test_snapshot_builder.py`、`test_snapshot_nested_evidence.py`、`test_snapshot_complete_evidence.py`
  （genuine strict baseline 重建：CCO+[1,2] → CC+[1,2]）
- 重新生成证据：`snapshot_build_sample.json`、`mutation_results.json`、`P1_GATE_REPORT.{json,md}`、
  `P0_GATE_REPORT.{json,md}`、`P1_REMEDIATION_WORKLOG.md` 及 round_7 拆分 JSON
- 交付物：`P1_ROUND_7_AUDIT_EVIDENCE.json`、`SUBMISSION_TO_CHATGPT_P1_ROUND_7.md`（本文件）

## 4. 未修改的冻结文件
`plan/final_design.md`、`plan/final_plan.md`、P0 ADRs/contracts、legacy source（`../benchmark`、`../core`）、
snapshot canonical payload（builder/loader 结构未改）、G09 11 个 mandatory nodes、G08 既有 82 个节点（保留并扩展）、
M1–M77、schema（`mapping.py`/`ledger.py` 未改）。

---

## 5. R7-01 underflow
`CC`（2 heavy atoms）声明 1 个 map + `mapped_fraction=1.0` → 修复后 `strict_prohibited`
（`participant_heavy_atom_map_count`）。RED 测试 `test_heavy_atom_map_count_underflow_never_strict` 修复前 fail、修复后 pass。

## 6. R7-01 overflow
`C`（1 heavy atom）声明 2 个 maps + `mapped_fraction=1.0` → 修复后 `strict_prohibited`
（`participant_heavy_atom_map_count`）。RED 测试 `test_heavy_atom_map_count_overflow_never_strict` 修复前 fail、修复后 pass。

## 7. genuine strict baseline
旧的 "fully mapped positive baseline"（`CCO + [1,2]`）有 3 个重原子、只有 2 个 map，不是 genuinely fully mapped。
本轮重建为：r1/p1 = `CC`（2 heavy atoms，RDKit 验证）+ `atom_map_numbers=[1,2]`（2 个唯一 map）+ `mapped_fraction=1.0`；
formal pairs `r1:1→p1:1`、`r1:2→p1:2`；lineage transformed maps `[1,2]`。全部门限均一致，baseline 为 `strict_eligible`。

## 8. R7-02 zero map
participant `atom_map_numbers=[0,1]` → `strict_prohibited`（`participant_map_identifier`）。

## 9. R7-02 negative map
participant `atom_map_numbers=[-1,1]` → `strict_prohibited`（`participant_map_identifier`）。

## 10. duplicate AddedAtomSource
同一 `AddedAtomSource` 出现两次 → `strict_prohibited`（`added_atom_source_duplicate`）。

## 11. conflicting AddedAtomSource
同一 atom map 被两个不同 source authority claim → `strict_prohibited`（`added_atom_source_conflict`）。

## 12. duplicate RemovedAtomSink
同一 `RemovedAtomSink` 出现两次 → `strict_prohibited`（`removed_atom_sink_duplicate`）。

## 13. conflicting RemovedAtomSink
同一 atom map 被两个不同 sink claim → `strict_prohibited`（`removed_atom_sink_conflict`）。

## 14. duplicate FAT assignment
同一 `FormalAtomTransferAssignment` 出现两次 → `strict_prohibited`（`formal_atom_transfer_duplicate_assignment`）。

## 15. conflicting FAT assignment
同一 source atom map 被两个不同 target edge 的 FAT claim（无 typed split authority）→ `strict_prohibited`
（`formal_atom_transfer_assignment_conflict`）。

## 16. duplicate mechanistic target maps
`MechanisticOriginEvidence.target_atom_map_numbers=[1,1]` → `strict_prohibited`
（`mechanistic_evidence_duplicate_target_map`）。

## 17. unbacked RemovedAtomSink
`RemovedAtomSink(atom_map_number=1, sink_participant_id="r1", formal_assignment=False)` 且无其他 typed authority
→ `strict_prohibited`（`removed_atom_sink_unbacked`）。

## 18. direct negative evidence
每个 R7 负向测试从 genuine strict baseline 出发（先 `_assert_reference_baseline_strict()`，含 RDKit heavy/map count 一致 +
map IDs 全正），只改一个目标条件，assert 非 strict + invariant-specific reason。修复前 24 个全部 fail（RED），修复后全 pass。

## 19. direct positive evidence
- `test_genuinely_fully_mapped_heavy_atom_participant_remains_strict`（CC+[1,2] baseline → strict）
- `test_zero_heavy_atom_proton_policy_remains_valid`（[H+] 无 maps → strict）
- `test_positive_atom_map_identifiers_remain_strict`
- `test_distinct_valid_ledger_evidence_remains_valid`（distinct AAS/sink/FAT/mechanistic → strict）
- `test_formally_backed_removed_atom_sink_remains_valid`
- `test_public_snapshot_strict_positive_is_in_production_index`

## 20. records lane evidence
R7 负向反例经 `build_snapshot` 后 records.jsonl lane 均非 strict（diagnostic），且不在 production index。

## 21. production membership evidence
`_build_lanes` 读取 production_index.jsonl：R7 负向反例的 reaction_id 均 `not in production_ids`。

## 22. diagnostic/quarantine membership evidence
R7 负向反例落在 diagnostic_index.jsonl（`_assert_public_negative` 验证）；quarantine 反例（R4 element imbalance）落在
quarantine_index.jsonl。

## 23. index-only leakage mutation
M83：保持 records lane=diagnostic，把 diagnostic reaction ID 注入 production_index.jsonl → index-aware public boundary FAIL
（`unexpected production membership`），失败来源精确为 production membership，非 lane 改/hash 错/缺文件/collection 失败。

## 24. G08 nodes
G08 mandatory nodes = **112**（既有 82 + 本轮 30 个 R7 节点），全部显式列出并强制校验。

## 25. deletion protection
M56 扩展为 M56a/b/c/d/e。M56e：删除单个 Round 7 节点（`test_heavy_atom_map_count_underflow_never_strict`）→ G08 FAIL，随后恢复。

## 26. M1–M83
`M1–M83 = 83/83 caught`。M1–M77 无回退；M78–M83 全部被目标 invariant 捕获（含 M83 index-only leakage）。
每项带完整 result（修复 Round 6 `"M75": []` 空数组问题）。

## 27. contracts count
`290 passed`（0 failed / 0 errors / 0 skipped / 0 xfailed / 0 xpassed）。

## 28. P1 tests count
`526 passed`（0 failed / 0 errors / 0 skipped / 0 xfailed / 0 xpassed）。

## 29. full suite count
`816 passed`（0 failed / 0 errors / 0 skipped / 0 xfailed / 0 xpassed）。

## 30. zero skip/xfail/xpass
是。全部套件 0 skipped / 0 xfailed / 0 xpassed。

## 31. P0 Gate
`10/10 PASS`，Status = `READY_FOR_CHATGPT_AUDIT`。

## 32. P1 Gate matrix
```
P1-G01 PASS   P1-G02 PASS   P1-G03 BLOCKED
P1-G04 BLOCKED P1-G05 PASS   P1-G06 PASS
P1-G07 PASS   P1-G08 PASS   P1-G09 PASS
P1-G10 BLOCKED
overall = BLOCKED   (7 PASS / 0 FAIL / 3 BLOCKED)
```
G08 无 implementation failure（112/112 mandatory nodes）；G09 无回退（11/11 + independent rebuild match + cross-verify stored）。

## 33. G09
11 个 mandatory nodes 全部保留并 pass；独立重建两次哈希一致；与 stored hash 交叉验证通过。

## 34. snapshot ID/hash
- snapshot_id = `snap_5acdcbe5ee61`
- snapshot_hash = `5acdcbe5ee61f86e89ee5fab8e21d1aec21c7d79d569c551a84baa68df5cf8c4`
- **变化原因（明确记录，非偷偷改 stored hash）**：R7-01B 有依据地重建 synthetic strict-valid fixture baseline，
  由 `CCO+[1,2]`（并非 genuinely fully mapped）改为 `CC+[1,2]`。该 snapshot 是 synthetic fixture（非真实数据）。

## 35. runtime probe
Python 3.11.15，RDKit 2026.03.4（只读 probe；`CC`=2、`C`=1、`CCO`=3、`CC(=O)O`=4、`[H+]`=0、`[e-]`=None）。未安装/升级依赖，未联网。

## 36. G03 blocker
`real_reaction_source_not_confirmed`；`required real proline/2OG source record not located`。**非** `rdkit_absent`。

## 37. G04 blocker
`RealMapperAdapter.map_reaction()` 仍 skeleton（backend 可用，非 rdkit_absent）。

## 38. G10 blocker
`annotator_a_status=NOT_PRODUCED`、`annotator_b_status=NOT_PRODUCED`、`adjudication_status=NOT_PRODUCED`；
未伪造 inter-annotator agreement。

## 39. known limitations
- electron `[e-]` SMILES 无法用 RDKit 解析，zero-heavy-atom 语义仅用 proton `[H+]` 正向验证（schema limitation）。
- RemovedAtomSink 无 mechanistic sink authority 字段 → `formal_assignment=False` 一律视为 unbacked（fail closed）。
- FAT assignment_method 受控词表 = {"formal"}（同 Round 5 记录）。
- fixture snapshot 是 synthetic，验证 pipeline contract 而非真实化学。

## 40. structured evidence 路径
`reports/p1/P1_ROUND_7_AUDIT_EVIDENCE.json`

## 41. worklog 路径
`reports/p1/P1_REMEDIATION_WORKLOG.md`（Round 7 章节，含 RED→GREEN 证据）

## 42. P2 状态
**BLOCKED**（P1 overall=BLOCKED，未进入 P2）。

---

## 结论

Round 7 达成任务书 §18 的合理预期矩阵（7 PASS / 0 FAIL / 3 BLOCKED）：

- R7-01–R7-06 全部修复（direct + public index-aware boundary 全通过）。
- genuine strict baseline 在 molecule/map/pair/lineage 层科学一致（CC+[1,2]）。
- G08 mandatory manifest 扩展至 112 nodes（82 → 112），删除单个 Round 7 节点 → G08 FAIL（M56e）。
- M1–M77 无回退；M78–M83 全部由目标 invariant 捕获（83/83），M83 证明 index-only leakage 被 index-aware boundary 捕获。
- contracts / P1 / full tests 全绿（290 / 526 / 816，零 skip/xfail/xpass）。
- P0 Gate 10/10；G08/G09 无 implementation failure；G09 交叉验证通过（snapshot hash 因 fixture 重建有依据地更新）。
- 3 个剩余 BLOCKED 均因真实外部输入缺失（G03 real source / G04 mapper / G10 annotator）。

READY_FOR_CHATGPT_P1_ROUND_7_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
