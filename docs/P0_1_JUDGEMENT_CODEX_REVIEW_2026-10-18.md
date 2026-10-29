# P0-1 判读产物与结果表 Codex 代审（2026-10-18）

**总体结论：回修。** 批链与现有数字核算通过，但发现两组 P1，当前只能保留为待核的 judger 原始读数，不能认定为已通过设计门的误拒率结果。未发现 P0。

| 级别 | 阻塞项 | 最小收口 |
|---|---|---|
| P1-1 | 一件阳性 `mapping_anchor` 与材料模板直接相反 | 返工 `a-075c0a3e10c5426f` 的具体映射锚与阳性身份，按原流程确认；不得机械改判 reject，也不得带着错误锚直接作为有效阳性送确认。 |
| P1-2 | 判读可用性门缺少可复核记录 | 补齐 A/B 各15件独立二读或同人间隔≥1天的配对记录、agreement与κ，以及 S2通过件15件盲判控制记录；按既定失败处置执行。未核过前撤销“已满足设计门”的读法，区分原始 judger 数字与可用结果。 |

题域：**298＝RHEA 通用酶学／已见题，限 chain13 本次候选拒绝面**。本轮不判最终化学真值，不外推全部拒绝件，也不替代师姐确认。

## 审核范围与执行事实

实际 HEAD=`4eede032d2815dd20f3a532b44a41afde8289aa4`；Python 3.11.16、RDKit 2026.03.6。输入22文件的字节数与SHA见[快照](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/p0_1_judgement_codex_2026-10-18/snapshot_metadata.json)。只读用户指定判读目录与两份设计／结果文档；未访问题面、金标、封存逐题run，未执行会读取上游run的原物化脚本，未调用外部模型。

首次标准库JSON结构查看从仓库cwd发起，只读授权文件，因文件实际为JSONL而停止；未核算、未导入源码、未写入。全部验收核算及RDKit图核在新tmp中运行，使用 `PYTHONDONTWRITEBYTECODE=1` 与 `-B`；未跑pytest。批链验证先发现B前缀口径差异并停止，改为显式核对 `b-`／`c-` 与相同row_id后完整重跑，退出0。实际命令、失败说明、输入哈希及可复跑脚本均留在[本轮证据目录](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/p0_1_judgement_codex_2026-10-18/REVIEW_TASK.md)，不把中途停止算通过。

## Q1 批链完整性：通过

独立重算 A 五批为20+34+34+34+33＝155，B三批为33+33+31＝97；两通道各批case集合零重叠，并集逐一等于对应sampled清单。case_id前缀分别为 `a-`／`b-`，后缀与row_id一一对应。B材料包使用 `c-`，判读使用 `b-`，两者按row_id严格双射，未改源文件、未丢件。A材料case_id逐字相等155件；B该项为0，但显式前缀规则下97件完整对应，不能误报逐字相等。

给定安全frame内，A为1886＝155+1731，B为97＝97+0；集合闭合、抽中与未抽中互斥、去重键唯一。按seed=20261016、同族层和原排序重抽，两个通道均与原抽中列表逐项相等。证据：[核算JSON](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/p0_1_judgement_codex_2026-10-18/chain_validation.json)，路径 `$.channels.{A,B}` 的 `judgement_union_equals_sample`、`material_row_id_bijection_equals_expected`、`replayed_sample_exact_list_equal` 均为true，`errors=[]`。

证明范围止于所交付frame。原始2818／224和上游去重是否完整，本轮未重建；不能将安全frame重抽说成独立重跑了原始物化全链。

## Q2 结果表核算：算术通过；消费表述需P2纠正

| 通道 | 独立计数 | 点估计 | Wilson95% |
|---|---|---|---|
| A | pass27／reject107／uncertain21；总155，有效分母134 | 27/134＝0.201493 | [0.142334,0.277290] |
| B | pass1／reject96／uncertain0；总97，有效分母97 | 1/97＝0.010309 | [0.001822,0.056106] |

与[结果表12行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/P0_1_ERR_RATE_RESULT_2026-10-18.md:12)的三位小数相符。uncertain不进率符合[设计147行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/P0_1_PROBE_INITIATION_INPUT_2026-10-16.md:147)。原设计是**各通道点估计≥10%分别判定，CI随报**；不增加“下界必须≥10%”或两通道同时过线的新门。因此当前数字若经后续确认仍成立，A对应立项、B对应降维护；这不是本轮可直接生效的最终裁定。结果表表内“⇒立项修复／降维护”应与正文待确认状态统一，改成明确条件读法。

