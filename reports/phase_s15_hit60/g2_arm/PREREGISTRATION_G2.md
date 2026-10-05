# PREREGISTRATION_G2 — T8 G2 novel 守恒过滤 + 自产 5 候选自排序(合并设计,冻结版正文)

> **版本 v2**(2026-10-05,v1→v2 修订)。v1 正文见本文件历史读数与
> §5.1;v2 按 mimo 终版评审
> `docs/mimo_g2_rules_final_review_response.md`(A–G 全文)**9 条必改**
> 逐条修订,修订记录见 §0;fork 窗口草稿
> `reports/phase_s15_hit60/g2_prereg/PREREGISTRATION_G2_DRAFT.md` 的三处
> 独有内容已并入(判定线 spurious 净降 ≥3 / 对照方案 A/B 表述 / 三个
> 挂起拍板点)。

- 状态:**DRAFT v2(增侧惰性 (a) 已由用户裁决 2026-10-05;冻结待 mimo delta 确认)**。冻结生效链:
  本稿落盘 → `docs/mimo_g2_v2_confirmation_request.md` 送 mimo delta 确认
  (9 必改落法 + v2 重放读数,规则级零金标)→ 用户确认冻结 → FROZEN
  (整文件 SHA256 登记,此后看分后修改一律无效,I2)。
- 立项依据:[T8 任务书](../../../docs/TASK_V43_HIT60_S1R2_GENERATION_ARMS.md)
  §3 G2 设计、§5 预注册要求;[mimo 守恒判据评审回复](../../../docs/mimo_conservation_rules_review_response.md)
  (v1 改版蓝图)+ [mimo 终版评审回复](../../../docs/mimo_g2_rules_final_review_response.md)
  (v2 修订依据,9 必改 + 8 处背书不改)+ [采纳登记](../../../docs/MIMO_REVIEWS_ADOPTION_REGISTER.md)
  §2/§4 + [门 1 迭代 2 报告](../../../docs/HIT60_T8_GATE1_ITERATION2_REPORT.md)
  (两条硬约束,见 §3)。
- 题域与分母:dev v1.1 = **51 分母**(quarantine 已生效
  [QUARANTINE_EFFECTIVE](../gold_health_check/QUARANTINE_EFFECTIVE.md));
  判分口径 v3(component-aware 全主产物命中,`PREREGISTRATION_V3.md`);
  对照基线 **C0-a v3 = 14/51 = 27.5% @1**(双采样 C0-b 同参封存)。
  题域标签:dev = B1 环境路径中间步骤,数字不外推 298。
- **判定线先于任何付费跑冻结**(I2,对付费臂生效)。本任务内的离线重放
  属"已见 dev 数据的工程设计验证",其读数标注 **in-sample(非确证)**,
  只作发车建议,**不作臂判定**,见 §5 声明。
- 撰写纪律:2026-09-30(v1)/ 2026-10-05(v2 修订),零 LLM 零 API;分支
  v4.3,工作树未提交改动全部保留(两轮开工 `git status --short | head -30`
  均已记录);不 git commit。本文件不含任何金标内容(零 SMILES 零身份串,
  只有 qid/计数/旗标引用)。

---

## 0. v1→v2 修订记录(mimo 终版评审 G 节 9 条必改逐条落法)

评审原文引用节号见 `docs/mimo_g2_rules_final_review_response.md`
(A–G)。每条:评审必改 → v2 落法 → 落点。

