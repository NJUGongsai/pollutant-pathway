# HIT60 · GitHub 技术侦察报告：LLM 协议层技术（闭卷生成能力提升）

- 侦察窗口：2024-09 至 2026-09（repo 创建时间优先取窗内；个别窗口外但活跃/有强论文背书者单独标注）
- 侦察日期：2026-09-29 ~ 2026-09-30
- 侦察方式：WebSearch + GitHub REST API（repos 端点）逐项核实 star/许可/最近提交；零 LLM API 费用；未改动仓库代码
- 侦察人：GitHub 技术侦察代理（生成侧）
- 数据标注约定：凡标注"（待核实）"的字段为本轮因 API 限频未能完成的项；其余 star/许可/提交时间均来自 GitHub API 或 GitHub 页面元数据实测

---

## 0. 大白话摘要（给非术语读者）

我们去 GitHub 扫了近两年的开源项目，目标只有一个：**当检索库里没有答案时，让大模型环节猜得更准、排得更对**。共登记 12 个候选、深评 5 个。最值得先看的三个：① **RankLLM**——成熟的"重排工具包"，专治"正确答案明明在候选里却排第 2-5 名"；② **REAP**——免训练的化学推理框架，把原子级化学先验写进提示词，专治闭卷瞎猜，与我们"不动模型、只动协议"的路线完全同频；③ **XGrammar / 结构化输出约束**——用语法约束保证模型只能吐合法分子串，治格式漂移和无效分子。**意外发现**：化学界 2025-2026 冒出一批"免训练 + 冻结大模型 + 外挂先验"的工作（REAP、ChemATP 等），我们的架构哲学正踩在这条新潮流上；而"微生物降解产物预测"的 LLM 专属开源项目**一个都没找到**——这个生态位目前是空的。

---

## 1. 候选总表（按 可接入性 × 预期收益 排序）

