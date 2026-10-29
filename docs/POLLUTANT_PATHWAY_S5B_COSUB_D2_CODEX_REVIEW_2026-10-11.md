# PPV1 S5b 共底物 D2 正链复审

日期：2026-10-11。实际 HEAD：`2e679b31ded26e8b977896800bda3c8f17e9bf14`；直接父基线：`64ef32c8879aaa1330edbfab56357dc6090d7749`。

## 1. 编号裁定

| 编号 | 裁定 |
|---|---|
| D2-C01 | **D2 工程不通过，P1=[S5B-D2-01]。** 三分类与正常参与物装配基本成立，但 NC-10 的触发条件可被删字段关闭；同一记录丢共底物和拷贝后，公开链仍提交事件并被参考边匹配为 strict。 |
| D2-C02 | 不重开 v4b-R1、金额守卫、提交序、S3/S4及历史已关组。新阻塞直接对应设计 §五.4 NC-10、r32 R32-CS3-3 和交付书入口矩阵，没有新增阶段要求。 |
| D2-C03 | r32 意见采信到源码与本轮程序证据互证的程度。其 NC-10 强制义务未兑现；r34 回应本轮封包时尚未到，不能预填其意见或宣布 D3 三方收口。 |
| D2-C04 | **设计线本轮不收口；chain12 继续缓发。** 修复并复审通过后，才可把 D2 纳入另行登记的组合批。显式氢墙不是本报告自动批准或默认必含的改动。 |
| D2-C05 | 冻结正文、FREEZE_RECORD、path_context、scorer/evaluation/AtomTool及金额链没有本轮字节改动；EAWAG默认编译合成父子对照成立。字节不变不能替代新事件守卫的行为核验。 |

这是工程及合成接口复审，不是298题域性能验收，不声称命中增长，不启动模型或真实批。

## 2. 固定验收面与执行边界

必读材料：设计书 `docs/S5B_COSUBSTRATE_PARTICIPANT_SEMANTICS_DESIGN_2026-10-10.md` §四～六、§十二及追加的「§12 决策点处置记录」；交付书 `docs/POLLUTANT_PATHWAY_S5B_COSUB_D2_DELIVERY_2026-10-10.md`；mimo r32回应、r34请求；上一轮 `docs/POLLUTANT_PATHWAY_S5B_HIT50_V4B_R1_CODEX_REVIEW_2026-10-10.md` §7。

本轮只验三分类、方案a参与物表示、union gate、NC/PC固定控件、版本、条件采纳和组合批条件。T-1仍暂不立项、T-5挂起；T-2 declared_complete、T-3保守拒、T-4机读为设计书登记的**主会话默认、待用户/teacher改判**，不能写成teacher已经逐项批准。另只读2026-10-11 T-1裁定包前65行，其头部仍为`awaiting_teacher_decision`，这是请求件，不是teacher回复；没有把该请求中“唯一解锁路线”等范围外断言作为本轮结论。已声明完整名单不证明计量完整或机制可行。

三路独立工作均使用新 `/private/tmp` 目录。源码隔离副本含必要vendor/metadata；父基线从git对象写入临时树，没有在仓库创建worktree或修改索引。父子共用同一隔离v3依赖根；主进程用depending43、`-B`、`PYTHONDONTWRITEBYTECODE=1`及`-p no:cacheprovider`，隔离子进程pyc例外见§3。公共链探针封禁socket，模型为合成scripted实现；速率/金额回归使用本地假提供者，不调用外部模型。

未读取真实题面、金标、封存逐题run、dependingv4或原v3评测资产。实现方CS2c只读其聚合README和探针源码，**不读其逐题结果**；真实298离线漏斗及池层数字不复跑。它们在本报告均为来源声明加摘要算术核对。旧永久证据仅用于安全脚本谱系与完整性读核，没有原地执行或写库。

## 3. 独立执行数字与红绿精度

