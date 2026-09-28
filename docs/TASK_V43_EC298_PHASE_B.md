# v4.3 EC298 Phase B 任务书：候选报告与路径展开解耦

> 交给独立实施模型；本会话负责 review。目标仓：`/Volumes/CC/Enzyme_Agent/dependingv43/`。依据已验收的 [`EC298_PHASE_A_REPORT.md`](EC298_PHASE_A_REPORT.md)、[`EC298_PHASE_A_REVIEW.md`](EC298_PHASE_A_REVIEW.md) R3 与 [`EC298_REVIEW_R2.md`](EC298_REVIEW_R2.md) §6。实施前阅读 [`ARCHITECTURE.md`](../ARCHITECTURE.md)、[`TASK_V43_EXPORT_DEV.md`](TASK_V43_EXPORT_DEV.md) 和当前代码；文档中的历史方案不替代实际接口检查。**本阶段只改候选裁决、报告投影及其必要的工作流接线；类比适用性、AtomTool 编辑协议和模型成本优化另属 Phase C/D。**

## 0. 问题与本阶段目标

Phase A 的正式口径为：298 题 agent @1/@3/@5 = **116/128/130**，引擎 Top-10 = **118/174/193/209**；agent 输出宽度为 0 个 51 题、1 个 197 题。`rank_candidates` 70 题中，22 条 engine-only 题的**模型选择集**存在含金标的未选中 recorded 卡；这证明候选进入过任务，尚不证明该卡通过全部报告门禁。82/82 的原始检索重叠更不能直接当作可报告覆盖。

当前 `workflow/nodes.py::_report_adjudication_payload` 只写被选卡的产物；`output/export_v3.py::project_route` 又要求 `reportable_ids == event_products`。因此报告列表被已提交事件锁死，模型的 `order` 不能形成同一父节点的多候选答卷。本阶段建立**每个父 PathInstance 的候选报告裁决**：逐卡审查，合格产物可进入最多五位的报告列表；只有策略选定的反应进入 ReactionEvent，只有调度选中的产物成为继续探索的 frontier。报告声明、化学事实和调度决定须分别可追溯。

成功标准是架构和证据口径正确；**不承诺 22 题都能挽回，也不以 298 金标选择报告顺序或放宽门禁**。每条新增候选必须能说明来源、门禁和排序，失败者留拒因。

## 1. 范围与不可改动项

1. 保留 Phase A 的 `reports/ec298/phase_a_v2/`、`score_v2.json`、封存首跑 `runs/ec298_v43r1/`、金标及其输入/输出清单原样。不得覆盖、迁移或用新代码 `resume` 旧 run。代码/策略改变后使用新 run ID；旧 run 的导出仍按旧 schema 读取，或通过显式只读旧版导出入口读取，不能被新规则悄悄重解释。
2. 不修改资产、v3 冻结评测器、split、Phase A scorer v2 的身份/计分规则；金标只能由离线评测进程读取，不能进入 ReactionFinder、PredictionTask、prompt、裁决或运行配置。测试夹具可用人工构造的已知答案验证逻辑。
3. 保持已有 `commit_recorded` 的唯一 recorded 直通、`rank_candidates` 只能在既有证据 ID 中选择、类比/novel 的 AtomTool 和元素门禁、预算及孤儿调用记账。不得为了增加宽度把未检验检索卡、模型原文、弱映射供体或无效 SMILES 当成产品输出。
4. 仅在本阶段功能验证需要时运行冻结 **dev 20**；保持 `eval 100` 未触碰。298 是已见试卷，如后续另行做新版 298 复跑，只能标为 `post_hoc_repair_check`，不得作为新盲测或本阶段选参依据。本任务书不要求新一轮 298 付费运行。
5. 工作树已有其他未提交改动；实施者先保存 `git status` 与起点 SHA，按文件范围改动，不清理、不覆盖其他任务的文件。不得将密钥或金标原文写入仓库/日志。

## 2. 数据契约：一父节点一份完整候选裁决

