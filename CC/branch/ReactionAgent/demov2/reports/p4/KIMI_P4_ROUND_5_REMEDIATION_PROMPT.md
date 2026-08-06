# Kimi P4 Round 5 Remediation Instructions

## 1. 任务与正式审计状态

你正在修复 ReactionAgent 的 P4。kimi-k3 已完成 Round 4 只读审核（独立裁决）+ 独立验证。

正式状态为：

```text
P4_ROUND_4_READ_ONLY_AUDIT_FAIL
P4_IMPLEMENTATION_COMPLETE = NOT_ACCEPTED
P5_INTEGRATION = BLOCKED
```

本轮是 **P4 Round 5 定向修复**。目标是建立真正的信任根与上游权威绑定，而不是继续给调用方自填字段增加更多自签名 hash。这不是架构重写，不是下一阶段开发，也不是修改冻结合同来适配代码。真实上游权威缺失可以继续诚实标记 `BLOCKED`，但任何 machinery / boundary 缺陷必须使审计状态为 `FAIL`，不能被 BLOCKED 掩盖。

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

开始前必须运行并记录起始状态（写入 `reports/p4/P4_ROUND_5_STARTING_WORKTREE_STATE.md`）：

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

## 3. Mandatory findings

### P4-R4-01 — P1/P2 receipt 可伪造：owning-frozen verifier 接受自洽伪造 receipt（P0）

#### 证据
任务书 §五 Probe A（审计者独立 probe，已实测）：仅用公开常量 + 自洽 hash 构造 receipt，不声明 case_id/query_id/fold_id/snapshot_id/snapshot_hash/artifact_root，结果为 `"p2_verifier_reasons": [], "p1_verifier_reasons": [], "p2_forged_passes": true, "p1_forged_passes": true`。根因定位（`reaction_agent/authority/receipts.py`）：
- `_verify_receipt_shape` 只强制 6 字段（run_id/session_nonce/gate_version/status/gate_items_hash/receipt_hash），不强制任何 cross-bind 字段；
- `verify()` 仅检查 hash 自洽、`status == 公开常量`、`gate_version == 公开常量`；
- `_cross_bind` 逻辑为 `if exp and receipt.get(field) and receipt[field] != exp`——receipt 不声明字段即跳过比较；
- `gate_items_hash` 无内容验证，不绑定真实 Gate 执行内容。

#### 影响
P1/P2 receipt 不构成上游权威：任何知道公开常量（status/gate_version 字面值）的一方均可铸造 verifier 接受的 "accepted" receipt，且 verifier 零 reason。Round 4 声称的 "owning verifier" 边界被直接击穿；上一轮 P4-R3-A、P4-R3-C 的修复声称不成立。

#### 修复要求
1. receipt shape 强制声明全部 cross-bind 字段（case_id/query_id/fold_id/snapshot_id/snapshot_hash/artifact_root，按各 gate 适用集），缺失即拒绝并给出 typed failure code；
2. `_cross_bind` 改为 fail-closed：任一期望字段在 receipt 侧缺失即拒绝，不得跳过；
3. `gate_items_hash` 必须由 verifier 从上游已注册 gate 执行内容重算比对，禁止接受自声明值；
4. 新增负向测试：Probe A 构造（省略 cross-bind 字段的自洽伪造 receipt）必须被拒，且返回明确 typed failure code。

### P4-R4-02 — 完整伪造链产出 REAL bundle：信任根是文件系统权限而非内容绑定（P0）

#### 证据
任务书 §五 Probe B（审计者独立 probe，已实测）：伪造 pin（指向真实 manifest、hash 正确、status=accepted）+ 伪造自洽 artifact（`evidence_kind=real`、`capability=True`）+ 伪造 P1/P2 报告（自洽 receipt），经 `P3InterfaceConsumer.load()` + `resolve_bundle()` 后：`"state_present": true, "state_capability_available": true, "bundle_evidence_kind": "real", "bundle_capability_available": true, "bundle_blocked_reasons": [], "FORGED_REAL_BUNDLE_PRODUCED": true`。公平性声明：攻击前提为可写 `reports/p3/current_run_artifact.json`、`reports/p2/P2_GATE_REPORT.json`、`reports/p1/P1_GATE_REPORT.json`。

