# pollutant_pathway_v1 S4 回修 r2 正链复审（报告 R3）

日期：2026-10-08，Asia/Shanghai。实际正链 Codex 会话及协作子代理取证；账号额度中断后继续，不调用外部模型。

**最终裁定：S4 不通过。原 S4-C02、S4-C04 已关闭，C01/C03 保持关闭；本轮唯一阻塞 P1＝[PPV1-ISO-01：同位素变化漏核导致错误中心 verified/full、R6 和实际提交]。S4 完成交接点尚不成立，不交接 S5。**

**mimo 同位素发现互证：缺轴和错误立体理由码属实，是历史实现缺口；“只会保守判 unknown、不产生假 verified、不影响放行”只能用于本次纯同位素例，不能用于混合变化。**本审的中心外同位素＋正常键变化合成例经公开诊断、审核、准入、提交及实际生产 caller，得到错误 verified/full/R6。不能仅登记缺口或改理由码后放行。

## 1. 固定验收、实际身份与续跑

- HEAD：`2ff919fa6ef127d4a477b1b1bb52beb685365a9d`；直接父：`0dd35d14d6539fbf134be18565f6709e852fc076`。
- 工程收口基线：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4_CODEX_REVIEW_R2_2026-10-08.md` §4 C02/C04 及 §7。C01/C03 与其它已关闭项保留，不追加机制库、科学性能或 S5 门。
- 本轮独立化学发现范围来自派单明确要求的 mimo v19 同位素专项；裁定出处为冻结判据五的“实际净变化集合”及 AGENTS §返工教训 2/3/5，不是新创化学硬门。
- 交付书：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4_REWORK_DELIVERY_R2_2026-10-08.md`；回应：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r19.md`。
- 阶段任务书：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4_IMPLEMENTATION_TASK_2026-10-08.md`；冻结正文及记录仍是 `ppv1-criteria-v1`，本审不修改、不重新冻结或自动宣布 criteria-v2。
- conda `depending43`：Python 3.11.16、RDKit 2026.03.6、SQLite 3.53.4；运行 argv/env/exit、实际 schema/profile 见各子包。

初段约 21:00 建隔离树，root 输入快照为 **21:01:31+08:00**；之后因 ChatGPT 账号额度中断，旧 agent 明确返回 usage limit。中断精确时刻未独立记录，不伪造退出码。用户授权后 **21:47:28+08:00** 续跑；HEAD、父、127 项实际源/测试/文档输入及旧永久证据 1178 文件 SHA 全部未变，工作树状态相同。

已完成 PPV1、父基线、legacy 两树专项、五项出口探针/正常链完整复用；G01 只有约 4% 输出，没有完成 JUnit/exit、没有存活进程，保留原未完成输出后只补该项。此前同位素 tmp 为空，无可复用执行，续跑新做该专项。出口只补未覆盖的封包前/B4/缺版本控制。额度中断是执行中断，不是产品缺陷；没有为凑数字重复已通过验证。

## 2. 独立执行数字与隔离口径

| 验证 | 本审实际结果 | 分类 |
|---|---|---|
| PPV1 全量 | **962 passed / 0 skipped，exit 0** | 36 文件；复用中断前完整 JUnit/命令/退出码 |
| G01 安全隔离 | **1564 passed / 8 skipped / 17 deselected，exit 0** | 296 项输入前后 SHA 相同；唯一未完成 suite 补跑，228.11 秒 |
| 父 0dd35d1：同字节新增文件 | **8 failed / 3 passed** | 7 缺预期拒绝行为红＋1 新 `necessary_basis` 返回字段 KeyError；0 collection 红 |
| 父：同字节更新两文件 | **3 failed / 38 passed** | 3 个版本字面量失败用例；包含合法和拒绝控制 |
| 父合计 | **11 红 / 41 绿，0 collection 红** | 7 行为＋1 字段＋3 版本；不等于 11 个漏洞 |
| legacy 两树实际产物 | **4/4 逐字节相同** | 两个合成 run×两类产物，实际分别执行两树 |
| legacy 标准 code identity | **52 文件聚合不变** | `18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6` |

G01 的 8 skip：v4 parser 对照根缺席 1；v2 provenance/summary 未生成 2；冻结 v3 真实评价依赖缺席 5。17 deselect＝16 slow 节点＋1 显式排除的 charge/evaluation fixture 节点。逐 nodeid、原始理由/时点及白名单输入见 `execution/README.md`、缺席 JSON 和日志；缺席不算通过。不读取原 v3 assets/evaluation、v4、金标、真实题面或封存逐题 run。交付“仓内树非 slow 1573/16”不是本审安全隔离数字，不混计或采作独立执行。