| 独立执行 | 结果 | 说明 |
|---|---|---|
| D2新19＋wv41 | 39 passed / 0 skipped | 包含在下列定向集合，不另加到总数 |
| 定向及邻接闭合组 | 434 passed / 3 skipped | 新19、旧供给/提交序/runtime/qid/金额/AtomTool/生产链控制；3缺席依赖逐nodeid存 execution/logs/directed_absences.json |
| 安全隔离G01 | **2008 passed / 10 skipped / 17 deselected，exit 0** | 单次完整执行，314.54秒；完整stdout/stderr/JUnit及缺席逐nodeid存 execution/logs/g01* |
| G01中的PPV1文件子集 | 1405 passed / 2 skipped | 两skip是隔离树未复制冻结docs的自检；冻结字节另行核验，不冒称原仓全量 |
| 直接父同字节61案 | **25 failed / 36 passed / 0 collection** | 新/改测试字节固定，源码为64ef32c8；类别见下文和execution/parent_red_green_classification.json |
| 既关R1/R2/R3金额族 | 72 passed | 定向子集19＋28＋25；不重复计数 |
| G01输入谱系 | **330输入，329继承；7换＋1新＋0缺，前后SHA失配0** | 44普通批准资产仅SHA/size锚定，不重复复制248,371,747字节；其余286输入完整留包 |

交付2019 passed / 0 skipped / 16 deselected原仓全量是**来源声明**，本会话没有越过安全边界重跑。G01不能替代缺席的真实v3/v4评价资产验证：10skip包括v4对照根1、v2 provenance/summary 2、冻结v3基准5、未复制冻结docs的自身守卫2；17剔除按完整nodeid文件登记，不凑成原环境全绿。隔离并行定向/G01子进程共观察7个pyc，不能单独归因某一pytest；仅在新隔离树，父pyc0、pytest缓存0，封包不含pyc/缓存。

公开语义复现：23案完整执行，5个合法事件、4个违规退化事件、14案零事件；其中10案生产准备结构化拒、4案检索空池。9个已提交事件均是 `R5/retain_conditional`、中心unknown，**没有声称错误R6**。4个违规事件的问题是记录参与物丢失及边匹配误入strict。原探针23次resume均遗漏原scripted model，先被prediction身份门拒绝；原23案17表零增行只证明拒绝未增行，**不是恢复成功**。随后将9个有event的既有合成run复制fresh tmp，以同一脚本模型身份调用公开resume，9/9成功、新event0、17表新行0、模型/化学/socket调用0；没有重跑start。stop与endpoint内容将本次session提交列表置空，native摘要随之改变，但原event内容及匹配桶不变；不声称表内容或native摘要字节零写。辅助“native摘要全等”断言使补证控制脚本exit1，完整保留；纯读回确认API9/9成功（不是重跑），其后初次纯读回的payload_hash过滤错误也保留并订正。证据见recovery/facts.json、recovery/recovery/<name>.json及logs。拒绝案不宣称所有业务表零写：root检索、决策等合法先行写入在完整转储中逐表保留。

父25红分类为：真供给/行为8、拒因标签迁移10、新增API参数缺失3（`TypeError: declared_copies`）、版本字面量4；合计25。新D2文件实际17红/2绿（原有补全许可无碳、默认whole/EAWAG两正控绿），wv41实际7红/13绿，w23456为1红/21绿。交付书 §十称新18红/1绿、wv41六红，需要订正。父NC-9/NC-10在「spec非None」前置处已停，没有执行内部篡改/prepare；3个API红也没有执行拒绝分支。不能拿这些红证明父事件级反例已跑，更不能把25红统称25个漏洞。

EAWAG/whole默认编译另做8个独立合成父子案，4成功、4原有unsupported，完整compile结果逐字节相同。成功案prepare多出内部 `cosubstrate_disclosure=None` 一个返回键，其他hypothesis/states/tools内容相同；生产报告仅在非None时添加披露。交付「无共底物零字段零变化」须限定到事件/生产报告，不是prepare返回字典。

## 4. 唯一P1：S5B-D2-01——删装配字段可关闭记录侧NC-10

### 4.1 对应原验收和实际代码

设计 §五.4 NC-10、r32 R32-CS3-3、交付书 :50 均要求：记录声明全部B进入reactant cosubstrate参与物，记录全部产物与事件产物多重集相等，**spec gate不能替代事件核对**。`production.py:365–377`自身docstring还明确「B与拷贝同丢会退化A→P，事件不变量是唯一事件层闸」。

实际入口却两次依赖被核对象是否还存在：`production.py:234–237`用`or []`将缺失/null归一为空；`:241`仅`co_sub_entries or copy_entries`才检查contract并装配状态；`:331–340`仅`b_states or copy_states`才调用`_check_cosubstrate_event_invariant`。原记录契约或corpus侧B声明仍在，两个装配列表为空就不消费。随后`:289–312`允许缺失participants走默认A/P装配。

