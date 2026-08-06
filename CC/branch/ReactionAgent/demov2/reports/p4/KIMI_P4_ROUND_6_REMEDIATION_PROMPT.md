# Kimi P4 Round 6 Remediation Instructions

## 1. 任务与正式审计状态

你正在修复 ReactionAgent 的 P4。kimi-k3 已完成 Round 5 只读审核（独立裁决）+ 独立验证。

正式状态为：

```text
P4_ROUND_5_READ_ONLY_AUDIT_FAIL
P4_IMPLEMENTATION_COMPLETE = NOT_ACCEPTED
P5_INTEGRATION = BLOCKED
```

本轮是 **P4 Round 6 定向修复**。目标是建立真正的信任根与上游权威绑定，而不是继续给调用方自填字段增加更多自签名 hash。这不是架构重写，不是下一阶段开发，也不是修改冻结合同来适配代码。真实上游权威缺失可以继续诚实标记 `BLOCKED`，但任何 machinery / boundary 缺陷必须使审计状态为 `FAIL`，不能被 BLOCKED 掩盖。

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

开始前必须运行并记录起始状态（写入 `reports/p4/P4_ROUND_6_STARTING_WORKTREE_STATE.md`）：

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

### P4-R5-01 — P1/P2 receipt 校验器接受伪造 receipt，owning-frozen verifier 不构成信任边界（P0）

#### 证据
任务书第五节 Probe A（审计者独立 probe，实测结果）：
- 构造方法：仅用公开常量 + 自洽 hash 构造 receipt，不声明 case_id / query_id / fold_id / snapshot_id / snapshot_hash / artifact_root。
- 实测结果：`"p2_verifier_reasons": []`、`"p1_verifier_reasons": []`、`"p2_forged_passes": true`、`"p1_forged_passes": true`。
- 根因（代码级，任务书已定位到函数）：
  - `reaction_agent/authority/receipts.py` `_verify_receipt_shape` 只强制 6 个字段（run_id / session_nonce / gate_version / status / gate_items_hash / receipt_hash），绑定字段全部可选；
  - `verify()` 只检查 hash 自洽、`status == 公开常量`、`gate_version == 公开常量`；
  - `_cross_bind` 的跳过逻辑：`if exp and receipt.get(field) and receipt[field] != exp` —— receipt 不声明该字段即跳过比对，缺失不触发拒绝；
  - `gate_items_hash` 无内容验证，不绑定真实 Gate 执行内容。

#### 影响
伪造 P1/P2 receipt 可通过 owning-frozen verifier，Round 4 声称的"内容绑定 + owning verifier"边界在 receipt 层完全不成立。任何能写 receipt 文件的实体均可伪造 P1/P2 权威通过状态，fail-closed 被直接绕过。这是 P4 安全模型的命门缺陷，且是 P4-R5-02 完整伪造链的必要环节。

#### 修复要求
1. `_cross_bind` 改为 fail-closed on absence：凡 verifier 侧持有期望值（exp 非空）的绑定字段（case_id / query_id / fold_id / snapshot_id / snapshot_hash / artifact_root），receipt 必须声明且相等；缺失即拒绝，不得跳过。
2. `_verify_receipt_shape` 将上述绑定字段列为必填。
3. `gate_items_hash` 必须绑定真实 Gate 执行内容：verify 时用实际 gate items 重算 hash 比对，而非仅检查字段存在/自洽。
4. 新增负向测试：缺少绑定字段的伪造 receipt 必须被拒；hash 自洽但无内容绑定的伪造 receipt 必须被拒。
5. 关闭条件：Probe A 复跑，两个 `*_forged_passes` 均为 false，且 verifier reasons 非空。

### P4-R5-02 — 完整伪造链经 P3InterfaceConsumer 产出 REAL bundle（P0）

#### 证据
任务书第五节 Probe B（审计者独立 probe，实测结果）：
- 方法：伪造 pin（指向真实 manifest、hash 正确、status=accepted）+ 伪造自洽 artifact（`evidence_kind=real`、`capability=True`）+ 伪造 P1/P2 报告（自洽 receipt）→ 经 `P3InterfaceConsumer.load()` + `resolve_bundle()`。
- 实测结果：`"state_present": true`、`"state_capability_available": true`、`"bundle_source": "p3_current_run"`、`"bundle_evidence_kind": "real"`、`"bundle_capability_available": true`、`"bundle_blocked_reasons": []`、`"FORGED_REAL_BUNDLE_PRODUCED": true`。

#### 影响
实际信任根是 `reports/p3/current_run_artifact.json`、`reports/p2/P2_GATE_REPORT.json`、`reports/p1/P1_GATE_REPORT.json` 三个路径的文件系统写权限，而非 Round 4 声称的内容绑定。pin 只绑定 manifest，不保护 artifact 与 receipts：P1/P2/P3 任一进程被攻破或输出被注入，伪造的 "real + capability available" 状态即向下游传播。按任务书公平性声明，攻击前提是这三个权威输出目录可写——即边界等价于目录权限，这在多进程/多 agent 管线中不成立。P5 在此缺陷关闭前必须保持 BLOCKED。

#### 修复要求
1. 绑定链延伸：pin 必须绑定 artifact 内容 hash（不仅是 manifest）；`resolve_bundle()` 必须对 artifact 内容重算 hash 并与 pin/manifest 链交叉验证，任一环节缺失或不匹配即 fail-closed。
2. artifact 的 `evidence_kind=real` / `capability=True` 不得仅凭自声明字段生效，必须有经 R5-01 修复后内容绑定的 receipt 背书。
3. 消费端（P3InterfaceConsumer）交叉验证 artifact hash ↔ pin ↔ receipts 三方一致性。
4. 新增负向测试：自洽伪造 artifact + 伪造 receipt 输入 `resolve_bundle()` 必须被拒且 blocked_reasons 非空。
5. 关闭条件：Probe B 复跑，`FORGED_REAL_BUNDLE_PRODUCED` 为 false。

