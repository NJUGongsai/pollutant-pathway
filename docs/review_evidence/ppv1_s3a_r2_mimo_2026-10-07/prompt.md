你是独立外部化学评审员，对 pollutant_pathway_v1 化学判据草案第十轮版本（v10，S3a 回修 r2 后，尚未冻结）做化学评审。评审请求全文附在最后（本版自包含展开，规则全文在请求内）。

回复要求（与请求原文的回复格式要求相同，重申）：对请求列出的各判据**逐条**给出：1) 结论（同意/不同意/有条件同意+条件）；2) 可直接落进规则文字的修改建议；3) "程序上诚实但化学上误导"风险点。不接受总体评价式回复。

执行边界（重要）：
- 本轮你只能用读取类工具浏览仓库源码/文档来核对请求中的表述（仓库根 /Volumes/CC/Enzyme_Agent/dependingv43；判据实现于 src/pathway_v43/pollutant/，S3a r2 变更集中在 search.py 与 profile.py，回归测试 tests/test_ppv1_*.py）；你**没有 shell 执行权限**，无法运行测试或探针——若某项判断必须依赖执行证据，请如实标注"待执行验证"并说明需要跑什么，**不要编造任何执行结果或数字**。
- 禁止访问 gitignored 金标/题面目录（如 reports/phase_s0_hit60/manual_review/）及任何金标、题面、封存逐题 run 内容；本轮评审仅限规则级判据文本。
- 不修改任何文件，直接输出评审回应文本。
- 请求原文自包含（规则级表述+合成夹具，无金标）；你的结论基于请求文本与你实际读到的代码。注意：S3a r2 只闭合搜索消费协议（工程事实、不新增化学判据）；主会话已本机独立复跑 PPV1 648 绿证实；G01 采用安全隔离口径。

--- 评审请求全文如下 ---
# mimo 化学评审请求:pollutant_pathway_v1 化学判据(S3a 回修 r2 版 v10)

- 日期:2026-10-07(S3a 回修第二轮;替换同日 v9 请求。v9 送审快照
  已存 `docs/review_evidence/ppv1_s3_impl_2026-10-07/s3a_r2/mimo/`;
  旧回应 r5–r9 原样保留不覆盖)
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或
  发布前)
- 评审对象:S0–S2 判据(ppv1-*-8 契约族,文本含 v8/v9 落字)+ S3a
  搜索底座化学消费契约边界的 r2 更新(ppv1-search-2 / ppv1-store-9
  / ppv1-profile-10 / search-limits-3);**判据尚未冻结**
- 与 v9 的差异来源:Codex S3a 复审
  (`POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_2026-10-07.md` §4 五组 P1
  + §5/§6 精度项)。r2 回修只闭合搜索消费协议(工程事实),**不
  新增任何化学判据或门禁**;受审文字为:0b 节边界披露更新、判据三
  的 mimo 精度更正(⑥:coverage 枚举/早退口径)、v9 已落字的各处
  精度确认
- 自包含性:**本版展开必要规则全文,不再以"同 v7/v8"缩写引用历史**
  (复审 §6 P2 3);规则级表述与合成规则级夹具,无任何金标/题面/
  封存逐题数据;由用户转交,回复原文落盘 `docs/`;实施 agent 不调用
  模型,只读/执行类声明一律待执行验证

## 0. 背景(一段话)

S0–S2 判据 v8 经 R8 独立复审放行;S3a 首批(底座)经 Codex S3a
复审发现五组 P1(输出恢复错绑、完成/恢复接受坏权威账、预算可退还
已执行额度且配置首消费失守、请求同键异内容及执行权失守、停止报告
漏掉正在执行的动作),本批(r2)已逐组闭合并有行为级红绿回归
(新回归 54 项在直接父基线 9b78f42 红 52/绿 2;ppv1 全量
**648 passed/0 skip**;G01 安全隔离数字见 §6)。**S3b 仍未交付**:
队列化学集成(冻结池/备选/两类 deferred 调度)、条件依赖/场景转换、
`proposals[]` 模型协议与有界格式反馈、固定 AtomTool 中心证据生产
链、PPV1 独立 runner 分流(公开 start_run/resume_run 对 PPV1 继续
fail-closed)。目标不变:可能降解路径与条件相容路径的诚实表示;
unknown 不升格;verified 不靠模型或调用方自报字符串;账平、物种同
CN 或一份正确局部诊断不能代替整条声明的覆盖与追溯。工程数字是
合成规则级契约结果,不代表 dev(B1 环境中间步骤)或 298(RHEA
通用酶学)科学性能。

