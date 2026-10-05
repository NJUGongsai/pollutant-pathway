# pathway v4.3 架构评审报告（独立评审人）

评审对象：`/Volumes/CC/Enzyme_Agent/dependingv43`（分支 `v4.3` @ `bf1ac38`）
评审性质：静态架构评审（只读代码与文档，不运行任何命令）
评审依据：`docs/fable5_review_request.md` + Phase D 复测实证
评审日期：2026-09-29
作答语言：中文

> 与作者无利益关系，直言不讳。引用精确到 `文件:行号`。没有证据的断言写“未见证据”。每条建议落到具体文件/函数/字段。

---

## 一、架构（分层、依赖方向、模块边界）

### 1.1 分层清晰度：良好，个别越界

实测依赖方向与 `REPO_DESIGN.md:79-97` 声称的“单向向下”基本一致，但存在三处实际泄漏：

**[P1] domain/policy.py:77 字符串耦合 services**
`src/pathway_v43/domain/policy.py:71-74` 硬编码 `_ANALOGY_FALLBACKS` 拒因词表，注释承认“避免 domain → services 反向依赖”但实际是脆弱的字符串契约。`services/donor_applicability.py` 若改拒因字面量，`decide_prediction_route` 分支逻辑静默失效。
建议：将拒因枚举提到 `domain/models.py`（纯常量），或 `decide_prediction_route` 改收结构化 `eligibility.status/fallback_reason`，不依赖字面量对齐。

**[P2] workflow/nodes.py:1-73 层间职责下沉**
节点层作为编排适配，导入下层合理；但 `workflow/nodes.py:444` 附近 `call_model` 构造 `task_user_payload` 时直接操作 MoleCode/donor 细节（`services/prediction.py:356-400`），职责下沉不彻底。LangGraph 节点应是“调用 services 并转换 State”的薄层。
建议：将 `task_user_payload` 全部逻辑下沉到 `services/prediction.py`，节点只传 State 字段。

**[P3] vendor/molecode 命名空间隔离不充分**
`src/pathway_v43/vendor/molecode/` 随仓第三方代码未加子包隔离符，导入时与标准库命名空间平级。若依赖另有同名包，存在优先级冲突风险。
建议：重命名为 `_vendored_molecode` 或在 `vendor/__init__.py` 显式声明 `__all__ = []` 并文档标注“非公开 API”。

### 1.2 “多步路径预测”缺失与过度工程

**缺失：**

1. **frontier 全局优先级调度**：`domain/policy.py:select_frontier` 只按 `seq`（创建序）FIFO 展开，无跨父节点的全局优先级（如优先展开高可信度分支）。298 题单步外考未暴露，多步时会陷入宽度优先盲目展开。
   证据：`docs/EC298_PHASE_D_RETEST_REPORT.md:88` 冻结 `max_depth=1`；`ARCHITECTURE.md:99` 承诺“frontier 按创建顺序展开”但未说如何应对多步竞争路径的资源分配。

2. **路径级概率校准**：`domain/models.py` 定义 `confidence_band`（定性），`ARCHITECTURE.md:101` 承认“路径整体概率须在独立校准后才能输出”，但 `storage/` 与 `output/` 无校准实现。多步累积不确定性无量化依据。

**过度工程：**

1. **ArtifactStore 不可变产物存储**：`storage/artifact_store.py` 每个 task_id 持久化 retrieval/prediction/validation JSON。单步外考 298 题已见语料直通 112 题零调用（`docs/EC298_PHASE_D_RETEST_REPORT.md:99`），大量幂等读无 IO 收益。若改为内存 LRU + 选择性落盘（仅调用模型的任务），可减少文件碎片。
   反驳前置：幂等恢复确需持久键，但当前粒度（每检索结果一个 JSON）vs 实际复用率不匹配。

2. **双 identity 块（run_identity + batch_identity）**：`storage/run_identity.py` + `src/pathway_v43/batch.py:build_batch_identity` 功能重叠。batch 场景下 run_identity 已含代码/资产/策略全量，batch_identity 的 58 键扁平结构是冗余投影（`docs/EC298_PHASE_D_RETEST_REPORT.md:73-79` 对比发现唯一差异就是一个 bool）。
   建议：batch_identity 只保留 `route_id -> run_id` 映射 + 共享策略哈希，run_identity 作为唯一身份源。

