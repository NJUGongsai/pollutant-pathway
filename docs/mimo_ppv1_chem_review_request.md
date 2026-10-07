# mimo 化学评审请求:pollutant_pathway_v1 化学判据(S3a 回修 r4 版 v12)

- 日期:2026-10-08(S3a 回修第四轮;替换 2026-10-07 v11 请求。v11
  送审快照已存 `docs/review_evidence/ppv1_s3_impl_2026-10-08/s3a_r4/
  mimo/mimo_ppv1_chem_review_request_v11_sent.md`(字节同仓内 v11);
  旧回应 r5–r11 原样保留不覆盖)
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或
  发布前)
- 评审对象:S0–S2 判据(ppv1-*-8 契约族)+ S3a 搜索底座消费契约的
  r4 更新(ppv1-search-4 / ppv1-store-9 / ppv1-profile-12 /
  search-limits-3);**判据尚未冻结**
- 与 v11 的差异来源:Codex S3a 复审 R3
  (`POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R3_2026-10-08.md` §4 三组
  残余 P1(S3A-02/03/04 的必要集合/状态口策略/生命周期来源)+
  §6 mimo v11 八条件裁定与事实澄清)。r4 回修只闭合搜索消费协议的
  残余工程缺口,**不新增任何化学判据或门禁**;受审文字为:0b 节
  边界披露更新、§0c 重写的"mimo v11 回应八条件采信/纠错清单"、
  判据一 2b 的 v12 括注更正与真实 token 落字、判据二的系数句与
  known_absent 轴归属、判据三的 R2b caller 映射与入口划界、判据五
  8b 的"失败 diagnostic 与下游 audit 分开"落字(见各节"v12 落字")
- 自包含性:本版展开必要规则全文,不以"同 v7/v8"缩写引用历史;
  规则级表述与合成规则级夹具,无任何金标/题面/封存逐题数据;由
  用户转交,回复原文落盘 `docs/`;实施 agent 不调用模型,只读/执行
  类声明一律待执行验证

## 0. 背景(一段话)

S0–S2 判据 v8 经 R8 独立复审放行;S3a 首批五组 P1 经 r2 闭合
S3A-01/05 及三组主要反例,r3 闭合三组残余的行级内容/冻结策略/引用
消费缺口;复审 R3 确认 S3A-01/05 与 r3 行级旧反例全部保持关闭,但
三组仍各有同合同内更深层入口残余:S3A-02 必要预约**集合**缺项
(逐行守卫在、集合不完整仍可消费)、S3A-03 请求**状态口**未消费
冻结策略、S3A-04 枚举外状态可被正常改记 failed。本批(r4)已逐组
闭合并有行为级红绿回归(新回归 90 项在直接父基线 41d0cd5 上
**77 未发生指定异常红 + 1 形态红 + 12 正控绿**;ppv1 全量
**787 passed/0 skip**;G01 安全隔离数字见 §6)。**S3b 仍未交付**:
队列化学集成(冻结池/备选/两类 deferred 调度)、条件依赖/场景
转换、`proposals[]` 模型协议与有界格式反馈、固定 AtomTool 中心
证据生产链、PPV1 独立 runner 分流(公开 start_run/resume_run 对
PPV1 继续 fail-closed)。目标不变:可能降解路径与条件相容路径的
诚实表示;unknown 不升格;verified 不靠模型或调用方自报字符串;
账平、物种同 CN 或一份正确局部诊断不能代替整条声明的覆盖与追溯。
工程数字是合成规则级契约结果,不代表 dev(B1 环境中间步骤)或
298(RHEA 通用酶学)科学性能。

## 0b. S3a r4 实现与未实现边界(工程披露;受审表述)

