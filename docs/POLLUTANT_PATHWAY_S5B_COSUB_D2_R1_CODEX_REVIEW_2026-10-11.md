# PPV1 S5b 共底物 D2-R1 正链有限复审

日期：2026-10-11。被审提交及首次验证时 HEAD：`ea00297e82931deae6417ca60af60008982d8b5c`；直接父基线：`2e679b31ded26e8b977896800bda3c8f17e9bf14`。

账号用量中断后续跑时，仓库已由主会话推进至`0f83584004769e3dc4e8d19224159e935f069adc`。父子差异只有新增外部评审请求文档，src/tests及本轮既有输入字节相同；该请求不纳入本轮裁定。复用全部已完成验证，不把续跑HEAD冒称为另一轮已跑结果。

## 1. 编号裁定

| 编号 | 裁定 |
|---|---|
| D2R1-C01 | **D2-R1 不通过，唯一残余 P1=[S5B-D2-01]。** 四个原始双删反例已经关闭，记录侧触发及 B 侧合并成立；产物侧仍只相信可被收缩的 contract，另一侧完整记录未消费，公开链仍提交缺记录产物的事件。 |
| D2R1-C02 | 保持其他已关组关闭；本轮不是重开金额守卫、提交序、v4b、S3/S4 或历史 launch。残余直接对应原 NC-10「记录全部产物与事件产物多重集相等」和首次消费完整性，不新增机制/配平/性能要求。 |
| D2R1-C03 | r34 只能采信到互证程度。其原 D3「已封死双删、无旁路」结论不成立；原四案经本轮修好，但不能据此确认完整 NC-10 收口。r34 的多数条件可归 P2；不把读码意见当执行或放行背书。 |
| D2R1-C04 | **D2 设计线尚不收口，D3 评审闭环未完成，chain12 继续缓发。** 修复这一产物声明残余并独立复审通过后，可沿 §7 条件纳入组合批；显式氢墙未因此获批。 |
| D2R1-C05 | 本轮版本登记基本合格：corpus-retrieval-4 / pool-policy-5 / recorded-source-3 / compiler-3；是待修 HEAD 身份，不是已通过冻结基线。三冻结 SHA 及 AtomTool/scorer/evaluation/金额链字节未改。 |

这是合成工程接口复审，不是298题域科学性能验收；不声称命中改善，不启动模型或真实批。

## 2. 固定验收面与证据边界

验收源为上一轮 `docs/POLLUTANT_PATHWAY_S5B_COSUB_D2_CODEX_REVIEW_2026-10-11.md` §4.3/§7/§8，以及既有设计 §五.4 NC-10、r32 R32-CS3-3。R1 交付书和 mimo r34 均已读核；r34 头部明确评的是原 D2，不是 ea00297e，原行号不能搬作本轮源码位置。

只核四个原反例、同规则的记录消费、合法控制、版本/文字同步、r34 条件和组合批条件。交付方在 §十主动登记的 contract/corpus 产物分歧，本轮以合成公开链核验；是否超范围由原验收及具体行为裁定，不由「四案之外」的自报决定。

全部项目执行在新 `/private/tmp` 源码隔离副本，包含必要 vendor/metadata；父子用同一安全 v3 依赖根。depending43、`-B`、禁主进程 pyc/pytest 缓存；隔离子进程例外逐项见执行证据。公共链封禁 socket，模型为 scripted 合成响应；不调用外部模型、不启动真实批。

没有读取真实题面、金标、封存逐题 run、dependingv4 或原 v3 评价资产。真实298的 CS2c/漏斗/池深不重跑，仅核来源摘要及算术；实现方「8真实底物等价」不冒称本会话已复跑，本会话另用8合成默认编译控制。teacher T-1 文档只核状态及 r34 点名的有限规则文句，不评其三个方案，不代替裁定。旧永久证据只读，不原地执行写库。

## 3. 独立执行、红绿分类与缺席

