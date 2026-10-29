# PPV1 S5b 共底物 D2-R2 正链有限复审

日期：2026-10-11（Asia/Shanghai）。被审 HEAD：`02a4b272e7f9ac481f67c2df7fba1974e095748c`。

实际直接父为 `0f83584004769e3dc4e8d19224159e935f069adc`，其父为任务所称 `ea00297e82931deae6417ca60af60008982d8b5c`。中间提交只新增一份不属于本验收面的评审请求文档，src/tests 完全同字节；本轮父红绿采用 ea 的隔离源码及当前测试字节，对实际直接父具有同等源码对照意义。不把任务摘要的父哈希照抄成 git 事实，也不读这份无关请求的正文。

## 1. 编号裁定

| 编号 | 正链结论 |
|---|---|
| D2R2-C01 | **D2-R2 不通过；唯一残余 P1=[S5B-D2-01]。** 原三案已经翻拒；两份合法列表的同源多重集核验成立。但第二份产物声明明示 null/非list时，被当作不存在，收缩后的 contract 仍可提交缺记录产物的事件。 |
| D2R2-C02 | 接管和代笔已如实披露，缺失实施公开探针已由本审 fresh tmp 公开链补证；这一处理方式可接受。代理死亡/原作者/两次原仓2038/“已知flake”归因仍是交付来源声明，不冒称独立核验。 |
| D2R2-C03 | **D2 设计线尚不收口，D3 仍未闭环；chain12 继续缓发。** 唯一代码阻塞为明示损坏的第二产物声明被降为单来源。其他已关组保持关闭；显式氢墙未因本轮获批。 |
| D2R2-C04 | retrieval-5 / pool-policy-5 / recorded-source-3 / compiler-3 已登记，是本轮待修身份，不是已通过的冻结发车基线。三冻结 SHA、scorer/evaluation/AtomTool/金额链和 EAWAG 默认能力维持，证据与范围见 §9。 |

本轮是合成工程接口复审，不是298题域科学性能验收。不读取真实题面、金标或封存逐题 run，不启动真实批，不外推 dev。

## 2. 固定验收面与证据纪律

验收以 `docs/POLLUTANT_PATHWAY_S5B_COSUB_D2_R1_CODEX_REVIEW_2026-10-11.md` §4.2 三反例、§4.3 最低收口、§8 提示词为准，沿既定 NC-10「记录全部产物与事件产物多重集相等」及首次消费完整性。只核产物侧剩余、合法控制、接管记录、版本/红线和组合批条件。

R1 §8 已要求缺/重复/冲突来源的适用消费控制。明示 null/坏类型的第二声明不能因为不是 list 就被洗成无来源；这个残余直接属于同一原验收，不是增加机制、配平、全库抗篡改或性能要求。合法本来只有单来源的默认路径继续允许，见 §4.3。

所有项目执行在新 `/private/tmp` 隔离源码副本；旧永久证据只读核 SHA 后复制。父子共用同一安全 v3 根，depending43、`-B`、`PYTHONDONTWRITEBYTECODE=1`、`-p no:cacheprovider`。公共链 socket 禁用、模型为 scripted 合成响应，网络尝试0；金额回归只用本机假提供者，无外部模型。嵌套 manifest 全部纳根 SHA，根只排 manifest.json 和 SHA256SUMS；不封装运行数据库或缓存。

没有在真实仓运行 tests/ 全量，也没有复制原 v3 评价资产或 dependingv4。普通已批准反应资产沿既有安全谱系核 SHA/size，其余准入源码、vendor、metadata、测试及合成输入完整封包。真实 CS2c、1323供给漏斗、22spec或池深不复跑；不以本轮合成控制冒称真实题域全部等价。

## 3. 独立执行、父红绿与缺席

| 执行面 | 本审结果 | 精度 |
|---|---|---|
| 本轮定向三文件 | **80 passed / 0 skipped** | cosub_d2 38、wv41 20、v4b 22；包含7个新增测试函数及原有控制 |
| 定向＋既关金额族 | **152 passed / 0 skipped** | 80＋金额R1/R2/R3旧控制72；子集不重复累加 |
| 安全隔离 G01 | **2027 passed / 10 skipped / 17 deselected，exit 0** | 首跑完成，363.35秒，无失败/flake；完整 stdout/stderr/JUnit |
| G01 内安全 PPV1 子集 | **1424 passed / 2 skipped** | 不冒称原仓2038全量；缺席冻结文档守卫另以只读SHA覆盖 |
| 父源码＋当前同字节三文件 | **10 failed / 70 passed / 0 collection** | 有效行为基线ea，已证与直接父0f源/测试完全相同 |
| G01 输入谱系 | **330输入，5换/0新/0缺，前后SHA失配0** | 相对R1，恰2 source＋3 test变化；286非资产完整，44普通资产只锚SHA/size |
| 默认合成父子控制 | 8/8 compile 内容逐字节相同；4个成功案 prepare 完整输出相同 | 另4案本来unsupported，未执行prepare；不把两个None当执行通过 |
| 公共链独立观察 | **40 start、35 resume；14事件=10合法＋4坏形状事件** | 34主案＋5入口控制＋1 EAWAG；观察脚本exit0仅说明取证完整，不是40案安全全通过 |