#### 影响
凡能写上游权威输出目录的调用方，即可伪造 evidence_kind=real、capability_available=true 且 blocked_reasons 为空的 REAL bundle。这直接否定 Round 4 声称的 "内容绑定 + owning verifier" 边界：pin 只绑定 manifest，artifact 内容与 receipts 均不受保护；artifact 的 real/capability 属性实为文件自声明。科学正确性命门（证据内容真实性）仍可被调用方重造——上一轮 P4-R3-B 未被关闭。

#### 修复要求
1. `evidence_kind` / `capability_available` 必须由消费者从上游已注册、内容绑定的记录推导，禁止采信 artifact 文件自声明字段；
2. pin 必须同时绑定 artifact 内容 hash 与所依赖 receipt 的 hash，不得仅绑定 manifest；
3. `load()`/`resolve_bundle()` fail-closed：artifact 内容无法从已注册上游输出重现时拒绝；
4. 新增负向测试：Probe B 全链（伪造 pin + artifact + receipts）必须被拒并返回 typed failure code。

### P4-R4-03 — 上一轮 mandatory findings 未关闭（P4-R3-A/B/C 复发，P4-R3-D 不可验证）（P0）

#### 证据
- P4-R3-A（self-attested bundle/receipts/pin，P0）：Probe A + Probe B 直接复现——receipt 可伪造、pin 不保护 artifact → **Open**。
- P4-R3-B（候选结构/特征值/证据内容调用方可重算，P0）：提交方声称两条拒绝探针通过（`p4_production_bundle_unregistered`、`p4_production_bundle_not_consumer_object`，任务书 §三），但 Probe B 证明在上游输出目录可写时，调用方伪造的 "real" 证据内容仍被接受 → **Open**（注册路径本身信任调用方产物，拒绝路径只覆盖未注册情形）。
- P4-R3-C（上游 hash 与接口校验可选/自声明，P1）：`_cross_bind` 条件跳过 + shape 不强制字段（Probe A 根因）→ **Open**。
- P4-R3-D（Round 3 audit receipts 与 changed-file 计数内部不一致，P1）：任务书未提供任何对账证据，且 §四 独立重放已跳过 → **不可验证，按 fail-closed 计 Open**。

#### 影响
Round 4 未关闭上一轮任何一条 P0/P1 mandatory finding；按任务书 §七 fail-closed 规范，本轮不得判 PASS。

#### 修复要求
按 P4-R4-01 / P4-R4-02 的修复项逐条关闭 R3-A/B/C；对 R3-D 提交 audit receipt 计数与 changed-file 清单的对账表；每条上一轮 finding 附专属负向测试证明拒绝路径生效。

### P4-R4-04 — 提交声称的验证矩阵未获独立确认；real-input 路径仍为 BLOCKED（P1）

#### 证据
任务书 §四 标题声称 "审计者已实测"，正文却为 "（验证重放已跳过）"——二者矛盾，§三 全部数字（tests/p4 248 passed、tests/contracts 290 passed、mutations 14/14 CAUGHT、probes 12/12 rejected）实际仅来自提交方自述。另 §三 自认 `python -m scripts.run_p4_gate` exit 2：machinery 11/11 PASS 但 real-input 3/3 BLOCKED。

#### 影响
按审核规范 2（不信任自述）与 5（无法验证 → BLOCKED），上述 PASS 计数均不能记为已验证；real 输入端到端路径从未跑通，P4 gate 对真实数据的行为无任何证据。

#### 修复要求
1. Round 5 提交可独立重放的验证物：每条命令的 pytest-json-report 输出文件、命令行、exit code 及文件 hash；
2. real-input 3/3 BLOCKED 项必须实际执行并给出结果，或明确保持 BLOCKED 并说明阻塞原因；禁止以 machinery PASS 替代 real-input 证据。

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

1. `reports/p4/P4_ROUND_5_REMEDIATION_WORKLOG.md`（逐 finding 记录：RED 证据 → 修复 → GREEN 证据）
2. `reports/p4/P4_ROUND_5_STARTING_WORKTREE_STATE.md`（§2 起始状态）
3. 新增/修改的测试与实现代码（含负向测试）
4. `reports/p4/SUBMISSION_TO_CHATGPT_P4_ROUND_5.md`（提交封面，含验证矩阵 + probe 重跑结果）

完成后停止，保持 P5 BLOCKED，等待 Round 5 复审。

---

*Generated by run_kimi_audit.py（kimi-k3 裁决 + 独立验证）。*
