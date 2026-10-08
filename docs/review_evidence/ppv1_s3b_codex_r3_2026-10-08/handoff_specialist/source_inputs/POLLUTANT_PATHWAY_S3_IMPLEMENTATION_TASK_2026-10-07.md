# pollutant_pathway_v1：S3 工程实施任务书

日期：2026-10-07。仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。任务基线：`00e509a974b40a7c9779fcd35e53b16637a13d60`（R8）。

**授权与目标：用户已拍板“开干 S3”。R8 复审已放行 S3 工程，P1=[]；本任务不再开 S0–S2 R9。S3 要把已经验收的状态、假设、条件、审核和事件存储接成可有限探索、可恢复、可审计的执行流程。建议分 S3a/S3b 两批，每批完整走“实施→主会话核对→mimo→Codex 复审”。S3a 通过只表示底座通过，完整 S3 放行在 S3b 集成验收后裁定。**

本文件展开全部必需需求；实施 agent 阅读本文与当前 AGENTS.md 即可开工，下面绝对路径用于核对来源、已关闭问题和现成接口。若旧规格正文与 §17 冲突，以 §17 裁定为准；若本文与当前 AGENTS.md 的数据、费用及操作边界冲突，遵守后者并报告具体冲突。判据尚未正式冻结，科学性能 pending；本任务不代表化学判据冻结或 S4/S5 启动。

## 1. 必读与基线核对

