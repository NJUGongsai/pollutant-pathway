# PPV1 S5b 架构·结果·提升 外部评审请求（GPT 审阅版，2026-10-09）

撰稿：S5b 评审请求汇编子代理（2026-10-09，基于仓内文档、源码只读核实
与本批官方终判分）。
读者：GPT（外部评审模型，**无本项目任何对话上下文**——本文完全自包含）。
审阅对象：PPV1 S5b——污染物降解路径系统 v4.3 的 298 题全量真实模型
评测子系统——的 ① 架构设计 ② 代码路径组织 ③ 测试与运行结果
④ 失分诊断与三轴提升建议。

**题域声明**：本文全部对外数字属 **298 题域**（RHEA 通用酶学单步酶促
转化）；本仓另有 dev 题域（B1 环境路径），两题域双向不外推、不混报。
**口径声明**：**主口径（新严格口径，matched_strict 参考边召回）** 与
**老口径敏感性（v43-ec298-scorer-2 官方"整串任一命中"复刻）** 是两把
尺子，**互不可比**；任何带数字的句子都注明口径名；主口径数字不与老
系统历史数字直接对比。
**零金标声明**：本文零金标内容（不出现题卷 questions.jsonl 的任何产物
SMILES / 参考图边取值；示意一律用合成小分子，如 CCO → CC=O 级）；
成稿后做了三通道泄露扫描（§8.4，0 命中）。

---

## 0. 审阅请求边界

1. **只读审阅**：本请求只要求评审意见，不要求、也不授权任何仓库改动。
   若你有执行通道，可跑**只读探针与 pytest**（见 §3 命令），但：
   - 不得修改任何仓内文件、不得提交、不得 push；
   - 不得触发任何真实模型调用（花钱/联网推理一律禁止）；
   - 不得访问金标仓、题卷原文、封存 run 之外的判分中间产物（金标只
     允许在判分进程语义内被讨论，不需要你读取）。
2. **不信任执行声明**：本文引用的运行数字均注明来源（官方判分链输出、
   批根账本、测试记录）；这些是**待你核验的声明**，不是已证事实。凡是
   你无法复核的，请按"声明"对待并注明。
3. **结论采信以与程序证据互证为限**：你给出的化学判断与工程判断，我们
   只在与源码/测试/账本证据互证一致的范围内采信；不因通道身份背书。
4. **冻结侧不可碰**：预注册冻结稿（口径、通过线、分母）、冻结判据正文、
   封存 run（批根）都是只读历史；你的建议若触及口径级改动，只能进入
   "下一轮预注册"流程，不能改写已冻结判定。
5. 回复格式：请逐条回答 §7 的问题清单（可加自由补充节）；对每个结论
   标注置信度与依据类型（代码事实 / 运行数字 / 化学推断 / 猜测）。

---

## 1. 系统架构总览

### 1.1 PPV1 定位（一句话与展开）

**LLM 只做假设提案；检索、编辑执行、审计、判分全部确定性，判分零
LLM。** 展开：

- 模型在整条链上只出现一次：`decide` 步的 proposals 协议（一个
  system prompt + 一份用户载荷，要求模型返回一个 JSON 对象，内含
  池内假设选择与/或池外 novel 提案，novel 须带完整 reaction_spec：
  产物 SMILES + 原子级编辑列表 + 供体中心 + 对齐映射 + 预期产物）。
- 其余全部确定性：类比池检索（底物侧 Tanimoto 相似）、分子编辑执行
  （AtomTool，凯库勒空间原子级编辑器）、化学审计（ChemicalAudit，
  unknown 不可冒充核实）、事件提交契约（store 公共 writer）、判分
  （evaluate_scientific，零 LLM 零网络）。
- **fail-closed 契约层层设防**：结构化拒因贯穿全链——预算 0 时请求
  登记被拒（网络发送被阻止）；编辑引用未知原子/未知键级词落结构化
  拒因（不抛裸异常）；展开计划对同一产物互斥状态整题拒
  （`expansion_status_conflict`）；real 档评测输入两侧无 qid ⇒ 配对
  守卫结构化拒（`real_data_root_identity_fallback_forbidden`，先于
  任何评分/聚合/落盘）。
- **身份与版本机制**：run 身份（代码/资产/策略/profile/prediction
  逐字段）+ 冻结计划持久化 + resume 身份核对（不符即拒，不静默续跑）；
  提示词内容哈希进批身份（§2.3）。

### 1.2 一条题的生命周期（单题公共链）

```
run_input(qid, substrate_smiles, plan{pools, model.provider_kind})
  → start_ppv1_run(runflow.py:1528)
      严格 root state → 根 context → 冻结计划持久化(S3B-01)
      → 注册搜索 run(十上限) → 根 retrieve 入队
  → _Driver.drive(runflow.py:674) 主循环,按 action_kind 分发:
      retrieve  池获取(空池仍进 decide——novel 合法路径 S3B-05)
      decide    schedule_hypotheses + 底物档案 + 模型 proposals
                (_model_proposals runflow.py:1016:注入对象实现
                ppv1_real_fetch ⇒ 真实取响应;同一确定性解析器
                parse_model_proposals;有界格式反馈轮,反馈轮占额度)
      expand_hypothesis  固定生产链(production.py):
                AtomTool render/execute_edits(真实执行,凯库勒空间)
                → check_edit_against_donor(供体诊断)
                → center_evidence converter → audit_hypothesis
                → decide_admission(R1–R7) → 事件提交(store writer,
                含 _check_expansion_plan 提交期校验)
  → 停止(stop_report) → endpoint 四分账 → 原生导出 native_export
  → 判分(封存答卷后): s5b_scoring.score_s5b_batch
      → evaluate_scientific(参考边匹配 match_reference_edges,S5A-03
        必要节点全覆盖+参与物集合相等+step_scope 一致)
      → 双口径聚合 + CI + §9-4 配对硬门核验
```

