# v4.3 第五阶段任务书：ENZYMECAGE 298 题单步外考

> 交给独立执行模型在 Chenyu 实施；本会话负责 review。**本文件是准备任务书，不是开考命令。**发车前先完成 `docs/TASK_V43_EXPORT_DEV.md` 的 dev 实跑与 review，并冻结 v4.3 配置。旧 v4 题卷协议见 `/Volumes/CC/Enzyme_Agent/dependingv4-fix/evaluation/enzymecage_v6/TASK_298.md`；远端通道和历史产物见 `docs/CHENYU_ACCESS.md`。旧任务书涉及 v4/P6 的路径、代码与预算不能直接当作 v4.3 实现。

## 0. 测试问题与口径

298 题是**单步**微生物酶促污染物转化的外部题卷。要回答的是：在**同一份 298 题、同一底物提取和同一 `cn` 身份判分**下，v4.3 的有序产物比本仓冻结引擎直接预测多答对多少题。它不同于 v3 pathway benchmark 的 dev 20 / eval 100 多步路线指标；两类分数不得混算。

主指标为含碳产物集合匹配的 **hit@1、hit@3、hit@5**（分母始终 298），另报每题首个命中 rank、失败数、模型调用/费用和墙钟时间。历史协议还报 hit@10；v4.3 每步最多报告五个产物，故 v4.3 的 hit@10 必然等于 hit@5，必须注明这是输出宽度上限，不能据此声称第 6–10 位性能。引擎基线同时报 Top-5 与 Top-10；与 v4.3 的主对照只用相同 K=1/3/5。

## 1. 发车前冻结与核验

1. `TASK_V43_EXPORT_DEV.md` 的工程与 20 路真实模型 dev 结果已 review；其中新增的**已校验可报告 top-5 与实际展开分离**契约必须通过。不能把 ReactionFinder 的原始 `top5_candidates` 直接导出为 agent 答卷，也不能只取已展开主线而漏掉已接纳未展开的候选。
2. 基于 dev 结果选择一份配置，锁定代码/资产/提示词/模型/映射策略、报告候选排序、预算、最大输出 token、推理参数与导出/判分版本，生成 `exam_identity.json`（不含密钥）。本卷只允许题意所需的统一覆盖：`max_depth=1`、`max_expansions=1`；另明确冻结考卷调度参数 `exam_worker_count=40`、`max_in_flight_api_requests=40`。`max_frontier_width`、`max_llm_calls`、`max_proposals`、每题墙钟、账号实际 RPM/TPM 限额与 batch 总费用上限在**看到 298 分数前**固定。模型仍为 dev 使用的 DashScope 按量 `ZHIPU/GLM-5.3-Flash`；统一读取远端受限 env 文件，不换模型或端点。
3. 本地冻结 CSV 位于 `/Volumes/CC/Enzyme_Agent/dependingv4/evaluation/enzymecage_v6/ENZYMECAGE_POLLUTANT_REACTION_TEST_298_FINAL_V6_PAYLOAD_2026-09-21/ENZYMECAGE_POLLUTANT_REACTION_TEST_298_FINAL_V6_PROVISIONAL_2026-09-21.csv`，独立重算 SHA256 必须是 `a3cb7955c1b9e9c1ae0d70636e9df057a35fc35f311f683835de4f19a02ffd0a`。本地 `/Volumes/CC/Enzyme_Agent/dependingv4/runs/enzymecage298/questions.jsonl` 已核到 298 行；用旧 `scripts/build_ec298_questions.py` 对源卷重新生成并按字节/逐题核对，不临场改底物/产物提取规则。原始 payload 与题目金标只读、untracked，不放进 v4.3 代码仓或模型任务。
4. Chenyu `dependingv4_v41` 的历史 agent/engine run 和 `per_question_scoring.jsonl` 只读；**2026-09-25 实查该目录下旧任务书所写 `runs/enzymecage298/questions.jsonl` 和 `scripts/score_ec298.py` 均不存在**，不能照旧路径硬启动。实施者须从上述本地冻结源和实际存在的提取脚本/历史评分事实重建独立的 v4.3 评测输入与 scorer，并核验远端 SHA/298 行。旧 `per_question_scoring.jsonl` 的 298 行可作 scorer 对拍，不作预测输入。