## 0b. S3a r2 实现与未实现边界(工程披露;受审表述)

- **r2 闭合的五组消费协议缺口(全部为工程记账行为,不改化学判定)**:
  1. B3 bundle 消费、write_commit_bundle 写侧与正常提交共用
     action+attempt+task+event 完整身份绑定 —— 属于别的动作身份的
     有效事件在写 event/commit/consume 之前拒,artifact 保全;
  2. 首次 complete、B4 补账、done/已有提交结果复用统一经**公共
     `store.submit_event` 重放分支同源**的完整事件账权威核验
     (states/出现/假设/投影/计划/清单/links 行齐全且内容一致),
     并核本 action 的 attempt/预约引用行 —— 12×2 坏事件账在首次
     消费前结构化失败、零补账;
  3. defer 先核"确实未执行"持久事实(已提交事件/已发送请求/已
     落账 attempt 不退已用预算);注册/读取/恢复共用 profile 的
     十键类型/范围/版本单一校验实现;
  4. 模型请求同键异身份内容(载荷/purpose/action/损坏 hash)结构化
     冲突零写入;登记/发送/响应/失败核合法 run/action/attempt
     执行引用与生命周期;
  5. 停止报告披露 claimed action 与 open attempt,执行未完成不称
     exhausted_search。
- **v9 表述更正(受审)**:v9 0b 曾写"不存在经搜索层绕过化学验证
  产生 verified/事件的路径"——该全称被复审 B4/done 证据反驳(当
  时 get_event 索引列被当完整性证书,坏事件账可经恢复入口补账)。
  r2 后的准确表述:**搜索层全部事件消费入口(正常提交/B3/complete/
  B4/done 复用)都经公共 writer 同一验证源;消费侧权威核验是"写账
  前的只读复核",其强度与正常 writer 重放一致,不是第二套独立
  化学算法**(候选阅读:mimo⑤同类口径——同源复用,非独立双算)。
  该闭合有 54 项 r2 回归支持(含 24 个坏事件账反例逐案恢复前拒)。
- **未实现(S3b,不冒充已交付)**:冻结池/备选/两类 deferred 的调度
  语义与 expected_parent_revision 激活;条件依赖/场景转换实际进入
  调度;模型协议与格式反馈;冻结 AtomTool → donor 诊断 → converter
  → audit → admission → submit 的生产调用链(**S3a/r2 仍未新增
  audit_hypothesis 生产 caller**,判据五 8d 的 caller 义务继续由
  S3b 承担);PPV1 独立 runner 双入口(继续 fail-closed)。
- 搜索层不构造/不修改任何化学对象;停止不是化学终点:停止报告保留
  未探索集合(deferred/blocked/悬空请求/claimed/open attempt),存在
  deferred/知识缺口时不称"所有路线都探索完";chemical endpoint 评估
  属 S4,本批不产出任何终点/矿化/解毒结论。

## 1. 判据一:分子身份(v10 文本,自包含)

**1. 身份键**:`state_id` = **化学 CX 事实子集**的规范化 canonical
CXSMILES 的稳定哈希。生成前移除非化学 CX 元数据:坐标(conformer)、
原子标签(atomLabel)、任意 atomProp(绘图/注释不改严格分子图身份);
保留增强立体组(AND/OR/绝对)、自由基层、基串内的同位素/电荷/
立体。无组且无自由基层注解的分子输出与普通 canonical isomeric
SMILES 逐字相同(自由基分子带 `|^n:…|` 后缀是例外:身份层区分
自由基,保真轴为已登记缺口)。与 RDKit RegistrationHash 的一致性
限定在整组翻转/部分反转/排列/kekulé/映射号子集;plain≡`|a:…|`
同键是本仓归一设计,与 RegistrationHash 的 CANONICAL_SMILES 层
存在已登记分歧。

