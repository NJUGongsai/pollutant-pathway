# S3a-r4 独立工程与化学互证（2026-10-08）

实际仓 `/Volumes/CC/Enzyme_Agent/dependingv43`，HEAD `b7f2bba02ca49edd0a45a13bc9b8434909d99175`，直接父`41d0cd55f3def050a62325f00235cf22da302d2e`。本专项所有执行在新的`/private/tmp/ppv1_s3a_r4_execution_oo8np5ce`；没有复用实施/主会话执行结果，没有改仓库src/tests/既有docs/AGENTS。父detached sparse worktree完整含src/vendor/metadata，已清理。

- PPV1全量26文件：**787 passed /0 skipped /0 failed**，pytest9.11s；新90在787内，不相加。
- 父r3同字节新90：**78 failed /12 passed /0 collection error**，pytest1.57s；77未发生指定异常（58Integrity/18Recovery/1Contract）+1KeyError形态红。12绿=11合法行为+1旧坏输入拒绝保持。baseline_case_classification.json保留每个输入/失败/到达边界，未执行内部不报通过。
- 安全G01：**1389 passed /8 skipped /17 deselected**，pytest197.70s/内部subprocess199.226s/controller199.841615s；277输入=repo217+普通v3src42+普通允许资产镜像18，原/复制SHA前后相等。全部277字节封在g01_inputs.tar.gz并逐成员SHA验证，不含链接/数据库/cache。缺席/排除逐项见g01_exclusions_detail.json。没有补缺席真实评价/v4/phase_d数据。
- 公共writer坏缺产物state输入BEGIN IMMEDIATE+ROLLBACK，全表零改变；合法首提与同参幂等重放全表一致。runner PPV1 start/resume合成身份双入口fail-closed；runner/legacy code_identity对父不变，聚合`4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c29ae`。
- 旧窄化学15案完整assert footer，7CX写出/别名控制，额外7factory/strict/R1坏对象+合法audit控制，全部只运行一次且exit0；不与pytest数字相加，不冒称全旧R8化学矩阵复跑。五化学核心文件对父字节相同，65src+83白名单test静态inventory完整。
- mimo12条件/源码行号/执行标注见STATIC_FINDINGS.md。RegistrationHash额外对照与跨RDKit稳定性本轮未跑；本批不是冻结或新科学性能门。

环境depending43：Python3.11.16/RDKit2026.03.6/SQLite3.53.4，profile12/search4/store9/limits3。所有目标Python -B/PYTHONDONTWRITEBYTECODE=1/pytest无cacheprovider。完整stdout/stderr/JUnit与argv/cwd/env/exit/wall/SHA/实际HEAD/schema在各目录。G01被动观察插件只记选项/skip/nodeid，不改输入/期待/选择；collection中selected名单不是最终执行名单。

本轮执行各suite/探针均一次完成，无准备失败/无需重试；父预期红不是当前失败。没有本轮账号中断事件。只归档脚本/源/元数据/JSON表前后/日志，不含执行SQLite、pytesttmp、字节码/cache。manifest.json/SHA256SUMS覆盖除自身外全部附件。旧永久证据脚本先复制tmp，不在永久库跑脚本写库。金标/题面/封存run/dependingv4/真实provider/外部模型/网络无访问，不push/commit。工程合成结果不外推dev或298科学性能。

以下portable入口只syntax检查，**本审未执行**；运行必须指定新的仓外目录，绝不能在永久证据内部写库：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  scripts/reproduce_engineering_portable.py --out /private/tmp/ppv1_s3a_r4_new_engineering
```

该入口要求当前repo HEAD仍为本审r4，只复制明确PPV1源码/tests与安全G01白名单，建立限定父sparse worktree。实际本审使用scripts/run_actual.py；portable不是另一次执行证据。
