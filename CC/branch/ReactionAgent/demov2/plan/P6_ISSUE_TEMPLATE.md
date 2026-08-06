# P6 实现派单模板（ReactionAgent MCP Service）

> 用法：把本模板复制为 issue 描述，替换 `‹...›` 占位符后派给实施者（claude-deepseek / claude-glm）。完成后转交 claude-kimi 走 Gate P6 审核。

## 任务
‹P6 具体子任务，对应 final_plan.md §9 的 P6-T1~T6 之一或整体›

## 工作目录（必须，第一优先）
```
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
```
所有代码/测试/报告都写在这个目录内。该目录之外一律只读参考。

## 分支策略（必须）
- 在服务端 worktree 建分支：`‹p6-xxx›`（如 `p6-mcp-kernel`）
- 只在你自己的分支上 commit；**不 push、不 merge、不碰 main**
- commit 仅限本任务授权范围，未授权 commit 一律禁止

## 权威参考
- `plan/final_plan.md` §9（P6 — MCP Service）：P6-T1 contracts / T2 strict schemas / T3 idempotency / T4 side effects / T5 resources / T6 contract+chaos / Gate P6
- `final_design/` 目录（设计文档）
- P5 提示词中的边界说明（P6 有独立实现提示词，勿混用）

## 环境
- 依赖：demov2 的 `pyproject.toml` + `requirements.lock.txt`（必要时 `pip install -e .`，勿全局乱装）
- 测试：`pytest`（当前环境 pytest 9.1.1 / Python 3.11.8）
- MCP SDK：按 pyproject 声明（fastmcp / mcp）

## 交付物
- [ ] 4 个 MCP 工具：`reaction.predict_analogical_products_v1` / `reaction.get_run_v1` / `reaction.get_candidate_evidence_v1` / `reaction.expand_evidence_v1`
- [ ] Strict JSON schemas（`additionalProperties:false`、enums/version、required、limits、typed errors、cross-field、golden schemas）
- [ ] Idempotency：repeat / concurrent duplicate / same key diff payload / interrupted write / child expansion
- [ ] Side effects 准确（predict=run write、get=read、local expand=child run）
- [ ] Resources（URI、access control、tenant binding、retention）
- [ ] Contract/chaos 测试（malformed / unknown / stale / missing / budgets / concurrency / large payload / partial failure）
- [ ] 证据报告（逐项可追溯）

## 硬性要求（铁律）
- **先写真实 RED tests，再实现**；拿不出 RED 证据的改动不算完成
- **不伪造** PASS / 证据 / 审核结果
- Gate P6 未过就如实报 **FAIL / BLOCKED**，不糊弄
- 完成后报告：状态（PASS / FAIL / BLOCKED）+ 改动清单 + RED 证据 + 运行方式

## 审核转交
实施完成后，把本任务转给 **claude-kimi**（审核专家），按 Gate P6 检查清单独立审核：
- schemas match / invariants / idempotency / immutable / side effects / typed failures / usable without LLM

## 审核输出格式
```
## 0. Verdict: {STAGE}_ROUND_{N}_READ_ONLY_AUDIT_‹PASS|FAIL|BLOCKED›
## 1. Independent verification matrix
## 2. Finding closure matrix
## 3. Mandatory findings（P0/P1/P2，含 file:line 证据）
## 4. Remediation requirements（FAIL 时）
```