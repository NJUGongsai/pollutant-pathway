# mimo 化学评审回应（chain12 40 题 superset partial 现况·§五化学面）

> Provenance：通道 A（opencode / mimo-v2.6-flash-free 免费网关），
> 2026-10-14，v43 仓根发起，exit=0。请求
> docs/REVIEW_REQUEST_PARTIAL40_2026-10-14.md 拼只读边界头单一提示词；
> 原始输出 /tmp/mimo_p40_resp_raw.txt（主窗口保全）。mimo 自述只读
> 核对（含两份 qid 前缀逐题桶分类/谓词聚合表——主窗口判定：零金标
> 零题面零结构、本地消费未外带，边界完好，如实登记）。采信原则同
> AGENTS：评审独立性不背书，采信到与程序证据互证的程度；执行类
> 断言待验证。回应原文逐字保留（下文）。

---

[0m
> build · mimo-v2.6-flash-free
[0m→ [0mRead docs/REVIEW_REQUEST_PARTIAL40_2026-10-14.md 
[0m✱ [0mGlob "docs/*r36*.md" [90m2 matches[0m
> build · mimo-v2.6-flash-free
[0m→ [0mRead docs/mimo_ppv1_chem_review_response_r36.md 
[0m✱ [0mGlob "docs/TEACHER_*PPV1_T1*.md" [90m2 matches[0m
> build · mimo-v2.6-flash-free
[0m→ [0mRead docs/TEACHER_DECISION_PPV1_T1_COSUBSTRATE_TIER_2026-10-12.md 
[0m✱ [0mGlob "docs/*FREEZE*.md" [90m3 matches[0m
[0m✱ [0mGlob "docs/*root_only*.md" [90m0 matches[0m
> build · mimo-v2.6-flash-free
[0m→ [0mRead docs/TEACHER_REPLY_PPV1_T1_FREEZE_APPROVAL_2026-10-13.md 
[0m✱ [0mGrep "root-only|root_only" [90min docs · 40 matches[0m
> build · mimo-v2.6-flash-free
[0m✱ [0mGlob "docs/*2026-10-14*.md" [90m21 matches[0m
[0m✱ [0mGlob "docs/*PREREGISTRATION*.md" [90m2 matches[0m
[0m✱ [0mGlob "docs/*criteria_v2*.md" [90m0 matches[0m
> build · mimo-v2.6-flash-free
[0m→ [0mRead docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md [90m[limit=150][0m
[0m✱ [0mGrep "参考侧聚合探针|参考侧.*root-only 构图|298 张参考图" [90min docs · 5 matches[0m
> build · mimo-v2.6-flash-free
[0m→ [0mRead docs/C_COSUB_SUPPLY_DESIGN_PREREG_2026-10-14.md 
> build · mimo-v2.6-flash-free
[0m→ [0mRead docs/mimo_c_cosub_design_review_response_2026-10-14.md 
> build · mimo-v2.6-flash-free
[0m✱ [0mGlob "reports/**/refside*" [90m0 matches[0m
[0m✱ [0mGrep "refside_visibility" [90min . · 1 match[0m
> build · mimo-v2.6-flash-free
[0m✱ [0mGrep "第二底物型保留面|0/73" [90min docs · 1 match[0m
[0m$ [0mfind /Volumes/CC/Enzyme_Agent/dependingv43 -name "*refside*" -o -name "*reference_side*" 2>/dev/null | head -20
/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/c_probe_cosubgate_2026-10-14/refside_visibility.json
/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/c_probe_cosubgate_2026-10-14/refside_probe.py
/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/c_probe_cosubgate_2026-10-14/refside_visibility_summary.md
> build · mimo-v2.6-flash-free
[0m→ [0mRead reports/ppv1_s5b/c_probe_cosubgate_2026-10-14/refside_visibility_summary.md 
> build · mimo-v2.6-flash-free
[0m→ [0mRead reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/partial_breakdown.md [90m[limit=80][0m
[0m✱ [0mGrep "76→79|92→95|hit@3 \+9|\+3 / hit@3" [90min docs · 14 matches[0m
> build · mimo-v2.6-flash-free
[0m→ [0mRead reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/cs2c_side_predicates.md [90m[limit=70][0m
> build · mimo-v2.6-flash-free
[0m→ [0mRead reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/cs2c_side_predicates.md [90m[offset=71][0m
> build · mimo-v2.6-flash-free
[0m✱ [0mGrep "HARD_REJECT|hard_reject|O=O|NH3" [90min src/pathway_v43/pollutant/evaluation.py · 1 match[0m
[0m✱ [0mGrep "REACTANT_SIDE|reactant_side_exempt|PRODUCT_SIDE_EXEMPT|side_restricted|方向限定" [90min src · 2 matches[0m
> build · mimo-v2.6-flash-free
[0m→ [0mRead src/pathway_v43/pollutant/evaluation.py [90m[limit=70, offset=855][0m
> build · mimo-v2.6-flash-free
# mimo 化学评审回应 — REVIEW_REQUEST_PARTIAL40_2026-10-14 §五

**Provenance（先行）**：只读评审，无执行权限，未创建/修改任何文件，未读金标/题面原件（questions.jsonl、reference_graphs/ 未触碰）。实读：请求文本身、`TEACHER_DECISION_PPV1_T1_COSUBSTRATE_TIER_2026-10-12.md`、`TEACHER_REPLY_PPV1_T1_FREEZE_APPROVAL_2026-10-13.md`、`POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md`、`TEACHER_T1_FREEZE_DECISION_PACKAGE_2026-10-13.md`（片段）、`C_COSUB_SUPPLY_DESIGN_PREREG_2026-10-14.md`、r36 与 C 线两份我方既往回应、`refside_visibility_summary.md`（聚合）、`cs2c_side_predicates.md`、`partial_breakdown.md`（分类表）、`evaluation.py:855-924`。**如实披露**：后两份含 qid 前缀逐题桶分类/谓词表——零金标、零题面、零结构，但属逐题级聚合；如主窗口判定越搬运边界请标注。所有探针数字均为**转引，待执行验证**。题域 298/RHEA/已见题，不外推 dev。

---

## Q1（拆分公允性）【化学实质】→ **支持现状读法**

**root-only 实证不改变我的判断，只把它从"条件放行"加固成"前提已实测"。**

1. **判据①（参考侧系统性剥除）从推定变实证**：298/298 参考图仅 `root`+`principal_product` 两种角色、无任何共底物节点；我 r36 条件 4 要求的"参考侧出现豁免身份次数应为 0"实测 **0/298（涉题 0）**——豁免对象全部来自记录侧声明、退出信号干净。这条证据满足了我冻结前挂的条件，不是新争议。
2. **方向限定被新证据再加固一票**：豁免面（产物侧 H₂O/H⁺/Pi/PPi + 反应物侧仅 H₂O/H⁺）已按 r36 条件 1 落字于 `evaluation.py:871-875`，硬拒绝表 `:879-882` 在位（程序互证）。root-only 还给了反应物侧排除 Pi/PPi 一个新论据：**参考对磷酰供体身份零信息** ⇒ 若豁免，`A+Pi→A-P` 与 `A+PPi→A-P+Pi` 两个不可区分的酶学主张都会升 strict = 判分面发未挣的分；不豁免 ⇒ 两类事件诚实 partial，与 24 题同一逻辑。r36 的"塌缩+自指追溯"论与这条"金标无供体信息⇒strict 未挣"论同向。
3. **16→13 的剔除化学上是守恒必然、不是保守过拒**：反应物侧 O=0 而净产水 ⇒ O 凭空出现，事件方程自身不闭合，不配经豁免升 strict；维持 partial 不构成"判错"。本批边界实际形态很窄：12 个 H₂O **全部产物侧**（脱水/氧化型）、4 个 PPi 全部过非豁免 P 源（A6 半套簿记零出现）、H⁺/Pi 实例 0。

**两处口径登记（不阻断，沿 r36）**：① 表内"多写的身份 H₂O/H⁺/Pi/PPi"宜标"豁免面四类"，实际实例只有 H₂O/PPi 两类；② NH₃ 归"机制信息类"是**范围收窄措辞**而非化学定性（产物侧 NH₃ 可为脱氨真实产物）——不重开裁定，但别让这顶帽子进 v2 讨论。

## Q2（24 题不救论断）【化学实质】→ **支持现状读法，无应重开身份**

论断在 root-only 实证下**成立，且现在是三段证据链而非一段**：

- **(a) 结构层**：298/298 参考图 reactant 侧恒单 root、无共底物节点 ⇒ 生成时就不可能携带 NH₃/O₂/H₂O₂/OTHER；
- **(b) 桶定义层**：superset 的 extras 就是"参考该侧没有的身份"，加 misplaced=0/41（写错侧零实例）⇒ "参考无信息"是**构造性事实**，不是抽样观察；
- **(c) 落点层**：因此"诚实 partial（超出可核验范围）而非化学判错"正确，"豁免=洗白"红线判断成立——判分面本来就没有对机制主张的正向检测能力，豁免只是让它失明。

**OTHER 逐签名核（我 r36 M4-6 要的聚合已出）**：14 次多写、7 种元素签名——N1O2⁻（亚硝酸）、N1O3H/N1O3、C1H2O（甲醛样）、N1O3S1H2（硫酰胺样）都是真实含 C/N/S 分子＝机制成分；**无一落入四类簿记**（全表 P=0、无 O1H2 中性水形；cn 守卫 0/14 落入豁免集）。**无簿记噪音藏在 OTHER 里，无重开候选。**

**一处措辞修正**：应写"参考构图无该身份节点（298/298 结构实证）"，不写"参考里没有该分子"——C 线 refside 探针在有机桶实测 **12 题/8 身份与 principal_product 同身份**（产物侧重合真实存在，现行侧别口径不改判定，开侧别口子属契约裁定）。存量 40 因 superset 定义构造上排除了这种重合，风险低，但两句话的适用域要分开写。

## Q3（跨集合一致性）【口径】→ **支持（同一把尺子成立），附两个必须保持的披露**

- **同在哪**：同一豁免身份集与 cn 键、同一方向限定（C 设计 v2 已照抄，我的修正点 P4 关闭）、同一三谓词+完备二分单归属、同一硬拒绝表、机制类同一"声明后诚实 partial"落点、事件级一票否决同构；分账也干净（C 线 11 行纯簿记 + 34 行机制 = 45 行精确分档）。
- **差在数据、不在尺子**：pred1 的**证据可得性**不同——存量 41 事件声明链缺失 ⇒ unknown ⇒ 0 解锁（fail-closed，实现更诚实）；C 线新事件由模板记录发射声明链 ⇒ 可判。这是"同一契约 + 不同数据就绪度 + 旧批零回写"，不是两把尺子。**新旧结果不同必须落字为"存量 0 是数据未回填，不是 C 线用了更宽的尺子"**，否则外部读者会读成双标。
- **披露①（必须原样保留）**：C 线 pred1 是**构造性成立**（供给源=声明源=模板记录）——设计书 §三.5"pred1 证据含义=记录声明了它，防自我背书误读"这条必须进实施，否则新批 pred1 会被读成"模型独立主张获验证"。
- **披露②**：12 题产品侧重合按现行侧别口径不改判定、开侧别口子另行拍板（设计书已写，保持）。
- 我 C 线评审的 **P1（有机第二底物"金标无信息可核"未证）已被 refside 实证关闭**（reactant 侧保留面 0/73）；P2/P3/P4 均已在设计 v2 见到落实。

## Q4（预期管理）【口径】→ **部分支持——定性如实，数字口径 2 处必修、1 处需标注**

**如实的部分**：①"修尺子不修分数"逐字对齐 teacher 批复 §四（"+3 不得包装为进展"）；② 请求文自带三层防包装（模拟≠实施成绩、供给解锁面≠hit 预测、探针仅覆盖 43 题=下界）；③ "存量批解锁 0"与"模拟 13"并列、没把 13 说成已兑现——这是全请求最诚实的一句。

**修正点 A（规则级文件数字互斥）**：探针表（`cs2c_side_predicates.md` §1）的 +3/+9/+0 是**首命中位次分档新增**（3/9/0/只进U 1，合计 13；N1 行 3/11/1/1 合 16 与投影 95/140/145 自洽）⇒ 累计投影 = **95 / 138 / 142**（126+3+9、130+3+9+0），与预注册 §:80 一致；但**冻结拍板包 :12 写"126→135"（把 +9 当累计）**——两份规则级文件不能据同一句互推，Codex 已登记同款。需：拍板包补口径注/勘误，并把该记法统一命名"首命中位次分档新增"。

**修正点 B（U 方向疑误抄）**：预注册 §:80 "U +1"疑为探针列"只进U=1题"的误读——U=298−hit@5=168（N1 行 168→153=−15 恰为进 top5 题数），13 题情形 12 题进 top5 ⇒ U 应为 **168→156（−12）**而非 +1。需澄清"只进U"语义并加注。

**标注 C（基线不同源）**：teacher 批复/WORKPHASE 的"**76→79**"与探针/预注册的"**92→95**"是两个基线挂同一个 +3。需标注 76 属哪条链/哪个口径（或勘误），否则对外引用会撞。

以上三处都不推翻"模拟下界、非成绩、不包装"的定性结论。

---

## 总判定：**部分支持（列修正点）**

| # | 修正点 | 类型 | 动作 |
|---|---|---|---|
| 1 | 拍板包 126→135 vs 预注册 138/142 同句互斥（+9 累计 vs 分档读法） | 口径 | 以探针分档表为准统一措辞，拍板包补注/勘误 |
| 2 | "U +1"疑为"只进U=1题"误抄（U 实为 168→156） | 口径 | 预注册加注澄清 U 定义与方向 |
| 3 | "76→79"与"92→95"双基线 | 口径 | 标注链次/口径或勘误 |
| 4 | "金标无信息可核"措辞应限定为"参考构图无该身份节点"（有机桶存在 12 题产物侧重合，存量 40 构造上排除） | 化学实质+口径 | 请求文 §二/§四 措辞加限定 |
| 5 | NH₃"机制信息类"=范围收窄措辞非化学定性 | 化学实质 | 沿 r36 M1 登记，v2 讨论前勿被误用 |

**支持维持的核心**：豁免面方向限定与 16/24 拆分公允、24 题不救论断成立、新旧同一把尺子、"修尺子不修分数"的定性表述。

## 不确定 + 需要什么证据

1. **探针全部数字**（16/13、3/9/0/1 分档、0/645、43/43、0/298、0/14 cn 守卫）——转引，待隔离目录复跑/机读数据核对（工程面归 Codex）。
2. **OTHER 中 H1 中性×5、零原子电荷−1×3 的 cn 键**——需零结构的 cn 聚合清单确认描述（形如 [H] 自由基/电子）；**仅影响描述、不影响拦截裁定**（两者均非四类簿记）。
3. **U 的明文定义**——我按 298−hit@5 反推，需探针报告定义句坐实。
4. **存量 24 身份在参考产物侧的专项重合扫描**——现由 superset 定义+misplaced=0 推得风险低，未见针对存量身份的 refside 扫描；如需绝对化"零信息"，一个聚合计数即可。

**独立性声明**：本回应是化学判据面意见，不构成背书；声明链可满足性、双口径重判、数字链程序复核归 Codex（§六）；全部结论采信到与仓内文档/源码互证处为止，执行类断言一律待执行验证。
