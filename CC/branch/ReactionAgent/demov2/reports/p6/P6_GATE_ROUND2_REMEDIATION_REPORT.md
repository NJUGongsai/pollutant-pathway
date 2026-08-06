# P6 Gate Round 2 — 整改报告（执行者: claude-glm）

> 状态：**PASS**（G1–G6 全部落实，17/17 Round 2 测试绿，全量终态不变）
> RED commit：`59120a5`（`tests/p6/test_gate_round2_remediation.py`，13 failed 真 RED）
> GREEN commit：`2be752d`（G1–G6 perimeter hardening）
> 触发：kimi Gate Round 1 `P6_GATE_ROUND_1_READ_ONLY_AUDIT_FAIL`（2 P1 + 4 P2）

## 0. 结论

Gate Round 1 的 6 个 finding 全部修复，严格 RED→GREEN。整改只在 `reaction_agent/mcp/`
+ `tests/p6/` + gate report 文件内，未碰 main、未碰 T0 已关闭文件。Phase A 53 测试零回归；
Phase B 58 测试零回归；新增 17 个 Round 2 针脚全绿。

## 1. Finding → 修复 → 针脚

| Finding | 根因 | 修复 | 测试（test_gate_round2_remediation.py） |
|---|---|---|---|
| **G1 (P1)** unbound run 跨 tenant 可读 | `_authorize`/`_authorize_tenant` 仅查 `tenant_id is not None and !=`，unbound 放行 | secured 模式下 `tenant_id is None` → `ForbiddenError`（fail-closed） | `TestG1UnboundRunBypass`（4）：get_run/resolve/expand/owner 全拒 |
| **G2 (P1)** 幂等键跨 tenant 共享 | `_path(key)` 裸 key + `make_request_hash` 不含 tenant + 复用路径无 tenant 校验 | `make_request_hash(+tenant)` 混 tenant；predict/expand 用 `effective_key=f"{tenant}:{key}"`（secured）；unsecured 不变 | `TestG2IdempotencyTenantNamespace`（4）：同 key 同 payload 各自独立 run；同 key 不同 payload conflict 仅同 tenant；不复用不泄存在性 |
| **G3 (P2)** `reused` 恒 True | `"reused": rec.run_id is not None`（恒真） | `IdempotencyRecord` +`reused` 调用瞬态标志；`record_if_absent` 命中→True/新建→False；predict 响应 `rec.reused` | `TestG3ReusedField`（3）：首调 False、重复 True、异 key False |
| **G4 (P2)** sweep 僵尸 idem | sweep 只删 run 不感知 idem；重放命中旧记录→`get_run(已删)`→`RunNotFoundError` | `ResourceManager` 持有 idem store；`sweep()` 清理指向已逝 run 的 idem 记录 → 重放透明重建 | `TestG4SweepZombieIdem`（2）：sweep 后重放 rebuilt(reused=False) 非 NotFound；idem `list_keys()==[]` |
| **G6 (P2)** manifest URI 尾段宽容 | `__init__` 允许 manifest+evidence_id | `ResourceURI.__init__`：manifest+evidence_id → `ProtocolError` | `TestG6ManifestTailReject`（4）：manifest/garbage 拒、构造拒、evidence/extra 拒、manifest 无尾 OK |
| **G5 (P2)** gate report 脏态 | 全量跑再生成 | 本报告同 commit 内附干净全量跑刷新的 4 个 gate report | —（见 §3） |

## 2. 改动清单

**`reaction_agent/mcp/`**
- `idempotency.py`：`make_request_hash(+tenant)`；`IdempotencyRecord` +`reused` slot；`record_if_absent` 命中返回 `reused=True`、新建 `reused=False`；`+list_keys()`/`+delete(key)`
- `resources.py`：`_authorize` secured 模式 unbound→`ForbiddenError`；`ResourceURI.__init__` 拒 manifest+evidence_id；`ResourceManager(+idem_store)`；`sweep()` 第 3 步清理指向已逝 run 的 idem 记录
- `runs.py`：`+run_exists(run_id)`（sweep helper）
- `tools.py`：`_authorize_tenant` unbound→`ForbiddenError`；`+_effective_key(key,ctx)` tenant 命名空间；predict/expand 用 tenant-aware hash + effective_key；predict 响应 `rec.reused`
- `secured.py`：把 `idem_store` 传给 `ResourceManager`

**`tests/p6/`**
- `test_gate_round2_remediation.py`（新，17 用例，RED 先行 `59120a5`）
- `test_server_stdio.py`：predict-repeat 测试前清理 `/tmp/reaction_agent_mcp`（server.py main() 持久目录跨 session 污染，原 `assert a==b` 碰巧通过）；断言改为 run_id 相等 + reused 语义（G3 在 transport 层确定性验证）

## 3. RED→GREEN 证据

```
59120a5 test(p6): Gate Round 2 RED — G1-G6 adversarial probe pins   ← 13 failed (真 RED)
2be752d fix(p6): Gate Round 2 GREEN — G1-G6 perimeter hardening    ← 17/17 PASS
```
RED 阶段 13 个针脚失败（unbound 放行 / 跨 tenant 静默复用 / reused 恒 True / sweep 后 RunNotFoundError / manifest 尾段合法）；GREEN 后 17/17 全绿。

## 4. 运行 / 全量终态

```bash
PYBIN=/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
$PYBIN -m pytest tests/p6/test_gate_round2_remediation.py -q        # 17 passed
$PYBIN -m pytest tests/p6 -q                                       # 128 passed (53+58+17)
$PYBIN -m pytest -q                                                # 1 failed, 1094 passed, 25 skipped
```

全量 **1 failed** = `test_zero_skip_xfail_in_full_suite`（§17 零-skip 门禁，预期，知悉项 #26）。
**1094** = 966 基线 + 53 Phase A + 58 Phase B + 17 Round 2。**25 skipped** = P5 real_snapshot 隔离。

## 5. G5 gate report 刷新

`reports/p0/P0_GATE_REPORT.{json,md}`、`reports/p1/P1_GATE_REPORT.{json,md}` 随本次干净全量跑刷新
（timestamp 2026-08-06T10:3xZ，P0-G10 evidence = `collected 1120, passed 1094, failed 1, skipped 25`），
与本 commit 一并入库。任何全量跑都会再生成，故在最终 commit 前最后执行。

## 6. 未做 / 边界

- 未碰 main（HEAD 仍 `4eb4633`）；未碰 T0 已关闭文件（`tests/p5/`、baseline 文档/receipt）。
- GATE-P6-04（§17 collection-interrupted legacy，P1 知悉不阻塞 Gate）维持现状，留 P1 备查。
- external expand 仍 absent from MVP（final_plan §9.5）。

转 [@claude-kimi](mention://agent/69db06b9-8b8f-4790-ba18-fbed026f865e) Gate P6 Round 2 终审（请重点复 probe G1/G2 四个场景 + 全量终态）。
