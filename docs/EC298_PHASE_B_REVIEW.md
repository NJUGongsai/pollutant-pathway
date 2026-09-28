# EC298 Phase B 独立 Review（2026-09-28，R1–R3）

**最终判定（R3）：通过。** R1–R3 发现的问题均已修复并独立复核。第 1–3 节保留 R1 当时的发现与数据，不代表当前代码仍有这些缺陷；各轮闭环和最终验收证据见第 4–6 节。本 review 只检查代码、测试与产物，未修改预测实现、Phase A 封存件、资产或金标。

## 1. R1 当时的阻断项（历史）

### P1：选中 recorded 卡绕过同底物资格门禁，可被报告并提交

[`prediction.py`](../src/pathway_v43/services/prediction.py) 的 rank 任务候选筛选只要求 `kind=recorded_reaction` 且 `condition_fit != conflict`，不核对 `query_identity`、`reactant_identity` 或 `donor_exact_match`；路由只需检索集中另有两张 usable recorded 卡即可进入 rank。模型于是可能选到任务中那张不属于当前底物的 recorded 卡。

未选中卡会经过 [`report_adjudication.py`](../src/pathway_v43/services/report_adjudication.py) 的 `_recorded_card_reasons`，但**选中卡**在 `_selected_card_validation_view` 被直接置 `card_eligible=True`。[`nodes.py`](../src/pathway_v43/workflow/nodes.py) 的 `validate_products_node` 仅检查来源挂牌与产物结构，没有复核这张卡的同底物条件。三个路径相接后，选中卡可以占 `report_rank=1` 并进入 `ReactionEvent`。

我用独立临时 run 复现：当前底物为儿茶酚，两张真实同底物 recorded 卡使系统进入 rank；第三张 `reactant_identity=CN`、`query_identity=当前底物` 的 recorded 卡被放入任务。fake 模型选第三张且 `order=[第三张,另外两张]`。结果为 **1 个已提交事件**，最终裁决把第三张标为 `card_eligible=true`、报告第一位；其产物 `CC#N` 被提交。该反例不依赖 Phase C 的类比代码。

**修复门槛：** rank 任务候选与选中卡最终资格均使用同一 recorded 判据；即使任务候选构造出现脏卡，选中后也必须复验并拒绝，不得凭模型 `evidence_id` 升格。新增完整工作流回归：两张 usable + 一张异底物/方向错误/`donor_exact_match=false` 卡，模型选脏卡时零提交、零报告该卡、拒因和状态清晰；正常两张 usable 的解耦行为不回退。

### P1：最终可报告条目的 `validation_ref` 全为空，逐卡验证无法按裁决引用回查

[`report_adjudication.py`](../src/pathway_v43/services/report_adjudication.py) 的 `validate_card_for_reporting` 没有返回 `validation_ref`；`_selected_card_validation_view` 也没有写入已有 `validation_task_id`。裁决构造时用 `val.get("validation_ref", "")`，于是卡级与产品级的 `validation_ref` 均为空。`validation_verdict_hash` 虽有值，但没有定位到哪个不可变验证产物，也未在读取时与该产物逐项核对。

复现有两层：已交付的 `reports/ec298/phase_b/dev_off_runs/dev_off_pb_0074` 中，一条已提交产品的卡级和产品级 `validation_ref` 均为 `""`；另起两张 recorded 卡的临时 rank run，**选中卡与未选中可报告卡**的引用也全为 `""`。这不满足 [`TASK_V43_EC298_PHASE_B.md`](TASK_V43_EC298_PHASE_B.md) §2 的“每个 accepted/reportable 能回到不可变输入与确定性验证引用”，也使报告所称“逐卡来源与验证可回查”缺少直接引用。

**修复门槛：** 选中卡引用原 `validation.json` 的 task ID/产物名和 payload SHA；未选中卡引用对应 `cardval.<...>.json` 的 task ID/产物名和 payload SHA。最终裁决的每个可报告条目须能解析到真实验证产物及其对应 verdict，ID、位次、raw/cn 与 accepted 值逐项一致；缺失、错指、哈希不符时 fail-closed。新增一条真实工作流测试覆盖选中与未选中两种引用。

## 2. R1 当时的其他需修复项（历史）

### P2：任务候选与模型排序层被混写，六层漏斗会误计

