# 新旧架构对比：v4.3 EC298 考试系统 vs pollutant_pathway_v1（PPV1）

日期：2026-10-09。用途：给老板/同事讲解的对比材料。本文主文用大白话，
技术细节收在附录 A/B/C。无金标、无题面、无密钥内容。

一句话总结：**老系统（v4.3 EC298）是"检索 + 大模型预测"的答题管线，
模型直接给候选答案；新系统（PPV1）是"化学审计驱动的假设搜索系统"，
模型只提假设，每一步化学编辑都要过审计关，判分更严但每一步都有据可
查。新系统不是推倒重来——同一个模型、同一份 298 题卷，换了心脏
（判定逻辑），保留了血管（模型通道、题目、工程纪律）。**

---

## 1. 一句话定位

- **老系统（v4.3 EC298 考试系统）**：一条"检索 + LLM 预测"管线。先从
  冻结的反应语料里检索相似反应（检索就是"在书架上找长得像的先例"），
  找到就直接抄或让模型裁决排序；找不到就让模型照着相似先例类比改写，
  或凭空提案。最后每题产出排好序的前五个候选产物，机器判分。
  入口：`docs/TASK_V43_EC298.md`、`src/pathway_v43/exam.py`。

- **新系统（PPV1，pollutant_pathway_v1）**：一个"化学审计驱动的假设
  搜索系统"（假设 = 一个待验证的化学反应猜想）。模型只能提假设，不
  能直接产出答案；每个假设要真正执行原子编辑（原子编辑 = 在分子结构
  上按操作改键改原子），然后过化学审计（原子守恒、电荷账、反应中心
  核验、准入裁决四道关），过关的写进账本（账本 = 可审计的数据库记
  录），不过关的如实记 unknown/拒绝，绝不蒙混。最后按"参考图"判分
  （参考图 = 事先冻结的标准答案路径图，判分时才打开）。
  入口：`docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md`、
  `src/pathway_v43/pollutant/`。

## 2. 一图流对比表

| 维度 | 老系统（v4.3 EC298） | 新系统（PPV1） |
|---|---|---|
| 定位 | 检索 + LLM 预测的答题管线 | 化学审计驱动的假设搜索系统 |
| 模型干什么 | 直接产出/裁决候选答案（选已有卡或提案卡） | 只提"假设"（proposals），不碰判分、不碰数据库 |
| 化学把关 | 确定性校验门禁（validate），一次过 | 每步编辑过审计：原子守恒/电荷账/中心核验/准入裁决 R1–R7 |
| 记账 | 路径账本 + 候选卡，报告截断前五 | 独立账本：事件存全部参与物，报告 K 不删事实 |
| 终点判断 | 无（单步题，不做终点） | 四分账：执行状态/停止原因/化学终点/账目闭合分开，停止≠终点、账平≠矿化 |
| 判分 | cn 身份（电荷归一+立体盲，"长得像就算同一个"）+ 任一金标产物命中 | 严格结构身份（原子级同一）+ 参考边全覆盖，双口径同报 |
| 质量关 | 测试 + 人工 phase review | 六阶段正链评审循环、判据冻结成版本、导出确定性+过期识别、25 轮 Codex 复审 P1 清零 |
| 复用件 | —— | 同一模型 GLM-5.3-Flash、同一份 298 题卷、模型客户端/闸门/AtomTool/老判分口径全部只读复用 |
| 298 真跑数字 | 已有（见附录 C） | 尚未发车（预注册 2026-10-09 已确认，真跑待发车） |

## 3. 一道题的旅程（两套各一遍，每步一句）

**老系统：一道 298 题怎么流过去**

1. 白名单：从冻结题卷提取每题的题号和底物分子，答案字段一律不进
   运行侧（`exam.py build_exam_inputs`）。
2. 并行开工：40 个题各起一个独立进程，共享限流闸门（`batch.py`
   BatchCoordinator；40 个真实请求同时在途）。
