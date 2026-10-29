# T-E 记录侧形式归一「run 身份／缓存 key 闭合」设计稿审核

**结论：需修正。无 P0；四组 P1须在实施前闭合。** 原始索引留原样、下游内存归一的方向可用，但现有设计尚未封住“旧构建输入以新代码首次启动”，且 corpus 消费链、算子状态合同与审计对拍合同仍有冲突。本次不授权实施，不认证成绩或科学收益。

题域：**298＝RHEA 通用酶学／已见题（post-hoc）**；文档引用的来源数字未在本轮复现，不外推 dev。审核基线 HEAD：`26ad11977852644ac581d8422e88f85074d7afcb`；设计稿 SHA256：`b407fce8cf52cbe9986bb69a7a5f45be13f9ae0a3a83a12a4faa3c38ab7f69e3`。FROZEN_V3 是语义权威，本报告仅细化工程合同，不改写冻结判据。**本报告只裁定该设计基线，不覆盖审中出现的同期D1／compiler-5改动，不能据此放行其新源码树。**

## 1. 阅读范围与实际证据

下列简称的行号指本轮审前设计基线；点击文件可核。审前src/tests干净；审中另有执行者变更compiler、两个测试及工程任务书，HEAD未变。主审未回退这些变化，只从git只读取得原compiler／任务书副本，SHA与审前快照逐字相同，以下C及工程任务书链接固定到该副本。其余11个审前输入文件当时未变；不宣称交付时工作树干净。并发登记见[concurrent_changes.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/t_e_run_identity_codex_2026-10-19/concurrent_changes.json)。设计稿引出的真实资产、题面、金标、封存逐题 run 及 reports 数据均未读取。两任务书作为背景读取，其附录命令没有执行。

| 简称 | 读过的文件／范围 |
|---|---|
| D／F | [设计稿 D](/Volumes/CC/Enzyme_Agent/dependingv43/docs/T_E_RUN_IDENTITY_DESIGN_DRAFT_2026-10-19.md)全文；[冻结文本 F](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md)重点§3／§5／§8／§11及N3/N7 |
| 背景 | [工程任务书（审前固定副本）](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/t_e_run_identity_codex_2026-10-19/baseline_sources/docs/TASK_T_G_FIX_ENGINEERING_2026-10-19.md)Step E1及红线；[前置1任务书](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_T_DE_E1_PRE1_RECOMPUTE_2026-10-19.md)；[criteria-v2预注册](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md)pred1合同；AGENTS.md |
| R／B／C | [recorded_source.py（R）](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/recorded_source.py)索引、分类、find、编译、装配；[s5b_builder.py（B）](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_builder.py)版本、输入、供给、诊断及三通道；[s5b_compiler.py（C，审前固定副本）](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/t_e_run_identity_codex_2026-10-19/baseline_sources/src/pathway_v43/pollutant/s5b_compiler.py)变换、中心查询、枚举、spec |
| A／I／K | [analog_source.py（A）](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/analog_source.py)缓存与召回；[run_identity.py（I）](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/storage/run_identity.py)身份构造及指纹；[domain/identity.py（K）](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/domain/identity.py)全文 |
| W／U／P／E | [s5b_worker.py（W）](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_worker.py)首次启动／恢复；[runflow.py（U）](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py)start／resume身份；[production.py（P）](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/production.py)记录声明与NC-10消费；[evaluation.py（E）](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/evaluation.py)pred1及豁免 |
| N／S／L | [native_export.py（N）](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/native_export.py)manifest及读取；[s5b_scoring.py（S）](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_scoring.py)实际导出读取；[legacy export_v3.py（L）](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/output/export_v3.py)设计所引指纹门 |

本轮团队实际执行两类合成检查，均在全新 tmp，`PYTHONDONTWRITEBYTECODE=1`、Python `-B`；没有真实模型、网络或真实批数据消费。详细命令、环境、输出及哈希见[算子执行记录](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/t_e_run_identity_codex_2026-10-19/operator_execution.md)和[身份执行记录](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/t_e_run_identity_codex_2026-10-19/identity_execution.md)。