1. `/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md`：操作红线、单实施 agent 串行派工、评审循环与阶段交接。
2. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md`：§17 优先；§3、§4、§6–§9、§11–§12 为 S3 原定任务和验收出处。
3. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R8_2026-10-07.md`：§2 状态恢复/首消费关闭，§3 ledger/put_state 边界，§5 八项落字，§7 放行范围，§8 交接。
4. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r8.md`：原只读化学回应；程序结论以 R8 独立执行互证为限。
5. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R8_2026-10-07.md`：既有入口矩阵、回归与边界登记。
6. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_request.md`：当前 v8 请求；下一批按本书 §10 更新，不把旧回应改写成新验证。
7. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r8_codex_2026-10-07/README.md`：永久证据入口；其 `execution_specialist/` 为安全 G01 白名单与旧执行证据，`chemical_matrix/`、`storage_current/`、`conditions_current/` 为分段控制。
8. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r7_codex_2026-10-07/README.md`、`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r6_codex_2026-10-07/README.md`：历史原反例与正控入口，只读；脚本须复制到新 tmp，禁止原地写库/日志。

基线现状：PPV1 工程回归 536 passed/0 skipped；R8 新增 28 项在当前全绿、父提交 14 failed/14 passed，均为行为翻转，但不是 14 个旧错误 R6。安全隔离 G01 历史为 1138 passed/8 skipped/17 deselected，R7 历史 1110/8/17 单列。这些是历史工程结果，不是 S3 当前目标数字，也不代表 dev（B1 环境中间步骤）或 298（RHEA 通用酶学）科学性能。

开工先记录实际 HEAD、工作区差异和父提交。预计已有未跟踪审核报告、mimo 回应与永久证据，AGENTS.md 还可能有用户授权的未提交更新：保留，不删除、不顺手暂存。若源码相对基线已有未说明改动，确认来源并在新隔离 checkout/worktree 实施，不能覆盖别人的工作。

## 2. 范围与分批边界

### 2.1 必须实现

- PPV1 独立的任务/搜索身份、语义 attempt、持久 SearchAction、有限预算和停止原因。
- 队列选择、备选假设探索、共同产物 deferred 与备选反应 deferred 的分别激活、条件/依赖继承与显式场景转换。
- 并发认领、预算预约、请求预登记、不可变 artifact、事件/搜索状态的事务一致性和四个崩溃边界的恢复。
- 新模型假设协议与有界格式反馈；真实 provider 默认 off，scripted/off 规则级工程验收。
- 固定 AtomTool 的真实执行输出→供体诊断→center evidence converter→audit→admission→事件提交的生产调用链。
- E01–E04、C06 搜索集成、H04 调度及 H05–H08；继承 S0–S2 合法、unknown/partial 与损坏拒绝控制。
- 本书 §8 的 R8 P2 文档同步，尤其 scope 归属更正；本书 §9–§10 的回归、证据和交付。

### 2.2 不做

不修改冻结 legacy/G2/AtomTool 的化学判定、rank 资格、排序、原预算含义、旧任务协议或评分。可在公共 runner 增加显式 PPV1 分流，但 legacy 分支行为保持。不得把 PPV1 引到 legacy 的 CN 状态、PathwayStore 或旧 reportable 提交流程。

不做 S4 的终点推断、路径原生正式导出/v3 有损适配，不做 S5 评测器、真实数据集、留出/阈值冻结与性能实验。本轮为审计写出的搜索记录/合成图不是提前完成 S4。本轮仅输出用于验收的最小搜索运行摘要、持久refs、预算和停止原因；搜索停止不得变成“终产物/矿化/解毒”结论，缺独立终点证据保持未知。

不访问真实金标、题面、封存逐题 run，不动 dependingv4；不调用在线答案服务，不发真实付费模型请求，判分零 LLM。mimo 请求仅规则级合成示例，由主会话按既有通道送审；实施 agent 不自行调用外部模型。

不新增机制库、酶活性认证、电子转移硬门或来源真实性认证，不把未覆盖科学问题升级为 S3 工程前置。遇到原契约内公共链真缺陷应留证并修复；一般增强和已登记保守过拒仍列后续，不借本任务无限扩边。

### 2.3 两批交付

| 批次 | 实施内容 | 批次边界与可 review 结果 |
| --- | --- | --- |
| S3a：持久搜索底座 | 新搜索/任务/attempt/request 身份与 schema；配置实际计数；认领/预算事务；artifact 校验；低层提交恢复协议；停止原因；四崩溃、H05–H08 和 E03/E04 底座夹具；§8 文档同步 | 用公开底座接口和 scripted/fake driver 完整验证。`workflow.runner.start_run/resume_run` 对 PPV1 仍 fail-closed，legacy 仍可用；队列化学集成和生产中心证据明确未交付，不称完整 S3 |
| S3b：调度与生产链接线 | 新假设模型协议/有界格式反馈；冻结池/备选/两类 deferred；条件依赖/场景转换；固定工具中心证据链；PPV1 独立 runner start_run/resume_run；全 S3 集成 | 复用已审 S3a 底座，显式启用 PPV1 分流；E01–E04、C06、H04–H08 端到端与所有继承控制。交付完整 S3，由 Codex 裁定放行下一阶段 |

主会话串行派单个实施 agent；S3a 审核通过再启动 S3b。批次内可按模块组织提交，不能以“先解锁跑起来”为由提前解除 fail-closed。每批未完成部分逐项标明，不拿底座绿冒充生产链绿。若实际选择一批实现全部 S3，须覆盖同一完整验收面，不减少恢复/并发项；不要边实施边加第三类科学阶段门。

## 3. 固定入口与继承契约

现成源码挂接点（绝对路径）：

- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/profile.py`：profile 版本/开关与 P0-3 草案，S3 新族在 `contract_versions()` 登记。
- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py`：`build_chemical_state`、`ChemicalState.from_dict`、`validate_state_object`、`strict_identity_of`。
- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py`：context 内容校验、条件评估、派生及历史快照；路径相同分子不同来路不可共用覆盖上下文。
- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/hypothesis.py`、`events.py`、`store.py`：假设、完整事件/报告投影/展开计划及 `PollutantPathwayStore.submit_event` 首提/重放契约。
- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py`：`check_edit_against_donor`、`center_evidence_from_donor_diagnostic`、`audit_hypothesis`、`decide_admission`。
- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/pool_audit.py`、`substrate_profile.py`、`provenance.py`：池审计/底物档案/支持来源。
- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/workflow/runner.py`：`start_run`/`resume_run` 当前分别经 `_refuse_undelivered_profile` 拒 PPV1；S3b 必须在拒绝旧流前明确分流。
- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/workflow/graph.py`、`nodes.py`：既有 LangGraph 职责；新 PPV1 函数确定性接入，无需重写自由工具 multi-agent。
- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/storage/run_identity.py`、`artifact_store.py`：身份与 artifact 设施；复用前确认新任务/版本绑定，不能继承旧 CN-only 任务键。
- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/atom_tool.py`：冻结工具，仅调用，不修改；所需 vendor 完整复制入隔离源。

开工先列适用入口矩阵：build/parse/from_dict/derive/audit/首次 submit/replay/start/resume/action claim/恢复/模型响应消费；登记每处消费的对象、身份、版本、事实与证明范围。模块与接口名称可按仓内风格调整，下面行为契约固定，不要求照着造一批空接口。

1. **状态与上下文首消费继续验证。** restore/direct dataclass/派生/任务组装/audit 消费前用现成同源内容验证，raw 守卫、raw→strict 同图、版本、事实与历史快照都不能被队列/缓存绕过。损坏即结构化失败；不清洗 raw 后继续 full，也不当前条件重评旧边。
2. **ledger 首消费绑定不能后移。** 调度/恢复使用已存 state/appearance/hypothesis/event 时闭合对应内容/版本/身份和 distinct occurrence 集合；事件首提/重放继续经过 `submit_event` 校验。`put_state` 返回 None/无异常不是旧行完整性证书，`get_state` 读视图也不证明 appearance_hash 或来源真实性。不得因先 put 成功而豁免实际复用行。
3. **证明不能扩范围。** strict、中心、元素/电荷、条件与来源分轴；缺 proof/映射/参与物覆盖时保持 unknown/partial。center license/scope 存在不等于适用；补全只解除声明的覆盖轴，不核实机制/样品纯度。
4. **失败诊断不是通过。** `execution_ok=False` 诊断的三个判定字段 `reaction_center_match/strict_target_match/legacy_cn_match` 都为 None；`diagnostic.center_evidence={}`，converter 仍返回元数据与 `center_match=None`。新 caller 不得把 None 当通过，不得吞 `AuditContractError` 后继续本次 admission/submit；可记录结构化失败并调度另一假设。
5. **版本与恢复分离新旧。** 新搜索/任务/模型/反馈/调度/恢复策略进入 run identity；缓存键绑定其实际依赖。语义改变升版本并登记待审，不改原版本值。profile/未知 schema/代码或策略身份不一致恢复 fail-closed；不原地切换旧 run、不猜迁移。legacy 同版本恢复与旧预算语义保持。

## 4. S3a：身份、预算、认领与恢复

### 4.1 持久身份和对象

SearchAction 至少保存：`action_id/run_id/parent_path_id/context_ref/hypothesis_id_or_pool_ref/action_kind/parent_search_revision/policy_version/status/attempt_refs/outcome_ref/budget_reservation_ref`。action_kind 覆盖 retrieve、decide、expand_hypothesis、activate_deferred、scenario_transition；状态能明确表示 pending/claimed/done/deferred/blocked，失败及未知请求状态不得假装 done。若增加状态，写迁移/消费语义，不模糊并发所有权。

每个语义尝试有持久 `expansion_attempt_id`：恢复继续旧 attempt，新备选换 attempt。决策任务绑定 frozen_pool_digest、父 context 与所需局部搜索快照；单假设验证/裁决绑定 hypothesis_id/attempt。严格原始化学状态、池/工具/提示词/反馈/策略版本进入相关任务键；同键异内容明确冲突，artifact 不覆盖。parent_search_revision 只进实际依赖局部搜索状态的键，不进无关底物特征缓存。

事件幂等继续绑定 run、parent_path、hypothesis、context 和事件语义，不能因 retry/claim owner/attempt 序号变化重复建事件。保留路径来路，不按 CN 归为单一路径；不同 parent/context 的同 hypothesis 不是全局互斥对象。

### 4.2 用现成十个上限落实计数

S2 草案在 profile.py 的版本为 `ppv1-search-limits-2-proposed`。S3 登记实际可执行版本与计数规则，不凭空重造键/范围；配置完整往返可重放，未知键、错误类型、负数/越界拒绝。下列默认用于规则级小夹具，不是科学最优参数：

| 键 | 默认 | 允许范围（含端点） | 必须落账的单位 |
| --- | ---: | ---: | --- |
| max_alternative_hypotheses_per_parent | 2 | 0–8 | 同父路径被选择探索的不同备选假设数，不混为 attempt 数 |
| max_attempts_per_hypothesis | 2 | 0–8 | 单假设语义尝试数，含首次，恢复同 attempt 不再扣 |
| max_product_expansion_width | 2 | 0–8 | 单事件继续展开的产品宽度，不截断完整参与物/共同产物事件 |
| max_search_depth | 3 | 0–10 | 路径反应边深度；0 不展开产品；阶段转换另计 |
| max_total_search_actions | 10 | 0–1000 | run 级 action 执行/预约数，含 scenario_transition；队列待办不可伪装已用 |
| max_scenario_transitions | 2 | 0–4 | 有显式支持的阶段转换次数，不是反应边 |
| max_reopens_per_hypothesis | 1 | 0–3 | 同假设无新信息重开上限；与总 attempt 双重约束 |
| max_real_model_requests | 0 | 0–10000 | 真实 provider 的请求预登记数，失败/超时/悬空均占额 |
| max_retrievals_per_parent | 1 | 0–4 | 每父路径实际检索数；复用缓存不重复计 actual retrieval |
| max_retrievals_total | 64 | 0–4096 | run 级实际检索数 |

具体预约/consume/release/失败计数边界，尤其 action、attempt、重开、格式反馈的关系，开工写预算账表并让 fixture 逐步复算。上述单位不允许靠内存 counter 或最终 snapshot 自报；持久记录是事实源，snapshot 是可校验派生值。复用检索不能让新增搜索尝试免费无限，队列创建/去重也不能重复扣已预约 action。真实 provider 请求发出前预登记，真实请求预算0必须阻止网络发送；legacy 有 model 对象时可能把0派生成正数，该逻辑不能进入 PPV1。零预算只阻止确实需要消费该资源的动作，不能看任一个上限为0就全局停：默认真实请求0/off仍允许纯规则或scripted搜索，检索0可使用已有冻结池，转换0不阻普通反应；给适用资源判定的正负控。

停止原因主因优先级继承草案并在 S3 版本登记：`user_stop > budget_limit > depth_limit > no_local_candidate > awaiting_prediction > exhausted_search`；保留同时成立的其他原因/尚未探索集合。零预算、零深度、空池分别做独立夹具，不能用复合夹具早停当三个已测。停止不是化学终点，deferred/知识缺口存在时不称“所有路线都探索完”。

### 4.3 并发与事务

同 action 认领、预算预约与状态转换在事务/唯一约束下只有一方取得执行权。竞争方返回 already_claimed/unchanged 或复用已完成结果，不创建新 attempt/request、不开新事件、不重复扣额度。测试用两个独立连接/进程配 barrier 同时争同 action，不靠顺序调用或 sleep 概率；同时保留不同 parent/context 同 hypothesis 两者均合法的正控。

claim owner/恢复者有可核验执行权，陈旧 worker 不得越权提交或覆盖完成结果。锁超时/SQLite busy 是可见并发结果，不当化学拒绝；重试必须沿原 action/预约身份，不能绕预算。

事件、投影、展开计划、参与物以及必要搜索提交事实保持一致。优先与现成 `submit_event` 在同 SQLite 事务边界接合；若必须多库/artifact 分开落盘，给明确 durable commit record/阶段机/恢复协议证明何处权威，不能用 LangGraph checkpoint 声称跨文件原子。artifact 可先写，但“有文件”不等于事件已提交。

### 4.4 四个强制崩溃边界

| 崩溃位置 | 恢复必须观察到 | 合成验收 |
| --- | --- | --- |
| action 已认领、预约已落账 | 读冻结 action/attempt/预约继续，禁止按当前 revision 重算任务身份或再次扣额 | 强制终止后新进程 resume；事件/request/预约唯一，预算复算相同 |
| 请求已登记、无响应 | 暴露 pending/unknown；不承诺外部 exactly-once，不默发第二请求；若显式重试需新 request 及剩余额度 | scripted/fake provider 模拟边界，登记与发送计数分别记录；`provider_kind` 与 `network_request_count=0` 明示，不能报成真实模型调用 |
| 输出 artifact 已写、事件未提交 | 先验版本/hash/身份，再消费同一 output/attempt 完成；不能重发模型或将草稿当事件 | 字节有效正控、反序列化失败/hash错两负控；事件仅一次 |
| 事件已提交、队列/后续状态未完成 | 由完整权威记录确定恢复剩余状态，事件/产品扩展/request/预算不重复；损坏时保全失败 | 注入提交后终止；合法恢复与 event/ledger 不一致两案分测 |

H07：artifact 不可反序列化或 hash 不符，明确完整性错误、保全输入/原文件，不静默跳过或重跑覆盖。H08：提交事实与 ledger 不一致，保全证据、明确失败/隔离，不默认补事件/修库，更不改旧/封存 run。新活动合成 run 的自动恢复仅按版本化显式策略，使用完整且已验证权威记录留轨迹；不足就失败，不猜数据。

## 5. S3b：队列、条件依赖与模型任务

### 5.1 冻结池与队列

提供等价职责的接口：`schedule_hypotheses(parent,frozen_pool,context,budget)` 产 selected/deferred/blocked+原因；`record_expansion_outcome(attempt_id,outcome,evidence_refs)` 持久化尝试；`activate_deferred(parent,trigger,expected_parent_revision,budget)` 产 activated_ids/unchanged+原因。名字可调整，身份/理由/事务不能省略。

父路径提交一个事件后仍可探索其他反应备选；不只靠 PathInstance.frontier 表示全部搜索。共同产物 deferred 和父底物备选反应 deferred 分别有类型、对象、触发条件/未展开原因。完整事件保存全部已知参与物/产物，报告 K、产品展开宽度或预算不足不得删事件事实。

首选下游无候选，记录 unresolved_continuation，按稳定次序继续可用备选，不改上游真假；明确条件 conflict/审核 violated/方法失败分别记因。有限排序/tie-break、池处理 hash/count/处置/截断仍可重放；input_preview_policy 只能 off/diagnostic且进入run/任务策略身份；off记录未执行及原因，diagnostic只附有限规则诊断。复用conservation_filter_and_rank时不能消费其筛选/排序结果回流改变池成员、档位或原顺序；首次模型/调度消费也沿用该已有规则，不新增隐含G2门。

无新信息不能无限重开；激活用 expected_parent_revision 与可验证 trigger，旧 revision/重复 trigger 明确 unchanged/冲突，不重复安排同 action。循环提案用 action/attempt/重开/深度等持久上限稳定停，留下未探索原因。

### 5.2 条件与依赖实际进入调度

子路径继承父事实/要求/假设/依赖，分支互不污染；下游 exact/recorded 匹配不能洗掉上游 unresolved。环境 essential conflict 留假设、阻止当前场景展开；unknown 可经既有 retain_conditional 在预算内探索，不把请求 condition_compatible 直接标为已相容。空要求/未知覆盖也不能自动 compatible。

场景转换只由用户/来源明确支持，独立 action/预算/记录，仅改变后续阶段，不重写旧边评估。不能从文献观察环境、矩阵“污水”、工具隐式 O2/H2O 或 transformation_class 标签造当前条件。

H04 的共底物循环：有启动供应/再生支持不能自动阻断；缺支持标 unresolved_initial_supply，按显式、版本化策略处理，不能称化学不可能。实现时同时测 supported 与 unresolved 两类、真实继承与重复触发；不要求通量求解器。C06 必须从真实公共调度→审核/准入→提交→子路径证明 unknown 仍保留且有界可展开，不能只复用 S2 admission 单元测试。

### 5.3 模型协议和反馈

PPV1 新任务使用 `proposals[]`：每项一条独立反应假设，内部共同产物集合与 participants/来源/条件/依赖按既有契约；rank_hypotheses 引稳定 ID，不能把模型选择升成 recorded。对工具已确定的产品只能引用，不暗改结构。novel 有界 proposal_context 可参考冻结池或提出池外假设，`reference_hypothesis_ids/output_origin` 明示，不伪造来源。空列表/弃权合法，底物档案独立于 candidates，空池时仍可组装。

只有 JSON 字段/类型、允许 ID、语法契约错误可进格式反馈；为格式反馈登记独立有界policy键、默认值、范围、计数单位与任务版本，可复用适用的既有有限计数但不能把同任务JSON修复轮数当hypothesis语义attempt。反馈策略属于原规格§7.2，S2十个搜索上限并未自带反馈轮数，不把新键说成旧草案字段。每次反馈持久记录输入/错误类别/反馈版本/次数，并受该有限策略及相关请求预算。结构无法解析记结构失败，不能以格式反馈改分子再试到通过；chemical_reproposal 首版保持 off，化学重提案数0/路径unsupported如实披露，不能隐含启用；启用或增加新化学重提案语义不在本任务自动授权内。

模型不直接写 SQLite、frontier、条件事实或策略。真实 provider 默认 off、max_real_model_requests=0，传入模型对象不自动启用/补预算。scripted/fake 可测试模型协议和请求恢复，但网络次数必须0、日志区分 script 调用/请求登记/真实请求；不做付费效果试跑。

## 6. S3b：实际中心证据与 PPV1 runner

### 6.1 固定工具生产链

合成合法编辑必须实际调用冻结 AtomTool（渲染、映射/编辑执行及现有约束），保存真实执行前后/atom_id_map/edits/donor/alignment/expectation/result；固定接：

`AtomTool 真实输出 → check_edit_against_donor → center_evidence_from_donor_diagnostic → audit_hypothesis → decide_admission → build/submit_event → 搜索结果/子路径`。

converter 已在 audit.py 实现，不另手造 verified 中心结论；proof_record/绑定/版本及复算由现成审核消费。证据必须对应当前假设全部被声明覆盖的参与物，不能拿单产品成功外推整反应。供体/映射/模板信息不足继续 unknown/partial，保留 checker scope；这是既有确定性诊断接线，不实现完整机制证明。scripted 模型只提供合法动作/假设数据，不伪造 center proof。

分段负控：合法工具链；工具 execution_ok=False；缺/歧义映射；strict 目标偏离；raw 未登记 CX；proof 更改/跨假设复用；复杂共底物不能只凭配平升级；登记补全 composition-only 边界。契约异常中止本次audit/admission及成功提交；执行失败记录方法失败，不能伪装成功工具结果，允许调度独立备选。普通缺证据/映射的None或空payload不是契约异常或执行失败：由现成audit保留unknown/partial，仍可按既有admission有界探索，不能按“没有反对”授verified。

### 6.2 公开 start_run/resume_run 安全分流

S3b 在 `workflow/runner.py` 明确按 profile 分流到 PPV1 独立执行/存储，再解除对应未交付拒绝；不能只删 `_refuse_undelivered_profile` 让 PPV1 落入随后 legacy CN/PathwayStore/预算派生。legacy 路径本身不改冻结语义。

PPV1 start_run 保存严格 root state、context、池/策略/新版本/搜索预算与 asset/tool/model 身份；resume_run 验完整身份后读取既有搜索/attempt/request/提交记录，不重建或覆盖。未知 profile、未交付批次、身份变动明确拒绝。S3a 使用新底座测试入口，但此双公开入口继续拒 PPV1；S3b 两入口均需真实公共链测试，不能只测内部函数。

run identity 的代码集合按现成 profile 规范消费：只改 pollutant 新包不该影响 legacy 专属身份；若更改共享 runner 等文件，如实登记对身份的影响，不伪称旧身份字节必然不变。新 run 用新根目录，旧 run 不原地切换 profile/版本。

## 7. 分任务验收矩阵

以下每行都要有入口→行为→可执行断言，提供合法/unknown 正控；合成输出不是科学性能。batch 标“a+b”表示 S3a 底座验、S3b 公共链再验，不是未实现集成也算完成。

| 任务/批次 | 验收入口 | 必须行为与证据 |
| --- | --- | --- |
| 身份/E03，a+b | 新 action/attempt/task 创建、artifact 读写、同父换假设、resume | 两假设 task/attempt 不复用旧 decision；context/池/相关版本变化换键；同键异内容拒；同事件重放不多事件；恢复沿已冻结键 |
| P0-3/E04，a+b | 完整配置→预约→执行/失败/恢复→budget 重算 | 十上限/default/range/单位/优先级登记；循环稳定停；内存重置仍从记录复算；缓存检索不重复 actual 检索，新增 action不无限免费 |
| H05，a+b | stop 解析/队列入口 | 零 action预算、零深度、空池三独立夹具；复合原因主因按既定优先级并保留其他原因；合法非零正控 |
| H06，a+b | 同 action 两连接/进程同时 claim | 一方执行/预约，另一方 already_claimed/unchanged/复用；request/event/额度无翻倍；不同父/context同 hypothesis各自合法 |
| 四崩溃，a+b | 强制终止→新进程 resume | 四个明确故障注入点各自关闭重开进程/数据库，读持久reservation/request/artifact/event/action计数、hash/预算/身份；不以事务回滚单案代替四边界；未响应不默发，输出不重算新任务，事件已提交不重复产品扩展 |
| H07/H08，a+b | artifact读/恢复、event/ledger消费 | 不可解析/hash错和权威不一致分案；明确失败/隔离且原证据保全、零猜修；完整合法记录按策略恢复 |
| E01，b | 公共 start_run→首选后续无候选→剩余备选 | B 留事件/attempt/unresolved_continuation，C在上限内继续；不反证上游、不无限重开 |
| E02，b | 两类 activate_deferred及重复/旧revision调用 | 共同产物与备选反应分别激活；预算不足留独立未展开原因；完整共同产物事件不截断；重复触发幂等 |
| C06/H04/条件继承，b | 调度→audit/admission→submit→子路径 | unknown可有界探索且沿途保留；essential conflict阻当前场景；两分支隔离；启动供应supported循环不一律阻断，缺支持unresolved_initial_supply |
| 场景转换，b | scenario_transition action→新context→下一边 | 必须显式支持、扣转换/action预算；只后效；转换次数/深度分账，原边评估保持 |
| 模型协议/反馈，b | rank/proposals parse→冻结假设→固定工具/审核 | 备选与共同产物不混；空列表合法；稳定ID引用；有限格式反馈不修化学结构；真实默认off/0，scripted网络0 |
| 实际中心链，b | 冻结AtomTool→diagnostic→converter→audit→admission→submit | 真工具输出产生可复算绑定证据；合法/缺映射/失败/偏离/损坏proof分段；契约异常中止本次audit/admission/成功提交；执行失败记方法失败不伪装成功工具结果；缺证据/映射None按现成audit保留unknown/partial，可按既有admission有界探索、不授verified；所有已关闭反例及合法控保持 |
| 公开分流，b | workflow.runner.start_run与resume_run | PPV1走独立严格状态/ledger/搜索；legacy G01功能保持；profile/身份不符拒；不因传model把PPV1真实0预算变正 |
| R8继承，a+b | restore/direct/context derive/首提/replay | R7两P1及R6五组原反例仍拒/诚实partial；source_refs坏appearance实际复用不可信；合法同图/手性/CN-only/unknown/多来源幂等保持 |
| G01，a+b | 新source白名单的安全隔离旧工程回归 | 按§9逐项披露skip/desel/缺依赖；不拿旧1138充新执行，不为凑数读真实评价/旧v4/原v3资产 |

复合探针有拒绝就可能早停：逐段 capture 或分案记录实际到达的内部分支。进程 exit0/顶层继续、字段存在、测试数都不替代逐案断言；缺接口/字段/表红与实际行为红分类分开。

## 8. R8 P2 文档同步清单（本轮交付项）

在新规则请求/新交付书精确落字，保留旧 R6/R7/R8 报告与永久证据原样，不回写历史“修正”旧哈希。优先④；可只更正请求文字归属以避免不必要 schema 变动。八条均是范围/文字同步，不凭缺一句新增化学功能门：

1. raw `r` 被拒绝不能用于推断实验消旋/样品纯度，存在与含义均未被采纳/反驳；裸指定结构/strict身份也不是同样品或对映纯认证。
2. 工厂/恢复/审核/writer共同事实源是同源验证，不是独立双算；两个包装实现的存在不自动变成新阻塞。
3. 自报 formal_charge/stereo/isotope 与结构重推导一致的声明，限定“经首消费验证的入口”，不是所有裸对象无条件性质。
4. 更正“scope 字面含不区分键断裂方式与电子去向”的归属：当前代码 scope 不含这句，把它归属许可定义/规则正文即可；若选择改字段字面则登记版本/身份影响。composition-only不能升级机制证明。
5. `completion_license/completion_license_scope` 恒入 center detail，字段存在≠使用许可；判“本结论含许可补全”同时看 product_coverage=full、uncovered_*_refs非空、unlicensed_uncovered_identities为空。scope随结论保留，license_applied/顶层/同屏渲染等一般增强仍按原P2，不要求为S3a先补整个展示层。
6. Requirement/ConditionFact由 frozen及嵌套冻结保护；PathContext本体非frozen，消费前内容身份验证兜底。修改语义字段保留旧context_id应拒，不能把两种机制写成同一类型不可变。
7. 失败诊断是**三个**判定字段None，diagnostic.center_evidence为空；converter仍有版本/来源元数据和center_match=None。None=未评估，不=通过，不能写“四轴None”或“converter整个evidence为空”。
8. R8源码当时无 audit_hypothesis生产caller；S3新caller必须承担异常中止本次admission/submit的义务，不吞AuditContractError继续。新增调用链提供执行证据，grep空不是动态安全的通用证明。

另更正文案：canonical+r 的上层 state_structure_unparseable 实际包工厂未登记 CX 类守卫拒绝，不等于 RDKit 本体不能解析/化学非法；14行为红不是14个旧错误R6（单改charge=99在父基线已有电荷violated、R5d retain）；R7旧化学脚本实际55条早停，旧assert先停在55/57计数失败、未执行行为分支，尾部由新分段补全，不写成“旧assert首个行为翻转通过”。这些修正在新交付书及必要测试注释落字，旧原记录只读。

## 9. 回归、红绿与安全隔离

### 9.1 PPV1及基线红绿

每批运行相关新旧单测、PPV1工程全量，随后安全G01；按实际当前测试数登记，不锁死“必须恰好536”。S0–S2 既有功能断言、合法和诚实unknown/partial不能被全拒改写。语义版本升位需要的fixture版本更新单列理由，不修改旧回归的行为期望绕过失败。

新增测试在基线 `00e509a974b40a7c9779fcd35e53b16637a13d60` detached worktree 的隔离源跑同字节文件，固定合法输入/行为期望，禁止为基线改import/适配返回值后声称同测试。新API缺失造成collection/import/字段/表红可以真实登记，不假称旧错误行为；把缺实现红、真正行为红、正控绿、未执行内部段分别统计。新S3功能缺失红本来不是新化学漏洞。

S3b另在S3a已审核直接父批基线跑同批集成测试定位新增行为，仍保留00e509a总体对照；不得把S3a新API在00e缺失当S3b行为证成。以分段公共链补充不能collect的接口，用实际调用输入/输出区别未实现与错误。基线失败不等于runner/整套审核失败，退出码和逐案类别分别保存。

### 9.2 G01只用安全隔离工程口径

继承R8白名单范围，复制当前仓内普通src/tests/vendor/必要metadata和明确非题面冻结反应资产；普通dependingv3/src必要42文件及本仓18资产镜像可延续，禁止补原v3真实评价/资产、dependingv4、reports/data/evaluation/benchmark/金标题面/封存逐题材料。若当前S3新增文件/依赖，增列白名单路径/理由/当前SHA，不能扫描真实敏感目录“找齐依赖”。

固定 PYTHONPATH、空 BBD_DATA_ROOT、V3_CODE_ROOT、V43_ASSET_ROOT、DEPENDING_V3_ROOT到隔离树；源码副本含完整vendor与必要project metadata；禁字节码/pytest cache，不在永久证据内建库。R8 `safe_g01_reproduce.py` 固定00e509a和270旧输入hash，**只能复核历史，不能直接用它声称S3当前测试**；S3需新控制器/当前源清单/实际HEAD，保留原文件只读。

历史缺席依赖须逐项对照：真实评价5项（test_batch_runner:52；test_score_report:110/163/172/184），v4对照1项（test_analog_assets:95），phase_d派生metadata2项（test_analog_v2_corpus:62/153）；选择not slow排16项，另明确排 `test_export_v3::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden` 1项。S3行号/数目变了用当前nodeid和实际理由登记，不将skip改pass或以“全量”掩盖排除。1138/8/17和1110/8/17保留历史标签，不混成新数字或原环境1119/16。

### 9.3 证据目录

每批使用新合成批次根和新tmp；产永久入口 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3_impl_<实际日期>/`，下分 `s3a_<轮次>/`、`s3b_<轮次>/`，同日可并列，每批子目录各有独立README/manifest.json/SHA256SUMS并冻结；父目录只作容器，不让首批manifest覆盖未来会变化的父索引。回修新建子目录、不覆盖老批，完整S3若需总索引则新写最终索引，不回写旧清单。每个批次至少含：

