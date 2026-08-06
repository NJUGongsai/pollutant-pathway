# SUBMISSION TO CHATGPT — P1 REMEDIATION ROUND 6

本封面逐项回答 `CHATGPT_P1_REMEDIATION_PROMPT_ROUND_6.md` §21 的 28 项要求。
所有数字与状态均来自本轮真实运行产物（pytest / P0 Gate / P1 Gate / mutation runner / 结构化 evidence），非手工推断。

配套结构化证据：`reports/p1/P1_ROUND_6_AUDIT_EVIDENCE.json`
工作日志：`reports/p1/P1_REMEDIATION_WORKLOG.md`（Round 6 章节）

---

## 1. 项目根
`/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`

## 2. branch / HEAD / dirty status
- **branch**：`main`；**HEAD**：`4eb463368e38f2faa3d3656a05974c4b1c1211a6`
- **working tree**：dirty。保留开工前已存在的用户与前几轮模型修改，未执行 `git reset`/`git checkout --`/`git clean`。

## 3. changed-files 清单
- 实现代码：`reaction_agent/eligibility/engine.py`（cofactor direction 受控 / stoich authority
  key / mechanistic product registry / empty・duplicate FAT / heavy-atom 空 map 证据 / 两个空壳 evidence fail closed）
- Gate/mutation 脚本：`scripts/run_p1_gate.py`（G08 manifest 57→82 nodes）、
  `scripts/run_p1_mutations.py`（M56d + M73–M77 + Round 6 拆分输出）
- 测试：`tests/p1/test_eligibility_reference_integrity.py`（+25 Round 6 节点；修复 Round 5
  FAT-pair-conflict 测试的 p1 SMILES 为 `[H+]` 以避免 heavy-atom 检查提前拦截）
- 重新生成证据：`reports/p1/P1_GATE_REPORT.{json,md}`、`reports/p0/P0_GATE_REPORT.{json,md}`、
  `reports/p1/mutation_results.json` 及 Round 4/5/6 拆分 JSON
- 交付物：`reports/p1/P1_ROUND_6_AUDIT_EVIDENCE.json`、`SUBMISSION_TO_CHATGPT_P1_ROUND_6.md`（本文件）、
  `reports/p1/P1_REMEDIATION_WORKLOG.md`（Round 6 章节）

## 4. 未修改的冻结文件
- `plan/final_design.md`、`plan/final_plan.md`、P0 ADRs/contracts、legacy source、snapshot
  canonical payload（builder/loader 未改）、G09 11 个 mandatory nodes、G08 既有 57 个节点。

---

## 5. 五类问题逐项修复说明（+ 两个空壳 evidence 风险）

### R6-01 uncontrolled cofactor direction
- 查证：`final_design`/docs/ADR 无 cofactor direction 词表；真实 builder
  `reaction_agent/ledgers/source_builder.py` 只产出 `direction="unknown"`。
- 修复：`_ALLOWED_COFACTOR_DIRECTIONS={"unknown"}`；`unknown` → 既有 conditional；
  其他任意无 authority 的非空值 → strict fail closed（`cofactor_change_direction`）。

### R6-02 duplicate/conflicting stoichiometric authority
- 修复：`reactant_entries`/`product_entries` 用 `participant_id` 作 authority key；
  `stoichiometry` 用 `(participant_id, side)`。同 key + 同 coefficient → `*_duplicate`；
  同 key + 不同 coefficient → `*_conflict`。均不得 strict。

### R6-03 mechanistic target 用错 side registry
- 修复：`MechanisticOriginEvidence.target_atom_map_numbers` 必须由 product-side map registry 解析
  （`mechanistic_evidence_map_product_side`），不再用全局 map union。

### R6-04 empty formal atom transfer assignment
- 修复：FAT collection 可为空，但存在 assignment 时 transferred maps 非空
  （`formal_atom_transfer_empty`）、无内部重复（`formal_atom_transfer_duplicate_map`）。

