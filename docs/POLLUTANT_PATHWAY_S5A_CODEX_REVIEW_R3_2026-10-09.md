# pollutant_pathway_v1 S5a 回修 r2 正链复审（R3）

日期：2026-10-09，Asia/Shanghai。正链 Codex 主审；协作子代理在 fresh 隔离树独立执行，结论采信到与本轮程序证据互证为止。

**结论：S5a r2 不通过，唯一阻塞 P1=[S5A-05]。原 S5A-02 已关闭，单位回修六案6/6、17桶4变13保持。新增的具体公开证据是：旧 `ctx:<context_ref>` 地址下换入另一个自洽 `context_id` 的上下文，公开 resume 仍接受并提交事件。缺的是引用与内容身份绑定，不是单位分类、物种条件口径或科学性能。**S5A-01/03/04及旧继承反例继续关闭；仅重开生产上下文首消费这一已定契约。程序模式 `interface_verified_only` 不等于本审阶段验收确认；S5b未授权、未启动，科学性能pending。

## 1. 固定验收、身份与中断续跑

- 实际 HEAD：`39d739d04f9b3e6e7ad78cb0ec5f1547ac54c962`；直接父：`1ef9e4840ff1be233dedcb543b967447cd591276`。
- 本轮最低范围：上一轮 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_R2_2026-10-09.md` §4.2/§8 的 S5A-02；阶段任务 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md` §14/15/16/12；既定首消费、恢复、引用完整性继承不回退。
- 材料：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5A_REWORK_DELIVERY_R2_2026-10-09.md`，mimo请求/回应r23。mimo为用户提供的只读评审，未执行；本审不调用外部模型。
- 版本：evaluation-2→3、preregistration-template-2→3、profile-21→22；reference-graph-1/split-manifest-1不变。要求侧映射能力由评测侧消费，不默选独立条件判据。

初始守卫为 **2026-10-09 05:20:33+08:00**，134项源码/vendor/PPV1测试/指定文档输入、4537个旧永久证据文件SHA及精确集合、HEAD/父/工作树。发布前后同一守卫复核。用户续跑消息报告账号限额中断、7:51恢复、已约1950行验证输出；如实登记在 `root_audit/continuation_event.json`，不把账号限额当产品错误，也不把用户报告的时刻/行数冒称本审测量。已完成套件和业务输出直接复用；续跑尝试追加判别控制（平台拦截、未执行），随后仅只读核验、裁定与封包，没有为续跑重复全量suite。

业务脚本先复制到 fresh `/private/tmp`；完整src含vendor和pyproject，conda depending43，Python3.11.16/RDKit2026.03.6/SQLite3.53.4，主命令 `-B`、`PYTHONDONTWRITEBYTECODE=1`、pytest cacheoff。父子批准普通v3镜像同根；真实仓 tests/从未全量执行。未访问金标/题面/封存逐题run/dependingv4/原v3评价资产；判分零LLM，无commit/push。本轮仓内只新增本报告和永久证据目录。

## 2. 独立执行数字与缺席、事故裁定

| 项目 | 实际结果 | 证明范围 |
| --- | --- | --- |
| PPV1全量 | **1105 passed /0 skipped，exit0** | 42文件，1087既有+18新；不是科学性能或漏洞计数 |
| 父1ef9e48同字节回归 | **15 failed /106 passed /0 collection /0 skipped，exit1** | 当前5个新增/更新文件的121 nodeid，detached父隔离源码；不是父完整PPV1 |
| 父15红分类 | **10行为+1字段KeyError(reason)+4版本字面量** | 空要求单位父本来compatible；其reason缺失只算字段红。首失败之后未执行的内部断言不冒称行为翻转 |
| G01安全隔离 | **1706 passed /9 skipped /17 deselected，exit0** | 305输入，复制时/执行后/当前批准来源SHA全同，仓侧245；谱系304+1新、7合法变更 |
| 六B1公开案 | **6/6最低断言通过** | 四不支持单位unknown、两合法保持；sample与aggregate同源，不用空facts伪造单位分支 |
| 17桶对照 | **4变化/13保持** | before复用上一轮正链独立父记录，after本轮fresh；不冒称两边本轮新跑，不采实施before数字 |
| 条件/身份/写边界专项 | **64次公开evaluate，71规则断言通过；5写边界4拒/1合法** | 17+20+4条件、17+6身份；额外探针不与pytest通过数相加 |
| legacy | **52标准聚合保持，两树4合成公共产物逐字节同** | 聚合 `18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6` |

父逐nodeid及首失败类别/未执行范围在 `execution/baseline_classification.json`；完整输出/JUnit在 `execution/logs/parent_complete/`。G01控制器陈旧expected=1707不当结果；实际是1706通过+新增第九skip。

305谱系：新增 `repo/tests/test_ppv1_s5a_rework_r2.py`；七个合法变更是evaluation/preregistration/profile及test_ppv1_profile、test_ppv1_s4b_export、test_ppv1_s5a_rework_r1、test_ppv1_s5a_schema，其余输入SHA与304谱系全同。清单、前后/current来源核对在 `execution/g01_lineage.json`及SHA文件。

9个skip逐nodeid/原因全部载于 `execution/README.md`和缺席JSON：v4对照1、v2 provenance/summary2、原冻结v3真实评价5，以及新冻结文档守卫1。17个deselected为16slow+1明确charge/evaluation依赖，逐nodeid也完整登记。**缺席不算通过**，不读取红线资产补数。第九skip为 `tests/test_ppv1_s5a_rework_r2.py::test_s5a_r2_contract_version_registration_and_frozen_integrity`：安全G01白名单不复制docs，skipif按此明确缺席；本审窄PPV1和父树只补两份已批准冻结正文/record，使这条守卫实际执行，最终1105/0与15/106/0如上。

**交付G01首跑事故裁定：可接受当前版本的最终工程回归证据，不认证丢失的历史完整执行。**实施方登记首跑1 failed/1706 passed/8 skipped/17 deselected，失败是该守卫读取缺席docs的FileNotFoundError；改skipif后1706/9/17。首跑完整stdout/JUnit已被删除，现存只有摘要/定位/事件记录。本审只读核验这些现存材料，不补造首跑，不把“1706业务通过、无影响”扩大成独立历史背书。当前HEAD由本审完整fresh G01验证，守卫另在窄PPV1实执、冻结SHA独立互证，因此日志缺失为P2过程教训，不单凭历史缺口阻塞当前版本；以后每次尝试用独立输出目录、封包前不删日志。

本审自身准备事件与交付事故分开：初始窄树沿无docs布局得1104/1 skip、父14红/106绿/1 skip；完整原始日志保留。补批准元数据后复跑必要套件取得最终数字，不称初次产品失败。只读legacy后处理器tuple键错误发生在任何legacy业务前，修适配后两树各只执行一次。conditions初次缺指定synthetic helper在业务前停止；追加oxygen案业务已完成，随后独立对照误用basis失败，修只读对照而未重跑业务。mimo专项的计数后处理更正以专项日志为准，不重写原观察。G01测试子进程产生7个隔离pyc；current/parent为0，源SHA不变，缓存不入包、不写真实仓，不声称所有树均无pyc。

## 3. S5A-02关闭：单位实际参与首消费与聚合

`evaluation.py:1044-1089`的共同映射处先决定显式要求单位能否被冻结Requirement表示；`:1211-1226`把不可表示单位分类为 `condition_unknown`、reason=`requirement_unit_not_representable`。未换算、不猜测，不把K/F丢掉后当C比较；sample逐条转录披露，aggregate消费实际分类桶，未仍记compatible/conflict。

六案均经 `start_run→带ledger的read_native_export→evaluate_scientific→sample/aggregate`，存在合法事实及必要性来源：

| 参考要求 | 事实 | 当前sample/aggregate | 裁定 |
| --- | --- | --- | --- |
| temperature_C=298，K | 25 C | condition_unknown | 原essential_conflict翻转 |
| temperature_C=25，K | 25 C | condition_unknown | 原compatible翻转 |
| temperature_C=77，F | 25 C | condition_unknown | 原essential_conflict翻转 |
| electron_acceptor=O2，mg/L | O2已知在场，无单位 | condition_unknown | 原compatible翻转 |
| temperature_C=25，C | 25 C | compatible | 合法正控保持 |
| temperature_C=25，空要求unit | 25 C | compatible | canonical-by-key默认保持，reason披露随行 |

原key/unit/value展示串/失败原因保留，非规范温度allowed_units保留。**披露value是 `repr(raw_value)` 展示串，不是JSON原生value_raw**；原JSON输入本身在reference_graph完整归档，不能宣称已提供无损typed value_raw字段。pH允许单位集含空串，不要求每个键的空单位都额外披露nondeclared。实际机读值为condition_unknown，不笼统把unknown/unsupported族写成condition_unsupported_key枚举。

旧20案：18语义映射与冻结同一 `aggregate_environment_fit`一致，2 required_absent保持 `requirement_status_not_representable`单列。事实侧source_unit_unknown/unit_mismatch三态未改，空要求单位不升级事实缺单位。17桶B2/B3均保持，恰好四单位案变化。直接语义对照不是两schema字节等形；四不可表示单位的旧手工canonical Requirement对照不拿来给新输入背书。

## 4. 新P1：S5A-05 生产恢复接受旧引用下的新上下文身份

### 4.1 原契约与具体代码

此项由mimo v23“restore表面”互证触发，**不是本轮单位改动引入**。AGENTS返工教训2/4明确允许以公开证据重开接受损坏权威的同契约缺口；S3任务书§3.1/3.2/§7继承矩阵要求上下文、内容身份、引用及历史快照在首次消费闭合。冻结判据四 `POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md:352-366`明示内容身份核验且新内容新context_id、**旧引用不复用**。只加引用绑定兑现现义，不新增冻结条件判断门。

`production.py:315-324`声明 `persist_context`返回context_id就是存储键，写 `ctx:<context_id>`。但 `load_context:327-335`仅按请求ref读取H07包装，再直接返回 `PathContext.from_dict(payload)`。后者 `path_context.py:2070-2092`只证明载荷context_id等于载荷自身内容hash，未证明它等于请求/行动引用context_ref。H07外层task/hash与载荷selfhash分别自洽，仍不能证明旧行动引用的是这份内容。`runflow.py:845/1113/1281`共同消费此结果；生产事件 `production.py:436-438`使用返回context_id构建，可能沿新身份继续。

### 4.2 公开复现与证据限制

专项实际公开 `start_run(after_claim)→resume_run`，使用三个新的合成库；正常控制、旧id篡改控制、自洽新id保留旧ctx存储键三案已完整执行。错配案保留了直构unknown+实体值，不能称checked正规新内容。拟追加的一案checked正规新内容判别控制被运行平台内容风险筛查拦截，**未执行、未计通过或产品失败，没有换代理重试该执行**；只读封包续跑。平台仅给“possible cybersecurity risk”，不推测额外理由。三个已完成公开案已直接证明引用不变量违约，定P1不依赖未执行控制；该额外fixture列下一轮正负控。各案完整输入、H07封包、前后表/产物、错误与事件在 `mimo/`，根只读提取在 `root_audit/independent_binding_readonly.json`。

- 正常上下文合法resume可产事件；合法unknown经checked构造value=None。
- 改事实并保留旧payload context_id，即使重封H07，也被 `context_content_identity_mismatch`拒。这证明现有自hash守卫有效，**不是它完全失效**。
- 改事实并重算payload context_id、H07，**地址和行动context_ref仍旧**，当前共同load返回新context_id；公开resume接受并真实提交事件、派生后续上下文。自洽新内容应存到新地址并显式沿新引用，不应覆盖旧引用消费。

原专项unknown+实体值案实际audit条件为unknown、admission为retain_conditional/R5；正常对照整体audit也unknown/R5。只在必要unknown键等范围有差异，**不宣称已证错误compatible、verified/R6或科学终点翻转**。低层顺序差异与本P1地址绑定分开；即使本案化学判决保守，接纳旧地址下不同内容身份仍违反既定权威绑定契约。

实际根引用三案均为 `pc_a72ff6b1f27d9335da52`。错配案存储地址/外层task仍是 `ctx:pc_a72ff6b1f27d9335da52`，payload及load返回却为 `pc_d9978ff5d99526ca0c46`；resume成功，events **0→1**、search_actions **1→5**、search_commit_records **0→5**、budget_reservations **3→13**。真实事件 `ppev_54b49bbef300cf40cf4d` 使用从错误父身份派生的子context `pc_cb6c6735e241fb855c45`，并非直接把root新ID当事件context_hash。错配artifact在resume后仍与原mutation envelope相等，未被改写覆盖。

保留旧payload ID的负控load/resume均拒 `context_content_identity_mismatch`，events **0保持**；但search_actions **1→2**、search_commit_records **0→1**、budget_reservations **3→4**。旧id拒绝发生前，resume已完成root retrieve等相关业务，所以**不能写15表零变化/整个resume零写**。本P1最低要求是在实际消费这份坏上下文前拒，之后不派生、不audit、不提交坏上下文事件；合法恢复保持。任何既有无关retrieve/claim写入须如实逐案登记。原错误events表名造成的只读计数更正保留，不以旧“0 events”观察代最终真实events表。

### 4.3 最低收口

在共同load_context的H07+from_dict完成后、返回/派生/评估/审核前，校验请求context_ref与恢复payload context_id相同，不拿新selfhash洗掉旧地址身份。结构化拒绝须披露expected ref/actual id，保全坏artifact，不覆盖、迁移或默发新的有效引用。逐一覆盖decide、expand、scenario_transition及其他实际复用入口，复用同一守卫而不各自造规则。

保留合法roundtrip、新内容新ID且新地址、parent_context_ref链、正常resume/子上下文/场景转换；旧selfhash不符继续拒。增加两个判别负控（畸形unknown自洽新ID、checked合法新内容自洽新ID却旧地址）与合法新ID正控。**不修改冻结path_context物种三分、unknown正规化、criteria-v1正文/FREEZE_RECORD；不借此全面拒绝合法重建或开启S5b。**

## 5. mimo v23：五处文案成立，恢复语义与绑定分开裁定

**头条文案项成立，归P2文字同步且为proposed evaluation-3/template-3冻结前置项，不是当前条件实现P1。**五处为evaluation.py:77-78、1136-1138；preregistration.py:20、137-141；profile.py:267-268。现行“known×unknown按已知裁决”无范围限定，须限定到物种键；删合法链“顺序相关”尾巴。

旧四species两序公开案已知present→compatible、absent→essential_conflict；新增temperature/oxygen_regime四公开两序均condition_unknown。专项另对七键known_present×unknown双序及三物种known_absent×unknown双序合计20 checked对照，合法两序结果一致；非物种任一适用unknown走unknown，只有物种按实体已知事实裁决。不要把“非物种键”全部称数值键，oxygen_regime/matrix是枚举/标签。

`ConditionFact(**dict)`恢复不经checked正规化读码属实；typed直构→from_dict→persist/load保留unknown+实体，低层两序可compatible/unknown。普通改存储facts保留旧context_id不能绕过内容身份守卫，已公开实测拒；mimo不能只凭恢复构造行宣称任何任意篡改都可达。**自洽新ID仍用旧存储地址的具体公共链可达已确证，另按§4绑定契约定P1。**未知实体值如何正规化/校验、冻结物种语义如何调整仍归用户/teacher P2，不用本轮身份绑定修复代选。

其他建议处置：

- 空要求unit按键规范值的代价需披露：作者实际想写298K却省略unit，程序只能按temperature_C声明读298C；不猜作者意图。不把空单位全面降unknown，也不新增K/F换算。
- condition_unknown枚举、实体单位不可区分装饰错误与浓度阈值意图的原因、value仅展示勿eval，均P2落字；JSON原生value_raw和按披露kind聚合是后续增强。静态换算公式非本轮必要验收，实际换算须teacher另定。
- **分母尚TBD**：当前environment_conflict_rate只有分桶、无标量。本审不采信mimo“分母含unknown”作为已定科学分母；准确文字是未知桶独立披露、unknown不等于无冲突，不从桶数自行承诺正式冲突率。
- “声明越具体必然只降档”的宽泛单调性不能照抄：仅固定其他输入、空unit→显式不支持unit这一组行为可证。合法纠正单位/改变key/value可有不同结果；不宣布任意声明编辑总序或科学定理。
- 事实侧species+mg/L仍按实体裁决的窄面已checked实测compatible；只证实体、不证浓度阈值。改冻结事实侧单位纪律/restore正规化需用户/teacher裁定，不自动修；同导出其他事实单位不构成本条单位证据。

mimo三判断面关于要求单位回修的同意获得执行互证；“未发现P1”限其只读观察，不能作为全系统无缺口背书。五处行号与当前源已抽验；不改其原始回应、不替历史评审补执行。

## 6. 已关闭项、交付一致性与晨报事项

- S5A-01六scope封顶、strict/CN合法控制、S5A-03必要节点及exact/superset/共同产物/独立备选、S5A-04四出界拒零目标文件/一授权根合法写，fresh旧脚本逐案保持。写内容仅synthetic-placeholder-not-gold，不含真实金标。条件18同源+2required_absent保持；ISO-01的17常驻正负控在全量，S4 C01-C04/B4/版本门及S3已证用例通过。仅§4的新首消费绑定反例重开对应契约，不推翻其他既有修复。
- 冻结正文SHA `7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4`，FREEZE_RECORD SHA `6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610`；path_context SHA `971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d`，均与直接父字节同。production/runflow、S3/S4/audit/legacy关键源亦未因单位回修修改；**字节不变不豁免本轮新证漏洞**。
- 交付1105/15+106/1706+9+17/305及6/6、4变13保持与独立执行一致；其“单位收口”确认。若解释为继承全部首消费闭合、阶段P1清零则不成立，见§4。实施证据实际78文件、76附件全纳SHA，根只排manifest/SUMS，完整核验通过；封包前记录的HEAD不替待审提交身份。
- 遗留P2：五处文字；A1有限参考根配不上却假native_missing的保守不评归因、participant_list_status未消费/集合exact仅声明集合、roles/coefs/occurrence及unknown==unknown参考语义、聚合因果/kind子桶、point值basis、endpoint helper/死键、R16样本≠确认事件，按上一轮范围继续登记，不捆成新阶段功能门。

晨报/交接仍待用户或teacher：任务书§10.1二十项TBD，含题源/金标口径/独立性、dev/298及known/unseen样本与分母、阈值/CI/费用、条件低层语义/负要求/单位换算、有限根配对及partial清单/occurrence支持。没有真实指标数值、不外推dev/298，不代定阈值/分母/费用。**S5b未授权不启动**；proposed评测契约也不由本审自动宣布冻结。

## 7. 永久证据与最终裁定

目录：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s5a_codex_r3_2026-10-09/`。

