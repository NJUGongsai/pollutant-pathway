# pollutant_pathway_v1 S5a 回修 r3 正链终局复审（R4）

日期：2026-10-09，Asia/Shanghai。正链 Codex 主审；协作子代理在独立 fresh 隔离树执行，mimo读码与交付数字只采信到本轮程序互证的程度。

**结论：S5a r3通过，P1=[]；S5A-05关闭，S5a正式到达 `interface_verified_only` 工程接口阶段验收点。**旧引用下换入另一个自洽身份已被共同首消费守卫拒绝，合法恢复、新内容新地址和场景转换保持。S5A-01/02/03/04、S4/S3/ISO-01旧已证项保持关闭。此结论不是科学性能验收，不代表完整S5完成；proposed评测契约未自动冻结，正式S5b尚未启动。

## 1. 固定验收、身份与授权范围

- 实际HEAD：`c91d557e94823e223355521f180d5384cd8d9d4a`；直接父：`39d739d04f9b3e6e7ad78cb0ec5f1547ac54c962`。
- 验收基准：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_R3_2026-10-09.md` §4/§8唯一P1 S5A-05；阶段任务 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md` §14/15/16/12。固定首消费身份绑定与合法正控，不新增科学门或重开一般unsupported。
- 交付：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5A_REWORK_DELIVERY_R3_2026-10-09.md`；mimo请求/回应r24。mimo只读未执行，本审未调用外部模型。
- 最新授权：题源已拍板**298题域题集**，费用**不设上限**；这两项不再写TBD。金标转换规则、通过线、正式分母及预注册/独立性仍须用户/teacher圈定；正式S5b未启动。本轮仍是工程接口复审，不触真实题面/金标或原v3评价资产。

初始守卫 **2026-10-09 08:47:53+08:00**：135项src/vendor/PPV1测试/指定文档输入、5592个旧永久文件SHA及精确集合、HEAD/父/工作树。发布前后同一守卫复核。原snapshot沿用旧模板的一句“S5b not authorized”仅为文本残留，保留原记录、在 `root_audit/authorization_annotation.json`按最新派单更正，不影响实际输入SHA守卫。当前轮没有额度中断；上一轮用量中断与平台未执行控制只属旧历史，不嫁接成本轮事件。

所有业务fresh `/private/tmp`，完整src含vendor/pyproject，conda depending43（Python3.11.16/RDKit2026.03.6/SQLite3.53.4），主命令 `-B`、`PYTHONDONTWRITEBYTECODE=1`、pytest cacheoff。父子普通v3镜像同根，镜像只复制既有批准源；G01只在安全白名单树全量，真实仓tests/不全量。未访问金标/题面/封存逐题run/dependingv4/原v3评价资产，无LLM判分、commit/push；仓内仅新增本报告与永久证据目录。

## 2. 独立执行、红绿及G01缺席

| 项目 | 本审实际结果 | 范围与精度 |
| --- | --- | --- |
| PPV1全量 | **1119 passed /0 skipped，exit0** | 43文件；1105既有+14新；不是科学性能或漏洞数 |
| 父39d739d同字节回归 | **12 failed /123 passed /0 collection /0 skipped，exit1** | 当前6个新增/更新文件，135 nodeid，detached父隔离源码；不是父全量PPV1 |
| 父12红分类 | **5行为+2静态守门/文案断言+5版本字面量** | 交付称2“字段红”；实际无KeyError/字段缺失，不计真正漏拒行为。首次停止后未执行的内部断言不报翻转 |
| G01安全隔离 | **1719 passed /10 skipped /17 deselected，exit0** | 306输入复制时/执行后/当前批准来源SHA全同，仓侧246；305+1新、9合法变化 |
| 五案与共同入口 | **五案全部完成；六消费体实测拒错配** | 三原公开start/resume；两本轮自构造亲自实测；六体级负控不冒称六次完整公开resume |
| 单位继承 | **六B1公开案6/6** | 四unknown、两compatible；sample/aggregate一致，有合法事实与必要性来源 |
| legacy | **52标准聚合保持、两树4合成公共产物逐字节同** | 聚合 `18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6` |

135父nodeid、首失败原文/类别在 `execution/baseline_classification.json`；完整argv/cwd/固定env/exit/stdout/stderr/JUnit保全。工程数字不外推dev/298；专项观察与suite通过数不相加。

306谱系新增 `repo/tests/test_ppv1_s5a_rework_r3.py`。9合法变更为production/evaluation/preregistration/profile及test_ppv1_profile、test_ppv1_s4b_export、test_ppv1_s5a_rework_r1、test_ppv1_s5a_rework_r2、test_ppv1_s5a_schema；其余输入与305谱系SHA同。见 `execution/g01_lineage.json`、输入及前后/current批准源清单。

**10skip逐nodeid/理由全部登记**于 `execution/README.md`及 `execution/g01_exclusions_detail.json`：原v4对照1、v2 provenance/summary2、原冻结v3真实评价5、r2/r3两代冻结docs守卫2。新增第十skip是 `tests/test_ppv1_s5a_rework_r3.py::test_s5a_r3_contract_version_registration_and_frozen_integrity`；第九仍为r2对应守卫。安全树不复制docs，skipif如实缺席；本审窄PPV1与父树开跑前只补两份批准冻结正文/record，使两守卫实际执行。17deselect＝16slow+1明确charge/evaluation依赖，逐nodeid也登记；不读红线资产补数，缺席不算通过。

**首跑与历史日志裁定**：本审三suite首跑如上（父exit1为预期红绿对照结果）；各有独立日志根，未删除/重复已成业务。实施r3的attempt1 stdout/stderr/JUnit、命令/env、input/post-SHA档案完整且数字互证；同字节副本在 `execution/implementer_g01/`，核验收据在 `execution/implementer_first_run_audit.json`。实施日志HEAD当时仍是父39d739d+待提交改动，不冒称已执行当时尚不存在的c91d557；当前已提交HEAD由本审独立执行验证。r2历史首跑完整stdout丢失仍保持原限制，r3日志保全不回填历史。本审没有从单一attempt目录推断所有未知历史尝试，只确认现存首跑记录及当前独立结果。

G01子进程7个隔离pyc诚实登记，current/parent为0；源SHA不变，缓存不入包、不写真实仓，不说所有树均无pyc。案件探针有准备/后处理错误，见§7，不把它们称产品失败或藏成全轮零事故。

## 3. S5A-05关闭：三层校验在共同消费前接齐

`production.load_context:355-375`依次读H07、执行冻结 `PathContext.from_dict`内容身份复算，再比较 **requested context_ref == recovered context_id**，通过后才return。不一致抛 `ConditionContractError`、kind=`context_reference_binding_mismatch`，detail有expected_context_ref/recovered_context_id/storage_key/parent_context_ref。保全坏artifact，不换绑旧地址、不覆盖、不猜迁移、不默发新引用。

from_dict只证明载荷自洽，绑定层证明请求地址对应这份内容；两层职责分开。新增守卫兑现冻结判据四“新内容新context_id、旧引用不复用”，不是新增criteria-v2化学硬门。冻结from_dict、物种三分和事实正规化语义未改；typed/restore低层unknown+值顺序边界仍P2。

### 五案公开链与合法正控

| 案 | 本审实际行为 | 裁定 |
| --- | --- | --- |
| 1 正常checked unknown=None | 原字节探针公开start(after_claim)→resume成功，真实events=1 | 合法恢复保持 |
| 2 改内容、保留旧payload ID、重封H07 | load/resume拒context_content_identity_mismatch，events=0 | 原内容身份层保持，先于新绑定层 |
| 3 自洽新payload ID、重封H07、仍旧存储地址/行动引用 | load/resume拒context_reference_binding_mismatch，events=0，坏输入保全 | **原P1翻转，关闭** |
| 4 checked合法新内容占旧地址 | 本轮亲自实测load/公开resume拒绑定错，events=0；同payload存自身新地址可正常load | 内容合法不豁免地址绑定；上一轮未执行的判别面补齐 |
| 5 合法新ID新地址、parent链/场景转换 | 亲自实测子ctx引用、地址/载荷ID一致，公开start→resume转换成功，followup沿新子ctx | 合法重建半边不误伤 |

1–3来自上一轮永久mimo原脚本，复制fresh并保持原字节；4–5来源是实施方自构造脚本，本审复制fresh亲自运行，**不冒称上一轮Codex已经执行过**。当前三原案完整观察exit0不是“产品所有契约都通过”的通用证书；正式events从真实表重算，旧原脚本reaction_events错误摘要原样保留。

案3根请求仍为 `pc_a72ff6b1f27d9335da52`，地址 `ctx:pc_a72ff6b1f27d9335da52`；自洽载荷是 `pc_d9978ff5d99526ca0c46`。当前共同loader先拒，不再像上一轮沿新身份派生子ctx和提交事件。对照before复用上一轮正链封包的独立实际结果，**不冒称本轮再次fresh跑这三案父业务**；本轮父新回归独立fresh红绿见§2。

### 拒绝写入、保全与六入口

案2/3原公开前后17表按主键做added/removed/updated对照：**只有search_actions/search_commit_records/budget_reservations发生变化，各新增1且部分既存状态变化**；其余14表（含meta/search_runs）真实逐行同。合法root retrieve已先完成，所以不能称整个resume/十五业务表零写。拒后events、hypotheses、生产report、ctx新文件、endpoint/stop均无坏对象新增；decide保持claimed，错误原样上抛，不吞成成功或普通run_error。

案4原自构造脚本提供逐表完整计数和artifact JSON保全，缺其原before全部行；**不冒称案4有全表逐行零写证明**。其拒后events=0、无关三表增量如实登记。案5末态快照也不是before/after零写证据。

案2/3的artifact JSON相等及原字节文件均保全；主审另只读按原probe固定 `json.dumps(indent=2)+newline`序列化重构突变写入字节，与拒后文件逐字节相同。此为确定原写协议的重构互证，**不是补造原来已记录的pre-write SHA**；案4只采JSON保全观察，不补造前字节证书。补件在 `root_audit/qa/artifact_bytes_readonly.py/.json`。

六生产消费口都共用loader：runflow decide/expand_hypothesis/scenario_transition三处；endpoint继承依赖/路线条件评估/路线条件快照三处。AST/source互证之外，本审六体均动态拒绑定错：前两endpoint包装成endpoint_context_consumption_failed并保留binding cause，第三口直抛；三个driver方法使用合法已完成run的真实done receipt直接调用体，**不是三个新的完整公开driver-loop负控**。六次调用前后17表逐行及非DB产物字节保持，不以个别合法入口覆盖不适用入口。路径矩阵在 `cases/results/entry_matrix_static.json`与 `entry_matrix_dynamic.json`。

## 4. 继承、版本与五处P2文字同步

- S5A-01身份六scope封顶、S5A-03逐必要from/to覆盖、S5A-04授权resolved写边界、18同源条件+2 required_absent单列，均由完整常驻r1/r2用例守门。本轮不重跑大批旧身份/必要节点/写边界专项，不把未额外执行部分说成再次专项通过。
- 六B1额外fresh公开复跑：K298/K25/F77/实体mg-L四案condition_unknown+requirement_unit_not_representable，C25/空要求unit两compatible，sample/aggregate同源，有合法事实和必要性来源。透明wrapper只选原17脚本 `CASES[:6]`，未把其余11案算执行。原input/unit/key/value展示保全；value仍repr展示，非已实现typed value_raw。
- S4 C01-C04/B4/版本门、S3已关组与ISO-01的17常驻正负控保留，全量通过。冻结正文SHA `7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4`，FREEZE_RECORD `6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610`，path_context `971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d`均与父逐字节同。runflow/endpoint/search/store/S4/audit/legacy关键源也与父同；production本轮有改动，不冒称其字节继承。不用字节相同掩盖新证漏洞。
- search-production-1→2、profile-22→23；evaluation-3/template-3、reference-graph-1/split-manifest-1不变。profile.contract_versions并未增加search_production字面键：实际profile版本、PPV1全树code_identity与production_report.production_version承载本次变化；不夸大成新字段。旧run不能默续新profile/code身份。
- evaluation去除docstring后操作AST与父同；preregistration除docstring及condition_policy.rule字符串外AST同；profile除schema_version常量外操作AST同；production类/函数体仅load_context改变。模板proposed正文确实变、prereg内容SHA会变，不能说输出逐字节不变；条件classification语义零变，未默选独立判据或单位换算。

**上一轮五处必须同步文字已兑现**：evaluation两处、preregistration两处、profile一处known×unknown限定物种键，非物种适用unknown仍unknown，删合法链“顺序相关”尾巴。condition_unknown具体枚举、canonical-by-key省略单位代价、value仅repr/禁止eval、实体事实只证存在不证浓度、指标只分桶且正式分母TBD也准确落字。拟冻结前的这个必同步项关闭，不把mimo新建议变成新增工程阶段门。

## 5. mimo v24正式互证与八组P2

三判断面的同意在本审五案、六入口、AST/版本/冻结SHA证据下成立：职责放在唯一生产恢复消费loader，selfhash与地址绑定分开，合法新地址/历史冻结保持；**采信其“收对”**，未见新增同契约P1。不因mimo“无P1”背书全系统无缺陷，执行类声明均由本审另验证。

原回应没有逐条连续编号8，以下按其来源语义整理八组，完整出处与未执行项见 `mimo/mimo_adjudication.json`：

| 建议组 | 正式处置与证明边界 |
| --- | --- |
| 1 正常地址=身份、旧输入冻结/禁止静默換绑 | P2解释；指正常persist路径，不包括任意低层文件写入；同身份合法复现仍允许 |
| 2 同身份去重与run来源 | P2；绑定证明引用=内容，不证明来源属本run；H07/run信封及账本另有约束，未做跨run实测，不声称外国原封包可通过 |
| 3 新增入口共用loader/导出provenance范围 | P2维护义务；必要集构建存在/H07核验与公开reader的manifestcore/版本/权威/引用/hash/策略/stale闭合不同，不简读为整个导出不验；无新公开授信漏洞，不重开S4 |
| 4 合法内容不豁免绑定/显式修订 | P2；未来修订应新记录/新地址/父引用/明确取代，未实现新修订机制，不能借修订覆盖旧裁决 |
| 5 当前fail-stop/未来per-action及后代隔离 | 当前方向符合最低要求；未来细粒度隔离P2，不加入本轮门。重复resume/解除只能人工等未额外实测，不声明已实现全部承诺 |
| 6 父链逐环证明范围 | P2；子hash含parent_ref不自动认证每代存在、完整或科学可信，loader不递归验证祖先；缺父科学回溯unknown与运行消费结构化失败须分写，不照抄成已实现恢复机制 |
| 7 新引用与旧phase历史冻结 | P2可读性同步，冻结现义不变；程序历史记录不是实验真实性认证 |
| 8 继承≠新观测 | P2；按事实自身phase_id/subject_scenario_ref等作用域过滤；空/全局scope可合法跨阶段，不能笼统说所有继承旧事实都不参加新阶段 |

mimo问2①把unknown事实附值O2描述成“此处有氧受体”须缩窄：**status仍unknown，不是known_present**。原P1按引用/历史地址成立，原案也未证错误R6或科学终点翻转。父链存在引用≠整条祖先已核；正文中这些程序/化学证明范围不因修复升级。mimo原文只读保留，不替其补执行。

## 6. 交付一致性、遗留P2与最新晨报决策

交付1119/12+123/1719+10+17/306及五案主行为与本审一致，S5A-05闭合声明确认。精度同步三项：父两“字段红”改静态断言红；实施封包是**63纳SHA附件+2根controls=65实际文件**，不是65全部排无控制；实施提交前HEAD字段保持实际父+改动，不当当前审定HEAD。

实施r3首跑日志教训已应用、全附件SHA核验通过，r2丢失日志不追补。五处旧P2必同步文字已关闭，其他八组建议及以下旧边界按P2/teacher继续登记，**不阻塞本轮工程接口验收**：

- A1有限身份参考根配不上却以native_missing归因的保守不评、C1 participant_list_status未消费/exact仅声明集合、roles/coefs/occurrence及unknown==unknown参考支持范围；
- 聚合因果/kind子桶、点值basis/数值优化语义、value_raw展示增强、实体事实单位仅存在性不含浓度阈值；
- typed/restore低层语义、未来新增入口纪律/父链审计/精细隔离、endpoint helper/死键、R16样本≠确认事件等已披露支持边界。

**已决定**：题源298，费用不限。交付旧“题源/费用全部TBD”“S5b未授权”的泛句已落后于最新派单，应在交接明确更新；本审只新增自己的报告，不回写该交付书或通用模板。

**仍待用户/teacher**：金标转换规则（反应/状态/角色计量/条件来源怎样映射及unknown/partial许可）、通过线/阈值、正式样本/边/确认步分母与统计/独立性、预注册拟冻结口径及其他尚未圈定TBD。298是RHEA通用酶学题域；本轮合成工程结果不证明该题域科学成绩，也不外推dev污染物路径性能。费用授权不替代判分零LLM、数据访问/外发红线或冻结判定；本轮没有真实指标数值、没有启动正式S5b。

## 7. 永久证据、事故及证明范围

目录：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s5a_codex_r4_2026-10-09/`。

