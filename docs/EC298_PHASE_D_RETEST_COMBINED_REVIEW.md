# EC298 Phase D 复测与 Chenyu 原始 run 综合 Review

> Review 日期：2026-09-29。对象：[Phase D 复测报告](EC298_PHASE_D_RETEST_REPORT.md) v2、[原始 run 审计报告](EC298_PHASE_D_RETEST_RAW_RUN_AUDIT_REPORT.md)及其脱敏证据。本文是**当前修复清单**；用户此前粘贴的四项审计 v1 review 意见已由审计 v2 补件解决，不再作为待修故障重复派单。审计总判定保持 `contradictory`，范围见下文。
>
> **状态：resolved（2026-09-29）**——F1/F2 已消除（§6 关账核验），K1/K2 口径已明确并写入代码/报告/测试；主分数、配对、费用、峰值数字不变。

## 1. 当前结论

**原始运行、配对和主分数可接受；报告与派生在途表尚需勘误。**Chenyu 两臂原始文件的身份、298 题终态、187 次调用、usage、报告产物来源、离线计分和配对四格均与复测报告主数字一致。`pairing_gate: complete` 表示两臂数据可合法配对；原始 run 审计的 `contradictory` 指两处旧派生/报告主张与原始事实冲突，**不等同于配对门失败或主分数被推翻**。复测报告页首的整体 `complete` 暂不宜解释为“所有证据与措辞均无待修项”。

| 主指标，分母 298 | C0 | D-3 | D-3 − C0 |
|---|---:|---:|---:|
| hit@1 | 136 | 132 | −4 |
| hit@3 | 182 | 174 | −8 |
| hit@5 | 186 | 182 | −4 |

@5 配对四格 `both/C0_only/D3_only/neither = 178/8/4/108`，D-3 赢/输/平 `4/8/286`。这是**已见 298 题、冻结配置、单次模型抽样**的观察差异，不能单独定量归因于 D1，也不证明独立集增益；`reactant_similar_enabled` 发布默认继续为 `false`。

## 2. Chenyu 原始事实与复测报告交叉核对

远端原始臂为 `/usrdata/EnzymeCAGE_data/workspaces/dependingv43/runs/ec298_pd_retest_{C0,D3}/`；本仓脱敏证据位于 [`reports/phase_d/retest/raw_run_audit/`](../reports/phase_d/retest/raw_run_audit/)。审计脚本 [`audit_raw_run_v2.py`](../reports/phase_d/retest/raw_run_audit/audit_raw_run_v2.py) 与远端同 SHA `b96a051a…`；[`OUTPUT_SHA256.txt`](../reports/phase_d/retest/raw_run_audit/OUTPUT_SHA256.txt) 所列 44 项均通过本地校验。v1 审计脚本的来源读取错误已明确封存作废，以 v2 结果为准。