## 2. 隔离题目与判分答案

由冻结 `questions.jsonl` 一次性生成**运行侧白名单** `exam_inputs.jsonl`，每行仅有 `qid`、`substrate_smiles` 和输入索引；不能携带 `products_smiles`、`raw_reaction`、`category`、来源、金标标签或历史命中信息。核对 298 个 qid 唯一、与原卷顺序/底物一致，并记录原卷 SHA、提取脚本 SHA、白名单 SHA。v4.3 的 PredictionTask、检索请求、LLM prompt、run_identity 中不能出现答案字段。判分进程只在全部原始答卷封存后打开含答案的文件；评测零 LLM。

原始答卷和金标分开存放。每题一个稳定 run_id 和独立 SQLite/results 目录，`qid` 不靠 `rsplit('_')` 从目录名推断（旧工程曾因此出现全零误判）；合并只读白名单里的显式 qid 映射。任何缺题、重复题、异常停止、超时或无有效产物，都保留一行空/部分预测并纳入 298 分母，不能剔除困难题。

## 3. 引擎基线与 agent 首跑

**引擎臂先行，零模型费用。** 使用 v4.3 已校验 assets 与冻结 `V43Engine`，同一 `exam_inputs.jsonl` 逐题调用一次单步预测，保存原始候选、稳定身份、来源、排名及引擎/资产 SHA；输出有序 Top-10。此臂应与旧 v4.1 同卷引擎结果逐题对照，但旧卷数字不是新臂的替代品；差异按引擎、资产或排序版本解释。不得用引擎对金标的命中结果调整 agent 路由或提示词。

**agent 臂只跑一次冻结配置。** 先在非 298 夹具上验证单步预算、top-5、GLM 响应解析、限流/断点恢复、评分器及 40 并发调度；若用 298 前几题检查部署健康，其预测即属于正式首跑，不能在看到分数后修改并重跑。将 dev 已验证的 Chenyu 协调器扩至 **40 个独立题目 worker**：首批 40 题同时启动，结束一题便按冻结 qid 顺序补位，直至 298 题全部处理；每 worker `OMP_NUM_THREADS=1`、独立账本与日志，共享持久 API 限流/费用闸门。通过 `nohup` 等分离方式保活，SSH 只短连接查看状态。远端密钥只从 `/usrdata/EnzymeCAGE_data/workspaces/.dependingv43-dashscope.env` 读取，不复制到 run/报告。

**40 个 worker 还须落实为 40 次真实 API 调用同时在途。** 对需要模型的不同 qid，先完成各自本地检索与任务准备，再通过发车屏障放行 40 个真实请求；全批同时在途请求上限也设为 40，空出的请求槽由后续需模型的题目补位。以请求发出、响应结束的单调时钟时间戳计算重叠数，并保存请求 ID、qid、HTTP 状态和用量；验收峰值须达到 **40 个得到提供方正常响应的请求同时在途**，限流拒绝、连接失败和本地排队不计入达标峰值。单纯看到 40 个进程不算达标。发车前核对账号当时允许的并发、RPM/TPM 与费用额度，令共享闸门在这些限额内放行；限额不足时记录实际峰值和原因，不通过伪请求、重复请求或绕过闸门凑数，也不声称已达到 40 并发。已知反应无需模型的题目仍按原证据策略直接完成，不为并发数字强迫调用模型。

从每题**已校验且策略接纳的可报告候选**导出最多五个按 `report_rank` 排列的产物，并记录 `evidence_id`、验证引用、是否展开、模型响应引用；未入账的原始检索卡和被拒提案不得补位。`max_depth=1` 后不再预测第二步。考卷耗时或费用上限触发时停止新 API 请求，保留已有部分答卷与额度账，不因失分而换模型、扩大候选池或改参数。

