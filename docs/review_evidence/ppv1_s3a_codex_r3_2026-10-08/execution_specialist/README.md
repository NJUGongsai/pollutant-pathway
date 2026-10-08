# S3a-r3 独立工程执行证据（2026-10-08）

实际仓 `/Volumes/CC/Enzyme_Agent/dependingv43`，实际 HEAD `41d0cd55f3def050a62325f00235cf22da302d2e`，直接父 `dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`。本审所有执行在全新 `/private/tmp/ppv1_s3a_r3_execution_hypuljsk`；没有复用实施方或主会话suite结果，没有改仓库src/tests/既有docs/AGENTS。父detached sparse worktree含完整src/vendor/metadata，已清理。源与明确允许输入执行前后SHA一致。

- PPV1 25文件：**697 passed /0 skipped /0 failed**，exit0，pytest7.93s，墙钟8.255s。r3新文件49项从全量JUnit筛得全绿，不与697相加。
- 父dcb7同字节新回归49：**40 failed /9 passed /0 collection error**，墙钟1.265s。40全部行为失败：28未拒Integrity、3未拒Contract、2未拒Recovery、2未拒IdentityConflict、5值断言。无返回形态/缺字段/缺表/旧kind先停。9绿细分5既有坏输入拒绝控制+4合法控制，不当9个纯合法化学正控。失败内部到达与未执行后段见baseline_case_classification.json，原测试/预期/日志未改。
- 安全G01：**1299 passed /8 skipped /17 deselected**，exit0；pytest196.91s，控制器198.929s（其中pytest子进程墙钟198.409s，见commands.json及g01/execution_result.json）。276输入=repo216+普通dependingv3/src42+本仓普通反应资产镜像18，源/副本前后SHA核对一致。全部输入原字节保存于g01_inputs.tar.gz，276个成员逐SHA验证，无数据库/cache/链接。缺席依赖逐nodeid/理由见g01_exclusions_detail.json；8skip为真实评测5/v4对照1/phase_d元数据2，17排除为slow16+显式export1。没有补任何真实数据根或伪造缺席输入。
- 公共store.submit_event坏缺产物输入全表零变化，trace含BEGIN IMMEDIATE+ROLLBACK；合法首提一次，重放createdFalse全表一致。runner.start_run/resume_run的合成PPV1身份均fail-closed，无新运行/恢复身份变化。public_controls目录保留完整输入/trace/前后全表。没有访问历史真实run。
- runner.py字节对父相同，legacy code_identity完整逐文件和聚合对父相同：`4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c29ae`。当前/父runtime记录schema/新库meta/版本，不由源码版本文本代替实际新库观察。
- 一次沿用窄化学探针 **15 cases /完整assert footer**（exit0、1.572s）：只适配实际父输入与HEAD metadata，未改结构输入/行为断言。原脚本、精确diff、父输入保存。另7例CX实际写出/别名拒（exit0）：ABS=`a:1,3`，AND=`&1:1,3`，OR=`o1:1,3`，radical=`^1:0`；4个合法身份往返、3个and/or/rad字面别名拒。STATIC_FINDINGS.md逐条互证mimo11八条件、外层异常与内因、None/converter/audit限度。
- 化学五核心chemstate/audit/path_context/hypothesis/events父/当前字节相同。完整src65 Python文件+安全白名单82测试静态扫描：AuditContractError十抛点全audit.py，无body广捕获/specific except；没有生产audit/converter调用，不构成动态或未来caller安全证明。

环境depending43：Python3.11.16/RDKit2026.03.6/SQLite3.53.4；profile11/search3/store9/limits3。所有目标Python -B/PYTHONDONTWRITEBYTECODE=1/pytest no:cacheprovider。完整stdout/stderr/JUnit、argv/cwd/env/exit/耗时/SHA、实际HEAD/schema在各目录及commands.json。G01观察插件被动记录实际skip/deselect，未改selection/fixture/断言；collection hook瞬时selected不是最终已执行清单。

安全边界：金标/题面/封存逐题run/dependingv4/原v3 assets/evaluation未读、无外部模型/provider/网络调用、不push/commit。ordinary代码+允许非题面资产为白名单输入。所有数字是合成工程契约结果，不外推dev或298科学性能。旧655c7e8及交付“既有更新1版本红/22绿”此次未跑；不冒充独立证实。

本轮有效执行各suite/探针均首遍完成，无准备错误、无需失败重跑。父预期40红日志保留。本轮账号中断未发生，R2限额中断历史不算本轮新事件。static_precision.run.json如实登记静态脚本没有独立墙钟计时，不补造数字。

归档不含运行SQLite/pytest临时数据库/字节码/cache；manifest.json/SHA256SUMS覆盖全部附件，排除自身。schema和SQL全表以JSON留证。源码/vendor/metadata/原测试在sources/current与sources/baseline；安全G01原字节在tar。只有portable主入口做syntax检查、**本审未执行**；本审实际suite由scripts/run_actual.py启动，其他实际脚本与run记录分开。

安全复现必须新仓外目录，禁止在永久证据内运行任何会写库脚本：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  scripts/reproduce_engineering_portable.py \
  --out /private/tmp/ppv1_s3a_r3_new_engineering
```

该入口从当前仓复制明确源/PPV1测试、建立限定父sparse worktree、执行完整工程suite；要求HEAD仍等本审r3。它是可复现入口，不是一份额外已执行suite。既存输出不被覆盖。静态/窄化学结果按本次实际记录，不把portable脚本当已复跑。