| 核对项 | Chenyu 原始证据结论 | Review 判定 |
|---|---|---|
| 冻结身份 | 两臂配置 38 键、批次身份 58 键，均只差 `reactant_similar_enabled=false/true`；白名单、题卷、引擎、merged、seal 锚一致；实际 50 个代码文件和 22 个资产文件重算聚合 SHA 一致 | 通过；远端非 Git 工作区，不能用远端 HEAD 替代文件身份 |
| 完成性 | 各 298 个 run，C0 `286 success + 12 legal_stop`，D-3 `285 + 13`；无缺题、异常失败、导出失败；归并各 298 唯一 qid，报告宽度 ≤5 | 通过，`pairing_gate: complete` 有原始终态支撑 |
| 请求与费用 | 各 187 个唯一 request_id、187 ok、0 失败/429/孤儿，usage 187/187；**185 题×1 + 1 题×2 = 187**，另 112 题零调用；C0 ¥4.8911、D-3 ¥5.2016，烟测另计 ¥0.0761 | 原始事实通过；服务商账单回填仍是独立费用门 |
| 产物来源 | 从 `report_adjudication.json` 的 `payload.products[reportable]` 重建，首位 C0 `286/286`、D-3 `285/285`；全部报告位 `762/762`、`740/740`，零不匹配 | 通过；逐位表见 `v2_source_positions_{C0,D3}.tsv` |
| 评分与配对 | 原始 merged 重新计算的 298×2 rank 与 `score_v2` 零差异，hit@1/3/5 与 @5 四格同上 | 通过；主分数无需因 F1/F2 重算 |
| 并发 | 原始响应区间两臂各 187 条；先发与先完两种同时间戳排序的峰值均为 C0 `33`、D-3 `32` | 数字通过；时间戳与区间端点术语待勘误 |
| 封存与隔离 | 两臂 seal 各 309 文件清单重算文本/SHA 一致，官方 601 文件扫描零违规；补充扫描遍历 C0 46,751、D-3 47,408 个文件，对可解码文本全文检查，旗标 291/290，均解释为 seal 自身词表或合法 `products_smiles` 键名，无值级标记/严格凭证命中 | 在报告所列扫描口径内通过；不推断题卷与语料无重叠 |
| 只读性 | 两臂审计前后逐文件清单 `changed/added/removed=[]`；审计新输出在独立目录 | 通过；后续复现仍须使用独立输出目录 |

隔离范围说明：全文本扫描无法把 SQLite 当作 UTF-8 文本解析。此次 review 另对两臂各 596 个 SQLite 文件按同组路径/凭证标记做只读字节检查，零命中；这不是对载荷语义或题卷与语料重叠的审计结论。

## 3. 仍待修的冲突与勘误

| 编号 | 优先级 | 现状与最小反例 | 影响 |
|---|---|---|---|
| **F1：在途表 attempt 错标** | P1 | [`ec298_pd_retest_inflight.py`](../scripts/ec298_pd_retest_inflight.py) 以 `(run_id, task_id)` 存 attempt，第二次响应覆盖第一次。C0 的 `RXNG_16560019…`、D-3 的 `RXNG_7701b699…` 在原始 `prediction_response.a1/a2.json` 和 API 调用表中为 `1/2`，旧 `*_inflight_events.tsv` 两行却均为 `2`。 | 逐请求证据列不可信；请求时间、request_id、峰值和主分数未见受影响。 |
| **F2：调用分布表述与算式** | P1 | [复测报告 §3](EC298_PHASE_D_RETEST_REPORT.md) 将 C0 的 187 次解释为“186 题各 1 次 + 1 题 2 次”（其和实际为 188）；D-3 写“分布与 C0 逐题相同”，但二次尝试 qid 分别是 `RXNG_16560019…` 与 `RXNG_7701b699…`。实际两臂均为 `185×1+1×2=187`，零调用的 112 题集合相同。 | 报告事实描述错误；187 次调用及费用数字仍成立。 |
| **K1：时钟术语** | P2 | [复测报告 §9](EC298_PHASE_D_RETEST_REPORT.md)及 [`llm_client.py`](../src/pathway_v43/adapters/llm_client.py) 注释称 sent/done 为“单调时间戳”；实现使用 `time.time()` 记录 epoch 墙钟，只有 `elapsed_s` 使用 `time.monotonic()` 差值。 | 术语错误；本轮无异常时长，峰值数字未变。 |
| **K2：同时间戳事件顺序** | P2 | [`exam.inflight_evidence`](../src/pathway_v43/exam.py) 采用同一时间先发后完；半开区间 `[sent,done)` 应先完后发。本轮两种排序均得 `33/32`。 | 历史数字未变；未来复核口径需固定。 |

## 4. 修复顺序与验收

