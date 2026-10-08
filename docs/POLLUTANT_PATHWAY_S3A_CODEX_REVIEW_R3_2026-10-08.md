# pollutant_pathway_v1：S3a 回修 r3 独立复审

日期：**2026-10-08（Asia/Shanghai）**。仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。

**结论：S3a 不通过，S3b 暂不可启动。P1 仍为原三组 S3A-02／03／04，但 R2 已列的主要反例均已修复；本次残余是必要引用集合缺项、请求状态口未消费冻结策略、未知状态可被正常写成 failed。** S3A-01／05 保持关闭。本审不追加 S3b、科学性能、机制库、正式冻结或外部 exactly-once 门。

实际 HEAD：`41d0cd55f3def050a62325f00235cf22da302d2e`；直接父提交：`dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`。本报告源码行号对应 r3 HEAD。

从污染物降解路径预测的目标看，本批应先保证路径搜索能够如实记录用掉的额度、执行身份和恢复状态。漏掉必要额度仍完成、坏策略仍授权状态变更，会让后续搜索和恢复失去可信底座；这与具体反应机理或预测准确率无关。

永久证据：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_r3_2026-10-08/README.md`。报告 §8 可直接交实施 agent 做有限回修。

## 1. 固定验收面、独立性与执行纪律

本轮唯一阻塞基准是 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R2_2026-10-07.md` §4 三组最低验收、§7 放行条件；继承原 S3 任务书的 S3a 范围。主文件：

- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3A_DELIVERY_R3_2026-10-07.md`。
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r11.md`，连同当前 v11 请求；意见采信到与源码、公开执行互证为止。

三个专项分别负责工程全量与化学精度、搜索权威、预算／请求／停止；在新仓外 tmp 复制完整源码（含 vendor 与必要 metadata）及 R2 合成反例输入后执行。没有在永久证据原地建库。使用 depending43、Python `-B`、禁字节码与 pytest cache；不访问真实金标、题面、封存逐题 run、dependingv4，不调用外部模型／真实 provider、不 push／commit，判分零 LLM、实际网络 0。`provider_kind=real` 的登记夹具不代表真实调用。

PPV1、父基线新回归、安全 G01 各独立执行一次，三个专项包、归档暂存与草稿交叉核对已在中断前完成。永久发布前因 **ChatGPT账号用量上限**中断（用户说明为额度限制、非代码错误）；额度恢复后用户授权继续，2026-10-07 18:04:51 UTC（本地2026-10-08 02:04:51）恢复盘点，HEAD／父与工作树未变。本次直接复用全部已完成的本审验证，只补文档、中断记录与最终SHA归档，**没有重跑测试／探针**，亦未将实施方／主会话日志换成本审结果。用户描述约5800行输出未独立精确计数，不作验收指标；详见 `INTERRUPTION_RESUME.json`。 探针夹具错误保留原日志：done foreign输出已完整捕获后，adapter误期待SearchIdentityConflict而实际SearchContractError，随后只读纠正断言，不重跑两案；预算补充脚本末段合法装配控制误删version，前31案完整、未到后段不报通过，合法带version控制另行单案执行。旧永久文件和现存源码／测试／文档／AGENTS.md 均只读，主仓仅新增本报告与新证据目录。输入哈希、实际 HEAD／父、原工作树差异及发布前后校验见 `input_snapshot.json`、`workspace_integrity.json`。

## 2. 独立执行数字及红绿精度

| 执行 | 本审结果 | 边界 |
| --- | --- | --- |
| PPV1 全量（25 文件） | **697 passed／0 skipped／0 failed** | 648 存量＋49 新回归；工程合成，不是科学性能 |
| 父 dcb7 同字节 r3 新回归 | **40 failed／9 passed／0 collection error** | 未改 import、输入或期待适配父版本 |
| 安全隔离 G01 | **1299 passed／8 skipped／17 deselected**，exit 0 | **276** 白名单输入，前后 SHA 一致 |

40 失败全部为有效行为断言：**28 未发生预期 SearchIntegrityError＋3 未发生 SearchContractError＋2 未发生 SearchRecoveryError＋2 未发生 SearchIdentityConflict＋5 返回值／表状态断言失败**。其中 B3 两案锁定先写 event 后拒的顺序缺口；没有 R2 的返回形态 TypeError、collection 红或错误 kind 首断言先停。交付书“28 未拒＋12 值断言”应精化为 **35 未发生指定异常＋5 值断言**。