这些数字是合成规则级工程回归，不外推 dev 或 298 科学性能。8 个同位素分案及 3 个生产 caller 案是另行观察探针，不与 962/G01 相加，也不把观察脚本 exit 0 说成产品安全通过。

## 3. C02/C04 及继承契约逐项收口

| 验收 | 本轮公开输入→行为→效果 | 裁定 |
|---|---|---|
| C02 原 `single_ref_missing` | 原报告被 native 实际消费；仅删报告＋删 manifest 同 ref＋自洽新 digest，DB/native 不变。现在拒 `export_reference_mismatch`，check=`necessary_artifact_reference_set_closure`，basis=`payload_audit_production_report_consumed`；17 表零写、缺席与原 payload/native 保全、恢复正控通过 | **关闭** |
| C02 写前守卫 | 已完成 retrieve 的必要 soutc 删除，再构建/封包；写侧先拒 `missing_necessary_files`，basis=`done_outcome_completion_soutc`，0 新导出目录/0 业务写；恢复后同 digest | 保持正确 |
| C02 集合分工 | DB action/commit/计划锚及已验证 payload 实际消费列必要集合；存在集合另核。`omitted_necessary`、`omitted_existing`、`dangling` 分写，必要性不以文件存在为输入 | 达最低收口；来源能力边界见 §5 |
| B4 合法缺报告 | 公开 runner start_run 注入 `after_event_submitted`→公开 resume_run；1 event、done expand，合法没有 production_report；native 与带/不带 ledger 的投影均可读 | 正控通过，不强加 done 必有 report |
| C04 无 ledger 原三未知版本 | export schema、contract profile、native_result 版本自洽改坏，均先拒 `v3_native_source_version_unknown`，不能再由当前 adapter 解释；带 ledger 包装原生拒 | **关闭** |
| C04 缺失/冲突补证 | 缺 native_result 版本、整个 contract_versions 缺失、投影自记 profile 冲突分别先拒；读侧零写、原文件保全 | 达最低收口 |
| C04 正常及登记边界 | 真投影无/有 ledger 同值；两个旧 no_ledger H07/重封已知源形态仍按已登记文件级边界接受，带 ledger 拒 | 保持分工，未新增 DB freshness 门 |
| C03/正常链 | 四 soutc 全文与空 task_key child 保持；坏 child 拒。正常 start→endpoint→native→export→project→read、三次 resume、同进程/独立子进程字节确定性完整复用 | 已关项保持 |
| C01/S3 其它继承 | 当前全量对应 C01、历史条件、S3a/S3b、首消费、四崩溃/barrier/H07/H08、E01/E02/C06/H04、八 kind 与有损/空池控制保持；endpoint/native_result/runflow/production/audit 等本批与父字节不变 | 不以字节不变掩盖 §4 新证历史漏洞；其余已证组不重开 |

代码同源：`native_export.py:252` 必要集合函数不读文件，`:549–595` 写前守卫、`:775–791` 原生 payload 版本、`:901–933` 读集合闭合；`v3_projection.py:680–756` 版本门、`:791–792` 调用先于绑定及 adapter。当前登记为 native-export/policy-3、v3-projection-3、profile-18；endpoint/policy-2、native-result-2、runflow-5、store-10 沿用。

## 4. 唯一剩余 P1：PPV1-ISO-01

### 4.1 冻结同位素净变化轴缺实现，纯变化被误标成立体

冻结正文 §5 第 394–396 行明定 **键 diff ∪ 电荷/立体/同位素变化集** 为实际净变化基础。`audit.py:2110–2179 _atom_property_diffs` 有 formal charge、H count、四面体/其它立体和原子增删，没有 isotope diff。`:2711–2726` 对“严格身份不同、图变化集合为空”固定返回 `net_change_only_in_stereo_representation`，该排他理由不正确。

独立 isotope-only 输入确有 `S_C_1 isotope 0→13`、strict target=True，却没有 isotope delta，中心 unknown、R5/retain_conditional，理由为上述立体码。真实非四面体 stereo-only 控制也走 unknown/R5，说明同一理由把不同身份轴混为一谈。这个最小例支持 mimo 的“保守方向”，但不能证明混合变化无假 verified。

### 4.2 混合变化公开审核→提交反例

