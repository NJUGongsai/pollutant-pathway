# Orchestra DeepSeek live-dispatch repair — independent read-only audit

审计日期：2026-08-03（Asia/Shanghai）  
审计对象：`/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl`  
独立证据：`/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/ORCHESTRA_DEEPSEEK_REPAIR_READ_ONLY_AUDIT_EVIDENCE_2026-08-03.json`

## 裁决

本修复不能接受，必须整改。虽然修复测试、局部测试、ruff 和 `git diff --check` 有通过结果，但严格审核发现至少两个关键安全边界仍然缺失：真实 repository context 没有在调用前进行 token preflight，且实际 usage 被截断到 reservation 后写入权威 budget ledger；timeout/recovery 也没有实现。修复报告明确承认了这些缺口，却仍把 O-C01、O-C02 和 O-C08 标为 PASS。独立复现还证明了：约 66k 输入 token 的 context 会实际进入 gateway，并能以 `completed` 结果被接受，同时持久化 budget 只记 30k token。

因此最终状态为：

**ORCHESTRA_REPAIR_REJECTED_REMEDIATION_REQUIRED**

## 审计边界和不可变性声明

- 严格只读审计。没有修改目标 worktree 中的源码、测试、报告、数据库或 MCP 配置；没有 reset、stash、clean、覆盖、暂存、commit、push、merge 或重启 MCP。
- 没有联网、安装依赖、调用真实 DeepSeek 或其他模型，也没有使用 live dispatch。所有动态反例均使用临时目录、临时 SQLite/SQLAlchemy stack 和 `httpx.MockTransport`，不触碰生产服务。
- 生产数据库只用 `sqlite3 -readonly` 查询；没有迁移或写入。
- 目标 worktree 审计前后都保持同一组待审改动：3 个 tracked source 文件被修改，修复报告/evidence 和新测试为 untracked。审计输出只写入用户指定的 ReactionAgent 文档路径；除此之外不修改 ReactionAgent。
- 本审计使用了 `$orchestra-live` skill，并先完整阅读其 `SKILL.md`，遵守其不得伪造 worker/live 结果、不得泄露 secret、不得擅自写入或提交的边界。该任务是独立只读审核，所以没有执行 Orchestra workflow/live dispatch。

## 已完整阅读的材料

以下文件均从文件系统完整读取，没有依赖聊天摘要：

1. `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/CHATGPT_PROMPT_REVIEW_ORCHESTRA_DEEPSEEK_REPAIR_2026-08-03.md`
2. `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/CHATGPT_HANDOFF_REVIEW_ORCHESTRA_DEEPSEEK_REPAIR_2026-08-03.md`
3. `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/CHATGPT_HANDOFF_ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_2026-08-02.md`
4. `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/orchestra/CHATGPT_PROMPT_REPAIR_ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_2026-08-02.md`
5. `/Users/frank_gong/.codex/skills/orchestra-live/SKILL.md`
6. `/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl/docs/reports/ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_REPAIR_REPORT_2026-08-02.md`
7. `/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl/docs/reports/ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_REPAIR_EVIDENCE_2026-08-02.json`

审核标准按 review prompt/handoff 中的 O-C01 至 O-C12 执行；特别把 prompt 指出的“真实输入 token 预估”和“timeout alignment 未修复”当作需要独立验证的阻断风险，而没有接受报告的 READY 或 PASS 标签。

## 目标 worktree 快照

| 项目 | 独立观察 |
|---|---|
| Git root | `/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra/.worktrees/milestone-d-codex-mcp-impl` |
| branch | `milestone-e-real-worker` |
| HEAD | `ce53690cf6a806594871580aa941021cb0461466` |
| 预期 base | `milestone-e-real-worker` / 同一 HEAD（与 handoff 一致） |
| tracked 修改 | `src/orchestra/cognition/engine.py`；`src/orchestra/services/external_workflows.py`；`src/orchestra/services/live_dispatch.py` |
| untracked 待审文件 | `docs/reports/ORCHESTRA_DEEPSEEK_LIVE_DISPATCH_REPAIR_REPORT_2026-08-02.md`；同名 evidence JSON；`tests/services/test_live_dispatch_repair.py` |
| tracked diff | 119 insertions / 10 deletions；只由以上 3 个 source 文件组成 |
| `git diff --check` | 通过，无 whitespace error |
| 新修复测试实际行数 | 784 行（修复报告写成 382 行，统计不一致） |

