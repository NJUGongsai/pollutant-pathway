# pollutant_pathway_v1 S5a 正链复审

日期：2026-10-09，Asia/Shanghai。正链 Codex 主审与协作子代理独立执行；账号额度中断后续跑，完成结果复用，不调用外部模型。

**裁定：S5a 不通过，P1=[S5A-01, S5A-02, S5A-03, S5A-04]。**mimo v21 报出的参考身份 scope 越权、条件口径分歧均成立；另在本轮既定工程契约内实证必要参考参与节点漏核及输出写目录越界。S4 完成交接与已关项保持，不重开。科学性能保持 pending；本审不确认 S5a 的 `interface_verified_only` 阶段验收，不启动 S5b，不代定金标、阈值或分母。

## 1. 固定验收、身份与中断续跑

- HEAD：`2e1e7af3c4bef9e98db9481167a835cabd3c088e`；直接父：`a19960f9012ceb326a1c40d5906861f223124946`。
- 验收任务书：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md` §14、§15 S5a、§16 S5-01～28、§12。仅工程接口/合成数据规格，S5b 不在授权范围。
- 交付：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5A_DELIVERY_2026-10-08.md`；请求/回应：`docs/mimo_ppv1_chem_review_request_r21.md`、`docs/mimo_ppv1_chem_review_response_r21.md`。
- 继承：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4_CODEX_REVIEW_R4_2026-10-08.md` §5/§7/§8。P2 搭车允许披露与常驻合成测试，不改变冻结判定语义，不增加科学验收门。
- 实际环境：conda `depending43`，Python 3.11.16、RDKit 2026.03.6、SQLite 3.53.4；各包记录 argv/env/cwd/exit/schema/profile。新接口契约 reference-graph-1、split-manifest-1、evaluation-1、preregistration-template-1；profile-20、donor-diagnostic-10。四契约对应三个新模块，不能将它们说成四次科学冻结。

初始守卫为 **2026-10-09 00:39:05+08:00**：131 项源/PPV1测试/文档输入和旧永久目录 **2725 文件 SHA**。用户报告账号用量限额中断、约3000行已有验证输出、重置时间02:47；这些是用户事件说明，不是本审精确测量的执行量或账户系统日志。中断精确时刻没有独立记录，不编造退出码。续跑首次工具时间 **02:51:55 CST**，正式续跑守卫 **02:53:14+08:00**；HEAD/父、131输入、2725旧文件及工作树状态全部相同。

中断前 PPV1、完整父基线、G01、legacy、身份/边、原8+3同位素、出口继承、20条件、8真实终点、5写边界及矩阵执行已有完整输出/退出码。三包已封闭；条件包只缺总结及封包。续跑只做只读结果核对、缺失元数据/README与封包、独立只读论证复核、报告/发布守卫；**不重跑任何已完成业务链或 suite**。限额中断不是产品错误。

保留的 `execution/README.md` 写“本轮未中断”，指该执行子任务在主会话限额前已完成，不能解释为主评审未中断；本报告、根README与 `root_audit/resume_event.json` 记录本次主会话中断—续跑。

所有业务在 fresh `/private/tmp` 源/vendor/pyproject副本，主命令 `-B`、`PYTHONDONTWRITEBYTECODE=1`、pytest cacheoff；父 detached 源与子源用同字节当前测试和同根批准 v3 镜像。G01 只用历史安全白名单及新增普通工程输入，不在真实仓 `tests/` 全量运行。没有访问金标/题面/封存逐题 run/dependingv4/原 v3 评价资产，没有外部模型、LLM判分、commit/push；仓内仅新增本报告及证据目录。

## 2. 独立执行数字和证据分类

| 项目 | 本审实际结果 | 解释 |
| --- | --- | --- |
| PPV1 全量 | **1045 passed / 0 skipped，exit0** | 40测试文件；976既有＋69新增（20 schema＋32 evaluator＋17 isotope） |
| 父 a19960f 同字节全套 | **12 failed / 981 passed / 2 collection errors，exit1** | `--continue-on-collection-errors`；两缺模块导致52用例未收集/未执行，不能叫52红或52绿 |
| 12失败根因 | **2披露字段 KeyError＋6版本字面量＋3 checker注册间接失败＋1 delivered_stages身份字面量** | 新isotope文件3失败＝2字段＋1版本；更新文件数量不等于失败节点数量，不能把12节点写成3行为＋7版本 |
| G01 安全隔离 | **1647 passed / 8 skipped / 17 deselected，exit0** | **303 输入**前后与当前批准来源 SHA 全同；不采旧控制器 expected=1648 作为结果 |
| S5-01～12 原矩阵例 | **15 passed / 0 skipped** | S5-01四节点，S5-02～12各一节点；按明确nodeid独立执行 |
| S5-13～28 原矩阵例 | **19实际函数断言完成，exit0** | 14函数有35次捕获API调用，5函数仅局部schema/模板/分类器断言；多节点覆盖同一行，不把函数数当矩阵行数或19条完整公共链 |
| 身份/边专项 | **17公开评测变体＋6必要节点案＋1立体单元控制完成** | 最低契约输出断言 **8失败/7正控通过，exit1**；六scope＋两必需节点缺口，采集脚本exit0不等于产品通过 |
| 条件专项 | **20公开评测案完成** | 18可同源对照＝**5同义正控＋13分歧**；另2要求侧known_absent不能直接表示，不计作冻结对照 |
| 终点/写边界 | **8真实终点控制＋4分类器局部案；5写边界案完成** | 局部分类器输入不冒充真实S4链；写边界两相对路径真实越界、两绝对路径拒、一个合法正控 |
| 继承 | **原8+3同位素及19+6出口观察完整复用新执行** | 11案判定/准入/提交方式与R4相同；25出口观察不是25漏洞 |
| legacy | **两树4产物逐字节相同、标准52聚合不变** | `18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6` |

G01 的8 skip：v4 parser对照根缺席1；v2 provenance/summary缺席2；冻结v3真实评价依赖缺席5。17 deselect＝16 slow＋1显式排除charge/evaluation fixture节点。逐 nodeid、理由、命令和303输入见 `execution/README.md`、JUnit/缺席JSON。缺席不算通过，不能补读红线依赖来凑全绿。提供的G01准备控制器与条件包复制输入里“70新/1648”是陈旧预期；实际69新/1647以本审日志为准。

缓存口径：主命令禁字节码/pytest缓存；`execution/cache_observation.json` 仍观察到G01隔离树内测试子进程产生7个pyc，当前PPV1及父隔离树为0。303源输入SHA未变，7文件不归档，未写真实仓或旧证据；不能称所有子进程缓存均为0。此隔离执行偏差如实保留，不用它改写测试数字。

以上均合成规则级工程数字，不外推 dev/298，不是科学通过线、漏洞数或真实路径性能。额外探针不与1045或G01相加。

## 3. S5-01～28 固定矩阵独立验收

原矩阵标准夹具都有独立执行；基础正控全绿，但不足以抵销同契约公开反例。下表“基础通过”限定已执行基本场景，不代表对应规则已对所有消费输入闭合。

| 编号 | 本审观察及范围裁定 |
| --- | --- |
| S5-01 | 合法/缺字段/坏版本/坏文件均按基本schema契约处理；参考侧多视图与证明范围不足见§4、§5，不把字段存在当完整授信 |
| S5-02 | A→B、A→C保持两个备选事件；未合并共同产物 |
| S5-03 | 已有共同产物/报告K正控保持；**新增合法完整参考边的必需反应物/共同产物未匹配仍授strict，S5A-03未达** |
| S5-04 | distinct occurrence保留；同state多参考来路的计数/分母P2，不要求本轮一一注入映射 |
| S5-05 | 同研究记录归一个明确source group；不虚加独立支持 |
| S5-06 | 来源身份/独立性unknown保持unknown；分母最终TBD不冒称已定 |
| S5-07 | 同研究跨开发/留出触发blocked_leakage，零聚合 |
| S5-08 | known/unseen直接证据重叠阻断，零聚合 |
| S5-09 | 未画参考边不自动记化学错误，覆盖限制单列 |
| S5-10 | 严格结构与中心证据分轴；真实样本audit_unknown_checks=9、conditional事件2、confirmed计数0，不因结构strict授R6 |
| S5-11 | 同位素/电荷/立体严格不同的CN旁证正控正确；**参考自声明cn_only/partial/unknown仍授strict，S5A-01未达** |
| S5-12 | 已知不同step_scope为structure_only；unknown==unknown进入strict的proposed文字不一致另列P2/待裁定，不把它说成净反应已核实 |
| S5-13 | 缺事实基本例为unknown；**单位未知/无源必要性等被越过，S5A-02未达** |
| S5-14 | 明确同词缺席/已知相反基本冲突控制正确；**异值/数值缺席、多事实矛盾被误计conflict或compatible，S5A-02未达** |
| S5-15 | 历史source_conditions原样保留；场景信息不改写为当前事实；条件合取/适用范围不能再由首条事实代替 |
| S5-16 | unknown/partial/conditional基本例不计confirmed、不自动计错；R16字段名实及独立分母列P2，不能冒充独立科学确认 |
| S5-17 | 仅CO₂/无证据真实链不授矿化；8真实S4终点控制保持；评测helper漏检的伪支持输入列P2，不倒推S4假支持可达 |
| S5-18 | budget/depth停止不变成终点；停止与化学终点分账保持 |
| S5-19 | 上游unresolved不被下游recorded洗白；实际S4终点守卫保持 |
| S5-20 | 预算漏展开单列，不静默删分母；正式分母TBD |
| S5-21 | dev/298混合拒或分报告，不输出无题域总分 |
| S5-22 | known/unseen混合拒合并，分轨保留 |
| S5-23 | TBD不生成科学通过；程序永不发evaluated_* |
| S5-24 | 重复同输入结果/hash确定性一致；中断后不重跑已完成此例 |
| S5-25 | 自由文本不能改变结构评分决定，评分代码无模型裁判 |
| S5-26 | provider默认关、real无授权先拒，基本例无请求/费用；不从标志推导任意自定义callback网络全局为零 |
| S5-27 | 普通目录基本拒绝、合法授权根基本接受；**错cwd/符号链接相对路径实际越界写，S5A-04未达** |
| S5-28 | 无native读取通道/导出缺席为pending_no_independent_data，不伪造正式科学评测 |

任务书§14.1的读取/确定性/备选/共同产物/occurrence/stop/budget/损坏输入基础均已验证；本轮四组P1仍属于这些接口验收及既有范围诚实、条件、写入边界，不要求真实机制库、科学性能、未授权S5b或新teacher阈值。

## 4. 四组 P1 与最低收口

### 4.1 S5A-01：参考身份许可范围未消费，旁证升格为严格

出处：任务书§7.2/§8.2/§11、S5-11；冻结v1“旁证不叠加升格”。mimo面一发现**成立**。

`evaluation.py:590-591`只把`structure_identity_scope`抄为披露；`:597-620`无条件算结构相等并授`strict_structure`；`:648-652`进入`strict_by_node`供边匹配。真实`start_run→native_export→ledger首读→evaluate_scientific`六scope分案：cn_only/partial/unknown，每类分别只限中间体/限制全部参考节点；均仍给strict节点及两条matched_strict边，聚合`reference_edge_recall.matched_strict=2`、关键中间体strict_structure=2。合法strict、严格不同的同位素/电荷CN控制保持；立体对照是单元控制，不能说它也走了native公共链。

**最低收口**：严格身份比较的“内容同值”不能突破参考声明的许可范围。只有许可strict scope进入严格节点档、边strict候选和严格指标；cn_only/partial/unknown保留旁证/limited/unknown及原因，不全面拒绝合法图，不以附risk文字仍授strict。原合法strict和真实CN旁证控制保持，公开入口与聚合一并验收。

证据：`identity/outputs/summary.json`、逐scope完整图/输入/输出、`logs/contract_assertions/`。六最低断言失败不是六个独立漏洞。

### 4.2 S5A-02：条件评测另写简化规则，同名桶与冻结语义不一致

出处：任务书§9.5/§14.1、S5-13/14/15及冻结判据四。mimo面三发现**成立**，不是模型自行执行的结论。

`evaluation.py:790-815`仅取`matching[0]`；不读单位、源必要性、全部适用事实；absence一律转冲突，值用字符串/单个连字符比较。冻结同源实现`path_context.py:761-762`无源necessary→unknown、`:774-777`多事实矛盾→unknown、`:790-803`单位三态、`:819-837`数值/异值absence→unknown，仍在本批原字节保持。

20案由真实public start→ledger导出首读→评测完成。18有可比较冻结结果，**5同义保持、13分歧**：

| 输入族 | 公开evaluation | 冻结同源评估 |
| --- | --- | --- |
| 缺事实/同值present/相反present/同值absent/规范单位 | unknown/compatible/conflict/conflict/compatible | unknown/satisfied/conflict/conflict/satisfied；5正控同义 |
| 字符串异值absent、数值absent、异实体absent | essential_conflict（3案） | unknown，不能由另一值缺席推必需值缺席 |
| 温度无单位/K/F | compatible（3案） | unknown：source_unit_unknown/unit_mismatch |
| 矛盾事实正/反顺序 | conflict或compatible（2案） | 两次均unknown，不能首条说了算 |
| 必要性source_refs为空 | essential_conflict（1案） | necessity_unsourced_not_gating→unknown |
| 零点/负区间/区间事实 | conflict（3案） | 已声明point/range语义下satisfied |
| matrix不同未注册标签 | conflict（1案） | unresolved→unknown，不把文本异名当化学矛盾 |

**映射限定**：两接口不是字节等形。对照明确将参考range字符串规范到lo/hi，并给冻结Requirement显式basis/value_basis（源声明necessary、point/range/entity）以表达同一测试意图；原适配全文保存，不能说18案都是原schema同字节。其中单位/absence/多事实/必要性缺口已独立足以成立；值解析案同时暴露schema映射/表达能力不足。另2“要求侧status=known_absent”在冻结Requirement没有直接对应字段，原输出标`not_directly_representable`；不算冻结分歧案，列待明确的参考schema语义，不能代teacher发明负要求。

**最低收口**：登记并消费可审计的ConditionScope→Requirement/事实映射；可表达部分沿冻结同源规则，适用场景/阶段/实体、单位、必要性来源和所有事实必须共同消费；不能表达时给机器unknown/unsupported及缺失维度，不默认冲突或相容。不要求遍地新数值转换/label注册库，不改变历史快照或冻结正文。合法同义控制及不可映射披露保持。

若另选“评测侧独立版本口径”，涉及用户/teacher裁定：必须先裁定、独立命名/version与分歧报告，不能静默沿用同名essential_conflict解释为冻结一致。本审**不替用户选该方案、不自动升criteria-v2**。将字符串简化分类原样挂牌不构成收口。

证据：`conditions/results/conditions_summary.json`及20完整分案、`conditions/scripts/probe.py`和实际命令；13分歧逐案仍输出interface_verified_only，该程序标志不等于本审放行。

### 4.3 S5A-03：必要参考节点的空命中被union吞掉，假完整边匹配

出处：任务书§7.4、S5-03、§14.1/§11不得自动把部分结构匹配变成严格结构通过的要求。这是同既定匹配契约的新执行证据，不是新增科学偏好。

`evaluation.py:667-676`把整侧节点命中集合union，只要求一侧整体非空；某个必需节点为空就消失。`:712-724`再用缩小集合授exact/matched_strict。两核心案在原合法declared_complete边分别增加一个必需反应物或共同产物C；**from/to与participants全同源完整、schema通过**，该必要节点unmatched，真实原CCO→CC=O事件却仍matched_strict，聚合仍strict=2。全回执包含真实ledger-native载荷/事件与再次校验的同一参考图，不是伪造native。

**最低收口**：每个声明必要from/to节点都须有许可的严格命中才能授完整strict；空集合必须保持为未覆盖/unknown，不被union删除。参与物完整清单与实际消费来源要闭合；不能只证明缩小后的子集精确。合法exact及partial_subset/superset控制、共同产物、独立备选保持。

其它仅participants新增但from/to未列的多视图案单列P2/表示语义同步材料；本P1不依赖该schema歧义，不要求任意骨架投影字段全部强等，也不顺带新增角色/系数门或occurrence一一对应门。

证据：`identity/outputs/required_node_reactant_full_receipt.json`、`required_node_product_full_receipt.json`、`legal_exact_nonexact_controls.json`；两最低断言失败。

### 4.4 S5A-04：输出写守卫用未解析路径名授权，越过显式repo_root

出处：**S5-27**、任务书§4.2，公开`persist_evaluation_output`。不涉及实际金标访问；仅用`synthetic-placeholder-not-gold`字面内容在fresh tmp仿真目录测试。

`evaluation.py:1662-1670`已解析target但相对repo_root失败后仍回退原相对字符串，`:1671-1680`凭白名单前缀授权并最终写原target。五案完整：

- 显式repo_root=A、cwd=B，相对`reports/phase_s1_hit60/dev_gold/report.json`解析落B，仍返回receipt并真实写B。
- A内授权名目录为symlink指向A外fresh目录，相对target仍获准真实写A外。
- 两同形absolute target分别拒`gold_content_unauthorized_path`、零新文件；合法A内relative正控接受。

**最低收口**：核验与写入必须使用同一个解析后实际路径；明确relative target基准（相对repo_root规范化并实际写那里，或相对cwd并在出界时拒），禁止解析出界后按原字符串放行。任何实际逃出授权root/授权子根的symlink路径先结构化拒，零新文件/目录；未指定root也需清楚一致的根规则。保留合法授权目录及普通非敏感写入控制。无需新增内容DLP、完整沙箱、敌意并发symlink-race防御或读取真实金标来证明该边界。

证据：`conditions/results/write_boundary.json`、`scripts/write_boundary_probe.py`、完整日志；记录写前不存在/写后文本与SHA。不是“可能越界”的假设，也不能因absolute路径基本例已拒就说S5-27通过。

## 5. mimo/交付一致性、P2与晨报决策项

mimo v21为只读读码，所有执行类主张仍按来源登记。本审将其面一、面三P1采信至上述程序证据；四面条件/建议不自动升级阻塞。行号抽查与当前名称/行为一致；冻结条件来源位于path_context而非元素账，必要性来源与数值basis映射限定必须保留。主会话1045和交付G01不能换署成本审执行；本审有自己的隔离日志。交付28/28仅基本夹具，不能代表本轮新反例满足原契约。实施方17附件封包按其attachments格式只读核验，全文件纳SHA，仅排两个根控制文件；该实施包实际没有嵌套manifest，不凭格式声明虚报存在。不将实施封包校验冒充程序执行。

**后续P2/待裁定，不能冒充这四P1的新增门**：

1. unknown==unknown进入matched_strict已执行；不同scope的结构内事件也被outside_reference桶记两项。同步proposed文本/披露范围，冻结前明确已知scope严格档与结构匹配档、参考内scope失配的分桶；不因此宣称净反应已核实。
2. 系数2对真实1、角色异标、参考participant_list_status partial/unknown不改变strict已执行。当前strict只比参与state集合/scope，不承诺角色与计量核验；预注册“角色/系数完整匹配”必须与实现证明范围同步。是否引入这些新评分轴、部分参考超集分桶属匹配口径裁定，不能暗中借本轮加科学门。
3. occurrence保留方向成立；同一预测state可命中多个参考来路，计数基数跨档不一。禁止无说明跨occurrence求和；双轴、共享state披露、独立来源/分母去重属后续口径。
4. endpoint helper的direct/观察窗/检出范围漏核、handoff用evidence_basis死键、supported_terminal无证据兜底等读码/单独分类器问题成立；但8条**合法真实S4→eval链**中direct充分可supported_mineralization，其余无证据/inferred/model+inferred/缺source/缺window/缺detection均unknown、direct_handoff为handoff，未复现S4假支持。按既有范围列P2，不用伪造callback证明S4漏洞；冻结前同步“三件最低口径”与实际检查，不将bookkeeping单字符串当科学矿化证书。
5. R16已由公开空池run互证：events=0却`confirmed_claim_events=1`，当前是样本数而非独立确认事件数。列字段名实/后续分母P2；不能作科学确认分母。保留S5-16基本conditional例confirmed=0，不把空池这一名字错误说成真实酶边已确认。
6. supplied G01 70/1648与派单父红“3行为＋7版本”精度更正见§2；交付实际表称3个P2节点＋9个版本关联节点，12总数闭合，但前3实为2字段＋1版本，后9也需按nodeid细分。模板/free-form文字不是实际执行证明。

**晨报需用户/teacher决策**：任务书§10.1二十项仍TBD，题源/金标/可评分参考、来源独立性、dev/298与known/unseen样本/分母、阈值/置信区间/费用等均未代定。另须明确：条件沿冻结同源还是经批准的独立评测版本；无法表示的负要求/数值basis；proposed scope、角色/系数、参考不完整与occurrence双轴；endpoint独立复核边界和confirmed分母。工程修复可以先收四P1，不能把这些决策默认为已冻结或启动S5b。

## 6. S4/S3继承、搭车P2与永久证据

冻结正文与FREEZE_RECORD逐字节不改：正文SHA `7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4`，记录SHA `6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610`。legacy/G2/AtomTool/出口及S3关键源保持，与实际回归/有限公共输入互证。既有no-ledger仅文件级证明边界及B4合法done无production_report不加新门。

R4搭车四件确已落地：四处文案与profile过时闭流句同步；被增/删原子isotope记录补单侧标签；audit axis_detail携带**复算**extra_changes/center_property_deltas；17常驻合成回归钉同位素方向/对称与披露。donor10/profile20及输出schema/字段有变化，不能说整体字节零改；公开8+3判定/准入/提交方式保持，不新增判定语义。混合中心外仍violated/R5v，生产可按既有retain留存但不R6；product_coverage=full只是完整产物绑定覆盖，不洗中心violated。标签仅表示层核素标签，不核实样品组成、核过程或机制，self-contained重算不证执行历史；工程数不外推dev/298。

永久目录：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s5a_codex_2026-10-09/`。

