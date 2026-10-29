# PPV1 S5b HIT50 v3 回修 R2 正链有限复审（2026-10-10）

## 1. 正式裁定

**R2 不通过，chain10 不放行；P1=[S5B-V3-02]。** 没有新增阻塞编号：原 usage 完整性规则还有“自矛盾总计被信任”的残余，原存储冻结块首消费规则还有“整块缺失被降成旧未启用分支”的残余。无 usage 的 429 保守保留已经收口。S5B-V3-01、提交序、化学供给、S3/S4/ISO 和历史 launch 保持关闭。

| 编号裁定 | 正链结论 |
|---|---|
| 1：三残余 | A：prompt-only/output-only 原案已翻转，但缺轴且 total 小于已知轴仍被低额结算，未完全闭合。B：429 无计费依据不退、槽位/冷却/有界重试保持，闭合。C：坏/缺派生 bound/hash 原案已翻转，但运行中整块 null/删除仍绕过预留，未完全闭合。 |
| 2：交付残留处置 | 429 body 不读、total=0-only 保留、坏块不推断 overrun 可以随批披露；TPM 补零和 raw snapshot 列 P2；当日价格/上下界/60帽配置和实际代码身份必须发车前冻结。具体见 §5。 |
| 3：chain10 | 当前不发车。§7 六条清单及 §9-④ 原文义务继续有效，第3条金额机器生效仍受原 P1 阻塞；其余当日步骤未由本审执行，不签已完成。 |
| 4：红线 | 三冻结 SHA 父子/工作树一致；evaluation/scoring 全文件逐字节不变，匹配/排序/配对守卫未改。三处源码改动均为程序金额语义，mimo 跳过与其限定职责相符；不冒称本轮已做化学评审。 |

实际 HEAD：`d08432c6014ec476436df0b85765058e43464ffa`；直接父：`b502b75c267842caa109ec8bb6735b5a0555584a`。本轮红绿使用这个直接父；它和 fecb 的金额行为相同，不沿用上一轮 0c6 红绿基线。读取范围先固定为 R1 报告 §4.2–4.4/§7/§8 与 R2 交付。两个新反例均对应原“合法可核总计才能退未知”和“存储冻结配置错/缺先拒”的最低要求；不要求新阶段防篡改体系或真实服务商账单证明。

本审由主审读取三个本地执行分支的源码、原始输入输出与封包后形成裁定。全部为 fresh tmp 合成工程验证，真实模型调用/费用为0，不认证 298 科学目标或泛化能力。

## 2. 独立执行及数字边界

| 执行面 | 独立结果 | 范围与分类 |
|---|---|---|
| 定向14文件 | **258 passed，exit 0** | 包含 scope/basis、金额、runtime/pairing/提交序及 rate_gate/prediction_task；不与 G01 相加。 |
| 安全隔离 G01 | **1922 passed / 10 skipped / 17 deselected，exit 0** | 326准入输入前后零SHA失配；相对R1真实b502集合仅4变化+1新增，27缺席逐nodeid见附表。 |
| G01 内 PPV1 子集 | **1319 passed / 2 skipped** | 隔离冻结 docs 缺席由 SHA 只读审计补核，不冒称 unrestricted 全量。 |
| 直接父两 cost 文件、当前同字节测试 | **1 failed / 18 passed / 1 collection error** | 唯一红为 429 原退款→保守保留行为翻转；新 verifier 在父缺席，R2 28案未执行。0字段/拒绝 kind/拒因顺序红。当前两文件47绿包含在定向258。 |
| 原预算反例/控制 | 原client10场景/20次complete/8假发送；补资产后原worker4场景/7次worker/4假发送；barrier1假发送；新21场景/28次complete+10次worker/30假发送，合计43假发送 | 原脚本逐字节复制，旧缺口断言因修复失败与新安全断言分开；不能把旧 assert 非零退出误报回归失败。 |
| C首消费专项 | 四入口24形态+8worker=32原矩阵，另4公共worker补充/6合法控制断言，合计11假发送 | 错/缺派生字段、整块缺失四入口及公开 worker，对照合法 builder/恢复/旧未启用/结算幂等。安全反例断言按真实漏洞失败，不凑全绿。 |

交付及主会话“1933 passed / 0 failed / 16 deselected”为他方真实仓树全量声明，本审登记来源；本审没有在真实仓树跑 `tests/` 全量，独立安全口径与其分开。父模块 collection 的28案不能写28行为红；父1红也不能证明全部新规则有效，收口依赖旧反例和合法公开链控制。