9 个父绿是 **4 个合法行为控制＋5 个既有坏输入拒绝控制**（3 首提附随语义、1 已拒的越界冻结块、1 commit.run 错属 recover 单口已拒），不是9个合法化学正控。当前49通过是697全量中的子计数，不相加。PPV1 pytest7.93s／命令墙钟8.255s；G01 pytest196.91s／控制器命令墙钟198.929s（内部pytest子进程198.409s），不同计时层分别登记。交付方额外独立49、23项矩阵和更新既有测试1红／22绿不冒充本审又跑一次；本审四硬杀／barrier另有实际执行证据。

G01 白名单：当前仓 **216**＋普通 dependingv3/src **42**＋本仓明确非题面普通资产镜像 **18**。所有引擎／资产路径固定隔离树，外部数据根空；不补缺席真实评价、v4 或 phase_d 派生资产。

| 实际缺席／排除 | 披露 |
| --- | --- |
| 5 skip，真实评价依赖 | test_batch_runner:52；test_score_report:110／163／172／184 |
| 1 skip，v4 对照 | test_analog_assets:95 |
| 2 skip，phase_d metadata | test_analog_v2_corpus:62／153 |
| 16 deselect，slow | nodeid 逐项留证，未执行测试体 |
| 1 显式 deselect | `tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden` |

历史 R7 1110、R8 1138、S3a 首批1196、r2 1250 的隔离通过数分别登记，不与1299混计。实际环境 Python3.11.16／RDKit2026.03.6／SQLite3.53.4；profile-11／search-3／store-9／limits-3。全部数字不外推 dev（B1 环境中间步骤）或298（RHEA 通用酶学）的科学性能。

## 3. 原反例与继承状态

| 原组 | 本轮已证修复／合法控制 | 裁定 |
| --- | --- | --- |
| S3A-01 | 四异身份输出普通提交／write／B3拒且保全；合法 B3 同 output 幂等 | 保持关闭 |
| S3A-02 | R2 原27分案及120分段捕获（111坏案拒、9合法）：预约单位／状态／scope、attempt 状态／hypothesis／task、commit 归属／引用、附随投影／计划、B3缺行前置均拒；done同A返回真实A，foreign明确冲突；原坏记录无新成功消费 | 原已列行级反例关闭，但必要引用**集合**仍不完整，§4.1 |
| S3A-03 | 原40个有效预算矩阵控制符合合同；null／缺版本在预算读取、claim、无 expected recover 先拒；合法装配完整块、各资源0、不退款／未执行释放保持 | 原读取／恢复缺口关闭，请求状态口仍漏冻结块，§4.2 |
| S3A-04 | 原60请求矩阵适用拒绝或允许的结构化 reference_integrity；stored/incoming 身份冲突、run绑定、expand必要attempt、坏 pending 披露均成立；非expand空attempt／retry／scripted0／real0保持 | 原引用反例关闭，未知状态正常转 failed 仍违生命周期，§4.3 |
| S3A-05 | claimed／open 有余不 exhausted；14停止控制与六原因63组合保持 | 保持关闭 |

四独立子进程硬杀 B1–B4、双独立进程 ready／GO barrier、H07 hash／反序列化保全、H08记录负控与合法重复恢复保持。正常 public store 首提事务回滚、合法首提／幂等、runner PPV1 start／resume 双入口 fail-closed 保持。

化学五核心文件 chemstate／audit／path_context／hypothesis／events 对父全字节相同；R8认可的R6五组与R7两项保持关闭。本次用旧12×2权威反例、全量回归及窄化学探针检查必要继承，不冒称重新执行全部历史 R8 脚本。

## 4. 三组同合同内残余 P1

### 4.1 S3A-02：逐行有效不等于必要引用集合完整

**原验收：R2 §4.1 最低修复要求必要预约／完整冻结引用、done必要结算证明及B3写事件前校验；首轮最低修复要求本action必需预约／attempt的内容与冻结引用。** 此处不要求历史来源认证或整库抗一致重造。

`search.py:1651` 的 `_verify_action_references` 对已列的每一行核单位、状态、scope／subject和归属，这是有效修复。但取出 `budget_reservation_ref` 后只要求非空，再遍历列出的引用；没有判断该 action 按既有 claim／attempt 创建规则**应具有的必要预约集合**是否缺项。

限定补证：同一合法 expand claim 本有总 action、alternative、attempt 三类必要预约，每次仅从冻结引用清单删其中一项；分别保留对应行或再删除该行，不重造 event／hypothesis／hash，不改其他权威。9适用入口×3必要项×2模式，**54坏分案全部正常返回**；9个未改控制正常。

