# Round 9 提交（P1 manifest-authority envelope 最小整改）

> **提交对象：** ChatGPT（独立只读审核）
> **性质：** P1 manifest-authority envelope 最小完整整改，不是 P2 开发
> **日期：** 2026-07-31
> **结构化证据：** `reports/p1/P1_ROUND_9_AUDIT_EVIDENCE.json`
> **工作日志：** `reports/p1/P1_REMEDIATION_WORKLOG.md`（Round 9 章节）

---

## 逐项回答（Round 9 任务书 §19 的 21 项）

1. **项目根、branch、HEAD、dirty status**
   - 项目根：`/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`
   - branch：`main`；HEAD：`4eb463368e38f2faa3d3656a05974c4b1c1211a6`（未提交）
   - dirty：dirty（Round 7 + Round 8 + Round 9 改动未提交）

2. **changed-files 与 frozen files**
   - changed：见 `P1_ROUND_9_AUDIT_EVIDENCE.json["changed_files"]`（loader、test_snapshot_nested_evidence、run_p1_gate、run_p1_mutations、P0/P1 Gate reports、mutation_results、round_9 拆分 JSON ×2、evidence、submission、worklog）
   - frozen 未改：`plan/final_design.md`、`plan/final_plan.md`、`reaction_agent/eligibility/engine.py`、`reaction_agent/schemas/*`、`reaction_agent/policies/*`、`reaction_agent/snapshot/builder.py`（本轮未改）、P0 ADRs、P0 frozen contracts、`../benchmark`、`../core`

3. **Round 8 baseline**（开工前串行冻结）：contracts 290 / P1 541 / full 831 / P0 10/10 / P1 7P·0F·3B / G08 117 / G09 21 / M1–M85 85/85；0 skip / 0 xfail / 0 xpass

4. **R9-01 pre/post**
   - pre：删除 `manifest.diagnostic_index_hash` → `accepted=true`（`.get()` 跳过缺失字段）
   - post：`accepted=false`，`SnapshotHashMismatchError`，token `manifest_required_field_missing`

5. **R9-02 pre/post**
   - pre：`manifest.diagnostic_count=999` → `accepted=true`，downstream 读到 `999`（raw manifest 直接构造返回对象）
   - post：`accepted=false`，token `manifest_count_mismatch`（从 verified records 重建比较：diagnostic_count=1）

6. **R9-03 pre/post**
   - pre：`manifest.snapshot_id=snap_forged000000` → `accepted=true`，loaded_id=snap_forged000000
   - post：`accepted=false`，token `snapshot_identity_mismatch`（snapshot_id 必须 == `"snap_"+snapshot_hash[:12]` == 目录 basename）

7. **required manifest fields**：20 个 required field（snapshot_id / schema_version / included_strict_count / conditional_count / diagnostic_count / quarantine_count / build_status / snapshot_hash / build_id / source_counts / policy_version / record_count / versions / source_files / failure_counts_by_reason / record_content_hashes / production_index_hash / diagnostic_index_hash / quarantine_index_hash / build_config_hash），缺失 → `manifest_required_field_missing`，类型错 → `manifest_field_type_invalid`，**不再用 `.get()` 跳过**

8. **identity / count / record-hash / index-hash / source-summary / failure-summary contracts**
   - identity：snapshot_hash == COMPLETE marker == recomputed canonical hash；snapshot_id == `"snap_"+hash[:12]` == 目录 basename → `snapshot_identity_mismatch`
   - counts：record_count == len(records) == 四 lane 和；每 lane count 从 verified records 重建 → `manifest_count_mismatch`
   - record-hash：manifest.record_content_hashes == sorted verified record hashes → `manifest_record_hashes_mismatch`
   - index-hash：production/diagnostic/quarantine 三值均从 verified indexes 重算比较 → `manifest_index_hash_mismatch`
   - source-summary：source_counts 总和 == record_count、键集 == records source 集合、source_files 每值重算 → `manifest_source_counts_mismatch` / `manifest_source_hash_mismatch`
   - failure-summary：从 verified diagnostic/quarantine decisions 重建 → `manifest_failure_counts_mismatch`

9. **verified returned object**：`SnapshotManifest` 全部由 `_validate_manifest_authority` 返回的 verified values 构造；`SnapshotRecord.snapshot_id` / `build_config_hash` 同用 verified 值。禁止 `SnapshotManifest(**raw_manifest_values_without_cross_verify)`