崩溃恢复四边界（B1–B4）：续跑/补账/消费 bundle/悬空请求披露，
resume 走同一公共链（`resume_ppv1_run` runflow.py:1633），run 目录
flock 互斥（双进程只一方取得执行权）。

### 1.3 S5b 批处理层（298 题全量编排）

- **builder**（`s5b_builder.py`）：questions.jsonl → 每题一条 run 输入
  + 一张 G1 参考图（一题一图，qid 进 source_refs，全 principal，
  step_scope=net_reaction 无守恒声明，participant partial + 固定披露，
  known_gaps 仅披露不豁免分母）；输出根守卫 `check_output_root`
  （line 90）：仓内只许 gitignored `reports/ppv1_s5b/`，仓外合法，
  其余拒——金标承载物零入仓。
- **approve/price 门**：预注册批准记录（`preregistration_confirmed`，
  2026-10-09 用户确认）与当日价格快照落批根，score 侧门校验。
- **orchestrator**（`s5b_orchestrator.py`）：40 路进程、每题一个
  worker 子进程（`OMP_NUM_THREADS=1`，进程级崩溃隔离）；批级
  FileRateGate（`adapters/rate_gate.py:80`，flock + 单一 JSON 状态
  文件的跨进程闸门）：RPM 180 / TPM 2.7M 滑窗、429 全局冷却、
  401/403/402 付费停止、批调用数上限（本批 894）、在飞上限
  `max_in_flight=40` + 峰值原子记账；发车参数冻结（同批根改参 ⇒ 拒）。
- **断点续跑**：已完成 qid（终态 case 文件）SKIP；run 已存在 ⇒
  resume 幂等续跑；worker 死亡 ⇒ 无 case ⇒ 失败补位留分母。
- **worker**（`s5b_worker.py:33`）：装配 RealModelAdapter
  （`real_model.py:191`，凭证只从 env `V43_LLM_*`，v41 老名只读回退；
  逐调用账本 `<run_dir>/s5b_real_calls.jsonl`，零密钥；复用 legacy
  `OpenAICompatibleClient` 的 429 有界退避/付费停止/usage 归一）；
  结束落终态 case（stop_reason/endpoint/export_digest/调用/usage，
  从 ledger 与账本复算，不信内存）。
- **scoring**（`s5b_scoring.py:148`）：封存答卷后零 LLM 双口径聚合
  （§4）+ 预注册门 + §9-4 配对硬门（`coverage_report.pairing.
  bases_by_graph` 全部 = qid_strict 才放行判分聚合）。

### 1.4 数据流图（ASCII）

```
                    ┌────────────────────────────────────────────────┐
                    │  questions.jsonl(题卷,金标;只读,SHA 三锚核验)   │
                    └───────────────┬────────────────────────────────┘
                                    │ s5b_cli build (s5b_builder)
                                    ▼
        ┌───────────────────────────────────────────────────────┐
        │ 批根(gitignored/仓外): 参考图×298 + run_inputs×298     │
        │   + split/批清单(冻结注册序=行序)                       │
        └───────────────┬───────────────────────────────────────┘
                        │ s5b_cli approve / price
                        ▼
                 ┌─────────────┐
                 │ 预注册+价格  │ (confirmed 快照落盘)
                 └──────┬──────┘
                        │ s5b_cli run (orchestrator, 40 workers)
                        ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ 每题一进程 worker ──► FileRateGate(flock: RPM/TPM/894/在飞40)   │
  │   worker: RealModelAdapter.from_env ──► 真实模型(仅 proposals)  │
  │   start/resume_ppv1_run 公共链:                                   │
  │     retrieve(池: 底物侧 Tanimoto≥0.45 top-8 模板检索,零金标)     │
  │     decide(proposals→确定性解析→假设)                             │
  │     expand(AtomTool 凯库勒编辑→诊断→audit→admission→事件)        │
  │     → stop → endpoint → native_export                            │
  │   产物: runs/<run_id>/ + cases/<qid>.json + 调用账本             │
  └───────────────┬─────────────────────────────────────────────────┘
                  │ s5b_cli score (封存答卷后;金标此时进判分进程)
                  ▼
        ┌──────────────────────────────────────────┐
        │ s5b_scoring: evaluate_scientific(零LLM)  │
        │  主口径 hit@K + 老口径敏感性 + any-of 表  │
        │  分桶/CI + §9-4 配对硬门(qid_strict)      │
        │  → metrics.json / report.md / report_plain│
        └──────────────────────────────────────────┘
```

---

## 2. 代码路径地图

### 2.1 核心模块表（`src/pathway_v43/pollutant/`，行号为 2026-10-09 HEAD `57ea99b` 实读）