---

## 二、Prompt（协议提示词与组装）

### 2.1 职责切分：清晰但有遗漏交待

三协议职责正交：

- `configs/prompts/ranker.md:9`：既有候选间裁决，铁律禁止虚构 evidence_id
- `configs/prompts/analogy_editor.md:26-34`：受限编辑，四种操作 + 映射一致性
- `configs/prompts/novel_proposal.md:13-18`：受约束新提案，外源元素白名单

**[P1] 未定义 reasoning_effort=max 的含义**
`src/pathway_v43/adapters/llm_client.py:18-19` 提到 `reasoning_effort` 由批次身份冻结，但三份提示词均未说明 effort=max 对输出格式/长度/结构的要求。若模型返回纯思考块 + 空决策，`services/prediction.py` 解析器契约未覆盖此形制。
建议：在提示词首段或 system prompt 显式写明“输出单个 JSON 对象，思考过程可选但决策字段必须完整”，与 `request_params` 文档交叉引用。

**[P2] temperature 未设的语义冲突**
`src/pathway_v43/adapters/llm_client.py:17-18` 注释“缺省不发 temperature…按官方默认 temperature=1.0 运行”，但三份提示词都有确定性要求（ranker 的 order 契约、analogy 的映射一致性、novel 的元素守恒），却容忍 temperature=1.0 抽样噪声。Phase D 复测 8 题“无任何 D1 召回差异”的分歧只能来自模型抽样（`docs/EC298_PHASE_D_RETEST_REPORT.md:42-44`）。
建议：文档明确“协议设计容忍抽样变异，单次 run 不保证可复现；冻结实验需显式 temperature=0”，或在 `PREDICTION_POLICY_DEFAULTS` 加 `default_temperature: null`（显式记录“未设即提供方默认”）。

### 2.2 组装链完整性：冗余字段，缺环校验

组装链 `services/prediction.py:137 build_prediction_task -> :356 task_user_payload -> workflow/nodes.py:616 _prompt_for`，任务书包含 ancestry / siblings / donor / candidates / discipline / budget。

**冗余**：`ancestry[].display_name`（如“S211”）由 `domain/pathway.py:display_name` 按结构计算，任务书注释承认“仅冗余视图 —— 不得据展示名反推来路”（`src/pathway_v43/services/prediction.py:87`），但仍序列化进每次模型请求。多步时该字段累积无用。
建议：移除 `display_name` 或改为可选 debug 字段。

**缺失**：祖先链 `evidence_hash` 校验。`src/pathway_v43/services/prediction.py:95` 记录 `evidence_hash`，但组装时未与 ArtifactStore 中检索产物交叉核对哈希一致性。若账本与产物因人工修改不同步，任务书引用陈旧证据。
建议：`build_prediction_task` 入口加断言 `store.get_event(ev.event_id).evidence_hash == artifacts.read(retrieval_task_id)["hash"]`，不匹配抛 `TaskIntegrityError`。

### 2.3 Prompt 版本机制：足以复现，缺变更检测

`src/pathway_v43/adapters/llm_client.py:119-134 prompt_versions` 对三份 `.md` 计算 SHA256，写入 `run_identity.prediction.prompt_versions`（`src/pathway_v43/storage/run_identity.py:129`）。身份变更拒绝 resume（`src/pathway_v43/storage/run_identity.py:143-150`）。
机制充分：prompt 内容变更 -> SHA 变化 -> 新批次身份 -> 不复用旧检查点。

缺失：无 prompt 变更的前向兼容策略。若修 prompt 只影响解析（如加可选字段），旧 run 响应产物仍可读，但当前设计强制全量重跑。
建议（非关键路径）：为向后兼容修订引入语义版本，`run_identity` 记录 `(sha256, semantic_version)`，resume 时只拒绝 breaking 差异。

---

## 三、System design（并发、幂等、账本、身份）

### 3.1 并发与容错：设计自洽，实测未达标

