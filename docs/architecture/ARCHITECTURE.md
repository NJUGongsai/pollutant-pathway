# pathway_agent v4.3 架构设计

> 状态：2026-09-24 设计稿。已确定采用 LangGraph StateGraph 重建工作流；化学能力优先复用并验证 v3/v4 的现有实现。实现目录与交付顺序见 [REPO_DESIGN.md](REPO_DESIGN.md)。

## 1. 目标与架构结论

系统从一个待降解底物出发，逐步建立有证据的环境降解路径。每一步可以报告最多五个有序产物候选，但只选择有依据的路径继续展开。预测某条路径的下一步时，任务同时提供当前分子、从原始底物走到当前分子的反应链、每条边的证据与适用环境。

v4.3 改变 v4.1/v4.2 的调度顺序：先检索当前路径的反应证据，再决定接受已知产物、调用预测模型、继续探索或回溯。候选排序能够影响下一步的探索预算。反应规则与反应库由本仓 assets/ 提供并按哈希校验；v3 冻结引擎代码、分子工具和确定性评测能力经适配后继续使用。

核心分工：

| 部件 | 职责 | 执行性质 |
|---|---|---|
| Orchestrator | 选待探索路径、下发任务、控制预算与停止、提交经过验证的反应边 | LangGraph 工作流 + 确定性节点 |
| ReactionFinder | 检索当前底物的已知反应、规则候选和相似反应，生成可追溯证据 JSON | 确定性检索服务 |
| PredictionAgent | 根据完整路径及证据，对不确定候选作判断；类比或空缺时提出产物 | LLM，仅在需要时调用 |
| AtomTool | 原子映射、SMILES 与 MoleCode 往返、结构校验 | 确定性工具 |
| PathwayStore | 保存分子、反应事件、路径实例、证据和探索状态 | 领域数据存储 |
| Export/Evaluator | 导出冻结评测契约并确定性判分 | 零 LLM |

“Agent”是职责名称，不意味着每个职责都要调用一个 LLM。Orchestrator 的判断规则和 ReactionFinder 的检索结果必须可重放；PredictionAgent 是唯一需要模型生成或裁决的职责。精排与编辑使用不同的任务协议及提示词，初版可共用同一个模型适配器。

## 2. 两种图与两层状态

**执行图**由 LangGraph StateGraph 定义，表示下一步执行哪个工作节点。节点是函数，条件边决定路由；checkpointer 保存执行进度。LangGraph 的 State 不自动等于污染物的化学路径图。

**降解路径图**由 PathwayStore 保存，表示分子和反应之间的关系。一个已记录反应可能有多个产物，故领域层使用“分子 → 反应事件 → 产物集合”，不强行把多产物反应拆成互不相关的单产物事实。

同一个化学分子可以经不同路线到达。分子身份可去重以便展示和检索缓存，但每条来路保留独立的 PathInstance、入边和路径证据。PredictionAgent 的任务通过 path_id 确定它正在判断哪一条完整路线；循环检测按路径进行。显示名称可使用 S11、S211 等，内部引用使用稳定 ID，不解析显示编号来推断父子关系。

工作流 State 保持小而明确：

| 字段 | 含义 |
|---|---|
| run_id、root_compound_id | 一次预测的稳定身份 |
| active_path_id、active_compound_id | 当前处理的路径实例和末端分子 |
| graph_revision | 已提交领域图的版本，用于检查点恢复和审计 |
| retrieval_ref、decision_ref、validation_ref | 当前任务的 JSON 产物引用 |
| frontier_ref | 待探索路径队列的持久化引用 |
| budget | 展开、LLM 调用、提案、深度和节点额度 |
| phase、stop_reason | 执行阶段与结束原因 |

证据卡、MoleCode 原文、完整候选池和对话记录保存在运行产物中，State 只放稳定引用。任务书从 PathwayStore 与这些引用确定性组装。

## 3. LangGraph 执行流程

    START
      → normalize_input
      → select_frontier
      → retrieve_reactions
      → classify_evidence
          ├─ 单一适用的已记录反应 → accept_recorded
          ├─ 规则或多个候选需裁决 → rank_candidates
          ├─ 类比反应需迁移 → analogy_edit
          └─ 无可用证据 → novel_proposal / mark_dead_end
      → validate_products
      → rank_and_schedule
      → commit_pathway
      → select_frontier（有待探索路径且预算未尽时）
      → export_results
      → END

所有通路在写入降解路径图前汇合到 validate_products。classify_evidence 和 select_frontier 使用确定性路由；LLM 输出只是候选提议，不能直接修改图。初版一次只处理一条 active_path，以保证预算与提交顺序可复现。未来若并行检索或展开多条路径，可使用 LangGraph Send 分发独立任务，并定义稳定归并顺序与 reducer。

LangGraph 的节点恢复可能重新执行整个节点。每个副作用使用 task_id 幂等键：run_id + path_id + compound_id + phase + 输入证据版本。检索文件和模型返回值按该键写入不可变 JSON；PathwayStore 对同一反应提交键只接受一次。文件先写临时文件再原子替换。检查点与领域图分别持久化；恢复时用 graph_revision 与幂等键对齐。

## 4. 逐步任务协议

ReactionFinder 输入包括当前分子的原始 SMILES、规范身份、path_id、上一条转化及可用环境条件。已知反应匹配主要针对当前分子；路径历史用于判断反应方向、适用性和类比转化。它输出结构化证据，至少包括：