敏感性文字亦须修正：27→14若13件转reject，为14/134＝10.45%、CI[6.33%,16.77%]；若全部转uncertain，才是14/121＝11.57%、CI[7.02%,18.49%]。两者点估计仍≥10%，失去的是“CI下界稳过10%”，不能混说点估计门已经耗尽。证据：核算JSON `$.sensitivity`。B为去重后全查，Wilson按指定格式复算正确，其区间不能消除判读误差。

## Q3 判读质量抽核：不通过，P1-1

先固定15件选择规则再读材料：B唯一阳性＋按case_id排序前4件拒绝；A前3件阳性＋前4件uncertain＋前3件拒绝。不因错误换样。逐件定位及复跑图核见[15件审计表](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/p0_1_judgement_codex_2026-10-18/quality_audit.md)与 `quality_audit.json` 的 `$.selected`。

明确反例：[`judgement_mimo_A_batch4.json:19`](/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/p0_1_initiation_input_2026-10-17/judgement_mimo_A_batch4.json:19)，case=`a-075c0a3e10c5426f`，依据和锚均说断map5–map12。但[材料A](/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/p0_1_initiation_input_2026-10-17/material_packs_A.json) `$[106].record_content.templates[0]` 的lhs/rhs都保留此SINGLE键；RDKit复核一致。N12真正失去的是连接无map芳基的另一条键。原设计105／132行要求阳性有具体可核映射锚，该条目前不满足，故不是一般措辞偏差。返工锚后再判断，不据此强改reject或推断全27件有错。

其余抽核范围内，A另两件阳性锚能回指具体键级变化；四件uncertain均能指向未声明的新增氧／片段来源。B四件拒绝依据涉及材料中实有的辅底物跨源成键、组分／产物差异，并非简单重复机械拒因；所以96/97全拒在这四例中未见循环论证，但**不能认证其余92件**。

P2事实纠正：B唯一阳性 `b-79533937d6e8a476` 的所述断N=N片段确可对上记录产物，但重原子为17、不是锚写的16；未证明完整映射在截断面外。A拒绝 `a-05c5ef09e7966e6b` 存在目标局部子图匹配，原“目标环无对应”需澄清；局部匹配不证明整体可编译，不据此改成阳性。其他名称／map文字误记见审计附表，归P2纠正，不增独立阻塞。

## Q4 一致性与诚实边界：不通过，P1-2

[设计111行](/Volumes/CC/Enzyme_Agent/dependingv43/docs/P0_1_PROBE_INITIATION_INPUT_2026-10-16.md:111)明确要求A/B各15件独立二读，换人或同人间隔≥1天，agreement≥90%且κ≥0.6；134行另设S2通过件15件盲判可用性负锚。结果表5行仅自报pilot20件19件一致，并称达到90%线；授权目录未见原判／复判配对、时间、B二读、κ及通过件盲判控制记录。252条最终记录的 `second_read` 均null，故**19/20未被本轮独立重算，完整设计前门未获证明**。这不等于断言历史一定没做；应补可核材料，不去其他真实run越界追索。证据：[一致性输出](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/p0_1_judgement_codex_2026-10-18/consistency_probe_output.json)。

结果表19／21行已如实写师姐逐件确认和编译重放尚待完成，本轮不把这些已登记后续项另开P1。确认轮仍须按原流程处理阳性、每通道15件reject抽检及重放；不能只凭“师姐确认”替代可用性门，也不能将未重放说成正控通过。当前27／1是judger所判阳性，尚非最终分子。

## Q5 采信边界：有限通过

结果表6／22行明确298题域、机械量只是抽样框、限chain13单批、不外推；未发现越界数字表述。材料字段为候选身份、运行侧冻结底物、语料donor/product/template和规则引用，未见金标、评分参考或模型输出字段。物化脚本91／108／169行取冻结manifest底物，162–175行取语料解析；这里只读脚本文字与交付材料，未执行它、未读真实manifest或语料解析实现，因此不背书历史读取过程的全链盲性。判读者为mimo的历史来源声明与本轮独立执行须分开，不能把本审核当成化学正确率认证。

## 总体裁定

**回修。** 收口只限错误阳性锚、原有判读可用性门的可核证据及所列P2表述；不追加科学性能门。批链与算术保持通过，师姐确认／重放按原后续步骤完成后，才形成最终T-G输入。
