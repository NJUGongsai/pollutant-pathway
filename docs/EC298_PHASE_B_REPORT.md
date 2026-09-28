# EC298 Phase B 交付报告:候选报告与路径展开解耦

> 实施依据 [`TASK_V43_EC298_PHASE_B.md`](TASK_V43_EC298_PHASE_B.md);基线为已验收的 Phase A([`EC298_PHASE_A_REPORT.md`](EC298_PHASE_A_REPORT.md) / R3)。起点 SHA `5c8f284`(HEAD 未变,改动在工作树未提交状态)。本阶段**未调用任何付费模型 API**;金标仅由离线评测器读取,未进入检索、预测、裁决或运行配置。
>
> **R1(2026-09-28):首轮 review 两项 P1、两项 P2 已全部修复并复测**,修复记录见文末 §10;§0/§6/§7 中与修复前状态相关的数字已就地更新(修复前的交付物存档于 `reports/ec298/phase_b/*_pre_r1fix.*`),测试时间为 2026-09-28、基于当前共享工作树(含 Phase C 会话遗留改动,见 §9/§10)。
>
> **R2(2026-09-28):二轮 review 两项 P1(规则卡可经 rank 选中提交;verify 可删裁决绕过)、一项 P3(文档残留字段)已全部修复并复测**,见 §10 末 R2 修复记录;dev 20 off-model 已重导出并全部通过 `--verify`(空裁决 run 的指纹块如实标注 v2/n=0)。
>
> **R3(2026-09-28):三轮审核确认 R2 三项关闭;新增 P2(裁决 schema 与 run identity 不一致仍可导出)、P3(守卫视图布尔字段与拒因不一致)已修复**,见 §10 末 R3 修复记录;导出与 verify 现均强制"裁决 schema ⇄ 身份声明"一致性核对,双向失配(v2 身份配 v1 裁决、无声明身份配 v2 裁决)都有拒绝测试。

## 0. 结论概要

Phase B 建立了**每个父 PathInstance 一份完整候选裁决**(`report_adjudication` schema v2):逐卡审查、逐产物验证,合格产物进入最多五位的报告列表;只有策略选定的反应进入 ReactionEvent,只有调度选中的产物成为 frontier。报告列表与已提交事件产物**正式解耦**——可报告集合可以大于事件产物集合,未提交候选进父步骤但不产生子步骤。

- 新增纯函数裁决层 `services/report_adjudication.py`(裁决 + 不变量校验),rank 协议收紧(order ⊆ 任务候选、无重复、selected 恰一次且排第一),裁决策略/版本进入 run identity(旧 run resume 被拒)。
- 工作流新增 `adjudicate_candidates` 节点:**先固定验证/排序草稿 → 幂等提交事件 → 写含真实事件引用的最终裁决**;三处硬杀(草稿后/事件后/最终化后)重放实测同一账本与同一裁决。
- 导出器 schema 显式分派:v1 旧 run 逐字节保持原投影;v2 按 `report_rank` 投影并只交叉核对 `committed_event_ref` 指向的产物;`export --verify` 新增答卷文件 SHA 与裁决集合指纹核对。
- 测试(R1 修复后,2026-09-28):**全仓 356 passed / 0 failed**(当前共享工作树,含 Phase C 会话遗留改动;其中 Phase B 新增/适配测试 42 项全绿,明细见 §6/§10)。
- dev 离线结构诊断(无模型、无金标;R1 修复后重跑):dev 20 路全部重放完成、20/20 导出与 `--verify` 通过,**32 个裁决父节点的全部可报告条目(32 条)都能按 `validation_ref` 回查到真实验证产物并逐项一致**;5,777 张规则/类比原始卡被 `not_validated_for_reporting` 门禁如实拦下,52 条路径、32 个事件,报告宽度与展开宽度逐层可审计。**真实模型 dev 对照未执行**(`dev_real_run_not_executed`,§7)。

## 1. 问题回顾与本阶段不改项

Phase A 证明:22 条 engine-only 题的模型选择集内存在含金标 recorded 卡,但 `report_adjudication-1` 只写被选卡产物、导出又要求可报告集合 == 事件产物,模型的 `order` 无法形成同一父节点的多候选答卷。本阶段只改候选裁决、报告投影及必要接线;类比适用性、AtomTool 编辑协议与成本优化属 Phase C/D。

逐条核对不可改动项:

