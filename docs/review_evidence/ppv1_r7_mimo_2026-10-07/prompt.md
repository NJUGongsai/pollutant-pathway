你是独立外部化学评审员，对 pollutant_pathway_v1 化学判据草案第七轮版本（v7，S0–S2 回修后，尚未冻结）做化学评审。评审请求全文附在最后。

回复要求（与请求原文 §7 相同，重申）：对判据一～判据五**逐条**给出：1) 结论（同意/不同意/有条件同意+条件）；2) 可直接落进规则文字的修改建议；3) "程序上诚实但化学上误导"风险点。不接受总体评价式回复。

执行边界（重要）：
- 本轮你只能用读取类工具浏览仓库源码/文档来核对请求中的表述（仓库根 /Volumes/CC/Enzyme_Agent/dependingv43；判据实现于 src/pathway_v43/pollutant/，回归测试 tests/test_ppv1_*.py）；你**没有 shell 执行权限**，无法运行测试或探针——若某项判断必须依赖执行证据，请如实标注"待执行验证"并说明需要跑什么，**不要编造任何执行结果或数字**。
- 禁止访问 gitignored 金标/题面目录（如 reports/phase_s0_hit60/manual_review/）及任何金标、题面、封存逐题 run 内容；本轮评审仅限规则级判据文本。
- 不修改任何文件，直接输出评审回应文本。
- 请求原文自包含（规则级表述+合成夹具，无金标）；你的结论基于请求文本与你实际读到的代码。

--- 评审请求全文如下 ---
# mimo 化学评审请求:pollutant_pathway_v1 化学判据(S0–S2 回修版 v7)

- 日期:2026-10-07(R7 回修版;替换同日 v6 请求)
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或发布前)
- 评审对象:S0–S2 第七轮回修后的化学判据草案 v7(实现于
  `src/pathway_v43/pollutant/`,ppv1-*-7 版本族);**尚未冻结**
- 与 v6 的差异来源:第六轮 mimo 回应
  (`docs/mimo_ppv1_chem_review_response_r6.md`)+ Codex R6 复审
  (`POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R6_2026-10-07.md` R6-01～05
  五组 P1 与 §4 两项 P2 文档同步)。Codex R6 §5 采信边界:采纳
  third consumer(供体诊断原始入口)与含空格合法内容过拒;不采纳
  "输入登记类及默认拒绝已完整"(登记头后的并列未知项仍绕过)、
  不采纳"composition-only 注册说明或 strict 轴可兜底复杂共底物
  全覆盖"。R6 实测缺陷五组:数值配平的复杂共底物结构贡献未核实
  仍 full/R6(R6-01);原始 CX 并列未知类与供体诊断原始字符串入口
  两处不闭合(R6-02);公开派生 API 可洗掉旧必要未知(R6-03);
  首提复用既存 state/appearance 行不验、校验拖到重放(R6-04);
  事件出现清单无独立完整性依据、删项漏检(R6-05;存储两项 mimo
  不审,仅程序事实披露)。
- 自包含性:规则级表述与合成规则级夹具,无任何金标/题面/封存
  逐题数据;由用户转交,回复原文落盘 `docs/`

## 0. 背景(一段话)

v6 判据经第六轮独立复审发现五组同源/完整性缺口:真实 AtomTool
C→CCCO(依次新增 C/C/O,不载入任何共底物初始图)的证据用于
C+C2H4O 异构体(乙醛/环氧乙烷/乙烯醇)→CCCO,数值全配平即授
"全部核实";工厂/strict 接受 `|atomProp:0.note.hello,r|` 等登记头后
并列未知项(RDKit 解析时静默丢 r 后与裸串同身份);供体诊断直接
解析 current/mapped 原始串,加 `|r|` 后仍 True/True、公共 audit→
R6;公开派生 API 不验父对象,篡改快照删必要评估行后重算子 ID 即
洗掉旧必要未知;首提复用既存损坏行零校验;同 SID 多出现的事件
清单删项漏检。五组已全部回修并有行为级红绿回归(基线 6d90201
新增回归 57 例红 33/绿 24,其中 26 红为复审反例行为翻转、7 红仅
因 v7 新披露字段/新表缺失;ppv1 全量 508 passed/0 skip;G01 全量
not slow 1119 passed/16 deselected)。本轮请评审**回修后的判据
文本 v7**。目标不变:可能降解路径与条件相容路径的诚实表示;
unknown 不升格;verified 不靠模型或调用方自报字符串;**账平、
物种同 CN 或一份正确局部诊断不能代替整条声明的覆盖与追溯;
数值配平不等于未覆盖参与物初始图的结构贡献已核实**。