- **B3 删总额度引用＋行：**初始 event0，recover 实际写 event1／commit1并 done，总action预算 **used=0／remaining=10**。已有的B3行级前置守卫被不完整清单绕过。
- **首次 complete／B4：**只删引用、行仍在时，被漏行没有结算，仍 reserved，却写提交／完成；删引用＋行时必要额度消失。
- **done 四复用：**缺必要集合仍被称 `done_commit_verified`或成功复用，不能仅因剩余行都合法就证明已完整结算。
- **B1／defer：**不完整引用仍当 intact／可挂起；不是所有54案都新增event，逐案前后表分别登记，不能把零新增的读取口说成写了事件。

独立上限1完整链进一步钉住实际额度突破：干净同输入第一次完成后第二claim按预算不足拒；仅第一次claim后的总额度ref＋row移除，第一次仍complete且used0，第二个不同hypothesis正常claim／submit／complete，最终**events2／commits2／总used1，而max_total_search_actions=1**。无defer退款，此项仍归必要证明遗漏S3A-02，不重开已关闭的退款反例。

这是“漏掉必要证明仍成功消费”，不是原三种坏scope／units／status回退。证据由 authority 专项的必要引用集合补证脚本、完整前后表、原正确输入与9控制组成。

**最低收口：**按现有创建参数同源确定各 action kind／attempt 所需预约集合，首次消费核完整性后再逐行核内容；不能只检查剩余清单非空。覆盖first complete／B4／B3事件前／B1／defer／done四口，缺项先结构化拒、保全、无坏action新commit／consume／成功确认，B3零event新增。保持主体共享alternative、条件适用reopen、合法非expand／非事件outcome、同hypothesis不同revision、合法幂等，不把无关资源强加所有action，也不猜补缺行；合法cache_hit retrieve不强加未消费的资源预约。无需另建机制库或给全部历史记录新签名。

### 4.2 S3A-03：请求状态口仍不核已冻结策略

**原验收：R2 §4.2 明列首次注册后的读取／recovery／budget／claim／request消费先核完整冻结块；首轮S3A-04也要求请求各适用口核策略。** 不需要实际provider才可检验状态写账协议。

`register_model_request`（search.py:1085）调用 `_limits`，r3装配／严格消费拆分正确；但 `record_request_sent`、`record_request_response`、`mark_request_failed` 的状态消费只核状态和 `_verify_request_execution`（:1288），不消费 `_limits`／冻结块守卫。

合法先登记scripted请求，再只把存储 `search_limits` 置null或删version：**3状态口×2模式均成功、实际写sent／responded／failed**，没有 `search_policy_block_corrupt`；四个原坏值（bool／越界／未知键／负数）×3状态口亦接受。实际网络0，不宣称发送了provider。相同坏块在预算／claim／recover已拒，不能扩大为所有请求消费都拒。

**最低收口：**状态首消费也共用严格冻结块守卫，在新status写入／执行许可之前失败；核失败不得正常改状态，不依赖expected policy或调用方预验。保持合法用户partial覆盖的装配、注册后完整块、合法registered→sent→responded／failed、各适用零预算和失败／悬空不退已登记额度。无需重复扣已占请求额度或重新解释limits单位；这里只补缺失消费口。

### 4.3 S3A-04：枚举外状态可被正常改记 failed

**原验收：R2 §4.3／首轮S3A-04最低修复要求合法生命周期及坏案零status成功写入。** 当前已有 `REQUEST_STATUSES` 和状态迁移定义，不要求新枚举体系或专门reason名称。

`mark_request_failed`（search.py:1460，文档:1461）明确 **registered／sent→failed**；实现只排除responded／failed／abandoned，未正面限定合法来源。合法登记行仅改status为 `corrupt-status` 后，公共 `mark_request_failed` 正常返回并写 **corrupt-status→failed**。损坏的生命周期被正常化，原未知状态消失。sent／response对同坏status确实拒且零写；所以交付§7.4“不会成功写新状态”不实。

同键重登记返回unchanged并带坏status是旁证，不额外数一组；run范围恢复不扫描该未知状态也单列边界，不把它误报成合法pending。合法registered／sent失败控制正常、额度不退。

**最低收口：**所有适用状态消费核已有枚举和合法来源；失败口只有registered／sent才允许正常failed，未知值结构化拒／unknown并保全，不能静默修成合法终态。专用“状态未知”理由码可选，不能以新增理由码替代行为拒绝；合法失败、显式retry、closed状态不重发、scripted网络0保持。不新增真实provider或外部exactly-once。

## 5. 四项登记残留及范围裁定

