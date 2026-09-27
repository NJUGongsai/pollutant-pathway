# v4.3 第五阶段:ENZYMECAGE 298 题单步外考报告(Phase A 同口径重评分与归因补全版)

> 任务书:`docs/TASK_V43_EC298.md`;Phase A 修订:`docs/TASK_V43_EC298_PHASE_A.md`(依据老师 2026-09-27 归因要求与独立复核 [`EC298_REVIEW_R2.md`](EC298_REVIEW_R2.md))。执行环境:Chenyu `/usrdata/EnzymeCAGE_data/workspaces/dependingv43_dev`(独立工作区,未触碰 v4/v4.1/v4.2 任何 runs);原始日志与逐题产物保留在远端 `runs/ec298_v43r1/`。
>
> **判分器版本**:正式数字全部出自 `pathway_v43.exam_v2`(**v43-ec298-scorer-2**,零 LLM、零网络):两臂统一从原始候选 SMILES 计算 `cn_identity`,引擎臂显式忽略缓存 `product_identity`。scorer-1(`exam.score_exam`)与其结果原样保留供审计;其引擎身份口径不对称,数字**不得**再外传。Phase A 产物与对账见 `reports/ec298/phase_a_v2/`,展开报告见 [`EC298_PHASE_A_REPORT.md`](EC298_PHASE_A_REPORT.md)。
>
> v1 报告快照:`reports/ec298/phase_a_v2/ec298_report_v1_snapshot.md`(SHA256 `ca17f674a69df8c8c180a90b22f4a5c2dff3409fb891bb93a6b76c4760e5764d`)。

## 0. 结论(修正口径)

**在同一份 298 题、同一底物提取、两臂同函数 `cn` 身份判分下,v4.3 agent 相对新引擎基线在全部主对照 K 上净落后:hit@1 −2、hit@3 −46、hit@5 −63 题。** 两臂在同一 K 上不存在 agent 领先的档位(@10 亦为 130 对 209);@10 列受输出宽度上限影响,不构成性能声明。

| 指标(分母恒 298) | v4.3 agent | 引擎基线(Top-10) | 净差(agent − engine) |
|---|---|---|---|
| hit@1 | **116 (38.9%)** | 118 (39.6%) | **−2 (−0.7 pp)** |
| hit@3 | **128 (43.0%)** | 174 (58.4%) | −46 (−15.4 pp) |
| hit@5 | **130 (43.6%)** | 193 (64.8%) | **−63 (−21.1 pp)** |
| hit@10(辅助列) | 130\* | 209 (70.1%) | −79\* |

\* v4.3 每步最多报告五个产物,hit@10 恒等于 hit@5,是**输出宽度上限**,不代表第 6–10 位性能。

### 勘误(对 v1 快照报告的错误断言,逐一标注)

1. **"agent hit@1 +34(+11.4 pp)"不成立**:来自 scorer-1 的引擎身份不对称——agent 臂从原始 SMILES 现算 `cn_identity`,引擎臂却直接用缓存 `product_identity`(可能保留电荷)对已经 `cn` 归一化的金标。同口径重评后引擎 hit@1 为 118,净差 **−2**。
2. **引擎 82/117/135/153 不成立**:v2 口径为 **118/174/193/209**。逐题对账:引擎首命中 rank 变化 **68 题**(56 题为新命中、12 题为 rank 移位、0 题丢失),见 `phase_a_v2/score_v1_v2_diff.tsv`;agent 侧 rank 298/298 不变,验证仅引擎口径被修正。
3. **"完整候选池三档 153/0/145"不成立**:`_engine_chunk` 只调用 `top_k=10`,`pool_identities` 仅由返回的十条填充,从未代表完整池。v2 只保留两档:**209 题金标在已导出 Top-10 内,89 题未在已导出 Top-10 命中**;89 题不得称为"完整池真空"(Top-10 外是否存在引擎候选未知),本阶段亦未重跑引擎补档。
4. **"hit@5 −5"不成立**:v2 口径逐题配对净差 **−63**(engine-only 82 题、agent-only 19 题)。
5. 上述旧数字仅可作为"历史错误口径"审计线索在 Phase A 报告中引用,不得用于任何对外结论、表格分母或验收。

## 1. 冻结身份与预核验(先于任何答卷)