本轮合计54次专项假传输（A/B43+C11），外部provider调用/真实费用为0；定向/G01另含本机回环假提供者，不声称本机HTTP为0。数字不相加成科学样本。7个G01隔离子进程pyc例外逐路径在 execution/logs/g01.post_sha.json，包不含缓存/数据库二进制。

## 3. 已闭合部分与继承

`rate_gate.py:787-800` 区分轴缺席、显式有效（包括0）、显式无效；`:807-819` 完整双轴按冻结各自单价，合法 total-only 按较贵单价。原 prompt-only/output-only 不再补0；公开 worker 第一题未知金额保留，第二题预算终态留分母。完整双轴、显式0输入/输出/双0、合法总计、低费用、重复回执正控保持，不以全面拒绝换通过。

`rate_gate.py:717-733` 无可计 usage 一律 unsettled，删除429退款分支；`llm_client.py:423-447` 不读错误体，含 body usage 的429也不归零，`:394-401` 每次 retry 再 acquire。有余额可在有界退避下重试，无余额先拒；slots/cooldown/HTTP计数保留。实际证明的是“无依据不退款”，不是已核服务商收费政策。**残余 B 关闭。**

`verify_stored_cost_guard:217-267` 对已有 bound/hash 同源重算；装配 `:357-369`、摘要 `:920-932`、发送 `:539-554`、结算 `:694-712` 已消费同源规范对象。原 worker bound=.046938、cap=.001、stored bound=.000001 案在装配即 `budget_guard_invalid/stored_derived_mismatch`，rc=5、零发送/零预约，坏块保全；错误 hash、两派生字段缺席原案拒。`s5b_worker.py:106-119` 捕获装配期 GateCorrupt 留失败 case。结算期字段坏时旧预约 .046938 转 unsettled，原始坏块未洗；这部分正确。

既有 flock 原子预约、双进程最后额度、孤儿只退槽位及完整结算幂等保持。S5B-V3-01 由未改 evaluation/scoring 字节及定向/G01 控制守门，不复跑上一轮全部50观测，也不重开历史组。继承闭合不是对所有未测试输入的背书。

## 4. 唯一 P1 S5B-V3-02 的实际残余

### 4.1 A：自矛盾 total 被当“合法可核总计”

独立公开 `OpenAICompatibleClient.complete → FileRateGate.record_response` 合成案：

- 配置 cap=.00768、单次 bound=.0064、入价 .8/出价2.8 CNY/Mtoken、输入界1000、输出界2000。
- 同一响应给 `prompt_tokens=900, total_tokens=1`，缺 completion 轴；两次 logical complete，均有实际合成响应内容。
- 实际两次假传输均成功；每次 settled=.000003，累计=.000006，unsettled=0，两次均退掉预约。仅已披露900输入轴按入价已是 .00072，“总计1”与该轴自矛盾。

根因 `rate_gate.py:812-815` 只核 total 数值有效且>0，未核其是否至少覆盖同一 usage 的已知有效轴。**缺轴分支不可以靠一个内部不可能的总计把未知费用低额结清。** 对应 R1 §4.2“合法可核总计”及“不退可能已付未知”的既有最低要求，仍是原 A，不新增金额证明体系。

最低收口：总计回退分支消费前核已知有效轴下界，内部矛盾就 unknown 保留预约；不通过取已知单轴费用退其余来掩盖未知。无轴 total-only>0、兼容已知轴的 total、完整拆分/明确0保持。完整900/1000双轴加一个矛盾冗余total1实际仍结算 .00352，本审如实保留该控制：它没有发生本案的缺输出低额结清，不要求全面拒绝冗余字段来通过本轮。

证据：`budget_ab/extended/incomplete_contradictory_total/input_output.json`，含两响应、请求体、预约/结算、余额与原始 usage；完整双轴对照在同目录 `complete_contradictory_total/`。未调用实际provider，不能把这组数值称真实账单或真实超支。

### 4.2 C：已启用金额帽的整块缺失被当 legacy 未启用

公开 worker 合成端到端，不只 helper：第一合法发送时 fake provider 返回429，同时仅将 `cost_guard` 整块设 null 或删键，**原 cost 账本/预约及批根 budget_guard.json 均不改**。两形态分别 fresh 执行：