关键文件 SHA-256（审计时重新计算）：

| 文件 | SHA-256 |
|---|---|
| `src/orchestra/cognition/engine.py` | `c76f74785859fae7c29830aaee2908536012f0073ebe4c7317abb7a8c63eaf46` |
| `src/orchestra/services/external_workflows.py` | `6004be6ae51ec571df6ba0e7aabd764a313f853a016a59673aac28c085bb3efb` |
| `src/orchestra/services/live_dispatch.py` | `dc9bf89b025a3f33c89aea71518769a028137def185e3fcb4e270859fc0e0456` |
| `tests/services/test_live_dispatch_repair.py` | `2f624afa1147a98a88e34c7414f1f9e83f9bc9fa948185019569fd5efbb0a176` |
| repair report | `8acdf27f2770d6f52c6a973583644aa7a95fa295d444ec42cf9c01986091afad` |
| repair evidence JSON | `886f47be5f1764a76f4c7b1e8dc734625a6b7df0f36caca353f233d0fb366684` |

## 生产数据库的只读事实

数据库路径：`/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/orchestra-data/orchestra.db`。查询还发现旁边存在 SQLite WAL/SHM 文件；没有对它们执行任何写操作。

| workflow | operation | model-call 事实 | workflow state | artifacts/execution |
|---|---|---|---|---|
| `wf-8c6ac1eccb5348f2a0f985671b684f0f` | `reservation_token_limit`；recovery operation `worker_unexpected` | DeepSeek；`incomplete/max_output_tokens`；input 66,685；output 29,000；total 95,685；latency 316,581 ms；retryable=1；cost=0 | `executing`, version 5 | `live_artifacts=0`, `live_executions=0` |
| `wf-dd44f94e4dc24a5688712ee7a0b8e0e1` | `reservation_token_limit` | DeepSeek；`incomplete/max_output_tokens`；input 6,571；output 11,000；total 17,571；latency 98,453 ms；retryable=1；cost=0 | `executing`, version 5 | `live_artifacts=0`, `live_executions=0` |

三个对应 failed operation journal row 的 `result_json` 都是 `NULL`。这确认了原始故障 handoff 中“有实际 provider usage、没有 artifact/execution、workflow 留在 executing”的事实，也确认了 repair report 没有把该诊断持久化到公开的 workflow result。

## 独立反例和源码证据

### 1. 真实大小的 input preflight 仍不存在（关键）

`EngineConfig.worker_estimated_input_tokens` 仍固定为 `1000`（`src/orchestra/cognition/engine.py:76-84`）。`_execute_task` 使用 `per_attempt_tokens - 1000` 计算 output cap，并将同一个固定值作为 `estimated_input_tokens` 和 `minimum_context_tokens` 的输入（`engine.py:654-672`）。`LiveProposalDispatchService._preflight` 只检查 state、approval、已有 execution 和 repository 条件（`src/orchestra/services/live_dispatch.py:222-264`），没有读取已选择的 repository context 并估算 token，也没有在 adapter/gateway 之前比较 workflow/task 的真实可用预算。

我用临时 git repository 写入约 272,710 字符的 context（约 66k token），workflow/task token limit 均为 30,000，并用 `httpx.MockTransport` 捕获请求：

```text
gateway_calls: 1
service result: completed; view state: verifying
view input_units: 66685; output_units: 1
request max_tokens: 29000
persisted budget spent.tokens: 30000
durable model-call total_tokens: 66686
```

也就是说，真实大小的输入已经通过了 service/engine gate，gateway 被调用，completed artifact path 被接受；并非“调用前拒绝”。这不是 DeepSeek live call，而是足以证明 preflight 缺失的本地 fake-gateway 反例。

修复测试 R1（`tests/services/test_live_dispatch_repair.py:221-279`）并没有覆盖这个场景：它创建一个很小的 `app.py`，把 `task_tokens` 设为 `100`，因此固定的 1000 token estimate 自己就让 partition 失败；这只能验证旧的 `task_token_partition_infeasible` 分支，不能验证真实 context 预算。

结论：O-C01 **FAIL（Critical）**。

### 2. actual usage 被错误截断，权威 ledger 低记（关键）

