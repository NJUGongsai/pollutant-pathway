# S3a-r4 / mimo v12 工程与化学事实互证

实际 HEAD `b7f2bba02ca49edd0a45a13bc9b8434909d99175`，直接父 `41d0cd55f3def050a62325f00235cf22da302d2e`。所有执行只在新的 `/private/tmp/ppv1_s3a_r4_execution_oo8np5ce`，本专项不改仓库、不读真实金标/题面/封存run、不联网/模型/provider。五化学核心 chemstate/audit/path_context/hypothesis/events 的全字节对父未变。以下不增加 S3a 新化学门。

## 1. 工程数字与交付精度

- 全量26个PPV1文件787/0（当前90新项均在这787里）。父同字节90项78fail/12pass/0collection：58未发生Integrity+18未发生Recovery+1未发生Contract+1缺报告键KeyError。77是行为红，1为形态红，不是78种漏洞。遇父raises断言失败后的内部保全/次级控制没有执行，详见逐案classification；不称通过。
- 12父绿实际 **11合法行为控制+1已存在坏状态拒绝保持**：9入口clean、合法策略生命周期1、合法failed生命周期1；sent/response未知状态已拒1。交付§3的明列分法相符；§5末句“9+3既有坏输入/已闭合保持”分类不精确，需P2落字，不能说三个都是坏输入控制。
- 安全G011389/8/17，277输入=当前仓217+普通v3src42+允许的非题面资产镜像18。每个缺席依赖逐nodeid披露于g01_exclusions_detail.json；原/副本前后SHA均相等。8skip=真实评价5/v4对照1/phase_d元数据2，17deselect=16slow+1显式export。原v3资产/evaluation/v4/报告数据树未读。
- 当前环境Python3.11.16/RDKit2026.03.6/SQLite3.53.4，实际新库schema与meta在current_runtime。版本profile12/search4/store9/limits3；父profile11/search3/store9/limits3。公共writer事务拒绝实际BEGIN IMMEDIATE→ROLLBACK，全表不变；合法一次首提、同参重放createdFalse全表相同。runner start/resume合成PPV1双入口fail-closed，无legacy回流。runner与legacy code_identity全文件、聚合对父一致，聚合`4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c29ae`。

## 2. v12 条件与待执行清单

| v12内容 | 本审实际证据与边界 |
| --- | --- |
| 条件A按入口拆detail字段 | 正确。额外7案中工厂/strict各未登记r、真坏SMILES一次执行，均ChemicalStateError，顶层detail.kind分别unregistered_cx_class/unparseable_smiles，无reason子层。strict mol None分支源码913–934与执行相符。恢复的canonical+r/真坏串外kind均state_structure_unparseable、内reason.kind分列；raw+r恢复outer raw_structure_rejected。公共writer外Ppv1StateContractError：canonical由同验证源带reason；raw+r外kind=raw_structure_unparseable且**没有reason字段**，不可推广所有writer均detail.reason.kind。 |
| 条件B实际CX写出/往返 | 已一次独立执行7案：ABS `a:1,3`、AND `&1:1,3`、OR `o1:1,3`、自由基`^1:0`真实写出；四合法身份往返相同，and/or/rad三字面别名拒。另旧窄15案完整执行并保留assert footer。标签语义不是输入字面英文。 |
| RegistrationHash对照限定子集 | 本轮**未另跑**RegistrationHash对照，不冒称执行证成；五核心化学文件相同，既有已审子集结论保持历史来源标签。不限本批放行，需要实际冻结材料再按预注册子集留证。 |
| 跨RDKit版本稳定性 | 本轮只用锁定2026.03.6，不安装/调用其他版本，**未验证跨版本身份稳定性**。identity可比性按锁定版本披露，不新增本批跨版本门或假证实。包内无强制运行期RDKit版本断言是静态现状，不承诺换版本不变。 |
| 空/坏isomeric直达audit，R1可达性 | 额外7案中两坏直接对象均提前ChemicalStateError：空串structured_state_missing_isomeric，真坏串state_structure_unparseable(reason.unparseable_smiles)。没有ChemicalAudit返回、admission没有调用、没有R行。合法audit控制正常。只说明这两个公共坏对象消费链，不证明R1对所有调用输入普遍不可达；若外部手工构造violated AuditCheck喂decide，防御R1分支本身存在，这不同于公共audit能到达。 |
| §6全部计数/红绿 | 本审已独立证787、78/12、1389/8/17、277SHA；实施方单独90/23以及既有test_profile1/22本轮不重复跑，不当作本审额外执行。mimo读码不构成执行，原回应保留待执行标签。 |
| cache_hit同构 | 相关消耗/创建函数源码保存，专项由authority评审裁定实际反例，工程全量含合法cache_hit；本专项不把测试数背书为边界已闭合。 |

## 3. 其余化学文字与源码互证

- 计量：unknown coefficient使元素/电荷账unknown；verified只核已声明完整清单的数值闭合，不核事实真实性或漏项真实不存在。系数绑定使用声明系数，completion surplus/deficit确按结构元素差分配平，不能扩大“未比结构重推导”的句子。known_absent是条件轴：实体或同值字符串conflict，异值/未列出unknown，数值/区间缺席numeric_absence_semantics_undefined unknown，不泛化同值结论。
- 完成许可：full/partial完成分支恒带license/scope，但unknown_coefficients或unverifiable早退不带；许可被用还需full+uncovered非空+unlicensed空。scope本身不含两根据那句，规则正文+许可定义注释260–271承载同义语义，不能再要求本轮重复硬塞scope。
- admission：R2b需caller映射构造异常detail，表示/契约拒绝不认证化学不可能；R6expand为证据覆盖许可，不是反应机理/生物可行性/速率证明。中心partial属覆盖unknown，checker scope unknown返回unknown，类型/复算完整性违规抛AuditContractError，未知center不能单独满足R6。若其他轴更早命中reject，不能一概说所有unknown最后都落R5。
- 条件：from_dict/derive父对象/audit对象强制validate；assess_conditions/assess_candidate_conditions/route_assessment本体无validate调用，需上游discipline与S3b生产接线。孤儿旧要求无快照→unknown；签名快照集合矛盾→拒；旧ID新内容→拒。条件conflict只对给定作用域，不认证事实来源或永远不可行。
- donor：失败三None与空evidence完整保留，converter返回来源/版本元数据+center_match=None，缺scope/proof进UNKNOWN；此audit其他轴可verified，不等于失败诊断已核。最终可先被其他规则reject，但中心unknown不能R6expand。供体净图对账不是完整模板/酶识别，legacy CN只旁证。
- 静态完整src65Python文件+白名单83test：十raise AuditContractError全audit.py，无包内specific except、十抛点在body不被bare/Exception/BaseException捕获。audit_hypothesis/decide_admission无src生产caller，converter也无生产caller，不构成未来动态通用证明。下一批生产caller不得吞审计异常后当verified。

## 4. 行号精度

本轮当前源码 `_verify_state_payload_facts` **store.py:475** 确为函数定义与实现，v12引用475–496正确。build_chemical_state定义chemstate.py:652（v12引用687为函数内部解析段，不是定义行）；strict定义913，audit_hypothesis417，decide_admission1643。v12“audit.py:14643→:1643”属明显笔误。from_dict引用648是入口委托行，不是对全部from_dict消费语义的新独立证明。回应该保留“读码非执行”以及未读上下文/未确认边界，实际执行数字用本审日志替换来源标签。

没有把mimo的措辞建议当新增化学代码范围或正式冻结。所有数字是合成工程契约，不外推dev（B1环境中间步骤）或298（RHEA通用酶学）科学性能。
