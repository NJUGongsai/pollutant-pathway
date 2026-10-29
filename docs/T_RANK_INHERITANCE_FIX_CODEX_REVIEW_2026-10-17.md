# T-F 折叠位次继承修复 Codex 代审（2026-10-17）

**裁定：回修。1 项 P1，另 1 项 P2 口径纠正；未发现 P0。** 本轮继承合同在合法重名输入下未闭合：novel 自报 ID 等于池逻辑 key 时，被折叠者的原始位次 1 被读成池条目的 2 或 3，模型首选反应仍排第二。两个公共链合成反例均实际提交 CC=O 在 CCOO 之前。Q2、Q4 涉及的是同一个 P1，不重复计数；不将既有裸 key 设计泛化为本轮新增的全仓身份漏洞。

审核对象为 `e3fe446c84842f9f3d9dea0b7d99f84d535ea1dc`，实际 HEAD 为 `3ad658621e172f7fec5292dfef1b4346b66afd44`。两者后续差异仅为文档，src/tests 零差异；目标文件哈希和工作树状态见[快照记录](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_2026-10-17/snapshot_metadata.json)。以下源码行号对应目标提交，也适用于当前相同文件。

本会话执行者在全新 tmp 中按指定提交导出完整 src（含 vendor）、pyproject 和必要测试；Python 3.11.16、RDKit 2026.03.6，禁 pyc 与 pytest 缓存，运行输出放在源码根外。原四夹具加版本断言 **5 passed / 1.23s**；新增公共 `start_run(scripted=True)` 矩阵 10 例，8 例符合合同、2 例同根反例、0 执行异常。探针退出 0 仅表示观测完成，绝不代表修复全过。未复跑实施方自报的全量 2197/0/16，未发真实模型/外部模型请求，未访问金标、题面或封存逐题 run，未修改原源码、测试和既有文档。

最终采信[原测试命令](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_2026-10-17/execution_original_tests.json)、[测试日志](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_2026-10-17/execution_original_tests.log)、[v3 探针](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_2026-10-17/execution_boundary_probe_v3.py)、[v3 命令及脚本哈希](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_2026-10-17/execution_boundary_run_v3.json)、[v3 完整输入输出](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_2026-10-17/execution_boundary_output_v3.json)。早期 v1/v2 采集器错误保留作执行历史，不用其中缺失的事件观测下结论。

## Q1 继承语义：不通过（P1，唯一阻塞项）

常规边界正确：[_declared_rank](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1009) 取声明位次；1023–1033 逐次保存更优折叠位次；1045–1056 过滤幸存池键并补回 novel 自身位次；1057–1067 最后应用 min。无位次不覆盖已有位次，双方无位次不误标，多次折叠取最优，novel 幸存者先补自身位次再继承。这些边界均有本轮公共链合成验证，不凭缺少原测试直接判错。

**P1：新增查表消费没有区分“池逻辑 key”和“novel 自报 ID”。** `rank_by_key` 是池 prepared ID 映射成逻辑 key 的表（[runflow.py:1310](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1310)）；`model_rank_by_id` 保留模型原 ID 表（1324）。两者命名空间不同，但 1009–1012 对裸字串优先查池表，随后 survivor/best/final rank 也以裸字串关联。

最小可达输入：底物 CCO，池 A→CC=O、B→CCOO；模型引用池 A 的 prepared ID，同时提交 novel `hypothesis_id="A"`、产物 CCOO，排序 `["A", pool_A_prepared_id]`。该 ID 合法：[model_protocol.py:174](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/model_protocol.py:174) 仅与池 prepared ID 比较，[real_model.py:148](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:148) 允许自行命名 novel ID。

公开执行结果：

| 合成反例 | 原始 novel 位次 | 错读/最终幸存者位次 | 实际事件顺序 |
|---|---:|---:|---|
| `novel-id-collides-pool-key`：novel A 折入池 B | 1 | 2 / 2 | CC=O → CCOO |
| `novel-id-collides-survivor-key`：novel B 折入池 B，池 B 自身位次 3 | 1 | 3 / 3 | CC=O → CCOO |

另补严格单变量配对：两组使用相同 run_id、池、prepared IDs、reaction_spec 和运行参数，仅 response 内 novel ID 及其 rank 引用由 A 改为 novel:A，输出根分开隔离。递归差异断言与事件序断言均通过：重名组 B 位次 2、CC=O 先提交；对照组 B 位次 1、CCOO 先提交。见[配对脚本](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_2026-10-17/execution_single_variable_pair.py)、[命令](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_2026-10-17/execution_single_variable_pair_run.json)、[输入输出](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_2026-10-17/execution_single_variable_pair_output.json)。v3 原无重名正控还改变了来源字段，故不称单变量；更正记录见[EXECUTION_PAIR_NOTES.md](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_2026-10-17/EXECUTION_PAIR_NOTES.md)。

第一例让 A、B 同为 model_rank 2，再由 [runflow.py:1068](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1068) 的 key 排序把 A 放前；第二例把 novel 自身位次误读为幸存池的 3，直接判不继承。两例都落在“保留被折叠者最优声明位次”的本轮原验收内。

最小修复方向：条目进入继承计算时保留池/novel 来源，按来源读取各自声明位次，并使 survivor、best-folded、最终位次关联和审计来源不混淆。同名字串可保留作展示，内部可用来源加 ID 的组合身份。无需全仓架构重写；不能仅倒转两表优先级，也不能靠强迫 novel 前缀或拒绝原本合法名称掩盖此问题。