3. 检索：拿底物去冻结反应语料里找先例（`workflow` retrieve）。
4. 三路分流：检索命中唯一已记录反应 → 直接抄答案不花模型钱；
   命中多条 → 让模型排序裁决；有相似先例 → 类比改写；都没有 →
   模型 novel 提案（`domain/policy.py decide_prediction_route`）。
5. 模型出手：模型给出"选中哪张已有卡"或"提案卡"，经确定性校验
   门禁后入账——模型不能直接改数据库（`workflow/graph.py`）。
6. 出答卷：每题最多导出五个已验证可报告产物，按位次排好。
7. 封存判分：答卷全部封存后才打开金标，机器判分（零 LLM），
   hit@1/3/5，分母恒 298，失败题不剔除。

**新系统：同一道题怎么流过去**

1. 题卷构建：同一份 298 题卷转成每题一个独立 run 的输入 + 一张
   参考图（金标答案只落 gitignored 目录，仓里零金标；
   `pollutant/s5b_builder.py`）。
2. 开卷：给底物建"化学状态"（严格身份 = 原子级指纹）和路径上下文
   （环境条件、依赖），冻结成不可变计划（`pollutant/runflow.py`）。
3. 提候选：模板池（底物侧确定性检索出的候选假设）交给模型，
   模型只做两件事——给池内假设排序，或提 novel 假设（必须自带
   完整反应内容，不许空说）（`pollutant/model_protocol.py`）。
4. 执行编辑：选中的假设交给冻结的原子编辑工具真实执行——真的在
   分子上改，不是嘴上说说（`pollutant/production.py`）。
5. 化学审计：编辑结果过四道关——原子守恒账（元素/电荷分轴）、
   供体一致性诊断（改的地方和声明的编辑对不对）、反应中心核验
   （实际改的原子是不是声称的反应中心）、准入裁决表 R1–R7
   （拒绝/搁置/有条件保留/放行，首中即决）（`pollutant/audit.py`）。
6. 账本记录：过关的事件把全部参与物、系数、共同产物写进独立
   SQLite 账本；不过关的如实留 unknown/partial，不许吞异常装成功
   （`pollutant/store.py`）。
7. 调度循环：队列决定哪些继续展开、哪些挂起（共同产物挂起和备选
   反应挂起分两类），直到预算/深度/无候选而停止（`pollutant/queue.py`）。
8. 终点分账：四本账分开——执行完没完、搜索为啥停、化学终点是
   什么（没证据就是 unknown）、账目闭合没有。停止不冒充终点，
   账平不冒充矿化（`pollutant/endpoint.py`）。
9. 导出：全部事实做确定性导出（同样的事实必然产出同样的字节），
   另给旧格式一个明确标注"有损"的兼容投影（`pollutant/native_export.py`）。
10. 参考图判分：答卷封存后才开金标，零 LLM；主口径 = 参考边召回
    hit@1/3/5，同时附一张老口径对照表；失败题照留 298 分母
    （`pollutant/s5b_scoring.py`）。

## 4. 模型在哪、干什么（核心区别）

- **老**：模型是"答题人"。它直接决定答案长什么样——要么从检索到的
  候选里挑，要么自己写一张新卡。模型输出经确定性校验后就是答卷内容。
- **新**：模型降级成"提假设的人"。它只能交一份假设清单（proposals，
  每条一个独立反应猜想），排序也只能引用池内已有假设的稳定 ID。
  每条假设都要真刀真枪过审计；模型不碰判分、不碰数据库、不碰条件
  事实（`model_protocol.py`：模型不直接写 SQLite/frontier/条件事实）。
  换句话说：**老系统信模型的答案，新系统只信模型的猜想，答案由
  化学规则说了算。**

## 5. 判分：为什么更严反而更可信

- **老的口径**：cn 身份（电荷归一、立体盲——粗略说"电荷抹平、
  手性忽略，骨架一样就算同一个分子"）+ 任一金标产物命中即算
  （答对一个就算这题命中）。宽容但容易把"长得像"当"答对了"。
  出处：`src/pathway_v43/exam.py:22-26`、`exam_v2.py:52-55`。