- 原 cap=.056326、bound=.046938。第一次合法预约在破坏前发生；未知占额保留后再加一次 bound 应超过帽。
- 实际第二次假 urlopen 仍发生，worker rc=0、case status=completed；`total_requests=2`，金额 reservations 只有1条，reserved=.046938，settled/unsettled均0。
- 即**破坏之后新增1次发送、0条金额预约**。不是“所有表零写”；已有第一次发送/预约不能抹去。null/删键的坏形态还在盘，未被覆盖修复。

根因：`_load:460-463`、`_init_state:357-359`、`cost_guard_summary:922-924`、`acquire:539-541`、`record_response:686-687` 都由 raw块当前是否非None决定“启用”。新 verifier 对整块None的拒绝永远到不了这些分支；即使对象早已启用、原账本还在，当前块消失也降为旧 dev 分支。首次 worker 装配前整块缺失会被 `_verify_budget_guard` 拒，**不能据此扩大成运行中每次发送都已闭合**；公开429重试把范围差展示出来。

对应 R1 §4.4“存储/恢复冻结块错/缺首消费拒、实际临界区同一合法对象”和§7机器金额帽，仍是原 C。未改 cap/core/hash协同伪造，也不要求抵抗全库协同改写。

最低收口：根据既有启用事实（已装配/构造配置、既存金额账本、worker冻结预算等适用事实）区分“合法旧未启用”与“已启用块消失/置空”；四入口共同验证，发送先结构化拒/零新发送与预约、坏形态保全；已经发出的预约继续保守保留，不能删除账本或假退款。真正无 guard、无金额账本的旧分支保持合法。


补充公共链在第一次发送/fault注入点有真实逐表快照：两坏形态其后均 events+2、hypotheses+2、states+2、appearances+3、projections+2、event_appearance_links+4、search_actions+4、search_attempts+2、search_commit_records+3、工程budget_reservations+6、expansion_plans+2、endpoint/stop各+1；meta/model_requests/provenance/search_runs均0。这里工程预算表与HTTP金额reservation是不同账，不能把工程+6当金额已预留。未改守卫的429对照只有1次发送，unsettled=.046938、send_rejections=1、events0，但终态case也写completed并有endpoint失败；故本审不用case标签单独证明成功。合法200控制没有初始表快照，只采final counts，不把零基线计算冒充实测delta；详见 `budget_c/summary.json`。

证据：`budget_c/cases/worker_retry_block_null.json` / `worker_retry_block_deleted.json`，含原配置、破坏时状态、两次请求、case与最终账本；`checks.json` 的阻断第二发送断言为false。原坏派生值的单案与合法旧分支控制另列，不能因这个新坏形态否认原修复。

## 5. 残留清单、文稿与身份精度

| 残留/精度项 | 裁定与处置 |
|---|---|
| 不读429 body | 本次保守选择合法，不作为发车阻塞。以后读/退款要同源 usage 完整性或可核未计费依据，单独受审。 |
| TPM partial `or0` | 速率记账面未改，P2披露。本轮不以它要求改RPM/TPM；坏类型令尾部记账异常时金额仍在reserved，不称成功结算。 |
| total=0-only | 未知全额保留属保守过拒，可随批披露；完整双轴0须保持合法。 |
| 结算坏块不做overrun | cap不可核时不猜overrun可以接受；已付/预约账本和未知占额须保留、新发送拒绝。本轮整块缺失新增发送漏洞由§4.2单列，不能借该残留豁免。 |
| raw cost_snapshot | 只读披露不当发送/结算证书。当前块空会披露enabled=false，不能据此签“旧未启用”；修复C后协调者也不把raw摘要当完整性证明。 |
| 当日60/价/输入界/输出界 | **发车前必办**。CLI60/30000/8192是默认而非核到的真实上界。尤其计费输出含reasoning是否受该max_tokens约束、每个prompt输入界，当日受权协调者核，不代定或声称已核。 |
| usage坏轴+合法total的文字 | P2精度：源码可走total分支，“所有坏字段必None”表述过宽；本轮真正阻塞是total与已知轴自矛盾，二者分开。 |
| R1交付四处订正 | 已读git diff和4标记，原口径错误及新语义明确可追溯，旧主审/永久证据未回写。 |
| 冻结记录SHA文字笔误 | R2交付写 `…fea1a6e7…`，实际为 `…fea1b6e7…`，见§6全值。P2复制错误，冻结文件没有改。下一交付/新登记用实测完整值，不改旧审核快照。 |
| legacy52聚合不相容 | 52逐文件SHA与交付完全相同，但公开 `storage/run_identity.py:97-99` 的排序k:v换行聚合实际为 `b0d4e9bc13935d17cfdd999717d8a99993fb6ea7bde4221c5770772cbd00a82e`，父为 `e4b934e9d83affbb3d5a7449d6227523c575509bd4b0b97c30091e09e669a9b0`；仅两个adapter字节变。交付 `cd683e…` 聚合算法未确认、与公开函数不相容，不能当部署身份。P2文稿错误，**新发车登记必须用实际公开聚合**；后续修复须再算，勿沿用本次值。 |
| 语义/版本与mimo跳过 | budget-guard-1核心结构/派生SHA算法、orchestrator-2不变；修复后的代码行为必须以实际新代码身份、新批登记，不能回写R1旧429退款记录。本轮纯程序修复跳过化学mimo可接受；R2交付末尾仍写mimo流程模板，实际未执行，下一完整请求携带采纳注记。 |

