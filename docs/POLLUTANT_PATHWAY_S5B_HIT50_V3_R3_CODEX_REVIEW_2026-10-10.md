# PPV1 S5b HIT50 v3 回修 R3 正链有限复审（2026-10-10）

## 1. 正式裁定

**R3 通过；S5B-V3-02 清零，P1=[]。chain10 工程侧有条件放行：受权协调者完成 §7 六条既定发车步骤并封包后可发车，不再要求金额代码回修。** 当日价格、真实输入/计费输出上界、最终部署身份及新登记尚未由本审核实；因此本裁定不等于“当前旧登记可直接发车”或“真实批已获完成核验”。

| 编号裁定 | 正链结论 |
|---|---|
| 1：A′/C′ | A′：缺轴且 total 小于已知有效轴，实际保留原预约、第二发送先拒；合法总计/完整拆分/明确0保持。C′：已启用块 null/删键，实际首消费拒，已发金额转未结算且不假退款；真旧未启用保持。两项闭合。 |
| 2：残留处置 | 429 body 不读、total=0-only、坏块不猜 overrun、协同改写边界可随批披露；TPM、快照错误呈现及两处旧注释列 P2。当天金额配置与新代码/登记身份属于发车前必办，见 §5/§7。 |
| 3：chain10 | 程序阻塞已消除，六条清单可由已授权协调者执行。§9-④原文已在现有登记读回，但登记仍写 d084/旧价，须按 R3实际部署更新、读回并纳全文SHA；未完成不得凭本报告跳过硬门。 |
| 4：红线/继承 | 三冻结SHA父子/工作树相同；scorer匹配/排序、evaluation及既有47金额用例字节不变且控制通过。只改金额程序一文件，mimo本轮实际跳过可接受；不冒称已做化学评审。 |

实际 HEAD：`d24004533e5e3a48f9c4a35049fed20f1d227afa`；直接父：`d08432c6014ec476436df0b85765058e43464ffa`。验收面先固定为 R2主审报告 §4两残余最低收口、§5/§7/§8和本轮交付。不重开已闭合的429保守保留、S5B-V3-01、提交序、化学供给、S3/S4/ISO及历史launch，不要求全库防篡改或新的科学性能。

本审读取三个本地执行分支的实际输入、源码、原始输出、JUnit、业务快照和SHA封包，再独立重验关键观测与封包。全部是fresh tmp合成工程验证，真实模型调用/费用为0；不认证298目标命中率，不启动真实批。

## 2. 独立执行与数字边界

| 执行面 | 本审独立结果 | 范围/证据 |
|---|---|---|
| 定向15文件 | **283 passed，exit 0** | 258存量+25新案；r1/r2 cost 19+28零字节改动、47/47保持绿。 |
| 安全隔离G01 | **1947 passed / 10 skipped / 17 deselected，exit 0** | 327准入输入=326旧+1新增，恰1旧输入更新rate_gate；两套回归前后SHA零失配。缺席逐nodeid见附表。 |
| G01内PPV1子集 | **1344 passed / 2 skipped** | 未把缺席冻结docs测试或原v3/v4依赖计成通过；冻结完整性另以只读SHA对照闭合。 |
| 直接父+当前同字节r3_cost | **17 failed / 8 passed / 0 collection error** | 15行为红（A′4+C′11）+2拒绝kind红；无字段/版本红。子代25/25完整执行通过。逐nodeid/首个失败断言在 `execution/parent_red_green_classification.json`。 |
| A′公开client专项 | **19场景、38次complete、25次假发送**，另3次重复receipt | 16固定矩阵+3足额高帽正控；99既有输出核验+6高帽断言通过，未重跑前16案。 |
| C′公开恢复/worker专项 | **24入口形态+8worker**原矩阵；补充4worker；6旧合法断言+22额外断言通过；共9次假发送 | 原R2脚本逐字节复制fresh tmp；结算、重开、同进程装配、真legacy、worker冻结预算及完整429正控。 |

交付书及主会话 **1958 passed / 0 failed / 16 deselected** 是他方真实仓树全量执行声明，本审如实登记来源；本审不在真实仓树跑 `tests/` 全量，安全G01与其分开。定向/G01/PPV1子集有重叠，不能相加。专项共34次假传输（A25+C9），外部provider调用/真实费用为0；回归另有本机回环假提供者，不声称本机HTTP为0。