- **新的口径**：严格结构身份（原子级同一才算同一分子；立体、同位素
  都区分）+ 事件级全覆盖（一条参考边的必要产物节点全部严格命中才算
  matched_strict）。另有两道诚实阀门：未知不许升格（cn 只能当旁证，
  旁证不叠加）；同分不同路（distinct occurrence）不合并。
- **双口径同报**：新系统把老口径（scorer-2 官方整串 any-one）原样
  复刻成"敏感性对照表"，新旧数字可以并排看，不能各说各话
  （`s5b_scoring.py:17-24` 复用 `exam_v2.first_hit_rank` 只读不重写）。
- **为什么更严更可信**：严的口径下命中更"硬"——命中 = 原子级同一
  + 全覆盖，不含糊；没命中也有账可查（是结构没对上、还是节点没盖
  全、还是预算没展开，分桶单列）。宽口径可以当历史锚，严口径才是
  能拿去下结论的数字。预注册还规定了"更严"只限定命中存在性，
  通过线以老口径历史数字作参照锚、双口径并列报告
  （`docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md` §5）。

## 6. 质量保障差异：新系统多过的质量关

老系统也有质量纪律（判分零 LLM、金标不进运行侧、失败题留分母——
这些新系统全继承了），且有 Phase A–D 的人工评审在案。新系统在这
之上把质量关做成了"硬门"（不过不放行）：

1. **契约身份**：每个对象（状态/假设/事件/账本）都有版本号+内容
   哈希；身份对不上就拒，改一个字都是新版本。
2. **首消费校验**：任何数据第一次被读用时先验身份和内容（防篡改、
   防张冠李戴），"写进去成功"不等于"读出来可信"。
3. **账本 + 审计决策表**：每步编辑的判定理由是机器可读的理由码，
   R1–R7 决策表首中即决，任何 unknown 不自动拒绝也不自动放行。
4. **零 LLM 判分 + 金标隔离**：判分进程无模型调用；含金标产物只能
   落 gitignored 目录，写普通目录直接拒（S5-27）。
5. **导出确定性 + 过期识别**：同样的事实必产出同样的字节；源数据
   变了，旧导出会被识别为过期，不会冒充当前结果。
6. **评审循环**：六个阶段正链（S0–S2 契约 → S3a 搜索底座 → S3b
   生产链 → S4 终点/导出 → S5a 评测器 → S5b 运行时），每一关都走
   "实施 → mimo 化学评审 → Codex 程序复审 → 回修"循环，累计 25 轮
   Codex 复审报告（S0–S2×8、S3a×4、S3b×3、S4×5、S5a×4、S5b×1）
   + 27 轮 mimo 化学评审往来在案（r1–r27），实锤 P1
   问题逐个修复、清零才放行（例如 S5A-05 引用绑定漏洞、S5B-L01
   判分配对错位——后者是 mimo r25 先抓到的 ⚠️P1，修复前同底物两题
   会拿错对方的答卷）。
7. **判据冻结**：化学判定规则冻结成版本 ppv1-criteria-v1
   （2026-10-08），以后改一个字都要升版本、重新评审，不许静默改。

## 7. 继承关系：换了心脏，保留了血管

| 保留的东西 | 说明 |
|---|---|
| 同一个模型 | DashScope 按量 `ZHIPU/GLM-5.3-Flash`，两代同款 |
| 同一份 298 题卷 | 三个 SHA 锚（题卷 CSV/questions.jsonl/白名单）原样沿用，S5b 只读消费 |
| 模型客户端 | `adapters/llm_client.py OpenAICompatibleClient` 整套只读复用（429 退避、付费停止、幂等键、usage 记账），`pollutant/real_model.py` 不重写 |
| 限流闸门 | `adapters/rate_gate.py FileRateGate`（RPM/TPM/在途峰值）批级闸门照用 |
| 原子编辑工具 | 冻结的 `services/atom_tool.py` 照用（production 链只调用不修改） |
| 编排思想 | 40 路 worker、一题一进程、断点续跑、批次身份、失败题留分母——从 `batch.py` 的思路平移到 `s5b_orchestrator.py` |
| 判分口径 | 老口径由 `exam_v2.first_hit_rank` 只读复刻成敏感性对照表 |
| 工程纪律 | 白名单/金标隔离/零 LLM 判分/发车冻结身份——老系统立的规矩全继承 |

