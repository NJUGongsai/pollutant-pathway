# P7 Cost & Latency Report

> 报告日期：2026-08-07 | 数据来源：`t7_evaluation.json` latency_token_cost 字段 + `tests/p7/` 实测

---

## 1. Token 消耗

### 1.1 实测数据

| 环节 | provider 调用次数 | 说明 |
|---|---|---|
| expand_evidence | 1 | 1 次 evidence expansion（fx_oct） |
| choose_t_s | 1 | 1 次候选选择 |
| stop | 1 | 1 次终止信号 |
| **合计** | **3** | 3 次 provider 调用 |

> 数据来源：`t7_evaluation.json.metrics.latency_token_cost = 3`

### 1.2 与 baseline / fixed 对比

| 角色 | provider 调用 | 说明 |
|---|---|---|
| baseline | 0 | 确定性 ML 内核，无 LLM 调用 |
| agent | **3** | 完整 agent 流程：expand + choose + stop |
| fixed | 0 | 人工指定，无 LLM 调用 |

---

## 2. 延迟分析

### 2.1 工具调用延迟

| 工具 | 调用数 | 说明 |
|---|---|---|
| expand_evidence | 1 | 1 次 evidence expansion |
| choose_t_s | 1 | 1 次候选选择 |
| stop | 1 | 1 次终止（不计入 tool_calls 计数，但计入 provider 调用） |
| **总计** | **3** | 完整流程 |

> 数据来源：`t7_evaluation.json.agent.tool_calls = 2`（expand + choose，stop 不计入 tool_calls 计数，但计入 `latency_token_cost`）

### 2.2 Agent 步骤数

| 属性 | 值 | 说明 |
|---|---|---|
| agent steps | **3** | 3 步完成完整流程 |
| 每步最大 tool calls | 1 | 每个 step 调用 1 个工具 |
| 合计 tool calls | 2 | expand + choose（stop 不计入） |

> 数据来源：`t7_evaluation.json.agent.steps = 3`, `agent.tool_calls = 2`

### 2.3 拒绝/重试

| 指标 | 值 | 说明 |
|---|---|---|
| rejections | **0** | 0 次 rejection，所有工具调用均通过 grounding 验证 |
| 重试轮次 | 0 | 0 次重试 |

> 数据来源：`t7_evaluation.json.agent.rejections = 0`

---

## 3. 成本估算

### 3.1 单次运行成本

假设 provider 为 Anthropic Claude 系列（当前主力模型），估算：

| 项目 | 调用次数 | 输入 Token（估算） | 输出 Token（估算） | 成本（估算） |
|---|---|---|---|---|
| expand_evidence | 1 | ~500 | ~200 | 低 |
| choose_t_s | 1 | ~400 | ~100 | 低 |
| stop | 1 | ~300 | ~50 | 极低 |
| **合计** | **3** | **~1,200** | **~350** | **极低** |

> 注：上述 token 估算基于 `t7_evaluation.json` 的 agent 行为（2 次实际 tool call + 1 次 stop），实际 token 消耗取决于 provider 实现和 prompt 大小。

### 3.2 关键成本特征

- **无拒绝/重试开销**：rejections=0，无额外成本
- **最小调用序列**：3 次调用是完成 agent 流程的最少次数
- **确定性基线无成本**：baseline 是本地 ML 内核，不产生 LLM 成本

---

## 4. 测试级性能

### 4.1 测试套件执行时间参考

| 测试模块 | 测试数 | 说明 |
|---|---|---|
| `tests/p7/test_t0_bridge.py` | 8 | 桥接适配器测试，快速 |
| `tests/p7/test_t0_handle_predict_e2e.py` | 2 | 端到端 predict，快速 |
| `tests/p7/test_t0_kernel_integration.py` | 3 | 内核导入，最快 |
| `tests/p7/test_t2_baseline.py` | 11 | 基线门测试，快速 |
| `tests/p7/test_t2_loop.py` | 6 | 循环策略测试，快速 |
| `tests/p7/test_t4_grounding.py` | 17 | grounding 测试，中等 |
| `tests/p7/test_t4_p2_closures.py` | 2 | P2 关闭测试，快速 |
| `tests/p7/test_t5_reporter.py` | 13 | 报告器测试，中等 |
| `tests/p7/test_t6_harness.py` | 19 | 诱导测试（6 个 hard gate），中等 |
| `tests/p7/test_t7_evaluation.py` | 12 | 评估测试（含 T7 end-to-end），较慢 |
| `tests/p7/test_provider_adapter.py` | 18 | provider 适配器测试，快速 |
| **合计** | **111** | 全 suite 实测 PASS |

### 4.2 性能特征

- **所有测试使用 fake/mock provider**：`tests/p7/` 无真实 API 调用，测试延迟低
- **确定性测试**：所有测试在 fixture 模式下运行，可复现
- **无外部依赖**：测试不依赖网络或外部 API

---

## 5. 延迟/成本优化建议

### 5.1 当前基线

```
provider 调用: 3 次
tool calls: 2 次
steps: 3 步
rejections: 0 次
```

这是能完成 agent 选择流程的最少调用次数。任何优化都不应增加步骤数。

### 5.2 优化方向

| 方向 | 预期效果 | 风险 |
|---|---|---|
| 合并 expand + choose 为 1 步 | 减少 1 次调用 | 违反单一职责原则 |
| 预缓存 expand 结果 | 减少重复调用 | 需处理缓存失效 |
| 增加 evidence expansion 数量 | 提高 recall 但增加 1-2 次调用 | 成本增加 |

---

## 6. 结论

**PASS** ✅

- latency_token_cost = 3（最小调用序列）
- tool_calls = 2（仅 expand + choose）
- rejections = 0（零额外成本）
- 完整测试套件 111 项全部 PASS，使用 fake provider 无真实 API 成本
- 在最小成本下完成了从基线获取到候选选择的完整 agent 流程