父红绿的两worker装配红，父已零发送拒绝，只是 `budget_guard_missing → budget_guard_invalid` 和检出入口变化，不能冒称两条新增放行漏洞。两个父worker重试在run_error文案断言先停，后续calls断言未执行；另存父gate实际 `total_requests=2`/首预约reserved，不把gate请求计数当独立urlopen遥测。原R2公开反例已有真实fake_calls=2，作为before只读复用。当前25新案完整通过，另本轮公开worker实测fake_calls=1，二者互证。

父子使用同根、同SHA的60个非仓输入（source-only v3及普通反应资产等），267仓侧输入分别核验。原v3评价资产、真实题面/金标、封存逐题run未复制或读取；大普通资产248,371,747字节只准入SHA钉住，不塞进永久包。两套隔离回归各观察到同7个子进程pyc例外，逐路径在 `execution/logs/{directed,g01}.post_sha.json`；证据包不含缓存或SQLite二进制，合成业务表保留JSON/SQL文本。

## 3. 共用判据与消费入口核验

| 入口/事实 | 实际源码 | 本审观察/裁定 |
|---|---|---|
| usage已知有效轴与总计下界 | `rate_gate.py:925-938`、`:950-967` | 轴缺席/坏值分开；total回退前核有效轴之和。坏轴不当下界；自矛盾返回None，由结算保留未知金额。 |
| 完整双轴优先 | `rate_gate.py:945-949` | 两轴有效含明确0精确结算，冗余total不参与；这是已认可的保持面，不重开。 |
| 既存金额账本 | `rate_gate.py:290-304` | 任一既有账本键为启用事实；不直接由当前guard块是否存在推“未启用”。 |
| 装配/运行中存在性 | `rate_gate.py:355-385`、`:435-448` | 共用账本判据；运行中再消费本进程已装配配置。重开装配直接用同源ledger判据，不夸大成所有入口逐字调用同一个方法。 |
| 摘要与发送首消费 | `rate_gate.py:560-565`、`:615-616`、`:1078-1084` | `_load`默认拒绝，先于槽位/金额预留；summary不再返回None洗成旧未启用，acquire在flock内重读。原派生bound/hash验证及规范对象消费保持。 |
| 已发回执结算 | `rate_gate.py:781`、`:854-876` | conserve档允许释放槽位/记冷却；已有reserved一次转unsettled，note机读，坏guard不补造、不结清、不退款。重复回执不重扣。 |
| 公开client | `llm_client.py:362`、`:394-401` | complete先summary，每次retry再acquire；坏配置结构化 `budget_config_invalid`，第二HTTP不到传输。文件本轮零改。 |
| 公开worker | `s5b_worker.py:106-117`、`:211-286` | 装配异常留失败case；独立冻结budget与摘要首消费兜底，零发送；runtime传输失败留题分母。文件本轮零改。 |
| 只读快照 | `rate_gate.py:1095-1098` | 消失的已启用块现在抛GateCorrupt，真legacy仍enabled=false；快照不充当金额完整性或发送证书。 |

既有发送前原子金额预留仍在同一flock内消费规范bound/cap，`rate_gate.py:627-678`；本轮修改没有拆开这个事务。旧双进程最后额度、孤儿仅退槽位、完整回执/未知保留/429有界重试由未改47用例及定向/G01保持，不重新要求后续分布式机制。

## 4. 两残余的逐案收口

### 4.1 A′：自矛盾total不再低额结清未知

复现R2原公开 `OpenAICompatibleClient.complete → gate` 案，cap=.00768、bound=.0064、入价.8/出价2.8、输入界1000/输出界2000，usage=`prompt_tokens=900,total_tokens=1`且缺输出轴：

- 第一次合法假发送仍返回内容；金额settled=0、unsettled=.0064，只有1条预约。
- 第二complete在发送前返回 `budget_cost_exhausted`；fake_calls=1、total_requests=1、reserved=0，未再退掉未知占额。
- 旧R2执行观察为2次发送、每次settled=.000003，已只读复用before，没有为凑翻转重复跑旧代码探针。

