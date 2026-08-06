# P4 Round 9 — 真实数据审核提交任务书

**目标：** P4 gate 已全绿（G01-G14 全 PASS，status `READY_FOR_CHATGPT_P4_READ_ONLY_AUDIT`）。本次任务：**全量验证 → 生成 Round 9 提交材料 → 送 kimi Round 9 复审**。

**背景：** 50 条真实 Rhea audited cases 已接入 P2/P3/P4 管道，真实 evidence 链路打通。上一轮 kimi Round 8 裁决 BLOCKED（原因：synthetic-only evidence + 验证重放跳过）。本轮 real evidence 就位，P4 gate 已转绿。

---

## 一、工作树与关键文件

```text
P4 worktree: /Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2
```

**本轮新增/修改（真实数据接入）：**

| 文件 | 说明 |
|---|---|
| `reports/p3/current_run_artifact.json` | P3 kernel real 产物（evidence_kind=real, status=completed, case_id=real_audit_case_001, 1 candidate） |
| `reports/p3/p3_p4_interface_pin.json` | pin（status=accepted, 匹配 manifest） |
| `reports/p2/P2_GATE_REPORT.json` | P2 receipt 格式（status=READY_FOR_CHATGPT_P2_AUDIT, 六身份字段齐全） |
| `reports/p1/P1_GATE_REPORT.json` | P1 报告（status=READY_FOR_CHATGPT_P1_AUDIT, 10/10 PASS） |
| `scripts/run_p4_gate_real.py` | **关键脚本**：collector + gate，注册 P1/P2 receipt 到 process-local registry 后同进程跑 gate |
| `scripts/build_real_snapshot.py` | P1 真实 snapshot 构建 |
| `scripts/build_real_train_view.py` | P3 train view 构建 |
| `scripts/run_real_kernel.py` | P3 kernel real 运行 |
| `scripts/produce_current_run_artifact.py` | current_run_artifact 生产者 |
| `scripts/build_real_mini_benchmark.py` | P2 真实 mini benchmark 构建（P2 worktree） |
| `scripts/run_real_p2_gate.py` | P2 receipt 生成（P2 worktree） |
| `data/audited_cases/audited_cases_50.json` | 50 条真实候选案例（主目录） |

**真实数据源：** `/Volumes/CC/Enzyme_Agent/depending/data/rxn2enzyme_positives.pkl`（3601 条 Rhea 真实反应，只读勿改）

---

## 二、全量验证（必须全部实际运行并记录输出）

```bash
cd /Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2

# 1. P4 测试套件
/opt/anaconda3/bin/python3 -m pytest -q -p no:cacheprovider tests/p4
# 2. contracts
/opt/anaconda3/bin/python3 -m pytest -q -p no:cacheprovider tests/contracts
# 3. 合并套件
/opt/anaconda3/bin/python3 -m pytest -q -p no:cacheprovider tests/p4 tests/contracts
# 4. mutations（应有 14/14 CAUGHT）
/opt/anaconda3/bin/python3 -m scripts.run_p4_mutations
# 5. round4 probes（应有 12/12 rejected）
/opt/anaconda3/bin/python3 scripts/run_p4_round4_probes.py
# 6. round5 probe A（伪造 receipt 应被拒）
/opt/anaconda3/bin/python3 scripts/run_p4_round5_probe_a.py
# 7. P4 gate REAL（关键！应有 G01-G14 全 PASS）
/opt/anaconda3/bin/python3 scripts/run_p4_gate_real.py
```

**预期结果：** 全部通过；gate status = `READY_FOR_CHATGPT_P4_READ_ONLY_AUDIT`。

---

## 三、生成 Round 9 提交材料

### 3.1 `reports/p4/SUBMISSION_TO_CHATGPT_P4_ROUND_9.md`

参考 `SUBMISSION_TO_CHATGPT_P4_ROUND_8.md` 格式，更新：

- **状态声明：**
  ```text
  P4_ROUND_8_READ_ONLY_AUDIT_BLOCKED（真实数据接入完成，等待复审）
  P4_IMPLEMENTATION_COMPLETE = READY_FOR_CHATGPT_P4_READ_ONLY_AUDIT
  P5_INTEGRATION = BLOCKED（待 P4 复审通过后解锁）
  ```