- **r4 闭合的三组残余消费缺口(全部为工程记账行为,不改化学
  判定)**:
  1. **S3A-02 必要预约集合完整性**:`_verify_action_references`
     在既有逐行内容守卫(保留不动)之后,按 claim/`_create_attempt`
     现有创建规则**同源派生**本 action 应有的必要预约集合(总
     action 恒有;scenario_transition 另有 transitions;expand 按
     attempt 引用集有 alternatives/attempts,attempt 行记录
     reopen_of 非空另有 reopens;retrieve 的两条检索预约按"行存在
     ⇒ 必须被引用"核验 —— cache_hit 合法认领不落检索预约行,不强
     加),必要行被删或引用清单缺项**即使剩余清单非空也先结构化
     拒**,覆盖 first complete/B4/B3 事件提交前/B1/defer/done 四口;
     B3 事件提交之前先核,坏链 0 event/commit/consume、artifact
     保全;不猜补缺行;预约 ID 派生抽出单一来源函数与 `_reserve`
     共用(核验与创建同源,不是第二套派生);
  2. **S3A-03 请求状态口接冻结策略守卫**:record_request_sent/
     response/failed 在新 status 写入之前消费**同一**严格冻结块
     校验(`_limits`/validate_frozen_search_limits)—— 存储
     search_limits 为 null/缺 version/坏值 ⇒ 状态口先结构化拒
     (search_policy_block_corrupt)且无成功状态变化,与预算/认领/
     恢复同一守卫来源(不补默认、不依赖 expected policy 或调用方
     预验;合法已登记请求不重新扣额度、失败/悬空占额、scripted
     网络 0 保持);
  3. **S3A-04 非法来源状态不能改记合法 failed**:mark_request_
     failed 正面限定只有 registered/sent 是合法来源(枚举外未知
     来源结构化拒 request_status_unknown 并保全,不静默洗成合法
     终态);register 同键复用对存储状态核枚举(坏行按完整性失败
     拒,不把坏状态当合法幂等 unchanged 返回);recover 对 run 范围
     状态枚举外请求行结构化披露(不改状态、不猜补)。
- **r2/r3 已闭合并经复审 R3 确认保持的项(不重开)**:S3A-01 四类
  异身份输出绑定、S3A-05 停止披露、r3 的行级内容判据(预约单位/
  状态/scope-subject、attempt 状态/hypothesis/task、提交记录归属/
  kind/适用引用、附随投影/计划首提同判据、B3 事件前置、done submit
  真实已完成 event)、r3 的冻结策略读取/恢复/预算/认领严格核验与
  请求身份/引用闭合。
- **并发边界如实披露(复审 R2/R3 §5 裁定保持)**:complete 的只读
  预核验与后续写事务**两个事务之间不持锁**;顺序单消费者/合法公共
  writer 模型内无窗口,但不提供跨并发外部 SQL 改库的保证;defer 对
  未归因已提交事件的保守拒绝同为登记接受边界。跨 run pending 扫描
  作用域、生产 caller/调度属已登记后续边界(S3b)。
- **r4 如实新增披露的边界(不升级为门,留 mimo/Codex 裁定)**:
  retrieve 的 cache_hit 认领不落检索预约行,cache_hit 合法状态与
  "非 cache_hit 认领后把两条检索预约 ref+row 一起删"在存储上同构
  (创建规则的条件参数 cache_hit 不落独立列;本轮不加 schema 列,
  store 保持 -9)—— 检索预约的必要集合按"行存在 ⇒ 必须被引用"
  核验,行不存在按 cache_hit 合法不强制;复审探针未覆盖该形态,
  已在交付书残留清单登记。
- **消费侧权威核验是"写账前的只读复核",其强度与正常 writer 重放
  一致,不是第二套独立化学算法**(同类口径——同源复用,非独立
  双算)。**搜索层的结构权威依公共 writer 重放;verify_event_
  attachment_content 只核附随内容,不单独证明 state 身份**(复审
  R3 §6⑤ 入口划界,判据三 v12 落字)。
- **未实现(S3b,不冒充已交付)**:冻结池/备选/两类 deferred 的调度
  语义与 expected_parent_revision 激活;条件依赖/场景转换实际进入
  调度;模型协议与格式反馈;冻结 AtomTool → donor 诊断 → converter
  → audit → admission → submit 的生产调用链(**S3a/r4 仍未新增
  audit_hypothesis 生产 caller**,判据五 8d 的 caller 义务继续由
  S3b 承担);PPV1 独立 runner 双入口(继续 fail-closed)。
- 搜索层不构造/不修改任何化学对象;停止不是化学终点:停止报告保留
  未探索集合(deferred/blocked/悬空请求/claimed/open attempt),存在
  deferred/知识缺口时不称"所有路线都探索完";chemical endpoint 评估
  属 S4,本批不产出任何终点/矿化/解毒结论。

## 0c. mimo v11 回应八条件采信/纠错清单(受审;v12 重写)

复审 R3 §6 对 mimo v11 回应的裁定如下,**本仓采信限度:读码与
公开运行一致的部分才可作为事实输入;下列更正不得在 v12 回应中
再次照搬**:

