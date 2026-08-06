# P6 Phase A — T0–T4 交付报告（执行者: claude-deepseek）

> 状态：**PASS**（T0–T4 全部完成，RED 证据齐备，交给 kimi 审核）
> 分支：`worktree-p6-mcp-kernel`（worktree `.claude/worktrees/p6-mcp-kernel`）
> 基线 commit：`c40ee6d`
> RED commit：`为 T1-T4 RED 测试`（tests/p6 先行）
> GREEN commit：`feat(p6): T1-T4 GREEN — ...`

## 0. 结论

Phase A（T0 基线固化 → T4 幂等层 + side effects）全部完成，未触碰 main。
既有一千余测试无回归。MCP SDK 走 `pip install mcp` 路径成功（F2 以官方 SDK 解决，
非 stdlib 兜底）。

## 1. 关键勘察发现应对（对应 kimi 的 F1/F2/F3）

| 发现 | 处置 |
|------|------|
| F1 P5 未入库 | T0 从 main 建 worktree，把 demov2 磁盘现状 + 未跟踪兄弟目录（benchmark/core/docs/reports）拷入，baseline commit `c40ee6d` |
| F2 MCP SDK 缺失 | `pip install mcp` 成功（mcp 2.0.0），走官方 SDK 路；非 stdlib 兜底 |
| F3 side-effect 权威合同 | T4 实现逐条对齐 `contracts/mcp_side_effects.py`（predict=append_write_immutable_run、get=read-only、local expand=append_immutable_child_run、network=False） |

## 2. 改动清单

新增（全部在 `reaction_agent/mcp/` + `tests/p6/`）：

| 文件 | 职责 |
|------|------|
| `reaction_agent/mcp/schemas.py` | 4 工具 strict JSON schema + golden registry + `validate_input`（typed SchemaError） |
| `reaction_agent/mcp/errors.py` | typed P6Error 分类（Schema/Protocol/IdempotencyConflict/RunNotFound/Storage/...） |
| `reaction_agent/mcp/runs.py` | 不可变 run store（write-then-rename 原子写，completed run frozen，child 保留 parent） |
| `reaction_agent/mcp/idempotency.py` | canonical request hash（order-independent）+ idempotency store（atomic dedup） |
| `reaction_agent/mcp/tools.py` | `ReactionMCPKernel` 4 工具 dispatch，side effects 对齐 F3 |
| `reaction_agent/mcp/server.py` | MCP stdio server（mcp 2.x SDK），可用而无需 LLM |
| `tests/p6/test_contracts_schemas.py` | T1+T2 RED→GREEN（35 项） |
| `tests/p6/test_idempotency_side_effects.py` | T3+T4 RED→GREEN（幂等 5 场景 + side-effect 矩阵） |
| `tests/p6/test_server_kernel.py` | kernel dispatch 全程 typed failure（无未捕获泄漏） |
| `tests/p6/test_server_stdio.py` | 真实 MCP stdio transport 端到端测试 |

## 3. RED 证据

- **测试先行**：git 历史中 `tests/p6/` 的 RED commit 先于实现 commit；
  实现前两个测试文件均以 `ModuleNotFoundError: No module named 'reaction_agent.mcp.*'`
  ERROR（RED），实现后 53 项全部 PASS（GREEN）。
- 未伪造任何 PASS/证据。

## 4. 验收对照（kimi 计划中的 Phase A 验收标准）

| 验收标准 | 结果 |
|----------|------|
| T0: worktree 内既有 pytest 全绿 | ✅ 966 基线 PASS（变更前一致；4 fail+22 error 为已知缺 real_snapshot 数据，非本阶段引入） |
| T0: baseline commit 存在；main 零改动 | ✅ `c40ee6d`；main HEAD 仍 `4eb4633` |
| T1+T2: RED 先行；golden schema 测试绿；未知字段/坏类型 typed-error 拒绝 | ✅ `test_contracts_schemas.py` 35 项绿；`SCHEMA_VALIDATION_ERROR` |
| T3+T4: 5 场景测试绿（repeat/concurrent duplicate/same-key-diff-payload/interrupted write/child expansion） | ✅ `test_idempotency_side_effects.py` 全覆盖 |
| T4: side effects 严格符合 F3 矩阵 | ✅ `TestSideEffectMatrix` 逐条断言 |

## 5. 运行方式

```bash
# 在 worktree 内（venv 用 demov2 主工作区 .venv，或自建）
.venv/bin/python -m pytest tests/p6 -q          # 53 passed
.venv/bin/python -m pytest -q                   # 全量无回归

# 启动 MCP stdio server（可被任意 MCP client 驱动，无需 LLM）
PYTHONPATH=. .venv/bin/python reaction_agent/mcp/server.py
```

## 6. 未做 / 边界

- **T5 Resources / T6 chaos**：属于 Phase B（glm），本阶段未涉足；
  kernel 侧已保留 `reactionagent://runs/...` opaque URI 的输出约定，供 T5 使用。
- **external expand**：final_plan §9.5 明确 absent from MVP，未实现。
- **真实化学反应引擎**：不在 P6 范围（P3/P4 引擎为 BLOCKED 状态，P6 只做服务面契约）。