父10红按逐 nodeid 归类：**6行为红＋1新披露键KeyError＋3版本字面量红**。行为红为原收缩两案、同源控制、公开start两案、公开novel一案。没有 collection 红；字段红不能冒称新的拒绝行为红，测试数不能冒称漏洞数。完整分类在 `execution/parent_red_green_classification.json`，原始 failure 与JUnit保留。

G01缺席逐 nodeid、原因及路径在 `execution/logs/g01_absences.json`：10 skip=1个v4对照根、2个v2 provenance/summary、5个原v3冻结基准、2个未复制冻结docs守卫；17 deselect=16 slow＋1敏感CN评价夹具。缺席资产不认证、skip不改计通过。子进程在隔离目录观察7个pyc，父pyc0、双方pytest缓存0；定向/G01并行，不能把这些pyc独归因G01。封包排除pyc，真实仓及旧证据没有本轮缓存写入。

交付方 `2038 passed / 0 failed / 16 deselected` 两次原仓全量仍记**来源声明**。其指定易失G01原始stdout/JUnit可读，独立核得2027/10/17、exit0，stdout SHA一致；与本审fresh G01互证，但不是两次2038的独立证明。

## 4. S5B-D2-01：三原案关闭，坏第二声明仍可关闭核验

### 4.1 已经兑现的修复

`src/pathway_v43/pollutant/production.py:470`新增同源键函数，沿已有 `strict_identity_of`，排序列表保留重复组分，不另开比较器。`:540–563`在双方均为list时先核同源严格身份多重集，冲突码实际是 **cosubstrate_record_products_divergent**；`:604–623`再核事件产物全量。contract侧坏形状已由`:275–282`先拒。

| 原反例/适用入口 | 当前独立执行 | 事件与事件提交 |
|---|---|---|
| contract_products_shrink_keep_copyrefs／公开池 | prepare/start/resume 均结构化 divergent；原 corpus 完整保留，copy refs仍在 | 0 / 0 |
| contract_products_shrink_keep_corpus／公开池 | 同上；三项版本/语义metadata以外与旧输入逐字节同源对照 | 0 / 0 |
| 相同坏spec／公开novel | 共享prepare拒，记逐条novel拒绝；不是run级进程失败 | 0 / 0 |
| expand防御性边界注入／原收缩spec | 共享prepare即拒 divergent，早于前轮后续身份门 | 0 / 0 |

两池拒绝后仍有先行合法 root retrieve：search_actions=2、budget_reservations=4、search_commit_records=1，提交kind为outcome_recorded且event_id为空；hypotheses/events/model_requests=0。17表完整转储保留。**公开resume的17表增行全0，不等于公开start全表零写。**

原四双删、corpus-only/B并集、缺/重复/冲突产物、非法引用控制保持；6个直接prepare负控均结构化拒。合法copy、旁观B零copy、多B多copy、whole、多组分whole、EAWAG水解及单来源默认保持。合法root-only参考partial，经过schema核验的完整B/copy参考strict，不用全面拒绝或改判分换通过。

共享构建源仍是 prepare_hypothesis：runflow.py:870 的池decide、:933 novel、:1324 expand共用；`:740–749`结构化登记run_error，novel按`:941–951`逐条容错。守卫在production.py:371的内存hypothesis构造之后、:397的不变量检查处，早于实际工具/audit/submit；不能写成“构造假设之前”。

### 4.2 唯一残余：字段在位但损坏，被当成合法不存在

问题在 `production.py:542–546`：读取 corpus.record_products 后只以 `isinstance(..., list)`决定是否存在第二来源。键明示在位、值为null/string/dict/bool时，不报坏声明，直接保留`:544`的单来源并消费`:564`收缩后的contract。`:718`仍输出NC-10 checked，甚至描述“across contract AND corpus declarations”已核。

