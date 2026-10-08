# pollutant_pathway_v1：S3b／完整 S3 独立复审

日期：**2026-10-08（Asia/Shanghai）**。仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。

**结论：S3 不通过，尚未到达 S3 工程完成交接点。P1=[S3B-01、02、03、04、05、06]。** S3a 原放行保持，生产化学链及 AuditContractError“不吞成成功”义务已证闭合；S3b 的冻结输入恢复、损坏artifact恢复消费、后续调度集合、公开恢复执行权、novel提案生产消费者、停止报告必要原因／未探索对象仍有 P1。科学性能pending、判据未冻结不用于增加本轮阻塞。

实际 HEAD：`c1211183c0874b12c5b5461845d3c61f0a84719c`；直接父：`b7f2bba02ca49edd0a45a13bc9b8434909d99175`。本报告源码行号对应当前HEAD。永久证据入口：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3b_codex_2026-10-08/README.md`。

从污染物降解路径预测的目标看，工具和化学审核能正确判断一次给定提案，还不足以保证整次路径搜索可靠。恢复时换输入、丢后续产物、重复执行同任务，会改变实际被搜索的路径；这些是原S3工程契约的问题，不是要求本轮证明真实降解机制或预测性能。

## 1. 固定验收面与独立性

唯一验收面为 S3任务书 `POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md` §2.3b、§3、§5／§6／§7及原规格§17，连同 S3a-r4 报告§8五条交接要求。主文件为本轮交付书 `POLLUTANT_PATHWAY_S3B_DELIVERY_2026-10-08.md` 与 `mimo_ppv1_chem_review_response_r13.md`；核对当前v13请求0d／0c-v13。已关闭S3a和R8继承项不因新阶段开始自动重开。新P1均有原验收条款、实际源码和公开调用链证据；不追加S4／S5、真实检索效果、机制库或外部provider exactly-once门。

工程全量、实际化学生产、队列／公开恢复三个专项在不同新 `/private/tmp` 完整隔离副本执行，含vendor和必要metadata。depending43解释器，`-B`、禁字节码与pytest缓存；旧脚本／证据只读复制，不在永久目录建库。全部规则级合成，无真实金标、题面、封存逐题run、dependingv4、真实v3资产／评价数据访问，无外部模型／provider／实际网络，无commit／push。评测判分零LLM。

全量PPV1、两个父基线执行集合、安全G01各一次。生产17案一次；原断言13通过／4失败的评审期待错误与范围边界完整保留，之后仅只读重判，无行为重跑。队列探针的未触发注入、空stdout解析错误与补充未完成段另行登记，不将其称为完整原脚本全部通过。具体命令、输入输出、退出码、进程日志与SHA见三个专项README。

评审主仓只新增本报告和新证据目录。发布前后保护 **1006个既存输入文件**及实际HEAD／父／tracked diff／工作树，保留用户原AGENTS差异和旧未跟踪资料，见 `input_snapshot.json`、`workspace_integrity.json`。全部行为验证及三个专项包已完成，根报告／第三包汇总尚未发布时，因 **ChatGPT账号额度上限**中断（用户说明非代码错误，两个专项返回用量上限消息）。用户授权续跑后于2026-10-07 **23:12:22 UTC**（本地2026-10-08 **07:12:22**）盘点：HEAD／父／工作树及1006输入全未变化；直接复用所有已完成验证，续跑只补纯归档、文档与SHA核验，**没有重跑测试／行为探针**。用户描述约4500行未独立精确计数，不作验收指标。各冻结专项中“执行无额度中断”是其先前执行／封包时快照，原字节保留，根续跑记录限定中断在汇总写作期；详 `INTERRUPTION_RESUME.json`。合成数据库只在tmp；永久证据保留可读全表／artifact／日志及被省略数据库哈希，不含数据库二进制或缓存。

## 2. 独立执行数字与红绿分类

| 执行 | 本审结果 | 精度／范围 |
| --- | --- | --- |
| PPV1全量 | **851 passed／0 skipped／0 failed**，exit0 | **30文件＝26存量＋4新**；交付31／5应更正 |
| 父b7f同字节两个更新的既有测试文件 | **4 failed／64 passed** | **3行为红＋1缺字段形态红**，不是4行为红 |
| 父b7f同字节四个新测试文件 | **4 collection errors** | 缺queue／model_protocol／production／runflow，64个内部新用例未执行 |
| 安全隔离G01 | **1453 passed／8 skipped／17 deselected**，exit0 | **286输入**，原／副本SHA前后一致 |

父4失败具体是1个profile版本断言、1个 `KeyError('format_feedback_policy')`、2个公开start分流的有意翻转。其中双入口旧测试在父start即失败，resume内段未到，不能说两端行为均在该例翻转。父旧文件64绿与当前四新文件64通过是**两个不同集合**；当前新64从851全量JUnit提取，不相加、不冒称另跑一次。版本红不是化学漏洞数，collection红不认证缺失生产功能的正确性。

PPV1 pytest **14.63s**／外层 **14.968675s**；G01 pytest **203.54s**／外层 **205.542929s**。Python3.11.16／RDKit2026.03.6／SQLite3.53.4；profile-13／search-5／store-9／limits-3／format-feedback-1。

G01＝当前仓 **226**＋普通dependingv3/src **42**＋本仓允许非题面资产镜像 **18**，外部数据根空、固定隔离代码／资产路径。缺席逐项：5真实评价依赖（`test_batch_runner:52`、`test_score_report:110／163／172／184`）、1旧v4对照（`test_analog_assets:95`）、2phase_d metadata（`test_analog_v2_corpus:62／153`）；排除16slow及1显式 `test_export_v3::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden`。完整nodeid与实际理由留证，未将skip改pass。历史1110／1138／1196／1250／1299／1389分别保留历史标签；851和1453都是工程合成，不外推dev（B1中间步骤）或298（RHEA通用酶学）科学性能。

## 3. R4五条与S3任务矩阵实际验收

| 原要求 | 本轮实际证据 | 裁定 |
| --- | --- | --- |
| ①生产首消费／身份恢复 | state语义本体、context信封／内容身份公开链拒；合法工具／writer链保持。公开resume冻结plan／池却可更换，§4.1 | 部分通过，冻结输入消费P1 |
| ②真中心链／异常 | 真render／execute_edits→donor→converter→audit→admission→事件／结算；缺证据unknown，失败三None；实际production宽捕获与真实driver窄捕获分别执行 | **AuditContractError义务关闭**，不扩成所有异常都有统一报告 |
| ③预算／恢复／并发 | 合法四硬杀、预算不重扣、B2不默发、旧底座控制保持；坏artifact／部分后续／两个公开resume反例，§4.2–4.4 | 正控通过，三类原工程门P1 |
| ④公开runner／端到端 | 公开start/resume走独立存储；E01/E02、C06/H04、分支／正常转换控制成立；真实公开恢复新增反例否定完整S3通过 | 分流已交付，完整验收未闭合 |
| ⑤P2文案同步 | 0c-v13有相应落字；错误层次、strict、生产异常、产品来源、测试精度／mimo文件名引用仍需§6更正 | P2落字；不能用改文案代替§4代码缺口 |

E01合法公开链保留首选事件／attempt及下游 `unresolved_continuation`，独立备选继续；E02两类deferred保持、旧revision／重复激活／预算不足控制成立，共同产物不从event删掉。C06／H04实际unknown依赖可有界提交，缺初始供应标unresolved、supported不自动阻断；essential conflict仅当前场景，分支隔离与正常显式转换只后效保持。E03／E04／H05–H08完整公共链仍受§4反例限制，不能仅拿S3a存量通过来认证新增caller。H05新增caller丢depth原因／blocked对象见§4.6，原底座优先级正控不因此重开。

交付方硬杀worker实际调用 `start_ppv1_run/resume_ppv1_run`，不是 `workflow.runner.start_run/resume_run`。本审另用两公开入口的独立子进程完成四硬杀及新进程恢复、二次幂等恢复和并发控制，未伪称交付worker已覆盖公开包装。B1／B3／B4合法无转换控制为1event／4commit／1attempt；**B2为0event／1commit／1registered scripted request／network0**，恢复披露悬空，不把四案都说成1event／4commit。正常转换控制为phase-1，受损恢复不同见§4.3。

生产专项17案原raw13／4如实留证：strict偏离实际violated、H2登记补全合法verified、event的hypothesis_id在SQL列而非payload三项属于评审脚本期待／字段错误，仅只读纠正。另unused旧appearance案按固定范围P2，详§5。没有将这些原失败删掉或重跑探针凑全绿。

## 4. 同原S3合同内P1与最低回修

### 4.1 S3B-01：恢复任务消费了新的plan／池，旧身份没有挡住

**原验收：任务书§3身份首消费、§6.2保存池／任务身份并沿既有记录resume、§7 E03；R4§8.1。** 不是要求真实provider或科学冻结池。

`runflow.py:125／193／345／412`：plan由调用方交给Driver，retrieve／decide再按当前plan取pool；`:987–991`把plan摘要放根task_key，`:1004–1065`的resume身份核对没有验证传入plan或加载原完整计划；decide payload已有pool_digest，却未与重新取出的specs核对。

公开B1同run恢复：同计划正控生成原B事件；不传plan仍正常完成旧任务、0event／no_local_candidate；换合法计划接受新X条目并生成事件。已冻结decide的pool_digest后换计划也被接受，沿旧decide action／task_key执行新池。没有修改数据库或重造原ID，故不是全库一致重造边界。

**最低回修：**首用与恢复共用持久冻结的实际输入来源；plan／池／相关响应与条件转换输入能校验到被消费的task身份。缺原输入不能当空池合法完成；传入变更必须拒或按明确的新revision／新任务登记，不能消费旧裁决键。同plan、无损恢复和合法有显式新revision的任务保持。只存一个无处消费的hash不够；不用新增真实检索器。

### 4.2 S3B-02：recover已识别坏输出，resume又把同action当B1重执行

**原验收：规格§17.4 H07与四崩溃；任务书§3、§7 H07/H08、§9.3。**

B3工具输出已写未提交后，在合成副本分别改坏bundle hash或JSON。`SearchLedger.recover_run`诚实返回 `artifact_hash_mismatch`／`artifact_unparseable`、保持claimed、保全坏文件；但 `resume_ppv1_run`仅把恢复报告放最后summary，Driver仍读取所有本逻辑worker的claimed action（`:255–268`）并重新执行expand。

实测从0event／2commit／7预约行，最终重新运行真工具并写1event／4commit／10预约行；原坏artifact虽保全，错误没有成为隔离／执行门。`search.py:3057–3066／3076–3085` 是实际读取失败和disposition后continue的支段，专项早期notes的2999–3024只指循环／done支段，不能作为错误发生行。不能把recover子调用识别失败扩大为公开resume已fail-closed，也不能把重新计算说成“消费同一output”。合法B3同output恢复正控保持。

**最低回修：**公开驱动必须消费恢复裁定，仅续跑已校验可恢复的任务。坏hash／不可解析／缺权威明确失败或隔离，不以claimed旧收据授权重执行、不自动猜补或创建成功event／commit／consume。其他合法独立任务可按明确隔离策略继续；坏证据保全，合法B1–B4与None／unknown行为保持。

### 4.3 S3B-03：B4只看“已有一些后续”，丢掉完整集合与转换后效

**原验收：任务书§5队列／两类deferred、§7 E02、场景转换和四崩溃；规格§17.4恢复只能用完整权威，不猜补。**

`reconcile_followups`（`:205–254`）以payload LIKE event_id的计数大于1跳过整事件；不核期望的完整产物／deferred／转换后续集合。转换入队与pending_followup附加（`:688–775`）又是两次写入，恢复没有闭合所需后效事实。

三个公开控制：正常转换后followup phase-1且1个done转换；常规after_event_submitted硬杀恢复用phase-0且转换action为0；转换action已入队、pending_followup尚未附加硬杀后，恢复有1个done转换，但followup仍phase-0，已执行转换没承载必要后效上下文。这里不是“已执行转换倒改旧边”，是显式计划的转换／后续关联丢失，不能仅用“以实际执行时点为准”免责。

三产物正常控制全部3条followup；在第二条入队后硬杀，恢复仅2／3，water对应state的任务缺席；完整event／plan仍含3产物。共同产物event不截断的局部正控，不能证明后续调度集合完整。

**最低回修：**从验证通过的event／展开计划及冻结转换输入同源派生必要后续集合，逐项身份幂等补齐，而非“任意已有引用”就宣告完成。转换和待跟进集合持久关联，覆盖event后、转换入队前后、附加前后、0／部分／全部followup及重复恢复；只后效、旧边冻结、预算分账、宽度deferred理由与全部产品event保全保持。无需跨外部系统全局事务。

### 4.4 S3B-04：公开resume共用逻辑worker，两进程都获实际执行权

**原验收：规格§17.4 H06、任务书§7同action两连接／进程，R4§8.3。** 双start目录只有一个胜者不替代此门。

`runflow.py:149`按run生成固定worker；`:255–268`纳入同worker在途任务；`search.py:1157`同workerclaimed收据返回 `claimed=True/reclaimed_by_owner`。两个公开resume进程都被当作同一旧owner。

独立双进程barrier证明：两PID获同action／attempt／逻辑owner，**两方均进入真实 `execute_atomtool_expansion`**，两份tool_entered记录；最终event／commit幂等仍只有1／4，一方artifact冲突退出。幂等最终一条event不能证明只有一方得到执行权。没有推断付费网络重发，实际网络0。

**最低回修：**公开运行／恢复需可验证的执行会话所有权／排他或明确接管协议，使并发竞争方在工具／请求执行前返回already_claimed／unchanged／复用完成，不能都凭同一个固定owner续跑。保留单进程硬杀后合法接管和原attempt／预约身份，不永久锁死崩溃任务；并发用两个真实公开resume进程及执行入口计数，不只看最终event数量。不要求分布式锁服务或外部provider exactly-once。

### 4.5 S3B-05：novel只解析和计数，没有本阶段的假设消费者

**原验收：原规格§7.2，任务书§5.3和§7“parse→冻结假设→固定工具／审核”；空池仍能组装独立底物档案。** 这是S3已定功能，不是科学提案质量门或chemical_reproposal。

`model_protocol.py:76–230`接受novel id／proposal_context；`runflow.py:598–606`仅映射池内rank和记录提案数量，`:412–509`仍只构造、调度冻结池spec。空池在`:345–359`直接no_local_candidate，未进入模型／底物档案组装。

公开非空池＋合法novel响应：parsed_proposals=1，实际只扩原B，novel不形成hypothesis／action，不进入参与物、条件／依赖、真实工具及audit契约。空池＋相同有界响应没有模型请求。把“已接受一条池外提案”改成“只披露计数”可以修文字，但不能宣告本阶段消费者已交付。

**最低回修：**完整novel提案需明确反应内容与来源，按既有结构身份、participants／系数／共同产物、条件／依赖及有限proposal_context构造独立假设，再按预算入队走固定工具／审核；无足够内容不能授有效hypothesis或伪造来源。底物档案独立于池，空池／弃权是合法控制。保留池内稳定ID引用与不可暗改工具已确定产品；不启用chemical_reproposal，不调用真实provider，不要求novel科学性能。弃权可与规则池并行，不另加“弃权必须全停”的新策略。

### 4.6 S3B-06：停止报告丢掉真实depth阻断原因和未探索对象

**原验收：任务书§7 H05、规格§17.4“多原因保留其他原因”、R4§8.4公开接线验收。** 不是增加新的停止优先级或展示增强。

从已有公开 `zero_depth` 输出只读提取，未新增运行：非空CCO池含donor-B；实际depth=0、total=10，结束total用2剩8、retrieval_total用1剩63；root retrieval_per_parent用1／1，故主因 **budget_limit按冻结优先级正确**。`queue.py:224–241`已返回depth_limit阻断的假设对象；scheduled outcome明确selected0／deferred0／blocked1。

但 `runflow.py:490–509`只保存blocked数量，未把reason／对象传给refusals或持久未探索集合，最终 `other_reasons=[]`、`unexplored.blocked=0`且其余未探索计数亦0。已知深度阻断及仍未展开的假设在公开报告消失。不能仅因0event和停止主因正确就说H05整门闭合，也不能误报主因排序错误。完整实际limits／outcome／停止报告在 `queue_recovery_specialist/zero_depth_existing_extraction.json`。

**最低回修：**调度的真实blocked原因／假设／作用域同源持久记录并由公开stop消费；保留既定主因优先级、其他真实原因及未探索对象，恢复后不丢／不重数。覆盖零深度与预算同时到限、独立零资源、空池、合法非零、重复resume；不把从未请求的real0变全局停止，不强行执行blocked，不把停止当化学终点。

## 5. 已接受残留与不升级事项

| 项 | 固定范围裁定 |
| --- | --- |
| 计划池为合成规则级、真实检索效果未验证 | 接受科学／后续数据边界；**合成输入也必须满足本阶段冻结身份与恢复契约** |
| cache_hit同构 | R4已接受P2保持，S3b retrieve不走cache复用；不要求补全所有历史真实性，也不宣称已认证 |
| 两事务间外部SQL并发窗口、保守defer、foreign-run反向诊断 | 旧范围P2保持，不追加全库扫描／外部exactly-once门 |
| 三类RuntimeError原样逃逸 | ChemicalStateError／HypothesisContractError／ConditionContractError已公开执行前拒0event，未吞成verified或成功。缺统一stop／run_error为P2披露，不单凭报错包装升级P1；Audit异常闭合不能外推全部异常都有失败结算 |
| unused历史root appearance损坏 | 不在当前event manifest／links，新合法来源生成另一appearance；新event可先保存，complete全SID历史重放拒，event_committed=0、claimed保持。P2保全，不重开R8已关闭的同hash实际复用守卫；put_state返回None非证书，不冒称零event或坏旧出现被认证 |
| 默认反馈0／脚本响应 | 格式错误默认即停止，有界反馈配置1–4但当前一次重试范围需如实披露；real0默认不得暗开收费。已用脚本反馈成功，登记行仍registered／pending的生命周期与实际网络0分开，不因此自创全新provider门 |

科学性能pending与判据未冻结接受；B4转换窗口**不能**仅登记为非阻塞，因为§4.3已有原恢复／转换验收面具体反证。

## 6. mimo v13：条件、行号与执行事实互证

mimo只读provenance保留，本审未调用外部模型。测试数字／硬杀／恢复／RDKit实跑不能由读码背书。源码核心与父一致不意味着新增caller自然继承全部门；本轮真实caller已分别检验。

| 受审项 | 本审裁定／落字 |
| --- | --- |
| 判据一／kind子集 | 实际 malformed `atomProp:0.n,r` 在atomProp项三元组畸形处拒，kind同名且registered_head=atomProp，不是独立r未知头。kind／reason枚举是词法解析内因子集，不代表所有拒因／所有入口。R4 CX7和15窄探针是历史执行，不冒称本轮新跑；跨RDKit稳定性未验证 |
| 判据二／λ_s×Δ | coefficient_binding与completion分写；audit.py:973–979有lambda_s*delta_pos/neg源式，回应“未确认”是其采信边界，本审读码互证但不编造新的逐式执行。未知系数账unknown、verified仅声明清单数值闭合，不认证漏项、机制或事实来源 |
| 判据三／strict／R2b | 完整绑定且经过前置覆盖／inconclusive分支后strictFalse实际中心violated、R5v；绑定先失败可以unknown，不能将回应的strictFalse→violated写成无条件全称。R2b需显式contract_violation映射，该生产caller不传，构造拒／Audit异常中止不当R1／R2b行；防御R1不声明全称不可达 |
| 判据四 | audit直接对象／derive父对象／from_dict真实强制点保持；assess／aggregate自身无新增强制门。相容性基于给定事实，不认证事实真实性或永久不可行 |
| 判据五／三个None | 工具执行失败在生产audit前短路，真实trace audit0；三None、diagnostic evidence={}、converter仍有元数据。执行成功但证据／映射不足才进入audit unknown，可与其他轴verified共存；unknown不授权R6 |
| 0d.1产品来源 | event产品身份来自池spec.product_smiles内容派生，实际工具输出是核验输入，不覆盖声明身份。声明酸／实际醛的公开链中心unknown并有界提交声明结构，不能称事件产物必等于实际工具输出 |
| 0d.2异常 | production函数宽捕获负控15表零变化；真实driver狭捕获后**有失败outcome结算**、attempt failed，只继续已经排队的独立条目，不自动激活deferred；“零成功”不是整库零完成写入。audit.py有10处AuditContractError直接抛点，runflow.py有1处specific except（:645）；production.py自身无这些抛点／捕获，静态≠任意caller安全证明 |
| 0d.5／0d.7／0d.8 | 既有持久上限来源可核，不能仅凭幂等推全球防循环；novel消费者、公开恢复完整性与执行权见§4，**不是全都落字级条件**；默认反馈0的实际停止行为需落字 |
| 0c-v13／测试来源 | R4父绿11＋1继承其独立JUnit；数test函数不能证明参数化绿case。本文父红为3行为＋1字段，64旧绿与64新当前是不同集合。mimo执行类声明留原待执行标签，不能冒称模型跑过 |

行号抽查发现明确文件名错误：回应0d.8写 `runflow.py:214–223／315–319`为公开分流，实际该文件是reconcile／drive；正确是 **`workflow/runner.py:214–228／305–320`**。`production.py:399–409`失败短路／audit、`runflow.py:645`窄捕获、audit:973–979／1188及context:2327等与本轮源码互证。回应仅看若干completion violation段未确认公式，不代表源码没有公式。

mimo的只读建议不替代§4执行反例。报告与实际双方错处均如实指出；不扩大化学证明范围，composition-only的H2合法verified正控保留，不借此要求完整机制验证。

## 7. 交付一致性与阶段裁定

851／1453／8／17／286输入及legacy身份影响独立证成。legacy代码集合唯一变更为共享runner.py，聚合：`4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c29ae` → `18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6`。旧run跨此变更resume按身份门拒属于已披露行为，不等于字节身份不变；G01安全口径内legacy运行保持，冻结AtomTool／G2与chemstate／path_context／hypothesis／audit／events／store对父字节一致。

交付30文件、父红类别、两个64集合、硬杀入口、B2计数、实际driver失败结算与产品来源需按本文修正；不改旧交付／旧证据哈希，本轮新交付落字。真实化学链、既有合法与unknown控制可以保持已证通过；完整S3恢复、并发及模型消费者未满足，不能将新模块collection缺失、全量绿或mimo“基本同意”当最终审定。

**P1=[S3B-01、S3B-02、S3B-03、S3B-04、S3B-05、S3B-06]；本轮不放行S3工程完成交接，不启动S4／S5，不宣布判据冻结。** 下一轮仅收口§4的六组具体生产消费规则，保留已证S3a、真实工具／异常与合法／unknown控制。第06来自中断前已完成输出的只读裁定，同原H05条款，并非续跑扩充探针或增加新验收面。

冻结建议流程保持为：有限回修→新自包含无金标mimo请求／回应→独立Codex复审→P1清零、完整S3矩阵证成后到工程交接点→用户另行裁定判据版本／证明范围／冻结材料；S4／S5及真实评测、费用／金标相关授权另起任务。本评审不发起外部通道或后续实施。

## 8. 下一轮有限回修提示词

你负责 **S3b-r2**，只在 `/Volumes/CC/Enzyme_Agent/dependingv43`，基线 `c1211183c0874b12c5b5461845d3c61f0a84719c`。必读绝对路径：

- `/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md`。
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_2026-10-08.md` §3–§7及新永久证据README／三个专项说明。
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md` §3、§5、§6、§7、§9／§10。
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R4_2026-10-08.md` §5／§8。
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3B_DELIVERY_2026-10-08.md`、`/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r13.md`及当前请求。

**只修本文§4既定P1，先列入口→消费权威→同源守卫→正负控制矩阵，再改共享规则；不追单字符串补丁。**

1. 固定计划／池／必要输入的首次与恢复消费，旧任务不消费新输入，缺输入不变空池；覆盖retrieve前、decide已冻结、model请求、expand／followup／转换恢复。保持同计划正控与明确新revision的合法新身份。
2. 将recover的坏artifact／缺权威裁定接到driver执行门，零猜重算、零坏任务event／成功commit／consume，证据保全；继续合法B1–B4和明确独立隔离任务。
3. 后续集合从已核event／plan／转换事实确定，补0／部分／全部的每个期望项，保持2类deferred／宽度原因及所有产品；转换入队／附随／执行前后和B4硬杀均验到实际下一边新context，旧边冻结。不能以任意payload引用或计数当完整性证书。
4. 公开resume实际执行会话独占／接管，双进程同action只一方执行；保留崩溃恢复原attempt／预约、竞争方复用。用真实工具入口计数＋barrier及表量，最终event幂等不是唯一断言。
5. 为novel交付完整独立假设消费者，既有participants／结构／来源／条件／依赖与有界工具／audit／admission契约继续消费；空池可组底物档案，池内选择／弃权合法，不启chemical_reproposal，不付费试性能。
6. 将blocked原因／假设／作用域从调度结果持久接到公开stop，保持正确主因并披露其他原因与未探索对象；本案budget主因合法，不改优先级。正常运行／恢复同源、零深度／预算复合／空池／合法非零与重复控制均完整，不用只存blocked计数充当整对象消费。

保留真实AtomTool中心链、Audit异常中止成功义务、三None／unknown／partial、H2 composition-only合法控制、E01/E02／C06/H04、S3a/R8全部已关项。cache同构和外部SQL并发范围P2保持，不补机制库，不访问真实金标／题面／封存run，不改冻结legacy/G2/AtomTool，不含S4/S5，科学pending。

回修新测试对**直接父c121**同字节分类，行为红／字段或collection红／合法和拒绝保持绿分开，早停内部段不报通过。PPV1及安全G01独立新批执行，缺席依赖逐项披露，旧数字不当当前；完整输入输出／worker日志／schema与SHA入新证据目录。新交付／下一序号mimo请求同步本文§2／§5／§6精度，不回写历史报告／证据。版本／身份影响按已有规范登记待审；本地显式git add、不push。实施由主会话派单一实施agent，完成后mimo→Codex复审；本报告不授权跨阶段或外模费用。