记录侧源字段实际由 `recorded_source.py:1854–1872`装配，corpus声明见`:1875–1894`。本反例保留这些记录侧声明、编译结果及来源，没有把整个记录改成另一反应，没有伪造全库或重写冻结判据。

### 4.2 合成公共链证据

同一合成记录：`CCO + c1ccncc1 → CC=O + C1CCNCC1`。这只是守卫夹具；按氢数不配平，计量保持unknown，不把它当真实酶学反应。正常builder入池、prepare、AtomTool→audit→admission→submit、native首读、参考边匹配都实际执行。

| 输入 | prepare | 原生event | root-only参考边结果 |
|---|---|---:|---|
| 原合法spec | 成功，B/copy完整、披露在位 | 1，完整反应物/产物 | matched_participant_coverage_partial |
| 同时将两装配数组设`[]`，删B/copy参与物，保留原contract/corpus | 无拒绝，披露为None | 1，仅CCO→CC=O | **matched_strict** |
| 同时删两装配键，其他同上 | 无拒绝 | 1，仅CCO→CC=O | **matched_strict** |
| 两装配键设null，其他同上 | 无拒绝 | 1，仅CCO→CC=O | **matched_strict** |
| 两装配键与participants均省略，contract/corpus仍在 | 默认装配，无拒绝 | 1，仅CCO→CC=O | **matched_strict** |

证据：`semantics/public/strip_both_empty.json`、`strip_both_missing.json`、`strip_both_null.json`、`all_arrays_missing_participants_default.json`。各含原输入、变更后公开plan、prepare结果、start/resume、原生事件、native首读、参考边/节点匹配、完整17表前后转储；socket尝试0。观察脚本退出0表示取证完整，**不代表四坏案验收通过**。

现有 `tests/test_ppv1_s5b_cosub_d2.py:393–440`只分别删除B参与物、或删除copy参与物/拷贝状态，另一装配数组仍在，从而仍进入guard。这两负控通过，但没有检验关掉guard的形态；`:684–793` NC-12只检验合法样本，不拦截本例。

### 4.3 最低收口

共底物语义适用性必须由同源记录声明/语义标记决定，不由可删的装配数组是否非空决定。原contract或corpus侧声明B/copy时，与声明不符的装配列表缺失/null/空、participants删减/缺失都必须进入同一守卫或先结构化拒；合法旁观B的copy=[]不拒。不能默认装配成普通A→P，也不能丢诊断后继续提交。

四原反例应在prepare及公开消费链拒，新增坏event及其提交为0；保全输入与拒因；先行root检索等合法账目逐表如实披露。保留单删负控、缺/坏contract及非法引用/产物多重集控制。合法拷贝、零拷贝旁观B、多B/多拷贝、whole及EAWAG默认通道保持；不以全面拒绝换通过。不得通过改scorer或让此类参考一律partial来隐藏坏事件。

## 5. 其他D2验收与r32逐组互证

三分类实际位于 `recorded_source.py:837–1074`，基于现有映射枚举及any-bond查询。断连B来源整组分进入split；A/new混组分、B-B融合拒；不可解析、触顶、无对应、无可执行子集诚实拒。`:1497–1530`在装配前再拒add_atom。NC-8映射注入是防未来漂移控制，公共枚举正常不能声称已出现空执行子集；NC-3注入同样不当作真实化学恢复。T-3保守拒、fallback分列均保持，没有替本轮要求机制库或原子级B执行。

方案a正常事件成立：B显式reactant/cosubstrate，拷贝显式product/coproduct且标记`record_declared_copy`/`declared_not_executed`，未知计量和中心；执行期望只涵盖实际A产物。合法旁观B（copy为空）及多B/多copy均实际提交partial事件。单删B/copy、坏状态引用/来源、记录产物缺/重复、copy混入expectation已逐案零坏event。唯一未闭合的是§4绕过触发。

