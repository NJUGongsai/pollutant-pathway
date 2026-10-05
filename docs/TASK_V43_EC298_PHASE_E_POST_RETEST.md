# v4.3 Phase E 任务书：dev20 开发，EC298 终测

> **状态：待执行；本文件仅是任务书。**2026-09-29 用户确定：只用 dev20 做 Phase E 开发；
> EC298 保留为 final test。此决定取代本文件早先“用 EC298 逐题结果做
> E0/E1 诊断”的安排。开始前记录 Git 状态，保留共享工作树全部旧产物。

> **现场记录**：起草本书时误启动过 Chenyu
> `runs/phase_e_dev20_C0/`，随后已停止该批次协调器与 worker，并核实
> 活进程为 0。停止时 `progress.json` 为 15/20 终态，目录中有 17 个
> 响应文件、没有批次报告；实际计费尚未核对。它是未完成的试运行，
> **不构成基线，不评分、不续跑、不并入效果表**；可能产生的费用须
> 单列核对，目录保留作事实记录，正式
> 执行必须换新批次根。起草时部署的临时配置与评分脚本已撤回。

## 1. 数据边界与已有暴露

- **开发集**：冻结 v3 `dev20` 的 20 条路线及金标，只在离线诊断、评分
  进程读取答案。允许用 dev20 的逐题错误选择下一步机制和开发期参数，
  但必须记录每次选择，避免把这 20 题上的增益误写成泛化结论。
- **终测集**：EC298 的 298 题，仍按原 `v43-ec298-scorer-2`、整串
  `cn_identity`、固定分母与 hit@1/@3/@5 评分。Phase E 实施期间不读取
  `reports/phase_d/retest/loss_audit/`、配对逐题表、原始 EC298 run 或金标
  来选规则、权重、阈值、prompt 或特例；不得在 EC298 上做开发回放。
- **历史披露**：Phase E 决定前已经生成 EC298 的逐题审计与失分报告，
  旧版任务书也引用过其中的类别计数。因此这批题不是从未接触的全新
  盲测集。后续开发不再借用那些信息；最终报告明确披露这一限制，
  不把 EC298 的一次终测结果称为完全独立的泛化证明。
- 当前默认仍是 C0，`reactant_similar_enabled=false`。Phase D 原始运行
  和修复后的派生表均为历史证据，不参与 Phase E 规则选择。Phase D
  F1/F2/K1/K2 的报告修正不要求重跑 EC298。
- **协议差异**：已有 dev20 Phase D C0 是多步路径任务（`max_depth=6`、
  `max_expansions=40`、报告宽度 3），EC298 是单步任务（1/1/5）。旧
  dev20 路径分数可作机制线索，不能直接预测 EC298 的 hit@K。开发期
  正式配对须为 dev20 另建单步输入、根节点金标与 1/1/5 同口径评分；
  题目来源仍只限 dev20，不从 EC298 复制题目或答案。

## 2. S0：执行前冻结登记

1. 记录本地/Chenyu Git 状态、运行代码聚合 SHA、v1 资产 SHA、模型、
   三份 prompt SHA、价格快照、dev20 输入来源及配置；不覆盖旧 run 或
   上述中止目录。用户批准执行后才创建新的单步开发批次根。
2. dev20 来源固定为 v3 `evaluation/pathway_benchmark/` 的
   `split_manifest.json` 与 `gold_routes.jsonl`，本地已核对 SHA 分别为
   `fb7742f98b6511275d16e613b18ca2dc62340403958f92ead6a0c2bf15d25dce`
   与 `d8e626a266ec0ee36dd6cd9befcf761fc7c3ff95efe384abcae5094527fbdcdc`。
   先重算远端字节，要求 20 个唯一 dev route ID、与 eval 不交叠、输入
   清单仅含 `route_id/root_smiles/root_smiles_sha256`。
3. 单步开发配置与 EC298 的任务预算同口径：`max_depth=1`、
   `max_expansions=1`、`max_frontier_width=5`、`max_llm_calls=3`、
   `max_proposals=1`、`reactant_similar_enabled=false`。并发和费用上限
   可按 dev20 容量单独预登记，但对照臂和变体臂须一致。
4. 冻结 dev20 根节点评分器：以每条 gold route 的 `root_cn` 为父节点，
   收集其全部一跳 `product_smiles`，按正式 `cn_identity` 比较有序报告
   候选；任一合法首步命中即取最早位次。20 题中有一题存在 6 条不同
   根边，不能误把“最多报告 5 个”解释为只保留前 5 个金标。校验每题
   最多 1 个预测 step、最多 5 个报告产物、根底物一致、20 题恰好齐全；
   空答仍留在分母。金标只在隔离评分进程打开，持久报告只存位次、布尔
   判定、数量与来源 SHA，不存金标 SMILES。