## 6. 构成与红线

d08432c 相对直接父共7文件：3源 `{adapters/rate_gate,llm_client; pollutant/s5b_worker}.py`、旧cost测试改写/新cost测试、R1交付四处订正/新R2交付。没有化学判据、scorer匹配/排序/提交序改动。本审11个继承源文件完整逐字节父子/工作树对照，其中 evaluation/scoring/runflow/store/recorded_source/audit/endpoint/production/编排器等保持；零触碰不代替§4新的同契约证据。

冻结三完整SHA在父b502、HEADd084与工作树一致：

- 判据：`7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4`
- 冻结记录：`6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610`
- path_context：`971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d`

实际只读git/准入源码、文档及合成输入；没有取真实题面/金标/封存逐题run/dependingv4/原v3评价资产，没有push/commit/外部模型或启动真实批。历史远端行为/真实账单不是本轮完整审计，不作绝对背书。审核发布前后固定输入与8527份旧证据hash/文件集、tracked diff及工作树状态核对，本审只新增本报告和本轮永久证据；途中主会话另加发车登记的外部状态差异单列，不冒称整个共享工作区只有两项变化。

## 7. 六条发车映射及§9-④义务

当前**不放行**；下表是修复后受权协调者的执行映射，不代表本审已做真实准备。

| 六条清单 | 映射/状态 |
|---|---|
| 1 新根、锁和完整身份 | 新登记引用最终修复HEAD与实际公开code_identity、vendor/资产/protocol/prompt/池/融合/排序/profile/模型/金额配置SHA；coord/run锁，旧根只读。d084及交付错误聚合不能当后续修复实际身份。 |
| 2 298目标主列 | strict hit@1≥119/298，H5≥150仅参考；旧116/128/130历史锚保留。seen298_post_hoc_repair_check / known_evidence_reconstruction，泛化pending，零dev外推。 |
| 3 参数与金额机器生效 | depth1/8备选/width2/1logical/format0/retries4/40workers与40在途/RPM180/TPM2.7M/HTTP1490/60CNY分别冻结；每付费HTTP attempt先预约。**§4A/C阻塞**。闭合后再核当日价与真实输入/计费输出界，configSHA入身份。 |
| 4 当日题源、qid与配对全集 | 受权数据通道核当日SHA/298唯一qid/白名单隔离。本审不读真实资产。scope/basis既有门保持；途中新增登记已经插入下面原文，本审去除Markdown引用硬换行后读回逐字符相同；源码/合法与坏形态方向也一致。当前文档SHA纳本审证据，但部署config/完整发车封包与真实资产未核。 |
| 5 固定正式前缀10 | 同新批/身份/298分母，只看运行完整性和费用，不看gold调参、不重采样；身份变则停批新登记。未执行。 |
| 6 全终态、封存与零LLM评分 | 298全留分母，unknown/失败/预算不豁免。usage/未知占额/账单对账后封存；主/老/any-of/K联合表/U-H5-L/所有批与费用披露，零模型判分。未执行，不承诺119命中。 |

**§9-④新登记待插原文（沿R1 §7，不静默改旧冻结稿）：**

> 现行真实批配对采用整批二档；`data_scope=real` 时禁止根身份回退的守卫触发 ⇔ `manifest_qids` 与 `export_qids` 皆空。判分前须核注册图集合非空、`bases_by_graph` 键集精确覆盖注册图且值全为 `qid_strict`，任一缺失、额外键、坏类型或非 strict 即阻断。本门只核配对档位与覆盖，不核 qid↔图映射正确性，映射由评测器权威链负责。若配对档改为逐图混合，§9-④、evaluation-5 守卫与判分门须同步改为逐图判定，不得沿用整批判。