1. **⑦ 括注更正(v11 判据一 2b 的表述错误,本版已改)**:v11 所写
   "工厂未登记 CX 类守卫拒绝 vs 真解析失败是不同异常类"的括注
   **不实** —— 同一入口(工厂/恢复)下 canonical+r 与真坏
   canonical 两种内因的外层**同为 ChemicalStateError 的不同
   kind**,按 `detail.reason.kind` 区分(unregistered_cx_class /
   unparseable_smiles);**跨入口**的外层才确不同(restore 入口
   外层 ChemicalStateError、公共 writer 外层 Ppv1StateContract
   Error)。不能把所有外层写成同一类,也不能把同入口内因写成
   不同异常类。
2. **两种潜在扩大(v11 回应若含,不采信)**:(a) 失败 diagnostic
   三个 None/`center_evidence={}` **不等于**下游 audit 所有轴/
   所有 R 行都不存在 —— converter 仍返回版本/来源元数据与
   center_match=None,缺 scope/proof 进 audit 中心 UNKNOWN;同一次
   audit 仍可以给其他轴 verified 并由决策表处置;(b) 同源重放/
   输入守卫**不证明来源真实性、历史执行、酶识别或供体机制**。
   (判据五 8b v12 落字。)
3. **① CX 保留 token(采纳更正)**:登记保留注解头按**真实 CX
   token** 写 —— `a:`(绝对/ABS)、`o<N>:`、`&<N>:`(相对组)、
   `^<N>:`(自由基层)与已登记 Sg 类;**不把 and/or/rad 英文类名
   当输入字面**;RDKit 2026.03.6 实际写出 ABS/AND/OR/自由基并
   保持严格身份往返;以三字面别名(and/or/rad)传入均按
   unregistered_cx_class 拒。接受/拒绝不认证样品。(判据一 v12
   落字。)
4. **② 系数句边界(采纳精化)**:非法表示系数在构造/提交边界拒;
   coefficient_binding_mismatch **属覆盖轴**(partial_unchecked_
   transformation + 中心 unknown,最终依首中规则),**不可虚称
   入口在比对"系数与结构重推导值"**;R2b 还需 caller 映射
   detail。(判据二/判据三 v12 落字。)
5. **③ 恒入/R2b(采纳精化)**:覆盖判定完成 full/partial 分支必带
   license/scope;unknown_coefficients/unverifiable 早退不带;
   R2b 调用方依赖落字,不把缺映射当化学已核;未来 caller 义务留
   S3b。(判据三 v12 落字。)
6. **④ 中心 partial 与四串守卫(采纳)**:删"裸 partial"概念,
   按映射理由码/中心 unknown 表述,与覆盖枚举分开;四个原始字符串
   守卫**限定执行成功路径解析前**;失败早退未解析;None 非通过。
   (判据三/判据五 v12 落字。)
7. **⑤ 入口划界(采纳)**:公共 writer 清单可补;搜索结构权威依
   公共 writer 重放,verify_event_attachment_content 只核附随内容,
   **不单独证明 state 身份**;substrate_profile 无生产 caller,档案
   输出/未来 caller 前置验证划界为 P2,不重开旧 S0–S2 门。(判据三
   v12 落字。)
8. **⑥ known_absent 轴归属(采纳)**:属**条件评估轴**非元素账;
   实体缺席/非物种字符串同值 ⇒ conflict;异值/未列出 ⇒ unknown;
   数值/区间缺席 ⇒ numeric_absence_semantics_undefined 的 unknown;
   不跨值域泛化物种字符串规则。(判据二/判据四 v12 落字。)
9. **⑧ 执行证据互证(保持)**:R3 复审独立验证 697、40/9、
   1299/8/17 与 276 输入;655c7e8 非任一轮父基线,其历史数字不引用
   为证据;读码行号/版本须与实际源码交叉核对,不能拿模型"已读"
   当执行。锁定 RDKit **2026.03.6**(v10 所写 2025.03.1 不采信)。

## 1. 判据一:分子身份(v12 文本,自包含)

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
(...) 坐标块=移除类;增强立体与自由基层注解=保留类)各自耗尽
自己的字段(字段内逗号/空格是内容,**登记内容含空格放行**,如
`atomProp:0.note.hello world`);未登记首头(含并列位置,如
`atomProp:0.n,r` 的 `r`)显式拒绝;DAT(SgD)值内逗号继续受
保护(DAT 剥离有适配器前提,只剥已登记 SgD 形态)。同一守卫覆盖
**全部原始 CX 入口**:工厂 build、strict_identity_of、判据五的
四个原始字符串字段、恢复入口与 audit 直接对象(2b)。
**v12 落字(复审 R3 §6①,真实 token)**:登记保留的立体/自由
基层注解头按**实际 CX token** 写 —— `a:`(绝对/ABS)、`o<N>:`
与 `&<N>:`(相对增强组)、`^<N>:`(自由基层)及已登记 Sg 类;
**and/or/rad 是英文类名,不是输入字面**(RDKit 2026.03.6 实际
写出 ABS/AND/OR/自由基并保持严格身份往返;以三字面别名作为
输入串传入均按 unregistered_cx_class 拒)。"接受/拒绝"只是输入
表示层契约结果,**不构成样品认证**(见 2b 的 r 不反推条款)。

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

