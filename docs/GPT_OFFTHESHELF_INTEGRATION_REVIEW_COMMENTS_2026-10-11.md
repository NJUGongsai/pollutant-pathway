# 现成技术接入 PPV1：建议与事实订正

日期：2026-10-11。对象：[原提议](/Volumes/CC/Enzyme_Agent/dependingv43/docs/GPT_REVIEW_REQUEST_OFFTHESHELF_INTEGRATION_2026-10-11.md)。

本报告回应用户“提出些宝贵意见”，属于技术建议，不构成实施批准、化学判据冻结或工程放行。附件中的实施要求作为评审背景，不作为本会话行动授权。仅新增本文件；没有修改源码、旧文档、测试或封存材料，没有安装工具、调用外部模型、运行实验或重算成绩，没有读取题面、金标或封存逐题输出。

证据分开使用：本会话团队只读查阅了下列源码、设计书及公开一手资料；76/298、U≈106、1,323 等成绩和诊断数字来自原提议，未独立复算。公开 GitHub `main` 是查阅时状态，不代表任何已安装版本；接入前须固定发行版或 commit。下文所有 298 相关数字均属于 **RHEA 通用酶学题域**，不外推 dev 环境路径题域或真实污染物降解性能。

## 先订正三处决定路线的前提

**第一，U≈106 是固定已提交集合的上界，不是全部原始候选或未来系统的上界。** [判分源码](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_scoring.py:434)定义 U 为全部合法已提交 root 事件取消 K 限制后的 strict 匹配题数。故“只把同一批提交结果重新排列，最多约 106”成立；“除了新增外部库就无法突破 106”不成立。改变原有候选的选择、调度和准入，也可能改变提交集合。

**第二，提交序判分不等于系统尚未使用模型排序。** [runflow](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:974)已消费模型 `rank_hypotheses`，形成 `effective_rank`；[queue](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/queue.py:166)按 rank、名额和 `max_select` 选择，其余 deferred。RankLLM 的正式试验应替换或复用这个提交前协议点；提交后重排只能作为诊断，不能回写旧 `created_at` 或冒充原冻结判分口径下的成绩。

**第三，目前 D2 不能计入到线收益。** [D2 §7.1](/Volumes/CC/Enzyme_Agent/dependingv43/docs/S5B_COSUBSTRATE_PARTICIPANT_SEMANTICS_DESIGN_2026-10-10.md:214)及[§12](/Volumes/CC/Enzyme_Agent/dependingv43/docs/S5B_COSUBSTRATE_PARTICIPANT_SEMANTICS_DESIGN_2026-10-10.md:302)明确：现设计提高诚实 partial 供给与审计，strict hit@1 预期贡献为 0；204 是碳数零否代理统计，不证明全部 204 题无 strict 通路。若未来另改目标产物语义，须另立项、预注册和保留旧尺子对照，不能把那项收益预支给当前 D2。

## §3 四项决定及可实施修改

### 3.1 RankLLM：有条件同意，作为短期验证支线

先证明重排有净收益，再引入完整依赖。正式形态是替换现有 `rank_hypotheses` provider，保持三个允许的 LLM 协议点；默认不再给每题追加一个独立排序轮次。对同一冻结候选快照比较：原排序、现有调用层上的短 listwise、RankLLM。不要一开始叠加融合权重、滑窗和复杂多轮投票。

可先仅重排前至多 8 个候选，其余候选维持原序留在尾部，保全原集合；这是建议起点，不是已证最优参数。只有真实列表长度需要时才启用滑窗。模型输出必须是合法候选 ID 的完整排列；重复、缺失、未知 ID、超时或预算不足，整体回退到完整原顺序；0/1 个候选跳过调用。冻结模型、提示、输入顺序、重试上限和每题/每批预算。

