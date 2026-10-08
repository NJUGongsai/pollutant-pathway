# S3a-r4 权威专项证据（2026-10-08）

入口 `AUTHORITY_REVIEW.md`；实际HEAD/父/source SHA在 `source_inputs.json`、最终校验在 `final_source_integrity.json`，环境/schema在 `runtime_schema.json`。仅新tmp独立执行，仓库零修改、无外部模型/provider/真实评价数据。

- `repo/`：当前完整src/vendor/pyproject/worker副本；旧脚本硬编码HEAD不代表当前HEAD。
- `original_scripts/`：R3永久证据原脚本副本；当前捕获沿相同输入，不修改源码/输入去适配行为。
- `run_r4_captures.py`、`capture_commands.json`：9批实际argv/cwd/env/UTC/exit/耗时；对应完整stdout/stderr，每案14表与完整合成输入存于各case目录。
- `necessary_reference_cases/`：63个完整捕获，其中54坏已拒、9合法；`one_action_chain_cases/`：上限1两个完整链，坏完成拒。旧script末期assert期待commits2失败、正确只读断言读取完整保存案，不重跑。
- `authority_cases/`、`segmented_cases/`、`done_result_reuse_cases/`、`supplementary_cases/`、`defer_control_cases/`、`crash_generated/`：旧27/120/done2/首提3/defer13/硬杀barrier5。crash沿原script6表快照与完整worker日志；schema完整保留。
- `cache_hit_boundary_probe.py`、`cache_boundary_command.json`、`cache_boundary_cases/`及观测汇总：7案公共链/零预算控制，合法cache与一致删除两ref+row形态14表相等，固定范围P2限制详见专项报告。
- `assert_r4_capture.py`、diff、`readonly_assert_commands.json`、`contract_results.json`：已捕获IO的只读正确合同断言exit0。历史observed/R3旧断言故意失败的日志也保留，不把其后未执行段算通过。done历史错误异常类期待、上限1旧漏洞期待已逐项说明。
- `omitted_databases.json`：合成SQLite二进制不入包，其SHA/大小登记；所有case完整输入/表变化/schema/artifact包已保留。重放须复制至新tmp，禁止在永久证据目录建库或写结果。
- `manifest.json`为 `files` 列表，每项path/bytes/sha256；`SHA256SUMS`和 `manifest.sha256`冻结附件。不得把case数相加到PPV1/G01，或外推dev/298科学性能。