有效output轴下界同样闭合；坏output+有效prompt900+total1仍按已知prompt下界拒退。合法prompt900+total1900按max价=.00532、output1000+total1500=.0042、total恰等900=.00252、无轴total-only1900=.00532仍可结算（新回归另含3000=.0084）；900/1000完整拆分即使冗余total1仍=.00352，明确双0=0，单轴明确0配齐另一有效轴也合法。足额高帽三案各2次发送，证明不是把所有第二次调用都拒掉；原小帽合法高费案余额不足拒发是正确金额行为。

重复原预约回执3次，未知只记一次，不退款不重扣。收口范围是同一usage内部有效下界一致性，不是验证服务商账单真实性或补推未给出的拆分。**A′关闭。** 原始请求、usage、两response、每步余额/预约及source SHA在 `budget_a/current/`，正控在 `budget_a/high_cap_controls/`；主审13项读回断言另在 `root_audit/primary_proof_readback.json`。

### 4.2 C′：已启用块消失不再降成旧未启用

复现R2两个公开worker案，cap=.056326、bound=.046938。第一次合法HTTP429时**只**将cost_guard设null或删键，原金额账本/预约与批根budget_guard.json不动，各fresh执行：

- 两案均fake_calls=1、total_requests=1；恰1条原预约变unsettled=.046938、note=`cost_guard_block_missing_settlement_kept`，settled/reserved=0，send_rejections=0。
- 第二HTTP在acquire首消费被坏配置拒绝；不是余额拒绝，所以不假报send_rejections增加。guard原null/删键形态保全，批根机器配置字节SHA不变。
- 17业务表在第一次发送/fault点取真实前快照：其后仅endpoint_records+1、stop_reason_records+1，其余15表全部0，含events/search/工程budget_reservations。不能报“全部零写”，也不能把首次合法HTTP或预约抹掉。
- case仍终态completed，但run_error=`real_model_transport_failure`含 `budget_config_invalid`、endpoint执行failed；这是失败题保留分母，不用case标签证明化学/生产成功。

四入口6种坏形态共24观测：坏/缺bound/hash16维持适用的首消费拒绝/保守保留，整块null/删键8逐案翻转为首消费拒绝或结算保守保留；worker装配原坏派生反例保持先拒。新null/删键summary、acquire、重开均先拒，坏状态字节保全；结算允许保守记已发事实，重复回执幂等。相同金额策略、足额帽、guard完整的429公开worker仍可第二HTTP（2次假发送，第一未知=.046938、第二完整结算=.00352）。真正无guard无金额账本的旧null/删键legacy可发送、记账、summary None、重开，不凭全拒通过。

同进程即使guard+ledger一起删除，已装配事实仍令summary/acquire/verify_config/cost_snapshot拒。新进程guard+ledger全删，gate单看盘无法区分真实legacy；真实worker另有冻结budget，实测 `budget_guard_missing`/rc5/HTTP0。这是既定“不要求抵抗全库协同改写”证明边界，未承诺无独立启用事实的通用gate也能识别所有改写。**C′关闭，S5B-V3-02清零。** 证据 `budget_c/cases/`、`cases_supplement/`、`extra/`及合成runtime全表文本；主审直接读回金额、两形态及17表delta已通过。

## 5. 残留与交付精度裁定