| # | 评审必改(节号) | v2 落法 | 落点 |
|---|---|---|---|
| 1 | **G1-b 裂解判据重构为"碎片可重构"**(D-2,最高误杀风险) | 三通道统一判据 `_gap_reconstructible`:①三 motif 快路径(β-羟基羰基/β-二羰基/α-羟基酸,+**1,2-二羰基**);②封闭小碎片清单(v43-cons-frag-1:CO₂/CO/HCOOH/CH₂O/CH₃OH/乙酸/HCN/CH₃SH/NH₃/H₂S,须母体命中该碎片要求的官能团);③有界杂原子单键切搜索(P–O/酯 C–O/糖苷 C–O/酰胺 C–N/醚 C–O/磺酰胺 S–N/C–P;≤4 键、可切键 ≤128、求值预算 2048,超限 → 不可审计降位,绝不假放行)。匹配要求:硬元素(C/N/S/P/卤/金属)逐元素精确一致;O/H 自由元素不设界。**同一判据统一三处**:G1-b 允许集(ΔC_main≤−3)、ΔC=−1/−2 放行(R1 加条件)、②硬剔第三条件——糖苷/酯/酰胺/醚/磷酯/肽断裂在碳侧同样被认,修复"同一规则三处互斥"(毒死蜱 ΔC=−7 族、parathion −4、菊酯 −7、糖苷 −6、大酯/肽 ≥3 全部放行,夹具逐类钉住) | §2.1;`conservation.py` `_gap_reconstructible`/`_search_cover`/`FRAGMENT_CATALOG` |
| 2 | **②完整性硬剔加第三条件+关键词修缮**(A-3) | ②仅在"声明完整 ∧ 总碳减少 ∧ 缺碳无可重构碎片"三者同时成立时硬剔,否则降位(`declared_complete_loss_reconstructible`);关键词表 v43-cons-kw-2:英文词边界正则(`complete` 不再命中 `incomplete`)+ 前 2 token 否定回看(not/no/never/n't/without…)+ 封闭表补矿化措辞族(mineralized/mineralization/fully degraded/completely converted/quantitatively/彻底降解/矿化/完全转化/完全降解)+ 中文否定前缀字(不/未/非/没/难);**CO₂/H₂O 组分接口显式对齐判分口径**:缺失可重构为 CO₂/H₂O 族时②永不硬剔(金标组分集省略 CO₂ 时该候选仍可命中,降位保留其可及性) | §2.0;`conservation.py` `declared_complete`/judge ②分支 |
| 3 | **key 2 语义改"化学矛盾"、unclassified 归中性**(E-2/D-3) | key 2 只对"底物具备该可进攻基团而候选变换类与其化学矛盾"生效(transform 为已分类类目 ∉ 底物允许集 ∧ 允许集非空);`unclassified`/`isomerization`/`parse_fail` 一律中性落 key 3(分类器覆盖失败不是化学不可能的证据);补变换类:**环氧化/S-氧化/N-氧化**(+O 非羟化族,经"底物基团 + 产物子结构差"鉴别;羟化族归 oxygenation);同分异构放行仅 key 1 同档内生效(键序 tier 为首键,豁免不可能越过处置档与矛盾判据);另补归属:脱烷基(N-dealkylation)归 c1_release 族、偶联/二聚归 conjugation(增侧,当前门禁下惰性留位)、重排归 isomerization | §2.7;`conservation.py` `_classify_transform`/`NEUTRAL_TRANSFORM_CLASSES` |
| 4 | **增侧惰性声明**(A-1,评审二选一;**用户 2026-10-05 裁决选 (a)**) | **(a) 声明惰性 no-op 写死**:G1-a①增侧拒/G2-a 增侧/供体表放行三者在当前门禁次序的答案路径上不可达——既有元素白名单门(`gate_element_changes`:一步只允许 O 增加 ≤2)在答案记录路径上先于 G2 生效,v1 重放六批复封答卷剔除侧零触发(excl=0×6)为程序证据;**供体表降级为规格性文档**(v43-donor-registry-2,无操作行为;数值供未来参考);若未来臂放活增侧,须另立臂走自己的判定线,不得在本臂内改门禁次序(否则违反"单变量、纯后置、与现状逐字节一致")。选 (a) 而非 (b)(改门禁次序重走判定)系协调方建议,**用户已裁决生效(2026-10-05)** | §2.2;`conservation.py` DONOR_REGISTRY 注释 |
| 5 | **R1 放行加碎片重构条件 + ②优先级显式化**(A-6) | ΔC_main∈{−1,−2} 须碎片可重构(通道②③)且 \|ΔDoU\|<2 才 fragment_inferred 放行;保留四类应降位形态:**碎片不可重构**(G1b_fragment_not_reconstructible)/**跨元素不一致**(硬元素精确对账,如苄胺→苯的 C1N1 缺口对不上 HCN 因无腈基)/ **ΔDoU 异常**(\|ΔDoU\|≥2 或不可审计,仅约束 C1/C2 族;裂解族 ≤−3 的缺口碎片天然携带 π 键/环,不设此守卫)/ **与完整性声明叠加**(②先行,判定顺序写死:剔除 > 降位 > hold,② 在 G1-b 缺口放行之前) | §2.1;judge 顺序 |
| 6 | **编目对账+缺口补全**(D-4/D-5) | 计数对账修复:v1 文本写"25 条"而枚举 26/27 项不一致 → v2 编目 **34 条逐条枚举与计数一致**(夹具断言);补:**氨基甲酸酯**(carbamate,酰胺 SMARTS 不专覆盖)、**脲**(urea)、**磺酰胺**(sulfonamide)、**膦酸酯/C–P**(phosphonate_cp)、**季铵**(quaternary_ammonium)、**过氧化物**(peroxide)、**1,2-二羰基**(alpha_dicarbonyl)、**五元杂芳环**(heteroaromatic_5);声明**芳香性模型 = RDKit 默认**(sanitize 感知,六元含氮杂芳环走 aromatic_ring、五元杂芳环单列;芳香噻吩 S 不被脂肪硫醚 SMARTS 覆盖,属 heteroaromatic_5,登记为已知边界);声明**酯 SMARTS 无环限制 → 内酯已覆盖、缩醛条目覆盖糖苷端基碳**(C–O–C) | §2.4;`ATTACKABLE_PATTERNS` |
| 7 | **DoU 带电荷项或改由图算 + 去盐扩展多原子反离子**(F-2/F-3/C-2) | DoU 采用**分子图/价键算法**(DoU = 1 + Σ(vᵢ−2)/2,v=sanitize 后总价键数)——与 (2C+2+N−H−X+q)/2 等价且对五价磷(P=S)/六价硫/季铵(q 项)给出整数正确值(v1 中性式对毒死蜱类读出半整数属实现缺陷,夹具钉 DoU=5);**非整数 → 不可审计断言**(dou=None,不进 DoU 依赖分支);去盐扩展:剥离"带电 ∧ 独立组分 ∧ 碳数严格小于保留主体"的抗衡离子(覆盖 formate/acetate/sulfate/草酸/Tris/TEA/HCO₃⁻;中性共结晶分子不剥;并列最大碳数的带电组分不剥=保守保留并披露);**去盐仍先于电荷归一**(评审 F-1 背书) | §2.6;`_dou_of`/`_desalt_components` |
| 8 | **档位闭合性补写**(C 节) | ①共价金属新增 → **G2-a 硬剔**(归属档写死;配位/spectator 剥离后不触发;金属计数不变而共价态翻转 → 不可审计**降位+标注** metal_coordination_shift,不硬剔不 hold,C 节 6);②parse-fail 分支取舍:G2 与既有门**同一解析器**(MolFromSmiles+SanitizeMol 同源)→ 工作流路径下该分支**不可达**(既有门先行),保留仅作离线重放的防御分支(重放答卷可能含未过门记录),处置=降位不按零——与 C 节 3"删该分支"的取舍差异:重放侧需要防御,写明;③hold 分账:`hold_reason ∈ {substrate_undecidable(输入侧), all_rejected(模型侧)}` + `reject_count`(剔空过触发经②计数留痕,不静默变现空答);④**档位优先级显式:剔除 > 降位 > hold**(判定顺序写死,剔除先行短路);⑤降位全空(无剔除)时按原位次照常报出(G2 no-op,无害,C 节 5) | §2.3/§2.5 |
| 9 | **判定线独立性**(E-3) | 离线重放读数一律标注 **in-sample**(dev 引导编目反哺后的读数,非确证——一个符号能被目录编辑翻转 ±3 的排序键,量到的是目录不是化学);**确证路径写死 = 冻结后付费跑双采样符号检验**(fresh sample,方案 A,¥12 备选须另批);判定线并入 fork 草稿独有项:加 **spurious 净降 ≥3**(双采样 36/36 零噪声依据)为主终点之一 | §4.2/§5 |

**8 处背书不改**(评审原文点名,全部维持 v1):守恒连续值不入键;G3-a
不重复实现不放宽不收紧(= 既有 gate_smiles);G3-c 只提示不硬杀;同分异构
恒放行(限 key 1 内);剔空诚实弃权;解析失败不按零;去盐先于电荷归一;
note 非供体登记源 + 卤素新增先验排除。

**供体表细节按 B 节修**(规格性文档内容):按关键词分别定值(乙酰 +C2/
丙二酰 +C3/丁酰·琥珀酰 +C4,删裸词 coa);"不叠加"改**按元素取 max**
(同元素不求和、跨元素天然并存);ASCII 关键词词边界(`coa` 不命中
`coal/coast`、`sam` 不命中 `sample`、CO₂ Unicode 归一);**ThDP 行删除**
(+C 非可判定值,本题域几乎不出现;不授予 → 走增侧 → 惰性无害);
**缺口清单登记为规格性文档内容**(不入运行时表):碳共底物 glucose/
glycerol/succinate/pyruvate/acetate/methanol/酵母提取物,缀合供体
谷胱甘肽/甘氨酸/半胱氨酸·巯基尿酸/牛磺酸/葡萄糖醛酸(中文关键词)/
泛醌·核苷糖基,一碳单位 formate/formaldehyde/methylene-THF,含硫无机
thiosulfate/sulfite,氨酰化 aspartate/asparagine,金属辅因子(Mg/Mn/Zn/
Fe-S,归 C 档金属档)。B-6 降位通道(碎片公式与题面语义隐含供体精确
吻合 → 降位不硬剔)随增侧惰性声明一并挂起(不可达,登记待放活时启用)。

---

## 1. 臂定义与单变量

- **臂名**:`G2-ConsFilter-SelfRank v2`(novel/analogy 产出环节守恒过滤 +
  确定性自排序,合并设计,一个开关)。
- **单变量开关**:`prediction_policy.novel_conservation_filter = "off" | "on"`,
  **默认 "off" = C0 行为逐字节不变**(off 路径不新增任何分支副作用;开关
  取值随 policy 块进 run/batch identity,同 `rank_candidate_presentation` /
  `temperature` 的机制——值域 fail-closed,非法取值装配期拒绝,不静默回退)。
- **版本三元组(随开关进身份;v2 全量升版)**:

| 组件 | 版本 | 内容 |
|---|---|---|
| 守恒判据 | `v43-cons-2` | 本稿 §2.1–§2.5 全文(含 §0 修订) |
| 前置规范化 | `v43-norm-2` | 本稿 §2.6 |
| 自排序键 | `v43-selfrank-2` | 本稿 §2.7 |
| G3-b 编目 | `v43-g3b-catalog-2` | 本稿 §2.4.2 封闭 SMARTS 表(34 条) |
| 完整性声明关键词 | `v43-cons-kw-2` | 本稿 §2.0 |
| 供体登记表(规格性) | `v43-donor-registry-2` | 本稿 §2.2 |
| 封闭碎片清单 | `v43-cons-frag-1` | 本稿 §2.1(通道②) |

- **作用位点(钉死,不得二义)**:novel / analogy 两路由的**提案落账环节**
  (`_apply_novel` / `_apply_analogy` 内、提案卡构造前后)——对已进入提案的
  候选(每题最多 5 个 novel 产物;analogy 单产物)做确定性守恒判定、档位
  处置与重排序;结构化拒因/降位标记随提案卡落账。**纯后处理、无生成端
  反馈**:不改 prompt、不改 LLM 调用参数、不触发重试或再采样。recorded /
  rank 路由**不经过**本过滤器(既有门禁不动,门禁只紧不松)。
- **单变量纪律**:除开关(及其版本三元组)外,臂与对照逐字段相等——
  输入、代码、资产、模型、预算参数、scorer 版本(v3)、价格快照、并发
  策略(S1 总则沿用)。
- **与 G1 先决 3 的关系**:判据底稿与深位付费臂先决 3 共用(任务书 §2.3);
  门 1 迭代 2 已落"明显不过"支 → G1 付费臂维持不发车 → 本臂不依赖 G1,
  不受门 1 结论限制(teacher §六资源排序第 3 位)。
- **REAP 式 prompt 先验不并入本臂**(另立可选辅助臂,teacher §四.2:闭卷
  A/B 先行、不与主杠杆捆绑判定);本稿判据体系可作其规则来源,但 REAP 臂
  若发车须另行单变量预注册。

## 2. 判据终版(v2 冻结版正文;按评审 §六四步冻结顺序组织)

> 四步顺序:①计数口径(§2.1)→ ②供体登记表(§2.2)→ ③"不可审计/
> 剔空即 hold"两档语义(§2.3)→ ④G3 三层拆分(§2.4)。所有计数在 §2.6
> 前置规范化之后进行;实现为纯函数、零 LLM(`src/pathway_v43/validation/
> conservation.py`),工作流挂接与离线重放共用同一函数(同一判定,两种
> 驱动)。**档位优先级显式:剔除 > 降位 > hold**;②优先于 G1-b 缺口
> 放行(判定顺序在实现中写死)。

### 2.0 适用对象与声明语义(v43-cons-kw-2)

- 适用对象:novel/analogy 提案进入答案的每个候选产物(含 `.` 多组分串,
  按 G1-a/G2-a 全物种口径整体计数)。dev 题卷构造为单步(max_depth=1),
  候选一律按**单步产物**处理;整体矿化式答案("X → CO₂ + H₂O + NH₃"型)
  落 G1-b 缺口判定 → 可重构降位 / 不可重构降位(超出口径不是违规,mimo
  风险 #4)。
- **产物列表完整性声明(操作化定义,封闭关键词表 v43-cons-kw-2)**:
  - 英文**词边界正则**匹配(大小写不敏感):`complete` / `completely` /
    `only product` / `sole product` / `exhaustive(ly)` / `mineraliz(ed|
    ation|es|ing)` / `fully degraded` / `quantitatively` /
    `(completely|fully|totally) (converted|degraded|oxidized|mineralized|
    transformed)`;**否定排除**:命中处前 2 个 token 含
    not/no/never/n't/without/hardly/scarcely/nor/none 之一 → 不算声明
    (子串陷阱修复:`complete` 不再命中 `incomplete`,`not completely`
    不算声明);
  - 中文子串匹配:`唯一产物` / `产物完整` / `全部产物` / `彻底降解` /
    `彻底矿化` / `完全降解` / `完全矿化` / `完全转化` / `矿化`;
    **否定前缀字排除**(紧邻前字 ∈ 不/未/非/没/难 → 不算声明);
  - novel 候选默认**未声明完整**。
- 未声明完整时,减少侧守恒异常一律落"不可审计 → 降位"(信息不足不是
  违反守恒);**增加侧不依赖该声明**(原子凭空出现本身可证明——但在
  当前门禁次序下不可达,见 §2.2 惰性声明)。
- **② 的 CO₂/H₂O 组分接口(与判分口径显式对齐)**:判分口径 v3 的金标
  组分集**可能省略 CO₂/H₂**(常见做法:矿化终产物不计组分)。因此②的
  硬剔不依赖"缺失是否列出",而依赖**缺失可否重构**:候选声明完整、
  总碳减少、但缺口可重构为 CO₂/H₂O 族(母体有对应官能团)时,该候选
  仍可能与省略 CO₂ 的金标组分集全中 ⇒ **②不硬剔,降位+标注**
  (`declared_complete_loss_reconstructible`);仅当三者同时成立(声明
  完整 ∧ 总碳减少 ∧ 缺碳无可重构碎片)才硬剔。

### 2.1 ①计数口径:G1-a 全局碳守恒(硬剔除)/ G1-b 主产物碳骨架(降位)

**计数口径(先冻结)**:底物侧与产物侧的**全部含碳物种**计数,含
CO₂/HCO₃⁻、CN⁻、甲酸、甲醛、乙酰-CoA、糖基、酰基等一切含碳碎片与
显式写出的气态产物;多组分串按组分求和。杂原子侧(N/S/P/卤素/金属)同
口径。H 与 O 两侧计数但**不设硬门**(自由元素:默认隐式供体 {H₂O,O₂};
脱氢的 H、脱水的 O 可经未建模受体/水离开)。

- **G1-a(全局碳守恒;硬剔除仅两条)**:
  1. **违规①增碳无登记供体**:产物总 C > 底物总 C + 题面已登记碳供体
     提供的 C ⇒ **剔除**(**A-1 惰性声明**:当前门禁次序的答案路径上
     既有元素门先行,本条不可达——v1/v2 重放六批 excl=0×6 为证;单元
     级夹具仍钉住判据本身);
  2. **违规②原子消失**:声明完整(§2.0)∧ 硬元素(C/N/S/P/卤/金属)
     减少 ∧ **缺失不可重构碎片** ⇒ **剔除**;缺失可重构 ⇒ 降位
     (A-3 三条件,见 §2.0 接口);
  3. **其余碳减少:碎片可重构判据(统一三处,评审 D-2)**——
     `_gap_reconstructible(底物式 − 目标式)` 三通道:
     - **通道① motif 快路径**(C–C 氧化断键族):β-羟基羰基(逆醛醇)/
       β-二羰基(硫解)/ α-羟基酸 / **1,2-二羰基**(v2 补)——母体命中
       其一即放行(条件(ii)由 motif 本身给出);
     - **通道② 封闭小碎片清单**(v43-cons-frag-1):CO₂(羧基/酯/氨基
       甲酸酯/脲/二羰基族)、CO(羰基)、HCOOH(酯/酸)、CH₂O(杂原子
       甲基/缩醛)、CH₃OH(杂原子甲基/酯)、乙酸(酯/氨基甲酸酯/脲)、
       HCN(腈/氰醇)、CH₃SH(硫醚)、NH₃(胺/酰胺/脲)、H₂S(硫醚/
       磺酸)——硬元素逐元素精确相等 ∧ 母体命中该碎片要求的官能团
       (条件(ii));
     - **通道③ 有界杂原子单键切搜索**(大离去基团):枚举母体非环
       单键中至少一端为杂原子的键(N/O/S/P/卤/金属–C 键),H 帽补全
       后碎片并集精确覆盖硬元素缺口(条件(ii) = 母体真实存在可断键);
       界:同时切键 ≤4(三酰甘油=3)、可切键数 ≤128、每候选求值预算
       2048,**超限 → 不可审计 → 降位,绝不假放行**;C–C 键不进通用
       切搜索(烷烃任意切会假放行;C–C 断键仅经通道①/②)。
     - 匹配要求(i):**硬元素(C/N/S/P/卤/金属)逐元素精确一致**;
       O/H 自由元素不设界。
     - ΔC_main∈{−1,−2}(C1/C2 脱除族):可重构 ∧ |ΔDoU|<2 →
       `fragment_inferred` 放行(标注不降位);否则降位(四类形态:
       碎片不可重构 / 跨元素不一致 / ΔDoU 异常 / 与完整性声明叠加);
     - ΔC_main≤−3:可重构(三通道任一)→ 放行 +
       `cleavage_reconstructible` 标注;不可重构 → 降位。
     - **减少侧白名单族(糖苷/酯/酰胺/醚断裂)在碳侧也被认**——即
       本判据;G2-b 白名单(§2.4)处理纯杂原子减少(ΔC=0)形态,
       两者同一"碎片可重构"哲学,不再互斥。
     - **A-5 平票闭合**:主产物 = 候选组分中碳数最大的有机组分;并列
       最大 C 组分**全部**作为 main,逐一施加 G1-b(任一失败即降位;
       对称水解 C3+C3、二聚体对称水解不再有藏违规的空隙)。
- **G1-b(主产物碳骨架;启发式降位,排序信号)**:主产物相对题面母体的
  ΔC 允许集 = **{0} ∪ {碎片可重构的减少} ∪ {登记供体放行的增加(惰性)}**;
  越界(不可重构的减少)⇒ **降位**(不剔除;金标口径登记的裂解配比
  **永不**作为放行依据——评审明确否决:同时踩金标不入仓 + novel 退化
  为回忆两条红线)。

### 2.2 ②供体登记表(v43-donor-registry-2;**规格性文档**——A-1 惰性)

**A-1 惰性声明(选 (a),用户 2026-10-05 已裁决)**:既有元素白名单门
(`gate_element_changes`:一步只允许 O 增加 ≤2,其余任何元素增加一律拒)
在答案记录路径上先于 G2 生效 ⇒ 任何 +C/+N/+P 候选在到达 G2 前已被杀
(v1/v2 重放六批剔除侧零触发为程序证据)⇒ **G1-a①增侧拒、G2-a 增侧、
供体表"放行"三者在同一方向上都不可能触发**。因此:

- 供体登记表**降级为规格性文档**:数值与关键词供"未来放活增侧的臂"
  参考,在本臂内无操作行为;若未来放活增侧,须**另立臂走自己的判定线**
  (改门禁次序 = 放弃"纯后置、单变量、与现状逐字节一致",须按新干预
  重新预注册),不得在本臂内静默改。
- 默认隐式供体恒为 {H₂O, O₂}(仅引入 O/H)。

规格性内容(B 节修缮后):**按关键词分别定值**——NH₄⁺/NH₃/ammonium/
谷氨酸/丙氨酸/谷氨酰胺 +N;ATP +P;SAM +C1;PAPS/APS +S;UDP-糖族
+C6;**乙酰-CoA +C2;丙二酰 +C3;丁酰/琥珀酰-CoA +C4**(删裸词
`coa/辅酶A`:过宽触发器且语义含混);氨甲酰磷酸 +C1+N;CO₂/HCO₃⁻/
羧化 +C1;**ThDP 行删除**(裸 +C 非可判定值,本题域几乎不出现)。
**每元素授予 = 所有命中关键词在该元素上的最大值**(同元素不求和、
跨元素天然并存,如乙酰+丙二酰同时命中 → C 预算 = 3)。ASCII 关键词
词边界;CO₂ Unicode 归一。解析对象 = **题面条件文本**(工作流侧 =
conditions 块确定性序列化;离线重放侧 = 空);**候选 note 不是供体
登记源**(模型自称"用了谷氨酸"不构成题面登记)。**缺口清单**(登记
为规格性文档内容,见 §0)。

### 2.3 ③档位语义:"不可审计"降位 + "剔空即 hold"(含分账)

- **不可审计(降位,不剔除)**:碎片不可重构、供体疑似未登记(惰性)、
  共底物省略、结构解析失败、DoU 非整数、键切搜索超限。这些是**信息
  不足**不是**违反守恒**——把不可审计当违规是本过滤器最可能的诚实性
  出血点。降位项保留候选,但**排在所有未违规项之后**,降位次数与原因
  入报告;降位档内部按 §2.7 键序。
- **剔空即 hold(诚实弃权)+ 分账(C 节 4)**:若一题的全部候选(≤5)
  都被剔除 ⇒ 触发 **hold**:该题不报候选、不空转重试、不被迫回报最优
  违规者;留痕 `hold_reason ∈ {substrate_undecidable(输入侧信号:
  底物解析失败/结构歧义), all_rejected(模型侧信号:剔空)}` +
  `hold_detail`(substrate_unparseable / no_candidates / all_excluded)+
  **`reject_count`**——②的任何过触发都会经 reject_count 留痕,不静默
  表现成空答。hold 只由上述两类触发,**不作化学违规的软化通道**;
  **降位全空(无剔除)时按原位次照常报出**(G2 no-op,无害,C 节 5)。
- 降位项必须排在任何未违规项之后、降位计数入报告(否则降位等同无事
  发生)。

### 2.4 ④G3 三层拆分(价键硬过滤并现有结构门 / 官能团级降位 / 原子级仅提示)

- **G3-a 价键/形式不可行(硬剔除)**:五价碳、价态/形式电荷非法、芳香性
  与环完整性被破坏、"无 H 的碳被直接羟化且未去饱和"、无登记供体的
  烷基/酰基/糖基/磷酸基新增。**实现 = 并入既有结构门**(`validation.
  gates.gate_smiles` 的 RDKit sanitize 已含价态/原子检查,novel/analogy
  既有门禁)——本臂不重复实现、不放宽、不收紧该层(评审背书)。
  **parse-fail 分支取舍(C 节 3)**:G2 与既有门**同一解析器**
  (MolFromSmiles + SanitizeMol 同源)→ 工作流路径下 parse-fail 候选
  到不了 G2(既有门先行),守恒侧 parse-fail 分支不可达;保留仅作
  **离线重放的防御分支**(重放答卷可能含未过门记录),处置 = 降位
  (不按零),最终仍由既有 gate_smiles 硬拒——写明,不再含"工作流
  侧最终硬拒"的自相矛盾表述。
- **G3-b 官能团级可进攻性(标注 + 降位排序分量)**:封闭 SMARTS 编目
  `v43-g3b-catalog-2`,两组表:
  1. **底物可进攻键型表**(母体 SMARTS → 允许的首步反应类清单),
     **34 条(逐条枚举与计数一致,D-4 对账修复)**:羧酸、酯(无环
     限制→**内酯已覆盖**)、酰胺、**氨基甲酸酯**、**脲**、**磺酰胺**、
     磷酸酯、**膦酸酯/C–P**、硫酸酯/磺酸、砜、硫醚、亚砜、缩醛
     (**糖苷端基碳已覆盖**)、环氧化物、醚、碳卤、硝基、N-氧化物、
     腈、胺/亚胺/芳族 N、**季铵**、醇/酚、**过氧化物**、烯、醛/酮、
     β-羟基酮(逆醛醇)、1,3-二羰基(硫解)、**1,2-二羰基**、
     α-羟基酸、杂原子甲基、氰醇、sp3 C-H、芳环(环信息)、
     **五元杂芳环**(环信息);**芳香性模型声明 = RDKit 默认**
     (sanitize 感知;芳香噻吩 S 不被脂肪硫醚 SMARTS 覆盖,属五元杂芳
     环条目,已知边界);
  2. **候选变换类签名表**(Δ计数 + ΔDoU + 碎片重构 + 子结构差 →
     变换类):羟化(+1O/+2O)、醇氧化(ΔH−2 ΔDoU+1)、羰基还原、
     脱氢/加氢、脱羧(−1C 且羧基消失)、水合/水解(+1O+2H;底物有
     可水解链接族 → hydrolysis,否则 hydration——类名与编目允许类
     对齐)、脱水、脱 X/N/S/P、还原脱 O、转氨/氨化、磷酸化、磺化、
     **环氧化/S-氧化/N-氧化**(+O ΔH=0,经"底物基团 + 产物子结构差"
     鉴别,D-3 补)、同分异构/互变(Δ全 0)、裂解(碎片可重构)等;
     归属写明:脱烷基(N-dealkylation)归 c1_release 族;偶联/二聚归
     conjugation(增侧,当前门禁下惰性,类目留位);重排归 isomerization。
- 候选变换类**化学矛盾**(底物具备该可进攻基团而变换类与其矛盾)⇒
  **降位排序分量(key 2 靠后,不剔除)**;**unclassified 归中性**
  (落 key 3,不受惩罚——分类器覆盖失败不是化学不可能的证据)。
  编目来源分工(评审采纳):Rhea/MetaCyc 供守恒碎片清单、KEGG RCLASS/
  EC 第三位供键变化分类、UM-BBD 供题域先验、BNICE 供 novel 开放集;
  **不用任何库的已登记产物配比做放行白名单**。
- **G3-c 原子级区域选择性(仅提示层)**:不产出"该位点不可进攻"的硬
  判定;候选结构自身违反几何事实(如季碳直接羟化)按 G3-a 处理;其余
  只作披露列。**守恒合规但位点错 → 不硬杀**(G3-c 不硬杀,夹具钉住)。

**G2 杂原子增删(并入 §2.4 判定,口径如下)**:

- **G2-a 全局杂原子守恒(硬剔除)**:对 N/S/P/卤素/金属做与 G1-a 相同的
  两侧全物种计数。增杂原子无来源(无登记供体)⇒ **剔除**(**A-1 惰性**:
  答案路径不可达;**共价金属新增计违规 → 本档硬剔,C 节 1 归属写死**);
  去盐剥离 spectator 反离子后的配位/缔合形态不按"新增金属"剔除。
  **金属配位不可判形态(C 节 6)**:金属计数不变而共价态在两侧翻转 ⇒
  **不可审计降位 + 标注**(metal_coordination_shift),不硬剔(可能误杀)
  不 hold(污染弃权语义),由 G3-a/既有价态门兜底。
- **G2-b 主产物杂原子增删(分档)**:新增默认仅 {O, H}(源 O₂/H₂O);
  新增 N/S/P/卤素/金属按 G2-a 剔除(除非题面显式登记供体,§2.2 惰性)。
  **卤素新增:有意禁用并登记为"先验排除"**;卤素迁移不改变卤素计数,
  不触发。**减少侧白名单(一次性写全,全表)**:脱卤(还原/水解/氧化
  脱卤、脱卤素酶)、脱硫(含脱磺酸、硫酸酯水解、硫醚裂解)、脱氨/
  脱酰胺、脱磷酸(磷酸酶/酯酶)、脱糖基(糖苷酶)、脱酰基(酯酶/
  酰胺酶)、含氧基团还原脱 O(硝基→胺、N-氧化物→胺、亚砜→硫醚、
  过氧化物)——白名单处理**纯杂原子减少(ΔC=0)**形态;**伴随碳损失
  的杂原子键断裂(糖苷/酯/酰胺/醚)统一走 §2.1 碎片可重构判据**
  (同一规则三处互斥的修复)。白名单外的减少 ⇒ 不可审计 → **降位**,
  不落剔除(硝基→羟胺→胺是脱 O 不是脱 N;脱羧不改杂原子计数,归
  G1-a 口径管)。

### 2.5 处置四档(冻结语义;优先级:剔除 > 降位 > hold)

| 档 | 触发 | 动作与留痕 |
|---|---|---|
| **剔除(硬)** | G1-a 违规①(惰性)/ 违规②(三条件:声明完整∧硬元素减∧不可重构)、G2-a 增杂原子无来源(**含共价金属**,归属写死) | 候选移出答卷榜(不入名次);剔除数与规则号随提案卡结构化落账;判定顺序先行短路 |
| **降位** | 不可审计(碎片不可重构/供体疑似未登记/解析失败/DoU 非整数/键切超限/金属配位翻转)、G1-b 越界(不可重构减少、ΔDoU 异常)、G2-b 白名单外减少、G3-b 化学矛盾(排序分量)、②可重构缺失 | 保留候选但排在所有未违规项之后;降位次数与原因随提案卡落账;降位档内部按 §2.7 键序 |
| **hold(诚实弃权,分账)** | (a) `substrate_undecidable`:底物解析失败/结构歧义(输入侧);(b) `all_rejected`:剔空(模型侧,带 `reject_count`) | 该题不报候选、不重试、不被迫回报违规者;结构化留痕(hold_reason/hold_detail/reject_count)。**不作化学违规的软化通道**;降位全空时照常报出 |
| **标注(披露列)** | G3-b 可进攻键型清单、ΔDoU、元素计数差、去盐/互变规范化痕迹、碎片重构证据(fragment_evidence)、cleavage_reconstructible | 仅报告披露,不影响名次 |

### 2.6 前置规范化(v43-norm-2;计数前的硬步骤,不是可选项)

1. **电荷归一**:`rdMolStandardize.Uncharger`,与判分 cn_identity 同源
   口径(质子化态差异:羧酸 vs 羧酸根不再读成增删 H);
2. **立体忽略**:判分口径立体盲,同构处理;
3. **去盐前置,且先于电荷归一**(评审 F-1 背书,顺序不变):剥离
   **spectator 反离子**——v2 扩展(F-3/C-2):组分**带电** ∧(不含碳
   ∨ 存在**严格更大碳数**的保留组分)⇒ 剥离;覆盖带电单原子(金属/
   卤素 counterion)与**多原子反离子**(formate/acetate/sulfate/草酸/
   Tris/TEA/HCO₃⁻);中性共结晶分子(结晶水/DMSO/甲醇)不剥(属列出
   产物,计数如实);并列最大碳数的带电组分不剥(无法定谁是主体 →
   保守保留并披露)。盐型标记入披露(金标体检 v2 断言 1);
4. **互变规范化**:`TautomerEnumerator.Canonicalize` 后再 SMARTS 匹配
   (计数对互变天然不敏感——互变只移动 H;SMARTS 匹配侧防 keto/enol
   写法差,门 1 迭代 2 实测互变规范化为两轮最优零成本信号);
5. **DoU(F-2)**:**分子图/价键算法** DoU = 1 + Σ原子(vᵢ−2)/2
   (v = sanitize 后总价键数,AddHs 后全原子入账)——与
   (2C+2+N−H−X+q)/2 在无 P/S 变价时同值,对五价磷(P=S)/六价硫/
   季铵(q 项)给出整数正确值;**非整数 → 不可审计断言**(dou=None,
   不参与 DoU 依赖分支,候选按不可审计处置);
6. **解析失败按"未知"不按"零"**(金标体检 v2 断言 3 教训):底物/题面
   解析失败 → 整题 hold(substrate_undecidable);候选产物解析失败 →
   该候选降位(parse_fail 计数入披露),不参与守恒判定与自排序键,
   最终仍由既有 gate_smiles 硬拒(与既有门同一解析器,工作流路径下
   该分支不可达,重放防御,§2.4)。

### 2.7 确定性自排序键(v43-selfrank-2;冻结键序)

novel 自产候选(处置完成后,≤5 个)按以下键序重排:

1. **处置档**:未违规项在前,降位项垫底(剔除项不入榜);**守恒只作
   违规降位,不作正向先验**——键 1 是降位语义,不是"守恒越好排越前"
   的连续排序;
2. 未违规项内部:**G3-b 化学矛盾判据**(底物具备该可进攻基团而候选
   变换类与其化学矛盾者**靠后**;**unclassified/同分异构/parse_fail
   中性**——v2 语义,E-2/D-3:编目覆盖失败不是化学不可能的证据);
   同分异构放行仅 key 1 同档内生效(tier 为首键,豁免不可能越过处置
   档边界、不越过 key 2 矛盾判据);
3. 来源信号 = 提案原位次(模型 proposal 顺序,稳定序,防实现者自由发挥);
4. 同键稳定:提案原位次(整个排序为**确定性稳定重排**)。

**明令禁止(迭代 2 硬证据,见 §3)**:守恒连续值(cons 罚分)**不参与
任何排序键**(只进披露列);守恒档**不作全局前置排序**(档位是降位
分量不是主序)。

**纯重排硬验收(E1 order 契约工程复用)**:自排序分量执行后,候选集合
与 @5 逐题不变(剔除与 hold 除外——集合变化只允许来自剔除与 hold);
pytest 钉住。

## 3. 降位制约束(迭代 2 两条硬证据 → 设计原则,冻结,v2 不变)

1. **硬过滤误杀率 7/22(32%)**:任务书口径守恒硬过滤杀死 22 题金标卡中
   的 7 题。按硬剔除语义部署会永久损失这 7 题 → **本臂默认降位不硬剔**;
   硬剔除仅限 §2.1/§2.4"可证明违规"两条 + G3-a 价键不可行(= 既有
   结构门)。
2. **守恒优先排序是反向先验**:22 题金标卡 cons 分布 = cons=0 同分级
   5 题、小步 6 题、**cons>1(原子数变动)11 题**;预声明主口径 s3x
   (cons 升序)回撤到 7/10/10(比基线 S3 还差)→ **守恒特征只作降位
   分量与簇识别,不作全局前置排序、不进任何排序键的连续值**(§2.7
   明令)。

配套护栏:判据健全性预检(发车前置)须实测"金标候选落剔除档 = 0 题",
否则判据回修走新冻结链(见 §6.4)。

## 4. 主终点与判定线(先于任何付费跑冻结;v2 并入 fork 草稿独有项)

### 4.1 口径与基线

- 分母 dev v1.1 = **51**(quarantine 后);判分口径 v3;对照基线
  C0-a v3 = **14/51 = 27.5% @1**(C0-b 同参封存,双采样现成)。
- @5 与 spurious 的 51 分母基线:从 dual_track_rescore 封存件确定性导出
  (剔除 5 道 quarantine qid),随发车授权一并封存;本稿锚 @1 = 14/51。
- spurious 定义沿用 S1:答卷含 ≥1 预测产物且全部产物不中任何金标组分的
  题数(空答单列,不算 spurious)。

### 4.2 判定线(dev_candidate,全部满足;v2:spurious 升主终点)

1. **cn@1 净赢 ≥3 题**(14/51 → ≥17/51 = 33.3%,+5.9pp;S1 最小有用
   增益同刻度;自排序承载面 = 金标@2–5 全走 novel 路由的 11 题量级);
2. **spurious 净降 ≥3 题**(判定口径 = 总 spurious 题数下降;双轨披露
   含/不含 hold 转化两列;依据:spurious 指标在 C0-a/C0-b 双采样间读数
   相同(v2 口径均 24)→ 采样方差近零,净降 3 远超其噪声带——fork 草稿
   独有项并入);
3. **@5 不降**(净 0 为底线;自排序纯重排承诺 + 剔除只作用于违规候选);
4. **空答不升**(净变化 ≤0;hold 转化逐题披露——若空答上升全部来自
   剔空 hold,逐题归因登记后仍按"空答不升"线判,不得以弃权换数字)。

**机制正向登记带(mechanism_positive_not_adopted;非采用)**:spurious
净降 ≥3 且 cn@1 净赢 +1~+2 且护栏全守 → 机制正向但不足采用线(teacher
§七路径预算对 G2 的 +1–2 预期带);是否收编由 teacher/用户裁定,不改
判定线,采纳走下一轮预注册。**挂起拍板点(fork 草稿 §7.2 沿用)**:
①对照方案 A/B 选择(建议默认:B 为判定主案、A 为可选补强);②hold
转化上限(建议默认:≤3 且双轨披露);③机制正向中间档去留(建议默认:
保留)——三项随发车授权一并确认,**未冻结**。

**rejected**:cn@1 净赢 ≤0 或任一护栏击穿(spurious 净升 / 空答净升 /
@5 净降 >2)。
**inconclusive**:账目/终态/方差证据不完整(缺 usage、非法终态 >10%、
双采样缺失)。
三态不写 adopted(发布默认变更另走发布审查,S1 惯例)。

### 4.3 统计、独立性与止损(S1 框架同款;v2 强化 E-3)

- **双采样**:判定读数基于两次独立采样。**确证路径写死 = 冻结后付费跑
  双采样符号检验(fresh sample)**;方案 B(封存答卷离线重放)读数一律
  标注 **in-sample,非确证**——dev 引导的编目反哺会使同批 dev 上的读数
  循环(v1 实测:初版 −2~−3 → 编目补全后 +3,符号被目录编辑翻转 ±3;
  E-3:一个符号能被目录编辑翻转的排序键,量到的是目录不是化学)。
- **符号检验(佐证列,不作门槛)**:对配对逐题差值的 @1 翻转与
  spurious 翻转做两侧精确二项检验,两采样分别做并合并报。功效事实
  如实登记:n=51 下 @1 净赢 3 符号检验不可能显著——主判定按预注册点
  估计线执行,不以不显著推翻已达线结果、不以显著加持未达线结果(防
  看分后用 p 值翻案)。
- **累计止损门 +8pp 沿用**(teacher §四 S1)。累计起算口径:口径 v3 +
  51 分母新链起算(S1 四臂 v2 链判定已由 teacher §七路径预算承接、
  不混算)。
- 里程碑口径:30% 里程碑 = 16/51(dev 刻度);G2 净赢 3 → 17/51 过线;
  正式判定场所在题源落地后的新盲测集,dev 结果只作开发期判定(I1)。

### 4.4 对照设计与费用帽(v2 按 fork 草稿表述更新)

- **方案 B(本任务已执行的重放复验形态)= 判定主案建议(挂起)**:
  复用封存 C0-a/C0-b 答卷 + 离线确定性重放(生成成本 ¥0;答案级完美
  配对,双采样现成)。**其读数 in-sample(非确证)**,作发车建议与
  工程验证;若用户显式授权方案 B 为判定形态,判定线按冻结文本执行。
- **方案 A(同代码关过滤重跑 C0,in-run 双臂新跑 4 批)= 可选补强,
  ¥12 备选须另批**:主臂(开关 on)与对照(off)各 ≥2 次独立采样,
  身份级配对;fresh sample → **E-3 的确证读数来源**。付费跑不在本
  任务内,等本预注册冻结 + 用户批预算。
- 总帽建议 ≤¥6(B 判定 ¥0 + 可选 in-run 烟测 ≤¥5 + 计账余量);若只
  跑方案 B,实际支出 ¥0。

## 5. 离线重放声明(本任务工程的定位,如实;v2 = in-sample 标注)

- 本任务内的**离线重放**(对封存六批答卷的 novel/analogy 路由题,离线
  跑 G2 过滤 + 自排序,重算口径 v3 读数)属**"已见 dev 数据的工程设计
  验证"**,且 v2 起读数一律标注 **in-sample**(dev 引导编目反哺后的
  读数,**非确证**,E-3):用途限于 (a) 判据健全性预检(金标候选落剔除
  档必须 = 0);(b) 发车建议与预期面校准;(c) 夹具外的真实分布压力
  测试。
- **重放读数不作臂判定**;判定线(§4.2)在付费跑(或授权重放判定)
  之前冻结,判定读数一律出自冻结后流程。重放预测须注明"in-sample
  离线预测,确证须付费跑 fresh-sample 双采样"。
- 重放金标比对只在本地离线进程(dev_gold gitignored 只读);仓内产物
  零 SMILES(qid + 旗标 + 计数可)。

### 5.1 v1 工程验证闭环登记(2026-09-30,判据 v43-cons-1;保留)

- **初版规则重放读数(负)**:G1-b 降位 + G3-b 键 2 双双为反向先验
  (C0b @1 15→12;分解测量:仅 G1-b 键 = −2,仅 G3-b 键 = −3,两者皆
  负、剔除侧零触发);初版编目缺环氧化物/醚/胺-亚胺三类,经失败案例
  **分析补全后**读数 = 判定对 C0a **+3** / C0b **0**(@5/spurious/
  空答全平、hold=0、金标落剔除档=0)。**补全属"已见 dev 数据的工程
  补全",+3 不可作独立确证**;键 2(编目匹配)与 G1-b 降位(碎片
  未列族)在中间位次仍有 −1~−2 的系统性反压(六批一致)。
- v1 结论(发车建议):本版规则**不建议直接发付费臂**;若追,须按
  失败分支 1 走新冻结链。→ **已走**:mimo 终版评审(9 必改)→ 本 v2。

### 5.2 v2 工程验证闭环登记(2026-10-05,判据 v43-cons-2;in-sample)

六批复封答卷(v1 副本 `*_v1.*` 保留对照;`--check` 复算 PASS;锚点
fail-closed 全过):

| 批 | @1 | @3 | @5 | spurious | 空答 | 降位数 | 剔除 | hold | 金标落剔除档 |
|---|---|---|---|---|---|---|---|---|---|
| C0a | 14→**16**(+2) | 22→21 | 25→25 | 24→24 | 1→1 | 6(v1:16) | 0 | 0 | 0 |
| C0b | 15→**16**(+1) | 22→21 | 26→26 | 24→24 | 0→0 | 6(v1:18) | 0 | 0 | 0 |
| E1 | 15→**17**(+2) | 22→21 | 25→25 | 24→24 | 1→1 | 5(v1:19) | 0 | 0 | 0 |
| E2a | 14→**15**(+1) | 24→23 | 26→26 | 23→23 | 1→1 | 6(v1:24) | 0 | 0 | 0 |
| E2b | 12→**13**(+1) | 21→20 | 24→24 | 24→24 | 1→1 | 5(v1:19) | 0 | 0 | 0 |
| E3 | 15→15 | 21→20 | 22→22 | 28→28 | 0→0 | 9(v1:17) | 0 | 0 | 0 |

- **被救回(对 v1 的核心修复,判定对)**:092-S03(ΔC_main=−12,
  v1 rank 1→3,v2 rank 1→1)与 101-S05(ΔC=−5,v1 1→4,v2 1→1)——
  v1 把大缺口金标按"G1-b 越界"降位,v2 碎片可重构判据(通道③)放行;
  E1/E2a/E2b/E3 四批同型救回(092/101 全部恢复 orig rank)。这正是评审
  D-2 点名的教科书误杀(大缺口水解/裂解族金标)。
- **@3 反压缓解**:v1 六批 −1~−2(C0b −2、E 批 −2),v2 六批全部 −1。
- **净赢形态变化(如实)**:判定对 v2 = C0a +2 / C0b +1(合计 +3 与
  v1 持平,但双样本都为正、**零金标损失**——v1 的 C0a+3 里有 125-S08
  一题系"降位一个 v2 判定其缺口可重构的候选"侥幸获得,v2 将其救回,
  金标回到 rank 2)。机制上:v2 的放行是对称的(救金标也救 spurious),
  v1 的 +3 有部分是运气不是化学。
- **降位数大降**(16/18→6/6):碎片重构 + unclassified 中性把大多数
  v1 降位转为放行;剩余降位 = 真不可重构缺口与化学矛盾。
- 剔除侧零触发(excl=0×6)与 hold=0:**A-1 惰性声明的程序证据**(既有
  元素门在答案路径上先行);spurious/空答/@5 全平。
- **对照判定线**:cn@1 净赢 +2/+1(均值 +1.5)< 3;spurious 净降 0
  < 3 → in-sample 读数未达判定线,落"机制正向不采用"带(护栏全守)。
  发车建议见设计报告 §6-v2。

## 6. 失败分支预声明(对齐 teacher §七;届时不得临时找理由)

1. **线未达但护栏全守**(cn@1 净赢 <3 或 spurious 净降 <3)→ rejected
   (或机制正向带内登记);不得自行加臂(不叠 REAP 硬凑、不调判据权重
   重跑——权重/规则/键序改动 = 判据新版本,须走新冻结链 + 新预注册)。
2. **护栏击穿**(@5 净降 >2、空答/spurious 净升)→ 判据或实现缺陷
   登记 → 新冻结链(mimo 评审 → 用户人审 → 冻结 v3)→ 新批次重跑;
   不得在原批次上静默改。
3. **净赢为负**(自排序反向:金标落降位档被压到未违规错答之后——
   迭代 2 s3x 同型风险,金标 11 题 cons>1)→ 判据回撤登记 → 新冻结链,
   不在本臂判定内消化。
4. **剔除误杀金标**:发车前被健全性预检拦截(金标候选落剔除档须 = 0);
   跑后发现 → 判定作废(inconclusive),新冻结链回修后重跑。
5. **G2 rejected 且深位付费臂维持不发车** → 闭卷 30% 里程碑重估,
   teacher 侧重新审议目标,学生不得在 dev 上加臂硬凑。

## 7. 冻结链状态(v2)

- 判据证据链:v1(评审 #2 改版蓝图 + 门 1 迭代 2 程序互证)→ 实施 →
  mimo 终版评审(9 必改 + 8 背书不改)→ **本 v2**;待 mimo delta 确认
  (`docs/mimo_g2_v2_confirmation_request.md`)→ 用户确认冻结 → FROZEN。
- 四步冻结顺序状态:①计数口径 §2.1(碎片可重构判据)冻结;②供体
  登记表 §2.2(规格性文档 + 惰性声明)冻结;③两档语义 §2.3(hold
  分账 + 优先级)冻结;④G3 三层 §2.4(34 条编目 + 化学矛盾键)冻结。
- 发车前置三件套:(1) 判据实现 + 合成夹具全绿(**50 用例,v1 29 → 
  v2 50,只增不减**;全仓 627 绿);(2) C0 等价性验收(off 路径逐字节
  不变 + pytest 钉住);(3) 判据健全性预检(离线重放:金标候选落剔除
  档 = 0、全候选档位分布、供体解析组件双向边界用例)——(3) 已随
  §5.2 执行(excl=0×6)。
- 跑分后 mimo 结果复核(AGENTS.md 触发点 3):G2 判定即时出后另出
  评审请求,后置不改已冻结判定,采纳走下一轮预注册。

## 8. 红线附录(v2 不变)

- **金标隔离**:金标 SMILES 永不进 git 跟踪文件;判据、编目、过滤器
  代码零金标零题面;裂解按键型/碎片可重构判,不按配比;健全性预检的
  金标比对仅本地离线进程,仓内只进聚合计数;含金标中间件入 gitignored。
- **门禁只紧不松**:既有门禁(gate_smiles/gate_element_changes 等)
  逐条不动;本臂只新增处置与排序层。降位制满足"不放宽"的论证:降位
  项恒排在未违规项之后(收紧排序);默认隐式供体仅 {H₂O,O₂};不可
  审计 ≠ 放行(仍受压、计数入报告);硬剔除收缩到"可证明违规"是防
  误杀(误杀率 7/22 硬数据),不是放松门禁。
- **预注册先于跑分(I2)**:本稿冻结先于任何 G2 判定读数;看分后改
  判据/键序/判定线一律无效,触发新冻结链重跑。
- **298 不碰(I1)**:本臂仅 dev;所有数字带题域标签(dev = B1 环境
  路径中间步骤),双向不外推。
- **判分/评测零 LLM**:过滤器、自排序、判定、统计全确定性。
- **封存与批次纪律**:封存 run/远端只读;新实验一律新批次根;不
  git commit;工作树未提交改动全部保留;C0 off 行为逐字节不变。

---

## 附录 A:机器可读 diff(v2 冻结版摘要;JSON)

```json
{
  "prereg_id": "PREREG-G2-v2-DRAFT",
  "arm": "G2-ConsFilter-SelfRank",
  "revision": "v1->v2 per mimo final review (docs/mimo_g2_rules_final_review_response.md) 9 mandatory items",
  "single_variable": {
    "switch": "novel_conservation_filter",
    "values": ["off", "on"],
    "default": "off",
    "off_semantics": "byte_identical_to_C0",
    "identity_fields": ["prediction_policy block in run/batch identity"],
    "versions": {
      "cons_filter": "v43-cons-2",
      "normalization": "v43-norm-2",
      "self_rank": "v43-selfrank-2",
      "g3b_catalog": "v43-g3b-catalog-2",
      "completeness_keywords": "v43-cons-kw-2",
      "donor_registry": "v43-donor-registry-2",
      "fragment_catalog": "v43-cons-frag-1"
    }
  },
  "scope": {
    "routes": ["novel", "analogy"],
    "position": "in_apply_novel_and_apply_analogy_before_proposed_card_commit",
    "feedback": "none_no_retry_no_reprompt",
    "routes_excluded": ["recorded", "rank"]
  },
  "criteria": {
    "counting": "all_species_both_sides_sum_multicomponent",
    "tier_priority": "exclude > downgrade > hold (2nd_rule_before_G1b_gap_release)",
    "hard_exclusion": [
      "G1-a-1 surplus_C_no_registered_donor [INERT: upstream element gate precedes on answer path]",
      "G1-a-2 declared_complete_AND_hard_element_loss_AND_gap_NOT_reconstructible",
      "G2-a surplus_NSPXMetal_no_registered_donor (covalent_metal_new -> this tier, fixed)"
    ],
    "G3_a": "merged_into_existing_gate_smiles_no_relax_no_tighten; same_parser -> workflow_path_unreachable, replay_defensive_downgrade",
    "fragment_reconstructibility": {
      "unified_in_three_places": ["G1b_allowed_set", "dC_-1_-2_release (R1 condition)",
                                  "rule2_third_condition"],
      "channels": ["motif_fastpath (beta_hydroxy_carbonyl,beta_dicarbonyl,alpha_hydroxy_acid,alpha_dicarbonyl)",
                   "closed_fragment_catalog v43-cons-frag-1 (co2,co,hcooh,ch2o,ch3oh,acetic_acid,hcn,ch3sh,nh3,h2s + group existence)",
                   "bounded_heteroatom_single_bond_cut_search (<=4 cuts, <=128 bonds, 2048 eval budget; C-C excluded)"],
      "match": "hard_elements_exact_per_element; O_H_free_no_bound",
      "downgrade_forms_kept": ["fragment_not_reconstructible", "cross_element_inconsistent",
                               "ddou_anomaly_|ddou|>=2 (C1/C2 family only)", "declared_complete_stacking (rule2 first)"],
      "tied_main_components": "all_max_C_components_judged (A-5)"
    },
    "completeness_keywords_v2": {
      "word_boundary_regex": true,
      "negation_exclusion": "2-token lookback (not/no/never/n't/without/...) + CN prefix chars",
      "mineralization_family": ["mineralized", "mineralization", "fully degraded",
                                "completely converted", "quantitatively",
                                "彻底降解", "矿化", "完全转化"],
      "co2_h2o_interface": "reconstructible_co2_loss_never_hard_excluded (scoring caliber may omit CO2)"
    },
    "key2_semantics_v2": {
      "contradiction_only": "substrate_has_group_AND_transform_classified_AND_not_in_allowed_AND_allowed_nonempty",
      "unclassified_neutral": ["unclassified", "isomerization", "parse_fail"],
      "isomer_pass_within_key1_tier_only": true,
      "new_transform_classes": ["epoxidation", "s_oxidation", "n_oxidation",
                                "hydrolysis_vs_hydration_disambiguated"]
    },
    "increase_side": {
      "declaration": "INERT_NO_OP (option a, coordinator_suggestion, PENDING_USER_CONFIRM)",
      "evidence": "upstream element gate precedes on answer path; replay excl=0 across 6 batches",
      "donor_registry": "speculative_document_only; future arm must re-register own decision line"
    },
    "donor_registry_v2": {
      "per_keyword_values": {"acetyl-CoA": "+C2", "malonyl": "+C3",
                             "butyryl/succinyl-CoA": "+C4", "SAM": "+C1",
                             "UDP-sugars": "+C6", "CO2/HCO3-": "+C1",
                             "carbamoyl-phosphate": "+C1+N"},
      "per_element_max_not_sum": true,
      "word_boundary_ascii": true,
      "thdp_row": "deleted",
      "bare_coa_keyword": "deleted",
      "gap_list": "speculative document content (glucose/glycerol/succinate/glutathione/glycine/taurine/formate/methylene-THF/thiosulfate/aspartate/...)"
    },
    "catalog_v2": {
      "count_declared_equals_enumerated": 34,
      "added": ["carbamate", "urea", "sulfonamide", "phosphonate_cp",
                "quaternary_ammonium", "peroxide", "alpha_dicarbonyl",
                "heteroaromatic_5"],
      "aromaticity_model": "RDKit default; aromatic thiophene-S via heteroaromatic_5 (known boundary)",
      "coverage_declarations": ["ester SMARTS ring-free -> lactones covered",
                                "acetal SMARTS -> glycosidic anomeric C covered"]
    },
    "normalization_v2": {
      "dou": "graph/valence algorithm DoU=1+sum((v-2)/2); equivalent to (2C+2+N-H-X+q)/2; P=S/v6-S/quaternary-N integer; non-integer -> unauditable",
      "desalt": "charged AND separate component AND (no C OR strictly-fewer-C-than-kept-max) -> strip; multiatomic counterions (formate/acetate/sulfate/Tris/TEA/HCO3-); neutral cocrystals kept; tied-C charged kept+disclosed",
      "desalt_before_uncharge": "unchanged (endorsed)"
    },
    "hold_v2": {
      "reasons": ["substrate_undecidable", "all_rejected"],
      "reject_count": true,
      "downgrade_all_empty": "report original order (G2 no-op, harmless)"
    },
    "metal": {
      "covalent_new": "G2-a hard exclude (fixed tier)",
      "spectator_coordination": "desalt-stripped, no trigger",
      "undecidable_shift": "unauditable downgrade + annotation (not hold)"
    },
    "halogen_new": "intentional_prior_exclusion",
    "reduction_whitelist": [
      "dehalogenation", "desulfuration+desulfonation+sulfate-ester-hydrolysis",
      "deamination/deamidation", "dephosphorylation", "deglycosylation",
      "deacylation", "reductive-deoxygenation(nitro/N-oxide/sulfoxide/peroxide)",
      "carbon_loss_heteroatom_scission -> unified fragment_reconstructibility"
    ]
  },
  "self_rank_keys": ["disposal_tier_pass_before_downgrade",
                     "g3b_chemical_contradiction_only_unclassified_neutral",
                     "source_signal_original_proposal_position_stable"],
  "self_rank_forbidden": ["cons_continuous_value_as_sort_key",
                          "conservation_tier_as_global_pre_sort"],
  "pure_reorder_acceptance": "candidate_set_and_at5_identical_per_question_except_exclusion_and_hold",
  "endpoint": {
    "denominator": "dev_v1.1_n51_quarantine",
    "scoring": "caliber_v3",
    "baseline_C0a_v3_at1": "14/51",
    "dev_candidate_lines": {
      "cn_at1_net_win_min": 3,
      "spurious_net_reduction_min": 3,
      "at5_floor": "net_0",
      "empty_answer": "no_rise_hold_conversions_disclosed_per_question"
    },
    "secondary_band": "spurious_-3_and_cn_at1_+1..+2_all_guardrails_held_mechanism_positive_not_adopted",
    "stop_loss_cumulative_pp": 8,
    "stats": "confirmatory=PAID fresh-sample double-sampling sign test (option A); offline replay readings labeled in_sample_non_confirmatory",
    "cost_cap_cny": 6,
    "control_design": {
      "B_sealed_offline_replay": "executed (in-sample engineering validation)",
      "A_in_run_paired_rerun": "optional confirmatory, cap 12, requires authorization"
    }
  },
  "offline_replay_position": "in_sample_engineering_validation_not_arm_judgment",
  "offline_replay_v2": {
    "C0a": {"at1": "14->16 (+2)", "at3": "22->21", "downgraded": 6},
    "C0b": {"at1": "15->16 (+1)", "at3": "22->21", "downgraded": 6},
    "rescued_from_v1": ["092-S03 (dC_main=-12, v1 rank1->3, v2 rank1->1)",
                        "101-S05 (dC_main=-5, v1 rank1->4, v2 rank1->1)"],
    "at3_counterpressure": "v1 -1..-2 -> v2 -1 uniformly",
    "gold_in_exclusion_tier": 0,
    "hold": 0, "excluded": 0,
    "v1_win_partially_reverted": "125-S08: v1 win relied on demoting a v2-reconstructible candidate (+3 luck component); v2 rescues it symmetrically"
  },
  "freeze_chain": {
    "criteria_sources": ["mimo_conservation_rules_review_response",
                         "mimo_g2_rules_final_review_response (9 mandatory items)",
                         "MIMO_REVIEWS_ADOPTION_REGISTER_S2_S4",
                         "gate1_iteration2_sealed"],
    "status": "DRAFT_v2_awaiting_mimo_delta_confirmation_and_user_freeze",
    "launch_gates": ["mimo_delta_confirmation", "user_authorization",
                     "fixtures_all_green (50 cases, suite 627)",
                     "C0_off_byte_identical_regression",
                     "soundness_precheck_gold_in_exclusion_tier_equals_zero (passed: 0x6)"]
  },
  "red_lines": ["gold_isolation", "gates_tighten_only", "prereg_before_scoring",
                "no_298", "zero_llm_judging", "sealed_readonly",
                "new_batch_root", "no_git_commit", "C0_off_byte_identical"]
}
```