## 3. E0：dev20 基线和断点审计

1. 核验 dev20 输入、金标、既有 C0 答卷和评分口径的 SHA、数量、唯一
   route ID、合法终态及完整调用账。把既有多步 C0 明确标为历史诊断。
   从 dev20 金标图确定根节点的一跳可接受产物集合，冻结单步开发
   scorer；若图存在多种平行合法首步，要在看到新答卷前固定答案语义。
   旧 `dev20 r1` 中的 300 秒超时和 Phase D 旧报告的完整性错误只记为
   历史，不预设仍是当前断点。
2. 只对 dev20 逐题建立五层漏斗：输入/检索 → 资格与路由 → 模型任务或
   确定性直通 → 产物验证 → 裁决与报告位。区分“候选未到任务”“到任务
   未产生”“产生后被验证拒绝”“可报告但排序靠后”“运行截断”。
3. 记录每题 @1/@3/@5、报告位次、答案类别、停因、卡来源、候选资格、
   验证拒因与费用；类别可多标签，但主断点须唯一并守恒。化学不确定
   情况保留 `undetermined`，不能按金标倒推原始卡具备资格。
4. 交付 `reports/phase_e/dev20/e0/` 和 `docs/PHASE_E_DEV20_E0_REPORT.md`。
   旧 run 审计段零模型调用；新 1/1/5 C0 基线是另行登记的开发运行，
   运行完成后再做 E0 逐题归因。不输出 EC298 的任何逐题信息。

## 4. E1：已验证产物排序，主攻 hit@1 / hit@3

**当前代码断点**：`services/report_adjudication.py:adjudicate_parent`
按“选中卡 → 模型 `order` → `(retrieval_rank,evidence_id,position)`”
排列，再去重、截到 5 位。`services/prediction.py:build_prediction_task` 的
`rank_candidates` 只列合格 recorded 卡，不能把不合格卡混进排序任务。

**要写的代码**：把“哪些产物已验证且占用最多 5 个报告位”与“这批产物
按什么顺序展示”拆成两个可复核步骤。在前者集合完全冻结之后，增加
版本化的排序策略，只用运行时已有的来源强度、条件状态、验证结果等
字段做通用顺序，不使用 route ID、金标、命中位次或由 dev20 答案拟合的
权重。`report_rank`、同 `cn_identity` 去重和来源引用随新顺序一致重算；
原选中反应及 `ReactionEvent` 不因显示顺序改变。若要修改 ranker prompt
或模型 `order`，须作为**另一个实验臂**，因为它可能改变选中卡和候选
集合，不能称为纯重排。

**硬验收**：先用 dev20 新单步 C0 的旧答卷做零 API 回放，逐题检查排序
前后 reportable `cn_identity` 多重集合、宽度、@5 完全相同，只有位次
可以变；`@1/@3` 同时报 promote 与 demote。补
`tests/test_report_adjudication.py`、`tests/test_export_v2.py` 的多卡、
重复身份、宽度 5、选中卡不在首位、崩溃恢复反例。纯重排若造成任何
@5 变化或绕过验证，直接判失败。

## 5. E2：候选召回与进入任务，主攻 hit@3 / hit@5

**当前代码断点**：`services/reaction_finder.py:EngineReactionFinder.find`
把 v3 `expand_raw` 映射成 recorded/rule/analog 卡；
`domain/policy.py:classify_evidence` 遇唯一合格 recorded 直接提交；
`services/prediction.py:build_prediction_task` 对 rank 只取
`usable_recorded[:max_candidates_for_ranking]`（默认 8）。检索池中有某
结构不等于该卡有资格直接成为报告产物。

按 dev20 E0 的实际断点拆为**三个独立变体**，每次只做一个：

1. **E2a 排名任务截断**：若有合格 recorded 卡因 8 卡上限未进任务，
   在 `build_prediction_task` 增加版本化、预算有界的入围规则，逐卡记录
   `eligible / shortlisted / excluded_reason`。入围只用条件、来源与运行时
   检索字段，不按金标选择；`rank_candidates` 仍只许合格 recorded。
2. **E2b 唯一 recorded 直通**：仅当 E0 证明另有可迁移的竞争证据时，
   在 `domain/policy.py` 与 `workflow/nodes.py` 增加独立提案/验证支路；
   保留 recorded 原证据，rule/analog 先过供体适用性、编辑执行及产物
   验证，再决定能否参与报告。禁止直接将原始 rule/analog 卡加入 rank
   任务或因其检索出现就提交。
3. **E2c 真召回缺口**：先区分 `engine_meta.budget_cut/pool_capped` 与
   v1 资产全池确无来源。若是截断，在 `adapters/v3_engine.py`、
   `reaction_finder.py` 实现有界补召回并保留原/补召回来源与排序；若是
   资产缺席，转 E5 独立资产版本，不在 E2 偷换语料。