1. `reports/ec298/phase_a_v2/`、`score_v2.json`、封存首跑 `runs/ec298_v43r1/`、金标清单**零改动**(本阶段无任何写操作触及;旧 run 直接 resume 被身份核对拒绝,旧导出按 v1 schema 显式分派可读)。
2. 资产、v3 冻结评测器、split、scorer v2 未动;金标只在评测器内读取,裁决层无金标输入。
3. `commit_recorded` 唯一 recorded 直通、`rank_candidates` 只能在既有证据 ID 中选择、AtomTool/元素门禁、预算与孤儿调用记账全部保持;未检验检索卡、模型原文、弱映射供体、无效 SMILES 均不能成为产品(实测见 §7:5,777 张原始卡被拦;R1 后选中卡同受完整资格判据约束,见 §10)。
4. dev 20 以**无模型、无金标**方式重放用于结构验证;`eval 100` 未触碰;未做 298 复跑。

## 2. 数据字典:`report_adjudication` schema v2

产物名 `results/<adjudication_task_id>/report_adjudication.json`(最终态)与 `report_adjudication_draft.json`(草稿;导出永不读取)。`adjudication_task_id = stable_id("T", run_id, path_id, "adjudication", substrate_identity, STRATEGY_VERSION, REPORT_ADJUDICATION_POLICY_VERSION, manifest_sha, source_file_sha)` —— 裁决策略版本进入幂等键。未选中卡的逐卡验证产物为同任务目录下 `cardval.<sha256(evidence_id)[:16]>.json`。

顶层字段:`schema_version="v43-report-adjudication-2"`、`stage=draft|final`、`run_id/path_id/substrate_identity`、`policy`(§3)、`rank_basis`、`selection`、`cards[]`、`products[]`、`event`、`n_reportable/n_committed/n_expand_selected/n_deferred`。

**卡级记录**(`cards[]`,每张进入审查范围的卡一条):`evidence_id`、`kind`、`source_id`、`entry_layer`(`retrieval|model_proposal`)、`in_task` 与 `task_candidate_position`(不在任务中为 null)、`selected`(是否选中卡)、`in_model_order` 与 `model_order_position`(不在模型 order 中为 false/null)、`retrieval_rank`、`source_file`/`asset_sha256`、`condition_fit`/`match_type`/`mapping_status`、`card_eligible`、`not_validated_for_reporting`、`card_reasons[]`、`validation_ref`、`n_products/n_accepted`。"不在任务中"、"模型未排序"、"非选中卡"分别由 `in_task=false`、`in_model_order=false`、`selected=false` 独立表达,四层不互相冒充(R1 P2 起 `in_model_selection_set` 混写字段已删除)。

**产品级记录**(`products[]`,卡内每个产物一条,未通过者留拒因):`path_id`(作用域强制)、`evidence_id`、`card_kind`、`entry_layer`、`retrieval_rank`、`task_candidate_position`、`model_order_position`、`position`(卡内位次)、`product_smiles_full`/`product_smiles`/`raw_source`、`cn_identity`(**由原始字符串重算**,不信任缓存 `product_identity`;缓存值存于 `stored_product_identity` 并给 `identity_match` 对比)、`validation_ref` + `validation_verdict_hash`、`accepted`、`reasons[]`、`reportable`、`report_rank`、`dedup_reason`、`committed_event_ref`(未提交为 null)、`expand_selected`、`deferred`、`expand_status`、`endorsed`。

**事件块**(`event`,仅 final):`event_id`(无事件为 null)、`no_event`、`no_event_reason`(如 `selected_card_all_products_rejected`)。草稿的 `event` 必须为 null。

**代码内强制的不变量**(`validate_adjudication_payload`,写入前与导出/报告读取时都执行):

- `expand_selected ⇒ committed_event_ref != null ⇒ reportable ⇒ accepted`;已提交条目必须属于选中卡且与事件块一致;
- `reportable ⇔ report_rank != null`;`report_rank` 按父节点连续从 1 编号、最多 `max_reportable_products=5`;相同 `cn` 只占一个位次;
- 产品记录 `path_id` 必须等于裁决 `path_id`(禁止兄弟/同分子另一来路串线);
- no_event 终态必须带拒因且不含任何已提交引用。

## 3. 冻结裁决策略 `v43-repadj-1`

策略全文落盘于每个裁决 payload 的 `policy` 字段与 run identity 的 `adjudication` 块:

| 键 | 取值 | 含义 |
|---|---|---|
| `max_reportable_products` | 5 | 每父最多五位报告 |
| `rank_mode_order_contract` | `task_candidate_ids_no_duplicates_selected_first` | order 全部来自任务候选、无重复、selected 恰一次且排第一;违反=解析失败走有界重试 |
| `order_missing_policy` | `selected_only` | 旧形制未给 order:只报告被选卡合格产品,记 `rank_basis=order_missing_selected_only` |
| `order_incomplete_policy` | `listed_only_not_auto_filled` | order 不完整时仅按列出的卡排列,不自动补进报告 |
| `non_selected_promotion` | `model_selection_set_plus_kind_gates_only` | 未进模型选择集的卡不因检索/分数升格;hold/abstain/failed 不批准任何其他候选 |
| `raw_rule_analog_policy` | `not_validated_for_reporting` | 规则/类比原始卡结构可解析≠反应适用,留给 Phase C |
| `cross_card_dedup` | `keep_first_in_rank_order_record_all_sources` | 同 cn 多卡只占一个位次;主条目 `same_identity_sources` 保留全部来源/验证引用;主来源 = 排序键首个 |
| `unique_recorded_fallback_order` | `retrieval_rank_evidence_id_position` | 唯一 recorded 直通无模型顺序时,额外合格卡按冻结后备键排列,`rank_basis=deterministic_fallback` |
| `no_event_reportable` | `allow_report_only_step` | 父节点无事件但有最终可报告候选:允许只报告不提交,导出生成父步骤、无子步骤(策略显式允许并有测试) |

排序规则(唯一纯函数 `adjudicate_parent`):选中卡合格产品按位次占优先位次 → rank 模式下模型 `order` 剩余候选按序 → 其余背书合格卡按后备键。**提交集合 = 选中卡占用报告位次的产物**——这是 `committed ⇒ reportable` 不变量与"至少七个合格产品只报五个"同时成立的唯一一致语义(超出报告宽度的合格产物保持已验证、未提交,留 `report_width_cap:5` 拒因)。

**超过五位时的语义披露(R1 review 要求)**:选中卡有效产物多于五位时,第六位起保留完整验证记录(逐卡验证产物 + 裁决条目与拒因),但**不会成为 ReactionEvent 产物、不产生后续路径**;因此已提交事件**不等于**原始反应的全量产物集合,报告与导出均不如此声称——事件账本如实只含占位提交集,完整证据在裁决与逐卡验证产物中。

recorded 卡逐卡门禁:同规范底物(query/reactant identity)、精确来源(match_type + donor_exact_match)、反应方向、条件无冲突、可解析/价态、路径内循环、产物身份重算;多产物卡逐项裁决,一项失败不丢其余有效项。**不使用针对已提交兄弟路径的 sibling_dedup 拒绝未提交替代卡**,跨卡去重单独定义如上。

## 4. 工作流接线与崩溃恢复

图变更:`validate_products → adjudicate_candidates →(commit_pathway | mark_dead_end)`。`adjudicate_candidates`:写逐卡验证产物 → 固定草稿 → `crash_after=adjudicate_candidates` 注入点 → 有占位产物则进入提交,否则写 no_event 最终裁决(`crash_after=adjudication_finalized`)后显式死端。`commit_pathway`:从**草稿**读提交集合(不重算)→ `submit_event` 幂等提交 → `crash_after=commit_event` 注入点 → 写含事件引用的最终裁决 → `crash_after=commit_pathway`(沿用既有注入名)。State 新增 `adjudication_task_id`,随迭代隔离重置。

裁决策略/schema 版本进入 run identity(`adjudication` 块 + 指纹核对键)与裁决任务幂等键;代码身份覆盖全部 `src/pathway_v43/**/*.py` —— 旧 run resume 一律被 `IdentityMismatch` 拒绝,不得静默继续。

崩溃恢复实测(`tests/test_phase_b_workflow.py::test_crash_replay_three_kill_points_same_ledger_and_adjudication`,子进程真实 `os._exit(70)`):三个注入点硬杀后续跑,最终账本事件数/产物数/路径数与无崩溃基线一致,LLM 调用账一致(恢复不多耗),崩溃时刻已落盘的草稿/最终裁决在恢复后逐字节不变,每份草稿都有对应最终裁决(无悬空)。重放确定性由幂等写保证:恢复重算若内容漂移,`ArtifactConflict`/`EventConflict` 会直接使 resume 失败——resume 成功即证明同输入重算同内容。

## 5. 导出、研究报告与历史兼容

`output/export_v3.py` 按 schema 显式分派;同一 run 混用 v1/v2 拒绝,未知 schema 拒绝,非 final 状态拒绝。