**2. 输入侧注册感知校验(原始串词法守卫)**:解析**之前**对原始
结构串逐项词法 —— RDKit 解析会静默丢弃 `|r|`、`|Ln:1|`、`|c:1|`、
`|wU:1.5|` 等未登记块(之后与裸输入同 state_id,输出侧守卫永远
看不到),故输入侧按真实 CX 类边界逐项分派:项序列由 ','/空格
分隔;登记类(atomProp/SgD=移除类;Sg=保留类;$…$ 标签值块与
(...) 坐标块=移除类;`a/o/and/or/rad` 立体注解=保留类)各自耗尽
自己的字段(字段内逗号/空格是内容,**登记内容含空格放行**,如
`atomProp:0.note.hello world`);未登记首头(含并列位置,如
`atomProp:0.n,r` 的 `r`)显式拒绝;DAT(SgD)值内逗号继续受
保护(DAT 剥离有适配器前提,只剥已登记 SgD 形态)。同一守卫覆盖
**全部原始 CX 入口**:工厂 build、strict_identity_of、判据五的
四个原始字符串字段、恢复入口与 audit 直接对象(2b)。

**3. 混合并列 ABS 归一**:ABS(绝对立体)注解剥离为令牌级语法
解析(`a:1,&1:3` ≡ `|&1:3|`、`^1:0,a:1` ≡ `|^1:0|`;段级正则对
逗号并列形态匹配不上会造成同一立体事实分裂成两个 state_id——
已修复)。plain 与 ABS 归一后的分子同键。

**4. 公开表示往返闭合**:`smiles_isomeric` = 身份键同串(往返
无损);`structure_smiles_raw` 保留原始串与 structure_origin/
source_refs/分轴 representation_fidelity 一起存出现记录(appearance),
语义块(states 行)只存严格分子事实 —— representation_fidelity
不是语义成分,同图不同来源保真度共存、互不升级/降级;需要某来源
保真度必须按出现取。

**2b. 恢复/直接对象首消费同源验证(v8 新增,v9 落字三处)**:
恢复入口(`ChemicalState.from_dict`)与 audit 直接 states 对象在
首次授信前共用与公共 writer 同源的纯状态验证
(`validate_state_object`):(i) 版本门 + fidelity 分轴契约 +
structure_origin 合法;(ii) 结构态:raw 非空且过判据一第 2 条
同一输入守卫(未登记项 ⇒ 拒,不静默清洗信息再授 full);(iii)
raw 重推严格身份 == smiles_isomeric(同图异拼写如 OCC 接受;跨
分子如 H2 状态挂 CC=O 拒);(iv) smiles_isomeric 须为身份键规范形,
state_id/formal_charge/cn_identity/立体/同位素状态按工厂同源重推导
一致;(v) CN-only 走专用命名空间身份(cs(cn-only,cn))+ 未知
事实契约(不重推导结构)。v9 三处落字:
- **同源验证证明与工厂契约一致,不是独立双算** —— 两个包装实现
  的存在不自动变成新阻塞,下游不得读成双重独立证明;
- **原始 `r` 标记的存在与含义均不被采纳也不被反驳**:拒绝事实
  不得用于推断实验消旋/样品纯度;裸指定结构/strict 身份也不是
  同样品或对映纯认证(拒绝是输入表示层契约,不反推输入真实化学
  含义;当前 RDKit 直接解析 `CCO|r|` 能输出 CCO,守卫拒绝不能
  反推样品 —— v9 ②对称文字);
- **canonical+r 的上层错误名语义**:canonical 串加 `r` 走
  `state_structure_unparseable` 拒绝,该上层 kind 实际包裹**工厂
  未登记 CX 类守卫拒绝**(内因 unregistered_cx_class;真坏串内因
  是 unparseable_smiles)—— 不等于 RDKit 本体不能解析、更不表示
  化学非法或实验事实已证;补读法:读内因 reason.kind,不用外层
  名作全称化学判断(P2 精度,mimo v9 ①)。
- 自报 formal_charge/stereo/isotope 与结构重推导一致的声明,
  限定"经首消费验证的入口"(2b 覆盖的 from_dict/直接对象/工厂/
  writer),不是所有裸 dataclass 对象的无条件性质。