ReactionFinder 在运行前校验 v4.3/assets 的 manifest，检索结果写入所用文件的相对路径及 SHA256。资产来源与校验命令见 [ASSETS.md](ASSETS.md)。旧 v3 引擎桥接若在迁移阶段仍依赖原有资产根，应在 run_identity 中分别记录“v4.3 检索资产”和“v3 桥接资产”，避免把两套数据误认为完全相同。

| 字段 | 内容 |
|---|---|
| evidence_id、source_id | 稳定证据 ID；数据库、规则或索引条目 ID |
| kind | recorded_reaction、rule_application、analog_reaction |
| query_identity、match_type | 当前分子身份及匹配方式 |
| reactants、products、atom_mapping | 原反应及其原子对应；缺失时明确标记 |
| conditions、condition_fit | 已知环境条件与本任务条件的相容、冲突或未知状态 |
| source_record、asset_hash | 可复查的出处与检索资产版本 |
| retrieval_rank、score_semantics | 原始排序及分数含义，不混称概率 |

PredictionAgent 的任务书包含 root_smiles、current_smiles、path_id、按时间顺序列出的祖先反应与证据、当前检索结果、可选环境条件、已经存在的兄弟候选和剩余额度。输出为结构化候选：产物 SMILES、可选 MoleCode、反应中心/原子映射、引用的 evidence_id、理由、候选顺序和模型原文引用。

已记录反应若满足接受规则，其产物由确定性数据路径进入校验；PredictionAgent无需改写该产物。规则候选优先由引擎计算，LLM 仅处理排序或适用性不明的情况。类比编辑时 AtomTool 先将当前分子转换为带稳定原子标识的 MoleCode；模型基于已对齐到当前分子的映射作受限编辑；AtomTool 转回 SMILES 并复验映射、结构和原子守恒。MoleCode 是编辑视图，化学状态以可解析的分子图及其 SMILES 为准。

## 5. 证据等级、排序与选择性展开

证据等级分开记录：

1. 已记录反应：同一规范底物、方向一致、反应来源可追溯。
2. 规则应用：规则匹配当前结构并计算出产物；它是预测，不是该底物的实测记录。
3. 类比反应：来源反应和当前分子存在可解释的结构及反应中心对应。
4. 新提案：LLM 基于路径与化学约束提出，缺少以上直接依据。

“确切命中”只指第 1 类的底物与已记录反应命中。条件相容、条件未知、条件冲突单独标记；“规则模式匹配”不能提升为实测确切命中。检索出的多个已记录产物均保留各自来源和实验条件。

输出候选数与向下展开数分离：每一步可报告 top-5；frontier 只放当前策略选中的路径实例。初始策略为：存在单一且条件不冲突的强已记录反应时，优先展开其主线；存在多个可信已知产物或条件未知时，保留竞争候选并按预算探索少数分支；只有规则/类比/新提案时，允许有限探索与回溯。初始工作上限和宽度必须在 dev 上定值、写入配置及 run_identity，再做冻结评测。

每条反应边分别记录 evidence_level、condition_fit、confidence_band、ranking_basis 和可选的 calibrated_probability。confidence_band 是附理由的定性证据强度（高／中／低／未知），不是由原始引擎分数直接转换的概率。原始分数跨来源语义不同；路径整体概率须在独立校准后才能输出。

select_frontier 以路径为单位选择下一项，并明确记录继续、暂缓、拒绝或回溯的原因。终点判定、重复路径、预算耗尽及无有效候选由确定性代码处理。系统不会因没有已记录反应而静默停止：它会依次尝试规则、类比，再进入受约束的新提案流程。

## 6. 化学校验、存储与导出

进入 PathwayStore 前至少完成：分子可解析与价态检查；原子映射和往返转换一致性；按反应类型允许的元素变化检查；方向与来源挂牌；终点锁定；同一步兄弟候选去重；路径内循环检查；预算检查。对环境反应允许的外源氧等变化使用显式规则并记录依据，不把简单元素计数当作完整反应机理证明。

图中的每个反应事件保存 evidence_ids、检索资产身份、模型决策引用、校验结果和创建时间。PathwayStore 是领域事实账本；LangGraph checkpoint 是执行恢复点；results/ 下的 JSON 是不可变证据与模型响应。三者以稳定 ID 关联。

导出器将领域图投影为现有 v3 基准需要的 root_smiles 与有序 steps，rank 从每个父节点的候选顺序计算。多产物反应的展示方式与基准的平面产物列表由适配器显式处理。评测器继续只读调用，判分全过程零 LLM；同时另出包含路径、证据和拒因的研究报告。

## 7. 验证方案与边界

先用固定夹具检验：同一分子经两条不同路径到达、多个已记录产物、条件冲突、类比映射失败、MoleCode 往返失败、恢复时重复执行、死端回溯、终点及预算停止。再与 v4.1/v4.2 冻结答卷在相同口径下比较单步 hit@1/3/5、多步 route_recall、spurious rate、展开节点数、LLM 调用数、成本与耗时，并分开报告已知反应、规则、类比和无证据切片。

v4 的 dev 路线来自 EAWAG 相关语料，适合检查已知证据检索与排序；泛化能力需使用与检索语料隔离的外部题集。298 外考的既有 run-once 答卷保持历史基线，不把旧考题用于 v4.3 参数选择。

## 8. 参考

- 设计讨论：../dependingv4-fix/docs/Discussion-v4.3.md
- LangGraph 官方说明：[Graph API 与 StateGraph](https://docs.langchain.com/oss/python/langgraph/graph-api)、[持久化](https://docs.langchain.com/oss/python/langgraph/persistence)
- 旧系统代码基线：dependingv4 的 feat/v42-fix 及 v3 冻结引擎、评测器
