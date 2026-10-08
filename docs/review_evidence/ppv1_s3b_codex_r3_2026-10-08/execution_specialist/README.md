# S3b-r3 独立工程执行专项（2026-10-08）

实际仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`，HEAD `adf0287abef0c4803962fee0df0065d8e6f3793d`，直接父 `2bedfc060a9b19019ba44aa2a56dcacb88450c3b`。全部执行仅在 fresh `/private/tmp/ppv1_s3b_r3_execution_z7vc5n31`；主仓只读。源码隔离含src/vendor/必要根metadata；Python字节码和pytest缓存禁用。父是detached sparse worktree，只有src/vendor及根metadata；取出隔离副本后worktree已移除。主仓AGENTS用户差异与已有评审文件未改。

不访问真实金标、题面、封存逐题run、dependingv4或原v3资产/评价数据，不调用外部模型/provider/网络，不commit/push。G01仅沿既有路径白名单复制普通v3源码和本仓非题面反应资产镜像。数字均为工程合成回归，不代表dev(B1环境中间步骤)或298(RHEA酶学)科学性能。

结果总入口：`independent_execution_results.json`、`baseline_classification.json`、`legacy_identity_and_core_integrity.json`。

## 1. 全量与父基线（均只执行一次）

- PPV1：**879 passed/0 skipped/0 failed**，32测试文件，pytest26.19s/外层26.520921s，exit0。32=31存量+1新增；新8由879完整JUnit抽取，没有单独重跑当前新8。
- 父同字节新8：**5 failed/3 passed**，pytest4.89s/外层5.183765s，exit1。五红全部`DID NOT RAISE PPV1RunError`，即公开resume正常返回后缺预期拒绝，**5行为红、0collection/版本/字段红**。父后三段零业务变化/保全断言没执行，不能称负控内部所有断言均执行；三合法父绿全部完成。
- 只读归档后的父最终业务表提供额外实际行为：B3、B4、自洽artifact+显式新plan、anchor_corrupt四父案最终各1event/5commit/1transition；anchor_missing最终1event/4commit/0transition。见`parent_final_synthetic_table_observations.json`及其所指全表，不重新执行父行为。
- r3没有修改既有测试文件，无需父“更新旧文件”额外执行。相同测试/worker字节见`same_byte_test_inputs.json`。五拒因当前为binding_mismatch(B3/B4/显式新plan)、anchor_missing、anchor_corrupt；全量新8验完整零写/原文件保全与合法恢复。
- PPV1父环境与清环境worker均指同隔离根`dependingv3`，避免R2的absent_v3路径身份误配。没有环境错误或任何重试、没有复用实施方执行数字。本执行专项形成此快照期间无用量中断；根评审后续写作事件应由根单独登记。

## 2. 安全隔离G01（一次执行）

**1481 passed/8 skipped/17 deselected/0 failed**，pytest217.95s/控制器外层219.866072s，exit0。**288输入=228本仓+42普通v3源码+18非题面镜像**。复制输入与原输入SHA前后一致，完整允许字节在`g01_inputs.tar.gz`，各成员核验在`g01_archive_integrity.json`。不读原v3资产/真实评价/v4来补数，不拿原环境或历史数字冒充本轮。

8缺席依赖逐项：

- `test_analog_assets.py::test_row_counts_match_v4_parser`，95行：v4源码未提供。
- `test_analog_v2_corpus.py::test_v2_selected_and_remapped_rows_decidable`，62行：v2 provenance未生成。
- `test_analog_v2_corpus.py::test_v2_line_level_one_to_one_and_duplicate_ids_recorded`，153行：v2 summary未生成。
- `test_batch_runner.py::test_input_manifest_whitelist_from_frozen_v3`，52行：真实冻结基准未提供。
- `test_score_report.py::test_frozen_evaluator_cli_really_runs_dev`，110行：同上。
- `test_score_report.py::test_evaluator_refusal_on_wrong_split`，163行：同上。
- `test_score_report.py::test_evaluator_refusal_on_missing_lines`，172行：同上。
- `test_score_report.py::test_diagnose_route_buckets`，184行：同上。

17deselect=16slow+1明确export用例`test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden`。完整nodeid/实际理由见`g01_exclusions_detail.json`，无skip改pass。supplied控制器复制后只加被动pytest报告插件，不改输入准备、选择、测试、断言或期望；插件/前后脚本SHA在`g01_instrumentation.json`。selected_nodeids是collection记录，不是完成执行证书；完成依JUnit/实际退出码。

## 3. 身份、源码及化学继承

Python3.11.16/RDKit2026.03.6/SQLite3.53.4；实际库schema ppv1-store-9，15业务表；profile-14/search-6/search-limits-3/format-feedback-1/model-proposals-2，runflow-3/frozen-plan-1。源常量、schema、运行环境详`source_version_constants.json`与current/parent runtime日志。

production.py当前/父SHA同 **3b1a66ea2bc3aa37f7caaa2ed1a7f5395cda5901ef2a03d765b932ee5b082262**。52份legacy文件逐字节相同，聚合保持 **18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6**。12选定共享核心全部同父（原9+search/queue/model_protocol），AtomTool/G2/runner无变化。隔离源码与metadata交集仅runflow.py/profile.py变；git源码/测试/vendor差异也只有这两文件及新test_ppv1_s3b_r3.py。不会将旧已验化学链或全部历轮探针冒称本轮重新执行；本轮全量继承回归保持，公共原反例复跑另由恢复专项负责。

r3测试resume确实走`workflow.runner.resume_run`公开包装，但start硬杀worker调用底层runflow，pytest相同worker的公共层证据范围不能扩大；强公开真子进程入口由根恢复专项独立提供。

## 4. 证据完整性与复现

`commands.json`有全部argv/cwd/固定env/exit/wall/stdoutstderrSHA；完整stdout/stderr、JUnit、源/test/worker/vendor/metadata/普通允许G01输入字节、实际HEAD/parent/worktree与schema在包中。PPV1/父已经完成的explicit basetemp产物只读快照1001原文件，其中418SQLite以schema/全表JSON归档并保留原二进制SHA/大小（`synthetic_pytest_artifacts.json`），不在永久证据内建库或运行。G01提供全量输入/日志/JUnit/skipdeselect详情，未声称归档其所有临时运行产物。passed测试内部捕获但未持久化的子进程stdout不伪补；这项限制不替代恢复专项的完整公开worker日志。

只在新外部目录复现：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B scripts/reproduce_portable.py --out /private/tmp/ppv1_s3b_r3_fresh_engineering
```

portable脚本只做AST语法确认，未实际重复执行；它复制本包控制器及白名单到fresh目录，并要求仓HEAD相同。不可原地运行永久证据；不同HEAD不能冒称本审复现。`manifest.json`、`SHA256SUMS`、`manifest.sha256`由归档后字节生成，不认证现实化学性能。