**请评审**:(a) 2b 三处落字与 r-不反推/内因读法精度是否准确、
不引入越权认证;(b) 入口清单(工厂/strict/判据五四字段/恢复/
直接对象/搜索层全部消费入口)是否闭合,不产生身份或 verified
证据的诊断入口(池输入 preview 的 conservation 诊断、冻结执行器
内部解析)按 C2 划界在守卫外、其结果不得回流为身份或核实证据
(preview 保持 pool_unchanged/diagnostic_only);(c) 判据本身
(1–4)无需重评——文本如上展开供自包含核对。

## 2. 判据二:参与物计量与元素/电荷核算(v10 文本,自包含)

- **全氢账**:元素核算按全氢(分子式含 H);D/T 合并计 H(已
  登记披露,不区分同位素);**自由基电子不计入元素/电荷账**(数值
  账"平"在这两类有系统盲区,不得读成质量/电子守恒已核)。
- **系数契约**:participants 的 coefficient 为 None(unknown)或
  正有限数;系数状态 coefficient_status 枚举;声明系数与结构重
  推导的可确定不一致按契约拒绝(表示层违约,判据三 R2b),不是
  化学否定。
- **完整性 unknown**:未知系数 ⇒ coverage unknown_coefficients
  (中心结论 unknown,不猜数值);known_absent 三方语义
  (registered_missing/documented_absent/unrecorded)分开。
- **电荷轴前提**:formal_charge 判定以经首消费验证的结构重推导
  值为前提(2b 后不可被直传对象伪造);电荷与元素分轴,不互相
  抵消解释。
- **结构化 omission_pattern_matches**:缺参与物按模式匹配结构化
  报告(不静默);R5d 触发集合显式限定
  {element_accounting, formal_charge_accounting},其他 violated 走
  R5v 独立码(防新增检查静默挂进"声明账不一致")。
- **恒等 ≠ 落点**:净反应两侧同分子(恒等变换)不因元素/电荷平
  而获得任何"转化已核实"结论;数值配平只证明组成闭合,不证明
  转化身份、机理或未覆盖参与物初始图的键变化(与判据三的 full
  两根据互锁)。

**请评审**:确认文本展开与已同意条款一致(v9 无变化,r2 亦无
变化);重点确认"数值配平≠结构贡献已核实"的口径未被 r2 工程回修
改变(未改变)。

## 3. 判据三:admission 决策表与中心证据契约(v10 文本,自包含;
有序,首中即决)

决策表(评估顺序固定,首中即决):

```
R1  structure_unparseable      → reject  (实际输入语法非法;CN-only 等
    合法缺结构走 unknown,悬空引用走 R1b,不进本行)
R1b participant_state_missing  → reject  (参与物 state 引用悬空 = 账本/
    引用完整性问题,理由码保留,不压平成"结构不可解析")
R2  active_gate_rejected       → reject  (活动门禁显式拒绝;仅 reject_gates
    名单内 —— 不暗改冻结判据,新门禁须独立评审)
R2p per_product_gate_rejected  → reject(全部共同产物被拒)/
    retain_conditional(部分被拒:被拒产物保留拒因、不可展开,不删除
    被拒共同产物凑合法事件)
R2b contract_violated_representation → reject (表示契约违反:零/负/
    非有限系数、酶计入净计量、结构性违约;理由码 representation =
    非化学)
R3  current_scenario_conflict  → defer   (有来源 essential 条件与当前
    场景已知事实冲突;action=blocked,假设保留不在此场景展开)
R4  budget_or_wait             → defer   (独立原因)
R5d declared_account_violated  → retain_conditional(触发集合显式限定
    {element_accounting, formal_charge_accounting};账不平只证明声明
    内部矛盾,不证明反应不存在;绝不进入 R6)
R5v declared_violated_other    → retain_conditional(其他检查 violated
    的独立码,如确定性 checker 的中心偏离)
R5c required_check_coverage_missing → retain_conditional(必需适用检查
    未被执行/不在审计内:窄 audit_scope 只能作诊断,R6 覆盖核算
    不通过)
R5  unknown_checks_present     → retain_conditional(检查 unknown/因缺
    输入未执行;继承未解决依赖)
R6  default_all_verified       → expand(全部必需适用检查覆盖且
    verified,无 unknown/violated/缺输入未执行;语义 NA 白名单除外)
R7  no_applicable_checks       → retain_conditional(无适用检查:保守
    保留,不冒充核实)
```

