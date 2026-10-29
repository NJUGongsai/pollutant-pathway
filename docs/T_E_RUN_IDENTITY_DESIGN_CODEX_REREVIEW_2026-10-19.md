# T-E「run 身份／缓存 key 闭合」设计稿 v2 同范围复审

**终判定：放行（可进入实施）。** 四组 P1 的实质合同已落实；v2 未展开的来源保存生命周期、审计字段及嵌套归一事件归属，由本报告直接确定为实施口径，不再留作实施自由项。本次放行对象是设计，不能当作实现验收、真实成绩认证或 HPC 发车许可。

题域：**298＝RHEA 通用酶学／已见题（post-hoc）**，不外推 dev。被审 v2 SHA256：`4f1cc37fa0a143fb01f7252661f0a304820ac819d79465368684162f69eefae0`。HEAD 为 `26ad11977852644ac581d8422e88f85074d7afcb`；审前即有并行 compiler／tests 改动，未回退、未修改，不宣称工作树干净。编译语义固定为首轮 compiler-4 副本，SHA256 `aa6806b8f28d79d11b05cf587906e1ca4ad9ca3389b9d7f211824d4e032b09e1`，不裁定同期 compiler-5。

## 1. 阅读范围与实际证据

以下行号均指本轮快照。FROZEN_V3 为语义权威；本报告只承接首轮既定验收，不增加科学性能门。v2 确有少数简写未逐字承接首轮最小字段合同，不能宣称它已包含所有细项；相应定值见 §4、§5，优先于 v2 的简写和“留实施任务书定”表述。

| 读件 | 本轮读取／核对范围 |
|---|---|
| [设计 v2](T_E_RUN_IDENTITY_DESIGN_DRAFT_2026-10-19.md) | 全稿，重点 §1.1／§1.2、§3.1–3.6、§4、§5、§6及修订对照 |
| [首轮报告](T_E_RUN_IDENTITY_DESIGN_CODEX_REVIEW_2026-10-19.md) | 四组 P1、Q1–Q11、§5七行口径表及其后最小字段合同 |
| [FROZEN_V3](POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md) | §3、§5 C-1／C-3／C-5／C-6与§5.3、§8、§11缺口6；N3／N7 |
| 静态源码 | `recorded_source.py`分类／find／compile／装配；`s5b_builder.py`三通道／诊断；`s5b_worker.py`首启／恢复；`runflow.py`身份／plan核对；`storage/run_identity.py`代码与资产身份。另核`production.py`、`evaluation.py`、`domain/identity.py`、`analog_source.py`、`native_export.py`、`s5b_scoring.py`有关消费链 |
| 固定编译副本 | [compiler-4](review_evidence/t_e_run_identity_codex_2026-10-19/baseline_sources/src/pathway_v43/pollutant/s5b_compiler.py)：中心查询／枚举及原子映射，未以当前 compiler-5 替代 |

行号简称：R＝`recorded_source.py`，B＝`s5b_builder.py`，W＝`s5b_worker.py`，U＝`runflow.py`，均位于`src/pathway_v43/pollutant/`。

本轮团队实际证据见[输入快照](review_evidence/t_e_run_identity_codex_rereview_2026-10-19/snapshot_metadata.json)、[身份核对](review_evidence/t_e_run_identity_codex_rereview_2026-10-19/identity_findings.md)、[消费链核对](review_evidence/t_e_run_identity_codex_rereview_2026-10-19/consumers_findings.md)、[算子核对](review_evidence/t_e_run_identity_codex_rereview_2026-10-19/operator_findings.md)。只补跑了6个纯构造输入的 H 计数检查：新 tmp，`PYTHONDONTWRITEBYTECODE=1`、Python `-B`，RDKit `2026.03.6`，退出0；未重复首轮16构造矩阵或身份探针，未执行真实资产／批脚本，未读 reports 数据、金标、题面或封存逐题 run，未联网或调用模型。设计所列全量双遍、build首消费及差分对拍仍是实施义务，不能写成已执行。

