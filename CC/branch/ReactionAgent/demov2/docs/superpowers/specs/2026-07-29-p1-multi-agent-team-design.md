# P1 多智能体团队设计 — Reaction Analogy Agent

> **日期：** 2026-07-29
> **服务对象：** `demov2/` P1 — Data Foundation（见 `training/chatgpt_p1_train.md`）
> **设计方法：** superpowers brainstorming
> **状态：** 待用户审查 → 转 writing-plans
> **产出边界：** 本次只做团队设计 + 实现计划，不写 P1 实现代码

---

## 0. 背景与约束

P1 是 Reaction Analogy Agent 的数据地基阶段，目标建立可信、可重放、可审计的证据层：

```
完整来源反应 → normalization → formal atom mapping → participant role hypotheses
→ bipartite fragment-lineage graph → resolved transformed lineages
→ SourceReactionLedger → eligibility / diagnostic / quarantine
→ immutable evidence snapshot → manual audit
```

P1 共 1 个 Preflight + 11 个 task（T1–T11）+ 十项 Gate。文档（`chatgpt_p1_train.md`）强制：

- **严格顺序** T1→T11，下游依赖上游冻结的 schema，不得并行编写依赖未冻结的下游模块（§5）
- **每 task** 走 READ → ASSUMPTIONS → RED → minimal impl → GREEN → full P0+P1 regression → artifact → checkpoint（§5）
- **测试先行、最小实现、真实数据优先、缺证据即 fail-closed、阶段 Gate 后再推进**（§0）
- **独立性硬要求**：双独立 annotator、formal ≠ mechanistic、审计与实现分离、不得自评 confidence 当 audit confidence（§11、§17）
- **诚实报告**：BLOCKED 比假 PASS 正确，七种 `BLOCKED_*` 状态（§23）

### 当前项目状态（2026-07-29 实测）

| 维度 | 现状 |
|---|---|
| P0 | ✅ 冻结：290 contract tests + P0 Gate 10/10 + 6 ADR + schema skeleton |
| Python/依赖 | Python 3.11.15、pydantic 2.13.4、pytest 9.1.1 |
| 缺失依赖 | rdkit / numpy / networkx / scipy **全部 absent**（与文档 §4.3 一致） |
| P1 | ❌ 未开始：无 `reports/p1/`、无 `scripts/p1_preflight.py`、无 lock 文件 |
| 阻断点 | 真实 reaction source / atom mapper / 第二位独立 annotator 均未知 |

### 用户决策（本次 brainstorming 锁定）

| 维度 | 选择 |
|---|---|
| 执行模型 | 纯 Claude Code subagent（不委派外部 qwen/glm/mimo/deepseek） |
| 阻断处理 | 先跑 Preflight 探明阻断，诚实报告 |
| 产出边界 | 设计团队 + writing-plans（本次不写 P1 代码） |
| 并行策略 | 串行交接（task 间）+ task 内并行 |

### 偏差记录（必须显式，写入 worklog 与 submission 封面）

| 项 | 文档要求 | 实际 | 处理 |
|---|---|---|---|
| 执行模型 | Qwen | Claude Code subagent | worklog + submission 封面明确记录 |
| 终审 | ChatGPT 只读审核 | 不变 | 严格遵守 |
| 权威顺序 | final_design → final_plan → final_discussion → ADRs → P0 → 本提示词 | 不变 | 严格遵守 |

---

## 1. 团队拓扑：三层架构

```
┌─────────────────────────────────────────────────────────┐
│  L0  Orchestrator（主 Claude）                           │
│  唯一串行调度者 · 持全局状态 · 判 checkpoint · 记 worklog  │
└───────────────┬─────────────────────────┬───────────────┘
                │                         │
        ┌───────▼────────┐       ┌────────▼─────────┐
        │  L1 角色专家池   │       │  L2 独立审计池    │
        │  （实现层）      │       │  （只读，不碰实现）│
        ├────────────────┤       ├──────────────────┤
        │ Preflight Scout │       │ Legacy Auditor   │
        │ architect      │       │ Annotator A      │
        │ tdd-guide      │       │ Annotator B      │
        │ code-reviewer  │       │ Adjudicator      │
        │ python-reviewer│       │ Gate Keeper      │
        │ security-review│       │                  │
        └────────────────┘       └──────────────────┘
```