任何 unknown 不自动 reject;新增"诊断转拒绝"必须扩表并升版本;
chemical_reproposal 首版 off。

类型契约/内部重算:center_evidence 的判定字段由**内部重算**(不采
信自报签名/字符串)产生;无 proof_record ⇒ unknown(不猜);复算
比对含 center_match_basis 披露;proof_record 载荷不可变 + 入口身份
复算(改前提不换 ID ⇒ 拒);跨假设复用 proof ⇒ 拒。audit.scope/
proof_scope+basis 分轴披露:缺 proof/映射/参与物覆盖时 unknown/
partial(center_checker_scope_unknown 等),字段存在不等于适用。

**覆盖核算与补全许可(composition_only_hydrogen_equivalents)**:
绑定核验按复算的底物/产物身份做整组覆盖;产物覆盖判定输出
`product_coverage` ∈ {full, partial_unchecked_transformation,
unknown_coefficients} 与逐条 `coverage_violations`(kind 如
coefficient_binding_mismatch[系数与声明不符]、completion_surplus/
deficit[补全规则数值不符]、completion_license_unregistered_identity
[未覆盖参与物严格结构身份未登记许可])。**覆盖 full 的两个互不
替代根据**:① 无未覆盖参与物;② 注册补全规则(H2/[H] 按 2[H]
氢当量)数值精确相等且未覆盖参与物身份全部在登记许可内。**二者
都只解除覆盖轴** —— 补全(无论是否持许可)只证明组成闭合,不
证明转化身份、机理或共底物初始图的键变化已核实;身份归 strict
轴、元素/电荷归判据二、转化核实归证据门。

**v9 落字两处 + v10 精度更正一处**:
- **scope 归属(v9,⑤已落地)**:当前代码 `completion_license_
  scope` 字面**不含**"不区分键断裂方式与电子去向"句;该表述归属
  **许可定义/本规则正文**(composition-only 许可不区分该参与物的
  键断裂方式与电子去向,是许可的语义边界)。字段字面未改、无版本
  身份影响;**本请求不再要求改代码 scope 字面**(复审 §5:已在
  规则正文,勿再当未闭合项)。
- **恒入 ≠ 已适用(v9)**:`completion_license`/`completion_license_
  scope` 恒入 center detail,字段存在不等于本结论使用了补全许可;
  判定"本结论依据含许可补全"须同时看 **product_coverage=full、
  uncovered_reactant_refs/uncovered_product_refs 非空、
  unlicensed_uncovered_identities 为空** 三条件组合;license_applied
  标志/顶层别名/同屏渲染列属后续 API/展示层(P2,不作本轮门)。
- **v10 精度更正(mimo v9 回应 ⑥ 的判负口径,受审)**:mimo 曾
  概括"partial = 许可本身判负"—— **不精确,不得照抄**:
  (a) 实际枚举是 `partial_unchecked_transformation`(存在额外
  未核实转化/未核实结构贡献),不是裸 "partial";
  (b) uncovered+partial 组合下 `coverage_violations` 可能是
  `coefficient_binding_mismatch`(系数与声明不符)或补全数值
  不符,与许可是否登记无关 —— **不能一律称"许可本身判负"**,
  须读 coverage_violations 的逐条 kind;
  (c) `unknown_coefficients` 等早退(coverage unknown)发生在
  覆盖判定之前,**尚未使用许可**,不得称"已使用许可后判负";
  (d) 许可未登记身份的 case(completion_license_unregistered_
  identity)才直接关联"数值配平不证明未登记多原子共底物初始图
  的结构贡献"这句规则正文。

**请评审**:(a) v10 精度更正四点(a–d)是否准确反映实现语义、
足以防止下游把 coverage 枚举读成"许可判负";(b) v9 scope 归属
与恒入≠已适用+三条件判定是否如实(确认后本项不再列入后续请求);
(c) 决策表与覆盖核算展开文本是否与实现一致。