| 独立执行 | 结果 | 精度 |
|---|---|---|
| R1 定向四文件 | 95 passed / 0 skipped | cosub_d2 31、wv41 20、v4b 22、w23456 22；包含原案/正控/NC-12/去重计数 |
| 定向＋既关金额族 | 167 passed / 0 skipped | 95＋原 R1/R2/R3 金额控制72；子集不重复累计 |
| 安全隔离 G01 | **2020 passed / 10 skipped / 17 deselected，exit 0**（318.25秒） | 完整 stdout/stderr/JUnit、缺席逐 nodeid 在 execution/logs/ |
| G01 中 PPV1 文件子集 | 1417 passed / 2 skipped | 缺席的冻结文档守卫由本轮字节核验覆盖，不冒称原仓全量 |
| 直接父同字节三改测试 | 15 failed / 58 passed / 0 collection | 当前测试字节＋2e679b31 源码，逐 nodeid 分类 |
| G01 输入谱系 | 330 输入，6换＋0新＋0缺；前后 SHA 失配0 | 与上一安全控制器同谱系；普通批准大资产仅 SHA/size 锚定，不重复复制 |
| 默认 EAWAG/whole 合成父子 | 8/8 compile 内容相同；4个成功案 prepare 同内容 | 4编译成功、4原有unsupported；后4案未运行prepare，不报其内部校验通过；不是全称的真实题域性能证明 |

交付方 `2031 passed / 0 failed / 16 deselected` 原仓全量仍为**来源声明**；本会话没有越过安全隔离边界执行真实仓 tests/ 全量。G01 与真实环境统计分开，10 skip/17 deselect 不隐去：缺席依赖按完整 nodeid、原因、路径见 execution/logs 的 absences 文件，不能据此认证未复制的真实 v3/v4 评价资产。隔离并行定向/G01子进程观察7个pyc，不能独归因某一pytest；父pyc0、双方pytest缓存0，真实仓及旧永久证据无本轮缓存写入，封包排除所有pyc/缓存。

父15红分类：真实守卫行为10（6指定异常未发生＋4公开 start/resume 未结构化拒）、新披露键缺失1、去重池计数1、版本/语义字面量3。不能把15红说成15漏洞；披露键正控在父上已被接受，其失败只在新字段。初次沿用旧控制器误选 w23456 作第三文件，执行14F/59P；有效前两个文件不重跑，只补真正第三文件 v4b（1F/21P），从两份原始 JUnit 合并本轮三文件得到15F/58P。额外22个 w23456 正控绿及初跑原始日志保留，不伪报一次命令跑了正确集合。

语义共33次公开start：27主案＋5入口控制＋1独立合成EAWAG水解；共10事件，其中合法7、残余坏事件3。主27案的同模型公开resume均实际调用成功（拒绝案保留run_error），17表增行均0；不是27个化学验收通过。EAWAG水解保持1事件/strict及恢复17表增行0。入口控制见 §4 和 semantics/facts.json。公开观察脚本 exit0 只表示取证完整，不等于所有输入满足验收；对坏输入实际成功提交的结果如实留下。所有完整输入、17表文本转储、原生事件、生产报告、native 首读及匹配均封包。

## 4. S5B-D2-01：原四案关闭，产物侧仍有同契约残余

### 4.1 已经兑现的修复

`production.py:254`统一调用 `_cosubstrate_record_declaration`；`:400–448`的适用性来自 contract dict 或 corpus 记录声明，不再来自装配数组。`:264–283`先拒缺 participants 及缺/null/非list装配；`:368–381`在声明适用时无条件调用 NC-10。B 侧 `:499–521`使用 contract∪corpus 合并的严格身份集。

| 原输入 | 当前 prepare/start | 当前事件 | 同模型公开 resume |
|---|---|---:|---|
| strip_both_empty | cosubstrate_event_invariant_violation / declared_cosubstrates_subset | 0 | 同 kind 再拒；17表增行0 |
| strip_both_missing | cosubstrate_assembly_missing | 0 | 同 kind 再拒；17表增行0 |
| strip_both_null | cosubstrate_assembly_missing | 0 | 同 kind 再拒；17表增行0 |
| all_arrays_missing_participants_default | cosubstrate_participants_required | 0 | 同 kind 再拒；17表增行0 |

corpus-only 声明和 contract 单侧清空 B 的附加控制同样拒；合法旁观 B 的 `copy=[]`保持接受。先行 root 检索/认领/预算/注册账逐表保留，不能把「坏事件0、resume增行0」说成 start 全表零写。

共享入口实读：池 decide `runflow.py:870`、novel `:933`、expand `:1324`都调同一 prepare；`:740–749`将 SearchContractError 结构化登记 run_error。novel 坏双删被 `:941–951`记入 novel_rejections，零坏事件，符合原逐条容错，并非吞错或 run 级异常。公开 expand 在 prepare 边界注入双删时也拒；这是明确登记的防御性注入，不冒称修改持久任务权威后的普通重放。