## 2. 四组 P1 闭合判定

| 组 | 判定 | v2依据与本轮收口 | 剩余要求动作 |
|---|---|---|---|
| **P1-1 build→首次消费绑定** | **已闭合** | §3.6:383–404绑定代码聚合、版本／指纹、RDKit、资产及逐输入原字节sha，创建run／发送前核；408–410旧／缺／坏／错版本拒并新build。§1.4:170–173及A9:237更正旧导出论证。405–407已要求绑定进run来源，保存与恢复生命周期由§4.1确定，非自由项 | 实施并验证拒例及来源持久化；不是补交新设计 |
| **P1-2 corpus分类／装配入口** | **已闭合** | §1.1:94–109、§3.1:266–274把视体建于分类前，贯穿分类、compile、co_comps／flat_products／copy_products、装配与NC-10两处声明；对应R:1483、1519、1630、1957、2021。raw例外与analog不得再传raw ref均落字。首次事务事件归属按§4.3 | 按统一视体接线，保留raw来源例外，不再扩入口规则 |
| **P1-3 参数／事务／幂等** | **已闭合** | §3.2:293–317登记三个真实默认值及完整指纹；§4.1:423–436按提交事务定义三值；438–448整消费视体回滚，保None／空列表／顺序／重数；450–461双遍成功固定点、failed重现及允许永久电荷 | 实现既定矩阵，不把局部16构造替代批内全量义务 |
| **P1-4 C-5／字节／对拍** | **已闭合** | §5.1:476–514覆盖全形态trace、坐标、实际query交集、unknown及人工复核；518–524条件spec及证明域；534–545旧基线和两层对拍。首轮§5:113–115的源引用、字段集合及trace内容绑定未被v2完整展开，**由§4.2最终定值承接** | 依最终schema实施和验收；不得把内容绑定降为任意命名项 |

以上“已闭合”指设计合同加本轮定值可直接实施，不等于相关代码已经存在或测试已通过。原来已过的身份不升格、判分语义不动等边界继续有效。

## 3. Q1–Q11 一致性核验

| Q | 结论 | v2依据／出入处理 |
|---|---|---|
| Q1 短路 | 一致 | 278–286、426–429：先跑默认算子，再按同原子状态核无操作；不凭图等价宣称来源canonical臂字节等价 |
| Q2 applied | 一致 | 423–436：成功提交改变／成功无操作／未提交回滚三分；不按净电荷或字符串判 |
| Q3 record_equation | 一致 | 148、273–274、595：保raw原始条目、侧和重数；消费视体另用，N3/N7固定同payload |
| Q4 matched_component | 一致 | 140、269、512–514、596：保raw，两装配分支另披露消费态；实际copies／co_substrates／record_products同域 |
| Q5 组分顺序 | 一致 | 275–288、597：保输入序与重复份数，applied内部重排保对应，无操作直通 |
| Q6 失败直通 | 一致 | 430–436、598：整候选回raw而非新增一律拒；原始编译照既有门运行 |
| Q7 事务单位 | 一致 | 438–448、599：全视体原子提交；嵌套compile不得重授失败子集收益，见§4.3 |
| Q8 版本／N10 | 一致 | 321–336、383–410、558–566：pool-9／source-4／formnorm-1，route绑定；固定事实逐事件比，新池另列 |
| Q9 参数指纹 | 一致 | 293–317、601：默认Uncharger()三值登记，不可自省单列，删无效neutralize参数 |
| Q10 披露／零字节 | 语义一致；表示有简写出入 | 518–524写成status/version等嵌套简写，未展开首轮精确键及hash回指；本轮§4.2采用首轮最小schema，不选该简写作为另一个schema |
| Q11 原子trace／风险 | 方向一致；明细由本轮定值 | 480–510已定坐标／交集／unknown；source_ref、前后值、H来源分列、scope／风险枚举与trace绑定依§4.2，不只存Δq／ΔH |