| 文件 | 职责（一行） | 关键入口（行号锚点） |
|---|---|---|
| runflow.py | PPV1 独立 runner：start/resume 分流 + 确定性驱动循环 + 真实模型钩子 | `start_ppv1_run`(1528) / `resume_ppv1_run`(1633) / `_Driver.drive`(674) / `_model_proposals`(1016, real 钩子) |
| search.py | S3a 持久搜索底座：身份/预算/认领/恢复/请求生命周期 | 契约 ppv1-search-6；S3A-01..05 消费闭合 |
| production.py | 固定生产链 AtomTool→诊断→converter→audit→admission→提交 | `prepare_hypothesis`(152) / `execute_atomtool_expansion`(270) / `expand_hypothesis_production`(381) |
| queue.py | 调度事务：冻结池选择、deferred 激活、followup | `schedule_hypotheses` / `record_expansion_outcome` / `activate_deferred` |
| store.py | 公共 writer/事件账/提交期契约校验 | `_check_expansion_plan`(1059；同 state_ref 多互斥状态 ⇒ `expansion_status_conflict` 拒) |
| audit.py | ChemicalAudit v10：检查范围明确，unknown 不冒充核实 | `audit_hypothesis` / `check_edit_against_donor` / `decide_admission`(R1–R7) |
| chemstate.py | 化学状态与身份键（化学 CX 事实子集 canonical CXSMILES） | `build_chemical_state`；ppv1-chemstate-4 |
| hypothesis.py / events.py | 假设/事件/报告投影/展开计划三集合分开（A02/A03） | — |
| endpoint.py | 停止≠终点：execution/stop/chemical endpoint/bookkeeping 四分账 | — |
| native_export.py / v3_projection.py | 文件级正式导出 + 显式有损投影（可回溯原生权威） | `read_native_export` |
| reference_graph.py | 参考图 schema（ppv1-reference-graph-1） | `load_reference_graph` / `validate_reference_graph` |
| evaluation.py | 科学评测器 ppv1-evaluation-5：零 LLM 判分 + real 档配对守卫 | `evaluate_scientific` / `match_reference_edges`(S5A-03) |
| real_model.py | S5b 真实模型适配层（传输与调用状态，不解释内容） | `_PROPOSALS_SYSTEM_PROMPT`(77–127) / `PROPOSALS_PROMPT_VERSION`(129) / `RealModelAdapter.from_env`(215) / `ppv1_real_fetch`(302) / `ScriptedRealModelAdapter`(447) |
| s5b_builder.py | 题卷→run 输入+参考图+清单；金标输出根守卫 | `check_output_root`(90) / `default_pool_provider`(380) / `_template_to_spec`(415) / `_bond_diff_edits`(488) |
| s5b_orchestrator.py | 40 路进程编排 + 断点续跑 + 闸门参数 | `run_s5b_batch`(137) / `summarize_batch`(342)；缺省闸门常量(42–46) |
| s5b_worker.py | 一题一进程执行入口 | `worker_main`(33)；装配 adapter + start/resume + 落 case |
| s5b_scoring.py | 封存答卷后零 LLM 双口径判分与报告 | `score_s5b_batch`(148) / `_bucket_counts`(581) / `_main_caliber_row`(452) / `_old_caliber_row`(494) / CI(594–682) |
| s5b_cli.py | 远端操作入口 | `build/approve/price/run/score/envcheck/summary` |

### 2.2 services / domain / adapters

| 文件 | 职责 | 关键锚点 |
|---|---|---|
| services/atom_tool.py | AtomTool：SMILES↔MoleCode 往返 + 受限编辑核验（确定性零模型；vendored MoleCode 逐文件 SHA256 fail-closed） | `render`(174) / `execute_edits`(402；入口 `Chem.Kekulize(clearAromaticFlags=True)`@417，凯库勒空间) / `check_target_consistency`(621) / `align_donor_mapping`(756)；协议 v43-editproto-2 |
| services/donor_applicability.py | 供体变换提取与适用性门禁：全部相关对齐枚举 + 确定性施加 + fallback 词表 | `extract_donor_transform`(148) / `enumerate_alignments`(295) / `assess_donor`(556) / `evaluate_card`(712)；**对齐用芳香形式（aromatic≡aromatic 一致、混合记失配）**；v43-applicability-3 |
| services/analog_source.py | 类比语料检索（`AnalogSourceResolver.templates_similar_to`，供体反应物↔底物 Tanimoto） | 池检索通道 |
| domain/identity.py | `cn_identity`（电荷归一 + 立体盲 canonical，cn-v1）——老口径判分身份 | — |
| domain/policy.py / models.py | PREDICTION_POLICY_VERSION(v43-predpol-3)；`DONOR_FALLBACK_*` 词表单一事实源（产出方与消费方共用） | — |
| adapters/rate_gate.py | `FileRateGate`(80)：flock + 单一 JSON 状态文件的跨进程闸门（RPM/TPM/max_calls/max_in_flight） | — |
| adapters/llm_client.py | legacy `OpenAICompatibleClient`（429 退避/付费停止/usage 归一/Idempotency-Key）——S5b 只读复用，不重写 | — |

### 2.3 契约与版本注册机制（评审重点之一）

- 每模块带 `*_VERSION` 常量（s5b-real-model-1 / s5b-builder-1 /
  s5b-orchestrator-1 / s5b-worker-1 / s5b-scoring-1；atomtool/
  editproto/applicability/evaluation 同理），进 run 身份与批清单。
- **提示词内容哈希**：`PROPOSALS_PROMPT_VERSION = sha256(
  _PROPOSALS_SYSTEM_PROMPT)`（real_model.py:129）——提示词任何内容
  变更自动升版，随 `run_identity.prediction.prompt_versions.proposals`
  入批身份；**旧批 resume 按身份拒**。这是"改提示词=新实验"的机制化。
- 批身份另有 `code_identity.aggregate_sha256`（本批 c637fda4…）与
  类比语料资产身份（analog corpus v1，sha256 8f3f2c1a…）。
- 模型身份：`ZHIPU/GLM-5.3-Flash`（dashscope 兼容通道，env 注入，
  密钥零回显零落盘）。

### 2.4 测试文件表（tests/，S5b 相关）

