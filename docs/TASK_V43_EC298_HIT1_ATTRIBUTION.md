# v4.3 EC298 首跑 hit@1 失分逐题归因任务书

> 交给独立实施 agent；本会话负责 review。目标是回答「原来 298 题中 182 道未命中 hit@1 的题，失分发生在哪里；当前 Phase B/C/D 的改动分别触及哪些断点，效果是否已被验证」。本任务只做**封存首跑的离线审计与改动对照**，不实施新的预测策略。

## 0. 固定事实与边界

- 正式口径为 Phase A `v43-ec298-scorer-2`：agent hit@1/@3/@5 = **116/128/130**，因此 hit@1 未命中 **182/298**。引擎 Top-10 同口径为 **118/174/193/209**。旧 scorer 的「agent @1 比引擎多 34」已作废，不能用来定义本任务。
- 182 题按封存 decision 路径分为：唯一 recorded **48**、多 recorded rank **43**、analogy_edit **66**、novel_proposal **25**。四组相加必须为 182；模式来自持久 decision/prediction 产物，不从 SMILES 猜测。
- 既有 Phase A 的 `hit5_paired_attribution.tsv` 是 **@5 配对差异**分析，不能将其主因标签直接复制成 182 题的 @1 根因。其「模型选错 22」有任务候选层证据，但并不覆盖所有 rank 失分题。
- 「原始检索卡含金标」只是检索层重叠；不能推出该卡满足反应条件、进入任务、通过验证或能被报告。引擎导出的是 Top-10，不代表完整候选池。
- 唯一允许读金标的进程是离线分析脚本。**零 API、零预测/引擎重跑、零金标回灌**：不得把金标、命中标签或这 182 题用于候选选择、提示词、路由、预算、阈值及模型调参。后续若复跑已见 298，须标 `post_hoc_repair_check`，不得称盲测。

## 1. 输入、隔离与复现

1. 使用 Phase A 已封存输入清单 `reports/ec298/phase_a_v2/input_manifest.json`、正式逐题分数 `score_v2.json`、A3/A4 明细，以及同一份只读首跑镜像：`runs/ec298_v43r1/`、`ec298_gold_readonly/questions.jsonl`。原始 run 与金标在本仓不一定存在；实施者必须从**与清单 SHA 完全一致**的封存镜像显式传入路径。缺输入或哈希不一致时失败，不得拿当前代码重跑代替封存件。
2. 从 `score_v2.json` 选择 `agent_rank != 1` 的 qid；`null` 与 2–5 分开记录。对 298 行、182 个唯一失分 qid、四组 48/43/66/25、`agent_rank=2–5` 的 **14** 题设置硬对账。若任何锚点不符，输出差异清单并停止正式报告，不能改数据凑数。
3. 新脚本建议放 `scripts/ec298_hit1_attribution.py`，输出只写新目录 `reports/ec298/hit1_attribution_v1/`；不覆盖 Phase A、Phase B/C、首跑或金标文件。复用 Phase A 的只读 manifest 校验与 scorer v2 身份函数；不要另造近似 SMILES 匹配规则。记录脚本版本、Git SHA、工作树状态摘要、所有输入及输出 SHA。共享工作树有 Phase B/C 并行改动，归因脚本不得顺手修改其实现文件。
4. 归因脚本以 `--run-dir`、`--gold`、`--phase-a-dir`、`--out-dir` 等显式参数接收路径；不得写入 Chenyu 地址、密钥或本机私密绝对路径。正常复算必须验证既有输入清单，不能通过重建清单接受变动。若封存镜像暂时不可用，只交缺失输入的阻断报告，**不得**以 Phase A 的聚合表伪造逐题引用。

## 2. 182 题逐题表：先记事实，再写解释

交付 `hit1_misses.tsv`，**182 题一题一行**，附列字典。至少包含以下字段；布尔列使用 `true/false/unknown/not_applicable`，不能用空字符串同时表示「未查」「无」和「不适用」。