**BatchCoordinator 机制**（`src/pathway_v43/batch.py:15-19`）：40 worker subprocess 并发，共享只读代码/资产 + 持久闸门（`adapters/rate_gate.py:FileRateGate`），每 worker 独立 run 目录 + SQLite，崩溃 worker 按未完成路线恢复，不重发已落盘请求。

**幂等点**（`src/pathway_v43/workflow/nodes.py:1-11`）：

- retrieve_reactions: 先读 `results/<task_id>/retrieval.json`，命中复用
- call_model: 查同键 `prediction.json`，已有跳过请求
- commit_pathway: `PathwayStore.submit_event` 同键幂等，不同内容抛 `EventConflict`

**问题 [P1] 实测峰值未达 40**
Phase D 复测 C0 峰值 33、D-3 峰值 32（`docs/EC298_PHASE_D_RETEST_REPORT.md:104`），原因：“298 题中 112 题 recorded 确定性直通（无模型调用），需要模型的题目在补位调度下的重叠不足以填满 40 槽”（`docs/EC298_PHASE_D_RETEST_REPORT.md:260-262`）。
归因正确但设计暴露缺陷：recorded 直通题（37.6%）占比过高 + 无发车屏障 -> 工作分布不均。
建议：短期文档承认“recorded 占比高的题集并发度受限，40 槽为理论上限”（已在 `docs/EC298_PHASE_D_RETEST_REPORT.md:264` 披露）；中期 recorded 题不占 worker 槽（同步处理批量提交），或引入“待模型调用队列”与“确定性处理队列”双轨。

**问题 [P2] FileRateGate 跨进程持久化竞态**
`src/pathway_v43/adapters/rate_gate.py` 共享闸门文件，40 worker 并发读写 `peak_in_flight` / `issued` 计数，未见互斥锁（flock）或原子操作证据。虽 Phase D 复测“闸门全程未停止”（`docs/EC298_PHASE_D_RETEST_REPORT.md:110`），但高并发下存在丢失更新风险。
建议：在 `FileRateGate._increment_issued` 实现 `fcntl.flock` 文件锁 + 读-改-写原子段，或改用 SQLite 计数表。

### 3.2 run_identity / batch_identity 粒度：过多，实际只差一键

Phase D 复测披露：“两臂批次身份 58 键唯一差异 = `prediction_policy_overrides.reactant_similar_enabled`”（`docs/EC298_PHASE_D_RETEST_REPORT.md:67-68`）。设计意图正确，但扁平化 58 键存储冗余：`batch_identity` 与 `run_identity.strategy` 的 `max_depth/max_expansions` 等字段重复（`src/pathway_v43/storage/run_identity.py:124`）。
建议：batch_identity 只保留共享策略的哈希指纹 + 差异键，不展开全部配置。

### 3.3 PathwayStore + ArtifactStore 语义：清晰，验证位置正确

PathwayStore（`storage/pathway_store.py`）：可变账本。ArtifactStore（`storage/artifact_store.py`）：不可变产物。
验证门禁位置（`src/pathway_v43/workflow/graph.py:86`）：`validate_products -> adjudicate_candidates -> commit_pathway`，确保脏数据不进账本。证据：`src/pathway_v43/validation/gates.py:127-150 validate_event_products` 在 commit 之前执行，Phase B 修复后 recorded 卡资格在四处共用同一判据（`src/pathway_v43/domain/policy.py:166-198 recorded_eligibility_reasons`）。

小瑕疵：`adjudicate_candidates` 草稿（stage=draft）与最终（stage=final）语义在 `src/pathway_v43/services/report_adjudication.py:18-19` 说清楚，但 `src/pathway_v43/workflow/graph.py:15-16` 注释只写草稿固定，未说明何时升最终。
建议：`workflow/graph.py:15-16` 补注释草稿与最终的调用时序。

### 3.4 预算体系：真正约束行为

