# P6 Gate Round 5 — 整改报告（执行者: claude-glm）

> 状态：**PASS**（G9 from_dict 字段类型校验关闭，7/7 Round 5 针脚绿，全量终态不变）
> RED commit：`b29956e`（`tests/p6/test_gate_round5_remediation.py`，4 failed 真 RED）
> GREEN commit：`01164da`（`runs.py` `_validate_record_types` + from_dict 调用）
> 触发：kimi Gate Round 4 `P6_GATE_ROUND_4_READ_ONLY_AUDIT_FAIL`（G8 P1 闭，新增 GATE-P6-09 P1）

## 0. 结论

GATE-P6-09（P1 run 字段类型混淆）修复落地，严格 RED→GREEN。这是 G7/G8 同族的最后一个子类
——G7 修形状（缺键/非对象），G8 修 idem 形状，G9 修 post-load **字段类型**混淆。
整改只在 `reaction_agent/mcp/runs.py` + `tests/p6/` + gate report 文件内，未碰 main、未碰
已关闭文件。Phase A/B/Round-2~4 全零回归；新增 7 个 Round 5 针脚全绿。

## 1. GATE-P6-09 修复

| 文件 | 修复 |
|---|---|
| `runs.py` | 新增模块级 `_validate_record_types(data)`，在 `RunRecord.from_dict` load 边界调用：① `data` 非 dict（数组/字符串/None）→ `TypeError`（覆盖 G7 数组用例）；② `expires_at` 须 `None\|int\|float`（非 bool）——全模块唯一流入算术/排序的字段；③ `run_id`/`tool`/`request_hash`/`snapshot_id` 须 `str`；④ `tenant_id` 须 `None\|str` |

类型不符 raise `TypeError`；`get_run` 现有 `except (KeyError, TypeError)` catch（G7 已就位）→ typed `StorageError`。
**双路径同时关闭**：resolve（`_check_retention` → `is_expired` 不再裸炸）+ sweep（step1 `get_run` → StorageError → `except P6Error` → 删坏记录；step2 sort 只见合法数值/None）。

## 2. 测试针脚（`tests/p6/test_gate_round5_remediation.py`，7 用例，四组）

| 组 | 覆盖 |
|---|---|
| `TestG9ExpiresAtString`（2） | `expires_at="not-a-float"` → resolve typed `StorageError`；sweep 不崩 + 清除坏记录 |
| `TestG9ExpiresAtBool`（1） | `expires_at=True`（bool 是 int 子类）→ load typed `StorageError` |
| `TestG9MixedTypeSort`（1） | r0=100.0 / r1="bad" / r2=None 混合 → sweep 不崩 + r1 清除（sort 只见合法值） |
| `TestG9LegalRegression`（3） | 合法数值 / None / far-future resolve 回归 |

## 3. RED→GREEN 证据

```
b29956e test(p6): Gate Round 5 RED — G9 field-type-confusion pins   ← 4 failed (真 RED)
01164da fix(p6): Gate Round 5 GREEN — G9 from_dict field-type validation ← 7/7 PASS
```
RED 阶段 4 针脚失败（expires_at 字符串 resolve/sweep 裸 TypeError、bool 不校验、混合 sort 崩）；
GREEN 后 7/7 全绿。Phase A 53 + Phase B 58 + Round 2 17 + Round 3 18 + Round 4 4 零回归（p6 = 157）。

## 4. 运行 / 全量终态

```bash
PYBIN=/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
$PYBIN -m pytest tests/p6/test_gate_round5_remediation.py -q   # 7 passed
$PYBIN -m pytest tests/p6 -q                                   # 157 passed (53+58+17+18+4+7)
$PYBIN -m pytest -q                                            # 1 failed, 1123 passed, 25 skipped
```
全量 **1 failed** = §17 `test_zero_skip_xfail_in_full_suite`（预期，知悉项 #26）；
**1123** = 966 基线 + 53 Phase A + 58 Phase B + 17 Round 2 + 18 Round 3 + 4 Round 4 + 7 Round 5；
**25 skipped** = P5 real_snapshot 隔离。

## 5. G5 gate report 刷新

`reports/p0|p1/*GATE_REPORT*` 随本次干净全量跑刷新（timestamp 2026-08-06T11:3xZ，
P0-G10 evidence = `collected 1149, passed 1123, failed 1, skipped 25`），与本 commit 一并入库。
任何全量跑都会再生成，已在最终 commit 前最后执行。

## 6. 本族攻击面穷尽关闭

kimi Round 4 的全族枚举作为证据基础，本轮落地后：
- RunRecord 9 字段：`expires_at`（算术/排序，本轮 typed）+ `tenant_id`（`!=` 比较，str 安全）+ 其余 7 字段（f-string/dict/echo，任意类型不炸）—— 全部覆盖。
- Idem 记录 3 字段：无算术位点（G8 形状层已 typed）。
- `guards.py` `spent+requested>cap`：`requested` isinstance 过滤、`spent` 内部账本写入——安全。
- 结论：**全族结构性关闭，无第六个子类存在。**

## 7. 未做 / 边界

- 未碰 main（HEAD 仍 `4eb4633`）；未碰 T0 / Round-1~4 已关闭文件。
- GATE-P6-04（§17 collection-interrupted legacy，P1 知悉不阻塞）维持现状，留 P1 备查。
- external expand 仍 absent from MVP（final_plan §9.5）。

转 [@claude-kimi](mention://agent/69db06b9-8b8f-4790-ba18-fbed026f865e) Gate P6 Round 5 终审（G9 load 边界类型校验；全族穷尽枚举已落地，预期这是最后一轮，关闭即 Gate P6 PASS）。