- **v1(旧 run)**:投影语义逐条保持(可报告集合必须与事件产物逐位一致等);本仓两个旧 run 用新代码导出成功且 schema 标注 `v43-report-adjudication-1`。`runs/v43-predict-smoke` 导出报"已提交事件缺少候选裁决产物"——该 run 为历史中间态(0 份裁决产物 + 已提交事件),旧导出器有完全相同的 fail-closed 检查,**非本阶段回归**。
- **v2(Phase B)**:`predicted_products` 按 `report_rank` 投影;账本逐位对账范围 = `committed_event_ref` 指向条目 ⇄ 账本事件产物(position/raw/cn 双向集合比对),不再要求整个可报告列表等于 event_products;未提交可报告产品进父步骤不产生子步骤;无事件但有占位候选的父节点生成父步骤;`cn/raw_sb` 双口径不串(原始字符串进答卷,不提前中和);同身份父节点首现合并、稳定排序、每父上限 5、数据损坏 fail-closed 全部保持。
- **元数据**:新增 `adjudication` 块(schema 版本、策略版本、全部裁决 payload 内容哈希聚合 SHA256、`n_adjudications`、已提交事件引用清单)与 `counts.n_report_only_products`。
- **`export --verify`**:在 revision/策略/身份之外,新增答卷文件自身 SHA 核对与裁决集合指纹核对——新增/删减/篡改裁决、事件变动或策略变动都使旧导出过期(`ExportStale`)。
- **研究报告**(`output/report.py`):`top5_reportable_products` 兼容读取 v1 `entries` / v2 `products`,新增 `committed_event_ref` 列;每路径新增 `report` 块(报告数、已提交数、仅报告未提交数、展开数、来源等级)与 `adjudication` 引用块;summary 新增 `report_vs_expansion` 合计,不把报告宽度说成展开宽度。

## 6. 测试与验收覆盖(任务书 §5 六项)

新增 42 项(R1 修复后计数):`tests/test_report_adjudication.py`(20)、`tests/test_phase_b_workflow.py`(12)、`tests/test_export_v2.py`(12,含 v1 兼容与 verify 门禁夹具);改动 `tests/wf_helpers.py`(rank_response 支持 order 参数,向后兼容)。R1 新增回归:脏 selected 卡零提交(任务候选筛选 + 资格复验双层)、`donor_exact_match=false` 卡不进任务、验证引用端到端回查 + 篡改 fail-closed、verify 删块/删字段/伪版本失败夹具。

1. **同父两张 usable recorded**:模型选 A、order 含 B → A 占 @1 并提交,B 逐卡验证后可报告但不提交、无子路径;B 条件冲突 → 留 `condition_conflict` 拒因不占位;模型 order 未知 ID/重复/selected 不在首位 → 解析失败,1+2 次有界重试后显式停留,调用账=3,无裁决悬空。
2. **唯一 recorded + 其他卡**:首位与下一步稳定;规则卡 `not_validated_for_reporting` 不进答卷;选中卡多产物有效/无效逐项裁决;同 cn 多证据单占一位并保留全部来源引用;novel 提案产物正常报告而供体原始卡不升格。
3. **宽度分离**:七个合格产品 → 报告五位(`report_width_cap:5` 留痕),展开宽度 2 → 2 frontier + 3 deferred;deferred 已提交产物仍报告;两者都不凭空产生下一步。
4. **三处硬杀/重放**:§4 所述,比较账本计数、payload 内容哈希、LLM 调用账;无重复事件、不多耗调用、无悬空裁决;损坏/缺失/多余裁决与 raw↔身份不符均 fail-closed(test_export_v2)。
5. **旧 schema 兼容**:v1 run 新代码导出正常;混用 schema 拒绝;草稿永不进导出;`export --verify` 对裁决增删改、答卷篡改报过期;报告 top5 与导出前五逐位一致。
6. **全仓回归**(2026-09-28,R1 修复后):**356 passed / 0 failed**(当前共享工作树;含 Phase C 会话遗留改动及其配套测试 —— 实施首轮时的 3 项失败已由该会话中断前的自身修复闭环,详见 §9/§10)。Phase B 相关现有套件(候选、PredictionTask、恢复、导出、score_report、state 隔离、batch)全部通过。

## 7. dev 对照:离线结构诊断(无金标、`dev_real_run_not_executed`)

**真实模型 dev 20 路未执行**:本会话无模型凭证与批次预算,且任务书不要求新一轮付费运行;标记 `dev_real_run_not_executed`,交付无凭证测试与离线诊断,不以 fake 成绩冒充效果。

执行的离线诊断(零 LLM、零金标):

- **输入冻结**:新批次根 `reports/ec298/phase_b/dev_off_batch/`,`batch plan --split dev` 生成输入清单(route_id + root_smiles + SHA;金标 edges/leaves 不进入运行侧文件,清单头部记录 `gold_fields_excluded`);预算与原 dev 批一致(depth6/expansions40/width3)。新 run ID `dev_off_pb_*`,原版 dev 对照(`reports/export_dev/`)零改动。
- **执行**:20/20 路线以 `--model off` 确定性重放(总计约 16 分钟,单路 29–211s),20/20 导出成功,摘要与逐路线 SHA 见 `reports/ec298/phase_b/dev_off_export_summary.json`。

