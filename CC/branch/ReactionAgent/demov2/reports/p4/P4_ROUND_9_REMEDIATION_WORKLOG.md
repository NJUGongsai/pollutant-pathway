# P4 Round 9 — Remediation Worklog（真实数据接入）

**Date:** 2026-08-06
**Task:** `P4_ROUND9_SUBMIT_TASK.md` — 全量验证 → 提交材料 → kimi Round 9 复审
**详细 real-data 接入日志：** `REAL_DATA_INTEGRATION_WORKLOG.md`（P1→P2→P3→P4 每段 RED→GREEN 证据）

---

## 1. 本轮目标

Round 8 kimi 裁决 BLOCKED（P4-R6-01：G12/G13/G14 real-input 证据缺失，synthetic-only；验证重放自述跳过；回归矩阵表截断）。本轮以真实数据接入关闭 P4-R6-01，并全量实测验证。

## 2. 执行记录（§二 全量验证，全部实际运行）

| # | 命令 | exit | 结果 |
|---|---|---|---|
| 1 | `pytest -q -p no:cacheprovider tests/p4` | 0 | **287 passed** |
| 2 | `pytest -q -p no:cacheprovider tests/contracts` | 0 | **290 passed** |
| 3 | `pytest -q -p no:cacheprovider tests/p4 tests/contracts` | 0 | **577 passed** |
| 4 | `python -m scripts.run_p4_mutations` | 0 | **14/14 CAUGHT** |
| 5 | `python scripts/run_p4_round4_probes.py` | 0 | **12/12 rejected** |
| 6 | `python scripts/run_p4_round5_probe_a.py` | 0 | forged_passes=false ×2，probe_run_accepted=true |
| 7 | `python scripts/run_p4_gate_real.py` | **0** | **G01-G14 全 PASS，READY_FOR_CHATGPT_P4_READ_ONLY_AUDIT** |

## 3. 真实数据接入链（与 REAL_DATA_INTEGRATION_WORKLOG.md 一致）

- **P1**：`scripts/build_real_snapshot.py` → `snap_19caddc6b312`（50 条 audited Rhea，7 fully_mapped / 43 partial）
- **P2**（P2 worktree）：`scripts/build_real_mini_benchmark.py` + `run_real_p2_gate.py` → P2 Gate 8/8 PASS receipt（READY_FOR_CHATGPT_P2_AUDIT）
- **P3**（P3 worktree）：`build_real_train_view.py` + `run_real_kernel.py` + `produce_current_run_artifact.py` → `current_run_artifact.json`（real, completed, 1 candidate）
- **P4**：`scripts/run_p4_gate_real.py`（collector）→ 注册 P1/P2 receipts → 同进程 gate → **G12/G13/G14 PASS**

## 4. 关键设计决策

1. **receipt re-bind**：P1/P2 receipts 必须匹配 bundle namespace（run_id/case_id/query_id/fold_id/snapshot_id/snapshot_hash/artifact_root），receipt_hash 按 `load_p1_receipt`/`load_p2_receipt` consumer shape 精确重算；
2. **registry 注册**：`PRODUCTION_ISSUANCE_REGISTRY` + `PRODUCTION_GATE_EXECUTION_REGISTRY`（opaque capability），同进程跑 gate 使注册立即可验证；
3. **P3 kernel real gate**：只要求实际依赖的 4 个 capability（chemistry/explicit_map/real_snapshot/automatic_donor），与 P4 契约一致，strict_mapper 属未接线未来能力；
4. **P2 authority 更新**：`ACCEPTED_P1_SNAPSHOT_HASH` 更新为真实 snapshot hash（authority 更新，非放宽逻辑）。

## 5. 红线遵守

- 未改 frozen / 上游合同 / P0 ADR / final_design / final_plan
- 未伪造 real（50 条全真实 Rhea + audited）
- 未放宽 gate 逻辑
- 未改原始 pkl（只读）
- 未 commit / push / merge

## 6. 产物清单（本轮）

| 文件 | 说明 |
|---|---|
| `reports/p4/SUBMISSION_TO_CHATGPT_P4_ROUND_9.md` | Round 9 提交材料 |
| `reports/p4/P4_ROUND_9_REMEDIATION_WORKLOG.md` | 本文件 |
| `reports/p4/INDEPENDENT_VERIFICATION_PACKET_R9.md` | 独立验证包（Probe A/B + 真实 gate 证据） |
| `reports/p4/P4_GATE_REPORT.json` / `.md` | gate 完整逐项（G01-G14 全 PASS） |
| `reports/p4/REAL_DATA_INTEGRATION_WORKLOG.md` | 真实数据接入详细日志 |