新增版本化不可变产物，建议 `report_adjudication` schema v2；沿用 `ArtifactStore` 的 task_id、payload SHA 和同键同内容幂等。一个父 `path_id` 的**每张进入审查范围的证据卡**都有卡级记录，卡内每个产物有产品级记录；未通过者也保留明确拒因。审查范围至少包括本父检索产物、实际 PredictionTask 候选、模型提案卡及选中卡，并标明每张卡从哪一层进入、是否在模型选择集。不能把“不在任务中”冒充“模型未选中”。

每个产品记录至少包含：`path_id`、`evidence_id`、卡种/来源级别与来源文件及 SHA 引用、`retrieval_rank`、`task_candidate_position`（不在任务中为 null）、模型 `order` 位次（未给出为 null）、卡内 `position`、原始 `product_smiles_full`/`product_smiles`、由原始字符串重算的 `cn_identity`、逐卡确定性验证产物引用及其哈希、`accepted`、`reportable`、`report_rank`、`committed_event_ref`（未提交为 null）、`expand_selected`、`deferred`、拒因/去重因。卡级记录给证据资格判定、`condition_fit`、方向/底物匹配、映射适用性状态、策略版本和模型决策引用。若资产不能提供真正 raw 形，应如实标注字段来源，不用 canonical 冒充 raw。

必须建立并在代码中检查以下不变量：

- `expand_selected ⇒ committed_event_ref != null ⇒ reportable ⇒ accepted`；事件中的有效产物必须能在本父裁决中逐位找到，但**可报告集合可以大于已提交事件产物集合**。已提交事件的 deferred 产物仍属事件事实，`expand_selected=false`；未提交的可报告替代产物没有 PathInstance、不会生成下一步。
- `report_rank` 仅给最终可报告去重项，按父节点连续从 1 编号，最多五位；少于五位就少报。相同 `cn` 的多卡候选只占一个位次，保留全部来源/验证引用，标注主来源选择规则。原始字符串与身份必须重新核对，不信任缓存 `product_identity`。
- 审查与报告以父 `path_id` 为作用域，禁止兄弟或同分子另一来路串线。`reportable` 是预测报告资格，不能把未提交的候选写成已证实 ReactionEvent，也不能把模型/引擎分数当校准概率。
- 卡或产物未满足其证据类型的门禁时，`reportable=false` 且拒因具体。recorded 至少核对同规范底物、精确来源、反应方向、条件无冲突、可解析/价态、路径内循环和产物身份；复用现有确定性校验，但不能直接用针对已提交兄弟路径的 `sibling_dedup` 拒绝所有未提交替代卡，跨卡去重须单独定义。规则/类比原始卡只有结构可解析不等于反应适用；缺映射适用性或缺可复核门禁的，记录 `not_validated_for_reporting`，留给 Phase C。已通过当前 AtomTool/提案门禁的产物保持原有资格。
- 每个 `accepted/reportable` 都能回到不可变输入与确定性验证引用；不能仅凭模型 `order`、检索分数或金标把卡升级为可报告。验证器对部分有效、部分无效的多产物卡逐项裁决，不因一项失败丢掉其余有效项，也不让无效项占报告位次。

## 3. 排序、选中反应和工作流接线

定义唯一的纯函数裁决策略并版本化，输入为本父检索/任务/预测/验证产物与已有路径状态，输出为完整候选裁决和最多五位的报告列表；报告与导出共用这份产物，不各自再做一次排序。