合法 copy、旁观 B 零copy、多B/多copy、whole、多组分whole均保持正常事件。当前 root-only 参考下三个合法共底物事件落 partial；同一合法事件对经过 schema 校验的完整 B/copy 参考可以 matched_strict。这不改冻结判据，不是口径漂移。默认 EAWAG 控件及8合成父子等价保持。

### 4.2 残余证据与代码

记录装配时，两份产物声明本来由同一列表生成：`recorded_source.py:1886–1893`的 contract.record_products 与 `:1912–1932`的 corpus.record_products。当前首次消费却只读 `production.py:480–482`的 contract；`:523–541`只与这一份名单对比，未核对仍在位的 corpus，也未消费原 contract.copy_state_refs 来发现拷贝装配被丢。

最小合成案保留原记录：`CCO + c1ccncc1 → CC=O + C1CCNCC1`。其氢数不配平，计量unknown；这是守卫夹具，不是真实酶反应。仅作三项修改：

1. `contract.record_products` 从 `['CC=O','C1CCNCC1']` 收缩成 `['CC=O']`；
2. `declared_copy_components=[]`；
3. 删除对应 product/coproduct 参与物。

**corpus 块完整不变**（仍声明两种产物）；B 状态/B 参与物、record_key、provenance、原 compile、edits/alignment/expectation、原 contract.copy_state_refs 均保留。不是重写整条原记录，也不是协同改写全库。

| 输入 | 首消费 | 实际公开链 | 原记录消费完整性 |
|---|---|---|---|
| 原合法 spec | NC-10 通过 | 1 event，反应物含B、产物含乙醛＋哌啶copy | 完整 |
| contract_products_shrink_keep_copyrefs | **未拒，仍披露 NC-10 checked** | **1 event，仅乙醛产物，缺哌啶**；resume成功、无新增行 | **违反原NC-10全量产物承诺** |
| contract_products_shrink_keep_corpus（另清copy refs） | 未拒 | 同样1缺产物事件 | 同一残余，不另算P1 |
| 公开 novel 提案传入相同坏spec | 未拒 | 同样提交1缺产物事件 | 证明共享入口消费了同一不完整名单 |

直接证据：semantics/public/contract_products_shrink_keep_copyrefs.json、contract_products_shrink_keep_corpus.json，以及 semantics/entry_controls/novel_contract_products_shrink.json；包含原输入与变更、公开 start/resume、event、production_report、native、17表与网络0记录。**这些事件实际是 R5/retain_conditional、root-only matched_participant_coverage_partial，未声称它们错误 strict/R6。** P1是接受不一致记录后继续提交，并虚报全量声明已消费；原验收没有给 partial 事件豁免记录完整性。

expand 边界注入这个残余时 prepare 放过，但后续 `event_identity_not_frozen_to_action` 门拒、事件0；不能把该注入案报为成功提交。池及 novel 两条正常公开链的成功坏提交已足以成立本残余，不要求拆除后续身份门来证明问题。

### 4.3 范围与最低剩余收口

交付书 §十.1「超出上轮 §4.3 最低收口」的归类**不采信**。上一轮 §4.1/§4.3和设计NC-10明确要求记录全部产物与事件产物多重集相等，且保留缺/重复记录产物控制。现在完整 corpus 权威仍在，却只使用收缩后的合同自比较；这是同一记录消费完整性，并非要求新机制、全库抗篡改或新性能门。

只补这个剩余规则：适用记录在多处声明同一产物时，第一次消费必须先核同源一致性，或从既有单一权威重建并对照各声明；不得选择被改的一侧作为新全量。使用既有 strict_identity_of/状态身份同一键空间按**多重集**核对，保留重复组分意义，不用集合并集隐藏分歧。不规定另开化学比较器或必须重新读取语料全库。

两个本轮池反例及 novel 反例应在 prepare/公开消费前结构化拒，坏event和相关事件提交0；坏声明保全，先行合法账逐表如实记录。已过四原案、缺/重复产物/非法引用控制及所有合法族保持。没有 corpus 双来源的合法旧/默认入口按既有契约处理，不以全面拒绝换通过。不要求抵抗所有权威同步重写后无历史证据可判别的范围外攻击。

## 5. r34 D1–D6 的当前互证与条件归类