## 4. 判据四:条件相容聚合(v10 文本,自包含)

- **快照一致性**:路径上下文快照由已验证父对象派生,派生先验
  validate 父对象;快照的 covered_requirement_signatures 与已记录
  的 per_requirement 评估行**双向对应**(签名↔行双向:删行/改
  签名都拒)。
- **内容身份**:PathContext 内容身份同源重算;**两种不可变机制
  分写(v9 落字)**:Requirement/ConditionFact 由 frozen(嵌套冻结)
  强制;PathContext 本体**非 frozen**,其不可变性由消费前 validate
  的内容身份同源重算兜底(就地改语义字段保留原 context_id ⇒
  `context_content_identity_mismatch` 拒)。不得把两种机制写成同一
  类不可变;任何派生/评估/审核入口消费前必须先 validate(绕过
  validate 直读字段属违约)。
- **三分与矛盾**:条件评估三分为 satisfied/conflict/unknown;已知
  事实与要求冲突为**单向矛盾**(conflict 只阻止当前场景,不反证
  全局);孤儿引用(评估行无对应要求)按 unknown 处理不崩溃。
- **场景评估口径**:文献观察环境、矩阵"污水"标签、工具隐式
  O2/H2O、transformation_class 标签都**不能**构造当前条件事实;
  请求 condition_compatible 不是已相容;空要求/未知覆盖不自动
  compatible(相容判断需实际评估)。
- **行↔签名对应的契约前提**:绑定字段一经冻结不得后改;变更须
  走新评估/新快照(将来引入要求可变性,旧快照整体拒绝是故意
  fail-closed,不当 bug 修)。

**请评审**:确认分写/口径与实现一致(v9 无变化,r2 无变化)。

## 5. 判据五:供体一致性诊断(v10 文本,自包含)

- **判定基础 = 实际净变化集**:供体编辑一致性以键 diff ∪ 电荷/
  立体/同位素变化集的实际净变化判定(含 bond_stereo_change 与
  键级立体入变化集;非四面体公开列项按标签类型分开),不采信
  声明的"编辑列表"与实际不一致的自报。
- **奇偶构型比较与非四面体 unsupported**:四面体手性按奇偶
  (parity)构型比较;非四面体立体(_at 等)公开列
  unsupported(不冒充核实也不静默拒);E/Z 与非四面体轴分开。
- **联合映射三类支持范围**:原子映射支持范围(完全/部分/缺失)
  与歧义映射分列;缺/歧义映射 ⇒ 中心 unknown(partial),不猜
  对应。
- **中心属性披露/strict 同源**:诊断输出的中心属性(参与物/键/
  电荷/立体)按 proof_scope 分轴披露;strict 目标比较与
  strict_identity_of 同源(与身份键同一推导,不是第二套)。
- **证据载荷内嵌**:check 结果(含 proof_record)内嵌进审核证据
  载荷(不可变、入口身份复算);跨假设复用/篡改 proof ⇒ 拒。
- **四个原始字符串入口与工厂同源守卫**:供体诊断的四个原始结构
  串字段与工厂共用判据一第 2 条输入守卫(未登记 CX 项 ⇒ 契约
  拒绝)。
- **声明–执行净效应对账 + 镜像终态归一**:声明编辑与实际执行
  对账(镜像活 ID 表 + 前置复核);终态序列化与冻结执行器对齐。
- **8b 拒绝与失败早退(v9 落字,精度保持)**:失败诊断是**三个**
  判定字段 reaction_center_match/strict_target_match/legacy_cn_match
  均为 None、`diagnostic.center_evidence={}`;**converter 仍返回
  版本/来源元数据与 center_match=None**(不是"四轴 None",也不
  是"converter 整个 evidence 为空")。None=未评估,**不等于通过**;
  `execution_ok=False` 早退路径不解析三字段亦不消费其任何轴,无
  verified 泄漏面。拒绝为契约性拒绝 ⇒ 本次诊断/审核不产生任何
  轴结论与 disposition;调用方不得吞异常后按 retain/verified/
  any-R 行记录(异常≠处置行)。两处表述边界:拒绝原始 `r` 不构成
  "已证实实验精确消旋";裸指定 SMILES 只声明表示事实,不称实验
  纯品/对映纯;strict=True = 同一化学身份,不是同一样品/同一
  立体纯度。