## 1. 判据一:分子身份(v7 文本)

1–4 同 v6(state_id 生成条件/化学 CX 事实子集/混合并列 ABS 归一/
公开表示往返闭合/fidelity 分轴)。v7 改第 2 条的词法边界:

2. **输入侧注册感知校验——按真实 CX 类边界逐项词法(R6-02A,
   替换 v6 的"空格拆块 + 只查首头")**:
   - v6 缺陷:登记头(atomProp/SgD/Sg)之后的**并列未知项**
     (`|atomProp:0.note.hello,r|`、`|SgD:…::::,r|`、
     `|Sg:n:…:::,r|`、`|atomProp:…,Ln:1|`、`|atomProp:…,w:1.0|`)
     整块放行,解析器静默丢弃后与裸输入同 state_id/as_written;
   - v7 词法:按 RDKit CXSMILES 解析器(实测 Release_2026_03_6
     的主分派循环)的**真实类边界**逐项检查——扩展段是"项序列",
     项间由 ','/空格分隔(逐字符跳过);各登记类解析器自耗字段,
     **字段内逗号/空格是内容**(atomProp 值到 ':'/'|'/',' 止,
     SgD/Sg 冒号字段到 ':' 止——DAT 值内逗号受保护,`$…$` 标签
     到 '$' 止);未登记首头(含并列位置)⇒
     ChemicalStateError(kind=unregistered_cx_class,带违规项原文
     与登记头上下文);
   - **登记内容含空格不再过拒**(R6 §4-1 P2 同修):RDKit 写出器
     生成的 `atomProp:0.note.hello world`、`SgD:…:hello world::
     ::`、`$foo bar;$` 可合法往返,v6 按空格拆块误报未登记;
   - **DAT/SgD 剥离的适配器前提(明示)**:本仓把 DATA SGroup
     (SgD)视为纯出现/注记元数据,生成身份前**分子级剥离**——
     **化学事实不得只编码进将被视为注记的 DAT**(需要进身份的
     化学事实走结构串本身或登记保留类 Sg/SRU;DATA 中的文本
     不是化学事实);SRU/聚合物等非 DAT SGroup 保留;
   - 语法整体不可解析且无违规 CX 项的输入仍归 unparseable_smiles
     (机读码分列,同为拒绝);输出侧守卫(v4 起)不动;
   - **不要求解释新 CX 类、不按整类名称免审**;新 CX 类默认拒绝
     (fail-closed),RDKit 行为变化须重登记。

**请评审**:(a) 按真实类边界逐项词法(而非按空格拆块)是否正确
闭合"并列未知项";(b) **全部原始 CX 入口清单**——
build_chemical_state、strict_identity_of 与判据五供体诊断的
current/mapped/plain/target 四个原始字段共用同一守卫(见判据五),
是否还有本仓未覆盖的公共入口;(c) DAT 剥离前提("化学事实不能
只编码进将被视为注记的 DAT")的表述;(d) 含空格登记内容的
放行与 DAT 值内逗号保护的边界。

## 2. 判据二:参与物计量与元素/电荷核算(v7 文本)

1–8 同 v6(全氢账/系数契约/完整性 unknown/电荷轴前提/结构化
omission_pattern_matches/H+_count1 命名;R5d 触发集合限定
{元素,电荷};恒等≠落点口径句)。v7 无变化。

**请评审**:确认已同意条款不需重评。

## 3. 判据三:admission 决策表与中心证据契约(v7 文本;有序,首中即决)

R1/R1b/R2/R2p(on/off 披露)/R2b/R3/R4/R5d{元素,电荷}/R5v/
R5c/R5/R6/R7 行语义同 v6;类型契约/内部重算/无 proof_record ⇒
unknown/复算比对含 center_match_basis/strict 轴/input_hash 域/
audit.scope/proof_scope+basis 披露同 v6。v7 重写注册补全规则的
**许可范围**:

- 4) 绑定核验(复算值)——系数绑定、λ_s、覆盖产物集两级映射、
  未知系数 ⇒ unknown_coefficients 同 v6;**注册计量补全规则增
  许可边界(R6-01)**:
  - 规则名 `atom_delta_stoichiometric_completion` 不变:Δ=
    elements(s)−elements(p);Σ 未覆盖产物元素 == λ_s×Δ⁺ 且
    Σ 未覆盖反应物元素 == λ_s×(−Δ)⁺,两侧各自精确相等不许
    抵消;无未覆盖参与物 ⇒ full;
  - **补全许可(新增,命名
    `composition_only_hydrogen_equivalents`)**:数值配平只证明
    未覆盖参与物的**组成**贡献;其**初始分子图的键变化/连接
    贡献**须另行核实。许可按**严格结构身份**(smiles_isomeric)
    登记为组合型氢当量:H2(`[H][H]`)与原子氢(`[H]`)——
    **H2 对 2[H] 只是 composition-only 作用域说明,不新增电子/
    自由基轴**(radical 保真轴仍是已登记缺口);**不按整类名称
    免审**(不因"是小分子/二原子"免),也不按整类名称一刀切
    拒;
  - **未登记身份的未覆盖参与物(即使数值全配平)⇒ 部分覆盖**
    (violation kind=completion_license_unregistered_identity,
    中心 unknown、不 R6)——依据:真实 AtomTool C→CCCO 只依次
    新增 C/C/O,不载入任何共底物初始图;C+CC=O/C+C1CO1/C+C=CO
    →CCCO 三个 C2H4O 异构体数值上都能补足同一 Δ,数值配平无法
    区分乙醛 C=O/环氧环键/乙烯醇 C=C 的贡献是否属实;
  - 正控保持:正常氧化/还原的明确计量补全(乙醇脱氢 CCO→
    CC=O+H2、乙醛加氢 CC=O+H2→CCO、原子氢当量 CCO→CC=O+2[H])、
    合法比例缩放(2CCO→2CC=O+2H2)、真实断裂分列/合并(碎片
    两级映射)在许可内 full;**不要求所有小分子共产物完整走
    AtomTool**,也不要求 S3 full_template/机制库;许可边界之外
    的贡献可另提交可确定复算的初始图证据后扩登记;
  - detail 机器披露:coverage_rule、completion_license、
    completion_license_scope(作用域说明文本)、
    unlicensed_uncovered_identities(未登记严格身份清单)、
    逐条 coverage_violations(数值类带数值、许可类带身份);
  - **边界声明**:本许可变化是**待审语义变更(v7)**——若认为
    氢当量之外还应登记其他组成型身份(如 O2/H2O/CO2 的特定
    作用域)或反之收紧,请给出可机器判定的登记判据;登记集
    只按"结构贡献完全由组成决定"的论证接纳,不按名称。

