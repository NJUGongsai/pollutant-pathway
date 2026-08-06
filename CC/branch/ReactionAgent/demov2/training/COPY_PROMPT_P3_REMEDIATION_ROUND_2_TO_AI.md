# 可直接复制给 P3 修改 AI 的提示词

请在下面指定的独立 P3 worktree 中执行 Round 2 严格返工：

```text
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2
```

预期分支：

```text
codex/p3-strict-kernel
```

你没有之前聊天记忆。开始前必须完整阅读并严格执行这份返工规范：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/CHATGPT_P3_REMEDIATION_PROMPT_ROUND_2_2026-08-03.md
```

本轮目标不是进入 P4，也不是把缺真实数据造成的 BLOCKED 改成 PASS；目标是修复 ChatGPT P3 Round 1 审阅中已经被独立探针复现的实现不变量错误，包括：

- fold isolation 可被调用者重写；
- 同一 donor A 的多个完整 reactions 只加载第一条；
- 错误 product 只要重原子数相同就能通过 transform fidelity；
- forged source ledger 能通过 validation；
- `critical_contradiction=True` 仍能进入 strict lane；
- artifactless 状态字典能骗 Gate 返回 PASS；
- mutation 10/10 存在宽泛异常、错误断言和非 P3 production-path 假阳性；
- 负电荷输入被拒绝；
- isotope policy 声称 preserve 但 identity 删除 isotope；
- fixture NormalizedQuery 被标成 real；
- P3→P4 输出缺少完整 run/query/fold/snapshot namespace；
- graph edit 对缺失 endpoint/anchor/target 静默跳过；
- transform hash 使用错误 lineage 且 preimage 不完整；
- candidate merge 丢失逐路径 ledger；
- RDKit 被错误报告成 strict atom mapper available；
- full regression 数量由 `906 + P3 count` 合成，changed-files 不是实际 Git delta。

必须先记录 starting dirty worktree；不得 reset/checkout/clean/stash/删除其他 agent 文件。不得修改 P0/P1 authority、final docs、ADR、P4/P5。不得联网、安装依赖、调用 LLM/MCP/Orchestra，也不得 commit/push/merge。

该 worktree 没有 `.venv/bin/python`。使用已有 Python：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
```

每个问题必须先写可验证的 RED test，再做最小修复并转 GREEN；禁止 `pytest.raises(Exception)`，禁止把“总体仍 BLOCKED”当 mutation caught，禁止用状态字符串、人工布尔值、硬编码测试数制造 PASS。

完成后必须提交：

```text
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_2.md
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_ROUND_2_AUDIT_EVIDENCE.json
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/P3_ROUND_2_REMEDIATION_WORKLOG.md
```

必须运行真实 P3/full regression/P0 Gate/P1 Gate/P3 Gate 并记录实际命令、退出码和原始结果。真实 snapshot、automatic donor、P2 pilot 仍缺失时，P3 real-evidence Gate 应诚实保持 BLOCKED；但任何 implementation invariant 失败必须让 Gate 为 FAIL，不能被 BLOCKED 掩盖。

完成后停止，等待 ChatGPT 只读审核；不得自行批准 P3，不得开始 P4 正式集成。