输入为合成 `CCO`。先用**未修改的真实 AtomTool** 做合法 `S_C_2—S_O_1 single→double`，得到 `CC=O`；随后只在隔离工具返回的 plain/mapped 产物两份一致地把**中心外** `S_C_1` 改为 isotope 13，得到 `[13CH3]C=O`。声明中心是 `S_C_2/S_O_1`，完整映射/系数和自包含 proof 均合法；expected target 与消费结果同值，另用 `[H][H]` 共同产物闭合本契约元素/电荷账。不编造 proof：由公开 checker 生成，audit 内部按相同输入重新计算。

公开 `check_edit_against_donor→center_evidence_from_donor_diagnostic→audit_hypothesis→decide_admission` 实际得到：

- isotope 真差异 `S_C_1 0→13` 在中心外，但变化集合仍只列中心键/H 等变化；`declaration_mismatches=[]`、diagnostic center=True、strict target=True、missing=[]。
- 审核 transformation_center=`verified`，product_coverage=`full`；无 unknown 阻挡；准入 `expand` / **`R6:all_verified_no_conflict`**。
- 公开 `store.submit_event` 实际 created=True、事件 `ppev_622dcbaa1c42bbdc24dc` 和展开计划落库；第二次同输入 replay created=False、全表内容不增加。

**合法控制：**正常键变、原有 13C 标签保持的键变均 R6 且可提交；只改错 expected target 则中心 violated/R5v，不提交。把全部受变原子列入中心的测试是范围控制，不认证同位素核反应或现实可行性。证明目标是“中心外变化不能被漏核后称全部局限中心”，不是同位素计量/机制新门。

### 4.3 实际 production caller 可达性

为排除只有 writer 裸入口的疑问，另执行三案 `production.expand_hypothesis_production`。唯一替换是 `production.execute_edits` 的**输出通道**：内部仍先调用真实 AtomTool，混合案之后加上述一致 13C 标签；donor、converter、audit、admission、writer、complete 全是真实函数，未 patch 审核结论。

混合案实际返回 `status=submitted`、center=verified/full、expand/R6；event_count=1、commit_count=1、action=done，事件 `ppev_0819a581aaf3ab0e7c91`。无替换的正常键变与 13C 保持两正控均真实合法提交。完整 raw AtomTool 结果与消费结果、maps/edits/proof、state/hypothesis/context、17 表前后、生产报告等 artifact 全文保存。

**可达性限定必须保留：**固定 AtomTool 协议没有同位素编辑操作；本审没有证明其正常执行自发改变标签，没有真实外部来源或真实污染物性能结论。反例是自包含合成工具结果的公共防御消费链。冻结判据及 proof 本来不认证“编辑曾执行”，但即使给定这一自包含输入，区域变化也被错误复算为全覆盖；来源真实性限度不能抵销这件具体范围核验错误。

### 4.4 正链严重性与最低收口

**确认为历史实现缺口，并确认为本轮阻塞 P1。**audit/production 与父字节相同，问题不是本批 C02/C04 引入。mimo 的缺轴/错误理由事实采信；其“不产生假 verified、不影响放行”的全称判断被本轮混合变化与真实 caller 执行证伪。此前评审没有覆盖这一组合，本审不以历轮放行替代程序证据。

原契约出处是冻结 §5 实际变化并集、区域证据不扩大范围及公共生产准入 R6 的全核前提；不要求新机制库、真实同位素实验或完整科学性能。仅登记缺口＋理由码中性化**不足以清零**，因为仍会把中心外未核变化写成 verified/R6。

最低行为要求：同位素差异必须进入实际净变化/changed atoms/属性披露及公共重算的许可范围；若暂不支持相应比较，必须机器披露未核轴、限制 scope，并阻止该反例获 center verified/full/R6。纯同位素不得错标“仅立体”。保留没有 isotope 变化的真实键变及原 13C 保持正控、strict False→violated、合法未知/partial，不能一概拒绝所有带标签的结构。

冻结/处置选择交用户：A 按冻结现义补同位素轴并升实现/证据契约身份；B 暂时登记 unsupported 并**实际阻断过度授信**、用中性理由披露，待下一版补轴。单纯文字 B 不够。若要删掉或缩窄冻结判据五的承诺，须另走用户裁定与下一判据版本；本审核不改冻结正文、不自动选方案或升 criteria-v2。

## 5. 交付/mimo 一致性、残留与 P2

