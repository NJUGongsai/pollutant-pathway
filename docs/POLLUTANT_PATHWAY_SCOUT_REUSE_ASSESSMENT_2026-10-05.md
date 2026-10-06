# GitHub 侦察项目对污染物路径架构的复用裁定

- 日期：2026-10-05
- 对象：HIT60_GITHUB_SCOUT_CORPUS.md、HIT60_GITHUB_SCOUT_LLM_LAYER.md
- 依据：当前 dependingv43 源码、上一轮 S0–S2 审核、官方仓库／文档／论文复核
- 性质：复用建议。未安装依赖、未集成数据、未调用真实模型、未修改原始侦察报告或源码。

## 1. 结论

**有现成组件可用，但应复用小模块，不能把整个项目接上就认为路径预测能力已升级。**

最实际的路线是：当前回修复用已有 RDKit／AtomTool，并考虑 Pydantic 严格字段契约；底座过审后，用 EVODEX 补规则候选生成，用现有 enviPath 来源补路径与场景证据；RankLLM 作为候选排序实验。REAP 整套、OctoTools／DeepAgents 主干、XGrammar 新部署、语义熵采样暂不优先。

两份侦察报告主要围绕 HIT60 单步命中和旧实验路线。本文按“污染物多步降解路径”的目标重新排序。旧报告中的“S3 语料扩充”与新升级规格的“S3 有界搜索执行流”是不同的阶段命名，不能直接互换。

## 2. 最值得复用的项目

| 项目 | 可以拿来用什么 | 是否直接接当前系统 | 本轮建议 |
|---|---|---|---|
| Pydantic／Instructor 方案 | 类型契约、JSON Schema、结构化错误反馈 | Pydantic 可加薄层；Instructor 的完整请求链需适配 | **先做字段契约，优先级最高** |
| EVODEX | 局部反应算子应用、候选产物生成、算子匹配 | 有现成 Python API；需做来源／参与物／版本适配 | **最值得试的外部化学工具**，底座过审后再集成 |
| enviPath Python SDK／REST | 路径、反应边、来源场景与条件读取 | 现成对象接口；先对账已有镜像 | **最贴目标的数据补充方向** |
| RankLLM | 列表重排、滑窗聚合、响应分析 | 需把我们的假设／证据卡映射成稳定 ID 的排序请求 | 可做有限实验；当前不是第一优先 |
| ReactZyme | UniProt 酶与 Rhea 反应关联、检索评测切分 | 需结构与来源适配 | 适合辅助酶解释，不能直接作为完整降解反应账 |
| REAP | 原子特征表达、结构信息注入的思路 | 全框架涉及新 GNN／检索链 | 借鉴表达，不直接引入整套 |

### 2.1 Pydantic 可直接用；Instructor 不能直接绕过当前调用账