### 铁律

- **L2 agent 实例永不在 L1 出现**。这是文档"不得让同一执行过程复制两份答案冒充 double annotation"（§17.1）的物理保证。
- **L2 全部只读**，不写任何实现代码（`reaction_agent/`、`tests/p1/`、`scripts/` 除外只读访问）。
- **Orchestrator 是唯一调度者**，subagent 之间不直接通信，全部经 Orchestrator 中转 artifact。

### 角色定义

| 角色 | agent 类型 | 职责 | 所在层 |
|---|---|---|---|
| Orchestrator | 主 Claude | 串行调度、checkpoint 交接、deviation 记录、worklog 维护、阻断判定 | L0 |
| Preflight Scout | Explore | 真实资源盘点、runtime/legacy/real-source/case 四项盘点、stop condition 判定 | L1 |
| Architect | architect | schema/ID/hash/ledger/snapshot/mapping-protocol 架构决策 | L1 |
| TDD Coach | tdd-guide | RED→GREEN→重构，强制 80% 覆盖、测试隔离、mock 正确 | L1 |
| Code Reviewer | code-reviewer | GREEN 后即审，CRITICAL/HIGH 必修、MEDIUM 尽量 | L1 |
| Python Reviewer | python-reviewer | PEP8、类型提示、Pythonic、不可变性、错误处理 | L1 |
| Security Reviewer | security-reviewer | logging redaction、snapshot 不可变、no-legacy-write、无硬编码 | L1 |
| Legacy Auditor | Explore（独立实例） | 只读重放 `canonical_identity.transformed_pair` 等并对比新证据 | L2 |
| Annotator A | general-purpose（独立实例） | T11 双盲标注第一人 | L2 |
| Annotator B | general-purpose（独立实例） | T11 双盲标注第二人 | L2 |
| Adjudicator | general-purpose（独立实例） | 裁决 A/B 分歧 | L2 |
| Gate Keeper | general-purpose（独立实例） | P1 十项 Gate + 八项 mutation 反假阳性 | L2 |

---

## 2. 调度矩阵：每个 task 谁介入、谁并行

| Task | 串行主线 | task 内并行 | 独立审计（L2） | Checkpoint artifact |
|---|---|---|---|---|
| **Preflight** | Explore(scout) | — | — | `reports/p1/P1_PREFLIGHT.md` + `.json` → 判 GO/PARTIAL/BLOCKED |
| **T1** Package bootstrap | architect → tdd-guide → 实现 | RED 测试 ∥ architect 审配置合同 | security-reviewer（redaction / no-legacy-write / lock） | `P1_T1_PACKAGE_BOOTSTRAP.md` |
| **T2** Strict schemas | architect → tdd-guide | RED ∥ Explore 查 P0 frozen schema 字段语义 | — | `P1_T2_DOMAIN_SCHEMAS.md` + `schemas/json/` 导出 |
| **T3** Legacy audit | Legacy Auditor（L2 独立） | — | Legacy Auditor 只读重放 | `reports/data_audit/legacy_lineage_audit.json` + `.md` |
| **T4** Mapping adapter | architect → tdd-guide | RED ∥ Explore 查 mapper backend 可用性 | — | `P1_T4_MAPPING_ADAPTER.md` + `mapping_integration_sample.json` |
| **T5** Roles/eligibility | tdd-guide → 实现 | — | — | `P1_T5_PARTICIPANT_ROLES.md` + `participant_role_sample.json` |
| **T6** Lineage graph | architect → tdd-guide | RED ∥ Explore 查 proline/2OG 真实案例 | — | `P1_T6_LINEAGE_GRAPH.md` + `lineage_regression_cases.json` |
| **T7** Source ledger | architect → tdd-guide | — | — | `P1_T7_SOURCE_LEDGER.md` + `source_ledger_samples.json` |
| **T8** Candidate ledger skeleton | tdd-guide | — | — | `P1_T8_CANDIDATE_LEDGER_SKELETON.md` |
| **T9** Eligibility/quarantine | tdd-guide → 实现 | — | — | `P1_T9_ELIGIBILITY.md` + `eligibility_matrix_execution.json` |
| **T10** Snapshot builder | architect → tdd-guide | RED ∥ security-reviewer（atomicity / read-only loader） | — | `P1_T10_SNAPSHOT.md` + `snapshot_build_sample.json` |
| **T11** Manual audit | Annotator A ∥ B（L2 双盲） | A、B 独立并行标注 | Adjudicator 裁决 | `manual_audit_*` 8 件套（§17.7） |
| **Gate** | Gate Keeper（L2 独立） | 10 项 Gate ∥ 8 项 mutation | — | `P1_GATE_REPORT.md` + `.json` |