## 4. 残余项、新问题及本轮确定值

### 4.1 批旁块与run来源生命周期：可进入实施，直接指定

批根采用唯一权威旁块 **`build_identity.json`**；manifest可放引用／摘要，不再另存一份可独立变更的同内容权威块。字段集采用v2:386–397。`build_identity_fingerprint`＝整个build_identity载荷的 `sha256(canonical_json(payload))`；只排除顶层自身哈希键及明确的展示项`created_at`、`display_note`，排除清单随schema登记。代码、资产、版本／参数、RDKit、逐qid/run_id及输入sha等实际身份事实**不得排除**，不能只挑部分版本号算摘要。

首消费核对通过后，在run合法创建后、driver开始或任何付费调用前，将已核 `{build_identity_fingerprint, run_input_sha256, qid, run_id}` **唯一、不可覆盖地持久化**到run内来源工件或ledger。case只作摘要，不能成为唯一且可被覆盖的权威记录。来源落盘失败即不得继续调用。恢复先读并核既存原来源，再与当前已验旁块／输入逐项同值；缺、坏、不符均拒并保全原记录，不覆盖、不用当前新摘要补造旧出处。

该生命周期落实v2:405–407“绑定进run来源”和AGENTS首次消费／重放同核的既定义务。当前worker恢复不传plan（W:221–223），runflow只在plan非空时比较调用方计划（U:2026–2038），现有门**不能**替代上述新出处核验；本报告没有声称源码已实现。无需改`run_identity.json`或native-export schema，不强改通用无批scripted start。

拒因建议分为`build_identity_invalid`（detail区分missing／corrupt／version／content mismatch）、`run_input_bytes_mismatch`、`run_build_origin_mismatch`（detail区分缺／坏／错）。实施书可沿现有枚举风格定名，但必须保留这三类可判定事实，不能吞并成无法判断是否补调模型的笼统异常。拒绝时失败题留分母、零发送；首启核对失败不建run，恢复失败不改既存run。

### 4.2 审计字段：采用首轮最小合同，不留内容绑定选择

**首轮§5:113–115字段集合继续生效，并优先于v2:518–524简写。** 诊断行`record_side_form_norm`为三值标量，追加`record_side_form_norm_trace`：

- `source_ref`含`channel/asset_sha256/record_key/matched_side_or_component`；`source_fields`标明raw来源例外。不能只靠record_key：R:1427–1437允许同一记录多匹配侧，B:1088–1098旧诊断没有天然完整源锚。
- `changes[]`含`side/entry_index/fragment_index/source_atom_index/original_map`及`charge_before/charge_after`、`hydrogen_before/hydrogen_after`；使用源坐标。`atom_correspondence[]`以同坐标绑定`normalized_atom_index/generated_map`，changes回指它；缺对应给原因，不拿重排后idx猜测。
- H总数固定为`GetTotalNumHs(includeNeighbors=True)`，并分列显式属性H、隐式H、邻接H原子及其同位素来源，均存前后值；保原子身份，不能把D当普通H。v2默认API不计独立邻接H/D，6个构造检查未发现ΔH漏报，仅据此澄清口径，不另判化学漏洞。
- `matching_scope`区分`center_l1_l2`与`legacy_whole`，后者仅作来源复现，不能合并冒充同一消费范围。`intersection`用实际消费query／匹配原子与同坐标lhs改动原子；rhs另列。
- `risk_status ∈ {present, absent, unknown, not_applicable}`并带原因；可核交集非空为present，可核空集才为absent；无法追溯／无匹配／截断如实unknown或not_applicable，不伪填false。风险及unknown行保留人工复核义务。