- **算子检查**：RDKit `2026.03.6`；16个合法构造输入通过成功域双遍字节固定点检查，1个故意无效输入两遍均failed。构造器实测有三个默认参数；`neutralize=True`关键字被拒。另证实applied输出仍可保留永久电荷。它检查的是设计原型，不能认证尚未实施的生产函数或全输入性质。
- **身份检查**：隔离完整src（含vendor）及pyproject，用原代码构建合成空池输入，只在tmp将pool常量8改9模拟构建后升级，未实现未来T-E；原输入字节不变，公开scripted start仍返回并登记新代码身份；再改tmp代码后resume正确报`IdentityMismatch(code_identity)`。worker接线只做静态互证，未跑worker端到端或真实批。`stop_reason=budget_limit`仅说明该身份入口走通，不是化学正控。副本pyc／pytest缓存计数均为0。主审另从HEAD的86个Python源码blob重算code_identity聚合，与探针复制时old-build聚合逐字相同，见[基线核对](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/t_e_run_identity_codex_2026-10-19/baseline_code_identity_check.json)，排除该探针混入同期D1。

## 2. Q1–Q11逐条裁定

| 问题 | 裁定 | 依据 | 实施前要求动作 |
|---|---|---|---|
| **Q1 短路** | **改写** | F:309–312冻结默认Uncharger分子算子、逐组分及map保留，并未冻结“无操作也必须重序列化”；D:185–190仅用电荷不变断言H不变，证明过强。R:2110–2123、C:653–668表明序列化顺序可影响映射和枚举。 | 先实际执行默认算子；按同一原子对应核q/H及重原子图、键、map、同位素、立体未变，才认成功无操作并直通原串。该细化与C-1相容；不能据图等价宣称与来源无条件canonical臂的字节／枚举结果恒等，实施臂另行对账。 |
| **Q2 applied判据** | **改写** | F:337–346要求实际q/H改写披露；D:329仅q向量判据且§4把applied误等于无电荷输出。合成检查见算子JSON。 | applied＝事务成功提交的原子化学状态改变；not_applicable＝成功无操作；failed＝未提交并完整回滚。不是比较净总电荷，也不是比较输出字符串。canon-only且算子状态不变走not_applicable。未找到q恒定而H改变的反例，不把此假设另报漏洞。 |
| **Q3 record_equation** | **采纳设计稿倾向** | B:404–406、806–822规定原始模板两侧去map声明；P:256–329发射至provenance；E:1017–1101按同侧cn和role判pred1。D:181–182“一律视体”与D:330留原样相反。 | 固定raw_ref供记录方程和出处，消费视体供路由／编译／供给／spectator。明确record_equation是“一律读视体”的例外，保原始条目、侧和重数；固定同payload做N3/N7，不凭cn已有电荷归一免对照。 |
| **Q4 matched_component** | **采纳设计稿倾向** | R:1415–1437由原始匹配侧定检索和tier；whole的R:1735及component的R:2002均记录出处；当前E/P不消费该键作身份判断。 | 保持raw matched_component；applied时另披露消费态／trace，标明它不是归一后严格身份声明。覆盖两装配分支；实际co_substrates、copies、record_products须另依同一消费域装配，不能混当只读provenance。 |
| **Q5 组分顺序** | **采纳设计稿倾向** | F:310–312逐组分重接且保map；D:183–184；R:770–785按组分序计算产物offset。 | 保输入组分序、重复份数，不跨组分排序；applied组分内部重排保原子对应，成功无操作保原串。 |
| **Q6 失败直通** | **采纳设计稿倾向** | F:162是不授归一相等，F:337–338另有failed；R:755–764原始解析拒因仍有效。 | 任失败整候选回原始消费视体并记原因，不新增“一律拒候选”规则，不继续享用另一字段成功归一收益；原始编译仍按既有门运行。 |
| **Q7 all-or-nothing** | **改写** | D:176–178要多字段同域，D:263–271却只定义单串回退；R:2061–2064／2226–2244一次消费多个列表；B:1219–1258共同消费lhs/rhs。 | 事务单位升为一次候选消费视体：donor/lhs、rhs/products、copies、full_products、派生供给及装配字段。任字段任组分失败全部回原始；保留None、空列表、顺序、重数的既有区别。 |
| **Q8 N10与版本** | **改写** | F:303–305／356／360–366、399–412；B:380–477、489–492；R:88–119、180、1276、2060–2093。I:76–112、U:1867–1876只证明启动后的身份，不能证明build出处。 | 选定pool-policy-9、recorded-source-4；route-f1f4-1可保留但绑定formnorm版本／指纹并注明路由结果可变、算法未改；compiler-4及判分语义不动。N10固定同批同事实前后逐项对拍，新池结果另列。补build→首次消费绑定，详见P1-1。 |
| **Q9 参数指纹** | **驳回原倾向，替代口径明确** | F:64／163–168／404–408要求实际默认参数；D:203–205称neutralize=True且几乎无可自省项。运行构造器文档与试调明确`canonicalOrder=True, force=False, protonationOnly=False`；neutralize关键字ArgumentError。 | 默认调用仍Uncharger()，把三个真实默认值、逐组分／序列化／短路／事务策略及RDKit入指纹；删无效工程参数。确实不可读取的内部规则单列不可读，不能以“实例只有两个方法”免掉可取得默认值。 |
| **Q10 披露／零字节** | **改写** | F:337–346；D:242–253要逐行新增三值，D:298又要旧诊断除版本键全文不变；B:1069–1100为候选诊断汇合点。R:2277–2290的verified_product_set将改为消费态产品核验。 | 每候选三态与trace落诊断，成功spec仅applied条件增加status/version/hash/trace_ref及`verification_domain=normalized_record_side`。未applied spec不改。旧诊断字段投影不变，新审计字段另验；A恒等臂先证等价旧policy-8，不能自称天然旧基线。 |
| **Q11 原子追踪／风险交集** | **改写** | F:341–344已要求落账；D:338仍留实施轮细化。C:629–668实际中心查询仅覆盖lhs子集，C:671–733的F5并不返回完整匹配原子集。 | 本设计轮定同一坐标：侧／字段／组分序／原始idx／可选原map，保源idx→归一idx→生成map关系；q/H分列并定H口径。取实际消费查询／匹配原子与同坐标lhs改动原子交集；rhs另列。无法追溯、无匹配、截断各给原因／unknown，不能伪填risk=false。风险行交人工复核，不作机制证明。 |

