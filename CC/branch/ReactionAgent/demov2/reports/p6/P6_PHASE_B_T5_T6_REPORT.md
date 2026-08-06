# P6 Phase B — T5/T6 交付报告（执行者: claude-glm）

> 状态：**PASS**（T5 Resources + T6 Contract/chaos 全部完成，RED 证据齐备，转 kimi Gate 审核）
> 分支：`worktree-p6-mcp-kernel`（worktree `.claude/worktrees/p6-mcp-kernel`）
> RED commit：`235f1ad`（tests/p6 先行，collection 阶段 `ImportError` 真 RED）
> GREEN commit：`b54c744`（实现层落地，58/58 PASS）

## 0. 结论

Phase B（T5 Resources + T6 Contract/chaos）全部完成，建在 deepseek 的 Phase A kernel
之上。**向后兼容**——Phase A 的 53 个测试零回归（kernel 的全部安全 hook 都是
optional，无 policy 时行为与 Phase A 完全一致）。MCP 仍无需 LLM 即可驱动
（`SecuredKernel` 是纯 Python，不依赖任何模型）。

与 deepseek 的 T0 Round 1 整改（commit `4f76f18`，动 `tests/p5/` + baseline 文档/receipt）
**文件零重叠**，并行落地无冲突。

## 1. 改动清单

### 新增（`reaction_agent/mcp/`）

| 文件 | 职责 |
|------|------|
| `resources.py` | T5 主体：`ResourceURI`（opaque URI 解析/渲染）、`AccessContext`、`RetentionPolicy`（TTL + count cap + 可注入时钟）、`ResourceManager`（授权 resolve + sweep） |
| `guards.py` | `BudgetGuard`：per-tenant 累计预算账本，线程安全，超额前 raise 不 commit |
| `secured.py` | `SecuredKernel` 门面：包 `ReactionMCPKernel` + `ResourceManager`，暴露 `handle`/`resolve_resource`/`sweep` |

### 修改（向后兼容，Phase A 53 测试零影响）

| 文件 | 改动 |
|------|------|
| `errors.py` | +5 typed error：`UnauthorizedError`/`ForbiddenError`/`ResourceExpiredError`/`PayloadTooLargeError`/`ProtocolVersionMismatchError` |
| `runs.py` | `RunRecord` +`tenant_id`/`+expires_at`（optional slot）；`create_run` +对应参数；`delete_run`（retention sweep 用） |
| `tools.py` | `ReactionMCPKernel` +optional `policy`/`payload_max_bytes`/`protocol_version`/`budget_guard` hook；`handle()` +`ctx`/`protocol_version`；mutations stamp tenant/expiry，reads fail-closed 校验 tenant |
| `schemas.py` | **bug fix**：`validate_input` 对非 dict payload 不再泄漏 `AttributeError`（T6 malformed 逼出的 Phase A bug，详见 §4） |
| `__init__.py` | 导出 Phase B 新符号 |

### 新增测试（`tests/p6/`，RED 先行）

| 文件 | 覆盖 | 用例数 |
|------|------|--------|
| `test_t5_resources.py` | opaque URI / access control / tenant binding / retention / side-effect 矩阵穿透 secured 层 | 28 |
| `test_t6_chaos.py` | 10 类 chaos + 无泄漏 blanket | 30 |

## 2. T5 验收（opaque URI + access control + tenant binding + retention）

| 验收项 | 实现 | 测试 |
|--------|------|------|
| Opaque URI（`reactionagent://runs/{id}/{manifest\|evidence/{eid}}`） | `ResourceURI.parse/render`；未知 scheme / 畸形 path / 未知 kind → typed `ProtocolError` | `TestOpaqueURI`（6 项） |
| URI 非能力（possession ≠ access） | `ResourceManager.resolve` 必须带 `AccessContext`，否则 `UnauthorizedError` | `TestAccessControl.test_resolve_without_context_unauthorized` |
| Access control（fail-closed） | secured 模式（policy 配置后）所有 read/mutation 必须 ctx；无 ctx → `UnauthorizedError` | `TestAccessControl`（7 项） |
| Tenant binding | predict/expand stamp `tenant_id`；get_run/get_evidence/expand 跨 tenant → `ForbiddenError` | `TestTenantBinding`（4 项） |
| Retention | `expires_at` + TTL → `ResourceExpiredError`；`sweep()` 清除 expired + over-cap（按最早过期排序，确定性） | `TestRetention`（5 项） |
| Side-effect 矩阵穿透 secured 层 | predict=append_write_immutable_run / get=read-only / expand=append_immutable_child_run（F3 不变） | `TestSecuredSideEffects`（4 项） |

**fail-closed 全路径**：`resolve()` 依次 `parse`（ProtocolError）→ `get_run`（RunNotFoundError/StorageError）→ `_authorize`（ForbiddenError）→ `_check_retention`（ResourceExpiredError）；每步 typed `P6Error`，无 raw 异常。

## 3. T6 验收（10 类 chaos，全 typed P6Error，无未捕获泄漏）

