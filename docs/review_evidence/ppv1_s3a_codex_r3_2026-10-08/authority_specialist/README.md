# S3a-r3 权威专项证据（2026-10-08）

实际HEAD/父、运行时/版本/schema、输入SHA见 `source_inputs.json`、`runtime_schema.json`、`final_source_integrity.json`。结论与有限修复范围见 `AUTHORITY_REVIEW.md`。

- `repo/`：实际当前完整src/vendor、pyproject与worker隔离副本；历史metadata不当当前HEAD。
- `original_scripts/`、`old_scripts/`：R2永久证据原脚本复制；`*.adapter.diff`登记异常捕获/窗口不重跑适配，输入不更改，源码未适配。
- `capture_commands.json`：原27、120segmented、done2、附随首提3、四硬杀/barrier5、旧observed的实际argv/cwd/env/exit/UTC/耗时；对应完整stdout/stderr及每案input_output。
- `necessary_reference_probe.py`、`necessary_reference_command.json`/stdout/stderr、`necessary_reference_cases/`：63完整捕获（9合法+54坏必要引用集合仍错误成功）。`one_action_budget_chain_probe.py`与同名命令/输出、`one_action_chain_cases/`：总额度1双案合法挡第二、坏集合仍两event/commit成功而只计used1。
- `defer_and_controls_probe.py`/命令/完整输入输出：9坏行defer拒、4合法未执行释放/共享alternative/非expand/failedattempt保持。
- `assert_r3_capture.py`、`readonly_assert_commands.json`、`contract_results.json`：正确当前合同只读断言exit0；明确54残余不算通过。旧observed/旧R2捕获assert按设计失败；其失败后的内段不得说通过。
- done捕获末断言误期待SearchIdentityConflict已在专项报告登记；两案数据完整，之后仅只读核正确SearchContractError/kind和零写，未重跑。
- `omitted_databases.json`：为了减少永久包体积，合成SQLite二进制不复制，其SHA/大小留存；全部反例保留完整JSON输入及14表前后快照/元schema/实际artifact信封。旧crash控制沿原脚本6表快照、完整input/worker日志/schema；若重放需按源码在新tmp重建，不原地运行本包。
- `manifest.json`/`SHA256SUMS`/`manifest.sha256`：所有列入附件冻结SHA，格式files列表。只读复核不得在永久目录建库/运行写结果脚本。

全部depending43，Python -B/禁字节码；只新tmp，金标题面封存run/dependingv4未访问，无provider/网络/外模，主仓零修改。case数不与PPV1/G01相加，不外推科学性能。