**请评审**:(a) 补全许可 scope 的化学合理性——"数值配平不证明
未登记多原子共底物初始图的结构贡献"是否为正确的默认;氢当量
(H2/[H])作为唯一登记许可是否过宽/过窄;(b) 许可按严格结构
身份登记、不按名称免审/拒审的边界;(c) 未登记身份 partial/
unknown(不 R6)的降级是否与"允许诚实 partial/unknown"一致;
(d) 既有系数绑定/两侧精确相等/未知系数语义不需重评。

## 4. 判据四:条件相容聚合(v7 文本)

1–4、7、9(非物种 known_absent 三分)、11(环诊断分轴)同 v6。
v6 的 10(a/b) 扩为:

10. **恢复/审核/派生入口共用同源契约 + 签名↔评估行对应
    (R5-04 + R6-03)**:
    - (a) 快照内部一致性同 v6(environment_fit/has_gate/
      essential_keys 与逐条行同源派生,单向矛盾判定;
      covered_requirement_signatures ⊆ 累积要求签名集合);
    - (a′) **签名↔评估行双向对应(新增)**:每条评估行携带
      requirement_signature(=该行评估的要求的 canonical JSON);
      快照 covered_requirement_signatures 集合必须**等于**逐条行
      的签名集合——签名只属累积要求集合不再充分:删评估行/清
      coverage/降 has_gate 而保留签名(快照"覆盖"了一个从未被
      评估记录的要求)⇒ context_snapshot_inconsistent 拒;行/签名
      由同一要求集合同源派生,任一侧单独被删即不一致;
    - (b) 内容身份同 v6(from_dict/audit 按构造期同源重算
      context_id;篡改任何语义字段保 id ⇒ 拒);
    - (b′) **派生入口先验父对象(新增)**:derive_child_context
      先调 validate_context_object(与 from_dict/audit 同源:版本
      门 + 快照一致性[含 a′] + 内容身份)——就地篡改的父不得经
      公开派生 API 不加新事实重算合法子 ID,再借子对象把旧必要
      unknown 洗成 verified/R6;
    - 保留:合法历史 unknown/conflict/satisfied 往返、正常阶段
      转换、same phase 跨 scenario、孤儿绑定显式 unknown、凭空
      签名拒绝;**不用当前事实重评旧边,不认证用户事实真实性,
      不要求防完全重造自洽历史**(重算 id 的自洽空快照走孤儿
      unknown,是诚实方向)。

