# mimo 化学评审请求 r23:pollutant_pathway_v1 S5a 回修 r2 单位收口后的化学判断面

日期 2026-10-09。本请求**自包含、只含规则级表述与合成例**(如
CCO/CC=O/[H][H]/温度 K/F/C 与氧/电子受体标签),不含金标/题面/
封存逐题 run 数据,不含任何真实 dev/298 指标数值;由用户送 mimo,
回复原文落盘。触发点:AGENTS.md 化学评审三类之 1(需评判条件/
守恒口径——S5a 回修 r2 改动了评测器条件分类的**要求侧单位消费
语义**,冻结前需化学复核)。**评审独立性不做背书;结论采信到与
程序证据互证的程度为止;本请求只问规则级判据,不请求任何执行
声明。所有"已执行"字样的程序事实均标注〔待执行验证〕,mimo 不
复跑代码。**

---

## 0. 背景(一段)

S5a 回修 r1 的四组修复经 Codex 正链 R2 复审(2026-10-09):
S5A-01/03/04 关闭,S5A-02 旧核心(18 同源对照 + 2 负要求单列)
确认,但**唯一残余 P1**:参考要求侧显式声明的非规范单位(如
temperature_C=298 配 unit=K)被识别并披露后**在适配时丢弃**,值
按键规范单位直比送入冻结 Requirement——298 K 被当 298 °C 判
essential_conflict、25 K 被当 25 °C 判 compatible(披露文字与分类
互相打脸;缺表示能力被实际授了相容/冲突)。本轮回修 r2 按
"映射首消费处决定单位支持能力"最小收口,登记
`ppv1-evaluation-3`(分类语义变更不偷换同一已登记契约;
criteria-v1 冻结正文与 FREEZE_RECORD 逐字节不改;不新增 K/F
换算/单位 label 库/负要求表示)。同时按复审更正一处文案事实
(B2:合法公共链 unknown 事实经 checked 构造器值清 None)。
请评审以下三个判断面是否把口径收对了——是否存在"收得过紧
导致漏报"或"收得不彻底仍有化学误导"。

## 1. 判断面一(修复 S5A-02 r2):要求侧单位支持在映射首消费处决定

**修复后规则**:ConditionScope(参考条件要求)→ 冻结 Requirement
的**共同映射首消费处**决定单位支持能力:

- 冻结契约:Requirement **要求值恒为键规范单位**(键名即量纲:
  temperature_C ⇒ °C;pH 无量纲),构造器无 unit 形参;
- **显式规范单位**(temperature_C 配 °C/C/celsius)⇒ 合法,与
  canonical-by-key 默认一致;
- **空单位** ⇒ **canonical-by-key 默认合法不降档**(要求值按
  键规范单位约定消费;机读披露 kind=requirement_unit_not_
  declared、reason=requirement_unit_canonical_by_key——评审要求
  "明确按冻结键规范单位约定,不要求全面拒空");
- **显式非规范单位**(temperature_C 配 K/F)或**无量纲键声明
  单位**(物种键 electron_acceptor 配 mg/L)⇒ **无合法冻结表示**
  ⇒ 分类进 unknown/unsupported 族(reason=requirement_unit_
  not_representable),机读披露保留**原 key/unit/value/
  allowed_units/原因**——不丢弃单位后授 compatible/conflict、
  不做 K/F→°C 换算、不猜测单位语义;sample 分类与聚合同源
  传导(桶不再记 compatible/essential_conflict)。

**合成例**(六案与复审 R2 §4.1 同案构造,真实公共链合成 run,
无金标;复审断言 before 4 失败/2 通过、after 6/6 通过
〔待执行验证〕):