| 文件 | 数量 | 覆盖点 |
|---|---|---|
| test_ppv1_s5b_runtime.py | 20 | 客户端 8（env 缺失 fail-closed / v41 回退 / 身份块 / 载荷形状 / 桩全链 / 传输失败记账 / 额度 0 阻断 / 无 model 旧行为回归）+ 构建器 3（合成端到端 / 输出根守卫 / 题卷校验）+ 编排器 3（子进程 + resume SKIP + 失败留分母）+ 判分 5（双口径 / real 门三态 / 预注册 helper / 通过线 / 配对）+ **冒烟回归 1**（提示词键级词表 ↔ 执行器凯库勒空间双锚断言，57ea99b 新增，~719–730 行） |
| test_ppv1_s5b_pairing.py | 14 | qid 感知样本↔导出配对语义（同根多题不串题） |
| test_ppv1_s5b_rework_l01.py | 7 | real 档配对禁 root_identity_fallback 守卫（反例翻转 + 正控保留 + 契约注册） |
| test_atom_tool.py | 15 | 往返/编辑/对齐；含 `test_execute_edits_unknown_to_order_refused_not_raised`（未知键级词落结构化拒因、不抛异常——57ea99b 修复的正控） |
| test_ppv1_r5_chem.py | 25 | 化学判据回归（audit/diagnostic/立体 EZ/新原子锚定等） |

---

## 3. 测试与验证现状

### 3.1 全量回归

- **全仓 1788 passed / 0 failed / 0 skipped**（2026-10-09，conda 环境
  depending43，`python -B -m pytest tests/ -q -p no:cacheprovider`，
  约 9 分钟）——aromatic 修复（57ea99b）合入后、全量发车前的绿灯记录。
  此为仓内执行声明，你可复跑核验（只读，不触发模型）。

### 3.2 今日事故驱动的增量验证链（冒烟两轮对照）

1. **第一轮冒烟（批根 batch1，后作废）**：10 题中 3 失败——
   - 2 例 `KeyError: 'aromatic'` **整题崩溃**：proposals 提示词键级
     词表含 `aromatic`，而执行器 `execute_edits` 为凯库勒空间，只认
     single/double/triple——模型按词表规范输出 `to_order=aromatic`，
     `_BOND_TOKENS` 查不到即抛裸 KeyError；
   - 1 例 `expansion_status_conflict`（模型侧提交契约冲突，按预注册
     记模型侧诚实失败）。
2. **修复 57ea99b**（当前 HEAD）：`execute_edits` 对未知键级词落结构化
   拒因（`edit_execution_failed:bad_bond_order:…:to_aromatic:…`，
   atom_tool.py:465–474，防御注释点名冒烟崩溃根因）；提示词词表改
   `single|double|triple`；`PROPOSALS_PROMPT_VERSION` 内容哈希自动
   升版；新增词表双锚测试。全仓 1788 绿后仅两 src 文件
   （real_model.py / atom_tool.py）重部署远端，部署核验 = 远端两文件
   SHA256 与本地 `git show 57ea99b:...` 逐字节一致
   （7b39136e0a67… / f2efc993ee33…）。
3. **第二轮冒烟（批根 batch2，官方批前缀）**：10/10 终态、**零代码
   崩溃**（原 2 崩题一活一走完多轮追问）。修复后模型仍输出
   `to_aromatic`（词表遵从度有限），但后果从整题崩溃降为提案级
   结构化拒绝、run 继续——这正是 fail-closed 设计意图。
4. 行为差异一句话：崩溃（整题 KeyError）→ 结构化拒因（提案级拒绝、
   run 继续）。

### 3.3 本地零成本复现方法

- **脚本桩**：`ScriptedRealModelAdapter`（real_model.py:447）与真实
  适配器**同一**取响应调用序与同一确定性解析器，provider_kind 按
  plan 注册（scripted ⇒ 网络 0、不占真实额度）——测试与冒烟用。
- **账本重放**：每题真实调用的响应原文已存逐调用账本
  （`s5b_real_calls.jsonl` 的 responded 行含 response_text 截断 20K），
  可把响应原文注入 scripted 桩、走**同一条 `start_ppv1_run` 公共链**
  重放——零模型、零新调用、本地即可复现执行期行为（57ea99b 修复
  验证与后续 17 qid 冲突重放均用此配方）。

---

## 4. 298 全量结果（官方终判分，官方链）

数字版本：远端 chain8 自动判分链输出（2026-10-09 10:24 UTC），
`CHAIN8_SCORE_EXIT=0`、`CHAIN8_BASIS_OK graphs=298`；判分数字引自
冻结判分链输出（批根 metrics.json），未自行重算口径。**§9-4 配对硬门
通过**：全部 298 图 pairing basis = `qid_strict`。

### 4.1 双口径数字表（题域 298，分母固定 298，零 LLM 判分）

| 口径 | hit@1 | hit@3 | hit@5 |
|---|---|---|---|
| **主口径**（matched_strict 参考边召回，事件报告序） | **39**（13.09%） | **72**（24.16%） | **74**（24.83%） |
| **老口径敏感性**（v43-ec298-scorer-2 官方整串 any-one 复刻） | **71**（23.83%） | **111**（37.25%） | **122**（40.94%） |
| 多组分 any-of 探索表（不与主表混算） | 72 | 114 | 125 |
| 预注册通过线（锚=老口径首轮历史数字） | ≥116 | ≥128 | ≥130 |

- **两口径互不可比**（判定单位：主口径 K 槽=候选事件，老口径 K 槽=
  产物字符串；身份：严格 canonical vs cn 归一；输入宇宙不同）。
  两口径命中集合关系：主口径 74 ⊂ 老口径 122（both 74、old-only 51、
  main-only 0）。
