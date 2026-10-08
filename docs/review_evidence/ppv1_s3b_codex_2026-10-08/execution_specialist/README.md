# S3b 独立工程执行专项（2026-10-08）

仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`，实际 HEAD `c1211183c0874b12c5b5461845d3c61f0a84719c`、直接父 `b7f2bba02ca49edd0a45a13bc9b8434909d99175`。本专项所有执行在 fresh `/private/tmp/ppv1_s3b_execution_elmxhbxz`，主仓只读。没有调用外部模型/provider/network，没有访问金标、題面、封存 run、dependingv4、原 v3 资产/评价数据；普通 v3/src 42文件与仓内反应资产镜像18文件仅用于允许的安全 G01。判分零 LLM；所有结果是合成工程回归，不外推 dev 或298科学性能。

- PPV1 一次全量：**851 passed/0 skipped/0 failed**，pytest14.63s、外层14.968675s。实际 **30** 文件（26旧+4新），不是交付§3的31（26+5）。新64在851内，按原全量JUnit抽出，未单独重跑；各文件 model13/production11/queue19/runner21。
- 父 detached sparse worktree 两更新测试同字节：**4 failed/64 passed**，pytest0.95s、外层1.243300s。其中 **3行为红+1新字段形态红**：1 profile schema版本断言；1 `KeyError: format_feedback_policy`；2 runner start拒绝的有意翻转。双入口用例父在start即停，resume段未执行，不冒称父resume已验证。交付把缺字段列成第二个版本字面量，须更正。
- 同父四新文件：**4 collection errors**，exit2，缺 queue/model_protocol/production/runflow 模块；内部64用例未执行，不报64行为红。
- 安全 G01 一次：**1453 passed/8 skipped/17 deselected/0 failed**，pytest203.54s、外层205.542929s。**286输入=226仓内+42普通v3源+18允许资产镜像**；每项当前输入与复制SHA，执行前后相等；包含完整字节 `g01_inputs.tar.gz` 和逐成员SHA验证。8缺席依赖与17排除详见 `g01_exclusions_detail.json`，没有补缺数据或改skip到pass。G01数字与历史1389/1299/1250/1196/1138/1110分别登记。
- legacy code_identity 聚合独立复算：父 `4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c29ae` → 当前 `18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6`，哈希集合中唯一变化文件 `pathway_v43/workflow/runner.py`。runner真实代码变化增加PPV1分流；不能只称文字改动。legacy后续分支未改，当前白名单legacy工程回归保持。五化学核心、store、AtomTool字节对父一致，具体SHA见 `legacy_identity_and_core_integrity.json`。
- 四硬杀/B2/barrier共6测试在PPV1全量内运行。`s3b_worker.py` **直接调用 start_ppv1_run/resume_ppv1_run**，不能将这些案例称经共享 `workflow.runner.start_run/resume_run`；后者由其他公开分流/E01等测试验证。所有真实子进程worker控制源/命令模板封存。passed测试内部捕获的 worker stdout 没有由原测试持久化，不能伪补；完整suite输出/JUnit和执行后synthetic全表/产物保留，额外公开链证明由其他专项另列。
- 原始四硬杀最终全表：B1/B3/B4各1event/4commit/1attempt；B2为0event/1commit/1registered scripted request/network0、decide保持claimed。交付笼统“四崩溃事件一次commit4”需要限定前三，不把B2当成功展开。

`captured_pytest_outputs/` 是已完成的两个suite基线/当前显式basetemp输出：619文件原记录，420数据库二进制以只读全表JSON替代，原SHA/大小留 `synthetic_pytest_artifacts.json`；不跑任何探针重新生成。不含数据库/链接/cache。只读物化最终表不是故障点前后连续日志；强结论仅取源代码中实际断言到达的边界与其他专项公共探针。

`commands.json` 保存各命令argv/cwd/隔离env/exit/wall/stdout-stderrSHA；`current_runtime/`与`baseline_runtime/`含Python/RDKit/SQLite、contracts、真实meta与schema、legacy全文件集合；使用depending43 Python3.11.16/RDKit2026.03.6/SQLite3.53.4，profile13/search5/store9/limits3。`-B`/PYTHONDONTWRITEBYTECODE=1/pytest no:cacheprovider；无账号中断事件、无suite重试。被动观察插件只登记skip/nodeid，不改选题/输入/断言；旧控制器中历史注释/白名单SHA不当当前HEAD或执行数字。

只在新仓外目录复现，绝不能原地运行 `scripts/run_actual.py`：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B scripts/reproduce_portable.py --out /private/tmp/ppv1_s3b_new_engineering
```

portable只做AST语法检查，本审未再次执行；运行要求仓HEAD仍为本次审核HEAD。它先复制控制脚本/路径白名单到fresh目录，再执行。父worktree已清理，本专项未改主仓src/tests/既有docs/AGENTS，也未commit/push。
