# Round 8 提交（P1 snapshot-index authority 最小整改）

> **提交对象：** ChatGPT（独立只读审核）
> **性质：** P1 snapshot-index authority 最小整改，不是 P2 开发
> **日期：** 2026-07-31
> **结构化证据：** `reports/p1/P1_ROUND_8_AUDIT_EVIDENCE.json`
> **工作日志：** `reports/p1/P1_REMEDIATION_WORKLOG.md`（Round 8 章节）

---

## 逐项回答（Round 8 任务书 §23 的 53 项）

1. **项目根**：`/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`
2. **branch**：`main`
3. **HEAD**：`4eb463368e38f2faa3d3656a05974c4b1c1211a6`（本轮未提交；Round 7 + Round 8 改动均为 working-tree）
4. **dirty status**：dirty（Round 7 与 Round 8 改动未提交）
5. **changed-files**：见 `P1_ROUND_8_AUDIT_EVIDENCE.json["changed_files"]`（builder/loader、test_snapshot_nested_evidence、test_snapshot_builder、run_p1_gate、run_p1_mutations、snapshot_build_sample、P0/P1 Gate reports、mutation_results、round_8 拆分 JSON ×2、evidence、submission、worklog）
6. **未修改 frozen files**：`plan/final_design.md`、`plan/final_plan.md`、`reaction_agent/eligibility/engine.py`、`reaction_agent/schemas/{evidence,mapping,ledger,lineage,p1_entities}.py`、`reaction_agent/policies/*`、P0 ADRs、P0 frozen contracts、`../benchmark`、`../core`
7. **Round 7 baseline**（本轮开工前串行冻结）：contracts 290 / P1 526 / full 816 / P0 10/10 / P1 7P·0F·3B / G08 112 / G09 11 / M1–M83 83/83；0 skip / 0 xfail / 0 xpass
8. **R8-01 pre-fix**：`coherent_diagnostic_in_production_loader.accepted = true`（真实 `load_snapshot` 接受 hash-coherent diagnostic-in-production）
9. **R8-01 post-fix**：`accepted = false`，异常 `SnapshotHashMismatchError`，reason token `index_partition_wrong_lane`
10. **R8-02 pre-fix**：`diagnostic_before_nonempty=true, diagnostic_after_empty=true, accepted=true`（清空 diagnostic index 被接受）
11. **R8-02 post-fix**：`accepted = false`，reason token `index_partition_missing`
12. **R8-03 pre-fix**：`mutated_nested_payload=true, accepted=true`（index entry 嵌套 payload 篡改被接受）
13. **R8-03 post-fix**：`accepted = false`，reason token `index_entry_content_mismatch`
14. **partition contract**：`records.jsonl` 为完整 record authority；strict/conditional → production、diagnostic → diagnostic、quarantine → quarantine，均 exactly once
15. **production allowed lanes**：`strict` + `conditional`（`diagnostic`/`quarantine` 禁止）
16. **diagnostic allowed lanes**：`diagnostic`
17. **quarantine allowed lanes**：`quarantine`
18. **completeness**：`production_ids ∪ diagnostic_ids ∪ quarantine_ids == record_ids`
19. **disjointness**：三 index 两两不相交（`index_partition_overlap` 拒绝）
20. **records uniqueness**：records.jsonl reaction_id 唯一（`index_record_duplicate` 拒绝）
21. **index uniqueness**：每个 index 内 reaction_id 唯一（`index_entry_duplicate` 拒绝）
22. **index entry rehash**：对每个 index entry 重算 record hash == entry stored hash（`index_entry_content_mismatch` 拒绝）
23. **index/full-record equality**：entry stored hash == full record stored hash（`index_entry_hash_mismatch`）+ canonical payload == full record payload（`index_entry_content_mismatch`）
24. **diagnostic index hash**：`canonical_hash(sorted(record_content_hashes))`；已加入 builder canonical content 与 loader canonical recomputation
25. **diagnostic hash manifest field**：on-disk manifest 持久化 `diagnostic_index_hash`，loader 精确重建并交叉验证（manifest 字段不匹配 → `diagnostic_index_hash_mismatch`）
26. **valid snapshot positive protection**：`test_loader_accepts_exact_complete_index_partition`（四 lane 快照精确 partition 正常加载，union==records、disjoint、lane-exact）
27. **conditional production positive protection**：`test_conditional_record_is_only_in_production_index`（conditional 仍在 production，不进 diagnostic/quarantine）
28. **G08 previous/final totals**：112 → **117**（mandatory passed = 117）
29. **G08 new nodes**：`test_loader_rejects_hash_coherent_diagnostic_in_production`、`test_loader_rejects_hash_coherent_quarantine_in_production`、`test_loader_rejects_cross_index_membership`、`test_loader_accepts_exact_complete_index_partition`、`test_conditional_record_is_only_in_production_index`
30. **G09 previous/final totals**：11 → **21**（mandatory passed = 21）
31. **G09 new nodes**：missing_diagnostic_member / missing_production_member / missing_quarantine_member / duplicate_records_reaction_id / duplicate_index_reaction_id / mutated_nested_production_index_payload / mutated_nested_diagnostic_index_payload / diagnostic_index_content_changes_snapshot_hash / snapshot_manifest_persists_diagnostic_index_hash / accepts_exact_complete_index_partition
32. **M56f/M56g**：M56f 删除 Round 8 G08 production-partition 节点 → G08 FAIL；M56g 删除 Round 8 G09 diagnostic-integrity 节点 → G09 FAIL（temp copy / finally 恢复，失败来自 missing mandatory node）
33. **corrected M83**：真实 `load_snapshot` 拒绝注入 production 的 diagnostic record，reason `index_partition_wrong_lane`（不再 self-assert、不再 generic hash mismatch）
34. **M84**：删除 diagnostic_index expected member（manifest/hash/COMPLETE 不动）→ 真实 `load_snapshot` 拒绝，reason `index_partition_missing`
35. **M85**：篡改 production_index entry 嵌套 payload（保持自报 hash）→ 真实 `load_snapshot` 拒绝，reason `index_entry_content_mismatch`
36. **M1–M82 preservation**：全部保留并继续 caught（无回退）
37. **final mutation count**：**85/85 caught**（M83 corrected、M84/M85 added、M1–M82 preserved）
38. **contracts count**：**290 passed**（0 failed/errors/skipped/xfailed/xpassed）
39. **P1 count**：**541 passed**（526 + 15 新增）
40. **full count**：**831 passed**（816 + 15）
41. **zero skip/xfail/xpass**：是
42. **P0 Gate**：**10/10 PASS**，`READY_FOR_CHATGPT_AUDIT`
43. **P1 Gate matrix**：