[`report_adjudication.py`](../src/pathway_v43/services/report_adjudication.py) 构造卡记录时，`in_model_selection_set` 被定义为“被选中或出现在模型 `order`”。然而模型的选择集是 PredictionTask 的 `candidates`，即 `in_task=true` 的卡；模型可以省略某个任务候选的排序。复现：任务包含 A/B，响应只给 `order=[A]`，最终裁决显示 B `in_task=true`、`in_model_selection_set=false`，即把“模型看过但未排序”误记为“模型没有选择机会”。这会污染 Phase A 所要求的任务候选层归因。

[`phase_b_offline_diagnostics.py`](../scripts/phase_b_offline_diagnostics.py) 又将 `in_model_selection_set or card_eligible` 计作 `n_cards_gate_passed`，模型排序出现本身不是化学门禁通过。当前 off-model 的 32 个计数恰好不受影响，但真实模型批次会高估“逐卡过门禁”。请把 `in_task`、`in_model_order`、`selected`、`card_eligible` 分开命名与计数；任务候选数和验证通过数从各自事实源取值，新增“在任务中但不在 order 中”的诊断夹具。

### P2：v2 的 `export --verify` 可因删去裁决指纹块而跳过核对

[`export_v3.py`](../src/pathway_v43/output/export_v3.py) `verify_only` 分支仅在元数据含 `adjudication` 块时才比较当前裁决集合。该兼容分支对旧 v1 元数据合理，但对 v2 新导出不能可选。我将已交付的 `dev_off_pb_0074` run 拷贝到临时目录，仅从 `export_metadata.json` 删除 `adjudication` 字段，再执行 `export_run_v3(..., verify_only=True)`；返回仍是 **`verified=True`**。任务书 §4 要求 v2 的裁决集合指纹为新鲜度门禁。

请按导出/run schema 判断：v2 元数据缺裁决指纹或字段不完整即 `ExportStale`；只对确有历史依据的 v1 旧元数据保留兼容。增加删整个块、删块内字段和伪造版本的失败测试。

## 3. R1 当时的检查与范围限制（历史）

- 用本机 `depending43` 环境独立运行 Phase B 及相关恢复、PredictionTask、导出测试：**80 passed**；全仓 `OMP_NUM_THREADS=1 ... pytest tests/ -q`：**345 passed，耗时 480.82 秒**。交付报告的“298 项、295 通过/3 失败”属于实施时的旧共享工作树状态；当前树已包含更多 Phase C 改动，故这 345 项不能作为独立的 Phase B-only 版本签收。报告应更新测试时间点与所用代码状态。
- 资产 `MANIFEST.sha256`：**21/21 OK**。离线诊断文件独立汇总为 20 个唯一 run、10,926 张检索卡、32 个事件/报告/提交/展开产品，以及 `not_validated_for_reporting=5,778`、`in_path_cycle=51`、`unparseable_smiles=1`；与实施报告的 off-model 数字一致。这些数字证明离线产物自洽，**没有真实模型下未提交可报告候选的性能对照**。
- 源码与报告目前主要在共享工作树的未提交改动中，`HEAD` 仍为 Phase A 的 `5c8f284`，且 Phase B/C 改动重叠。复核修复时请给可识别的 Phase B 改动范围与起点 SHA，避免把并行 Phase C 的新语义归到 Phase B；无需回退其他任务。
- “提交集合 = 选中卡占用报告位次的产品”在 `committed ⇒ reportable` 和每父五位上限下内部一致，已明确改变 v1 的事件产品语义。本轮不将其列为阻断，但报告应继续披露：超过五个有效产物时，第六位以后保留验证记录、不会成为 ReactionEvent 或后续路径；不能把事件称为原始反应的全量产物。

**R1 当时的二轮复核入口（历史）：** 先修两项 P1，并补上 P2 的层次字段与 v2 新鲜度门禁；给出新增失败夹具、独立测试结果和实际裁决样例。后续复核结果见下文。

## 4. R1 遗留的闭环复核