新架构的入口分流也是"加分支不改旧路"：`workflow/runner.py` 按
profile 分流，legacy 走原 LangGraph 流程逐字节不变，PPV1 走独立
执行流（`workflow/runner.py:214-228/305-320`，冻结判据 0d.8）。

## 8. 对用户的意义

- **数字更可信**：预注册（开跑前把通过线、分母、口径全部写死，
  赛后不许改——"先定规则再比赛"）；可审计（每题每步有账本和理由
  码，出问题能定位到具体一步）；失败题不剔（298 分母恒定，不存在
  "剔掉难题后的漂亮数字"）；双口径并列（新旧数字能对上话）。
- **以后能干什么（老系统做不到的新能力）**：
  - **条件依赖**：路径记忆环境条件（缺氧/温度/共底物），条件冲突
    会挂起而不是硬答，场景切换可以接续推演；
  - **预算控制**：每题的真实模型调用数、深度、展开宽度全部有上限
    有记账，花在哪一清二楚；
  - **崩溃恢复**：断电/进程被杀后按同一身份幂等续跑，已发出的请求
    不重复计费，坏账本隔离不猜补；
  - **诚实的不确定性**：unknown/partial/deferred 如实保留——系统
    会说"我不知道"，而不是把猜的说成真的。这在老系统里没有对应物
    （老系统只有"答了/没答"）。
- **一句话**：老系统回答"答案对不对"；新系统还回答"为什么、凭什么、
  差在哪、花了多少"。

---

## 附录 A：两套流程的技术细节（模块级对应表）

老架构核心（`src/pathway_v43/`，非 pollutant 部分）：

| 老模块 | 职责 | 新架构里的对应 | 职责变化 |
|---|---|---|---|
| `exam.py`（run_exam_agent/score_exam） | 输入隔离、引擎臂、agent 臂、在途证据、scorer-1 | `pollutant/s5b_builder.py` + `s5b_scoring.py` | 题卷→run 输入+参考图；判分升级为严格结构+双口径 |
| `batch.py`（BatchCoordinator） | 20/40 路进程协调、批次身份、归并、API 账 | `pollutant/s5b_orchestrator.py`/`s5b_worker.py`/`s5b_cli.py` | 同思想平移；run 级+批级双层预算；case 文件终态 |
| `adapters/llm_client.py` | 唯一允许发模型请求的模块（off/fake/real） | `pollutant/real_model.py` | **只读复用**，不重写；加逐调用账本 |
| `adapters/rate_gate.py`（FileRateGate） | 跨进程 RPM/TPM/在途闸门 | 同一文件 | **只读复用**（批级闸门） |
| `adapters/v3_engine.py` | 冻结 v3 引擎（检索语料预测） | 无对应（PPV1 不用引擎臂） | 检索改为模板池（底物侧确定性检索） |
| `workflow/`（graph/nodes/routing/runner/state） | LangGraph 主循环：检索→分类→预测→校验→裁决→入账→导出 | `pollutant/runflow.py`（独立执行流，无 LangGraph） | 流程内核重写：假设→审计→账本→终点→导出 |
| `domain/policy.py`（decide_prediction_route） | recorded 直通/rank/analogy/novel 三路路由 | `pollutant/model_protocol.py` | 路由改为 proposals 协议（模型只提假设） |
| `services/atom_tool.py` | 冻结原子编辑工具 | 同一文件 | **只读复用**（production 链真实执行） |
| `exam_v2.py`（scorer-2/caliber v3） | cn 身份整串判分、组分全覆盖口径 | `pollutant/evaluation.py` | 严格结构+事件级匹配+分轴指标；`first_hit_rank` 只读复用成敏感性表 |
| `output/export_v3.py` | 冻结 v3 导出 | `pollutant/native_export.py` + `v3_projection.py` | 原生全量导出+确定性+过期识别；v3 只是显式有损投影 |
| `storage/pathway_store.py` 等 | 老路径账本 | `pollutant/store.py`（PollutantPathwayStore） | 独立 SQLite 账本：事件/出现/假设/搜索/endpoint 分表，首消费校验 |

