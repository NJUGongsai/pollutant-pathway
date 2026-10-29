> **通道与 provenance（主会话 ZCode 记录，非 mimo 回应正文）**
>
> - 2026-10-09 清晨（S5a 回修 r2 轮内第③步自动送审，AGENTS.md「评审-回修自动循环」）：请求 `docs/mimo_ppv1_chem_review_request_r23.md`（自包含、无金标、只规则级+合成例）经 **opencode 免费模型 `opencode/mimo-v2.6-flash-free`** 只读评审；opencode 会话 `ses_ee2a93674ffevoyKPdS0PiVycy`（标题 "mimo ppv1 v23 chem review"）。与手机 mimo 应用是否同一实例未经证实，采信按本通道口径区分。
> - 一次运行完整输出（无断流、无 TLS 错误；opencode 服务自 04:12 起带代理环境运行）。
> - 评审为**只读**：执行类断言（1105 绿、6/6 B1 案、r1 二十案保持等）一律"〔待执行验证〕"；读码引用带行号，并按 r22 教训先核了 checked 构造器正规化行为再落字。其中 PPV1 1105 passed 已由主会话本机独立复跑证实（2026-10-09 清晨）；G01 安全隔离 1706/9/17 为交付方隔离证据，留 Codex 复核。
> - **本轮结论：三个判断面全同意（附落字条件），未发现与 ppv1-criteria-v1 冻结正文的 P1 冲突。**头条文案项：判断面三"known×unknown 按已知裁决"文字在 evaluation.py/preregistration.py/profile.py 五处须限定到物种键并删"顺序相关"尾巴（实现对、文字范围错，建议 evaluation-3/template-3 冻结前回修）；其余为落字建议（空单位假冲突代价条款、机读枚举写死 condition_unknown、environment_conflict_rate 分母披露、单调性条款、按 kind 暴露计数）与 P2 登记（事实侧 species+unit 静默忽略、value_raw 展示说明、restore 入口入 P2 表面）。
> - 请求原文：`docs/mimo_ppv1_chem_review_request_r23.md`。运行证据与原始输出：`docs/review_evidence/ppv1_s5a_rework_r2_mimo_2026-10-09/`。
> - 以下为 mimo 回应原文（仅清理终端控制字符，未做任何内容改动）。

---
# mimo 化学评审回应 r23:pollutant_pathway_v1 S5a 回修 r2 单位收口(判断面一~三)

**通道**:opencode mimo 只读评审(无执行权限;本轮全部执行类断言标〔待执行验证〕,不复跑代码)。
**我实际读过的文件**:`src/pathway_v43/pollutant/evaluation.py`(模块头、`_map_condition_scope_to_requirement`、`_build_frozen_facts`、`_classify_condition_requirement_detailed`、`classify_condition_requirement`、`classify_sample_conditions`、聚合指标段)、`src/pathway_v43/pollutant/path_context.py`(键集/单位表、`ConditionFact`、`build_condition_fact`、`build_requirement`、`_unit_ok`、`_assess_species_requirement`、`_assess_requirement`、restore 入口)、`src/pathway_v43/pollutant/preregistration.py`(condition_policy 文案)、`src/pathway_v43/pollutant/profile.py`(版本登记)、`tests/test_ppv1_s5a_rework_r2.py` 全文。
**未确认**:test_ppv1_s5a_schema.py 的 `condition_scope` 助手字段细节、test_ppv1_s5a_rework_r1.py 的 `_condition_case` 内容(仅见 import,未读);path_context.py 相对父基线的字节一致性(本轮无 git 读取)——〔待执行验证〕。按 r22 教训,本轮先核了 checked 构造器正规化(path_context.py:406-407:status=unknown ⇒ `value=None`)再落字。

---

## 判断面一:要求侧单位支持在映射首消费处决定

### 问 1① 空单位 canonical-by-key 默认是否正确口径