**2b. 恢复/直接对象首消费同源验证(v8 新增,v9 落字三处,v11
再落一处,v12 更正一处)**:恢复入口(`ChemicalState.from_dict`)与
audit 直接 states 对象在首次授信前共用与公共 writer 同源的纯状态
验证(`validate_state_object`):(i) 版本门 + fidelity 分轴契约 +
structure_origin 合法;(ii) 结构态:raw 非空且过判据一第 2 条
同一输入守卫(未登记项 ⇒ 拒,不静默清洗信息再授 full);(iii)
raw 重推严格身份 == smiles_isomeric(同图异拼写如 OCC 接受;跨
分子如 H2 状态挂 CC=O 拒);(iv) smiles_isomeric 须为身份键规范形,
state_id/formal_charge/cn_identity/立体/同位素状态按工厂同源重推导
一致;(v) CN-only 走专用命名空间身份(cs(cn-only,cn))+ 未知
事实契约(不重推导结构)。v9 三处落字保持(同源验证非独立双算;
`r` 标记存在与含义均不采纳也不反驳;canonical+r 的上层错误名
语义须读内因)。**v12 落字(更正 v11 括注,复审 R3 §6⑦ 分两维)**:
同一入口下 canonical+r 与真坏 canonical 两种内因的外层**同为
ChemicalStateError 的不同 kind**,按 `detail.reason.kind` 区分
(unregistered_cx_class / unparseable_smiles)—— v11 所写"工厂
未登记 vs 真解析是不同异常类"的括注**错误**,不得沿用;**跨
入口**的外层才确不同(恢复入口外层 ChemicalStateError、公共
writer 外层 Ppv1StateContractError)。不能把所有外层写成同一类,
也不能把同入口内因写成不同异常类;"同源确定性重推导拒篡改"是
同一算法的复算(不是第二套独立证明);v10 ②③的精度句保持。
- 自报 formal_charge/stereo/isotope 与结构重推导一致的声明,
  限定"经首消费验证的入口"(2b 覆盖的 from_dict/直接对象/工厂/
  writer),不是所有裸 dataclass 对象的无条件性质。

**请评审**:(a) v12 落字(真实 token 表/外层-内因两维更正/同源
非独立算法)与 2b 三处 v9 落字是否准确、不引入越权认证;(b) 入口
清单(工厂/strict/判据五四字段/恢复/直接对象/搜索层全部消费入口)
是否闭合,不产生身份或 verified 证据的诊断入口(池输入 preview 的
conservation 诊断、冻结执行器内部解析)按 C2 划界在守卫外、其
结果不得回流为身份或核实证据(preview 保持 pool_unchanged/
diagnostic_only);(c) 判据本身(1–4)无需重评——文本如上展开
供自包含核对。

## 2. 判据二:参与物计量与元素/电荷核算(v12 文本,自包含;
v12 落字两处)

- **全氢账**:元素核算按全氢(分子式含 H);D/T 合并计 H(已
  登记披露,不区分同位素);**自由基电子不计入元素/电荷账**(数值
  账"平"在这两类有系统盲区,不得读成质量/电子守恒已核)。
- **系数契约(v12 落字,复审 R3 §6②)**:非法表示系数
  (零/负/非有限/bool)在**构造/提交边界拒绝**;
  coefficient_binding_mismatch **属覆盖轴违例**(按判据三处理:
  partial_unchecked_transformation/中心 unknown,**最终处置依
  其他轴与决策表首中规则,不能固定写成自动 reject/R2b,也不能
  固定写成 R5**);**不可虚称"入口在比对系数与结构重推导值"**
  —— 系数绑定核的是声明与补全/覆盖核算的对应,不是对结构重
  推导数值的比对;caller 侧须如实报告映射、不吞错改写处置;
  R2b(表示契约违反)的判定还须 caller 映射 detail(缺映射不当
  化学已核,见判据三 v12 落字)。