| 层 | 必需字段与核验方式 |
|---|---|
| 身份/评分 | `qid`、`input_index`、`run_id`、`path_id`、`agent_rank_v2`、`engine_rank_v2`、`n_gold_products`、`n_reported`、首位原始 SMILES/规范身份、与金标的正式同口径匹配结果；多金标逐一比较，不只检查第一金标。 |
| 路径/结局 | 持久 `decision_mode`、`prediction_mode`、`outcome`、选中 `evidence_id`、模型 `order`/候选位置、`decision_ref`、`task_ref`、`prediction_ref`、`validation_ref`、`report_ref`；无模型调用的直接 recorded 标 `not_applicable`。 |
| 证据五层 | `raw_retrieval_gold`、`task_candidate_gold`、`selected_gold`、`validated_reportable_gold`、`reported_gold`，各自的证据 ID、文件引用、来源种类、所用身份口径。**下层成立不自动推出上层成立**；没有相应持久产物时记 `unknown`，不能填 `false`。 |
| 首位断点 | `first_proven_loss_stage`、`observed_mechanism`、`cause_confidence`、`uncertainty_reason`、可复核的源文件路径/记录 ID/字段或哈希。断点是可观察事实；化学或模型因果推测单列 `causal_hypothesis`，无证据则填 `undetermined`。 |
| 候选与门禁 | 含金标候选是否处在**模型实际选择集**、是否通过同底物/方向/条件/结构门禁、被选/未选、验证结果及拒因；`order` 中出现 ≠ 通过门禁，任务候选中出现 ≠ 被模型排序。 |
| 评分敏感性 | `multicomponent_candidate`、`any_component_hit1`、`formal_hit1`；任一组分匹配只作探索性诊断，两臂应采用同一替代规则，不得改正式 116/298。 |

另交 `evidence_trace.jsonl`：每题列出支撑上述判断的有限证据清单（相对封存根的路径、artifact/task/evidence ID、相关字段和文件 SHA），以及人工复核备注。不要复制整份金标题卷或大量模型原文；金标只保留离线匹配布尔、规范身份摘要及必要的复核引用。遇到文件缺失、互相矛盾或引用无法解析，列 `audit_gap` 并保留题目，不得静默丢行。

### 2.1 断点分类必须满足的证据条件

- `eligible_gold_not_selected`：必须有**当时真实 PredictionTask 的候选卡**含金标、该卡满足当时可用资格、且选择了别的卡。只在原始检索或引擎 Top-10 中见到金标，不得用此标签。把「模型未选」与「任务候选存在但未过门禁」分开。
- `selected_wrong_product`：指选中卡产物不匹配正式金标，是**观察结果**，不是「模型化学推理错误」的自动结论。唯一 recorded 的 48 题尤其要区分无模型直通、来源记录、底物/方向/条件和 benchmark 金标是否相容。
- `validation_rejected_gold`：须能指向相应产物及确定性拒因，并证明它在验证前与金标匹配；不能把旧类比的 `bond_already_present` 或 `unknown_atom` 直接称为「本可答对」。
- `validated_but_not_reported`：须有同一父路径的合格验证产物与最终报告/裁决落账记录，证明其确实被遗漏。没有独立可报告资格的原始卡不能算入。
- `reported_at_rank_2_to_5`：以正式 score v2 首命中位次为准；这 14 题属于首位排序问题，另记正确产物来源。不得将「提高 @5」等同于「提高 @1」。
- `retrieval_absence_within_observed_scope`：只能写清**检索了哪些已封存卡及范围**；缺完整候选池时不能称「数据库没有正确反应」。
- `unknown`：任何关键层缺证据、多个解释竞争、化学适用性仅靠猜测时使用；仍在事实列写出已核实的材料。

主因标签与多项事实列分离：允许一题有多个观察事实，但主断点至多一个，并给出选取规则。报告须说明标签互斥性、剩余 `unknown` 数和任何不可判定题的后续人工审查需求。

## 3. 四组专项审计

1. **唯一 recorded：48 题。** 核对选中 exact 记录的底物身份、产物、方向、条件、来源文件/行号及资产 SHA；与金标逐组分对照。分别统计「当前选中记录不含金标」「另一条真实合格 exact 记录含金标」「仅原始检索或引擎结果含金标」「多金标/组分口径敏感」「证据不足」。不能因为引擎 @5 命中就推断当前系统可合法报告它，也不能称模型选错。
2. **多 recorded：43 题。** 还原每题 PredictionTask 的选择集、模型 `selected` 和 `order`、各 recorded 卡的资格与产物。复核 Phase A 已证实的**至少 22**条「选择集内含金标卡未选」；说明「未选」是否确实是首位失分断点，并单列任务中有卡却不在 `order`、模型选中卡自身无效、以及正确卡只在原始检索层的题。旧 R2 的「25/70 未选中 recorded 卡含金标」是不同集合口径，不得直接写成 25 个 @1 可修复题。
3. **类比：66 题。** 逐题对平 28 弃答、23 编辑拒绝、15 接纳但未命中；记录旧供体 `mapping_status`、对齐范围、模型响应、AtomTool 拒因或最终产物。可与 Phase C 的**只读再分类**按 qid 对照（23 仍适用、43 分流），但其 23/43 是**路由资格模拟**，不是新命中分数。Phase C 报告与旧 R2 对「23 条被拒目标中有多少直接匹配金标」存在 8/23 与 0/23 分歧；本任务须从封存目标字符串、正式金标和明确身份函数独立重算，列出逐题差异，不预先采信任一数字。
4. **novel：25 题。** 核实 14 题金标在第 2–5 位，另 11 题前五位没有正式命中；区分首位排序、未产生正确候选、结构门禁、输出截断及组分口径。`novel_proposal` 的 50 题并非「无检索产物」，不得把这 25 题称为真正零证据生成失败；原始检索重叠仅写事实，不上升为模型可用证据。