- `execution/`：三suite完整JUnit/stdout/stderr/argv/env/exit，40同字节测试/2workers、303SHA前后与来源、8/17缺席nodeid、legacy两树产物/标准52身份、schema/runtime。
- `identity/`：S5-01～12独立15节点，真实评测变体与完整图/native/业务表、六scope/两必要节点失败断言及合法exact/nonexact控制。
- `conditions/`：20条件的同源映射与18/2区分、矩阵19函数断言、8真实endpoint、R16、5写边界与写前后文本；只合成占位，不含真实金标。
- `inheritance/`：旧脚本逐字复制后新执行8+3及19+6，完整input/proof/audit/admission/表/schema/artifact、四搭车P2、旧与新语义签名。
- `root_audit/`：131输入/2725旧永久SHA，初段/续跑/发布守卫、材料片段、只读复核与封包收据；`report.sha256`绑定本报告。
- 根manifest/SHA256SUMS覆盖所有实际附件、嵌套业务manifest与子包controls，仅排根自控制文件；各子包独立封包并经只读核验。

原脚本硬编码旧HEAD/未重跑标志仅历史文本，实际argv/metadata钉当前身份；新增stageflags不当ledger证书。继承后处理首遍把donor9/10 token及生产diagnostic路径当语义差异，断言停止；修比较器后只读同一完成输出核验，未重跑链、未改原理由或判据，初次日志保全。限额后条件仅补metadata/README/封包，不伪造缺失exit；所有原命令已有退出码。通用只读封包校验器因实施方采用attachments而非files键报KeyError，适配原格式后核验，不算产品失败或红绿行为。