### 并行规则

- **task 间严格串行**：上一个 checkpoint 通过才交接（文档 §5）。Orchestrator 读取上一 task 的 worklog 节 + artifact 路径，喂给下一个 agent。
- **task 内并行**：允许 RED 测试写作 ∥ architect 审假设 ∥ Explore 查证据并发（同一 task 内、无写冲突时）。
- **T11 双 annotator 真并行**：两个独立 agent 实例同时标注同一 stratified sample，互不可见对方输出。
- **每完成一个 P1 task 都必须重跑 P0 contract tests**（文档 §3）；P0 任何失败 → 立即停止当前 task，修复回归，不进下一个。

### 每 task 统一执行循环

```
READ（读权威文件 + 上一 task worklog 节 + artifact）
→ ASSUMPTIONS（写进 worklog）
→ RED tests（tdd-guide）
→ minimal implementation（architect 指导边界）
→ GREEN targeted tests
→ code-reviewer + python-reviewer 审查（CRITICAL/HIGH 必修）
→ full P0 + P1 regression
→ artifact/report 落盘
→ task checkpoint（Orchestrator 判 GO/STOP）
```

---

## 3. 数据流与 artifact 交接协议

Subagent 无跨调用状态，task 间靠三样东西交接：

```
Task N checkpoint
  ├─ reports/p1/P1_REMEDIATION_WORKLOG.md   ← 追加一节（唯一连续真相源）
  ├─ reports/p1/P1_TN_<NAME>.md             ← 该 task checkpoint 报告
  └─ 对应 .json / sample artifact           ← 机器可读证据
        │
        ▼
Orchestrator 读取上一 task 的 worklog 节 + artifact 路径
        │
        ▼
Task N+1 启动时，把上述喂给新 agent 作为前置上下文
```

### Worklog 每 task 必记字段（文档 §20）

```
timestamp
assumptions
input files/hashes
RED tests
implementation decision
changed files
targeted GREEN
full regression
real vs fixture evidence
deviations
risks
blocked items
next task authorization
```

不得只写 "implemented successfully"，必须提供精确命令、统计和 artifact path。

### 权威文件读取顺序（每 task READ 阶段）

```
plan/final_design.md
→ plan/final_plan.md
→ plan/final_discussion.md
→ docs/decisions/ADR-0001..0006
→ reports/p0/P0_GATE_REPORT.{md,json}
→ reports/p0/V4_REMEDIATION_WORKLOG.md
→ 本提示词（chatgpt_p1_train.md）
→ 上一 task 的 worklog 节 + artifact
```

如本提示词与三份 final 权威文件冲突，以 final 为准，并在 worklog 记录冲突，不静默选择（文档 §1）。

---

## 4. 阻断 / 恢复协议

### Preflight 三态判定

