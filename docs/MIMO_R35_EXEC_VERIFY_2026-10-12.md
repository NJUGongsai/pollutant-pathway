# mimo r35 待执行验证项——读码/查题四件记录（2026-10-12）

> 对应 docs/mimo_ppv1_chem_review_response_r35.md 尾部 6 处"待执行验证"。本文件覆盖其中 4 件轻量件（主会话执行）；剩余 2 件扫描类（自由基扫描、hwall 位点抽查）并入 T3/T6 任务范围。

| # | mimo 断言（待验证） | 验证方法 | 结论 |
|---|---|---|---|
| 1 | cn_identity 若含 InChI，互变异构可能判同一身份 | 读 `src/pathway_v43/domain/identity.py:46` | **不含 InChI**。cn_identity = stereo_blind(normalize_charge_smiles(smi))，纯 canonical SMILES 口径；互变异构体身份**区分**，mimo 担心的分支不触发。方向仍是"伤召回不伤精度" |
| 2 | target 终判是否覆盖全部入池路径 | grep check_target_consistency 消费点 | **覆盖 model/analog 编辑通道**（workflow/nodes.py:788，类比编辑协议 v2 的 canonical 终判）；recorded 通道不经编辑+target 路径，等价兜底是 strict 产物多重集最终门（recorded_source.py:2175-2182）。与 mimo 自报推测一致 |
| 3 | 底物括号显式氢来源（管线归一 or 记录原样） | grep AddHs/RemoveHs 全 src | **管线无 AddHs/RemoveHs 状态归一**（仅 validation/conservation.py 校验计数用）。括号氢来自题卷底物 SMILES 原样书写。mimo 的"若为归一"条件不成立，但结论方向不变：hwall 消除的是书写形态依赖的执行差异 |
| 4 | strict→uncovered 退步题 RXNG_5e9b5672…（c12 出现 valence 异常）的失败记录 | 读该题 c12 payload（run s5br_f2f9aed2b8d） | **死因 = execution_failed:edit_execution_failed:sanitize_failed:AtomValenceException:edit[last]**——c12 的模型候选在编辑末步撞 sanitize 价态墙（旧墙同族），非 hwall 新引入。支持 mimo"候选/协议方差、不像 hwall 副作用"解读 |

未覆盖 2 件（转 T3/T6）：①自由基通过实例扫描（43 partial + rank2-5 候选产物 NumRadicalElectrons）；②hwall 指纹 strict 题位点合理性抽查（10-20 道）。

Provenance：主会话只读验证（identity.py/nodes.py grep + synced payload 单题查询），零模型零网络；2026-10-12。