**六层漏斗**(脚本 `scripts/phase_b_offline_diagnostics.py`,输出 `reports/ec298/phase_b/diagnostics_dev_off.json`;分母与逐父引用均在 JSON 内;R1 修复后重跑):

| 层 | 计数 | 说明 |
|---|---|---|
| 原始检索卡 | 10,926 | 20 路、52 个被探索父节点合计 |
| 任务候选 | 0 | off-model:竞争 recorded 停留 awaiting,无 PredictionTask(11/20 路);分层计数 `n_in_task/n_in_model_order/n_selected` 分别为 0/0/32,无"在任务但不在 order"混计 |
| 逐卡过门禁 | 32 | 只按 `card_eligible` 计(化学门禁;模型排序出现不再计入),32 个裁决父节点 = 唯一 usable recorded 直通卡 |
| 可报告 | 32 | 全部来自 `recorded_reaction`;**32/32 条目 `validation_ref` 指向真实验证产物且回查逐项一致**(选中卡 → `validation.json`,含 payload SHA) |
| 已提交 | 32 | 提交集 = 报告占位产物,`n_report_only=0`(确定性通路无模型 order,无未提交替代卡——解耦行为由 §6 测试 1/3 覆盖) |
| 已展开 | 32 | frontier 系产物路径,与报告宽度逐层可审计 |

**拒因分布**(产品级,诚实留痕):`not_validated_for_reporting` **5,777**(规则/类比原始卡——Phase B 门禁在真实检索数据上的直接效果)、`in_path_cycle` 52、`unparseable_smiles` 1。来源等级:可报告产物 100% `recorded_reaction`。

**口径声明**:off-model 重放只证明架构与门禁行为,**不是**新版 298/dev 成绩;旧 dev run(封存于原批次)只能按旧 schema 读取,本报告未把旧产物套新排序;11/20 路在无模型下停于 `awaiting_prediction` 属既定语义(竞争 recorded 需模型裁决)。与 Phase A 的 298 数字(116/128/130)仅作基线引用,任何新版 298 分数将另标 `post_hoc_repair_check`。修复前的 off-model 产物(旧字段、无验证引用)已归档为 `reports/ec298/phase_b/dev_off_runs_pre_r1fix/`、`dev_off_export_summary_pre_r1fix.json`、`diagnostics_dev_off_pre_r1fix.json`,不再作为交付证据。

## 8. 复现命令

```bash
# 全仓测试(环境:conda depending43)
python -m pytest tests/ -q

# 新 schema run(合成夹具)
python -m pytest tests/test_phase_b_workflow.py tests/test_report_adjudication.py tests/test_export_v2.py -q

# dev 离线结构诊断(无模型、无金标;新批次根,不触碰原 dev 对照)
python -m pathway_v43 batch plan --split dev --batch-root reports/ec298/phase_b/dev_off_batch
python -m pathway_v43 run --smiles <root_smiles> --run-id dev_off_<route_id> \
    --runs-root reports/ec298/phase_b/dev_off_runs \
    --max-depth 6 --max-expansions 40 --max-frontier-width 3 --model off
python -m pathway_v43 export --run-id dev_off_<route_id> \
    --runs-root reports/ec298/phase_b/dev_off_runs --route-id <route_id>
python scripts/phase_b_offline_diagnostics.py \
    $(ls -d reports/ec298/phase_b/dev_off_runs/dev_off_* | sed 's/^/--run-dir /') \
    --out reports/ec298/phase_b/diagnostics_dev_off.json

# 新鲜度核对(答卷 SHA + 裁决集合指纹)
python -m pathway_v43 export --run-id <run_id> --verify
```

样例(v2 run `dev_off_pb_0324`,6 步):`predictions.jsonl` SHA256 `55fca21f3544bcec37887a09d6f056bb0d0fea294cbe976e17ca823e3339290c`;元数据 `adjudication` 块含 6 个已提交事件引用与裁决聚合哈希;`counts.n_report_only_products=0`(off-model 预期)。20 路逐路线 SHA 见 `dev_off_export_summary.json`。

## 9. 披露:并行 Phase C 遗留与限制

