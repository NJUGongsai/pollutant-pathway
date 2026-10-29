# PPV1 S5b HIT50 提升、复审与298复测任务书（2026-10-09）

状态：`implementation_authorized / scientific_target_pending`。
任务链：实施agent完成代码与离线自审 → 交回本聊天主agent复审 → 新登记 → 同模型真实298 → 零LLM判分。
用户已授权本聊天主agent在实施完成后复审并重测298；本任务不另设重复授权停点。
实施agent不得越过用户指定的“先复审”分工，自行点火或多跑真实批。

## 0. 目标、基线与完成含义

本任务默认验收目标：**298题域主口径matched_strict hit@5 ≥150/298=50.34%**，严格超过50%。
用户若随后指定hit@1/@3或其他已存在指标，调整目标字段与验收主列，不修改scorer判据；实现阶段继续推进。
旧报告主@1/@3/@5为39/72/74（待授权聚合核定），因此默认@5暂缺**净76题**；若改@1缺111、改@3缺78。
缺口是净新增：保留旧命中、新增命中、丢失命中分别披露，不能把17失败题、258拒因、35近似题相加作收益承诺。
旧C0老口径@5=186、112题零模型recorded直通、首位recorded182，是既有汇总的潜在供给线索，不能保证严格150。
本轮必须实施真正改善候选供给、可执行性和排序的工作包；仅修gate/账本而结束，不算性能任务交付完成。
编译接受率、测试绿、Codex放行均不等于科学目标达成；最终只由新批同口径150/298判定。
结果定位为`seen298_post_hoc_repair_check / known_evidence_reconstruction`，不称独立held-out推广，也不外推dev环境路径题域。

## 1. 开工基线、权限和不可改的尺子

开工前读AGENTS.md；已核实际HEAD `0d86c48a26822cccfadd7818fec08279d6d55089`，相对57ea99b所查src/tests无变更，末提交仅交接文档。
实施前再次记录实际HEAD、工作树、src/vendor/依赖/资产身份；保留他人未提交和未跟踪文件，不重写历史证据。
授权修改：本任务所需源码、合成测试、新交付书、新规则级化学评审请求与新证据；不顺手重构legacy发布默认值。
实施与自审：零真实模型调用、不读298题卷/金标、不读旧答卷或封存逐题run，不提交到远端、不push、不部署真实批。
只有明确授权的已封存**预测侧完整响应**可另行在隔离副本离线重放；当前默认用合成响应，不自行找旧账本。
响应只有截断摘要、不能确认原始完整性时标`replay_unavailable`；不猜补、不补调用、不因不可回放剔除298分母。
后续受权builder可在数据转换阶段读题卷生成参考图；承载内容只留gitignored/合法仓外根，与预测白名单分离。
预测输入限授权底物及既有许可证据；pool-provider只消费substrate，不按qid语义查答案，不接金标、参考图、旧正确source ID。
金标只在答卷封存后的受权确定性评分进程用于判分；评价反馈只回传批准的计数，不回传目标结构或oracle排序。
冻结：strict身份/CN含义、participant集合与step_scope、match_reference_edges、主K候选定义及(created_at,event_id)顺序、分母298、失败规则。
不得以忽略共产物、canonical tautomer、中和电荷、乱加立体、过滤失败题或从多个答案挑金标最接近者过线。
新协议/编译/排名/资产策略必须进新身份；旧run、旧冻结预注册/判据、历史报告及S5B_PASS_LINES历史含义不改。
允许最小批准门/报告完整性修复，但计分函数行为必须有前后同输入等价证据；新目标另建字段，不重定义旧通过线。

## 1.1 防止为298硬调效果：承认适应性评测，保留泛化边界