受权协调者在**新登记**插原文→读回确认完整文本→核 `evaluation.py:2316-2340` / `s5b_scoring.py:338-399` 及合法全strict通过/空缺foreign非strict拒的证据→算登记全文SHA，连金额config SHA/实际部署代码身份封包。本次新增登记的条款正文已读回，见下述状态；没有登记实际读回记录/部署SHA封包者仍不签“全执行完成”。也不把r29方向写反的“全strict阻断”沿用。

### 7.1 封包期间新增登记的实际状态

发布前guard发现主会话新建 `docs/S5B_HIT50V3_RETEST_REGISTRATION_2026-10-10.md`，不在初始snapshot；本审未写该文件。只读这份登记，没有访问其所列题源/真实批/远端。其§三引用按Markdown换行拼接后与R1待插原文逐字符相同，本审读回已完成；当前整份文档SHA为 `125894776dc6c511660b687c702858a119d00bf659102877f30bcc876fa6c13f`，副本及核验存 `root_audit/parallel_registration_readback.json`。这是本审所读版本的证据封包，不代替真实部署/发车证据完成，若主会话再改须重读/重封。

登记写 `ready_for_real_retest / launched_pending_backup_channel_confirmation`、以备用通道意见先放行；这些是他方声明，本审未确认实际是否已启动，**本轮正链不确认其金额帽放行面**。不扩成备用通道全部历史复审，也不触碰或停改现场。登记§二明示沿用9月29价格、发车日未联网刷新，尚未兑现R1§4.5/§7第3条的当日价或可证明保守上界义务；“价上浮仍保守”方向错误：按旧低价估出来的同一token金额帽不能保证更高实际CNY费用≤60。须由受权协调者核有效当日价/上下界并另冻config与实际部署身份，不代定数值。这个登记缺口属已有发车条件，未另增P1编号；当前首先仍修§4两程序残余。

## 8. 下一轮有限回修提示词

你在 `/Volumes/CC/Enzyme_Agent/dependingv43` 修唯一原P1 **S5B-V3-02**。基线 `d08432c6014ec476436df0b85765058e43464ffa`。必读 AGENTS、本报告§4/5/7、R1主审§4.2/4.4与R2交付。只修下面两个同规则残余；B保守429、原prompt/output缺轴、原坏派生字段修复保持，不重开S5B-V3-01/化学供给/提交序/S3/S4/历史launch，不改冻结/scorer匹配排序，不实施V4/E，不读真实题面/金标/封存、不调模型、不push、不自行真批。

1. **合法总计回退**：已有有效轴与total内部自矛盾时不能当合法总计退掉未知。复现 prompt900、total1、缺output，cap=.00768/bound=.0064；金额保守保留，第二次发送先拒。同规则output轴下界及两轴情况列适用矩阵，不新增外部账单证明。合法total-only、prompt900+total1900、双轴900/1000、明确0输入/输出/双0、重复回执保持。完整双轴的冗余total冲突与缺轴回退分开，不全面拒绝替代安全规则。
2. **已启用配置存在性**：四消费入口先据既有启用事实辨别legacy未启用与坏块消失；null/删整块、原账本保留不能绕过校验。公开worker第一合法HTTP429时仅破坏cost_guard，cap=.056326/bound=.046938，第二HTTP必须先结构化拒，零新增发送/预约；第一次已发账本仍保守保留，坏块保全，失败case留分母。字段坏/缺、同值恢复、正常builder、真实旧无guard无账本、槽位/冷却/有界retry、孤儿/幂等和双进程最后额度保持。避免以raw当前块不存在直接当未启用；不删除账本/重建配置来洗坏，也不要求抵抗全库协同改写。

先列适用init/summary/acquire/record_response/client retry/worker入口，再共用校验与消费事实。将本轮两个新probe复制fresh tmp复跑，保存观察与正负控；父新回归逐nodeid分行为/字段/拒因/collection，缺模块不报内部行为绿。安全G01及定向回归、326谱系增量/输入SHA前后、完整argv/env/exit/输入输出、嵌套manifest纳哈希；保留准备和失败日志。金额语义按实际修复code_identity登记新批，不静默改旧429账。

搭车文字仅限本轮§5精度：修正不相容legacy聚合/冻结记录SHA笔误、total分支的可信范围、四入口整块缺失与首装配拒绝的证明范围；保留旧主审/永久证据。§9-④正文在途中新增登记已读回，但真实部署封包仍未确认；新修复后更新登记实际HEAD/config/SHA和§7.1价格方向，不在修复里假称已经发车。纯程序回修mimo按既有职责登记实际跳过/采纳注记，不编造回应。实施交付后由主会话核对→正链有限复审，金额P1清零前不发chain10。

