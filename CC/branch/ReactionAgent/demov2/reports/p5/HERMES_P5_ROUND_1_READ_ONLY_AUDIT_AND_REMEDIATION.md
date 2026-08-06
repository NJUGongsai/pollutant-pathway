# P5 Round 1 Read-Only Audit and Round 2 Remediation

**Audit date:** 2026-08-05
**Audited worktree:** `/Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2`
**Auditor:** kimi-k3（独立裁决，经 Hermes）+ 独立验证
**Submitted entry:** `/Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p5/SUBMISSION_TO_CHATGPT_P5.md`

---

## 0. Verdict

P5_ROUND_1_READ_ONLY_AUDIT_FAIL
P5_ROUND_2_REMEDIATION_REQUIRED
P6_BLOCKED

一句理由：独立重放（任务书第四节）实测 `pytest tests/p5` 失败——`tests/p5/test_p5_real_data.py::TestRealSixLayer::test_data_layer_real_counts` 抛 pydantic `LayerM...` validation error，与提交方声称的"83 passed"及 Probe B 的"83 passed"直接矛盾；按 fail-closed 原则实测 FAIL 优先于任何自述/旁证，且 Probe C 上游真实链证据表在 P3 行被截断（无 P4 行）、第六节明确"未找到 findings 标题"致上一轮 findings 关闭状态无法核对，故判 FAIL，P6 阻塞直至 Round 2 整改后重审通过。

---

## 1. Independent verification matrix

提交声称：

| P5 invariant tests | **83 passed**（60 原 + 23 real_data） |
| P5 Gate | **PASS**（7 pass, 0 block, 0 fail） |
| P4 status | **READY**（14/14 gate PASS） |

独立重放：