- **8d caller 义务(如实披露,仍未闭合)**:S3 新 caller 必须承担
  "让 AuditContractError 逃逸并中止本次 admission 计算/提交"的
  义务,不得吞异常继续。**S3a/r2 未新增生产 caller(生产链属
  S3b)**,该义务尚未被执行证据闭合;当前静态证据(10 个
  AuditContractError 抛点无 enclosing 宽捕获 try-body、
  check_edit_against_donor 唯一源内调用无 try 祖先)不是动态安全
  的通用证明。S3b 交付生产链时以实际调用与宽捕获负控闭合。

**请评审**:(a) 8b"三个 None + converter 元数据"表述与早退边界
是否准确;(b) 8d"未闭合但如实披露"作为 S3a/r2 边界是否可接受
(闭合路径 = S3b caller + 回归测试);(c) 其余条款展开文本是否
与实现一致。

## 6. 程序证据与状态(程序事实,不替代化学判断;执行类声明待验证)

- 规则级测试:ppv1 全量 **648 passed/0 skip**(594 v9 存量 + 54
  r2 新增,全部合成夹具;54 项覆盖五组 P1 反例与合法控制);
- 基线红绿(直接父基线 9b78f42 detached worktree 同字节):新
  回归 **52 行为红 + 2 正控绿**(坏案按预期失败 = 修前缺口;合法
  未执行 defer 释放/非 expand 空 attempt 请求两正控在基线亦绿);
  更新的既有测试 2 红(1 行为红:提交记录 event_id 篡改在基线仅
  报事件缺失,r2 先在记录哈希层拒;1 版本红:profile-10 断言)+
  79 绿;无 collection 红(新回归只用公开 API,基线可收集);
- G01:安全隔离工程回归(R7 路径白名单 + R8/S3a/r2 输入;不复制
  evaluation/金标/题面/封存/v4;固定 PYTHONPATH/空 BBD_DATA_ROOT/
  V3_CODE_ROOT/V43_ASSET_ROOT/DEPENDING_V3_ROOT)⇒ 实际数字见
  交付书与本批证据(预期 1196+54=1250 passed/8 skipped/
  17 deselected;8 skip = 5 真实评价依赖 + 1 v4 对照源 + 2 phase_d
  派生 metadata;17 deselect = 16 slow + 1 明确排除 export 用例,
  逐项 nodeid 披露;R7 历史 1110/8/17、R8 历史 1138/8/17 与 S3a
  首批 1196/8/17 单列,不混计);
- 契约族:search ppv1-search-1 → **ppv1-search-2**(消费协议闭合),
  profile -9 → **-10**(contracts 登记);store 保持 -9(表结构与
  writer 行为未改,r2 权威核验从 search 层调用公共 submit_event,
  不复制校验);search-limits 保持 -3(注册/读取/恢复改同源复用
  profile 的 validate_search_limits 单一实现,计数语义未动);
  PPV1 从未放行执行流,无历史产物迁移;
- 判据未冻结;v10 无新化学机制;受审文字:0b 边界披露更新
  (v9 全称被反驳后的准确表述)、判据三 v10 精度更正(a–d)、
  v9 已落字各处(判据一 2b 三处/判据三 scope 与恒入/判据四分写/
  判据五三个 None 与 caller 披露)的确认;
- 参考(外部常识,非本仓资产):RDKit Book(CXSMILES 扩展/增强
  立体/立体化学章节)、rdCIPLabeler API;CXSMILES 解析器行为经
  Release_2026_03_6 源码取证与实证用例校准;**冻结前须以执行
  证据复核 RDKit(锁定版本)词法取证与放行正控的往返无损**。

## 7. 请求的回复格式

对每条判据:1) 结论(同意/不同意/有条件同意+条件);2) 可直接
落进规则文字的修改建议;3) "程序上诚实但化学上误导"风险点。
逐条表态,不接受总体评价式回复。执行类声明一律标"待执行验证"。