- `execution/`：三suite完整argv/cwd/固定env/exit/stdout/stderr/JUnit、121 nodeid父分类、305前后/current批准输入SHA/谱系、9skip/17deselect、两树legacy真实产物与52聚合、源继承/缓存/准备事件。
- `conditions/`：六B1/17桶对照、旧20/身份/必要节点/5写边界与追加四非物种公开案；64公共evaluate、71规则断言，43合成库末态全表、564产物及43嵌套业务manifest。只有两identity库另有评测前后DB/全表零变化证明，不把其他末态快照叫零写证据。
- `mimo/`：五处文字/20 checked单条两序对照（不称20公开run）；2个typed直构→from_dict→persist/load低层两序；1个事实单位实体窄面；旧ID篡改低层控制及3个完整真实公开start/resume案。真实events更正、前后业务表、输入保全与source原文齐全。追加checked正规新内容公开案未执行，单列平台事件，不计控制通过；不夸大为全部合法重建反例。末态或已发生的无关retrieve写不冒称全表零写。
- `root_audit/`：134输入/4537旧证据SHA及集合前后守卫、冻结/旧包/实施包核验、原mimo/交付材料、账号中断续跑登记、只读复核/组装发布脚本与收据。`report.sha256`绑定本报告。

所有脚本必须复制fresh tmp再执行，不在永久证据原地建库；归档完整输入/输出、固定相关env而非含凭据的全部ambient环境。无socket仪表的探针不声称全局网络计数实测零。SQLite二进制、symlink、pyc/pytest缓存不入包；根manifest/SHA256SUMS覆盖所有附件与嵌套manifest/子包控制文件，**只排自身这两个根控制文件**。

