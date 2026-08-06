# 复制给 P5 AI 的短提示词

请在独立 worktree/branch 中执行 P5；不要修改其他 worker、P0/P1/P2/P3/P4、final docs/ADR，不要 commit/push/merge、联网、安装依赖、调用真实 LLM/MCP/Orchestra。

完整读取并严格执行：

~~~
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/training/CHATGPT_P5_IMPLEMENTATION_PROMPT_2026-08-03.md
~~~

同时读取其中列出的 final_design、final_plan、final_discussion、六份 ADR、P1 final pass、P1 prompt、P3/P4 prompts，以及存在的 P2/P3/P4 submission/interface manifests；以本地磁盘重新核验为准。当前 P2 formal Gate BLOCKED，P3/P4 若未形成真实、hash-valid、leakage-audited authority，P5 只能做 protocol/fixture/reporting machinery，不能 PASS。

你的范围只包括：P5 full snapshot/production-diagnostic-quarantine index、filter accounting、rebuilt multi-answer cases、exact-X/scaffold/transformation-family/source/time/OOD splits、same-data/same-split fair baselines、six-layer structured reports、N/CI/coverage/reasons、formal KPI registry、Go/No-Go、P5 schemas/tests/fixtures/Gate/reports，以及 reports/p5/p5_p6_interface_manifest.json。

不得修改 P1 source、mapping、lineage、eligibility；不得把 fixture 当 real evidence；不得把 database absence 当 negative；不得伪造 source/time provenance；不得复制旧 accuracy/KPI；不得把 oracle 结果放 primary；不得把 system failure 或 incomplete truth 计成普通 miss。先写 RED tests。所有报告 JSON 是 authority，Markdown 只是渲染；Gate 必须验证 artifact schema/hash/cross-stage joins、leakage、split fairness 和上游状态，不能信 status string。

mutation 必须从 PASS-capable fixture 验证目标 PASS→FAIL，不能用 BLOCKED baseline 冒充 caught。缺真实 snapshot、上游 P2/P3/P4、RDKit/mapper 或 audited truth 时准确 BLOCKED，不伪造 performance 或 PASS。

完成后生成 reports/p5/SUBMISSION_TO_CHATGPT_P5.md、P5_GATE_REPORT.md/json、P5_MUTATION_RESULTS.json、full snapshot/split/baseline/six-layer manifests、interface manifest 和完整 changed-files/tests/assumptions/blocked evidence。

最后一行只能是：

~~~
READY_FOR_CHATGPT_P5_READ_ONLY_AUDIT
~~~

或诚实的：

~~~
P5_IMPLEMENTATION_COMPLETE_GATE_BLOCKED
~~~

不要声称 P5 Gate PASS，除非当前 run 的全部真实 snapshot、truth、split、P3/P4 artifacts、leakage audit、baseline fairness 和 Gate 项均有机器可核验证据。
