# P1 Round 10 — Task C：集成验收、证据与提交

> 执行角色：只读 integrator / evidence agent  
> 项目根目录：`/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`  
> 前置依赖：Task A 和 Task B 均必须 READY  
> 执行顺序：A → B → C  
> 本任务性质：独立验收并生成 Round 10 正式提交，不承担 implementation 修复

---

## 1. 核心原则

本 agent 不得因为 A/B 自报 PASS 就复制数字。必须重新运行关键命令，并从真实输出和 JSON 产物生成最终 evidence。

若发现任何 implementation failure：

1. 不修改 loader、tests、Gate 或 mutation runner；
2. 在 integration report 中准确记录；
3. submission 状态写 NOT_READY；
4. 返回给对应 Task A/B agent 修复；
5. 不得宣布 P1、Round 10 或 P2 通过。

---

## 2. 开始前必须阅读

完整阅读：

1. `reports/p1/CHATGPT_P1_ROUND_10_TASK_A_MANIFEST_CORE.md`
2. `reports/p1/ROUND_10_TASK_A_HANDOFF.md`
3. `reports/p1/CHATGPT_P1_ROUND_10_TASK_B_GATE_MUTATIONS.md`
4. `reports/p1/ROUND_10_TASK_B_HANDOFF.md`
5. `reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_9.md`
6. `reports/p1/P1_ROUND_9_AUDIT_EVIDENCE.json`
7. `reports/p1/manifest_type_authority_results_round_10.json`
8. `reports/p1/gate_false_positive_mutation_results_round_10.json`
9. `reaction_agent/snapshot/loader.py`
10. `tests/p1/test_manifest_authority_type_integrity.py`
11. `scripts/run_p1_gate.py`
12. `scripts/run_p1_mutations.py`
13. `reports/p1/P1_GATE_REPORT.json`
14. `reports/p1/mutation_results.json`

检查 branch、HEAD、dirty status 和 changed-files。不得 reset、checkout、清理用户改动或安装依赖。

---

## 3. 本 agent 的文件所有权

允许修改/生成：

```text
reports/p1/P1_REMEDIATION_WORKLOG.md              # 只追加 Round 10 章节
reports/p1/P1_ROUND_10_AUDIT_EVIDENCE.json        # 新建
reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_10.md    # 新建
reports/p1/ROUND_10_INTEGRATION_RESULTS.json       # 新建
```

运行官方 Gate 后自然刷新的派生报告允许保留。

禁止修改：

```text
reaction_agent/**
tests/**
scripts/**
plan/final_design.md
plan/final_plan.md
P0 ADRs/contracts
Task A/Task B handoff
Task A/Task B split evidence
../benchmark
../core
```

如果实现有问题，退回 A/B，不得越权修复。

---

## 4. 独立回归

必须串行运行并记录 exit code、passed/failed/skipped/xfail/xpass：

```bash
.venv/bin/python -m pytest -q tests/p1/test_manifest_authority_type_integrity.py
.venv/bin/python -m pytest -q tests/p1/test_snapshot_nested_evidence.py tests/p1/test_snapshot_builder.py tests/p1/test_snapshot_complete_evidence.py
.venv/bin/python -m pytest -q tests/contracts
.venv/bin/python -m pytest -q tests/p1
.venv/bin/python -m pytest -q
.venv/bin/python scripts/run_p0_gate.py
.venv/bin/python scripts/run_p1_gate.py
.venv/bin/python scripts/run_p1_mutations.py
git diff --check
```

不得并行运行会写相同报告文件的 Gate/mutation 命令。

预期关系，不得手填具体最终数字：

```text
contracts >= 290
P1 > 556
full = contracts + P1
P0 Gate = 10/10 PASS
P1 Gate = 7 PASS / 0 FAIL / 3 BLOCKED
G08 = 117/117
G09 mandatory total > 33 and all passed
mutations = 91/91 caught
0 skip / 0 xfail / 0 xpass
```

若真实数字不满足，submission 必须 NOT_READY。

---

## 5. 必须独立重做的攻击探针

不能只调用已有 mutation runner。使用临时目录、真实 public `build_snapshot` 和 `load_snapshot`，独立复现：

```text
IC-01 record_count=true
      → SnapshotHashMismatchError
      → manifest_field_type_invalid

IC-02 failure_counts_by_reason count=true
      → SnapshotHashMismatchError
      → manifest_field_type_invalid

IC-03 failure_counts_by_reason count=1.0
      → SnapshotHashMismatchError
      → manifest_field_type_invalid

IC-04 missing build_status
      → SnapshotHashMismatchError
      → manifest_required_field_missing

IC-05 build_status=true
      → SnapshotHashMismatchError
      → manifest_field_type_invalid

IC-06 build_status="partial"
      → SnapshotIncompleteError

IC-07 included_strict_count=true
      → SnapshotHashMismatchError
      → manifest_field_type_invalid

IC-08 legal all-four-lanes snapshot
      → load succeeds
      → returned counts/source_counts equal independently rebuilt values
```

