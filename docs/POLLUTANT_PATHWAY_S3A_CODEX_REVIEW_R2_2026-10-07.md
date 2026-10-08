# pollutant_pathway_v1：S3a 回修 r2 独立复审

日期：2026-10-07（Asia/Shanghai）。仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。

**结论：S3a 仍不通过，S3b 暂不可启动。首轮五组中，S3A-01 的四类异身份输出绑定和 S3A-05 的进行中工作披露已关闭；S3A-02、S3A-03、S3A-04 仍有同合同内 P1。** 本轮已修掉首轮主要反例，并非没有进展；残余集中在完整权威的内容/状态/引用、已冻结策略恢复、请求跨入口校验。下轮只收口这三组，不追加 S3b、机制库、正式冻结或科学性能门。

实际 HEAD：`dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`；直接父提交：`9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`。源码行号均对应 r2 HEAD。

从污染物降解路径预测的目标看，事件正确还不够：搜索账若能把坏预约、失效尝试或错误结果引用当作成功，路径恢复和有限搜索就不可靠。本审评的是这些工程契约，不认证具体降解反应、酶活性或机制。

报告证据入口：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_r2_2026-10-07/README.md`；其中三个专项分别为 `execution_specialist/`、`authority_specialist/`、`budget_request_specialist/`。原输入来自首轮永久证据，复制到新 tmp 后执行，不在永久目录原地建库。

## 1. 固定验收、授权与中断续跑

基准仍是 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_2026-10-07.md` §4 五组最低验收、§7 放行条件，及 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md` 的 S3a 边界与继承。本轮审核主文件：

- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3A_DELIVERY_R2_2026-10-07.md`。
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r10.md`，连同 v10 请求；只读模型意见以当前源码/执行互证为限。

2026-10-07 13:57:46 UTC 开始读取仓库与主文件、确认完整哈希；三个初次专项代理随后均因 **ChatGPT 账号用量限额**未启动有效执行。用户明确要求续跑，15:11:05 UTC 恢复盘点。已有 r2 tmp 为实施/主会话材料，不当本审执行；没有中断前完成的本审 PPV1/G01/反例结果可复用。初读与哈希确认复用，本次各独立套件只执行一次；归档不再重跑。`INTERRUPTION_RESUME.json` 登记事件、来源与续跑，不把限额算代码错误，也不把他方日志换成本审结果。

全部测试在新仓外隔离 source（完整 vendor/必要 metadata）上使用 depending43 Python 3.11.16、RDKit 2026.03.6、SQLite 3.53.4，`-B`、禁字节码/pytest cache。只合成工程输入，不访问真实金标、题面、封存逐题 run、dependingv4，不调用外部模型/真实 provider、不 push、不 commit，判分零 LLM。`provider_kind=real` 只用于本地登记夹具，实际网络 0。

主仓仅新增本报告和新证据目录；原 AGENTS.md 用户差异、`.zcodeignore`、旧未跟踪材料均保留。375 个明确既存输入、HEAD/父与 tracked diff 的前后核对见 `workspace_integrity.json`；专项另外保存自身安全白名单/hash。

## 2. 独立执行数字及真实红绿分类

| 执行 | 实际结果 | 证明边界 |
| --- | --- | --- |
| PPV1 工程全量 | **648 passed / 0 skipped / 0 failed** | 594 存量 + 54 r2 新回归；不是科学性能 |
| 当前 r2 新文件 | **54 passed**（从648全量JUnit筛得） | 不与全量相加 |
| 直接父 9b78 同字节新增54项 | **52 failed / 2 passed / 0 collection error** | 52 失败的内部分类见下，不全称52个有效漏洞断言 |
| 安全隔离 G01 | **1250 passed / 8 skipped / 17 deselected**，exit 0 | pytest 194.23s，控制器 196.598s；275输入 |

父基线 detached sparse worktree 和完整隔离源使用相同新文件，未改 import/输入/期待来适配父版本。52 失败细分：**48 个行为断言失败，3 个返回形态 TypeError，1 个普通 submit 的旧拒绝 kind 与新期待不同先失败**。后三个 B3 案在字符串 disposition 上按 dict 取值早停；hypothesis 案在普通提交异常 kind 首断言停，未到内部 B3。不能把这些脚本未达到的后段报已验。

专项另用同四类有效异身份合成案完整分段捕获，父基线四案均错误写 event=1/commit=1；当前均 event=0/commit=0 且 artifact 保全。该补证与原52项分类分别存档，没有修改原测试冒称同一断言运行。两个合法正控父/当前均通过。交付“52 行为红”需改为上述分类；这是证据精度项，独立完整探针能补其行为证明。

安全 G01：275 项输入=当前仓215+普通 dependingv3/src42+本仓明确非题面资产镜像18，执行前后 SHA 一致。空 BBD_DATA_ROOT、PYTHONPATH 与 V3_CODE_ROOT/V43_ASSET_ROOT/DEPENDING_V3_ROOT 全固定到隔离树，不补原 v3 真实评价/资产或 v4 依赖。

| 缺席/排除 | 实际项 |
| --- | --- |
| skip：真实评价依赖5 | test_batch_runner:52；test_score_report:110/163/172/184 |
| skip：v4对照1 | test_analog_assets:95 |
| skip：phase_d派生metadata2 | test_analog_v2_corpus:62/153 |
| deselect：slow16 | 具体nodeid留证，未执行其测试体 |
| deselect：显式1 | `tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden` |

R7 1110/8/17、R8 1138/8/17、S3a首批1196/8/17均是各自历史，不能与1250混计。全部工程结果不外推 dev（B1 环境中间步骤）或298（RHEA通用酶学）科学性能。交付的既有更新测试2红/79绿及 mimo提的655c7e8不是本审此次独立执行；不冒充复跑数字。

## 3. 首轮五组逐案关闭状态

| 首轮组 | 已证修复/正控 | r2裁定 |
| --- | --- | --- |
| S3A-01 输出绑定 | 四类run/parent/context/hypothesis普通submit与write侧拒；独立有效旧artifact经B3也拒，零event/commit/consume、原文件保全；合法同output一次提交/二次零新增 | **四类异身份问题关闭**。坏搜索引用造成的B3写入顺序列S3A-02，不重复算新组 |
| S3A-02 权威消费 | 原12×2坏事件账全部拒且零写；缺行/缺event/异父event首次complete拒；合法B4/done及raw守卫保持 | **未关闭**：内容/状态未核全、done复用缺引用、附随载荷自比较、B3过早写event、done返错结果ref，见§4.1 |
| S3A-03 预算/策略 | 已提交event无法defer退款，上限1原连用缺口关闭；未执行合法释放、真实请求登记占额不退；四非法块注册即拒 | **未关闭**：坏已冻结块读取/恢复可补默认或缺版本，见§4.2 |
| S3A-04 请求身份/引用 | 原同键异payload/purpose/action、坏首次登记/释放后继续发送反例拒；合法空attempt非expand、scripted0/explicit retry/real0保持 | **未关闭**：已有row复用、发送/响应/失败与恢复的适用引用验证不一致，见§4.3 |
| S3A-05 停止 | 原claimed有余返回primary=None，claimed=1/open=1公开；六原因优先级63个非空组合及独立资源/空池/user_stop控制保持 | **关闭** |

四个独立子进程硬杀 B1–B4 及双独立进程 ready/GO barrier 保持；合法 B1 同 attempt/预约续跑，B2 悬空不默发/显式 retry另请求、网络0，B3/B4一次提交/补账再恢复不重复。H07 hash/不可反序列化保全、H08已有缺失/错绑拒绝控制保持；基础正控不替代下列坏完整权威分案。

旧脚本使用旧版硬编码HEAD时不当实际HEAD；本轮metadata另记dcb7ed6和实际版本。旧observed脚本在修复前现象不再成立处按设计失败；分案新断言说明修复翻转，早停后的内段未执行均单列。

权威专项完整捕获27个旧分案、5个硬杀/并发控制、120个分段案、5个补充案（3首提守卫+2窗口故障注入）、2个done结果复用案；120案中的81个坏记录被接受、2个晚拒但已写event，是同规则的入口分布，不是83个漏洞。预算/请求/停止矩阵有效114案=91符合合同/23不符合，另有63个停止优先级组合；与旧案及pytest有重叠，不相加。

审核夹具准备错误也保留：首次vendor路径假设错误尚未进入有效执行；初始停止优先级oracle顺序错两项，旧原始日志保留、修正的63组合另记；missing-version拒绝若只是budget_exhausted不能计策略门通过。补充窗口脚本最后误期待Ppv1LedgerCorrupt，实际正确writer对账拒为Ppv1EventConflict；5案完整捕获后才在该断言停，随后仅对已存输出作正确只读断言，没有重跑窗口。各专项README列实际退出码、更正和未执行内段。

## 4. 三组残余P1及最低收口

### 4.1 S3A-02：完整权威仍有内容、引用和消费顺序缺口

**原验收出处：首轮§4 S3A-02明列必要attempt/预约/commit的存在、归属、版本、状态、内容、冻结引用及first complete/B4/done复用；任务书§3第2条、§4.3/§4.4 H08。** 不要求新机制或来源真实性认证。

现有修复只读重放有效地关闭原24个坏化学/事件账反例，但 `_verify_action_references`（search.py:1461）对预约主要核存在/run/action；不读取units，对本action预约不核各limit所需scope/subject内容，不拒所有未知状态；attempt主要核run/action，不核其状态/假设/task内容。`_preverify_completion`（:1691）已有commit复用也没有该完整搜索引用核验；done的 `_verify_commit_event`（:2334）不消费完整attempt/预约/提交记录引用。

独立公共链证据：

1. 在完整合法event已提交的单案中，把预约units改0、status改未知或scope改错，或把attempt改abandoned、异hypothesis/task，**first complete与B4仍可写done/commit**。预约units/status/scope三类可出现已执行但相应预算used=0，坏行未被拒。这是坏记录首次消费，不依赖竞态。
2. 已done后删除必需预约/attempt，recover/claim/complete/submit复用仍接受；recover称 `done_commit_verified`。commit.attempt_id不存在也被四口接受；commit.run错属时recover会拒，而claim/complete/submit仍接受。不能把一个入口能拒扩大成全入口闭合。
3. `report_projection`/`expansion_plan`保留正确版本但改成不存在state引用、plan非法status，first complete/B4及done复用仍通过。`_verify_event_ledger_authority`（:1557）从当前坏行取payload，再作为“预期”传同一 `store.submit_event` 重放；后者附随部分比较的是“坏存储=传入坏存储”，没有在该分支执行首提的范围/状态语义校验。相同坏载荷**正常首提会拒**；同库原正确载荷writer重放拒且零变化。存在且自比较相等不是内容完整证书。
4. B3 已有合法正确bundle，删除该action必需预约或attempt，再recover：**先event0→1及附随对象写入，之后complete才SearchIntegrityError**，commit0、action仍claimed。不满足坏必要引用消费前零event的要求。B3需在事件提交之前核完整执行权威，不能靠后半段拒来证明整段零写。
5. 合法done A后提交有效异parent B，done分支（:1351–1354）验证旧A后返回 `created=False/already_completed/event_id=B`；A库中B不存在，commit仍指A，零表变化。该成功复用**返回了未经完成的结果引用**，不是插错事件。合法同A返回A正控成立；属于完成结果复用的一致性，不重开已关闭的四类B3写入绑定。

证据：`authority_specialist/` 的逐案输入/前后全表、源码和原公共参数、正确合同观察断言；其中 `done_result_reuse_cases/done_result_foreign_parent/input_output.json` 锁定第5项。每案与合法对照分别捕获，不把案例数当漏洞数。

**最低修复/验收：**一次列清first complete/B4/B3事件消费前/claim已完成复用/submit已完成复用/complete已有commit/recover各适用入口，复用同源完整搜索权威验证。核预约实际单位/状态/limit/所需scope-subject，attempt状态/主体/task与冻结引用、commit归属/适用引用/合法kind及结果ref；保持按主体共享alternative预约的合法语义，不能要求共享行都由本action创建。done也消费其必要结算证明，不只核event。附随对象沿现有first-submit语义复核合法范围/互斥/状态，避免自己比自己；不要求无独立来源的历史真实性认证。B3先验全部必要引用后才能写event。坏单案结构化失败、保全且零该action新成功消费/补账，非法引用不得返回成功ref；合法非事件outcome、同事件幂等/不同parent/context、正常S0–S2控制保持。可提取PPV1共享验证帮助函数，别另造三套判据。

### 4.2 S3A-03：用户覆盖装配的“补默认”被用于已冻结坏策略

**出处：首轮S3A-03要求注册与读取/恢复首次消费同源类型、键、范围、版本拒坏块；任务书§4.2完整往返可重放、§3第5条不猜迁移。** 原四非法块在register已经正确拒；已执行defer退款也保持关闭。

`profile.validate_search_limits`（profile.py:258）是合法用户覆盖装配函数，缺项补默认；`SearchLedger._limits`（search.py:584）/恢复读取对**存储的完整冻结块**也使用这条宽装配语义。

以原完整合法profile块登记总action额度0，仅把已存 `search_limits` 改成null：`_limits`/budget_snapshot变成默认总额度10，随后claim真的新增3条预约。recover不传expectedpolicy或传同一坏存储块均接受；传原冻结块会在identity比较处正确拒，这一正控不能代替无expected的公共恢复校验。仅删除存储limits.version，预算/无expected恢复也接受；其后claim仍按原总额0报budget_exhausted，**这不是坏版本被拒**。

证据：`budget_request_specialist/` 保留原冻结块、单字段mutation、每个读取/claim/recover的实际输入、异常/输出及全表变化。没有改当前默认参数，不把用户合法partial overrides本身判坏。

**最低修复/验收：**区分配置装配和已冻结对象消费。合法用户覆盖仍按现成十键生成完整块；首次注册后的读取/recovery/budget/claim/request消费必须先核冻结块存在、完整类型、必需键/版本和适用身份，缺/null/坏值不能静默补默认/猜迁移。核验失败无成功执行/预约/补账；null与缺版本、原四非法块在各适用消费口分案，同时保持合法完整往返、默认real0/off、各资源适用零预算和未执行defer释放。不要删除shared validator或强制所有合法用户配置显式给十项。

### 4.3 S3A-04：已有请求/状态迁移/恢复未共用完整冻结引用

**出处：首轮S3A-04最低修复明确登记、已有复用、发送/响应/失败/恢复核合法run/action/适用attempt、策略、生命周期；任务书§4.1同键异内容/§4.3/§4.4 B2。** 原首次登记反例与载荷/目的/新action冲突多数已拒，不能因此声明全请求生命周期闭合。

`register_model_request`（search.py:984）的已有row复用与新输入校验不完全对照stored run/attempt引用；`_verify_request_execution`（:1170）主要核action仍claimed、attempt属于action且open，不核所有run绑定/expand必要attempt；`recover_run`（:2159）直接列pending行，未消费相同引用守卫。

当前公共链实证：stored request.run_id/attempt_id被改坏后，用原正确参数重复登记仍可unchanged；状态口接受foreign run或expand请求空attempt，并写sent/responded/failed；恢复将缺action/已失效执行引用列为普通pending。不是声明它们产生了实际网络或verified化学结论，而是已损坏的请求权威没有被识别，正常pending与缺权威未分开。原同键同内容、合法非expand空attempt、scripted网络0、显式retry新ID/占剩余额度、real0与released正控另列保持。

证据：`budget_request_specialist/`逐入口原正确请求、单字段坏stored row及前后ledger/返回。digest-only缺原载荷时不要求凭空重算payload；已有incoming正确payload的冲突与结构/引用/身份能核部分须实际消费。

**最低修复/验收：**登记新/已有row复用、发送/响应/失败、恢复的适用身份/引用用同源验证：stored与incoming的冻结run/action/attempt/目的/载荷digest/retry一致；run-action-attempt完整归属，expand不能静默省其必要attempt，合法非expand空attempt保留。坏或失效引用不得新建/改变成功状态，不得包装成普通合法pending；可记录结构化unknown/完整性错误并保全，不因无法证明真实响应而猜补。真实登记失败/超时/悬空仍占额，scripted/fake网络0，不真实provider/不外部exactly-once；显式retry与竞争方复用已完成结果语义保持。

## 5. 两个登记边界的裁定

**complete核验→写入窗口：确有窗口，顺序单消费者假设内不单列新P1。** `_preverify_completion`走public writer replay取 `BEGIN IMMEDIATE` 后rollback；接着complete才重新 `_begin`。结果零行内容写入不等于纯读事务。两连接确定性故障注入，在原预核验结束/事务已退出后只插barrier等待，另一独立进程取得写锁、把state charge改99并commit，随后原complete仍done/commit，无SQLite busy；之后正确writer重放拒。干净同harness正控保持。

这证明窗口**无“微秒级”协议上界**，锁释放后的并发修改不保证busy可见。该实验主动用SQL并发破坏不可变记录，未证明合法公共writer或顺序单消费模型会自行改坏它们；按固定验收不凭这种额外故障模型增加第4组阻塞。应将文字明确为“两个事务间未持锁，不提供跨并发外部改库保证”，避免宣称程序强制无窗口。S3b若扩展权威并发写模型，应明确事务/不可变所有权；本轮三组P1首先修复不依赖竞态的实证。

**defer未归因事件保守拒绝：可接受边界，不升级P1。** 冻结身份下事件已提交但没有其他action的提交记录能归因时，拒释放是保额度的保守选择；合法未执行释放、已归因场景正控实际保持。不认证这次一定执行过，只说未能安全证明可退；不能拿它要求S3a提前实现S3b trigger/调度。

## 6. mimo v10 条件与事实更正

回应provenance披露一次ECONNRESET断流、续会话判据四拼装；本审不修改原回应、不调用模型。读码不等于执行，只有与源和公开运行一致的段落采信。**判据四三处、判据二两处属于下轮规则文本修订，不增加r2化学代码门；但回应判据五及程序清单另有大量事实错误，不能照单转实施要求。**

| 项目 | 当前核对/下轮文字 |
| --- | --- |
| 判据四孤儿方向 | 已有必要要求绑定旧作用域但无按签名快照→unknown；评估行/签名无对应要求或集合不一致→context_snapshot_inconsistent拒。v10把后一种写成unknown、方向也反，应更正 |
| 判据四入口限定 | 恢复/from_dict、derive父对象、audit直接对象强制validate；assess_conditions/assess_candidate_conditions/route_assessment自身没有该调用，需上游纪律。明列已强制/仅调用纪律，不因文字更正重开旧S0–S2范围；新S3b必须接真实守卫 |
| 判据四重建半边 | 新语义context用新context_id并保留parent_context_ref链，旧引用不复用。合法新内容重建不应被当篡改拒绝；补落字 |
| 判据二known_absent | 请求的registered_missing/documented_absent/unrecorded不是当前实现理由码；实体缺席及非物种字符串同值缺席→conflict，非物种字符串异值known_absent/未列出→unknown；数值/区间缺席→unknown（numeric_absence_semantics_undefined）。按实际消费语义落字，不跨值域泛化 |
| 判据二系数与结构句 | 非法表示系数在构造/提交拒，R2b须caller报告映射；coefficient_binding_mismatch是覆盖违例→partial_unchecked_transformation/中心unknown，最终处置依其他轴和规则顺序，不能固定写自动reject/R2b，也不能照mimo一律固定R5 |
| 判据一内因读法/同源/标签 | 两处state_structure_unparseable外包装对应不同异常类，按detail.reason.kind分CX守卫/真解析失败；同源确定性拒篡改非独立算法。C2等外部标签内联，保留类按实际CX token写，不把接受/拒绝当样品认证 |
| 判据三恒入/复用 | full/partial完成分支有license/scope；unknown_coefficients/unverifiable早退例外；跨假设未绑定proof通常中心unknown，篡改自报与复算不一致抛契约异常，无本次成功admission，不混成同一种“拒” |
| 许可语义⑤ | 键断裂/电子去向句已在正文，仍归规则而非code scope，不再次要求改代码字面；正式冻结由用户另裁 |
| S3b caller/模板/图等价 | 生产caller仍没有，异常正常逃逸+宽捕获负控及合法正控待S3b；区域净变化不认证供体模板/机制，图等价非酶识别；legacy_cn_match仅旁证，三个None非通过 |

**回应自身必须更正：**

- 实际锁定 RDKit **2026.03.6**，不是§6所列2025.03.1；`655c7e8`不是本轮父基线，也未执行它的2红/79绿。
- 当前src中 **10个AuditContractError抛点全部在audit.py**，不是回应列的search×2/context×2/profile×1/store×4/audit×1；源/本轮白名单tests的specific except为0，抛点无吞异常的广捕获body包覆。未来caller义务仍不因grep0闭合。
- 判据五所引 donor_present/donor_consistency/_walk_conversions/same_cid/conversion_warnings 等大量名称在当前src没有；其所称对应分支/处置不能作为读码事实或测试要求。该段关于R3/R5、供体电荷WARN、转换步数等推论不采信，必须回到实际DonorConsistencyDiagnostic/净变化/strict/声明对账/内部proof重算。
- 回应称未知checker_scope会抛AuditContractError不实：audit.py:1064–1070实际产生中心UNKNOWN及center_checker_scope_unknown。真正类型违约/完整性失配的异常在后续分支，不能用不同scope规则替换当前合法unknown。
- 回应把旧test_f11说成“legacy_cn_match True⇒R1”等，与当前测试和失败早退源不一致；本轮实际三None/diag{}→converter无scope/proof→公共audit unknown保持。
- 对r9的精度更正应引用原话“补全规则被调用且判负”，不能再转写成原作者说“许可本身判负”。独立判断仍应看coverage_violations及真实枚举，不用无条件partial等式。

当前15案窄化学探针：raw+r/canonical+r/真正坏canonical的双包装与内kind、RDKit直接可解析r、9登记CX往返、失败三None/converter→audit unknown、runner小控制、全src AST。它不是再跑全部历史R8证据，不与648相加。chemstate/audit/path_context/hypothesis/events五源对9b78字节全同，继承的R6五组/R7两项继续保持；本轮P1发生在新搜索消费，不宣布旧普通化学writer失效。mimo要求的执行数字以§2本审替代他方声明。

## 7. 交付一致性与放行条件

数字648、1250/8/17可证；版本profile-10/search-2/store-9/limits-3登记、runner/store对父字节不变、legacy code_identity仍 `4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c29ae`，正常事件事务及PPV1双入口fail-closed保持。测试调整显式非事件OUTCOME/版本/先触发错误kind，不把存量S0–S2正确行为改成全面拒绝。

交付“完整权威闭合”“全部事件消费入口”“存储块被改坏消费前拒”“全请求执行引用闭合”仍超出实际证据；§4三组必须修代码，不能只修文案。52行为红需细分类，mimo读码错误需与真实源分开。S3b未交付清单诚实，不用其缺席新增本批门。

**本轮P1=[S3A-02,S3A-03,S3A-04]；不放行S3b。** 下轮在固定矩阵上闭合三组、保留已关S3A-01/05及合法/unknown/partial，独立PPV1和当前白名单G01、四硬杀/barrier/H07/H08不回退，文档精度与完整证据一致后裁定。测试数不锁死648/1250。

S3b未来仍按原任务书范围：两类deferred/冻结池队列、条件与依赖/场景转换、模型协议有限反馈、固定工具中心证据生产链、独立runner分流。先建立正确PPV1存储与消费闸再解除fail-closed；不要把None/partial或license存在变成功，不吞AuditContractError继续本次admission/submit；原判据与工程通过均不代表科学性能或S4/S5启动。

## 8. 下一轮有限回修提示词

你负责S3a-r3回修，只用 `/Volumes/CC/Enzyme_Agent/dependingv43`，基线 `dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`。先读AGENTS.md、首轮S3a报告、本文§3–§7及新永久证据README。**只有三个原组继续P1：S3A-02/03/04；S3A-01四B3异身份与S3A-05已证保持关闭。不实施S3b。**

先列register/read/claim/write_bundle/submit/first complete/已有commit复用/defer/B1–B4/recover/request登记及状态/预算/停止入口矩阵，登记适用对象、合法状态、冻结身份、必须引用和共用事实源。依次修：

1. **S3A-02：完整搜索权威与附随语义。** 对预约单位、合法状态、实际limit所需scope/subject及主体共享，attempt状态/hypothesis/task、commit.run/action/适用attempt与outcome引用做同源消费核验，first/B4及done四入口一致；不要只核“行存在/run/action”。附随projection/plan不能从坏当前payload取出再自比较，沿现成合法范围/互斥/状态同源核验。B3写event前先核必要attempt/预约，坏链0event/commit/consume并保全artifact；done submit返回真实已完成event或明确冲突，不能createdFalse却返回未存的foreign event。保留合法非事件outcome、共享alternative预约、同hyp不同parent/context、已完成幂等及raw拒。
2. **S3A-03：冻结策略消费不能补默认。** 保持用户override装配函数合法补齐；已登记完整块读取/恢复先严格核类型、必需完整键/版本及适用身份。null/缺版本/坏值必须消费前拒、零执行预约；budget0不能被坏恢复变10。四非法原注册与合法完整往返/各资源0正控、未执行defer释放、已执行不退款保持。不靠必须传expectedpolicy或调用方先手工校验弥补公共恢复缺口。
3. **S3A-04：所有请求消费同源冻结引用。** 已有row复用对照stored与incoming run/action/适用attempt/目的/payloaddigest/retry；发送/响应/失败/recover共享合法run-action-attempt归属/生命周期。expand必要attempt不能空，非expand合法空保留；坏引用结构化失败/unknown并保全，不伪装普通合法pending，不新状态成功写入/猜补。digest-only不要求凭空原载荷复算，已有incomingpayload则必须比较。scripted/fake网络0、真实额度0、失败悬空占额、显式retry新ID/剩余额度、单认领执行权与合法完成结果复用保持。

按本文证据逐案从公共链做完整自审，坏记录写入后的首次消费、B4、B3前置、done各口和合法正控都实际运行。正确信息不全仍unknown/partial，不能全面拒绝换通过；不增加机制库、来源真实性认证、S3b功能或外部exactly-once。TOCTOU主动并发破库是已登记范围边界，准确披露两个事务间未持锁，无“微秒/必busy”承诺；若顺手同源事务收口不得改变冻结legacy行为，不以未证支持的外部破坏模型增阶段门。

新回归在直接父dcb7ed6 detached worktree隔离源跑同字节，固定输入/行为，不适配import/期待；区分行为assert、返回形态异常、错误kind先停、collection/字段/表缺失、合法正控及内部未执行。首轮旧observed只读保存，修后按设计失败，用新分段合同断言登记翻转，不修改永久hash。PPV1全量、安全白名单当前G01（8缺席/17排除逐项，数若变化实记）、四硬杀/barrier/H07/H08与继承矩阵复跑；工程数不外推dev/298性能。

新交付书按三组逐入口→行为→证据→红绿，明确哪些已关/未关、版本/身份/hash影响和S3b未交付。下一mimo规则请求按真实轮序v11，自包含内联定义；本文§6文字修订与mimo事实纠错都落字，**不能把虚构的供体分支/错误RDKit/错误异常处置照搬**。caller生产链仍未闭合留S3b，判据未冻结；实施agent不外模，由主会话按通道送审。

证据使用新 `docs/review_evidence/ppv1_s3_impl_<实际日期>/s3a_<新轮次>/`，原脚本/完整合成输入输出前后表/实际argv env exit耗时/HEAD schema/白名单SHA/JUnit/manifest+SHA（含嵌套清单）齐备，所有执行新tmp不原地写永久证据。不访问真实金标/题面/封存run/dependingv4，不真实provider，不push；判分零LLM。只必要PPV1模块改动及本轮测试/文档，语义/version按现规登记；v4.3本地提交git add显式路径，不带既存AGENTS/未跟踪旧评审材料。单实施agent串行，完成后主会话核对→mimo→Codex复审。