- **完整性 unknown**:未知系数 ⇒ coverage unknown_coefficients
  (中心结论 unknown,不猜数值)。**v12 落字(复审 R3 §6⑥,
  known_absent 轴归属)**:known_absent 类语义**属条件评估轴,
  不是元素账的判据**;实体缺席与**非物种字符串的同值缺席** ⇒
  conflict;非物种字符串**异值** known_absent 或未列出 ⇒ unknown;
  **数值/区间缺席 ⇒ unknown(数值缺席语义未定义
  numeric_absence_semantics_undefined,不跨值域泛化物种字符串的
  规则)**。
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

**请评审**:确认 v12 两处落字(系数句"不可虚称入口在比对系数与
结构重推导值" + known_absent 轴归属与数值缺席语义)是否准确反映
实现、防止下游把覆盖违例读成固定 R 行或把条件评估轴语义泛化到
元素账;其余展开文本与已同意条款一致(r3/r4 工程回修未改变本
判据任何口径)。

## 3. 判据三:admission 决策表与中心证据契约(v12 文本,自包含;
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
复算(改前提不换 ID ⇒ 拒)。**v11 落字(复审 §6 判据三"复用")**:
"跨假设复用 proof ⇒ 拒"按实际行为分写:跨假设**未绑定** proof 通常
产出**中心 unknown**;**篡改自报与复算不一致**抛契约异常、**本次
无成功 admission**(异常逃逸,不落任何 R 行)—— 两种情形不混成
同一种"拒"。audit.scope/proof_scope+basis 分轴披露:缺 proof/映射/
参与物覆盖时 unknown/partial(center_checker_scope_unknown 等),
字段存在不等于适用。**v12 落字(复审 R3 §6③④⑤)**:
- **R2b caller 映射依赖(③)**:R2b(表示契约违反)的最终判定依赖
  caller 侧如实提供映射 detail —— **缺映射不得当成化学已核**;
  未来 caller 映射义务留 S3b 生产链交付,不在本判据预先虚称已闭合;
- **中心 partial 的表述(④)**:中心结论层面**没有"裸 partial"**
  —— 未满足核(center)按**映射理由码/中心 unknown** 表述
  (center_checker_scope_unknown 等),与覆盖轴枚举
  (partial_unchecked_transformation)分开,不得把覆盖枚举当作中心
  结论名词用;四个原始字符串守卫(判据五)限定**执行成功路径的
  解析之前**;失败早退未解析、不消费其任何轴;None 非通过;
- **入口划界(⑤)**:公共 writer 清单可补;**搜索层的结构权威依
  公共 writer 重放,store.verify_event_attachment_content 只核附随
  投影/计划内容,不单独证明 state 身份**(state 身份的事实源仍是
  states/appearance 行与首消费同源验证);substrate_profile 无生产
  caller,档案输出/未来 caller 前置验证划界为 P2,不重开旧 S0–S2 门。

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

**v9 落字两处 + v10 精度更正一处 + v11 落字一处**:
- **scope 归属(v9,⑤已落地)**:当前代码 `completion_license_
  scope` 字面**不含**"不区分键断裂方式与电子去向"句;该表述归属
  **许可定义/本规则正文**(composition-only 许可不区分该参与物的
  键断裂方式与电子去向,是许可的语义边界)。字段字面未改、无版本
  身份影响;**本请求不再要求改代码 scope 字面**(复审 §5:已在
  规则正文,勿再当未闭合项;正式冻结由用户另裁)。
- **恒入 ≠ 已适用(v9;v11 精度补写)**:`completion_license`/
  `completion_license_scope` 恒入 center detail,**full/partial 完成
  分支携带 license/scope 字段**,但 unknown_coefficients/unverifiable
  的**早退例外**不携带(早退发生在覆盖判定之前);字段存在不等于
  本结论使用了补全许可;判定"本结论依据含许可补全"须同时看
  **product_coverage=full、uncovered_reactant_refs/uncovered_
  product_refs 非空、unlicensed_uncovered_identities 为空** 三条件
  组合;license_applied 标志/顶层别名/同屏渲染列属后续 API/展示层
  (P2,不作本轮门)。
- **v10 精度更正(mimo v9 回应 ⑥ 的判负口径,保持)**:mimo 曾
  概括"partial = 许可本身判负"—— 不精确,不得照抄:(a) 实际枚举
  是 `partial_unchecked_transformation`(存在额外未核实转化/未
  核实结构贡献),不是裸 "partial";(b) uncovered+partial 组合下
  `coverage_violations` 可能是 `coefficient_binding_mismatch`(系数
  与声明不符)或补全数值不符,与许可是否登记无关 —— **不能一律称
  "许可本身判负"**,须读 coverage_violations 的逐条 kind;(c)
  `unknown_coefficients` 等早退(coverage unknown)发生在覆盖判定
  之前,**尚未使用许可**,不得称"已使用许可后判负"(**r9 原话是
  "补全规则被调用且判负",不得转写成"许可本身判负"**);(d)
  许可未登记身份的 case(completion_license_unregistered_identity)
  才直接关联"数值配平不证明未登记多原子共底物初始图的结构贡献"
  这句规则正文。
- **v11 落字(复审 §6 判据三"恒入/复用"补写)**:见上文类型契约
  段 —— full/partial 完成分支的 license/scope 恒入、早退例外、跨
  假设未绑定 proof 与篡改复算不一致两种情形分写,不再用单一"拒"
  概括。

**请评审**:(a) v12 落字(R2b caller 映射依赖/中心 partial 按映射
理由码与覆盖枚举分开/入口划界)与 v11 落字(恒入/复用分写)、v10
精度更正四点(a–d)是否准确反映实现语义、足以防止下游把 coverage
枚举读成"许可判负"或把附随内容核验读成 state 身份证明;(b) v9
scope 归属与恒入≠已适用+三条件判定是否如实(确认后本项不再列入
后续请求);(c) 决策表与覆盖核算展开文本是否与实现一致。

## 4. 判据四:条件相容聚合(v12 文本,自包含;v11 落字三处保持,
v12 补一处轴归属)