新架构新增（老系统没有对应物）：

| 新模块 | 新增职责 |
|---|---|
| `pollutant/chemstate.py` | ChemicalState 严格结构身份（CXSMILES 规范化哈希，立体/同位素/自由基保真） |
| `pollutant/hypothesis.py` | 反应假设：参与物/系数/共同产物/step_scope 契约 |
| `pollutant/events.py` | 事件 vs 报告投影 vs 展开计划三集合分开（报告 K 不删事件事实） |
| `pollutant/path_context.py` | 路径上下文：条件事实三态评估、依赖继承、场景转换 |
| `pollutant/audit.py` | ChemicalAudit + admission 决策表 R1–R7 + 供体诊断消费 |
| `pollutant/search.py` | 持久搜索底座：action/attempt/request 身份、预算、四崩溃恢复 |
| `pollutant/queue.py` | 调度：池选择、两类 deferred、场景转换入队 |
| `pollutant/production.py` | 固定生产链：AtomTool→供体诊断→converter→audit→admission→submit |
| `pollutant/endpoint.py` | 终点四分账 + F01/F02/F03 硬约束 |
| `pollutant/native_result.py`/`native_export.py` | 原生结果对象 + 确定性文件导出 + 过期/完整性首消费 |
| `pollutant/reference_graph.py` | 参考图 schema（权威判分输入，非模型输出） |
| `pollutant/preregistration.py` | 预注册模板（TBD 标注哪些必须用户/teacher 裁定） |
| `pollutant/profile.py` | PPV1 profile 注册与契约版本清单（单一事实源） |

判分口径的原文出处见附录 B；旧引擎臂在新系统没有对应臂（298 对照
沿用封存历史数字作参照锚）。

## 附录 B：判分口径对照（原文出处）

### B.1 老口径（v4.3 EC298）

| 口径 | 定义 | 出处 |
|---|---|---|
| scorer-1（cn 身份 any-one） | "金标集合 cn 身份（v3 eawag_lookup._cn_identity 同口径，charge-normalized stereo-blind）对有序候选逐一比较，任一金标产物命中即取该题首个命中 rank；分母恒为全部 298 题" | `src/pathway_v43/exam.py:22-26`（docstring）、`:588-590`（summary identity 字段） |
| scorer-2（两臂同口径） | "两臂统一从原始候选 SMILES 计算 cn_identity（charge-normalized stereo-blind…）；计分单位仍为整条候选字符串…多组分任一组分命中只进敏感性表" | `src/pathway_v43/exam_v2.py:9-14`、`:52-55`（IDENTITY_CALIBER）、`:122-157`（first_hit_rank）、`:369`（scoring_unit 字段） |
| 任务书冻结定义 | "对每题 products_smiles 金标集合，按 v3 eawag_lookup._cn_identity 的电荷归一化、立体盲身份比较有序候选，任一含碳金标产物命中即得该题首个命中 rank" | `docs/TASK_V43_EC298.md:38` |
| caliber v3（HIT60 后续勘误，组分全覆盖） | "候选组分集合包含全部金标主产物组分…any-of 禁止进主分" | `src/pathway_v43/exam_v2.py:16-21`、`:47-51`、`:196-210`（first_full_coverage_rank） |

### B.2 新口径（PPV1，冻结判据 ppv1-criteria-v1 + S5/S5b）

