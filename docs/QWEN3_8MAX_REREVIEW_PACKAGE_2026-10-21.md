# qwen3.8max 代复审包（代 Codex，2026-10-21）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 零金标、零题面、零凭证值。
>
> **授权**：CC 2026-10-21 指示「把 Codex 的复审报告发给 qwen3.8max 代为复审」。
> **provenance 纪律**：报告必须写明「qwen3.8max 代 Codex 复审，按 CC 2026-10-21 指示」，
> **不得冒充 Codex 本人**；Codex 此前的报告保留为历史意见，不因本次复审改写。
> **只读审核**：不改代码/文档/封存批、不跑 HPC、不调模型、不 push、不读金标/题面/reference_graphs/env/key。

## 一、两个待复审任务（各自自包含）

### 任务 A：P0b/D-6 R1–R4 回修复审

**请求文件（直接读）**：
`docs/T_H_P0B_D6_CODEX_REREVIEW_REQUEST_2026-10-21.md`

**背景（Codex 上一轮结论）**：
`docs/T_H_P0B_D6_CODEX_REVIEW_2026-10-20.md`（R1–R4 需修正；零漂移门被采信）

**回修交付**：
- 合同：`docs/T_H_P0B_D6_CONTRACT_2026-10-20.md`（回修后版本，块 `version=2`、`rule_version=p0b-d6-reconcile-2`）
- 实施报告：`docs/T_H_P0B_D6_IMPL_2026-10-20.md`
- patch：`docs/review_evidence/t_h_p0b_fix_2026-10-21/impl.patch`（SHA `035123de…204aa4`）
- 证据：`docs/review_evidence/t_h_p0b_fix_2026-10-21/`（SHA256SUMS 全过）
- 化学评审请求：`docs/T_H_P0B_D6_CHEM_REVIEW_REQUEST_2026-10-21.md`（R4 尚未完成）

**希望 qwen 输出**：
`docs/T_H_P0B_D6_QWEN_REREVIEW_2026-10-21.md`
（总裁定 / R1–R4 逐项 / 零漂移门是否采信 / R4 如何挂账 / 放行或最小回修 / unknown）

### 任务 B：T-I TI-F1 定点回修复审

**请求文件（直接读）**：
`docs/T_I_CODEX_F1_REREVIEW_REQUEST_2026-10-21.md`

**背景（Codex 上一轮结论）**：
`docs/T_I_CODEX_REREVIEW_2026-10-21.md`（TI-F2 关闭；TI-F1 不关闭：
completed 内嵌 `forbidden_permanent` 被降级、full 放行、收割后仍派新 qid）

**回修交付**：
- 报告：`docs/T_I_TI_F1_FATAL_FIX_REPORT_2026-10-21.md`
- 证据：`docs/review_evidence/ti_f1_fatal_2026-10-21/`（含 `actual_dispatch_stop_result.json`、
  `actual_worker_result_source.json`、`orchestrator_stop_dispatch.patch`、SHA256SUMS）
- 脚本锁：`docs/T_I_SCRIPT_LOCK_2026-10-20.json`（14 件，SHA `f0a43420…10625f46`）
- 批准包：`docs/T_I_APPROVAL_PACKAGE_2026-10-20/`（批准 JSON SHA `190e42a5…a50ae7`）
- 源码补丁只在 worktree，主树 `src/` 零 diff

**希望 qwen 输出**：
`docs/T_I_F1_QWEN_REREVIEW_2026-10-21.md`
（总裁定 / fatal 分类四项回归 / 停派发 / 原 63 项与 NC-9 正控 / 锁与批准包 /
是否允许关闭 TI-F1 / 关闭后 C0–C8 最小清单 / 当前 GO-NO-GO）

## 二、可选的背景文件（不强制）

- `docs/T_H_P0_DECISION_CODEX_REVIEW_2026-10-20.md`（P0 决议包审核与代决）
- `docs/T_I_CODEX_FINAL_REVIEW_2026-10-20.md`（T-I 两臂终审）
- `docs/T_H_HIT1_OPTIMIZATION_PLAN_2026-10-20.md`（优化方案，含 P0 实测回填）
- `docs/T_H_P0_DECISION_PACK_2026-10-20.md`（P0 决议包，头部已注“以 Codex 审核为准”）

## 三、给 qwen 的硬约束（请原样转达）

1. 只读审核；只新增上述两个 qwen 报告（如需运行校验，证据写
   `docs/review_evidence/qwen_rereview_2026-10-21/`，带 SHA256SUMS）。
2. 不改 `src/`、`tests/`、`scripts/`、既有 docs、封存批；不 push；不跑 HPC；不调模型。
3. 不读金标/题面/`reference_graphs`/`llm.env`/私钥；不输出候选 SMILES 或结构正文。
4. 不把“合成正负控通过”写成“真实可发车”；不把“复审通过”写成“作业已提交”。
5. 不替 CC/老师批准判据变更、付费批或真实题面外发；这些仍归 CC/老师。
6. 结论格式：总裁定（放行/需修正/NO-GO）+ 逐项证据 + 最小回修清单 + unknown 清单。

## 四、说明

- 若 qwen 的结论与 Codex 冲突，**以证据与源码互证为准**；请在两份报告中逐条写冲突点，
  不要静默取舍。
- 本包不包含任何 key、金标、题面或结构正文；只含计数、SHA、代码补丁与规则级描述。
- Codex 的 05:20 自动重试仍可能产出报告；两套报告可并存，由 CC 决定采信顺序。