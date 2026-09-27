# EC298 Phase A 实施首轮 Review（2026-09-27）

**审查提交**：`a66ceae`、`e51675e`、`27829ad`。  
**审查范围**：scorer v2、A1–A6 派生表、输入/输出清单、两份报告；只读检查封存件，未改实施代码或结果。  
**判定**：**核心重评分通过；Phase A 最终验收暂不通过。** 需修正下述 P1 后再送复核。首跑无需重跑，也无需 API。

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