## 3. 八项重点裁定

**1．短路与C-1：改写后可相容。** “已实际调用默认Uncharger，确认原子状态无操作，再免去无意义重序列化”是该算子的工程实现；原稿“q向量不变便足证全部状态不变”不能无条件认可。序列化未被C-1固定，不等于来源实验的canonical枚举结果已被证明等价。保留实施臂来源锚对账，不改来源账。

**2．身份面零升格：是硬约束。** F:303–305、360–363只授同一母体的对齐候选。R:1238–1250及1415–1455的raw donor／matched side分层必须保持；不把归一后相等改名strict exact，不改底物strict/CN定义。此限制不等于新产物永远不能strict：真实执行产物仍可按未改动的既有strict判据独立验证，不能用对齐通过代替。

**3．版本：pool 8→9、source 3→4，route不升有条件成立。** 公共compile默认输入的核验域与spec会改变，source-3不能静默解释成已有归一。route-1表达F1–F4分支公式，不保证本轮输入域或路由结果不变；与pool/source/formnorm/RDKit同源机读绑定。编译器代码／判据不动时保compiler-4；本任务不要求顺带实现T-D判分披露轴或改既有criteria。

**4．N10：固定事实不变，新池变化另记。** 固定同一批不可变事件、产物、参考事实、导出及criteria版本，钉输入哈希，旧／新实现逐事件核strict布尔、身份／参与物判据及原因；v1、显式v2分开。只比总命中数会掩盖交换，不足。新池候选和事件可能不同，其strict/hit变化另外归因，既不能要求不同事件总数必同，也不能拿“池策略级”豁免N10。历史原事实合法只读重判与禁止旧产物冒充policy-9并不冲突；本次未读取实际批次执行N10。