| Gate | 状态 |
|---|---:|
| P1-G01 | PASS |
| P1-G02 | PASS |
| P1-G03 | BLOCKED |
| P1-G04 | BLOCKED |
| P1-G05 | PASS |
| P1-G06 | PASS |
| P1-G07 | PASS |
| P1-G08 | PASS |
| P1-G09 | PASS |
| P1-G10 | BLOCKED |

7 PASS / 0 FAIL / 3 BLOCKED，overall = BLOCKED（退出码非零为预期）。

44. **snapshot ID/hash**：`snap_0672a2d6ff95` / `0672a2d6ff95c9d0bff3f72011c196c6fd01ab1b5108145ccb1d9bcc849a4a5b`；`diagnostic_index_hash = f8d8ef5eb3a7649c7a9cc98f0b72e73fd655acd4f78863479465686d3db362cc`
45. **snapshot hash change reason**：Round 8 把 `diagnostic_index_hash` 绑定进 canonical content（Round 7 `5acdcbe5ee61…` → Round 8 `0672a2d6ff95…`）；fixture 为 synthetic，`snapshot_build_sample.json` 已重新生成，G09 cross-verify 通过
46. **G03 blocker**：`real_reaction_source_not_confirmed`（缺真实 proline/2OG source record）
47. **G04 blocker**：`RealMapperAdapter.map_reaction()` 仍 skeleton
48. **G10 blocker**：annotator_a/b + adjudication `NOT_PRODUCED`
49. **deferred semantic risks**：同一 AddedAtomSource formal=True/False、同内容仅 evidence_id 不同的 MechanisticOriginEvidence、同一 FAT edge `[1]` vs `[1,2]` overlap —— 三者本轮未改，worklog 记录为 `must be frozen before P4 evidence aggregation/ranking` / `not modified in Round 8 without authority`
50. **structured evidence path**：`reports/p1/P1_ROUND_8_AUDIT_EVIDENCE.json`
51. **worklog path**：`reports/p1/P1_REMEDIATION_WORKLOG.md`（Round 8 章节）
52. **dependency/network actions**：无（未安装依赖、未联网、RDKit 2026.03.4 仅只读探测）
53. **P2 status**：**BLOCKED**（本轮未进入 P2，未生成任何 P2 performance）

---

## 补充证据（防伪）

- 三个 fail-open 的修复前复现与修复后复现均使用**真实 public `build_snapshot` + `load_snapshot`**，见 `P1_ROUND_8_AUDIT_EVIDENCE.json` 的 `R8-01_before/after`、`R8-02_before/after`、`R8-03_before/after`（含 fixture reaction_id、records lane、mutation、pre/post loader result、exception type、reason token、manifest/hash/COMPLETE 是否变更、是否 generic hash mismatch）。
- M83/M84/M85 的 evidence 均为真实 loader 抛出的 typed reason token（`index_partition_wrong_lane` / `index_partition_missing` / `index_entry_content_mismatch`），非 mutation runner 自我断言。
- 本轮新增 15 个测试，其中 13 个在旧实现上真实失败（7 个 fail-open + 4 个 token 缺失 + 2 个 hash/字段缺失），GREEN 后全绿。

---

## 最终提交状态

```
READY_FOR_CHATGPT_P1_ROUND_8_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
```

- 无任何 "P2 started" / "P2 ready" / "Gate passed therefore P2" 声明。
- 三个 BLOCKED（G03/G04/G10）为真实外部 blocker；P1 未通过前不做 candidate performance 承诺。
- 最终由 ChatGPT 判定 `ACCEPTED / REJECTED`；本 agent 无权自行宣布 P1 accepted 或 P2 authorized。
