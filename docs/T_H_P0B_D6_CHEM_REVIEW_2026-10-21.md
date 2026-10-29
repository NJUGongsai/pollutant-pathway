# T-H P0b/D-6 规则级化学评审回应（2026-10-21）

> **provenance：qwen3.8max 代 Codex 规则级化学评审，按 CC 2026-10-21 指示。**
> 本报告不是 Codex 本人裁定，不是 mimo 通道回应，**不是化学终认**；是对
> `docs/T_H_P0B_D6_CHEM_REVIEW_REQUEST_2026-10-21.md`（R4 硬挂账）的规则级
> 答复，采信到与修后程序证据互证为止，通道等效性（可否充抵 R4 所要求的
> 化学评审）由 CC/Codex 决定。
>
> **题域：[298域] = RHEA 通用酶学 / 已见题（post-hoc）。** 全文零金标、
> 零题面、零真实候选结构、零参考图、零结构正文；引用的聚合计数来自
> `docs/review_evidence/t_h_p0b_fix_2026-10-21/provenance.json`，只在该
> 题域成立，不外推。
>
> **评审对象身份（本轮实测）：** 合同
> `docs/T_H_P0B_D6_CONTRACT_2026-10-20.md`，块 `version=2`、
> `rule_version=p0b-d6-reconcile-2`；基线 HEAD
> `c9c6c7a7ae02b46769add09fbc2536323ce8a985`；
> `impl.patch` SHA256 `035123de…204aa4` 与 SHA256SUMS 吻合。**评审期间
> HEAD 移动**：主会话于 02:13:30 提交 `11aeeafded1b41185f24de49767933709aad49db`
> （"P0b/D-6 旁路披露(2026-10-21)"），本轮实测该 commit 的 src+tests
> diff 与 impl.patch **逐字节一致**（`git diff c9c6c7a..11aeeaf -- src tests`
> == patch；新测试文件 blob `00d0c8f` 与 patch index 一致），符合前轮复审
> §5"允许单独 commit"的授权面。本报告只读，仅新增本文件；未跑 HPC、
> 未调外部模型、未读金标/题面/reference_graphs/llm.env/私钥。

## 1. 总裁定

**规则级语义可接受（可冻结）。** 8 问全部可在规则级判定：0 项 unsound、
0 项 blocking、0 项必须修正；4 项 sound、4 项 clarify（全部为措辞/解释级，
不改任何判定规则、不加门、不改判据）。本报告不解除既有硬挂账：真实批
58 条 `principal_stereo_only` 与 146 条 `principal_absent` 的化学正确性
仍需真实结构复核，规则级评审不替代（前轮复审 §5(b) 继续有效）。

## 2. 逐条回答（按请求 §3 判定词）

### Q1 多重集/出现次数口径 — **sound**

按出现次数计与三方真实记录约定一致，不是人为口径：执行侧
`execute_edits` 以 `Chem.MolToSmiles` 输出全部分离片段、**不去重**
（对称裂解产两分子同结构 ⇒ 串内出现两次）；装配侧事件写入按声明
逐出现追加产物参与物（`production.py` prepare_hypothesis：每个
coproduct 条目一个 Participant），且仓内供给语义早已钉死
"exact multiset, 2 H2O != 1 H2O"；声明侧 `coefficient` 全为
None/unknown，出现次数是唯一忠实读法。因此"同一分子多份在装配侧
只记一次"的误判形态在**现行写入路径下不会发生**。
**边界：** 出现次数 ≠ 配平系数（合同已排除配平解释，proof_scope 已列
"stoichiometric completeness 不证明"）；"同结构在位但份数不足"会落
`principal_absent`/`declared_coproduct_missing_from_event`，读者须借
`relation`/`declared_missing_from_executed` 计数区分"分子未出现"与
"份数不足"，不得把后者读成前者。本批 [298域] 实测
`declared_coproduct_missing_from_event` 为 0 件，无实际暴露。

### Q2 copy 引用轴 — **sound**

copy 的化学内容是"记录侧声明、未经执行通道"——这是**来源声明**而不止
结构声明；同结构不同 `state_ref` 意味着事件中该组分的 provenance 不是
所声明的记录拷贝（可能来自执行或另一状态条目），故引用轴是唯一忠实
记录语义的合法性轴，结构轴保留为披露恰当地保存了"分子在位、引用不
对齐"的化学相关信息。不应设同结构豁免：豁免会静默改写来源声明；现双
轴字段（`in_event_products=false` ∧ `structure_in_event_products=true`）
已让下游可辨"记录卫生问题"与"化学矛盾"。空 `state_ref` 按引用缺失
处理、无静默豁免（代码 `bool(ref) and ref in ref_set` 已核）。
**边界：** 该轴判定是记录完整性声明，不得对外当化学结论引用。