- 双口径均未达预注册线。老口径为与老系统可比口径：本批 71/111/122
  对**复测锚 C0**（同口径 136/182/186）为 52.2% / 61.0% / 65.6%
  相对水平——**仅供老口径相对定位**；首轮锚与复测锚互不可比；主口径
  数字不与上述任何老系统数字直接对比。
- 主口径 95% CI（S1 bootstrap，单题簇，不消除跨题相关）：hit@1
  [9.4%, 17.1%]，hit@3 [19.5%, 28.9%]，hit@5 [20.1%, 29.9%]；
  Wilson 按题 hit@1 [9.7%, 17.4%]。
- 中期视图披露：18:15 中期判分（288/298 终态、10 题按漏计）主口径
  39/71/73、老口径 70/110/121；与终数差 = 长尾 1 题 + 1 题转 failed。
- 调用与费用（题域 298，官方链账本）：gate 请求启动 310/894 上限
  （34.7%）；429 共 15 次（3 次重试耗尽）；并发峰值 40（=在飞上限）；
  计费调用 298 次成功（全量 288 + 冒烟 10）+ 4 次调用层错误
  （3×429 耗尽 + 1 空响应，未触发题级重试、按空跑计）；tokens
  in 270,604 / out 5,001,101；费用全量段 14.2168 CNY + 冒烟段
  0.5628 CNY ≈ **14.78 CNY**（价格快照 0.8/2.8 CNY/Mtok 在位）；
  墙钟全量段 3,534 s。每题恰好 1 次调用；output 计费均值 ≈17.4K
  tok/调用（推断差额为 reasoning token 计费，未取得 provider 字段级
  确认）。

### 4.2 终局分桶（题数；语义已对照 s5b_scoring.py `_bucket_counts`
核实：两遍叠加——第一遍每题计首参考边 match_status 桶，之和=298；
第二遍对 run 非 completed 追加 `run_<status>` 桶）

| 桶 | 题数 | 语义 |
|---|---|---|
| matched_strict | 74 | 必要节点全覆盖 + 参与物集合相等 + step_scope 一致 |
| matched_participant_coverage_partial | 15 | 结构候选存在但参与物集合非 exact（超集多写/子集缺声明） |
| unmatched_required_node_uncovered | 187 | 必答参考节点至少一个无许可严格命中（不是"没答题"） |
| not_evaluated_no_edges | 22 | = 22 个 failed run，评测器无样本边可匹配 |
| run_failed（叠加遍） | 22 | 17 `expansion_status_conflict` + 5 `unparseable_smiles`；终局无 run_no_case |

对 187 uncovered 的接近度分带（Morgan(2) Tanimoto，比对只在远端只读
分析进程内完成、正文零金标）：exact 产物已在预测态 **14** + 近似
≥0.90 **21**（合计 35 = 身份级近似未中：互变异构/立体未标注/质子化
状态差）；0.60–0.90 **23**（官能团级答偏：氧化深度跳档/断键位置/
对称位点）；<0.60 带假说 **84**（**反应方向未中——最大单一失分带**）；
零假说完成 49（<0.60 的 45 + 0.60–0.90 的 4：run completed 但全部
  提案被执行期结构化拒因拒掉，含 4 题调用层错误）；failed 22 零态。

### 4.3 关键相关性（题级，全 298）

- **来源 × 命中**：analog-only 题 21 中 14 中（**66.7%**）；mixed 35
  中 14 中（40.0%）；novel-only 170 中 60 中（**35.3%**）；零假说
  71 题 0 中。
- **池深**：实收池深分布 {0:120, 1:92, 2:37, 3:26, 4:13, 5:7, 7:2,
  8:1}，均值 **1.18**，**40.3% 空池**（120 题），池深 ≥3 仅 43 题。
- **池深 × 命中为负向关联**（观测，因果未证）：命中题均池深 0.95 vs
  uncovered 题 1.36；空池 120 题 35 中（29.2%）vs 非空池 178 题 39 中
  （21.9%）。两种候选解释（未证）：0.45 阈值召回的模板偏向难题底物；
  或模板错误断键先验误导。
- **留存率（导出假说 495 条，按来源分）**：analog-template 92 条
  （池提案留存率 92/331 ≈ **27.8%**）vs novel 403 条（novel 留存率
  403/574 ≈ **70.2%**）——模板侧执行留存率显著低于 novel。
- **提案结构**：905 条提案（331 池 36.6% + 574 novel 63.4%）；292 个
  可解析响应（2 响应整体不可解析）；252/292 题含 novel；零弃权；
  novel 被模型排首位 129/252；novel 引用率 24.4%（浅语义，仅登记）。
- **执行期拒因普查**（880 次展开尝试，306 次 ok=False）：
  `bond_order_mismatch`（以 `expected_aromatic_have_single/double`
  为主）**258**；`bad_bond_order`（含大量 `to_aromatic`）**229**；
  `bond_already_present` 146；`sanitize_failed` 79；`bond_not_present`/
  `unknown_atom` 12/2。**芳香/凯库勒表示鸿沟是最大单一执行期损耗源**。
- 模板来源（留存假说侧 transformation_ref 前缀）：EAWAG-BBD 42、
  EAWAG-SEDIMENT 6、EAWAG-SOIL 5、rhea:* 若干。

---

## 5. 失分诊断（继承自 teacher 版审核文档，供你审）

**总判断：本批失分主结构不在"模型不会写 JSON"或"系统崩溃"，而在
供给端三连 + 方向性答偏。**

1. **检索池饿死**（轴 2 靶点）：底物侧单通道 Tanimoto ≥0.45、top-8、
   仅带映射模板——实收均值 1.18、40.3% 空池；而 analog-only 命中率
   66.7% 显著高于 novel-only 35.3%，说明"池留存下来时是最强正向信号，
   问题在召回面与执行留存率"（与池深负向关联合并解读）。