| 项目 | 定级/处置 |
|---|---|
| 429 body不读 | 已闭合的保守选择，允许随批披露；含429无可核usage一律保留，不猜提供者未计费。未来退款口径另受审。 |
| TPM partial补0 | 速率统计P2不动；不能把它拿来退未知金额或声称费用已核。 |
| total=0-only | 保守过拒可披露，双轴明确0已证合法；本轮不要求扩大接受面。 |
| 坏块结算不猜overrun | cap不可核时可以不报overrun，已发金额必须保留且新发送拒。当前满足，不猜恢复配置。 |
| cost_snapshot抛GateCorrupt | 已实测的保守行为变化可披露；协调者遇此按坏配置停止/失败处理，不洗成disabled或完成证明。只读raw金额字段仍不充当完整性证书。 |
| total可信范围、两处活注释 | R3交付准确限定有效下界/坏轴合法total/完整双轴。源码`:918-921`仍可能被读成“任一坏字段必None”，`:548-550`旧注释仍笼统“块不存在即未启用”；正文新判据与执行正确，列P2文字同步，不构成本轮新阻塞。 |
| 账本/guard共同删且换新进程 | 既定协同改写边界可披露；公开真实worker冻结预算已核先拒，不扩大gate证明范围。 |
| 代码语义/版本 | budget-guard-1 schema/core/hash、orchestrator-2未变。代码行为按实际d240及新code_identity冻结，R1/R2旧账不迁移/重算或静默退款。 |
| R2交付两处订正 | 实际diff含2个【v3-R3】标记，公共52聚合算法和FREEZE_RECORD笔误如实纠正；旧主审报告/永久证据未回写。新登记用实测完整值。 |
| 当天价格、上下界、60帽 | **发车前必办**；价格须当日有效或可核保守上界，prompt输入与计费输出（含reasoning）确受所冻上限约束，机器配置SHA入身份。不得沿用未核旧低价并称上涨仍保守；本审不代定、不签已核。 |
| 交付取证过程 | 交付披露两次probe准备失败的旧raw被覆盖，只剩复述；不把复述当完整原日志。本审fresh独立原始输入/输出/exit补足本轮收口，不倒填实施缺失，证据保全习惯仍列P2。 |
| mimo本轮跳过 | 本轮仅金额程序语义，一源文件改动，无化学判据/诊断/冻结面；限定化学职责下实际跳过可接受。下一完整mimo请求携带本轮采纳注记，不能虚构本轮回应。 |

上述P2不作为新轮次门；当日配置/部署/登记是此前已定真实发车条件，不借P1清零豁免。

## 6. 构成、身份与红线

父d084→HEADd240只有4路径：`src/pathway_v43/adapters/rate_gate.py`、新 `tests/test_ppv1_s5b_hit50_v3r3_cost.py`、R2交付2订正、新R3交付。llm_client/worker/既有测试字节未动。11个继承生产源完整父子/工作树对照，包括evaluation、s5b_scoring、runflow、store、recorded_source、orchestrator、real_model、CLI、audit、endpoint、production；执行分支另核search、旧cost/scope文件不变。scorer匹配/排序零触碰、S5B-V3-01合法/坏输入控制保持。零字节变化不代替本轮公开新反例验证。

冻结三SHA在父、HEAD、工作树一致：

- 判据：`7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4`
- 冻结记录：`6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610`
- path_context：`971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d`

公开 `storage/run_identity.py:97-99` 排序k:v换行聚合，legacy52当前 **`279d9bc19bad25e51b7c23ee276da95151a8f25cf598b9dc3642b508d817c4bb`**，父 **`b0d4e9bc13935d17cfdd999717d8a99993fb6ea7bde4221c5770772cbd00a82e`**，恰rate_gate一项变化，与R3订正一致。这是实际行为代码身份变化，不声称整个legacy聚合不变，也不能把旧错误cd683值当新部署证书。

本审只读准入源码/docs/本地git对象与合成材料，没有访问真实题面/金标/封存逐题run/dependingv4/原v3评价资产，没有push/commit/外部模型/真实批；不审计或背书未经读取的历史远端行为。发布前后163固定输入及10,397份旧永久证据SHA/精确文件集、tracked diff、HEAD/工作树状态核对，审查者只新增本报告与本轮证据目录。

## 7. chain10六条执行映射与§9-④封包义务

**工程侧有条件放行；下列既定步骤的执行主体是受权协调者。** 金额程序P1不再阻塞，未执行的当天准备不能记已完成。本审不发真实请求。

