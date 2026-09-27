# v4.3 第五阶段:ENZYMECAGE 298 题单步外考报告

> 任务书:`docs/TASK_V43_EC298.md`。执行环境:Chenyu `/usrdata/EnzymeCAGE_data/workspaces/dependingv43_dev`(独立工作区,未触碰 v4/v4.1/v4.2 任何 runs);原始日志与逐题产物保留在远端 `runs/ec298_v43r1/`。判分器:`pathway_v43.exam.score_exam`(v43-ec298-scorer-1,零 LLM)。

## 0. 结论

**在同一份 298 题、同一底物提取与同一 `cn` 身份判分下,v4.3 agent 相对新引擎基线:hit@1 多答对 34 题(+11.4 个百分点),hit@3 多 11 题(+3.7 pp),hit@5 少 5 题(−1.7 pp)。**

| 指标(分母恒 298) | v4.3 agent | 引擎基线(Top-10) | 净增减 |
|---|---|---|---|
| hit@1 | **116 (38.9%)** | 82 (27.5%) | **+34 (+11.4 pp)** |
| hit@3 | **128 (43.0%)** | 117 (39.3%) | +11 (+3.7 pp) |
| hit@5 | **130 (43.6%)** | 135 (45.3%) | −5 (−1.7 pp) |
| hit@10(辅助列) | 130\* | 153 (51.3%) | −23 (−7.7 pp)\* |

\* v4.3 每步最多报告五个产物,hit@10 恒等于 hit@5,是**输出宽度上限**,不代表第 6–10 位性能;与引擎 Top-10 的 K=10 对比不构成性能声明。

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

**引擎臂(先行,零模型费用)**:40 进程分片并行,298/298 全部成功(`n_empty_or_failed=0`),每题有序 Top-10 + 完整候选池身份表,结果 sha256 `c6b9156f…ab205bc8f`。

**agent 臂(首跑,一次冻结配置)**:40 个独立题目 worker(补位式,首批 40 题同时启动),`OMP_NUM_THREADS=1`/worker,共享 FileRateGate(RPM 180/TPM 2.7M/批 900 调用/在途上限 40),持久 API 闸门与账目;无 nohup 中断、无重启、无 post-hoc 重跑。

- 停止原因:completed 247 / awaiting_prediction 50 / budget_exhausted 1;
- 答卷:full 247 + empty 51,**298 行且 qid 唯一**,无漏题无重复;失败/空答计入分母;
- 真实模型调用 191 次(186 次提供方 200 正常,5 次失败),**0 次 429、0 孤儿请求**;
- 用量(186 个 usage 记录):输入 739,114 / 输出 1,815,743(其中思考 1,675,450,按输出计费);按官方价目估算 known-usage 部分约 **¥5.7**,5 次失败调用无 usage → 批级总费用按纪律标 `unknown`;
- 需模型的题目先本地检索/备妥再发起请求;已知反应(recorded 证据)不经模型直接完成。

**40 在途验收:实测峰值 33 个提供方正常响应同时在途**(以请求发出/响应结束的单调时间戳重叠计算,每请求含 request_id/HTTP status/usage;限流拒绝与失败不计入)。未达 40,如实标注**该项未完全通过**:补位机制下 298 题中大量题目无需模型,自然并发未触顶;未用伪请求或重复请求凑数。

## 3. 判分与三档诊断

- 判分在全部原始答卷封存后打开金标(`ec298_gold_readonly/`,只读);`cn` = v3 `eawag_lookup._cn_identity` 同口径(电荷归一化、立体盲);金标任一含碳产物命中即取首个命中 rank;不可解析/重复候选不计新排名。
- **逐题配对净增减**(agent − engine):hit@1 +34、hit@3 +11、hit@5 −5、hit@10 −23(宽度上限)。
- **判分器对拍**:以本评分器对历史 v4.1 首跑 298 题有序预测逐题重算 `agent_rank`,与历史 `per_question_scoring.jsonl` 的 298 行**逐题一致(298 match / 0 diff)**,无需要解释的差异;旧 scorer 不存在,本评分器即只读复现器。
- 引擎完整候选池三档(判分后诊断,不送回模型):

| 档 | 新引擎(本卷) | 历史 v4.1 档(锚点,另一引擎/资产) |
|---|---|---|
| Top-10 已含金标 | 153 | 208 |
| 池内 Top-10 外 | **0** | 51 |
| 池内无金标 | 145 | 39 |

  两档分布不可比:新引擎(v4.3 资产)排序/池构成不同,Top-10 外候选从未含金标;历史 208/51/39 为 v4.1 首跑锚点,仅标注来源、不作预期值。
- 历史锚点(v4.1 首跑判分件):agent 118/179/190,engine 118/172/190——**另一引擎、另一 agent 配置,不与本卷数字混算**;本卷 agent hit@1 116 vs 历史 118 属不同口径,不构成退化声明。

## 4. 失败与恢复

- 单 worker 无硬杀/无重启;协调器日志 respawn=0、failure-status=0(已核实);
- 5 次模型调用失败(超时/传输类),对应题目按显式拒因停留/空答,全部计入分母;
- 封存:逐题 `status.json`(298)、归并 `merged/predictions.jsonl`(sha256 `68efc082e4cfadc0…`)、`batch_identity.json`、`exam_identity.json` 均先于判分落盘;评分 JSON、原始答卷、金标、引擎池各有 SHA。

## 5. 披露与限定(必随数字外传)

1. 题卷 RHEA/BRENDA/EnzymeMap 来源与 v4.3 检索语料的潜在重叠**未经单独审计**;本外考不排除检索资产与题目事实同源带来的有利偏差。
2. 本卷是**单步**酶促污染物转化外考,不能证明多步环境 pathway 的整体准确率;v3 dev 多步指标(hit@1 0.2512 等,见 `EXPORT_DEV_REPORT_ADDENDUM.md`)另行呈现,**未与本卷 hit@K 合并**。
3. hit@10 的 agent 值是输出宽度上限,不是排名性能;引擎 K=10 优于 agent 是宽度差异而非质量差异,K=1/3/5 主对照不受影响。
4. 首跑答卷未因分数做任何修改;score=0 的 51 题空答全部保留在分母与逐题表中(见 `per_question_scoring.json`)。
5. 在途峰值 33 < 40,该项未完全通过(见 §2);账号限额与需模型题数均未构成硬阻塞,差异来自补位调度下模型请求的自然稀疏性。

## 6. 产物索引

- 本仓:`reports/ec298/{per_question_scoring,exam_identity,agent_batch_identity,agent_merge_metadata,engine_arm_metadata,agent_run_summary}.json`
- 远端(原始):`runs/ec298_v43r1/{exam_inputs.jsonl,exam_identity.json,engine_arm/,agent_batch/,agent_runs/,scoring/}`;dev 两轮在 `runs/devbatch_v43r2|r3/`;金标只读 `ec298_gold_readonly/`
- 复算命令(远端,凭证脱敏):`OMP_NUM_THREADS=1 .venv/bin/python -m pathway_v43 score --predictions runs/ec298_v43r1/agent_batch/merged/predictions.jsonl --out-dir … --v3-code-root …`(dev 判分)与 `python /tmp/ec298_seal_score.py`(外考判分,见仓库 review 记录)