r34 评的是原2e679b31。其源码行号多为旧行；以下只引用实际 ea00297e 位置，不采「同意」标签代替执行。

| 判断面/条件 | 正链结论与后续 |
|---|---|
| D1 三分类 | 既关分类/守门不重开，函数原文父子相同、定向保持。984/317/22是来源漏斗，不能把 CS2c 不可归属代理22当实际拒22；摘要账目闭合，不是本轮真实面复跑。D1-1下份请求/报告改记账；bonded子拆、fallback子拆、重原子/H盲区为P2诊断项。 |
| D2 拷贝诚实性 | 合法事件的declared_not_executed、center unknown、expectation coverage refs机读成立。`role=coproduct`不证明已执行，消费执行覆盖必须联读同批生产报告。旁观型无copy仍是声明形态，消耗/催化角色与系数未知；建议补机读说明为P2，不因没有新字段重开冻结Participant协议。 |
| **D3 NC-10** | **原「无双删旁路」读码结论被上一轮公开证据反驳；本轮四案确已修好，但产物侧残余仍成立。** 不采其完整封死或本设计线已收口结论。当前检查在内存build_hypothesis `production.py:352`之后、NC-10 `:378`，早于实际工具及提交；不是「假设构造前」。异常已通过SearchContractError进run_error/novel_rejections，不是必然逃逸进程级终止。 |
| D3-1/2 证明范围与键空间 | 接受限定：声明层/提交前核验，不认证原子来源、执行生成或配平；两侧身份均同源，无第二套比较器。完整性不足时不能仍称checked；其余文字可随下一有限轮同步。额外B计数/严格相等替代子集属于后续，不新加阻塞。 |
| D4 EAWAG/union | parent→R1的find_recorded_exact及compile_recorded_reaction函数原文相同，8合成默认输出全等；实现方真实8例及剥登记键等价仍是来源声明。不能把抽样等价扩大成全域证明。扩展模式中间裸键可能过拒、zip示例非最小差异配对归P2，不放宽gate。 |
| D5 NC-12 | retrieval顶层语义、池标签及新完整参考正控已限定root-only参考；无ignore-tier正在实施。**不采D5-2无条件声称回strict必须criteria-v2**：合法完整参考在criteria-v1内即可strict。本轮没有批准改变真实参考/豁免档；任何未来真实口径变化仍另走裁定/预注册/版本流程。 |
| D6 总采纳 | 冻结判据面未改，不等于NC-10实现完整。当前D3评审责任尚未闭环。r32实际24唯一编号合并为16行，不能把「16行」报成24项全已机器兑现。真实22spec化学抽审没有执行，不冒称已完成。 |

P2落字处置（下一有限回修搭车，纯文字不另立阻塞）：

1. **事件消费者义务及禁句**：coproduct≠执行生成；执行覆盖联读 `expectation_covered_state_refs` / `execution_status`；身份与记录一致、形成未核、配平未知必须分栏。不得写「全部原子有来源」「copy已生成/已核实」。本报告正式采用该消费纪律；实施对外模板同步仍需落实。
2. **旁观型机读说明**：记录声明B但无产物对应不等于已消耗/催化作用已证；系数unknown。现有unknown方向保持，字段增强归P2。
3. **NC-12残句**：`recorded_source.py:1924–1930`每spec的co_substrate_semantics仍留retrieval-3及无范围「结构性无strict通路」，应与顶层retrieval-4/当前root-only限定同步；测试`:1039`「事件提交本身即证明」也须限定实际守卫验证范围，不能把成功提交当独立证明。
4. **记账/请求头/teacher证据状态**：D1代理22≠实际拒；r34请求边界头过时且原D3结论需标事实订正，历史原文不回写。teacher请求仍awaiting_teacher_decision，其「CS2c未跑」规则文句送审前更新为来源摘要已出；不是teacher已经批准。
5. 本轮均值/重叠格/计数P2已有订正：143/298→165/298、增22/298；1276/25/7/15互斥、copy32与代理22交7；3来源→2去重后、截断前池槽的count现为2。真实供给/命中分开，仍不外推dev。数值标签是**去重后、截断前**，不等于最终截断后池规模。

### 5.1 备用通道对照