完成/失败恢复以同一 `exam_identity` 和 task 幂等键执行；已落盘响应不重复调用，悬空 issued 请求按既有 orphan 审计并计入调用预算。基础设施中断的原样恢复不算新尝试；代码/策略/模型变更后的运行必须使用新的明确标为 **post-hoc** 的 run 标签，不能覆盖首跑答卷。先封存 `agent_results.jsonl`、逐题 run identity 与 SHA，再启动 scorer。

## 4. 冻结评分器与研究报告

对 298 题使用旧 `TASK_298.md` 的评分定义：对每题 `products_smiles` 金标集合，按 v3 `eawag_lookup._cn_identity` 的电荷归一化、立体盲身份比较有序候选，任一含碳金标产物命中即得该题首个命中 rank。不得用原始字符串比较；金标多组件、离子/中性差异、重复候选、解析失败和 K=1/3/5/10 边界均有合成单测。若旧 scorer 找不到，在 v4.3 写只读复现器，先用历史 `per_question_scoring.jsonl` 对拍 298 个 `agent_rank/baseline_rank`，解释任何差异；不得为对齐期望分数而改金标。主报告只读取封存答案和预测。

报告至少包括：引擎与 v4.3 agent 的 hit@1/3/5 命中数、百分比及**逐题配对净增减**；hit@10 只作标注输出宽度的辅助列；逐题 qid、类别、金标数、两臂 rank、模型/证据来源、拒因、LLM 次数、token、费用与耗时。另按**新引擎的完整候选池**在判分后分成“Top-10 已含金标 / 池内 Top-10 外 / 池内无金标”三档，并与历史 208/51/39 档及旧 v4.1 首跑数字分开标明来源。三档只用于事后诊断，不送回模型。历史 v4.1 的 298 行首跑判分件实查 agent hit@1/3/5 为 118/179/190，引擎为 118/172/190；这是历史锚，不当作 v4.3 预期值。

结论明确写「v4.3 相对同卷新引擎多/少答对 X 题（Y 个百分点）」，同时披露：题卷 RHEA/BRENDA/EnzymeMap 来源与检索语料的潜在重叠未经单独审计；外考是**单步**酶促污染物转化，不能证明多步环境 pathway 的整体准确率。v3 多步 eval 数字另表呈现，不与本卷 hit@K 合并。不要用外考结果反调 v4.3 后再把新分数当首跑。

## 5. 验收与交付

1. 冻结 CSV SHA、提取产物、298 白名单与输入/金标隔离均独立复核；检查模型任务和日志无答案字段/密钥。
2. 单步预算、可报告 top-5 与 frontier 分离通过夹具和真实 run 检查；298 个 qid 均有唯一 agent 与引擎答卷，失败题计入分母。
3. 40-worker 池和 **40 个不同题目真实 API 请求同时在途**有时间戳与请求状态证据；共享 DashScope 速率/费用账、掉线和硬杀恢复有持久证据，真实 `ZHIPU/GLM-5.3-Flash` 的模型 ID、usage 和请求状态逐题可查。若账号限额或实际需模型题数不允许达到 40，报告实测峰值并将此项标为未通过，不改题目路由凑并发。
4. 判分器对历史首跑判分件逐题一致或差异有完整解释；新卷主结果为 hit@1/3/5 同 K 对照，三档、成本和失败归因可重算。
5. 原始首跑答卷、金标、引擎池、评分结果及报告各自有 SHA；旧 v4/v4.1/v4.2 runs 一字不改，298 的新产物落 v4.3 专用 run/tag。总报告写在 `docs/EC298_REPORT.md`，远端原始日志与逐题产物保留在 `runs/`。

review 硬门槛：**冻结身份先于答卷；金标不进 agent；40 题并行且 40 次真实 API 调用同时在途有证据；单步额度不超；top-5 是已校验的预测而非原始检索；298 全量无漏题；同卷、同 K、同身份口径比较；首跑不可因分数改写。** 不满足时如实标为“未完成外考”，不要报一个删题后的命中率。