`src/pathway_v43/domain/policy.py:84` 的 `llm_remaining / proposals_remaining` 直接影响 `decide_prediction_route` 返回值（`:109-110`、`:128`、`:155`），耗尽时不进模型。证据：Phase D 配置 `max_llm_calls=3/题、max_proposals=1/题`（`docs/EC298_PHASE_D_RETEST_REPORT.md:87-88`），复测 C0 187 调用（185x1+1x2）符合预算分配（`docs/EC298_PHASE_D_RETEST_REPORT.md:99`）。预算耗尽的题标记 `awaiting_prediction` 或 `budget_exhausted`（`src/pathway_v43/batch.py:55-57` 合法终态）。

费用账（`src/pathway_v43/batch.py:26-28 api_account`）：汇总 issued/响应/429/孤儿/token/费用，但报告承认“须服务商账单回填核对后费用门才可报绿”（`docs/EC298_PHASE_D_RETEST_REPORT.md:212-217`）。当前只是记账，真实约束靠 `batch_cost_cap_cny`（Phase D 设为 null）。
建议：`api_account` 补充 estimated 标签，明确区分“根据 usage 估算”与“已对账”。

---

## 四、Workflow（LangGraph 节点与路由策略）

### 4.1 状态机：经核查无死角

流程图（`src/pathway_v43/workflow/graph.py:5-19`）：START -> normalize -> select_frontier -> retrieve -> classify（四分支 validate / prepare / mark_awaiting / mark_dead_end）-> adjudicate -> commit -> select_frontier 循环 -> export -> END。

路由函数（`src/pathway_v43/workflow/routing.py`）六个覆盖全部条件边。曾怀疑 `condition_fit=conflict` 唯一路径会导致卡住，经核查：`mark_dead_end` 后记账 + `select_frontier` 取兄弟或 export，语义正确，非死角。误报撤回。

`mark_awaiting` / `mark_dead_end` 合法停留完备：`src/pathway_v43/batch.py:55-57 LEGAL_RUN_TERMINALS` 含 completed / already_completed / awaiting_prediction / budget_exhausted / invalid_input，与 `domain/policy.py:27-29` 的 OUTCOME 常量对齐。

### 4.2 策略与提示词“两层决策打架”：未见冲突

`domain/policy.py:classify_evidence` 与 `decide_prediction_route` 是确定性预筛选，决定是否进模型、进哪个协议。模型提示词是任务职责说明，不重复做分级。recorded 永不进模型（`src/pathway_v43/domain/policy.py:105-106`），多条可用 recorded -> rank（`:114-118`），类比资格门通过才进 analogy_editor。

唯一边界模糊：`configs/prompts/novel_proposal.md:3-4` 括号内“或映射找回失败后策略允许受约束提案”与 `src/pathway_v43/domain/policy.py:154-158` 的 `allow_novel_on_mapping_failure` 重复表述。
建议：提示词只说职责，策略条件留给 `policy.py`。

### 4.3 D1 相似通道开关设计：阈值合理性未见证据，默认 false 正确

开关：`prediction_policy_overrides.reactant_similar_enabled`（`src/pathway_v43/domain/policy.py:54`，默认 `false`）。参数：threshold 0.45 / top_k 16 / max_analogy_donor_candidates 3（`:55-56`）。

Phase D 复测（`docs/EC298_PHASE_D_RETEST_REPORT.md:16-17`）：D-3（开启）vs C0（关闭）hit@1/3/5 = 132/174/182 vs 136/182/186，净差 -4/-8/-4；配对 @5 四格 D-3 赢/输/平 = 4/8/286；3 题可归因到 D1（novel->analogy_edit 转路由后落空），8 题无召回差异纯抽样噪声（`:42-44`）。

评价：阈值 0.45 选择依据未见证据（`docs/PHASE_D_D1_PARAM_CARD.md` 未读到）；top_k=16 与 max_analogy_donor_candidates=3 的关系未见说明（为何不直接 top_k=3，若是召回后筛选则筛选规则未见）。默认 false 正确，复测证据不支持改默认值（`docs/EC298_PHASE_D_RETEST_REPORT.md:45-47`）。

---

## 五、Datachain（检索证据 -> 预测任务 -> 模型响应 -> 裁决 -> 账本提交 -> 导出）

### 5.1 Schema 显式性与校验：充分，一处缺失