298已经被观察、诊断并用于目标驱动迭代，因此本轮是**已知集合验收/适应性评测**，不是独立盲测。
预测侧不读gold能阻止直接答案泄漏，但仍有按aggregate反复选方案的适应性过拟合风险；不能承诺“完全没有过拟合”。
反复依据测试集反馈调整假设，可能对测试集本身过拟合，方法学依据见[Dwork等，NIPS2015](https://proceedings.neurips.cc/paper/2015/hash/bad5f33780c42f2588878a9d07405083-Abstract.html)。
保持150/298验收目标，但每项改动必须写通用机制理由、适用范围及独立构造正负控，不能仅写“这几题这样就对”。
禁止qid/本卷题目/目标产物/gold reaction ID定制，禁止把历史C0答案索引洗成语料、逐题best-of拼接或oracle排序。
阈值、提示词、池宽与融合规则优先用**预先冻结独立开发集**选择；与298按strict底物、重复组及近邻化学/同来源记录簇隔离。
如有合法现存独立开发集先复用；若没有，用事先构造并冻结的合成正负控和许可corpus非298样本，不假定已有真实开发集。
既有dev56已用于多组采样/调参，只能叫development，不能拿作独立holdout；见[既有S1报告](/Volumes/CC/Enzyme_Agent/dependingv43/docs/HIT60_S1_CHANGESET_REPORT.md:29)。
dev与298排重/资产泄漏审计目前只是既有文档声明，本任务未核底层manifest；用于开发比较前核strict/CN重复、近邻及来源/路径组隔离。
相邻题也须group split，不能同一路径邻步随机拆分；未核隔离者只做工程合成/契约验证，不声称dev成绩是独立证据。
[既有S2任务书](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_V43_HIT60_S2_BLIND_TEST.md:3)仍待新题源，[S1预留记录](/Volumes/CC/Enzyme_Agent/dependingv43/docs/HIT60_S1_CHANGESET_REPORT.md:56)盲测预留0；目前没有已证明独立未见测试，不能虚构已有盲卷。
既有汇总“209个unique底物/53个重复组”为待核分组声明；先确认定义，分组split，不能把同底物多题随机拆进dev/test。
近邻结构、同反应记录/来源、预先已见题与资产时间都登记；仅改SMILES拼写不算不同底物或独立样本。
预先存在的授权文献/反应记录可作grounded evidence，但要审计语料生成时间、来源和独立于本卷gold的生成过程。
已知证据重建允许合法corpus覆盖，不等同unseen泛化；对未来未见集明确资产暴露/重叠范围，不隐藏训练或检索覆盖。
独立未见集只能在方案冻结后评测；曾用于调参的旧holdout不得继续称盲测，也不能因表现不好再择新holdout。
本轮不新增付费holdout测试，不因未找到独立集阻塞通用修复和已授权298重测；暂无独立集时明确“298达标，泛化未验证”。
每次修改与评测前后冻结并逐次公开完整批，承认298反馈影响了后续方案；不能只发表最佳批或声称单批证实因果。
U/H5/L仅aggregate诊断，用来选择通用供给/排序问题，不将逐题gold信息或oracle候选排名回传预测侧。
known_evidence_reconstruction与held_out的既定含义见[旧S5b预注册](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md:53)，新任务不得把其升为盲测。
结构/反应近邻及数据偏差的审计背景参见[Kovács等，Nature Communications 2021](https://www.nature.com/articles/s41467-021-21895-w)；论文阈值不移植为本任务检索参数。

## 2. 共用交付与入口矩阵

开工列`asset lookup/build → compile → payload/parse/prepare → execute → donor/audit/admission → store → export/score → resume/replay`。
每入口登记消费的身份、事实、版本、source/proof_scope、允许unknown/unsupported和拒因，复用同源helper而非多处独立补丁。
所有性能候选，包括exact recorded、analogy和novel，都经同一production/audit/admission/store链，不直接插事件/假设行。
recorded来源存在不证明酶机制或当前条件可行；无条件/机制/外源原子依据时保留unknown，不授全覆盖/R6。
证据探针在新的/tmp隔离src副本执行，含vendor、必要metadata；`python -B`、禁字节码、pytest `-p no:cacheprovider`。
记录实际HEAD、schema、输入/命令/输出/哈希和执行到的最后入口；未走audit/store的工具探针不能报公共链通过。

## W0. 先闭合数字和候选漏斗，不凭猜测修成绩

公开汇总存在以下冲突，先出零金标勘误表，不能从疑似any-of/不限K混接猜官方真实值：
- both74+old-only51=125≠老@5的122；联合表必须注明K/身份/候选宇宙，逐K四格总和298。
- 来源21+35+170+71=297，命中14+14+60=88，不等于主74/老122/any-of125；补missing/unclassified并明确阶段/口径。
- 池深分布合计298、均值1.18456、空池40.27%可闭合；深度≥3按分布是49，不是43。
- uncovered互斥应为14+21+19带假说mid+84带假说far+49零假说=187；原mid23含4零假说，不能再加49。
- “298成功+4错误”与每题一请求冲突；292可解析+2不可解析+4调用层错误=298只是待核分母线索。
- 文中token按0.8/2.8价算14.2196元，接近全量14.2168而非含冒烟14.7796；分段核调用/usage/均值/费用。
- 拒因次数726超过失败尝试306，按distinct proposal/attempt/qid及拒因交集报告，258不等于258题。
不能独立核定的旧数字标`unverified`，交授权汇总流程核；不阻止已证源码缺陷修复，也不改旧冻结判分产物。
来源漏斗至少含raw检索→解析→对齐→编译→可执行→strict_target→获许可→提交→可报告，按source和统一单位去重。
analog-only21题是留存后的选择组，未核的66.7%不能当降阈值后的命中概率；Tanimoto分带不能单独认证方向/互变错误。
新增评分侧合成验证的**聚合诊断**：U=全部合法已提交root事件的strict匹配题数；H5=正式strict@5；L=U−H5。
U只取消K作候选覆盖上限诊断，不改正式尺子；若U<150优先供给/生成，若U≥150而H5<150才主攻排序。
诊断仅由后续封存评分隔离进程读真实参考；向预测侧不得返回逐题目标、reference、正确source ID或oracle事件顺序。
至少断言0≤H1≤H3≤H5≤U≤298；判分互斥桶总298、运行状态附表总298，叠加桶不重复计分母。

## W1. 共同compiler闭合；已证缺陷不能只修aromatic词

入口：s5b_builder `_template_to_spec:415/_bond_diff_edits:488`，donor_applicability transform/align，atom_tool render/validate/execute，production/audit。
1. lhs/rhs按**atom-map number**联结，不按两侧解析idx；拒重复map、坏引用、保留原子改元素；原idx只作临时索引。
2. 在当前底物施加供体变化，保留未覆盖旁基和必要组分；目标、expectation、edits、中心由同一迁移结果产生，不能复制donor rhs。
3. donor中心与alignment键同一供体命名空间，current IDs在映射值与当前edits；不得以S中心配D键伪称已对齐。
4. 共用一次确定的current执行base/ID-labelled bonds；from_order从该图读，目标芳香指派与映射及未变区域共同约束。
5. 两侧独立canonical Kekule仍可能6键反向；去map也非充分修复，不能仅补canonical=True或全面拒绝aromatic换通过。
6. 新原子ID符合ATOM_ID_RE且无冲突；add_atom自动接single锚定键，不再次form同键；新double/triple先成single再变阶。
7. 多新增原子按有依据锚点拓扑顺序处理；电荷/H/立体等现协议不支持时稳定`unsupported`，不能用空edits冒支持。
8. 编译后validate+离线execute+完整target/center诊断，再进入可执行pool；失败有结构化原因，不吞全部Exception只回None。
9. 重复state_ref在计划生产者按distinct状态生成唯一调度条目，保留事件参与物/occurrence/计量语义；不以writer强弱合并洗损坏。
10. “expanded>deferred>not_tracked”不是通用化学优先级；真正互斥状态和损坏权威记录仍拒，完整性守卫不放宽。
至少**12组合成正/负控或诚实unsupported**，各组列公共链最后行为，保留合法已有正控：
| 组 | 必须覆盖 |
|---|---|
| 1 | ordered乙醇→乙醛正控；同map rhs反写不能变成C=CO，结果与有序式等价 |
| 2 | 乙醇模板迁移CCCO→CCC=O，spec/expectation保留额外C，不能仍CC=O |
| 3 | donor中心S/D namespace错配负控，单改中心到合法供体ID正控center=True |
| 4 | 新O合法ID正控、原S_O_N1坏格式负控，未知/撞ID拒 |
| 5 | add_atom自动锚定单键不再form；重复成同键明确拒 |
| 6 | 新double/triple真实形成；仅form导致single的旧行为被覆盖 |
| 7 | mapped donor/unmapped current benzene共振错位，合法去芳香化能执行 |
| 8 | 去map donor benzene/current toluene仍共振错位，旁基与from_order闭合 |
| 9 | 杂芳香/稠合与芳香化正控；非法价态/无法执行表示不伪通过 |
| 10 | charge-only、stereo-only空edits不一致诚实unsupported；未参与中心的事实保真 |
| 11 | 重复map/元素变化/对称对齐不同目标拒或ambiguous；等价映射保留正控 |
| 12 | 重复产品计划经production→store→export/replay正控；真实冲突/悬空引用负控 |
此前13项化学helper断言只走到工具/供体诊断；本轮必须补audit/admission/store/replay，不能叫13个仓库pytest或性能证明。

## W2. 既有授权exact recorded源适配PPV1，作为主要新增供给

复用`EngineReactionFinder.find:192`及211–268记录分组、`V43Engine.expand_raw:357/lookup:378/asset_identity:299`、recorded_eligibility_reasons。
只用已授权且哈希校验的corpus；新增公共exact wrapper可以，builder不得越层抓engine私有对象；legacy默认similar开关不变。
禁止搬C0/旧run答卷、qid→答案表、参考图→池、按本卷命中补资产；许可先于本轮，源范围与哈希可审计。
现exact查询是电荷归一立体盲CN，base_card会回填current且mapping unavailable；卡名“exact”不等于PPV1 strict。
按原生source record ID/hash回读真实reactant、方向、**完整净产物集合**、角色/系数/条件、过滤声明及mapping证据。
分`recorded_strict_exact / recorded_cn_candidate / analog_transfer`，不把CN近似、另一底物或反向记录升级strict exact。
一个原反应多产品构成同一事件；不同原反应是备选事件，不拼共同产物；结构重复合并需保留全部来源与条件边界。
过滤过的单产品卡不冒充完整record；不机械删无机/辅因子迎合gold，原生覆盖不足保持partial/unknown并披露。
有原生mapping走W1；无mapping可实现有版本/枚举预算/歧义披露的确定性结构对应编译，标“推断映射”而非原生/机制证据。
图差必须约束元素对应、旧原子保全、离去组分、新原子来源及完整target；不能任意首MCS、补原子或删旁基。
无法编译留下unsupported/source诊断，不假装AtomTool执行成功，不直接recorded提交；所有获许可事件仍走共同公共链。
若实施认为必须新增source-only提交路径，先交清楚设计/proof_scope/正负控供主agent复审，不擅降proof或绕AtomTool。
单一合法strict源可预注册0模型确定性候选；竞争源保留备选，不因唯一主产品封锁其他已冻结合法方向。
正控：合成授权格式source单反应/双产品、同底物双反应、明示推断映射、未知条件不授机制verified。
负控：源hash篡改、CN同而电荷/手性不同、方向反、另一底物、filtered记录冒完整、缺产品/来源、映射触顶。
交exact→完整源→编译→提交计数和unsupported分层，不能用旧186或source卡数量宣称150可达。

## W3. 真正选择和排序贯穿到事件，保持scorer事件序

源码问题：runflow1105–1111只把调用前pool IDs映射rank；novel895–909后追加，941按池后index fallback，模型首位可能丢失。
833–868还prepare全部池，不按parsed pool proposals筛选；必须明确“模型选择”与“确定性fallback”两个版本化规则。
构造完pool+novel后统一logical proposal ID→prepared hypothesis ID→净反应签名→effective_rank→实际提交event。
记录model_rank、effective_rank、rank_basis与资格/拒因；所有显式有效rank先于未rank fallback，novel不因来源被排后。
模型未选池不隐式抢前5；允许的source deterministic/fallback配额在新策略冻结，不能score后重排事件。
同净产品集合+step_scope+参与物语义去重、合并provenance；不同反应/条件/角色不能只因主产物或CN一样被误并。
最多8个可执行备选尝试，优先优化前5次成功root事件，剩余预算内合法root事件仍提交并纳入U；适度多样性不能硬凑无效方向。
拒绝候选的候补只来自已冻结候选集；所有成功root事件仍按实际(created_at,event_id)供原scorer计K。
domain.models.now_iso:74–75当前秒精度、events.event_id:127–131为hash；同秒事件即使按模型rank先提交，也可能被原scorer的hash字典序重排。
必须以**原scorer最终候选rank**验收，补同秒tie反例与合法正控；不能只看queue/model_rank或声称先提交就必排前。
权威events表store.py:1949–1961首次INSERT会重记now_iso，未采用PathwayEvent.created_at；仅改dataclass时间无效。
新版本公共writer须忠实记录首次实际提交的高分辨率时间，重放不刷新并冻结版本/身份；不造时间、不改event_id迎合rank、不改scorer排序。
时间正负控必须穿过store→native_export→原score；旧表/旧批时间只读，不回填或补造历史时间。
正控：8池+首位novel，budget8时novel实际被选且在原scorer得rank1；交错序到export/replay和同秒tie行为一致可解释。
负控：未知/重复logical ID、缺rank歧义、未提交event出报告、未rank池抢前、不同净反应被误去重。
说明主K=事件、老K=每事件内有序报告产品字符串展平；产品宽度不是备选数，不改宽度换新strict分数。

## W4. 编译后补位和有界输入侧动态检索

候选配置建议固定：raw top24、最终可用pool8、compiler/对齐枚举预算另明示；超过预算诚实unknown。
先阈值0.45；可用独特候选不足预注册目标3时，仅按输入侧条件降至0.40，仍raw≤24、pool≤8，不支持不强补满。
原top8里失败不补位是已证源码问题；正控raw前8均unsupported而第9合法，必须可补入。
模板先按相似度/稳定source序召回，编译成功再去重/融合，不能key字典序无意覆盖原检索排名。
明确exact与analog的融合/配额、raw预算和pool8的计数单位，重复多source不重复挤占独特净反应槽。
使用同源全对齐/中心适用性，等价目标合并、非等价对齐列备选或ambiguous；错中心/电荷/H不因低阈值放行。
可在固定独立非298合成/授权corpus开发集合比较0.45与0.40，开发前冻结集合/hash、候选配置和选择准则。
实施期只做零模型结构/执行统计；后续授权aggregate开发评分也不得回传逐题目标/source IDs，不按本卷gold调参数。
阈值与适用性若一起改，注明复合策略；想分离效应用离线2×2，不从一次全量混合结果分别归功。
W0的U/H5/L告诉后续轮主攻供给还是排序；U<150时不能只反复调ranker承诺过线。

## W5. 同一执行图载荷、中性单步任务与有限候选容错

payload由W1同一helper输出ID→idx/元素/charge/H/必要stereo、ID-labelled实际键表、mapped SMILES、图hash与能力版本。
避免模型自行猜RDKit解析/Kekule；edit order按实际single/double/triple，合法小写芳香product SMILES仍可用。
system任务改成中性“酶促单步转化”，覆盖适用氧化/还原/转移/水解/裂解/异构/连接，不专偏degradation。
底物不足以唯一给酶/方向；只提有功能团依据的多个合理净转化，不捏造EC、条件或强制氧化深度。
一次响应至多8个不同净反应，完整产品/参与物scope与必要未核条件，模型给偏好但不做判分或机制授信。
短提示词和合成协议示例教合法ID、自动锚定、单步、完整组分及unknown；不输出长推理，不固定所有产品为酮/内酰胺。
能确定性计算的图差/一致性放compiler；新增字段同步parser/schema/validator/version和所有公共入口，不只改prompt。
有限容错：单条模型无效SMILES/不支持编辑，在共同prevalidation逐条拒并保留合法候选；全坏诚实empty。
整JSON不可解析、权威记录身份/内容损坏、真正audit/store契约违规仍run拒；不能catch-all把损坏洗成方法失败。
语义候选拒绝不反馈模型再猜、不改SMILES“修到能过”、不向模型提供gold；protocol升级且正负控覆盖所有入口。
charge/H/stereo-only可初版unsupported，但必须交能力覆盖诊断；若大量exact source受阻并影响150可行性，升级有界实现方案交复审。
可选同轮新属性op从formal charge/H/stereo最小集合开始：from属性前提、to属性、原子对应、实际执行与证据重算同源且版本化。
立体保真按实际配体对应，不能只保持CIP字母；来源/条件不足仍unknown，不能自动中和/补氢/加手性碰gold。
编辑表达能力扩大不等于放宽strict身份/许可判据；若后者确需变化，拆独立请求先review，不在本任务暗改。
不默认强迫完整化学编辑大改，也不以“四op不支持”结束性能任务；未实现能力/触顶/歧义及其覆盖缺口交付清楚。
正控空池novel/非空novel优先/多方向/一坏一合法；负控all坏、错图hash、非法价态、备选冒共产物、未支持变化漂移。
费用字段分input、visible content、billed output、reasoning（若provider有）、usage unknown与延迟，不用短JSON推计费成本必降。

## W6. 最小运行时闭合，不开展大重构

R1批准状态共用枚举白名单：approved/confirmed/preregistration_confirmed；rejected/空白/not_approved/pending/未知拒，归一helper也验证。
R2每次gate acquire有占位ID，所有200/400/503/429/鉴权/timeout/解码路径恰一次release；未acquire不release，重复release幂等。
父协调者只回收已确认死亡owner的占位，活长请求不因TTL释放；total_requests不退，unknown活跃状态不得清零后继续付费。
保留flock+原子JSON，新schema仅新批；gate参数首消费/恢复核对，峰值≤40；无需Redis/多机/自适应并发。
R3完整最终content先原子blob保存、SHA/字节/字符/引用校验再responded；摘要可截断，权威响应不可截断。
blob缺失/篡改/持久化失败不能授可重放；>20K与中文响应即时parse和blob重放同义，crash正负控不生成假responded。
固定1logical的resume：responded+有效完整blob须零调用消费既有响应继续同一公共链，补合法首次消费/重放入口。
仅保存blob不等于恢复：当前ppv1_real_fetch会对responded报request_not_consumable，必须覆盖该状态正控。
sent但无完整blob保守unknown/failed并占额度，禁止现real_model:341–360孤儿自动新logical请求；未知费用不凭空退款。
R4共用validated case reader绑定qid/run_id/schema/批与计划身份/终态/export_digest；验证后才SKIP、汇总和评分。
env_check_only另文件，不写正式completed；case原子replace；合法terminal_failed留分母且不因低分重跑。
单协调者flock与run锁并存；坏completed/外qid/错digest/错identity拒；死亡未封存恢复只有一份最终case、一次评分。
R5首批每qid最多**1次逻辑proposal**，合法deterministic recorded可0；格式反馈0、题级/适配层新logical retry0。
仅HTTP429按同一request/idempotency key做冻结有界传输retry；空/坏响应、timeout/429耗尽均失败，不新logical请求。
显式`max_http_retries=4`表示初次+4重试=5总HTTP尝试；298×1×5=**1490**理论gate cap，不盲用旧894。
这是新配置数值，不声称旧真实env也用4；模型身份须包括retry/timeout参数，变化拒同批resume。
冻结解析后**实际生效配置**：retry、HTTPtimeout、request_params和无密钥provider endpoint身份；worker从冻结值装配并拒env冲突。
不能只登记默认4/timeout0却允许env静默覆盖；凭证继续只env内存，无回显、无入identity或日志。
worker_total_timeout支持0禁用/正值生效，首批默认0沿现政策；负值配置拒，非正值不得隐式kill而少跑题。
正值模式monotonic总时限、terminate/grace/kill与死亡占位对账；stderr独立有界日志/主动drain，防PIPE阻塞。
401/403/402停止新付费；不明“provider收到但本地失响应”保守计预算/费用，不声称远端exactly-once或自动重发。
合成验收HTTP各结束路径、预算0/1、新logical禁发、死亡/活worker、参数变更resume、case污染/双协调者、完整响应重放。

## W7. 公共链证据、定向回归和有限交付

把W1十二组、W2source、W3排序、W4补位、W5容错和W6运行时都登记到入口矩阵并执行正负控，不能仅列测试名字。
每性能路径至少一合法实例走prepare→AtomTool→donor→audit/admission→store→export→resume/replay→合成score。
authority损坏、unknown/partial、unsupported和合法精确正控同时保留；不以全面拒绝换工程绿。
先定向跑受影响compiler/atomtool/donor/protocol/runflow/rate/case/pairing测试，完成仓规**required PPV1+G01**。
入口版本/公共协议改动需要相关回归；按现交付要求必要时一次完整回归，过后没有新改动/失败不无限重复。
提交只含任务源码/合成tests/新交付与规则级评审请求；证据按AGENTS默认留未跟踪/隔离，实际dirty情况如实列。
至少交mimo规则级化学请求md，自包含、零gold；已有用户规则级送审授权按现scope执行，不新起外发流程或由实施agent调用模型。
交付状态`implementation_ready_for_review`，返回本聊天root复审；有未执行内部控制/失败/unsupported如实列，不发“目标完成”。

## 3. 复审后新预注册与真实298（单协调者执行）

主agent复审有有限阻塞则回修并再交付；复审通过转`ready_for_real_retest`，用户已授权随后真测，不另重复求许可。
新增预注册/发车登记，不改旧冻结稿；首次真实调用前冻结新target、代码/资产/protocol/prompt/池/融合/排序/profile/模型身份。
冻结同模型GLM-5.3-Flash的现有授权provider，temperature/请求参数沿有效单通道显式入身份；不默认换模型、多模型或多成功样本。
首批profile depth=1、最多8备选、产品展开width=2、1logical/题、format0、HTTP retries4、workers/max_in_flight40、RPM180/TPM2.7M。
原价只作估算，发车用**同日价格快照**；完整请求/HTTP尝试/成功响应/failed与unknown usage分别记账，不混“调用数”。
首批拟安全硬帽60CNY，是任务书估算而非用户已选价格；主agent真实发车前按当日报价定稿并写新登记/机器配置，不自动放大。
本次默认**首次冻结后一次完整真实298**；后续版本需要另外明确实验安排与有限预算，不按本卷成绩机械循环点火。
预算/总HTTP/输出上限及未知usage保守预留真正先于send生效；预算过低早停仍留298分母，不自行升预算。
新batch_root/runs_root/gate/cases/ledger，许可gitignored根或仓外；核新部署字节与复审源码身份一致，旧封存批只读。
受权build流程核题源/白名单身份与298唯一qid；预测只substrate/授权source，参考图与gold不入prompt、pool或预测日志。
零付费前置验证环境/价格/审批/预算/单协调者/新identity；envcheck不污染case，未知凭证/模型权限现在不阻离线实施。
如新登记允许冒烟，用固定前缀或预定名单并作为正式新批前缀；只看运行完整性/费用，不看gold或中期命中调参。
同批同身份续全298；任何prompt/池/模型/retry/profile变化停止该批，计费和终态如实披露，另新登记新批。
所有298注册题validated终态（失败补位），gate死亡/unknown占位及请求/usage/费用对账完成后封存，停止模型调用。
后置score零LLM，全部qid_strict；固定298分母，失败/unknown/无候选/预算漏展开算未中，不逐题挑多批最佳答卷。
新target判定独立字段读取原main hit@K，并验证全集/身份/冻结配置/零模型评分；旧S5B_PASS_LINES仍是历史参照线。
达≥150/298标`target_met_seen298`；低于目标标`target_not_met`，报告所有批主/老/any-of、U/H5/L、配对净赢/输与成本。
首批未达则交完整报告与**实质不同下一版本任务包**，不机械循环跑到过线；代码可继续形成可复审改法，真实再测不自动启动。
后续方案按298反馈设计则诚实标post-hoc；参数选择用独立预冻开发集，不一边看298选阈值/提示词一边宣称冻结泛化验证。
预算耗尽、无实质改善或无合法供给路径交真实未达/受阻证据，不冒完成、不把最好一次逐题拼成新成绩。
模型切换/每题多logical请求只能下一轮明示配置、价格、有限硬预算和候选融合/首成功政策先登记；所有尝试费全计。
不得让gold决定触发多调用、oracle rank或替换答案；科学单批净效果不拆成每工作包因果收益。

## 4. 最终hand-off清单和短派工prompt

交付书必须有实际HEAD/commit与dirty状态、有限diff、W0–W7矩阵、合成输入/正负控/输出哈希、公共链证据、定向与required回归命令。
列source许可/哈希、unsupported化学与proof_scope缺口、完整响应/重放可用性、待复审问题、每阶段成本（当前实施期真实模型费用0）。
附新预注册/manifest/目标status草稿、预算公式/配置与停止策略；区分`implementation_ready_for_review / review_changes_required / ready_for_real_retest`。
后续运行另列`scientific_target_pending / target_not_met / target_met_seen298`及实际成本，不把工程交付称科学完成。

> 执行本任务书W0–W7，先读AGENTS.md并核实际HEAD。目标默认同冻结strict hit@5≥150/298；保持身份、参与物、事件K和298分母。
> 真正完成共同compiler、授权exact source适配、pool/novel统一选择排序、有界补位和同源图payload，全部走production/audit/admission/store。
> 只改任务源码、合成tests与新交付文档，实施期不真实调用、不读298题卷/gold/旧答卷、不改封存run、不push。
> 完成十二组合成正负控和公共链/replay/合成score、定向回归及required PPV1+G01，按矩阵一次自审，交commit/证据/范围和新登记草稿。
> 返回本聊天root等待复审，不自行点火298、不自行多批、不调用外部评审模型；复审通过后主agent按已授权分工启动新冻结批。
> 工程验收或候选接受率改善不冒科学达标；不能完成的source/编辑范围诚实unsupported，目标由后续新批零LLM同尺子判分。