每个变体要交逐卡漏斗（检索→资格→任务→验证→报告）和明确拒因，
监测旧 dev20 命中题倒退、空答、异常、费用及 hit@1/3/5。新增候选
必须通过现有 `validate_card_for_reporting`、
`validate_products_node` 与 `validate_adjudication_payload`；单看召回率
或 task 候选数增加不算成功。测试放在 `tests/test_prediction_task.py`、
`tests/test_prediction_workflow.py`、`tests/test_report_adjudication.py`，
覆盖异底物/方向错误、条件冲突、无映射、超限和跨身份 resume。

## 6. E3：产物生成，E4：类比编辑，E5：资产覆盖

**E3 生成任务**：`build_prediction_task` 在 `novel_proposal` 模式下当前
`candidates=[]`，只留下检索引用，不能假设模型看到了那些卡。若 dev20
E0 证明“检索已有可用线索但生成链未利用”，给 novel 任务增加有界、
结构化的检索状态/适用性拒因上下文，并同步版本化
`configs/prompts/novel_proposal.md`。明确区分“完全无证据”和“有证据但
映射/条件未过门”，不得把未验证产物写成事实或照抄进报告。改
`services/prediction.py`、`workflow/nodes.py:_apply_novel` 及相关测试；
验收看**通过最终化学门禁且实际进入报告位**的产物，而非提案数。

**E3 多组分分支**：仅当 dev20 人审发现全串少报/错组装时，追踪
`product_smiles_full` 从检索卡、预测提案、
`report_adjudication` 到导出；修丢失字段或顺序，不改正式整串
`cn_identity` 口径。测试单产物、真正多产物、盐/辅因子及额外错误
组分。金标歧义单列数据问题，不靠改 scorer 消除。

**E4 类比编辑**：若 dev20 的编辑执行或 `target_consistency` 是断点，
在 `workflow/nodes.py:_apply_analogy` 与
`configs/prompts/analogy_editor.md` 改善可执行编辑表达；需要重试时
最多增一个有界、独立计费且写入 run identity 的重试分支，沿用同一
通过资格门的供体。AtomTool、元素/键级、目标一致性和最终产物验证
始终 fail-closed；不接受模型只声明目标却无法执行的产物。测试拒因、
幂等、恢复和费用账。

**E5 资产覆盖**：只有 dev20 E0 证明 v1 完整池缺口才启动。新增来源
须有许可/来源/化学复核记录、独立资产版本和逐文件 SHA；与 E1–E4
分臂，不把资产变化的效果归给排序、生成或 D1 相似通道。

## 7. 实验与采用门

1. E0 后、看到变体分数前写明每个模块的单一主终点、最小有用增益、
   次级指标最大回退、费用/失败上限和停机规则。20 题样本小，逐题
   配对四格与不确定性一起报告，不用百分比小变化宣称确定性效果。
2. 每个变体只改一个机制；先在 dev20 建立 1/1/5 单步 C0 基线，
   之后同版 C0 对照保持输入、代码、资产、模型、
   预算、scorer、价格快照相同，除预登记差异外身份逐字段相等。真实
   调用前通过无凭证回归和单独计账烟测；使用新 run 根，禁止跨身份
   resume。两臂都须 20/20 合法终态、完整 usage 与失败/429/孤儿账。
3. dev20 可以决定是否继续改进，但“adopted”是**开发期候选**。全部
   模块与配置冻结后，EC298 只做一次 Phase E 终测；看到终测分数后
   不得再改同一版本并重复声称 final。若需下一轮改动，另起版本和
   新终测集。
4. 终测需与冻结 C0 配对，报告 hit@1/@3/@5、逐题四格、空答、停因、
   费用和化学门禁。终测评分只在独立评分进程读金标。费用账单回填
   与结构合法性分开判定。

## 8. 交付

- **Phase E 完成定义**：不能以 E0、任务书或报告修订代替算法修复。
  至少一个 E1/E2/E3/E4 变体须形成版本化运行代码、针对性测试和
  dev20 同口径配对结果；只有代码/配置冻结后的一次 EC298 终测满足
  预登记指标且门禁通过，才能写“确认提升 hit@K”。否则明确写
  `dev_candidate`、`inconclusive` 或 `rejected`，不能写 `adopted`。
- dev20 E0 报告与证据、各模块设计/测试/实验登记、配置/代码/资产/
  prompt/scorer SHA、逐题配对与费用账。
- `docs/PHASE_E_REPORT.md`：每模块 `dev_candidate | rejected |
  inconclusive | not_attempted`，冻结身份与终测结果分节列出；明确
  EC298 在此前被逐题审计过的历史暴露。
- 不修改 Phase D 旧 run、封存报告、金标或评分口径；任何终测重跑
  只用于事先定义的执行失败恢复，不用于择优。