| 项 | 值 |
|---|---|
| 题卷 CSV SHA256 | `a3cb7955c1b9e9c1ae0d70636e9df057a35fc35f311f683835de4f19a02ffd0a`(独立重算一致) |
| questions.jsonl(298 行) | `9f5955d418c2f387…9211c`;用旧 `build_ec298_questions.py` 从冻结 CSV **重新生成并逐字节一致** |
| 运行侧白名单 | `exam_inputs.jsonl` sha256 `cb5996c9…f11d703`,仅 qid/substrate_smiles/input_index 三字段,298 qid 唯一;金标字段隔离由 `load_exam_inputs` 结构化校验 |
| exam_identity.json | 冻结于发车前(`frozen_before_answers`);执行批次身份 **`1328faf97261390e`**,另记录冻结版 `4233adaa`(差异仅为 exam.py 的 Path 参数机械修复被身份机制察觉,见 v2 reissue note) |
| 引擎/资产 | 冻结 V43Engine + 资产 21/21;引擎臂逐题携带 `asset_identity` |
| 模型 | `ZHIPU/GLM-5.3-Flash`(DashScope 北京按量,OpenAI 兼容入口),request_params=`{"reasoning_effort":"max"}`,无 temperature,timeout=900s |
| 预算 | max_depth=1,max_expansions=1(单步);max_llm_calls=3/题;批级 max_calls=900(实发 191);**max_in_flight=40** |

dev 配置选择依据:复核轮 r2(300s)→r3(900s)证实 300s 超时造成成批模型调用失败(见 `EXPORT_DEV_REPORT_ADDENDUM.md` §A);属基础设施参数修正,非调分。

## 2. 两臂执行

**引擎臂(先行,零模型费用)**:40 进程分片并行,298/298 全部成功(`n_empty_or_failed=0`),每题保存有序 Top-10 及其身份表(注意:`pool_identities` 仅由 Top-10 返回值填充,**不是完整候选池**),结果 sha256 `c6b9156f…ab205bc8f`。

**agent 臂(首跑,一次冻结配置)**:40 个独立题目 worker(补位式,首批 40 题同时启动),`OMP_NUM_THREADS=1`/worker,共享 FileRateGate(RPM 180/TPM 2.7M/批 900 调用/在途上限 40),持久 API 闸门与账目;无 nohup 中断、无重启、无 post-hoc 重跑。

- 停止原因:completed 247 / awaiting_prediction 50 / budget_exhausted 1;
- 答卷:full 247 + empty 51,**298 行且 qid 唯一**,无漏题无重复;失败/空答计入分母;
- 真实模型调用 191 次(186 次提供方 200 正常,5 次失败),**0 次 429、0 孤儿请求**(Phase A 逐题复核同值,见 `phase_a_v2/llm_call_distribution.tsv`);
- 用量(186 个 usage 记录):输入 739,114 / 输出 1,815,743(其中思考 1,675,450,按输出计费);按官方价目估算 known-usage 部分约 **¥5.7**,5 次失败调用无 usage → 批级总费用按纪律标 `unknown`;
- 需模型的题目先本地检索/备妥再发起请求;已知反应(recorded 证据)不经模型直接完成。

**40 在途验收:实测峰值 33 个提供方正常响应同时在途**(以请求发出/响应结束的单调时间戳重叠计算,每请求含 request_id/HTTP status/usage;限流拒绝与失败不计入)。未达 40,如实标注**该项未完全通过**:补位机制下 298 题中大量题目无需模型,自然并发未触顶;未用伪请求或重复请求凑数。

## 3. 判分与 Top-10 诊断(v2 口径)

- 判分在全部原始答卷封存后打开金标(`ec298_gold_readonly/`,只读);`cn` = v3 `eawag_lookup._cn_identity` 同口径(电荷归一化、立体盲);金标任一含碳产物命中即取首个命中 rank;不可解析/重复候选不计新排名,但**占名次**。
- **scorer-2 与 scorer-1 的唯一主差异**:引擎臂忽略缓存 `product_identity`,从每条 Top-10 的原始 `product_smiles` 现算同一身份;计分单位仍为整条候选字符串,排名/空答/去重/金标提取/298 分母规则不变。
- **多组分敏感性(探索性,非主结果)**:18 条 agent 候选含 `.`(引擎侧 34 条);按"任一组分命中"两臂同法重评,agent @1/@3/@5 = 129/141/143,引擎 = 132/184/199;不与主分数混算,正式组分口径变更须另立 scorer 版本(见 `phase_a_v2/multicomponent_sensitivity.tsv`)。
- **Top-10 两档(判分后诊断,不送回模型;不是完整池分档)**:

| 档 | 新引擎(本卷,v2 口径) | agent 命中(@1/@3/@5) |
|---|---|---|
| 金标在已导出 Top-10 内 | 209 | 111 / 114 / 114 |
| 未在已导出 Top-10 命中 | 89 | 5 / 14 / 16 |

  89 题档中 agent 命中的 16 题全部来自 `novel_proposal` 模式,其来源已逐题回查(见 `phase_a_v2/agent_hits_by_engine_tier.tsv`);Top-10 外是否存在引擎候选未知,不得称"真正无证据泛化"或完整池真空。