| # | 项目（repo） | 一句话干什么 | 主要接入协议 | 预期补哪类失分 | 许可 | star / 最近提交 | 零训练 | 主要风险 |
|---|---|---|---|---|---|---|---|---|
| 1 | [castorini/rank_llm](https://github.com/castorini/rank_llm)（RankLLM/RankGPT） | LLM 列表式/成对/点式重排工具包，滑窗排列生成 | rank_candidates | **排序弱**（答案在 2-5 位）→ 直接攻 hit@1 | Apache-2.0 | 660★ / 2026-09-29（当天仍在提交） | 是 | token 成本上升；长列表位置偏置（已有滑窗缓解） |
| 2 | [mingxuZhang2/REAP](https://github.com/mingxuZhang2/REAP)（ACL 2026 Findings） | 免训练化学推理：把原子级先验（电荷、局部拓扑）文本化注入提示词 + 外置知识库 | novel_proposal、analogy_edit | **闭卷生成差**、spurious 中"改错位点"子集 | **MIT（已核实）** | 6★ / 2026-08-29（repo 2026-04 新建，靠论文背书过门槛） | 是 | repo 极新、工程成熟度未知；评测域是考题非产物生成 |
| 3 | [mlc-ai/xgrammar](https://github.com/mlc-ai/xgrammar)（XGrammar） | 把 CFG 语法编译成 token 掩码，解码层保证输出合法（SMILES 语法级） | 三协议输出层（本地推理路径） | **格式漂移（6/56）**、无效 SMILES | Apache-2.0 | 1940★ / 2026-09-30（当天仍在提交） | 是 | **需本地权重推理栈**（vLLM/SGLang）；语法合法≠化学正确 |
| 4 | [OctoTools/octotools](https://github.com/OctoTools/OctoTools)（Stanford） | 标准化"工具卡"+规划器+执行器，让 LLM 每步操作都过确定性工具 | analogy_edit（工具化编辑）、novel_proposal | spurious（非法/价态错的编辑） | **MIT（已核实）** | **1472★ / 2026-05-02**（创建 2025-02-15） | 是（training-free） | 学习曲线；对我们是"协议节点重设计"而非即插即用 |
| 5 | [jlko/semantic_uncertainty](https://github.com/jlko/semantic_uncertainty)（Nature 2024 官方代码） | 语义熵幻觉检测：多次采样→语义聚类→熵高=幻觉嫌疑 | novel_proposal（置信度/降位/弃权） | spurious 中"模型其实不确定"的子集 | **MIT（页面元数据核实）** | 39★ /（创建 2023-03，窗口外，靠 Nature 论文背书） | 是（但需采样） | 研究复现代码需自行工程化；治不了"自信地错"；与 temp=0 确定性策略冲突 |
| 6 | [OATML/semantic-entropy-probes](https://github.com/OATML/semantic-entropy-probes)（SEP，ICLR 2025） | 用模型隐藏态 embedding 直接预测语义熵，免多次采样 | 同上 | 同上 | （待核实） | （待核实） | 是（需 embedding 访问） | 依赖模型内部访问权限（API 模型未必给） |
| 7 | [chembench/chembench](https://github.com/chembench/chembench)（JACS 2024/2025） | 化学能力评测框架（2700+ 化学题、多模型接入） | 度量层：闭卷 56 题扩展、协议 A/B 外部锚点 | 度量可信度（防自我感觉良好） | （待核实，通常 MIT） | （待核实） | 是 | 考题域≠降解产物预测域，只能做能力锚点不能做任务评测 |
| 8 | [pnnl/cactus](https://github.com/pnnl/cactus)（PNNL，ACS Omega 2024） | 化学信息学工具 LLM 智能体（RDKit 等工具编排） | analogy_edit（工具调用参考实现） | spurious（工具化编辑替代自由生成） | （待核实，PNNL 多为 BSD 系） | 创建 2024-04-30 / 更新 2026-04-07（第三方目录数据） | 是 | 维护节奏一般；偏问答/计算化学场景 |
| 9 | [s20ss/mcp-rdkit](https://github.com/s20ss/mcp-rdkit) | RDKit 的 MCP（Model Context Protocol）服务器封装：SMILES 生成、分子修改 | analogy_edit / novel_proposal 的工具通道 | spurious、格式（工具化 + 通道标准化） | （待核实） | ~42★（第三方目录数据，待核实） | 是 | 个人项目、单维护者风险；需走 MCP 接入 |
| 10 | [langchain-ai/deepagents](https://github.com/langchain-ai/deepagents)（LangChain 官方） | "深度智能体"脚手架：规划 + 子智能体（隔离上下文）+ 虚拟文件系统，基于 LangGraph | novel_proposal（深推理多步化） | 闭卷生成（多步推理预算） | （待核实，LangChain 系多为 MIT） | （待核实）/ 2025-08 发布、README 活跃 | 是 | 与现有 LangGraph 主干功能重叠；token 成本高 |
| 11 | [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | 类型化结构输出优先的智能体框架（Pydantic schema 驱动） | 三协议 I/O 层 | 格式漂移、解析失败 | （待核实，通常 MIT） | （待核实）/ 2024-11 发布、活跃 | 是 | 与 LangGraph 双栈并存的维护成本；不解决化学内容 |
| 12 | [AnswerDotAI/rerankers](https://github.com/AnswerDotAI/rerankers) | 轻量统一重排 API（交叉编码器 + LLM 重排） | rank_candidates（备选实现） | 排序弱 | （待核实） | （待核实） | LLM 模式是；交叉编码器模式=新模型组件（越界） | 默认路径多走模型重排器，与"不引入新预测模型"边界需甄别 |

**窗口外但值得知道的通用框架**（创建于 2023、本轮未深评，均活跃）：dspy（BSD-3，提示词自动优化，优化过程耗 LLM 调用费用）、dottxt-ai/outlines（Apache-2.0，结构化生成鼻祖）、567-labs/instructor（MIT，API 模型结构化输出，XGrammar 的 API 侧平替）、guidance-ai/guidance（MIT，微软）、promptfoo（MIT，提示词 A/B 工具）。这些与 #3/#11 同类，若走 API 模型路线，**instructor 是最先能用的**。

---

## 2. Top 5 深评

> 接入点统一按现行架构描述：LangGraph 确定性主干 + 三协议（rank_candidates / analogy_edit / novel_proposal）+ 确定性化学门禁（fail-closed）。所有接入均不动 v3 冻结检索引擎、不引入新预测模型。

### 2.1 RankLLM（castorini/rank_llm）——把"第 2-5 名"变成"第 1 名"

- **是什么**：滑窗列表式（listwise）LLM 重排工具包，核心是 RankGPT 的"排列生成"（permutation generation）提示范式：让 LLM 直接输出候选的完整排列而非逐个打分。支持 listwise/pairwise/pointwise 三模式，后端支持 OpenAI 兼容 API 与 vLLM/SGLang 本地推理。已核实：Apache-2.0、660★、2026-09-29（侦察当天）仍有提交，活跃度极高；配套论文 arXiv:2505.15804（2025-05）。
- **接法**：改造 rank_candidates 协议。现状是"候选间裁决"；改为 RankGPT 式——把 v3 检索出的候选（含供体反应证据卡、供体分子、反应 SMARTS 摘要）按滑动窗口（约 20 个/窗）输入，要求 LLM 输出排列，再按 RankLLM 的窗口聚合逻辑合并。保留现有确定性门禁与 fail-closed 语义不动。工程量：**2-5 人日**（提示词重写 + 排列解析 + 聚合；若直接 pip 复用其聚合代码更少）。可先做零依赖版本：仅借鉴排列生成提示词模式自写。
- **预期收益（诚实）**：文献上 listwise 重排在 IR 基准（BEIR/TREC）普遍带来 nDCG@10 +5~15 点，GPT-4 重排可超传统监督重排器。对我们的痛点映射：闭卷 hit@1 只有 15%（开卷 45.6%），且"答案常在报告第 2-5 位"——这正是重排的定义域。保守预期闭卷 hit@1 **+3~8 点**。**诚实上限**：重排只重排既有候选，不产生新答案；闭卷题里"正确答案根本不在候选集"的部分（novel_proposal 失败的题）救不了。
- **风险与回退**：token 成本上升（滑窗多轮调用）；LLM 排列有首位/末位偏置（滑窗已缓解）；排列输出无原生置信度，需"位置→分数"映射后与 v3 检索分融合。回退路径：退到 pairwise 锦标赛 + 确定性平票裁决（RankLLM 同样支持），或仅保留现裁决提示词不变。

### 2.2 REAP（mingxuZhang2/REAP）——免训练的原子级化学先验注入（最同频的发现）

- **是什么**：ACL 2026 Findings 论文《REAP: Towards Effective Training-Free Chemical Reasoning with Explicit Atomic Priors》官方代码。核心思想：LLM 做化学题差，不是推理差，是缺少显式的细粒度化学先验（电荷、局部拓扑等"原子级"信息）；REAP 把这些先验文本化注入提示词，并外挂一个可检索的先验知识库，全程免训练、模型冻结。论文报告：7B 级模型上也有效，超过免训练基线 MolRAG。发布物含**知识库构建代码 + 提示词脚本**。已核实：MIT 许可、2026-08-29 仍有提交、repo 2026-04-19 新建（6★，靠论文背书过门槛）。同组后续工作 **ChemATP**（arXiv:2512.19240，2025-12）进一步做成"原子级文本知识库"，让冻结 LLM 显式检索后推理，明确对标"训练型 SOTA"（代码发布情况待查）。
- **接法**：novel_proposal 与 analogy_edit 两处注入。(a) **底物分子先验**：对输入 SMILES 用 RDKit 算 Gasteiger 电荷、官能团标签、原子环境片段（ECFP 文本化），组成"底物攻击位点档案"进提示词——让模型先"看见"哪里电子云密/哪个官能团易被微生物攻击再提产物；(b) **供体先验**：analogy_edit 的供体反应卡附上"变化位点描述"（哪个原子/键变了、电荷如何迁移），把"基于供体分子的受限编辑"从整分子级收紧到官能团/原子级。提示词骨架可结合 StructChem（ICML 2024）的三段式（概念→规则→逐步推理，见排除清单备注）。REAP 的知识库构建脚本是"先验文本化 schema"的参考实现。工程量：**5-10 人日**（先验文本化函数 + 提示词模板 + 闭卷 56 题 A/B）。
- **预期收益（诚实）**：闭卷 hit@1 15% vs 开卷 45.6% 的落差，相当部分来自 LLM 对"这个分子哪里会被降解"没有显式依据、只能凭记忆猜——先验注入把这部分依据从"模型玄学"变成"提示词内证据"。REAP 论文在化学推理基准上免训练方法显著超过 MolRAG、接近部分微调方法；**但**其评测域是化学考题/分子性质，不是"产物 SMILES 生成"，迁移收益**未证实**，必须用闭卷 56 题 A/B 验证。保守预期：spurious（36-40/56）中"改错位点/改错官能团"的子集应有可见改善。
- **风险与回退**：repo 极新、star 少，社区验证不足；知识库是为考题集构建的，需改造为"按底物即时构建"。**许可已核实为 MIT，代码可引**。回退：自研"底物档案卡"提示词模块（先验计算用 RDKit 本来就能做），不依赖该 repo 任何代码。

### 2.3 结构化输出约束双路径：XGrammar（本地推理）/ Instructor（API 模型）——治漂移与无效串

- **是什么**：**XGrammar**（mlc-ai/xgrammar，已核实 Apache-2.0、1940★、2026-09-30 仍在提交）把上下文无关文法编译成自适应 token 掩码，在**解码层**保证输出合法，已被 vLLM/SGLang/TensorRT-LLM 集成——SMILES 有形式文法，可用 EBNF 约束"只采样出语法合法的分子串"。API 模型路径的平替是 **instructor**（MIT，把 Pydantic schema 变为强约束 + 校验失败自动重试）或厂商 JSON mode。
- **接法**：三协议的输出层。**API 路径（现实主路径）**：把三个协议的输出全部 schema 化（rank_candidates → 排列 JSON；analogy_edit → 结构化编辑操作（反应位点、键变化、产物 SMILES 分列）；novel_proposal → 产物 + 依据字段分列），instructor 式校验失败带错误信息自动重试；SMILES 字段前置 RDKit 语法/价态预检（把现有门禁前移到协议内，fail-fast）。**本地路径（彻底）**：vLLM/SGLang 部署开放权重模型 + XGrammar 的 SMILES EBNF，语法非法 token 根本不被采样，且推理可复现。工程量：API 路径 **1-3 人日**；本地路径 **1-2 周**（含部署、grammar 编写与验证）。
- **预期收益（诚实）**：确定性收益——治"温度=0 仍有 6/56 答案漂移"中的**格式分叉**部分与无效 SMILES；**不治 spurious**（合法但错误的分子照样合法）。漂移的另一来源是 API 端非确定性（temperature=0 不保证逐位复现）：API 路径只能靠结构化输出 + 响应缓存把漂移**压低**，无法归零；本地路径可彻底复现，但引入 GPU 运维成本，且"换推理栈"是否超出协议层边界需用户拍板（我的判断：属基础设施不属于新预测模型，但应明确确认）。
- **风险与回退**：本地路径成本/运维最重；XGrammar 的 SMILES grammar 需自写（社区有 SMILES/SELFIES 文法参考）。回退顺序：本地 XGrammar → API + instructor + RDKit 预检重试 → 现状。

### 2.4 OctoTools（octotools/octotools）——工具中介编辑：把"自由写 SMILES"变成"调用受控编辑原语"

- **是什么**：Stanford 出品的免训练工具编排框架：标准化**工具卡**（功能描述 + 输入输出 schema + 验证方式）、高层/低层规划器、执行器与验证器；LLM 引擎可插拔（OpenAI/Claude/Gemini/LiteLLM/vLLM/Ollama 等）。已核实：MIT、1472★、创建 2025-02-15、最近提交 2026-05-02、ACL 2026 录用 + NAACL 2025 KnowledgeNLP 最佳论文（arXiv:2502.11271）。（注：中文社区有"18k★"的传闻数据，实测 1472★，以 API 为准。）
- **接法**：analogy_edit 协议的工具化改造——这是与本协议设计意图**最贴合**的一条。把 RDKit 的确定性操作封装成 20~30 个"编辑原语"工具卡（如：定位官能团、水解酯键、氧化羟基、脱烷基、开环、加氧到指定位点），LLM 不再直接输出产物 SMILES 字符串，而是输出**编辑操作序列**，操作在工具卡内由 RDKit 执行——输出天然通过语法/价态校验。novel_proposal 同样走"提案 → 工具卡执行 → 读错误信息 → 定向修复"循环。这与现有 fail-closed 门禁形成互补：门禁是**事后拒绝**，工具卡是**事中修复**。工程量：**5-10 人日**（工具卡封装 + 规划提示词 + 循环控制；可不引入 OctoTools 全框架，只取工具卡规范与执行循环模式）。
- **预期收益（诚实）**：**结构性消灭**"非法/价态错/原子对不上账"类 spurious（这部分在 36-40/56 中的占比建议先做一次归因统计）；"合法但化学上错"的 spurious 治不了；对闭卷 hit@1 的贡献是间接的（第 1 位少报废项）。附带收益：AtomTool 目标对账从"事后核对"变成"构造时保证"。
- **风险与回退**：全套框架引入较重（planner 对模型能力有要求）；编辑原语集合的覆盖度决定上限（覆盖不到的变换只能回退自由生成）。回退：只实现"编辑原语 + 错误反馈循环"，不引入其框架代码。

### 2.5 语义熵一致性检测：semantic_uncertainty（+SEP）——把"模型其实不确定"的第 1 位挤下去

- **是什么**：jlko/semantic_uncertainty 是 Nature 2024《Detecting hallucinations in large language models using semantic entropy》（Farquhar 等，引用 2000+）官方代码。方法：多次采样 → 按语义聚类 → 语义熵高 = 幻觉嫌疑大。已核实：MIT（页面元数据）、39★、创建 2023-03（窗口外，靠 Nature 论文背书）。README 明示这是**论文复现代码**（GPU 推理、wandb、Llama-2/405B 实验），生产集成需自行工程化。同组 **OATML/semantic-entropy-probes**（SEP，ICLR 2025）用模型 embedding 免采样预测语义熵（本轮未核实其许可/活跃度）。
- **接法**：novel_proposal / analogy_edit 的**置信度回路**：固定 seed 采样 n=5~10 个提案（temp~0.7）→ 全部过现有 RDKit 门禁 → canonical SMILES 归一后聚类 → 簇大小即置信度：一致簇的代表进 rank_candidates；整体分歧大的题将 novel_proposal 提案**降位**（fail-closed 语义下可触发弃权，只报检索候选）。这是语义熵思想的无 logprob 实现（Universal Self-Consistency 式簇投票）；若 API 提供 logprobs 或走本地推理，可升级为标准语义熵。工程量：**3-5 人日**。
- **预期收益（诚实）**：语义熵检测幻觉在 QA 类任务上效果明确（Nature 2024），但**治不了"自信地错"**——spurious 里模型一致猜错的部分它检测不到，别指望全救。可期望：把"模型其实不确定却排第 1 位"的 spurious 挤到后位，hit@1 间接提升。成本警示：采样 n 次意味着 novel_proposal 调用费用 ×n；固定 seed 可保证可复现，但与 temp=0 的确定性语义不同，**需用户拍板**。
- **风险与回退**：采样引入方差（seed 固定可控）；SEP 需要模型 embedding 访问（API 未必开放）；官方代码为研究复现用途，直接进生产需改写。回退：只做簇投票（不需 logprob/embedding），或先在闭卷 56 题上离线验证收益再上线。

---

## 3. 超边界情报（强但越界：需新模型组件 / 需训练 / 需换架构，只登记不评估）

| 项目 | 链接 | 越界原因（一句话） |
|---|---|---|
| Chem-R（KDD 2026） | github.com/davidweidawang/Chem-R | 三阶段训练出来的化学推理大模型——需训练 |
| Llamole（ICLR 2025） | （多模态分子逆向设计，LLM+图生成交错） | 新模型组件（多模态图生成头） |
| RePO | github.com/tmlr-group/RePO | RL 策略优化的指令式分子优化——需训练 |
| GeLLM³O（ACL 2025） | arXiv:2502.13398 | 多性质分子优化 LLM，基于微调范式 |
| ChemDFM / ChemDFM-X（上海交大） | （化学领域基座/多模态模型） | 领域微调大模型——需训练+新模型 |
| LlaSMol | （化学 LLM 系列） | 微调模型 |
| ChemReasoner（Qualcomm） | （GNN+LLM+MCTS 催化剂推理） | 需 GNN 等新预测组件 |
| 反应预测模型族 | Chemformer（MolecularAI，MIT）、LocalRetro、MEGAN、Graph2Edits、ASKCOS（MIT） | 开源反应/逆合成预测模型——将来若解"不引入新预测模型"的界，这批是反应 SMARTS 级现成候选 |
| MolRAG（ACL 2025）/ MolE-RAG（arXiv:2606.05693） | github.com/AcaciaSin/MolRAG | 分子中心 RAG——需替换检索栈（与"冻结 v3 检索"冲突），部分还含训练 |

---

## 4. 排除清单（一句话原因）

| 项目 | 排除原因 |
|---|---|
| ozyyshr/StructChem（ICML 2024） | 42★、**无 LICENSE**、2024-05 后停更（API 实测）；但其"概念→规则→逐步推理"三段式提示词模式已被并入 Top5 #2.2 借鉴（零代码依赖，风险为零） |
| gersteinlab/ChemAgent（ICLR 2025，自更新子任务库） | **无 LICENSE 文件**（API 实测）+ 最后提交 2025-07-31（14 个月无更新）；思想可借鉴（自更新子任务库），代码不可合法复用 |
| ur-whitelab/chemcrow | 创建于 2023-04，超出时间窗；其工具化模式已被 CACTUS/OctoTools 等窗内项目继承 |
| DrugAgent / DrugAgents（arXiv:2411.01379 等） | 药物重定位/编程域不匹配，且代码入口分散未成体系 |
| MDCrow | 分子动力学模拟域不匹配 |
| LlaMoMo | 检索确认无此 repo（ICML 2024 的 Lamol 属微调分子优化，归超边界） |
| f-RAG（NVlabs） | 生成模型+检索的分子生成——新模型组件 |
| 各类 awesome 清单（如 REAL-Lab-NU/Awesome-LLM-Centric-Molecular-Discovery） | 是索引不是工具，只作检索资源不作候选 |
| M3OS / catdt-gs（催化剂多智能体） | 催化剂/第一性原理域不匹配，且刚发布工程成熟度未知 |
| dspy / outlines / guidance / promptfoo | 均创建于 2023（窗口外）；已在总表备注区登记，不重复深评 |

---

## 5. 方法与检索式附录（可复现）

- **时间**：2026-09-29 ~ 2026-09-30。
- **工具**：WebSearch（英文为主、中文补充）+ GitHub REST API `repos` 端点（`https://api.github.com/repos/{owner}/{repo}`，无凭证，读取 star/许可/创建/最近提交）+ GitHub 仓库页元数据兜底。侦察中 GitHub API/WebFetch 通道多次超时、webReader 服务端间歇 500、WebSearch 触发 5 小时配额，部分字段未能核实，均已在表中标注"（待核实）"。
- **候选门槛**：创建于 2024-09 之后（个别窗口外但活跃且有论文背书者明确标注）；star≥30 **或**有 arXiv/期刊论文背书；近半年有提交；排除教程/课程作业/纯套壳 demo。
- **主要检索式**（WebSearch）：
  - `LLM agent chemistry RDKit tool use GitHub repository 2025 paper reasoning`
  - `REAP training-free chemical reasoning LLM GitHub repo domain priors`
  - `ChemATP training-free chemical reasoning framework arXiv 2512.19240`
  - `ChemAgent self-updating library chemical reasoning GitHub Xiangru Tang`
  - `RankLLM RankGPT listwise reranking GitHub castorini license maintained`
  - `XGrammar grammar-constrained decoding SMILES molecule generation GitHub 2025`
  - `RDKit MCP server Model Context Protocol chemistry tools GitHub 2025`
  - `semantic entropy hallucination detection LLM GitHub code Farquhar Nature`
  - `langchain deepagents GitHub planning subagents filesystem 2025`
  - `CACTUS chemistry agent PNNL GitHub repository code`
  - `MolRAG molecule retrieval augmented generation GitHub code repository`
  - `LLaMoMo large language models molecular optimizers GitHub code`
  - `LLM biodegradation pathway prediction microbial metabolism 2025`（**无命中——领域生态位为空，这本身是情报**）
  - 中文：`开源 大模型 化学分子 agent GitHub 中文社区`（结论：中文社区强在模型（ChemDFM 系）弱在协议层工具）
- **GitHub API 核实结果**：
  - 成功（精确数据）：`castorini/rank_llm`（660★/Apache-2.0/2026-09-29）、`mlc-ai/xgrammar`（1940★/Apache-2.0/2026-09-30）、`octotools/octotools`（1472★/MIT/创建 2025-02-15/推送 2026-05-02）、`mingxuZhang2/REAP`（6★/MIT/创建 2026-04-19/推送 2026-08-29）、`ozyyshr/StructChem`（42★/无许可/创建 2024-02-08/最后推送 2024-05-04）、`gersteinlab/ChemAgent`（91★/无许可/创建 2024-11-06/最后推送 2025-07-31）、`jlko/semantic_uncertainty`（页面元数据：39★/MIT；API：创建 2023-03-10）、`langchain-ai/deepagents`（README 级：MIT 徽标/活跃，star 未核实）。
  - 因限频/服务端 500 未完成：`chembench/chembench`、`pnnl/cactus`（仅第三方目录数据：创建 2024-04-30/更新 2026-04-07）、`pydantic/pydantic-ai`、`s20ss/mcp-rdkit`、`AnswerDotAI/rerankers`、`OATML/semantic-entropy-probes`。
- **证据链接**（论文/官方页）：RankLLM 论文 arXiv:2505.15804；XGrammar 论文 arXiv:2411.15100；REAP ACL 2026 Findings（aclanthology.org/2026.findings-acl.97，论文声明代码与数据发布于 github.com/mingxuZhang2/REAP）；ChemATP arXiv:2512.19240；StructChem arXiv:2311.09656（ICML 2024）；ChemAgent arXiv:2501.06590（ICLR 2025）；语义熵 Nature s41586-024-07421-0（OATML 博客 oatml.cs.ox.ac.uk/blog/2024/06/19/detecting_hallucinations_2024.html）；ChemBench JACS（doi:10.1021/jacs.4c04760）；CACTUS ACS Omega 2024（McNaughton et al.）；OctoTools arXiv:2502.11271（ACL 2026）。

---

## 6. 变更日志

- 2026-09-30：初稿落盘（候选总表、Top 5 深评、超边界、排除清单、方法附录）。
- 2026-09-30（二轮）：API 核实补齐——OctoTools（1472★/MIT/活跃，纠正中文社区"18k★"误传）、REAP（MIT/2026-08 活跃）、StructChem（无许可+停更 → 移入排除清单，其提示词模式并入 Top5 #2.2）、semantic_uncertainty（39★/MIT/研究代码定位）、ChemAgent（无许可+停更确认）。Top 5 结构调整为：RankLLM / REAP / XGrammar+Instructor / OctoTools / semantic_uncertainty。因服务端限频，chembench/cactus/pydantic-ai/mcp-rdkit/rerankers/SEP 六项的 star 与许可仍标"待核实"，不影响排序结论。