显式 schema：任务 `PREDICTION_TASK_SCHEMA_VERSION=v43-prediction-task-3`（`src/pathway_v43/services/prediction.py:36`）、响应 `v43-prediction-response-1`（`:38`）、裁决 `v43-report-adjudication-2`（`src/pathway_v43/services/report_adjudication.py:51`）。校验点：`validate_card_for_reporting` + `validate_adjudication_payload`（写入前与读取时双重执行）。

缺失 [P1]：检索结果无 schema 版本字段。`services/reaction_finder.py` 返回证据卡字典未见 `schema_version`。若检索实现变更字段结构，下游无法区分旧新格式。
建议：返回值加 `{"schema_version": "v43-evidence-card-1", "cards": [...]}`，任务书组装时校验版本兼容性。

### 5.2 来源链端到端可审计：Phase D R2 已修复

来源链：`report_adjudication.json products[reportable=true]` 按 `report_rank` 排序 -> merged 答卷 `predicted_products` -> `export_v3` 三字段答卷。

Phase D R2 修复前：r1 从 merged 不存在的 `steps[].source` 取来源导致全空；deepdiff 读不存在的 `report/entries` 键计入全部候选（max 505）而非可报告产物（`docs/EC298_PHASE_D_RETEST_COMBINED_REVIEW.md:39-41` F1/F2）。修复后从裁决产物重建并交叉核对，填充率 C0 286/286、D-3 285/285，首位不匹配 0 题（`docs/EC298_PHASE_D_RETEST_REPORT.md:127-136`）。修复到位。
建议：`output/export_v3.py` 导出时直接从裁决产物提取来源写入 `steps[].source`，避免外部脚本重新组装。

### 5.3 Usage/费用/peak 采集口径：一致，有一处未来风险

transport 结构（`src/pathway_v43/adapters/llm_client.py:62-88 LLMResponse`）：`sent_at_epoch/done_at_epoch` epoch 墙钟（`time.time()`），`elapsed_s` 单调时钟差，`usage` 归一化六字段（`:94-108`），`http_attempts` 逐条记录。Phase D 各 187 调用 usage 齐全（`docs/EC298_PHASE_D_RETEST_REPORT.md:101-102`），峰值按同一函数半开区间计算（`:254-257`）。

未来风险 [P2]：`normalize_usage` 依赖提供方 `prompt_tokens_details.cached_tokens` 字段名（`:104`），若 API 变更则静默失败。
建议：加防御性日志“若 raw 非空但提取全 None 则 warn usage schema 可能已变更”。

---

## 六、Transfer（跨步传递：ancestry/path_id 去重与循环门禁）

### 6.1 引用完整性：可回查完整路径，resume 不断裂

`domain/pathway.py:ancestry_chain` 从 `path_id` 递归查 `parent_path_id` 直到根；`services/prediction.py:76-99 _ancestry_task_block` 每步含 path_id / parent_path_id / event_id / evidence_id，可从任意产物反查到根。resume 指纹（`src/pathway_v43/storage/run_identity.py:143-150 identity_fingerprint`）排除时间字段，只校验策略/资产/代码，path_id/event_id 为账本主键不因 resume 重生成。Phase D 两臂一次跑完无 resume（`docs/EC298_PHASE_D_RETEST_REPORT.md:110`），但测试套件含 resume 端到端（`:57` 456 passed）。

小瑕疵：`ancestry_chain` 若遇环形引用会无限递归。
建议：加防御性深度上限（如 `MAX_DEPTH_HARD=64`，`src/pathway_v43/validation/gates.py:23` 已定义），超出抛 `PathIntegrityError`。

### 6.2 去重门与循环检查粒度：正确，旧案已修复

`src/pathway_v43/validation/gates.py:134-150 validate_event_products`：事件内去重（`seen_in_event`）、兄弟去重（同父路径既有产物）、路径内循环（`is_in_path_cycle` 回到祖先链任一分子则拒）。旧案“金标被查重门毙”现已修为兄弟查重；跨卡去重在裁决层单独定义（`src/pathway_v43/services/report_adjudication.py:85 cross_card_dedup` 占一个位次保留全部来源）。粒度正确。

