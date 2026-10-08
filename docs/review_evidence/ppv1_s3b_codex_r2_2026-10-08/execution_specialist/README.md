# S3b-r2 独立工程执行专项（2026-10-08）

仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`，实际 HEAD `2bedfc060a9b19019ba44aa2a56dcacb88450c3b`，直接父 `c1211183c0874b12c5b5461845d3c61f0a84719c`。本专项所有执行在 fresh `/private/tmp/ppv1_s3b_r2_execution_gvh309hu`，主仓只读。仅普通src/vendor/metadata、精确工程测试输入；safe G01沿既有路径白名单复制普通v3/src与本仓允许反应资产镜像。没有访问真实金标、题面、封存逐题run、dependingv4、原v3资产/评价资料；没有模型/provider/网络调用；判分零LLM、未commit/push。全部数字是工程合成回归，不外推dev(B1中间步骤)或298(RHEA酶学)科学性能。

**最终结果入口为 `independent_execution_results.json`、`baseline_classification.json`。** `execution_summary.json`保持第一次控制器的原始结果，不冒充环境修正后的最终数字。

## 1. 实际执行与环境纠正

- 第一遍PPV1 **861 passed/10 failed/0 skipped**，pytest21.34s/外层21.711607s，31文件。10失败均在新worker启动→父进程恢复的 `v3_engine_code` 身份门提前拒绝：本专项父环境把 `V3_CODE_ROOT` 钉到隔离目录 `absent_v3`，新worker主动清理环境后默认选择同一隔离目录的 `dependingv3`。两处均不存在、git_available=false，但路径身份不同。审核环境配置错误，不是产品代码缺口；未将提前拒绝解释成十个功能失败。实际持久身份、父期待与十case见 `environment_identity_paths.json`，保留全部初始JUnit/stdout/stderr。
- 修正父环境到worker相同的隔离默认 `dependingv3`（没有复制外部数据或改源码/断言），按用户要求重跑完整PPV1：**871 passed/0 skipped/0 failed**，31文件=30存量+1新，pytest25.73s/外层26.174203875s，exit0。
- 新20全部由这次871的JUnit抽出，**没有单独再次跑当前新20**；其余851全绿。完整初始控制器和实际环境重试控制器分别保留，`environment_correction.json`记录原因与重复范围。没有账号用量中断事件；这次重复是环境纠错，不是额度续跑。
- 初始父新20受同一环境问题影响为17failed/3passed，日志保留而不用于红绿裁定；必要修正后只重复父新20。父更新3文件和G01未重复。

## 2. 直接父基线同字节红绿

- 实际父从 **detached sparse worktree** 取得，只checkout src/vendor及根metadata，不checkout禁止资料；随后在独立baseline_source运行，同字节测试/worker SHA见 `same_byte_test_inputs.json`。worktree已清理。
- 父更新3个既有测试文件：**3 failed/52 passed**（55用例），pytest0.64s/外层0.937694s，exit1：1profile版本断言、1 `KeyError('action_id')` 字段形态红、1novel缺reaction_spec未拒的行为红。交付表格的54绿须更正为52；合并数字不受此影响。
- 修正后父新20：**15 failed/5 passed/0 collection errors**，pytest69.59s/外层70.005045416s，exit1。分类 **13行为红+2artifact/字段形态红+5合法正控绿**，不是15条内部功能断言都走完。
- 形态红① `frozen_plan_tamper_integrity_failure`：父没有新的frozen_plan.json，在is_file断言即停，**没有执行篡改或恢复完整性门**。② `transition_enqueued_crash_window_closed`：已执行resume、验证转换done，后停在payload缺pending_followup，**后续followup新上下文断言未执行**。原缺口的行为证明须引用首轮公开探针/本轮恢复专项，不能由缺字段单例替代。
- 五真正父绿：same_plan_resume、b4_event_submitted_no_followup、three_products_normal、legal_nonzero_no_blocked、empty_pool_no_local_candidate。`model_abstain_empty_pool_legal` 父实际红于请求计数0≠1；它是空池进入模型的新行为翻转，交付§1.5的“父绿”有误。合法弃权当前保持。
- 新20+更新3合并 **18failed/57passed**，与交付合计相同；既有“1版本+1字段+1行为”分类准确。版本红不是化学漏洞，形态红不认证尚未到达的内部边界。

## 3. 安全隔离G01：一次独立执行

**1473 passed/8 skipped/17 deselected/0 failed**，pytest214.61s，控制器外层216.949056s，exit0。**287输入=227仓内+42普通v3源码+18本仓资产镜像**；每项原输入/复制SHA前后一致。完整input字节保存在 `g01_inputs.tar.gz`，逐成员SHA核验见 `g01_archive_integrity.json`，不接触原v3资产、评价数据或v4。历史1453/1389/1299/1250/1196/1138/1110保持历史标签，不混算。

8缺席依赖逐项：

- `test_analog_assets.py::test_row_counts_match_v4_parser`，95行，v4代码根不可用。
- `test_analog_v2_corpus.py::test_v2_selected_and_remapped_rows_decidable`，62行，v2 provenance未生成。
- `test_analog_v2_corpus.py::test_v2_line_level_one_to_one_and_duplicate_ids_recorded`，153行，v2 summary未生成。
- `test_batch_runner.py::test_input_manifest_whitelist_from_frozen_v3`，52行，真实冻结基准缺席。
- `test_score_report.py::test_frozen_evaluator_cli_really_runs_dev`，110行，同上。
- `test_score_report.py::test_evaluator_refusal_on_wrong_split`，163行，同上。
- `test_score_report.py::test_evaluator_refusal_on_missing_lines`，172行，同上。
- `test_score_report.py::test_diagnose_route_buckets`，184行，同上。

17deselect为16slow和1明确export用例 `test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden`；全nodeid与实际skip理由保存在 `g01_exclusions_detail.json`，没有把skip改pass。原控制器只加被动观察插件登记nodeid；不改选择、测试、断言。控制器外层env仍显示absent_v3，但其内部pinned_env明确重置到g01副本的dependingv3，与清环境worker默认一致；G01没有上述身份问题。

## 4. production/legacy字节保持与边界精度

- `production.py`当前/父同SHA **3b1a66ea2bc3aa37f7caaa2ed1a7f5395cda5901ef2a03d765b932ee5b082262**，SEARCH_PRODUCTION_VERSION不变；五化学核心/path_context/store/AtomTool/runner共9选定文件逐字节一致。首轮化学生产义务不是本轮新认证，依赖已验冻结链与本轮回归保持。
- **52份legacy代码文件全部逐字节一致**，聚合身份父/当前同 **18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6**。本轮没有共享legacy变化；vendor包含source副本与hash。详 `legacy_identity_and_core_integrity.json`。
- 版本真实meta/schema由隔离库取得：profile-14/search-6/store-9/search-limits-3/format-feedback-1；model-proposals-2/runflow-2见源码。Python3.11.16/RDKit2026.03.6/SQLite3.53.4。
- r2 `tests/s3b_worker.py`（包括concurrent-resume）仍调用 **runflow.start_ppv1_run/resume_ppv1_run**；两个子进程真实工具计数/barrier成立，但不能单凭该worker将其扩大成两个 `workflow.runner.resume_run` 包装入口。新文件部分in-process用例确用公共start_run/resume_run；包装层并发和恢复的独立证明由恢复专项提供。低层公开函数与共享runner包装分开登记，不新增门。

## 5. 证据与复现

`commands.json`为首控制器完整argv/cwd/env/exit/wall/SHA；`corrected_execution_commands.json`为实际纠错两次命令；JUnit、完整stdout/stderr、精确source/tests/worker/metadata、原输入SHA、实际HEAD/parent、运行meta/schema与全部已完成合成basetemp产物/全表在本包。`captured_pytest_outputs/`只读整理1926个原文件，其中867数据库以全表JSON替代，原SHA/大小见 `synthetic_pytest_artifacts.json`；没有运行探针重新生成，没有数据库二进制/cache/symlink。

初始和纠正后输出都保留。被pytest捕获而原用例未持久化的passed子进程stdout不伪补；全量日志/JUnit、实际断言源、工具入口收据与最终全表可审；强公共链证明另由恢复专项提供。G01全suite输入/输出日志和skip/deselect明细完整留存，未把collection观察当已执行。

只在新仓外目录复现，**绝不能在永久证据目录原地运行**：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B scripts/reproduce_portable.py --out /private/tmp/ppv1_s3b_r2_fresh_engineering
```

portable复制控制器与路径白名单到fresh目录，默认使用已纠正父/worker一致路径，调用 `run_fresh_corrected.py`。该可携带脚本仅AST语法检查，**本审未再次执行**。复现要求仓HEAD仍与本审一致；不同HEAD不能冒称本审复现。所有主仓既存文件保全见根source guard及本专项post_corrected_source_integrity/G01_input_integrity_after；不push、不新增或修改src/tests/既存docs/AGENTS。