## 9. 永久证据与续跑事件

报告：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_R2_CODEX_REVIEW_2026-10-10.md`。

证据：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_v3r2_codex_2026-10-10/`。

- `execution/`：258、G01、父1/18/1完整日志/JUnit与逐nodeid缺席；326输入、实际HEAD/谱系、legacy52聚合核验，子进程缓存例外登记。
- `budget_ab/`：原逐字节probe、完整响应/请求/usage/账本、合法0/total与原partial/429翻转、自矛盾total残余；旧assert/夹具准备失败与修正分开。
- `budget_c/`：四入口24形态、8公开worker、合法controls、原坏bound关闭与整块缺失两公开反例，坏形态/实际delta保全。
- `root_audit/`：159初始固定输入/8527旧证据保护、真实git构成/编号源码/三冻结SHA/继承11文件字节、续跑通知、子包封装复核、发布前后工作树收据。

用户补发额度恢复通知：沿同一有限复审继续，已读材料/初始snapshot/只读核验直接复用。执行分支中断只留下G01的`..`残日志和准备，没有最终JUnit/结果、无存活pytest；残日志保全，续跑只完成未完成suite。A/B先前仅只读准备，无已绿probe重复；C原分支无完成结果交回。账号限额为用户报告来源，本审没有另存quota-error stderr，不伪造异常退出或“已完成数字”。根只读helper首版错列不存在admission.py、JSON摘要helper首次遇None失败，属审核准备错误，修正只读清单/摘要后继续，未执行产品probe或修改仓；失败留档。A/B旧worker初次缺ordinary资产，7次调用未进入模型，不记通过；补已审白名单后fresh重试。新21场景初版1个夹具误期望保留，仅重新解释已有输出22/22，不重跑21场景、不把观察断言绿当P1已清。C准备脚本首版语法错误发生在业务执行前；32案安全断言因整块缺失漏洞exit1，4补充仅补逐表/必要正控，6合法断言绿。这些事件全部留档。

根manifest/SHA只排根`manifest.json`和`SHA256SUMS`，子包控制及嵌套合成artifact manifest纳外层哈希；报告SHA单列。SQLite二进制/pyc不封包，必要合成表文本与省略路径/理由明示。复跑先复制fresh tmp，不在永久证据原地写库或费用状态。不将合成执行外推真实费用、历史remote行为或科学性能。

## 附：安全G01缺席逐nodeid

以下按实际observer记录；10 skip不补读禁区依赖，17 deselected不记通过。

| skipped nodeid | 实际原因 |
|---|---|
| `tests/test_analog_assets.py::test_row_counts_match_v4_parser` | v4 对照代码根不可用:/private/tmp/ppv1_v3r2_execution_resume.ruy8dmpa/g01/dependingv4 |
| `tests/test_analog_v2_corpus.py::test_v2_selected_and_remapped_rows_decidable` | v2 provenance 未生成 |
| `tests/test_analog_v2_corpus.py::test_v2_line_level_one_to_one_and_duplicate_ids_recorded` | v2 summary 未生成 |
| `tests/test_batch_runner.py::test_input_manifest_whitelist_from_frozen_v3` | v3 冻结基准不可用 |
| `tests/test_ppv1_s5a_rework_r2.py::test_s5a_r2_contract_version_registration_and_frozen_integrity` | frozen criteria text not copied into allowlisted isolation trees (G01 boundary); byte integrity verified at the evidence level (shasum in review_evidence package) |
| `tests/test_ppv1_s5a_rework_r3.py::test_s5a_r3_contract_version_registration_and_frozen_integrity` | frozen criteria text not copied into allowlisted isolation trees (G01 boundary); byte integrity verified at the evidence level (shasum in review_evidence package) |
| `tests/test_score_report.py::test_frozen_evaluator_cli_really_runs_dev` | v3 冻结基准不可用 |
| `tests/test_score_report.py::test_evaluator_refusal_on_wrong_split` | v3 冻结基准不可用 |
| `tests/test_score_report.py::test_evaluator_refusal_on_missing_lines` | v3 冻结基准不可用 |
| `tests/test_score_report.py::test_diagnose_route_buckets` | v3 冻结基准不可用 |

17个deselected（16 slow+1显式缺评测器出口）：

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