**5．record_equation／matched_component：原始来源面保真，实际装配同域。** Q3/Q4倾向可采纳；D:181–182须明确例外，不能一面留raw、一面命令全部读视体。E按cn消费声明通常会消除部分形式差，但这不证明对所有输入更换方程原文恒等；保持原声明是最小方案。F:241／287／377–378的N3/N7固定同payload比，不要求不同新事件的v2总计数恒等。corpus参与物与NC-10字段属于真实消费，不享受raw出处例外。

**6．披露落点：pool逐行可用，现合同未完备。** compiled、compile_rejected、merged_into、pool_truncated均须保留归一事件；不能只从成功spec回填。trace需字段／侧／组分／原子坐标：R:1427–1437允许同源记录的不同匹配侧各成候选，仅record_key不能消除歧义。applied的`verified_product_set=True`只核消费态归一记录产品，在条件元数据明示证明范围；不冒充原始资产完整离子身份通过strict。未applied spec零改可保；诊断新增状态不是版本号，必须另验而非整体排除。

**7．注入点：analog方向基本可用，recorded/corpus清单须补。** analog两次召回都进_compile_analog_refs（B:1414–1425），for-ref起点建视体可覆盖F1–F5、_compile_at、supply、light_gap、spectator及状态装配，前提这些调用确实改读同一view，不能只改局部lhs/rhs仍把raw ref传编译。recorded公共compile入口覆盖其主路径；corpus component早于compile的分类以及成功后的装配尚被遗漏，见P1-2。

**8．旧compiler消费点更正：设计基线事实通过，但不能据此宣布新清单完整。** 审前C:485–510是_stereo_dissolution_mismatch，审前src搜索无enumerate_template_alignments；该基线C:125为compiler-4，C:653–668中心枚举由C:1234–1235消费。前置1任务书:56–63已将旧函数作为legacy复现另列。审前工程任务书:262的旧行号不能再作注入点；冻结C-2来源复现与中心编译的已登记口径差继续披露，不回写冻结文本。本结论不裁定同期compiler-5的新增行为。

## 4. 分级问题与最小回修清单

### P0

**未发现P0。** 本稿尚未实施；以下均以实施前可闭合的工程合同缺口列P1，没有把缺少性能数字、unsupported或本轮未做科学验证升级为阻塞。

### P1-1：build到首次消费未绑定，旧导出门的论证路径错误

**证据。** B:351–374的run_input只有qid/run_id/substrate/plan/note；B:1627–1647落文件及manifest，未绑定该输入字节sha和构建算子身份。W:70–74读磁盘plan；W:215–229若run尚不存在就start；U:1867–1876此时才登记当前源码。I:76–112、U:1997–2005确能拒既存run跨代码resume，却不能证明输入在首次start前由当前代码构建。合成探针证实旧输入可不变地被新代码start接纳并登记新身份；未实施T-E，仅模拟该入口。

D的旧导出自动过期理由也不成立：实际S:584–587调用N.read_native_export；N:180–191／600–616没有pool/formnorm/code身份字段。D引L:869–871是legacy路径，且比较saved身份与导出元数据，不是自动对当前源码重新哈希。