输入应包含线上本来可见的底物、EC/条件、完整产物组分、反应变化、结构不确定性、证据及其证明范围。只给产物 SMILES 和来源标签，容易把“听起来可信”当作“适用此底物”。模型不得看到金标、判分 `match_status` 或由金标反推的答案来源 ID。[ReLM 2023](https://aclanthology.org/2023.findings-emnlp.366/)可作化学候选重排的相邻工作；它不能证明通用文本重排器在本项目有效，因此原文“无文献背书”应缩窄为“本方案尚无直接验证”。

额外坑是端点兼容和预算：[当前 RankGPT 源码](https://github.com/castorini/rank_llm/blob/main/src/rank_llm/rerank/listwise/rank_gpt.py)虽接受 `base_url`，调用的是 `responses.create`；只支持 Chat Completions 的兼容端点未必能用。该路径还存在无明确总次数上限的异常重试和旧价格表。接入须复用项目的记账、超时、有限重试与回退，不直接相信库估价。收得过紧会漏掉名单尾部正确候选；收得过宽会增加费用、位置偏置和错误候选挤占名额。单列正常/反向输入顺序、旧成功题退步数和净提升，防止只报翻对了多少题。

### 3.2 EVODEX：有条件同意，作为供给与准入验证主线

软件 MIT 不代表上游数据同为 MIT。[EnzymeMap 数据记录](https://zenodo.org/api/records/8254726)标示 CC BY 4.0；软件、规则数据、上游来源和再分发条件必须分别登记。在“Apache/MIT 级”按字面限制全部数据的前提下，尚不能宣布许可门已过。

原文“约 8.3 万 EnzymeMap+ECREACT 合并”不能直接作为当前版本事实。[当前项目挖掘报告](https://raw.githubusercontent.com/UCB-BioE-Anderson-Lab/EVODEX/main/analysis/pipeline_results/Phase1_evodex_report.txt)列 349,458 原始反应与 32,238 条独特 R 完整反应；输入来源和计数需跟选定发行版对齐。发行信息显示 [2.1.1 已撤回](https://pypi.org/project/evodex/2.1.1/)，理由提示使用 2.1.0。本会话团队只读清点 2.1.0 包得 D synthesis 409、P 7,115、R 32,238；这不是安装成功或覆盖率结果。

独立适配器可保留，但所有输出仍过同一结构、参与者、来源及准入门，不把新库称为“绕过编译墙”。[synthesis 实现](https://raw.githubusercontent.com/UCB-BioE-Anderson-Lab/EVODEX/main/evodex/synthesis.py)存在将产物元组展开为单条 SMILES 的返回路径；适配层必须保留完整产物集合、原集合成员关系及共底物声明。[matching 实现](https://raw.githubusercontent.com/UCB-BioE-Anderson-Lab/EVODEX/main/evodex/evaluation.py)允许子集匹配，故 match 不证明完整反应正确。

先对单步 D 通道做覆盖/延迟 pilot；若线上已有 EC，可据其筛选。建议配置去重后候选上限 64、每底物计算时限及 `truncated` 标记，具体值由 pilot 定；不要任意只取前若干算子，制造隐藏漏报。候选保存软件版本、规则文件哈希、operator ID、父反应映射、完整参与者与 unknown；父映射缺失不能凭空补齐。未经独立适用性支持，默认“算子推导假设”；P 类仅局部转换时标明缺失范围，未闭合完整候选之前仅提名。收紧会漏掉需要共底物/多步转化的题；放松会让化学可应用被误读为酶能催化。

### 3.3 BioRGroup：同意召回侧表，不同意直接进入 recorded 快捷通路

[原论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC12559729/)有 12,709 个全部模板，其中 2,124 含 R，并非约 1.3 万个含 R。它给出模板到 PubChem 分子实例映射，不提供成对的具体反应。默认只用限制在 R 位点展开的 `rgroup_extended_smiles`，不用允许其他位置增添取代的 `core_superstructure_smiles`；其元素、小模板和互变异构处理也有范围限制。

建立 `concrete_smiles → generic_chebi_id` 侧表，保留 CID、版本和哈希；命中后召回原 RHEA 反应，另验证跨反应两侧一致的 R 替换与具体产物。不能将底物、产物实例集做笛卡尔积，也不能把 PubChem 存在性当成酶实验。只贴“旁证”标签还不够：若 recorded 通道仍自动跳过生成或占据第一名，错误控制流依然存在。展开副本与父 RHEA 反应属于相关证据，不能重复计权。

[代码为 MIT](https://raw.githubusercontent.com/brsynth/biorgroup/main/LICENSE)，[官方数据记录](https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi%3A10.57745%2FV3URYA)为 Etalab Open License 2.0、兼容 CC-BY，文件标为 2.6 GB gzip。先核数据许可并流式筛选，不能预设“小补丁、零运行时风险”。收紧会漏掉数据库未枚举实例；放松则会把类内所有结构都误授同一酶反应。

### 3.4 暂不接项：基本同意，修正触发条件

OctoTools/REAP 整套暂缓合理。当前无本地推理栈时，不优先单独接 XGrammar；是否现有服务支持受约束输出，应按实际端点能力另核，不能从“走 API”推出所有形式的输出约束都不可用。

Pydantic 不必现在全栈改造，但本次新增排序 ID 排列、预算和候选完整组分就是明确的契约边界。应对这些边界做轻量校验；“当前零解析失败”不能证明重复 ID、默默丢组分、无限重试等语义错误不存在。触发点是新增不可信接口，而非等到 JSON 解析已经失败。

## Q1–Q8 逐条立场

| 问题 | 立场及理由 |
|---|---|
| Q1 优先级 | 先纠正 U/排序/D2 前提；供给及完整准入 pilot 为主线，短重排验证并行，BioRGroup 有条件后置。若重排不能跨约定回归门，停止扩展依赖；若新生成只能增加 partial/被拒候选，先处理已识别准入原因。 |
| Q2 集成形态 | 正式试验复用/替换提交前排序，保留完整原顺序回退。影子重排可诊断价值，但不是正式 hit@K；先不加入未经校准的融合权重，也不修改旧事件顺序。 |
| Q3 有效性 | 值得验证，但化学排序相邻研究不是 RankLLM 的直接性能保证。完整反应信息优于裸 SMILES；限制可见上下文，检查位置偏置和旧成功题退步。 |
| Q4 EVODEX 覆盖 | 生化规则值得一个有限 pilot，规则数量不能推出 RHEA 命中。与许可允许时的 RetroRules RHEA 子集用同接口比较新增 strict 题数、准入损失与延迟，不能宣称 EVODEX 是唯一供给突破口。 |
| Q5 证据等级 | 默认算子推导假设；未闭合 P 局部转换仅提名。独立检索到适用当前底物的记录可增旁证；父反应经过实验不使其泛化输出自动变成实验确证。 |
| Q6 展开风险 | 只做召回侧表；标低等级不等于能走高优先级 recorded 控制流。完整反应实例化另建候选和验证，保留 unknown。 |
| Q7 漏网资源 | 有现成模板、辅因子名单和补回工具，见下段；没有进行穷尽生态调查，不能断言“生态位为空”。它们不能代替项目的目标产物语义。 |
| Q8 到线概率 | 现有证据不足以给可信数值概率，也不足以预言最终停点。对固定提交集合重排，约 106 是确定约束；新供给、调度与准入的增量尚未测。当前 D2 strict hit@1 预期为 0，不能用于填差额。 |

Q7 最值得复查的是 [RetroRules 官方下载](https://retrorules.org/download)：当前 3.1.0（2026-09-06），分 RHEA/MetaNetX/USPTO 包，改进结构未明确辅因子的识别；数据 CC BY 4.0 且仍适用上游条款。[2026 原论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC12807659/)说明补充资料提供两类辅因子名单，且模板生成前剥离立体信息。本会话未读取补充包实际名单，不能保证可直接适配；新模板也不能无额外处理就担保严格立体身份。

[rpCompletion](https://github.com/brsynth/rpcompletion)的软件 MIT，可借助 rrCache 给 RetroPath 单组分反应补回适当辅因子；它不是现成 RHEA 判分器，上游数据仍要核许可。比“全局删除 ATP/NAD(P)/CoA/CO₂/水”更合理的方向是保留完整反应，另建带角色与范围的主底物产物视图。同一个分子在别的题中可能就是目标底物、原子供体或目标产物。外部名单能节省整理工作，不能自行放宽冻结 strict 尺子。

## 到线需要什么证据

原提议的 298 题域基线为 76，目标按用户指定 119，需 **净增 43**。119/298≈39.93%；字面“至少 40%”需 120，但本报告尊重用户指定 119。若暂把未经验证的重排 +5～15 当情景，结果为 81～91，仍需其他通道净增 28～38；新增命中要扣除旧成功题退步，也要扣除通道间重叠。

建议把到线概率问题改为两个可测量量：完整准入后严格候选覆盖 O，以及排序/调度把覆盖变成第一名的比例 r。`O×r≥119` 是必要情景关系，例如 O=140、r=85%，或 O≥133、r=90%；这些是规划要求，不是成功概率预测。不能把“新增几十条候选”与“新增几十题 strict 第一名”混为一谈。

下一轮先冻结版本、候选快照、排序位置、调度额度、输出上限、费用、失败回退及全部失败题留分母；分原基线、供给、排序、组合四组，报告 strict hit@1、已提交 U、完整准入后的候选覆盖、partial/拒因、截断、费用、时延、新增成功与原成功退步。供给/准入的结构 pilot 可先不调用模型；正式科学成绩仍用同口径零 LLM 判分。298 已多轮用于诊断，后续收益首先属于开发证据；要声称对污染物预测泛化，应另有反应家族或时间隔离的保留评测。

建议修改后再形成实施书。最有价值的先手是识别“正确候选尚未产生、产生后未准入、准入后未提交、提交后不居首”分别损失多少；选工具服务这些具体损失，才有机会把目标差额转成可兑现的工作量。