交付 C02/C04 入口修复、962/1564/296、11红41绿、B4 合法报告缺席及正常链证据，与本审互证。C02 必要性源是 DB＋已验证 payload 声明：构建前报告未被 payload 消费时，缺席与 B4 合法形态不可区分，不强加 done 必有报告；soutc/outcome 的先写后完成行不变量仍独立闭合。全库/权威/所有文件自洽共改超范围。无 ledger 两形态按前轮认可的文件级/完整授信分工保持，生产完整授信继续传 ledger；不因此新增 P1。

mimo v19 的程序行号主张与运行已逐案互证；其判据三有条件同意与各节 P2，不应被转述成“全部无条件同意”。同位素严重性按 §4 正式更正。只读校验实施归档 **235 条 manifest 记录**及 SHA256SUMS 相符，来源仍是实施方，不换署本审；其 assets 准备失败及预建目录冲突副本如实留存，非本审有效结果。其 52 文件自有序列化聚合 `2b32c86e…` 不与本审标准 `18007e6a…` 混称同一身份算法。

mimo 十一项文字/覆盖建议均分写为 P2，不为数量加新阻塞：

1. 请求 §6 仍把 v18 的 profile-17/export-2 当“本批”，应列 v19 profile-18/export/policy/projection-3，并标旧段历史。
2. endpoint staleness 现五摘要，补 `route_conditions_digest`，不能仍写“四摘要”。
3. 六个冻结 stop 值与散文“七类”区分，模型弃权是映射情形。
4. 必要性“在读文件之前”意指**不以文件为输入**；read step9 时序实际在逐引用读后，不误写全流程先后。
5. 写/读 helper 不同，共用的是下层 `artifact_reference_index`，标同源层级。
6. 父版本块核登记 7 键及整块缺席；登记源外多出键当前不核，不写成任意扩展键全拒，不把未消费扩展键当新的 blocker。
7. runflow/runner/store 行号漂移分历史与当前；不回写冻结快照伪造旧行号。
8. export_v3 实际路径 `src/pathway_v43/output/export_v3.py`，没有 legacy 包。
9. 两个 no_ledger 登记边界的本轮专项已执行，但 tests 尚无同名常驻用例，列后续工程建议。
10. export_digest_mismatch 专门断言缺项是测试建议；原八 kind/正常链已回归，不凭 grep 升 P1。
11. proof_record 自报与复算一致、audit input_hash 与 hypothesis_id 的入口完整性机制分写，不冒充密码学执行证明。

交付称“8 字面量行”把代码值及注释混计，实差分保持记录；本审以 3 个失败用例、41 控制绿为红绿口径，不拿行数作行为翻转。旧“存量零改动”限定逐批测试字面量例外，当前962＝951＋11新，不全叫存量。

## 6. 永久证据与完整性