- README：范围、完成/未完成、可复现安全命令、输入白名单、实际执行与声明来源、异常/早停/准备错误说明。
- 原脚本、合成完整输入/输出、stdout/stderr、junit、实际argv/cwd/env关键隔离变量、退出码与耗时，不只摘要。
- actual HEAD/父提交/dirty状态、依赖与RDKit版本、schema/策略/工具/资产身份、逐输入hash；基线worktree建立/清理日志。
- 逐attempt/action/request/budget预约/事件/展开/deferred的可读账目与必要合成前后count，四崩溃和并发独立worker日志、重算断言。
- 红绿分类，行为失败与字段/表/导入缺失分开；正控、unknown及每个组合实际执行段标明。
- manifest.json与SHA256SUMS覆盖全部附件和嵌套清单，只有外层清单不自我hash；交付书/请求可单列hash引用，不能更新后仍引用旧hash。

永不在永久证据目录原地执行会写库/日志的探针；README复现复制到新tmp或控制器拒已有输出目录。旧脚本硬编码HEAD不是当前HEAD，版本漂移需明确。合成SQLite是否封存为证据按仓库忽略规则登记，目录不能混真实数据；日志优先可审计载荷。证据不以模型意见替代程序执行，不把scripted网络0说成真实调用。

## 10. mimo、交付与本地提交

