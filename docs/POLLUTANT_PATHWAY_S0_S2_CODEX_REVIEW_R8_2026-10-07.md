# pollutant_pathway_v1 S0–S2 第九轮独立复审（R8 交付）

日期：2026-10-07。仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。
实际 HEAD：`00e509a974b40a7c9779fcd35e53b16637a13d60`；父提交及本轮验收基线：`858dd94c7c6c8fc387940242403d67b6b36b5313`。

**结论：放行 S3 工程实施。R7-01、R7-02 均满足已定最低验收，剩余 P1 清单为空；R6 五组已关闭控制保持，不要求再开 S0–S2 的 R9 回修。** 本次只交审核报告，没有修改执行开关或实施 S3。判据/契约不在此宣称正式冻结，科学性能仍 pending；下阶段按原规格 §17启动，不追加本轮机制、类型、展示或性能门。

## 1. 固定验收、独立执行与保全

本轮按用户自动转发授权，固定 R7 主报告 §4 两项 P1 最低验收、§7 放行条件及 §8 有限范围；不逐轮扩边。已读 AGENTS、R8 交付、mimo v8 回应/请求、R7 主报告和源/测试 diff。三条专项分别核查化学首次消费、存储首提、工程执行；主审再执行原 R6 12脚本、R7 化学/存储/条件公共链及本轮拆分矩阵、静态清单。

只新增本报告与永久证据目录；没有修改 src/tests/既有 docs/AGENTS、旧永久证据，也未 push、调用外部模型或访问真实金标/题面/封存逐题 run；没有读取或修改旧 dependingv4。AGENTS 的两章节入 R8 提交是预期基线组成，不当成审核期间漂移。源码隔离副本含完整 vendor/metadata，执行禁字节码与 pytest 缓存，合成 SQLite 只写新 tmp。

**中断与续跑登记：**全部下表运行验证已在账号额度中断前完成并落盘；中断发生于报告/证据整理阶段，是ChatGPT账号用量限制，不是程序或测试失败。2026-10-07（Asia/Shanghai；续跑时钟18:03:40）接用户指令继续，提交/父提交未变，463份既有输入与工程/化学/存储原SHA清单全部匹配。续跑仅复核既有日志、读取附件、打包与哈希校验；未重跑pytest、公共探针或G01。确切中断时刻没有独立日志，不猜测；原稿最终化学文字二次复核受额度影响，已完成专项及主审独立执行证据仍保留，续跑附件核对已完成。详见 `INTERRUPTION_RESUME.json`。

**归档前的并行变更：**18:17:43（UTC+8）写入前哈希检查发现AGENTS.md相对续跑初核新增未提交流程文字，涉及自动续轮及P1清零/S3放行后交接。具体写入方未独立确认，非本审核修改；实际HEAD仍为00e509a，src/tests及其余462份既有输入全部不变。第一次写入在检查处停止，未创建永久文件。保留该改动，不回滚或提交；初始快照不改，最终清单单独登记它的前后hash/diff，见`concurrent_policy_change.json`。源码证据继续对应固定R8 HEAD，审核范围与结论不变。

| 本会话独立执行 | 实际结果 |
| --- | --- |
| PPV1 全量，21文件，depending43 | **536 passed、0 skipped，1 warning，4.73s** |
| R8 新增两文件在当前隔离源 | **28 passed** |
| 同两文件在858dd94 detached worktree/其隔离源 | **14 failed /14 passed**；原测试字节不改，无 import 适配；worktree finally清理 |
| 基线红分类 | **12 化学拒绝契约翻转 +2存储错误接受翻转；0字段/缺表红** |
| G01安全隔离，实际当前输入270文件 | **1138 passed /8 skipped /17 deselected，1 warning，192.46s，exit0** |
| R6原12入口 + 修后关键行为断言 | 12脚本全部exit0；五组原反例翻转与旧关键控制保持，断言exit0 |
| R7冻结原化学脚本 | **55条、exit1**；在未包 capture 的手性恢复拒绝处停止，原57并未全部运行 |
| 原化学尾部补全 | **3条、exit0**：原尾两案 + 指定手性直接对象补充；主审独立再执行 |
| 本轮化学首消费分段矩阵 | **60条（59 case+metadata）、exit0，观察断言exit0**；主审独立再执行 |
| R7原存储公共链 | **15 case+metadata，exit0，修后逐案断言exit0**；主审独立再执行 |
| 本轮存储公共矩阵 | **17 case+metadata+结尾断言，exit0**；主审独立再执行 |
| R7条件分段控制 | **16 case+metadata，exit0**，脚本内部断言完整完成 |
| 基线单边电荷文案复核 | clean→R6；只改产物charge=99→电荷violated、R5d retain，非R6 |