- `execution/`：1119全量、135父nodeid红绿分类、G01完整argv/env/exit/JUnit/stdout/stderr、306输入前后/current源SHA/谱系、10skip/17deselect逐nodeid、实施首跑档案、legacy52及四合成公共产物、缓存观察。
- `cases/`：三原公开案完整输入/17表原行与PK差分、原脚本/产物；实施自构造4–5亲自执行输入与输出；六动态消费体前后行/非DB文件SHA；六B1真实公共继承、20单项/2typed低层等附随观察，175业务JSON/text及嵌套manifest全部保全。低层/体级/完整公开链明确分开，不把末态快照当零写证书。
- `mimo/`：原请求/回应/交付材料、编号源码/父读、AST操作等同性/六入口、八建议来源矩阵/未执行项、五处文字及版本/proposed证明范围；仅读码不冒称运行。
- `root_audit/`：135输入/5592旧永久SHA与精确集合前后守卫、冻结/旧包/实施包只读核验、授权注记、只读artifact字节重构互证、主审判断/终稿QA与发布收据。`report.sha256`绑定终稿。

案件两个执行包装器事故如实保留：第一次完成decide后，观察器用错expand标签，在调用expand前停止；修选择器后只执行剩余五体，没有重跑decide/五公共案。第二次全部六体已完成，汇总cause=None发生TypeError；只读归并原JSON，不重跑业务。另只读字段探索误用aggregate（实际aggregate_metrics）已登记，不算产品失败或通过。mimo只读探索路径错误已更正，父不存在新测试的git128也不是collection红。这些不影响产品收口，不能照抄实施“零事故”作为本审全轮声明。当前轮未发生平台拦截/额度续跑；案4–5这次真正执行，不用上一轮未执行控制冒充。