- **快照一致性**:路径上下文快照由已验证父对象派生,派生先验
  validate 父对象;快照的 covered_requirement_signatures 与已记录
  的 per_requirement 评估行**双向对应**(签名↔行双向:删行/改
  签名都拒)。**v11 落字(复审 §6 判据四"孤儿方向",更正 v10
  方向)**:两个方向的处置分写 —— **已有必要要求绑定旧作用域但
  无按签名快照 ⇒ unknown**(证据不足,不猜);**评估行/签名无
  对应要求或集合不一致 ⇒ `context_snapshot_inconsistent` 拒**
  (引用完整性/一致性失败,不是 unknown;v10 把后一种写成 unknown
  且方向写反,以本版为准)。
- **内容身份**:PathContext 内容身份同源重算;**两种不可变机制
  分写(v9 落字)**:Requirement/ConditionFact 由 frozen(嵌套冻结)
  强制;PathContext 本体**非 frozen**,其不可变性由消费前 validate
  的内容身份同源重算兜底(就地改语义字段保留原 context_id ⇒
  `context_content_identity_mismatch` 拒)。不得把两种机制写成同一
  类不可变;任何派生/评估/审核入口消费前必须先 validate(绕过
  validate 直读字段属违约)。**v11 落字(复审 §6 判据四"入口
  限定")**:已**强制** validate 的入口 = 恢复/from_dict、derive 的
  父对象、audit 直接对象;`assess_conditions`/`assess_candidate_
  conditions`/`route_assessment` 自身**没有**该调用,**需上游纪律**
  (新 S3b 必须接真实守卫,不以上游纪律替代入口强制)。
- **重建半边(v11 落字,复审 §6 判据四)**:合法**新内容重建**的
  语义 context 使用**新 context_id** 并保留 `parent_context_ref`
  链(旧引用不复用)—— 新内容重建**不是篡改**,不得被
  content_identity 判据拒绝;篡改是"旧 ID + 新内容"的组合(见
  上文 mismatch 拒)。
- **三分与矛盾**:条件评估三分为 satisfied/conflict/unknown;已知
  事实与要求冲突为**单向矛盾**(conflict 只阻止当前场景,不反推
  全局)。**v12 落字(复审 R3 §6⑥,known_absent 轴归属)**:
  known_absent 类缺席语义**属本条件评估轴,不是元素账判据** ——
  实体缺席/非物种字符串同值 ⇒ conflict;非物种字符串异值
  known_absent 或未列出 ⇒ unknown;数值/区间缺席 ⇒ unknown
  (numeric_absence_semantics_undefined,不跨值域泛化物种字符串
  规则;该句与判据二 v12 落字同源,两处一致表述)。
- **场景评估口径**:文献观察环境、矩阵"污水"标签、工具隐式
  O2/H2O、transformation_class 标签都**不能**构造当前条件事实;
  请求 condition_compatible 不是已相容;空要求/未知覆盖不自动
  compatible(相容判断需实际评估)。
- **行↔签名对应的契约前提**:绑定字段一经冻结不得后改;变更须
  走新评估/新快照(将来引入要求可变性,旧快照整体拒绝是故意
  fail-closed,不当 bug 修)。

**请评审**:(a) v11 三处落字(孤儿方向更正/入口强制与纪律清单/
重建半边)与 v12 known_absent 轴归属补写是否准确、与 v10 的差异
是否如实登记;(b) 分写/口径其余文本与实现一致(v9/r2/r3/r4 无
进一步变化)。

## 5. 判据五:供体一致性诊断(v12 文本,自包含)

- **判定基础 = 实际净变化集**:供体编辑一致性以键 diff ∪ 电荷/
  立体/同位素变化集的实际净变化判定(含 bond_stereo_change 与
  键级立体入变化集;非四面体公开列项按标签类型分开),不采信
  声明的"编辑列表"与实际不一致的自报。**v11 落字(复审 §6
  S3b 行)**:区域净变化不认证**供体模板/机制**(净变化判定是
  表示层契约,不是机理证明);**图等价不是酶识别**;
  legacy_cn_match 仅**旁证**(不是反应身份判定)。
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
  载荷(不可变、入口身份复算);跨假设未绑定 proof ⇒ 中心
  unknown;篡改自报与复算不一致 ⇒ 契约异常(本次无成功
  admission;见判据三 v11 落字)。
- **四个原始字符串入口与工厂同源守卫**:供体诊断的四个原始结构
  串字段与工厂共用判据一第 2 条输入守卫(未登记 CX 项 ⇒ 契约
  拒绝)。
- **声明–执行净效应对账 + 镜像终态归一**:声明编辑与实际执行
  对账(镜像活 ID 表 + 前置复核);终态序列化与冻结执行器对齐。
- **8b 拒绝与失败早退(v9 落字,精度保持;v12 补一处)**:失败诊断
  是**三个**判定字段 reaction_center_match/strict_target_match/
  legacy_cn_match 均为 None、`diagnostic.center_evidence={}`;
  **converter 仍返回版本/来源元数据与 center_match=None**(不是
  "四轴 None",也不是"converter 整个 evidence 为空")。None=未
  评估,**不等于通过**(三个 None 不是通过;legacy_cn_match 单
  True 也不是任何 R 行的通过依据);`execution_ok=False` 早退
  路径不解析三字段亦不消费其任何轴,无 verified 泄漏面。拒绝为
  契约性拒绝 ⇒ 本次诊断/审核不产生任何轴结论与 disposition;
  调用方不得吞异常后按 retain/verified/any-R 行记录(异常≠处置
  行)。两处表述边界:拒绝原始 `r` 不构成"已证实实验精确消旋";
  裸指定 SMILES 只声明表示事实,不称实验纯品/对映纯;strict=
  True = 同一化学身份,不是同一样品/同一立体纯度。
  **v12 落字(复审 R3 §6"两种潜在扩大"之 (a),失败 diagnostic
  与下游 audit 分开)**:失败 diagnostic 的三个 None/`center_
  evidence={}` **不等于**下游 audit 所有轴/所有 R 行都不存在 ——
  converter 仍返回版本/来源元数据与 center_match=None,缺
  scope/proof 进 audit 中心 UNKNOWN;**同一次 audit 仍可以给
  其他轴 verified 并由决策表处置**(中心 unknown 与其他轴的
  verified 不互斥,按决策表首中规则合成整体处置);不得把
  "诊断失败"扩大成"整个 audit 无结论"。同源重放/输入守卫也
  **不证明来源真实性、历史执行、酶识别或供体机制**(②之 (b),
  同类口径)。四个原始字符串守卫限定**执行成功路径的解析之前**
  (§6④;失败早退未解析)。
- **8d caller 义务(如实披露,仍未闭合)**:S3 新 caller 必须承担
  "让 AuditContractError 逃逸并中止本次 admission 计算/提交"的
  义务,不得吞异常继续。**S3a/r4 未新增生产 caller(生产链属
  S3b)**,该义务尚未被执行证据闭合;当前静态证据(10 个
  AuditContractError 抛点全部在 audit.py、无 enclosing 宽捕获
  try-body、check_edit_against_donor 唯一源内调用无 try 祖先)
  不是动态安全的通用证明。S3b 交付生产链时以实际调用与宽捕获
  负控(异常正常逃逸 + 合法正控)闭合。

**请评审**:(a) 8b"三个 None + converter 元数据"表述与早退边界
是否准确,v12 落字"失败 diagnostic 与下游 audit 各轴分开"是否
如实(中心 unknown 与其他轴 verified 不互斥);(b) 8d"未闭合但
如实披露"作为 S3a/r4 边界是否可接受(闭合路径 = S3b caller +
回归测试);(c) v11 落字(净变化不认证模板/图等价非酶识别/
legacy_cn_match 仅旁证)与 0c 清单是否足以防止把不存在的分支名/
错误版本/错误异常处置再次当作读码事实;(d) 其余条款展开文本
是否与实现一致。