**结论:同意(有条件)。** 代码与请求表述一致:`temperature_C` 允许集 {°C, C, celsius}、pH 允许集 {"", pH, dimensionless}(path_context.py:163-166);空单位对 temperature 产出 `requirement_unit_not_declared`/`requirement_unit_canonical_by_key` 披露但**不返回 None**(evaluation.py:1075-1087),对 pH 不产生披露(允许集含 "",1075 条件不成立)。化学上,键名 `temperature_C` 本身就是量纲声明,这与冻结 R4-03「要求值恒为键规范单位」(path_context.py:563-567)一致——要求侧是**作者的规范性声明**,声明载体就是键名,空单位只是省略了冗余注记。反过来「空单位⇒unknown」会把参考图里绝大多数天然不带单位的要求整批推进 unknown,等于废掉 conflict/compatible 轴,属**收得过紧导致漏报(可判性漏报)**,且与冻结契约精神相悖。**条件**:(a) canonical-by-key 默认派生的每个判定都必须携带 `requirement_unit_not_declared` 披露——我核到详细分类器所有冻结路径返回都带 `mapping_disclosures`(evaluation.py:1260-1265、1280-1284),sample 级对每条要求无条件转录披露(evaluation.py:1356-1360),结构成立〔端到端 compatible/conflict 行的披露落盘待执行验证〕;(b) 落字建议见下。

**可落字建议**:
1. 规则文字写死空单位默认的**代价条款**:"若作者实际按 K 意图填数值且漏写 unit,298 会被读作 298 °C 判 conflict(披露随行)——读 temperature 行的 conflict/compatible 前先看 `requirement_unit_not_declared` 披露"。这个代价目前只在测试里可见(tests:175-177 钉空单位 "298" ⇒ `essential_conflict`),规则正文没写。
2. 落字写具体机读枚举:单位失败的 classification 实际取值是 **`condition_unknown`**(evaluation.py:1220-1224);`condition_unsupported_key` 只用于键集外(1167-1173)。请求与 docstring 里的"unknown/unsupported 族"是族名,不是枚举值,建议文字写死,防止读者以为单位案会进 `condition_unsupported_key`。

**结构性缺陷**:本面无明显过紧;不彻底侧见问 ④ 的披露强度问题。
**程序诚实但化学误导风险**:上面 1 的空单位假冲突——机读层诚实(披露随行、reason 是 canonical_by_key),但一个把 298 K 意图写成空单位的作者会得到一个**读起来像化学不相容**的 essential_conflict。披露能否被人类读者真正消费,是本面唯一实质风险点。

### 问 1② 非规范单位降 unknown 而非 conflict:保守方向对吗

**结论:同意。** 代码核对:temperature 配 "K"/"F" ⇒ `requirement_unit_noncanonical` 披露 + 返回 None(evaluation.py:1060-1074)⇒ `condition_unknown` + `requirement_unit_not_representable`(1214-1224)。判别守门成立:映射失败发生在 `build_requirement`/`aggregate_environment_fit` **之前**,所以该 unknown 的 reason 不可能是 `no_applicable_fact`(764-766)或 `necessity_unsourced`(761-762)——测试 tests:130-137 正是钉这一点,与代码路径互证〔待执行验证〕。"真实存在的温度不合漏报成 unknown"确实会发生(如 25 K vs 25 °C,换算后是极端不相容,但首版只能报 unknown)——这是**诚实的不可评估**,不是漏报式掩盖;方向正确,因为另一侧(按数值直比)会把披露与分类打脸(复审 R2 §4 的原 P1)。unknown 被读成"无冲突"的防线我核到两层:`environment_conflict_rate` 是**分桶无标量**(evaluation.py:1799-1808),note 明示"unknown 不计冲突";sample 级 note 同句(1380-1381)。

**可落字建议**:`environment_conflict_rate` 的 note 增加一句"**分母含 condition_unknown(含单位不可表示)等不可评估桶;首版无 K/F 换算 ⇒ 温度单位类要求在本指标中系统性不可判,不得解读为低冲突**"。残留风险只在下游自行拿桶数算比值的人,这句话是最低成本的护栏。

