# S3a-r2 权威专项证据

详细裁定见 `AUTHORITY_REVIEW.md`；独立当前执行，仓外新 tmp，全合成、无网络/provider/模型调用，无真实题面、金标、封存 run、dependingv4。

- `initial_metadata.json`、`runtime_schema.json`、`final_integrity.json`：实际 HEAD/父、源码隔离及输入哈希、depending43 Python/RDKit/SQLite/schema、环境与工作区前后。
- `old_scripts/` 与 `old_counterexamples/`：首轮永久证据的只读复制输入；未修改原证据。旧脚本硬编码或旧 metadata 不是当前 HEAD。
- `inheritance_as_executed.py` + `inheritance.stdout.jsonl` / `.stderr.txt` + `authority_cases/`：原 12×2 authority + 2合法控制 + raw首提交；全部前后表及公共 writer 对照。
- `crash_concurrency_as_executed.py` + `crash_commands.json` / `crash_observations.json` / stdout/stderr + `crash_generated/`：实际4硬杀/1双独立进程barrier，含worker argv/cwd/exit/输出。
- `probe_original.py`、`old_probe_observed.*`：旧搜索观察脚本按预期早停，仅第一个正控完整执行；后续分案见下。
- `segmented_authority_probe.py`、`segmented_commands.json`、`segmented.stdout.jsonl` / `.stderr.txt`、`segmented_observations.json`、`segmented_cases/`：120分案完整捕获；四种异身份写/提交/B3分离，首次complete，八种消费入口的search引用、六入口projection/plan/event载荷、四入口commit引用、H07H08。
- `supplementary_probe.py`、`supplementary_command.json`、`supplementary.stdout.jsonl` / `.stderr.txt`、`supplementary_cases/`：3正常firstsubmit语义守卫+2并发故障注入；最后错误类型断言准备失误已登记，数据5案完整。
- `done_result_reuse_probe.py`、stdout/stderr、`done_result_reuse_cases/`：同事件已完成复用正控与有效异父事件返回错引用，零写；命令在 `final_assert_commands.json`。
- `assert_current_capture.py`、对应命令/stdout/stderr、`contract_results.json`：只读纠正断言；明确区分固定修复、合法控制、81被接受坏记录、2晚拒但事件已写。
- `portable_reproduce.py`、`portable_supplementary_probe.py`：新便携控制器，仅 AST/语法静态检查，未以此重跑已完整的probe；实际命令见 `*_commands.json`。
- `manifest.json`、`SHA256SUMS`、`manifest.sha256`：整个嵌套包（含隔离 src/vendor/metadata/worker、合成DB、输入/输出）的冻结哈希。

证据重放只能把脚本和完整repo复制进新的tmp、改用全新输出根，`python -B` + `PYTHONDONTWRITEBYTECODE=1`；不得在本包或仓内永久证据原地执行会建库/写日志的脚本。