`_settle_actual_usage` 的 docstring 声称处理 non-completed calls，但代码在所有结果状态检查之前调用（`engine.py:747-752`）。settlement 使用 `min(tokens, reservation.max_tokens)` 与 `min(cost, reservation.max_cost_minor_units)`（`engine.py:390-422`）。因此上面的 66,686 actual tokens 被 durable `model_calls` 记录为真实值，却在 workflow budget 中只计 30,000；actual cost 也会被同样截断。该 ledger 没有 debt/overspend/actual-settlement 状态可供后续 preflight 使用。

这会产生两个危险后果：budget remaining 被虚增，后续调用可能继续获准；成本和费用记账也低于 provider 实际消耗。修复报告自己承认“budget undercounts actual overspend by min”，但仍将 O-C02 标为 PASS。

结论：O-C02 **FAIL（Critical）**。

### 3. `IncompleteReason` 被抹成统一的 `worker_output_truncated`

contract 明确定义 `MAX_OUTPUT_TOKENS`、`CONTENT_FILTER`、`UNKNOWN`（`src/orchestra/gateway/contracts.py:28-32`）。但 engine 对所有 `ModelCallStatus.INCOMPLETE` 都执行 `_fail(run, "worker_output_truncated")`（`engine.py:753-768`），没有分派 `result.incomplete_reason`。

独立用现有 fake engine 构造 `IncompleteReason.CONTENT_FILTER` 的合法 `ModelCallResult`，得到：

```text
ModelCallAudit: status=incomplete, incomplete_reason=content_filter
EngineError.reason_code: worker_output_truncated
```

内部审计保留了 provider reason，但对调用方暴露的 failure reason 是错误的。结论：O-C03 **FAIL（High）**。

### 4. 没有公开 MCP/workflow diagnostics

`WorkflowView` 只包含 workflow metadata、state、evidence、next_actions（`src/orchestra/services/external_workflows.py:97-115`）；`GetWorkflowSuccess` 的公开 schema 也没有 `profile_id/route`、attempt、input/output/total tokens、latency、`incomplete_reason` 或 no-artifact diagnostic 字段（`src/orchestra/mcp/schemas.py:280-296`）。这些值仅在内部 `ModelCallRow`/`DurableModelCallAudit` 中可查。

R7（`test_live_dispatch_repair.py:594-653`）直接查内部 audit，再仅检查 `next_actions`；它没有通过 MCP `get_workflow` 验证诊断是否公开。因此“diagnostics persisted”不能等同于“公开 MCP diagnostics”。结论：O-C05 **FAIL（High）**。

### 5. failed replay 只有 error code，没有稳定 terminal result

live dispatch 在失败 replay 时只取 `begun.record.error_code`，重新抛出一个通用 `ServiceError`（`src/orchestra/services/live_dispatch.py:359-379`）。`OperationJournal.fail` 只写 `status/error_code`，不写 `result_json`（`src/orchestra/persistence/journal.py:216-229`）。生产 DB 三个 failed row 的 `result_json` 均为 `NULL`。

它确实不会重新调用 provider，也不会返回 generic `operation_not_replayable`，所以有一部分幂等保护；但不能重放同一个结构化 terminal result、diagnostic fingerprint、usage 或 original next actions。严格按 O-C06 的“same terminal result / deterministic reconstruction”要求，结论为 **FAIL（High，部分行为通过）**。

### 6. attempt exhaustion 不是 revision-aware

dispatch 在 provider 调用前查询 workflow 内全部 durable model calls，然后以 `task_id == task.task_id and purpose == "execute"` 的数量与当前 task 的 `max_attempts` 比较（`src/orchestra/services/live_dispatch.py:386-403`）。它没有按 plan/revision/execution identity 区分历史尝试，也没有证明多 task、revised plan、跨 operation 的计数契约。现有 R5 只覆盖一个 task、一次旧 incomplete call 后的单次新 request（`test_live_dispatch_repair.py:477-538`）。

因此当前实现能把单一故障映射成 typed exhaustion，但不能证明新的 plan/revision 不会错误继承旧 attempt，也不能证明多个 task 互不污染。结论：O-C07 **FAIL（High）**，需要 revision-aware durable attempt identity 和 adversarial tests。

### 7. timeout/recovery 没有实现

Anthropic adapter 将 task `timeout_seconds` 原样传给 `httpx`（`src/orchestra/gateway/anthropic.py:191-205`）；没有 MCP transport margin、start/poll、provider request reconciliation 或 timeout 后查询。live server 是同步 stdio surface。失败时 dispatch 只 mark operation failed（`live_dispatch.py:431-450`），没有一个可以查询/认领 provider completion 的 durable in-flight state。