- **并行会话遗留**:实施期间工作树存在另一个 Phase C 会话的未提交改动(`domain/policy.py` 升 `v43-policy-3`/`v43-predpol-2` 并加类比消融键、新增 `services/donor_applicability.py`、`services/atom_tool.py` 修改、`docs/TASK_V43_EC298_PHASE_C.md`)。该会话已被用户中止,改动留在工作树。实施首轮全仓曾有 3 项失败全部由其造成(predpol 版本硬编码与类比路由语义变更),与 Phase B 无关;**R1 复测时该会话中断前已把自己的三处测试改配套,当前全仓 356 passed / 0 failed**。按 Phase B 任务书 §1.5,本实施不清理、不回退其他任务的文件;Phase C 重启或回退时需一并处置。
- **报告宽度=提交宽度(off-model)**:确定性通路无模型 order,`n_report_only=0`;解耦行为(未提交可报告候选、no_event 报告步骤、宽度封顶)由合成夹具覆盖,真实模型行为待真实 dev 对照验证。
- **逐卡验证产物粒度**:未选中卡每卡一份 `cardval.*` 产物;本阶段全部同任务目录,`load_adjudications` 只扫描最终裁决文件名,草稿与逐卡产物不可导出。
- **review 门槛对照**:逐卡资格全部经确定性门禁并留拒因(§8 拒因分布);报告列表与事件/路径严格分离(invariant + 导出对账);rank 来源逐条可追溯(`rank_basis` + `model_order_position`);封存基线零改动;恢复与导出新鲜度可复核(§4/§5);dev 比较同输入清单、无金标泄漏(清单 `gold_fields_excluded`,脚本 `gold_free=true`)。无任何候选仅因出现在检索、模型 order 或引擎 Top-10 就进入报告。


## 10. R1 修复记录(2026-09-28)

首轮独立 review([`EC298_PHASE_B_REVIEW.md`](EC298_PHASE_B_REVIEW.md))判定暂不通过:两项 P1、两项 P2。全部修复,逐项对应:

### P1-1 选中卡资格绕过 → 单一判据 + 三道防线

新增 **`domain/policy.py::recorded_eligibility_reasons`**(完整判据单一事实源:同规范底物 query/reactant 双核、精确挂牌 match_type/source_id/donor_exact_match、条件无冲突;逐项拒因),同一判据贯穿四处:

1. **rank 任务候选筛选**(`services/prediction.py`):此前只查 `kind+condition_fit`,异底物 recorded 卡可进任务被模型选中;现按完整判据筛选,脏卡留在检索产物但不进 PredictionTask;
2. **classify/route**(`domain/policy.py::_usable_recorded`):委托同一判据(保留 kind 显式排除,规则/类比卡不因"无拒因"被误判 usable);
3. **validate_products 门禁**(`validation/gates.py::gate_recorded_eligibility`):选中卡在确定性校验层复验,脏卡全部产物拒绝并留拒因,validation 产物新增 `gates.recorded_eligibility` 块;
4. **裁决层选中卡复验**(`_selected_card_validation_view`):不再硬编码 `card_eligible=True`;资格复验失败 → 零占位 + 拒因 `selected_card_ineligible`,工作流 no_event 终态拒因区分资格失败与产物全拒。

工作流回归(`test_phase_b_workflow.py`):review 的复现场景(两张 usable + 一张 `reactant_identity=CN` 脏卡,模型选脏卡且 order 排第一)现为零提交、零报告该卡、调用账 1+2 次有界重试、状态 awaiting_prediction + `prediction_failed` 拒因、脏卡不在 PredictionTask 候选;`donor_exact_match=false` 变体同样不进任务且正常解耦行为不回退。

### P1-2 验证引用 → 结构化 ref + 读取端 fail-closed 回查

- 选中卡引用 `validation.json`、未选中卡引用 `cardval.<sha16>.json`,统一形状 `validation_ref = {"task_id", "artifact", "payload_sha256"}`(payload SHA 来自落盘信封真实哈希);卡级与产品级记录均携带;
- 不变量新增:可报告条目引用三项字段缺一即 `AdjudicationError`;
- 新增读取端 **`resolve_adjudication_validation_refs`**:每个可报告条目解析到真实验证产物,核信封哈希 = 引用哈希,并逐项核对 evidence_id/位次/raw/cn/accepted;缺失、错指、哈希不符、verdict 翻转全部结构化失败;v2 导出投影对每份裁决强制执行(包成 `LedgerCorrupt`);
- 工作流回归:rank 模式选中+未选中两条引用分别可回查、导出通过;篡改引用 SHA → 导出 fail-closed。

### P2-1 层次混写 → 四层分开命名与计数

卡级字段 `in_model_selection_set` 删除,代之 `selected` / `in_model_order`(+ 既有 `in_task` / `card_eligible`);"在任务中但模型未排序"如实可表达(新夹具:`order` 省略 B → `in_task=true, in_model_order=false`、不升格、拒因 `not_in_model_order_not_promoted`)。诊断脚本 `n_cards_gate_passed` 只按 `card_eligible` 计,新增 `n_in_task/n_in_model_order/n_selected/n_task_not_in_order` 四列;任务候选数与验证通过数各从 prediction_task / 逐卡验证事实源取值。