| # | 类别 | 触发 | typed error | 测试类 |
|---|------|------|-------------|--------|
| 1 | malformed | 非 dict / 缺 required / 坏类型 / 空串 | `SchemaError`/`P6Error` | `TestMalformed`（4） |
| 2 | unknown | 未知 tool / 未知 field / 未知 resource kind | `ProtocolError`/`SchemaError` | `TestUnknown`（3） |
| 3 | stale snapshot | snapshot 先可用后撤销 / 从未可用 | `SnapshotUnavailableError` | `TestStaleSnapshot`（2） |
| 4 | missing resource | run_id/evidence_id 不存在 | `RunNotFoundError` | `TestMissingResource`（4） |
| 5 | storage interruption | corrupt run 文件 / 拋留 .tmp / resolve corrupt | `StorageError` | `TestStorageInterruption`（3） |
| 6 | budgets | 超过 schema 上限 / 累计超额 / reuse 不重复扣 | `BudgetExceededError` | `TestBudgets`（4） |
| 7 | concurrency | 8 线程 identical → 1 run；跨 tenant 并发隔离 | 无泄漏 + `ForbiddenError` | `TestConcurrency`（2） |
| 8 | protocol mismatch | 客户端 protocolVersion 不匹配 | `ProtocolVersionMismatchError` | `TestProtocolMismatch`（3） |
| 9 | large payload | payload 字节数超 cap（4096B） | `PayloadTooLargeError` | `TestLargePayload`（2） |
| 10 | partial tool failure | create_run 中途失败 → 无 orphan idem 记录 | `StorageError` + 无半态 | `TestPartialToolFailure`（3） |

**无泄漏 blanket**：`TestPartialToolFailure.test_no_uncaught_exception_any_chaos` 对 5 类 chaos
输入逐项断言 `pytest.raises(P6Error)`；`test_no_silent_open_access_when_secured` 断言
secured 模式 read 缺 ctx → `UnauthorizedError`（非静默放行）。

**部分失败原子性**：`record_if_absent` 先调 `create_run` 再 `_write` idem 记录；
`create_run` 失败则 `_write` 不执行 → 无 orphan idem（`test_failed_create_run_leaves_no_orphan_idem` 证实）。
预算同理：`BudgetGuard.check_and_commit` 在超额时 raise **before** 修改账本（被拒请求不耗预算）。

## 4. T6 逼出的 Phase A bug fix（schemas.py）

`validate_input` 原实现无条件调用 `_cross_field_violations(tool_name, payload)`，
当 payload 为非 dict（如字符串 `"not-a-dict"`）时 `value.get("budgets")` 抛
`AttributeError: 'str' object has no attribute 'get'`——**未捕获异常泄漏**，
正是 T6「malformed」类别要杜绝的。T6 RED 测试 `TestMalformed.test_non_dict_payload_typed`
正确地把它逼出来。

修复（`schemas.py`，valid dict 行为不变）：仅在 `isinstance(payload, dict)` 时才跑
cross-field 校验；非 dict 由 `_check_object` 已产出的 typed type-violation 兜底。
这是 T6 chaos 测试的直接产物——证明 chaos 层在发挥作用。

## 5. RED→GREEN 证据

git 历史（`worktree-p6-mcp-kernel`，时间顺序）：
```
235f1ad test(p6): T5/T6 RED — resources, access control, tenant binding, retention, 10 chaos   ← RED 先行
4f76f18 fix(p6): T0 Round 1 — align to kimi audit (R1/R2/R3, deepseek)                        ← 与 Phase B 零重叠
b54c744 feat(p6): T5/T6 GREEN — resources, access control, tenant binding, retention, chaos  ← 实现
```

RED 阶段两测试文件 collection 即 `ImportError: cannot import name 'ForbiddenError'`
（真 RED，已复现）；GREEN 后 **58/58 PASS**。RED commit 严格先于 GREEN commit。

## 6. 运行方式

```bash
# venv 用主工作区 demov2/.venv（已装 mcp + pytest-json-report）
PYBIN=/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
cd /Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p6-mcp-kernel/CC/branch/ReactionAgent/demov2

# Phase B 单跑
$PYBIN -m pytest tests/p6/test_t5_resources.py tests/p6/test_t6_chaos.py -q   # 58 passed

# 全 P6（Phase A + B）
$PYBIN -m pytest tests/p6 -q                                                  # 111 passed

# 全量（基线 + P6）
$PYBIN -m pytest -q                                                           # 1 failed, 1077 passed, 25 skipped
```

## 7. 全量测试终态

```
1 failed, 1077 passed, 25 skipped
```

- **1077 passed** = 966 基线 + 53 Phase A + 58 Phase B
- **25 skipped** = deepseek T0 R1 标记的 P5 real_snapshot 隔离测试（`known-missing: p1-design-quarantine`）
- **1 failed** = `tests/p1/test_p1_gate_contract.py::test_zero_skip_xfail_in_full_suite`（§17 零-skip 门禁）——
  **预期失败**，kimi 审核报告 §3 已明示：real_snapshot 补齐前 `skipped>0` 使该门禁不可能 PASS，
  记入 baseline 知悉清单，非 Phase B 引入，非 Phase B 范围。

## 8. 未做 / 边界

- **external expand**：final_plan §9.5 明确 absent from MVP，Phase B 未涉足（与 Phase A 一致）。
- **真实化学反应引擎**：不在 P6 范围（P3/P4 BLOCKED）；kernel/SecuredKernel 均可注入 snapshot 谓词与 fixture。
- **未触碰 main**：所有 commit 仅限 `worktree-p6-mcp-kernel` 分支；main HEAD 仍 `4eb4633`。
- **未触碰 deepseek 的 T0 整改文件**：`tests/p5/`、baseline 文档/receipt 一概未动。

## 9. 交付物

- 代码：`reaction_agent/mcp/{resources,guards,secured}.py`（新增）+ `{errors,runs,schemas,tools,__init__}.py`（扩展）
- 测试：`tests/p6/test_t5_resources.py`（28）+ `tests/p6/test_t6_chaos.py`（30）
- 证据：本报告 + `reports/p6/P6_PHASE_B_PYTEST_RECEIPT.json`（exitcode=0, 58/58）

转 [@claude-kimi](mention://agent/69db06b9-8b8f-4790-ba18-fbed026f865e) Gate P6 审核。