目录：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s4_codex_r3_2026-10-08/`。

- `execution/README.md`：复用的 PPV1/父/legacy 完整日志，未完成 G01 原输出及 `logs/g01_resumed/` 正式补跑，296 项 SHA、8/17 nodeid、runtime schema/versions、源差分与标准52聚合。
- `export_chain/README.md`：旧输入/脚本逐字复用与实际五项 exit，C02/C04/C03/公共链及 `resume_supplement/` 的写前/B4/缺版本补证；完整 JSON/schema/表哈希、原文件/缺席形态保全。
- `isotope_contract/README.md`：本轮新做的8分案＋3 production caller，真实工具原返回与手工同位素改后返回、公开 audit/admission/submit/replay 与生产提交、所有状态/上下文/proof/表/产物、实际脚本命令/exit/源码SHA；原始 IO 不改。
- `root_audit/`：127 项源/测试/文档和旧永久1178文件初始SHA、续跑守卫、中断事件、材料片段、实施归档哈希互证；`workspace_integrity.json` 钉发布前后只新增两路径。
- `manifest.json`/`SHA256SUMS` 覆盖实际所有附件，包括嵌套业务manifest和子包控制；外层只自排除这两个文件。子包独立清单；`report.sha256` 绑定本报告。

旧三复合出口脚本按已修缺口在假 native 构建拒/无漏聚 child 的 StopIteration 处 exit1，后段未执行；独立分案及 public_controls 补证，不能报旧脚本全绿。两份旧断言仅逐字归档未执行，不计翻转数字。账号中断前五项有效出口执行完整复用，已完成任何 suite 不重跑。

所有写库在 fresh tmp 源码/vendor/metadata副本，主脚本 `-B`/pyc 禁用/pytest cacheoff；隔离G01既有非PPV1子进程可能生成临时pyc，明确记录且不归档，源码SHA不变。没有金标/题面/封存run/原v3评价资产、外模/provider/LLM判分、push/commit；不动现有src/tests/docs/AGENTS/旧永久目录。库二进制不入包；逐案全表与schema/hash保存，suite库仅schema/count/hash不能当逐案全行。

网络口径如实收窄：public_controls 的零是应用请求记录；同位素 production 原输出 `network_calls=0` 未仪器化，保留原文但不当 socket 实测。本审没有为测 socket 重跑11案，没有声称G01全进程网络测量为零。

## 7. S4/S5 交接及判据版本状态

**原 C01–C04 全部清零，但新实证 PPV1-ISO-01 未清零，完整 S4 暂不交接。**工程出口、版本门、G01/PPV1、legacy、文件确定性和其它已关阶段验收可确认；同位素范围的实际过度授信不确认。其余已关组不重开；下一轮只处理该净变化轴、实际生产消费及相关精度文字。

沿上一轮专项：必要条件阻断仍不单独触发 criteria-v2，冻结正文/记录逐字节不改；S4契约本批升到-3如实登记。历史 isotope 缺口的存在不自动改冻结定义：要兑现当前定义，修实现并登记版本；要缩窄定义，另行用户判据裁定。不能把“源码字节未改”当被冻结能力已实现。

ISO-01 实际范围闭合后按已定验收收口，不加真实机制/科学门，S4才到正式完成交接点。S5 的任务书、题域/留出、统计预注册、阈值/费用、provider、敏感资料及teacher裁定仍须用户另行授权；本轮不访问或执行。交接材料必须披露同位素能力及实际支持范围，工程测试数不认证污染物降解性能。

## 8. 下轮有限范围回修提示词

```text
在 /Volumes/CC/Enzyme_Agent/dependingv43 实施有限回修；HEAD基线
2ff919fa6ef127d4a477b1b1bb52beb685365a9d。
读AGENTS.md、本报告POLLUTANT_PATHWAY_S4_CODEX_REVIEW_R3_2026-10-08.md
§4/§7、冻结判据五与本轮isotope_contract/README；只收PPV1-ISO-01。
C01/C02/C03/C04、其它S3已证组保持关闭，不改legacy/G2/AtomTool、不加科学门。

先列原始诊断→converter→audit重算/proof gate→admission→公开production caller→
submit/replay入口矩阵，登记实际净变化轴、映射、scope、身份/版本和正常/unknown控制。
不能只改net_change_only_in_stereo_representation名字。

核心反例：真实AtomTool将CCO中S_C_2–S_O_1 single→double；一致合成plain/mapped
工具返回再把中心外S_C_1置13C，target=[13CH3]C=O、中心S_C_2/S_O_1、全maps/coeff/
self_contained proof合法。当前diagnostic True→audit center verified/full→R6→
生产submitted,event1/commit1/action done，必须不再过度授信。

最低收口：按冻结现义把isotope diff并入实际净变化、changed atoms、属性披露与公开
重算；若采取暂时unsupported方案，必须机器披露未核轴/scope并实际阻止错误verified/
full/R6。方案与冻结文字若要缩窄先交用户裁定；不能自行改冻结稿当修复。
保留正常键变、原有13C保持、中心范围合法/未知控制、strictFalse→violated、
unknown/partial可有界探索，不以所有带标签结构全面拒绝换通过。

公开复现本轮8分案与3个production caller（先复制fresh tmp，旧永久不动），核真实
工具结果与合成返回差分、内部proof重算、各轴/admission、event/commit/plan/replay。
混合中心外不能R6；按当前已登记策略诚实处理，未展开项/unknown不得消失。
不宣称原AtomTool会编辑同位素、不认证实验/机制。纯isotope理由用中性归因或真实轴。

新回归对直接父2ff919f跑同字节红绿（行为/字段/版本/collection分开），正常控保持。
PPV1全量/G01安全隔离296谱系按本轮新增安全项登记，逐8/17缺席与SHA前后；
vendor/metadata及父子v3环境同根，禁pyc/cache、不重跑已有效验证来凑数。
旧复合脚本早停未执行段如实单列；完整inputs/logs/argv/env/exit/schema/表前后/文件
保全和SHA封包，所有嵌套manifest纳哈希，只排根控制文件。

代码/证据契约语义与身份变化按既有规范登记，criteria-v1正文/记录不回写；
自包含mimo请求附本轮纯同位素与混合变化区别、原保守全称更正及实际caller边界，
只规则/合成例不外发题面金标。按仓规本地显式路径提交，不push，不代提交评审侧文件。
本轮不含S5；不访问金标/题面/封存逐题run/v4/原v3评价资产，判分零LLM。
```