每个探针必须记录：

```text
fixture reaction IDs
field/value mutated
pre-mutation load result
post-mutation load result
exception type
reason token
records/index/hash/COMPLETE changed flags
accepted true/false
```

临时探针文件执行后必须移除；不得污染正式 tests。

---

## 6. 证据一致性检查

逐项确认：

1. A/B handoff 的 changed-files 与 git diff 一致；
2. frozen files 未因 Round 10 改动；
3. Gate mandatory totals 来自 P1 Gate JSON；
4. mutation totals 来自 mutation_results JSON；
5. split JSON 与总 mutation JSON 一致；
6. submission 数字与 structured evidence 一致；
7. synthetic fixtures 明确标记，不冒充 real reaction source；
8. G03/G04/G10 仍是 external blockers，而非被伪造为 PASS；
9. P2 没有实现、performance 或 PASS 声明；
10. 没有依赖安装或联网行为；
11. `git diff --check` clean；
12. 所有测试为零 skip/xfail/xpass。

---

## 7. Integration results

生成：

```text
reports/p1/ROUND_10_INTEGRATION_RESULTS.json
```

最低字段：

```json
{
  "round": 10,
  "task_a_ready": true,
  "task_b_ready": true,
  "independent_probes": [],
  "test_counts": {},
  "p0_gate": {},
  "p1_gate": {},
  "g08": {},
  "g09": {},
  "mutations": {},
  "implementation_failures": [],
  "external_blockers": {},
  "ready_for_chatgpt_audit": false,
  "p2_status": "BLOCKED"
}
```

`ready_for_chatgpt_audit` 只能由真实验收结果决定。

---

## 8. Worklog Round 10

只在 `P1_REMEDIATION_WORKLOG.md` 末尾追加 Round 10，至少记录：

1. Round 9 审核拒绝原因；
2. A/B/C 分工与文件所有权；
3. RED→GREEN；
4. exact type 与 nested shape contract；
5. build_status 顺序；
6. reconstructed return contract；
7. G09 expansion；
8. M56j–M56l；
9. M89–M91；
10. 独立 IC-01–IC-08；
11. 完整回归；
12. P0/P1 Gate；
13. external blockers；
14. dependency/network actions；
15. frozen-file check；
16. P2 BLOCKED。

不得重写以前 Round 的日志。

---

## 9. Structured evidence

生成：

```text
reports/p1/P1_ROUND_10_AUDIT_EVIDENCE.json
```

至少包含：

```text
round/branch/head/working_tree
task_a_handoff/task_b_handoff
changed_files/unchanged_frozen_files
round9_baseline_counts
round10_final_counts
required_fields_and_exact_types
nested_shape_contract
verified_return_sources
IC-01..IC-08
G08/G09 previous/final totals
M56j/M56k/M56l
M1-M88 preservation
M89/M90/M91
mutation total/caught
P0 Gate/P1 Gate matrix
zero skip/xfail/xpass
external blockers
dependency/network actions
p2_status
```

所有数字必须与实际产物一致。

---

## 10. Round 10 submission

仅当无 implementation failure 时生成 READY submission：

```text
reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_10.md
```

submission 应简洁，逐项回答：

1. branch/HEAD/dirty status；
2. changed files 与 frozen files；
3. Round 9 基线；
4. 两个真实 fail-open 的 pre/post；
5. build_status error taxonomy；
6. exact primitive 和 nested shape contract；
7. reconstructed return values；
8. 新测试与实际 RED/GREEN；
9. G08/G09 totals；
10. M56j–M56l；
11. M89–M91；
12. M1–M88 preservation；
13. contracts/P1/full counts；
14. P0/P1 Gate matrix；
15. IC-01–IC-08；
16. external blockers；
17. dependency/network actions；
18. evidence/worklog paths；
19. P2 status。

成功时文件最后两行必须严格为：

```text
READY_FOR_CHATGPT_P1_ROUND_10_READ_ONLY_AUDIT

P2 BLOCKED pending ChatGPT re-audit
```

如果任何 implementation check 失败，结尾必须改为：

```text
NOT_READY_FOR_CHATGPT_P1_ROUND_10_AUDIT

P2 BLOCKED
```

不得自行宣布 ChatGPT accepted、P1 PASS 或 P2 authorized。