| 登记项 | 本审裁定 |
| --- | --- |
| 两事务间未持锁 | **P2范围披露，非另加P1。** R2确定性主动外部SQL破库证据保持；r3未改该事务模型，不重跑窗口。实际两个事务间有窗口；“顺序单消费者／合法不可变writer假设内没有并发插入方”不等于程序强制无窗口。继续明确不保证外部并发改库，不扩大到新分布式门 |
| defer保守拒未归因event | **接受。** 不能安全证明可退就不退；合法未执行释放保持，不认证一定执行过 |
| foreign-run请求不在本run pending扫描中披露 | **P2作用域边界，单凭此不阻塞。** 已按run过滤；同键重登记和状态口run绑定拒，claimed／open仍披露，未证明默发或错误verified。不可宣称跨run完整诊断；S3b实际caller消费前必须守卫，未来若扩反向清单按版本登记 |
| unknown request status无专门枚举码 | **不能按交付所称“仅缺错误名”接受。** sent／response已拒可不加专用码，但failed实际成功写，§4.3为原组P1。不要求新enum；修已存在的来源状态规则 |

交付另列claim幂等收据／停止报告未接行级守卫，不仅凭只读收据或计数缺增强另增门；done复用已接，原S3A-05披露正控保持。三组阻塞各有坏权威真实消费证据，非凭“可能还有入口”升级。

## 6. mimo v11 八条件及事实互证

provenance披露本轮一次只读输出、无断流；本审未调用模型。化学判据未冻结，以下精度项不成为S3a新化学代码门，也不替代§4工程证据。

| 汇总条件 | 本审裁定／落字要求 |
| --- | --- |
| ① CX保留token | 采纳更正：按真实token写 `a:`／`oN:`／`&N:`／`^N:`（及登记Sg类），不把and／or／rad英文类名当输入字面。RDKit2026.03.6实际写出ABS／AND／OR／自由基并严格身份往返保持；三字面别名均unregistered_cx_class拒。接受／拒绝不认证样品 |
| ② 系数句边界 | 采纳精化：非法表示系数在构造／提交拒；coefficient_binding_mismatch属于覆盖轴，partial_unchecked_transformation＋中心unknown，最终依首中规则。不可虚称入口在比对“系数与结构重推导值”；R2b还需caller映射detail |
| ③ 恒入／R2b | 改“覆盖判定完成full／partial分支必带license／scope”；unknown_coefficients／unverifiable早退不带。R2b调用方依赖落字，不把缺映射当化学已核；未来caller义务留S3b |
| ④ 中心partial与四串守卫 | 删裸partial，按映射理由码／中心unknown，与覆盖枚举分开；四原始串守卫限定执行成功路径解析前，失败早退未解析。None非通过 |
| ⑤ 入口划界 | 公共writer清单可补；搜索结构权威依公共writer重放，**verify_event_attachment_content只核附随内容，不单独证明state身份**。substrate_profile无生产caller，档案输出／未来caller前置验证划界为P2，不重开旧S0–S2门 |
| ⑥ known_absent轴归属 | 属条件评估轴非元素账；实体缺席／非物种字符串同值→conflict，异值／未列出→unknown，数值／区间缺席→numeric_absence_semantics_undefined unknown。保持已更正事实，不跨域泛化 |
| ⑦ 外包装／异常类 | **分两维澄清。** 同一入口canonical+r／真坏canonical内因均ChemicalStateError的不同kind；跨入口restore外层ChemicalStateError、writer外层Ppv1StateContractError确不同。v11“工厂未登记vs真解析是不同异常类”括注错误；读detail.reason.kind正确。不能改成所有外层都同一类 |
| ⑧ 执行证据 | 本审697、40／9、1299／8／17与276输入已独立验证；655c7e8非本轮父，未复跑其历史数字；RDKit往返另记。读码行号／版本与实际源码交叉核对，不能拿模型“已读”当执行 |

窄化学15案完整执行，加7个RDKit实际写出／字面别名控制；不与pytest相加，不冒充全部历史化学矩阵。r3五化学核心字节未改，mimo八条件主要为文字精度。

另须纠正回应的两种潜在扩大：**失败diagnostic三None／{}不等于下游audit所有轴／所有R行都不存在。** converter仍返回版本／来源元数据与center_match=None，缺scope／proof进audit中心UNKNOWN；同一次audit仍可以给其他轴verified并由决策表处置。其次，同源重放／输入守卫不证明来源真实性、历史执行、酶识别或供体机制。

## 7. 交付一致性及放行条件

交付数字697、1299／8／17、父40／9证成；红分类与9控制性质按§2精化。profile-11／search-3升版、store-9／limits-3保持已登记，runner未改，legacy code_identity与父同为 `4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c29ae`。store新增只读附随语义入口，无事件writer事务改变；合法共享、非事件outcome、幂等保持，未用全面拒绝换通过。