每批产新交付书，建议 `docs/POLLUTANT_PATHWAY_S3A_DELIVERY_<日期>.md` / `docs/POLLUTANT_PATHWAY_S3B_DELIVERY_<日期>.md`，逐项映射本书§7矩阵，附实际提交/版本/diff/测试命令数字/预算账与公共链入口/已知边界/未完成项。S3a交付明确runner仍拒；S3b明确完整链的启用、默认off/0及实际证据。

首批将 `docs/mimo_ppv1_chem_review_request.md` 更新为 **v9（S3a）**：自包含全部适用化学规则、R8八项更正、继承的center/proof/unknown与失败契约；列实现与未实现边界，要求mimo只读化学判据，执行类声明待执行验证。保存v8请求及v9送审快照在本批证据，旧回应不覆盖。S3b及回修按实际送审轮序升级v10等，每批独立请求与回应/provenance，不能两次送审都叫v9。没有新化学机制也应说明本批哪些消费契约/文字受审，未实施的中心集成不得伪称执行完成。

实施agent只准备请求，不自行外模。主会话按当前AGENTS自动接力核对后送mimo、回Codex；mimo读码不是执行，独立评审不做背书，采信到公开程序互证。判据冻结由用户另行裁定，本批不宣布冻结。

仅在 dependingv43（v4.3）做本地提交，不push；实现可修改必要新profile源码/公共分流/新测试/新交付和请求，冻结模块仍不动。本次起草任务书本身只新增本文，不能把它误解为“未来实施也只写docs”。提交前检查 `git diff`、`git diff --cached`、状态与每项路径，`git add`显式列本批源码/测试/交付书/请求；禁止`git add .`/`-A`，不要带入已有用户AGENTS改动、旧未跟踪审核/mimo回应或证据目录。评审侧材料默认留未跟踪由用户定，实施证据是否入该提交按现有忽略/归档口径在交付书明列。本次起草代理不git commit，只新增本文；本文是否在后续实施提交纳入，由实施方显式选路径登记。交付状态应为“本代理变更已提交、无本代理未提交源码测试；既存AGENTS差异/未跟踪评审材料单列保留”，不通过stash/restore/clean或全量暂存制造整仓干净。