union gate位于 `recorded_source.py:1933–2166` 可选扩展；实际使用同源严格身份，执行∪声明拷贝对记录全部产物多重集核对，CN-only拷贝不升格，键空间一致性单独披露。它证明记录转写完整性，**不证明元素/电荷配平或拷贝已生成**。默认None路径保持旧选择与gate；`find_recorded_exact:1100–1186`函数原文父子逐字节相同，8个合成默认compile输出全等，证据见§3。`s5b_compiler.py:166–193`只扩展拷贝进入去重签名，默认签名相同，compile_donor_template原文相同。

r32自称「16条」；实际唯一编号为24条，交付表将多条归为16行。本报告按实际编号合并核，不把16行冒称24项全已实现：

| r32项 | 正链裁定与实际边界 |
|---|---|
| CS1-1/2/3 | 合法事件两轴披露、union非配平、declared_complete非计量完整已接线；内部prepare的None新键须文稿精确。 |
| CS2-1/2/3 | 物理执行图不含B与规则禁令分写，已知损失类/隐式EAWAG不对称、四轴代理诊断在源码；真实频数仅来源摘要，不能把碳代理当角色/机制证明。 |
| CS2-4 | 无可执行子集结构化拒，注入控制通过；是纵深防御，不宣称当前普通枚举可达。 |
| CS3-1/2 | fallback保守拒与分列、严格键空间/多重集同源成立；EAWAG默认合成等价成立。 |
| **CS3-3** | **未落地到所有适用消费形态，S5B-D2-01阻塞。** guard函数存在/单删测试绿不等于强制消费。 |
| CS3-4 | NC-8..12/PC-4/5已有测试和合法公共链证据；NC-10须补四案。NC-12范围见下文，不能称真实批熔断已执行。 |
| CS4-1/2 | ignore-tier尚未实施；含碳白名单挡板、声明copy与extras两读法选择是T-1立项后义务，当前不得声称已装机。 |
| CS4-3 | COMPLETION_LICENSED_IDENTITIES及audit零改，氢许可无碳测试保持；B/copy coverage未知系数对称句落字。它不自动禁止所有未来未知无碳身份，不扩大证明。 |
| CS4-4 | role归因、合成NC-12、partial收益与命中分栏、拒因迁移已登记；真实批后置归因/熔断仍须新登记落地，不预报已完成。 |
| CS5-1/2/3/4 | 供给面与命中分开、计数单位/拷贝非执行/迁移披露基本在；池计数字段与旧均值需P2更正，真实全表未复跑。 |
| CS6-3 | 旁观B无copy不允许为成对豁免而造copy；当前剥B参考保持partial，合法公共控制已执行。 |
| CS6-1/2/4/5 | 追溯开关、H2O carve-out、辅因子不得豁免/退出条件、长线参考依赖为拟议预注册面。T-1/T-5不立项，登记待裁，不隐含实施或修改冻结判据。 |

T1′三条的当前意义是边界维持：不扩有机/辅因子许可，不因partial压力修改判分，记录转写与ignore不同栏。CS6中原设计拟议四元组/方向条款的文字修正仍须在重新立项时形成一致新稿；不以T-1暂不立项宣布这些拟议冲突已经消失或新口径已批准。

**NC-12必须限定参考范围。** 本轮三合法cosubstrate事件对当前root-only参考确为partial；对另一个合法完整声明B与copy的合成参考，同一事件可以合法strict（reference_control.json中两参考均通过validate_reference_graph，完整参考matched_strict）。所以「本通道strict恒0」仅能作为**当前剥除B/copy参考构建口径**的归因/熔断约束，不能写成冻结判据对所有参考的普遍定理，更不能为守0改evaluation。实际完整参考/schema核验记录见语义证据。当前真实参考构建与金标未读取，预期hit@1=0是依赖已登记参考口径的工程预期，不是新298实测。

## 6. 漏斗、计量及P2订正

来源摘要漏斗 `984+317+22=1323`，编译拒 `219+73+13+10+1+1=317`，解锁率 `22/1323=1.663%`；可以采信其摘要账目闭合，不能称本会话重跑了1323记录、22spec/15题或5题脱空。

CS2c README的四个互斥格实际是1276/25/7/15，共1323；copy代理32与rhs excess/unattributable代理22的交集为7。交付§六把边际22放在最后格，若理解成四个互斥格会误加成1330；应显式交集及独占15，不报数据错误或悄悄改观测。物种/配平/organic标签都是代理，202+1121仅分类计数。204题、水118题、EAWAG322/99/隐式书写68等全部来源声明，未访问真实题目互证，不能当命中。

