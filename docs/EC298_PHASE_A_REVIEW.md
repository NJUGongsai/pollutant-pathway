# EC298 Phase A 实施 Review（2026-09-27）

> 本文保留前两轮发现作为修复记录；**最新判定见文末 R3 复核**。

**审查提交**：`a66ceae`、`e51675e`、`27829ad`。  
**审查范围**：scorer v2、A1–A6 派生表、输入/输出清单、两份报告；只读检查封存件，未改实施代码或结果。  
**R1 当时判定**：**核心重评分通过；Phase A 最终验收暂不通过。** 下述 P1 已在 R2 修复复核。首跑无需重跑，也无需 API。

## 已独立核实

- 用提交中的 scorer v2 在 Chenyu 封存首跑上重新执行：agent @1/@3/@5 = **116/128/130**；引擎 @1/@3/@5/@10 = **118/174/193/209**；Top-10 两档 **209/89**；v1→v2 引擎 rank 变化 **68**，agent **0**。多组分探索性数字也与报告一致。
- `reports/ec298/phase_a_v2/output_manifest.sha256` 的 **17/17** 条目通过逐文件 SHA256 检查；`input_manifest.json` 指向的封存输入 **4,663 个清单条目**均与本地镜像匹配（其中 v1 评分文件既在 run 目录内又单列一次，故不同物理文件为 4,662 个）。
- 在 Chenyu 的 RDKit/pytest 环境中对提交源码运行 `test_exam_v2.py` 和 `test_phase_a_attribution.py`：**16 passed**。本地默认 Python 缺 RDKit/pytest，因此测试在临时目录执行，没有改封存 run。
- 独立扫描封存账本：agent/引擎/白名单均为 **298 行、298 个不同 qid**；模型调用分布 **0:112、1:182、2:3、3:1**，191 call、191 response、186 成功/5 失败；以**完整相对路径和 attempt**配对时 orphan 仍为 **0**。这支持当前批次的调用结论。

## P1-1：正式 `score_v2.json` 未交付

Phase A 任务书 §2 要求版本化的逐题正式评分文件，产物树也明确列出 `score_v2.json`。[`scripts/ec298_phase_a.py`](../scripts/ec298_phase_a.py) 调用 `score_exam_v2(...)` 时未传 `out_path`，只将结果留在内存；已提交的 `phase_a_v2/` 目录及输出 SHA 清单均无 `score_v2.json`。独立 `python -m pathway_v43.exam_v2` 入口能生成该文件，但这不能替代本次已归档的交付。

**影响**：报告中的正式逐题分数没有独立的版本化、带哈希主产物；读者只能从各张 TSV 反推。**修复**：总脚本写入 `phase_a_v2/score_v2.json`，将 scorer 版本、输入 SHA、逐题 rank、汇总和配对四分一并封存；更新数据字典与输出清单，验证该文件同各 TSV 的 298 qid 和 rank 逐题一致。

## P1-2：A4 的“主因”标签把检索存在误写成可报告能力

[`phase_a_attribution.py`](../src/pathway_v43/phase_a_attribution.py) 的 `attribute_discordant` 把“任意原始检索卡含金标”直接归为“候选检出但未报告”。在 57 条此标签的 engine-only 题中，**22 条**有未选中含金标 recorded 卡，另 **35 条**仅由 `retrieval_gold_any_card=true` 触发；后 35 条并未证明该卡通过结构门禁、满足条件、进入模型任务或可报告。报告据此断言“82/82 原始检索视图含金标，所以损失不在检索覆盖率”，把**原始检索覆盖**外推成**可用候选覆盖**，会误导下一阶段修复优先级。

同一函数在 `candidates and selected` 且**没有查到未选中含金标 recorded 卡**时，把 5 题判为“模型选错”；这恰恰没有证明任务候选中存在正确选项。19 条 agent-only 又统一标“候选未检出”，但其中 **14 条**的 agent 原始检索卡含金标；该标签若仅指“引擎已导出 Top-10 未命中”，须写全限定对象。

**修复**：把事实分层列为 `raw_retrieval_gold`、`task_candidate_gold`、`validated_reportable_gold`、`selected_gold`、`reported_gold`，每层给来源与验证引用；仅在存在正确且可选的任务候选、模型却选错时标“模型选错”。没有门禁证据的 35 条使用“原始检索含金标，是否可用未证实”或 `证据不足以判断`。报告 §0/§7 撤回 57/5/19 作为确定性根因的表述；82/82 只可描述为**原始检索产物重叠**。

## P1-3：输入封存校验可以被复算命令绕过

[`ec298_phase_a.py`](../scripts/ec298_phase_a.py) 在 `--write-input-manifest` **或清单缺失**时直接重建 `input_manifest.json`，随后再“验证”新清单；主报告 §6 给出的复算命令又含 `--write-input-manifest`。因此输入若先变化，该命令会接受变化后的 SHA，和报告“输入缺失或 SHA 不符即失败”不符。`verify_input_manifest` 还只核已有条目，不核 run 目录是否多出会被解析的文件。资产重叠使用的 `library_full.jsonl` SHA 出现在结果摘要中，却未作为输入清单的受保护角色。