1. **修 F1**：逐个 `prediction_response.aN.json` 读取自己的 `payload.attempt`，并以文件名 `aN`、request_id 交叉核对；禁止按 task 最后一次 attempt 回填所有请求。把原两张在途表留历史副本，在版本化的新输出中重导，再更新报告索引。验收：每臂 187 行、187 唯一 request_id、两次尝试题为 `1/2`、其余行不变，峰值仍 `33/32`。
2. **修 F2**：复测报告 §3 同时改算式和 D-3 “逐题相同”措辞，明确两臂二次尝试 qid 不同。验收：`185×1+1×2=187`、`185+1+112=298` 与 [`v2_call_arith_C0.json`](../reports/phase_d/retest/raw_run_audit/v2_call_arith_C0.json)、[`v2_call_arith_D3.json`](../reports/phase_d/retest/raw_run_audit/v2_call_arith_D3.json) 和原始逐调用表一致；不要只改 D-3 栏而保留 C0 的错误算式。
3. **修 K1/K2**：把 sent/done 明称 epoch 墙钟、`elapsed_s` 明称单调时钟差。并发端点选定一种口径并写入代码/报告；若改为半开区间，加入“两个区间在边界相接”反例测试，重算本轮峰值仍须为 `33/32`。若沿用先发后完，也要把报告表述改为实际实现口径。
4. **关账与封存**：在新版本派生表及报告上复核 298×2 rank、hits、@1/@3/@5 四格、来源 762/740、费用与输出 SHA 未变；仅在 F1/F2 消除、K1/K2 口径明确后，将综合 review 标为 `resolved`。服务商账单费用门另记，不混作本次修复通过条件。

本轮**不需要重新发模型请求或重跑原始 run**。修复对象是派生脚本、派生表及报告/注释；不得修改 Chenyu 原始臂、金标、批次身份、既有评分口径或默认策略。

## 6. 关账核验（resolved 依据，2026-09-29）

- **F1 验收**：现表各 187 行、187 唯一 request_id；C0 `RXNG_16560019…`、D-3 `RXNG_7701b699…` 为 attempt `1/2`；与旧表逐格比对每臂仅改 1 格（a1 行 attempt 2→1）；文件名交叉核对 0 不匹配、request_id 重复 0；峰值 C0 33/D-3 32（peaks_match=true）。旧表留 `reports/phase_d/retest/inflight_v1_superseded/`（含 README 说明），现表 schema `ec298-pd-retest-inflight-2`。
- **F2 验收**：复测报告 §3 已为 `185×1+1×2=187`（C0 二次尝试 `RXNG_16560019…`、D-3 `RXNG_7701b699…`，112 零调用集合相同），与 `v2_call_arith_{C0,D3}.json` 及原始逐调用表一致。
- **K1/K2 验收**：`llm_client.py` 注释改称 epoch 墙钟/`elapsed_s` 单调时钟差；`exam.inflight_evidence` 改半开区间先完后发并同步文档/`note`；新增 `tests/test_exam.py::test_inflight_peak_half_open_boundary_touching`（边界相接反例，本地 10/10 通过）；固定函数在本轮 187×2 真实区间上重算仍为 33/32。
- **不变性**：298×2 rank、hits、四格、赢/输/平、来源 762/762 与 740/740、费用三数、引擎/归并/seal SHA 均未变；`scoring/`、`C0/`、`D3/`、`*_api_calls.tsv` 零改写（本时段内仅 4 张新在途表 + README 落盘）。
- **部署披露**：`exam.py`/`llm_client.py` 已同步至 Chenyu 工作区（两地逐字节一致），远端代码聚合现为 `538a5bc6…`（50 文件）；冻结锚 `07fef84f…` 仍指两臂运行时刻验收字节。服务商账单费用门另记。

## 5. 旧 review 意见的当前状态

用户粘贴的早期四项审计 review 指向审计 v1，现已由 v2 补件覆盖：①来源误读顶层 `products` → v2 读取 `payload.products` 并交付逐位表；②只读复现命令写旧目录 → 改用独立目录、seal 改只读复核；③隔离 601 口径之外缺判别 → 新增全文本扫描和逐文件上下文，同时保留语料重叠限制；④算式及代码/资产 SHA 证据不足 → 审计报告与 v2 算式、实际文件聚合已更正。**这些是审计工具和审计报告的已修历史，不应与当前 F1/F2 混同。**