2. **类比模板与凯库勒执行器语言不通**（轴 3 靶点，与已修 aromatic
   事故同根但长在模板转换侧）：代码事实——对齐层
   `donor_applicability` 用**芳香形式**（aromatic≡aromatic 视为一致，
   混合记失配），而执行器 `execute_edits` 在**凯库勒空间**施加编辑
   （入口 `Chem.Kekulize(clearAromaticFlags=True)`，atom_tool.py:417，
   kekulize 失败则按芳香形式继续、键级前提如实失配）；两套表示在模板
   派生 spec 处相遇——`s5b_builder._bond_diff_edits` 的 `order_token`
   把模板分子图的 `AROMATIC` 键型直接映射为词表外的 `"aromatic"`
   键级词（s5b_builder.py:506–512 区域），产出的 edits 撞凯库勒执行器
   即 `expected_aromatic_have_*` 258 例——模板留存率 27.8% 远低于
   novel 70.2% 的直接嫌疑。
3. **提交契约过严丢 17 题**：`expansion_status_conflict`（store.py:
   1087–1093：同一事件展开计划对同一 `state_ref` 给多个互斥状态 ⇒
   fail-closed 拒整题）。抽样证据示至少 1 题模型已给出与金标同方向的
   正确 novel 提案、死于该提交期校验；触发形态推断为"同一分子以主
   产物+共产物（或重复）双写"，根因未钉死（离线探针列为前置项）。
4. **最大头：方向性答偏**——187 uncovered 中 <0.60 带假说 84 题
   （提案全程与金标产物远带：反应类别/方向错误或仅底物自异构化类无效
   位移）+ 零假说 49 题（拒因吞掉全部提案，芳香鸿沟为公共成因）。
   归因初判 = **首版提示词 + 检索成熟度**（池浅、无产物侧/反应类型级
   检索、提示词无断键/氧化深度自查要求）。
5. 口径严格性成本（如实披露，不当"失分"处理）：35 题身份级近似未中
   （互变/立体/质子化）+ 15 partial（多写无机共产物）——预注册已知
   低估方向，改口径须走下一轮预注册，不在本轮工程修复范围。

---

## 6. 三轴提升建议（同源 teacher 版 §3；每条：证据→改法→影响→验证→
风险→级别。**全部属下一轮预注册流程；任何提示词内容变更自动升
PROPOSALS_PROMPT_VERSION 哈希并改变批身份（机制，非障碍）；判分口径
与冻结判据零触碰。**）

### 轴 1 提示词（real_model._PROPOSALS_SYSTEM_PROMPT）

1. **[工程] 芳香体系表示指令**：证据 = to_aromatic 229 例 + 零假说
   49 题；改法 = 提示词加一句规则级指令"芳香环必须以交替单双键表达；
   执行器工作在凯库勒空间"；影响 bucket = 零假说 49 部分回收（novel
   留存率 70.2% → ↑）；验证 = 下轮同口径拒因普查对比 + 零假说题数；
   风险 = 词表遵从度未知（本轮已见违规输出），纯提示词天花板有限，
   建议与轴 3-1 二选一或并行（执行器侧是根修）。
2. **[工程] 展开计划冲突消除**：证据 = 17 题整题报废（§5.3）；改法 =
   提交侧对重复 `state_ref` 计划条目做确定性合并（语义最强：expanded
   > deferred > not_tracked），或提案解析侧同事件内重复分子去重；
   影响 = failed 22 中的 17 直接回收为可评测态；验证 = 17 qid 用已存
   调用账本响应**离线重放**（零模型）验证合并后走完公共链 + 新批分桶
   对比；风险 = 合并/去重语义须与 R2-09 契约核对——契约内解释走回修
   轮，新规则须化学判据评审后进预注册；先做根因探针钉死重复形态。
3. **[工程] 断键/氧化深度自查字段**：证据 = mid 带 23 题（氧化深度
   跳档/断键位置/对称位点）；改法 = 每条 novel 提案附结构化自查（断/
   成键原子对 + 反应中心氧化态变化）显式入 reaction_spec；影响 =
   mid 带 23 题与部分 far 带官能团错位题；验证 = mid 带题集下轮同口径
   对比 + 自查字段与 edits 一致性抽查；风险 = 输出更长→费用上升
   （现均 17.4K output tok/调用），自查可能流于形式。
4. **[口径级] 共产物策略对齐**：证据 = partial 15 题全部主产物精确、
   败于多写共产物；改法 A（工程）= 提示词"只声明转化必需的共产物"；
   改法 B（口径级）= 参与物覆盖对小分子无机共产物设忽略档——**改主
   口径严格性，须 teacher 裁定 + 预注册 + 化学判据评审**；顺序 = 先 A
   观察一拍，B 不与其他改动混轮；风险 = A 可能压掉真实共产物，B 须防
   "以放宽换通过"。
5. **[工程] 词表同源纪律**（aromatic 事故的通用化）：把提示词↔执行器
   词表双锚扩展到提示词内全部受控词表（op/order/side/status/
   output_origin），从执行器常量单一来源生成或 CI 双向断言；验证 =
   CI 常驻；风险 = 无直接分数影响，防再犯。

### 轴 2 检索池（s5b_builder.default_pool_provider：阈值 0.45 / max 8）

1. **[工程] 阈值/池深参数扫描**（最高杠杆）：证据 = 均值 1.18、
   40.3% 空池 vs analog-only 命中率 66.7%；改法 = 阈值降至 0.35–0.40
   或动态降档（不足 3 条时降阈值补齐），max_pool 维持 8；影响 = 空池
   120 题覆盖↑、含 analog 假说题 56 → 100+；验证 = **离线零模型重放
   检索面**（只读资产统计池深/模板来源分布）→ 新批来源×命中表；风险 =
   低相似模板引入错误断键先验，须与轴 1-3 自查或轴 3-2 适用性门配套，
   不能单变量放阈值。
