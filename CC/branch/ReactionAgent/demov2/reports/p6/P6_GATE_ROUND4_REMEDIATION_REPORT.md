# P6 Gate Round 4 — 整改报告（执行者: claude-glm）

> 状态：**PASS**（G8 一行修复关闭，4/4 Round 4 针脚绿，全量终态不变）
> RED commit：`7855e66`（`tests/p6/test_gate_round4_remediation.py`，4 failed 真 RED）
> GREEN commit：`69ee487`（`_read` except 补 `TypeError`，1 行）
> 触发：kimi Gate Round 3 `P6_GATE_ROUND_3_READ_ONLY_AUDIT_FAIL`（G7 P0 闭，新增 GATE-P6-08 P1）

## 0. 结论

GATE-P6-08（P1 idem 形状不符裸泄 TypeError）一行修复落地，严格 RED→GREEN。
Round 3 的 G7 修了 `runs.get_run` 的 `from_dict` catch，但同族缺陷在相邻的
`idempotency._read` 漏网——本轮补齐。整改只在 `reaction_agent/mcp/idempotency.py`
+ `tests/p6/` + gate report 文件内，未碰 main、未碰已关闭文件。Phase A/B/Round-2/3
全零回归；新增 4 个 Round 4 针脚全绿。

## 1. GATE-P6-08 修复

| 文件 | 修复 |
|---|---|
| `idempotency.py` | `_read` 的 except 元组 `(json.JSONDecodeError, OSError, KeyError)` → `+ TypeError`。形状不符的 idem 记录（合法 JSON 非对象，如 `[1,2,3]` / `"x"`）原本 `data["key"]` 裸泄 `TypeError`，现 → typed `StorageError` |

**双路径同时关闭**：
- **replay**：`record_if_absent` 快路径 `_read` raise `StorageError`（P6Error）→ 经 `handle()` 传播，MCP server 的 P6Error-only catch 正确接住。
- **sweep**：`ResourceManager.sweep` 的 `except P6Error` 分支接住 `StorageError` → `delete(key)` 清除坏记录（G4 清理逻辑天然复用）。

## 2. 测试针脚（`tests/p6/test_gate_round4_remediation.py`，4 用例，两组）

| 组 | 覆盖 |
|---|---|
| `TestG8IdemShapeMismatchReplay`（2） | 数组 `[1,2,3]` / 字符串 `"not-an-object"` 形态 idem 文件 → replay predict typed `StorageError`（非裸 TypeError） |
| `TestG8IdemShapeMismatchSweep`（2） | 同形态 → `sweep()` 不崩 + 清除坏记录（`"t1:k1" not in list_keys()`） |

## 3. RED→GREEN 证据

```
7855e66 test(p6): Gate Round 4 RED — G8 idem shape-mismatch pins   ← 4 failed (真 RED)
69ee487 fix(p6): Gate Round 4 GREEN — G8 _read catches TypeError   ← 4/4 PASS (1 行)
```
RED 阶段 4 针脚全失败（replay 裸 TypeError、sweep 崩 TypeError）；GREEN 后 4/4 全绿。
Phase A 53 + Phase B 58 + Round 2 17 + Round 3 18 零回归（p6 = 150）。

## 4. 运行 / 全量终态

```bash
PYBIN=/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
$PYBIN -m pytest tests/p6/test_gate_round4_remediation.py -q   # 4 passed
$PYBIN -m pytest tests/p6 -q                                   # 150 passed (53+58+17+18+4)
$PYBIN -m pytest -q                                            # 1 failed, 1116 passed, 25 skipped
```
全量 **1 failed** = §17 `test_zero_skip_xfail_in_full_suite`（预期，知悉项 #26）；
**1116** = 966 基线 + 53 Phase A + 58 Phase B + 17 Round 2 + 18 Round 3 + 4 Round 4；
**25 skipped** = P5 real_snapshot 隔离。

## 5. G5 gate report 刷新

`reports/p0|p1/*GATE_REPORT*` 随本次干净全量跑刷新（timestamp 2026-08-06T11:2xZ，
P0-G10 evidence = `collected 1142, passed 1116, failed 1, skipped 25`），与本 commit 一并入库。
任何全量跑都会再生成，已在最终 commit 前最后执行。

## 6. 未做 / 边界

- 未碰 main（HEAD 仍 `4eb4633`）；未碰 T0 / Round-1~3 已关闭文件。
- GATE-P6-04（§17 collection-interrupted legacy，P1 知悉不阻塞）维持现状，留 P1 备查。
- kimi Round 3 已对 `mcp/` 全部 `json.loads`+键取位点穷尽核对（runs ✓ / idem ✓ 本轮 / 其余无此类路径）——预期无遗留同类项。

转 [@claude-kimi](mention://agent/69db06b9-8b8f-4790-ba18-fbed026f865e) Gate P6 Round 4 终审（G8 一行 + 两针脚；预期这是最后一轮，关闭即 Gate P6 PASS）。
