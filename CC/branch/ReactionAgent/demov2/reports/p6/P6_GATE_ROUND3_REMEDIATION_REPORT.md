# P6 Gate Round 3 — 整改报告（执行者: claude-glm）

> 状态：**PASS**（G7 三层修复完成，18/18 Round 3 针脚绿，全量终态不变）
> RED commit：`8f79200`（`tests/p6/test_gate_round3_remediation.py`，15 failed 真 RED）
> GREEN commit：`80ca81e`（G7 path sanitization，3 层）
> 触发：kimi Gate Round 2 `P6_GATE_ROUND_2_READ_ONLY_AUDIT_FAIL`（G1–G6 全闭，新增 GATE-P6-07 P0）

## 0. 结论

GATE-P6-07（P0 路径穿越）三层修复全部落地，严格 RED→GREEN。整改只在
`reaction_agent/mcp/` + `tests/p6/` + gate report 文件内，未碰 main、未碰 T0/Round-2
已关闭文件。Phase A 53 + Phase B 58 + Round 2 17 零回归；新增 18 个 Round 3 针脚全绿。

## 1. GATE-P6-07 三层修复

| 层 | 文件 | 修复 |
|---|---|---|
| **1. schema** | `schemas.py` | `IDENT_PATTERN = ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$` 加到 `run_id`/`evidence_id`/`idempotency_key`/`snapshot_id`/`client_request_id`；`_check_object` string 分支加 `re.fullmatch(pattern, val)`。`substrate_smiles` 故意不加（SMILES 语法含 `/`，且不进文件路径）。golden schema 自动同步（引用 `MCP_TOOL_SCHEMAS`） |
| **2. store containment** | `runs.py`/`idempotency.py` | `_run_path`/`_path` 对 `(root / f"{id}.json").resolve()` 做 `relative_to(root.resolve())` 校验，逃逸 → typed `StorageError`（不依赖 schema，防内部调用方） |
| **3. parse** | `runs.py` | `get_run` 把 `RunRecord.from_dict(data)` 包进 `try/except (KeyError, TypeError)` → typed `StorageError`；杜绝裸 `KeyError('run_id')` 泄漏 |
| **AccessContext** | `resources.py` | `tenant_id` + `principal` 加 `_IDENT_RE.fullmatch`（`tenant_id` 进 `effective_key` → 文件名）；非法 → `UnauthorizedError` |

## 2. 测试针脚（`tests/p6/test_gate_round3_remediation.py`，18 用例，四组）

| 组 | 类 | 覆盖 |
|---|---|---|
| 读穿越 | `TestReadTraversal`（2） | `get_run("../foreign")` → `StorageError`；植入形状不符 JSON → `StorageError`（非裸 `KeyError`） |
| 写穿越 | `TestWriteTraversal`（5） | `idem.record("../escaped")` → `StorageError` + 无文件逃逸；predict `idempotency_key`/`snapshot_id`/`run_id` 含 `../` → `SchemaError` |
| 形状不符 | `TestShapeMismatch`（3） | root 内 `{}` / 缺字段 / JSON 数组（TypeError） → `StorageError` |
| 合法回归 | `TestLegalIdentifiersRegression`（3） | `k-1.abc`/`snap_2`/dotted run_id 仍工作；`AccessContext(tenant_id="tenant_a.b")` 合法 |
| AccessContext | `TestAccessContextSanitization`（5） | `../etc`/`t/x`/`t\x`/`.hidden`/`../p` 全 → `UnauthorizedError` |

## 3. RED→GREEN 证据

```
8f79200 test(p6): Gate Round 3 RED — G7 path-traversal pins    ← 15 failed (真 RED)
80ca81e fix(p6): Gate Round 3 GREEN — G7 path sanitization     ← 18/18 PASS
```
RED 阶段 15 针脚失败（读穿越 RunNotFoundError/裸 KeyError、写穿越成功逃逸、形状不符裸 KeyError、schema 不拒 `../x`、AccessContext 接受 `../etc`）；GREEN 后 18/18 全绿。Phase A/B/Round-2 零回归。

## 4. 运行 / 全量终态

```bash
PYBIN=/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
$PYBIN -m pytest tests/p6/test_gate_round3_remediation.py -q   # 18 passed
$PYBIN -m pytest tests/p6 -q                                   # 146 passed (53+58+17+18)
$PYBIN -m pytest -q                                            # 1 failed, 1112 passed, 25 skipped
```
全量 **1 failed** = §17 `test_zero_skip_xfail_in_full_suite`（预期，知悉项 #26）；
**1112** = 966 基线 + 53 Phase A + 58 Phase B + 17 Round 2 + 18 Round 3；
**25 skipped** = P5 real_snapshot 隔离。

## 5. G5 gate report 刷新

`reports/p0|p1/*GATE_REPORT*` 随本次干净全量跑刷新（timestamp 2026-08-06T10:5xZ，
P0-G10 evidence = `collected 1138, passed 1112, failed 1, skipped 25`），与本 commit 一并入库。
任何全量跑都会再生成，已在最终 commit 前最后执行。

## 6. 未做 / 边界

- 未碰 main（HEAD 仍 `4eb4633`）；未碰 T0 / Round-2 已关闭文件。
- GATE-P6-04（§17 collection-interrupted legacy，P1 知悉不阻塞）维持现状，留 P1 备查。
- external expand 仍 absent from MVP（final_plan §9.5）。

转 [@claude-kimi](mention://agent/69db06b9-8b8f-4790-ba18-fbed026f865e) Gate P6 Round 3 终审（请复跑全部历史 probe + 新穿越场景，含 schema/store/parse 三层）。
