# pollutant_pathway_v1 S5a 回修 r1 正链复审（R2）

日期：2026-10-09，Asia/Shanghai。正链 Codex 主审，协作子代理在独立 fresh 隔离树执行；不调用外部模型，不以交付数字或 mimo 读码替代程序证据。

**结论：S5a r1 不通过；唯一残余阻塞 P1=[S5A-02]。**S5A-01/03/04 关闭；S5A-02 的旧18项同源对照已一致、2项负要求已单列，但显式非规范要求单位仍在适配时丢失，可被判成相容或冲突。mimo v22 B1 获公共链确证；A1/C1 事实成立但按固定范围归P2；B2的合法公共链顺序推论未成立，正式更正。S4/S3、ISO-01 保持关闭；不确认本轮阶段放行，不启动S5b，科学性能pending。

## 1. 固定验收、实际身份与执行纪律

- HEAD：`1ef9e4840ff1be233dedcb543b967447cd591276`；直接父：`2e1e7af3c4bef9e98db9481167a835cabd3c088e`。
- 基准：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_2026-10-09.md` §4四P1/§8有限提示词；任务书 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md` §14/§15/§16/§12。不重开已证项，不凭unsupported或保守过拒增加科学门。
- 交付：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5A_REWORK_DELIVERY_R1_2026-10-09.md`；mimo请求/回应r22。回应为只读意见；网关证书失败两次、代理重启续跑为用户材料/provenance，不是本审模型执行。本审未调用任何模型通道。
- 版本：evaluation-1→2、preregistration-template-1→2、profile-20→21；reference-graph-1/split-manifest-1保持。条件沿冻结`path_context`同源路线，未选独立评测口径，未改criteria-v1正文或FREEZE_RECORD。

初始守卫 **2026-10-09 04:22:13+08:00**：133项src/vendor/PPV1测试/指定文档输入、旧永久证据3505文件SHA与精确文件集合、HEAD/父/工作树。发布前后再次核验。当前阶段没有账号额度中断；上一轮中断只作为旧封包来源历史，不嫁接到本轮。

PPV1、父5文件、G01、legacy、所有本轮业务探针均fresh `/private/tmp`，完整src含vendor与pyproject metadata，conda depending43 Python3.11.16/RDKit2026.03.6/SQLite3.53.4，主命令`-B`、`PYTHONDONTWRITEBYTECODE=1`、pytest cacheoff；父子v3同根批准普通镜像。G01304安全输入，真实仓tests/不全量执行。未访问金标/题面/封存逐题run/dependingv4/原v3评价资产；判分零LLM，无commit/push；仓内仅新增本报告与证据目录。

## 2. 独立执行数字、红绿和40检查口径

| 项目 | 本审实际结果 | 范围与精度 |
| --- | --- | --- |
| PPV1全量 | **1087 passed / 0 skipped，exit0** | 41文件；1045既有+42新；不把通过数当漏洞数/科学指标 |
| 父2e1e7af同字节 | **41 failed / 94 passed / 0 collection，exit1** | 本轮5个新增/更新文件，detached父隔离源码；不是父全部PPV1的数字 |
| 父41红 | **32行为+1实现缺失+3字段缺失+2拒绝kind+3版本** | 行为=01七+02十九+03四+04二；AttributeError/KeyError不报行为翻转 |
| G01安全隔离 | **1689 passed / 8 skipped / 17 deselected，exit0** | 304输入复制时/执行后/批准来源SHA一致；仓侧244输入；谱系303+1新测试，7旧输入经本轮源码/测试变更如实登记 |
| 旧40检查 | **40/40通过** | **27分类变化+13保持**，不是40漏洞或40行为翻转；见下文 |
| 身份/边专项 | **50次公开evaluate、1匹配器单元、56观察断言完成** | 17旧identity+6旧necessary+18新A1+9新C1；5真实run全表/数据库字节守卫保持 |
| 旧条件/写边界 | **20条件、5写边界完整执行** | 18可比与冻结一致；2负要求不可表示；4写出界拒/1合法保持，另无root/普通写2控制 |
| mimo条件新增 | **17真实公开条件案** | B1六、B2十（五两序）、B3一点值；B1契约断言4失败/2正控通过，exit1按设计揭示残余 |
| legacy/继承 | **两树4合成公共产物逐字节同、标准52聚合保持** | `18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6` |

父分类更正：交付称04“三行为+一kind”；实际为**两行为+两kind**。新增no_root案父本来就拒，只是`gold_content_unauthorized_path`与`gold_content_root_required`不同；旧S5-27也在kind断言首次停止。未执行的后续plain-write不能算行为红。完整逐nodeid及首次停止范围在`execution/baseline_classification.json`。

40核对使用复制到fresh tmp的交付只读后处理器，输入是**上一轮正链独立封包的父观察**与本轮fresh当前观察，未采实施方before/after数字，也未把旧before冒称本轮新跑父探针。本轮父新回归独立fresh执行如上。40=六scope+一strict+两真实CN+四necessary+两participants-only P2+20条件+5写边界：

- 分类变化27：六封顶+四必要节点+13旧条件分歧+两负要求换不表示桶+两相对路径拒。
- 保持13：strict/CN三+participants-only两+条件五同义+两绝对拒/一合法写。

其中负要求换桶不是两项冻结判据失败。顶层40通过只验证旧验收输入，不能抵销新增显式要求单位反例。只读后处理初版漏合并单独的六necessary数组，得34/0，包装器40计数断言失败；保留原输入/输出/exit，合并原数组后40/0。没有修改业务字段、没有重跑业务，不算产品失败。

G018 skip＝v4对照根1、v2 provenance/summary2、冻结v3真实评价依赖5；17 deselect＝16slow+1显式charge/evaluation fixture，逐nodeid/理由完整见`execution/README.md`与缺席JSON。缺席不算通过，不读取红线依赖凑数。主命令禁缓存，G01测试子进程仍产生7个隔离pyc，current/parent为0；源SHA不变、不归档、不写真实仓/旧证据，不能照抄交付“隔离树均未见pyc”。全部数字是合成工程口径，不外推dev/298，额外探针不与suite数相加。

## 3. 原四P1逐入口收口与合法正控

| 原项 | 首消费→实际行为→裁定 |
| --- | --- |
| S5A-01 | `match_reference_nodes`先消费节点scope，再授strict；cn_only/partial/unknown内容同值也封顶，边严格候选/严格聚合同步不授strict。六原案完整翻转，合法strict、真正同位素/电荷CN控制保持。**关闭**；根配对有限支持例外另列P2，不宣称所有身份入口都已消费许可 |
| S5A-02 | ConditionScope适配→`build_requirement/build_condition_fact`→`aggregate_environment_fit`，18可比旧案分类全同源、13旧分歧翻转、五控制保持。两要求known_absent单列`requirement_status_not_representable`。**旧核心修复确认，整体仍残余P1**，见§4 |
| S5A-03 | 逐声明必要from/to节点许可严格命中→完整集合覆盖→边/聚合；两合法完整reactant/product核心案及两个limited duplicate不再strict，`required_node_gaps`如实。合法exact、partial_subset、superset/共同产物、独立备选保持。participants-only旧P2保持。**关闭** |
| S5A-04 | 相对cwd解析→声明根/授权子根核验→同一resolved路径写入；四出界先拒，零目标新文件/目录，合法根写保持。无root含金标标记先拒，普通输出保持。仅synthetic-placeholder-not-gold文本，无真实金标。**关闭**；不扩DLP/敌意race/沙箱门 |

旧条件的18案仍是**语义适配对照，不是两schema原字节等形**：区间字符串规范成lo/hi、点值显式point、源必要性/场景映射登记；未知/单位不符/absence/多事实/无源必要性与同源冻结结果一致。负要求两案在冻结Requirement无直接字段，不能发明对称负要求。阶段/时间要求完整表示尚无，ConditionScope无introduced_phase_id，评测传phase_id空、已有事实阶段由同源过滤；科学支持范围保持披露，不单因这个unsupported添加P1。

## 4. 唯一残余P1：S5A-02 显式要求单位被披露但不参与判决

### 4.1 原验收出处与公开证据

上一轮§4.2/§8-02要求可审计映射、单位消费、缺表示能力给unknown/unsupported；任务书§9.5/§14.1、S5-13/14禁止把未知混入相容/冲突。此处属于**同一个适配首消费规则的残余**，不是新增单位换算或科学性能门。

`evaluation.py:999-1024`识别noncanonical/unexpected/未声明unit，只append披露，然后return仍不含unit的kwargs；`:1128-1202`按这些kwargs构造冻结Requirement并分类。冻结Requirement本来值恒为键规范单位，没有unit参数；故**显式298 K不能在丢掉K后当298 C送入该契约**。同源裁决无法修正已经丢失的输入语义。

全部六案经真实`start_run→带ledger的read_native_export→evaluate_scientific→聚合`，不是假native/自制reader：

| 参考要求 | 真实同源事实 | 实际分类 | 执行级裁定 |
| --- | --- | --- | --- |
| temperature_C=298，unit=K | 25 C | essential_conflict+unit_noncanonical | 应为不支持映射/unknown；没有做K→C换算，不能直接比 |
| temperature_C=25，unit=K | 25 C | compatible+unit_noncanonical | 未核单位语义却授相容，直接违背缺表示能力保守规则 |
| temperature_C=77，unit=F | 25 C | essential_conflict+unit_noncanonical | 同上，不以猜测换算判相容 |
| electron_acceptor=O2，unit=mg/L | O2、无单位 | compatible+unit_unexpected | 该实体键无此单位语义，不能披露未知后仍授相容 |
| temperature_C=25，unit=C | 25 C | compatible | 合法正控保持 |
| temperature_C=25，unit空 | 25 C | compatible+unit_not_declared | 要求值可按冻结键规范单位约定；此案不要求一律拒空单位，披露文字需同步 |

`conditions/results/B1_contract_assertions.json`四不支持单位最低断言失败、两合法正控通过。披露note说unknown却实际compatible/conflict，是事实失真；**只把note改成“忽略单位”不能兑现原最低收口**。mimo B1采信到上述程序互证；未授权独立条件口径不能通过改文字默选。

### 4.2 最低收口（下一轮有限范围）

1. 在共同ConditionScope→Requirement映射首消费处决定支持能力。显式非规范/与键量纲冲突的单位无法合法映射时，真正返回unknown/unsupported分类及原unit/value/key/原因，不能丢unit后授compatible或conflict；公共单条分类、sample分类与聚合同源消费。
2. 区分**要求侧按键规范单位约定**与**事实侧来源单位三态**。空要求unit若按冻结canonical-by-key默认合法，应明确机器/文案说明；事实侧temperature缺unit仍source_unit_unknown。规范C、pH无量纲合法控制保持；不要求全面拒空单位。
3. 复用六真实公开案，至少四不支持单位实际降档、两个正控保持；补“有合法事实+有必要性来源+非规范要求unit”的判别回归，不用facts=[]天然unknown的测试代替单位分支验收。若无法表示维度不授完整相容/冲突。
4. 不新增K/F换算、标签库、负要求、优化值语义，不修改冻结path_context/criteria-v1，不扩S5b。语义变化依已有version规范登记，proposed/交付/mimo请求与实际支持范围同步。

证据入口：`conditions/results/mimo/conditions_summary.json`及六分案、完整请求/reader/native结果、`results/B1_contract_assertions.json`、`inputs/source_excerpts.md`、`logs/`。

## 5. mimo v22四项建议P1的正式互证裁定

### A1：根配对事实成立，归P2，不能宣称所有入口许可闭合

`evaluation.py:1582-1611`根内容strict配对，未读root identity_scope；`:1890-1898`配不上便记native_export_missing。18真实公开root案（同位素/电荷/立体三轴×六）：9有限scope内容不同但CN同+3strict内容不同对照均不评；3有限内容相同+3strict相同正常scored。所有native首读成功，五run全表/数据库字节不变，**“S4未交付”归因失实**。

按AGENTS固定范围与上一轮scope最低门，当前方向是保守unsupported/不评，未授错误strict/R6、未把unknown计化学错误、未接纳坏权威；本轮不以支持增强单独加新P1。归P2而非否认事实。后续先区分actual native missing与root_identity_unresolved，保留未配对导出/有限根维度证据并同步例外；不由本审发明CN/模糊根配对、歧义多样本归属算法或独立指标许可。科学评测/拟冻结前须准确披露此支持范围。

### B1：公共链成立，保留S5A-02 P1

见§4。不是仅文案级错误；实际丢显式单位后授compatible/conflict，因此不能以“同源实现”背书映射正确。

### B2：合法公共链顺序P1未成立，纠正读码扩推；低层边界P2

`_assess_species_requirement`有same[0]属实，但checked `build_condition_fact`在`path_context.py:406-407`先将unknown的value清为None；合法native回执也保存此正规化。十真实公开案/五个两序：present×unknown均compatible、absent×unknown均conflict、同实体present×absent均unknown、O2/NO3并存均compatible、仅NO3/Fe3而要求O2均unknown。**不能由same[0]推本轮合法链known×unknown顺序相关。**

mimo请求原文只承诺“同键多条**相反**事实”两序同判，此承诺已实测成立；mimo将它扩大为任意多事实unknown且假设unknown仍带O2，须更正。四个直接dataclass低层对照绕过checked builder、保留unknown实体值时确有次序差异；这是低层支持边界，非合法`start→native→evaluate`反例。不替用户/teacher选择修改冻结侧对象或物种语义，列P2/文字范围限定。

### C1：字段未消费事实成立，保持既有P2

九公开组（完整、少H2产物、多H2反应物×declared_complete/partial/unknown）结果不因participant_list_status改变；exact、superset/partial_subset、共同产物披露保持。只消费声明from/to状态集合，未证明参考清单完整、角色/计量完整。上一轮§5-P2已登记此限制，§4.3也未要求新增这套门；没有新的同契约错误严格授信证据把它重开。保持P2/teacher口径，拟冻结前同步“exact=与声明集合相等”与partial/unknown清单超集/分母；不私自增角色系数/occurrence一一映射门。

## 6. 交付一致性、继承与遗留P2/晨报事项

核心旧修复/1087/41+94/1689执行数字互证。交付“四P1闭合”需缩窄为三项闭合、02旧案闭合但单位映射残余；40全过是检查数，不是全规则无残余。

- **来源精度**：实施包实际126文件，manifest/SUMS纳123附件，另排根manifest、SUMS及seal_package.py；123附件全部SHA核验通过，但不能说126全部纳SHA、只排两控制文件。主审另保存封包脚本副本与SHA，不修改实施包；本审新根仅排自身两控制文件，所有嵌套manifest/子controls纳hash。实施seal的HEAD记录父2e1e7af是提交前封包时事实，不当当前待审HEAD。
- **字段/数字同步**：04父红两行为+两kind；G01子进程7pyc例外；FREEZE_RECORD完整SHA实际`6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610`，交付§2一处写成b6a7属字符误记。冻结文件实际与父字节同；正文SHA`7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4`。
- **A3/A4/A5**：封顶CN与真正CN聚合同桶、necessary gap因果需联读节点；不可解析参考样本invalid_input有例外。读码/已完成身份观察可核，后续精度同步，不假装当前已具因果子桶或无限支持。
- **B3/B4/B5/B6**：裸数25映point而事实30C判冲突已公开执行；点值假定已登记，不能代teacher改成optimum。私有helper坏oxygen+合法oxygen可跳坏事实后compatible，但真实start在构造期已拒，eval未执行；不报成合法公共链漏洞。preference无源探针/oxygen枚举包含等本轮未额外执行，读码建议仍P2/teacher；不夸称每建议已通过。不新增标签/换算/集合包含语义。
- **C3/C4/继承P2**：图级known_gaps/运行级预算因果下放边桶、非strict事件与outside桶双计为读码精度项，不能把分轴数无说明相加。participants-only、unknown==unknown scope、roles/coefs/occurrence分母、endpoint helper三件/死键、R16样本≠确认事件继续旧P2。未伪造native重开S4，不把P2捆成新阶段门。

S3生产/存储/搜索/队列/协议/runner，S4endpoint/native_result/native_export及audit、legacy/G2/AtomTool与父关键字节保持，1087回归含17同位素常驻正负控，四legacy公共产物与52聚合互证。条件变动只在评测适配侧，冻结规则未改。继承字节不作为新证漏洞免责；本轮已检验新增单位反例。

晨报需用户/teacher：任务书§10.1二十项TBD（题源/金标/独立性、dev/298及known/unseen样本/分母、阈值/CI/费用等）；负要求/数值basis/物种低层边界、有限根配对支持、partial参考清单/occurrence轴、endpoint独立复核与confirmed分母。保持沿冻结同源路线；如另选独立条件口径先裁定/独立命名版本/分歧报告，当前不得默选。S5b仍未授权未启动。

## 7. 永久证据、证明范围及最终裁定

目录：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s5a_codex_r2_2026-10-09/`。