warning 为 chemstate 文档字符串无效转义，不是跳过。记录数包含元数据、拒绝与正控，不是漏洞数。536/1138 是工程契约回归，不代表污染物降解路径、dev（B1环境中间步骤）或298（RHEA通用酶学）的科学性能。

证据：[README](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r8_codex_2026-10-07/README.md)。包含全部输入夹具/公开载荷、证明、审核与准入、合成损坏及前后counts、完整日志/junit、基线分类、实际HEAD/schema/命令/输入与产物SHA-256、专项报告和复跑脚本。所有会写库/日志的脚本须先复制到新tmp或用隔离控制器，不能在永久目录原地跑。

## 2. R7 两项 P1 的关闭证据

### R7-01：状态恢复和直接审核的首次验证——关闭

位置：[chemstate.py:630](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:630) 的 from_dict接线、[754](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:754) 的 validate_state_object、[audit.py:474](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:474) 逐对象首验。

正常冻结 AtomTool 乙醇氧化证明不动；只在状态 raw 加未登记 r，底物/产物/H2在恢复和直接 `ChemicalState(**payload)`→audit两路均 ChemicalStateError，kind=raw_structure_rejected，底层reason=unregistered_cx_class，不产生本次audit/admission。H2 raw改另一分子CC=O，两路raw_identity_mismatch。指定手性表示远端氧化的同根恢复/直接对象均拒。writer对相同载荷仍拒且零写入，没有静默清洗信息再授full。

规范身份/state_id/CN/formal_charge/stereo/isotope重推导矛盾、未知origin/schema、fidelity缺轴及CN-only伪装也在首消费拒；这些是已有内部一致性，不是新机制或来源真实性认证。from_dict与audit共用同一个纯对象验证函数；writer仍有自己的异常包装，但**共同事实源是build_chemical_state、strict_identity_of、_validate_fidelity**，不是独立双算。不因尚有两个包装实现要求重写才能放行。

合法 clean、raw OCC/canonical CCO、登记atomProp空格、SgD逗号/空格、label空格、指定手性正常链仍R6；CN-only与存档absent_in_archive继续identity unknown/retain。当前全部拒绝不是靠破坏合法正控换取。

**canonical加r边界裁定：**R7的三例retain，在R8恢复/直接两路改为拒绝，符合原最低验收允许“拒绝或诚实unknown，不R6”，无回退。上层kind=state_structure_unparseable；底层是工厂输入守卫的unregistered_cx_class，不能解释成RDKit本体无法解析、真实化学结构非法或实验消旋/纯度已证。交付“结构不可解析”应按这一含义更正措辞。

证据：`chemistry_current/`原55条和补全，`chemical_matrix/`主审独立60条及断言；专项`chemistry_specialist/`保存全部矩阵/静态取证/版本。

### R7-02：显式提供有效载荷时首提复用同hash坏行——关闭

位置：[store.py:1013](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1013) 的_collect_state_writes；[1030](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1030) 计算incoming appearance_hash，读取同(SID,hash)既存行并重算内容，错误立即Ppv1LedgerCorrupt/appearance_hash_corrupt。首提与带载荷重放共用收集阶段；不再因supplied SID豁免实际复用行。

原产物source_refs-only损坏/hash不动，none/prod_only/all三路径首提均拒、counts完全不变、event/projection/plan/links零新增。独立矩阵将同根损坏换到底物，none/sub_only/prod_only/all四路径亦全部拒。落账后损坏+带载荷重放同码拒，原无输入重放保持。