沿上轮同一合成原记录 `CCO + c1ccncc1 → CC=O + C1CCNCC1`，先作原收缩/删copy装配及对应产物参与物，再把**仍在位**的 corpus.record_products 改坏类型。四案均保留 corpus 的其他字段、B声明/参与物、record_key/provenance、compile原全量、edits/donor/alignment/expectation、原contract.copy_state_refs；这些保全字段逐项SHA相同。不是所有权威一起重写，更不是合法原生单来源旧spec。

| 明示坏第二产物声明 | prepare／公开start | 实际event产品 | 实际事件提交 | production机读结论 |
|---|---|---|---:|---|
| null | **接受** | 仅CC=O，缺C1CCNCC1 | 1 | NC-10 checked；record_products_sources仅contract |
| 字符串 `CC=O.C1CCNCC1` | **接受** | 同上 | 1 | 同上 |
| 字典 `{"0":"CC=O","1":"C1CCNCC1"}` | **接受** | 同上 | 1 | 同上 |
| bool false | **接受** | 同上 | 1 | 同上 |

直接证据为 `semantics/public/shrunk_contract_corrupt_corpus_{null,string,dict,bool}.json`，含全部输入/输出、event、native首读、生产报告和17表。四案 start 均 events=1、search_commit_records=3（其中event_committed恰1）、search_actions=4、budget_reservations=7；同模型resume无异常、17表增行0。不得把恢复幂等说成坏事件已消失或未曾提交。

四事件实际均 **R5/retain_conditional、matched_participant_coverage_partial**，不是错误strict/R6；也不冒称配平/机制成立。这一P1是明示坏权威声明被静默降级后仍成功提交，且继续宣称全量记录已核。partial并不豁免既有记录完整性契约。旁观unknown/新消费者禁句是有用披露，但不补这个守卫缺口。

### 4.3 有限剩余最低收口

**仅补同一第二产物声明的存在性与格式消费。** 第一份contract已有合法list门不回退；第二份字段明确在位时，null/非list是坏声明，须首消费结构化拒，不能把类型错误解释成“没有第二来源”。合法list继续用现有严格身份多重集比对；来源真正未声明的合法默认路径继续允许。

本轮两种单来源正控均完整保留copy产物：无corpus块，以及合法corpus块本来缺record_products键，均成功提交完整事件；两源同义/反序也成功。**不把这些正控改成拒绝，不要求追踪不存在的声明历史，不新加全库协同改写防御。** 双方同源有效但重复或冲突的控制保持，空list是有效声明并按既有多重集比较，不能将其归无来源。

四坏形状公开池案修后必须0坏event、0相关event_committed；坏声明保全、既有先行合法账逐表披露；同模型恢复仍拒且无新增。共享规则覆盖novel/expand等实际适用入口，不在builder单口补过滤。其他已关组无需重开。

## 5. 接管收尾、交付一致性及r34/P2

**接管方式合格，代码验收仍未通过。** 交付头部承认代笔及代理进程死亡，尾部承认缺实施方fresh公开探针，没有冒称旧公开输入已经由实施方执行。主会话接管提交、明确来源、如实登记中间失败的处理符合纪律；本审已自行补40次公开链而不是以“没探针”为由退回，也不以死亡为代码免责理由。

可独立核的事实：实际git构成6文件（2 source、3 test、1新交付书）；指定易失G01完整stdout/JUnit2027/10/17与SHA；本审fresh回归和公开行为；中间docs桥接。**未确认**：代理死亡的具体原因/过程、作者身份、两次原仓2038完整日志、中间workflow预算失败的原始全输出与隔离单测重跑。交付说“已知flake”，本审只登记这一来源分类，不把未取得的失败原因当已证。指定G01的该workflow测试通过1次，本审G01首跑无失败；这些不能倒推出原失败必定无害。

这种如实披露的验证局限可接受，不额外立P1；下一交付应保留每次实际执行的完整日志，不删首失败再凑全绿。唯一阻塞仍是 §4 的实际产品声明绕过。

交付两处精度订正：

- 实际拒码为cosubstrate_record_products_divergent，报告用实际码；“conflict族”宜写清具体kind。
- recorded_source.py:1920/:1973从同一record_products_flat生成两份声明；本轮该函数diff为版本/文字/披露，**没有另新增运行时装配一致性拒门**。真正拒门在production首次消费，不能把装配同列表与新增独立验证器混为一谈。

沿R1对r34的互证口径，不因r34对原D2的“无旁路”读码标签授本轮放行；本轮没有编造新mimo回应。双合法list原三案确实修好，但不能把这扩大为全部第二来源形状已经闭合。