| 口径 | 定义 | 出处 |
|---|---|---|
| 严格结构身份（判据一） | state_id = 化学 CX 事实子集的规范化 canonical CXSMILES 稳定哈希；保留增强立体/自由基层/同位素；CN 与严格结构分开 | `docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md:56-140` |
| 原子守恒/电荷账（判据二） | 全氢元素账、电荷分轴、系数契约在提交边界拒绝非法值；unknown 不猜数值 | 同上 `:141-188` |
| 准入决策表（判据三） | R1–R7 有序首中即决：reject/defer/retain_conditional/expand；unknown 不自动 reject | 同上 `:191-243` |
| 节点匹配三档 | strict_structure / cn_only（不授严格命中，旁证不叠加）/ unmatched；scope 声明 cn_only/partial/unknown ⇒ 内容严格相等也封顶为 CN 旁证 | `src/pathway_v43/pollutant/evaluation.py:754-762` |
| 边匹配 | match_status ∈ matched_strict / matched_structure_only / partial / unmatched_required_node_uncovered / …；任一必要节点无严格命中 ⇒ 该边不产生严格候选；step_scope 不一致只算 structure_only | `src/pathway_v43/pollutant/evaluation.py:862-870` |
| S5 主指标 | 参考边召回（严格反应边召回/仅结构身份匹配/step scope 一致/预算未展开分列） | `docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md:563-588`（§9.1）、`:766-799`（§11 十九步判分流程）、`:1010-1011`（S5-10/S5-11） |
| S5b 双口径落地 | "主口径（新）：参考边召回 hit@1/@3/@5——每题命中 ⇔ 该题参考边 match_status=matched_strict…分母固定 = 全部注册 qid；老口径敏感性表（第二口径）：复刻 v43-ec298-scorer-2 官方主口径…复用 exam_v2.first_hit_rank 只读" | `src/pathway_v43/pollutant/s5b_scoring.py:11-32`（docstring） |
| "更严"限定 | 主口径系统性更严，结论句必须双口径并列、通过线以老口径历史数字为参照锚，不得单报主口径宣称达到 | `docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md` §5.3（回修修订⑤） |

### B.3 一句话对照

老口径问"五个候选里有没有一个和金标长得一样"（cn 粗粒度 + any-one
宽松）；新口径问"你提交的这条反应边，原子级就是参考边、必要产物全
盖住了、机理口径也对得上吗"（strict + 全覆盖 + 分轴披露）。两者在新
系统里同报，宽严自见。

## 附录 C：数字口径提醒（对外必读）

1. **对外数字必须带题域标签**：298 = RHEA 通用酶学单步酶促题域；
   dev = B1 环境路径中间步骤题域。两个题域双向不外推、不混报
   （AGENTS.md 红线；S5 任务书 §5.1）。
2. **老系统 298 成绩（历史锚，题域 298）**：
   - 首轮 v43r1（scorer v2）：agent hit@1/3/5 = 116/128/130，
     引擎 = 118/174/193（`docs/EC298_REPORT.md:15-17`）；
   - Phase D 复测：C0 = 136/182/186，D-3 = 132/174/182
     （`docs/EC298_PHASE_D_RETEST_REPORT.md:30-32`；复测性质为
     `seen298_post_hoc_repair_check`，非独立外部验证）；
   - 更早历史锚 v4.1：agent 118/179/190（`docs/TASK_V43_EC298.md:40`）。
3. **新系统（PPV1）没有 298 真跑数字**：截至本文落盘（HEAD
   `cf64624`，2026-10-09），S5b 预注册已确认、真模型 298 跑未发车。
   PPV1 现有数字全部是**工程验收数字**（如全量 1786 测试通过，
   `docs/POLLUTANT_PATHWAY_S5B_RUNTIME_DELIVERY_2026-10-09.md`），
   **工程验收 ≠ 科学性能**——不能拿测试通过数外推命中率。
4. **结论句式**（预注册冻结，对外沿用）："在已见 298 题、冻结配置下
   的已知证据重建成绩（题域 298；dev 题域结果不外推、不混报）"
   （`docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md` §1）。