- 历史对照(v4.1 首跑判分件,另一引擎/资产):engine @1/@3/@5 = 118/172/190(其封存判分文件仅记录 ≤5 的 baseline_rank,@10=208 引用历史 v4.1 报告),逐题首命中 rank 与新引擎有 **24 题**不同——汇总接近**不能宣称版本等价**;v4.1 agent 118/179/190 属另一 agent 配置,不与本卷混算。所谓"82 对 118 因资产域偏移"的前提(engine 82)在 v2 口径下不存在。
- v1 判分器对拍记录(历史):以 scorer-1 对历史 v4.1 有序预测重算 agent_rank 298 match / 0 diff;该结论只涉及 agent 臂,v2 口径下 agent rank 同样 298/298 不变。

## 4. 失败与恢复

- 单 worker 无硬杀/无重启;协调器日志 respawn=0、failure-status=0(已核实);
- 5 次模型调用失败(超时/传输类),对应题目按显式拒因停留/空答,全部计入分母;
- 封存:逐题 `status.json`(298)、归并 `merged/predictions.jsonl`(sha256 `68efc082e4cfadc0…`)、`batch_identity.json`、`exam_identity.json` 均先于判分落盘;评分 JSON、原始答卷、金标、引擎池各有 SHA。

## 5. 披露与限定(必随数字外传)

1. 题卷 RHEA/BRENDA/EnzymeMap 来源与检索语料的潜在重叠:**Phase A 已完成本卷资产库 `library_full` 的部分 membership 扫描**(182/298 底物身份重叠、113/298 底物-金标产物对重叠,描述性统计,见 `phase_a_v2/asset_exam_overlap.tsv`);其它检索资产(uspto/envipath 规则、类比索引)、历史 v4.1 语料的 membership 与真实泄漏风险**未完整审计**(旧库状态 `not_assessed`)。
2. 本卷是**单步**酶促污染物转化外考,不能证明多步环境 pathway 的整体准确率;v3 dev 多步指标(hit@1 0.2512 等,见 `EXPORT_DEV_REPORT_ADDENDUM.md`)另行呈现,**未与本卷 hit@K 合并**。
3. hit@10 的 agent 值是输出宽度上限,不是排名性能;两臂 @5 名义上限相同,故 **−63 的 @5 净差不能解释为"五位 vs 十位"的宽度不对称**(rank 9–10 本就不计入引擎 @5);agent 实际只报 1 个候选的题有 197 题,"有效宽度不足"才是宽度侧事实。K=10 列才有五位与十位的不对称。
4. 首跑答卷未因分数做任何修改;score=0 的 51 题空答全部保留在分母与逐题表中(命运闭环见 `phase_a_v2/awaiting_prediction_fates.tsv`)。
5. 在途峰值 33 < 40,该项未完全通过(见 §2);账号限额与需模型题数均未构成硬阻塞,差异来自补位调度下模型请求的自然稀疏性。
6. 资产重叠统计(`phase_a_v2/asset_exam_overlap.tsv`)是描述统计,不能单凭它证明性能差异的因果来源;规则覆盖 `not_assessed`。

## 6. 产物索引

- 本仓(首跑 v1 判分,仅对账用):`reports/ec298/{per_question_scoring,exam_identity,agent_batch_identity,agent_merge_metadata,engine_arm_metadata,agent_run_summary}.json`
- 本仓(Phase A v2,正式口径):`reports/ec298/phase_a_v2/`(正式逐题评分 `score_v2.json`、score_v1_v2_diff、multicomponent_sensitivity、agent_hits_by_engine_tier、awaiting_prediction_fates、decision_path_contribution、hit5_paired_attribution、llm_call_distribution、v41_baseline_diff、asset_exam_overlap、input_manifest、anchor_reconciliation、输出 SHA 清单、v1 报告快照、R1 review 前产物快照 `r1_snapshot/`;数据字典见 [`EC298_PHASE_A_REPORT.md`](EC298_PHASE_A_REPORT.md))
- 远端(原始):`runs/ec298_v43r1/{exam_inputs.jsonl,exam_identity.json,engine_arm/,agent_batch/,agent_runs/,scoring/}`;dev 两轮在 `runs/devbatch_v43r2|r3/`;金标只读 `ec298_gold_readonly/`
- 零网络复算分两步(路径显式传入,无凭证入仓;**输入清单绝不重建**,封存输入变化会使复算失败而非被接受):
  1. 一次性初始化(仅在核验过的封存副本上,清单已存在时拒绝):`python scripts/ec298_phase_a.py --run-dir <封存 run 目录> --gold <金标> --v1-scoring <v1 评分> --v41-baseline <v4.1 判分件> --asset-library assets/v3_reactions/library/library_full.jsonl --out-dir <输出目录> --init-input-manifest`
  2. 正常复算(同上去掉 `--init-input-manifest`):逐文件校验完整文件集合与 SHA——少文件、多文件、改任一字节或换资产库都立即失败;亦可单用 `PYTHONPATH=src python -m pathway_v43.exam_v2 --agent-predictions <封存>/agent_batch/merged/predictions.jsonl --engine-results <封存>/engine_arm/engine_results.jsonl --gold <金标>/questions.jsonl --out-dir <输出目录>`(其 score_v2.json 记录三输入 SHA)