- recorded 资格已集中到 `domain/policy.py::recorded_eligibility_reasons`，用于 rank 候选筛选、路由、产物验证和选中卡裁决复验。异底物、非精确匹配或 `donor_exact_match=false` 的卡不能由模型选择后升格；规则/类比卡也不会被 `_usable_recorded` 误判为 recorded。
- 可报告条目的 `validation_ref` 现在含 `task_id`、`artifact`、`payload_sha256`。读取端逐条核对验证产物的信封哈希、证据 ID、位次、原始 SMILES、规范身份及 accepted 值；缺失或篡改时导出拒绝。重跑的 dev 20 中 **32/32** 条可报告引用回查一致。
- 卡级 `in_task`、`in_model_order`、`selected`、`card_eligible` 已分开；诊断的化学门禁计数只取 `card_eligible`。v2 导出元数据缺裁决指纹块或五个必要字段时，`--verify` 报 `ExportStale`。

以上四项 R1 遗留已关闭；具体实现与夹具见 [`EC298_PHASE_B_REPORT.md`](EC298_PHASE_B_REPORT.md) §10 的 R1 修复记录。

## 5. R2 新发现及闭环

R2 复核另外发现两项阻断和一项文档问题：rank 曾允许模型选中原始规则卡并提交；同时删除 v2 最终裁决文件和元数据指纹块曾使 `--verify` 错误返回成功；报告数据字典仍保留已删除的 `in_model_selection_set`。

- rank 任务候选现仅含通过完整资格判据的 recorded 卡。独立复现“两张合格 recorded + 一张规则卡，模型选规则卡”得到 `awaiting_prediction`、零事件、零最终裁决。裁决层另设守卫：即使上游错误地选中检索层规则/类比原始卡，其产物也不占报告位次。
- v2 裁决指纹的预期 schema 取自 `run_identity.json`。我在真实 `dev_off_pb_0074` 的临时副本中删除两份最终裁决：保留指纹块时因集合变化报 `ExportStale`，连指纹块一起删除时同样报 `ExportStale`。合法 v2 空裁决 run 使用可复算的 v2 空集合指纹。
- 报告 §2 数据字典已改为四层字段，不再把任务候选与模型排序混写。

以上三项 R2 发现已关闭；对应回归夹具见 [`test_phase_b_workflow.py`](../tests/test_phase_b_workflow.py) 与 [`test_export_v2.py`](../tests/test_export_v2.py)。

## 6. R3 最终复核与验收

R3 复核发现并现已关闭两处剩余问题：身份声明为 v2 的 run 曾可按非空 v1 裁决静默走旧投影；异常守卫中的检索层规则卡虽有 `not_validated_for_reporting` 拒因，同名布尔字段却为 false。

- [`export_v3.py`](../src/pathway_v43/output/export_v3.py) 的 `check_adjudication_schema_identity` 在导出和 `--verify` 两个入口核对身份声明与实际非空裁决 schema。我独立构造双向失配：**v2 身份 + v1 裁决**、**无声明旧身份 + v2 裁决**，导出均报 `LedgerCorrupt`；已有导出物的 `--verify` 也均报 `LedgerCorrupt`。**v2 身份 + 空裁决**及**旧身份 + v1 裁决**继续合法。
- 检索层规则卡的选中守卫视图现为 `card_eligible=false`、`not_validated_for_reporting=true`，对应产物 `accepted=false`；已过模型提案门禁的卡不受该拒升格规则影响。
- 独立重跑 Phase B 与相邻恢复/导出测试：**76 passed**；另外两项 Phase C 相邻守卫测试：**2 passed**。全仓 `OMP_NUM_THREADS=1 PYTHONPATH=src:tests python -m pytest tests/ -q`：**387 passed / 0 failed（509.14 秒）**。全仓运行前后 `src/`、`tests/`、`configs/` 的 99 个代码/配置文件内容快照一致；此前共享工作树移动期间报告的两项失败在这一稳定快照下未复现。
- 已交付的 dev 20 off-model run：**20/20 `--verify` 通过**；其中 11 个合法空裁决 run 的指纹为 v2、`n_adjudications=0`；**32/32** 条可报告产物验证引用逐项回查一致。此离线检查只验证结构和来源，不作为真实模型效果结论。

**验收结论：** 按 [`TASK_V43_EC298_PHASE_B.md`](TASK_V43_EC298_PHASE_B.md) 的范围，Phase B 的候选报告、事件提交与路径展开分层，以及资格、引用、schema 身份和导出新鲜度门禁均通过本轮复核。可以作为后续 Phase C/D 工作的底座。