搭车P2已兑现：production.py:665的旁观消耗/催化角色unknown注记、:698的消费者联读同批生产报告与禁止“copy已生成”措辞、recorded_source.py:1961–1972的每spec retrieval-5/root-only NC-12与完整合法参考strict限定；测试`:1455`提交证明语句已限定实际守卫核验范围。字段是披露义务，不冒称所有下游消费者已有新的执行拦截。原D1记账/请求头/teacher证据状态仍按R1后续登记，不重写历史回应或因此新加阻塞。T-1裁定文档头仍 awaiting_teacher_decision，本审不代选。

## 6. 版本与继承

corpus-retrieval-4→5记录本次消费语义；pool-policy-5 / recorded-source-3 / compiler-3 / search-production-2维持。版本升档已登记，但本轮仍未通过，因此不能写成retrieval-5已经冻结发车。下一有限修复按既有身份/version规则登记实际差异，不硬指定无关契约升版。

金额72旧控制保持；冻结判据、audit、runflow、endpoint、compiler、runner、real_model、worker、orchestrator、scorer/evaluation/AtomTool等闭合源码均父子字节相同。find_recorded_exact和compile_recorded_reaction原函数字节相同；8合成默认编译及4成功prepare实际输出同内容。recorded_source整个文件因语义/版本文字变化，不能声称整文件零字节；EAWAG路径等价只认证本轮函数及合成控制范围，不扩大成所有真实题域证明。

## 7. 设计线与chain12终版条件

**本轮尚不收口D2/D3，不放行chain12。** 原三案与双合法list规则保持关闭；仅明示坏第二声明这一S5B-D2-01残余待修。unsupported、真实漏斗未重跑、性能pending、teacher尚待裁、纯P2注记均不另立代码P1。

下一有限复审清掉该残余、登记r34事实订正与条件互证后，D3才可闭环。部署身份以真正通过的HEAD与最终retrieval版本为准；当前待修清单为 corpus-retrieval-5 / pool-policy-5 / recorded-source-3 / compiler-3，不冒称已冻结。chain12沿R1 §C04/§7：已过v4b＋已过D2最终修复、用户授权实际组合和新batch、读回用户/teacher的T状态。**显式氢墙仍须单独批准，若纳入组合再实施和复审；不是每个D2批必须包含，也不是本报告批准AtomTool改动。** T-1未立项/待裁、T-5挂起等按真实当前状态登记；不得借partial/成绩压力放宽冻结判据。

获得有限代码放行后，受权协调者仍须执行六项，当前未执行，不能当已经发车：

1. 新batch/新根/新登记及单协调者锁；冻结实际部署HEAD、资产/vendor/model/prompt/protocol/profile/budget_guard与最终retrieval/recorded/pool/compiler身份。不热换封存根。
2. **298题域**strict hit@1≥119/298主列、hit@5≥150参考，旧锚/seen敏感性/U-H5-L及共底物partial归因分栏；不外推dev，不保证达线。
3. 沿既有40在途、1logical/题、HTTP1490、60CNY机器帽；同日有效价格/可核保守价界、真实输入及计费输出上限、配置SHA与run身份绑定；保守预约/结算不放松，费用异常停止。
4. 当日题源授权/SHA与唯一qid双门；expected graphIds非空、键集精确覆盖、全qid_strict。将以下原文插**新登记**，读回全文，核代码/正负控，再算登记全文SHA，与部署/预算配置封包；不改旧冻结登记。
5. 同批同身份固定正式前10冒烟，核完整性/费用后按授权继续；不看gold调参，不代定当日数值。
6. 298全终态留分母、封包封存、零LLM判分、费用/未结算对账；NC-12按实际root-only scope执行，异常保全。多变量组合是探索，不能把增益独占归因某一个组件；因果另做固定其余项的配对消融。

§9-④原文延续已定v3-R3口径，本轮不替发车登记：

> 现行真实批配对采用整批二档；`data_scope=real` 时禁止根身份回退的守卫触发 ⇔ `manifest_qids` 与 `export_qids` 皆空。判分前须核注册图集合非空、`bases_by_graph` 键集精确覆盖注册图且值全为 `qid_strict`，任一缺失、额外键、坏类型或非 strict 即阻断。本门只核配对档位与覆盖，不核 qid↔图映射正确性，映射由评测器权威链负责。若配对档改为逐图混合，§9-④、evaluation-5 守卫与判分门须同步改为逐图判定，不得沿用整批判。

## 8. 下一轮有限回修提示词