### P2-2 v2 verify 可绕过 → 按 run schema 强制

`export --verify`:当前 run 裁决 schema 为 v2 时,元数据缺 `adjudication` 指纹块或块内五字段(`schema_version/policy_versions/n_adjudications/payload_hashes_sha256/committed_event_ids`)任一缺失即 `ExportStale`(新鲜度门禁不可选);仅 v1 旧 run 元数据保留无块兼容。失败夹具:删整块、删 `payload_hashes_sha256`、伪造块内 schema 版本、篡改聚合哈希 —— 全部拒绝;恢复完整块后通过。

### 复测与产物状态(2026-09-28)

- **全仓 356 passed / 0 failed**(`OMP_NUM_THREADS=1 python -m pytest tests/ -q`,505s;当前共享工作树,HEAD 仍为 `5c8f284`)。**Phase B 改动范围**(与 Phase C 遗留区分):新增 `src/pathway_v43/services/report_adjudication.py`、`src/pathway_v43/output/export_v3.py`*、`src/pathway_v43/output/score_report.py`*、`src/pathway_v43/adapters/rate_gate.py`*、`src/pathway_v43/batch.py`*、`tests/test_report_adjudication.py`、`tests/test_phase_b_workflow.py`、`tests/test_export_v2.py`、`tests/test_export_v3.py`*、`scripts/phase_b_offline_diagnostics.py`、`configs/phase_b_dev_off.json`、`reports/ec298/phase_b/`;修改 `src/pathway_v43/domain/policy.py`†、`services/prediction.py`、`validation/gates.py`、`workflow/{nodes,routing,graph,state,runner}.py`、`storage/run_identity.py`、`output/report.py`、`storage/run_identity.py`、`configs/prompts/ranker.md`、`tests/wf_helpers.py`(带 * 者为 Phase A/export-dev 阶段已有未提交产物、带 † 者含 Phase C 会话的类比开关改动,Phase B 只增补 `recorded_eligibility_reasons` 并收紧 `_usable_recorded`)。
- dev 20 off-model 全部重跑(R1 修复后代码),20/20 导出 + `--verify` 通过;32/32 最终裁决可报告条目引用回查逐项一致;修复前产物归档(`*_pre_r1fix*`)不作为交付证据。
- review 复现的 `dev_off_pb_0074` 空 `validation_ref` 已随重跑消除(样例:`{"artifact": "validation", "task_id": "T_d6897ce0…", "payload_sha256": "b2ab35e2…"}`)。


### R2 修复记录(2026-09-28,二轮 review)

R2 判定 R1 三项修复已有实证,新增两项 P1、一项 P3。全部修复:

**P1(A) 模型可把原始规则卡选成已提交反应 → rank 可选 ID 限合格 recorded + 裁决层守卫**

- `services/prediction.py` rank 任务候选**删除 predictive 拼接**:候选 = 合格 recorded 卡(`kind` 显式 + 完整资格判据)。规则/类比卡属预测证据,各走 `analogy_edit`/`novel_proposal` 的适用性与编辑流程;它们仍保留在检索产物与裁决审查范围(逐卡记录 + `not_validated_for_reporting` 拒因),只是不进任务、不可被选。
- 第二道守卫(`services/report_adjudication.py::_selected_card_validation_view`):检索层 rule/analog/novel 原始卡**即使被选中**也判 `card_eligible=false`、产物零占位、拒因 `not_validated_for_reporting`;模型提案卡(entry_layer=model_proposal,已过 AtomTool/元素门禁)资格不变。
- 端到端失败夹具(`test_phase_b_workflow.py`):两张合格 recorded + 一张规则卡,模型选规则卡 → 规则卡不在 PredictionTask 候选、引用它的响应 invalid → 有界重试 → 零提交、无 `rule_application` ReactionEvent、账面 awaiting_prediction;裁决层守卫由独立夹具贯通(选中规则卡 → 零占位 + 拒因,干净 recorded 正常占位不连坐)。Phase C 的 `test_forged_analog_card_never_passes_as_usable_recorded` 断言由"类比卡进任务一次"更新为更严的"类比卡不进 rank 任务"(语义收严所致,该测试的本意——伪造卡不得当 usable recorded——不变)。
- 复测:off-model dev 20 不触发 rank(无模型),六层漏斗数字与 R1 后一致;20/20 重导出 + `--verify` 通过(元数据按新指纹约定重写)。

**P1(B) `export --verify` 可绕过 v2 新鲜度检查 → 预期 schema 以 run identity 为准**