### Q3 立体子类边界 — **clarify**（判定规则 sound，解释须钉住）

`RemoveStereochemistry` 移除四面体、双键 E/Z 与增强立体组，这三类在
RDKit 立体模型中都是立体事实，落 `principal_stereo_only` 诚实；阻转
异构若以键立体表达同样归入，化学上可辩护（阻转异构体属立体异构）。
**穿透该代理、语义弱于"构型冲突"的两类形态**：(a) 指定 vs 未指定
（一侧有 @@、一侧无立体标记）——去立体后相等 ⇒ stereo_only，但这是
粒度/缺信息差，不是已证构型不同；(b) 增强立体组（AND/OR/外消旋注记）
差异——注记语义差而非确定构型差。互变异构/质子化**不会**穿透该代理
（连接/H 位置不同 ⇒ 落 `principal_absent`，见 Q5/Q7）。
**建议（措辞级）：** 在子类说明写入"stereo_only 含'立体粒度/注记差'，
不得读作'已证构型错误'"。**边界：** 本批 58 件 stereo_only 的真实化学
性质 unknown，需结构复核（已挂账）。

### Q4 纯同位素差 — **clarify**（粒度可接受，含义可写得更准）

规则级可证一个更强的蕴含：strict≠ ∧ 去立体≠ ∧ 非异构= ⇒ 差异必在
**同位素或 CX 扩展类事实（如非 DAT SGroup）**（可伴立体差），连接/
电荷差被排除——因为去立体代理保留同位素/电荷/连接，非异构代理保留
电荷/连接但**不携带 CX 扩展**（`MolToSmiles(isomericSmiles=False)`
不经 `strict_identity_of`）。合同现措辞"可能是同位素或其它异构事实"
under-informative（不 overclaim）。
**建议（措辞级）：** 子类说明写明上述蕴含；是否改名（如
`principal_isotope_or_cx_involved`）动冻结枚举，不必须。同位素标记物
是否视为同一物种：RHEA/MetaNetX 体系同位素体是独立条目，且"是否给
更明确等价词"属判据所有者（CC/老师）的评分语义决定，**不在本披露层**
——本层维持"诚实未细分"是正确的。
**边界：** 本批 [298域] 该子类 0 件，暴露为零；R3-b 合成控制证明行为。

### Q5 连接差的措辞 — **sound**

分类学已把"执行失败/未执行"与"结构不同"分开：前者走
`execution_not_verified`/`missing_executed_product` ⇒ unknown，永不落
`principal_absent`；`principal_absent` 的前提是执行已核真、两侧可解析、
三代理皆不含——语义干净，无需再拆新状态。残余歧义仅在子类内部：
principal_absent 同时覆盖"完全不同骨架"（强信号）与"近缘连接级差异"
（互变异构、质子化/电荷态、份数不足——弱信号）；披露层可接受，
`relation`/missing 计数已提供部分区分，未来可选更细 reason code 便利
人工分诊，不必须本轮。**边界：** "结构不同 ≠ 化学错误"已在
does_not_prove 钉死，维持。

### Q6 缺资料语义 — **clarify**（分界正确，一处措辞缺口）

分界本身符合化学证据语义：证据缺失（载荷缺失/坏类型/不可解析）⇒
unknown + `unverified_ranges`，不等于矛盾证据；合法空列表是"已核
absence 证据"⇒ 按矛盾判，不升级 unknown——两个方向都未混淆。
**缺口：** 空列表分支不读 `participant_list_status`（derive 路径已核不
消费该字段），而事件写入允许 `participant_list_status="partial"`；严格
说"partial 且空"是记录截断，不完全等价"已核无产物"。现实暴露极小：
现行写入路径参与物恒含至少底物+主产物条目，空列表实为防御分支，本批
相关子类 0 件。
**建议（措辞级，二选一）：** 空列表分支消费 `participant_list_status`
（partial+空 ⇒ unknown/`event_assembly_unavailable`），或在 proof_scope
明示"空列表判定不区分 partial 状态"。非阻断。

### Q7 覆盖与限度 — **clarify**（无缺失判定轴，补解释清单）

电荷/质子化：strict 身份保留电荷为化学事实，差异落
`principal_absent`——在 RHEA 题域质子化态是有意义区分（反应以显式 H+
配平），严格处理**正确**，不应放宽。盐/溶剂化物/多组分：`.` 拆分
多重集覆盖，水合物组分独立身份，无去重风险。保护基：普通连接差，归
`principal_absent`，披露层无需专轴。互变异构：未归一、落
`principal_absent`；引入互变异构归一器会违反"禁止第二套身份/规范器"
的冻结，披露层也不应引入——应以措辞代替。
**建议（措辞级）：** does_not_prove/解释清单加一句"互变异构、质子化
微状态、分子盐形态未做归一，此类差异归入 principal_absent /
isomeric_unspecified，不意味着生物学上不同分子物种"。