Pydantic 支持严格类型、额外字段控制及 JSON Schema，可用于统一新模式的假设、参与物、系数、编辑操作和模型响应格式；采用严格校验时，仍须保留动态 ID、底物锚点、排列完整性、跨对象引用和化学检查。[严格模式](https://docs.pydantic.dev/latest/concepts/strict_mode/)、[模型与额外字段](https://docs.pydantic.dev/latest/concepts/models/#extra-data)

当前代码已有手工 JSON 解析及完整排序契约：[prediction.py:648](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/prediction.py:648)、[prediction.py:709](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/prediction.py:709)。因此收益是减少协议与解析器不一致、统一表示验证，不是从零获得结构化输出。不能直接把 legacy 解析器全部改严，改变旧冻结行为。

Instructor 是基于 Pydantic 的结构化响应封装，包含校验后自动重问。我们的客户端是自写 urllib，并已有请求登记、预算和恢复；完整迁入其请求链会产生额外适配，且其校验重试与 SDK HTTP 重试需分别控制。[官方仓库](https://github.com/567-labs/instructor)、[重试说明](https://python.useinstructor.com/concepts/retrying/)

建议先用 Pydantic 薄层和现有调用环；如果采用 Instructor，所有请求仍必须经过既有预算／attempt 登记，关闭库内不可见重试。格式错误反馈与化学重新提案分开，chemical_reproposal=off 时不能因 SMILES／化学审计不通过自动反复生成。

**它能辅助修表示契约，不能替代氢计数、条件继承、严格身份和账本参照完整性修复。**

### 2.2 EVODEX 是外部候选工具的第一选择

官方提供可安装的 Python 包，现成接口包括：

- project_reaction_operator：将指定 SMIRKS 算子应用于底物。
- project_evodex_operator：按算子 ID 应用规则。
- project_synthesis_operators：应用候选算子集合。
- match_operators：匹配反应与算子。

官方 README 目前标软件 2.1.0、算子 ID 前缀 EVODEX.2.1，并说明修过反应中心检测算法；代码标 MIT。本轮未安装运行，依赖兼容性尚未实测。原侦察的 0.1.23／许可待核应更新。[官方版本、接口和许可证](https://github.com/UCB-BioE-Anderson-Lab/EVODEX)

建议作为独立候选生成／局部规则诊断适配器，保留 operator_id、软件／数据版本、父来源反应与映射关系。P 类部分转化与局部算子不是完整净反应，也不能据此授予 experimentally_observed_exact、full_balance verified 或机制基元步。[官方算子集合说明](https://ucb-bioe-anderson-lab.github.io/EVODEX/)、[原始论文](https://pubmed.ncbi.nlm.nih.gov/41925163/)

接入位置：新模式的候选池／假设构建层。输出须区分备选假设与共同产物，不得把规则生成的主产物直接提交成完整反应事件。计量、共底物、环境及生物支持仍分别审核。算子数、生成数、失败和截断也要纳入有界搜索记录。

先做指定少量算子的合成验证和独立环境兼容检查，不把它的全套依赖直接覆盖现有 RDKit 环境。官方构建说明本身提示依赖版本窗口较窄。[构建说明](https://github.com/UCB-BioE-Anderson-Lab/EVODEX#building-and-running-the-mining-pipeline)

**复用价值是增加可解释的候选来源，不能代替本地 ChemicalAudit，也不能自动证明污染物在当前场景中会沿该路线降解。**

### 2.3 enviPath 应先补已有数据的路径与场景信息

对我们的目标，环境路径、原始来源和实验条件比增加大量通用酶反应更直接。官方 SDK 有 Package、Pathway、Edge／Reaction、Scenario 对象，可作离线读取工具；先核对已有镜像保存了哪些字段。[官方 Python 对象接口](https://envipath-python.readthedocs.io/en/main/objects.html)

优先补 pathway／edge 身份、原文引用、来源场景、条件、review／录入状态及预测与记录的区别。Scenario 可能描述来源实验采用的条件或规则适用信息，必须保留作用对象和依据；不能把来源实验事实写成当前用户场景，也不能把培养设置推为反应 essential。[Scenario 定义](https://wiki.envipath.org/doku.php?id=scenarios)、[作者更新论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC11304562/)

建议下载／读取阶段冻结原始快照、来源 ID 与哈希，运行和评测使用冻结资产。SDK 的代码授权与各数据包的授权分别记录，不作“整个 enviPath 所有内容都可随意再分发”的推定。

### 2.4 RankLLM 可以复用，但目前已有排序能力

RankLLM 提供列表重排、RankGPT 等提供方后端、自定义提示词及响应分析；当前官方也区分 hosted-provider 与本地推理等可选依赖。[官方仓库](https://github.com/castorini/rank_llm)

我们已有 rank v2 完整 order 校验，当前默认排序任务最多给 8 张合格 recorded 卡：[prediction.py:420](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/prediction.py:420)、[prediction.py:709](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/prediction.py:709)。所以 RankLLM 不等于新增一个原来没有的模块；8／16 张候选也未必需要 20 张滑窗。

可以复用其排列提示、窗口聚合、响应分析；每次窗口请求须经过现有模型调用账。新模式排序应使用稳定假设 ID，保留假设的计量、证据、条件和准入状态。排序不能把不合格卡升为可执行反应，也不能用名次代替校准过的概率。

先验证排序确为主要损失来源；正确候选不在池中，重排无法补救。原侦察的“闭卷 hit@1 提升 3–8 点”没有本任务证据，不作为承诺、排期收益或通过门槛。

## 3. 数据侧不能直接混入完整事件的项目

### ReactZyme

可复用酶—反应关联与时间／结构等切分方式。官方说明数据仅提供正酶—反应配对，反应处理和检索训练的目的与完整计量事件不同；其配对数不能作为独立污染物降解反应数。[官方仓库](https://github.com/WillHua127/ReactZyme)、[数据记录](https://zenodo.org/records/13635807)

该酶与 Rhea 反应存在关联，不证明当前菌群具有该酶、表达活跃或环境相容。水及小分子等预处理丢项须追溯，不能直接标计量完整。优先做关联层，蛋白表示模型与训练流程后置；仓库 CC0 已核实，具体下载资产许可仍按资产记录。

### BioRGroup

它是分子级 R 基团与具体 PubChem 结构的计算匹配，不是直接提供完整底物—产物配对或实测降解反应。原文共有 12,709 个记录，其中 2,124 个含 R 基团；原侦察“约1.3万个含R基团分子”不准确。数据记录标 Etalab Open License 2.0。[原始论文](https://www.nature.com/articles/s41597-025-05983-w)、[官方数据记录](https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi%3A10.57745%2FV3URYA)

可借鉴泛型结构匹配，用于 computed instantiation 候选。跨反应参与物必须保持同一 R 基团绑定、映射和立体关系；真实分子存在不证明它接受该酶的此项转化。大规模实例化不是当前回修任务。

### ECREACT

原始工作为单产物预测处理过辅酶、常见副产物和小分子。原子映射不等于完整参与物账；直接并入会重现我们正在修的“主产物对冒充完整净反应”问题。[原始论文](https://www.nature.com/articles/s41467-022-28536-w)

代码仓库有 MIT，但上游数据授权与代码许可分别记录，不作一揽子授权推定。[仓库许可证](https://github.com/rxn4chemistry/biocatalysis-model/blob/main/LICENSE)

## 4. 暂不整体引入的项目及侦察纠偏

| 项目／说法 | 裁定与依据 |
|---|---|
| REAP 全框架“只动提示词、无需新模型组件” | 官方 AtomDisc 包含 GIN 图神经网络、向量量化和已训练 checkpoint，任务为分子性质预测，另有检索链。整套不能视为纯 RDKit 提示词模块。借鉴原子环境表达即可。[官方说明](https://github.com/mingxuZhang2/REAP) |
| REAP 式 Gasteiger 电荷能给“微生物攻击位点” | 计算描述符可作提示信息，不能升格为酶选择性、实际反应位点或环境降解证据。已有 substrate_profile／供体变换提取可扩展，不需照搬框架 |
| OctoTools／DeepAgents | 当前 LangGraph 与 AtomTool 已有编排和受限编辑。借鉴工具卡的输入、前提、输出、错误码、版本和检查范围，避免再造 planner／executor。[OctoTools 官方框架](https://github.com/octotools/octotools) |
| XGrammar 作为普通 API 客户端的即插即用插件 | 它是推理侧解码约束；服务端须支持，客户端安装包不产生 token 掩码。JSON／语法合规不能证明分子、反应或环境正确。[官方仓库](https://github.com/mlc-ai/xgrammar) |
| 本地推理或固定 seed 保证完全复现 | 不能笼统承诺。推理栈仍有硬件／版本／配置条件；缓存保证已存结果重放，不保证重新请求逐字相同。[vLLM 官方复现说明](https://docs.vllm.ai/en/latest/usage/reproducibility/) |
| semantic_uncertainty／SEP 的簇大小就是可信化学概率 | 一致性与真实正确率不同，模型可能一致地错；重复采样增加请求预算，SEP 还需内部表示。暂缓新采样链 |
| s20ss/mcp-rdkit | 正确仓库是 s20ss/mcp_rdkit。实际工具主要为绘图、描述符、子结构、名称查库等，没有当前所需的完整账和供体核验；当前无需替代 AtomTool。[实际源码](https://github.com/s20ss/mcp_rdkit/blob/main/mcp_rdkit/rdkit_helper.py) |
| chembench/chembench | 化学 LLM 基准正确项目为 lamalab-org/chembench。可作独立外部能力评测，通用化学题不替代污染物路径验收。[官方项目](https://github.com/lamalab-org/chembench) |

原报告的“工具化编辑消灭原子账错误”“语法保证化学合法”“同一 seed 保证复现”以及直接预测本任务提升幅度，都应收紧。当前计量、条件、来源与账本错误不需要购买新框架才能解决。

## 5. 给执行 agent 的使用次序

1. 先完成 [S0–S2 审核回修](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_2026-10-05.md)：复用 RDKit 的完整氢、形式电荷、StereoGroups／CXSMILES，以及已有 AtomTool／供体变换提取；修好账本和条件契约。[RDKit 官方扩展表示说明](https://www.rdkit.org/docs/RDKit_Book.html#cxsmiles-cxsmarts-extensions)
2. 在新模式补严格类型／Schema 薄层，不引第二套 agent 主干，不绕过现有预算和恢复。
3. 底座通过审核后，先做 EVODEX 少量算子的隔离适配验证及 enviPath 来源元数据对账，明确候选来源与未知项。实际集成属于新任务，不能顺带改 frozen legacy 或默认启用外部预测。
4. 新的有界搜索具备持久调用账后，再评估 RankLLM 的小规模排序方案。
5. 原子描述符、酶关联、泛型实例化和新语料各自独立记录增量；按来源去重与评测隔离，不将同源新增覆盖包装成未见路径的泛化提升。

这是一份复用优先级和适配边界说明，不代替化学判据冻结审核，也不构成任何命中率或生物学可行性保证。