2. **[工程] 空池显式声明**：空池时 payload 增 `pool_empty: true`
   标志，提示模型此题须走 novel 化学；影响 = 空池 120 题 novel 方向性；
   风险 = 低。
3. **[工程] 调用层有界重试**：4 题调用层错误（3×429 耗尽 + 1 空响应）
   无题级重试、按空跑计 0 分（≈1.3 个百分点）；改法 = gate 冷却后题级
   单次重试；风险 = 费用微增。
4. **[口径级+资产级] 检索面扩展**（产物侧/反应类型级检索）：需新语料
   授权且批内同卷跨题复用有泄漏风险——语料可用范围须 teacher 裁定后
   走预注册；风险 = 工程量大、泄漏红线敏感。

### 轴 3 类比模板（donor_applicability + alignment 链 + _template_to_spec）

1. **[工程] 芳香/凯库勒空间统一（根修，与轴 1-1 二选一或并行）**：
   证据 = §5.2 代码事实 + 258 例 mismatch + 模板留存率 27.8% vs novel
   70.2%；改法二选一——(a) 转换侧：`_bond_diff_edits` 输出凯库勒显式
   键（模板分子先 kekulize 再取键差）；(b) 执行器侧：施加前对当前
   分子统一表示空间（或 execute_edits 接受 aromatic 词并在内部
   kekulize）；验证 = 对 258 例样本**离线零模型重放**（同响应重放公共
   链）→ 接受率对比 + 全仓回归；影响 = 模板留存率与含 analog 假说题数
   双升，经 66.7% 命中率传导至主口径；风险 = **触及身份计算空间**
   （结构身份/CN 同值口径），属判据级敏感面——化学判据评审后再进
   预注册，保留合法正控、防过拒。
2. **[工程] 模板适用性门与误导普查**：先聚合本批 `DONOR_FALLBACK_*`
   五类 fallback 原因分布（本轮未聚合，前置探针）；再评估收紧
   `COMPETING_TRANSFORMS`/键级上下文失配门槛；风险 = 过拒丢正控
   （池供给本就浅）。
3. **[工程] alignment 质量抽检探针**：对 56 个含 analog 假问题抽 10
   个人工核对对齐映射 vs 模板 lhs（与模板自身对照，零金标要求）；
   产出对齐错误率基线。
4. **[口径级] 参考图共产物声明语义**（与轴 1-4B 同一裁定点）：teacher
   裁定参考图共产物口径（声明完整性 vs 判分忽略档），出题侧与判分侧
   同源落字。

优先级排序（teacher 版）：**轴 1-2 ≈ 轴 3-1 > 轴 2-1 > 轴 1-4 > 其余**。

---

## 7. 请 GPT 重点审的问题清单

1. **供给端诊断是否成立**：§5 的三连（检索池饿死 / 模板-执行器表示
   语言不通 / 提交契约过严丢 17 题）作为主失分解释是否成立？有无更优
   或遗漏的解释？特别是池深与命中率**负向关联**（空池 29.2% vs 非空
   21.9%）——除"阈值召回偏难题底物"与"错误断键先验误导"外，有无第三
   种解释（如选择效应/难题集中在多步或杂环类）？你建议用什么最小探针
   区分？
2. **修复优先级**：teacher 版排序（轴 1-2 ≈ 轴 3-1 > 轴 2-1 > 轴 1-4 >
   其余）是否正确？若按"每工程日期望回收题数 × 风险"重排，你的排序
   与理由？特别地：17 题冲突合并（工程小、回收直接）与 258 例表示
   统一（根修、判据敏感）哪个应先行？
3. **方向性答偏的提示词良方**：84 题 far 带带假说（反应类别/方向未中）
   是最大单一失分带。在"提示词不许引导模型猜金标"的边界内，有无已知
   有效的提示词层改法（如反应类型分类先行、断键自查结构化字段、
   few-shot 合成示例——注意示例只能用合成分子如 CCO→CC=O 级）？
   各改法对输出 token（现均 17.4K/调用）的费用弹性如何评估？
4. **架构级风险盲区**：审 §1 架构与 §2 代码组织，指出我们可能的结构性
   盲区。已知候选（请验证或反驳）：(a) 每题一进程 + 40 在飞的伸缩性与
   长尾（max 单调用 2,054 s、timeout 3,600 s）——批墙钟被单题长尾
   支配时 gate 席位空转；(b) FileRateGate 单 JSON 文件 + flock 的单点
   与竞争开销；(c) worker `except Exception` 全捕获落 failed case
   ——契约异常与方法失败同桶，是否掩盖应分开的类别；(d) 断点续跑的
   case SKIP 语义对"case 在而 run 不完整"的场景是否充分；
   (e) `preregistration_approved`（s5b_scoring.py:93–101）把"非空且
   不含 pending"一概视为已批准——如 `rejected` 这类状态词也会过门，
   状态词表是否应改为枚举白名单；(f) 每题恰 1 次调用 + 无题级重试的
   设计在 4 例调用层错误上的损失（1.3 个百分点）是否可接受。
5. **模板-执行器表示统一的收敛侧**：轴 3-1 的 (a) 转换侧（模板派生
   spec 输出凯库勒显式键）vs (b) 执行器侧（施加前统一表示空间/接受
   aromatic 词）——从正确性、爆炸半径（版本/身份影响面：chemstate
   身份键、run resume 拒、既有 1788 测试的回归面）、可验证性（离线
   重放）三方面，你主张在哪侧收敛？两侧并行的风险（同一题 edits 在
   两个空间各被归一一次）如何防？
