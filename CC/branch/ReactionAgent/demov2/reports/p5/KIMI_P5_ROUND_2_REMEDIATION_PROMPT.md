# Kimi P5 Round 2 Remediation Instructions

## 1. 任务与正式审计状态

你正在修复 ReactionAgent 的 P5。kimi-k3 已完成 Round 1 只读审核（独立裁决）+ 独立验证。

正式状态为：

```text
P5_ROUND_1_READ_ONLY_AUDIT_FAIL
P5_IMPLEMENTATION_COMPLETE = NOT_ACCEPTED
P5_INTEGRATION = BLOCKED
```

本轮是 **P5 Round 2 定向修复**。目标是建立真正的信任根与上游权威绑定，而不是继续给调用方自填字段增加更多自签名 hash。这不是架构重写，不是下一阶段开发，也不是修改冻结合同来适配代码。真实上游权威缺失可以继续诚实标记 `BLOCKED`，但任何 machinery / boundary 缺陷必须使审计状态为 `FAIL`，不能被 BLOCKED 掩盖。

## 2. 工作树、分支和环境

只在以下工作树中实施修复：

```text
/Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2
```

工作树分支：见 `git branch --show-current`。

Python / 测试环境（已就绪，勿重装）：

```text
/opt/anaconda3/bin/python3   (Python 3.11+, pytest 9.1.1+, pytest-json-report 1.5.0)
```

开始前必须运行并记录起始状态（写入 `reports/p5/P5_ROUND_2_STARTING_WORKTREE_STATE.md`）：

```bash
cd /Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git diff --stat
git diff --name-status
git ls-files --others --exclude-standard
```

## 3. Mandatory findings（必须全部修复）

### P5-R1-01 — P5 测试套件独立重放 FAIL，与提交声称 "83 passed" 直接矛盾（P0）

#### 证据
- 任务书 §四（独立重放，审计者实测）：`pytest tests/p5 -q -p no:cacheprovider` → **FAIL**；失败节点 `tests/p5/test_p5_real_data.py::TestRealSixLayer::test_data_layer_real_counts`，错误为 pydantic `ValidationError`（"1 validation error for LayerM…"，原文截断）。
- 对照任务书 §三：提交方声称 "P5 invariant tests **83 passed**（60 原 + 23 real_data）"。
- 该失败节点正是 23 条新增 real_data 诚实性断言之一（six-layer N/denominator，见 §五 Probe B 描述）。

#### 影响
- 提交的核心验证声明不可复现；且失败的不是边缘测试，而是 real_data 六层计数/分母诚实性断言——P5 全部指标（N、分母、KPI）的科学有效性在此断言闭合之前不可信。
- fail-closed：存在实测 FAIL 记录时，"83 passed" 不作数。

#### 修复要求
1. 定位并修复 `test_data_layer_real_counts` 的根因（LayerM* StrictModel 校验失败的字段与真实 snapshot 数据），禁止改测试迁就代码或放宽校验。
2. 在干净环境重跑 `pytest tests/p5 -q -p no:cacheprovider` 全绿，附 pytest-json-report 机器可读结果（含该节点 passing 记录）。
3.  sibling 检查：确认其余 six-layer 计数断言无同类缺陷。

### P5-R1-02 — Gate PASS 与测试套件 FAIL 并存：P5 Gate 未将 invariant 测试失败纳入阻断条件（P0）

#### 证据
- 任务书 §五 Probe A：`/opt/anaconda3/bin/python3 scripts/run_p5_gate.py` → exit 0，`P5 Gate Status: PASS, Pass: 7, Block: 0, Fail: 0`；`P5_GATE_REPORT.json`：`status=PASS, fail_count=0`。
- 同一证据包 §四：`pytest tests/p5` 实测 FAIL（见 P5-R1-01）。
- P5-G01~G07 逐项输出（§四/§五）中无任何一项引用测试套件结果作为通过条件。

#### 影响
- Gate 可在测试套件失败状态下报 PASS——这是绕过路径（bypass）："Gate 全绿" 不再蕴含 "实现正确"。按任务书 §七.1，任何绕过路径/概念缺陷 → FAIL。

#### 修复要求
1. P5 Gate 新增阻断性 check：消费 `pytest tests/p5` 的 pytest-json-report，非全绿则 Gate FAIL/BLOCK。
2. 负向测试：人为注入一个 failing test（或 mock 非零 exit 的 json report），断言 Gate 必 FAIL。
3. 重出 `P5_GATE_REPORT.json`，其中该 check 可见且 pass。

### P5-R1-03 — 证据包内部自相矛盾：Probe B "83 passed" vs §四 实测 FAIL（P1）

