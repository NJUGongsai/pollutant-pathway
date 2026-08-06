# P4 Round 4 独立只读审核 — Hermes 任务书（kimi-tp）

> 你是独立只读审核者。审核对象：P4 Round 4 提交。请自主完成整个审核流程，产出审核报告。

## 一、任务目标

对 P4 Round 4 的提交做**严格、fail-closed 的独立审核**，判定 PASS / FAIL / BLOCKED，若 FAIL 则输出下一轮 remediation 要求。

## 二、被审对象与环境

- **项目根（worktree）**：`/Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2`
- **分支**：`worktree-p4-strict-kernel`
- **提交入口**：`reports/p4/SUBMISSION_TO_CHATGPT_P4_ROUND_4.md`
- **结构化证据**：`reports/p4/P4_ROUND_4_AUDIT_EVIDENCE.json`
- **环境**：Python 3.11（anaconda3），pytest 9.1.1，pytest-json-report 1.5.0 已装
- **状态声明**：`P4_ROUND_4_IMPLEMENTATION_COMPLETE_REAL_GATE_BLOCKED_READY_FOR_CHATGPT_AUDIT` / `P5_BLOCKED`

## 三、审核流程（必须执行）

### 1. 读任务书
- `plan/final_plan.md` §7（P4-T1~T8 + Gate P4 checklist）

### 2. 读上轮 audit（Round 3，FAIL）与 remediation 要求
- 主目录 `reports/p4/CHATGPT_P4_ROUND_3_READ_ONLY_AUDIT_AND_REMEDIATION.md`
- 重点：P4-R3-A（P0）、P4-R3-B（P0）、P4-R3-C（P1）、P4-R3-D（P1）的 mandatory requirements

### 3. 独立重放提交验证矩阵（不信任提交者自述）
```bash
cd /Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2
python3 -m pytest -q -p no:cacheprovider tests/p4
python3 -m pytest -q -p no:cacheprovider tests/contracts
python3 -m scripts.run_p4_gate
python3 -m scripts.run_p4_mutations
python3 -m scripts.run_p4_round4_probes
```
提交声称：248 passed / 290 passed / 11-11 PASS + 3-3 BLOCKED / 14-14 CAUGHT / 12-12 rejected

### 4. 独立核查 Round 3 findings 关闭状态
逐条核对 P4-R3-A/B/C/D 在 Round 4 是否真正关闭（重点：execution-authority registry、receipt verifier、interface pin、seal 覆盖）。

### 5. 写并运行你自己的反例 probe
重点攻击面（Round 3 的同步重算类反例 + 你可能发现的新的）：
- **receipt 可伪造性**：仅用公开常量 + 自洽 hash 能否通过 `P2ReceiptVerifier`/`P1ReceiptVerifier`？（`reaction_agent/authority/receipts.py`；`_cross_bind` 只在双方都声明时对比；`gate_items_hash` 是否验证内容）
- **artifact 与 pin 绑定**：`current_run_artifact.json` 是否有 pin 绑定？（`reaction_agent/adapters/p3_consumer.py` 的 `_validate_artifact` 是否只做内部自洽）
- **registry exact-object 语义**：`is not` identity + content_hash 是否可绕过？（`reaction_agent/authority/registry.py`）
- **跨进程/跨会话**：registry process-local 的约束
- 写 probe 到 `/private/tmp/`，不要改 repo 源码

### 6. 输出审核报告
写到 **worktree 主目录** `reports/p4/HERMES_P4_ROUND_4_READ_ONLY_AUDIT_AND_REMEDIATION.md`（与 ChatGPT 审核文件并列，前缀 HERMES）。

## 四、审核行为规范

1. **Fail-closed**：任何绕过路径/概念缺陷 → FAIL。宁可错杀。
2. **不信任自述**：以你自己的验证输出为准。
3. **证据导向**：每个 finding 带 `file:line` 或可复现输出。
4. **逐项核对**：任务书 checklist 逐项 PASS/FAIL/BLOCKED。
5. **诚实**：无法验证 → BLOCKED，禁止编造 PASS。
6. **分级**：P0（科学/安全命门）、P1（重要）、P2（次要）。

## 五、报告格式（严格遵循）

```markdown
# Hermes P4 Round 4 Read-Only Audit and Round 5 Remediation

## 0. Verdict
一句话判定 + 状态码：
HERMES_P4_ROUND_4_READ_ONLY_AUDIT_PASS   # 或 FAIL / BLOCKED
P4_ROUND_5_REMEDIATION_REQUIRED          # FAIL 时
P5_BLOCKED

## 1. Independent verification matrix
（你实际跑出的结果表）

## 2. Finding closure matrix
（上轮 P4-R3-A/B/C/D 关闭状态）

## 3. Mandatory findings
### P4-R4-X — 标题（等级）
#### 证据 / #### 影响 / #### 修复要求

## 4. Remediation requirements
（FAIL 时给下一轮最小整改清单）
```

## 六、禁止事项

- 不安装依赖（环境已就绪）
- 不改 repo 源码/测试
- 不 commit/push
- probe 只写 /private/tmp/
- 不借用他人结论，全部自己验证