6. **下一轮预注册变量控制**：若下一轮同时落地轴 1-2（合并）+ 轴 3-1
   （表示统一）+ 轴 2-1（阈值 0.35–0.40），三因子混轮的归因可行性？
   你建议的轮次切分与每轮预注册应控制/冻结的变量清单（提示词版本
   哈希、池参数、判分口径、并发）？哪些改动绝对不能与性能改动同轮？
7. **判分链与报告语义**：(a) 两遍叠加分桶（match_status 桶 + run_*
   叠加桶）的呈现是否易被误读为"分母 >298"；(b) 老口径
   `report_rank=None` 排除规则（宽度外产物不进候选序列、计数披露）
   对新系统的可报告宽度是否构成系统性悲观偏（cap = max(1, min(w,4))
   vs 老答卷 ≤5/步）；(c) 主口径 `matched_event_not_in_candidates=0`
   能否作为 rank 归位无异常的充分证据；有无你建议补的判分侧健全性
   探针。
8. **身份级近似未中的提示词侧回收空间**：35 题（互变异构 14 exact +
   21 near ≥0.90）在**不改判据**（互变等价轴本轮不加、strict 身份
   冻结）前提下，提示词要求"产物以最稳定酮/内酰胺形式表达、显式立体
   标注"有多大回收空间？这与"提示词不得引导模型迎合金标表示"的边界
   如何划（判据是通用的表示规范还是对金标口径的过拟合）？

---

## 8. 附录

### 8.1 今日事故链时间线（"提示词词汇表必须与执行器/校验器同源"案例）

| 时点（CST） | 事件 |
|---|---|
| 09:03 | 预注册冻结稿状态 `preregistration_confirmed`（用户逐项圈定 20+2 项 + 要点确认） |
| 批 1 | 冒烟 10 题：6 完成 / 3 失败——2 例 `KeyError 'aromatic'` 整题崩溃（提示词词表含 aromatic、执行器凯库勒空间不认）+ 1 例 expansion_status_conflict；~15 次真实调用随批作废（原批根保留只读，作废如实披露） |
| 修复 | 57ea99b：execute_edits 未知键级词 → 结构化拒因；提示词词表改 single\|double\|triple；PROPOSALS_PROMPT_VERSION 内容哈希自动升版；词表双锚测试入仓；全仓 1788 绿；两文件重部署 + SHA 逐字节核验 |
| 批 2 | 冒烟重跑 10/10 终态、零代码崩溃 → 白名单推全量（288 qid） |
| 17:25 | 全量 40 路起跑；18:23 长尾收口，cases 达 298 |
| 18:24 | chain8 自动判分：CHAIN8_SCORE_EXIT=0、BASIS_OK graphs=298（终数见 §4.1） |

教训（通用化）：提示词内一切受控词表（键级/操作/状态/来源）必须与
执行器/校验器常量**同源**（单一事实源或 CI 双锚），否则模型"按规范
输出"本身成为崩溃向量；fail-closed 结构化拒因把同类事故从整题崩溃
降为提案级拒绝。

### 8.2 未核项清单（继承 teacher 版附录 C，供你核验）

1. 批 1 作废段 ~15 调用未单独计价（作废披露口径）。
2. `expansion_status_conflict` 重复形态根因未钉死（已定位校验点
   store.py:1059 与影响面 17 题；需一离线探针）。
3. output token 与响应正文差额归因"reasoning token 计费"为推断
   （有耗时旁证，无 provider 字段级确认）。
4. `DONOR_FALLBACK_*` 分布与 alignment 错误率未聚合/未抽检（本轮证据
   缺口，轴 3-2/3-3 前置探针）。
5. 池深与命中的负向关联为观测关联，因果未证（两种解释并存，§7-1）。
6. 结果化学复核（外部化学评审通道，按仓内三触发点之 3）未随本文执行；
   本文为程序证据侧汇编，建议随下一轮判据冻结/预注册一并送审。

### 8.3 完整性声明

- **两次发车**：批 1（batch1，作废，~15 调用如实披露不计入正式数字）
  与批 2（batch2，官方批，全部正文数字来源）。
- **判分零 LLM**：判分链（s5b_scoring → evaluate_scientific）无任何
  模型调用；金标仅在封存答卷后的判分进程进入；metrics 零金标 SMILES
  取值。
- **冒烟即正式批前缀**：冒烟 10 题与全量同批根同身份续跑，不借看
  结果改配置（预注册纪律）；gate 上限 894 与并发 40 为冻结值。
- **本文引用的运行数字**全部来自官方判分链输出与批根账本（声明，
  待你按 §0.2 核验）；源码行号为 2026-10-09 HEAD `57ea99b` 实读。
- **金标边界**：本文撰写全程未读取题卷金标内容；接近度分带等涉金标
  比对的分析均在远端只读分析进程内完成，只回传计数。

### 8.4 金标泄露扫描

- 方法：对本文抽取全部类 SMILES token（正则覆盖 `>>` 反应式与含键符/
  括号的紧凑分子串），与金标题卷 questions.jsonl 的
  `products_smiles` / `substrate_smiles` 全集做三通道比对：精确相等、
  RDKit 规范化相等、金标组分（≥8 字符）作为子串出现在文中。
- 结果：三通道命中均 **0**（详见扫描执行记录；文中仅有的分子串为
  合成示意 CCO / CC=O，均非金标组分）。
- 扫描为成稿后本地只读执行；脚本与输出留存 `/tmp/s5b_review/
  leak_scan_gpt/`（仓外，零金标内容）。