- `execution/`：三suite完整argv/cwd/固定env/exit/stdout/stderr/JUnit，同字节测试、304来源/前后SHA、逐nodeid缺席/分类、legacy/源继承、缓存观察。
- `identity/`：50公开评测、1单元、56观察；五run全表/DB字节守卫及54artifact、五嵌套manifest；A1十八案/C1九案、旧scope/necessary及正控。
- `conditions/`：20旧+17新真实条件案、写边界与无root/普通控制、B1四失败/两正控、B2十公开/四低层与B4前置拒；38合成库**末态全表**、482个artifact JSON/文本、37嵌套manifest。不把末态快照冒称所有案的前后零写证明。
- `root_audit/`：133输入/3505旧证据守卫，冻结与实施/旧包只读核验，source diff与mimo材料，34→40只读后处理全过程/原输入/原脚本，发布收据；`report.sha256`绑定本报告。

脚本先复制fresh tmp执行，永久包不原地建库/写缓存。argv/env是固定相关环境，不伪造全部ambient环境。条件探针无socket仪表，不宣称全局网络计数实测为零。SQLite二进制、pyc/pytest缓存/symlink不封包；业务输入输出及必要全表/版本/SHA保全，嵌套manifest纳哈希。

条件新专项第一次CLI mode调度错误exit1发生在任何新业务案前，修正调度后17案只执行一次；完整初次日志保留。root只读34计数包装失败亦保留，不计产品红。新B1断言exit1是已完成公开输出违反契约，不伪装成功；采集exit0与规则通过分开。