### 6.3 元素门禁护栏：在正确粒度

`src/pathway_v43/validation/gates.py:93-124 gate_element_changes`：重元素仅允许白名单外源 O，其余拒；O 允许 +<=2 超出拒；元素减少一律允许；delta 留痕 `ProductVerdict.exceptions`（`:38`）。适用范围 `check_elements` 仅模型提案（analogy/novel），recorded 不检查。注释明确“不把元素计数当作机理证明”（`:6-7`、`:108`）。Phase D 8 题 `validation_rejected_gold` 全部是编辑门禁（AtomTool 拒绝）而非元素门禁（`docs/EC298_HIT1_ATTRIBUTION_REPORT.md:16-17`、`:84-98`）。未见“该拦没拦/不该拦拦了”证据。

---

## 七、综合建议与优先级

### P1

1. FileRateGate 跨进程竞态（`src/pathway_v43/adapters/rate_gate.py`）：加 `fcntl.flock` 或改 SQLite 计数表。
2. 检索结果无 schema 版本（`src/pathway_v43/services/reaction_finder.py`）：加 `v43-evidence-card-1`。
3. domain -> services 字符串耦合（`src/pathway_v43/domain/policy.py:71-74`）：拒因枚举上移 `domain/models.py`。

### P2

4. 并发度未达 40（`src/pathway_v43/batch.py`）：recorded 双轨或待模型队列。
5. prompt 未定义 reasoning_effort=max（`configs/prompts/*.md`）：补充输出格式要求。
6. temperature 未设语义冲突（`src/pathway_v43/adapters/llm_client.py:17-18`）：文档明确容忍变异，冻结实验显式 temperature=0。
7. D1 top_k=16 vs max_analogy_donor_candidates=3 关系（`src/pathway_v43/domain/policy.py:56-57`）：文档说明分开计数原因。
8. normalize_usage 防御（`src/pathway_v43/adapters/llm_client.py:94-108`）：加 schema 变更警告。

### P3

9. ArtifactStore 粒度优化：内存 LRU + 选择性落盘。
10. batch_identity 冗余：改为指纹 + 差异键。
11. ancestry 冗余字段 `display_name`（`src/pathway_v43/services/prediction.py:87`）：移除或 debug 可选。
12. ancestry_chain 环形防御（`domain/pathway.py`）：加深度上限。

---

## 八、结论

### 8.1 架构成熟度：工程可交付，科学待验证

优点：分层清晰依赖基本单向；幂等完整（456 passed 含崩溃注入）；账本+产物语义明确验证位置正确；提示词正交版本可复现。

短板（目标 hit@1 >= 60%）：当前 Phase D C0 实测 45.6%（136/298），距目标 14.4pp（43 题）。162 题失分归因（`docs/EC298_HIT1_ATTRIBUTION_REPORT.md:11-21`）：27 题模型有金标卡可选但选错、33 题检索无金标、8 题编辑目标匹配但被门禁拒、61 题生成阶段离线不可判。四项 Phase A/B/C/D 改动均无 @1 提升证据（`:25`）。

架构不是瓶颈，检索覆盖与模型选择是。以上三项均不需要改架构，当前设计已充分支持。

### 8.2 与实测证据一致性

全部数字均可在 `docs/EC298_PHASE_D_RETEST_REPORT.md`、`docs/EC298_PHASE_D_RETEST_COMBINED_REVIEW.md`、`docs/EC298_HIT1_ATTRIBUTION_REPORT.md` 找到依据。未能验证：D1 阈值 0.45 选择依据（`docs/PHASE_D_D1_PARAM_CARD.md` 未读到）；recorded 112 题 qid 清单（报告只给总数）。

### 8.3 最诚实结论

系统架构本身已达工程交付标准，P1/P2 可在 2-4 周修复。距 hit@1 >= 60% 差距在检索覆盖（33 题/11.1%）、模型裁决（27 题/9.1%）、编辑宽松度（8 题/2.7%）。Phase D D1 通道未能证明增益，默认关闭正确。

评审人声明：静态代码与文档，未运行命令，未访问远端凭证，未修改仓库文件。引用精确到文件:行号，未见证据已标注。
