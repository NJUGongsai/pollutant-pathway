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

## 0.1 T0 CC 决策（方案 A）落实 — 26 个已知失败 + §17 放宽

CC 决策（issue 内 `b510742b`）与 kimi 验收追加（`7fadc47f`）已并入 T0，三项全部落实：

### T0-① 基线固化：26 个已知失败如实记录并归因

worktree baseline 的 `pytest` 结果为 **26 个已知失败（4 failed + 22 errors）**，
全部归因 **`real_snapshot 缺失（P1 设计隔离）`**，性质为**知悉项（baseline
acknowledged item）**，非 P6 Gate 缺陷：

| 类别 | 数量 | 归因/证据 |
|------|------|-----------|
| 22 errors | 22 | `tests/p5/test_p5_real_data.py` 模块级 `p1_data` fixture 依赖 `reports/p1/real_snapshot/`，该目录因 P1 对 3 条 proline/2OG 案例 atom-mapping 质量不达标（`mapped_heavy_atom_fraction=0.4`）全部 quarantine、从未生成。证据：`reports/p1/required_case_quarantine_evidence.json`（status=`REQUIRED_CASES_EXPLICITLY_QUARANTINED`） |
| 4 failed | 4 | ① `test_zero_skip_xfail_in_full_suite`（§17 门，因套件存在失败而红，非 real_snapshot 直接依赖）；②③ `test_p5_gate_overwrite_guard.py` 两个用例（`_load_all()`→`load_real_p1_snapshot()`，实时依赖 real_snapshot）；④ `test_real_chain_ready`（P2/P3/P4 上游缺失，是 real_snapshot 隔离的下游后果） |

> 证据链核实（CC 实地核查）：真实数据源 `data/rxn2enzyme_positives.pkl`（3601 条）
> + `reacting_center.pkl`（4541 条）存在且有效；P1 G03 定位 3 条真实 proline/2OG 反应，
> 但 atom-mapping 质量不达标，按 P1 "The builder does not fabricate real data"
> (fail-closed) 全部 quarantine，real_snapshot 从未生成。

### T0-② P5 测试标记：已知缺失 → 显式 skip + 精确 reason

依赖 real_snapshot 的 P5 测试全部标记 `skip`，reason **逐字等于**
`known-missing: p1-design-quarantine (see required_case_quarantine_evidence.json)`：

| 文件 | 标记 |
|------|------|
| `tests/p5/test_p5_real_data.py` | 模块级 `pytestmark = pytest.mark.skip(reason=KNOWN_MISSING_REASON)`（23 用例） |
| `tests/p5/test_p5_gate_overwrite_guard.py` | `test_rank_layer_unavailable_without_crash`、`test_rank_layer_available_with_real_gate` 两个方法级 skip（`test_real_gate_report_is_14_14` 不依赖 real_snapshot，保持运行） |

无静默跳过：每个 skip 都带精确 reason；reason 字符串经运行期断言逐字核对通过。

### T0-③ 51 vs 26 差异排查：已修复（sibling benchmark/core 拷贝）

T0 基线固化时，除 demov2 磁盘现状外，把未跟踪兄弟目录 `benchmark/`、`core/`、
`docs/`、`reports/` 一并拷入 worktree（`tests/p5/test_p5_real_data.py` 与
`reaction_agent/roles/cofactors.py` 通过 `../benchmark/canonical_identity.py` 读取
兄弟目录）。修复后 worktree 失败数由 51 降至与源工作区一致（26），仅有的差异已归因
（sibling benchmark 是真实拷贝问题，与 real_snapshot 无关）。

### §17 不变式放宽（与 CC 决策对齐）

`test_p1_gate_contract.py::test_zero_skip_xfail_in_full_suite` 由"零 skip 硬断言"
改为"**允许携带精确 known-missing reason 的 skip，拒绝静默 skip / 其他 reason**"
（新增 `_assert_skips_all_documented` 帮助函数）。这既保留 §17 反伪造意图
（静默跳过/伪造 PASS 仍 FAIL），又对齐 CC 决策允许的 documented quarantine skip。

### T0 落实后的套件状态

```
1020 passed, 25 skipped, 0 failed, 0 errors
```
- 26 个已知失败中：22 errors + 2 real_snapshot failures → 25 documented skips；
  `test_zero_skip_xfail_in_full_suite` 经 §17 放宽后通过；`test_real_gate_report_is_14_14`
  不依赖 real_snapshot 保持通过。
- **main 零改动**（HEAD 仍 `4eb4633`）；源工作区未动（仍为原始 26 失败状态）。

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