临时库不入包：identity/inheritance保存全表JSON/schema/SHA，conditions保存完整业务输入/reader载荷/API返回，不宣称每份库逐行快照；suite表计数不冒称全行。只有conditions guards四个早期授权控制有socket仪表且计数0，未调用reader；其余原network_calls=0字段未经socket仪器化，不能外推全局网络流量。没有永久目录原地写库/缓存、没有修改旧证据；发布守卫限定新两路径。

## 7. 最终裁定与下一轮边界

**S5a 不通过，四P1如§4。**原S4/S3已关项保持，四搭车P2完成；接口状态/无模型评分/费用默认关/确定性等基础可确认，不能因这些和1045绿替代范围、条件、完整匹配与写边界验收。当前程序发interface_verified_only只是程序模式标志，本审尚不确认阶段放行。

下一轮只收四组已有接口缺口，保留正控及诚实unknown/partial、身份版本、源快照与继承。阈值、金标、S5b数据、费用、provider、teacher分母和独立科学口径仍另行裁定。本审不修改冻结正文、不自动选条件独立口径、不要求科学性能通过后才能修接口。

## 8. 有限范围回修提示词

```text
在 /Volumes/CC/Enzyme_Agent/dependingv43 做S5a有限回修。
基线2e1e7af3c4bef9e98db9481167a835cabd3c088e。
必读AGENTS、本报告§3/§4/§7、S5任务书§14/15/16/12、mimo v21。
只收S5A-01/02/03/04；S4/S3、ISO-01保持关闭，不实施S5b，
不触金标/题面/封存run/v4/原v3评价资产、不外模判分/真实费用。

先列validate/load/match/evaluate/aggregate/persist入口及消费事实矩阵。
四同根规则须在适用入口同源闭合，保留基础28场景及合法正控。

01 参考identity scope先消费许可，再授严格档；cn_only/partial/unknown
不得因内容相等授strict_structure或进strict_by_node/严格指标。
保留旁证/limited/unknown与合法strict，不全面拒绝带标签或有限图。
复用identity六scope公开输入，节点→边→聚合逐层翻转。

02 登记ConditionScope→冻结Requirement/事实的合法映射。消费同源
条件规则：单位三态、实体/数值/异值absence、多事实保守unknown、
necessity来源、适用场景阶段和声明value_basis不能被字符串首条替代。
缺少表示能力时unknown/unsupported及缺失维度机读披露；不要推断
负要求或发明label库/换算/必要性。18可比case保留映射限定、5正控；
2 required_absent无直接映射单列，不伪称冻结矛盾。若拟选独立评测
条件口径，先报用户/teacher决策，未经裁定不能默选/改冻结正文。

03 每个声明必要from/to参考节点须有许可严格命中才可完整strict。
不得union吞空节点再把缩小集合标exact；必要参与物完整清单同源
消费。复用2个合法完整参考案：缺必需reactant/product均不得strict，
schema回执/真实native/全部node与aggregate保存。合法exact、
superset/partial、共同产物、独立备选保持；不搭车新增角色/计量门、
任意投影强等或occurrence一一对应科学要求。

04 persist检查和写入同一个实际规范路径。明确relative target基准：
相对repo_root则实际写该根，或相对cwd则出界先拒；禁止出界后回退
原字符串授权。symlink实际逃根必须先拒、零新文件/目录；未给root
亦有明确根规则。复用5个全合成写边界，不接触真实金标。
保留合法授权根与普通非敏感写入，不新增内容DLP/沙箱/race机制。

身份/version按既有规范登记：匹配/分类/写侧语义变更不能偷换同一
已登记契约；候选proposed与实现证明范围同步，不改criteria-v1。
晨报P2/teacher事项分列，不当本轮新增科学放行门。

交付：逐P1入口→行为→正负控→证据与有限残留；PPV1、父同字节
红绿逐nodeid/collection/字段/版本/行为分开；安全G01沿303谱系
SHA前后/缺席逐项；新fresh证据含完整input/output/argv/env/exit/
SHA，所有嵌套manifest纳哈希只排根controls。旧probe只复制tmp跑。
新回归对本轮父基线真实失败、合法保持，不用KeyError当行为翻转。
依AGENTS交付本地v4.3显式路径提交、不push；mimo请求自包含合成，
程序事实待执行标注，主会话安排只读化学复核与Codex正链复审。
不要替用户/teacher定阈值/分母/金标或启动S5b。
```
