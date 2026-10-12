# 任务书 T3：chain12 评测器离线重跑基建 + 43 partial 三拆 + 自由基扫描（2026-10-12）

> 主会话起草，交实施子代理。零上下文可接。
> 上游：CC 拍板 T3（37→43 partial 细分，口径不变）+ mimo r35 P1 建议（superset/partial_subset/身份差异三拆）与 M5 watch item（自由基扫描）+ 验证记录 docs/MIMO_R35_EXEC_VERIFY_2026-10-12.md。

## 0. 一句话目标

建一个**评测器离线重跑基建**（复用仓内判分代码，不重写判据），对 chain12 全 298 题重跑拿到**逐事件匹配明细**（判分时只进内存不落盘的部分），基于它产出 **43 道 partial 的三拆细分表**与**自由基扫描**，全部零 LLM 零网络，判分口径零改动。

## 1. 数据与代码位置

| 项 | 路径 | 说明 |
|---|---|---|
| chain12 逐题 payload | `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/synced/runs/<run_id>/native_export/<case>/payload.json` | 298 个全量事实投影 |
| chain12 判分结果 | `…chain12_s5b_298_v4b_20261012/metrics.json` | per_qid 桶与 rank（对齐自检用） |
| 金标参考图 | `reports/ppv1_s5b/s5b_298_local/reference_graphs/` | **本地已有、gitignored**；同题卷（QSHA 一致，对账报告核过）。qid 内容寻址 RXNG_*，与 chain12 可对齐 |
| 判分代码 | `src/pathway_v43/pollutant/s5b_scoring.py:184-322`（score_s5b_batch）、`evaluation.py:2147`（evaluate_scientific） | **复用调用，不得修改**；逐题入口从 s5b_scoring 读 run/case → read_native_export → evaluate_scientific 的链路照抄 |

mimo r35 指出的细分字段（evaluation.py:1046-1107 已实现、判分时只进内存）：`predicted_edge_matches[].coverage_mismatch_events[]`（每事件 participant_coverage ∈ {superset, partial_subset}、coproduct_participants）、`required_node_gaps[]`（node_id/side/node_match_status）。

## 2. 三步走

### 2.1 基建：评测器重跑（全 298 题）

- 新脚本 `scripts/s5b_offline_rescore.py`：对每 qid 组装判分输入（payload + 参考图，复用 s5b_scoring 的读取/构建函数），调 evaluate_scientific，把**逐事件匹配明细**（含上述 coverage_mismatch_events/required_node_gaps/每事件严格命中位次）落 `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/rescore_detail.json`。
- **对齐自检门（必须过才算基建可用）**：重跑出的题级桶（strict/partial/uncovered）与 metrics.json per_qid 逐题对比；一致率与不一致清单如实报告（可能来源：本地判分代码版本与判分批次版本差、金标参考图构建差异）。一致率 <100% 时不硬对齐，如实披露并分析差异题；若三桶大量不一致（>5 题），停下报告版本差异原因再继续。
- 记录 provenance：本地 HEAD、payload 内版本串（s5b_scoring_version 等）、参考图 QSHA。

### 2.2 43 partial 三拆（mimo P1 分类）

对 metrics 桶=partial 的 43 题，按重跑明细归三类（每题一类，可注明复合）：

| 类 | 判据 |
|---|---|
| superset（诚实多写） | 存在 coverage_mismatch_events ∈ superset（事件参与物多于参考），典型 D2/coproduct 类 |
| partial_subset（缺必要物种） | 存在 ∈ partial_subset（缺参考要求的参与物） |
| 身份差异 | 无覆盖失配但 required_node_gaps 非空/身份匹配失败（互变异构·立体·状态表示） |

产出：三拆计数表 + 逐题 qid 清单 + 每题摘要行（事件数/失配事件数/缺失节点数）。与对账报告 §6 的 D2 双刃预期交叉（13 道 declared_copy_components 题应主要落 superset——核对并报告）。

### 2.3 自由基扫描（mimo M2 #1 / M5 watch item）

对 43 partial 题 + 全部 rank2-5 候选事件（T6 相关面）扫描事件产物的 `NumRadicalElectrons>0`：RDKit 解析产物 SMILES（payload events/states 的 smiles），计数阳性事件并抽样列出（qid+state+radical 原子）。**只披露不做门**（mimo：先披露后评估，防过拒）。strict 命中事件因身份相等天然干净，可只做对照抽样（可选）。

## 3. 红线

1. **判分口径零改动**：evaluation.py/s5b_scoring.py 只读复用；发现疑似 bug 停下报告不顺手修。
2. **金标纪律**：reference_graphs 只在判分进程内消费；不复制出 reports/、不把金标结构/内容写进任何 docs/ 或最终消息（统计计数可以）。
3. 零 LLM 零网络；synced/ 只读；产出落 analysis/（gitignored）与 /tmp/s5b_t3_rescore/；脚本新文件入 scripts/ 不碰既有。
4. 数字诚实：重跑对齐率、三拆类间复合、自由基阳性数原样报告；不确定标 unknown。
5. 不 commit 不 push。题域标签 298/RHEA 已见题写进输出头。

## 4. 排障表

| 症状 | 处置 |
|---|---|
| evaluate_scientific 输入形态与预期不符 | 以 s5b_scoring.py 实际调用链为准照抄构建，不自行拼输入 |
| 重跑桶与 metrics 不齐 | 逐题 diff 找模式（版本/随机性/参考图差异）；≤5 题如实披露继续，>5 题停下报告 |
| 参考图 qid 对不上 chain12 | 用 metrics per_qid run_id↔qid 映射回查；仍不齐停下报告（不得改参考图） |
| RDKit 解析产物失败 | 计数解析失败并单列，不跳过不猜 |

## 5. 回传义务

1. 脚本用法一行 + provenance（HEAD/版本串/QSHA）；2. 对齐自检结果（一致率+不一致清单与归因）；3. 三拆计数表+qid 清单+与 D2 指纹交叉核对结果；4. 自由基扫描计数+抽样；5. known limits；6. 产出文件路径。最终消息按此六项，不贴大段 JSON、不贴金标内容。