#### 证据
- §五 Probe B（line 59 区域）："**命令：** `python3 -m pytest -q -p no:cacheprovider tests/p5` → **83 passed**"。
- §四（line 27-28 区域）：同命令族实测 **FAIL**。
- 两处均为"审计者实测"，无环境/时点/代码状态差异说明。

#### 影响
- 审核所依赖的 probe 证据自身不可调和，无法据此采信任何一侧的测试结论；fail-closed 取负向证据（FAIL）为准，同时该矛盾本身构成必须关闭的 finding。

#### 修复要求
1. 提交方解释矛盾来源（代码状态差异、缓存、环境），或承认 Probe B 记录失效。
2. 以单一权威重放为准重跑并附原始输出 + json report；两次独立重放结果须一致。

### P5-R1-04 — 上游真实链证据截断：P3 行残缺、P4 证据整行缺失（P1，未闭合前 BLOCKED）

#### 证据
- §五 Probe C 上游表（line 67-71）：P1（manifest.json，50 audited Rhea）、P2（truth_records.json 50 + split_manifest.json 30/10/10）有完整路径；**P3 行在 `| P3 | \`** 处截断**，P4 行整体不存在。
- §三提交声称 "P4 status **READY**（14/14 gate PASS）"，但包内无对应证据。
- Gate 输出（Probe A）声称 `Upstream: P3=READY, P4=READY`，属自述，非独立证据。

#### 影响
- P5-G04 明确依赖 `blocked_by_p3_missing` / `blocked_by_p4_missing`；上游 P3/P4 证据缺失意味着 P5 指标输入链完整性无法独立核实 → 该维度 BLOCKED，禁止编造 PASS。

#### 修复要求
1. 补齐 P3、P4 制品路径与关键字段（gate report、记录计数、manifest）。
2. Round 2 审核据此逐项核对 upstream readiness，缺失即维持 BLOCKED。

### P5-R1-05 — 上一轮 mandatory findings 未找到，关闭状态无法逐条核对（P1，未闭合前 BLOCKED）

#### 证据
- §六（line 73-75）："上一轮 mandatory findings（必须逐条核对关闭状态）**（未找到 findings 标题）**"。
- 任务书 §八.2 要求"判定各 finding 关闭状态（Closed/Partial/Open）"。

#### 影响
- Finding closure matrix 无法构建；无法确认 Round 0 遗留问题已关闭。fail-closed 下不得默认 Closed。

#### 修复要求
1. 提交方提供上一轮（Round 0）findings 清单或书面确认该轮无 findings，并附出处。
2. Round 2 逐条核对关闭状态；凡无法溯源的 finding 一律按 Open 处理。

---
说明：以上 finding 仅基于任务书内载证据；LayerM 校验错误的完整字段信息在任务书中被截断，修复时须以实际重放的完整 traceback 为准（此为 P5-R1-01 修复步骤的一部分，不构成对本 finding 证据的扩充）。

---

## 4. RED→GREEN 测试要求（强制）

1. **先写 RED tests**：为每个 finding 写负向测试（攻击场景），运行确认失败（RED）。
2. 再实施修复（GREEN）。
3. 全部验证命令必须实际运行并记录输出（见审核报告 §1 的验证命令）。

## 5. 复审准入条件（全部满足方可申请重测）

1. 每个 finding 的修复要求全部落实，负向测试覆盖对应攻击场景。
2. 负向测试 + 正向对照已提交且全绿；变异自检通过（抽查任一用例被注释后 pytest 必须红）。
3. 重跑独立 probe（若审核报告有）：伪造路径必须被拒绝。
4. 不得伪造 PASS；BLOCKED 项保持诚实 BLOCKED。

## 6. 禁止事项

- 不得修改上游合同 / frozen 文件 / P0 ADRs / final_design / final_plan
- 不得伪造 real / Gate PASS；machinery 缺陷不得被 BLOCKED 掩盖
- 不得 commit / push / merge / 安装依赖（环境已就绪）
- 不得修改其他阶段（P1/P2/P3）的冻结产物

## 7. 交付物（完成标准）

1. `reports/p5/P5_ROUND_2_REMEDIATION_WORKLOG.md`（逐 finding 记录：RED 证据 → 修复 → GREEN 证据）
2. `reports/p5/P5_ROUND_2_STARTING_WORKTREE_STATE.md`（§2 起始状态）
3. 新增/修改的测试与实现代码（含负向测试）
4. `reports/p5/SUBMISSION_TO_CHATGPT_P5_ROUND_2.md`（提交封面，含验证矩阵 + probe 重跑结果）

完成后停止，保持 P5 BLOCKED，等待 Round 2 复审。

---

*Generated by run_kimi_audit.py（kimi-k3 裁决 + 独立验证）。*