所有业务证据脚本必须复制fresh tmp再跑，不在永久包原地建库/日志。argv/env是固定相关环境，不含全ambient凭据；无socket仪表不宣称实测全局网络次数零。SQLite二进制、symlink、pyc/pytest缓存不入封包；根manifest/SHA256SUMS仅排自身这两根控制文件，所有子包controls和嵌套业务manifest均纳SHA。

## 8. 阶段验收确认与S5b前置交接

**正式确认：S5a r3通过，P1=[]，S5A-05关闭，S5a工程接口到达interface_verified_only阶段验收点。**原S5A-01至05全部收口；科学性能pending、S5整体尚未完成，不自动宣布proposed评测契约冻结。

下一步由主会话交用户/teacher圈定仍未决金标转换规则与通过线、分母/独立性、预注册口径，再按S5任务书组织正式S5b；题源298与费用不限已获授权，不重复当未决选项。不因本报告自动开始读取真实题面/金标，不以工程通过数代科学指标或跨域成绩。

交接应携带：本报告+任务书、当前审定HEAD/契约版本与源码身份、合成接口证据、旧P2支持范围与上述八组建议；继续unknown/partial机器披露、事实/要求同源裁决、参考节点/边许可封顶、必要节点覆盖、授权写根、零LLM判分、阶段状态不得由评测器自行生成evaluated_*。真实金标/题面相关mimo出题前及后置评审按既有三触发纪律，真实数据外发不由本工程报告授权。

不提供下一轮P1回修提示词：本轮P1已清零。P2增强进入后续明确授权批次，不与当前工程放行捆绑；真实数据的金标口径和通过线不能由实施或审核代理替teacher决定。