applied成功spec的`compile`仅条件追加五个审计键：`record_side_form_norm="applied"`、`record_side_form_norm_version`、`record_side_form_norm_param_sha256`、`record_side_form_norm_trace_ref`、`verification_domain="normalized_record_side"`。**采用标量加独立字段，不采用嵌套status/version对象。** trace_ref为同候选trace规范内容的确定性sha256且必须能回到相应诊断；不能只存可漂移行号或无绑定的引用。`verified_product_set=True`只证明消费态归一记录域产品集通过既有核验，不授原始资产完整离子身份。未applied spec这五键缺席、原字节不变；新audit字段另验，不当版本键整块排除。

### 4.3 嵌套消费、固定compiler与A臂：可进入实施

首次source→view事务持有候选原始status／trace。corpus视体二次进入公共compile的局部not_applicable不得覆盖首次applied或移除证明域；完整视体failed时，子集compile不得重新归一授益。这是v2:433–445及476–478的既有原子事务／保留义务，不是新增一种算子或可选流程。实施矩阵应覆盖首次applied→二遍no-op和父事务failed两形态。

**固定compiler副本可用。** v2:14–19／611–613已声明口径；本报告仅支持compiler-4设计，不能据此放行同期compiler-5与tests。后续若集成新编译器，应固定实际树并核其适用合同，不回头冒称本轮已审。

**A臂两条路线均可。** v2:534–537可执行：先证明恒等臂与pre-T-E旧树等价，或直接旧树／新树对比；推荐后者，非强制。实施书必须选一、记录源码和输入身份，未选择或未证等价不得称“旧基线”。旧diag字段投影与新audit分开验，未applied输入不变，受影响题逐差异归因；不能靠扩大排除键掩盖漂移。

**新增分级：未发现需重开的P0／P1。** 以上来源生命周期、schema、事件归属是原合同的工程定值，H API为P2口径澄清；均已在本报告确定，无未决设计项。不声称v2逐字齐备，最小schema由本报告直接确定。

## 5. 实施任务书可直接消费的最终口径

| 合同面 | 最终口径（对齐首轮§5；标明本轮澄清） |
|---|---|
| 算子／标签 | 默认Uncharger()三参数与RDKit入指纹；实际运行后按同原子状态核无操作直通。三值按事务提交状态，不按字符串或净电荷；applied可留永久电荷。沿用首轮 |
| 事务／入口 | 完整候选视体原子提交；corpus分类前贯通装配／NC-10，analog同ref全消费同域，公共compile无旁路；保None／空集／顺序／重数。**本轮澄清首次事件持有及父failed不得子集授益** |
| 身份／来源 | 底物、raw tier、原始召回不变；record_equation／matched_component保raw，消费态另披露，归一对齐不授严格身份。沿用首轮 |
| build／缓存 | 原始缓存key不加归一版本，值写时复制；memo含指纹与原串。**本轮指定build_identity.json、完整载荷指纹及run不可覆盖来源／恢复同核**；首启前验证输入原字节和全部运行身份 |
| 版本／历史 | pool-9／source-4／formnorm-1与实参指纹；route-1算法未改但结果可变，compiler-4固定。新根／新tag，旧批零回写；历史合法固定事实可重判，不冒充新策略产物 |
| C-5／对拍 | 每候选全形态三值、可定位trace及诚实风险；**本轮明确承接首轮最小schema、内容hash回指和H来源口径**。applied spec条件证明域，未applied spec不变，旧diag／新audit分别验，A臂先证旧基线或直接两树 |
| N10／正交 | 固定同批不可变事件／产物／参考／导出／criteria，钉哈希，逐事件核strict／身份参与物／原因，v1与显式v2分开；N3/N7同payload，新池候选／事件变化另列。P3/P4来源与实施口径差如实登记，不以来源数字替代实施证据 |

**总体裁定：放行，可按上述确定口径进入实施。实施后的接线、持久化、拒例、幂等和差分结果仍须交付验收；本报告不认证真实成绩，不构成HPC发车许可。**