### Q8 总体 — **可作为 P0b/D-6 规则级冻结口径（仅披露层）**

四态互斥、优先级冻结、unknown 诚实、"consistent ≠ 化学正确 /
inconsistent ≠ 化学错误"的限度声明，在规则级自洽且与写入路径/执行器
真实约定对齐；三条 clarify 均为措辞/解释级，不构成冻结前置。冻结的
**附带条件**（既有、非新增）：(a) D-2 离线实施书启动前本报告须与修后
程序证据互证并由 CC/Codex 认可通道等效性；(b) 58 stereo_only /
146 principal_absent 在真实结构化学复核前不得对外当化学结论引用。

**总评（按请求 §3 格式）：`v2 规则可冻结`**（附 Q3/Q4/Q6/Q7 四条
非阻断措辞澄清，建议随冻结文本一并落，不改变任何判定行为）。

## 3. 必须修正项与最小范围

**必须修正项：0。** 非阻断措辞澄清（全部只动合同/子类说明文字，不动
代码判定、不加门、不改判据、不扩题域）：

| # | 位置 | 措辞 |
|---|---|---|
| 1 | `principal_stereo_only` 子类说明 | 该子类含"立体粒度差（指定 vs 未指定）与增强立体注记差"，不得读作"已证构型错误" |
| 2 | `principal_isomeric_unspecified` 子类说明 | 写明蕴含：该桶必含同位素或 CX 扩展（SGroup）差异（可伴立体差），连接/电荷差已排除 |
| 3 | §1.7 空列表分支或 proof_scope | 明示"空参与物判不一致不区分 `participant_list_status=partial`"（或消费该字段，二选一） |
| 4 | does_not_prove/解释清单 | 补"互变异构/质子化微状态/分子盐形态未归一，此类差异不意味着生物学上不同分子物种" |

## 4. 与程序证据的互证关系

**只凭规则级即可成立（本报告依据）：** Q1 口径与写入路径一致性、Q2
引用轴语义、Q3 代理行为（RDKit `RemoveStereochemistry` 语义）、Q4 桶
蕴含（逻辑推导 + flat 代理不经 strict_identity_of 的代码事实）、Q5
unknown/inconsistent 分界、Q6 缺资料边界、Q7 覆盖清单。

**本轮只读核过的程序事实（与前轮复审互证，非重跑）：** commit
`11aeeaf` 的 src+tests diff 与 impl.patch 逐字节一致；
`execute_edits` 片段输出不去重（`Chem.MolToSmiles` 全片段）；事件
参与物按声明出现逐条写入（prepare_hypothesis）；derive 路径
`_p0b_d6_product_participants` 不消费 `participant_list_status`；子类
优先级代码与合同 §1.9 一致；聚合计数（[298域] 1381/204/1/0；
146+58；桶内 isomeric_unspecified 与装配/copy 子类均 0 件）与
provenance.json 相符、算术闭合。

**必须真实化学复核、规则级不能替代（维持硬挂账）：** 58 件
`principal_stereo_only` 与 146 件 `principal_absent` 的化学正确性、
机制/生物可行性；principal_absent 中是否存在互变异构/质子化/份数不足
等"近缘弱信号"个案；stereo_only 中"构型冲突 vs 粒度差"的真实占比；
同位素体等价口径。以上全部 `cannot_assess_without_structures`，需
CC/老师授权的真实结构抽样复核（零金标红线不破）。

## 5. unknown / 未核清单

| 项 | 状态 |
|---|---|
| 真实批 204 件 inconsistent 的化学真伪 | unknown（未读任何真实结构；挂账不变） |
| 同位素体"同一物种与否"的评分口径 | unknown（属判据所有者，非本层） |
| 本报告可否充抵 R4 所要求化学评审（通道等效性） | 待 CC/Codex 确认（原请求指名 mimo 通道；本报告为 qwen3.8max 代审，独立性不做背书） |
| RDKit 2026.03.5 vs 2026.03.6 下 `RemoveStereochemistry`/代理键行为等价性 | 未独立复核（前轮已披露版本差、历史锚点对齐） |
| 评审期间 HEAD 移动（c9c6c7a → 11aeeaf） | 如实记录：并发 commit 内容 == impl.patch，符合前轮授权面；commit 过程本身未审计 |
| `participant_list_status=partial` ∧ 空参与物的真实发生频率 | 未统计（现行写入路径分析表明恒非空，未对 1586 事件逐一实证） |

## 6. 结语

规则级语义可接受、可冻结；四条措辞澄清建议随冻结文本落。本报告
不构成化学终认，不解除 D-2 前置与对外引用限制；最终采信顺序归 CC。