### P4-R5-03 — 提交的 p4 测试套件独立重放失败，"273 passed" 声称不可复现（P1）

#### 证据
- 任务书第三节提交声称：`python -m pytest -q -p no:cacheprovider tests/p4` → 273 passed。
- 任务书第四节审计者独立重放：FAIL —— `ack_scenarios.py::TestCrossBindFailClosed::test_positive_matching_both_sides_passes`，`AssertionError: assert ['p3_p2_recei...ion_registry'] ==`（重放输出在任务书中被截断，仅能确认至少 1 例失败，实际通过总数未经核实）。
- 其余三项重放与声称一致：contracts OK、mutations 14/14 CAUGHT、probes 12/12 rejected。

#### 影响
状态声明 `P4_ROUND_5_IMPLEMENTATION_COMPLETE_..._READY_FOR_AUDIT` 不成立：提交方自己的 S1–S5 fail-closed 场景套件是红的，且失败用例正是 cross-bind 正向匹配场景——与 R5-01 的绑定字段语义缺陷同源的可能性极高。未经独立重放通过的声称行一律不作数。

#### 修复要求
1. 修复 `TestCrossBindFailClosed::test_positive_matching_both_sides_passes`：核对期望的绑定 registry 列表与实现实际产出的差异，根因大概率是 R5-01 中绑定字段"声明才比对"的语义——随 R5-01 一并修。
2. 全量重跑 `tests/p4` 至全绿，并附 pytest-json-report 产物作为可复核证据。
3. Round 6 提交的所有验证矩阵行必须附可直接复跑的命令与原始输出。
4. 关闭条件：独立重放 `pytest tests/p4 -q -p no:cacheprovider` exit 0，通过数与声称一致。

### P4-R5-04 — P4 gate real-input 仍 BLOCKED（G13/G14），P4 不得判 PASS（P1）

#### 证据
任务书第四节独立重放 `python3 -m scripts.run_p4_gate`：FAIL（exit 2）—— `[BLOCKED] P4-G13: real evidence available BLOCKED: evidence is synthetic-only; real P3 chemistry absent`、`[BLOCKED] P4-G14: P2 truth authority valid BLOC...`（输出截断）。与提交方自称的 machinery 11/11 PASS、real-input 3/3 BLOCKED 一致。

#### 影响
此项为诚实的 fail-closed 状态（非伪造 PASS），本身值得肯定；但它意味着 P4 gate 未通过、P5 保持 BLOCKED，直到存在真实 P3 化学证据与有效 P2 权威。且须注意：在 R5-01/R5-02 未关闭的情况下，当前"唯一缺口是 real evidence"的状态同时是攻击面——伪造的 "real" 会被当作 real 接受（Probe B 已证实）。

#### 修复要求
1. 不得为让 gate 转绿而改动 G13/G14 判定逻辑或注入 synthetic 证据；保持 fail-closed。
2. 取得真实 P3 run 证据与有效 P2 truth authority 后再求 gate exit 0。
3. 前置依赖：R5-01、R5-02 必须先关闭，确保 G13 的 "real evidence" 判定无法被 synthetic-forged-real 满足。
4. 关闭条件：真实证据下 `run_p4_gate` exit 0；且 Probe B 类伪造输入仍被 G13/G14 拒绝（负向测试）。

### P4-R5-05 — 上一轮 findings 关闭状态无法从审核包验证，fail-closed 下视为未关闭（P1）

#### 证据
- 任务书第六节"上一轮 mandatory findings（必须逐条核对关闭状态）"下仅有一行："（未找到 findings 标题）"。
- 任务书第四节"4. 代码级证据"表为空（只有表头 `| 位置 | 证据 |`，无任何行）。

#### 影响
Round 4 → Round 5 的 finding 闭环无法核验：按 fail-closed 与"无法验证 → 不得编造 PASS"原则，上一轮全部 mandatory findings 只能记为 Open/Unverifiable，审核报告第 2 节（closure matrix）无法给出任何 Closed 判定。审核包自身证据链不完整，也削弱了本轮提交的可审性。

#### 修复要求
1. Round 6 提交必须附 finding-closure 附录：逐条列出 Round 4（及本轮 R5-01~R5-05）每个 finding 的关闭状态 + file:line 级代码证据 + 对应测试名。
2. 审核包第 4 节代码级证据表不得留空；引用代码须给 file:line。
3. 关闭条件：下一轮审核能仅凭任务书内证据逐条复核关闭状态，无需审计者自行考古。

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

1. `reports/p4/P4_ROUND_6_REMEDIATION_WORKLOG.md`（逐 finding 记录：RED 证据 → 修复 → GREEN 证据）
2. `reports/p4/P4_ROUND_6_STARTING_WORKTREE_STATE.md`（§2 起始状态）
3. 新增/修改的测试与实现代码（含负向测试）
4. `reports/p4/SUBMISSION_TO_CHATGPT_P4_ROUND_6.md`（提交封面，含验证矩阵 + probe 重跑结果）

完成后停止，保持 P5 BLOCKED，等待 Round 6 复审。

---

*Generated by run_kimi_audit.py（kimi-k3 裁决 + 独立验证）。*