**S5a r1 不通过，P1=[S5A-02]。**三组关闭、旧18+2同源修复确认，但单位适配授信仍阻塞原工程验收。程序interface_verified_only是模式标志，本审尚不确认阶段放行。下一轮仅修§4显式要求单位映射；其余新增意见按§5/§6保留P2/待裁定，不重开已证项、不触S5b或科学阈值。

## 8. 下一轮有限范围回修提示词

```text
在 /Volumes/CC/Enzyme_Agent/dependingv43 做S5a r2有限回修。
基线1ef9e4840ff1be233dedcb543b967447cd591276。
必读AGENTS、本报告§3/§4/§5/§7、S5任务书§14/15/16/12、mimo r22。
唯一阻塞S5A-02：显式非规范/键量纲不支持的要求unit被识别披露，
但丢弃后送入冻结canonical-by-key Requirement，授compatible/conflict。
只收这个适配首消费缺口；S5A-01/03/04、S4/S3/ISO-01保持关闭。

先列ConditionScope validate/map/classify/classify_sample/aggregate入口。
共同映射先决定单位支持；无法合法表示的显式K/F/实体键mg/L等，
真正分类unknown/unsupported并机读保留原unit/value/key/原因，
不能只改note说忽略单位，不能把未知范围授相容或冲突。
未能映射就沿既有不支持路线；不新做K/F换算/label/负要求，
不改冻结path_context/criteria-v1或FREEZE_RECORD。

区分要求值canonical-by-key默认与事实侧来源单位三态。
空要求unit可明确按冻结键规范单位约定，不要求全面拒空；
事实temperature缺unit仍unknown；合法C/无量纲/既有正控保持。
复用conditions六个B1真实公开案：四不支持单位实际降档，两合法保持。
新增回归要有合法事实、有necessity来源，不用facts=[]天然unknown
冒充单位分支；公开sample结果→聚合不得仍记compatible/conflict。
保留18旧同源条件+2required_absent单列、旧写边界/身份/必要节点，
不发明teacher口径。对父新回归真实红与合法绿，行为/字段/版本分开。

语义/version依既有规范登记，proposed/交付/mimo请求与代码同真。
文案同步B2事实纠错：合法unknown经checked builder值清None，
相反present/absent两序均unknown；直接dataclass低层边界另列P2。
A1有限根配对假missing、C1清单完整性和其它晨报P2保持登记，
不强迫本轮扩根模糊配对/角色计量/科学分母门。

交付逐入口→行为→完整正负控制→证据/残留；PPV1、直接父同字节
逐nodeid红绿分类，G01安全隔离沿304谱系及source SHA前后/缺席逐项。
新fresh证据含完整输入输出/argv/env/exit/SHA，所有嵌套manifest及
子包controls纳hash，只排根两个自控制文件；旧probe只复制tmp跑。
准确记录子进程缓存例外、调度失败与未执行内段，不凑全绿/40翻转。
禁止金标/题面/封存逐题/v4/原v3评价资产；不启动S5b、不外模判分/
真实费用，不代用户teacher定阈值/金标/分母或独立条件规则。
按AGENTS本地v4.3显式路径提交不push；自包含合成mimo请求由主会话
安排评审，执行类标待验证，再交Codex正链有限复审。
```
