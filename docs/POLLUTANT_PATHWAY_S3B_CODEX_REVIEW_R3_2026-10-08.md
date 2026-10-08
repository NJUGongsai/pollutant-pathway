# pollutant_pathway_v1：S3b 回修 r3 Codex 独立复审与 S3 工程交接

日期：2026-10-08（Asia/Shanghai）。实际 HEAD：`adf0287abef0c4803962fee0df0065d8e6f3793d`；直接父：`2bedfc060a9b19019ba44aa2a56dcacb88450c3b`。

**结论：S3b 通过，唯一残余 S3B-01 关闭，P1=[]。结合已通过的 S3a 与本轮全部继承控制，完整 S3 达到工程完成交接点。** 本结论不宣布判据冻结、污染物路径科学性能通过或 S4/S5 已实施。评审自动循环在此停点结束，后续交接由用户裁定。

永久证据入口：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3b_codex_r3_2026-10-08/README.md`。

## 1. 固定范围与执行来源

验收基线为 R2 复审报告 §4 唯一残余 S3B-01 的最低收口与 §7 放行条件，继承 S3 任务书 §3/§7、S3a R4 §8、原升级规格 §17。只裁定公开恢复首次消费前的冻结计划内容身份锚定，不提前要求机制库、现实来源认证、分布式锁、终点推断或科学性能。

本审读取 r3 交付书、mimo v15 只读回应及相关代码，程序数字用本审三个 fresh tmp 专项互证，不采纳交付自报或模型读码作为执行证明。源码副本含 vendor/metadata；禁字节码/pytest 缓存。原 R2 脚本与合成反例先复制，不在永久证据原地建库/运行；父基线为 detached sparse worktree。全部套件一次，无环境纠错、额度中断或行为重跑。观察器对两项请求数的错误期待仅从既有完整日志更正，raw 不抹去。

不访问真实金标/题面/封存逐题 run/dependingv4，不调用外部模型/真实 provider/网络，不做 LLM 判分、不 commit/push。本轮只新增本报告与本轮证据目录，不改 src/tests/既有 docs/AGENTS.md。根快照明确白名单 4554 个既存文件（含完整 R2 合成证据的 manifest 路径），记录实际 HEAD/父/git 差异及用户原工作树，发布时逐 SHA 保全。

## 2. 独立执行数字与红绿

| 本审执行集合 | 结果 | 证明范围 |
| --- | --- | --- |
| 当前 PPV1 全量 | **879 passed / 0 skipped / 0 failed，exit 0**；32文件，pytest26.19s/外层26.520921s | 871存量＋8新r3；新8从全量JUnit提取，未另跑当前焦点 |
| 父2bedfc0同字节新r3八项 | **5 failed / 3 passed，0 collection/版本/字段红**；pytest4.89s/外层5.183765s | 五个均 `DID NOT RAISE(PPV1RunError)`，public resume正常返回后的行为红；不把五红说成五漏洞组 |
| 安全隔离G01 | **1481 passed / 8 skipped / 17 deselected / 0 failed，exit 0**；pytest217.95s/外层219.866072s | 288白名单输入SHA前后一致；工程安全口径，缺席逐项下列 |
| 锚/恢复公共链专项 | 38顶层观察：36契约符合＋2 header-only P2边界 | 原B3/B4、11拒绝控制、四硬杀、并发、继承；不是38 pytest passed |
| 化学/交接补充 | 当前RDKit五正控＋三别名×两个入口六负控；九项公共消费控制 | 原子工具/审核/准入/提交、unknown/None/Audit异常及停止；不外推科学性能 |

父三绿为合法 B3 省略计划恢复幂等、显式同计划、原计划合法转换。五红尾部“拒后零变化/保全”断言在父没有执行，不能冒称父也跑完这些内部控制。本审仅读已完成父合成全表：B3/B4/显式同新计划/坏锚四案各 event1/commit5/transition1；缺锚案 event1/commit4/transition0，确认是行为缺拒，非缺字段红。当前8的拒后控制及下面公开探针另有完整证据。

G01 288输入＝228本仓白名单（源码/测试/配置/脚本/非题面资产）＋42普通v3/src＋18非题面资产镜像；源与副本SHA前后同值。8 skipped：真实冻结评价5（`test_batch_runner:52`，`test_score_report:110/163/172/184`），缺旧v4对照1（`test_analog_assets:95`），phase_d派生provenance/summary2（`test_analog_v2_corpus:62/153`）。17 deselected＝16 slow＋明确 `test_export_v3::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden`。完整nodeid/理由/白名单/输入tar及逐成员SHA在 execution 专项；不进入缺席依赖补数。历史1110…1473各轮保持历史标签，不混计。

环境：depending43，Python3.11.16/RDKit2026.03.6/SQLite3.53.4；runflow-3/frozen-plan-1，profile-14/search-6/store-9/search-limits-3/format-feedback-1/model-proposals-2。工程数字不代表 dev（B1环境路径中间步骤）或298（RHEA通用酶学）科学性能，也不是性能增长曲线。

## 3. S3B-01 完整收口证据

`runflow.py:274–390` 新增 `_verify_frozen_plan_binding`：读本run的retrieve数据库行，对含 plan_digest 的锚，复用 start 侧同一个 `decision_task_key`，按冻结行字段＋摘要重算并对照 task_key 列/载荷；再把锚摘要与读出的计划摘要对照。锚内容自身不一致/不可解析/非dict报 `frozen_plan_anchor_corrupt`；无必要锚报 `frozen_plan_anchor_missing`；计划内容与原锚不符报 `frozen_plan_binding_mismatch`。实际锚是start根retrieve，followup retrieve没有plan_digest；不是用artifact里的自hash再自证。

公开resume `runflow.py:1514–1522` **先锚核对，后 recover_run**；因此root retrieve已done的B3/B4仍核，不依赖它重执行。原显式plan比对、H07加载、执行层二次plan/pool核验保持。start `:1395–1416` 用同源计划派生artifact/root任务；“同一次正常调用同源”不扩大为抗外部协同改写承诺。

| 原/附加输入 | 本轮实际公共链 | 裁定 |
| --- | --- | --- |
| R2 B3已写bundle，只改计划artifact并重算自身hash；省略plan | root done，binding_mismatch；业务十五表相等，event0/commit2不增，改文件字节保全 | B3 bundle消费/事件提交之前拒 |
| R2 B4已提交event，同样自洽新包；省略plan | root done，binding_mismatch；业务十五表相等，event1/commit2不增，无新转换 | B4补账/consume/后续调度之前拒 |
| 自洽新包＋显式传入同新计划、已全部done后新包 | 同一锚规则拒，不因传入==artifact或队列已完成授新输入 | 后段各消费面闭合 |
| 根锚删除/plan_digest缺、坏digest/task_key列或载荷/非法载荷等11附加拒绝控制 | missing/corrupt/mismatch三kind俱全；instrument recover_run/drive/真工具进入均0；十五表相等、原artifact保全 | 不是拒后已写/只尾部断言 |
| 合法同计划/省略/显式同计划、原计划转换/重复 | 正常完成，恢复不重数；新summary披露frozen_plan_binding/task_key_verified/原锚 | 保留合法，不以全拒换通过 |

两原反例原摘要 `880bf6c37d09af15db7a82ad19cfd9aa4b4d1d52eab0efe256e8dd08babdeb94`、新artifact摘要 `7164d4f966b107f19544e5e0a0cac7a4a80ce22e7f289f24a5ebc8c7fe3acd04` 与R2完全相同；仅新run根/源码/版本更新。完整旧新信封、public输入、进程命令/输出、十五表快照及文件SHA和保全哈希在 anchor 专项，不以旧硬编码HEAD冒充当前。解码后的十五表同值与SQLite二进制SHA分开；本包未另算canonical表摘要，不能将文件SHA称为该指标，未采到的before binary值不倒补。

**关闭S3B-01，P1=[]。** 已定的“版本/身份”在本门指当前run/profile/code与实际计划内容/task绑定；下面的未解释header不当作全wrapper版本认证。本轮没有新的不同计划内容被旧锚接纳，亦无错误verified/R6或必要unknown丢失的证据。

## 4. 已关闭组与化学/legacy不回退

S3B-02坏bundle保持blocked、零坏任务重执行/事件，坏event或reservation权威公开先拒；合法独立任务继续。S3B-03转换正常及四窗口恢复phase-1，三产物2→3补全、重复零新增、旧边历史冻结。S3B-04两个真实workflow.runner.resume_run进程barrier：败者在胜者GO前driver_session_active，实际工具入口1、原attempt/预约保持；不只看最终event幂等。B1/B3/B4合法event1/commit4各保持，B2请求1/网络0/不默发保持，不能把四边界写成同一计数。

S3B-05空/非空novel形成独立hypothesis/真实工具→audit→admission→event1/2；空池档案/合法弃权保持、网络0。两项本审novel observer期待请求恰1过窄，实际3/2含合法产物后续decide请求；原raw保留，按完整输出更正≥1，未重跑。S3B-06原depth0停止主因budget_limit正确、depth_limit其他原因与持久blocked对象/repeat不丢不重数。E01/E02、C06的unknown有界公共探索、H04循环initial_supply、条件冲突/分支隔离、runner分流和全部S3a旧回归保持。不声称历轮每份永久探针又跑了一遍。

source相对父只有runflow消费守卫/版本与profile登记注释变化，新测试一个，**31份既有PPV1测试文件及两份worker字节零改，871存量用例保持通过**。production.py当前/父 SHA同 **`3b1a66ea2bc3aa37f7caaa2ed1a7f5395cda5901ef2a03d765b932ee5b082262`**；12共享核心同父（原九加search/queue/model_protocol），52份legacy代码同字节，聚合仍 **`18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6`**。冻结G2/AtomTool不改；PPV1旧run不跨版本原地迁移。

本轮真实caller坏proof经真工具/audit抛AuditContractError，窄捕获contract_aborted/failed、零event；无吞成verified/R6/成功。正常unknown/conditional控制与三None/执行失败audit前短路依赖不变化学模块/全量与既有证据保持，证据不足不改成通过。当前RDKit实际写出plain/ABS/AND/OR/自由基五合法样例并 strict/state.from_dict往返保真；and/or/rad三个字面别名在factory与strict两入口各拒，记录真实CX token及当前版本。仅验证本机RDKit2026.03.6，非跨版本兼容/酶学机制认证。

## 5. 交付一致性、残留P2与许可范围

879/5+3/1481/8/17/288、production/legacy不变与入口时序独立证成。交付15/15属于交付方取证，本审38观察及九项消费控制分别登记；不拿自报数字代独立验证。实施时证据HEAD=2bedfc0＋dirty有采集时序，最终受审HEAD为adf0287，不能混称。拒绝路径driver.lock披露文本可被持锁方重写，“零变化”指十五业务表及被改输入保全，不说全目录无写。

| P2/范围 | 本轮裁定及交接说明 |
| --- | --- |
| plan_version header未解释 | 只改未知/删除payload.plan_version、重算外包装，但plan与根锚完全不变的两个公共B3控制仍消费原bundle，无新内容/转换/工具重执行。loader只取plan，未解释此header；**不宣称已拒未知/缺header，也不认证未来schema**。列metadata规范/校验P2；不是原“不同计划内容沿旧身份”的残余，不凭未来格式假设增加阻塞。正式schema演进前明确该字段约束或补校验 |
| 协同改写/第二核 | DB锚与文件artifact为不同通道、同一run存储环境，不抗同时一致改写全部权威；无密码学真实性服务。入口正常核过后执行层第二核是纵深防御，未认证运行期外部SQL全部窗口 |
| 锁/预算夹具 | 同机flock，不认证分布式/external exactly-once；锁文本仅披露。三产物probe总预算30（原20）给余量，化学/硬杀规则保持，不说完整输入字节同原 |
| novel源标签 | decide model source_refs、expand默认synthetic-pool-spec，event appearance后者；state_id/hypID不因此变化，action proposal_context/冻结响应保留可追溯，未认证现实来源/逐字一致。冻结前同步文字/来源一致性设计，仍P2 |
| 旧注释/异常包装 | audit2980–2981“至少unknown”须同步现行前置绑定通过后strictFalse→violated/R5v；None→unknown。三个RuntimeError可原样逃逸，不能把Audit失败结算外推所有异常；unused旧appearance并未被认证 |
| 既定底座P2 | cache_hit同构、两事务间外部SQL窗口、foreign-run反向诊断、保守defer、scripted请求登记生命周期及stop对象列有界100保留。不要求本轮全库扫描/机制或provider新门 |
| 科学/收费/真实资料 | 合成规则池不认证检索质量；工程pending边界不外推dev/298；真实provider默认off，科学pending、判据未冻结 |

## 6. mimo v15 冻结改字与执行取证清单

mimo只读意见采信到源码/程序互证为止；原回应和请求不回写。本轮允许工程交接，**下列文字未在本审授权范围内修改，判据仍不可自动宣布冻结**。

| mimo §十二项 | 同步要求/本审互证 |
| --- | --- |
| 1 substrate_profile“无生产caller”过时 | 改为已接生产decide只读档案；runflow809/812–814实际调用/写artifact，不让其证明结构或当审核证书 |
| 2 R3“action=blocked”错误 | 化学admission的defer与持久search_actions.blocked分开：实际admission_deferred结算/假设保留，action可done，未写blocked；runflow1122–1133/audit1528–1529/1757与公共冲突控制互证。改文字，不改行为去迎合误句 |
| 3 reconcile/drive旧区间 | r3 plan persist/load229–272、anchor274–390、锁392后；reconcile500、ensure_transition_followup577，旧209–226/304–321不再是reconcile/drive |
| 4 窄捕获旧行号 | r3 Audit窄捕获1091–1102；955–972仅r2历史，标版本或更新当前锚。静态无宽捕获不是任意第三方caller动态安全证书 |
| 5 “恒入center detail”全路径歧义 | 完成覆盖判定的detail必带license/scope（full/partial），889–897早退不带；1009–1013有字段≠已适用。full只解除覆盖轴，不认证机理/生物可行性/来源 |
| 6 λ_s×Δ区间 | 源式973–980；系数绑定和补全账分开，声明清单账平不认证漏项/电子/质子实际计量 |
| 7 数字/HEAD/字节一致采信 | 模型无执行权限，原声明继续“待执行验证”；新冻结包可标“由本报告/独立日志证成”，不得改原回应成模型已跑。工程数字不当化学证据 |

mimo待执行五类：①当前879及父新八项5/3本审已执行（当前新8在全量内）；②G01已执行；③本机RDKit词法/往返与别名负控已执行；④production/legacy字节/身份已核；⑤novel source_refs两侧行号已补读及实际appearance互证。不重复历史R2全量/父红：mimo §十.1把R2历史20的父写成2bedfc0不准确，历史R2正确父为c1211183，直接引用R2永久JUnit/分类；本轮新r3八项的父才是2bedfc0。

冻结前同时同步判据五两句：standalone audit被调用时可分轴判定；固定生产链execution_ok=False在production399–404于audit前method_failed、零audit/event。strictFalse→violated须带绑定/覆盖先行分支范围，不能无条件全称。given facts satisfied/conflict不认证环境事实，旁证不叠加升格，unknown/partial不授R6；本轮不改变判据一–五科学边界。

依mimo v15，可先完成上述纯文案更正与证据引用，若不改变已审正文语义则无需新增化学评审轮次；若改字实际改变判据正文/范围/硬门，应按仓库已有化学评审与版本规范另评。最终冻结权归用户/teacher，不归本报告自动执行。

## 7. S3工程完成交接与下一阶段路线

**S3通过，P1=[]，无需S3b-r4回修提示词。** 把本报告、r3交付、mimo v15、三专项证据和版本清单作为S3交接包；保留旧轮次历史只读，不把“通过”改写为污染物路径已科学确证。常设回修循环到达AGENTS指定S3交接停点，在此交回用户，不自动进入S4/S5/判据冻结。

建议交接顺序：

1. 做冻结稿的纯文案同步：§6七项＋§5旧注释/元数据/来源标签许可范围，附当前源码与独立证据；正文/门禁无语义变化时按mimo v15不必再拉一轮化学意见。用户/teacher确认判据版本、proof_scope、术语及未核事项；工程完成与冻结状态分开记录。
2. 用户另行启动S4任务书：按规格§10/§11/§17做endpoint分账、路径原生导出、v3有损适配、端到端scripted验收。保留不同来路、共同产物/备选、条件/依赖、audit、未展开/暂缓集合及预算停止原因；停止不当终点，账平不当矿化，不把备选CO₂相加，不自动推解毒；F01停止非终点、F02未知依赖不被recorded洗白、F03不同来路/重复来源不增独立支持；G02导出确定性与过期可识别，旧legacy导出冻结不改。
3. S5数据/科学验收规格可按规格与S4并行设计，但不在本审实施：参考图/schema、研究来源分组留出、防泄漏、阈值/样本量/统计预注册，判分零LLM；真实题面/金标/封存结果/模型费用另循明确授权。没有独立路径数据时可review工程评测接口，科学性能保持pending；dev/298及检索支持/未见推演轨道分别报告，不用当前工程绿数倒推科学通过线。

交接方须继续消费恢复/ledger首消费守卫，put_state返回不当证书；保留失败None/unknown/partial与合法条件控制，旧run不跨版本续跑，新批实验新根。P2登记不能省略也不自动扩成下一阶段全部前置门；后续若出现原契约具体高风险公共反证，按AGENTS单列、只停受影响部分。本轮无源码实施、外模或跨阶段动作。