| 状态 | 触发条件 | 行动 |
|---|---|---|
| **GO** | 真实 source 可访问 + mapper 可装 + 核心依赖 OK + 权限明确 + 写入范围 ≤ demov2 | 正常推进 T1→T11 |
| **PARTIAL** | 部分缺（如 mapper 缺但 source 有） | 推进到能推的最远点；T4 标 `UNIT_CONTRACT_COMPLETE / INTEGRATION_BLOCKED`，不标 PASS |
| **BLOCKED** | 真实 source 不可访问 / 核心依赖装不上 / 无可用 mapper / 原始 reaction 权限不明 / 写入需超 demov2 | 停止实现，只做 read-only 诊断 + fixture 单测，报 `BLOCKED_*` + 用户需提供的具体输入 |

### 七种 BLOCKED 状态码（文档 §23）

```
BLOCKED_MISSING_REAL_REACTION_SOURCE
BLOCKED_MAPPER_UNAVAILABLE
BLOCKED_DEPENDENCY_INSTALLATION
BLOCKED_REQUIRED_CASE_MISSING
BLOCKED_MANUAL_AUDIT_INCOMPLETE
BLOCKED_CATASTROPHIC_MISMATCH
BLOCKED_SNAPSHOT_NONDETERMINISTIC
```

### 阻断时纪律

- 完成所有仍可安全完成的 read-only 诊断
- 提交 blocker evidence
- 给出需要用户提供的具体输入
- 不得构造虚假成功数据
- 不得自行扩大权限
- 不得进入下一阶段

### 恢复

用户提供输入后，从阻断 task 继续，不回退已 checkpoint 的 task。每步诚实报告。

---

## 5. Gate 与 mutation 反假阳性

Gate Keeper（L2 独立）跑两件事。

### 5.1 十项 Gate（G01–G10，文档 §18.1）

每项**读机器可读 evidence**，不只查文件存在（文档 §18.2 禁止 `passed = report_file.exists()`）：

| Gate | 验证内容 |
|---|---|
| G01 | package import / supported Python / dependency lock / explicit config & snapshot / no legacy write |
| G02 | strict schema / stable IDs / content hashes / required provenance / P0 contract still green |
| G03 | 真实 source used / counts & denominators / mismatch categories / source IDs & examples / proline-2OG included |
| G04 | real adapter integration / quality metrics / failure states / MCS not strict / formal not mechanism |
| G05 | complete participant multiset / COFACTORS no deletion / small molecule can be substrate/source / ambiguity retained |
| G06 | bipartite graph / split-merge-transfer / no independent picking / no silent tie / stable IDs / proline-2OG correct or quarantined |
| G07 | SourceReactionLedger valid / CandidateAnalogyLedger skeleton valid / unknowns preserved / formal-mechanistic separated / source linkage valid |
| G08 | all 8 policy rows / warnings / quarantine behavior / production index excludes prohibited & quarantine / all reasons typed |
| G09 | deterministic rebuild / content hash / manifest complete / all filters counted / interrupted build invalid / read-only loader |
| G10 | double annotation complete / adjudication complete / threshold frozen before results / catastrophic errors = 0 / all P0+P1 tests pass / zero fail/error/skip/xfail/xpass |

Gate 验证示例（非穷举）：
- 对 snapshot 重建两次并比较 hash
- 读 production/quarantine index 检查交集为空
- 构造 critical tie，确认不返回单一 strict lineage
- 构造 COFACTORS participant，确认完整反应仍保留
- 检查 MappingReport 不自动生成 mechanism
- 检查 manual audit annotations 来自两个不同 annotator IDs
- 结构化读取 pytest stats

### 5.2 八项 mutation（隔离临时副本，文档 §18.3）

| Mutation | 预期 |
|---|---|
| 删 participant preservation check | Gate fail |
| 让 critical tie 取 max | Gate fail |
| 让 MCS 标 full mapping | Gate fail |
| 让 mapper 自动填 mechanism | Gate fail |
| 把 quarantine record 放进 production | Gate fail |
| 让 snapshot hash 非确定 | Gate fail |
| 删 proline/2OG required case | Gate fail |
| 加一个 skipped/xfailed test | Gate fail |