按交付直方图，旧 `[191,82,19,1,5]`共298题、143槽；新 `[186,78,25,3,5,1]`按0/1/2/3/4/8槽共165槽。旧均值应`143/298=0.479866`，新`165/298=0.553691`，增量`22/298=0.073826`；不是`.477→.5537`的`.077`增量。旧空191/298=64.094%，新186/298=62.416%。真实集合与输出谱系未由本会话重跑，仅算术订正。

P2同步清单（下一有限回修搭车，不新增化学实施）：

1. 上述均值、CS2c重叠格与题/候选计数分清；README「实际放行集大于②代理」限distinct题15>10，candidate22并不大于代理32。
2. 父红绿改为§3的实际分组/类别、内部未到达情况；测试数不当漏洞数。
3. `n_cosubstrate_declared_specs`在`s5b_builder.py:551`去重前递增，`:627`才merge，label却称去重后池spec。独立合成3来源spec→2池槽而该计数为3。改标签成编译候选数或按实际去重池数统计，并逐项定义截断前后；不凭它计算命中或池净槽。
4. 「零字段」限定到生产报告/事件；prepare新增None键如实登记。NC-12全称加当前root-only参考限定，真实后置检查待执行；完整参考strict不属于漂移。
5. T-1..5仍主会话默认；mimo r34待到后读码/执行互证，禁止先宣布三方D3收口。编译候选、池槽、事件及partial匹配量分别报。

## 7. 版本、轮收口与合批发车

当前版本已在实际代码登记：corpus-retrieval-3（recorded_source:188及语义块）、recorded-source-3（:173）、pool-policy-5（s5b_builder:416）、compiler-3（编译谓词未改；copy签名新字段由检索契约承载）。它们可登记为**当前待修/未放行HEAD身份**，不能因为有版本号自动冻结成通过基线。修复若改变已发布消费/诊断语义，按既有版本身份规则登记差异，不硬指定升哪个无关契约。

本轮D2不通过，D3不收口，chain12维持缓发。不是因为仅1.7%解锁率、unsupported多或科学收益pending，而是实际NC-10违例。修复并正链通过、r34采纳核对后，可以工程收口本设计线。T-1不立项时保持partial，不把结果压力转换为豁免批准。

下一真实组合批的条件：已过v4b＋已过D2；用户授权实际组合范围/新batch；teacher/用户对T状态的现行登记读回。若拟含显式氢墙，须另行批准、实施、工程复审，不能默认为本报告已授权，或无条件强制所有D2批必须搭氢墙。组合是多变量探索，增益不能独占归因v4b/D2/氢；要因果归因时另做固定其余项的配对消融或预注册多臂。

发车六项沿上轮落实，不预报本轮已完成：

1. 新登记、新batch、实际部署HEAD、代码/资产SHA及最终检索/recorded/池/compiler版本；不得复用封存链11/12根。
2. 298题域hit@1≥119/298主列、hit@5=150参考、seen/旧敏感性/U-H5-L及cosubstrate partial归因分栏，零外推dev；收益预期≠通过线已达。
3. 40在途、1logical/题、HTTP1490、60CNY帽；同日价/输入保守界/输出上限的budget_guard及run身份绑定、金额与数量双门机器生效；既有保守结算不放松。
4. 真实qid配对双门、expected graphIds非空/精确键集/全qid_strict；§9-④待插原文沿v3-R3报告及新登记逐字插入、读回、SHA封包，不以本报告代替登记。
5. 同身份固定前10冒烟后再按授权启动全批；本轮未冒烟，不代定费用/时长数值。
6. 298全终态留分母，封存后零LLM判分/费用对账；通道角色归因、NC-12仅在当前reference scope下执行，异常即停并保全，不改封存结果。

## 8. 下一轮有限回修提示词