**请评审**:(a) 签名↔评估行双向对应(而非仅属累积集合)的
判定;(b) 派生入口先验父对象的执行位置;(c) 既有 v6 条款
(三分/单向矛盾/内容身份/分轴)不需重评。

## 5. 判据五:供体一致性诊断(v7 文本)

1–3、5–7 同 v6(实际净变化判定基础/奇偶构型比较与非四面体
unsupported/联合映射三类支持范围/中心属性披露/strict 同源/
证据载荷内嵌);4(声明–执行净效应对账 + **镜像终态归一**)
同 v6——镜像终态先序列化再重解析后与实际比较(与冻结执行器
产物同口径;已声明断键的自然 E/Z 消失不称漏申报;失败按原
内存图;不改执行器)。v7 新增第 8 条:

8. **全部原始字符串入口与工厂/strict 同源守卫(R6-02B,新增)**:
   供体诊断消费的**四个原始字符串**——current.smiles(编辑前
   渲染事实)、result.product_mapped_smiles(执行图)、
   result.product_smiles(对外产物)、expectation.target_smiles
   (预期产物)——在解析之前统一过判据一的输入侧守卫;未登记/
   并列未知 CX 项 ⇒ 结构化拒绝(kind=raw_input_cx_class_
   unregistered,带字段名),**任何轴不得以剥掉标记后的解析
   身份参与 verified 证据**(实测:干净乙醇→乙醛执行仅在
   current 或 mapped 接口加 `|r|`,v6 诊断 True/True、公共
   audit→R6;指定手性底物远端编辑同样成立;审计复算链对
   proof_record 内含未登记项同样拒绝)。clean 输入与全部
   既有正控不受影响。

**请评审**:(a) 四个原始入口与工厂/strict 共用同一守卫的
完备性(是否还有消费原始串的入口);(b) 拒绝(而非轴
unknown)的选择;(c) 镜像终态归一条款(v6)不需重评;
(d) **两处表述边界**:原始 `r` 标记被拒绝**不**解释为"已证实
实验精确消旋";裸指定 SMILES(无来源记录)**不**称为实验
纯品——身份层只声明表示事实。

## 6. 程序证据与状态(程序事实,不替代化学判断)

- 规则级测试:ppv1 全量 **508 passed/0 skip**(451 v6 存量 +
  57 新增 R7 回归,全部合成夹具);新增回归在基线 6d90201
  **红 33/57**——其中 26 红为复审反例行为翻转(复杂共底物
  3、并列未知 CX 9、供体原始入口 6、derive 洗白 2、首提既存
  行 4、清单删项 2)、7 红仅因 v7 新披露字段(completion_
  license/unlicensed_uncovered_identities/requirement_
  signature)或新表(event_appearance_links)缺失(其核心语义
  断言在基线已通过)、24 绿为基线已绿的正控制;
- R6 复审探针在 v7 复跑(R6 证据目录 reproduce.py --allow-head-
  change,隔离临时目录):五组 P1 逐案翻转、旧控制保持
  (genuine 氧化/氢化 verified/full/expand;existing_state_
  first_valid created=True;multi_occurrence normal 重放
  created=False;删行留清单 entry_missing);assert_observed.py
  按设计在翻转点失败(它钉住 R6 当前缺口,不是修后期望);
- G01 全量 not slow:1119 passed/16 deselected(611 legacy +
  508 ppv1;legacy 路径零改动,冻结 AtomTool 未改);
- 存储两项(R6-04/05:mimo 不审,仅披露):首提复用既存行
  立即共用重放同源校验(四例损坏首提即 Ppv1LedgerCorrupt
  零写入);事件出现集合新增独立完整性表 event_appearance_
  links 与 payload 清单双向核验(删清单项/删行/删 links 行
  均损坏;schema 升 ppv1-store-7 拒旧库,无迁移);
- 判据未冻结;v7 语义变更(补全许可/输入词法/签名对应/供体
  原始入口守卫/存储完整性表)全部**待审**;契约族升
  ppv1-*-7(未发布 profile,无历史产物迁移;旧 -6 载荷按
  未知版本既有门拒绝);
- 参考(外部常识,非本仓资产):RDKit Book(CXSMILES 扩展/
  增强立体/立体化学章节/非四面体立体支持说明)、rdCIPLabeler
  API;CXSMILES 解析器行为经 Release_2026_03_6 源码取证
  (parseCXExtensions 主分派循环)与实证用例校准。

## 7. 请求的回复格式

对每条判据:1) 结论(同意/不同意/有条件同意+条件);2) 可直接
落进规则文字的修改建议;3) "程序上诚实但化学上误导"风险点。
逐条表态,不接受总体评价式回复。
