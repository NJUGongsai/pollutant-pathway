# 复制给 P4 AI 的短提示词

请在独立 worktree/branch 中执行 P4；不要修改其他 worker、P0/P1/P2、final docs/ADR，不要 commit/push/merge、联网、安装依赖、调用真实 LLM/MCP/Orchestra。

完整读取并执行：

~~~
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/CHATGPT_P4_IMPLEMENTATION_PROMPT_2026-08-03.md
~~~

必须先重新核验磁盘状态，并读取其中列出的 final_design、final_plan、final_discussion、ADR、P1 final pass、P3 prompt 和可用的 P3 interface manifest。P2 formal Gate 仍 BLOCKED；P2 当前 truth/isolation/Gate/mutation 不能无条件当作 authority。

你的范围只包括：P4 independent evidence identity/dedup、support aggregation、允许的 counterevidence、strict-only deterministic ranker、structural applicability、typed abstention、PredictionResult invariants、immutable run/trace/manifest、P4 schemas/tests/fixtures/Gate/reports，以及 reports/p4/p4_p5_interface_manifest.json。不得创建或修改化学结构，不实现 P3 graph edit，不实现 P5 benchmark。

先写 RED tests。支持只能绑定 evidence IDs；database absence/低频/未找到第二个 enzyme 不是 negative；support score 不是 probability/confidence；strict/generalized/agent_proposed 不横向混排；system failure 不能改成 abstention。P3 或真实 evidence 缺失时必须 typed BLOCKED，不能伪造 candidate、performance 或 PASS。

完成后生成 reports/p4/SUBMISSION_TO_CHATGPT_P4.md、P4_GATE_REPORT.md/json、P4_MUTATION_RESULTS.json、interface manifest 和完整 changed-files/tests/assumptions/blocked evidence。mutation 必须从 PASS-capable fixture 验证目标 PASS→FAIL，不能用 BLOCKED 基线冒充 caught。

最后一行只能是：

~~~
READY_FOR_CHATGPT_P4_READ_ONLY_AUDIT
~~~

或诚实的：

~~~
P4_IMPLEMENTATION_COMPLETE_GATE_BLOCKED
~~~

不要声称 P4 Gate PASS，除非当前 run 的所有 evidence、trace、hash、依赖和 Gate 项均机器可核验。
