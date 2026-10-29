# T-F 位次继承回修 Codex 同范围复审（2026-10-17）

**P1 闭合＝否；总体裁定＝再回修。** 首轮两个具体反例已经修好，但同一来源规则在去重后的位次补回入口仍有遗漏：池 A 未获模型位次、同名 novel A 排第一并折入池 B 时，池 A 偷取 novel A 的位次 1，模型首选反应仍第二提交。这是首轮 P1 的同根余项，不新增独立 P1，也不以已登记的“双同名条目同时幸存”现状另设门。

审核对象及实际 HEAD 均为 `0facf85333eed4fef3436e18f80dc295d6532caa`；目标源码、测试与隔离副本哈希一致，前后 src/tests 工作树无改动。见[快照](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview_2026-10-17/snapshot_metadata.json)及[执行后核对](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview_2026-10-17/execution_postcheck.json)。以下行号对应该提交。

## 1. 首轮两个反例：具体反例通过，P1 整体未闭合

`novel_entry_idx` 在 novel 成功追加时记录原条目索引；`_declared_rank(entry_idx,key)` 按该来源分别读取池逻辑键表与模型原始 ID 表；去重签名保存 `(key,idx)`。这部分修法正确。首轮“novel ID 撞其它池 key”“撞幸存池 key”两例均实跑通过：折叠位次为原始 1，来源为 novel，幸存池条目获得位次 1、继承来源分别为 `novel:A`／`novel:B`，实际 CCOO 均先于 CC=O 提交。

原严格配对也复跑通过：两组使用相同 run_id、池、prepared IDs、reaction_spec 和参数，仅 novel ID 及其排序引用由 A 改为 novel:A；现在两组均为 B 先、A 后。见[原配对输入输出](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview_2026-10-17/execution_strictpair_output.json)。这两项已修事实保持关闭；不能因此把来源规则在后续消费入口也认定为闭合。

## 2. 来源分流：不通过（原 P1 余项）

[runflow.py:1015](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1015) 的 helper 已消除池条目回退读模型原始 ID 表；但[1063 行](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1063)的最终补回仍遍历全部幸存条目，仅凭 `key in novel_by_key` 判来源。该表保留已被折出的 novel，因而“幸存池条目与已折出 novel 同名”仍会读错表。

最小公共链输入：底物 CCO，池 A→CC=O、B→CCOO，两个池条目均未获显式位次；模型仅提交 novel `hypothesis_id="A"`、产物 CCOO，排序仅 `["A"]`。novel A 合法折入池 B，去重后仅池 A／B 两个不同 key 幸存。程序先把原始 novel 位次 1 错误补给池 A，再使 B 正确继承 1；随后按 `(model_rank,key)` 排序，A 在 B 前。

本会话执行者经公共 `start_run(scripted=True)` 观测到：A 的 `model_rank=1`、继承来源 null、`effective_rank=1`；B 的 `model_rank=1`、继承来源 `novel:A`、`effective_rank=2`。dedup 行本身已正确披露 novel、位次 1、继承 true，但无法抵消另一反应偷取位次造成的实际乱序。

又做严格单变量配对：run_id、池、反应内容、prepared IDs 和运行参数全部一致，输出根隔离，仅修改模型响应中的 novel ID 及其排序引用。结果如下，配对结构与事件断言全部执行通过；此处“断言通过”确认了错误行为的复现，绝非修复通过。

| 合成输入 | A／B 生效位次 | 实际事件顺序 | 合同结果 |
|---|---|---|---|
| novel ID=A，与未排名池 A 同名 | 1／2 | CC=O → CCOO | 违约：模型首选仍第二 |
| novel ID=novel:A，无重名 | 2／1 | CCOO → CC=O | 正常 |

见[最小探针完整输入输出](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview_2026-10-17/execution_unranked_collision_output.json)、[严格配对脚本](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview_2026-10-17/execution_unranked_strictpair.py)、[严格配对命令](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview_2026-10-17/execution_unranked_strictpair_run.json)及[严格配对结果](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview_2026-10-17/execution_unranked_strictpair_output.json)。执行退出 0，合同违例与执行异常明确分开。

正常多次折叠仍取最优：先 3 后 1 时逐条 true／true、最终来源指向 1；先 1 后 3 时 true／false。每个签名均指向首次幸存者，不构成逐级折叠链。`best_folded_rank` 仍以裸 key 索引这一静态边界予以登记，本轮没有新增跨签名执行证据，不据此另立阻塞，也不要求本轮修复无折叠时既有的同名双幸存行为。

## 3. 固定矩阵：原具体项目通过，来源合同尚不能收口

| 执行范围 | 实际结果 | 采信范围 |
|---|---|---|
| 仓内 7 测＋hit50 版本断言 | 8 passed，1.35s | 原测试和 policy-2 断言通过 |
| 首轮公共链 10 例矩阵 | 10／10，零执行异常 | 两个原反例、无重名正控及正常边界通过 |
| 原严格单变量配对 | 两组均 CCOO 先提交 | 原重名反例确已修复 |
| 未排名池变体及无重名正控 | 1 违约、1 正常，零执行异常 | 同一 P1 的后续补回入口尚漏 |

正常矩阵覆盖两次折叠的两种顺序、折叠者无位次、双方无位次、novel 幸存者继承／自身更优、池折入池及重名正负控。见[原测试记录](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview_2026-10-17/execution_original_tests.json)及[矩阵完整结果](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/tf_fix_codex_rereview_2026-10-17/execution_boundary_output.json)。测试通过数不能覆盖已经实证的同规则漏口。

回修仅需使去重后的补回也消费真实条目来源：保留幸存条目的原索引或来源标记，只有真正幸存的 novel 才读模型原始 ID 表，池条目只读池逻辑键表。不能在去重后重新 enumerate 再套用去重前的 `novel_entry_idx`，否则索引错位会再次误判来源。显示 ID 可保留，不应强迫前缀或拒绝原本合法名称。

收口矩阵保持有限：首轮①分别核池有显式位次／无显式位次，并保留对应无重名正控；两种状态均核原始位次、去重披露、最终来源及实际提交顺序。原已修两个反例和正常矩阵继续保持通过，不追加科学性能门或无关身份重构。

## 分级及执行边界

P0 未发现；原 P1 未闭合 1 项，新增独立 P1 为 0；首轮 P2 的措辞纠正已在本次提交说明采纳，本轮不新增 P2。采纳口径为“判分算法与产物身份判据零改动；新运行提交顺序可能改变，科学收益未认证”。

本会话执行者在全新 tmp 导出目标 src（含 vendor）及必要 metadata／测试；Python 3.11.16、RDKit 2026.03.6，禁 pyc、禁 pytest 缓存，运行产物位于隔离运行目录；后核无缓存。全部输入纯构造、零真实模型及外部模型调用，未访问金标、题面或封存逐题 run，未执行 git 写操作，原仓源码、测试及既有文档未改。本轮仅新增指定报告与证据目录。实施方自报全量 2200／0／16 未在本会话复跑，不作独立认证。

**总体裁定：再回修——修闭原 P1 的最终位次补回来源漏口；原两个具体反例已闭合，按上述有限矩阵复核。**