1. **唯一 usable recorded**：既有直通卡的合格产品保持首位及原顺序；随后才考虑本父其他**逐卡证明可报告**的候选。不得因凑宽度调整 exact known 的首位，不自动调用模型。若其他规则/类比卡缺适用性证据，保留卡级拒因，不填入报告。
2. **多 recorded / `rank_candidates`**：选中的 `evidence_id` 仍决定唯一要提交的 ReactionEvent；它的合格产品占优先报告位次，模型 `order` 仅为剩余候选的相对顺序提供依据。新协议要求 `order` 中的 ID 均来自本次任务候选、无重复，且 `selected_evidence_id` 恰出现一次并排第一；未知 ID、重复或 selected 不在首位都算解析失败，走既有有界重试。若旧形制未给 `order`，只报告被选卡的合格产品，记录 `order_missing_selected_only`；`order` 不完整时仅按列出的卡排列，不自动把遗漏卡补进报告。唯一 recorded 直通没有模型顺序，此时额外合格卡才按冻结的 `retrieval_rank,evidence_id,position` 后备键排列，并标明 `rank_basis=deterministic_fallback`。不要从未进入模型选择集的预测性卡推断模型认可。
3. **类比和 novel**：现有被接纳的提案产物按原有策略报告、提交和调度；类比供体只是推理依据时不能把供体原始产品另列为本底物的报告产品。Phase C 再处理弱映射、供体选择和 MoleCode 编辑能力，本阶段不靠“放宽拒绝”提分。
4. **选择与状态**：先将检索/预测的不可变输入落盘，再完成所有候选验证和报告裁决；仅对选中且通过门禁的卡调用 `submit_event`，按既有 `schedule_products` 生成 frontier/deferred。若选中卡全被拒，明确 `awaiting_prediction` 或 `dead_end`，不可为了出分偷换另一卡作为提交事件；其他通过门禁的卡能否只报告不提交，须在裁决与导出中一致表达。模型 `hold/abstain/failed` 不等同于批准其他候选，报告资格需有单独的可核验证据和冻结策略。
5. **崩溃恢复**：区分可重算的候选裁决草稿与最终 `report_adjudication`；草稿不得被导出读取。先固定验证/排序草稿，再幂等提交事件，最后写含真实事件引用的最终裁决；无选中事件时以显式 `no_event` 终态最终化。使“草稿已写、事件未提交”“事件已提交、最终裁决未写”“最终裁决已写、checkpoint 未写”三处硬杀后复跑得到同一账本与同一裁决；不出现半成品可导出。不得覆盖不可变产物。策略、prompt/schema、排序规则进入 run identity/task_id；旧身份 resume 必须拒绝。

## 4. 导出、研究报告和历史兼容

更新 `output/export_v3.py`：v2 裁决以 `report_rank` 投影 `predicted_products`，账本只交叉核对 `committed_event_ref` 指向的产物及其 `position/raw/cn`，不得再要求整个可报告列表等于 event_products。未提交的可报告产品进入该父步骤，但不产生子步骤；如果父节点完全没有 ReactionEvent，只要存在最终可报告候选，也须能生成一个父步骤。若决定不允许这种状态，须在策略中明确并测试，不能被导出器无意删掉。

继续保持：每父最多五位、`product_smiles_full` 优先回落 `product_smiles`、`cn/raw_sb` 双口径不串、同身份父节点按现有首现合并语义投影、稳定排序与去重、数据损坏 fail-closed。更新 `output/report.py::top5_reportable_products` 读取 v2 全父裁决，仍与 `top5_candidates` 检索视图区分；报告中同时给报告数、已提交数、frontier 数、仅报告未提交数和来源等级，不把报告宽度说成展开宽度。

旧 `v43-report-adjudication-1` 产物和旧导出应通过显式 schema 分派继续可读；新旧 schema 混在同一 run，或裁决/账本/身份不一致时拒绝。导出元数据加入候选裁决 schema/策略版本、全部裁决产物内容哈希的聚合值及已提交事件引用；`export --verify` 除 graph revision、策略和 run identity 外，还核对裁决集合及哈希、答卷文件自身 SHA。新增/删减/篡改裁决、事件变动或策略变动都使旧导出过期。不得用文件修改时间或遍历顺序决定答案。

## 5. 实施顺序与验收夹具

建议分四个可 review 的提交：**(a)** 纯函数裁决与 schema/验证器；**(b)** 工作流落盘、提交与恢复；**(c)** v2 导出、研究报告和旧版兼容；**(d)** 冻结 dev 对照报告。每批说明改动文件、旧测试影响和新增不变量，避免一次性改完整图后无法归因。