**修复**：把首次建清单设为独立显式初始化，已有清单时严禁覆盖；正常复算缺清单或 SHA 不符即失败。校验 run 目录的**完整文件集合**与逐文件 SHA；将实际使用的资产库列入清单。修订报告命令，不带重建清单标志。对“改一个输入字节”“添一个会被扫描的结果文件”“换资产库”加入失败测试。

## P2：审计实现和报告文字需收紧

1. [`_call_response_ledger`](../src/pathway_v43/phase_a_attribution.py) 用**文件名**而非所在 task 目录和 `payload.attempt` 配对 call/response。同一 run 的两个任务若都存在 `a1`，可能互相抵消 orphan。本次我用完整相对路径独立核到 **0 orphan**，所以不推翻当前数字；仍应修配对键和测试。
2. [`score_exam_v2`](../src/pathway_v43/exam_v2.py) 只校验答卷行数等于金标题数，未拒绝重复 qid 或检查引擎 qid 集合。当前封存件三臂实际均 298 个唯一 qid，主分数不受影响；作为可复用 scorer 应 fail-closed。
3. [`EC298_REPORT.md`](EC298_REPORT.md) §0 写“agent 的相对优势只出现在输出宽度的下游”，但 @10 仍是 **130 对 209**，没有相对优势。§5 又写“语料潜在重叠未经单独审计”，与 Phase A 已做 `library_full` 的 **182/298 底物重叠、113/298 底物-金标对重叠**相冲突。应改为“已完成该库的部分 membership 扫描；其它检索资产、历史语料与真实泄漏风险未完整审计”。老师建议的新旧两套语料 membership 只完成了新库，旧库状态也应明确写出。
4. `input_manifest.json` 是 **4,663 条角色条目 / 4,662 个不同物理文件**；报告数据字典写“4,662 项”容易误读，明确两种计数即可。

## 复核门槛

请保留本次 17 个文件及哈希作为 R1 快照；在新的修复提交中补齐 `score_v2.json`，重生成 A4/报告/清单，不触碰首跑封存件，不调用 API。复核时我会检查：逐题正式评分与 TSV 一致；A4 标签有资格证据支撑且不能从原始检索直接推出“可报告”；输入更改和文件集合变化均使复算失败；全文不再出现无依据的“模型选错”“候选未检出”或 @10 优势声明。

---

## R2 复核（提交 `e6543f1`）：数据通过，工程签收待两处 P2

**验收结论**：R1 的三项 P1 已闭环；Phase A **数据结果通过**，可作为后续架构修复的离线基线。两处 P2 防护尚未完全实现，工程全项签收待补。正式分数仍为 agent 116/128/130、引擎 118/174/193/209，@5 配对 both/agent-only/engine-only/neither = 111/19/82/86。无需重跑 298 题或调用 API。

### 三项阻断门槛逐项判定

1. **正式评分：通过。** 新增的 `reports/ec298/phase_a_v2/score_v2.json` 有 scorer 版本、三份核心输入 SHA、298 个唯一 qid、逐题 rank 和配对四分。独立计算输入 SHA 均匹配封存镜像；与 `score_v1_v2_diff`、多组分敏感性、A1、A3 逐题明细、A4 及两个筛选视图、v4.1 对照这八类 TSV 的适用 rank 列逐题比对，**零差异**。提交的输出 SHA 清单通过；R1 快照的 18 个文件与修复前提交 `27829ad` 逐字节一致。
2. **A4 归因：通过。** 82 条 engine-only 中，22 条标“模型选错”的题全属于 `rank_candidates`，均有 `task_candidate_gold=true`、非空含金标 recorded 卡引用、`selected_gold=false` 和模型排序；40 条改为“证据不足以判断”（原始检索层 35 + 无正确任务候选 5），14 条类比弃答、6 条编辑拒绝。19 条 agent-only 的标签限定为“引擎已导出 Top-10 未检出”，其中 14 条原始检索含金标只列事实。报告已把 82/82 限定为**未经门禁的原始检索产物重叠**。
3. **清单防绕过：通过。** 清单现有 `run_dir/gold/v1_scoring/v41_baseline/asset_library` 五个角色，4,664 条角色记录；正常复算缺清单即失败，`--init-input-manifest` 遇已有清单即拒绝。验证器检查 run 目录完整文件集合和逐字节 SHA，资产库也受保护。相关 8 个失败/成功测试通过；主报告命令已区分一次性初始化与正常复算。

### 独立验证与剩余说明