## 6. 程序证据与状态(程序事实,不替代化学判断;执行类声明待验证)

- 规则级测试:ppv1 全量 **787 passed/0 skip**(697 r3 存量 + 90
  r4 新增,全部合成夹具;90 项覆盖三组残余 P1 的必要集合/状态口
  策略/生命周期来源反例与合法控制;四崩溃/H06 双进程 barrier/
  H07 H08/零预算/悬空请求矩阵 23 项复跑通过);
- 基线红绿(直接父基线 41d0cd5 detached worktree 同字节):新
  回归 **78 红 + 12 正控绿**(78 = **77"预期结构化拒绝未发生"**
  ——58 SearchIntegrityError + 18 SearchRecoveryError + 1
  SearchContractError —— **+ 1 形态红**(恢复报告缺
  unknown_status_requests 键的 KeyError);无 collection 红/无
  错误 kind 先停/无值断言红;12 绿 = 9 入口正控 + 1 sent/response
  未知状态已拒保持 + 2 合法生命周期控制);更新的既有测试
  **1 版本红(profile-12/search-4 断言)+ 22 绿**;复审 R3 §2 的
  精度口径按实记录(交付方不再把"未发生指定异常"与"值断言"混计);
- G01:安全隔离工程回归(R7 路径白名单 + R8/S3a/r2/r3/r4 输入,
  **277** 项输入 SHA 前后一致;不复制 evaluation/金标/题面/封存/
  v4;固定 PYTHONPATH/空 BBD_DATA_ROOT/V3_CODE_ROOT/V43_ASSET_
  ROOT/DEPENDING_V3_ROOT)⇒ **1389 passed/8 skipped/17
  deselected**,exit 0(8 skip = 5 真实评价依赖 + 1 v4 对照源 +
  2 phase_d 派生 metadata;17 deselect = 16 slow + 1 明确排除
  export 用例,逐项 nodeid 披露;R7 1110/8/17、R8 1138/8/17、
  S3a 首批 1196/8/17、r2 1250/8/17、r3 1299/8/17 各自单列,不
  混计;1389 = r3 1299 + 90 新 r4 测试);