**最终：S5a r2不通过，P1=[S5A-05]；S5A-02正式关闭。**五处文案为proposed冻结前P2必同步，可在本次有限回修搭车；G01历史日志缺失P2，不影响当前fresh完整数字采信。下一轮只修共同上下文首消费引用绑定；其他已关项、冻结条件语义、S5b及科学性能范围不扩大。

## 8. 下一轮有限回修提示词

```text
你在 /Volumes/CC/Enzyme_Agent/dependingv43 实施S5a r3有限回修。
只修本报告S5A-05，不重开已经关闭的S5A-01/02/03/04、S4/S3其他旧反例。

必读：AGENTS.md；本报告§4；S3任务书§3/§7首消费继承；冻结判据四现义。
先列load_context及decide/expand/scenario_transition等实际消费入口矩阵。

P1：共同load_context读H07并恢复PathContext后，实际消费前核
requested context_ref == payload/recovered context_id。
selfhash重算正确不能替代旧引用绑定；错配结构化拒，披露期望/实值，
保全坏artifact，不重封覆盖、不猜迁移、不默发新引用。

用本审mimo专项复制到fresh tmp的原输入逐案验证：
下列1–3已有本审真实公开输入；4是本轮未执行的建议补控，5是须构造的合法新地址正控，
4–5不得冒称本审已执行。
1 正常checked unknown None和正常公开resume保持；
2 原context_id+改内容继续context_content_identity_mismatch拒；
3 自洽新context_id+重封H07但旧ctx存储键，在首消费拒；
4 checked正规合法新内容+新context_id但旧地址，同样拒；
5 合法新内容新ID新地址+parent_context_ref链允许，正常子ctx/场景转换保持。
拒绝后不派生/评估/audit/提交坏上下文事件，保全输入；
已有无关retrieve/claim写入逐表披露，不伪报整个resume十五表零变化。
在39d739d直接父回修基线上跑新增同字节红绿；行为红/字段/版本/collection分开。

允许搭车P2文字同步（不改变冻结条件实现）：
evaluation.py两处、preregistration.py两处、profile.py一处known×unknown
限定物种键；非物种任一适用unknown仍unknown；删合法链顺序相关尾巴。
typed/restore低层语义登记P2，不能以文字宣称首消费绑定已通过。
condition_unknown具体枚举、空要求unit canonical-by-key代价、value仅repr展示、
实体事实只证存在不证浓度、指标只分桶且正式分母TBD准确披露。
不用‘所有声明越具体只能降档’或‘分母已定包含unknown’作宽泛承诺。
文本/契约/策略/code_identity变化按现有版本规范登记待审，不默改旧冻结契约。
不改criteria-v1/FREEZE_RECORD/path_context冻结判决；不增加换算、单位推断、
负要求或物种语义新门，不启动S5b、不访问真实题面/金标/封存run。

交付：逐入口→行为→正负控→原反例翻转；PPV1全量、父新增同字节红绿、
G01安全隔离305谱系并逐项披露新增/变更/9skip/17deselect、输入SHA前后。
历史首次G01日志丢失只登记；每次尝试新输出根保留argv/env/exit/完整日志。
新证据ppv1_s5a_rework_r3_<日期>，嵌套manifest全部纳SHA，只排根控制文件；
生成自包含无金标mimo v24请求，按既有主会话通道送审（实施子代理不自调）。
v4.3本地提交，git add显式路径；不push，不带旧评审/mimo回应/证据/用户AGENTS差异。
审核侧旧报告/永久证据一律不改，科学性能pending，全部teacher TBD不代定。
```