**结构性缺陷**:接受"过紧→unknown"的方向,但要如实登记其代价——冲突率的**分子**对单位不合规的参考要求永久失明;这不是本轮能修的(不新增换算是既定边界),属于要随指标 note 长期携带的已知偏差。

**程序诚实但化学误导风险**:低。unknown 桶名与 reason 码都是诚实的;唯一注意点是"25 K 极端不相容却只报 unknown"这类行,读者可能反向推论"评审员不认为它冲突"——上面的 note 建议即针对此。

### 问 1③ 物种键(electron_acceptor)配 mg/L:降 unknown 合适还是应结构化拒绝/单独分桶

**结论:同意降 unknown/unsupported 族(有条件:建议单独分披露子码计数)。** 代码核对:species 键不在 `CONDITION_KEY_UNITS`,`allowed_units is None` 且 unit 非空 ⇒ `requirement_unit_unexpected` + None(evaluation.py:1044-1058)。化学上,这个声明形状背后有两种**不可区分**的意图:(a) 单位是装饰性误填,要求实质是"O2 必需";(b) 单位携带浓度阈值语义(O2 ≥ 5 mg/L),首版实体比对表示不了。若为了"少报 unknown"而忽略单位、降级成实体比对,就是**收得不彻底仍有化学误导**——会把 (b) 类要求授 compatible,而作者要的其实是浓度保证。所以现状方向正确。**条件**:披露 kind 已经把两类单位失败分开(`requirement_unit_ununexpected` vs `requirement_unit_noncanonical`,1044-1074),但聚合层 `environment_conflict_rate` 只汇总 classification 桶、不汇总披露 kind(1738-1743)——两种修法(需要改声明的 curation 错误 vs 需要换算的表示缺口)在聚合里混成一个桶。

**可落字建议**:规则文字补一句判据理由:"实体键挂单位不可区分'装饰性误填'与'浓度阈值语义',故不做忽略单位的实体比对降级——未知不代表要求不存在"。另建议(非阻塞)聚合侧按披露 kind 暴露计数,便于 curation 定向修声明形状错误。

**结构性缺陷**:聚合层 kind 不可见(如上),属轻度"不彻底披露",不误导判定方向。
**程序诚实但化学误导风险**:无新增;现状的 reason 码 `requirement_unit_not_representable` + kind 区分是诚实的。

### 问 1④ 机读保留原 unit/value/key 是否足够;要不要换算建议附注

**结论:基本足够;建议两处加强(有条件同意"不执行换算"边界不动)。** 代码核对:三类单位披露均保留 key/unit/value(及非规范时 allowed_units)(evaluation.py:1046-1087),sample 级原样转录(1356-1360)。两个可改进点:
1. `value` 字段存的是 `repr(raw_value)` 字符串(1050、1065、1080)——机读消费者拿到的是 `"'298'"` 这种带引号的展示串。建议并列增加一个 JSON 原生的 `value_raw` 字段,或在规则文字里写明 `value` 仅供展示(勿 eval)。
2. **换算附注:建议加,但只加静态公式串、不按值计算。** 即在单位失败披露的 note 里附"仅披露不执行:K→°C 差 273.15;°F→°C =(x−32)×5/9"这类**字面文本**。化学价值:人类复核员看到"298 K vs 25 °C ⇒ unknown"能立刻明白换算后其实相容,unknown 的语义是"首版不可判"而非"疑似不合";这正是防"unknown 被读成无冲突/有冲突"的最便宜手段。边界纪律:**不得**把公式对 value 做计算(一旦输出 "298 K ≈ 24.85 °C" 就等于把换算语义偷渡进 v1,违反本批"不新增 K/F 换算"边界)。静态文本 + "是否采纳换算属 teacher 裁定"标注即可。

**结构性缺陷**:无。
**程序诚实但化学误导风险**:见上——"不可判"与"判了"在人类阅读里只隔一条 note;加强披露是唯一不需要动判定语义的收口。

---

## 判断面二:要求侧 canonical-by-key 默认 vs 事实侧来源单位三态的分立