- p5 测试: FAIL `pytest tests/p5 -q -p no:cacheprovider`
  → onError: 1 validation error for LayerM... [31mFAILED[0m tests/p5/test_p5_real_data.py::[1mTestRealSixLayer::test_data_layer_real_counts[0m - pydan
- contracts: OK（exit 0） `pytest tests/contracts -q -p no:cacheprovider`
  → .[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m

## 2. Finding closure matrix

证据基础：HANDOFF_p5_R1.md 第六节「上一轮 mandatory findings（必须逐条核对关闭状态）」（L73–75）。该节下任务书仅记录一句：「（未找到 findings 标题）」。任务书所引用的上一轮文档为 `reports/p5/HERMES_P5_ROUND_0_STARTING_STATE.md`——从题名看是 Round 0 起始状态记录，而非含 mandatory findings 清单的审核报告；且任务书作者已明示在其中未定位到 findings 标题。本输出严格限于任务书内证据，未执行任何额外读取/验证。

| Finding ID | 标题 | 等级 | 关闭状态 | 依据 |
|---|---|---|---|---|
| —（无可枚举条目） | 证据包中不存在任何上一轮 finding 的 ID / 标题 / 修复要求 | — | BLOCKED（无法验证） | HANDOFF_p5_R1.md §六 L73–75：「（未找到 findings 标题）」；证据包内无逐条可核对对象 |

判定说明：

- 可逐条核对的上一轮 findings 数量：0。不存在可判 Closed / Partial / Open 的具体条目。
- 依任务书 §七.5（无法验证 → BLOCKED，禁止编造 PASS）与 §七.1 fail-closed（宁可错杀，不可放过）：本节不得记为「全部 Closed」或「无遗留问题」。上一轮 findings 关闭状态整体记为 BLOCKED / 未证实，而非 vacuous pass。
- 此 BLOCKED 的性质为证据包程序性缺口（任务书未装载上一轮 findings 或其不存在之证明），不直接等同于代码缺陷；但对本轮审核而言效果相同：关闭性未获证据支持。
- 解除条件（供 Round 2 前置）：提交方须提供下列二者之一——(a) HERMES_P5_ROUND_0_STARTING_STATE.md 中「本轮无 mandatory findings」的显式声明及该文相关段落引用（file:line）；或 (b) 上一轮 findings 完整清单，供逐条重做关闭核对。在此之前本项维持 BLOCKED，并作为 P5-R1 审核结论的一项负向输入。

---

## 3. Mandatory findings

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

## 4. Remediation requirements

依据任务书第三~六节证据，独立重放（第四节）与提交声称/Probe B（第三节、第五节）存在直接矛盾，fail-closed 判定 FAIL。下一轮（Round 2）最小整改清单如下，按优先级排列。

### R2-01 (P0) — 修复 `test_data_layer_real_counts` 的 LayerM... ValidationError（根因，非症状）

- 依据：第四节独立重放 `pytest tests/p5 -q -p no:cacheprovider` → FAILED `tests/p5/test_p5_real_data.py::TestRealSixLayer::test_data_layer_real_counts`，报 `1 validation error for LayerM...`（pydantic，错误文本被截断）。
- 整改要求：定位真实数据送入六层模型（LayerM...）时校验失败的根因（数据缺字段/类型不符/模型定义与真实 snapshot 不匹配的哪一种），修复数据生产侧或模型定义侧使其一致。禁止通过放宽 schema（加 Optional/默认值/关闭 strict）或弱化断言来让测试变绿。提交完整的、未截断的错误输出。
- 关闭条件：审核者用同一环境（anaconda3 Python 3.11）重放 `pytest tests/p5 -q -p no:cacheprovider` 退出码 0、全绿，且该用例在列。
- 负向测试：构造一条缺失必填层字段或字段类型错误的六层记录 → 必须仍抛 ValidationError 且测试套件必须能捕获到失败（证明 schema 未被放宽、断言未被削弱）。

### R2-02 (P0) — 消除"83 passed"与独立重放 FAIL 的证据矛盾

- 依据：第三节声称 83 passed；Probe B（第五节）实测 83 passed；第四节独立重放同命令 FAIL。三者不可同时为真。
- 整改要求：提交方给出可复现的完整原始日志（精确命令、Python 解释器路径、工作目录、退出码、未截断输出），并解释与第四节差异的来源（环境差异、缓存、测试选择、代码在两次运行间被改动等）。日志归档至 `reports/p5/`。
- 关闭条件：审核者在 worktree 当前 HEAD 上以同一命令独立重放，结果与提交方日志一致（退出码 0）。
- 负向测试：临时向 `tests/p5` 注入一个必失败断言 → 该命令必须退出非零；若仍报 83 passed 则证明日志/流程造假，直接 FAIL 到底。

### R2-03 (P0) — Gate 与测试套件结果脱钩必须解释或接线

- 依据：Probe A 显示 `scripts/run_p5_gate.py` exit 0、PASS（7/0/0，mutations 14/14 caught），而同一轮独立重放 p5 测试 FAIL。P5 Gate 全绿与测试套件红灯并存，说明 real_data 诚实性测试的失败不构成 gate 阻塞项，或 gate 运行在与测试不同的代码状态上。
- 整改要求：二选一——(a) 将 `pytest tests/p5` 结果接入 `run_p5_gate.py` 作为阻塞检查（gate 的 upstream/checks 中显式包含）；或 (b) 书面论证 gate 与测试套件各自覆盖不变量的边界，并证明 G01–G07 已覆盖该失败用例所断言的性质（six-layer real counts）。无法论证则必须走 (a)。
- 关闭条件：gate 报告与测试套件状态一致——测试 FAIL 时 `run_p5_gate.py` 非 PASS（exit != 0 或 status != PASS）。
- 负向测试：注入一个 p5 测试失败 → 重跑 `run_p5_gate.py`，必须转为 FAIL/BLOCK，且 `P5_GATE_REPORT.json` 中对应计数变化可追溯。

### R2-04 (P1) — 补齐 Probe C 上游真实链证据（P3 行截断、P4 行缺失）

- 依据：第五节 Probe C 表格在 P3 行被截断（`P3 | \`` 戛然而止），P4 完全无行；仅 P1（`reports/p1/real_snapshot/snap_19caddc6b312/manifest.json`，50 audited Rhea）与 P2（`reports/p2/truth_records.json` 50 条 + `split_manifest.json` 30/10/10）有完整证据。但 Probe A 声称 Upstream: P3=READY, P4=READY。
- 整改要求：补齐 P3、P4 的 artifact 路径 + 计数/状态证据（file:line 级引用），使上游 READY 声明可独立开包验证。
- 关闭条件：审核者逐一打开所引路径，计数与声称一致。
- 负向测试：临时移除/改名任一上游 artifact → `run_p5_gate.py` 必须转为 BLOCK（证明上游检查真实接线，而非硬编码 READY）。

### R2-05 (P1) — 上一轮 mandatory findings 无法定位，关闭状态不可审

- 依据：第六节"（未找到 findings 标题）"——在 `reports/p5/HERMES_P5_ROUND_0_STARTING_STATE.md` 中未检索到 findings 章节，Round 0 findings 的 Closed/Partial/Open 无法逐条核对。
- 整改要求：提交方提供 Round 0 findings → 关闭证据的显式映射表（每条 finding 附 file:line 或命令输出）；若 Round 0 确无 findings，须引用该文档相应段落原文佐证。
- 关闭条件：审核者逐条复核通过；任一 finding 无法给出关闭证据 → 按 Open 处理并计入 Round 2 findings。
- 负向测试：不适用（文档完整性要求），但映射表中引用失效路径/行号即视为未关闭。

整改完成前状态码维持：`P5_ROUND_2_REMEDIATION_REQUIRED` / `P6_BLOCKED`。

---

*Generated by run_kimi_audit.py (kimi-k3 via Hermes).*
