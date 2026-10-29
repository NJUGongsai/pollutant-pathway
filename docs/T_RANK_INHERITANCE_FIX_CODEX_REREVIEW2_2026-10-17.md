# T-F 位次补回余项 Codex 同范围复审二（2026-10-17）

**P1 余项闭合＝是；总体裁定＝放行。** 未排名池条目不再偷取已折叠同名 novel 的位次；原反例、严格配对与正常边界均经公共运行入口复验通过。放行范围仅为本次 T-F 修复。

复核实际执行于 2026-10-18（北京时间），文件名沿请求日期。审核目标和实际 HEAD 均为 `84cc9ff0a9cb5fcce5559d3ba9520e86bec40dcf`；本次提交只改 runflow 的补回来源逻辑（+10/−3）及两项测试（+35），不涉及判分、池或检索。[目标快照和源码哈希](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview2_2026-10-17/snapshot_metadata.json)、[完整增量](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview2_2026-10-17/source_test_diff.patch)。

## 1. 未排名池反例及严格单变量配对：通过

上轮最小反例保持底物 CCO、池 A→CC=O、B→CCOO，两池均未排名；novel ID=A、产物 CCOO、模型只排该 novel 第一。修后池 A 的 `model_rank=null`、`rank_basis=deterministic_fallback`、`effective_rank=2`；B 获得位次 1、生效位次 1、来源 `novel:A`。去重行披露来源 novel、折叠位次 1、继承 true，实际事件顺序为 **CCOO→CC=O**。

再用相同 run_id、池、prepared IDs、reaction_spec 和参数隔离运行，只把响应的 novel ID 及其排序引用改成 novel:A。无撞名对照结果同样为 A 退后、B 第一，B 的来源正确变为 `novel:novel:A`。两组输入差异断言与实际事件序断言全部执行通过，未再出现上轮“撞名组错序、对照组正常”。见[未排名严格配对脚本](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview2_2026-10-17/execution_unranked_strictpair.py)、[运行记录](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview2_2026-10-17/execution_unranked_strictpair_run.json)及[完整输入输出](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview2_2026-10-17/execution_unranked_strictpair_output.json)。

池 A 有显式位次 2 的原反例及其无撞名严格配对也均为 B 位次 1、A 位次 2，实际均 CCOO 先提交；原“撞幸存池 key”反例同样保持通过。见[有位次严格配对](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview2_2026-10-17/execution_ranked_strictpair_output.json)与下节正常矩阵。

## 2. 原索引补回、折叠和披露：通过，未发现新增同范围问题

[runflow.py:964](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:964) 先成功追加 novel，再记录原索引；非法条目不登记。[1054 行](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1054)在同一幸存分支成对追加条目与原索引，折叠分支直接继续、两列均不追加。随后 prepared_entries 仅重绑定为幸存列表，zip 前无其它修改，因此两列等长同序，不会静默截断。

[1069 行](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1069)按随行原索引核来源；只有真实幸存 novel 才读原始模型 ID 表。池与已折叠 novel 同名时不会再补错表，也未在去重后重新编号。两项公共链索引移动正控分别让前序池、前序 novel 折出，后序独立 novel 仍正确补回位次 1，且实际 CCCO 先于 CC=O 提交；两项均匹配预期、零执行异常。见[索引移动脚本](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview2_2026-10-17/execution_index_shift.py)及[实跑结果](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview2_2026-10-17/execution_index_shift_output.json)。

每个签名仍指向首次幸存者，不存在逐级折叠链。两次折叠按“3→1”“1→3”分别披露 true/true、true/false，最终都取 1 且来源指向最优折叠者；原来源分流、最佳位次四元组和折叠位次来源披露字段本次无改动。池未排名、同名 novel 同时幸存的共享字串槽亦如实观察，属于上轮已登记 v1 身份现状，不宣称已修；best_folded_rank 裸 key 静态边界不重开、不另设门。

## 3. 收口矩阵：全部通过

| 执行范围 | 本会话实际结果 | 证明范围 |
|---|---|---|
| 仓内 9 测＋hit50 版本断言 | 10 passed，1.59s | 新反例、对照、原测及 policy-2 |
| 上轮公共链正常矩阵 | 10/10，零异常 | 多次折叠、无位次、novel 幸存、池折入池及原重名反例 |
| 池有／无位次的严格配对 | 4 次运行，断言全过 | 各状态撞名／无撞名均首选反应先提交 |
| 前序折叠后的原索引正控 | 2/2，零异常 | 池或 novel 折出后来源不漂移 |

[定向测试命令和输出](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview2_2026-10-17/execution_original_tests.json)、[正常矩阵完整输入输出](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview2_2026-10-17/execution_boundary_output.json)。仓内新增两测使用不同 run_id，本报告的严格单变量结论来自独立配对探针。实施方自报全量 2202/0/16 未在本会话复跑，不作独立认证。

## 分级与执行边界

原 P1 余项关闭；未发现新增 P0/P1/P2，原已修事实保持关闭。版本仍为 s5b-rank-policy-2，本轮修正其来源合同并通过版本断言，不另加升版门。判分算法及产物身份判据未改；新运行提交顺序可能改变，科学收益未认证。

本会话执行者在全新 tmp 导出目标源码（含 vendor）及必要 metadata／测试，以 Python 3.11.16、RDKit 2026.03.6 经公共 start_run(scripted=True) 运行纯构造输入；设置 PYTHONDONTWRITEBYTECODE=1、Python -B、禁 pytest 缓存，数据库及产物在隔离源码根外。[执行后核对](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview2_2026-10-17/execution_postcheck.json)确认隔离副本 93/93 文件与目标导出一致、无缓存、原仓 src/tests 工作树无改动。 未访问金标、题面或封存逐题 run，未调用真实或外部模型，未执行 git 写操作；仅新增指定报告和证据目录。

**总体裁定：放行——本轮 T-F 位次补回来源余项闭合；不据此认证科学收益或自动启动 HPC。**