**要求动作。** 受控批manifest或旁块绑定build代码聚合、pool/source/formnorm版本及指纹、RDKit、源资产身份和逐run_input原始字节sha；worker／公共批首次消费先核，绑定进run来源，再创建run／调用模型。正式批旧／缺／损坏／错版本须拒并新build；不能靠新batch_tag或启动后登记当前身份洗白。可放批侧以保未applied输入可比，不要求所有通用无批scripted start加新协议，也不要求升级native-export schema或拒所有历史导出。修正D的实际导出路径与证明边界。

### P1-2：corpus分类／装配漏入口，raw声明与消费视体规则冲突

**证据。** R:1480–1485先用raw产品与A/B调用_classify_cosubstrate_candidate；其R:971–1013解析B、infer mapping并归属，早于拟归一的R:1519–1525。编译成功后R:1630–1635又把raw co_comps、flat_products、copy_products送装配；R:1898–1927建B/copy及执行产物状态，R:1957／2021以raw全产品建NC-10两处声明。若可执行产品在compile内已归一，实际执行产品与raw声明按strict可不等，P:839–858在首消费拒绝。此为具体可达合同缺口，未宣称已在真实批观察到；分类中的部分any-bond／元素判据本来不敏感，不能仅以“混域”空泛判错。

另D:181–182要求record_equation读视体，D:330却保原样；不应把原始记录声明顺手改成消费态。

**要求动作。** 原始召回／tier／来源字段不变；候选识别后、分类前建立统一消费视体，贯穿分类、编译与装配；公共compile直接入口仍共用算子，不留旁路。明确raw record_equation／matched_component是来源例外，实际供给、copy、NC-10声明各面同域同源。R:1479的碳类诊断与通配预筛不需改变既有规则，可登记原始域及不变性。

### P1-3：真实参数、事务回滚与幂等状态合同不自洽

**证据。** F:163–168要求实际参数；实测三个默认构造值可读取，D:203–205的neutralize=True不能作为构造参数。D:269–271单串回滚不足以保证跨lhs/rhs/products全组同域；D:272–274“applied输出全无电荷、二遍一律not_applicable”被构造输入反证：一个组分中和后，另一永久内盐仍带正负电；无效输入两遍均failed。成功固定点与失败原样回退是两类状态，不能强行改标签换通过。

**要求动作。** 落真实默认参数和完整指纹；整候选消费视体原子事务；成功域双遍字节固定且第二遍无新增改动，failed域允许确定性重现failed并原串不变。真实残余电荷如实保留。短路先运行算子、按同原子状态核无操作，不更换为force=True等另一算子。16合法构造仅作局部证据，批内实际消费串的既定双遍义务仍待实施履行。

### P1-4：C-5审计／字节不变及差分基线需统一成可验合同

**证据。** D:242–253每行新增三值与原子明细，与D:298只排版本键后旧诊断全文相同不能同时按字面成立；D:289把同树恒等monkeypatch直接称旧policy-8，没有证明其它新增接线／装配／披露对旧输出等价。C:629–668的实际中心查询子集与源原子、底物索引不是同坐标；D:338仍将交集算法留实施轮，无法事前验C-5。

**要求动作。** 写死逐行trace坐标、三值与unknown语义、风险交集及人工复核义务；spec条件披露与verified_product_set证明域按Q10落字。对拍分旧字段投影不变与新审计字段正确，不把后者当版本键吞掉。恒等A臂先与真实pre-T-E旧树证明等价，再比较A/B；或直接使用旧树／新树。受影响题逐差异能追溯实际applied事件；失败／无操作题保持未改spec／输入。不得通过扩大排除键、把整诊断当新增版本块来掩盖漂移。

### P2：非阻塞实施登记

| 项 | 依据 | 要求动作 |
|---|---|---|
| 原缓存共享可变对象 | R:427–460／540–611、A:196–286返回原始索引；D已要求值不变 | 落写时复制：新列表／局部view不原地改缓存；同进程A-B-A／B-A-B及缓存内容hash核既定承诺。不是另一个新P1。 |
| 术语与版本注释 | D:272–274错误无电荷推导；route-1与source版本含义易混 | 随P1修稿统一“归一收益／来源声明／消费态／独立strict验证”；route算法不变不写成路由结果不变。 |
| 执行强度边界 | 两类合成证据只覆盖构造输入／身份入口 | 实施交付分别登记代码核对、已执行测试、来源锚待验；不将本报告写成真实批复跑或性能认证。 |