| 参考要求(合成参考图) | 同源真实事实 | 修复前(父) | 修复后(r2) |
|---|---|---|---|
| temperature_C=298,unit=K | 25 °C known_present | essential_conflict | **condition_unknown**(requirement_unit_not_representable) |
| temperature_C=25,unit=K | 25 °C | compatible | **condition_unknown** |
| temperature_C=77,unit=F | 25 °C | essential_conflict | **condition_unknown** |
| electron_acceptor=O2,unit=mg/L | O2 无单位 present | compatible | **condition_unknown** |
| temperature_C=25,unit=C | 25 °C | compatible | **compatible**(正控保持) |
| temperature_C=25,unit 空 | 25 °C | compatible | **compatible**(canonical-by-key 默认;披露改约定说明) |

判别守门(复审要求"有合法事实+有必要性来源,不用 facts= []
天然 unknown 冒充"):K 单位案的事实 25 °C 与 source_refs 均在场,
unknown 的 reason 是 requirement_unit_not_representable(非
no_applicable_fact/necessity_unsourced);同案单位改空 ⇒ 恢复
合法判定〔待执行验证〕。

**问 1**:
①"要求值恒为键规范单位、空单位按 canonical-by-key 默认"是否
正确的化学口径?是否应当反过来**要求显式单位**才参与比较
(空单位视为声明不完整 ⇒ unknown)?
②非规范单位(K/F)降 **unknown** 而不是 conflict——保守方向对
吗?会不会把"真实存在的温度不合"漏报成 unknown(298 K 对 25 °C
在物理上若换算并不冲突,但首版无换算;若换算则 25 K 是极低温、
必冲突)?unknown 与"不可评估"在环境冲突率里如何避免被读成
"无冲突"?
③物种键(electron_acceptor)配 mg/L:浓度单位挂在实体键上属于
**声明形状错误**而非"单位不支持"——降 unknown/unsupported 是否
合适,还是应结构化拒绝/单独分桶?
④机读保留原 unit/value/key/原因是否足够可审计?还需要单位
换算建议(K→°C 差 273.15)作为披露附注吗(仅披露、不执行)?

## 2. 判断面二:要求侧 canonical-by-key 默认 vs 事实侧来源单位三态的分立

**修复后规则**:要求侧与事实侧单位语义**分立**,不互相覆盖:

- **要求侧**(参考图 ConditionScope):如上,canonical-by-key
  默认/显式规范单位合法/非规范无表示降 unknown;
- **事实侧**(导出 contexts 的 condition_facts):来源单位三态由
  冻结同源 `_assess_requirement` 裁决,**不受要求侧默认影响**:
  带量纲键(temperature_C)事实**必须显式规范单位**才数值比较
  (canonical);**空单位 ⇒ source_unit_unknown ⇒ unknown**(原
  来源单位未知,不按数值直比);**非规范单位 ⇒ unit_mismatch ⇒
  unknown**(首版无换算);pH 空单位合法;物种/枚举/matrix 键
  不带单位。

**合成例**〔待执行验证〕:
- 要求 temperature_C=25(空单位,canonical-by-key)+ 事实
  25 无单位 ⇒ **condition_unknown(source_unit_unknown)**——
  要求侧默认**不**把事实侧缺单位升级为已归一;
- 要求 temperature_C=25(空单位)+ 事实 25 °C ⇒ compatible;
- 要求 temperature_C=25(空单位)+ 事实 25 K ⇒
  condition_unknown(unit_mismatch);
- pH:要求 6.5-7.5(空单位)+ 事实 7 ⇒ compatible(无量纲键
  空单位本就合法,无 not_declared 披露)。

**问 2**:
①这个**不对称**(要求侧按声明约定、事实侧按来源证据)在化学
上是否站得住——即"要求是作者声明(键名已定量纲),事实是观测
记录(来源单位必须显式)"的区分是否合理?有没有应当对称处理
的场景?
②事实侧"缺单位=未知来源单位⇒unknown"是否过保守(比如同一导出
内其它温度事实都带 °C,可否推断本条同单位)?本轮不实现推断,
该边界留给 teacher 是否正确?

## 3. 判断面三(B2 文案更正):多事实口径的文字与实现同真

**更正后的事实表述**(文字已与实现同步;实现零改动,冻结侧
不动):

- 合法公共链的 unknown 事实经 checked `build_condition_fact`
  **值清为 None**(unknown ⇒ 值不可知、不带身份)——mimo r22
  把 `_assess_species_requirement` 取首条解读为"合法链顺序相关"
  的推论**不成立**(经复审 R2 §5-B2 十个真实公开两序案确证);
- 同键**相反**事实(present×absent)两序均 ⇒ unknown
  (conflicting_applicable_facts;请求 r22 只承诺过这一条,实测
  成立);
- known×unknown 混合:两序均按**首条已知事实**裁决(present ⇒
  compatible;absent ⇒ essential_conflict)——不是"任意多事实
  皆 unknown";
- 直接 dataclass 构造 `ConditionFact(value='O2', status=
  'unknown')` 绕过 checked 构造器时,冻结公开 assess 确有
  `same[0]` 次序差异——这是**低层对象支持边界**,登记 P2 不在
  本契约内;是否改冻结侧物种/多事实语义归用户/teacher 裁定。

**合成例**(electron_acceptor=O2 essential 要求)〔待执行验证〕:
- [O2 present, O2 absent] 与 [O2 absent, O2 present] ⇒ 两序均
  condition_unknown;
- [O2 present, O2 unknown] 与 [O2 unknown, O2 present] ⇒ 两序
  均 compatible(unknown 事实值已清 None,不进同实体组);
- [O2 absent, O2 unknown] 与 [O2 unknown, O2 absent] ⇒ 两序均
  essential_conflict;
- [O2 present, NO3 present] ⇒ compatible(多值并存);
- [NO3, Fe3] 而 O2 缺席 ⇒ condition_unknown(未列出 ≠ absent)。

**问 3**:
①"known×unknown 混合按已知事实裁决"是否可接受的化学口径,
还是应当保守 unknown(存在一条 unknown ⇒ 该键未知)?首版沿
冻结实现,是否属 teacher 冻结前须裁定的口径?
②"未列出的实体 ≠ absent"(entity_not_among_known_facts ⇒
unknown)在物种键上是否正确(供体/受体清单不完备是常态)?
③低层 dataclass 绕过 checked 构造器的次序边界列 P2 而不修——
处置是否正确(改冻结侧对象语义属 teacher)?

## 4. 请求汇总

| 面 | 修复/更正 | 关键问 | 程序事实 |
|---|---|---|---|
| 一 | 要求侧单位首消费收口(非规范/无量纲键单位 ⇒ unknown/unsupported + 机读保留原值;空单位 canonical-by-key 默认) | 空单位默认/降 unknown 方向/实体键挂单位/机读充分性 | 六 B1 合成案 4 降 2 保持、复审契约断言 6/6〔待执行验证〕 |
| 二 | 要求侧 canonical-by-key 默认 vs 事实侧来源单位三态分立 | 不对称合理性/事实缺单位过保守边界 | 事实三态正控保持、要求空单位不升级事实缺单位〔待执行验证〕 |
| 三 | B2 文案更正(checked 值清 None;相反两序 unknown;known×unknown 按已知) | known×unknown 口径/未列出≠absent/低层边界 P2 | 十个两序公开案实测成立(复审 R2 执行)〔待执行验证〕 |

边界重申:不新增 K/F 换算、单位 label 库、负要求表示、
preference 语义;不改冻结 path_context/criteria-v1/FREEZE_RECORD;
A1(根配对)/C1(participant_list_status)等晨报 P2 保持登记
不在本请求范围;18 旧同源条件 + 2 required_absent 单列保持
〔待执行验证〕。请逐面回答:该修复是否把口径收对了?哪里收得
过紧/不彻底?有没有应单列的化学误导风险?以上为完整评审请求;
mimo 回应原文将落盘 `docs/`,结论按"采信到与程序证据互证为止"
处理。