10. **G08/G09 totals**：G08 117/117（未减少）；G09 **21 → 33**，mandatory passed = 33

11. **M56h/M56i**：M56h 删除 Round 9 manifest-required-field 节点 → G09 FAIL；M56i 删除 Round 9 snapshot-identity 节点 → G09 FAIL（temp copy / finally restore，失败来自 missing mandatory node）

12. **M86/M87/M88**
    - M86 删除 manifest.diagnostic_index_hash → `manifest_required_field_missing`
    - M87a–M87d：diagnostic_count=999 / record_count=999 / source_counts 伪造 / production_index_hash 伪造 → `manifest_count_mismatch` ×2、`manifest_source_counts_mismatch`、`manifest_index_hash_mismatch`（全部真实 loader）
    - M88 snapshot_id=snap_forged000000 → `snapshot_identity_mismatch`

13. **M1–M85 preservation**：全部保留并继续 caught（无回退）

14. **final mutation total/caught**：**88/88 caught**（从 `reports/p1/mutation_results.json` 读取，非手填）

15. **contracts/P1/full counts**：contracts **290**；P1 **556**（541 + 15）；full **846**（831 + 15）

16. **zero skip/xfail/xpass**：是

17. **P0/P1 Gate matrix**：P0 **10/10 PASS**；P1 **7 PASS / 0 FAIL / 3 BLOCKED**（G01/G02/G05/G06/G07/G08/G09 PASS；G03/G04/G10 BLOCKED），overall = BLOCKED

18. **snapshot ID/hash 与 diagnostic index hash**：`snap_0672a2d6ff95` / `0672a2d6ff95c9d0bff3f72011c196c6fd01ab1b5108145ccb1d9bcc849a4a5b` / `f8d8ef5eb3a7649c7a9cc98f0b72e73fd655acd4f78863479465686d3db362cc`（与 Round 8 相同，本轮未改 builder canonical content）

19. **external blockers**：G03 `real_reaction_source_not_confirmed`；G04 `RealMapperAdapter.map_reaction()` skeleton；G10 annotator_a/b + adjudication `NOT_PRODUCED`（均为真实外部输入缺失，implementation failure = 0）

20. **deferred semantic risks**：same AddedAtomSource formal=True/False、identical MechanisticOriginEvidence with different IDs、overlapping FAT assignments —— 本轮不改，worklog 标记 `must be frozen before P4 evidence aggregation/ranking`

21. **structured evidence / worklog paths**：`reports/p1/P1_ROUND_9_AUDIT_EVIDENCE.json` / `reports/p1/P1_REMEDIATION_WORKLOG.md`（Round 9 章节）

22. **dependency/network actions**：无（未安装依赖、未联网、RDKit 2026.03.4 仅只读探测）

23. **P2 status**：**BLOCKED**（本轮未进入 P2，未生成任何 P2 performance）

---

## 补充证据（防伪）

- 三个 fail-open 的修复前/后复现均使用**真实 public `build_snapshot` + `load_snapshot`**，见 `P1_ROUND_9_AUDIT_EVIDENCE.json` 的 `R9-01/02/03_before/after`（含 fixture reaction_id、field mutated、pre/post loader result、exception type、reason token、artifacts 是否变更、snapshot hash/COMPLETE 是否变更、是否 generic hash mismatch、verified downstream value）。
- M86/M87/M88 的 evidence 均为真实 loader 抛出的 typed reason token（`manifest_required_field_missing` / `manifest_count_mismatch` / `manifest_source_counts_mismatch` / `manifest_index_hash_mismatch` / `snapshot_identity_mismatch`），非 mutation runner 自我断言。
- 本轮新增 15 个测试，其中 13 个在旧实现上真实失败（11 个 fail-open + 3 个 token 不匹配），GREEN 后全绿。
- `git diff --check` = **clean**。

---

## 最终提交状态

```
READY_FOR_CHATGPT_P1_ROUND_9_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
```

- 无任何 "P2 started" / "P2 ready" / "Gate passed therefore P2" 声明。
- 三个 BLOCKED（G03/G04/G10）为真实外部 blocker；P1 未通过前不做 candidate performance 承诺。
- 最终由 ChatGPT 判定 `ACCEPTED / REJECTED`；本 agent 无权自行宣布 P1 accepted 或 P2 authorized。