### R6-05 heavy-atom participant 空 map 自报
- 修复：RDKit 只读解析 `canonical_smiles`，heavy_atom_count>0 + 空 maps → fail closed
  （`participant_heavy_atom_map_evidence`）；zero-heavy-atom（proton `[H+]`）允许；
  SMILES 不可解析 → fail closed。

### §11.1 AddedAtomSource non-formal 且无 mechanism
- 修复：无 typed authority 允许其 strict → fail closed（`added_atom_source_unbacked`）。

### §11.2 MechanisticOriginEvidence 空 target
- 修复：空 target 不能靠 vacuous truth 成为 strict mechanism authority → fail closed
  （`mechanistic_evidence_empty_target`）。

---

## 6. 每类 direct negative evidence
| 反例 | Direct 修复后 | Reason token |
|---|---|---|
| R6-01 | `strict_prohibited` | `cofactor_change_direction` |
| R6-02 | `strict_prohibited` | `reactant_entry_conflict` |
| R6-03 | `strict_prohibited` | `mechanistic_evidence_map_product_side` |
| R6-04 | `strict_prohibited` | `formal_atom_transfer_empty` |
| R6-05 | `strict_prohibited` | `participant_heavy_atom_map_evidence` |
| §11.1 | `strict_prohibited` | `added_atom_source_unbacked` |
| §11.2 | `strict_prohibited` | `mechanistic_evidence_empty_target` |

## 7. 每类 public snapshot lane evidence
`SnapshotEvidenceItem → build_snapshot → records.jsonl`：
R6-01/R6-02/R6-03/R6-04/R6-05 均落在 `diagnostic` lane（非 strict）。6 个
`test_public_snapshot_cannot_promote_*` 读取真实 records.jsonl 全部通过。

## 8. positive protection evidence
- `test_unknown_cofactor_direction_remains_conditional`：direction=unknown → conditional。
- `test_mechanistic_target_product_map_remains_valid`：product-side target → strict。
- `test_valid_nonempty_formal_transfer_remains_strict`：非空 FAT（edge 支撑）→ strict。
- `test_valid_fully_mapped_heavy_atom_participant_remains_strict`：CCO + maps → strict。
- `test_zero_heavy_atom_policy_does_not_get_accidentally_broken`：proton `[H+]` → strict。

## 9. G08 mandatory node 明细和数量
- G08：**82 mandatory nodes**（20 Round 4 + 37 Round 5 + 25 Round 6），全部显式列出并强制校验。
- G08 实际运行 `test_eligibility_fail_closed.py` + `test_eligibility_engine.py` +
  `test_eligibility_cross_invariants.py` + `test_eligibility_reference_integrity.py`；
  报告 mandatory_total=82、collected=138、mandatory_passed=82。

## 10. G08 deletion mutation
- M56d：删除单个 Round 6 节点（`test_uncontrolled_cofactor_direction_never_strict`）后
  G08 FAIL（`MANDATORY test node not collected`），随后恢复。
- M56a/M56b/M56c 继续证明整文件 shadowing → G08/G09 FAIL。

## 11. M1–M77 汇总
`77/77 caught`（`all_caught=true`）。M1–M72 无回退；M73–M77 新增全部被目标 invariant 捕获。

## 12. M73–M77 sub-results
| Mutation | sub-results | caught |
|---|---|---|
| M73 | M73a direct / M73b public | true |
| M74 | M74a reactant_entries / M74b product_entries / M74c stoichiometry | true |
| M75 | （单）mechanistic product-registry | true |
| M76 | M76a empty / M76b duplicate / M76c public | true |
| M77 | M77a direct / M77b public | true |

## 13. contracts count
`290 passed`（0 failed / 0 errors / 0 skipped / 0 xfailed / 0 xpassed）。

## 14. P1 tests count
`496 passed`（0 failed / 0 errors / 0 skipped / 0 xfailed / 0 xpassed）。

