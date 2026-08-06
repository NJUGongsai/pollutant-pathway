# 复制给 P3 AI 的短提示词

请在一个独立 worktree/branch 中执行 P3，不要修改原工作树、P0/P1/final docs/ADR，也不要 commit/push/merge、联网、安装依赖、调用真实 LLM/MCP/Orchestra。

请先完整读取并严格遵守：

~~~
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/CHATGPT_P3_IMPLEMENTATION_PROMPT_2026-08-03.md
~~~

同时读取其中列出的 final_design.md、final_plan.md、final_discussion.md、六份 ADR、P1 final pass、P1 implementation prompt；以磁盘当前状态为准。P2 formal Gate 仍 BLOCKED，P2 当前 truth/isolation/Gate/mutation 不能直接作为已冻结 authority。

你的范围只包括：P3 strict one-step kernel（X normalization → train-only distinct donor retrieval → complete reaction load → mapped lineage → strict transform → conditioned site → deterministic graph edit → validation/dual ledger → canonical unranked strict candidates）、P3 schemas/tests/fixtures/Gate skeleton/reports，以及 reports/p3/p3_p4_interface_manifest.json。

必须先写 RED tests；缺 RDKit、mapper、real snapshot 或完整 P1 capability 时只能 typed BLOCKED，不能伪造 SMILES、reaction、mapping、performance 或 PASS。P4 ranking/abstention 和 P5 benchmark 不要实现。

完成后生成 reports/p3/SUBMISSION_TO_CHATGPT_P3.md、P3_GATE_REPORT.md/json、P3_MUTATION_RESULTS.json 和完整 changed-files/tests/assumptions/blocked evidence。最后一行只能是：

~~~
READY_FOR_CHATGPT_P3_READ_ONLY_AUDIT
~~~

或诚实的：

~~~
P3_IMPLEMENTATION_COMPLETE_GATE_BLOCKED
~~~

不要声称 P3 Gate PASS，除非当前 run 的全部真实 evidence 与所有 Gate 条件均由机器可核验 artifact 证明。