- R1 的实现从现存裁决文件推断 schema,删光裁决文件会把 v2 run 伪装成 v1 从而跳过指纹块要求(review 复现:`dev_off_pb_0074` 副本删两份裁决 + 删块 → verified=True)。现改为:`run_identity.json` 的 `adjudication.schema_version` 声明预期 schema;声明为 v2 的 run **无论现存文件多少**,元数据缺指纹块或块内五字段任一缺失即 `ExportStale`;指纹比较同样失配即过期。
- **合法空裁决集合的明确校验**:v2 run 全部路径停待预测时零裁决属合法状态,指纹块按 identity 预期 schema 记 `schema_version=v43-report-adjudication-2, n_adjudications=0`,聚合哈希确定可复算;删光文件必然与导出时指纹失配。此前空集合 run 的指纹块误标 v1,已随重导出修正。
- 组合删除夹具(`test_export_v2.py`):v2 run 删光裁决文件 + 删指纹块 → 过期;只删文件留块 → 指纹失配过期;空裁决 v2 run 导出/verify 通过、事后追加裁决 → 过期。真旧 v1 run(身份无 adjudication 声明)保留 R1 起明确的历史兼容:verify 无裁决门禁,但其"事件缺裁决"损坏由重导出投影兜底 `LedgerCorrupt`(不静默重导)—— 该边界已在测试中注明。

**P3 文档未同步** — 报告 §2 数据字典的 `in_model_selection_set` 残留已改为 `selected` / `in_model_order` / `in_task` / `card_eligible` 四层独立表达。

**复测口径(R2 后,2026-09-28)**:全仓 `OMP_NUM_THREADS=1 python -m pytest tests/ -q` 结果见本轮交付说明;dev 20 off-model 重导出 20/20、verify 20/20 通过;32/32 可报告条目引用回查不变。R2 后新增/更新测试:Phase B 侧 rank 限源、裁决层守卫、组合删除、空集合共 4 项 + Phase C 旧断言语义更新 1 处。


### R3 修复记录(2026-09-28,三轮审核)

三轮确认 R2 三项关闭(规则卡 rank 场景独立复现零事件零裁决;删裁决文件的 verify 双路径均过期;11 个空裁决 run 正确标 v2;32/32 引用回查一致)。新增两项修复:

**P2 裁决 schema 与 run identity 不一致仍可导出 → 一致性核对门禁**

新增 `export_v3.check_adjudication_schema_identity(run_dir, identity)`,**导出与 verify 都调用**:

- 身份声明 v2 而实际非空裁决集合为 v1 → `LedgerCorrupt`(review 复现场景;schema 分派决定用哪套投影,但分派结果不得与身份声明矛盾 —— 身份声明的预期 schema 是一致性核对基准,不是投影选择器);
- 反向组合:v2 裁决文件 + 无身份声明的旧式身份 → `LedgerCorrupt`(v2 只由写入 identity 块的新代码产生,无声明 + v2 = 拼装 run);
- 身份声明 v2 + 空裁决集合 = 合法状态,继续放行(指纹按预期 schema 记 v2/n=0);无声明旧 run + v1 裁决 = 历史兼容,放行。

测试(`test_export_v2.py`):v2 身份配完整 v1 裁决 + 已提交事件 → 导出与 verify 都拒绝(verify 腿同步元数据身份指纹以越过外层身份门禁,直达 schema 核对);无声明身份配 v2 裁决 → 导出拒绝 + 核对函数直测拒绝;无声明 + v1 历史兼容不回归。顺带修复一处调用缺陷:一致性核对后向投影分派器显式传实际 schema(此前传裁决不传 schema 会误落 v1 投影)。

**P3 守卫视图布尔字段与拒因不一致** — `_selected_card_validation_view` 的检索层规则/类比卡拒升格分支:`not_validated_for_reporting` 布尔从硬编码 `false` 改为与 `card_reasons` 同源(`raw_predictive`),逐卡诊断不再被误导;零报告结果不变。

**复测(R3 后,2026-09-28)**:Phase B 全套件 + 相邻套件(report_adjudication 20、phase_b_workflow 15、export_v2 17、export_v3 18、score_report、state_isolation,及 Phase C 守卫测试与 batch_dev 崩溃恢复各 1)**77 passed / 0 failed**。同日的全仓运行收集到 387 项、2 项瞬时失败(`test_batch_dev` 崩溃恢复、`test_phase_c_workflow` 守卫),两者**单跑均通过** —— 时间戳显示重启的并行 Phase C 会话在全仓运行期间仍在改树(其测试文件 11:25/11:36 落盘),属共享树移动目标,非 Phase B 回归;Phase B 改动在本次全仓运行中的全部自有用例通过。dev 20 off-model 导出物不受影响(身份与裁决 schema 一致,20/20 verified 维持)。
