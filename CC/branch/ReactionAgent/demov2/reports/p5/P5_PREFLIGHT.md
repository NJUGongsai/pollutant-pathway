# P5 Preflight

**Timestamp:** 2026-08-06（真实数据接入后）
**Schema version:** p5-1
**Project root:** `/Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2`

## Environment

| Check | Status |
|-------|--------|
| Python | 3.11.15（anaconda3） |
| pydantic | 2.13.4 |
| RDKit | Available（2026.03.4） |
| Git branch | worktree-p4-strict-kernel |

## Upstream status（真实链）

| Phase | Status | Evidence |
|-------|--------|----------|
| P1 | **real snapshot** `snap_19caddc6b312`（50 audited Rhea cases） | `reports/p1/real_snapshot/` |
| P2 | **READY**（truth 50 + split 30/10/10, fold_real_0） | `reports/p2/truth_records.json` + `split_manifest.json` |
| P3 | **READY**（real kernel, 1 strict candidate） | `reports/p3/current_run_artifact.json` |
| P4 | **READY**（14/14 gate PASS） | `reports/p4/P4_GATE_REPORT.json` |

## Constraints

- 无网络 / 无安装 / 无 commit / 无 push / 无 merge
- 不伪造 real（synthetic 不重标 real）
- 不修改上游 authority（P1-P4 只读消费）

## JSON authority

`P5_PREFLIGHT.json` 是 authority；本 Markdown 由其渲染。