| 既定清单 | 本轮执行映射与未确认面 |
|---|---|
| 1 新根/锁/实际身份 | 新批根、runs/gate/cases/ledger，单协调者/run锁；冻结最终部署d240、上述公共代码聚合、vendor/普通资产/protocol/prompt/池/融合/排序/profile/model/budget_guard SHA。旧根只读。旧d084登记不能充当R3身份。实际部署未由本审核。 |
| 2 298目标主列 | strict hit@1≥119/298为主列，hit@5≥150仅参考；旧116/128/130历史锚不改。seen298_post_hoc_repair_check/known_evidence_reconstruction；泛化pending、零dev/盲测外推。不承诺119命中。 |
| 3 参数与60元机器生效 | depth1/8备选/width2/1logical/format0/HTTP retries4（最多5次attempt）/40workers及40在途/RPM180/TPM2.7M/HTTP1490逐项冻结；原子预约+保守保留+完整性代码验收已过。**当日价格或可核保守价界、输入界/计费输出界、真实60配置装配与SHA发车前必办**，每付费attempt独立预约，预算耗尽不升帽、失败留分母。 |
| 4 当日题源/qid/配对全集 | 授权数据通道核当天题源SHA/298唯一qid/白名单；本审不读真实资产。scope及exact nonempty全qid_strict门保持。新登记插下文、读回、核代码/正负控、算全文SHA，与实际部署及金额配置封包。已有旧登记正文读回成立，但代码/价格/全封包未完成确认。 |
| 5 固定正式前缀10 | 同批同身份同298分母；只看完整性/成本，不看gold调参、不重采样。身份变动先停、新登记；旧身份批不能热换d240再当同一冻结批。未由本审执行。 |
| 6 全终态/封存/零LLM评分 | 298全留分母，unknown/失败/预算不豁免；终态及usage/未结算/账单对账、封包后判分。主/老/any-of/K联合表/U-H5-L/所有批与费用披露，评分零模型。未由本审执行。 |

**§9-④同步句原文（新登记沿用，不静默改旧冻结稿）：**

> 现行真实批配对采用整批二档；`data_scope=real` 时禁止根身份回退的守卫触发 ⇔ `manifest_qids` 与 `export_qids` 皆空。判分前须核注册图集合非空、`bases_by_graph` 键集精确覆盖注册图且值全为 `qid_strict`，任一缺失、额外键、坏类型或非 strict 即阻断。本门只核配对档位与覆盖，不核 qid↔图映射正确性，映射由评测器权威链负责。若配对档改为逐图混合，§9-④、evaluation-5 守卫与判分门须同步改为逐图判定，不得沿用整批判。

插入→读回完整正文→核当前 `evaluation.py:2316-2340`、`s5b_scoring.py:338-399` 及合法全strict通过/空缺foreign非strict拒的控制→算登记全文SHA，与金额config SHA、实际部署身份封包。值全strict且精确非空覆盖是**通过**，不沿用r29曾方向写反的“全strict阻断”。

### 7.1 现有发车登记的实际读回状态

本审只读 `docs/S5B_HIT50V3_RETEST_REGISTRATION_2026-10-10.md`，未访问其列出的远端/题源/批根。SHA仍为 **`125894776dc6c511660b687c702858a119d00bf659102877f30bcc876fa6c13f`**；§三引用去Markdown硬换行后与上文逐字符相同，**正文已插入且读回成立**，本审副本/结果纳 `root_audit/preflight_readback.json`。后续更新必须再次读回、重封全文。

该文仍引用d084、9月29价格并明示发车日未刷新，全文SHA“部署后回填”。“价上浮则实际美元当量低于60帽，保守方向”仍错误：按旧低价计算同一token金额，不能保证更高实际CNY费用≤60。**须在R3实际发车登记更新，核当日有效/可证保守价界、真实上下界、部署和配置SHA，封包后才能点火。** 已有发车门不改成新的代码P1。其ready/launched_pending状态是他方历史声明，实际是否已启动、旧批结果、远端代码和收费均未确认；本审不追认旧d084实际批为通过，不触碰/停改现场。

## 8. 后续有限范围与证据纪律

无需再开金额回修轮。协调者执行§7既定准备、更新实际部署与登记、读回/SHA封包、以同批固定前缀10校验链路后按既定授权继续；本审只提供工程放行，不替执行或代定当天数值。P2随下一小修/文稿同步，不要求实现V4/E、不改冻结/判分，不用本轮合成结果保证298性能。

本轮各已完成suite/探针只执行一次；前轮before输出只读复用，旧证据未重跑。无本轮账号额度中断；不把R2历史中断当R3事件。A分支首版审核断言误期望小帽下所有合法高费控制还可第二发，原exit1/stdout/stderr与summary保全；按真实余额重验既有输出99项通过，另补3高帽正控，未重跑原16案。C原补充脚本旧assert钉“第二次无预约仍发”，修后完整观察后按设计exit1，替代安全断言全真，不报产品回归失败。只读工具适配旧标记计数误差、准备路径误读均是取证工具事件，不是产品失败；实际失败/更正记录可追溯，未凑全绿。