必须覆盖以下无凭证测试，重点检查真实产物和账本，不只测纯函数返回值：

1. 同父两张 usable recorded 卡：模型选 A，`order` 含 B；A 有效占 @1，B 逐卡验证后可报告但不提交、不生成子路径。B 若条件冲突、底物不符、无效 SMILES、循环或方向错误，则留拒因且不占位。模型原文自造产品、未知/重复 ID、顺序冲突都不能入答卷。
2. 唯一 recorded + 其他卡：首位及下一步稳定；其他仅在完成证据类型对应验证后才排在后面；原始规则/类比产品不得因可解析就进入答卷。选中卡多产物含有效/无效项、同 `cn` 多证据、多来路同分子父节点、带电 raw 形均有夹具。
3. `max_reportable_products=5` 与 `max_frontier_width` 分别限制报告/展开：至少七个合格产品时只报五个；有可报告未提交候选和已提交 deferred 产物两种不同状态；两者都可报告但都不得凭空产生下一步。`cn` 与 `raw_sb` 夹具对照 v3 冻结评测器。
4. 三处硬杀/重放：验证/裁决草稿落盘后、事件提交后、裁决最终化但 checkpoint 未写时；比较最终账本事件数、裁决 payload SHA、导出 JSONL 字节与模型调用账。无重复事件、不多耗 API 预算、不出现无法解释的悬空裁决。损坏/缺失/多余裁决及原始 SMILES 与身份不符时 fail-closed。
5. 旧 schema run 导出逐字节或逐字段保持原结果，新 schema run 无旧版身份混用。`export --verify` 对候选产物集合增删改及答卷文件篡改报过期；`top5_reportable_products` 与导出前五逐位一致。
6. 全仓回归通过；至少实际复跑与候选、PredictionTask、恢复、导出、score_report 相关的现有测试。测试总数由实施者实测报告，不把 Phase A 的 **264 passed** 当作本阶段完成数。

## 6. dev 对照与交付报告

先用无模型合成夹具和已有 dev 产物做**离线、无金标参与的结构诊断**：每父检索卡数、任务候选数、逐卡过门禁数、可报告宽度、已提交/展开数、拒因分布及来源等级。旧 dev run 只能用旧 schema 读取，不能把旧产物直接套新排序声称新版表现。

若执行新的真实模型 dev 20 路：固定输入清单、模型/提示词/资产/策略、预算与并发配置，用**新的批次/run ID**，保留原版 dev 对照；相同 v3 冻结评测器同时报告 `cn` 与 `raw_sb` 的 @1/@3/@5、路线指标和逐题配对变化。同时报告报告宽度与展开宽度，并审计 @1 是否保持 exact known 优先。旧/新代码或模型配置不同，逐项披露，不能把差异全归因于 Phase B。现有 Chenyu/DashScope 凭证只在远端环境文件读取；报告不写密钥。若资源或凭证不足，明确 `dev_real_run_not_executed`，交付无凭证测试与离线诊断，不用 fake 成绩冒充效果。

交付 `docs/EC298_PHASE_B_REPORT.md`、schema/排序/门禁的数据字典、代码与测试、可复现命令、旧/新导出样例和哈希、dev 对照表及逐题差异（若真实运行）。报告必须区分**原始检索 → 任务候选 → 通过验证 → 可报告 → 已提交 → 已展开**六层，按层给分母与引用；不根据金标事后改资格或排序。Phase A 的 298 数字只作基线引用；任何新版 298 分数另标事后修复验证。

## 7. 本会话 review 门槛

我将按以下顺序审核：**逐卡资格是否真实通过确定性门禁；报告列表与事件/路径是否严格分离；rank 的来源和 exact known 首位是否稳定；历史 run/封存基线是否保持；崩溃恢复与导出新鲜度是否可复核；dev 比较是否同口径且没有金标泄漏。** 任一候选仅因出现在检索、模型 `order` 或引擎 Top-10 就进入报告，均不通过。