## 5. 实施前必须落字的口径

| 合同面 | 供实施任务书直接消费的确定口径 |
|---|---|
| 算子／标签 | 默认Uncharger三参数实值及RDKit绑定；实际运行后判原子state-no-op直通；applied／not_applicable／failed按提交事务状态，不按字符串或净电荷。 |
| 事务／入口 | 记录候选全消费视体原子提交；corpus分类前至事件字段装配全贯通；analog同ref全消费同域；公共compile直呼同源，保None／空集／重数。 |
| 身份／来源 | 底物、raw tier及原始召回不变；record_equation与matched_component保raw；消费态字段和trace明确，归一对齐不授严格身份。 |
| build／缓存 | 原始缓存key不加归一版本，值不可变；归一memo带指纹与原串；正式批build身份与输入字节绑定，worker首次消费核对且run保来源。 |
| 版本／历史 | pool-9、source-4、formnorm-1及实参指纹；route-1／compiler-4按未改规则保留并绑定上下文。旧批零回写；历史导出保合法固定事实重判，不冒充新策略产物。 |
| C-5／对拍 | 每候选三值及可定位原子trace，匹配交集未知诚实披露；applied spec条件加证明域；未applied spec不变，旧diag投影／新增审计分别验，A臂先证旧基线等价。 |
| N10／正交 | 固定同批同事实同criteria前后逐项不变，N3/N7固定payload比；新池候选／事件变化另表归因。P3/P4来源与实施口径差登记，不以来源数字替代本轮执行，不追加科学性能门。 |

**Q10最小字段合同（修订设计采用本段定名与集合）。** 诊断行保留`record_side_form_norm ∈ {applied, not_applicable, failed}`，追加`record_side_form_norm_trace`：`source_ref`包含`channel/asset_sha256/record_key/matched_side_or_component`；`source_fields`标明`record_equation`与`matched_component`为raw来源字段；`changes[]`逐项包含`side/entry_index/fragment_index/source_atom_index/original_map`、`charge_before/charge_after`、`hydrogen_before/hydrogen_after`（H口径固定为总H并分列显式／隐式来源）。trace包含`atom_correspondence[]`，逐项以同一源坐标绑定`normalized_atom_index`及`generated_map`（如有）；`changes[]`原子锚回指该表，缺失对应须给明确原因，不凭重排后的idx猜测；因此recorded无原始map也可机核对应与交集。trace另含`matching_scope`、`intersection`、`risk_status`及`unknown_reason`；原子集合全部用前述同一坐标。`matching_scope`明确`center_l1_l2`为设计基线实际消费范围，`legacy_whole`仅作来源复现，两者不得合并冒充冻结C-2与现实编译范围完全相同。`risk_status ∈ {present, absent, unknown, not_applicable}`；可核交集非空为present，可核空集才为absent，无法追溯／无匹配／截断须如实给unknown或not_applicable及原因，不硬填false。该结构不要求重复存整条SMILES。

applied成功spec的`compile`中条件追加且仅追加本轮审计集合：`record_side_form_norm="applied"`、`record_side_form_norm_version`、`record_side_form_norm_param_sha256`、`record_side_form_norm_trace_ref`、`verification_domain="normalized_record_side"`；trace_ref以同一候选trace的确定性内容哈希绑定，必须能回到对应诊断。未applied spec这些新键缺席，保原字节。批级版本与指纹仍须输出；所有新增audit字段单独验收，不能全部作为version键从对拍排除而不核。

**总体裁定：需修正。四组P1按上表落字并同范围复审后，再进入实施；本轮没有P0、没有新增科学性能门。**