R6 的名称和 docstring 声称测试 client timeout，但 handler 立即返回 200，第一次 dispatch 直接成功，第二次只是普通 successful idempotency replay（`test_live_dispatch_repair.py:541-589`）。没有延迟、disconnect、transport timeout、provider completion-after-timeout 或 reconciliation。修复报告也明确写着 timeout alignment 尚未修复，却把 O-C08 标为 PASS。

结论：O-C08 **FAIL（Critical）**。

### 8. workflow state 与 next actions 不一致，且 fail-open

EngineError catch 只调用 `_mark_failed(operation_id, reason_code)`，没有 `WorkflowRepository.transition`（`live_dispatch.py:431-434`）。因此 provider/incomplete failure 后 external workflow 可以仍然是 `executing`，生产 DB 的两个原始 workflow 正是如此。`ExternalWorkflowService` 可能为 executing failure 返回 `replan_or_revise_task`（`external_workflows.py:184-201`），但 live MCP 注册的 11 个 tool 中没有这个 handler；`LiveToolDispatcher` 只新增 dispatch/artifacts/evidence 三个 handler（`src/orchestra/mcp/live_tools.py:25-43`），base dispatcher 也没有该动作。

此外，公开 workflow 查询对 model-call diagnostics 的 SQL 被一个宽泛 `except Exception: pass` 包住（`external_workflows.py:372-386`）。查询失败会把 `has_failed_dispatch` 留成 false，从而可能重新建议普通 dispatch，属于 fail-open recovery。

结论：O-C09 **FAIL（High）**。

### 9. 测试与修复报告的独立一致性问题

- 修复报告/evidence 宣称 full suite `760 passed`；独立运行相同项目的 full suite 得到 `759 passed, 1 failed`。失败为 `tests/test_build_backend.py::test_uv_editable_request_installs_regular_wheel_contents`；首次失败因 uv cache 目录权限，改用 `/private/tmp` cache 后离线 editable install 仍 exit 1。没有联网或安装依赖来绕过它，所以不能把报告数字当作已复现事实。
- 新测试实际 784 行，报告写 382 行；report/evidence 的 changed-files 只列 tracked source/test，未列出自身两个 untracked report artifacts。
- R1 使用 `task_tokens=100` + 小 repo，未测真实 66k context。
- R2 只断言 gateway `max_tokens < task max_tokens`，没有验证 input+output+retry/cost 的统一预算。
- R6 是立即成功响应的 successful replay，不是 timeout recovery。
- R7 直接读内部 DB，未检查 MCP payload 的 diagnostics。
- R8 允许“只要有任意包含 recovery/revision/replan 的字符串即可”，不是注册动作集合校验。
- R9 只验证 `ModelCall` actual usage，未验证 budget ledger、remaining budget 或 actual cost。

因此 O-C10 **FAIL（High）**：focused tests 的绿灯不足以证明真实 acceptance；full suite 也没有独立复现为全绿。

## O-C01 至 O-C12 逐项裁决

| Criterion | 严格状态 | 依据 |
|---|---|---|
| O-C01 真实 input preflight | **FAIL** | 固定 1000 estimate；66,685-input fake gateway 实际被调用并完成 |
| O-C02 token/cost semantics | **FAIL** | actual usage/cost 用 `min` 截断至 reservation；ledger 低记 |
| O-C03 typed incomplete reason | **FAIL** | `content_filter` 被映射成 `worker_output_truncated` |
| O-C04 no false artifact | **PASS（限定）** | incomplete/failed path 未创建 live artifact/execution；生产 DB 两 workflow 均为 0 |
| O-C05 public MCP diagnostics | **FAIL** | WorkflowView/GetWorkflowSuccess 没有 route/usage/latency/reason 字段 |
| O-C06 idempotent replay | **FAIL（部分通过）** | 不重复 provider call，但 failed result_json 为 NULL，无法重放结构化 terminal result |
| O-C07 attempt exhaustion | **FAIL** | 仅按 task_id+purpose 计数，未按 revision/plan identity；测试不充分 |
| O-C08 timeout recovery | **FAIL** | 原样同步 timeout；无 start/poll/reconcile；R6 立即成功 |
| O-C09 workflow state/next actions | **FAIL** | failure 后 DB 留 executing；动作未注册；diagnostic query fail-open |
| O-C10 regression/test validity | **FAIL** | full suite 759+1 failed；关键 tests 是 false positive/permissive |
| O-C11 DB safety | **PASS（本次审计范围）** | 无 migration；本审计只读；目标 worktree 无 DB 改动 |
| O-C12 no live provider call | **PASS（本次审计范围）** | 审计和 repair tests 使用 fake transport；无真实 provider call |