永久入口：`docs/review_evidence/ppv1_v3r3_codex_2026-10-10/README.md`。含三子包及root_audit、脚本/输入/完整验证输出/argv/env/exit/JUnit/缺席/合成业务表、报告SHA、总manifest与SHA256SUMS；根仅排自己的两个控制文件，所有嵌套manifest/控制纳哈希。探针只复制fresh tmp重放，不在永久包原地建库；金额账本与工程budget表分开，字段红/拒因红/行为红、旧assert失败/产品失败、独立执行/他方声明分开登记。

## 附：安全G01缺席逐nodeid

10个skip来自实际observer，下面保留实际原因；冻结doc缺席以本轮独立SHA替代核验，不补读禁区。

| skipped nodeid | 实际缺席原因 |
|---|---|
| `tests/test_analog_assets.py::test_row_counts_match_v4_parser` | v4 对照代码根不可用:/private/tmp/ppv1_v3r3_execution.r8FIe3Ge/g01/dependingv4 |
| `tests/test_analog_v2_corpus.py::test_v2_selected_and_remapped_rows_decidable` | v2 provenance 未生成 |
| `tests/test_analog_v2_corpus.py::test_v2_line_level_one_to_one_and_duplicate_ids_recorded` | v2 summary 未生成 |
| `tests/test_batch_runner.py::test_input_manifest_whitelist_from_frozen_v3` | v3 冻结基准不可用 |
| `tests/test_ppv1_s5a_rework_r2.py::test_s5a_r2_contract_version_registration_and_frozen_integrity` | frozen criteria text not copied into allowlisted isolation trees (G01 boundary); byte integrity verified at the evidence level (shasum in review_evidence package) |
| `tests/test_ppv1_s5a_rework_r3.py::test_s5a_r3_contract_version_registration_and_frozen_integrity` | frozen criteria text not copied into allowlisted isolation trees (G01 boundary); byte integrity verified at the evidence level (shasum in review_evidence package) |
| `tests/test_score_report.py::test_frozen_evaluator_cli_really_runs_dev` | v3 冻结基准不可用 |
| `tests/test_score_report.py::test_evaluator_refusal_on_wrong_split` | v3 冻结基准不可用 |
| `tests/test_score_report.py::test_evaluator_refusal_on_missing_lines` | v3 冻结基准不可用 |
| `tests/test_score_report.py::test_diagnose_route_buckets` | v3 冻结基准不可用 |

17个deselected：16 slow + 1显式缺评测器出口；不记通过。

- `tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden`
- `tests/test_asset_root_isolation.py::test_engine_load_isolation_and_reinit`
- `tests/test_cli_workflow.py::test_real_run_inspect_resume_smoke`
- `tests/test_domain_identity.py::test_identity_parity_with_frozen_engine`
- `tests/test_engine_asset_parity.py::test_all_fixtures_parity`
- `tests/test_engine_asset_parity.py::test_parity_covers_required_categories`
- `tests/test_engine_asset_parity.py::test_arms_ran_on_expected_roots`
- `tests/test_engine_asset_parity.py::test_same_runtime_failure_on_valid_fixture_fails`
- `tests/test_engine_asset_parity.py::test_runtime_failure_in_one_arm_only_fails`
- `tests/test_engine_asset_parity.py::test_unparseable_passes_only_with_expected_error`
- `tests/test_engine_asset_parity.py::test_category_and_count_expectations_enforced_against_actual_candidates`
- `tests/test_engine_asset_parity.py::test_missing_fixtures_in_both_arms_fail`
- `tests/test_engine_asset_parity.py::test_duplicate_and_unexpected_result_names_fail`
- `tests/test_engine_asset_parity.py::test_real_comparison_reports_found_categories`
- `tests/test_finder_real.py::test_real_engine_catechol_recorded_evidences`
- `tests/test_prediction_real.py::test_real_catechol_rank_candidates_smoke`
- `tests/test_prediction_real.py::test_real_donor_recovery_attempt_recorded`