> 你是PPV1实施agent。仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`。本轮只修 `S5B-D2-01`，验收源为本报告§4，不重开金额守卫/提交序/v4b/S3/S4/scorer及历史已关组。
>
> 先列共底物语义的适用入口与记录侧单一声明来源。修复production.prepare_hypothesis的触发条件：原cosubstrate_event_contract/corpus仍声明B/copy时，装配数组缺失/null/空、participants删减或省略都不能绕过NC-10、不能默认成A→P。所有适用公开消费及恢复共用核验；不在各入口复制不同规则，不改评价尺子来掩盖错误事件。
>
> 将本轮语义证据脚本复制fresh tmp，复现四案：strip_both_empty、strip_both_missing、strip_both_null、all_arrays_missing_participants_default。修前均1坏event且root-only matched_strict；修后首消费结构化拒、零新增坏event/相关事件提交。保留contract/corpus与坏输入，逐表登记先行合法root检索/决策账，不伪称全表零写。补首提与适用恢复入口回归，正负控同矩阵。
>
> 保持合法copy、旁观B零copy、多B/多copy、whole、多组分whole、EAWAG水解和默认编译正控；保持现有NC3/8/9/10单删/多重集/非法引用负控；不以全面拒绝换通过。当前root-only参考应partial；合法完整B/copy参考允许strict，NC12加范围限定。
>
> 搭车修本报告§6 P2文稿/计数标签精度及父红绿分类；来源摘要与独立执行、候选/池槽/事件/命中四类数字分开。按既有身份/version规则登记修复；三冻结正文/FREEZE_RECORD/path_context、AtomTool/scorer/evaluation及金额链保持。
>
> 新证据在fresh tmp跑，完整输入/输出/argv/env/exit/JUnit逐nodeid分类/前后SHA；嵌套manifest纳哈希，仅排根控制文件。安全G01仍隔离口径。金标/题面/封存逐题run不读，判分零LLM，不启动真实批、不push。r34实际回应到后互证并登记；不得编造mimo意见。交付仅此有限范围，交主会话按既有流程送独立复审。

## 9. 红线与永久证据

三冻结父/HEAD/工作树一致：

| 项 | SHA-256 |
|---|---|
| criteria-v1 | 7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4 |
| FREEZE_RECORD | 6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610 |
| path_context | 971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d |

legacy52聚合父/子同为 `279d9bc19bad25e51b7c23ee276da95151a8f25cf598b9dc3642b508d817c4bb`；PPV1的84文件聚合从 `659cf08935ddaeaa37746039f6ee74dff0a1d5cce810744744b20b62a88f562c` 变为 `f587e478b87b4b496313efd0bb5dccf02ead9d20cb3ef6128b2e75f9625ba188`，差异恰production/recorded_source/s5b_builder/s5b_compiler四源文件。15项闭合字节比较（13源码＋2冻结docs）在scope封包；AtomTool/scorer/evaluation/金额/runner/runflow未改。旧共底物全部诚实拒规则被D2**有意替换**，不误写其字节不变；本轮核新许可闭环而非强求旧拒因继续。

发布守卫固定165项输入、另一个后补读取的T-1请求状态头对应文件SHA，以及20,312份旧证据，发布前后逐SHA及旧文件集合一致；HEAD/父、既存tracked diff和工作树状态保持，仅新增授权两路径。

证据入口：`docs/review_evidence/ppv1_d2_codex_2026-10-11/README.md`。execution含安全树谱系、SHA输入清单、完整pytest/JUnit/缺席逐nodeid、父红分类、闭合族核验；semantics含23公开合成输入、事件/native首读/匹配/17表转储、socket封禁及控制；recovery含原run复制fresh后的9次正确模型身份恢复补证和完整失败控制日志；scope含源码实际行号、r32编号、聚合算术与8案默认父子等价；root_audit含输入和旧证据前后守卫、封包脚本、实际命令及最终读回。

本轮账户用量中断：无。仅复用已封存安全控制器及源码谱系，所有当前项目执行均在新tmp；上下文交接不是执行重跑。根文稿核对脚本两次错误路径（rate_gate/llm_client位置、不存在的admission模块）导致只读git失败；失败脚本/完整stdout/stderr保留，修正路径后成功，没有项目行为重跑或隐去失败。root封包读回还发现原23次resume遗漏原scripted model，先停在prediction身份门；零新增不是恢复通过，独立补证按§3。初次合成完整参考角色不合法/未跑schema，随后改合法角色并validate_reference_graph；只复用既有native，没有重跑start化学，不采信初稿匹配作为完整参考证据。失败观察和修正均保留，不回写原包。子任务其他事件如实记在各包README。只新增本报告和本证据目录，不改任何已有源码/测试/文稿/AGENTS/旧永久证据；不commit、不push、不启动真实批、不调用外部模型。