### 问 2① 不对称是否站得住

**结论:同意,不对称在化学上站得住。** 冻结侧核对:事实侧三态在 `_assess_requirement`(path_context.py:790-803):带量纲键空单位 ⇒ `source_unit_unknown` ⇒ unknown(791-797);非规范单位 ⇒ `unit_mismatch` ⇒ unknown(798-801);pH 空单位合法(`UNIT_REQUIRED_KEYS` 只含 temperature,171;pH 允许集含 "",165)。`build_requirement` 无 unit 形参(554-560),要求侧单位根本进不了冻结侧——分立是结构性的,不是补丁。化学理由:**要求是规范声明**(键名即量纲,作者对语义负责,省略冗余注记可按约定消费);**事实是观测记录**(来源单位是证据属性,未声明就是未证,不能拿要求侧的约定替观测背书)。应当对称处理的场景我没想到;测试 tests:183-212 正钉"要求侧默认不升级事实侧缺单位"〔待执行验证〕。

**可落字建议**:
1. 规则文字补**单调性条款**:"要求侧单位注记越具体,判定只会从 compatible/conflict 移向 unknown,绝不反向——诚实注记不被惩罚"。这句话是本设计最有力的自辩护(显式 K 得到诚实的 unknown,漏写却可能得到自信的 conflict),值得写进正文防止未来被"简化"。
2. 补一条**事实侧形状不对称的如实登记**(我读码发现,请求未提):要求侧 species 键挂 mg/L ⇒ unknown(如面一);但**事实侧** species/enum/matrix 键的 unit 是被静默忽略的——单位三态检查只对 `CONDITION_KEY_UNITS` 键生效(path_context.py:790 的 guard),`build_condition_fact` 也不校验 unit(382-432)。即事实写 "O2 present, mg/L" 会照常按实体判 compatible。这属**冻结侧行为**,不属本轮 r2 收口范围,但建议以 P2 形态向 teacher 登记(与 A1/C1 同式),理由:若该 unit 携带"低于阈值的浓度"语义,静默忽略即"程序诚实但化学误导"的轻微形态。

**结构性缺陷**:如上第 2 点——事实侧声明形状纪律弱于要求侧,方向上是"不彻底",但改动属冻结侧、teacher 裁定。
**程序诚实但化学误导风险**:事实侧 mg/L 被忽略那类行:程序链全程诚实(无伪造、无换算),但 compatible 的化学含义比读者预期的窄(只证实体在场,不证浓度达标)。建议至少在 P2 登记文本里写明这个语义窄面。

### 问 2② 事实侧缺单位=unknown 是否过保守;同导出推断留给 teacher 是否正确

**结论:同意现状,推断边界留给 teacher 正确。** "同一导出内其他温度事实都带 °C ⇒ 推断本条同单位"不成立的原因:一个批次内混入 K 源记录是现实可能的(多来源汇编),跨记录推断会把错误单位**静默传播**到本该 unknown 的行,比现在的保守 unknown 更糟;且该三态是冻结 R4-03 已定语义,本轮动它就破坏"冻结 path_context 字节不动"的边界。留 teacher 是对的。

**可落字建议**:规则文字加一句封口:"同导出内同键其他事实带规范单位**不构成本条事实的单位证据**;是否允许导出级单位归一推断属 teacher 裁定,评测侧不实现"。防未来有人以"减少 unknown"为名加推断。

**结构性缺陷**:无(保守方向,漏报以 unknown 承载,诚实)。
**程序诚实但化学误导风险**:无。

---

## 判断面三:B2 文案更正——文字与实现同真

### 本面头条发现(冻结前须修文字,条件级)