- **验证矩阵**（用 §二 的实际输出，附命令 + exit code + 计数）：
  - `pytest tests/p4` → N passed
  - `pytest tests/contracts` → N passed
  - 合并套件 → N passed
  - `run_p4_mutations` → 14/14 CAUGHT
  - `run_p4_round4_probes` → 12/12 rejected
  - `run_p4_round5_probe_a` → forged_passes=false
  - `run_p4_gate_real` → **G01-G14 全 PASS, status=READY_FOR_CHATGPT_P4_READ_ONLY_AUDIT**
- **关闭项：**
  - **P4-R6-01（G12/G13/G14 BLOCKED）** → **Closed**：真实证据接入，G12/G13/G14 全 PASS
  - **P4-R6-02（审计包证据截断）** → Closed（上轮已修，gate 完整输出随包）
  - **P4-R6-03（Probe accepted 字段）** → Closed（上轮已修，probe_run_accepted）
- **本轮新增：真实数据接入说明**
  - 50 条真实 audited cases（`data/audited_cases/audited_cases_50.json`）
  - P1/P2/P3 真实证据链打通（snapshot → mini_benchmark → kernel real → bundle）
  - 跨进程 registry 注册方案（run_p4_gate_real.py：collector + 同进程 gate）

### 3.2 `reports/p4/P4_ROUND_9_REMEDIATION_WORKLOG.md`（如需要）

真实数据接入的完整 worklog：每条接入步骤（RED→GREEN 证据）、P1/P2/P3/P4 各段改动、验证输出。

### 3.3 更新验证包（可选）

`/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p4/INDEPENDENT_VERIFICATION_PACKET_R9.md`：
- Probe A：伪造 receipt 被拒（forged_passes=false）
- Probe B：伪造 bundle 链被拒（FORGED_REAL_BUNDLE_PRODUCED=false）
- **新增：真实 gate 全绿证据（G01-G14 全 PASS + status）**

---

## 四、送 kimi Round 9 复审

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
/opt/anaconda3/bin/python3 -m scripts.run_kimi_audit \
  --stage p4 --round 8 \
  --worktree /Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2 \
  --submission /Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p4/SUBMISSION_TO_CHATGPT_P4_ROUND_9.md \
  --prior-audit /Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p4/HERMES_P4_ROUND_8_READ_ONLY_AUDIT_AND_REMEDIATION.md \
  --verification-packet /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p4/INDEPENDENT_VERIFICATION_PACKET_R9.md \
  --output /Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p4/HERMES_P4_ROUND_9_READ_ONLY_AUDIT_AND_REMEDIATION.md \
  --repo-root /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
```

**注意：**
- **不要 `--skip-verify`**——本轮必须让 kimi 拿到验证重放的独立证据（上轮因"验证已跳过"被 BLOCKED）
- 若后台 shell 报 `/Volumes` 相关 FileNotFoundError：改用 `--skip-verify` 重跑，但要在 submission 里如实标注"验证由提交方实测"（先跑 §二 拿真实输出）
- 若 kimi 征询 429 限流：脚本会自动重试，耐心等

---

## 五、验收标准

- [ ] §二 全量验证全部通过（含 `run_p4_gate_real` G01-G14 全 PASS）
- [ ] `SUBMISSION_TO_CHATGPT_P4_ROUND_9.md` 生成，验证矩阵用真实输出
- [ ] kimi Round 9 审核报告落盘
- [ ] kimi 裁决：P4-R6-01 Closed（真实证据就位），P4 至少 BLOCKED→ 期望 PASS 或接近

---

## 六、禁止事项

- 不得修改上游合同 / frozen 文件 / P0 ADR / final_design / final_plan
- 不得伪造 real evidence（synthetic 重标 real 属于 P0 违规）
- 不得放宽 gate 判定逻辑
- 不得修改原始 pkl 数据文件（只读）
- 不得 commit / push / merge（除非明示授权）

---

*Generated by Claude（P4 gate 全绿后，供新窗口执行 Round 9 提交 + kimi 复审）。*