## 15. full suite count
`786 passed`（0 failed / 0 errors / 0 skipped / 0 xfailed / 0 xpassed）。

## 16. zero skip/xfail/xpass
是。全部套件 0 skipped / 0 xfailed / 0 xpassed。

## 17. P0 Gate 10/10
`10/10 PASS`，Status = `READY_FOR_CHATGPT_AUDIT`。

## 18. P1 Gate 逐项矩阵
```
P1-G01 PASS   P1-G02 PASS   P1-G03 BLOCKED
P1-G04 BLOCKED P1-G05 PASS   P1-G06 PASS
P1-G07 PASS   P1-G08 PASS   P1-G09 PASS
P1-G10 BLOCKED
overall = BLOCKED   (7 PASS / 0 FAIL / 3 BLOCKED)
```
G08 无 implementation failure（82/82 mandatory nodes）；G09 无回退（11/11 + independent
rebuild match + cross-verify stored）。

## 19. snapshot ID/hash
- snapshot_id = `snap_a54fc0a46b30`
- snapshot_hash = `a54fc0a46b3055e560ac2127f8e6464e6a5ab51675879f97cfe21d811e5bc103`
- 与 Round 3/4/5 一致（本轮未改 canonical payload/builder/loader，G09 交叉验证通过）。

## 20. G09 无回退
11 个 mandatory nodes 全部保留并 pass；独立重建两次哈希一致；与 stored hash 交叉验证通过。

## 21. current runtime dependency probe
Python 3.11.15，RDKit 2026.03.4（只读 probe 可用，用于 heavy-atom count）。未安装/升级依赖，未联网。

## 22. G03 blocker
`real_reaction_source_not_confirmed`；`required real proline/2OG source record not located`。
**非** `rdkit_absent`。

## 23. G04 blocker
`RealMapperAdapter.map_reaction()` 仍 skeleton（backend 可用，非 rdkit_absent）。

## 24. G10 blocker
`annotator_a_status=NOT_PRODUCED`、`annotator_b_status=NOT_PRODUCED`、`adjudication_status=NOT_PRODUCED`；
未伪造 inter-annotator agreement。

## 25. worklog 路径
`reports/p1/P1_REMEDIATION_WORKLOG.md`（Round 6 章节，25 项全含，含 RED→GREEN 证据）。

## 26. structured evidence 路径
`reports/p1/P1_ROUND_6_AUDIT_EVIDENCE.json`

## 27. known limitations
- electron `[e-]` SMILES 无法用 RDKit 解析，zero-heavy-atom 语义仅用 proton `[H+]` 正向验证
  （schema limitation，worklog §12 记录）。
- RemovedAtomSink 语义沿用 Round 5 记录（participant 存在 + map 归属最强可证检查）。
- FAT assignment_method 受控词表 = {"formal"}（同 Round 5 记录）。
- 本轮未强制 reactant_entries 与 stoichiometry 跨 collection 一致（无 design authority）。
- G03/G04/G10 仍需真实外部输入。

## 28. P2 状态
**BLOCKED**（P1 overall=BLOCKED，未进入 P2）。

---

## 结论

Round 6 达成任务书 §18 的合理预期矩阵（7 PASS / 0 FAIL / 3 BLOCKED）：

- R6-01–R6-05 + §11 两个空壳 evidence 风险全部修复（direct + public boundary 全通过）。
- G08 mandatory manifest 扩展至 82 nodes（57 → 82），删除单个 Round 6 节点 → G08 FAIL（M56d）。
- M1–M72 无回退；M73–M77 全部由目标 invariant 捕获（77/77）。
- contracts / P1 / full tests 全绿（290 / 496 / 786，零 skip/xfail/xpass）。
- P0 Gate 10/10；G08/G09 无 implementation failure；snapshot hash 未变；无 stale blocker。
- 3 个剩余 BLOCKED 均因真实外部输入缺失（G03 real source / G04 mapper / G10 annotator）。

READY_FOR_CHATGPT_P1_ROUND_6_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