## 4. 改进对照：覆盖范围与实际效果分开报告

交付 `fix_coverage.tsv` 与报告中的对照表。每类断点列：`affected_qids`、所对应的 Phase B/C/D 改动、代码/版本引用、实施状态、review 状态、测试层级、是否有**冻结 dev 的真实模型同条件对照**、是否有新 @1 数据、可支持的结论与尚存风险。至少核对：

- **Phase A** 修正两臂评分口径；agent 298/298 的 rank 未变，所以它修的是测量，不是 @1 预测。
- **Phase B** 扩展经验证的报告候选，主要瞄准 @3/@5；当前策略的 `selected` 仍排首位，不得将「22 条可在后位报告」宣传成 @1 获益。截至本任务书编写时，独立 R1 review 为**暂不通过**（选中 recorded 资格、验证引用等缺口）；若实施时状态已变，必须按新证据更新，并注明版本/时间点。
- **Phase C** 供体适用性门禁与 AtomTool 编辑协议针对类比失效；旧 66 题的 23/43 分流及旧拒绝再分类仅是离线诊断。没有真实模型 dev 对照时，`hit@1 gain` 必须写 `not_measured`；新门禁减少类比进入率也可能把题转向 novel/hold，不能当作准确率提升。
- **Phase D** 目前是供体找回、模板重映射、预算实验的**草案**；以实际代码和交付报告为准辨认是否启动，不把计划算已实现。
- **尚未直接瞄准的断点**须单列：唯一 recorded 的金标/条件冲突、多 recorded 的首位选择、novel 的首位排序、多组分正式评分定义。对每项给低风险的后续验证方案，优先在冻结 dev 或新外考做成对比较；不得用已见 298 选参。

报告里用四个状态严格区分：`observed_in_first_run`、`implemented`、`independently_reviewed`、`measured_on_frozen_dev`。测试全绿只证明实现行为，不等于 298 或 dev 命中率提升。若有新 298 复跑，也只能作为 `post_hoc_repair_check` 独立列示，不并入首跑基线。

## 5. 输出与验收门槛

交付建议：

```text
reports/ec298/hit1_attribution_v1/
  input_sha256.json
  hit1_misses.tsv                 # 恰 182 行
  evidence_trace.jsonl            # 恰 182 行，逐题可回查
  group_summary.tsv               # 四组及证据层/断点计数
  fix_coverage.tsv                # 实施、review、效果分列
  score_sensitivity.tsv           # 主分数与多组分探索口径分离
  audit_gaps.tsv                  # 可为空，但须有文件与表头
  output_manifest.sha256
docs/EC298_HIT1_ATTRIBUTION_REPORT.md
scripts/ec298_hit1_attribution.py
tests/test_ec298_hit1_attribution.py
```

**硬门槛：**

1. `score_v2.json` 的 298 qid 与封存白名单完全一致；182 失分 qid 一一对应；48+43+66+25=182，14 道 rank 2–5 可逐题对账。按组给 `null` 与非首位 rank 的分布；标签计数之和与分母对平。
2. 每个非 `unknown` 主断点都有满足 §2.1 的实际输入、决策、验证或报告引用；抽查时能回到同一 run/qid/path，不能串父节点或用当前新代码产物冒充首跑事实。引用缺失或互相矛盾则 fail-closed 或明记 `audit_gap`。
3. 对「任务候选有金标」「验证通过但未报告」「类比目标匹配金标」等强结论设置**负例测试**：原始检索有金标但不在任务中、脏 recorded 卡、不同父路径相同 SMILES、验证前目标可解析却非金标、rank 2 正确但 rank 1 错、缺文件/改 SHA。测试必须能抓到证据越层，而不只是镜像实现代码。
4. 输入清单前后核对一致；正常复算字节一致；衍生文件及报告写明版本和 SHA；零 API、零封存写入、零预测实现/资产改动。Phase B/C/D 的当前状态来自实际代码和 review 文档，带快照时间，不仅引用实施者自报。
5. 报告首先回答用户的问题：哪些 @1 未命中原因**已被证实**、哪些只是断点或假设、各项改动是否已实施/通过 review/在冻结 dev 上证明 @1 收益；明确写出「目前尚无新 @1 提升证据」或以真实对照数据修正该句。不得以首跑的后验分析宣称泛化改善。

提交前只纳入本任务的脚本、测试、报告与衍生产物；现有共享工作树中其他未提交改动保持原样。实施者在交付说明中给出复算命令、输入镜像身份、测试输出、未判定题数和需要人工化学审核的 qid 列表，供本会话独立复核。