"known×unknown 混合按冻结侧首条已知事实裁决"这句在实现里**只对物种键成立**。冻结代码:物种键走 `_assess_species_requirement`(path_context.py:769-771 → 701-733),unknown 事实经 checked 构造器值清 None(406-407)后 `f.value == entity` 永不命中(714),故 `same` 只含已知事实、按其裁决——请求的四个两序例与代码一致〔待执行验证〕。但**非物种键**(temperature_C、pH、oxygen_regime、matrix,共 4/7 键)走通用路径:任何一条 unknown 适用事实 ⇒ `fact_unknown` ⇒ unknown(path_context.py:778-779),**比"按已知裁决"更保守**。而无范围限定的表述出现在 evaluation.py:77-78、1136-1138,preregistration.py:20、137-141,profile.py:267-268——即模板 condition_policy 正文本身。本面标题就是"文字与实现同真",按现状文字,读者会误推"温度要求带一条 unknown 事实仍按已知 °C 事实判 compatible",实现实际报 unknown。**这是本评审唯一必须修的项**:实现侧无需改动(保守方向正确),须把上述五处文案限定为"**物种键** known×unknown 按已知事实裁决;非物种键任一 unknown 适用事实即 unknown"。不修就冻结,等于把一条对 4/7 键不成立的规则写进 proposed 契约。

**附带一处措辞**:evaluation.py:78 的"(既有实现,顺序相关)"不准确——合法 checked 链上 known×unknown **两序同判**(unknown 值为 None 根本不进 `same`),次序差异只存在于绕过构造器的低层路径(见问 ③)。建议改为"合法链两序同判;次序差异仅低层绕过路径(P2)"。请求正文的"两序均按首条已知事实裁决"本身没错,错在代码 docstring 的"顺序相关"尾巴。

### 问 3① known×unknown 按已知裁决:可接受还是应保守 unknown

**结论:有条件同意(限物种键)。** 化学理由:**存在性证据逻辑**——一条经核的 present 检出即确立"该实体在场",一条经核的 absent 即确立"必需实体不在场",另一条状态未定的记录既不推翻也不补强;对 essential 的"实体必须在场"要求,已证缺席 ⇒ conflict 是"就给定记录集"的结论(冻结 docstring 本身就把 compatible/conflict 定义为给定事实集的结论)。**条件**:如上,文字限定物种键,并把"物种键(存在性逻辑,按已知裁决)vs 量值键(状态逻辑,任一 unknown 即 unknown)"的**键族不对称**作为显式口径写进规则文字或向 teacher 备案。若 teacher 日后要统一成保守 unknown,那是冻结侧语义变更,与低层 P2 同属 teacher 裁定范围——本请求不改是对的。

**可落字建议**:规则文字加一句判据理由:"物种键的 present/absent 是存在性断言,单条已知记录即可定;量值键的多条事实描述同一状态量,任一 unknown 都实质动摇取值——两族不同判由此而来"。

**结构性缺陷**:不对称若不写明理由,未来读者很可能把它当 bug"修平",届时反而制造真正的口径漂移。
**程序诚实但化学误导风险**:低;风险集中在上面头条的文字问题,不在判定。

### 问 3② "未列出的实体 ≠ absent"在物种键上是否正确

**结论:同意(强)。** 代码核对:无自身事实 ⇒ `entity_not_among_known_facts`/`no_applicable_fact` ⇒ unknown(path_context.py:716-722)。生物降解数据里供体/受体清单不完备是常态(文献极少穷举所有电子受体),把"未列出"当 absent 会批量制造假 essential_conflict——那是灾难性的过紧。现状代价是:物种 essential 要求在没有显式 absence 记录时几乎不产生 conflict,冲突率分子偏小——这是诚实方向,由 unknown 桶承载。

**可落字建议**:无需改;可在规则文字里把这句与"清单不完备是常态"的理由一并写入,防止未来以"提高冲突检出"为名收紧。

**结构性缺陷**:无。
**程序诚实但化学误导风险**:无(方向诚实)。

### 问 3③ 低层 dataclass 绕过 checked 构造器的次序边界列 P2 而不修:处置是否正确