## Q2 披露完备：不通过（同 Q1 的 P1，不另立项）

两个反例的 `model_rank_by_id` 原始值分别明确为 `"A":1`、`"B":1`，但 dedup 行 `folded_model_rank` 分别写成 2、3；后一例还写 `rank_inherited=false`、最终来源 null。[runflow.py:1033](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1033) 至 1038 如实落下了错误查表结果，字段存在并不足以证明来源正确。原始 ID 与 `merged_into` 同为 B 时，还须能区分 novel B 和池 B。

无重名时，现有披露基本足够：同一 model 记录保留 `model_rank_by_id` 与 `novel_proposals`，输出仅移除 `rank_by_key`（[runflow.py:1157](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1157)）；novel 位次来源可据此联回，不必单为正常 novel 另加一个阻塞字段。

`rank_inherited` 应解释为“处理本条折叠时改善了当前最好位次”，不等于“最终唯一胜出来源”。例如两次折叠 3→1，两条均 true，而最终 `model_rank_inherited_from` 指向位次 1 的提案，程序结果正确。修复后沿同一来源身份记录真实原始位次和最终来源即可收口。

## Q3 版本与兼容：通过；P2 纠正 hit@K“零传导”口径

父版 policy-1 已升为 [runflow.py:208](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:208) 的 policy-2；1123–1129 为新构造的排序载荷写位次、继承来源和 policy-2；[版本断言](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_s5b_hit50_w23456.py:1005) 同步且独立复跑通过。

旧载荷不迁移、不回写的证据是静态代码门：PPV1 对全部 Python 源树生成代码身份（[run_identity.py:76](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/storage/run_identity.py:76)），resume 逐列拒绝身份不一致（229–257），该核验在打开 ledger 和恢复前执行（[runflow.py:1976](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1976)）。同 action 异 payload 也拒覆盖（[search.py:956](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/search.py:956)）。本轮未读旧 run，不把静态核验写成旧批恢复实跑。

**P2：判分代码零改动，不等于 hit@K 零传导。** scorer 的确不直接读取 effective_rank，但按事件 `(created_at,event_id)` 计命中位次（[s5b_scoring.py:631](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_scoring.py:631)、677–685）；排序经 [queue.py:211](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/queue.py:211) 的选择/入队传到实际事件序。因此修复本来就可能改变新 run 的候选选择、提交顺序和 hit@K。应改为：“判分算法与产物身份判据零改动；新运行的提交顺序可能改变，科学收益未认证。”该纠正不新增性能门，也不要求真实模型验证。完整静态核对见[兼容证据](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_2026-10-17/compat_findings.md)。

## Q4 测试覆盖：不通过（对应已复现的同一 P1）

原四测覆盖“无位次池幸存者继承、幸存者更优不继承、折叠者更优继承、不折叠基线”，见 [test_tf_rank_inheritance.py:143](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_tf_rank_inheritance.py:143)。原四测与版本断言全绿可信，但没有覆盖合法名称重叠；此处不通过依据公共链实错，而不是缺测试数量。

本轮补充矩阵的执行账：

| 验收形态 | 例数 | 结果 |
|---|---:|---|
| 两次折叠，分别先差后好/先好后差 | 2 | 均取最优，逐条披露正确 |
| 折叠者无位次/双方无位次 | 2 | 保持原位次或 fallback，不误继承 |
| novel 幸存者，继承/自身更优 | 2 | 补回及继承顺序正确 |
| 池条目折入池条目；相同反应形状的无重名正控 | 2 | 均符合合同 |
| novel ID 等于其它池 key / 等于幸存池 key | 2 | 均复现同一 P1 |

固定回修收口矩阵仅为：① novel ID 等于其它池 key，原始位次 1 正确进入幸存者且首选反应先提交；② novel ID 等于幸存池 key，仍正确比较两个不同来源的位次；③对应无重名正控；④原四测、版本断言和上述正常边界继续通过。两类反例均核原始 rank、dedup rank/来源、最终继承来源及实际事件序。不追加科学性能或无关阶段验收。可沿同根补一个“同名且 novel 幸存”的自检，避免只修查表局部，不据此扩成新的独立门。

## Q5 三次真实批折叠的行为声明：通过，限摘要支持的局部排序判断

只核用户明确允许的 fold_detail；题域为 **298=RHEA 通用酶学/已见题**，未访问对应逐题 run。顶层与 aggregates 下的 fold_detail 为同一三条，不能重复计成六次。见[允许摘要的脱敏副本](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_2026-10-17/fold_detail_sanitized.json)。

| 折叠者 → 幸存者 | 折叠者声明位次 → 幸存者声明位次 | 幸存者 effective_rank |
|---|---:|---:|
| novel-4 → novel-2 | 4 → 2 | 2 |
| novel-3 → novel-1 | 2 → 1 | 1 |
| novel-6 → novel-4 | 5 → 4 | 3 |

按这三条摘要提供的位次，折叠者均更差，不满足 1029–1032 的继承条件，局部排序决定不变。该证据支持“这三次已披露折叠无须转移位次”，不证明所有新旧产物逐字节相同：新字段和 policy 标签本就变化。此处是摘要与源码互证，未独立重放历史运行或重建摘要生成链，不外推其它批次、科学收益或整体分数恒等。

**总体裁定：回修——修闭 1 项 P1（合法重名输入的来源混淆），并纠正 1 项 P2（hit@K 零传导措辞）；按 Q4 固定矩阵复核，不增设性能门。**