续跑时按用户指定路径 `docs/POLLUTANT_PATHWAY_S5B_COSUB_D2_R1_BACKUP_REVIEW_2026-10-11.md` 检查，**该文件不存在**；docs根按D2-R1/backup文件名限定检索也未见对应报告。因此没有可读的备用裁定可作逐项互证，不编造其数字、意见或质量评价。存在性与时点存root_audit/resume_snapshot.json及发布前读核；本报告结论来自正链已完成的三份独立封包、原始公开证据与根纯读回。后来若有备用报告，应按实际证据另行对照，不倒填为本轮已经读过。

## 6. 交付一致性与版本

R1四原案翻拒、合法族、共享prepare入口、新去重计数和版本登记均有程序证据，不能否认这部分已完成。交付方如实登记剩余产物分歧及r34 pending，披露值得保留；但登记为边界不自动使违反既有全量记录契约可接受。其「全部适用入口已收口」应限已过触发/B侧，不得包括本轮证实的产物侧。

当前source更改恰production/recorded_source/s5b_builder，三个改测试和一个新交付书；无新source/test。retrieval-4承载此次消费语义、pool-policy-5/recorded-source-3/compiler-3/search-production-2维持登记。修剩余若改变消费/披露语义，按既有版本/身份规范登记差异，不硬指定无关契约升级。

## 7. 设计线与chain12最终裁定

**本轮不收口设计线，不放行chain12。** 阻塞只剩本报告§4的S5B-D2-01产物消费一致性；unsupported比例、1.7%解锁率、命中预期pending和纯P2文稿不构成额外P1。

通过下一有限复审并将r34事实/条件互证结论登记后，D3可闭环。拟冻结身份以真正通过的部署HEAD及最终corpus-retrieval版本为准，暂登记本轮retrieval-4 / pool-policy-5 / recorded-source-3 / compiler-3；不得把本未通过HEAD当成已冻结通过基线。

组合批条件延续上轮，尚不是已执行清单：已过v4b＋已过D2-R1/后续收口；用户授权实际组合范围及新batch；用户/teacher的T状态读回。显式氢墙仍待批准，若组合包含它，另须实施和工程复审；**不把它当每个D2批无条件必含的门，也不默认为本评审批准了那几行AtomTool改动。** 审阅封包所示T-1不立项/待裁，T-5挂起，其他默认档不是teacher批准；不因partial或成绩压力放宽判据。

发车六项执行映射仍需实际新登记：

1. 新batch、新登记，实际部署HEAD、资产SHA、最终retrieval/recorded/pool/compiler身份；不复用封存根。
2. 298题域hit@1≥119/298主列、hit@5=150参考，seen/旧敏感性/U-H5-L及cosubstrate partial归因分栏，零外推dev；预期不是已经过线。
3. 40在途、1logical/题、HTTP1490、60CNY帽，沿用机器budget_guard及同日价/保守输入界/输出上限身份绑定，保守结算不放松。
4. qid双门＋expected graphIds非空/精确键集/全qid_strict；§9-④原文沿v3-R3报告逐字插新登记、读回、SHA封包，本报告不替登记。
5. 同身份固定前10冒烟后按授权发全批；未冒烟不代定真实费用/时长。
6. 全298终态留分母，封存后零LLM判分/费用对账；NC-12按实际root-only scope执行，异常停止保全，不改封存结果。合批为多变量探索，不把增益独占归因v4b/D2/氢；因果归因另做固定其余项的配对消融。

## 8. 下一轮有限回修提示词