> 你是PPV1实施agent，仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`。只修本报告§4的同一P1 `S5B-D2-01`：corpus第二产物声明键在位但null/非list时被降成合法单来源。不重开已闭合的原四双删、双合法list多重集核验、金额/提交序/v4b/S3/S4/历史launch，不改scorer/evaluation/AtomTool或三冻结文件。
>
> 先列record→contract/corpus→prepare→池decide/novel/expand/恢复入口。仍用production单一消费源；分开“字段确未声明的合法默认路径”和“字段在位但损坏”。第二产物声明明确在位而null/string/dict/bool或其他非list，第一次消费须结构化拒，披露字段/类型/原因，保全坏声明；不得再以isinstance为是否存在的判定并静默降级。有效list继续使用现有strict身份多重集核同源，保留重复意义；contract既有list守卫不退回。不另写比较器、不重扫语料、不要求抗所有权威协同改写。
>
> 把本轮 `docs/review_evidence/ppv1_d2r2_codex_2026-10-11/semantics/scripts/` 及合成输入复制fresh tmp执行，旧永久证据不动。四案 `shrunk_contract_corrupt_corpus_null/string/dict/bool` 修前公开start各提交1缺copy event及1 event_committed，实际R5/partial、NC10 checked，不夸为strict/R6；修后共享prepare/公开消费拒、0坏event/相关提交，坏spec保全，同模型resume同拒/无新增，先行root retrieve等合法账逐表如实，不报start全零。补一个novel同根及适用expand的共享守卫控制，防御注入如实标明，不拆后续身份门。
>
> 已过三原案、四双删、缺/重复/冲突list、非法引用保持；合法无corpus、corpus本来缺record_products键且contract完整的单来源、合法copy/旁观B零copy/多B多copy/whole/EAWAG、两源同义反序保持。不要以全面拒绝换通过；空list作为合法声明按既有多重集比较，不当缺省。root-only参考partial、schema有效完整参考strict保持。R2消费者/旁观unknown/NC12范围披露保留，checked与实际消费来源措辞必须同真。
>
> 明确actual parent/HEAD、版本身份和交付作者/接管provenance。保留每次首次失败及最终完整日志，flake来源与独立确认分开；独立公开探针不只用测试断言代替。fresh tmp、安全G01、完整输入输出/argv/env/exit/JUnit逐nodeid分类/前后SHA；嵌套manifest纳哈希只排根控制。零金标/题面/封存逐题run/原v3评价资产、零外部模型/真实批/push。实际化学评审按既有职责及流程登记，不编造新回应；交主会话核构成/复跑后送正链有限复审。只交这个剩余。

## 9. 红线、证据与事件登记

| 冻结项 | 父/HEAD/工作树一致的完整SHA-256 |
|---|---|
| criteria-v1 | 7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4 |
| FREEZE_RECORD | 6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610 |
| path_context | 971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d |

legacy52父子聚合保持 `279d9bc19bad25e51b7c23ee276da95151a8f25cf598b9dc3642b508d817c4bb`。PPV1的84文件聚合从 `7103a1f53bc2e1c63ed3e30c855cea42ec2c6283492fe95a38b5a48706d0009c` 到 `5de6f86dee187b9d89e963d9a283b1a97e53452c50092bf57493fa78829eab74`，恰production/recorded_source两项变化。scorer匹配/排序、evaluation、AtomTool、金额代码字节同父；测试控制保持，不以这些字节相同掩盖 §4 的新证行为。

永久证据目录：`docs/review_evidence/ppv1_d2r2_codex_2026-10-11/`。README列 execution（完整隔离回归/父分类/缺席/330谱系/合成数据库文本）、semantics（40公开start/35resume、完整输入/生产报告/event/native/17表/合法参考）、scope（实际源码行号/接管控制日志/默认8编译与4prepare等价/P2）、root_audit（输入/旧证据保护快照、根纯读回、命令/事件/发布封包脚本）。三隔离子包的manifest均独立验SHA后原样纳总包；所有嵌套manifest/SHA文件也纳根哈希。

本轮固定171个既有输入、24,888份旧永久证据的精确文件集合与SHA，在发布前后保护核验；本轮只新增本报告和本证据目录。不commit/push，不调用外部模型或启动真实批，不审计/背书未读取的历史远端行为。本轮没有账号用量中断；不把历史R1中断写成本轮事件。执行准备一次临时日志目录重定向失败发生在prepare/test未启动前，修正后各执行口径仅首跑一次；根一次nl路径遗漏pollutant，已按实际路径读核，未执行或改写项目。全部如实登记，不重跑已完成验证、不凑原环境全绿。
