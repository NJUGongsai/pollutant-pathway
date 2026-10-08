# S3a 独立工程执行证据

实际 HEAD：`9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`。父/红基线：`00e509a974b40a7c9779fcd35e53b16637a13d60`。这是审核方新 tmp 的独立执行，没有复用交付方执行数字。

- PPV1 23 文件：594 passed / 0 skipped，pytest 6.51s，命令墙钟6.839s，1条历史docstring警告。
- 当前 S3a 两新文件：58 passed / 0 skipped（search45 + recover13）。
- 父基线：两新文件各 collection 错误，新模块不存在；58用例未执行，不能算58行为红。单独同字节profile：2 failed /21 passed。红为profile-9与search-limits-3版本断言；后一用例的delivered_stages断言未执行。
- 安全隔离 G01：1196 passed /8 skipped /17 deselected，pytest194.01s，控制器195.855s，1条同一历史警告。274输入全部SHA前后相同：仓214、普通v3源42、本仓普通资产镜像18。
- 仅slow collect-only：16条实际nodeid，未执行测试体；另明确排除export_v3一条。`g01_slow_collection/result.json`保存16条。
- 动态合成legacy身份控制通过：legacy逐文件仅runner.py改变，跨代码resume按既有门拒；去除PPV1拒绝函数后runner AST完全相同；legacy拒绝函数仍返回None，PPV1仍拒。未加载任何历史真实run。

边界：工程测试数不是科学性能；R7的1110/8/17、R8的1138/8/17独立历史标签不混入。本包只证明实际工程执行与明确分段事实，预算/恢复的额外反例由其他专项核对，不能单凭594通过裁定整个S3a。

## 文件

`commands.json`记录完整argv/cwd/退出码/耗时/关键隔离环境；各命令目录完整stdout/stderr/JUnit。`initial_metadata.json`、`final_repo_metadata.json`记录HEAD/父/工作区；`runtime_environment/stdout.txt`记录Python3.11.16/RDKit2026.03.6/SQLite3.53.4、profile9/store9/search1/search-limits3及未变契约。`input_hashes.json`覆盖PPV1当前/基线源码（含vendor）和同字节测试。`test_inputs/`为24份准确测试/worker输入，未改import或预期。`test_byte_equality.json`保存四个前后同字节输入，`worktree_cleanup.json`确认detached sparse worktree清理且只余主仓。

`g01_safe_isolation/`记录白名单、274输入、实际9b78HEAD、缺席路径与8项具体skip/17排除。原控制器只复制白名单ordinary源/冻结非题面资产，原v3 assets/evaluation/v4/reports/data/benchmark/金标/题面/封存逐题材料不读取不复制；固定空BBD_DATA_ROOT与全部外部路径到临时树。`safe_g01_s3a_original.py`是原脚本；`safe_g01_s3a_instrumented.py`只新增输出JUnit参数，选测/预期/依赖准备完全未改，逐字变更在`g01_instrumentation.json`。`allowlists/`两份历史清单只作路径白名单，历史hash不是本次hash。

## 安全复现

以下控制器只写新仓外目录，拒绝已有输出目录；必须继续守无金标题面/封存run/外部模型边界，禁止在此永久证据内原地运行会写库的底层脚本。

```bash
PY=/Users/cc/miniconda3/envs/depending43/bin/python
REPO=/Volumes/CC/Enzyme_Agent/dependingv43
# 此脚本从当前固定9b78HEAD读取普通src/vendor、测试、metadata；
# 全套只跑一次各项，自动创建/移除仅src的父提交sparse worktree。
PYTHONDONTWRITEBYTECODE=1 "$PY" -B reproduce_engineering.py \
  --repo "$REPO" --out /private/tmp/ppv1_s3a_new_review_run \
  --python "$PY"
# 额外合成身份控制，沿上面隔离源码，另用新输出目录。
PYTHONDONTWRITEBYTECODE=1 "$PY" -B legacy_identity_probe.py \
  --source-run /private/tmp/ppv1_s3a_new_review_run \
  --out /private/tmp/ppv1_s3a_new_identity --python "$PY"
# 独立G01：本包白名单可显式供应，仍必须新目录。
PYTHONDONTWRITEBYTECODE=1 "$PY" -B safe_g01_s3a_instrumented.py \
  --repo "$REPO" --out /private/tmp/ppv1_s3a_g01_new \
  --python "$PY" --r7-path-manifests ./allowlists
```

归档核对（只读取结果，不重跑pytest/探针）：`python -B assert_execution_artifacts.py .`。外层`SHA256SUMS`和`manifest.json`覆盖全部附件，只有外层清单不自我hash。包不保存会写入的源码树/SQLite/pytest临时库/字节码；源与资产按固定提交+显式输入SHA再取。

## 准备事件与如实分类

全部执行第一遍完成，无超时/断流重试，无源码/断言修补。基线import错误是按设计的新实现缺席；基线两失败是新版本期待，不是两化学漏洞。合成legacy身份probe三段输出与完整传入旧/新身份在`legacy_identity/`。当前生产caller未交付（S3b），上述静态及底座控制不声称生产审计异常义务已闭合。