合法无先存、部分先存、全部先存、supplied反序/多来源与无输入重放全部保持首提created=True、重放created=False。supplied状态的已存CN/schema/innerID矛盾继续Ppv1EventConflict/state_semantic_conflict、零写入；unsupplied原state_*_corrupt拒绝保持。按已定范围，不仅为统一错误名称返工。旧manifest/links distinct occurrence完整性没有退回。

证据：`storage_current/`原15case、主审17case矩阵/断言，`storage_specialist/`完整专项附件；不只看进程exit0。

## 3. put_state 幂等边界与已关闭五组

### 3.1 put_state 的登记属实，按本轮首提契约不升级P1

[store.py:673](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:673) 的put_state对重复同(SID,hash)用INSERT OR IGNORE，未重算旧appearance。合成库先put合法状态后，只改source_refs或raw/hash不动，再put原有效载荷：**返回None、counts不变、坏行仍在**；交付§8.4如实。不能把无异常返回当旧行hash已验证，亦没有自动修库。

继续公开submit_event实际引用该出现时，立即LedgerCorrupt、零新增，无坏行被事件/计划当作可信引用。get_state返回的是语义+出现读视图，不是账本完整性认证：raw跨分子首出现镜像经from_dict也拒；source_refs-only镜像可恢复为结构自洽对象，**不证明来源真实性或旧行hash完好**。

R6-04/R7-02的明确最低验收是首提实际引用/复用权威记录，不是所有读写API无条件审核整库。本轮没有此put_state边界使坏行获事件准入、verified/R6或扩展计划的公共证据；仅函数未加同形检查不足以新增P1。它是非阻塞API完善项，后续消费继续遵守已有ledger绑定/submit校验，不把put_state返回当ledger证书。不新增整本账本抗一致重造/真实来源认证要求。

### 3.2 R6 已闭五组保持关闭

| 原组 | 独立回退检查 | 裁定 |
| --- | --- | --- |
| R6-01 复杂共底物补全 | 三个C2H4O初始图center unknown/partial/retain；合法氧化/氢化、H2/[H] composition-only及旧缩放/碎片控制保持 | 关闭 |
| R6-02 原始CX | 并列r/Ln拒；登记移除类正控/供体四字段/手性及proof复算拒保持；恢复/直接对象漏口已关 | 关闭 |
| R6-03 历史条件 | 原12脚本中的条件块+独立16分段；derive/from_dict/audit双向删改拒，unknown/conflict/satisfied与转换保持 | 关闭 |
| R6-04 既存首提 | 四原损坏及supplied残余首提零写入拒；合法先存/显式载荷保持 | 关闭 |
| R6-05 多来源集合 | normal/reverse幂等；删manifest/连row删/只删link→link_corrupt；只删row→entry_missing；均零写入 | 关闭 |

旧六条化学/存储lane的关键行为与R6参考保持，主审assert_r7_replay通过；比较拒绝存在/异常类型/关键轴与准入，不要求更新后的错误解释文字或版本字面相同。旧条件复合探针在预期拒绝后未到达内部后半段，不算内部全过；16分段控制完整补足。

## 4. G01安全隔离数字与缺席依赖

本轮独立结果是**1138/8/17**；R7审核历史结果**1110/8/17**单列，不合并统计，也不冒充原环境1119/16。隔离白名单沿R7的208仓内输入+本轮两份新增测试，另42普通dependingv3/src和18本仓非题面反应资产物理镜像，共**270已哈希输入**。没有复制原v3评价/资产目录或dependingv4、reports/data/evaluation/benchmark/金标题面/封存材料。

PYTHONPATH、BBD_DATA_ROOT空目录、V3_CODE_ROOT、V43_ASSET_ROOT、DEPENDING_V3_ROOT固定隔离路径。原样运行not slow工程测试，只有以下缺席/排除如实登记：

| 类型 | 数量及实际项 |
| --- | --- |
| skip：真实评价依赖缺席 | 5：test_batch_runner:52；test_score_report:110/163/172/184 |
| skip：v4对照源缺席 | 1：test_analog_assets:95 |
| skip：phase_d派生metadata未复制 | 2：test_analog_v2_corpus:62/153（provenance/summary） |
| deselect：slow | 16：原-m not slow选择 |
| deselect：明确排除缺席评价脚本的export纯函数 | 1：test_export_v3::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden |

与交付当前执行证据逐项一致。没有把缺席项改pass，也没有用真实金标凑数；本轮安全工程口径满足R7§2/§7及本条授权。科学评价基准未执行，不认证题域性能。

`execution_specialist/`保存原实际G01控制器、完整输出/错误流、270输入hash、preparation与执行结果。另一个固定R8HEAD/输入hash的可移植safe_g01_reproduce已prepare-only验证，**实际1138来自前述独立测试，未重复整套测试凑数字**。

## 5. mimo v8八项落字与待执行清单

回应为已授权本机opencode免费模型只读渠道记录，不是本会话调用；手机应用是否同实例未证实。执行类声明按程序互证采信，头部主会话536与实施1138自报不替代本轮独立日志。

| 条件 | 独立裁定及有限处理 |
| --- | --- |
| ① r拒绝不反推含义升格正文 | 当前放在“请评审”问题，升格规则正文可取；无从r推实验消旋/纯度路径，P2文字 |
| ② 同源=非独立双算 | 共享工厂/strict/fidelity事实源，两个包装实现；括注应补，P2文字 |
| ③ 判据二入口限定 | 状态自报事实不得伪造的声明须限定经首消费验证入口；本轮恢复/直传已实证，P2文字 |
| ④ scope字面/归属不一致 | **属实，应优先更正**：请求称scope文本包含“不区分键断裂方式与电子去向”，实际completion_license_scope字面不含该句。追加代码字面或改请求归属为许可定义/规则文本均可；composition-only已有范围，不是新增机制/P1 |
| ⑤ 恒入字段≠已适用 | license/scope恒入center detail，存在不能推导已用。须同时看full、uncovered_*非空、unlicensed列表空；没有未覆盖参与物的full也带字段，故渲染不能只看存在性。license_applied/顶层/同屏仍按R7列P2，未证当前假准入 |
| ⑥ frozen与内容身份机制分写 | Requirement/ConditionFact frozen；PathContext非frozen，消费前内容验证兜底；16分段和原历史控制已执行，精确文字P2 |
| ⑦ None≠通过 | 实际失败诊断**三个**判定字段reaction_center_match/strict_target_match/legacy_cn_match均None，diagnostic.center_evidence={}；converter evidence有版本/来源等元数据和center_match=None，不能写成整个evidence为空或“四轴None”。均未评估，非通过；P2精度更正 |
| ⑧ 异常承担方 | src当前无audit_hypothesis调用方；唯一donor复算调用无try包覆，当前拒绝逃逸。未来调用方不得吞异常继续admission，文字P2；不把未来宽捕获假设当本轮漏洞 |

这些条件未证出新的同契约错误R6；按R7§7，不能单因文案缺一句增加阶段门。正式判据冻结前仍需按既有流程把采纳/未采纳及边界文字整理清楚，本报告不替用户外发新模型请求或宣布科学认证。

**“src无except AuditContractError”独立取证：**完整隔离src执行rg返回1、stdout/stderr空；AST找到10个AuditContractError抛点，均未处于Exception/bare宽捕获的try body；唯一check_edit_against_donor复算调用没有try祖先。全src的ChemicalState实际构造2处均在工厂，状态字段直接属性赋值0处；普通外围解析归既有诊断/渲染/冻结边界，静态清单没有把未注册外围入口自动当PPV1授信。grep空本身不是所有动态吞异常的普遍证明，裁定限当前源码与公开链。

待执行清单已裁定：①536/28证成；②基线14/14无适配、全部行为红证成，但不是14个旧R6；③R7公共反例逐案翻转/正控及尾部补全证成；④G01安全1138/8/17证成；⑤锁定RDKit下保留类6/移除类3往返与4形保守过拒登记证成；额外字段/入口清单和异常包覆取证如上。无完整机制、电子轴或真实科学性能背书。

## 6. 新回归和交付表述核对