mutation **只在临时副本**进行，不污染正式代码。任一 Gate fail：

```
exit code != 0
status = NOT_READY_FOR_CHATGPT_AUDIT
P2 = BLOCKED
```

---

## 6. 独立性硬要求如何落地

| 文档要求 | 落地方式 |
|---|---|
| 双独立 annotator（§17.1） | Annotator A、B = 两个独立 `general-purpose` 实例，不同 agent ID，双盲，Adjudicator 第三方裁决 |
| formal ≠ mechanistic（§10.4） | T4 架构层只产 `formal_mapped_source_assignment`；mechanistic 只接受独立 curated/isotope 证据，由 architect 在 schema 层强制 |
| 审计 vs 实现隔离 | L2 池（Legacy Auditor / Annotator A,B / Adjudicator / Gate Keeper）全部只读，不写实现代码 |
| 不得自评 confidence 当 audit confidence（§17.5） | Annotator 输出只含 agreement/disagreement/adjudication/catastrophic error count，不采信 LLM 自评 confidence |
| 阈值冻结先于结果（§17.6） | T11 启动前由 Orchestrator 在 `docs/manual_audit_protocol.md` 冻结阈值，不得看结果后调整 |
| 不得先改 legacy（§9.2） | Legacy Auditor 只读 `../benchmark/canonical_identity.py`，不修改；mismatch 不得靠改 legacy 减少 |

---

## 7. 报告规范

### 每 task 产出

- `reports/p1/P1_Tx_<NAME>.md` — checkpoint 报告
- 文档指定的 `.json` / sample artifact — 机器可读证据
- `reports/p1/P1_REMEDIATION_WORKLOG.md` 追加一节

### 最终提交（文档 §21）

`reports/p1/SUBMISSION_TO_CHATGPT_P1.md` 含 17 项封面：

1. P1 十项 Gate
2. P0 baseline 和最终回归
3. P1 targeted/full test 精确统计
4. runtime/dependency versions
5. real source manifest/hash
6. mapper backend/version
7. proline/2OG 实际结果
8. participant preservation 统计
9. lineage mismatch 统计
10. eligibility/quarantine 统计
11. snapshot deterministic rebuild 证据
12. manual audit 样本、agreement、adjudication
13. catastrophic error count
14. changed files
15. deviations/risks
16. git/user-files protection
17. P2 状态

结尾**只允许写**：

```
READY_FOR_CHATGPT_P1_READ_ONLY_AUDIT
P2 BLOCKED pending ChatGPT audit
```

绝不自行写 "P1 finally accepted / P2 authorized / system can reliably predict X→Y"。

---

## 8. 科学主线对齐（文档 §24）

团队最高优先级不是代码量，而是：

```
不丢反应
不跨 lineage
不伪造 mapping
不误删 cofactor/小分子
不静默解 ambiguity
不让 quarantine 泄漏
所有结果可追溯、可重放、可审计
```

Orchestrator 在每个 checkpoint 用这七条作为最终验收口径。

---

## 9. 未覆盖范围（明确排除）

本设计**不**涵盖以下内容（属于 P2 或后续，文档 §0 明确排除）：

- 给用户未知分子 X 检索 donor
- 把 A→B transformation 应用到 X
- 生成 Y
- 排序 candidate
- MCP tools
- LLM hypothesis orchestration
- benchmark candidate top-K performance
- enzyme activity probability
- environmental occurrence
- kinetics、yield
- multi-step pathway

P1 未通过前，团队不实现这些以"展示进展"。

---

## 10. 下一步

1. 本 spec 经用户审查通过
2. 转 superpowers:writing-plans，产出分 task 的详细实现计划（每 task 拆成可执行的 RED/impl/GREEN/regression/artifact 步骤，带 agent 分配）
3. 计划批准后，按本设计执行（本次 brainstorming 边界到 writing-plans 为止，不写 P1 代码）