- 在 Chenyu 临时目录运行提交源码的相关测试：**28 passed**（scorer、归因、清单脚本）。这是我独立重跑的范围；用户报告的全仓 260 项未在本轮独立复跑。
- 在 Chenyu 用原始封存 run、只读金标、历史对照、资产库和提交的输入清单重新执行 Phase A 管线：**42/42 锚点通过**。`score_v2.json`、A1/A2/A3/A4/A6 主表、资产重叠、v1-v2 差异及多组分敏感性等关键产物与已提交版本 SHA 一致；封存 run 的文件集合及 SHA 均被清单接受。外层输出清单 **35/35** 项校验通过。
- 独立以完整 task 相对路径、文件名 attempt 与 `payload.attempt` 对拍封存调用/响应，得到 **191/191 成对、0 orphan**。实现已将 task 目录纳入配对键，主报告 @10 与资产披露也已勘误。
- **非阻断文案精度**：`EC298_PHASE_A_REPORT.md` 称“脚本回读 `score_v2.json` 与各 TSV 逐题对账”。脚本确实回读了 JSON 并与内存评分对账，但没有在写盘后重新读取所有 TSV；本轮 review 已独立对八类含 rank 的 TSV 做逐题对账。建议将报告改为“脚本回读正式评分并与内存结果对账；TSV 由同一结果生成，review 另行逐题核对”，以免把人工复核说成自动门禁。该措辞不影响本批数据与 Phase A 验收。

### 两处尚未闭环的 P2 防护

1. **Orphan 键只核文件名 attempt，未核 `payload.attempt`。** [`_call_response_ledger`](../src/pathway_v43/phase_a_attribution.py) 的键是 `(task 相对目录, 文件名 stem)`；未读取 call/response payload 中的 `attempt`。同目录的 `call.a1` 与 `response.a1` 若 payload 分别写 2 与 1，当前实现仍计为成对。封存首跑的 191 对我已独立核到文件名/payload 一致，因此当前 **0 orphan 正确**；请让实现对两侧 payload 与文件名逐条校验，并补一个 payload 错配夹具。
2. **scorer 的空引擎文件仍可静默计分。** [`score_exam_v2`](../src/pathway_v43/exam_v2.py) 仅在 `engine` 非空时检查其 qid 集合；显式传入一个存在但零行的引擎结果文件时，会把所有题记为引擎未命中，不报集合不一致。正式 Phase A 管线的输入清单保护了本次非空封存文件，当前分数不受影响；但 standalone scorer 声称 fail-closed，应在显式指定引擎文件时要求其 qid 集合与金标完全一致，包括空文件，并加测试。

---

## R3 复核（提交 `5c8f284`）：Phase A 通过

**最终判定**：R2 剩余两处 P2 已闭环，Phase A 可作为后续阶段 B/C 的**离线基线**。正式分数、逐题评分和 A4 归因不变；本轮不涉及模型调用、引擎/agent 重跑或首跑答卷改写。

1. **调用审计：通过。** `_call_response_ledger` 现以完整 task 目录和 `payload.attempt` 配对，并把 payload 与文件名 `aN` 不一致逐条计入 `attempt_mismatch_count`；错配 call/response 不会互相抵消。新增夹具的 `call.a1` payload attempt=2 / `response.a1` payload attempt=1 得 **错配 1、orphan 2**。封存首跑的 191 call、191 response 我再次独立核对：382 个文件均带 attempt，文件名/payload **0 错配**、全路径配对 **0 orphan**；A2/A6 与新增锚点均为 0。
2. **空引擎拒绝：通过。** 显式引擎路径缺失或文件零行时 `_engine_rows` 抛 `ScorerV2Error`；`score_exam_v2`、多组分敏感性和差异表共用此入口。新增测试覆盖缺文件、空文件及敏感性入口；`None` 仍是明确的无引擎臂模式。
3. **产物与复算：通过。** 在 Chenyu 临时目录独立运行本轮相关测试 **32 passed**；用原始封存 run、只读金标、历史对照、资产库和受保护清单执行 Phase A 管线，**43/43 锚点通过**。`score_v2.json`、A2 两表、A6 表、A4 表与提交版 SHA 逐文件一致；提交的外层输出清单亦全部通过。用户所报全仓 **264 passed** 未在本轮独立复跑。

**非阻断门禁范围说明**：`verify_score_v2_against_tsvs` 现在会回读并核对六张**全量逐题**含 rank 的 TSV，解决了 R2 的主要文案问题；`hit5_engine_only.tsv`、`hit5_agent_only.tsv` 两张筛选视图和 `awaiting_prediction_fates.tsv` 的 rank 列未纳入该自动门禁。其代码只验表行数与每行 rank，没有显式拒绝重复 qid 导致的等量缺题；本次提交的所有这些表我已独立核对 qid/取值，当前数据无误。建议将报告的“全部含 rank 的 TSV”改称“六张全量逐题 TSV”，并在后续维护中对筛选视图、qid 集合加断言。`payload.attempt` 缺失时审计器会回退文件名；本次封存 382 个调用/响应文件均无缺失，当前 0 错配结论不受影响。