- 契约族:search ppv1-search-3 → **ppv1-search-4**(必要集合完整
  性/请求状态口策略守卫/生命周期来源闭合),profile -11 →
  **-12**(contracts 登记);store 保持 **-9**(表结构与 writer
  行为未改;r4 核验全部复用既有函数,无新入口);search-limits
  保持 **-3**(键/默认/范围/单位/计数语义未动;状态口接守卫与
  必要集合语义随 search 契约登记);PPV1 从未放行执行流,无历史
  产物迁移;legacy code_identity 聚合不变
  (4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c
  29ae;legacy 排除 pollutant/ 新包,r4 改动全部在其内);
- 判据未冻结;v12 无新化学机制;受审文字:0b 边界披露更新、0c
  重写的 mimo v11 回应八条件采信/纠错清单、判据一 2b(真实
  token 表 + 外层-内因两维更正)、判据二(系数句/known_absent
  轴归属)、判据三(R2b caller 映射/中心 partial 分写/入口划界)、
  判据四(known_absent 轴归属)、判据五 8b(失败 diagnostic 与
  下游 audit 分开)的 v12 落字,8d 披露保持;
- 参考(外部常识,非本仓资产):RDKit Book(CXSMILES 扩展/增强
  立体/立体化学章节)、rdCIPLabeler API;CXSMILES 解析器行为经
  Release_2026_03_6 源码取证与实证用例校准;**冻结前须以执行
  证据复核 RDKit(锁定 2026.03.6)词法取证与放行正控的往返无损**。

## 7. 请求的回复格式

对每条判据:1) 结论(同意/不同意/有条件同意+条件);2) 可直接
落进规则文字的修改建议;3) "程序上诚实但化学上误导"风险点。
逐条表态,不接受总体评价式回复。执行类声明一律标"待执行验证"。
引用 0c 清单之外的事实(分支名/版本/异常处置)时必须先给出可复核
的源位置,否则按不采信处理。