1. **28新测试有效**：覆盖恢复与直接对象、raw未登记/跨分子、已有规范事实/origin、指定手性、supplied两个首提残余，及合法同图/metadata/手性/CN-only/archive、先存/重放、旧语义冲突。两文件在父提交原字节执行，无import适配；14行为红/14绿、0字段红事实成立。
2. **14行为红不等于14次错误R6。** 部分是将原本允许返回审计结果改为输入契约拒绝。例如[test_ppv1_r8_chem.py的direct_dataclass_fact_tampered](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_r8_chem.py)声称单独把产物charge改99后旧电荷账verified，实际父提交公开链：元素/身份/center verified/full，但电荷violated、charge_delta=-99、R5d retain。该注释须更正；raw最小链才有旧R6→新拒证据。此精度不撤销两项真正P1修复或14行为红。
3. 组合回归在基线第一个DID NOT RAISE失败后，后续内部直接对象/准入部分未运行；当前全绿时执行完整。不能把后半段报成基线已跑，独立直接对象反例与分段矩阵已补足。
4. R7化学原脚本55条早停与补全3条交付如实；但§5.3称“两个旧观察断言都在首个翻转断言失败”**不精确**：化学旧assert首先在len==57失败，行为分支未执行；存储旧assert确实在prod_only首提created=True断言翻转失败。原R6旧assert在首个复杂共底物verified旧断言失败。真实修后证明来自新逐案断言，不能用计数失败背书。
5. R7 flag测试实参顺序和from_dict基线说明修正准确，当前gate_flag_mismatch意图实际受验；6存量文件9处版本升位、另1文件P2语义/文案修正、2新文件，与diff吻合。源码4文件，冻结services/AtomTool、legacy storage/G2/runner未变；AGENTS90行是用户已授权流程固化，不当新增代码功能。
6. “两项全部处置”在固定最低验收内可接受；put_state边界、canonical拒绝路径和P2限制按§2/§3/§5精确登记。工程数字和G01缺席披露与独立实际结果一致，不外推任何题域科学性能。

本审自写/拼装附件也如实记录：存储专项最初误把get_state的appearances envelope当ChemicalState载荷，TypeError是探针误用；已按文档首出现镜像完整重跑17案，原错误流保留。主审复制化学观察断言时初次漏了所需“旧探针执行metadata”文件，FileNotFoundError是附件准备错；补齐实际记录后同断言通过，矩阵/静态先前已完整执行，未改源码或断言消失败。

## 7. 放行与下一步有限范围

**放行S3工程；剩余P1=[]。** R7两项关闭，R6五组保持关闭；无证据要求新的S0–S2 R9回修。八项落字/文案精度、put_state幂等API完善、SRU保守过拒、scope顶层/同屏等继续P2，不新增本轮化学功能门，也不宣称未来消费自动安全。

下阶段遵循[原规格§17](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md:761)与S3既定任务：搜索身份/预算、队列和条件依赖调度、崩溃恢复/并发认领、实际center_evidence接线及既有E03/E04、H05–H08验收。原有恢复/ledger首消费校验必须继续消费，不能把put_state无异常、scope字段存在或失败诊断None当已核实；这是继承已有契约，不是追加阶段门。科学性能可pending，不以通用工程夹具声称路径泛化。

当前执行入口仍fail-closed是未实施S3的既定状态；本审没有解除开关、改源码、启动后续实施或自动再送模型。本轮复审委托在交报告后结束；并行新增的AGENTS流程文字也将“P1清零且S3放行”列为阶段交接点，S3实施由用户/主会话按既有任务流程另行启动。

## 8. 交接事项（无新增P1回修任务）

必读本报告§2/§3/§5/§7、原规格§17和AGENTS。下一实施Agent可以开始S3既定工程，不需要先凭空造R9阻塞单。保留536工程回归与安全G01口径、原合法/诚实未知控制；后续版本变化按内容/HEAD/schema记录，不以硬编码旧HEAD证明当前执行。

文档同步优先④scope归属，其余八落字按表整理；更正canonical上层错误名的含义、三个None与converter metadata、14红不是14旧R6、化学旧assert实际停在55/57。不能回写R7/R6旧报告或永久manifest；更正放新交付/规则文本。

S3实施及后续审核继续不访问真实金标/题面/封存逐题run，不把科学pending列新工程阻塞；若涉及那些数据，走既有用户边界。完成S3按既定阶段验收交回复审，不用“S0–S2绿”冒充S3已实现或科学已验。