**结论:同意处置正确(P2 归 teacher);但我把 P2 的实际面核实得更具体,建议登记文本照抄。** 评测器公共链经 checked 构造器建事实(evaluation.py:1109),评测器自身的判定不受次序边界影响——测试 tests:288-290 钉 `build_condition_fact(status="unknown")` 值为 None〔待执行验证〕。读码发现该边界**不止"直接 dataclass 直构"一条路**:restore/反序列化入口用 `ConditionFact(**f)` 从存储 dict 直接重建事实(path_context.py:2055),不经 checked 归一;而同段对 requirements 有 `validate_requirement_dict` 预校验(2053),facts 无对应校验;`ConditionFact.__post_init__` 只做嵌套冻结、不校验 status/value/unit(350-353)。即"unknown + 实体值"的事实可经**存储恢复入口**(不只是临时手写直构)流入评估,次序差异因此是可经正门到达的,不是纯理论边界。建议 P2 登记文本明确点名该入口(措辞示例:"restore 入口 ConditionFact(**dict) 不经 checked 归一,unknown+实体值可入评估并激活 same[0] 次序差异;是否在恢复入口补齐归一/校验属 teacher 裁定")——这同时呼应本仓"身份与完整性在首次消费时闭合"的返工教训。不修冻结侧对象语义归 teacher,同意。

**可落字建议**:如上,把 P2 的表面从"低层直构"修正为"直构 + restore 入口"。

**结构性缺陷**:无新增(P2 已登记,范围描述需按上文精确化)。
**程序诚实但化学误导风险**:若外部消费者(评测器之外)用 restore 入口喂事实并把结果当科学结论,可能得到顺序依赖的 conflict/unknown——诚实性在评测器契约内无损,契约外的误用风险由 P2 登记文本承担说明义务。

---

## 逐条汇总

| 条目 | 结论 | 冻结前须做 |
|---|---|---|
| 一① 空单位 canonical-by-key | 同意(有条件:披露随行已核,建议补代价条款) | 落字"空单位默认的假冲突代价" + 写死机读枚举值 condition_unknown |
| 一② 非规范单位降 unknown | 同意 | 建议 environment_conflict_rate note 补"分母含不可评估桶" |
| 一③ 实体键挂单位降 unknown | 同意(不可区分装饰误填与阈值语义,不做实体降级) | 落字判据理由;建议聚合按 kind 暴露计数(非阻塞) |
| 一④ 机读保留 + 换算附注 | 基本足够;附注建议加**静态公式串、不按值计算** | value_raw 或"value 仅供展示"说明 |
| 二① 两侧不对称 | 同意 | 落字"声明越具体判定越保守(诚实不惩罚)"单调性条款;事实侧 species+unit 被静默忽略一事建议 P2 登记(冻结侧,teacher) |
| 二② 事实缺单位=unknown | 同意;推断留 teacher 正确 | 落字"同导出同键他条单位不构成本条单位证据" |
| 三头条 known×unknown 文案 | **不同意现状文字(实现对、文字错范围)** | **五处限定到物种键**(evaluation.py:77-78、1136-1138;preregistration.py:20、137-141;profile.py:267-268);删"顺序相关"尾巴 |
| 三① 按已知裁决 | 有条件同意(限物种键;键族不对称须写明理由并可备案 teacher) | 落字存在性 vs 状态量的判据理由 |
| 三② 未列出≠absent | 同意(强) | 无 |
| 三③ 低层边界 P2 | 同意;P2 表面应含 restore 入口(path_context.py:2055) | P2 登记文本精确化 |

**与冻结判据冲突检查(P1 项)**:未发现。r2 的单位收口只发生在评测侧映射(映射失败在 build_requirement/aggregate 之前短路),冻结 `_assess_requirement` 三态与判据一~五消费语义未被触碰;criteria-v1 与 FREEZE_RECORD 有测试内 SHA 守卫(tests:334-373)〔守卫实际执行与 path_context 字节一致性待执行验证〕。

**执行边界声明**:本轮零执行;所有测试结果、端到端桶传导、6/6 与 4 降 2 保持、r1 二十案保持、版本号断言均为读码互证 +〔待执行验证〕。以上为完整评审回应;按"采信到与程序证据互证为止"处理,头条文案项建议在 evaluation-3/template-3 冻结前回修。