O-C04/O-C11/O-C12 的 PASS 只表示在可验证范围内没有发现对应违规，不抵消 O-C01/O-C02/O-C08 的 critical failure。

## 独立测试与静态检查记录

所有命令都在目标 worktree 执行，使用已有 `.venv`，没有安装依赖：

| 检查 | 结果 |
|---|---|
| `PYTHONPATH=src .venv/bin/python -m pytest tests/services/test_live_dispatch_repair.py -q --tb=short` | **10 passed**，约 3.03 s |
| services/operations focused：`tests/services/test_live_dispatch.py tests/services/test_operations.py` | **11 passed**，约 2.45 s |
| budget focused：`tests/budget/test_ledger.py` | **18 passed** |
| gateway focused：`tests/gateway/test_anthropic.py tests/gateway/test_contracts.py` | **49 passed** |
| persistence focused：model_calls/journal/live_repositories | **45 passed** |
| MCP focused：live_tools/live_stdio/live_schemas | **20 passed** |
| cognition/e2e focused：live_proposals + codex MCP bridge | **15 passed**，约 34.99 s |
| full suite：`PYTHONPATH=src .venv/bin/python -m pytest tests/ -q --tb=no -p no:cacheprovider` | **759 passed, 1 failed**，约 53.93 s；build-backend test failed |
| full suite rerun with `UV_CACHE_DIR=/private/tmp/...` | 同一 build-backend editable-install failure；没有联网/安装依赖 |
| `.venv/bin/ruff check src/ tests/services/test_live_dispatch_repair.py` | 通过 |
| `RUFF_CACHE_DIR=/private/tmp/... .venv/bin/ruff check .` | 通过；初次默认 cache 目录因权限失败，使用临时 cache 后复跑 |
| `.venv/bin/ruff format --check .` | 通过，149 files already formatted |
| `git diff --check` | 通过 |

`-p no:cacheprovider` 和临时 ruff/uv cache 仅用于避免工具写入目标目录；没有改变待审源码。完整命令、exit code 和结果也记录在 JSON evidence 中。

## 必须完成的整改门槛

在重新声称 READY 或 PASS 前，至少需要：

1. 在 adapter 之前基于**实际选定 repository context**做 deterministic token estimate/preflight；明确 input+output、attempt、workflow/task budget 和 model context limit 的语义，并用约 66k input 的反例证明 gateway call 为 0。
2. 将 reservation、actual usage、actual cost 和 overspend/debt 分开记账；不能用 `min(actual, reservation)` 隐藏 provider 消耗。完成和 incomplete/failed 均须有可审计的最终结算。
3. 只把 `max_output_tokens` 映射成 `worker_output_truncated`；保留 `content_filter`、`unknown` 和其他 gateway reason 的 typed code，并在公开诊断中可见。
4. 在 `get_workflow`/公开 MCP response 提供 bounded、去 secret 的 route/profile、attempt、usage、latency、incomplete reason、operation status/no-artifact diagnostics。
5. 为 failed/in-flight operation 持久化稳定结构化 terminal result 或 deterministic diagnostic fingerprint，使相同 request replay 得到相同结果且绝不重复收费；写清 timeout 后 provider completion 的 reconcile 流程。
6. 将 attempt identity 与 plan/revision/execution 绑定，覆盖多 task、修订计划、旧 call 和新 request 的 exhaustion adversarial tests。
7. 实现 MCP timeout margin 或异步 start/poll/reconcile；测试必须包含 delayed provider、client disconnect/timeout、provider 已完成、replay/poll 不重复调用。
8. failure 时持久化真实 workflow state；所有 `next_actions` 必须来自已注册且可执行的动作集合；诊断查询异常须 fail closed。
9. 补强上述测试并让 full suite 真正全绿；修复 report/evidence 的 test count、changed-files 和 O-C status 矛盾后再提交新审计。

## 最终状态

**ORCHESTRA_REPAIR_REJECTED_REMEDIATION_REQUIRED**