> 你是PPV1实施agent，仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`。只修本报告§4剩余 `S5B-D2-01`：记录产物的同源权威消费，不重开原四删字段修复、金额/提交序/v4b/S3/S4/历史launch/scorer/evaluation/AtomTool。
>
> 先列record→spec contract/corpus→prepare→decide池/novel/expand首提和恢复入口，说明产物声明单一来源与各声明的核验关系。当前B侧已有声明并集，产物侧不得只取被收缩的contract自比较。采用既有strict身份键按多重集核同源声明，双来源在位而分歧应首次消费结构化拒，不默用一边覆盖另一边，不重算新身份洗掉坏声明；不另开比较器，不要求重扫语料或抗全库协同改写。
>
> 复制本轮semantics脚本到fresh tmp，复现contract_products_shrink_keep_copyrefs、contract_products_shrink_keep_corpus及公开novel同根反例。保留corpus原全量、record_key/provenance/compile/edit/alignment/expectation；修前池两案/novel均成功提交1缺产物event、NC10仍checked，实际R5/partial（不得夸成strict/R6）。修后prepare/公开消费结构化拒、坏event及相关commit0，坏输入保全；先行合法检索等账逐表如实，resume增行0不当成start全零。补缺/重复/冲突来源的适用消费正负控，合法同义表示按原strict键规范，重复组分保留多重集意义；无第二来源的合法默认路径不全面拒绝。
>
> 四原案、corpus-only/contract单侧B删/单删参与物/非法引用/记录产物缺重复控制保持；合法copy、旁观B零copy、多B多copy、whole、多组分whole、EAWAG默认compile保持。root-only参考partial、完整合法B/copy参考strict保持；不得改判分隐藏坏事件。expand防御注入后原身份门仍保留，不能以拆该门换公开提交证据。
>
> 本报告§5 P2可搭车落字：消费者联读生产报告、旁观型unknown注记、NC12每spec残句/旧版本标签、D1代理记账、r34原D3事实订正及teacher请求证据状态。历史mimo/交付/旧证据不回写；只在新请求/新交付注明订正。按既有version/身份规则登记实际消费差异。
>
> 三冻结SHA/AtomTool/scorer/evaluation/金额链保持。fresh tmp完整输入输出/argv/env/exit/JUnit分类/前后SHA，nested manifest纳哈希只排根控制；安全G01隔离。金标/题面/封存逐题run/原v3评价资产不读，零外部模型/真实批/push。mimo只评本次化学声明消费语义部分，实际回应互证不编造；交主会话按流程核构成与复跑，再送正链有限复审。只交此剩余收口范围。

## 9. 红线、证据和事件登记

| 冻结项 | 父/HEAD/工作树一致的完整SHA-256 |
|---|---|
| criteria-v1 | 7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4 |
| FREEZE_RECORD | 6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610 |
| path_context | 971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d |

legacy52父子聚合均为`279d9bc19bad25e51b7c23ee276da95151a8f25cf598b9dc3642b508d817c4bb`；PPV1的84文件聚合从`f587e478b87b4b496313efd0bb5dccf02ead9d20cb3ef6128b2e75f9625ba188`变为`7103a1f53bc2e1c63ed3e30c855cea42ec2c6283492fe95a38b5a48706d0009c`，恰production/recorded_source/s5b_builder三源文件变化。scorer/evaluation/AtomTool/amount/client/worker/orchestrator/compiler/runflow/endpoint/runner闭合字节和当前原文锚在scope与root_audit，EAWAG函数原文父子一致。旧诚实全拒规则D2已有意替换，不误称仍零字节。

本轮源/测试/既有文稿/AGENTS固定169输入，旧永久证据22,959文件的集合及SHA在发布前后精确核验；既有输入及旧证据未变；中断期间主会话另提交一份请求文档，见首段及root_audit/resume_snapshot.json，不能写成整个期间HEAD未变。续跑快照到本次发布的HEAD/tracked diff/工作树受守卫核对，仅本评审新增本报告及 `docs/review_evidence/ppv1_d2r1_codex_2026-10-11/`，不commit、不push、不启动真实批。

证据README列三隔离包：execution完整回归/JUnit/缺席/父分类/输入谱系；semantics27案及5入口控制＋1 EAWAG公共案/合法reference schema/17表/event/native/生产披露；scope实际行号/r34条件/红线/8合成compile等价及4成功prepare/去重计数；root_audit输入守卫/纯读取证读回/封包脚本/发布收据。嵌套manifest/SHA文件均纳根SHA，仅排根manifest.json和SHA256SUMS；不打包运行SQLite或缓存。

本轮账号用量中断：有。执行代理在回归及finalize全部完成后、根报告与execution manifest封包前撞额度；按用户恢复指令续跑，只纯读取证、补封包/文稿，没有重跑已完成项目验证。semantics/scope此前已封，保持原文不回写，其“无中断”描述仅针对各自完成的子任务；全轮事件由本报告/root新增续跑记录承载。读码路径初次拼错导致一次`nl`未找到文件，随后rg定位，未执行/改写项目；原情况留root事件。父控制器初选旧第三测试文件的事件、scope两次准备路径错误、语义资料猜测路径读错、只读进度tail路径错、根纯读回初次误索stop_report/表转储层级（KeyError后按实际schema修正，未重跑项目）均如实保留，不凑原环境全绿，不把内部未执行的控制报通过。