§1／§5的“最低验收闭合”仍需收缩到已验证的行级旧反例：**必要集合完整性、请求状态口策略、未知生命周期**尚未收口，必须修代码，不仅修文案。§7.4实行为与登记不同，明确更正。S3b未交付清单诚实，不因其未实现增加本批门。

**P1=[S3A-02,S3A-03,S3A-04]，本轮不放行S3b。** 下轮只修这三个明确入口／同源规则，保持已关01／05及本轮全部已证修复。科学性能pending、判据未冻结、S4／S5未启动均保持；不把工程通过当污染物路径可靠率或科学结论。

## 8. 下一轮有限回修提示词

你负责 **S3a-r4**，只在 `/Volumes/CC/Enzyme_Agent/dependingv43` 工作，基线 `41d0cd55f3def050a62325f00235cf22da302d2e`。先读AGENTS.md、本文§3–§7和新证据README、R2§4最低验收。**只继续原三组S3A-02／03／04；01／05及已证行级旧反例保持关闭，不实施S3b。**

先列本轮固定入口矩阵：必要预约集合在first complete／B4／B3事件前／B1／defer／done四口；冻结策略在register装配、已存读取／budget／claim／recover／请求新旧登记及sent／response／failed；请求状态在同键复用／sent／response／failed／recover。明确合法来源状态、必要资源条件、共享主体和验证来源，复用现成创建／验证规则。

1. **S3A-02：补必要集合完整性。** 现有逐行守卫保留。按现有claim／attempt创建规则验证所需预约集合不能少项，即使剩余清单非空也先拒。复跑本审9入口×3必要预约×仅删ref／删ref+row，尤其B3不得event0→1／commit1且总额度used0；firstcomplete／done不能漏结算或伪称verified。保全零新成功消费，不猜补缺行；合法共享alternative、条件适用reopen、非expand资源、非事件outcome、同hypothesis不同revision与幂等保持。无需新增独立来源证明／全库签名／机制库。
2. **S3A-03：请求状态首消费接冻结策略守卫。** sent／response／failed写状态前消费同一严格冻结块校验，null／缺version／四坏值先结构化拒且无成功状态变化。合法用户override只在装配补齐，存储消费不补默认；预算0不变10，无expected恢复保持。合法已登记请求不要重新扣额度；失败／悬空占额、scripted网络0／real0保持。
3. **S3A-04：非法来源状态不能改成合法failed。** 复用已有REQUEST_STATUSES与迁移规则，mark_failed仅合法registered／sent来源；unknown结构化拒／unknown并保全，不静默洗成failed。sent／response已拒保持，同键既有坏status与恢复披露按适用语义明确，不拿新增reason名代替行为拒绝。合法registered／sent→failed、终态不重发、显式retry、非expand空attempt保持。

只按本文已有公共链输入逐案从登记／claim走到消费／恢复，前后完整表、合法控制、实际错误和未执行内段实记。跨run pending扫描、主动外部SQL并发破库、生产caller和调度仍是已登记后续边界，不增加S3b／科学性能／冻结门；unknown／partial诚实保留，不全面拒绝。

新回归在直接父41d0cd5 detached隔离worktree跑同字节，分类行为拒绝／值断言／形态／kind先停／collection及保持控制，不改测试适配父。PPV1全量＋安全G01新白名单完整SHA与8缺席／17排除逐项披露，四硬杀／barrier／H07H08、旧R6／R7继承及01／05保持。数字若变按实际记，不锁697／1299，不外推dev／298性能。

交付按三个原组逐入口→行为→证据→红绿，更正r3未知status不会写的错误声明及§2数字精度。下一mimo自包含v12请求纳入本文§6八条件和事实澄清，真实token、异常外层／内因、失败diagnostic与下游audit分开；不新增化学判定，判据仍未冻结。实施agent不调用外模，主会话按既定通道送审。

证据新 `docs/review_evidence/ppv1_s3_impl_<实际日期>/s3a_r4/`，含脚本／完整合成输入输出／前后表／实际argv env exit耗时／HEAD schema／JUnit／输入SHA／manifest＋SHA（嵌套清单也覆盖）；所有执行新tmp，不改历史证据。仅必要PPV1改动和本轮测试／交付／请求／证据，语义版本按现规登记。v4.3本地提交git add显式路径，不纳入原AGENTS差异／旧未跟踪评审材料、不push；不访问真实金标／题面／封存run／dependingv4，不真实provider，判分零LLM。单实施agent串行，主会话核对→mimo→Codex复审。