开工/交付都登记工作区原差异；只清理本批自建worktree/tmp，不删除别人文件，不回写旧永久证据/报告/封存run。若真契约矛盾、范围外/金标风险/费用异常，报告具体证据与选项，只停受影响部分；常规工程选择可自行完成。自动循环停点依当前AGENTS和本批主会话授权执行，不能将已授权S3扩成自动实施S4/S5。

## 11. 实施顺序与主要风险

1. **S3a先固定消费面和预算账。** 对准真实入口列矩阵→版本/身份/持久对象→事务claim/预约→artifact提交/恢复→四崩溃及并发/零预算/循环夹具→继承回归/G01→文档与请求→交付复审。底座可独立使用合成driver，不需要先开公开runner。
2. **S3b先确定独立分流，再接具体流程。** 模型协议/反馈→冻结池和两类deferred→条件依赖/场景转换→固定工具中心证据→audit/admission/submit与队列提交→PPV1 start_run/resume_run→端到端恢复/所有验收→回归/G01→新轮请求与交付。不要先删拒绝再寻找正确存储。
3. **合成fixture先算过程再实现期望。** 每父备选2、产品宽度2、深度3、action10为默认小值，逐步列实际retrieve/decide/expand/activate/transition占额；需要调整合法小值就登记fixture版本和理由。action10不是保证任意场景都跑完，耗尽时应诚实停。并发用真实独立连接/进程与确定同步，崩溃用可定位故障点、新进程恢复，不能“raise后同进程内存继续”冒充进程崩溃恢复。

高风险点是：删除拒绝落入legacy；事件/队列跨库误称原子；悬空请求默重发或预约重复扣；同分子共享上下文；deferred把产物与反应备选混成一队；失败诊断或scope字段被当通过；只测内部假证明而漏生产caller；固定旧hash脚本被当当前G01。交付书逐项说明接法和验证，把这些风险对应到§7的公共入口，不再追一个字符串反例打一处补丁。

**完成定义：**S3a固定底座验收通过且未交付集成诚实登记；S3b全部S3矩阵/继承控制、安全G01与证据齐备，经mimo及Codex复审裁定。工程通过后科学性能仍pending，下一阶段由用户/主会话另行启动。
